#!/usr/bin/env python3
"""Run focused retrieval checks against the installed ATLAS content pack."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from atlas.app.dependency_container import Container
from atlas.config.loader import load_settings
from atlas.models.enums import EducationalLevel, Intent, Language, RunMode
from atlas.models.retrieval import RetrievalQuery


@dataclass(frozen=True)
class Case:
    artwork_id: str
    question: str
    language: Language
    intent: Intent
    expected_terms: tuple[str, ...]


CASES = (
    Case("mona_lisa", "Why is it behind glass?", Language.EN, Intent.HISTORY,
         ("glass", "poplar", "crack")),
    Case("starry_night", "Could Van Gogh see the village from his window?",
         Language.EN, Intent.HISTORY, ("village", "window")),
    Case("tutankhamun_mask", "Which gods are connected to the mask?",
         Language.EN, Intent.MEANING, ("osiris", "re")),
    Case("sunflowers", "Why did Van Gogh paint the sunflower series?",
         Language.EN, Intent.HISTORY, ("gauguin", "yellow house")),
    Case("liberty_leading_the_people", "Is this the French Revolution of 1789?",
         Language.EN, Intent.HISTORY, ("1789", "1830")),
    Case("girl_with_a_pearl_earring", "Is she a real portrait?",
         Language.EN, Intent.WHAT_IS_THIS, ("tronie", "portrait")),
    Case("great_wave_off_kanagawa", "What is special about the blue pigment?",
         Language.EN, Intent.HOW_MADE, ("prussian blue", "pigment")),
    Case("mona_lisa", "Qui est la Joconde?", Language.FR,
         Intent.WHAT_IS_THIS, ("lisa gherardini", "joconde")),
    Case("starry_night", "Quien pinto esta obra?", Language.ES,
         Intent.WHO_MADE_IT, ("van gogh",)),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args()

    settings = load_settings(args.config_dir)
    settings.mode = RunMode.DEVICE
    container = Container(settings)
    failures = 0

    for case in CASES:
        result = container.retriever.retrieve(
            RetrievalQuery(
                text=case.question,
                artwork_id=case.artwork_id,
                language=case.language,
                educational_level=EducationalLevel.ADULT_BEGINNER,
                intent=case.intent,
                top_k=5,
            )
        )
        combined = " ".join(chunk.text.lower() for chunk in result.chunks)
        scoped = bool(result.chunks) and all(
            chunk.artwork_id == case.artwork_id for chunk in result.chunks
        )
        grounded = all(term in combined for term in case.expected_terms)
        fallback_ok = (
            case.language is not Language.ES
            or all(chunk.language == "en" for chunk in result.chunks)
        )
        passed = scoped and grounded and fallback_ok
        failures += int(not passed)
        top_id = result.chunks[0].chunk_id if result.chunks else "NONE"
        print(
            f"{'PASS' if passed else 'FAIL'} | {case.artwork_id:30} "
            f"| {case.language.value} | {result.total_latency_ms:7.1f} ms "
            f"| {top_id}"
        )
        if not passed:
            print(f"  expected={case.expected_terms} returned={combined[:300]!r}")

    print(f"\nRAG evaluation: {len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
