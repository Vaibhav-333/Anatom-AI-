"""
run_preprocessing.py — CLI entrypoint for the Anatom AI imaging pipeline.

Usage
-----
# Process a single BraTS subject:
    python scripts/run_preprocessing.py \\
        --subject-dir data/sample/BraTS-001 \\
        --output-dir  outputs/processed

# Process a single subject with augmentation:
    python scripts/run_preprocessing.py \\
        --subject-dir data/sample/BraTS-001 \\
        --output-dir  outputs/augmented \\
        --augment

# QC check only (no processing, no output files written):
    python scripts/run_preprocessing.py \\
        --subject-dir data/sample/BraTS-001 \\
        --qc-only

# Batch process an entire BraTS dataset directory:
    python scripts/run_preprocessing.py \\
        --brats-root data/BraTS2024 \\
        --output-dir outputs/processed \\
        --batch

# Save a QC visualisation figure alongside outputs:
    python scripts/run_preprocessing.py \\
        --subject-dir data/sample/BraTS-001 \\
        --output-dir  outputs/processed \\
        --visualize

# Use a custom config file:
    python scripts/run_preprocessing.py \\
        --subject-dir data/sample/BraTS-001 \\
        --output-dir  outputs/processed \\
        --config      config/my_custom.yaml
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running from project root without installing as a package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.imaging.pipeline import PreprocessingPipeline
from src.utils.qc_validator import QCValidator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Anatom AI Phase 1 — MRI Preprocessing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--subject-dir",
        type=Path,
        metavar="PATH",
        help="Path to a single BraTS subject directory.",
    )
    input_group.add_argument(
        "--brats-root",
        type=Path,
        metavar="PATH",
        help="Root of a BraTS dataset (batch mode — processes all subdirectories).",
    )

    # Output
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        metavar="PATH",
        help="Directory where processed files and provenance logs are saved.",
    )

    # Config
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent.parent / "config" / "preprocessing.yaml",
        metavar="YAML",
        help="Path to preprocessing.yaml (default: config/preprocessing.yaml).",
    )

    # Modes
    parser.add_argument(
        "--augment",
        action="store_true",
        help="Apply data augmentation after preprocessing (training mode).",
    )
    parser.add_argument(
        "--qc-only",
        action="store_true",
        help="Run pre-pipeline QC checks only; do not process or save outputs.",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch mode: process all subject subdirectories under --brats-root.",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Save a multi-planar QC figure (PNG) alongside each processed subject.",
    )
    parser.add_argument(
        "--no-seg",
        action="store_true",
        help="Inference mode — do not require a segmentation label file.",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )

    return parser.parse_args()


def run_qc_only(subject_dir: Path) -> None:
    """Load and validate a subject without running any processing."""
    from src.imaging.loader import NIfTILoader
    print(f"\n--- QC Check: {subject_dir.name} ---")

    loader = NIfTILoader(require_seg=False)
    subject = loader.load(subject_dir)

    validator = QCValidator()
    report = validator.validate_pre(subject)

    print(f"Subject ID  : {report.subject_id}")
    print(f"QC Passed   : {report.passed}")

    if report.failures:
        print("FAILURES:")
        for f in report.failures:
            print(f"  [FAIL] {f}")

    if report.warnings:
        print("WARNINGS:")
        for w in report.warnings:
            print(f"  [WARN] {w}")

    print("Stats:")
    for k, v in report.stats.items():
        print(f"  {k}: {v}")

    if not report.passed:
        sys.exit(1)


def run_single(
    subject_dir: Path,
    output_dir: Path,
    pipeline: PreprocessingPipeline,
    augment: bool,
    visualize: bool,
) -> None:
    """Process a single subject."""
    print(f"\n--- Processing: {subject_dir.name} ---")
    subject = pipeline.run(subject_dir, output_dir / subject_dir.name, apply_augmentation=augment)

    if visualize:
        from src.utils.visualizer import SliceVisualizer
        viz = SliceVisualizer()
        fig_path = output_dir / subject_dir.name / "qc_preview.png"
        viz.save_qc_figure(subject, fig_path)
        print(f"QC figure saved: {fig_path}")

    print(f"Done. Outputs written to: {output_dir / subject_dir.name}")


def run_batch(
    brats_root: Path,
    output_dir: Path,
    pipeline: PreprocessingPipeline,
    augment: bool,
    visualize: bool,
) -> None:
    """Process all BraTS subjects under brats_root."""
    subject_dirs = sorted([d for d in brats_root.iterdir() if d.is_dir()])
    print(f"\nBatch mode: {len(subject_dirs)} subjects found under {brats_root}")

    results = {}
    for subject_dir in subject_dirs:
        try:
            run_single(subject_dir, output_dir, pipeline, augment, visualize)
            results[subject_dir.name] = "ok"
        except Exception as exc:
            results[subject_dir.name] = f"FAILED: {exc}"
            logging.error("Subject '%s' failed: %s", subject_dir.name, exc)

    # Summary
    n_ok = sum(1 for v in results.values() if v == "ok")
    print(f"\nBatch complete: {n_ok}/{len(results)} subjects succeeded.")
    if n_ok < len(results):
        print("Failed subjects:")
        for sid, status in results.items():
            if status != "ok":
                print(f"  {sid}: {status}")
        sys.exit(1)


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # QC-only mode
    if args.qc_only:
        if args.subject_dir is None:
            print("Error: --qc-only requires --subject-dir.")
            sys.exit(1)
        run_qc_only(args.subject_dir)
        return

    # Build pipeline
    if not args.config.exists():
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    pipeline = PreprocessingPipeline.from_yaml(
        args.config,
        require_seg=not args.no_seg,
    )

    if args.batch:
        if args.brats_root is None:
            print("Error: --batch requires --brats-root.")
            sys.exit(1)
        run_batch(args.brats_root, args.output_dir, pipeline, args.augment, args.visualize)
    else:
        run_single(args.subject_dir, args.output_dir, pipeline, args.augment, args.visualize)


if __name__ == "__main__":
    main()
