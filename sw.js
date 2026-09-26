// Offline cache: the app makes no network calls, so cache-first is safe.
const CACHE = "invarianttap-v5";
const FILES = ["./", "./index.html", "./sentinel_dot.js", "./manifest.webmanifest", "./icon-180.png", "./icon-192.png", "./icon-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).catch(() => {})); self.skipWaiting(); });
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks =>
  Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(r => r || fetch(e.request))));
