"""Dalle risposte grezze ai numeri della dashboard.

Regole che tengono i numeri onesti:
- le piattaforme non si sommano mai fra loro: ognuna ha il suo numero;
- la visibilità "spontanea" si misura SOLO sulle domande che non nominano il
  brand; le domande col nome servono a capire cosa si dice di te;
- ogni percentuale porta con sé il suo denominatore e un margine di incertezza.
"""
import json
import math

from .util import stesso_dominio
from collections import Counter, defaultdict
from urllib.parse import urlparse

from . import piattaforme as P
from . import segnali as S
from .domande import FASI
from .misura import carica_risposte


def wilson(k, n, z=1.96):
    """Intervallo al 95% per una proporzione. Calcolato sul numero di DOMANDE,
    non di risposte: le ripetizioni della stessa domanda si somigliano, quindi
    contarle come indipendenti darebbe un margine falsamente stretto."""
    if n == 0:
        return (0.0, 0.0)
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def pct(k, n):
    return 100.0 * k / n if n else 0.0


def _carica_giudizi(cartella):
    g = {}
    f = cartella / "giudizi.jsonl"
    if f.exists():
        for riga in f.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(riga)
                g[(d["id"], d["piattaforma"], int(d["ripetizione"]))] = d
            except Exception:  # noqa: BLE001
                pass
    return g


def arricchisci(p, risposte, giudizi):
    """Segnali + giudizio su ogni risposta. Una menzione che l'AI di servizio
    riconosce come omonimo (parola comune, altra azienda) non conta."""
    out, falsi = [], 0
    for r in risposte:
        sg = S.leggi(p, r["testo"], r["fonti"])
        g = giudizi.get((r["id"], r["piattaforma"], int(r["ripetizione"])))
        if sg["menzione"] and g and g.get("metodo") != "euristica" and g.get("si_riferisce_al_brand") is False:
            sg["menzione"] = False
            sg["posizione"] = None
            falsi += 1
            g = None
        out.append({**r, **sg, "giudizio": g if sg["menzione"] else None})
    return out, falsi


def _percorso(url):
    try:
        u = urlparse(url)
        return (u.path or "/") + (("?" + u.query) if u.query else "")
    except Exception:  # noqa: BLE001
        return url


