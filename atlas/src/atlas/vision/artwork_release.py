"""Validate the contract between a vision model and an ATLAS content pack."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from atlas.rag.ingest import load_content_pack
from atlas.vision.yolo_detector import normalize_yolo_label


@dataclass
class ArtworkReleaseReport:
    pack_id: str
    artwork_count: int
    chunk_count: int
    model_label_count: int
    normalized_labels: list[str]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "pack_id": self.pack_id,
            "artwork_count": self.artwork_count,
            "chunk_count": self.chunk_count,
            "model_label_count": self.model_label_count,
            "normalized_labels": self.normalized_labels,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _extract_names(payload: Any) -> list[str]:
    if isinstance(payload, dict) and "names" in payload:
        payload = payload["names"]
    if isinstance(payload, dict):
        try:
            ordered = sorted(payload.items(), key=lambda pair: int(pair[0]))
        except (TypeError, ValueError):
            ordered = list(payload.items())
        return [str(value).strip() for _, value in ordered if str(value).strip()]
    if isinstance(payload, list):
        return [str(value).strip() for value in payload if str(value).strip()]
    raise ValueError("label file must contain a names list or index-to-name mapping")


def load_model_labels(path: str | Path) -> list[str]:
    label_path = Path(path)
    suffix = label_path.suffix.lower()
    text = label_path.read_text(encoding="utf-8")
    if suffix in {".yaml", ".yml"}:
        return _extract_names(yaml.safe_load(text))
    if suffix == ".json":
        return _extract_names(json.loads(text))
    if suffix == ".txt":
        return [line.strip() for line in text.splitlines() if line.strip()]
    raise ValueError("label file must be YAML, JSON, or newline-delimited TXT")


def validate_artwork_release(
    pack_dir: str | Path,
    label_file: str | Path,
    *,
    require_all_content_detectable: bool = False,
) -> ArtworkReleaseReport:
    pack_path = Path(pack_dir)
    pack = load_content_pack(pack_path)
    labels = load_model_labels(label_file)
    normalized = [normalize_yolo_label(label) for label in labels]
    artwork_ids = [artwork.artwork_id for artwork in pack.artworks]
    chunk_count = sum(len(artwork.chunks) for artwork in pack.artworks)
    report = ArtworkReleaseReport(
        pack_id=pack.manifest.pack_id,
        artwork_count=len(pack.artworks),
        chunk_count=chunk_count,
        model_label_count=len(labels),
        normalized_labels=normalized,
    )

    if len(set(pack.manifest.artwork_files)) != len(pack.manifest.artwork_files):
        report.errors.append("manifest contains duplicate artwork file paths")
    if len(set(artwork_ids)) != len(artwork_ids):
        report.errors.append("content pack contains duplicate artwork_id values")
    if len(set(normalized)) != len(normalized):
        report.errors.append("multiple model labels normalize to the same artwork_id")

    content_ids = set(artwork_ids)
    unknown_labels = sorted(set(normalized) - content_ids)
    if unknown_labels:
        report.errors.append(
            "model labels have no content entry: " + ", ".join(unknown_labels)
        )
    undetectable = sorted(content_ids - set(normalized))
    if undetectable:
        message = "content entries have no model label: " + ", ".join(undetectable)
        if require_all_content_detectable:
            report.errors.append(message)
        else:
            report.warnings.append(message)

    chunk_ids: list[str] = []
    for artwork in pack.artworks:
        if not artwork.chunks:
            report.errors.append(f"{artwork.artwork_id} has no retrieval chunks")
        if not artwork.sources:
            report.errors.append(f"{artwork.artwork_id} has no cited sources")
        missing_sources = artwork.validate_source_links()
        if missing_sources:
            report.errors.append(
                f"{artwork.artwork_id} has chunks with missing sources: "
                + ", ".join(missing_sources)
            )
        chunk_ids.extend(chunk.chunk_id for chunk in artwork.chunks)
        chunk_languages = {chunk.language for chunk in artwork.chunks}
        for language in artwork.supported_languages:
            if language not in chunk_languages:
                report.errors.append(
                    f"{artwork.artwork_id} declares {language.value} without a chunk"
                )
        for source in artwork.sources:
            try:
                date.fromisoformat(source.last_checked)
            except ValueError:
                report.errors.append(
                    f"{artwork.artwork_id} source {source.source_id} "
                    "has an invalid date"
                )
            if not source.url.startswith(("https://", "http://")):
                report.errors.append(
                    f"{artwork.artwork_id} source {source.source_id} has an invalid URL"
                )

    if len(set(chunk_ids)) != len(chunk_ids):
        report.errors.append("content pack contains duplicate chunk_id values")
    return report
