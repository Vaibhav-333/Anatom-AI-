# Anatom AI — Technical Reference for AI Developers

**This document is a deep-dive for AI agents implementing Phase 6 features or extending the codebase.**

---

## Section 1: Data Flow & Pipeline Architecture

### End-to-End Medical Image Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INPUT DATA SOURCES                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────┐
    │ NIfTI Folder (BraTS format)           │
    │ ├── T1.nii.gz   (pre-contrast)        │
    │ ├── T1ce.nii.gz (post-contrast)       │
    │ ├── T2.nii.gz   (T2-weighted)         │
    │ ├── FLAIR.nii.gz (FLAIR)              │
    │ └── seg.nii.gz (segmentation)         │
    └───────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│              PREPROCESSING LAYER (src/imaging/pipeline.py)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  NIfTILoader.load(path) → MRISubject                                        │
│     ├─ nibabel: read 4 modalities into float32 arrays                       │
│     ├─ Extract affine, voxel_spacing from NIfTI header                      │
│     └─ Load segmentation (dtype=int32, labels 0–3)                          │
│           ↓                                                                   │
│  SkullStripper.strip(subject) → (subject_stripped, brain_mask)              │
│     ├─ SimpleITK: cast T1 to float32                                        │
│     ├─ Otsu threshold on T1 voxels → binary mask                            │
│     └─ Apply mask to all 4 modalities                                       │
│           ↓                                                                   │
│  Normalizer.normalize(subject) → subject_normalized                         │
│     ├─ Per-modality robust scaling (Q1–Q99, ignore outliers)                │
│     └─ (Option) Z-norm if register_to_mni=true                             │
│           ↓                                                                   │
│  [OPTIONAL] Registrar.register(subject) → subject_registered                │
│     ├─ ANTsPy rigid affine to MNI152                                        │
│     ├─ Inverse transform for landmark projection                            │
│     └─ Registration matrix stored in metadata["registration_affine"]        │
│           ↓                                                                   │
│  [OPTIONAL] Resampler.resample(subject, target_spacing) → subject_resampled │
│     ├─ SimpleITK linear interpolation for volumes                           │
│     └─ Nearest-neighbor for segmentation (preserve label values)            │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INFERENCE LAYER (torch backend)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Preprocessing complete → concatenate 4 modalities along channel axis       │
│     Input shape: (1, 4, 128, 128, 128)  [batch, channels, depth, H, W]     │
│           ↓                                                                   │
│  Load 3D U-Net checkpoint (19.1M params)                                    │
│     ├─ Input: 4 modalities (T1, T1ce, T2, FLAIR)                           │
│     ├─ Output: (1, 4, 128, 128, 128) logits for 4 classes                  │
│     └─ Deep supervision: 4 auxiliary heads (training only)                  │
│           ↓                                                                   │
│  forward() in training=False (no auxiliary heads)                           │
│     ├─ Encoder: 5 levels, skip connections stored                          │
│     ├─ Bottleneck: 320 channels, spatial dropout (p=0.1)                   │
│     └─ Decoder: 4 levels, upsampling with concatenation                    │
│           ↓                                                                   │
│  Output: logits → softmax → argmax per voxel                               │
│     Segmentation: (128, 128, 128) int32 with labels 0–3                    │
│           ↓                                                                   │
│  [OPTIONAL] MC Dropout inference (N=10 forward passes with dropout on)      │
│     ├─ Collect all N probability maps                                       │
│     ├─ Compute per-voxel entropy: H(x) = -∑ p(c) log p(c)                  │
│     └─ Entropy shape: (128, 128, 128) float32                              │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ANALYTICS LAYER (src/analytics/)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  VolumetricAnalyzer.compute(seg, voxel_spacing) → VolumetricResult          │
│     ├─ Count voxels per class (1=NCR, 2=ED, 3=ET)                          │
│     ├─ Multiply by voxel volume: (sx*sy*sz) mm³                            │
│     ├─ Compute sums: WT=1+2+3, TC=1+3, ET=3, etc.                          │
│     └─ Return: dict with all volumes + fractions of brain                   │
│           ↓                                                                   │
│  LongitudinalTracker.classify_rano(baseline_wt, current_wt) → category      │
│     ├─ CR if current ≤ 10% baseline                                         │
│     ├─ PR if 10% < current ≤ baseline AND ≥25% reduction                   │
│     ├─ SD if < 25% reduction and < 25% increase                            │
│     └─ PD if ≥ 25% increase                                                 │
│           ↓                                                                   │
│  RadiomicsExtractor.extract(seg, vol, voxel_spacing) → dict                │
│     ├─ Primary: PyRadiomics on per-class masks                              │
│     │   ├─ Shape: sphericity, SAV ratio, elongation                         │
│     │   ├─ First-order: entropy, kurtosis, skewness                         │
│     │   └─ GLCM: contrast, homogeneity, energy                              │
│     ├─ Fallback: scipy morphology + histogram if PyRadiomics unavailable    │
│     └─ Output: {"NCR": {...}, "ED": {...}, "ET": {...}}                    │
│           ↓                                                                   │
│  RecurrenceRiskEstimator.estimate(vol_result, radiomic_features) → score    │
│     ├─ Base score: 50                                                        │
│     ├─ Adjustments: ET vol, ED/WT, TC/WT, sphericity, GLCM, RANO          │
│     ├─ Final: max(0, min(100, base + sum(adjustments)))                    │
│     └─ Return: RiskEstimate with interpretation + contributions             │
│           ↓                                                                   │
│  CortexExtractor.extract(subject, brain_mask) → pyvista.PolyData            │
│     ├─ Input: subject.t1 (skull-stripped), brain_mask                      │
│     ├─ Smooth: scipy.ndimage.gaussian_filter(σ=1.5)                        │
│     ├─ Threshold: Otsu on voxels within brain_mask                          │
│     ├─ Marching cubes: skimage.measure.marching_cubes                       │
│     ├─ Decimation: trimesh.simplification.simplify (target ~80K triangles)  │
│     ├─ Curvature: per-vertex mean curvature for shading scalar              │
│     └─ Output: PolyData(points, faces, scalars={})                          │
│           ↓                                                                   │
│  SurgicalTrajectoryPlanner.plan(cortex, centroid, landmarks) → [top-3]      │
│     ├─ Sample ~2000 entry points from pial surface                          │
│     ├─ For each: cast ray to centroid, check landmark intersections         │
│     ├─ Score: 0.30*length + 0.55*safety + 0.15*normal_alignment            │
│     └─ Return: [TrajectoryResult, ...] sorted by score (descending)         │
│           ↓                                                                   │
│  AnatomicalLandmarkDetector.detect(subject, registration_affine)            │
│     ├─ If ANTsPy available: use computed registration                       │
│     ├─ Else: fallback geometric estimates from brain centroid               │
│     ├─ Inverse-transform canonical MNI coords to patient space              │
│     └─ Return: {"brainstem": (x,y,z), "l_ventricle": (x,y,z), ...}        │
│           ↓                                                                   │
│  UncertaintyFog.build(entropy_map, voxel_spacing) → pyvista.PolyData        │
│     ├─ Threshold: entropy > P78 (outer sparse layer)                        │
│     ├─ Threshold: entropy > P90 (inner dense layer)                         │
│     ├─ Convert voxel coords to patient coords: voxel_idx * voxel_spacing    │
│     └─ Return: point cloud with plasma colormap + opacity=0.4              │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                  RENDERING LAYER (PyVista 3D visualization)                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  NeuroRenderer.render_combined(cortex_mesh, segmentation, params)            │
│     ├─ Initialize: Plotter(off_screen=True, window_size=(1200,900))        │
│     ├─ Add cortex mesh with Phong shading + curvature scalars              │
│     ├─ Add tumor sub-regions (NCR/ED/ET) with per-class colors             │
│     ├─ Enable depth peeling (4 peels) for correct alpha blending           │
│     │                                                                         │
│     ├─ [IF params.mode == "craniotomy"]                                    │
│     │   ├─ Compute tumor centroid                                           │
│     │   ├─ Create vtkSphere implicit function at centroid                  │
│     │   ├─ Clip cortex mesh: remove voxels outside sphere                  │
│     │   └─ sphere radius = params.clip_radius                               │
│     │                                                                         │
│     ├─ [IF params.show_uncertainty_fog]                                    │
│     │   └─ Add neon fog point cloud (plasma colormap)                      │
│     │                                                                         │
│     ├─ [IF params.show_landmarks]                                          │
│     │   ├─ Add colored spheres at landmark coords                           │
│     │   └─ Add text labels                                                  │
│     │                                                                         │
│     ├─ [IF params.camera_preset == "axial"]                               │
│     │   └─ Set camera: position=[cx, cy, cz+300], focal=[cx, cy, cz]      │
│     │                                                                         │
│     ├─ Set background color, lighting                                       │
│     ├─ Render off-screen                                                    │
│     └─ Export: pl.screenshot() → numpy uint8 (H, W, 3)                     │
│           ↓                                                                   │
│  Streamlit st.image(numpy_array)                                            │
│     └─ Display in browser at 1200×900px                                    │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                   REPORTING LAYER (PDF / DICOM output)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  NarrativeReportBuilder.render(vol_result, radiomic_features, risk) → text  │
│     ├─ Load Jinja2 template: templates/narrative_report.j2                  │
│     ├─ Build context dict with clinical variables                          │
│     ├─ Render template → 5-section narrative (markdown-like)               │
│     └─ Fallback to plaintext if Jinja2 fails                               │
│           ↓                                                                   │
│  PDFReportBuilder.build(...) → bytes                                        │
│     ├─ Header + institution logo                                            │
│     ├─ Patient demographics                                                 │
│     ├─ Volume metrics (bar chart)                                           │
│     ├─ Sub-region table (NCR/ED/ET)                                        │
│     ├─ [NEW] Radiomics section (feature table)                             │
│     ├─ [NEW] Risk section (score + factors)                                │
│     ├─ [NEW] Narrative section (preformatted monospace)                    │
│     ├─ Recommendations                                                      │
│     └─ ReportLab: PDF → bytes                                              │
│           ↓                                                                   │
│  [PHASE 6 S2] DicomRTStructWriter.write(tumor_mesh, trajectory) → bytes     │
│     ├─ Create DICOM RT Structure Set                                        │
│     ├─ Add tumor contours (referenced to segmentation)                      │
│     ├─ Add trajectory as reference line (ReferencedBeamNumber)             │
│     └─ Return DICOM binary (importable by Brainlab / Medtronic)            │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                    ↓
        ┌─────────────────────────────┐
        │   OUTPUT ARTIFACTS          │
        ├─────────────────────────────┤
        │ ├─ Report PDF (1–2 MB)      │
        │ ├─ DICOM SR (100–500 KB)    │
        │ ├─ RTSTRUCT (50–200 KB)     │
        │ ├─ 3D render PNG (100–200 KB)
        │ └─ Narrative TXT (5–10 KB)  │
        └─────────────────────────────┘
