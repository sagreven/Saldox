#!/usr/bin/env python3
"""Controleert de huishouden-templates: optellingen, btw, terugverdientijden en
dat de getallen in de tekst gelijk zijn aan uitkomsten.json (uit het rekenmodel)."""
import json
import re
import sys
from pathlib import Path

HERE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent  # map met uitkomsten.json
fails = []


def ok(c, msg):
    print(("  OK   " if c else "  FOUT ") + msg)
    if not c:
        fails.append(msg)


def eur(s):
    s = s.replace("*", "").strip()
    neg = s.startswith(("−", "-"))
    v = float(re.sub(r"[^\d,]", "", s).replace(",", "."))
    return -v if neg else v


def tabellen(md):
    out, cur = [], []
    for line in md.splitlines() + [""]:
        if line.startswith("|"):
            row = [c.strip() for c in line.strip().strip("|").split("|")]
            if not re.fullmatch(r"[-\s|]+", "|".join(row)):
                cur.append(row)
        elif cur:
            out.append(cur)
            cur = []
    return out


uit = json.loads((HERE / "uitkomsten.json").read_text())
for key, u in uit.items():
    print(f"\n{key}")
    md = (HERE / f"energieplan-huishouden-{key}.md").read_text(encoding="utf-8")
    T = tabellen(md)
    beg = next(t for t in T if t[0][0] == "Post")
    ex = sum(eur(r[1]) for r in beg[1:-1])
    inc = sum(eur(r[3]) for r in beg[1:-1])
    ok(abs(ex - eur(beg[-1][1])) < 0.01 and abs(inc - eur(beg[-1][3])) < 0.01, f"begroting telt op: {ex:.2f} excl., {inc:.2f} incl.")
    for r in beg[1:-1]:
        b = int(r[2].rstrip("%")) / 100
        ok(abs(round(eur(r[1]) * (1 + b), 2) - eur(r[3])) < 0.01, f"  btw {r[2]}: {r[0][:45]}")
    ok(abs(inc - u["inv"]) < 0.01, "investering = uitkomsten.json")
    jt = next(t for t in T if t[0][0] == "Per jaar")
    names = [r[0].replace("*", "") for r in jt]
    bi, ni = names.index("Bruto per jaar"), names.index("Netto per jaar")
    for k in (1, 2, 3):
        bruto = sum(eur(r[k]) for r in jt[1:bi])
        netto = bruto + sum(eur(r[k]) for r in jt[bi + 1:ni])
        ok(bruto == eur(jt[bi][k]) and netto == eur(jt[ni][k]) and netto == u["netto"][k - 1],
           f"{jt[0][k]}: bruto {bruto:.0f}, netto {netto:.0f}")
        ok(f"{u['inv'] / netto:.1f}".replace(".", ",") == u["jaren"][k - 1], f"  terugverdientijd {u['jaren'][k - 1]} jaar")
    ot = next(t for t in T if t[0][0] == "Onderdeel")
    ok(abs(sum(eur(r[1]) for r in ot[1:-1]) - u["inv"]) < 0.01, "investering per onderdeel telt op")
    ok(sum(eur(r[2]) for r in ot[1:-1]) == u["netto"][1], "netto per onderdeel telt op")
    for r in ot[1:-1]:
        ok(r[3] == f"{eur(r[1]) / eur(r[2]):.1f}".replace(".", ",") + " jaar", f"  {r[0][:30]}: {r[3]}")

print()
if fails:
    print(f"{len(fails)} fout(en)")
    sys.exit(1)
print("Alle controles geslaagd.")
