# Conversation and listening stability — October 11, 2026

Source branch: `codex/conversation-listening-stability`, based on `main`
at `9dfe260`. This is laptop-tested source, not a Jetson deployment or a
fresh physical health check. Jetson, cameras and headset were offline.
Implementation commit: `e6b3f2a` (local; not pushed or deployed).

## Problems reproduced

Before the fix, nine synthetic regressions reproduced these failures:

- Discussion disappeared after the third exchange.
- A named question about another artwork still retrieved the camera artwork.
- An explicitly discussed work was forgotten when there was no camera frame.
- A new artwork was not labelled as a subject change in Gemini's prompt.
- A two-artwork question received a canned answer for only one work.
- A hesitation ended capture before resumed speech.
- The eight-second listening deadline cut off speech already in progress.
- A finalized transcript prefix suppressed the unfinished final words.
- Repeated words in distinct final segments were wrongly deduplicated.

## Shared conversation subject

The dialogue engine now resolves one visit-only artwork focus before local
FAQ answers, retrieval and Gemini prompting. Typed and spoken questions use
the same memory. The prompt separates **current camera artwork** from
**discussion artwork**, and labels historical exchanges with their subject.

- A fresh, stable, centered new detection takes priority over the old device
  conversation latch. Manual overrides retain their existing priority.
- An explicit capture/staff selection reselects that work even if the camera
  ID has not changed since an intervening named discussion. A delayed manual
  cloud capture cannot restore an artwork after its visit was reset.
- A clearly named artwork becomes the discussion subject without claiming
  that the camera sees it. An unchanged camera does not undo that choice.
- A question asking what the visitor is currently looking at uses the actual
  camera identification, not a remembered or merely named work.
- Descriptive questions such as "What can we see in Mona Lisa?" or questions
  about an artist's past viewpoint retain the named artwork. Direct current-view
  wording is normalized for accent marks and punctuation; it is not a generic
  match on the words "see" or "looking at".
- A missing frame does not erase the discussion. It also does not become a
  false camera identification. New visits clear memory and invalidate old
  in-flight answers/captures.
- Comparisons retrieve each named artwork and interleave evidence. Compound
  questions bypass single-intent canned answers so Gemini sees the whole request.
- Gemini receives guidance to tolerate fillers, repetitions, imperfect grammar
  and clear phonetic mistakes. Material ambiguity calls for clarification,
  not an invented meaning or a silently substituted artwork.

Memory is bounded, not an unlimited transcript: 12 recent exchanges, up to
96 older exchanges, and up to 16 early subject anchors. Earlier prompt excerpts
are capped at 8,000 characters and prioritize the current/named works. Questions
and answers retain the existing 500/1,000-character per-turn limits. Extremely
long visits can therefore omit details. No new database, browser storage,
background summarization or extra cloud model call was added. Historical
conversation is labelled as untrusted context, not verified museum evidence.

## Deepgram turn capture

Default source settings:

| Setting | Meaning | Default |
| --- | --- | --- |
| `speech.listen_duration_s` | Wait for speech to begin | 8 s |
| `speech.max_utterance_s` | Maximum capture after speech begins | 45 s |
| `speech.silero_min_silence_ms` | Normal end-of-question pause | 2,000 ms |
| `speech.silero_hesitation_silence_ms` | Grace for empty/clearly unfinished phrases | 4,000 ms |

Deepgram results are processed during capture. Its `speech_final` marks a
provider segment, not the end of the application's question. Final segments
are concatenated; an interim tail is retained if the flush does not replace it.
Only repeat deliveries of the same timed final segment are deduplicated.
Quiet waiting sends a socket keepalive without streaming idle microphone audio.
Captured audio stays in memory for the existing local recovery path, including
when sending audio fails. Cancelled captures discard that audio.

Visit stop/runtime shutdown interrupts supported Deepgram capture. A cancellation
during socket preparation or the cue cannot start an old recording afterward.
The listener still pauses while ATLAS speaks, preventing its own voice from
becoming a visitor question; this is not full-duplex listening/barge-in support.
The existing complete-answer, single-provider TTS safeguards were preserved.
Whisper's offline fallback remains a bounded fixed-window recorder; the new
adaptive pause behavior applies to Deepgram, not that fallback recorder.

The implementation follows Deepgram's [segment/endpoint documentation](https://developers.deepgram.com/docs/understand-endpointing-interim-results),
[Finalize behavior](https://developers.deepgram.com/docs/finalize), and
[keepalive guidance](https://developers.deepgram.com/docs/audio-keep-alive).

## Verification

- 65 new deterministic/synthetic regressions pass, covering subjects, return
  visits to a work, bounded long-visit memory, aliases, typed/spoken sharing,
  comparisons, session cancellation, pauses, transcript assembly, socket
  keepalive, audio recovery, manual reselection/cancellation and default
  transcript-log privacy. Three additional regressions reproduced the manual
  capture/selection edge cases before their fixes.
  Four further failing cases exposed overbroad view-question matching and
  accent/punctuation handling; all five view-classification regressions now pass.
- Visitor browser QA passes 33 keyboard transitions at 1024×768 with reduced
  motion, six interface languages, no page errors/failed responses, and empty
  local/session storage and cookies. This is mock laptop behavior.
- Final full isolated suite: **3,146 passed, one expected skip** in 337.01 seconds.
  The existing Starlette/httpx deprecation warning is non-failing. The full
  gate caught a session-start argument-placement mistake during implementation;
  it was corrected before this final successful run.
- Ruff, source/test compilation, dependency consistency, secret scan,
  whitespace checks, recovery-bundle verification and repository-navigation
  verification pass. The gates preserve private/generated exclusions.
- Tests use synthetic data and block loading the installation's live `.env`.
  Windows sandbox restrictions blocked temporary paths/loopback test sockets
  initially; isolated tests were rerun with approved local process access.
  Mock UI/server and stalled/superseded test processes were stopped afterward.

## Before physical acceptance

Deploy only with the owner's explicit approval; preserve private configuration,
firmware, JetPack/L4T, model files and service settings. Review non-secret speech
overrides so old pause values do not mask the new source defaults. Do not change
voice or language selections merely to apply this patch.

At the Jetson, test actual headset input/output and both camera paths, then:

1. Identify artwork A, discuss its artist/technique through several follow-ups.
2. Pause 1.5 seconds mid-question; pause about 3 seconds after an unfinished
   phrase; resume and confirm the final words are answered.
3. Begin near the eight-second waiting limit and continue speaking beyond it.
4. View confirmed artwork B and ask "Who painted this?"; ensure the answer is B.
5. Explicitly name A while looking at B, follow up with "it", compare both,
   then ask what the camera currently sees. Check subject and evidence each time.
6. Return to A; briefly interrupt camera connectivity; verify discussion stays
   coherent but no stale view is claimed. End/reset the visit and verify a new
   visitor cannot recover the old discussion.
7. Verify repeat listening, headset buttons, cloud/local recovery and one voice
   throughout each complete answer under real network conditions.

No software test guarantees every accent, arbitrary hesitation duration,
provider availability or hardware connection. The live camera-stream watchdog
and school-network acceptance items in current state remain separate open risks.
