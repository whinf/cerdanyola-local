import gzip
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from unittest import mock
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import i18n  # noqa: E402
import render  # noqa: E402
import sources as S  # noqa: E402
import tz  # noqa: E402
from render import Site  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"
NOW = tz.to_madrid(tz.parse_iso("2026-10-20T18:16:00+02:00"))


def fixture(name):
    text = (FIX / name).read_text(encoding="utf-8")
    return text if name.endswith(".html") else json.loads(text)


class TestSources(unittest.TestCase):
    def test_weather(self):
        w = S.parse_weather(fixture("metno.json"), NOW)
        self.assertEqual(w["now"]["temp"], 18.0)
        self.assertEqual(w["days"][0]["date"], "2026-10-20")
        self.assertEqual(len(w["days"]), 6)
        self.assertEqual(i18n.sky("ca", w["days"][2]["symbol"]), ("cloudy", "Ennuvolat"))

    def test_agenda(self):
        gencat, permanent = S.parse_agenda_gencat(fixture("agenda.json"), NOW.date())
        self.assertEqual([e["title"] for e in gencat], ["Simposi sobre Montserrat Torrent"])
        self.assertEqual(len(permanent), 5)
        page = fixture("ajunt_agenda.html")
        city = S.parse_agenda_ajuntament(page, NOW.date())
        self.assertEqual(S.last_page(page), 3)
        expo = next(e for e in city if e["title"].startswith("Exposició 'Miquel"))  # empezó antes, sigue abierta
        self.assertEqual((expo["start"], expo["end"]), ("2026-10-20", "2026-10-31"))
        party = next(e for e in city if e["title"] == "Castahalloween a Canaletes")
        self.assertEqual((party["start"], party["time"], party["category"]), ("2026-10-31", "17:30", "Festes populars"))
        self.assertTrue(render.festive(party))
        self.assertFalse(render.festive(expo))
        later = S.merge_events(S.parse_agenda_ajuntament(page, date(2026, 11, 6)))
        self.assertEqual(len(later), 6)  # solo quedan los rangos que siguen abiertos (sin duplicados)
        merged = S.merge_events(gencat, city, city)
        self.assertEqual(len(merged), len({(e["title"], e["start"]) for e in gencat + city}))

    def test_agenda_survives_town_site_down(self):
        city = S.parse_agenda_ajuntament(fixture("ajunt_agenda.html"), NOW.date())
        down = mock.Mock(side_effect=S.FetchError("cerdanyola.cat: 404"))
        uab = S.parse_uab(fixture("uab_agenda.html"), NOW.date())
        maintenance = "<html><h1>En manteniment</h1></html>"
        with mock.patch.object(S, "socrata", return_value=fixture("agenda.json")), \
                mock.patch.object(S, "fetch_ajuntament", down), mock.patch.object(S, "get_text", return_value=maintenance), \
                mock.patch.object(S, "fetch_tribe", return_value=[]):
            ag = S.fetch_agenda(NOW, {"events": city + uab})
        titles = [e["title"] for e in ag["events"]]
        self.assertIn("Castahalloween a Canaletes", titles)  # del Ajuntament, guardado
        self.assertIn(uab[1]["title"], titles)  # de la UAB, guardado: su web responde 200 con un aviso
        self.assertIn("Simposi sobre Montserrat Torrent", titles)  # de la Generalitat, nuevo

    def test_uab_and_entities(self):
        uab = S.parse_uab(fixture("uab_agenda.html"), NOW.date())
        lliure = next(e for e in uab if e["title"].startswith("Teatre Lliure"))
        self.assertEqual((lliure["start"], lliure["end"]), ("2026-10-22", "2026-10-24"))
        self.assertEqual((uab[0]["start"], uab[0]["end"]), ("2026-10-08", "2026-10-30"))  # exposició «08 - 30 oct.»
        self.assertEqual(uab[1]["time"], "11:00")
        self.assertTrue(all(e["url"].startswith("https://www.uab.cat/web/") for e in uab))
        self.assertEqual([S.month_ca(m) for m in ("gen.", "juny", "jul.", "ag.", "d’octubre"[2:])], [1, 6, 7, 8, 10])
        blues = S.parse_tribe(fixture("tribe_blues.json"), "blues", "Música", date(2026, 10, 1))
        self.assertEqual((blues[0]["title"], blues[0]["place"], blues[0]["time"]), ("MENPHIS TRAIN", "Cal Pintxo", "20:30"))
        self.assertTrue(render.festive(blues[0]))
        afocer = S.parse_tribe(fixture("tribe_afocer.json"), "afocer", "", NOW.date())
        self.assertEqual(len(afocer), 7)  # los 2 actos de Ripollet quedan fuera

    def test_leisure(self):
        places = S.parse_leisure(fixture("osm.json"))
        names = {p["name"] for p in places}
        self.assertIn("Castell de Sant Marçal", names)
        self.assertIn("Sender del Vallès Natural", names)
        self.assertFalse({"96", "Plaça Castanyer", "Piscina Comunitaria"} & names)
        for p in places:
            self.assertIn(p["group"], i18n.LEISURE_GROUPS)
            self.assertIn(p["type"], i18n.PLACE_TYPES)
            self.assertTrue(p["web"] == "" or p["web"].startswith(("http://", "https://")))
        self.assertEqual(i18n.hours("ca", "Mo-Fr 08:00-20:00; Su off"), "dl-dv 08:00-20:00; dg tancat")
        self.assertEqual(i18n.cuisine("es", "regional;pizza"), "cocina tradicional, pizza")

    def test_nightlife(self):
        self.assertEqual([S._tile_id(0, 0, 0)] + [S._tile_id(1, x, y) for x, y in ((0, 0), (0, 1), (1, 1), (1, 0))],
                         [0, 1, 2, 3, 4])  # ejemplos de la especificación de PMTiles
        tile = gzip.decompress((FIX / "overture_14_8288_6113.mvt.gz").read_bytes())
        features = S.parse_mvt(tile, 14, 8288, 6113)
        self.assertEqual(len(features), 265)
        segments = S.boundary()
        places = S.parse_overture_night(features, segments)
        self.assertEqual([p["name"] for p in places], ["Sala Acme"])  # «ACME Privée», al lado, es el mismo local
        acme = places[0]
        self.assertEqual((acme["type"], acme["address"], acme["phone"], acme["src"]),
                         ("nightclub", "Carrer de Portugal 33", "+34 686 146 964", ["BrightQuery"]))

        def venue(name, address, status="", confidence=0.9, primary="dance_club", lon=2.137, lat=41.49):
            return {"@name": name, "operating_status": status, "confidence": confidence, "lon": lon, "lat": lat,
                    "taxonomy": json.dumps({"primary": primary, "hierarchy": ["arts_and_entertainment", primary]}),
                    "addresses": json.dumps([{"freeform": address}]),
                    "sources": json.dumps([{"dataset": "meta", "license": "CDLA-Permissive-2.0"}])}
        fake = [venue("Nou Nom", "Carrer De Can Mitjans 4", "open"), venue("Nom Antic", "Carrer de Can Mitjans, 4"),
                venue("Night Swinger", "Carrer Del Bosc Tancat 5", "open"), venue("Tancat", "Carrer Major 1", "permanently_closed"),
                venue("Coral Polifònica", "Carrer Major 2", primary="music_venue"), venue("Fora", "Carrer Major 3", lon=2.3),
                venue("Sala Rock", "Carrer Major 4", primary="music_venue")]
        self.assertEqual([p["name"] for p in S.parse_overture_night(fake, segments)], ["Nou Nom", "Sala Rock"])
        osm = [p for p in S.parse_leisure(fixture("osm.json")) if p["name"] == "The 1916"]
        pub = dict(osm[0], name="The 1916 Irish Pub", lat=osm[0]["lat"] + 0.0005, osm="", src=["meta"])
        self.assertEqual(S.merge_places(osm, [pub, acme]), [acme, osm[0]])

    def test_air(self):
        air = S.parse_air(fixture("air.json"))
        self.assertEqual(air["Sabadell"]["PM2.5"], {"value": 1.0, "date": "2026-10-20", "hour": 4})
        self.assertEqual(i18n.aq_level("NO2", 41), 1)
        self.assertEqual(i18n.aq_level("PM10", 500), 5)

    def test_alerts_only_r7_r8(self):
        alerts = S.parse_alerts(fixture("renfe_alerts.json"), NOW)
        self.assertEqual(len(alerts), 3)
        self.assertTrue(all(set(a["lines"]) <= {"R7", "R8"} for a in alerts))

    def test_aids(self):
        today = NOW.date()
        calls = {a["id"]: a for a in (S.parse_bdns_call(d, today) for d in fixture("bdns_calls.json"))}
        states = {n: (S.aid_state(a, today) or (None,))[0] for n, a in calls.items() if S.bdns_relevant(a)}
        self.assertEqual(states, {"933847": "open", "936187": "soon", "933143": "check", "922783": "open",
                                  "936968": "approx", "910930": "open"})
        self.assertFalse(S.bdns_relevant(calls["906102"]))  # grupo municipal
        self.assertFalse(S.bdns_relevant(calls["921706"]))  # Consorci de l'Habitatge de la ciudad de Barcelona
        self.assertIsNone(S.aid_state(calls["934569"], today))  # «Sense termini de presentació»
        self.assertEqual(S.aid_state(calls["922783"], today), ("open", date(2026, 12, 31)))  # fecha en el texto
        self.assertEqual(calls["933847"]["who"], ["people"])
        start = date(2026, 10, 1)
        self.assertEqual(S.end_from_text("15 Dies Hàbils", start), (date(2026, 10, 22), True))
        self.assertEqual(S.end_from_text("Diez (10) días hábiles", start), (date(2026, 10, 15), True))
        self.assertEqual(S.end_from_text("fins al 15 d’octubre", start), (date(2026, 10, 15), False))
        self.assertEqual(S.end_from_text("Indicado en la convocatoria", start), (None, False))
        self.assertEqual(S.end_from_text("del 01/10/2026 al 31/10/2026", start), (date(2026, 10, 31), False))
        self.assertEqual(S.end_from_text("fins al 15 de gener", date(2026, 12, 1)), (date(2027, 1, 15), False))
        self.assertEqual(i18n.organ_name("AGÈNCIA DE GESTIÓ D'AJUTS (AGAUR)"), "Agència de Gestió d'Ajuts (AGAUR)")
        self.assertEqual(i18n.fmt_money("ca", 2750000), "2.750.000 €")

    def test_fetch_aids_reuses_cache(self):
        details = {d["codigoBDNS"]: d for d in fixture("bdns_calls.json")}
        asked = []

        def fake(url):
            if "busqueda" in url:
                return {"content": [{"numeroConvocatoria": n} for n in details], "last": True}
            asked.append(url.rsplit("=", 1)[1])
            return details[asked[-1]]

        with mock.patch.object(S, "get_json", fake), mock.patch.object(S.time, "sleep"):
            first = S.fetch_aids(NOW)
            self.assertEqual(set(first["calls"]), {"933847", "936187", "933143", "922783", "936968", "910930"})
            self.assertEqual(first["closed"], ["906102", "921706", "934569"])
            asked.clear()
            again = S.fetch_aids(NOW, first)
        self.assertEqual(asked, [])  # nada nuevo ni caducado: ninguna consulta de detalle
        self.assertEqual(again, first)

    def test_jobs_and_fuel(self):
        public = S.parse_cido(fixture("cido.json"), NOW.date())
        town = [j for j in public if j["org"] == "Ajuntament de Cerdanyola del Vallès"]
        self.assertEqual(len(town), 3)
        self.assertTrue(all(j["km"] < 1 and j["url"].startswith("https://cido.diba.cat/") for j in town))
        offers = S.parse_offers((FIX / "feina_activa.xml").read_text(encoding="utf-8"), NOW.date())
        self.assertEqual([j["town"] for j in offers], ["CERDANYOLA DEL VALLÈS"] * 4 + ["RIPOLLET"] * 2)  # sin Calella ni las viejas
        self.assertEqual(offers[0]["date"], max(j["date"] for j in offers[:4]))
        fuel = S.parse_fuel(fixture("fuel_931.json"), "Cerdanyola del Vallès")
        self.assertEqual(len(fuel), 10)
        self.assertTrue(all(1 < s["prices"]["g95"] < 3 for s in fuel))

    def test_contracts(self):
        cs = S.parse_contracts(fixture("contracts.json"))
        by = lambda words: next(c for c in cs if c["title"].startswith(words))  # noqa: E731
        clean = by("Serveis de neteja dels edificis")  # «CONTR-59/2025 Serveis...»: sin el código del expediente
        self.assertEqual((clean["lots"], clean["phase"], round(clean["amount"])), (4, "Formalització", 11805133))
        self.assertEqual(clean["winners"], ["Multiserveis NDAVANT S.L", "ACCIONA FACILITY SERVICES, SA"])
        self.assertEqual(by("La prestació del servei de les unitats")["amount"], 884192.4)  # solo el lote de Cerdanyola
        self.assertEqual(by("Contracte del servei de gestió")["winners"], [])  # un particular: su nombre no sale
        self.assertEqual(len(by("Acord Marc per al subministrament")["winners"]), 5)  # «A||B||C» en cada lote
        self.assertEqual(by("Subministrament de contenidors higiènics")["deadline"], "2026-10-28T14:00")
        self.assertEqual(S.companies_only("*** 3757 **||B12345678", "Pascual López||Obres Vallès SL"), ["Obres Vallès SL"])
        self.assertEqual(i18n.fmt_big("ca", 49950920.77), "50,0 M€")
        self.assertEqual(i18n.fmt_big("en", 1050000), "€1.1m")

    def test_borme(self):
        page = (FIX / "borme_bcn.html").read_text(encoding="utf-8")
        known = {"B 542552": "BINDI BOOKS S.L.", "B 284195": "TIMOSA SL", "B 635310": "ARKE RNM S.L."}
        events = {e["name"]: e for e in S.parse_borme(page, "2026-10-23", "https://www.boe.es/b", known)}
        self.assertEqual({n: e["kind"] for n, e in events.items()}, {
            "JX PEOPLE & INVESTMENTS S.L.": "new", "SIMAFRO TRADING S.L.": "new", "MZA BARCINO MEAT S.L.": "moved_in",
            "BINDI BOOKS S.L.": "capital", "TIMOSA SL": "capital_down", "ARKE RNM S.L.": "closed"})  # nada de Sant Cugat
        self.assertEqual((events["BINDI BOOKS S.L."]["capital"], events["BINDI BOOKS S.L."]["total"]), (25000.0, 65000.0))
        self.assertEqual(events["JX PEOPLE & INVESTMENTS S.L."]["activity"], "Actividades de sociedades holding")
        self.assertNotIn("LLAURADO", json.dumps(list(events.values())))  # ni administradores ni direcciones
        self.assertEqual(set(known), {"B 542552", "B 284195", "B 665157", "B 665177", "B 550397"})  # ARKE, extinguida

    def test_fetch_companies(self):
        sumario = json.dumps(fixture("borme_sumario.json")).encode()
        page = (FIX / "borme_bcn.html").read_text(encoding="utf-8")
        asked = []

        def fake(url, **kw):
            asked.append(url[-8:])
            if url.endswith(("20261024", "20261025")):  # sábado, y el domingo de hoy
                raise S.FetchError(f"{url}: HTTP Error 404: Not Found")
            return sumario
        sunday = tz.to_madrid(tz.parse_iso("2026-10-25T09:00:00+01:00"))
        prev = {"since": "2025-10-26", "last": "2026-10-22", "known": {}, "events": []}
        with mock.patch.object(S, "get_bytes", fake), mock.patch.object(S, "get_text", return_value=page), \
                mock.patch.object(S.time, "sleep"):
            first = S.fetch_companies(sunday, prev)
            self.assertEqual(asked, ["20261023", "20261024", "20261025"])
            self.assertEqual((first["last"], len(first["events"]), len(first["known"])), ("2026-10-24", 3, 3))
            asked.clear()
            self.assertEqual(S.fetch_companies(sunday, first), first)
            self.assertEqual(asked, ["20261025"])
        down = mock.Mock(side_effect=S.FetchError("boe.es: HTTP Error 503"))
        with mock.patch.object(S, "get_bytes", down), self.assertRaises(S.FetchError):
            S.fetch_companies(sunday, prev)

    def test_directory(self):
        eq = S.parse_equipments(fixture("equip.json"))
        self.assertEqual(len(eq), 224)
        self.assertTrue(all(len(e["cp"]) == 5 for e in eq))
        self.assertEqual(len(S.parse_chargers(fixture("ev.json"))), 3)
        for cat in {e["cat"] for e in eq}:
            self.assertIn(cat, i18n.CATEGORIES)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.links += [a[k] for k in ("href", "src") if a.get(k)]


