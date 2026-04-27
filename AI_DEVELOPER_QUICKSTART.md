# Anatom AI — AI Developer Quick Start

**5-minute onboarding guide for other AI systems working on this project.**

---

## What is Anatom AI?

A **clinical-grade surgical planning platform** that:
1. Takes brain tumor segmentations (3D MRI, BraTS labels: 0=BG, 1=NCR, 2=ED, 3=ET)
2. Computes volumes, RANO response categories, radiomic features, recurrence risk scores
3. Renders **photorealistic 3D brain visualization** with cortical surface, virtual craniotomy, uncertainty fog
4. Plans optimal surgical trajectories to avoid critical brain structures
5. Generates PDF reports with AI clinical narratives

**Status:** Production-ready (Phases 0–5 complete), **Phase 6 pending** (4 advanced features: S2–S5).

---

## Key Metrics & Numbers

| Metric | Value | Notes |
|--------|-------|-------|
| **Model Size** | 19.1M params | 3D U-Net, 4-class segmentation |
| **Input Volume** | 128³ voxels | 4 modalities (T1, T1ce, T2, FLAIR) |
| **Inference Time** | 2–4s | Single GPU, ~0.5s |
| **Render Time** | 1–2s | PyVista off-screen, 1200×900 PNG |
| **Features Extracted** | 35+ | Radiomic: shape, texture, first-order |
| **Risk Score Range** | 0–100 | Heuristic 6-factor model |
| **Anatomical Landmarks** | 9 | Brainstem, ventricles, thalami, corpus callosum |
| **Top Trajectories** | 3 | Ranked by safety score |

---

## File Map for Quick Navigation

### Core Medical Imaging
- `src/imaging/loader.py` — Load NIfTI files
- `src/imaging/skull_stripper.py` — Extract brain from skull
- `src/imaging/cortex_extractor.py` — Generate cortical surface mesh

### Deep Learning
- `src/models/unet3d.py` — 3D U-Net architecture
- `src/training/trainer.py` — Training loop

### Analytics
- `src/analytics/volumetrics.py` — Volume computation (core metric)
- `src/analytics/radiomics.py` — Radiomic fingerprinting
- `src/analytics/recurrence_risk.py` — Risk scoring (0–100)
- `src/analytics/trajectory_planner.py` — Surgical route optimization

### 3D Visualization
- `src/ui/pyvista_renderer.py` — **3D rendering engine** (PyVista)
- `src/ui/surgical_viewer_page.py` — Streamlit 3D viewer page
- `src/ui/theme.py` — Medical workstation CSS

### Reporting
- `src/reporting/pdf_report.py` — PDF generation (ReportLab)
- `src/reporting/narrative_report.py` — AI clinical narrative (Jinja2)

### API
- `src/serving/api.py` — REST endpoints (FastAPI)

---

## BraTS Label Encoding (Critical)

**All segmentations use this encoding:**
```
0 = Background (non-brain)
1 = NCR (Necrotic Core) — red [220, 60, 60]
2 = ED (Peritumoral Edema) — yellow [240, 200, 30]
3 = ET (Enhancing Tumor) — cyan [60, 200, 220]
```

**Composite metrics:**
- **WT (Whole Tumor)** = 1 + 2 + 3
- **TC (Tumor Core)** = 1 + 3
- **ET (Enhancing)** = 3 only

---

## Start the App in 30 Seconds

```bash
# 1. Install
pip install -r requirements.txt

# 2. Start dashboard
export PYVISTA_OFF_SCREEN=true  # Critical on Windows
streamlit run src/ui/app.py --server.port 8502

# 3. Open browser
open http://localhost:8502
```

**Everything works without data — click through all pages with built-in demo data first.**

---

## Key Code Examples

### Load a Segmentation & Compute Volumes

