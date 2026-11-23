/* 蓄电池热榜 · Service Worker
   静态资源 cache-first；data/ 下的内容 network-first，保证每天更新不被旧缓存挡住 */
const CACHE = "battery-hot-v5";
const SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./assets/css/style.css",
  "./assets/css/archive.css",
  "./assets/css/ai.css",
  "./assets/css/pwa.css",
  "./assets/js/app.js",
  "./assets/js/ai.js",
  "./assets/js/pwa.js",
  "./assets/img/icon.svg",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL).catch(() => null)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  const isData = url.pathname.includes("data/") || url.pathname.endsWith(".webmanifest") ||
    url.pathname.endsWith("index.html") || url.pathname.endsWith("sw.js") ||
    url.pathname.endsWith(".css");

  if (isData) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  e.respondWith(
    caches.match(req).then((hit) => {
      if (hit) {
        fetch(req).then((res) => caches.open(CACHE).then((c) => c.put(req, res))).catch(() => {});
        return hit;
      }
      return fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      });
    })
  );
});
