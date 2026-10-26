# Cartesia name pronunciation — October 25

The public introduction added in `f90bf48` includes the uppercase brand name
`ATLAS`. The Cartesia request builder previously passed that spelling verbatim;
it had no name-pronunciation rule. Earlier wake greetings used local Piper,
so an earlier correct greeting is not proof that the same Cartesia path was used.

Cartesia recommends normal capitalization for names and warns that all-caps
words can be interpreted as initialisms:
https://docs.cartesia.ai/build-with-cartesia/capability-guides/prompting-tips

The Cartesia request boundary now changes only the complete uppercase token
`ATLAS` to `Atlas`. Both whole-answer and complete-segment streaming requests use
that builder. Public/UI copy, source introductions, other acronyms, localized
name spellings, model, voice ID, language, speed, volume and provider fallback
remain unchanged. Private name-bearing greetings remain local-only; this change
does not add any cloud request or persist text/audio.

Synthetic tests cover all 20 language introductions, word boundaries, repeated
names and possessives, empty terminal frames, and actual whole/streaming adapter
requests using fake transport and playback. These tests verify request contents,
not the sound produced by Cartesia. The all-caps ambiguity is a likely cause,
not an audibly proven diagnosis. Live acceptance requires the user to hear one
anonymous introduction through the existing selected Cartesia voice after an
explicitly approved, coordinated deployment. No live deployment or audible
acceptance is implied by this document.

Local verification: 182 focused speech/identity/privacy tests passed. The full
guarded suite passed 3,789 tests with two skips across all 55 test files, each
covered once in four disjoint partitions. Maintained-source Ruff, secret,
recovery-bundle and whitespace checks passed. No UI files changed; the existing
navigation release's browser verification remains applicable. Deployment and
the audible greeting check are separate acceptance steps.
