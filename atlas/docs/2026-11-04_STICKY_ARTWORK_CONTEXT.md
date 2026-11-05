# Keep the visitor-selected artwork active

Branch: `codex/sticky-artwork-context`, continuing installed source `d745d3d`
and its deployment documentation `363a776`. The owner explicitly requests a
Jetson test deployment and forbids promotion to main.

## Behavior

- A supported, unambiguous closing invitation can register a pending artwork
  even when the visitor did not explicitly ask for a recommendation. A generic
  learn-more question after a clear named recommendation is supported too.
- Only known catalog titles/aliases are candidates. Incidental mentions,
  comparison invitations and multiple-choice artwork offers do not arbitrarily
  select a new work. Rejection, interruption and visit reset discard the offer.
- Accepting the offer or explicitly naming an artwork locks the discussion to
  that work. Ordinary unnamed followups retain it across camera changes, loss
  of frames and history rotation. Live camera metadata remains separate.
- A direct current-view question, explicit capture or staff artwork selection
  can reselect the actual camera work. A missing frame never becomes a claimed
  live identification. When no spoken topic is locked, automatic camera changes
  keep their existing behavior.
- A passive camera invitation about a different work is suppressed while a
  visitor-selected discussion is locked. Explicit capture can still change it.
- Yes/Oui accepting a supported prepared artwork introduces that new work locally
  before its next relevant question. The typed and both spoken routes share the
  state. Original visitor wording is retained in the bounded visit history.
- Generated-answer instructions use DISCUSSION ARTWORK for implicit followups
  while current-view questions still use CURRENT ARTWORK. Two existing camera
  transition tests now ask explicitly what is being viewed instead of relying
  on the ambiguous phrase 'Who painted this?' to discard a selected topic.

No new model/provider call, database, persistence, history expansion or dependency
is introduced. History stays at 12 recent turns with the existing bounded archive.
Normal/slow speech settings, STT waits, wake introductions and private names are
unchanged. End-to-end latency and live-provider acceptance still need the owner’s
physical test; no numerical latency promise is made.

## Validation and release

Focused synthetic gate passes 513 cases, including spontaneous offers, catalog
ambiguity, long followups, camera override, passive invitations, original wording,
streamed and whole generated proposals, and direct prepared acceptance without
retrieval/model calls. The complete local gate passes 4,771 tests with three
explicit skips (C++ compiler, Windows symlink privilege, opt-in real inference).
The JUnit case count and separate collection both equal 4,774. Lint, compile,
dependency compatibility, secrets, recovery, repository layout and 106 synthetic
JavaScript checks pass. The installed source matches the preceding speech release
with no unreviewed managed source drift. Jetson replacement is pending.
