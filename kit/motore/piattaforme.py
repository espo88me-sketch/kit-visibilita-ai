"""Le tre piattaforme: ChatGPT (API OpenAI), Gemini (API Google), Perplexity.

Ogni piattaforma viene interrogata CON la ricerca web attiva. Senza, il modello
risponde a memoria, non mostra fonti e la "citazione con link" sarebbe sempre
falsa per costruzione.

Ogni funzione `chiedi_*` ritorna un dizionario:
    testo   : la risposta
    fonti   : lista di {"url", "dominio"} nell'ordine in cui compaiono
    costo   : costo in dollari della chiamata (misurato dalla risposta quando
              possibile, altrimenti stimato)
    modello : il modello che ha risposto
"""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

from .util import dominio, post_json, risolvi_redirect, ErroreHTTP

NOMI = {"chatgpt": "ChatGPT", "gemini": "Gemini", "perplexity": "Perplexity"}
ORDINE = ["chatgpt", "gemini", "perplexity"]

# Modelli di default. Si cambiano in progetti/<sito>/progetto.json alla voce
# "modelli". ⚠️ Cambiarli fra due misure fa misurare la differenza fra modelli,
# non il cambiamento della tua visibilità.
MODELLI_DEFAULT = {
    "chatgpt": os.environ.get("KIT_MODELLO_CHATGPT", "gpt-5-mini"),
    "gemini": os.environ.get("KIT_MODELLO_GEMINI", "gemini-2.5-flash"),
    "perplexity": os.environ.get("KIT_MODELLO_PERPLEXITY", "sonar-pro"),
}

# Costo stimato per chiamata (dollari), usato SOLO per il preventivo prima di
# partire. Durante la misura il costo si calcola dai token della risposta.
STIMA_CHIAMATA = {"chatgpt": 0.02, "gemini": 0.004, "perplexity": 0.014}

# Prezzi per milione di token (input, output). Se il modello non è in tabella si
# usa la stima per chiamata: meglio sovrastimare che sforare il tetto di spesa.
PREZZI = {
    "gpt-5-mini": (0.25, 2.00), "gpt-5": (1.25, 10.00), "gpt-5-nano": (0.05, 0.40),
    "gpt-4.1-mini": (0.40, 1.60), "gpt-4.1": (2.00, 8.00), "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gemini-2.5-flash": (0.30, 2.50), "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-pro": (1.25, 10.00),
    "sonar": (1.00, 1.00), "sonar-pro": (3.00, 15.00),
}
COSTO_RICERCA_OPENAI = 0.01      # 10 $ ogni 1.000 ricerche web
COSTO_RICHIESTA_PERPLEXITY = {"sonar": 0.005, "sonar-pro": 0.006}

TIMEOUT = {"chatgpt": 180, "gemini": 90, "perplexity": 90}


def _prezzo(modello: str):
    if modello in PREZZI:
        return PREZZI[modello]
    # snapshot datati: "gpt-5-mini-2025-08-07" → "gpt-5-mini"
    for k in sorted(PREZZI, key=len, reverse=True):
        if modello.startswith(k):
            return PREZZI[k]
    return None


def _costo_token(modello, tin, tout, fallback):
    p = _prezzo(modello)
    if not p:
        return fallback
    return tin / 1e6 * p[0] + tout / 1e6 * p[1]


def _fonte(url: str):
    return {"url": url, "dominio": dominio(url)}


def _dedup(fonti):
    visti, out = set(), []
    for f in fonti:
        k = f["url"] or f["dominio"]
        if k and k not in visti:
            visti.add(k)
            out.append(f)
    return out


# ───────────────────────── ChatGPT ───────────────────────────────────────────

