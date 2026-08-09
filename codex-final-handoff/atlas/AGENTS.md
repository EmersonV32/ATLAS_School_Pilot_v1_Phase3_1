# ATLAS application instructions

These instructions apply to the maintained application in this directory.

## Architecture and compatibility

- Preserve FastAPI, Pydantic, server-rendered HTML, CSS, and vanilla
  JavaScript. Do not add a frontend framework, package manager, CDN, remote
  font, analytics tool, or production build step without approval.
- Preserve existing API routes and admin operations unless a documented
  migration is required.
- Keep visitor and admin assets separate. The visitor kiosk must not expose
  camera frames, YOLO/confidence, latency, provider names, transcripts, or
  admin navigation.
- Use mock/dev adapters for laptop tests. Hardware and cloud services must
  remain optional.

## Privacy

- Raw audio/images/video, face data, names, exact ages, keys, prompts, and
  private profile history must never enter logs.
- Exact age is browser-only and must be converted immediately into bounded,
  non-identifying guidance.
- An optional greeting name is ephemeral. It must never appear in monitoring,
  logs, prompts, retrieval, or cloud requests.
- Browser persistence is forbidden for visitor profiles. Do not use cookies,
  localStorage, sessionStorage, or IndexedDB for visitor state.
- Service workers may cache only versioned static shell assets and approved
  public images, never API responses.

## Quality gate

- Add focused tests for every dashboard/API/privacy behavior.
- Before delivery run focused tests, the full test suite, Ruff,
  `scripts/check_no_secrets.py`, and `git diff --check`.
- Validate the visitor flow at 1024x768 landscape, with reduced motion and
  keyboard navigation.
- Clearly label mock behavior and physical Jetson/iPad validation still due.

