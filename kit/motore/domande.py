"""Il set di domande da porre agli assistenti AI.

Segue il metodo di Aleyda Solis (AI Search Prompt Library):
- si parte da chi è il cliente e cosa cerca, non da un elenco di parole chiave;
- le domande coprono tutte le fasi del percorso del cliente;
- sono scritte come le scriverebbe una persona vera, con vincoli realistici
  (budget, luogo, periodo, profilo, urgenza);
- le domande GENERICHE (che non nominano il brand) sono separate da quelle che
  lo nominano: le prime misurano se l'AI ti propone spontaneamente, le seconde
  cosa dice di te quando qualcuno ti cerca per nome. Mescolarle gonfia i numeri.
"""
import csv
import re

from . import piattaforme as P
from .util import regex_nome

FASI = {
    "scoperta": "Scoperta",
    "scelta": "Scelta",
    "confronto": "Confronto",
    "acquisto": "Acquisto",
    "brand": "Sul tuo nome",
}
SPIEGAZIONE_FASI = {
    "scoperta": "la persona ha un bisogno e vuole capire come muoversi",
    "scelta": "cerca le opzioni migliori per il suo caso",
    "confronto": "mette a confronto opzioni o cerca alternative",
    "acquisto": "è pronta a comprare, prenotare o contattare",
    "brand": "ti cerca per nome: cosa si sente rispondere",
}

COLONNE = ["id", "domanda", "fase", "tipo", "vincolo"]


def ripartizione(n: int) -> dict:
    """Quante domande per fase. Le domande sul brand sono una minoranza di proposito."""
    brand = max(2, round(n * 0.15))
    resto = n - brand
    conf = max(1, round(resto * 0.17))
    acq = max(1, round(resto * 0.2))
    scop = max(1, round(resto * 0.28))
    scelta = resto - conf - acq - scop
    return {"scoperta": scop, "scelta": scelta, "confronto": conf, "acquisto": acq, "brand": brand}


def _istruzioni(p: dict, n: int) -> str:
    rip = ripartizione(n)
    conc = ", ".join(c["nome"] for c in p.get("concorrenti", [])) or "(nessuno indicato)"
    clienti = "\n".join(f"- {d}" for d in p.get("domande_clienti", [])) or "(nessuna)"
    return f"""Sei un esperto di GEO (Generative Engine Optimization) e segui il metodo della
"AI Search Prompt Library" di Aleyda Solis. Devi costruire il set di domande con cui
misurare quanto un brand è visibile nelle risposte di ChatGPT, Gemini e Perplexity.

IL BRAND
- Nome: {p['brand']}
- Sito: {p['dominio']}
- Cosa offre: {p['offerta']}
- A chi si rivolge: {p.get('pubblico') or 'non specificato'}
- Dove opera: {p.get('zona') or 'non specificato'}
- Concorrenti noti: {conc}

DOMANDE CHE I CLIENTI FANNO DAVVERO (includile così come sono, assegnando la fase giusta):
{clienti}

COSA DEVI PRODURRE
{n} domande in lingua "{p['lingua']}", scritte come le scriverebbe una persona vera in chat
con un assistente AI, ripartite così:
- scoperta: {rip['scoperta']} — ha un bisogno, non conosce ancora le opzioni
- scelta: {rip['scelta']} — cerca le opzioni migliori per il suo caso specifico
- confronto: {rip['confronto']} — confronta opzioni o cerca alternative (puoi nominare i concorrenti, MAI il brand)
- acquisto: {rip['acquisto']} — vuole comprare, prenotare, contattare: dove, come, quanto costa
- brand: {rip['brand']} — nominano esplicitamente "{p['brand']}" (opinioni, affidabilità, prezzi, alternative, confronto con un concorrente)

REGOLE
1. Nelle fasi scoperta, scelta, confronto e acquisto il nome "{p['brand']}" e il sito NON devono comparire: misurano se l'AI ti propone spontaneamente.
2. Ogni domanda di scelta e acquisto contiene UN vincolo realistico (budget, luogo, periodo, tipo di persona, caso d'uso, urgenza, una caratteristica precisa). Varia i vincoli.
3. Linguaggio naturale e colloquiale, a volte con un po' di contesto personale ("ho due bambini...", "ho un budget di..."). Niente gergo da marketer, niente parole chiave messe in fila.
4. Domande diverse fra loro: niente parafrasi della stessa domanda.
5. Se il brand opera in un luogo preciso, usa quel luogo e i luoghi vicini nel modo in cui ne parlano i clienti.
6. Lunghezza: da 6 a 35 parole.

Rispondi SOLO con questo JSON:
{{"domande": [{{"domanda": "...", "fase": "scoperta|scelta|confronto|acquisto|brand", "vincolo": "breve etichetta del vincolo o vuoto"}}]}}"""


