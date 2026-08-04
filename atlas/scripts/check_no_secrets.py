#!/usr/bin/env python3
"""Fail when staged/repository files contain obvious credential material."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".env", "wifi_secrets.h"}
PATTERNS = {
    "Google API key": re.compile(rb"AIza[0-9A-Za-z_-]{20,}"),
    "OpenAI-style secret": re.compile(rb"sk-[0-9A-Za-z_-]{20,}"),
    "private key": re.compile(rb"BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY"),
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        cwd=ROOT.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT.parent / line for line in result.stdout.splitlines() if line]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if not path.is_file() or path.name in SKIP or path.stat().st_size > 50_000_000:
            continue
        data = path.read_bytes()
        for label, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append(f"{label}: {path.relative_to(ROOT.parent)}")
    if findings:
        print("Potential secrets found:")
        print("\n".join(f"- {item}" for item in findings))
        return 1
    print("No obvious secrets found in tracked/unignored files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
