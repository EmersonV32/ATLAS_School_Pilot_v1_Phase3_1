# ATLAS archive

This directory contains historical material that is useful for provenance,
comparison, or emergency investigation but is not part of the current ATLAS
runtime. Active development and deployment must use `../atlas/`.

## Index

| Directory | Contents |
| --- | --- |
| `2026-06-22-phase4-patch/` | Standalone Phase 4 patch utility retained for provenance. |
| `2026-08-04-engineering-reports/` | Integration and technical-reference reports. |
| `2026-08-04-integration-utilities/` | One-time inspection, patching, and demo scripts from the integration phase. |
| `2026-08-04-jetson-recovery-utilities/` | Superseded nationals-era startup, package-repair, stack-check, and one-time deployment scripts. |
| `2026-08-04-nationals-2026/` | Earlier nationals-era implementation, models, dataset, and notes. |
| `2026-08-09-final-handoff-bundle/` | Superseded handoff documents from the previous repository layout. |
| `2026-08-16-live-hotfixes/` | Superseded deployment scripts and backed-up live hotfix files. |
| `2026-08-28-pre-integrated-atlas/` | Earlier pre-integrated ATLAS source snapshot. |
| `2026-08-28-repository-transition/` | Notes from the former nested handoff layout. |

## Rules

1. Do not import, deploy, or execute archive files as part of normal ATLAS
   operation.
2. Do not repair historical path references inside archived material; they
   document the repository as it existed at that date.
3. New retired material belongs in `YYYY-MM-DD-short-description/` with a brief
   entry in this index.
4. Secrets, API keys, local databases, generated embeddings, virtual
   environments, and private visitor data do not belong here or anywhere else
   in Git.
