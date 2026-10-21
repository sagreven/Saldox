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
// twee klikbeugels; hoogte in halve bakjes.
//
// De generator controleert of het onderdeel op je printbed past (instelling
// Printer > bed) en stopt met een melding als het te groot is.

/* [Wat wil je printen?] */
onderdeel = "bakje"; // [bakje:Bakje, schuifdeksel:Schuifdeksel, bakje_en_deksel:Bakje + deksel - één printplaat, cassette_onderbak:Cassette - onderbak, cassette_deksel:Cassette - deksel, cassette_beide:Cassette - onderbak + deksel, inlegplaat:Inlegplaat - vlakke plaat met Gridfinity-voeten, baseplate:Losse Gridfinity-bodem - voor een cassette met vlakke bodem, test_voet:Proefstukje klik - voeten van het bakje, test_rand:Proefstukje klik - stapelrand van het bakje, voorbeeld_bakje:Voorbeeld - bakje met deksel dicht, voorbeeld_cassette:Voorbeeld - cassette dicht]

/* [Maat] */
// Breedte (maat van het bakje; een cassette is 0.6 cm groter)
gx = 1; // [1:1 vak - 4.2 cm, 2:2 vakken - 8.4 cm, 3:3 vakken - 12.6 cm, 4:4 vakken - 16.8 cm, 5:5 vakken - 21.0 cm, 6:6 vakken - 25.2 cm, 7:7 vakken - 29.4 cm, 8:8 vakken - 33.6 cm]
// Diepte (maat van het bakje; een cassette is 0.6 cm groter plus 1.3 cm voor scharnier en klikbeugels)
gy = 1; // [1:1 vak - 4.2 cm, 2:2 vakken - 8.4 cm, 3:3 vakken - 12.6 cm, 4:4 vakken - 16.8 cm, 5:5 vakken - 21.0 cm, 6:6 vakken - 25.2 cm, 7:7 vakken - 29.4 cm, 8:8 vakken - 33.6 cm]

/* [Bakje] */
// Hoogte van het bakje (heel past in de Packout low-profile organizer; 2 halve = 1 heel)
hu = 2.5; // [2.5:half - 2.2 cm hoog - stapelt per 1.75 cm, 5:heel - 3.9 cm hoog - stapelt per 3.5 cm]
// Indeling binnenin
vakken = "per_vak"; // [per_vak:Elk vak apart, open:Eén open ruimte, eigen:Eigen aantal vakjes]
// Aantal vakjes in de breedte (alleen bij Eigen aantal vakjes)
vakjes_x = 2; // [1:1:8]
// Aantal vakjes in de diepte (alleen bij Eigen aantal vakjes)
vakjes_y = 1; // [1:1:8]
// Schuifdeksel (uit = open bakje)
deksel = true;

/* [Schuifdeksel] */
// Speling van de deksel in de groef, per kant (0,1 getest: strak, schuift goed)
lid_fit = 0.1; // [0.05:0.05:0.3]
// Diepte van de stickeruitsparing (0 = geen)
label_d = 0.4; // [0:0.1:1]
// Breekbare steuntjes in de sleuf aan de voorkant, per vak van 4.2 cm (0 = geen)
steunen = 2; // [0:1:5]
// Klik-nokje tegen vanzelf openschuiven
klik = false;
// Kant waar de deksel uit schuift (voor = kant van de klikbeugels van de cassette)
schuif = "rechts"; // [rechts:Rechts, links:Links, voor:Voor, achter:Achter]

/* [Inlegplaat] */
// Dikte van de vlakke plaat boven de voeten in mm (een inlegplaat maakt van Gridfinity-vakken een vlakke vloer, bv. voor gereedschap in een al geprinte cassette)
inleg_t = 1.2; // [0.8:0.2:3]

/* [Stapelen] */
// Bakjes klikken op elkaar vast: nokjes in de stapelrand vallen in een groefje in de voeten van het bakje erboven. Hoe ver de nokjes ingrijpen in mm (0 = geen klik)
stapel_klik = 0.4; // [0:0.05:0.8]

