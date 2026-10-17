// Gridfinity draagcassette — afsluitbare doos met Gridfinity-bodem binnenin.
// Past in een Milwaukee Packout-koffer én in een rugzak: je pakt de cassette
// over, niet de inhoud.
//
// Onderdelen: body (onderbak met baseplate-patroon), lid (deksel met
// scharnier-knokkels en klikbeugels). Scharnierpen = stukje 1,75 mm filament.
//
// Render:  openscad -D 'part="body"' -o body.stl cassette.scad
//          openscad -D 'part="lid"'  -o lid.stl  cassette.scad

/* [Formaat] */
gx = 4;          // breedte in Gridfinity-eenheden (42 mm)
gy = 2;          // diepte in Gridfinity-eenheden
hu = 3;          // hoogte van de bakjes erin, in eenheden van 7 mm
bin_lip = 4.4;   // stapelrand bovenop de bakjes (0 als je bakjes zonder rand print)
lid_gap = 0.4;   // speling tussen bakje en deksel: klein = deksel klemt bakjes vast

/* [Opties] */
baseplate = true; // false = vlakke bodem (voor schuim/TPU-inleg, bv. schroevendraaiers)
part = "both";    // body | lid | both | assembled

/* [Constructie] */
wall   = 2.4;    // wanddikte
floor_t = 1.2;   // bodem onder het baseplate-patroon
top_t  = 2.0;    // dikte deksel
lid_h  = 8;      // totale hoogte deksel
tongue_h = 3;    // hoogte van de sluitrand (tong-en-groef)
fit    = 0.2;    // passpeling tong/groef

/* [Scharnier] */
kr      = 3.5;   // straal knokkel
pin_d   = 2.0;   // gat voor 1,75 mm filament
k_gap   = 0.4;   // speling tussen knokkels
k_count = 5;     // aantal knokkels (oneven: body heeft de buitenste)

/* [Klikbeugel] */
latch_w   = 18;
latch_t   = 1.8;  // dikte van de veer
latch_len = 12;   // lengte onder de scheidingslijn
ridge_d   = 1.2;  // hoe ver de nok uitsteekt

$fn = 48;

// ---- afgeleide maten ----
G       = 42;
gf_base = 4.65;                                  // hoogte baseplate-profiel
cav_w   = gx * G + 0.5;
cav_d   = gy * G + 0.5;
cav_r   = 4;
out_w   = cav_w + 2 * wall;
out_d   = cav_d + 2 * wall;
out_r   = cav_r + wall;
inner_h = hu * 7 + bin_lip + lid_gap; // vanaf bodemvloer
H_body  = floor_t + inner_h - (lid_h - top_t);  // scheidingslijn body/deksel
k_axis_y = out_d + kr + 0.3;                    // scharnieras (y), achterkant

// ---- hulpvormen ----
module rsq(w, d, r, h) {
    linear_extrude(h)
        offset(r = r) square([w - 2 * r, d - 2 * r], center = true);
}

// afgeronde rechthoek, gecentreerd in xy, met dunne schijf op hoogte z
module slice(w, d, r, z) { translate([0, 0, z]) rsq(w, d, max(r, 0.01), 0.01); }

// Eén Gridfinity baseplate-uitsparing (42 mm), top op z = 0, naar beneden
module gf_socket() {
    hull() {
        slice(42,   42,   4,    -0.01 + 0.01);
        slice(37.7, 37.7, 1.85, -2.15);
    }
    hull() {
        slice(37.7, 37.7, 1.85, -2.15);
        slice(37.7, 37.7, 1.85, -3.95);
    }
    hull() {
        slice(37.7, 37.7, 1.85, -3.95);
        slice(36.3, 36.3, 1.15, -gf_base - 0.01);
    }
}

// rand die de tong vormt: tussen holte en holte + halve wand
module tongue_ring(h, grow = 0) {
    difference() {
        rsq(cav_w + wall + 2 * grow, cav_d + wall + 2 * grow, cav_r + wall / 2 + grow, h);
        translate([0, 0, -1]) rsq(cav_w - 2 * grow, cav_d - 2 * grow, max(cav_r - grow, 0.5), h + 2);
    }
}

// knokkelsegmenten langs x; body krijgt even indices, deksel oneven
module knuckles(for_lid) {
    seg = (out_w - 2 * out_r - (k_count - 1) * k_gap) / k_count;
    x0  = -out_w / 2 + out_r;
    for (i = [0 : k_count - 1])
        if ((i % 2 == 1) == for_lid)
            translate([x0 + i * (seg + k_gap), 0, 0]) {
                hull() {
                    translate([0, k_axis_y - out_d / 2, H_body])
                        rotate([0, 90, 0]) cylinder(r = kr, h = seg);
                    // steunblok tegen de achterwand, onder (body) of boven (deksel)
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

// ---- body ----
module body() {
    difference() {
        union() {
            rsq(out_w, out_d, out_r, H_body);
            translate([0, 0, H_body - 0.01]) tongue_ring(tongue_h + 0.01);
            knuckles(false);
            // nokken voor de klikbeugels (voorkant, y = -out_d/2)
            for (x = latch_xs()) latch_ridge(x);
        }
        // holte
        translate([0, 0, floor_t + (baseplate ? gf_base : 0)])
            rsq(cav_w, cav_d, cav_r, H_body + tongue_h + 1);
        pin_hole();
    }
    if (baseplate) baseplate_insert();
}

module baseplate_insert() {
    translate([0, 0, floor_t])
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
module lid() {
    difference() {
        union() {
            translate([0, 0, H_body]) rsq(out_w, out_d, out_r, lid_h);
            knuckles(true);
        }
        // binnenruimte deksel
        translate([0, 0, H_body - 1]) rsq(cav_w, cav_d, cav_r, lid_h - top_t + 1);
        // groef voor de tong
        translate([0, 0, H_body - 1]) tongue_ring(tongue_h + fit + 1, fit);
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
        translate([0, y_in - latch_t, H_body + 1]) cube([latch_w, off + latch_t + 0.5, lid_h - 1]);
        // veer
        translate([0, y_in - latch_t, H_body - latch_len]) cube([latch_w, latch_t, latch_len + lid_h]);
        // haak: vlakke bovenkant, schuine onderkant
        translate([0, y_in, H_body - latch_len])
            rotate([90, 0, 90]) linear_extrude(latch_w)
                polygon([[-0.01, 0], [ridge_d, 1.2], [ridge_d, 2.5], [-0.01, 2.5]]);
        // trekrand om te openen
        translate([0, y_in - latch_t - 2, H_body - latch_len]) cube([latch_w, 2 + 0.01, 1.6]);
    }
}

// ---- uitvoer ----
if (part == "body") body();
else if (part == "lid") translate([0, 0, H_body + lid_h]) rotate([180, 0, 0]) lid();
else if (part == "assembled") { body(); lid(); }
else if (part == "both") {
    body();
    translate([0, out_d + 20, H_body + lid_h]) rotate([180, 0, 0]) lid();
}

echo(str("Buitenmaat romp: ", out_w, " x ", out_d, " mm, hoogte gesloten: ", H_body + lid_h, " mm"));
echo(str("Inclusief scharnier en klikbeugels: diepte ~", out_d + 2 * kr + 0.3 + ridge_d + 0.3 + latch_t + 2, " mm"));
