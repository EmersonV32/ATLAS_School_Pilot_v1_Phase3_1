# Visitor onboarding API contract

All routes are namespaced to avoid breaking the existing dashboard API.
Pydantic models reject unknown fields.

## Visitor routes

### `GET /api/visitor/bootstrap`

Returns kiosk/unit identifiers, public locale availability, onboarding steps,
interest manifest, current public state, and whether the adapter is mock.

### `POST /api/visitor/onboarding/progress`

Accepts only non-sensitive progress:

```json
{
  "step": "interests",
  "language": "en",
  "name_entered": true,
  "age_guidance": {
    "vocabulary": "plain",
    "scaffolding": "guided",
    "example_maturity": "youth",
    "minor_safety": true
  },
  "expertise": "curious",
  "interest_ids": ["storytelling"],
  "accessibility": ["shorter_answers"]
}
```

There is intentionally no name or age field.

### `GET /api/visitor/readiness`

Returns each requirement as `ready`, `pending`, `unavailable`, `degraded`, or
`unsupported`, plus public blockers and profile-transfer state.

### `POST /api/visitor/onboarding/start`

Atomically validates language, transfer state, and all required readiness
items. Pass 1 creates an in-memory mock session. Failure returns a safe error
category and does not create a partial session.

### `POST /api/visitor/help`

Creates or returns the single open help request for this kiosk/unit.

### `POST /api/visitor/reset`

Clears all onboarding and help state and returns the kiosk to idle.

## Protected admin routes

- `GET /api/admin/live-status`
- `POST /api/admin/help/{request_id}/acknowledge`
- `POST /api/admin/session/stop`
- `POST /api/admin/visitor/simulate`

They use the existing admin-token guard. When prototype authentication is
disabled, the existing loopback-only safety restriction still applies.

## Privacy exclusions

No response contains a first name, exact age, transcript, answer text, raw
audio, raw image, prompt, key, or persistent profile history. Existing camera
and runtime-log routes remain separate operator functions.

