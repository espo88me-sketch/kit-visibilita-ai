"""Collaudo offline: piattaforme finte, nessuna spesa.

Uso: python3 test/test_offline.py <cartella-kit-di-prova>
Copia il kit in una cartella temporanea e ci lavora dentro, per non sporcare il sorgente.
"""
import json, os, random, sys, shutil
from pathlib import Path

kit = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(kit))
os.environ.update({"OPENAI_API_KEY": "sk-finta-1234567890", "GEMINI_API_KEY": "g-finta-1234567890",
                   "PERPLEXITY_API_KEY": "pplx-finta-1234567890"})
from motore import piattaforme as P, misura as MI, flusso as F, util as U, domande as DOM, segnali as S

MI.INTERVALLO["gemini"] = 0.0
import time as _t
MI.time.sleep = lambda s: None   # niente attese nei retry durante il test
random.seed(7)
chiamate = {"n": 0}
errori_iniettati = {"n": 0}

def finta(x):
    def f(chiave, domanda, modello, paese=""):
        chiamate["n"] += 1
        r = random.random()
        if r < 0.04:
            errori_iniettati["n"] += 1
            raise U.ErroreHTTP(429, "rate limit, slow down")
        if r < 0.06:
            errori_iniettati["n"] += 1
            raise U.ErroreHTTP(503, "overloaded")
        brand = "Acme Yoga" if random.random() < {"chatgpt": .3, "gemini": .15, "perplexity": .5}[x] else ""
        conc = random.choice(["", "YogaStar", "Zen Online", "YogaStar e Zen Online"])
        testo = (f"## Le migliori opzioni\n\n1. **{conc or 'Studio Om'}** è molto apprezzato.\n"
                 + (f"2. {brand} è una scelta consigliata per chi inizia, con prezzi chiari.\n" if brand else "")
                 + "3. Anche le palestre locali offrono corsi. [1][2]")
        fonti = [{"url": "https://www.yogajournal.com/a", "dominio": "yogajournal.com"},
                 {"url": "https://it.wikipedia.org/wiki/Yoga", "dominio": "it.wikipedia.org"}]
        if random.random() < {"chatgpt": .2, "gemini": .1, "perplexity": .4}[x]:
            pag = random.choice(["/", "/corsi/principianti/", "/prezzi?utm_source=openai"])
            fonti.append({"url": "https://acmeyoga.it" + pag, "dominio": "acmeyoga.it"} if x != "gemini" or random.random() < .5
                         else {"url": "", "dominio": "acmeyoga.it"})
        if "YogaStar" in conc:
            fonti.append({"url": "https://yogastar.com/x", "dominio": "yogastar.com"})
        return {"testo": testo, "fonti": fonti, "costo": 0.01, "modello": P.MODELLI_DEFAULT[x]}
    return f

for x in P.ORDINE:
    P.CHIEDI[x] = finta(x)

def json_finto(chiave, istruzioni, modello=None):
    if "domande" in istruzioni and "COSA DEVI PRODURRE" in istruzioni:
        n = int(istruzioni.split("COSA DEVI PRODURRE\n")[1].split(" domande")[0])
        out = []
        for i in range(n):
            fase = ["scoperta", "scelta", "confronto", "acquisto", "brand"][i % 5]
            t = f"Domanda finta numero {i} sullo yoga online per principianti"
            if fase == "brand": t = f"Acme Yoga è affidabile? variante {i}"
            out.append({"domanda": t, "fase": fase, "vincolo": "budget"})
        # una domanda generica che contiene il brand: deve diventare 'brand'
        out.append({"domanda": "Meglio acmeyoga.it o altri siti per lo yoga?", "fase": "scelta", "vincolo": ""})
        # un doppione
        out.append({"domanda": out[0]["domanda"], "fase": "scoperta", "vincolo": ""})
        return {"domande": out}, 0.001
    return {"si_riferisce_al_brand": random.random() > .1, "ruolo": random.choice(S.RUOLI),
            "tono": random.choice(S.TONI), "cosa_dice": f"frase finta {random.randint(1, 30)}"}, 0.0005

for x in P.JSON_SERVIZIO:
    P.JSON_SERVIZIO[x] = json_finto

risposte = {"sito": "https://www.acmeyoga.it/", "brand": "Acme Yoga", "alias": ["AcmeYoga"],
            "offerta": "corsi di yoga online", "pubblico": "principianti", "zona": "online",
            "mercato": {"lingua": "it", "paese": "IT"},
            "concorrenti": ["YogaStar (yogastar.com)", "yogastar.com", "Zen Online"],
            "domande_clienti": ["Come inizio lo yoga da casa senza istruttore?"],
            "piattaforme": ["chatgpt", "gemini", "perplexity"], "n_domande": 15, "ripetizioni": 3, "tetto_spesa": 5}
fr = kit / "risposte-test.json"
fr.write_text(json.dumps(risposte), encoding="utf-8")

print("=== crea ==="); F.da_riga_di_comando(["--crea", str(fr)])
p = F.carica_progetto("acmeyoga.it")
print("\nconcorrenti normalizzati:", p["concorrenti"])
dom = DOM.carica(Path(p["_cartella"]) / "domande.csv", p)
print("domande:", len(dom), {t: sum(d["tipo"] == t for d in dom) for t in ("generica", "brand")})
assert len(dom) == 15, len(dom)
assert any(d["domanda"].startswith("Come inizio lo yoga") for d in dom), "domanda cliente persa"
assert all(d["tipo"] == "brand" for d in dom if "acme" in d["domanda"].lower()), "riclassificazione brand"
print("\n=== misura ==="); F.da_riga_di_comando(["--misura", "acmeyoga.it", "--si", "--non-aprire"])
c = F.cartelle_misure(p)[-1]
n_ok = len(MI.carica_risposte(c / "risposte.jsonl"))
print("risposte valide:", n_ok, "chiamate:", chiamate["n"], "errori iniettati:", errori_iniettati["n"])
print("\n=== ripresa (non deve rifare nulla) ===")
prima = chiamate["n"]
F.da_riga_di_comando(["--misura", "acmeyoga.it", "--si", "--non-aprire"])
print("chiamate nuove alla ripresa:", chiamate["n"] - prima)
assert chiamate["n"] - prima == 0, "la ripresa di una misura completa non deve spendere"
assert [c["nome"] for c in p["concorrenti"]] == ["YogaStar", "Zen Online"], p["concorrenti"]
print("\n=== seconda misura (confronto) ===")
F.da_riga_di_comando(["--misura", "acmeyoga.it", "--si", "--nuova", "--non-aprire"])
html = (Path(p["_cartella"]) / "dashboard.html").read_text(encoding="utf-8")
for frase in ("In breve", "Rispetto alla misura del", "Tu e i concorrenti", "I limiti di questa analisi", "Le tue pagine"):
    assert frase in html, frase
print("dashboard OK,", len(html) // 1024, "KB")
print("\n=== tetto di spesa: misura con tetto 0,20$ ===")
p["tetto_spesa"] = 0.2; F.salva_progetto(p)
prima = chiamate["n"]
F.da_riga_di_comando(["--misura", "acmeyoga.it", "--si", "--nuova", "--non-aprire"])
c = F.cartelle_misure(p)[-1]
speso = MI.costo_registrato(c / "risposte.jsonl") + MI.costo_registrato(c / "giudizi.jsonl")
print(f"speso {speso:.3f} con tetto 0.20 → chiamate {chiamate['n'] - prima}")
assert speso <= 0.2 + 1e-9
print("\nTUTTO OK")
