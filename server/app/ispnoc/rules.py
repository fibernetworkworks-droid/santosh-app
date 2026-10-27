"""NOC Sahayak rules: optical classes / budgets, alarm parsing (OLT logs, syslog, SNMP trap text, NMS CSV, email alerts),
correlation to the REAL fault (pure functions, no database), plain-word explanations, teams, SLA starters, vendor command
templates for changes on live equipment (with rollback), and the regulatory facts we cite.

Nothing here talks to equipment. Formats: Syrotech / VSOL / C-Data / BDCOM OLT logs are not publicly documented, so the parser
is word- and pattern-based (port forms seen in common Indian OLT logs: EPON0/1:12, GPON0/3:5, gpon-onu_1/1/3:12 (ZTE),
FrameID/SlotID/PortID/ONT ID (Huawei), "PON 3 ONU 7", "0/1/3 ONT 12"); she can add her own words (`extra_words`).
"""
from __future__ import annotations

import csv
import io
import re
import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------- optics (ONT receive power, dBm)
# ITU-T G.984.2 GPON: class B+ ONU Rx sensitivity -27 dBm, overload -8 dBm; C+ -32 / -12. IEEE 802.3ah EPON PX20 ONU Rx
# sensitivity -24 dBm, overload -3 dBm; "PX20+" modules sold for Indian EPON OLTs usually state -27 dBm (vendor datasheet).
# ok_min = start of the "weak" band (2 dB margin kept for ageing, dirt, temperature).
OPTICS: dict[str, dict[str, Any]] = {
    "gpon_b+": {"label": "GPON class B+", "tech": "gpon", "sens": -27.0, "ok_min": -25.0, "overload": -8.0, "budget_db": 28.0, "olt_tx": 3.0},
    "gpon_c+": {"label": "GPON class C+", "tech": "gpon", "sens": -32.0, "ok_min": -29.0, "overload": -12.0, "budget_db": 32.0, "olt_tx": 5.0},
    "epon_px20": {"label": "EPON PX20", "tech": "epon", "sens": -24.0, "ok_min": -22.0, "overload": -3.0, "budget_db": 24.0, "olt_tx": 4.0},
    "epon_px20+": {"label": "EPON PX20+", "tech": "epon", "sens": -27.0, "ok_min": -25.0, "overload": -3.0, "budget_db": 28.0, "olt_tx": 4.0},
}
SPLIT_LOSS = {2: 3.6, 4: 7.3, 8: 10.5, 16: 13.8, 32: 17.1, 64: 20.5}     # typical PLC splitter insertion loss, dB
FIBRE_DB_KM = 0.35                                                    # G.652 at 1310 nm (upstream, the worse one)
CONNECTOR_DB = 0.5
SPLICE_DB = 0.1
RX_DROP_DB = 3.0                                                      # a drop this big vs its own normal = something changed


def optics_of(key: str) -> dict:
    return OPTICS.get((key or "").lower().strip(), OPTICS["gpon_b+"])


def rx_band(rx: float | None, cls: str = "gpon_b+") -> str:
    """'high' (too strong, overload) | 'good' | 'weak' | 'bad' (below sensitivity: drops / errors) | '' (no value)."""
    if rx is None:
        return ""
    o = optics_of(cls)
    if rx > o["overload"]:
        return "high"
    if rx < o["sens"]:
        return "bad"
    if rx < o["ok_min"]:
        return "weak"
    return "good"


def budget(cls: str = "gpon_b+", km: float = 0.0, splits: list[int] | None = None, connectors: int = 4, splices: int = 4,
           olt_tx: float | None = None) -> dict:
    """Expected loss and ONT Rx for a planned / existing drop. Typical figures, the real link is measured with a power meter."""
    o = optics_of(cls)
    splits = [int(s) for s in (splits or []) if int(s) in SPLIT_LOSS]
    parts = {"fibre": round(max(0.0, km) * FIBRE_DB_KM, 2), "splitters": round(sum(SPLIT_LOSS[s] for s in splits), 2),
             "connectors": round(max(0, connectors) * CONNECTOR_DB, 2), "splices": round(max(0, splices) * SPLICE_DB, 2)}
    loss = round(sum(parts.values()), 2)
    tx = o["olt_tx"] if olt_tx is None else float(olt_tx)
    rx = round(tx - loss, 2)
    margin = round(o["budget_db"] - loss, 2)
    band = rx_band(rx, cls)
    say = (f"Andaazan loss {loss} dB ({', '.join(f'{k} {v}' for k, v in parts.items() if v)}), ONT par Rx lagbhag {rx} dBm "
           f"({o['label']}: theek {o['ok_min']} se {o['overload']}, {o['sens']} se neeche kharab). Margin {margin} dB.")
    if margin < 3:
        say += " Margin 3 dB se kam hai: splitter kam karo ya route chhota karo."
    return {"class": cls, "label": o["label"], "parts": parts, "loss_db": loss, "rx_expected": rx, "margin_db": margin,
            "band": band, "say": say}


# ---------------------------------------------------------------- alarm kinds
KINDS = {
    "los": "ONT ki light gayi (LOS)", "dying_gasp": "ONT ki bijli gayi (dying gasp)", "offline": "ONT offline",
    "online": "ONT wapas online", "rx": "Rx power reading", "rx_low": "Rx kam", "rx_high": "Rx bahut zyada",
    "pon_los": "PON port par light nahi", "pon_up": "PON port wapas", "uplink_down": "Uplink band", "uplink_up": "Uplink wapas",
    "olt_power": "OLT power / PSU", "olt_fan": "OLT fan", "olt_temp": "OLT garam", "olt_cpu": "OLT CPU zyada",
    "olt_restart": "OLT restart / cold start", "olt_unreachable": "OLT se jawab nahi", "olt_up": "OLT wapas",
    "storm": "Loop / broadcast storm", "rogue_onu": "Rogue ONT", "auth_fail": "ONT auth fail", "bng": "BNG / RADIUS dikkat",
}
DOWN = {"los", "dying_gasp", "offline"}

_CLEAR = re.compile(r"\b(clear(?:ed)?|recover(?:ed|y)?|restor(?:e|ed)|resum(?:e|ed)|normal|ok again|back online|is up)\b", re.I)
_K: list[tuple[str, re.Pattern]] = [
    ("dying_gasp", re.compile(r"dying[\s_-]?gasp|\bpower[\s_-]?(?:off|down|fail(?:ure)?)\b.*\b(?:onu|ont)\b|\b(?:onu|ont)\b.*\bpower[\s_-]?(?:off|down|fail)", re.I)),
    ("rogue_onu", re.compile(r"\brogue\b", re.I)),
    ("storm", re.compile(r"\bloop(?:back)? detect|\bloop\b|broadcast[\s_-]?storm|\bstorm\b|mac[\s_-]?flap", re.I)),
    ("auth_fail", re.compile(r"auth(?:entication)?[\s_-]?fail|unauthori[sz]ed onu|illegal (?:onu|ont)|sn conflict|mac conflict|password error", re.I)),
    ("bng", re.compile(r"\bradius\b|\bbng\b|\bbras\b|pppoe.*(?:fail|timeout|reject)", re.I)),
    ("rx_high", re.compile(r"rx[\s_-]?(?:power)?[\s_-]?(?:high|too high|overload)|optical power (?:too )?high", re.I)),
    ("rx_low", re.compile(r"rx[\s_-]?(?:power)?[\s_-]?(?:low|too low|below)|low rx|optical power (?:too )?low|weak (?:optical|signal)|\blowpower\b", re.I)),
    ("olt_power", re.compile(r"\b(?:psu|power supply|power module|mains|ac fail|dc fail|input power)\b", re.I)),
    ("olt_fan", re.compile(r"\bfan\b", re.I)),
    ("olt_temp", re.compile(r"temperature|temp(?:erature)? (?:high|alarm)|over[\s_-]?temp", re.I)),
    ("olt_cpu", re.compile(r"\bcpu\b.*(?:high|usage|overload)", re.I)),
    ("olt_restart", re.compile(r"cold[\s_-]?start|warm[\s_-]?start|system (?:reboot|restart)|olt (?:reboot|restart)|1\.3\.6\.1\.6\.3\.1\.1\.5\.[12]\b", re.I)),
    ("olt_unreachable", re.compile(r"unreachable|no response|ping (?:fail|loss|timeout)|request timed out|snmp timeout|node down", re.I)),
    ("los", re.compile(r"\blos[ifa]?\b|\blofi\b|\bloami\b|loss of (?:signal|frame)|fib(?:er|re)[\s_-]?cut|link[\s_-]?loss|optical loss|signal lost", re.I)),
    ("offline", re.compile(r"de-?regist|offline|deactivat|\bdereg\b|\bdown\b|link fault|\bdisconnect", re.I)),
    ("online", re.compile(r"\bregist(?:er|ered|ration)\b|\bonline\b|\bactivat(?:e|ed)\b|\bauth(?:enticat)?(?:ed)? success|\bis up\b|\bup\b", re.I)),
]
LINK_DOWN_OID = "1.3.6.1.6.3.1.1.5.3"
LINK_UP_OID = "1.3.6.1.6.3.1.1.5.4"

