"""
train.py — CLI entrypoint for Phase 2: 3D U-Net training.

Usage
-----
# Train with default config on processed BraTS data:
    python scripts/train.py \\
        --data-root outputs/processed \\
        --output-dir outputs/checkpoints

# Train with custom hyperparameters:
    python scripts/train.py \\
        --data-root outputs/processed \\
        --output-dir outputs/checkpoints \\
        --epochs 300 \\
        --batch-size 2 \\
        --lr 1e-4 \\
        --patch-size 128 128 128 \\
        --base-channels 32 \\
        --device cuda

# Resume from checkpoint:
    python scripts/train.py \\
        --data-root outputs/processed \\
        --output-dir outputs/checkpoints \\
        --resume outputs/checkpoints/checkpoint_best.pt

# Evaluate only (no training):
    python scripts/train.py \\
        --data-root outputs/processed \\
        --output-dir outputs/eval \\
        --eval-only \\
        --resume outputs/checkpoints/checkpoint_best.pt

# Dry run (1 epoch, 1 batch) to verify pipeline:
    python scripts/train.py \\
        --data-root outputs/processed \\
        --output-dir outputs/debug \\
        --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.trainer import Trainer, TrainingConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Anatom AI Phase 2 — 3D U-Net Training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Paths
    parser.add_argument("--data-root", type=Path, required=True,
                        help="Root of processed BraTS subjects (Phase 1 output).")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Directory for checkpoints and logs.")
    parser.add_argument("--resume", type=Path, default=None,
                        help="Path to a .pt checkpoint to resume from.")

    # Model
    parser.add_argument("--base-channels", type=int, default=32,
                        help="Base feature channels (default 32).")
    parser.add_argument("--no-deep-supervision", action="store_true",
                        help="Disable deep supervision auxiliary heads.")

    # Training
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--patch-size", type=int, nargs=3, default=[128, 128, 128],
                        metavar=("H", "W", "D"))
    parser.add_argument("--patches-per-subject", type=int, default=2)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)

    # Loss
    parser.add_argument("--dice-weight", type=float, default=0.5,
                        help="Weight for Dice component in combined loss.")
    parser.add_argument("--focal-gamma", type=float, default=2.0)

    # Hardware
    parser.add_argument("--device", type=str, default="auto",
                        choices=["auto", "cuda", "cpu", "mps"])
    parser.add_argument("--no-amp", action="store_true",
                        help="Disable automatic mixed precision.")

    # Modes
    parser.add_argument("--eval-only", action="store_true",
                        help="Skip training — evaluate the loaded checkpoint.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run 1 epoch with 1 batch for pipeline verification.")

    # Logging
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING"])

    return parser.parse_args()


def build_config(args: argparse.Namespace) -> TrainingConfig:
    return TrainingConfig(
        data_root=str(args.data_root),
        output_dir=str(args.output_dir),
        base_channels=args.base_channels,
        deep_supervision=not args.no_deep_supervision,
        max_epochs=1 if args.dry_run else args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        patch_size=tuple(args.patch_size),
        patches_per_subject=1 if args.dry_run else args.patches_per_subject,
        val_split=args.val_split,
        num_workers=0 if args.dry_run else args.num_workers,
        dice_weight=args.dice_weight,
        focal_gamma=args.focal_gamma,
        device=args.device,
        mixed_precision=not args.no_amp,
        seed=args.seed,
        validate_every_n_epochs=1 if args.dry_run else 5,
        save_every_n_epochs=1 if args.dry_run else 10,
    )


def run_evaluation(trainer: Trainer, args: argparse.Namespace) -> None:
    """Run full evaluation loop with HD95 enabled."""
    from src.training.metrics import SegmentationMetrics
    from src.training.dataset import BraTSDataset
    from torch.utils.data import DataLoader
    from pathlib import Path
    import torch

    data_root = Path(args.data_root)
    subject_dirs = sorted([d for d in data_root.glob("BraTS*") if d.is_dir()])

    eval_ds = BraTSDataset(
        subject_dirs,
        patch_size=tuple(args.patch_size),
        patches_per_subject=1,
        augment=False,
    )
    loader = DataLoader(eval_ds, batch_size=1, num_workers=0)
    metrics_fn = SegmentationMetrics(compute_hd95=True)

    trainer.model.eval()
    all_results = []

    with torch.no_grad():
        for i, (images, labels) in enumerate(loader):
            images = images.to(trainer.device)
            logits = trainer.model(images)
            if isinstance(logits, tuple):
                logits = logits[0]
            pred = logits.argmax(dim=1).cpu().numpy()
            target = labels.numpy()
            result = metrics_fn.compute(pred[0], target[0], f"subject_{i}")
            all_results.append(result)
            print(f"  Subject {i:03d}: WT={result.dice_wt:.4f}  TC={result.dice_tc:.4f}  ET={result.dice_et:.4f}")

    summary = SegmentationMetrics.aggregate(all_results)
    print("\n=== Evaluation Summary ===")
    for k, v in sorted(summary.items()):
        print(f"  {k}: {v:.4f}")


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    config = build_config(args)

    if args.resume:
        print(f"Resuming from checkpoint: {args.resume}")
        trainer = Trainer.load_checkpoint(args.resume, config=config)
    else:
        trainer = Trainer(config)

    if args.dry_run:
        print("DRY RUN MODE: 1 epoch, verifying pipeline integrity.")

    if args.eval_only:
        if args.resume is None:
            print("Error: --eval-only requires --resume.")
            sys.exit(1)
        run_evaluation(trainer, args)
        return

    print(f"\nStarting training — {config.max_epochs} epochs")
    print(f"Data root : {config.data_root}")
    print(f"Output dir: {config.output_dir}")
    print(f"Device    : {trainer.device}")
    print(f"Parameters: {trainer.model.count_parameters() / 1e6:.1f}M\n")

    trainer.fit()


if __name__ == "__main__":
    main()
