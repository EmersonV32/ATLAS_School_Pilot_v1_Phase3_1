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
|   `-- tests/                Automated tests
|-- handoff/                  Current operational and technical documentation
|   |-- architecture/         System and hardware boundaries
|   |-- jetson/               Rebuild, setup, and operations manuals
|   |-- operations/           Demo, pilot, and teacher procedures
|   |-- policies/             Privacy and cloud-service disclosures
|   `-- visitor-dashboard/    Product, API, localization, and test documents
`-- archive/                  Date-named historical material only
```

## Placement rules

- Code that runs ATLAS belongs in `atlas/`.
- A current procedure needed to operate or rebuild ATLAS belongs in
  `handoff/`.
- A superseded snapshot, one-time patch, or historical report belongs in a
  date-named directory under `archive/`.
- Generated output and machine-local state belong outside Git and are restored
  from installation steps or protected backup.
- There must be no second active runtime tree. A path named
  `codex-final-handoff/atlas` is obsolete.
