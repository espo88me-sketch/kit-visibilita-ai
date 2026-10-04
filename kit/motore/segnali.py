"""Cosa si legge in ogni risposta.

I segnali restano DISTINTI, come chiede il metodo: essere nominati, essere
linkati come fonte, essere consigliati e essere descritti correttamente sono
quattro cose diverse. Schiacciarle in un "sì/no" nasconde proprio le
differenze che servono per decidere cosa fare.

- menzione   : il nome del brand (o il dominio) compare nel testo. Deterministico.
- citazione  : un link al sito è fra le fonti della risposta. Deterministico.
- pagine     : QUALI pagine del sito vengono linkate.
- posizione  : fra il brand e i concorrenti nominati, in che ordine compare.
- ruolo/tono : consigliato, fra le opzioni, citato di passaggio, sconsigliato.
               Richiede di capire il testo: lo fa un'AI di servizio, oppure
               un'euristica se nessuna AI di servizio è disponibile.
"""
import re

from . import piattaforme as P
from .util import radice, regex_nome, stesso_dominio


def _regex_brand(p):
    rx = [regex_nome(p["brand"])] + [regex_nome(a) for a in p.get("alias", [])]
    rx.append(re.compile(re.escape(p["dominio"]), re.I))
    return [r for r in rx if r]


def _regex_conc(c):
    rx = [regex_nome(c["nome"])]
    if c.get("dominio"):
        rx.append(re.compile(re.escape(c["dominio"]), re.I))
    return [r for r in rx if r]


def _primo(rx_list, testo):
    pos = [m.start() for r in rx_list for m in [r.search(testo)] if m]
    return min(pos) if pos else None


def senza_tracciamento(url: str) -> str:
    """Toglie utm_* e simili: ChatGPT aggiunge ?utm_source=openai ai link, e la
    stessa pagina non deve contare come due pagine diverse."""
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
    u = urlparse(url)
    q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
         if not k.lower().startswith(("utm_", "gclid", "fbclid", "srsltid"))]
    return urlunparse(u._replace(query=urlencode(q), fragment=""))


def leggi(p: dict, testo: str, fonti: list) -> dict:
    testo = testo or ""
    rxb = _regex_brand(p)
    inizio_brand = _primo(rxb, testo)
    menzione = inizio_brand is not None

    nostre = [f for f in fonti if stesso_dominio(f["dominio"], p["dominio"])]
    pagine = sorted({senza_tracciamento(f["url"]) for f in nostre if f["url"]})

    conc_menz, conc_cit, ordine = [], [], []
    if menzione:
        ordine.append((inizio_brand, p["brand"]))
    for c in p.get("concorrenti", []):
        i = _primo(_regex_conc(c), testo)
        if i is not None:
            conc_menz.append(c["nome"])
            ordine.append((i, c["nome"]))
        if c.get("dominio") and any(stesso_dominio(f["dominio"], c["dominio"]) or radice(f["dominio"]) == radice(c["dominio"])
                                    for f in fonti):
            conc_cit.append(c["nome"])
    ordine.sort()
    posizione = [n for _, n in ordine].index(p["brand"]) + 1 if menzione else None

    return {
        "menzione": menzione,
        "citazione": bool(nostre),
        "pagine": pagine,
        "posizione": posizione,
        "nominati": len(ordine),
        "conc_menzionati": conc_menz,
        "conc_citati": conc_cit,
        "domini_fonti": sorted({f["dominio"] for f in fonti if f["dominio"]}),
        "estratto": estratto(rxb, testo),
    }


def estratto(rx_list, testo, larghezza=220, massimo=3):
    """Le frasi attorno alle menzioni del brand, per chi legge e per il giudizio."""
    pezzi, coperto = [], -1
    for r in rx_list:
        for m in r.finditer(testo):
            if m.start() <= coperto:
                continue
            a, b = max(0, m.start() - larghezza), min(len(testo), m.end() + larghezza)
            coperto = b
            pezzi.append((a, b))
    pezzi.sort()
    fusi = []
    for a, b in pezzi:
        if fusi and a <= fusi[-1][1]:
            fusi[-1] = (fusi[-1][0], max(b, fusi[-1][1]))
        else:
            fusi.append((a, b))
    out = []
    for a, b in fusi[:massimo]:
        s = testo[a:b].replace("\n", " ")
        s = re.sub(r"\s+", " ", s).strip()
        out.append(("…" if a > 0 else "") + s + ("…" if b < len(testo) else ""))
    return " ".join(out)


