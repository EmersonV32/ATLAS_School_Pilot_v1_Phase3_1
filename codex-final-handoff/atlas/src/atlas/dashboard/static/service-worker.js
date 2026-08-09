/* Static shell only. API requests are deliberately never cached. */
"use strict";

const CACHE_NAME = "atlas-visitor-shell-v5";
const STATIC_ALLOWLIST = [
  "/",
  "/static/visitor.css?v=5",
  "/static/visitor.js?v=5",
  "/static/manifest.webmanifest",
  "/static/visitor/interests.json",
  "/static/visitor/assets/stories.svg",
  "/static/visitor/assets/technique.svg",
  "/static/visitor/assets/symbols.svg",
  "/static/visitor/assets/history.svg",
  "/static/visitor/assets/color-light.svg",
  "/static/visitor/assets/people-society.svg"
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
