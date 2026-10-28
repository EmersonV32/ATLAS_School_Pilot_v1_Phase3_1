# ATLAS prepared answers, introductions, and French dates

Prepared Tuesday, 2026-10-27. Implemented locally; device acceptance pending.

## Result and authority

Branch: `codex/faq-wake-french-dates-runtime`.
Base: `9996dd7`, fetched `origin/codex/camera-offline-demo-2026-10-25`.
Commit for this task: none. Push/main merge/deployment performed: **No**.

Confirmed source authority: `handoff/START_HERE.md`,
`handoff/2026-10-26_TEAMMATE_HANDOFF.md`, and `handoff/CURRENT_STATE.md` name
this continuation branch. Main lacks later operating fixes. The recorded last
installed revision is dated evidence, not a fresh observation of the Jetson.
The early main-based scratch work/package is superseded and must not deploy.

## Implemented behavior

- Prepared catalog: seven artworks match the demo manifest; ten question
  families, five public spoken languages, seven profiles, all 213 original
  phrasings, and 178 complete forms are tested. Exact `Who is the Mona Lisa?`
  resolves locally to the existing Lisa Gherardini subject answer. No retrieval,
  model, or network call is needed for a hit. Unknown/deep/multipart questions
  intentionally retain the ordinary deeper route.
- All spoken routes: both `run_once` and `respond_to_transcript` check the same
  helper before retrieval/model calls; typed questions retain their fast path.
  Conversation focus, simple-language facts, vocabulary, safety/injection
  guards, memory, live-camera questions, and named-artwork transitions remain.
  A fast but wrong generic answer is prevented by event/correction negatives.
- Introductions: neither admin start nor visitor onboarding queues an automatic
  introduction. Ordinary questions still work before any greeting. Say
  `Hey Atlas` or `Bonjour Atlas` **by itself**, with case/punctuation ignored,
  to authorize the one-time introduction in the selected language. Other
  familiar addresses may still prefix questions without authorizing an intro.
  Repeated accepted greetings are handled locally without another model turn
  or introduction. A pause after waking remains quiet.
- Name: a supplied dashboard name appears in the wake-triggered introduction,
  e.g. `Hey Emerson, I'm ATLAS` or `Bonjour Emerson, je suis ATLAS` plus the
  existing art-guide invitation. Name-bearing speech remains private/local;
  the name never enters model/cloud/retrieval/API response text. Success erases
  it; failure retains it until another explicit wake attempt or visit stop.
- Model defense: all generated answers receive the no-introduction instruction;
  explicit common English/French self-introduction sentences are removed before
  speech, display, and conversation memory. Useful remaining text still enters
  the existing topic memory. An intro-only model answer becomes a brief artwork
  question. The authorized local greeting bypasses this output guard.
- French speech: `1896` becomes `mille huit cent quatre-vingt-seize` before
  synthesis. Standalone/streamed Cartesia and Piper/private/fallback share
  deterministic number/date expansion. Year ranges, valid numeric calendar
  dates, `premier`, grouped/spaced year forms and locale variants are covered.
  Other languages, display text, URL/ID/decimal/large-number tokens are preserved.
  The newer Cartesia `ATLAS` -> `Atlas` pronunciation and provider locks remain.
- Visitor instructions: all locales show both wake phrases; static shell v31
  preserves the newer navigation fix and prevents stale cached instructions.

## Verification evidence

Final guarded full suite: **4,336 passed, three skipped**, with two existing
TestClient deprecation warnings and the intentional duplicate-ZIP fixture
warning. Independent guarded collection reports 4,339 tests, matching passes
plus skips. Command: `python scripts/run_deployment_pytest.py`, using the
checklist's wrapper argument extension for a new ASCII Windows `--basetemp`,
`PYTHONUTF8=1`, and this worktree's `src` on PYTHONPATH. No live dotenv loaded.
The complete output is saved outside Git in
`deliverables/faq-runtime-review/pytest-final.txt`.

Focused testing includes the complete FAQ coverage matrix, forbidden retrieval
and model doubles, failed/private greeting recovery, actual device-loop test
ordering, camera-free questions, conversation subjects, vocabulary, output guard
callbacks/memory, provider payloads, cancellation, and one-provider-per-answer.

Ruff over `src tests scripts`, Python compilation, dependency compatibility
(`uv pip check --offline`, since this existing venv has no pip module), obvious
secret scan, recovery bundle, repository layout, and `git diff --check` pass.
Modified JavaScript parses; 106 synthetic admin JavaScript checks pass.

Two independent warm laptop measurements for the exact Mona Lisa lookup:
`timeit.repeat` median 1.4733 ms per lookup and `perf_counter_ns` median 1.4324 ms.
These measure resolver work only, excluding capture, STT, speech synthesis,
network, playback, and Jetson load. The superseded main-based 0.1 ms result must
not be reused for this build. Raw inventory/timing evidence is saved in the
outer local `deliverables/faq-runtime-review/lookup-evidence.json`.

