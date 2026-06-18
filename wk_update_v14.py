#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WK Speelschema 2026  (v14)
==========================
v14: poulestanden worden nu rechtstreeks uit de wedstrijduitslagen berekend
(standen_uit_wedstrijden) i.p.v. uit het standings-endpoint. Afgelopen ÉN lopende
duels tellen live mee, zodat de poule en het knock-outschema meebewegen met de
wedstrijden. Het standings-endpoint blijft als terugval als de wedstrijden niet
opgehaald kunnen worden.
v13: titel 'WK Speelschema 2026' (zonder 'De').
v12: titel 'De WK Speelschema 2026' + tagline 'voor de echte voetballiefhebber'.
Mobiele weergave wedstrijdregels gefixt: status op eigen regel, teamnamen krijgen
de volle breedte en mogen afbreken; kleinere paddings op smalle schermen.
v11: drukke kopregel (Stand van... + legenda) vervangen door een korte intro;
per tabblad een eigen uitleg, met disclaimer bij de knock-out; footer 'Powered
by Marny'. De legenda (door/beste 3/=) staat nu in het tabblad Groepen.
v10: landnamen in het Nederlands (vertaaltabel LAND_NL), toegepast op zowel de
groepsstanden als de wedstrijden/knock-out; onbekende namen vallen terug op de
API-naam.
v9: (1) titel nu 'WK 2026 — De tussenstand'. (2) pagina ververst elke 15 min
(was 2 min). (3) wedstrijden-overzicht toont de laatste 4 gespeelde + de 4
eerstvolgende wedstrijden, met lopende duels ertussen (was: alle van vandaag).
(4) drie tabbladen: Wedstrijden / Groepen / Knockout.
v8: volledig bracket doorgetrokken t/m de finale (achtste/kwart/halve/finale) met
match-nummers M89-M104 en feeder-labels ('Winnaar M74'); teams vullen zich vanzelf.
v7: bovenaan een 'Vandaag'-blok met de wedstrijden van vandaag + live-stand voor
wedstrijden die bezig zijn (LIVE/rust). v6: 'Stand van'-tijd in NL-tijd, ook bij
cloud/UTC-run. v5: layout-opschoning groepskaart. v4: Laatste 32 ingevuld op basis
van de huidige stand (officiele FIFA-kandidatenlijsten).
v3: voegt wedstrijdtijden toe. Per groep een inklapbaar programma met kick-off-
tijden + uitslagen, en een volledig knock-outschema (Laatste 32 t/m finale) met
tijden. Alle tijden in NL-tijd (CEST = UTC+2, geldt heel het toernooi).
v2-fix: rang wordt bepaald op tabelvolgorde i.p.v. het 'position'-veld, omdat
de API bij gelijke stand soms gedeelde posities geeft (bv. 1,2,2,4). Teams die
gelijk staan krijgen een '='-markering.

Haalt de actuele groepsstanden + wedstrijden van het WK 2026 op bij
football-data.org, berekent wie er met de huidige stand doorgaat naar de
knock-outfase (laatste 32) en genereert een zelf-verversend dashboard.

Doorgangsregels WK 2026 (48 landen, 12 groepen van 4):
  - de nummers 1 en 2 van elke groep gaan door  -> 24 landen
  - de 8 beste nummers 3 (over alle groepen)     ->  8 landen
  - totaal 32 landen naar de laatste 32

Rangschikking nummers 3 (FIFA-criteria):
  1) punten  2) doelsaldo  3) doelpunten voor

Gebruik:
  1) Maak gratis account op https://www.football-data.org/client/register
  2) Zet je API-token in wk_config.txt of in omgevingsvariabele FOOTBALL_DATA_TOKEN.
  3) Draai dit script:  python wk_update_v9.py
  4) Open wk_dashboard.html in je browser. De pagina ververst zichzelf.
