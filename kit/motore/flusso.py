"""Il percorso completo: intervista → domande → misura → dashboard.

Si usa in due modi:
- interattivo: `python3 avvia.py` fa tutte le domande nel terminale;
- senza domande (per chi lavora con Claude Code o per automatizzare):
    python3 avvia.py --crea risposte.json     crea il progetto e le domande
    python3 avvia.py --misura <sito> --si     lancia la misura senza conferme
    python3 avvia.py --dashboard <sito>       rifà la dashboard, zero spesa
"""
import getpass
import json
import math
import re
import sys
import webbrowser
from datetime import date
from pathlib import Path

from . import analisi as AN
from . import dashboard as DB
from . import domande as DOM
from . import misura as MI
from . import piattaforme as P
from .util import (KIT, FILE_CHIAVI, chiave, chiedi, conferma, dominio, get_ok, giallo,
                   grassetto, maschera, rosso, salva_chiave, scegli, sembra_dominio, tenue,
                   titolo, verde, blu)

PROGETTI = KIT / "progetti"

MERCATI = [
    ("Italia (domande in italiano)", "it", "IT"),
    ("Svizzera italiana (italiano)", "it", "CH"),
    ("Spagna (spagnolo)", "es", "ES"),
    ("Francia (francese)", "fr", "FR"),
    ("Germania (tedesco)", "de", "DE"),
    ("Regno Unito (inglese)", "en", "GB"),
    ("Stati Uniti (inglese)", "en", "US"),
]

DIMENSIONI = [("Rapida", 15), ("Completa", 30)]
RIPETIZIONI = 3


# ───────────────────────── progetto su disco ─────────────────────────────────

def cartella_progetto(dom: str) -> Path:
    return PROGETTI / dom.replace(".", "-")


def carica_progetto(nome: str) -> dict:
    c = PROGETTI / nome
    if not (c / "progetto.json").exists():
        c = cartella_progetto(nome)
    f = c / "progetto.json"
    if not f.exists():
        sys.exit(rosso(f"Progetto non trovato: {nome}"))
    p = json.loads(f.read_text(encoding="utf-8"))
    p["_cartella"] = str(c)
    p.setdefault("modelli", {})
    for x, m in P.MODELLI_DEFAULT.items():
        p["modelli"].setdefault(x, m)
    return p


def salva_progetto(p: dict):
    c = Path(p["_cartella"])
    c.mkdir(parents=True, exist_ok=True)
    dati = {k: v for k, v in p.items() if not k.startswith("_")}
    (c / "progetto.json").write_text(json.dumps(dati, ensure_ascii=False, indent=2), encoding="utf-8")


def progetti_esistenti():
    if not PROGETTI.exists():
        return []
    return sorted(d.name for d in PROGETTI.iterdir() if (d / "progetto.json").exists())