def analizza(p, domande, cartella, precedente=None):
    risposte = carica_risposte(cartella / "risposte.jsonl")
    ids_validi = {d["id"] for d in domande}
    risposte = [r for r in risposte if r["id"] in ids_validi]
    giudizi = _carica_giudizi(cartella)
    R, falsi = arricchisci(p, risposte, giudizi)
    piatt = [x for x in P.ORDINE if any(r["piattaforma"] == x for r in R)]
    gen = [r for r in R if r["tipo"] == "generica"]
    bra = [r for r in R if r["tipo"] == "brand"]
    dom_gen = [d for d in domande if d["tipo"] == "generica"]
    dom_bra = [d for d in domande if d["tipo"] == "brand"]
    nomi_conc = [c["nome"] for c in p.get("concorrenti", [])]

    # ── per piattaforma (solo domande generiche) ───────────────────────────
    per_p = []
    for x in piatt:
        rs = [r for r in gen if r["piattaforma"] == x]
        n = len(rs)
        km = sum(r["menzione"] for r in rs)
        kc = sum(r["citazione"] for r in rs)
        per_dom = defaultdict(list)
        for r in rs:
            per_dom[r["id"]].append(r)
        nd = len(per_dom)
        almeno = sum(any(r["menzione"] for r in v) for v in per_dom.values())
        almeno_c = sum(any(r["citazione"] for r in v) for v in per_dom.values())
        # margine sul tasso medio per domanda, con n = numero di domande
        tassi = [sum(r["menzione"] for r in v) / len(v) for v in per_dom.values()]
        tassi_c = [sum(r["citazione"] for r in v) / len(v) for v in per_dom.values()]
        m_lo, m_hi = wilson(sum(tassi), nd)
        c_lo, c_hi = wilson(sum(tassi_c), nd)
        pos = [r["posizione"] for r in rs if r["posizione"]]
        ruoli = Counter((r["giudizio"] or {}).get("ruolo") for r in rs if r["menzione"])
        per_p.append({
            "p": x, "nome": P.NOMI[x], "n": n, "domande": nd,
            "menz": pct(km, n), "menz_k": km, "menz_ci": (100 * m_lo, 100 * m_hi),
            "cit": pct(kc, n), "cit_k": kc, "cit_ci": (100 * c_lo, 100 * c_hi),
            "almeno": almeno, "almeno_c": almeno_c,
            "solo_fonte": sum(r["citazione"] and not r["menzione"] for r in rs),
            "primo": pct(sum(1 for q in pos if q == 1), len(pos)) if pos else None,
            "consigliato": ruoli.get("consigliato", 0),
            "fonti_medie": (sum(len(r["fonti"]) for r in rs) / n) if n else 0,
        })

    # ── per fase ───────────────────────────────────────────────────────────
    fasi = []
    for f in [f for f in FASI if f != "brand"]:
        riga = {"fase": f, "nome": FASI[f], "domande": sum(1 for d in dom_gen if d["fase"] == f), "valori": {}}
        if not riga["domande"]:
            continue
        for x in piatt:
            rs = [r for r in gen if r["piattaforma"] == x and r["fase"] == f]
            riga["valori"][x] = (pct(sum(r["menzione"] for r in rs), len(rs)), len(rs))
        fasi.append(riga)

    # ── tu e i concorrenti (share of voice per piattaforma) ───────────────
    sov = {}
    for x in piatt:
        rs = [r for r in gen if r["piattaforma"] == x]
        voci = [(p["brand"], pct(sum(r["menzione"] for r in rs), len(rs)), True)]
        for c in nomi_conc:
            voci.append((c, pct(sum(c in r["conc_menzionati"] for r in rs), len(rs)), False))
        voci.sort(key=lambda v: -v[1])
        sov[x] = voci

    # ── fonti più citate (domande generiche) ──────────────────────────────
    cont_f = Counter()
    per_pf = defaultdict(Counter)
    for r in gen:
        for d in set(r["domini_fonti"]):
            cont_f[d] += 1
            per_pf[d][r["piattaforma"]] += 1
    n_gen = len(gen)
    from .util import radice
    conc_dom = {c["dominio"]: c["nome"] for c in p.get("concorrenti", []) if c.get("dominio")}

    def etichetta(d):
        if stesso_dominio(d, p["dominio"]):
            return "tu"
        for cd, cn in conc_dom.items():
            if stesso_dominio(d, cd) or radice(d) == radice(cd):
                return "concorrente"
        return ""

    fonti = [{"dominio": d, "k": k, "pct": pct(k, n_gen), "tipo": etichetta(d),
              "per_p": {x: per_pf[d][x] for x in piatt}} for d, k in cont_f.most_common(15)]
    nostra = next((f for f in fonti if f["tipo"] == "tu"), None)
    if not nostra:
        k = sum(1 for r in gen if r["citazione"])
        posto = 1 + sum(1 for d, kk in cont_f.items() if kk > k and not stesso_dominio(d, p["dominio"]))
        nostra = {"dominio": p["dominio"], "k": k, "pct": pct(k, n_gen), "posto": posto if k else None}
    else:
        nostra = {**nostra, "posto": fonti.index(nostra) + 1}

    # ── pagine del sito linkate (tutte le domande) ────────────────────────
    pag = defaultdict(Counter)
    senza_url = Counter()
    for r in R:
        for u in r["pagine"]:
            pag[u][r["piattaforma"]] += 1
        if r["citazione"] and not r["pagine"]:
            senza_url[r["piattaforma"]] += 1
    pagine = sorted(({"url": u, "percorso": _percorso(u), "tot": sum(c.values()), "per_p": dict(c)}
                     for u, c in pag.items()), key=lambda v: -v["tot"])

    # ── stabilità: sempre / a volte / mai (domande generiche) ─────────────
    stab = {}
    for x in piatt:
        per_dom = defaultdict(list)
        for r in gen:
            if r["piattaforma"] == x:
                per_dom[r["id"]].append(r["menzione"])
        c = Counter("sempre" if all(v) else ("mai" if not any(v) else "a volte") for v in per_dom.values())
        stab[x] = {k: c.get(k, 0) for k in ("sempre", "a volte", "mai")}

    # ── dettaglio per domanda ─────────────────────────────────────────────
    righe = []
    for d in domande:
        rs = [r for r in R if r["id"] == d["id"]]
        if not rs:
            continue
        cella = {}
        for x in piatt:
            q = [r for r in rs if r["piattaforma"] == x]
            cella[x] = {"n": len(q), "m": sum(r["menzione"] for r in q), "c": sum(r["citazione"] for r in q)}
        concorrenti = Counter(c for r in rs for c in r["conc_menzionati"])
        fonti_d = Counter(dd for r in rs for dd in r["domini_fonti"] if not stesso_dominio(dd, p["dominio"]))
        righe.append({**d, "celle": cella, "linkato": sum(r["citazione"] for r in rs),
                      "concorrenti": [c for c, _ in concorrenti.most_common(4)],
                      "fonti": [f for f, _ in fonti_d.most_common(4)],
                      "risposte": [{"p": r["piattaforma"], "n": r["ripetizione"], "m": r["menzione"],
                                    "c": r["citazione"], "testo": r["testo"][:1800],
                                    "fonti": [f["url"] or f["dominio"] for f in r["fonti"]][:8]}
                                   for r in sorted(rs, key=lambda r: (P.ORDINE.index(r["piattaforma"]), r["ripetizione"]))]})

    gap = [r for r in righe if r["tipo"] == "generica" and not any(c["m"] for c in r["celle"].values())]

    # ── cosa dicono di te ─────────────────────────────────────────────────
    menz_tutte = [r for r in R if r["menzione"]]
    ruoli = Counter((r["giudizio"] or {}).get("ruolo", "tra le opzioni") for r in menz_tutte)
    toni = Counter((r["giudizio"] or {}).get("tono", "neutro") for r in menz_tutte)
    metodo_g = Counter((r["giudizio"] or {}).get("metodo", "euristica") for r in menz_tutte)
    # al massimo 2 frasi per domanda, alternando le domande: più varietà, meno ripetizioni
    frasi, visti, per_dom = [], set(), Counter()
    for r in sorted(menz_tutte, key=lambda r: (r["ripetizione"], r["tipo"] != "brand", r["id"])):
        cd = ((r["giudizio"] or {}).get("cosa_dice") or "").strip()
        if cd and cd.lower() not in visti and per_dom[r["id"]] < 2:
            per_dom[r["id"]] += 1
            visti.add(cd.lower())
            frasi.append({"testo": cd, "p": r["piattaforma"], "tono": r["giudizio"].get("tono", "neutro"),
                          "domanda": r["domanda"]})
    brand_p = []
    for x in piatt:
        rs = [r for r in bra if r["piattaforma"] == x]
        if rs:
            brand_p.append({"p": x, "nome": P.NOMI[x], "n": len(rs),
                            "cit": pct(sum(r["citazione"] for r in rs), len(rs)),
                            "cit_k": sum(r["citazione"] for r in rs)})

    A = {
        "brand": p["brand"], "dominio": p["dominio"], "piattaforme": piatt,
        "ripetizioni": p["ripetizioni"], "n_dom_gen": len(dom_gen), "n_dom_bra": len(dom_bra),
        "n_risposte": len(R), "per_p": per_p, "fasi": fasi, "sov": sov, "fonti": fonti, "nostra_fonte": nostra,
        "pagine": pagine, "senza_url": dict(senza_url), "stab": stab, "righe": righe, "gap": gap,
        "ruoli": dict(ruoli), "toni": dict(toni), "metodo_giudizio": dict(metodo_g), "frasi": frasi[:14],
        "brand_p": brand_p, "falsi_positivi": falsi, "concorrenti": nomi_conc,
        "modelli": {x: next((r["modello"] for r in R if r["piattaforma"] == x), p["modelli"].get(x)) for x in piatt},
        "date": (min((r["quando"] for r in R), default=""), max((r["quando"] for r in R), default="")),
        "costo_risposte": sum(float(r.get("costo", 0) or 0) for r in risposte),
    }
    A["confronto"] = confronta(p, domande, precedente) if precedente else None
    if A["confronto"]:
        A["confronto"]["attuale"] = {v["p"]: (v["menz"], v["cit"]) for v in per_p}
        _completa_confronto(A)
    A["sintesi"] = sintesi(A)
    A["azioni"] = azioni(A)
    return A


