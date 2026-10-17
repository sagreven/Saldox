// Gridfinity-draagsysteem: generator
// ==================================
// Eén bestand voor alle onderdelen: stapelbare bakjes met schuifdeksel en de
// afsluitbare cassettes waar ze in gaan.
//
// Gebruik:
//  - OpenSCAD: open dit bestand, kies Window > Customizer, stel in, druk F6
//    (render) en F7 (STL exporteren).
//  - In de browser: upload dit bestand in de Parametric Model Maker van
//    MakerWorld; daar krijg je dezelfde keuzelijsten.
//  - Commandoregel:
//    openscad -D 'onderdeel="bakje"' -D gx=2 -D gy=1 -o bakje.stl generator.scad
//
// Bakjes: stapelbaar, Gridfinity-voeten, schuifdeksel die onder de stapelrand
// loopt (zwaluwstaartgroef, zonder support te printen). De deksel schuift er
// aan de rechterkant (+x) uit.
// Cassette: Gridfinity-bodem binnenin, scharnier met 1,75 mm filament als pen,
// twee klikbeugels; 1 of 2 lagen bakjes hoog.

/* [Wat wil je printen?] */
onderdeel = "bakje"; // [bakje:Bakje, schuifdeksel:Schuifdeksel, bakje_en_deksel:Bakje + deksel (één printplaat), cassette_onderbak:Cassette - onderbak, cassette_deksel:Cassette - deksel, cassette_beide:Cassette - onderbak + deksel, voorbeeld_bakje:Voorbeeld - bakje met deksel dicht, voorbeeld_cassette:Voorbeeld - cassette dicht]

/* [Maat] */
// Breedte in Gridfinity-vakken (42 mm)
gx = 1; // [1:1:8]
// Diepte in Gridfinity-vakken (42 mm)
gy = 1; // [1:1:6]

/* [Bakje] */
// Hoogte van het bakje (heel past in de Packout low-profile organizer; 2 halve = 1 heel)
hu = 5; // [2.5:half, 5:heel]
// Indeling binnenin
vakken = "per_vak"; // [per_vak:Elk vak apart, open:Eén open ruimte]
// Schuifdeksel (uit = open bakje)
deksel = true;

/* [Schuifdeksel] */
// Speling van de deksel in de groef, per kant (0,1 getest: strak, schuift goed)
lid_fit = 0.1; // [0.05:0.05:0.3]
// Diepte van de stickeruitsparing (0 = geen)
label_d = 0.4; // [0:0.1:1]
// Breekbare steuntjes in de sleuf aan de voorkant (0 = geen)
steunen = 2; // [0:1:5]
// Klik-nokje tegen vanzelf openschuiven
klik = false;

/* [Cassette] */
// Aantal lagen bakjes in de cassette (een laag = één heel of twee halve bakjes)
lagen = 1; // [1, 2]
// Gridfinity-bodem binnenin (uit = vlakke bodem voor schuim/TPU-inleg)
baseplate = true;
// Speling tussen bovenste bakje en deksel (klein = deksel klemt bakjes vast)
lid_gap = 0.4; // [0.2:0.1:1]

/* [Hidden] */
$fn = 40;

// Gridfinity-standaard
G       = 42;     // rastermaat
U       = 7;      // hoogte-eenheid
gf_base = 4.65;   // hoogte baseplate-profiel
foot_h  = 4.75;   // hoogte voetprofiel bakje
lip_h   = 4.4;    // hoogte stapelrand bakje

// bakje
wall    = 1.2;     // buitenwand
floor_t = 1.2;     // bodem boven de voeten
lid_t   = 1.5;     // dikte deksel
lid_bev = 1.1;     // afschuining (45 graden) van de deksel- en groefrand
ceil_t  = 1.0;     // materiaal boven de groef, tot de stapelrand
groove  = 1.4;     // hoe ver de groef in de wand gaat

// cassette
laag_hu  = 5;     // hoogte van een laag bakjes, in eenheden van 7 mm
c_wall   = 2.4;   // wanddikte
c_floor  = 1.2;   // bodem onder het baseplate-patroon
top_t    = 2.0;   // dikte deksel
c_lid_h  = 8;     // totale hoogte deksel
tongue_h = 3;     // hoogte van de sluitrand (tong-en-groef)
c_fit    = 0.2;   // passpeling tong/groef
kr       = 3.5;   // straal scharnierknokkel
pin_d    = 2.0;   // gat voor 1,75 mm filament
k_gap    = 0.4;   // speling tussen knokkels
k_count  = 5;     // aantal knokkels (oneven: onderbak heeft de buitenste)
latch_w   = 18;   // breedte klikbeugel
latch_t   = 1.8;  // dikte van de veer
latch_len = 12;   // lengte onder de scheidingslijn
ridge_d   = 1.2;  // hoe ver de nok uitsteekt

