"""SVG-grafieken voor het energieplan. Alle data komt uit CLAUDE.md of uit de
tabellen in energieplan-run-4258.md; hier wordt niets nieuws berekend behalve
posities op de as.

Palet (gevalideerd met de dataviz-validator, light): groen #0e8a50, zon #e29a00,
blauw #5a78b5, roze #b84a62; kosten #d9480f. Zon haalt geen 3:1 contrast op wit,
dus elk zon-element heeft een direct label en de tabel staat ernaast.
"""
import html

INK, INK_SOFT, MUTED = "#16221e", "#4a5a52", "#8a9a92"


def nl(v: float, dec: int = 0) -> str:
    s = f"{abs(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def eur(v: float, dec: int = 0, sign: bool = False) -> str:
    pre = "−" if v < 0 else ("+" if sign and v > 0 else "")
    return f"{pre}€{nl(v, dec)}"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def tw(text: str, size: float = 12, weight: int = 600) -> float:
    """Ruwe tekstbreedte voor Inter."""
    k = 0.56 if weight < 600 else 0.6
    return len(text) * size * k


def pill(x, y, text, kind="light", size=11.5, anchor="start"):
    w = tw(text, size) + 14
    x0 = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
    return (f'<g class="pill-svg {kind}"><rect x="{x0:.1f}" y="{y - 11:.1f}" width="{w:.1f}" height="21" rx="10.5"/>'
            f'<text x="{x0 + w / 2:.1f}" y="{y + 3.5:.1f}" text-anchor="middle" font-size="{size}">{esc(text)}</text></g>')


def figure(fid, eyebrow, title, sub, svg, legend="", scroll=False, note=""):
    lg = f'<div class="legend" aria-hidden="true">{legend}</div>' if legend else ""
    nt = f'<p class="fig-note">{note}</p>' if note else ""
    return (f'<figure class="figure" id="{fid}"><figcaption><span class="fig-eyebrow">{esc(eyebrow)}</span>'
            f'<strong>{esc(title)}</strong><span class="fig-sub">{sub}</span></figcaption>{lg}'
            f'<div class="chart-wrap{" scroll" if scroll else ""}">{svg}</div>{nt}</figure>')


def sw(cls, label):
    return f'<span><i class="sw {cls}"></i>{esc(label)}</span>'


def svg_open(w, h, title, desc, cls="chart"):
    return (f'<svg viewBox="0 0 {w} {h}" class="{cls}" role="img"><title>{esc(title)}</title><desc>{esc(desc)}</desc>'
            '<defs>'
            '<pattern id="hatch-sun" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            '<rect width="6" height="6" fill="#fdf1d6"/><line x1="0" y1="0" x2="0" y2="6" stroke="#e29a00" stroke-width="2.2"/></pattern>'
            '<pattern id="hatch-red" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            '<rect width="6" height="6" fill="#fbebe4"/><line x1="0" y1="0" x2="0" y2="6" stroke="#e8a48a" stroke-width="1.4"/></pattern>'
            '<pattern id="hatch-green" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            '<rect width="6" height="6" fill="#eaf6ee"/><line x1="0" y1="0" x2="0" y2="6" stroke="#8cd8a8" stroke-width="2"/></pattern>'
            '<linearGradient id="g-band" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2fa56b" stop-opacity=".20"/>'
            '<stop offset="1" stop-color="#2fa56b" stop-opacity=".04"/></linearGradient>'
            '<linearGradient id="g-dark" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0b3d2e"/><stop offset="1" stop-color="#1f6f4a"/></linearGradient>'
            '<linearGradient id="g-green" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0e8a50"/><stop offset="1" stop-color="#2fa56b"/></linearGradient>'
            '<filter id="soft" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-color="#0b3d2e" flood-opacity=".18"/></filter>'
            '</defs>')


# ════════════════════════════════════════════════ Grafiek 1: kasstroom
def stap(bereik, n=6):
    """Mooie asstap (1, 2, 2,5 of 5 × 10^k) voor ca. n intervallen."""
    import math as _m
    ruw = bereik / n
    k = 10 ** _m.floor(_m.log10(ruw))
    for f in (1, 2, 2.5, 5, 10):
        if f * k >= ruw:
            return f * k


