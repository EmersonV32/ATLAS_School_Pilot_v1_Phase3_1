# Visitor onboarding privacy model

## Data minimization

| Input | Lifetime | Server | Admin |
|---|---|---|---|
| Language | Session | Yes | Yes |
| Optional first name | Until first wake greeting | Local memory only | Boolean only |
| Exact age | Until client derivation | Never | Never |
| Derived age guidance | Session | Yes | Summary |
| Expertise/interests/accessibility | Session | Yes | Yes |
| Raw audio/images | In-memory runtime processing | Not stored | Existing live camera only |

The browser must not use cookies, localStorage, sessionStorage, or IndexedDB
for visitor state. The optional name crosses the local API only in the start
request, bypasses cloud TTS through the private Piper path, and is erased from
runtime memory immediately after the first greeting. Reset, staff stop, or page
reload erases the remaining browser profile.

## Public versus prototype logging

Public mode requires transcript, live STT, and LLM-response logging to be off.
Raw media and face data remain off in every mode. The repository's current
prototype YAML still enables text logging for engineering tests; it must not
be described or deployed as public mode.

## Cloud disclosure

ATLAS is edge-first, not fully offline. Depending on the approved runtime
configuration, question audio may reach a speech-to-text provider, question
text and retrieved museum facts may reach the language-model provider, and
answer text may reach text-to-speech. The onboarding profile does not widen
those cloud flows. Exact names are excluded from prompts, RAG, cloud LLM,
cloud TTS, monitoring, and logs. Only allow-listed art interests and
explanation styles persist in memory for the active session.

## Threat controls

- Pydantic rejects names on progress, exact ages, unknown fields, and unsafe
  greeting-name characters at API boundaries.
- A name-bearing greeting fails readiness when no selected-language local voice
  is available; it never falls back to cloud TTS.
- Admin live data is generated from a dedicated privacy-safe projection.
- Mutating admin routes share the established token guard.
- Static cache rules exclude `/api/` and every non-static response.
- Help requests contain only request ID, kiosk, unit, timestamps, and state.

