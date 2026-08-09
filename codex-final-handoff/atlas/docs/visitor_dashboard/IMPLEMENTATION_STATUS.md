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

## Pass 2 required

- Effective visitor profile in the real runtime and prompt builder.
- Real unit registry and readiness projection.
- Atomic runtime session start and local/generic greeting.
- Runtime interaction state, inactivity policy, and staff stop integration.
- Public-mode configuration and trusted-network deployment design.

## Pass 3 required

- Adversarial visual/accessibility/privacy review.
- PWA, iPad Safari, RTL, focus, and cache hardening.
- Human-validation, installation, trusted-network, Jetson-validation,
  rollback, and limitations runbooks.

## Physical validation required

No Pass 1 result proves real Jetson, Shokz, XIAO camera, router, cloud
provider, EV3, or iPad behavior. Those gates remain explicitly pending.