def kasstroom(investering, scenarios, horizon=15, titel="Normaal is het pakket na ca. 7,5 jaar terugverdiend"):
    import math as _m
    W, H = 760, 420
    ml, mr, mt, mb = 82, 150, 26, 50
    pw, ph = W - ml - mr, H - mt - mb
    top = max(-investering + v * horizon for _, v, *_ in scenarios)
    st = stap(top + investering)
    y0, y1 = -_m.ceil(investering / st) * st, _m.ceil(top / st) * st
    X = lambda j: ml + j / 15 * pw
    Y = lambda v: mt + (y1 - v) / (y1 - y0) * ph
    end = {n: -investering + v * 15 for n, v, *_ in scenarios}
    o = [svg_open(W, H, "Netto cumulatieve kasstroom per scenario",
                  "Lijngrafiek van jaar 0 tot 15. " + ", ".join(f"{n} terugverdiend na {j} jaar" for n, _, j, _ in scenarios) + ".")]
    # zone onder nul
    o.append(f'<rect x="{ml}" y="{Y(0):.1f}" width="{pw}" height="{Y(y0) - Y(0):.1f}" fill="#fbf3ef"/>')
    o.append(f'<text class="zone-label" x="{X(14.8):.1f}" y="{Y(y0) - 10:.1f}" text-anchor="end">nog niet terugverdiend</text>')
    v = y0
    while v <= y1 + 1e-6:
        if v:
            o.append(f'<line class="grid" x1="{ml}" x2="{ml + pw}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>')
        o.append(f'<text class="tick" x="{ml - 10}" y="{Y(v) + 4:.1f}" text-anchor="end">{eur(v)}</text>')
        v += st
    for j in range(16):
        o.append(f'<text class="tick" x="{X(j):.1f}" y="{mt + ph + 20}" text-anchor="middle">{j}</text>')
    o.append(f'<text class="axis-title" x="{ml + pw / 2:.1f}" y="{H - 8}" text-anchor="middle">Jaren na de investering</text>')
    # bandbreedte pessimistisch–optimistisch
    p, n_, op = scenarios[0], scenarios[1], scenarios[2]
    o.append(f'<polygon points="{X(0):.1f},{Y(-investering):.1f} {X(15):.1f},{Y(end[op[0]]):.1f} {X(15):.1f},{Y(end[p[0]]):.1f}" fill="url(#g-band)"/>')
    # nullijn
    o.append(f'<line class="zero" x1="{ml}" x2="{ml + pw}" y1="{Y(0):.1f}" y2="{Y(0):.1f}"/>')
    o.append(pill(X(0.2), Y(0) - 16, "Terugverdiend", "sun"))
    # lijnen
    for naam, netto, jaren, accent in sorted(scenarios, key=lambda s: s[3]):
        cls = "line accent" if accent else f"line muted {'pess' if naam.startswith('P') else 'opt'}"
        o.append(f'<line class="{cls}" x1="{X(0):.1f}" y1="{Y(-investering):.1f}" x2="{X(15):.1f}" y2="{Y(end[naam]):.1f}"/>')
    o.append(f'<circle class="pt start" cx="{X(0):.1f}" cy="{Y(-investering):.1f}" r="5"/>')
    # snijpunten
    ts = [investering / netto for _, netto, *_ in scenarios]
    dicht = (max(ts) - min(ts)) / 15 * pw < 230   # labels zouden overlappen: verspringen
    dy = {"P": 48, "N": 22, "O": -24} if dicht else {"P": 22, "N": 22, "O": 22}
    for (naam, netto, jaren, accent), t in zip(scenarios, ts):
        o.append(f'<circle class="pt {"accent" if accent else "muted"}" cx="{X(t):.1f}" cy="{Y(0):.1f}" r="{6.5 if accent else 5}"/>')
        o.append(pill(X(t) + 4, Y(0) + dy[naam[0]], f"{jaren} jaar", "accent" if accent else "light"))
    # eindlabels
    for naam, netto, jaren, accent in scenarios:
        y = Y(end[naam])
        o.append(f'<circle class="pt {"accent" if accent else "muted"} small" cx="{X(15):.1f}" cy="{y:.1f}" r="3.5"/>')
        o.append(f'<text class="end-label {"accent" if accent else ""}" x="{X(15) + 10:.1f}" y="{y - 2:.1f}">{naam}</text>')
        o.append(f'<text class="end-sub" x="{X(15) + 10:.1f}" y="{y + 13:.1f}">{eur(netto)} per jaar</text>')
    # hover
    o.append(f'<line class="crosshair" x1="0" x2="0" y1="{mt}" y2="{mt + ph}" visibility="hidden"/>')
    o.append(f'<rect class="hit kasstroom" x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="transparent" '
             f'data-ml="{ml}" data-pw="{pw}" data-inv="{investering}" '
             f'data-s="{";".join(f"{n}:{v}" for n, v, *_ in scenarios)}"/>')
    o.append("</svg><div class=\"tooltip\" hidden></div>")
    legend = sw("accent", "Normaal") + sw("pess", "Pessimistisch") + sw("opt", "Optimistisch") + sw("band", "Bandbreedte")
    return figure("grafiek-1", "Netto cumulatieve kasstroom", titel,
                  f"Investering {eur(investering, 2)} · kasstroom = −investering + netto per jaar × jaar",
                  "".join(o), legend)


