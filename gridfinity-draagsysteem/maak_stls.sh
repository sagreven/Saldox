#!/bin/sh
# Maakt de standaardset STL's in stl/ opnieuw uit generator.scad.
# Gebruik: ./maak_stls.sh   (OpenSCAD moet geïnstalleerd zijn)
set -e
cd "$(dirname "$0")"
rm -rf stl && mkdir -p stl

gen() { # uitvoerbestand, gevolgd door -D instellingen
    out=$1; shift
    echo "stl/$out.stl"
    openscad -q "$@" -o "stl/$out.stl" generator.scad
}

# bakjes: half (basis) en heel
for maat in "1 1 per_vak 1x1" "2 1 per_vak 2x1-vakjes" "2 2 per_vak 2x2-vakjes" \
            "2 1 open 2x1-open" "2 2 open 2x2-open" "4 1 open 4x1-open"; do
    set -- $maat
    gen "bakje-$4-half" -D 'onderdeel="bakje"' -D gx=$1 -D gy=$2 -D "vakken=\"$3\"" -D hu=2.5
done
for maat in "1 1 per_vak 1x1" "2 1 per_vak 2x1-vakjes" "2 2 per_vak 2x2-vakjes"; do
    set -- $maat
    gen "bakje-$4-heel" -D 'onderdeel="bakje"' -D gx=$1 -D gy=$2 -D "vakken=\"$3\"" -D hu=5
done

gen bakje-2x2-2vakjes-heel -D 'onderdeel="bakje"' -D gx=2 -D gy=2 -D hu=5 \
    -D 'vakken="eigen"' -D vakjes_x=2 -D vakjes_y=1

# schuifdeksels: passen op half en heel
for maat in "1 1" "2 1" "2 2" "4 1"; do
    set -- $maat
    gen "schuifdeksel-${1}x${2}" -D 'onderdeel="schuifdeksel"' -D gx=$1 -D gy=$2
done

# cassettes: naam = vakken en hoogte dicht (met magneten)
for c in "2 2 2 true 2x2-4.5cm-schroeven" "5 2 2 false 5x2-4.5cm-schroevendraaiers" \
         "5 3 2 true 5x3-4.5cm-krimptang" \
         "4 2 2 true 4x2-4.5cm" "4 2 4 true 4x2-8.0cm"; do
    set -- $c
    gen "cassette-$5-onderbak" -D 'onderdeel="cassette_onderbak"' -D gx=$1 -D gy=$2 -D lagen=$3 -D baseplate=$4
    gen "cassette-$5-deksel"   -D 'onderdeel="cassette_deksel"'   -D gx=$1 -D gy=$2 -D lagen=$3 -D baseplate=$4
done
