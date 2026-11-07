// Selector de tema (auto → claro → oscuro, guardado en localStorage) y chip de sección activo a la vista.
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
})();