```

---

## Section 2: PyVista Rendering Engine Deep-Dive

### PyVista Headless Rendering Strategy

**File:** `src/ui/renderer_context.py`

```python
# Platform-agnostic PyVista initialization
import os
import platform

if platform.system() == "Windows":
    os.environ["PYVISTA_OFF_SCREEN"] = "true"
else:  # Linux
    from pyvista import start_xvfb
    start_xvfb()

import pyvista as pv
pv.OFF_SCREEN = True  # Global override
```

**Why this works:**
- **Windows:** `PYVISTA_OFF_SCREEN` environment variable tells VTK to skip OpenGL display context creation
- **Linux (Docker):** Xvfb (X Virtual FrameBuffer) emulates a virtual X11 display, allowing VTK to render without a physical monitor

### Camera Positioning & Presets

**File:** `src/ui/pyvista_renderer.py`, line 191+

```python
class RenderParams:
    camera_preset: str = "default"  # one of: "default", "axial", "sagittal", "coronal"

def _apply_camera_preset(plotter, centroid, preset):
    """Apply camera preset based on anatomical orientation."""
    cx, cy, cz = centroid
    radius = 150  # mm distance from centroid
    
    if preset == "axial":
        # Superior view (looking down)
        pos = (cx, cy, cz + radius)
        focal = (cx, cy, cz)
        up = (0, -1, 0)  # anterior-posterior
    elif preset == "sagittal":
        # Right side view (looking left)
        pos = (cx + radius, cy, cz)
        focal = (cx, cy, cz)
        up = (0, 0, 1)   # superior-inferior
    elif preset == "coronal":
        # Front view (looking back)
        pos = (cx, cy + radius, cz)
        focal = (cx, cy, cz)
        up = (0, 0, 1)
    else:  # "default"
        # Oblique 3/4 view (medical workstation default)
        pos = (cx + 100, cy - 100, cz + 80)
        focal = (cx, cy, cz)
        up = (0, 0, 1)
    
    plotter.camera.position = pos
    plotter.camera.focal_point = focal
    plotter.camera.up = up  # PyVista 0.47.3 API
    plotter.reset_camera()
