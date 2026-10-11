# ATLAS privacy summary

Documentation reviewed against the maintained source: 2026-10-11. This describes
application boundaries, not a new physical pilot validation or a guarantee
about cloud-provider retention. Read it together with the
[visitor privacy model](../visitor-dashboard/PRIVACY_MODEL.md) and
[cloud-service disclosure](CLOUD_LLM_DISCLOSURE.md).

## Visitor setup and temporary state

A name is optional, not required. ATLAS does collect a short greeting name when
the visitor chooses to provide one; it is incorrect to claim there is no name
field or that names are never collected.

| Input | Application handling |
| --- | --- |
| Optional greeting name | Browser memory; sent only in the local start request, not onboarding progress or admin status. |
| Exact age | Reduced in the browser to broad age guidance; the numeric input is cleared and not sent to the server. |
| Age guidance, language, expertise, interests, accessibility | Temporary session preferences; privacy-bounded summaries can appear in operator status and shape responses. |
| Conversation context | Bounded in-memory recent turns; reset when the runtime session ends. Diagnostic text logs are a separate concern. |

The browser clears its name/age fields after successful start, reset, or a new
page load; it does not use browser persistence for visitor profiles. Reloading
a browser is not proof that an already running Jetson session has stopped.

The runtime holds the greeting name while waiting for the first wake phrase.
The name-bearing greeting uses the selected-language local Piper path, never
cloud TTS. Its name is not passed into dialogue prompts, retrieval, monitoring,
or structured session events. After a successful greeting, the pending runtime
name is cleared; session stop/reset also clears it. If local playback fails,
the wake gate remains pending and the name can remain locally for retry until
success or session stop. Missing local voice support blocks a named start.

Piper creates temporary local synthesized WAV files for playback and deletes
them in its normal cleanup path. This is not a retained microphone recording,
but it means that local speech is not exclusively RAM-only processing.
Normal cleanup is not a guarantee of secure erasure after a crash.

## Raw media, recognition, and cloud processing

The maintained configuration disables raw microphone-recording, camera-frame,
video, and face-data retention as session records. Camera/audio processing and
the authenticated operator preview do not establish permission to save or
publish recordings. ATLAS does not implement facial recognition or gender
inference as visitor features.

Local processing is not the same as keeping all data off the network:

- Enabled Deepgram STT can receive question audio.
- An enabled cloud LLM can receive question text, bounded dialogue context,
  relevant museum excerpts, and response guidance.
- Enabled Cartesia TTS can receive answer text.
- Explicit enabled Gemini artwork capture can receive an in-memory cropped
  image, although normal YOLO recognition remains local.

Cloud speech and cloud LLM controls are independent. Disabling
`llm.cloud_llm_enabled` does not disable `speech.cloud_speech_enabled`.
Manual image cropping does not guarantee that people or background details are
absent. A visitor's own spoken question may contain personal information even
though the optional onboarding name is excluded from cloud dialogue/greetings.

See the [cloud-service disclosure](CLOUD_LLM_DISCLOSURE.md) for exact feature
gates. Schools/museums must review provider terms, retention, consent, and
visitor notices before approving a public pilot.

## Logging and operator access

The Python settings model defaults transcript, live-STT, and LLM-response
logging to off. However, the tracked prototype YAML enables those diagnostic
text options. It must not be described as a public privacy-safe configuration
without reviewing the actual deployed settings.

Before public operation, disable all three:

```yaml
logging:
  log_transcripts: false
  log_live_stt: false
  log_llm_responses: false
```

Structured events support operational metadata such as session IDs, states,
artwork IDs, language, latency, and failure indicators. The event logger drops
known sensitive field names and omits transcripts when configured off; it is
not a universal redaction system for arbitrary free text or exception output.
Random session IDs are non-identifying application identifiers, not a guarantee
against correlation with outside information.

Admin routes require the configured authentication guard. Network exposure
depends on bind settings and the deployment; do not assume every installation
is localhost-only or safe on an untrusted LAN. Keep operator data, tokens,
camera previews, and private diagnostics separate from the visitor kiosk.

## Retention and protected recovery

`logging.retention_days` has a default target of 30 days; this summary does not
claim a verified automatic purge. The operator must establish and verify a
retention/deletion procedure for logs, backups, and diagnostics. Ending a
session or erasing its in-memory profile does not erase previously written
diagnostic logs or provider-side records.

Credentials, private environment files, Wi-Fi headers/profiles, visitor logs,
recordings, and generated databases belong outside Git. Ignore rules are not
encryption and do not prevent an independent backup/sync service from copying
machine-local files. Never publish secret values or private visitor output in
documentation, chat, screenshots, or tickets.

The [validation checklist](../VALIDATION_CHECKLIST.md) and current
[visitor privacy model](../visitor-dashboard/PRIVACY_MODEL.md) are required
release references. Automated tests cover application contracts; physical
device behavior, actual deployment configuration, and provider-side policy
still require separate review.
