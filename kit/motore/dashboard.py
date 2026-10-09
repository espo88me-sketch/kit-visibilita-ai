"""La dashboard: un solo file HTML, senza collegamenti esterni, leggibile da tutti.

Funziona anche offline e si può inoltrare per email. I grafici sono barre in
HTML/CSS (si adattano al telefono), il passaggio del mouse mostra il dettaglio.
"""
import html
import re
from datetime import datetime

from . import piattaforme as P
from .domande import FASI, SPIEGAZIONE_FASI

e = html.escape

CSS = """
:root{--bg:#f9f9f7;--card:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--mute:#6f6d68;--grid:#e1e0d9;
--base:#c3c2b7;--ring:rgba(11,11,11,.10);--s1:#2a78d6;--s2:#eb6834;--seq1:#cde2fb;--seq7:#0d366b;
--st-sempre:#184f95;--st-avolte:#86b6ef;--st-mai:#e1e0d9;--good:#006300;--bad:#d03b3b;--warn:#a86b00;--chip:#f0efec}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d0d0d;--card:#1a1a19;--ink:#fff;
--ink2:#c3c2b7;--mute:#9a988f;--grid:#2c2c2a;--base:#383835;--ring:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;
--st-sempre:#5598e7;--st-avolte:#1c5cab;--st-mai:#383835;--good:#0ca30c;--bad:#e66767;--warn:#fab219;--chip:#2c2c2a}}
:root[data-theme="dark"]{--bg:#0d0d0d;--card:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--mute:#9a988f;--grid:#2c2c2a;
--base:#383835;--ring:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;--st-sempre:#5598e7;--st-avolte:#1c5cab;
--st-mai:#383835;--good:#0ca30c;--bad:#e66767;--warn:#fab219;--chip:#2c2c2a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:28px 16px 64px}
header h1{font-size:28px;line-height:1.2;margin:0 0 6px}
header p{margin:0;color:var(--ink2);font-size:14px}
nav{display:flex;flex-wrap:wrap;gap:6px;margin:18px 0 8px}
nav a{font-size:13px;color:var(--ink2);text-decoration:none;background:var(--chip);padding:4px 10px;border-radius:99px}
nav a:hover{color:var(--ink)}
section{background:var(--card);border:1px solid var(--ring);border-radius:14px;padding:22px 22px 18px;margin:18px 0}
section h2{font-size:20px;margin:0 0 4px}
.lead{color:var(--ink2);margin:0 0 16px;font-size:15px}
.sintesi p{margin:0 0 8px;font-size:17px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin-top:16px}
.card{border:1px solid var(--ring);border-radius:12px;padding:14px 16px}
.card h3{margin:0 0 10px;font-size:15px}
.kpi{display:flex;align-items:baseline;gap:8px;margin:2px 0}
.kpi b{font-size:30px;line-height:1.1}
.kpi span{color:var(--ink2);font-size:14px}
.small{font-size:13px;color:var(--mute)}
.bars{display:grid;gap:10px}
.row{display:grid;grid-template-columns:minmax(90px,170px) 1fr 52px;align-items:center;gap:10px}
.row .lab{font-size:14px;display:flex;align-items:center;gap:6px;min-width:0}
.row .lab .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.row .lab .tag{flex:none}
.wide .row{grid-template-columns:minmax(120px,260px) 1fr 52px}
.row .val{font-size:14px;text-align:right;font-variant-numeric:tabular-nums}
.track{height:12px;border-radius:0 4px 4px 0;position:relative}
.fill{height:12px;border-radius:0 4px 4px 0;min-width:2px;border-left:1px solid var(--base)}
.grp{margin:4px 0 14px}.grp h4{margin:0 0 6px;font-size:14px}
.grp .row{grid-template-columns:110px 1fr 52px}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--ink2);margin:0 0 12px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.multi{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--grid);vertical-align:top}
th{font-weight:600;color:var(--ink2);font-size:13px}
td.n{text-align:right;font-variant-numeric:tabular-nums}
.heat td.h{text-align:center;font-variant-numeric:tabular-nums;font-weight:600;border-radius:6px;border:2px solid var(--card)}
.stack{display:flex;height:14px;border-radius:4px;overflow:hidden;gap:2px}
.stack div{height:14px}
.tag{font-size:12px;padding:1px 7px;border-radius:99px;background:var(--chip);color:var(--ink2);white-space:nowrap}
.tag.tu{background:var(--s1);color:#fff}.tag.conc{background:var(--s2);color:#fff}
.quote{border-left:3px solid var(--base);padding:4px 0 4px 12px;margin:0 0 10px}
.quote small{display:block;color:var(--mute);font-size:12px}
.tono-negativo{border-left-color:var(--bad)}.tono-positivo{border-left-color:var(--good)}
.azione{border:1px solid var(--ring);border-radius:12px;padding:14px 16px;margin:0 0 10px}
.azione h3{margin:0 0 4px;font-size:16px}.azione p{margin:0;color:var(--ink2)}
.dots{font-size:15px;letter-spacing:1px;white-space:nowrap}
.dots .m{color:var(--s1)}.dots .c{color:var(--s2)}.dots .o{color:var(--base)}
details{margin:6px 0}summary{cursor:pointer;color:var(--ink2);font-size:13px}
.ans{white-space:pre-wrap;font-size:13px;background:var(--bg);border-radius:8px;padding:10px;margin:6px 0;max-height:320px;overflow:auto}
.limiti li{margin:0 0 8px}
.delta-su{color:var(--good)}.delta-giu{color:var(--bad)}
.scroll{overflow-x:auto}
footer{color:var(--mute);font-size:13px;margin-top:24px}
a{color:var(--s1)}
@media (max-width:560px){section{padding:18px 14px}.row{grid-template-columns:90px 1fr 46px}header h1{font-size:23px}}
"""