Visitor synthetic browser QA passed: 42 keyboard transitions at 1024x768 with
reduced motion, zero recorded console/page errors, camera-degraded successful
start, and no browser visitor persistence. The generated completion screenshot
shows both exact phrases with static shell v31. This uses real assets with
intercepted fake APIs/hardware; it is not physical iPad/Jetson acceptance.
Report: `deliverables/faq-runtime-review/visitor-browser/` in the outer workspace.

Optional broader admin browser QA did not pass its final console assertion:
it recorded two HTTP 401 console resource errors during its deliberate invalid-
token scenarios. No admin HTML/JavaScript/CSS is changed in this patch; the
independent synthetic admin logic checks pass. Do not describe this optional
browser run as a clean pass. Its artifacts are retained in the outer
`deliverables/faq-runtime-review/admin-browser/` directory.

## Changed files

- Dialogue: `scripted_faq.py`, `prompt_builder.py`, `dialogue_engine.py`, and
  new `introduction_policy.py`.
- Pipeline/device: `pipeline/session_runner.py`, `app/device_runtime.py`.
- Speech: `audio/cartesia_tts.py`, `audio/piper_tts.py`, new `speech_text.py`.
- Dashboard: `visitor_activation.py`, `runtime_service.py`, visitor JavaScript,
  service worker, completion template and locale strings.
- Corresponding FAQ/pipeline/dialogue/audio/dashboard/visitor/wake regressions,
  including new `test_no_introductions.py` and `test_speech_text.py`.
- Patch history, this handoff, and the pending-local note in CURRENT_STATE.
  No dependency, model, firmware, network,
  service-unit, private settings, or motor change.

## Jetson test stage

Ready for source review: **Yes**, with the optional admin-harness limitation
recorded above. Physical verification: **not done**.
No SSH connection, restart, upload, audio playback, camera or motor test occurred.

Use `handoff/DEPLOYMENT_RUNBOOK.md` for the separately authorized test stage.
Its current `source_release.py` requires a reviewed immutable branch commit
before building. This task remains uncommitted for review; the delivery is a
review patch, not a deployable archive with a false source revision. Keep main
unchanged until the owner accepts the Jetson behavior. Do not use the broad
old `DEPLOY_ATLAS.ps1` for this source-only update. Preserve the running local
voice assets, credentials, venv, models, units, config, and disabled pan state.

Test in this order after staging the reviewed source:

1. Complete English/French onboarding with the sample name Emerson; also test
   admin demo start. Hear no automatic introduction. Ask an ordinary artwork
   question before waking and confirm it answers without an introduction.
2. Say `Hey Atlas` alone in English; hear the named introduction. Repeat it:
   no second intro. Start a fresh French visit and test `Bonjour Atlas`.
   Test either phrase with the other selected language. Stop clears identity.
3. Check `Hello Atlas`, `Hi Atlas`, `Salut Atlas`, quoted phrases, and compound
   greeting-plus-question utterances do not trigger an introduction. A compound
   addressed question should still be answered. If private local synthesis
   fails, restore the local voice and retry with another explicit wake.
4. Ask the exact Mona Lisa example with no camera context, then artist/date/
   material questions and follow-ups. Confirm `scripted_faq` in staff diagnostics.
   Try a named work different from camera context, plus a current-view question
   with a wrong guessed artwork, and confirm the correct subject.
5. Ask deeper event/correction questions such as `When was the Mona Lisa
   stolen?` and `Who painted over the crack during restoration?`. They must
   not receive the generic creation-date/artist answer just due to overlap.
6. In French, test artwork creation years, ranges, and `en 1896`. Hear full
   French number words on Cartesia and Piper fallback. Retain one provider/
   voice within each answer and the existing Atlas name pronunciation.
7. Record end-of-question to first audible answer separately from local FAQ
   lookup. Exercise long answers, wake pauses, stop/restart/cancel, and
   camera-free operation. The damaged camera need not be repaired for this
   voice test; capture remains unavailable without fresh frames.

## Risks and self-attack

Confirmed negative tests counter the strongest software failure: a fast but
incorrect match (event dates, restoration, correction, two artworks, live-view
wrong guesses). Unseen phrasings intentionally fall back rather than inventing
an immediate answer. Catalog completeness checks coverage/source-ID membership,
not fresh curator or native-speaker approval of every translation/fact.

Real STT/accent recognition, French pronunciation, provider quality, private
voice availability, headset echo/routing and total latency remain unverified.
The model filter covers explicit English/French forms; unusual paraphrases or
other languages still rely on prompt instructions and need targeted guards if
observed. A missing local voice cannot be bypassed by sending a name to cloud TTS.

Security/privacy: only synthetic names and public content were used in tests.
No credentials, real visitor logs/recordings, private databases or local device
state are part of the patch. Deployment performed: **No**.
