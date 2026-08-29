# Jetson Codex coordination

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
