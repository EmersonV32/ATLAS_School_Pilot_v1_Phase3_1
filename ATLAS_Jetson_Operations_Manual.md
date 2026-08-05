# 🚀 ATLAS Jetson Operations Manual

> **Project:** `~/atlas/ATLAS_School_Pilot_v1_integrated`\
> **Service:** `atlas.service`\
> **Dashboard:** http://127.0.0.1:8765/admin

------------------------------------------------------------------------

# 📋 Quick Reference

  -------------------------------------------------------------------------------------------------------------
  Task                         Command
  ---------------------------- --------------------------------------------------------------------------------
  Start                        `systemctl --user start atlas.service`

  Stop                         `systemctl --user stop atlas.service`

  Restart                      `systemctl --user restart atlas.service`

  Status                       `systemctl --user status atlas.service --no-pager`

  Health                       `curl http://127.0.0.1:8765/health`

  Dashboard                    `http://127.0.0.1:8765/admin`

  Live logs                    `tail -f ~/atlas/ATLAS_School_Pilot_v1_integrated/data/logs/atlas-runtime.log`
  -------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 🟢 Daily Startup

``` bash
cd ~/atlas/ATLAS_School_Pilot_v1_integrated
source ~/atlas/venvs/atlas-school-pilot/bin/activate

systemctl --user restart atlas.service
sleep 10

curl http://127.0.0.1:8765/health
```

Open:

``` text
http://127.0.0.1:8765/admin
```

Verify:

-   ✅ Dashboard loads
-   ✅ Camera preview visible
-   ✅ `/health` reports `mode=device`
-   ✅ `vision=YoloDetector`
-   ✅ STT/TTS are `ready`

------------------------------------------------------------------------

# 🔴 Shutdown

``` bash
systemctl --user stop atlas.service
```

Confirm:

``` bash
systemctl --user status atlas.service --no-pager
```

Expected:

``` text
Active: inactive (dead)
```

------------------------------------------------------------------------

# 📊 Service Commands

## Start

``` bash
systemctl --user start atlas.service
```

## Restart

``` bash
systemctl --user restart atlas.service
```

## Stop

``` bash
systemctl --user stop atlas.service
```

## Status

``` bash
systemctl --user status atlas.service --no-pager
```

------------------------------------------------------------------------

# 🌐 Dashboard

Health:

``` bash
curl http://127.0.0.1:8765/health
```

Status:

``` bash
curl http://127.0.0.1:8765/status
```

Admin page:

``` text
http://127.0.0.1:8765/admin
```

------------------------------------------------------------------------

# 📷 Camera

Download one frame:

``` bash
curl -o camera.jpg http://127.0.0.1:8765/camera/frame.jpg
file camera.jpg
```

Expected:

``` text
camera.jpg: JPEG image data
```

Test the XIAO stream:

``` bash
curl http://atlas-camera.local:81/stream
```

or

``` bash
curl http://10.0.0.25:81/stream
```

------------------------------------------------------------------------

# 📝 Logs

Recent:

``` bash
tail -100 ~/atlas/ATLAS_School_Pilot_v1_integrated/data/logs/atlas-runtime.log
```

Live:

``` bash
tail -f ~/atlas/ATLAS_School_Pilot_v1_integrated/data/logs/atlas-runtime.log
```

------------------------------------------------------------------------

# ⚙️ Auto Start

Check:

``` bash
systemctl --user is-enabled atlas.service
```

Disable:

``` bash
systemctl --user disable atlas.service
```

Enable:

``` bash
systemctl --user enable atlas.service
```

------------------------------------------------------------------------

# 🔍 Diagnostics

Who owns port 8765?

``` bash
ss -ltnp | grep 8765
```

Kill process:

``` bash
kill <PID>
```

Force:

``` bash
kill -9 <PID>
```

Service internals:

``` bash
systemctl --user show atlas.service \
-p ActiveState \
-p SubState \
-p NRestarts \
-p ExecMainStatus
```

------------------------------------------------------------------------

# 🎤 Demo Startup Checklist

-   Restart service
-   Wait 10--15 seconds
-   Open dashboard
-   Confirm camera preview
-   Confirm health endpoint
-   Verify STT/TTS = ready
-   Verify Gemini = ready
-   Ask a sample question
-   Confirm audio response

------------------------------------------------------------------------

# 🚨 Common Problems

## Dashboard won't open

``` bash
curl http://127.0.0.1:8765/health
systemctl --user restart atlas.service
```

------------------------------------------------------------------------

## Camera missing

``` bash
curl -o camera.jpg http://127.0.0.1:8765/camera/frame.jpg
file camera.jpg

curl http://atlas-camera.local:81/stream
```

If the XIAO stream works but the dashboard doesn't, restart the service.

------------------------------------------------------------------------

## Port already in use

``` bash
ss -ltnp | grep 8765
```

Do **not** manually launch Uvicorn if `atlas.service` already owns port
8765.

------------------------------------------------------------------------

## Service won't start

``` bash
systemctl --user status atlas.service --no-pager

tail -100 ~/atlas/ATLAS_School_Pilot_v1_integrated/data/logs/atlas-runtime.log
```

------------------------------------------------------------------------

## Health endpoint

``` bash
curl http://127.0.0.1:8765/health
```

Ideal response includes:

-   `mode=device`
-   `GeminiClient`
-   `DeepgramSTT ... ready`
-   `CartesiaTTS ... ready`
-   `YoloDetector`

------------------------------------------------------------------------

# 💡 Personal Notes

Keep this page updated with: - Camera IP changes - New API keys - Common
fixes - Demo procedure improvements
