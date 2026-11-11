"""v0.121 What a Hoola website may never be: a look-alike of a bank / government office / courier / payment app / big
brand, a page that collects OTP / PIN / card / KYC details under false pretences, or a page carrying the national
emblem, flag or leaders' pictures (Emblems Act). Checked on every brief, change and (v0.123) domain name."""
from __future__ import annotations

import re

# trust brands: banks, payments, government, couriers, telecom - even "jaisi" (looks like) is refused
TRUST = (r"sbi|state bank|hdfc|icici|axis bank|kotak|bank of baroda|pnb|canara|union bank|idbi|yes bank|indusind|paytm|"
         r"phonepe|phone pe|google pay|gpay|bhim|npci|irctc|uidai|aadhaar|aadhar|income ?tax|incometax|gst portal|epfo|"
         r"digilocker|passport seva|india post|post office|bluedart|blue dart|delhivery|dtdc|fedex|dhl|lic of india|jio|"
         r"airtel|vodafone|bsnl|rbi|reserve bank|sebi|police|court|ministry|government|sarkar|sarkari|nic\.in|gov\.in")
# other big brands: "Amazon jaisa online store" is a fine wish (a style); copying their look is not
BIG = TRUST + r"|amazon|flipkart|myntra|meesho|swiggy|zomato|ola|uber|netflix|whatsapp|facebook|instagram|google|microsoft|apple"
COPY = r"(copy|clone|replica|duplicate|look ?alike|lookalike|same as|exactly like|hubahu|bilkul waisi|mirror|nakal|nakli|fake)"
LIKE = r"(jaisi|jaisa|jaise|ki tarah|similar to|like the)"
TRAPS = (r"(otp|pin|cvv|card number|card details|net ?banking|login|password|kyc|refund|lottery|prize|reward|kbc|"
         r"lucky draw|job offer fee|registration fee).{0,30}(collect|le lo|lena|form|page|update|verify|claim)")


def brief_problem(text: str) -> str:
    t = (text or "").lower()
    if not t.strip():
        return ""
    if (re.search(rf"{COPY}.{{0,40}}\b({BIG})\b|\b({BIG})\b.{{0,40}}{COPY}", t) or
            re.search(rf"\b({TRUST})\b.{{0,25}}{LIKE}|{LIKE}.{{0,25}}\b({TRUST})\b", t)):
        return ("Hoola does not make a website that looks like a bank, government office, courier, payment app or big brand "
                "(people could be cheated). I will gladly build your business's own website.")
    if re.search(TRAPS, t) and re.search(rf"\b({BIG}|bank|upi|wallet)\b", t):
        return ("Hoola does not make a page that takes an OTP / PIN / card / KYC / login. Money from customers comes only through their own UPI app "
                "or your real payment gateway.")
    try:
        from ..brand.rules import protected
        bad = protected(t)
        if bad:
            return "This cannot go on the website (Emblems Act / confusion): " + ", ".join(bad) + "."
    except Exception:
        pass
    return ""


def name_problem(name: str) -> str:
    """Domain / site names close to a known brand are refused (used again by the domain chooser)."""
    n = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    for b in ("sbi", "hdfc", "icici", "axisbank", "kotak", "paytm", "phonepe", "googlepay", "amazon", "flipkart", "irctc",
              "uidai", "aadhaar", "incometax", "epfo", "digilocker", "indiapost", "bluedart", "delhivery", "jio", "airtel",
              "bsnl", "swiggy", "zomato", "netflix", "whatsapp", "facebook", "instagram", "google", "microsoft", "apple",
              "rbi", "sebi", "lic"):
        if b in n and len(b) >= 4 or n.startswith(b) and len(b) >= 3:
            return f"'{name}' contains the well-known name '{b}'; such a name cannot be used (confusion + trademark)."
    return ""
