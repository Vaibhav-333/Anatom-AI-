"""
src/reporting — Phase 5: Medical Reporting

Modules
-------
pdf_report  : Generate PDF clinical reports via ReportLab.
dicom_sr    : Write DICOM Structured Reports (SR) via pydicom.
"""

from .pdf_report import PDFReportBuilder, ReportConfig
from .dicom_sr import DicomSRWriter, create_volume_sr

__all__ = ["PDFReportBuilder", "ReportConfig", "DicomSRWriter", "create_volume_sr"]
