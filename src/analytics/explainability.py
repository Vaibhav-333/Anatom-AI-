"""
explainability.py — Model interpretability for the 3D U-Net.

Two complementary techniques
------------------------------
1. Monte Carlo Dropout (MC Dropout)
   Runs N stochastic forward passes with dropout active to estimate
   per-voxel predictive uncertainty. Produces:
     - mean_probs : (C, H, W, D) — averaged class probabilities
     - variance   : (C, H, W, D) — epistemic uncertainty per class
     - entropy    : (H, W, D)    — predictive entropy (nats)

2. 3D Grad-CAM
   Hooks into a target layer and computes gradient-weighted activation
   maps to explain which spatial regions drove a specific class prediction.
   Produces a saliency map of shape (H, W, D) in [0, 1].

Usage
-----
    from src.analytics.explainability import GradCAM3D, UncertaintyEstimator
    from src.models.unet3d import UNet3D

    model = UNet3D(...)
    # --- MC Dropout ---
    estimator = UncertaintyEstimator(n_samples=20)
    result = estimator.estimate(model, x_tensor)

    # --- Grad-CAM (hook into dec0 block) ---
    cam = GradCAM3D(model, target_layer=model.dec0)
    saliency = cam.generate(x_tensor, target_class=3)   # ET class
    cam.remove_hooks()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class UncertaintyResult:
    """Per-voxel uncertainty estimates from MC Dropout inference."""

    # (C, H, W, D) — mean softmax probability per class across N passes
    mean_probs: np.ndarray

    # (C, H, W, D) — variance across N passes (epistemic uncertainty)
    variance: np.ndarray

    # (H, W, D) — predictive entropy: -Σ p·log(p) across classes
    entropy: np.ndarray

    # (H, W, D) — argmax of mean_probs (predicted segmentation)
    predicted_class: np.ndarray

    # Number of MC samples used
    n_samples: int = 0


class UncertaintyEstimator:
    """
    Monte Carlo Dropout uncertainty estimation.

    Activates Dropout layers during inference and runs N stochastic
    forward passes to estimate epistemic uncertainty per voxel.

    Parameters
    ----------
    n_samples : int
        Number of stochastic forward passes (default 20).
        Higher values reduce variance in the uncertainty estimate.
    """

    def __init__(self, n_samples: int = 20) -> None:
        if n_samples < 2:
            raise ValueError("n_samples must be >= 2 for meaningful uncertainty estimates.")
        self.n_samples = n_samples

    def estimate(
        self,
        model: nn.Module,
        x: torch.Tensor,
        device: Optional[torch.device] = None,
    ) -> UncertaintyResult:
        """
        Run MC Dropout inference and compute uncertainty maps.

        Parameters
        ----------
        model : nn.Module — trained UNet3D (or any model with Dropout).
        x     : (1, C, H, W, D) input tensor — single subject.
        device : torch device; if None, inferred from model parameters.

        Returns
        -------
        UncertaintyResult with mean_probs, variance, entropy, predicted_class.
        """
        if x.shape[0] != 1:
            raise ValueError(
                f"UncertaintyEstimator expects batch_size=1, got {x.shape[0]}. "
                "Process one subject at a time."
            )

        if device is None:
            device = next(model.parameters()).device
        x = x.to(device)

        # Enable Dropout while keeping rest of model behaviour stable.
        # model.train() activates all Dropout modules; we restore state afterward.
        was_training = model.training
        model.train()

        all_probs: list[np.ndarray] = []

        with torch.no_grad():
            for _ in range(self.n_samples):
                output = model(x)
                # UNet3D returns (main, [aux...]) in train mode with deep supervision
                logits = output[0] if isinstance(output, tuple) else output
                probs = torch.softmax(logits, dim=1)          # (1, C, H, W, D)
                all_probs.append(probs.squeeze(0).cpu().numpy())   # (C, H, W, D)

        # Restore original training state
        model.train(was_training)

        # Stack: (N, C, H, W, D)
        stacked = np.stack(all_probs, axis=0)
        mean_probs = stacked.mean(axis=0)    # (C, H, W, D)
        variance = stacked.var(axis=0)        # (C, H, W, D)

        # Predictive entropy: -Σ_c p_c · log(p_c)
        p_clipped = np.clip(mean_probs, 1e-8, 1.0)
        entropy = -(p_clipped * np.log(p_clipped)).sum(axis=0)  # (H, W, D)

        predicted_class = mean_probs.argmax(axis=0).astype(np.int32)  # (H, W, D)

        logger.info(
            "MC Dropout (%d samples): mean entropy=%.4f  max variance=%.4f",
            self.n_samples, float(entropy.mean()), float(variance.max()),
        )

        return UncertaintyResult(
            mean_probs=mean_probs,
            variance=variance,
            entropy=entropy,
            predicted_class=predicted_class,
            n_samples=self.n_samples,
        )


class GradCAM3D:
    """
    Gradient-weighted Class Activation Mapping for 3D volumetric networks.

    Registers forward and backward hooks on a target layer. Calling
    ``generate()`` runs a forward pass, backpropagates the class score,
    and returns the spatial saliency map via Grad-CAM.

    Parameters
    ----------
    model : nn.Module — the trained model.
    target_layer : nn.Module — layer whose activations are used for CAM
        (e.g. ``model.dec0`` for the final decoder block of UNet3D).

    Notes
    -----
    Call ``remove_hooks()`` after use to avoid memory leaks.

    Example
    -------
    >>> cam = GradCAM3D(model, target_layer=model.dec0)
    >>> saliency = cam.generate(x, target_class=3)   # Enhancing Tumour
    >>> cam.remove_hooks()
    """

    def __init__(self, model: nn.Module, target_layer: nn.Module) -> None:
        self.model = model
        self._features: Optional[torch.Tensor] = None
        self._gradients: Optional[torch.Tensor] = None

        self._fwd_handle = target_layer.register_forward_hook(self._save_features)
        self._bwd_handle = target_layer.register_full_backward_hook(self._save_gradients)

    # ------------------------------------------------------------------ hooks
    def _save_features(
        self, module: nn.Module, input: tuple, output: torch.Tensor
    ) -> None:
        self._features = output.detach()

    def _save_gradients(
        self, module: nn.Module, grad_input: tuple, grad_output: tuple
    ) -> None:
        self._gradients = grad_output[0].detach()

    # ------------------------------------------------------------------ API
    def generate(
        self,
        x: torch.Tensor,
        target_class: int,
        device: Optional[torch.device] = None,
    ) -> np.ndarray:
        """
        Generate a 3D Grad-CAM saliency map for the given class.

        Parameters
        ----------
        x            : (1, C, H, W, D) input tensor — single sample.
        target_class : int — class index to explain (0–3 for BraTS).
        device       : if None, inferred from model parameters.

        Returns
        -------
        cam : np.ndarray of shape (H, W, D), values normalised to [0, 1].
        """
        if x.shape[0] != 1:
            raise ValueError(
                f"GradCAM3D expects batch_size=1, got {x.shape[0]}."
            )

        if device is None:
            device = next(self.model.parameters()).device
        x = x.to(device)

        self.model.eval()
        self.model.zero_grad()
        self._features = None
        self._gradients = None

        # Forward pass with gradient tracking
        with torch.enable_grad():
            logits = self.model(x)
            if isinstance(logits, tuple):
                logits = logits[0]

            # Scalar score for the target class (sum over spatial dims)
            score = logits[:, target_class].sum()
            self.model.zero_grad()
            score.backward()

        if self._features is None or self._gradients is None:
            raise RuntimeError(
                "GradCAM hooks did not capture activations. "
                "Verify that target_layer is part of the forward graph."
            )

        # Global average pool of gradients → importance weights per channel
        # Shape: (1, C_feat, H', W', D') → weights (1, C_feat, 1, 1, 1)
        weights = self._gradients.mean(dim=(2, 3, 4), keepdim=True)

        # Weighted combination of feature maps, ReLU (keep only positive activation)
        # Shape: (1, H', W', D')
        cam = F.relu((weights * self._features).sum(dim=1, keepdim=True))

        # Upsample to input spatial resolution
        target_size = x.shape[2:]
        cam = F.interpolate(cam, size=target_size, mode="trilinear", align_corners=True)
        cam = cam.squeeze().cpu().numpy()   # (H, W, D)

        # Normalise to [0, 1]
        cam_min, cam_max = cam.min(), cam.max()
        if cam_max > cam_min:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            cam = np.zeros_like(cam)

        return cam

    def remove_hooks(self) -> None:
        """Remove registered hooks to prevent memory leaks."""
        self._fwd_handle.remove()
        self._bwd_handle.remove()