# ════════════════════════════════════════════════ Waterval normaal scenario
def waterval(items, sub="Bedragen uit de scenariotabel, kolom Normaal"):
    """items: (label, bedrag, soort) met soort in plus|min|totaal."""
    import math as _m
    W = 760
    lw, ml, mr, mt, rh = 200, 206, 70, 30, 27
    H = mt + rh * len(items) + 12
    pw = W - ml - mr
    hoogste = max(v for _, v, s in items if s == "totaal")
    st = stap(hoogste, 5)
    vmax = int(_m.ceil(hoogste / st) * st)
    X = lambda v: ml + v / vmax * pw
    o = [svg_open(W, H, "Van bruto naar netto, normaal scenario",
                  "Waterval: besparingen tellen op tot de bruto opbrengst, jaarlijkse kosten gaan eraf tot de netto opbrengst per jaar.")]
    v = 0
    while v <= vmax + 1e-6:
        o.append(f'<line class="grid" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{mt - 6}" y2="{H - 8}"/>')
        o.append(f'<text class="tick" x="{X(v):.1f}" y="{mt - 12}" text-anchor="middle">{eur(v)}</text>')
        v += st
    run = 0
    prev = None
    for i, (label, v, soort) in enumerate(items):
        y = mt + i * rh
        if soort == "totaal":
            a, b, cls = 0, v, "wf-total"
            run = v
        elif soort == "plus":
            a, b, cls = run, run + v, "wf-plus"
            run += v
        else:
            a, b, cls = run + v, run, "wf-min"
            run += v
        bold = ' font-weight="700"' if soort == "totaal" else ""
        o.append(f'<text class="wf-label" x="{lw}" y="{y + 15}" text-anchor="end"{bold}>{esc(label)}</text>')
        if prev is not None:
            o.append(f'<line class="wf-conn" x1="{X(prev):.1f}" x2="{X(prev):.1f}" y1="{y - 6}" y2="{y + 3}"/>')
        tip = f"{label}: {eur(v, sign=soort != 'totaal')} per jaar"
        o.append(f'<rect class="{cls}" x="{X(a):.1f}" y="{y + 3}" width="{max(X(b) - X(a), 2):.1f}" height="17" rx="4" data-tip="{esc(tip)}"/>')
        o.append(f'<text class="wf-val{" strong" if soort == "totaal" else ""}" x="{X(b) + 7:.1f}" y="{y + 15.5}">'
                 f'{eur(v, sign=soort != "totaal")}</text>')
        prev = run
    o.append("</svg><div class=\"tooltip\" hidden></div>")
    legend = sw("plus", "Besparing of opbrengst") + sw("min", "Jaarlijkse kosten") + sw("total", "Totaal")
    bruto = next(v for _, v, s in items if s == "totaal")
    return figure("waterval", "Normaal scenario · per jaar", f"Van {eur(bruto)} bruto naar {eur(items[-1][1])} netto per jaar",
                  sub, "".join(o), legend)


# ════════════════════════════════════════════════ Begroting per maatregel
def begroting(items, totaal, titel="Bijna de helft van het budget gaat naar de airco's", sub=None):
    import math as _m
    W = 760
    lw, ml, mr, mt, rh = 196, 204, 120, 8, 34
    H = mt + rh * len(items) + 8
    pw = W - ml - mr
    st = stap(max(v for _, v in items), 4)
    vmax = _m.ceil(max(v for _, v in items) / st) * st
    X = lambda v: ml + v / vmax * pw
    o = [svg_open(W, H, "Investering per maatregel", "Horizontale staven per maatregel, gesorteerd op bedrag.")]
    for i, (label, v) in enumerate(sorted(items, key=lambda r: -r[1])):
        y = mt + i * rh
        pct = v / totaal * 100
        o.append(f'<text class="wf-label" x="{lw}" y="{y + 18}" text-anchor="end">{esc(label)}</text>')
        o.append(f'<rect class="track" x="{ml}" y="{y + 6}" width="{pw}" height="18" rx="9"/>')
        o.append(f'<rect class="bar-green" x="{ml}" y="{y + 6}" width="{max(X(v) - ml, 6):.1f}" height="18" rx="9" '
                 f'data-tip="{esc(label)}: {eur(v, 2 if v % 1 else 0)} ({nl(pct, 1)}%)"/>')
        o.append(f'<text class="wf-val strong" x="{X(v) + 8:.1f}" y="{y + 19.5}">{eur(v, 2 if v % 1 else 0)}'
                 f'<tspan class="muted-t" dx="6">{nl(pct, 0)}%</tspan></text>')
    o.append("</svg><div class=\"tooltip\" hidden></div>")
    return figure("begroting-chart", "Investering per onderdeel", titel,
                  sub or f"Totaal {eur(totaal, 2)}", "".join(o))