_PORT_PATTERNS = [
    re.compile(r"gpon-onu_(\d+/\d+/\d+):(\d+)", re.I),                                         # ZTE
    re.compile(r"\b[eg]pon\s*(\d+/\d+(?:/\d+)?)\s*[:/]\s*(\d+)\b", re.I),                     # EPON0/1:12, GPON 0/3:5
    re.compile(r"(?:onu|ont)\s*(\d+/\d+(?:/\d+)?)\s*[:/]\s*(\d+)\b", re.I),                   # ONU 0/1/3:12
    re.compile(r"\b(\d+/\d+(?:/\d+)?)\s*(?:,\s*)?(?:onu|ont)(?:[\s_-]?id)?\s*[:=]?\s*(\d+)\b", re.I),   # 0/1/3 ONT 12
    re.compile(r"\bpon(?:[\s_-]?port)?\s*[:=]?\s*(\d+(?:/\d+){0,2})\s*,?\s*(?:onu|ont)(?:[\s_-]?id)?\s*[:=]?\s*(\d+)\b", re.I),   # PON 3 ONU 7
]
_HUAWEI = re.compile(r"frame\s*id\s*:\s*(\d+)\s*,\s*slot\s*id\s*:\s*(\d+)\s*,\s*port\s*id\s*:\s*(\d+)(?:\s*,\s*ont\s*id\s*:\s*(\d+))?", re.I)
_PON_ONLY = re.compile(r"\b(?:[eg]?pon|pon[\s_-]?port|port)\s*[:=]?\s*(\d+(?:/\d+){0,2})\b", re.I)
_UPLINK = re.compile(r"\b((?:ge|xge|xe|te|tge|eth|gei|gigabitethernet|tengigabitethernet|uplink|sfp)[\s_-]?\d+(?:/\d+){0,2})\b", re.I)
_SN = re.compile(r"\b([A-Z]{4}[0-9A-F]{8})\b")
_MAC = re.compile(r"\b([0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5}|[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4})\b")
_RX = re.compile(r"(?:rx(?:[\s_-]?power)?|receive(?:d)? power|optical power|rx optical)[^-\d]{0,12}(-\d{1,2}(?:\.\d{1,3})?)", re.I)
_DBM = re.compile(r"(-\d{1,2}(?:\.\d{1,3})?)\s*dbm", re.I)
_IP = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3})\b")
_MON = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


def norm_pon(p: str) -> str:
    parts = [str(int(x)) for x in re.findall(r"\d+", str(p or ""))]
    return "/".join(parts)


def norm_sn(s: str) -> str:
    return re.sub(r"[^0-9A-Z]", "", str(s or "").upper())


def _when(line: str, tz, year: int) -> tuple[datetime | None, str]:
    """(time, the text after the timestamp). ISO / dd-mm-yyyy / syslog 'Oct 23 10:15:01' / bare 'HH:MM:SS'."""
    s = line.strip()
    m = re.match(r"^\s*\[?(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})[ T,]+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?\]?", s)
    if m:
        y, mo, d, h, mi, se = (int(m.group(i) or 0) for i in range(1, 7))
        tzinfo = tz
        if m.group(7):
            z = m.group(7)
            if z == "Z":
                tzinfo = timezone.utc
            else:
                sign = 1 if z[0] == "+" else -1
                hh, mm = int(z[1:3]), int(z[-2:])
                tzinfo = timezone(sign * timedelta(hours=hh, minutes=mm))
        try:
            return datetime(y, mo, d, h, mi, se, tzinfo=tzinfo), s[m.end():]
        except ValueError:
            return None, s
    m = re.match(r"^\s*\[?(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})[ ,]+(\d{1,2}):(\d{2})(?::(\d{2}))?\]?", s)
    if m:
        d, mo, y, h, mi = (int(m.group(i)) for i in range(1, 6))
        se = int(m.group(6) or 0)
        y = y + 2000 if y < 100 else y
        try:
            return datetime(y, mo, d, h, mi, se, tzinfo=tz), s[m.end():]
        except ValueError:
            return None, s
    m = re.match(r"^\s*(?:<\d+>\s*)?([A-Za-z]{3})\s+(\d{1,2})\s+(\d{1,2}):(\d{2}):(\d{2})", s)
    if m and m.group(1).lower() in _MON:
        try:
            return datetime(year, _MON[m.group(1).lower()], int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)),
                            tzinfo=tz), s[m.end():]
        except ValueError:
            return None, s
    m = re.match(r"^\s*\[?(\d{1,2}):(\d{2}):(\d{2})\]?", s)
    if m:
        return None, s                         # time only: the caller uses "now" (a bare clock can't be trusted for the day)
    return None, s


def classify(text: str, extra_words: dict[str, str] | None = None) -> tuple[str, bool]:
    """-> (kind, clear). Her own words (extra_words {word: kind}) win."""
    t = str(text or "")
    low = t.lower()
    for w, k in (extra_words or {}).items():
        if w and w.lower() in low and k in KINDS:
            return k, bool(_CLEAR.search(t)) or k in ("online", "pon_up", "uplink_up", "olt_up")
    if LINK_DOWN_OID in t:
        return "uplink_down", False
    if LINK_UP_OID in t:
        return "uplink_up", True
    clear = bool(_CLEAR.search(t))
    for kind, rx in _K:
        if rx.search(t):
            return kind, clear
    return "", clear


