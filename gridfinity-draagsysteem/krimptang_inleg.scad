// Inleg voor de krimptang-cassette (5 x 4, voorste twee rijen)
// ===============================================================
// Een dunne vloer met daarop alleen wat de tang vasthoudt (geen rand eromheen,
// dat scheelt materiaal):
//  - verende halve bogen aan de kopse kanten: een tegen de kop en een tegen
//    het einde van elk handvat (houden de tang in de lengte op spanning);
//  - een "paddenstoel" in het midden, tussen de handvatten: twee pootjes die
//    bovenaan met een halve boog verbonden zijn (een veer in de vorm van een
//    omgekeerde U), met aan de buitenkant een ratel van haakjes die over de
//    binnenrand van de handvatten vallen; elk hoger haakje steekt iets verder
//    uit. De haakjes zijn driehoekig (45 graden boven en onder), zodat alles
//    zonder support print. Van opzij lijkt het een champignon.
//    Bij het indrukken veert de boog in en klikt de tang onder het eerste
//    haakje dat past; door de meerdere niveaus maakt een paar mm verschil in
//    de hoogte van de handvatten niet uit. De tang kan dan niet meer omhoog
//    en ook niet opzij.
//
// De vorm is overgetrokken van een foto (op A4-papier, gecorrigeerd voor
// perspectief en de hoogte van de tang boven het papier) en schaalt mee met
// tang_lengte en tang_breedte. Meet je tang na (handvatten in rust), en meet
// hoe hoog de handvatten zijn als de tang plat ligt (handvat_hoogte).
//
// Het frame ligt op de vlakke bodem van de cassette, in de voorste twee rijen
// (voor een losse Gridfinity-bodem in de achterste twee rijen). Leg de tang
// met de stelknop naar boven.

/* [Tang] */
// Totale lengte van de tang in mm (kop tot einde handvatten)
tang_lengte = 181; // [150:1:205]
// Grootste breedte van de tang in mm (handvatten in rust)
tang_breedte = 73; // [50:1:79]
// Hoogte van de handvatten als de tang plat ligt, in mm (hier grijpen de haakjes overheen)
handvat_hoogte = 24; // [15:0.5:35]
// Kop links of rechts in de cassette
kop = "links"; // [links, rechts]

/* [Uitsparing en bogen] */
// Ruimte rondom de tang in mm
ruim = 3; // [1:0.5:6]
// Kleine inhammen in de omtrek dichtgooien tot deze straal, voor een gladde rand
glad = 6; // [0:1:12]
// Hoe ver de bogen in de tang drukken als hij erin ligt, in mm
voorspanning = 1.0; // [0:0.25:3]
// Dikte van de bogen in mm (dunner = slapper)
boog_t = 1.2; // [0.8:0.1:2.4]

/* [Paddenstoel] */
// Plek tussen de handvatten (0 = midden van de tang, 0.5 = einde handvatten)
pad_x = 0.23; // [0.05:0.01:0.4]
// Speling tussen pootje en binnenrand van het handvat in mm
pad_speling = 1.0; // [0:0.25:2]
// Hoe ver het bovenste haakje over het handvat grijpt in mm
pad_haak = 2.5; // [1:0.5:4]
// Hoeveel elk lager haakje minder ver uitsteekt in mm
pad_groei = 0.5; // [0:0.1:1]
// Aantal klik-niveaus (haakjes onder elkaar)
pad_niveaus = 3; // [1:1:5]
// Afstand tussen de klik-niveaus in mm (groter = diepere inkeping, steviger klik)
pad_stap = 2.0; // [1:0.25:3]
// Hoogte van de boog boven de pootjes in mm
pad_boog = 5; // [3:0.5:10]
// Dikte van pootjes en boog in mm (dunner = slapper)
pad_t = 2.0; // [1.2:0.2:4]
// Lengte van de paddenstoel (langs de tang) in mm
pad_l = 12; // [8:1:24]

/* [Inleg] */
// Hoogte van de blokjes waar de bogen aan vastzitten in mm
hoogte = 10; // [6:1:30]
// Dikte van de vloer onder de tang in mm (houdt de paddenstoel op zijn plek)
vloer_t = 1.2; // [0.8:0.2:3]
// Breedte van de inleg: binnenmaat van de cassette (5 vakken = 210,5 mm) min speling
frame_b = 210; // [100:0.5:340]
// Diepte van de inleg: tot aan de losse Gridfinity-bodem (2 vakken) min speling
frame_d = 83.75; // [40:0.25:200]

/* [Hidden] */
$fn = 96;
L = tang_lengte;
B = tang_breedte;