```

**Critical Fix:** PyVista 0.47.3 changed the camera API:
- **Old (broken):** `pl.camera.view_up = up`
- **New (correct):** `pl.camera.up = up`

### Mesh Coloring & Opacity

```python
# NCR (Necrotic Core)
ncr_color = (220, 60, 60)   # RGB, normalized to [0, 1] in VTK
pl.add_mesh(ncr_mesh, color=ncr_color, opacity=1.0, smooth_shading=True)

# ED (Edema) — semi-transparent outer shell
ed_color = (240, 200, 30)
pl.add_mesh(ed_mesh, color=ed_color, opacity=0.5, smooth_shading=True)

# ET (Enhancing Tumor) — solid core
et_color = (60, 200, 220)
pl.add_mesh(et_mesh, color=et_color, opacity=1.0, smooth_shading=True)

# Cortex — very subtle
cortex_color = (210, 180, 140)  # Tan
pl.add_mesh(cortex_mesh, color=cortex_color, opacity=0.22, smooth_shading=True)
```

### Depth Peeling for Correct Transparency

```python
# Critical for ED (semi-transparent shell) to show ET (solid core) inside
pl.enable_depth_peeling(number_of_peels=4)

# Without depth peeling: ED appears in front regardless of Z-order
# With depth peeling: VTK sorts fragments by depth, composites in order
```

---

## Section 3: Medical Image Processing Implementation Details

### Skull Stripping Algorithm

**File:** `src/imaging/skull_stripper.py`

```python
def strip(self, subject: MRISubject) -> Tuple[MRISubject, np.ndarray]:
    """
    Extract brain from skull using Otsu thresholding.
    
    Steps:
    1. Use T1 as reference (brightest white matter)
    2. Cast to float32, clip outliers [P1, P99]
    3. Compute Otsu threshold
    4. Dilate mask (remove small holes)
    5. Label connected components, keep largest (brain)
    6. Apply mask to all 4 modalities
    """
    import skimage.filters, skimage.measure
    
    t1_arr = subject.t1.get_data().astype(np.float32)
    
    # Clip outliers to avoid threshold bias from extreme values
    p1, p99 = np.percentile(t1_arr, [1, 99])
    t1_clipped = np.clip(t1_arr, p1, p99)
    
    # Otsu threshold
    threshold = skimage.filters.threshold_otsu(t1_clipped)
    binary = t1_clipped > threshold
    
    # Morphology: dilate to fill holes, then erode to preserve boundary
    binary = scipy.ndimage.binary_dilation(binary, iterations=1)
    binary = scipy.ndimage.binary_erosion(binary, iterations=1)
    
    # Keep largest connected component (assume it's the brain)
    labeled = skimage.measure.label(binary)
    sizes = np.bincount(labeled)
    largest_label = np.argmax(sizes[1:]) + 1
    brain_mask = (labeled == largest_label).astype(np.uint8)
    
    # Apply mask
    subject.t1.get_data()[:] *= brain_mask
    subject.t1ce.get_data()[:] *= brain_mask
    subject.t2.get_data()[:] *= brain_mask
    subject.flair.get_data()[:] *= brain_mask
    
    return subject, brain_mask
