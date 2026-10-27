"""v0.111 Ads Sahayak: report columns, India benchmarks, ad-copy limits and the rules leaks are judged by (pure functions).

Sources (22 Oct 2026):
- Meta learning phase: about 50 optimization events in the 7 days after the last significant edit; budget changes are a
  significant edit, so practitioners change budgets in steps of about 20 % (cometly.com, lseo.com, fospha academy).
- India Meta benchmarks 2025 (vendor / agency data, a guide only): CPM Rs 50-120, CPC Rs 8-25, CTR 0.7-1.3 %, CPL real
  estate Rs 600-1,200, education Rs 200-450, clinics Rs 180-380, finance / insurance Rs 350-700, home services Rs 100-250
  (owlclaw.com/benchmarks/meta-ads-benchmarks-india).
- Meta: securities / investment ads aimed at India need SEBI-based beneficiary + payer verification (enforced from 31 Jul
  2025; developers.facebook.com blog 26 Jun 2025, ppc.land). Graph / Marketing API v26.0 (29 Jul 2026): Special Ad Category
  ad sets set advantage_audience explicitly; Instagram Explore Feed placement removed (relevantaudience.com).
- India: Promotion and Regulation of Online Gaming Act 2025 bans real-money online games and their ads; betting /
  gambling ads are not allowed; ASCI / CCPA claim rules are the same as for content (see kalam.service.RISK).
- Ad text limits: Meta primary text ~125 characters before "See more", headline 40 (27 shown), description 30;
  Google responsive search ads 3-15 headlines x 30, 2-4 descriptions x 90, two display paths x 15.
"""
from __future__ import annotations

import math
import re
from typing import Any

# ---------------------------------------------------------------- report columns (Meta Ads Manager / Google Ads exports)
COLS = {
    "day": ("day", "date", "reporting starts", "reporting_start", "date_start", "din", "tareekh"),
    "end": ("reporting ends", "reporting_end", "date_stop"),
    "campaign": ("campaign name", "campaign", "campaign_name"),
    "adset": ("ad set name", "adset name", "ad group", "ad group name", "adset_name", "adset"),
    "ad": ("ad name", "ad", "ad_name", "headline 1"),
    "term": ("search term", "search terms", "keyword", "search keyword"),
    "match": ("match type", "keyword match type", "search terms match type"),
    "spend": ("amount spent (inr)", "amount spent", "amount_spent", "spend", "cost", "cost (inr)", "kharcha"),
    "impressions": ("impressions", "impr.", "impr", "impression"),
    "reach": ("reach",),
    "frequency": ("frequency",),
    "clicks": ("link clicks", "clicks", "clicks (all)", "inline_link_clicks"),
    "results": ("results", "leads", "conversions", "purchases", "conv.", "on-facebook leads", "website leads",
                "messaging conversations started", "result"),
    "result_type": ("result indicator", "result type", "conversion action", "optimization goal"),
    "value": ("purchases conversion value", "conv. value", "conversion value", "all conv. value", "purchase value",
              "website purchases conversion value"),
    "lost_budget": ("search lost is (budget)", "search lost impression share (budget)"),
    "lost_rank": ("search lost is (rank)", "search lost impression share (rank)"),
    "quality": ("quality score", "qual. score"),
    "status": ("delivery", "status", "campaign state", "ad set delivery", "ad group state"),
    "budget": ("budget", "ad set budget", "daily budget", "budget (inr)"),
    "placement": ("placement", "platform position", "publisher platform", "network", "network (with search partners)"),
}
PLATFORM_WORDS = {
    "google": ("impr.", "avg. cpc", "cost / conv.", "search term", "ad group", "conv.", "search lost is (budget)",
               "quality score"),
    "meta": ("amount spent (inr)", "ad set name", "reach", "frequency", "result indicator", "link clicks",
             "reporting starts", "cpm (cost per 1,000 impressions)"),
}
# benchmarks (India, 2025 agency data; shown as "andaaza", never as a promise)
SEGMENTS = {
    "real_estate": {"label": "Real estate", "cpl": (600, 1200), "good_cpl": 500, "ctr": 0.9},
    "education": {"label": "Coaching / education", "cpl": (200, 450), "good_cpl": 200, "ctr": 1.1},
    "clinic": {"label": "Clinic / health", "cpl": (180, 380), "good_cpl": 180, "ctr": 0.8},
    "finance": {"label": "Loan / insurance / finance", "cpl": (350, 700), "good_cpl": 300, "ctr": 0.7},
    "ecommerce": {"label": "Online store", "cpl": None, "good_roas": 3.5, "ctr": 1.3},
    "home_services": {"label": "Ghar ki seva (repair, cleaning)", "cpl": (100, 250), "good_cpl": 120, "ctr": 1.0},
    "isp": {"label": "Internet / broadband", "cpl": (120, 300), "good_cpl": 150, "ctr": 1.0},
    "local": {"label": "Dukaan / local business", "cpl": (80, 250), "good_cpl": 120, "ctr": 1.0},
    "general": {"label": "Baaki", "cpl": None, "ctr": 0.9},
}
BENCH_NOTE = "India 2025 agency data, sirf andaaza; aapka apna pichhla hisaab zyada sach hai."
LEARNING_EVENTS = 50          # Meta: ~50 optimization events / 7 days to leave learning
MAX_STEP_PCT = 20             # budget step that does not reset learning (practice)
FATIGUE_FREQ = 3.5            # frequency over 7 days where CTR usually falls
LIMITS = {
    "meta": {"primary": 125, "headline": 40, "description": 30, "variants": 5},
    "google": {"headline": 30, "description": 90, "path": 15, "headlines": (3, 15), "descriptions": (2, 4)},
}
BANNED = [
    (r"\b(real[- ]?money|rummy|teen ?patti|fantasy (cricket|team)|poker|ludo (cash|paisa)|betting|satta|matka|"
     r"casino|bet\s?(lagao|karo)|jua|जुआ|सट्टा)\b",
     "Real-money game / satta / jua ka ad India mein mana hai (Online Gaming Act 2025; Meta / Google bhi rokte hain)."),
    (r"\b(guaranteed returns?|assured returns?|paisa double|double your money|pakka munafa|fixed profit)\b",
     "Pakka munafa / guaranteed return: SEBI / RBI aur ASCI ke hisaab se mana."),
]
FIN_WORDS = r"\b(stock|share market|trading|demat|mutual fund|sip|ipo|f&o|options|intraday|portfolio|investment advice|" \
            r"शेयर|ट्रेडिंग)\b"


