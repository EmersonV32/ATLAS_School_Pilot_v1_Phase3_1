# Private operations dashboard redesign — October 12, 2026

Branch: `codex/dashboard-redesign`, based on the local
`codex/conversation-listening-stability` fixes. `main` is unchanged. Nothing in
this task has been pushed or deployed; Jetson, cameras and headset were offline.
The SG90 feature remains on its separate deferred hardware branch.

## Design and operation

- Navy navigation, warm white surfaces, blue primary controls and explicit
  amber/red fault states. Local system fonts; no CDN, framework, animation,
  production build step or new runtime dependency.
- Overview prioritizes the live artwork preview, experience controls and audio.
  Logs and settings have dedicated views. All seven existing views and admin
  operations remain available. Visitor kiosk assets are unchanged and separate.
- Responsive layout verified at 1440×900, 1024×768, 768×1024, 390×844 and 320×768.
  Narrow navigation scrolls within its own bar, not the page. Compact controls
  are at least 40px high; primary controls are 44px. Visible focus, a skip link,
  reduced-motion support and explicit labels accompany colour states.

## Visible failures and truthful live status

- A persistent issue board covers emergency stop, camera freshness, preview
  failures, audio availability, component failures/degraded fallback paths,
  visitor connection/transfer/readiness, assistance requests and failed actions.
  A sticky header issue button returns to the board from long pages.
- Live faults clear only when their source reports recovery. Dismissing an
  action error does not dismiss hardware faults. A failed login stays at the
  unlock gate and does not linger after successful authentication.
- Status older than ten seconds is explicitly stale. Connection failures never
  produce a healthy banner. “Reported checks are healthy” does not certify
  provider billing, every hardware function or the physical network.
- Device/runtime frame readiness and browser preview availability are distinct.
  Failed previews remove the old image and show instructions while retrying.
  Mock/dev mode is labelled; token-free local access is not called a test mode.
- Audio input shows the reported device name, not a hard-coded headset.
  An active session is not falsely described as a microphone currently listening.
- Voice interactions now publish only outcome flags and elapsed time to the
  authenticated `/status` response. AI/interaction failures and unsuccessful
  playback are shown until the next successful outcome or a new visit. Typed
  outcomes use the same indicator. No speech, answer text, exception text, name
  or prompts enter this new projection. It is memory-only and session/generation
  guarded. An optional monitoring failure cannot interrupt visitor playback.
- Existing `/status.last_answer` compatibility is preserved. The new
  `last_interaction` field is additive; it does not alter dialogue or TTS logic.

## Resource and control safeguards

GET requests have ten-second deadlines, mutations sixty-second deadlines,
preview fetches eight-second deadlines and image decoding five-second deadlines.
These are browser request limits, not server-operation rollback: a timed-out
mutation may already have executed, so check its state before retrying.
Primary mutation controls show busy state and resist duplicate requests.
Background status polls do not overlap for the same source. Logs refresh every
five seconds only in their view (manual refresh still works). Previews request
no new frames in hidden tabs/unrelated views and refresh at most about four times
per second. Image object URLs are revoked after replacement, failures and lock.
Authentication expiry stops refresh loops. An old credential response cannot
lock a newly entered credential.

## Verification

- Final full isolated suite: **3,159 passed**, one expected skip and the
  existing non-failing Starlette/httpx deprecation warning (173.55 seconds).
  An earlier pre-outcome-projection run passed 3,151 tests (270.19 seconds).
- Thirteen focused new Python checks passed, including eight privacy/session
  outcome checks; all are included in the final full suite.
- 49 dependency-free synthetic checks execute the production admin JavaScript,
  including fallback grading, persistent errors, stale state, non-overlapping
  polls, failed previews, request timeout, duplicate mutations and credential
  races. Run `node scripts/verify_admin_logic.cjs`.
- Optional Playwright QA executes real HTML/CSS/JS against intercepted synthetic
  API responses. It does not touch browser accounts, real device endpoints or
  private configuration. Run `node scripts/verify_admin_browser.cjs OUTPUT_DIR
  [CHROME_EXECUTABLE]` with Playwright supplied by the test environment; it is
  not a production dependency. Final pass: 35 layouts, 17 control actions,
  eight recovery checks (including voice/AI outcome failure and recovery),
  2,555 text contrast comparisons and no unexpected browser errors.
- The unchanged visitor kiosk passed a fresh intercepted-API browser regression:
  33 keyboard transitions at 1024×768 with reduced motion, six interface locales,
  no overflow, missing images, browser errors or failed responses. Browser local
  and session storage and cookies remained empty; the synthetic start sent no
  greeting name. These are interface tests, not language/speech hardware tests.
- Ruff, dependency, secret, recovery and portable repository-layout checks pass.

The final full-suite and expanded browser reruns passed. Sandbox-blocked
synthetic server/test attempts were stopped; headless UI checks used intercepted
APIs, not a physical device or cloud connection. No test server is required by
the supplied dashboard QA helper.
Screenshots and synthetic test output live outside Git in
`../../repository-backups/2026-10-12-dashboard-qa/`.

## Physical acceptance still required

After an explicitly approved deployment, verify the dashboard from the intended
judge display/iPad and actual Jetson network. Check both previews, headset input
and every available audio route, a spoken answer, a controlled provider failure,
camera disconnection/recovery, assistance, session reset, and emergency stop with
safe equipment. Compare dashboard timing with real playback.
The existing XIAO camera watchdog and school-network acceptance risks are not
fixed by a dashboard redesign. No software test establishes those devices'
current health. Undetected failures without a runtime signal still require
operator investigation; this is not a universal fault detector.