// Omtrek van de tang, genormaliseerd naar lengte 1 en breedte 1, kop bij x < 0
tang_omtrek = [
    [-0.4998, 0.0286], [-0.4932, 0.0960], [-0.4805, 0.1576], [-0.4632, 0.2083],
    [-0.4395, 0.2509], [-0.4211, 0.2711], [-0.4018, 0.2828], [-0.3707, 0.2841],
    [-0.3482, 0.2768], [-0.3101, 0.2981], [-0.3046, 0.3068], [-0.3041, 0.3470],
    [-0.2956, 0.3834], [-0.2880, 0.4022], [-0.2842, 0.4018], [-0.2812, 0.4149],
    [-0.2631, 0.4316], [-0.2468, 0.4330], [-0.2334, 0.4265], [-0.2196, 0.4076],
    [-0.2105, 0.3861], [-0.1516, 0.3833], [-0.1594, 0.3871], [-0.1607, 0.3954],
    [-0.1569, 0.4196], [-0.1502, 0.4271], [-0.1526, 0.4703], [-0.1493, 0.4893],
    [-0.1443, 0.5000], [-0.1332, 0.4917], [-0.1098, 0.4464], [-0.0909, 0.4260],
    [-0.0811, 0.4271], [-0.0786, 0.4187], [-0.0729, 0.4160], [-0.0680, 0.4328],
    [-0.0606, 0.4412], [-0.0390, 0.4409], [-0.0320, 0.4524], [-0.0145, 0.4505],
    [-0.0101, 0.4419], [-0.0076, 0.4478], [-0.0023, 0.4472], [0.0005, 0.4398],
    [0.0171, 0.4472], [0.0195, 0.4408], [0.0377, 0.4389], [0.0433, 0.4303],
    [0.0494, 0.4316], [0.0578, 0.4217], [0.0763, 0.4187], [0.0779, 0.4296],
    [0.0848, 0.4319], [0.0880, 0.4286], [0.0891, 0.4184], [0.0916, 0.4312],
    [0.1084, 0.4234], [0.1100, 0.4303], [0.1148, 0.4308], [0.1172, 0.4406],
    [0.1216, 0.4371], [0.1223, 0.4260], [0.1252, 0.4377], [0.1351, 0.4387],
    [0.1614, 0.4299], [0.1646, 0.4375], [0.1852, 0.4333], [0.1872, 0.4391],
    [0.2042, 0.4373], [0.2065, 0.4451], [0.2109, 0.4366], [0.2231, 0.4353],
    [0.2255, 0.4430], [0.2357, 0.4439], [0.2381, 0.4536], [0.2604, 0.4472],
    [0.2628, 0.4549], [0.2792, 0.4532], [0.2875, 0.4602], [0.3062, 0.4621],
    [0.3128, 0.4575], [0.3249, 0.4720], [0.3354, 0.4708], [0.3377, 0.4765],
    [0.3427, 0.4700], [0.3586, 0.4722], [0.3609, 0.4621], [0.3667, 0.4615],
    [0.3691, 0.4751], [0.3733, 0.4667], [0.3872, 0.4652], [0.3922, 0.4745],
    [0.4014, 0.4606], [0.4033, 0.4516], [0.4156, 0.4502], [0.4260, 0.4589],
    [0.4513, 0.4650], [0.4680, 0.4543], [0.4836, 0.4261], [0.4885, 0.4001],
    [0.4940, 0.3241], [0.4927, -0.2487], [0.4992, -0.2707], [0.5002, -0.3030],
    [0.4947, -0.3810], [0.4810, -0.4214], [0.4611, -0.4489], [0.4320, -0.4632],
    [0.3971, -0.4674], [0.3767, -0.4615], [0.3532, -0.4436], [0.3326, -0.4356],
    [0.1465, -0.4064], [0.0991, -0.3929], [0.0328, -0.3632], [0.0175, -0.3634],
    [-0.0113, -0.3740], [-0.0345, -0.3971], [-0.0648, -0.4454], [-0.0846, -0.4943],
    [-0.0936, -0.5000], [-0.0993, -0.4926], [-0.1042, -0.4761], [-0.1319, -0.3075],
    [-0.1364, -0.3022], [-0.4033, -0.2964], [-0.4195, -0.2851], [-0.4443, -0.2566],
    [-0.4730, -0.1934], [-0.4880, -0.1372], [-0.4991, -0.0529]
];

// Gemeten aan de foto (genormaliseerd):
kop_y = -0.007;                         // midden van de kop
tips = [[0.491, 0.311], [0.497, -0.295]]; // uiteinden van de handvatten
// binnenranden van de handvatten op twee plekken: [x, y onder, y boven]
rand1 = [0.193, -0.121, 0.171];
rand2 = [0.271, -0.150, 0.195];

module tang_2d() scale([L, B]) polygon(tang_omtrek);

// ruime, gladde uitsparing (zonder het gat tussen de handvatten)
module zak_2d() offset(r = ruim) offset(r = -glad) offset(r = glad) tang_2d();

