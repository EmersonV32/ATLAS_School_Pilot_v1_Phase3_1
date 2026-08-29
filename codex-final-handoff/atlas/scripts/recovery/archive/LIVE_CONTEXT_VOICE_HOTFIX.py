"""Apply a reversible live fix for follow-up artwork context and TTS provider locking."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path


root = Path(sys.argv[1]).resolve()
backup = Path(f"/tmp/atlas_context_voice_hotfix_{datetime.now():%Y%m%d_%H%M%S}")
paths = {
    "runner": root / "src/atlas/pipeline/session_runner.py",
    "fallback": root / "src/atlas/audio/fallback.py",
    "runtime_service": root / "src/atlas/dashboard/runtime_service.py",
    "history": root / "docs/PATCH_HISTORY.md",
}


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one match in {path.name}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


backup.mkdir(parents=True)
for name, path in paths.items():
    if path.exists():
        shutil.copy2(path, backup / f"{name}{path.suffix}")

try:
    replace_once(
        paths["runner"],
        '        self._preferred_profile = "adult_beginner"\n',
        '        self._preferred_profile = "adult_beginner"\n'
        '        self._last_artwork_id: str | None = None\n',
    )
    replace_once(
        paths["runner"],
        '    @property\n    def preferred_language(self) -> str:\n',
        '    def clear_conversation_context(self) -> None:\n'
        '        """Forget the prior artwork when a visitor session ends."""\n'
        '        self._last_artwork_id = None\n'
        '\n'
        '    @property\n    def preferred_language(self) -> str:\n',
    )
    replace_once(
        paths["runner"],
        '        artwork_id = detection.artwork_id if detection is not None else None\n'
        '        if detection is not None:\n',
        '        artwork_id = detection.artwork_id if detection is not None else self._last_artwork_id\n'
        '        if detection is not None:\n'
        '            self._last_artwork_id = detection.artwork_id\n'
        '        elif artwork_id is not None:\n'
        '            logger.info("[Vision] Reusing last artwork context [artwork_id=%s]", artwork_id)\n'
        '        if detection is not None:\n',
    )
    replace_once(
        paths["fallback"],
        '            if adapter is self.primary and self.fallback_ready:\n'
        '                self._locked_adapter = self.fallback\n'
        '                logger.warning(\n'
        '                    "[TTS] Locked primary failed before speech; response will use %s",\n'
        '                    type(self.fallback).__name__,\n'
        '                )\n'
        '                return self.speak(text, language)\n'
        '            return False\n',
        '            if adapter is self.primary:\n'
        '                logger.error(\n'
        '                    "[TTS] Cartesia failed before speech; local fallback suppressed "\n'
        '                    "for this response to preserve one voice"\n'
        '                )\n'
        '            return False\n',
    )
    replace_once(
        paths["fallback"],
        '            logger.warning(\n'
        '                "[TTS] Primary %s produced no audio; switching to %s",\n'
        '                type(self.primary).__name__,\n'
        '                type(self.fallback).__name__,\n'
        '            )\n'
        '            self.primary_ready = False\n',
        '            logger.error(\n'
        '                "[TTS] Primary %s produced no audio; fallback suppressed "\n'
        '                "for this response to preserve one voice",\n'
        '                type(self.primary).__name__,\n'
        '            )\n'
        '            return False\n',
    )
    replace_once(
        paths["runtime_service"],
        '        stopped = self.session_id\n'
        '        self.session_id = None\n',
        '        stopped = self.session_id\n'
        '        clear_context = getattr(self.container.session_runner, "clear_conversation_context", None)\n'
        '        if callable(clear_context):\n'
        '            clear_context()\n'
        '        self.session_id = None\n',
    )
    with paths["history"].open("a", encoding="utf-8") as handle:
        handle.write(
            "\n## 2026-08-16 - Follow-up context and strict response voice\n\n"
            "- Remember the last detected artwork for follow-up questions in the active visitor session.\n"
            "- Clear that context as soon as the session ends.\n"
            "- Suppress a mid-response Cartesia-to-Piper handoff; a failed Cartesia response now remains text-only.\n"
            f"- Backup: `{backup}`.\n"
        )
except Exception:
    for name, path in paths.items():
        saved = backup / f"{name}{path.suffix}"
        if saved.exists():
            shutil.copy2(saved, path)
    raise

print(f"Applied follow-up and strict-voice hotfix. Backup retained at: {backup}")
