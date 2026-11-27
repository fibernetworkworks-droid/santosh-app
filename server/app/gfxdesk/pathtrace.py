"""A small CPU path tracer (numpy, vectorized over pixels) for REFERENCE images: a scene as data (camera, spheres, planes, boxes,
materials: diffuse, metal, glass, light; a sky), rendered with a fixed seed so the same scene always gives the same picture.
She renders the same scene in her own engine and the desk compares the two. Not fast, not fancy: correct and repeatable.

Built-in scenes include a 'white furnace' (an albedo-1 object under a uniform sky must vanish - a classic energy test)."""
from __future__ import annotations

import base64
import io
import math
import time
from typing import Any

import numpy as np

MAX_PIXELS = 512 * 512
MAX_WORK = 512 * 512 * 64            # pixels x samples
MAX_OBJECTS = 64
KINDS = {"diffuse": 0, "metal": 1, "glass": 2, "light": 3}
EPS = 1e-4


class SceneError(ValueError):
    pass


def _v(x: Any, n: int = 3, lo: float = -1e4, hi: float = 1e4, what: str = "a vector") -> np.ndarray:
    try:
        a = np.asarray([float(t) for t in x], dtype=np.float64)
    except (TypeError, ValueError):
        raise SceneError(f"{what} must be {n} numbers")
    if a.shape != (n,) or not np.all(np.isfinite(a)) or np.any(a < lo) or np.any(a > hi):
        raise SceneError(f"{what} must be {n} numbers between {lo:g} and {hi:g}")
    return a


def _f(x: Any, lo: float, hi: float, what: str) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise SceneError(f"{what} must be a number")
    if not (lo <= v <= hi) or not math.isfinite(v):
        raise SceneError(f"{what} must be between {lo:g} and {hi:g}")
    return v


