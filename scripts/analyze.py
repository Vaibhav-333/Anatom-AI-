"""
analyze.py -CLI entrypoint for Phase 3: Clinical Analytics.

Modes
-----
volume
    Compute tumor sub-region volumes (NCR, ED, ET, WT, TC) from a segmentation
    file (.npy or .nii.gz) and print/save a JSON report.

uncertainty
    Run Monte Carlo Dropout inference on a trained checkpoint to produce
    per-voxel uncertainty maps saved as .npy files.

gradcam
    Generate a 3D Grad-CAM saliency map for a specified target class and save
    it as a .npy file.

longitudinal
    Compare two segmentation files from different timepoints, compute volume
    deltas and growth rates, and classify response by RANO criteria.

Usage examples
--------------
# Volume report from a NumPy segmentation:
    python scripts/analyze.py volume \\
        --segmentation outputs/processed/BraTS-001/seg.npy \\
        --voxel-spacing 1.0 1.0 1.0 \\
        --subject-id BraTS-001 \\
        --output-dir outputs/analytics

# Uncertainty maps (requires a model checkpoint + input NIfTI/npy):
    python scripts/analyze.py uncertainty \\
        --checkpoint outputs/checkpoints/checkpoint_best.pt \\
        --input outputs/processed/BraTS-001/image.npy \\
        --n-samples 20 \\
        --output-dir outputs/analytics

# Grad-CAM for Enhancing Tumour (class 3):
    python scripts/analyze.py gradcam \\
        --checkpoint outputs/checkpoints/checkpoint_best.pt \\
        --input outputs/processed/BraTS-001/image.npy \\
        --target-class 3 \\
        --output-dir outputs/analytics

# Longitudinal RANO comparison:
    python scripts/analyze.py longitudinal \\
        --seg-t1 outputs/processed/BraTS-001/seg_t1.npy \\
        --seg-t2 outputs/processed/BraTS-001/seg_t2.npy \\
        --days-elapsed 90 \\
        --voxel-spacing 1.0 1.0 1.0 \\
        --subject-id BraTS-001 \\
        --output-dir outputs/analytics
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Anatom AI Phase 3 - Clinical Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("mode", choices=["volume", "uncertainty", "gradcam", "longitudinal"],
                        help="Analysis mode.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analytics"),
                        help="Directory to write output files.")
    parser.add_argument("--subject-id", type=str, default="unknown",
                        help="Subject identifier for output files and logs.")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING"])

    # --- Volume / Longitudinal ---
    seg_group = parser.add_argument_group("Volume / Longitudinal")
    seg_group.add_argument("--segmentation", type=Path, default=None,
                           help="Path to segmentation array (.npy or .nii.gz).")
    seg_group.add_argument("--seg-t1", type=Path, default=None,
                           help="Baseline segmentation for longitudinal mode.")
    seg_group.add_argument("--seg-t2", type=Path, default=None,
                           help="Follow-up segmentation for longitudinal mode.")
    seg_group.add_argument("--voxel-spacing", type=float, nargs=3,
                           default=[1.0, 1.0, 1.0], metavar=("SX", "SY", "SZ"),
                           help="Voxel spacing in mm (default 1.0 1.0 1.0).")
    seg_group.add_argument("--days-elapsed", type=float, default=None,
                           help="Days between T1 and T2 scans (longitudinal mode).")

    # --- Model-based modes ---
    model_group = parser.add_argument_group("Uncertainty / GradCAM")
    model_group.add_argument("--checkpoint", type=Path, default=None,
                             help="Path to trained .pt checkpoint.")
    model_group.add_argument("--input", type=Path, default=None,
                             help="Path to model input array (.npy), shape (4, H, W, D).")
    model_group.add_argument("--device", type=str, default="auto",
                             choices=["auto", "cuda", "cpu", "mps"])

    # Uncertainty specific
    parser.add_argument("--n-samples", type=int, default=20,
                        help="MC Dropout samples (uncertainty mode, default 20).")

    # GradCAM specific
    parser.add_argument("--target-class", type=int, default=3,
                        help="Class index for Grad-CAM (0=BG,1=NCR,2=ED,3=ET; default 3).")

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_array(path: Path) -> np.ndarray:
    """Load a .npy file or raise a clear error."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix == ".npy":
        return np.load(path)
    # Minimal NIfTI support via nibabel
    try:
        import nibabel as nib
        return nib.load(str(path)).get_fdata(dtype=np.float32)
    except ImportError:
        raise ValueError(f"nibabel required to load {path}. Install it or use .npy files.")


def _load_model(checkpoint: Path, device: str):
    """Load a UNet3D from a checkpoint file."""
    import torch
    from src.training.trainer import Trainer, TrainingConfig

    ckpt = torch.load(checkpoint, map_location="cpu")
    cfg_dict = ckpt.get("config", {})
    config = TrainingConfig(**cfg_dict)
    trainer = Trainer(config)
    trainer.model.load_state_dict(ckpt["model_state"])

    dev = _resolve_device(device)
    trainer.model.to(dev)
    return trainer.model, dev


def _resolve_device(device_str: str):
    import torch
    if device_str == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    return torch.device(device_str)


def _save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved: {path}")


def _save_npy(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, arr)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Mode handlers
# ---------------------------------------------------------------------------

