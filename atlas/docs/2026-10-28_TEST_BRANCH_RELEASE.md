# ATLAS test-branch source release

This is the earlier release. It is superseded by the
[interactive FAQ test release](2026-10-28_INTERACTIVE_FAQ_TEST_RELEASE.md),
which records the latest installed source and owner acceptance steps.

The owner explicitly authorized deploying the pending changes from a separate
test branch on 2026-10-28. Main must remain unchanged until hardware acceptance.

## Installed test release — confirmed 2026-10-28

Deployment succeeded from source commit `a1a81543684b7bdc3490b6f0853ddd37145fa784` on the
separate test branch. Main was not merged or modified. Archive SHA-256:
`c18b889bf6d38bead59f6b38eda9dbf1a0dc945e1f779fef6cfde9bf1785f965`. Its 208 entries include eight validation-only public fixtures;
all 200 installed managed files exactly match the reviewed manifest.

The source-only transaction passed native staging validation and restarted
only the existing user service. Afterward the four new-feature test files
passed **2,994 native mocked tests**; independent collection confirms the same
count. No real visitor question, microphone recording, or provider speech was
used by those tests. Final service state: active/running, ExecMainStatus 0,
NRestarts 0; public health and visitor/admin pages HTTP 200; real protected
routes reject unauthenticated access with HTTP 401. The PC-to-Jetson health
request also returned HTTP 200. Boot ID stayed unchanged. Metadata of excluded
settings, models, credential file and service unit remained unchanged; no
credential contents or hashes were read.

Rollback backup retained:
`/home/super-alex/atlas/backups/faq-20261028-581a9e5b/atlas-source-20261028-170622-be3a7aad`.

Hardware/audible acceptance remains pending with the owner. Start a fresh visit
and follow the acceptance steps below. Detailed public deployment evidence is
retained outside Git in `ATLAS/deliverables/faq-runtime-review/deployment-20261028/`.
A later documentation-only branch commit records this result; it does not
change the installed source revision above or require another restart.

## Scope

Branch: `codex/faq-wake-french-dates-runtime`, based on the current continuation
`9996dd7a40685dd49f94d03acce7d6e08f1882a0`. Includes prepared-answer matching
and bypass, exact requested introductions with private visitor name, French
spoken dates, and contextual artwork recommendations with a learn-more question.
An accepted recommendation now selects the recommended supported artwork for
subsequent retrieval; explicit named/current-view questions and resets override
or clear that pending suggestion. The reason may mention the previous artwork
without making the new recommendation ambiguous.

The current camera-free, navigation, Cartesia pronunciation/recovery, voice
locking, cancellation, conversation focus, privacy and disabled-pan safeguards
are retained. Recommendations use prompt instructions for actual selection and
wording, so live model quality still needs human acceptance.

## Pre-deployment evidence

SSH with strict known-host verification reached `super` at `192.168.137.193`.
The user service was active/running, ExecMainStatus 0, NRestarts 0, public health
HTTP 200. Its working directory and existing interpreter match the runbook.
All 125 committed baseline application files matched installed source after
normalizing line endings; there were no unexplained source differences.
Boot ID: `f8ac966e-e204-4546-b63b-c748cbe5d699`.
These are observations before apply, not evidence that this release is installed.

Final guarded local suite: 4,357 passed, three skipped. Earlier focused recommendation,
conversation and pipeline verification passed; the new supported-artwork
follow-up correction has behavioral tests, not only prompt assertions.
Ruff, secret scan, recovery and navigation checks pass before preparation.
The prior visitor reduced-motion browser gate passed. The optional unchanged
admin browser harness's authentication-console assertion limitation remains
recorded in the October 27 review.

## Deployment and verification

Use the existing `scripts/deploy/source_release.py` source-only transaction,
from a committed reviewed test branch. Build and verify an immutable archive,
record its SHA-256, transfer to a unique mode-0700 stage, and apply once using
the existing Jetson venv and user service. Keep its rollback backup. Do not
change packages, models, unit, secrets, local settings, firmware, networking,
or motor state. Do not repeat apply after an SSH interruption: inspect the
same transaction/result. No main merge is authorized.

The final deployment record must include exact source/archive hashes, managed
file comparison, native test result, service/public health, unchanged boot ID,
backup path, and remaining audible/manual acceptance. A successful source apply
does not prove model recommendation quality or headset pronunciation/latency.

## Owner acceptance

Start a fresh ATLAS experience. Confirm no automatic introduction; say Hey
Atlas or Bonjour Atlas alone and hear the supplied name in the introduction.
Ask the exact Mona Lisa example and prepared date/material questions. In
French, check 1896 is spoken as mille huit cent quatre-vingt-seize. Ask for an
artwork recommendation after choosing interests or discussing another work;
hear a reason and invitation, then say Yes / Oui and verify the follow-up is
about that recommendation. Check stop/restart and one voice per answer.
The damaged primary camera may remain offline for this voice acceptance.