# ════════════════════════════════════════════════ Terugverdientijd per maatregel
def payback(rows, pakket_normaal, refs=None, lw=160, cap=25, fid="payback-chart", eyebrow="Terugverdientijd per maatregel",
            title="Laadpalen, smart control en zon zijn snel terug; de airco's niet",
            sub="Netto, na jaarlijkse kosten · meten per unit en inspectie hebben geen eigen opbrengst"):
    """rows: (label, pess|None, normaal|None, opt). None = niet terugverdiend (pess) / meer dan cap (normaal)."""
    W = 760
    ml, mr, mt, rh = lw + 12, 30, 60, 50
    H = mt + rh * len(rows) + 30
    pw = W - ml - mr
    zone = cap * 0.128  # extra jaren voor de zone 'niet'
    X = lambda j: ml + min(j, cap + zone) / (cap + zone) * pw
    o = [svg_open(W, H, "Terugverdientijd per maatregel",
                  "Per maatregel een lijn van optimistisch tot pessimistisch, met een punt voor het normale scenario.")]
    o.append(f'<rect x="{X(cap):.1f}" y="{mt - 14}" width="{X(cap + zone) - X(cap):.1f}" height="{rh * len(rows) + 8}" fill="url(#hatch-red)" opacity=".75"/>')
    o.append(f'<text class="zone-label" x="{(X(cap) + X(cap + zone)) / 2:.1f}" y="{mt - 20}" text-anchor="middle">niet / &gt; {cap}</text>')
    for j in range(0, cap + 1, 5 if cap > 15 else 1):
        o.append(f'<line class="grid" x1="{X(j):.1f}" x2="{X(j):.1f}" y1="{mt - 14}" y2="{mt + rh * len(rows) - 6}"/>')
        o.append(f'<text class="tick" x="{X(j):.1f}" y="{mt + rh * len(rows) + 12}" text-anchor="middle">{j}</text>')
    o.append(f'<text class="axis-title" x="{ml + pw / 2:.1f}" y="{H - 2}" text-anchor="middle">Jaren</text>')
    # referentielijnen
    if refs is None:
        refs = [(pakket_normaal, f"totaal pakket {nl(pakket_normaal, 1)} jaar", "ref-sun", 36),
                (15, "levensduur airco 15 jaar (aanname)", "ref-ink", 20)]
    for j, lab, cls, dy in refs:
        o.append(f'<line class="{cls}" x1="{X(j):.1f}" x2="{X(j):.1f}" y1="{mt - dy + 4}" y2="{mt + rh * len(rows) - 6}"/>')
        o.append(f'<text class="ref-label" x="{X(j) + 5:.1f}" y="{mt - dy + 2}">{esc(lab)}</text>')
    fmt = lambda v: "niet" if v is None else nl(v, 1)
    for i, (label, pess, norm, opt) in enumerate(rows):
        y = mt + i * rh + 14
        o.append(f'<text class="wf-label" x="{lw}" y="{y + 4}" text-anchor="end">{esc(label)}</text>')
        xp = X(cap + zone - 0.4) if pess is None else X(pess)
        xo = X(opt)
        o.append(f'<line class="range" x1="{xo:.1f}" x2="{xp:.1f}" y1="{y}" y2="{y}"/>')
        if pess is None:
            o.append(f'<path class="range-arrow" d="M{xp - 7:.1f},{y - 5} L{xp:.1f},{y} L{xp - 7:.1f},{y + 5}"/>')
        else:
            o.append(f'<circle class="dot-end" cx="{xp:.1f}" cy="{y}" r="4.5"/>')
        o.append(f'<circle class="dot-end" cx="{xo:.1f}" cy="{y}" r="4.5"/>')
        xn = X(cap + zone / 2) if norm is None else X(norm)
        o.append(f'<circle class="dot-norm" cx="{xn:.1f}" cy="{y}" r="7.5" data-tip="{esc(label)}: '
                 f'pessimistisch {fmt(pess)}, normaal {"meer dan 25" if norm is None else nl(norm, 1)}, optimistisch {nl(opt, 1)} jaar"/>')
        o.append(f'<text class="dot-label" x="{xn:.1f}" y="{y - 13}" text-anchor="middle">{f"> {cap}" if norm is None else nl(norm, 1)}</text>')
        if (xp - xo) > 40:
            o.append(f'<text class="end-sub" x="{xo:.1f}" y="{y + 19}" text-anchor="middle">{nl(opt, 1)}</text>')
            if pess is not None:
                o.append(f'<text class="end-sub" x="{xp:.1f}" y="{y + 19}" text-anchor="middle">{nl(pess, 1)}</text>')
    o.append("</svg><div class=\"tooltip\" hidden></div>")
    legend = sw("dot", "Normaal") + sw("range", "Optimistisch tot pessimistisch") + sw("hatch-red", f"Niet of na meer dan {cap} jaar")
    return figure(fid, eyebrow, title, sub, "".join(o), legend)


