"""Offline contract tests for OpenAI and Kimi request shaping."""

from __future__ import annotations

from atlas.dialogue.openai_compatible_client import OpenAICompatibleClient


def test_openai_uses_gpt5_completion_token_field_without_network() -> None:
    client = OpenAICompatibleClient(
        provider_name="OpenAI",
        model="gpt-5",
        api_key_env="OPENAI_API_KEY",
    )

    options = client._request_options(
        [
            {"role": "system", "content": "Use museum context."},
            {"role": "user", "content": "Who painted the Mona Lisa?"},
        ],
        120,
    )

    assert options["model"] == "gpt-5"
    assert options["max_completion_tokens"] == 120
    assert "max_tokens" not in options
    assert options["messages"][0]["role"] == "system"


def test_kimi_uses_compatible_token_field_without_network() -> None:
    client = OpenAICompatibleClient(
        provider_name="Kimi",
        model="kimi-k2.5",
        api_key_env="MOONSHOT_API_KEY",
        base_url="https://api.moonshot.cn/v1",
    )

    options = client._request_options(
        [{"role": "user", "content": "Explain this artwork."}], 90
    )

    assert options["model"] == "kimi-k2.5"
    assert options["max_tokens"] == 90
    assert "max_completion_tokens" not in options
