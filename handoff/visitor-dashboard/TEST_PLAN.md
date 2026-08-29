# Visitor dashboard test plan

## Automated tests

- Visitor and admin pages remain available and existing routes stay compatible.
- Language is required to start; every other preference is optional.
- Name and exact age are rejected by API schemas and absent from live/admin
  status, logs, and serialized profile state.
- Help is idempotent, acknowledgment updates the kiosk, and staff stop clears
  the mock session and profile.
- Admin live and mutating routes use the existing authentication guard.
- Service-worker allowlists contain static assets only and exclude `/api/`.
- Visitor HTML contains no admin link, camera, YOLO, confidence, latency,
  provider, transcript, or technical runtime label.
- Landmarks, headings, labels, focus controls, RTL, and reduced-motion rules
  are present.

## Visual review

At 1024x768 landscape inspect idle, language, interests, accessibility,
readiness, privacy, in-use, thank-you, help/error, RTL, and reduced-motion
states. Also inspect Visitor Live during onboarding, active use, help, and a
readiness blocker.

## Physical review deferred

VoiceOver, Switch Control, Safari Guided Access, gallery lighting, stand
height, router reconnection, Shokz readiness, and real session start require
the physical iPad/Jetson environment and are not Pass 1 claims.

