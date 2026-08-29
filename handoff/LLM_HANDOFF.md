# Handoff to another LLM or developer

## Authority

- Active source: `../atlas/`
- Current documentation: this `handoff/` directory
- Historical reference only: `../archive/`
- Target Jetson install path used by the current service:
  `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`

The GitHub folder and target installation path intentionally differ. Changing
the repository layout does not require renaming a working Jetson installation.

## Required workflow

1. Read `START_HERE.md`, `CURRENT_STATE.md`, and the relevant architecture or
   operations document.
2. Inspect `git status` and recent commits before editing.
3. Follow existing module boundaries and avoid unrelated refactors.
4. Add or update focused tests for every behavior change.
5. Run the complete laptop gate and recovery verifier.
6. For deployment changes, create a backup on the Jetson, deploy, restart, and
   run the physical gate. Preserve the backup until the device passes.
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