class TestSite(unittest.TestCase):
    def test_week_picks_rotate(self):
        items = [{"id": f"p{i}"} for i in range(10)]
        mon, sun, next_mon = date(2026, 10, 26), date(2026, 11, 1), date(2026, 11, 2)
        self.assertEqual(render.week_picks(items, mon, 3), render.week_picks(items, sun, 3))
        this, after = render.week_picks(items, mon, 3), render.week_picks(items, next_mon, 3)
        self.assertEqual(len(this), 3)
        self.assertFalse({p["id"] for p in this} & {p["id"] for p in after})
        self.assertEqual(render.week_picks([], mon, 3), [])
        self.assertEqual(len(render.week_picks(items[:2], mon, 3)), 2)

    def test_curated_picks(self):
        picks = render.load_picks()
        self.assertGreaterEqual(sum(p["kind"] == "food" for p in picks), 2 * render.PICKS_PER_WEEK["food"])
        self.assertGreaterEqual(sum(p["kind"] == "experience" for p in picks), 2 * render.PICKS_PER_WEEK["experience"])
        self.assertEqual(len({p["id"] for p in picks}), len(picks))
        for p in picks:
            for lang in i18n.LANGS:
                self.assertTrue(p["why"][lang] and p["tags"][lang], p["id"])
            self.assertTrue(not p.get("url") or p["url"].startswith(("https://", "http://")), p["id"])
            self.assertTrue(set(p.get("months", [1])) <= set(range(1, 13)), p["id"])
            date.fromisoformat(p["checked"])

    def test_events_split_and_weekend(self):
        cfg = {"site_name": "x", "site_url": "https://example.github.io/cerdanyola-local"}
        events = [{"title": "Acabat", "start": "2026-10-10", "end": "2026-10-12", "source": "uab"},
                  {"title": "En marxa", "start": "2026-10-18", "end": "2026-10-25", "source": "uab"},
                  {"title": "Dissabte", "start": "2026-10-24", "end": "2026-10-24", "source": "uab"},
                  {"title": "<script>x</script>", "start": "2026-10-21", "url": "javascript:alert(1)", "source": "uab"}]
        site = Site(cfg, {"agenda": {"fetched": NOW.isoformat(), "data": {"events": events}}}, "unused", NOW)
        upcoming, ongoing = site.events_split()
        self.assertEqual([e["title"] for e in ongoing], ["En marxa"])  # el acabado no sale
        self.assertEqual(sorted(e["title"] for e in site.weekend_events()), ["Dissabte", "En marxa"])
        item = site.event_item("ca", next(e for e in upcoming if e.get("url")))
        self.assertNotIn("javascript:", item)
        self.assertIn("&lt;script&gt;", item)
        self.assertIn("\\u003c", render.jsonld_text({"name": "</script>"}))

    def test_same_keys(self):
        for lang in i18n.LANGS:
            self.assertEqual(set(i18n.STRINGS[lang]), set(i18n.STRINGS["ca"]), lang)

    def test_build_and_links(self):
        gencat, permanent = S.parse_agenda_gencat(fixture("agenda.json"), NOW.date())
        data = {
            "weather": S.parse_weather(fixture("metno.json"), NOW),
            "agenda": {"events": S.merge_events(gencat, S.parse_agenda_ajuntament(fixture("ajunt_agenda.html"), NOW.date())),
                       "permanent": permanent},
            "air": S.parse_air(fixture("air.json")),
            "alerts": S.parse_alerts(fixture("renfe_alerts.json"), NOW),
            "equipments": S.parse_equipments(fixture("equip.json")),
            "chargers": S.parse_chargers(fixture("ev.json")),
            "leisure": S.parse_leisure(fixture("osm.json")),
            "nightlife": S.parse_overture_night(S.parse_mvt(gzip.decompress(
                (FIX / "overture_14_8288_6113.mvt.gz").read_bytes()), 14, 8288, 6113), S.boundary()),
            "aids": {"calls": {d["codigoBDNS"]: S.parse_bdns_call(d, NOW.date()) for d in fixture("bdns_calls.json")}},
            "cido": S.parse_cido(fixture("cido.json"), NOW.date()),
            "offers": S.parse_offers((FIX / "feina_activa.xml").read_text(encoding="utf-8"), NOW.date()),
            "fuel": {"updated": "20/10/2026 18:00:00", "stations": S.parse_fuel(fixture("fuel_931.json"), "Cerdanyola del Vallès")},
            "contracts": S.parse_contracts(fixture("contracts.json")),
            "companies": {"since": "2025-10-21", "last": "2026-10-19", "known": {}, "events": S.parse_borme(
                (FIX / "borme_bcn.html").read_text(encoding="utf-8"), "2026-10-19", "https://www.boe.es/b", {})},
        }
        cfg = {"site_name": "Cerdanyola Avui", "site_url": "https://example.github.io/cerdanyola-local"}
        with tempfile.TemporaryDirectory() as tmp:
            out = Site(cfg, {k: {"fetched": NOW.isoformat(), "data": v} for k, v in data.items()}, tmp, NOW).build()
            home = (out / "ca/index.html").read_text(encoding="utf-8")
            self.assertIn("Castahalloween a Canaletes", home)
            self.assertIn("Guia d'oci", home)
            leisure = (out / "es/ocio/index.html").read_text(encoding="utf-8")
            self.assertIn("The 1916", leisure)
            self.assertIn('href="#i-party-popper"', leisure)  # icono de fiesta
            self.assertIn('aria-current="page"', leisure)  # chip de sección activo
            self.assertIn('class="sections"', leisure)
            self.assertIn("OpenStreetMap", leisure)
            self.assertIn("Sala Acme", leisure)
            self.assertIn("datos de BrightQuery, licencia", leisure)
            self.assertIn("R7", home)
            self.assertIn("Ajudes que pots demanar ara", home)
            aids = (out / "es/ayudas/index.html").read_text(encoding="utf-8")
            self.assertIn("ayudas a la infancia", aids.lower())
            self.assertIn("convocatorias/933847", aids)
            self.assertNotIn("grupos politicos", aids.lower())
            self.assertIn('id="weekend"', leisure)
            ics = (out / "agenda.ics").read_bytes().decode("utf-8")
            self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n"))
            self.assertIn("SUMMARY:Castahalloween a Canaletes", ics)
            self.assertIn("DTSTART:20261031T163000Z", ics)  # 17:30 en Madrid, ya en horario de invierno (UTC+1)
            self.assertTrue(all(len(x.encode()) <= 75 for x in ics.split("\r\n")))
            jobs = (out / "ca/feina/index.html").read_text(encoding="utf-8")
            self.assertIn("cido.diba.cat/oposicions/", jobs)
            self.assertIn("feinaactiva.gencat.cat/search/offers/detail/", jobs)
            self.assertIn("Carburant més barat avui", home)
            self.assertIn('id="fuel"', (out / "es/equipamientos/index.html").read_text(encoding="utf-8"))
            self.assertIn("Inversions i empreses", home)
            invest = (out / "ca/inversions/index.html").read_text(encoding="utf-8")
            for text in ("Passeig dels Gorgs", "50,0 M€", "ofertes fins al 28 d'octubre", "Anunci previ",
                         "JX PEOPLE &amp; INVESTMENTS S.L.", "feed.xml", "no és cap recomanació"):
                self.assertIn(text, invest)
            self.assertNotIn("Pascual", invest)
            self.assertNotIn("Servei de telefonia", invest)  # anul·lat
            self.assertIn("€74.4m", (out / "en/investment/index.html").read_text(encoding="utf-8"))
            atom = "{http://www.w3.org/2005/Atom}"
            feed = ET.parse(out / "es/inversiones/feed.xml").getroot()
            titles = [e.findtext(atom + "title") for e in feed.iter(atom + "entry")]
            self.assertIn("En licitación · 23.071 € · Subministrament de contenidors higiènics", titles)
            self.assertIn("Empresas nuevas · JX PEOPLE & INVESTMENTS S.L.", titles)
            self.assertIn("Estalvia a Cerdanyola", home)
            save = (out / "es/ahorra/index.html").read_text(encoding="utf-8")
            self.assertIn("La gasolinera más barata", save)
            self.assertIn("subastas.boe.es", save)
            self.assertIn("Recomanat aquesta setmana", home)
            picks_en = (out / "en/recommendations/index.html").read_text(encoding="utf-8")
            self.assertIn("Where to eat</h2>", picks_en)
            self.assertIn('href="#i-utensils"', picks_en)
            self.assertTrue((out / "static/style.css").exists())
            self.assertFalse((out / "static/base.css").exists())
            sw = (out / "sw.js").read_text(encoding="utf-8")  # en la raíz, versionado por build
            self.assertIn('"cerdanyola-20', sw)
            self.assertNotIn("__BUILD__", sw)
            self.assertFalse((out / "static/sw.js").exists())
            mans = {lg: json.loads((out / f"static/manifest.{lg}.webmanifest").read_text(encoding="utf-8")) for lg in i18n.LANGS}
            self.assertEqual({m["id"] for m in mans.values()}, {"/cerdanyola-local/"})  # una sola app
            self.assertEqual(mans["es"]["start_url"], "/cerdanyola-local/es/")
            self.assertEqual(mans["en"]["display"], "standalone")
            self.assertEqual(mans["ca"]["shortcuts"][2]["url"], "/cerdanyola-local/ca/emergencies/")
            self.assertIn("/static/manifest.en.webmanifest", picks_en)
            self.assertIn('data-sw="/cerdanyola-local/sw.js"', picks_en)
            self.assertIn("data-install", picks_en)
            self.assertIn('href="#i-smartphone"', home)
            offline = (out / "offline.html").read_text(encoding="utf-8")
            self.assertIn("noindex", offline)
            self.assertIn("Sense connexió", offline)
            sos = (out / "en/emergencies/index.html").read_text(encoding="utf-8")
            self.assertIn('href="tel:112"', sos)
            self.assertIn("Policia Local", sos)
            broken = []
            for page in out.rglob("*.html"):
                p = Links()
                p.feed(page.read_text(encoding="utf-8"))
                for link in p.links:
                    link = link.split("#")[0].replace("https://example.github.io", "")
                    if link.startswith("/cerdanyola-local/"):
                        target = out / link[len("/cerdanyola-local/"):]
                        target = target / "index.html" if link.endswith("/") else target
                        if not target.exists():
                            broken.append(f"{page.relative_to(out)} -> {link}")
            self.assertEqual(broken, [])


