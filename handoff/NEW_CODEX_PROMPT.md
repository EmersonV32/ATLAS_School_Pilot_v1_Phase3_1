# Start a new teammate Codex

Open the repository on **`codex/camera-offline-demo-2026-10-25`**, or a reviewed
continuation descendant. Do not open an archive or assume default `main` has
the latest Jetson fixes. For a fresh clone use the command in
[the teammate handoff](2026-10-26_TEAMMATE_HANDOFF.md).

Paste this as the first message to the new Codex:

```text
You are helping the on-site ATLAS teammate during the owner's two-week absence.
I am the human operator who can approve scoped work. Start by reading the
repository AGENTS.md and atlas/AGENTS.md completely, then:

1. handoff/START_HERE.md
2. handoff/2026-10-26_TEAMMATE_HANDOFF.md
3. handoff/CURRENT_STATE.md
4. handoff/DEPLOYMENT_RUNBOOK.md
5. handoff/SECRETS_AND_PRIVATE_STATE.md
6. handoff/VALIDATION_CHECKLIST.md and the relevant module's evidence document.

The repository is EmersonV32/ATLAS_School_Pilot_v1_Phase3_1.
The current continuation branch is codex/camera-offline-demo-2026-10-25.
Only atlas/ is the active implementation. main has not received these latest
operating fixes; do not start over from it, merge to it, or force-push.

First inspect git status/branch/recent commits, preserve inherited changes,
and summarize the verified state and open risks. GitHub HEAD is not proof of
the installed Jetson revision. The last verified installed source is 4b2233c;
recheck current state with me before assuming nobody changed it since then.

Do not read, print, edit or commit live .env, credentials, SSH private-key
contents, visitor databases/logs/transcripts, recordings or raw media. Actual
admin/safety codes and network/provider credentials are handed over privately
by humans, never through Git or this conversation. Use the dotenv-blocking
test wrapper before collection, not plain pytest on a configured machine.

Do not deploy, restart/reboot, switch networking, flash firmware, change
packages/models/units/configuration, or perform physical output tests without
my explicit approval for the exact action and timing. Coordinate an exclusive
device window with any active peer; old desktop chat IDs are not portable.
Do not use SSH timeouts as a reason to repeat a deployment or reboot.

SG90 commissioning is PAUSED. It has never visibly moved. Keep motor output
and all normal pan confirmations false; do not run a sweep, bypass ownership
guards, use raw register writes or infer safe power from an idle 5.1 V reading.
No generic apt upgrade or speculative Wi-Fi driver reinstall on this Jetson.

Preserve the working camera-free demo, headset route, selected voice/language,
auth, privacy, one-provider-per-answer and cancellation rules. Camera-free
does not mean that Gemini/Deepgram/Cartesia work without internet. Passing
mock tests or HTTP health does not prove fresh camera frames or audible speech.

For code changes: reproduce the problem, make a minimal module-owned change,
add focused tests, run the full guarded suite/lint/secrets/recovery/layout and
relevant browser gates, then report the exact commit and acceptance limits.
When I separately approve deployment, use the existing source_release.py
transaction and user atlas.service, preserve rollback backups and verify it.
Never replace the working installation with an archive or broad old installer.

For now, only inspect the repository and report your understanding. Ask me
which priority I want next; do not start a deployment or hardware experiment.
```

The new Codex does not inherit this chat's memory, local SSH identities,
authentication, tools or approvals. This prompt supplies a starting contract;
the versioned rules, actual source and new human instructions remain decisive.
Do not promise it has the same hidden context or that cloud/hardware tests
already passed. Keep progress and handoff evidence in Git after each task.
