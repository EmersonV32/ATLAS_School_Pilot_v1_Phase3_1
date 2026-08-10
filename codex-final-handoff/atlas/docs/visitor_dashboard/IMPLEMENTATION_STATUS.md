# Visitor dashboard implementation status

## Pass 1 target

- Product, information architecture, API, privacy, localization, asset, test,
  and iPad review contracts: specified.
- Visitor onboarding UI and Visitor Live monitor: mock-backed Pass 1 complete.
- Existing runtime/API compatibility: covered by the complete automated suite.
- Desktop browser review at an explicit 1024x768 viewport: complete, including
  the full journey, help lifecycle, operator stop, reset, reload recovery, and
  Arabic RTL preview.
- Static-shell service worker: complete with a versioned allowlist and no API
  response caching.

## Pass 2 runtime bridge

- Device mode now shares the existing `RuntimeService` with visitor onboarding.
- The visitor language and a coarse explanation profile transfer only when the
  visitor starts; the live `SessionRunner` forwards that profile to the prompt
  builder for spoken answers.
- Device-mode readiness comes from the real runtime: unit, audio pathway,
  local response connection, fresh camera frame, content, language support,
  and emergency-stop state.
- Starting is guarded by readiness and starts one shared runtime session. A
  staff stop or kiosk reset stops that runtime session before clearing the
  browser-facing state.
- Dev and laptop tests remain mock-backed. Browser onboarding is not allowed to
  expose hardware details, provider names, transcripts, answers, media, names,
  or exact ages.

## Pass 2 still required

- Local/generic spoken greeting after a visitor start.
- Runtime interaction-state and inactivity-policy validation on the physical
  Jetson.
- Public-mode configuration and trusted-network deployment design.

## Pass 3 required

- Adversarial visual/accessibility/privacy review.
- PWA, iPad Safari, RTL, focus, and cache hardening.
- Human-validation, installation, trusted-network, Jetson-validation,
  rollback, and limitations runbooks.

## Physical validation required

The runtime bridge has automated coverage but does not yet prove physical
Jetson, Shokz, XIAO camera, router, cloud-provider, EV3, or iPad behavior.
Those gates remain explicitly pending.
