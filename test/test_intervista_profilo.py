"""Intervista con file di brand identity (.docx) e scansione del sito: niente rete, niente spesa.
Uso: python3 test/test_intervista_profilo.py <copia-del-kit>"""
import builtins, getpass, os, sys, tempfile, zipfile
from pathlib import Path
kit = Path(sys.argv[1]).resolve(); sys.path.insert(0, str(kit))
for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "PERPLEXITY_API_KEY"):
    os.environ.pop(k, None)
sys.argv = [sys.argv[0]]
import test_offline_fakes as T  # noqa
from motore import flusso as F, profilo as PR, piattaforme as P

# un computer finto: il .docx giusto, un'immagine con lo stesso nome, una cartella da saltare
casa = Path(tempfile.mkdtemp())
(casa / "Documents" / "Marketing 2026").mkdir(parents=True)
(casa / "Documents" / "node_modules").mkdir()
(casa / "Documents" / "node_modules" / "brand-book.docx").write_text("x")
(casa / "Documents" / "Marketing 2026" / "Brand Book.png").write_text("x")
tmp = casa / "Documents" / "Marketing 2026" / "Brand_Identità Il Poggio.docx"
with zipfile.ZipFile(tmp, "w") as z:
    z.writestr("word/document.xml", "<w:document><w:body><w:p><w:r><w:t>Agriturismo Il Poggio Srl: "
               "agriturismo con piscina sulle colline di Siena per famiglie e coppie.</w:t></w:r></w:p>"
               "<w:p><w:r><w:t>Ci confrontano spesso con Podere Verde.</w:t></w:r></w:p></w:body></w:document>")

PAGINE = {
    "https://www.ilpoggio.it": ("<html lang='it-IT'><head><title>Il Poggio</title><meta name='description' "
        "content='Agriturismo a Siena'><script>var x=1;</script></head><body><h1>Benvenuti</h1>"
        "<a href='/chi-siamo/'>Chi siamo</a><a href='/camere'>Le camere</a><a href='/contatti'>Contatti</a>"
        "<a href='https://facebook.com/ilpoggio'>fb</a><a href='/brochure.pdf'>pdf</a></body></html>"),
    "https://www.ilpoggio.it/chi-siamo/": "<p>Siamo una famiglia che dal 1990 accoglie ospiti a Siena, con piscina panoramica e cucina toscana.</p>",
    "https://www.ilpoggio.it/contatti": "<p>Strada del Poggio 1, Siena. Telefono e mail per prenotare il tuo soggiorno in Toscana.</p>",
}
scaricate = []
def finto_scarica(url, timeout=15):
    scaricate.append(url)
    return PAGINE[url], url
PR._scarica = finto_scarica
PR.cartelle_ricerca = lambda: [casa / "Documents"]
assert PR.cerca_documenti("brand identita") == [tmp]
assert PR.cerca_documenti("marketing") == [tmp]   # anche dal nome della cartella

viste = {}
vecchio = P.JSON_SERVIZIO["chatgpt"]
def json_profilo(chiave, istr, modello=None):
    if "compilare la scheda di un brand" in istr:
        viste["istr"] = istr
        return {"brand": "Il Poggio", "alias": ["Agriturismo Il Poggio Srl"], "offerta": "agriturismo con piscina",
                "pubblico": "famiglie e coppie", "zona": "Siena", "lingua": "it", "paese": "IT",
                "concorrenti": ["Podere Verde"]}, 0.002
    return vecchio(chiave, istr, modello)
for x in P.JSON_SERVIZIO:
    P.JSON_SERVIZIO[x] = json_profilo

risposte = iter([
    "www.ilpoggio.it",                 # sito
    "s",                               # ho un file di brand identity
    "listino prezzi",                  # niente → chiede un'altra parola
    "brand",                           # trova il file giusto, non il .png né node_modules
    "1",                               # lo sceglie
    "",                                # scansione: default sì
    "s",                               # salva chiavi
    "",                                # tengo le informazioni: default sì
    "",                                # concorrenti: tengo il default ricavato
    "",                                # nessuna domanda vera
    "1", "", "1", "s",                 # misura rapida, tetto default, domande ok, parto
])
builtins.input = lambda prompt="": (print(prompt, end=""), (r := next(risposte)), print(r))[1]
chiavi = iter(["", "g-finta-chiave-1234567890", ""])
getpass.getpass = lambda prompt="": (print(prompt + "****"), next(chiavi))[1]
F.verifica_chiave = lambda x, k: (True, "")
import webbrowser; webbrowser.open = lambda *a, **k: True
F.interattivo()
p = F.carica_progetto("ilpoggio.it")
print("\nPROGETTO:", {k: p[k] for k in ("brand", "alias", "offerta", "pubblico", "zona", "lingua", "paese", "concorrenti", "piattaforme")})
assert p["brand"] == "Il Poggio" and p["offerta"] == "agriturismo con piscina" and p["zona"] == "Siena"
assert p["concorrenti"] == [{"nome": "Podere Verde", "dominio": ""}] and p["piattaforme"] == ["gemini"]
assert p["spesa_preparazione"] >= 0.002
assert "/brochure.pdf" not in " ".join(scaricate) and "facebook" not in " ".join(scaricate)
assert scaricate[1] == "https://www.ilpoggio.it/chi-siamo/" and len(scaricate) == 3, scaricate
assert "colline di Siena" in viste["istr"] and "dal 1990" in viste["istr"] and "var x" not in viste["istr"]
print("INTERVISTA CON PROFILO OK")
