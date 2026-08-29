/* ATLAS visitor onboarding. Framework-free and intentionally storage-free. */
"use strict";

const $ = (id) => document.getElementById(id);
const steps = [
  "welcome", "language", "about", "expertise", "interests",
  "accessibility", "headset", "readiness", "privacy",
];
const visitor = {
  step: 0,
  firstName: "",
  ageGuidance: null,
  language: null,
  expertise: null,
  interests: [],
  accessibility: [],
  helpContext: "onboarding",
  helpRequestId: null,
  acknowledgedHelpRequestId: null,
  timeoutSeconds: 120,
};
const ENGLISH_STRINGS = {
  "document.title": "ATLAS Museum Guide",
  "brand.subtitle": "Museum guide",
  "status.connecting": "Connecting to your guide",
  "status.online": "Local guide connected",
  "status.offline": "Connection unavailable",
  "progress.aria": "Setup progress",
  "progress.count": "{current} of {total}",
  "step.welcome": "Welcome",
  "step.language": "Language",
  "step.about": "About you",
  "step.expertise": "Art familiarity",
  "step.interests": "Interests",
  "step.accessibility": "Accessibility",
  "step.headset": "Headset",
  "step.readiness": "Readiness",
  "step.privacy": "Privacy",
  "common.optional": "Optional",
  "actions.begin": "Begin setup",
  "actions.privacy": "How your choices are used",
  "actions.back": "Back",
  "actions.continue": "Continue",
  "actions.review_privacy": "Review privacy",
  "actions.help": "Need help",
  "actions.start": "Start my experience",
  "actions.next_visitor": "Set up for the next visitor",
  "actions.welcome_next": "Welcome the next visitor",
  "actions.cancel": "Cancel",
  "actions.done": "Done",
  "actions.got_it": "Got it",
  "actions.not_now": "Not now",
  "actions.request_help": "Request help",
  "actions.request_sent": "Request sent",
  "hint.choose": "Choose one to continue",
  "hint.optional": "Optional — continue when ready",
  "welcome.kicker": "A museum guide shaped around you",
  "welcome.title": "Meet art through your own curiosity.",
  "welcome.lead": "A few quick choices help ATLAS match its stories, pace, and voice to you. It takes about two minutes.",
  "language.kicker": "Choose your language",
  "language.title": "Which language feels most comfortable?",
  "language.lead": "The entire setup will switch as soon as you choose.",
  "language.legend": "Choose a language",
  "language.required": "Choose a language before continuing.",
  "about.kicker": "A little context",
  "about.title": "How should ATLAS guide you?",
  "about.lead": "Both answers are optional. Your name stays on this screen and your age becomes a broad guidance band.",
  "about.name": "First name",
  "about.age": "Age",
  "about.name_placeholder": "What should ATLAS call you?",
  "about.age_placeholder": "Tap to enter your age",
  "age_pad.kicker": "Age guidance",
  "age_pad.title": "Enter your age",
  "age_pad.aria": "Numeric keypad",
  "age_pad.clear": "Clear",
  "age_pad.delete": "Delete last digit",
  "age_pad.range": "Enter your age, or choose Cancel.",
  "age_pad.invalid": "Enter a whole-number age, or choose Cancel.",
  "expertise.kicker": "Set the depth",
  "expertise.title": "How familiar are you with art?",
  "expertise.lead": "Choose the artwork that best matches your comfort level.",
  "expertise.legend": "Choose your art familiarity",
  "expertise.curious_title": "Curious explorer",
  "expertise.curious_desc": "Clear, lively stories with familiar references.",
  "expertise.curious_art": "Mona Lisa",
  "expertise.familiar_title": "I know a little",
  "expertise.familiar_desc": "More context with a few art terms.",
  "expertise.familiar_art": "The Great Wave",
  "expertise.enthusiast_title": "Art enthusiast",
  "expertise.enthusiast_desc": "Deeper technique, symbolism, and history.",
  "expertise.enthusiast_art": "The Ambassadors",
  "interests.kicker": "Choose your lens",
  "interests.title": "What draws you into an artwork?",
  "interests.lead": "Choose any that interest you, or continue without choosing.",
  "interests.legend": "Choose any interests",
  "interests.count": "{count} selected",
  "interest.stories.title": "Stories",
  "interest.stories.desc": "People, myths, and dramatic moments",
  "interest.technique.title": "Technique",
  "interest.technique.desc": "Materials, tools, and the artist’s hand",
  "interest.symbols.title": "Symbols",
  "interest.symbols.desc": "Clues, allegories, and hidden meaning",
  "interest.history.title": "History",
  "interest.history.desc": "The world that shaped the work",
  "interest.color-light.title": "Colour & light",
  "interest.color-light.desc": "Mood, contrast, and atmosphere",
  "interest.people-society.title": "People & society",
  "interest.people-society.desc": "Identity, power, and community",
  "accessibility.kicker": "Make the visit comfortable",
  "accessibility.title": "Would any of these help?",
  "accessibility.lead": "Choose as many as you like, or skip this step.",
  "accessibility.legend": "Accessibility preferences",
  "accessibility.audio_title": "Audio description",
  "accessibility.audio_desc": "More detail about visual elements.",
  "accessibility.simple_title": "Simple language",
  "accessibility.simple_desc": "Shorter sentences and less jargon.",
  "accessibility.pace_title": "Slower pace",
  "accessibility.pace_desc": "More pauses and time to reflect.",
  "accessibility.none_title": "No adjustments",
  "accessibility.none_desc": "Use the standard experience.",
  "headset.kicker": "Your OpenComm2",
  "headset.title": "Open ears. Clear voice. One capture button.",
  "headset.step1": "Rest the pads just in front of your ears and keep the band behind your head.",
  "headset.step2": "Lower the microphone toward your mouth. Use + and − to adjust volume.",
  "headset.step3": "Press the multifunction button once to manually capture the artwork in front of you.",
  "headset.help": "I need help with the headset",
  "headset.callout_fit": "OPEN-EAR FIT",
  "headset.callout_volume": "VOLUME + / −",
  "headset.callout_capture": "1× CAPTURE",
  "headset.callout_mic": "LOWER MIC",
  "readiness.kicker": "One last check",
  "readiness.title": "Preparing your ATLAS unit",
  "readiness.checking": "Checking",
  "readiness.ready": "Ready",
  "readiness.attention": "Needs attention",
  "readiness.unavailable": "Unavailable",
  "readiness.loading_title": "Checking your unit",
  "readiness.loading_detail": "Confirming the local connection and experience settings.",
  "readiness.blocker": "A museum team member must resolve one item before the experience can start.",
  "readiness.item.unit": "Wearable unit",
  "readiness.item.headset": "Headset",
  "readiness.item.connection": "Local connection",
  "readiness.item.camera": "Camera",
  "readiness.item.content": "Museum content",
  "readiness.item.language": "Language support",
  "readiness.item.safety": "Safety controls",
  "readiness.item.profile": "Visitor profile",
  "readiness.detail.ready": "{label} is ready.",
  "readiness.detail.degraded": "{label} needs attention.",
  "readiness.detail.pending": "Waiting for {label}.",
  "readiness.detail.unavailable": "{label} is unavailable.",
  "readiness.detail.unsupported": "This language is not available on this ATLAS unit.",
  "privacy.kicker": "You are in control",
  "privacy.title": "Your setup is temporary.",
  "privacy.lead": "ATLAS uses your choices only to shape this visit. Your name and exact age never leave this screen.",
  "privacy.point1": "Coarse preferences only",
  "privacy.point2": "No raw setup media stored",
  "privacy.point3": "Museum staff can clear the session",
  "privacy.close": "Close privacy information",
  "privacy.dialog_kicker": "Privacy at a glance",
  "privacy.dialog_title": "Personal for this visit. Temporary by design.",
  "privacy.dialog_p1": "Your first name stays in this browser’s memory only. Your age is converted into a broad guidance band before any update is sent.",
  "privacy.dialog_p2": "Nothing is written to browser storage. Setup clears on completion, staff stop, reset, or inactivity.",
  "in_use.kicker": "Profile transferred",
  "in_use.title": "You are ready to explore.",
  "in_use.lead": "Put on your ATLAS unit and follow the museum team’s direction. This kiosk will clear itself.",
  "thanks.kicker": "Experience ended",
  "thanks.title": "Thank you for exploring with ATLAS.",
  "thanks.lead": "Your temporary setup choices have been cleared.",
  "help.close": "Close help dialog",
  "help.kicker": "Museum assistance",
  "help.title": "Would you like a team member?",
  "help.message": "Send a quiet request to the operations desk. You can keep using this screen while you wait.",
  "help.sent_title": "Help is on the way",
  "help.sent_message": "The operations desk has received your request. You can close this message and continue.",
  "help.sent_notice": "A museum team member has been notified.",
  "help.acknowledged": "A museum team member has acknowledged your request.",
  "notice.timeout": "Setup cleared after two minutes of inactivity.",
  "notice.preparing": "Preparing your unit…",
  "error.unavailable": "ATLAS is not available right now."
};

