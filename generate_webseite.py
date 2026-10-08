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
import shutil
import re
import sys

# ---------------------------------------------------------------------------
# Schalter
# ---------------------------------------------------------------------------

# Solange False: jede Seite bekommt noindex, robots.txt bekommt Disallow.
# Die Seite ist dann ueber die Domain erreichbar, aber fuer Suchmaschinen
# unsichtbar. Am 08.10.2026 auf Victors Wort umgelegt.
VEROEFFENTLICHEN = True

DOMAIN = "https://divites-quartett.com"
ENSEMBLE = "Divites Quartett"

# Vorschaubild fuer geteilte Links (Open Graph). Ohne das erscheint jeder
# Link, den jemand per WhatsApp oder Mail weitergibt, als grauer Kasten
# ohne Bild und ohne Titel -- und die Seite verbreitet sich nun einmal
# durch Weitergeben, nicht durch Ranking.
#
# Quelle ist ein Querformat: 1.91:1 laesst sich daraus beschneiden, ohne
# dass Koepfe fehlen. Aus dem hochformatigen Auftaktfoto wuerde derselbe
# Schnitt einen Streifen machen.
OG_QUELLE = "quartett_kurhaus_profil.jpg"
OG_DATEI = "vorschau.jpg"
OG_BREITE, OG_HOEHE = 1200, 630
# Wo der Schnitt sitzt, senkrecht: 0.5 waere die Bildmitte. Etwas tiefer,
# weil die vier auf dem Foto in der unteren Haelfte stehen.
OG_SCHNITT = 0.58
OG_ALT = ("Das Divites Quartett mit Violine, Bratsche und Violoncello auf der "
          "Bühne des Friedrich-von-Thiersch-Saals im Kurhaus Wiesbaden")

HIER = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.expanduser("~/Desktop/Second_Brain/Musik_Brain")
TERMINE_STANDARD = os.path.join(VAULT, "03_projekte/divites/termine.md")
BILDER_QUELLE = os.path.join(VAULT, "03_projekte/divites/bilder")

# Die Beschreibung landet im Google-Snippet und in der Social-Vorschau.
# Sie wird also gelesen, und zwar bevor jemand die Seite gesehen hat.
# Deshalb hier echte Umlaute: "2020 gegruendet" im Suchergebnis sieht aus
# wie ein Tippfehler, den niemand korrigiert hat.
#
# Der Suchtitel ist nicht der Seitentitel. Wer "Divites Quartett" sucht,
# kennt den Namen schon; gefunden werden muss das Ensemble von Leuten,
# die "Streichquartett Frankfurt" eingeben. Steht der Zusatz leer, wird
# der Seitentitel genommen.
SEITEN = [
    # (Dateiname, Navigationstitel, Seitentitel, Beschreibung, Suchtitel)
    ("start",       "Start",      ENSEMBLE,
     "Streichquartett aus Frankfurt, 2020 gegründet. Klassik, Filmmusik und "
     "Rock in eigenen Arrangements, ohne Verstärker.",
     "%s – Streichquartett Frankfurt" % ENSEMBLE),
    ("termine",     "Termine",    "Termine",
     "Kommende Candlelight-Konzerte des Divites Quartetts in "
     "Frankfurt, Wiesbaden und weiteren Städten. Mit Datum, Programm und "
     "Ticketlink, nach Ort filterbar.",
     "Konzerttermine"),
    ("ensemble",    "Ensemble",   "Das Ensemble",
     "Die Musikerinnen und Musiker des Divites Quartetts aus Frankfurt: "
     "Violine, Viola und Violoncello, mit Porträts und Biografien.",
     "Das Ensemble"),
    ("musik",       "Musik",      "Musik",
     "Videomitschnitte des Divites Quartetts: Vivaldi, Queen, AC/DC und "
     "Coldplay in eigenen Arrangements für Streichquartett.",
     "Videos und Repertoire"),
    ("kontakt",     "Kontakt",    "Kontakt",
     "Ein Streichquartett für Konzerte und Veranstaltungen buchen. "
     "Anfragen an das Divites Quartett.",
     "Streichquartett buchen"),
    ("impressum",   "Impressum",  "Impressum",
     "Impressum und Anbieterkennzeichnung.", ""),
    ("datenschutz", "Datenschutz","Datenschutz",
     "Datenschutzerklärung.", ""),
]

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni",
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