"""

import os
import sys
import json
import html
import datetime
import urllib.request
import urllib.error

API_BASE = "https://api.football-data.org/v4"
COMPETITION = "WC"          # FIFA World Cup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "wk_dashboard.html")
DATA_JSON = os.path.join(SCRIPT_DIR, "wk_data.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "wk_config.txt")
REFRESH_SECONDS = 900       # browserpagina herlaadt zichzelf (15 min)

NUM_BEST_THIRDS = 8         # aantal beste nummers 3 dat doorgaat
VENSTER_AANTAL = 4          # aantal gespeelde + aantal komende wedstrijden in beeld

# NL-tijd: het WK 2026 (11 juni - 19 juli) valt volledig in de zomertijd,
# dus NL = UTC + 2 uur gedurende het hele toernooi.
NL_UTC_OFFSET = 2
NL_DAGEN = ["ma", "di", "wo", "do", "vr", "za", "zo"]
NL_MAANDEN = ["jan", "feb", "mrt", "apr", "mei", "jun",
              "jul", "aug", "sep", "okt", "nov", "dec"]

# Engelse landnaam (zoals football-data.org die teruggeeft) -> Nederlandse naam.
# De 48 WK 2026-deelnemers staan er sowieso in; daarnaast een ruime set andere
# FIFA-landen voor als de stand nog schuift. Onbekende namen vallen via nl_land()
# terug op de API-naam, dus de lijst hoeft niet uitputtend te zijn.
LAND_NL = {
    "Algeria": "Algerije", "Angola": "Angola", "Argentina": "Argentinië",
    "Australia": "Australië", "Austria": "Oostenrijk", "Belgium": "België",
    "Bolivia": "Bolivia", "Bosnia-Herzegovina": "Bosnië-Herzegovina",
    "Brazil": "Brazilië", "Bulgaria": "Bulgarije", "Burkina Faso": "Burkina Faso",
    "Cameroon": "Kameroen", "Canada": "Canada", "Cape Verde Islands": "Kaapverdië",
    "Chile": "Chili", "China PR": "China", "Colombia": "Colombia",
    "Congo DR": "DR Congo", "Costa Rica": "Costa Rica", "Croatia": "Kroatië",
    "Curaçao": "Curaçao", "Czechia": "Tsjechië", "Czech Republic": "Tsjechië",
    "Denmark": "Denemarken", "Ecuador": "Ecuador", "Egypt": "Egypte",
    "England": "Engeland", "Finland": "Finland", "France": "Frankrijk",
    "Germany": "Duitsland", "Ghana": "Ghana", "Greece": "Griekenland",
    "Guinea": "Guinee", "Haiti": "Haïti", "Honduras": "Honduras",
    "Hungary": "Hongarije", "Iceland": "IJsland", "Iran": "Iran", "Iraq": "Irak",
    "Ireland": "Ierland", "Israel": "Israël", "Italy": "Italië",
    "Ivory Coast": "Ivoorkust", "Jamaica": "Jamaica", "Japan": "Japan",
    "Jordan": "Jordanië", "Korea Republic": "Zuid-Korea",
    "Korea DPR": "Noord-Korea", "Mali": "Mali", "Mexico": "Mexico",
    "Morocco": "Marokko", "Netherlands": "Nederland", "New Zealand": "Nieuw-Zeeland",
    "Nigeria": "Nigeria", "North Korea": "Noord-Korea", "North Macedonia": "Noord-Macedonië",
    "Norway": "Noorwegen", "Panama": "Panama", "Paraguay": "Paraguay",
    "Peru": "Peru", "Poland": "Polen", "Portugal": "Portugal", "Qatar": "Qatar",
    "Romania": "Roemenië", "Russia": "Rusland", "Saudi Arabia": "Saoedi-Arabië",
    "Scotland": "Schotland", "Senegal": "Senegal", "Serbia": "Servië",
    "Slovakia": "Slowakije", "Slovenia": "Slovenië", "South Africa": "Zuid-Afrika",
    "South Korea": "Zuid-Korea", "Spain": "Spanje", "Sweden": "Zweden",
    "Switzerland": "Zwitserland", "Tunisia": "Tunesië", "Turkey": "Turkije",
    "Türkiye": "Turkije", "Ukraine": "Oekraïne",
    "United Arab Emirates": "Verenigde Arabische Emiraten",
    "United States": "Verenigde Staten", "USA": "Verenigde Staten",
    "Uruguay": "Uruguay", "Uzbekistan": "Oezbekistan", "Venezuela": "Venezuela",
    "Wales": "Wales", "Zambia": "Zambia",
}


def nl_land(naam):
    """Engelse landnaam -> Nederlands; valt terug op de originele naam."""
    if not naam:
        return naam
    return LAND_NL.get(naam, naam)


def _vertaal_teamdict(t):
    """Geeft een kopie van een API-team-dict met de naam in het Nederlands."""
    t = dict(t or {})
    if t.get("name"):
        t["name"] = nl_land(t["name"])
    return t

# Knock-outrondes in volgorde, met NL-titel
KO_RONDES = [
    ("LAST_32", "Laatste 32"),
    ("LAST_16", "Achtste finale"),
    ("QUARTER_FINALS", "Kwartfinale"),
    ("SEMI_FINALS", "Halve finale"),
    ("THIRD_PLACE", "Troostfinale"),
    ("FINAL", "Finale"),
]

# Officieel Laatste-32-schema WK 2026 (match 73-88). Per wedstrijd: het
# wedstrijdnummer, de UTC-aftrap (= sleutel om aan de API-tijd te koppelen) en
# de twee deelnemers als 'slot':
#   ("winner", "A")  -> winnaar groep A      (1A)
#   ("runner", "B")  -> nummer 2 groep B     (2B)
#   ("third", [...]) -> beste nummer 3 uit een van deze groepen (kandidatenlijst)
# Bron: officieel FIFA-schema / Wikipedia 2026 FIFA World Cup knockout stage.
R32_SCHEMA = [
    {"nr": 73, "utc": "2026-06-28T19:00:00Z", "thuis": ("runner", "A"), "uit": ("runner", "B")},
    {"nr": 74, "utc": "2026-06-29T20:30:00Z", "thuis": ("winner", "E"), "uit": ("third", ["A", "B", "C", "D", "F"])},
    {"nr": 75, "utc": "2026-06-30T01:00:00Z", "thuis": ("winner", "F"), "uit": ("runner", "C")},
    {"nr": 76, "utc": "2026-06-29T17:00:00Z", "thuis": ("winner", "C"), "uit": ("runner", "F")},
    {"nr": 77, "utc": "2026-06-30T21:00:00Z", "thuis": ("winner", "I"), "uit": ("third", ["C", "D", "F", "G", "H"])},
    {"nr": 78, "utc": "2026-06-30T17:00:00Z", "thuis": ("runner", "E"), "uit": ("runner", "I")},
    {"nr": 79, "utc": "2026-07-01T01:00:00Z", "thuis": ("winner", "A"), "uit": ("third", ["C", "E", "F", "H", "I"])},
    {"nr": 80, "utc": "2026-07-01T16:00:00Z", "thuis": ("winner", "L"), "uit": ("third", ["E", "H", "I", "J", "K"])},
    {"nr": 81, "utc": "2026-07-02T00:00:00Z", "thuis": ("winner", "D"), "uit": ("third", ["B", "E", "F", "I", "J"])},
    {"nr": 82, "utc": "2026-07-01T20:00:00Z", "thuis": ("winner", "G"), "uit": ("third", ["A", "E", "H", "I", "J"])},
    {"nr": 83, "utc": "2026-07-02T23:00:00Z", "thuis": ("runner", "K"), "uit": ("runner", "L")},
    {"nr": 84, "utc": "2026-07-02T19:00:00Z", "thuis": ("winner", "H"), "uit": ("runner", "J")},
    {"nr": 85, "utc": "2026-07-03T03:00:00Z", "thuis": ("winner", "B"), "uit": ("third", ["E", "F", "G", "I", "J"])},
    {"nr": 86, "utc": "2026-07-03T22:00:00Z", "thuis": ("winner", "J"), "uit": ("runner", "H")},
    {"nr": 87, "utc": "2026-07-04T01:30:00Z", "thuis": ("winner", "K"), "uit": ("third", ["D", "E", "I", "J", "L"])},
    {"nr": 88, "utc": "2026-07-03T18:00:00Z", "thuis": ("runner", "D"), "uit": ("runner", "G")},
]

# De acht wedstrijden waar een nummer 3 instroomt, met hun kandidatenlijst.
THIRD_SLOTS = [
    (74, ["A", "B", "C", "D", "F"]),
    (77, ["C", "D", "F", "G", "H"]),
    (79, ["C", "E", "F", "H", "I"]),
    (80, ["E", "H", "I", "J", "K"]),
    (81, ["B", "E", "F", "I", "J"]),
    (82, ["A", "E", "H", "I", "J"]),
    (85, ["E", "F", "G", "I", "J"]),
    (87, ["D", "E", "I", "J", "L"]),
]

# Officieel bracket vanaf de achtste finale (match 89-104). Per wedstrijd het
# nummer, de stage, de UTC-aftrap (sleutel naar de API-tijd) en de twee
# 'feeders': de wedstrijd waarvan de winnaar (W) of, bij de troostfinale, de
# verliezer (L) instroomt. UTC-tijden geverifieerd tegen de football-data-API.
# Bron: officieel FIFA-schema / Wikipedia 2026 FIFA World Cup knockout stage.
KO_BRACKET = [
    # Achtste finale
    {"nr": 89, "stage": "LAST_16", "utc": "2026-07-04T21:00:00Z", "thuis": ("W", 74), "uit": ("W", 77)},
    {"nr": 90, "stage": "LAST_16", "utc": "2026-07-04T17:00:00Z", "thuis": ("W", 73), "uit": ("W", 75)},
    {"nr": 91, "stage": "LAST_16", "utc": "2026-07-05T20:00:00Z", "thuis": ("W", 76), "uit": ("W", 78)},
    {"nr": 92, "stage": "LAST_16", "utc": "2026-07-06T00:00:00Z", "thuis": ("W", 79), "uit": ("W", 80)},
    {"nr": 93, "stage": "LAST_16", "utc": "2026-07-06T19:00:00Z", "thuis": ("W", 83), "uit": ("W", 84)},
    {"nr": 94, "stage": "LAST_16", "utc": "2026-07-07T00:00:00Z", "thuis": ("W", 81), "uit": ("W", 82)},
    {"nr": 95, "stage": "LAST_16", "utc": "2026-07-07T16:00:00Z", "thuis": ("W", 86), "uit": ("W", 88)},
    {"nr": 96, "stage": "LAST_16", "utc": "2026-07-07T20:00:00Z", "thuis": ("W", 85), "uit": ("W", 87)},
    # Kwartfinale
    {"nr": 97, "stage": "QUARTER_FINALS", "utc": "2026-07-09T20:00:00Z", "thuis": ("W", 89), "uit": ("W", 90)},
    {"nr": 98, "stage": "QUARTER_FINALS", "utc": "2026-07-10T19:00:00Z", "thuis": ("W", 93), "uit": ("W", 94)},
    {"nr": 99, "stage": "QUARTER_FINALS", "utc": "2026-07-11T21:00:00Z", "thuis": ("W", 91), "uit": ("W", 92)},
    {"nr": 100, "stage": "QUARTER_FINALS", "utc": "2026-07-12T01:00:00Z", "thuis": ("W", 95), "uit": ("W", 96)},
    # Halve finale
    {"nr": 101, "stage": "SEMI_FINALS", "utc": "2026-07-14T19:00:00Z", "thuis": ("W", 97), "uit": ("W", 98)},
    {"nr": 102, "stage": "SEMI_FINALS", "utc": "2026-07-15T19:00:00Z", "thuis": ("W", 99), "uit": ("W", 100)},
    # Troostfinale + finale
    {"nr": 103, "stage": "THIRD_PLACE", "utc": "2026-07-18T21:00:00Z", "thuis": ("L", 101), "uit": ("L", 102)},
    {"nr": 104, "stage": "FINAL", "utc": "2026-07-19T19:00:00Z", "thuis": ("W", 101), "uit": ("W", 102)},
]


# ---------------------------------------------------------------------------
# API-token ophalen
# ---------------------------------------------------------------------------
def lees_token():
    token = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
    if token:
        return token
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for regel in f:
                regel = regel.strip()
                if regel and not regel.startswith("#"):
                    return regel
    return ""


# ---------------------------------------------------------------------------
# Data ophalen
# ---------------------------------------------------------------------------
def _haal(token, pad):
    url = "%s/%s" % (API_BASE, pad)
    req = urllib.request.Request(url, headers={"X-Auth-Token": token})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def haal_standen(token):
    return _haal(token, "competitions/%s/standings" % COMPETITION)


def haal_wedstrijden(token):
    return _haal(token, "competitions/%s/matches" % COMPETITION)


# ---------------------------------------------------------------------------
# Tijd-helper: UTC -> NL-tijd, bv. "za 28 jun 21:00"
# ---------------------------------------------------------------------------
def nl_tijd(utc_str):
    if not utc_str:
        return "n.t.b."
    try:
        dt = datetime.datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return "n.t.b."
    dt += datetime.timedelta(hours=NL_UTC_OFFSET)
    return "%s %d %s %02d:%02d" % (
        NL_DAGEN[dt.weekday()], dt.day, NL_MAANDEN[dt.month - 1],
        dt.hour, dt.minute,
    )


def nl_datum(utc_str):
    """UTC-string -> NL-datum als 'YYYY-MM-DD' (of None)."""
    if not utc_str:
        return None
    try:
        dt = datetime.datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    dt += datetime.timedelta(hours=NL_UTC_OFFSET)
    return dt.strftime("%Y-%m-%d")


def nl_vandaag():
    """Huidige NL-datum als 'YYYY-MM-DD' (werkt ook bij UTC-cloudrun)."""
    nu = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=NL_UTC_OFFSET)
    return nu.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Standen omzetten naar groepen
# ---------------------------------------------------------------------------
def parse_groepen(data):
    """Geeft een dict {groepsletter: [rij, ...]} terug, gesorteerd op stand."""
    groepen = {}
    for blok in data.get("standings", []):
        if blok.get("type") != "TOTAL":
            continue
        groep_naam = blok.get("group") or ""
        if not groep_naam:
            continue
        letter = groep_naam.replace("GROUP_", "").replace("Group ", "").strip()
        # De API levert de tabel al op volgorde. We gebruiken de TABELVOLGORDE
        # (index) als rang, niet het 'position'-veld: bij een gelijke stand geeft
        # de API soms gedeelde posities (bv. 1,2,2,4), wat het tellen verstoort.
        rijen = []
        for idx, r in enumerate(blok.get("table", [])):
            team = r.get("team", {})
            rijen.append({
                "positie": idx + 1,
                "api_positie": r.get("position"),
                "naam": nl_land(team.get("name", "?")),
                "tla": team.get("tla") or "",
                "crest": team.get("crest") or "",
                "gespeeld": r.get("playedGames", 0),
                "w": r.get("won", 0),
                "g": r.get("draw", 0),
                "v": r.get("lost", 0),
                "dv": r.get("goalsFor", 0),
                "dt": r.get("goalsAgainst", 0),
                "saldo": r.get("goalDifference", 0),
                "punten": r.get("points", 0),
                "gelijk": False,
            })
        # 'gelijk' markeren: zelfde punten/saldo/doelpunten als de buur erboven.
        for i in range(1, len(rijen)):
            a, b = rijen[i - 1], rijen[i]
            if (a["punten"], a["saldo"], a["dv"]) == (b["punten"], b["saldo"], b["dv"]):
                a["gelijk"] = True
                b["gelijk"] = True
        groepen[letter] = rijen
    return dict(sorted(groepen.items()))


def standen_uit_wedstrijden(groep_wedstrijden):
    """Berekent de groepsstanden rechtstreeks uit de wedstrijduitslagen, zodat de
    poule (en daarmee de knock-out) live meebeweegt met de wedstrijden: afgelopen
    EN lopende duels tellen mee (football-data zet de actuele tussenstand tijdens
    het spelen ook in score.fullTime). Geeft dezelfde structuur als parse_groepen:
    {letter: [rij, ...]}, gesorteerd op stand (punten, saldo, doelpunten voor).
    Geeft {} terug als er geen wedstrijden zijn (dan gebruikt main het standings-
    endpoint als terugval)."""
    meetel = ("FINISHED",) + LIVE_STATUS

    def _zorg(teams, team):
        tid = team.get("id") or team.get("name")
        if tid not in teams:
            teams[tid] = {
                "positie": 0, "api_positie": None,
                "naam": team.get("name", "?"),
                "tla": team.get("tla") or "", "crest": team.get("crest") or "",
                "gespeeld": 0, "w": 0, "g": 0, "v": 0,
                "dv": 0, "dt": 0, "saldo": 0, "punten": 0, "gelijk": False,
            }
        return teams[tid]

    groepen = {}
    for letter, wedstrijden in (groep_wedstrijden or {}).items():
        if not letter:
            continue
        teams = {}
        for m in wedstrijden:
            th = _zorg(teams, m.get("thuis") or {})
            ut = _zorg(teams, m.get("uit") or {})
            sc = m.get("score") or {}
            h, a = sc.get("home"), sc.get("away")
            if m.get("status") in meetel and h is not None and a is not None:
                th["gespeeld"] += 1
                ut["gespeeld"] += 1
                th["dv"] += h
                th["dt"] += a
                ut["dv"] += a
                ut["dt"] += h
                if h > a:
                    th["w"] += 1
                    ut["v"] += 1
                    th["punten"] += 3
                elif h < a:
                    ut["w"] += 1
                    th["v"] += 1
                    ut["punten"] += 3
                else:
                    th["g"] += 1
                    ut["g"] += 1
                    th["punten"] += 1
                    ut["punten"] += 1
        for t in teams.values():
            t["saldo"] = t["dv"] - t["dt"]
        rijen = sorted(teams.values(),
                       key=lambda x: (x["punten"], x["saldo"], x["dv"]),
                       reverse=True)
        for i, r in enumerate(rijen):
            r["positie"] = i + 1
        for i in range(1, len(rijen)):
            a, b = rijen[i - 1], rijen[i]
            if (a["punten"], a["saldo"], a["dv"]) == (b["punten"], b["saldo"], b["dv"]):
                a["gelijk"] = True
                b["gelijk"] = True
        groepen[letter] = rijen
    return dict(sorted(groepen.items()))


# ---------------------------------------------------------------------------
# Wedstrijden omzetten naar groepsprogramma + knock-outschema
# ---------------------------------------------------------------------------
def parse_wedstrijden(data):
    groep_w = {}    # letter -> [wedstrijd, ...]
    knockout = {}   # stage  -> [wedstrijd, ...]
    alle = []       # platte lijst van alle wedstrijden (voor het venster)
    ko_titels = dict(KO_RONDES)
    for m in data.get("matches", []):
        stage = m.get("stage")
        score = m.get("score") or {}
        info = {
            "utc": m.get("utcDate"),
            "tijd": nl_tijd(m.get("utcDate")),
            "nl_datum": nl_datum(m.get("utcDate")),
            "status": m.get("status"),
            "thuis": _vertaal_teamdict(m.get("homeTeam")),
            "uit": _vertaal_teamdict(m.get("awayTeam")),
            "score": score.get("fullTime") or {},
            "context": "",
        }
        if stage in ("GROUP_STAGE", "LEAGUE_STAGE"):
            groep_naam = m.get("group") or ""
            letter = groep_naam.replace("GROUP_", "").replace("Group ", "").strip()
            info["context"] = "Groep " + letter if letter else ""
            groep_w.setdefault(letter, []).append(info)
        elif stage:
            info["context"] = ko_titels.get(stage, "Knock-out")
            knockout.setdefault(stage, []).append(info)
        alle.append(info)
    for v in groep_w.values():
        v.sort(key=lambda x: x["utc"] or "")
    for v in knockout.values():
        v.sort(key=lambda x: x["utc"] or "")
    alle.sort(key=lambda x: x["utc"] or "")
    return groep_w, knockout, alle


# ---------------------------------------------------------------------------
# Doorgang berekenen
# ---------------------------------------------------------------------------
def bereken_doorgang(groepen):
    """Voegt 'status' toe per rij: 'door' (nr 1/2), 'beste3' (beste nr 3), 'uit'."""
    derde_plaatsen = []
    for letter, rijen in groepen.items():
        for r in rijen:
            r["status"] = "uit"
            if r["positie"] in (1, 2):
                r["status"] = "door"
        for r in rijen:
            if r["positie"] == 3:
                derde = dict(r)
                derde["groep"] = letter
                derde_plaatsen.append(derde)

    derde_plaatsen.sort(key=lambda x: (x["punten"], x["saldo"], x["dv"]), reverse=True)
    for i, d in enumerate(derde_plaatsen):
        d["beste3_positie"] = i + 1
        d["door"] = i < NUM_BEST_THIRDS

    door_namen = {d["naam"] for d in derde_plaatsen[:NUM_BEST_THIRDS]}
    for letter, rijen in groepen.items():
        for r in rijen:
            if r["positie"] == 3 and r["naam"] in door_namen:
                r["status"] = "beste3"

    return derde_plaatsen


# ---------------------------------------------------------------------------
# Laatste 32 projecteren op basis van de huidige standen
# ---------------------------------------------------------------------------
def wijs_derden_toe(qualifying):
    """Wijst de 8 doorgaande nummers 3 toe aan de 8 'derde'-wedstrijden via de
    officiele kandidatenlijsten (bipartiete matching). Geeft (toewijzing, n) terug:
      toewijzing = {wedstrijdnummer: groepsletter}
      n          = aantal geldige indelingen gevonden (gecapt op 2; 2 => meerdere)
    """
    qual = set(qualifying)
    cand = []
    for nr, groups in THIRD_SLOTS:
        cand.append([nr, [g for g in groups if g in qual]])
    # Meest beperkte wedstrijd eerst -> efficiente, stabiele backtracking.
    cand.sort(key=lambda x: len(x[1]))

    oplossingen = []

    def bt(i, used, assign):
        if len(oplossingen) >= 2:
            return
        if i == len(cand):
            oplossingen.append(dict(assign))
            return
        nr, groups = cand[i]
        for g in sorted(groups):
            if g not in used:
                used.add(g)
                assign[nr] = g
                bt(i + 1, used, assign)
                del assign[nr]
                used.discard(g)

    bt(0, set(), {})
    if not oplossingen:
        return {}, 0
    return oplossingen[0], len(oplossingen)


def _team_van_groep(groepen, letter, positie):
    for r in groepen.get(letter, []):
        if r["positie"] == positie:
            return {"name": r["naam"], "crest": r["crest"], "tla": r["tla"]}
    return {}


def _slot_team(spec, nr, assign, groepen):
    """Geeft (label, team-dict) voor een bracket-slot."""
    typ = spec[0]
    if typ == "winner":
        g = spec[1]
        return "1" + g, _team_van_groep(groepen, g, 1)
    if typ == "runner":
        g = spec[1]
        return "2" + g, _team_van_groep(groepen, g, 2)
    if typ == "third":
        g = assign.get(nr)
        if not g:
            return "3?", {}
        return "3" + g, _team_van_groep(groepen, g, 3)
    return "?", {}


def projecteer_last32(groepen, derde_plaatsen, api_last32):
    """Bouwt de 16 Laatste-32-duels (match-nummer-volgorde). Gebruikt de echte
    API-teams zodra die bekend zijn, anders de projectie uit de huidige stand."""
    if not groepen:
        return [], False
    qualifying = [d["groep"] for d in derde_plaatsen[:NUM_BEST_THIRDS]]
    assign, n_opl = wijs_derden_toe(qualifying)
    ambigu = n_opl >= 2

    api_by_utc = {m.get("utc"): m for m in (api_last32 or [])}

    duels = []
    for s in R32_SCHEMA:
        api = api_by_utc.get(s["utc"], {})
        tijd = api.get("tijd") or nl_tijd(s["utc"])
        api_thuis = api.get("thuis") or {}
        api_uit = api.get("uit") or {}
        thuis_label, proj_thuis = _slot_team(s["thuis"], s["nr"], assign, groepen)
        uit_label, proj_uit = _slot_team(s["uit"], s["nr"], assign, groepen)
        if api_thuis.get("name") and api_uit.get("name"):
            # Definitief: de echte loting/uitslag is bekend.
            thuis_team, uit_team = api_thuis, api_uit
            bron, score = "definitief", score_str(api)
        else:
            thuis_team, uit_team = proj_thuis, proj_uit
            bron, score = "projectie", ""
        duels.append({
            "nr": s["nr"], "tijd": tijd, "bron": bron, "score": score,
            "thuis_label": thuis_label, "thuis_team": thuis_team,
            "uit_label": uit_label, "uit_team": uit_team,
        })
    return duels, ambigu


def _feeder_label(spec):
    """('W', 74) -> 'Winnaar M74'  /  ('L', 101) -> 'Verliezer M101'."""
    typ, nr = spec
    woord = "Winnaar" if typ == "W" else "Verliezer"
    return "%s M%d" % (woord, nr)


# KO_BRACKET op match-nummer, voor het terugrekenen van mogelijke landen.
_BRACKET_BY_NR = {s["nr"]: s for s in KO_BRACKET}


def _mogelijke_landen(nr, r32_by_nr):
    """Loopt de bracket terug naar de Laatste-32-deelnemers en geeft de lijst
    landen die wedstrijd `nr` (en dus de winnaar ervan) zou kunnen opleveren.
    M74 -> de 2 deelnemers van M74; M89 -> de 4 uit M74+M77; enz."""
    if nr in r32_by_nr:
        d = r32_by_nr[nr]
        return [t["name"] for t in (d["thuis_team"], d["uit_team"]) if t.get("name")]
    s = _BRACKET_BY_NR.get(nr)
    if not s:
        return []
    namen = []
    for spec in (s["thuis"], s["uit"]):
        for nm in _mogelijke_landen(spec[1], r32_by_nr):
            if nm not in namen:
                namen.append(nm)
    return namen


def projecteer_knockout(knockout, last32_proj):
    """Bouwt per ronde (achtste t/m finale) de duels uit KO_BRACKET, met
    match-nummer + feeder-labels ('Winnaar M74') en de mogelijke landen per
    feeder (teruggerekend naar de Laatste 32). Zodra de API echte teams invult,
    worden die getoond. Geeft dict stage -> [duel, ...] terug."""
    api_by_utc = {}
    for lst in (knockout or {}).values():
        for m in lst:
            if m.get("utc"):
                api_by_utc[m["utc"]] = m
    r32_by_nr = {d["nr"]: d for d in (last32_proj or [])}

    per_stage = {}
    for s in KO_BRACKET:
        api = api_by_utc.get(s["utc"], {})
        tijd = api.get("tijd") or nl_tijd(s["utc"])
        api_thuis = api.get("thuis") or {}
        api_uit = api.get("uit") or {}
        if api_thuis.get("name") and api_uit.get("name"):
            thuis_team, uit_team = api_thuis, api_uit
            bron, score = "definitief", score_str(api)
        else:
            thuis_team, uit_team = {}, {}
            bron, score = "ntb", ""
        per_stage.setdefault(s["stage"], []).append({
            "nr": s["nr"], "tijd": tijd, "bron": bron, "score": score,
            "thuis_label": _feeder_label(s["thuis"]), "thuis_team": thuis_team,
            "uit_label": _feeder_label(s["uit"]), "uit_team": uit_team,
            "thuis_mogelijk": _mogelijke_landen(s["thuis"][1], r32_by_nr),
            "uit_mogelijk": _mogelijke_landen(s["uit"][1], r32_by_nr),
        })
    return per_stage


# ---------------------------------------------------------------------------
# HTML genereren
# ---------------------------------------------------------------------------
def status_badge(status):
    if status == "door":
        return '<span class="badge badge-door">DOOR</span>'
    if status == "beste3":
        return '<span class="badge badge-beste3">BESTE 3</span>'
    return ""


def crest_img(crest, tla):
    if crest:
        return '<img class="crest" src="%s" alt="" loading="lazy">' % html.escape(crest)
    if tla:
        return '<span class="crest crest-leeg">%s</span>' % html.escape(tla)
    return ""


def team_label(t):
    naam = t.get("name")
    if not naam:
        return '<span class="ntb">n.t.b.</span>'
    return '%s<span class="naam">%s</span>' % (
        crest_img(t.get("crest") or "", t.get("tla") or ""), html.escape(naam))


def score_str(info):
    s = info.get("score") or {}
    h, a = s.get("home"), s.get("away")
    # Toon de stand bij afgelopen EN lopende wedstrijden (football-data zet de
    # actuele tussenstand tijdens het spelen ook in score.fullTime).
    if (info.get("status") in ("FINISHED",) + LIVE_STATUS
            and h is not None and a is not None):
        return "%d&ndash;%d" % (h, a)
    return ""


def wedstrijd_regel(info):
    sc = score_str(info)
    mid = sc if sc else '<span class="vs">&ndash;</span>'
    return (
        '<div class="wedstrijd">'
        '<span class="w-tijd">%s</span>'
        '<span class="w-thuis">%s</span>'
        '<span class="w-score">%s</span>'
        '<span class="w-uit">%s</span>'
        '</div>' % (
            html.escape(info["tijd"]),
            team_label(info["thuis"]), mid, team_label(info["uit"]),
        )
    )


def programma_block(wedstrijden):
    if not wedstrijden:
        return ""
    regels = "".join(wedstrijd_regel(w) for w in wedstrijden)
    return ('<details class="programma"><summary>Wedstrijden &amp; tijden (NL)'
            '</summary>%s</details>' % regels)


def groep_kaart(letter, rijen, wedstrijden):
    rows = []
    for r in rijen:
        klasse = "rij-%s" % r["status"]
        gelijk_mark = ('<span class="gelijk" title="Staat gelijk met buur '
                       '— volgorde bij deze stand nog niet beslist">=</span>'
                       if r.get("gelijk") else "")
        rows.append(
            '<tr class="%s">'
            '<td class="pos">%s%s</td>'
            '<td class="team">%s<span class="naam">%s</span></td>'
            '<td>%s</td><td>%s</td><td>%s</td>'
            '<td class="saldo">%+d</td>'
            '<td class="pnt">%s</td>'
            '</tr>' % (
                klasse,
                r["positie"] if r["positie"] else "-",
                gelijk_mark,
                crest_img(r["crest"], r["tla"]),
                html.escape(r["naam"]),
                r["w"], r["g"], r["v"],
                r["saldo"], r["punten"],
            )
        )
    return (
        '<div class="kaart">'
        '<h3>Groep %s</h3>'
        '<table class="groep">'
        '<colgroup><col class="c-pos"><col class="c-team"><col class="c-st">'
        '<col class="c-st"><col class="c-st"><col class="c-sal"><col class="c-pnt">'
        '</colgroup>'
        '<thead><tr><th></th><th>Team</th><th>W</th><th>G</th>'
        '<th>V</th><th>+/-</th><th>Ptn</th></tr></thead>'
        '<tbody>%s</tbody>'
        '</table>'
        '%s'
        '</div>' % (html.escape(letter), "".join(rows), programma_block(wedstrijden))
    )


def beste3_panel(derde_plaatsen):
    if not derde_plaatsen:
        return ""
    rows = []
    for d in derde_plaatsen:
        klasse = "rij-beste3" if d["door"] else "rij-uit"
        grens = ' class="grens"' if d["beste3_positie"] == NUM_BEST_THIRDS else ""
        rows.append(
            '<tr class="%s"%s>'
            '<td class="pos">%s</td>'
            '<td class="team">%s<span class="naam">%s</span>'
            '<span class="groeplabel">groep %s</span></td>'
            '<td>%s</td><td class="saldo">%+d</td><td>%s</td>'
            '<td class="pnt">%s</td>'
            '<td>%s</td>'
            '</tr>' % (
                klasse, grens,
                d["beste3_positie"],
                crest_img(d["crest"], d["tla"]),
                html.escape(d["naam"]),
                html.escape(d["groep"]),
                d["gespeeld"], d["saldo"], d["dv"], d["punten"],
                '<span class="badge badge-door">DOOR</span>' if d["door"]
                else '<span class="badge badge-uit">af</span>',
            )
        )
    return (
        '<div class="kaart kaart-breed">'
        '<h3>Klassement nummers 3 &mdash; de beste %d gaan door</h3>'
        '<p class="toelichting">Gerangschikt op punten, doelsaldo en doelpunten voor. '
        'De stippellijn is de grens: daarboven = door naar de laatste 32.</p>'
        '<table>'
        '<thead><tr><th>#</th><th>Team</th><th>G</th><th>Saldo</th>'
        '<th>DV</th><th>Ptn</th><th>Status</th></tr></thead>'
        '<tbody>%s</tbody>'
        '</table>'
        '</div>' % (NUM_BEST_THIRDS, "".join(rows))
    )


def ko_match_block(info):
    sc = score_str(info)
    mid = sc if sc else '<span class="vs">vs</span>'
    return (
        '<div class="ko-match">'
        '<div class="ko-tijd">%s</div>'
        '<div class="ko-teams"><span>%s</span><span class="ko-mid">%s</span>'
        '<span>%s</span></div>'
        '</div>' % (
            html.escape(info["tijd"]),
            team_label(info["thuis"]), mid, team_label(info["uit"]),
        )
    )


def proj_match_block(m):
    """Render een geprojecteerd Laatste-32-duel met slot-labels en match-nr."""
    if m["bron"] == "definitief":
        badge = '<span class="ko-badge def">definitief</span>'
        mid = m["score"] if m["score"] else '<span class="vs">vs</span>'
    else:
        badge = '<span class="ko-badge">projectie</span>'
        mid = '<span class="vs">vs</span>'
    return (
        '<div class="ko-match">'
        '<div class="ko-tijd">M%d &middot; %s %s</div>'
        '<div class="ko-teams">'
        '<span><span class="slot">%s</span>%s</span>'
        '<span class="ko-mid">%s</span>'
        '<span>%s<span class="slot">%s</span></span>'
        '</div></div>' % (
            m["nr"], html.escape(m["tijd"]), badge,
            html.escape(m["thuis_label"]), team_label(m["thuis_team"]),
            mid,
            team_label(m["uit_team"]), html.escape(m["uit_label"]),
        )
    )


def _mogelijk_html(namen, rechts=False):
    """Compacte lijst mogelijke landen onder een feeder-label (max 8 + rest)."""
    if not namen:
        return ""
    MAX = 8
    toon = namen[:MAX]
    tekst = " / ".join(html.escape(n) for n in toon)
    if len(namen) > MAX:
        tekst += " +%d" % (len(namen) - MAX)
    return '<span class="mogelijk">%s</span>' % tekst


def _feeder_zijde(label, namen, rechts=False):
    return ('<span class="feeder">'
            '<span class="slot">%s</span>%s</span>'
            % (html.escape(label), _mogelijk_html(namen, rechts)))


def bracket_match_block(m):
    """Render een bracket-duel (achtste t/m finale): match-nr + feeder-labels
    ('Winnaar M74') met de mogelijke landen eronder, of de echte teams +
    uitslag zodra die bekend zijn."""
    if m["bron"] == "definitief":
        badge = '<span class="ko-badge def">definitief</span>'
        mid = m["score"] if m["score"] else '<span class="vs">vs</span>'
        thuis = team_label(m["thuis_team"])
        uit = team_label(m["uit_team"])
    else:
        badge = '<span class="ko-badge">n.t.b.</span>'
        mid = '<span class="vs">vs</span>'
        thuis = _feeder_zijde(m["thuis_label"], m.get("thuis_mogelijk"))
        uit = _feeder_zijde(m["uit_label"], m.get("uit_mogelijk"), rechts=True)
    return (
        '<div class="ko-match">'
        '<div class="ko-tijd">M%d &middot; %s %s</div>'
        '<div class="ko-teams"><span>%s</span>'
        '<span class="ko-mid">%s</span><span>%s</span></div>'
        '</div>' % (m["nr"], html.escape(m["tijd"]), badge, thuis, mid, uit)
    )


def knockout_sectie(knockout, last32_proj, ambigu):
    if not knockout and not last32_proj:
        return ""
    later = projecteer_knockout(knockout, last32_proj)
    kolommen = []
    for stage, titel in KO_RONDES:
        if stage == "LAST_32" and last32_proj:
            blokken = "".join(proj_match_block(m) for m in last32_proj)
        elif stage in later:
            blokken = "".join(bracket_match_block(m) for m in later[stage])
        else:
            ms = knockout.get(stage, [])
            if not ms:
                continue
            blokken = "".join(ko_match_block(m) for m in ms)
        kolommen.append('<div class="ko-kolom"><h4>%s</h4>%s</div>'
                        % (html.escape(titel), blokken))
    if not kolommen:
        return ""
    extra = (' Bij deze stand zijn meerdere geldige indelingen van de nummers 3 '
             'mogelijk; hier is er &eacute;&eacute;n getoond.' if ambigu else '')
    return (
        '<div class="kaart kaart-breed">'
        '<h3>Knock-outschema &mdash; Laatste 32 op basis van de huidige stand</h3>'
        '<p class="toelichting">De Laatste 32 is ingevuld met de huidige (nog '
        'voorlopige) standen: nrs 1 &amp; 2 op vaste posities, de 8 beste nummers 3 '
        'volgens de offici&euml;le FIFA-kandidatenlijsten. Vanaf de achtste finale '
        'staat het volledige bracket met match-nummers en de doorstroming '
        '(&ldquo;Winnaar M74&rdquo; enz.); de teams vullen zich vanzelf in zodra de '
        'uitslagen bekend zijn. Alle tijden in NL-tijd.%s</p>'
        '<div class="ko-bracket">%s</div>'
        '</div>' % (extra, "".join(kolommen))
    )


LIVE_STATUS = ("IN_PLAY", "LIVE", "PAUSED", "SUSPENDED")
KOMEND_STATUS = ("SCHEDULED", "TIMED")


def _venster_status(info):
    """Geeft (css-klasse, label, toon_score) voor een wedstrijd in het venster."""
    s = info.get("status")
    if s in ("IN_PLAY", "LIVE"):
        return "live", "LIVE", True
    if s == "PAUSED":
        return "live", "rust", True
    if s == "SUSPENDED":
        return "live", "onderbroken", True
    if s == "FINISHED":
        return "klaar", "afgelopen", True
    if s in ("POSTPONED", "CANCELLED"):
        return "muted", ("uitgesteld" if s == "POSTPONED" else "afgelast"), False
    # nog te spelen: toon de aftraptijd (klok) als label
    tijd = info.get("tijd") or ""
    klok = tijd.split(" ")[-1] if tijd else ""
    return "tijd", klok, False


def venster_match_regel(info):
    klasse, label, toon_score = _venster_status(info)
    if toon_score:
        sc = score_str(info)
        midden = sc if sc else '<span class="vs">&ndash;</span>'
    else:
        midden = '<span class="vs">vs</span>'
    meta = html.escape(info.get("tijd") or "")
    context = info.get("context") or ""
    if context:
        meta += " &middot; " + html.escape(context)
    return (
        '<div class="vd-match vd-%s">'
        '<span class="vd-status vd-%s">%s</span>'
        '<span class="vd-thuis">%s</span>'
        '<span class="vd-score">%s</span>'
        '<span class="vd-uit">%s</span>'
        '<span class="vd-context">%s</span>'
        '</div>' % (
            klasse, klasse, html.escape(label),
            team_label(info["thuis"]), midden, team_label(info["uit"]),
            meta,
        )
    )


def wedstrijden_venster(alle, aantal=VENSTER_AANTAL):
    """De laatste `aantal` gespeelde + alle lopende + de eerstvolgende `aantal`
    wedstrijden, chronologisch. Zo staan de net-gespeelde en de eraan-komende
    duels samen in beeld, met de live-wedstrijden ertussen."""
    if not alle:
        return []
    gespeeld = [m for m in alle if m.get("status") == "FINISHED"]
    live = [m for m in alle if m.get("status") in LIVE_STATUS]
    komend = [m for m in alle if m.get("status") in KOMEND_STATUS]
    gespeeld.sort(key=lambda x: x["utc"] or "")
    komend.sort(key=lambda x: x["utc"] or "")
    venster = gespeeld[-aantal:] + live + komend[:aantal]
    venster.sort(key=lambda x: x["utc"] or "")
    return venster


def wedstrijden_sectie(alle_wedstrijden):
    if alle_wedstrijden is None:
        return ""
    venster = wedstrijden_venster(alle_wedstrijden)
    live_n = sum(1 for m in venster if m.get("status") in LIVE_STATUS)
    live_badge = (' &middot; <span class="live-tel">%d live</span>' % live_n
                  if live_n else "")
    if venster:
        inhoud = "".join(venster_match_regel(m) for m in venster)
    else:
        inhoud = ('<p class="vd-leeg">Nog geen wedstrijdgegevens beschikbaar. '
                  'Zodra het programma bekend is, verschijnen hier de laatste en '
                  'eerstvolgende wedstrijden.</p>')
    return (
        '<div class="kaart kaart-breed vandaag">'
        '<h3>Wedstrijden &mdash; net gespeeld &amp; eraan komend%s</h3>'
        '%s'
        '</div>' % (live_badge, inhoud)
    )


# Vaste uitleg per tabblad (de legenda staat in 'Groepen', de disclaimer in
# 'Knockout fase').
UITLEG_WEDSTRIJDEN = (
    '<div class="uitleg">'
    '<h3>Wat zie je hier?</h3>'
    '<p>De laatste vier gespeelde en de vier eerstvolgende WK-wedstrijden. '
    'Loopt er een wedstrijd? Dan staat die ertussen met de actuele tussenstand. '
    'Bij afgelopen duels zie je de einduitslag, bij komende duels de aftraptijd '
    '(in NL-tijd).</p>'
    '</div>'
)

UITLEG_GROEPEN = (
    '<div class="uitleg">'
    '<h3>Wat zie je hier?</h3>'
    '<p>De twaalf groepen met de actuele stand. De nummers 1 en 2 van elke groep '
    'gaan rechtstreeks door naar de laatste 32. Daarnaast plaatsen de acht beste '
    'nummers 3 (over alle groepen) zich ook &mdash; onderaan staat hun volledige '
    'klassement, gerangschikt op punten, doelsaldo en doelpunten voor. De stand '
    'wordt live berekend uit de uitslagen: ook een lopende wedstrijd telt al mee.</p>'
    '<div class="legenda">'
    '<span><span class="dot dot-door"></span> nr. 1 &amp; 2 &mdash; door</span>'
    '<span><span class="dot dot-beste3"></span> beste nummer 3 &mdash; door</span>'
    '<span><span class="gelijk">=</span> staat gelijk &mdash; volgorde nog niet '
    'beslist</span>'
    '</div>'
    '</div>'
)

UITLEG_KNOCKOUT = (
    '<div class="uitleg">'
    '<h3>Wat zie je hier?</h3>'
    '<p>Het volledige schema van de laatste 32 tot en met de finale. De teams '
    'schuiven vanzelf door zodra de uitslagen bekend zijn (&ldquo;Winnaar M74&rdquo; '
    'wordt dan het echte land).</p>'
    '<p class="disclaimer"><strong>Let op &mdash; dit is een projectie.</strong> '
    'Zolang de groepsfase nog loopt, is de indeling gebaseerd op de h&uacute;idige '
    'stand. Vooral de plek van de nummers 3 kan bij gelijke standen anders '
    'uitpakken. Pas als de groepsfase is afgelopen en de loting/uitslagen binnen '
    'zijn, staan de echte tegenstanders definitief vast.</p>'
    '</div>'
)


def bouw_html(groepen, derde_plaatsen, groep_wedstrijden, knockout, tijd,
              alle_wedstrijden=None, vandaag=None, foutmelding=""):
    if foutmelding:
        body = '<div class="kaart kaart-breed melding">%s</div>' % foutmelding
    elif not groepen:
        body = ('<div class="kaart kaart-breed melding">Nog geen groepsstanden '
                'beschikbaar. Zodra de eerste wedstrijden gespeeld zijn, verschijnt '
                'hier de stand.</div>')
    else:
        kaarten = "".join(
            groep_kaart(l, r, (groep_wedstrijden or {}).get(l, []))
            for l, r in groepen.items()
        )
        last32_proj, ambigu = projecteer_last32(
            groepen, derde_plaatsen, (knockout or {}).get("LAST_32", []))

        wedstrijden_html = wedstrijden_sectie(alle_wedstrijden)
        groepen_html = ('<div class="grid">%s</div>%s'
                        % (kaarten, beste3_panel(derde_plaatsen)))
        knockout_html = knockout_sectie(knockout, last32_proj, ambigu)

        body = (
            '<nav class="tabs">'
            '<button class="tab-btn active" data-tab="wedstrijden">Wedstrijden</button>'
            '<button class="tab-btn" data-tab="groepen">Groepen</button>'
            '<button class="tab-btn" data-tab="knockout">Knockout fase</button>'
            '</nav>'
            '<section id="tab-wedstrijden" class="tab-panel active">%s%s</section>'
            '<section id="tab-groepen" class="tab-panel">%s%s</section>'
            '<section id="tab-knockout" class="tab-panel">%s%s</section>'
            % (UITLEG_WEDSTRIJDEN, wedstrijden_html,
               UITLEG_GROEPEN, groepen_html,
               UITLEG_KNOCKOUT, knockout_html)
        )

    aantal_door = sum(1 for rijen in groepen.values() for r in rijen
                      if r["status"] in ("door", "beste3"))

    return """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{refresh}">
