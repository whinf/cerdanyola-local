"""Genera el sitio estático de Cerdanyola a partir de los datos en caché."""
import hashlib
import json
import re
import shutil
from datetime import date, datetime, timedelta
from html import escape as esc
from pathlib import Path
from urllib.parse import urlparse

import i18n
import sources
import tz
from i18n import LANGS, t

ROOT = Path(__file__).resolve().parent.parent
RODALIES = "https://rodalies.gencat.cat/ca/estat_servei/"

# Qué cuenta como fiesta: por categoría o por palabras del título (ca/es/en)
FESTIVE_CATS = {"Festes populars", "Música", "Festivals", "Hostalaria", "Fires i mercats", "Nadal"}
FESTIVE_WORDS = re.compile(
    r"\b(fest[ae]s?|fiestas?|festival\w*|\w*halloween|castanyad\w*|carnaval|carnestoltes|revetlla|verbena|"
    r"sant joan|concerts?|dj|disco\w*|balls?|baile|cercavila|correfoc|gegants|castellers?|castellera|"
    r"sardan\w*|fira|jam|karaoke|tribut\w*|xou|show|terror|cap d'any|nochevieja|tardeo|rumba|flamenc\w*|"
    r"corretapes|vermut|party|música en viu|en directe|en directo)\b", re.I)
RAINY = ("rain", "sleet", "snow", "thunder", "showers")
KIDS_WORDS = re.compile(r"\b(infantil\w*|famíli\w*|familiar\w*|nens|niños|kids|contacontes|cuentacuentos)\b", re.I)
AUDIENCES = ("people", "business", "entities")
LEVELS = ("LOCAL", "AUTONOMICA", "ESTADO")
BDNS_CALL = "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias/{}"
BIG = 1_000_000  # «gran inversión»: contratos de 1 M€ o más, sin IVA
INVEST_DAYS = 365  # grandes inversiones y anuncios con novedades en este tiempo
COMPANY_DAYS = 90
FEED_DAYS = 60
SOON_PHASES = ("Alerta futura", "Consulta preliminar del mercat", "Anunci previ")
PHASE_TIER = {"Anunci de licitació": "t0", "Alerta futura": "t1", "Consulta preliminar del mercat": "t1",
              "Anunci previ": "t1", "Expedient en avaluació": "t1"}  # el resto, gris


def festive(e):
    return e.get("category") in FESTIVE_CATS or bool(FESTIVE_WORDS.search(e["title"]))


def for_kids(e):
    return e.get("category") == "Infància" or bool(KIDS_WORDS.search(e["title"]))


def aid_level(a):
    return a["level"] if a.get("level") in LEVELS else "AUTONOMICA"


def fmt_dt(iso):
    if not iso:
        return ""
    d = tz.to_madrid(tz.parse_iso(iso))
    return f"{d.day:02d}/{d.month:02d}/{d.year} {d.hour:02d}:{d.minute:02d}"


def osm(lat, lon):
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}"


class Site:
    def __init__(self, cfg, data, out_dir, now):
        self.cfg = cfg
        self.data = data  # {fuente: {"fetched": iso, "data": ...}}
        self.out = Path(out_dir)
        self.now = now
        self.base_url = cfg["site_url"].rstrip("/")
        self.prefix = urlparse(self.base_url).path.rstrip("/")
        self.name = cfg["site_name"]

    def get(self, key):
        return (self.data.get(key) or {}).get("data")

    # ---------- URLs ----------
    def path(self, lang, kind):
        return f"/{lang}/" if kind == "home" else f"/{lang}/{t(lang, 'slug_' + kind)}/"

    def href(self, path):
        return self.prefix + path

    def absolute(self, path):
        return self.base_url + path

    def write(self, path, text):
        target = self.out / path.lstrip("/")
        if path.endswith("/"):
            target = target / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    # ---------- plantilla ----------
    def layout(self, lang, kind, title, desc, body, jsonld=None, noindex=False, head=""):
        alts = "".join(f'<link rel="alternate" hreflang="{lg}" href="{self.absolute(self.path(lg, kind))}">'
                       for lg in LANGS)
        x_default = self.absolute("/") if kind == "home" else self.absolute(self.path("ca", kind))
        ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>'
                     for j in (jsonld or []))
        switch = " · ".join(
            f'<a href="{self.href(self.path(lg, kind))}" hreflang="{lg}" lang="{lg}"'
            f'{" aria-current=\"true\"" if lg == lang else ""}>{t(lg, "lang_name")}</a>' for lg in LANGS)
        nav = " · ".join(f'<a href="{self.href(self.path(lang, k))}">{t(lang, k + "_title" if k != "home" else "home")}</a>'
                         for k in ("home", "agenda", "leisure", "aids", "jobs", "invest", "directory"))
        links = " · ".join([f'<a href="{self.href(self.path(lang, "emergency"))}">🆘 112</a>'] + [
            f'<a href="{self.href(self.path(lang, k))}">{t(lang, k)}</a>' for k in ("about", "legal", "privacy")] + [f'<a href="https://onestudioman.horaverda.es/{lang}/">{t(lang, "studio")}</a>'])
        donate = (f' · <a class="donate" href="{esc(self.cfg["donate_url"])}" rel="noopener">♥</a>'
                  if self.cfg.get("donate_url") else "")
        updated = max((v.get("fetched") or "" for v in self.data.values()), default="")
        return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{'<meta name="robots" content="noindex">' if noindex else ''}
