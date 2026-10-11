# ATLAS maintenance scripts

Run scripts from `atlas/` unless their own instructions say otherwise. Commands
in this directory are tools, not startup steps to run indiscriminately. Device,
network, credential, deployment and live-cloud checks can change external state
or send data; use only for an explicitly requested operation.

| Purpose | Maintained entry points |
| --- | --- |
| Safe laptop regression | `run_deployment_pytest.py`, `check_no_secrets.py`, `verify_recovery_bundle.py`, `verify_repository_layout.py` |
| Jetson installation/startup | `bootstrap_jetson.sh`, `install_user_service.sh`, `start_device.sh`, `atlas.service`; see [rebuild manual](../../handoff/jetson/REBUILD_FROM_FRESH_FLASH.md) |
| Transactional deployment | [DEPLOY_ATLAS.ps1](../DEPLOY_ATLAS.ps1), `deploy/DEPLOY_ATLAS_VISITOR_IMPROVEMENTS.ps1`, `deploy/apply_visitor_patch.sh` |
| Network and credentials | `configure_school_wifi.py`, `verify_school_firmware.ps1`, `configure_cloud_keys.sh`; see [school guide](../docs/SCHOOL_WIFI_SETUP.md) |
| Device readiness | `preflight_device.sh`, `check_arducam.sh` |
| Model recovery/export | `restore_models.sh`, `verify_yolo_checkpoint.py`, `export_tensorrt.py`, `promote_staged_engine.py`; see [model guide](../models/README.md) |
| Model evaluation | `smoke_yolo_runtime.py`, `benchmark_yolo_backends.py`, `inspect_yolo_results.py`, `validate_artwork_release.py` |
| Dataset diagnosis/preparation | `audit_yolo_dataset_splits.py`, `diagnose_yolo_dataset.py`, `diagnose_yolo_images.py`, `build_phone_yolo_dataset.py`, `finetune_yolo_phone.py`; also [training workflow](../training/README.md) |
| Retrieval evaluation | `evaluate_rag.py` |
| Explicit live audio/vision checks | `shokz_live_loopback.py`, `test_cloud_speech_live.py`, `test_listening_cue.py`, `test_manual_capture_gemini.py`, `test_silero_vad.py` |

`run_deployment_pytest.py` disables real dotenv/discovered credential loading
while allowing synthetic test fixtures. It does not flash cameras or exercise
physical devices. Run `ruff check src tests scripts` alongside it. Training
recipes and frozen release scripts have separate reproducibility requirements
and are not included in this maintained-code lint scope.
