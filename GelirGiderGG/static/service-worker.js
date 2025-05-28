const CACHE_NAME = 'gelirgidergg-cache-v1';
const urlsToCache = [
  '/',
  '/static/index.html',
  '/static/manifest.json',
  // Diğer önemli dosyalar eklenebilir
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        return response || fetch(event.request);
      })
  );
}); 