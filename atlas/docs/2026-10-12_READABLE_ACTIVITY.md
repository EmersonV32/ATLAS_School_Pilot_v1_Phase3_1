# Readable live activity — October 12

Local feature branch: `codex/readable-live-activity`, based on
`codex/dashboard-redesign`. Not pushed, promoted to `main`, or deployed.
The Jetson, camera and headset are offline; examples and screenshots use
synthetic fixtures, not visitor logs or live conversations.

## Operator experience

Open **Activity & logs** in the private staff dashboard. The new timeline
explains listening, final and interim visitor questions, ATLAS responses,
camera detections and artwork changes, headset multifunction-button presses,
museum knowledge searches, sessions and voice failures in plain English.
Speaker/category labels and explicit Warning/Error text accompany colours.

Technical logs remain available in a collapsible section, and each readable
update has its own **Matching technical entry** disclosure. An unknown log
message receives a neutral explanation and retains its original technical
entry; ATLAS does not ask another AI to interpret it or invent a success.

Search and severity filtering apply to both views. Pause freezes both views;
explicit Refresh can replace the paused snapshot once. Raw/Guided switches
reformat the current snapshot locally, even while paused. Export contains
readable activity and both original sources with the same snapshot ID and
capture time. Download links remain valid briefly until the browser reads
them, then their object URLs are released.

Follow newest can be disabled to inspect older entries. Unchanged snapshots
do not rebuild the timeline; updated snapshots preserve open disclosures,
keyboard focus on retained entries and scroll position when following is off.

## Synchronisation and cost

The authenticated, `Cache-Control: no-store` `/logs/snapshot` endpoint reads
each source once and returns paired raw/readable entries. Every entry has a
content-and-occurrence ID; the entire snapshot has a content hash and capture
time. This is a consistent pair of representations, not a transaction across
independently written process and structured logs. Each source preserves its
recorded order. Untimestamped stdout is labelled **No recorded time** and is
not interleaved as if its exact time were known.

The browser uses one request every two seconds while this view is visible,
with overlapping requests prevented and hidden-tab polling skipped. Late
responses after a pause, token change or lock cannot replace the displayed
snapshot. Connection failures retain both last-known views and label them
offline/stale; recovery replaces them together. Locking clears the retained
activity from the DOM and browser memory.

Default tail: 250 process lines and 100 structured events. API caps are 1,000
and 200 respectively. File reads are byte-bounded; structured polling no
longer scans an entire day's file. Malformed/incomplete/non-object JSON rows
are skipped. History is bounded, not a complete visit archive. No new cloud
call, framework, production dependency, background capture, or browser
conversation storage was introduced.

## Privacy and honest status

No privacy configuration is changed automatically. User-final, user-interim
and ATLAS-response text respect the active `log_transcripts`, `log_live_stt`
and `log_llm_responses` flags respectively. The new endpoint hides historical
tagged text too when its active flag is off, in both paired representations.
If speech text was not recorded, the view shows a status instead of inventing
a quotation. Existing legacy log endpoints remain available for compatibility.

Verified local FAQ answers now emit an opt-in `[ATLAS final]` observation,
so they can be displayed alongside Gemini responses. The typed FAQ path also
records a privacy-safe question-received event, without newly copying the
question text into logs. These observations do not change voice selection,
playback, retrieval, conversation memory or artwork selection. Greeting names,
visitor profiles, raw media, prompts and secrets are not added to monitoring.
Existing transcript logging still requires appropriate staff privacy approval;
this view is not an anonymisation service.

Interim speech is explicitly **not yet final**. A prepared response is not
proof that it was audible. Audio-generation completion, first audio arrival,
playback confirmation and voice fallback/failure have distinct wording. User
speech containing “error” is not classified as a system error, and metadata
such as `error=none` / `fallback=False` does not create false alarms.

The visitor kiosk remains separate: no activity feed, technical log, provider
name, transcript or camera preview is added there.

## Validation and acceptance

- Focused final unit/pipeline checks: 116 passed before the final full run.
- Final committed full suite: 3,246 passed, one expected skip and the existing
  non-failing Starlette/httpx deprecation warning (399.51 seconds). The isolated
  deployment test wrapper blocked installation secrets; no devices/cloud were
  used. Earlier full runs also passed before the last added regression cases.
- Dependency-free dashboard logic: 62 checks, including refresh overlap,
  pause/late-result races, lock clearing and shared offline snapshots.
- Browser: 35 layouts (all seven views at five sizes), 18 control actions,
  nine failure/recovery scenarios, 2,650 text-contrast checks, no unexpected
  browser errors. Verified actual exported file contents with normal Windows
  permissions; sandbox-only attempts cancelled the browser download.
- Browser scenarios include safe literal rendering of HTML-like log text,
  matching raw entries, format changes without fetching, retained focus/open
  disclosures, paused snapshot consistency, offline retention and recovery.
- Lint, secret scan, dependency check, whitespace and recovery checks pass.
- Visitor regression: 33 keyboard transitions at 1024x768 with reduced motion,
  six language paths, no browser errors and no cookie/local/session storage.

When devices are available: start a session, ask a question with a hesitation,
check the final User entry and the matching ATLAS answer, press the headset
button, move between two artworks, and verify selection/listening/voice
outcomes against actual camera and headset behaviour. Test pause, reconnect
and export on the real staff device. Physical acceptance remains outstanding;
this work does not repair the separate camera-stream watchdog or confirm
school Wi-Fi connectivity, and does not integrate the deferred SG90 branch.