let activeStrings = { ...ENGLISH_STRINGS };
let activeDirection = "ltr";
let inactivityTimer = null;
let navigationInFlight = false;
let interestManifest = null;
let keypadValue = "";
let connectionState = "connecting";
let readinessSnapshot = null;
let readinessRefreshTimer = null;
let readinessRefreshInFlight = false;

function format(template, values = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) => (
    Object.prototype.hasOwnProperty.call(values, key) ? String(values[key]) : `{${key}}`
  ));
}

function t(key, fallback = "") {
  return activeStrings[key] ?? ENGLISH_STRINGS[key] ?? fallback ?? key;
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const response = await fetch(path, { ...options, headers, cache: "no-store" });
  let body = null;
  try { body = await response.json(); } catch (_) { /* empty response */ }
  if (!response.ok) {
    throw new Error(body && body.detail ? String(body.detail) : t("error.unavailable"));
  }
  return body;
}

function notice(message, bad = false) {
  const node = $("visitor-notice");
  node.textContent = message;
  node.classList.toggle("is-bad", bad);
  node.classList.remove("hidden");
  window.clearTimeout(notice.timer);
  notice.timer = window.setTimeout(() => node.classList.add("hidden"), 4200);
}

function selected(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map((node) => node.value);
}

function progressPayload(step) {
  return {
    step,
    language: visitor.language,
    name_entered: Boolean(visitor.firstName),
    age_guidance: visitor.ageGuidance,
    expertise: visitor.expertise,
    interests: visitor.interests,
    accessibility: visitor.accessibility,
  };
}

