/* VARANTRADAR minimal service worker: uygulama kurulumu + temel statik onbellek. */
const CACHE = 'vr-static-v1';
const CORE = ['/', '/login', '/manifest.json', '/icons/icon-192.png', '/icons/icon-512.png'];

self.addEventListener('install', (e) => {
    e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE).catch(() => {})).then(() => self.skipWaiting()));
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
    if (url.pathname.startsWith('/api/')) return; // canli veri hic onbelleklenmez

    // Sayfa gezinmeleri: once ag, olmazsa onbellek (cevrimdisi acilis)
    if (e.request.mode === 'navigate') {
        e.respondWith(
            fetch(e.request).then((r) => {
                const copy = r.clone();
                caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
                return r;
            }).catch(() => caches.match(e.request).then((m) => m || caches.match('/')))
        );
        return;
    }

    // Statik dosyalar: once onbellek
    e.respondWith(
        caches.match(e.request).then((m) => m || fetch(e.request).then((r) => {
            const copy = r.clone();
            caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
            return r;
        }))
    );
});
