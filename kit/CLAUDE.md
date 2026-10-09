# Kit Visibilità AI — istruzioni per Claude Code

Questa cartella è un tool che misura come ChatGPT, Gemini e Perplexity parlano di un sito.
La guida per le persone è `LEGGIMI.md`. Se l'utente ti chiede di usare il kit:

1. **Intervista in chat, breve.** Chiedi l'indirizzo del sito, poi due domande esplicite prima delle altre:
   - "Hai un file di brand identity (brand book, presentazione, profilo aziendale)?" Se sì, chiedi come si chiama
     (anche solo una parola) e cercalo tu sul computer (Scrivania, Documenti, Download, OneDrive, iCloud):
     proponi i file trovati, fai scegliere quello giusto e leggilo. Non chiedere di trascinarlo;
   - "Posso leggere le pagine principali del sito (home, chi siamo, servizi, contatti) per ricavare le
     informazioni?" Solo con un sì esplicito.
   Da quello che leggi ricava brand, altri nomi, offerta (come la direbbe un cliente), pubblico, zona,
   mercato/lingua e i concorrenti nominati: mostrali tutti insieme e chiedi conferma. Chiedi solo i campi
   mancanti o da correggere, poi fino a 3 domande vere dei clienti, piattaforme e tetto di spesa.
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
