"""Fuentes de datos abiertos para Cerdanyola del Vallès.

Cada fuente tiene una función `parse_*` pura (probada con datos reales
guardados en tests/fixtures) y una `fetch_*` que la descarga.
"""
import html
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path

import tz

ROOT = Path(__file__).resolve().parent.parent
LAT, LON, ALTITUDE = 41.4913, 2.1408, 80
SOCRATA = "https://analisi.transparenciacatalunya.cat/resource/{}.json?"
AGENDA_MUNICIPI = "agenda:ubicacions/barcelona/valles-occidental/cerdanyola-del-valles"
AIR_MUNICIPIS = ("Sant Cugat del Vallès", "Montcada i Reixac", "Barberà del Vallès", "Sabadell")
POLLUTANTS = ("NO2", "O3", "PM10", "PM2.5")
LINES = ("R7", "R8")

# cerdanyola.cat no envía su certificado intermedio; lo añadimos (válido hasta 2036).
_CTX = ssl.create_default_context()
_CTX.load_verify_locations(str(ROOT / "certs" / "sectigo-ov-r36.pem"))


class FetchError(Exception):
    pass


def user_agent():
    repo = os.environ.get("GITHUB_REPOSITORY", "cerdanyola-local")
    return f"cerdanyola-local/1.0 (+https://github.com/{repo})"


def get_text(url, tries=3, timeout=40):
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": user_agent()})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code < 500:
                break
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def get_json(url):
    try:
        return json.loads(get_text(url))
    except json.JSONDecodeError as exc:
        raise FetchError(f"{url}: {exc}") from exc


def socrata(dataset, **params):
    return get_json(SOCRATA.format(dataset) + urllib.parse.urlencode(
        {f"${k}": v for k, v in params.items()}))


# ---------- tiempo (MET Norway, CC BY 4.0) ----------
def parse_weather(doc, now):
    days, current = {}, None
    for e in doc["properties"]["timeseries"]:
        t = tz.to_madrid(tz.parse_iso(e["time"]))
        data = e["data"]
        inst = data["instant"]["details"]
        nxt = data.get("next_1_hours") or data.get("next_6_hours") or {}
        symbol = nxt.get("summary", {}).get("symbol_code")
        rain = nxt.get("details", {}).get("precipitation_amount", 0.0)
        if current is None and t + timedelta(hours=1) > now:
            current = {"time": t.isoformat(), "temp": inst.get("air_temperature"),
                       "wind_kmh": round(inst.get("wind_speed", 0) * 3.6), "symbol": symbol}
        d = days.setdefault(t.date().isoformat(), {"temps": [], "rain": 0.0, "wind": 0, "symbol": None, "dist": 99})
        if inst.get("air_temperature") is not None:
            d["temps"].append(inst["air_temperature"])
        d["rain"] += rain
        d["wind"] = max(d["wind"], round(inst.get("wind_speed", 0) * 3.6))
        if symbol and abs(t.hour - 13) < d["dist"]:
            d["symbol"], d["dist"] = symbol, abs(t.hour - 13)
    out = []
    for day in sorted(days):
        d = days[day]
        if day < now.date().isoformat() or not d["temps"]:
            continue
        out.append({"date": day, "tmin": round(min(d["temps"])), "tmax": round(max(d["temps"])),
                    "rain_mm": round(d["rain"], 1), "wind_kmh": d["wind"], "symbol": d["symbol"]})
    return {"updated": doc["properties"]["meta"].get("updated_at"), "now": current, "days": out[:6]}


def fetch_weather(now):
    url = (f"https://api.met.no/weatherapi/locationforecast/2.0/compact"
           f"?lat={LAT}&lon={LON}&altitude={ALTITUDE}")
    return parse_weather(get_json(url), now)


# ---------- agenda ----------
def parse_agenda_gencat(rows, today):
    events, permanent = [], []
    for r in rows:
        links = [u.strip() for u in (r.get("enlla_os") or "").split(",") if u.strip()]
        item = {"title": (r.get("denominaci") or "").strip(), "place": (r.get("espai") or "").strip(),
                "url": next((u for u in links if "agenda.cultura.gencat.cat" in u), links[0] if links else ""),
                "free": r.get("gratuita") == "Sí", "source": "gencat"}
        if not item["title"]:
            continue
        if r.get("permanent") == "Sí":
            permanent.append(item)
            continue
        start = (r.get("data_inici") or "")[:10]
        end = (r.get("data_fi") or start)[:10]
        if start and end >= today.isoformat():
            item.update(start=start, end=end, time=(r.get("horari") or "").strip()[:90])
            events.append(item)
    return events, permanent


_ITEM = re.compile(
    r'content="(\d{4}-\d\d-\d\d)T(\d\d:\d\d)[^"]*"[^>]*class="date-display-(?:single|start)"'
    r'(?:(?!date-display-(?:single|start)).)*?<a href="(/agenda/[^"#?]+)"[^>]*>\s*<p>(.*?)</p>', re.S)


def parse_agenda_ajuntament(page, today):
    out = []
    for day, hhmm, path, title in _ITEM.findall(page):
        if day < today.isoformat():
            continue
        out.append({"title": html.unescape(re.sub(r"<[^>]+>", "", title)).strip(), "start": day, "end": day,
                    "time": "" if hhmm == "00:00" else hhmm, "place": "",
                    "url": "https://www.cerdanyola.cat" + path, "source": "ajuntament"})
    return out