```python
import numpy as np
from src.analytics.volumetrics import VolumetricAnalyzer

# Your segmentation: shape (128, 128, 128), dtype int32, labels 0–3
seg = np.load("seg.npy").astype(np.int32)
voxel_spacing = (1.0, 1.0, 1.2)  # mm

analyzer = VolumetricAnalyzer()
result = analyzer.compute(seg, voxel_spacing, subject_id="BraTS-001")

print(f"Whole Tumor: {result.wt_mm3:.1f} mm³")
print(f"ET volume: {result.et_mm3:.1f} mm³")
print(f"Risk score: {result.risk_score}")  # If computed
```

### Extract Radiomic Features

```python
from src.analytics.radiomics import RadiomicsExtractor

seg = np.load("seg.npy").astype(np.int32)
vol = np.load("vol.npy").astype(np.float32)

extractor = RadiomicsExtractor(use_pyradiomics=True)
features = extractor.extract(seg, volume=vol, voxel_spacing=(1.0, 1.0, 1.2))

# features["ET"] = {"sphericity": 0.65, "glcm_contrast": 125.3, ...}
print(f"ET Sphericity: {features['ET'].get('sphericity', 0):.3f}")
```

### Generate PDF Report

```python
from src.reporting.pdf_report import PDFReportBuilder, ReportConfig

cfg = ReportConfig(
    subject_id="BraTS-001",
    institution="Hospital X",
    scan_date="2026-04-14",
)

builder = PDFReportBuilder(cfg)
pdf_bytes = builder.build(
    segmentation=seg,
    volume=vol,
    voxel_spacing=(1.0, 1.0, 1.2),
    vol_result=result,
    radiomic_features=features,
    risk_estimate=risk,
    narrative_text=narrative,
)

# Save or upload
with open("report.pdf", "wb") as f:
    f.write(pdf_bytes)
```

### Render 3D Tumor Visualization

```python
from src.ui.pyvista_renderer import NeuroRenderer, RenderParams

renderer = NeuroRenderer(width=1200, height=900)

params = RenderParams(
    mode="standard",         # or "craniotomy", "xray"
    clip_radius=50.0,        # for craniotomy mode
    cortex_opacity=0.22,
    camera_preset="axial",   # or "sagittal", "coronal", "default"
)

# Render tumour only (no cortex needed)
png_bytes = renderer.render_combined(
    cortex_mesh=None,
    segmentation=seg,
    voxel_spacing=(1.0, 1.0, 1.2),
    params=params,
)

# Save or display
with open("render.png", "wb") as f:
    f.write(png_bytes)
```

### Call REST API

```bash
# POST /analyze/volume
curl -X POST http://localhost:8000/analyze/volume \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": "BraTS-001",
    "segmentation": {
      "data": "<base64-encoded-seg>",
      "dtype": "int32",
      "shape": [128, 128, 128]
    },
    "voxel_spacing": [1.0, 1.0, 1.2]
  }'

# Response:
# {
#   "subject_id": "BraTS-001",
#   "wt_mm3": 18000.5,
#   "tc_mm3": 10000.2,
#   "et_mm3": 4000.1,
#   ...
# }
```

---

## Debugging & Common Issues

### Issue: `PYVISTA_OFF_SCREEN` Error
```
Error: X11 display required / RuntimeError: Cannot create offscreen context
```
**Fix:**
```bash
export PYVISTA_OFF_SCREEN=true
# or in Python:
import os
os.environ["PYVISTA_OFF_SCREEN"] = "true"
import pyvista as pv
```

### Issue: PyVista Renders Blank PNG
```
PNG is all black / white
```
**Fix:**
- Check: is `Plotter(off_screen=True)` set?
- Check: is `pl.enable_depth_peeling()` called?
- Check: are colors valid RGB tuples in [0, 255] range?

### Issue: ANTsPy Registration Hangs
```
Takes 30+ seconds or fails silently
```
**Status:** Expected (ANTsPy Rigid is slow). For production, cache registration matrices.

### Issue: Streamlit App Doesn't Show 3D Viewer
```
Page shows alert: "PyVista is not installed"
```
**Fix:** `pip install pyvista>=0.44.0 vtk>=9.3.0`

---

## 3 Essential Files to Read First

1. **`src/ui/app.py`** (main Streamlit app)
   - 7 pages + sidebar navigation
   - Page routing logic
   - Data pipeline: upload → preprocess → render

