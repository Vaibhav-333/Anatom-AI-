"""
Tests for src/reporting/pdf_report.py
"""

import pytest

from src.analytics.volumetrics import VolumetricAnalyzer, VolumetricResult
from src.analytics.longitudinal import LongitudinalTracker
from src.reporting.pdf_report import PDFReportBuilder, ReportConfig

import numpy as np

SPACING = (1.0, 1.0, 1.0)
SHAPE = (30, 30, 30)


def _make_seg():
    seg = np.zeros(SHAPE, dtype=np.int32)
    seg[5:15, 5:15, 5:15] = 2   # ED
    seg[8:12, 8:12, 8:12] = 1   # NCR
    seg[9:11, 9:11, 9:11] = 3   # ET
    return seg


def _make_result(sid="BraTS-001"):
    return VolumetricAnalyzer().compute(_make_seg(), SPACING, subject_id=sid)


def _make_long_report():
    seg1 = _make_seg()
    seg2 = np.zeros(SHAPE, dtype=np.int32)
    seg2[5:12, 5:12, 5:12] = 2
    seg2[8:10, 8:10, 8:10] = 1
    return LongitudinalTracker.from_segmentations(seg1, seg2, SPACING, 90.0)


class TestReportConfig:
    def test_defaults(self):
        cfg = ReportConfig()
        assert cfg.subject_id == "Unknown"
        assert cfg.institution == "Anatom AI Clinical Analytics"
        assert len(cfg.disclaimer) > 20

    def test_custom_values(self):
        cfg = ReportConfig(subject_id="BraTS-007", institution="MGH")
        assert cfg.subject_id == "BraTS-007"
        assert cfg.institution == "MGH"


class TestPDFReportBuilder:
    def test_build_returns_bytes(self):
        cfg = ReportConfig(subject_id="BraTS-001")
        builder = PDFReportBuilder(cfg)
        pdf = builder.build(_make_result())
        assert isinstance(pdf, bytes)

    def test_pdf_magic_header(self):
        """PDF files must start with %PDF."""
        pdf = PDFReportBuilder(ReportConfig()).build(_make_result())
        assert pdf[:4] == b"%PDF"

    def test_pdf_nonempty(self):
        pdf = PDFReportBuilder(ReportConfig()).build(_make_result())
        assert len(pdf) > 1024   # at least 1 KB

    def test_pdf_with_longitudinal_section(self):
        """Adding a longitudinal report should not raise and still produce valid PDF."""
        cfg = ReportConfig(subject_id="BraTS-001", scan_date="2026-04-13")
        builder = PDFReportBuilder(cfg)
        pdf = builder.build(_make_result(), longitudinal_report=_make_long_report())
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1024

    def test_pdf_without_longitudinal(self):
        """Report without longitudinal section is valid."""
        pdf = PDFReportBuilder(ReportConfig()).build(_make_result(), longitudinal_report=None)
        assert pdf[:4] == b"%PDF"

    def test_all_zero_seg_produces_valid_pdf(self):
        """All-background segmentation (zero tumour) must not crash."""
        seg = np.zeros(SHAPE, dtype=np.int32)
        result = VolumetricAnalyzer().compute(seg, SPACING, subject_id="empty")
        pdf = PDFReportBuilder(ReportConfig(subject_id="empty")).build(result)
        assert pdf[:4] == b"%PDF"

    def test_different_subject_ids_produce_different_pdfs(self):
        """Two reports with different subject IDs should not be byte-identical."""
        r1 = VolumetricAnalyzer().compute(_make_seg(), SPACING, "SubjectA")
        r2 = VolumetricAnalyzer().compute(_make_seg(), SPACING, "SubjectB")
        pdf1 = PDFReportBuilder(ReportConfig(subject_id="SubjectA")).build(r1)
        pdf2 = PDFReportBuilder(ReportConfig(subject_id="SubjectB")).build(r2)
        assert pdf1 != pdf2

    def test_report_config_institution_used(self):
        cfg = ReportConfig(institution="Mayo Clinic")
        builder = PDFReportBuilder(cfg)
        pdf = builder.build(_make_result())
        # Institution string should appear somewhere in the PDF binary
        assert b"Mayo Clinic" in pdf
