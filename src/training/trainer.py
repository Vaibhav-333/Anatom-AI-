"""
trainer.py — Training and validation loop for the 3D U-Net.

Features
--------
- Mixed precision training (torch.amp) for 40–60% memory reduction on GPU.
- Cosine annealing LR schedule with linear warmup.
- Model checkpointing: saves best validation Dice and last checkpoint.
- Gradient clipping to prevent exploding gradients in deep 3D networks.
- Deep supervision loss integration (Elite Feature A).
- Structured per-epoch logging of all loss components and BraTS Dice metrics.

Usage (see scripts/train.py for the full CLI):

    from src.training.trainer import Trainer, TrainingConfig

    config = TrainingConfig(
        data_root="outputs/processed",
        output_dir="outputs/checkpoints",
        max_epochs=300,
        batch_size=2,
        patch_size=(128, 128, 128),
    )
    trainer = Trainer(config)
    trainer.fit()
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR
from torch.utils.data import DataLoader, random_split

from src.models.losses import CombinedLoss, DeepSupervisionLoss
from src.models.unet3d import UNet3D
from src.training.dataset import BraTSDataset
from src.training.metrics import SegmentationMetrics

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Hyperparameters and paths for a training run."""
    # Paths
    data_root: str = "outputs/processed"
    output_dir: str = "outputs/checkpoints"
    subject_pattern: str = "BraTS*"

    # Model
    in_channels: int = 4
    num_classes: int = 4
    base_channels: int = 32
    deep_supervision: bool = True
    dropout_p: float = 0.1

    # Training
    max_epochs: int = 300
    batch_size: int = 2
    num_workers: int = 4
    val_split: float = 0.2               # Fraction of subjects used for validation
    patch_size: Tuple[int, int, int] = (128, 128, 128)
    patches_per_subject: int = 2
    tumor_sample_prob: float = 0.5

    # Optimiser
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5
    grad_clip_norm: float = 1.0

    # LR schedule
    warmup_epochs: int = 10             # Linear warmup
    min_lr: float = 1e-6               # Cosine annealing floor

    # Loss
    dice_weight: float = 0.5
    focal_gamma: float = 2.0

    # Checkpointing
    save_every_n_epochs: int = 10
    validate_every_n_epochs: int = 5
    early_stop_patience: int = 50       # Epochs without val improvement before stopping

    # Hardware
    device: str = "auto"               # "auto" | "cuda" | "cpu" | "mps"
    mixed_precision: bool = True       # AMP — disable if hitting precision issues
    seed: int = 42


