#!/usr/bin/env python3
"""Play ATLAS's short pre-listening cue through the configured headset."""

from atlas.app.dependency_container import build_container
from atlas.models.enums import RunMode


def main() -> None:
    container = build_container("config")
    container.settings.mode = RunMode.DEVICE
    try:
        tts = container.tts
        tts.warm_up()
        if not tts.cue():
            raise SystemExit("Listening cue playback failed")
        print("Listening cue playback succeeded")
    finally:
        container.close()


if __name__ == "__main__":
    main()
