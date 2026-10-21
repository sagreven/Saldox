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
    ("cassette-5x4-4.5cm", 5, 4, 4),
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

# hoe ver de nokjes echt voorbij het voetvlak (18,6 mm uit het midden van een
# vak) steken; minder dan 0,3 mm valt weg in de printtolerantie (oude versie:
# 0,2 en 0,15 mm, klikte geprint niet)
def ingrijping(m, x, y, z):
    loc, _, _ = m.ray.intersects_location([[x, y, z]], [[1, 0, 0]])
    return 18.6 - min(loc[:, 0] - x)
b11 = laad("bakje-1x1-heel.stl")
k = ingrijping(b11, 0, 0, 35 + 2.2)
check("E4", "nokjes stapelrand grijpen ver genoeg in", 0.3 <= k <= 0.8, f"{k:.2f} mm")
k = ingrijping(bp, -2 * G, -G / 2, 2.2)
check("E5", "nokjes Gridfinity-bodem grijpen ver genoeg in", 0.25 <= k <= 0.8, f"{k:.2f} mm")
k = ingrijping(onder, x, y, C_FLOOR + 2.2)
check("E5", "nokjes ingebouwde bodem grijpen ver genoeg in", 0.25 <= k <= 0.8, f"{k:.2f} mm")

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
for variant, onderbak, frame_d, z_inleg in [
        ("vlak + losse bodem", "cassette-5x4-4.5cm-krimptang-vlak-onderbak.stl", 83.75, C_FLOOR),
        ("ingebouwde bodem achterin", "cassette-5x4-4.5cm-krimptang-onderbak.stl", 81.75, C_FLOOR),
        ("bovenop volledige Gridfinity", "cassette-5x4-4.5cm-onderbak.stl", 83.75, C_FLOOR + BP)]:
    inleg_f = "inleg-krimptang-5x2.stl" if frame_d == 83.75 else "inleg-krimptang-5x2-ingebouwd.stl"
    yc = -84.0 + frame_d / 2
    inleg = verplaatst(laad(inleg_f), 0, yc, z_inleg)
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

# ---------- H: bakjes 2x2 ----------