class Trainer:
    """
    Manages the complete training lifecycle for the 3D U-Net.

    Parameters
    ----------
    config : TrainingConfig
    """

    def __init__(self, config: TrainingConfig) -> None:
        self.cfg = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.device = self._resolve_device(config.device)
        logger.info("Training device: %s", self.device)

        torch.manual_seed(config.seed)
        np.random.seed(config.seed)

        # Model
        self.model = UNet3D(
            in_channels=config.in_channels,
            num_classes=config.num_classes,
            base_channels=config.base_channels,
            deep_supervision=config.deep_supervision,
            dropout_p=config.dropout_p,
        ).to(self.device)
        logger.info("Model parameters: %s M", f"{self.model.count_parameters() / 1e6:.1f}")

        # Loss
        base_loss = CombinedLoss(
            dice_weight=config.dice_weight,
            focal_gamma=config.focal_gamma,
        )
        self.criterion = DeepSupervisionLoss(base_loss=base_loss) if config.deep_supervision \
            else base_loss

        # Optimiser
        self.optimiser = AdamW(
            self.model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )

        # LR scheduler: linear warmup → cosine decay
        warmup = LinearLR(
            self.optimiser,
            start_factor=0.1,
            end_factor=1.0,
            total_iters=config.warmup_epochs,
        )
        cosine = CosineAnnealingLR(
            self.optimiser,
            T_max=max(config.max_epochs - config.warmup_epochs, 1),
            eta_min=config.min_lr,
        )
        self.scheduler = SequentialLR(
            self.optimiser,
            schedulers=[warmup, cosine],
            milestones=[config.warmup_epochs],
        )

        # AMP scaler
        self.scaler = torch.amp.GradScaler(enabled=config.mixed_precision and self.device.type == "cuda")

        # Metrics
        self.metrics_fn = SegmentationMetrics(
            num_classes=config.num_classes,
            compute_hd95=False,   # Disabled during training for speed
        )

        # State
        self.best_val_dice: float = 0.0
        self.no_improve_count: int = 0
        self.history: List[Dict] = []

    def fit(self) -> None:
        """Run the full training loop."""
        train_loader, val_loader = self._build_dataloaders()

        logger.info("Starting training: %d epochs", self.cfg.max_epochs)
        self._save_config()

        for epoch in range(1, self.cfg.max_epochs + 1):
            t0 = time.perf_counter()

            train_metrics = self._train_epoch(train_loader, epoch)

            val_metrics: Dict = {}
            if epoch % self.cfg.validate_every_n_epochs == 0:
                val_metrics = self._validate_epoch(val_loader, epoch)
                self._check_improvement(val_metrics, epoch)

            if epoch % self.cfg.save_every_n_epochs == 0:
                self._save_checkpoint(epoch, tag="periodic")

            self.scheduler.step()
            elapsed = time.perf_counter() - t0

            epoch_log = {
                "epoch": epoch,
                "lr": self.scheduler.get_last_lr()[0],
                "elapsed_sec": round(elapsed, 1),
                **train_metrics,
                **{f"val_{k}": v for k, v in val_metrics.items()},
            }
            self.history.append(epoch_log)

            logger.info(
                "Epoch %4d/%d  loss=%.4f  val_dice_wt=%.4f  lr=%.2e  t=%.1fs",
                epoch, self.cfg.max_epochs,
                train_metrics.get("loss", 0),
                val_metrics.get("dice_wt", 0),
                epoch_log["lr"],
                elapsed,
            )

            if self.no_improve_count >= self.cfg.early_stop_patience:
                logger.info(
                    "Early stopping at epoch %d (no val improvement for %d epochs).",
                    epoch, self.cfg.early_stop_patience,
                )
                break

        self._save_history()
        logger.info("Training complete. Best val Dice (WT): %.4f", self.best_val_dice)

    def _train_epoch(self, loader: DataLoader, epoch: int) -> Dict:
        """One training epoch. Returns averaged loss metrics."""
        self.model.train()
        total_loss = 0.0
        breakdown_accum: Dict[str, float] = {}
        n_batches = 0

        for images, labels in loader:
            images = images.to(self.device, non_blocking=True)
            labels = labels.to(self.device, non_blocking=True)

            self.optimiser.zero_grad(set_to_none=True)

            with torch.amp.autocast(device_type=self.device.type, enabled=self.cfg.mixed_precision and self.device.type == "cuda"):
                output = self.model(images)

                if self.cfg.deep_supervision and isinstance(output, tuple):
                    main_logits, aux_logits = output
                    loss, breakdown = self.criterion(main_logits, aux_logits, labels)
                else:
                    logits = output if not isinstance(output, tuple) else output[0]
                    loss, breakdown = self.criterion(logits, labels)

            self.scaler.scale(loss).backward()
            self.scaler.unscale_(self.optimiser)
            nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.grad_clip_norm)
            self.scaler.step(self.optimiser)
            self.scaler.update()

            total_loss += loss.item()
            for k, v in breakdown.items():
                breakdown_accum[k] = breakdown_accum.get(k, 0.0) + v
            n_batches += 1

        n = max(n_batches, 1)
        return {
            "loss": total_loss / n,
            **{k: v / n for k, v in breakdown_accum.items()},
        }

    @torch.no_grad()
    def _validate_epoch(self, loader: DataLoader, epoch: int) -> Dict:
        """One validation epoch. Returns averaged BraTS Dice metrics."""
        self.model.eval()
        all_results = []

        for images, labels in loader:
            images = images.to(self.device)
            labels_np = labels.cpu().numpy()

            logits = self.model(images)
            if isinstance(logits, tuple):
                logits = logits[0]

            preds = logits.argmax(dim=1).cpu().numpy()

            for b in range(preds.shape[0]):
                result = self.metrics_fn.compute(preds[b], labels_np[b])
                all_results.append(result)

        return SegmentationMetrics.aggregate(all_results)

    def _check_improvement(self, val_metrics: Dict, epoch: int) -> None:
        """Update best model checkpoint if val WT Dice improved."""
        dice_wt = val_metrics.get("dice_wt", 0.0)
        if dice_wt > self.best_val_dice:
            self.best_val_dice = dice_wt
            self.no_improve_count = 0
            self._save_checkpoint(epoch, tag="best")
            logger.info("New best val WT Dice: %.4f — checkpoint saved.", dice_wt)
        else:
            self.no_improve_count += self.cfg.validate_every_n_epochs

    def _save_checkpoint(self, epoch: int, tag: str) -> None:
        """Save model state dict + optimiser state to disk."""
        path = self.output_dir / f"checkpoint_{tag}.pt"
        torch.save({
            "epoch": epoch,
            "model_state": self.model.state_dict(),
            "optimiser_state": self.optimiser.state_dict(),
            "best_val_dice": self.best_val_dice,
            "config": asdict(self.cfg),
        }, path)
        logger.debug("Checkpoint saved: %s", path)

    def _save_config(self) -> None:
        """Persist training config to JSON for reproducibility."""
        with open(self.output_dir / "training_config.json", "w") as f:
            json.dump(asdict(self.cfg), f, indent=2)

    def _save_history(self) -> None:
        """Write per-epoch training history to JSON."""
        with open(self.output_dir / "training_history.json", "w") as f:
            json.dump(self.history, f, indent=2)

    def _build_dataloaders(self) -> Tuple[DataLoader, DataLoader]:
        """Split subjects into train/val sets and build DataLoaders."""
        data_root = Path(self.cfg.data_root)
        subject_dirs = sorted([
            d for d in data_root.glob(self.cfg.subject_pattern) if d.is_dir()
        ])

        if not subject_dirs:
            raise FileNotFoundError(
                f"No processed subjects found in {data_root}. "
                "Run the Phase 1 pipeline first."
            )

        n_val = max(1, int(len(subject_dirs) * self.cfg.val_split))
        n_train = len(subject_dirs) - n_val

        rng = torch.Generator().manual_seed(self.cfg.seed)
        train_dirs, val_dirs = random_split(subject_dirs, [n_train, n_val], generator=rng)

        train_ds = BraTSDataset(
            list(train_dirs),
            patch_size=self.cfg.patch_size,
            patches_per_subject=self.cfg.patches_per_subject,
            tumor_sample_prob=self.cfg.tumor_sample_prob,
            augment=True,
            seed=self.cfg.seed,
        )
        val_ds = BraTSDataset(
            list(val_dirs),
            patch_size=self.cfg.patch_size,
            patches_per_subject=1,
            tumor_sample_prob=0.0,   # No tumour bias during val
            augment=False,
            seed=self.cfg.seed,
        )

        logger.info(
            "Dataset split: %d train subjects / %d val subjects",
            len(list(train_dirs)), len(list(val_dirs)),
        )

        train_loader = DataLoader(
            train_ds,
            batch_size=self.cfg.batch_size,
            shuffle=True,
            num_workers=self.cfg.num_workers,
            pin_memory=self.device.type == "cuda",
        )
        val_loader = DataLoader(
            val_ds,
            batch_size=1,
            shuffle=False,
            num_workers=self.cfg.num_workers,
        )
        return train_loader, val_loader

    @staticmethod
    def _resolve_device(device_str: str) -> torch.device:
        if device_str == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return torch.device("mps")
            return torch.device("cpu")
        return torch.device(device_str)

    @classmethod
    def load_checkpoint(
        cls,
        checkpoint_path: str | Path,
        config: Optional[TrainingConfig] = None,
    ) -> "Trainer":
        """
        Restore a Trainer from a saved checkpoint.

        Parameters
        ----------
        checkpoint_path : path to a .pt checkpoint file.
        config : if None, config is loaded from the checkpoint itself.

        Returns
        -------
        Trainer with model weights and optimiser state restored.
        """
        ckpt = torch.load(checkpoint_path, map_location="cpu")
        if config is None:
            cfg_dict = ckpt.get("config", {})
            config = TrainingConfig(**cfg_dict)

        trainer = cls(config)
        trainer.model.load_state_dict(ckpt["model_state"])
        trainer.optimiser.load_state_dict(ckpt["optimiser_state"])
        trainer.best_val_dice = ckpt.get("best_val_dice", 0.0)
        logger.info(
            "Restored checkpoint from epoch %d  (best val dice=%.4f)",
            ckpt.get("epoch", "?"), trainer.best_val_dice,
        )
        return trainer
