"""Hoola TV channel list, built from the open iptv-org lists (public domain), keeping ONLY legitimate free streams.

iptv-org collects links to live streams from all over the web; many Indian entries are unofficial re-broadcasts of pay
channels. Hoola keeps a stream only when it comes from the broadcaster's own servers or an official free distributor:

  * Prasar Bharati (Doordarshan / WAVES) and Sansad TV (NIC) servers,
  * official free ad-supported platforms: Samsung TV Plus, Amagi playout, Wurl, Distro TV,
  * a CDN host named after the channel / its owner (e.g. ndtvprofit.akamaized.net, vg-zeefta.akamaized.net).

Always dropped: bare IP addresses, plain http, re-streaming aggregators and proxies, OTT-app feeds (YuppTV, Airtel,
JioTV...), anything on iptv-org's copyright/NSFW blocklist, closed channels, and channels outside India.
A nightly check keeps only streams that actually answer, and notes which ones a TV (Chromecast) can play.
"""
from __future__ import annotations

import csv
import io
import ipaddress
import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

log = logging.getLogger("santosh.tv")

RAW = "https://raw.githubusercontent.com/iptv-org"
STREAM_FILES = ["in.m3u", "in_doordarshan.m3u", "in_samsung.m3u", "in_distro.m3u"]
DB_FILES = ["channels.csv", "blocklist.csv", "logos.csv"]
TRUSTED_FILES = {"in_doordarshan.m3u", "in_samsung.m3u", "in_distro.m3u"}

# Prasar Bharati (DD / WAVES) and Sansad TV (NIC) delivery hosts
OFFICIAL_HOSTS = {"d3qs3d2rkhfqrt.cloudfront.net", "d2lk5u59tns74c.cloudfront.net", "playhls.media.nic.in"}
# official free ad-supported (FAST) platforms
OFFICIAL_PLATFORMS = re.compile(r"(\.amagi\.tv|\.wurl\.tv|\.wurl\.com|\.samsungtv\.plus|distrotv)$|distrotv", re.I)
# re-streamers, proxies, OTT-app feeds, free-DNS and other places a broadcaster would not publish its own stream
NOT_OFFICIAL = re.compile(
    r"(tangotv|smartplaytv|aynaott|aynascope|pishow|yupp|airtel|jiotv|jiocinema|githubusercontent|workers\.dev|proxy|"
    r"ottlive|streamlock|nellai|xtream|iptv|dpdns|inet\.moe|applelive|duckdns|ngrok|herokuapp|blogspot|pages\.dev|"
    r"netlify|vercel)", re.I)
STOP = {"the", "news", "media", "network", "limited", "ltd", "private", "pvt", "india", "channel", "live", "corporation",
        "group", "www", "com", "broadcast", "broadcasting", "entertainment", "television", "digital", "services", "tv",
        "hd", "and", "net", "org"}

DATA_DIR = Path("data") / "tv"
SEED = Path(__file__).parent / "channels_seed.json"
CATEGORY_HI = {
    "news": "News", "entertainment": "Manoranjan", "movies": "Filmein", "music": "Gaane", "religious": "Bhakti",
    "kids": "Bachche", "sports": "Khel", "general": "Sab ke liye", "business": "Business", "documentary": "Documentary",
    "legislative": "Sansad", "education": "Padhai", "culture": "Sanskriti", "comedy": "Comedy", "lifestyle": "Lifestyle",
    "travel": "Safar", "classic": "Purane", "family": "Parivar", "weather": "Mausam", "outdoor": "Kheti / Bahar",
}
# words people say -> category
SAY = {"khabar": "news", "samachar": "news", "news": "news", "bhajan": "religious", "bhakti": "religious",
       "aastha": "religious", "dharmik": "religious", "gaane": "music", "gana": "music", "music": "music",
       "film": "movies", "movie": "movies", "picture": "movies", "cartoon": "kids", "bachche": "kids", "kids": "kids",
       "khel": "sports", "sports": "sports", "cricket": "sports", "kheti": "education", "kisan": "education",
       "comedy": "comedy", "sansad": "legislative", "parliament": "legislative", "business": "business",
       "share": "business", "market": "business"}