/* [Cassette] */
// Binnenhoogte, in halve bakjes (een heel bakje telt als 2); erachter de hoogte van de gesloten cassette met magneten (zonder magneten 0.2 cm lager)
lagen = 2; // [1:1 half bakje - 2.8 cm, 2:2 halve - 4.6 cm, 3:3 halve - 6.4 cm, 4:4 halve - 8.1 cm, 5:5 halve - 9.9 cm, 6:6 halve - 11.6 cm]
// Gridfinity-bodem binnenin (uit = helemaal vlakke bodem voor schuim/TPU-inleg)
baseplate = true;
// Aantal rijen Gridfinity, gerekend vanaf de achterkant (scharnier); de rijen ervoor krijgen een vlakke, 0.5 cm diepere vloer voor gereedschap (0 = overal Gridfinity)
gridfinity_rijen = 0; // [0:1:8]
// Bakjes klikken vast in de Gridfinity-bodem van de cassette: hoe ver de nokjes ingrijpen in mm (0 = geen klik)
cassette_klik = 0.3; // [0:0.05:0.6]
// Speling tussen bovenste bakje en deksel (klein = deksel klemt bakjes vast)
lid_gap = 0.4; // [0.2:0.1:1]
// Extra ruimte boven de bakjes in mm; alleen de deksel wordt hoger, de onderbak blijft gelijk
deksel_extra = 1.0; // [0:0.5:3]
// Diepte van de stickeruitsparing bovenop de deksel van de cassette in mm (0 = geen); de staalband ligt er nog dieper in, de sticker gaat eroverheen
cassette_sticker = 0.3; // [0:0.1:1]

/* [Cassette - magneten] */
// Magneten in de zijwanden en de bodem, en een baan voor zelfklevende staalband bovenop de deksel: cassettes klikken naast en op elkaar vast
magneten = true;
// Diameter van de magneten in mm
magneet_d = 6; // [4, 5, 6, 8, 10]
// Dikte van de magneten in mm (de wand wordt zo nodig dikker)
magneet_h = 2; // [1, 1.5, 2, 3, 4]
// Extra ruimte in het gat, op de diameter (0.1-0.2 = klemmend, met een druppel lijm vast)
magneet_speling = 0.2; // [0:0.05:0.4]
// Breedte van de zelfklevende staalband bovenop de deksel in mm
staalband_b = 12.7; // [10, 12, 12.7, 15, 19, 25]
// Dikte van de staalband in mm (de baan wordt zo diep, zodat de band vlak ligt)
staalband_t = 0.5; // [0.3:0.1:1]

/* [Printer] */
// Maat van je printbed in mm (vierkant)
bed = 350; // [180:10:400]

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
laag_hu  = 2.5;   // hoogte van een half bakje, in eenheden van 7 mm
c_skin   = 1.0;   // materiaal achter een magneet, aan de binnenkant
c_wall   = max(3.2, magneet_h + 0.2 + c_skin); // wanddikte (3,2 mm past bij magneten van 2 mm)
c_floor  = magneten ? max(1.2, magneet_h + 0.2 + c_skin) : 1.2; // bodem (dikker voor magneten)
top_t    = 2.0;   // dikte bovenkant deksel
c_lid_h  = 8;     // hoogte deksel zonder extra ruimte (bepaalt de hoogte van de onderbak)
d_lid_h  = c_lid_h + deksel_extra; // werkelijke hoogte deksel
tongue_h = 3;     // hoogte van de sluitrand (tong-en-groef)
c_fit    = 0.3;   // passpeling tong/groef, per kant
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
// De deksel wordt getekend alsof hij naar +x schuift en daarna gedraaid naar
// de gekozen kant. Wl x Dl is de maat van het bakje in dat gedraaide stelsel,
// nl het aantal vakken langs de sleuf.
sl_rot  = schuif == "achter" ? 90 : schuif == "links" ? 180 : schuif == "voor" ? 270 : 0;
Wl      = sl_rot % 180 == 0 ? W : D;
Dl      = sl_rot % 180 == 0 ? D : W;
nl      = sl_rot % 180 == 0 ? gy : gx;
lid_w   = Wl - (wall + lid_fit) - 0.3;          // lengte deksel (in schuifrichting)
lid_d   = Dl - open_i + 2 * groove - 2 * lid_fit; // breedte deksel
lid_x   = lid_w / 2 - (Wl / 2 - wall - lid_fit); // middelpunt deksel in gesloten stand