# ───────────────────────── modelli di riserva ────────────────────────────────
# Usati solo se nessuna AI di servizio risponde. Più rigidi delle domande
# generate, ma permettono comunque di fare la misura.

MODELLI = {
    "it": {
        "scoperta": ["Ho bisogno di {o}{z}: da dove parto e cosa devo sapere prima di scegliere?",
                     "Quali errori evitare quando si sceglie {o}{z}?",
                     "Come capisco se {o}{z} è adatto a {pb}?"],
        "scelta": ["Quali sono le migliori opzioni per {o}{z}?",
                   "Mi consigli {o}{z} con un buon rapporto qualità prezzo?",
                   "Cerco {o}{z} per {pb}: cosa mi suggerisci?",
                   "Quali sono le opzioni più affidabili per {o}{z}, secondo le recensioni?",
                   "Ho un budget limitato: quale scelta conviene per {o}{z}?",
                   "Mi serve {o}{z} entro pochi giorni: a chi mi rivolgo?"],
        "confronto": ["Confronta le principali opzioni per {o}{z}: pro e contro di ciascuna.",
                      "Quali alternative ci sono a {c1} per {o}?",
                      "{c1} o {c2}: cosa conviene per {o}?"],
        "acquisto": ["Dove posso acquistare o prenotare {o}{z}?",
                     "Qual è il sito migliore per {o}{z}?",
                     "Quanto costa in media {o}{z} e dove conviene prenderlo?"],
        "brand": ["Cos'è {b} e com'è secondo chi lo ha provato?",
                  "{b} è affidabile? Cosa dicono le recensioni?",
                  "Quali sono le alternative a {b}?",
                  "{b} o {c1}: quale scegliere?",
                  "Quanto costa {b}?"],
    },
    "en": {
        "scoperta": ["I need {o}{z}: where do I start and what should I know before choosing?",
                     "What mistakes should I avoid when choosing {o}{z}?",
                     "How do I know if {o}{z} is right for {pb}?"],
        "scelta": ["What are the best options for {o}{z}?",
                   "Can you recommend {o}{z} with good value for money?",
                   "I'm looking for {o}{z} for {pb}: what do you suggest?",
                   "Which are the most reliable options for {o}{z}, based on reviews?",
                   "I'm on a tight budget: what's the best choice for {o}{z}?",
                   "I need {o}{z} within a few days: who should I contact?"],
        "confronto": ["Compare the main options for {o}{z}: pros and cons of each.",
                      "What are the alternatives to {c1} for {o}?",
                      "{c1} or {c2}: which is better for {o}?"],
        "acquisto": ["Where can I buy or book {o}{z}?",
                     "What's the best website for {o}{z}?",
                     "How much does {o}{z} usually cost and where is it cheapest?"],
        "brand": ["What is {b} and what do people think of it?",
                  "Is {b} reliable? What do reviews say?",
                  "What are the alternatives to {b}?",
                  "{b} or {c1}: which should I choose?",
                  "How much does {b} cost?"],
    },
}


def da_modelli(p: dict, n: int) -> list:
    lingua = p["lingua"] if p["lingua"] in MODELLI else "en"
    m = MODELLI[lingua]
    conc = [c["nome"] for c in p.get("concorrenti", [])]
    zona = p.get("zona") or ""
    z = ""
    if zona and zona.lower() not in ("online", "italia", "italy", "ovunque", "everywhere"):
        z = (" a " if lingua == "it" else " in ") + zona
    pb = p.get("pubblico") or ("le mie esigenze" if lingua == "it" else "my needs")
    rip = ripartizione(n)
    out = []
    for fase, k in rip.items():
        cand = []
        for t in m[fase]:
            if ("{c1}" in t and not conc) or ("{c2}" in t and len(conc) < 2):
                continue
            cand.append(t.format(o=p["offerta"], z=z, pb=pb, b=p["brand"],
                                 c1=conc[0] if conc else "", c2=conc[1] if len(conc) > 1 else ""))
        out += [{"domanda": c, "fase": fase, "vincolo": ""} for c in cand[:k]]
    return out


