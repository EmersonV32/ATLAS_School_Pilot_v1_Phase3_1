# Historical ATLAS evidence

Nothing in this directory is an active runtime, deployment source or current
instruction. Develop and deploy from [atlas/](../atlas/) on `main`; current
procedures are in [handoff/](../handoff/README.md).

## Retained evidence

| Directory | Why it stays |
| --- | --- |
| `2026-08-04-engineering-reports/` | Two unique integration/technical-reference PDFs. |
| `2026-08-04-nationals-2026/` | Early detector datasets, training recipes, metrics, predictions and original weights; not an alternative application. |
| `2026-08-09-final-handoff-bundle/` | Historical final-handoff report PDF and its source. Their old paths/instructions are evidence only. |

The nationals `weights/last.pt` was byte-identical to `best.pt` and was
removed; `best.pt` remains. Original and pretrained model files are distinct
provenance and stay. Frozen training scripts may be inspected for reproducibility
but must not be used as current live-camera or deployment tools.

## Material retired from the working checkout on October 11

Duplicate pre-integrated runtimes, one-time Phase 4/integration patches,
superseded Jetson repair/deployment utilities, old live hotfixes, legacy
nationals hardware/RAG experiments and obsolete continuation prompts/builders
were removed after dependency checks and verified backups.

They remain in the Git tag `snapshot/repository-pre-cleanup-2026-10-11`.
The verified all-branch bundle also retains original branch-only history.
See [cleanup and recovery](../handoff/2026-10-11_REPOSITORY_CLEANUP.md) and
[the branch ledger](../handoff/BRANCHES.md).

Do not keep another full runtime here to provide rollback: use Git history and
the model/device rollback procedures. Keep only unique historical evidence with
a dated index entry. Secrets, databases, visitor media, embeddings, environments
and generated device engines must remain outside Git.
