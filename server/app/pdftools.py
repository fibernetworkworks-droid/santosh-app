"""v0.59 PDF kaam for the avatar: merge, pick pages, rotate, make smaller (pikepdf, MPL-2.0) and check digital
signatures (pyHanko, MIT) on PDFs from government portals / banks / companies.

Passwords: a locked PDF is never opened here (Hoola never takes passwords in chat); the owner opens it on her phone
and shares a copy. Signature check says: signed by whom, when, whether the file was changed after signing; trust in
the issuing authority (CCA India roots) is not checked, and that is said plainly.
"""
from __future__ import annotations

import io
import re
from typing import Any


class PdfError(ValueError):
    pass


def _open(data: bytes):
    import pikepdf
    try:
        return pikepdf.open(io.BytesIO(data))
    except pikepdf.PasswordError:
        raise PdfError("Is PDF par password hai. Phone par kholkar 'Print > Save as PDF' se bina password ki copy "
                       "banaiye aur woh bhejiye — password chat mein mat likhiye.")
    except Exception as e:
        raise PdfError(f"PDF khul nahi rahi ({type(e).__name__}).")


def _save(pdf, compress: bool = False) -> bytes:
    import pikepdf
    buf = io.BytesIO()
    pdf.save(buf, compress_streams=True, recompress_flate=compress,
             object_stream_mode=pikepdf.ObjectStreamMode.generate if compress else pikepdf.ObjectStreamMode.preserve)
    return buf.getvalue()


def pages_from(spec: str, n: int) -> list[int]:
    """'1-3, 5, 8-' -> zero-based page indexes (in order, no repeats)."""
    out: list[int] = []
    for part in re.split(r"[,\s]+", (spec or "").strip()):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)?-(\d+)?|(\d+)", part)
        if not m:
            raise PdfError(f"Page '{part}' samajh nahi aaya (jaise: 1-3,5).")
        if m.group(3):
            a = b = int(m.group(3))
        else:
            a = int(m.group(1) or 1)
            b = int(m.group(2) or n)
        for p in range(a, b + 1):
            if 1 <= p <= n and p - 1 not in out:
                out.append(p - 1)
    if not out:
        raise PdfError(f"In pages mein se koi nahi mila (PDF mein {n} pages hain).")
    return out


def info(data: bytes) -> dict[str, Any]:
    pdf = _open(data)
    with pdf:
        sigs = 0
        try:
            for f in pdf.Root.get("/AcroForm", {}).get("/Fields", []):
                if f.get("/FT") == "/Sig":
                    sigs += 1
        except Exception:
            pass
        return {"pages": len(pdf.pages), "size": len(data), "signatures": sigs,
                "title": str(pdf.docinfo.get("/Title", "")) if pdf.docinfo else ""}


def merge(files: list[tuple[str, bytes]]) -> bytes:
    import pikepdf
    if len(files) < 2:
        raise PdfError("Jodne ke liye kam se kam 2 PDF chahiye.")
    out = pikepdf.new()
    keep = []                       # sources must stay open until the merged file is saved
    for name, data in files:
        src = _open(data)
        keep.append(src)
        out.pages.extend(src.pages)
    return _save(out)


def pick(data: bytes, spec: str) -> bytes:
    import pikepdf
    src = _open(data)
    idx = pages_from(spec, len(src.pages))
    out = pikepdf.new()
    for i in idx:
        out.pages.append(src.pages[i])
    return _save(out)


def rotate(data: bytes, degrees: int, spec: str = "") -> bytes:
    if degrees % 90:
        raise PdfError("Sirf 90 / 180 / 270 degree ghuma sakte hain.")
    pdf = _open(data)
    idx = pages_from(spec, len(pdf.pages)) if spec else range(len(pdf.pages))
    for i in idx:
        pdf.pages[i].rotate(degrees, relative=True)
    return _save(pdf)


def shrink(data: bytes, max_side: int = 1600, quality: int = 62) -> bytes:
    """Smaller PDF: big photos inside are re-saved as JPEG (max_side px), streams packed. Text stays sharp."""
    import pikepdf
    from PIL import Image
    pdf = _open(data)
    done = set()
    for page in pdf.pages:
        imgs = page.get_images() if hasattr(page, "get_images") else page.images
        for _, raw in list(imgs.items()):
            if raw.objgen in done:
                continue
            done.add(raw.objgen)
            try:
                im = pikepdf.PdfImage(raw)
                if im.width * im.height < 600 * 600 or raw.get("/SMask") is not None or raw.get("/Mask") is not None:
                    continue
                pil = im.as_pil_image()
                if pil.mode not in ("RGB", "L"):
                    pil = pil.convert("RGB")
                if max(pil.size) > max_side:
                    pil.thumbnail((max_side, max_side), Image.LANCZOS)
                buf = io.BytesIO()
                pil.save(buf, "JPEG", quality=quality, optimize=True)
                if buf.tell() >= len(raw.read_raw_bytes()):
                    continue
                raw.write(buf.getvalue(), filter=pikepdf.Name.DCTDecode)
                raw.Width, raw.Height = pil.size
                raw.ColorSpace = pikepdf.Name.DeviceGray if pil.mode == "L" else pikepdf.Name.DeviceRGB
                raw.BitsPerComponent = 8
                for k in ("/DecodeParms", "/Decode"):
                    if k in raw:
                        del raw[k]
            except Exception:
                continue
    out = _save(pdf, compress=True)
    return out if len(out) < len(data) else data


def verify(data: bytes) -> dict[str, Any]:
    """Digital signatures inside the PDF: who, when, intact (not changed after signing), covers the whole file."""
    try:
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign.validation import validate_pdf_signature
        from pyhanko_certvalidator import ValidationContext
    except Exception:
        return {"available": False, "say": "Signature check is server par abhi install nahi hai (pip install pyhanko)."}
    try:
        r = PdfFileReader(io.BytesIO(data))
        sigs = list(r.embedded_signatures)
    except Exception as e:
        raise PdfError(f"PDF padh nahi paye ({type(e).__name__}).")
    if not sigs:
        return {"available": True, "signatures": [], "say": "Is PDF mein koi digital signature nahi hai."}
    out = []
    for s in sigs[:6]:
        row: dict[str, Any] = {"field": s.field_name}
        try:
            st = validate_pdf_signature(s, ValidationContext(trust_roots=[], allow_fetching=False))
            cert = st.signing_cert
            row |= {"signer": cert.subject.human_friendly if cert else "", "issuer": cert.issuer.human_friendly if cert else "",
                    "signed_at": st.signer_reported_dt.isoformat() if st.signer_reported_dt else None,
                    "intact": bool(st.intact), "crypto_ok": bool(st.valid), "trusted": bool(st.trusted),
                    "whole_file": str(getattr(st, "coverage", "")).endswith("ENTIRE_FILE")}
        except Exception as e:
            row["error"] = type(e).__name__
        out.append(row)
    changed = [x for x in out if x.get("intact") is False or x.get("crypto_ok") is False]
    later = [x for x in out if x.get("intact") and not x.get("whole_file")]
    say = ("⚠️ Signature ke baad PDF badli gayi hai — isse asli mat maaniye." if changed else
           "Signature sahi hai: sign ke baad file nahi badli." + (" (Sign ke baad kuch pages / form jode gaye hain.)" if later else ""))
    return {"available": True, "signatures": out, "say": say + " Sign karne wali authority par bharosa (CCA India) yahan check nahi hota."}
