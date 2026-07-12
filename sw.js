/* Enkel service worker: cacher app-skallet slik at appen kan legges til
   på hjem-skjermen og fungere uten nett. */
const CACHE = 'hjemme-v1';
const ASSETS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // Kun app-skallet (samme opphav) skal caches. La alt annet gå rett til nett:
  // Firebase-synk (REST + SSE) og Google Fonts er kryssopphav og må IKKE fanges,
  // ellers brytes sanntidsstrømmen (EventSource).
  if (url.origin !== self.location.origin) return;
  if ((req.headers.get('accept') || '').includes('text/event-stream')) return;
  e.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          return res;
        })
        .catch(() => cached);
    })
  );
});