// Stickervlak: het deel van de deksel dat zichtbaar is als hij dicht zit
// (binnen de opening W - open_i), tussen de achterkant en de greepsleuf.
// Coordinaten ten opzichte van het midden van de deksel.
grip_x  = lid_w / 2 - 9;                                   // greepsleuf
label_x0 = -(Wl / 2 - open_i / 2) + 1 - lid_x;             // achterkant zichtbaar deel
label_x1 = grip_x - 1.5 - 1.5;                             // tot net voor de greepsleuf
label_y  = Dl - open_i - 2;

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
    difference() {
        union() {
            hull() { slice(35.6, 35.6, 0.8, 0);   slice(37.2, 37.2, 1.6, 0.8); }
            hull() { slice(37.2, 37.2, 1.6, 0.8); slice(37.2, 37.2, 1.6, 2.6); }
            hull() { slice(37.2, 37.2, 1.6, 2.6); slice(41.5, 41.5, 3.75, foot_h); }
        }
        // groefje rondom (45 graden flanken) waar de nokjes van de stapelrand
        // van het bakje eronder in vallen
        if (stapel_klik > 0 || cassette_klik > 0) difference() {
            translate([-25, -25, klik_z - groef]) cube([50, 50, 2 * groef]);
            hull() { slice(37.2, 37.2, 1.6, klik_z - groef); slice(37.2 - 2 * groef, 37.2 - 2 * groef, 0.8, klik_z); }
            hull() { slice(37.2 - 2 * groef, 37.2 - 2 * groef, 0.8, klik_z); slice(37.2, 37.2, 1.6, klik_z + groef); }
        }
    }
}

// Klik bij stapelen: hoogte van groefje (voet) en nokje (stapelrand), gemeten
// vanaf de onderkant van de voet, die in de stapelrand op de randbodem staat.
klik_z = 2.2;
// diepte van het groefje rondom de voet; de nokjes (stapel_klik, cassette_klik)
// grijpen er hoogstens zo ver in
groef = 0.8;

