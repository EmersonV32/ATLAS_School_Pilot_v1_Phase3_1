# Persistent STT connection and listening-ready sound

The owner requested keeping STT ready between turns and a short buzz-like
readiness sound, with a beep alternative and removal for the presentation.
They explicitly selected restoring introductions only after **Hey Atlas** or
**Bonjour Atlas** instead of preserving the five divergent greeting/identity
files found on the Jetson. This branch continues from `be33d66` and retains its
one/two-second pauses and 600 ms eligible prepared-question shortcut.

## Behavior

- Reuse a healthy, visit-scoped Deepgram socket between questions. A background
  keepalive continues during replies without opening microphone capture or
  sending visitor audio. A fresh socket sends only ten milliseconds of generated
  silence to initialize the audio protocol; its duration is included in offsets.
- Convert cumulative provider timestamps into current-turn offsets. Late old
  results are excluded; boundary-spanning segments retain only timed current
  words. Unknown/invalid timing cannot establish a current-turn boundary.
- Preserve the existing finalization wait when a question still has an interim
  tail. A final already covering the latest voiced frame needs no second
  `Finalize`; Deepgram does not guarantee an acknowledgement for an empty flush.
  An unconfirmed flush, disconnect, queue overflow, cancellation or language
  change retires the stream instead of reusing ambiguous state.
- Close sockets and discard queued data when the visit stops. Keepalive does
  not capture speech while ATLAS answers; this is not interruption support.
- A capture-ready callback runs after Deepgram input opens or Whisper recording
  starts. The local 80 ms buzz-like sound uses the selected output and volume;
  `beep` is an alternative. Cue failure cannot suppress an otherwise valid
  question. No new microphone buffer is flushed after the cue, preserving a
  visitor's immediate first words. Idle timeout windows do not repeatedly buzz.
- Continuous-listener startup defers its old early cue until input is ready.
  The cue is rearmed after a received question and at a new visit. Cancelled
  visits cannot announce readiness for an old capture generation.

## Settings

```yaml
speech:
  deepgram_keep_connection: true
  listening_ready_cue: buzz  # buzz | beep | off
```

These fields are available through the protected admin configuration API.
Set `listening_ready_cue: off` and apply the normal configuration restart before
filming; it does not disable connection reuse. Schema validation rejects
unrecognized modes. Existing installations without these fields receive the
new defaults from the settings model; source-only deployment preserves explicit
site overrides, the existing pauses, credentials and hardware configuration.

The buzz is an audio waveform through the headset/output, not a mechanical
vibration of the microphone. It uses local PCM playback, without cloud TTS or
text containing visitor information.

## Protocol sources

The implementation follows Deepgram's [KeepAlive](https://developers.deepgram.com/docs/audio-keep-alive),
[Finalize](https://developers.deepgram.com/docs/finalize) and
[streaming response schema](https://developers.deepgram.com/reference/speech-to-text/listen-streaming).
Audio timestamps advance with sent audio rather than keepalive wall time.

## Validation and release status

The final guarded full suite passed: **4,618 passed, three skipped**, with
**4,621 independently collected**. The skips concern an unavailable C++ compiler,
Windows symbolic-link permissions and opt-in real inference. The final new
socket/cue modules independently
passed all 66 cases. They cover multiple turns, idle keepalive, stale data,
teardown/recovery, actual input-open ordering, cue modes, immediate questions,
PCM frame alignment and factory wiring. The source-release required and smoke
lists include both new regression modules. Its disposable validation stage
creates a public defaults-only configuration; live configuration is excluded
from the archive and replacement.

Ruff, compilation, offline dependency consistency, synthetic dashboard logic
(106 checks), secret/recovery/layout and whitespace checks pass. No packages
were installed. Review found no remaining source or release-tool blocker.

No new packages, firmware, models, visitor UI or motor changes are required.
No fresh visitor/admin layout is claimed because no rendered UI was changed.
No raw speech, names, keys or provider payloads are added to monitoring.

The Jetson did not respond at its last recorded address during the read-only
check. The owner then explicitly requested leaving the update ready on the
test branch. No deployment or restart for this change has occurred. A future
deployment needs a fresh baseline and renewed online handoff; do not retry SSH
or replace the live source while this request remains in effect. Main remains
excluded.

## Physical acceptance still required

Confirm the buzz is audible at a comfortable level, is not interpreted as a
visitor question, and preserves a question spoken immediately after it. Check
French and English, repeated turns, stop/restart, a network reconnect, and both
explicit wake phrases before the full optional-name introduction. Software
readiness is not a measurement of the first/last audible sample at the headset.
Do not claim a quantified reduction in the inter-turn gap without that test.
