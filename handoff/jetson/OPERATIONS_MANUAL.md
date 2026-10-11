# ATLAS Jetson operations manual

Documentation refreshed: 2026-10-11. These procedures do not establish new
physical acceptance or change the installed service.

The maintained source branch is `main`. The existing installed runtime stays
at `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`, using
`/home/super-alex/atlas/venvs/atlas-school-pilot` and the user service
`atlas.service`. Do not rename that installation to match a repository cleanup.

## Daily startup and shutdown

Run as `super-alex` in a Jetson terminal. Coordinate with the operator before
interrupting an active visitor experience.

```bash
systemctl --user status atlas.service --no-pager
systemctl --user start atlas.service
curl --fail http://127.0.0.1:8765/health
```

Open the visitor page at `http://127.0.0.1:8765/` or the operator dashboard at
`http://127.0.0.1:8765/admin`. Unlock admin functions privately in the dashboard;
never paste the token into documentation, screenshots, or shared output.

Confirm live readiness rather than assuming a particular provider is available:

- The service is active and `/health` responds.
- The installed configuration selects the intended device mode.
- The authenticated admin preview receives fresh camera frames.
- The selected microphone and output are ready.
- The intended language works through one complete spoken response.
- Any local or cloud fallback is honestly reported.

To stop or restart deliberately, use only the command you intend:

```bash
systemctl --user stop atlas.service
systemctl --user restart atlas.service
```

A restart interrupts listening and playback. Do not launch a second Uvicorn or
device loop while the service owns port 8765.

## Read-only diagnostics

```bash
cd /home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated
source /home/super-alex/atlas/venvs/atlas-school-pilot/bin/activate
./scripts/preflight_device.sh
python -m pip check
systemctl --user is-enabled atlas.service
systemctl --user show atlas.service -p ActiveState -p SubState -p NRestarts -p ExecMainStatus
ss -ltnp 'sport = :8765'
```

Changing service enablement, packages, device configuration, or cloud credentials
is a separate operator action, not part of routine repository organization.
Do not run a generic `apt upgrade` or unhold NVIDIA L4T packages. Read the
[setup/recovery log](ATLAS_JETSON_NX_SETUP_LOG.md) before any low-level repair.

## Camera and audio

Use **Admin > Audio / Vision** for the XIAO preview, FPS, capture controls, and
Shokz/judge-speaker routing. Use **Admin > Arducam** for the separate CSI camera;
it does not feed artwork YOLO or replace the wearable camera.

`/status`, `/camera/frame.jpg`, and Arducam admin APIs are protected endpoints.
An unauthenticated request returning 401 or 503 is not proof of camera failure.
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

## Troubleshooting and incident evidence

| Symptom | Safe first check |
| --- | --- |
| Dashboard unavailable | Inspect service status, health, current IP, and port ownership. |
| Camera unavailable | Check authenticated preview, preflight, power, and active network. |
| No speech | Confirm microphone/output selection and provider readiness. |
| Port occupied | Identify the existing process; do not start another ATLAS copy. |
| School access fails | Keep the permitted hotspot available and use the network guide. |
| Repeated restarts | Stop the experience and diagnose before changing multiple systems. |

Prototype logs can contain text when diagnostic logging is enabled. Do not copy
raw logs or private `.env` contents into Git, chat, or public tickets. Record
only sanitized error codes, component names, software versions, and timings.
Never record API key/password/token values in this manual's notes.

## Deployment and recovery

Repository cleanup alone does not deploy to hardware. For a separately approved
deployment, use the validated `main` checkout and
[`atlas/DEPLOY_ATLAS.ps1`](../../atlas/DEPLOY_ATLAS.ps1), retain its backup, and
complete the [validation checklist](../VALIDATION_CHECKLIST.md).

October 4 deployment evidence is in
[`2026-10-04_JETSON_V6_DEPLOYMENT.md`](../../atlas/docs/2026-10-04_JETSON_V6_DEPLOYMENT.md).
Treat it as dated evidence, not a claim about today's physical state. For a
replacement/freshly flashed Jetson, follow
[`REBUILD_FROM_FRESH_FLASH.md`](REBUILD_FROM_FRESH_FLASH.md). Historical source
and reports are indexed in [`archive/README.md`](../../archive/README.md).
