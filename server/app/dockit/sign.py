"""D5 signing - honest about what each kind is (plan law 4.8):

- place: her own signature picture (saved once, sealed) put on the pages she names = an ELECTRONIC signature.
- digital: a cryptographic signature (pyHanko) with HER Hoola document certificate - made for her on first use, kept
  sealed on her server. It proves the file has NOT CHANGED since it was signed; it does NOT prove her legal identity
  (that needs a Class 3 DSC on a USB token, or Aadhaar eSign through a licensed provider - not built, owner decision D4).
- requests: other people sign on a one-time page (/sign/<token>) in her order; each signature is placed, an audit page is
  added (who, when, from where, the file's fingerprint before and after) and the file is sealed with her certificate.
  The signer's identity is whoever holds the link - no OTP yet, and the audit page says so.

Every result says which of these it is."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import core
from .core import DocError

IST = timezone(timedelta(hours=5, minutes=30))
WHAT_IT_IS = {
    "place": "An electronic signature: her signature picture placed on the page. It is not a digital (cryptographic) "
             "signature.",
    "digital": "A digital signature with her Hoola document certificate: it proves the file has not changed since it was "
               "signed. It does not prove her legal identity - for that a Class 3 DSC or Aadhaar eSign is needed.",
}


# ---------------------------------------------------------------------------------------------- storage
def _dir(sub: str) -> Path:
    from ..config import get_settings
    d = Path(get_settings().pc_files_dir).parent / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_tenant(tenant: str) -> str:
    t = re.sub(r"[^A-Za-z0-9_-]", "_", str(tenant or ""))[:80]
    if not t:
        raise DocError("Signing needs her account.")
    return t


def _seal(blob: bytes) -> bytes:
    from ..config import get_settings
    if not get_settings().secret_key:
        return b""
    from ..accounts import _fernet
    return _fernet().encrypt(blob)


def _unseal(blob: bytes) -> bytes | None:
    try:
        from ..accounts import _fernet
        return _fernet().decrypt(blob)
    except Exception:
        return None


_MEM: dict[str, bytes] = {}


def _keep(name: str, blob: bytes) -> bool:
    """Sealed on disk with SECRET_KEY; without it, in this process only (a restart forgets - said)."""
    sealed = _seal(blob)
    if sealed:
        (_dir("dockit_keys") / name).write_bytes(sealed)
        return True
    _MEM[name] = blob
    return False


def _load(name: str) -> bytes | None:
    if name in _MEM:
        return _MEM[name]
    p = _dir("dockit_keys") / name
    if p.exists():
        return _unseal(p.read_bytes())
    return None


# ---------------------------------------------------------------------------------------------- her signature
def clean_signature(img: bytes) -> bytes:
    """A photo of her signature on paper (or a drawn PNG) -> the ink on a transparent background, trimmed."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(img))
        im.load()
    except Exception:
        raise DocError("The signature must be a picture (PNG / JPG): a photo of it on white paper works.")
    im = ImageOps.exif_transpose(im).convert("RGBA")
    if max(im.size) > 1600:
        im.thumbnail((1600, 1600))
    see_through = im.getchannel("A").getextrema()[0] < 255     # a drawn signature: transparent background
    flat = Image.new("RGBA", im.size, (255, 255, 255, 255))
    flat.alpha_composite(im)
    g = flat.convert("L")
    if not see_through:
        g = ImageOps.autocontrast(g)
    alpha = g.point(lambda v: 0 if v > 175 else min(255, int((175 - v) * 2.2)))
    box = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
    if not box:
        raise DocError("No ink was found in that picture. Sign in dark ink on white paper and take the photo again.")
    ink = Image.new("RGBA", im.size, (20, 30, 90, 0))
    ink.putalpha(alpha)
    out = ink.crop(box)
    b = io.BytesIO()
    out.save(b, "PNG")
    return b.getvalue()


