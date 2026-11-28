"""Camera and lens worked out for a vision job: from the sensor (pixel size and resolution, or a sensor format) and the lens, the field
of view, how many pixels land on an object at a distance, the lens needed to put enough pixels on it or to cover a width, motion
blur at a speed and exposure, depth of field, and stereo depth error. A calibration file (ROS camera_info / OpenCV YAML) is read
too: focal lengths, principal point, distortion at the corners and the reprojection error. Pinhole optics, in code."""
from __future__ import annotations

import math
import re
from typing import Any


class CameraError(ValueError):
    pass


# nominal sensor sizes (mm, width x height) - the "inch" names are not real sizes; a datasheet's pixel size beats these
FORMATS = {'1/4"': (3.6, 2.7), '1/3.6"': (4.0, 3.0), '1/3"': (4.8, 3.6), '1/2.9"': (5.0, 3.7), '1/2.8"': (5.6, 3.2), '1/2.7"': (5.37, 4.04),
           '1/2.5"': (5.76, 4.29), '1/2.3"': (6.17, 4.55), '1/2"': (6.4, 4.8), '1/1.8"': (7.18, 5.32), '1/1.7"': (7.6, 5.7), '2/3"': (8.8, 6.6),
           '1/1.2"': (11.1, 6.2), '1"': (13.2, 8.8), '4/3"': (17.3, 13.0), 'aps-c': (23.5, 15.6), 'full frame': (36.0, 24.0)}
_L = {"m": 1.0, "cm": 0.01, "mm": 0.001, "um": 1e-6, "µm": 1e-6, "km": 1000.0, "in": 0.0254, "ft": 0.3048}


def _len(v: str, what: str) -> float:
    m = re.fullmatch(r"\s*([\d.]+(?:e-?\d+)?)\s*(m|cm|mm|um|µm|km|in|ft)?\s*", v, re.I)
    if not m:
        raise CameraError(f"{what}: a length with its unit, e.g. 5m or 200mm.")
    return float(m.group(1)) * _L[(m.group(2) or "m").lower()]


