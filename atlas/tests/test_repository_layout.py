"""Regressions for repository navigation without reading local credentials."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "verify_repository_layout",
    Path(__file__).resolve().parents[1] / "scripts/verify_repository_layout.py",
)
assert SPEC and SPEC.loader
LAYOUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAYOUT)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    workflow = tmp_path / ".github/workflows/pages.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "on:\n  push:\n    branches:\n      - main\n"
        "jobs:\n  deploy:\n    if: github.ref == 'refs/heads/main'\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# ATLAS\n", encoding="utf-8")
    return tmp_path


def verify(root: Path, tracked: set[str] | None = None) -> list[str]:
    return LAYOUT.verify_layout(
        root, tracked if tracked is not None else {"README.md"}, ("README.md",)
    )


def test_valid_minimal_layout(repository: Path) -> None:
    assert verify(repository) == []


@pytest.mark.parametrize("tracked", [set(), {"README.md"}])
def test_missing_index(repository: Path, tracked: set[str]) -> None:
    (repository / "README.md").unlink()
    assert "missing tracked navigation file: README.md" in verify(repository, tracked)


def test_broken_link(repository: Path) -> None:
    (repository / "README.md").write_text("[guide](missing.md)", encoding="utf-8")
    assert verify(repository) == ["broken local link: README.md: missing.md"]


def test_external_and_anchor_links_do_not_access_network(repository: Path) -> None:
    (repository / "README.md").write_text(
        "[web](https://example.org/x) [section](#x) [mail](mailto:a@example.org)",
        encoding="utf-8",
    )
    assert verify(repository) == []


def test_fenced_examples_are_not_links(repository: Path) -> None:
    (repository / "README.md").write_text(
        "```text\n[example](nonexistent.md)\n```", encoding="utf-8"
    )
    assert verify(repository) == []


@pytest.mark.parametrize("name", ["CAD model.stp", "modèle CAD.stp"])
def test_space_and_encoded_relative_links(repository: Path, name: str) -> None:
    (repository / name).write_text("reference", encoding="utf-8")
    (repository / "README.md").write_text(
        f"[CAD](<{name}>) [same]({name.replace(' ', '%20')})", encoding="utf-8"
    )
    assert verify(repository, {"README.md", name}) == []


def test_untracked_link_is_not_portable(repository: Path) -> None:
    (repository / "local.md").write_text("local", encoding="utf-8")
    (repository / "README.md").write_text("[local](local.md)", encoding="utf-8")
    assert verify(repository) == [
        "navigation target is not tracked: README.md: local.md"
    ]


def test_link_cannot_leave_repository(repository: Path) -> None:
    (repository / "README.md").write_text("[private](../.env)", encoding="utf-8")
    assert verify(repository) == ["navigation leaves repository: README.md: ../.env"]


@pytest.mark.parametrize("prefix", LAYOUT.RETIRED_PREFIXES)
def test_retired_runtime_tree_is_rejected(repository: Path, prefix: str) -> None:
    assert verify(repository, {"README.md", prefix + "old.py"}) == [
        f"retired runtime/utility path is tracked: {prefix}old.py"
    ]


@pytest.mark.parametrize("branches", ["", "      - main\n      - old-runtime\n"])
def test_pages_cannot_publish_old_runtime(repository: Path, branches: str) -> None:
    (repository / ".github/workflows/pages.yml").write_text(
        "on:\n  push:\n    branches:\n" + branches
        + "jobs:\n  deploy:\n    if: github.ref == 'refs/heads/main'\n",
        encoding="utf-8",
    )
    assert verify(repository) == ["Pages push branches must contain only main"]


def test_pages_manual_run_requires_main(repository: Path) -> None:
    (repository / ".github/workflows/pages.yml").write_text(
        "on:\n  push:\n    branches:\n      - main\n", encoding="utf-8"
    )
    assert verify(repository) == ["Pages manual deployment must be guarded to main"]
