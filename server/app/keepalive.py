"""v0.49 "Hoola band na ho": per phone-maker steps from dontkillmyapp.com (CC BY 4.0, credit shown in the app)
so Xiaomi / Oppo / Vivo / Realme / Samsung ... battery savers don't stop Hoola's background service and push.

steps(brand) -> {vendor, name, rank, steps: [..plain lines..], source, credit}   (cached 7 days in data/keepalive)
"""
from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path
from typing import Any

CACHE = Path("data") / "keepalive"
URL = "https://dontkillmyapp.com/api/v2/{vendor}.json"
CREDIT = "dontkillmyapp.com (CC BY 4.0)"
ALIASES = {"redmi": "xiaomi", "poco": "xiaomi", "mi": "xiaomi", "iqoo": "vivo", "realme": "realme", "oneplus": "oneplus",
           "oppo": "oppo", "vivo": "vivo", "samsung": "samsung", "huawei": "huawei", "honor": "huawei", "asus": "asus",
           "nokia": "nokia", "hmd global": "nokia", "motorola": "motorola", "lenovo": "lenovo", "sony": "sony",
           "google": "google", "meizu": "meizu", "tecno": "tecno", "infinix": "tecno", "itel": "tecno", "lava": "",
           "micromax": "", "xiaomi": "xiaomi", "blackview": "blackview", "wiko": "wiko", "htc": "htc", "lg": "lg",
           "nothing": "nothing", "zte": "zte", "unihertz": "unihertz"}
_transport = None   # tests


def vendor_for(brand: str) -> str:
    b = (brand or "").strip().lower()
    for k, v in ALIASES.items():
        if b == k or b.startswith(k):
            return v
    return re.sub(r"[^a-z0-9-]", "", b)[:30]


def _text(h: str) -> list[str]:
    h = re.sub(r"(?is)<(script|style).*?</\1>", "", h or "")
    h = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>", "\n", h)
    h = re.sub(r"(?i)<li[^>]*>", "• ", h)
    t = html.unescape(re.sub(r"<[^>]+>", "", h))
    lines = [re.sub(r"\s+", " ", x).strip() for x in t.split("\n")]
    return [x for x in lines if len(x) > 2][:40]


def steps(brand: str) -> dict[str, Any]:
    vendor = vendor_for(brand)
    if not vendor:
        return {"vendor": "", "steps": [], "credit": CREDIT}
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{vendor}.json"
    raw = None
    if f.exists() and time.time() - f.stat().st_mtime < 7 * 86400:
        raw = json.loads(f.read_text())
    if raw is None:
        import httpx
        try:
            with httpx.Client(timeout=15, transport=_transport, follow_redirects=True) as c:
                r = c.get(URL.format(vendor=vendor), headers={"User-Agent": "Hoola/0.49 (+dontkillmyapp credit)"})
            raw = r.json() if r.status_code == 200 else {}
        except Exception:
            raw = {}
        if raw:
            f.write_text(json.dumps(raw))
        elif f.exists():
            raw = json.loads(f.read_text())       # stale is better than nothing
    if not raw:
        return {"vendor": vendor, "steps": [], "credit": CREDIT}
    return {"vendor": vendor, "name": raw.get("name") or vendor.title(), "rank": raw.get("award"),
            "steps": _text(raw.get("user_solution") or ""), "why": _text(raw.get("explanation") or "")[:4],
            "source": f"https://dontkillmyapp.com/{vendor}", "credit": CREDIT}


# ---------------- v0.56 "Hoola band na ho": a checklist per phone family + a health check from the phone ----------------
# The phone sends what Android itself knows (battery optimisation, "background restricted", standby bucket, and the
# last process exits from ActivityManager.getHistoricalProcessExitReasons); the server turns that into plain-word
# problems and a checklist where every line opens the right settings page. Only settings pages are opened (Play policy:
# no REQUEST_IGNORE_BATTERY_OPTIMIZATIONS); the owner flips the switch herself.

