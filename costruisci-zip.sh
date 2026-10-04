#!/bin/bash
# Costruisce dist/visibilita-ai-<versione>.zip dal sorgente kit/ (e la copia a nome fisso per le release).
# I file stanno dentro una sola cartella visibilita-ai/: "Estrai tutto" e Archive Utility non annidano.
set -euo pipefail
QUI="$(cd "$(dirname "$0")" && pwd)"
VER="${1:?uso: $0 <versione, es. 1.0.0>}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/kitvai.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/visibilita-ai" "$QUI/dist"
cp -R "$QUI/kit/." "$TMP/visibilita-ai/"
cd "$TMP/visibilita-ai"
find . \( -name .DS_Store -o -name __pycache__ -o -name .cc-writes -o -name "*.pyc" -o -name .claude \) -prune -exec rm -rf {} +
# niente stato di un utente nello zip
rm -rf progetti/*/ ; touch progetti/.gitkeep
for f in chiavi-api.txt risposte-test.json; do
  [ ! -e "$f" ] || { echo "ERRORE: $f non deve stare nello zip" >&2; exit 1; }
done
# niente chiavi e niente riferimenti aziendali
if grep -rIlE "sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|pplx-[A-Za-z0-9]{20,}" . ; then
  echo "ERRORE: possibile chiave API nei file sopra" >&2; exit 1; fi
# parole da non pubblicare (una per riga) in .parole-vietate, file locale escluso da git
VIETATE="/Users/"
[ -f "$QUI/.parole-vietate" ] && VIETATE="$VIETATE|$(grep -v '^\s*$' "$QUI/.parole-vietate" | paste -sd'|' -)"
if grep -rIliE "$VIETATE" --exclude=LICENSE . ; then
  echo "ERRORE: riferimenti personali o aziendali nei file sopra" >&2; exit 1; fi
sed -i '' "s/^__version__ = .*/__version__ = \"$VER\"/" motore/__init__.py
chmod +x avvia.py avvia-mac.command
cd "$TMP"
ZIP="$QUI/dist/visibilita-ai-$VER.zip"
rm -f "$ZIP"
zip -qr -X "$ZIP" visibilita-ai
cd "$QUI/dist" && shasum -a 256 "$(basename "$ZIP")" > "$(basename "$ZIP").sha256"
cp "$ZIP" visibilita-ai.zip && shasum -a 256 visibilita-ai.zip > visibilita-ai.zip.sha256
echo "Creato $ZIP"; cat "$(basename "$ZIP").sha256"
