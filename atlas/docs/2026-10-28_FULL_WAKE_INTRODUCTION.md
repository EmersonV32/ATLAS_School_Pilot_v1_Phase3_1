# Complete wake introduction before suggestions

The owner requested the complete self-introduction after Hey Atlas / Bonjour
Atlas, with the optional dashboard name, before an interest invitation, and
explicitly authorized another Jetson test deployment. Main remains excluded.
Branch: `codex/full-wake-introduction`, based on the installed interactive FAQ
continuation rather than main.

## Confirmed cause and correction

The named route selected a short greeting plus artwork invitation instead of
the full public introduction. It now inserts the name into the same complete
introduction. English and French explain ATLAS's role and help before one
optional interest question; an empty name uses the complete anonymous copy.
The entire name-bearing introduction remains one private-local synthesis.
Names never enter the public response, model, retrieval or logs, and are erased
after successful greeting or visit stop.

The visitor dashboard starts an ungated voice session. Both stable-camera and
manual-capture demo paths previously allowed proactive invitations before any
explicit greeting. They now require the current visit's successful spoken
introduction. Queued callbacks also recheck the visit before speaking. Failed,
cancelled, stopped or superseded introductions do not unlock those suggestions.
Ordinary visitor questions remain usable before a wake greeting; they never
introduce ATLAS or use the optional name. The introduction remains once per
visit, after an exact standalone allowed wake phrase.

## Validation and deployment

Final guarded local suite: **4,537 passed, three skipped**; independent
collection confirms 4,540 tests. Root greeting/API/privacy/pronunciation tests
passed; the device loop/camera/wake regression gate passed. Ruff, compilation,
offline dependency compatibility, secret scan, recovery, repository layout and
whitespace checks pass. Synthetic admin logic and visitor 1024x768 reduced-
motion keyboard flow pass. The unchanged optional admin-browser harness
limitation remains recorded in earlier release notes; no new pass is claimed.

Before deployment, every previous managed file and public fixture matches the
interactive FAQ archive. Service is active/running with NRestarts 0 and
ExecMainStatus 0; public pages/health return HTTP 200, protected routes HTTP 401.
Local settings, packages, models, secrets, service units, firmware, networking
and motor state are outside this release.

## Installed release — confirmed 2026-10-28

Source `228f4daadcd3c193eba52a4be6733f9fc09bbdca`, branch
`codex/full-wake-introduction`. Archive SHA-256:
`35049b8dd2e6bf890b207c6d66ea32df42f9e7493cc87ef1b3ed7d11d59bd5bb`.
Independent laptop hashing and remote archive verification agree. The
source-only transaction passed staged validation, installed 203 managed files
from the 211-entry archive (eight validation-only public fixtures), and
restarted only the existing user service. All installed managed files match
the manifest; the public fixtures also match.

Additional installed-source mocked tests: **306 passed**, independently 306
collected. The first native run had 294 pass and twelve wake-loop tests fail
because their real port probe correctly found the running dashboard on 8765.
The native harness now runs that module's real availability probe on ephemeral
port 0 and immediately restores its test setting; dashboard startup in those
tests was already mocked. A first wrapper attempt used the wrong settings
member and also failed those twelve tests; that wrapper was corrected before
the final complete pass. Production files, settings and the running service
were untouched by this test isolation. These were test-environment/wrapper
failures, not waived assertions or a claimed initial clean pass.

Service active/running, ExecMainStatus 0, NRestarts 0; visitor/admin/health HTTP
200, protected audio/pan routes HTTP 401. PC-to-Jetson health also HTTP 200.
Boot ID and stat metadata of credentials, local settings/overrides, models and
the service unit remained unchanged. No credential contents/hashes were read.

Rollback retained:
`/home/super-alex/atlas/backups/wakeintro-20261028-387fb151/atlas-source-20261028-180246-da8bff00`.
Sanitized evidence and the native harness are outside Git in
`ATLAS/deliverables/faq-runtime-review/wake-intro-deployment-20261028/`.
Main remains `9dfe2606e907f85e2c9b626118a98e65e9f09e7a`. A subsequent
documentation-only commit records this result; no additional restart is needed.

## Owner retest

Start a fresh experience with a name and say Hey Atlas or Bonjour Atlas alone.
Hear the name, the complete role/help explanation, then the interest question.
Start another fresh experience without a name; hear the same full explanation
with no name or placeholder. Confirm a camera artwork suggestion cannot speak
first. A second wake in the same visit must not repeat the introduction.
Audible completeness, name pronunciation and actual headset routing remain
physical acceptance checks; mocked tests prove the submitted sequence only.
