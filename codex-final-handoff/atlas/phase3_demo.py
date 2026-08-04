"""
Phase 3 dev demo — run this from the atlas project root to confirm
the full dialogue pipeline works without any API key or hardware.

Usage:
    python phase3_demo.py

Expected output:
    ATLAS Dialogue Engine — Phase 3 Dev Demo
    =========================================
    Q: Who painted The Starry Night?
    [MOCK] <some response>
    grounded=True  filtered=False  lang=en

    Q: Quand a-t-il été peint?  (French)
    [MOCK] <some response>
    grounded=True  filtered=False  lang=fr

    Q: Describe the colours used.  (child visitor, age 9)
    [MOCK] <some response>
    grounded=True  filtered=False  lang=en

    All checks passed.
"""

from atlas.dialogue.mock_llm_client import MockLLMClient
from atlas.dialogue.dialogue_engine import DialogueEngine

CHUNKS = [
    {
        "text": (
            "The Starry Night is an oil-on-canvas painting by Dutch Post-Impressionist "
            "artist Vincent van Gogh. Painted in June 1889, it depicts the view from "
            "the east-facing window of his asylum room at Saint-Paul-de-Mausole, near "
            "Saint-Rémy-de-Provence, France."
        )
    },
    {
        "text": (
            "The painting is dominated by a swirling night sky filled with luminous "
            "stars and a crescent moon. The colour palette is rich in deep blues, "
            "vibrant yellows, and warm whites. It has been in the permanent collection "
            "of the Museum of Modern Art in New York since 1941."
        )
    },
]

engine = DialogueEngine(llm_client=MockLLMClient())

cases = [
    ("Who painted The Starry Night?",       None,  "en"),
    ("Quand a-t-il été peint?",             None,  "fr"),
    ("Describe the colours used.",          9,     "en"),
]

print("ATLAS Dialogue Engine — Phase 3 Dev Demo")
print("=" * 41)

all_ok = True
for question, age, lang in cases:
    label = f"  (child visitor, age {age})" if age else f"  (French)" if lang == "fr" else ""
    print(f"\nQ: {question}{label}")
    result = engine.respond(question=question, artwork_chunks=CHUNKS, visitor_age=age, language=lang)
    print(result.response)
    print(f"  grounded={result.grounded}  filtered={result.filtered}  lang={result.language}")
    if result.error:
        print(f"  ERROR: {result.error}")
        all_ok = False

print()
if all_ok:
    print("All checks passed.")
else:
    print("One or more errors — see above.")
