"""Funzioni di servizio: HTTP senza dipendenze, terminale, chiavi API.

Tutto il kit usa solo la libreria standard di Python: chi lo scarica non deve
installare nulla oltre a Python 3.8+.
"""
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

KIT = Path(__file__).resolve().parent.parent
FILE_CHIAVI = KIT / "chiavi-api.txt"

# Su Windows il terminale non sempre parla UTF-8: senza questo le lettere
# accentate e i simboli mandano in crash la stampa.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass


# ───────────────────────── terminale ─────────────────────────────────────────

def _colori_attivi() -> bool:
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        os.system("")  # attiva le sequenze ANSI nel terminale di Windows 10+
    return True


_C = _colori_attivi()


def _c(cod, t):
    return f"\033[{cod}m{t}\033[0m" if _C else t


def grassetto(t): return _c("1", t)
def tenue(t): return _c("2", t)
def verde(t): return _c("32", t)
def giallo(t): return _c("33", t)
def rosso(t): return _c("31", t)
def blu(t): return _c("36", t)


def titolo(passo: str, testo: str):
    print()
    print(grassetto(blu(f"── {passo} · {testo} ")) + blu("─" * max(0, 56 - len(passo) - len(testo))))


def chiedi(domanda: str, default: str = "", obbligatoria: bool = False) -> str:
    suff = f" [{default}]" if default else ""
    while True:
        try:
            r = input(f"  {domanda}{tenue(suff)}: ").strip()
        except EOFError:
            r = ""
        if not r:
            r = default
        if r or not obbligatoria:
            return r
        print(giallo("  Serve una risposta per andare avanti."))


def conferma(domanda: str, default: bool = True) -> bool:
    d = "S/n" if default else "s/N"
    r = chiedi(f"{domanda} ({d})").lower()
    if not r:
        return default
    return r[0] in ("s", "y")


def scegli(domanda: str, opzioni: list, default: int = 1) -> int:
    """Menu numerato. Ritorna l'indice (da 1) dell'opzione scelta."""
    for i, o in enumerate(opzioni, 1):
        print(f"    {i}) {o}")
    while True:
        r = chiedi(domanda, str(default))
        if r.isdigit() and 1 <= int(r) <= len(opzioni):
            return int(r)
        print(giallo(f"  Scrivi un numero da 1 a {len(opzioni)}."))


# ───────────────────────── domini e testo ────────────────────────────────────

def dominio(url_o_dominio: str) -> str:
    """'https://www.Esempio.it/pagina' → 'esempio.it'."""
    s = (url_o_dominio or "").strip().lower()
    if not s:
        return ""
    if "://" not in s:
        s = "http://" + s
    try:
        h = urlparse(s).hostname or ""
    except Exception:  # noqa: BLE001
        return ""
    return h[4:] if h.startswith("www.") else h


def sembra_dominio(s: str) -> bool:
    return bool(re.fullmatch(r"(https?://)?(www\.)?[a-z0-9-]+(\.[a-z0-9-]+)+(/.*)?", s.strip().lower()))


def stesso_dominio(d: str, nostro: str) -> bool:
    """Vero anche per i sottodomini: blog.esempio.it conta come esempio.it."""
    d, nostro = (d or "").lower(), (nostro or "").lower()
    return bool(nostro) and (d == nostro or d.endswith("." + nostro))


def radice(d: str) -> str:
    """'tripadvisor.co.uk' e 'it.tripadvisor.com' → 'tripadvisor'. Serve a
    riconoscere le versioni nazionali di uno stesso concorrente."""
    parti = (d or "").lower().split(".")
    if len(parti) >= 3 and parti[-2] in ("co", "com", "org", "net", "gov", "ac", "gob", "edu"):
        return parti[-3]
    return parti[-2] if len(parti) >= 2 else (parti[0] if parti else "")


def regex_nome(nome: str):
    """Regex tollerante per un nome di brand.

    'Esempio.it' trova anche 'esempio it' e 'Esempio .it'; 'Mario Rossi Srl'
    trova 'mario-rossi srl'. I bordi sono lookaround e non \\b, perché un nome
    può finire con un punto o un simbolo.
    """
    pezzi = [re.escape(p) for p in re.findall(r"[^\W_]+", nome or "", flags=re.UNICODE)]
    if not pezzi:
        return None
    corpo = r"[\s.\-_'’&]*".join(pezzi)
    return re.compile(rf"(?<![^\W_]){corpo}(?![^\W_])", re.I | re.UNICODE)


# ───────────────────────── chiavi API ────────────────────────────────────────