def parse_line(line: str, tz=timezone.utc, now_: datetime | None = None, extra_words: dict[str, str] | None = None) -> dict | None:
    """One alarm line -> event dict {at, host, ip, pon, onu, sn, port, kind, clear, rx, raw} or None when it says nothing useful."""
    raw = str(line or "").strip()
    if len(raw) < 4:
        return None
    now_ = now_ or datetime.now(timezone.utc)
    at, rest = _when(raw, tz, now_.astimezone(tz).year)
    if at and at > now_ + timedelta(days=1):                      # syslog without a year around New Year
        at = at.replace(year=at.year - 1)
    host = ""
    m = re.match(r"^\s*(?:<\d+>\s*)?([A-Za-z][\w.-]{1,40})\s+[\w%-]*", rest)
    if m and not re.fullmatch(r"(?i)(gpon|epon|pon|onu|ont|olt|port|alarm|the|link|interface|snmp|trap|frameid:?|\d[\d.]*)", m.group(1)):
        host = m.group(1)
    ipm = _IP.search(raw)
    ip = ipm.group(1) if ipm else ""
    pon = onu = ""
    hw = _HUAWEI.search(raw)
    if hw:
        pon = norm_pon(f"{hw.group(1)}/{hw.group(2)}/{hw.group(3)}")
        onu = hw.group(4) or ""
    else:
        for p in _PORT_PATTERNS:
            pm = p.search(raw)
            if pm:
                pon, onu = norm_pon(pm.group(1)), str(int(pm.group(2)))
                break
    upl = ""
    if not pon:
        um = _UPLINK.search(raw)
        if um:
            upl = re.sub(r"\s+", "", um.group(1)).lower()
        else:
            pm = _PON_ONLY.search(raw)
            if pm and re.search(r"(?i)\b[eg]?pon\b", raw):
                pon = norm_pon(pm.group(1))
    sn = ""
    sm = _SN.search(raw.upper())
    if sm and not sm.group(1).startswith(("GPON", "EPON")):
        sn = sm.group(1)
    else:
        mm = _MAC.search(raw)
        if mm:
            sn = norm_sn(mm.group(1))
    rx = None
    rm = _RX.search(raw) or _DBM.search(raw)
    if rm:
        try:
            v = float(rm.group(1))
            rx = v if -45 < v < 10 else None
        except ValueError:
            rx = None
    kind, clear = classify(raw, extra_words)
    if upl and kind in ("offline", "los", "online") and not onu:
        kind = "uplink_up" if (kind == "online" or clear) else "uplink_down"
    if pon and not onu and not sn and kind in ("los", "offline"):
        kind = "pon_up" if clear else "pon_los"
    if pon and not onu and not sn and kind == "online":
        kind = "pon_up"
    if kind == "online" and not (pon or onu or sn or upl):
        kind = "olt_up"                                  # "node is up / reachable again" about the device itself
    if kind in ("olt_unreachable",) and clear:
        kind, clear = "olt_up", True
    if kind in DOWN and clear:
        kind = "online"
    if kind == "uplink_down" and clear:
        kind = "uplink_up"
    if kind == "pon_los" and clear:
        kind = "pon_up"
    if not kind and rx is not None:
        kind = "rx"
    if not kind:
        return None
    return {"at": at, "host": host, "ip": ip, "pon": pon, "onu": onu, "sn": sn, "port": upl, "kind": kind,
            "clear": clear or kind in ("online", "pon_up", "uplink_up", "olt_up"), "rx": rx, "raw": scrub(raw)[:400]}


_COLS = {
    "at": ("time", "date", "timestamp", "occur", "raised", "alarm time", "start time", "event time"),
    "host": ("olt", "device", "host", "ne name", "node", "olt name", "source"),
    "ip": ("ip", "olt ip", "device ip", "ne ip"),
    "pon": ("pon", "pon port", "port", "interface", "location"),
    "onu": ("onu", "ont", "onu id", "ont id", "llid"),
    "sn": ("sn", "serial", "mac", "onu sn", "ont sn", "onu mac"),
    "alarm": ("alarm", "event", "alarm name", "description", "message", "type", "status", "cause", "reason"),
    "rx": ("rx", "rx power", "rx power(dbm)", "optical rx", "receive power"),
}


def _col(header: list[str], key: str) -> int:
    hs = [h.strip().lower() for h in header]
    for want in _COLS[key]:
        if want in hs:
            return hs.index(want)
    for i, h in enumerate(hs):
        if any(h.startswith(w) for w in _COLS[key]):
            return i
    return -1


def parse_text(text: str, tz=timezone.utc, now_: datetime | None = None, extra_words: dict[str, str] | None = None,
               limit: int = 5000) -> dict:
    """Paste / file / email text -> {events, skipped}. CSV from an NMS (header with time / alarm / port...) or free log lines."""
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [x for x in text.split("\n") if x.strip()][:limit]
    events: list[dict] = []
    skipped = 0
    if lines and lines[0].count(",") >= 2 and any(w in lines[0].lower() for w in ("alarm", "event", "onu", "ont", "pon", "time")):
        rows = list(csv.reader(io.StringIO("\n".join(lines))))
        head = rows[0]
        idx = {k: _col(head, k) for k in _COLS}
        for row in rows[1:]:
            get = lambda k: (row[idx[k]].strip() if 0 <= idx[k] < len(row) else "")   # noqa: E731
            parts = []
            if get("at"):
                parts.append(get("at"))
            if get("host"):
                parts.append(get("host"))
            pon, onu = get("pon"), get("onu")
            if pon and onu:
                parts.append(f"PON {norm_pon(pon)} ONU {re.sub(r'[^0-9]', '', onu) or onu}")
            elif pon:
                parts.append(f"PON {pon}" if re.fullmatch(r"[\d/]+", pon) else pon)
            if get("sn"):
                parts.append(get("sn"))
            parts.append(get("alarm"))
            if get("rx"):
                parts.append(f"rx {get('rx')} dBm")
            if get("ip"):
                parts.append(get("ip"))
            ev = parse_line(" ".join(p for p in parts if p), tz, now_, extra_words)
            if ev:
                events.append(ev)
            else:
                skipped += 1
        return {"events": events, "skipped": skipped, "format": "csv"}
    for ln in lines:
        ev = parse_line(ln, tz, now_, extra_words)
        if ev:
            events.append(ev)
        else:
            skipped += 1
    return {"events": events, "skipped": skipped, "format": "lines"}


# ---------------------------------------------------------------- secrets never kept
_SECRET = re.compile(r"(?i)\b(password|passwd|pwd|pass ?word|enable secret|snmp community|community string)\b(\s*(?:is|hai|:|=|-)?\s*)(\S{3,})"
                     r"|\b(pass|secret|community|key|token|api[_ -]?key)\b(\s*(?:is|hai|:|=)\s*)(\S{3,})")


def scrub(text: str) -> str:
    """Device passwords / SNMP communities / keys someone pasted are blanked before anything is stored."""
    return _SECRET.sub(lambda m: f"{m.group(1) or m.group(4)}{m.group(2) if m.group(1) else m.group(5)}[hataya]", str(text or ""))


def has_secret(text: str) -> bool:
    return bool(_SECRET.search(str(text or "")))


# ---------------------------------------------------------------- teams + SLA starters
TEAMS = {
    "field_fibre": "Field fibre team", "noc": "NOC / OLT team", "bsnl": "BSNL (franchise / upstream)", "upstream": "Upstream ISP / bandwidth",
    "customer": "Customer side", "electricity": "Bijli (MSEB / DISCOM)", "vendor": "OLT vendor / support",
}
# Starter hours to fix (clock). TRAI's Aug 2026 draft proposes MTTR <= 10 h for wireline broadband (not final); the 2006
# broadband QoS rule was fault repair by the next working day. Her own / her BSNL agreement's hours always win.
SLA_DEFAULT = {"olt_down": 2, "uplink": 2, "uplink_flap": 4, "storm": 2, "rogue_onu": 4, "feeder_cut": 4, "splitter_branch": 6,
               "drop_fibre": 10, "ont_offline": 10, "flap": 24, "rx_bad": 24, "pon_degrade": 24, "rx_high": 48, "bng": 2,
               "area_power": 0, "customer_power": 0}