def _pct(v):
    return f"{v:.0f}%"


def barra(lab, v, colore, titolo="", valore=None, tag=""):
    v = max(0.0, min(100.0, v))
    tt = e(titolo or f"{lab}: {_pct(v)}")
    fill = (f'<div class="fill" style="width:{v:.1f}%;background:{colore}"></div>' if v > 0 else "")
    return (f'<div class="row" title="{tt}"><div class="lab"><span class="nm">{e(lab)}</span>{tag}</div>'
            f'<div class="track">{fill}</div>'
            f'<div class="val">{e(valore if valore is not None else _pct(v))}</div></div>')


def _sfondo_seq(v):
    """Scala sequenziale a un colore (blu chiaro → blu scuro) per la tabella a caldo."""
    passi = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
    i = min(len(passi) - 1, int(v / 100 * (len(passi) - 1) + 0.5))
    return passi[i], ("#0b0b0b" if i <= 2 else "#ffffff")


def _pulisci_testo(t):
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t or "")
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"\[(\d+)\]", "", t)
    return t.strip()


def _punti(cella, n_rip):
    """●  nominato · ◆ solo linkato · ○ assente — una icona per ripetizione."""
    m, c, n = cella["m"], cella["c"], cella["n"]
    if not n:
        return '<span class="small">—</span>'
    s = '<span class="m">●</span>' * m
    solo_c = max(0, min(n - m, c))
    s += '<span class="c">◆</span>' * solo_c
    s += '<span class="o">○</span>' * (n - m - solo_c)
    return f'<span class="dots" title="nominato {m} volte su {n}, linkato {c} volte su {n}">{s}</span>'


def _data_it(s):
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:  # noqa: BLE001
        return s


