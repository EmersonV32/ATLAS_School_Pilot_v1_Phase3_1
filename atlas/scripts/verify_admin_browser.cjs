/* Optional headless UI QA with Playwright supplied by the test environment.
 * Uses the real HTML/CSS/JS and intercepted synthetic APIs. No server or keys.
 * Run: node scripts/verify_admin_browser.cjs OUTPUT_DIR [CHROME_EXECUTABLE]
 */
"use strict";
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "../src/atlas/dashboard");
const output = path.resolve(process.argv[2]);
fs.mkdirSync(output, { recursive: true });
const clone = value => JSON.parse(JSON.stringify(value));
const languages = ["en", "fr", "es", "zh", "pt", "ar", "hi", "de", "it", "ja", "ko", "ru", "bn", "id", "te", "tr", "vi", "ta", "th", "pl"];
const html = fs.readFileSync(path.join(root, "templates/admin.html"), "utf8").replace("<!-- ATLAS_ADMIN_LANGUAGE_OPTIONS -->", languages.map(code => `<option value="${code}">${code.toUpperCase()}</option>`).join(""));
const config = {
  llm: { provider: "mock", model: "mock-guide", timeout_s: 12, cloud_llm_enabled: false, streaming_enabled: false, sentence_tts_enabled: false },
  speech: { stt_provider: "deepgram", tts_provider: "cartesia", deepgram_model: "nova-3", deepgram_language: "multi", listen_duration_s: 8, cartesia_model: "sonic-3", cartesia_voice_id: "synthetic-voice", silero_threshold: 0.5, silero_min_silence_ms: 2000, cloud_speech_enabled: false, offline_fallback_enabled: true },
  hardware: { yolo_backend: "auto", vision_conf_threshold: 0.65, vision_mask_conf_threshold: 0.7, vision_center_weight: 0.5, vision_center_threshold: 0.5, vision_hold_seconds: 1, vision_gap_tolerance_s: 1, manual_capture_crop_ratio: 0.8, camera_width: 800, camera_height: 600, camera_fps: 15 },
  rag: { top_k: 4, dense_top_k: 8, keyword_top_k: 8, chunk_max_words: 100, language_fallback_enabled: true, fallback_language: "en" },
  logging: { log_transcripts: false, log_live_stt: false, log_llm_responses: false },
};
const initial = {
  status: { mode: "dev", session_active: false, demo_active: false, emergency_stopped: false, experience: { language: "en", profile: "adult_beginner", pack_id: "demo_pack", accessibility_mode: false }, artwork: { artwork_id: "mona_lisa", label: "Mona Lisa", stable: true, confidence: 0.94, source: "synthetic" }, camera: { ready: true, actual_width: 800, actual_height: 600, observed_fps: 15, last_frame_age_s: 0.1, last_error: null }, last_answer: null },
  health: { components: { stt: "MockSTT", tts: "MockTTS", vision: "MockVision", retriever: "HybridRetriever", vector_store: "ok", llm: "MockLLM", hardware: "MockHardware" } },
  audio: { route: "headset", volume_percent: 75, output_device_name: "Simulated headset output", headset_name: "Simulated microphone", headset_available: true, speaker_available: true, both_available: true, provider: "MockTTS" },
  visitor: { state: { unit_id: "ATLAS demo", connection: "online", phase: "idle", step: "welcome", language: "en", demo_mode: false, transfer: "idle", updated_at: new Date().toISOString(), profile: { age_guidance: null, interests: [], accessibility: [], expertise: null } }, readiness: { ready: true, blockers: [], items: ["camera", "headset", "speech", "knowledge"].map(id => ({ id, label: id, status: "ready", detail: "Synthetic check" })) }, help_request: null },
};
const activityEntry = (id, actor, kind, text, raw, level = "info") => ({id, source: "runtime", actor, kind, text, raw, level, timestamp: "2026-10-12 10:30:00"});
let activitySnapshot = {
  snapshot_id: "synthetic-activity-1", captured_at: "2026-10-12T14:30:00Z", runtime_available: true,
  text_visibility: { user_final: true, user_live: true, atlas: true },
  runtime: [
    activityEntry("listen", "Listening", "listening", "The microphone is listening in English. The visitor can ask a question.", "[STT] Preparing to listen [language=en timeout=45s]"),
    activityEntry("question", "User", "conversation", "Question: “Who is in the Mona Lisa?”", "[STT final] Who is in the Mona Lisa?"),
    activityEntry("answer", "ATLAS", "conversation", "Response: “The Mona Lisa is a portrait of Lisa Gherardini, painted by Leonardo da Vinci.”", "[LLM final] The Mona Lisa is a portrait of Lisa Gherardini, painted by Leonardo da Vinci."),
    activityEntry("camera", "Camera", "camera", "The camera detected Mona Lisa. This artwork is now selected.", "[Vision] Triggered Mona Lisa after 1.2s"),
    activityEntry("button", "Button", "button", "The headset multifunction button was pressed. ATLAS will identify the artwork in front of the camera.", "[Button] Manual artwork capture requested"),
    activityEntry("check", "System", "system", "Synthetic knowledge check complete. No physical devices connected.", "Synthetic knowledge check complete. No physical devices connected."),
  ],
  events: [{id: "session", source: "events", actor: "Session", kind: "session", level: "info", timestamp: "2026-10-12T14:29:00Z", text: "A demonstration session started.", raw: {event: "demo_session_start", state: "session"}}],
};
const report = { layouts: [], actions: [], failures: [], errors: [], contrastChecks: 0 };

