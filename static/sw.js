// Service worker de Cerdanyola Avui. Páginas: red primero (los datos cambian 4 veces al día) y, sin
// conexión, la copia guardada o /offline.html. /static/: caché primero y actualización en segundo plano.
// __BUILD__ lo sustituye src/render.py en cada build, así que cada despliegue estrena caché.
var CACHE = "cerdanyola-__BUILD__";
var PREFIX = new URL(self.registration.scope).pathname.replace(/\/$/, "");
var OFFLINE = PREFIX + "/offline.html";
var PRECACHE = ["/offline.html", "/static/style.css", "/static/fonts/inter-latin.var.woff2", "/static/favicon.svg",
  "/static/icon-192.png", "/static/icon-512.png"].map(function (p) { return PREFIX + p; });

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(PRECACHE); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (e) {
  var req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) { return; }  // el tablón (workers.dev) y el resto, intactos
  if (req.mode === "navigate") {
    e.respondWith(networkFirst(req));
  } else if (url.pathname.indexOf(PREFIX + "/static/") === 0) {
    e.respondWith(staleWhileRevalidate(req));
  }
});

function networkFirst(req) {
  return caches.open(CACHE).then(function (c) {
    return fetch(req).then(function (res) {
      if (res.ok) { c.put(req, res.clone()); }
      return res;
    }).catch(function () {
      return c.match(req, { ignoreSearch: true }).then(function (hit) { return hit || c.match(OFFLINE); });
    });
  });
}

function staleWhileRevalidate(req) {
  return caches.open(CACHE).then(function (c) {
    return c.match(req).then(function (hit) {
      var net = fetch(req).then(function (res) {
        if (res.ok) { c.put(req, res.clone()); }
        return res;
      }).catch(function () { return null; });
      return hit || net.then(function (res) { return res || Response.error(); });
    });
  });
}
