"""Real YOLO detector. Lazy-imports ultralytics — safe to import on any OS."""
from __future__ import annotations
import logging
from typing import Any, Optional
from .detector import ArtworkDetection, BaseDetector

logger = logging.getLogger(__name__)

_LABEL_TO_ID: dict[str, str] = {
    "starry night":     "starry_night",
    "mona lisa":        "mona_lisa",
    "tutankhamun mask": "tutankhamun_mask",
}


class YoloDetector(BaseDetector):
    """
    Requires:  pip install ultralytics
    model_path: path to your trained .pt weights file.
    Train via Roboflow on ATLAS content-pack images (see Phase 5 runbook).
    """

    def __init__(self, model_path: str, conf_threshold: float = 0.65) -> None:
        self._model_path = model_path
        self._conf_threshold = conf_threshold
        self._model = None

    def warm_up(self) -> None:
        try:
            from ultralytics import YOLO  # type: ignore
            self._model = YOLO(self._model_path)
            logger.info("YOLO model loaded from %s", self._model_path)
        except ImportError:
            logger.error("ultralytics not installed — run: pip install ultralytics")
            raise

    def detect(self, frame: Any) -> Optional[ArtworkDetection]:
        if self._model is None:
            self.warm_up()
        results = self._model(frame, verbose=False)
        best: Optional[ArtworkDetection] = None
        best_conf = 0.0
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf >= self._conf_threshold and conf > best_conf:
                    raw_label = r.names[int(box.cls[0])].lower()
                    artwork_id = _LABEL_TO_ID.get(raw_label, raw_label.replace(" ", "_"))
                    x1, y1, x2, y2 = (float(v) for v in box.xyxyn[0])
                    best_conf = conf
                    best = ArtworkDetection(
                        artwork_id=artwork_id,
                        label=raw_label.title(),
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                    )
        return best