def save_signature(tenant: str, img: bytes, kind: str = "signature") -> dict[str, Any]:
    if kind not in ("signature", "initials", "stamp"):
        raise DocError("kind = signature | initials | stamp.")
    png = img if kind == "stamp" else clean_signature(img)
    if kind == "stamp":
        from PIL import Image
        try:
            Image.open(io.BytesIO(png)).load()
        except Exception:
            raise DocError("The stamp must be a picture (PNG / JPG).")
    kept = _keep(f"{_safe_tenant(tenant)}.{kind}.png", png)
    return {"saved": kind, "kept_after_restart": kept, "kb": core.kb(len(png))}


def saved_signature(tenant: str, kind: str = "signature") -> bytes | None:
    return _load(f"{_safe_tenant(tenant)}.{kind}.png")


def place(data: bytes, tenant: str, pages: Any = "last", x: Any = None, y: Any = None, w: Any = 45,
          kind: str = "signature", name: str = "", date: bool = True, image: bytes | None = None) -> bytes:
    """Her saved signature (or the picture given now) on the pages she names, with her name + date under it."""
    from . import edit
    img = image or saved_signature(tenant, kind)
    if img is None:
        raise DocError(f"No {kind} is saved yet. Send a photo of it on white paper and use action=signature_save.")
    if image is not None and kind != "stamp":
        img = clean_signature(image)
    items = [{"type": "image", "page": pages or "last", "x": x if x is not None else "60%",
              "y": y if y is not None else "82%", "w": w, "file_id": "__sig"}]
    under = " · ".join(t for t in (name.strip(), datetime.now(IST).strftime("%d %b %Y") if date else "") if t)
    if under:
        items.append({"type": "text", "page": pages or "last", "x": x if x is not None else "60%",
                      "y": _below(y if y is not None else "82%", 17), "text": under, "size": 8, "color": "#333333"})
    out, _ = edit.add(data, items, {"__sig": img})
    return out


def _below(y: Any, mm: float) -> Any:
    s = str(y)
    if s.endswith("%"):
        return f"{float(s[:-1]) + mm / 2.97:.1f}%"          # A4 height 297 mm
    try:
        return float(s.replace("mm", "")) + mm
    except ValueError:
        return y