def _res(v: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*[x×*]\s*(\d+)\s*", v)
    if not m:
        raise CameraError("Resolution: width x height in pixels, e.g. 1920x1080.")
    return int(m.group(1)), int(m.group(2))


def _kv(line: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"([a-z_/]+)\s*[=:]\s*([^\s,]+)", line, re.I):
        out[m.group(1).lower()] = m.group(2)
    return out


def calib(text: str) -> dict[str, Any] | None:
    t = str(text or "")
    if not re.search(r"camera_matrix|\bK\s*:|!!opencv-matrix|\bfx\b", t):
        return None
    nums = lambda block: [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e[-+]?\d+)?", block, re.I)]   # noqa: E731

    def grab(*keys: str) -> list[float] | None:
        for k in keys:
            m = re.search(rf"{k}\s*:\s*(?:!!opencv-matrix)?[\s\S]*?data\s*:\s*\[([^\]]*)\]", t)
            if m:
                return nums(m.group(1))
            m = re.search(rf"\b{k}\s*:\s*\[([^\]]*)\]", t)
            if m:
                return nums(m.group(1))
        return None

    K = grab("camera_matrix", "K", "cameraMatrix", "camera_matrix_left")
    if K is None:
        fx = re.search(r"\bfx\s*[:=]\s*([\d.]+)", t)
        if not fx:
            return None
        g = {k: float(m.group(1)) for k in ("fx", "fy", "cx", "cy") if (m := re.search(rf"\b{k}\s*[:=]\s*([\d.]+)", t))}
        K = [g.get("fx", 0), 0, g.get("cx", 0), 0, g.get("fy", g.get("fx", 0)), g.get("cy", 0), 0, 0, 1]
    if len(K) < 9:
        raise CameraError("The camera matrix needs 9 numbers.")
    D = grab("distortion_coefficients", "D", "distCoeffs", "dist_coeffs") or []
    w = re.search(r"\b(?:image_width|width|cols)\s*:\s*(\d+)", t)
    h = re.search(r"\b(?:image_height|height|rows)\s*:\s*(\d+)", t)
    W = int(w.group(1)) if w else int(round(K[2] * 2))
    H = int(h.group(1)) if h else int(round(K[5] * 2))
    rms = re.search(r"(?:rms|reprojection[_ ]error|avg_reprojection_error|reproj(?:ection)?_err(?:or)?)\s*[:=]\s*([\d.]+)", t, re.I)
    model = re.search(r"distortion_model\s*:\s*(\S+)", t)
    return {"fx": K[0], "fy": K[4], "cx": K[2], "cy": K[5], "skew": K[1], "W": W, "H": H, "D": D, "rms": float(rms.group(1)) if rms else None,
            "model": model.group(1) if model else ("plumb_bob" if D else "")}


def _corner_shift(c: dict[str, Any]) -> float | None:
    D = c["D"]
    if not D or c["model"] in ("equidistant", "fisheye", "kannala_brandt"):
        return None
    k1, k2, p1, p2 = (D + [0, 0, 0, 0])[:4]
    k3 = D[4] if len(D) > 4 else 0.0
    x = (0 - c["cx"]) / c["fx"]
    y = (0 - c["cy"]) / c["fy"]
    r2 = x * x + y * y
    rad = 1 + k1 * r2 + k2 * r2 * r2 + k3 * r2 ** 3
    if len(D) >= 8:
        rad /= 1 + D[5] * r2 + D[6] * r2 * r2 + D[7] * r2 ** 3
    xd = x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
    yd = y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
    return math.hypot((xd - x) * c["fx"], (yd - y) * c["fy"])


def analyse(text: str, ask: str = "", min_px: float = 20) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", fn="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": fn})   # noqa: E731
    out: dict[str, Any] = {"answers": []}
    cam: dict[str, Any] = {}
    c = calib(text)
    lines = [l.split("#")[0].strip() for l in (str(ask or "") + "\n" + ("" if c else str(text or ""))).splitlines()]
    lines = [l for l in lines if l]
    if c:
        out["calib"] = c
        cam = {"fpx": c["fx"], "fpy": c["fy"], "W": c["W"], "H": c["H"], "src": "the calibration"}
        if abs(c["fx"] / c["fy"] - 1) > 0.02:
            add("warn", "Calibration", f"fx and fy differ by {abs(c['fx'] / c['fy'] - 1) * 100:.1f}% - square pixels usually give under 1%.", "Recalibrate with more board poses, tilted toward the camera.")
        off = math.hypot(c["cx"] - c["W"] / 2, c["cy"] - c["H"] / 2) / math.hypot(c["W"], c["H"]) * 100
        if off > 5:
            add("warn", "Calibration", f"The principal point sits {off:.1f}% of the diagonal away from the image centre.", "Usual is under 2-3%; more often means too few board views near the edges.")
        if c["rms"] is not None:
            if c["rms"] > 1:
                add("bad", "Calibration", f"Reprojection error {c['rms']:g} px - over 1 px means the calibration does not fit.", "Recapture: a flat, rigid board, sharp images, the board in every corner and tilted.")
            elif c["rms"] > 0.5:
                add("warn", "Calibration", f"Reprojection error {c['rms']:g} px - usable, but under 0.5 px is usual for a good calibration.", "")
        sh = _corner_shift(c)
        c["corner_px"] = sh
        if sh is not None and sh > 0.05 * c["W"]:
            add("info", "Distortion", f"Distortion moves the corner pixel by {sh:.0f} px - undistort before measuring anything in the image.", "cv2.undistort / image_proc rectify.")
        if c["skew"] and abs(c["skew"]) > 1e-6 * c["fx"]:
            add("info", "Calibration", "The calibration has a skew term; modern sensors have none - fix it to 0 when calibrating.", "")
    for ln in lines:
        low = ln.lower()
        kv = _kv(low)
        if low.startswith(("sensor", "camera")):
            res = kv.get("res") or kv.get("resolution") or (m.group(0) if (m := re.search(r"\d+\s*[x×]\s*\d+(?!\s*mm)", low)) else None)
            W, H = _res(res) if res else (None, None)
            pix = kv.get("pixel") or kv.get("pitch")
            fmt = next((k for k in sorted(FORMATS, key=len, reverse=True) if k in low.replace("in", '"').replace('""', '"')), None)
            mm = re.search(r"([\d.]+)\s*[x×]\s*([\d.]+)\s*mm", low)
            if W is None:
                raise CameraError(f"'{ln}': give the resolution, e.g. res=1920x1080.")
            if pix:
                p = _len(pix if re.search(r"[a-zµ]$", pix) else pix + "um", "Pixel size")
                sw, sh_ = W * p, H * p
                src = f"{p * 1e6:g} µm pixels"
            elif mm:
                sw, sh_ = float(mm.group(1)) / 1000, float(mm.group(2)) / 1000
                src = f"a {mm.group(1)} x {mm.group(2)} mm sensor"
            elif fmt:
                sw, sh_ = FORMATS[fmt][0] / 1000, FORMATS[fmt][1] / 1000
                src = f"a {fmt} sensor (nominal size)"
                add("info", "Sensor", f"Sensor formats like {fmt} are names, not sizes - the size used ({FORMATS[fmt][0]} x {FORMATS[fmt][1]} mm) is nominal.", "Give pixel= from the datasheet for exact numbers.")
            else:
                sw = sh_ = None
                src = ""
            lens = kv.get("lens") or kv.get("f") or kv.get("focal")
            fov = kv.get("fov") or kv.get("hfov")
            cam = {"W": W, "H": H, "sw": sw, "sh": sh_, "src": src}
            if lens and sw:
                f = _len(lens if re.search(r"[a-z]$", lens) else lens + "mm", "Lens")
                cam.update(f=f, fpx=f / (sw / W), fpy=f / (sh_ / H))
            elif fov:
                hf = math.radians(float(re.sub(r"[^\d.]", "", fov)))
                cam.update(fpx=W / 2 / math.tan(hf / 2), fpy=W / 2 / math.tan(hf / 2))
            continue
        if not cam:
            raise CameraError("Start with the camera: 'sensor pixel=2.9um res=1920x1080 lens=6mm' (or fov=90), or paste a calibration file.")
        need_f = "fpx" in cam
        dists = re.findall(r"(?:at|distance)\s*=?\s*([\d.]+\s*(?:m|cm|mm|km|ft)?)\b", low)
        d = _len(dists[-1], "Distance") if dists else None
        if low.startswith(("distance", "at ")) and need_f:
            wv, hv = cam["W"] / cam["fpx"] * d, cam["H"] / cam["fpy"] * d
            out["answers"].append({"q": ln, "title": f"At {d:g} m", "rows": [["Seen width x height", f"{wv:.3g} x {hv:.3g} m"], ["Pixels per metre", f"{cam['fpx'] / d:.4g}"],
                                                                             ["One pixel covers", f"{d / cam['fpx'] * 1000:.3g} mm"], ["Smallest object with " + f"{min_px:g} px", f"{min_px * d / cam['fpx'] * 100:.3g} cm"]]})
        elif low.startswith(("object", "target")) and need_f:
            size = _len(re.search(r"(?:object|target)\s+([\d.]+\s*(?:m|cm|mm)?)", low).group(1), "Object size")
            if d is None:
                raise CameraError(f"'{ln}': say at what distance, e.g. 'object 0.2m at 20m'.")
            px = size * cam["fpx"] / d
            st = "ok" if px >= min_px else "bad"
            out["answers"].append({"q": ln, "title": f"A {size * 100:g} cm object at {d:g} m", "rows": [["Pixels across it", f"{px:.1f}"],
                                   ["Detectable (≥ " + f"{min_px:g} px)", "yes" if px >= min_px else "no"], ["Farthest it stays detectable", f"{size * cam['fpx'] / min_px:.3g} m"]], "state": st})
            if px < min_px:
                add("bad", "Resolution", f"A {size * 100:g} cm object at {d:g} m gets {px:.1f} pixels - under the {min_px:g} you set as the least a detector needs.",
                    f"A longer lens, a higher resolution, or the camera nearer (within {size * cam['fpx'] / min_px:.3g} m).")
        elif low.startswith("need"):
            m = re.search(r"need\s+([\d.]+)\s*px\s+on\s+([\d.]+\s*(?:m|cm|mm)?)", low)
            if not m or d is None or not cam.get("sw"):
                raise CameraError(f"'{ln}': 'need 30px on 0.2m at 20m', with the sensor size known (pixel=).")
            px, size = float(m.group(1)), _len(m.group(2), "Object size")
            f = px * (cam["sw"] / cam["W"]) * d / size
            hf = 2 * math.degrees(math.atan(cam["sw"] / 2 / f))
            out["answers"].append({"q": ln, "title": f"{px:g} px on {size * 100:g} cm at {d:g} m", "rows": [["Lens needed", f"{f * 1000:.3g} mm or longer"], ["Its horizontal field of view", f"{hf:.3g}°"],
                                                                                                   ["Width seen there", f"{cam['sw'] / f * d:.3g} m"]]})
        elif low.startswith("cover"):
            m = re.search(r"cover\s+([\d.]+\s*(?:m|cm|mm)?)", low)
            if not m or d is None or not cam.get("sw"):
                raise CameraError(f"'{ln}': 'cover 4m at 10m', with the sensor size known (pixel=).")
            wd = _len(m.group(1), "Width")
            f = cam["sw"] * d / wd
            out["answers"].append({"q": ln, "title": f"Covering {wd:g} m at {d:g} m", "rows": [["Lens", f"{f * 1000:.3g} mm or shorter"], ["Horizontal field of view", f"{2 * math.degrees(math.atan(wd / 2 / d)):.3g}°"],
                                                                                        ["Pixels per metre there", f"{cam['W'] / wd:.4g}"]]})
        elif low.startswith(("motion", "speed")) and need_f:
            m = re.search(r"([\d.]+)\s*(m/s|km/h|mm/s)", low)
            e = re.search(r"(?:exposure|shutter)\s*=?\s*([\d.]+)\s*(ms|us|µs|s)", low)
            if not m or not e or d is None:
                raise CameraError(f"'{ln}': 'motion 10m/s exposure 1ms at 5m'.")
            v = float(m.group(1)) * {"m/s": 1, "km/h": 1 / 3.6, "mm/s": 0.001}[m.group(2)]
            ex = float(e.group(1)) * {"ms": 1e-3, "us": 1e-6, "µs": 1e-6, "s": 1}[e.group(2)]
            blur = v * ex * cam["fpx"] / d
            mx = 1.0 * d / (v * cam["fpx"])
            out["answers"].append({"q": ln, "title": f"{v:g} m/s at {d:g} m, {ex * 1000:g} ms exposure", "rows": [["Motion blur", f"{blur:.2f} px"], ["Exposure for 1 px of blur", f"{mx * 1e6:.4g} µs"]],
                                   "state": "bad" if blur > 2 else "ok"})
            if blur > 2:
                add("warn", "Motion blur", f"Motion blur of {blur:.1f} px at {v:g} m/s - edges and codes smear.", f"Shorten the exposure to about {mx * 1e6:.3g} µs (more light or gain), or use a global-shutter sensor for fast motion.")
        elif low.startswith(("dof", "focus")):
            m = re.search(r"f\s*/\s*([\d.]+)", low)
            if not m or d is None or not cam.get("f"):
                raise CameraError(f"'{ln}': 'dof f/2.8 at 3m', with the lens and pixel size known.")
            N = float(m.group(1))
            f = cam["f"]
            coc = 2 * cam["sw"] / cam["W"]
            Hh = f * f / (N * coc) + f
            near = d * (Hh - f) / (Hh + d - 2 * f)
            far = d * (Hh - f) / (Hh - d) if d < Hh else float("inf")
            out["answers"].append({"q": ln, "title": f"Focused at {d:g} m, f/{N:g}", "rows": [["Sharp from", f"{near:.3g} m"], ["Sharp to", "infinity" if far == float('inf') else f"{far:.3g} m"],
                                                                                        ["Hyperfocal distance", f"{Hh:.3g} m"], ["Blur circle allowed", f"{coc * 1e6:.3g} µm (2 pixels)"]]})
        elif low.startswith("stereo") and need_f:
            b = re.search(r"baseline\s*=?\s*([\d.]+\s*(?:m|cm|mm)?)", low)
            de = re.search(r"(?:disparity|subpixel|error)\s*=?\s*([\d.]+)\s*px", low)
            if not b or d is None:
                raise CameraError(f"'{ln}': 'stereo baseline=0.12m at 5m disparity 0.25px'.")
            B = _len(b.group(1), "Baseline")
            dd = float(de.group(1)) if de else 0.25
            disp = cam["fpx"] * B / d
            dz = d * d * dd / (cam["fpx"] * B)
            out["answers"].append({"q": ln, "title": f"Stereo, {B * 100:g} cm baseline, at {d:g} m", "rows": [["Disparity there", f"{disp:.3g} px"], ["Depth error", f"±{dz * 100:.3g} cm ({dz / d * 100:.2g}%)"],
                                                                                                    ["Range where error stays under 1%", f"{0.01 * cam['fpx'] * B / dd:.3g} m"]]})
            if dz / d > 0.05:
                add("warn", "Stereo", f"Depth error at {d:g} m is ±{dz * 100:.0f} cm ({dz / d * 100:.0f}%).", "Widen the baseline or use a longer lens; error grows with the square of the distance.")
        else:
            raise CameraError(f"'{ln}' is not a question here: distance 5m, object 0.2m at 20m, need 30px on 0.2m at 20m, cover 4m at 10m, motion 10m/s exposure 1ms at 5m, dof f/2.8 at 3m, stereo baseline=0.12m at 5m.")
    if not cam:
        raise CameraError("Start with the camera: 'sensor pixel=2.9um res=1920x1080 lens=6mm', or paste a calibration file (ROS camera_info / OpenCV YAML).")
    if "fpx" in cam:
        cam["hfov"] = 2 * math.degrees(math.atan(cam["W"] / 2 / cam["fpx"]))
        cam["vfov"] = 2 * math.degrees(math.atan(cam["H"] / 2 / cam["fpy"]))
        cam["dfov"] = 2 * math.degrees(math.atan(math.hypot(cam["W"] / 2 / cam["fpx"], cam["H"] / 2 / cam["fpy"])))
        if cam["hfov"] > 100:
            add("info", "Lens", f"A {cam['hfov']:.0f}° field of view: a pinhole model underestimates the edges of such a wide lens - use the fisheye / equidistant model to calibrate.", "")
    out["camera"] = cam
    out["min_px"] = min_px
    out["issues"] = issues
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    out["verdict"] = (f"{cam['W']}x{cam['H']}" + (f", {cam['hfov']:.1f}° x {cam['vfov']:.1f}° field of view" if cam.get("hfov") else "")
                      + (f", focal length {cam['fpx']:.1f} px" if cam.get("fpx") else "") + (f" - {len(out['answers'])} question{'s' if len(out['answers']) != 1 else ''} answered" if out["answers"] else ""))
    out["note"] = ("Pinhole optics with the numbers given: real lenses distort toward the edges and lose sharpness beyond the pixel limit "
                   "(diffraction at small apertures, lens resolution) - check a test image at the real distance.")
    return out
