# ATLAS Visitor Reliability Hardening - Jetson Acceptance Gate

Date: 2026-09-14
Branch: `codex/visitor-reliability-hardening`

## Current status

- Development: complete on the dedicated branch.
- Local validation: complete; the commands and results are recorded in
  `docs/PATCH_HISTORY.md`.
- Merge to `main`: prohibited until the owner approves after Jetson testing.
- Jetson deployment: not performed.
- Hardware acceptance: not performed; the Jetson, cameras, XIAO, EV3, Shokz
  headset, TensorRT engine, and live cloud providers are outside local proof.

## What this gate protects

The patch keeps the dashboard available while required providers start or
recover, prevents overlapping voice and typed interactions, makes stop and
emergency-stop cancel active speech, bounds cloud waits, preserves a single TTS
voice per answer, reduces dashboard polling load, and rebuilds the RAG indexes
during deployment with rollback coverage.

Passing local tests is not permission to merge. Every item below must be
recorded as `PASS`, `FAIL`, or `NOT TESTED` on the actual Jetson.

## Pre-deployment record

1. Record the deployed commit, `systemctl --user status atlas.service`, free
   disk space, JetPack/L4T version, and the active model/index hashes.
2. Export a copy of the current ATLAS runtime log and dashboard overrides.
3. Record a baseline using the same questions, language, headset route, network,
   and artwork positions that will be used after the patch. Capture first-token,
   first-audio, total-response, retrieval, CPU, memory, and temperature data.
4. Confirm that the administrator token is available without writing it into a
   command transcript, screenshot, test artifact, or Git file.

## Required Jetson acceptance cases

| ID | Test | Pass condition | Result |
|---|---|---|---|
| J1 | Normal startup | `/health` is reachable during startup; `/ready` returns `503` until required providers are ready and then returns `200`. | NOT TESTED |
| J2 | Provider recovery | With one required provider temporarily unavailable, the dashboard remains usable and shows the failed component; restoring it makes preload recover without a process restart. | NOT TESTED |
| J3 | Camera loss | Removing only the safe-to-unplug visitor camera pauses new visual context but wake, global questions, scripted FAQ, stop, and session controls continue; reconnect restores frames. Never hot-unplug a CSI ribbon. | NOT TESTED |
| J4 | Concurrent requests | While one question is active, a second `/ask` request returns `409`; memory, audio, and logs contain only the accepted interaction. | NOT TESTED |
| J5 | Session stop | Stop during Gemini generation, Cartesia playback, and Piper playback produces no late speech and no late memory entry. | NOT TESTED |
| J6 | Emergency stop | Emergency-stop during an answer immediately stops audio and hardware motion; clear-stop works only after the active interaction releases. | NOT TESTED |
| J7 | STT fallback | Interrupting Deepgram makes the current question use local Whisper without asking the visitor to repeat it; cloud recovery happens in the background. | NOT TESTED |
| J8 | Local endpointing | After the visitor finishes speaking, Whisper/Silero ends the recording on configured silence instead of always consuming the full listen window; noisy-room false starts are checked. | NOT TESTED |
| J9 | LLM failure behavior | Timeout, empty/malformed output, and self-reported unsupported claims produce the localized safe response and are never spoken as raw JSON or unverified claims. Test all configured visitor languages. | NOT TESTED |
| J10 | RAG integrity | The deployment rebuilds SQLite and Chroma from `demo_pack`; the expected artwork set is present, source IDs resolve, and the RAG evaluation completes. | NOT TESTED |
| J11 | Admin authorization | Protected status, camera, session, question, log, and emergency routes reject a missing/wrong token and work with the configured token from the LAN admin device. | NOT TESTED |
| J12 | Dashboard load | Visitor/admin pages stay responsive with both previews active; there are no overlapping poll storms, browser console errors, or sustained CPU spikes caused by JPEG encoding. | NOT TESTED |
| J13 | Latency comparison | Re-run the identical baseline set and compare p50/p95 first-audio and total-response latency. Report the measured delta; do not claim no regression from visual impressions. | NOT TESTED |
| J14 | Soak and thermal | Run a continuous 30-minute representative visit with questions, artwork changes, camera preview, TTS, and EV3 events; record crashes, throttling, memory growth, temperature, and recovery failures. | NOT TESTED |
| J15 | Vision release | Test every artwork with the production TensorRT engine at real viewing distances, angles, glare, occlusion, and movement; record misses and class confusions. | NOT TESTED |
| J16 | Physical integration | Verify XIAO camera/network, headset input/output and button, judge speaker route, EV3 actions/e-stop, and visitor restart/recovery end to end. | NOT TESTED |

## Fast service checks

Run on the Jetson without exposing credentials:

```bash
systemctl --user status atlas.service --no-pager
curl -i http://127.0.0.1:8765/health
curl -i http://127.0.0.1:8765/ready
journalctl --user -u atlas.service -n 250 --no-pager
```

Use the configured `X-Atlas-Admin-Token` header for protected route checks.
Do not paste the token into this document or a shared log.

## Deployment and rollback boundary

Only after owner approval, run from the repository's `atlas` directory on the
Windows machine:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\deploy\DEPLOY_ATLAS_VISITOR_IMPROVEMENTS.ps1"
```

The script backs up deployed files plus `data/chroma` and `data/sqlite`, runs
the Jetson test suite, verifies/exports the production vision model, restores
device configuration, rebuilds the RAG indexes, starts the service, and accepts
the deployment only when `/ready` returns success. A failed step triggers its
remote rollback. Keep the reported `/tmp/atlas_visitor_backup_<timestamp>` path
until every Jetson case above passes.

## Release decision

Merge only when J1-J16 have recorded evidence or the owner explicitly accepts a
named exception. A failed cancellation, emergency-stop, RAG-integrity, privacy,
or admin-authorization case blocks the release.
