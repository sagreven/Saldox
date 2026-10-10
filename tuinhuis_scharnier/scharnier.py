"""Verstelbaar opdekdeur-scharnier voor de dubbele deuren van het tuinhuis
(3D-print).

Het scharnier vervangt de paumelles: het deurdeel heeft twee pennen die in de
bestaande paumelle-gaten in de deurkant vallen (zelfde diameter, diepte en
hart-op-hart afstand als de paumelle-pennen) en wordt daarnaast met schroeven
vastgezet. Het kozijndeel wordt met schroeven door sleufgaten op de VOORKANT
van het kozijn/de gevel naast de deur gezet (grof in hoogte verstelbaar). De
scharnieras is een M8 inbusbout die van onderen in een ingesloten moer draait;
de deur hangt op de punt van die bout, dus door de bout te draaien stel je de
deur fijn in hoogte af (borgen met een contramoer). De deur is uit te tillen.

Assenstelsel (mm), van buiten gezien: z omhoog, y naar buiten. De deur zit op
x < 0, y = 0..DOOR_T (opdek: de achterkant ligt in het gevelvlak y = 0), de
deurkant met de paumelle-gaten in het vlak x = 0. Scharnieras op (AX, AY),
voor het gevelvlak.

Gebruik:  python3 scharnier.py    -> schrijft STL's naar ./stl
"""

import math
import os

import numpy as np
import trimesh
from manifold3d import Manifold

# ---------------------------------------------------------------- parameters
# >>> meet deze aan je deur / de oude paumelle (kant die in de muur gaat) <<<
DOOR_T = 20.0        # dikte van de deur (breedte van de deurkant)
HOLE_D = 10.0        # diameter van de paumelle-gaten in de deurkant
HOLE_DEPTH = 25.0    # diepte van die gaten
HOLE_PITCH = 50.0    # hart-op-hart afstand tussen de twee gaten
HOLE_Y = DOOR_T / 2  # afstand hart gat tot achterkant deur
PEG_CLEAR = 0.4      # speling pen in gat
PEG_TOP_Z = 25.0     # hoogte bovenste pen t.o.v. midden scharnier

PLATE_T = 5.0        # dikte van de flenzen
KNUCKLE_R = 11.0     # straal van de scharnierknokkels (diameter 22)
AX = PLATE_T + KNUCKLE_R + 1.0   # as 1 mm naast de deurflens
AY = PLATE_T + KNUCKLE_R + 1.0   # as 1 mm voor de kozijnplaat
GAP = 6.0            # nominale spleet tussen de knokkels (instelbereik +-4 mm)
FLANGE_H = 90.0      # hoogte van de knokkelzone
KNUCKLE_H = FLANGE_H / 2 - GAP / 2   # knokkel loopt door tot de flensrand
DOOR_FLANGE_LO = -55.0   # deurflens loopt verder omlaag voor de schroeven
FRAME_W = 50.0       # breedte kozijnplaat naast de knokkel

BOLT_CLEAR = 8.6     # boring voor M8
BORE_DEPTH = 26.0    # blinde boring in deurknokkel (bout draagt de deur)
NUT_AF = 13.3        # M8 moer sleutelwijdte + speling
NUT_H = 7.0

SCREW_D = 4.5        # houtschroef 4-4,5 mm
SCREW_HEAD_D = 9.0
SLOT_LEN = 14.0      # sleuflengte (hart-hart 9,2 mm -> +-4,6 mm)
SEG = 72


# ---------------------------------------------------------------- helpers
def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def zcyl(r, z0, z1, x=0.0, y=0.0, r_top=None, seg=SEG):
    r_top = r if r_top is None else r_top
    return Manifold.cylinder(z1 - z0, r, r_top, seg).translate([x, y, z0])


def xcyl(r, x0, x1, y, z, r_end=None, seg=SEG):
    """Cilinder langs x van x0 naar x1 (r bij x0, r_end bij x1)."""
    r_end = r if r_end is None else r_end
    c = Manifold.cylinder(x1 - x0, r, r_end, seg)        # langs +z
    return c.rotate([0, 90, 0]).translate([x0, y, z])     # z -> +x


def ycyl(r, y0, y1, x, z, r_end=None, seg=SEG):
    """Cilinder langs y van y0 naar y1."""
    r_end = r if r_end is None else r_end
    c = Manifold.cylinder(y1 - y0, r, r_end, seg)
    return c.rotate([-90, 0, 0]).translate([x, y0, z])    # z -> +y


def screw_hole_x(y, z):
    """Verzonken schroefgat door de deurflens (kop aan de buitenkant)."""
    rs, rh = SCREW_D / 2, SCREW_HEAD_D / 2 + 0.25
    return (xcyl(rs, -50, PLATE_T, y, z)
            + xcyl(rs, PLATE_T - (rh - rs), PLATE_T + 0.01, y, z, r_end=rh)
            + xcyl(rh, PLATE_T, PLATE_T + 20, y, z))


def slot_y(x, z, w=4.8, length=SLOT_LEN):
    """Verticaal sleufgat door de kozijnplaat."""
    r = w / 2
    a = ycyl(r, -1, PLATE_T + 1, x, z - (length / 2 - r))
    b = ycyl(r, -1, PLATE_T + 1, x, z + (length / 2 - r))
    return Manifold.batch_hull([a, b])