# Doordarshan regional channels by the language people ask for
LANG_DD = {"marathi": "DD Sahyadri", "tamil": "DD Tamil", "telugu": "DD Saptagiri", "kannada": "DD Chandana",
           "malayalam": "DD Malayalam", "bangla": "DD Bangla", "bengali": "DD Bangla", "gujarati": "DD Girnar",
           "odia": "DD Odia", "punjabi": "DD Punjabi", "urdu": "DD Urdu", "assamese": "DD Assam", "kashmiri": "DD Kashir"}


# ----------------------------------------------------------------------------- building
def parse_m3u(text: str, file: str) -> list[dict]:
    out, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("#EXTINF"):
            continue
        m = re.search(r'tvg-id="([^"]*)"', line)
        title = line.split(",", 1)[1].strip() if "," in line else ""
        opts, j = [], i + 1
        while j < len(lines) and lines[j].startswith("#"):
            opts.append(lines[j])
            j += 1
        if j >= len(lines):
            continue
        ua = ref = ""
        for o in opts:
            if o.startswith("#EXTVLCOPT:http-user-agent="):
                ua = o.split("=", 1)[1].strip()
            if o.startswith("#EXTVLCOPT:http-referrer="):
                ref = o.split("=", 1)[1].strip()
        q = re.search(r"\((\d{3,4})[pi]\)", title)
        out.append({"tvg": (m.group(1) if m else "").split("@")[0], "title": title, "url": lines[j].strip(), "file": file,
                    "quality": int(q.group(1)) if q else 0, "geo": "[Geo-blocked]" in title,
                    "not247": "[Not 24/7]" in title, "user_agent": ua, "referrer": ref})
    return out


def clean_title(t: str) -> str:
    t = re.sub(r"\[[^\]]*\]", "", t)
    t = re.sub(r"\(\d{3,4}[pi]\)", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _tokens(ch: dict, title: str) -> set[str]:
    out = set()
    for s in (ch.get("network", ""), ch.get("owners", ""), ch.get("name", ""), title, urlparse(ch.get("website", "")).hostname or ""):
        for w in re.findall(r"[a-z0-9]{3,}", (s or "").lower()):
            if w not in STOP:
                out.add(w)
    return out


def official(stream: dict, ch: dict) -> tuple[bool, str]:
    """Is this stream the broadcaster's own / an official free distributor's? (ok, reason)"""
    url = stream["url"]
    host = (urlparse(url).hostname or "").lower()
    if not url.startswith("https://") or not host:
        return False, "not https"
    try:
        ipaddress.ip_address(host)
        return False, "bare ip"
    except ValueError:
        pass
    if NOT_OFFICIAL.search(host):
        return False, "re-streamer / app feed"
    if host in OFFICIAL_HOSTS:
        return True, "prasar bharati / nic"
    if OFFICIAL_PLATFORMS.search(host) or stream["file"] in TRUSTED_FILES:
        return True, "official free platform"
    flat = re.sub(r"[^a-z0-9]", "", host)
    if any(t in flat for t in _tokens(ch, stream["title"])):
        return True, "broadcaster's own cdn"
    return False, "unknown host"


def build(m3u: dict[str, str], channels_csv: str, blocklist_csv: str, logos_csv: str) -> list[dict]:
    chans = {r["id"]: r for r in csv.DictReader(io.StringIO(channels_csv))}
    blocked = {r["channel"] for r in csv.DictReader(io.StringIO(blocklist_csv))}
    logos: dict[str, tuple[int, str]] = {}
    for r in csv.DictReader(io.StringIO(logos_csv)):
        url = r.get("url", "")
        if not url.startswith("https://") or r.get("format", "").upper() not in ("PNG", "JPEG", "JPG", "WEBP", ""):
            continue
        try:
            w = int(r.get("width") or 0)
        except ValueError:
            w = 0
        score = (1000 if r.get("in_use", "").upper() == "TRUE" else 0) + min(w, 512)
        if r["channel"] not in logos or score > logos[r["channel"]][0]:
            logos[r["channel"]] = (score, url)
    by: dict[str, dict] = {}
    for file, text in m3u.items():
        for s in parse_m3u(text, file):
            ch = chans.get(s["tvg"], {})
            cid = s["tvg"] or re.sub(r"[^a-z0-9]+", "-", clean_title(s["title"]).lower()).strip("-")
            if not cid or cid in blocked or ch.get("is_nsfw", "").upper() == "TRUE" or ch.get("closed"):
                continue
            if ch and ch.get("country") != "IN":
                continue
            ok, why = official(s, ch)
            if not ok:
                continue
            c = by.setdefault(cid, {
                "id": cid, "name": ch.get("name") or clean_title(s["title"]),
                "categories": [x for x in (ch.get("categories") or "").split(";") if x] or ["general"],
                "network": ch.get("network", ""), "website": ch.get("website", ""),
                "logo_src": logos.get(cid, (0, ""))[1], "streams": []})
            c["streams"].append({"url": s["url"], "quality": s["quality"], "geo": s["geo"], "not247": s["not247"],
                                 "user_agent": s["user_agent"], "referrer": s["referrer"], "source": why})
    out = []
    for c in by.values():
        # best first: always-on, not geo-blocked, no special headers (a TV can play it), then quality
        c["streams"].sort(key=lambda x: (x["not247"], x["geo"], bool(x["user_agent"] or x["referrer"]), -x["quality"]))
        c["streams"] = c["streams"][:3]
        out.append(c)
    return sorted(out, key=lambda c: c["name"].lower())


def fetch_sources(client=None) -> tuple[dict[str, str], str, str, str]:
    import httpx
    own = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=True)
    try:
        m3u = {}
        for f in STREAM_FILES:
            r = client.get(f"{RAW}/iptv/master/streams/{f}")
            r.raise_for_status()
            m3u[f] = r.text
        db = []
        for f in DB_FILES:
            r = client.get(f"{RAW}/database/master/data/{f}")
            r.raise_for_status()
            db.append(r.text)
        return m3u, db[0], db[1], db[2]
    finally:
        if own:
            client.close()


