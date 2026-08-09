# Visitor onboarding privacy model

## Data minimization

| Input | Lifetime | Server | Admin |
|---|---|---|---|
| Language | Session | Yes | Yes |
| Optional first name | Onboarding memory only | No in Pass 1 | Boolean only |
| Exact age | Until client derivation | Never | Never |
| Derived age guidance | Session | Yes | Summary |
| Expertise/interests/accessibility | Session | Yes | Yes |
| Raw audio/images | In-memory runtime processing | Not stored | Existing live camera only |

The browser must not use cookies, localStorage, sessionStorage, or IndexedDB
for visitor state. Reset, inactivity, staff stop, or page reload erases the
Pass 1 profile.

## Public versus prototype logging

Public mode requires transcript, live STT, and LLM-response logging to be off.
Raw media and face data remain off in every mode. The repository's current
prototype YAML still enables text logging for engineering tests; it must not
be described or deployed as public mode.

## Cloud disclosure

ATLAS is edge-first, not fully offline. Depending on the approved runtime
configuration, question audio may reach a speech-to-text provider, question
text and retrieved museum facts may reach the language-model provider, and
answer text may reach text-to-speech. The onboarding profile must not widen
those flows in Pass 1.

## Threat controls

- Pydantic rejects name, age, and unknown fields at API boundaries.
- Admin live data is generated from a dedicated privacy-safe projection.
- Mutating admin routes share the established token guard.
- Static cache rules exclude `/api/` and every non-static response.
- Help requests contain only request ID, kiosk, unit, timestamps, and state.

