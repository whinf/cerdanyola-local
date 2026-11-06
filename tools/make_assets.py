"""Genera los PNG de static/ (iconos PWA, apple-touch-icon y og:image). Requiere Pillow; se ejecuta en local:

py tools/make_assets.py

Dibuja el mismo logotipo que static/favicon.svg (disco verde con marcador de mapa amarillo).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "static"
GREEN, YELLOW, BG = (11, 107, 58), (245, 213, 71), (249, 249, 247)
NAME, TAGLINE = "Cerdanyola Avui", "Temps, agenda, llum i transport · Tiempo, agenda, luz y transporte"


def logo(size, pad=0.0):
    """Disco verde con marcador; `pad` = margen relativo (para iconos maskable)."""
    s = 4
    im = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = pad * size * s
    d.ellipse((m, m, size * s - m, size * s - m), fill=GREEN)
    k = (size * s - 2 * m) / 32  # unidades de la caja de 32 del favicon
    c = size * s / 2
    cx, top = c, c + (6 - 16) * k  # el marcador va de y=6 a y=26 en la caja de 32
    r = 7 * k
    d.ellipse((cx - r, top, cx + r, top + 2 * r), fill=YELLOW)
    d.polygon([(cx - r * 0.93, top + r * 1.35), (cx + r * 0.93, top + r * 1.35), (cx, top + 20 * k)], fill=YELLOW)
    hole = 2.6 * k
    d.ellipse((cx - hole, top + r - hole, cx + hole, top + r + hole), fill=GREEN)
    return im.resize((size, size), Image.LANCZOS)


def font(size, bold=True):
    for name in ("segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


logo(512, 0.1).save(OUT / "icon-512.png", optimize=True)
logo(192, 0.1).save(OUT / "icon-192.png", optimize=True)
bg = Image.new("RGBA", (180, 180), GREEN)
bg.alpha_composite(logo(180))
bg.convert("RGB").save(OUT / "apple-touch-icon.png", optimize=True)

og = Image.new("RGB", (1200, 630), BG)
og.paste(logo(300), (90, 165), logo(300))
d = ImageDraw.Draw(og)
d.text((450, 215), NAME, fill=(26, 25, 23), font=font(84))
d.text((452, 335), TAGLINE, fill=(82, 81, 78), font=font(24, bold=False))
d.rectangle((0, 610, 1200, 630), fill=GREEN)
og.save(OUT / "og.png", optimize=True)
print("ok", [p.name for p in OUT.glob("*.png")])
