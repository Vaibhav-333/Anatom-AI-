"""
renderer_context.py
-------------------
Singleton initializer for PyVista headless (off-screen) rendering.

Must be imported before any other PyVista code runs. Safe to import multiple
times — initialization runs only once per process.

Platform strategy
-----------------
- Windows / macOS : pyvista.OFF_SCREEN = True  (no display needed)
- Linux / Docker  : starts Xvfb virtual framebuffer via pyvista.start_xvfb(),
                    then sets OFF_SCREEN = True

If PyVista is not installed the module degrades gracefully so that existing
Streamlit pages (which don't use PyVista) continue to load without error.
"""

from __future__ import annotations

import platform
import sys
import warnings

# ── Module-level state ────────────────────────────────────────────────────────
_initialized: bool = False
PYVISTA_AVAILABLE: bool = False


def _init_renderer() -> None:
    """Run once: configure PyVista for headless rendering."""
    global _initialized, PYVISTA_AVAILABLE

    if _initialized:
        return

    try:
        import pyvista as pv  # noqa: PLC0415

        PYVISTA_AVAILABLE = True

        # Always request off-screen rendering — this works on all platforms
        # and avoids any dependency on a live display / DISPLAY environment
        # variable.
        pv.OFF_SCREEN = True

        # On Linux (Docker / CI / headless server) also start a virtual
        # framebuffer.  This gives VTK an OpenGL context without a physical
        # display.  The call is safe to make even when Xvfb isn't required
        # (e.g., a pre-existing virtual display) because PyVista checks
        # internally before spawning a new server.
        if platform.system() == "Linux":
            try:
                pv.start_xvfb()
            except Exception as xvfb_err:  # noqa: BLE001
                warnings.warn(
                    f"Anatom AI: could not start Xvfb — "
                    f"PyVista will attempt software rendering. ({xvfb_err})",
                    RuntimeWarning,
                    stacklevel=2,
                )

        # Global theme: dark background, white foreground — matches the
        # Anatom AI Streamlit dark theme.
        pv.global_theme.background = "black"
        pv.global_theme.font.color = "white"
        pv.global_theme.anti_aliasing = "ssaa"  # software AA — always works

    except ImportError:
        PYVISTA_AVAILABLE = False
        warnings.warn(
            "Anatom AI: PyVista is not installed. "
            "Surgical 3D Viewer pages will be unavailable. "
            "Install with: pip install pyvista>=0.44.0 vtk>=9.3.0",
            ImportWarning,
            stacklevel=2,
        )

    finally:
        _initialized = True


def require_pyvista() -> None:
    """
    Raise ImportError with a friendly message if PyVista is not available.
    Call this at the top of any function that unconditionally needs PyVista.
    """
    if not PYVISTA_AVAILABLE:
        raise ImportError(
            "PyVista is required for the Surgical 3D Viewer. "
            "Install with: pip install pyvista>=0.44.0 vtk>=9.3.0"
        )


def get_pyvista():
    """
    Return the pyvista module, or raise ImportError if not installed.
    Preferred over bare `import pyvista` in feature modules so that the
    renderer_context initialization always runs first.
    """
    require_pyvista()
    import pyvista as pv  # noqa: PLC0415

    return pv


# Run initialization immediately on import.
_init_renderer()