# ════════════════════════════════════════════════ Laadplan
def laadplan(rows, investering):
    """rows: (label, marge, ere_min, ere_max)."""
    W = 760
    lw, ml, mr, mt, rh = 150, 160, 150, 26, 44
    H = mt + rh * len(rows) + 8
    pw = W - ml - mr
    vmax = 4800
    X = lambda v: ml + v / vmax * pw
    o = [svg_open(W, H, "Opbrengst laadpalen per jaar", "Gestapelde staven: marge op stroom plus ERE-opbrengst, met bandbreedte.")]
    for v in range(0, vmax + 1, 800):
        o.append(f'<line class="grid" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{mt - 6}" y2="{H - 8}"/>')
        o.append(f'<text class="tick" x="{X(v):.1f}" y="{mt - 12}" text-anchor="middle">{eur(v)}</text>')
    o.append(f'<text class="tick" x="{W - 4}" y="{mt - 12}" text-anchor="end" font-weight="700">terugverdientijd</text>')
    for i, (label, marge, emin, emax) in enumerate(rows):
        y = mt + i * rh
        lo, hi = marge + emin, marge + emax
        o.append(f'<text class="wf-label" x="{lw}" y="{y + 20}" text-anchor="end">{esc(label)}</text>')
        o.append(f'<rect class="seg-green" x="{ml}" y="{y + 7}" width="{X(marge) - ml:.1f}" height="20" rx="4" data-tip="Marge stroom {esc(label)}: {eur(marge)}"/>')
        o.append(f'<rect class="seg-sun" x="{X(marge) + 2:.1f}" y="{y + 7}" width="{X(lo) - X(marge) - 2:.1f}" height="20" rx="4" data-tip="ERE minimaal: {eur(emin)}"/>')
        o.append(f'<rect x="{X(lo) + 2:.1f}" y="{y + 7}" width="{X(hi) - X(lo) - 2:.1f}" height="20" rx="4" fill="url(#hatch-sun)" data-tip="ERE bandbreedte tot {eur(emax)}"/>')
        o.append(f'<text class="wf-val strong" x="{X(hi) + 8:.1f}" y="{y + 21.5}">{eur(lo)}–{nl(hi)}</text>')
        a_, b_ = nl(investering / hi, 1), nl(investering / lo, 1)
        o.append(f'<text class="wf-val" x="{W - 4}" y="{y + 21.5}" text-anchor="end">{a_ if a_ == b_ else a_ + "–" + b_} jaar</text>')
    o.append("</svg><div class=\"tooltip\" hidden></div>")
    legend = sw("plus", "Marge stroom") + sw("sun", "ERE (minimaal)") + sw("hatch-sun", "ERE (bandbreedte)")
    return figure("laadplan-chart", "Laadplan · 2 palen per jaar", "Tarief en bezetting bepalen samen de opbrengst",
                  f"Uit het rekenmodel, vóór wintercorrectie en backoffice · investering {eur(investering)}", "".join(o), legend)


