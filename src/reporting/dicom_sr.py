"""
dicom_sr.py — DICOM Structured Report (SR) writer for Anatom AI.

Produces a minimal but standards-compliant DICOM SR document encoding
tumour volumetric measurements so they can be ingested by PACS/RIS systems.

SOP Class : 1.2.840.10008.5.1.4.1.1.88.33 — Comprehensive SR Storage
Transfer Syntax: Explicit VR Little Endian

Document structure
------------------
CONTAINER (Root)
  └─ TEXT (Report Title)
  └─ CONTAINER (Patient Info)
       ├─ TEXT (Subject ID)
       └─ TEXT (Scan Date)
  └─ CONTAINER (Volumetric Measurements)
       ├─ NUM  (WT volume, mm³)
       ├─ NUM  (TC volume, mm³)
       ├─ NUM  (ET volume, mm³)
       ├─ NUM  (NCR volume, mm³)
       ├─ NUM  (ED volume, mm³)
       └─ TEXT (Voxel spacing)
  └─ CONTAINER (RANO Assessment) — optional
       ├─ TEXT (RANO category)
       ├─ NUM  (WT % change)
       └─ NUM  (Interval, days)

Usage
-----
    from src.reporting.dicom_sr import DicomSRWriter, create_volume_sr
    from src.analytics.volumetrics import VolumetricResult

    ds = create_volume_sr(vol_result)           # convenience wrapper
    ds.save_as("report.dcm", write_like_original=False)

    # or directly:
    writer = DicomSRWriter()
    ds = writer.build(vol_result, longitudinal_report=long_report)
"""

from __future__ import annotations

import datetime
import random
import string
from typing import Optional

import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.sequence import Sequence
from pydicom.uid import (
    ExplicitVRLittleEndian,
    generate_uid,
)

from src.analytics.volumetrics import VolumetricResult
from src.analytics.longitudinal import LongitudinalReport

# DICOM SOP Class UIDs
_COMPREHENSIVE_SR_SOP_CLASS = "1.2.840.10008.5.1.4.1.1.88.33"
_ANATOMAI_UID_ROOT = "1.2.826.0.1.3680043.9.7777"   # fictional root UID

# Concept Name Code Sequences (SNOMED / UCUM approximations)
def _code_seq(value: str, scheme: str, meaning: str) -> Sequence:
    cs = Dataset()
    cs.CodeValue = value[:16]          # CS VR max length = 16
    cs.CodingSchemeDesignator = scheme[:16]   # SH VR max length = 16
    cs.CodeMeaning = meaning
    return Sequence([cs])


def _num_item(name: str, value: float, unit: str = "mm3") -> Dataset:
    """Build a DICOM SR NUM content item."""
    item = Dataset()
    item.RelationshipType = "CONTAINS"
    item.ValueType = "NUM"
    item.ConceptNameCodeSequence = _code_seq("NEURM_" + name.upper(), "99NEURM", name)

    mv = Dataset()
    mv.NumericValue = pydicom.valuerep.DSfloat(round(value, 3))
    mv.MeasurementUnitsCodeSequence = _code_seq(unit, "UCUM", unit)
    item.MeasuredValueSequence = Sequence([mv])
    return item


def _text_item(name: str, value: str) -> Dataset:
    """Build a DICOM SR TEXT content item."""
    item = Dataset()
    item.RelationshipType = "CONTAINS"
    item.ValueType = "TEXT"
    item.ConceptNameCodeSequence = _code_seq("NEURM_" + name.upper(), "99NEURM", name)
    item.TextValue = str(value)
    return item


def _container(name: str, children: list[Dataset], relationship: str = "CONTAINS") -> Dataset:
    """Build a DICOM SR CONTAINER content item."""
    cont = Dataset()
    cont.RelationshipType = relationship
    cont.ValueType = "CONTAINER"
    cont.ConceptNameCodeSequence = _code_seq("NEURM_" + name.upper(), "99NEURM", name)
    cont.ContinuityOfContent = "SEPARATE"
    cont.ContentSequence = Sequence(children)
    return cont