<title>WK Speelschema 2026</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --bp-bg: #F4F1EC; --bp-surface: #FFFFFF; --bp-ink: #1E1A14;
  --bp-muted: #7B6D5D; --bp-gold: #C9A84C; --bp-border: #E0D9CF;
  --door: #2E7D4F; --door-tint: #E6F2EA;
  --beste3: #C9A84C; --beste3-tint: #FBF4E0;
  --uit-tint: #F7F4EF;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bp-bg); color: var(--bp-ink);
  font-family: 'DM Sans', sans-serif; font-weight: 300;
  padding: 28px 20px 60px;
}}
header {{ max-width: 1240px; margin: 0 auto 24px; }}
h1 {{
  font-family: 'Playfair Display', serif; font-weight: 700;
  font-size: 2.1rem; margin: 0 0 6px;
}}
.tagline {{
  font-family: 'Playfair Display', serif; font-style: italic; font-weight: 400;
  color: var(--bp-gold); font-size: 1.05rem; margin: 0 0 12px;
}}
.intro {{ color: var(--bp-muted); font-size: .95rem; line-height: 1.5; margin: 0; max-width: 760px; }}

/* Uitleg-blok bovenaan elk tabblad */
.uitleg {{
  max-width: 1240px; margin: 0 auto 18px;
  background: var(--bp-surface); border: 1px solid var(--bp-border);
  border-radius: 14px; padding: 14px 18px;
}}
.uitleg h3 {{ margin: 0 0 6px; }}
.uitleg p {{ color: var(--bp-muted); font-size: .88rem; line-height: 1.5; margin: 0 0 8px; }}
.uitleg p:last-child {{ margin-bottom: 0; }}
.uitleg .legenda {{ margin-top: 12px; }}
.disclaimer {{
  background: var(--beste3-tint); border-left: 3px solid var(--bp-gold);
  border-radius: 6px; padding: 9px 12px; color: var(--bp-ink) !important;
}}
.disclaimer strong {{ color: var(--bp-ink); }}
.legenda {{ margin-top: 14px; display: flex; gap: 18px; flex-wrap: wrap; font-size: .85rem; }}
.legenda span {{ display: inline-flex; align-items: center; gap: 6px; }}
.dot {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}
.dot-door {{ background: var(--door); }}
.dot-beste3 {{ background: var(--beste3); }}

