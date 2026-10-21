import json
import sys
import tempfile
import unittest
from datetime import date
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
        self.assertEqual(i18n.sky("ca", w["days"][2]["symbol"]), ("☁️", "Ennuvolat"))

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

    def test_air(self):
        air = S.parse_air(fixture("air.json"))
        self.assertEqual(air["Sabadell"]["PM2.5"], {"value": 1.0, "date": "2026-10-20", "hour": 4})
        self.assertEqual(i18n.aq_level("NO2", 41), 1)
        self.assertEqual(i18n.aq_level("PM10", 500), 5)

    def test_alerts_only_r7_r8(self):
        alerts = S.parse_alerts(fixture("renfe_alerts.json"), NOW)
        self.assertEqual(len(alerts), 3)
        self.assertTrue(all(set(a["lines"]) <= {"R7", "R8"} for a in alerts))

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
        }
        cfg = {"site_name": "Cerdanyola Avui", "site_url": "https://example.github.io/cerdanyola-local"}
        with tempfile.TemporaryDirectory() as tmp:
            out = Site(cfg, {k: {"fetched": NOW.isoformat(), "data": v} for k, v in data.items()}, tmp, NOW).build()
            home = (out / "ca/index.html").read_text(encoding="utf-8")
            self.assertIn("Castahalloween a Canaletes", home)
            self.assertIn("Guia d'oci", home)
            leisure = (out / "es/ocio/index.html").read_text(encoding="utf-8")
            self.assertIn("The 1916", leisure)
            self.assertIn("🎉", leisure)
            self.assertIn("OpenStreetMap", leisure)
            self.assertIn("R7", home)
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


if __name__ == "__main__":
    unittest.main()
