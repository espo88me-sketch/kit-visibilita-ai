#!/bin/bash
# Doppio clic per avviare il kit su Mac.
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 non è installato. Scaricalo da https://www.python.org/downloads/ e riprova."
  read -r -p "Premi Invio per chiudere..." _
  exit 1
fi
python3 avvia.py "$@"
echo
read -r -p "Fatto. Premi Invio per chiudere questa finestra..." _
