import io, os

CONTAINER = os.path.join("src", "atlas", "app", "dependency_container.py")
MAIN = os.path.join("src", "atlas", "app", "main.py")

EDITS = {
    CONTAINER: [
        # 1. Add cache slots in __init__ next to the existing ones
        (
            "        self._retriever = None\n"
            "        self._dialogue_engine = None",
            "        self._retriever = None\n"
            "        self._dialogue_engine = None\n"
            "        self._vision_detector = None\n"
            "        self._stt = None\n"
            "        self._tts = None\n"
            "        self._hardware = None\n"
            "        self._session_runner = None",
        ),
        # 2. Add Phase 4 properties right before the extension-points comment block
        (
            "    # --- Extension points (filled in later phases) ----------------------",
            "    # --- Phase 4: perception, speech, hardware, pipeline ---------------\n"
            "    @property\n"
            "    def vision_detector(self):\n"
            "        if self._vision_detector is None:\n"
            "            if self.settings.mode in (RunMode.DEVICE, RunMode.DEMO):\n"
            "                from atlas.vision.yolo_detector import YoloDetector\n"
            "                # TODO(jetson): add yolo_model_path to HardwareSettings\n"
            "                self._vision_detector = YoloDetector(\n"
            "                    model_path=\"models/atlas_yolo.pt\",\n"
            "                    conf_threshold=0.65,\n"
            "                )\n"
            "            else:\n"
            "                from atlas.vision.mock_detector import MockDetector\n"
            "                self._vision_detector = MockDetector()\n"
            "        return self._vision_detector\n"
            "\n"
            "    @property\n"
            "    def stt(self):\n"
            "        if self._stt is None:\n"
            "            if self.settings.mode in (RunMode.DEVICE, RunMode.DEMO):\n"
            "                from atlas.audio.whisper_stt import WhisperSTT\n"
            "                self._stt = WhisperSTT(model_size=\"small\", device=\"cuda\")\n"
            "            else:\n"
            "                from atlas.audio.mock_stt import MockSTT\n"
            "                self._stt = MockSTT()\n"
            "        return self._stt\n"
            "\n"
            "    @property\n"
            "    def tts(self):\n"
            "        if self._tts is None:\n"
            "            if self.settings.mode in (RunMode.DEVICE, RunMode.DEMO):\n"
            "                from atlas.audio.piper_tts import PiperTTS\n"
            "                # TODO(jetson): add piper_voice_en / piper_voice_fr to HardwareSettings\n"
            "                self._tts = PiperTTS(\n"
            "                    voice_en=\"voices/en_US-amy-medium.onnx\",\n"
            "                    voice_fr=\"voices/fr_FR-mls-medium.onnx\",\n"
            "                )\n"
            "            else:\n"
            "                from atlas.audio.mock_tts import MockTTS\n"
            "                self._tts = MockTTS()\n"
            "        return self._tts\n"
            "\n"
            "    @property\n"
            "    def hardware(self):\n"
            "        if self._hardware is None:\n"
            "            if self.settings.mode in (RunMode.DEVICE, RunMode.DEMO):\n"
            "                from atlas.hardware.ev3_hardware import EV3Hardware\n"
            "                # TODO(jetson): add ev3_bt_address to HardwareSettings\n"
            "                self._hardware = EV3Hardware(bt_address=\"00:16:53:XX:XX:XX\")\n"
            "            else:\n"
            "                from atlas.hardware.mock_hardware import MockHardware\n"
            "                self._hardware = MockHardware()\n"
            "        return self._hardware\n"
            "\n"
            "    @property\n"
            "    def session_runner(self):\n"
            "        if self._session_runner is None:\n"
            "            from atlas.pipeline.session_runner import SessionRunner, make_retriever\n"
            "            self._session_runner = SessionRunner(\n"
            "                detector=self.vision_detector,\n"
            "                stt=self.stt,\n"
            "                tts=self.tts,\n"
            "                hardware=self.hardware,\n"
            "                dialogue_engine=self.dialogue_engine,\n"
            "                retriever=make_retriever(self.retriever),\n"
            "            )\n"
            "        return self._session_runner\n"
            "\n"
            "    # --- Extension points (filled in later phases) ----------------------",
        ),
    ],
    MAIN: [
        # 3. Add a --run flag
        (
            "    parser.add_argument(\n"
            "        \"--config-dir\", default=\"config\", help=\"Path to the config directory\"\n"
            "    )",
            "    parser.add_argument(\n"
            "        \"--config-dir\", default=\"config\", help=\"Path to the config directory\"\n"
            "    )\n"
            "    parser.add_argument(\n"
            "        \"--run\", type=int, default=0, metavar=\"N\",\n"
            "        help=\"Run N real pipeline cycles via SessionRunner instead of the scripted walkthrough\",\n"
            "    )",
        ),
        # 4. Branch into the pipeline loop when --run is given
        (
            "    session_id = new_session_id()\n"
            "    sm = StateMachine(session_id=session_id, logger=container.logger)\n"
            "    print(f\"\\nSession {session_id} - scripted dev walkthrough:\")\n"
            "    _scripted_dev_walkthrough(sm)\n"
            "    print(\"\\nDone. Transitions logged to\", settings.paths.logs_dir)",
            "    if args.run > 0:\n"
            "        runner = container.session_runner\n"
            "        print(f\"\\nRunning {args.run} pipeline cycle(s):\")\n"
            "        for i in range(1, args.run + 1):\n"
            "            print(f\"\\n--- Cycle {i} ---\")\n"
            "            result = runner.run_once(frame=None)\n"
            "            if result.success:\n"
            "                print(f\"  Artwork : {result.detection.label}\")\n"
            "                print(f\"  Q       : {result.transcript.text}\")\n"
            "                print(f\"  A       : {result.dialogue.response[:90]}\")\n"
            "            else:\n"
            "                print(f\"  (no cycle: {result.error})\")\n"
            "        print(\"\\nDone. Logged to\", settings.paths.logs_dir)\n"
            "        return\n"
            "\n"
            "    session_id = new_session_id()\n"
            "    sm = StateMachine(session_id=session_id, logger=container.logger)\n"
            "    print(f\"\\nSession {session_id} - scripted dev walkthrough:\")\n"
            "    _scripted_dev_walkthrough(sm)\n"
            "    print(\"\\nDone. Transitions logged to\", settings.paths.logs_dir)",
        ),
    ],
}

problems = []
for path, repls in EDITS.items():
    if not os.path.exists(path):
        problems.append("MISSING FILE: " + path)
        continue
    with io.open(path, "r", encoding="utf-8") as f:
        text = f.read()
    original = text
    for old, new in repls:
        if old in text:
            text = text.replace(old, new)
        else:
            problems.append("NOT FOUND in " + path + ":\n----\n" + old[:90] + "\n----")
    if text != original:
        with io.open(path + ".bak", "w", encoding="utf-8") as f:
            f.write(original)
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print("PATCHED:", path, "(backup at " + path + ".bak)")
    else:
        print("NO CHANGE:", path)

print()
if problems:
    print("=== PROBLEMS ===")
    for p in problems:
        print(p)
    print("\nSome edits did not apply. Paste this whole output back.")
else:
    print("All edits applied cleanly.")
