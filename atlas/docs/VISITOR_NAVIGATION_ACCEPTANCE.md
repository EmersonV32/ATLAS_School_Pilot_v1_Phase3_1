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
- Focused dashboard/API tests: 149 passed. Full suite: **3,753 passed, 2 skipped**
  across all 54 test files in four disjoint isolated partitions. Ruff, secret
  scan, recovery verification and diff checks passed. These are not audible
  headset or on-device touchscreen acceptance.

## Applied Jetson release

Revision `38e2c69f6d7ed2e1d3bd7cbb9fa8a3c4e1b59523` was committed, pushed and
installed using the existing source-only transaction after explicit human
approval. Native staged validation passed before one controlled service
stop/start; no reboot or package installation was performed.

- Archive SHA-256:
  `0fc0edb0d25628e66c1c0cfddd5518111d5d3d3104be48d79e1502d1984ba5c5`.
- All 194 installed managed files match the manifest, with zero mismatches.
- ATLAS is active/running, health `ok`, `NRestarts=0`, `ExecMainStatus=0`.
  Visitor/admin/static routes return 200; actual protected audio/pan routes
  return 401 without authentication. Visitor HTML references shell version 30.
- Lightweight bootstrap took 3 ms locally on the Jetson in the acceptance check.
- Settings, overrides, model checkpoint, TensorRT engine and service-unit hashes
  are unchanged. Credential-file stat metadata is unchanged; its contents were
  not opened. Pan flags remain false and no PWM outputs are exported.
- Live readiness: unit, headset, connection, content, safety and profile ready;
  camera degraded/nonblocking; language pending the visitor's selection.

Retained rollback backup:
`/home/super-alex/atlas/backups/navigation-20261025/atlas-source-20261025-204741-9c167e2e`.
Keep it until physical acceptance. Coordinate any later restart with filming
and the mechanical/pronunciation chat; this chat has released its device window.

On the physical kiosk, reload the visitor page after deployment and check one
tap per screen, language/profile choices, Back, and Start with the camera offline.
Confirm one spoken answer through the charged OpenComm before filming. This
change does not alter voice providers, network profiles, models or servo flags.
