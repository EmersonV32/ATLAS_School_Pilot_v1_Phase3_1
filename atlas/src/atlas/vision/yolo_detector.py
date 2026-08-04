"""Ultralytics YOLO artwork detector for the Jetson device runtime."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any

from .detector import ArtworkDetection, BaseDetector

logger = logging.getLogger(__name__)

_JETPACK_DIST_PACKAGES = Path("/usr/lib/python3.10/dist-packages")

_LABEL_ALIASES: dict[str, str] = {
    "mona_lisa": "mona_lisa",
    "monalisa": "mona_lisa",
    "starry_night": "starry_night",
    "starrynight": "starry_night",
    "pharaoh_mask": "tutankhamun_mask",
    "tutankhamun": "tutankhamun_mask",
    "tutankhamun_mask": "tutankhamun_mask",
    "mask_of_tutankhamun": "tutankhamun_mask",
    "objects": "tutankhamun_mask",
    "sunflowers": "sunflowers",
    "van_gogh_sunflowers": "sunflowers",
    "liberty_leading_the_people": "liberty_leading_the_people",
    "liberty": "liberty_leading_the_people",
    "girl_with_a_pearl_earring": "girl_with_a_pearl_earring",
    "girl_pearl_earring": "girl_with_a_pearl_earring",
    "great_wave_off_kanagawa": "great_wave_off_kanagawa",
    "the_great_wave": "great_wave_off_kanagawa",
    "great_wave": "great_wave_off_kanagawa",
}


def normalize_yolo_label(label: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return _LABEL_ALIASES.get(key, key)


def bbox_center_score(bbox: tuple[float, float, float, float]) -> float:
    """Return 1 at frame center and 0 near a normalized frame corner."""
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    distance = ((cx - 0.5) ** 2 + (cy - 0.5) ** 2) ** 0.5
    max_distance = (0.5**2 + 0.5**2) ** 0.5
    return max(0.0, min(1.0, 1.0 - distance / max_distance))


class YoloDetector(BaseDetector):
    def __init__(
        self,
        model_path: str,
        conf_threshold: float = 0.24,
        mask_conf_threshold: float = 0.45,
        center_weight: float = 0.55,
        image_size: int = 416,
        device: str | int | None = 0,
        fallback_model_path: str | None = None,
    ) -> None:
        self._model_path = model_path
        self._fallback_model_path = fallback_model_path
        self._conf_threshold = conf_threshold
        self._mask_conf_threshold = mask_conf_threshold
        self._center_weight = max(0.0, min(1.0, center_weight))
        self._image_size = image_size
        self._device = device
        self._model = None
        self._active_model_path: str | None = None

    @property
    def active_model_path(self) -> str | None:
        """Model currently serving detections, useful for preflight/telemetry."""
        return self._active_model_path

    @staticmethod
    def _make_jetpack_tensorrt_visible(model_path: str) -> None:
        if Path(model_path).suffix.lower() != ".engine":
            return
        system_path = str(_JETPACK_DIST_PACKAGES)
        if _JETPACK_DIST_PACKAGES.is_dir() and system_path not in sys.path:
            sys.path.append(system_path)

    def _load_and_warm(self, model_path: str):
        import numpy as np  # type: ignore
        from ultralytics import YOLO  # type: ignore

        self._make_jetpack_tensorrt_visible(model_path)
        model = YOLO(model_path, task="detect")
        model.predict(
            np.zeros((self._image_size, self._image_size, 3), dtype=np.uint8),
            imgsz=self._image_size,
            device=self._device,
            verbose=False,
        )
        return model

    def _fallback_available(self) -> bool:
        return bool(
            self._fallback_model_path
            and self._fallback_model_path != self._active_model_path
            and Path(self._fallback_model_path).is_file()
        )

    def _activate_fallback(self, exc: Exception) -> bool:
        if not self._fallback_available():
            return False
        logger.warning(
            "YOLO model %s failed (%s); loading fallback %s",
            self._active_model_path or self._model_path,
            exc,
            self._fallback_model_path,
        )
        self._model = self._load_and_warm(self._fallback_model_path)
        self._active_model_path = self._fallback_model_path
        return True

    def warm_up(self) -> None:
        if self._model is not None:
            return
        try:
            self._model = self._load_and_warm(self._model_path)
            self._active_model_path = self._model_path
            logger.info("YOLO loaded and warmed from %s", self._active_model_path)
        except ImportError:
            logger.error("ultralytics is not installed")
            raise
        except Exception as exc:
            if not self._activate_fallback(exc):
                raise

    def detect(self, frame: Any) -> ArtworkDetection | None:
        if frame is None:
            return None
        if self._model is None:
            self.warm_up()
        try:
            results = self._model.predict(
                frame,
                imgsz=self._image_size,
                device=self._device,
                verbose=False,
            )
        except Exception as exc:
            if not self._activate_fallback(exc):
                raise
            results = self._model.predict(
                frame,
                imgsz=self._image_size,
                device=self._device,
                verbose=False,
            )
        best: ArtworkDetection | None = None
        best_priority = -1.0
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                confidence = float(box.conf[0])
                raw_label = str(result.names[int(box.cls[0])])
                artwork_id = normalize_yolo_label(raw_label)
                threshold = (
                    self._mask_conf_threshold
                    if artwork_id == "tutankhamun_mask"
                    else self._conf_threshold
                )
                if confidence < threshold:
                    continue
                bbox = tuple(float(value) for value in box.xyxyn[0])
                center_score = bbox_center_score(bbox)
                priority = (
                    1.0 - self._center_weight
                ) * confidence + self._center_weight * center_score
                if priority <= best_priority:
                    continue
                best_priority = priority
                best = ArtworkDetection(
                    artwork_id=artwork_id,
                    label=raw_label.replace("_", " ").title(),
                    confidence=confidence,
                    bbox=bbox,
                    center_score=center_score,
                )
        return best
