"""Fuentes de datos abiertos para Cerdanyola del Vallès.

Cada fuente tiene una función `parse_*` pura (probada con datos reales
guardados en tests/fixtures) y una `fetch_*` que la descarga.
"""
import bisect
import gzip
import html
import json
import math
import os
import re
import ssl
import struct
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import i18n
import tz

ROOT = Path(__file__).resolve().parent.parent
LAT, LON, ALTITUDE = 41.4913, 2.1408, 80
SOCRATA = "https://analisi.transparenciacatalunya.cat/resource/{}.json?"
AGENDA_MUNICIPI = "agenda:ubicacions/barcelona/valles-occidental/cerdanyola-del-valles"
AIR_MUNICIPIS = ("Sant Cugat del Vallès", "Montcada i Reixac", "Barberà del Vallès", "Sabadell")
POLLUTANTS = ("NO2", "O3", "PM10", "PM2.5")
LINES = ("R7", "R8")

# cerdanyola.cat no envía su certificado intermedio; los añadimos: Sectigo (hasta 2036) y,
# desde octubre de 2026, Let's Encrypt YE1 con su Root YE firmada por ISRG Root X2 (hasta 2028).
_CTX = ssl.create_default_context()
for _pem in ("sectigo-ov-r36.pem", "letsencrypt-ye1.pem"):
    _CTX.load_verify_locations(str(ROOT / "certs" / _pem))


class FetchError(Exception):
    pass


def user_agent():
    repo = os.environ.get("GITHUB_REPOSITORY", "cerdanyola-local")
    return f"cerdanyola-local/1.0 (+https://github.com/{repo})"


def get_bytes(url, tries=3, timeout=40, headers=None):
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": user_agent(), **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code < 500:
                break
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def get_text(url, tries=3, timeout=40):
    return get_bytes(url, tries, timeout).decode("utf-8")


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
# categorías de la Agenda cultural -> mismas etiquetas que usa el Ajuntament
GENCAT_CATS = {"exposicions": "Exposicions", "rutes-i-visites": "Rutes i visites", "infantil": "Infància",
               "concerts": "Música", "teatre": "Teatre i dansa", "dansa": "Teatre i dansa", "circ": "Teatre i dansa",
               "cursos": "Cursos i tallers", "conferencies": "Conferències", "cinema": "Cinema",
               "festivals-i-mostres": "Festivals", "festes": "Festes populars", "carnavals": "Festes populars",
               "sardanes": "Festes populars", "fires-i-mercats": "Fires i mercats", "gastronomia": "Hostalaria",
               "llibres-i-lletres": "Actes literaris", "nadal": "Nadal"}


def gencat_category(r):
    slug = (r.get("tags_categor_es") or "").split(",")[0].strip().rsplit("/", 1)[-1]
    return GENCAT_CATS.get(slug, slug.replace("-", " ").capitalize())


def parse_agenda_gencat(rows, today):
    events, permanent = [], []
    for r in rows:
        links = [u.strip() for u in (r.get("enlla_os") or "").split(",") if u.strip()]
        item = {"title": (r.get("denominaci") or "").strip(), "place": (r.get("espai") or "").strip(),
                "url": next((u for u in links if "agenda.cultura.gencat.cat" in u), links[0] if links else ""),
                "free": r.get("gratuita") == "Sí", "category": gencat_category(r), "source": "gencat"}
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


_ROW = re.compile(r'<(?:li|div) class="views-row[^"]*"')
_DATE = re.compile(r'content="(\d{4}-\d\d-\d\d)T(\d\d:\d\d)[^"]*" class="date-display-(single|start|end)"')
_LINK = re.compile(r'<a href="(/agenda/[^"#?]+)"[^>]*>(.*?)</a>', re.S)
_TAG = re.compile(r'href="/newsletter/[^"]+"[^>]*>([^<]+)</a>')
_LAST_PAGE = re.compile(r'pager-last"><a href="/agenda\?page=(\d+)"')


def parse_agenda_ajuntament(page, today):
    """Cada acto es un bloque views-row: fecha de inicio (y de fin, si es un rango), enlace y categoría."""
    out = []
    for block in _ROW.split(page)[1:]:
        dates, link = _DATE.findall(block), _LINK.search(block)
        if not dates or not link:
            continue
        start, hhmm, _ = dates[0]
        end = dates[-1][0] if dates[-1][2] == "end" else start
        if end < today.isoformat():
            continue
        tag = _TAG.search(block)
        out.append({"title": html.unescape(re.sub(r"<[^>]+>", "", link.group(2))).strip(), "start": start,
                    "end": end, "time": "" if hhmm == "00:00" else hhmm, "place": "",
                    "category": html.unescape(tag.group(1)).strip() if tag else "",
                    "url": "https://www.cerdanyola.cat" + link.group(1), "source": "ajuntament"})
    return out


def last_page(page):
    m = _LAST_PAGE.search(page)
    return int(m.group(1)) if m else 0


def merge_events(*lists):
    seen, out = set(), []
    for ev in sorted((e for lst in lists for e in lst), key=lambda e: (e["start"], e.get("time", ""), e["title"])):
        key = (re.sub(r"\W+", "", ev["title"].lower()), ev["start"])
        if key not in seen:
            seen.add(key)
            out.append(ev)
    return out


# Calendarios de entidades con WordPress + The Events Calendar: fuente -> (web, categoría por defecto)
TRIBE_FEEDS = {
    "blues": ("https://bluesdecerdanyola.com", "Música"),  # Festival de Blues: conciertos en bares (sept.-oct.)
    "afocer": ("https://afocer.cat", ""),  # Agrupació Foto-Cine Cerdanyola-Ripollet
}


def parse_tribe(doc, source, default_cat, today):
    out = []
    for e in doc.get("events", []):
        venue = e["venue"] if isinstance(e.get("venue"), dict) else {}
        town = (venue.get("city") or "").lower()
        if town and "cerdanyola" not in town and "bellaterra" not in town:
            continue  # AFOCER también organiza actos en Ripollet
        start, end = e["start_date"][:10], e["end_date"][:10]
        if end < today.isoformat():
            continue
        cats = [html.unescape(c.get("name", "")) for c in e.get("categories", [])]
        out.append({"title": html.unescape(e["title"]).strip(), "start": start, "end": end,
                    "time": "" if e.get("all_day") else e["start_date"][11:16],
                    "place": html.unescape(venue.get("venue") or "").strip(),
                    "category": next((c for c in cats if c in i18n.AGENDA_CATS), default_cat),
                    "url": e.get("url", ""), "source": source})
    return out