// Nokje in de stapelrand, gezien vanaf de buitenkant van de wand: a = afstand
// naar binnen, z = hoogte boven de onderkant van de stapelrand. De punt steekt
// stapel_klik voorbij het voetvlak van het bakje erboven (dat ligt 2,15 mm naar
// binnen) en valt bij gestapeld in het groefje.
module klik_nok(len) {
    a_tip = 2.15 + stapel_klik;
    p = a_tip - 0.9;
    rotate([90, 0, 0]) linear_extrude(len, center = true)
        polygon([[0.4, klik_z - p - 0.4], [0.9, klik_z - p], [a_tip, klik_z],
                 [0.9, klik_z + p], [0.4, klik_z + p + 0.4]]);
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

module cavity(w, d, lip = true) {
    c = 2 * wall;          // binnenmaat = buitenmaat - 2 wanden
    // recht deel, daarna 45 graden afschuining naar de stapelrand
    translate([0, 0, z_floor]) rsq(w - c, d - c, (41.5 - c - 34) / 2 + 0.5, Hb - 1.6 - z_floor + 0.01);
    hull() {
        slice(w - c, d - c, (41.5 - c - 34) / 2 + 0.5, Hb - 1.6);
        slice(w - 5.6, d - 5.6, (41.5 - 5.6 - 34) / 2, Hb + 0.01);
    }
    if (lip) translate([0, 0, Hb]) lip_cut(w, d);
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

module groove_cut() rotate([0, 0, sl_rot]) {
    // groef: achteraan dicht (aanslag), aan de schuifkant door de wand naar buiten
    hull() {
        translate([lid_x, 0, z_g0]) lid_shape(lid_fit);
        translate([lid_x + Wl, 0, z_g0]) lid_shape(lid_fit);
    }
    // opening tussen groef en stapelrand
    translate([0, 0, z_g1 - 0.01]) rsq(Wl - open_i, Dl - open_i, (41.5 - open_i - 34) / 2, ceil_t + 0.02);
}

// Breekbare steuntjes in de sleuf door de voorwand (+x), zodat de brug boven
// de sleuf niet te lang wordt. Dun in de schuifrichting: de deksel drukt ze
// er bij de eerste keer insteken uit.
module steuntjes() rotate([0, 0, sl_rot]) {
    n = steunen * nl;                  // per vak, gelijk verdeeld over de sleuf
    for (k = [1 : n])
        translate([Wl / 2 - wall / 2 - 0.2, -lid_d / 2 + k * lid_d / (n + 1) - 0.4, z_g0 - 0.01])
            cube([0.4, 0.8, lid_t + lid_fit + 0.02]);
}

// Indeling: aantal vakjes in x en y. Per vak = één vakje per 42 mm-vak.
nvx = vakken == "eigen" ? vakjes_x : vakken == "open" ? 1 : gx;
nvy = vakken == "eigen" ? vakjes_y : vakken == "open" ? 1 : gy;

// Voert children() uit op het midden van elk vakje, met de maat (w, d) van
// dat vakje als "buitenmaat" (zoals een los bakje: steek - 0,5 mm).
module vakjes() {
    px = (W + 0.5) / nvx;
    py = (D + 0.5) / nvy;
    for (i = [0 : nvx - 1], j = [0 : nvy - 1])
        translate([(i - (nvx - 1) / 2) * px, (j - (nvy - 1) / 2) * py, 0]) children();
}

module bakje() {
    vw = (W + 0.5) / nvx - 0.5;
    vd = (D + 0.5) / nvy - 0.5;
    if (deksel && steunen > 0) steuntjes();
    difference() {
        union() {
            for (i = [0 : gx - 1], j = [0 : gy - 1])
                translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, 0]) gf_foot();
            translate([0, 0, foot_h - 0.01]) rsq(W, D, 3.75, Hb + lip_h - foot_h + 0.01);
        }
        if (deksel) {
            vakjes() cavity_lid(vw, vd);
            groove_cut();
            translate([0, 0, Hb]) lip_cut(W, D);
        } else if (vakken == "per_vak") {
            // tussenwanden lopen door in de stapelrand (bakje erboven valt per vak vast)
            vakjes() cavity(vw, vd);
        } else {
            vakjes() cavity(vw, vd, lip = false);
            translate([0, 0, Hb]) lip_cut(W, D);
        }
    }
    // nokjes in de stapelrand, één per vak aan elke buitenkant
    if (stapel_klik > 0) translate([0, 0, Hb]) {
        for (j = [0 : gy - 1], side = [-1, 1])
            translate([side * W / 2, (j - (gy - 1) / 2) * G, 0])
                rotate([0, 0, side > 0 ? 180 : 0]) klik_nok(10);
        for (i = [0 : gx - 1], side = [-1, 1])
            translate([(i - (gx - 1) / 2) * G, side * D / 2, 0])
                rotate([0, 0, side > 0 ? 270 : 90]) klik_nok(10);
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

// Losse Gridfinity-bodem (open onderkant, zoals een gewone baseplate) met de
// klik-nokjes van de cassette. Voor een cassette die met een vlakke bodem is
// geprint: de bakjes staan met hun voeten op de bodem van de cassette, dus op
// dezelfde hoogte als met een ingebouwde Gridfinity-bodem. Buitenmaat
// gx x 42 bij gy x 42 mm: 0,25 mm speling rondom in de cassette.
module losse_baseplate() {
    difference() {
        rsq(gx * G, gy * G, cav_r, gf_base);
        for (i = [0 : gx - 1], j = [0 : gy - 1])
            translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, gf_base + 0.01])
                gf_socket();
    }
    if (cassette_klik > 0)
        for (i = [0 : gx - 1], j = [0 : gy - 1], r = [0 : 90 : 270])
            translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, 0])
                rotate([0, 0, r]) socket_nok();
}

