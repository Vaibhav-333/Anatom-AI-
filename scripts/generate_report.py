"""
generate_report.py — CLI for Phase 5: PDF and DICOM SR report generation.

Usage examples
--------------
# PDF report from a segmentation:
    python scripts/generate_report.py pdf \\
        --segmentation outputs/processed/BraTS-001/seg.npy \\
        --voxel-spacing 1.0 1.0 1.0 \\
        --subject-id BraTS-001 \\
        --output outputs/reports/BraTS-001_report.pdf

# DICOM SR from a segmentation + longitudinal comparison:
    python scripts/generate_report.py dicom \\
        --segmentation outputs/processed/BraTS-001/seg_t2.npy \\
        --seg-t1 outputs/processed/BraTS-001/seg_t1.npy \\
        --days-elapsed 90 \\
        --subject-id BraTS-001 \\
        --output outputs/reports/BraTS-001.dcm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Anatom AI Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("mode", choices=["pdf", "dicom"],
                        help="Output format: 'pdf' or 'dicom'.")
    parser.add_argument("--segmentation", type=Path, required=True,
                        help="Primary (T2 / follow-up) segmentation (.npy or .nii.gz).")
    parser.add_argument("--seg-t1", type=Path, default=None,
                        help="Baseline segmentation for longitudinal section.")
    parser.add_argument("--days-elapsed", type=float, default=None,
                        help="Days between T1 and primary scan.")
    parser.add_argument("--voxel-spacing", type=float, nargs=3,
                        default=[1.0, 1.0, 1.0], metavar=("SX", "SY", "SZ"))
    parser.add_argument("--subject-id", default="unknown")
    parser.add_argument("--scan-date", default="", help="Scan date string (YYYY-MM-DD).")
    parser.add_argument("--institution", default="Anatom AI Clinical Analytics")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output file path. Defaults to <subject_id>_report.pdf/.dcm.")
    return parser.parse_args()


def _load(path: Path) -> np.ndarray:
    if not path.exists():
        print(f"Error: file not found — {path}", file=sys.stderr)
        sys.exit(1)
    if path.suffix == ".npy":
        return np.load(path)
    try:
        import nibabel as nib
        return nib.load(str(path)).get_fdata(dtype=np.float32)
    except ImportError:
        print("nibabel required for .nii.gz files.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    args = parse_args()

    from src.analytics.volumetrics import VolumetricAnalyzer
    from src.analytics.longitudinal import LongitudinalTracker

    seg = _load(args.segmentation).astype(np.int32)
    spacing = tuple(args.voxel_spacing)

    analyzer = VolumetricAnalyzer()
    result = analyzer.compute(seg, spacing, subject_id=args.subject_id)

    long_report = None
    if args.seg_t1 is not None and args.days_elapsed is not None:
        seg_t1 = _load(args.seg_t1).astype(np.int32)
        long_report = LongitudinalTracker.from_segmentations(
            seg_t1, seg, spacing, args.days_elapsed, subject_id=args.subject_id
        )

    if args.mode == "pdf":
        from src.reporting.pdf_report import PDFReportBuilder, ReportConfig
        from datetime import date

        cfg = ReportConfig(
            subject_id=args.subject_id,
            scan_date=args.scan_date or str(date.today()),
            institution=args.institution,
        )
        pdf_bytes = PDFReportBuilder(cfg).build(result, longitudinal_report=long_report)

        out = args.output or Path(f"{args.subject_id}_report.pdf")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf_bytes)
        print(f"PDF saved: {out}  ({len(pdf_bytes):,} bytes)")

        # Print summary
        print(f"\n=== Volume Summary — {args.subject_id} ===")
        print(f"  WT : {result.wt_mm3:,.1f} mm3")
        print(f"  TC : {result.tc_mm3:,.1f} mm3")
        print(f"  ET : {result.et_mm3:,.1f} mm3")
        if long_report:
            print(f"  RANO: {long_report.rano_category}  ({long_report.rano_pct_change:+.1f}% WT)")

    elif args.mode == "dicom":
        from src.reporting.dicom_sr import DicomSRWriter
        import io

        ds = DicomSRWriter().build(result, longitudinal_report=long_report)
        out = args.output or Path(f"{args.subject_id}_report.dcm")
        out.parent.mkdir(parents=True, exist_ok=True)
        ds.save_as(str(out), enforce_file_format=True)
        print(f"DICOM SR saved: {out}")
        print(f"  SOPInstanceUID : {ds.SOPInstanceUID}")
        print(f"  ContentDate    : {ds.ContentDate}")


if __name__ == "__main__":
    main()