# ───────────────────────── giudizio: consigliato o solo nominato? ───────────

RUOLI = ["consigliato", "tra le opzioni", "citato di passaggio", "sconsigliato"]
TONI = ["positivo", "neutro", "negativo"]


def _istruzioni_giudizio(p, domanda, estratto_txt, lingua_report="italiano"):
    return f"""Leggi questo estratto della risposta di un assistente AI alla domanda di un utente.
Il brand da valutare è "{p['brand']}" (sito {p['dominio']}), che offre: {p['offerta']}.

DOMANDA DELL'UTENTE: {domanda}

ESTRATTO DELLA RISPOSTA:
{estratto_txt[:2400]}

Rispondi SOLO con questo JSON:
{{"si_riferisce_al_brand": true/false,
  "ruolo": "consigliato" | "tra le opzioni" | "citato di passaggio" | "sconsigliato",
  "tono": "positivo" | "neutro" | "negativo",
  "cosa_dice": "in {lingua_report}, massimo 20 parole: cosa afferma la risposta sul brand"}}

Definizioni:
- si_riferisce_al_brand: false se la parola coincide col nome ma indica altro (una parola comune, un omonimo).
- consigliato: la risposta lo indica come scelta da fare o fra le prime raccomandate.
- tra le opzioni: compare in un elenco di alternative, senza una spinta particolare.
- citato di passaggio: nominato come esempio, fonte o dettaglio, non come opzione da scegliere.
- sconsigliato: la risposta invita a evitarlo o ne evidenzia soprattutto problemi."""


_RX_CONSIGLIO = re.compile(
    r"\b(consigli|raccomand|miglior|ti suggerisco|la scelta|ideale|perfett|top|"
    r"recommend|best|ideal|go[- ]to|top pick|first choice)\w*", re.I)
_RX_NEG = re.compile(r"\b(evita|sconsigli|problem|lament|truffa|negativ|avoid|scam|complain|poor)\w*", re.I)


def giudizio_euristico(p, estratto_txt):
    vicino = estratto_txt[:600]
    if _RX_NEG.search(vicino):
        return {"si_riferisce_al_brand": True, "ruolo": "tra le opzioni", "tono": "negativo",
                "cosa_dice": "", "metodo": "euristica"}
    ruolo = "consigliato" if _RX_CONSIGLIO.search(vicino) else "tra le opzioni"
    return {"si_riferisce_al_brand": True, "ruolo": ruolo, "tono": "neutro", "cosa_dice": "",
            "metodo": "euristica"}


def giudica(p, domanda, estratto_txt, chiavi) -> tuple:
    """Prova con le AI di servizio (mai Perplexity: cercherebbe sul web e
    giudicherebbe altro), altrimenti euristica. Ritorna (giudizio, costo)."""
    for piatt in ("chatgpt", "gemini"):
        k = chiavi.get(piatt)
        if not k:
            continue
        try:
            g, costo = P.JSON_SERVIZIO[piatt](k, _istruzioni_giudizio(p, domanda, estratto_txt))
            ruolo = g.get("ruolo") if g.get("ruolo") in RUOLI else "tra le opzioni"
            tono = g.get("tono") if g.get("tono") in TONI else "neutro"
            rif = g.get("si_riferisce_al_brand")
            rif = rif if isinstance(rif, bool) else str(rif).lower() != "false"
            return {"si_riferisce_al_brand": rif, "ruolo": ruolo, "tono": tono,
                    "cosa_dice": str(g.get("cosa_dice", ""))[:200], "metodo": P.NOMI[piatt]}, costo
        except Exception:  # noqa: BLE001
            continue
    return giudizio_euristico(p, estratto_txt), 0.0