// Inlegplaat: Gridfinity-voeten met een vlakke plaat erop, zonder wanden.
// Valt in de Gridfinity-bodem en maakt er een vlakke vloer van.
module inlegplaat() {
    for (i = [0 : gx - 1], j = [0 : gy - 1])
        translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, 0]) gf_foot();
    translate([0, 0, foot_h - 0.01]) rsq(W, D, 3.75, inleg_t + 0.01);
}

// deksel in gesloten stand (voor previews)
module schuifdeksel_dicht() {
    rotate([0, 0, sl_rot]) translate([lid_x, 0, z_g0]) schuifdeksel();
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
        // holte (de Gridfinity-bodem wordt er daarna weer in gezet)
        translate([0, 0, c_floor])
            rsq(cav_w, cav_d, cav_r, H_body + tongue_h + 1);
        pin_hole();
        if (magneten) { magnet_pockets(); bottom_magnets(); }
    }
    if (baseplate) baseplate_insert();
}

// Magneten en staalband.
//
// Naast elkaar (Packout): twee magneten per vak van 42 mm in elke zijwand, op
// vaste hoogte vanaf de bodem. Met de voorkant gelijk liggen ze altijd
// tegenover elkaar, hoe breed of hoog de cassettes ook zijn.
// Polariteit: in de gaten met een stipje gaan alle magneten met dezelfde kant
// naar buiten, in de gaten zonder stipje met de andere kant. Rechts zit het
// stipje bij het voorste gat van elk vak, links bij het achterste; zo trekt
// elke rechterkant elke linkerkant aan.
//
// Op elkaar (rugzak): een magneet per vak in de bodem, en bovenop de deksel per
// rij vakken een baan voor zelfklevende staalband over de hele breedte. Een
// magneet pakt overal op de band, dus het maakt niet uit hoe ver een cassette
// opzij ligt; ook de polariteit doet er hier niet toe.
function mag_d() = magneet_d + magneet_speling;

// één gat met (optioneel) stipje, vanaf het oppervlak de holte in langs +z
module mag_hole(dot) {
    translate([0, 0, -0.01]) cylinder(d = mag_d(), h = magneet_h + 0.2 + 0.01);
    if (dot) translate([mag_d() / 2 + 2, 0, -0.01]) cylinder(d = 1.6, h = 0.5);
}

module magnet_pockets() {
    zc = c_floor + 1 + mag_d() / 2;
    for (side = [-1, 1], j = [0 : gy - 1], k = [-1, 1])
        translate([side * out_w / 2, (j - (gy - 1) / 2) * G + k * G / 4, zc])
            rotate([0, side * -90, 0]) rotate([0, 0, 90]) mag_hole(side * k < 0);
}

// één magneet per vak in de bodem, in het midden van het vak
module bottom_magnets() {
    for (i = [0 : gx - 1], j = [0 : gy - 1])
        translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, 0]) mag_hole(false);
}

// baan voor staalband bovenop de deksel, per rij vakken over de hele breedte
module steel_strips() {
    for (j = [0 : gy - 1])
        translate([0, (j - (gy - 1) / 2) * G, H_body + d_lid_h - cassette_sticker - staalband_t])
            rsq(out_w - 4, staalband_b + 0.4, 0.5, staalband_t + cassette_sticker + 1);
}