def norm(h: Any) -> str:
    return re.sub(r"\s+", " ", str(h or "").strip().lower().replace("﻿", ""))


def detect(headers: list[str]) -> str:
    hs = {norm(h) for h in headers}
    score = {p: sum(1 for w in ws if w in hs) for p, ws in PLATFORM_WORDS.items()}
    best = max(score, key=lambda p: score[p])
    return best if score[best] else "other"


def map_columns(headers: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    hs = [norm(h) for h in headers]
    for key, names in COLS.items():
        for n in names:
            if n in hs and key not in out:
                out[key] = hs.index(n)
        if key not in out:                      # "Amount spent (USD)", "Cost per lead" must NOT match spend / results
            for i, h in enumerate(hs):
                if any(h.startswith(n + " (") for n in names) and not h.startswith("cost per"):
                    out[key] = i
                    break
    return out


def num(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("INR", "").strip()
    if s in ("", "-", "--", "—", "N/A", "n/a", "<10%", " --"):
        return None
    s = s.rstrip("%").strip()
    if s.startswith("<") or s.startswith(">"):
        s = s[1:]
    try:
        return float(s)
    except ValueError:
        return None


def pct(v: Any) -> float | None:
    """Google shares come as '45.20%' or '<10%' or 0.452."""
    if v is None:
        return None
    s = str(v).strip()
    n = num(s)
    if n is None:
        return 10.0 if s.startswith("<") else None
    if "%" in s or n > 1:
        return n
    return n * 100


# ---------------------------------------------------------------- the numbers
def ratios(spend: float, impressions: float, clicks: float, results: float, value: float = 0) -> dict[str, Any]:
    return {"ctr": round(clicks / impressions * 100, 2) if impressions else None,
            "cpc": round(spend / clicks, 2) if clicks else None,
            "cpm": round(spend / impressions * 1000, 2) if impressions else None,
            "cpl": round(spend / results, 2) if results else None,
            "cvr": round(results / clicks * 100, 2) if clicks else None,
            "roas": round(value / spend, 2) if spend and value else None}


def max_cpl(avg_order: float, margin_pct: float, close_pct: float) -> float | None:
    """The most a lead may cost before it loses money: order value x margin x leads that buy."""
    if avg_order > 0 and margin_pct > 0 and close_pct > 0:
        return round(avg_order * margin_pct / 100 * close_pct / 100, 2)
    return None


def two_prop_p(x1: int, n1: int, x2: int, n2: int) -> float | None:
    """Two-sided p-value of a difference in rates (z-test, pooled). None when too small to say."""
    if min(n1, n2) < 30 or x1 + x2 < 10:
        return None
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = abs(x1 / n1 - x2 / n2) / se
    return round(math.erfc(z / math.sqrt(2)), 4)


def banned(text: str) -> list[str]:
    t = (text or "").lower()
    return [msg for pat, msg in BANNED if re.search(pat, t, re.I)]


def financial(text: str) -> bool:
    return bool(re.search(FIN_WORDS, (text or "").lower(), re.I))
