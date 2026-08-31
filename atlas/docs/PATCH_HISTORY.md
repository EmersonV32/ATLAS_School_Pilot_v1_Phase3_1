# ATLAS Patch History

This file is the permanent record of deployed ATLAS changes. Add one dated entry
for every future patch, including the files changed, validation run, deployment
result, and any remaining limitation. Do not remove older entries.

## 2026-08-30 - Public website language availability note

**Changed:** Added the accurate line “20 languages available on demand” beneath
the six featured languages on the public ATLAS website. The visitor and admin
dashboards were not changed.

**Validation:** Confirmed the new copy is visible on desktop and mobile, the six
featured language labels remain intact, the page has no horizontal overflow,
and the browser console reports no errors.

**Deployment result:** Prepared for the GitHub Pages workflow triggered by this
website commit.

**Remaining limitation:** The website presents six examples; the complete set
of 20 remains available through the staff-controlled admin demo selector.

## 2026-08-30 - Admin-only 20-language expansion

**Changed:**

- Expanded the admin Demo language selector from 5 to 20 ordered choices:
  English, Mandarin Chinese, Hindi, Spanish, French, Arabic, Bengali,
  Portuguese, Russian, Indonesian, German, Japanese, Telugu, Turkish, Korean,
  Vietnamese, Italian, Tamil, Thai, and Polish.
- Kept the visitor onboarding and its public language list unchanged. The wider
  list is accepted only by staff-controlled profile and demo activation paths.
- Added one shared language registry for API validation, runtime normalization,
  LLM output instructions, Deepgram, Whisper, Cartesia, and readable logs.
- Added localized manual-capture confirmations, capture failures, artwork
  invitations, and spoken language-change acknowledgements for all 20 choices.
- Added regression coverage for selector order, invalid-language rejection,
  every provider boundary, every prompt language, every localized demo message,
  and the unchanged visitor language contract.

**Validation:** Full laptop-safe suite passed: 344 tests, with one existing
Starlette/httpx deprecation warning. Patch-scoped Ruff, Python compilation,
secret scanning, recovery-bundle verification, and `git diff --check` passed.
The rendered admin page showed all 20 options in the intended order, retained a
new selection through the refresh interval, aligned every control, and had no
horizontal page or panel overflow. The visitor regression suite confirmed its
public list remains `en`, `fr`, `es`, `it`, and `zh-Hant`.

**Deployment result:** Not deployed; prepared locally for the existing
single-command Jetson deployment script.

**Remaining limitation:** The 15 added choices require the configured cloud
speech path for credible audio. Piper remains an emergency fallback only for
locally installed voices, and live pronunciation still needs a Jetson speaker
acceptance pass before a judged demo.

## 2026-08-30 - Audio controls, focused admin views, and public presentation

**Changed:**

- Added live Shokz/judge-speaker output routing, a test sound, and 0-100 volume
  control without changing the Shokz microphone route. Added availability and
  active-route telemetry to the admin API and dashboard.
- Made offline Piper fallback buffer a streamed response and synthesize it once,
  preventing the fallback model from restarting for every sentence. Cartesia
  keeps its existing continuous streaming path.
- Split the admin console into Main, Demo, Audio/Vision, Visitor, Logs, and
  Settings views. Main retains every panel; focused tabs reuse the same live
  controls and telemetry instead of maintaining duplicate state.
- Added a static public ATLAS website with full-bleed artwork, responsive
  layouts, reduced-motion support, scroll reveals, and a GitHub Pages workflow.
  The public site contains no admin endpoints, tokens, Jetson address, or local
  control surface.
- Added a Roboflow/YOLO artwork release validator. It checks model-label mapping,
  manifest uniqueness, artwork/chunk IDs, source links, dates, URLs, and declared
  languages before a detector can be released.
- Rebuilt the judge runbook and device checklist and added a real-world test
  plan, booth/slide package, 60-90 second video storyboard, permanent laptop
  release evidence, and an editable seven-slide judge deck with source-backed
  speaker notes.