# family -> list of (id, title, how, action). action = what the app opens: autostart | battery | maker_battery |
# maker_perms | notifications | app_info | recents (manual: lock in recent apps) | none
_COMMON_TAIL = [
    ("notifications", "Notifications ON", "Hoola ki saari notifications allow rakhiye (warna jawab aur call ki ghanti nahi aayegi).", "notifications"),
]
CHECKLISTS: dict[str, list[tuple[str, str, str, str]]] = {
    "xiaomi": [
        ("autostart", "Autostart ON", "Settings → Apps → Manage apps → Hoola → Autostart: ON", "autostart"),
        ("battery", "Battery saver: No restrictions", "Settings → Apps → Manage apps → Hoola → Battery saver → \"No restrictions\"", "maker_battery"),
        ("perms", "Lock screen par dikhana + background popup", "Hoola → Other permissions → \"Show on Lock screen\" aur \"Display pop-up windows while running in the background\": Allow", "maker_perms"),
        ("recents", "Recent apps mein lock", "Recent apps kholiye → Hoola ke card ko neeche kheenchiye / dabake rakhiye → 🔒 Lock", "recents"),
    ],
    "oppo": [
        ("battery", "Background activity allow", "Settings → Battery → App battery management → Hoola → \"Allow background activity\" ON (aur \"Allow foreground activity\")", "maker_battery"),
        ("autostart", "Auto launch ON", "Settings → Apps → App management → Hoola → \"Allow auto launch\" / Auto startup: ON", "autostart"),
        ("recents", "Recent apps mein lock", "Recent apps → Hoola ke upar ⋮ → Lock", "recents"),
    ],
    "vivo": [
        ("battery", "High background power allow", "Settings → Battery → Background power consumption management → Hoola → \"Allow\"", "maker_battery"),
        ("autostart", "Autostart ON", "i Manager → App manager → Autostart manager → Hoola: ON  (ya Settings → Apps → Hoola → Autostart)", "autostart"),
        ("recents", "Recent apps mein lock", "Recent apps → Hoola ke card ko neeche kheench kar 🔒 lock", "recents"),
    ],
    "samsung": [
        ("battery", "Battery: Unrestricted", "Settings → Apps → Hoola → Battery → \"Unrestricted\"", "battery"),
        ("never_sleep", "Never sleeping apps", "Settings → Battery → Background usage limits → \"Never sleeping apps\" → + Hoola  (aur \"Put unused apps to sleep\" mein Hoola na ho)", "maker_battery"),
    ],
    "huawei": [
        ("battery", "App launch: Manage manually", "Settings → Battery → App launch → Hoola → OFF karke teeno (Auto-launch, Secondary launch, Run in background) ON", "autostart"),
        ("recents", "Recent apps mein lock", "Recent apps → Hoola ko neeche kheench kar lock", "recents"),
    ],
    "oneplus": [
        ("battery", "Battery optimisation: Don't optimise", "Settings → Battery → Battery optimisation → Hoola → \"Don't optimise\"  (OxygenOS 13+: App battery management → Allow background activity)", "battery"),
        ("autostart", "Auto launch ON", "Settings → Apps → Hoola → \"Auto launch\" ON", "autostart"),
        ("recents", "Recent apps mein lock", "Recent apps → Hoola ke upar ⋮ → Lock", "recents"),
    ],
    "tecno": [
        ("battery", "Phone Master: Hoola ko protect karein", "Phone Master → App protection / Auto-start management → Hoola: ON", "autostart"),
        ("battery_opt", "Battery: Unrestricted", "Settings → Apps → Hoola → Battery → Unrestricted", "battery"),
        ("recents", "Recent apps mein lock", "Recent apps → Hoola ko lock", "recents"),
    ],
    "generic": [
        ("battery", "Battery: Unrestricted", "Settings → Apps → Hoola → Battery → \"Unrestricted\" / \"Don't optimise\"", "battery"),
    ],
}
FAMILY = {"xiaomi": "xiaomi", "oppo": "oppo", "realme": "oppo", "oneplus": "oneplus", "vivo": "vivo", "samsung": "samsung",
          "huawei": "huawei", "tecno": "tecno"}
STRICT = {"xiaomi", "oppo", "vivo", "huawei", "oneplus", "tecno", "samsung"}


def family(brand: str) -> str:
    return FAMILY.get(vendor_for(brand), "generic")


def checklist(brand: str) -> list[dict[str, str]]:
    fam = family(brand)
    items = CHECKLISTS[fam] + _COMMON_TAIL
    return [{"id": i, "title": t, "how": h, "action": a} for i, t, h, a in items]


# ApplicationExitInfo reasons (Android 11+)
R_UNKNOWN, R_EXIT_SELF, R_SIGNALED, R_LOW_MEMORY, R_CRASH, R_CRASH_NATIVE, R_ANR = 0, 1, 2, 3, 4, 5, 6
R_PERMISSION_CHANGE, R_EXCESSIVE, R_USER_REQUESTED, R_USER_STOPPED, R_OTHER, R_FREEZER = 8, 9, 10, 11, 13, 14
R_PACKAGE_STATE, R_PACKAGE_UPDATED = 15, 16
IMPORTANCE_FOREGROUND_SERVICE = 125
_CLEAN_WORDS = re.compile(r"(?i)swipe|clean|remove ?task|onekey|one key|recent|clear|kill ?background|force-?stop by")