def check(scene: dict[str, Any]) -> dict[str, Any]:
    """Validate + normalise a scene. Raises SceneError naming the field."""
    if not isinstance(scene, dict):
        raise SceneError("The scene must be a JSON object")
    w = int(_f(scene.get("width", 256), 16, 1024, "width"))
    h = int(_f(scene.get("height", 256), 16, 1024, "height"))
    if w * h > MAX_PIXELS:
        raise SceneError(f"width x height must be at most {MAX_PIXELS:,} pixels")
    spp = int(_f(scene.get("samples", 16), 1, 1024, "samples"))
    if w * h * spp > MAX_WORK:
        raise SceneError(f"width x height x samples must be at most {MAX_WORK:,} - lower the samples or the size")
    bounces = int(_f(scene.get("bounces", 6), 1, 16, "bounces"))
    cam = scene.get("camera") or {}
    camera = {"from": _v(cam.get("from", [0, 1, 4]), what="camera.from"), "to": _v(cam.get("to", [0, 0.5, 0]), what="camera.to"),
              "fov": _f(cam.get("fov", 40), 5, 150, "camera.fov")}
    if np.linalg.norm(camera["from"] - camera["to"]) < 1e-6:
        raise SceneError("camera.from and camera.to must differ")
    sky = scene.get("sky") or {}
    sky_top = _v(sky.get("top", [0.6, 0.75, 1.0]), lo=0, hi=100, what="sky.top")
    sky_bottom = _v(sky.get("bottom", sky.get("top", [1, 1, 1])), lo=0, hi=100, what="sky.bottom")
    mats_in = scene.get("materials") or {}
    if not isinstance(mats_in, dict) or not mats_in:
        raise SceneError("materials must be an object of named materials")
    mats: dict[str, dict[str, Any]] = {}
    for name, m in list(mats_in.items())[:32]:
        if not isinstance(m, dict):
            raise SceneError(f"material {name} must be an object")
        kind = str(m.get("kind", "diffuse"))
        if kind not in KINDS:
            raise SceneError(f"material {name}: kind is one of {', '.join(KINDS)}")
        mats[str(name)] = {"kind": kind, "albedo": _v(m.get("albedo", [0.8, 0.8, 0.8]), lo=0, hi=1, what=f"{name}.albedo"),
                           "emit": _v(m.get("emit", [0, 0, 0]), lo=0, hi=1000, what=f"{name}.emit"),
                           "rough": _f(m.get("rough", 0.0), 0, 1, f"{name}.rough"), "ior": _f(m.get("ior", 1.5), 1.0, 3.0, f"{name}.ior")}
    objs = scene.get("objects") or []
    if not isinstance(objs, list) or not objs:
        raise SceneError("objects must be a list (sphere, plane, box)")
    if len(objs) > MAX_OBJECTS:
        raise SceneError(f"at most {MAX_OBJECTS} objects")
    out = []
    for i, o in enumerate(objs):
        if not isinstance(o, dict):
            raise SceneError(f"object {i + 1} must be an object")
        t, mat = str(o.get("type", "")), str(o.get("material", ""))
        if mat not in mats:
            raise SceneError(f"object {i + 1}: material '{mat}' is not defined")
        if t == "sphere":
            out.append({"type": t, "center": _v(o.get("center"), what=f"object {i + 1} center"),
                        "radius": _f(o.get("radius"), 1e-3, 1e4, f"object {i + 1} radius"), "material": mat})
        elif t == "plane":
            n = _v(o.get("normal", [0, 1, 0]), what=f"object {i + 1} normal")
            if np.linalg.norm(n) < 1e-9:
                raise SceneError(f"object {i + 1}: the normal cannot be zero")
            out.append({"type": t, "point": _v(o.get("point", [0, 0, 0]), what=f"object {i + 1} point"), "normal": n / np.linalg.norm(n),
                        "material": mat})
        elif t == "box":
            lo, hi = _v(o.get("min"), what=f"object {i + 1} min"), _v(o.get("max"), what=f"object {i + 1} max")
            if np.any(hi <= lo):
                raise SceneError(f"object {i + 1}: max must be larger than min on every axis")
            out.append({"type": t, "min": lo, "max": hi, "material": mat})
        else:
            raise SceneError(f"object {i + 1}: type is sphere, plane or box")
    seed = int(_f(scene.get("seed", 1), 0, 2 ** 31 - 1, "seed"))
    exposure = _f(scene.get("exposure", 1.0), 0.01, 100, "exposure")
    return {"width": w, "height": h, "samples": spp, "bounces": bounces, "camera": camera, "sky_top": sky_top, "sky_bottom": sky_bottom,
            "materials": mats, "objects": out, "seed": seed, "exposure": exposure, "tonemap": str(scene.get("tonemap", "clamp"))}


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def _rand_unit(rng: np.random.Generator, n: int) -> np.ndarray:
    z = rng.uniform(-1, 1, n)
    a = rng.uniform(0, 2 * math.pi, n)
    r = np.sqrt(1 - z * z)
    return np.stack([r * np.cos(a), r * np.sin(a), z], axis=1)


