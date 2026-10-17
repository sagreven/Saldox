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
lid_bev = 1.1;     // afschuining (45 graden) van de deksel- en groefrand
ceil_t  = 1.0;     // materiaal boven de groef, tot de stapelrand
groove  = 1.4;     // hoe ver de groef in de wand gaat (deksel grijpt 1,4 mm in)
lid_fit = 0.1;     // speling deksel in de groef, per kant (0,1 getest: strak, schuift goed)
steunen = 2;       // breekbare steuntjes in de sleuf aan de voorkant (0 = geen)
klik    = false;   // klik-nokje tegen vanzelf openschuiven (standaard: alleen schuiven)

$fn = 40;

W  = gx * G - 0.5;
D  = gy * G - 0.5;
Hb = hu * U;               // bovenkant wand = onderkant stapelrand
z_floor = foot_h + floor_t;
open_i  = 5.6;             // opening aan de onderkant van de stapelrand = W - 5.6
z_g1    = Hb - ceil_t;     // bovenkant groef
z_g0    = z_g1 - lid_t - lid_fit; // onderkant groef = bovenkant tussenwanden
lid_w   = W - (wall + lid_fit) - 0.3;          // lengte deksel (x)
lid_d   = D - open_i + 2 * groove - 2 * lid_fit; // breedte deksel (y)
lid_x   = lid_w / 2 - (W / 2 - wall - lid_fit); // middelpunt deksel in gesloten stand

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

// Vorm van de deksel (g = 0) of van de groef (g = speling): onderaan recht,
// bovenaan aan -x en beide zijkanten 45 graden afgeschuind. Zo heeft de groef
// een schuin plafond (zwaluwstaart) dat zonder support te printen is.
module lid_shape(g = 0) {
    hull() {
        translate([-lid_w / 2 - g, -lid_d / 2 - g, 0])
            cube([lid_w + 2 * g, lid_d + 2 * g, lid_t - lid_bev + g]);
        translate([-lid_w / 2 - g + lid_bev, -lid_d / 2 - g + lid_bev, 0])
            cube([lid_w + 2 * g - lid_bev, lid_d + 2 * g - 2 * lid_bev, lid_t + g]);
    }
}

module groove_cut() {
    // groef: aan -x dicht (aanslag), aan +x door de wand naar buiten
    hull() {
        translate([lid_x, 0, z_g0]) lid_shape(lid_fit);
        translate([lid_x + W, 0, z_g0]) lid_shape(lid_fit);
    }
    // opening tussen groef en stapelrand
    translate([0, 0, z_g1 - 0.01]) rsq(W - open_i, D - open_i, (41.5 - open_i - 34) / 2, ceil_t + 0.02);
}

// Breekbare steuntjes in de sleuf door de voorwand (+x), zodat de brug boven
// de sleuf niet te lang wordt. Dun in de schuifrichting: de deksel drukt ze
// er bij de eerste keer insteken uit.
module steuntjes() {
    for (k = [1 : steunen])
        translate([W / 2 - wall / 2 - 0.2, -lid_d / 2 + k * lid_d / (steunen + 1) - 0.4, z_g0 - 0.01])
            cube([0.4, 0.8, lid_t + lid_fit + 0.02]);
}

module bakje() {
    if (deksel && steunen > 0) steuntjes();
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
    difference() {
        lid_shape();
        translate([lid_w / 2 - 9, 0, lid_t - 0.8]) rsq(3, min(20, lid_d - 10), 1, 1);
    }
    bw = D - open_i - 2;               // alleen onder de opening, niet in de zijgroeven
    if (klik) translate([lid_w / 2 - 4.5, 0, lid_t])
        scale([1, 1, 0.5]) rotate([90, 0, 0]) cylinder(r = 1.2, h = bw, center = true);
}

// deksel in gesloten stand (voor previews)
module schuifdeksel_dicht() {
    translate([lid_x, 0, z_g0]) schuifdeksel();
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