FAULTS = {
    "olt_down": {"title": "Poora OLT band", "team": "noc", "scope": "olt"},
    "uplink": {"title": "Uplink band (internet upar se nahi aa raha)", "team": "noc", "scope": "uplink"},
    "uplink_flap": {"title": "Uplink baar baar gir raha hai", "team": "noc", "scope": "uplink"},
    "bng": {"title": "BNG / RADIUS dikkat (login nahi ho raha)", "team": "upstream", "scope": "olt"},
    "storm": {"title": "Loop / broadcast storm", "team": "noc", "scope": "pon"},
    "rogue_onu": {"title": "Rogue ONT poora PON bigaad raha hai", "team": "field_fibre", "scope": "pon"},
    "area_power": {"title": "Area mein bijli gayi", "team": "electricity", "scope": "pon"},
    "feeder_cut": {"title": "Feeder fibre cut / pehla splitter", "team": "field_fibre", "scope": "pon"},
    "splitter_branch": {"title": "Ek splitter / uski branch band", "team": "field_fibre", "scope": "splitter"},
    "pon_degrade": {"title": "Poore PON ki light kam ho gayi", "team": "field_fibre", "scope": "pon"},
    "drop_fibre": {"title": "Customer ki drop fibre / patch cord", "team": "field_fibre", "scope": "ont"},
    "customer_power": {"title": "Customer ke ghar bijli / adapter", "team": "customer", "scope": "ont"},
    "ont_offline": {"title": "ONT offline", "team": "field_fibre", "scope": "ont"},
    "flap": {"title": "ONT baar baar aa-ja raha hai", "team": "field_fibre", "scope": "ont"},
    "rx_bad": {"title": "ONT ki light kharab (Rx)", "team": "field_fibre", "scope": "ont"},
    "rx_high": {"title": "ONT par light zyada (overload)", "team": "field_fibre", "scope": "ont"},
}


def sla_for(kind: str, custom: dict | None = None) -> float:
    c = custom or {}
    try:
        if kind in c and c[kind] is not None:
            return float(c[kind])
    except (TypeError, ValueError):
        pass
    return float(SLA_DEFAULT.get(kind, 24))


def conf_label(c: float) -> str:
    return "pakka jaisa" if c >= 0.8 else ("shayad" if c >= 0.55 else "andaaza")


# ---------------------------------------------------------------- correlation (pure)
def _t(e: dict) -> datetime:
    return e["at"]


def ont_states(events: list[dict]) -> dict[str, dict]:
    """events sorted by time with 'ont' (inventory id or 'olt|pon|onu' / sn key) -> latest state per ONT + flap counts."""
    st: dict[str, dict] = {}
    for e in sorted(events, key=_t):
        k = e.get("ont")
        if not k:
            continue
        s = st.setdefault(k, {"state": "", "kind": "", "since": None, "downs": [], "rx": [], "olt": e.get("olt", ""), "pon": e.get("pon", "")})
        if e.get("pon"):
            s["pon"] = e["pon"]
        if e.get("olt"):
            s["olt"] = e["olt"]
        if e["kind"] in DOWN:
            if s["state"] != "down":
                s["since"] = e["at"]
            # dying gasp followed by LOS (power cut sends both on some ONTs) stays "dying_gasp"
            if not (s["state"] == "down" and s["kind"] == "dying_gasp" and e["kind"] in ("los", "offline")):
                s["kind"] = e["kind"]
            s["state"] = "down"
            s["downs"].append(e["at"])
        elif e["kind"] == "online":
            s["state"], s["since"] = "up", e["at"]
        if e.get("rx") is not None:
            s["rx"].append((e["at"], e["rx"]))
    return st


