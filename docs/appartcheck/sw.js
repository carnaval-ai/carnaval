/* =====================================================================
   AppartCheck - Service Worker
   Enables 100% offline functionality using Stale-While-Revalidate.
   ===================================================================== */

const CACHE_NAME = 'appartcheck-v2';
const ASSETS = [
  './',
  './index.html',
  './app.css',
  './app.js',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './favicon.png'
];

// Install Event - Pre-cache all static resources
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Pre-caching offline assets...');
        return cache.addAll(ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate Event - Clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheKeys => {
      return Promise.all(
        cacheKeys.map(key => {
          if (key !== CACHE_NAME) {
            console.log('[Service Worker] Removing old cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event - Stale-While-Revalidate caching strategy
self.addEventListener('fetch', event => {
  // Only handle GET requests and local files
  if (event.request.method !== 'GET') return;
  
  const url = new URL(event.request.url);
  
  // Only cache files from our own origin
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      // Return cached response immediately if exists
      const fetchPromise = fetch(event.request).then(networkResponse => {
        // Update cache in background
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      }).catch(err => {
        console.log('[Service Worker] Network request failed, using cache:', err);
      });
      
      return cachedResponse || fetchPromise;
    })
  );
});