// Halve boog (verende strip) met de koorde op y = 0, bolling naar +y met de
// top op y = ruim + voorspanning, plus ankers aan beide uiteinden in de wand.
module boog_2d(c) {
    b = ruim + voorspanning;
    R = (c * c / 4 + b * b) / (2 * b);
    intersection() {
        translate([0, b - R]) difference() { circle(R); circle(R - boog_t); }
        translate([-c, 0]) square([2 * c, b + 1]);
    }
    for (s = [-1, 1]) translate([s * c / 2 - 2, -4]) square([4, 4.5]);
}

module rechthoek() offset(r = 4) square([frame_b - 8, frame_d - 8], center = true);

// Blokje achter een boog: van de koorde tot de rand van de inleg, iets breder
// dan de boog, zonder de ruimte voor de tang.
module blokje_2d(c) {
    translate([-c / 2 - 6, -30]) square([c + 12, 30.01]);
}

module bogen_2d() {
    intersection() {
        rechthoek();
        difference() {
            union() {
                // tegen de kop
                translate([-L / 2 - ruim, kop_y * B]) rotate(-90) { boog_2d(26); blokje_2d(26); }
                // tegen het einde van elk handvat
                for (t = tips) translate([L / 2 + ruim, t[1] * B]) rotate(90) { boog_2d(18); blokje_2d(18); }
            }
            difference() { zak_2d(); union() {
                translate([-L / 2 - ruim, kop_y * B]) rotate(-90) boog_2d(26);
                for (t = tips) translate([L / 2 + ruim, t[1] * B]) rotate(90) boog_2d(18);
            } }
        }
    }
}

// Paddenstoel: twee pootjes evenwijdig aan de tang, bovenaan verbonden met
// een halve (afgeplatte) boog, met een ratel van haakjes aan de buitenkant.
// Het middelste klik-niveau ligt op handvat_hoogte; de andere pad_stap mm
// erboven en eronder.
function rand_y(k) = (rand1[k] + (rand2[k] - rand1[k]) * (pad_x - rand1[0]) / (rand2[0] - rand1[0])) * B;

module paddenstoel() {
    yo = rand_y(2) - pad_speling;          // buitenvlak bovenste pootje
    yu = rand_y(1) + pad_speling;          // buitenvlak onderste pootje
    ym = (yo + yu) / 2;
    hw = (yo - yu) / 2;                    // halve breedte, buitenvlak
    n  = pad_niveaus;
    z0 = handvat_hoogte + 0.3 - (n - 1) / 2 * pad_stap;   // punt onderste haakje
    zt = z0 + (n - 1) * pad_stap + pad_haak;              // bovenkant pootjes
    translate([pad_x * L, ym, 0]) rotate([90, 0, 90]) linear_extrude(pad_l, center = true) {
        // pootjes met een halve (afgeplatte) boog erover; van binnen een spits
        // dak van 45 graden, zodat er geen vlak plafond is (print zonder support)
        wi = hw - pad_t;                                  // halve binnenbreedte
        zs = zt + pad_boog - pad_t - wi;                  // begin van het dak
        difference() {
            union() {
                translate([-hw, 0]) square([2 * hw, zt]);
                translate([0, zt]) intersection() {
                    scale([hw, pad_boog]) circle(1);
                    translate([-hw, 0]) square([2 * hw, pad_boog]);
                }
            }
            polygon([[-wi, -1], [wi, -1], [wi, zs], [0, zs + wi], [-wi, zs]]);
        }
        // ratel: per niveau een driehoekig haakje met 45 graden boven en onder
        // (print zonder support); samen een kartelrand die naar boven breder
        // wordt. De bovenrand van het handvat valt in een van de inkepingen.
        for (s = [-1, 1], i = [0 : n - 1]) {
            h = pad_haak - (n - 1 - i) * pad_groei;   // naar boven steeds iets breder
            translate([s * hw, z0 + i * pad_stap]) mirror([s < 0 ? 1 : 0, 0])
                polygon([[-0.01, -h], [h, 0], [-0.01, h]]);
        }
    }
}

mirror([kop == "rechts" ? 1 : 0, 0, 0]) {
    linear_extrude(vloer_t) rechthoek();
    linear_extrude(hoogte) bogen_2d();
    translate([0, 0, vloer_t - 0.01]) paddenstoel();
}

echo(str("Inleg ", frame_b / 10, " x ", frame_d / 10, " cm; tang ", L / 10, " x ", B / 10, " cm; klik-niveaus rond ", handvat_hoogte,
         " mm boven de vloer; paddenstoel ",
         vloer_t + handvat_hoogte + 0.3 + (pad_niveaus - 1) / 2 * pad_stap + pad_haak + pad_boog,
         " mm hoog (cassette binnen: 39,8 mm)"));