/* Tabbladen */
.tabs {{
  max-width: 1240px; margin: 0 auto 20px; display: flex; gap: 6px;
  border-bottom: 1px solid var(--bp-border); flex-wrap: wrap;
}}
.tab-btn {{
  font-family: 'DM Sans', sans-serif; font-size: .92rem; font-weight: 500;
  color: var(--bp-muted); background: none; border: none; cursor: pointer;
  padding: 10px 16px; border-bottom: 2px solid transparent; margin-bottom: -1px;
}}
.tab-btn:hover {{ color: var(--bp-ink); }}
.tab-btn.active {{ color: var(--bp-ink); border-bottom-color: var(--bp-gold); }}
.tab-panel {{ display: none; }}
.tab-panel.active {{ display: block; }}

.grid {{
  max-width: 1240px; margin: 0 auto;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 16px;
}}
.kaart {{
  background: var(--bp-surface); border: 1px solid var(--bp-border);
  border-radius: 14px; padding: 16px 18px;
  box-shadow: 0 1px 3px rgba(30,26,20,.04);
}}
.kaart-breed {{ max-width: 1240px; margin: 22px auto 0; }}
.tab-panel > .kaart-breed:first-child {{ margin-top: 0; }}
h3 {{
  font-family: 'Playfair Display', serif; font-weight: 700;
  font-size: 1.15rem; margin: 0 0 10px;
}}
table {{ width: 100%; border-collapse: collapse; font-size: .86rem; }}
th {{
  text-align: center; font-weight: 500; color: var(--bp-muted);
  border-bottom: 1px solid var(--bp-border); padding: 4px 2px; font-size: .72rem;
  text-transform: uppercase; letter-spacing: .03em;
}}
th:nth-child(2) {{ text-align: left; }}
td {{ text-align: center; padding: 6px 2px; border-bottom: 1px solid #F0EBE3; }}
tbody tr:last-child td {{ border-bottom: none; }}

/* Groepstabel: vaste kolombreedtes zodat niets afkapt */
table.groep {{ table-layout: fixed; }}
table.groep .c-pos {{ width: 30px; }}
table.groep .c-st  {{ width: 26px; }}
table.groep .c-sal {{ width: 40px; }}
table.groep .c-pnt {{ width: 34px; }}
table.groep td, table.groep th {{ font-variant-numeric: tabular-nums; }}

.pos {{ color: var(--bp-muted); font-weight: 500; white-space: nowrap; }}
.team {{
  text-align: left; display: flex; align-items: center; gap: 7px;
  min-width: 0; overflow: hidden;
}}
.naam {{ font-weight: 400; line-height: 1.15; min-width: 0; }}
.groeplabel {{ color: var(--bp-muted); font-size: .72rem; margin-left: 4px; }}
.crest {{ width: 20px; height: 15px; object-fit: contain; flex: none; }}
.crest-leeg {{
  width: 24px; font-size: .68rem; color: var(--bp-muted);
  border: 1px solid var(--bp-border); border-radius: 3px; padding: 1px 0;
}}
.saldo {{ font-variant-numeric: tabular-nums; }}
.pnt {{ font-weight: 600; }}
.rij-door {{ background: var(--door-tint); }}
.rij-door .pnt {{ color: var(--door); }}
.rij-beste3 {{ background: var(--beste3-tint); }}
.grens {{ border-bottom: 2px dashed var(--bp-muted) !important; }}
.badge {{
  font-size: .6rem; font-weight: 600; letter-spacing: .04em;
  padding: 2px 6px; border-radius: 20px; margin-left: 6px; white-space: nowrap;
}}
.badge-door {{ background: var(--door); color: #fff; }}
.badge-beste3 {{ background: var(--beste3); color: #3a2f10; }}
.badge-uit {{ background: #E5DED4; color: var(--bp-muted); }}
.gelijk {{ color: var(--bp-muted); font-weight: 600; font-size: .72rem; margin-left: 2px; }}
.toelichting {{ color: var(--bp-muted); font-size: .82rem; margin: -2px 0 12px; }}
.melding {{ color: var(--bp-muted); text-align: center; padding: 40px; }}

/* Groepsprogramma (inklapbaar) */
.programma {{ margin-top: 12px; border-top: 1px solid #F0EBE3; padding-top: 8px; }}
.programma summary {{
  cursor: pointer; font-size: .8rem; color: var(--bp-muted); font-weight: 500;
}}
.programma summary:hover {{ color: var(--bp-ink); }}
.wedstrijd {{
  display: grid; grid-template-columns: 92px 1fr auto 1fr; gap: 8px;
  align-items: center; font-size: .78rem; padding: 5px 0;
  border-bottom: 1px solid #F4EFE8;
}}
.wedstrijd:last-child {{ border-bottom: none; }}
.w-tijd {{ color: var(--bp-muted); font-size: .72rem; }}
.w-thuis {{ display: flex; align-items: center; gap: 5px; justify-content: flex-end; text-align: right; }}
.w-uit {{ display: flex; align-items: center; gap: 5px; }}
.w-score {{ font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.vs {{ color: var(--bp-muted); font-weight: 400; }}
.ntb {{ color: var(--bp-muted); font-style: italic; }}

/* Knock-outschema */
.ko-bracket {{ display: flex; gap: 16px; overflow-x: auto; padding-bottom: 8px; }}
.ko-kolom {{ min-width: 232px; flex: none; }}
.ko-kolom h4 {{
  font-family: 'Playfair Display', serif; font-weight: 700;
  font-size: 1rem; margin: 0 0 10px; color: var(--bp-ink);
}}
.ko-match {{
  background: var(--bp-bg); border: 1px solid var(--bp-border);
  border-radius: 10px; padding: 8px 10px; margin-bottom: 9px;
}}
.ko-tijd {{ color: var(--bp-muted); font-size: .7rem; margin-bottom: 4px; }}
.ko-teams {{
  display: grid; grid-template-columns: 1fr auto 1fr; gap: 8px;
  align-items: center; font-size: .8rem;
}}
.ko-teams > span:first-child {{ display: flex; align-items: center; gap: 5px; }}
.ko-teams > span:last-child {{ display: flex; align-items: center; gap: 5px; justify-content: flex-end; text-align: right; }}
.ko-mid {{ font-weight: 600; font-variant-numeric: tabular-nums; color: var(--bp-muted); }}
.slot {{
  display: inline-block; min-width: 20px; font-size: .62rem; font-weight: 600;
  color: #fff; background: var(--bp-muted); border-radius: 4px;
  padding: 1px 4px; margin: 0 4px;
}}
.feeder {{ display: flex; flex-direction: column; gap: 2px; }}
.ko-teams > span:last-child .feeder {{ align-items: flex-end; }}
.mogelijk {{
  font-size: .64rem; line-height: 1.25; color: var(--bp-muted);
  margin: 0 4px; font-style: italic;
}}
.ko-badge {{
  float: right; font-size: .58rem; font-weight: 600; letter-spacing: .03em;
  text-transform: uppercase; color: var(--bp-muted);
  background: #EDE7DD; border-radius: 10px; padding: 1px 6px;
}}
.ko-badge.def {{ background: var(--door-tint); color: var(--door); }}

/* Wedstrijden-venster (tab Wedstrijden) */
.vandaag {{ margin-top: 0; border-color: var(--bp-gold); }}
.vandaag h3 {{ display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }}
.live-tel {{
  color: #fff; background: #C0202A; border-radius: 20px;
  font-family: 'DM Sans', sans-serif; font-size: .72rem; font-weight: 600;
  padding: 2px 9px; letter-spacing: .02em;
}}
.vd-leeg {{ color: var(--bp-muted); font-size: .9rem; margin: 4px 0 0; }}
.vd-match {{
  display: grid; grid-template-columns: 76px 1fr auto 1fr 168px;
  grid-template-areas: "status thuis score uit meta";
  gap: 10px; align-items: center; padding: 9px 0;
  border-bottom: 1px solid #F0EBE3; font-size: .92rem;
}}
.vd-match:last-child {{ border-bottom: none; }}
.vd-match.vd-live {{ background: #FCEEEE; border-radius: 8px; padding: 9px 8px; }}
.vd-status {{
  grid-area: status;
  font-size: .64rem; font-weight: 700; letter-spacing: .04em;
  text-transform: uppercase; text-align: center; border-radius: 20px;
  padding: 3px 0;
}}
.vd-status.vd-tijd {{ color: var(--bp-ink); background: #EFEAE1; font-variant-numeric: tabular-nums; }}
.vd-status.vd-live {{ color: #fff; background: #C0202A; animation: knipper 1.6s ease-in-out infinite; }}
.vd-status.vd-klaar {{ color: var(--door); background: var(--door-tint); }}
.vd-status.vd-muted {{ color: var(--bp-muted); background: #EDE7DD; }}
@keyframes knipper {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .55; }} }}
.vd-thuis {{ grid-area: thuis; display: flex; align-items: center; gap: 7px; justify-content: flex-end; text-align: right; min-width: 0; }}
.vd-uit {{ grid-area: uit; display: flex; align-items: center; gap: 7px; min-width: 0; }}
.vd-thuis .naam, .vd-uit .naam {{ overflow-wrap: break-word; }}
.vd-score {{ grid-area: score; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; min-width: 34px; text-align: center; }}
.vd-context {{ grid-area: meta; color: var(--bp-muted); font-size: .72rem; text-align: right; line-height: 1.25; }}
@media (max-width: 560px) {{
  body {{ padding: 16px 12px 48px; }}
  h1 {{ font-size: 1.65rem; }}
  .kaart {{ padding: 14px 13px; }}
  /* Wedstrijdregel: status op een eigen regel, de twee teams eronder met de
     volle breedte zodat lange landnamen netjes afbreken i.p.v. uit de tabel
     te lopen. */
  .vd-match {{
    grid-template-columns: 1fr auto 1fr;
    grid-template-areas:
      "status status status"
      "thuis  score  uit";
    row-gap: 5px; column-gap: 8px; font-size: .85rem;
  }}
  .vd-status {{ justify-self: start; padding: 3px 10px; }}
  .vd-context {{ display: none; }}
  .vd-thuis, .vd-uit {{ line-height: 1.2; }}
  /* Groepstabel iets compacter op smalle schermen */
  table {{ font-size: .82rem; }}
  table.groep .c-st {{ width: 22px; }}
  table.groep .c-sal {{ width: 34px; }}
  table.groep .c-pnt {{ width: 30px; }}
}}

footer {{
  max-width: 1240px; margin: 30px auto 0; color: var(--bp-muted);
  font-size: .78rem; text-align: center;
}}
.maker {{
  margin-top: 10px; font-family: 'Playfair Display', serif; font-weight: 700;
  font-size: 1rem; color: var(--bp-gold); letter-spacing: .02em;
}}
</style>
</head>
<body>
<header>
  <h1>WK Speelschema 2026</h1>
  <p class="tagline">voor de echte voetballiefhebber</p>
  <p class="intro">Een live overzicht van het WK 2026: welke landen er bij deze stand doorgaan naar de laatste 32, de volledige groepsstanden en het knock-outschema t/m de finale. Kies hieronder een tabblad. De pagina ververst zichzelf elke {refresh_min} minuten; alle tijden in NL-tijd.</p>
</header>
{body}
<footer>Laatst bijgewerkt: {tijd} (NL-tijd) &middot; bron: football-data.org &middot; doorgangsregels WK 2026: nr. 1 &amp; 2 per groep + 8 beste nummers 3<div class="maker">Powered by Marny</div></footer>
<script>
document.querySelectorAll('.tab-btn').forEach(function (knop) {{
  knop.addEventListener('click', function () {{
    document.querySelectorAll('.tab-btn').forEach(function (x) {{ x.classList.remove('active'); }});
    document.querySelectorAll('.tab-panel').forEach(function (x) {{ x.classList.remove('active'); }});
    knop.classList.add('active');
    var doel = document.getElementById('tab-' + knop.dataset.tab);
    if (doel) {{ doel.classList.add('active'); }}
  }});
}});
</script>
</body>
</html>""".format(
        refresh=REFRESH_SECONDS,
        refresh_min=max(1, REFRESH_SECONDS // 60),
        tijd=html.escape(tijd),
        aantal_door=aantal_door,
        body=body,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _schrijf_fout(boodschap, nu):
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(bouw_html({}, [], {}, {}, nu, foutmelding=boodschap))


def main():
    # NL-tijd, ook als het script in de cloud (UTC) draait: UTC + 2 uur (CEST).
    nu = (datetime.datetime.now(datetime.timezone.utc)
          + datetime.timedelta(hours=NL_UTC_OFFSET)).strftime("%d-%m-%Y %H:%M")
    token = lees_token()

    if not token:
        boodschap = ("Geen API-token gevonden. Maak een gratis account op "
                     "football-data.org en zet je token in <code>wk_config.txt</code> "
                     "of in de omgevingsvariabele FOOTBALL_DATA_TOKEN.")
        _schrijf_fout(boodschap, nu)
        print("[!] Geen API-token. Dashboard met instructie geschreven naar")
        print("    " + OUTPUT_HTML)
        sys.exit(1)

    try:
        data = haal_standen(token)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("message", "")
        except Exception:
            pass
        boodschap = "Fout bij ophalen (HTTP %s): %s" % (e.code, html.escape(detail or str(e)))
        _schrijf_fout(boodschap, nu)
        print("[!] " + boodschap)
        sys.exit(1)
    except Exception as e:
        boodschap = "Fout bij ophalen: %s" % html.escape(str(e))
        _schrijf_fout(boodschap, nu)
        print("[!] " + boodschap)
        sys.exit(1)

    # Wedstrijden zijn een aanvulling: lukt dit niet, dan tonen we toch de stand.
    groep_wedstrijden, knockout, alle_wedstrijden = {}, {}, []
    try:
        wedstrijden = haal_wedstrijden(token)
        groep_wedstrijden, knockout, alle_wedstrijden = parse_wedstrijden(wedstrijden)
    except Exception as e:
        print("[!] Wedstrijden niet opgehaald (stand wordt wel getoond): %s" % e)

    vandaag = nl_vandaag()
    # Standen bij voorkeur live uit de wedstrijduitslagen (afgelopen + lopende
    # duels); valt terug op het standings-endpoint als er geen wedstrijden zijn.
    groepen = standen_uit_wedstrijden(groep_wedstrijden) or parse_groepen(data)
    derde_plaatsen = bereken_doorgang(groepen)

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump({"tijd": nu, "vandaag": vandaag, "groepen": groepen,
                   "nummers_3": derde_plaatsen,
                   "groep_wedstrijden": groep_wedstrijden, "knockout": knockout},
                  f, ensure_ascii=False, indent=2)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(bouw_html(groepen, derde_plaatsen, groep_wedstrijden, knockout, nu,
                          alle_wedstrijden=alle_wedstrijden, vandaag=vandaag))

    aantal = sum(1 for rijen in groepen.values() for r in rijen
                 if r["status"] in ("door", "beste3"))
    ko_aantal = sum(len(v) for v in knockout.values())
    n_venster = len(wedstrijden_venster(alle_wedstrijden))
    print("[OK] %s  |  %d groepen  |  %d landen door  |  %d knock-outduels  |  "
          "%d wedstrijden in venster  ->  %s"
          % (nu, len(groepen), aantal, ko_aantal, n_venster, OUTPUT_HTML))


if __name__ == "__main__":
    main()
