// Gedeelde Gridfinity-vormen voor de cassette en de bakjes.
// Maatvoering volgens de Gridfinity-standaard: raster 42 mm, hoogte-eenheid 7 mm.

G       = 42;     // rastermaat
U       = 7;      // hoogte-eenheid
gf_base = 4.65;   // hoogte baseplate-profiel
foot_h  = 4.75;   // hoogte voetprofiel bakje
lip_h   = 4.4;    // hoogte stapelrand bakje

module rsq(w, d, r, h) {
    linear_extrude(h)
        offset(r = r) square([w - 2 * r, d - 2 * r], center = true);
}

// afgeronde rechthoek als dunne schijf op hoogte z (voor hull-profielen)
module slice(w, d, r, z) { translate([0, 0, z]) rsq(w, d, max(r, 0.01), 0.01); }

// Gridfinity baseplate-uitsparing voor één vak, top op z = 0, naar beneden
module gf_socket() {
    hull() { slice(42,   42,   4,    0);     slice(37.7, 37.7, 1.85, -2.15); }
    hull() { slice(37.7, 37.7, 1.85, -2.15); slice(37.7, 37.7, 1.85, -3.95); }
    hull() { slice(37.7, 37.7, 1.85, -3.95); slice(36.3, 36.3, 1.15, -gf_base - 0.01); }
}

// voet van één vak, onderkant op z = 0
module gf_foot() {
    hull() { slice(35.6, 35.6, 0.8, 0);   slice(37.2, 37.2, 1.6, 0.8); }
    hull() { slice(37.2, 37.2, 1.6, 0.8); slice(37.2, 37.2, 1.6, 2.6); }
    hull() { slice(37.2, 37.2, 1.6, 2.6); slice(41.5, 41.5, 3.75, foot_h); }
}

// Uitsparing van de stapelrand voor een rechthoek w x d (buitenmaat bakje),
// onderkant op z = 0. Volgt het voetprofiel met 0,15 mm speling rondom, zodat
// het bakje erboven per vak vastvalt.
module lip_cut(w, d) {
    module sl(i, z) slice(w - i, d - i, (41.5 - i - 34) / 2, z);
    hull() { sl(5.6, 0);   sl(1.8, 1.9); }
    hull() { sl(1.8, 1.9); sl(1.8, 3.7); }
    hull() { sl(1.8, 3.7); sl(0.4, lip_h + 0.01); }
}
