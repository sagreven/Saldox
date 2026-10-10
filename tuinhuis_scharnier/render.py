"""Render het scharnier (gemonteerd + exploded) met een eenvoudige z-buffer
rasterizer in numpy; geen OpenGL nodig.  python3 render.py -> ./render/*.png"""

import math
import os

import numpy as np
from manifold3d import Manifold
from PIL import Image, ImageDraw, ImageFont

import scharnier as S

SS = 2  # supersampling


def tris_of(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    f = np.asarray(mesh.tri_verts)
    return v[f]  # (n,3,3)


def look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = map(np.asarray, (eye, target, up))
    f = target - eye
    f = f / np.linalg.norm(f)
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return eye, np.stack([r, u, f])


def render(objects, eye, target, fov=30, size=(1600, 1200), light=(0.4, 0.8, 1.0),
           bg=(246, 244, 240)):
    W, H = size[0] * SS, size[1] * SS
    eye, R = look_at(eye, target)
    fpx = 0.5 * H / math.tan(math.radians(fov) / 2)
    zbuf = np.full((H, W), np.inf)
    img = np.zeros((H, W, 3))
    nbuf = np.zeros((H, W, 3))
    idbuf = np.full((H, W), -1, dtype=np.int32)
    L = np.asarray(light, float)
    L /= np.linalg.norm(L)
    L_cam = R @ L

    for oid, (m, color) in enumerate(objects):
        T = tris_of(m)
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        C = (T - eye) @ R.T  # camera coords: x right, y up, z forward
        keep = (C[:, :, 2] > 1).all(axis=1)
        # back-face culling
        cen = T.mean(axis=1)
        keep &= np.einsum("ij,ij->i", n, eye - cen) > 0
        C, n = C[keep], n[keep]
        px = W / 2 + fpx * C[:, :, 0] / C[:, :, 2]
        py = H / 2 - fpx * C[:, :, 1] / C[:, :, 2]
        iz = 1.0 / C[:, :, 2]
        view = (eye - T[keep].mean(axis=1))
        view /= np.linalg.norm(view, axis=1, keepdims=True)
        diff = 0.65 * np.clip(n @ L, 0, 1) + 0.45 * np.clip(np.einsum("ij,ij->i", n, view), 0, 1)
        h = (L - (T[keep].mean(axis=1) - eye) / np.linalg.norm(T[keep].mean(axis=1) - eye, axis=1, keepdims=True))
        h /= np.linalg.norm(h, axis=1, keepdims=True)
        spec = np.clip(np.einsum("ij,ij->i", n, h), 0, 1) ** 40
        sky = 0.5 + 0.5 * n[:, 2]
        col = np.asarray(color, float) / 255.0
        shade = (0.28 + 0.12 * sky)[:, None] * col + 0.62 * diff[:, None] * col + 0.18 * spec[:, None]
        for i in range(len(px)):
            x0, x1 = int(max(px[i].min(), 0)), int(min(px[i].max() + 1, W))
            y0, y1 = int(max(py[i].min(), 0)), int(min(py[i].max() + 1, H))
            if x0 >= x1 or y0 >= y1:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            (ax, bx, cx), (ay, by, cy) = px[i], py[i]
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-9:
                continue
            w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
            w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not inside.any():
                continue
            z = 1.0 / (w0 * iz[i, 0] + w1 * iz[i, 1] + w2 * iz[i, 2])
            zb = zbuf[y0:y1, x0:x1]
            upd = inside & (z < zb)
            zb[upd] = z[upd]
            img[y0:y1, x0:x1][upd] = shade[i]
            nbuf[y0:y1, x0:x1][upd] = n[i]
            idbuf[y0:y1, x0:x1][upd] = oid

    # contourlijnen: diepte-sprong, normaal-knik of object-grens
    hit = np.isfinite(zbuf)
    zf = np.where(hit, zbuf, 1e9)
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        za, zb_ = zf, np.roll(np.roll(zf, -dy, 0), -dx, 1)
        na, nb = nbuf, np.roll(np.roll(nbuf, -dy, 0), -dx, 1)
        ia, ib = idbuf, np.roll(np.roll(idbuf, -dy, 0), -dx, 1)
        both = (ia >= 0) & (ib >= 0)
        e = (ia != ib) | (both & ((np.abs(za - zb_) > 0.015 * np.minimum(za, zb_)) |
                                  ((na * nb).sum(-1) < 0.8)))
        edge |= e
    out = np.where(hit[..., None], img, np.asarray(bg) / 255.0)
    out = np.where(edge[..., None], out * 0.35, out)
    out = np.clip(out, 0, 1)
    out = out.reshape(H // SS, SS, W // SS, SS, 3).mean(axis=(1, 3))
    return Image.fromarray((out * 255).astype(np.uint8))


WOOD = (196, 160, 112)
WOOD2 = (170, 132, 88)
PLA = (52, 92, 140)
PLA2 = (214, 120, 48)
STEEL = (160, 165, 172)


def door_board(w=180, h=300):
    door = S.box(-w, 0, 0, S.DOOR_T, -h / 2, h / 2)
    for z in (S.PEG_TOP_Z, S.PEG_TOP_Z - S.HOLE_PITCH):
        door = door - S.xcyl(S.HOLE_D / 2, -S.HOLE_DEPTH, 0.1, S.HOLE_Y, z)
    return door


def swing(m, deg):
    return m.translate([-S.AX, -S.AY, 0]).rotate([0, 0, -deg]).translate([S.AX, S.AY, 0])


def hinge(open_deg):
    tip_z = S.GAP / 2 + S.BORE_DEPTH
    return [
        (swing(S.door_part(), open_deg), PLA2),
        (S.frame_part(), PLA),
        (S.bolt(tip_z), STEEL),
        (S.nut(-S.GAP / 2 - S.NUT_H), STEEL),          # ingesloten moer
        (S.nut(-S.FLANGE_H / 2 - 6.5), STEEL),          # contramoer
    ]


def scene_assembled(open_deg=35.0):
    wall = S.box(-60, 140, -40, 0, -150, 150)
    return [(wall, WOOD2), (swing(door_board(), open_deg), WOOD)] + hinge(open_deg)


def scene_exploded():
    tip_z = S.GAP / 2 + S.BORE_DEPTH
    return [
        (S.door_part().translate([0, 0, 45]), PLA2),
        (S.frame_part(), PLA),
        (S.bolt(tip_z).translate([0, 0, -45]), STEEL),
        (S.nut(-S.GAP / 2 - S.NUT_H + 30), STEEL),
        (S.nut(-S.FLANGE_H / 2 - 6.5 - 30), STEEL),
    ]


def scene_overview(w=800, h=1900, gap=4, open_left=0, open_right=40, hinge_z=650):
    """Twee opdekdeuren van buiten gezien; scharnieren boven en onder."""
    objs = [(S.box(-2 * w - gap - 160, 160, -40, 0, -h / 2 - 120, h / 2 + 120), WOOD2)]
    for side, deg in (("L", open_left), ("R", open_right)):
        parts = [(swing(S.box(-w, 0, 0, S.DOOR_T, -h / 2, h / 2), deg), WOOD)]
        for zc in (hinge_z, -hinge_z):
            parts += [(m.translate([0, 0, zc]), c) for m, c in hinge(deg)]
        if side == "R":  # gespiegeld, scharnier aan de andere kant
            parts = [(m.mirror([1, 0, 0]).translate([-2 * w - gap, 0, 0]), c) for m, c in parts]
        objs += parts
    return objs


def label(img, lines, title):
    d = ImageDraw.Draw(img)
    try:
        f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
        f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    d.text((36, 28), title, fill=(40, 40, 40), font=f1)
    for i, (txt, col) in enumerate(lines):
        y = 84 + i * 32
        d.rectangle([36, y + 4, 56, y + 24], fill=col)
        d.text((68, y), txt, fill=(60, 60, 60), font=f2)
    return img


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "render")
    os.makedirs(out, exist_ok=True)
    legend = [("deurdeel (2 pennen in paumelle-gaten)", PLA2),
              ("kozijndeel (sleufgaten)", PLA),
              ("M8x80 inbusbout + moeren", STEEL)]

    img = render(scene_overview(), eye=(700, 3600, 700), target=(-800, 0, 0), fov=36)
    label(img, legend + [("deuren / gevel", WOOD)],
          "Tuinhuis – twee opdekdeuren, 2 scharnieren per deur").save(os.path.join(out, "overzicht_deuren.png"))

    img = render(scene_assembled(35), eye=(330, 420, 150), target=(10, 5, -5), fov=30)
    label(img, legend + [("deur / gevel", WOOD)], "Scharnier linkerdeur – gemonteerd (35° open)").save(
        os.path.join(out, "scharnier_gemonteerd.png"))

    img = render(scene_exploded(), eye=(300, 300, 110), target=(15, 5, 0), fov=27)
    label(img, legend, "Scharnier – exploded").save(os.path.join(out, "scharnier_exploded.png"))

    img = render(scene_exploded(), eye=(-330, 380, 110), target=(10, 5, 12), fov=32)
    label(img, legend, "Deurkant – twee pennen voor de paumelle-gaten").save(
        os.path.join(out, "scharnier_achterkant.png"))
    print("klaar")


if __name__ == "__main__":
    main()
