"""Genera el sitio estático de Cerdanyola a partir de los datos en caché."""
import json
import shutil
from datetime import date
from html import escape as esc
from pathlib import Path
from urllib.parse import urlparse

import i18n
import tz
from i18n import LANGS, t

ROOT = Path(__file__).resolve().parent.parent
RODALIES = "https://rodalies.gencat.cat/ca/estat_servei/"


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
    def layout(self, lang, kind, title, desc, body, jsonld=None, noindex=False):
        alts = "".join(f'<link rel="alternate" hreflang="{lg}" href="{self.absolute(self.path(lg, kind))}">'
                       for lg in LANGS)
        x_default = self.absolute("/") if kind == "home" else self.absolute(self.path("ca", kind))
        ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>'
                     for j in (jsonld or []))
        switch = " · ".join(
            f'<a href="{self.href(self.path(lg, kind))}" hreflang="{lg}" lang="{lg}"'
            f'{" aria-current=\"true\"" if lg == lang else ""}>{t(lg, "lang_name")}</a>' for lg in LANGS)
        nav = " · ".join(f'<a href="{self.href(self.path(lang, k))}">{t(lang, k + "_title" if k != "home" else "home")}</a>'
                         for k in ("home", "agenda", "directory"))
        links = " · ".join(f'<a href="{self.href(self.path(lang, k))}">{t(lang, k)}</a>'
                           for k in ("about", "legal", "privacy"))
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
{ld}
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
        meta = " · ".join(x for x in (esc(e.get("place", "")), t(lang, "free") if e.get("free") else "",
                                       t(lang, "src_" + e["source"])) if x)
        return f'<li><span class="when">{when}</span><span class="what">{title}</span><small class="muted">{meta}</small></li>'

    def agenda_preview(self, lang, n=6):
        ag = self.get("agenda")
        if ag is None:
            return ""
        events = ag.get("events", [])[:n]
        body = (f'<ul class="events">{"".join(self.event_item(lang, e) for e in events)}</ul>'
                if events else f'<p>{t(lang, "agenda_empty")}</p>')
        return (f'<section><h2>{t(lang, "agenda_next")}</h2>{body}'
                f'<p><a href="{self.href(self.path(lang, "agenda"))}">{t(lang, "agenda_all")} →</a></p></section>')

    # ---------- páginas ----------
    def home(self, lang):
        quick = (f'<section><h2>{t(lang, "quick_title")}</h2><ul class="months">'
                 f'<li><a href="{self.href(self.path(lang, "agenda"))}">{t(lang, "agenda_title")}</a></li>'
                 f'<li><a href="{self.href(self.path(lang, "directory"))}">{t(lang, "directory_title")}</a></li>'
                 f'<li><a href="{self.href(self.path(lang, "directory"))}#chargers">{t(lang, "chargers_title")}</a></li></ul></section>')
        body = (f'<h1>{t(lang, "home_title")}</h1><p class="lede">{i18n.fmt_date(lang, self.now.date())} · '
                f'{t(lang, "tagline")}</p>{self.weather(lang)}{self.light(lang)}{self.transport(lang)}'
                f'{self.agenda_preview(lang)}{self.air(lang)}{quick}')
        ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": self.name, "inLanguage": lang,
               "url": self.absolute(self.path(lang, "home")), "description": t(lang, "home_desc")}]
        return self.layout(lang, "home", f'{t(lang, "home_title")} · {self.name}', t(lang, "home_desc"), body, ld)

    def agenda_page(self, lang):
        ag = self.get("agenda") or {}
        events, permanent = ag.get("events", []), ag.get("permanent", [])
        body = [f'<h1>{t(lang, "agenda_title")}</h1><p class="lede">{t(lang, "agenda_desc")}</p>']
        body.append(f'<ul class="events">{"".join(self.event_item(lang, e) for e in events)}</ul>'
                    if events else f'<p>{t(lang, "agenda_empty")}</p>')
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
        body = [f'<h1>{t(lang, "directory_title")}</h1><p class="lede">{t(lang, "directory_desc")}</p>']
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

    def sitemap(self):
        today = self.now.date().isoformat()
        urls = []
        for kind in ("home", "agenda", "directory", "about", "legal", "privacy"):
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{lg}" href="{self.absolute(self.path(lg, kind))}"/>'
                           for lg in LANGS)
            for lg in LANGS:
                lastmod = f"<lastmod>{today}</lastmod>" if kind in ("home", "agenda") else ""
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
            self.write(self.path(lang, "directory"), self.directory_page(lang))
            for kind in ("about", "legal", "privacy"):
                self.write(self.path(lang, kind), self.text_page(lang, kind))
        self.write("/", self.root_page())
        self.write("/404.html", self.not_found())
        self.write("/sitemap.xml", self.sitemap())
        self.write("/robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {self.absolute('/sitemap.xml')}\n")
        self.write("/.nojekyll", "")
        return self.out
