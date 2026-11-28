/* Hoola App Engine - locked by Hoola. v0.999.91 D8 wave 9: browser notifications on a React website on its own address,
   the same as her HTML website's worker. It shows a notification the visitor said yes to (her tap + the browser's own
   permission) and opens her website when it is tapped. No caching and no fetch handling: it never sits between the
   visitor and her pages. */
self.addEventListener('push', function (e) {
  var j = {};
  try { j = e.data ? e.data.json() : {}; } catch (er) { j = {body: e.data ? e.data.text() : ''}; }
  e.waitUntil(self.registration.showNotification(String(j.title || 'Update').slice(0, 80),
    {body: String(j.body || '').slice(0, 200), tag: j.tag || undefined, data: {url: j.url || '/'}}));
});
self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var url = new URL((e.notification.data && e.notification.data.url) || '/', self.location.origin).href;
  e.waitUntil(self.clients.matchAll({type: 'window', includeUncontrolled: true}).then(function (cs) {
    for (var i = 0; i < cs.length; i++) { if (cs[i].url.indexOf(self.location.origin) === 0 && 'focus' in cs[i]) return cs[i].focus(); }
    return self.clients.openWindow(url);
  }));
});
