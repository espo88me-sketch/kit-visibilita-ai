"""La misura: ogni domanda, su ogni piattaforma scelta, ripetuta più volte.

Perché ripetere: gli assistenti AI non danno sempre la stessa risposta. Una
sola interrogazione misura il caso, non la visibilità. Il metodo chiede 3-5
ripetizioni per domanda, in una finestra di 24-72 ore.

Garanzie:
- la risposta grezza si salva PRIMA di qualsiasi elaborazione (risposte.jsonl):
  l'analisi si può rifare gratis in ogni momento;
- se la misura si interrompe (Ctrl+C, rete, credito) si riprende da dove era
  rimasta senza ripagare le risposte già raccolte;
- il tetto di spesa non si supera: prima di ogni chiamata si "prenota" il
  costo stimato, dopo si scala il costo vero.
"""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from . import piattaforme as P
from . import segnali as S
from .util import (blocca_piattaforma, errore_leggibile, giallo, non_riprovare, rosso,
                   tenue, verde)

TENTATIVI = 4
# Thread per piattaforma, separati: se Gemini rallenta per il suo limite al
# minuto, ChatGPT e Perplexity non devono aspettarlo.
LAVORATORI = {"chatgpt": 4, "gemini": 1, "perplexity": 2}
# Distanza minima fra due chiamate alla stessa piattaforma (secondi). Gemini col
# piano gratuito accetta circa 10 richieste al minuto; Perplexity ai livelli
# base circa 50 al minuto per sonar-pro.
INTERVALLO = {"gemini": 6.5, "chatgpt": 0.0, "perplexity": 1.4}
ERRORI_CONSECUTIVI_MAX = 5


class Cassa:
    """Tiene il conto della spesa, condiviso fra i thread."""

    def __init__(self, tetto, gia_speso=0.0):
        self.tetto = tetto
        self.speso = gia_speso
        self.prenotato = 0.0
        self._l = threading.Lock()

    def prenota(self, stima) -> bool:
        with self._l:
            if self.speso + self.prenotato + stima > self.tetto:
                return False
            self.prenotato += stima
            return True

    def salda(self, stima, vero):
        with self._l:
            self.prenotato -= stima
            self.speso += vero


def _chiave_run(r):
    return (r["id"], r["piattaforma"], int(r["ripetizione"]))


def gia_fatte(percorso) -> set:
    """Le risposte raccolte con successo. Gli errori NON contano: al rilancio
    si ritentano, altrimenti resterebbe un buco silenzioso nei dati."""
    fatte = set()
    if percorso.exists():
        with open(percorso, encoding="utf-8") as f:
            for riga in f:
                try:
                    d = json.loads(riga)
                except Exception:  # noqa: BLE001
                    continue
                if not d.get("errore"):
                    fatte.add(_chiave_run(d))
    return fatte


def carica_risposte(percorso) -> list:
    """Una sola risposta valida per (domanda, piattaforma, ripetizione)."""
    migliori = {}
    if percorso.exists():
        with open(percorso, encoding="utf-8") as f:
            for riga in f:
                try:
                    d = json.loads(riga)
                except Exception:  # noqa: BLE001
                    continue
                if not d.get("errore"):
                    migliori[_chiave_run(d)] = d
    return list(migliori.values())


def costo_registrato(percorso) -> float:
    tot = 0.0
    if percorso.exists():
        with open(percorso, encoding="utf-8") as f:
            for riga in f:
                try:
                    tot += float(json.loads(riga).get("costo", 0) or 0)
                except Exception:  # noqa: BLE001
                    pass
    return tot


