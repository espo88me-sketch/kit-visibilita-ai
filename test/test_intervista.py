"""Simula un utente che risponde all'intervista interattiva (piattaforme finte, zero spesa)."""
import builtins, getpass, os, sys
from pathlib import Path
kit = Path(sys.argv[1]).resolve(); sys.path.insert(0, str(kit))
for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "PERPLEXITY_API_KEY"):
    os.environ.pop(k, None)
sys.argv = [sys.argv[0]]
import test_offline_fakes as T  # noqa
from motore import flusso as F
risposte = iter([
    "www.Pizzeria-Da-Mario.it/menu",   # sito
    "",                                # brand: default
    "Da Mario, Pizzeria Mario",        # alias
    "",                                # offerta vuota → deve richiederla
    "pizzeria napoletana con consegna a domicilio",
    "famiglie e studenti",
    "Bologna",
    "1",                               # mercato Italia
    "Pizzeria Rossa (pizzeriarossa.it), Domino's",
    "Qual è la pizza più buona a Bologna con consegna dopo le 23?",
    "",                                # fine domande
    "s",                               # salva chiavi
    "1",                               # dimensione rapida
    "",                                # tetto default
    "1",                               # domande vanno bene
    "s",                               # parto
])
builtins.input = lambda prompt="": (print(prompt, end=""), (r := next(risposte)), print(r))[1]
chiavi = iter(["sk-finta-chiave-1234567890", "", "pplx-finta-1234567890"])
getpass.getpass = lambda prompt="": (print(prompt + "****"), next(chiavi))[1]
F.verifica_chiave = lambda x, k: (True, "")
import webbrowser; webbrowser.open = lambda *a, **k: True
F.interattivo()
p = F.carica_progetto("pizzeria-da-mario.it")
print("\nPROGETTO:", {k: p[k] for k in ("dominio", "brand", "alias", "zona", "concorrenti", "piattaforme", "tetto_spesa", "n_domande")})
assert p["brand"] == "Pizzeria Da Mario" and p["piattaforme"] == ["chatgpt", "perplexity"]
assert (kit / "chiavi-api.txt").exists()
print("INTERVISTA OK")
