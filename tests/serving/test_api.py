"""
Tests for src/serving/api.py — uses FastAPI TestClient (no server needed).
"""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.serving.api import app
from src.serving.schemas import ArrayPayload

client = TestClient(app)

SHAPE = (20, 20, 20)
SPACING = [1.0, 1.0, 1.0]


def _make_seg_payload(ncr=True, ed=True, et=True) -> dict:
    seg = np.zeros(SHAPE, dtype=np.int32)
    if ed:
        seg[4:16, 4:16, 4:16] = 2
    if ncr:
        seg[7:13, 7:13, 7:13] = 1
    if et:
        seg[9:11, 9:11, 9:11] = 3
    return ArrayPayload.from_numpy(seg).model_dump()


def _volume_body(**kwargs) -> dict:
    body = {
        "segmentation": _make_seg_payload(),
        "voxel_spacing": SPACING,
        "subject_id": "test-subject",
    }
    body.update(kwargs)
    return body


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_status_ok(self):
        r = client.get("/health")
        assert r.json()["status"] == "ok"

    def test_version_present(self):
        r = client.get("/health")
        assert "version" in r.json()


# ---------------------------------------------------------------------------
# /analyze/volume
# ---------------------------------------------------------------------------

class TestAnalyzeVolume:
    def test_returns_200(self):
        r = client.post("/analyze/volume", json=_volume_body())
        assert r.status_code == 200

    def test_response_has_wt(self):
        r = client.post("/analyze/volume", json=_volume_body())
        assert "wt_mm3" in r.json()

    def test_response_has_tc(self):
        r = client.post("/analyze/volume", json=_volume_body())
        assert "tc_mm3" in r.json()

    def test_response_has_et(self):
        r = client.post("/analyze/volume", json=_volume_body())
        assert "et_mm3" in r.json()

    def test_subject_id_echoed(self):
        r = client.post("/analyze/volume", json=_volume_body(subject_id="my-subject"))
        assert r.json()["subject_id"] == "my-subject"

    def test_wt_greater_than_tc(self):
        """WT must be >= TC (WT = NCR+ED+ET, TC = NCR+ET)."""
        r = client.post("/analyze/volume", json=_volume_body())
        data = r.json()
        assert data["wt_mm3"] >= data["tc_mm3"]

    def test_tc_greater_than_et(self):
        r = client.post("/analyze/volume", json=_volume_body())
        data = r.json()
        assert data["tc_mm3"] >= data["et_mm3"]

    def test_all_background_returns_zero_volumes(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        payload = ArrayPayload.from_numpy(seg).model_dump()
        r = client.post("/analyze/volume", json={
            "segmentation": payload,
            "voxel_spacing": SPACING,
            "subject_id": "empty",
        })
        assert r.status_code == 200
        assert r.json()["wt_mm3"] == pytest.approx(0.0)

    def test_voxel_spacing_scales_volume(self):
        """Double spacing should produce 8× the volume."""
        body1 = _volume_body()
        body2 = _volume_body()
        body2["voxel_spacing"] = [2.0, 2.0, 2.0]
        r1 = client.post("/analyze/volume", json=body1)
        r2 = client.post("/analyze/volume", json=body2)
        wt1 = r1.json()["wt_mm3"]
        wt2 = r2.json()["wt_mm3"]
        if wt1 > 0:
            assert wt2 == pytest.approx(wt1 * 8, rel=0.01)

    def test_fractions_present(self):
        r = client.post("/analyze/volume", json=_volume_body())
        assert "fractions" in r.json()

    def test_volumes_mm3_dict_present(self):
        r = client.post("/analyze/volume", json=_volume_body())
        assert "volumes_mm3" in r.json()

    def test_invalid_body_returns_422(self):
        r = client.post("/analyze/volume", json={"bad": "data"})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# /analyze/longitudinal
# ---------------------------------------------------------------------------

class TestAnalyzeLongitudinal:
    def _body(self, days=90.0) -> dict:
        seg1 = np.zeros(SHAPE, dtype=np.int32)
        seg1[4:16, 4:16, 4:16] = 2
        seg1[7:13, 7:13, 7:13] = 1
        seg2 = np.zeros(SHAPE, dtype=np.int32)
        seg2[5:12, 5:12, 5:12] = 2
        return {
            "seg_t1": ArrayPayload.from_numpy(seg1).model_dump(),
            "seg_t2": ArrayPayload.from_numpy(seg2).model_dump(),
            "voxel_spacing": SPACING,
            "days_elapsed": days,
            "subject_id": "long-subject",
        }

    def test_returns_200(self):
        r = client.post("/analyze/longitudinal", json=self._body())
        assert r.status_code == 200

    def test_rano_category_present(self):
        r = client.post("/analyze/longitudinal", json=self._body())
        assert "rano_category" in r.json()
        assert r.json()["rano_category"] in ("CR", "PR", "SD", "PD")

    def test_delta_mm3_present(self):
        r = client.post("/analyze/longitudinal", json=self._body())
        assert "delta_mm3" in r.json()

    def test_rate_mm3_per_day_present(self):
        r = client.post("/analyze/longitudinal", json=self._body())
        assert "rate_mm3_per_day" in r.json()

    def test_days_elapsed_echoed(self):
        r = client.post("/analyze/longitudinal", json=self._body(days=45.0))
        assert r.json()["days_elapsed"] == pytest.approx(45.0)

    def test_missing_days_returns_422(self):
        body = self._body()
        del body["days_elapsed"]
        r = client.post("/analyze/longitudinal", json=body)
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# /report/pdf
# ---------------------------------------------------------------------------

class TestReportPDF:
    def test_returns_200(self):
        r = client.post("/report/pdf", json=_volume_body())
        assert r.status_code == 200

    def test_content_type_is_pdf(self):
        r = client.post("/report/pdf", json=_volume_body())
        assert "application/pdf" in r.headers["content-type"]

    def test_response_starts_with_pdf_magic(self):
        r = client.post("/report/pdf", json=_volume_body())
        assert r.content[:4] == b"%PDF"

    def test_content_disposition_filename(self):
        body = _volume_body(subject_id="BraTS-007")
        r = client.post("/report/pdf", json=body)
        assert "BraTS-007" in r.headers.get("content-disposition", "")

    def test_nonempty_pdf(self):
        r = client.post("/report/pdf", json=_volume_body())
        assert len(r.content) > 1024


# ---------------------------------------------------------------------------
# /report/dicom
# ---------------------------------------------------------------------------

class TestReportDICOM:
    def test_returns_200(self):
        r = client.post("/report/dicom", json=_volume_body())
        assert r.status_code == 200

    def test_content_type_is_dicom(self):
        r = client.post("/report/dicom", json=_volume_body())
        assert "application/dicom" in r.headers["content-type"]

    def test_dicom_preamble(self):
        """DICOM files have a 128-byte preamble + 'DICM' magic."""
        r = client.post("/report/dicom", json=_volume_body())
        assert r.content[128:132] == b"DICM"

    def test_content_disposition_filename(self):
        body = _volume_body(subject_id="BraTS-042")
        r = client.post("/report/dicom", json=body)
        assert "BraTS-042" in r.headers.get("content-disposition", "")

    def test_nonempty_dicom(self):
        r = client.post("/report/dicom", json=_volume_body())
        assert len(r.content) > 512