// Stickervlak bovenop de deksel: bijna de hele bovenkant, 5 mm van de rand.
sticker_c = [out_w - 10, out_d - 10];
module cassette_sticker_cut() {
    translate([0, 0, H_body + d_lid_h - cassette_sticker])
        rsq(sticker_c[0], sticker_c[1], 3, cassette_sticker + 1);
}

// Gridfinity-bodem in de cassette: over alle rijen, of alleen over de
// achterste gridfinity_rijen rijen (dan 2 mm extra rand naar voren, zodat de
// voorste vakken ook een voorwand hebben).
bp_rijen = gridfinity_rijen == 0 ? gy : min(gridfinity_rijen, gy);
bp_y0    = gridfinity_rijen == 0 ? -cav_d / 2 - 1
                                 : (gy - bp_rijen - (gy - 1) / 2) * G - G / 2 - 2;

module baseplate_insert() {
    translate([0, 0, c_floor]) {
        difference() {
            intersection() {
                // 0,01 mm in vloer en wanden, zodat het één dicht geheel wordt
                translate([0, 0, -0.01]) rsq(cav_w + 0.02, cav_d + 0.02, cav_r, gf_base + 0.01);
                translate([-cav_w, bp_y0, -1]) cube([2 * cav_w, 2 * cav_d, gf_base + 2]);
            }
            for (i = [0 : gx - 1], j = [gy - bp_rijen : gy - 1])
                translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, gf_base + 0.01])
                    gf_socket();
        }
        // klik-nokjes: aan elke kant van elk vak, in het rechte stuk van de
        // uitsparing, op de hoogte van het groefje in de bakvoet
        if (cassette_klik > 0)
            for (i = [0 : gx - 1], j = [gy - bp_rijen : gy - 1], r = [0 : 90 : 270])
                translate([(i - (gx - 1) / 2) * G, (j - (gy - 1) / 2) * G, 0])
                    rotate([0, 0, r]) socket_nok();
    }
}

// Nokje op de wand van een baseplate-uitsparing (half 18,85 mm vanaf het
// midden). De punt steekt cassette_klik voorbij het voetvlak (18,6 mm) en valt
// bij een geplaatst bakje in het groefje.
module socket_nok() {
    a_tip = 18.6 - cassette_klik;
    p = 18.85 - a_tip;
    // driehoek met de achterkant ruim in de wand (20 mm), zodat het nokje de
    // schuine wand van de uitsparing niet net raakt maar er echt in zit
    rotate([90, 0, 0]) linear_extrude(8, center = true)
        polygon([[20, klik_z - p - (20 - 18.85)], [a_tip, klik_z],
                 [20, klik_z + p + (20 - 18.85)]]);
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
            translate([0, 0, H_body]) rsq(out_w, out_d, out_r, d_lid_h);
            knuckles(true);
        }
        // binnenruimte deksel
        translate([0, 0, H_body - 1]) rsq(cav_w, cav_d, cav_r, d_lid_h - top_t + 1);
        // groef voor de tong
        translate([0, 0, H_body - 1]) tongue_ring(tongue_h + c_fit + 1, c_fit);
        pin_hole();
        if (magneten) steel_strips();
        if (cassette_sticker > 0) cassette_sticker_cut();
    }
    for (x = latch_xs()) latch_arm(x);
}

