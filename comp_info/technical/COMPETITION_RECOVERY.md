# Competition Technical Readiness And Recovery

This guide complements the operational manuals in `../../handoff/`.

## Freeze Package

The final competition release must have:

- Git commit and release tag;
- exact model weights and checksums;
- dependency lock and Jetson install instructions;
- sanitized configuration template;
- encrypted backup of runtime configuration and secrets;
- Jetson disk/partition image or proven rebuild path;
- two local recovery drives in separate bags;
- one remote backup;
- printed startup, shutdown, and recovery card.

Never commit API keys, Wi-Fi credentials, admin tokens, or private participant
information.

## Required Failure Drills

- cold boot with all hardware connected;
- start with camera disconnected, then reconnect it;
- disconnect/reconnect Shokz and restore microphone/output automatically;
- Cartesia outage with Piper fallback;
- Gemini/network outage with an honest degraded experience;
- dashboard device reconnect and IP change;
- camera stream interruption and recovery;
- model load failure and rollback;
- high temperature and controlled shutdown;
- accidental service stop;
- corrupted local configuration restored from template;
- replacement of each field-replaceable cable/device.

Record every drill in `../templates/FAILURE_DRILL_LOG.csv`.

## Reliability Acceptance Targets

Set final numeric targets from measured baseline; do not invent them. At
minimum, acceptance should cover:

- consecutive successful full demos;
- cold-boot-to-ready time;
- artwork detection accuracy on held-out real images;
- end-to-end response latency;
- camera FPS and reconnect time;
- maximum temperatures during an eight-hour booth test;
- battery duration where batteries are used;
- restart and full-restore time.

## Judge-Day Failure Order

1. Keep speaking and explain what ATLAS is designed to do.
2. Preserve functioning subsystems instead of restarting everything instantly.
3. Attempt the single rehearsed local correction.
4. Perform one clean service restart if the correction fails.
5. Use recorded proof and measured results while another member recovers the
   system.
6. Do not deploy untested code or model files at the booth.

## Project-Specific References

- [Operations manual](../../handoff/jetson/OPERATIONS_MANUAL.md)
- [Troubleshooting guide](../../handoff/TROUBLESHOOTING.md)
- [Fresh-flash rebuild](../../handoff/jetson/REBUILD_FROM_FRESH_FLASH.md)
- [Validation checklist](../../handoff/VALIDATION_CHECKLIST.md)
- [Demo script](../../handoff/operations/DEMO_SCRIPT.md)
- [Privacy policy](../../handoff/policies/PRIVACY.md)
- [Cloud disclosure](../../handoff/policies/CLOUD_LLM_DISCLOSURE.md)