def confronta(p, domande, cartella_prec):
    """Numeri della misura precedente sulle STESSE domande (stesso id e testo)."""
    vecchie = carica_risposte(cartella_prec / "risposte.jsonl")
    testi = {d["id"]: d["domanda"] for d in domande if d["tipo"] == "generica"}
    vecchie = [r for r in vecchie if testi.get(r["id"]) == r.get("domanda")]
    if not vecchie:
        return None
    Rv, _ = arricchisci(p, vecchie, _carica_giudizi(cartella_prec))
    prima = {}
    for x in P.ORDINE:
        rs = [r for r in Rv if r["piattaforma"] == x]
        if rs:
            prima[x] = (pct(sum(r["menzione"] for r in rs), len(rs)), pct(sum(r["citazione"] for r in rs), len(rs)))
    data = min(r["quando"] for r in Rv)[:10]
    return {"data": data, "prima": prima, "ids": sorted({r["id"] for r in Rv})}


def _completa_confronto(A):
    """Il confronto vale solo sulle domande presenti in entrambe le misure:
    ricalcolo l'attuale sullo stesso sottoinsieme."""
    ids = set(A["confronto"]["ids"])
    att = {}
    for x in A["piattaforme"]:
        rs = []
        for riga in A["righe"]:
            if riga["id"] in ids and riga["tipo"] == "generica":
                rs += [r for r in riga["risposte"] if r["p"] == x]
        if rs:
            att[x] = (pct(sum(r["m"] for r in rs), len(rs)), pct(sum(r["c"] for r in rs), len(rs)))
    A["confronto"]["attuale"] = att


