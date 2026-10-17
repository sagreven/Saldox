// Stapelbaar Gridfinity-bakje voor in de draagcassette (en de Packout
// low-profile organizer).
//
// Het bakje heeft een schuifdeksel die vlak onder de stapelrand in een groef
// loopt. Het bakje erboven valt dus nog steeds met zijn voeten in de
// stapelrand. De deksel rust ook op de tussenwanden (vakken = "per_vak"), zodat
// elk vakje apart dicht is: schroeven kunnen niet van vakje naar vakje, ook
// niet als het bakje los in een tas ligt. De deksel schuift er aan de
// rechterkant (+x) uit.
//
// Render: openscad -D gx=2 -D gy=1 -D 'part="bakje"'  -o bakje.stl  bakje.scad
//         openscad -D gx=2 -D gy=1 -D 'part="deksel"' -o deksel.stl bakje.scad

include <gridfinity.scad>

/* [Formaat] */
gx = 2;            // breedte in vakken (42 mm)
gy = 1;            // diepte in vakken
hu = 5;            // hoogte in eenheden van 7 mm (5 = past in de low-profile organizer)
vakken = "per_vak"; // per_vak | open
deksel = true;     // schuifdeksel (false = open bakje; met per_vak lopen de
                   // tussenwanden dan door in de stapelrand)
part = "both";     // bakje | deksel | both | dicht (preview)

/* [Constructie] */
wall    = 1.2;     // buitenwand
floor_t = 1.2;     // bodem boven de voeten

/* [Schuifdeksel] */
lid_t   = 1.5;     // dikte deksel
slot_t  = 1.8;     // hoogte van de groef
ceil_t  = 1.0;     // materiaal boven de groef, tot de stapelrand
groove  = 1.4;     // hoe ver de groef in de wand gaat (deksel grijpt 1,4 mm in)
lid_fit = 0.2;     // speling deksel in de groef, per kant
klik    = false;   // klik-nokje tegen vanzelf openschuiven (standaard: alleen schuiven)

$fn = 40;

W  = gx * G - 0.5;
D  = gy * G - 0.5;
Hb = hu * U;               // bovenkant wand = onderkant stapelrand
z_floor = foot_h + floor_t;
open_i  = 5.6;             // opening aan de onderkant van de stapelrand = W - 5.6
z_g1    = Hb - ceil_t;     // bovenkant groef
z_g0    = z_g1 - slot_t;   // onderkant groef = bovenkant tussenwanden

module cavity(w, d) {
    c = 2 * wall;          // binnenmaat = buitenmaat - 2 wanden
    // recht deel, daarna 45 graden afschuining naar de stapelrand
    translate([0, 0, z_floor]) rsq(w - c, d - c, (41.5 - c - 34) / 2 + 0.5, Hb - 1.6 - z_floor + 0.01);
    hull() {
        slice(w - c, d - c, (41.5 - c - 34) / 2 + 0.5, Hb - 1.6);
        slice(w - 5.6, d - 5.6, (41.5 - 5.6 - 34) / 2, Hb + 0.01);
    }
    translate([0, 0, Hb]) lip_cut(w, d);
}

// Vakje met schuifdeksel: recht deel, 45 graden versmalling tot de
// groefbodem, daarna de groef en de opening naar de stapelrand.
module cavity_lid(w, d) {
    c = 2 * wall;
    translate([0, 0, z_floor]) rsq(w - c, d - c, (41.5 - c - 34) / 2 + 0.5, z_g0 - 1.6 - z_floor + 0.01);
    hull() {
        slice(w - c, d - c, (41.5 - c - 34) / 2 + 0.5, z_g0 - 1.6);
        slice(w - open_i, d - open_i, (41.5 - open_i - 34) / 2, z_g0 + 0.01);
    }
}

module groove_cut() {
    // groef: aan -x dicht (aanslag), aan +x door de wand naar buiten
    gw = D - open_i + 2 * groove;
    translate([-(W / 2 - wall - lid_fit), -gw / 2, z_g0]) cube([W, gw, slot_t]);
    // opening tussen groef en stapelrand
    translate([0, 0, z_g1 - 0.01]) rsq(W - open_i, D - open_i, (41.5 - open_i - 34) / 2, ceil_t + 0.02);
}

module bakje() {
    difference() {
        union() {
            for (i = [0 : gx - 1], j = [0 : gy - 1])
                translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, 0]) gf_foot();
            translate([0, 0, foot_h - 0.01]) rsq(W, D, 3.75, Hb + lip_h - foot_h + 0.01);
        }
        if (deksel) {
            if (vakken == "open") cavity_lid(W, D);
            else for (i = [0 : gx - 1], j = [0 : gy - 1])
                translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, 0]) cavity_lid(41.5, 41.5);
            groove_cut();
            translate([0, 0, Hb]) lip_cut(W, D);
        } else if (vakken == "open")
            cavity(W, D);
        else
            for (i = [0 : gx - 1], j = [0 : gy - 1])
                translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, 0]) cavity(41.5, 41.5);
    }
}

// Schuifdeksel, plat op het bed. Aan de +x kant een greepsleuf voor je nagel.
// Optioneel (klik = true) een nokje dat achter de bovenrand van de groef valt.
module schuifdeksel() {
    lw = W - (wall + lid_fit) - 0.3;   // van aanslag tot net binnen de voorkant
    ld = D - open_i + 2 * groove - 2 * lid_fit;
    difference() {
        translate([-lw / 2, -ld / 2, 0]) cube([lw, ld, lid_t]);
        translate([lw / 2 - 9, 0, lid_t - 0.8]) rsq(3, min(20, ld - 10), 1, 1);
    }
    bw = D - open_i - 2;               // alleen onder de opening, niet in de zijgroeven
    if (klik) translate([lw / 2 - 4.5, 0, lid_t])
        scale([1, 1, 0.5]) rotate([90, 0, 0]) cylinder(r = 1.2, h = bw, center = true);
}

// deksel in gesloten stand (voor previews)
module schuifdeksel_dicht() {
    lw = W - (wall + lid_fit) - 0.3;
    translate([lw / 2 - (W / 2 - wall - lid_fit), 0, z_g0]) schuifdeksel();
}

if (part == "bakje") bakje();
else if (part == "deksel") schuifdeksel();
else if (part == "dicht") { bakje(); schuifdeksel_dicht(); }
else if (part == "both") {
    bakje();
    if (deksel) translate([0, D / 2 + 10 + (D - open_i + 2 * groove) / 2, 0]) schuifdeksel();
}

echo(str("Bakje ", gx, "x", gy, "x", hu, "u: ", W, " x ", D, " x ", Hb + lip_h,
         " mm (gestapeld telt elk bakje ", Hb, " mm)"));
