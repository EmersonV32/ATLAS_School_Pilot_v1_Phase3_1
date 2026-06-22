"""Abstract detector interface and ArtworkDetection dataclass."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ArtworkDetection:
    """Single-frame detection result."""
    artwork_id: str
    label: str
    confidence: float
    bbox: Optional[tuple] = None  # (x1,y1,x2,y2) normalised 0-1

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.65


class BaseDetector(ABC):
    """Swap-in interface for all detector implementations."""

    @abstractmethod
    def detect(self, frame: Any) -> Optional[ArtworkDetection]:
        """Return best detection or None if nothing recognised above threshold."""
        ...

    def warm_up(self) -> None:
        """Optional: pre-load model weights at startup."""
