"""
schemas.py — Pydantic request/response models for the Anatom AI REST API.

All numpy arrays are transferred as base64-encoded bytes with explicit dtype
and shape metadata so any HTTP client can reconstruct them without side-channels.
"""

from __future__ import annotations

import base64
from typing import Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Shared array encoding helpers
# ---------------------------------------------------------------------------

def array_to_b64(arr: np.ndarray) -> str:
    """Encode a numpy array to a base64 string."""
    return base64.b64encode(arr.tobytes()).decode("ascii")


def b64_to_array(b64: str, dtype: str, shape: List[int]) -> np.ndarray:
    """Decode a base64 string back to a numpy array."""
    raw = base64.b64decode(b64.encode("ascii"))
    return np.frombuffer(raw, dtype=np.dtype(dtype)).reshape(shape)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class ArrayPayload(BaseModel):
    """A numpy array serialised as base64."""
    data_b64: str = Field(..., description="Base64-encoded raw bytes of the array.")
    dtype: str    = Field(..., description="NumPy dtype string, e.g. 'int32' or 'float32'.")
    shape: List[int] = Field(..., description="Array shape, e.g. [240, 240, 155].")

    def to_numpy(self) -> np.ndarray:
        return b64_to_array(self.data_b64, self.dtype, self.shape)

    @classmethod
    def from_numpy(cls, arr: np.ndarray) -> "ArrayPayload":
        return cls(
            data_b64=array_to_b64(arr),
            dtype=str(arr.dtype),
            shape=list(arr.shape),
        )


class VolumeRequest(BaseModel):
    """Request body for POST /analyze/volume."""
    segmentation: ArrayPayload = Field(..., description="Integer label array (H,W,D).")
    voxel_spacing: Tuple[float, float, float] = Field(
        (1.0, 1.0, 1.0), description="Physical voxel size in mm."
    )
    subject_id: str = Field("unknown", description="Subject / patient identifier.")


class LongitudinalRequest(BaseModel):
    """Request body for POST /analyze/longitudinal."""
    seg_t1: ArrayPayload = Field(..., description="Baseline segmentation (H,W,D).")
    seg_t2: ArrayPayload = Field(..., description="Follow-up segmentation (H,W,D).")
    voxel_spacing: Tuple[float, float, float] = Field((1.0, 1.0, 1.0))
    days_elapsed: float = Field(..., gt=0, description="Days between scans.")
    subject_id: str = Field("unknown")


class ReportRequest(BaseModel):
    """Request body for POST /report/pdf."""
    segmentation: ArrayPayload
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    subject_id: str = "unknown"
    scan_date: str = ""
    institution: str = "Anatom AI"
    # Optional longitudinal data for the growth section
    seg_t1: Optional[ArrayPayload] = None
    days_elapsed: Optional[float] = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class VolumeResponse(BaseModel):
    """Response for POST /analyze/volume."""
    subject_id: str
    voxel_volume_mm3: float
    volumes_mm3: Dict[str, float]
    wt_mm3: float
    tc_mm3: float
    et_mm3: float
    total_tumor_mm3: float
    fractions: Dict[str, float]


class LongitudinalResponse(BaseModel):
    """Response for POST /analyze/longitudinal."""
    subject_id: str
    days_elapsed: float
    volumes_t1: Dict[str, float]
    volumes_t2: Dict[str, float]
    delta_mm3: Dict[str, float]
    rate_mm3_per_day: Dict[str, float]
    pct_change: Dict[str, float]
    rano_category: str
    rano_pct_change: float


class HealthResponse(BaseModel):
    """Response for GET /health."""
    status: str = "ok"
    version: str = "4.0.0"
    service: str = "Anatom AI Surgical Planning API"


# ---------------------------------------------------------------------------
# Phase 4 — Surgical Trajectory Planning
# ---------------------------------------------------------------------------

