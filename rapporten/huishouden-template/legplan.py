#!/usr/bin/env python3
"""Legplan voor één dakvlak: zoekt het grootste aaneengesloten paneelveld in één raster
(zoals een indak-systeem vraagt) en tekent het als SVG in Saldox-stijl.

Invoer (JSON): het dakvlak in vlakcoördinaten (u langs de goot, w de helling op, in m;
bijvoorbeeld uit 3D BAG), obstakels (dakkapel, schoorsteen, dakraam) als rechthoeken,
paneelmaat en randafstanden. Gebruik:

    python3 legplan.py dak.json legplan.svg
"""
import json
import sys


def binnen(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def afstand_rand(pt, poly):
    x, y = pt
    best = 1e9
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        best = min(best, ((x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2) ** 0.5)
    return best


def maak_past(vlak, obstakels, marge, marge_obst):
    def past(r):
        u0, w0, u1, w1 = r
        um, wm = (u0 + u1) / 2, (w0 + w1) / 2
        for p in [(u0, w0), (u1, w0), (u0, w1), (u1, w1), (um, w0), (um, w1), (u0, wm), (u1, wm)]:
            if not binnen(p, vlak) or afstand_rand(p, vlak) < marge - 1e-9:
                return False
        return not any(u0 < o[2] + marge_obst and u1 > o[0] - marge_obst and w0 < o[3] + marge_obst and w1 > o[1] - marge_obst
                       for o in obstakels)
    return past


def raster(past, bw, bh, gap=0.02, stap=0.05, n=40):
    """Grootste aaneengesloten groep panelen in één raster (alle rijen en kolommen uitgelijnd)."""
    best = []
    for i in range(n):
        for j in range(n):
            u0, w0 = stap * i, stap * j
            cel = {}
            for r in range(10):
                for c in range(10):
                    rect = (u0 + c * (bw + gap), w0 + r * (bh + gap), u0 + c * (bw + gap) + bw, w0 + r * (bh + gap) + bh)
                    if past(rect):
                        cel[(r, c)] = rect
            gezien = set()
            for k in cel:
                if k in gezien:
                    continue
                st, g = [k], []
                gezien.add(k)
                while st:
                    x = st.pop()
                    g.append(x)
                    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        y = (x[0] + d[0], x[1] + d[1])
                        if y in cel and y not in gezien:
                            gezien.add(y)
                            st.append(y)
                if len(g) > len(best):
                    best = [cel[x] for x in g]
    return best


def nl(v, dec=1):
    return f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def svg(d, panelen, richting):
    vlak, S = d["vlak"], 52
    umax, wmax = max(p[0] for p in vlak), max(p[1] for p in vlak)
    ml, mt, mb = 20, 34, 58
    W, H = ml * 2 + umax * S, mt + mb + wmax * S

    def X(u):
        return ml + u * S

    def Y(w):
        return mt + (wmax - w) * S
    o = [f'<svg class="chart" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Legplan: {len(panelen)} panelen {richting}">',
         '<defs><pattern id="arc" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         '<rect width="6" height="6" fill="#fbebe4"/><line x1="0" y1="0" x2="0" y2="6" stroke="#e8a48a" stroke-width="2"/></pattern></defs>']
    pts = " ".join(f"{X(u):.1f},{Y(w):.1f}" for u, w in vlak)
    o.append(f'<polygon points="{pts}" fill="#eef3ef" stroke="#4a5a52" stroke-width="1.5" stroke-linejoin="round"/>')
    for ob in d.get("obstakels", []):
        u0, w0, u1, w1 = ob["rect"]
        o.append(f'<rect x="{X(u0):.1f}" y="{Y(w1):.1f}" width="{(u1 - u0) * S:.1f}" height="{(w1 - w0) * S:.1f}" fill="url(#arc)" stroke="#d9480f" stroke-width="1.2" rx="3"/>')
        o.append(f'<text class="ref-label" x="{X((u0 + u1) / 2):.1f}" y="{Y((w0 + w1) / 2) + 4:.1f}" text-anchor="middle">{ob["naam"]}</text>')
    for k, (u0, w0, u1, w1) in enumerate(sorted(panelen, key=lambda r: (-r[1], r[0])), 1):
        o.append(f'<rect x="{X(u0):.1f}" y="{Y(w1):.1f}" width="{(u1 - u0) * S:.1f}" height="{(w1 - w0) * S:.1f}" fill="#0b3d2e" stroke="#ffffff" stroke-width="1" rx="2"/>')
        o.append(f'<text x="{X((u0 + u1) / 2):.1f}" y="{Y((w0 + w1) / 2) + 4:.1f}" text-anchor="middle" style="font-size:11px;font-weight:700;fill:#ffffff">{k}</text>')
    o.append(f'<text class="axis-title" x="{X(umax / 2):.1f}" y="{mt - 14}" text-anchor="middle">Nok</text>')
    o.append(f'<text class="axis-title" x="{X(umax / 2):.1f}" y="{H - mb + 22:.1f}" text-anchor="middle">Goot · ca. {nl(umax)} m langs de goot, '
             f'{nl(wmax)} m langs de helling</text>')
    o.append(f'<text class="tick" x="{X(umax / 2):.1f}" y="{H - mb + 42:.1f}" text-anchor="middle">Panelen {nl(d["paneel"][0], 3)} × {nl(d["paneel"][1], 3)} m, '
             f'{richting}; randafstand {nl(d["marge"], 2)} m, rond obstakels {nl(d["marge_obstakel"], 2)} m</text>')
    o.append("</svg>")
    return "".join(o)


def main():
    d = json.load(open(sys.argv[1]))
    vlak = [tuple(p) for p in d["vlak"]]
    past = maak_past(vlak, [o["rect"] for o in d.get("obstakels", [])], d["marge"], d["marge_obstakel"])
    bw, bh = d["paneel"]
    ligg, staand = raster(past, bw, bh), raster(past, bh, bw)
    panelen, richting = (ligg, "liggend") if len(ligg) >= len(staand) else (staand, "staand")
    open(sys.argv[2], "w").write(svg(dict(d, vlak=vlak), panelen, richting))
    print(json.dumps(dict(liggend=len(ligg), staand=len(staand), gekozen=richting, panelen=len(panelen))))


if __name__ == "__main__":
    main()
