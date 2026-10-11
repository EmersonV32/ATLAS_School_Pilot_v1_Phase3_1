"""The on-device test runner must not read the live environment file."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import dotenv
import dotenv.main
import pytest


def test_deployment_runner_skips_live_secrets_but_allows_synthetic_fixtures(
    tmp_path, monkeypatch
):
    script = Path(__file__).parents[1] / "scripts/run_deployment_pytest.py"
    spec = importlib.util.spec_from_file_location("isolated_runner", script)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    project = tmp_path / "project"
    synthetic = tmp_path / "synthetic/.env"
    reads = []
    def original(path, *_args, **_kwargs):
        reads.append(path)
        return True
    monkeypatch.setattr(dotenv, "load_dotenv", original)
    monkeypatch.setattr(dotenv.main, "load_dotenv", original)
    monkeypatch.setattr(runner, "ROOT", project)

    def fake_pytest(args):
        assert "no:cacheprovider" in args
        assert not dotenv.load_dotenv(project / ".env")
        assert not dotenv.main.load_dotenv(project / "subdir/../.env")
        assert not dotenv.load_dotenv()
        assert dotenv.load_dotenv(synthetic)
        return 0

    monkeypatch.setattr(pytest, "main", fake_pytest)
    assert runner.run_tests() == 0
    assert reads == [synthetic]
    assert dotenv.load_dotenv is original
    assert dotenv.main.load_dotenv is original
