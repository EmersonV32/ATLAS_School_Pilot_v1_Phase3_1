#!/usr/bin/env python3
"""
ATLAS Phase 4 Patch Helper
Run this once to see the exact code to add to dependency_container.py and main.py.
It does NOT modify any files — it prints instructions only.
"""

CONTAINER_IMPORTS = """\
# --- Phase 4 imports (add at the top of dependency_container.py) ---
from atlas.vision.mock_detector import MockDetector
from atlas.vision.yolo_detector import YoloDetector
from atlas.audio.mock_stt import MockSTT
from atlas.audio.mock_tts import MockTTS
from atlas.audio.whisper_stt import WhisperSTT
from atlas.audio.piper_tts import PiperTTS
from atlas.hardware.mock_hardware import MockHardware
from atlas.hardware.ev3_hardware import EV3Hardware
from atlas.pipeline.session_runner import SessionRunner, make_retriever
"""

CONTAINER_METHODS = """\
# --- Phase 4 methods (add inside DependencyContainer class) ---

    def detector(self):
        if self._config.run_mode in (RunMode.DEVICE, RunMode.DEMO):
            return YoloDetector(
                model_path=self._config.yolo_model_path,
                conf_threshold=0.65,
            )
        return MockDetector()

    def stt(self):
        if self._config.run_mode in (RunMode.DEVICE, RunMode.DEMO):
            return WhisperSTT(model_size="small", device="cuda")
        return MockSTT()

    def tts(self):
        if self._config.run_mode in (RunMode.DEVICE, RunMode.DEMO):
            return PiperTTS(
                voice_en=self._config.piper_voice_en,
                voice_fr=self._config.piper_voice_fr,
            )
        return MockTTS()

    def hardware(self):
        if self._config.run_mode in (RunMode.DEVICE, RunMode.DEMO):
            return EV3Hardware(bt_address=self._config.ev3_bt_address)
        return MockHardware()

    def session_runner(self):
        return SessionRunner(
            detector=self.detector(),
            stt=self.stt(),
            tts=self.tts(),
            hardware=self.hardware(),
            dialogue_engine=self.dialogue_engine(),
            retriever=make_retriever(self.retriever()),
        )
"""

CONFIG_FIELDS = """\
# --- Phase 4 config fields (add to your Settings / config class) ---
# yolo_model_path: str = "models/atlas_yolo.pt"
# piper_voice_en: str = "voices/en_US-amy-medium.onnx"
# piper_voice_fr: str = "voices/fr_FR-mls-medium.onnx"
# ev3_bt_address: str = "00:16:53:XX:XX:XX"   # replace with your EV3 MAC
"""

MAIN_UPDATE = """\
# --- Updated main loop in app/main.py ---
# Replace your existing main loop with SessionRunner:

    runner = container.session_runner()
    import time
    while True:
        result = runner.run_once(frame=None)   # pass real camera frame in device mode
        if result.success:
            logger.info("Cycle OK: %s -> %.60s", result.detection.label, result.dialogue.answer_text)
        time.sleep(0.5)
"""

if __name__ == "__main__":
    print("=" * 64)
    print("ATLAS Phase 4 Patch — copy these blocks into your codebase")
    print("=" * 64)
    print("\n[1] ADD TO TOP OF dependency_container.py:")
    print(CONTAINER_IMPORTS)
    print("\n[2] ADD INSIDE DependencyContainer CLASS:")
    print(CONTAINER_METHODS)
    print("\n[3] ADD TO config/settings.py:")
    print(CONFIG_FIELDS)
    print("\n[4] UPDATE app/main.py:")
    print(MAIN_UPDATE)
    print("=" * 64)
    print("Done. No files were modified.")
