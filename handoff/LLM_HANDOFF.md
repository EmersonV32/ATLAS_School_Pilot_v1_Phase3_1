# Handoff to another LLM or developer

## Authority

- Maintained release/recovery branch: `main`
- Active source: `../atlas/`
- Current documentation: this `handoff/` directory
- Historical reference only: `../archive/`
- Target Jetson install path used by the current service:
  `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`

The GitHub folder and target installation path intentionally differ. Changing
the repository layout does not require renaming a working Jetson installation.
Earlier feature-branch names in dated reports are historical evidence, not
current branch instructions. Superseded source is recoverable from
`snapshot/repository-pre-cleanup-2026-10-11`, as indexed in
[`../archive/README.md`](../archive/README.md).

## Required workflow

1. Read `START_HERE.md`, `CURRENT_STATE.md`, and the relevant architecture or
   operations document.
2. Inspect `git status`, the active branch, and recent commits before editing.
   Preserve inherited work, start new implementation from `main` on a `codex/`
   feature branch, and promote it only after the validation gate passes.
3. Follow existing module boundaries and avoid unrelated refactors.
4. Add or update focused tests for every behavior change.
5. Run the complete laptop gate and recovery verifier.
6. For explicitly authorized deployment changes, create a backup on the
   Jetson, deploy the validated source, restart, and run the physical gate.
   Preserve the backup until the device passes. Repository organization or
   branch cleanup alone does not authorize hardware deployment.
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

Automated tests prove software contracts only. Camera, audio, headset, CUDA,
network, and service behavior require the target Jetson. State those two kinds
of evidence separately in every handoff.
The October 11 repository cleanup is not a new physical-device test. Keep
October 4 deployment evidence and the pending camera, voice, thermal, network,
and iPad acceptance checks explicitly dated.
