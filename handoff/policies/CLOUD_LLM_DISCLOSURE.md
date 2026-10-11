# Cloud-service disclosure

Documentation reviewed against the maintained source: 2026-10-11. This is not
a new physical-device test or a statement of provider-side retention terms.

ATLAS is edge-oriented, not fully offline. Local YOLO, retrieval, session state,
Whisper, and Piper are available, but approved configurations can use cloud
speech, language, and explicit manual artwork identification. The actual flows
depend on run mode, selected providers, consent, credentials, and readiness.

## Data that can leave the Jetson

| Feature | Cloud data flow | Configuration boundary |
| --- | --- | --- |
| Deepgram STT | Visitor question audio for transcription | Device mode, `speech.stt_provider: deepgram`, cloud speech enabled |
| Cloud LLM | Question text, bounded conversation context, relevant museum excerpts, and response guidance | Demo/device mode, selected cloud LLM, `llm.cloud_llm_enabled: true` |
| Cartesia TTS | Answer text for spoken playback | Device mode, `speech.tts_provider: cartesia`, cloud speech enabled |
| Explicit Gemini artwork capture | In-memory center-cropped JPEG and artwork candidate list | Manual capture enabled, Gemini selected, cloud LLM enabled, demo/device mode |

Each real provider also needs its local credentials and optional dependencies.
The maintained prototype integrates Gemini, Deepgram, and Cartesia, with other
LLM adapters available behind configuration. A configured provider is not proof
that its account, network, or service is ready.

Normal YOLO recognition remains local. The explicit manual-capture fallback is
an important exception: it can send a cropped image to Gemini, even though the
application does not save that image to disk. Aim only at an approved artwork;
cropping does not guarantee that people or background details are absent.

## Independent cloud controls and local fallbacks

Disabling `llm.cloud_llm_enabled` alone does **not** disable Deepgram or Cartesia.
Review `speech.cloud_speech_enabled` separately. Local Whisper/Piper fallback
depends on the configured models and fallback policy; it does not guarantee
all languages or full functionality without a network.

Dev/local runtime adapters use mock speech and LLMs rather than production
provider requests. Preparing dependencies or model caches can still require
downloads. Do not interpret a passing mock test as physical/cloud acceptance.

## Visitor data and disclosure boundaries

- Raw audio/images/video are not retained as application session records by
  default. In-memory processing or remote processing is different from storage.
- The optional onboarding greeting name is local-only, bypasses cloud TTS, and
  is erased after the greeting. Exact age remains browser-only and is reduced
  to broad response guidance.
- A visitor's spoken question can itself contain identifying information;
  do not promise that raw cloud speech contains no personal information.
- Privacy-safe admin projections and telemetry do not justify publishing raw
  diagnostic logs, transcripts, private environment files, or recordings.
- Provider-side retention, account terms, school/museum approval, and visitor
  notices must be reviewed separately before a public pilot.

The prototype configuration enables some diagnostic text logging. Before a
public deployment, disable transcript, live-STT, and LLM-response logging and
complete the privacy gate. See
[`../visitor-dashboard/PRIVACY_MODEL.md`](../visitor-dashboard/PRIVACY_MODEL.md)
and [`../VALIDATION_CHECKLIST.md`](../VALIDATION_CHECKLIST.md).

## Answer reliability

ATLAS uses curated retrieval, grounding/safety checks, deterministic FAQ paths,
and bounded context. General cloud answers are not automatically
museum-verified facts, and those safeguards cannot eliminate hallucinations.
Do not claim that every provider answer is fully grounded or that every
failure automatically becomes a refusal. Preserve honest limitations and
the supervised fallback path in the visitor notice and operator procedure.

Source boundaries: `atlas/app/dependency_container.py`,
`atlas/audio/deepgram_stt.py`, `atlas/audio/cartesia_tts.py`,
`atlas/vision/manual_capture.py`, and the selected LLM adapter in the maintained
Python package under `atlas/src/`.