def render(scene_in: dict[str, Any]) -> dict[str, Any]:
    s = check(scene_in)
    t0 = time.perf_counter()
    W, H, spp = s["width"], s["height"], s["samples"]
    rng = np.random.default_rng(s["seed"])
    names = list(s["materials"])
    alb = np.array([s["materials"][n]["albedo"] for n in names])
    emit = np.array([s["materials"][n]["emit"] for n in names])
    kind = np.array([KINDS[s["materials"][n]["kind"]] for n in names])
    rough = np.array([s["materials"][n]["rough"] for n in names])
    ior = np.array([s["materials"][n]["ior"] for n in names])
    objs = s["objects"]
    sph = [o for o in objs if o["type"] == "sphere"]
    pln = [o for o in objs if o["type"] == "plane"]
    box = [o for o in objs if o["type"] == "box"]
    SC = np.array([o["center"] for o in sph]).reshape(-1, 3)
    SR = np.array([o["radius"] for o in sph])
    SM = np.array([names.index(o["material"]) for o in sph], dtype=int)
    PP = np.array([o["point"] for o in pln]).reshape(-1, 3)
    PN = np.array([o["normal"] for o in pln]).reshape(-1, 3)
    PM = np.array([names.index(o["material"]) for o in pln], dtype=int)
    BL = np.array([o["min"] for o in box]).reshape(-1, 3)
    BH = np.array([o["max"] for o in box]).reshape(-1, 3)
    BM = np.array([names.index(o["material"]) for o in box], dtype=int)
    cam = s["camera"]
    fwd = _unit(cam["to"] - cam["from"])
    up0 = np.array([0.0, 1.0, 0.0]) if abs(fwd[1]) < 0.999 else np.array([0.0, 0.0, 1.0])
    right = _unit(np.cross(fwd, up0))
    up = np.cross(right, fwd)
    half = math.tan(math.radians(cam["fov"]) / 2)
    aspect = W / H
    ys, xs = np.mgrid[0:H, 0:W]
    xs = xs.reshape(-1).astype(np.float64)
    ys = ys.reshape(-1).astype(np.float64)
    N = W * H
    acc = np.zeros((N, 3))
    nan_paths = 0
    for _ in range(spp):
        px = (xs + rng.uniform(0, 1, N)) / W * 2 - 1
        py = 1 - (ys + rng.uniform(0, 1, N)) / H * 2
        D = _unit(fwd[None, :] + right[None, :] * (px * half * aspect)[:, None] + up[None, :] * (py * half)[:, None])
        O = np.repeat(cam["from"][None, :], N, axis=0)
        T = np.ones((N, 3))
        L = np.zeros((N, 3))
        alive = np.ones(N, dtype=bool)
        for _b in range(s["bounces"]):
            idx = np.nonzero(alive)[0]
            if not len(idx):
                break
            o, d = O[idx], D[idx]
            n_ = len(idx)
            best = np.full(n_, np.inf)
            nrm = np.zeros((n_, 3))
            mat = np.full(n_, -1)
            if len(SR):
                oc = o[:, None, :] - SC[None, :, :]
                b = np.einsum("ij,ikj->ik", d, oc)
                c = np.einsum("ikj,ikj->ik", oc, oc) - SR[None, :] ** 2
                disc = b * b - c
                sq = np.sqrt(np.maximum(disc, 0))
                t1, t2 = -b - sq, -b + sq
                t = np.where(t1 > EPS, t1, np.where(t2 > EPS, t2, np.inf))
                t = np.where(disc > 0, t, np.inf)
                k = np.argmin(t, axis=1)
                tk = t[np.arange(n_), k]
                hit = tk < best
                best = np.where(hit, tk, best)
                p = o + d * tk[:, None]
                nn = (p - SC[k]) / SR[k][:, None]
                nrm[hit], mat[hit] = nn[hit], SM[k][hit]
            if len(PM):
                den = d @ PN.T
                t = np.einsum("kj,ikj->ik", PN, PP[None, :, :] - o[:, None, :]) / np.where(np.abs(den) > 1e-9, den, np.nan)
                t = np.where((t > EPS) & np.isfinite(t), t, np.inf)
                k = np.argmin(t, axis=1)
                tk = t[np.arange(n_), k]
                hit = tk < best
                best = np.where(hit, tk, best)
                nrm[hit], mat[hit] = PN[k][hit], PM[k][hit]
            if len(BM):
                inv = 1.0 / np.where(np.abs(d) > 1e-12, d, 1e-12)
                ta = (BL[None, :, :] - o[:, None, :]) * inv[:, None, :]
                tb = (BH[None, :, :] - o[:, None, :]) * inv[:, None, :]
                tmin = np.max(np.minimum(ta, tb), axis=2)
                tmax = np.min(np.maximum(ta, tb), axis=2)
                t = np.where(tmin > EPS, tmin, tmax)
                t = np.where((tmax >= np.maximum(tmin, EPS)) & (t > EPS), t, np.inf)
                k = np.argmin(t, axis=1)
                tk = t[np.arange(n_), k]
                hit = tk < best
                best = np.where(hit, tk, best)
                p = o + d * tk[:, None]
                c_ = (BL[k] + BH[k]) / 2
                hs = (BH[k] - BL[k]) / 2
                q = (p - c_) / hs
                ax = np.argmax(np.abs(q), axis=1)
                bn = np.zeros((n_, 3))
                bn[np.arange(n_), ax] = np.sign(q[np.arange(n_), ax])
                nrm[hit], mat[hit] = bn[hit], BM[k][hit]
            miss = mat < 0
            if miss.any():
                tt = 0.5 * (d[miss, 1] + 1)
                sky = s["sky_bottom"][None, :] * (1 - tt)[:, None] + s["sky_top"][None, :] * tt[:, None]
                L[idx[miss]] += T[idx[miss]] * sky
                alive[idx[miss]] = False
            h = ~miss
            if not h.any():
                break
            hi = idx[h]
            m = mat[h]
            p = o[h] + d[h] * best[h][:, None]
            n0 = nrm[h]
            dd = d[h]
            front = np.einsum("ij,ij->i", dd, n0) < 0
            nf = np.where(front[:, None], n0, -n0)
            L[hi] += T[hi] * emit[m]
            kk = kind[m]
            newd = np.zeros_like(dd)
            light = kk == 3
            alive[hi[light]] = False
            df = kk == 0
            if df.any():
                newd[df] = _unit(nf[df] + _rand_unit(rng, int(df.sum())))
            mt = kk == 1
            if mt.any():
                r = dd[mt] - 2 * np.einsum("ij,ij->i", dd[mt], nf[mt])[:, None] * nf[mt]
                r = _unit(r + rough[m[mt]][:, None] * _rand_unit(rng, int(mt.sum())))
                bad = np.einsum("ij,ij->i", r, nf[mt]) <= 0
                newd[mt] = r
                alive[hi[mt][bad]] = False
            gl = kk == 2
            if gl.any():
                eta = np.where(front[gl], 1.0 / ior[m[gl]], ior[m[gl]])
                cos_i = np.minimum(-np.einsum("ij,ij->i", dd[gl], nf[gl]), 1.0)
                sin2 = eta * eta * (1 - cos_i * cos_i)
                r0 = ((1 - eta) / (1 + eta)) ** 2
                fres = r0 + (1 - r0) * (1 - cos_i) ** 5
                refl = (sin2 > 1) | (rng.uniform(0, 1, int(gl.sum())) < fres)
                rdir = dd[gl] + 2 * cos_i[:, None] * nf[gl]
                tdir = eta[:, None] * dd[gl] + (eta * cos_i - np.sqrt(np.maximum(1 - sin2, 0)))[:, None] * nf[gl]
                newd[gl] = _unit(np.where(refl[:, None], rdir, tdir))
            T[hi] *= np.where(light[:, None], 1.0, alb[m])
            side = np.where((kk == 2)[:, None] & (np.einsum("ij,ij->i", newd, nf) < 0)[:, None], -nf, nf)
            O[hi] = p + side * (EPS * 10)
            D[hi] = newd
        bad = ~np.all(np.isfinite(L), axis=1)
        nan_paths += int(bad.sum())
        L[bad] = 0
        acc += L
    img = acc / spp * s["exposure"]
    lin_mean = float(img.mean())
    if s["tonemap"] == "aces":
        a, b, c, d_, e = 2.51, 0.03, 2.43, 0.59, 0.14
        img = np.clip((img * (a * img + b)) / (img * (c * img + d_) + e), 0, 1)
    out = np.clip(img, 0, 1) ** (1 / 2.2)
    px = (out.reshape(H, W, 3) * 255 + 0.5).astype(np.uint8)
    secs = round(time.perf_counter() - t0, 2)
    return {"png": png_b64(px), "width": W, "height": H, "samples": spp, "seconds": secs, "linear_mean": round(lin_mean, 5),
            "nan_paths": nan_paths, "rays": W * H * spp, "linear": img.reshape(H, W, 3)}