async function saveProgress(step) {
  return api("/api/visitor/onboarding/progress", {
    method: "POST",
    body: JSON.stringify(progressPayload(step)),
  });
}

function reduceAge() {
  const input = $("visitor-age");
  if (!input.value) return;
  const age = Number(input.value);
  if (Number.isInteger(age) && age >= 0) {
    visitor.ageGuidance = age < 13 ? "under_13" : age < 18 ? "13_17" : "18_plus";
  }
  input.value = "";
}

function captureStep() {
  const step = steps[visitor.step];
  if (step === "language") {
    visitor.language = selected("language")[0] || null;
  } else if (step === "about") {
    visitor.firstName = $("visitor-name").value.trim();
    reduceAge();
  } else if (step === "expertise") {
    visitor.expertise = selected("expertise")[0] || null;
  } else if (step === "interests") {
    visitor.interests = selected("interest");
  } else if (step === "accessibility") {
    visitor.accessibility = selected("accessibility");
  }
}

function validateStep() {
  if (steps[visitor.step] === "language" && !selected("language").length) {
    notice(t("language.required"), true);
    return false;
  }
  return true;
}

function updateDirection() {
  document.documentElement.lang = visitor.language || "en";
  document.documentElement.dir = "ltr";
  document.body.classList.toggle("is-rtl-language", activeDirection === "rtl");
}

function updateConnectionStatus() {
  const isOnline = connectionState === "online";
  $("connection-status").classList.toggle("is-online", isOnline);
  $("connection-status").querySelector("span").textContent = t(`status.${connectionState}`);
}