# ---------------------------------------------------------------- parts
def door_part():
    """Deurdeel: flens op de deurkant met twee pennen + bovenste knokkel."""
    k0, k1 = GAP / 2, FLANGE_H / 2
    flange = box(0, PLATE_T, 0, DOOR_T, DOOR_FLANGE_LO, k1)
    bridge = box(0, AX, PLATE_T + 1, AY, k0, k1)
    knuckle = zcyl(KNUCKLE_R, k0, k1, AX, AY)
    body = flange + bridge + knuckle

    # twee pennen in de bestaande paumelle-gaten
    pr = (HOLE_D - PEG_CLEAR) / 2
    for z in (PEG_TOP_Z, PEG_TOP_Z - HOLE_PITCH):
        body = body + xcyl(pr, -(HOLE_DEPTH - 3), 0.01, HOLE_Y, z) \
            + xcyl(pr - 1.0, -(HOLE_DEPTH - 2), -(HOLE_DEPTH - 3) + 0.01, HOLE_Y, z, r_end=pr)

    # schroeven buiten de knokkelzone en tussen/naast de pennen
    z_lo = PEG_TOP_Z - HOLE_PITCH
    screw_z = [min(-5.0, (PEG_TOP_Z + z_lo) / 2), DOOR_FLANGE_LO + 8]
    holes = [screw_hole_x(DOOR_T / 2, z) for z in screw_z]
    # blinde boring voor de M8 bout (bovenkant dicht: deur hangt op de boutpunt)
    holes.append(zcyl(BOLT_CLEAR / 2, k0 - 1, k0 + BORE_DEPTH, AX, AY))
    holes.append(zcyl(BOLT_CLEAR / 2 + 1.2, k0 - 0.01, k0 + 1.2, AX, AY, r_top=BOLT_CLEAR / 2))
    for h in holes:
        body = body - h
    return body


def frame_part():
    """Kozijndeel: plaat met sleufgaten op de voorkant van kozijn/gevel naast
    de deur + onderste knokkel met ingesloten M8 moer."""
    k0, k1 = -FLANGE_H / 2, -GAP / 2
    x0 = PLATE_T + 1
    plate = box(x0, AX + KNUCKLE_R + FRAME_W - 22, 0, PLATE_T, -FLANGE_H / 2, FLANGE_H / 2)
    bridge = box(AX - KNUCKLE_R, AX + KNUCKLE_R, 0, AY, k0, k1)
    knuckle = zcyl(KNUCKLE_R, k0, k1, AX, AY)
    body = plate + bridge + knuckle

    holes = [zcyl(BOLT_CLEAR / 2, k0 - 1, k1 + 1, AX, AY)]
    nut_r = NUT_AF / math.sqrt(3)  # omgeschreven straal van de zeskant
    holes.append(Manifold.cylinder(NUT_H + 1, nut_r, nut_r, 6).rotate([0, 0, 30])
                 .translate([AX, AY, k1 - NUT_H]))
    xa, xb = AX + KNUCKLE_R + 8, AX + KNUCKLE_R + 22
    holes += [slot_y(xa, 30), slot_y(xa, -30), slot_y(xb, 0), slot_y(xb, 30), slot_y(xb, -30)]
    for h in holes:
        body = body - h
    return body


# ---------------------------------------------------------------- hardware (alleen voor de render)
def bolt(tip_z):
    """M8 inbusbout DIN 912 M8x80, punt op tip_z."""
    L = 80.0
    shank = zcyl(4.0, tip_z - L, tip_z, AX, AY, seg=32)
    head = zcyl(6.5, tip_z - L - 8, tip_z - L, AX, AY, seg=40) - \
        Manifold.cylinder(5, 3.5, 3.5, 6).translate([AX, AY, tip_z - L - 8.01])
    return shank + head


def nut(z0):
    r = 13.0 / math.sqrt(3)
    return Manifold.cylinder(6.5, r, r, 6).rotate([0, 0, 30]).translate([AX, AY, z0]) - \
        zcyl(4.0, z0 - 1, z0 + 8, AX, AY, seg=32)


# ---------------------------------------------------------------- export
def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3],
                           np.asarray(mesh.tri_verts), process=True)


def mirrored(m):
    """Spiegelbeeld voor de deur die aan de andere kant draait."""
    return m.mirror([1, 0, 0])


def print_orient(m, upside_down):
    """Printstand: knokkel en flens hebben een gezamenlijk eindvlak op het
    bed, zodat er geen support nodig is."""
    if upside_down:
        m = m.rotate([180, 0, 0])
    lo = m.bounding_box()[2]
    return m.translate([0, 0, -lo])


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "stl")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))
    # van buiten gezien: linkerdeur scharniert links, rechterdeur rechts
    parts = {
        "deurdeel_linkerdeur": door_part(),
        "kozijndeel_linkerdeur": frame_part(),
        "deurdeel_rechterdeur": mirrored(door_part()),
        "kozijndeel_rechterdeur": mirrored(frame_part()),
    }
    for name, m in parts.items():
        tm = to_trimesh(print_orient(m, name.startswith("deur")))
        assert tm.is_watertight, name
        tm.export(os.path.join(out, f"{name}.stl"))
        print(f"{name:24s} {m.volume() / 1000:6.1f} cm3  {m.num_tri():6d} tri  "
              f"bbox {np.round(tm.extents, 1)}")


if __name__ == "__main__":
    main()
