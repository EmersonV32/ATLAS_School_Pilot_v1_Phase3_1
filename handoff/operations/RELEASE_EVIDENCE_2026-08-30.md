# ATLAS laptop release evidence - 2026-08-30

This record covers the laptop-safe validation run for the audio controls,
focused admin views, public website, artwork release gate, and presentation
package. It does not replace the Jetson hardware acceptance pass.

## Source state

- Branch: `codex/jetson-runtime-reconcile`
- Runtime expansion commit: `5dc5633`
- Documentation follow-up commit at test time: `d9ea921`
- Recovery tag created before the expansion: `snapshot/pre-expansion-2026-08-30`

## Automated checks

| Check | Result |
| --- | --- |
| Full Python test suite | 303 passed; one Starlette/httpx deprecation warning |
| Ruff, patch-scoped Python files | Passed |
| Secret scan | No obvious secrets found in tracked or unignored files |
| Recovery-bundle verification | Required portable files are tracked; private and generated artifacts remain excluded |
| Git whitespace check | Passed |

## Artwork release gate

The release validator passed with:

- 7 curated artworks;
- 157 knowledge chunks;
- 7 normalized detector labels;
- no errors;
- no warnings.

The validated labels are `starry_night`, `mona_lisa`,
`tutankhamun_mask`, `sunflowers`, `liberty_leading_the_people`,
`girl_with_a_pearl_earring`, and `great_wave_off_kanagawa`.

## Browser checks

- All six admin views were opened and checked: Main, Demo, Audio/Vision,
  Visitor, Logs, and Settings.
- Judge-speaker routing, volume control, and the test-sound action were checked
  against the laptop mock runtime.
- The public site was checked at desktop and mobile widths, including horizontal
  overflow and title fit.

## Physical acceptance still required

- Switch between the real Shokz output and judge speaker while keeping the Shokz
  microphone selected.
- Listen to a complete Piper fallback response and confirm that one voice remains
  stable for the whole answer.
- Confirm camera reconnect, measured FPS, five-second artwork hold, manual
  multifunction-button capture, and emergency stop on the Jetson.
- Run the deployment script and retain its remote backup path before the live
  judge rehearsal.

GitHub Pages publication was subsequently enabled and verified at
`https://emersonv32.github.io/ATLAS_School_Pilot_v1_Phase3_1/`.
