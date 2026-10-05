#!/usr/bin/env python3
"""Bouwt rapport.html in Saldox-huisstijl uit energieplan-run-4258.md.

Tekst en tabellen komen letterlijk uit de markdown. Toegevoegd worden alleen:
kopregels in Saldox-toon (boven de originele sectietitel), de KPI-tegels in de
kop (cijfers uit de samenvatting), Grafiek 1 en Diagram 2 (data uit CLAUDE.md).

Gebruik:  python3 build.py && node render_pdf.js && python3 check.py
"""
import base64
import html
import re
from pathlib import Path

import markdown

import charts

HERE = Path(__file__).parent
SRC = HERE / "energieplan-run-4258.md"
OUT = HERE / "rapport.html"

# ── Toon: 'u' zoals op saldox.nl, in plaats van 'jullie'. Elke vervanging moet
#    precies één keer voorkomen, zodat een gewijzigde bron opvalt.
TONE = [
    ("de software maken jullie zelf", "de software maakt u zelf"),
    ("De software (EMS en app) bouwen jullie parallel", "De software (EMS en app) bouwt u parallel"),
    ("de huurcontracten regelen jullie in de voorbereiding", "de huurcontracten regelt u in de voorbereiding"),
]

# ── Per sectie: kopregel in Saldox-toon. De originele titel wordt het label erboven.
HEADLINES = {
    "Samenvatting": "Wat het pakket kost, en wat het u oplevert.",
    "Begroting (excl. btw)": "Elke post op een rij.",
    "Terugverdientijd per onderdeel": "Zon en batterij doen het zware werk.",
    "Scenario's terugverdientijd": "Wat er na de jaarlijkse kosten overblijft.",
    "Terugverdientijd per maatregel": "Niet elke maatregel hoeft zich terug te verdienen.",
    "Verdienmodel verhuurder: wie betaalt, wie bespaart": "Wie betaalt de rekening, wie houdt de besparing?",
    "Waarom de airco's geen terugverdientijd hebben": "Vervangen moet. De vraag is alleen: welke vervanging.",
    "Inkoopprijzen via een relatie": "Het inkoopvoordeel gaat volledig naar de verhuurder.",
    "Laadplan en tariefopties voor de klant": "Twee laadpalen, drie tarieven.",
    "Netaansluiting 3x25 A en meten per unit": "Krap in de winter, haalbaar met de batterij.",
    "EMS: slim verwarmen en koelen": "Warm als u er bent, zuinig als u weg bent.",
    "App, aanwezigheid en netwerk (UniFi)": "Eén app voor temperatuur, stroom en internet.",
    "Windturbine": "Eerst meten, dan pas bouwen.",
    "Planning": "Van opdracht tot oplevering.",
    "Aannames, risico's en openstaande punten": "Wat nog bevestigd moet worden.",
    "Begrippenlijst": "Begrippen in gewone taal.",
}

# ── Grafiek 1 (CLAUDE.md)
INVESTERING = 48987.80
SCENARIOS = [  # (naam, netto per jaar, terugverdiend na, nadruk)
    ("Pessimistisch", 3751, "13,1", False),
    ("Normaal", 6663, "7,4", True),
    ("Optimistisch", 9743, "5,0", False),
]

# ── Diagram 2 (CLAUDE.md)
PLANNING = [  # (fase, periode, inhoud, start-week, eind-week)
    ("Voorbereiding", "Week 1 tot 4", "Dakinspectie, Enexis, offertes, btw en EIA, huurcontracten", 1, 4),
    ("Bestellen en leveren", "Week 5 tot 8", "Bestellen en leveren, software EMS en app bouwen", 5, 8),
    ("Installatie energie", "Week 9 tot 11", "Panelen, omvormer, batterij, laadpalen, meters, sensoren", 9, 11),
    ("Airco vervangen", "Week 12 tot 13", "Per verdieping, inclusief verticaal transport en afvoer", 12, 13),
    ("Oplevering", "Week 14", "Inspectie installatie, test EMS en app, Enexis-meter", 14, 14),
]
TURBINE = ("Windturbine (optie, apart spoor)", "Maand 6 tot 12", "Alleen na positieve windmeting en vergunning", 6, 12)