```

### Cortex Extraction Mesh Generation

**File:** `src/imaging/cortex_extractor.py`

```python
def extract(self, subject: MRISubject, brain_mask: np.ndarray) -> pv.PolyData:
    """
    Extract cortical pial surface from T1 MRI.
    
    Steps:
    1. Gaussian smooth T1 (σ=1.5mm → physical space)
    2. Otsu threshold on brain voxels
    3. Marching cubes surface extraction
    4. Mesh decimation (target ~80K triangles)
    5. Compute per-vertex curvature for shading
    6. Color map: gray matter (tan) + curvature scalars
    """
    import skimage.measure, skimage.filters, trimesh
    
    # 1. Smooth T1
    t1_arr = subject.t1.get_data().astype(np.float32)
    voxel_spacing = subject.metadata["voxel_spacing_mm"]
    sigma_voxels = 1.5 / np.array(voxel_spacing)  # physical to voxel space
    t1_smooth = scipy.ndimage.gaussian_filter(t1_arr, sigma=sigma_voxels)
    
    # 2. Threshold
    brain_voxels = t1_smooth[brain_mask.astype(bool)]
    threshold = skimage.filters.threshold_otsu(brain_voxels)
    binary = t1_smooth > threshold
    
    # 3. Marching cubes
    verts, faces, normals, values = skimage.measure.marching_cubes(
        binary,
        level=0.5,
        spacing=voxel_spacing,
    )
    
    # 4. Trimesh decimation
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    mesh = mesh.simplify_quadratic_mesh(target_count=80000)
    
    # 5. Compute curvature
    verts_decimated = mesh.vertices
    faces_decimated = mesh.faces
    # Compute mean curvature at each vertex via local geometry
    curvature = compute_mean_curvature(verts_decimated, faces_decimated)
    
    # 6. Convert to PyVista
    poly = pv.PolyData(verts_decimated, faces_decimated)
    poly["curvature"] = curvature
    
    return poly
