# Visitor dashboard implementation status

## Pass 1 target

- Product, information architecture, API, privacy, localization, asset, test,
  and iPad review contracts: specified.
- Visitor onboarding UI and Visitor Live monitor: mock-backed Pass 1 complete.
- Existing runtime/API compatibility: covered by the complete automated suite.
- Desktop browser review at an explicit 1024x768 viewport: complete, including
  the full journey, help lifecycle, operator stop, reset, reload recovery, and
  Arabic RTL preview.
- Static-shell service worker: complete with a versioned allowlist and no API
  response caching.

## Pass 2 runtime bridge

- Device mode now shares the existing `RuntimeService` with visitor onboarding.
- The visitor language and a coarse explanation profile transfer only when the
  visitor starts; the live `SessionRunner` forwards that profile to the prompt
  builder for spoken answers.
- Device-mode readiness comes from the real runtime: unit, audio pathway,
  local response connection, fresh camera frame, content, language support,
  and emergency-stop state.
- Starting is guarded by readiness and starts one shared runtime session. A
  staff stop or kiosk reset stops that runtime session before clearing the
  browser-facing state.
- Dev and laptop tests remain mock-backed. Browser onboarding is not allowed to
  expose hardware details, provider names, transcripts, answers, media, names,
  or exact ages.
- Visitor start now creates a selected-language wake gate. Only “Hello ATLAS”
  or its configured local-language equivalent activates normal question
  handling; wake matching is deterministic and adds no LLM request.
- The optional first name uses a local-only Piper greeting, remains only in
  private runtime memory for the active visit, and is erased on stop. It cannot
  enter Gemini, Cartesia, RAG, status responses, logs, or monitoring.
- Browser age reduction now separates visitors aged 6 or younger into an
  `early_child` profile. The prompt specifies one idea at a time, common words,
  short sentences, concrete examples, and explanations for art terms in every
  visitor-ready spoken language. Age remains the primary speaking level when
  accessibility options are selected; audio description and other adjustments
  are layered on top instead of replacing the child's age profile.
- Ten deterministic FAQ intents are available for all seven demo artworks, all
  five visitor-ready spoken languages, and every age/expertise/accessibility
  profile. Phrase and close-paraphrase matching happens locally before RAG.
- Scripted turns enter the same three-completed-turn conversation memory. A
  question that does not match the scripted catalogue continues through the
  existing hybrid dense/keyword RAG and Gemini path.
- Onboarding interests, expertise, and accessibility choices now shape the
  dialogue prompt. A bounded local preference extractor can add only approved
  art-interest and explanation-style labels for the active session.
- The existing dialogue memory remains capped at the three most recently
  completed question/answer turns and resets at session end.

## Pass 2 still required

- Physical Jetson/Shokz validation of wake recognition and every public-language
  local greeting voice.
- Native-speaker review of the French, Spanish, Italian, and Traditional Chinese
  scripted answers before a public museum deployment.
- Runtime interaction-state and inactivity-policy validation on the physical
  Jetson.
- Public-mode configuration and trusted-network deployment design.

## Pass 3 required

- Adversarial visual/accessibility/privacy review.
- PWA, iPad Safari, RTL, focus, and cache hardening.
- Human-validation, installation, trusted-network, Jetson-validation,
  rollback, and limitations runbooks.

## Physical validation required

The runtime bridge has automated coverage but does not yet prove physical
Jetson, Shokz, XIAO camera, router, cloud-provider, EV3, or iPad behavior.
Those gates remain explicitly pending.