def fetch_tribe(source, today):
    site, default_cat = TRIBE_FEEDS[source]
    url = f"{site}/wp-json/tribe/events/v1/events?per_page=50&start_date={today.isoformat()}"
    return parse_tribe(get_json(url), source, default_cat, today)


# Agenda de la UAB (campus de Bellaterra). Contenido CC BY-NC: válido mientras la web no sea comercial.
UAB_AGENDA = "https://www.uab.cat/web/agenda-1345828727305.html?categoria={}"
UAB_CATS = ("1345668589727", "5000000909775")  # agenda cultural, participació estudiantil
MONTHS_CA = ("gener", "febrer", "març", "abril", "maig", "juny", "juliol", "agost",
             "setembre", "octubre", "novembre", "desembre")
_UAB_DAY = re.compile(r",\s*(\d+)\s+(?:de\s+|d[’'])(\w+)")
_UAB_LINK = re.compile(r"<h4>\s*<a href='([^']+)'>([^<]+)</a>")
_UAB_END = re.compile(r"(\d+)\s+(\w+)\.?\s+(\d{4})\s*$")


def month_ca(word):
    word = word.lower().rstrip(".")
    return next((i + 1 for i, m in enumerate(MONTHS_CA) if word and m.startswith(word)), None)


def parse_uab(page, today):
    out = []
    for chunk in page.split('<h3 class="capcalera-dia">')[1:]:
        day = _UAB_DAY.search(chunk[:200])
        if not day or not month_ca(day.group(2)):
            continue
        d, m = int(day.group(1)), month_ca(day.group(2))
        for item in chunk.split('<li class="avanc">')[1:]:
            link = _UAB_LINK.search(item)
            if not link:
                continue
            rng = re.search(r'class="data">([^<]+)<', item)
            end_m = _UAB_END.search(rng.group(1)) if rng else None
            if end_m and month_ca(end_m.group(2)):
                end = date(int(end_m.group(3)), month_ca(end_m.group(2)), int(end_m.group(1)))
                start = date(end.year - (m > end.month), m, d)
            else:  # la cabecera del día no lleva año: el próximo que encaje
                start = date(today.year, m, d)
                if start < today - timedelta(days=180):
                    start = date(today.year + 1, m, d)
                end = start
            if end < today:
                continue
            hour = re.search(r'class="hora">.*?(\d\d:\d\d)', item, re.S)
            place = re.search(r'class="lloc">(?:.*?</svg>)?\s*([^<]+?)\s*</li>', item, re.S)
            out.append({"title": html.unescape(re.sub(r"\s+", " ", link.group(2))).strip(),
                        "start": start.isoformat(), "end": end.isoformat(), "time": hour.group(1) if hour else "",
                        "place": html.unescape(place.group(1)) if place else "", "category": "",
                        "url": "https://www.uab.cat" + html.unescape(link.group(1)), "source": "uab"})
    return out


def fetch_uab(today):
    pages = [get_text(UAB_AGENDA.format(cat)) for cat in UAB_CATS]
    if not any('class="capcalera-dia"' in p for p in pages):  # «En manteniment» también responde 200
        raise FetchError("agenda UAB sin días: ¿web en mantenimiento?")
    return [e for p in pages for e in parse_uab(p, today)]


def fetch_ajuntament(today):
    first = get_text("https://www.cerdanyola.cat/agenda")
    events = parse_agenda_ajuntament(first, today)
    for n in range(1, min(last_page(first), 6) + 1):  # unas 10 fechas por página: ~1 mes
        time.sleep(10)  # el robots.txt de cerdanyola.cat pide Crawl-delay: 10
        events += parse_agenda_ajuntament(get_text(f"https://www.cerdanyola.cat/agenda?page={n}"), today)
    if not events:  # una página sin ningún acto es un cambio de la web, no un mes sin agenda
        raise FetchError("cerdanyola.cat/agenda: no se encuentra ningún acto")
    return events


def fetch_agenda(now, previous=None):
    today = now.date()
    rows = socrata("rhpv-yr4f", where=f"municipi='{AGENDA_MUNICIPI}'", order="data_inici DESC", limit=200)
    gencat, permanent = parse_agenda_gencat(rows, today)
    extra = []
    jobs = [("ajuntament", lambda: fetch_ajuntament(today)), ("uab", lambda: fetch_uab(today))] + [
        (s, lambda s=s: fetch_tribe(s, today)) for s in TRIBE_FEEDS]
    for name, job in jobs:
        try:
            extra += job()
        except Exception as exc:  # si una web cae, la agenda sigue con las demás y con sus actos ya guardados
            print(f"aviso: agenda/{name}: {exc}")
            extra += [e for e in (previous or {}).get("events", [])
                      if e["source"] == name and e["end"] >= today.isoformat()]
    return {"events": merge_events(gencat, extra), "permanent": permanent}


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


# ---------- guía de ocio (OpenStreetMap, ODbL) ----------
OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter")
LEISURE_QUERY = """[out:json][timeout:90];
area["boundary"="administrative"]["admin_level"="8"]["name"="Cerdanyola del Vallès"]->.a;
(
 nwr(area.a)["name"]["amenity"~"^(restaurant|fast_food|bar|cafe|ice_cream|pub|biergarten|nightclub|music_venue|karaoke_box|hookah_lounge|cinema|theatre|arts_centre|community_centre)$"];
 nwr(area.a)["name"]["tourism"~"^(museum|gallery|viewpoint|picnic_site|attraction)$"];
 nwr(area.a)["name"]["leisure"~"^(park|nature_reserve|playground|water_park|sports_centre|swimming_pool|stadium|fitness_centre|dance|escape_game|bowling_alley)$"];
 nwr(area.a)["name"]["historic"~"^(castle|manor|ruins|archaeological_site|monument|memorial|fort|tower|farm)$"];
 nwr(area.a)["name"]["natural"~"^(spring|peak|cave_entrance)$"];
 relation(area.a)["name"]["route"~"^(hiking|foot|bicycle|mtb)$"];
);
out center tags;"""