def letzter_sonntag(jahr, monat):
    """Letzter Sonntag eines Monats — Angelpunkt der EU-Sommerzeitregel."""
    if monat == 12:
        tag = datetime.date(jahr + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        tag = datetime.date(jahr, monat + 1, 1) - datetime.timedelta(days=1)
    return tag - datetime.timedelta(days=(tag.weekday() + 1) % 7)


def zeitzone(tag, uhrzeit):
    """
    Liefert '+02:00' oder '+01:00' fuer Europe/Berlin.

    Selbst gerechnet statt ueber zoneinfo, damit der Generator keine
    System-Zeitzonendaten braucht. Die Regel: Sommerzeit vom letzten
    Sonntag im Maerz, 01:00 UTC, bis zum letzten Sonntag im Oktober,
    01:00 UTC.

    Fest verdrahtetes '+02:00' waere der naheliegende Fehler: ab dem
    25.10.2026 waere dann jeder Termin eine Stunde falsch, und das
    faellt in strukturierten Daten niemandem auf.
    """
    beginn = letzter_sonntag(tag.year, 3)
    ende = letzter_sonntag(tag.year, 10)
    stunde = int(uhrzeit.split(":")[0])
    if tag < beginn or tag > ende:
        return "+01:00"
    if tag == beginn:
        return "+02:00" if stunde >= 3 else "+01:00"
    if tag == ende:
        return "+01:00" if stunde >= 3 else "+02:00"
    return "+02:00"


def stadt_aus_adresse(adresse):
    """
    Zieht die Stadt aus der Adresse: alles nach der Postleitzahl.

    Gefiltert wird nach Stadt, nicht nach Spielstaette. Vier Spielstaetten
    ergaeben vier Knoepfe, die Staedte nur zwei — und die Frage des
    Besuchers lautet "spielt ihr in meiner Stadt", nicht "in welchem Haus".
    Die Spielstaette steht ohnehin in jeder Zeile.
    """
    import re as _re
    m = _re.search(r"\b\d{5}\s+(.+)$", adresse.strip())
    if not m:
        return adresse.strip() or "Ohne Ortsangabe"
    stadt = m.group(1).strip()
    # "Frankfurt am Main" bleibt so — Abkuerzen waere eine Behauptung
    # ueber den Sprachgebrauch, die niemand verlangt hat.
    return stadt


def adresse_zerlegen(adresse):
    """
    Trennt "Kurhausplatz 1, 65189 Wiesbaden" in Strasse, Postleitzahl und Ort.

    Bis zum 29.09.2026 stand die vollstaendige Adresse als ein einziges
    streetAddress im Markup. Google liest sie dann als Strassenangabe und hat
    zu Ort und Postleitzahl nichts -- genau die beiden Felder, auf die eine
    Suche nach "Streichquartett Wiesbaden" trifft.

    Passt das Muster nicht, bleibt alles im streetAddress. Lieber eine
    unaufgeteilte Adresse als eine falsch aufgeteilte.
    """
    import re as _re
    m = _re.match(r"^(.*?),\s*(\d{5})\s+(.+)$", adresse.strip())
    if not m:
        return {"streetAddress": adresse.strip()}
    return {"streetAddress": m.group(1).strip(),
            "postalCode": m.group(2),
            "addressLocality": m.group(3).strip(),
            "addressCountry": "DE"}


def termin_html(t, folge=False):
    """Eine Terminzeile. folge=True bei mehreren Konzerten am selben Tag."""
    klassen = "termin"
    if t["abgesagt"]:
        klassen += " termin--abgesagt"
    if folge:
        klassen += " termin--folge"
    a = []
    # data-datum traegt Datum und Anfangszeit in den Browser. Dort
    # entscheidet termine.js, was kommend und was vergangen ist -- sonst
    # friert die Trennung auf dem Stand des letzten Exports ein.
    #
    # Mit Uhrzeit, nicht nur mit Datum: Drei Konzerte an einem Abend sind
    # um 22 Uhr alle drei vorbei, standen mit reiner Tagesgenauigkeit aber
    # bis Mitternacht unter "die naechsten Konzerte".
    a.append('  <li class="%s" data-ort="%s" data-datum="%sT%s">'
             % (klassen, html.escape(stadt_aus_adresse(t["adresse"]), True),
                t["datum"].isoformat(), t["uhrzeit"]))
    a.append('    <div class="termin__marke">')
    a.append('      <span class="termin__tag">%02d</span>' % t["datum"].day)
    a.append('      <span class="termin__monat">%s</span>' % MONATE[t["datum"].month - 1][:3])
    a.append('      <span class="termin__jahr">%d</span>' % t["datum"].year)
    a.append('    </div>')
    a.append('    <div class="termin__inhalt">')
    a.append('      <h3 class="termin__programm">%s</h3>' % html.escape(t["programm"]))
    a.append('      <p class="termin__wann"><time datetime="%sT%s">%s, %s Uhr</time></p>'
             % (t["datum"].isoformat(), t["uhrzeit"], datum_lang(t["datum"]), t["uhrzeit"]))
    if t["ticket"]:
        ort = ('<a class="termin__ort" href="%s" rel="noopener">%s</a>'
               % (html.escape(t["ticket"], True), html.escape(t["ort"])))
    else:
        ort = '<span class="termin__ort">%s</span>' % html.escape(t["ort"])
    a.append('      <p class="termin__wo">%s<span class="termin__adresse">%s</span></p>'
             % (ort, html.escape(t["adresse"])))
    if t["abgesagt"]:
        a.append('      <p class="termin__hinweis">Abgesagt</p>')
    a.append('    </div>')
    a.append('  </li>')
    return "\n".join(a)


def programme_html(termine):
    """
    Die Programmliste der Musikseite, gebaut aus denselben Terminen wie die
    Terminliste. Sie von Hand zu pflegen hiesse, sie zweimal zu pflegen -- und
    nach dem zweiten vergessenen Nachtrag stuende dort ein Repertoire, das es
    nicht mehr gibt. Sortiert nach Haeufigkeit: was oft gespielt wird, steht
    oben, weil es das Programm ist, nach dem gefragt wird.
    """
    zaehler = {}
    for t in termine:
        name = (t.get("programm") or "").strip()
        if name:
            zaehler[name] = zaehler.get(name, 0) + 1
    if not zaehler:
        return ""
    sortiert = sorted(zaehler.items(), key=lambda kv: (-kv[1], kv[0]))
    zeilen = ['<ul class="programme">']
    for name, _ in sortiert:
        zeilen.append("<li>%s</li>" % html.escape(name))
    zeilen.append("</ul>")
    return "\n".join(zeilen)


def termine_html(termine, heute, nur_naechste=None):
    """Baut die Terminliste. Orte werden nur verlinkt, wenn ein Link da ist."""
    kommend = [t for t in termine if t["datum"] >= heute]
    vergangen = [t for t in termine if t["datum"] < heute]
    if nur_naechste:
        kommend, vergangen = kommend[:nur_naechste], []

    orte = []
    for t in kommend:
        st = stadt_aus_adresse(t["adresse"])
        if st not in orte:
            orte.append(st)
    orte.sort()

    teile = []

    # Filter nur anbieten, wenn es ueberhaupt etwas zu filtern gibt.
    if not nur_naechste and len(orte) > 1:
        teile.append('<div class="filter" data-filter hidden>')
        teile.append('  <span class="filter__titel" id="filter-titel">Stadt:</span>')
        teile.append('  <div class="filter__knoepfe" role="group" aria-labelledby="filter-titel">')
        teile.append('    <button type="button" class="filter__knopf" '
                     'data-ort="*" aria-pressed="true">Alle</button>')
        for ort in orte:
            teile.append('    <button type="button" class="filter__knopf" data-ort="%s" '
                         'aria-pressed="false">%s</button>'
                         % (html.escape(ort, True), html.escape(ort)))
        teile.append('  </div>')
        teile.append('</div>')

    def liste(eintraege, titel=None, nach_monaten=False):
        """
        Baut die Terminliste. Mit nach_monaten=True wird nach Monaten
        gegliedert: vierzig gleichfoermige Zeilen sind sonst nicht zu
        ueberblicken.

        Mehrere Konzerte am selben Tag bekommen ab dem zweiten die Klasse
        termin--folge. Die Datumsmarke wird dort zurueckgenommen, damit
        derselbe Tag nicht dreimal gleich laut dasteht.
        """
        if nach_monaten:
            aus = []
            monat_jetzt = None
            offen = False
            letzter_tag = None
            for t in eintraege:
                mk = (t["datum"].year, t["datum"].month)
                if mk != monat_jetzt:
                    if offen:
                        aus.append('</ul>')
                        aus.append('</section>')
                    kennung = "m-%04d-%02d" % mk
                    aus.append('<section class="monat" data-monat aria-labelledby="%s">' % kennung)
                    aus.append('<h2 class="monat__titel" id="%s">%s <span class="monat__jahr">%d</span></h2>'
                               % (kennung, MONATE[mk[1] - 1], mk[0]))
                    aus.append('<ul class="termine" data-termine>')
                    monat_jetzt, offen, letzter_tag = mk, True, None
                folge = (letzter_tag == t["datum"])
                aus.append(termin_html(t, folge))
                letzter_tag = t["datum"]
            if offen:
                aus.append('</ul>')
                aus.append('</section>')
            return "\n".join(aus)

        aus = []
        if titel:
            aus.append('<h2 class="termine__trenner">%s</h2>' % html.escape(titel))
        # Auf der Startseite steht die Zahl der gewuenschten Termine am
        # Element; welche drei es sind, entscheidet sich im Browser.
        aus.append('<ul class="termine" data-termine%s>'
                   % (' data-naechste="3"' if nur_naechste else ''))
        for t in eintraege:
            # termin_html statt einer zweiten, fast gleichen Fassung an
            # dieser Stelle. Die Dopplung hatte data-datum nicht bekommen
            # und haette die Vergangenen stumm vom Abgleich ausgenommen.
            aus.append(termin_html(t))
        aus.append('</ul>')
        return "\n".join(aus)

    if kommend:
        teile.append(liste(kommend, nach_monaten=not nur_naechste))
    else:
        teile.append('<p class="leer">Zurzeit sind keine Termine angekuendigt.</p>')

    # Der Bereich fuer Vergangenes wird immer angelegt, auch wenn er heute
    # leer ist: termine.js braucht ein Ziel, in das es Termine schieben
    # kann, die seit dem letzten Export verstrichen sind.
    if not nur_naechste:
        teile.append('<div data-vergangen%s>' % ('' if vergangen else ' hidden'))
        teile.append('<h2 class="termine__trenner">Vergangene Konzerte</h2>')
        teile.append('<ul class="termine" data-termine data-vergangen-liste>')
        for t in reversed(vergangen):
            teile.append(termin_html(t))
        teile.append('</ul>')
        teile.append('</div>')

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
        # Markdown-Bildsyntax wird nicht unterstuetzt. Echtes <img> in
        # einem HTML-Block schon - deshalb nur auf "![" ausserhalb von
        # HTML-Zeilen pruefen.
        (re.compile(r"(?<!\S)!\["), "Markdown-Bildsyntax"),
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

def json_ensemble():
    """
    JSON-LD fuer das Ensemble. Nur belegte Angaben.

    Die Mitgliederliste war bis zum 29.09.2026 bei fuenf Namen stehengeblieben,
    waehrend die Ensembleseite sieben zeigte -- Karolina Rybka und Larissa
    Nagel fehlten. Zwei Quellen fuer dieselbe Besetzung sind eine zu viel;
    deshalb steht sie jetzt an einer Stelle und wird von hier ausgegeben.

    Die `sameAs` je Person nur dort, wo eine eigene Seite belegt ist. Eine
    geratene URL waere schlimmer als keine: Sie verknuepft die Person mit einer
    fremden Entitaet, und das laesst sich nachtraeglich schwer aufloesen.
    """
    besetzung = [
        ("Marta Danilkovich", "https://marta.danilkovich.com/"),
        ("Namhyun Kim", None),
        ("Eunseon Oh", None),
        ("Karolina Rybka", None),
        ("Victor aus Butzbach", None),
        ("Attila Hündöl", None),
        ("Larissa Nagel", "https://larissanagel.com/"),
    ]
    zeilen = []
    for name, seite in besetzung:
        if seite:
            zeilen.append('    {"@type": "Person", "name": %s, "sameAs": %s}'
                          % (json_text(name), json_text(seite)))
        else:
            zeilen.append('    {"@type": "Person", "name": %s}' % json_text(name))
    mitglieder = ",\n".join(zeilen)
    return (
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "MusicGroup",\n'
        '  "name": %s,\n'
        '  "description": %s,\n'
        '  "foundingDate": "2020",\n'
        '  "genre": ["Klassik", "Filmmusik", "Rock", "Pop"],\n'
        '  "url": %s,\n'
        '  "image": %s,\n'
        '  "logo": "https://divites-quartett.com/logo-512.png",\n'
        # Ort ohne Strasse: Die volle Anschrift steht im Impressum, wo das
        # Gesetz sie verlangt. Im Markup braucht es nur die Stadt -- auf sie
        # trifft eine Suche nach "Streichquartett Frankfurt".
        '  "address": {"@type": "PostalAddress", '
        '"addressLocality": "Frankfurt am Main", "addressCountry": "DE"},\n'
        '  "areaServed": {"@type": "Country", "name": "Deutschland"},\n'
        '  "sameAs": [\n'
        '    "https://www.instagram.com/divites.quartett/",\n'
        '    "https://www.facebook.com/966775389852634/"\n'
        '  ],\n'
        '  "member": [\n%s\n  ]\n'
        '}\n'
        '</script>' % (
            json_text(ENSEMBLE),
            json_text("Streichquartett aus Frankfurt am Main, gegründet 2020 von "
                      "Marta Danilkovich. Klassik, Filmmusik, Rock und Pop in "
                      "eigenen Arrangements, gespielt ohne Verstärker."),
            json_text(DOMAIN),
            json_text("%s/bilder/%s" % (DOMAIN, OG_DATEI)),
            mitglieder))


def json_text(s):
    """Minimaler JSON-String-Encoder, damit kein Modul noetig ist."""
    aus = s.replace("\\", "\\\\").replace('"', '\\"')
    aus = aus.replace("\n", "\\n").replace("\r", "").replace("\t", "\\t")
    return '"%s"' % aus


def json_termine(termine, heute):
    """
    Ein Event je Termin, aus derselben Quelle wie die sichtbare Liste.
    Doppelte Pflege waere der sichere Weg zu Widerspruechen zwischen dem,
    was Besucher sehen, und dem, was Google liest.
    """
    kommend = [t for t in termine if t["datum"] >= heute]
    if not kommend:
        return ""
    bloecke = []
    for t in kommend:
        felder = [
            '    "@context": "https://schema.org"',
            # MusicEvent statt Event: Nur der spezielle Typ kommt in Googles
            # Veranstaltungssuche. Der generische wird gelesen und ignoriert.
            '    "@type": "MusicEvent"',
            '    "name": %s' % json_text("%s – %s" % (ENSEMBLE, t["programm"])),
            '    "startDate": "%sT%s:00%s"' % (t["datum"].isoformat(), t["uhrzeit"],
                                               zeitzone(t["datum"], t["uhrzeit"])),
            '    "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode"',
            '    "eventStatus": "https://schema.org/%s"'
            % ("EventCancelled" if t["abgesagt"] else "EventScheduled"),
            '    "performer": {"@type": "MusicGroup", "name": %s, "url": %s}'
            % (json_text(ENSEMBLE), json_text(DOMAIN)),
            '    "image": %s' % json_text("%s/bilder/%s" % (DOMAIN, OG_DATEI)),
            '    "description": %s'
            % json_text("%s spielt %s. Streichquartett in eigenen Arrangements."
                        % (ENSEMBLE, t["programm"])),
            '    "organizer": {"@type": "Organization", "name": "Fever"}',
            '    "location": {"@type": "Place", "name": %s, "address": '
            '{"@type": "PostalAddress", %s}}'
            % (json_text(t["ort"]),
               ", ".join('%s: %s' % (json_text(k), json_text(v))
                         for k, v in adresse_zerlegen(t["adresse"]).items())),
        ]
        if t["ticket"]:
            # Bei einem abgesagten Konzert waere "InStock" eine falsche
            # Auskunft an Google -- und Google zeigt sie dem Publikum an.
            verf = "SoldOut" if t["abgesagt"] else "InStock"
            felder.append('    "offers": {"@type": "Offer", "url": %s, '
                          '"availability": "https://schema.org/%s"}'
                          % (json_text(t["ticket"]), verf))
        bloecke.append('<script type="application/ld+json">\n{\n%s\n}\n</script>'
                       % ",\n".join(felder))
    return "\n".join(bloecke)


def sitemap(heute):
    zeilen = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for name, _, _, _, _ in SEITEN:
        ziel = "" if name == "start" else "%s.html" % name
        zeilen.append("  <url><loc>%s/%s</loc><lastmod>%s</lastmod></url>"
                      % (DOMAIN, ziel, heute.isoformat()))
    zeilen.append("</urlset>")
    return "\n".join(zeilen) + "\n"


# Crawler, die ausschliesslich Trainingsmaterial sammeln. Sie bringen keine
# Sichtbarkeit -- kein Nutzer sieht je eine Antwort, in der diese Seite wegen
# ihnen auftaucht. Gesperrt werden sie wegen der Fotos: Nach dem Urteil des
# OLG Hamburg vom 10.12.2025 ist ein Nutzungsvorbehalt in natuerlicher Sprache
# nicht "maschinenlesbar" im Sinne des § 44b Abs. 3 UrhG. Ein Satz im
# Impressum genuegt also nicht; die robots.txt ist der einzige derzeit
# belastbare Ort dafuer.
NUR_TRAINING = [
    "GPTBot",            # OpenAI, Modelltraining
    "ClaudeBot",         # Anthropic, Modelltraining
    "anthropic-ai",      # aeltere Anthropic-Kennung
    "Applebot-Extended",  # Apple Intelligence, reines Trainings-Opt-out
    "CCBot",             # Common Crawl, speist zahlreiche Trainingskorpora
    "Bytespider",        # ByteDance
    "Meta-ExternalAgent",
    "FacebookBot",
    "cohere-ai",
    "Diffbot",
    "ImagesiftBot",
    "omgilibot",
    "PanguBot",
    "Timpibot",
]

# Diese holen Seiten, um sie in Antworten zu zeigen und zu verlinken. Sie sind
# der Grund, ueberhaupt auffindbar sein zu wollen, und bleiben deshalb offen.
# Sie stehen hier nur als Kommentar -- "User-agent: *" erlaubt sie bereits,
# und eine ueberfluessige Allow-Zeile ist eine Zeile, die irgendwann veraltet:
#   Googlebot, bingbot, Applebot, DuckDuckBot   (klassische Suche)
#   OAI-SearchBot, ChatGPT-User                 (OpenAI, Suche und Nutzeraufruf)
#   PerplexityBot, Perplexity-User              (Perplexity)
#   Claude-SearchBot, Claude-User               (Anthropic)
#
# Google-Extended steht bewusst NICHT in NUR_TRAINING. Es steuert laut Googles
# Dokumentation das Training von Gemini *und* das Grounding -- wer es sperrt,
# verschwindet aus Gemini-Antworten. Auf Google Search hat es keine Wirkung:
# "Google-Extended does not impact a site's inclusion in Google Search nor is
# it used as a ranking signal in Google Search." Hier gewinnt die Sichtbarkeit.
# Soll das umgekehrt entschieden werden, gehoert der Name in die Liste oben.


def robots():
    if VEROEFFENTLICHEN:
        zeilen = ["# Suchmaschinen und Antwortdienste sind willkommen.",
                  "User-agent: *", "Allow: /", ""]
        zeilen.append("# Reine Trainings-Crawler: siehe NUR_TRAINING in "
                      "generate_webseite.py")
        for bot in NUR_TRAINING:
            zeilen += ["User-agent: %s" % bot, "Disallow: /", ""]
        zeilen.append("Sitemap: %s/sitemap.xml" % DOMAIN)
        return "\n".join(zeilen) + "\n"
    # Disallow UND noindex im Kopf jeder Seite. Disallow allein verhindert nur
    # das Crawlen; die URL kann trotzdem im Index auftauchen.
    return ("# Die Seite ist im Aufbau und soll nicht in Suchmaschinen erscheinen.\n"
            "# Zusaetzlich traegt jede Seite ein noindex im Kopf.\n"
            "User-agent: *\nDisallow: /\n")


def fingerabdruck(pfad):
    """
    Kurzer Hash des Dateiinhalts, wird als ?v=... an Verweise gehaengt.

    Ohne das haelt der Browser eine geaenderte Datei unter gleichem Namen
    fuer dieselbe und zeigt weiter die alte. Genau das ist am 27.09.2026
    passiert: das Portraetfoto wurde dreimal ersetzt, im Browser blieb die
    erste Fassung stehen, und es sah nach einem Fehler in der Seite aus.
    """
    import hashlib
    if not os.path.isfile(pfad):
        return ""
    with open(pfad, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:8]


def navigation(aktuell):
    teile = ['<nav class="nav" aria-label="Hauptnavigation"><ul>']
    for name, titel, _, _, _ in SEITEN:
        if name in ("impressum", "datenschutz"):
            continue
        ziel = "index.html" if name == "start" else "%s.html" % name
        if name == aktuell:
            teile.append('<li><a href="%s" aria-current="page">%s</a></li>' % (ziel, titel))
        else:
            teile.append('<li><a href="%s">%s</a></li>' % (ziel, titel))
    teile.append("</ul></nav>")
    return "\n".join(teile)


def sicherheits_kopf():
    """
    Die zwei Sicherheitsregeln, die sich ohne Server setzen lassen.

    GitHub Pages liefert keine eigenen Kopfzeilen aus. Damit fallen
    Strict-Transport-Security und X-Frame-Options weg: die gibt es nur als
    echten HTTP-Header, nicht als Meta-Element. Was bleibt, ist die CSP und
    die Referrer-Regel -- beide wirken als Meta genauso, mit Ausnahme
    einzelner Direktiven (siehe frame-ancestors unten).

    script-src 'self' ist scharf: Die Seite laedt nur eigene Dateien, und
    Blockbausteine vom Typ application/ld+json zaehlen nicht als Skript.
    style-src braucht 'unsafe-inline', weil die Videovorschauen ihr Bild
    ueber ein style-Attribut setzen. frame-src laesst YouTube zu, aber erst
    nach dem Klick entsteht dort ueberhaupt ein Rahmen.
    """
    regeln = [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        "frame-src https://www.youtube.com",
        # Seit dem 29.09.2026 hat die Seite kein Formular mehr. 'none' statt
        # 'self' heisst: Auch ein eingeschleustes Formular findet kein Ziel.
        "form-action 'none'",
        "base-uri 'none'",
        "object-src 'none'",
        # frame-ancestors steht bewusst NICHT hier: Der Browser ignoriert die
        # Direktive in einem Meta-Element und schreibt eine Warnung in die
        # Konsole. Eine Regel, die nichts tut, aber nach Schutz aussieht, ist
        # schlimmer als ihr Fehlen. Gegen Einbettung in fremde Rahmen hilft
        # nur X-Frame-Options oder frame-ancestors als echter HTTP-Header,
        # und Kopfzeilen kann GitHub Pages nicht setzen.
        "upgrade-insecure-requests",
    ]
    return ('<meta http-equiv="Content-Security-Policy" content="%s">\n'
            '<meta name="referrer" content="strict-origin-when-cross-origin">'
            % "; ".join(regeln))


def social_kopf(titel, beschreibung, url):
    """
    Open Graph und Twitter Cards. Beides zusammen, weil die Dienste sich
    nicht einig sind: WhatsApp, Facebook, LinkedIn und Signal lesen og:*,
    X liest twitter:*. Wer nur eines setzt, hat in der Haelfte der Faelle
    wieder den grauen Kasten.
    """
    bild = "%s/bilder/%s" % (DOMAIN, OG_DATEI)
    m = [
        ('meta', 'property', 'og:type', 'website'),
        ('meta', 'property', 'og:site_name', ENSEMBLE),
        ('meta', 'property', 'og:locale', 'de_DE'),
        ('meta', 'property', 'og:title', titel),
        ('meta', 'property', 'og:description', beschreibung),
        ('meta', 'property', 'og:url', url),
        ('meta', 'property', 'og:image', bild),
        ('meta', 'property', 'og:image:width', str(OG_BREITE)),
        ('meta', 'property', 'og:image:height', str(OG_HOEHE)),
        ('meta', 'property', 'og:image:alt', OG_ALT),
        ('meta', 'name', 'twitter:card', 'summary_large_image'),
        ('meta', 'name', 'twitter:title', titel),
        ('meta', 'name', 'twitter:description', beschreibung),
        ('meta', 'name', 'twitter:image', bild),
        ('meta', 'name', 'twitter:image:alt', OG_ALT),
    ]
    return "\n".join('<%s %s="%s" content="%s">' % (t, a, k, html.escape(v, quote=True))
                     for t, a, k, v in m)


def og_bild_bauen(bilderordner):
    """
    Schneidet das Vorschaubild auf 1.91:1, das Format, das die Dienste
    erwarten. Wird es nicht geliefert, schneiden sie selbst -- und zwar
    mittig, was bei diesem Foto die Fuesse behaelt und die Koepfe verliert.
    """
    quelle = os.path.join(bilderordner, OG_QUELLE)
    if not os.path.isfile(quelle):
        raise Abbruch("Vorschaubild fehlt: %s. Erwartet wird %s im Bilderordner."
                      % (quelle, OG_QUELLE))
    from PIL import Image, ImageFilter
    bild = Image.open(quelle)
    ziel_verh = OG_BREITE / float(OG_HOEHE)
    if bild.width / float(bild.height) > ziel_verh:
        # zu breit: seitlich beschneiden, mittig
        neu_b = int(round(bild.height * ziel_verh))
        links = (bild.width - neu_b) // 2
        bild = bild.crop((links, 0, links + neu_b, bild.height))
    else:
        # zu hoch: oben und unten beschneiden, Schnittmitte nach OG_SCHNITT
        neu_h = int(round(bild.width / ziel_verh))
        mitte = bild.height * OG_SCHNITT
        oben = int(round(mitte - neu_h / 2.0))
        oben = max(0, min(oben, bild.height - neu_h))
        bild = bild.crop((0, oben, bild.width, oben + neu_h))
    bild = bild.resize((OG_BREITE, OG_HOEHE), Image.LANCZOS)
    bild = bild.filter(ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=3))
    bild.save(os.path.join(bilderordner, OG_DATEI), quality=84, optimize=True)


