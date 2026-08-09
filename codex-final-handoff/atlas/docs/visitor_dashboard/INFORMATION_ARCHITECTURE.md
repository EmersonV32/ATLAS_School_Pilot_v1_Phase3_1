# Visitor dashboard information architecture

## State model

```text
idle -> language -> about -> expertise -> interests -> accessibility
     -> headset -> readiness -> privacy -> ready -> starting -> in_use
     -> thank_you -> idle
```

Temporary sheets can appear over the current state for expanded interests,
privacy detail, reconnection, retry, help, unit unavailability, profile
transfer failure, and headset attention.

## Navigation rules

- Language is required before advancing.
- Every other preference screen offers a neutral choice or manual Continue.
- Back and progress dots remain available throughout onboarding.
- Auto-advance may reinforce a single selection, but is never the only path.
- Reduced-motion and assistive paths use manual, restrained transitions.
- The in-use state exposes only return instructions and help.

## Admin hierarchy

Visitor Live appears near the top of `/admin` and summarizes:

1. Kiosk and unit assignment.
2. Onboarding or session state.
3. Non-sensitive preferences.
4. Readiness and connection blockers.
5. Help request and acknowledgment.
6. Staff stop and explicit simulation controls.

Technical health, camera, settings, content, logs, and emergency controls
remain in their existing sections.

## Responsive boundary

The visitor interface is optimized for 1024x768 landscape and remains usable
on larger landscape tablets and desktop. Phone-first layouts are out of scope
for Version 1. Admin remains desktop-oriented.