```

### MNI152 Registration & Landmark Projection

**File:** `src/imaging/landmark_detector.py`

```python
def detect(self, subject: MRISubject) -> Dict[str, Tuple[float, float, float]]:
    """
    Project canonical brain landmarks from MNI152 into patient space.
    
    Steps:
    1. Register subject T1 to MNI152 template (ANTsPy Rigid)
    2. Load canonical landmark coords from config/landmarks_mni.yaml
    3. Inverse-transform: MNI coords → patient coords
    4. Return: {"brainstem": (x, y, z), ...}
    """
    import ants
    
    # 1. Load MNI template (standard 1mm isotropic)
    mni_template = ants.get_data("mni152")  # or load from disk
    
    # Convert subject T1 to ANTs format
    subject_ants = ants.from_numpy(subject.t1.get_data())
    
    # Rigid affine registration (quick, ~30s)
    registration = ants.registration(
        fixed=mni_template,
        moving=subject_ants,
        type_of_transform="Rigid",
    )
    
    # Extract transformation matrix (4x4 affine)
    fwd_xfm = registration["fwdtransforms"][0]  # subject → MNI
    
    # 2. Load landmark coordinates from YAML
    landmarks_mni = load_yaml("config/landmarks_mni.yaml")
    
    # 3. Inverse transform
    landmarks_patient = {}
    for landmark_name, mni_coords in landmarks_mni.items():
        # mni_coords is [x, y, z] in MNI space
        # Apply inverse transformation to get patient space coords
        patient_coords = apply_inverse_affine(fwd_xfm, mni_coords)
        landmarks_patient[landmark_name] = patient_coords
    
    # 4. Fallback if ANTsPy fails: estimate from brain centroid
    if registration is None:
        landmarks_patient = self._fallback_landmarks(subject)
    
    return landmarks_patient
```

---

## Section 4: Analytics & Risk Scoring

### Radiomic Feature Extraction

**File:** `src/analytics/radiomics.py`

```python
def extract(self, seg: np.ndarray, volume: Optional[np.ndarray] = None,
            voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0)) -> dict:
    """
    Extract IBSI-compliant radiomic features per tumor region.
    
    Returns: {
        "NCR": {"sphericity": 0.65, "surface_area_to_volume": 0.045, ...},
        "ED": {...},
        "ET": {...},
        "WT": {...},  # Whole tumor (1+2+3)
        "TC": {...},  # Tumor core (1+3)
    }
    """
    features = {}
    
    for region_name, region_label in [("NCR", 1), ("ED", 2), ("ET", 3), ...]:
        mask = (seg == region_label).astype(np.uint8)
        
        if np.sum(mask) == 0:
            features[region_name] = {}
            continue
        
        try:
            # Primary: PyRadiomics
            extractor = radiomics.featureextractor.RadiomicsFeatureExtractor(
                **DEFAULT_RADIOMICS_PARAMS
            )
            # PyRadiomics requires: image (volume), mask, and spacing
            feature_dict = extractor.execute(volume, mask, spacing=voxel_spacing)
        except ImportError:
            # Fallback: scipy + numpy
            feature_dict = self._extract_scipy(mask, volume, voxel_spacing)
        
        features[region_name] = {
            "sphericity": feature_dict.get("shape_Sphericity", 0.0),
            "surface_area_to_volume": feature_dict.get("shape_SurfaceAreaToVolume", 0.0),
            "elongation": feature_dict.get("shape_Elongation", 0.0),
            "entropy": feature_dict.get("firstorder_Entropy", 0.0),
            "glcm_contrast": feature_dict.get("glcm_Contrast", 0.0),
            "glcm_homogeneity": feature_dict.get("glcm_Homogeneity", 0.0),
            # ... (30+ more features)
        }
    
    return features