class TestBoard(unittest.TestCase):
    POST = {"id": "abc123def456", "cat": "deal", "lang": "es", "title": "Bici <script>alert(1)</script>",
            "body": "Bici de paseo, poco uso.\nRecogida en el centro.", "name": "Marta", "contact": "Telegram @marta",
            "price": "40 €", "created": 1761000000, "expires": 1764888000, "email": "secreto@example.com"}

    def test_parse_board(self):
        parsed = S.parse_board({"posts": [self.POST, {"id": "x"}, "basura"]})
        self.assertEqual(len(parsed["posts"]), 1)
        self.assertNotIn("email", parsed["posts"][0])  # nunca llega a la web estática
        self.assertEqual(parsed["posts"][0]["price"], "40 €")
        with self.assertRaises(S.FetchError):
            S.parse_board({"error": "x"})

    def build(self, cfg, data=None):
        with tempfile.TemporaryDirectory() as tmp:
            out = Site(cfg, data or {}, tmp, NOW).build()
            return {lg: (out / lg / i18n.t(lg, "slug_board") / "index.html").read_text(encoding="utf-8") for lg in i18n.LANGS}

    def test_board_page_without_worker(self):
        pages = self.build({"site_name": "Cerdanyola Avui", "site_url": "https://example.github.io/cerdanyola-local"})
        self.assertIn("encara no està en marxa", pages["ca"])
        self.assertNotIn("board.js", pages["ca"])
        self.assertNotIn("challenges.cloudflare.com", pages["ca"])
        self.assertIn('aria-current="page"', pages["en"])
        self.assertIn("Community board", pages["en"])

    def test_board_page_with_worker(self):
        cfg = {"site_name": "Cerdanyola Avui", "site_url": "https://example.github.io/cerdanyola-local",
               "board_api_url": "https://board.example.workers.dev/", "turnstile_site_key": "1x00000000000000000000AA"}
        data = {"board": {"fetched": NOW.isoformat(), "data": {"posts": [self.POST]}}}
        page = self.build(cfg, data)["es"]
        self.assertIn('data-api="https://board.example.workers.dev"', page)
        self.assertIn("static/board.js", page)
        self.assertIn("challenges.cloudflare.com/turnstile", page)
        self.assertIn("Bici &lt;script&gt;alert(1)&lt;/script&gt;", page)  # título escapado
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("secreto@example.com", page)
        self.assertIn('id="p-abc123def456"', page)
        self.assertIn("Recogida en el centro.", page)
        self.assertIn('href="#i-tag"', page)
        self.assertIn("publicado el 21 de octubre", page)  # 1761000000 = 21/10/2025 00:40 en Madrid
        self.assertIn("<\\/", page)  # el JSON de textos escapa «</»

    def test_board_home_count(self):
        cfg = {"site_name": "Cerdanyola Avui", "site_url": "https://example.github.io/cerdanyola-local", "board_api_url": "https://b.example"}
        data = {"board": {"fetched": NOW.isoformat(), "data": {"posts": [self.POST]}}}
        with tempfile.TemporaryDirectory() as tmp:
            out = Site(cfg, data, tmp, NOW).build()
            self.assertIn("1 anuncis actius", (out / "ca/index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