# grupo de la guía -> (clave OSM, valores)
LEISURE_KINDS = [
    ("nature", "leisure", ("park", "nature_reserve", "playground", "water_park")),
    ("nature", "tourism", ("viewpoint", "picnic_site")), ("nature", "natural", ("spring", "peak", "cave_entrance")),
    ("routes", "route", ("hiking", "foot", "bicycle", "mtb")),
    ("heritage", "historic", ("castle", "manor", "ruins", "archaeological_site", "monument", "memorial", "fort", "tower", "farm")),
    ("culture", "tourism", ("museum", "gallery", "attraction")),
    ("culture", "amenity", ("cinema", "theatre", "arts_centre")),
    ("culture", "leisure", ("escape_game", "bowling_alley")),
    ("community", "amenity", ("community_centre",)),
    ("eat", "amenity", ("restaurant", "fast_food")),
    ("drink", "amenity", ("bar", "cafe", "ice_cream", "biergarten")),
    ("night", "amenity", ("pub", "nightclub", "music_venue", "karaoke_box", "hookah_lounge")), ("night", "leisure", ("dance",)),
    ("sport", "leisure", ("sports_centre", "swimming_pool", "stadium", "fitness_centre")),
]
# en OSM muchas plazas pequeñas y piscinas de comunidad están marcadas como parque
_NOT_A_PARK = re.compile(r"^(\d+|plaça\b.*|parc infantil|.*comunitari.*)$", re.I)


def _web(tags):
    url = (tags.get("website") or tags.get("contact:website") or tags.get("url") or "").split(";")[0].strip()
    if url.startswith("www."):
        url = "https://" + url
    return url if url.startswith(("http://", "https://")) else ""


def parse_leisure(doc):
    out, seen = [], set()
    for el in doc.get("elements", []):
        tags = el.get("tags", {})
        if tags.get("access") in ("private", "no") or tags.get("disused") == "yes":
            continue
        kind = next(((g, tags[k]) for g, k, vals in LEISURE_KINDS if tags.get(k) in vals), None)
        name = (tags.get("name") or "").strip()
        if not kind or not name or (name.lower(), kind[1]) in seen:
            continue
        if kind[1] in ("park", "playground", "swimming_pool") and _NOT_A_PARK.match(name):
            continue
        seen.add((name.lower(), kind[1]))
        pos = el.get("center") or el
        street = " ".join(x for x in (tags.get("addr:street"), tags.get("addr:housenumber")) if x)
        km = tags.get("distance", "").replace(",", ".").removesuffix("km").strip()
        out.append({"name": name, "group": kind[0], "type": kind[1], "cuisine": tags.get("cuisine", ""),
                    "address": street, "hours": tags.get("opening_hours", ""), "web": _web(tags),
                    "phone": (tags.get("phone") or tags.get("contact:phone") or "").split(";")[0].strip(),
                    "km": km if re.fullmatch(r"\d+(\.\d+)?", km) else "", "ref": tags.get("ref", ""),
                    "lat": pos.get("lat"), "lon": pos.get("lon"), "osm": f'{el["type"]}/{el["id"]}'})
    return sorted(out, key=lambda e: (e["group"], e["name"].lower()))


def fetch_leisure(now):
    errors = []
    for url in OVERPASS:  # dos servidores: si uno está saturado, probamos el otro
        try:
            doc = json.loads(get_text(url + "?" + urllib.parse.urlencode({"data": LEISURE_QUERY}), timeout=120))
        except (FetchError, json.JSONDecodeError) as exc:
            errors.append(str(exc)[:150])
            continue
        places = parse_leisure(doc)
        if len(places) > 50:  # una respuesta casi vacía es un error del servidor, no un cambio real
            return places
        errors.append(f"{url}: solo {len(places)} lugares")
    raise FetchError(" | ".join(errors))


# ---------- más locales nocturnos (Overture Maps: Meta, BrightQuery..., CDLA Permissive 2.0) ----------
# Overture publica cada mes sus lugares en un PMTiles de 20 GB; con peticiones HTTP por rangos leemos
# solo las ~25 teselas de Cerdanyola (unos 2 MB). En OpenStreetMap faltan muchos pubs y discotecas.
OVERTURE = "https://stac.overturemaps.org/"
BOUNDARY = ROOT / "geo" / "cerdanyola.json"  # término municipal, de OpenStreetMap
NIGHT_TAXONOMY = {  # categoría de Overture -> tipo de la guía
    "dance_club": "nightclub", "salsa_club": "nightclub", "nightlife_venue": "night_venue",
    "karaoke_venue": "karaoke_box", "cocktail_bar": "cocktail_bar", "pub": "pub", "irish_pub": "pub",
    "hookah_bar": "hookah_lounge", "piano_bar": "piano_bar", "jazz_and_blues_venue": "music_venue",
    "music_venue": "music_venue",
}
# la atribución de la web cubre estas licencias; Foursquare (Apache 2.0) pediría su propio aviso
OVERTURE_LICENSES = {"CDLA-Permissive-2.0", "CC0-1.0"}
# «music_venue» también son orquestas, coros y academias: solo salas, cafés concierto...
_MUSIC_VENUE = re.compile(r"\b(sala|caf[eé]|bar|club|pub|concierto|concert|live|jazz|blues)\b", re.I)
# fuera los clubs de alterne, que Overture suele catalogar como discotecas
_NIGHT_SKIP = re.compile(r"alterne|strip|er[oòó]tic|\bsex|swinger", re.I)
_GENERIC_WORDS = {"sala", "club", "cafe", "disco", "discoteca", "lounge", "shisha", "cerdanyola", "valles",
                  "irish", "cocktail", "copes", "copas", "musical", "local", "karaoke", "cerveceria", "sant",
                  "santa", "night", "scene", "premium"}
_ADDRESS_WORDS = {"de", "del", "dels", "la", "les", "l", "d", "el", "els", "i", "carrer", "c"}


def _varint(b, i):
    v = shift = 0
    while True:
        c = b[i]
        i += 1
        v |= (c & 0x7F) << shift
        shift += 7
        if c < 0x80:
            return v, i


def _packed(b):
    out, i = [], 0
    while i < len(b):
        v, i = _varint(b, i)
        out.append(v)
    return out


def _zigzag(v):
    return (v >> 1) ^ -(v & 1)


def _pmtiles_dir(raw):
    """Directorio PMTiles v3: id de tesela, repeticiones, longitud y desplazamiento de cada entrada."""
    b = gzip.decompress(raw)
    n, i = _varint(b, 0)
    ids, runs, lens, offs = (_packed(b[i:])[k * n:(k + 1) * n] for k in range(4))
    for k in range(1, n):
        ids[k] += ids[k - 1]
    for k in range(n):  # 0 = justo detrás de la anterior
        offs[k] = offs[k - 1] + lens[k - 1] if k and offs[k] == 0 else offs[k] - 1
    return list(zip(ids, runs, lens, offs))


def _tile_id(z, x, y):
    """Número de tesela de PMTiles: teselas de los niveles anteriores + posición en la curva de Hilbert."""
    tid, n = sum(4 ** k for k in range(z)), 1 << z
    s = n >> 1
    while s:
        rx, ry = int(x & s > 0), int(y & s > 0)
        tid += s * s * ((3 * rx) ^ ry)
        if not ry:
            if rx:
                x, y = n - 1 - x, n - 1 - y
            x, y = y, x
        s >>= 1
    return tid


