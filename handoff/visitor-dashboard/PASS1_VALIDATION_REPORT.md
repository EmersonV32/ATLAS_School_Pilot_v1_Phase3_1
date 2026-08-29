# Pass 1 validation report

Date: 2026-08-09

Branch: `codex/atlas-onboarding-admin-live-monitor`

## Delivered

- Nine-step visitor onboarding at `/` with language as the only required
  personalization answer.
- Optional first name held only in browser memory and never accepted by the
  server schema.
- Optional numeric age reduced in the browser to `under_13`, `13_17`, or
  `18_plus`, with the numeric field cleared before progress is transmitted.
- Mock-backed, thread-safe visitor lifecycle and readiness projection isolated
  from the device runtime.
- Protected admin live monitor, readiness display, help acknowledgement,
  explicit staff stop-and-clear, and mock failure scenarios.
- Six local development artwork placeholders with explicit unapproved status.
- English validated locale metadata and French, Spanish, Italian, Arabic, and
  Traditional Chinese preview metadata. Arabic applies document-level RTL.
- Versioned static-shell service worker that never caches API responses.

## Automated evidence

- Focused dashboard suite: 52 passed.
- Complete repository suite: 230 passed, with one upstream
  `StarletteDeprecationWarning`.
- Targeted Ruff checks for all changed Python modules and tests: passed.
- JavaScript syntax checks for visitor, admin, and service worker: passed with
  the bundled Node.js runtime.
- Secret scan and staged diff whitespace checks: required again before commit.

Repository-wide Ruff is not a clean baseline. It reports 241 existing findings
in legacy patch scripts, older device modules, tests, and handoff tooling that
are outside this dashboard change. No unrelated lint rewrite was attempted.

## Browser evidence

The local FastAPI app was exercised in the in-app browser with an explicit
1024x768 viewport.

- Exact viewport: 1024x768.
- Document width: 1024; no horizontal overflow.
- Visitor help and Continue controls: no overlap.
- Console errors on visitor and admin pages: none.
- Full onboarding reaches ready, privacy, and `Start My Experience` states.
- Optional age input is empty after leaving the step.
- Admin receives only broad age guidance, interest IDs, language, and state.
- Help request is idempotent, appears in the admin monitor, can be
  acknowledged, and returns acknowledgement to the visitor.
- Staff stop clears the profile, closes an open help modal, and presents the
  thank-you screen.
- Reload during an active experience restores the in-use screen.
- Arabic preview sets `lang="ar"` and `dir="rtl"`.
- Static asset cache versioning was tested across multiple shell revisions.

## Not proven by Pass 1

- Physical iPad Safari and standalone-mode behavior.
- VoiceOver, Switch Control, and external keyboard behavior on the real iPad.
- Jetson deployment, real Shokz audio, XIAO camera, router, cloud providers,
  EV3, or real unit transfer/readiness.
- Final translations or approved production artwork assets.

The mock API seam is deliberate. Pass 2 should replace its inputs with real
unit/runtime projections while preserving the documented public contract and
privacy bounds.