def normalizza(r: dict) -> dict:
    """Da risposte grezze (intervista o file JSON) a progetto valido."""
    sito = r.get("sito", "").strip()
    dom = dominio(sito)
    if not dom or "." not in dom:
        raise ValueError(f"indirizzo del sito non valido: {sito!r}")
    brand = (r.get("brand") or "").strip() or dom.split(".")[0].replace("-", " ").title()
    conc, visti = [], set()
    for c in r.get("concorrenti", []):
        if isinstance(c, dict):
            nome, d = c.get("nome", "").strip(), dominio(c.get("dominio", ""))
        else:
            c = str(c).strip()
            if not c:
                continue
            m = re.fullmatch(r"(.+?)\s*[\(\[]\s*([^\)\]]+?)\s*[\)\]]", c)   # "Nome (sito.it)"
            if m and sembra_dominio(m.group(2)):
                nome, d = m.group(1).strip(), dominio(m.group(2))
            elif sembra_dominio(c):
                d = dominio(c)
                nome = d.split(".")[0].replace("-", " ").title() if len(d.split(".")[0]) > 2 else d
            else:
                nome, d = c, ""
        chiave_c = (d or nome.lower())
        if not nome or (d and d == dom) or chiave_c in visti or nome.lower() in visti:
            continue
        visti.update({chiave_c, nome.lower()})
        conc.append({"nome": nome, "dominio": d})
    mercato = r.get("mercato") or {}
    return {
        "versione": 1, "creato": date.today().isoformat(),
        "sito": sito if "://" in sito else "https://" + sito, "dominio": dom, "brand": brand,
        "alias": [a.strip() for a in r.get("alias", []) if a.strip()],
        "offerta": r["offerta"].strip(), "pubblico": (r.get("pubblico") or "").strip(),
        "zona": (r.get("zona") or "").strip(),
        "lingua": mercato.get("lingua", r.get("lingua", "it")), "paese": mercato.get("paese", r.get("paese", "IT")),
        "concorrenti": conc[:5],
        "domande_clienti": [q.strip() for q in r.get("domande_clienti", []) if q.strip()][:3],
        "piattaforme": [x for x in r.get("piattaforme", P.ORDINE) if x in P.ORDINE],
        "n_domande": int(r.get("n_domande", 15)), "ripetizioni": int(r.get("ripetizioni", RIPETIZIONI)),
        "tetto_spesa": float(r.get("tetto_spesa", 5)),
        "modelli": dict(P.MODELLI_DEFAULT),
        "_cartella": str(cartella_progetto(dom)),
    }


# ───────────────────────── chiavi ────────────────────────────────────────────

LINK_CHIAVI = {
    "chatgpt": "platform.openai.com/api-keys",
    "gemini": "aistudio.google.com/apikey",
    "perplexity": "perplexity.ai/account/api/keys",
}


def verifica_chiave(x, k):
    """Controllo gratuito dove possibile. Perplexity non ha un endpoint gratuito:
    la chiave si verifica alla prima domanda."""
    if x == "chatgpt":
        return get_ok("https://api.openai.com/v1/models", {"Authorization": f"Bearer {k}"})
    if x == "gemini":
        return get_ok("https://generativelanguage.googleapis.com/v1beta/models", {"x-goog-api-key": k})
    return True, ""


def chiavi_disponibili(piatt):
    return {x: chiave(x) for x in piatt if chiave(x)}


def passo_chiavi():
    titolo("Passo 4 di 4", "Piattaforme")
    print("  Per ogni assistente serve una chiave API, che si crea sul sito del servizio. Puoi usarne")
    print("  anche solo una o due: il kit misura le piattaforme che attivi.")
    print(tenue("  Mentre incolli una chiave non vedrai i caratteri: è normale.\n"))
    scelte, nuove = [], {}
    for x in P.ORDINE:
        k = chiave(x)
        if k:
            print(f"  {verde('✓')} {P.NOMI[x]}: chiave trovata ({maschera(k)})")
            if conferma(f"Uso {P.NOMI[x]}?"):
                scelte.append(x)
            continue
        print(f"  {P.NOMI[x]}: chiave da {tenue(LINK_CHIAVI[x])}")
        try:
            k = getpass.getpass(f"  Incolla la chiave {P.NOMI[x]} (Invio per saltare): ").strip()
        except Exception:  # noqa: BLE001
            k = input(f"  Incolla la chiave {P.NOMI[x]} (Invio per saltare): ").strip()
        if not k:
            continue
        ok, msg = verifica_chiave(x, k)
        if not ok:
            print(rosso(f"  ✗ La chiave non funziona: {msg}. {P.NOMI[x]} resta fuori."))
            continue
        print(verde(f"  ✓ {P.NOMI[x]} pronto"))
        nuove[x] = k
        scelte.append(x)
    if nuove:
        print()
        if conferma(f"Salvo le chiavi nel file {FILE_CHIAVI.name} di questa cartella, per la prossima volta?"):
            for x, k in nuove.items():
                salva_chiave(x, k)
            print(tenue(f"  Salvate in {FILE_CHIAVI}. Non condividere quel file."))
        else:
            import os
            for x, k in nuove.items():
                os.environ[{"chatgpt": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY",
                            "perplexity": "PERPLEXITY_API_KEY"}[x]] = k
    return scelte


