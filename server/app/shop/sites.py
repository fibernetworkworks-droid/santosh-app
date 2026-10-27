"""Sites Hoola can order from, and how (official MCP first, else the Computer Operator in its own Chrome).

Each playbook is plain guidance for the operator (who already follows every gate in code): direct cart / checkout
addresses are opened by URL so the job reaches the payment page without pressing buttons that only LOOK like paying
("Buy now", Flipkart's "Place order" in the cart). The real pay / place-your-order button is still pressed only by her.
"""
from __future__ import annotations

import re
from urllib.parse import quote_plus

SITES: dict[str, dict] = {
    # food
    "swiggy": {"name": "Swiggy", "kind": "food", "web": "https://www.swiggy.com", "mcp": "swiggy-food",
               "search": "https://www.swiggy.com/search?query={q}", "words": ["swiggy"],
               "play": "Pick the restaurant (open now, rating 4+, delivery time) -> add the dishes with the right quantity / "
                       "options -> open the cart (https://www.swiggy.com/checkout) -> choose her saved address -> apply the "
                       "best visible coupon -> stop at the pay step."},
    "zomato": {"name": "Zomato", "kind": "food", "web": "https://www.zomato.com", "mcp": "zomato",
               "search": "https://www.zomato.com/search?q={q}", "words": ["zomato"],
               "play": "Pick the restaurant (open now, delivery rating 4+) -> Order Online -> add dishes -> cart -> saved "
                       "address -> best coupon -> stop at the pay step."},
    # quick grocery
    "instamart": {"name": "Swiggy Instamart", "kind": "grocery", "web": "https://www.swiggy.com/instamart",
                  "mcp": "swiggy-instamart", "search": "https://www.swiggy.com/instamart/search?query={q}",
                  "words": ["instamart"],
                  "play": "Search each item, pick the right brand / size, add with quantity -> cart -> saved address / "
                          "slot -> stop at the pay step."},
    "blinkit": {"name": "Blinkit", "kind": "grocery", "web": "https://blinkit.com", "search": "https://blinkit.com/s/?q={q}",
                "words": ["blinkit", "grofers"],
                "play": "Set her delivery location if asked -> search each item -> ADD with quantity -> open cart -> saved "
                        "address -> stop at 'Proceed to pay'."},
    "zepto": {"name": "Zepto", "kind": "grocery", "web": "https://www.zeptonow.com", "mcp": "zepto",
              "search": "https://www.zeptonow.com/search?query={q}", "words": ["zepto"],
              "play": "Location -> search each item -> Add -> cart -> address -> stop at the pay step."},
    "bigbasket": {"name": "BigBasket", "kind": "grocery", "web": "https://www.bigbasket.com",
                  "search": "https://www.bigbasket.com/ps/?q={q}", "words": ["bigbasket", "big basket", "bb now"],
                  "play": "Search each item -> Add -> basket (https://www.bigbasket.com/basket/) -> Checkout -> slot / "
                          "address -> stop at the pay step."},
    "jiomart": {"name": "JioMart", "kind": "grocery", "web": "https://www.jiomart.com",
                "search": "https://www.jiomart.com/search/{q}", "words": ["jiomart", "jio mart"],
                "play": "Pincode -> search -> Add to cart -> cart (https://www.jiomart.com/checkout/cart) -> Place order "
                        "leads to address / payment: stop at the pay step."},
    "dmart": {"name": "DMart Ready", "kind": "grocery", "web": "https://www.dmart.in",
              "search": "https://www.dmart.in/search?searchTerm={q}", "words": ["dmart", "d mart"],
              "play": "Pincode / pick-up point -> search -> Add -> cart -> slot -> stop at the pay step."},
    # shopping
    "amazon": {"name": "Amazon", "kind": "shopping", "web": "https://www.amazon.in",
               "search": "https://www.amazon.in/s?k={q}", "words": ["amazon"],
               "play": "Search -> open 2-3 good results (rating 4+, many reviews, sold by a known seller, delivery date) "
                       "and choose by her wishes / budget -> pick size / colour / quantity -> 'Add to Cart' (not 'Buy Now') "
                       "-> open the cart https://www.amazon.in/gp/cart/view.html and check items + quantity -> open "
                       "checkout https://www.amazon.in/gp/buy/spc/handlers/display.html?hasWorkingJavascript=1 -> choose her "
                       "saved delivery address -> stop at 'Place your order' / payment (she presses it)."},
    "flipkart": {"name": "Flipkart", "kind": "shopping", "web": "https://www.flipkart.com",
                 "search": "https://www.flipkart.com/search?q={q}", "words": ["flipkart"],
                 "play": "Search -> compare 2-3 results (rating 4+, Flipkart Assured, delivery date) -> pick variant -> "
                         "'Add to cart' -> cart https://www.flipkart.com/viewcart -> open https://www.flipkart.com/checkout/init "
                         "-> saved address -> Continue -> stop at the payment options (she pays)."},
    "meesho": {"name": "Meesho", "kind": "shopping", "web": "https://www.meesho.com",
               "search": "https://www.meesho.com/search?q={q}", "words": ["meesho"],
               "play": "Search -> pick (rating, reviews, size) -> Add to cart -> cart -> address -> stop at payment."},
    "myntra": {"name": "Myntra", "kind": "fashion", "web": "https://www.myntra.com",
               "search": "https://www.myntra.com/{q}", "words": ["myntra"],
               "play": "Search -> filter size / price -> pick -> select size -> Add to bag -> bag "
                       "https://www.myntra.com/checkout/cart -> address -> stop at payment."},
    "ajio": {"name": "AJIO", "kind": "fashion", "web": "https://www.ajio.com", "search": "https://www.ajio.com/search/?text={q}",
             "words": ["ajio"], "play": "Search -> size -> Add to bag -> bag -> address -> stop at payment."},
    "nykaa": {"name": "Nykaa", "kind": "beauty", "web": "https://www.nykaa.com",
              "search": "https://www.nykaa.com/search/result/?q={q}", "words": ["nykaa"],
              "play": "Search -> pick shade / size -> Add to bag -> bag -> address -> stop at payment."},
    "croma": {"name": "Croma", "kind": "electronics", "web": "https://www.croma.com",
              "search": "https://www.croma.com/searchB?q={q}", "words": ["croma"],
              "play": "Search -> compare specs / price -> Add to cart -> cart -> pincode delivery -> stop at payment."},
    "tatacliq": {"name": "Tata CLiQ", "kind": "shopping", "web": "https://www.tatacliq.com",
                 "search": "https://www.tatacliq.com/search/?searchCategory=all&text={q}", "words": ["tata cliq", "tatacliq"],
                 "play": "Search -> pick -> Add to bag -> bag -> address -> stop at payment."},
    # medicines
    "1mg": {"name": "Tata 1mg", "kind": "pharmacy", "web": "https://www.1mg.com", "search": "https://www.1mg.com/search/all?name={q}",
            "words": ["1mg", "tata 1mg"],
            "play": "Search the exact medicine / strength -> Add -> cart -> upload prescription ONLY from her file_ids when "
                    "the site asks -> address -> stop at payment."},
    "pharmeasy": {"name": "PharmEasy", "kind": "pharmacy", "web": "https://pharmeasy.in",
                  "search": "https://pharmeasy.in/search/all?name={q}", "words": ["pharmeasy", "pharm easy"],
                  "play": "Search -> Add -> cart -> prescription (her file only) -> address -> stop at payment."},
    # travel / tickets
    "irctc": {"name": "IRCTC", "kind": "travel", "web": "https://www.irctc.co.in/nget/train-search", "words": ["irctc", "train"],
              "play": "Login (her password / OTP / CAPTCHA via her phone) -> From / To / date / class / quota -> pick the "
                      "train with seats -> Book Now -> passengers (names, ages from her message; IDs from the locker if "
                      "asked) -> review -> stop at payment."},
    "redbus": {"name": "redBus", "kind": "travel", "web": "https://www.redbus.in", "words": ["redbus", "red bus", "bus"],
               "play": "From / To / date -> pick bus (rating, time, price) -> seats -> boarding / dropping -> passenger "
                       "details -> stop at payment."},
    "makemytrip": {"name": "MakeMyTrip", "kind": "travel", "web": "https://www.makemytrip.com",
                   "words": ["makemytrip", "make my trip", "mmt", "flight", "hotel"],
                   "play": "Search (flights / hotels) with her dates -> compare 3 options -> select -> traveller details "
                           "-> no paid add-ons unless she asked -> stop at payment."},
    "bookmyshow": {"name": "BookMyShow", "kind": "tickets", "web": "https://in.bookmyshow.com",
                   "words": ["bookmyshow", "book my show", "movie ticket"],
                   "play": "City -> movie / event -> date / show time -> seats she wants -> stop at payment."},
}