- Expanded the single-command Jetson deployment bundle to include the current
  artwork-label contract and validator while preserving deployment-specific
  settings and automatic rollback.

**Validation:** Full laptop-safe suite passed: 303 tests. Ruff, Python
compilation, JavaScript syntax, workflow YAML, deployment PowerShell parsing,
secret scanning, recovery-bundle validation, and `git diff --check` passed.
Live browser checks covered every admin tab, speaker routing, test sound,
desktop public-site layout, and mobile overflow. The presentation was rendered
before and after PowerPoint export; all seven slides and source-note blocks were
visually checked with no observed clipping or distortion.

**Deployment result:** Git snapshot tag `snapshot/pre-expansion-2026-08-30`
was pushed before development. Jetson deployment remains intentionally pending;
the patch is prepared for the existing one-command deployment script. The public
site was deployed successfully from `main` through GitHub Pages and verified at
`https://emersonv32.github.io/ATLAS_School_Pilot_v1_Phase3_1/`; the page and all
local CSS, JavaScript, and image references returned HTTP 200.

**Remaining limitation:** Real Shokz/speaker switching, Piper audio quality,
camera recovery, and detector behavior require the hardware acceptance pass.

## 2026-08-30 - Unified judge demo mode

**Changed:**

- Added one authenticated `Start demo` control to the admin Experience panel.
  Visitor onboarding and the admin control now activate the same runtime-backed
  demo lifecycle, and both retain the existing explicit stop behavior.
- Made demo activation atomic: it applies language, response profile, content
  pack, and accessibility mode before creating a fresh session and resetting
  bounded conversation memory. A failed readiness check does not replace a
  session that is already running.
- Marked demo state in both privacy-bounded visitor status and runtime status so
  the admin dashboard and device loop agree on the active mode.
- Added a demo-only five-second centered-artwork hold. It selects the current
  artwork and asks a localized follow-up in English, French, Spanish, Italian,
  or Traditional Chinese.
- Scheduled proactive artwork speech between microphone windows so ATLAS does
  not speak over its own STT capture. Manual multifunction-button capture uses
  the same follow-up path while demo mode is active.
- Let a spoken artwork question use the current stable YOLO detection even
  before the five-second invitation has fired. Existing spoken language changes
  continue to synchronize the runtime and dashboard for later cycles.
- Replaced the admin panel's split direct start/stop controls with the shared
  visitor-session endpoints. The runtime remains active until an explicit End
  or Stop & clear action.

**Validation:** Full laptop-safe suite passed: 296 tests. Focused demo tests
cover authenticated start/restart, readiness-preserving failure, onboarding
activation, runtime state, five-second timing, queued speech, all five localized
invitations, language switching, and continuous listening. Python compilation,
Ruff checks, JavaScript syntax validation, and `git diff --check` passed.

**Deployment result:** Not deployed; prepared locally for the existing
single-command Jetson deployment script.

**Remaining limitation:** Live microphone, Cartesia voice, Shokz button, YOLO,
and camera timing still require one hardware acceptance pass after deployment.

## 2026-08-18 - Mandarin session activation and one-press capture

**Changed:**

- Promoted the visitor's `zh-Hant` (Traditional Chinese) selection from a
  presentation-only option to an active ATLAS language. The visitor retains
  `zh-Hant`; speech, dialogue, retrieval, and configuration boundaries map it
  to the runtime language code `zh`.
- Added `zh` to the core language enum, session language parsing, dashboard
  schemas, Deepgram STT, Cartesia TTS, and Whisper fallback language paths.
- Set the configured Shokz play/pause control action to `manual_capture`.
  Any recognized press sequence now creates one manual artwork-capture request;
  it no longer changes language or resets a session.
- Updated every visitor headset instruction and invalidated the visitor cache
  to describe one press for capture.
- Expanded the visitor deployment script so it backs up and rolls back these
  core language/button files and runs focused language, button, and visitor
  tests before restarting ATLAS.