// verende klikbeugel aan de voorkant van het deksel
module latch_arm(x) {
    off = ridge_d + 0.3;                 // afstand veer tot bodywand
    y_in = -out_d / 2 - off;             // binnenkant van de veer
    translate([x - latch_w / 2, 0, 0]) {
        // bevestigingsblok op het deksel
        translate([0, y_in - latch_t, H_body + 1]) cube([latch_w, off + latch_t + 0.5, d_lid_h - 1]);
        // veer
        translate([0, y_in - latch_t, H_body - latch_len]) cube([latch_w, latch_t, latch_len + d_lid_h]);
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
    translate([0, 0, H_body + d_lid_h]) rotate([180, 0, 0]) cassette_deksel();
}

if (onderdeel == "bakje") bakje();
else if (onderdeel == "schuifdeksel") schuifdeksel();
else if (onderdeel == "bakje_en_deksel") {
    bakje();
    if (deksel) translate([0, D / 2 + 10 + lid_d / 2, 0]) schuifdeksel();
}
else if (onderdeel == "cassette_onderbak") cassette_body();
else if (onderdeel == "cassette_deksel") cassette_deksel_print();
else if (onderdeel == "cassette_beide") {
    cassette_body();
    translate([0, out_d + 20, 0]) cassette_deksel_print();
}
else if (onderdeel == "inlegplaat") inlegplaat();
else if (onderdeel == "baseplate") losse_baseplate();
// proefstukjes voor de klik: alleen de voeten, of alleen de stapelrand
else if (onderdeel == "test_voet") intersection() {
    bakje(); translate([0, 0, -1]) rsq(W + 2, D + 2, 1, foot_h + 2.2);
}
else if (onderdeel == "test_rand") translate([0, 0, -(Hb - 1.2)]) intersection() {
    bakje(); translate([0, 0, Hb - 1.2]) rsq(W + 2, D + 2, 1, lip_h + 2);
}
else if (onderdeel == "voorbeeld_bakje") { bakje(); if (deksel) schuifdeksel_dicht(); }
else if (onderdeel == "voorbeeld_cassette") { cassette_body(); cassette_deksel(); }

is_cassette = onderdeel == "cassette_onderbak" || onderdeel == "cassette_deksel"
           || onderdeel == "cassette_beide" || onderdeel == "voorbeeld_cassette";

// ruimte op het bed (x, y) per onderdeel
c_ext_d = out_d + 2 * kr + 0.3 + ridge_d + 0.3 + latch_t + 2;  // incl. scharnier en klikbeugels
footprint =
    onderdeel == "schuifdeksel"    ? [lid_w, lid_d] :
    onderdeel == "bakje_en_deksel" ? [max(W, lid_w), D + 10 + lid_d] :
    onderdeel == "cassette_beide"  ? [out_w, 2 * c_ext_d + 20] :
    is_cassette                    ? [out_w, c_ext_d] :
                                     [W, D];

function cm(mm) = round(mm) / 10;

assert(footprint[0] <= bed && footprint[1] <= bed,
       str("Past niet op je printbed van ", cm(bed), " cm: dit onderdeel is ",
           cm(footprint[0]), " x ", cm(footprint[1]), " cm. Kies minder vakken",
           onderdeel == "bakje_en_deksel" || onderdeel == "cassette_beide"
               ? " of print de onderdelen los." : "."));

if (is_cassette) {
    echo(str("Cassette ", gx, "x", gy, ": ", cm(out_w), " x ", cm(c_ext_d), " x ",
             cm(H_body + d_lid_h), " cm (b x d x h, dicht, incl. scharnier en klikbeugels)"));
    if (cassette_sticker > 0)
        echo(str("Stickervlak op de deksel: ", cm(sticker_c[0]), " x ", cm(sticker_c[1]), " cm"));
} else if (onderdeel == "baseplate") {
    echo(str("Losse Gridfinity-bodem ", gx, "x", gy, ": ", cm(gx * G), " x ", cm(gy * G),
             " x ", gf_base / 10, " cm"));
} else if (onderdeel == "inlegplaat") {
    echo(str("Inlegplaat ", gx, "x", gy, ": ", cm(W), " x ", cm(D), " cm, vloer ",
             foot_h + inleg_t, " mm boven de bodem van de cassette"));
} else {
    if (deksel && label_d > 0)
        echo(str("Stickervlak op de deksel: ", cm(label_x1 - label_x0), " x ", cm(label_y), " cm"));
    echo(str("Bakje ", gx, "x", gy, ": ", cm(W), " x ", cm(D), " x ", cm(Hb + lip_h),
             " cm (stapelt per ", Hb / 10, " cm)"));
}