def chiedi_chatgpt(chiave, domanda, modello, paese=""):
    tool = {"type": "web_search"}
    if paese:
        tool["user_location"] = {"type": "approximate", "country": paese}
    corpo = {"model": modello, "input": domanda, "tools": [tool]}
    if modello.startswith(("gpt-5", "o")):
        corpo["reasoning"] = {"effort": "low"}
    d = post_json("https://api.openai.com/v1/responses", corpo,
                  {"Authorization": f"Bearer {chiave}"}, timeout=TIMEOUT["chatgpt"])
    testo, fonti, ricerche = "", [], 0
    for item in d.get("output", []) or []:
        if item.get("type") == "web_search_call":
            ricerche += 1
        for c in item.get("content", []) or []:
            if c.get("type") != "output_text":
                continue
            testo += c.get("text", "") or ""
            # le fonti stanno nelle annotation del testo: sono i link che vede l'utente
            for a in c.get("annotations", []) or []:
                if a.get("type") == "url_citation" and a.get("url"):
                    fonti.append(_fonte(a["url"]))
    u = d.get("usage") or {}
    costo = _costo_token(modello, u.get("input_tokens", 0) or 0, u.get("output_tokens", 0) or 0,
                         STIMA_CHIAMATA["chatgpt"]) + ricerche * COSTO_RICERCA_OPENAI
    return {"testo": testo, "fonti": _dedup(fonti), "costo": costo, "modello": d.get("model", modello)}


# ───────────────────────── Gemini ────────────────────────────────────────────

def chiedi_gemini(chiave, domanda, modello, paese=""):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modello}:generateContent"
    corpo = {"contents": [{"parts": [{"text": domanda}]}], "tools": [{"google_search": {}}]}
    d = post_json(url, corpo, {"x-goog-api-key": chiave}, timeout=TIMEOUT["gemini"])
    cands = d.get("candidates") or []
    if not cands:
        motivo = (d.get("promptFeedback") or {}).get("blockReason", "risposta vuota")
        raise RuntimeError(f"Gemini non ha risposto ({motivo})")
    cand = cands[0]
    testo = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []) or [])
    chunk = (cand.get("groundingMetadata") or {}).get("groundingChunks", []) or []

    # Gemini non dà l'indirizzo della pagina ma un link di reindirizzamento di
    # Google: lo si segue per sapere QUALE pagina è stata usata, non solo il sito.
    def risolvi(ch):
        w = ch.get("web") or {}
        uri, tit = w.get("uri", ""), (w.get("domain") or w.get("title") or "")
        finale = risolvi_redirect(uri) if "grounding-api-redirect" in uri else uri
        if finale:
            return {"url": finale, "dominio": dominio(finale)}
        return {"url": "", "dominio": dominio(tit) if "." in tit else tit.lower()}

    with ThreadPoolExecutor(6) as ex:
        fonti = list(ex.map(risolvi, chunk))
    u = d.get("usageMetadata") or {}
    tout = (u.get("candidatesTokenCount", 0) or 0) + (u.get("thoughtsTokenCount", 0) or 0)
    costo = _costo_token(modello, u.get("promptTokenCount", 0) or 0, tout, STIMA_CHIAMATA["gemini"])
    return {"testo": testo, "fonti": _dedup([f for f in fonti if f["dominio"]]), "costo": costo,
            "modello": d.get("modelVersion", modello)}


# ───────────────────────── Perplexity ────────────────────────────────────────

def chiedi_perplexity(chiave, domanda, modello, paese=""):
    corpo = {"model": modello, "messages": [{"role": "user", "content": domanda}]}
    if paese:
        corpo["web_search_options"] = {"user_location": {"country": paese}}
    d = post_json("https://api.perplexity.ai/chat/completions", corpo,
                  {"Authorization": f"Bearer {chiave}"}, timeout=TIMEOUT["perplexity"])
    testo = d["choices"][0]["message"]["content"] or ""
    # l'API ha esposto nel tempo sia `citations` (lista di URL) sia `search_results`
    urls = d.get("citations") or [s.get("url", "") for s in d.get("search_results", []) or []]
    u = d.get("usage") or {}
    costo = (u.get("cost") or {}).get("total_cost")
    if costo is None:
        costo = _costo_token(modello, u.get("prompt_tokens", 0) or 0, u.get("completion_tokens", 0) or 0,
                             STIMA_CHIAMATA["perplexity"]) + COSTO_RICHIESTA_PERPLEXITY.get(modello, 0.006)
    return {"testo": testo, "fonti": _dedup([_fonte(x) for x in urls if x]), "costo": float(costo),
            "modello": d.get("model", modello)}


