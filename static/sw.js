const CACHE_VERSION = 'haccp-v1';
const STATIC_ASSETS = [
  '/',
  '/hub.html',
  '/taches.html',
  '/etiquettes.html',
  '/reception.html',
  '/ouverture.html',
  '/admin.html',
  '/index.html',
  '/static/css/reset.css',
  '/static/css/tokens.css',
  '/static/css/base.css',
  '/static/css/components.css',
  '/static/css/layouts.css',
  '/static/css/style.css',
  '/static/css/pages/hub.css',
  '/static/css/pages/taches.css',
  '/static/css/pages/etiquettes.css',
  '/static/css/pages/reception.css',
  '/static/css/pages/ouverture.css',
  '/static/css/pages/admin.css',
  '/static/js/hub.js',
  '/static/js/taches.js',
  '/static/js/etiquettes.js',
  '/static/js/reception.js',
  '/static/js/ouverture.js',
  '/static/js/dashboard.js',
  '/static/js/charts.js',
  '/static/manifest.json',
];

const CACHE_NAME = `haccp-static-${CACHE_VERSION}`;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith('haccp-static-') && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') {
    return;
  }

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
  } else if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request));
  } else if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(staleWhileRevalidate(request));
  } else {
    event.respondWith(cacheFirst(request));
  }
});

function isStaticAsset(pathname) {
  return /\.(css|js|woff2?|ttf|eot|ico|png|jpg|jpeg|webp|svg|json)$/.test(pathname);
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Offline', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: 'Offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const networkPromise = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => null);
  return cached || networkPromise;
}