# ════════════════════════════════════════════════ Energie per werkdag
def werkdag(data):
    """data: {seizoen: {'vraag': [(label, kWh)], 'aanbod': [(label, kWh)]}}"""
    W, H = 760, 360
    ml, mr, mt, mb = 60, 170, 24, 54
    pw, ph = W - ml - mr, H - mt - mb
    vmax = 300
    Y = lambda v: mt + ph - v / vmax * ph
    cls_of = {"Verbruik pand (incl. airco)": "c-ink", "Laadpalen": "c-rose",
              "Net": "c-blue", "Batterij": "c-green", "Zon": "c-sun"}
    o = [svg_open(W, H, "Energie per werkdag, winter en zomer",
                  "Gestapelde kolommen: vraag tegenover beschikbare energie, per seizoen.")]
    for v in range(0, vmax + 1, 50):
        o.append(f'<line class="grid" x1="{ml}" x2="{ml + pw}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>')
        o.append(f'<text class="tick" x="{ml - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    o.append(f'<text class="tick" x="{ml - 8}" y="{mt - 10}" text-anchor="end" font-weight="700">kWh</text>')
    bw, gap, ggap = 76, 18, 70
    x = ml + 34
    for seizoen, d in data.items():
        tops = {}
        for kind in ("vraag", "aanbod"):
            acc = 0
            for label, v in d[kind]:
                y_top = Y(acc + v)
                o.append(f'<rect class="{cls_of[label]}" x="{x}" y="{y_top + 1:.1f}" width="{bw}" height="{Y(acc) - y_top - 2:.1f}" rx="3" '
                         f'data-tip="{seizoen}, {"vraag" if kind == "vraag" else "beschikbaar"}: {esc(label)} {v} kWh"/>')
                if Y(acc) - y_top > 16:
                    light = cls_of[label] in ("c-ink", "c-blue", "c-green", "c-rose")
                    o.append(f'<text class="seg-val{" on-dark" if light else ""}" x="{x + bw / 2}" y="{(Y(acc) + y_top) / 2 + 4:.1f}" text-anchor="middle">{v}</text>')
                acc += v
            tops[kind] = (x, acc)
            o.append(f'<text class="wf-val strong" x="{x + bw / 2}" y="{Y(acc) - 7:.1f}" text-anchor="middle">{acc} kWh</text>')
            o.append(f'<text class="tick" x="{x + bw / 2}" y="{mt + ph + 18}" text-anchor="middle">{"Vraag" if kind == "vraag" else "Beschikbaar"}</text>')
            x += bw + gap
        o.append(f'<text class="g-name" x="{x - gap - bw - gap / 2:.1f}" y="{mt + ph + 40}" text-anchor="middle">{seizoen}</text>')
        marge = tops["aanbod"][1] - tops["vraag"][1]
        xv = tops["vraag"][0]
        o.append(pill(xv + bw + gap / 2, Y(tops["aanbod"][1]) - 30, f"ruimte {marge} kWh", "sun" if marge < 20 else "light", 11, "middle"))
        x += ggap - gap
    # legenda rechts
    ly = mt + 10
    for label, cls in [("Verbruik pand (incl. airco)", "c-ink"), ("Laadpalen", "c-rose"), ("Net (17 kW × 10 uur)", "c-blue"),
                       ("Batterij (90% van 50 kWh)", "c-green"), ("Zon", "c-sun")]:
        o.append(f'<rect class="{cls}" x="{W - mr + 14}" y="{ly - 9}" width="12" height="12" rx="3"/>')
        o.append(f'<text class="end-sub" x="{W - mr + 32}" y="{ly + 1}">{esc(label)}</text>')
        ly += 22
    o.append("</svg><div class=\"tooltip\" hidden></div>")
    return figure("werkdag-chart", "Netaansluiting 3x25 A · per werkdag 08:00 tot 18:00",
                  "In de winter blijft er maar 7 kWh over",
                  "Uit de tabel ‘Energie per werkdag’", "".join(o))


# ════════════════════════════════════════════════ Stroomcontract-varianten
def contract(rows, investering, fid="contract-chart", eyebrow="Stroomcontract · nu → straks", title=None, sub=None):
    """rows: (variant, (netto pess, norm, opt), (jaren pess, norm, opt))."""
    W = 760
    lw, ml, mr, mt, rh = 168, 178, 150, 30, 50
    H = mt + rh * len(rows) + 10
    pw = W - ml - mr
    vmax = 12000
    X = lambda v: ml + v / vmax * pw
    o = [svg_open(W, H, "Netto per jaar per stroomcontract",
                  "Per contractvariant een staaf voor het normale scenario en een lijn van pessimistisch tot optimistisch.")]
    for v in range(0, vmax + 1, 2000):
        o.append(f'<line class="grid" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{mt - 6}" y2="{H - 8}"/>')
        o.append(f'<text class="tick" x="{X(v):.1f}" y="{mt - 12}" text-anchor="middle">{eur(v)}</text>')
    o.append(f'<text class="tick" x="{W - 4}" y="{mt - 12}" text-anchor="end" font-weight="700">terugverdientijd</text>')
    for i, (naam, netto, jaren) in enumerate(rows):
        y = mt + i * rh
        best = i == len(rows) - 1
        fw = ' font-weight="700"' if best else ""
        o.append(f'<text class="wf-label"{fw} x="{lw}" y="{y + 22}" text-anchor="end">{esc(naam)}</text>')
        o.append(f'<rect class="track" x="{ml}" y="{y + 9}" width="{pw}" height="20" rx="10"/>')
        o.append(f'<rect class="{"bar-green" if best else "bar-muted"}" x="{ml}" y="{y + 9}" width="{X(netto[1]) - ml:.1f}" height="20" rx="10" '
                 f'data-tip="{esc(naam)}: netto {eur(netto[0])} / {eur(netto[1])} / {eur(netto[2])} per jaar"/>')
        o.append(f'<line class="range" x1="{X(netto[0]):.1f}" x2="{X(netto[2]):.1f}" y1="{y + 19}" y2="{y + 19}" stroke-width="2.5"/>')
        for v in (netto[0], netto[2]):
            o.append(f'<circle class="dot-end" cx="{X(v):.1f}" cy="{y + 19}" r="4"/>')
        o.append(f'<text class="seg-val{" on-dark" if best else ""}" x="{ml + 12}" y="{y + 23.5}">{eur(netto[1])}</text>')
        o.append(f'<text class="wf-val{" strong" if best else ""}" x="{W - 4}" y="{y + 23.5}" text-anchor="end">{jaren[1]} jaar'
                 f'<tspan class="muted-t" dx="5">({jaren[2]}–{jaren[0]})</tspan></text>')
    o.append("</svg><div class=\"tooltip\" hidden></div>")
    legend = sw("plus", "Netto per jaar, normaal") + sw("range", "Pessimistisch tot optimistisch")
    return figure(fid, eyebrow,
                  title or f"Dynamisch straks levert ca. {eur(rows[-1][1][1] - rows[0][1][1])} per jaar meer op",
                  sub or f"Investering {eur(investering, 2)} · deze klant: dynamisch → dynamisch · verschil zit in de batterij en de teruglevering",
                  "".join(o), legend)


# ════════════════════════════════════════════════ EMS-dagschema
def dagschema():
    W, H = 760, 300
    ml, mr, mt, mb = 52, 24, 30, 44
    pw, ph = W - ml - mr, H - mt - mb
    t0, t1 = 13, 26
    X = lambda h: ml + h / 24 * pw
    Y = lambda t: mt + (t1 - t) / (t1 - t0) * ph
    o = [svg_open(W, H, "Dagschema verwarmen en koelen (illustratief)",
                  "Streeftemperatuur over een werkdag: nachtverlaging, voorverwarmen, basis 20 °C, koelen op 24 °C.")]
    o.append(f'<rect x="{X(8):.1f}" y="{mt}" width="{X(18) - X(8):.1f}" height="{ph}" fill="#eaf6ee"/>')
    o.append(f'<text class="zone-label green" x="{(X(8) + X(18)) / 2:.1f}" y="{mt + ph - 8}" text-anchor="middle">kantoortijd 08:00 tot 18:00</text>')
    for t in range(14, 26, 2):
        o.append(f'<line class="grid" x1="{ml}" x2="{ml + pw}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>')
        o.append(f'<text class="tick" x="{ml - 8}" y="{Y(t) + 4:.1f}" text-anchor="end">{t} °C</text>')
    for h in range(0, 25, 2):
        o.append(f'<text class="tick" x="{X(h):.1f}" y="{mt + ph + 18}" text-anchor="middle">{h:02d}:00</text>')
    # nachtband 15–16
    for a, b in [(0, 6.5), (18, 24)]:
        o.append(f'<rect x="{X(a):.1f}" y="{Y(16):.1f}" width="{X(b) - X(a):.1f}" height="{Y(15) - Y(16):.1f}" fill="#fbe3d7" rx="2"/>')
    # handmatige ruimte
    o.append(f'<rect x="{X(8):.1f}" y="{Y(22):.1f}" width="{X(18) - X(8):.1f}" height="{Y(20) - Y(22):.1f}" fill="url(#hatch-red)" opacity=".8"/>')
    o.append(f'<text class="end-sub" x="{X(13):.1f}" y="{Y(21) + 4:.1f}" text-anchor="middle">+2 °C op verzoek, vervalt na 2 uur</text>')
    # verwarmen
    o.append(f'<polyline class="heat" points="{X(0):.1f},{Y(15.5):.1f} {X(6.5):.1f},{Y(15.5):.1f}"/>')
    o.append(f'<polyline class="heat dashed" points="{X(6.5):.1f},{Y(15.5):.1f} {X(8):.1f},{Y(20):.1f}"/>')
    o.append(f'<polyline class="heat" points="{X(8):.1f},{Y(20):.1f} {X(18):.1f},{Y(20):.1f} {X(18):.1f},{Y(15.5):.1f} {X(24):.1f},{Y(15.5):.1f}"/>')
    # koelen
    o.append(f'<polyline class="cool" points="{X(8):.1f},{Y(24):.1f} {X(18):.1f},{Y(24):.1f}"/>')
    o.append(f'<line class="cool dashed" x1="{X(8):.1f}" x2="{X(18):.1f}" y1="{Y(22):.1f}" y2="{Y(22):.1f}"/>')
    o.append(f'<text class="end-sub" x="{X(18) + 6:.1f}" y="{Y(22) + 4:.1f}">koelen nooit onder 22 °C</text>')
    o.append(pill(X(8.2), Y(24) - 16, "Koelen 24 °C", "blue"))
    o.append(pill(X(8.2), Y(20) + 18, "Verwarmen 20 °C", "red"))
    o.append(f'<text class="end-sub" x="{X(3.2):.1f}" y="{Y(16) - 8:.1f}" text-anchor="middle">nacht: afkoelen tot 15 à 16 °C</text>')
    o.append(f'<text class="end-sub" x="{X(21):.1f}" y="{Y(16) - 8:.1f}" text-anchor="middle">eco vanaf 18:00 · koelen uit</text>')
    o.append(f'<text class="end-sub" x="{X(7.1):.1f}" y="{Y(19.6):.1f}" text-anchor="end">voorverwarmen,</text>')
    o.append(f'<text class="end-sub" x="{X(7.1):.1f}" y="{Y(19.6) + 13:.1f}" text-anchor="end">start op buitentemperatuur</text>')
    o.append("</svg>")
    legend = sw("heat", "Verwarmen") + sw("cool", "Koelen") + sw("hatch-red", "Handmatige ruimte")
    return figure("dagschema-chart", "EMS · werkdag", "Warm als u er bent, zuinig als u weg bent",
                  "Illustratie van het dagschema hierboven · de starttijd van het voorverwarmen varieert met de buitentemperatuur",
                  "".join(o), legend)


# ════════════════════════════════════════════════ Diagram 2: planning
def _wrap(text, n):
    lines, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur]


