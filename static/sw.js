/* Service Worker para Mindly - cache apenas de assets estáticos */
const CACHE_NAME = 'mindly-static-v8';
const PRECACHE = [
  '/static/style.css?v=calendar-modal2',
  '/static/app.js?v=calendar-modal2',
  '/static/manifest.webmanifest',
  '/static/icons/icon-192.svg',
  '/static/icons/icon-512.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Apenas GET pode ser cacheado
  if (req.method !== 'GET') return;

  // Não interceptar navegação HTML (evita páginas desatualizadas)
  const accepts = req.headers.get('accept') || '';
  if (req.mode === 'navigate' || accepts.includes('text/html')) {
    event.respondWith(fetch(req));
    return;
  }

  // Não cachear APIs dinâmicas
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(req));
    return;
  }

  // Apenas assets estáticos
  const isStatic = url.pathname.startsWith('/static/') || url.pathname.endsWith('/manifest.webmanifest');
  if (!isStatic) {
    // Pass-through com fallback ao cache se offline
    event.respondWith(
      fetch(req).catch(() => caches.match(req))
    );
    return;
  }

  // Cache-first para assets estáticos
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req).then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(req, copy)).catch(() => {});
        return resp;
      });
    })
  );
});