CHIEDI = {"chatgpt": chiedi_chatgpt, "gemini": chiedi_gemini, "perplexity": chiedi_perplexity}


# ───────────────────────── chiamate di servizio (senza ricerca web) ──────────
# Servono a preparare le domande e a leggere le risposte (raccomandazione, tono).
# Si usa la piattaforma più economica disponibile, mai con la ricerca accesa.

def _estrai_json(testo: str):
    testo = (testo or "").strip()
    testo = re.sub(r"^```(?:json)?\s*|\s*```$", "", testo)
    try:
        return json.loads(testo)
    except Exception:  # noqa: BLE001
        m = re.search(r"\{.*\}", testo, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def json_chatgpt(chiave, istruzioni, modello="gpt-5-mini"):
    corpo = {"model": modello, "input": istruzioni, "text": {"format": {"type": "json_object"}}}
    if modello.startswith("gpt-5"):
        corpo["reasoning"] = {"effort": "minimal"}
    try:
        d = post_json("https://api.openai.com/v1/responses", corpo,
                      {"Authorization": f"Bearer {chiave}"}, timeout=120)
    except ErroreHTTP as e:
        # i modelli più nuovi possono non accettare "minimal": si riprova senza
        if e.stato == 400 and "reasoning" in e.corpo.lower() and "reasoning" in corpo:
            corpo.pop("reasoning")
            d = post_json("https://api.openai.com/v1/responses", corpo,
                          {"Authorization": f"Bearer {chiave}"}, timeout=120)
        else:
            raise
    testo = "".join(c.get("text", "") for it in d.get("output", []) or []
                    for c in it.get("content", []) or [] if c.get("type") == "output_text")
    u = d.get("usage") or {}
    costo = _costo_token(modello, u.get("input_tokens", 0) or 0, u.get("output_tokens", 0) or 0, 0.005)
    return _estrai_json(testo), costo


def json_gemini(chiave, istruzioni, modello="gemini-2.5-flash"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modello}:generateContent"
    gen = {"responseMimeType": "application/json"}
    if "flash" in modello:
        gen["thinkingConfig"] = {"thinkingBudget": 0}
    d = post_json(url, {"contents": [{"parts": [{"text": istruzioni}]}], "generationConfig": gen},
                  {"x-goog-api-key": chiave}, timeout=120)
    testo = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
    u = d.get("usageMetadata") or {}
    costo = _costo_token(modello, u.get("promptTokenCount", 0) or 0,
                         (u.get("candidatesTokenCount", 0) or 0) + (u.get("thoughtsTokenCount", 0) or 0), 0.002)
    return _estrai_json(testo), costo


def json_perplexity(chiave, istruzioni, modello="sonar"):
    d = post_json("https://api.perplexity.ai/chat/completions",
                  {"model": modello, "messages": [
                      {"role": "system", "content": "Rispondi solo con un oggetto JSON valido, senza testo prima o dopo."},
                      {"role": "user", "content": istruzioni}]},
                  {"Authorization": f"Bearer {chiave}"}, timeout=120)
    u = d.get("usage") or {}
    costo = (u.get("cost") or {}).get("total_cost") or 0.01
    return _estrai_json(d["choices"][0]["message"]["content"]), float(costo)


JSON_SERVIZIO = {"chatgpt": json_chatgpt, "gemini": json_gemini, "perplexity": json_perplexity}
# ordine di preferenza: dal più economico e senza ricerca web al più caro
PREFERENZA_SERVIZIO = ["gemini", "chatgpt", "perplexity"]