def correlate(events: list[dict], inv: dict, now_: datetime, window_min: int = 15, optics_default: str = "gpon_b+") -> list[dict]:
    """The real faults behind a pile of alarms.

    events: [{at, olt, pon, onu, ont, kind, rx, port, raw}] (olt = inventory OLT id or host; ont = inventory ONT id or a key).
    inv: {"olts": {olt_id: {name, pons, optics, uplinks}}, "onts": {ont_id: {olt, pon, splitter, rx_base, customer}},
          "splitters": {name: {olt, pon, level}}}.
    -> faults [{key, kind, scope, olt, pon, target, started, last, affected, n_affected, n_total, confidence, reasons, evidence}].
    """
    W = timedelta(minutes=max(1, window_min))
    out: list[dict] = []
    olts = inv.get("olts", {})
    onts = inv.get("onts", {})
    by_pon_total: dict[tuple[str, str], list[str]] = {}
    for oid, o in onts.items():
        if o.get("active", True):
            by_pon_total.setdefault((o.get("olt", ""), o.get("pon", "")), []).append(oid)
    evs = sorted([e for e in events if e.get("at")], key=_t)
    states = ont_states(evs)
    taken: set[str] = set()

    def evidence(sel) -> list[dict]:
        rows = [{"at": e["at"].isoformat(timespec="seconds"), "kind": e["kind"], "line": e.get("raw", "")[:200]} for e in sel]
        return rows[:12] + ([{"at": "", "kind": "", "line": f"... aur {len(rows) - 12} alarm"}] if len(rows) > 12 else [])

    # ---- OLT level
    for olt in sorted({e.get("olt", "") for e in evs if e.get("olt")}):
        mine = [e for e in evs if e.get("olt") == olt]
        hard = [e for e in mine if e["kind"] in ("olt_unreachable", "olt_power", "olt_restart")]
        last_up = max((e["at"] for e in mine if e["kind"] in ("olt_up",)), default=None)
        down_onts = [k for k, s in states.items() if s["olt"] == olt and s["state"] == "down"]
        pons_down = {states[k]["pon"] for k in down_onts}
        known_pons = {p for (o, p) in by_pon_total if o == olt and p}
        all_onts = [k for (o, _p), ks in by_pon_total.items() if o == olt for k in ks]
        frac = (len([k for k in down_onts if k in all_onts]) / len(all_onts)) if all_onts else 0.0
        hard_live = [e for e in hard if not last_up or e["at"] > last_up]
        if hard_live and not down_onts and any(e["kind"] == "online" and e["at"] > hard_live[-1]["at"] for e in mine):
            hard_live = []                               # its customers came back after the alarm
        if hard_live or (len(pons_down) >= 2 and known_pons and len(pons_down & known_pons) >= max(2, int(0.8 * len(known_pons)))
                         and frac >= 0.8):
            reasons = []
            conf = 0.55
            if hard_live:
                reasons.append(f"OLT ka khud ka alarm: {KINDS.get(hard_live[0]['kind'], hard_live[0]['kind'])}")
                conf += 0.25
            if frac >= 0.8:
                reasons.append(f"OLT ke {len(down_onts)} / {len(all_onts)} ONT ek saath band, {len(pons_down)} PON par")
                conf += 0.15
            gasp = sum(1 for k in down_onts if states[k]["kind"] == "dying_gasp")
            if down_onts and gasp / len(down_onts) >= 0.6:
                reasons.append("zyada ONT ne dying gasp bheja: OLT site ke aaspaas poore area ki bijli gayi ho sakti hai")
            started = min([e["at"] for e in hard_live] + [states[k]["since"] for k in down_onts if states[k]["since"]], default=now_)
            out.append({"key": f"olt_down:{olt}", "kind": "olt_down", "scope": "olt", "olt": olt, "pon": "", "target": olt,
                        "started": started, "last": max(e["at"] for e in mine), "affected": sorted(set(all_onts) | set(down_onts)),
                        "n_affected": max(len(all_onts), len(down_onts)), "n_total": len(all_onts), "confidence": round(min(conf, 0.95), 2),
                        "reasons": reasons, "evidence": evidence(hard_live + [e for e in mine if e["kind"] in DOWN][:6])})
            taken.update(down_onts)
            taken.add(f"olt:{olt}")
        # uplink
        ups: dict[str, list[dict]] = {}
        for e in mine:
            if e["kind"] in ("uplink_down", "uplink_up") and f"olt:{olt}" not in taken:
                ups.setdefault(e.get("port") or "uplink", []).append(e)
        for port, ue in ups.items():
            downs = [e for e in ue if e["kind"] == "uplink_down"]
            recent = [e for e in downs if e["at"] >= now_ - timedelta(minutes=30)]
            last = ue[-1]
            if len(recent) >= 3:
                out.append({"key": f"uplink_flap:{olt}:{port}", "kind": "uplink_flap", "scope": "uplink", "olt": olt, "pon": "", "target": port,
                            "started": recent[0]["at"], "last": last["at"], "affected": list(all_onts), "n_affected": len(all_onts),
                            "n_total": len(all_onts), "confidence": 0.85, "reasons": [f"{port} 30 minute mein {len(recent)} baar gira"],
                            "evidence": evidence(ue)})
            elif last["kind"] == "uplink_down":
                out.append({"key": f"uplink:{olt}:{port}", "kind": "uplink", "scope": "uplink", "olt": olt, "pon": "", "target": port,
                            "started": last["at"], "last": last["at"], "affected": list(all_onts), "n_affected": len(all_onts),
                            "n_total": len(all_onts), "confidence": 0.8,
                            "reasons": [f"{port} band hai aur wapas aane ka alarm nahi aaya; ONT online dikh sakte hain par internet nahi"],
                            "evidence": evidence(ue)})
        bng = [e for e in mine if e["kind"] == "bng" and e["at"] >= now_ - W * 2]
        if len(bng) >= 2:
            out.append({"key": f"bng:{olt}", "kind": "bng", "scope": "olt", "olt": olt, "pon": "", "target": olt, "started": bng[0]["at"],
                        "last": bng[-1]["at"], "affected": [], "n_affected": 0, "n_total": len(all_onts), "confidence": 0.6,
                        "reasons": [f"{len(bng)} BNG / RADIUS / PPPoE alarm"], "evidence": evidence(bng)})

    # ---- PON level
    pon_keys = sorted({(s["olt"], s["pon"]) for k, s in states.items() if s["state"] == "down" and k not in taken and s["pon"]}
                      | {(e.get("olt", ""), e["pon"]) for e in evs if e["kind"] in ("pon_los", "storm", "rogue_onu") and e.get("pon")})
    for olt, pon in pon_keys:
        if f"olt:{olt}" in taken:
            continue
        down = [k for k, s in states.items() if s["state"] == "down" and s["olt"] == olt and s["pon"] == pon and k not in taken]
        total = by_pon_total.get((olt, pon), [])
        ponev = [e for e in evs if e.get("olt") == olt and e.get("pon") == pon]
        ponlos = [e for e in ponev if e["kind"] == "pon_los"]
        pon_up_after = ponlos and any(e["kind"] == "pon_up" and e["at"] > ponlos[-1]["at"] for e in ponev)
        storm = [e for e in ponev if e["kind"] == "storm" and e["at"] >= now_ - W * 4]
        rogue = [e for e in ponev if e["kind"] == "rogue_onu" and e["at"] >= now_ - W * 4]
        base = {"olt": olt, "pon": pon, "n_total": len(total)}
        if storm:
            out.append({**base, "key": f"storm:{olt}:{pon}", "kind": "storm", "scope": "pon", "target": f"PON {pon}", "started": storm[0]["at"],
                        "last": storm[-1]["at"], "affected": list(total), "n_affected": len(total), "confidence": 0.75,
                        "reasons": [f"{len(storm)} loop / storm alarm PON {pon} par"], "evidence": evidence(storm)})
        if rogue:
            out.append({**base, "key": f"rogue_onu:{olt}:{pon}", "kind": "rogue_onu", "scope": "pon", "target": f"PON {pon}",
                        "started": rogue[0]["at"], "last": rogue[-1]["at"], "affected": sorted(set(down) | set(total)),
                        "n_affected": max(len(down), len(total)), "confidence": 0.8,
                        "reasons": ["OLT ne rogue ONT bataya: ek ONT lagatar light bhej kar baaki sab ko bigaad raha hai"], "evidence": evidence(rogue)})
            taken.update(down)
            continue
        if not down and not (ponlos and not pon_up_after):
            continue
        downs_t = sorted(states[k]["since"] for k in down if states[k]["since"])
        tight = bool(downs_t) and (downs_t[-1] - downs_t[0]) <= timedelta(minutes=3)
        gasp = sum(1 for k in down if states[k]["kind"] == "dying_gasp")
        gasp_share = gasp / len(down) if down else 0.0
        ratio = (len([k for k in down if k in total]) / len(total)) if total else None
        started = downs_t[0] if downs_t else (ponlos[0]["at"] if ponlos else now_)
        last = max([e["at"] for e in ponev], default=started)
        sel = ponlos + [e for e in ponev if e["kind"] in DOWN]
        if len(down) >= 3 and gasp_share >= 0.6:
            conf = 0.6 + (0.2 if tight else 0) + (0.1 if gasp_share >= 0.85 else 0)
            out.append({**base, "key": f"area_power:{olt}:{pon}", "kind": "area_power", "scope": "pon", "target": f"PON {pon}",
                        "started": started, "last": last, "affected": down, "n_affected": len(down), "confidence": round(min(conf, 0.92), 2),
                        "reasons": [f"{gasp} / {len(down)} ONT ne band hone se pehle dying gasp bheja (bijli jaane ka signal)"]
                        + (["sab 3 minute ke andar"] if tight else []), "evidence": evidence(sel)})
            taken.update(down)
            continue
        feeder = (ponlos and not pon_up_after) or (ratio is not None and ratio >= 0.8 and len(down) >= 2) or \
                 (ratio is None and len(down) >= 4 and tight)
        if feeder:
            conf = 0.5 + (0.3 * ratio if ratio is not None else 0.1) + (0.15 if ponlos else 0) + (0.05 if tight else 0)
            if 0.3 <= gasp_share < 0.6:
                conf -= 0.2
            reasons = []
            if ponlos:
                reasons.append(f"OLT ne PON {pon} par hi light nahi dekhi (PON LOS)")
            if ratio is not None:
                reasons.append(f"PON {pon} ke {len([k for k in down if k in total])} / {len(total)} ONT band")
            else:
                reasons.append(f"PON {pon} ke {len(down)} ONT band (is PON ki poori list Hoola ke paas nahi)")
            if tight:
                reasons.append("sab ek saath (3 minute ke andar) gaye: ek hi jagah kata hai")
            if gasp_share >= 0.3:
                reasons.append(f"{gasp} ne dying gasp bheja: kuch jagah bijli bhi gayi ho sakti hai")
            out.append({**base, "key": f"feeder_cut:{olt}:{pon}", "kind": "feeder_cut", "scope": "pon", "target": f"PON {pon}",
                        "started": started, "last": last, "affected": sorted(set(down) | set(total if ratio is not None and ratio >= 0.8 else [])),
                        "n_affected": max(len(down), len(total) if ratio is not None and ratio >= 0.8 else 0),
                        "confidence": round(max(0.3, min(conf, 0.95)), 2), "reasons": reasons, "evidence": evidence(sel)})
            taken.update(down)
            continue
        # splitter branches inside this PON
        by_spl: dict[str, list[str]] = {}
        for k in total:
            sp = onts.get(k, {}).get("splitter", "")
            if sp:
                by_spl.setdefault(sp, []).append(k)
        for sp, members in sorted(by_spl.items()):
            d = [k for k in down if k in members]
            if len(d) >= 2 and len(d) / len(members) >= 0.7:
                dt = sorted(states[k]["since"] for k in d if states[k]["since"])
                g = sum(1 for k in d if states[k]["kind"] == "dying_gasp")
                conf = 0.55 + 0.3 * (len(d) / len(members)) + (0.05 if dt and dt[-1] - dt[0] <= timedelta(minutes=3) else 0) - (0.2 if g >= len(d) / 2 else 0)
                out.append({**base, "key": f"splitter_branch:{olt}:{pon}:{sp}", "kind": "splitter_branch", "scope": "splitter",
                            "target": sp, "started": dt[0] if dt else started, "last": last, "affected": members, "n_affected": len(members),
                            "n_total": len(members), "confidence": round(min(conf, 0.92), 2),
                            "reasons": [f"splitter {sp} ke {len(d)} / {len(members)} ONT band, PON ke baaki chal rahe hain"],
                            "evidence": evidence([e for e in ponev if e.get("ont") in d])})
                taken.update(d)

    # ---- single ONTs (down)
    for k, s in states.items():
        if s["state"] != "down" or k in taken:
            continue
        recent_downs = [t for t in s["downs"] if t >= now_ - timedelta(hours=1)]
        kind = {"los": "drop_fibre", "dying_gasp": "customer_power", "offline": "ont_offline"}[s["kind"] or "offline"]
        reasons = [f"sirf yeh ONT ({KINDS.get(s['kind'], s['kind'])}), PON ke baaki chal rahe hain"]
        conf = 0.7 if s["kind"] in ("los", "dying_gasp") else 0.5
        if len(recent_downs) >= 3:
            kind, conf = "flap", 0.75
            reasons = [f"ek ghante mein {len(recent_downs)} baar gaya: dheela connector / adapter / mudi hui fibre"]
        sel = [e for e in evs if e.get("ont") == k]
        out.append({"key": f"{kind}:{k}", "kind": kind, "scope": "ont", "olt": s["olt"], "pon": s["pon"], "target": k, "started": s["since"] or now_,
                    "last": sel[-1]["at"] if sel else now_, "affected": [k], "n_affected": 1, "n_total": 1, "confidence": conf,
                    "reasons": reasons, "evidence": evidence(sel)})
        taken.add(k)
    # flapping ONTs that are up right now
    for k, s in states.items():
        if k in taken or s["state"] != "up":
            continue
        recent_downs = [t for t in s["downs"] if t >= now_ - timedelta(hours=1)]
        if len(recent_downs) >= 3:
            sel = [e for e in evs if e.get("ont") == k]
            out.append({"key": f"flap:{k}", "kind": "flap", "scope": "ont", "olt": s["olt"], "pon": s["pon"], "target": k,
                        "started": recent_downs[0], "last": sel[-1]["at"], "affected": [k], "n_affected": 1, "n_total": 1, "confidence": 0.75,
                        "reasons": [f"ek ghante mein {len(recent_downs)} baar gaya aur aaya"], "evidence": evidence(sel)})
            taken.add(k)

    # ---- optical (Rx) health
    rx_now: dict[str, tuple[float, float | None]] = {}
    for k, s in states.items():
        if not s["rx"] or k in taken:
            continue
        latest = s["rx"][-1][1]
        earlier = [v for _t2, v in s["rx"][:-1]]
        base_rx = onts.get(k, {}).get("rx_base")
        if base_rx is None and len(earlier) >= 2:
            base_rx = statistics.median(earlier)
        rx_now[k] = (latest, base_rx)
    drops: dict[tuple[str, str], list[tuple[str, float]]] = {}
    for k, (latest, base_rx) in rx_now.items():
        if base_rx is not None and base_rx - latest >= RX_DROP_DB:
            drops.setdefault((states[k]["olt"], states[k]["pon"]), []).append((k, base_rx - latest))
    for (olt, pon), lst in drops.items():
        total = by_pon_total.get((olt, pon), [])
        if len(lst) >= 3 and (not total or len(lst) / max(1, len(total)) >= 0.5):
            deltas = [d for _k, d in lst]
            spread = statistics.pstdev(deltas) if len(deltas) > 1 else 0.0
            conf = 0.6 + (0.2 if spread <= 1.5 else 0) + (0.1 if total and len(lst) / len(total) >= 0.8 else 0)
            out.append({"key": f"pon_degrade:{olt}:{pon}", "kind": "pon_degrade", "scope": "pon", "olt": olt, "pon": pon, "target": f"PON {pon}",
                        "started": now_, "last": now_, "affected": [k for k, _d in lst], "n_affected": len(lst), "n_total": len(total),
                        "confidence": round(min(conf, 0.9), 2),
                        "reasons": [f"PON {pon} ke {len(lst)} ONT ki light lagbhag {statistics.mean(deltas):.1f} dB ek saath giri: "
                                    "feeder par mod / gandi OLT port / OLT ka SFP"],
                        "evidence": [{"at": "", "kind": "rx", "line": f"{k}: -{d:.1f} dB"} for k, d in lst[:12]]})
            taken.update(k for k, _d in lst)
    for k, (latest, base_rx) in rx_now.items():
        if k in taken:
            continue
        cls = olts.get(states[k]["olt"], {}).get("optics") or optics_default
        band = rx_band(latest, cls)
        dropped = base_rx is not None and base_rx - latest >= RX_DROP_DB
        if band in ("bad", "weak") and (band == "bad" or dropped) or band == "high":
            kind = "rx_high" if band == "high" else "rx_bad"
            o = optics_of(cls)
            reasons = [f"Rx {latest} dBm ({o['label']}: {o['sens']} se neeche kharab, {o['ok_min']} tak theek)" if kind == "rx_bad"
                       else f"Rx {latest} dBm, {o['overload']} se zyada: ONT ki receiver overload"]
            if dropped:
                reasons.append(f"pehle {base_rx} dBm tha: {base_rx - latest:.1f} dB gira")
            out.append({"key": f"{kind}:{k}", "kind": kind, "scope": "ont", "olt": states[k]["olt"], "pon": states[k]["pon"], "target": k,
                        "started": now_, "last": now_, "affected": [k], "n_affected": 1, "n_total": 1,
                        "confidence": 0.8 if band == "bad" or kind == "rx_high" else 0.6, "reasons": reasons,
                        "evidence": [{"at": t.isoformat(timespec="seconds"), "kind": "rx", "line": f"{v} dBm"} for t, v in states[k]["rx"][-6:]]})
    return out


