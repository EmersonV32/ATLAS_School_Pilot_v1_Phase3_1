# ATLAS Patch History

This file is the permanent record of deployed ATLAS changes. Add one dated entry
for every future patch, including the files changed, validation run, deployment
result, and any remaining limitation. Do not remove older entries.

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
