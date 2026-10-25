# Conversation timing and plain-language acceptance — 2026-10-25

## Intended behaviour

- Starting a visitor or admin session still queues one ATLAS introduction on
  the speech-owning thread, before the microphone opens.
- A standalone “Bonjour Atlas”, “Hey Atlas” or supported local wake address
  then stays silent while waiting for the actual request. Hesitation-only
  transcripts also keep listening. Repeated addresses do not repeat the intro.
- If the address and question arrive together, preserve the question and its
  language/confidence metadata. Legacy wake-gated sessions defer their intro
  until a real request arrives, then answer it; they do not discard that request.
- Suppress proactive artwork invitations during that waiting pause, while
  still allowing camera/manual selection to update the artwork context.
- Child, early-child and simple-language answers use everyday descriptions,
  not shortened adult jargon. The local five-language catalogue has matching
  plain versions for all seven artworks. Expert interests do not override a
  simple-language accessibility choice.
- Word questions go to the contextual dialogue path rather than a canned
  whole-artwork interpretation. Explain the word simply first, then how it
  applies to the discussed artwork. The earlier answer remains in session
  memory even after the camera switches artworks. Ask which word if unclear.

## Local verification

Tests use synthetic speech, mocked providers and camera outages. Run the
existing `scripts/run_deployment_pytest.py` guard before collection so the live
installation's `.env` is never loaded. On Windows use fresh process-local
TEMP/TMP and a fresh pytest basetemp. The test suite covers:

- French and multilingual wake matching, same-breath questions and pauses;
- one introduction, muted microphone during speech, private-name local-only
  routing, cancellation and no duplicate private greeting after a failure;
- all public artwork/language/profile/FAQ combinations and plain vocabulary;
- all admin languages retaining child-level prompt guidance;
- vocabulary follow-ups retaining the previous answer and artwork labels,
  without starting a preference interview or learning a technical preference;
- existing context, voice, camera-free, privacy and dashboard regressions.

Visitor browser QA uses real static assets and mocked APIs at 1024×768,
reduced motion, keyboard navigation and empty browser storage. No live visitor
audio, names, transcripts or images are used for these checks.

Final local gate: **3,751 passed, 2 skipped** across all 54 test files, run in
four disjoint isolated partitions against the final source. The updated
early-child audio-description wording assertion passes. Ruff, secret scan,
recovery-bundle verification and `git diff --check` pass. Browser QA completes
38 keyboard transitions with zero errors and no persisted visitor state.

## Still required on the physical installation

These changes are local until a separately coordinated deployment. Do not
restart or deploy while the mechanical chat holds the Jetson test window.

1. With a charged OpenComm, start from both admin and visitor dashboards.
   Hear one complete introduction; ensure ATLAS does not transcribe itself.
2. In French say “Bonjour Atlas”, pause several seconds, say “euh”, then ask
   a question. ATLAS must stay silent through the pause and answer the question.
   Repeat with “Hey Atlas” and with the address plus question in one breath.
3. Use the child profile. Ask how Sunflowers was painted: expect “peinture
   épaisse qui dépasse”, not unexplained “relief” or “empâtement”. Repeat with
   Mona Lisa and The Starry Night in each language used for the demonstration.
4. Ask what a word in the last answer means, including “relief”. Expect an
   easier definition and an example linked to that answer's artwork, not a
   generic interpretation of the painting. Repeat after the camera switches
   artworks and with adult/expert profiles. Ambiguous “that word” should prompt
   a short clarification rather than a guess.
5. Confirm a simple-language accessibility choice still applies with expert
   interests, and audio-description answers use the same easy words.
6. Stop/restart a session during speech. No old greeting/question may continue
   into the new visit. Repeat with the camera offline.
7. Check real hesitation/accent handling and complete, stable voice playback.
   No TTS provider, voice ID, fallback policy, audio route or Deepgram timing
   setting was changed here. Cloud answer quality and physical audio timing
   cannot be proven by mocked tests.