# ---------------------------------------------------------------- plain words
_EXPLAIN = {
    "olt_down": ("Poora OLT {olt} band hai: is par ke saare {n} customer offline. Sabse aam wajah: OLT site ki bijli / UPS khatam, "
                 "OLT hang / restart, ya OLT ka power module. Pehle site par bijli aur UPS dekhiye."),
    "uplink": ("OLT {olt} ka uplink {target} band hai. ONT jal rahe honge par internet upar se nahi aa raha: switch / router port, "
               "uplink SFP / patch cord, ya upar wale ({up}) ki taraf dikkat."),
    "uplink_flap": ("OLT {olt} ka uplink {target} baar baar gir-uth raha hai: SFP ya patch cord dheela / gandi, ya upar wale "
                    "({up}) ka link. Customers ko net ruk-ruk kar milega."),
    "bng": "Login (PPPoE / RADIUS / BNG) mein dikkat dikh rahi hai: ONT chalu hain par customers login nahi kar pa rahe. Upar wale ({up}) se baat kijiye.",
    "storm": "PON {pon} par loop / broadcast storm hai: kisi customer ne router ke do port aapas mein jod diye ya switch loop. Us PON ka net dheema / band.",
    "rogue_onu": ("PON {pon} par ek kharab (rogue) ONT lagatar light bhej raha hai, isliye us PON ke baaki ONT bhi gir rahe hain. "
                  "Team ko us PON ke ONT ek-ek karke dekhne honge."),
    "area_power": ("PON {pon} ke {n} customers ke ONT ne band hone se pehle 'dying gasp' bheja: wahan bijli gayi hai, fibre theek "
                   "lag rahi hai. Bijli aate hi wapas aa jaayenge; tab bhi na aaye to fibre dekhni hogi."),
    "feeder_cut": ("PON {pon} ke {n} customers ek saath band hue: OLT se pehle splitter tak ki main (feeder) fibre kati hai ya pehla "
                   "splitter kharab. Route: {route}."),
    "splitter_branch": "Splitter {target} ke neeche ke {n} customers band, baaki PON chal raha hai: us splitter ki taraf aane wali fibre ya splitter khud.",
    "pon_degrade": ("PON {pon} ke {n} ONT ki light ek saath kam hui: feeder par kahin mod / dabav, OLT port ka connector gandi, ya OLT ka "
                    "SFP purana. Abhi chal raha hai par barsaat / garmi mein gir sakta hai."),
    "drop_fibre": "Sirf {cust} ka ONT band (light gayi): unke ghar tak ki drop fibre / patch cord / connector. Field team bhejiye.",
    "customer_power": "{cust} ke ONT ne dying gasp bheja: unke ghar bijli gayi ya ONT ka adapter. Fibre theek hai; customer se poochh lijiye.",
    "ont_offline": "{cust} ka ONT offline hai (wajah alarm mein saaf nahi). Customer se light / bijli poochhiye, phir team.",
    "flap": "{cust} ka ONT baar baar aa-ja raha hai: dheela connector, mudi hui fibre ya kharab adapter. Customer ko net tootta milega.",
    "rx_bad": "{cust} ke ONT ki light kam hai ({rx}): gandi connector / patch cord, fibre mudi hui. Saaf karke dobara Rx naapiye.",
    "rx_high": "{cust} ke ONT par light zyada hai ({rx}): OLT ke bahut paas, attenuator lagana padega.",
}
_CUSTOMER = {
    "olt_down": "Namaskar, {isp} ki taraf se: aapke area mein network equipment mein dikkat ki wajah se internet band hai. Team kaam par hai. Theek hone ka andaazan samay: {eta}. Asuvidha ke liye maafi.",
    "uplink": "Namaskar, {isp} ki taraf se: humare main link mein dikkat ki wajah se internet band hai. Team kaam par hai. Andaazan samay: {eta}.",
    "uplink_flap": "Namaskar, {isp} ki taraf se: main link mein dikkat ki wajah se internet ruk-ruk kar chal raha hai. Team theek kar rahi hai. Andaazan samay: {eta}.",
    "bng": "Namaskar, {isp} ki taraf se: login server mein dikkat ki wajah se internet nahi chal raha. Hum theek karwa rahe hain. Andaazan samay: {eta}.",
    "storm": "Namaskar, {isp} ki taraf se: aapke area mein network dheema / band hai, team theek kar rahi hai. Andaazan samay: {eta}.",
    "rogue_onu": "Namaskar, {isp} ki taraf se: aapke area mein network mein dikkat hai, team jaanch kar rahi hai. Andaazan samay: {eta}.",
    "area_power": "Namaskar, {isp} ki taraf se: aapke area mein bijli jaane ki wajah se internet band hai. Bijli aate hi chalu ho jayega; tab bhi na chale to humein bataiye.",
    "feeder_cut": "Namaskar, {isp} ki taraf se: aapke area ki main fibre mein dikkat (cut) hai. Team jagah par ja rahi hai. Theek hone ka andaazan samay: {eta}. Asuvidha ke liye maafi.",
    "splitter_branch": "Namaskar, {isp} ki taraf se: aapki gali / building ki fibre mein dikkat hai, team aa rahi hai. Andaazan samay: {eta}.",
    "pon_degrade": "",
    "drop_fibre": "Namaskar {name}, {isp} se: aapke connection ki fibre mein dikkat dikh rahi hai. Humari team aapse sampark karegi. Andaazan samay: {eta}.",
    "customer_power": "Namaskar {name}, {isp} se: aapka ONT (router ka dabba) band dikh raha hai. Kripya dekhiye ki uski bijli / adapter chalu hai.",
    "ont_offline": "Namaskar {name}, {isp} se: aapka ONT band dikh raha hai. Kya uski light jal rahi hai? Bataiye, hum madad karenge.",
    "flap": "Namaskar {name}, {isp} se: aapka connection baar baar toot raha hai, humari team aapse sampark karegi.",
    "rx_bad": "Namaskar {name}, {isp} se: aapki fibre ki light kam aa rahi hai, team aakar theek karegi. Andaazan samay: {eta}.",
    "rx_high": "",
}