**Validation:** Laptop-safe suite passed: 257 tests, dependency integrity,
Python compilation, repository secret scan, and artwork SHA-256 checks.

**Deployment result:** Not deployed; prepared locally.

**Remaining limitation:** The Mandarin cloud speech path and single-press
action are confirmed in code only until tested with the paired Shokz and live
providers on the Jetson.

## 2026-08-18 - Corrected independent expertise artwork files

**Changed:**

- Rebuilt `expertise-mona.webp`, `expertise-wave.webp`, and
  `expertise-ambassadors.webp` from three independent original artwork files.
  The prior files were crops from a combined triptych, so Mona Lisa and The
  Ambassadors carried a visible strip of their neighbouring artwork.
- Retained the padded `object-fit: contain` mount: each card now shows one full,
  undistorted painting in its own 4:3 frame, with neutral space where the
  original aspect ratio requires it.
- Bumped the visitor service-worker shell to `v25` and the visitor CSS/JS query
  versions to force the corrected image files to replace stale cached copies.

**Validation:** Opened each rebuilt WebP locally and confirmed it contains only
its intended artwork. Focused visitor-dashboard tests remain required before
deployment.

**Deployment result:** Not deployed; prepared locally.

## 2026-08-18 - Full expertise artwork sources

**Changed:**

- Replaced the three expertise-card image sources with the dedicated full artwork
  files: `expertise-mona.webp`, `expertise-wave.webp`, and
  `expertise-ambassadors.webp`.
- Kept the padded `object-fit: contain` gallery mount so each original composition
  remains visible without stretching or cropping.
- Bumped the visitor service-worker shell to `v24`, forcing browsers to fetch the
  corrected expertise sources immediately after deployment.

**Validation:** Focused visitor asset and cache assertions updated. Full runtime
validation occurs during the Jetson deployment.

**Deployment result:** Not deployed; prepared locally.

## 2026-08-18 - Expertise gallery mount and live Shokz reconnect check

**Changed:**

- Rebuilt only the art-familiarity media frame as the welcome gallery's padded
  `4:3` dark mount. Mona Lisa, The Great Wave, and The Ambassadors now keep
  their original composition with `object-fit: contain`; no image is cropped
  or stretched.
- Left the approved interest-card images and layout unchanged.
- Added a live Shokz OpenComm2 readiness probe that checks Pulse playback,
  Pulse capture, and ALSA playback each time the visitor readiness endpoint is
  requested.
- The readiness screen now refreshes itself every two seconds while open, so a
  headset reconnect appears without restarting ATLAS.
- Bumped the visitor service-worker shell to `v23`, preventing kiosk browsers
  from retaining the old expertise CSS or readiness JavaScript.

**Validation:** Focused visitor tests cover the new frame/cache version and a
simulated Shokz disconnect followed by reconnect. Deployment validation must
run on the Jetson because the audio-device probe requires its Pulse/ALSA stack.

**Deployment result:** Not deployed; prepared locally.

**Remaining limitation:** The headset is marked ready only when the Jetson can
see both Shokz playback and microphone endpoints. A powered-but-unpaired USB
adapter will remain unavailable, which is intentional.

## 2026-08-18 - Visitor interest panel fit and cache-test repair

**Changed:**

- Matched the interest image panel to the supplied illustration ratio (`8:3`),
  so every full-width visual fills its card without crop or letterboxing.
- Corrected the focused visitor tests to expect the current visitor shell
  version (`v22`) in both the HTML and service-worker cache allowlist.

**Validation:** PowerShell syntax validation passed for the deployment script.
Dependency-free static validation confirmed the current `v22` references in the
template, service worker, and focused tests, plus the `8:3` full-composition
interest frame. `git diff --check` passed. The focused pytest suite must still
run during Jetson deployment.

**Deployment result:** Not deployed; prepared locally.

**Remaining limitation:** The compact mobile two-column layout still uses the
same full-width images; verify it on the target kiosk display after deployment.

## 2026-08-18 - Visitor interest illustration replacement

**Changed:**