function applyTranslations() {
  document.title = t("document.title");
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n, node.textContent);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.setAttribute("placeholder", t(node.dataset.i18nPlaceholder, node.getAttribute("placeholder")));
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel, node.getAttribute("aria-label")));
  });
  updateDirection();
  updateConnectionStatus();
  if (interestManifest) renderInterests();
  if (readinessSnapshot) renderReadiness(readinessSnapshot);
  updateChoiceStyles();
  if (steps[visitor.step]) updateJourneyCopy(steps[visitor.step]);
}

async function setLocale(locale) {
  const response = await fetch(`/static/visitor/locales/${encodeURIComponent(locale)}.json`, { cache: "no-store" });
  if (!response.ok) throw new Error(t("error.unavailable"));
  const localeData = await response.json();
  activeStrings = { ...ENGLISH_STRINGS, ...(localeData.strings || {}) };
  activeDirection = localeData.direction === "rtl" ? "rtl" : "ltr";
  visitor.language = locale;
  applyTranslations();
}

function updateJourneyCopy(name) {
  $("progress-label").textContent = t(`step.${name}`, name);
  $("progress-count").textContent = format(t("progress.count"), {
    current: visitor.step + 1,
    total: steps.length,
  });
  $("step-hint").textContent = name === "language" ? t("hint.choose") : t("hint.optional");
  const continueLabel = $("btn-continue").querySelector("[data-i18n]");
  const key = name === "readiness" ? "actions.review_privacy" : "actions.continue";
  continueLabel.dataset.i18n = key;
  continueLabel.textContent = t(key);
}

function showScreen(name) {
  document.querySelectorAll("[data-screen]").forEach((screen) => {
    const isActive = screen.dataset.screen === name;
    screen.classList.toggle("is-active", isActive);
    if (isActive) screen.scrollTop = 0;
  });
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => window.scrollTo(0, 0));
  });
  const inJourney = steps.includes(name);
  document.body.classList.toggle("in-journey", inJourney && name !== "welcome" && name !== "privacy");
  $("progress-dots").parentElement.classList.toggle("hidden", !inJourney);
  $("step-actions").classList.toggle("hidden", !inJourney || name === "welcome" || name === "privacy");
  if (inJourney) {
    visitor.step = steps.indexOf(name);
    [...$("progress-dots").children].forEach((dot, index) => {
      dot.classList.toggle("is-current", index === visitor.step);
      dot.classList.toggle("is-complete", index < visitor.step);
    });
    updateJourneyCopy(name);
  }
  if (name === "readiness") startReadinessPolling();
  else stopReadinessPolling();
  updateDirection();
  window.requestAnimationFrame(() => {
    const heading = document.querySelector(`[data-screen="${name}"] h1`);
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    }
  });
}