def _tile_xy(lon, lat, z):
    n = 1 << z
    return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)


class PMTiles:
    def __init__(self, url):
        self.url, self.dirs = url, {}
        h = self.read(0, 127)
        if h[:7] != b"PMTiles" or h[7] != 3 or h[97] != 2 or h[98] != 2 or h[99] != 1:  # v3, gzip, vectorial
            raise FetchError(f"{url}: formato PMTiles inesperado")
        self.root, self.root_len, _, _, self.leaves, _, self.tiles = struct.unpack_from("<7Q", h, 8)
        self.maxzoom = h[101]

    def read(self, offset, length):
        return get_bytes(self.url, timeout=60, headers={"Range": f"bytes={offset}-{offset + length - 1}"})

    def tile(self, z, x, y):
        tid, offset, length = _tile_id(z, x, y), self.root, self.root_len
        for _ in range(4):  # raíz y, como mucho, tres niveles de directorios hoja
            if offset not in self.dirs:
                self.dirs[offset] = _pmtiles_dir(self.read(offset, length))
            entries = self.dirs[offset]
            k = bisect.bisect_right(entries, tid, key=lambda e: e[0]) - 1
            if k < 0:
                return None
            start, run, length, offset = entries[k]
            if run:
                return gzip.decompress(self.read(self.tiles + offset, length)) if tid < start + run else None
            offset += self.leaves
        return None


def _pbf(b):
    """Campos (número, valor) de un mensaje protobuf."""
    i = 0
    while i < len(b):
        key, i = _varint(b, i)
        wire = key & 7
        if wire == 0:
            v, i = _varint(b, i)
        elif wire == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif wire in (1, 5):
            n = 8 if wire == 1 else 4
            v, i = b[i:i + n], i + n
        else:
            raise ValueError(f"protobuf: tipo {wire}")
        yield key >> 3, v


def _mvt_value(b):
    for f, v in _pbf(b):
        if f == 1:
            return v.decode("utf-8")
        if f in (2, 3):
            return struct.unpack("<f" if f == 2 else "<d", v)[0]
        if f in (4, 5):
            return v
        if f == 6:
            return _zigzag(v)
        if f == 7:
            return bool(v)
    return None


def parse_mvt(tile, z, x, y):
    """Puntos de una tesela vectorial (Mapbox Vector Tile 2): sus propiedades, más lat y lon."""
    out, n = [], 1 << z
    for f, layer in _pbf(tile):
        if f != 3:
            continue
        keys, values, features, extent = [], [], [], 4096
        for g, v in _pbf(layer):
            if g == 2:
                features.append(v)
            elif g == 3:
                keys.append(v.decode("utf-8"))
            elif g == 4:
                values.append(_mvt_value(v))
            elif g == 5:
                extent = v
        for feat in features:
            fields = dict(_pbf(feat))
            tags, geom = _packed(fields.get(2, b"")), _packed(fields.get(4, b""))
            if fields.get(3) != 1 or len(geom) < 3:  # solo puntos
                continue
            props = {keys[tags[k]]: values[tags[k + 1]] for k in range(0, len(tags) - 1, 2)}
            px, py = _zigzag(geom[1]) / extent, _zigzag(geom[2]) / extent
            props["lon"] = round((x + px) / n * 360 - 180, 6)
            props["lat"] = round(math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + py) / n)))), 6)
            out.append(props)
    return out


def boundary():
    """Segmentos del límite municipal (de OpenStreetMap; no cambia)."""
    ways = json.loads(BOUNDARY.read_text(encoding="utf-8"))["ways"]
    return [(a, b) for w in ways for a, b in zip(w, w[1:])]


def _inside(lon, lat, segments):
    inside = False
    for (x1, y1), (x2, y2) in segments:
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _words(text):
    plain = unicodedata.normalize("NFKD", (text or "").lower()).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", plain)


def _metres(a, b):
    return math.hypot((a["lon"] - b["lon"]) * 111320 * math.cos(math.radians(a["lat"])), (a["lat"] - b["lat"]) * 110540)


def same_place(a, b):
    """Mismo local con nombres algo distintos («The 1916» y «The 1916 Irish Pub», «Sala Acme» y «ACME Privée»)."""
    if a.get("lat") is None or b.get("lat") is None or _metres(a, b) > 200:
        return False
    wa, wb = _words(a["name"]), _words(b["name"])
    distinct = [{w for w in ws if len(w) >= 4 and w not in _GENERIC_WORDS} for ws in (wa, wb)]
    return bool(distinct[0] & distinct[1]) or " ".join(wa) in " ".join(wb) or " ".join(wb) in " ".join(wa)


def _address(text):
    """«Carrer De La Bona-Sort 24» -> «Carrer de la Bona-Sort 24»."""
    text = re.sub(r"(?<=\s)(De|Del|Dels|La|Les|El|Els|I)\b(?!')", lambda m: m.group(1).lower(), text.strip())
    return re.sub(r"(?<=\s)([DL])'", lambda m: m.group(1).lower() + "'", text)


def _phone(text):
    digits = re.sub(r"\D", "", text or "")
    if len(digits) == 9:
        digits = "34" + digits
    return f"+{digits[:2]} {digits[2:5]} {digits[5:8]} {digits[8:]}" if len(digits) == 11 else ""


def parse_overture_night(features, segments):
    found = []
    for p in features:
        taxonomy = json.loads(p.get("taxonomy") or "{}")
        kind = NIGHT_TAXONOMY.get(taxonomy.get("primary"))
        name = (p.get("@name") or "").strip()
        address = (json.loads(p.get("addresses") or "[]") or [{}])[0].get("freeform") or ""
        srcs = json.loads(p.get("sources") or "[]")
        status, confidence = p.get("operating_status") or "", p.get("confidence") or 0
        if (not kind or not name or not address.strip() or status.endswith("closed") or confidence < 0.5
                or "adult_entertainment_venue" in taxonomy.get("hierarchy", []) or _NIGHT_SKIP.search(name)
                or (kind == "music_venue" and not _MUSIC_VENUE.search(name))
                or any(s.get("license") not in OVERTURE_LICENSES for s in srcs)
                or not _inside(p["lon"], p["lat"], segments)):
            continue
        webs = json.loads(p.get("websites") or "[]") + json.loads(p.get("socials") or "[]")
        found.append({"name": name, "group": "night", "type": kind, "cuisine": "", "address": _address(address),
                      "hours": "", "web": next((w for w in webs if w.startswith(("http://", "https://"))
                                                and not re.search(r"goo\.gl|google\.", w)), ""),
                      "phone": _phone((json.loads(p.get("phones") or "[]") or [""])[0]), "km": "", "ref": "",
                      "lat": p["lat"], "lon": p["lon"], "osm": "", "open": status == "open", "confidence": confidence,
                      "src": sorted({s["dataset"] for s in srcs if s.get("dataset") and s["dataset"] != "Overture"})})
    # primero los que el registro mercantil da por abiertos, luego los más fiables
    found.sort(key=lambda e: (not e["open"], -e["confidence"]))
    out, addresses = [], set()
    for e in found:
        key = " ".join(w for w in _words(e["address"]) if w not in _ADDRESS_WORDS)
        # en una dirección ya cogida, los que no constan abiertos suelen ser nombres antiguos del mismo local
        if (key in addresses and not e["open"]) or any(same_place(e, o) for o in out):
            continue
        addresses.add(key)
        out.append(e)
    for e in out:
        del e["open"], e["confidence"]
    return sorted(out, key=lambda e: e["name"].lower())


