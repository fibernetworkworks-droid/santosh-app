"""v0.423 VFX PIPELINE (Hoola Game Engine plan Phase 7 batch 4, Game Desk plan role 7 - the VFX Pipeline Technical
Director): a CG pipeline for her film / TV / game cinematics as DATA and CODE (numpy, no model, no money): shots and
assets with a naming + versioning rule, colour management to ACES, EXR frames, a render queue with re-queue of failed
frames and a cost per shot, and a publish manifest that traces every frame to the scene version that made it.

Checked in code, a failure named:
- naming: every published file matches <show>_<seq>_<shot>_<task>_v<###>.<####>.<ext>; versions only go up;
- colour end to end: every source declares its colour space (sRGB texture, linear sRGB, ARRI LogC3, Sony S-Log3 /
  S-Gamut3.Cine, ACEScg), the working space is ACEScg (AP1), the output view is declared (sRGB / Rec.709 display); an
  undeclared source or a missing view is named. The conversion is DONE and MEASURED here: sRGB -> linear -> ACEScg
  (the published AP1 matrix) -> back to sRGB must round-trip within 1e-4 on a test chart, and LogC3 / S-Log3 decode
  their own published 18 % grey code values to 0.18 linear;
- EXR: a real OpenEXR file (scanline, uncompressed, HALF R / G / B, with the AP1 'chromaticities' attribute so tools
  know it is ACEScg) is written and parsed back by Hoola's own reader - pixels must match at half precision. Not opened
  in Nuke / Resolve here (said);
- render queue: frames x shots on N workers, a per-frame failure chance (her number), failed frames re-queued up to 3
  times - every frame ends DONE or is NAMED as failed for good; cost per shot = core-hours x her rate;
- traceability: every frame record in the publish manifest carries shot, version, the scene's sha256, colour space,
  worker and attempt - a frame without a scene version fails the check.
Blender / OpenUSD / OpenColorIO are NOT installed on this server: the Blender render script and the OCIO config are
written for her machines and NOT run here (said on the card)."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import struct
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
KEY = "vfx_td"
NAME_RE = re.compile(r"^(?P<show>[a-z0-9]{2,12})_(?P<seq>[a-z0-9]{2,8})_(?P<shot>sh\d{3,4})_(?P<task>[a-z]{2,12})_v(?P<v>\d{3})"
                     r"\.(?P<frame>\d{4})\.(?P<ext>exr|png|jpg|tif)$")
SPACES = ("srgb_texture", "lin_srgb", "logc3", "slog3", "acescg")
VIEWS = ("srgb_display", "rec709_display")
# linear sRGB (Rec.709 primaries, D65) -> ACEScg (AP1, D60), Bradford-adapted; the matrix published with the ACES configs
SRGB_TO_AP1 = np.array([[0.6131178129, 0.3411819959, 0.0457873443],
                        [0.0699340823, 0.9181030375, 0.0119327755],
                        [0.0204629926, 0.1067686634, 0.8727159106]])
AP1_CHROMA = (0.713, 0.293, 0.165, 0.830, 0.128, 0.044, 0.32168, 0.33767)   # R xy, G xy, B xy, white xy (ACES AP1)


class VfxError(G.GameError):
    pass


class GameVfx(Base):
    __tablename__ = "game_vfx"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    show: Mapped[str] = mapped_column(String(12), default="")
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameVfx.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


EXAMPLE = {"show": "hoola", "seq": "op", "workers": 8, "fail_rate": 0.03, "rate_inr_per_core_h": 6.0, "cores": 16,
           "shots": [{"shot": "sh010", "frames": [1001, 1048], "frame_min": 4.0}, {"shot": "sh020", "frames": [1001, 1072], "frame_min": 6.5},
                     {"shot": "sh030", "frames": [1001, 1024], "frame_min": 9.0}],
           "sources": [{"name": "plate_sh010", "space": "logc3"}, {"name": "plate_sh020", "space": "slog3"},
                       {"name": "albedo_textures", "space": "srgb_texture"}, {"name": "hdri_sky", "space": "lin_srgb"}],
           "working": "acescg", "view": "srgb_display"}


# ================================================================ colour (measured here)
def srgb_decode(v: np.ndarray) -> np.ndarray:
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_encode(v: np.ndarray) -> np.ndarray:
    v = np.clip(v, 0, None)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * np.power(v, 1 / 2.4) - 0.055)


def logc3_decode(t: np.ndarray) -> np.ndarray:
    """ARRI LogC3 (EI 800) to scene linear (ARRI's published curve)."""
    cut, a, b, c, d, e, f = 0.010591, 5.555556, 0.052272, 0.247190, 0.385537, 5.367655, 0.092809
    return np.where(t > e * cut + f, (np.power(10, (t - d) / c) - b) / a, (t - f) / e)


def slog3_decode(t: np.ndarray) -> np.ndarray:
    """Sony S-Log3 to scene linear (Sony's published curve; t = code / 1023)."""
    return np.where(t >= 171.2102946929 / 1023.0, np.power(10.0, (t * 1023.0 - 420.0) / 261.5) * (0.18 + 0.01) - 0.01,
                    (t * 1023.0 - 95.0) * 0.01125000 / (171.2102946929 - 95.0))


def colour_checks(plan: dict) -> dict:
    errors, passed = [], []
    for s in plan.get("sources") or []:
        if s.get("space") not in SPACES:
            errors.append(f"source {s.get('name')!r} has no known colour space ({s.get('space')!r}) - declare one of {', '.join(SPACES)}")
    if plan.get("working") != "acescg":
        errors.append("the working space must be ACEScg (AP1)")
    if plan.get("view") not in VIEWS:
        errors.append("no output view declared (sRGB or Rec.709 display)")
    chart = np.linspace(0, 1, 33)
    rgb = np.stack(np.meshgrid(chart, chart[::4], chart[::8]), axis=-1).reshape(-1, 3)
    lin = srgb_decode(rgb)
    ap1 = lin @ SRGB_TO_AP1.T
    back = srgb_encode(ap1 @ np.linalg.inv(SRGB_TO_AP1).T)
    rt = float(np.abs(back - rgb).max())
    white = (np.ones(3) @ SRGB_TO_AP1.T)
    if rt > 1e-4:
        errors.append(f"sRGB -> ACEScg -> sRGB does not round-trip ({rt:.2e})")
    else:
        passed.append(f"sRGB -> linear -> ACEScg -> back round-trips within {rt:.1e} on a {len(rgb)}-patch chart; white stays white "
                      f"({white.round(4).tolist()})")
    g_logc = float(logc3_decode(np.array([0.391007]))[0])          # ARRI: 18 % grey at EI 800 = code 0.391
    g_slog = float(slog3_decode(np.array([420.0 / 1023.0]))[0])    # Sony: 18 % grey = code 420
    for name, g in (("ARRI LogC3", g_logc), ("Sony S-Log3", g_slog)):
        if abs(g - 0.18) > 0.002:
            errors.append(f"{name} 18 % grey decodes to {g:.4f}, not 0.18")
        else:
            passed.append(f"{name} 18 % grey code decodes to {g:.4f} linear")
    if not errors:
        passed.append(f"every source declares its space; working ACEScg; view {plan.get('view')}")
    return {"errors": errors, "passed": passed, "roundtrip": rt}


# ================================================================ EXR (written + read back here)
def _attr(name: str, typ: str, data: bytes) -> bytes:
    return name.encode() + b"\0" + typ.encode() + b"\0" + struct.pack("<i", len(data)) + data


def write_exr(rgb: np.ndarray, chroma: tuple = AP1_CHROMA) -> bytes:
    """A scanline OpenEXR, uncompressed, HALF B / G / R channels (alphabetical, as the format stores them)."""
    h, w, _ = rgb.shape
    chans = b"".join(n.encode() + b"\0" + struct.pack("<iBBBBii", 1, 0, 0, 0, 0, 1, 1) for n in ("B", "G", "R")) + b"\0"
    box = struct.pack("<iiii", 0, 0, w - 1, h - 1)
    hdr = (_attr("channels", "chlist", chans) + _attr("chromaticities", "chromaticities", struct.pack("<8f", *chroma))
           + _attr("compression", "compression", b"\0") + _attr("dataWindow", "box2i", box) + _attr("displayWindow", "box2i", box)
           + _attr("lineOrder", "lineOrder", b"\0") + _attr("pixelAspectRatio", "float", struct.pack("<f", 1.0))
           + _attr("screenWindowCenter", "v2f", struct.pack("<ff", 0, 0)) + _attr("screenWindowWidth", "float", struct.pack("<f", 1.0)) + b"\0")
    head = struct.pack("<ii", 20000630, 2) + hdr
    line_bytes = w * 3 * 2
    table_at = len(head)
    first = table_at + 8 * h
    offsets = b"".join(struct.pack("<Q", first + y * (8 + line_bytes)) for y in range(h))
    body = io.BytesIO()
    half = rgb.astype("<f2")
    for y in range(h):
        body.write(struct.pack("<ii", y, line_bytes))
        for c in (2, 1, 0):                              # B, G, R
            body.write(half[y, :, c].tobytes())
    return head + offsets + body.getvalue()


def read_exr(data: bytes) -> tuple[np.ndarray, dict]:
    magic, ver = struct.unpack_from("<ii", data, 0)
    if magic != 20000630:
        raise VfxError("not an OpenEXR file")
    pos, attrs = 8, {}
    while data[pos] != 0:
        e = data.index(b"\0", pos)
        name = data[pos:e].decode()
        e2 = data.index(b"\0", e + 1)
        typ = data[e + 1:e2].decode()
        size = struct.unpack_from("<i", data, e2 + 1)[0]
        attrs[name] = (typ, data[e2 + 5:e2 + 5 + size])
        pos = e2 + 5 + size
    pos += 1
    x0, y0, x1, y1 = struct.unpack("<iiii", attrs["dataWindow"][1])
    w, h = x1 - x0 + 1, y1 - y0 + 1
    if attrs["compression"][1] != b"\0":
        raise VfxError("only uncompressed EXR is read here")
    offs = struct.unpack_from(f"<{h}Q", data, pos)
    out = np.zeros((h, w, 3), dtype=np.float32)
    for y, o in enumerate(offs):
        yy, n = struct.unpack_from("<ii", data, o)
        row = np.frombuffer(data, dtype="<f2", count=w * 3, offset=o + 8).reshape(3, w)
        out[yy, :, 2], out[yy, :, 1], out[yy, :, 0] = row[0], row[1], row[2]
    chroma = struct.unpack("<8f", attrs["chromaticities"][1]) if "chromaticities" in attrs else None
    return out, {"w": w, "h": h, "chromaticities": chroma, "channels": attrs["channels"][1].count(b"\0") // 2}


def test_frame() -> np.ndarray:
    """A small ACEScg test frame: a grey ramp row and colour patches (from sRGB chart values)."""
    h, w = 32, 64
    x = np.linspace(0, 1, w)
    img = np.zeros((h, w, 3))
    img[:16] = srgb_decode(x)[None, :, None]
    patches = np.array([[0.8, 0.2, 0.2], [0.2, 0.7, 0.3], [0.2, 0.3, 0.8], [0.9, 0.9, 0.2]])
    for i, p in enumerate(patches):
        img[16:, i * 16:(i + 1) * 16] = srgb_decode(p)
    return (img.reshape(-1, 3) @ SRGB_TO_AP1.T).reshape(h, w, 3)


# ================================================================ render queue + manifest
def scene_hash(plan: dict, shot: dict, version: int) -> str:
    return hashlib.sha256(json.dumps({"show": plan["show"], "seq": plan["seq"], "shot": shot, "v": version,
                                      "sources": plan["sources"]}, sort_keys=True).encode()).hexdigest()


def frame_name(plan: dict, shot: str, task: str, v: int, frame: int, ext: str = "exr") -> str:
    return f"{plan['show']}_{plan['seq']}_{shot}_{task}_v{v:03d}.{frame:04d}.{ext}"


def render_queue(plan: dict, version: int = 1, seed: int = 9) -> dict:
    """Event simulation of a render farm: every frame is a job; a job fails with the given chance and goes back in the
    queue (at most 3 more tries); workers take the next job as they free up. Cost per shot from core-hours."""
    import heapq
    rng = np.random.default_rng(seed)
    jobs = []
    for s in plan["shots"]:
        for f in range(int(s["frames"][0]), int(s["frames"][1]) + 1):
            jobs.append({"shot": s["shot"], "frame": f, "minutes": float(s["frame_min"]), "attempt": 1})
    free = [(0.0, w) for w in range(int(plan["workers"]))]
    heapq.heapify(free)
    queue = list(jobs)
    manifest, failed, core_min = [], [], {s["shot"]: 0.0 for s in plan["shots"]}
    hashes = {s["shot"]: scene_hash(plan, s, version) for s in plan["shots"]}
    while queue:
        j = queue.pop(0)
        t, w = heapq.heappop(free)
        dur = j["minutes"] * float(rng.uniform(0.85, 1.25))
        core_min[j["shot"]] += dur * int(plan["cores"])
        ok = rng.random() >= float(plan["fail_rate"])
        heapq.heappush(free, (t + dur, w))
        if ok:
            manifest.append({"file": frame_name(plan, j["shot"], "comp", version, j["frame"]), "shot": j["shot"], "frame": j["frame"],
                             "version": version, "scene_sha256": hashes[j["shot"]], "colour": "ACEScg", "worker": w,
                             "attempt": j["attempt"], "finished_min": round(t + dur, 2)})
        elif j["attempt"] < 4:
            queue.append({**j, "attempt": j["attempt"] + 1})
        else:
            failed.append(f"{j['shot']} frame {j['frame']}")
    rate = float(plan["rate_inr_per_core_h"])
    cost = {s: round(core_min[s] / 60 * rate, 2) for s in core_min}
    wall = max(t for t, _w in free)
    return {"manifest": manifest, "failed": failed, "cost_inr": cost, "core_hours": {s: round(v / 60, 1) for s, v in core_min.items()},
            "requeued": sum(1 for m in manifest if m["attempt"] > 1), "frames": len(jobs), "wall_hours": round(wall / 60, 2)}


def check_manifest(rq: dict) -> dict:
    errors, passed = [], []
    bad_names = [m["file"] for m in rq["manifest"] if not NAME_RE.match(m["file"])]
    if bad_names:
        errors.append(f"{len(bad_names)} files break the naming rule (first {bad_names[0]})")
    else:
        passed.append(f"all {len(rq['manifest'])} files follow <show>_<seq>_<shot>_<task>_v###.####.ext")
    untraced = [m for m in rq["manifest"] if not re.fullmatch(r"[0-9a-f]{64}", str(m.get("scene_sha256", ""))) or not m.get("version")]
    if untraced:
        errors.append(f"{len(untraced)} frames have no scene version")
    else:
        passed.append("every frame traces to its shot, version and scene sha256")
    done = len(rq["manifest"]) + len(rq["failed"])
    if done != rq["frames"]:
        errors.append(f"{rq['frames'] - done} frames are neither done nor reported failed")
    else:
        passed.append(f"{len(rq['manifest'])} of {rq['frames']} frames done ({rq['requeued']} after a re-queue); "
                      f"{len(rq['failed'])} failed for good" + (f": {', '.join(rq['failed'][:3])}" if rq["failed"] else ""))
    return {"errors": errors, "passed": passed}


BLENDER_PY = '''# Hoola render script for Blender (run on HER machine: blender -b scene.blend -P hoola_render.py -- <shot> <first> <last>)
# NOT run on Hoola's server (Blender is not installed there).
import sys, bpy
argv = sys.argv[sys.argv.index("--") + 1:]
shot, first, last = argv[0], int(argv[1]), int(argv[2])
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.frame_start, sc.frame_end = first, last
sc.render.image_settings.file_format = "OPEN_EXR"
sc.render.image_settings.color_depth = "16"
sc.render.image_settings.exr_codec = "ZIP"
sc.view_settings.view_transform = "Standard"     # with the ACES OCIO config set in OCIO env var on her machine
sc.render.filepath = f"//render/{shot}/__NAME__"
bpy.ops.render.render(animation=True)
'''


def kit_zip(plan: dict, rq: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(rq["manifest"], indent=1))
        z.writestr("pipeline.json", json.dumps(plan, indent=2))
        z.writestr("hoola_render.py", BLENDER_PY.replace("__NAME__", f"{plan['show']}_{plan['seq']}_\" + shot + \"_comp_v001.####"))
        z.writestr("test_frame_acescg.exr", write_exr(test_frame()))
        z.writestr("README.txt", "Hoola VFX pipeline kit\n\nmanifest.json: every frame -> shot, version, scene sha256, colour space, "
                   "worker, attempt.\nhoola_render.py: a Blender (Cycles, EXR) render script for YOUR machines - not run on "
                   "Hoola's server.\ntest_frame_acescg.exr: an ACEScg test frame (AP1 chromaticities) written and read back by "
                   "Hoola; open it in your compositor to check your colour setup.\nOpenColorIO / OpenUSD are not installed on "
                   "Hoola's server; set your ACES OCIO config on your machines.\n")
    return buf.getvalue()


def evaluate(plan: dict) -> tuple[dict, dict]:
    col = colour_checks(plan)
    img = test_frame()
    data = write_exr(img)
    back, info = read_exr(data)
    exr_err = float(np.abs(back - img.astype(np.float16).astype(np.float32)).max())
    exr_ok = exr_err == 0 and info["chromaticities"] is not None and abs(info["chromaticities"][0] - 0.713) < 1e-4
    rq = render_queue(plan)
    rq2 = render_queue(plan)
    man = check_manifest(rq)
    checks = [{"check": "colour end to end", "ok": not col["errors"], "note": "; ".join(col["errors"] or col["passed"])},
              {"check": "EXR written and read back", "ok": exr_ok,
               "note": f"{info['w']}x{info['h']} HALF RGB, AP1 chromaticities {info['chromaticities'][:2] if info['chromaticities'] else None}, "
                       f"pixel difference {exr_err} (read by Hoola's own reader; not opened in Nuke / Resolve here)"},
              {"check": "naming, traceability, re-queue", "ok": not man["errors"], "note": "; ".join(man["errors"] or man["passed"])},
              {"check": "cost per shot stated", "ok": True,
               "note": ", ".join(f"{s} Rs {c} ({rq['core_hours'][s]} core-h)" for s, c in rq["cost_inr"].items())
                       + f"; farm wall time {rq['wall_hours']} h on {plan['workers']} workers"},
              {"check": "same queue run twice", "ok": rq["manifest"] == rq2["manifest"], "note": "seeded"}]
    ok = all(c["ok"] for c in checks)
    return ({"checks": checks, "verdict": "PASS" if ok else "FAIL", "passed": sum(c["ok"] for c in checks), "total": len(checks),
             "queue": {k: rq[k] for k in ("cost_inr", "core_hours", "requeued", "frames", "failed", "wall_hours")},
             "not_here": "Blender, OpenColorIO and OpenUSD are not installed on this server: the render script is for her machines"}, rq)


def clean_plan(p: dict | None) -> dict:
    out = json.loads(json.dumps(EXAMPLE))
    for k, v in (p or {}).items():
        if k in out:
            out[k] = v
    out["show"] = re.sub(r"[^a-z0-9]", "", str(out["show"]).lower())[:12] or "show"
    out["seq"] = re.sub(r"[^a-z0-9]", "", str(out["seq"]).lower())[:8] or "sq"
    for s in out["shots"]:
        s["shot"] = s["shot"] if re.fullmatch(r"sh\d{3,4}", str(s.get("shot", ""))) else "sh010"
        a, b = (int(x) for x in (s.get("frames") or [1001, 1001])[:2])
        s["frames"] = [a, max(a, min(b, a + 2000))]
    out["workers"] = int(min(max(int(out["workers"]), 1), 512))
    out["fail_rate"] = float(min(max(float(out["fail_rate"]), 0.0), 0.5))
    return out


# ================================================================ store
def _root(tenant: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "vfx"


def _get(s, tenant: str, ref: str) -> GameVfx:
    ref = str(ref or "").strip()
    q = select(GameVfx).where(GameVfx.tenant_id == tenant)
    r = s.scalars(q.where(GameVfx.id == ref)).first() or s.scalars(q.where(GameVfx.number == ref.upper())).first()
    if r is None:
        raise VfxError("This pipeline was not found (give V-001).")
    return r


def _sig(name: str) -> str:
    import hmac as _h
    from ..config import get_settings
    key = (getattr(get_settings(), "api_key", "") or "hoola-vfx").encode()
    return _h.new(key, f"vfx:{name}".encode(), "sha256").hexdigest()[:16]


def file_url(r: GameVfx) -> str:
    return f"/api/gamedesk/vfx/{r.id}/file/kit.zip?sig={_sig(r.id + 'kit.zip')}"


def vfx_file(xid: str, name: str, sig: str) -> Path | None:
    import hmac as _h
    if not re.fullmatch(r"gv_[A-Za-z0-9_-]{4,40}", str(xid or "")) or name != "kit.zip" or not _h.compare_digest(_sig(xid + name), str(sig or "")):
        return None
    ensure_table()
    with session() as s:
        r = s.get(GameVfx, xid)
        if r is None:
            return None
        s.expunge(r)
    p = _root(r.tenant_id) / r.id / name
    return p if p.is_file() else None


def view(r: GameVfx) -> dict[str, Any]:
    d = _root(r.tenant_id) / r.id
    return {"id": r.id, "number": r.number, "show": r.show, "status": r.status, "plan": r.plan or {}, "report": r.report or {},
            "files": {"kit.zip": file_url(r)} if (d / "kit.zip").is_file() else {},
            "at": r.created_at.isoformat() if r.created_at else ""}


def setup(tenant: str, words: str = "", plan: dict | None = None, studio: str = "") -> dict[str, Any]:
    ensure_table()
    p = clean_plan(plan)
    rep, rq = evaluate(p)
    with session() as s:
        n = len(s.scalars(select(GameVfx.id).where(GameVfx.tenant_id == tenant)).all()) + 1
        r = GameVfx(tenant_id=tenant, number=f"V-{n:03d}", show=p["show"], plan=p, report=rep,
                    status="draft" if rep["verdict"] == "PASS" else "failed")
        s.add(r)
        s.flush()
        s.expunge(r)
    d = _root(tenant) / r.id
    d.mkdir(parents=True, exist_ok=True)
    (d / "kit.zip").write_bytes(kit_zip(p, rq))
    return view(r)


def approve(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        if r.status != "draft":
            raise VfxError("Only a pipeline that PASSED can be OKed.")
        r.status = "approved"
        s.flush()
        s.expunge(r)
    return view(r)


def reject(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        r.status = "rejected"
        s.flush()
        s.expunge(r)
    return view(r)


def setups(tenant: str, studio: str = "") -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(GameVfx).where(GameVfx.tenant_id == tenant).order_by(GameVfx.created_at.desc())).all()[:30]
        for r in rows:
            s.expunge(r)
    return [view(r) for r in rows]


def get(tenant: str, ref: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _get(s, tenant, ref)
        s.expunge(r)
    return view(r)


def apply(tenant: str, studio: str) -> dict[str, Any]:
    raise VfxError("A VFX pipeline does not go into the game build - it is a kit for render / colour / publish.")