# ───────────────────────── parole per chi legge ──────────────────────────────

def _f(v):
    return f"{v:.0f}%"


def _elenco(voci):
    voci = list(voci)
    if len(voci) <= 1:
        return "".join(voci)
    return ", ".join(voci[:-1]) + " e " + voci[-1]


def sintesi(A):
    s = []
    pp = A["per_p"]
    if not pp:
        return ["Non ci sono ancora risposte da analizzare."]
    s.append(f"Abbiamo fatto {A['n_dom_gen']} domande in cui {A['brand']} non viene nominato, "
             f"ripetendole {A['ripetizioni']} volte su {_elenco(v['nome'] for v in pp)}.")
    s.append("Quando l'utente non fa il tuo nome, ti nominano "
             + _elenco(f"{v['nome']} nel {_f(v['menz'])}" for v in pp) + " delle risposte.")
    s.append("Il tuo sito compare fra i link delle fonti "
             + _elenco(f"nel {_f(v['cit'])} su {v['nome']}" for v in pp) + ".")
    migliore = max(pp, key=lambda v: v["menz"] + v["cit"])
    if len(pp) > 1 and migliore["menz"] + migliore["cit"] > 0:
        s.append(f"La piattaforma dove sei più visibile è {migliore['nome']}.")
    # concorrente più forte
    tot = Counter()
    for x, voci in A["sov"].items():
        for nome, v, tu in voci:
            if not tu:
                tot[nome] += v / len(A["sov"])
    if tot:
        nome, v = tot.most_common(1)[0]
        mia = sum(v2["menz"] for v2 in pp) / len(pp)
        if v > mia:
            s.append(f"Fra i concorrenti che ci hai indicato, {nome} compare più spesso di te "
                     f"({_f(v)} contro {_f(mia)}, in media fra le piattaforme).")
        elif v > 0:
            s.append(f"Compari più spesso dei concorrenti che ci hai indicato: il primo è {nome} con il {_f(v)}.")
    if A["gap"]:
        s.append(f"In {len(A['gap'])} domande su {A['n_dom_gen']} nessuna piattaforma ti nomina mai: "
                 f"le trovi più in basso.")
    return s


