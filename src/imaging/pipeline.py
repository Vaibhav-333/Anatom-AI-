"""
pipeline.py — Preprocessing orchestrator with provenance logging.

Chains all preprocessing steps in the correct clinical order:

    1. QC (pre)          — reject corrupt / incomplete inputs
    2. Bias correction   — N4ITK (removes scanner artefacts)
    3. Registration      — align all modalities to T1ce
    4. Skull stripping   — remove non-brain tissue
    5. Resampling        — isotropic 1 mm³, canonical size
    6. Normalization     — per-modality z-score over brain voxels
    7. QC (post)         — verify outputs are sane
    8. Augmentation      — applied on-the-fly during training only

Each step records wall-clock time, input/output shapes, and QC status.
The full provenance log is written to a JSON file alongside the output.

Usage
-----
    from src.imaging.pipeline import PreprocessingPipeline

    pipeline = PreprocessingPipeline.from_yaml("config/preprocessing.yaml")
    subject  = pipeline.run(subject_dir="data/BraTS-001", output_dir="outputs/processed")
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .augmentor import AugmentationConfig, Augmentor
from .bias_corrector import BiasCorrector
from .loader import MRISubject, NIfTILoader
from .normalizer import Normalizer
from .registrar import ModalityRegistrar
from .resampler import Resampler
from .skull_stripper import SkullStripper

logger = logging.getLogger(__name__)


@dataclass
class StepRecord:
    """Provenance record for a single pipeline step."""
    step: str
    enabled: bool
    status: str = "skipped"          # "ok" | "skipped" | "failed"
    input_shape: Optional[tuple] = None
    output_shape: Optional[tuple] = None
    elapsed_sec: float = 0.0
    notes: str = ""


@dataclass
class ProvenanceLog:
    """Full provenance record for one subject run."""
    subject_id: str
    timestamp: str
    total_elapsed_sec: float = 0.0
    steps: List[StepRecord] = field(default_factory=list)
    qc_passed: bool = True
    error: Optional[str] = None


class PreprocessingPipeline:
    """
    End-to-end MRI preprocessing pipeline.

    Parameters
    ----------
    config : dict
        Parsed contents of preprocessing.yaml. Use from_yaml() class method
        to load from file.
    require_seg : bool
        Pass to NIfTILoader — set False for inference-only subjects.
    """

    def __init__(self, config: Dict[str, Any], require_seg: bool = True) -> None:
        self.cfg = config
        self.require_seg = require_seg
        self._configure_logging()

    @classmethod
    def from_yaml(cls, yaml_path: str | Path, require_seg: bool = True) -> "PreprocessingPipeline":
        """Load pipeline configuration from a YAML file."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path) as f:
            config = yaml.safe_load(f)
        logger.info("Loaded config from %s", path)
        return cls(config, require_seg=require_seg)

    def run(
        self,
        subject_dir: str | Path,
        output_dir: str | Path,
        apply_augmentation: bool = False,
    ) -> MRISubject:
        """
        Run the full preprocessing pipeline on a single BraTS subject directory.

        Parameters
        ----------
        subject_dir : path to the subject folder (containing 4 NIfTI modalities).
        output_dir  : where to save processed NIfTI files and the provenance log.
        apply_augmentation : if True, run augmentation as the final step.

        Returns
        -------
        Fully preprocessed MRISubject.

        Raises
        ------
        RuntimeError : wraps any step failure with the provenance log path.
        """
        subject_dir = Path(subject_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        pipeline_cfg = self.cfg.get("pipeline", {})
        t_pipeline_start = time.perf_counter()

        from datetime import datetime, timezone
        log = ProvenanceLog(
            subject_id=subject_dir.name,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        try:
            # ----------------------------------------------------------------
            # 1. Load
            # ----------------------------------------------------------------
            subject = self._timed_step(log, "load", self._load, subject_dir)

            # ----------------------------------------------------------------
            # 2. QC (pre)
            # ----------------------------------------------------------------
            if pipeline_cfg.get("run_qc_pre", True):
                subject = self._timed_step(log, "qc_pre", self._qc_pre, subject)

            # ----------------------------------------------------------------
            # 3. Bias correction
            # ----------------------------------------------------------------
            if pipeline_cfg.get("run_bias_correction", True):
                subject = self._timed_step(log, "bias_correction", self._bias_correct, subject)

            # ----------------------------------------------------------------
            # 4. Registration
            # ----------------------------------------------------------------
            if pipeline_cfg.get("run_registration", True):
                subject = self._timed_step(log, "registration", self._register, subject)

            # ----------------------------------------------------------------
            # 5. Skull stripping
            # ----------------------------------------------------------------
            brain_mask = None
            if pipeline_cfg.get("run_skull_strip", True):
                subject, brain_mask = self._timed_step(
                    log, "skull_strip", self._skull_strip, subject
                )

            # ----------------------------------------------------------------
            # 6. Resampling
            # ----------------------------------------------------------------
            if pipeline_cfg.get("run_resampling", True):
                subject = self._timed_step(log, "resampling", self._resample, subject)

            # ----------------------------------------------------------------
            # 7. Normalization
            # ----------------------------------------------------------------
            if pipeline_cfg.get("run_normalization", True):
                subject = self._timed_step(
                    log, "normalization", self._normalize, subject, brain_mask
                )

            # ----------------------------------------------------------------
            # 8. QC (post)
            # ----------------------------------------------------------------
            if pipeline_cfg.get("run_qc_post", True):
                self._timed_step(log, "qc_post", self._qc_post, subject)

            # ----------------------------------------------------------------
            # 9. Optional augmentation
            # ----------------------------------------------------------------
            if apply_augmentation:
                subject = self._timed_step(log, "augmentation", self._augment, subject)

        except Exception as exc:
            log.qc_passed = False
            log.error = str(exc)
            logger.error("Pipeline failed for '%s': %s", subject_dir.name, exc)
            self._save_provenance(log, output_dir)
            raise RuntimeError(
                f"Preprocessing failed for subject '{subject_dir.name}'. "
                f"See provenance log: {output_dir / 'provenance.json'}"
            ) from exc

        log.total_elapsed_sec = time.perf_counter() - t_pipeline_start
        logger.info(
            "Pipeline complete for '%s'  total=%.1fs",
            subject_dir.name, log.total_elapsed_sec,
        )

        # Save outputs
        self._save_subject(subject, output_dir)
        self._save_provenance(log, output_dir)

        return subject

    def run_batch(
        self,
        brats_root: str | Path,
        output_root: str | Path,
        pattern: str = "BraTS*",
    ) -> Dict[str, bool]:
        """
        Process all subjects matching pattern under brats_root.

        Returns dict of subject_id → success (True/False).
        """
        brats_root = Path(brats_root)
        output_root = Path(output_root)
        subject_dirs = sorted(brats_root.glob(pattern))

        results: Dict[str, bool] = {}
        for subject_dir in subject_dirs:
            if not subject_dir.is_dir():
                continue
            try:
                self.run(subject_dir, output_root / subject_dir.name)
                results[subject_dir.name] = True
            except Exception as exc:
                logger.error("Batch: subject '%s' failed — %s", subject_dir.name, exc)
                results[subject_dir.name] = False

        n_ok = sum(results.values())
        logger.info("Batch complete: %d/%d succeeded.", n_ok, len(results))
        return results

    # ------------------------------------------------------------------
    # Private step implementations
    # ------------------------------------------------------------------

    def _load(self, subject_dir: Path) -> MRISubject:
        loader = NIfTILoader(require_seg=self.require_seg)
        return loader.load(subject_dir)

    def _qc_pre(self, subject: MRISubject) -> MRISubject:
        from src.utils.qc_validator import QCValidator
        qc = QCValidator()
        report = qc.validate_pre(subject)
        if not report.passed:
            raise ValueError(f"Pre-pipeline QC failed: {report.failures}")
        return subject

    def _bias_correct(self, subject: MRISubject) -> MRISubject:
        bc_cfg = self.cfg.get("bias_correction", {})
        corrector = BiasCorrector(
            n_iterations=bc_cfg.get("n_iterations", [50, 50, 50, 50]),
            convergence_threshold=bc_cfg.get("convergence_threshold", 0.001),
        )
        return corrector.correct(subject)

    def _register(self, subject: MRISubject) -> MRISubject:
        reg_cfg = self.cfg.get("registration", {})
        registrar = ModalityRegistrar(
            reference_modality=reg_cfg.get("reference_modality", "t1ce"),
            interpolator=reg_cfg.get("interpolator", "linear"),
        )
        registered_subject, _ = registrar.register(subject)
        return registered_subject

    def _skull_strip(self, subject: MRISubject):
        ss_cfg = self.cfg.get("skull_strip", {})
        stripper = SkullStripper(
            threshold_method=ss_cfg.get("method", "otsu"),
            closing_radius=ss_cfg.get("closing_radius", 5),
            min_brain_coverage=ss_cfg.get("min_brain_coverage", 0.05),
        )
        return stripper.strip(subject)

    def _resample(self, subject: MRISubject) -> MRISubject:
        tgt_spacing = tuple(self.cfg.get("target_spacing", [1.0, 1.0, 1.0]))
        tgt_size = tuple(self.cfg.get("target_size", [240, 240, 155]))
        resampler = Resampler(target_spacing=tgt_spacing, target_size=tgt_size)
        return resampler.resample(subject)

    def _normalize(self, subject: MRISubject, brain_mask=None) -> MRISubject:
        clip = tuple(self.cfg.get("clip_percentiles", [1.0, 99.0]))
        method = self.cfg.get("normalization_method", "zscore")
        normalizer = Normalizer(method=method, clip_percentiles=clip, brain_mask=brain_mask)
        return normalizer.normalize(subject)

    def _qc_post(self, subject: MRISubject) -> MRISubject:
        from src.utils.qc_validator import QCValidator
        qc = QCValidator()
        report = qc.validate_post(subject)
        if not report.passed:
            raise ValueError(f"Post-pipeline QC failed: {report.failures}")
        return subject

    def _augment(self, subject: MRISubject) -> MRISubject:
        aug_cfg = self.cfg.get("augmentation", {})
        config = AugmentationConfig(
            flip_axial=aug_cfg.get("flips", {}).get("axial", True),
            flip_sagittal=aug_cfg.get("flips", {}).get("sagittal", True),
            flip_coronal=aug_cfg.get("flips", {}).get("coronal", True),
            rotation_range_deg=aug_cfg.get("rotation_range_deg", 15.0),
            elastic_enabled=aug_cfg.get("elastic", {}).get("enabled", True),
            elastic_sigma=aug_cfg.get("elastic", {}).get("sigma", 5.0),
            elastic_alpha=aug_cfg.get("elastic", {}).get("alpha", 40.0),
            gamma_range=tuple(aug_cfg.get("gamma_range", [0.7, 1.5])),
        )
        return Augmentor(config).augment(subject)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _timed_step(self, log: ProvenanceLog, step_name: str, fn, *args):
        """Run a pipeline step, recording timing and shape into the provenance log."""
        t_start = time.perf_counter()

        # Determine input shape (first MRISubject arg)
        input_shape = None
        for a in args:
            if isinstance(a, MRISubject):
                input_shape = a.shape
                break

        result = fn(*args)

        elapsed = time.perf_counter() - t_start

        # Output shape
        output_shape = None
        result_for_shape = result[0] if isinstance(result, tuple) else result
        if isinstance(result_for_shape, MRISubject):
            output_shape = result_for_shape.shape

        record = StepRecord(
            step=step_name,
            enabled=True,
            status="ok",
            input_shape=input_shape,
            output_shape=output_shape,
            elapsed_sec=round(elapsed, 3),
        )
        log.steps.append(record)
        logger.info("Step %-20s  %.2fs  %s → %s", step_name, elapsed, input_shape, output_shape)
        return result

    def _save_subject(self, subject: MRISubject, output_dir: Path) -> None:
        """Save all modalities as NIfTI files."""
        import nibabel as nib
        import numpy as np
        affine = np.eye(4)
        for name, volume in subject.modalities.items():
            nib.save(nib.Nifti1Image(volume, affine), str(output_dir / f"{subject.subject_id}_{name}.nii.gz"))
        if subject.seg is not None:
            nib.save(nib.Nifti1Image(subject.seg, affine), str(output_dir / f"{subject.subject_id}_seg.nii.gz"))
        logger.info("Saved processed volumes to %s", output_dir)

    def _save_provenance(self, log: ProvenanceLog, output_dir: Path) -> None:
        """Write provenance log as JSON."""
        log_dict = {
            "subject_id": log.subject_id,
            "timestamp": log.timestamp,
            "total_elapsed_sec": log.total_elapsed_sec,
            "qc_passed": log.qc_passed,
            "error": log.error,
            "steps": [
                {
                    "step": s.step,
                    "status": s.status,
                    "input_shape": list(s.input_shape) if s.input_shape else None,
                    "output_shape": list(s.output_shape) if s.output_shape else None,
                    "elapsed_sec": s.elapsed_sec,
                    "notes": s.notes,
                }
                for s in log.steps
            ],
        }
        prov_path = output_dir / "provenance.json"
        with open(prov_path, "w") as f:
            json.dump(log_dict, f, indent=2)
        logger.debug("Provenance log: %s", prov_path)

    def _configure_logging(self) -> None:
        level_str = self.cfg.get("pipeline", {}).get("log_level", "INFO")
        level = getattr(logging, level_str.upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s  %(name)-30s  %(levelname)-8s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