// ---- afgeleide maten: bakje ----
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


// Stickervlak: het deel van de deksel dat zichtbaar is als hij dicht zit
// (binnen de opening W - open_i), tussen de achterkant en de greepsleuf.
// Coordinaten ten opzichte van het midden van de deksel.
grip_x  = lid_w / 2 - 9;                                   // greepsleuf
label_x0 = -(W / 2 - open_i / 2) + 1 - lid_x;              // achterkant zichtbaar deel
label_x1 = grip_x - 1.5 - 1.5;                             // tot net voor de greepsleuf
label_y  = D - open_i - 2;

// ---- afgeleide maten: cassette ----
cav_w   = gx * G + 0.5;
cav_d   = gy * G + 0.5;
cav_r   = 4;
out_w   = cav_w + 2 * c_wall;
out_d   = cav_d + 2 * c_wall;
out_r   = cav_r + c_wall;
inner_h = lagen * laag_hu * U + lip_h + lid_gap; // vanaf bodemvloer
H_body  = c_floor + inner_h - (c_lid_h - top_t);  // scheidingslijn onderbak/deksel
k_axis_y = out_d + kr + 0.3;                    // scharnieras (y), achterkant

// ==== Gridfinity-vormen ====

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

// ==== Bakje en schuifdeksel ====

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

// Schuifdeksel, plat op het bed. Aan de +x kant een greepsleuf voor je nagel,
// daarnaast een ondiepe uitsparing voor een sticker.
// Optioneel (klik = true) een nokje dat achter de bovenrand van de groef valt.
module schuifdeksel() {
    difference() {
        lid_shape();
        translate([grip_x, 0, lid_t - 0.8]) rsq(3, min(20, lid_d - 10), 1, 1);
        if (label_d > 0)
            translate([(label_x0 + label_x1) / 2, 0, lid_t - label_d])
                rsq(label_x1 - label_x0, label_y, 1.5, label_d + 1);
    }
    bw = D - open_i - 2;               // alleen onder de opening, niet in de zijgroeven
    if (klik) translate([lid_w / 2 - 4.5, 0, lid_t])
        scale([1, 1, 0.5]) rotate([90, 0, 0]) cylinder(r = 1.2, h = bw, center = true);
}

// deksel in gesloten stand (voor previews)
module schuifdeksel_dicht() {
    translate([lid_x, 0, z_g0]) schuifdeksel();
}

// ==== Cassette ====

// rand die de tong vormt: tussen holte en holte + halve wand
module tongue_ring(h, grow = 0) {
    difference() {
        rsq(cav_w + c_wall + 2 * grow, cav_d + c_wall + 2 * grow, cav_r + c_wall / 2 + grow, h);
        translate([0, 0, -1]) rsq(cav_w - 2 * grow, cav_d - 2 * grow, max(cav_r - grow, 0.5), h + 2);
    }
}

// knokkelsegmenten langs x; onderbak krijgt even indices, deksel oneven
module knuckles(for_lid) {
    seg = (out_w - 2 * out_r - (k_count - 1) * k_gap) / k_count;
    x0  = -out_w / 2 + out_r;
    for (i = [0 : k_count - 1])
        if ((i % 2 == 1) == for_lid)
            translate([x0 + i * (seg + k_gap), 0, 0]) {
                hull() {
                    translate([0, k_axis_y - out_d / 2, H_body])
                        rotate([0, 90, 0]) cylinder(r = kr, h = seg);
                    // steunblok tegen de achterwand, onder (onderbak) of boven (deksel)
                    translate([0, out_d / 2 - 0.01, for_lid ? H_body : H_body - 2 * kr])
                        cube([seg, 0.01, 2 * kr]);
                }
            }
}

module pin_hole() {
    translate([-out_w, k_axis_y - out_d / 2, H_body])
        rotate([0, 90, 0]) cylinder(d = pin_d, h = 2 * out_w);
}

function latch_xs() = gx >= 3 ? [-out_w / 4, out_w / 4] : [0];

// ---- onderbak ----
module cassette_body() {
    difference() {
        union() {
            rsq(out_w, out_d, out_r, H_body);
            translate([0, 0, H_body - 0.01]) tongue_ring(tongue_h + 0.01);
            knuckles(false);
            // nokken voor de klikbeugels (voorkant, y = -out_d/2)
            for (x = latch_xs()) latch_ridge(x);
        }
        // holte
        translate([0, 0, c_floor + (baseplate ? gf_base : 0)])
            rsq(cav_w, cav_d, cav_r, H_body + tongue_h + 1);
        pin_hole();
    }
    if (baseplate) baseplate_insert();
}