def explain(f: dict, names: dict | None = None) -> str:
    n = names or {}
    rx = n.get("rx")
    return _EXPLAIN.get(f["kind"], "Network mein dikkat dikhi.").format(
        olt=n.get("olt") or f.get("olt") or "?", pon=f.get("pon") or "?", target=n.get("target") or f.get("target") or "?",
        n=f.get("n_affected") or "kuch", up=n.get("upstream") or "upstream", route=n.get("route") or "[route ka naam nahi pata]",
        cust=n.get("customer") or "Is customer", rx=f"{rx} dBm" if rx is not None else "kam")


def customer_message(f: dict, isp: str, eta: str = "", name: str = "") -> str:
    t = _CUSTOMER.get(f["kind"], "")
    if not t:
        return ""
    return t.format(isp=isp or "[ISP ka naam]", eta=eta or "[samay]", name=name or "ji")


# ---------------------------------------------------------------- changes on live equipment
CHANGE_ACTIONS = {
    "reboot_ont": "ONT restart", "pon_reset": "PON port band karke chalu (shutdown / no shutdown)", "ont_disable": "ONT band (deactivate)",
    "ont_enable": "ONT chalu (activate)", "uplink_reset": "Uplink port band karke chalu", "custom": "Apni command",
}
_ACTION_RISK = {
    "reboot_ont": "Sirf us customer ka net 2-3 minute jaayega.",
    "pon_reset": "Us PON ke SAARE customers ka net 2-5 minute jaayega.",
    "ont_disable": "Us customer ka net tab tak band jab tak wapas chalu na karein.",
    "ont_enable": "Us customer ka ONT chalu hoga.",
    "uplink_reset": "Is OLT ke SAARE customers ka net kuch minute jaayega; galat port chuna to OLT tak pahunch bhi ja sakti hai.",
    "custom": "Command aapki likhi hai: kya badlega yeh aap hi jaanti hain.",
}
# Commands per make. Huawei / ZTE follow their published CLI manuals; Syrotech / VSOL / C-Data / BDCOM manuals are not public,
# so their lines are STARTERS (verified=False): the card says to match them with her OLT's own manual / Telnet help before Haan.
VENDOR_CMDS: dict[str, dict[str, Any]] = {
    "huawei": {"verified": True,
               "reboot_ont": (["config", "interface gpon {f}/{s}", "ont reset {p} {onu}", "quit"], []),
               "ont_disable": (["config", "interface gpon {f}/{s}", "ont deactivate {p} {onu}", "quit"],
                               ["config", "interface gpon {f}/{s}", "ont activate {p} {onu}", "quit"]),
               "ont_enable": (["config", "interface gpon {f}/{s}", "ont activate {p} {onu}", "quit"],
                              ["config", "interface gpon {f}/{s}", "ont deactivate {p} {onu}", "quit"]),
               "pon_reset": (["config", "interface gpon {f}/{s}", "shutdown {p}", "undo shutdown {p}", "quit"], ["config", "interface gpon {f}/{s}", "undo shutdown {p}", "quit"]),
               "uplink_reset": (["config", "interface giu {f}/{s}", "shutdown {p}", "undo shutdown {p}", "quit"], ["config", "interface giu {f}/{s}", "undo shutdown {p}", "quit"])},
    "zte": {"verified": True,
            "reboot_ont": (["pon-onu-mng gpon-onu_{pon}:{onu}", "reboot", "exit"], []),
            "ont_disable": (["configure terminal", "interface gpon-onu_{pon}:{onu}", "shutdown", "end"], ["configure terminal", "interface gpon-onu_{pon}:{onu}", "no shutdown", "end"]),
            "ont_enable": (["configure terminal", "interface gpon-onu_{pon}:{onu}", "no shutdown", "end"], ["configure terminal", "interface gpon-onu_{pon}:{onu}", "shutdown", "end"]),
            "pon_reset": (["configure terminal", "interface gpon-olt_{pon}", "shutdown", "no shutdown", "end"], ["configure terminal", "interface gpon-olt_{pon}", "no shutdown", "end"]),
            "uplink_reset": (["configure terminal", "interface {port}", "shutdown", "no shutdown", "end"], ["configure terminal", "interface {port}", "no shutdown", "end"])},
}
_GENERIC = {"verified": False,
            "reboot_ont": (["configure terminal", "interface {tech} 0/{p}", "onu reboot {onu}", "exit"], []),
            "ont_disable": (["configure terminal", "interface {tech} 0/{p}", "onu {onu} deactivate", "exit"], ["configure terminal", "interface {tech} 0/{p}", "onu {onu} activate", "exit"]),
            "ont_enable": (["configure terminal", "interface {tech} 0/{p}", "onu {onu} activate", "exit"], ["configure terminal", "interface {tech} 0/{p}", "onu {onu} deactivate", "exit"]),
            "pon_reset": (["configure terminal", "interface {tech} 0/{p}", "shutdown", "no shutdown", "exit"], ["configure terminal", "interface {tech} 0/{p}", "no shutdown", "exit"]),
            "uplink_reset": (["configure terminal", "interface {port}", "shutdown", "no shutdown", "exit"], ["configure terminal", "interface {port}", "no shutdown", "exit"])}