# ───────────────────────── intervista ────────────────────────────────────────

def intervista() -> dict:
    print(grassetto("\n  Quattro passi, un paio di minuti. Le risposte tra [parentesi] sono già pronte: premi Invio per tenerle."))

    titolo("Passo 1 di 4", "Il tuo sito")
    while True:
        sito = chiedi("Indirizzo del sito (es. www.esempio.it)", obbligatoria=True)
        if "." in dominio(sito):
            break
        print(giallo("  Non sembra un indirizzo web. Riprova, per esempio: www.esempio.it"))
    dom = dominio(sito)
    brand = chiedi("Nome del brand, come lo scrivono i clienti", dom.split(".")[0].replace("-", " ").title())
    alias = chiedi("Altri modi in cui ti chiamano, separati da virgola (Invio per saltare)")

    titolo("Passo 2 di 4", "Cosa offri e a chi")
    print(tenue("  Scrivilo come lo direbbe un cliente, non come uno slogan."))
    print(tenue("  Esempi: 'corsi di yoga online' · 'software per la gestione delle palestre' · 'agriturismo con piscina'"))
    offerta = chiedi("Cosa offri, in poche parole", obbligatoria=True)
    pubblico = chiedi("A chi ti rivolgi (es. famiglie, piccole aziende; Invio per saltare)")
    zona = chiedi("Dove lavori: una città, una regione, o 'online'", "online")
    print("  In quale mercato e lingua faccio le domande?")
    i = scegli("Scegli un numero", [m[0] for m in MERCATI] + ["Altro"], 1)
    if i <= len(MERCATI):
        lingua, paese = MERCATI[i - 1][1], MERCATI[i - 1][2]
    else:
        lingua = chiedi("Codice lingua di due lettere (es. pt, nl)", "en").lower()[:2]
        paese = chiedi("Codice paese di due lettere (es. PT, NL)", "").upper()[:2]

    titolo("Passo 3 di 4", "Concorrenti e domande vere")
    conc = chiedi("Fino a 5 concorrenti, nome o sito, separati da virgola (Invio per saltare)")
    print(tenue("  Una domanda che i tuoi clienti fanno davvero rende la misura più realistica. Fino a 3."))
    dc = []
    for n in range(3):
        q = chiedi(f"Domanda {n + 1} (Invio per {'saltare' if n == 0 else 'finire'})")
        if not q:
            break
        dc.append(q)

    piatt = passo_chiavi()
    if not piatt:
        sys.exit(rosso("\n  Serve almeno una piattaforma con una chiave valida. Rilancia il kit quando ne hai una."))

    print("\n  Quanto grande vuoi la misura?")
    opz = []
    for nome, n in DIMENSIONI:
        st = stima(n, RIPETIZIONI, piatt)
        opz.append(f"{nome}: {n} domande × {RIPETIZIONI} ripetizioni · circa ${st:.2f}")
    d = scegli("Scegli un numero", opz, 1)
    n_dom = DIMENSIONI[d - 1][1]
    st = stima(n_dom, RIPETIZIONI, piatt)
    tetto_def = max(1, math.ceil(st * 1.5 + 0.5))
    tetto = chiedi("Spesa massima in dollari: il kit si ferma prima di superarla", str(tetto_def))
    try:
        tetto = float(tetto.replace(",", ".").replace("$", ""))
    except ValueError:
        tetto = float(tetto_def)

    return normalizza({
        "sito": sito, "brand": brand, "alias": alias.split(",") if alias else [],
        "offerta": offerta, "pubblico": pubblico, "zona": zona,
        "mercato": {"lingua": lingua, "paese": paese},
        "concorrenti": [c for c in conc.split(",")] if conc else [],
        "domande_clienti": dc, "piattaforme": piatt, "n_domande": n_dom,
        "ripetizioni": RIPETIZIONI, "tetto_spesa": tetto,
    })


