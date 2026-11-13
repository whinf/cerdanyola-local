// Instalación como app (PWA): registra el service worker y muestra «Instala la app» solo donde se puede instalar
// (Android/Chrome/Edge con beforeinstallprompt; en iPhone/iPad, instrucciones de «Añadir a pantalla de inicio»).
(function () {
  var me = document.currentScript, sw = (me && me.dataset.sw) || "/sw.js";
  if ("serviceWorker" in navigator) { navigator.serviceWorker.register(sw).catch(function () {}); }
  var blocks = document.querySelectorAll("[data-install]");
  if (!blocks.length || window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true) { return; }
  var ios = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var deferred = null;
  function show(mode) { blocks.forEach(function (b) { b.hidden = false; b.dataset.mode = mode; }); }
  blocks.forEach(function (b) {
    var btn = b.querySelector("button"), help = b.querySelector("details");
    if (!btn) { return; }
    btn.addEventListener("click", function () {
      if (deferred) {
        deferred.prompt();
        deferred.userChoice.then(function () { deferred = null; }, function () {});
      } else if (help) {
        help.open = true;
      }
    });
  });
  window.addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); deferred = e; show("prompt"); });
  window.addEventListener("appinstalled", function () { blocks.forEach(function (b) { b.hidden = true; }); });
  if (ios) { show("ios"); }
})();