def raccogli(p, domande, cartella, chiavi, cassa) -> dict:
    """Esegue le chiamate mancanti. Ritorna un riepilogo."""
    file_r = cartella / "risposte.jsonl"
    fatte = gia_fatte(file_r)
    piatt = [x for x in p["piattaforme"] if chiavi.get(x)]
    lavori = [(d, x, n) for d in domande for x in piatt for n in range(1, p["ripetizioni"] + 1)
              if (d["id"], x, n) not in fatte]
    if fatte:
        print(tenue(f"  Riprendo: {len(fatte)} risposte già raccolte, ne mancano {len(lavori)}."))
    if not lavori:
        return {"ok": 0, "errori": 0, "saltate_budget": 0, "bloccate": {}}

    lock_file = threading.Lock()
    passo = {x: threading.Lock() for x in piatt}
    ultimo = {x: 0.0 for x in piatt}
    errori_fila = {x: 0 for x in piatt}
    bloccate = {}
    fermo = threading.Event()
    conti = {"ok": 0, "errori": 0, "saltate_budget": 0}
    lc = threading.Lock()

    def attendi_turno(x):
        iv = INTERVALLO.get(x, 0)
        if not iv:
            return
        with passo[x]:
            w = iv - (time.monotonic() - ultimo[x])
            if w > 0:
                time.sleep(w)
            ultimo[x] = time.monotonic()

    def lavoro(d, x, n):
        if fermo.is_set() or x in bloccate:
            return None
        stima = P.STIMA_CHIAMATA[x]
        if not cassa.prenota(stima):
            with lc:
                conti["saltate_budget"] += 1
            return None
        ultimo_err = None
        try:
            for t in range(TENTATIVI):
                if fermo.is_set() or x in bloccate:
                    break
                try:
                    attendi_turno(x)
                    r = P.CHIEDI[x](chiavi[x], d["domanda"], p["modelli"][x], p.get("paese", ""))
                    rec = {"id": d["id"], "domanda": d["domanda"], "fase": d["fase"], "tipo": d["tipo"],
                           "piattaforma": x, "ripetizione": n, "modello": r["modello"],
                           "quando": datetime.now().isoformat(timespec="seconds"),
                           "costo": round(r["costo"], 6), "testo": r["testo"], "fonti": r["fonti"]}
                    with lock_file, open(file_r, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    cassa.salda(stima, r["costo"])
                    stima = 0
                    with lc:
                        errori_fila[x] = 0
                        conti["ok"] += 1
                    return rec
                except Exception as e:  # noqa: BLE001
                    ultimo_err = e
                    if blocca_piattaforma(e):
                        bloccate.setdefault(x, errore_leggibile(e))
                        break
                    if non_riprovare(e):
                        break
                    attesa = 20 if "429" in str(e) else 3
                    time.sleep(attesa * (t + 1))
            # fallita
            with lc:
                conti["errori"] += 1
                errori_fila[x] += 1
                if errori_fila[x] >= ERRORI_CONSECUTIVI_MAX and x not in bloccate:
                    bloccate[x] = f"{ERRORI_CONSECUTIVI_MAX} errori di fila ({errore_leggibile(ultimo_err)})"
            if ultimo_err is not None:
                with lock_file, open(file_r, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"id": d["id"], "piattaforma": x, "ripetizione": n,
                                         "quando": datetime.now().isoformat(timespec="seconds"),
                                         "errore": errore_leggibile(ultimo_err)}, ensure_ascii=False) + "\n")
            return None
        finally:
            if stima:
                cassa.salda(stima, 0.0)

    tot = len(lavori)
    fatti = 0
    esecutori = {x: ThreadPoolExecutor(LAVORATORI.get(x, 2)) for x in piatt}
    futuri = [esecutori[l[1]].submit(lavoro, *l) for l in lavori]
    avvisate = set()
    try:
        for f in as_completed(futuri):
            fatti += 1
            rec = f.result()
            for x, motivo in list(bloccate.items()):
                if x not in avvisate:
                    avvisate.add(x)
                    print(rosso(f"\n  ✗ {P.NOMI[x]} fermato: {motivo}. Le altre piattaforme continuano."))
            if rec:
                segno = verde("✓")
                det = f"{P.NOMI[rec['piattaforma']]:<10} {rec['id']} #{rec['ripetizione']}"
            else:
                segno, det = tenue("·"), tenue("saltata")
            print(f"\r  [{fatti:>4}/{tot}] {segno} {det:<28} speso ${cassa.speso:5.2f}   ", end="", flush=True)
    except KeyboardInterrupt:
        fermo.set()
        print(giallo("\n\n  Interrotto. Quello che è stato raccolto è salvato: rilancia il kit per riprendere."))
        for ex in esecutori.values():
            ex.shutdown(wait=False, cancel_futures=True)
        raise
    for ex in esecutori.values():
        ex.shutdown(wait=True)
    print()
    conti["bloccate"] = dict(bloccate)
    return conti


# ───────────────────────── seconda lettura: il giudizio ───────────────────────

def giudica_tutte(p, risposte, cartella, chiavi, cassa):
    """Per ogni risposta che nomina il brand: è consigliato o solo nominato?
    Il risultato va in giudizi.jsonl, una volta sola per risposta."""
    file_g = cartella / "giudizi.jsonl"
    fatti = {}
    if file_g.exists():
        with open(file_g, encoding="utf-8") as f:
            for riga in f:
                try:
                    d = json.loads(riga)
                    fatti[(d["id"], d["piattaforma"], int(d["ripetizione"]))] = d
                except Exception:  # noqa: BLE001
                    pass
    # un giudizio "euristico" si rifà appena c'è un'AI di lettura (es. chiave aggiunta dopo)
    ai_lettura = bool(chiavi.get("chatgpt") or chiavi.get("gemini"))
    da_fare = []
    for r in risposte:
        k = _chiave_run(r)
        if k in fatti and not (ai_lettura and fatti[k].get("metodo") == "euristica"):
            continue
        sg = S.leggi(p, r["testo"], r["fonti"])
        if sg["menzione"]:
            da_fare.append((r, sg["estratto"]))
    if da_fare:
        print(tenue(f"  Leggo {len(da_fare)} risposte che ti nominano, per capire come ne parlano…"))
    lock = threading.Lock()

    def uno(r, est):
        stima = 0.003
        if not cassa.prenota(stima):
            g, costo = S.giudizio_euristico(p, est), 0.0
        else:
            g, costo = S.giudica(p, r["domanda"], est, chiavi)
            cassa.salda(stima, costo)
        rec = {"id": r["id"], "piattaforma": r["piattaforma"], "ripetizione": r["ripetizione"],
               "costo": round(costo, 6), **g}
        with lock, open(file_g, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    if chiavi.get("chatgpt"):
        with ThreadPoolExecutor(4) as ex:
            for rec in ex.map(lambda a: uno(*a), da_fare):
                fatti[_chiave_run(rec)] = rec
    else:
        # solo Gemini (o nessuna AI di servizio): in fila, per non sfondare il
        # limite al minuto del piano gratuito
        for i, a in enumerate(da_fare):
            if i and chiavi.get("gemini"):
                time.sleep(INTERVALLO["gemini"])
            rec = uno(*a)
            fatti[_chiave_run(rec)] = rec
    return fatti
