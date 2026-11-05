/* Prayogshala offline cache (v0.415): the engine files cache-first, lab data network-first with the cached copy as fallback. */
var CACHE = 'prayog-0.458.0';
var CORE = ['index.html', 'lab.html', 'lab.css?v=0.458.0', 'kernels.js?v=0.458.0', 'lab3d.js?v=0.458.0', '/api/prayog/three.js'];
self.addEventListener('install', function (e) { e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(CORE); }).catch(function () {})); self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k.indexOf('prayog-') === 0 && k !== CACHE; }).map(function (k) { return caches.delete(k); })); }));
  self.clients.claim();
});
self.addEventListener('fetch', function (e) {
  var u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  var isData = u.pathname.indexOf('/api/prayog/labs') === 0;
  var isCore = u.pathname.indexOf('/static/prayog/') === 0 || u.pathname === '/api/prayog/three.js';
  if (!isData && !isCore) return;
  if (isData) {
    e.respondWith(fetch(e.request).then(function (r) { var c = r.clone(); if (r.ok) caches.open(CACHE).then(function (k) { k.put(e.request, c); }); return r; })
      .catch(function () { return caches.match(e.request); }));
    return;
  }
  e.respondWith(caches.match(e.request).then(function (hit) {
    return hit || fetch(e.request).then(function (r) { var c = r.clone(); if (r.ok) caches.open(CACHE).then(function (k) { k.put(e.request, c); }); return r; });
  }));
});