```

### Recurrence Risk Heuristic Model

**File:** `src/analytics/recurrence_risk.py`

```python
def estimate(self, vol_result: VolumetricResult,
             radiomic_features: Optional[dict] = None,
             rano_category: str = "SD") -> RiskEstimate:
    """
    Heuristic recurrence risk model: 0–100 score.
    
    Factors:
    1. ET volume (large = higher risk)
    2. ED/WT ratio (high edema = infiltration, higher risk)
    3. TC/WT ratio (well-defined core = lower risk)
    4. ET sphericity (irregular boundary = higher risk)
    5. GLCM contrast (heterogeneous = higher risk)
    6. RANO category (PD > SD > PR > CR)
    """
    score = 50  # baseline
    contributions = []
    
    # Factor 1: ET volume
    et_vol = vol_result.et_mm3
    if et_vol > 5000:
        delta = 10
    elif et_vol > 2000:
        delta = 5
    else:
        delta = 0
    score += delta
    contributions.append(RiskContribution("ET Volume", delta, "increase", f"{et_vol:.0f} mm³"))
    
    # Factor 2: ED/WT ratio
    ed_wt_ratio = vol_result.ed_mm3 / max(vol_result.wt_mm3, 1.0)
    if ed_wt_ratio > 0.6:
        delta = 8
    elif ed_wt_ratio > 0.4:
        delta = 4
    else:
        delta = 0
    score += delta
    contributions.append(RiskContribution("ED/WT Ratio", delta, "increase", f"{ed_wt_ratio:.2f}"))
    
    # Factor 3: TC/WT ratio (inverse penalty)
    tc_wt_ratio = vol_result.tc_mm3 / max(vol_result.wt_mm3, 1.0)
    if tc_wt_ratio < 0.3:
        delta = -5  # decreases risk
    else:
        delta = 0
    score += delta
    contributions.append(RiskContribution("TC/WT Ratio", delta, "decrease", f"{tc_wt_ratio:.2f}"))
    
    # Factor 4: Sphericity (from radiomic features)
    if radiomic_features and "ET" in radiomic_features:
        sphericity = radiomic_features["ET"].get("sphericity", 0.5)
        if sphericity < 0.50:
            delta = 8  # irregular boundary
        elif sphericity > 0.80:
            delta = -3  # well-circumscribed (protective)
        else:
            delta = 0
        score += delta
        contributions.append(RiskContribution("ET Sphericity", delta, "increase" if delta > 0 else "decrease", f"{sphericity:.3f}"))
    
    # Factor 5: GLCM Contrast (texture heterogeneity)
    if radiomic_features and "ET" in radiomic_features:
        contrast = radiomic_features["ET"].get("glcm_contrast", 0.0)
        if contrast > 500:
            delta = 6
        else:
            delta = 0
        score += delta
        contributions.append(RiskContribution("GLCM Contrast", delta, "increase", f"{contrast:.1f}"))
    
    # Factor 6: RANO category
    rano_deltas = {"CR": -10, "PR": -5, "SD": 0, "PD": 15}
    delta = rano_deltas.get(rano_category, 0)
    score += delta
    contributions.append(RiskContribution("RANO Category", delta, "increase" if delta > 0 else "decrease", rano_category))
    
    # Clamp to [0, 100]
    score = max(0, min(100, score))
    
    # Interpretation
    if score < 25:
        interp = "Low"
    elif score < 50:
        interp = "Moderate"
    elif score < 75:
        interp = "High"
    else:
        interp = "Very High"
    
    return RiskEstimate(
        score=score,
        interpretation=interp,
        contributions=contributions,
        disclaimer="This is a heuristic model for research only. Clinical decisions should incorporate expert judgment."
    )
```

---

## Section 5: REST API Architecture

### Request/Response Models (Pydantic)

**File:** `src/serving/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ArrayPayload(BaseModel):
    """Base64-encoded numpy array (standard for JSON APIs)."""
    data: str  # base64-encoded bytes from np.save() → BytesIO → b64encode
    dtype: str = "int32"
    shape: List[int]
    
    def to_numpy(self) -> np.ndarray:
        """Decode base64 → bytes → numpy."""
        import base64, io
        decoded = base64.b64decode(self.data)
        return np.load(io.BytesIO(decoded))