# ───────────────────────── generazione ───────────────────────────────────────

def pulisci(p: dict, grezze: list, n: int) -> list:
    """Normalizza, toglie i doppioni e RICLASSIFICA: una domanda che nomina il
    brand è sempre 'brand', qualunque fase abbia scritto l'AI. È la regola che
    tiene puliti i numeri della visibilità spontanea."""
    rx = [r for r in [regex_nome(p["brand"])] + [regex_nome(a) for a in p.get("alias", [])] if r]
    dom = p["dominio"].lower()
    visti, out = set(), []
    for g in grezze:
        t = re.sub(r"\s+", " ", str(g.get("domanda", "")).strip())
        if not (8 <= len(t) <= 400):
            continue
        k = re.sub(r"\W+", "", t.lower())
        if k in visti:
            continue
        visti.add(k)
        fase = str(g.get("fase", "")).strip().lower()
        if fase not in FASI:
            fase = "scelta"
        nomina = any(r.search(t) for r in rx) or dom in t.lower()
        if nomina:
            fase = "brand"
        elif fase == "brand":
            fase = "scelta"   # l'AI l'ha chiamata brand ma il nome non c'è
        out.append({"id": str(g.get("id", "") or "").strip(), "domanda": t, "fase": fase,
                    "tipo": "brand" if nomina else "generica",
                    "vincolo": str(g.get("vincolo", "") or "").strip()[:60]})
    return out


def genera(p: dict, n: int, chiavi: dict, spesa: dict) -> tuple:
    """Ritorna (domande, fonte) dove fonte dice chi le ha scritte."""
    for piatt in P.PREFERENZA_SERVIZIO:
        k = chiavi.get(piatt)
        if not k:
            continue
        try:
            dati, costo = P.JSON_SERVIZIO[piatt](k, _istruzioni(p, n))
            spesa["totale"] = spesa.get("totale", 0) + costo
            dom = pulisci(p, dati.get("domande", []), n)
            if len(dom) >= n * 0.6:
                dom = _completa(p, dom, n)
                return dom, P.NOMI[piatt]
        except Exception:  # noqa: BLE001
            continue
    return _completa(p, [], n), "modelli predefiniti"


def _completa(p, dom, n):
    """Garantisce le domande dei clienti e porta il set al numero giusto."""
    testi = {d["domanda"].lower() for d in dom}
    mancanti = [{"domanda": q, "fase": "scelta", "vincolo": "domanda reale"}
                for q in p.get("domande_clienti", []) if q.lower() not in testi]
    dom = pulisci(p, mancanti, n) + dom
    if len(dom) < n:
        dom += [d for d in pulisci(p, da_modelli(p, n), n)
                if d["domanda"].lower() not in {x["domanda"].lower() for x in dom}]
    # almeno 2 domande sul brand: senza, il blocco "Cosa dicono di te" resterebbe vuoto
    if sum(d["tipo"] == "brand" for d in dom) < 2:
        presenti = {x["domanda"].lower() for x in dom}
        dom += [d for d in pulisci(p, [m for m in da_modelli(p, max(n, 14)) if m["fase"] == "brand"], n)
                if d["domanda"].lower() not in presenti]
    brand = [d for d in dom if d["tipo"] == "brand"]
    gen = [d for d in dom if d["tipo"] != "brand"]
    nb = min(len(brand), max(2, round(n * 0.15)))
    dom = gen[: n - nb] + brand[:nb]
    ordine = list(FASI)
    dom.sort(key=lambda d: ordine.index(d["fase"]))
    for i, d in enumerate(dom, 1):
        d["id"] = f"D{i:02d}"
    return dom


def salva(dom: list, percorso):
    with open(percorso, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLONNE, extrasaction="ignore")
        w.writeheader()
        w.writerows(dom)


def carica(percorso, p: dict) -> list:
    """Rilegge il file (anche modificato a mano) e lo ricontrolla."""
    with open(percorso, newline="", encoding="utf-8-sig") as f:
        righe = list(csv.DictReader(f))
    dom = pulisci(p, righe, len(righe))
    usati = set()
    for i, d in enumerate(dom, 1):
        if not d["id"] or d["id"] in usati:
            d["id"] = f"D{i:02d}"
            while d["id"] in usati:
                d["id"] += "b"
        usati.add(d["id"])
    return dom
