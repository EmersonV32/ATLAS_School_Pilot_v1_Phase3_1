"""Gemini LLM client for ATLAS.

Uses the Google Gen AI SDK (optional dependency).
Falls back gracefully with a clear error message if the package is not installed
or the API key is missing — dev mode should always use MockLLMClient instead.

Install when ready for real responses:
    pip install google-genai
"""
from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Iterator

logger = logging.getLogger(__name__)


class GeminiClient:
    """Calls Gemini via the supported Google Gen AI SDK."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        api_key_env: str = "GEMINI_API_KEY",
    ) -> None:
        self.model_name = model
        self._api_key_env = api_key_env
        self._api_key = api_key or os.getenv(api_key_env, "")
        self._client = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            from google import genai  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "google-genai is not installed.\n"
                "Run:  pip install google-genai\n"
                "Or use MockLLMClient for dev mode (no API key needed)."
            ) from exc

        if not self._api_key:
            raise RuntimeError(
                f"{self._api_key_env} is not set.\n"
                f"Set it with:  $env:{self._api_key_env}='your-key'  (PowerShell)\n"
                "Or use MockLLMClient for dev mode."
            )

        self._client = genai.Client(api_key=self._api_key)
        logger.info("GeminiClient: loaded model %s", self.model_name)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def warm_up(self) -> None:
        """Initialize the SDK client without making a billable model request."""
        self._ensure_client()

    @staticmethod
    def _generation_config(types, max_tokens: int, system_instruction: str | None):
        options = {
            "max_output_tokens": max_tokens,
            "system_instruction": system_instruction,
        }
        thinking_config = getattr(types, "ThinkingConfig", None)
        if thinking_config is not None:
            options["thinking_config"] = thinking_config(thinking_budget=0)
        return types.GenerateContentConfig(**options)

    @staticmethod
    def _conversation_text(messages: list[dict]) -> str:
        turns = [message for message in messages if message["role"] != "system"]
        if len(turns) == 1:
            return str(turns[0]["content"])
        labels = {"user": "VISITOR", "assistant": "ATLAS"}
        return "\n\n".join(
            f"{labels.get(turn['role'], turn['role'].upper())}: {turn['content']}"
            for turn in turns
        )

    def _log_usage(self, response) -> None:
        """Record provider usage metadata when Gemini supplies it, never prompts."""
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None)
        output_tokens = getattr(usage, "candidates_token_count", None)
        total_tokens = getattr(usage, "total_token_count", None)
        logger.info(
            "[Gemini] Usage "
            "[model=%s input_tokens=%s output_tokens=%s total_tokens=%s]",
            self.model_name,
            prompt_tokens if prompt_tokens is not None else "n/a",
            output_tokens if output_tokens is not None else "n/a",
            total_tokens if total_tokens is not None else "n/a",
        )

    def generate(self, messages: list[dict], max_tokens: int = 300) -> str:
        self._ensure_client()
        started = time.perf_counter()
        logger.info("[Gemini] Generation started [model=%s]", self.model_name)

        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        system_instruction = system_parts[0] if system_parts else None
        user_text = self._conversation_text(messages)

        from google.genai import types  # type: ignore[import]

        generation_config = self._generation_config(
            types,
            max_tokens,
            system_instruction,
        )
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=user_text,
            config=generation_config,
        )
        text = response.text or ""
        if not text.strip():
            raise RuntimeError("Gemini returned an empty response")
        logger.info(
            "[Timing] Gemini generation %.0f ms [chars=%d]",
            (time.perf_counter() - started) * 1000.0,
            len(text.strip()),
        )
        self._log_usage(response)
        return text.strip()

    def generate_stream(
        self,
        messages: list[dict],
        max_tokens: int = 300,
    ) -> Iterator[str]:
        """Yield text as Gemini produces it instead of waiting for completion."""
        self._ensure_client()
        started = time.perf_counter()
        first_chunk_logged = False
        produced_chars = 0
        logger.info("[Gemini] Stream started [model=%s]", self.model_name)
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        system_instruction = system_parts[0] if system_parts else None
        user_text = self._conversation_text(messages)

        from google.genai import types  # type: ignore[import]

        generation_config = self._generation_config(
            types,
            max_tokens,
            system_instruction,
        )
        response_stream = self._client.models.generate_content_stream(
            model=self.model_name,
            contents=user_text,
            config=generation_config,
        )
        produced_text = False
        last_response = None
        for response in response_stream:
            last_response = response
            text = response.text or ""
            if text:
                produced_text = True
                produced_chars += len(text)
                if not first_chunk_logged:
                    logger.info(
                        "[Timing] Gemini first token %.0f ms",
                        (time.perf_counter() - started) * 1000.0,
                    )
                    first_chunk_logged = True
                yield text
        if not produced_text:
            raise RuntimeError("Gemini returned an empty response stream")
        logger.info(
            "[Timing] Gemini stream complete %.0f ms [chars=%d]",
            (time.perf_counter() - started) * 1000.0,
            produced_chars,
        )
        if last_response is not None:
            self._log_usage(last_response)

    def identify_artwork(
        self,
        image_jpeg: bytes,
        candidates: dict[str, str],
    ) -> str | None:
        """Choose one configured artwork from an in-memory JPEG center crop."""
        self._ensure_client()
        if not image_jpeg or not candidates:
            return None

        from google.genai import types  # type: ignore[import]

        choices = "\n".join(
            f"- {artwork_id}: {title}" for artwork_id, title in candidates.items()
        )
        prompt = (
            "You are the visual fallback for ATLAS, a museum guide. Identify the "
            "main artwork centered in this image, even if it is a photograph or "
            "cropped reproduction. Choose exactly one candidate ID from the list "
            "below, or return unknown if none match. Return only the ID, with no "
            f"explanation.\n{choices}"
        )
        config_options = {
            "max_output_tokens": 64,
            "temperature": 0,
        }
        thinking_config = getattr(types, "ThinkingConfig", None)
        if thinking_config is not None:
            config_options["thinking_config"] = thinking_config(thinking_budget=0)
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(
                            data=image_jpeg,
                            mime_type="image/jpeg",
                        ),
                    ],
                )
            ],
            config=types.GenerateContentConfig(**config_options),
        )
        raw = (response.text or "").strip().lower()
        logger.info("Gemini visual fallback answer: %r", raw)
        answer = re.sub(r"[^a-z0-9_]+", "", raw)
        if answer in candidates:
            return answer

        id_matches = [
            artwork_id
            for artwork_id in candidates
            if re.search(
                rf"(?<![a-z0-9_]){re.escape(artwork_id)}(?![a-z0-9_])",
                raw,
            )
        ]
        if len(id_matches) == 1:
            return id_matches[0]

        normalised_titles = {
            re.sub(r"[^a-z0-9]+", "", title.lower()): artwork_id
            for artwork_id, title in candidates.items()
        }
        return normalised_titles.get(answer)
