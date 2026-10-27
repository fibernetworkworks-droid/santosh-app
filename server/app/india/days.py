"""v0.59 India's calendar for the avatar: public holidays per state (vacanza/holidays, MIT) and the day's panchang.

Panchang is computed here from the Sun's and Moon's positions (Meeus' series, good to ~0.01-0.02 deg, so tithi end
times are right to a few minutes; Lahiri ayanamsa for nakshatra). Tithi, paksha and nakshatra are taken at local
sunrise as almanacs do. Lunar month = amanta (new moon to new moon), named by the Sun's rashi at the new moon; an adhik
(extra) month is not marked. Muhurat / rahu kaal are NOT given: those differ between traditions; say "panditji se puchhiye".
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

IST = timezone(timedelta(hours=5, minutes=30))
CITIES = {   # name -> (lat, lon, state code for holidays)
    "delhi": (28.61, 77.21, "DL"), "new delhi": (28.61, 77.21, "DL"), "mumbai": (19.08, 72.88, "MH"),
    "pune": (18.52, 73.86, "MH"), "nagpur": (21.15, 79.09, "MH"), "nashik": (20.0, 73.79, "MH"), "akola": (20.7, 77.0, "MH"),
    "akot": (21.1, 77.06, "MH"), "aurangabad": (19.88, 75.34, "MH"), "kolhapur": (16.7, 74.24, "MH"),
    "goa": (15.49, 73.83, "GA"), "panaji": (15.49, 73.83, "GA"), "bengaluru": (12.97, 77.59, "KA"),
    "bangalore": (12.97, 77.59, "KA"), "mysuru": (12.3, 76.64, "KA"), "chennai": (13.08, 80.27, "TN"),
    "madurai": (9.93, 78.12, "TN"), "coimbatore": (11.0, 76.96, "TN"), "hyderabad": (17.39, 78.49, "TS"),
    "vijayawada": (16.51, 80.65, "AP"), "visakhapatnam": (17.69, 83.22, "AP"), "kolkata": (22.57, 88.36, "WB"),
    "ahmedabad": (23.02, 72.57, "GJ"), "surat": (21.17, 72.83, "GJ"), "jaipur": (26.91, 75.79, "RJ"),
    "lucknow": (26.85, 80.95, "UP"), "varanasi": (25.32, 82.97, "UP"), "kanpur": (26.45, 80.33, "UP"),
    "patna": (25.59, 85.14, "BR"), "bhopal": (23.26, 77.41, "MP"), "indore": (22.72, 75.86, "MP"),
    "ujjain": (23.18, 75.78, "MP"), "raipur": (21.25, 81.63, "CG"), "bhubaneswar": (20.3, 85.82, "OD"),
    "guwahati": (26.14, 91.74, "AS"), "chandigarh": (30.73, 76.78, "CH"), "amritsar": (31.63, 74.87, "PB"),
    "ludhiana": (30.9, 75.85, "PB"), "dehradun": (30.32, 78.03, "UK"), "shimla": (31.1, 77.17, "HP"),
    "srinagar": (34.08, 74.8, "JK"), "jammu": (32.73, 74.86, "JK"), "kochi": (9.93, 76.27, "KL"),
    "thiruvananthapuram": (8.52, 76.94, "KL"), "ranchi": (23.34, 85.31, "JH"), "gurugram": (28.46, 77.03, "HR"),
    "noida": (28.54, 77.39, "UP"),
}
STATES = {"AN", "AP", "AR", "AS", "BR", "CG", "CH", "DH", "DL", "GA", "GJ", "HP", "HR", "JH", "JK", "KA", "KL", "LA",
          "LD", "MH", "ML", "MN", "MP", "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB"}
STATE_NAMES = {"maharashtra": "MH", "goa": "GA", "karnataka": "KA", "tamil nadu": "TN", "kerala": "KL", "gujarat": "GJ",
               "rajasthan": "RJ", "uttar pradesh": "UP", "bihar": "BR", "west bengal": "WB", "delhi": "DL", "punjab": "PB",
               "haryana": "HR", "telangana": "TS", "andhra pradesh": "AP", "madhya pradesh": "MP", "odisha": "OD",
               "assam": "AS", "jharkhand": "JH", "chhattisgarh": "CG", "uttarakhand": "UK", "himachal pradesh": "HP"}
TITHI = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", "Navami",
         "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi"]
NAKSHATRA = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
             "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
             "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
             "Uttara Bhadrapada", "Revati"]
RASHI = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]
# amanta month named by the Sun's sidereal rashi at the new moon that starts it
MONTH_BY_SUN = {"Meena": "Chaitra", "Mesha": "Vaishakha", "Vrishabha": "Jyeshtha", "Mithuna": "Ashadha", "Karka": "Shravana",
                "Simha": "Bhadrapada", "Kanya": "Ashwin", "Tula": "Kartik", "Vrishchika": "Margashirsha", "Dhanu": "Paush",
                "Makara": "Magh", "Kumbha": "Phalgun"}
VAAR = ["Somvar", "Mangalvar", "Budhvar", "Guruvar", "Shukravar", "Shanivar", "Ravivar"]
SPECIAL = {11: "Ekadashi", 26: "Ekadashi", 15: "Purnima", 30: "Amavasya", 19: "Sankashti Chaturthi", 4: "Vinayaka Chaturthi",
           13: "Pradosh", 28: "Pradosh", 29: "Masik Shivratri", 8: "Durga Ashtami (masik)"}


# ------------------------------------------------------------------ astronomy
def _jd(dt: datetime) -> float:
    dt = dt.astimezone(timezone.utc)
    return dt.timestamp() / 86400.0 + 2440587.5


def _T(dt: datetime) -> float:
    return (_jd(dt) + 69.0 / 86400 - 2451545.0) / 36525.0        # TT ~ UT + 69 s


def _n(x: float) -> float:
    return x % 360.0


def sun_lon(dt: datetime) -> float:
    T = _T(dt)
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = math.radians(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M) + (0.019993 - 0.000101 * T) * math.sin(2 * M)
         + 0.000289 * math.sin(3 * M))
    om = math.radians(125.04 - 1934.136 * T)
    return _n(L0 + C - 0.00569 - 0.00478 * math.sin(om))


_MOON = [  # (D, M, M', F, coeff 1e-6 deg) — Meeus table 47.A, largest terms
    (0, 0, 1, 0, 6288774), (2, 0, -1, 0, 1274027), (2, 0, 0, 0, 658314), (0, 0, 2, 0, 213618), (0, 1, 0, 0, -185116),
    (0, 0, 0, 2, -114332), (2, 0, -2, 0, 58793), (2, -1, -1, 0, 57066), (2, 0, 1, 0, 53322), (2, -1, 0, 0, 45758),
    (0, 1, -1, 0, -40923), (1, 0, 0, 0, -34720), (0, 1, 1, 0, -30383), (2, 0, 0, -2, 15327), (0, 0, 1, 2, -12528),
    (0, 0, 1, -2, 10980), (4, 0, -1, 0, 10675), (0, 0, 3, 0, 10034), (4, 0, -2, 0, 8548), (2, 1, -1, 0, -7888),
    (2, 1, 0, 0, -6766), (1, 0, -1, 0, -5163), (1, 1, 0, 0, 4987), (2, -1, 1, 0, 4036), (2, 0, 2, 0, 3994),
    (4, 0, 0, 0, 3861), (2, 0, -3, 0, 3665), (0, 1, -2, 0, -2689), (2, 0, -1, 2, -2602), (2, -1, -2, 0, 2390),
    (1, 0, 1, 0, -2348), (2, -2, 0, 0, 2236), (0, 1, 2, 0, -2120), (0, 2, 0, 0, -2069), (2, -2, -1, 0, 2048),
    (2, 0, 1, -2, -1773), (2, 0, 0, 2, -1595), (4, -1, -1, 0, 1215), (0, 0, 2, 2, -1110), (3, 0, -1, 0, -892),
    (2, 1, 1, 0, -810), (4, -1, -2, 0, 759), (0, 2, -1, 0, -713), (2, 2, -1, 0, -700), (2, 1, -2, 0, 691),
    (2, -1, 0, -2, 596), (4, 0, 1, 0, 549), (0, 0, 4, 0, 537), (4, -1, 0, 0, 520), (1, 0, -2, 0, -487),
]


def moon_lon(dt: datetime) -> float:
    T = _T(dt)
    Lp = 218.3164477 + 481267.88123421 * T - 0.0015786 * T * T
    D = math.radians(297.8501921 + 445267.1114034 * T - 0.0018819 * T * T)
    M = math.radians(357.5291092 + 35999.0502909 * T - 0.0001536 * T * T)
    Mp = math.radians(134.9633964 + 477198.8675055 * T + 0.0087414 * T * T)
    F = math.radians(93.2720950 + 483202.0175233 * T - 0.0036539 * T * T)
    E = 1 - 0.002516 * T - 0.0000074 * T * T
    s = 0.0
    for d, m, mp, f, c in _MOON:
        e = E ** abs(m)
        s += c * e * math.sin(d * D + m * M + mp * Mp + f * F)
    A1 = math.radians(119.75 + 131.849 * T)
    A2 = math.radians(53.09 + 479264.290 * T)
    s += 3958 * math.sin(A1) + 1962 * math.sin(math.radians(Lp) - F) + 318 * math.sin(A2)
    om = math.radians(125.04 - 1934.136 * T)
    return _n(Lp + s / 1e6 - 0.00478 * math.sin(om))


def ayanamsa(dt: datetime) -> float:
    """Lahiri (Chitrapaksha), linear fit: 23.853 deg at J2000, 50.29"/year."""
    return 23.853 + (_jd(dt) - 2451545.0) / 365.25 * 50.29 / 3600


