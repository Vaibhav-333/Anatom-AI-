"""
blocks.py — Reusable 3D convolutional building blocks for the U-Net.

All blocks use:
  - GroupNorm instead of BatchNorm (GroupNorm works correctly with batch_size=1,
    which is the norm in 3D medical imaging due to memory constraints).
  - LeakyReLU (negative_slope=0.01) — more stable than ReLU for deep networks
    and preserves gradient flow through the decoder's upsampling path.
  - Residual connections in DoubleConv (optional) — accelerates convergence
    and provides gradient highway in very deep encoders.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class DoubleConv3D(nn.Module):
    """
    Two consecutive 3D convolutions with normalisation and activation.

    Structure:
        Conv3D(3×3×3) → GroupNorm → LeakyReLU →
        Conv3D(3×3×3) → GroupNorm → LeakyReLU
        [+ residual projection if in_channels ≠ out_channels]

    Parameters
    ----------
    in_channels  : Input feature map channels.
    out_channels : Output feature map channels.
    groups       : GroupNorm number of groups. Must divide out_channels evenly.
    residual     : If True, add a learnable residual shortcut.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        groups: int = 8,
        residual: bool = True,
    ) -> None:
        super().__init__()
        # Clamp groups so GroupNorm never receives more groups than channels
        groups = min(groups, out_channels)
        while out_channels % groups != 0 and groups > 1:
            groups -= 1

        self.conv = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(groups, out_channels),
            nn.LeakyReLU(0.01, inplace=True),
            nn.Conv3d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(groups, out_channels),
            nn.LeakyReLU(0.01, inplace=True),
        )

        self.residual = residual
        if residual and in_channels != out_channels:
            self.skip = nn.Conv3d(in_channels, out_channels, kernel_size=1, bias=False)
        else:
            self.skip = None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv(x)
        if self.residual:
            shortcut = self.skip(x) if self.skip is not None else x
            out = out + shortcut
        return out


class DownBlock(nn.Module):
    """
    Encoder block: MaxPool3D (stride 2) followed by DoubleConv3D.

    Halves spatial dimensions while doubling channels.
    """

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.pool = nn.MaxPool3d(kernel_size=2, stride=2)
        self.conv = DoubleConv3D(in_channels, out_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(self.pool(x))


class UpBlock(nn.Module):
    """
    Decoder block: trilinear upsampling + skip connection concatenation + DoubleConv3D.

    Uses trilinear interpolation (not transposed conv) to avoid checkerboard artefacts —
    a known issue in medical image segmentation models.

    Parameters
    ----------
    in_channels  : Channels from the upsampled path.
    skip_channels: Channels from the encoder skip connection.
    out_channels : Channels produced by the block.
    """

    def __init__(self, in_channels: int, skip_channels: int, out_channels: int) -> None:
        super().__init__()
        self.up = nn.Upsample(scale_factor=2, mode="trilinear", align_corners=True)
        self.conv = DoubleConv3D(in_channels + skip_channels, out_channels)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        # Pad if spatial dims don't match exactly (odd input sizes)
        diff = [skip.shape[i + 2] - x.shape[i + 2] for i in range(3)]
        x = F.pad(x, [0, diff[2], 0, diff[1], 0, diff[0]])
        x = torch.cat([skip, x], dim=1)
        return self.conv(x)


class OutputHead(nn.Module):
    """
    1×1×1 convolution that maps feature maps to class logits.

    Used at the final decoder level AND at each deep supervision output.
    No activation — raw logits are returned (compatible with CrossEntropyLoss
    and Softmax for inference).
    """

    def __init__(self, in_channels: int, num_classes: int) -> None:
        super().__init__()
        self.conv = nn.Conv3d(in_channels, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


class SpatialDropout3D(nn.Module):
    """
    Drops entire feature maps (channels) with probability p.

    More effective than standard Dropout in convolutional networks because
    adjacent voxels are highly correlated — dropping a full channel is a
    stronger regulariser than dropping individual voxels.
    """

    def __init__(self, p: float = 0.1) -> None:
        super().__init__()
        self.drop = nn.Dropout3d(p=p)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.drop(x)