def run_volume(args: argparse.Namespace) -> None:
    from src.analytics.volumetrics import VolumetricAnalyzer

    if args.segmentation is None:
        print("Error: --segmentation is required for volume mode.")
        sys.exit(1)

    seg = _load_array(args.segmentation).astype(np.int32)
    analyzer = VolumetricAnalyzer()
    result = analyzer.compute(seg, tuple(args.voxel_spacing), subject_id=args.subject_id)

    print(f"\n=== Volumetric Report -{result.subject_id} ===")
    print(f"  Voxel volume : {result.voxel_volume_mm3:.3f} mm3")
    for cls_name, vol in result.volumes_mm3.items():
        print(f"  {cls_name:12s}: {vol:12.1f} mm3")
    print(f"  --- BraTS regions ---")
    print(f"  WT           : {result.wt_mm3:12.1f} mm3")
    print(f"  TC           : {result.tc_mm3:12.1f} mm3")
    print(f"  ET           : {result.et_mm3:12.1f} mm3")

    out_path = args.output_dir / f"{args.subject_id}_volumes.json"
    _save_json(result.to_dict(), out_path)


def run_uncertainty(args: argparse.Namespace) -> None:
    import torch
    from src.analytics.explainability import UncertaintyEstimator

    if args.checkpoint is None or args.input is None:
        print("Error: --checkpoint and --input are required for uncertainty mode.")
        sys.exit(1)

    raw = _load_array(args.input)
    if raw.ndim == 3:
        raw = raw[np.newaxis]   # add channel dim if needed
    x = torch.from_numpy(raw).float().unsqueeze(0)  # (1, C, H, W, D)

    model, device = _load_model(args.checkpoint, args.device)
    estimator = UncertaintyEstimator(n_samples=args.n_samples)
    result = estimator.estimate(model, x, device=device)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _save_npy(result.mean_probs, args.output_dir / f"{args.subject_id}_mean_probs.npy")
    _save_npy(result.variance,   args.output_dir / f"{args.subject_id}_variance.npy")
    _save_npy(result.entropy,    args.output_dir / f"{args.subject_id}_entropy.npy")
    _save_npy(result.predicted_class.astype(np.uint8),
              args.output_dir / f"{args.subject_id}_prediction.npy")

    print(f"\nMC Dropout ({args.n_samples} samples)")
    print(f"  Mean entropy : {result.entropy.mean():.4f} nats")
    print(f"  Max variance : {result.variance.max():.4f}")


def run_gradcam(args: argparse.Namespace) -> None:
    import torch
    from src.analytics.explainability import GradCAM3D
    CLASS_NAMES = {0: "Background", 1: "NCR", 2: "ED", 3: "ET"}

    if args.checkpoint is None or args.input is None:
        print("Error: --checkpoint and --input are required for gradcam mode.")
        sys.exit(1)

    raw = _load_array(args.input)
    if raw.ndim == 3:
        raw = raw[np.newaxis]
    x = torch.from_numpy(raw).float().unsqueeze(0)  # (1, C, H, W, D)

    model, device = _load_model(args.checkpoint, args.device)
    cam = GradCAM3D(model, target_layer=model.dec0)
    saliency = cam.generate(x, target_class=args.target_class, device=device)
    cam.remove_hooks()

    cls_name = CLASS_NAMES.get(args.target_class, str(args.target_class))
    out_name = f"{args.subject_id}_gradcam_class{args.target_class}_{cls_name}.npy"
    _save_npy(saliency, args.output_dir / out_name)
    print(f"\nGrad-CAM for class {args.target_class} ({cls_name})")
    print(f"  Saliency shape : {saliency.shape}")
    print(f"  Max activation : {saliency.max():.4f}")


def run_longitudinal(args: argparse.Namespace) -> None:
    from src.analytics.longitudinal import LongitudinalTracker

    for flag, name in [(args.seg_t1, "--seg-t1"), (args.seg_t2, "--seg-t2")]:
        if flag is None:
            print(f"Error: {name} is required for longitudinal mode.")
            sys.exit(1)
    if args.days_elapsed is None:
        print("Error: --days-elapsed is required for longitudinal mode.")
        sys.exit(1)

    seg_t1 = _load_array(args.seg_t1).astype(np.int32)
    seg_t2 = _load_array(args.seg_t2).astype(np.int32)

    report = LongitudinalTracker.from_segmentations(
        seg_t1, seg_t2,
        voxel_spacing=tuple(args.voxel_spacing),
        days_elapsed=args.days_elapsed,
        subject_id=args.subject_id,
    )

    print(f"\n=== Longitudinal Report - {report.subject_id} ===")
    print(f"  Interval     : {report.days_elapsed:.0f} days")
    print(f"  RANO Category: {report.rano_category}")
    print(f"  WT change    : {report.rano_pct_change:+.1f}%")
    print(f"\n  Region    T1 (mm3)    T2 (mm3)      D (mm3)   Rate (mm3/day)")
    for region in ("WT", "TC", "ET"):
        t1 = report.volumes_t1[region]
        t2 = report.volumes_t2[region]
        delta = report.delta_mm3[region]
        rate = report.rate_mm3_per_day[region]
        print(f"  {region:6s}  {t1:10.1f}  {t2:10.1f}  {delta:+10.1f}  {rate:+12.3f}")

    out_path = args.output_dir / f"{args.subject_id}_longitudinal.json"
    _save_json(report.to_dict(), out_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    dispatch = {
        "volume": run_volume,
        "uncertainty": run_uncertainty,
        "gradcam": run_gradcam,
        "longitudinal": run_longitudinal,
    }
    dispatch[args.mode](args)


if __name__ == "__main__":
    main()