- Replaced the six placeholder interest illustrations with the user-supplied
  visual set, mapped by meaning: Stories, Technique, Symbols, History, Colour
  & light, and People & society.
- Converted the supplied PNGs into six local 1280 x 480 WebP assets (24-31 KB
  each), avoiding both network loading and the prior multi-megabyte image cost.
- Changed interest-card artwork rendering to `object-fit: contain` on a dark
  gallery mount, so the complete supplied illustration remains visible rather
  than being cropped at the top and sides.
- Bumped the offline visitor shell to `v22`; existing kiosk browsers discard
  the old placeholder assets and cache the replacement set.

**Validation:** JavaScript syntax validation passed with Node `--check`.
Dependency-free static validation confirmed all six WebPs exist, map to the six
interest ids, are 1280 x 480 WebP files, total 163,404 bytes, and appear in the
offline-cache allowlist. `git diff --check` passed. The local bundled Python
runtime does not include pytest, so the focused visitor suite must run during
Jetson deployment.

**Deployment result:** Not deployed; prepared locally.

**Remaining limitation:** The artwork illustrations are supplied for this
prototype. Confirm the final display rights before public distribution.

## 2026-08-18 - Full-composition visitor artwork gallery

**Changed:**

- Replaced the cropped welcome triptych with a true three-artwork slideshow,
  using the user-supplied original Mona Lisa, The Great Wave, and The
  Ambassadors. The fade rotates every 2.6 seconds and respects reduced-motion
  preferences.
- Rebuilt the familiarity artwork panels as real image elements inside neutral
  gallery mounts. Each image uses `object-fit: contain`, so portrait, square,
  and wide originals remain complete rather than being forced into the same
  crop.
- Generated optimized local WebP delivery files from the supplied originals:
  the largest source was reduced from 18.5 MB to a 728 KB kiosk asset. The
  visitor shell now preloads and offline-caches only these compact files.
- Bumped the visitor static shell to `v21` so old cropped assets are removed
  from existing kiosk browser caches.
- Updated the visitor deployment health check to verify all three replacement
  artwork files after service restart, so a partial asset upload rolls back
  instead of shipping a page with missing images.

**Validation:** JavaScript syntax validation passed with Node `--check`.
Dependency-free static validation confirmed all three WebPs exist, are referenced
by the template and service-worker allowlist, and the `v21` shell references
match. The local bundled Python runtime does not include pytest, so the focused
visitor suite must run during Jetson deployment.

**Deployment result:** Not deployed; prepared offline while the Jetson is
unavailable.

**Remaining limitation:** This deliberately leaves neutral margins around
portrait or wide works. The margins preserve the full composition and are not
image-loading failures.

## 2026-08-16 - Gemini general-knowledge response policy

**Changed:**

- Made museum retrieval supporting context rather than a hard answer gate.
  Gemini may now answer normal visitor questions from its own knowledge when
  RAG is missing, incomplete, or off-topic.
- Removed the prompt instruction to claim a missing fact is absent from a
  verified guide or database. The selected visitor language remains mandatory.
- Removed the response and streaming paths that replaced a normal Gemini answer
  with the old verified-context fallback after a token-overlap mismatch.
- Kept prompt-injection and content-safety protections in place.

**Validation:** Pending focused dialogue and streaming tests plus deployment.

**Deployment result:** Pending deployment.

**Remaining limitation:** Gemini still cannot guarantee every answer is correct;
it should state uncertainty for genuinely uncertain or disputed facts.

## 2026-08-16 - Visitor artwork loading and kiosk-layout correction

**Changed:**

- Replaced the 2.9 MB combined expertise artwork sprite with three independently
  compressed WebP artwork panels (about 390 KB total). Each card now reads only
  its own panel, preventing the neighboring artwork sliver visible at the card
  edge.
- Replaced the 1.6 MB PNG brand image used by the visitor shell with a 38 KB
  WebP version and preloads the initial logo and three immediate artwork assets.
- Bumped the visitor shell to `v20` so an existing kiosk cache is replaced.
  The service worker now caches the lightweight WebP files instead of the old
  multi-megabyte artwork and logo assets.
