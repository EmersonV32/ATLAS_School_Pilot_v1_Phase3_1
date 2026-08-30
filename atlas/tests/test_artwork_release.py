from pathlib import Path

from atlas.vision.artwork_release import (
    load_model_labels,
    validate_artwork_release,
)

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data" / "content_packs" / "demo_pack"
LABELS = ROOT / "config" / "artwork_labels.yaml"


def test_current_artwork_release_contract_is_complete() -> None:
    report = validate_artwork_release(
        PACK,
        LABELS,
        require_all_content_detectable=True,
    )

    assert report.valid, report.errors
    assert report.artwork_count == 7
    assert report.model_label_count == 7
    assert not report.warnings


def test_unknown_model_label_fails_validation(tmp_path: Path) -> None:
    labels = tmp_path / "data.yaml"
    labels.write_text("names: [mona_lisa, imaginary_work]\n", encoding="utf-8")

    report = validate_artwork_release(PACK, labels)

    assert not report.valid
    assert "imaginary_work" in " ".join(report.errors)


def test_roboflow_index_mapping_is_loaded_in_order(tmp_path: Path) -> None:
    labels = tmp_path / "data.yaml"
    labels.write_text("names:\n  1: Mona Lisa\n  0: The Great Wave\n", encoding="utf-8")

    assert load_model_labels(labels) == ["The Great Wave", "Mona Lisa"]
