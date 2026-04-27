"""
Tests for src/reporting/dicom_sr.py
"""

import io
import pytest
import numpy as np
import pydicom
from pydicom.dataset import FileDataset

from src.analytics.volumetrics import VolumetricAnalyzer, VolumetricResult
from src.analytics.longitudinal import LongitudinalTracker
from src.reporting.dicom_sr import DicomSRWriter, create_volume_sr

SPACING = (1.0, 1.0, 1.0)
SHAPE = (30, 30, 30)
_COMPREHENSIVE_SR_SOP = "1.2.840.10008.5.1.4.1.1.88.33"


def _make_seg():
    seg = np.zeros(SHAPE, dtype=np.int32)
    seg[5:15, 5:15, 5:15] = 2
    seg[8:12, 8:12, 8:12] = 1
    seg[9:11, 9:11, 9:11] = 3
    return seg


def _make_result(sid="BraTS-001"):
    return VolumetricAnalyzer().compute(_make_seg(), SPACING, subject_id=sid)


def _make_long_report():
    seg1 = _make_seg()
    seg2 = np.zeros(SHAPE, dtype=np.int32)
    seg2[5:10, 5:10, 5:10] = 2
    return LongitudinalTracker.from_segmentations(seg1, seg2, SPACING, 90.0)


class TestDicomSRWriter:
    def test_returns_file_dataset(self):
        ds = DicomSRWriter().build(_make_result())
        assert isinstance(ds, FileDataset)

    def test_sop_class_is_comprehensive_sr(self):
        ds = DicomSRWriter().build(_make_result())
        assert ds.SOPClassUID == _COMPREHENSIVE_SR_SOP

    def test_modality_is_sr(self):
        ds = DicomSRWriter().build(_make_result())
        assert ds.Modality == "SR"

    def test_patient_id_matches_subject_id(self):
        ds = DicomSRWriter().build(_make_result("BraTS-007"))
        assert ds.PatientID == "BraTS-007"

    def test_completion_flag(self):
        ds = DicomSRWriter().build(_make_result())
        assert ds.CompletionFlag == "COMPLETE"

    def test_verification_flag(self):
        ds = DicomSRWriter().build(_make_result())
        assert ds.VerificationFlag == "UNVERIFIED"

    def test_content_sequence_present(self):
        ds = DicomSRWriter().build(_make_result())
        assert hasattr(ds, "ContentSequence")
        assert len(ds.ContentSequence) >= 3   # title + patient + volumes

    def test_with_longitudinal_report_adds_rano_container(self):
        ds = DicomSRWriter().build(_make_result(), longitudinal_report=_make_long_report())
        # Should have 4 content items: title + patient + volumes + RANO
        assert len(ds.ContentSequence) >= 4

    def test_study_instance_uid_is_set(self):
        ds = DicomSRWriter().build(_make_result())
        assert ds.StudyInstanceUID != ""

    def test_unique_sop_instance_uids_per_call(self):
        """Each build() call must produce a unique SOP Instance UID."""
        ds1 = DicomSRWriter().build(_make_result())
        ds2 = DicomSRWriter().build(_make_result())
        assert ds1.SOPInstanceUID != ds2.SOPInstanceUID

    def test_can_be_saved_and_reloaded(self):
        """Dataset must survive a round-trip through pydicom save/load."""
        ds = DicomSRWriter().build(_make_result("BraTS-042"))
        buf = io.BytesIO()
        ds.save_as(buf, enforce_file_format=True)
        buf.seek(0)
        reloaded = pydicom.dcmread(buf)
        assert reloaded.PatientID == "BraTS-042"
        assert reloaded.Modality == "SR"

    def test_custom_patient_name(self):
        ds = DicomSRWriter().build(_make_result(), patient_name="Doe^John")
        assert "Doe" in str(ds.PatientName)

    def test_content_description_contains_subject_id(self):
        ds = DicomSRWriter().build(_make_result("BraTS-999"))
        assert "BraTS-999" in ds.ContentDescription


class TestCreateVolumeSR:
    def test_convenience_wrapper_returns_dataset(self):
        ds = create_volume_sr(_make_result())
        assert isinstance(ds, FileDataset)

    def test_with_longitudinal(self):
        ds = create_volume_sr(_make_result(), _make_long_report())
        assert isinstance(ds, FileDataset)
        assert len(ds.ContentSequence) >= 4
