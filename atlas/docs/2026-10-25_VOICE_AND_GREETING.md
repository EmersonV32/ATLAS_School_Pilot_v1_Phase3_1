# October 25 voice recovery and automatic introduction

Implementation revision: `f90bf486f2261310975da571f104e3f64136b664` on
`codex/camera-offline-demo-2026-10-25`. Main is unchanged.

## Confirmed voice defect and scope

One temporary Cartesia failure before playback previously set
`FallbackTTS.primary_ready = False` permanently. Subsequent answers stayed on
Piper until the service restarted. Recovery now retries the preferred provider
between answers after a bounded 15-second cooldown; a failure does not leave
the installation permanently stuck on another voice.

Whole-answer calls are serialized so a concurrent request cannot reset the
shared `playback_started` indicator before the failure guard inspects it.
Queued cancelled speech is discarded. Existing fixed voice/context/language,
one-player whole-answer synthesis and no provider fallback after audible speech
starts remain enforced. Production sentence-at-a-time speech remains disabled.
No saved model/voice ID, provider preference or audio route was changed.

These are client-side reliability fixes, not proof that provider-generated
timbre cannot vary inside a single audio response. The owner's all-language
mid-answer report still needs audible long-answer retesting; do not describe
the cloud voice as permanently defect-free. Offline fallback may still sound
different for an entire answer when the cloud is unavailable. It must never
take over partway through an already audible answer.

## Automatic greetings

- Admin Start demo and visitor onboarding finish queue one introduction in the
  selected language. HTTP does not wait on synthesis.
- The device speech thread consumes it once before opening the microphone.
  Visitor onboarding no longer requires a wake phrase first.
- Public introduction copy exists for all 20 admin language codes, for example:
  “Hello, I'm ATLAS, your AI art guide. Ask me about an artwork by name, or tell
  me what you would like to explore.”
- A name-bearing introduction uses one complete local-only synthesis. No name
  enters cloud requests, prompts, retrieval, monitoring or logs; the ephemeral
  name is erased before playback. This private local greeting can sound
  different from subsequent cloud answers, by design, not as a mid-answer swap.
- Stop/restart discards old pending greetings and cancels current speech. An
  emergency stop suppresses the introduction. Failed playback is not replayed
  or sent to the cloud with a private name. Listening remains available after
  an ordinary failed introduction.
- Visitor instructions and static shell version `v29` match immediate greeting.
  Camera-free conversation remains supported.

## Verification and installation

Source-only archive: `ATLAS-voice-greeting-source.zip`, 197 allowlisted files,
SHA-256 `2fb1bf2656c9a75e8618667d0f3462e6fc7ec6e86e8a887b269efa2d2746a48e`.
Jetson isolated native preflight passed. The source release's native gate now
also includes fallback, all-language voice identity and greeting/privacy tests.

Focused speech tests include all 20 admin languages, one synthesis identity
across chunks, stale context rejection, no late fallback/reconnect/replay,
cancel isolation, cooldown recovery and serialized queued cancellation.
Both real HTTP-entry integration tests use explicitly mocked device readiness.
The first draft test used an unbridged dev preview and failed; its synthetic
fixture was corrected without changing runtime behavior.

Visitor browser QA: 38 keyboard transitions at 1024x768 with reduced motion,
camera-degraded successful start, no cookies/browser storage/IndexedDB and zero
browser errors. Synthetic admin JavaScript: 106 checks. Ruff, dependency,
secret, recovery and whitespace gates pass.

Final full suite: **3,593 passed, two skipped**, with the existing TestClient
deprecation and intentional duplicate-ZIP fixture warnings. Source apply and
apply completed successfully. All **189 installed managed files** match
`f90bf48`; the user service is active/running with zero unexpected restarts.
Headset, speech, AI and retrieval are ready; camera remains correctly degraded.
Visitor assets `v29` load and protected routes still reject unauthenticated
requests. Rollback backup:
`/home/super-alex/atlas/backups/onsite-20261025/atlas-source-20261025-145348-67892ce8`.
Live acceptance must check an automatic introduction
from each start path, then short and long answers in English/French, stop
during greeting, and conversation context with the camera still offline.

No Wi-Fi, firmware, motor output, service unit, package, model or private
configuration changes are part of this release.
