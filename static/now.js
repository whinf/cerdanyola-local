// Lo que depende de «ahora» y el build (un par de veces al día) no puede saber: actos que ya han empezado o
// acabado, datos que llevan demasiado sin actualizarse y el turno de guardia en curso. Sin JS la página sigue
// siendo correcta; solo es menos fina.
(function () {
  var fmt;
  try {
    fmt = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Madrid", year: "numeric", month: "2-digit", day: "2-digit" });
  } catch (e) { return; }
  function day(d) { return fmt.format(d); }  // «2026-11-18» en hora de Madrid, esté donde esté el visitante

  function tick() {
    var now = new Date(), today = day(now);
    // Actos: lo acabado se esconde y lo de hoy que ya ha empezado se marca.
    document.querySelectorAll("li[data-end]").forEach(function (li) {
      if (li.dataset.end < today) { li.dataset.gone = "1"; li.hidden = true; return; }
      var s = li.dataset.start && new Date(li.dataset.start);
      if (s && s <= now && day(s) === today) {
        li.classList.add("started");
        var tag = li.querySelector(".on");
        if (tag) { tag.hidden = false; }
      }
    });
    // «Próximas actividades» de la portada: siempre las n primeras que aún no han empezado.
    document.querySelectorAll("ul[data-upcoming]").forEach(function (ul) {
      var want = +ul.dataset.upcoming, shown = 0;
      ul.querySelectorAll("li").forEach(function (li) {
        li.hidden = !!li.dataset.gone || li.classList.contains("started") || shown >= want;
        if (!li.hidden) { shown++; }
      });
    });
    // Franja «hoy» de la portada: previsión del día que es y actos de hoy que aún no han empezado.
    document.querySelectorAll("[data-wx]").forEach(function (a) {
      var t = JSON.parse(a.dataset.wx)[today], span = a.querySelector("span");
      a.parentNode.hidden = !t;
      if (t && span) { span.textContent = a.dataset.text.replace("{t}", t); }
    });
    document.querySelectorAll("[data-today-events]").forEach(function (a) {
      var starts = JSON.parse(a.dataset.todayEvents)[today] || [], span = a.querySelector("span");
      var n = starts.filter(function (s) { return !s || new Date(s) > now; }).length;
      if (span) { span.textContent = a.dataset[n < 2 ? "t" + n : "tn"].replace("{n}", n); }
    });
    // Frescura: el aviso aparece cuando la fuente supera su margen, aunque no haya habido build.
    document.querySelectorAll("[data-fetched]").forEach(function (p) {
      var warn = p.querySelector(".stale"), age = (now - new Date(p.dataset.fetched)) / 36e5;
      if (warn && age === age) { warn.hidden = !(age > +p.dataset.maxH); }
    });
    // Turnos (farmacias de guardia): [data-from][data-to] en ISO; el que contiene «ahora» queda marcado.
    document.querySelectorAll("[data-from][data-to]").forEach(function (el) {
      var from = new Date(el.dataset.from), to = new Date(el.dataset.to);
      el.classList.toggle("now", from <= now && now < to);
      if (el.hasAttribute("data-hide-past")) { el.hidden = to <= now; }
    });
    // Si el build es tan viejo que ya no queda ningún turno por delante, sale el aviso con el enlace oficial.
    document.querySelectorAll("[data-shifts]").forEach(function (ul) {
      var empty = ul.parentNode.querySelector("[data-shifts-empty]");
      if (empty) { empty.hidden = !!ul.querySelector("li.now"); }
    });
    document.querySelectorAll("[data-shift-chip]").forEach(function (a) {
      var span = a.querySelector("span"), cur = JSON.parse(a.dataset.shiftChip).filter(function (s) {
        return new Date(s.from) <= now && now < new Date(s.to);
      })[0];
      if (span) { span.textContent = cur ? a.dataset.text.replace("{n}", cur.name) : a.dataset.none; }
    });
  }

  tick();
  setInterval(tick, 60000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) { tick(); } });
})();
