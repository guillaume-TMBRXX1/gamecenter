/* Snapline GameCenter — service worker (bloc 2, étape 6) : rappels avant le coup d'envoi (Web Push).
   Pas de cache hors ligne : il affiche les notifications envoyées par le serveur et ouvre le match quand on les touche. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('push', e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data ? e.data.text() : '' }; }
  e.waitUntil(self.registration.showNotification(d.title || 'Snapline', {
    body: d.body || '', tag: d.tag || undefined, renotify: !!d.tag, icon: '/icons/icon-192.png', badge: '/icons/icon-192.png',
    data: { url: d.url || '/' } }));
});
self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || '/', self.location.origin);
  const watch = url.searchParams.get('watch');
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    for (const c of list) {
      if (new URL(c.url).origin === self.location.origin && 'focus' in c) {
        if (watch) c.postMessage({ watch });
        return c.focus();
      }
    }
    return self.clients.openWindow(url.href);
  }));
});
