/* ATLAS visitor onboarding. Framework-free and intentionally storage-free. */
"use strict";

const $ = (id) => document.getElementById(id);
const steps = [
  "welcome", "language", "about", "expertise", "interests",
  "accessibility", "headset", "readiness", "privacy",
];
const stepLabels = [
  "Welcome", "Language", "About you", "Art familiarity", "Interests",
  "Accessibility", "Headset", "Readiness", "Privacy",
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
let inactivityTimer = null;

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const response = await fetch(path, { ...options, headers, cache: "no-store" });
  let body = null;
  try { body = await response.json(); } catch (_) { /* empty response */ }
  if (!response.ok) {
    throw new Error(body && body.detail ? String(body.detail) : "ATLAS is not available right now.");
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
  if (Number.isFinite(age) && age >= 5 && age <= 120) {
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
    notice("Choose a language before continuing.", true);
    return false;
  }
  return true;
}

function updateDirection() {
  const rtl = visitor.language === "ar";
  document.documentElement.lang = visitor.language || "en";
  document.documentElement.dir = rtl ? "rtl" : "ltr";
}

function showScreen(name) {
  document.querySelectorAll("[data-screen]").forEach((screen) => {
    screen.classList.toggle("is-active", screen.dataset.screen === name);
  });
  const inJourney = steps.includes(name);
  $("progress-dots").parentElement.classList.toggle("hidden", !inJourney);
  $("step-actions").classList.toggle("hidden", !inJourney || name === "welcome" || name === "privacy");
  if (inJourney) {
    visitor.step = steps.indexOf(name);
    $("progress-label").textContent = stepLabels[visitor.step];
    $("progress-count").textContent = `${visitor.step + 1} of ${steps.length}`;
    [...$("progress-dots").children].forEach((dot, index) => {
      dot.classList.toggle("is-current", index === visitor.step);
      dot.classList.toggle("is-complete", index < visitor.step);
    });
    $("step-hint").textContent = name === "language"
      ? "Choose one to continue" : "Optional — continue when ready";
    $("btn-continue").textContent = name === "readiness" ? "Review privacy →" : "Continue →";
  }
  updateDirection();
  window.requestAnimationFrame(() => {
    const heading = document.querySelector(`[data-screen="${name}"] h1`);
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    }
  });
}

async function goNext() {
  if (!validateStep()) return;
  captureStep();
  const current = steps[visitor.step];
  const next = steps[Math.min(visitor.step + 1, steps.length - 1)];
  try {
    if (current !== "welcome") await saveProgress(current);
    if (current === "language") updateDirection();
    showScreen(next);
    if (current === "language" && visitor.language !== "en") {
      notice("Language preview selected. Interface copy remains in English for Pass 1.");
    }
    if (next === "readiness") await refreshReadiness();
  } catch (error) {
    notice(error.message, true);
  }
}

function goBack() {
  captureStep();
  showScreen(steps[Math.max(visitor.step - 1, 0)]);
}

function readinessIcon(status) {
  if (status === "ready") return "✓";
  if (status === "degraded") return "!";
  if (status === "pending") return "…";
  return "×";
}

async function refreshReadiness() {
  const list = $("readiness-list");
  list.innerHTML = '<li class="readiness-loading"><span></span><div><strong>Checking your unit</strong><small>Confirming the local connection and experience settings.</small></div></li>';
  try {
    const readiness = await api("/api/visitor/readiness");
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
      label.textContent = item.label;
      detail.textContent = item.detail;
      text.append(label, detail);
      row.append(icon, text);
      list.append(row);
    });
    $("readiness-summary").textContent = readiness.ready ? "Ready" : "Needs attention";
    $("readiness-summary").className = `readiness-summary ${readiness.ready ? "is-ready" : "is-blocked"}`;
    const blocker = $("readiness-blocker");
    blocker.classList.toggle("hidden", readiness.blockers.length === 0);
    blocker.textContent = readiness.blockers.join(" ");
  } catch (error) {
    $("readiness-summary").textContent = "Unavailable";
    $("readiness-summary").className = "readiness-summary is-blocked";
    $("readiness-blocker").textContent = error.message;
    $("readiness-blocker").classList.remove("hidden");
  }
}

