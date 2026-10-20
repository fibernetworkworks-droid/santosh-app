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
