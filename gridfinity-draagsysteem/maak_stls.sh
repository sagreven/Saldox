#!/bin/sh
# Maakt de standaardset STL's in stl/ opnieuw uit generator.scad.
# Gebruik: ./maak_stls.sh   (OpenSCAD moet geïnstalleerd zijn)
set -e
cd "$(dirname "$0")"
mkdir -p stl

gen() { # uitvoerbestand, gevolgd door -D instellingen
    out=$1; shift
    echo "stl/$out.stl"
    openscad -q "$@" -o "stl/$out.stl" generator.scad
}

for maat in "1 1 per_vak 1x1" "2 1 per_vak 2x1-vakjes" "2 2 per_vak 2x2-vakjes" \
            "2 1 open 2x1-open" "2 2 open 2x2-open" "4 1 open 4x1-open"; do
    set -- $maat
    gen "bakje-$4" -D 'onderdeel="bakje"' -D gx=$1 -D gy=$2 -D "vakken=\"$3\""
done
gen bakje-1x1-half -D 'onderdeel="bakje"' -D gx=1 -D gy=1 -D hu=2.5

for maat in "1 1" "2 1" "2 2" "4 1"; do
    set -- $maat
    gen "schuifdeksel-${1}x${2}" -D 'onderdeel="schuifdeksel"' -D gx=$1 -D gy=$2
done

for c in "4 2 1 true 4x2-1laag" "4 2 2 true 4x2-2lagen" "5 2 1 false 5x2-schroevendraaiers"; do
    set -- $c
    gen "cassette-$5-body" -D 'onderdeel="cassette_onderbak"' -D gx=$1 -D gy=$2 -D lagen=$3 -D baseplate=$4
    gen "cassette-$5-lid"  -D 'onderdeel="cassette_deksel"'   -D gx=$1 -D gy=$2 -D lagen=$3 -D baseplate=$4
done
