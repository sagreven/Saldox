"""Verstelbaar opdekdeur-scharnier voor de dubbele deuren van het tuinhuis
(3D-print), versie 2: staal draagt, plastic klemt.

Waarom v1 brak: de onderdelen werden rechtop geprint, waardoor de lagen
dwars op de buigspanning in de flenzen lagen (scheuren langs een laag in de
scherpe hoek waar de knokkel ophoudt), de wanden waren dun (5 mm) en de deur
hing op een half ingestoken bout in een blind gat.

v2:
- Beide delen worden PLAT geprint (op de flens), zodat de lagen in het vlak
  van de buigspanning liggen.
- Flenzen 8 mm, knokkels Ø28 mm, knokkelbrug over de volle breedte.
- Eén doorgaande M8 bout door beide knokkels: de bout neemt alle dwarskrachten,
  het plastic krijgt alleen stuik (druk) op de boring.
- De deur hangt aan de boutkop (met sluitring); de bout draait onder in een
  ingesloten moer: kop draaien = deur omhoog/omlaag, contramoer eronder borgt.
- In de bestaande paumelle-gaten komen stalen verzonken (constructie)schroeven
  in plaats van geprinte pennen.

Assenstelsel (mm), van buiten gezien: z omhoog, y naar buiten. De deur zit op
x < 0, y = 0..DOOR_T (opdek: de achterkant ligt in het gevelvlak y = 0), de
deurkant met de paumelle-gaten in het vlak x = 0. Scharnieras op (AX, AY),
voor het gevelvlak.

Gebruik:  python3 scharnier.py    -> schrijft STL's (printstand) naar ./stl
"""

import math
import os

import numpy as np
import trimesh
from manifold3d import Manifold

# ---------------------------------------------------------------- parameters
# >>> meet deze aan je deur / de oude paumelle (kant die in de muur gaat) <<<
DOOR_T = 20.0        # dikte van de deur (breedte van de deurkant)
HOLE_PITCH = 50.0    # hart-op-hart afstand tussen de twee paumelle-gaten
HOLE_Y = DOOR_T / 2  # afstand hart gat tot achterkant deur
HOLE_TOP_Z = -14.0   # hoogte bovenste gat t.o.v. midden scharnier
HOLE_SCREW_D = 8.0   # verzonken schroef in de paumelle-gaten (moet in het gat bijten)

PLATE_T = 8.0        # dikte van de flenzen
KNUCKLE_R = 14.0     # straal van de knokkels (Ø28)
AX = PLATE_T + 1.0 + KNUCKLE_R   # as 1 mm naast de deurflens
AY = PLATE_T + 1.0 + KNUCKLE_R   # as 1 mm voor de kozijnplaat
HALF_H = 55.0        # knokkels lopen van +-GAP/2 tot +-HALF_H
GAP = 6.0            # nominale spleet tussen de knokkels (instelbereik +-4 mm)
FRAME_W = 70.0       # breedte kozijnplaat

BOLT_CLEAR = 8.5     # boring voor M8
NUT_AF = 13.3        # M8 moer sleutelwijdte + speling
NUT_H = 7.0

SCREW_D = 5.0        # extra houtschroeven 5 mm
SLOT_W = 5.4
SLOT_LEN = 14.0      # sleuflengte (+-4,3 mm grof verstellen)
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


def csk_hole_x(d, y, z):
    """Verzonken gat (90°) door de deurflens, kop vlak met de buitenkant."""
    rs, rh = d / 2 + 0.25, d + 0.3
    return xcyl(rs, -60, PLATE_T + 1, y, z) + \
        xcyl(rs, PLATE_T - (rh - rs), PLATE_T + 0.01, y, z, r_end=rh) + \
        xcyl(rh, PLATE_T, PLATE_T + 1, y, z)


def slot_y(x, z):
    """Verticaal sleufgat door de kozijnplaat."""
    r = SLOT_W / 2
    a = ycyl(r, -1, PLATE_T + 1, x, z - (SLOT_LEN / 2 - r))
    b = ycyl(r, -1, PLATE_T + 1, x, z + (SLOT_LEN / 2 - r))
    return Manifold.batch_hull([a, b])


def hole_z():
    return [HOLE_TOP_Z, HOLE_TOP_Z - HOLE_PITCH]


def door_screw_spots():
    """(diameter, z) van de verzonken schroeven in de deurflens."""
    zs = hole_z()
    return [(HOLE_SCREW_D, z) for z in zs] + [(SCREW_D, sum(zs) / 2), (SCREW_D, min(zs) - 16)]