def stima(n_dom, rip, piatt):
    # +10% per la lettura delle risposte che ti nominano e la preparazione delle domande
    return n_dom * rip * sum(P.STIMA_CHIAMATA[x] for x in piatt) * 1.1 + 0.02


# ───────────────────────── domande ───────────────────────────────────────────

def prepara_domande(p, interattivo=True):
    chiavi = chiavi_disponibili(P.ORDINE)
    spesa = {"totale": 0.0}
    print(tenue("\n  Preparo le domande con il metodo di Aleyda Solis…"))
    dom, fonte = DOM.genera(p, p["n_domande"], chiavi, spesa)
    p["spesa_preparazione"] = round(p.get("spesa_preparazione", 0) + spesa["totale"], 4)
    f = Path(p["_cartella"]) / "domande.csv"
    DOM.salva(dom, f)
    salva_progetto(p)
    print(tenue(f"  Scritte da: {fonte}."))
    if interattivo:
        dom = rivedi(p, dom, f, chiavi)
    return dom


def mostra(dom):
    fase = None
    for d in dom:
        if d["fase"] != fase:
            fase = d["fase"]
            print("\n  " + grassetto(DOM.FASI[fase]) + tenue(f" — {DOM.SPIEGAZIONE_FASI[fase]}"))
        print(f"   {tenue(d['id'])} {d['domanda']}")


def rivedi(p, dom, f, chiavi):
    while True:
        mostra(dom)
        print(f"\n  Le domande sono nel file {tenue(str(f))}")
        r = scegli("Come procedo?", ["Vanno bene, avanti",
                                     "Rigenerale da capo",
                                     "Le modifico io nel file (aprilo, salva, poi torna qui)"], 1)
        if r == 1:
            return dom
        if r == 2:
            spesa = {"totale": 0.0}
            dom, _ = DOM.genera(p, p["n_domande"], chiavi, spesa)
            p["spesa_preparazione"] = round(p.get("spesa_preparazione", 0) + spesa["totale"], 4)
            DOM.salva(dom, f)
            salva_progetto(p)
        else:
            input(tenue("  Premi Invio quando hai salvato il file… "))
            try:
                dom = DOM.carica(f, p)
            except Exception as e:  # noqa: BLE001
                print(rosso(f"  Il file non si legge ({e}). Torno alla versione precedente."))
                DOM.salva(dom, f)
            if not dom:
                print(rosso("  Il file è vuoto. Rigenero."))
                dom, _ = DOM.genera(p, p["n_domande"], chiavi, {"totale": 0.0})
                DOM.salva(dom, f)


# ───────────────────────── misura ────────────────────────────────────────────

def cartelle_misure(p):
    m = Path(p["_cartella"]) / "misure"
    if not m.exists():
        return []
    return sorted(d for d in m.iterdir() if d.is_dir() and (d / "risposte.jsonl").exists())


def misura_completa(p, domande, cartella, chiavi):
    fatte = MI.gia_fatte(cartella / "risposte.jsonl")
    piatt = [x for x in p["piattaforme"] if chiavi.get(x)]
    attese = {(d["id"], x, n) for d in domande for x in piatt for n in range(1, p["ripetizioni"] + 1)}
    return attese <= fatte


def scegli_cartella_misura(p, domande, chiavi, nuova):
    esistenti = cartelle_misure(p)
    if esistenti and not nuova:
        # interrotta: si riprende · completa: non si ripaga nulla, si rifà solo la dashboard
        return esistenti[-1]
    base = Path(p["_cartella"]) / "misure" / date.today().isoformat()
    c, i = base, 2
    while c.exists():
        c = base.with_name(f"{base.name}-{i}")
        i += 1
    c.mkdir(parents=True)
    return c