def fetch_nightlife(now):
    release = get_json(OVERTURE + "catalog.json")["latest"]
    links = get_json(f"{OVERTURE}{release}/places/catalog.json")["links"]
    tiles = PMTiles(next(link["href"] for link in links if link.get("rel") == "pmtiles"))
    segments = boundary()
    lons, lats = [p[0] for s in segments for p in s], [p[1] for s in segments for p in s]
    z = tiles.maxzoom
    (x0, y0), (x1, y1) = _tile_xy(min(lons), max(lats), z), _tile_xy(max(lons), min(lats), z)
    features = []
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            tile = tiles.tile(z, x, y)
            if tile:
                features += parse_mvt(tile, z, x, y)
    places = parse_overture_night(features, segments)
    if len(places) < 5:  # un error del servidor, no un cambio real
        raise FetchError(f"Overture {release}: solo {len(places)} locales")
    return places


def merge_places(osm_places, extra):
    """La guía con los lugares de otras fuentes que aún no están en OpenStreetMap."""
    new = [e for e in extra if not any(same_place(e, p) for p in osm_places)]
    return sorted(osm_places + new, key=lambda e: (e["group"], e["name"].lower()))


# ---------- ayudas y subvenciones (BDNS, Ministerio de Hacienda; reutilización libre) ----------
BDNS = "https://www.infosubvenciones.es/bdnstrans/api/"
BDNS_QUERIES = (  # qué convocatorias pueden pedir los vecinos de Cerdanyola
    "organos=2047,4967",  # Ajuntament de Cerdanyola, Mancomunitat Cerdanyola-Ripollet-Montcada
    "organos=2859,1672,6226,720",  # Consell Comarcal del Vallès Occidental, AMB, Consorci Habitatge AMB, Diputació
    "tipoAdministracion=A&regiones=49,50&tiposBeneficiario=1,2,3",  # Generalitat: personas, entidades, pymes
    "tipoAdministracion=C&regiones=1&tiposBeneficiario=1,3",  # Estado, en toda España: personas y pymes
)
WHO = {"PERSONAS FÍSICAS QUE NO DESARROLLAN ACTIVIDAD ECONÓMICA": "people",
       "PYME Y PERSONAS FÍSICAS QUE DESARROLLAN ACTIVIDAD ECONÓMICA": "business", "GRAN EMPRESA": "business",
       "PERSONAS JURÍDICAS QUE NO DESARROLLAN ACTIVIDAD ECONÓMICA": "entities"}
# convocatorias que nadie más puede pedir: grupos municipales, convenios con una entidad concreta, ayuntamientos...
_AID_SKIP = re.compile(r"grupos? pol[ií]tic|grups? (pol[ií]tic|municipal)|caja fija|caixa fixa|^conveni|^sub\. directa|"
                       r"convocatoria instrumental|por la que se concede|per la qual es concedeix|cooperaci[oó]n? local|"
                       r"\b(ajuntaments|ayuntamientos|ens locals|entes locales|municipis|municipios)\b", re.I)
# organismos de la ciudad de Barcelona y universidades cuyas becas son para su propio alumnado (salvo la UAB)
_ORGAN_SKIP = re.compile(r"CONSORCI D'EDUCACIÓ DE BARCELONA|CONSORCI DE L'HABITATGE DE BARCELONA|"
                         r"CONSORCIO DE (LA VIVIENDA|EDUCACIÓN) DE BARCELONA|"
                         r"^(FUNDACIÓ )?UNIVERSI(?!.*AUT[OÒ]NOMA DE BARCELONA)", re.I)
_NO_TERM = re.compile(r"^\s*(sin plazo|sense termini)", re.I)
NUMBER_WORDS = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cinco": 5, "cinc": 5, "diez": 10, "deu": 10,
                "quince": 15, "quinze": 15, "veinte": 20, "vint": 20, "treinta": 30, "trenta": 30}
_SPAN = re.compile(r"\b(\d+|" + "|".join(NUMBER_WORDS) + r")\s*(?:\(\d+\)\s*)?(d[ií]as?|dies|mes(?:os|es)?)\b"
                   r"\s*(h[aàá]bils|h[áa]biles)?", re.I)
_DMY = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_D_MONTH = re.compile(r"\b(\d{1,2}) d(?:e |['’])(\w+)(?: de (\d{4}))?", re.I)
MONTHS_ES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre")
CHECK_DAYS = 30  # una convocatoria sin plazo legible se muestra este tiempo desde que se registra