function startWelcomeSlideshow() {
  const slides = [...document.querySelectorAll(".welcome-slide")];
  if (slides.length < 2 || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  let activeIndex = Math.max(0, slides.findIndex((slide) => slide.classList.contains("is-active")));
  window.setInterval(() => {
    slides[activeIndex].classList.remove("is-active");
    activeIndex = (activeIndex + 1) % slides.length;
    slides[activeIndex].classList.add("is-active");
  }, 2600);
}

async function goNext() {
  if (navigationInFlight || !validateStep()) return;
  captureStep();
  const next = steps[Math.min(visitor.step + 1, steps.length - 1)];
  navigationInFlight = true;
  try {
    // The admin monitor must receive the screen the visitor is entering.
    await saveProgress(next);
    showScreen(next);
    if (next === "readiness") await refreshReadiness();
  } catch (error) {
    notice(error.message, true);
  } finally {
    navigationInFlight = false;
  }
}

async function goBack() {
  if (navigationInFlight) return;
  captureStep();
  const previous = steps[Math.max(visitor.step - 1, 0)];
  navigationInFlight = true;
  try {
    await saveProgress(previous);
    showScreen(previous);
  } catch (error) {
    notice(error.message, true);
  } finally {
    navigationInFlight = false;
  }
}

function readinessIcon(status) {
  if (status === "ready") return "✓";
  if (status === "degraded") return "!";
  if (status === "pending") return "…";
  return "×";
}

function readinessDetail(item, label) {
  return format(t(`readiness.detail.${item.status}`, item.detail), {
    label: label.toLocaleLowerCase(document.documentElement.lang),
  });
}

function renderReadiness(readiness) {
    const list = $("readiness-list");
    list.replaceChildren();
    readiness.items.forEach((item) => {
      const row = document.createElement("li");
      row.className = `readiness-${item.status}`;
      const icon = document.createElement("span");
      icon.className = "readiness-icon";
      icon.textContent = readinessIcon(item.status);
      const text = document.createElement("div");
      const label = document.createElement("strong");
      const detail = document.createElement("small");
      label.textContent = t(`readiness.item.${item.id}`, item.label);
      detail.textContent = readinessDetail(item, label.textContent);
      text.append(label, detail);
      row.append(icon, text);
      list.append(row);
    });
    $("readiness-summary").textContent = readiness.ready ? t("readiness.ready") : t("readiness.attention");
    $("readiness-summary").className = `readiness-summary ${readiness.ready ? "is-ready" : "is-blocked"}`;
    const blocker = $("readiness-blocker");
    blocker.classList.toggle("hidden", readiness.blockers.length === 0);
    blocker.textContent = readiness.blockers.length ? t("readiness.blocker") : "";
}

function stopReadinessPolling() {
  if (readinessRefreshTimer !== null) {
    window.clearInterval(readinessRefreshTimer);
    readinessRefreshTimer = null;
  }
}

function startReadinessPolling() {
  stopReadinessPolling();
  readinessRefreshTimer = window.setInterval(() => {
    if (steps[visitor.step] === "readiness" && !navigationInFlight) {
      void refreshReadiness({ silent: true });
    }
  }, 2000);
}

async function refreshReadiness({ silent = false } = {}) {
  if (readinessRefreshInFlight) return;
  readinessRefreshInFlight = true;
  const list = $("readiness-list");
  if (!silent) {
    list.innerHTML = `<li class="readiness-loading"><span class="readiness-icon">…</span><div><strong>${t("readiness.loading_title")}</strong><small>${t("readiness.loading_detail")}</small></div></li>`;
  }
  try {
    const readiness = await api("/api/visitor/readiness");
    readinessSnapshot = readiness;
    renderReadiness(readiness);
  } catch (error) {
    $("readiness-summary").textContent = t("readiness.unavailable");
    $("readiness-summary").className = "readiness-summary is-blocked";
    $("readiness-blocker").textContent = error.message;
    $("readiness-blocker").classList.remove("hidden");
  } finally {
    readinessRefreshInFlight = false;
  }
}

async function startExperience() {
  const button = $("btn-start-experience");
  const label = button.querySelector("[data-i18n]");
  const errorNode = $("start-error");
  button.disabled = true;
  label.textContent = t("notice.preparing");
  errorNode.classList.add("hidden");
  try {
    await saveProgress("privacy");
    await api("/api/visitor/onboarding/start", { method: "POST" });
    clearSensitiveBrowserState();
    showScreen("in_use");
    window.clearTimeout(inactivityTimer);
  } catch (error) {
    errorNode.textContent = error.message;
    errorNode.classList.remove("hidden");
    button.disabled = false;
    label.textContent = t("actions.start");
  }
}

function clearSensitiveBrowserState() {
  visitor.firstName = "";
  visitor.ageGuidance = null;
  $("visitor-name").value = "";
  $("visitor-age").value = "";
  keypadValue = "";
}

function closeVisitorDialogs() {
  document.querySelectorAll("dialog[open]").forEach((dialog) => dialog.close());
}

async function resetExperience(timedOut = false) {
  try { await api("/api/visitor/reset", { method: "POST" }); } catch (_) { /* local reset still proceeds */ }
  clearSensitiveBrowserState();
  visitor.language = null;
  visitor.expertise = null;
  visitor.interests = [];
  visitor.accessibility = [];
  visitor.helpRequestId = null;
  visitor.acknowledgedHelpRequestId = null;
  closeVisitorDialogs();
  document.querySelectorAll("input:checked").forEach((input) => { input.checked = false; });
  await setLocale("en");
  updateChoiceStyles();
  showScreen("welcome");
  if (timedOut) notice(t("notice.timeout"));
  restartInactivityTimer();
}

function restartInactivityTimer() {
  if (!steps.includes(steps[visitor.step])) return;
  window.clearTimeout(inactivityTimer);
  inactivityTimer = window.setTimeout(() => resetExperience(true), visitor.timeoutSeconds * 1000);
}

function updateChoiceStyles() {
  document.querySelectorAll(".choice-tile, .interest-card").forEach((tile) => {
    const input = tile.querySelector("input");
    tile.classList.toggle("is-selected", Boolean(input && input.checked));
  });
  const interests = selected("interest");
  visitor.interests = interests;
  if ($("interest-count")) {
    $("interest-count").textContent = format(t("interests.count"), { count: interests.length });
  }
  document.querySelectorAll('input[name="interest"]').forEach((input) => { input.disabled = false; });
}

function bindChoiceControls() {
  document.addEventListener("change", async (event) => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement)) return;
    if (input.name === "language" && input.checked) {
      try {
        await setLocale(input.value);
      } catch (error) {
        notice(error.message, true);
      }
    }
    if (input.name === "accessibility" && input.value === "none" && input.checked) {
      document.querySelectorAll('input[name="accessibility"]').forEach((choice) => {
        if (choice.value !== "none") choice.checked = false;
      });
    } else if (input.name === "accessibility" && input.checked) {
      const none = document.querySelector('input[name="accessibility"][value="none"]');
      if (none) none.checked = false;
    }
    updateChoiceStyles();
  });
}