def esegui_misura(p, domande, interattivo=True, nuova=False):
    chiavi = chiavi_disponibili(p["piattaforme"])
    mancanti = [P.NOMI[x] for x in p["piattaforme"] if x not in chiavi]
    if mancanti:
        print(giallo(f"  Nessuna chiave per {', '.join(mancanti)}: queste piattaforme restano fuori."))
    if not chiavi:
        sys.exit(rosso("  Nessuna chiave disponibile: inseriscila in chiavi-api.txt o rilancia l'intervista."))
    cartella = scegli_cartella_misura(p, domande, chiavi, nuova)
    gia = MI.costo_registrato(cartella / "risposte.jsonl") + MI.costo_registrato(cartella / "giudizi.jsonl")
    n_chiamate = len(domande) * len(chiavi) * p["ripetizioni"]
    fatte = MI.gia_fatte(cartella / "risposte.jsonl")
    mancanti_n = sum(1 for d in domande for x in chiavi for n in range(1, p["ripetizioni"] + 1)
                     if (d["id"], x, n) not in fatte)
    st = stima(len(domande), p["ripetizioni"], list(chiavi)) * mancanti_n / max(1, n_chiamate)

    titolo("Misura", f"{len(domande)} domande × {p['ripetizioni']} ripetizioni × {len(chiavi)} piattaforme")
    if not mancanti_n:
        print(verde(f"  Questa misura ({cartella.name}) è già completa: nessuna spesa, rifaccio solo la dashboard."))
        MI.giudica_tutte(p, MI.carica_risposte(cartella / "risposte.jsonl"), cartella, chiavi,
                         MI.Cassa(p["tetto_spesa"], gia))
        return cartella
    print(f"  {mancanti_n} risposte da raccogliere · costo stimato ${st:.2f} · tetto ${p['tetto_spesa']:.2f}")
    if gia:
        print(tenue(f"  Già speso in questa misura: ${gia:.2f}"))
    if "gemini" in chiavi:
        print(tenue("  Gemini va più piano (circa 9 risposte al minuto) per restare nei limiti del piano gratuito."))
    if interattivo and not conferma("Parto?"):
        sys.exit(tenue("  Va bene, nessuna spesa. Rilancia il kit quando vuoi."))

    cassa = MI.Cassa(p["tetto_spesa"], gia)
    print(tenue("  Puoi interrompere con Ctrl+C: rilanciando, il kit riprende da qui.\n"))
    conti = MI.raccogli(p, domande, cartella, chiavi, cassa)
    risposte = MI.carica_risposte(cartella / "risposte.jsonl")
    MI.giudica_tutte(p, risposte, cartella, chiavi, cassa)

    print()
    if conti["saltate_budget"]:
        print(giallo(f"  {conti['saltate_budget']} risposte non raccolte per non superare il tetto di spesa. "
                     "Alza 'tetto_spesa' in progetto.json e rilancia per completarle."))
    if conti["errori"]:
        print(giallo(f"  {conti['errori']} risposte non riuscite: rilanciando il kit vengono ritentate."))
    print(verde(f"  ✓ Misura salvata. Spesa di questa misura: circa ${cassa.speso:.2f}"))
    return cartella


def fai_dashboard(p, domande, cartella, apri=True):
    prec = [c for c in cartelle_misure(p) if c.name < cartella.name]
    A = AN.analizza(p, domande, cartella, prec[-1] if prec else None)
    out = cartella / "dashboard.html"
    DB.genera(A, p, out, cartella.name[:10])
    copia = Path(p["_cartella"]) / "dashboard.html"
    copia.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    print(verde(f"  ✓ Dashboard: {copia}"))
    if apri:
        try:
            webbrowser.open(copia.resolve().as_uri())
        except Exception:  # noqa: BLE001
            pass
    return A


# ───────────────────────── avvio ─────────────────────────────────────────────

def benvenuto():
    print(grassetto(blu("\n  Visibilità AI")) + " — come ChatGPT, Gemini e Perplexity parlano del tuo sito")
    print(tenue("  Metodo: AI Search Prompt Library di Aleyda Solis\n"))


