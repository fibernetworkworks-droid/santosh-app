"""v0.59 QR codes and barcodes in the owner's photos and screenshots (zxing-cpp, Apache-2.0), READ ONLY.

- UPI QR (upi://pay, upi://mandate) -> who gets the money, amount, note + plain-word scam hints. Hoola never pays:
  scanning a QR only ever SENDS money, it never brings money in, and that is said every time.
- GST e-invoice QR (signed JWT from the IRP) -> seller / buyer GSTIN, invoice no, date, value, IRN (signature not checked).
- Links -> shown as a link (the owner decides); product barcodes (EAN / UPC) -> the number, "made in India" for 890.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

log = logging.getLogger("santosh.qr")

SCAM_WORDS = re.compile(r"(?i)refund|cash ?back|reward|prize|lottery|lucky|kyc|verify|verification|receive|recieve|"
                        r"won|winner|gift|bonus|claim|electricity cut|bijli|army|olx|customs|parcel|job fee|registration fee|"
                        r"paise milenge|paisa aayega|inaam|jeet")
_VPA = re.compile(r"^[\w.\-]{2,256}@[a-zA-Z][\w]{1,64}$")


def scan(data: bytes) -> list[dict[str, Any]]:
    """All codes in one picture. [] when none / zxing-cpp missing / not a picture."""
    try:
        import zxingcpp
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        found = zxingcpp.read_barcodes(im)
        if not found and max(im.size) > 1800:          # big photo with a small QR: try a smaller copy too
            small = im.copy()
            small.thumbnail((1400, 1400))
            found = zxingcpp.read_barcodes(small)
    except Exception as e:
        log.info("qr scan: %s", e)
        return []
    out, seen = [], set()
    for b in found[:8]:
        text = (b.text or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(describe(text, str(b.format).split(".")[-1]))
    return out


def describe(text: str, fmt: str = "QRCode") -> dict[str, Any]:
    low = text.lower()
    if low.startswith("upi://"):
        return {"format": fmt, "kind": "upi", **parse_upi(text)}
    if text.count(".") == 2 and len(text) > 200 and re.fullmatch(r"[\w\-]+\.[\w\-]+\.[\w\-]+", text):
        inv = parse_einvoice(text)
        if inv:
            return {"format": fmt, "kind": "gst_invoice", "invoice": inv,
                    "say": f"GST e-invoice: {inv.get('seller_gstin', '?')}, bill {inv.get('doc_no', '?')} "
                           f"({inv.get('doc_date', '?')}), ₹{inv.get('total', '?')}. The signature was not checked here."}
    if re.match(r"(?i)^https?://", text):
        host = urlsplit(text).hostname or ""
        return {"format": fmt, "kind": "link", "url": text[:500], "host": host,
                "say": f"This is a link: {host}. Before opening it, check that it is the right site."}
    if fmt.upper().startswith(("EAN", "UPC")) and text.isdigit():
        made = "Made in India (890)" if text.startswith("890") and len(text) == 13 else ""
        return {"format": fmt, "kind": "product", "code": text, "say": f"Product barcode {text}" + (f" · {made}" if made else "")}
    if low.startswith(("begin:vcard", "mecard:")):
        return {"format": fmt, "kind": "contact", "text": text[:600], "say": "This is a contact card (vCard)."}
    if low.startswith("wifi:"):
        ssid = re.search(r"S:([^;]*)", text)
        return {"format": fmt, "kind": "wifi", "ssid": ssid.group(1) if ssid else "",
                "say": f"Wi-Fi QR: {ssid.group(1) if ssid else ''} (the password is in the QR; I will not write it in the chat)."}
    return {"format": fmt, "kind": "text", "text": text[:600], "say": "The QR says: " + text[:120]}


def parse_upi(text: str) -> dict[str, Any]:
    u = urlsplit(text)
    action = (u.netloc or u.path.strip("/")).lower() or "pay"
    q = {k.lower(): unquote(v[0]).strip() for k, v in parse_qs(u.query, keep_blank_values=True).items() if v}
    pa, pn = q.get("pa", ""), q.get("pn", "")
    amount = None
    try:
        amount = round(float(q.get("am", "") or "nan"), 2)
        if amount != amount:
            amount = None
    except ValueError:
        amount = None
    note = q.get("tn", "")
    warnings: list[str] = []
    if action == "mandate":
        warnings.append("This is an AUTOPAY / mandate QR: it gives permission to take money again and again.")
    if not pa or not _VPA.match(pa):
        warnings.append("The UPI ID does not look right.")
    if amount is not None and amount > 0:
        warnings.append(f"The QR already has ₹{amount:,.2f} filled in: the moment you enter your PIN, that much money GOES OUT.")
    if SCAM_WORDS.search(" ".join((note, pn, q.get("purpose", "")))):
        warnings.append("The note talks of 'refund / prize / KYC / you will get money': this is a common scam.")
    if amount is not None and amount >= 10000:
        warnings.append("This is a large amount: talk to that person on the phone before you send it.")
    if not pn:
        warnings.append("The QR does not have the receiver's name.")
    merchant = bool(q.get("mc")) and q.get("mc") != "0000"
    who = pn or pa or "?"
    say = (f"UPI QR: the money will go to '{who}' ({pa})" + (f", ₹{amount:,.2f}" if amount else "") +
           (f", note: {note}" if note else "") + ". Remember: scanning a QR only SENDS money, it never brings money in.")
    return {"action": action, "payee_vpa": pa, "payee_name": pn, "amount": amount, "currency": q.get("cu", "INR") or "INR",
            "note": note[:120], "merchant": merchant, "warnings": warnings,
            "risky": any(k in w for w in warnings for k in ("scam", "AUTOPAY", "does not look right")), "say": say,
            "never_pays": True}


def parse_einvoice(token: str) -> dict[str, Any] | None:
    """The payload of the IRP-signed QR (JWT); the signature itself is not verified here."""
    try:
        part = token.split(".")[1]
        payload = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        d = payload.get("data")
        d = json.loads(d) if isinstance(d, str) else (d or payload)
    except Exception:
        return None
    if not isinstance(d, dict) or not (d.get("SellerGstin") or d.get("Irn")):
        return None
    out = {"seller_gstin": d.get("SellerGstin"), "buyer_gstin": d.get("BuyerGstin"), "doc_no": d.get("DocNo"),
           "doc_type": d.get("DocTyp"), "doc_date": d.get("DocDt"), "total": d.get("TotInvVal"), "items": d.get("ItemCnt"),
           "hsn": d.get("MainHsnCode"), "irn": d.get("Irn"), "irn_date": d.get("IrnDt"), "issuer": payload.get("iss")}
    from .india.money import gstin_ok
    for k in ("seller_gstin", "buyer_gstin"):
        if out.get(k):
            out[k + "_valid"] = gstin_ok(str(out[k]))
    return {k: v for k, v in out.items() if v not in (None, "")}


def summary_line(codes: list[dict[str, Any]]) -> str:
    """One line for the agent's context when a photo carries codes."""
    if not codes:
        return ""
    bits = []
    for c in codes[:3]:
        s = c.get("say") or c.get("kind")
        if c.get("warnings"):
            s += " WARNINGS: " + " | ".join(c["warnings"])
        bits.append(s)
    return "QR/barcode found: " + " ;; ".join(bits)