2. **`src/ui/pyvista_renderer.py`** (3D rendering engine)
   - NeuroRenderer class
   - RenderParams dataclass
   - Camera positioning logic
   - Depth peeling for transparency

3. **`src/analytics/volumetrics.py`** (core analytics)
   - VolumetricAnalyzer: the most-used class
   - Volumetric result computation
   - RANO classification

---

## Phase 6 Features (Next Steps)

**If asked to implement Phase 6, prioritize in this order:**

### S2: DICOM RTSTRUCT Export ⭐ **Do this first**
- **File:** `src/reporting/dicom_rtstruct.py`
- **Purpose:** Export tumor surfaces as DICOM RT Structure Set (surgical planning integration)
- **Why first:** High clinical value, medium complexity, ≤1 day work
- **Acceptance:** File opens in 3D Slicer without errors

### S3: Eloquent Cortex Mapping
- **File:** `src/imaging/eloquent_mapper.py`
- **Purpose:** Highlight language-critical regions (Broca/Wernicke) to avoid
- **Complexity:** Medium (atlas registration already done)
- **Acceptance:** Colored patches appear on cortical surface

### S4: Population Cohort Heatmap
- **File:** `src/analytics/cohort_analyzer.py` + `src/ui/population_analytics_page.py`
- **Purpose:** Aggregate multiple patients → voxel-wise probability heatmap
- **Complexity:** Medium (batch processing, visualization)
- **Acceptance:** Upload 10 segmentations, see probability gradient

### S5: WebSocket Streaming Inference ⭐ **High effort, high impact**
- **File:** `src/serving/ws_inference.py`
- **Purpose:** Real-time tumor "emergence" during inference
- **Complexity:** High (async/await, patch coordination)
- **Acceptance:** Tumor appears voxel-by-voxel during inference

---

## Testing Your Changes

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_analytics/test_volumetrics.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Test a single function
pytest tests/test_analytics/test_volumetrics.py::test_compute_rano -v
```

---

## Directory Structure (Simplified)

```
Anatom AI/
├── src/
│   ├── imaging/          # MRI I/O, preprocessing
│   ├── models/           # U-Net architecture
│   ├── training/         # Training loop
│   ├── analytics/        # Volumetrics, risk scoring, trajectory planning
│   ├── reporting/        # PDF, DICOM, narrative generation
│   ├── serving/          # REST API
│   └── ui/               # Streamlit dashboard + PyVista rendering
├── config/               # YAML configs (landmarks, preprocessing)
├── scripts/              # CLI utilities
├── tests/                # Pytest unit tests
├── templates/            # Jinja2 templates (narrative report)
├── Dockerfile            # Docker image
├── requirements.txt      # Dependencies
├── PROJECT_CONTEXT.md    # **START HERE: Full project overview**
├── TECHNICAL_REFERENCE.md # Deep implementation details
└── AI_DEVELOPER_QUICKSTART.md  # **This file**
```

---

## Code Standards

### Type Hints (Required)
```python
def compute(self, seg: np.ndarray, spacing: Tuple[float, float, float]) -> VolumetricResult:
    """Compute volumes from segmentation."""
```

### Docstrings (Required)
```python
def extract_cortex(subject: MRISubject, brain_mask: np.ndarray) -> pv.PolyData:
    """
    Extract cortical pial surface from T1 MRI via marching cubes.
    
    Parameters
    ----------
    subject : MRISubject
        Loaded subject with T1 modality.
    brain_mask : np.ndarray
        Binary brain mask (uint8, same shape as T1).
    
    Returns
    -------
    pv.PolyData
        Cortical surface mesh with curvature scalars.
    """
```

### Error Handling
```python
try:
    from pyradiomics import featureextractor
except ImportError:
    # Fallback to scipy
    featureextractor = None
```

### Testing Pattern (TDD)
```python
def test_volumetric_computation():
    seg = np.zeros((64, 64, 64), dtype=np.int32)
    seg[20:40, 20:40, 20:40] = 1  # NCR cube
    result = VolumetricAnalyzer().compute(seg, (1.0, 1.0, 1.0))
    assert result.ncr_mm3 == 8000.0  # 20×20×20 = 8000 voxels = 8000 mm³
