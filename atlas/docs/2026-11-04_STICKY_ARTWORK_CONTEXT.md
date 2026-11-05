# Keep the visitor-selected artwork active

Branch: `codex/sticky-artwork-context`, continuing installed source `d745d3d`
and its deployment documentation `363a776`. The owner explicitly requests a
Jetson test deployment and forbids promotion to main.

## Behavior

- A supported, unambiguous closing invitation can register a pending artwork
  even when the visitor did not explicitly ask for a recommendation. A generic
  learn-more question after a clear named recommendation is supported too.
- Only known catalog titles/aliases are candidates. Incidental mentions,
  comparison invitations and multiple-choice artwork offers do not arbitrarily
  select a new work. Rejection, interruption and visit reset discard the offer.
- Accepting the offer or explicitly naming an artwork locks the discussion to
  that work. Ordinary unnamed followups retain it across camera changes, loss
  of frames and history rotation. Live camera metadata remains separate.
- A direct current-view question, explicit capture or staff artwork selection
  can reselect the actual camera work. A missing frame never becomes a claimed
  live identification. When no spoken topic is locked, automatic camera changes
  keep their existing behavior.
- A passive camera invitation about a different work is suppressed while a
  visitor-selected discussion is locked. Explicit capture can still change it.
- Yes/Oui accepting a supported prepared artwork introduces that new work locally
  before its next relevant question. The typed and both spoken routes share the
  state. Original visitor wording is retained in the bounded visit history.
- Generated-answer instructions use DISCUSSION ARTWORK for implicit followups
  while current-view questions still use CURRENT ARTWORK. Two existing camera
  transition tests now ask explicitly what is being viewed instead of relying
  on the ambiguous phrase 'Who painted this?' to discard a selected topic.

No new model/provider call, database, persistence, history expansion or dependency
is introduced. History stays at 12 recent turns with the existing bounded archive.
Normal/slow speech settings, STT waits, wake introductions and private names are
unchanged. End-to-end latency and live-provider acceptance still need the owner’s
physical test; no numerical latency promise is made.

## Validation and release

Focused synthetic gate passes 513 cases, including spontaneous offers, catalog
ambiguity, long followups, camera override, passive invitations, original wording,
streamed and whole generated proposals, and direct prepared acceptance without
retrieval/model calls. The complete local gate passes 4,771 tests with three
explicit skips (C++ compiler, Windows symlink privilege, opt-in real inference).
The JUnit case count and separate collection both equal 4,774. Lint, compile,
dependency compatibility, secrets, recovery, repository layout and 106 synthetic
JavaScript checks pass. Before replacement, the installed source matched the
preceding speech release without unreviewed managed source drift.

## Jetson test deployment completed

- Branch: `codex/sticky-artwork-context`; installed source commit:
  `fcf646e30487393a325f716e6dc669171f5567e6`.
- Maintained source-only release procedure verified the staged archive, ran its
  isolated dependency/compile/synthetic gate, backed up source, replaced only
  managed roots and restarted `atlas.service`. No dependency/model/unit/network
  changes or main promotion were performed.
- Archive SHA-256 (independently checked with Get-FileHash):
  `ddc75e41aa50b98f447f2ccb4f3b326aa4d2672f79578807e62d941ecf1f6a18`.
  All 212 managed files match their manifest; eight public content fixtures also
  match. No extra managed source files were found.
- Backup:
  `/home/super-alex/atlas/backups/context-20261104-523c3b5b/atlas-source-20261104-213946-e9440573`.
- Post-install native synthetic gate: 978 passed; independent collection: 978.
  It includes typed and spoken/streamed acceptance, implicit followups and camera
  priority, plus inherited speech/listening/greeting/privacy regressions. Wake
  tests use an ephemeral synthetic port; the production port guard is unchanged.
- Service is active/running, ExecMainStatus=0 and automatic restart count unchanged.
  Boot ID is unchanged. Loopback and laptop status-only checks return 200 for
  `/`, `/admin`, `/health`, and 401 for the protected audio/camera-pan APIs.
- All saved configuration, credential/model/unit stat metadata is unchanged.
  Selected effective speech values were checked without loading dotenv: normal
  speed 0.90, extra slow 0.80; silence waits 500/1,000/300 ms; persistent STT=true;
  ready cue=buzz. No private credentials, visitor history or recordings were read.

## Handoff and owner acceptance

Changed files: conversation memory/engine/prompt rules, session camera-invitation
guard, source-release smoke list, targeted tests and this release documentation.
No dashboard markup, configuration defaults or dependencies changed. Visual
layout was not retested; HTTP and synthetic dashboard logic checks passed.

Local commands: guarded `run_deployment_pytest.py` full suite and independent
collection; Ruff; compileall; offline dependency check; secrets/recovery/layout
scripts; `node atlas/scripts/verify_admin_logic.cjs`; `git diff --check`.
Native commands: maintained `source_release.py apply`, then guarded selected
synthetic tests and separate collection from installed source. Local evidence is
under `deliverables/sticky-artwork-20261104/` outside the repository.

Deployment performed: Yes. Ready for owner testing: Yes. Main promotion: No.
Physical headset/provider acceptance and end-to-end latency remain unmeasured.
Known limit: offers must unambiguously name a catalog work; comparisons or unknown
titles do not silently replace the discussion. This is per-visit bounded state,
not long-term visitor memory, and reset clears the selected subject.

Owner check: discuss Mona Lisa, accept an offer of Great Wave, then ask its artist,
date and technique without repeating its title. The subject should remain Great
Wave even with Mona Lisa in view. Ask explicitly what you are looking at (or use
manual capture) to reselect the camera work. Repeat after ending/restarting the
visit to confirm previous visitor context has cleared. Keep the test branch until
the owner accepts the physical result.