KIND_DEFAULT = {"food": ["swiggy", "zomato"], "grocery": ["blinkit", "zepto", "instamart", "bigbasket"],
                "shopping": ["amazon", "flipkart"], "fashion": ["myntra", "ajio"], "pharmacy": ["1mg", "pharmeasy"],
                "electronics": ["amazon", "flipkart", "croma"], "beauty": ["nykaa", "amazon"], "travel": ["irctc"],
                "tickets": ["bookmyshow"]}

FOOD_WORDS = ("khana", "biryani", "pizza", "burger", "thali", "dosa", "momos", "restaurant", "dinner", "lunch", "food")
GROCERY_WORDS = ("doodh", "milk", "atta", "dal", "sabzi", "vegetable", "grocery", "kirana", "eggs", "anda", "bread")


def find(text: str) -> str:
    """Site id named in her words ('' = none named)."""
    t = (text or "").lower()
    for sid, s in SITES.items():
        if sid in t or any(w in t for w in s.get("words", [])):
            return sid
    return ""


def guess_kind(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in FOOD_WORDS):
        return "food"
    if any(w in t for w in GROCERY_WORDS):
        return "grocery"
    return "shopping"


FILLER = {"se", "par", "pe", "mein", "mangwa", "mangwao", "mangao", "manga", "do", "dena", "de", "dijiye", "order", "karo",
          "kar", "kardo", "karna", "book", "chahiye", "lao", "le", "lo", "lena", "please", "plz", "mujhe", "mere", "liye",
          "ek", "achha", "accha", "sabse", "sasta", "saste", "tak", "under", "from", "on", "buy", "get", "me", "a", "an"}


def query_of(what: str, site: str = "") -> str:
    """Search words from her sentence: no site name, no 'mangwa do', no quantities / budget."""
    t = (what or "").lower()
    t = re.split(r"[,;]| aur | and ", t)[0] if len(t) > 40 else t
    for w in SITES.get(site, {}).get("words", []) + [site]:
        if w:
            t = t.replace(w, " ")
    t = re.sub(r"(rs\.?|₹)\s*[\d,]+|\b\d+\s*tak\b|\b\d+\s*(piece|pcs|plate|packet|pack|kg|g|gm|litre|liter|l|ml)\b", " ", t)
    words = [w for w in re.findall(r"[\w\-\.]+", t) if w not in FILLER]
    return " ".join(words)[:80] or (what or "")[:80]


def search_url(site: str, query: str) -> str:
    s = SITES[site]
    if s.get("search") and query:
        return s["search"].format(q=quote_plus(query) if "{q}" in s["search"] and "/{q}" not in s["search"]
                                  else quote_plus(query).replace("+", "-"))
    return s["web"]


def listing() -> list[dict]:
    return [{"id": k, "name": v["name"], "kind": v["kind"], "web": v["web"], "official_api": bool(v.get("mcp"))}
            for k, v in SITES.items()]
