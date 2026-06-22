import io, os, sys

EDITS = {
    "phase4_demo.py": [
        (
            "    engine = DialogueEngine(\n"
            "        llm=MockLLMClient(),\n"
            "        prompt_builder=PromptBuilder(),\n"
            "        grounding_validator=GroundingValidator(),\n"
            "        safety_filter=SafetyFilter(),\n"
            "    )",
            "    engine = DialogueEngine(llm_client=MockLLMClient())",
        ),
        (
            "            ans = result.dialogue.answer_text",
            "            ans = result.dialogue.response",
        ),
    ],
    os.path.join("src", "atlas", "pipeline", "session_runner.py"): [
        (
            "        dialogue_result = self._engine.answer(\n"
            "            query=transcript.text,\n"
            "            chunks=chunks,\n"
            "            language=transcript.language,\n"
            "            age_level=transcript.age_hint,\n"
            "        )",
            "        dialogue_result = self._engine.respond(\n"
            "            question=transcript.text,\n"
            "            artwork_chunks=chunks,\n"
            "            language=transcript.language,\n"
            "            visitor_age=_age_hint_to_number(transcript.age_hint),\n"
            "        )",
        ),
        (
            "            dialogue_result.answer_text,",
            "            dialogue_result.response,",
        ),
        (
            "        self._tts.speak(dialogue_result.answer_text, language=transcript.language)",
            "        self._tts.speak(dialogue_result.response, language=transcript.language)",
        ),
        (
            "logger = logging.getLogger(__name__)",
            "logger = logging.getLogger(__name__)\n\n\n"
            "def _age_hint_to_number(age_hint):\n"
            "    mapping = {\"child\": 8, \"teen\": 14, \"adult\": 30}\n"
            "    if isinstance(age_hint, int):\n"
            "        return age_hint\n"
            "    return mapping.get(str(age_hint).lower())",
        ),
    ],
    os.path.join("tests", "test_pipeline.py"): [
        (
            "    engine = DialogueEngine(\n"
            "        llm=MockLLMClient(),\n"
            "        prompt_builder=PromptBuilder(),\n"
            "        grounding_validator=GroundingValidator(),\n"
            "        safety_filter=SafetyFilter(),\n",
            "    engine = DialogueEngine(llm_client=MockLLMClient())\n    _unused = (\n",
        ),
        (
            ".answer_text",
            ".response",
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
            problems.append("NOT FOUND in " + path + ":\n----\n" + old[:80] + "\n----")
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
