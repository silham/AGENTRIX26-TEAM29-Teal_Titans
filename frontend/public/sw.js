/**
 * HelpLK service worker.
 *
 * Scope is deliberately narrow. This exists to make the app installable and to
 * show something useful when a citizen opens it with no signal — NOT to be a
 * general caching layer.
 *
 * What it never touches, and why:
 *   - Cross-origin requests. The FastAPI backend is a separate origin; the
 *     agent run is an SSE stream, and buffering that through a worker would
 *     stall the live progress screen.
 *   - Anything that is not a GET. No mutation is ever replayed or cached.
 *   - text/event-stream, even same-origin, in case the API is ever proxied
 *     under this domain.
 *
 * Everything it does not handle is left entirely alone: no respondWith call,
 * so the browser performs its normal fetch.
 */
const VERSION = "helplk-v1";
const SHELL_CACHE = `${VERSION}-shell`;
const OFFLINE_URL = "/offline.html";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll([OFFLINE_URL]))
      // Take over immediately rather than waiting for every tab to close;
      // otherwise an updated worker sits idle until the citizen fully quits.
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

function isCacheableStatic(url) {
  // Next's build output is content-hashed, so a hit is always the right file.
  // Icons are stable and small.
  return (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.startsWith("/icon-") ||
    url.pathname === "/apple-icon.png" ||
    url.pathname === "/icon.png"
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;

  if (request.method !== "GET") return;
  if (request.headers.get("accept")?.includes("text/event-stream")) return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Never serve a stale page: a government procedure that changed must not be
  // read from cache. Network first, cache only as an offline fallback.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(async () => {
          return (
            (await caches.match(request)) ||
            (await caches.match(OFFLINE_URL)) ||
            Response.error()
          );
        }),
    );
    return;
  }

  if (isCacheableStatic(url)) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((response) => {
            if (response.ok) {
              const copy = response.clone();
              caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
            }
            return response;
          }),
      ),
    );
  }
});