# ---------------------------------------------------------------------------------------------- her certificate
def _certificate(tenant: str, name: str = "") -> tuple[Any, Any, bool]:
    """Her Hoola document certificate (RSA 3072, 5 years), made on first use."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    key_name = f"{_safe_tenant(tenant)}.cert.json"
    raw = _load(key_name)
    if raw:
        d = json.loads(raw)
        key = serialization.load_pem_private_key(d["key"].encode(), password=None)
        cert = x509.load_pem_x509_certificate(d["cert"].encode())
        return key, cert, True
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    who = (name or "Hoola document owner").strip()[:64]
    subj = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, who),
                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Hoola document certificate"),
                      x509.NameAttribute(NameOID.COUNTRY_NAME, "IN")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subj).issuer_name(subj).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=5 * 365))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=True, key_encipherment=False,
                                         data_encipherment=False, key_agreement=False, key_cert_sign=False,
                                         crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
            .sign(key, hashes.SHA256()))
    blob = json.dumps({"key": key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                serialization.NoEncryption()).decode(),
                       "cert": cert.public_bytes(serialization.Encoding.PEM).decode()}).encode()
    kept = _keep(key_name, blob)
    return key, cert, kept


def certificate_info(tenant: str) -> dict[str, Any] | None:
    raw = _load(f"{_safe_tenant(tenant)}.cert.json")
    if not raw:
        return None
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    cert = x509.load_pem_x509_certificate(json.loads(raw)["cert"].encode())
    return {"name": cert.subject.rfc4514_string(), "valid_until": cert.not_valid_after_utc.date().isoformat(),
            "fingerprint": cert.fingerprint(hashes.SHA256()).hex()[:32]}


def digital(data: bytes, tenant: str, name: str = "", reason: str = "", location: str = "", field: str = "",
            visible: bool = True, page: int = 0, box: tuple[float, float, float, float] | None = None) -> dict[str, Any]:
    """Sign with her certificate. field = an existing empty signature box; else a new one (visible stamp at the bottom
    right of the chosen page, or invisible). Signing is an incremental save, so earlier signatures stay valid."""
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import fields as F
    from pyhanko.sign import signers
    from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata
    from pyhanko.stamp import TextStampStyle
    from pyhanko_certvalidator.registry import SimpleCertificateStore
    from asn1crypto import keys as akeys, x509 as ax509
    from cryptography.hazmat.primitives import serialization
    core.check_size(data)
    key, cert, kept = _certificate(tenant, name)
    signer = signers.SimpleSigner(
        signing_cert=ax509.Certificate.load(cert.public_bytes(serialization.Encoding.DER)),
        signing_key=akeys.PrivateKeyInfo.load(key.private_bytes(serialization.Encoding.DER,
                                                                serialization.PrivateFormat.PKCS8,
                                                                serialization.NoEncryption())),
        cert_registry=SimpleCertificateStore())
    try:
        w = IncrementalPdfFileWriter(io.BytesIO(data), strict=False)
    except Exception as e:
        raise DocError(f"This PDF cannot be signed ({type(e).__name__}); a locked PDF must be unlocked first.")
    existing = {}
    try:
        for name_, value, _ref in F.enumerate_sig_fields(w, filled_status=None):
            existing[name_] = value is not None
    except Exception:
        existing = {}
    if field:
        if field not in existing:
            raise DocError(f"No signature box named '{field}'. Boxes: {', '.join(existing) or 'none'}.")
        if existing[field]:
            raise DocError(f"'{field}' is already signed.")
        fname = field
    else:
        fname = f"Hoola-{secrets.token_hex(3)}"
        n = core.page_count(data)
        pg = (page or n) - 1
        if not 0 <= pg < n:
            raise DocError(f"page {page} does not exist (the file has {n} pages).")
        if visible:
            with core.open_pdf(data) as pdf:
                mb = [float(v) for v in pdf.pages[pg].mediabox]
            bx = box or (mb[2] - 240, mb[1] + 36, mb[2] - 36, mb[1] + 96)
        else:
            bx = (0, 0, 0, 0)
        F.append_signature_field(w, F.SigFieldSpec(sig_field_name=fname, on_page=pg, box=bx))
    meta = PdfSignatureMetadata(field_name=fname, reason=(reason or "Signed with Hoola")[:200],
                                location=(location or "")[:100], name=(name or None))
    style = TextStampStyle(stamp_text="Digitally signed by %(signer)s\n%(ts)s\nHoola document certificate",
                           border_width=1)
    out = io.BytesIO()
    try:
        signers.PdfSigner(meta, signer, stamp_style=style).sign_pdf(w, output=out)
    except Exception as e:
        raise DocError(f"The signature could not be made ({type(e).__name__}: {str(e)[:120]}).")
    signed = out.getvalue()
    v = verify(signed, tenant)
    mine = [s for s in v["signatures"] if s.get("field") == fname]
    if not mine or not mine[0].get("intact") or not mine[0].get("valid"):
        raise DocError("Check failed: the new signature does not validate; nothing was delivered.")
    return {"bytes": signed, "field": fname, "certificate": certificate_info(tenant), "kept_after_restart": kept,
            "what_it_is": WHAT_IT_IS["digital"]}


def verify(data: bytes, tenant: str = "") -> dict[str, Any]:
    """Every signature: who, when, intact (file unchanged since), valid, and whether it is HER Hoola certificate."""
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext
    roots = []
    if tenant:
        raw = _load(f"{_safe_tenant(tenant)}.cert.json")
        if raw:
            from asn1crypto import pem, x509 as ax509
            _, _, der = pem.unarmor(json.loads(raw)["cert"].encode())
            roots.append(ax509.Certificate.load(der))
    try:
        r = PdfFileReader(io.BytesIO(data), strict=False)
        sigs = list(r.embedded_signatures)
    except Exception as e:
        raise DocError(f"This PDF could not be read ({type(e).__name__}).")
    rows = []
    for s in sigs[:12]:
        row: dict[str, Any] = {"field": s.field_name}
        try:
            st = validate_pdf_signature(s, ValidationContext(trust_roots=roots, allow_fetching=False))
            c = st.signing_cert
            row |= {"signer": c.subject.human_friendly if c else "", "signed_at": st.signer_reported_dt.isoformat()
                    if st.signer_reported_dt else None, "intact": bool(st.intact), "valid": bool(st.valid),
                    "her_hoola_certificate": bool(st.trusted and roots),
                    "covers_whole_file": str(getattr(st, "coverage", "")).endswith("ENTIRE_FILE")}
        except Exception as e:
            row["error"] = type(e).__name__
        rows.append(row)
    changed = [x for x in rows if x.get("intact") is False or x.get("valid") is False]
    say = ("No digital signature in this file." if not rows else
           "WARNING: the file was changed after it was signed - do not treat it as the signed original." if changed else
           "Every signature checks out: the file has not changed since it was signed.")
    return {"signatures": rows, "say": say}


# ---------------------------------------------------------------------------------------------- requests
REQ_DAYS = 15


def _req_dir() -> Path:
    return _dir("dockit_sign")


def request(tenant: str, conversation_id: str, data: bytes, name: str, signers_: list[dict], days: int = REQ_DAYS,
            message: str = "") -> dict[str, Any]:
    """signers [{name, page ('last'), x, y, w}] in signing order -> one link each; only the next in line can sign."""
    if not signers_:
        raise DocError("Who signs? signers=[{name: 'Ramesh Kumar'}, ...] in signing order.")
    if len(signers_) > 10:
        raise DocError("At most 10 signers on one document.")
    core.page_count(data)
    rid = secrets.token_hex(8)
    rows = []
    for i, s in enumerate(signers_):
        nm = str(s.get("name") or "").strip()[:80]
        if not nm:
            raise DocError("Every signer needs a name.")
        rows.append({"name": nm, "token": secrets.token_urlsafe(24), "page": s.get("page") or "last",
                     "x": s.get("x"), "y": s.get("y"), "w": s.get("w") or 45, "signed_at": None, "audit": None})
    req = {"id": rid, "tenant": tenant, "conv": conversation_id, "file_name": name, "created": time.time(),
           "expires": time.time() + max(1, min(60, int(days or REQ_DAYS))) * 86400, "signers": rows,
           "message": str(message or "")[:500], "sha_before": hashlib.sha256(data).hexdigest(), "done": False}
    (_req_dir() / f"{rid}.pdf").write_bytes(data)
    (_req_dir() / f"{rid}.json").write_text(json.dumps(req))
    return {"request_id": rid, "links": [{"name": r["name"], "link": sign_link(rid, r["token"]), "order": i + 1}
                                         for i, r in enumerate(rows)],
            "expires": datetime.fromtimestamp(req["expires"], IST).strftime("%d %b %Y")}


def sign_link(rid: str, token: str) -> str:
    from ..config import get_settings
    base = (get_settings().public_base_url or "").rstrip("/")
    return f"{base}/sign/{rid}.{token}"


def load_request(key: str) -> tuple[dict, dict, int] | None:
    m = re.fullmatch(r"([0-9a-f]{16})\.([A-Za-z0-9_-]{20,64})", key or "")
    if not m:
        return None
    p = _req_dir() / f"{m.group(1)}.json"
    if not p.exists():
        return None
    req = json.loads(p.read_text())
    for i, s in enumerate(req["signers"]):
        if secrets.compare_digest(s["token"], m.group(2)):
            return req, s, i
    return None


def _save_req(req: dict) -> None:
    (_req_dir() / f"{req['id']}.json").write_text(json.dumps(req))


def status(tenant: str, rid: str) -> dict[str, Any]:
    p = _req_dir() / f"{re.sub(r'[^0-9a-f]', '', rid)}.json"
    if not p.exists():
        raise DocError("No signing request with that id.")
    req = json.loads(p.read_text())
    if req["tenant"] != tenant:
        raise DocError("No signing request with that id.")
    return {"request_id": req["id"], "file": req["file_name"], "done": req["done"],
            "expires": datetime.fromtimestamp(req["expires"], IST).strftime("%d %b %Y"),
            "signers": [{"name": s["name"], "signed": bool(s["signed_at"]),
                         "at": datetime.fromtimestamp(s["signed_at"], IST).strftime("%d %b %Y %H:%M") if s["signed_at"]
                         else None} for s in req["signers"]]}


def cancel(tenant: str, rid: str) -> dict[str, Any]:
    st = status(tenant, rid)
    p = _req_dir() / f"{rid}.json"
    req = json.loads(p.read_text())
    req["expires"] = 0
    _save_req(req)
    return st | {"cancelled": True}


def turn_of(req: dict) -> int:
    for i, s in enumerate(req["signers"]):
        if not s["signed_at"]:
            return i
    return -1


def page_pictures(req: dict, max_pages: int = 12) -> list[str]:
    from . import convert
    data = (_req_dir() / f"{req['id']}.pdf").read_bytes()
    imgs = convert.pdf_to_images(data, f"1-{max_pages}", dpi=80, fmt="jpg")
    return ["data:image/jpeg;base64," + base64.b64encode(i["bytes"]).decode() for i in imgs]


def complete_one(req: dict, signer: dict, idx: int, png: bytes, typed_name: str, ip: str, agent: str) -> dict[str, Any]:
    """Place this signer's signature + audit row; when the last one signs, add the audit page and seal the file."""
    if req["expires"] < time.time():
        raise DocError("This signing link has expired.")
    if signer["signed_at"]:
        raise DocError("You have already signed this document.")
    if turn_of(req) != idx:
        raise DocError(f"It is {req['signers'][turn_of(req)]['name']}'s turn to sign first.")
    if not typed_name.strip():
        raise DocError("Type your full name.")
    path = _req_dir() / f"{req['id']}.pdf"
    data = path.read_bytes()
    out = place(data, req["tenant"], signer["page"], signer["x"], signer["y"], signer["w"], name=typed_name.strip(),
                image=png)
    path.write_bytes(out)
    signer["signed_at"] = time.time()
    signer["audit"] = {"typed_name": typed_name.strip()[:80], "ip": ip[:64], "agent": agent[:160],
                       "sha_after": hashlib.sha256(out).hexdigest()}
    done = turn_of(req) == -1
    result: dict[str, Any] = {"done": done}
    if done:
        sealed = _finish(req, out)
        path.write_bytes(sealed)
        req["done"] = True
        result["bytes"] = sealed
    _save_req(req)
    return result


