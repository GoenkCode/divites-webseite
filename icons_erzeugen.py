"""Rechnet die Raster-Icons aus static/favicon.svg. Einmalig nach jeder
Aenderung am Logo auszufuehren, nicht Teil des Builds.

Das Logo stammt aus Claude Design (08.10.2026): F-Loch, gekreuzt von vier
Saiten unterschiedlicher Laenge, fuer vier Spieler. Die SVG-Dateien aller
Varianten liegen im Vault unter 03_projekte/divites/logo/.

Gerendert wird mit Chrome headless, weil weder Pillow noch die Systemwerkzeuge
SVG zuverlaessig rastern -- Quick Look schneidet Dateien mit verschobenem
viewBox-Ursprung ab. Chrome rechnet auf 768 Bildpunkte, Pillow verkleinert.
"""
import os
import subprocess
import tempfile

from PIL import Image

HIER = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
GROESSE = 768


def rastern(svg):
    with tempfile.TemporaryDirectory() as tmp:
        seite = os.path.join(tmp, "s.html")
        bild = os.path.join(tmp, "s.png")
        with open(seite, "w") as f:
            f.write('<html><body style="margin:0"><img src="file://%s" '
                    'style="width:%dpx;height:%dpx;display:block"></body></html>'
                    % (svg, GROESSE, GROESSE))
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--screenshot=" + bild, "--window-size=%d,%d" % (GROESSE, GROESSE),
                        "file://" + seite], check=True, capture_output=True)
        return Image.open(bild).convert("RGB")


if __name__ == "__main__":
    s = os.path.join(HIER, "static")
    gross = rastern(os.path.join(s, "favicon.svg"))
    klein = lambda n: gross.resize((n, n), Image.LANCZOS)
    klein(512).save(os.path.join(s, "logo-512.png"), optimize=True)
    klein(192).save(os.path.join(s, "icon-192.png"), optimize=True)
    klein(96).save(os.path.join(s, "icon-96.png"), optimize=True)
    klein(180).save(os.path.join(s, "apple-touch-icon.png"), optimize=True)
    klein(256).save(os.path.join(s, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
