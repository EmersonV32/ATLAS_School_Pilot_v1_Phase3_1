# Interactive FAQ test release

This earlier release is superseded by the
[full wake introduction release](2026-10-28_FULL_WAKE_INTRODUCTION.md).

The owner requested more conversational invitations and faster prepared answers,
then explicitly clarified that the result must be redeployed to the Jetson for
retesting. This is a descendant test branch, `codex/interactive-fast-faq`.
Main promotion is not authorized.

## Behavior

- Reuse the existing museum-sourced prepared catalogue; no regeneration or
  format migration. Its supported artworks, languages, profiles, source IDs,
  accessibility descriptions and deeper-question fallback are retained.
- Add common complete French forms such as "C'est quoi la Joconde ?" and
  "En quelle année elle a été peinte ?", including œ and contraction handling.
- Offer one relevant, varied optional next detail on spaced turns. An accepted
  prepared invitation delivers the promised facts locally; refusals, topic
  changes and resets clear it. Typed and both spoken entry points share this
  state. Model prompts also ask for contextual, varied invitations.
- Exact complete final FAQ transcriptions can end after 600 ms stable silence.
  General questions retain 2,000 ms and incomplete/hesitant questions 4,000 ms.
  Interim/fuzzy/compound/partial/quoted questions cannot use the shortcut. A
  timed final must cover the latest voiced PCM, including pre-roll; a delayed
  old final cannot shorten resumed speech. Ignored empty/stale interims do not
  cancel an otherwise eligible result. Missing timing retains the general path.
- Flush Cartesia PCM chunks immediately. Timing starts after successful flush;
  traces explicitly call this player input, not audible headset onset. Failed,
  missing and stale measurements are unavailable, never successful samples.

The new default works when an older private settings file lacks its field;
source-only deployment preserves the existing Jetson settings. A configured
zero disables the FAQ endpoint shortcut. Existing wake-only private name,
French date normalization, recommendation routing, cancellation, voice locking,
camera-free operation and disabled pan remain in place.

## Verification and deployment

Final local guarded suite: **4,506 passed, three skipped**. Independent collection
confirms 4,509 tests. Ruff, compile, offline dependency compatibility,
secret/recovery/repository checks and whitespace checks pass. Synthetic admin
logic passes; the visitor browser gate passes at 1024x768 with reduced motion,
42 keyboard transitions and no console errors. The previously documented optional
admin browser harness limitation remains; its unchanged harness is not a claimed
pass in this release. A superseded full run was stopped after final review found
the French person-pronoun ambiguity; the complete result above is the corrected
source, including the new regression.

Before apply, all 200 previous managed files and eight public fixtures matched
the previous archive; service is active/running, NRestarts 0, ExecMainStatus 0,
visitor/admin/health HTTP 200 and protected routes HTTP 401. This baseline is
separate from the post-deployment evidence below.
No packages, models, credentials, live configuration, service unit, firmware,
networking or motor state are part of this release.

## Installed release — confirmed 2026-10-28

Source revision: `d7ecce77974b461b64545851abafd07b80f4bfca` on
`codex/interactive-fast-faq`. Archive SHA-256:
`c679384ac1e1d552034dc1ecb07cc2f17eda975062716169f0c3fc061f523a70`.
The source-only transaction passed native staging checks, installed 202 managed
files from the 210-entry archive (eight validation-only public fixtures), and
restarted the existing user service. Every installed managed file matches the
manifest. The public fixtures also match; private config and data were not
replaced. Archive SHA-256 was independently checked on the laptop and verified
again after transfer.

Native new-feature mocked suite: **3,334 passed**, with independent collection
confirming 3,334. The suite covers prepared answers, interactive continuations,
endpoint/PCM handling, voice identity, spoken pipeline, French normalization
and private visitor personalization. Staging additionally tested typed dashboard
integration. No real visitor audio, provider synthesis or physical headset
measurement was performed by these tests.

Afterward: service active/running, NRestarts 0, ExecMainStatus 0; visitor/admin/
health HTTP 200; protected audio/pan endpoints HTTP 401. PC-to-Jetson health
also returned HTTP 200. Boot ID remained
`f8ac966e-e204-4546-b63b-c748cbe5d699`. Stat metadata of the credential file,
local settings/overrides, models and user service unit remained identical;
credential contents and hashes were never read.

Rollback retained:
`/home/super-alex/atlas/backups/interactive-20261028-8a9b9096/atlas-source-20261028-174319-41c57358`.
Sanitized evidence is retained outside Git in
`ATLAS/deliverables/faq-runtime-review/interactive-deployment-20261028/`.
Main remains `9dfe2606e907f85e2c9b626118a98e65e9f09e7a`. The later documentation
commit records deployment only and requires no new service restart.

Automated endpoint tests and resolver benchmarks do not prove an answer becomes
audible within two seconds. Deepgram final delivery/cleanup, dispatch, cloud
synthesis, playback buffering and hardware remain part of that measurement.

## Owner retest

Start a fresh experience and select French with the desired interests/profile.
Ask "C'est quoi la Joconde ?", "Qui a peint la Joconde ?" and
"En quelle année elle a été peinte ?". After an invitation, say "Oui" and
check that the promised topic is explained without asking permission again.
Try "Non merci", a new subject, and a longer question with a pause; speech
must not be truncated. Ask for another artwork after expressing an interest;
check the connection and accept the recommendation.

Measure from the end of the visitor's speech to the first sound of the answer,
using the real headset and network. Retest explicit Hey Atlas / Bonjour Atlas,
the private dashboard name, French dates, stop/restart and one voice per answer.
Keep main unchanged until the owner accepts these physical tests.