def seite_bauen(vorlage, name, titel, beschreibung, inhalt, braucht_filter,
                jsonld="", suchtitel=""):
    ziel = "index.html" if name == "start" else "%s.html" % name
    kopf = ""
    if not VEROEFFENTLICHEN:
        kopf = '<meta name="robots" content="noindex, nofollow">'
    skripte = []
    # termine.js vor filter.js: Es haengt verstrichene Termine um, der
    # Ortsfilter soll schon die nachgefuehrte Liste sehen. Beide tragen
    # defer und laufen deshalb in dieser Reihenfolge.
    if name in ("termine", "start"):
        skripte.append('<script src="termine.js?v=%s" defer></script>'
                       % fingerabdruck(os.path.join(HIER, "src", "termine.js")))
    if braucht_filter:
        skripte.append('<script src="filter.js?v=%s" defer></script>'
                       % fingerabdruck(os.path.join(HIER, "src", "filter.js")))
    if name == "musik":
        skripte.append('<script src="video.js?v=%s" defer></script>'
                       % fingerabdruck(os.path.join(HIER, "src", "video.js")))
    if name == "start":
        skripte.append('<script src="stimmen.js?v=%s" defer></script>'
                       % fingerabdruck(os.path.join(HIER, "src", "stimmen.js")))
    skript = "\n".join(skripte)
    # Im Suchergebnis steht der Suchtitel, auf der Seite die Ueberschrift.
    # "Kontakt" sagt einem Veranstalter, der googelt, nichts; "Streichquartett
    # buchen" schon. Ist kein Suchtitel gesetzt, bleibt es beim Seitentitel.
    basis = suchtitel or titel
    voller_titel = basis if name == "start" else "%s – %s" % (basis, ENSEMBLE)
    css_v = fingerabdruck(os.path.join(HIER, "src", "stil.css"))
    seiten_url = "%s/%s" % (DOMAIN, "" if name == "start" else ziel)
    social = social_kopf(voller_titel, beschreibung, seiten_url)
    sicherheit = sicherheits_kopf()
    return vorlage \
        .replace("stil.css\"", "stil.css?v=%s\"" % css_v) \
        .replace("{{TITEL}}", html.escape(voller_titel)) \
        .replace("{{BESCHREIBUNG}}", html.escape(beschreibung)) \
        .replace("{{ROBOTS}}", kopf) \
        .replace("{{CANONICAL}}", seiten_url) \
        .replace("{{SOCIAL}}", social) \
        .replace("{{SICHERHEIT}}", sicherheit) \
        .replace("{{SEITE}}", "seite--%s" % name) \
        .replace("{{NAV}}", navigation(name)) \
        .replace("{{INHALT}}", inhalt) \
        .replace("{{JAHR}}", str(datetime.date.today().year)) \
        .replace("{{SKRIPT}}", skript) \
        .replace("{{JSONLD}}", jsonld)


