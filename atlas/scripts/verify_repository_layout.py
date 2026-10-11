#!/usr/bin/env python3
"""Check maintained navigation and prevent retired parallel runtime trees."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
NAVIGATION = (
    "README.md",
    "handoff/README.md",
    "handoff/START_HERE.md",
    "handoff/LLM_HANDOFF.md",
    "handoff/CURRENT_STATE.md",
    "handoff/REPOSITORY_MAP.md",
    "handoff/BRANCHES.md",
    "handoff/2026-10-11_REPOSITORY_CLEANUP.md",
    "archive/README.md",
    "resources/README.md",
    "website/README.md",
    "atlas/docs/README.md",
    "atlas/scripts/README.md",
    "atlas/models/README.md",
    "atlas/artwork-source/design/README.md",
)
RETIRED_PREFIXES = (
    "codex-final-handoff/",
    "archive/2026-06-22-phase4-patch/",
    "archive/2026-08-04-integration-utilities/",
    "archive/2026-08-04-jetson-recovery-utilities/",
    "archive/2026-08-16-live-hotfixes/",
    "archive/2026-08-28-pre-integrated-atlas/",
    "archive/2026-08-28-repository-transition/",
    "archive/2026-08-04-nationals-2026/atlas/",
    "archive/2026-08-04-nationals-2026/useless/",
)
LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>\n]+>|[^)\n]+)\)")


def verify_layout(
    root: Path, tracked: set[str], navigation: tuple[str, ...] = NAVIGATION
) -> list[str]:
    """Inspect only public index files; never traverse private/local state."""
    root = root.resolve()
    failures: list[str] = []
    for relative in sorted(tracked):
        if relative.startswith(RETIRED_PREFIXES):
            failures.append(f"retired runtime/utility path is tracked: {relative}")
    for relative in navigation:
        path = root / relative
        if relative not in tracked or not path.is_file():
            failures.append(f"missing tracked navigation file: {relative}")
            continue
        content = path.read_text(encoding="utf-8")
        # Examples inside fences are not rendered navigation links.
        content = re.sub(r"```[^\n]*\n.*?```", "", content, flags=re.DOTALL)
        for match in LINK.finditer(content):
            target = match.group(1)
            target = target[1:-1] if target.startswith("<") else target.split()[0]
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target_path = unquote(parsed.path)
            resolved = (path.parent / target_path).resolve()
            if not resolved.is_relative_to(root):
                failures.append(f"navigation leaves repository: {relative}: {target}")
                continue
            if not resolved.exists():
                failures.append(f"broken local link: {relative}: {target}")
                continue
            if (
                resolved.is_file()
                and resolved.relative_to(root).as_posix() not in tracked
            ):
                failures.append(
                    f"navigation target is not tracked: {relative}: {target}"
                )
    workflow = root / ".github/workflows/pages.yml"
    if not workflow.is_file():
        failures.append("missing Pages workflow")
    else:
        content = workflow.read_text(encoding="utf-8")
        branches = re.search(
            r"(?m)^    branches:\s*\n((?:      - [^\n]+\n)+)", content
        )
        names = re.findall(r"- (\S+)", branches.group(1)) if branches else []
        if names != ["main"]:
            failures.append("Pages push branches must contain only main")
        if "if: github.ref == 'refs/heads/main'" not in content:
            failures.append("Pages manual deployment must be guarded to main")
    return failures


def main() -> int:
    tracked = set(
        subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.split("\0")
    )
    failures = verify_layout(REPOSITORY_ROOT, tracked)
    if failures:
        print("Repository layout verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Repository layout verified: portable navigation and main-only Pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
