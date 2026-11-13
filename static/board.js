/* board.js — tauler veïnal: lista en vivo, filtros y formularios (publicar, responder, denunciar).
   Habla con el worker de Cloudflare (data-api). Nunca inserta HTML con datos de la API: solo textContent. */
(function () {
  "use strict";
  var root = document.getElementById("board");
  var i18nEl = document.getElementById("board-i18n");
  if (!root || !i18nEl || !root.dataset.api || !window.fetch) return;
  var S = JSON.parse(i18nEl.textContent);
  var API = root.dataset.api, LANG = root.dataset.lang, SITEKEY = root.dataset.sitekey;
  var LIMITS = { title: 80, body: 1000, name: 40, contact: 60, price: 20, reason: 200, message: 2000, email: 254 };
  var ICONS = { help: "handshake", give: "gift", deal: "tag" };
  var dateFmt = new Intl.DateTimeFormat(LANG, { day: "numeric", month: "long" });
  var current = "";

  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "text") e.textContent = attrs[k];
      else if (k === "class") e.className = attrs[k];
      else e.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return e;
  }
  function icon(name) {
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "i"); svg.setAttribute("aria-hidden", "true");
    var use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", "#i-" + name); svg.appendChild(use);
    return svg;
  }
  function fmt(key, vars) {
    return String(S[key] || key).replace(/\{(\w+)\}/g, function (_, k) { return vars && k in vars ? vars[k] : ""; });
  }

  // ----- lista -----
  function post(p) {
    var cat = ICONS[p.cat] ? p.cat : "help";
    var when = el("span", { class: "when" }, [icon(ICONS[cat]), S["cat_" + cat]]);
    if (p.price) when.appendChild(el("span", { class: "tier t0", text: " " + p.price }));
    if (p.lang && p.lang !== LANG) when.appendChild(el("span", { class: "tier t3", lang: p.lang, text: p.lang }));
    var li = el("li", { id: "p-" + p.id, class: "post", "data-cat": cat }, [
      when,
      el("span", { class: "what", text: p.title }),
      el("p", { class: "body", text: p.body })]);
    if (p.contact) {
      var show = el("button", { type: "button", class: "linkish", text: S.contact_show });
      var holder = el("p", { class: "contact" }, [show]);
      show.addEventListener("click", function () { holder.textContent = p.contact; });
      li.appendChild(holder);
    }
    li.appendChild(el("small", { class: "muted", text: (p.name || "") + " · " + fmt("posted", { d: dateFmt.format(new Date(p.created * 1000)) }) }));
    var reply = el("button", { type: "button", class: "linkish", text: S.reply });
    var report = el("button", { type: "button", class: "linkish muted", text: S.report });
    reply.addEventListener("click", function () { openDialog("reply", p); });
    report.addEventListener("click", function () { openDialog("report", p); });
    li.appendChild(el("p", { class: "actions" }, [reply, " · ", report]));
    return li;
  }
  function applyFilter() {
    var list = root.querySelector(".board-list"), any = false;
    if (!list) return;
    Array.prototype.forEach.call(list.children, function (li) {
      var show = !current || li.dataset.cat === current;
      li.hidden = !show; any = any || show;
    });
    list.hidden = !any;
    var empty = root.querySelector(".board-empty");
    if (!empty) { empty = el("p", { class: "board-empty", text: S.empty }); root.appendChild(empty); }
    empty.hidden = any;
  }
  function render(posts) {
    var list = root.querySelector(".board-list");
    var fresh = el("ul", { class: "events board-list" }, posts.map(post));
    if (list) list.replaceWith(fresh); else root.appendChild(fresh);
    var status = root.querySelector("[data-board-status]");
    if (status) status.hidden = true;
    applyFilter();
    if (location.hash && location.hash.indexOf("#p-") === 0) {
      var target = document.getElementById(location.hash.slice(1));
      if (target) target.scrollIntoView({ block: "center" });
    }
  }
  function load() {
    // Al llegar desde el correo de confirmación (#p-id) se salta la caché del navegador para ver el anuncio al momento.
    var bust = location.hash.indexOf("#p-") === 0 ? "&t=" + Date.now() : "";
    fetch(API + "/posts?lang=" + LANG + bust, { headers: { Accept: "application/json" } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { render(Array.isArray(j.posts) ? j.posts : []); })
      .catch(function () { /* se queda la lista estática y su nota */ });
  }

  // ----- filtros y botón de publicar -----
  var filters = document.querySelector(".board-filters");
  if (filters) filters.addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-cat]");
    if (!b) return;
    current = b.dataset.cat;
    Array.prototype.forEach.call(filters.querySelectorAll("button"), function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    applyFilter();
  });
  var newBtn = document.querySelector("[data-board-new]");
  if (newBtn) { newBtn.hidden = false; newBtn.addEventListener("click", function () { openDialog("new"); }); }

  // ----- formularios -----
  function field(name, label, type, opts) {
    opts = opts || {};
    var input;
    if (type === "textarea") input = el("textarea", { name: name, rows: opts.rows || 5 });
    else if (type === "select") {
      input = el("select", { name: name }, opts.options.map(function (o) { return el("option", { value: o[0], text: o[1] }); }));
    } else input = el("input", { name: name, type: type });
    if (LIMITS[name]) input.setAttribute("maxlength", LIMITS[name]);
    if (opts.min) input.setAttribute("minlength", opts.min);
    if (opts.required) input.required = true;
    var wrap = el("label", { class: opts.cls || "" }, [el("span", { text: label }), input]);
    return wrap;
  }
  function openDialog(kind, p) {
    var old = document.querySelector("dialog.board");
    if (old) old.remove();
    var form = el("form", { class: "board", method: "dialog" });
    var title = kind === "new" ? S.new : kind === "reply" ? S.reply_title : S.report_title;
    form.appendChild(el("h2", { text: title }));
    if (p) form.appendChild(el("p", { class: "muted", text: "«" + p.title + "»" }));
    if (kind === "new") {
      form.appendChild(field("cat", S.f_cat, "select", { options: S.cats.map(function (c) { return [c, S["cat_" + c]]; }) }));
      form.appendChild(field("title", S.f_title, "text", { required: true, min: 5 }));
      form.appendChild(field("body", S.f_body, "textarea", { required: true, min: 20 }));
      form.appendChild(field("price", S.f_price, "text", { cls: "price" }));
      form.appendChild(field("name", S.f_name, "text", { required: true, min: 2 }));
      form.appendChild(field("email", S.f_email, "email", { required: true }));
      form.appendChild(field("contact", S.f_contact, "text"));
      var consent = el("input", { type: "checkbox", name: "consent" }); consent.required = true;
      form.appendChild(el("label", { class: "check" }, [consent, el("span", { text: S.f_consent })]));
      var sel = form.querySelector("select[name=cat]"), priceRow = form.querySelector("label.price");
      var syncPrice = function () { priceRow.hidden = sel.value !== "deal"; };
      sel.addEventListener("change", syncPrice); syncPrice();
    } else if (kind === "reply") {
      form.appendChild(field("message", S.f_message, "textarea", { required: true, min: 20 }));
      form.appendChild(field("email", S.f_reply_email, "email", { required: true }));
    } else {
      form.appendChild(el("p", { class: "muted", text: S.report_hint }));
      form.appendChild(field("reason", S.f_reason, "textarea", { rows: 3 }));
    }
    var captcha = el("div", { class: "cf-turnstile" });
    form.appendChild(captcha);
    var msg = el("p", { class: "msg", role: "alert" });
    form.appendChild(msg);
    var send = el("button", { type: "submit", class: "donate", text: S.submit });
    var cancel = el("button", { type: "button", class: "linkish", text: S.cancel });
    form.appendChild(el("p", { class: "buttons" }, [send, " ", cancel]));
    var dlg = el("dialog", { class: "board card" }, [form]);
    document.body.appendChild(dlg);
    cancel.addEventListener("click", function () { dlg.close(); });
    dlg.addEventListener("close", function () { dlg.remove(); });
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");

    var widget = null;
    if (SITEKEY && window.turnstile) widget = turnstile.render(captcha, { sitekey: SITEKEY, language: LANG });

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      msg.textContent = "";
      var data = {};
      Array.prototype.forEach.call(form.elements, function (f) {
        if (!f.name) return;
        data[f.name] = f.type === "checkbox" ? f.checked : f.value.trim();
      });
      if (kind !== "new" || data.cat !== "deal") delete data.price;
      if (p) data.id = p.id;
      data.lang = LANG;
      data.turnstile = widget !== null && window.turnstile ? (turnstile.getResponse(widget) || "") : "";
      send.disabled = true;
      var path = kind === "new" ? "/posts" : kind === "reply" ? "/reply" : "/report";
      fetch(API + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          if (res.ok) {
            form.textContent = "";
            form.appendChild(el("p", { text: kind === "new" ? S.sent : kind === "reply" ? S.reply_sent : S.report_sent }));
            var close = el("button", { type: "button", class: "donate", text: S.cancel.replace(/.*/, "OK") });
            close.addEventListener("click", function () { dlg.close(); });
            form.appendChild(el("p", { class: "buttons" }, [close]));
          } else {
            msg.textContent = S["err_" + (res.j && res.j.error)] || S.err_generic;
            send.disabled = false;
            if (widget !== null && window.turnstile) turnstile.reset(widget);
          }
        })
        .catch(function () { msg.textContent = S.err_network; send.disabled = false; });
    });
  }

  load();
})();
