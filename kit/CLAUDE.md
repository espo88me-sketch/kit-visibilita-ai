# Kit Visibilità AI — istruzioni per Claude Code

Questa cartella è un tool che misura come ChatGPT, Gemini e Perplexity parlano di un sito.
La guida per le persone è `LEGGIMI.md`. Se l'utente ti chiede di usare il kit:

1. **Intervista in chat, breve.** Raccogli le risposte dei 4 passi (sito e brand · cosa offre, a chi,
   dove, mercato/lingua · concorrenti e fino a 3 domande vere dei clienti · piattaforme e tetto di spesa).
   Una domanda per volta, proponi tu i default. Scrivi le risposte in un file JSON con la stessa
   struttura di `esempio-risposte.json`.
2. **Chiavi.** Mai chiederle in chat e mai scriverle tu. L'utente le mette nel file `chiavi-api.txt`
   (righe `OPENAI_API_KEY=…`, `GEMINI_API_KEY=…`, `PERPLEXITY_API_KEY=…`) o nelle variabili d'ambiente.
3. `python3 avvia.py --crea <file.json>` → mostra le domande generate e chiedi se vanno bene.
   Si modificano in `progetti/<sito>/domande.csv`.
4. Comunica il costo stimato e chiedi conferma esplicita, poi:
   `python3 avvia.py --misura <sito> --si`. Non superare il tetto indicato dall'utente.
5. Indica il percorso di `progetti/<sito>/dashboard.html` e riassumi i numeri principali e i limiti.

Regole: non cambiare i modelli in `progetto.json` fra due misure dello stesso sito; per un confronto
usa `--misura <sito> --nuova` con le stesse domande; `--dashboard <sito>` non spende nulla.