(async () => {
  const browser = await chromium.launch({ headless: true, downloadsPath: output, ...(process.argv[3] ? { executablePath: process.argv[3] } : {}) });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce", serviceWorkers: "block", acceptDownloads: true });
    const page = await context.newPage();
    page.on("pageerror", error => report.errors.push(String(error)));
    let state = clone(initial);
    let auth = false;
    let acceptedToken = "synthetic-test-token";
    let failedAction = false;
    let previewFailed = false;
    let offline = false;
    let expectedFailure = false;
    let previewRequests = 0;
    let activityRequests = 0;
    let failActivity = false;
    page.on("console", message => { if (message.type() === "error" && !expectedFailure) report.errors.push(message.text()); });
    await context.route("**/*", async route => {
      const request = route.request();
      const url = new URL(request.url());
      assert.equal(url.hostname, "atlas.test", "Unexpected external network request");
      const pathname = url.pathname;
      const json = value => route.fulfill({ contentType: "application/json", body: JSON.stringify(value) });
      if (pathname === "/admin") return route.fulfill({ contentType: "text/html", body: html });
      if (pathname.startsWith("/static/")) {
        assert(["/static/style.css", "/static/admin.js"].includes(pathname), "Unexpected static file");
        return route.fulfill({ contentType: pathname.endsWith(".css") ? "text/css" : "text/javascript", body: fs.readFileSync(path.join(root, pathname.slice(1))) });
      }
      if (pathname === "/favicon.ico") return route.fulfill({ status: 204 });
      if (pathname === "/admin/access") return json({ auth_required: auth });
      if (auth && request.headers()["x-atlas-admin-token"] !== acceptedToken) return route.fulfill({ status: 401, contentType: "application/json", body: '{"detail":"Token not accepted"}' });
      if (offline) return route.abort();
      if (pathname.endsWith("frame.jpg")) {
        previewRequests++;
        if (previewFailed) return route.fulfill({ status: 503 });
        return route.fulfill({ contentType: "image/webp", body: fs.readFileSync(path.join(root, "static/visitor/assets/gallery-mona-lisa.webp")) });
      }
      if (request.method() !== "GET") {
        report.actions.push(`${request.method()} ${pathname}`);
        if (failedAction) return route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Synthetic action failed. Please retry."}' });
        const body = request.postDataJSON() || {};
        if (pathname === "/admin/config") { Object.entries(body).forEach(([key, value]) => Object.assign(config[key], value)); return json({ config, restart_required: true }); }
        if (pathname === "/session/profile") { Object.assign(state.status.experience, body); return json({}); }
        if (pathname === "/api/admin/demo/start") { state.status.session_active = state.status.demo_active = true; return json({}); }
        if (pathname === "/api/admin/session/stop") { state.status.session_active = state.status.demo_active = false; return json({}); }
        if (pathname === "/api/admin/audio") { Object.assign(state.audio, body); return json(state.audio); }
        if (pathname === "/api/admin/audio/test") return json({ audio: state.audio });
        if (pathname === "/hardware/emergency-stop") state.status.emergency_stopped = true;
        if (pathname === "/hardware/clear-emergency-stop") state.status.emergency_stopped = false;
        if (pathname.includes("/acknowledge")) state.visitor.help_request.status = "acknowledged";
        return json({ ok: true, synthetic: true });
      }
      if (pathname === "/admin/config") return json({ config, restart_required: false });
      if (pathname === "/status") return json(state.status);
      if (pathname === "/health") return json(state.health);
      if (pathname === "/api/admin/audio") return json(state.audio);
      if (pathname === "/api/admin/live-status") return json(state.visitor);
      if (pathname === "/content/packs") return json([{ pack_id: "demo_pack", name: "Museum collection", selected: true }]);
      if (pathname === "/artworks") return json([{ artwork_id: "mona_lisa", title: "Mona Lisa" }, { artwork_id: "starry_night", title: "The Starry Night" }]);
      if (pathname === "/logs/snapshot") {
        activityRequests++;
        if (failActivity) return route.fulfill({status: 503, contentType: "application/json", body: '{"detail":"Synthetic activity offline"}'});
        return json(activitySnapshot);
      }
      if (pathname === "/api/admin/arducam/status") return json({ ready: true, enabled: true, source: "Synthetic CSI preview", configured_width: 800, configured_height: 600, configured_fps: 15, observed_fps: 15, sensor_id: 0, last_frame_age_s: 0.1, reconnect_count: 0 });
      throw new Error(`Unexpected endpoint ${pathname}`);
    });
    const ready = () => page.waitForFunction(() => document.querySelector("#issue-board").dataset.severity === "ok");
    await page.goto("http://atlas.test/admin");
    await ready();
    await page.waitForFunction(() => document.querySelector("#admin-camera").naturalWidth > 0);
    assert.match(await page.locator("#runtime-mode").innerText(), /Simulated/);
    const tabs = ["main", "demo", "audio-vision", "arducam", "visitor", "logs", "settings"];
    for (const [width, height] of [[1440, 900], [1024, 768], [768, 1024], [390, 844], [320, 768]]) {
      await page.setViewportSize({ width, height });
      for (const tab of tabs) {
        await page.locator(`[data-admin-tab="${tab}"]`).click();
        if (tab === "settings") await page.locator(".settings-panel details").evaluateAll(nodes => nodes.forEach(node => node.open = true));
        const dimensions = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth, small: [...document.querySelectorAll("button")].filter(node => node.getClientRects().length && node.getBoundingClientRect().height < 39).map(node => node.id || node.textContent), reduced: matchMedia("(prefers-reduced-motion: reduce)").matches }));
        assert.equal(dimensions.scroll, dimensions.width, `${tab} at ${width}: overflow`);
        assert.deepEqual(dimensions.small, [], `${tab}: small controls`);
        assert.equal(dimensions.reduced, true);
        const contrast = await page.evaluate(() => {
          const rgb = value => value.match(/[\d.]+/g).map(Number);
          const luminance = value => rgb(value).slice(0, 3).map(x => x / 255).map(x => x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4).reduce((sum, x, index) => sum + x * [0.2126, 0.7152, 0.0722][index], 0);
          const background = node => {
            for (let ancestor = node; ancestor; ancestor = ancestor.parentElement) {
              const color = getComputedStyle(ancestor).backgroundColor;
              const values = rgb(color);
              if (values.length === 3 || values[3] === 1) return color;
            }
            return "rgb(255,255,255)";
          };
          const failures = [];
          let checks = 0;
          for (const node of document.querySelectorAll("h1,h2,p,label,button,strong,dt,dd,.status-pill,.nav-label,.nav-symbol")) {
            if (!node.getClientRects().length || node.disabled || !node.textContent.trim()) continue;
            const style = getComputedStyle(node);
            const a = luminance(style.color), b = luminance(background(node));
            const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
            const size = parseFloat(style.fontSize);
            const large = size >= 24 || size >= 18.66 && parseInt(style.fontWeight) >= 700;
            checks++;
            if (ratio < (large ? 3 : 4.5)) failures.push({ element: node.id || node.textContent.slice(0, 45), ratio });
          }
          return { checks, failures };
        });
        assert.deepEqual(contrast.failures, [], `${tab} at ${width}: text contrast`);
        report.contrastChecks += contrast.checks;
        report.layouts.push({ tab, width, height });
      }
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.locator('[data-admin-tab="main"]').click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(output, "overview.png"), fullPage: true });
    await page.screenshot({ path: path.join(output, "overview-viewport.png") });
    await page.locator("#sel-language").selectOption("fr");
    await page.evaluate(() => refreshStatus());
    assert.equal(await page.locator("#sel-language").inputValue(), "fr", "Polling overwrote unsaved experience");
    await page.locator("#btn-apply-experience").click();
    await page.locator("#btn-start-demo").click();
    await page.waitForFunction(() => document.querySelector("#metric-session").textContent === "Active");
    await page.locator("#btn-stop").click();
    await page.waitForFunction(() => document.querySelector("#metric-session").textContent === "Idle");
    await page.locator('[data-audio-route="speaker"]').click();
    await page.locator("#btn-test-audio").click();
    await page.locator("#audio-volume").fill("60");
    await page.waitForFunction(() => latestAudio.volume_percent === 60);
    await page.locator("#btn-override").click();
    await page.locator("#btn-clear-override").click();
    await page.locator("#btn-capture").click();
    await page.locator("#btn-ingest").click();
    await page.locator("#btn-eval").click();
    await page.locator('[data-sim="low_confidence"]').click();
    await page.locator("#btn-estop").click();
    await page.waitForFunction(() => document.querySelector("#issue-list").textContent.includes("Emergency stop"));
    await page.locator("#btn-clear-estop").click();
    await ready();
    await page.locator('[data-admin-tab="settings"]').click();
    await page.locator("#btn-save-config-top").click();
    await page.waitForFunction(() => !document.querySelector("#restart-badge").classList.contains("hidden"));
    await page.locator('[data-admin-tab="logs"]').click();
    await page.waitForFunction(() => latestLogs.snapshot_id === "synthetic-activity-1");
    await page.locator("#technical-logs > summary").click();
    assert.match(await page.locator("#activity-timeline").innerText(), /Who is in the Mona Lisa/);
    assert.match(await page.locator("#activity-timeline").innerText(), /multifunction button was pressed/);
    const rawLine = page.locator('.activity-entry[data-entry-id="question"]');
    await rawLine.locator("summary").click();
    assert.equal(await rawLine.locator("pre").innerText(), activitySnapshot.runtime[1].raw);
    await rawLine.locator("summary").focus();
    await page.evaluate(() => refreshLogs(true));
    assert.equal(await rawLine.locator("details").getAttribute("open"), "");
    assert.equal(await page.evaluate(() => document.activeElement.dataset.entryId), "question");
    report.actions.push("Readable entries match raw entries; unchanged refresh preserves focus and disclosure");
    await page.locator("#chk-pause-logs").check();
    assert.match(await page.locator("#log-freshness").innerText(), /Paused/);
    const pausedId = await page.evaluate(() => latestLogs.snapshot_id);
    activitySnapshot = {...activitySnapshot, snapshot_id: "synthetic-activity-2", runtime: [...activitySnapshot.runtime, activityEntry("fault", "Voice", "voice", "The answer could not be played aloud. Speech needs attention.", "tts_fallback_used: showing answer as text only", "warning")]};
    await page.evaluate(() => refreshLogs());
    assert.equal(await page.evaluate(() => latestLogs.snapshot_id), pausedId);
    const pausedRequests = activityRequests;
    await page.locator('[data-log-view="runtime"][data-log-format="raw"]').click();
    assert.equal(activityRequests, pausedRequests, "Paused format switch fetched fresh data");
    assert.match(await page.locator("#runtime-log-view").innerText(), /\[STT final\]/);
    assert.match(await page.locator("#activity-count").innerText(), /synthet/);
    await page.locator("#chk-pause-logs").uncheck();
    await page.waitForFunction(() => latestLogs.snapshot_id === "synthetic-activity-2");
    await page.locator("#log-severity").selectOption("warning");
    assert.equal(await page.locator(".activity-entry").count(), 1);
    assert.match(await page.locator("#runtime-log-view").innerText(), /tts_fallback_used/);
    assert.match(await page.locator("#log-warning-count").innerText(), /1/);
    await page.locator("#log-search").fill("synthetic");
    await page.locator("#btn-clear-log-filter").click();
    await page.locator('[data-log-view="runtime"][data-log-format="raw"]').click();
    await page.locator('[data-log-view="runtime"][data-log-format="human"]').click();
    await page.locator("#chk-follow-activity").uncheck();
    await page.locator("#activity-timeline").evaluate(node => node.scrollTop = 0);
    activitySnapshot = {...activitySnapshot, snapshot_id: "synthetic-activity-3", runtime: [...activitySnapshot.runtime, activityEntry("safe-markup", "User", "conversation", 'Question: “<img src=x onerror="window.activityInjected=true">”', '[STT final] <img src=x onerror="window.activityInjected=true">')]};
    await page.evaluate(() => refreshLogs(true));
    assert.equal(await page.locator("#activity-timeline img").count(), 0, "Log text was interpreted as HTML");
    assert.equal(await page.locator("#activity-timeline").evaluate(node => node.scrollTop), 0);
    const sharedBeforeFailure = await page.locator("#runtime-log-view").innerText();
    failActivity = true; expectedFailure = true;
    await page.evaluate(() => refreshLogs(true));
    assert.equal(await page.locator("#runtime-log-view").innerText(), sharedBeforeFailure);
    assert.match(await page.locator("#log-freshness").innerText(), /Offline/);
    assert.match(await page.locator("#activity-count").innerText(), /synthet/);
    failActivity = false; expectedFailure = false;
    await page.evaluate(() => refreshLogs(true));
    assert.match(await page.locator("#log-freshness").innerText(), /Synced/);
    report.failures.push("Activity and raw logs freeze together on pause/offline, recover together, safely render markup");
    await page.locator("#log-search").fill("Mona Lisa");
    await page.locator("#chk-pause-logs").check();
    await page.locator("#technical-logs > summary").click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({path: path.join(output, "readable-activity.png"), fullPage: true});
    await page.locator("#btn-clear-log-filter").click();
    const download = page.waitForEvent("download");
    await page.locator("#btn-export-logs").click();
    assert.match((await download).suggestedFilename(), /^atlas-logs-/);
    const exported = fs.readFileSync(await (await download).path(), "utf8");
    assert.match(exported, /Shared snapshot: synthetic-activity-3/);
    assert.match(exported, /READABLE ACTIVITY/);
    assert.match(exported, /\[STT final\]/);
    await page.locator('[data-admin-tab="main"]').click();
    expectedFailure = true;
    failedAction = true;
    await page.locator("#btn-test-audio").click();
    await page.waitForFunction(() => document.querySelector("#issue-list").textContent.includes("Action did not complete"));
    await page.waitForTimeout(4700);
    assert.match(await page.locator("#issue-list").innerText(), /Synthetic action failed/);
    report.failures.push("Action error persists after toast disappears");
    previewFailed = true;
    await page.waitForFunction(() => document.querySelector("#issue-list").textContent.includes("Artwork preview unavailable"));
    assert(await page.locator("#camera-empty").isVisible());
    await page.locator("#btn-clear-action-error").click();
    assert.match(await page.locator("#issue-list").innerText(), /Artwork preview unavailable/);
    report.failures.push("Dismiss does not clear a live camera fault");
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(output, "camera-fault.png"), fullPage: true });
    previewFailed = false; failedAction = false;
    await ready();
    assert(!(await page.locator("#camera-empty").isVisible()));
    report.failures.push("Camera automatically recovers without stale/broken image");
    state.health.components.stt = "Deepgram primary (unavailable); Whisper fallback (ready)";
    await page.evaluate(() => refreshHealth());
    assert.equal(await page.locator("#issue-board").getAttribute("data-severity"), "warning");
    report.failures.push("Working fallback is degraded, not fully failed");
    state = clone(initial);
    await page.evaluate(() => refreshHealth());
    state.audio.headset_available = false;
    await page.evaluate(() => refreshAudio());
    assert.match(await page.locator("#issue-list").innerText(), /Selected audio output unavailable/);
    state = clone(initial);
    await page.evaluate(() => refreshAudio());
    state.visitor.help_request = { status: "requested", request_id: "synthetic-help", context: "headset", requested_at: new Date().toISOString() };
    await page.evaluate(() => refreshVisitorStatus());
    assert.match(await page.locator("#issue-list").innerText(), /Visitor needs assistance/);
    await page.locator('[data-admin-tab="visitor"]').click();
    await page.locator("#btn-ack-help").click();
    await page.waitForFunction(() => !document.querySelector("#issue-list").textContent.includes("Visitor needs assistance"));
    report.failures.push("Help request surfaced and acknowledged");
    state.status.last_interaction = { source: "voice", state: "failed", response_failed: true, speech_ok: false, latency_ms: 1400 };
    await page.evaluate(() => refreshStatus());
    assert.match(await page.locator("#issue-list").innerText(), /Last response failed/);
    assert.match(await page.locator("#issue-list").innerText(), /Last spoken response was not played/);
    state.status.last_interaction = { source: "voice", state: "completed", response_failed: false, speech_ok: true, latency_ms: 900 };
    await page.evaluate(() => refreshStatus());
    assert.match(await page.locator("#vision-last-answer").innerText(), /spoken response completed/);
    assert.equal(await page.locator("#metric-latency").innerText(), "900 ms");
    report.failures.push("Voice/AI outcome failures clear on the next completed response");
    offline = true;
    await page.evaluate(() => Promise.all([refreshStatus(), refreshHealth(), refreshAudio(), refreshVisitorStatus()]));
    assert.match(await page.locator("#issue-list").innerText(), /Runtime connection lost/);
    assert.equal(await page.locator("#admin-state").innerText(), "Offline");
    await page.evaluate(() => { lastStatusSync = Date.now() - 12000; updateFreshness(); });
    assert.match(await page.locator("#last-sync").innerText(), /12s ago/);
    report.failures.push("Disconnected status cannot appear healthy; stale timestamp shown");
    offline = false; state = clone(initial);
    await page.evaluate(() => Promise.all([refreshStatus(), refreshHealth(), refreshAudio(), refreshVisitorStatus()]));
    await ready();
    expectedFailure = false;
    // Keyboard: skip link, navigation, real controls, and focus survives live polls.
    await page.locator('[data-admin-tab="main"]').focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Tab");
    assert(await page.evaluate(() => document.activeElement.matches("button")));
    auth = true;
    await page.evaluate(() => sessionStorage.clear());
    const requestsBefore = previewRequests;
    await page.reload();
    await page.waitForSelector("body.admin-locked");
    assert(!(await page.locator("#admin-workspace").isVisible()));
    assert.equal(previewRequests, requestsBefore, "Camera requested before unlock");
    expectedFailure = true;
    await page.locator("#inp-token").fill("wrong-synthetic-token");
    await page.locator("#btn-unlock").click();
    await page.waitForFunction(() => document.querySelector("#admin-unlock-message").textContent.includes("accepted"));
    await page.locator("#inp-token").fill("synthetic-test-token");
    await page.keyboard.press("Enter");
    await ready();
    await page.evaluate(() => sessionStorage.setItem("atlasAdminToken", "wrong-synthetic-token"));
    acceptedToken = "rotated-synthetic-token";
    await page.evaluate(() => refreshStatus());
    assert(await page.locator("#admin-unlock-gate").isVisible());
    assert.equal(await page.evaluate(() => adminUnlocked), false);
    assert.equal(await page.evaluate(() => refreshIntervals.length), 0);
    report.failures.push("Invalid token locks workspace and stops live loops");
    assert.deepEqual(report.errors, []);
    fs.writeFileSync(path.join(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify({ layouts: report.layouts.length, actions: report.actions.length, failureChecks: report.failures.length, contrastChecks: report.contrastChecks, unexpectedBrowserErrors: report.errors.length, output }));
    await context.close();
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