NOMI_CHIAVI = {
    "chatgpt": ["OPENAI_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "perplexity": ["PERPLEXITY_API_KEY"],
}


def leggi_file_chiavi() -> dict:
    out = {}
    if FILE_CHIAVI.exists():
        for riga in FILE_CHIAVI.read_text(encoding="utf-8").splitlines():
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                k, v = riga.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v:
                    out[k.strip()] = v
    return out


def chiave(piattaforma: str) -> str:
    """Prima le variabili d'ambiente, poi il file chiavi-api.txt nella cartella del kit."""
    da_file = leggi_file_chiavi()
    for n in NOMI_CHIAVI[piattaforma]:
        v = os.environ.get(n) or da_file.get(n)
        if v:
            return v.strip()
    return ""


def salva_chiave(piattaforma: str, valore: str):
    nome = NOMI_CHIAVI[piattaforma][0]
    righe = []
    if FILE_CHIAVI.exists():
        righe = [r for r in FILE_CHIAVI.read_text(encoding="utf-8").splitlines()
                 if not r.strip().startswith(nome + "=")]
    else:
        righe = ["# Chiavi API del kit Visibilita' AI. Non condividere questo file.",
                 "# Si cancella in qualsiasi momento: il kit le richiede al prossimo avvio."]
    righe.append(f"{nome}={valore}")
    FILE_CHIAVI.write_text("\n".join(righe) + "\n", encoding="utf-8")
    try:
        os.chmod(FILE_CHIAVI, 0o600)
    except Exception:  # noqa: BLE001
        pass


def maschera(k: str) -> str:
    return (k[:4] + "…" + k[-4:]) if len(k) > 12 else "…"


# ───────────────────────── HTTP ──────────────────────────────────────────────

class ErroreHTTP(Exception):
    def __init__(self, stato: int, corpo: str):
        self.stato = stato
        self.corpo = corpo
        super().__init__(f"HTTP {stato}: {corpo[:300]}")


def _contesto_ssl():
    # Il Python scaricato da python.org su Mac spesso non trova i certificati:
    # se c'è certifi lo si usa, altrimenti il default di sistema.
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        return ssl.create_default_context()


_SSL = _contesto_ssl()

MSG_SSL = ("Python non riesce a verificare i certificati HTTPS. Su Mac apri la cartella "
           "Applicazioni → Python 3.x e fai doppio clic su 'Install Certificates.command', "
           "poi riavvia il kit.")


def post_json(url: str, corpo: dict, headers: dict, timeout: int = 120) -> dict:
    dati = json.dumps(corpo).encode("utf-8")
    h = {"Content-Type": "application/json", "User-Agent": "kit-visibilita-ai/1.0", **headers}
    req = urllib.request.Request(url, data=dati, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            testo = e.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            testo = ""
        raise ErroreHTTP(e.code, testo) from None
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLError) or "CERTIFICATE" in str(e.reason).upper():
            raise RuntimeError(MSG_SSL) from None
        raise


def get_ok(url: str, headers: dict, timeout: int = 20):
    """GET gratuito per verificare una chiave. Ritorna (ok, messaggio)."""
    req = urllib.request.Request(url, headers={"User-Agent": "kit-visibilita-ai/1.0", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
            r.read()
            return True, ""
    except urllib.error.HTTPError as e:
        try:
            corpo = e.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            corpo = ""
        return False, errore_leggibile(ErroreHTTP(e.code, corpo))
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLError) or "CERTIFICATE" in str(e.reason).upper():
            return False, MSG_SSL
        return False, f"connessione non riuscita ({e.reason})"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # noqa: D401
        return None


_opener_noredir = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=_SSL))


def risolvi_redirect(url: str, timeout: int = 8) -> str:
    """URL finale di un link di reindirizzamento (le fonti di Gemini passano da
    vertexaisearch.cloud.google.com). Se non si risolve ritorna stringa vuota."""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
    try:
        r = _opener_noredir.open(req, timeout=timeout)
        return r.geturl() if r.geturl() != url else ""
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e.headers.get("Location", "") or ""
        return ""
    except Exception:  # noqa: BLE001
        return ""


def errore_leggibile(e: Exception) -> str:
    """Traduce gli errori delle API in una frase che chiunque capisce."""
    if isinstance(e, ErroreHTTP):
        if e.stato in (401, 403):
            return "chiave non valida o senza permessi"
        if e.stato == 402:
            return "credito esaurito sull'account"
        if e.stato == 429:
            if "quota" in e.corpo.lower() or "billing" in e.corpo.lower() or "insufficient" in e.corpo.lower():
                return "quota o credito esaurito"
            return "troppe richieste ravvicinate (limite di frequenza)"
        if e.stato == 404:
            return "modello non trovato: potrebbe essere stato ritirato (vedi config nel LEGGIMI)"
        if e.stato >= 500:
            return "il servizio ha un problema temporaneo"
        return f"errore {e.stato}"
    if isinstance(e, TimeoutError) or "timed out" in str(e).lower():
        return "nessuna risposta entro il tempo limite"
    return str(e)[:200]


def non_riprovare(e: Exception) -> bool:
    """Errori che non migliorano riprovando la stessa chiamata."""
    if isinstance(e, ErroreHTTP):
        if e.stato in (400, 401, 402, 403, 404):
            return True
        if e.stato == 429 and "insufficient_quota" in e.corpo.lower():
            return True
    return False


def blocca_piattaforma(e: Exception) -> bool:
    """Errori che valgono per tutte le chiamate successive: chiave sbagliata,
    credito finito, modello sparito. Inutile continuare a bussare.

    ⚠️ Il 429 "quota" di Gemini NON è qui: Google usa lo stesso messaggio anche
    per il limite al minuto, che passa da solo. Ci pensa il contatore di errori
    consecutivi in misura.py.
    """
    if isinstance(e, ErroreHTTP):
        if e.stato in (401, 402, 403, 404):
            return True
        if e.stato == 429 and "insufficient_quota" in e.corpo.lower():
            return True
    return False