def merge_events(*lists):
    seen, out = set(), []
    for ev in sorted((e for lst in lists for e in lst), key=lambda e: (e["start"], e.get("time", ""), e["title"])):
        key = (re.sub(r"\W+", "", ev["title"].lower()), ev["start"])
        if key not in seen:
            seen.add(key)
            out.append(ev)
    return out


def fetch_agenda(now):
    today = now.date()
    rows = socrata("rhpv-yr4f", where=f"municipi='{AGENDA_MUNICIPI}'", order="data_inici DESC", limit=200)
    gencat, permanent = parse_agenda_gencat(rows, today)
    ajuntament = []
    for page in ("", "?page=1"):
        ajuntament += parse_agenda_ajuntament(get_text("https://www.cerdanyola.cat/agenda" + page), today)
    return {"events": merge_events(gencat, ajuntament), "permanent": permanent}


# ---------- calidad del aire (XVPCA, Generalitat) ----------
def parse_air(rows):
    out = {}
    for r in sorted(rows, key=lambda r: r.get("data", ""), reverse=True):
        station, pol = r.get("nom_estacio"), r.get("contaminant")
        if pol not in POLLUTANTS or pol in out.get(station, {}):
            continue
        hours = [(i, r[f"h{i:02d}"]) for i in range(1, 25) if r.get(f"h{i:02d}") not in (None, "")]
        if not hours:
            continue
        hour, value = hours[-1]
        out.setdefault(station, {})[pol] = {"value": float(value), "date": r["data"][:10], "hour": hour}
    return out


def fetch_air(now):
    since = (now.date() - timedelta(days=2)).isoformat()
    names = ",".join(f"'{m}'" for m in AIR_MUNICIPIS)
    rows = socrata("tasf-thgu", where=f"municipi in ({names}) AND data >= '{since}T00:00:00'", limit=500)
    return parse_air(rows)


# ---------- avisos de Rodalies (Renfe GTFS-RT, CC BY 4.0) ----------
def parse_alerts(doc, now):
    ts = now.timestamp()
    seen, out = set(), []
    for ent in doc.get("entity", []):
        al = ent.get("alert", {})
        routes = {x.get("routeId", "") for x in al.get("informedEntity", [])}
        lines = sorted({ln for ln in LINES for r in routes if r.startswith("51T") and r.endswith(ln)})
        if not lines:
            continue
        periods = al.get("activePeriod") or [{}]
        if not any(int(p.get("start", 0)) <= ts <= int(p.get("end", 2 ** 62)) for p in periods):
            continue
        texts = {x.get("language") or "es": x.get("text", "").strip()
                 for x in al.get("descriptionText", {}).get("translation", []) if x.get("text")}
        key = tuple(sorted(texts.values()))
        if texts and key not in seen:
            seen.add(key)
            out.append({"lines": lines, "text": texts})
    return out


def fetch_alerts(now):
    return parse_alerts(get_json("https://gtfsrt.renfe.com/alerts.json"), now)


# ---------- equipamientos y recarga de vehículos ----------
def parse_equipments(rows):
    out = []
    for r in rows:
        cat = (r.get("categoria") or "").split("|")
        out.append({"name": (r.get("nom") or "").strip(), "cat": cat[0].strip(),
                    "sub": cat[1].strip() if len(cat) > 1 else "",
                    "address": (r.get("via") or "").strip(),
                    "cp": (r.get("cpostal") or "").zfill(5), "phone": (r.get("telefon1") or "").strip(),
                    "lat": r.get("latitud"), "lon": r.get("longitud")})
    return sorted(out, key=lambda e: (e["cat"] or "~", e["sub"], e["name"]))


def fetch_equipments(now):
    return parse_equipments(socrata("8gmd-gz7i", where="poblacio like 'Cerdanyola%'", limit=1000))


def parse_chargers(rows):
    return [{"name": (r.get("designaci_descriptiva") or "").strip(), "address": (r.get("adre_a") or "").strip(),
             "speed": r.get("tipus_velocitat") or "", "access": r.get("acces") or "",
             "operator": r.get("promotor_gestor") or "", "lat": r.get("latitud"), "lon": r.get("longitud")}
            for r in rows]


def fetch_chargers(now):
    return parse_chargers(socrata("tb2m-m33b", where="upper(municipi) like '%CERDANYOLA%'", limit=100))


# ---------- horas baratas de la luz (web hermana llum-hores) ----------
def light_url():
    if os.environ.get("LIGHT_API_URL"):
        return os.environ["LIGHT_API_URL"]
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER")
    return f"https://{owner}.github.io/llum-hores/api/v1/latest.json" if owner else ""


def parse_light(doc):
    today = (doc or {}).get("today")
    if not today:
        return None
    return {"date": today["date"], "site": doc.get("site", ""), "avg": today["avg"],
            "cheapest": {k: today["cheapest"][k] for k in ("1", "3") if k in today["cheapest"]},
            "hours": [{"start": h["start"], "label": h["label"], "price": h["price"]} for h in today["hours"]]}


def fetch_light(now, url=None):
    url = url or light_url()
    if not url:
        raise FetchError("sin URL de la web de la luz (define LIGHT_API_URL)")
    return parse_light(get_json(url))