module baseplate_insert() {
    translate([0, 0, c_floor])
        difference() {
            rsq(cav_w + 0.01, cav_d + 0.01, cav_r, gf_base);
            for (i = [0 : gx - 1], j = [0 : gy - 1])
                translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, gf_base + 0.01])
                    gf_socket();
        }
}

// nok met schuine bovenkant (invoer) en vlakke onderkant (vanghaak)
module latch_ridge(x) {
    zc = H_body - latch_len + 2.7;   // onderkant van de nok
    w  = latch_w - 2;
    translate([x - w / 2, -out_d / 2, zc])
        rotate([90, 0, 90]) linear_extrude(w)
            polygon([[0.01, 0], [-ridge_d, 0], [-ridge_d, 0.6], [0.01, 0.6 + ridge_d * 1.5]]);
}

// ---- deksel ----
module cassette_deksel() {
    difference() {
        union() {
            translate([0, 0, H_body]) rsq(out_w, out_d, out_r, c_lid_h);
            knuckles(true);
        }
        // binnenruimte deksel
        translate([0, 0, H_body - 1]) rsq(cav_w, cav_d, cav_r, c_lid_h - top_t + 1);
        // groef voor de tong
        translate([0, 0, H_body - 1]) tongue_ring(tongue_h + c_fit + 1, c_fit);
        pin_hole();
    }
    for (x = latch_xs()) latch_arm(x);
}

// verende klikbeugel aan de voorkant van het deksel
module latch_arm(x) {
    off = ridge_d + 0.3;                 // afstand veer tot bodywand
    y_in = -out_d / 2 - off;             // binnenkant van de veer
    translate([x - latch_w / 2, 0, 0]) {
        // bevestigingsblok op het deksel
        translate([0, y_in - latch_t, H_body + 1]) cube([latch_w, off + latch_t + 0.5, c_lid_h - 1]);
        // veer
        translate([0, y_in - latch_t, H_body - latch_len]) cube([latch_w, latch_t, latch_len + c_lid_h]);
        // haak: vlakke bovenkant, schuine onderkant
        translate([0, y_in, H_body - latch_len])
            rotate([90, 0, 90]) linear_extrude(latch_w)
                polygon([[-0.01, 0], [ridge_d, 1.2], [ridge_d, 2.5], [-0.01, 2.5]]);
        // trekrand om te openen
        translate([0, y_in - latch_t - 2, H_body - latch_len]) cube([latch_w, 2 + 0.01, 1.6]);
    }
}

// ==== Uitvoer ====

module cassette_deksel_print() {
    translate([0, 0, H_body + c_lid_h]) rotate([180, 0, 0]) cassette_deksel();
}

if (onderdeel == "bakje") bakje();
else if (onderdeel == "schuifdeksel") schuifdeksel();
else if (onderdeel == "bakje_en_deksel") {
    bakje();
    if (deksel) translate([0, D / 2 + 10 + (D - open_i + 2 * groove) / 2, 0]) schuifdeksel();
}
else if (onderdeel == "cassette_onderbak") cassette_body();
else if (onderdeel == "cassette_deksel") cassette_deksel_print();
else if (onderdeel == "cassette_beide") {
    cassette_body();
    translate([0, out_d + 20, 0]) cassette_deksel_print();
}
else if (onderdeel == "voorbeeld_bakje") { bakje(); if (deksel) schuifdeksel_dicht(); }
else if (onderdeel == "voorbeeld_cassette") { cassette_body(); cassette_deksel(); }

is_cassette = onderdeel == "cassette_onderbak" || onderdeel == "cassette_deksel"
           || onderdeel == "cassette_beide" || onderdeel == "voorbeeld_cassette";
if (is_cassette) {
    echo(str("Cassette ", gx, "x", gy, ", ", lagen, " laag/lagen: ", out_w, " x ", out_d,
             " mm, hoogte dicht ", H_body + c_lid_h, " mm"));
} else {
    if (deksel && label_d > 0)
        echo(str("Stickervlak op de deksel: ", label_x1 - label_x0, " x ", label_y, " mm"));
    echo(str("Bakje ", gx, "x", gy, "x", hu, "u: ", W, " x ", D, " x ", Hb + lip_h,
             " mm (gestapeld telt elk bakje ", Hb, " mm)"));
}