```

---

## Performance Targets

| Operation | Target | Current | Notes |
|-----------|--------|---------|-------|
| U-Net inference | <5s | 2–4s | ✅ Good |
| PDF generation | <5s | 2–3s | ✅ Good |
| 3D render | <3s | 1–2s | ✅ Good |
| Radiomic extraction | <15s | 5–10s | ✅ Good |
| Cortex extraction | <10s | 3–5s | ✅ Good |
| MNI registration | <60s | ~30s | ✅ Acceptable (cache it) |

---

## Dependency Versions (Critical)

| Package | Min Version | Notes |
|---------|-------------|-------|
| PyVista | 0.47.3 | Camera API: use `camera.up`, not `camera.view_up` |
| VTK | 9.3.0 | Headless rendering support |
| NumPy | 1.26.0 | Type hints support |
| PyRadiomics | 3.1.0 | IBSI compliance |
| ANTsPy | 0.4.2 | Optional; falls back gracefully |
| Streamlit | 1.32.0 | Session state stability |
| FastAPI | 0.110.0 | WebSocket support (Phase 6) |

---

## Rapid Feature Development Workflow

1. **Plan** — Write docstring + type hints before code
2. **Implement** — Write implementation in isolated module
3. **Test** — Write pytest test case (TDD)
4. **Integrate** — Add to app.py or api.py
5. **Verify** — Run full test suite + manual test with demo data
6. **Document** — Update relevant .md file

**Example: Add a new analytic metric**
```python
# Step 1: Write in src/analytics/newmetric.py
class NewAnalyzer:
    def analyze(self, seg: np.ndarray) -> float:
        """Compute new metric from segmentation."""
        ...

# Step 2: Write test in tests/test_analytics/test_newmetric.py
def test_new_metric():
    seg = create_demo_seg()
    result = NewAnalyzer().analyze(seg)
    assert result > 0

# Step 3: Integrate in src/ui/app.py or src/serving/api.py
from src.analytics.newmetric import NewAnalyzer
analyzer = NewAnalyzer()
metric_val = analyzer.analyze(data["seg"])

# Step 4: Run tests
pytest tests/ -v
```

---

## What NOT to Do

❌ Don't hardcode file paths (use `Path` relative to project root)  
❌ Don't skip type hints  
❌ Don't bypass skull-stripping (critical for anatomical accuracy)  
❌ Don't ignore ANTsPy errors (use fallback landmarks)  
❌ Don't render without depth peeling enabled (transparency breaks)  
❌ Don't commit secrets or .env files  
❌ Don't assume GPU available (always provide CPU fallback)  

---

## Quick Command Reference

```bash
# Install all deps
pip install -r requirements.txt

# Run Streamlit
PYVISTA_OFF_SCREEN=true streamlit run src/ui/app.py --server.port 8502

# Start FastAPI
uvicorn src.serving.api:app --port 8000 --reload

# Run tests
pytest tests/ -v --cov=src

# Format code
black src/ && isort src/

# Type check
mypy src/ --ignore-missing-imports

# Docker build
docker build -t anatomai:latest .

# Docker run API
docker run -p 8000:8000 anatomai:latest

# Docker run dashboard
docker run -p 8502:8502 anatomai:latest streamlit run src/ui/app.py
```

---

## Next Steps

1. ✅ **Read** `PROJECT_CONTEXT.md` (this session's overview)
2. ✅ **Read** `TECHNICAL_REFERENCE.md` (deep dives for implementation)
3. ⏭️ **Run** `streamlit run src/ui/app.py` and explore all 7 pages
4. ⏭️ **Pick a Phase 6 feature** (S2 recommended first)
5. ⏭️ **Implement** following the checklist in TECHNICAL_REFERENCE.md
6. ⏭️ **Test** with pytest + manual verification
7. ⏭️ **Document** your changes in code + relevant .md files

---

**Good luck! The project is well-structured — focus on one Phase 6 feature at a time.**
