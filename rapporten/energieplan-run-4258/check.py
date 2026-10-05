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

print("\n3. Interne optellingen")
sc = tbl_starting("Per jaar")
names = [plain(r[0]) for r in sc]
bi, ni = names.index("Bruto besparing en opbrengst"), names.index("Netto per jaar")
for k in (1, 2, 3):
    bruto = sum(eur(r[k]) for r in sc[1:bi])
    netto = bruto + sum(eur(r[k]) for r in sc[bi + 1:ni])
    ok(near(bruto, eur(sc[bi][k])) and near(netto, eur(sc[ni][k])),
       f"scenario {sc[0][k]}: bruto {bruto:.0f}, netto {netto:.0f}")
    t = 48987.80 / netto
    ok(f"{t:.1f}".replace(".", ",") in {"12,9", "7,2", "5,0"}, f"terugverdientijd {sc[0][k]}: {t:.2f} jaar")

zl = tbl_starting("Scenario")
for r, netto in zip(zl[1:], (3809, 6762, 9732)):
    lp = {3809: 994, 6762: 1922, 9732: 2942}[netto]
    ok(near(eur(r[1]), netto - lp), f"zonder laadpalen {r[0]}: {netto} − {lp} = {eur(r[1]):.0f}")
    ok(f"{44987.80 / eur(r[1]):.1f}".replace(".", ",") == r[2].split()[0], f"  terugverdientijd {r[2]}")

ok(near(48987.80 - 23487.80, 25500), "zonder airco's: €25.500")
for netto, airco, want in ((3809, -400, 4209), (6762, 450, 6312), (9732, 1200, 8532)):
    ok(netto - airco == want, f"  netto zonder airco's {want} ({netto} − {airco})")

lp = tbl_starting("Tarief")
for r in lp[1:]:
    tarief, kwh = eur(r[0]), eur(r[2])
    marge = round(kwh * (tarief - 0.25))
    e_lo, e_hi = round(kwh * 0.07), round(kwh * 0.10)
    ok(marge == eur(r[3]) and f"€{e_lo:,}".replace(",", ".") in r[4] and f"{e_hi:,}".replace(",", ".") in r[4],
       f"laadplan {r[0]} {r[1]}: marge {marge}, ERE {e_lo}–{e_hi}")

wd = [t for t in md_tables if t[0] == ["", "Winter", "Zomer"]][0]
for k in (1, 2):
    v = [float(re.sub(r"[^\d]", "", plain(r[k]))) for r in wd[1:]]
    ok(v[0] + v[1] == v[2] and v[3] + v[4] + v[5] == v[6], f"energie per werkdag {wd[0][k]}: {v[2]:.0f} / {v[6]:.0f} kWh")

ems = [t for t in md_tables if t[0][1:] == ["Pessimistisch", "Normaal", "Optimistisch"] and t[0][0] == ""][0]
for k in (1, 2, 3):
    ok(near(eur(ems[1][k]) + eur(ems[2][k]), eur(ems[3][k])), f"EMS-besparing {ems[0][k]}")

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
