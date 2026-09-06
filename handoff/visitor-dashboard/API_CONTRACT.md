# Visitor onboarding API contract

All routes are namespaced to avoid breaking the existing dashboard API.
Pydantic models reject unknown fields.

## Visitor routes

### `GET /api/visitor/bootstrap`

Returns kiosk/unit identifiers, public locale availability, onboarding steps,
interest manifest, current public state, and whether the adapter is mock or
connected to the local device runtime. Device mode exposes only safe readiness
states, never diagnostic/provider details.

### `POST /api/visitor/onboarding/progress`

Accepts only non-sensitive progress:

```json
{
  "step": "interests",
  "language": "en",
  "name_entered": true,
  "age_guidance": "13_17",
  "expertise": "curious",
  "interests": ["stories"],
  "accessibility": ["simple_language"]
}
```

There is intentionally no name or exact-age field on the progress route. Age
guidance accepts `under_7`, `under_13`, `13_17`, or `18_plus`; an entered age of
6 or younger becomes `under_7` in the browser before the numeric field is cleared.

### `GET /api/visitor/readiness`

Returns each requirement as `ready`, `pending`, `unavailable`, `degraded`, or
`unsupported`, plus public blockers and profile-transfer state.

### `POST /api/visitor/onboarding/start`

Accepts an optional visit-only local greeting name:

```json
{"greeting_name": "Emerson"}
```

The schema accepts at most 40 Unicode letters plus spaces, apostrophes, and
hyphens. The name passes directly from browser memory to local runtime memory,
is spoken only through the configured local Piper voice after the selected-
language wake phrase, remains only in runtime memory for the active visit, and
is erased on stop. It is never placed in monitoring, logs, retrieval, prompts,
status responses, or cloud requests.

The route atomically validates language, transfer state, private local voice
availability when a name was entered, and all other readiness items. In device
mode it transfers the selected language, coarse explanation profile, interests,
expertise, and accessibility choices, then starts the existing runtime session
in `waiting_for_wake` state. Dev/laptop mode creates an in-memory mock session.

### `POST /api/visitor/help`

Creates or returns the single open help request for this kiosk/unit.

### `POST /api/visitor/reset`

Stops the linked runtime session when one exists, clears all onboarding and
help state, and returns the kiosk to idle.

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

