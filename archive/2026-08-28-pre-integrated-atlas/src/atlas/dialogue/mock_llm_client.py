"""Deterministic mock LLM client for dev and test mode.

No network calls, no API key required. Same question always returns the same
response so tests are reproducible.
"""
from __future__ import annotations

import hashlib


_MOCK_RESPONSES = [
    "This remarkable work demonstrates the artist's mastery of light and composition.",
    "The painting was created during a pivotal period in the history of Western art.",
    "Notice how the use of color guides the viewer's eye across the canvas.",
    "The technique used here was considered innovative for its time and influenced many later artists.",
    "This piece reflects the cultural and historical tensions of the era in which it was made.",
    "The artist's brushwork reveals a deep understanding of form and movement.",
    "Look closely at the foreground — there are details here that reward careful attention.",
]


class MockLLMClient:
    """Returns a canned response deterministically keyed to the question hash."""

    def generate(self, messages: list[dict], max_tokens: int = 300) -> str:
        user_msg = next(
            (m["content"] for m in messages if m["role"] == "user"), ""
        )
        idx = int(hashlib.md5(user_msg.encode()).hexdigest(), 16) % len(_MOCK_RESPONSES)
        return f"[MOCK] {_MOCK_RESPONSES[idx]}"