function renderInterests() {
  if (!interestManifest) return;
  const grid = $("interest-grid");
  const chosen = new Set(visitor.interests);
  grid.replaceChildren();
  interestManifest.interests.forEach((interest) => {
    const label = document.createElement("label");
    label.className = "interest-card";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = "interest";
    input.value = interest.id;
    input.checked = chosen.has(interest.id);
    const image = document.createElement("img");
    image.src = interest.asset;
    image.alt = "";
    const copy = document.createElement("span");
    const title = document.createElement("strong");
    const description = document.createElement("small");
    title.textContent = t(`interest.${interest.id}.title`, interest.label);
    description.textContent = t(`interest.${interest.id}.desc`, interest.description);
    copy.append(title, description);
    label.append(input, image, copy);
    grid.append(label);
  });
  updateChoiceStyles();
}

async function loadInterests() {
  interestManifest = await fetch("/static/visitor/interests.json", { cache: "no-store" }).then((response) => response.json());
  renderInterests();
}

function openAgeKeypad() {
  keypadValue = $("visitor-age").value;
  updateKeypadDisplay();
  $("age-keypad").showModal();
}

function updateKeypadDisplay() {
  $("age-keypad-value").textContent = keypadValue || "—";
  const warning = $("age-keypad-warning");
  const age = Number(keypadValue);
  const invalid = Boolean(keypadValue) && (!Number.isInteger(age) || age < 0);
  warning.classList.toggle("is-invalid", invalid);
  warning.textContent = invalid ? t("age_pad.invalid") : t("age_pad.range");
}

function appendAgeDigit(digit) {
  keypadValue = `${keypadValue}${digit}`.replace(/^0+(?=\d)/, "");
  updateKeypadDisplay();
}

function closeAgeKeypad(commit) {
  if (commit && keypadValue) {
    const age = Number(keypadValue);
    if (!Number.isInteger(age) || age < 0) {
      notice(t("age_pad.invalid"), true);
      return;
    }
    $("visitor-age").value = keypadValue;
  }
  $("age-keypad").close();
}

function bindAgeKeypad() {
  $("visitor-age").addEventListener("click", openAgeKeypad);
  document.querySelectorAll("[data-digit]").forEach((button) => {
    button.addEventListener("click", () => appendAgeDigit(button.dataset.digit));
  });
  $("age-clear").addEventListener("click", () => {
    keypadValue = "";
    updateKeypadDisplay();
  });
  $("age-delete").addEventListener("click", () => {
    keypadValue = keypadValue.slice(0, -1);
    updateKeypadDisplay();
  });
  $("age-cancel").addEventListener("click", () => closeAgeKeypad(false));
  $("age-done").addEventListener("click", () => closeAgeKeypad(true));
  document.addEventListener("keydown", (event) => {
    if (!$("age-keypad").open) return;
    if (/^\d$/.test(event.key)) {
      event.preventDefault();
      appendAgeDigit(event.key);
    } else if (event.key === "Backspace") {
      event.preventDefault();
      keypadValue = keypadValue.slice(0, -1);
      updateKeypadDisplay();
    } else if (event.key === "Enter") {
      event.preventDefault();
      closeAgeKeypad(true);
    }
  });
}