gen = os.path.join(HIER, "generator.scad")
onder = laad("cassette-5x4-4.5cm-onderbak.stl")
h_body = onder.bounds[1][2] - KR
klep, plafond = klep_dicht(laad("cassette-5x4-4.5cm-deksel.stl"), h_body)
xc, yc = (vak(0, 2, 5, 4)[0] + vak(1, 2, 5, 4)[0]) / 2, (vak(0, 2, 5, 4)[1] + vak(0, 3, 5, 4)[1]) / 2
for f, vakken, hu, vx, vy in [("bakje-2x2-vakjes-heel.stl", "per_vak", 5, 2, 2),
                              ("bakje-2x2-2vakjes-heel.stl", "eigen", 5, 2, 1),
                              ("bakje-2x2-vakjes-half.stl", "per_vak", 2.5, 2, 2),
                              ("bakje-2x2-open-half.stl", "open", 2.5, 1, 1)]:
    b = laad(f)
    Hb = hu * 7
    hoog = 39.4 if hu == 5 else 21.9
    e = b.extents
    check("H1", f"{f}: dicht, 83,5 x 83,5 x {hoog} mm",
          b.is_watertight and abs(e[0] - 83.5) < 0.05 and abs(e[1] - 83.5) < 0.05 and abs(e[2] - hoog) < 0.05,
          f"{e[0]:.2f} x {e[1]:.2f} x {e[2]:.2f} mm")
    stapel = [verplaatst(b, xc, yc, C_FLOOR)]
    if hu == 2.5:
        stapel.append(verplaatst(b, xc, yc, C_FLOOR + Hb))
    bots = sum(overlap(m, onder) + overlap(m, klep) for m in stapel)
    top = max(m.bounds[1][2] for m in stapel)
    check("H2", f"{f}: past in cassette 5x4{' (2 gestapeld)' if hu == 2.5 else ''}, klep dicht",
          bots < 0.1 and plafond - top >= 0.4, f"overlap {bots:.2f} mm3, ruimte {plafond - top:.2f} mm")
    zit = overlap(onder, verplaatst(b, xc, yc, C_FLOOR))
    til = overlap(onder, verplaatst(b, xc, yc, C_FLOOR + LIFT))
    check("H3", f"{f}: klikt in de cassette", zit < 0.1 and til > 0.5, f"geplaatst {zit:.2f}, opgetild {til:.2f} mm3")
    zit = overlap(b, verplaatst(b, 0, 0, Hb))
    til = overlap(b, verplaatst(b, 0, 0, Hb + LIFT))
    check("H4", f"{f}: klikt op een gelijk bakje", zit < 0.1 and til > 0.5, f"geplaatst {zit:.2f}, opgetild {til:.2f} mm3")
    # schuifdeksel: dezelfde instellingen als het bakje, zonder breekbare steuntjes
    params = (f'onderdeel="geen"; gx=2; gy=2; hu={hu}; vakken="{vakken}"; '
              f"vakjes_x={vx}; vakjes_y={vy}; steunen=0;\n")
    kop = f"include <{gen}>\n"
    bak = scad_code(kop + params + "bakje();\n", f"h_bak_{f}")
    dek = scad_code(kop + params + "schuifdeksel_dicht();\n", f"h_dek_{f}")
    check("H5", f"{f}: schuifdeksel past dicht", overlap(bak, dek) < 0.05)
    stappen = [overlap(bak, verplaatst(dek, s_)) for s_ in np.arange(2, 2 * G + 2, 4)]
    check("H6", f"{f}: schuifdeksel schuift er helemaal uit", max(stappen) < 0.05, f"grootste overlap {max(stappen):.2f} mm3")
    gelijk = abs(dek.extents[0] - laad("schuifdeksel-2x2.stl").extents[0]) < 0.05 and \
        abs(dek.extents[1] - laad("schuifdeksel-2x2.stl").extents[1]) < 0.05
    check("H7", f"{f}: schuifdeksel-2x2.stl is de juiste deksel", gelijk,
          f"{dek.extents[0]:.2f} x {dek.extents[1]:.2f} mm")
    z_g0 = Hb - 1.0 - 1.5 - 0.1        # onderkant groef = onderkant deksel (ceil_t, lid_t, lid_fit)
    if vakken != "open":
        # tussenschot onder de deksel: eerste materiaal van boven op het schot
        loc, _, _ = b.ray.intersects_location([[0, 10, Hb - 0.5]], [[0, 0, -1]]) if vx == 2 else \
            b.ray.intersects_location([[10, 0, Hb - 0.5]], [[0, 0, -1]])
        schot = max(loc[:, 2])
        check("H8", f"{f}: deksel rust op de tussenschotten (vakjes apart dicht)", abs(schot - z_g0) < 0.05,
              f"bovenkant schot {schot:.2f}, onderkant deksel {z_g0:.2f} mm")
    # steuntjes in de sleuf (deksel schuift naar rechts, +x)
    loc, _, _ = b.ray.intersects_location([[83.5 / 2 - 0.8, -60, z_g0 + 0.8]], [[0, 1, 0]])
    n = len(loc) // 2 - 2              # min de wandhoekjes aan beide uiteinden van de sleuf
    check("H9", f"{f}: breekbare steuntjes in de sleuf (2 per vak)", n == 4, f"{n} steuntjes")

# ---------- I: dozen met grote schuifdeksel ----------