def classify_exit(e: dict[str, Any]) -> str:
    """One process exit -> oem_kill | recents_clear | low_memory | crash | user | update | normal."""
    r = int(e.get("reason") or 0)
    desc = str(e.get("desc") or "")
    imp = int(e.get("importance") or 1000)
    if r in (R_CRASH, R_CRASH_NATIVE, R_ANR):
        return "crash"
    if r in (R_PACKAGE_UPDATED, R_PACKAGE_STATE, R_PERMISSION_CHANGE):
        return "update"
    if r == R_EXIT_SELF:
        return "normal"
    if r == R_LOW_MEMORY:
        return "low_memory"
    if r in (R_USER_REQUESTED, R_USER_STOPPED):
        return "recents_clear" if _CLEAN_WORDS.search(desc) else "user"
    if r in (R_SIGNALED, R_OTHER, R_EXCESSIVE, R_FREEZER, R_UNKNOWN):
        if _CLEAN_WORDS.search(desc) and r != R_EXCESSIVE:
            return "recents_clear"
        # killed while it was only working in the background (not the screen the owner was using)
        return "oem_kill" if imp > IMPORTANCE_FOREGROUND_SERVICE or r in (R_EXCESSIVE, R_FREEZER) else "normal"
    return "normal"


def health(report: dict[str, Any], now_ms: int | None = None) -> dict[str, Any]:
    """The phone's own facts -> {ok, problems:[{code,title,fix,action}], counts, family, checklist}."""
    now_ms = now_ms or int(time.time() * 1000)
    brand = str(report.get("brand") or "")
    fam = family(brand)
    week = now_ms - 7 * 86400_000
    counts: dict[str, int] = {}
    last_kill = 0
    for e in (report.get("exits") or [])[:50]:
        if not isinstance(e, dict) or int(e.get("ts") or 0) < week:
            continue
        c = classify_exit(e)
        counts[c] = counts.get(c, 0) + 1
        if c in ("oem_kill", "recents_clear"):
            last_kill = max(last_kill, int(e.get("ts") or 0))
    probs: list[dict[str, str]] = []

    def add(code: str, title: str, fix: str, action: str) -> None:
        probs.append({"code": code, "title": title, "fix": fix, "action": action})

    if report.get("notifications") is False:
        add("notifications_off", "Notifications band hain", "Bina notifications ke jawab aur call ki ghanti nahi aayegi.", "notifications")
    if report.get("background_restricted"):
        add("bg_restricted", "Background mein chalna mana hai", "Android ne Hoola par \"Restricted\" laga rakha hai: Battery → Unrestricted kijiye.", "battery")
    if report.get("battery_optimized") and (fam in STRICT or counts.get("oem_kill")):
        add("battery_optimized", "Battery saver Hoola ko rok raha hai", "Hoola ko \"Unrestricted / Don't optimise\" par rakhiye.", "maker_battery" if fam != "generic" else "battery")
    bucket = int(report.get("standby_bucket") or 0)
    if bucket >= 45:
        add("standby_restricted", "Phone ne Hoola ko 'Restricted' bucket mein daala", "Hoola ko roz kholiye aur Battery → Unrestricted kijiye.", "battery")
    if counts.get("oem_kill"):
        n = counts["oem_kill"]
        add("oem_kills", f"Phone ne {n} baar Hoola ko background mein band kiya (7 din)",
            "Autostart ON aur battery 'No restrictions' kar dijiye — tab yeh rukega.", "autostart" if fam != "generic" else "battery")
    if counts.get("recents_clear"):
        add("recents_clear", "Recent apps saaf karne par Hoola band ho jaata hai",
            "Recent apps mein Hoola ke card ko 🔒 lock kar dijiye.", "recents")
    if counts.get("low_memory", 0) >= 3:
        add("low_memory", "Phone ki memory bhar jaati hai", "Kuch bhaari apps band rakhiye; Hoola memory kam hone par ruk jaata hai.", "none")
    if counts.get("crash", 0) >= 2:
        add("crashes", "Hoola khud do baar ruka (crash)", "Yeh hamari galti hai — app update rakhiye; report hamein mil gayi.", "none")
    return {"ok": not probs, "problems": probs, "counts": counts, "last_kill": last_kill, "family": fam,
            "strict": fam in STRICT, "checklist": checklist(brand), "vendor": vendor_for(brand)}


HEALTH_DIR = CACHE / "health"


def save_health(tenant: str, report: dict[str, Any]) -> dict[str, Any]:
    """Checks the phone's report and keeps the latest one (so the avatar can explain a missed reminder)."""
    out = health(report)
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w-]", "_", tenant)[:64] or "default"
    keep = {"at": int(time.time()), "brand": str(report.get("brand") or "")[:40], "model": str(report.get("model") or "")[:60],
            "sdk": report.get("sdk"), **{k: out[k] for k in ("ok", "problems", "counts", "last_kill", "family")}}
    (HEALTH_DIR / f"{safe}.json").write_text(json.dumps(keep))
    return out


def last_health(tenant: str) -> dict[str, Any]:
    safe = re.sub(r"[^\w-]", "_", tenant)[:64] or "default"
    f = HEALTH_DIR / f"{safe}.json"
    try:
        return json.loads(f.read_text())
    except Exception:
        return {}