async function startExperience() {
  const button = $("btn-start-experience");
  const errorNode = $("start-error");
  button.disabled = true;
  button.textContent = "Preparing your unit…";
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
    button.textContent = "Start My Experience →";
  }
}

function clearSensitiveBrowserState() {
  visitor.firstName = "";
  visitor.ageGuidance = null;
  $("visitor-name").value = "";
  $("visitor-age").value = "";
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
  updateChoiceStyles();
  showScreen("welcome");
  if (timedOut) notice("Setup cleared after two minutes of inactivity.");
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
  $("interest-count").textContent = `${interests.length} of 3 selected`;
  document.querySelectorAll('input[name="interest"]:not(:checked)').forEach((input) => {
    input.disabled = interests.length >= 3;
  });
}

function bindChoiceControls() {
  document.addEventListener("change", (event) => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement)) return;
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

async function loadInterests() {
  const manifest = await fetch("/static/visitor/interests.json", { cache: "no-store" }).then((response) => response.json());
  const grid = $("interest-grid");
  manifest.interests.forEach((interest) => {
    const label = document.createElement("label");
    label.className = "interest-card";
    label.innerHTML = `<input type="checkbox" name="interest" value="${interest.id}"><img src="${interest.asset}" alt=""><span><strong>${interest.label}</strong><small>${interest.description}</small></span>`;
    grid.append(label);
  });
}

function openHelp(context) {
  visitor.helpContext = context;
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
    $("help-title").textContent = "Help is on the way";
    $("help-message").textContent = "The operations desk has received your request. You can close this message and continue.";
    button.textContent = "Request sent";
    notice("A museum team member has been notified.");
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
      notice("A museum team member has acknowledged your request.");
    }
    $("connection-status").classList.toggle("is-online", state.connection === "online");
    $("connection-status").lastChild.textContent = state.connection === "online"
      ? " Private local setup" : " Connection unavailable";
  } catch (_) {
    $("connection-status").classList.remove("is-online");
    $("connection-status").lastChild.textContent = " Connection unavailable";
  }
}

async function initialize() {
  bindChoiceControls();
  await loadInterests();
  const bootstrap = await api("/api/visitor/bootstrap");
  visitor.timeoutSeconds = bootstrap.inactivity_timeout_seconds;
  if (bootstrap.mode !== "mock") {
    document.querySelectorAll(".language-tile.is-preview").forEach((tile) => tile.classList.add("hidden"));
  }
  if (bootstrap.state.phase === "in_use") {
    clearSensitiveBrowserState();
    showScreen("in_use");
  } else if (bootstrap.state.phase === "thank_you") {
    clearSensitiveBrowserState();
    closeVisitorDialogs();
    showScreen("thank_you");
  }
  $("connection-status").classList.add("is-online");
  document.querySelectorAll("[data-next]").forEach((button) => button.addEventListener("click", goNext));
  document.querySelectorAll("[data-back]").forEach((button) => button.addEventListener("click", goBack));
  document.querySelectorAll("[data-reset]").forEach((button) => button.addEventListener("click", () => resetExperience()));
  document.querySelectorAll("[data-open-dialog]").forEach((button) => button.addEventListener("click", () => $(button.dataset.openDialog).showModal()));
  document.querySelectorAll("[data-help]").forEach((button) => button.addEventListener("click", () => openHelp(button.dataset.help)));
  $("btn-send-help").addEventListener("click", requestHelp);
  $("btn-start-experience").addEventListener("click", startExperience);
  $("visitor-age").addEventListener("change", reduceAge);
  ["pointerdown", "keydown", "touchstart"].forEach((eventName) => document.addEventListener(eventName, restartInactivityTimer, { passive: true }));
  if (!["in_use", "thank_you"].includes(bootstrap.state.phase)) restartInactivityTimer();
  window.setInterval(pollServerState, 1500);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/service-worker.js").catch(() => {});
}

initialize().catch((error) => notice(error.message, true));
