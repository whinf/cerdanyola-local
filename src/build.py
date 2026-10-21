"""Descarga las fuentes abiertas y genera la web de Cerdanyola en _site/.

  python src/build.py              descarga y genera
  python src/build.py --offline    solo genera con los datos guardados
  python src/build.py --check      falla si una fuente lleva 3 días sin responder
  --site-url URL                   URL pública (Actions pasa la de Pages)
  --now 2026-10-20T18:00           simula otra hora de Madrid
"""
import argparse
import json
import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sources  # noqa: E402
import tz  # noqa: E402
from render import ROOT, Site  # noqa: E402

DATA = ROOT / "data"
MAX_SILENCE = timedelta(days=3)

# nombre, función, horas mínimas entre descargas, ¿cuenta para --check?
SOURCES = [
    ("weather", sources.fetch_weather, 0, True),
    ("agenda", sources.fetch_agenda, 0, True),
    ("air", sources.fetch_air, 0, True),
    ("alerts", sources.fetch_alerts, 0, True),
    ("equipments", sources.fetch_equipments, 20, True),
    ("chargers", sources.fetch_chargers, 20, True),
    ("leisure", sources.fetch_leisure, 20, True),
    ("light", sources.fetch_light, 0, False),
]


def read(name):
    p = DATA / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def write(name, obj):
    DATA.mkdir(exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    p = DATA / f"{name}.json"
    if not p.exists() or p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def update(now):
    health = read("health") or {}
    for name, fetch, min_hours, _ in SOURCES:
        cached = read(name)
        if cached and min_hours and now - tz.parse_iso(cached["fetched"]) < timedelta(hours=min_hours):
            continue
        try:
            data = fetch(now)
        except Exception as exc:  # una fuente caída no debe tumbar la web
            print(f"aviso: {name}: {exc}")
            health.setdefault(name, {})["last_error"] = str(exc)[:300]
            continue
        if data is None:
            print(f"aviso: {name}: sin datos")
            continue
        write(name, {"fetched": now.isoformat(timespec="seconds"), "data": data})
        health[name] = {"last_ok": now.isoformat(timespec="seconds")}
        print(f"{name}: ok")
    write("health", health)


def check(now):
    health = read("health") or {}
    problems = []
    for name, _, _, required in SOURCES:
        last = (health.get(name) or {}).get("last_ok")
        if required and (not last or now - tz.parse_iso(last) > MAX_SILENCE):
            problems.append(f"{name} lleva más de 3 días sin datos: {(health.get(name) or {}).get('last_error')}")
    for p in problems:
        print("ERROR:", p)
    return 1 if problems else 0


def load_config(site_url=None):
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    if site_url:
        cfg["site_url"] = site_url
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not cfg.get("repo_url") and repo:
        cfg["repo_url"] = f"https://github.com/{repo}"
    if cfg.get("light_api_url") and not os.environ.get("LIGHT_API_URL"):
        os.environ["LIGHT_API_URL"] = cfg["light_api_url"]
    return cfg


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--site-url")
    ap.add_argument("--now")
    ap.add_argument("--out", default=str(ROOT / "_site"))
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    now = tz.now_madrid()
    if args.now:
        given = tz.parse_iso(args.now)
        if given.tzinfo is None:
            given = given.replace(tzinfo=tz.offset_at(given.replace(tzinfo=tz.CET)))
        now = tz.to_madrid(given)
    if args.check:
        return check(now)
    cfg = load_config(args.site_url)
    if not args.offline:
        update(now)
    data = {name: read(name) for name, *_ in SOURCES}
    out = Site(cfg, {k: v for k, v in data.items() if v}, args.out, now).build()
    print("sitio generado en", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
