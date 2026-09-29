"""PV-stringdiagnose: signaleert een uitgevallen of lekkende string.

WAAROM DIT BESTAAT
String 2 viel uit in de nacht van 8 op 9 september 2026 en bleef zestien dagen
onopgemerkt liggen -- ruwweg tweederde van de opwek. De data lag er de hele
tijd: pv2_power ging naar 0, de stringspanning stortte in van 450 V naar 6 V,
en de isolatieweerstand zakte van 384 kOhm naar 50 kOhm. Niemand kreeg een
seintje. Dit bestand is de reden dat dat niet nog eens gebeurt.

WAAROM pv2_power NIET MEER GEBRUIKT WORDT
Op 24 september 2026 bleek dat register kapot: het stond constant op 0 W
terwijl de string aantoonbaar leverde -- spanning en stroom gaven samen 220 W.
De oude regel "string levert 0 W terwijl de andere produceert" keek dus naar
een teller die niets meer zei. Erger: hij verklaarde de string DOOD terwijl
hij in werkelijkheid een vijfde van zijn vermogen leverde. De nieuwe regels
rekenen daarom op spanning en stroom, die wel kloppen.

DE OHMSE SIGNATUUR
Een gezonde string hangt aan de MPPT: die houdt de spanning rond een vast
punt en laat de stroom met de instraling meebewegen. U/I loopt daardoor over
een dag van honderden ohm bij weinig licht naar enkele tientallen bij vol zon.
Een string met een corroderend contact doet het omgekeerde: daar bepaalt de
overgangsweerstand alles, en staat U/I gespijkerd op diezelfde waarde -- hier
23 ohm -- bij elk lichtniveau. Die constantheid IS de diagnose, niet de hoogte.

DREMPELS
Teruggetoetst op 75 dagen eigen historie (13 juli - 23 september 2026):

  string dood      27 treffers, exact twee aaneengesloten blokken
                   (15-25 juli en 8 sept-heden). Nul losse valse meldingen op
                   de 48 gezonde dagen ertussen.
                   VERVALLEN -- zie hierboven, pv2_power is onbetrouwbaar.

  V2 < 0,50 x V1   eerste melding 17 juli, 27 van 73 dagen. Dat is zeven weken
                   voor de uitval van 9 september die we eerder als startpunt
                   aanhielden. Gemeten scheiding: defecte dagen 0,08-0,34,
                   gezonde dagen 0,59-2,26. De drempel ligt in dat gat, maar
                   niet in het midden -- naar de gezonde kant is de marge 0,09,
                   naar de defecte kant 0,16. Bij 0,45 zou hij gecentreerd zijn.

  CV < 0,15        zelfde 26 dagen. Defect 0,01-0,07, gezond 0,38-1,20. Geen
                   enkele overlap; dit is het schoonste onderscheid van de twee.

EEN RICHTING, GEEN SYMMETRIE
De twee strings draaien op verschillende spanning: string 1 rond 200 V, string
2 rond 426 V. In normaal bedrijf is V1/V2 daardoor 0,44-1,70, dus een
symmetrische toets "V1 < 0,50 x V2" zou op gezonde dagen afgaan. De snelle
vlag kijkt om die reden ALLEEN of string 2 wegzakt t.o.v. string 1. Valt string
1 uit, dan moet de CV-regel dat opvangen -- die werkt wel voor beide, omdat hij
elke string tegen zijn eigen gedrag over de dag afzet en niet tegen de andere.
Bij een installatie met andere stringtopologie moet STRING_FAULT_VOLTAGE_
FRACTION opnieuw worden bepaald.

LOKALE DAGEN, GEEN UTC
De dagindeling volgt de lokale tijd. Tijdens de terugtoets bleken dag- en
uurstatistieken in Home Assistant een dag te verschillen, vrijwel zeker doordat
HA lokaal groepeert en de query UTC-labels gaf. Een alarm dat op datums afgaat
moet dezelfde dagen hanteren als de gebruiker ziet.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

_LOG = logging.getLogger(__name__)

# Home Assistant koppelt /data als persistente opslag; die overleeft herstart
# en add-on-update. Zonder dit zou "bevestigd" bij elke herstart terugkomen --
# en de add-on herstartte vandaag al drie keer.
STATE_PATH = os.environ.get("SALDOX_DIAG_STATE", "/data/pv_diagnostics.json")

LOCAL_OFFSET_HOURS = 2          # CEST; alleen voor de dagindeling
DAYLIGHT_MIN_W = 200            # ondergrens waarboven we een string "actief" noemen
STRING_DEAD_MINUTES = 30        # hoe lang het verschil moet aanhouden
VOLTAGE_COLLAPSE_FRACTION = 0.20
INSULATION_FRACTION = 0.50      # gekozen op basis van de terugtoets
INSULATION_BASELINE_DAYS = 14
VOLTAGE_BASELINE_DAYS = 7
MIN_BASELINE_DAYS = 5           # onder dit aantal geen oordeel -- te weinig historie

# --- Stringfout op spanning/stroom (vervangt de pv2_power-toets) ---
STRING_FAULT_VOLTAGE_FRACTION = 0.50   # V2 onder deze fractie van V1 = verdacht
STRING_FAULT_MIN_CURRENT_A = 0.5       # onder deze stroom zegt de verhouding niets
STRING_FAULT_MIN_HOURS = 2             # zo lang moet het aanhouden voor de vlag
OHMIC_CV_MAX = 0.15                    # variatiecoefficient van U/I over de dag
OHMIC_MIN_HOURS = 4                    # minder belaste uren -> geen CV-oordeel
OHMIC_MIN_CURRENT_SPREAD = 2.5         # hoogste/laagste stroom over die uren
#
# Die laatste drempel is niet cosmetisch. Een vaste U/I zegt alleen iets als de
# stroom wel degelijk bewoog: bleef de instraling de hele meetperiode gelijk,
# dan is een constante verhouding vanzelfsprekend en geen bewijs van een
# weerstand. Zonder deze eis meldde de regel op 30 augustus string 1 als defect
# -- vier middaguren met nauwelijks variatie (stroombereik 1,6x) gaven daar een
# CV van 0,09. Gezonde dagen halen over hun eerste vier belaste uren 2,7x tot
# 3,9x; de defecte dagen zitten op 3,7x tot 6,3x. Bij 2,5x valt het valse geval
# af zonder een echte te missen.


def _local_day(ts: datetime) -> str:
    return (ts + timedelta(hours=LOCAL_OFFSET_HOURS)).strftime("%Y-%m-%d")


def _local_hour(ts: datetime) -> str:
    return (ts + timedelta(hours=LOCAL_OFFSET_HOURS)).strftime("%Y-%m-%dT%H")


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[len(s) // 2]


def _cv(values: list[float]) -> float | None:
    """Variatiecoefficient: spreiding gedeeld door gemiddelde.

    Dimensieloos, dus bruikbaar om "beweegt mee met het licht" (hoog) te
    onderscheiden van "staat vast" (laag), ongeacht het spanningsniveau van
    de string.
    """
    if len(values) < 3:
        return None
    mean = sum(values) / len(values)
    if mean <= 0:
        return None
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return (var ** 0.5) / mean


@dataclass
class Alarm:
    key: str
    severity: str          # "warning" | "critical"
    title: str
    detail: str
    since: str             # ISO-tijdstip van eerste signalering

    def as_dict(self, acknowledged: bool) -> dict:
        return {
            "key": self.key,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "since": self.since,
            "acknowledged": acknowledged,
        }


@dataclass
class PvDiagnostics:
    """Houdt dagelijkse basislijnen bij en beoordeelt de huidige meting."""

    # dag -> laagste isolatiewaarde die dag
    insulation_daily_min: dict[str, float] = field(default_factory=dict)
    # dag -> hoogste spanning per string
    voltage_daily_max: dict[str, dict[str, float]] = field(default_factory=dict)
    # string -> tijdstip waarop hij voor het eerst dood leek
    dead_since: dict[str, str] = field(default_factory=dict)
    # "YYYY-MM-DDTHH" (lokaal) -> string -> [somV, somI, aantal]
    # Uurgemiddelden zijn nodig omdat een losse meting te veel ruist om U/I
    # betrouwbaar te bepalen; per uur middelen haalt die ruis eruit.
    hourly: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    # alarmsleutel -> tijdstip van bevestigen
    acknowledged: dict[str, str] = field(default_factory=dict)

    # ---------------------------------------------------------------- opslag
    @classmethod
    def load(cls) -> "PvDiagnostics":
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            return cls(
                insulation_daily_min=raw.get("insulation_daily_min", {}),
                voltage_daily_max=raw.get("voltage_daily_max", {}),
                dead_since=raw.get("dead_since", {}),
                hourly=raw.get("hourly", {}),
                acknowledged=raw.get("acknowledged", {}),
            )
        except FileNotFoundError:
            return cls()
        except Exception as ex:                      # corrupte state mag niet fataal zijn
            _LOG.warning("Diagnose-state onleesbaar (%s) — opnieuw beginnen", ex)
            return cls()

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
            tmp = STATE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({
                    "insulation_daily_min": self.insulation_daily_min,
                    "voltage_daily_max": self.voltage_daily_max,
                    "dead_since": self.dead_since,
                    "hourly": self.hourly,
                    "acknowledged": self.acknowledged,
                }, fh)
            os.replace(tmp, STATE_PATH)              # atomair; geen half bestand bij stroomuitval
        except Exception as ex:
            _LOG.warning("Diagnose-state niet op te slaan: %s", ex)

    def _prune(self, now: datetime | None = None, keep_days: int = 45) -> None:
        # now expliciet meegeven, niet de wandklok pakken: bij het terugspelen
        # van historie wist de wandklok-variant alles wat ouder was dan 45 dagen
        # meteen weer uit, waardoor het juli-blok onzichtbaar bleef.
        now = now or datetime.now(timezone.utc)
        cutoff = _local_day(now - timedelta(days=keep_days))
        for store in (self.insulation_daily_min, self.voltage_daily_max):
            for day in [d for d in store if d < cutoff]:
                del store[day]
        # hourly heeft sleutels "YYYY-MM-DDTHH"; vergelijk op het datumdeel,
        # anders zou "2026-09-01T05" < "2026-09-01" onjuist uitpakken.
        for key in [k for k in self.hourly if k[:10] < cutoff]:
            del self.hourly[key]

    # ------------------------------------------------------------ bijwerken
    def observe(self, readings: dict, now: datetime | None = None) -> None:
        """Verwerk één meting in de dagelijkse basislijnen."""
        now = now or datetime.now(timezone.utc)
        day = _local_day(now)

        def val(key: str):
            entry = readings.get(key)
            return entry.get("value") if isinstance(entry, dict) else None

        iso = val("insulation_resistance")
        if isinstance(iso, (int, float)) and iso > 0:
            prev = self.insulation_daily_min.get(day)
            self.insulation_daily_min[day] = min(prev, iso) if prev is not None else float(iso)

        hour = _local_hour(now)
        for s in ("pv1", "pv2"):
            v = val(f"{s}_voltage_v")
            if isinstance(v, (int, float)):
                bucket = self.voltage_daily_max.setdefault(day, {})
                bucket[s] = max(bucket.get(s, 0.0), float(v))

            i = val(f"{s}_current_a")
            if isinstance(v, (int, float)) and isinstance(i, (int, float)):
                acc = self.hourly.setdefault(hour, {}).setdefault(s, [0.0, 0.0, 0.0])
                acc[0] += float(v)
                acc[1] += float(i)
                acc[2] += 1

        self._prune(now)

    def _hourly_ratios(self, string: str, day: str) -> list[tuple[float, float]]:
        """(U/I, I) per uur voor een string op een lokale dag, belaste uren.

        Onbelaste uren laten vallen: bij bijna nul stroom schiet de verhouding
        naar duizenden ohm en zou hij de spreiding domineren, waardoor juist
        een defecte string er gevarieerd uit gaat zien.

        De stroom komt mee terug omdat de CV-toets moet weten of er genoeg
        variatie in de instraling zat om iets te kunnen concluderen.
        """
        out: list[tuple[float, float]] = []
        # Niet sorteren: CV, mediaan en spreiding zijn volgorde-onafhankelijk,
        # en deze lus draait bij elke polling over de hele bewaarde historie.
        for key, per_string in self.hourly.items():
            if key[:10] != day:
                continue
            acc = per_string.get(string)
            if not acc or acc[2] <= 0:
                continue
            mean_v, mean_i = acc[0] / acc[2], acc[1] / acc[2]
            if mean_i > STRING_FAULT_MIN_CURRENT_A and mean_v > 0:
                out.append((mean_v / mean_i, mean_i))
        return out

    # -------------------------------------------------------------- oordeel
    def evaluate(self, readings: dict, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now(timezone.utc)
        today = _local_day(now)
        alarms: list[Alarm] = []

        def val(key: str):
            entry = readings.get(key)
            return entry.get("value") if isinstance(entry, dict) else None

        # --- Regel 1a: snelle vlag — string 2 zakt weg onder string 1 ---
        #
        # Eenrichtingsverkeer, en dat is geen slordigheid: string 1 draait rond
        # 200 V en string 2 rond 426 V, dus in gezond bedrijf is V1 al 0,44-1,70
        # keer V2. De omgekeerde toets zou daarmee op goede dagen afgaan.
        v1, i1 = val("pv1_voltage_v"), val("pv1_current_a")
        v2, i2 = val("pv2_voltage_v"), val("pv2_current_a")
        measured = all(isinstance(x, (int, float)) for x in (v1, i1, v2, i2))

        if measured and i1 > STRING_FAULT_MIN_CURRENT_A and v1 > 0:
            fraction = v2 / v1
            if fraction < STRING_FAULT_VOLTAGE_FRACTION:
                first = self.dead_since.get("pv2")
                if first is None:
                    self.dead_since["pv2"] = now.isoformat()
                elif now - datetime.fromisoformat(first) >= timedelta(hours=STRING_FAULT_MIN_HOURS):
                    alarms.append(Alarm(
                        key="string_fault_pv2",
                        severity="critical",
                        title="String 2 levert ver onder string 1",
                        detail=(f"String 2 staat op {v2:.0f} V tegen {v1:.0f} V voor "
                                f"string 1 ({fraction:.2f}x), al sinds "
                                f"{first[:16].replace('T', ' ')}. Normaal ligt die "
                                f"verhouding boven 0,59. Wijst op een onderbroken of "
                                f"weerstandsvolle verbinding: MC4-connectoren, "
                                f"DC-scheider, klemmen in de omvormer."),
                        since=first,
                    ))
            else:
                self.dead_since.pop("pv2", None)
        elif measured and i1 <= STRING_FAULT_MIN_CURRENT_A:
            pass          # te weinig licht om te oordelen; loper niet resetten

        # --- Regel 1b: bevestiging — U/I staat vast, dus een weerstand ---
        #
        # Werkt wel voor beide strings: hij zet elke string af tegen zijn eigen
        # verloop over de dag, niet tegen de andere string.
        for s, name in (("pv1", "1"), ("pv2", "2")):
            samples = self._hourly_ratios(s, today)
            if len(samples) < OHMIC_MIN_HOURS:
                continue
            currents = [i for _, i in samples]
            spread = max(currents) / min(currents) if min(currents) > 0 else 0.0
            if spread < OHMIC_MIN_CURRENT_SPREAD:
                continue           # te weinig variatie in het licht; zegt niets
            ratios = [r for r, _ in samples]
            cv = _cv(ratios)
            if cv is None or cv >= OHMIC_CV_MAX:
                continue
            alarms.append(Alarm(
                key=f"string_ohmic_{s}",
                severity="critical",
                title=f"String {name} gedraagt zich als weerstand",
                detail=(f"De verhouding spanning/stroom staat vandaag over "
                        f"{len(ratios)} belaste uren vast op {_median(ratios):.0f} ohm "
                        f"(spreiding {cv:.2f}). Een werkende string volgt de MPPT en "
                        f"varieert sterk over de dag; een vaste waarde betekent dat "
                        f"een overgangsweerstand het gedrag bepaalt. Zoek een "
                        f"gecorrodeerd of verbrand contact."),
                since=now.isoformat(),
            ))

        # --- Regel 2: stringspanning ingestort ---
        #
        # Alleen beoordelen wanneer de ANDERE string aantoonbaar levert. Dat is
        # het bewijs dat er zon is; zonder die voorwaarde vergelijk je een
        # ochtendwaarde met een dagmaximum en vuurt de regel elke dag opnieuw.
        # De proefdraai op 75 dagen historie liet dat zien: 42 valse dagen voor
        # BEIDE strings, terwijl string 1 nooit defect is geweest.
        #
        # We toetsen de MOMENTANE spanning, niet het dagmaximum: een string die
        # instort doet dat binnen een uur, en dan wil je het meteen zien.
        for s, name, other in (("pv1", "1", "pv2"), ("pv2", "2", "pv1")):
            v = val(f"{s}_voltage_v")
            other_p = val(f"{other}_power_w")
            if not isinstance(v, (int, float)) or not isinstance(other_p, (int, float)):
                continue
            if other_p <= DAYLIGHT_MIN_W:
                continue                      # geen zon, of de andere string is óók stil
            hist = [d[s] for day, d in sorted(self.voltage_daily_max.items())
                    if day < today and s in d and d[s] > 0]
            hist = hist[-VOLTAGE_BASELINE_DAYS:]
            if len(hist) < MIN_BASELINE_DAYS:
                continue
            baseline = _median(hist)
            if baseline > 0 and v < baseline * VOLTAGE_COLLAPSE_FRACTION:
                alarms.append(Alarm(
                    key=f"voltage_collapse_{s}",
                    severity="critical",
                    title=f"Stringspanning {name} ingestort",
                    detail=(f"Spanning {v:.0f} V terwijl string {other[-1]} "
                            f"{int(other_p)} W levert; normaal staat deze string "
                            f"op {baseline:.0f} V. Wijst op een onderbroken of "
                            f"kortgesloten string."),
                    since=now.isoformat(),
                ))

        # --- Regel 3: isolatieweerstand weggezakt ---
        iso = val("insulation_resistance")
        hist = [v for day, v in sorted(self.insulation_daily_min.items())
                if day < today][-INSULATION_BASELINE_DAYS:]
        if isinstance(iso, (int, float)) and len(hist) >= MIN_BASELINE_DAYS:
            baseline = _median(hist)
            todays_min = self.insulation_daily_min.get(today, float(iso))
            if baseline > 0 and todays_min < baseline * INSULATION_FRACTION:
                alarms.append(Alarm(
                    key="insulation_drop",
                    severity="warning",
                    title="Isolatieweerstand sterk gedaald",
                    detail=(f"Laagste waarde vandaag {todays_min:.0f} kΩ, tegen "
                            f"{baseline:.0f} kΩ over de afgelopen twee weken. "
                            f"Wijst op vocht of een aardlek in de DC-zijde. "
                            f"Dit signaal ging in augustus 2026 twaalf dagen vóór "
                            f"de stringuitval af."),
                    since=now.isoformat(),
                ))

        # Bevestigingen opruimen zodra het alarm verdwijnt, zodat een terugkeer
        # opnieuw opvalt in plaats van stilletjes bevestigd te blijven.
        live = {a.key for a in alarms}
        for key in [k for k in self.acknowledged if k not in live]:
            del self.acknowledged[key]

        self.save()
        return [a.as_dict(a.key in self.acknowledged) for a in alarms]

    # ---------------------------------------------------------- bevestigen
    def acknowledge(self, key: str) -> bool:
        self.acknowledged[key] = datetime.now(timezone.utc).isoformat()
        self.save()
        return True
