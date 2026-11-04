# Interactive conversation and halved question-end waits

Owner request: finish ordinary answers with a useful question, handle friendly
small talk and jokes before gently returning to art, and halve the configured
speech waits. The owner clarified that no question-bank/PDF rebuild is wanted.
Develop and deploy a separate test branch; main promotion requires a later
explicit instruction.

Branch: `codex/interactive-social-half-pauses`, continuing from the documented
`95b4b99` deployment and its documentation commit `0e1b445`.

## Behavior

- Prepared artwork answers now include their next concrete invitation on every
  turn, including the answer delivered after Yes/Oui. Accepting that invitation
  still delivers its promised prepared facts locally, without retrieval or a
  model call. The old every-other-turn cadence is removed.
- Generated ordinary answers are prompted to finish with one relevant question.
  If a successful answer omits it, a short local open question is added. An
  existing final question or clarification is preserved. The open fallback does
  not promise a canned fact or blindly redirect a non-art topic to a camera work.
- Streaming keeps early sentence playback; only a missing final invitation is
  appended locally. The spoken sentence sequence and saved conversational answer
  include the same question. No extra cloud request is introduced.
- Conservative whole-request French/English local small talk covers greetings,
  questions about wellbeing/the day, thanks and light jokes. Pending coarse
  intents let an appropriate short answer continue that exchange. A second joke
  is different, a refusal is respected, and a museum-interest bridge follows a
  short receptive exchange rather than every greeting. Other languages continue
  through the normal selected-language model path.
- Small talk never announces identity, requests a name or substitutes the full
  introduction. Hey Atlas / Bonjour Atlas still own the complete private/local
  optional-name introduction. Visit reset/configuration clears social state.
- Ordinary answers are interactive; cancelled turns, errors, safety refusals
  and explicit departure/control requests are not forced into a new invitation.

## Timings and deployment-specific settings

| Configured silence wait | Previous installed value | Requested value |
| --- | --- | --- |
| Normal question | 1,000 ms | 500 ms |
| Apparently unfinished question | 2,000 ms | 1,000 ms |
| Eligible exact prepared final | 600 ms | 300 ms |

These are end-of-speech waits, not an assertion that total STT/network/model/TTS
latency is halved. The guarded prepared shortcut still requires a complete final,
silence and coverage of the latest voiced PCM; resumed speech invalidates it.
Synthetic captures measure the reduced waits and resumed-speech behavior.
Physical microphone pauses and headset first-audible timing still need retesting.

Settings model, public YAML, Deepgram constructor and onsite preparation defaults
agree. Source-only deployment preserves live YAML layers, so both installed
speech layers also need the three explicit values. A task-scoped adapter of the
existing atomic settings tool updates only those three fields, with local Jetson
backups, dry-run and rollback checks. It does not apply the broader camera/pan
preparation patch. Other configuration, secrets, models and units are preserved.

No packages, firmware, raw recordings, visitor UI or network changes are part of
this release. The prior unresolved hotspot authentication is a separate task.

## Verification and release status

Local verification passed: 4,686 tests passed and three were skipped; the XML
case count and separate collection both contain 4,689 tests. Skips concern the
unavailable C++ compiler, Windows symlink permission and opt-in real inference.
Ruff, Python compilation, dependency compatibility, secret scan, recovery/layout
gates and 106 synthetic dashboard JavaScript checks pass. New tests cover social routing without a
model/retrieval, spoken and typed integration, question tails and streaming
memory, all enabled fallback-question languages, visit boundaries and the
halved waits. New modules are required and included in source-release smoke
validation. The narrow configuration transaction passes synthetic dry-run,
exact-scope, backup and injected second-write rollback checks.

Local evidence is in `deliverables/interactive-social-half-pauses-20261104/`
(outside the repository), including `full-verified.xml`, `collection.txt` and
`pause-ratios.json`. The last full run passes after updating old response-tail
assertions; no runtime behavior was weakened to satisfy those assertions.

This change is not yet deployed. A fresh source/config baseline, immutable
archive, staged native gate, retained backup and post-install checks are required
before reporting it installed. Audible/live-provider acceptance remains with
the owner after the authorized test deployment; main remains excluded.