def planning(fasen, turbine):
    W = 760
    wx0, wx1 = 262, 606
    gx0, mx0, mx1 = 614, 644, 752
    top, row = 46, 58
    rows = fasen + [turbine]
    H = top + row * len(rows) + 6
    wk = (wx1 - wx0) / 14
    mo = (mx1 - mx0) / 6
    o = [svg_open(W, H, "Planning in weken", "Vijf fasen van week 1 tot en met 14, plus de windturbine als apart spoor in maand 6 tot 12.",
                  "chart gantt")]
    o.append(f'<text class="axis-title" x="{wx0}" y="14">Week</text>')
    for w in range(1, 15):
        x = wx0 + (w - 0.5) * wk
        o.append(f'<text class="tick" x="{x:.1f}" y="32" text-anchor="middle">{w}</text>')
        if w % 2 == 1:
            o.append(f'<rect class="band" x="{wx0 + (w - 1) * wk:.1f}" y="{top - 6}" width="{wk:.1f}" height="{row * len(rows)}"/>')
    o.append(f'<text class="axis-title" x="{mx0}" y="14">Maand</text>')
    for m in range(6, 13):
        o.append(f'<text class="tick" x="{mx0 + (m - 6) * mo:.1f}" y="32" text-anchor="middle">{m}</text>')
    for dx in (0, 7):
        o.append(f'<line class="break" x1="{gx0 + dx:.1f}" y1="{top - 4}" x2="{gx0 + dx + 8:.1f}" y2="{top + row * len(rows) - 10}"/>')
    for i, (fase, periode, inhoud, a, b) in enumerate(rows):
        y = top + i * row
        turb = fase.startswith("Windturbine")
        o.append(f'<circle class="{"g-num optie" if turb else "g-num"}" cx="12" cy="{y + 12}" r="11"/>')
        o.append(f'<text class="g-num-t{" dark" if turb else ""}" x="12" y="{y + 16}" text-anchor="middle">{"+" if turb else i + 1}</text>')
        o.append(f'<text class="g-name" x="32" y="{y + 16}">{esc(fase)}</text>')
        for k, ln in enumerate(_wrap(inhoud, 40)):
            o.append(f'<text class="g-sub" x="32" y="{y + 31 + k * 13}">{esc(ln)}</text>')
        tip = esc(f"{fase}: {periode}. {inhoud}")
        if turb:
            x0, x1 = mx0 + (a - 6) * mo, mx0 + (b - 6) * mo
            o.append(f'<rect x="{x0:.1f}" y="{y + 4}" width="{x1 - x0:.1f}" height="24" rx="12" fill="url(#hatch-green)" stroke="#2fa56b" stroke-dasharray="4 3" data-tip="{tip}"/>')
            o.append(f'<text class="g-bar-label dark" x="{gx0 - 10:.1f}" y="{y + 20}" text-anchor="end">{esc(periode)}</text>')
        else:
            x0, x1 = wx0 + (a - 1) * wk + 2, wx0 + b * wk - 2
            o.append(f'<rect class="g-bar" x="{x0:.1f}" y="{y + 4}" width="{x1 - x0:.1f}" height="24" rx="12" filter="url(#soft)" data-tip="{tip}"/>')
            lab = periode.replace("Week ", "wk ").replace(" tot ", "–")
            if x1 - x0 > tw(lab, 11.5) + 12:
                o.append(f'<text class="g-bar-label" x="{(x0 + x1) / 2:.1f}" y="{y + 20}" text-anchor="middle">{esc(lab)}</text>')
            else:
                o.append(f'<text class="g-bar-label dark" x="{x0 - 7:.1f}" y="{y + 20}" text-anchor="end">{esc(lab)}</text>')
    # oplevering-vlag
    xf = wx0 + 13.5 * wk
    o.append(f'<path d="M{xf:.1f},{top + row * 4 + 2} l0,-14 l10,4 l-10,4" fill="#ffb627" stroke="#0b3d2e" stroke-width="1.2"/>')
    o.append("</svg><div class=\"tooltip\" hidden></div>")
    legend = sw("gbar", "Fase") + sw("hatch-green", "Optie, apart spoor")
    return figure("diagram-2", "Diagram 2 · planning", "In ca. 14 weken opgeleverd, de turbine als apart spoor",
                  "Week 1 tot en met 14; windturbine in maand 6 tot 12, alleen na positieve windmeting en vergunning",
                  "".join(o), legend, scroll=True)