# ----------------------------------------------------------------------------- health
def check_stream(client, st: dict) -> tuple[bool, bool]:
    """(answers, a TV can play it). A Chromecast plays HLS only when the server allows other sites (CORS)."""
    headers = {"Origin": "https://www.gstatic.com"}
    if st.get("user_agent"):
        headers["User-Agent"] = st["user_agent"]
    if st.get("referrer"):
        headers["Referer"] = st["referrer"]
    try:
        r = client.get(st["url"], headers=headers)
    except Exception:
        return False, False
    if r.status_code != 200 or "#EXTM3U" not in r.text[:2000]:
        return False, False
    acao = r.headers.get("access-control-allow-origin", "")
    castable = (acao == "*" or "gstatic" in acao) and not st.get("user_agent") and not st.get("referrer")
    return True, castable


def health(channels: list[dict], client=None, workers: int = 12) -> list[dict]:
    import concurrent.futures as cf

    import httpx
    own = client is None
    client = client or httpx.Client(timeout=8, follow_redirects=True)
    try:
        jobs = [(c, s) for c in channels for s in c["streams"]]
        with cf.ThreadPoolExecutor(workers) as pool:
            for (c, s), (ok, cast) in zip(jobs, pool.map(lambda j: check_stream(client, j[1]), jobs)):
                s["ok"], s["castable"] = ok, cast
    finally:
        if own:
            client.close()
    for c in channels:
        c["streams"].sort(key=lambda x: (not x.get("ok", True), x["not247"], x["geo"], not x.get("castable", False), -x["quality"]))
    return channels


# ----------------------------------------------------------------------------- the list in use
_lock = threading.Lock()
_cache: dict[str, Any] = {"at": 0.0, "data": None}


def _file() -> Path:
    return DATA_DIR / "channels.json"


def load() -> dict:
    """{'updated': ts, 'channels': [...]} from the last refresh, else the list shipped with Hoola."""
    with _lock:
        if _cache["data"] is not None and time.time() - _cache["at"] < 300:
            return _cache["data"]
        data = None
        for f in (_file(), SEED):
            try:
                data = json.loads(f.read_text())
                break
            except (OSError, ValueError):
                continue
        data = data or {"updated": 0, "channels": []}
        _cache.update(at=time.time(), data=data)
        return data


def refresh(client=None, check=True) -> dict:
    """Download the lists, keep the official free streams, check them, save. Returns counts."""
    m3u, chans, blocked, logos = fetch_sources(client)
    channels = build(m3u, chans, blocked, logos)
    if check:
        channels = health(channels)
    data = {"updated": time.time(), "channels": channels}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _file().with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False))
    tmp.replace(_file())
    with _lock:
        _cache.update(at=time.time(), data=data)
    working = sum(1 for c in channels if any(s.get("ok", True) for s in c["streams"]))
    log.info("tv list refreshed: %s channels, %s working", len(channels), working)
    return {"channels": len(channels), "working": working}