def _finish(req: dict, data: bytes) -> bytes:
    """Audit page appended, then the whole file sealed with her certificate."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from . import organize, stamp
    b = io.BytesIO()
    c = canvas.Canvas(b, pagesize=A4)
    W, H = A4
    y = H - 60
    c.setFont("Helvetica-Bold", 15)
    c.drawString(50, y, "Signing record")
    y -= 22
    c.setFont("Helvetica", 9)
    for line in (f"Document: {req['file_name']}", f"Fingerprint before signing (SHA-256): {req['sha_before']}",
                 "Signer identity = whoever held their private signing link. No OTP / ID check was done.",
                 "The file is sealed with the sender's Hoola document certificate after the last signature."):
        stamp.draw_text(c, 50, y, line[:140], 9)
        y -= 14
    y -= 8
    for i, s in enumerate(req["signers"], 1):
        a = s["audit"] or {}
        when = datetime.fromtimestamp(s["signed_at"], IST).strftime("%d %b %Y %H:%M:%S IST") if s["signed_at"] else "-"
        c.setFont("Helvetica-Bold", 10)
        stamp.draw_text(c, 50, y, f"{i}. {s['name']}", 10, True)
        y -= 14
        for line in (f"Typed name: {a.get('typed_name', '-')}", f"Signed: {when}", f"From: {a.get('ip', '-')}",
                     f"Device: {a.get('agent', '-')[:110]}", f"Fingerprint after: {a.get('sha_after', '-')}"):
            stamp.draw_text(c, 64, y, line, 8.5)
            y -= 12
        y -= 6
    c.showPage()
    c.save()
    merged = organize.merge([("doc.pdf", data), ("record.pdf", b.getvalue())], bookmarks=False)
    return digital(merged, req["tenant"], reason="Signed by: " + ", ".join(s["name"] for s in req["signers"]),
                   visible=False)["bytes"]
