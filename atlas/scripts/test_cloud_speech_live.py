#!/usr/bin/env python3
"""Run one low-usage Deepgram/Cartesia round trip on the Shokz headset."""

from __future__ import annotations

import argparse
import time

from atlas.audio.cartesia_tts import CartesiaTTS
from atlas.audio.deepgram_stt import DeepgramSTT
from atlas.config.loader import load_settings

PROMPTS = {
    "en": (
        "Cloud speech test. After the signal, please say: "
        "Who painted the Mona Lisa?"
    ),
    "fr": (
        "Test de parole Atlas. Apres le signal, dites : "
        "Qui a peint la Joconde ?"
    ),
}

CONFIRMATIONS = {
    "en": "Thank you. The cloud speech round trip is complete.",
    "fr": "Merci. Le test de parole infonuagique est termine.",
}


def _format_tts_timing(tts: CartesiaTTS) -> str:
    first_audio = (
        "n/a"
        if tts.last_first_audio_ms is None
        else f"{tts.last_first_audio_ms:.0f} ms"
    )
    total = "n/a" if tts.last_total_ms is None else f"{tts.last_total_ms:.0f} ms"
    return f"first_audio={first_audio}, total={total}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=sorted(PROMPTS), default="fr")
    parser.add_argument("--listen-seconds", type=float, default=12.0)
    args = parser.parse_args()

    settings = load_settings("config")
    speech = settings.speech
    hardware = settings.hardware
    stt = DeepgramSTT(
        api_key_env=speech.deepgram_api_key_env,
        model=speech.deepgram_model,
        # This benchmark already knows the requested language. Locking Nova-3
        # to it measures the path ATLAS should use after language discovery.
        language=args.language,
        input_device_name=hardware.headset_name,
        sample_rate=hardware.audio_sample_rate,
        channels=hardware.audio_channels,
        endpointing_ms=speech.deepgram_endpointing_ms,
        vad_threshold=speech.silero_threshold,
        min_speech_ms=speech.silero_min_speech_ms,
        min_silence_ms=speech.silero_min_silence_ms,
        pre_roll_ms=speech.silero_pre_roll_ms,
        final_timeout_s=speech.deepgram_final_timeout_s,
        silero_model_path=speech.silero_model_path,
        keyterms=speech.deepgram_keyterms,
    )
    tts = CartesiaTTS(
        api_key_env=speech.cartesia_api_key_env,
        model=speech.cartesia_model,
        voice_id=speech.cartesia_voice_id,
        api_version=speech.cartesia_api_version,
        output_device_name=hardware.headset_name,
        sample_rate=speech.cartesia_sample_rate,
        response_timeout_s=speech.cartesia_response_timeout_s,
    )

    try:
        print("[Live] Preparing Deepgram, Silero, Cartesia, and Shokz...")
        stt.warm_up()
        tts.warm_up()

        if not tts.speak(PROMPTS[args.language], language=args.language):
            raise RuntimeError("Cartesia prompt did not play")
        print(f"[Timing] Cartesia prompt: {_format_tts_timing(tts)}")

        stt.prepare_listen()
        tts.cue()
        started = time.perf_counter()
        transcript = stt.listen(duration_s=args.listen_seconds)
        wall_ms = (time.perf_counter() - started) * 1000.0
        if transcript is None:
            raise RuntimeError("Silero did not detect speech")
        print(
            "[Heard] "
            f"language={transcript.language}, confidence={transcript.confidence:.1%}, "
            f"text={transcript.text}"
        )
        print(
            "[Timing] Deepgram question: "
            f"adapter={transcript.duration_ms:.0f} ms, wall={wall_ms:.0f} ms"
        )

        if not tts.speak(CONFIRMATIONS[args.language], language=args.language):
            raise RuntimeError("Cartesia confirmation did not play")
        print(f"[Timing] Cartesia confirmation: {_format_tts_timing(tts)}")
        print("[Live] Cloud speech round trip passed.")
        return 0
    finally:
        stt.close()
        tts.close()


if __name__ == "__main__":
    raise SystemExit(main())
