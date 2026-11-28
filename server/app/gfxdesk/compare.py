"""Compare two images the way rendering tests do: PSNR, SSIM, mean / max error, the share of pixels over a threshold, and a heat
map of where they differ. Optional blur first, so the noise of a path-traced reference does not count as a difference."""
from __future__ import annotations

import base64
import io
import math
from typing import Any

import numpy as np

MAX_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 4096 * 4096


class CompareError(ValueError):
    pass


def load(data: str | bytes) -> np.ndarray:
    """A data URL / base64 / raw bytes (PNG, JPEG, WebP, BMP) -> float RGB in [0, 1]."""
    from PIL import Image
    if isinstance(data, str):
        s = data.split(",", 1)[1] if data.startswith("data:") else data
        try:
            raw = base64.b64decode(s, validate=False)
        except Exception:   # noqa: BLE001
            raise CompareError("That is not an image.")
    else:
        raw = bytes(data)
    if not raw:
        raise CompareError("The image is empty.")
    if len(raw) > MAX_BYTES:
        raise CompareError("An image may be at most 12 MB.")
    try:
        im = Image.open(io.BytesIO(raw))
        if im.width * im.height > MAX_PIXELS:
            raise CompareError("An image may be at most 4096 x 4096 pixels.")
        im = im.convert("RGB")
    except CompareError:
        raise
    except Exception:   # noqa: BLE001
        raise CompareError("That file is not an image Hoola can read (PNG, JPEG, WebP or BMP).")
    return np.asarray(im, dtype=np.float64) / 255.0


def _box(x: np.ndarray, r: int) -> np.ndarray:
    """A box blur of radius r over the two image axes (summed-area table)."""
    if r <= 0:
        return x
    k = 2 * r + 1
    pad = np.pad(x, ((r + 1, r), (r + 1, r)) + ((0, 0),) * (x.ndim - 2), mode="edge")
    c = pad.cumsum(0).cumsum(1)
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def _lum(x: np.ndarray) -> np.ndarray:
    return x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722


def ssim(a: np.ndarray, b: np.ndarray, r: int = 3) -> float:
    x, y = _lum(a), _lum(b)
    mx, my = _box(x, r), _box(y, r)
    sxx = _box(x * x, r) - mx * mx
    syy = _box(y * y, r) - my * my
    sxy = _box(x * y, r) - mx * my
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    m = ((2 * mx * my + c1) * (2 * sxy + c2)) / ((mx * mx + my * my + c1) * (sxx + syy + c2))
    return float(np.clip(m, -1, 1).mean())


def heat(diff: np.ndarray, scale: float) -> str:
    """black -> violet -> orange -> yellow by error, as a PNG data URL"""
    from PIL import Image
    v = np.clip(diff / max(scale, 1e-6), 0, 1)
    stops = np.array([[0.04, 0.04, 0.06], [0.42, 0.16, 0.72], [0.96, 0.45, 0.15], [1.0, 0.95, 0.55]])
    pos = v * (len(stops) - 1)
    i = np.minimum(pos.astype(int), len(stops) - 2)
    f = (pos - i)[..., None]
    rgb = stops[i] * (1 - f) + stops[i + 1] * f
    buf = io.BytesIO()
    Image.fromarray((rgb * 255 + 0.5).astype(np.uint8), "RGB").save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def compare(a_data: Any, b_data: Any, threshold: float = 0.05, blur: int = 0, psnr_min: float = 35.0, ssim_min: float = 0.98) -> dict[str, Any]:
    a = a_data if isinstance(a_data, np.ndarray) else load(a_data)
    b = b_data if isinstance(b_data, np.ndarray) else load(b_data)
    if a.shape != b.shape:
        raise CompareError(f"The images are different sizes ({a.shape[1]} x {a.shape[0]} and {b.shape[1]} x {b.shape[0]}): render both at "
                           "the same size.")
    blur = max(0, min(int(blur or 0), 8))
    if blur:
        a, b = _box(a, blur), _box(b, blur)
    d = np.abs(a - b)
    dm = d.max(axis=2)
    mse = float(np.mean((a - b) ** 2))
    psnr = float("inf") if mse == 0 else 10 * math.log10(1.0 / mse)
    s = ssim(a, b)
    over = float((dm > threshold).mean())
    passed = (psnr >= psnr_min) and (s >= ssim_min)
    rows = []
    h, w = dm.shape
    gy, gx = max(1, h // 8), max(1, w // 8)
    for yy in range(0, h, gy):
        for xx in range(0, w, gx):
            cell = dm[yy:yy + gy, xx:xx + gx]
            rows.append({"x": xx, "y": yy, "w": cell.shape[1], "h": cell.shape[0], "mean": float(cell.mean())})
    worst = sorted(rows, key=lambda r: -r["mean"])[:3]
    return {"width": w, "height": h, "psnr": None if math.isinf(psnr) else round(psnr, 2), "identical": mse == 0,
            "ssim": round(s, 5), "mean_error": round(float(d.mean()), 5), "max_error": round(float(d.max()), 4),
            "over_share": round(over, 5), "threshold": threshold, "blur": blur, "psnr_min": psnr_min, "ssim_min": ssim_min,
            "passed": passed, "heatmap": heat(dm, max(threshold * 4, 1e-3)),
            "worst": [{**r, "mean": round(r["mean"], 4)} for r in worst if r["mean"] > 0],
            "verdict": ("The same image." if mse == 0 else
                        f"Within your limits (PSNR {psnr:.1f} dB, SSIM {s:.4f})." if passed else
                        f"Different: PSNR {psnr:.1f} dB (limit {psnr_min:g}), SSIM {s:.4f} (limit {ssim_min:g}); "
                        f"{over * 100:.1f}% of pixels differ by more than {threshold:g}.")}
