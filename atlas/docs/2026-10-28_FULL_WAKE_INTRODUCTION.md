# Complete wake introduction before suggestions

The owner requested the complete self-introduction after Hey Atlas / Bonjour
Atlas, with the optional dashboard name, before an interest invitation, and
explicitly authorized another Jetson test deployment. Main remains excluded.
Branch: `codex/full-wake-introduction`, based on the installed interactive FAQ
continuation rather than main.

## Confirmed cause and correction

The named route selected a short greeting plus artwork invitation instead of
the full public introduction. It now inserts the name into the same complete
introduction. English and French explain ATLAS's role and help before one
optional interest question; an empty name uses the complete anonymous copy.
The entire name-bearing introduction remains one private-local synthesis.
Names never enter the public response, model, retrieval or logs, and are erased
after successful greeting or visit stop.

The visitor dashboard starts an ungated voice session. Both stable-camera and
manual-capture demo paths previously allowed proactive invitations before any
explicit greeting. They now require the current visit's successful spoken
introduction. Queued callbacks also recheck the visit before speaking. Failed,
cancelled, stopped or superseded introductions do not unlock those suggestions.
Ordinary visitor questions remain usable before a wake greeting; they never
introduce ATLAS or use the optional name. The introduction remains once per
visit, after an exact standalone allowed wake phrase.

## Validation and deployment

Final guarded local suite: **4,537 passed, three skipped**; independent
collection confirms 4,540 tests. Root greeting/API/privacy/pronunciation tests
passed; the device loop/camera/wake regression gate passed. Ruff, compilation,
offline dependency compatibility, secret scan, recovery, repository layout and
whitespace checks pass. Synthetic admin logic and visitor 1024x768 reduced-
motion keyboard flow pass. The unchanged optional admin-browser harness
limitation remains recorded in earlier release notes; no new pass is claimed.

Before deployment, every previous managed file and public fixture matches the
interactive FAQ archive. Service is active/running with NRestarts 0 and
ExecMainStatus 0; public pages/health return HTTP 200, protected routes HTTP 401.
Source-only deployment is pending. Local settings, packages, models, secrets,
service units, firmware, networking and motor state are outside this release.

## Owner retest

Start a fresh experience with a name and say Hey Atlas or Bonjour Atlas alone.
Hear the name, the complete role/help explanation, then the interest question.
Start another fresh experience without a name; hear the same full explanation
with no name or placeholder. Confirm a camera artwork suggestion cannot speak
first. A second wake in the same visit must not repeat the introduction.
Audible completeness, name pronunciation and actual headset routing remain
physical acceptance checks; mocked tests prove the submitted sequence only.