def bilder_kopieren(quelle, ziel, maxbreite=2000):
    # 2000 statt vormals 1600: Der Bildband auf der Ensembleseite wird ueber
    # die volle Seitenspalte von 1088 px dargestellt. Auf einem Schirm mit
    # doppelter Punktdichte braucht das 2176 px; mit 1600 war das Bild dort
    # sichtbar weich. 2000 ist der Kompromiss aus Schaerfe und Ladezeit.
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
    from PIL import ImageOps, ImageFilter
    os.makedirs(ziel, exist_ok=True)
    # Zuerst aufraeumen: Was im Quellordner nicht mehr liegt, muss auch aus
    # dem Generat verschwinden. Der Generator ergaenzte bisher nur, und
    # export.sh spiegelt build/ eins zu eins nach gh-pages -- ein geloeschtes
    # Bild waere also online liegengeblieben. Bei neun ausgetauschten
    # Videovorschauen ist das Unordnung; bei einem Bild, das aus Rechtegruenden
    # weg muss, ist es der eigentliche Schaden.
    # Das Vorschaubild wird erzeugt und liegt deshalb nicht in der Quelle.
    # Ohne diese Ausnahme wuerde es hier jedes Mal geloescht.
    bekannt = set(dateien) | {OG_DATEI}
    for f in os.listdir(ziel):
        if f not in bekannt and os.path.isfile(os.path.join(ziel, f)):
            os.remove(os.path.join(ziel, f))
    for f in dateien:
        bild = Image.open(os.path.join(quelle, f))
        # EXIF-Drehung anwenden. Viele Kameras speichern Hochformat als
        # Querformat mit einem Drehvermerk; wer den ignoriert, legt das
        # Bild auf die Seite.
        bild = ImageOps.exif_transpose(bild)
        if bild.mode != "RGB":
            bild = bild.convert("RGB")
        if bild.width > maxbreite:
            hoehe = int(bild.height * maxbreite / float(bild.width))
            bild = bild.resize((maxbreite, hoehe), Image.LANCZOS)
        # Portraets entfaerben. Die sieben Fotos kommen aus sieben Quellen,
        # mit verschiedenen Hintergruenden und verschiedenem Licht. In Farbe
        # nebeneinander wirkt das zusammengewuerfelt; entfaerbt wird daraus
        # eine Reihe. Erkannt am Dateinamen, damit das Gruppenfoto in Farbe
        # bleibt.
        if f.startswith("portraet_"):
            bild = ImageOps.grayscale(bild).convert("RGB")
        # Unschaerfemaske zum Schluss. Jedes Verkleinern kostet Kanten, und
        # die Quellen sind Handyfotos, die schon vor dem Verkleinern weich
        # sind. Radius klein und Schwelle 3, damit das Bildrauschen in
        # Waenden und Himmel nicht mitgeschaerft wird -- ohne Schwelle sieht
        # eine glatte Flaeche danach griesig aus.
        #
        # Das Schaerfen steht hier und nicht in den Vault-Dateien: zweimal
        # geschaerft gibt Saeume an Kontrastkanten, und welche Datei schon
        # durch war, sieht man ihr nicht an.
        bild = bild.filter(ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=3))
        bild.save(os.path.join(ziel, f), quality=84, optimize=True, progressive=True)
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
        # Alle kommenden ins HTML, nicht nur drei: Welche drei die
        # Startseite zeigt, entscheidet termine.js im Browser. Jede feste
        # Obergrenze ist eine Wette darauf, wie viele Termine zwischen zwei
        # Exporten verstreichen. Mit zwoelf getestet und prompt verloren --
        # ein Build vom 1. September hatte am 27. nur noch zwei uebrig,
        # weil zehn der zwoelf vorbei waren.
        #
        # Ohne JavaScript stehen dann alle Termine auf der Startseite. Das
        # ist lang, aber richtig; drei veraltete waeren kurz und falsch.
        liste_kurz, _, _ = termine_html(termine, heute, nur_naechste=len(termine) or 1)

        # Bilder zuerst, damit beim Seitenbau ihr Fingerabdruck vorliegt.
        bilder_ziel = os.path.join(args.ausgabe, "bilder")
        anz_bilder = bilder_kopieren(BILDER_QUELLE, bilder_ziel)
        og_bild_bauen(bilder_ziel)

        # Was am Ende im Ausgabeordner liegen darf. Alles andere fliegt raus,
        # siehe die Aufraeumschleife weiter unten.
        erwartet = {"bilder", "sitemap.xml", "robots.txt"}

        gebaut = 0
        for name, _, titel, beschreibung, suchtitel in SEITEN:
            quelle = os.path.join(HIER, "src", "seiten", "%s.md" % name)
            if not os.path.isfile(quelle):
                raise Abbruch("Seiteninhalt fehlt: %s" % quelle)
            roh = io.open(quelle, encoding="utf-8").read()
            inhalt = markdown_zu_html(roh, "%s.md" % name)
            # Bildverweise mit Fingerabdruck versehen, damit ein ersetztes
            # Bild im Browser auch wirklich neu geladen wird.
            def _bild_v(m):
                datei = m.group(1)
                v = fingerabdruck(os.path.join(args.ausgabe, "bilder", os.path.basename(datei)))
                return 'src="%s?v=%s"' % (datei, v) if v else m.group(0)
            inhalt = re.sub(r'src="(bilder/[^"?]+)"', _bild_v, inhalt)
            inhalt = inhalt.replace("<p>{{TERMINE}}</p>", liste_voll)
            inhalt = inhalt.replace("<p>{{TERMINE_KURZ}}</p>", liste_kurz)
            inhalt = inhalt.replace("<p>{{PROGRAMME}}</p>", programme_html(termine))
            ziel = "index.html" if name == "start" else "%s.html" % name
            erwartet.add(ziel)
            if name == "start":
                jsonld = json_ensemble()
            elif name == "termine":
                jsonld = json_termine(termine, heute)
            else:
                jsonld = ""
            io.open(os.path.join(args.ausgabe, ziel), "w", encoding="utf-8").write(
                seite_bauen(vorlage, name, titel, beschreibung, inhalt,
                            braucht_filter=("{{TERMINE}}" in roh), jsonld=jsonld,
                            suchtitel=suchtitel))
            gebaut += 1

        # statische Dateien unveraendert uebernehmen
        statisch = os.path.join(HIER, "static")
        kopiert = 0
        if os.path.isdir(statisch):
            for f in sorted(os.listdir(statisch)):
                q = os.path.join(statisch, f)
                if os.path.isfile(q):
                    # .nojekyll verhindert, dass GitHub das fertige HTML noch
                    # durch Jekyll schickt. Ohne die Datei schlaegt der Build
                    # fehl oder verschluckt Dateien mit Unterstrich.
                    # Binaer kopieren: seit dem 08.10.2026 liegen hier auch
                    # die Icons. Die alte Textkopie haette sie zerstoert.
                    shutil.copyfile(q, os.path.join(args.ausgabe, f))
                    erwartet.add(f)
                    kopiert += 1

        for name in ("stil.css", "termine.js", "filter.js", "video.js",
                     "stimmen.js"):
            q = os.path.join(HIER, "src", name)
            if os.path.isfile(q):
                io.open(os.path.join(args.ausgabe, name), "w", encoding="utf-8").write(
                    io.open(q, encoding="utf-8").read())
                erwartet.add(name)

        # Sitemap und robots.txt entstehen auch im noindex-Zustand. Sie schaden
        # nicht, und so ist beim Umlegen des Schalters nichts nachzuziehen.
        io.open(os.path.join(args.ausgabe, "sitemap.xml"), "w",
                encoding="utf-8").write(sitemap(heute))
        io.open(os.path.join(args.ausgabe, "robots.txt"), "w",
                encoding="utf-8").write(robots())

        # Aufraeumen. Der Generator ergaenzte bisher nur, und export.sh spiegelt
        # build/ eins zu eins nach gh-pages -- eine geloeschte Seite oder ein
        # abgehaengtes Skript blieb damit online. Fuer Bilder wird das seit dem
        # 28.09.2026 abgefangen, fuer alles andere nicht: Beim Entfernen des
        # Anfrageformulars am 29.09. waere formular.js liegengeblieben, samt
        # der Formularlogik, die es auf keiner Seite mehr gibt.
        entfernt = 0
        for f in sorted(os.listdir(args.ausgabe)):
            if f in erwartet or f.startswith("."):
                continue
            pfad = os.path.join(args.ausgabe, f)
            if os.path.isfile(pfad):
                os.remove(pfad)
                entfernt += 1

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
    if entfernt:
        print("Verwaiste entfernt: %d" % entfernt)
    print("Bilder:            %d" % anz_bilder)
    print("Sichtbarkeit:      %s" % ("oeffentlich, indexierbar" if VEROEFFENTLICHEN
                                     else "noindex (nicht in Suchmaschinen)"))
    print("Ausgabe:           %s" % args.ausgabe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
