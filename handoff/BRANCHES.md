# ATLAS branch guide and cleanup ledger

Audit date: 2026-10-11.

## Publication status

**Planned / in progress.** The decisions below describe the intended cleanup,
not proof that remote branches have already been renamed or deleted. The final
publication result must be recorded here after tests, the `main` update, and
remote-ref verification succeed.

`main` is the maintained ATLAS branch. Its application source is `atlas/`;
`handoff/` contains operating and continuity documentation. A historical or
experimental branch is not an alternative production deployment source.

## Retained work with readable names

| Intended branch | Purpose | Release boundary |
|---|---|---|
| `main` | Maintained application, current models, recovery tools, and manuals. | Publish only after the full validation gate. Physical deployment remains a separate owner-approved action. |
| `codex/history/jetson-runtime-sync-2026-08-09` | Historical Jetson integration checkpoint, preserved from `690bceb`. Much of its runtime work has since been reconciled into the maintained application. | Reference only; its nested runtime layout and startup assumptions are obsolete. |
| `codex/feature/admin-approval-copilot` | Unmerged optional admin AI prototype from `b3c56be`: allowlisted inspection, proposals, approvals, unpublished artwork drafts, routes, UI, and tests. | Not enabled, merged, or deployed by this cleanup. Requires a separate port to current `atlas/`, review, and validation. |
| `codex/research/visitor-prompt-v2-safeguards` | Unmerged visitor-prompt policy alternative from `4f52461`: authoritative museum facts, structured-response enforcement, and conservative artwork matching. | Retain for explicit product/safety review. Historical notes report an earlier Jetson rollout; that is not evidence of the currently installed implementation, and this cleanup performs no deployment. |
| `codex/feature/visitor-reliability-hardening` | Two unmerged reliability commits ending at `e51d652`: interaction cancellation, provider recovery, speech endpointing, validated streaming, conservative FAQ routing, and bounded dashboard polling. | Not merged or deployed by this cleanup. Its J1-J18 Jetson acceptance gate remains outstanding; overlaps with later v6 fixes need review, and streaming-latency effects need measurement. |

Do not copy a retained branch's old `codex-final-handoff/atlas/` tree over the
maintained application. Retention protects unique work without automatically
adding experimental features or changing visitor-answer policy.

## Recovery before retirement

The verified pre-cleanup snapshot commit is:

`b9e2002a856a6bb25ce3a643830d9eb0c516dc39`

It is preserved by the tag
`snapshot/repository-pre-cleanup-2026-10-11`. An all-ref Git bundle was also
created and verified before branch retirement. Preserve that bundle outside
the application source tree; it protects the original branch histories even
when their old remote names are removed.

To inspect the application snapshot without changing the working tree:

```bash
git show --stat snapshot/repository-pre-cleanup-2026-10-11
git ls-tree --name-only snapshot/repository-pre-cleanup-2026-10-11
```

To recover a retired branch, use its original full SHA below in a separate
feature branch or clone from the verified bundle. A Git bundle does not back up
uncommitted or untracked files. Private credentials and generated visitor/device
state remain outside Git and must follow `SECRETS_AND_PRIVATE_STATE.md`.

## Original remote branches: all 14

The counts are commits unique to each original tip relative to the audited
`main` at `f6609ebece67b57733425e9594585158d0b0d39e`. The symbolic
`origin/HEAD` alias is not a separate branch. **Retire** means remove the old
branch name only after verified backup and successful publication; its reachable
history is not erased.

