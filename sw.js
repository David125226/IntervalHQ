const CACHE_NAME = 'intervalhq-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json',
  '/Boxing Triple Bell.mp3',
  '/ff_logo.PNG'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
