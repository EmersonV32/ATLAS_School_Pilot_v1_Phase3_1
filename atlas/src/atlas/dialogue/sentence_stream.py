"""Turn arbitrary LLM token chunks into complete speakable sentences."""

from __future__ import annotations

import re


class SentenceAssembler:
    """Buffer partial tokens and emit only complete sentence boundaries."""

    _BOUNDARY = re.compile(r"[.!?]+[\"')\]]*(?:\s+|$)")

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, text: str) -> list[str]:
        self._buffer += text
        sentences: list[str] = []
        consumed = 0
        for match in self._BOUNDARY.finditer(self._buffer):
            candidate = self._buffer[consumed : match.end()].strip()
            if candidate:
                sentences.append(candidate)
            consumed = match.end()
        if consumed:
            self._buffer = self._buffer[consumed:]
        return sentences

    def flush(self) -> str:
        remainder = self._buffer.strip()
        self._buffer = ""
        return remainder
