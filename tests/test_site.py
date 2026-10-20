import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import i18n  # noqa: E402
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
        city = S.parse_agenda_ajuntament(fixture("ajunt_agenda.html"), NOW.date())
        self.assertEqual(city[0]["title"], "Presentació llibre 'La serra fantàstica'")
        self.assertEqual(city[0]["time"], "18:30")
        merged = S.merge_events(gencat, city, city)
        self.assertEqual(len(merged), len({(e["title"], e["start"]) for e in gencat + city}))

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
        }
        cfg = {"site_name": "Cerdanyola Avui", "site_url": "https://example.github.io/cerdanyola-local"}
        with tempfile.TemporaryDirectory() as tmp:
            out = Site(cfg, {k: {"fetched": NOW.isoformat(), "data": v} for k, v in data.items()}, tmp, NOW).build()
            home = (out / "ca/index.html").read_text(encoding="utf-8")
            self.assertIn("Presentació llibre", home)
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
