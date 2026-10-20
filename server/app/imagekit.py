"""v0.51 Photos the avatar can make from the owner's photos.

clean_background(data, color)   rembg (MIT, models u2net / isnet): cut the subject out, put it on white or a colour
                                 (shop / saree / product photos). Model downloads once (~170 MB) on first use.
id_photo(data, size, color)     HivisionIDPhotos (Apache-2.0) running as a local service (HIVISION_URL): face-aware crop
                                 to passport / visa / exam-form size + plain background + a 4x6 print sheet.
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Any

log = logging.getLogger("santosh.imagekit")

# name -> (height_px, width_px) at 300 dpi
SIZES = {
    "india_passport": (531, 413), "passport": (531, 413),         # 35 x 45 mm
    "us_visa": (600, 600), "us_passport": (600, 600),              # 2 x 2 inch
    "schengen_visa": (531, 413), "uk_visa": (531, 413),
    "pan_card": (295, 213),                                        # 25 x 35 mm
    "exam_form": (531, 413), "stamp": (295, 236), "one_inch": (413, 295),
}
COLORS = {"white": "ffffff", "blue": "438edb", "light_blue": "a6c8ea", "red": "d74532", "grey": "e5e5e5", "gray": "e5e5e5"}
_SESSION = None


class ImageError(Exception):
    pass


def _hex(color: str) -> str:
    c = (color or "white").strip().lower().lstrip("#")
    c = COLORS.get(c, c)
    if len(c) != 6 or any(ch not in "0123456789abcdef" for ch in c):
        c = "ffffff"
    return c


def clean_background(data: bytes, color: str = "white", model: str = "isnet-general-use") -> bytes:
    global _SESSION
    try:
        from rembg import new_session, remove
    except Exception:
        raise ImageError("Background hatane ka tool (rembg) server par nahi hai: pip install rembg")
    from PIL import Image, ImageOps
    if _SESSION is None:
        _SESSION = new_session(model)
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGBA")
    img.thumbnail((2048, 2048))
    cut = remove(img, session=_SESSION)
    c = _hex(color)
    bg = Image.new("RGBA", cut.size, tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,))
    bg.alpha_composite(cut)
    out = io.BytesIO()
    bg.convert("RGB").save(out, "JPEG", quality=92)
    return out.getvalue()


def id_photo(data: bytes, size: str = "india_passport", color: str = "white") -> dict[str, bytes]:
    from .config import get_settings
    url = (getattr(get_settings(), "hivision_url", "") or "").rstrip("/")
    if not url:
        raise ImageError("ID photo service set nahi hai (HIVISION_URL). VPS par: docker run -d -p 127.0.0.1:8085:8080 "
                         "linzeyi/hivision_idphotos python3 deploy_api.py")
    h, w = SIZES.get((size or "").lower().replace(" ", "_"), SIZES["india_passport"])
    import httpx
    try:
        r = httpx.post(f"{url}/idphoto", files={"input_image": ("photo.jpg", data, "image/jpeg")},
                       data={"height": h, "width": w, "hd": "true"}, timeout=120)
        j = r.json()
    except Exception as e:
        raise ImageError(f"ID photo service se jawab nahi aaya: {type(e).__name__}")
    if not j.get("status"):
        raise ImageError("Photo mein ek saaf chehra nahi mila. Seedha camera ki taraf, achhi roshni mein photo lijiye.")
    std = j.get("image_base64_standard") or j.get("image_base64") or ""
    std = std.split(",", 1)[-1]
    try:
        b = httpx.post(f"{url}/add_background", data={"input_image_base64": std, "color": _hex(color)}, timeout=120).json()
        single = (b.get("image_base64") or "").split(",", 1)[-1]
        sheet = httpx.post(f"{url}/generate_layout_photos", data={"input_image_base64": single, "height": h, "width": w},
                           timeout=120).json()
        sheet_b = (sheet.get("image_base64") or "").split(",", 1)[-1]
    except Exception as e:
        raise ImageError(f"ID photo ka background / sheet nahi ban paya: {type(e).__name__}")
    out = {"photo": base64.b64decode(single)}
    if sheet_b:
        out["sheet"] = base64.b64decode(sheet_b)
    return out


def sizes() -> list[str]:
    return sorted(SIZES)
