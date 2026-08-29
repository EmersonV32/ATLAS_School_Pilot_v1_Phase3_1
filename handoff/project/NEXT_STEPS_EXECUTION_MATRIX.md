# ATLAS Next Steps Execution Matrix

Updated: 2026-08-29

Source reviewed: `ATLAS Next Steps (1).docx`. This page turns the planning
document into an execution view; it does not replace the original roadmap.

## Completed or stabilized in this reconciliation

| Workstream | Result | Evidence |
| --- | --- | --- |
| Synchronize recent features | Reconciled the current runtime, dashboards, providers, fallback paths, content, tests, firmware, and deployment tools on `codex/jetson-runtime-reconcile`. | Full Jetson deployment suite passed 276 tests. |
| Survive camera absence | Visitor and staff websites remain reachable while the camera is unplugged and report a clear disconnected state. | LAN checks returned HTTP 200; local regression suite passed 277 tests. |
| Safer Jetson recovery | Deployment preserves private device configuration, replaces runtime trees atomically, tests before startup, and rolls back failed deployments. | Checksummed pre-deployment snapshot and retained deployment backup. |
| Language access | Traditional Chinese is a public visitor language; Arabic is retained as preview. | Bootstrap response verified on the live Jetson. |
| Headset control | The multifunction button is configured for manual capture. | Runtime reports `/dev/input/event2`, key `164`; physical press remains a demo check. |
| Camera quality baseline | Added a balanced 800x600 JPEG, quality 10, 15 FPS firmware/runtime profile with stream pacing and idle Wi-Fi power saving. | Firmware compile passed; physical flash and thermal test are pending. |
| Camera absence and return | Verified that the websites remain available while unplugged and the camera becomes ready after hot-plug without a service restart. | Live Jetson bootstrap and runtime status; one induced read failure recovered automatically. |

## Ready next

| Priority | Workstream | Next checkable output |
| --- | --- | --- |
| 1 | Camera reliability | Flash the compiled profile, then record 20 minutes of FPS, temperature, disconnect/reconnect behavior, and artwork-detection results. |
| 2 | Voice reliability | Resolve Cartesia HTTP 402, verify one stable voice across a complete response, then test Piper fallback and headset reconnect. |
| 3 | Real-world visitor test | Run a scripted visit with at least one person who did not build ATLAS and log failures, confusion points, latency, and recovery actions. |
| 4 | Artwork expansion | Finalize the next artwork list, source licensed/reference material, add content manifests, ingest it, and run retrieval tests before model training. |
| 5 | Presentation readiness | Freeze a reliable demo path, operator checklist, fallback video, booth layout, poster copy, judging script, and recovery drill. |

## Blocked by hardware, access, or a decision

| Workstream | Blocker | Unblock condition |
| --- | --- | --- |
| Roboflow annotation and YOLO26 training | Dataset/account work and final images are not available in this checkout. | Confirm the four artworks, upload/annotate images, obtain credits if needed, then version the dataset and training output. |
| Cartesia production speech | Live provider returns HTTP 402. | Fix account/billing, then rerun provider and end-to-end speech tests. |
| Camera/headset mechanical assembly | Requires the physical headset, camera, printed prototypes, cooling measurements, and fit tests. | Complete CAD prototype, print, verify forward alignment/retention, then thermal-test before enclosure closure. |
| Additional speaker, Jetson case, cables, and Arducam integration | Requires component choices and physical integration. | Produce a bill of materials and interface plan before purchasing or modifying hardware. |
| Public website | Vercel can host a public informational/demo frontend, but it cannot directly replace the private Jetson LAN runtime URL. | Decide whether the site is informational, simulated, or connected through an authenticated relay; define privacy and offline behavior before implementation. |

## Major project work, not a quick patch

- Improve multilingual voice, intonation, prompting, and language-by-language
  live validation.
- Expand and version the museum artwork/content catalogue.
- Build public-facing web content and any secure remote Jetson relay.
- Add richer monitoring for the Jetson, ATLAS runtime, visitor flow, and camera.
- Complete the physical wearable, cooling, cable management, Jetson enclosure,
  and assembly documentation.
- Produce booth materials, posters, monitor presentation, script, video, and
  final report.
- Continue the August-to-December calendar as the scheduling authority, with an
  owner and acceptance test attached to every milestone.

## Definition of project-safe completion

A roadmap item is complete only when its source is in Git, private state is in
the recovery inventory, automated tests pass, the physical behavior is checked
where applicable, and the handoff documents name the rollback path. A rendered
screen or successful compile alone is not enough for hardware-dependent work.