- Kept the page frame fixed to the usable kiosk viewport. Long screens now
  scroll within their current step instead of pushing titles, the progress rail,
  or the action bar outside the browser window. Switching steps resets that
  inner scroll position.
- Moved the onboarding Help control into the header, eliminating its overlap
  with Continue buttons and choice cards. The action bar no longer wraps long
  labels such as Review privacy.

**Validation:** Pending local static checks and focused Jetson visitor-suite
validation via `DEPLOY_ATLAS_VISITOR_IMPROVEMENTS.ps1`.

**Deployment result:** Pending deployment.

**Remaining limitation:** The interest tiles still use the existing local SVG
illustrations. Replacing them with licensed artwork imagery is a separate
content-design decision, not part of this loading and layout correction.

## 2026-08-16 - Admin controls and visitor presentation restoration

**Changed:**

- Restored the administrator dashboard's collapsible onboarding monitor. Its
  collapsed state is retained only for the current browser session.
- Restored Guided and Raw choices for both runtime and event logs. Guided mode
  removes timestamps and formatter noise while retaining visitor speech,
  speech-provider state, vision, response, voice, and timing events. Raw mode
  remains available for exact diagnostics.
- Protected unsaved Experience settings from the two-second dashboard refresh,
  so a language or profile selection stays visible until the operator applies
  it. Added a Save settings button to the Settings header while retaining the
  existing form submit control.
- Enlarged the visitor expertise and interest cards within their existing
  three-column layouts without distorting the artwork source aspect ratio.
- Bumped the visitor service-worker/static-shell version to `v18` so browsers
  retrieve the current localized template and styling rather than an older
  cached shell.
- Expanded the visitor deployment script to upload the dashboard API and
  runtime-service changes required by the restored Guided logs.

**Validation:** The Jetson ran `36 passed, 1 warning` for the focused visitor
suite. The shared service restarted and served the visitor and administrator
routes on port `8765`.

**Deployment result:** Deployed to the Jetson on 2026-08-16. The remote backup
path reported by the deployment wrapper was
`/tmp/atlas_visitor_backup_20260816_150519`.

**Remaining limitation:** The headset instructions are deliberately text-only
until a real, approved OpenComm2 fitting video is supplied.

## 2026-08-16 - Visitor visual hierarchy refinement

**Changed:**

- Replaced the duplicate welcome-page logo panel with an artwork-led gallery
  made from the existing, locally served expertise artwork. The header keeps
  the ATLAS brand mark, so the first screen now has one brand signal and one
  museum signal instead of two competing logos.
- Reduced the contrast of the page-wide marble veins, tightened the header and
  progress rail, and widened the main kiosk canvas for clearer use on a museum
  display or iPad.
- Refined the gold action treatment into a flatter, more premium control;
  enlarged image-led expertise and interest choices; and added a short,
  reduced-motion-safe screen transition.
- Kept the headset screen text-only until an approved fitting video exists.
  The floating help action is now always fixed inside the viewport rather than
  turning into a clipped, floating page element on narrow screens.
- Bumped the visitor cache shell to `v19` so connected devices retrieve the
  new template and visual rules.

**Validation:** Focused visitor tests and responsive browser review are
required before Jetson deployment.

**Deployment result:** Pending focused Jetson validation.

**Remaining limitation:** The welcome gallery reuses the existing local
artwork source. It is intentionally not a claim that ATLAS has licensed new
hero imagery.

## 2026-08-16 - Visitor asset deployment and administrator lock gate

**Changed:**

- The visitor deployment now includes every local visitor asset, locale, and
  manifest file. This corrects the missing ATLAS logo, hero image, expertise
  artwork, flags, and interest graphics on the Jetson.
- Bumped the visitor static cache to `v17` so a browser refresh installs a
  complete replacement shell instead of retaining the earlier missing-file
  responses.
- Replaced the buried administrator-token control with a full-page unlock gate.
  Until a valid token is accepted, the operation panels, visitor data, logs,
  camera, and controls are hidden. Server-side token checks remain unchanged.

