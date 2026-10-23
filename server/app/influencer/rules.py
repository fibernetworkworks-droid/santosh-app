"""Influencer Sahayak rules: pure functions (no DB). Disclosure checks (ASCI influencer guidelines + CCPA Endorsement Know-hows),
category gates (health / finance / crypto / real-money games / tobacco & alcohol), fee + GST + TDS notes, engagement numbers
from HER pasted exports, fake-engagement SIGNALS (never verdicts) and a hard refusal of bought followers / bots / pods.

Numbers that come from law / regulators are written with their source in WIRING.md; money figures always come from her."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------- basics
PLATFORMS = {"instagram": "Instagram", "youtube": "YouTube", "facebook": "Facebook", "x": "X (Twitter)", "linkedin": "LinkedIn",
             "snapchat": "Snapchat", "moj": "Moj", "josh": "Josh", "sharechat": "ShareChat", "podcast": "Podcast",
             "blog": "Blog", "whatsapp": "WhatsApp channel", "threads": "Threads", "other": "Doosra"}
PLATFORM_WORDS = {"insta": "instagram", "ig": "instagram", "yt": "youtube", "fb": "facebook", "twitter": "x", "tweet": "x",
                  "snap": "snapchat", "linkedin": "linkedin", "podcast": "podcast", "spotify": "podcast", "blog": "blog"}
FORMATS = {"reel": "Reel", "story": "Story", "post": "Post (photo)", "carousel": "Carousel", "video": "Video (lamba)",
           "short": "Short", "live": "Live", "podcast": "Podcast segment", "blog": "Blog", "tweet": "Tweet / thread",
           "community": "Community post", "other": "Doosra"}
VIDEO_FORMATS = {"reel", "video", "short", "live", "story"}
AUDIO_FORMATS = {"podcast", "live"}
DEAL_KINDS = {"paid": "Paise wali deal", "barter": "Barter (saamaan / trip)", "affiliate": "Affiliate / commission",
              "employee": "Brand ka employee / ambassador", "mixed": "Paise + saamaan"}
STAGES = ["lead", "pitched", "negotiating", "contracted", "live", "done", "lost"]
STAGE_LABEL = {"lead": "Nayi baat", "pitched": "Pitch gaya", "negotiating": "Baat chal rahi", "contracted": "Pakki",
               "live": "Post ho rahe", "done": "Poori", "lost": "Nahi hui"}
POST_STATUS = {"planned": "Planned", "draft": "Draft bana", "with_brand": "Brand ke paas", "approved": "Brand ki haan",
               "live": "Post ho gaya", "missed": "Chhoot gaya"}


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 500) -> str:
    """Her / brand / creator words: secrets never kept (OTP / PIN / password values, card-like / Aadhaar-like numbers)."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|passcode|upi pin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    return t.strip()[:n]


def phone(text: Any) -> str:
    d = re.sub(r"\D", "", str(text or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def money(v: Any) -> float | None:
    """'25k', '1.5 lakh', '₹40,000', 40000 -> rupees. None = not said (never guessed)."""
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if v >= 0 else None
    s = str(v).lower().replace(",", "").replace("₹", " ").replace("rs.", " ").replace("rs", " ").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k|hazar|hazaar|thousand|l|lakh|lac|lakhs|cr|crore)?\b", s)
    if not m:
        return None
    n = float(m.group(1))
    mult = {"k": 1e3, "hazar": 1e3, "hazaar": 1e3, "thousand": 1e3, "l": 1e5, "lakh": 1e5, "lac": 1e5, "lakhs": 1e5,
            "cr": 1e7, "crore": 1e7}.get(m.group(2) or "", 1)
    return round(n * mult, 2)


def count(v: Any) -> int | None:
    """Follower / view counts: '1.2M', '45.6k', '3 lakh', 12000."""
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v) if v >= 0 else None
    s = str(v).lower().replace(",", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k|m|mn|million|l|lakh|lac|cr|crore|b)?\b", s)
    if not m:
        return None
    mult = {"k": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "l": 1e5, "lakh": 1e5, "lac": 1e5, "cr": 1e7, "crore": 1e7,
            "b": 1e9}.get(m.group(2) or "", 1)
    return int(round(float(m.group(1)) * mult))