def genera(A, p, percorso, data_misura):
    data_misura = _data_it(data_misura)
    piatt = A["piattaforme"]
    out = [f"<!doctype html><html lang='it'><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>Visibilità AI · {e(A['brand'])}</title><style>{CSS}</style></head><body><div class='wrap'>"]

    modelli = " · ".join(f"{P.NOMI[x]} ({e(str(A['modelli'].get(x, '')))})" for x in piatt)
    out.append(f"<header><h1>Come gli assistenti AI parlano di {e(A['brand'])}</h1>"
               f"<p>{e(A['dominio'])} · misura del {e(data_misura)} · {A['n_dom_gen'] + A['n_dom_bra']} domande × "
               f"{A['ripetizioni']} ripetizioni · {A['n_risposte']} risposte lette</p>"
               f"<p class='small'>Modelli: {modelli}</p></header>")

    voci_nav = [("sintesi", "In breve"), ("piattaforme", "Piattaforme"), ("percorso", "Percorso del cliente"),
                ("concorrenti", "Concorrenti"), ("fonti", "Fonti"), ("pagine", "Le tue pagine"),
                ("stabilita", "Stabilità"), ("reputazione", "Cosa dicono di te"), ("assenze", "Dove non ti nominano"),
                ("azioni", "Cosa fare"), ("domande", "Tutte le domande"), ("limiti", "Limiti")]
    out.append("<nav>" + "".join(f"<a href='#{a}'>{e(b)}</a>" for a, b in voci_nav) + "</nav>")

    if not A["per_p"]:
        out.append("<section><h2>Nessuna risposta</h2><p class='lead'>La misura non ha raccolto risposte valide. "
                   "Controlla le chiavi API e rilancia il kit.</p></section></div></body></html>")
        percorso.write_text("".join(out), encoding="utf-8")
        return

    # ── 1. In breve ───────────────────────────────────────────────────────
    out.append("<section id='sintesi' class='sintesi'><h2>In breve</h2>")
    out.append("".join(f"<p>{e(s)}</p>" for s in A["sintesi"]))
    out.append("<div class='cards'>")
    for v in A["per_p"]:
        lo, hi = v["menz_ci"]
        out.append(
            f"<div class='card'><h3>{e(v['nome'])}</h3>"
            f"<div class='kpi'><b>{_pct(v['menz'])}</b><span>ti nomina</span></div>"
            f"<div class='small'>{v['menz_k']} risposte su {v['n']} · probabilmente fra {lo:.0f}% e {hi:.0f}%</div>"
            f"<div class='kpi' style='margin-top:10px'><b>{_pct(v['cit'])}</b><span>linka il tuo sito</span></div>"
            f"<div class='small'>{v['cit_k']} risposte su {v['n']}</div>"
            f"<div class='small' style='margin-top:10px'>Almeno una volta in {v['almeno']} domande su {v['domande']}</div>"
            "</div>")
    out.append("</div>")
    cf = A.get("confronto")
    if cf and cf.get("attuale"):
        righe = []
        for x in piatt:
            if x in cf["prima"] and x in cf["attuale"]:
                (m0, c0), (m1, c1) = cf["prima"][x], cf["attuale"][x]
                dm = m1 - m0
                cls = "delta-su" if dm > 0 else ("delta-giu" if dm < 0 else "")
                nota = "probabilmente casuale" if abs(dm) < 10 else "variazione marcata"
                righe.append(f"<tr><td>{P.NOMI[x]}</td><td class='n'>{_pct(m0)} → {_pct(m1)}</td>"
                             f"<td class='n {cls}'>{dm:+.0f} punti</td><td class='small'>{nota}</td></tr>")
        if righe:
            out.append(f"<h3 style='margin:20px 0 6px;font-size:16px'>Rispetto alla misura del {e(_data_it(cf['data']))}</h3>"
                       f"<p class='small'>Solo sulle domande generiche presenti in entrambe le misure. Con pochi dati, "
                       f"spostamenti sotto i 10 punti sono quasi sempre normali oscillazioni.</p>"
                       f"<div class='scroll'><table><tr><th>Piattaforma</th><th>Ti nomina</th><th>Differenza</th><th></th></tr>"
                       + "".join(righe) + "</table></div>")
    out.append("</section>")

    # ── 2. per piattaforma ────────────────────────────────────────────────
    out.append("<section id='piattaforme'><h2>Nominato e linkato, piattaforma per piattaforma</h2>"
               "<p class='lead'>Sono due cose diverse. <b>Nominato</b> vuol dire che il nome compare nel testo della "
               "risposta. <b>Linkato</b> vuol dire che il tuo sito è fra le fonti cliccabili. Essere linkati porta "
               "visite; essere nominati costruisce notorietà. Contano solo le domande che non fanno il tuo nome.</p>"
               "<div class='legend'><span><i style='background:var(--s1)'></i>Ti nomina</span>"
               "<span><i style='background:var(--s2)'></i>Linka il tuo sito</span></div>")
    for v in A["per_p"]:
        out.append(f"<div class='grp'><h4>{e(v['nome'])}</h4>"
                   + barra("Ti nomina", v["menz"], "var(--s1)", f"{v['nome']}: nominato in {v['menz_k']} risposte su {v['n']}")
                   + barra("Linka il sito", v["cit"], "var(--s2)", f"{v['nome']}: linkato in {v['cit_k']} risposte su {v['n']}")
                   + "</div>")
    extra = []
    for v in A["per_p"]:
        if v["primo"] is not None:
            extra.append(f"Su {v['nome']}, quando ti nomina insieme ai concorrenti, sei il primo nome nel {_pct(v['primo'])} dei casi.")
        if v["solo_fonte"]:
            extra.append(f"Su {v['nome']}, in {v['solo_fonte']} risposte il sito è linkato ma il nome non compare nel testo.")
    if extra:
        out.append("<p class='small'>" + "<br>".join(e(x) for x in extra) + "</p>")
    out.append("</section>")

    # ── 3. percorso del cliente ───────────────────────────────────────────
    out.append("<section id='percorso'><h2>In quali momenti del percorso del cliente ci sei</h2>"
               "<p class='lead'>Le domande sono divise per fase: da chi ha appena un bisogno a chi è pronto a comprare. "
               "Il numero è la quota di risposte che ti nominano. Più il colore è scuro, più sei presente.</p>"
               "<div class='scroll'><table class='heat'><tr><th>Fase</th>"
               + "".join(f"<th style='text-align:center'>{P.NOMI[x]}</th>" for x in piatt) + "</tr>")
    for f in A["fasi"]:
        celle = ""
        for x in piatt:
            v, n = f["valori"].get(x, (0, 0))
            if not n:
                celle += "<td class='h small'>—</td>"
                continue
            bg, fg = _sfondo_seq(v)
            celle += (f"<td class='h' style='background:{bg};color:{fg}' "
                      f"title='{e(f['nome'])} su {P.NOMI[x]}: {_pct(v)} di {n} risposte'>{_pct(v)}</td>")
        out.append(f"<tr><td><b>{e(f['nome'])}</b><br><span class='small'>{e(SPIEGAZIONE_FASI[f['fase']])} · "
                   f"{f['domande']} domande</span></td>{celle}</tr>")
    out.append("</table></div></section>")

    # ── 4. concorrenti ────────────────────────────────────────────────────
    out.append("<section id='concorrenti'><h2>Tu e i concorrenti</h2>")
    if A["concorrenti"]:
        out.append("<p class='lead'>Quante risposte nominano te e quante nominano ciascun concorrente che ci hai "
                   "indicato, sulle stesse domande. Un grafico per piattaforma, perché ognuna ragiona a modo suo.</p><div class='multi'>")
        for x in piatt:
            out.append(f"<div class='grp'><h4>{P.NOMI[x]}</h4>")
            for nome, v, tu in A["sov"][x]:
                out.append(barra(nome, v, "var(--s1)" if tu else "var(--mute)",
                                 f"{nome} su {P.NOMI[x]}: {_pct(v)} delle risposte",
                                 tag="<span class='tag tu'>tu</span>" if tu else ""))
            out.append("</div>")
        out.append("</div>")
    else:
        out.append("<p class='lead'>Non hai indicato concorrenti. Per scoprire chi viene proposto al posto tuo, "
                   "guarda le fonti più citate qui sotto e la colonna 'chi compare' nella tabella delle domande. "
                   "Alla prossima misura puoi aggiungerli in progetto.json.</p>")
    out.append("</section>")

    # ── 5. fonti ──────────────────────────────────────────────────────────
    nf = A["nostra_fonte"]
    pos = (f"Il tuo sito è al <b>{nf['posto']}° posto</b> fra le fonti, linkato in {nf['k']} risposte."
           if nf.get("posto") else "Il tuo sito non compare mai fra le fonti delle domande generiche.")
    out.append("<section id='fonti'><h2>Da dove prendono le informazioni</h2>"
               "<p class='lead'>I siti più usati come fonte nelle risposte alle domande generiche, su tutte le "
               "piattaforme. Sono i posti dove conviene essere presenti: chi sta qui viene raccontato dagli assistenti. "
               f"{pos}</p><div class='bars wide'>")
    for f in A["fonti"]:
        tag = ("<span class='tag tu'>tu</span>" if f["tipo"] == "tu" else
               "<span class='tag conc'>concorrente</span>" if f["tipo"] == "concorrente" else "")
        dett = ", ".join(f"{P.NOMI[x]} {k}" for x, k in f["per_p"].items() if k)
        col = "var(--s1)" if f["tipo"] == "tu" else ("var(--s2)" if f["tipo"] == "concorrente" else "var(--mute)")
        out.append(barra(f["dominio"], f["pct"], col, f"{f['dominio']}: {f['k']} risposte ({dett})", tag=tag))
    out.append("</div><p class='small'>Percentuale sul totale delle risposte alle domande generiche "
               f"({sum(v['n'] for v in A['per_p'])}). Passa sopra una barra per vedere il dettaglio per piattaforma.</p></section>")

    # ── 6. pagine ─────────────────────────────────────────────────────────
    out.append("<section id='pagine'><h2>Le tue pagine che vengono linkate</h2>"
               "<p class='lead'>Quali pagine del tuo sito finiscono fra le fonti, su tutte le domande (anche quelle "
               "col tuo nome). Dicono quali contenuti gli assistenti considerano utili.</p>")
    if A["pagine"]:
        out.append("<div class='scroll'><table><tr><th>Pagina</th>" + "".join(f"<th class='n'>{P.NOMI[x]}</th>" for x in piatt)
                   + "<th class='n'>Totale</th></tr>")
        for v in A["pagine"][:20]:
            out.append(f"<tr><td><a href='{e(v['url'])}' target='_blank' rel='noopener'>{e(v['percorso'][:90])}</a></td>"
                       + "".join(f"<td class='n'>{v['per_p'].get(x, 0) or ''}</td>" for x in piatt)
                       + f"<td class='n'><b>{v['tot']}</b></td></tr>")
        out.append("</table></div>")
    else:
        out.append("<p>Nessuna pagina del tuo sito è stata linkata.</p>")
    if A["senza_url"]:
        out.append("<p class='small'>In " + ", ".join(f"{k} risposte di {P.NOMI[x]}" for x, k in A["senza_url"].items())
                   + " il sito è fra le fonti ma la pagina esatta non è ricostruibile (la piattaforma ha restituito solo il dominio).</p>")
    out.append("</section>")

    # ── 7. stabilità ──────────────────────────────────────────────────────
    out.append("<section id='stabilita'><h2>Quanto sei stabile</h2>"
               f"<p class='lead'>Ogni domanda è stata ripetuta {A['ripetizioni']} volte, perché gli assistenti non "
               "rispondono sempre allo stesso modo. Qui vedi in quante domande compari <b>sempre</b>, <b>a volte</b> "
               "o <b>mai</b>. 'A volte' significa che sei in bilico: è lì che un miglioramento si vede prima.</p>"
               "<div class='legend'><span><i style='background:var(--st-sempre)'></i>Sempre</span>"
               "<span><i style='background:var(--st-avolte)'></i>A volte</span>"
               "<span><i style='background:var(--st-mai)'></i>Mai</span></div><div class='bars'>")
    for x in piatt:
        s = A["stab"][x]
        tot = sum(s.values()) or 1
        seg = "".join(f"<div style='width:{100 * s[k] / tot:.1f}%;background:var(--st-{k.replace(' ', '')})' "
                      f"title='{k}: {s[k]} domande su {tot}'></div>" for k in ("sempre", "a volte", "mai") if s[k])
        out.append(f"<div class='row'><div class='lab'>{P.NOMI[x]}</div><div class='stack'>{seg}</div>"
                   f"<div class='val small'>{s['sempre']}·{s['a volte']}·{s['mai']}</div></div>")
    out.append("</div><p class='small'>I tre numeri a destra: domande sempre · a volte · mai.</p></section>")

    # ── 8. reputazione ────────────────────────────────────────────────────
    tot_m = sum(A["ruoli"].values())
    out.append("<section id='reputazione'><h2>Cosa dicono di te</h2>")
    if tot_m:
        out.append("<p class='lead'>In tutte le risposte che ti nominano: vieni consigliato o solo elencato? "
                   "E con che tono?</p><div class='bars'>")
        for r, spieg in (("consigliato", "indicato come scelta da fare"), ("tra le opzioni", "in un elenco di alternative"),
                         ("citato di passaggio", "nominato come esempio o dettaglio"), ("sconsigliato", "da evitare")):
            k = A["ruoli"].get(r, 0)
            out.append(barra(r.capitalize(), 100 * k / tot_m, "var(--s1)" if r != "sconsigliato" else "var(--bad)",
                             f"{r}: {k} risposte su {tot_m} ({spieg})", valore=str(k)))
        out.append("</div>")
        toni = A["toni"]
        out.append(f"<p class='small' style='margin-top:12px'>Tono: {toni.get('positivo', 0)} positive · "
                   f"{toni.get('neutro', 0)} neutre · {toni.get('negativo', 0)} negative, su {tot_m} risposte che ti nominano.</p>")
        if A["frasi"]:
            out.append("<h3 style='font-size:16px;margin:18px 0 10px'>Le frasi su di te, in sintesi</h3>"
                       "<p class='small'>Controlla che siano corrette: un'informazione sbagliata (prezzo, servizio, "
                       "luogo) si ripete in tutte le risposte che la usano.</p>")
            for q in A["frasi"]:
                out.append(f"<div class='quote tono-{e(q['tono'])}'>{e(q['testo'])}"
                           f"<small>{P.NOMI[q['p']]} · alla domanda: {e(q['domanda'][:110])}</small></div>")
        if "euristica" in A["metodo_giudizio"] and len(A["metodo_giudizio"]) == 1:
            out.append("<p class='small'>Il giudizio su consigliato/tono è stato stimato con regole semplici, senza "
                       "un'AI di lettura (serve una chiave ChatGPT o Gemini): prendilo come indicativo.</p>")
    else:
        out.append("<p class='lead'>Nessuna risposta ti nomina, quindi non c'è nulla da valutare sul tono.</p>")
    if A["brand_p"]:
        out.append("<h3 style='font-size:16px;margin:18px 0 8px'>Quando ti cercano per nome</h3>"
                   f"<p class='small'>Nelle {A['n_dom_bra']} domande che contengono il tuo nome, quante volte il tuo "
                   "sito è fra le fonti? Se è basso, le informazioni su di te arrivano da altri siti.</p><div class='bars'>")
        for b in A["brand_p"]:
            out.append(barra(b["nome"], b["cit"], "var(--s2)", f"{b['nome']}: sito linkato in {b['cit_k']} risposte su {b['n']}"))
        out.append("</div>")
    out.append("</section>")

    # ── 9. assenze ────────────────────────────────────────────────────────
    out.append("<section id='assenze'><h2>Le domande dove non ti nominano mai</h2>")
    if A["gap"]:
        out.append("<p class='lead'>Nessuna piattaforma ha fatto il tuo nome, in nessuna ripetizione. Accanto, chi "
                   "viene nominato o usato come fonte al posto tuo. Se il tuo sito è comunque fra le fonti, lo trovi "
                   "segnalato: lì il contenuto c'è, manca il riconoscimento del nome.</p><div class='scroll'><table>"
                   "<tr><th>Domanda</th><th>Fase</th><th>Chi compare</th></tr>")
        for g in A["gap"]:
            pezzi = []
            if g["concorrenti"]:
                pezzi.append(e(", ".join(g["concorrenti"])))
            if g["fonti"]:
                pezzi.append("fonti: " + e(", ".join(g["fonti"][:3])))
            if g["linkato"]:
                pezzi.append(f"<span class='tag tu'>tu</span> linkato {g['linkato']} volte, senza nome")
            out.append(f"<tr><td>{e(g['domanda'])}</td><td class='small'>{e(FASI[g['fase']])}</td>"
                       f"<td class='small'>{'<br>'.join(pezzi)}</td></tr>")
        out.append("</table></div>")
    else:
        out.append("<p class='lead'>Ottimo: in ogni domanda generica almeno una piattaforma ti nomina almeno una volta.</p>")
    out.append("</section>")

    # ── 10. azioni ────────────────────────────────────────────────────────
    out.append("<section id='azioni'><h2>Cosa fare adesso</h2><p class='lead'>Suggerimenti ricavati dai numeri qui "
               "sopra, in ordine di importanza. Sono un punto di partenza, non una ricetta.</p>")
    for t, d in A["azioni"] or [("Continua a misurare", "Ripeti la misura fra 4-8 settimane con le stesse domande "
                                 "per vedere se la tendenza si conferma.")]:
        out.append(f"<div class='azione'><h3>{e(t)}</h3><p>{e(d)}</p></div>")
    out.append("<div class='azione'><h3>Ripeti la misura</h3><p>Rilancia il kit fra 4-8 settimane e scegli "
               "'nuova misura con le stesse domande': la dashboard ti mostrerà cosa è cambiato. Tenere le stesse "
               "domande è ciò che rende il confronto affidabile.</p></div></section>")

    # ── 11. tutte le domande ──────────────────────────────────────────────
    out.append("<section id='domande'><h2>Tutte le domande, una per una</h2>"
               f"<p class='lead'>Un simbolo per ogni ripetizione: <span class='dots'><span class='m'>●</span></span> "
               "ti nomina · <span class='dots'><span class='c'>◆</span></span> linka il sito senza nominarti · "
               "<span class='dots'><span class='o'>○</span></span> assente. Apri 'leggi le risposte' per vedere "
               "il testo completo.</p><div class='scroll'><table><tr><th>Domanda</th>"
               + "".join(f"<th>{P.NOMI[x]}</th>" for x in piatt) + "</tr>")
    fase_corr = None
    for r in A["righe"]:
        if r["fase"] != fase_corr:
            fase_corr = r["fase"]
            out.append(f"<tr><td colspan='{1 + len(piatt)}' style='padding-top:16px'><b>{e(FASI[fase_corr])}</b> "
                       f"<span class='small'>— {e(SPIEGAZIONE_FASI[fase_corr])}</span></td></tr>")
        risp = "".join(
            f"<div class='small' style='margin-top:8px'><b>{P.NOMI[a['p']]} · ripetizione {a['n']}</b> · "
            f"{'ti nomina' if a['m'] else 'non ti nomina'} · {'linka il sito' if a['c'] else 'non linka il sito'}</div>"
            f"<div class='ans'>{e(_pulisci_testo(a['testo']))}"
            + (f"\n\nFonti: {e(' · '.join(a['fonti']))}" if a["fonti"] else "") + "</div>"
            for a in r["risposte"])
        out.append(f"<tr><td>{e(r['domanda'])}<details><summary>leggi le risposte</summary>{risp}</details></td>"
                   + "".join(f"<td>{_punti(r['celle'][x], A['ripetizioni'])}</td>" for x in piatt) + "</tr>")
    out.append("</table></div></section>")

    # ── 12. limiti ────────────────────────────────────────────────────────
    out.append("<section id='limiti' class='limiti'><h2>I limiti di questa analisi</h2>"
               "<p class='lead'>Leggere i numeri senza questi limiti porta a conclusioni sbagliate.</p><ul>")
    for li in limiti(A, p):
        out.append(f"<li>{li}</li>")
    out.append("</ul></section>")

    out.append(f"<footer>Generato dal kit Visibilità AI il {datetime.now():%d/%m/%Y alle %H:%M}. "
               f"Costo delle risposte di questa misura: circa ${A['costo_risposte']:.2f}.</footer>")
    out.append("</div></body></html>")
    percorso.write_text("".join(out), encoding="utf-8")


