# Visibilità AI

Scopri come **ChatGPT, Gemini e Perplexity** parlano del tuo sito: se ti nominano, se linkano le tue pagine, quali pagine, chi propongono al posto tuo e cosa dicono di te.

Alla fine ottieni una **dashboard** che puoi aprire nel browser, anche offline, e inoltrare a chi vuoi.

Il metodo: le domande seguono il percorso del cliente, ognuna viene ripetuta più volte e le piattaforme restano separate.

---

## Cosa ti serve

| | |
|---|---|
| **Python 3.9 o più recente** | Su Mac di solito c'è già. Se manca, o su Windows: [python.org/downloads](https://www.python.org/downloads/). Su Windows, durante l'installazione spunta **"Add python.exe to PATH"** |
| **Almeno una chiave API** | Bastano anche una o due piattaforme: vedi la tabella qui sotto |
| **Qualche dollaro di credito** | Una misura rapida su tutte e tre le piattaforme costa circa 1,5 $. Il kit ti mostra il preventivo prima di partire e non supera mai il tetto che imposti |

Non serve installare altro: il kit usa solo Python.

### Le chiavi API

| Piattaforma | Dove si crea la chiave | Note |
|---|---|---|
| ChatGPT | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Serve credito prepagato sull'account API (è separato dall'abbonamento ChatGPT Plus) |
| Gemini | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Il piano gratuito basta per una misura rapida, ma va più lento |
| Perplexity | [perplexity.ai/account/api/keys](https://www.perplexity.ai/account/api/keys) | Serve credito prepagato |

Le chiavi le incolli durante l'intervista. Se vuoi, il kit le salva nel file `chiavi-api.txt` dentro questa cartella, così non te le richiede più. **Non condividere quel file.** Puoi anche cancellarlo quando vuoi.

Se l'incolla nel terminale non funziona, crea tu il file `chiavi-api.txt` in questa cartella, una riga per chiave (solo quelle che usi), e rilancia:

```
OPENAI_API_KEY=la-tua-chiave
GEMINI_API_KEY=la-tua-chiave
PERPLEXITY_API_KEY=la-tua-chiave
```

---

## Come si usa

**Mac:** doppio clic su `avvia-mac.command`. La prima volta macOS potrebbe bloccarlo: tasto destro → **Apri** → **Apri**.
In alternativa apri il Terminale in questa cartella e scrivi `python3 avvia.py`.

**Windows:** doppio clic su `avvia-windows.bat`.
In alternativa apri il Prompt dei comandi in questa cartella e scrivi `python avvia.py`.

Poi rispondi a **quattro passi**, in un paio di minuti:

1. **Il tuo sito**: l'indirizzo. Il kit ti chiede se hai un **file di brand identity** (PDF, Word, PowerPoint, testo): basta dirgli come si chiama, anche solo una parola, e lo cerca lui nelle cartelle Scrivania, Documenti, Download, OneDrive e iCloud. Poi ti chiede se può **leggere le pagine principali del sito** (home, chi siamo, servizi, contatti): se dici sì, ricava da lì le risposte dei passi 3 e 4 e tu le confermi
2. **Piattaforme**: le chiavi che vuoi usare
3. **Chi sei, cosa offri e a chi**: nome del brand, in poche parole cosa offri, dove lavori, in che lingua fare le domande
4. **Concorrenti e domande vere**: facoltativi, ma rendono la misura molto più utile. Alla fine scegli la grandezza della misura e il tetto di spesa

Il kit prepara le domande e te le mostra. Puoi accettarle, rigenerarle o correggerle a mano nel file `domande.csv`. Poi parte la misura e alla fine si apre la dashboard.

| Misura | Domande | Tempo | Costo indicativo (3 piattaforme) |
|---|---|---|---|
| Rapida | 15 × 3 ripetizioni | 5-10 minuti | circa 1,5 $ |
| Completa | 30 × 3 ripetizioni | 15-20 minuti | circa 3 $ |

Gemini è il più lento: il kit lo rallenta di proposito per restare nei limiti del piano gratuito. Il preventivo che vedi prima di partire è volutamente un po' più alto del costo reale.

### Se si interrompe

Nessun problema. Rilancia il kit e scegli **"Riprendi la misura interrotta"**: le risposte già raccolte non si ripagano.

### Per vedere se migliori

Rilancia il kit dopo 4-8 settimane e scegli **"Nuova misura con le stesse domande"**. La dashboard ti mostra la differenza rispetto alla misura precedente. Tieni le stesse domande: se le cambi, il confronto non vale più.

---

## Cosa trovi nella dashboard

- **In breve**: i numeri principali, piattaforma per piattaforma, spiegati a parole
- **Nominato e linkato**: due cose diverse, che il kit tiene separate
- **Percorso del cliente**: in quali fasi ci sei, dalla scoperta all'acquisto
- **Tu e i concorrenti**: chi viene nominato più spesso
- **Fonti**: i siti che gli assistenti usano per informarsi, e il tuo posto in classifica
- **Le tue pagine**: quali pagine del tuo sito vengono linkate
- **Stabilità**: in quante domande compari sempre, a volte o mai
- **Cosa dicono di te**: se sei consigliato o solo elencato, il tono, le frasi su di te
- **Dove non ci sei**: le domande in cui non compari mai, e chi compare al tuo posto
- **Cosa fare**: suggerimenti ricavati dai numeri
- **Tutte le domande**: ogni risposta, da leggere per intero
- **Limiti**: cosa questa analisi non può dirti

---

## I limiti, in breve

- Le domande passano dalle API, senza account né cronologia: chi usa le app da loggato può vedere risposte diverse
- I modelli delle API non sono per forza identici a quelli delle app
- Con 15-30 domande i numeri hanno un margine ampio: la dashboard lo indica sempre
- Le risposte cambiano nel tempo. La misura è una fotografia di questi giorni
- Non misura il traffico che arriva dagli assistenti: quello si legge in Google Analytics

La lista completa è nell'ultima sezione della dashboard.

---

## Dove finiscono i file

Tutto resta sul tuo computer, nella cartella `progetti/<tuo-sito>/`:

| File | Cosa contiene |
|---|---|
| `progetto.json` | le risposte all'intervista, i modelli usati e il tetto di spesa |
| `domande.csv` | le domande (modificabili con Excel o un editor di testo) |
| `dashboard.html` | l'ultima dashboard |
| `misure/<data>/risposte.jsonl` | le risposte grezze di ogni misura |

Le domande e le risposte passano solo da OpenAI, Google e Perplexity, attraverso le loro API. Se scegli di usarli, passano da lì anche il file di brand identity e il testo delle pagine del sito, una volta sola, per ricavare le risposte all'intervista: mandalo solo se puoi condividerlo con quel servizio. Il kit non manda niente a nessun altro.

---

## Problemi frequenti

| Messaggio | Cosa fare |
|---|---|
| `certificate verify failed` / "non riesce a verificare i certificati" | Mac con Python di python.org: apri Applicazioni → Python 3.x → doppio clic su **Install Certificates.command** |
| "chiave non valida" | Ricopia la chiave dal sito del servizio. Le chiavi salvate stanno in `chiavi-api.txt`: puoi correggerle lì o cancellarle |
| "credito esaurito" / "quota" | Aggiungi credito sull'account API di quella piattaforma, poi rilancia per riprendere |
| "modello non trovato" | Il modello è stato ritirato: cambialo in `progetto.json`, alla voce `"modelli"` (esempi: `gpt-5-mini`, `gemini-2.5-flash`, `sonar-pro`) |
| Su Windows si apre il Microsoft Store | Installa Python da python.org spuntando "Add python.exe to PATH" |

---

## Uso avanzato

```
python3 avvia.py --crea risposte.json        # crea un progetto da un file, senza intervista
python3 avvia.py --misura esempio.it --si    # lancia o riprende la misura senza conferme
python3 avvia.py --dashboard esempio.it      # rifà la dashboard senza spendere
```

Un esempio del file di risposte si trova in `esempio-risposte.json`.

---

Licenza MIT. Il software è fornito "così com'è", senza garanzie. I costi delle API sono a carico di chi usa il kit.
