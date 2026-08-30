# Presentation and booth package

## Booth layout

- Center: three physical artworks at comfortable viewing height.
- Presenter side: ATLAS headset and forward-facing camera, with cable strain
  relief and a spare printed mount.
- Operator side: admin dashboard on Audio/Vision or Demo, angled away from
  visitors so tokens and logs are not visible.
- Public side: QR code to the public website, one-sentence value proposition,
  and a privacy note that the prototype may use cloud speech/language services.
- Recovery area: speaker, power bank, spare cables, previous model, and local
  demo video accessible without internet.

## Slide order

1. Museum problem and target visitor.
2. ATLAS experience in one sentence.
3. Physical system and interaction flow.
4. Live demonstration.
5. Technical architecture and content grounding.
6. Testing evidence, limitations, and recovery behavior.
7. Impact, next steps, and team roles.

## Video storyboard (60 to 90 seconds)

1. **0-8 s:** artwork first, then ATLAS logo and the line "Art that speaks with
   you."
2. **8-20 s:** visitor puts on Shokz and starts the guided onboarding.
3. **20-38 s:** camera faces Mona Lisa; recognition appears; visitor asks one
   question and one contextual follow-up.
4. **38-52 s:** spoken language switch and concise response in the new language.
5. **52-66 s:** admin operator switches to judge speaker and shows live vision.
6. **66-80 s:** quick architecture view: camera, Jetson, curated knowledge,
   speech, and headset.
7. **80-90 s:** team and closing line. End on the public website address.

Capture clean speech separately if the venue recording is noisy. Do not fake a
feature in editing; label simulated or prerecorded behavior when applicable.

## Files to keep offline

- Demo video in two common formats.
- Slides as editable source and PDF.
- Public website as the complete `website/` directory.
- Current deployment archive or Git commit identifier.
- Judge runbook, device checklist, test evidence, and architecture diagram.

## Current package files

- `ATLAS_JUDGE_PRESENTATION.pptx`: editable judge-facing slide deck.
- `RELEASE_EVIDENCE_2026-08-30.md`: laptop validation evidence and the exact
  physical checks that remain.
- `DEMO_SCRIPT.md`: the live speaking and interaction sequence.
- `DEVICE_DEMO_CHECKLIST.md`: setup, rehearsal, and recovery checklist.
- `REAL_WORLD_TEST_PLAN.md`: hardware acceptance procedure.
