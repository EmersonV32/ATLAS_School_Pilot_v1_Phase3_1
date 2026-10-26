/* Synthetic camera-offline visitor QA. Real static assets, no hardware/server/keys.
 * Run: node scripts/verify_visitor_camera_offline.cjs OUTPUT_DIR [CHROME_EXECUTABLE]
 */
"use strict";
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "../src/atlas/dashboard");
const output = path.resolve(process.argv[2]);
fs.mkdirSync(output, { recursive: true });
const state = { phase: "idle", step: "welcome", connection: "online" };
const readiness = {
  ready: true, blockers: [],
  items: ["unit", "headset", "connection", "camera", "content", "language", "safety", "profile"].map(id => ({
    id, label: id, status: id === "camera" ? "degraded" : "ready",
    detail: id === "camera" ? "Camera offline; voice available." : "Synthetic ready check.",
  })),
};
const report = { synthetic: true, viewport: "1024x768", reducedMotion: true, keyboardTransitions: 0, errors: [] };
let releaseStartup;
const startupGate = new Promise(resolve => { releaseStartup = resolve; });
let progressPending = 0;
let maxProgressPending = 0;
let lastActivation = 0;
report.navigationLatencyMs = [];

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.argv[3] ? { executablePath: process.argv[3] } : {}) });
  try {
    const context = await browser.newContext({ viewport: { width: 1024, height: 768 }, reducedMotion: "reduce", serviceWorkers: "block" });
    const page = await context.newPage();
    page.on("pageerror", error => report.errors.push(String(error)));
    page.on("console", message => { if (message.type() === "error") report.errors.push(message.text()); });
    await context.route("**/*", async route => {
      const request = route.request();
      const url = new URL(request.url());
      assert.equal(url.hostname, "atlas.test", "Unexpected external request");
      const json = value => route.fulfill({ contentType: "application/json", body: JSON.stringify(value) });
      if (url.pathname === "/") return route.fulfill({ contentType: "text/html", body: fs.readFileSync(path.join(root, "templates/index.html")) });
      if (url.pathname === "/favicon.ico") return route.fulfill({ status: 204 });
      if (url.pathname.startsWith("/static/")) {
        if (url.pathname === "/static/visitor/interests.json") await startupGate;
        const target = path.resolve(root, "." + url.pathname);
        assert(target.startsWith(path.join(root, "static") + path.sep));
        const mime = { ".css": "text/css", ".js": "text/javascript", ".json": "application/json", ".webp": "image/webp", ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json" };
        return route.fulfill({ contentType: mime[path.extname(target)] || "application/octet-stream", body: fs.readFileSync(target) });
      }
      if (url.pathname === "/api/visitor/bootstrap") {
        assert.equal(url.searchParams.get("include_readiness"), "false");
        await startupGate;
        return json({ state, readiness, public_languages: ["en", "fr", "es", "it", "zh-Hant"], preview_languages: ["ar"], inactivity_timeout_seconds: 0 });
      }
      if (url.pathname === "/api/visitor/readiness") return json(readiness);
      if (url.pathname === "/api/visitor/onboarding/progress") {
        progressPending++;
        maxProgressPending = Math.max(maxProgressPending, progressPending);
        await new Promise(resolve => setTimeout(resolve, 500));
        state.step = request.postDataJSON().step;
        state.phase = "onboarding";
        progressPending--;
        return json({ state, readiness });
      }
      if (url.pathname === "/api/visitor/onboarding/start") {
        assert.equal(state.step, "privacy");
        assert.deepEqual(request.postDataJSON(), { greeting_name: null });
        state.phase = "in_use";
        return json({ state, readiness });
      }
      throw new Error(`Unexpected endpoint ${url.pathname}`);
    });
    await page.goto("http://atlas.test/");
    // Navigate only with Tab/Space/Enter, not programmatic click/focus.
    const activate = async selector => {
      await page.waitForFunction(() => !navigationInFlight);
      for (let attempt = 0; attempt < 90; attempt++) {
        if (await page.locator(selector).evaluate(node => node === document.activeElement)) {
          lastActivation = Date.now();
          await page.keyboard.press(selector.includes("input") ? "Space" : "Enter");
          report.keyboardTransitions++;
          return;
        }
        await page.keyboard.press("Tab");
        report.keyboardTransitions++;
      }
      throw new Error(`Not keyboard reachable: ${selector}`);
    };
    const checkScreen = async name => {
      await page.locator(`[data-screen="${name}"].is-active`).waitFor({ timeout: 1000 });
      if (name !== "in_use") {
        const latency = Date.now() - lastActivation;
        report.navigationLatencyMs.push(latency);
        assert(latency < 450, `${name}: screen waited for a slow progress response (${latency}ms)`);
      }
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${name}: horizontal overflow`);
      assert.equal(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches), true);
    };
    await activate("#screen-welcome [data-next]");
    await checkScreen("language");
    releaseStartup();
    await page.waitForFunction(() => document.querySelector("#connection-status").classList.contains("is-online"));
    await activate('input[name="language"][value="en"]');
    await activate("#btn-continue");
    for (const name of ["about", "expertise", "interests", "accessibility", "headset", "readiness"]) {
      await checkScreen(name);
      if (name === "readiness") {
        await page.waitForFunction(() => document.querySelector("#readiness-summary").classList.contains("is-ready"));
        assert.equal(await page.locator(".readiness-degraded").count(), 1);
        assert.equal(await page.locator("#readiness-blocker").isVisible(), false);
        await page.screenshot({ path: path.join(output, "visitor-camera-offline.png") });
      }
      await activate("#btn-continue");
    }
    await checkScreen("privacy");
    await activate("#btn-start-experience");
    await checkScreen("in_use");
    assert.equal(state.phase, "in_use");
    assert.equal(maxProgressPending, 1, "Progress saves must not overlap or reorder");
    report.maxProgressPending = maxProgressPending;
    assert.deepEqual(await context.cookies(), []);
    assert.deepEqual(await page.evaluate(async () => ({ local: localStorage.length, session: sessionStorage.length, databases: (await indexedDB.databases()).length })), { local: 0, session: 0, databases: 0 });
    assert.deepEqual(report.errors, []);
    await page.screenshot({ path: path.join(output, "visitor-camera-offline-started.png") });
    fs.writeFileSync(path.join(output, "visitor-camera-offline-report.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
