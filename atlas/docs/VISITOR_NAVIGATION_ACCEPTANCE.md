# Visitor navigation responsiveness — October 25

The visitor journey previously bound buttons only after startup requests and
waited for a progress response before changing every screen. Background state
polling also performed full hardware readiness checks under the onboarding
lock. Slow requests therefore made buttons appear unresponsive.

Navigation now binds immediately and renders locally. Coarse profile updates
are serialized and coalesced to the latest choices; they never contain the
optional name or exact age. Actual demo Start still waits for the final profile
save and real readiness checks. Reset waits for older saves before clearing
server state. Background polling is single-flight and skips hardware probes;
the default bootstrap contract and explicit readiness endpoint remain intact.
Requests have bounded timeouts. Static shell version 30 replaces version 29.

## Verification

- Real Chromium, mocked APIs, 1024×768, reduced motion and keyboard only.
- Initial bootstrap/interests deliberately held while the first button is used.
- Every progress response delayed 500 ms; screens changed in 14–152 ms.
- 42 keyboard transitions, one progress request at a time, zero browser errors,
  no horizontal overflow, no persisted visitor state.
- Camera degraded/offline remains nonblocking; the final Start waits for the
  saved privacy step before entering the running-demo screen.
- Focused dashboard/API tests: 149 passed. Full-suite and deployment results
  are recorded after the final gate, without treating mocked checks as audible
  headset or on-device touchscreen acceptance.

On the physical kiosk, reload the visitor page after deployment and check one
tap per screen, language/profile choices, Back, and Start with the camera offline.
Confirm one spoken answer through the charged OpenComm before filming. This
change does not alter voice providers, network profiles, models or servo flags.
