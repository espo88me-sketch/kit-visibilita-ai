"""Collaudo offline: piattaforme finte, nessuna spesa.

Uso: python3 test/test_offline.py <cartella-kit-di-prova>
Copia il kit in una cartella temporanea e ci lavora dentro, per non sporcare il sorgente.
"""
import json, os, random, sys, shutil
from pathlib import Path

kit = Path(sys.path[0]).resolve()
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