def interattivo():
    benvenuto()
    esistenti = progetti_esistenti()
    if esistenti:
        voci = [f"Continua con {n.replace('-', '.')}" for n in esistenti] + ["Analizza un nuovo sito"]
        i = scegli("Cosa vuoi fare?", voci, 1)
        if i <= len(esistenti):
            return progetto_esistente(carica_progetto(esistenti[i - 1]))
    p = intervista()
    if (Path(p["_cartella"]) / "progetto.json").exists():
        if not conferma(giallo(f"Esiste già un progetto per {p['dominio']}: lo sostituisco?"), False):
            return progetto_esistente(carica_progetto(p["dominio"]))
    salva_progetto(p)
    domande = prepara_domande(p)
    cartella = esegui_misura(p, domande)
    fai_dashboard(p, domande, cartella)


def progetto_esistente(p):
    f = Path(p["_cartella"]) / "domande.csv"
    if not f.exists():
        domande = prepara_domande(p)
    else:
        domande = DOM.carica(f, p)
    chiavi = chiavi_disponibili(p["piattaforme"])
    misure = cartelle_misure(p)
    interrotta = misure and not misura_completa(p, domande, misure[-1], chiavi)
    voci = []
    if interrotta:
        voci.append(("riprendi", f"Riprendi la misura interrotta del {misure[-1].name}"))
    voci.append(("nuova", "Nuova misura con le stesse domande (per vedere cosa è cambiato)"))
    if misure:
        voci.append(("dash", "Rifai solo la dashboard dell'ultima misura (gratis)"))
    voci.append(("domande", "Rivedi le domande (attenzione: cambiarle rende meno confrontabili le misure)"))
    i = scegli("Cosa vuoi fare?", [v[1] for v in voci], 1)
    scelta = voci[i - 1][0]
    if scelta == "dash":
        fai_dashboard(p, domande, misure[-1])
        return
    if scelta == "domande":
        domande = rivedi(p, domande, f, chiavi_disponibili(P.ORDINE))
    cartella = esegui_misura(p, domande, nuova=(scelta != "riprendi"))
    fai_dashboard(p, domande, cartella)


def da_riga_di_comando(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="avvia.py", description="Visibilità AI: misura come gli assistenti AI parlano di un sito.")
    ap.add_argument("--crea", metavar="RISPOSTE.json", help="crea il progetto da un file di risposte e prepara le domande")
    ap.add_argument("--misura", metavar="SITO", help="lancia (o riprende) la misura di un progetto")
    ap.add_argument("--nuova", action="store_true", help="con --misura: nuova misura anche se l'ultima è completa")
    ap.add_argument("--dashboard", metavar="SITO", help="rifà la dashboard dell'ultima misura, zero spesa")
    ap.add_argument("--si", action="store_true", help="non chiedere conferme")
    ap.add_argument("--non-aprire", action="store_true", help="non aprire il browser alla fine")
    a = ap.parse_args(argv)
    if a.crea:
        r = json.loads(Path(a.crea).read_text(encoding="utf-8"))
        p = normalizza(r)
        salva_progetto(p)
        dom = prepara_domande(p, interattivo=False)
        mostra(dom)
        print(f"\n  Progetto creato in {p['_cartella']}. Rivedi domande.csv, poi: python3 avvia.py --misura {p['dominio']}")
        return
    if a.misura:
        p = carica_progetto(a.misura)
        domande = DOM.carica(Path(p["_cartella"]) / "domande.csv", p)
        cartella = esegui_misura(p, domande, interattivo=not a.si, nuova=a.nuova)
        fai_dashboard(p, domande, cartella, apri=not a.non_aprire)
        return
    if a.dashboard:
        p = carica_progetto(a.dashboard)
        domande = DOM.carica(Path(p["_cartella"]) / "domande.csv", p)
        m = cartelle_misure(p)
        if not m:
            sys.exit(rosso("  Nessuna misura per questo progetto."))
        fai_dashboard(p, domande, m[-1], apri=not a.non_aprire)
        return
    interattivo()