for _m in ("syrotech", "vsol", "cdata", "bdcom", "other", ""):
    VENDOR_CMDS.setdefault(_m, _GENERIC)
READ_ONLY = re.compile(r"^\s*(show|display|get|ping|traceroute)\b", re.I)
FORBIDDEN = re.compile(r"(?i)\b(password|passwd|username|user\s+\S+\s+password|enable secret|community|erase|format|delete|"
                       r"reload|reboot system|write erase|factory|reset saved|upgrade|load|copy)\b")
FORBIDDEN_OK_LINE = re.compile(r"(?i)^\s*(onu reboot \d+|ont reset \d+ \d+|reboot)\s*$")


def commands_for(make: str, action: str, tech: str = "gpon", pon: str = "", onu: str = "", port: str = "") -> dict:
    vend = VENDOR_CMDS.get((make or "").lower(), _GENERIC)
    if action not in vend:
        return {"commands": [], "rollback": [], "verified": False}
    parts = (norm_pon(pon) or "0").split("/")
    f, s, p = (["0"] * (3 - len(parts)) + parts)[-3:] if len(parts) <= 3 else parts[:3]
    vals = {"f": f, "s": s, "p": p, "onu": onu or "?", "pon": norm_pon(pon), "port": port or "?", "tech": (tech or "gpon").lower()}
    cmds, back = vend[action]
    return {"commands": [c.format(**vals) for c in cmds], "rollback": [c.format(**vals) for c in back], "verified": bool(vend["verified"])}


def command_problems(cmds: list[str]) -> list[str]:
    """Lines that must never go through Hoola (passwords, erase / reload / firmware / copy)."""
    probs = []
    for c in cmds:
        if FORBIDDEN.search(c) and not FORBIDDEN_OK_LINE.match(c):
            probs.append(c.strip()[:80])
    return probs


def risk_of(action: str, n: int) -> str:
    return f"{_ACTION_RISK.get(action, '')} Asar: {n} customer." if n else _ACTION_RISK.get(action, "")


# ---------------------------------------------------------------- regulation facts (cited in the app + tool)
RULES_FACTS = {
    "trai_qos_2024": "TRAI Standards of QoS of Access (Wireline and Wireless) and Broadband (Wireline and Wireless) Regulations, 2024 "
                     "(notified 2 Aug 2024, in force 1 Oct 2024). TRAI's draft amendment (Consultation Paper 5 Aug 2026) proposes for "
                     "wireline broadband: MTTR <= 10 hours (quarterly), fault incidence <= 5 per 100 subscribers a month, Significant "
                     "Network Outage = a district down > 4 continuous hours or > 10% of subscribers in a service area > 4 h, reported to "
                     "TRAI within 24 h with root cause after restoration, rent rebate / validity extension for outages > 24 h (> 12 h in a "
                     "day = a full day). Draft only until TRAI notifies it.",
    "telecom_cyber_2024": "Telecommunications (Telecom Cyber Security) Rules, 2024 (DoT, 21 Nov 2024): a telecommunication entity "
                          "reports a security incident within 6 hours of becoming aware, more details within 24 hours. For a BSNL "
                          "franchise / TIP, BSNL is the licensee: tell BSNL at once.",
    "bsnl_franchise": "BSNL Bharat Fiber franchise SLA hours and penalties come from HER agreement with BSNL; Hoola uses the hours she "
                      "enters, never a guessed number.",
    "trai_2006": "TRAI broadband QoS (2006): fault repair by the next working day was the old benchmark.",
}
SOURCES = [
    ("TRAI Consultation Paper on QoS amendments (5 Aug 2026)", "https://www.trai.gov.in/sites/default/files/2026-08/CP_05082026.pdf"),
    ("Corpseed summary of the TRAI QoS consultation (Aug-Sep 2026)", "https://www.corpseed.com/law-update/trai-qos-consultation-paper-comments-deadline-2026"),
    ("Khaitan & Co: Telecom Cyber Security Rules 2024 finalised (29 Nov 2024)", "https://khaitanco.com/thought-leadership/Telecom-Cyber-Security-Rules-2024-Finalized"),
    ("FS community: PON module parameters (GPON B+/C+, EPON PX20)", "https://community.fs.com/article/pon-module-parameters-guide-how-to-choose-the-best-gpon-epon-modules.html"),
]


def parse_when(text: str, base: datetime, tz) -> datetime | None:
    """ETA from her words: '2 ghante', '30 min', 'shaam 6 baje', '6 pm', '18:30', 'kal 11 baje', ISO."""
    t = str(text or "").strip().lower()
    if not t:
        return None
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})[ t](\d{1,2}):(\d{2})", t)
    if m:
        d = date.fromisoformat(m.group(1))
        return datetime(d.year, d.month, d.day, int(m.group(2)), int(m.group(3)), tzinfo=tz)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ghante|ghanta|hours?|hrs?|h)\b", t)
    if m:
        return base + timedelta(hours=float(m.group(1)))
    m = re.search(r"(\d+)\s*(min(?:ute)?s?|mins?)\b", t)
    if m:
        return base + timedelta(minutes=int(m.group(1)))
    loc = base.astimezone(tz)
    day = loc.date() + (timedelta(days=1) if re.search(r"\bkal\b|tomorrow", t) else timedelta(0))
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|baje)?", t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        ap = m.group(3) or ""
        if ap == "pm" and h < 12 or (ap == "baje" and re.search(r"shaam|raat|dopahar|evening|night", t) and h < 12):
            h += 12
        elif ap == "baje" and h < 7 and not re.search(r"subah|morning", t):
            h += 12
        if h > 23 or mi > 59:
            return None
        out = datetime(day.year, day.month, day.day, h, mi, tzinfo=tz)
        if out < base and not re.search(r"\bkal\b|tomorrow", t):
            out += timedelta(days=1)
        return out
    return None