# ---------------------------------------------------------------- parts
def door_part():
    """Deurdeel: flens op de deurkant + bovenste knokkel."""
    z_lo = min(hole_z()) - 23
    flange = box(0, PLATE_T, 0, DOOR_T, z_lo, HALF_H)
    # brug onder de hele knokkel: stijf, en plat printbaar zonder support
    bridge = box(0, AX, PLATE_T + 1, AY + KNUCKLE_R, GAP / 2, HALF_H)
    knuckle = zcyl(KNUCKLE_R, GAP / 2, HALF_H, AX, AY)
    body = flange + bridge + knuckle

    holes = [csk_hole_x(d, HOLE_Y, z) for d, z in door_screw_spots()]
    holes.append(zcyl(BOLT_CLEAR / 2, 0, HALF_H + 1, AX, AY))
    for h in holes:
        body = body - h
    return body


def frame_part():
    """Kozijndeel: plaat met sleufgaten op de voorkant van kozijn/gevel naast
    de deur + onderste knokkel met ingesloten M8 moer aan de onderkant."""
    x0 = PLATE_T + 1
    plate = box(x0, x0 + FRAME_W, 0, PLATE_T, -HALF_H, HALF_H)
    bridge = box(AX - KNUCKLE_R, AX + KNUCKLE_R, 0, AY, -HALF_H, -GAP / 2)
    knuckle = zcyl(KNUCKLE_R, -HALF_H, -GAP / 2, AX, AY)
    body = plate + bridge + knuckle

    holes = [zcyl(BOLT_CLEAR / 2, -HALF_H - 1, 1, AX, AY)]
    nut_r = NUT_AF / math.sqrt(3)  # omgeschreven straal van de zeskant
    holes.append(Manifold.cylinder(NUT_H + 1, nut_r, nut_r, 6).rotate([0, 0, 30])
                 .translate([AX, AY, -HALF_H - 1]))
    xa = AX + KNUCKLE_R + 9
    xb = x0 + FRAME_W - 9
    holes += [slot_y(xa, 38), slot_y(xa, 0), slot_y(xa, -38),
              slot_y(xb, 38), slot_y(xb, 0), slot_y(xb, -38)]
    for h in holes:
        body = body - h
    return body


# ---------------------------------------------------------------- hardware (alleen voor de render)
BOLT_L = 130.0       # DIN 931 M8x130 (deels draad, 28 mm draad)


def hexprism(af, z0, h, x=AX, y=AY):
    r = af / math.sqrt(3)
    return Manifold.cylinder(h, r, r, 6).rotate([0, 0, 30]).translate([x, y, z0])


def bolt_assembly(split=False):
    top = HALF_H + 1.6
    washer = zcyl(12.0, HALF_H, top, AX, AY, seg=48) - zcyl(4.2, HALF_H - 1, top + 1, AX, AY, seg=32)
    head = hexprism(13, top, 5.3)
    shank = zcyl(4.0, top - BOLT_L, top, AX, AY, seg=32)
    nut1 = hexprism(13, -HALF_H, 6.5) - zcyl(4.0, -HALF_H - 1, -HALF_H + 8, AX, AY, seg=32)
    nut2 = hexprism(13, -HALF_H - 6.6, 6.5) - zcyl(4.0, -HALF_H - 8, -HALF_H + 1, AX, AY, seg=32)
    if split:
        return washer + head + shank, nut1 + nut2
    return washer + head + shank + nut1 + nut2


def door_screws():
    out = Manifold()
    for d, z in door_screw_spots():
        rs, rh = d / 2, d
        out = out + xcyl(rs, -60, PLATE_T - (rh - rs), HOLE_Y, z, seg=32) + \
            xcyl(rs, PLATE_T - (rh - rs), PLATE_T - 0.2, HOLE_Y, z, r_end=rh, seg=32)
    return out


# ---------------------------------------------------------------- export
def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3],
                           np.asarray(mesh.tri_verts), process=True)


def mirrored(m):
    """Spiegelbeeld voor de deur die aan de andere kant draait."""
    return m.mirror([1, 0, 0])


def print_orient(m, kind):
    """Printstand: plat op de flens die tegen het hout komt, zodat de lagen in
    het vlak van de buigspanning liggen."""
    if kind == "deur":
        m = m.rotate([0, -90, 0])      # deurkant-vlak naar beneden
    else:
        m = m.rotate([90, 0, 0])       # gevelvlak naar beneden
    x0, y0, z0, x1, y1, z1 = m.bounding_box()
    return m.translate([-(x0 + x1) / 2, -(y0 + y1) / 2, -z0])


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
        tm = to_trimesh(print_orient(m, name.split("_")[0][:4]))
        assert tm.is_watertight, name
        tm.export(os.path.join(out, f"{name}.stl"))
        print(f"{name:24s} {m.volume() / 1000:6.1f} cm3  {m.num_tri():6d} tri  "
              f"printmaat {np.round(tm.extents, 1)}")


if __name__ == "__main__":
    main()
