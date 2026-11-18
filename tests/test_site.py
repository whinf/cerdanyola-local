import gzip
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zlib
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

    def test_alerts_only_our_lines(self):
        alerts = S.parse_alerts(fixture("renfe_alerts.json"), NOW)
        self.assertEqual(len(alerts), 3)
        self.assertTrue(all(set(a["lines"]) <= {"R4", "R7", "R8"} for a in alerts))
        strike = next(a for a in alerts if a["text"]["ca"].startswith("Per causes alienes"))
        self.assertEqual(strike["lines"], ["R4", "R7", "R8"])  # aviso general, sin nombrar líneas
        self.assertTrue(strike["text"]["es"].startswith("Por causas ajenas"))  # las dos llegan marcadas «es»
        # Noviembre: Renfe etiqueta con toda la red unas obras de la R2 en Castelldefels y las de Montcada (R7)
        later = S.parse_alerts(fixture("renfe_alerts.json"), tz.to_madrid(tz.parse_iso("2026-11-18T19:00:00+01:00")))
        texts = " ".join(a["text"]["ca"] for a in later)
        self.assertNotIn("Castelldefels", texts)
        montcada = [a for a in later if "Montcada Bifurcació" in a["text"]["ca"]]
        self.assertEqual([a["lines"] for a in montcada], [["R7"]])  # una vez, por la entidad más concreta

    def test_notices(self):
        xml, day = (FIX / "actualitat.rss").read_text(encoding="utf-8"), date(2026, 11, 18)
        got = S.parse_notices(xml, day)
        self.assertEqual([n["date"] for n in got], ["2026-11-13"])  # de 10 noticias, la única que es un aviso
        self.assertIn("afectacions al trànsit", got[0]["title"])
        self.assertEqual(set(got[0]), {"title", "url", "date"})  # ni cuerpo ni autor: solo se enlaza
        old = [{"title": "Tall de l'avinguda X", "url": "https://www.cerdanyola.cat/actualitat/x", "date": "2026-11-15"},
               {"title": "Vell", "url": "https://www.cerdanyola.cat/actualitat/y", "date": "2026-11-01"}]
        self.assertEqual([n["date"] for n in S.parse_notices(xml, day, old)], ["2026-11-15", "2026-11-13"])
        self.assertEqual(S.parse_notices(xml, date(2026, 11, 25)), [])  # caducan a los 7 días
        with self.assertRaises(S.FetchError):
            S.parse_notices("<rss><channel></channel></rss>", day)
        self.assertIsNone(S._NOTICE_WORDS.search(S._plain("Taller intergeneracional: fils de futur")))  # «taller» no es «tall»
        self.assertTrue(S._NOTICE_WORDS.search(S._plain("Talls de trànsit per les obres del carrer Sol")))

    def test_pdf_reader(self):
        cmap = b"1 beginbfrange\n<0001> <0003> <0041>\nendbfrange\n1 beginbfchar\n<0004> <00E000640027>\nendbfchar"
        content = zlib.compress(b"BT /F1 12 Tf 1 0 0 -1 10 20 Tm [<00010002>-5<0003>] TJ 1 0 0 -1 50 20 Tm <0004> Tj ET")
        pdf = (b"%PDF-1.7\n1 0 obj\n<< /Type /Page /Contents 2 0 R /Resources << /Font << /F1 3 0 R >> >> >>\nendobj\n"
               b"2 0 obj\n<< /Filter /FlateDecode /Length " + str(len(content)).encode() + b" >>\nstream\n" + content +
               b"\nendstream\nendobj\n3 0 obj\n<< /Type /Font /ToUnicode 4 0 R >>\nendobj\n"
               b"4 0 obj\n<< /Length " + str(len(cmap)).encode() + b" >>\nstream\n" + cmap + b"\nendstream\nendobj\n")
        self.assertEqual(S.pdf_runs(pdf), [(10.0, 20.0, "ABC"), (50.0, 20.0, "àd'")])
        for bad in (b"no es un pdf", b"%PDF-1.7 /Encrypt 5 0 R", b"%PDF-1.7\n1 0 obj\n<< /Type /Page >>\nendobj\n"):
            with self.assertRaises(S.FetchError):
                S.pdf_runs(bad)

    def test_pharmacies(self):
        page = fixture("farmacies.html")
        directory = S.parse_pharmacy_directory(page)
        self.assertEqual(len(directory), 29)
        self.assertEqual(directory[1], {"id": "rovira", "name": "Farmàcia Rovira", "address": "Passeig Cordelles, 64",
                                        "town": "Cerdanyola", "phone": "935 921 399"})
        self.assertEqual(sum(p["town"] == "Ripollet" for p in directory), 12)
        self.assertTrue(S.pharmacy_pdf_link(page).endswith("/sites/default/files/farmacies_de_guardia_novembre_2026_1.pdf"))
        with self.assertRaises(S.FetchError):
            S.parse_pharmacy_directory("<table><tr><td>Farmàcia X</td><td>Carrer Y</td><td>935 000 000</td></tr></table>")
        pdf = (FIX / "farmacies_guardia_2026-11.pdf").read_bytes()
        runs = S.pdf_runs(pdf)
        month, days, extra = S.parse_pharmacy_roster(runs, directory)
        self.assertEqual((month, list(days)), ("2026-11", [str(n) for n in range(1, 31)]))
        self.assertEqual(days["1"], {"day": "rovira", "night": "nunna"})  # fin de semana: dos turnos
        self.assertEqual(days["2"], {"all": "la-farigola"})
        self.assertEqual(days["11"], {"day": "rovira", "night": "hidalgo-valls"})
        self.assertEqual(days["13"], {"all": "l-auditori"})  # «L’AUDITORI», con apóstrofo tipográfico
        self.assertEqual(days["24"], {"all": "alvarez"})  # no «Álvarez Pereiro»
        self.assertEqual(days["17"], {"all": "j-selva"})  # la de Ripollet, no «C. Selva»
        self.assertEqual(extra, {"origen": {"name": "Farmàcia Origen", "town": "Cerdanyola", "address": "Avda. Catalunya 17"}})
        # Ante cualquier duda, error: es preferible no enseñar el turno a enseñar uno equivocado.
        doubts = ([r for r in runs if r[2].strip() != "18"],  # falta un día
                  [(x, y, text.replace("NOVEMBRE", "DESEMBRE")) for x, y, text in runs],  # 30 días para un mes de 31
                  [(x, y, text.replace("21 a 9 hores", "22 a 8 hores")) for x, y, text in runs],  # cambian los horarios
                  [(x, y, text.replace("RIPOLLET", "SABADELL")) for x, y, text in runs])  # municipio desconocido
        for changed in doubts:
            with self.assertRaises(S.FetchError):
                S.parse_pharmacy_roster(changed, directory)
        with self.assertRaises(S.FetchError):  # demasiadas farmacias fuera del directorio: ha cambiado el formato
            S.parse_pharmacy_roster(runs, directory[:12])

        now = tz.to_madrid(tz.parse_iso("2026-11-18T19:30:00+01:00"))
        with mock.patch.object(S, "_cat_get", side_effect=lambda url, binary=False: pdf if binary else page):
            got = S.fetch_pharmacy(now)
        self.assertEqual((list(got["rosters"]), len(got["directory"])), (["2026-11"], 29))

        def down(url, binary=False):
            if binary:
                raise S.FetchError("timeout")
            return page
        with mock.patch.object(S, "_cat_get", side_effect=down):  # sin red para el PDF: vale el calendario guardado
            self.assertEqual(S.fetch_pharmacy(now, got)["rosters"], got["rosters"])
        with mock.patch.object(S, "_cat_get", side_effect=lambda url, binary=False: b"%PDF-1.7 roto" if binary else page):
            broken = S.fetch_pharmacy(now, got)  # hay un PDF nuevo que no se entiende: fuera el calendario del mes
        self.assertEqual((broken["rosters"], len(broken["directory"])), ({}, 29))

        cfg = {"site_name": "x", "site_url": "https://example.github.io/cerdanyola-local"}

        def site(iso):
            return Site(cfg, {"pharmacy": {"fetched": iso, "data": got}}, "unused", tz.to_madrid(tz.parse_iso(iso)))
        early = site("2026-11-08T08:30:00+01:00").pharmacy_shifts()  # domingo antes de las 9: sigue la noche del sábado
        self.assertEqual([(kind, p["id"]) for _, _, kind, p in early[:3]],
                         [("night", "caelles"), ("day", "rovira"), ("night", "teruel")])
        self.assertEqual((early[0][0].isoformat(), early[0][1].isoformat()),
                         ("2026-11-07T21:00:00+01:00", "2026-11-08T09:00:00+01:00"))
        block = site("2026-11-18T19:30:00+01:00").pharmacy_block("ca")
        self.assertIn("Farmàcia Sánchez", block)
        self.assertIn('data-from="2026-11-18T09:00+01:00" data-to="2026-11-19T09:00+01:00" data-hide-past', block)
        self.assertIn("data-shifts-empty hidden", block)
        self.assertIn('href="tel:936923184"', block)
        self.assertEqual(site("2026-12-01T08:00:00+01:00").pharmacy_shifts()[0][3]["id"], "sant-andreu")  # hasta las 9 del día 1
        gone = site("2026-12-01T10:00:00+01:00").pharmacy_block("es")  # diciembre aún sin calendario: solo el enlace oficial
        self.assertNotIn('class="events shifts"', gone)
        self.assertIn("web del Ayuntamiento", gone)
        self.assertNotIn("data-shifts-empty hidden", gone)
        page_ca = site("2026-11-18T19:30:00+01:00").pharmacy_page("ca")
        self.assertIn("Guàrdies de novembre de 2026", page_ca)
        self.assertIn("Farmàcia Origen", page_ca)
        self.assertEqual(page_ca.count("<tr data-from="), 30)
        strip = site("2026-11-18T19:30:00+01:00").today_strip("ca")
        self.assertIn("Guàrdia: Sánchez", strip)
        self.assertIn("data-shift-chip=", strip)

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

    def test_pick_window(self):
        fest = {"months": [10, 11], "from": "10-20", "until": "11-15"}
        self.assertEqual([render.pick_live(fest, d) for d in (date(2026, 10, 19), date(2026, 10, 20), date(2026, 11, 15),
                                                              date(2026, 11, 18))], [False, True, True, False])
        xmas = {"from": "12-15", "until": "01-06"}  # cruza el cambio de año
        self.assertEqual([render.pick_live(xmas, d) for d in (date(2026, 12, 14), date(2026, 12, 31), date(2027, 1, 6),
                                                              date(2027, 1, 7))], [False, True, True, False])
        self.assertTrue(render.pick_live({}, date(2026, 5, 1)))
        self.assertFalse(render.pick_live({"months": [10]}, date(2026, 5, 1)))

    def test_started_events_and_freshness(self):
        cfg = {"site_name": "x", "site_url": "https://example.github.io/cerdanyola-local"}
        today = NOW.date().isoformat()  # NOW = 18:16
        events = [{"title": "Matí", "start": today, "time": "10:00", "source": "uab"},
                  {"title": "Vespre", "start": today, "time": "20 h", "source": "gencat"},
                  {"title": "Sense hora", "start": today, "time": "tot el dia", "source": "uab"},
                  {"title": "Llarg", "start": today, "end": "2026-10-30", "time": "10:00", "source": "uab"}]
        old = "2026-10-18T09:00:00+02:00"  # más de 26 h antes de NOW
        site = Site(cfg, {"agenda": {"fetched": NOW.isoformat(), "data": {"events": events}},
                          "alerts": {"fetched": old, "data": []}}, "unused", NOW)
        self.assertEqual([site.started(e) for e in events], [True, False, False, False])
        self.assertEqual(render.event_start(events[1]).isoformat(), f"{today}T20:00:00+02:00")
        self.assertEqual([e["title"] for e in site.upcoming()], ["Vespre", "Sense hora", "Llarg"])
        done = site.event_item("ca", events[0])
        self.assertIn('class="started"', done)
        self.assertIn('<span class="tier t3 on">Ja ha començat</span>', done)
        later = site.event_item("ca", events[1])
        self.assertIn(f'data-start="{today}T20:00+02:00"', later)
        self.assertIn('class="tier t3 on" hidden', later)
        self.assertNotIn("data-start", site.event_item("ca", events[3]))  # varios días: no «empieza» hoy
        self.assertNotIn("Matí", site.agenda_preview("ca"))
        self.assertIn('data-upcoming="6"', site.agenda_preview("ca"))
        self.assertIn('class="stale">', site.stamp("ca", "agenda", "alerts"))  # manda la fuente más antigua
        self.assertIn('class="stale" hidden>', site.stamp("ca", "agenda"))
        self.assertEqual(site.stamp("ca", "weather"), "")

    def test_light_tip(self):
        cfg = {"site_name": "x", "site_url": "https://example.github.io/cerdanyola-local"}

        def block(hour):
            slot = {"avg_eur_kwh": 0.07, "label": f"{hour:02d}:00–{hour + 3:02d}:00", "start": f"2026-10-20T{hour:02d}:00:00+02:00"}
            light = {"date": NOW.date().isoformat(), "cheapest": {"1": slot, "3": slot}}
            return Site(cfg, {"light": {"fetched": NOW.isoformat(), "data": light}}, "unused", NOW).light("es")
        self.assertIn("tarifa regulada (PVPC)", block(3))
        self.assertNotIn("energía solar", block(3))  # de madrugada no hay sol
        self.assertIn("energía solar", block(13))

    def test_filter_tags(self):
        self.assertEqual(render.aid_topics({"title": "Ayudas al alquiler para jóvenes", "purpose": "Otras"}), ["housing", "family"])
        self.assertEqual(render.aid_topics({"title": "Subvencions a l'agricultura", "purpose": "Cultura"}), ["culture"])  # no «cultur» suelto
        self.assertEqual(render.aid_topics({"title": "Premio X", "title_ca": None, "purpose": "Educación"}), ["study", "culture"])
        self.assertEqual(render.aid_topics({"title": "Convocatoria genérica"}), [])
        self.assertEqual(render.job_tags({"contract": "Contracte laboral indefinit", "hours": "Jornada parcial matí (15 hores)"}),
                         ["indef", "part"])
        self.assertEqual(render.job_tags({"contract": "Contracte laboral temporal (6 mesos)", "hours": "Jornada completa"}),
                         ["temp", "full"])
        cfg = {"site_name": "Cerdanyola Avui", "site_url": "https://example.github.io/x", "owner": {"email": "a@example.com"}}
        site = Site(cfg, {}, "unused", NOW)
        self.assertIn('href="mailto:a@example.com?subject=Cerdanyola%20Avui%3A%20sugerencia"', site.suggest("es"))
        self.assertEqual(Site({"site_name": "x", "site_url": "https://example.github.io/x"}, {}, "unused", NOW).suggest("es"), "")
        bar = site.filter_bar("ca", [("a", "A")], [("b", "B")])
        self.assertIn("data-filter hidden", bar)  # sin JS no se ve
        self.assertIn('data-filter-tag="b" data-filter-group="1"', bar)

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
            "pharmacy": {"source": S.PHARMACY_URL, "directory": S.parse_pharmacy_directory(fixture("farmacies.html")),
                         "rosters": {}},
            "notices": [{"title": "Talls de trànsit al centre", "url": "https://www.cerdanyola.cat/actualitat/talls",
                         "date": "2026-10-19"}],
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
            self.assertNotIn('rel="canonical"', offline)  # no es la portada: ni canonical ni chip activo
            self.assertNotIn('aria-current="page"', offline)
            self.assertIn('rel="canonical" href="https://example.github.io/cerdanyola-local/ca/"', home)
            self.assertIn("/static/now.js", home)
            self.assertIn('og:image', (out / "index.html").read_text(encoding="utf-8"))
            self.assertIn("Rodalies R4, R7 i R8", home)
            self.assertIn('class="note fresh" data-fetched=', home)
            self.assertLess(home.index('class="today"'), home.index('id="weather"'))  # franja «hoy» arriba del todo
            self.assertLess(home.index('class="quick"'), home.index('id="transport"'))
            self.assertIn("data-today-events=", home)
            for page in (aids, jobs, (out / "ca/agenda/index.html").read_text(encoding="utf-8")):
                self.assertIn("/static/filter.js", page)
                self.assertIn("data-filter-scope", page)
                self.assertIn("data-filter-empty hidden", page)
            self.assertIn('data-filter-tag="family"', aids)
            self.assertIn('data-filter-tag="indef"', jobs)
            self.assertIn("data-count>(", jobs)
            self.assertNotIn("/static/filter.js", home)
            pharmacies = (out / "ca/farmacies/index.html").read_text(encoding="utf-8")
            self.assertIn("Farmàcia Rovira", pharmacies)  # sin calendario del mes queda el directorio...
            self.assertIn("no podem llegir amb seguretat", pharmacies)  # ...y el enlace oficial
            self.assertIn('href="#i-pill"', home)
            sos_ca = (out / "ca/emergencies/index.html").read_text(encoding="utf-8")
            self.assertIn('id="pharmacy"', sos_ca)
            self.assertIn("Talls de trànsit al centre", home)
            self.assertIn("/ca/farmacies/</loc>", (out / "sitemap.xml").read_text(encoding="utf-8"))
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
        self.assertNotIn("data-visits", pages["ca"])  # sin visits_url no hay contador
        self.assertNotIn("challenges.cloudflare.com", pages["ca"])
        self.assertIn('aria-current="page"', pages["en"])
        self.assertIn("Community board", pages["en"])

    def test_board_page_with_worker(self):
        cfg = {"site_name": "Cerdanyola Avui", "site_url": "https://example.github.io/cerdanyola-local",
               "board_api_url": "https://board.example.workers.dev/", "turnstile_site_key": "1x00000000000000000000AA",
               "visits_url": "https://board.example.workers.dev/hit?site=cer"}
        data = {"board": {"fetched": NOW.isoformat(), "data": {"posts": [self.POST]}}}
        page = self.build(cfg, data)["es"]
        self.assertIn('data-api="https://board.example.workers.dev"', page)
        self.assertIn("static/board.js", page)
        self.assertIn('data-visits="https://board.example.workers.dev/hit?site=cer" data-text="Visitas: {today} hoy', page)
        self.assertIn("challenges.cloudflare.com/turnstile", page)
        self.assertIn("Bici &lt;script&gt;alert(1)&lt;/script&gt;", page)  # título escapado
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("secreto@example.com", page)
        self.assertIn('id="p-abc123def456"', page)
        self.assertIn("Recogida en el centro.", page)
        self.assertIn('href="#i-tag"', page)
        self.assertIn("publicado el 21 de octubre", page)  # 1761000000 = 21/10/2025 00:40 en Madrid
        self.assertIn("<\\/", page)  # el JSON de textos escapa «</»

    def test_social(self):
        feed = (FIX / "youtube_feed.xml").read_text(encoding="utf-8")
        videos = S.parse_youtube(feed, "propera-parada", NOW.date())
        self.assertEqual([v["id"] for v in videos], ["WgyShGeo76U", "M61WQAPUto4", "veodYaaoP34", "_DGggN6rFg4"])
        self.assertEqual((videos[0]["views"], videos[0]["published"], videos[0]["short"]), (1364, "2026-07-09", True))
        self.assertFalse(videos[1]["short"])
        self.assertEqual(S.parse_youtube(feed, "x", date(2028, 1, 1)), [])  # los vídeos viejos no se guardan
        with self.assertRaises(S.FetchError):
            S.parse_youtube("<html>", "x", NOW.date())
        profiles = S.load_social()
        self.assertEqual(len({p["id"] for p in profiles}), len(profiles))
        for p in profiles:
            self.assertIn(p["group"], render.SOCIAL_GROUPS)
            self.assertEqual(set(p["desc"]), set(i18n.LANGS))
            self.assertTrue(p["links"] and all(u.startswith("https://") for u in p["links"].values()))
            date.fromisoformat(p["checked"])
        cfg = {"site_name": "Cerdanyola Avui", "site_url": "https://example.github.io/cerdanyola-local"}
        evil = {"id": "abcdefghijk", "title": "<b>Hola</b>", "published": "2026-10-01", "channel": "propera-parada", "short": False, "views": 37826}
        old = dict(evil, id="oldoldoldol", published="2025-01-01", views=10 ** 6)
        other = dict(evil, id="otherchanne", channel="no-existe", views=10 ** 6)
        data = {"social": {"fetched": NOW.isoformat(), "data": {"videos": videos + [evil, old, other]}}}
        with tempfile.TemporaryDirectory() as tmp:
            out = Site(cfg, data, tmp, NOW).build()
            page = (out / "es/redes/index.html").read_text(encoding="utf-8")
            home = (out / "es/index.html").read_text(encoding="utf-8")
            self.assertIn("redes/", (out / "sitemap.xml").read_text(encoding="utf-8"))
        self.assertIn("&lt;b&gt;Hola&lt;/b&gt;", page)
        self.assertIn("37.826 visualizaciones", page)
        self.assertIn('href="https://www.youtube.com/watch?v=abcdefghijk"', page)
        self.assertIn('href="https://www.youtube.com/shorts/WgyShGeo76U"', page)
        self.assertEqual(page.count("i.ytimg.com/vi/"), render.VIDEOS_PER_CHANNEL)  # tope por canal
        for hidden in ("oldoldoldol", "otherchanne", "M61WQAPUto4"):
            self.assertNotIn(hidden, page)
        self.assertIn("https://www.instagram.com/totcerdanyola/", page)
        self.assertIn('aria-current="page">Redes</a>', page)
        self.assertIn("Lo más visto en las redes", home)
        with tempfile.TemporaryDirectory() as tmp:  # sin datos de YouTube queda el directorio
            out = Site(cfg, {}, tmp, NOW).build()
            page = (out / "ca/xarxes/index.html").read_text(encoding="utf-8")
            self.assertNotIn("El més vist a les xarxes", (out / "ca/index.html").read_text(encoding="utf-8"))
        self.assertNotIn("ytimg", page)
        self.assertIn("A qui seguir", page)

    def test_board_home_count(self):
        cfg = {"site_name": "Cerdanyola Avui", "site_url": "https://example.github.io/cerdanyola-local", "board_api_url": "https://b.example"}
        data = {"board": {"fetched": NOW.isoformat(), "data": {"posts": [self.POST]}}}
        with tempfile.TemporaryDirectory() as tmp:
            out = Site(cfg, data, tmp, NOW).build()
            self.assertIn("1 anuncis actius", (out / "ca/index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
