"""Parse Indian bank / UPI transaction SMS into spend entries. Reads only messages the user chooses to share."""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

# An OTP/verification code with the code itself (a "never share your OTP" footer on a debit SMS is not one)
OTP = re.compile(r"\b(?:otp|one[- ]time password|verification code|security code)\b.{0,60}?(?<![\w,.])\d{4,8}(?![\w,.])"
                 r"|(?<![\w,.])\d{4,8}(?![\w,.]).{0,40}?\b(?:is (?:your|the) )?(?:otp|one[- ]time password|verification code)\b", re.I | re.S)
AMT = r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)"
DEBIT = re.compile(r"\b(debited|spent|paid|withdrawn|sent|purchase|dr\b|deducted)", re.I)
CREDIT = re.compile(r"\b(credited|received|deposited|cr\b|refund)", re.I)
MERCHANT_PATTERNS = [
    re.compile(r"\b(?:to|at|towards|for)\s+(?:vpa\s+)?([A-Za-z0-9@._\-& ]{2,40}?)(?:\s+on\b|\s+ref\b|\s+upi\b|\.|,|\s+avl|\s+bal|$)", re.I),
    re.compile(r"\binfo:?\s*([A-Za-z0-9@._\-/ ]{2,40})", re.I),
]
BANKS = ["SBI", "HDFC", "ICICI", "Axis", "Kotak", "PNB", "BoB", "Canara", "Union", "IDFC", "IndusInd", "Yes Bank", "Federal",
         "Bank of Maharashtra", "AU", "Paytm", "Airtel"]
CATEGORIES = {
    "food": ["swiggy", "zomato", "restaurant", "hotel", "cafe", "dominos", "pizza", "eatsure", "biryani"],
    "grocery": ["blinkit", "zepto", "instamart", "bigbasket", "dmart", "jiomart", "kirana", "grocery", "dairy", "milk"],
    "travel": ["uber", "ola", "rapido", "irctc", "redbus", "makemytrip", "indigo", "petrol", "hpcl", "iocl", "bpcl", "fastag", "metro"],
    "bills": ["electricity", "msedcl", "mahavitaran", "bescom", "jio", "airtel", "bsnl", "vodafone", "bbps", "recharge", "gas", "broadband", "dth"],
    "shopping": ["amazon", "flipkart", "myntra", "meesho", "ajio", "nykaa", "tata cliq", "croma"],
    "health": ["pharmacy", "medical", "1mg", "apollo", "pharmeasy", "netmeds", "hospital", "clinic", "lab"],
    "emi_loans": ["emi", "loan", "nach", "ecs"],
    "entertainment": ["netflix", "hotstar", "spotify", "bookmyshow", "prime video", "pvr"],
}


def categorize(merchant: str, text: str) -> str:
    s = (merchant + " " + text).lower()
    for cat, words in CATEGORIES.items():
        if any(w in s for w in words):
            return cat
    if re.search(r"@(ok\w+|ybl|paytm|axl|ibl|upi|apl)\b", merchant.lower()) and not any(c.isdigit() for c in merchant[:3]):
        return "transfers"
    return "other"


def parse_date(text: str, default: dt.date) -> dt.date:
    m = re.search(r"\b(\d{1,2})[-/ ]([A-Za-z]{3}|\d{1,2})[-/ ](\d{2,4})\b", text)
    if m:
        d, mo, y = m.groups()
        y = int(y) + 2000 if len(y) == 2 else int(y)
        try:
            mon = int(mo) if mo.isdigit() else dt.datetime.strptime(mo[:3].title(), "%b").month
            return dt.date(y, mon, int(d))
        except ValueError:
            pass
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        try:
            return dt.date(*map(int, m.groups()))
        except ValueError:
            pass
    return default


def parse_sms(text: str, today: dt.date | None = None) -> dict[str, Any] | None:
    today = today or dt.date.today()
    m = re.search(AMT, text, re.I)
    if not m:
        return None
    if OTP.search(text):
        return None  # never store OTP messages
    amount = int(round(float(m.group(1).replace(",", "")) * 100))
    if DEBIT.search(text) and not re.search(r"\bcredited to\b", text, re.I):
        direction = "debit"
    elif CREDIT.search(text):
        direction = "credit"
    else:
        return None
    merchant = ""
    for p in MERCHANT_PATTERNS:
        mm = p.search(text)
        if mm:
            merchant = mm.group(1).strip(" .-")
            break
    bank = next((b for b in BANKS if re.search(r"\b" + re.escape(b) + r"\b", text, re.I)), "")
    return {"amount_paise": amount, "direction": direction, "merchant": merchant[:160], "bank": bank,
            "category": categorize(merchant, text) if direction == "debit" else "income",
            "occurred_on": parse_date(text, today)}
