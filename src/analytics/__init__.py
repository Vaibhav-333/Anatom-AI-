"""
src/analytics — Phase 3: Clinical Analytics

Modules
-------
volumetrics   : Tumor sub-region volume calculation in mm³ (NCR, ED, ET, WT, TC).
explainability: Monte Carlo Dropout uncertainty maps and 3D Grad-CAM saliency (requires torch).
longitudinal  : Registration-free growth tracking and RANO criteria assessment.
"""

from .volumetrics import VolumetricAnalyzer, VolumetricResult
from .longitudinal import LongitudinalTracker, LongitudinalReport

__all__ = [
    "VolumetricAnalyzer",
    "VolumetricResult",
    "GradCAM3D",
    "UncertaintyEstimator",
    "UncertaintyResult",
    "LongitudinalTracker",
    "LongitudinalReport",
]

# Lazy imports for torch-dependent explainability symbols — only loaded on access.
_lazy = {
    "GradCAM3D": "explainability",
    "UncertaintyEstimator": "explainability",
    "UncertaintyResult": "explainability",
}


def __getattr__(name: str):
    if name in _lazy:
        import importlib
        mod = importlib.import_module(f".{_lazy[name]}", package=__name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
