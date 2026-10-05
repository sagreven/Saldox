#!/usr/bin/env python3
"""Controleert het rapport na het bouwen.

1. Elke tabelcel in rapport.html is letterlijk gelijk aan de markdown (geen bedrag veranderd).
2. De controletotalen uit CLAUDE.md, plus de interne optellingen van de tabellen.
3. De grafiekdata in build.py komt overeen met de tabellen.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import build
import model

HERE = Path(__file__).parent
fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  FOUT ") + msg)
    if not cond:
        fails.append(msg)


def eur(s: str) -> float:
    """'€48.987,80' / '−€1.500' / '**€9.672**' → float."""
    s = s.replace("*", "").replace("ca. ", "").strip()
    neg = s.startswith(("−", "-"))
    s = re.sub(r"[^\d,]", "", s).replace(",", ".")
    return -float(s) if neg else float(s)


def near(a, b, tol=0.005):
    return abs(a - b) <= tol


# ── markdown-tabellen
md = build.SRC.read_text(encoding="utf-8")
md_tables, cur = [], []
for line in md.splitlines():
    if line.startswith("|"):
        cur.append([c.strip() for c in line.strip().strip("|").split("|")])
    elif cur:
        md_tables.append([r for r in cur if not re.fullmatch(r"[-\s|]+", "|".join(r))])
        cur = []
if cur:
    md_tables.append([r for r in cur if not re.fullmatch(r"[-\s|]+", "|".join(r))])


def plain(s):
    return re.sub(r"\*\*(.*?)\*\*", r"\1", s).strip()


# ── html-tabellen
class T(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.cell, self.depth = [], None, 0

    def handle_starttag(self, tag, a):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self.tables[-1].append([])
        elif tag in ("td", "th"):
            self.cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.tables[-1][-1].append(" ".join(self.cell.split()))
            self.cell = None

    def handle_data(self, d):
        if self.cell is not None:
            self.cell += d


p = T()
p.feed((HERE / "rapport.html").read_text(encoding="utf-8"))

print("1. Tabellen letterlijk overgenomen")
ok(len(p.tables) == len(md_tables), f"{len(md_tables)} tabellen in markdown, {len(p.tables)} in html")
diff = 0
for i, (a, b) in enumerate(zip(md_tables, p.tables)):
    for r1, r2 in zip(a, b):
        for c1, c2 in zip(r1, r2):
            if " ".join(plain(c1).split()) != c2:
                diff += 1
                print(f"       tabel {i + 1}: {plain(c1)!r} ≠ {c2!r}")
    if len(a) != len(b):
        diff += 1
ok(diff == 0, "alle cellen identiek")


def table(first_header):
    for t in md_tables:
        if t[0][0] == first_header or t[0][1:2] == [first_header]:
            return t
    raise KeyError(first_header)


def tbl_starting(cell):
    return next(t for t in md_tables if t[0][0] == cell)


print("\n2. Controletotalen (CLAUDE.md)")
beg = tbl_starting("Post")
rows = {plain(r[0]): r for r in beg[1:]}
basis_idx = [plain(r[0]) for r in beg].index("Totaal basis")
basis_sum = sum(eur(r[1]) for r in beg[1:basis_idx])
ok(near(basis_sum, 48987.80), f"begroting basis telt op: {basis_sum:.2f} = 48.987,80")
ok(near(eur(rows["Totaal basis"][1]), 48987.80), "totaalregel basis = €48.987,80")
ok(near(round(48987.80 * 1.21, 2), 59275.24), f"incl. 21% btw: {48987.80 * 1.21:.2f} → €59.275,24")
opties = eur(rows["Optie: grote ruimte airco's (2 units i.p.v. 1)"][1]) + eur(rows["Optie: windturbine Fortis Montana 5 kW met mast"][1])
ok(near(48987.80 + opties, eur(rows["Totaal met beide opties"][1])) and near(48987.80 + opties, 80768.20),
   f"met beide opties: {48987.80 + opties:.2f} = 80.768,20")

mt = tbl_starting("Maatregel")
inv = sum(eur(r[1]) for r in mt[1:-1])
ok(near(inv, 48987.80), f"investering per maatregel telt op: {inv:.2f}")
for k, naam in enumerate(["pessimistisch", "normaal", "optimistisch"]):
    s = 0
    for r in mt[1:-1]:
        parts = r[2].split(" / ")
        if len(parts) == 3:
            s += eur(parts[k])
    want = eur(mt[-1][2].replace("**", "").split(" / ")[k])
    ok(near(s, want), f"netto per maatregel {naam}: {s:.0f} = {want:.0f}")

print("\n3. Interne optellingen en rekenmodel (model.py, actuele aannames)")
m = model.bereken(model.ACTUEEL)
sc = tbl_starting("Per jaar")
names = [plain(r[0]) for r in sc]
bi, ni = names.index("Bruto besparing en opbrengst"), names.index("Netto per jaar")
rows_model = [m["zon"], model.BATTERIJ, m["airco"], m["ems"], m["sens"], m["laadpalen"]]
for k in (1, 2, 3):
    bruto = sum(eur(r[k]) for r in sc[1:bi])
    netto = bruto + sum(eur(r[k]) for r in sc[bi + 1:ni])
    ok(near(bruto, eur(sc[bi][k])) and near(netto, eur(sc[ni][k])),
       f"scenario {sc[0][k]}: bruto {bruto:.0f}, netto {netto:.0f}")
    ok([eur(r[k]) for r in sc[1:bi]] == [x[k - 1] for x in rows_model], f"  regels = model.py")
    ok(netto == m["netto"][k - 1], f"  netto = model.py ({m['netto'][k - 1]})")
    ok(model.jaren(48987.80, netto) in mt[-1][3], f"  terugverdientijd {model.jaren(48987.80, netto)} jaar")

zl = tbl_starting("Scenario")
for i, r in enumerate(zl[1:]):
    want = m["netto"][i] - m["per"]["laad"][i]
    ok(near(eur(r[1]), want) and r[2].startswith(model.jaren(44987.80, want)),
       f"zonder laadpalen {r[0]}: {want} → {model.jaren(44987.80, want)} jaar")

ok(near(48987.80 - 23487.80, 25500), "zonder airco's: €25.500")
zonder = [n - a for n, a in zip(m["netto"], m["per"]["airco"])]
txt = "€" + " / €".join(f"{v:,}".replace(",", ".") for v in zonder)
ok(txt in md, f"  netto zonder airco's {txt}")
ok(" / ".join(model.jaren(25500, v) for v in zonder) + " jaar" in md, "  terugverdientijd zonder airco's")

lp = tbl_starting("Tarief")
for r in lp[1:]:
    kwh, marge, e_lo, e_hi, t_lo, t_hi = m["laadplan"][(eur(r[0]), int(r[1][0]))]
    ok(marge == eur(r[3]) and r[4] == f"€{e_lo:,} tot {e_hi:,}".replace(",", ".")
       and r[5] == f"€{t_lo:,} tot {t_hi:,}".replace(",", "."), f"laadplan {r[0]} {r[1]}: marge {marge}, ERE {e_lo}–{e_hi}")

for naam, key in [("Zonnepanelen", "zon"), ("Smart control", "smart"), ("Laadpalen", "laad"), ("Batterij", "batt"), ("Airco's", "airco")]:
    r = next(r for r in mt if r[0].startswith(naam))
    want = " / ".join(eur_s for eur_s in [("−€" if v < 0 else "€") + f"{abs(v):,}".replace(",", ".") for v in m["per"][key]])
    ok(r[2] == want, f"per maatregel {naam}: {want}")

wd = [t for t in md_tables if t[0] == ["", "Winter", "Zomer"]][0]
for k in (1, 2):
    v = [float(re.sub(r"[^\d]", "", plain(r[k]))) for r in wd[1:]]
    ok(v[0] + v[1] == v[2] and v[3] + v[4] + v[5] == v[6], f"energie per werkdag {wd[0][k]}: {v[2]:.0f} / {v[6]:.0f} kWh")

ems = [t for t in md_tables if t[0][1:] == ["Pessimistisch", "Normaal", "Optimistisch"] and t[0][0] == ""][0]
for k in (1, 2, 3):
    ok(near(eur(ems[1][k]) + eur(ems[2][k]), eur(ems[3][k])), f"EMS-besparing {ems[0][k]}")
    ok((eur(ems[1][k]), eur(ems[2][k])) == (m["ems_v"][k - 1], m["ems_k"][k - 1]), f"  EMS = model.py")

ct = next(t for t in md_tables if t[0][1:2] == ["Nu vast, straks vast"])
vs = model.varianten()
fmt = lambda xs: " / ".join(("−€" if v < 0 else "€") + f"{abs(v):,}".replace(",", ".") for v in xs)
rows_ct = {r[0]: r[1:] for r in ct}
for i, k in enumerate(["vast/vast", "vast/dynamisch", "dynamisch/dynamisch"]):
    v = vs[k]
    ok(rows_ct["Batterij per jaar"][i] == fmt(v["batterij"]) and rows_ct["Zon per jaar"][i] == fmt(v["zon"])
       and rows_ct["Netto per jaar"][i] == fmt(v["netto"])
       and rows_ct["Terugverdientijd"][i] == " / ".join(model.jaren(48987.80, n) for n in v["netto"]) + " jaar",
       f"stroomcontract {k}: netto {v['netto']}")
    ok(build.CONTRACT[i][1] == v["netto"], f"  grafiekdata {k}")
ok(vs["dynamisch/dynamisch"]["netto"] == m["netto"], "hoofdscenario = dynamisch/dynamisch")

pt = next(t for t in md_tables if t[0][1:] == ["Basis (huidige aannames)", "2027 volgens termijnmarkt"])
rp = {r[0]: r[1:] for r in pt}
for i, a_ in enumerate([model.ACTUEEL, model.PRIJZEN_2027]):
    v = model.bereken(a_)
    es = tuple(e + s_ for e, s_ in zip(v["ems"], v["sens"]))
    ok(rp["Zon per jaar"][i] == fmt(v["zon"]) and rp["Airco (stroom + gas)"][i] == fmt(v["airco"])
       and rp["EMS en sensoren"][i] == fmt(es) and rp["Laadpalen"][i] == fmt(v["laadpalen"])
       and rp["Netto per jaar"][i] == fmt(v["netto"])
       and rp["Terugverdientijd"][i] == " / ".join(model.jaren(48987.80, n) for n in v["netto"]) + " jaar",
       f"prijsscenario {pt[0][i + 1]}: netto {v['netto']}")
    ok(build.PRIJS[i][1] == v["netto"], "  grafiekdata prijsscenario")

print("\n4. Grafiekdata = tabellen")
ok(near(sum(v for _, v in build.MAATREGELEN), 48987.80), "begrotingsgrafiek telt op tot €48.987,80")
wf = build.WATERVAL
ok(sum(v for _, v, s in wf[:6]) == wf[6][1] and wf[6][1] + sum(v for _, v, s in wf[7:13]) == wf[13][1],
   "waterval: bruto 9.672, netto 6.762")
ok([eur(r[2]) for r in sc[1:bi]] == [v for _, v, _ in wf[:6]], "waterval-besparingen = kolom Normaal")
ok([eur(r[2]) for r in sc[bi + 1:ni]] == [v for _, v, _ in wf[7:13]], "waterval-kosten = kolom Normaal")
ok([(eur(r[3]),) for r in lp[1:]] == [(m,) for _, m, *_ in build.LAADPLAN], "laadplan-grafiek = rekenmodel")
for naam, netto, jaren, _ in build.SCENARIOS:
    ok(f"{build.INVESTERING / netto:.1f}".replace(".", ",") == jaren, f"grafiek 1 {naam}: {jaren} jaar")

print()
if fails:
    print(f"{len(fails)} fout(en)")
    sys.exit(1)
print("Alle controles geslaagd.")
