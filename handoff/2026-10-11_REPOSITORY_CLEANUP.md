# Repository organization and recovery — October 11, 2026

## Scope and source

`main` is the maintained ATLAS source; `atlas/` remains the one active runtime.
The audit covered all 14 remote and eight original local branch tips, their
ancestry and unique commits, and all tracked-file inventories. Current public
source/docs received reference and focused source review. Binary assets were
reviewed by metadata/hash/dependency checks, not interpreted as source text.
Large retired code snapshots were inventoried and compared, not all reread
line-by-line. Private secrets, visitor records, generated datasets and local
environments were excluded deliberately.

This operation reorganizes the Git repository, not the entire parent workspace.
Other repositories, personal design/training output, ignored tools/environments
and credentials are untouched. No physical deployment or service/network/
firmware change is performed.

## Organization

| Area | Purpose |
| --- | --- |
| [atlas/](../atlas/) | Application, tests, configuration, content, firmware, models and maintenance scripts. |
| [handoff/](README.md) | Current operational/continuation guidance, dated evidence and branch ledger. |
| [website/](../website/README.md) | Public static Pages site; deployment is restricted to `main`. |
| [comp_info/](../comp_info/README.md) | Current competition rules, logistics and evidence binder. |
| [resources/](../resources/README.md) | Unique vendor CAD references. |
| [archive/](../archive/README.md) | Unique historical reports and model-training evidence only. |

Indexes were added rather than relocating runtime paths, preserving imports,
deployment scripts, recovery manifests, firmware compilation and the installed
Jetson location. Contradictory old branch/deployment statements are now labelled
as dated history. Model, script and networking entry points are linked centrally.
Cloud/privacy guidance now distinguishes actual optional provider flows from
older local-only assumptions.

## Removed or relocated

- 213 obsolete archived text/code files: parallel runtimes, duplicate patches,
  legacy hardware/RAG experiments, outdated repair/deployment utilities and
  superseded handoff prompts/builders.
- One archived `last.pt`, byte-identical to retained `best.pt` (20,760,322 bytes).
- Three unreferenced Python prototypes and seven unused visitor SVGs.
- Two unused lossless design PNGs relocated to
  [artwork-source/design/](../atlas/artwork-source/design/README.md), with
  pre/post-move SHA-256 equality checks. Runtime WebP assets are unchanged.

Total: 224 genuinely retired files; two preserved source images moved, not
discarded. All removals are recoverable. Current model release evidence,
previous weights, dataset/training lineage, original artwork manifests, required
embedded camera controls, CAD, website assets and competition PDFs remain.

## Branch decisions

Nine superseded remote branch names are retired after their maintained work is
in `main`. Four branches with unique history/features/research are retained
under descriptive names, without merging experimental behavior. The complete
original SHA ledger and actual publication outcome are in [BRANCHES.md](BRANCHES.md).

## Recovery safeguards

Before any removal, all-ref Git bundles were created and verified. The prior
uncommitted v6/runtime/Wi-Fi work was tested and preserved as commit
`b9e2002a856a6bb25ce3a643830d9eb0c516dc39`, tagged
`snapshot/repository-pre-cleanup-2026-10-11`.

Owner-local backups are outside this repository at:

```text
C:\Users\zhupo\OneDrive - College Sainte-Anne\Documents\ChatGPT\ATLAS\repository-backups\2026-10-11-before-cleanup\
  all-branches-before-cleanup.bundle
  all-branches-and-local-integration.bundle
  duplicate-nationals-last.pt
```

These machine-local paths are not runtime or fresh-clone dependencies. To
inspect retired content without changing the checkout:

```bash
git show snapshot/repository-pre-cleanup-2026-10-11:archive/README.md
git ls-tree -r --name-only snapshot/repository-pre-cleanup-2026-10-11 archive/
```

Recover a specific file from the snapshot or a branch from its full SHA in a
separate recovery checkout. Clone the verified bundle if an original remote
ref is no longer available. The bundles contain Git objects, not private
credentials or ignored/untracked state; those remain under the owner's separate
private-state handling.

## Validation record

Baseline before cleanup: 3,033 passed, one expected skip. Focused runtime-hygiene
regressions: 123 passed. All 31 pre-existing maintained-code Ruff findings were
resolved with mechanical imports, formatting, annotations and explicit
`zip(..., strict=False)` to retain existing truncation behavior.

Post-cleanup full regression: **3,055 passed, one expected skip**, with the
existing non-failing Starlette/httpx deprecation warning. Maintained Ruff,
compileall, dependency consistency, secret scan, recovery manifests, navigation
and staged whitespace checks passed.

Isolated browser validation used a fresh headless Chrome profile and synthetic
DEV/mock server: 33 keyboard-driven states at 1024x768 with reduced motion,
complete English onboarding/back/headset/readiness/privacy/start/reset flow,
and all six language choices. No browser errors, HTTP failures, missing images,
outer-page overflow or persistent visitor storage appeared. Screenshots were
visually reviewed and the synthetic server stopped. Optional name/age entry,
Safari/iPad and all physical devices remain outside this browser claim.

Final clean-checkout full suite: **3,080 passed, one expected skip**, with the
same existing non-failing deprecation warning. The separately reviewed early
startup safeguard passed 97 focused startup/device/handoff regressions,
including the final IPv6-only parity correction. Fresh-checkout Ruff,
secret/recovery/navigation checks and shell LF normalization passed without
ignored local source/state. The existing laptop Python environment supplied
dependencies; this was not a fresh Jetson installation or new dependency stack.
The maintained checkout now has 516 tracked files.

No laptop check proves live camera, speech, school-network or Jetson thermal
acceptance. The owner explicitly confirmed that the Jetson, camera and headset
are offline.

The launcher now refuses an active user `atlas.service` before activating the
environment. Device-loop startup probes its configured dashboard address before
loading expensive adapters. IPv4/IPv6 fallback, occupied/invalid bindings,
disabled dashboards and unavailable systemd are covered by synthetic tests.
The probe releases its socket immediately: this reduces ordinary duplicate
starts, but is not a race-free singleton lock. Actual server binding still
occurs later and is independently checked.

## Performance boundaries

Runtime startup does not scan or import archived evidence, training datasets,
CAD, release history or the public website. It reads configured model artifacts
and integrity sidecars; static assets are served on request. Their retained
size is not a per-frame or normal-startup processing cost. No physical FPS,
latency, memory or thermal improvement was measured during this cleanup.

Two existing behaviors need separate product/device validation rather than a
blind merge from an experimental branch: required-component preload failures
occur before dashboard startup and can trigger systemd retries; explicit
authenticated Arducam preview can open CSI hardware even in dev mode when
enabled. Do not use live preview as a hardware-inert test. The independent
camera stream-watchdog race remains open in [current state](CURRENT_STATE.md).
