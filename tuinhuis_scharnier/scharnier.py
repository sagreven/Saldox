"""Verstelbaar opdekdeur-scharnier voor het tuinhuisje (3D-print).

Het scharnier vervangt een inboor-paumelle: het deurdeel heeft een pen die in
het bestaande paumelle-gat in de deurkant valt, en wordt daarnaast met
schroeven vastgezet. Het kozijndeel wordt met schroeven door sleufgaten op de
zijkant van het kozijn gezet (grof in hoogte verstelbaar). De scharnieras is
een M8 inbusbout die van onderen in een ingesloten moer draait; de deur hangt
op de punt van die bout, dus door de bout te draaien stel je de deur fijn in
hoogte af (borgen met een contramoer).

Assenstelsel (mm): z omhoog, scharnieras op (AX, 0). De deurkant en de
kozijnzijkant liggen in het vlak x = 0; de deur zit op y = 0..DOOR_T, het
kozijn op y < 0.

Gebruik:  python3 scharnier.py    -> schrijft STL's naar ./stl
"""

import math
import os

import numpy as np
import trimesh
from manifold3d import Manifold, Mesh

# ---------------------------------------------------------------- parameters
DOOR_T = 20.0        # dikte van de deur (breedte van de deurkant)
HOLE_D = 10.0        # diameter van het bestaande paumelle-gat in de deur
HOLE_DEPTH = 25.0    # diepte van dat gat
PEG_CLEAR = 0.4      # speling pen in gat
PEG_Z = 22.0         # hoogte pen t.o.v. midden scharnier

PLATE_T = 5.0        # dikte van de flenzen
KNUCKLE_R = 11.0     # straal van de scharnierknokkels (diameter 22)
AX = PLATE_T + KNUCKLE_R + 1.0   # as 1 mm vrij van de flenzen
GAP = 6.0            # nominale spleet tussen de knokkels (instelbereik +-4 mm)
FLANGE_H = 90.0      # hoogte van de flenzen
KNUCKLE_H = FLANGE_H / 2 - GAP / 2   # knokkel loopt door tot de flensrand
FRAME_W = 50.0       # breedte van de kozijnflens (langs de kozijnzijkant)

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


def screw_hole_x(y, z, x_face=PLATE_T, x_out=60.0):
    """Verzonken schroefgat door een flens (kop aan de buitenkant x_face),
    met een kopvrije boring tot x_out zodat schroeven onder de knokkelbrug
    bereikbaar blijven."""
    rs, rh = SCREW_D / 2, SCREW_HEAD_D / 2 + 0.25
    cs_depth = rh - rs
    return (xcyl(rs, -50, x_face, y, z)
            + xcyl(rs, x_face - cs_depth, x_face + 0.01, y, z, r_end=rh)
            + xcyl(rh, x_face, x_out, y, z))


def zslot(y, z, w=4.8, length=SLOT_LEN):
    r = w / 2
    a = xcyl(r, -1, PLATE_T + 1, y, z - (length / 2 - r))
    b = xcyl(r, -1, PLATE_T + 1, y, z + (length / 2 - r))
    return Manifold.batch_hull([a, b])


# ---------------------------------------------------------------- parts
def door_part():
    """Deurdeel: flens op de deurkant + bovenste knokkel."""
    k0, k1 = GAP / 2, GAP / 2 + KNUCKLE_H
    flange = box(0, PLATE_T, 0, DOOR_T, -FLANGE_H / 2, FLANGE_H / 2)
    bridge = box(0, AX, 0, KNUCKLE_R, k0, k1)
    knuckle = zcyl(KNUCKLE_R, k0, k1, AX, 0)
    body = flange + bridge + knuckle

    # pen in het bestaande paumelle-gat
    pr = (HOLE_D - PEG_CLEAR) / 2
    yc = DOOR_T / 2
    peg = xcyl(pr, -(HOLE_DEPTH - 2), 0.01, yc, PEG_Z)
    tip = xcyl(pr - 1.0, -(HOLE_DEPTH - 1), -(HOLE_DEPTH - 2) + 0.01, yc, PEG_Z, r_end=pr)
    body = body + peg + tip

    # pen boven (onder de knokkelbrug, draagt de deur op afschuiving),
    # schroeven onder de brug zodat ze bereikbaar zijn
    holes = [screw_hole_x(yc, -14), screw_hole_x(yc, -36)]
    # blinde boring voor de M8 bout (bovenkant dicht: deur hangt op de boutpunt)
    bore = zcyl(BOLT_CLEAR / 2, k0 - 1, k0 + BORE_DEPTH, AX, 0)
    chamfer = zcyl(BOLT_CLEAR / 2 + 1.2, k0 - 0.01, k0 + 1.2, AX, 0, r_top=BOLT_CLEAR / 2)
    for h in holes + [bore, chamfer]:
        body = body - h
    return body