class DicomSRWriter:
    """
    Build a DICOM Structured Report dataset from Anatom AI analytics results.

    Parameters
    ----------
    uid_root : str — UID root for generated instance UIDs.
    """

    def __init__(self, uid_root: str = _ANATOMAI_UID_ROOT) -> None:
        self.uid_root = uid_root

    def build(
        self,
        result: VolumetricResult,
        longitudinal_report: Optional[LongitudinalReport] = None,
        patient_name: str = "Anonymous^Patient",
        patient_id: Optional[str] = None,
    ) -> FileDataset:
        """
        Assemble and return a DICOM SR FileDataset.

        Parameters
        ----------
        result             : VolumetricResult from the target scan.
        longitudinal_report: optional LongitudinalReport for RANO section.
        patient_name       : DICOM PatientName tag value.
        patient_id         : DICOM PatientID; defaults to subject_id from result.

        Returns
        -------
        pydicom.dataset.FileDataset — ready to save_as() or transmit to PACS.
        """
        now = datetime.datetime.now()
        patient_id = patient_id or result.subject_id

        # --- File Meta ---
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = _COMPREHENSIVE_SR_SOP_CLASS
        file_meta.MediaStorageSOPInstanceUID = generate_uid(prefix=self.uid_root + ".")
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

        ds = FileDataset(
            filename_or_obj=None,
            dataset={},
            file_meta=file_meta,
            is_implicit_VR=False,
            is_little_endian=True,
            preamble=b"\x00" * 128,
        )

        # --- Patient Module ---
        ds.PatientName = patient_name
        ds.PatientID = patient_id
        ds.PatientBirthDate = ""
        ds.PatientSex = ""

        # --- General Study Module ---
        ds.StudyInstanceUID = generate_uid(prefix=self.uid_root + ".")
        ds.StudyDate = now.strftime("%Y%m%d")
        ds.StudyTime = now.strftime("%H%M%S")
        ds.AccessionNumber = ""
        ds.StudyID = result.subject_id
        ds.ReferringPhysicianName = ""

        # --- SR Document Series Module ---
        ds.SeriesInstanceUID = generate_uid(prefix=self.uid_root + ".")
        ds.SeriesNumber = "1"
        ds.Modality = "SR"

        # --- General Equipment Module ---
        ds.Manufacturer = "Anatom AI"
        ds.ManufacturerModelName = "Anatom AI v1.0"
        ds.SoftwareVersions = "Phase5"

        # --- SOP Common Module ---
        ds.SOPClassUID = _COMPREHENSIVE_SR_SOP_CLASS
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.InstanceNumber = "1"
        ds.ContentDate = now.strftime("%Y%m%d")
        ds.ContentTime = now.strftime("%H%M%S")

        # --- SR Document General Module ---
        ds.CompletionFlag = "COMPLETE"
        ds.VerificationFlag = "UNVERIFIED"
        ds.ContentLabel = "NEUROMAP_VOL"
        ds.ContentDescription = f"Tumour Volume Report — {result.subject_id}"
        ds.PreliminaryFlag = "PRELIMINARY"

        # --- Document Content Root ---
        root_children = [
            _text_item("Report Title", "Anatom AI Tumour Volumetric Analysis Report"),
            self._patient_container(result),
            self._volume_container(result),
        ]
        if longitudinal_report is not None:
            root_children.append(self._rano_container(longitudinal_report))

        root = Dataset()
        root.ValueType = "CONTAINER"
        root.ContinuityOfContent = "SEPARATE"
        root.ConceptNameCodeSequence = _code_seq("NEURM_ROOT", "99NEURM", "Anatom AI Report")
        root.ContentSequence = Sequence(root_children)

        ds.ValueType = root.ValueType
        ds.ContinuityOfContent = root.ContinuityOfContent
        ds.ConceptNameCodeSequence = root.ConceptNameCodeSequence
        ds.ContentSequence = root.ContentSequence

        return ds

    @staticmethod
    def _patient_container(result: VolumetricResult) -> Dataset:
        return _container("Patient Info", [
            _text_item("Subject ID", result.subject_id),
            _text_item("Analysis System", "Anatom AI v1.0"),
        ])

    @staticmethod
    def _volume_container(result: VolumetricResult) -> Dataset:
        items = [
            _num_item("WT Volume", result.wt_mm3, "mm3"),
            _num_item("TC Volume", result.tc_mm3, "mm3"),
            _num_item("ET Volume", result.et_mm3, "mm3"),
            _num_item("NCR Volume", result.volumes_mm3.get("NCR", 0.0), "mm3"),
            _num_item("ED Volume",  result.volumes_mm3.get("ED", 0.0), "mm3"),
            _text_item("Voxel Volume mm3", f"{result.voxel_volume_mm3:.4f}"),
        ]
        return _container("Volumetric Measurements", items)

    @staticmethod
    def _rano_container(report: LongitudinalReport) -> Dataset:
        items = [
            _text_item("RANO Category", report.rano_category),
            _num_item("WT Pct Change", report.rano_pct_change, "%"),
            _num_item("Interval Days", report.days_elapsed, "d"),
            _num_item("WT Delta mm3", report.delta_mm3.get("WT", 0.0), "mm3"),
        ]
        return _container("RANO Assessment", items)


def create_volume_sr(
    result: VolumetricResult,
    longitudinal_report: Optional[LongitudinalReport] = None,
) -> FileDataset:
    """
    Convenience function: build a DICOM SR with default settings.

    Returns pydicom FileDataset ready for save_as() or DIMSE C-STORE.
    """
    return DicomSRWriter().build(result, longitudinal_report)