**Validation:** `247 passed` locally on 2026-08-16. The Jetson ran `34 passed`
for the focused visitor suite, restarted the shared ATLAS service, and served
the new visitor shell plus the logo, expertise image, and interest artwork
assets with HTTP `200` responses.

**Deployment result:** Deployed to the Jetson shared service on port `8765`.
The initial deployment wrapper reported a false failure because it used an HTTP
`HEAD` check against a static route; the assets themselves had already deployed
and were verified with normal HTTP `GET` requests. The wrapper now uses that
supported check for future deployments.

**Remaining limitation:** The browser may need one normal refresh after the
service restart to activate the new service worker cache.

## 2026-08-16 - Visitor dashboard unified-service refinement

**Scope:** Visitor onboarding at `/` and the existing administrator dashboard at
`/admin`, served by the same ATLAS process on port `8765`.

**Changed:**

- Removed the visitor age minimum and maximum from the numeric entry flow. The
  runtime receives only the existing coarse age-guidance band, never an exact age.
- Kept the expertise artwork panels at their original source aspect ratio and
  enlarged the interest-card imagery without changing the six-card selection flow.
- Removed the placeholder OpenComm2 animation. The headset screen now provides
  written instructions until an approved real video is supplied.
- Made English, French, Spanish, and Italian show as ready in the visitor mock
  preview as well as in the tested device runtime. Arabic and Mandarin remain
  interface previews until their speech support is configured and validated.
- Added `DEPLOY_ATLAS_VISITOR_IMPROVEMENTS.ps1` for a timestamped backup,
  selective upload, focused tests, service restart, and same-port health check.

**Validation:** `246 passed` locally with the full Python test suite on 2026-08-16.
The first Jetson deployment attempt exposed a Python 3.10 `datetime.UTC`
compatibility failure before the service restarted. The patch now uses
`timezone.utc`, and the deployment script rolls back automatically if its
focused validation or restart fails.
The second attempt found an older Jetson admin template and visitor schema. The
deployment now uploads those dashboard dependencies together, rather than
lowering the validation standard.
ATLAS preloads its camera, RAG, speech, and TensorRT model before binding the
dashboard port. The deploy health check now waits up to 50 seconds for that
normal startup sequence instead of rolling back after two seconds.

**Deployment result:** Deployed to the Jetson on 2026-08-16. The Jetson ran
`33 passed` for the focused visitor tests, then the shared service became
healthy on `0.0.0.0:8765`. A final LAN check confirmed `200` responses for both
the visitor page and the authenticated administrator page.

**Remaining limitation:** This patch does not claim Arabic or Mandarin speech
recognition/synthesis support on the Jetson. It leaves those languages visibly
preview-only instead of falsely reporting them as ready.

## Earlier visitor dashboard work in this branch

## 2026-08-16 - Response voice stability and ambiguity guard

**Changed:**

- Disabled sentence-by-sentence TTS at the device runtime boundary. One complete
  Gemini response is now synthesized in one Cartesia request, so a second
  sentence cannot move to another voice or a fallback provider mid-answer.
- Kept RAG as supporting context but stopped collection-wide retrieval for
  deictic questions such as "Who created it?" when no artwork is identified.
  ATLAS now asks which artwork the visitor means instead of guessing the
  first high-ranking result.
- Added the current vision/manual-capture artwork ID to the dialogue prompt,
  so Gemini can distinguish a confirmed work from merely retrieved text.

**Validation planned:** the deployment script runs dialogue and pipeline tests
on the Jetson before it restarts ATLAS. Speech speed is unchanged: Cartesia
Sonic 3.5 does not currently accept a reliable speed control.

- `8de293c` - initial visitor dashboard redesign.
- `6c23d3c` - onboarding-flow refinements.
- `fe6132b` - visitor branding and preference-flow refinements.

The commit identifiers above preserve the prior patch trail when their original
date and deployment notes were not captured in this workspace.
