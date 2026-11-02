# Shorter question pauses and prepared-answer verification

The owner requested a one-second normal end-of-question pause instead of two,
and a two-second incomplete-question pause instead of four. This change is on
`codex/faster-question-endpoint`, descended from `codex/full-wake-introduction`
at `1654015`, preserving the earlier introduction and prepared-answer work.

## Behavior

| Question state | Previous default | New default |
| --- | --- | --- |
| General question | 2,000 ms | 1,000 ms |
| Obviously unfinished or hesitant question | 4,000 ms | 2,000 ms |
| Eligible exact, timed final prepared question | 600 ms stable silence | 600 ms stable silence |

The YAML, validated settings model, direct Deepgram constructor and onsite
settings preparation tool agree on the new normal/incomplete defaults. Explicit
site overrides remain authoritative. First-speech waiting and maximum utterance
length are unchanged. A late prepared final cannot extend the normal deadline;
resumed speech and final-coverage checks still protect the FAQ shortcut.

Prepared responses already bypass retrieval and Gemini in both spoken pipeline
entry points. They are selected locally with the visitor's language/profile,
remembered for follow-ups, and passed as complete text to TTS. This task does
not regenerate that catalogue or add a model rewrite. Unmatched, ambiguous or
deeper questions retain the normal retrieval/model route.

The expanded English/French integration checks forbid both retrieval and model
calls, capture the TTS request, and assert that its text exactly equals the
selected prepared response. Existing catalogue-wide coverage checks remain.

## Validation

The guarded focused suite passes **3,186 tests with one skip**. The complete
guarded local suite passes **4,547 tests with three skips**; independent
collection confirms **4,550 tests**. Ruff, compilation, obvious-secret scan,
recovery bundle, repository layout and whitespace checks pass. The existing
venv has no pip module, so dependency compatibility is checked with
`uv --no-cache pip check --offline --python <existing-venv-python>`; it passes
without changing installed packages. Existing dependency deprecations and the
malformed-ZIP regression fixture warning remain non-failing.

The initial expanded French test fixtures omitted the visitor language and
expected a subject answer for an identification question, then used a localized
artist name absent from the maintained catalogue. Those fixture expectations
were corrected; no FAQ runtime defect was established by those failures.
Windows sandbox execution also denied pytest temporary-directory access, so
the isolated suite is being run in the approved host execution context.

## Jetson application — confirmed 2026-11-02

The owner confirmed the Jetson is online for retesting. A fresh baseline found
five public files different from the last recorded `228f4da` release:
`app/device_runtime.py`, `dashboard/runtime_service.py`,
`dashboard/visitor_activation.py`, `dialogue/dialogue_engine.py` and
`dialogue/prompt_builder.py` (under `src/atlas/`). Their differences concern
greetings/self-identification and are outside this pause change. The full
source replacement was stopped before applying; those existing edits were
preserved. Do not infer a new complete installed source SHA from this update.

Instead, the already-supported configuration fields were updated on the
existing runtime. Both YAML layers now contain 1,000/2,000 ms; effective
validated settings after one authorized user-service restart confirm those
values and the retained 600 ms prepared-question shortcut. All 203 public
managed source files and eight public fixtures are byte-for-byte identical to
the fresh pre-change baseline, including the five existing differences.
Environment-file metadata, model/unit metadata, boot ID and unexpected restart
count are unchanged. Service active/running, ExecMainStatus 0, NRestarts 0;
visitor/admin/health return 200 and protected audio/pan routes return 401.

Additional mocked acceptance on the installed Jetson source: **17 passed**.
Five capture simulations use the actual effective pause fields, including
resumed speech; twelve English/French cases forbid retrieval/model calls and
assert the complete prepared text is submitted to TTS. These are tests on the
Jetson, not recordings of physical microphone/headset/provider behavior.

Settings rollback backup retained:
`/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated/.atlas-onsite-settings-backups/dd6c6c96aa1e46f4bece37b33562c16a`.
The previous complete source rollback remains unchanged. No firmware, packages,
service unit, network or motor configuration was changed.

A future source-only release preserves installed `config/settings.yaml` and
dashboard overrides. Changing source defaults alone does not replace explicit
site values. The applied configuration change has exactly this scope:

```json
{
  "speech": {
    "silero_min_silence_ms": 1000,
    "silero_hesitation_silence_ms": 2000
  }
}
```

Do not run the broader onsite migration just to change these two fields: that
tool also stages other settings. The task-scoped `pause_settings.py` wrapper
reuses its reviewed atomic two-file write/backup/rollback transaction with the
patch restricted to these two fields. Synthetic tests check dry-run, preserved
unrelated settings, exact original backups and restoration after a failed
second write. It never loads dotenv or prints existing configuration. Local
deployment evidence and wrappers are outside Git under
`ATLAS/deliverables/question-pauses-20261102/`. Follow the source-only
deployment/rollback runbook and coordinate the service interruption.

For physical acceptance, test a complete French/English prepared question,
one accepted follow-up, a question resuming within one second, and an unfinished
question resuming within two seconds. Longer pauses may now end a turn sooner,
as explicitly requested. Measure from the visitor's last voiced sound to the
first audible answer; player-input timestamps and mocked tests cannot prove an
under-two-second headset response. Keep `main` unchanged until acceptance.

The local branch carries the new defaults for future source integration;
**it was not installed wholesale over the divergent live tree**. Reconcile the
preserved public-source drift before a later full source promotion or main
merge. No dashboard UI changed, so no new visual acceptance is claimed.
No dependencies or schema fields were added. No credential contents were
inspected or logged.
Ready for scoped code review; physical audible latency remains pending.