def platform_of(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in PLATFORMS:
        return s
    for w, p in PLATFORM_WORDS.items():
        if re.search(rf"\b{re.escape(w)}", s):
            return p
    for p in PLATFORMS:
        if p in s:
            return p
    return "other" if s else ""


def format_of(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in FORMATS:
        return s
    for k, words in (("reel", ("reel",)), ("story", ("story", "stories")), ("short", ("short",)), ("carousel", ("carousel",)),
                     ("live", ("live",)), ("podcast", ("podcast", "episode")), ("blog", ("blog", "article")),
                     ("tweet", ("tweet", "thread")), ("video", ("video", "vlog", "integration", "dedicated")),
                     ("post", ("post", "photo", "static"))):
        if any(w in s for w in words):
            return k
    return "other" if s else ""


def as_date(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def fy_of(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def fy_start(d: date) -> date:
    return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


# ---------------------------------------------------------------- never: fake engagement
FAKE_WORDS = re.compile(
    r"\b(buy|kharid\w*|khareed\w*|purchase|order|badha\w*|boost)\s+(?:\w+\s+){0,3}(followers?|likes?|views?|subscribers?|comments?)\b|"
    r"\b(followers?|likes?|views?|subscribers?|comments?)\s+(?:\w+\s+){0,2}(kharid\w*|khareed\w*|buy|purchase|bought)\b|"
    r"\b(fake|nakli|bot|bots|bought)\s+(followers?|likes?|views?|comments?|engagement)\b|"
    r"\b(engagement pod|follow[- ]for[- ]follow|f4f|l4l|like for like|sub4sub|smm panel|follower panel|view bot|auto[- ]?liker)\b",
    re.I)


def fake_engagement(text: Any) -> bool:
    return bool(FAKE_WORDS.search(str(text or "")))


FAKE_REFUSAL = ("Followers / likes / views kharidna, bots ya engagement pods: Hoola yeh kabhi nahi karta. Yeh platform ke niyam "
                "todta hai, brand ko dhokha hai (CCPA misleading-ad / ASCI) aur account band ho sakta hai.")


# ---------------------------------------------------------------- category gates
CATEGORIES = {
    "health": r"\b(health|supplement|protein|vitamin|weight ?loss|wazan|diet|nutrition|ayurved\w*|herbal|skin ?care|acne|hair ?fall|"
              r"immunity|medicine|dawai|dawa|clinic|doctor|fitness|gym|wellness|keto|detox|sugar control|diabetes|bp)\b",
    "finance": r"\b(stock|share market|trading|demat|broker|mutual fund|sip|ipo|f&o|options|intraday|portfolio|investment|"
               r"loan|credit card|insurance|bima|nbfc|fintech|wealth management)\b",
    "crypto": r"\b(crypto|bitcoin|btc|ethereum|nft|web3|token sale|vda|virtual digital asset)\b",
    "gaming_money": r"\b(real[- ]?money|rummy|teen ?patti|fantasy (cricket|team|app)|poker|ludo (cash|paisa)|betting|bet|satta|"
                    r"matka|casino|jua|cash prize game|जुआ|सट्टा)\b",
    "tobacco_alcohol": r"\b(cigarette|tobacco|gutka|gutkha|pan masala|vape|e-?cig\w*|hookah|beer|whisky|whiskey|vodka|rum|wine|"
                       r"liquor|sharab|daaru|daru)\b",
    "kids": r"\b(kids?|children|bachch?on|toy|school bag|baby)\b",
}
BLOCK_CATEGORIES = {
    "gaming_money": "Real-money game / betting / satta ka promotion mana hai (Promotion and Regulation of Online Gaming Act 2025: "
                    "online money games ke ad par saza).",
    "tobacco_alcohol": "Tobacco / sharab (aur unke 'surrogate' brand) ka promotion mana: COTPA 2003 s.5, Cable TV rules aur ASCI. "
                       "Hoola yeh deal nahi chalata.",
}
CRYPTO_DISCLAIMER = ("Crypto products and NFTs are unregulated and can be highly risky. There may be no regulatory recourse for any "
                     "loss from such transactions.")
DISEASE_WORDS = ("diabetes", "sugar ki bimari", "cancer", "obesity", "motapa", "blood pressure", "high bp", "thyroid", "asthma",
                 "arthritis", "infertility", "baal ugana", "gorapan", "fairness", "height badhana", "kidney stone", "piles")
CURE_WORDS = r"(cure|treat|theek|thik|khatam|ilaaj|ilaj|heal|mukti|jad se|permanent)"
FIN_ADVICE = r"\b((buy|sell|kharido|becho|accumulate)\b.{0,40}\b(stock|share|shares|fund|ipo|nifty|option|crypto|coin)|" \
             r"(stock|share|shares|fund|ipo|nifty|option)\b.{0,40}\b(kharido|becho|buy|sell|target|stop ?loss)|" \
             r"multibagger|stock tip|target price|returns? of \d+|\d+\s*%\s*return)"


def categories(text: Any) -> list[str]:
    t = str(text or "").lower()
    return [k for k, pat in CATEGORIES.items() if re.search(pat, t, re.I)]


# ---------------------------------------------------------------- disclosure (ASCI + CCPA)
LABELS_OK = (r"#ad\b", r"#advertisement\b", r"#sponsored\b", r"#paid\b", r"#paidpartnership\b", r"#paid ?partnership\b",
             r"\bad\s*[:|]", r"\badvertisement\b", r"\bsponsored\b", r"\bpaid partnership\b", r"विज्ञापन", r"प्रायोजित")
LABELS_GIFT = (r"#gifted\b", r"#freegift\b", r"#free ?gift\b", r"\bgifted\b")
LABELS_AFF = (r"#affiliate\b", r"\baffiliate link\b")
LABELS_EMP = (r"#employee\b",)
LABELS_WEAK = (r"#collab\b", r"#collaboration\b", r"#partnership\b", r"#partner\b", r"#sp\b", r"#spon\b", r"#thanks\b", r"#ambassador\b")
AI_LABELS = (r"\bai[- ]generated\b", r"\bai se bana", r"\bvirtual (influencer|creator)\b", r"\bai influencer\b", r"#ai\b",
             r"#aigenerated\b", r"\bnot a real person\b", r"#virtualinfluencer\b", r"एआई")


def _has(pats, text: str) -> bool:
    return any(re.search(p, text, re.I) for p in pats)


def first_line(caption: str) -> str:
    for ln in str(caption or "").splitlines():
        if ln.strip():
            return ln.strip()
    return ""


def video_window(duration_s: float | None) -> float | None:
    """ASCI 2025 addendum: <= 15 s video -> label at least 3 s; 15 s - 2 min -> one-third of the length; longer -> whole
    segment where the brand comes (we ask for at least one-third as a safe floor; podcast / live: start AND end)."""
    if not duration_s or duration_s <= 0:
        return None
    if duration_s <= 15:
        return 3.0
    return round(duration_s / 3.0, 1)


def disclosure_check(caption: str, platform: str = "", fmt: str = "", deal_kind: str = "paid", *, virtual: bool = False,
                     ai_media: bool = False, cats: list[str] | None = None, health_qual: str = "", sebi_reg: str = "",
                     ticks: dict | None = None, duration_s: float | None = None) -> dict:
    """What ASCI / CCPA need for this one post. block = she can't approve go-live; warn = she decides; checklist = what she
    (or the creator) confirms by tick for video / audio (Hoola can't watch the final edit)."""
    cap = str(caption or "")
    low = cap.lower()
    fl = first_line(cap)
    cats = list(cats or [])
    ticks = dict(ticks or {})
    block, warn, check = [], [], []
    for c in cats:
        if c in BLOCK_CATEGORIES:
            block.append(BLOCK_CATEGORIES[c])
    if fake_engagement(cap):
        block.append(FAKE_REFUSAL)
    # the label
    kind = deal_kind if deal_kind in DEAL_KINDS else "paid"
    want = {"paid": LABELS_OK, "mixed": LABELS_OK, "barter": LABELS_OK + LABELS_GIFT, "affiliate": LABELS_OK + LABELS_AFF,
            "employee": LABELS_OK + LABELS_EMP}[kind]
    label_any = _has(want, cap)
    label_first = _has(want, fl)
    if not cap.strip():
        block.append("Caption / description khaali hai: pehle draft chahiye.")
    elif not label_any:
        if _has(LABELS_WEAK, cap):
            block.append("Sirf #collab / #partnership / #sp kaafi nahi: saaf '#ad' (ya #sponsored / #paid partnership) chahiye.")
        else:
            block.append("Disclosure label nahi mila: pehli line mein '#ad' (ya #sponsored / #paidpartnership"
                         + (" / #gifted" if kind == "barter" else "") + ") likhiye.")
    elif not label_first:
        block.append("Label pehli line mein hona chahiye ('...more' ke neeche chhupa nahi): '#ad' ko caption ki shuruaat mein laiye.")
    if label_any and _has(LABELS_WEAK, fl) and not label_first:
        warn.append("Pehli line mein #collab hai par #ad neeche: #ad upar laiye.")
    # platform tool (e.g. Instagram paid-partnership tag) is in ADDITION, ask her to tick
    if platform in ("instagram", "facebook", "youtube", "threads"):
        check.append({"key": "platform_tag", "text": "Platform ka apna 'Paid partnership / Includes paid promotion' toggle on kiya",
                      "done": bool(ticks.get("platform_tag"))})
    # video / audio
    if fmt in VIDEO_FORMATS:
        win = video_window(duration_s)
        check.append({"key": "overlay", "text": "Video par '#ad / Sponsored' likha hua (overlay) dikh raha hai"
                      + (f" kam se kam {win:g} second" if win else ""), "done": bool(ticks.get("overlay"))})
        check.append({"key": "spoken", "text": "Shuru ke 10 second mein bola: 'yeh ek paid partnership / ad hai'",
                      "done": bool(ticks.get("spoken"))})
        if fmt == "story":
            check.append({"key": "every_frame", "text": "Har story frame par label (poori der tak)", "done": bool(ticks.get("every_frame"))})
    if fmt in AUDIO_FORMATS:
        check.append({"key": "start_end", "text": "Live / podcast mein shuru AUR ant dono jagah bola ki yeh ad hai",
                      "done": bool(ticks.get("start_end"))})
    # AI / virtual
    if virtual and not _has(AI_LABELS, cap):
        block.append("Virtual / AI influencer: har post mein saaf likhiye ki yeh asli insaan nahi (sirf bio mein kaafi nahi).")
    if ai_media:
        if not _has(AI_LABELS, cap):
            warn.append("AI se bani tasveer / awaaz / video: caption mein 'AI-generated' likhiye.")
        check.append({"key": "ai_toggle", "text": "Upload karte waqt platform ka 'AI-generated' label on kiya (IT Rules 2026)",
                      "done": bool(ticks.get("ai_toggle"))})
    # health
    if "health" in cats:
        if any(d in low for d in DISEASE_WORDS) and re.search(CURE_WORDS, low):
            block.append("Bimari theek / jad se khatam karne ka daava: Drugs & Magic Remedies Act 1954 mein mana. Hata dijiye.")
        if not health_qual:
            warn.append("Health / nutrition par salah: ASCI ke hisaab se creator ki qualification (doctor / dietitian / nutritionist "
                        "certificate) honi chahiye aur post mein dikhni chahiye; warna sirf apna anubhav bataye, salah nahi.")
        elif health_qual.lower() not in low:
            warn.append(f"Qualification ({health_qual}) post mein dikhaiye (CCPA health endorsement guidelines 2023).")
    # finance
    if "finance" in cats:
        if re.search(r"\b(guaranteed|assured|pakka munafa|paisa double|double your money|risk[- ]free)\b", low):
            block.append("Pakka / guaranteed munafa ka daava mana hai (SEBI / ASCI).")
        if re.search(FIN_ADVICE, low) and not sebi_reg:
            block.append("Share / fund khareedne-bechne ki salah sirf SEBI-registered (RA / IA) de sakte hain: creator ka SEBI "
                         "registration number nahi hai, isliye salah wali line hataiye (sirf jaankari rakhiye).")
        if sebi_reg and sebi_reg.lower() not in low:
            warn.append(f"SEBI registration number ({sebi_reg}) post mein dikhaiye.")
    if "crypto" in cats and "unregulated" not in low:
        block.append("Crypto / NFT ad mein ASCI ka disclaimer zaroori: '" + CRYPTO_DISCLAIMER + "'")
    if "kids" in cats and re.search(r"\b(only today|jaldi|abhi kharido|mummy se bolo|ask your parents)\b", low):
        warn.append("Bachchon par dabaav ('mummy se bolo', 'abhi kharido') ASCI ke bachchon wale chapter ke khilaaf.")
    # claims (brand must prove)
    try:
        from ..kalam.service import claims_of
        cl = claims_of(cap)
    except Exception:
        cl = []
    for c in cl[:6]:
        warn.append(f"Daava: “{c['text'][:120]}” — brand se proof lein (ASCI: influencer ko bhi due diligence karni hai).")
    for c in check:
        if not c["done"]:
            warn.append("Tick baaki: " + c["text"])
    ok = not block
    return {"ok": ok, "block": block, "warn": list(dict.fromkeys(warn)), "checklist": check, "label_first": label_first,
            "label_found": label_any, "categories": cats}


# ---------------------------------------------------------------- money: GST + TDS notes (her CA decides)
GST_RATE = 18.0
GST_SAC = "998361"          # advertising services (influencer promotion); SAC 998365 for selling ad space (AdSense)


def gst_of(amount: float, registered: bool, her_state: str, brand_state: str, foreign: bool, lut: bool) -> dict:
    """GST on her invoice. Not registered -> no GST (registration needed above Rs 20 lakh a year, Rs 10 lakh in special states).
    Foreign brand paying in foreign exchange = export of services, zero-rated (with LUT: no IGST; without LUT she pays IGST
    and claims refund)."""
    if not registered or amount <= 0:
        return {"rate": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "total_tax": 0.0,
                "note": "GST registered nahi: invoice par GST nahi (saal mein Rs 20 lakh se upar registration zaroori)."}
    if foreign:
        if lut:
            return {"rate": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "total_tax": 0.0, "export": True,
                    "note": "Videshi brand, videshi mudra mein: export of services, LUT ke saath bina IGST (zero-rated)."}
        tax = round(amount * GST_RATE / 100, 2)
        return {"rate": GST_RATE, "cgst": 0.0, "sgst": 0.0, "igst": tax, "total_tax": tax, "export": True,
                "note": "Export par LUT nahi: IGST lagaya, baad mein refund. LUT (RFD-11) saal ki shuruaat mein bhar dijiye."}
    tax = round(amount * GST_RATE / 100, 2)
    if her_state and brand_state and her_state != brand_state:
        return {"rate": GST_RATE, "cgst": 0.0, "sgst": 0.0, "igst": tax, "total_tax": tax, "note": f"IGST {GST_RATE:g}% (alag rajya)."}
    half = round(tax / 2, 2)
    return {"rate": GST_RATE, "cgst": half, "sgst": round(tax - half, 2), "igst": 0.0, "total_tax": round(half * 2, 2),
            "note": f"CGST + SGST {GST_RATE / 2:g}% + {GST_RATE / 2:g}% (SAC {GST_SAC})."}


TDS_PRO_RATE, TDS_PRO_LIMIT = 10.0, 50000.0       # s.393(1) Table Sl. 6(iii) (old 194J), per FY per payer
TDS_BEN_RATE, TDS_BEN_LIMIT = 10.0, 20000.0       # s.393(1) Table Sl. 8(iv) (old 194R), per FY per giver


def tds_note(fee: float, barter_value: float, fy_fees_from_brand: float, fy_benefits_from_brand: float) -> dict:
    """What the BRAND is likely to deduct (a note: the brand and her CA decide the section; some brands treat creator fees as
    a 'contract' (old 194C) instead of professional fees)."""
    out = {"fee_tds": 0.0, "barter_tds": 0.0, "lines": []}
    if fee > 0:
        if fy_fees_from_brand + fee > TDS_PRO_LIMIT:
            out["fee_tds"] = round(fee * TDS_PRO_RATE / 100, 2)
            out["lines"].append(f"Brand fee par TDS kaat sakta hai: {TDS_PRO_RATE:g}% (Income-tax Act 2025 s.393(1), purana 194J; "
                                f"saal mein Rs {TDS_PRO_LIMIT:,.0f} se upar). Kuch brand ise contract (1% / 2%) maante hain: CA se pakka.")
        else:
            out["lines"].append(f"Is brand se is saal fee Rs {TDS_PRO_LIMIT:,.0f} tak: aam taur par TDS nahi.")
    if barter_value > 0:
        tot = fy_benefits_from_brand + barter_value
        if tot > TDS_BEN_LIMIT:
            out["barter_tds"] = round(barter_value * TDS_BEN_RATE / 100, 2)
            out["lines"].append(f"Barter / free saamaan Rs {tot:,.0f} (is saal is brand se) > Rs {TDS_BEN_LIMIT:,.0f}: brand ko "
                                f"{TDS_BEN_RATE:g}% TDS dena hai saamaan dene se PEHLE (s.393(1) Sl. 8(iv), purana 194R). Saamaan "
                                "creator ki income hai: ITR mein dikhega.")
        else:
            out["lines"].append("Barter saamaan bhi creator ki income hai (aur GST mein barter ka mool); Rs 20,000 tak TDS nahi.")
    return out


# ---------------------------------------------------------------- exclusivity
def overlap(a1: date | None, a2: date | None, b1: date | None, b2: date | None) -> bool:
    if not (a1 and a2 and b1 and b2):
        return False
    return a1 <= b2 and b1 <= a2


# ---------------------------------------------------------------- metrics from HER exports
COLS = {
    "url": ("url", "permalink", "link", "post link", "video link"),
    "post_id": ("post id", "media id", "video id", "content id", "id"),
    "date": ("date", "publish time", "published", "posted", "video publish time", "time"),
    "views": ("views", "plays", "video views", "impressions", "reel plays"),
    "reach": ("reach", "accounts reached", "unique viewers", "unique views"),
    "likes": ("likes", "like", "reactions"),
    "comments": ("comments", "comment"),
    "shares": ("shares", "share", "reposts", "sends"),
    "saves": ("saves", "saved", "bookmarks"),
    "clicks": ("link clicks", "clicks", "sticker taps", "link taps", "website taps", "swipe ups"),
    "watch_min": ("watch time (minutes)", "watch time (hours)", "watch time", "minutes watched"),
    "followers_gained": ("follows", "followers gained", "subscribers", "subscribers gained"),
}


def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ()]", " ", str(h or "").lower())).strip()


def map_cols(headers: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    hs = [_norm(h) for h in headers]
    for key, names in COLS.items():
        for i, h in enumerate(hs):
            if i in out.values():
                continue
            if h in names or any(h.startswith(n) for n in names if len(n) > 3):
                out[key] = i
                if key == "watch_min" and "hour" in h:
                    out["_watch_hours"] = i
                break
    return out


def parse_metrics(raw: bytes | str) -> list[dict]:
    """CSV export (Instagram / YouTube Studio / Meta Business Suite / any sheet with those columns) -> rows. Totals skipped."""
    text = raw.decode("utf-8-sig", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw or "")
    rows = list(csv.reader(io.StringIO(text)))
    head_i, cols = -1, {}
    for i, r in enumerate(rows[:15]):
        c = map_cols(r)
        if len([k for k in c if not k.startswith("_")]) >= 2 and ("views" in c or "reach" in c or "likes" in c):
            head_i, cols = i, c
            break
    if head_i < 0:
        return []
    out = []
    for r in rows[head_i + 1:]:
        if not any(x.strip() for x in r):
            continue
        if r and re.match(r"\s*(total|grand total|kul)\b", str(r[0]), re.I):
            continue
        row: dict[str, Any] = {}
        for k, i in cols.items():
            if k.startswith("_") or i >= len(r):
                continue
            v = r[i].strip()
            if k in ("url", "post_id", "date"):
                row[k] = v[:300]
            else:
                n = count(v) if not re.fullmatch(r"\d+\.\d+", v) else float(v)
                if k == "watch_min" and "_watch_hours" in cols and n is not None:
                    n = float(n) * 60
                row[k] = n
        if any(row.get(k) for k in ("views", "reach", "likes", "comments")):
            out.append(row)
    return out


def engagement(m: dict) -> dict:
    """Engagement only from her numbers. ER = (likes + comments + shares + saves) / reach (else views) x 100."""
    inter = sum(float(m.get(k) or 0) for k in ("likes", "comments", "shares", "saves"))
    base = float(m.get("reach") or 0) or float(m.get("views") or 0)
    er = round(inter / base * 100, 2) if base else None
    return {"interactions": int(inter), "er_pct": er, "base": "reach" if m.get("reach") else ("views" if m.get("views") else "")}


def campaign_numbers(posts: list[dict], fee: float | None) -> dict:
    tot = {k: 0.0 for k in ("views", "reach", "likes", "comments", "shares", "saves", "clicks")}
    have = 0
    for p in posts:
        m = p.get("metrics") or {}
        if not m:
            continue
        have += 1
        for k in tot:
            tot[k] += float(m.get(k) or 0)
    e = engagement(tot)
    out = {**{k: int(v) for k, v in tot.items()}, **e, "posts_with_numbers": have, "posts": len(posts)}
    if fee and fee > 0:
        out["cpm"] = round(fee / tot["views"] * 1000, 2) if tot["views"] else None
        out["cpe"] = round(fee / e["interactions"], 2) if e["interactions"] else None
        out["cpc"] = round(fee / tot["clicks"], 2) if tot["clicks"] else None
    return out


def fake_signals(followers: int | None, avg_likes: float | None, avg_comments: float | None,
                 history: list[dict] | None = None) -> list[str]:
    """SIGNALS only (never a verdict, never shown to a brand as an accusation): from numbers she typed / pasted."""
    out = []
    if followers and avg_likes is not None and followers > 0:
        er = (avg_likes + (avg_comments or 0)) / followers * 100
        if er > 25:
            out.append(f"Likes+comments followers ka {er:.1f}%: bahut zyada, numbers ek baar check kijiye (screenshot / export).")
        elif er < 0.3 and followers >= 10000:
            out.append(f"Likes+comments followers ka sirf {er:.2f}%: followers ka bada hissa shayad active nahi.")
    if avg_likes and avg_comments is not None and avg_likes >= 500 and avg_comments / avg_likes < 0.002:
        out.append("Likes ke hisaab se comments bahut kam: comments / likes check kijiye.")
    hs = sorted([h for h in (history or []) if h.get("on") and h.get("followers")], key=lambda h: str(h["on"]))
    for a, b in zip(hs, hs[1:]):
        da, db = as_date(a["on"]), as_date(b["on"])
        if da and db and 0 < (db - da).days <= 7 and a["followers"] and b["followers"] / a["followers"] >= 1.2:
            out.append(f"{a['on']} se {b['on']} ke beech followers {int((b['followers'] / a['followers'] - 1) * 100)}% badhe: "
                       "viral post tha ya kuch aur? Brand poochh sakta hai.")
    return out
