# Handoff to another LLM or developer

## Authority

- Current continuation branch: `codex/camera-offline-demo-2026-10-25`
  (later working fixes are not promoted to `main`)
- Active source: `../atlas/`
- Current documentation: this `handoff/` directory
- Historical reference only: `../archive/`
- Target Jetson install path used by the current service:
  `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`

The GitHub folder and target installation path intentionally differ. Changing
the repository layout does not require renaming a working Jetson installation.
Start with the [October 26 handoff](2026-10-26_TEAMMATE_HANDOFF.md) and
[new Codex prompt](NEW_CODEX_PROMPT.md). Earlier feature-branch names in older
reports are historical evidence. Superseded source is recoverable from
`snapshot/repository-pre-cleanup-2026-10-11`, as indexed in
[`../archive/README.md`](../archive/README.md).

## Required workflow

1. Read `START_HERE.md`, `CURRENT_STATE.md`, and the relevant architecture or
   operations document.
2. Inspect `git status`, the active branch, and recent commits before editing.
   Preserve inherited work and base new `codex/` work on the current
   continuation branch. Do not merge into `main` without an explicit request.
3. Follow existing module boundaries and avoid unrelated refactors.
4. Add or update focused tests for every behavior change.
5. Run the complete laptop gate and recovery verifier.
6. For explicitly authorized deployment changes, coordinate with the present
   operator and any peer chat, then follow the
   [deployment runbook](DEPLOYMENT_RUNBOOK.md). Preserve its backup and verify
   device acceptance. The teammate can authorize scoped work during the
   owner's absence; the handoff itself grants no standing device approval.
7. Update `CURRENT_STATE.md` and relevant troubleshooting material when the
   verified operating state changes.

## Architectural constraints

- Retrieval is evidence for museum-specific questions, not a command to answer
  every question with the highest-scoring artwork.
- Dialogue context must resolve immediate follow-ups while expiring superseded
  subjects.
- Speech synthesis must select one provider/voice per complete response. A
  provider failure may affect the next response; it must not splice a different
  voice into the current sentence.
- Manual capture is a first-class input path and must remain usable when
  automatic recognition is uncertain.
- Dashboard controls must reflect runtime state rather than simulate hardware
  readiness.
- Privacy documentation must match the actual cloud providers and retained
  data.

## Before claiming success

Normal SG90 pan remains disabled and commissioning is paused. Do not restart
motor experiments automatically. Never read or publish credentials, admin
codes, private environment files, visitor records, or raw media. Use the
guarded test runner before collection and selected service metadata instead
of journal/log dumps.

Automated tests prove software contracts only. Camera, audio, headset, CUDA,
network, and service behavior require the target Jetson. State those two kinds
of evidence separately in every handoff.
The latest verified runtime deployment is `4b2233c` on October 25, not proof
that today's device is unchanged. Audible pronunciation, current networking,
camera/headset, thermal, and iPad acceptance must remain explicitly dated.