def elongation(dt: datetime) -> float:
    return _n(moon_lon(dt) - sun_lon(dt))


def tithi_at(dt: datetime) -> int:
    """1..30 (1-15 Shukla, 16-30 Krishna; 15 = Purnima, 30 = Amavasya)."""
    return int(elongation(dt) // 12) + 1


def _cross(start: datetime, target: float, hours: float = 36) -> datetime | None:
    """First time after start when elongation passes target (deg), bisection on 30-min steps."""
    def diff(t):
        return (elongation(t) - target + 540) % 360 - 180
    a = start
    da = diff(a)
    step = timedelta(minutes=30)
    t = a
    while t - start < timedelta(hours=hours):
        b = t + step
        db = diff(b)
        if da < 0 <= db:
            lo, hi = t, b
            for _ in range(20):
                mid = lo + (hi - lo) / 2
                if diff(mid) < 0:
                    lo = mid
                else:
                    hi = mid
            return hi
        t, da = b, db
    return None


def sunrise(d: date, lat: float, lon: float) -> datetime:
    """NOAA solar position formulas; good to about a minute. Returns IST."""
    noon = datetime(d.year, d.month, d.day, 12, tzinfo=IST)
    for _ in range(2):
        g = 2 * math.pi / 365 * (noon.timetuple().tm_yday - 1 + (noon.astimezone(timezone.utc).hour - 12) / 24)
        eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                        - 0.040849 * math.sin(2 * g))
        decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
                + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
        la = math.radians(lat)
        cos_h = (math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(decl)) - math.tan(la) * math.tan(decl))
        ha = math.degrees(math.acos(max(-1.0, min(1.0, cos_h))))
        mins_utc = 720 - 4 * (lon + ha) - eqt
        rise = datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(minutes=mins_utc)
        noon = rise
    return rise.astimezone(IST)


