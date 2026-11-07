/* Enkel service worker: cacher app-skallet slik at appen kan legges til
   på hjem-skjermen og fungere uten nett. */
const CACHE = 'hjemme-v9';
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

  const accept = req.headers.get('accept') || '';
  const isHTML = req.mode === 'navigate' || accept.includes('text/html');

  if (isHTML) {
    // HTML: nett først, så nyeste app-versjon vises straks når du er online.
    // Faller tilbake til cache når du er offline.
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match(req).then((c) => c || caches.match('./index.html')))
    );
    return;
  }

  // Øvrige app-filer (ikoner, manifest): cache først for fart/offline.
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

/* ---------- Push-varsler (medisiner) ---------- */
self.addEventListener('push', (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) {
    try { d = { title: 'Hjemmetavla', body: e.data ? e.data.text() : '' }; } catch (__) { d = {}; }
  }
  const title = d.title || '💊 Medisin';
  const opts = {
    body: d.body || 'Tid for medisinen',
    tag: d.tag || 'hjemmetavla-med',
    renotify: true,
    icon: './icon-192.png',
    badge: './icon-192.png',
    data: { url: d.url || './index.html', slot: d.slot || null },
    requireInteraction: false,
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const target = (e.notification.data && e.notification.data.url) || './index.html';
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const c of list) {
        // Fokuser et åpent vindu hvis vi har ett
        if ('focus' in c) { c.focus(); if ('navigate' in c) c.navigate(target).catch(() => {}); return; }
      }
      if (self.clients.openWindow) return self.clients.openWindow(target);
    })
  );
});
