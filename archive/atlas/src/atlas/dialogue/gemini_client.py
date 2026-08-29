"""Gemini LLM client for ATLAS.

Uses the google-generativeai SDK (optional dependency).
Falls back gracefully with a clear error message if the package is not installed
or the API key is missing — dev mode should always use MockLLMClient instead.

Install when ready for real responses:
    pip install google-generativeai
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class GeminiClient:
    """Calls Gemini via the google-generativeai SDK."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
    ) -> None:
        self.model_name = model
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._model = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            import google.generativeai as genai  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "google-generativeai is not installed.\n"
                "Run:  pip install google-generativeai\n"
                "Or use MockLLMClient for dev mode (no API key needed)."
            ) from exc

        if not self._api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set.\n"
                "Set it with:  $env:GEMINI_API_KEY='your-key'  (PowerShell)\n"
                "Or use MockLLMClient for dev mode."
            )

        genai.configure(api_key=self._api_key)
        self._model = genai.GenerativeModel(self.model_name)
        logger.info("GeminiClient: loaded model %s", self.model_name)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def generate(self, messages: list[dict], max_tokens: int = 300) -> str:
        self._ensure_model()

        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        user_parts = [m["content"] for m in messages if m["role"] == "user"]

        system_instruction = system_parts[0] if system_parts else None
        user_text = user_parts[0] if user_parts else ""

        import google.generativeai as genai  # already imported above, safe

        if system_instruction:
            model = genai.GenerativeModel(
                self.model_name, system_instruction=system_instruction
            )
        else:
            model = self._model  # type: ignore[assignment]

        generation_config = genai.types.GenerationConfig(max_output_tokens=max_tokens)
        response = model.generate_content(user_text, generation_config=generation_config)
        return response.text.strip()
