/* VARANTRADAR service worker: anında güncelleme + network-first politika */
const CACHE = 'vr-static-v19';
const CORE = ['/', '/login', '/manifest.json', '/icons/icon-192.png', '/icons/icon-512.png'];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE).then((c) => c.addAll(CORE).catch(() => {})).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (e) => {
    const url = new URL(e.request.url);
    if (e.request.method !== 'GET' || url.origin !== self.location.origin) return;
    if (url.pathname.startsWith('/api/')) return; // Canlı veriler asla önbelleklenmez

    // Ağ öncelikli (Network First): Her zaman sunucudan en güncel dosyayı çek, yoksa önbellekten sun
    e.respondWith(
        fetch(e.request)
            .then((r) => {
                if (r && r.status === 200) {
                    const copy = r.clone();
                    caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
                }
                return r;
            })
            .catch(() => caches.match(e.request).then((m) => m || (e.request.mode === 'navigate' ? caches.match('/') : null)))
    );
});
