"""v0.129 Photo banao / photo badlo: pictures made or changed from her words with Google's Gemini image models.

- make: text -> picture (greeting, poster idea, product scene, illustration).
- edit: her own photo(s) (chat files, max 3) + words -> changed picture (background, colours, remove a thing, add a thing).
- quality fast (cheap, ~1K) or best (pro model). Models are tried in order; one that Google doesn't know any more (or a
  key that has no access to it) is skipped and the next one is used; the one that worked is remembered for this process.
- Every picture gets a small "AI se bana · Hoola" corner label and PNG text metadata (IT Rules 2026: synthetic media
  labelled). The cost is counted by app/usage.py like every other Gemini call.
- Refused in code before any model call: fake documents / IDs / currency / certificates / stamps, nudity, face swaps or
  pictures of famous / public people, national emblems / flag misuse.
"""
from __future__ import annotations

import io
import re
import threading
from typing import Any

FAST = ["gemini-3.1-flash-lite-image", "gemini-nano-banana-2.1", "gemini-3.1-flash-image"]
BEST = ["gemini-3-pro-image-preview", "gemini-3.1-flash-image", "gemini-nano-banana-2.1"]
ASPECTS = ["1:1", "4:5", "3:4", "9:16", "16:9", "4:3", "3:2", "2:3"]
ASPECT_WORDS = {"square": "1:1", "insta": "4:5", "instagram": "4:5", "post": "4:5", "story": "9:16", "status": "9:16",
                "reel": "9:16", "portrait": "3:4", "landscape": "16:9", "wide": "16:9", "youtube": "16:9",
                "thumbnail": "16:9", "banner": "16:9"}
# rough cost per picture in rupees (USD at 88), for the line the tool says; real cost is counted from usage
COST_INR = {"fast": 3, "best": 12}
LABEL = "AI se bana · Hoola"
MAX_INPUTS = 3
_GOOD: dict[str, str] = {}          # quality -> model that worked in this process
_LOCK = threading.Lock()


class PhotoError(Exception):
    pass


class Refused(PhotoError):
    pass


# ---------------------------------------------------------------- what Hoola never makes
_FAKE_DOC = re.compile(      # papers whose picture is almost always a forgery when "made"
    r"\b(aadhaa?r|aadhar|pan ?card|voter ?id|driving licen[cs]e|passport|ration card|identity card|marksheet|mark ?sheet|"
    r"degree certificate|stamp paper|e-?stamp|cheque|currency note|rupees? note|bank ?note|\d{2,4} (ka|ke|rs|rupee) note|"
    r"government seal|sarkari mohar|official seal|rubber stamp|signature|dastakhat|hastakshar|"
    r"आधार|पैन कार्ड|मार्कशीट|स्टांप)\b", re.I)
_WEAK_DOC = re.compile(     # fine as a design, a fake only when asked to look real / be a copy
    r"\b(certificate|diploma|invoice|bill|receipt|ticket|boarding pass|visa|salary slip|pay ?slip|bank statement|"
    r"prescription|rent agreement|id ?card|letterhead|notary|प्रमाणपत्र)\b", re.I)
_MAKE_WORDS = re.compile(r"\b(bana|banao|banaiye|make|create|generate|fake|nakli|duplicate|copy|jaisa|jaisi|edit|badlo|"
                         r"change|replace|likh|likho|daal|daalo|put|add)\b", re.I)
_REAL_LOOK = re.compile(r"\b(real|asli|original|jaisa asli|exact|same as|hubahu|official|genuine|valid|scan(ned)?)\b", re.I)
_NSFW = re.compile(r"\b(nude|nudes|naked|nangi|nanga|topless|porn|sexy|sex|bikini kiss|lingerie|undress|kapde utaar|"
                   r"without clothes|bina kapde|nsfw|erotic|hot girl|boobs|breast)\b", re.I)
_SWAP = re.compile(r"\b(face ?swap|swap (the )?face|chehra badal|chehra lagao|face lagao|deep ?fake|mera chehra .* par|"
                   r"uska chehra|chehra \w+ (upar|par|pe) lagao|someone else'?s face|face of)\b", re.I)
