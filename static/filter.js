// Buscador y chips de las listas largas (empleo, ayudas, agenda). Mejora progresiva: la barra va oculta en el
// HTML y solo aparece aquí. Contrato: [data-filter-scope] contiene la barra [data-filter] (campo [data-filter-q]
// y botones [data-filter-tag][data-filter-group]), los elementos li[data-tags] y un aviso [data-filter-empty].
// Dentro de un grupo de chips basta con cumplir uno; entre grupos y con el texto hay que cumplirlos todos.
(function () {
  function plain(s) { return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
  var fmt;
  try {
    fmt = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Madrid", year: "numeric", month: "2-digit", day: "2-digit" });
  } catch (e) { fmt = null; }
  function iso(d) { return d.toISOString().slice(0, 10); }

  // Etiquetas que dependen del día de hoy (agenda): «today» y «weekend» (de viernes a domingo, como en el build).
  function dated(li) {
    if (!li.dataset.day) { return []; }
    var today = fmt ? fmt.format(new Date()) : iso(new Date());
    var noon = new Date(today + "T12:00:00Z"), wd = (noon.getUTCDay() + 6) % 7;  // 0 = lunes
    var fri = new Date(noon), sun = new Date(noon);
    fri.setUTCDate(noon.getUTCDate() + (wd >= 4 ? 0 : 4 - wd));
    sun.setUTCDate(noon.getUTCDate() + 6 - wd);
    var from = li.dataset.day, to = li.dataset.end || from, out = [];
    if (from <= today && to >= today) { out.push("today"); }
    if (from <= iso(sun) && to >= iso(fri)) { out.push("weekend"); }
    return out;
  }

  document.querySelectorAll("[data-filter-scope]").forEach(function (scope) {
    var bar = scope.querySelector("[data-filter]");
    var items = [].slice.call(scope.querySelectorAll("li[data-tags]"));
    if (!bar || !items.length) { return; }
    var q = bar.querySelector("[data-filter-q]"), chips = [].slice.call(bar.querySelectorAll("[data-filter-tag]"));
    var count = bar.querySelector("[data-filter-count]"), empty = scope.querySelector("[data-filter-empty]");
    var groups = [].slice.call(scope.querySelectorAll("details.group"));
    var text = items.map(function (li) { return plain(li.textContent); });

    function apply() {
      var words = plain(q.value).split(/\s+/).filter(Boolean), need = {};
      chips.forEach(function (c) {
        if (c.getAttribute("aria-pressed") === "true") {
          (need[c.dataset.filterGroup] = need[c.dataset.filterGroup] || []).push(c.dataset.filterTag);
        }
      });
      var wanted = Object.keys(need), active = words.length > 0 || wanted.length > 0, shown = 0;
      items.forEach(function (li, i) {
        var tags = (li.dataset.tags ? li.dataset.tags.split(" ") : []).concat(dated(li));
        var ok = !li.dataset.gone &&
          words.every(function (w) { return text[i].indexOf(w) >= 0; }) &&
          wanted.every(function (g) { return need[g].some(function (x) { return tags.indexOf(x) >= 0; }); });
        li.hidden = !ok;
        if (ok) { shown++; }
      });
      groups.forEach(function (d) {
        var n = d.querySelectorAll("li[data-tags]:not([hidden])").length, c = d.querySelector("[data-count]");
        d.hidden = n === 0;
        if (c) { c.textContent = "(" + n + ")"; }
        if (active) {  // con un filtro puesto, los grupos con resultados se abren; al quitarlo vuelven a como estaban
          if (!("was" in d.dataset)) { d.dataset.was = d.open ? "1" : ""; }
          d.open = n > 0;
        } else if ("was" in d.dataset) {
          d.open = d.dataset.was === "1";
          delete d.dataset.was;
        }
      });
      if (count) { count.hidden = !active; count.textContent = count.dataset.text.replace("{n}", shown); }
      if (empty) { empty.hidden = !active || shown > 0; }
    }

    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        c.setAttribute("aria-pressed", c.getAttribute("aria-pressed") === "true" ? "false" : "true");
        apply();
      });
    });
    q.addEventListener("input", apply);
    bar.hidden = false;
  });
})();
