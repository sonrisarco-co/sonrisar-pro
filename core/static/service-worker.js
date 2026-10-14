const CACHE_NAME = "sonrisar-static-v3";

const urlsToCache = [
  "/static/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || !new URL(event.request.url).pathname.startsWith("/static/")) return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
