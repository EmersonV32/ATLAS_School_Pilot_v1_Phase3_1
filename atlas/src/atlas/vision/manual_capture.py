"""Privacy-conscious manual artwork identification from an in-memory frame."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .detector import ArtworkDetection

_CAPTURE_PHRASES = (
    "capture this artwork",
    "capture the artwork",
    "identify this artwork",
    "capture cette oeuvre",
    "identifie cette oeuvre",
    "photographie cette oeuvre",
    "captura esta obra",
    "identifica esta obra",
    "cattura quest opera",
    "identifica quest opera",
    "拍攝這件作品",
    "拍下這幅畫",
    "識別這件作品",
)


def _normalise_text(text: str) -> str:
    text = text.replace("œ", "oe").replace("Œ", "OE")
    text = text.replace("æ", "ae").replace("Æ", "AE")
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def is_capture_command(text: str) -> bool:
    """Recognise the explicit command in every supported spoken language."""
    if any(phrase in text for phrase in _CAPTURE_PHRASES if not phrase.isascii()):
        return True
    normalised = _normalise_text(text)
    return any(
        phrase in normalised for phrase in _CAPTURE_PHRASES if phrase.isascii()
    )


def center_crop(frame: Any, ratio: float) -> Any:
    """Return the centered square-ish region used for visual identification."""
    if frame is None or not hasattr(frame, "shape") or len(frame.shape) < 2:
        raise ValueError("manual capture requires an image frame")
    ratio = max(0.25, min(1.0, ratio))
    height, width = frame.shape[:2]
    crop_width = max(1, round(width * ratio))
    crop_height = max(1, round(height * ratio))
    x1 = (width - crop_width) // 2
    y1 = (height - crop_height) // 2
    return frame[y1 : y1 + crop_height, x1 : x1 + crop_width]


class ManualArtworkCapture:
    """Encode a center crop in memory and ask a vision-capable LLM to identify it."""

    def __init__(
        self,
        client,
        candidates: dict[str, str],
        crop_ratio: float = 0.70,
        jpeg_quality: int = 85,
    ) -> None:
        self._client = client
        self._candidates = dict(candidates)
        self._crop_ratio = max(0.25, min(1.0, crop_ratio))
        self._jpeg_quality = max(50, min(95, jpeg_quality))

    def identify(self, frame: Any) -> ArtworkDetection | None:
        if frame is None or not self._candidates:
            return None

        import cv2  # type: ignore

        crop = center_crop(frame, self._crop_ratio)
        ok, encoded = cv2.imencode(
            ".jpg",
            crop,
            [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality],
        )
        if not ok:
            raise RuntimeError("could not encode manual artwork capture")

        artwork_id = self._client.identify_artwork(
            image_jpeg=encoded.tobytes(),
            candidates=self._candidates,
        )
        if artwork_id not in self._candidates:
            return None

        margin = (1.0 - self._crop_ratio) / 2.0
        return ArtworkDetection(
            artwork_id=artwork_id,
            label=self._candidates[artwork_id],
            confidence=1.0,
            bbox=(margin, margin, 1.0 - margin, 1.0 - margin),
            center_score=1.0,
            source="manual_capture",
            stable=True,
        )
