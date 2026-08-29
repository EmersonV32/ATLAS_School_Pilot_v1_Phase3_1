"""Apply a minimal, reversible response-stability patch to the live Jetson."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path


root = Path(sys.argv[1]).resolve()
backup = Path(f"/tmp/atlas_response_hotfix_{datetime.now():%Y%m%d_%H%M%S}")
paths = {
    "container": root / "src/atlas/app/dependency_container.py",
    "runner": root / "src/atlas/pipeline/session_runner.py",
    "prompt": root / "src/atlas/dialogue/prompt_builder.py",
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
        paths["container"],
        "                stream_responses=self.settings.llm.streaming_enabled,\n",
        "                # One complete response per synthesis request prevents a\n"
        "                # mid-answer provider or voice change in both runtime paths.\n"
        "                stream_responses=False,\n",
    )
    replace_once(
        paths["runner"],
        "\n\n@dataclass\nclass SessionResult:\n",
        "\n\n_DEICTIC_ARTWORK_REFERENCE = re.compile(\n"
        "    r\"\\b(?:it|this|that|one|ceci|cela|ca|cette|esta|esto|questa|questo)\\b\",\n"
        "    re.IGNORECASE,\n"
        ")\n\n\ndef _needs_identified_artwork(query: str) -> bool:\n"
        "    normalized = unicodedata.normalize(\"NFKD\", str(query).casefold())\n"
        "    normalized = \"\".join(ch for ch in normalized if not unicodedata.combining(ch))\n"
        "    return bool(_DEICTIC_ARTWORK_REFERENCE.search(normalized))\n"
        "\n\n@dataclass\nclass SessionResult:\n",
    )
    replace_once(
        paths["runner"],
        "    ) -> list[dict]:\n        try:\n            rq = RetrievalQuery(\n",
        "    ) -> list[dict]:\n"
        "        # Do not let collection-wide ranking decide what 'it' means.\n"
        "        if artwork_id is None and _needs_identified_artwork(query):\n"
        "            logger.info(\"[RAG] Skipped ambiguous artwork reference without vision context\")\n"
        "            return []\n"
        "        try:\n            rq = RetrievalQuery(\n",
    )
    replace_once(
        paths["prompt"],
        '    "Use a warm, natural museum-guide style."\n)',
        '    "Use a warm, natural museum-guide style. "\n'
        '    "Do not infer which artwork words such as \'it\', \'this\', or \'that\' refer "\n'
        '    "to solely from retrieved context. If no artwork is identified, ask one "\n'
        '    "short clarification rather than guessing."\n)',
    )
    note = (
        "\n## 2026-08-16 - Live response stability hotfix\n\n"
        "- Forced one complete answer per TTS request for both device response paths.\n"
        "- Prevented collection-wide RAG from guessing an artwork for an ambiguous reference.\n"
        f"- Backup: `{backup}`.\n"
    )
    with paths["history"].open("a", encoding="utf-8") as handle:
        handle.write(note)
except Exception:
    for name, path in paths.items():
        saved = backup / f"{name}{path.suffix}"
        if saved.exists():
            shutil.copy2(saved, path)
    raise

print(f"Applied live response hotfix. Backup retained at: {backup}")