_PERSON = re.compile(r"\b(modi|narendra modi|rahul gandhi|amit shah|kejriwal|yogi|mamata|shah rukh|srk|salman|aamir|"
                     r"amitabh|deepika|alia bhatt|katrina|virat|kohli|dhoni|sachin tendulkar|rohit sharma|ambani|adani|ratan tata|"
                     r"elon musk|trump|biden|putin|celebrity|actor|actress|cricketer|politician|prime minister|"
                     r"chief minister|"
                     r"famous person)\b", re.I)


def problem(prompt: str, edit: bool = False, consent: bool = False) -> str:
    """'' when OK, else the plain reason Hoola won't make it."""
    t = " ".join((prompt or "").split())
    if not t:
        return "Kya banana hai, ek line mein bataiye."
    if _NSFW.search(t):
        return "Aisi (nangi / sexual) tasveer Hoola nahi banata."
    if (_FAKE_DOC.search(t) and (_MAKE_WORDS.search(t) or _REAL_LOOK.search(t) or edit)) or \
            (_WEAK_DOC.search(t) and (_REAL_LOOK.search(t) or re.search(r"\b(fake|nakli|duplicate|forge)\b", t, re.I))):
        return ("ID card, certificate, marksheet, note, bill, stamp, signature jaisi cheez ki tasveer Hoola nahi banata "
                "ya badalta: woh nakli kaagaz ban sakta hai. Poster / greeting / product photo bataiye.")
    if _SWAP.search(t):
        return "Kisi ka chehra doosre par lagana (face swap / deepfake) Hoola nahi karta."
    if _PERSON.search(t):
        return ("Asli, jaane-maane logon (neta, actor, khiladi) ki tasveer Hoola nahi banata. Apni ya apne logon ki photo "
                "badalni ho to woh photo bhejiye.")
    try:
        from .brand.rules import protected
        hit = protected(t)
    except Exception:
        hit = []
    if hit:
        return f"{hit[0]} wali tasveer Hoola nahi banata (Emblems Act / sarkari chinh)."
    return ""


def aspect_of(text: str, aspect: str = "") -> str:
    a = (aspect or "").strip().lower().replace("x", ":").replace("/", ":")
    if a in ASPECTS:
        return a
    if a in ASPECT_WORDS:
        return ASPECT_WORDS[a]
    for w, v in ASPECT_WORDS.items():
        if re.search(rf"\b{w}\b", (text or "").lower()):
            return v
    return "1:1"


def models_for(quality: str) -> list[str]:
    from .config import get_settings
    st = get_settings()
    own = [m.strip() for m in (getattr(st, f"photo_{'best' if quality == 'best' else 'fast'}_models", "") or "").split(",")
           if m.strip()]
    chain = own or (BEST if quality == "best" else FAST)
    good = _GOOD.get(quality)
    return ([good] + [m for m in chain if m != good]) if good else list(chain)


