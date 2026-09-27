#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_webseite.py — baut die Webseite des Divites Quartetts.

Quelle der Termine ist eine Markdown-Tabelle im Obsidian-Vault. Der Vault ist
lokal und hat kein Remote; ein Terminwechsel landet deshalb nicht von selbst
online, sondern erst beim naechsten Lauf dieses Skripts.

    python3 generate_webseite.py
    python3 generate_webseite.py --termine PFAD
    python3 generate_webseite.py --ausgabe PFAD

Laeuft mit Python 3.9. Einzige Abhaengigkeit ist Pillow, und auch die nur,
wenn Bilder vorhanden sind.
"""

import argparse
import datetime
import html
import io
import os
import re
import sys

# ---------------------------------------------------------------------------
# Schalter
# ---------------------------------------------------------------------------

# Solange False: jede Seite bekommt noindex, robots.txt bekommt Disallow.
# Die Seite ist dann ueber die Domain erreichbar, aber fuer Suchmaschinen
# unsichtbar. Erst auf True stellen, wenn die Inhalte wirklich stehen.
VEROEFFENTLICHEN = False

DOMAIN = "https://divites-quartett.com"
ENSEMBLE = "Divites Quartett"

HIER = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.expanduser("~/Desktop/Second_Brain/Musik_Brain")
TERMINE_STANDARD = os.path.join(VAULT, "03_projekte/divites/termine.md")
BILDER_QUELLE = os.path.join(VAULT, "03_projekte/divites/bilder")

SEITEN = [
    # (Dateiname ohne Endung, Navigationstitel, Seitentitel, Beschreibung)
    ("start",       "Start",      ENSEMBLE,
     "Streichquartett, 2020 gegruendet. Klassik, Filmmusik und Rock in eigenen Arrangements."),
    ("termine",     "Termine",    "Termine",
     "Alle kommenden Konzerte des Divites Quartetts, nach Ort filterbar."),
    ("ensemble",    "Ensemble",   "Das Ensemble",
     "Die Musikerinnen und Musiker des Divites Quartetts."),
    ("musik",       "Musik",      "Musik",
     "Hoerproben und Videomitschnitte des Divites Quartetts."),
    ("kontakt",     "Kontakt",    "Kontakt",
     "Anfragen und Buchungen fuer das Divites Quartett."),
    ("impressum",   "Impressum",  "Impressum", "Impressum und Anbieterkennzeichnung."),
    ("datenschutz", "Datenschutz","Datenschutz", "Datenschutzerklaerung."),
]

MONATE = ["Januar", "Februar", "Maerz", "April", "Mai", "Juni",
          "Juli", "August", "September", "Oktober", "November", "Dezember"]
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
              "Freitag", "Samstag", "Sonntag"]


class Abbruch(Exception):
    """Ein Zustand, bei dem nicht halb gebaut, sondern gar nicht gebaut wird."""


# ---------------------------------------------------------------------------
# Termine
# ---------------------------------------------------------------------------

ZEILE = re.compile(
    r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(\d{2}:\d{2})\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$"
)
STATUS_ERLAUBT = ("geplant", "bestaetigt", "bestätigt", "abgesagt")


def termine_lesen(pfad):
    """Liest die Termintabelle. Bricht ab statt eine leere Seite zu bauen."""
    if not os.path.isfile(pfad):
        raise Abbruch("Termindatei nicht gefunden: %s" % pfad)

    roh = io.open(pfad, encoding="utf-8").read()
    if not roh.strip():
        raise Abbruch("Termindatei ist leer: %s" % pfad)

    termine = []
    # Zeilen, die wie ein Termin aussehen, aber das Muster verfehlen, sind
    # Tippfehler und keine Kommentare. Sie werden gemeldet, nicht verschluckt.
    verdaechtig = []
    for nr, zeile in enumerate(roh.splitlines(), 1):
        if not zeile.startswith("| 20"):
            continue
        treffer = ZEILE.match(zeile)
        if not treffer:
            verdaechtig.append((nr, zeile.strip()))
            continue
        datum, uhrzeit, ort, adresse, programm, ticket, status = treffer.groups()
        status = status.strip().lower()
        if status not in STATUS_ERLAUBT:
            raise Abbruch(
                "Zeile %d: unbekannter Status %r. Erlaubt: geplant, bestaetigt, abgesagt"
                % (nr, status))
        try:
            tag = datetime.date(*[int(x) for x in datum.split("-")])
        except ValueError:
            raise Abbruch("Zeile %d: %s ist kein gueltiges Datum" % (nr, datum))
        termine.append({
            "datum": tag,
            "uhrzeit": uhrzeit.strip(),
            "ort": ort.strip(),
            "adresse": adresse.strip(),
            "programm": programm.strip(),
            "ticket": ticket.strip(),
            "abgesagt": status == "abgesagt",
        })

    if verdaechtig:
        for nr, text in verdaechtig:
            sys.stderr.write("  Zeile %d sieht aus wie ein Termin, passt aber nicht "
                             "ins Format:\n    %s\n" % (nr, text))
        raise Abbruch("%d Zeile(n) im falschen Format. Nichts gebaut."
                      % len(verdaechtig))

    if not termine:
        raise Abbruch("Keine einzige gueltige Terminzeile in %s" % pfad)

    termine.sort(key=lambda t: (t["datum"], t["uhrzeit"]))
    return termine


def datum_lang(tag):
    return "%s, %d. %s %d" % (WOCHENTAGE[tag.weekday()], tag.day,
                              MONATE[tag.month - 1], tag.year)


def termine_html(termine, heute, nur_naechste=None):
    """Baut die Terminliste. Orte werden nur verlinkt, wenn ein Link da ist."""
    kommend = [t for t in termine if t["datum"] >= heute]
    vergangen = [t for t in termine if t["datum"] < heute]
    if nur_naechste:
        kommend, vergangen = kommend[:nur_naechste], []

    orte = []
    for t in kommend:
        if t["ort"] not in orte:
            orte.append(t["ort"])

    teile = []

    # Filter nur anbieten, wenn es ueberhaupt etwas zu filtern gibt.
    if not nur_naechste and len(orte) > 1:
        teile.append('<div class="filter" data-filter hidden>')
        teile.append('  <span class="filter__titel" id="filter-titel">Ort:</span>')
        teile.append('  <div class="filter__knoepfe" role="group" aria-labelledby="filter-titel">')
        teile.append('    <button type="button" class="filter__knopf" '
                     'data-ort="*" aria-pressed="true">Alle</button>')
        for ort in orte:
            teile.append('    <button type="button" class="filter__knopf" data-ort="%s" '
                         'aria-pressed="false">%s</button>'
                         % (html.escape(ort, True), html.escape(ort)))
        teile.append('  </div>')
        teile.append('</div>')

    def liste(eintraege, titel=None):
        aus = []
        if titel:
            aus.append('<h2 class="termine__trenner">%s</h2>' % html.escape(titel))
        aus.append('<ul class="termine" data-termine>')
        for t in eintraege:
            klassen = "termin" + (" termin--abgesagt" if t["abgesagt"] else "")
            aus.append('  <li class="%s" data-ort="%s">'
                       % (klassen, html.escape(t["ort"], True)))
            aus.append('    <div class="termin__marke">')
            aus.append('      <span class="termin__tag">%02d</span>' % t["datum"].day)
            aus.append('      <span class="termin__monat">%s</span>'
                       % MONATE[t["datum"].month - 1][:3])
            aus.append('      <span class="termin__jahr">%d</span>' % t["datum"].year)
            aus.append('    </div>')
            aus.append('    <div class="termin__inhalt">')
            aus.append('      <h3 class="termin__programm">%s</h3>'
                       % html.escape(t["programm"]))
            aus.append('      <p class="termin__wann"><time datetime="%sT%s">%s, %s Uhr</time></p>'
                       % (t["datum"].isoformat(), t["uhrzeit"],
                          datum_lang(t["datum"]), t["uhrzeit"]))
            # Kein leerer href: ohne Ticketlink bleibt der Ort schlichter Text.
            if t["ticket"]:
                ort_html = ('<a class="termin__ort" href="%s" rel="noopener">%s</a>'
                            % (html.escape(t["ticket"], True), html.escape(t["ort"])))
            else:
                ort_html = '<span class="termin__ort">%s</span>' % html.escape(t["ort"])
            aus.append('      <p class="termin__wo">%s<span class="termin__adresse">%s</span></p>'
                       % (ort_html, html.escape(t["adresse"])))
            if t["abgesagt"]:
                aus.append('      <p class="termin__hinweis">Abgesagt</p>')
            aus.append('    </div>')
            aus.append('  </li>')
        aus.append('</ul>')
        return "\n".join(aus)

    if kommend:
        teile.append(liste(kommend))
    else:
        teile.append('<p class="leer">Zurzeit sind keine Termine angekuendigt.</p>')
    if vergangen:
        teile.append(liste(list(reversed(vergangen)), "Vergangene Konzerte"))

    return "\n".join(teile), len(kommend), len(vergangen)


# ---------------------------------------------------------------------------
# Markdown, nur so viel wie gebraucht wird
# ---------------------------------------------------------------------------

def markdown_zu_html(text, quelle):
    """
    Bewusst winziger Konverter: Ueberschriften, Absaetze, Listen, Zitate,
    fett, kursiv, Links, Platzhaltermarken.

    Er bricht bei unbekannter Syntax ab, statt sie stillschweigend als Text
    auszugeben. Ein halb gerenderter Seitentext faellt online kaum auf und
    ist genau deshalb gefaehrlich.
    """
    nicht_unterstuetzt = [
        (re.compile(r"^```"), "Codebloecke"),
        (re.compile(r"^\s{0,3}\|"), "Tabellen"),
        (re.compile(r"^\s*\d+\.\s"), "nummerierte Listen"),
        (re.compile(r"!\["), "Bild-Syntax"),
    ]
    # Callout-Marken ausserhalb einer Zitatzeile wuerden woertlich im HTML
    # landen. Genau das ist beim ersten Lauf passiert.
    for nr, zeile in enumerate(text.splitlines(), 1):
        if "[!" in zeile and not zeile.lstrip().startswith("> [!"):
            raise Abbruch(
                "%s, Zeile %d: Callout-Marke ausserhalb einer Zitatzeile.\n"
                "    %s\n"
                "    Callouts muessen als '> [!MARKE] Text' geschrieben werden."
                % (quelle, nr, zeile.strip()))
    for nr, zeile in enumerate(text.splitlines(), 1):
        for muster, name in nicht_unterstuetzt:
            if muster.search(zeile):
                raise Abbruch(
                    "%s, Zeile %d: %s werden vom Konverter nicht unterstuetzt.\n"
                    "    %s\n"
                    "    Entweder die Stelle umschreiben oder den Konverter erweitern."
                    % (quelle, nr, name, zeile.strip()))

    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                   lambda m: '<a href="%s">%s</a>' % (m.group(2), m.group(1)), s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        # Platzhalter sichtbar auszeichnen, damit sie im Generat auffallen
        s = re.sub(r"\[([A-ZÄÖÜ][A-ZÄÖÜ  ]*(?:FOLGT|OFFEN)?)\]",
                   r'<mark class="platzhalter">[\1]</mark>', s)
        return s

    aus, absatz, liste_offen = [], [], False

    def absatz_schliessen():
        if absatz:
            aus.append("<p>%s</p>" % inline(" ".join(absatz)))
            del absatz[:]

    def liste_schliessen():
        nonlocal_liste[0] = False
        aus.append("</ul>")

    nonlocal_liste = [False]

    for zeile in text.splitlines():
        s = zeile.rstrip()
        if not s.strip():
            absatz_schliessen()
            if nonlocal_liste[0]:
                liste_schliessen()
            continue
        # Rohe HTML-Bloecke unveraendert durchreichen. Noetig fuer Auftakt,
        # Stimmen und Raster, die sich in Markdown nicht ausdruecken lassen.
        # Erkannt an einer Zeile, die mit '<' beginnt.
        if s.lstrip().startswith("<"):
            absatz_schliessen()
            if nonlocal_liste[0]:
                liste_schliessen()
            aus.append(s)
            continue
        if s.startswith("#"):
            absatz_schliessen()
            if nonlocal_liste[0]:
                liste_schliessen()
            stufe = len(s) - len(s.lstrip("#"))
            aus.append("<h%d>%s</h%d>" % (stufe, inline(s[stufe:].strip()), stufe))
        elif s.startswith("> "):
            absatz_schliessen()
            if nonlocal_liste[0]:
                liste_schliessen()
            rest = s[2:]
            # Obsidian-Callouts: "> [!WARNUNG] Text". Ohne Sonderbehandlung
            # landet die Marke woertlich auf der Seite — genau das ist beim
            # ersten Lauf am 27.09.2026 passiert.
            callout = re.match(r"^\[!([A-ZÄÖÜa-zäöü]+)\]\s*(.*)$", rest)
            if callout:
                aus.append('<aside class="hinweis"><strong class="hinweis__marke">%s</strong> '
                           '<span>%s</span></aside>'
                           % (inline(callout.group(1).capitalize()), inline(callout.group(2))))
            else:
                aus.append("<blockquote><p>%s</p></blockquote>" % inline(rest))
        elif s.startswith("- "):
            absatz_schliessen()
            if not nonlocal_liste[0]:
                aus.append("<ul>")
                nonlocal_liste[0] = True
            aus.append("<li>%s</li>" % inline(s[2:]))
        else:
            absatz.append(s.strip())

    absatz_schliessen()
    if nonlocal_liste[0]:
        liste_schliessen()
    return "\n".join(aus)


# ---------------------------------------------------------------------------
# Seitenbau
# ---------------------------------------------------------------------------

def navigation(aktuell):
    teile = ['<nav class="nav" aria-label="Hauptnavigation"><ul>']
    for name, titel, _, _ in SEITEN:
        if name in ("impressum", "datenschutz"):
            continue
        ziel = "index.html" if name == "start" else "%s.html" % name
        if name == aktuell:
            teile.append('<li><a href="%s" aria-current="page">%s</a></li>' % (ziel, titel))
        else:
            teile.append('<li><a href="%s">%s</a></li>' % (ziel, titel))
    teile.append("</ul></nav>")
    return "\n".join(teile)


def seite_bauen(vorlage, name, titel, beschreibung, inhalt, braucht_filter):
    ziel = "index.html" if name == "start" else "%s.html" % name
    kopf = ""
    if not VEROEFFENTLICHEN:
        kopf = '<meta name="robots" content="noindex, nofollow">'
    skript = '<script src="filter.js" defer></script>' if braucht_filter else ""
    voller_titel = titel if name == "start" else "%s – %s" % (titel, ENSEMBLE)
    return vorlage \
        .replace("{{TITEL}}", html.escape(voller_titel)) \
        .replace("{{BESCHREIBUNG}}", html.escape(beschreibung)) \
        .replace("{{ROBOTS}}", kopf) \
        .replace("{{CANONICAL}}", "%s/%s" % (DOMAIN, "" if name == "start" else ziel)) \
        .replace("{{NAV}}", navigation(name)) \
        .replace("{{INHALT}}", inhalt) \
        .replace("{{JAHR}}", str(datetime.date.today().year)) \
        .replace("{{SKRIPT}}", skript)


def bilder_kopieren(quelle, ziel, maxbreite=1600):
    if not os.path.isdir(quelle):
        return 0
    dateien = [f for f in sorted(os.listdir(quelle))
               if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    if not dateien:
        return 0
    try:
        from PIL import Image
    except ImportError:
        raise Abbruch("Es liegen %d Bilder in %s, aber Pillow ist nicht installiert."
                      % (len(dateien), quelle))
    os.makedirs(ziel, exist_ok=True)
    for f in dateien:
        bild = Image.open(os.path.join(quelle, f))
        if bild.width > maxbreite:
            hoehe = int(bild.height * maxbreite / float(bild.width))
            bild = bild.resize((maxbreite, hoehe), Image.LANCZOS)
        bild.save(os.path.join(ziel, f))
    return len(dateien)


def main():
    p = argparse.ArgumentParser(description="Baut die Webseite des Divites Quartetts.")
    p.add_argument("--termine", default=TERMINE_STANDARD)
    p.add_argument("--ausgabe", default=os.path.join(HIER, "build"))
    p.add_argument("--heute", default=None, help="Stichtag ueberschreiben, Format YYYY-MM-DD")
    args = p.parse_args()

    heute = datetime.date.today()
    if args.heute:
        heute = datetime.date(*[int(x) for x in args.heute.split("-")])

    try:
        termine = termine_lesen(args.termine)

        vorlage_pfad = os.path.join(HIER, "src", "vorlage.html")
        if not os.path.isfile(vorlage_pfad):
            raise Abbruch("Vorlage fehlt: %s" % vorlage_pfad)
        vorlage = io.open(vorlage_pfad, encoding="utf-8").read()

        os.makedirs(args.ausgabe, exist_ok=True)

        liste_voll, anz_kommend, anz_vergangen = termine_html(termine, heute)
        liste_kurz, _, _ = termine_html(termine, heute, nur_naechste=3)

        gebaut = 0
        for name, _, titel, beschreibung in SEITEN:
            quelle = os.path.join(HIER, "src", "seiten", "%s.md" % name)
            if not os.path.isfile(quelle):
                raise Abbruch("Seiteninhalt fehlt: %s" % quelle)
            roh = io.open(quelle, encoding="utf-8").read()
            inhalt = markdown_zu_html(roh, "%s.md" % name)
            inhalt = inhalt.replace("<p>{{TERMINE}}</p>", liste_voll)
            inhalt = inhalt.replace("<p>{{TERMINE_KURZ}}</p>", liste_kurz)
            ziel = "index.html" if name == "start" else "%s.html" % name
            io.open(os.path.join(args.ausgabe, ziel), "w", encoding="utf-8").write(
                seite_bauen(vorlage, name, titel, beschreibung, inhalt,
                            braucht_filter=("{{TERMINE}}" in roh)))
            gebaut += 1

        # statische Dateien unveraendert uebernehmen
        statisch = os.path.join(HIER, "static")
        kopiert = 0
        if os.path.isdir(statisch):
            for f in sorted(os.listdir(statisch)):
                q = os.path.join(statisch, f)
                if os.path.isfile(q):
                    io.open(os.path.join(args.ausgabe, f), "w", encoding="utf-8").write(
                        io.open(q, encoding="utf-8").read())
                    kopiert += 1

        for name in ("stil.css", "filter.js"):
            q = os.path.join(HIER, "src", name)
            if os.path.isfile(q):
                io.open(os.path.join(args.ausgabe, name), "w", encoding="utf-8").write(
                    io.open(q, encoding="utf-8").read())

        anz_bilder = bilder_kopieren(BILDER_QUELLE, os.path.join(args.ausgabe, "bilder"))
        abgesagt = len([t for t in termine if t["abgesagt"]])

    except Abbruch as fehler:
        sys.stderr.write("\nABBRUCH: %s\n\n" % fehler)
        return 1

    print("Termine gelesen:   %d" % len(termine))
    print("  davon kommend:   %d" % anz_kommend)
    print("  davon vergangen: %d" % anz_vergangen)
    print("  davon abgesagt:  %d" % abgesagt)
    print("Seiten gebaut:     %d" % gebaut)
    print("Statische Dateien: %d" % kopiert)
    print("Bilder:            %d" % anz_bilder)
    print("Sichtbarkeit:      %s" % ("oeffentlich, indexierbar" if VEROEFFENTLICHEN
                                     else "noindex (nicht in Suchmaschinen)"))
    print("Ausgabe:           %s" % args.ausgabe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
