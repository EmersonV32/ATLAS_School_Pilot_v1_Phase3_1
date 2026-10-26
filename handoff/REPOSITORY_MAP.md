# Repository map

```text
visitor-runtime-bridge/
|-- README.md                 Public project overview
|-- atlas/                    Active runtime and deployable source
|   |-- artwork-source/       Versioned source material and integrity hashes
|   |-- config/               Runtime configuration templates
|   |-- data/                 Versioned content packs and fixtures
|   |-- firmware/             Wearable/embedded firmware
|   |-- models/               Model documentation and tracked model assets
|   |-- scripts/              Startup, deployment, diagnostics, and recovery
|   |-- src/atlas/            Python package
|   |-- tests/                Automated tests
|   |-- docs/                 Dated change evidence and model/network how-tos
|   `-- training/             Reproducible dataset and trainer workflows
|-- handoff/                  Current operational and technical documentation
|   |-- architecture/         System and hardware boundaries
|   |-- jetson/               Rebuild, setup, and operations manuals
|   |-- operations/           Demo, pilot, and teacher procedures
|   |-- policies/             Privacy and cloud-service disclosures
|   |-- visitor-dashboard/    Product, API, localization, and test documents
|   `-- BRANCHES.md           Branch purposes, retirement and recovery ledger
|-- website/                  Public Pages site (not the Python dashboard)
|-- comp_info/                Current WRO rules, logistics and evidence binder
|-- resources/3ddesigns/      Vendor CAD reference models
`-- archive/                  Historical reports and detector research only
```

## Placement rules

- Code that runs ATLAS belongs in `atlas/`.
- A current procedure needed to operate or rebuild ATLAS belongs in
  `handoff/`.
- Unique historical reports or training evidence belong in a date-named
  directory under `archive/`. Duplicate runtime snapshots and obsolete patch
  utilities do not belong in the current checkout; recover them from Git.
- Generated output and machine-local state belong outside Git and are restored
  from installation steps or protected backup.
- There must be no second active runtime tree. A path named
  `codex-final-handoff/atlas` is obsolete.

## Find the right starting point

| Task | Read first |
| --- | --- |
| Take over during the owner's absence | [Teammate handoff](2026-10-26_TEAMMATE_HANDOFF.md), [new Codex prompt](NEW_CODEX_PROMPT.md) |
| Deploy or roll back a source change | [Deployment runbook](DEPLOYMENT_RUNBOOK.md) |
| Understand today's source and device evidence | [Current state](CURRENT_STATE.md) |
| Continue development | [Start here](START_HERE.md), then [developer guide](DEVELOPER_GUIDE.md) |
| Rebuild or operate the Jetson | [Jetson rebuild](jetson/REBUILD_FROM_FRESH_FLASH.md) |
| Update detector weights | [Model guide](../atlas/models/README.md) and [training](../atlas/training/README.md) |
| Configure school networking | [School Wi-Fi](../atlas/docs/SCHOOL_WIFI_SETUP.md) |
| Find commands safely | [Script index](../atlas/scripts/README.md) |
| Edit the public site | [Website guide](../website/README.md) |
| Prepare competition evidence | [Competition binder](../comp_info/README.md) |
| Recover removed files or branches | [Cleanup record](2026-10-11_REPOSITORY_CLEANUP.md), [branch ledger](BRANCHES.md) |

The current continuation branch is `codex/camera-offline-demo-2026-10-25`;
its later fixes are not promoted to `main`. The runtime directory remains
`atlas/`. The existing Jetson installation is intentionally still at
`/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`; cleaning Git does not
rename that installation or change running services.
