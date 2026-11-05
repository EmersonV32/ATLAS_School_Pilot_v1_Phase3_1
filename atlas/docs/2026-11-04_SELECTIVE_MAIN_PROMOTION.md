# Selected conversation/audio features for main

The owner explicitly approved promoting these features together after clarifying
that the last-artwork memory and the input-ready **buzz** are included. This is
a selective port onto main baseline `9dfe260`, not a merge of the complete
`codex/sticky-artwork-context` lineage.

## Included

- Consistent normal synthesis speed 0.90, with 0.80 only for the explicit slower
  pace preference; simple language does not select a faster voice. Cartesia,
  Piper, fallback, whole/streamed responses and main's existing local greeting
  receive the control. The same response keeps one synthesis speed.
- A relevant closing question for ordinary successful answers. Local French and
  English greetings, wellbeing, thanks and jokes support gradual conversation;
  ending a conversation, provider errors and safety refusals are respected.
- Endpoint waits 500 ms ordinary / 1,000 ms hesitant or incomplete speech /
  300 ms confirmed complete prepared question. The conservative completeness,
  timed-final accumulation and cancellation prerequisites are included so the
  shorter waits do not simply discard a continuing question. These are local
  silence waits, not a promise of equal end-to-end answer latency.
- A reusable Deepgram connection with idle KeepAlive and no idle microphone
  capture. Finalization/old-turn filtering and visit/language/stop cancellation
  keep one visitor's transcription from leaking into the next turn or visit.
- A short input-ready buzz, with existing off/beep controls. It occurs only
  after the input opens and is not repeated for every empty listen window.
- Visit-only artwork memory. Explicitly selected works and accepted unambiguous
  catalogue suggestions stay active for unnamed followups across camera changes.
  Current-view questions/manual capture can reselect the actual camera work;
  passive camera invitations cannot interrupt a different locked discussion.
  Reset clears the state. Main keeps its existing three-exchange history window;
  the selected artwork is separate and survives that window rotating. The older
  branch's extended archives are excluded. No cloud summarizer, database or
  additional provider is introduced.

## Integration boundaries

Required wiring is confined to audio adapters/settings, dialogue state/prompt
rules, the two question entry paths, session cancellation and nonvisual speech
configuration API fields. Spoken routes share the existing prepared-answer path
so they commit the same artwork/interaction state. The existing FAQ facts and
answer matcher are preserved; added exact-form helpers serve endpointing and
catalogue-name resolution. Original visitor text remains in ephemeral history.

The camera/detector/hardware code, firmware, model files, networking/deployment
scripts, website, visitor activation policy, speech-text/date normalization,
dashboard HTML/CSS/JavaScript, dependency declarations and other pending fixes
remain at main's baseline. No wholesale copy of the pending runtime is used.
Other feature branches remain available and are not deleted or reset.

## Validation and device distinction

The final main-based gate passes **3,346 tests with one opt-in real-inference
skip**. JUnit contains 3,347 cases, matching the independently collected 3,347.
Ruff, compileall, offline dependency compatibility, secret scan, recovery/layout
checks, the selective-scope audit and whitespace checks pass. No UI markup or
asset was changed; visual layouts and real providers were not exercised.
Feature tests exercised both providers, input-ready ordering, reused
sockets, incomplete speech, local/generated questions, accepted recommendations,
typed/whole/streamed paths, manual selection and visit reset. The complete gate
also retains the original main regressions. No real cloud speech or headset test
is represented by these synthetic checks. Main's original three-turn regression
still passes while the sticky subject survives twenty subsequent followups.
Session reset during a spoken capture rejects the obsolete question.

The Jetson still runs the previously tested full branch source **`fcf646e`**.
Its installed manifest was rechecked with zero mismatches, and the service was
active/running. The enabled user service and desktop automatic-login settings
were checked read-only; a fresh power-cycle rehearsal was not performed. This
selective main promotion does not redeploy or restart the Jetson. Keep that
installed version for the Bourget presentation unless the owner separately
requests another deployment. A future deployment of main would exclude the
other pending fixes and needs its own reconciliation and acceptance.

Read-only scope evidence and isolated test outputs are retained outside Git in
`deliverables/selective-main-20261104/`. No secrets, live visitor state, raw media
or private configuration were read or included in this promotion.
