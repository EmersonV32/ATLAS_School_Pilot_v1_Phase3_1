"""OpenAI-compatible LLM adapter for ATLAS.

This adapter supports OpenAI's Chat Completions API and compatible endpoints such
as Kimi. API keys remain environment variables and are never exposed through the
dashboard or logs.
"""
from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterator

logger = logging.getLogger(__name__)


class OpenAICompatibleClient:
    """Stream text from OpenAI or an OpenAI-compatible provider."""

    def __init__(
        self,
        *,
        provider_name: str,
        model: str,
        api_key_env: str,
        base_url: str | None = None,
        timeout_s: float = 8.0,
    ) -> None:
        self.provider_name = provider_name
        self.model_name = model
        self._api_key_env = api_key_env
        self._base_url = base_url or None
        self._timeout_s = timeout_s
        self._client = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "The OpenAI-compatible LLM adapter is not installed. "
                "Install the ATLAS llm extra before selecting this provider."
            ) from exc
        api_key = os.getenv(self._api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"{self.provider_name} API key is missing from {self._api_key_env}"
            )
        self._client = OpenAI(
            api_key=api_key,
            base_url=self._base_url,
            timeout=self._timeout_s,
        )
        logger.info(
            "[LLM] %s client ready [model=%s]",
            self.provider_name,
            self.model_name,
        )

    def warm_up(self) -> None:
        """Validate the SDK and credential without making a billable request."""
        self._ensure_client()

    @staticmethod
    def _messages(messages: list[dict]) -> list[dict[str, str]]:
        return [
            {
                "role": str(message.get("role", "user")),
                "content": str(message.get("content", "")),
            }
            for message in messages
            if str(message.get("content", "")).strip()
        ]

    def _request_options(self, messages: list[dict], max_tokens: int) -> dict:
        # Kimi's OpenAI-compatible endpoint uses max_tokens. OpenAI's current
        # Chat Completions endpoint uses max_completion_tokens for GPT-5.
        token_key = (
            "max_tokens"
            if self.provider_name.lower() == "kimi"
            else "max_completion_tokens"
        )
        return {
            "model": self.model_name,
            "messages": self._messages(messages),
            token_key: max_tokens,
        }

    @staticmethod
    def _content(response) -> str:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        content = getattr(getattr(choices[0], "message", None), "content", "")
        return str(content or "").strip()

    def generate(self, messages: list[dict], max_tokens: int = 300) -> str:
        self._ensure_client()
        started = time.perf_counter()
        logger.info(
            "[LLM] Generation started [provider=%s model=%s]",
            self.provider_name,
            self.model_name,
        )
        response = self._client.chat.completions.create(
            **self._request_options(messages, max_tokens)
        )
        text = self._content(response)
        if not text:
            raise RuntimeError(f"{self.provider_name} returned an empty response")
        logger.info(
            "[Timing] %s generation %.0f ms [model=%s chars=%d]",
            self.provider_name,
            (time.perf_counter() - started) * 1000.0,
            self.model_name,
            len(text),
        )
        return text

    def generate_stream(
        self,
        messages: list[dict],
        max_tokens: int = 300,
    ) -> Iterator[str]:
        self._ensure_client()
        started = time.perf_counter()
        first_chunk_logged = False
        produced_chars = 0
        logger.info(
            "[LLM] Stream started [provider=%s model=%s]",
            self.provider_name,
            self.model_name,
        )
        stream = self._client.chat.completions.create(
            **self._request_options(messages, max_tokens),
            stream=True,
        )
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            text = getattr(getattr(choices[0], "delta", None), "content", "")
            if not text:
                continue
            text = str(text)
            produced_chars += len(text)
            if not first_chunk_logged:
                logger.info(
                    "[Timing] %s first token %.0f ms [model=%s]",
                    self.provider_name,
                    (time.perf_counter() - started) * 1000.0,
                    self.model_name,
                )
                first_chunk_logged = True
            yield text
        if not produced_chars:
            raise RuntimeError(f"{self.provider_name} returned an empty response stream")
        logger.info(
            "[Timing] %s stream complete %.0f ms [model=%s chars=%d]",
            self.provider_name,
            (time.perf_counter() - started) * 1000.0,
            self.model_name,
            produced_chars,
        )