def end_from_text(text, start):
    """Fecha de cierre a partir del texto libre del plazo: (fecha, ¿aproximada?) o (None, False)."""
    m = _DMY.search(text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))), False
        except ValueError:
            pass
    for m in _D_MONTH.finditer(text):
        word = m.group(2).lower()
        month = next((i + 1 for i, name in enumerate(MONTHS_ES) if name == word), None) or (
            month_ca(word) if len(word) > 3 else None)
        if month:
            try:
                return date(int(m.group(3) or start.year), month, int(m.group(1))), False
            except ValueError:
                pass
    m = _SPAN.search(text)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else NUMBER_WORDS[m.group(1).lower()]
        days = n * 30 if m.group(2).lower().startswith("mes") else -(-n * 7 // 5) if m.group(3) else n
        return start + timedelta(days=days), True
    return None, False


def aid_state(a, today):
    """('open'|'soon'|'approx'|'check', fecha) según el plazo de solicitud, o None si ya no se puede pedir."""
    start = date.fromisoformat(a["start"]) if a.get("start") else None
    end = date.fromisoformat(a["end"]) if a.get("end") else None
    if _NO_TERM.match(a.get("term") or ""):
        return None
    approx = False
    if not end:
        # sin fecha de inicio, el plazo suele empezar al publicarse el extracto, unos días después de registrarse
        base = start or date.fromisoformat(a["received"]) + timedelta(days=7)
        end, approx = end_from_text(a.get("term") or "", base)
    if start and start > today:
        return ("soon", start) if not end or end >= start else None
    if end:
        return (("approx" if approx else "open"), end) if end >= today else None
    received = date.fromisoformat(a["received"])
    return ("check", None) if (today - received).days <= CHECK_DAYS else None


def _title(s):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[0] + s[1:].lower() if s.isupper() else s


def parse_bdns_call(d, today):
    org = d.get("organo") or {}
    who = sorted({WHO[b["descripcion"]] for b in d.get("tiposBeneficiarios") or [] if b.get("descripcion") in WHO})
    lang = d.get("descripcionLeng") or ""
    return {"id": d["codigoBDNS"], "title": _title(d.get("descripcion")),
            "title_ca": _title(lang) if lang and org.get("nivel1") != "ESTADO"
            and lang.strip().lower() != (d.get("descripcion") or "").strip().lower() else "",
            "level": org.get("nivel1", ""), "region": org.get("nivel2", ""), "organ": org.get("nivel3", ""),
            "who": who, "start": d.get("fechaInicioSolicitud") or "", "end": d.get("fechaFinSolicitud") or "",
            "term": (d.get("textFin") or "").strip()[:160], "received": d.get("fechaRecepcion") or today.isoformat(),
            "budget": d.get("presupuestoTotal"), "purpose": d.get("descripcionFinalidad") or "",
            "checked": today.isoformat()}


def bdns_relevant(a):
    return bool(a["who"]) and not _AID_SKIP.search(a["title"]) and not _AID_SKIP.search(a["title_ca"]) \
        and not _ORGAN_SKIP.search(a["organ"])


def fetch_aids(now, previous=None, max_details=300):
    """Convocatorias con plazo abierto (o a punto de abrir). Guarda las ya vistas para no repetir consultas."""
    today = now.date()
    prev = previous or {}
    calls, closed = dict(prev.get("calls", {})), set(prev.get("closed", []))
    since, until = (today - timedelta(days=365)).strftime("%d/%m/%Y"), today.strftime("%d/%m/%Y")
    found = []
    for q in BDNS_QUERIES:
        for page in range(15):
            res = get_json(f"{BDNS}convocatorias/busqueda?vpd=GE&pageSize=200&page={page}&order=fechaRecepcion"
                           f"&direccion=desc&fechaDesde={since}&fechaHasta={until}&{q}")
            found += [c["numeroConvocatoria"] for c in res.get("content", [])]
            if res.get("last", True):
                break
    if not found:
        return None
    pending = [n for n in dict.fromkeys(found) if n not in closed and n not in calls]
    stale = [n for n, a in calls.items() if (today - date.fromisoformat(a["checked"])).days >= 7]
    for n in (pending + stale)[:max_details]:  # lo nuevo primero; lo pendiente sigue en la próxima ejecución
        time.sleep(0.3)
        try:
            a = parse_bdns_call(get_json(f"{BDNS}convocatorias?vpd=GE&numConv={n}"), today)
        except FetchError as exc:
            print(f"aviso: ayudas/{n}: {exc}")
            continue
        if bdns_relevant(a) and aid_state(a, today):
            calls[n] = a
        else:
            calls.pop(n, None)
            closed.add(n)
    for n in [n for n, a in calls.items() if not aid_state(a, today) or not bdns_relevant(a)]:
        del calls[n]
        closed.add(n)
    window = set(found)
    return {"calls": calls, "closed": sorted(closed & window, key=int)}


# ---------- empleo ----------
# Oposiciones y bolsas de trabajo públicas: CIDO de la Diputació de Barcelona (CC BY 4.0)
CIDO = ("https://api.diba.cat/dadesobertes/cido/v1/oposicions?filter[idEstat]=3"
        "&filter[institucio.comarca]=Vall%C3%A8s%20Occidental&page[limit]=500&sort=-maxDataPublicacioDocument")


def km_from_town(lat, lon):
    return math.hypot((lat - LAT) * 111.2, (lon - LON) * 111.2 * math.cos(math.radians(LAT)))


def parse_cido(doc, today):
    out = []
    for r in doc.get("data", []):
        a = r.get("attributes", {})
        end = a.get("dataFinalitzacio") or ""
        if end and end < today.isoformat():
            continue
        lat, lon = a.get("latitud"), a.get("longitud")
        out.append({"title": _title(a.get("titol")), "org": (a.get("institucioDesenvolupat") or "").strip(),
                    "end": end, "places": a.get("numPlaces") or 0, "pool": bool(a.get("borsaTreball")),
                    "kind": a.get("tipusPersonal") or "", "group": (a.get("grupTitulacio") or "").split(" - ")[0],
                    "km": round(km_from_town(lat, lon), 1) if lat and lon else None,
                    "url": a.get("urlCido") or a.get("accesTramit") or ""})
    return sorted(out, key=lambda j: (j["end"] or "9999", j["org"], j["title"]))


def fetch_cido(now):
    return parse_cido(get_json(CIDO), now.date())


# Ofertas de empleo del SOC (Feina Activa, Llicència oberta Catalunya): todas en un XML; filtramos por municipio
FEINA_ACTIVA = "https://feinaactiva.gencat.cat/api/offers/offers-xml"
NEAR_TOWNS = ("CERDANYOLA DEL VALLÈS", "BELLATERRA", "RIPOLLET", "MONTCADA I REIXAC", "BADIA DEL VALLÈS",
              "BARBERÀ DEL VALLÈS", "SANT CUGAT DEL VALLÈS")
OFFER_DAYS = 60  # las ofertas más antiguas suelen estar ya cubiertas aunque sigan publicadas


def parse_offers(xml_text, today):
    out = []
    for ad in ET.fromstring(xml_text).iter("ad"):
        get = lambda k: (ad.findtext(k) or "").strip()  # noqa: E731
        city = get("city").upper()
        if city not in NEAR_TOWNS or get("status") not in ("", "PUBLISHED"):
            continue
        try:
            day = date(*map(int, reversed(get("date").split("/"))))
        except (TypeError, ValueError):
            continue
        if (today - day).days > OFFER_DAYS:
            continue
        lo, hi = get("salaryMin"), get("salaryMax")
        out.append({"title": _title(get("title")), "company": get("company"), "town": city, "date": day.isoformat(),
                    "contract": get("contract"), "hours": get("workingHours"),
                    "salary": [int(float(x)) for x in (lo, hi) if re.fullmatch(r"\d+(\.\d+)?", x)],
                    "url": get("url")})
    out.sort(key=lambda j: j["date"], reverse=True)  # las más nuevas primero, Cerdanyola antes que los vecinos
    return sorted(out, key=lambda j: NEAR_TOWNS.index(j["town"]))


def fetch_offers(now):
    offers = parse_offers(get_text(FEINA_ACTIVA, timeout=120), now.date())
    return offers or None  # un XML sin ninguna oferta cercana es un fallo de la fuente, no la realidad


# ---------- carburantes (Ministerio para la Transición Ecológica; reutilización libre citando la fuente) ----------
FUEL_API = ("https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/"
            "EstacionesTerrestres/FiltroMunicipio/{}")
FUEL_TOWNS = {931: "Cerdanyola del Vallès", 1046: "Ripollet", 994: "Montcada i Reixac", 876: "Badia del Vallès",
              880: "Barberà del Vallès", 1067: "Sant Cugat del Vallès"}
FUELS = {"g95": "Precio Gasolina 95 E5", "diesel": "Precio Gasoleo A"}


def parse_fuel(doc, town):
    out = []
    for e in doc.get("ListaEESSPrecio", []):
        if e.get("Tipo Venta") != "P":  # «R»: venta restringida a socios
            continue
        prices = {k: float(e[v].replace(",", ".")) for k, v in FUELS.items() if e.get(v)}
        if prices:
            out.append({"name": (e.get("Rótulo") or "").strip(), "address": i18n.organ_name(e.get("Dirección") or ""),
                        "hours": e.get("Horario") or "", "town": town, "prices": prices,
                        "lat": (e.get("Latitud") or "").replace(",", "."),
                        "lon": (e.get("Longitud (WGS84)") or "").replace(",", ".")})
    return out


def fetch_fuel(now):
    stations, stamp = [], ""
    for code, town in FUEL_TOWNS.items():
        doc = json.loads(get_text(FUEL_API.format(code)))
        stamp = stamp or doc.get("Fecha", "")
        stations += parse_fuel(doc, town)
    return {"updated": stamp, "stations": stations} if stations else None


# ---------- inversiones y licitaciones públicas (Plataforma de serveis de contractació pública, Llicència oberta Catalunya) ----------
# Publican aquí el Ajuntament, la Generalitat, el AMB, la UAB y los centros de investigación del campus;
# las obras del Estado (sincrotrón ALBA, Adif...) van a la plataforma estatal y no salen.
CONTRACTS_PLACE = ("(starts_with(codi_ine10,'08266') OR nom_organ like '%Cerdanyola del Vall%' OR nom_organ like '%Bellaterra%'"
                   " OR lloc_execucio like '%Cerdanyola del Vall%' OR lloc_execucio like '%Bellaterra%')")
CONTRACT_DATES = ("data_publicacio_futura", "data_publicacio_consulta", "data_publicacio_previ", "data_publicacio_anunci",
                  "data_publicacio_avaluacio", "data_publicacio_adjudicacio", "data_publicacio_formalitzacio",
                  "data_publicacio_anul")
CONTRACT_DAYS = 400
AWARDED = ("Adjudicació", "Formalització", "Execució")
_CONTRACT_CODE = re.compile(r"^\s*(?:(?:contr|consu)\s*[-‐]?\s*)?\d+/\d{4}\s*[-–:]*\s*", re.I)
_CIF = re.compile(r"^[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]$")
# las personas físicas llegan con el NIF tapado; también algunas empresas, que se reconocen por la forma jurídica
_LEGAL_FORM = re.compile(r"\b(S\.?L\.?U?|S\.?A\.?U?|SCCL|SLP|SLL|S\.?R\.?L|UTE|GmbH|AG|KG|Inc|LLC|Ltd|Limited|B\.?V|"
                         r"Co|Corp|Fundaci[oó]n?|Associaci[oó]|Asociaci[oó]n|Cooperativa)\b", re.I)


def _float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def companies_only(ids, names):
    """Adjudicatarios que son empresas o entidades: los nombres de particulares no se publican en la web."""
    out = []
    for ident, name in zip((ids or "").split("||"), (names or "").split("||")):
        name = re.sub(r"\s+", " ", name).strip()
        if name and (_CIF.match(ident.strip()) or _LEGAL_FORM.search(name)):
            out.append(name)
    return out


def parse_contracts(rows):
    """Un elemento por expediente (los lotes van juntos), con la fase de su publicación más reciente."""
    groups = {}
    for r in rows:
        groups.setdefault((r.get("codi_organ") or r.get("nom_organ"), r.get("codi_expedient") or r.get("id_intern")), []).append(r)
    out = []
    for (organ, exp), rs in groups.items():
        live = [r for r in rs if r.get("fase_publicacio") != "Anul·lació"] or rs
        last = max(live, key=lambda r: max(r.get(k) or "" for k in CONTRACT_DATES))
        dates = sorted({(r.get(k) or "")[:10] for r in live for k in CONTRACT_DATES} - {""})
        lots = {r.get("numero_lot") or "": r for r in rs}
        # suma de los lotes: de un expediente de toda Cataluña solo cuentan los lotes que se hacen aquí
        budget = (sum(_float(r.get("pressupost_licitacio_sense")) or 0 for r in lots.values())
                  or _float(last.get("pressupost_licitacio_sense_1")) or _float(last.get("valor_estimat_contracte")) or 0)
        awarded = sum(_float(r.get("import_adjudicacio_sense")) or 0 for r in live if r.get("fase_publicacio") in AWARDED)
        phase = last.get("fase_publicacio") or ""
        title = _title(_CONTRACT_CODE.sub("", last.get("denominacio") or last.get("objecte_contracte") or ""))
        if not title or not dates:
            continue
        out.append({"id": f"{organ}/{exp}", "title": title[:240], "organ": (last.get("nom_organ") or "").strip(),
                    "type": last.get("tipus_contracte") or "", "phase": phase,
                    "amount": round(awarded if phase in AWARDED and awarded else budget, 2),
                    "deadline": max((r.get("termini_presentacio_ofertes") or "")[:16] for r in live),
                    "date": dates[-1], "url": (last.get("enllac_publicacio") or {}).get("url", ""),
                    "lots": len([k for k in lots if k]),
                    "winners": list(dict.fromkeys(w for r in live for w in companies_only(
                        r.get("identificacio_adjudicatari"), r.get("denominacio_adjudicatari"))))})
    return sorted(out, key=lambda c: (c["date"], c["id"]), reverse=True)


def fetch_contracts(now):
    since = (now.date() - timedelta(days=CONTRACT_DAYS)).isoformat()
    recent = " OR ".join(f"{k} >= '{since}'" for k in CONTRACT_DATES)
    rows = socrata("ybgg-dgi6", limit=5000, where=(
        f"{CONTRACTS_PLACE} AND ({recent} OR termini_presentacio_ofertes >= '{now.date().isoformat()}')"
        " AND fase_publicacio != 'Publicació agregada de contractes'"))  # los contratos menores, por trimestres
    return parse_contracts(rows) or None


# ---------- empresas: altas, traslados y capital (BORME, Agencia Estatal BOE; reutilización libre citando la fuente) ----------
# Sección A del BORME de Barcelona, un día cada vez. Solo se guardan empresas: ni administradores ni direcciones.
BORME = "https://www.boe.es/datosabiertos/api/borme/sumario/{}"
BORME_PROVINCE = "BARCELONA"
BORME_DAYS = 365  # la primera vez se lee un año: así se conocen las empresas que ya tienen domicilio aquí
BORME_KEEP = 120  # días de actos guardados
BORME_MAX_DAYS = 40  # días leídos por ejecución: el año inicial se completa en unas pocas
_BORME_ENTRY = re.compile(r'<h5 class="articulo">\s*(\d+)\s*-\s*(.*?)</h5>\s*<p class="parrafo">(.*?)</p>', re.S)
_HERE = re.compile(r"^(CERDANYOLA|BELLATERRA)\b")  # «SANT JULIA DE CERDANYOLA» es otro municipio
_TOWN = re.compile(r"\(([^()]+)\)\.(?:\s|$)")  # el municipio cierra el domicilio: «CL MAJOR 5 (CERDANYOLA DEL VALLES).»
_SHEET = re.compile(r"\bH (B \d+)")  # hoja registral: identifica a la empresa en el Registro de Barcelona


def _euros(text, label, start=0):
    m = re.compile(re.escape(label) + r"\s*([\d.]+,\d+) Euros").search(text, start)
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def _town_after(text, marker):
    i = text.find(marker)
    m = _TOWN.search(text, i) if i >= 0 else None
    return m.group(1).strip().upper() if m else ""


def _activity(text):
    m = re.search(r"Objeto social:\s*(.*?)\s*Domicilio:", text, re.S)
    if not m:
        return ""
    main = re.search(r"ACTIVIDAD PRINCIPAL:\s*\d+\s*/\s*([^.]+)", m.group(1))
    s = (main.group(1) if main else m.group(1)).strip().rstrip(".")
    return _title(s if len(s) <= 120 else s[:117].rsplit(" ", 1)[0] + "…")


def parse_borme(page, day, url, known):
    """Actos de empresas de Cerdanyola en una página del BORME. Actualiza `known` (hoja registral -> nombre):
    los traslados, ampliaciones y cierres solo se reconocen de empresas que ya se sabe que están aquí."""
    out = []
    for num, name, text in _BORME_ENTRY.findall(page):
        name = re.sub(r"(?<!\.[A-Z])\.$", "", html.unescape(name).strip())  # «X SL.» -> «X SL», pero «X S.L.» queda
        text = html.unescape(re.sub(r"<[^>]+>", "", text))
        sheet = _SHEET.search(text)
        if not sheet:
            continue
        sheet = sheet.group(1)
        base = {"date": day, "name": name, "url": url}

        def add(kind, **kw):
            out.append({"id": f"{day}-{num}-{kind}", "kind": kind, **base, **kw})
        if "Constitución." in text and _HERE.match(_town_after(text, "Domicilio:")):
            add("new", capital=_euros(text, "Capital:"), activity=_activity(text))
            known[sheet] = name
        moved = _town_after(text, "Cambio de domicilio social.")
        if moved and _HERE.match(moved) and sheet not in known:
            add("moved_in")
            known[sheet] = name
        elif moved and not _HERE.match(moved) and sheet in known:
            add("moved_out", town=moved)
            del known[sheet]
        if sheet not in known:
            continue
        i = text.find("Ampliación de capital.")
        if i >= 0:
            add("capital", capital=_euros(text, "Capital:", i), total=_euros(text, "Resultante Suscrito:", i))
        i = text.find("Reducción de capital.")
        if i >= 0:
            add("capital_down", capital=_euros(text, "Importe reducción:", i), total=_euros(text, "Resultante Suscrito:", i))
        if "Extinción." in text or "Disolución." in text:
            add("closed")
            if "Extinción." in text:
                del known[sheet]
    return out


def _as_list(x):
    return x if isinstance(x, list) else [x] if x else []


def borme_pages(day):
    """[(url, html)] de la sección A de Barcelona de un día; None si ese día no hubo BORME."""
    try:
        doc = json.loads(get_bytes(BORME.format(day.strftime("%Y%m%d")), headers={"Accept": "application/json"}))
    except FetchError as exc:
        if "404" in str(exc):  # fines de semana y festivos
            return None
        raise
    urls = [it["url_html"] for d in _as_list(doc["data"]["sumario"]["diario"]) for s in _as_list(d.get("seccion"))
            if s.get("codigo") == "A" for it in _as_list(s.get("item")) if it.get("titulo") == BORME_PROVINCE]
    return [(u, get_text(u)) for u in urls]


def fetch_companies(now, previous=None):
    today, prev = now.date(), previous or {}
    known, events = dict(prev.get("known", {})), list(prev.get("events", []))
    last = date.fromisoformat(prev["last"]) if prev.get("last") else today - timedelta(days=BORME_DAYS)
    done = 0
    while done < BORME_MAX_DAYS and last < today:
        day = last + timedelta(days=1)
        try:
            pages = borme_pages(day)
        except FetchError:
            if done:
                break  # lo leído hasta aquí se guarda; el resto, en la próxima ejecución
            raise
        if pages is None and day == today:
            break  # el de hoy aún no ha salido: se vuelve a mirar en la próxima ejecución
        for url, page in pages or []:
            events += parse_borme(page, day.isoformat(), url, known)
        last, done = day, done + 1
        time.sleep(1)
    keep = (today - timedelta(days=BORME_KEEP)).isoformat()
    events = sorted({e["id"]: e for e in events if e["date"] >= keep}.values(), key=lambda e: e["id"], reverse=True)
    return {"since": prev.get("since") or (today - timedelta(days=BORME_DAYS - 1)).isoformat(), "last": last.isoformat(),
            "known": dict(sorted(known.items())), "events": events}


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