class VolumeRequest(BaseModel):
    subject_id: str
    segmentation: ArrayPayload
    voxel_spacing: List[float] = Field(default=[1.0, 1.0, 1.2])

class VolumeResponse(BaseModel):
    subject_id: str
    wt_mm3: float
    tc_mm3: float
    et_mm3: float
    ncr_mm3: float
    ed_mm3: float
    volumes_mm3: dict
    fractions: dict
    voxel_volume_mm3: float

class TrajectoryResultSchema(BaseModel):
    entry_point: List[float]
    target_point: List[float]
    path_length_mm: float
    safety_score: int
    warnings: List[str]

class TrajectoryRequest(BaseModel):
    subject_id: str
    segmentation: ArrayPayload
    nifti_path: Optional[str] = None  # If None, seg-only mode
    voxel_spacing: List[float] = Field(default=[1.0, 1.0, 1.2])

class TrajectoryResponse(BaseModel):
    subject_id: str
    trajectories: List[TrajectoryResultSchema]
    warnings: Optional[str] = None
```

### Example API Client Code

```python
import requests
import numpy as np
import base64
import io

# Prepare segmentation
seg = np.array(..., dtype=np.int32)  # (128, 128, 128)
seg_bytes = io.BytesIO()
np.save(seg_bytes, seg)
seg_b64 = base64.b64encode(seg_bytes.getvalue()).decode()

# POST to /analyze/volume
payload = {
    "subject_id": "BraTS-001",
    "segmentation": {
        "data": seg_b64,
        "dtype": "int32",
        "shape": list(seg.shape)
    },
    "voxel_spacing": [1.0, 1.0, 1.2]
}

resp = requests.post("http://localhost:8000/analyze/volume", json=payload)
result = resp.json()
print(f"WT: {result['wt_mm3']:.1f} mm³")
```

---

## Section 6: Streamlit UI State Management

### Sidebar Data Dict

**File:** `src/ui/app.py`, function `sidebar()`

```python
data = {
    "page": str,              # Active page name
    "subject_id": str,        # Patient label
    "voxel_spacing": (float, float, float),  # Physical voxel size
    "seg": Optional[np.ndarray],  # int32, shape (H,W,D), labels 0–3
    "vol": Optional[np.ndarray],  # float32 T1 volume
    "entropy": Optional[np.ndarray],  # MC Dropout entropy map
    "nifti_subject": Optional[MRISubject],  # Loaded from NIfTI folder
    "brain_mask": Optional[np.ndarray],  # Binary mask (uint8)
}
```

### Session State Usage

```python
# Radiomic features (computed once, cached)
if "radiomic_feats" not in st.session_state:
    st.session_state["radiomic_feats"] = {}

# Narrative text (computed once, cached)
if "narrative_text" in st.session_state:
    st.markdown(st.session_state["narrative_text"])

# 3D render cache (keyed by params hash)
cache_key = (subject_id, render_mode, clip_radius)
if cache_key in st.session_state.get("pyvista_render_cache", {}):
    cached_img = st.session_state["pyvista_render_cache"][cache_key]
else:
    # Render
    img = renderer.render_combined(...)
    if "pyvista_render_cache" not in st.session_state:
        st.session_state["pyvista_render_cache"] = {}
    st.session_state["pyvista_render_cache"][cache_key] = img
    cached_img = img
```

---

## Section 7: Configuration Files

### `config/landmarks_mni.yaml`

```yaml
# Canonical brain structure coordinates in MNI152 space (mm RAS)
landmarks:
  brainstem_midbrain:
    mni_coords: [0, -33, -20]
    color_rgb: [255, 100, 0]      # orange
    radius_mm: 8.0
    description: "Midbrain (CN III/IV)"
  
  brainstem_pons:
    mni_coords: [0, -28, -15]
    color_rgb: [255, 100, 0]
    radius_mm: 10.0
  
  brainstem_medulla:
    mni_coords: [0, -45, -35]
    color_rgb: [255, 100, 0]
    radius_mm: 8.0
  
  left_ventricle:
    mni_coords: [-14, 2, 14]
    color_rgb: [100, 200, 255]    # cyan
    radius_mm: 6.0
  
  right_ventricle:
    mni_coords: [14, 2, 14]
    color_rgb: [100, 200, 255]
    radius_mm: 6.0
  
  left_thalamus:
    mni_coords: [-12, -22, 8]
    color_rgb: [200, 100, 255]    # purple
    radius_mm: 8.0
  
  right_thalamus:
    mni_coords: [12, -22, 8]
    color_rgb: [200, 100, 255]
    radius_mm: 8.0
  
  corpus_callosum:
    mni_coords: [0, 0, 20]
    color_rgb: [100, 255, 100]    # green
    radius_mm: 10.0

