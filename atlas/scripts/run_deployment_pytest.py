"""Run deployment regressions without loading the live installation's .env."""

from __future__ import annotations

from pathlib import Path

import dotenv
import dotenv.main
import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_tests() -> int:
    protected = (ROOT / ".env").resolve()
    original = dotenv.load_dotenv
    original_main = dotenv.main.load_dotenv

    def isolated_dotenv(dotenv_path=None, *args, **kwargs):
        # Synthetic per-test .env fixtures still work; never discover/read live secrets.
        if dotenv_path is None or Path(dotenv_path).resolve() == protected:
            return False
        return original(dotenv_path, *args, **kwargs)

    dotenv.load_dotenv = isolated_dotenv
    dotenv.main.load_dotenv = isolated_dotenv
    try:
        return int(pytest.main(["-q", "-p", "no:cacheprovider"]))
    finally:
        dotenv.load_dotenv = original
        dotenv.main.load_dotenv = original_main


if __name__ == "__main__":
    raise SystemExit(run_tests())
