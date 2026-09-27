# divites-webseite

Quellcode der Webseite des [Divites Quartetts](https://divites-quartett.com).

Statische Seite, erzeugt von einem Python-Skript, ausgeliefert über GitHub Pages.

## Woher die Termine kommen

Die Konzerttermine werden **nicht hier** gepflegt, sondern in einem privaten Obsidian-Vault:

```
Musik_Brain/03_projekte/divites/termine.md
```

Dort steht eine Markdown-Tabelle mit den Spalten Datum, Uhrzeit, Ort, Adresse,
Programm, Ticketlink und Status. `generate_webseite.py` liest genau diese Tabelle
und baut daraus die Terminseite sowie die strukturierten Daten für Suchmaschinen.

Der Vault ist rein lokal und hat bewusst kein Remote. Ein Terminwechsel landet
deshalb nicht von selbst online — er wird durch einen Export ausgelöst.

## Bauen

```bash
python3 generate_webseite.py                  # nutzt den Standardpfad zum Vault
python3 generate_webseite.py --termine PFAD   # oder eine andere Quelle
```

Das Ergebnis landet in `build/`. Das Skript bricht ab, wenn die Termindatei fehlt,
leer ist oder keine gültige Zeile enthält — eine Seite mit leerer Terminliste wäre
schlimmer als eine veraltete.

## Sichtbarkeit

Oben in `generate_webseite.py` steht:

```python
VEROEFFENTLICHEN = False
```

Solange das `False` ist, bekommt jede Seite ein `noindex` und die `robots.txt` ein
`Disallow: /`. Die Seite ist dann über die Domain erreichbar, aber für Suchmaschinen
unsichtbar. Umgestellt wird erst, wenn die Inhalte stehen.

## Aufbau

```
src/vorlage.html     HTML-Grundgerüst
src/stil.css         das gesamte Design
src/seiten/*.md      Seiteninhalte
static/              wird unverändert nach build/ kopiert (CNAME, robots.txt)
mockups/             Design-Entwürfe zur Auswahl, nicht Teil der Seite
build/               Generat, nicht versioniert
```
