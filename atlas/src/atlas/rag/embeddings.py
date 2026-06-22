"""Embedding interface with a real and a mock implementation.

The real implementation uses sentence-transformers (installed via
`pip install -e ".[rag]"`). The mock returns deterministic fake vectors so
the full pipeline runs in dev mode without any model download.

Usage (via dependency container):
    embedder = Embedder.from_settings(settings)
    vectors = embedder.embed(["text one", "text two"])
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

from atlas.config.settings import RagSettings


class EmbedderBase(ABC):
    """Abstract embedding interface."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one unit-length vector per input text."""

    @abstractmethod
    def embed_one(self, text: str) -> list[float]:
        """Convenience wrapper for a single string."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimensionality."""


class MockEmbedder(EmbedderBase):
    """Deterministic, dependency-free embedder for dev mode.

    Uses a bag-of-tokens hashing trick: each token is hashed into one of DIM
    buckets and its term frequency accumulated, then the vector is L2
    normalised. This means:
      - identical strings produce identical vectors, and
      - strings sharing words have higher cosine similarity.

    So dev-mode dense retrieval is actually meaningful (not random), while
    still requiring no model download. Real semantic quality comes from
    SentenceTransformerEmbedder via `pip install -e ".[rag]"`.
    """

    DIM = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_embed(t) for t in texts]

    def embed_one(self, text: str) -> list[float]:
        return self._hash_embed(text)

    @property
    def dimension(self) -> int:
        return self.DIM

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [t for t in "".join(
            c.lower() if c.isalnum() else " " for c in text
        ).split() if t]

    @staticmethod
    def _hash_embed(text: str) -> list[float]:
        vec = [0.0] * MockEmbedder.DIM
        for token in MockEmbedder._tokens(text):
            h = int(hashlib.sha1(token.encode()).hexdigest(), 16)
            idx = h % MockEmbedder.DIM
            sign = 1.0 if (h >> 8) & 1 else -1.0  # signed hashing reduces collisions
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class SentenceTransformerEmbedder(EmbedderBase):
    """Real embedder backed by sentence-transformers.

    Lazy-loads the model on first call so import is fast even if the library
    is installed. Raises ImportError with a clear message if the rag extra
    was not installed.
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None  # loaded on first use

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers is not installed. "
                    'Run: pip install -e ".[rag]"'
                ) from exc
            self._model = SentenceTransformer(self._model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._load()
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        self._load()
        return self._model.get_sentence_embedding_dimension()


def make_embedder(settings: RagSettings, *, mock: bool = False) -> EmbedderBase:
    """Factory: return MockEmbedder for dev/test, real embedder otherwise."""
    if mock:
        return MockEmbedder()
    return SentenceTransformerEmbedder(settings.embedding_model)