def png_b64(px: np.ndarray) -> str:
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(px, "RGB").save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


SCENES: dict[str, dict[str, Any]] = {
    "furnace": {"title": "White furnace (energy test)", "about": "An albedo-1 diffuse sphere under a uniform white sky must vanish: every "
                "pixel should be exactly the sky. Darker = your renderer loses energy, brighter = it creates energy.",
                "scene": {"width": 128, "height": 128, "samples": 32, "bounces": 16, "camera": {"from": [0, 0, 4], "to": [0, 0, 0], "fov": 40},
                          "sky": {"top": [0.5, 0.5, 0.5], "bottom": [0.5, 0.5, 0.5]}, "materials": {"white": {"kind": "diffuse", "albedo": [1, 1, 1]}},
                          "objects": [{"type": "sphere", "center": [0, 0, 0], "radius": 1, "material": "white"}], "seed": 7}},
    "spheres": {"title": "Three materials", "about": "Diffuse, rough metal and glass spheres on a floor under a sky - checks shading, "
                "reflection and refraction against a reference.",
                "scene": {"width": 256, "height": 160, "samples": 24, "bounces": 8, "camera": {"from": [0, 1.2, 4.2], "to": [0, 0.5, 0], "fov": 38},
                          "sky": {"top": [0.55, 0.7, 1.0], "bottom": [1, 1, 1]},
                          "materials": {"floor": {"kind": "diffuse", "albedo": [0.75, 0.75, 0.72]}, "red": {"kind": "diffuse", "albedo": [0.8, 0.25, 0.2]},
                                        "metal": {"kind": "metal", "albedo": [0.9, 0.85, 0.7], "rough": 0.15}, "glass": {"kind": "glass", "albedo": [1, 1, 1], "ior": 1.5}},
                          "objects": [{"type": "plane", "point": [0, 0, 0], "normal": [0, 1, 0], "material": "floor"},
                                      {"type": "sphere", "center": [-1.1, 0.5, 0], "radius": 0.5, "material": "red"},
                                      {"type": "sphere", "center": [0, 0.5, 0], "radius": 0.5, "material": "metal"},
                                      {"type": "sphere", "center": [1.1, 0.5, 0], "radius": 0.5, "material": "glass"}], "seed": 3}},
    "box": {"title": "Closed box with a lamp", "about": "A room lit only by an area light in the ceiling: indirect light and colour "
            "bleeding from the red and green walls. The reference is a noisy 32-sample render: compare with a blur of 2 or with SSIM, "
            "not pixel by pixel.",
            "scene": {"width": 160, "height": 160, "samples": 32, "bounces": 5, "camera": {"from": [0, 1, 3.4], "to": [0, 1, 0], "fov": 40},
                      "sky": {"top": [0, 0, 0], "bottom": [0, 0, 0]},
                      "materials": {"white": {"kind": "diffuse", "albedo": [0.73, 0.73, 0.73]}, "red": {"kind": "diffuse", "albedo": [0.65, 0.05, 0.05]},
                                    "green": {"kind": "diffuse", "albedo": [0.12, 0.45, 0.15]}, "lamp": {"kind": "light", "albedo": [1, 1, 1], "emit": [3, 3, 3]}},
                      "objects": [{"type": "plane", "point": [0, 0, 0], "normal": [0, 1, 0], "material": "white"},
                                  {"type": "plane", "point": [0, 2, 0], "normal": [0, -1, 0], "material": "white"},
                                  {"type": "plane", "point": [0, 0, -1], "normal": [0, 0, 1], "material": "white"},
                                  {"type": "plane", "point": [-1, 0, 0], "normal": [1, 0, 0], "material": "red"},
                                  {"type": "plane", "point": [1, 0, 0], "normal": [-1, 0, 0], "material": "green"},
                                  {"type": "box", "min": [-0.7, 1.97, -0.85], "max": [0.7, 2.0, 0.7], "material": "lamp"},
                                  {"type": "box", "min": [-0.6, 0, -0.6], "max": [-0.1, 0.9, -0.1], "material": "white"},
                                  {"type": "sphere", "center": [0.4, 0.3, 0.2], "radius": 0.3, "material": "white"}], "seed": 5}},
}


def furnace_check(r: dict[str, Any], sky: float = 0.5) -> dict[str, Any]:
    lin = r["linear"]
    dev = float(np.max(np.abs(lin - sky)))
    mean = float(lin.mean())
    return {"expected": sky, "mean": round(mean, 4), "max_deviation": round(dev, 4),
            "energy": "conserved" if abs(mean - sky) < 0.02 else ("lost" if mean < sky else "created")}