# ── Extra grafieken: data letterlijk uit de tabellen in de markdown (check.py controleert dat)
MAATREGELEN = [  # Terugverdientijd per maatregel: investering
    ("Airco's", 23487.80), ("Zonnepanelen", 11300), ("Laadpalen", 4000), ("Batterij", 4000),
    ("Meten per unit", 3350), ("Smart control", 2100), ("Inspectie elektra", 750),
]
PAYBACK = [  # (maatregel, pess, normaal, opt) in jaren; None = niet / meer dan 25
    ("Zonnepanelen", 4.9, 4.4, 4.1), ("Smart control", 6.9, 3.0, 2.0), ("Laadpalen", 2.7, 1.7, 1.1),
    ("Batterij", None, 8.0, 3.7), ("Airco's", None, None, 18),
]
WATERVAL = [  # scenariotabel, kolom Normaal
    ("Zon", 3100, "plus"), ("Batterij", 1000, "plus"), ("Airco (stroom + gas)", 1710, "plus"),
    ("EMS", 670, "plus"), ("Bewegingssensoren", 320, "plus"), ("Laadpalen", 2773, "plus"),
    ("Bruto", 9573, "totaal"),
    ("Onderhoud airco's, F-gas", -1200, "min"), ("Onderhoud zon en batterij", -200, "min"),
    ("Verzekering", -300, "min"), ("Backoffice laadpalen", -360, "min"), ("Software", -300, "min"),
    ("Reservering vervanging", -550, "min"), ("Netto per jaar", 6663, "totaal"),
]
LAADPLAN = [  # (tarief en bezetting, marge stroom, ERE min, ERE max)
    ("€0,39 · 3 dagen", 1404, 780, 1014), ("€0,39 · 4 dagen", 1872, 1040, 1352),
    ("€0,49 · 3 dagen", 2184, 780, 1014), ("€0,49 · 4 dagen", 2912, 1040, 1352),
]
WERKDAG = {
    "Winter": {"vraag": [("Verbruik pand (incl. airco)", 170), ("Laadpalen", 50)],
               "aanbod": [("Net", 172), ("Batterij", 45), ("Zon", 10)]},
    "Zomer": {"vraag": [("Verbruik pand (incl. airco)", 130), ("Laadpalen", 50)],
              "aanbod": [("Net", 172), ("Batterij", 45), ("Zon", 70)]},
}


def inserts():
    """Per sectie: (anker, html). Anker 'lede' = na de eerste alinea, 'table:N' = na de N-de tabel (1-based)."""
    return {
        "Begroting (excl. btw)": [("lede", charts.begroting(MAATREGELEN, INVESTERING))],
        "Scenario's terugverdientijd": [("table:1", charts.waterval(WATERVAL))],
        "Terugverdientijd per maatregel": [("lede", charts.payback(PAYBACK, 7.4))],
        "Laadplan en tariefopties voor de klant": [("table:2", charts.laadplan(LAADPLAN, 4000))],
        "Netaansluiting 3x25 A en meten per unit": [("table:2", charts.werkdag(WERKDAG))],
        "EMS: slim verwarmen en koelen": [("table:1", charts.dagschema())],
    }


# ─────────────────────────────────────────────────────────────── markdown → html
NUM_RE = re.compile(r"^(<strong>)?(−|-)?(ca\. )?€|^(<strong>)?\d")


def style_tables(h: str) -> str:
    def one(m):
        t = m.group(0)
        rows = re.findall(r"<tr>(.*?)</tr>", t, re.S)
        cells = [re.findall(r"<t([hd])>(.*?)</t[hd]>", r, re.S) for r in rows]
        head = [c[1] for c in cells[0]]
        ncol = len(head)
        numeric = []
        for ci in range(ncol):
            body = [r[ci][1].strip() for r in cells[1:] if ci < len(r) and r[ci][1].strip()]
            numeric.append(ci > 0 and body and sum(bool(NUM_RE.search(b)) for b in body) / len(body) >= 0.6)
        new_rows = []
        for ri, r in enumerate(cells):
            vals = [c[1].strip() for c in r]
            filled = [v for v in vals if v]
            total = ri > 0 and filled and all(v.startswith("<strong>") for v in filled)
            tds = []
            for ci, (kind, v) in enumerate(r):
                cls = []
                if numeric[ci]:
                    cls.append("num")
                if ri > 0 and head[ci] == "Status" and v.strip():
                    key = "stelpost" if "Stelpost" in v else "offerte" if "Offerte" in v else "vast"
                    v = f'<span class="pill {key}">{v}</span>'
                c = f' class="{" ".join(cls)}"' if cls else ""
                tds.append(f"<t{kind}{c}>{v}</t{kind}>")
            rc = ' class="total"' if total else ""
            new_rows.append(f"<tr{rc}>{''.join(tds)}</tr>")
        thead = f"<thead>{new_rows[0]}</thead>"
        tbody = f"<tbody>{''.join(new_rows[1:])}</tbody>"
        return f'<div class="table-wrap"><table>{thead}{tbody}</table></div><!--TABLE-->'
    return re.sub(r"<table>.*?</table>", one, h, flags=re.S)


