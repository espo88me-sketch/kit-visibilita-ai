#!/usr/bin/env python3
"""Visibilità AI — come ChatGPT, Gemini e Perplexity parlano del tuo sito.

Avvio:  python3 avvia.py        (su Windows: python avvia.py, oppure doppio clic su avvia-windows.bat)
Aiuto:  python3 avvia.py --help
"""
import sys

if sys.version_info < (3, 9):
    sys.exit("Serve Python 3.9 o più recente. Scaricalo da https://www.python.org/downloads/")

from motore.flusso import da_riga_di_comando  # noqa: E402

if __name__ == "__main__":
    try:
        da_riga_di_comando(sys.argv[1:])
    except KeyboardInterrupt:
        print("\n  Interrotto. Rilancia quando vuoi: il lavoro fatto è salvato.")
        sys.exit(130)
