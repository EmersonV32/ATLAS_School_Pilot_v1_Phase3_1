# Jetson Codex coordination

## 2026-08-18 5:29 PM EDT - Dashboard Codex

Visitor Prompt v2 and its enforcement safeguards are now deployed on the live
Jetson. The GitHub source is on branch `codex/visitor-prompt-v2`; do not merge
that branch into `main` until the project owner explicitly approves the merge.

Live files updated:

- `src/atlas/dialogue/prompt_builder.py`
- `src/atlas/dialogue/gemini_client.py`
- `src/atlas/dialogue/dialogue_engine.py`

The update makes museum context authoritative for artwork-specific facts,
allows stable general art knowledge without guessing artwork identity, attaches
Gemini's provider-level JSON response schema, rejects malformed structured
output and model-reported unsupported claims before speech, uses a conservative
`unknown` visual-identification rule, and restores Gemini's default dynamic
thinking by removing the forced zero thinking budget.

Verification completed:

- Local canonical suite: 235 passed.
- Jetson focused staging suite: 54 passed.
- Jetson full staging suite: 279 passed, with four unrelated existing dashboard
  expectation failures (visitor headline, admin login text, redirect style, and
  `log_llm_responses` default).
- Deployed live-source suite: 54 passed.
- `atlas.service`: active and running; `/health` reports device mode and
  `GeminiClient`.

Rollback backup:

`/home/super-alex/atlas/backups/visitor-prompt-v2-20260818-172749`

If you edit any of the three dialogue files directly on the Jetson, first pull
or inspect `codex/visitor-prompt-v2` so these safeguards are not accidentally
removed. Preserve `.env`, runtime data, logs, databases, and raw media.

## Current request from the dashboard Codex

Please preserve and publish the Jetson's current runtime work before we make
the visitor dashboard depend on real hardware state.

The GitHub `main` branch now contains the mock-backed visitor onboarding and
admin live monitor. It does **not** yet claim that the Jetson, headset, camera,
or other hardware is connected to that new dashboard contract.

## Safe sync protocol

1. Do not discard, reset, clean, or overwrite the Jetson working tree.
2. Run `git status` and review every local change.
3. From the Jetson's current working tree, create a branch named
   `codex/jetson-runtime-sync` (or use an existing branch with that purpose).
4. Commit the reviewed source code, configuration templates, documentation,
   tests, and service files that describe the Jetson runtime.
5. Do not commit `.env` files, API keys, tokens, raw audio/images, local logs,
   databases, large downloaded models, or generated build artifacts.
6. Push the branch to GitHub. Do not merge or force-push `main` from the
   Jetson.
7. Add or update `docs/handoff/JETSON_RUNTIME_STATUS.md` on that branch using
   the status template below.

## Required Jetson runtime status

Record concise, factual answers for each item:

- Git branch and commit used by the running Jetson system.
- Exact command, service unit, or script that starts ATLAS.
- Working directory, virtual environment, and configuration files actually
  used at runtime.
- Current HTTP/dashboard address and port, if any.
- Hardware status: Jetson, Shokz headset, XIAO camera, router/network, EV3,
  microphone, speakers, and buttons.
- Which flows are verified on physical hardware and which are mock-only.
- Known failures, manual workarounds, and required reboot/restart steps.
- Any local changes intentionally excluded from Git, described without secrets.
- The safest proposed command sequence for updating the Jetson from GitHub
  after the two Codex workstreams are reconciled.

## What the dashboard Codex will do next

Once the branch and status file are pushed, the dashboard Codex will:

1. Compare the Jetson runtime changes with GitHub `main`.
2. Reconcile conflicts without losing the Jetson's direct work.
3. Replace the visitor dashboard's mock readiness and start seam with a
   privacy-bounded real runtime projection.
4. Prepare a tested, reversible update path from this computer to the Jetson.

## Reply location

Do not edit this request file to reply. Put the Jetson report in
`docs/handoff/JETSON_RUNTIME_STATUS.md` on the Jetson sync branch, then push
that branch and share its name/commit.
