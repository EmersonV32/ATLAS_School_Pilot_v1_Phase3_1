# Slightly slower, consistent synthesis pace

Branch: `codex/slower-speech`, continuing the installed `db1586c` release and
its documentation head `3940ba2`. The owner requested laptop-only preparation;
the Jetson is offline. No SSH, hardware action, restart or deployment is authorized
for this task. Main remains excluded pending a later instruction.

## Requested and implemented behavior

- Normal synthesis speed is explicitly 0.90. Simple language, rich description,
  age, expertise and language do not select a different synthesis speed.
- The existing visitor `slower_pace` choice explicitly selects 0.80, including
  combinations with simple language or audio description. Removing it restores
  the normal setting for the next response/visit.
- Cartesia whole responses and continuous segments send `generation_config.speed`.
  The speed is pinned at the start of each continuous answer, including its final
  flush, so an updated choice cannot change pace halfway through that answer.
- Piper receives `--length-scale` as the inverse selected speed (1/0.90 normally,
  1/0.80 for extra slow). This also applies to private local name-bearing greetings.
- The fallback wrapper forwards the explicit choice to both providers. The device
  runner applies the visit choice and the separate wake-greeting path applies it
  before public or private speech. Existing identity/privacy rules remain intact.
- Speech settings validate finite, bounded values and reject a slow setting faster
  than normal. Saved configurations that omit these new keys use the new defaults;
  source-only installation does not need a rewrite of live YAML to enable them.

These are synthesis controls, not measured words per minute or a guarantee of an
exact percentage change in audible duration. Voice, language, content, pauses and
provider behavior still affect the sound. No voice, pitch, PCM sample rate, STT
endpoint wait, readiness buzz, provider retry or model version is changed. No
package/dependency changes or additional cloud call is introduced.

Primary API references checked during implementation:
- Cartesia generation controls (Sonic 3 and newer):
  https://docs.cartesia.ai/api-reference/tts/bytes
- Official Cartesia SDK WebSocket speed example:
  https://github.com/cartesia-ai/cartesia-python/blob/main/examples/examples.py
- Piper CLI accepts --length-scale / --length_scale:
  https://github.com/OHF-Voice/piper1-gpl/blob/main/src/piper/__main__.py
- Piper length scale greater than one means slower phonemes:
  https://github.com/OHF-Voice/piper1-gpl/blob/main/src/piper/config.py

## Verification

Focused isolated gate: 317 tests passed, covering explicit payloads, all profiles
and combined accessibility choices, continuous-answer pinning, local greetings, visit reset,
provider wiring, invalid settings, cancellation, French date pronunciation and
existing speech behavior. Three initial failures came from old synthetic Piper
fixtures assuming the last CLI argument was always the output filename; those
fixtures now locate --output-file and retain the same date assertions.
Complete guarded local suite: 4,738 passed / three skipped. Separate collection
and XML case counting both report 4,741 tests, including 52 new pace cases.
The skips are the unavailable native C++ compiler, Windows symlink permission
and opt-in real ML inference. Ruff, compilation, dependency compatibility,
secret scan, recovery/layout gates, diff check and 106 synthetic dashboard JS
checks pass. No UI markup/styles changed. Optional headless browser scripts
were not rerun because Playwright is unavailable in the local Node environment.

Evidence: `deliverables/speech-pace-20261104/` outside the repository contains
`full.xml`, `collection.txt` and `validation.json`. No live provider/audio calls,
Jetson connection or hardware change was made.

## Handoff

Task completed: slightly slower normal speech and extra-slow accessibility pace,
locally verified and ready for the owner-requested later Jetson test.
Files changed: shared speech pace helper; Cartesia, Piper, BaseTTS, mock and fallback;
settings model/public defaults; dependency factory; runner and wake greeting bridge;
focused tests, source-release smoke gate and continuity documentation.
Local visual verification: visitor UI unchanged; existing slower option retained.
Configuration/dependencies: two speech fields (tts_speed, tts_slower_speed); no new dependencies.
Jetson verification still required: staged native gate after reconnection, preserved
live configuration, actual French/English headset sound, normal versus simple
language, and the additional slower choice. No audible baseline/WPM is claimed.
Risks: Cartesia interprets the setting as guidance; the two providers may sound
different at equivalent numeric settings. Physical acceptance remains necessary.
Security/privacy: no secrets, private records, recordings or live state accessed.
Deployment performed: No.
Ready for primary Codex review: Yes. Deployment and physical listening are pending.