<link rel="canonical" href="{self.absolute(self.path(lang, kind))}">
{alts}<link rel="alternate" hreflang="x-default" href="{x_default}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{self.absolute(self.path(lang, kind))}">
<meta property="og:locale" content="{t(lang, 'locale')}">
<meta property="og:site_name" content="{esc(self.name)}">
<meta name="theme-color" content="#0b6b3a">
<link rel="icon" href="{self.href('/static/favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{self.href('/static/style.css')}">
{head}{ld}
</head>
<body>
<a class="skip" href="#main">{t(lang, "skip")}</a>
<header class="top"><div class="wrap">
<a class="brand" href="{self.href(self.path(lang, 'home'))}"><img src="{self.href('/static/favicon.svg')}" alt="" width="28" height="28"> {esc(self.name)}</a>
<nav class="langs" aria-label="{t(lang, 'language')}">{switch}</nav>
<nav class="sections">{nav}</nav>
</div></header>
<main id="main" class="wrap">
{body}
</main>
<footer class="foot"><div class="wrap">
<p>{t(lang, "source_line", t=fmt_dt(updated))}</p>
<p>{links}{donate}</p>
</div></footer>
</body>
</html>
"""

    # ---------- bloques ----------
    def weather(self, lang):
        w = self.get("weather")
        if not w or not w.get("days"):
            return ""
        now = w.get("now") or {}
        icon, text = i18n.sky(lang, now.get("symbol"))
        rows = []
        for d in w["days"]:
            day = date.fromisoformat(d["date"])
            di, dt_ = i18n.sky(lang, d["symbol"])
            rows.append(f'<tr><td>{i18n.fmt_date(lang, day, weekday=True).split(",")[0]} {day.day}</td>'
                        f'<td><span role="img" aria-label="{esc(dt_)}" title="{esc(dt_)}">{di}</span> <span class="skytxt" aria-hidden="true">{esc(dt_)}</span></td>'
                        f'<td class="num">{d["tmin"]}°</td><td class="num">{d["tmax"]}°</td>'
                        f'<td class="num">{i18n.fmt_num(lang, d["rain_mm"], 1)}</td>'
                        f'<td class="num">{d["wind_kmh"]}</td></tr>')
        hero = ""
        if now.get("temp") is not None:
            hero = (f'<p class="hero"><span class="big" aria-hidden="true">{icon}</span>'
                    f'<span><span class="k">{t(lang, "now")}</span> <strong class="v">{round(now["temp"])}°C</strong> '
                    f'{esc(text)} · {t(lang, "wind")} {now["wind_kmh"]} km/h</span></p>')
        return (f'<section><h2>{t(lang, "weather_title")}</h2>{hero}<table class="recent weather"><thead><tr>'
                f'<th>{t(lang, "th_day")}</th><th>{t(lang, "th_sky")}</th><th class="num">{t(lang, "th_min")}</th>'
                f'<th class="num">{t(lang, "th_max")}</th><th class="num">{t(lang, "th_rain")} (mm)</th>'
                f'<th class="num">{t(lang, "th_wind")} (km/h)</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
                f'<p class="note">{t(lang, "weather_note")}</p></section>')

    def light(self, lang):
        li = self.get("light")
        if not li or li.get("date") != self.now.date().isoformat() or "3" not in li.get("cheapest", {}):
            return ""
        one = li["cheapest"].get("1", li["cheapest"]["3"])
        price = i18n.fmt_num(lang, one["avg_eur_kwh"], 4)
        site = li.get("site") or ""
        home = site.rstrip("/") + f"/{'ca' if lang == 'ca' else lang}/" if site else ""
        more = f'<p><a href="{esc(home)}">{t(lang, "light_more")} →</a></p>' if home else ""
        return (f'<section class="light"><h2>⚡ {t(lang, "light_title")}</h2>'
                f'<p>{t(lang, "light_text", w=li["cheapest"]["3"]["label"], h=one["label"], p=price)}</p>'
                f'<p class="note">{t(lang, "light_tip")}</p>{more}</section>')

    def air(self, lang):
        air = self.get("air")
        if not air:
            return ""
        rows = []
        for station in sorted(air):
            cells = []
            for pol in ("NO2", "O3", "PM10", "PM2.5"):
                m = air[station].get(pol)
                if not m:
                    cells.append('<td class="num">–</td>')
                    continue
                lvl = i18n.aq_level(pol, m["value"])
                cells.append(f'<td class="num">{round(m["value"])} <span class="aq a{lvl}">{t(lang, f"aq_{lvl}")}</span></td>')
            latest = max(air[station].values(), key=lambda m: (m["date"], m["hour"]))
            when = t(lang, "air_at", date=i18n.fmt_date(lang, date.fromisoformat(latest["date"]), weekday=False),
                     h=f'{latest["hour"]:02d}')
            rows.append(f'<tr><td>{esc(station)}<br><small class="muted">{when}</small></td>{"".join(cells)}</tr>')
        return (f'<section><h2>{t(lang, "air_title")}</h2><div class="scroll-x"><table class="recent"><thead><tr>'
                f'<th>{t(lang, "station")}</th><th class="num">NO₂</th><th class="num">O₃</th>'
                f'<th class="num">PM10</th><th class="num">PM2,5</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
                f'<p class="note">{t(lang, "air_note")} µg/m³.</p></section>')

    def transport(self, lang):
        alerts = self.get("alerts")
        if alerts is None:
            return ""
        items = "".join(
            f'<li><span class="line">{" ".join(esc(x) for x in a["lines"])}</span> '
            f'{esc(a["text"].get(lang) or a["text"].get("ca") or a["text"].get("es") or next(iter(a["text"].values())))}</li>'
            for a in alerts[:6])
        body = f'<ul class="alerts">{items}</ul>' if items else f'<p>{t(lang, "transport_none")}</p>'
        return (f'<section><h2>🚆 {t(lang, "transport_title")}</h2>{body}'
                f'<p><a href="{RODALIES}">{t(lang, "transport_more")} →</a></p></section>')

    def event_item(self, lang, e):
        d = date.fromisoformat(e["start"])
        when = i18n.fmt_date(lang, d) + (f' · {esc(e["time"])}' if e.get("time") else "")
        if e.get("end") and e["end"] != e["start"]:
            when += f' → {i18n.fmt_date(lang, date.fromisoformat(e["end"]), weekday=False)}'
        title = esc(e["title"])
        title = f'<a href="{esc(e["url"])}">{title}</a>' if e.get("url") else title
        if festive(e):
            title = f'<span role="img" aria-label="{t(lang, "festive")}">🎉</span> {title}'
        if for_kids(e):
            title = f'<span role="img" aria-label="{t(lang, "kids")}" title="{t(lang, "kids")}">🧒</span> {title}'
        meta = " · ".join(x for x in (esc(i18n.agenda_cat(lang, e.get("category", ""))), esc(e.get("place", "")),
                                       t(lang, "free") if e.get("free") else "", t(lang, "src_" + e["source"])) if x)
        return f'<li><span class="when">{when}</span><span class="what">{title}</span><small class="muted">{meta}</small></li>'

    def events_split(self):
        """(próximos, en curso): los actos de varios días que ya han empezado van aparte."""
        today = self.now.date().isoformat()
        events = (self.get("agenda") or {}).get("events", [])
        return [e for e in events if e["start"] >= today], [e for e in events if e["start"] < today]

    def agenda_preview(self, lang, n=6):
        ag = self.get("agenda")
        if ag is None:
            return ""
        events = self.events_split()[0][:n]
        body = (f'<ul class="events">{"".join(self.event_item(lang, e) for e in events)}</ul>'
                if events else f'<p>{t(lang, "agenda_empty")}</p>')
        return (f'<section><h2>{t(lang, "agenda_next")}</h2>{body}'
                f'<p><a href="{self.href(self.path(lang, "agenda"))}">{t(lang, "agenda_all")} →</a></p></section>')

    def weekend(self, lang):
        """Actos que empiezan entre el viernes y el domingo (este, si ya estamos en fin de semana)."""
        today = self.now.date()
        fri = today if today.weekday() >= 4 else today + timedelta(days=4 - today.weekday())
        sun = fri + timedelta(days=6 - fri.weekday())
        events = [e for e in self.events_split()[0] if fri.isoformat() <= e["start"] <= sun.isoformat()]
        body = (f'<ul class="events">{"".join(self.event_item(lang, e) for e in events)}</ul>'
                if events else f'<p>{t(lang, "weekend_empty")}</p>')
        return f'<section id="weekend"><h2>{t(lang, "weekend_title")}</h2>{body}</section>'

    def aids_open(self):
        """[(estado, fecha, ayuda)] que aún se pueden pedir: primero las de plazo conocido, por fecha de cierre."""
        today, out = self.now.date(), []
        for a in ((self.get("aids") or {}).get("calls") or {}).values():
            st = sources.aid_state(a, today)
            if st:
                out.append((*st, a))
        rank = {"open": 0, "approx": 0, "soon": 1, "check": 2}
        return sorted(out, key=lambda x: (rank[x[0]], x[1] or date.max, x[2]["title"]))

    def aid_item(self, lang, state, day, a):
        today = self.now.date()
        title = a["title_ca"] if lang == "ca" and a.get("title_ca") else a["title"]
        if len(title) > 220:
            title = title[:217].rsplit(" ", 1)[0] + "…"
        d = i18n.fmt_deadline(lang, day, today) if day else ""
        if state in ("open", "approx", "soon"):
            when = t(lang, {"open": "aids_until", "approx": "aids_approx", "soon": "aids_opens"}[state], d=d)
        else:
            when = t(lang, "aids_check", t=esc(a["term"])) if a.get("term") else t(lang, "aids_check_none")
        if state in ("open", "approx") and (day - today).days <= 7:
            when = f'<strong title="{t(lang, "aids_soon")}">⏳ {when}</strong>'
        meta = [esc(i18n.organ_name(a["organ"]))]
        if a.get("budget"):
            meta.append(t(lang, "aids_budget", b=i18n.fmt_money(lang, a["budget"])))
        return (f'<li><span class="when">{when}</span><span class="what"><a href="{BDNS_CALL.format(esc(a["id"]))}">'
                f'{esc(title)}</a></span><small class="muted">{" · ".join(meta)}</small></li>')

    def aids_preview(self, lang):
        if self.get("aids") is None:
            return ""
        items = self.aids_open()
        n = {w: sum(w in x[2]["who"] for x in items) for w in AUDIENCES}
        mine = sorted((x for x in items if "people" in x[2]["who"] and x[0] in ("open", "approx")),
                      key=lambda x: (LEVELS.index(aid_level(x[2])), x[1]))[:3]
        top = f'<ul class="events">{"".join(self.aid_item(lang, *x) for x in mine)}</ul>' if mine else ""
        return (f'<section><h2>💶 {t(lang, "aids_home_title")}</h2>'
                f'<p>{t(lang, "aids_home_text", p=n["people"], b=n["business"], e=n["entities"])}</p>{top}'
                f'<p><a href="{self.href(self.path(lang, "aids"))}">{t(lang, "aids_all")} →</a></p></section>')

    def aids_page(self, lang):
        items = self.aids_open()
        jump = " · ".join(f'<a href="#{w}">{t(lang, "aids_" + w)}</a> ({sum(w in x[2]["who"] for x in items)})'
                          for w in AUDIENCES)
        body = [f'<h1>{t(lang, "aids_title")}</h1><p class="lede">{t(lang, "aids_desc")}</p><p>{jump}</p>']
        for who in AUDIENCES:
            mine = [x for x in items if who in x[2]["who"]]
            body.append(f'<h2 id="{who}">{t(lang, "aids_" + who)}</h2>')
            if not mine:
                body.append(f'<p>{t(lang, "aids_empty")}</p>')
            for lvl in LEVELS:
                group = [x for x in mine if aid_level(x[2]) == lvl]
                if group:
                    body.append(f'<details class="group"{" open" if lvl == "LOCAL" or len(group) <= 12 else ""}>'
                                f'<summary>{t(lang, "aids_lvl_" + lvl)} <span class="muted">({len(group)})</span></summary>'
                                f'<ul class="events">{"".join(self.aid_item(lang, *x) for x in group)}</ul></details>')
        body.append(f'<p class="note">{t(lang, "aids_note")}</p>')
        return self.layout(lang, "aids", f'{t(lang, "aids_title")} · {self.name}', t(lang, "aids_desc"), "".join(body))

    def public_jobs(self):
        today = self.now.date().isoformat()
        return [j for j in self.get("cido") or [] if not j["end"] or j["end"] >= today]

    def job_item(self, lang, j):
        meta = [esc(j["company"]), esc(j["contract"]), esc(j["hours"])]
        if j.get("salary"):
            meta.append("–".join(i18n.fmt_money(lang, x) for x in sorted(set(j["salary"]))))
        when = t(lang, "jobs_posted", d=i18n.fmt_deadline(lang, date.fromisoformat(j["date"]), self.now.date()))
        return (f'<li><span class="when">{when}</span><span class="what"><a href="{esc(j["url"])}">{esc(j["title"])}</a>'
                f'</span><small class="muted">{" · ".join(x for x in meta if x)}</small></li>')

    def public_job_item(self, lang, j):
        today = self.now.date()
        when = t(lang, "aids_until", d=i18n.fmt_deadline(lang, date.fromisoformat(j["end"]), today)) if j["end"] else ""
        if j["end"] and (date.fromisoformat(j["end"]) - today).days <= 3:
            when = f'<strong>⏳ {when}</strong>'
        size = t(lang, "jobs_pool") if j["pool"] else t(lang, "jobs_place") if j["places"] == 1 else (
            t(lang, "jobs_places", n=j["places"]) if j["places"] else "")
        meta = [esc(j["org"]), esc(j["kind"]), esc(j["group"]), size]
        return (f'<li><span class="when">{when}</span><span class="what"><a href="{esc(j["url"])}">{esc(j["title"])}</a>'
                f'</span><small class="muted">{" · ".join(x for x in meta if x)}</small></li>')

    def jobs_page(self, lang):
        offers, public = self.get("offers") or [], self.public_jobs()
        body = [f'<h1>{t(lang, "jobs_title")}</h1><p class="lede">{t(lang, "jobs_desc")}</p>'
                f'<p><a href="#offers">{t(lang, "jobs_offers")}</a> ({len(offers)}) · '
                f'<a href="#public">{t(lang, "jobs_public")}</a> ({len(public)})</p>',
                f'<h2 id="offers">{t(lang, "jobs_offers")}</h2>']
        towns = {}
        for j in offers:
            towns.setdefault(j["town"], []).append(j)
        for town, items in towns.items():
            body.append(f'<details class="group"{" open" if town == sources.NEAR_TOWNS[0] else ""}>'
                        f'<summary>{esc(i18n.organ_name(town))} <span class="muted">({len(items)})</span></summary>'
                        f'<ul class="events">{"".join(self.job_item(lang, j) for j in items)}</ul></details>')
        if not offers:
            body.append(f'<p>{t(lang, "jobs_empty")}</p>')
        body.append(f'<h2 id="public">{t(lang, "jobs_public")}</h2>')
        near = [j for j in public if j["km"] is not None and j["km"] <= 4.5]
        for key, items in (("jobs_near", near), ("jobs_far", [j for j in public if j not in near])):
            if items:
                body.append(f'<details class="group"{" open" if key == "jobs_near" or len(items) <= 12 else ""}>'
                            f'<summary>{t(lang, key)} <span class="muted">({len(items)})</span></summary>'
                            f'<ul class="events">{"".join(self.public_job_item(lang, j) for j in items)}</ul></details>')
        if not public:
            body.append(f'<p>{t(lang, "jobs_empty")}</p>')
        body.append(f'<p class="note">{t(lang, "jobs_note")}</p>')
        return self.layout(lang, "jobs", f'{t(lang, "jobs_title")} · {self.name}', t(lang, "jobs_desc"), "".join(body))

    def jobs_preview(self, lang):
        if self.get("offers") is None and self.get("cido") is None:
            return ""
        text = t(lang, "jobs_home_text", o=len(self.get("offers") or []), p=len(self.public_jobs()))
        return (f'<section><h2>{t(lang, "jobs_home")}</h2><p>{text}</p>'
                f'<p><a href="{self.href(self.path(lang, "jobs"))}">{t(lang, "jobs_all")} →</a></p></section>')

    def fuel_rows(self, lang, stations, fuel_best):
        rows = []
        for s in stations:
            cells = []
            for k in ("g95", "diesel"):
                p = s["prices"].get(k)
                txt = i18n.fmt_num(lang, p, 3) if p else "–"
                cells.append(f'<td class="num">{"<strong>" + txt + "</strong>" if p and p == fuel_best[k] else txt}</td>')
            where = esc(s["address"]) + ("" if s["town"] == sources.FUEL_TOWNS[931] else f', {esc(s["town"])}')
            link = f' · <a href="{osm(s["lat"], s["lon"])}">{t(lang, "map")}</a>' if s.get("lat") else ""
            rows.append(f'<tr><td><strong>{esc(s["name"])}</strong><br><small class="muted">{where} · '
                        f'{esc(s["hours"])}{link}</small></td>{"".join(cells)}</tr>')
        return "".join(rows)

    def fuel(self, lang):
        f = self.get("fuel")
        if not f or not f.get("stations"):
            return ""
        by_g95 = sorted(f["stations"], key=lambda s: (s["prices"].get("g95", 99), s["prices"].get("diesel", 99)))
        here = [s for s in by_g95 if s["town"] == sources.FUEL_TOWNS[931]]
        near = [s for s in by_g95 if s["town"] != sources.FUEL_TOWNS[931]][:5]
        head = (f'<thead><tr><th>{t(lang, "fuel_station")}</th><th class="num">{t(lang, "fuel_g95")}</th>'
                f'<th class="num">{t(lang, "fuel_diesel")}</th></tr></thead>')
        best = {k: min((s["prices"][k] for s in here if k in s["prices"]), default=None) for k in ("g95", "diesel")}
        out = [f'<h2 id="fuel">⛽ {t(lang, "fuel_title")}</h2>']
        for key, items, mark in (("fuel_town", here, best), ("fuel_near", near, {})):
            if items:
                out.append(f'<h3>{t(lang, key)}</h3><div class="scroll-x"><table class="recent">{head}<tbody>'
                           f'{self.fuel_rows(lang, items, {"g95": mark.get("g95"), "diesel": mark.get("diesel")})}'
                           f'</tbody></table></div>')
        out.append(f'<p class="note">{t(lang, "fuel_note", t=esc(f.get("updated", "")))}</p>')
        return "".join(out)

    def fuel_preview(self, lang):
        here = [s for s in (self.get("fuel") or {}).get("stations", []) if s["town"] == sources.FUEL_TOWNS[931]]
        best = {}
        for k in ("g95", "diesel"):
            cands = [s for s in here if k in s["prices"]]
            if cands:
                best[k] = min(cands, key=lambda s: s["prices"][k])
        if len(best) < 2:
            return ""
        name = lambda s: f'{esc(s["name"])} ({esc(s["address"])})'  # noqa: E731
        text = t(lang, "fuel_home_text", g=i18n.fmt_num(lang, best["g95"]["prices"]["g95"], 3), gs=name(best["g95"]),
                 d=i18n.fmt_num(lang, best["diesel"]["prices"]["diesel"], 3), ds=name(best["diesel"]))
        return (f'<section><h2>{t(lang, "fuel_home")}</h2><p>{text}</p>'
                f'<p><a href="{self.href(self.path(lang, "directory"))}#fuel">{t(lang, "fuel_more")} →</a></p></section>')

    def contracts(self):
        """(grandes inversiones, licitaciones abiertas, anunciadas): lo anulado no sale."""
        now = self.now.strftime("%Y-%m-%dT%H:%M")
        since = (self.now.date() - timedelta(days=INVEST_DAYS)).isoformat()
        live = [c for c in self.get("contracts") or [] if c["phase"] != "Anul·lació"]
        big = sorted((c for c in live if c["amount"] >= BIG and c["date"] >= since), key=lambda c: -c["amount"])
        bids = sorted((c for c in live if c["phase"] == "Anunci de licitació" and c["deadline"] >= now),
                      key=lambda c: c["deadline"])
        soon = [c for c in live if c["phase"] in SOON_PHASES and c["date"] >= since]
        return big, bids, soon

    def phase_key(self, c):
        closed = c["phase"] == "Anunci de licitació" and c["deadline"] < self.now.strftime("%Y-%m-%dT%H:%M")
        return "closed_bids" if closed else c["phase"]

    def contract_item(self, lang, c):
        today, key = self.now.date(), self.phase_key(c)
        when = [f'<strong>{i18n.fmt_big(lang, c["amount"])}</strong>' if c["amount"] else ""]
        if key == "Anunci de licitació" and c["deadline"]:
            d = date.fromisoformat(c["deadline"][:10])
            until = t(lang, "invest_until", d=i18n.fmt_deadline(lang, d, today))
            when.append(f"⏳ {until}" if (d - today).days <= 3 else until)
        else:
            when.append(i18n.fmt_deadline(lang, date.fromisoformat(c["date"]), today))
        badge = f'<span class="tier {PHASE_TIER.get(key, "t3")}">{esc(i18n.phase(lang, key))}</span>'
        meta = [esc(c["organ"]), esc(i18n.contract_type(lang, c["type"])),
                t(lang, "invest_lots", n=c["lots"]) if c["lots"] > 1 else ""]
        if c["winners"]:
            more = f' +{len(c["winners"]) - 3}' if len(c["winners"]) > 3 else ""
            meta.append(t(lang, "invest_winners", w=esc(", ".join(c["winners"][:3]) + more)))
        title = f'<a href="{esc(c["url"])}">{esc(c["title"])}</a>' if c.get("url") else esc(c["title"])
        return (f'<li><span class="when">{badge} {" · ".join(x for x in when if x)}</span><span class="what">{title}</span>'
                f'<small class="muted">{" · ".join(x for x in meta if x)}</small></li>')

    def company_events(self):
        since = (self.now.date() - timedelta(days=COMPANY_DAYS)).isoformat()
        return [e for e in (self.get("companies") or {}).get("events", []) if e["date"] >= since]

    def company_meta(self, lang, e):
        """Datos de un acto del BORME, en texto: capital, actividad o municipio de destino."""
        meta = []
        if e.get("capital"):
            sign = {"capital": "+", "capital_down": "−"}.get(e["kind"], "")
            c = sign + i18n.fmt_money(lang, e["capital"])
            meta.append(t(lang, "invest_capital_change", c=c, t=i18n.fmt_money(lang, e["total"])) if e.get("total")
                        else t(lang, "invest_capital", c=c))
        meta += [e.get("activity") or "", "→ " + i18n.organ_name(e["town"]) if e.get("town") else ""]
        return [x for x in meta if x]

    def company_item(self, lang, e):
        meta = [esc(x) for x in self.company_meta(lang, e)] + [f'<a href="{esc(e["url"])}">BORME</a>']
        return (f'<li><span class="when">{i18n.fmt_date(lang, date.fromisoformat(e["date"]))}</span>'
                f'<span class="what">{esc(e["name"])}</span><small class="muted">{" · ".join(meta)}</small></li>')

    def invest_page(self, lang):
        big, bids, soon = self.contracts()
        sections = (("big", "invest_big", big), ("open", "invest_open", bids), ("soon", "invest_soon", soon))
        comp, events = self.get("companies"), self.company_events()
        jump = [f'<a href="#{k}">{t(lang, key)}</a> ({len(items)})' for k, key, items in sections]
        if comp is not None:
            jump.append(f'<a href="#companies">{t(lang, "invest_companies")}</a> ({len(events)})')
        body = [f'<h1>{t(lang, "invest_title")}</h1><p class="lede">{t(lang, "invest_desc")}</p><p>{" · ".join(jump)}</p>']
        for k, key, items in sections:
            body.append(f'<h2 id="{k}">{t(lang, key)}</h2><p>{t(lang, key + "_text")}</p>')
            body.append(f'<ul class="events">{"".join(self.contract_item(lang, c) for c in items)}</ul>'
                        if items else f'<p>{t(lang, "invest_empty")}</p>')
        if comp is not None:
            kinds = {k: [e for e in events if e["kind"] == k] for k in i18n.COMPANY_KINDS}
            body.append(f'<h2 id="companies">{t(lang, "invest_companies")}</h2><p>' + t(
                lang, "invest_companies_text", d=COMPANY_DAYS, n=len(kinds["new"]), m=len(kinds["moved_in"]),
                u=len(kinds["capital"]), c=i18n.fmt_money(lang, sum(e.get("capital") or 0 for e in kinds["new"]))) + "</p>")
            for k, items in kinds.items():
                if items:
                    body.append(f'<details class="group"{" open" if k == "capital" or len(items) <= 12 else ""}>'
                                f'<summary>{esc(i18n.company_kind(lang, k))} <span class="muted">({len(items)})</span></summary>'
                                f'<ul class="events">{"".join(self.company_item(lang, e) for e in items)}</ul></details>')
        feed = self.href(self.path(lang, "invest") + "feed.xml")
        body.append(f'<p class="tip">{t(lang, "invest_feed", url=feed)}</p>')
        day = lambda iso: i18n.fmt_deadline(lang, date.fromisoformat(iso), self.now.date()) if iso else "–"  # noqa: E731
        body.append(f'<p class="note">{t(lang, "invest_note", t=day((comp or {}).get("last")), since=day((comp or {}).get("since")))}</p>')
        head = f'<link rel="alternate" type="application/atom+xml" title="{esc(t(lang, "invest_title"))}" href="{feed}">\n'
        return self.layout(lang, "invest", f'{t(lang, "invest_title")} · {self.name}', t(lang, "invest_desc"),
                           "".join(body), head=head)

    def invest_preview(self, lang):
        if self.get("contracts") is None and self.get("companies") is None:
            return ""
        big, bids, _ = self.contracts()
        arrived = [e for e in self.company_events() if e["kind"] in ("new", "moved_in")]
        latest = sorted(big, key=lambda c: c["date"], reverse=True)[:3]
        text = t(lang, "invest_home_text", o=len(bids), b=len(big), n=len(arrived), d=COMPANY_DAYS)
        top = f'<ul class="events">{"".join(self.contract_item(lang, c) for c in latest)}</ul>' if latest else ""
        return (f'<section><h2>{t(lang, "invest_home")}</h2><p>{text}</p>{top}'
                f'<p><a href="{self.href(self.path(lang, "invest"))}">{t(lang, "invest_all")} →</a></p></section>')

    def feed(self, lang):
        """Canal Atom con las novedades de la página de inversiones: un cambio de fase cuenta como novedad."""
        big, bids, soon = self.contracts()
        since = (self.now.date() - timedelta(days=FEED_DAYS)).isoformat()
        entries = []
        for c in {c["id"]: c for c in big + bids + soon}.values():
            if c["date"] >= since:
                key = self.phase_key(c)
                title = " · ".join(x for x in (i18n.phase(lang, key), i18n.fmt_big(lang, c["amount"]) if c["amount"] else "",
                                               c["title"]) if x)
                summary = " · ".join(x for x in (c["organ"], i18n.contract_type(lang, c["type"])) if x)
                entries.append((c["date"], f'{c["id"]}|{key}', title, c["url"], summary))
        for e in self.company_events():
            if e["date"] >= since:
                entries.append((e["date"], e["id"], f'{i18n.company_kind(lang, e["kind"])} · {e["name"]}', e["url"],
                                " · ".join(self.company_meta(lang, e))))
        page = self.absolute(self.path(lang, "invest"))
        host = urlparse(self.base_url).hostname
        items = "".join(
            f'<entry><title>{esc(title)}</title><link href="{esc(url or page)}"/>'
            f'<id>tag:{host},2026:{hashlib.sha1(key.encode()).hexdigest()[:20]}</id>'
            f'<updated>{day}T12:00:00Z</updated><summary>{esc(summary)}</summary></entry>\n'
            for day, key, title, url, summary in sorted(entries, reverse=True)[:80])
        return ('<?xml version="1.0" encoding="utf-8"?>\n'
                f'<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="{lang}">\n'
                f'<title>{esc(t(lang, "invest_title"))}</title><subtitle>{esc(t(lang, "invest_desc"))}</subtitle>\n'
                f'<link rel="alternate" href="{page}"/><link rel="self" href="{page}feed.xml"/>\n'
                f'<id>{page}</id><updated>{self.now.astimezone(tz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>'
                f'<author><name>{esc(self.name)}</name></author>\n{items}</feed>\n')

    def emergency_page(self, lang):
        items = []
        for e in self.get("equipments") or []:
            if e["cat"] != "Emergències. Seguretat":
                continue
            phone = re.sub(r"[^+0-9]", "", e.get("phone", ""))
            extra = [esc(e["address"]) if e.get("address") else "",
                     f'{t(lang, "phone")} <a href="tel:{phone}">{esc(e["phone"])}</a>' if phone else "",
                     f'<a href="{osm(e["lat"], e["lon"])}">{t(lang, "map")}</a>' if e.get("lat") else ""]
            items.append(f'<li><strong>{esc(e["name"])}</strong><br>{" · ".join(x for x in extra if x)}</li>')
        local = f'<h2>{t(lang, "emergency_local")}</h2><ul class="dir">{"".join(items)}</ul>' if items else ""
        return self.layout(lang, "emergency", f'{t(lang, "emergency_title")} · {self.name}', t(lang, "emergency_desc"),
                           f'<h1>{t(lang, "emergency_title")}</h1>{t(lang, "emergency_body", local=local)}')

    # ---------- páginas ----------
    def home(self, lang):
        quick = (f'<section><h2>{t(lang, "quick_title")}</h2><ul class="months">'
                 f'<li><a href="{self.href(self.path(lang, "agenda"))}">{t(lang, "agenda_title")}</a></li>'
                 f'<li><a href="{self.href(self.path(lang, "leisure"))}#weekend">{t(lang, "weekend_title")}</a></li>'
                 f'<li><a href="{self.href(self.path(lang, "aids"))}">{t(lang, "aids_title")}</a></li>'
                 f'<li><a href="{self.href(self.path(lang, "invest"))}">{t(lang, "invest_title")}</a></li>'
                 f'<li><a href="{self.href(self.path(lang, "leisure"))}">{t(lang, "leisure_title")}</a></li>'
                 f'<li><a href="{self.href(self.path(lang, "directory"))}">{t(lang, "directory_title")}</a></li>'
                 f'<li><a href="{self.href(self.path(lang, "directory"))}#chargers">{t(lang, "chargers_title")}</a></li>'
                 f'<li><a href="{self.href(self.path(lang, "emergency"))}">{t(lang, "emergency_title")}</a></li></ul></section>')
        body = (f'<h1>{t(lang, "home_title")}</h1><p class="lede">{i18n.fmt_date(lang, self.now.date())} · '
                f'{t(lang, "tagline")}</p>{self.weather(lang)}{self.light(lang)}{self.transport(lang)}'
                f'{self.agenda_preview(lang)}{self.aids_preview(lang)}{self.jobs_preview(lang)}{self.invest_preview(lang)}'
                f'{self.fuel_preview(lang)}'
                f'{self.air(lang)}{quick}')
        ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": self.name, "inLanguage": lang,
               "url": self.absolute(self.path(lang, "home")), "description": t(lang, "home_desc")}]
        return self.layout(lang, "home", f'{t(lang, "home_title")} · {self.name}', t(lang, "home_desc"), body, ld)

    def agenda_page(self, lang):
        ag = self.get("agenda") or {}
        permanent = ag.get("permanent", [])
        upcoming, ongoing = self.events_split()
        events = upcoming + ongoing
        body = [f'<h1>{t(lang, "agenda_title")}</h1><p class="lede">{t(lang, "agenda_desc")}</p>']
        body.append(f'<ul class="events">{"".join(self.event_item(lang, e) for e in upcoming)}</ul>'
                    if upcoming else f'<p>{t(lang, "agenda_empty")}</p>')
        if ongoing:
            body.append(f'<h2>{t(lang, "ongoing_title")}</h2>'
                        f'<ul class="events">{"".join(self.event_item(lang, e) for e in ongoing)}</ul>')
        body.append(f'<p>{t(lang, "ics_link", url=self.absolute("/agenda.ics"))}</p>'
                    f'<p class="note">{t(lang, "add_event", repo=esc(self.cfg.get("repo_url") or "https://github.com"))}</p>')
        if permanent:
            items = "".join(f'<li>{f"<a href=\"{esc(p["url"])}\">{esc(p["title"])}</a>" if p.get("url") else esc(p["title"])}'
                            f' <small class="muted">{esc(p.get("place", ""))}</small></li>' for p in permanent)
            body.append(f'<h2>{t(lang, "agenda_permanent")}</h2><ul class="months">{items}</ul>')
        ld = [{"@context": "https://schema.org", "@type": "Event", "name": e["title"],
               "startDate": e["start"] + (f'T{e["time"]}' if len(e.get("time", "")) == 5 else ""),
               "endDate": e.get("end") or e["start"],
               "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
               "eventStatus": "https://schema.org/EventScheduled",
               "location": {"@type": "Place", "name": e.get("place") or "Cerdanyola del Vallès",
                            "address": {"@type": "PostalAddress", "addressLocality": "Cerdanyola del Vallès",
                                        "addressRegion": "Barcelona", "addressCountry": "ES"}},
               **({"url": e["url"]} if e.get("url") else {})} for e in events[:30]]
        return self.layout(lang, "agenda", f'{t(lang, "agenda_title")} · {self.name}', t(lang, "agenda_desc"),
                           "".join(body), ld)

    def directory_page(self, lang):
        body = [f'<h1>{t(lang, "directory_title")}</h1><p class="lede">{t(lang, "directory_desc")}</p>', self.fuel(lang)]
        chargers = self.get("chargers") or []
        if chargers:
            items = "".join(
                f'<li><strong>{esc(c["name"])}</strong> · {esc(c["address"])} · {esc(c["speed"])}'
                f'{f" · <a href=\"{osm(c["lat"], c["lon"])}\">{t(lang, "map")}</a>" if c.get("lat") else ""}</li>'
                for c in chargers)
            body.append(f'<h2 id="chargers">🔌 {t(lang, "chargers_title")}</h2><ul class="months">{items}</ul>')
        groups = {}
        for e in self.get("equipments") or []:
            groups.setdefault(e["cat"], []).append(e)
        for cat in sorted(groups, key=lambda c: (c == "", i18n.category(lang, c))):
            items = []
            for e in groups[cat]:
                extra = [esc(f'{e["address"]}, {e["cp"]}') if e["address"] else ""]
                if e.get("phone"):
                    extra.append(f'{t(lang, "phone")} <a href="tel:{esc(e["phone"].replace("-", "").replace(" ", ""))}">{esc(e["phone"])}</a>')
                if e.get("lat"):
                    extra.append(f'<a href="{osm(e["lat"], e["lon"])}">{t(lang, "map")}</a>')
                items.append(f'<li><strong>{esc(e["name"])}</strong> <small class="muted">{esc(e["sub"])}</small>'
                             f'<br>{" · ".join(x for x in extra if x)}</li>')
            body.append(f'<details class="group"><summary>{esc(i18n.category(lang, cat))} '
                        f'<span class="muted">({len(groups[cat])})</span></summary><ul class="dir">{"".join(items)}</ul></details>')
        return self.layout(lang, "directory", f'{t(lang, "directory_title")} · {self.name}',
                           t(lang, "directory_desc"), "".join(body))

    def place_item(self, lang, p):
        name = esc(p["name"])
        name = f'<a href="{esc(p["web"])}" rel="noopener">{name}</a>' if p.get("web") else name
        kind = i18n.place_type(lang, p["type"])
        if p.get("cuisine"):
            kind += " · " + i18n.cuisine(lang, p["cuisine"])
        if re.match(r"(GR|PR|SL)\b|B\d", p.get("ref", "")) and p["ref"] not in p["name"]:  # GR 92, PR-C 35, Bicivia B6
            kind += " · " + p["ref"]
        extra = [esc(p.get("address", "")), f'{i18n.fmt_num(lang, float(p["km"]), 1)} km' if p.get("km") else "",
                 f'🕒 {esc(i18n.hours(lang, p["hours"]))}' if p.get("hours") else ""]
        if p.get("phone"):
            extra.append(f'{t(lang, "phone")} <a href="tel:{esc(re.sub(r"[^+0-9]", "", p["phone"]))}">{esc(p["phone"])}</a>')
        url = f'https://www.openstreetmap.org/{p["osm"]}' if p.get("osm") else osm(p["lat"], p["lon"])
        extra.append(f'<a href="{esc(url)}">{t(lang, "map")}</a>')
        return (f'<li><strong>{name}</strong> <small class="muted">{esc(kind)}</small>'
                f'<br>{" · ".join(x for x in extra if x)}</li>')

    def plan_today(self, lang, places):
        """Ideas para hoy según el tiempo: al aire libre si no llueve, a cubierto si llueve."""
        days = (self.get("weather") or {}).get("days") or []
        today = next((d for d in days if d["date"] == self.now.date().isoformat()), None)
        if not today:
            return ""
        rainy = today["rain_mm"] >= 2 or any(w in (today.get("symbol") or "") for w in RAINY)
        if rainy:
            pool = [p for p in places if p["group"] == "culture" and p["type"] != "attraction"]
            intro = t(lang, "plan_in", mm=i18n.fmt_num(lang, today["rain_mm"], 1))
        else:
            pool = [p for p in places if p["type"] in ("spring", "viewpoint", "peak", "picnic_site", "castle", "archaeological_site")
                    or (p["group"] == "routes" and p.get("km") and float(p["km"]) <= 15)]
            intro = t(lang, "plan_out", sky=i18n.sky(lang, today["symbol"])[1].lower() or "–", tmax=today["tmax"])
        if not pool:
            return ""
        # cambia cada día, sin azar; separadas un tercio de la lista para mezclar fuentes, miradores, rutas...
        start, step = self.now.date().toordinal() % len(pool), max(1, len(pool) // 3)
        picks = list({id(p): p for p in (pool[(start + i * step) % len(pool)] for i in range(3))}.values())
        todays = [e for e in self.events_split()[0] if e["start"] == self.now.date().isoformat()]
        more = (f'<p><a href="{self.href(self.path(lang, "agenda"))}">{t(lang, "plan_events", n=len(todays))} →</a></p>'
                if todays else "")
        return (f'<section><h2>{t(lang, "plan_title")}</h2><p>{intro}</p>'
                f'<ul class="dir">{"".join(self.place_item(lang, p) for p in picks)}</ul>{more}</section>')

    def leisure_page(self, lang):
        places = sources.merge_places(self.get("leisure") or [], self.get("nightlife") or [])
        upcoming, ongoing = self.events_split()
        limit = (self.now.date() + timedelta(days=45)).isoformat()
        parties = [e for e in upcoming if festive(e) and e["start"] <= limit][:15]
        body = [f'<h1>{t(lang, "leisure_title")}</h1><p class="lede">{t(lang, "leisure_desc")}</p>',
                self.plan_today(lang, places), self.weekend(lang),
                f'<section><h2>🎉 {t(lang, "festive_title")}</h2>']
        body.append(f'<ul class="events">{"".join(self.event_item(lang, e) for e in parties)}</ul>'
                    if parties else f'<p>{t(lang, "festive_empty")}</p>')
        body.append(f'<p><a href="{self.href(self.path(lang, "agenda"))}">{t(lang, "agenda_all")} →</a></p>'
                    f'<p class="note">{t(lang, "add_event", repo=esc(self.cfg.get("repo_url") or "https://github.com"))}</p></section>')
        groups = {}
        for p in places:
            groups.setdefault(p["group"], []).append(p)
        for key in i18n.LEISURE_GROUPS:
            items = groups.get(key)
            if not items:
                continue
            icon, label = i18n.group(lang, key)
            body.append(f'<details class="group" id="{key}"{" open" if len(items) <= 40 else ""}><summary>{icon} {esc(label)} '
                        f'<span class="muted">({len(items)})</span></summary>'
                        f'<ul class="dir">{"".join(self.place_item(lang, p) for p in items)}</ul></details>')
        if places:
            body.append(f'<p class="note">{t(lang, "osm_note")}</p>')
        extra = sorted({s[0].upper() + s[1:] for p in places for s in p.get("src", [])})
        if extra:
            body.append(f'<p class="note">{t(lang, "overture_note", src=esc(", ".join(extra)))}</p>')
        return self.layout(lang, "leisure", f'{t(lang, "leisure_title")} · {self.name}', t(lang, "leisure_desc"),
                           "".join(body))

    def text_page(self, lang, kind):
        repo = self.cfg.get("repo_url") or "https://github.com/"
        owner = self.cfg.get("owner") or {}
        if owner.get("name"):
            owner_html = esc(owner["name"]) + (f" · NIF {esc(owner['nif'])}" if owner.get("nif") else "") + (
                f' · <a href="mailto:{esc(owner["email"])}">{esc(owner["email"])}</a>' if owner.get("email") else "")
        else:
            owner_html = t(lang, "owner_missing", repo=repo)
        light = (self.get("light") or {}).get("site") or "https://github.com/"
        body = t(lang, f"{kind}_body", site=esc(self.name), repo=repo, owner=owner_html, light=esc(light))
        return self.layout(lang, kind, f'{t(lang, kind)} · {self.name}', t(lang, "home_desc"),
                           f'<article class="prose"><h1>{t(lang, kind)}</h1>{body}</article>')

    def root_page(self):
        links = "".join(f'<li><a href="{self.href(self.path(lg, "home"))}" hreflang="{lg}" lang="{lg}">'
                        f'{t(lg, "lang_name")} — {t(lg, "home_title")}</a></li>' for lg in LANGS)
        alts = "".join(f'<link rel="alternate" hreflang="{lg}" href="{self.absolute(self.path(lg, "home"))}">'
                       for lg in LANGS)
        return f"""<!doctype html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(self.name)} · {esc(t("ca", "home_title"))}</title>
