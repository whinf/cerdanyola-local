"""Fuentes de datos abiertos para Cerdanyola del Vallès.

Cada fuente tiene una función `parse_*` pura (probada con datos reales
guardados en tests/fixtures) y una `fetch_*` que la descarga.
"""
import html
import json
import math
import os
import re
import ssl
import time
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
    return [e for cat in UAB_CATS for e in parse_uab(get_text(UAB_AGENDA.format(cat)), today)]


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
    try:
        ajuntament = fetch_ajuntament(today)
    except FetchError as exc:  # si la web municipal cae, seguimos con sus actos ya guardados
        print(f"aviso: agenda/ajuntament: {exc}")
        ajuntament = [e for e in (previous or {}).get("events", [])
                      if e["source"] == "ajuntament" and e["end"] >= today.isoformat()]
    extra = []
    jobs = [("uab", lambda: fetch_uab(today))] + [(s, lambda s=s: fetch_tribe(s, today)) for s in TRIBE_FEEDS]
    for name, job in jobs:
        try:
            extra += job()
        except Exception as exc:  # fuentes secundarias: si una falla, la agenda sigue con las demás
            print(f"aviso: agenda/{name}: {exc}")
    return {"events": merge_events(gencat, ajuntament, extra), "permanent": permanent}


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
 nwr(area.a)["name"]["amenity"~"^(restaurant|fast_food|bar|cafe|ice_cream|pub|biergarten|nightclub|cinema|theatre|arts_centre|community_centre)$"];
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
    ("night", "amenity", ("pub", "nightclub")), ("night", "leisure", ("dance",)),
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
