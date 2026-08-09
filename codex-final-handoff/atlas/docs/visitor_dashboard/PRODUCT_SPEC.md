# ATLAS visitor onboarding and live monitor product specification

Status: Pass 1 specification, mock-backed implementation target.

## Product boundary

The visitor interface is a pre-visit kiosk, not the museum guide itself. It
collects a minimal set of optional preferences, teaches the headset
interaction, verifies readiness, starts one assigned ATLAS unit, becomes
unavailable while that unit is active, and resets when staff ends the visit.

The admin interface remains the technical operator console and gains a
privacy-safe Visitor Live section. Existing health, camera, logs,
configuration, content, simulation, and safety tools remain intact.

## Version 1 environment

- One landscape 9.79-inch iPad kiosk, designed at 1024x768 CSS pixels.
- One configured wearable unit, `unit-1`, paired to `kiosk-1`.
- Touch-first controls with complete keyboard and assistive navigation.
- Local FastAPI application with no external frontend assets or analytics.

## Visitor journey

1. Animated idle state with `Touch to Begin` available immediately.
2. Language selection. This is the only required choice.
3. Optional first name and age.
4. Optional expertise.
5. Optional art interests.
6. Optional accessibility preferences.
7. Silent headset instructions.
8. Connecting and readiness.
9. Short privacy notice with a layered Learn More view.
10. `Start My Experience` when every required readiness check passes.
11. Brief cinematic transition.
12. `ATLAS is currently in use` until staff ends the session.
13. Thank-you state, then automatic reset to idle.

Onboarding abandoned for two minutes resets and erases all in-memory data.

## Data choices

- Language: required. English is the only validated public locale in Pass 1.
- First name: optional, browser-memory only, never sent in Pass 1. Admin sees
  only `name_entered`.
- Age: optional and immediately replaced with bounded response guidance. The
  number is erased and never sent.
- Expertise: first-time explorer, curious visitor, art enthusiast, or expert.
- Interests: zero or more approved manifest identifiers; equal weight and
  subtle influence only.
- Accessibility: audio description, simpler language, slower speech, shorter
  answers, or no adjustments.

## Readiness gate

Start remains unavailable until unit assignment, headset input/output, camera
freshness, content, selected-language STT/TTS, truthful answer path,
emergency-stop clearance, and profile transfer are ready. Pass 1 supplies a
truthfully labelled mock adapter; Pass 2 connects these checks to runtime
state.

## Visual direction

Warm ivory, charcoal, muted gold, and restrained artwork-inspired color. The
experience should feel calm, editorial, magical, and brief. Avoid chatbot
styling, neon AI motifs, technical cards, maps, charts, and provider language.

## Pass 1 acceptance

- Complete mock journey and staff stop/reset cycle.
- Privacy-safe admin monitoring and help acknowledgment.
- Existing dashboard API and admin operations remain compatible.
- 1024x768, keyboard, reduced-motion, and RTL layout are testable.
- No hardware, cloud provider, Jetson, or deployment change.

