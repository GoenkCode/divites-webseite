#!/usr/bin/env bash
# Baut die Seite aus dem Vault und veroeffentlicht sie.
#
# Warum kein GitHub-Actions-Workflow: Der Build braucht die Termindatei aus
# dem lokalen Obsidian-Vault. Den gibt es auf GitHub nicht. Ein Workflow
# muesste aus einer mitgepushten Kopie bauen — doppelte Datenhaltung fuer
# nichts, und er verlangt einen workflow-Scope, den die CLI-Anmeldung nicht
# hat. Also wird lokal gebaut und nur das Ergebnis ausgeliefert.
#
# Der Branch gh-pages wird ueber ein separates git-worktree befuellt.
# Die naheliegende Variante — im Arbeitsverzeichnis den Branch wechseln und
# aufraeumen — haette rm -rf auf den Quellbaum losgelassen. Bricht das mitten
# drin ab, steht man vor einem halb geloeschten Repo. Ein worktree fasst das
# Arbeitsverzeichnis nicht an.
#
#   ./export.sh            baut und veroeffentlicht
#   ./export.sh --nur-bau  baut nur, veroeffentlicht nicht
set -euo pipefail

HIER="$(cd "$(dirname "$0")" && pwd)"
cd "$HIER"

echo "== Bauen =="
python3 generate_webseite.py

# Ein Deploy mit leerer Terminliste waere schlimmer als ein veralteter Stand.
# '<li class="termin' statt 'class="termin"': seit der Monatsgliederung
# tragen Folgetermine am selben Tag die Klasse "termin termin--folge".
# Die alte Zaehlung traf die nicht und meldete 24 statt 40 - eine
# Sicherung, die zu niedrig zaehlt, schlaegt irgendwann falsch an.
anzahl="$(grep -c '<li class="termin' build/termine.html || true)"
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

WT="$(mktemp -d)"
aufraeumen() {
  git worktree remove --force "$WT" >/dev/null 2>&1 || true
  rm -rf "$WT"
}
trap aufraeumen EXIT

if git show-ref --verify --quiet refs/heads/gh-pages; then
  git worktree add -q "$WT" gh-pages
else
  git worktree add -q --detach "$WT"
  git -C "$WT" checkout -q --orphan gh-pages
  git -C "$WT" rm -rq --cached . >/dev/null 2>&1 || true
fi

# Nur innerhalb des worktree loeschen, nie im Quellbaum.
find "$WT" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R build/. "$WT"/

git -C "$WT" add -A
if git -C "$WT" diff --cached --quiet; then
  echo "   Keine Aenderung gegenueber dem veroeffentlichten Stand."
  exit 0
fi

git -C "$WT" commit -q -m "Stand $(date '+%Y-%m-%d %H:%M')"
git -C "$WT" push -q --force origin gh-pages
echo "   Veroeffentlicht. GitHub Pages aktualisiert in ein bis zwei Minuten."