function openHelp(context) {
  visitor.helpContext = context;
  $("help-title").textContent = t("help.title");
  $("help-message").textContent = t("help.message");
  $("btn-send-help").disabled = false;
  $("btn-send-help").textContent = t("actions.request_help");
  $("help-dialog").showModal();
}

async function requestHelp() {
  const button = $("btn-send-help");
  button.disabled = true;
  try {
    const result = await api("/api/visitor/help", {
      method: "POST",
      body: JSON.stringify({ context: visitor.helpContext }),
    });
    visitor.helpRequestId = result.request_id;
    $("help-title").textContent = t("help.sent_title");
    $("help-message").textContent = t("help.sent_message");
    button.textContent = t("actions.request_sent");
    notice(t("help.sent_notice"));
  } catch (error) {
    notice(error.message, true);
    button.disabled = false;
  }
}

async function pollServerState() {
  try {
    const bootstrap = await api("/api/visitor/bootstrap");
    const state = bootstrap.state;
    if (state.phase === "thank_you") {
      clearSensitiveBrowserState();
      closeVisitorDialogs();
      showScreen("thank_you");
      window.clearTimeout(inactivityTimer);
    }
    if (state.help && state.help.status === "acknowledged"
      && state.help.request_id !== visitor.acknowledgedHelpRequestId) {
      visitor.acknowledgedHelpRequestId = state.help.request_id;
      notice(t("help.acknowledged"));
    }
    connectionState = state.connection === "online" ? "online" : "offline";
    updateConnectionStatus();
  } catch (_) {
    connectionState = "offline";
    updateConnectionStatus();
  }
}

async function initialize() {
  bindChoiceControls();
  bindAgeKeypad();
  await setLocale("en");
  await loadInterests();
  const bootstrap = await api("/api/visitor/bootstrap");
  visitor.timeoutSeconds = bootstrap.inactivity_timeout_seconds;
  const visibleLanguages = new Set([
    ...(bootstrap.public_languages || []),
    ...(bootstrap.preview_languages || []),
  ]);
  document.querySelectorAll(".language-tile").forEach((tile) => {
    const input = tile.querySelector('input[name="language"]');
    tile.classList.toggle("hidden", !input || !visibleLanguages.has(input.value));
  });
  if (bootstrap.state.phase === "in_use") {
    clearSensitiveBrowserState();
    showScreen("in_use");
  } else if (bootstrap.state.phase === "thank_you") {
    clearSensitiveBrowserState();
    closeVisitorDialogs();
    showScreen("thank_you");
  }
  connectionState = "online";
  updateConnectionStatus();
  document.querySelectorAll("[data-next]").forEach((button) => button.addEventListener("click", goNext));
  document.querySelectorAll("[data-back]").forEach((button) => button.addEventListener("click", goBack));
  document.querySelectorAll("[data-reset]").forEach((button) => button.addEventListener("click", () => resetExperience()));
  document.querySelectorAll("[data-open-dialog]").forEach((button) => button.addEventListener("click", () => $(button.dataset.openDialog).showModal()));
  document.querySelectorAll("[data-help]").forEach((button) => button.addEventListener("click", () => openHelp(button.dataset.help)));
  $("btn-send-help").addEventListener("click", requestHelp);
  $("btn-start-experience").addEventListener("click", startExperience);
  ["pointerdown", "keydown", "touchstart"].forEach((eventName) => document.addEventListener(eventName, restartInactivityTimer, { passive: true }));
  if (!["in_use", "thank_you"].includes(bootstrap.state.phase)) restartInactivityTimer();
  window.setInterval(pollServerState, 1500);
  startWelcomeSlideshow();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/service-worker.js").catch(() => {});
}

initialize().catch((error) => notice(error.message, true));
