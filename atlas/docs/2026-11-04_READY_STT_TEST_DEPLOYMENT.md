# Persistent STT test deployment — 2026-11-04

## Authorized scope and installed result

The owner explicitly requested deploying the pending `95b4b99` release to the
online Jetson and preferring the laptop hotspot over other saved Wi-Fi networks.
The earlier instruction to leave the update ready-only is superseded. Main
promotion was not requested. The prior explicit selection of introductions only
after Hey Atlas / Bonjour Atlas remains in effect.

Installed source revision: `95b4b99c553d1b9ad8abbc3dfe1cc4518aed95ae`.

Source branch: `codex/ready-stt-cue`. Later documentation commits do not change
the installed source identity.

Archive SHA-256:
`c6f6ffeb89e0ea39c0e9b4fef4da0014bdb37194f3858c9a08f0edc9d09480c8`.

The archive contains 206 managed source files and eight public validation
fixtures. All entry hashes were rechecked locally before transfer; the remote
verifier accepted the same archive. The fresh installed-before hashes match the
recorded actual November 2 baseline, including its five known live greeting
differences. No additional managed source drift or extra source files were
found. Replacement of those five differences with the maintained wake-only
source was explicitly authorized earlier by the owner.

One managed apply was dispatched, with staging validation followed by a source
backup/replacement and the existing user-service restart. No second apply,
reboot, package installation, model replacement or firmware change was used.

Retained rollback backup:
`/home/super-alex/atlas/backups/ready-20261104-0b6cba9c/atlas-source-20261104-162539-47bffeb9`.

Remote stage: `/tmp/atlas-source-ready-95b4b99-0b6cba9c`.

## Verification

- All 206 installed managed files match the release manifest; validation
  fixtures were not installed into live content. No unexpected extra source
  file remains.
- The deployment tool's native staged validation passed before replacement.
  Its dependency, compilation and synthetic smoke gates are prerequisites for
  that successful transaction.
- Focused native mocked acceptance: **497 passed**, with **497 independently
  collected**. The selected modules cover persistent sockets, readiness cues,
  cloud speech adapters, listening workflow, pipeline, personalization, wake
  gating, introductions, admin API and Cartesia pronunciation. The existing
  wake-test port isolation uses a real ephemeral bind instead of competing
  with the running dashboard. No production port guard was changed.
- User service is active/running, with NRestarts=0 and ExecMainStatus=0.
- Laptop and loopback checks agree: `/`, `/admin`, `/health` return 200;
  `/api/admin/audio` and `/api/admin/arducam/pan/status` return 401 without auth.
- Boot ID remains `d2380f35-0a35-4b8c-be16-dbf11eb7c34f`.
- Stat metadata for `.env`, both configuration layers, both model files and
  the user unit are unchanged. No credential contents or hashes were read.
- Selected public settings, loaded with dotenv discovery disabled, confirm
  Deepgram/Cartesia, `deepgram_keep_connection=true`, `listening_ready_cue=buzz`
  and effective 1,000/2,000/600 ms pause settings. Those fields are not
  environment-overridden by the maintained loader; credentials were not loaded.

The earlier full local suite belongs to this exact immutable source snapshot:
4,618 passed/three skipped, with 4,621 independently collected. Its JUnit totals
and archive identity were rechecked this session; the full local suite was not
rerun or relabeled as fresh physical evidence.

## Laptop hotspot preference — authentication pending

The Jetson is already connected to the laptop hotspot. Fresh non-secret profile
metadata shows its auto-connect priority is lower than two other saved Wi-Fi
profiles. The requested change is limited to enabling auto-connect and raising
that existing hotspot profile above the other saved priorities. All fallback
profiles should remain unchanged. No Wi-Fi password is required or requested.

The scoped `sudo -n nmcli connection modify` attempt failed because this SSH
account lacks noninteractive administrator authentication. NetworkManager
reports system-profile modification as disallowed in this session. No priority
modification succeeded, and no disconnect or network restart was attempted.
The owner has been given the exact single nmcli command to run in the existing
Jetson SSH terminal and authenticate there privately. Verification is pending.

As documented by [NetworkManager](https://www.networkmanager.dev/docs/api/latest/settings-connection.html),
auto-connect priority chooses among available profiles during automatic
connection; it does not preempt another already active connection when a
higher-priority network later appears. The current hotspot connection can be
preserved while changing its saved priority. No automatic roaming agent is
part of this request.

## Physical acceptance and evidence

Software deployment is verified; actual Deepgram network behavior, audible
buzz/echo pickup, immediate post-buzz words and measured headset latency still
need the owner's live test. No new camera or motor exercise was performed.

Evidence is retained outside Git under
`deliverables/ready-stt-cue-deployment-20261104/`: archive, source-preservation
baseline/after metadata, apply result/backup, native test output and collection,
selected settings, laptop HTTP checks and non-secret Wi-Fi baseline. Network
names and private connection details are not copied into this public record.
