"""
pyvista_renderer.py — NeuroRenderer: Clinical-grade 3D scene builder.

All PyVista rendering passes through this class. It is designed to be
completely headless (off-screen PNG export) — no VTK window ever opens.

Phase 1 capabilities
--------------------
- render_cortex()       : pial surface with sulcal-depth shading
- render_tumor_regions(): NCR / ED / ET sub-region meshes
- render_combined()     : full scene (cortex + tumour) in one call

Phase 2 additions
-----------------
- render_craniotomy()   : spherical clipping plane reveals tumour interior
- X-Ray mode            : ultra-low opacity, all structures visible
- Rotation presets      : axial / sagittal / coronal camera positions

Phase 3 additions
-----------------
- add_uncertainty_fog() : neon mist point cloud from MC Dropout entropy
- render_landmarks()    : labelled anatomical landmark spheres (brainstem etc.)

Usage
-----
    from src.ui.pyvista_renderer import NeuroRenderer
    renderer = NeuroRenderer(width=1200, height=900)
    png_bytes = renderer.render_combined(cortex_mesh, segmentation, voxel_spacing)
    st.image(png_bytes)
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── BraTS colour palette ──────────────────────────────────────────────────────
_TUMOR_CONFIG: Dict[int, Dict] = {
    1: {"name": "NCR",  "color": (220/255, 60/255,  60/255),  "opacity": 0.90},
    2: {"name": "ED",   "color": (240/255, 200/255, 30/255),  "opacity": 0.55},
    3: {"name": "ET",   "color": (60/255,  200/255, 220/255), "opacity": 0.95},
}

_CORTEX_COLOR    = (0.82, 0.71, 0.55)   # warm pinkish-tan — biological skin tone
_LANDMARK_COLORS = {
    "brainstem":       "orange",
    "left_ventricle":  "dodgerblue",
    "right_ventricle": "dodgerblue",
    "corpus_callosum": "mediumpurple",
    "tumor_centroid":  "red",
}

# Camera position presets (position, focal_point, view_up)
_CAMERA_PRESETS = {
    "default":  ((0.0, -500.0, 200.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "axial":    ((0.0, 0.0, 600.0),    (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    "sagittal": ((600.0, 0.0, 0.0),    (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "coronal":  ((0.0, -600.0, 0.0),   (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
}


@dataclass
class RenderParams:
    """Parameters controlling one render call."""
    mode: str = "standard"          # "standard" | "craniotomy" | "xray"
    clip_radius: float = 0.0        # 0 = no clipping; >0 = craniotomy sphere radius
    cortex_opacity: float = 0.22
    show_uncertainty_fog: bool = False
    show_landmarks: bool = False
    camera_preset: str = "default"
    background_color: str = "black"


class NeuroRenderer:
    """
    Off-screen PyVista renderer for the Anatom AI Surgical 3D Viewer.

    Parameters
    ----------
    width, height : int
        Screenshot resolution in pixels.
    """

    def __init__(self, width: int = 1200, height: int = 900) -> None:
        self.width = width
        self.height = height
        self._pv = None   # lazy import

    # ── Public API ────────────────────────────────────────────────────────────

    def render_combined(
        self,
        cortex_mesh,
        segmentation: np.ndarray,
        voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        params: Optional[RenderParams] = None,
        tumor_centroid: Optional[Tuple[float, float, float]] = None,
        uncertainty_fog=None,
        landmarks: Optional[Dict] = None,
        trajectories: Optional[List[Dict]] = None,
    ) -> bytes:
        """
        Build and render the full surgical scene. Returns PNG bytes.

        Parameters
        ----------
        cortex_mesh      : pyvista.PolyData from CortexExtractor.
        segmentation     : (H,W,D) int array — BraTS labels.
        voxel_spacing    : (sx,sy,sz) in mm.
        params           : RenderParams controlling display mode.
        tumor_centroid   : (x,y,z) mm — centre for craniotomy clipping.
        uncertainty_fog  : pyvista.PolyData point cloud (from uncertainty_3d).
        landmarks        : dict of name→(x,y,z) mm from LandmarkDetector.
        trajectories     : list of trajectory dicts from TrajectoryPlanner.

        Returns
        -------
        PNG image as bytes — pass directly to st.image().
        """
        pv = self._get_pv()
        if params is None:
            params = RenderParams()

        pl = pv.Plotter(
            off_screen=True,
            window_size=(self.width, self.height),
        )
        pl.set_background(params.background_color)

        # Attempt depth peeling for correct transparency; fall back gracefully
        try:
            pl.enable_depth_peeling(number_of_peels=4)
        except Exception:
            pl.enable_anti_aliasing("ssaa")

        # ── Cortex mesh ───────────────────────────────────────────────────
        if cortex_mesh is not None:
            self._add_cortex(pl, cortex_mesh, params)

        # ── Tumour sub-region meshes ──────────────────────────────────────
        tumor_meshes = self._build_tumor_meshes(segmentation, voxel_spacing)
        xray_mode = params.mode == "xray"
        for cls_idx, mesh in tumor_meshes.items():
            cfg = _TUMOR_CONFIG[cls_idx]
            opacity = 0.15 if xray_mode else cfg["opacity"]
            pl.add_mesh(
                mesh,
                color=cfg["color"],
                opacity=opacity,
                smooth_shading=True,
                ambient=0.35,
                diffuse=0.8,
                specular=0.4,
                specular_power=30,
                name=cfg["name"],
            )

        # ── Uncertainty fog (dual-layer neon mist) ────────────────────────
        if params.show_uncertainty_fog and uncertainty_fog is not None:
            self._add_uncertainty_fog_to_plotter(pl, uncertainty_fog)

        # ── Anatomical landmarks ───────────────────────────────────────────
        if params.show_landmarks and landmarks:
            self._add_landmarks(pl, landmarks)

        # ── Surgical trajectories ──────────────────────────────────────────
        if trajectories:
            self._add_trajectories(pl, trajectories)

        # ── Camera ────────────────────────────────────────────────────────
        pos, focal, up = _CAMERA_PRESETS.get(
            params.camera_preset, _CAMERA_PRESETS["default"]
        )
        # Auto-centre camera on the physical centre of the volume
        if cortex_mesh is not None:
            centre = np.array(cortex_mesh.center)
            focal = tuple(centre)
            dist = 500.0
            offset = np.array(pos) - np.array(_CAMERA_PRESETS["default"][1])
            offset_norm = offset / (np.linalg.norm(offset) + 1e-8)
            pos = tuple(centre + offset_norm * dist)

        pl.camera.position = pos
        pl.camera.focal_point = focal
        pl.camera.up = up
        pl.reset_camera()

        # ── Screenshot ────────────────────────────────────────────────────
        png_bytes = pl.screenshot(None, return_img=True)
        pl.close()

        # Convert numpy array to PNG bytes
        return _ndarray_to_png_bytes(png_bytes)

    def render_cortex_only(
        self,
        cortex_mesh,
        params: Optional[RenderParams] = None,
    ) -> bytes:
        """Render the cortical surface alone (Phase 0 validation render)."""
        pv = self._get_pv()
        if params is None:
            params = RenderParams()

        pl = pv.Plotter(off_screen=True, window_size=(self.width, self.height))
        pl.set_background("black")
        try:
            pl.enable_depth_peeling(number_of_peels=2)
        except Exception:
            pass

        self._add_cortex(pl, cortex_mesh, params)
        pl.reset_camera()
        png = pl.screenshot(None, return_img=True)
        pl.close()
        return _ndarray_to_png_bytes(png)

    def render_craniotomy(
        self,
        cortex_mesh,
        segmentation: np.ndarray,
        voxel_spacing: Tuple[float, float, float],
        tumor_centroid: Tuple[float, float, float],
        clip_radius: float,
        params: Optional[RenderParams] = None,
    ) -> bytes:
        """
        Render the Virtual Craniotomy view.

        A sphere of `clip_radius` mm centred on `tumor_centroid` clips away
        the cortex, revealing the tumour anatomy inside.

        Parameters
        ----------
        clip_radius : float
            0   = full cortex visible (no craniotomy).
            >0  = cortex clipped inside the sphere.
                  Grows from 0 to the tumour bounding radius for full reveal.
        """
        pv = self._get_pv()
        if params is None:
            params = RenderParams(mode="craniotomy")

        pl = pv.Plotter(off_screen=True, window_size=(self.width, self.height))
        pl.set_background("black")
        try:
            pl.enable_depth_peeling(number_of_peels=4)
        except Exception:
            pl.enable_anti_aliasing("ssaa")

        # ── Cortex: clip away the interior sphere ─────────────────────────
        if cortex_mesh is not None and clip_radius > 0:
            import vtk
            sphere_fn = vtk.vtkSphere()
            sphere_fn.SetCenter(*tumor_centroid)
            sphere_fn.SetRadius(float(clip_radius))

            clipper = vtk.vtkClipPolyData()
            clipper.SetInputData(cortex_mesh.GetOutputPort()
                                 if hasattr(cortex_mesh, "GetOutputPort")
                                 else cortex_mesh)
            # For pyvista PolyData we use pv's clip_surface method
            try:
                clipped_cortex = cortex_mesh.clip_surface(
                    pv.Sphere(radius=clip_radius, center=tumor_centroid),
                    invert=True,
                )
            except Exception:
                clipped_cortex = cortex_mesh   # fallback: no clipping
            self._add_cortex(pl, clipped_cortex, params)
        elif cortex_mesh is not None:
            self._add_cortex(pl, cortex_mesh, params)

        # ── Tumour sub-regions (always fully visible) ─────────────────────
        tumor_meshes = self._build_tumor_meshes(segmentation, voxel_spacing)
        for cls_idx, mesh in tumor_meshes.items():
            cfg = _TUMOR_CONFIG[cls_idx]
            pl.add_mesh(
                mesh,
                color=cfg["color"],
                opacity=cfg["opacity"],
                smooth_shading=True,
                ambient=0.4,
                diffuse=0.8,
                specular=0.5,
                specular_power=40,
                name=cfg["name"],
            )

        # Highlight craniotomy opening edge with a translucent ring
        if clip_radius > 0:
            ring = pv.Sphere(
                radius=clip_radius * 1.01,
                center=tumor_centroid,
                theta_resolution=64,
                phi_resolution=64,
            )
            pl.add_mesh(ring, color="white", opacity=0.08, style="wireframe")

        pl.reset_camera()
        png = pl.screenshot(None, return_img=True)
        pl.close()
        return _ndarray_to_png_bytes(png)

    def render_landmarks(
        self,
        base_image_bytes: bytes,
        landmarks: Dict[str, np.ndarray],
    ) -> bytes:
        """
        Render landmark spheres into a new scene and return PNG bytes.
        Typically called after render_combined when landmarks are toggled on.
        """
        pv = self._get_pv()
        pl = pv.Plotter(off_screen=True, window_size=(self.width, self.height))
        pl.set_background("black")
        self._add_landmarks(pl, landmarks)
        pl.reset_camera()
        png = pl.screenshot(None, return_img=True)
        pl.close()
        return _ndarray_to_png_bytes(png)

    def add_uncertainty_fog(
        self,
        entropy_map: np.ndarray,
        voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        segmentation: Optional[np.ndarray] = None,
        threshold_percentile: float = 78.0,
    ) -> object:
        """
        Build a pyvista.PolyData uncertainty fog cloud from an entropy map.

        Convenience wrapper around uncertainty_3d.build_uncertainty_fog().
        Returns the fog cloud, which can be passed to render_combined() as
        the `uncertainty_fog` argument.

        Parameters
        ----------
        entropy_map          : (H,W,D) float32 — per-voxel MC Dropout entropy.
        voxel_spacing        : (sx,sy,sz) in mm.
        segmentation         : optional BraTS label map — restricts fog to the
                               tumour boundary shell.
        threshold_percentile : entropy percentile cutoff (default 78 = top 22%).

        Returns
        -------
        pyvista.PolyData  with "entropy" and "layer" scalar arrays.
        """
        from src.ui.uncertainty_3d import build_uncertainty_fog
        return build_uncertainty_fog(
            entropy_map,
            voxel_spacing=voxel_spacing,
            threshold_percentile=threshold_percentile,
            segmentation=segmentation,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _add_cortex(self, pl, cortex_mesh, params: RenderParams) -> None:
        """Add the cortical surface to the plotter with sulcal shading."""
        pv = self._get_pv()

        xray = params.mode == "xray"
        opacity = 0.10 if xray else params.cortex_opacity

        if "curvature" in cortex_mesh.point_data.keys():
            # Sulcal depth shading: darker in sulci, brighter on gyri
            pl.add_mesh(
                cortex_mesh,
                scalars="curvature",
                cmap="bone",
                clim=[0.0, 1.0],
                opacity=opacity,
                smooth_shading=True,
                ambient=0.40,
                diffuse=0.70,
                specular=0.20,
                show_scalar_bar=False,
            )
        else:
            pl.add_mesh(
                cortex_mesh,
                color=_CORTEX_COLOR,
                opacity=opacity,
                smooth_shading=True,
                ambient=0.40,
                diffuse=0.70,
                specular=0.20,
            )

    def _build_tumor_meshes(
        self,
        segmentation: np.ndarray,
        voxel_spacing: Tuple[float, float, float],
    ) -> Dict[int, object]:
        """Extract pyvista meshes for each BraTS tumour sub-region."""
        from skimage.measure import marching_cubes
        pv = self._get_pv()

        meshes: Dict[int, object] = {}
        for cls_idx in [1, 2, 3]:
            mask = (segmentation == cls_idx).astype(np.float32)
            if mask.sum() < 8:
                continue

            padded = np.pad(mask, pad_width=1, mode="constant")
            try:
                verts, faces, _, _ = marching_cubes(
                    padded, level=0.5, spacing=voxel_spacing
                )
            except (ValueError, RuntimeError):
                continue

            verts = verts - np.array(voxel_spacing, dtype=np.float32)
            n_faces = len(faces)
            pv_faces = np.hstack(
                [np.full((n_faces, 1), 3, dtype=np.int32), faces.astype(np.int32)]
            ).ravel()

            mesh = pv.PolyData(verts.astype(np.float32), pv_faces)
            meshes[cls_idx] = mesh

        return meshes

    def _add_uncertainty_fog_to_plotter(self, pl, fog) -> None:
        """
        Add the dual-layer neon mist to an existing Plotter.

        Layer 0 (outer fog)  — sparse, low opacity, plasma colourmap.
        Layer 1 (dense core) — tight cluster near tumour edge, higher opacity.
        The two-pass approach creates a depth-graded glow without volumetric
        ray-casting, keeping render time under 3 s.
        """
        if fog is None or fog.n_points == 0:
            return

        # Split into layers using the "layer" scalar
        try:
            layers = fog.point_data["layer"]
            outer_mask = layers == 0
            dense_mask = layers == 1
        except KeyError:
            outer_mask = np.ones(fog.n_points, dtype=bool)
            dense_mask = np.zeros(fog.n_points, dtype=bool)

        # ── Outer fog layer ────────────────────────────────────────────────
        if outer_mask.any():
            outer_fog = fog.extract_points(outer_mask)
            pl.add_mesh(
                outer_fog,
                scalars="entropy",
                cmap="plasma",
                clim=[0.0, 1.0],
                point_size=3,
                render_points_as_spheres=True,
                opacity=0.22,
                show_scalar_bar=False,
                name="uncertainty_outer",
            )

        # ── Dense core layer ───────────────────────────────────────────────
        if dense_mask.any():
            dense_fog = fog.extract_points(dense_mask)
            pl.add_mesh(
                dense_fog,
                scalars="entropy",
                cmap="plasma",
                clim=[0.0, 1.0],
                point_size=4,
                render_points_as_spheres=True,
                opacity=0.58,
                show_scalar_bar=False,
                name="uncertainty_dense",
            )

    def _add_landmarks(self, pl, landmarks: Dict[str, np.ndarray]) -> None:
        """Add labelled sphere actors for anatomical landmarks."""
        pv = self._get_pv()
        for name, coords in landmarks.items():
            if coords is None:
                continue
            coords = np.asarray(coords, dtype=float)
            color = _LANDMARK_COLORS.get(name, "white")
            sphere = pv.Sphere(radius=4.0, center=coords)
            pl.add_mesh(sphere, color=color, opacity=0.85, smooth_shading=True)
            pl.add_point_labels(
                [coords],
                [name.replace("_", " ").title()],
                font_size=11,
                text_color=color,
                point_color=color,
                point_size=0,
                always_visible=True,
            )

    def _add_trajectories(self, pl, trajectories: List[Dict]) -> None:
        """Draw colour-coded surgical trajectory lines."""
        pv = self._get_pv()
        safety_colors = ["lime", "yellow", "tomato"]

        for i, traj in enumerate(trajectories[:3]):
            entry = np.asarray(traj["entry_point"], dtype=float)
            target = np.asarray(traj["target_point"], dtype=float)
            color = safety_colors[i]

            line = pv.Line(entry, target)
            pl.add_mesh(line, color=color, line_width=3, opacity=0.9)

            # Entry sphere
            pl.add_mesh(
                pv.Sphere(radius=3.0, center=entry),
                color=color, opacity=0.9, smooth_shading=True,
            )
            # Target sphere
            pl.add_mesh(
                pv.Sphere(radius=3.0, center=target),
                color="white", opacity=0.9, smooth_shading=True,
            )

    def _get_pv(self):
        """Return pyvista module (lazy import, after renderer_context init)."""
        if self._pv is None:
            from src.ui.renderer_context import get_pyvista
            self._pv = get_pyvista()
        return self._pv


# ── Utility ───────────────────────────────────────────────────────────────────

def _ndarray_to_png_bytes(arr: np.ndarray) -> bytes:
    """Convert an (H,W,3) uint8 numpy screenshot array to PNG bytes."""
    from PIL import Image
    img = Image.fromarray(arr.astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
