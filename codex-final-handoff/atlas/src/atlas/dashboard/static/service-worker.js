/* Static shell only. API requests are deliberately never cached. */
"use strict";

const CACHE_NAME = "atlas-visitor-shell-v18";
const STATIC_ALLOWLIST = [
  "/",
  "/static/visitor.css?v=18",
  "/static/visitor.js?v=18",
  "/static/manifest.webmanifest",
  "/static/visitor/interests.json",
  "/static/visitor/assets/stories.svg",
  "/static/visitor/assets/technique.svg",
  "/static/visitor/assets/symbols.svg",
  "/static/visitor/assets/history.svg",
  "/static/visitor/assets/color-light.svg",
  "/static/visitor/assets/people-society.svg",
  "/static/visitor/assets/expertise-triptych.png",
  "/static/visitor/assets/atlas-logo-v2.png",
  "/static/visitor/assets/flag-en.svg",
  "/static/visitor/assets/flag-fr.svg",
  "/static/visitor/assets/flag-es.svg",
  "/static/visitor/assets/flag-it.svg",
  "/static/visitor/assets/flag-ar.svg",
  "/static/visitor/assets/flag-zh.svg",
  "/static/visitor/locales/en.json",
  "/static/visitor/locales/fr.json",
  "/static/visitor/locales/es.json",
  "/static/visitor/locales/it.json",
  "/static/visitor/locales/ar.json",
  "/static/visitor/locales/zh-Hant.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ALLOWLIST)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
  )));
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || !STATIC_ALLOWLIST.includes(`${url.pathname}${url.search}`)) return;
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
