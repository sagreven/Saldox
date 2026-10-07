"""Markdown → HTML in Saldox-huisstijl (overgenomen uit het rapport Run 4258).

Figuren worden in de markdown aangegeven met een marker `<!-- FIG:naam -->` en
vervangen door de SVG-figuur uit het dict `figuren`.
"""
import base64
import html
import re
from pathlib import Path

import markdown

HERE = Path(__file__).parent
NUM_RE = re.compile(r"^(<strong>)?(−|-|\+)?(ca\. )?€|^(<strong>)?\d")


def style_tables(h: str) -> str:
    def one(m):
        rows = re.findall(r"<tr>(.*?)</tr>", m.group(0), re.S)
        cells = [re.findall(r"<t([hd])>(.*?)</t[hd]>", r, re.S) for r in rows]
        head = [c[1] for c in cells[0]]
        numeric = []
        for ci in range(len(head)):
            body = [r[ci][1].strip() for r in cells[1:] if ci < len(r) and r[ci][1].strip()]
            short = sum(len(re.sub(r"<[^>]+>", "", b_)) for b_ in body) / max(len(body), 1) <= 32
            numeric.append(ci > 0 and body and short and sum(bool(NUM_RE.search(b)) for b in body) / len(body) >= 0.6)
        new_rows = []
        for ri, r in enumerate(cells):
            filled = [c[1].strip() for c in r if c[1].strip()]
            total = ri > 0 and filled and all(v.startswith("<strong>") for v in filled)
            tds = []
            for ci, (kind, v) in enumerate(r):
                if ri > 0 and head[ci] == "Status" and v.strip():
                    key = "stelpost" if "Stelpost" in v else "offerte" if ("Offerte" in v or "Opgegeven" in v) else "vast"
                    v = f'<span class="pill {key}">{v}</span>'
                c = ' class="num"' if numeric[ci] else ""
                tds.append(f"<t{kind}{c}>{v}</t{kind}>")
            rc = ' class="total"' if total else ""
            new_rows.append(f"<tr{rc}>{''.join(tds)}</tr>")
        return (f'<div class="table-wrap"><table><thead>{new_rows[0]}</thead>'
                f'<tbody>{"".join(new_rows[1:])}</tbody></table></div>')
    return re.sub(r"<table>.*?</table>", one, h, flags=re.S)


def style_checklists(h: str) -> str:
    h = re.sub(r"<li>(\s*<p>)?\[ \] ", r'<li class="todo">\1', h)
    return re.sub(r"<ul>(\s*<li class=\"todo\">)", r'<ul class="checklist">\1', h)


def md(text: str) -> str:
    h = markdown.markdown(text, extensions=["tables", "sane_lists"])
    h = h.replace('<a href=', '<a target="_blank" rel="noopener" href=')
    return style_checklists(style_tables(h))


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "")).strip("-")


def summary_cards(body_html: str) -> str:
    def one(m):
        items = re.findall(r"<li><strong>(.*?)</strong>(.*?)</li>", m.group(0), re.S)
        cards = "".join(f'<div class="card"><h3>{t.rstrip(":")}</h3><p>{d.strip()}</p></div>' for t, d in items)
        return f'<div class="cards">{cards}</div>'
    return re.sub(r"<ul>.*?</ul>", one, body_html, count=1, flags=re.S)


def bouw(src: str, headlines: dict, figuren: dict, kpis: list, chip: str, out: Path):
    """kpis: lijst (waarde, label, accent)."""
    head, *parts = re.split(r"^## ", src, flags=re.M)
    title = re.search(r"^# (.+)$", head, re.M).group(1)
    meta = head.split("\n", 2)[2].strip()
    sections, toc = [], []
    for n, part in enumerate(parts, 1):
        name, body = part.split("\n", 1)
        name = name.strip()
        sid = slug(name)
        body_html = md(body)
        lede_end = body_html.index("</p>") + 4
        lede, body_html = body_html[:lede_end].replace("<p>", '<p class="lede">', 1), body_html[lede_end:]
        for key, fig in figuren.items():
            body_html = body_html.replace(f"<!-- FIG:{key} -->", fig)
        assert "<!--" not in body_html, f"onverwerkte marker in {name}: {re.findall(r'<!--.*?-->', body_html)}"
        if n == 1:
            body_html = summary_cards(body_html)
        toc.append(f'<li><a href="#{sid}"><span class="toc-n">{n:02d}</span>{html.escape(name)}</a></li>')
        sections.append(
            f'<section id="{sid}" class="section{" summary" if n == 1 else ""}">'
            f'<header class="sec-head"><div class="eyebrow"><span class="dot"></span>{n:02d} · {html.escape(name)}</div>'
            f'<h2>{html.escape(headlines[name])}</h2>{lede}</header>{body_html}</section>')
        if n == 1:
            sections.append('<nav class="toc" aria-label="Inhoud"><div class="eyebrow"><span class="dot"></span>Inhoud</div>'
                            '<ol>%TOC%</ol></nav>')
    page = (HERE / "template.html").read_text(encoding="utf-8")
    font_b64 = base64.b64encode((HERE / "assets/inter-latin-var.woff2").read_bytes()).decode()
    mark = (HERE / "assets/saldox-mark.svg").read_text(encoding="utf-8")
    mark = re.sub(r"<!--.*?-->", "", mark, flags=re.S)
    mark = mark.replace('role="img" aria-label="Saldox"', 'aria-hidden="true" class="mark"').replace("<title>Saldox</title>", "")
    accent = title.split(": ")[-1] if ": " in title else title.split(", ")[-1]
    h1 = html.escape(title).replace(html.escape(accent), f'<span class="sun">{html.escape(accent)}</span>', 1)
    kpi_html = "\n".join(f'      <div class="kpi{" accent" if acc else ""}"><span class="v">{html.escape(v)}</span>'
                         f'<span class="l">{html.escape(l)}</span></div>' for v, l, acc in kpis)
    repl = {"%TITLE%": html.escape(title), "%H1%": h1, "%META%": html.escape(meta), "%FONT%": font_b64,
            "%MARK%": mark, "%CHIP%": html.escape(chip), "%KPIS%": kpi_html,
            "%SECTIONS%": "\n".join(sections).replace("%TOC%", "".join(toc))}
    for k, v in repl.items():
        page = page.replace(k, v)
    out.write_text(page, encoding="utf-8")
    return title