| Original remote branch | Original HEAD SHA | Unique | Decision |
|---|---|---:|---|
| `main` | `f6609ebece67b57733425e9594585158d0b0d39e` | 0 | Keep; update to validated maintained source. |
| `atlas-v1-work` | `3a74e8fd8d54d4d2fd7692aea659e2ed25dd53c2` | 0 | Retire; v1 checkpoint already merged. |
| `codex-final-handoff` | `cbaac484029d87cfc7571a6a0d718a17709d9c09` | 0 | Retire; engineering handoff already merged. |
| `codex/admin-codex-operations-copilot` | `b3c56be7512aef50848946d596d3ebba7c5b581f` | 1 | Rename to `codex/feature/admin-approval-copilot`. |
| `codex/atlas-onboarding-admin-live-monitor` | `0fce3e0ea7ce437686129d4baadb64fca6474488` | 0 | Retire; onboarding/monitor work already merged. |
| `codex/jetson-runtime-reconcile` | `f969f05cbf86dbc26e5f5746d7a9654389cd36f0` | 0 | Retire; runtime/dashboard reconciliation already merged. |
| `codex/jetson-runtime-sync` | `690bceb742db526a974712745eb1cdacff05d5ac` | 1 | Rename to `codex/history/jetson-runtime-sync-2026-08-09`. |
| `codex/v6-model-handoff-2026-10-04` | `b731995ce05ef0ac92707d42322245635229be7e` | 1 | Incorporate tested v6/current work into `main`, then retire. |
| `codex/visitor-adaptive-conversation` | `6c5a25d9a3f37135bbd000f4f8fb6f370764a497` | 0 | Retire; wake/personalization work already merged. |
| `codex/visitor-kids-scripted-faq` | `ec03230a073a2245a533ea6041183ff2a8a2e9ae` | 0 | Retire; age-aware FAQ work already merged. |
| `codex/visitor-prompt-v2` | `4f52461cc3d20f020d3d618371dd01b489194665` | 1 | Rename to `codex/research/visitor-prompt-v2-safeguards`. |
| `codex/visitor-reliability-hardening` | `e51d6525800b38b4b3883c2bfd0da3c1e77765f3` | 2 | Rename to `codex/feature/visitor-reliability-hardening`. |
| `codex/visitor-runtime-bridge` | `70bb511f04fcf731d6057ed444b556b22bf53b25` | 0 | Retire; visitor/device bridge already merged. |
| `codex/visitor-sync-stability` | `e62f3c0250fda76ed25ee6b9830c4d827cd389d8` | 0 | Retire; recovery/stability work already merged. |

## Original local branches: all eight

| Original local branch | Original HEAD SHA | Unique | Decision |
|---|---|---:|---|
| `main` | `f6609ebece67b57733425e9594585158d0b0d39e` | 0 | Keep; update after validation/publication. |
| `codex/competition-info-main` | `955cea9636fb69b8a9094fe33d653ab35f124ed6` | 0 | Retire; competition information already merged. |
| `codex/jetson-runtime-reconcile` | `f969f05cbf86dbc26e5f5746d7a9654389cd36f0` | 0 | Retire; already merged. |
| `codex/rag-reliability` | `690bceb742db526a974712745eb1cdacff05d5ac` | 1 | Rename to the historical Jetson-sync name above; old local name misstates its purpose. |
| `codex/review-visitor-kids-scripted-faq` | `eaa742d4f130f4abca1d2376c3aec145b7af17f3` | 0 | Retire; FAQ release hardening already merged. |
| `codex/v6-model-handoff-2026-10-04` | `b731995ce05ef0ac92707d42322245635229be7e` | 1 | Incorporate tested current work, then retire. |
| `codex/visitor-runtime-bridge` | `70bb511f04fcf731d6057ed444b556b22bf53b25` | 0 | Retire; already merged. |
| `codex/visitor-sync-stability` | `128b55be0873a2e770af4893eb3a52deedeec3fd` | 0 | Retire; all five commits ahead of its old remote are already in `main`. |

The cleanup branch `codex/repository-cleanup-2026-10-11` was created during this
operation and is not one of those eight originals. Retire it only after its
validated contents are on `main`.

## Audit evidence and limits

- Every original local/remote head was enumerated and compared by ancestry, not
  judged obsolete solely by its date. Unique source/docs work was inspected;
  binary assets were treated as metadata and private state was excluded.
- `git rev-list --count --branches --not --remotes=origin` returned `0` before
  the cleanup snapshot: no original local-only commit was missing from the
  union of remote histories.
- GitHub reported no open pull requests during the audit; no open PR currently
  depends on an old branch name. Only the current checkout was registered as a
  worktree.
- Preserving source, passing laptop tests, and renaming branches do not prove
  Jetson, camera, audio, EV3, or school-network acceptance. No hardware deployment
  is authorized or performed by this branch cleanup.

## Final publication record

Pending the root operator's verification: record the published `main` SHA,
retained branch names/SHAs, retired local/remote names, backup location, and any
failed or deferred operation here. Do not mark the operation complete from
planned names alone.