def style_checklists(h: str) -> str:
    h = re.sub(r"<li>(\s*<p>)?\[ \] ", r'<li class="todo">\1', h)
    return re.sub(r"<ul>(\s*<li class=\"todo\">)", r'<ul class="checklist">\1', h)


def md(text: str) -> str:
    h = markdown.markdown(text, extensions=["tables", "sane_lists"])
    h = h.replace('<a href=', '<a target="_blank" rel="noopener" href=')
    return style_checklists(style_tables(h))


def slug(s: str) -> str:
    s = s.lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def summary_cards(body_html: str) -> str:
    """De opsomming in de samenvatting als kaarten, tekst ongewijzigd."""
    def one(m):
        items = re.findall(r"<li><strong>(.*?)</strong>(.*?)</li>", m.group(0), re.S)
        cards = "".join(f'<div class="card"><h3>{t.rstrip(":")}</h3><p>{d.strip()}</p></div>' for t, d in items)
        return f'<div class="cards">{cards}</div>'
    return re.sub(r"<ul>.*?</ul>", one, body_html, count=1, flags=re.S)


def build():
    src = SRC.read_text(encoding="utf-8")
    for old, new in TONE:
        assert src.count(old) == 1, f"toonvervanging niet eenduidig: {old!r}"
        src = src.replace(old, new)

    head, *parts = re.split(r"^## ", src, flags=re.M)
    title = re.search(r"^# (.+)$", head, re.M).group(1)
    meta = head.split("\n", 2)[2].strip()  # "5 oktober 2026 · Sascha Greven"

    sections, toc = [], []
    ins = inserts()
    for n, part in enumerate(parts, 1):
        name, body = part.split("\n", 1)
        name = name.strip()
        sid = slug(name)
        body_html = md(body)
        lede_end = body_html.index("</p>") + 4
        lede, body_html = body_html[:lede_end].replace("<p>", '<p class="lede">', 1), body_html[lede_end:]
        body_html = body_html.replace("<!-- GRAFIEK: scenario-kasstroom. Zie CLAUDE.md, sectie 'Grafiek 1'. -->",
                                      charts.kasstroom(INVESTERING, SCENARIOS))
        body_html = body_html.replace("<!-- DIAGRAM: planning. Zie CLAUDE.md, sectie 'Diagram 2'. -->",
                                      charts.planning(PLANNING, TURBINE))
        for anchor, fig in ins.get(name, []):
            if anchor == "lede":
                i = 0
            else:
                n_ = int(anchor.split(":")[1])
                i = [m.end() for m in re.finditer("<!--TABLE-->", body_html)][n_ - 1]
            body_html = body_html[:i] + fig + body_html[i:]
        body_html = body_html.replace("<!--TABLE-->", "")
        assert "<!--" not in body_html, f"onverwerkte marker in {name}"
        if name == "Samenvatting":
            body_html = summary_cards(body_html)
        headline = HEADLINES[name]
        toc.append(f'<li><a href="#{sid}"><span class="toc-n">{n:02d}</span>{html.escape(name)}</a></li>')
        sections.append(
            f'<section id="{sid}" class="section{" summary" if n == 1 else ""}">'
            f'<header class="sec-head"><div class="eyebrow"><span class="dot"></span>{n:02d} · {html.escape(name)}</div>'
            f'<h2>{html.escape(headline)}</h2>{lede}</header>{body_html}</section>'
        )
        if n == 1:
            sections.append(
                '<nav class="toc" aria-label="Inhoud"><div class="eyebrow"><span class="dot"></span>Inhoud</div>'
                '<ol>%TOC%</ol></nav>'
            )

    page = TEMPLATE
    font_b64 = base64.b64encode((HERE / "assets/inter-latin-var.woff2").read_bytes()).decode()
    mark = (HERE / "assets/saldox-mark.svg").read_text(encoding="utf-8")
    mark = re.sub(r"<!--.*?-->", "", mark, flags=re.S)
    mark = mark.replace('role="img" aria-label="Saldox"', 'aria-hidden="true" class="mark"').replace("<title>Saldox</title>", "")
    plaats = title.split(", ")[-1]
    h1 = html.escape(title).replace(html.escape(plaats), f'<span class="sun">{html.escape(plaats)}</span>')
    repl = {
        "%TITLE%": html.escape(title),
        "%H1%": h1,
        "%META%": html.escape(meta),
        "%FONT%": font_b64,
        "%MARK%": mark,
        "%SECTIONS%": "\n".join(sections).replace("%TOC%", "".join(toc)),
    }
    for k, v in repl.items():
        page = page.replace(k, v)
    OUT.write_text(page, encoding="utf-8")
    print(f"geschreven: {OUT} ({OUT.stat().st_size // 1024} kB)")


TEMPLATE = (HERE / "template.html").read_text(encoding="utf-8")

if __name__ == "__main__":
    build()
