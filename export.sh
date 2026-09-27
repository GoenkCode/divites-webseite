#!/usr/bin/env bash
# Baut die Seite aus dem Vault und veroeffentlicht sie.
#
# Warum kein GitHub-Actions-Workflow: Der Build braucht die Termindatei aus
# dem lokalen Obsidian-Vault. Den gibt es auf GitHub nicht. Ein Workflow
# muesste aus einer mitgepushten Kopie bauen — doppelte Datenhaltung fuer
# nichts. Also wird lokal gebaut und nur das Ergebnis ausgeliefert.
#
#   ./export.sh            baut und veroeffentlicht
#   ./export.sh --nur-bau  baut nur, veroeffentlicht nicht
set -euo pipefail

HIER="$(cd "$(dirname "$0")" && pwd)"
cd "$HIER"

echo "== Bauen =="
python3 generate_webseite.py

# Ein Deploy mit leerer Terminliste waere schlimmer als ein veralteter Stand.
anzahl=$(grep -c 'class="termin"' build/termine.html || true)
if [ "${anzahl:-0}" -lt 1 ]; then
  echo "ABBRUCH: keine Termine im Generat." >&2
  exit 1
fi

# Ohne CNAME verwirft GitHub die eigene Domain bei jedem Deploy.
if [ ! -f build/CNAME ]; then
  echo "ABBRUCH: CNAME fehlt im Generat." >&2
  exit 1
fi

echo "   $anzahl Termine, CNAME vorhanden."

if [ "${1:-}" = "--nur-bau" ]; then
  echo "Nur gebaut, nichts veroeffentlicht."
  exit 0
fi

echo "== Veroeffentlichen =="
# Das Generat als eigener Branch. --force ist hier richtig: gh-pages ist
# reines Ergebnis, keine Historie, die jemand braucht.
git add -A build -f 2>/dev/null || true
TMP="$(mktemp -d)"
cp -R build/. "$TMP/"
git checkout -q --orphan gh-pages-neu
git rm -rq --cached . >/dev/null 2>&1 || true
find . -maxdepth 1 ! -name . ! -name .git ! -name build -exec rm -rf {} + 2>/dev/null || true
cp -R "$TMP"/. .
rm -rf "$TMP" build
git add -A
git commit -q -m "Stand $(date +%Y-%m-%d\ %H:%M)"
git branch -M gh-pages-neu gh-pages
git push -q --force origin gh-pages
git checkout -q main
git checkout -q -- . 2>/dev/null || true
echo "Veroeffentlicht. GitHub Pages aktualisiert in ein bis zwei Minuten."
