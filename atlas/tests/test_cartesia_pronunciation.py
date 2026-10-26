"""Synthetic pronunciation request checks; no cloud, credentials, or playback."""

from __future__ import annotations

import base64
import io
import json
import queue

import pytest

from atlas.audio.cartesia_tts import CartesiaTTS, build_cartesia_request
from atlas.dashboard.visitor_activation import session_introduction
from atlas.models.languages import ADMIN_LANGUAGE_OPTIONS


def _request(text, language="en", *, continue_=False):
    return build_cartesia_request(
        text=text,
        language=language,
        model="sonic-3.5",
        voice_id="synthetic-selected-voice",
        sample_rate=24000,
        context_id="synthetic-context",
        continue_=continue_,
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hi, I'm ATLAS.", "Hi, I'm Atlas."),
        ("ATLAS, meet ATLAS!", "Atlas, meet Atlas!"),
        ("ATLAS's guide; ATLAS’s voice.", "Atlas's guide; Atlas’s voice."),
        ("(ATLAS) — ATLAS-powered.", "(Atlas) — Atlas-powered."),
        ("AI and UNESCO guide ATLAS.", "AI and UNESCO guide Atlas."),
        ("Atlas and atlas.", "Atlas and atlas."),
        ("ATLASIAN ATLAS2 _ATLAS ATLAS_", "ATLASIAN ATLAS2 _ATLAS ATLAS_"),
        ("éATLAS ATLASé 中文ATLAS", "éATLAS ATLASé 中文ATLAS"),
        ("أطلس アトラス एटलस АТЛАС", "أطلس アトラス एटलस АТЛАС"),
        ("  ATLAS!\n", "  Atlas!\n"),
        ("", ""),
    ],
)
def test_only_complete_uppercase_brand_token_changes(text, expected):
    assert _request(text)["transcript"] == expected


@pytest.mark.parametrize("language", [item.code for item in ADMIN_LANGUAGE_OPTIONS])
def test_public_introduction_changes_only_at_cartesia_boundary(language):
    original = session_introduction(language)
    request = _request(original, language)

    assert request["transcript"] == original.replace("ATLAS", "Atlas")
    assert session_introduction(language) == original
    assert request["language"] == language
    assert request["model_id"] == "sonic-3.5"
    assert request["voice"] == {"mode": "id", "id": "synthetic-selected-voice"}
    assert request["context_id"] == "synthetic-context"
    assert request["output_format"] == {
        "container": "raw", "encoding": "pcm_s16le", "sample_rate": 24000,
    }
    assert not request["continue"]


def test_empty_terminal_frame_and_language_normalization_are_preserved():
    request = _request("", "fr-CA")
    assert request["transcript"] == ""
    assert request["continue"] is False
    assert request["language"] == "fr"


class _Socket:
    def __init__(self):
        self.requests = []
        self.messages = queue.Queue()

    def send(self, raw):
        request = json.loads(raw)
        self.requests.append(request)
        if not request["continue"]:
            self.messages.put({
                "type": "chunk", "context_id": request["context_id"],
                "data": base64.b64encode(b"\x00\x00").decode(),
            })
            self.messages.put({
                "type": "done", "context_id": request["context_id"],
            })

    def recv(self, timeout):
        return json.dumps(self.messages.get(timeout=min(timeout, 1)))


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("streaming", [False, True])
def test_whole_and_continuous_speech_use_same_normalization(
    monkeypatch, language, streaming,
):
    class Player:
        stdin = io.BytesIO()

        def poll(self):
            return None

    player = Player()
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.open_raw_player", lambda *_args: player,
    )
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.finish_raw_player", lambda *_args, **_kw: True,
    )
    socket = _Socket()
    tts = CartesiaTTS(voice_id="synthetic-selected-voice")
    tts._connection = socket
    original = session_introduction(language)
    if streaming:
        assert tts.begin_utterance(language)
        assert tts.speak_segment(original, language)
        assert tts.end_utterance()
        assert socket.requests[-1]["transcript"] == ""
        assert socket.requests[-1]["continue"] is False
    else:
        assert tts.speak(original, language)

    expected = original.replace("ATLAS", "Atlas")
    assert socket.requests[0]["transcript"].strip() == expected
    assert all(
        request["voice"] == {"mode": "id", "id": "synthetic-selected-voice"}
        and request["language"] == language
        for request in socket.requests
    )
    assert player.stdin.getvalue() == b"\x00\x00"
