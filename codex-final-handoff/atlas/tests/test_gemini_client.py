"""Offline tests for the supported Google Gen AI client adapter."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from atlas.dialogue.gemini_client import GeminiClient


def test_generate_uses_new_genai_client_without_network(monkeypatch):
    calls = {}

    class FakeConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(text=" Leonardo da Vinci. ")

    class FakeClient:
        def __init__(self, api_key):
            calls["api_key"] = api_key
            self.models = FakeModels()

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    genai_module.Client = FakeClient
    genai_module.types = SimpleNamespace(
        GenerateContentConfig=FakeConfig,
    )
    google_module.genai = genai_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)

    client = GeminiClient(model="gemini-test", api_key="private-test-key")
    answer = client.generate(
        [
            {
                "role": "system",
                "content": "Use museum context only.",
                "response_format": {
                    "mime_type": "application/json",
                    "schema": {"type": "object"},
                },
            },
            {"role": "user", "content": "Who painted this?"},
        ],
        max_tokens=42,
    )

    assert answer == "Leonardo da Vinci."
    assert calls["api_key"] == "private-test-key"
    assert calls["model"] == "gemini-test"
    assert calls["contents"] == "Who painted this?"
    assert calls["config"].max_output_tokens == 42
    assert calls["config"].system_instruction == "Use museum context only."
    assert calls["config"].response_mime_type == "application/json"
    assert calls["config"].response_schema == {"type": "object"}
    assert not hasattr(calls["config"], "thinking_config")


def test_generate_stream_yields_sdk_chunks_without_network(monkeypatch):
    calls = {}

    class FakeConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeModels:
        def generate_content_stream(self, **kwargs):
            calls.update(kwargs)
            return [
                SimpleNamespace(text="Leonardo da Vinci "),
                SimpleNamespace(text="painted it."),
            ]

    class FakeClient:
        def __init__(self, api_key):
            calls["api_key"] = api_key
            self.models = FakeModels()

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    genai_module.Client = FakeClient
    genai_module.types = SimpleNamespace(GenerateContentConfig=FakeConfig)
    google_module.genai = genai_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)

    client = GeminiClient(model="gemini-test", api_key="private-test-key")
    chunks = list(
        client.generate_stream(
            [
                {"role": "system", "content": "Use context."},
                {"role": "user", "content": "Who painted it?"},
            ],
            max_tokens=50,
        )
    )
    assert chunks == ["Leonardo da Vinci ", "painted it."]
    assert calls["model"] == "gemini-test"
    assert calls["config"].max_output_tokens == 50


def test_identify_artwork_sends_in_memory_jpeg_and_parses_id(monkeypatch):
    calls = {}

    class FakeConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakePart:
        @staticmethod
        def from_text(text):
            return ("text", text)

        @staticmethod
        def from_bytes(data, mime_type):
            return ("bytes", data, mime_type)

    class FakeContent:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(text="mona_lisa")

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    genai_module.Client = FakeClient
    genai_module.types = SimpleNamespace(
        Content=FakeContent,
        Part=FakePart,
        GenerateContentConfig=FakeConfig,
    )
    google_module.genai = genai_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)

    client = GeminiClient(model="gemini-test", api_key="private-test-key")
    artwork_id = client.identify_artwork(
        image_jpeg=b"\xff\xd8test-jpeg",
        candidates={"mona_lisa": "Mona Lisa", "starry_night": "The Starry Night"},
    )
    assert artwork_id == "mona_lisa"
    assert calls["model"] == "gemini-test"
    parts = calls["contents"][0].parts
    assert parts[1] == ("bytes", b"\xff\xd8test-jpeg", "image/jpeg")
    prompt = parts[0][1]
    assert "unique, strong visual match" in prompt
    assert "return unknown" in prompt
    assert not hasattr(calls["config"], "thinking_config")