def azioni(A):
    out = []
    pp = A["per_p"]
    if not pp:
        return out
    menz_media = sum(v["menz"] for v in pp) / len(pp)
    cit_media = sum(v["cit"] for v in pp) / len(pp)
    solo_fonte = sum(v["solo_fonte"] for v in pp)
    cit_tot = sum(v["cit_k"] for v in pp)

    if A["gap"]:
        out.append(("Rispondi alle domande dove non ti nominano",
                    f"Nelle {len(A['gap'])} domande in cui non ti nomina nessuno, guarda chi viene nominato e quali siti vengono "
                    "usati come fonte. Se sul tuo sito manca una pagina che risponde in modo diretto e completo a "
                    "quella domanda, è il primo contenuto da creare."))
    if cit_tot and solo_fonte / cit_tot >= 0.25:
        out.append(("Ti usano come fonte, ma non dicono il tuo nome",
                    f"In {solo_fonte} risposte il tuo sito è fra i link ma il nome non compare nel testo. "
                    "Rendi il brand più riconoscibile dentro le pagine: nome nei titoli e nei dati originali, "
                    "pagine 'chi siamo' chiare, autore e azienda dichiarati."))
    if menz_media >= 15 and cit_media < menz_media / 2:
        out.append(("Ti nominano, ma linkano altri siti",
                    "Gli assistenti ti conoscono ma per i dettagli si affidano ad altre fonti. Crea pagine che "
                    "rispondono esattamente alle domande dei clienti (prezzi, confronti, guide, domande frequenti) "
                    "con informazioni aggiornate e facili da citare."))
    terzi = [f for f in A["fonti"] if not f["tipo"]][:5]
    if terzi:
        out.append(("Fatti trovare dove gli assistenti si informano",
                    f"I siti più usati come fonte sono {_elenco(f['dominio'] for f in terzi[:4])}. Essere presente "
                    "lì, con recensioni, schede, articoli o citazioni, aumenta la probabilità di essere nominato."))
    tot = Counter()
    for x, voci in A["sov"].items():
        for nome, v, tu in voci:
            if not tu:
                tot[nome] += v / len(A["sov"])
    if tot:
        nome, v = tot.most_common(1)[0]
        if v > menz_media:
            out.append((f"Studia perché {nome} viene preferito",
                        f"{nome} compare più spesso di te. Apri le sue risposte nella tabella delle domande: "
                        "guarda come viene descritto e da quali fonti arrivano le informazioni."))
    if len(pp) > 1:
        alto, basso = max(pp, key=lambda v: v["menz"]), min(pp, key=lambda v: v["menz"])
        if alto["menz"] - basso["menz"] >= 25:
            out.append((f"Su {basso['nome']} sei molto più debole",
                        f"Su {alto['nome']} ti nominano nel {_f(alto['menz'])} delle risposte, su {basso['nome']} "
                        f"nel {_f(basso['menz'])}. Le piattaforme cercano su motori e fonti diverse: controlla "
                        f"quali siti usa {basso['nome']} nella tabella delle fonti."))
    if A["brand_p"]:
        deboli = [b for b in A["brand_p"] if b["cit"] < 50]
        if deboli:
            out.append(("Quando ti cercano per nome, raccontano altri",
                        f"Nelle domande che contengono il tuo nome, {_elenco(b['nome'] for b in deboli)} "
                        "linka il tuo sito meno di una volta su due. Le informazioni su di te arrivano da siti terzi: "
                        "verifica che siano corrette e che il tuo sito spieghi bene chi sei, cosa offri e a che prezzo."))
    if A["toni"].get("negativo"):
        out.append(("Controlla le risposte con tono negativo",
                    f"In {A['toni']['negativo']} risposte il tono su di te è negativo. Leggile nella sezione "
                    "'Cosa dicono di te': spesso nascono da recensioni o articoli vecchi che si possono correggere."))
    if A["pagine"]:
        home = sum(v["tot"] for v in A["pagine"] if v["percorso"] in ("/", ""))
        tot_p = sum(v["tot"] for v in A["pagine"])
        if tot_p and home / tot_p > 0.6:
            out.append(("Viene linkata quasi solo la home",
                        "Gli assistenti linkano soprattutto la pagina principale. Pagine dedicate a singoli "
                        "prodotti, servizi o domande hanno più probabilità di essere citate come risposta precisa."))
    return out[:6]
