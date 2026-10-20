#!/usr/bin/env python3
"""Validatie van het Gridfinity-draagsysteem.

Controleert de STL-bestanden in stl/ tegen de eisen in VALIDATIE.md: zijn de
modellen dicht, kloppen de maten, passen bakjes, cassettes, deksels en de
krimptang-inleg in elkaar zonder te botsen, en grijpen de klikken en de
houders van de krimptang echt in.

Gebruik:  python3 valideer.py          (vanuit deze map; OpenSCAD moet
                                        geinstalleerd zijn)
Nodig:    pip install trimesh manifold3d rtree numpy
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
import trimesh

HIER = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(HIER, "stl")
TMP = tempfile.mkdtemp(prefix="valideer-")

G = 42.0          # Gridfinity-raster
C_FLOOR = 3.2     # bodem cassette met magneten
BP = 4.65         # hoogte Gridfinity-bodem
KR = 3.5          # straal scharnierknokkel (bovenkant onderbak = H_body + KR)
LATCH = 12.0      # lengte klikbeugel onder de scheidingslijn
TOP_T = 2.0       # dikte bovenkant klep
LIFT = 0.6        # hoe ver een bakje omhoog wordt getild voor de kliktest

resultaten = []


def check(eis, omschrijving, ok, waarde=""):
    resultaten.append((eis, omschrijving, "OK" if ok else "FOUT", waarde))


# ---------- hulpfuncties ----------

def laad(naam):
    return trimesh.load(os.path.join(STL, naam))


def scad(bestand, uit, **params):
    """Render een .scad naar een STL in de tijdelijke map."""
    pad = os.path.join(TMP, uit)
    args = ["openscad", "-q", "-o", pad]
    for k, v in params.items():
        args += ["-D", f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}"]
    subprocess.run(args + [os.path.join(HIER, bestand)], check=True)
    return trimesh.load(pad)


def scad_code(code, uit):
    """Render een stukje OpenSCAD dat generator.scad gebruikt."""
    src = os.path.join(TMP, uit + ".scad")
    with open(src, "w") as f:
        f.write(code)
    pad = os.path.join(TMP, uit)
    subprocess.run(["openscad", "-q", "-o", pad, src], check=True)
    return trimesh.load(pad)


def verplaatst(m, x=0, y=0, z=0):
    m = m.copy()
    m.apply_translation([x, y, z])
    return m


def overlap(a, b):
    """Volume (mm3) waarin twee modellen elkaar overlappen."""
    i = trimesh.boolean.intersection([a, b], engine="manifold")
    return 0.0 if i.is_empty else abs(i.volume)


def doos(x0, x1, y0, y1, z0, z1):
    b = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def vloer(m, x, y):
    """Hoogte van het eerste materiaal van bovenaf op punt (x, y)."""
    loc, _, _ = m.ray.intersects_location([[x, y, 500]], [[0, 0, -1]])
    return max(loc[:, 2]) if len(loc) else None


def klep_dicht(klep, h_body):
    """Klep-STL (ondersteboven geprint) terug in gesloten stand."""
    d_lid_h = klep.extents[2] - LATCH
    k = klep.copy()
    k.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    k.apply_translation([0, 0, h_body + d_lid_h])
    return k, h_body + d_lid_h - TOP_T          # klep, plafond binnenin


def vak(i, j, gx, gy):
    return (i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G


# ---------- A: integriteit en maten ----------

for f in sorted(os.listdir(STL)):
    if not f.endswith(".stl"):
        continue
    m = laad(f)
    delen = len(m.split(only_watertight=False))
    check("A1", f"{f} is een dicht model uit één stuk", m.is_watertight and delen == 1,
          f"dicht={m.is_watertight}, delen={delen}")

for f, n, h in [("bakje-1x1-heel.stl", (1, 1), 39.4), ("bakje-1x1-half.stl", (1, 1), 21.9),
                ("bakje-2x1-vakjes-heel.stl", (2, 1), 39.4), ("bakje-1x2-vakjes-heel.stl", (1, 2), 39.4),
                ("bakje-2x2-vakjes-half.stl", (2, 2), 21.9)]:
    e = laad(f).extents
    ok = abs(e[0] - (n[0] * G - 0.5)) < 0.05 and abs(e[1] - (n[1] * G - 0.5)) < 0.05 and abs(e[2] - h) < 0.05
    check("A2", f"{f}: maat {n[0]}x{n[1]} vakken, {h} mm hoog", ok,
          f"{e[0]:.2f} x {e[1]:.2f} x {e[2]:.2f} mm")

# ---------- C: vloer van de cassettes ----------

cassettes = [
    # bestand, gx, gy, Gridfinity-rijen (vanaf achter; 0 = geen)
    ("cassette-2x2-4.5cm-schroeven", 2, 2, 2),
    ("cassette-4x2-4.5cm", 4, 2, 2),
    ("cassette-4x2-8.0cm", 4, 2, 2),
    ("cassette-5x2-4.5cm-schroevendraaiers", 5, 2, 0),
    ("cassette-5x4-4.5cm-krimptang", 5, 4, 2),
    ("cassette-5x4-4.5cm-krimptang-vlak", 5, 4, 0),
]
for naam, gx, gy, rijen in cassettes:
    m = laad(naam + "-onderbak.stl")
    for j in range(gy):
        x, y = vak(0, j, gx, gy)
        gf = j >= gy - rijen
        v = vloer(m, x, y)
        check("C1", f"{naam}: vloer in vak rij {j} op {C_FLOOR} mm", abs(v - C_FLOOR) < 0.05, f"{v:.2f} mm")
        if gf:
            r = vloer(m, x + G / 2, y)
            check("C2", f"{naam}: Gridfinity-rand naast vak rij {j} op {C_FLOOR + BP:.2f} mm",
                  abs(r - (C_FLOOR + BP)) < 0.05, f"{r:.2f} mm")
            loc, _, _ = m.ray.intersects_location([[x, y, C_FLOOR + 2.2]], [[1, 0, 0]])
            wand = min(loc[:, 0] - x)
            check("C3", f"{naam}: klik-nokje in vak rij {j}", wand < 18.8, f"wand op {wand:.2f} mm (zonder nokje 18.85)")

# ---------- D: bakjes in de cassettes, klep dicht ----------

heel = laad("bakje-1x1-heel.stl")
half = laad("bakje-1x1-half.stl")
for naam, gx, gy, rijen in cassettes:
    onder = laad(naam + "-onderbak.stl")
    h_body = onder.bounds[1][2] - KR
    klep, plafond = klep_dicht(laad(naam.replace("-vlak", "") + "-deksel.stl"), h_body)
    check("D1", f"{naam}: klep sluit op onderbak", overlap(onder, klep) < 0.1)
    hoog = "8.0cm" in naam
    x, y = vak(0, gy - 1, gx, gy)
    stapel = [verplaatst(heel, x, y, C_FLOOR)]
    if hoog:
        stapel.append(verplaatst(heel, x, y, C_FLOOR + 35))
    x2, y2 = vak(1, gy - 1, gx, gy)
    stapel += [verplaatst(half, x2, y2, C_FLOOR), verplaatst(half, x2, y2, C_FLOOR + 17.5)]
    if hoog:
        stapel += [verplaatst(half, x2, y2, C_FLOOR + 35), verplaatst(half, x2, y2, C_FLOOR + 52.5)]
    botsing = sum(overlap(b, onder) + overlap(b, klep) for b in stapel)
    top = max(b.bounds[1][2] for b in stapel)
    check("D2", f"{naam}: hele en halve bakjes passen, klep dicht", botsing < 0.1, f"overlap {botsing:.2f} mm3")
    check("D3", f"{naam}: ruimte boven de bakjes 0,4 - 3 mm", 0.4 <= plafond - top <= 3.0,
          f"{plafond - top:.2f} mm")

# ---------- E: klikken ----------

onder = laad("cassette-5x4-4.5cm-krimptang-onderbak.stl")
x, y = vak(0, 3, 5, 4)
for naam, ond in [("ingebouwde bodem krimptang-cassette", onder)]:
    zit = overlap(ond, verplaatst(heel, x, y, C_FLOOR))
    til = overlap(ond, verplaatst(heel, x, y, C_FLOOR + LIFT))
    check("E1", f"bakje klikt in {naam}", zit < 0.1 and til > 0.5, f"geplaatst {zit:.2f}, opgetild {til:.2f} mm3")
bp = laad("baseplate-5x2.stl")
zit = overlap(bp, heel.copy())
til = overlap(bp, verplaatst(heel, -2 * G, -G / 2, LIFT))
zit = overlap(bp, verplaatst(heel, -2 * G, -G / 2, 0))
check("E2", "bakje klikt in losse Gridfinity-bodem", zit < 0.1 and til > 0.5, f"geplaatst {zit:.2f}, opgetild {til:.2f} mm3")
zit = overlap(half, verplaatst(half, 0, 0, 17.5))
til = overlap(half, verplaatst(half, 0, 0, 17.5 + LIFT))
check("E3", "bakje klikt op een ander bakje", zit < 0.1 and til > 0.5, f"geplaatst {zit:.2f}, opgetild {til:.2f} mm3")

# ---------- F: schuifdeksel ----------

for gx, gy, hu in [(1, 1, 5), (1, 2, 5), (2, 2, 2.5)]:
    gen = os.path.join(HIER, "generator.scad")
    kop = f'include <{gen}>\n'
    params = f"onderdeel=\"geen\"; gx={gx}; gy={gy}; hu={hu}; steunen=0;\n"
    # instellingen ná de include: in OpenSCAD wint de laatste toewijzing
    bak = scad_code(kop + params + "bakje();\n", f"bak{gx}{gy}{hu}.stl")
    dek = scad_code(kop + params + "schuifdeksel_dicht();\n", f"dek{gx}{gy}{hu}.stl")
    dicht = overlap(bak, dek)
    check("F1", f"schuifdeksel {gx}x{gy} past dicht in de groef", dicht < 0.05, f"overlap {dicht:.2f} mm3")
    w = gx * G
    stappen = [overlap(bak, verplaatst(dek, s)) for s in np.arange(2, w + 2, 4)]
    check("F2", f"schuifdeksel {gx}x{gy} schuift er helemaal uit", max(stappen) < 0.05,
          f"grootste overlap {max(stappen):.2f} mm3")

# ---------- G: krimptang-inleg ----------

ink = os.path.join(HIER, "krimptang_inleg.scad")
for variant, onderbak, frame_d in [("vlak + losse bodem", "cassette-5x4-4.5cm-krimptang-vlak-onderbak.stl", 83.75),
                                   ("ingebouwde bodem", "cassette-5x4-4.5cm-krimptang-onderbak.stl", 81.75)]:
    inleg_f = "inleg-krimptang-5x2.stl" if frame_d == 83.75 else "inleg-krimptang-5x2-ingebouwd.stl"
    yc = -84.0 + frame_d / 2
    inleg = verplaatst(laad(inleg_f), 0, yc, C_FLOOR)
    ond = laad(onderbak)
    h_body = ond.bounds[1][2] - KR
    _, plafond = klep_dicht(laad("cassette-5x4-4.5cm-krimptang-deksel.stl"), h_body)
    delen = [ond]
    if "vlak" in onderbak:
        delen.append(verplaatst(bp, 0, 42, C_FLOOR))
    botsing = sum(overlap(inleg, d) for d in delen)
    check("G1", f"inleg past in cassette ({variant})", botsing < 0.1, f"overlap {botsing:.2f} mm3")
    check("G2", f"paddenstoel blijft onder de klep ({variant})", inleg.bounds[1][2] <= plafond - 1,
          f"bovenkant {inleg.bounds[1][2]:.1f}, plafond {plafond:.1f} mm")

inleg = laad("inleg-krimptang-5x2.stl")
tang24 = scad("krimptang_inleg.scad", "tang24.stl", toon="tang", tang_h=24)
L = 181.0
links = doos(-120, -L / 2 + 5, -60, 60, 0, 40)
rechts = doos(L / 2 - 5, 120, -60, 60, 0, 40)
pad = doos(0.23 * L - 10, 0.23 * L + 10, -30, 30, 0, 40)
v = overlap(trimesh.boolean.intersection([inleg, links], engine="manifold"), tang24)
check("G3", "boog bij de kop drukt op de tang", v > 1, f"{v:.1f} mm3 voorspanning")
v = overlap(trimesh.boolean.intersection([inleg, rechts], engine="manifold"), tang24)
check("G4", "bogen bij de handvatten drukken op de tang", v > 1, f"{v:.1f} mm3 voorspanning")
# onder de onderste klik-tand: handvat_hoogte - (niveaus-1)/2 * stap - kleinste tand
# = 24 - 2 - 1,5 = 20,5 mm; daarboven drukken de tanden bewust op de afgeronde rand
tang_laag = scad("krimptang_inleg.scad", "tang_laag.stl", toon="tang", tang_h=20.5)
v = overlap(trimesh.boolean.intersection([inleg, pad], engine="manifold"), tang_laag)
check("G5", "pootjes paddenstoel raken de handvatten niet onder de klik-tanden", v < 0.1, f"{v:.2f} mm3")
tang_hoog = scad("krimptang_inleg.scad", "tang_hoog.stl", toon="tang", tang_h=24 + 5)
v = overlap(trimesh.boolean.intersection([inleg, pad], engine="manifold"), tang_hoog)
check("G6", "haakjes paddenstoel grijpen over de handvatten", v > 1, f"{v:.1f} mm3")

# ---------- rapport ----------

breed = max(len(r[1]) for r in resultaten)
fout = 0
for eis, oms, res, w in resultaten:
    print(f"{eis:3} {res:4}  {oms.ljust(breed)}  {w}")
    fout += res == "FOUT"
print(f"\n{len(resultaten)} controles, {fout} fout")
sys.exit(1 if fout else 0)
