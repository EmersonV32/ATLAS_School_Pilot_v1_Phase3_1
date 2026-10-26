# ATLAS Jetson operations manual

Documentation refreshed: 2026-10-26. Read the
[current teammate handoff](../2026-10-26_TEAMMATE_HANDOFF.md). These procedures
do not establish new physical acceptance or change the installed service.

The continuation branch is `codex/camera-offline-demo-2026-10-25`; later fixes
are not promoted to `main`. Last verified installed runtime is `4b2233c`
(October 25); recheck current state. The existing installed runtime stays
at `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`, using
`/home/super-alex/atlas/venvs/atlas-school-pilot` and the user service
`atlas.service`. Do not rename that installation to match a repository cleanup.

## Daily startup and shutdown

Run as `super-alex` in a Jetson terminal. Coordinate with the operator before
interrupting an active visitor experience.

```bash
systemctl --user show atlas.service -p ActiveState -p SubState -p NRestarts -p ExecMainStatus
curl --fail --max-time 5 http://127.0.0.1:8765/health
```

Open the visitor page at `http://127.0.0.1:8765/` or the operator dashboard at
`http://127.0.0.1:8765/admin`. Unlock admin functions privately in the dashboard;
never paste the token into documentation, screenshots, or shared output.

Confirm live readiness rather than assuming a particular provider is available:

- The service is active and `/health` responds.
- The installed configuration selects the intended device mode.
- Conversation may start with the primary camera degraded/offline. Fresh
  authenticated frames are required when demonstrating capture instead.
- The selected microphone and output are ready.
- The intended language works through one complete spoken response.
- Any local or cloud fallback is honestly reported.

After operator approval, use only the ONE start/stop/restart command you intend:

```bash
systemctl --user start atlas.service
systemctl --user stop atlas.service
systemctl --user restart atlas.service
```

A restart interrupts listening and playback. Do not launch a second Uvicorn or
device loop while the service owns port 8765.

## Read-only diagnostics

```bash
systemctl --user is-enabled atlas.service
systemctl --user show atlas.service -p ActiveState -p SubState -p NRestarts -p ExecMainStatus
ss -ltnp 'sport = :8765'
```

Changing service enablement, packages, device configuration, or cloud credentials
is a separate operator action, not part of routine repository organization.
Do not run a generic `apt upgrade` or unhold NVIDIA L4T packages. Read the
[setup/recovery log](ATLAS_JETSON_NX_SETUP_LOG.md) before any low-level repair.
Do not use `systemctl status`, journal dumps, or raw application logs as shared
diagnostics: they can expose visitor/private text. Deeper scripts require
review of their current scope before execution; do not run every helper.

## Camera and audio

Use **Admin > Audio / Vision** for the XIAO preview, FPS, capture controls, and
Shokz/judge-speaker routing. Use **Admin > Arducam** for the separate CSI camera;
it does not feed artwork YOLO or replace the wearable camera.

`/status`, `/camera/frame.jpg`, and Arducam admin APIs are protected endpoints.
An unauthenticated 401 is expected, not proof of camera failure. A 503 may
indicate missing configuration. Current protected examples include
`/api/admin/audio` and `/api/admin/arducam/pan/status`.
Use the admin UI rather than placing secrets in shell command arguments.

Do not save frames, video, raw audio, or visitor transcripts while following
this guide. Avoid a second direct MJPEG stream client: it can compete with
ATLAS's camera reader. A short preview is not evidence of sustained streaming,
model accuracy, or thermal safety.

The previously diagnosed stream-watchdog issue and remaining camera, voice,
thermal, and iPad acceptance checks are tracked in
[current state](../CURRENT_STATE.md). Repository cleanup does not fix or prove
those hardware behaviors.

## Networking and SSH

On the Jetson:

```bash
hostname -I
nmcli -f DEVICE,TYPE,STATE,CONNECTION device status
nmcli -f NAME,TYPE connection show --active
```

From another authorized device, try `ssh super-alex@super.local`. This requires
mDNS resolution and permitted peer traffic. Otherwise use the current IP from
`hostname -I`; the historical home address is not a permanent endpoint.

See [school Wi-Fi setup](../../atlas/docs/SCHOOL_WIFI_SETUP.md) for the optional
school-first/hotspot-fallback profiles. The camera and Jetson select networks
independently, and authentication does not prove peer reachability.
Do not change an active SSH connection's network without local-console recovery.
Do not expose SSH, the admin dashboard, or camera streams to the public internet.
The October 26 working arrangement was human-reported Windows hotspot sharing,
with Jetson IP `192.168.137.193`. Do not assume that address is permanent or
that direct school authentication is solved. Browser and local SSH-tunnel
instructions are in the current handoff. Keep the hotspot-host laptop awake.

## Troubleshooting and incident evidence

| Symptom | Safe first check |
| --- | --- |
| Dashboard unavailable | Inspect service status, health, current IP, and port ownership. |
| Camera unavailable | Primary camera is reported damaged/offline; use camera-free conversation. Review authenticated readiness for the specific camera feature. |
| No speech | Confirm microphone/output selection and provider readiness. |
| Port occupied | Identify the existing process; do not start another ATLAS copy. |
| School access fails | Keep the permitted hotspot available and use the network guide. |
| Repeated restarts | Stop the experience and diagnose before changing multiple systems. |

Prototype logs can contain text when diagnostic logging is enabled. Do not copy
raw logs or private `.env` contents into Git, chat, or public tickets. Record
only sanitized error codes, component names, software versions, and timings.
Never record API key/password/token values in this manual's notes.

## Deployment and recovery

Documentation publication does not deploy to hardware. For a separately
approved deployment, follow the current
[source-only deployment and rollback runbook](../DEPLOYMENT_RUNBOOK.md),
retain its backup, and complete the relevant
[validation checklist](../VALIDATION_CHECKLIST.md). Do not use the older broad
installer or reconfigure a working service for an ordinary source update.

October 4 deployment evidence is in
[`2026-10-04_JETSON_V6_DEPLOYMENT.md`](../../atlas/docs/2026-10-04_JETSON_V6_DEPLOYMENT.md).
Treat it as dated evidence, not a claim about today's physical state. For a
replacement/freshly flashed Jetson, follow
[`REBUILD_FROM_FRESH_FLASH.md`](REBUILD_FROM_FRESH_FLASH.md). Historical source
and reports are indexed in [`archive/README.md`](../../archive/README.md).