onder = laad("cassette-5x4-4.5cm-onderbak.stl")
h_body = onder.bounds[1][2] - KR
klep, plafond = klep_dicht(laad("cassette-5x4-4.5cm-deksel.stl"), h_body)
bp = laad("baseplate-5x2.stl")
for n in (2, 3):
    bx = laad(f"doos-{n}x1-half.stl")
    dk = laad(f"doos-dop-{n}x1-half.stl")
    W, Ht = n * G - 0.5, 21.9
    e = bx.extents
    check("I1", f"doos {n}x1 half: dicht model, maat", bx.is_watertight and len(bx.split()) == 1
          and abs(e[0] - W) < 0.05 and abs(e[1] - 41.5) < 0.05,
          f"{e[0]:.2f} x {e[1]:.2f} x {e[2]:.2f} mm")
    check("I1", f"dop {n}x1: dicht model", dk.is_watertight and len(dk.split()) == 1,
          f"{dk.extents[0]:.2f} x {dk.extents[1]:.2f} x {dk.extents[2]:.2f} mm")
    # dop is ondersteboven geprint: terugdraaien, bovenkant op Ht
    dicht = dk.copy()
    dicht.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    dicht.apply_translation([0, 0, Ht])
    zit = overlap(bx, dicht)
    check("I2", f"doos {n}x1: dop past dicht", zit < 0.01, f"overlap {zit:.3f} mm3")
    sb = dicht.bounds
    check("I3", f"doos {n}x1: dop gelijk met de buitenkant, hoogte {Ht} mm",
          abs(sb[1][2] - Ht) < 0.05 and abs(dicht.extents[0] - W) < 0.05 and abs(dicht.extents[1] - 41.5) < 0.05,
          f"{dicht.extents[0]:.2f} x {dicht.extents[1]:.2f}, bovenkant {sb[1][2]:.2f} mm")
    til = overlap(bx, verplaatst(dicht, 0, 0, 0.6))
    check("I4", f"doos {n}x1: dop klikt vast (0,6 mm opgetild: klikrandje)", til > 1, f"{til:.1f} mm3")
    # hoe ver het klikrandje voorbij de binnenkant van de dop steekt
    loc, _, _ = bx.ray.intersects_location([[W, 0, Ht - 8 + 2]], [[-1, 0, 0]])
    rand = max(loc[:, 0])
    loc, _, _ = dicht.ray.intersects_location([[0, 0, Ht - 8 + 0.8]], [[1, 0, 0]])
    binnen = min(loc[:, 0])
    k = rand - binnen
    check("I5", f"doos {n}x1: klikrandje grijpt ver genoeg in", 0.3 <= k <= 0.6, f"{k:.2f} mm")
    x = -2 * G + (n - 1) * G / 2
    zit = overlap(bp, verplaatst(bx, x, -G / 2, 0))
    lift = overlap(bp, verplaatst(bx, x, -G / 2, LIFT))
    check("I6", f"doos {n}x1: klikt in de Gridfinity-bodem", zit < 0.1 and lift > 0.5,
          f"geplaatst {zit:.2f}, opgetild {lift:.2f} mm3")
    zit = overlap(half, verplaatst(bx, (n - 1) * G / 2, 0, 17.5))
    lift = overlap(half, verplaatst(bx, (n - 1) * G / 2, 0, 17.5 + LIFT))
    check("I7", f"doos {n}x1: klikt op een half bakje", zit < 0.1 and lift > 0.5,
          f"geplaatst {zit:.2f}, opgetild {lift:.2f} mm3")
    # in de cassette 5x4 op een half bakje, klep dicht
    x, y = vak(0, 3, 5, 4)
    x += (n - 1) * G / 2
    stapel = [verplaatst(half, x - (n - 1) * G / 2, y, C_FLOOR), verplaatst(bx, x, y, C_FLOOR + 17.5),
              verplaatst(dicht, x, y, C_FLOOR + 17.5)]
    if n == 2:
        stapel.append(verplaatst(half, x + G / 2, y, C_FLOOR))
    botsing = sum(overlap(b, onder) + overlap(b, klep) for b in stapel)
    ruimte = plafond - max(b.bounds[1][2] for b in stapel)
    check("I8", f"doos {n}x1 met dop: op een half bakje in de cassette, klep dicht", botsing < 0.1 and ruimte >= 0.4,
          f"overlap {botsing:.2f} mm3, ruimte {ruimte:.2f} mm")

# ---------- rapport ----------

breed = max(len(r[1]) for r in resultaten)
fout = 0
for eis, oms, res, w in resultaten:
    print(f"{eis:3} {res:4}  {oms.ljust(breed)}  {w}")
    fout += res == "FOUT"
print(f"\n{len(resultaten)} controles, {fout} fout")
sys.exit(1 if fout else 0)