def place(city: str = "") -> tuple[float, float, str, str]:
    c = (city or "").strip().lower()
    if c in CITIES:
        lat, lon, st = CITIES[c]
        return lat, lon, st, c.title()
    return 28.61, 77.21, "DL", "Delhi"


def panchang(d: date, city: str = "") -> dict[str, Any]:
    lat, lon, _, cname = place(city)
    rise = sunrise(d, lat, lon)
    t = tithi_at(rise)
    paksha = "Shukla" if t <= 15 else "Krishna"
    name = "Purnima" if t == 15 else "Amavasya" if t == 30 else TITHI[(t - 1) % 15]
    ends = _cross(rise, (t * 12) % 360)
    sid_moon = _n(moon_lon(rise) - ayanamsa(rise))
    nak = NAKSHATRA[int(sid_moon // (360 / 27))]
    # month: Sun's rashi at the new moon that started this lunar month
    back = rise - timedelta(hours=(elongation(rise) / 12.19) * 24)
    nm = _cross(back - timedelta(hours=30), 0.0, 60) or back
    sun_sid = _n(sun_lon(nm) - ayanamsa(nm))
    month = MONTH_BY_SUN[RASHI[int(sun_sid // 30)]]
    out = {"date": d.isoformat(), "vaar": VAAR[d.weekday()], "city": cname, "sunrise": rise.strftime("%H:%M"),
           "tithi": name, "tithi_no": t, "paksha": paksha, "tithi_ends": ends.strftime("%d %b %H:%M") if ends else None,
           "nakshatra": nak, "month_amanta": month, "moon_rashi": RASHI[int(sid_moon // 30)],
           "note": "Hisaab se nikala (±5 min). Amanta mahina; Uttar Bharat (purnimanta) mein Krishna paksha agle mahine ka "
                   "maana jaata hai. Muhurat ke liye panditji se puchhiye."}
    if t in SPECIAL:
        out["special"] = SPECIAL[t]
    return out


def next_tithi(kind: str, start: date | None = None, count: int = 3, city: str = "") -> list[dict[str, Any]]:
    """Next dates of ekadashi / purnima / amavasya / sankashti / pradosh / shivratri (by tithi at sunrise)."""
    want = {"ekadashi": {11, 26}, "purnima": {15}, "amavasya": {30}, "sankashti": {19}, "pradosh": {13, 28},
            "shivratri": {29}, "chaturthi": {4}, "ashtami": {8, 23}}.get((kind or "").lower().strip(), set())
    if not want:
        return []
    d = start or datetime.now(IST).date()
    lat, lon, _, _ = place(city)
    out = []
    nxt = tithi_at(sunrise(d, lat, lon))
    for i in range(0, 130):
        day = d + timedelta(days=i)
        t, nxt = nxt, tithi_at(sunrise(day + timedelta(days=1), lat, lon))
        # tithis that run during this day: the one at sunrise, plus a short (kshaya) one that starts and ends before
        # the next sunrise; a tithi standing at two sunrises counts on the first day only
        during = {t}
        k = t
        while k != nxt and len(during) < 3:
            k = k % 30 + 1
            if k != nxt:
                during.add(k)
        if during & want and (not out or out[-1]["date"] != (day - timedelta(days=1)).isoformat()):
            p = panchang(day, city)
            hit = t if t in want else min(during & want)
            name = "Purnima" if hit == 15 else "Amavasya" if hit == 30 else TITHI[(hit - 1) % 15]
            out.append({"date": day.isoformat(), "vaar": p["vaar"], "tithi": name, "paksha": "Shukla" if hit <= 15 else "Krishna",
                        "month_amanta": p["month_amanta"],
                        **({"kshaya": True, "note": "Is din suryoday ke baad shuru hokar agle suryoday se pehle khatam"}
                           if t not in want else {})})
            if len(out) >= count:
                break
    return out


# ------------------------------------------------------------------ holidays
def state_code(state: str = "", city: str = "") -> str | None:
    s = (state or "").strip()
    if s.upper() in STATES:
        return s.upper()
    if s.lower() in STATE_NAMES:
        return STATE_NAMES[s.lower()]
    if city and city.strip().lower() in CITIES:
        return CITIES[city.strip().lower()][2]
    return None


def holidays_for(year: int, state: str = "", city: str = "", month: int | None = None) -> list[dict[str, Any]]:
    import holidays as hol
    sub = state_code(state, city)
    try:
        h = hol.India(years=year, subdiv=sub, categories=("public", "government"))
    except Exception:
        h = hol.India(years=year)
    opt = {}
    try:
        opt = hol.India(years=year, subdiv=sub, categories=("optional",))
    except Exception:
        pass
    out = [{"date": d.isoformat(), "name": n, "kind": "public"} for d, n in sorted(h.items())]
    have = {x["date"] for x in out}
    out += [{"date": d.isoformat(), "name": n, "kind": "optional"} for d, n in sorted(opt.items()) if d.isoformat() not in have]
    out.sort(key=lambda x: x["date"])
    if month:
        out = [x for x in out if int(x["date"][5:7]) == month]
    return out


def day_info(d: date, state: str = "", city: str = "") -> dict[str, Any]:
    hs = [h for h in holidays_for(d.year, state, city) if h["date"] == d.isoformat()]
    out = {"date": d.isoformat(), "weekday": d.strftime("%A"), "holidays": hs, "state": state_code(state, city),
           "panchang": panchang(d, city)}
    # bank holidays: 2nd / 4th Saturday + Sundays are fixed; the rest follow the state's list (RBI publishes the official one)
    sat_no = (d.day - 1) // 7 + 1
    bank_closed = d.weekday() == 6 or (d.weekday() == 5 and sat_no in (2, 4)) or any(h["kind"] == "public" for h in hs)
    out["bank_closed_likely"] = bank_closed
    out["bank_note"] = "RBI ki state-wise list hi pakki hai; yeh andaza hai (Ravivar, 2nd/4th Shanivar, sarkari chhutti)."
    return out