<meta name="description" content="{esc(t('ca', 'home_desc'))}">
<link rel="canonical" href="{self.absolute('/')}">
{alts}<link rel="alternate" hreflang="x-default" href="{self.absolute('/')}">
<link rel="icon" href="{self.href('/static/favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{self.href('/static/style.css')}">
<script>
(function(){{var m={{ca:"ca",es:"es",gl:"es",eu:"es",en:"en"}};var l=(navigator.languages||[navigator.language||"ca"]);
for(var i=0;i<l.length;i++){{var k=m[(l[i]||"").slice(0,2).toLowerCase()];if(k){{location.replace("{self.prefix}/"+k+"/");return;}}}}
location.replace("{self.prefix}/ca/");}})();
</script>
</head>
<body><main class="wrap"><h1>{esc(self.name)}</h1><p>{t("ca", "choose")} · {t("es", "choose")} · {t("en", "choose")}</p><ul class="months">{links}</ul></main></body>
</html>
"""

    def not_found(self):
        body = "".join(f'<p lang="{lg}"><strong>{t(lg, "notfound_title")}.</strong> '
                       f'<a href="{self.href(self.path(lg, "home"))}">{t(lg, "notfound_text")}</a></p>' for lg in LANGS)
        return self.layout("ca", "home", t("ca", "notfound_title"), "", body, noindex=True)

    def ics(self):
        """Agenda en iCalendar para suscribirse desde el móvil o Google Calendar (sin los actos de semanas)."""
        def text(s):
            return re.sub(r"([\\,;])", r"\\\1", s).replace("\n", "\\n")

        def fold(line):  # RFC 5545: líneas de 75 octetos como máximo
            out, raw = [], line.encode("utf-8")
            while len(raw) > 75:
                cut = 75 if not out else 74
                while raw[cut] & 0xC0 == 0x80:  # no partir un carácter UTF-8
                    cut -= 1
                out.append(raw[:cut].decode("utf-8"))
                raw = raw[cut:]
            out.append(raw.decode("utf-8"))
            return "\r\n ".join(out)

        stamp = self.now.astimezone(tz.UTC).strftime("%Y%m%dT%H%M%SZ")
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{self.name}//agenda//CA", "CALSCALE:GREGORIAN",
                 "METHOD:PUBLISH", f"X-WR-CALNAME:{text(t('ca', 'agenda_title'))}", "X-WR-TIMEZONE:Europe/Madrid",
                 "REFRESH-INTERVAL;VALUE=DURATION:PT12H"]
        for e in self.events_split()[0]:
            start, end = date.fromisoformat(e["start"]), date.fromisoformat(e.get("end") or e["start"])
            if (end - start).days > 3:
                continue
            uid = hashlib.sha1(f'{e["title"]}|{e["start"]}|{e["source"]}'.encode()).hexdigest()[:20]
            lines += ["BEGIN:VEVENT", f"UID:{uid}@{urlparse(self.base_url).hostname}", f"DTSTAMP:{stamp}"]
            if re.fullmatch(r"\d\d:\d\d", e.get("time", "")):
                local = datetime.fromisoformat(f'{e["start"]}T{e["time"]}')
                utc = local.replace(tzinfo=tz.offset_at(local.replace(tzinfo=tz.CET))).astimezone(tz.UTC)
                lines.append(f'DTSTART:{utc.strftime("%Y%m%dT%H%M%SZ")}')
            else:
                lines += [f'DTSTART;VALUE=DATE:{start.strftime("%Y%m%d")}',
                          f'DTEND;VALUE=DATE:{(end + timedelta(days=1)).strftime("%Y%m%d")}']
            lines.append(f'SUMMARY:{text(e["title"])}')
            if e.get("place"):
                lines.append(f'LOCATION:{text(e["place"] + ", Cerdanyola del Vallès")}')
            if e.get("url"):
                lines.append(f'URL:{e["url"]}')
            lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")
        return "".join(fold(x) + "\r\n" for x in lines)

    def sitemap(self):
        today = self.now.date().isoformat()
        urls = []
        daily = ("home", "agenda", "leisure", "aids", "jobs", "invest", "directory")
        for kind in daily + ("emergency", "about", "legal", "privacy"):
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{lg}" href="{self.absolute(self.path(lg, kind))}"/>'
                           for lg in LANGS)
            for lg in LANGS:
                lastmod = f"<lastmod>{today}</lastmod>" if kind in daily else ""
                urls.append(f"<url><loc>{self.absolute(self.path(lg, kind))}</loc>{lastmod}{alts}</url>")
        return ('<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                'xmlns:xhtml="http://www.w3.org/1999/xhtml">' + "".join(urls) + "</urlset>\n")

    def build(self):
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        shutil.copytree(ROOT / "static", self.out / "static")
        for lang in LANGS:
            self.write(self.path(lang, "home"), self.home(lang))
            self.write(self.path(lang, "agenda"), self.agenda_page(lang))
            self.write(self.path(lang, "leisure"), self.leisure_page(lang))
            self.write(self.path(lang, "aids"), self.aids_page(lang))
            self.write(self.path(lang, "jobs"), self.jobs_page(lang))
            self.write(self.path(lang, "invest"), self.invest_page(lang))
            self.write(self.path(lang, "invest") + "feed.xml", self.feed(lang))
            self.write(self.path(lang, "emergency"), self.emergency_page(lang))
            self.write(self.path(lang, "directory"), self.directory_page(lang))
            for kind in ("about", "legal", "privacy"):
                self.write(self.path(lang, kind), self.text_page(lang, kind))
        self.write("/", self.root_page())
        self.write("/404.html", self.not_found())
        self.write("/sitemap.xml", self.sitemap())
        (self.out / "agenda.ics").write_bytes(self.ics().encode("utf-8"))
        self.write("/robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {self.absolute('/sitemap.xml')}\n")
        self.write("/.nojekyll", "")
        return self.out