# ---------------------------------------------------------------- images in / out
def prepare_input(data: bytes) -> bytes:
    """Her photo re-encoded as JPEG <= 1600 px, EXIF / GPS dropped. Not a picture -> PhotoError."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im)
        im.load()
    except Exception:
        raise PhotoError("Yeh file photo nahi lagti; JPG / PNG / WEBP photo bhejiye.")
    if im.mode not in ("RGB", "L"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        rgba = im.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        im = bg
    im = im.convert("RGB")
    im.thumbnail((1600, 1600))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=88)
    return out.getvalue()


def label(data: bytes, text: str = LABEL) -> bytes:
    """Small corner label + PNG metadata. Returns PNG bytes."""
    from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    size = max(12, int(min(w, h) * 0.028))
    font = None
    for f in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            font = ImageFont.truetype(f, size)
            break
        except Exception:
            continue
    font = font or ImageFont.load_default()
    d = ImageDraw.Draw(im, "RGBA")
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    pad = max(4, size // 3)
    x0, y0 = w - tw - pad * 3, h - th - pad * 3
    d.rounded_rectangle((x0, y0, w - pad, h - pad), radius=pad, fill=(0, 0, 0, 120))
    d.text((x0 + pad, y0 + pad - box[1]), text, font=font, fill=(255, 255, 255, 230))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Software", "Hoola")
    meta.add_text("Description", "AI-generated image (Hoola, Google Gemini)")
    meta.add_text("ai_generated", "true")
    out = io.BytesIO()
    im.save(out, "PNG", pnginfo=meta, optimize=True)
    return out.getvalue()


# ---------------------------------------------------------------- the model call
def _client():
    from .config import get_settings
    st = get_settings()
    if not st.gemini_api_key:
        raise PhotoError("Photo banane ke liye server par GEMINI_API_KEY chahiye (VPS .env).")
    from google import genai
    return genai.Client(api_key=st.gemini_api_key)


def _skippable(e: Exception) -> bool:
    s = str(e).lower()
    return any(w in s for w in ("not found", "404", "not supported", "unsupported", "is not available", "deprecated",
                                "permission", "403", "does not exist", "invalid model", "unknown model", "no longer"))


def _config(types, aspect: str, with_aspect: bool):
    kw: dict[str, Any] = {"response_modalities": ["IMAGE", "TEXT"]}
    if with_aspect and aspect:
        try:
            kw["image_config"] = types.ImageConfig(aspect_ratio=aspect)
        except Exception:
            pass
    return types.GenerateContentConfig(**kw)


def _pull(resp) -> tuple[bytes, str]:
    text = ""
    for cand in getattr(resp, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in (getattr(content, "parts", None) or []):
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None):
                return inline.data, text
            if getattr(part, "text", None):
                text += part.text
    return b"", text


def generate(prompt: str, images: list[bytes] | None = None, aspect: str = "1:1", quality: str = "fast") -> tuple[bytes, str]:
    """Raw picture bytes + the model that made it. Raises PhotoError with a plain line."""
    from google.genai import types
    client = _client()
    quality = "best" if quality == "best" else "fast"
    parts: list[Any] = [types.Part.from_bytes(data=b, mime_type="image/jpeg") for b in (images or [])[:MAX_INPUTS]]
    instr = prompt.strip()[:1800]
    if images:
        instr = ("Edit the attached photo(s) as asked. Keep the people / things that were not asked to change as they are. "
                 "Do not add any text, logo or watermark unless asked.\nAsk: " + instr)
    else:
        instr = "Make one picture. Do not add a watermark or logo unless asked.\nAsk: " + instr
    parts.append(instr)
    last = ""
    for model in models_for(quality):
        for with_aspect in (True, False):
            try:
                r = client.models.generate_content(model=model, contents=parts, config=_config(types, aspect, with_aspect))
            except Exception as e:
                last = str(e)[:300]
                low = last.lower()
                if with_aspect and ("image_config" in low or "aspect" in low or "unknown field" in low or "invalid" in low) \
                        and not _skippable(e):
                    continue                            # model refused the aspect setting: once more without it
                if _skippable(e):
                    break                               # next model
                raise PhotoError(f"Photo nahi ban payi: {last[:160]}")
            data, said = _pull(r)
            if data:
                with _LOCK:
                    _GOOD[quality] = model
                return data, model
            fb = getattr(r, "prompt_feedback", None)
            if fb is not None and getattr(fb, "block_reason", None):
                raise Refused("Google ne yeh tasveer banane se mana kiya (safety). Doosre shabdon mein bataiye.")
            if said:
                raise PhotoError("Model ne tasveer nahi di, sirf yeh kaha: " + said.strip()[:200])
            last = "khaali jawab"
            break
    raise PhotoError("Abhi koi photo model chal nahi raha (" + (last[:120] or "pata nahi") + "). Thodi der baad try kijiye.")


def make(prompt: str, images: list[bytes] | None = None, aspect: str = "", quality: str = "fast",
         consent: bool = False) -> dict[str, Any]:
    edit = bool(images)
    why = problem(prompt, edit=edit, consent=consent)
    if why:
        raise Refused(why)
    ins = [prepare_input(b) for b in (images or [])[:MAX_INPUTS]]
    asp = aspect_of(prompt, aspect)
    raw, model = generate(prompt, ins, asp, quality)
    return {"png": label(raw), "model": model, "aspect": asp, "quality": "best" if quality == "best" else "fast",
            "edit": edit, "cost_inr": COST_INR["best" if quality == "best" else "fast"]}
