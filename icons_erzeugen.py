"""Erzeugt die Favicons in static/. Einmalig auszufuehren, nicht Teil des Builds.

Schrift: Lato Bold (SIL Open Font License), aus /Library/Fonts. Farben aus
stil.css: Grund --papier, D in --tinte, Q in --tinte-matt -- wie die Marke
im Seitenkopf, die "Divites" fett und "Quartett" gedaempft setzt.
Gerechnet wird vierfach und dann verkleinert, sonst franst die Schrift bei
16 Bildpunkten aus. Die Buchstaben bleiben innerhalb des Kreises, auf den
Google das Icon in den Suchergebnissen zuschneidet.
"""
from PIL import Image, ImageDraw, ImageFont

SCHRIFT = "/Library/Fonts/Lato-Bold.ttf"
PAPIER, TINTE, MATT = (16, 15, 13), (238, 235, 229), (168, 162, 153)


def icon(s):
    n = s * 4
    bild = Image.new("RGB", (n, n), PAPIER)
    d = ImageDraw.Draw(bild)
    f = ImageFont.truetype(SCHRIFT, int(n * 0.50))
    luecke = int(n * 0.02)
    bd = d.textbbox((0, 0), "D", font=f)
    bq = d.textbbox((0, 0), "Q", font=f)
    breite = (bd[2] - bd[0]) + luecke + (bq[2] - bq[0])
    x = (n - breite) // 2
    y = (n - (bd[3] - bd[1])) // 2 - bd[1]
    d.text((x - bd[0], y), "D", font=f, fill=TINTE)
    d.text((x + (bd[2] - bd[0]) + luecke - bq[0], y), "Q", font=f, fill=MATT)
    return bild.resize((s, s), Image.LANCZOS)


if __name__ == "__main__":
    icon(192).save("static/icon-192.png", optimize=True)
    icon(96).save("static/icon-96.png", optimize=True)
    icon(180).save("static/apple-touch-icon.png", optimize=True)
    icon(256).save("static/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
