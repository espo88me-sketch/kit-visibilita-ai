# Visibilità AI

Misura come **ChatGPT, Gemini e Perplexity** parlano del tuo sito: se ti nominano, se ti linkano, quali pagine, chi propongono al posto tuo e cosa dicono di te. Alla fine apre una dashboard leggibile da chiunque.

- Intervista in 4 passi, poi le domande le prepara il kit, seguendo la [AI Search Prompt Library di Aleyda Solis](https://www.aleydasolis.com/en/ai-search/ai-search-prompt-library/)
- Usa una, due o tutte e tre le piattaforme: dipende dalle chiavi API che hai
- Solo Python 3.9+, nessuna libreria da installare
- Tetto di spesa: il kit non lo supera mai. Una misura rapida su tre piattaforme costa circa 1,5 $
- Tutto resta sul tuo computer

## Scarica

Scarica `visibilita-ai.zip` dall'ultima [release](../../releases/latest), estrailo e leggi `LEGGIMI.md`. Su Windows estrailo con tasto destro → **Estrai tutto…**: non aprirlo con l'app di Claude, che lo scambierebbe per una skill da installare. Il file `.sha256` accanto allo zip serve a verificare che non sia stato alterato:

```
shasum -a 256 visibilita-ai.zip        # Mac / Linux
certutil -hashfile visibilita-ai.zip SHA256   # Windows
```

## Licenza

MIT. Fornito "così com'è", senza garanzie. I costi delle API sono a carico di chi usa il kit.