def limiti(A, p):
    n = A["n_dom_gen"]
    L = [
        "<b>Non è quello che vede ogni persona.</b> Le domande passano dalle API ufficiali, senza account, "
        "cronologia o memoria. Chi usa ChatGPT o Gemini da loggato può ricevere risposte diverse, "
        "personalizzate sulle sue conversazioni precedenti.",
        f"<b>I modelli non sono identici alle app.</b> Le API usano modelli scelti dal kit "
        f"({', '.join(f'{P.NOMI[x]}: {e(str(A['modelli'].get(x, '')))}' for x in A['piattaforme'])}), "
        "che possono differire da quelli dell'app gratuita o a pagamento. Il confronto vale soprattutto "
        "fra una misura e l'altra, con gli stessi modelli.",
        f"<b>Pochi dati, margini larghi.</b> Le percentuali poggiano su {n} domande generiche. Il margine indicato "
        "nelle schede ('probabilmente fra… e…') dice quanto il numero può oscillare: differenze piccole fra "
        "piattaforme o fra due misure spesso non sono reali.",
        "<b>Le risposte cambiano nel tempo.</b> Gli assistenti si aggiornano spesso e le loro risposte variano "
        "anche a parità di domanda: la misura è una fotografia di questi giorni, non un dato fisso.",
        "<b>Le domande sono un campione.</b> Rappresentano le ricerche dei tuoi clienti, ma non le contengono tutte. "
        "Non sappiamo quante persone fanno davvero ciascuna domanda: gli assistenti non pubblicano questi volumi.",
        "<b>Il nome si riconosce dal testo.</b> Se il tuo brand ha un nome comune o simile ad altro, qualche "
        "menzione può essere falsa; se viene scritto in modo molto diverso, qualcuna può sfuggire."
        + (f" In questa misura l'AI di lettura ha scartato {A['falsi_positivi']} falsi positivi." if A["falsi_positivi"] else ""),
        "<b>'Consigliato' e il tono sono una lettura automatica.</b> Sono utili per orientarsi; per decisioni "
        "importanti leggi le risposte nella tabella delle domande.",
        "<b>Correttezza delle informazioni.</b> Il kit mostra cosa dicono di te, ma solo tu puoi verificare se è vero.",
        "<b>Non misura il traffico.</b> Qui si misura la presenza nelle risposte. Le visite che arrivano davvero "
        "dagli assistenti si leggono in Google Analytics (sorgenti come chatgpt.com, perplexity.ai, gemini.google.com).",
    ]
    if "gemini" in A["piattaforme"]:
        L.append("<b>Gemini</b> usa la Ricerca Google per le fonti; il kit segue i suoi link di reindirizzamento per "
                 "risalire alla pagina. Se il reindirizzamento non risponde resta solo il dominio. Le risposte "
                 "dell'API non coincidono con le AI Overview di Google Search, che sono un prodotto diverso.")
    mancanti = [P.NOMI[x] for x in P.ORDINE if x not in A["piattaforme"]]
    if mancanti:
        L.append(f"<b>Piattaforme non misurate:</b> {', '.join(mancanti)} (nessuna chiave API inserita). "
                 "I risultati non dicono nulla su come ti vedono lì.")
    return L