_bg = False


def refresh_in_background(every_s: float = 24 * 3600) -> None:
    """Nightly: download the lists again and check which channels work (a daemon thread)."""
    global _bg
    if _bg:
        return
    _bg = True

    def go():
        time.sleep(60)
        while True:
            try:
                refresh()
            except Exception:
                log.exception("tv list refresh failed; keeping the last good list")
            time.sleep(every_s)
    threading.Thread(target=go, daemon=True, name="tv-refresh").start()


# ----------------------------------------------------------------------------- reading
def _usable(c: dict) -> bool:
    return any(s.get("ok", True) for s in c["streams"])


def view(c: dict) -> dict:
    best = c["streams"][0]
    return {"id": c["id"], "name": c["name"], "category": c["categories"][0],
            "category_label": CATEGORY_HI.get(c["categories"][0], c["categories"][0].title()),
            "logo": f"/api/logo/tv/{c['id']}" if c.get("logo_src") else None, "quality": best["quality"],
            "on_tv": any(s.get("castable") for s in c["streams"]), "geo": best["geo"], "not247": best["not247"],
            "ok": _usable(c)}


def get(cid: str) -> dict | None:
    return next((c for c in load()["channels"] if c["id"] == cid), None)


GENERIC = {"plus", "hd", "tv", "india", "indian", "digital", "one", "max", "gold", "bharat", "network", "channel",
           "24x7", "24", "7", "the", "new", "star", "times"}


def find(query: str = "", category: str = "", limit: int = 60) -> list[dict]:
    chans = [c for c in load()["channels"] if _usable(c)]
    q = (query or "").lower().strip()
    cat = category if category in CATEGORY_HI else ""
    words = re.findall(r"[a-z0-9]+", q)
    for w in words:
        if not cat and w in SAY:
            cat = SAY[w]
        if w in LANG_DD:
            q = q.replace(w, LANG_DD[w].lower())
    if cat:
        chans = [c for c in chans if cat in c["categories"]]
    filler = {"channel", "lagao", "chalao", "dikhao", "live", "pe", "par", "ka", "ki", "ke", "chahiye", "dekhna"}
    words = [w for w in re.findall(r"[a-z0-9]+", q) if w not in filler]
    keys = [w for w in words if w not in SAY and w not in GENERIC]
    if not [w for w in words if w not in SAY]:
        return [view(c) for c in chans[:limit]]

    def score(c: dict) -> float:
        name = c["name"].lower()
        flat = re.sub(r"[^a-z0-9]", "", name)
        s = 0.0
        if " ".join(words) == name:
            s += 10
        hit, key_hit = 0, False
        for w in words:
            if re.search(rf"\b{re.escape(w)}", name):
                s += 3
            elif w in flat:
                s += 1.5
            else:
                continue
            hit += 1
            key_hit = key_hit or w in keys
        # "star plus" must not land on "Raj Digital Plus": a filler word alone is no match
        if keys and not key_hit:
            return 0.0
        if hit * 2 < len(words) or (not keys and hit < len(words)):
            return 0.0
        return s
    ranked = sorted(((score(c), c) for c in chans), key=lambda t: (-t[0], t[1]["name"]))
    return [view(c) for s, c in ranked if s > 0][:limit]


def categories() -> list[dict]:
    seen: dict[str, int] = {}
    for c in load()["channels"]:
        if _usable(c):
            seen[c["categories"][0]] = seen.get(c["categories"][0], 0) + 1
    order = ["news", "entertainment", "movies", "music", "religious", "kids", "sports", "general"]
    keys = sorted(seen, key=lambda k: (order.index(k) if k in order else 99, -seen[k]))
    return [{"id": k, "label": CATEGORY_HI.get(k, k.title()), "count": seen[k]} for k in keys]


def stream_for(c: dict, for_tv: bool = False) -> dict | None:
    ok = [s for s in c["streams"] if s.get("ok", True)]
    if for_tv:
        ok = [s for s in ok if s.get("castable") or ("castable" not in s and not s["user_agent"] and not s["referrer"])]
    return ok[0] if ok else None