proximity_warning_mm: 8.0
```

### `config/preprocessing.yaml`

```yaml
preprocessing:
  skull_strip: true
  register_to_mni: false          # Set to true for landmark detection
  normalize: "robust"             # "robust" | "z_score"
  resample:
    enabled: false
    target_spacing: [1.0, 1.0, 1.0]  # mm
  bias_correct: true

augmentation:  # Training-time only
  enabled: true
  rotation_degrees: 10
  scale_range: [0.9, 1.1]
  elastic_deform: true
  gamma_correction: true
```

---

## Section 8: Common Pitfalls & Solutions

| Pitfall | Symptom | Solution |
|---------|---------|----------|
| **PYVISTA_OFF_SCREEN not set** | `RuntimeError: X11 display required` (Linux) or blank PNG (Windows) | Set `PYVISTA_OFF_SCREEN=true` before importing pyvista |
| **Depth peeling not enabled** | ED (semi-transparent) hides ET (solid inner) | Call `pl.enable_depth_peeling(number_of_peels=4)` before render |
| **PyVista camera.view_up (old API)** | `AttributeError: 'Camera' has no attribute 'view_up'` (PyVista 0.47.3) | Use `pl.camera.up = up` instead of `pl.camera.view_up = up` |
| **ANTsPy registration fails** | `RuntimeError: ANTs not found` | Fallback to geometric landmark estimation; ANTsPy is optional |
| **MC Dropout entropy map is all zeros** | Model running in eval mode, dropout disabled | Call `model.train()` before inference; PyRadiomics fails silently | Use scipy fallback; add try/except |
| **Streamlit re-runs on slider change** | Entire script re-executes, losing cached objects | Use `st.session_state` to persist across reruns |
| **DICOM RTSTRUCT import fails in Brainlab** | File corrupted or missing required fields | Ensure ContourSequence has ReferencedROINumber + valid coordinates |

---

## Section 9: Phase 6 Implementation Checklists

### S2: DICOM RTSTRUCT Export

```
[ ] Create src/reporting/dicom_rtstruct.py
    [ ] DicomRTStructWriter class
    [ ] Method: write(tumor_surfaces, trajectory) → bytes
    [ ] Generate ROI IDs, contour sequences per region
    [ ] Write to DICOM Part 10 format
[ ] Add POST /export/rtstruct endpoint (api.py)
[ ] Test: import into 3D Slicer, verify contours visible
[ ] Test: import into Brainlab Elements
```

### S3: Eloquent Cortex Mapping

```
[ ] Create config/eloquent_mni.yaml with Brodmann area coords
[ ] Create src/imaging/eloquent_mapper.py
    [ ] Class: EloquentCortexMapper
    [ ] Method: map(subject, registration_affine) → dict of patches
[ ] Update SurgicalTrajectoryPlanner to avoid eloquent zones
[ ] Add checkboxes to Surgical Viewer: "Show Broca", "Show Wernicke"
[ ] Test: landmarks render as colored cortical patches
```

### S4: Population Cohort Heatmap

```
[ ] Create src/analytics/cohort_analyzer.py
    [ ] Class: CohortAnalyzer
    [ ] Method: analyze_batch(list_of_segs) → probability map
[ ] Create src/ui/population_analytics_page.py
    [ ] File uploader for multiple segmentations
    [ ] Render probability heatmap in PyVista
[ ] Add "Population Analytics" nav entry to app.py
[ ] Test: upload 10 segmentations, verify probability gradient
```

### S5: WebSocket Streaming Inference

```
[ ] Create src/serving/ws_inference.py
    [ ] FastAPI WebSocket endpoint /infer/stream
    [ ] Implement patch-based inference with progress events
    [ ] Stream completed regions as (patch_id, logits) tuples
[ ] Create src/ui/components/inference_progress.py
    [ ] Live progress ring that updates as patches complete
[ ] Test: WebSocket client connects, receives 10 events/sec during inference
```

---

This concludes the technical reference. Use PROJECT_CONTEXT.md for high-level overview and architectural decisions; use this document when implementing Phase 6 features or debugging specific components.
