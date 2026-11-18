// Selector de tema (auto → claro → oscuro, guardado en localStorage), chip de sección activo a la vista
// y contador de visitas anónimo del pie ([data-visits]: sin cookies ni almacenamiento).
(function () {
  var root = document.documentElement, btn = document.querySelector("[data-theme-toggle]"), order = ["auto", "light", "dark"];
  function get() { return root.dataset.theme || "auto"; }
  function set(t) {
    if (t === "auto") { delete root.dataset.theme; } else { root.dataset.theme = t; }
    try { t === "auto" ? localStorage.removeItem("theme") : localStorage.setItem("theme", t); } catch (e) {}
    if (btn) { btn.setAttribute("aria-label", btn.dataset[t]); btn.title = btn.dataset[t]; }
  }
  if (btn) {
    btn.hidden = false; set(get());
    btn.addEventListener("click", function () { set(order[(order.indexOf(get()) + 1) % 3]); });
  }
  // Centra el chip activo en su fila sin mover la página (así no se pierde el #ancla de la URL).
  var cur = document.querySelector(".sections [aria-current]"), ul = cur && cur.closest("ul");
  if (ul) {
    var a = cur.getBoundingClientRect(), u = ul.getBoundingClientRect();
    ul.scrollLeft += a.left - u.left - (u.width - a.width) / 2;
  }
  var vis = document.querySelector("[data-visits]");
  if (vis && window.fetch) {
    fetch(vis.dataset.visits, { method: "POST", mode: "cors", credentials: "omit" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || !d.total) return;
        var n = function (x) { return Number(x).toLocaleString(root.lang || undefined); };
        vis.textContent = vis.dataset.text.replace("{today}", n(d.today)).replace("{total}", n(d.total));
        vis.hidden = false;
      })
      .catch(function () {});
  }
})();