class TrajectoryRequest(BaseModel):
    """Request body for POST /plan/trajectory."""
    segmentation: ArrayPayload = Field(..., description="Integer label array (H,W,D).")
    voxel_spacing: Tuple[float, float, float] = Field(
        (1.0, 1.0, 1.0), description="Physical voxel size in mm."
    )
    landmarks: Optional[Dict[str, List[float]]] = Field(
        None,
        description="Dict of landmark_name → [x_mm, y_mm, z_mm]. "
                    "If not provided, trajectories are scored without landmark avoidance.",
    )
    n_candidates: int = Field(
        800, ge=50, le=5000,
        description="Number of candidate entry points sampled from the cortex.",
    )
    subject_id: str = Field("unknown")


class TrajectoryResultSchema(BaseModel):
    """A single ranked trajectory."""
    rank: int
    entry_point: List[float]       # [x, y, z] mm
    target_point: List[float]      # [x, y, z] mm
    path_length_mm: float
    safety_score: float            # 0.0–1.0
    warnings: List[str]
    landmark_distances: Dict[str, float]
    normal_alignment: float


class TrajectoryResponse(BaseModel):
    """Response for POST /plan/trajectory."""
    subject_id: str
    tumor_centroid: List[float]    # [x, y, z] mm
    trajectories: List[TrajectoryResultSchema]


# ---------------------------------------------------------------------------
# Phase 2 — User Health Profile
# ---------------------------------------------------------------------------

class ProfileRequest(BaseModel):
    """Request body for POST /profile."""
    user_id: str = Field(..., description="Client-generated UUID for the user.")
    name: str
    age: int = Field(..., ge=1, le=120)
    gender: str
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    blood_type: Optional[str] = None
    conditions: List[str] = []
    medications: List[str] = []


class ProfileResponse(BaseModel):
    """Response for POST /profile and GET /profile/{user_id}."""
    id: str
    name: str
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    blood_type: Optional[str]
    conditions: List[str]
    medications: List[str]
    health_score: float
    bmi: float
    metabolic_age: int
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Phase 3 — AI Medical Report Interpreter
# ---------------------------------------------------------------------------

class FindingSchema(BaseModel):
    text: str
    severity: str  # "normal" | "borderline" | "critical"
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None


class AnatomicalMappingItem(BaseModel):
    region_id: str
    finding_index: int = 0
    camera_focus: List[float] = [0.0, 0.5, 0.0]
    severity: str = "normal"


class InterpretResponse(BaseModel):
    """Response for POST /interpret."""
    report_id: str
    summary: str
    findings: List[FindingSchema]
    affected_regions: List[str]
    confidence: float
    reasoning: str
    report_type: str
    risk_level: str
    anatomical_mapping: List[AnatomicalMappingItem] = []


class GuidanceRequest(BaseModel):
    """Request body for POST /guidance."""
    report_id: str
    user_id: str


class ReportSummaryResponse(BaseModel):
    """Single item in GET /history/{user_id}."""
    id: str
    user_id: str
    file_name: str
    file_type: str
    report_type: str
    risk_level: str
    upload_date: str
    summary_snippet: str
    affected_regions: List[str]
    triage_level: Optional[str] = None  # denormalised for list performance


class ReportDetailResponse(ReportSummaryResponse):
    """Response for GET /history/{user_id}/{report_id}."""
    interpretation: InterpretResponse
    guidance: Optional[Dict] = None
    triage: Optional[Dict] = None
    knowledge_graph: Optional[Dict] = None
    personalized_insights: Optional[List[Dict]] = None
    diagnosis_data: Optional[Dict] = None


# ---------------------------------------------------------------------------
# AI Text Analysis (POST /analyze-report)
# ---------------------------------------------------------------------------

class ConditionResult(BaseModel):
    """A single disease / condition extracted by Gemini."""
    name:            str
    confidence:      float = Field(..., ge=0.0, le=1.0)
    affected_organs: List[str]
    severity:        str    # "mild" | "moderate" | "severe"
    description:     str


class AnalyzeReportRequest(BaseModel):
    """Request body for POST /analyze-report."""
    text: str = Field(..., min_length=10, description="Raw medical report text to analyse.")


class AnalyzeReportResponse(BaseModel):
    """Response for POST /analyze-report."""
    conditions:  List[ConditionResult]
    summary:     str
    risk_level:  str           # "low" | "moderate" | "high" | "critical"
    organ_keys:  List[str]     # resolved mesh keys, de-duped, most severe first