def frame_part():
    """Kozijndeel: flens met sleufgaten op de kozijnzijkant + onderste knokkel
    met ingesloten M8 moer."""
    k0, k1 = -GAP / 2 - KNUCKLE_H, -GAP / 2
    flange = box(0, PLATE_T, -FRAME_W, 0, -FLANGE_H / 2, FLANGE_H / 2)
    bridge = box(0, AX, -KNUCKLE_R, 0, k0, k1)
    knuckle = zcyl(KNUCKLE_R, k0, k1, AX, 0)
    body = flange + bridge + knuckle

    bore = zcyl(BOLT_CLEAR / 2, k0 - 1, k1 + 1, AX, 0)
    nut_r = NUT_AF / math.sqrt(3)  # omgeschreven straal van de zeskant
    nut = Manifold.cylinder(NUT_H + 1, nut_r, nut_r, 6).rotate([0, 0, 30]) \
        .translate([AX, 0, k1 - NUT_H])
    slots = [zslot(-24, 28), zslot(-40, 0), zslot(-24, -28), zslot(-40, -30), zslot(-40, 30)]
    for h in [bore, nut] + slots:
        body = body - h
    return body


# ---------------------------------------------------------------- hardware (alleen voor de render)
def bolt(tip_z):
    """M8 inbusbout DIN 912 M8x80, punt op tip_z."""
    L = 80.0
    shank = zcyl(4.0, tip_z - L, tip_z, AX, 0, seg=32)
    head = zcyl(6.5, tip_z - L - 8, tip_z - L, AX, 0, seg=40) - \
        Manifold.cylinder(5, 3.5, 3.5, 6).translate([AX, 0, tip_z - L - 8.01])
    return shank + head


def nut(z0):
    r = 13.0 / math.sqrt(3)
    return Manifold.cylinder(6.5, r, r, 6).rotate([0, 0, 30]).translate([AX, 0, z0]) - \
        zcyl(4.0, z0 - 1, z0 + 8, AX, 0, seg=32)


# ---------------------------------------------------------------- export
def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3],
                           np.asarray(mesh.tri_verts), process=True)


def mirrored(m):
    """Spiegelbeeld voor een deur die aan de andere kant draait."""
    return m.mirror([1, 0, 0])


def print_orient(m, upside_down):
    """Printstand: knokkel en flens staan rechtop met hun gezamenlijke
    eindvlak op het bed, zodat er geen support nodig is."""
    if upside_down:
        m = m.rotate([180, 0, 0])
    lo = m.bounding_box()[2]
    return m.translate([0, 0, -lo])


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "stl")
    os.makedirs(out, exist_ok=True)
    parts = {
        "deurdeel_rechts": door_part(),
        "kozijndeel_rechts": frame_part(),
        "deurdeel_links": mirrored(door_part()),
        "kozijndeel_links": mirrored(frame_part()),
    }
    for name, m in parts.items():
        tm = to_trimesh(print_orient(m, name.startswith("deur")))
        assert tm.is_watertight, name
        tm.export(os.path.join(out, f"{name}.stl"))
        print(f"{name:20s} {m.volume() / 1000:6.1f} cm3  {m.num_tri():6d} tri  "
              f"bbox {np.round(tm.extents, 1)}")


if __name__ == "__main__":
    main()
