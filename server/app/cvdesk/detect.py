"""Object detection scored the way COCO scores it: predictions matched to ground truth per image and class (best IoU first, highest
score first, at most 100 detections an image), precision made monotone, average precision by 101-point interpolation, averaged over
IoU 0.50:0.95 - plus AP50 / AP75, per class, by object size (small / medium / large by area 32² and 96²), precision / recall / F1 at
her score threshold and the best one, the classes confused with each other, and where the errors are. Ground truth and predictions
as COCO JSON or as one box per line. All in code from what she pastes."""
from __future__ import annotations

import json
import re
from typing import Any

import numpy as np


class DetectError(ValueError):
    pass


IOUS = np.round(np.arange(0.5, 0.951, 0.05), 2)
REC = np.linspace(0, 1, 101)
SIZES = {"all": (0, 1e10), "small": (0, 32 ** 2), "medium": (32 ** 2, 96 ** 2), "large": (96 ** 2, 1e10)}
MAX_DET = 100
MAX_BOXES = 400_000


def _boxes_lines(text: str, pred: bool, fmt: str) -> list[dict[str, Any]]:
    out = []
    for n, raw in enumerate(str(text or "").splitlines(), 1):
        s = raw.split("#")[0].strip()
        if not s:
            continue
        parts = [p for p in re.split(r"[,\s]+", s) if p]
        if re.fullmatch(r"(image|img|file|filename|image_id)", parts[0], re.I):
            continue
        if len(parts) == 1 and not pred:
            out.append({"image": parts[0], "empty": True})
            continue
        need = 7 if pred else 6
        if len(parts) != need:
            raise DetectError(f"Line {n}: {'image class score x1 y1 x2 y2' if pred else 'image class x1 y1 x2 y2'} ({need} values), "
                              f"{'or COCO JSON' if not pred else 'or a COCO results list'}.")
        try:
            nums = [float(p) for p in parts[2:]]
        except ValueError:
            raise DetectError(f"Line {n}: the box numbers are not numbers.")
        score = nums.pop(0) if pred else 1.0
        a, b, c, d = nums
        x1, y1, x2, y2 = (a, b, a + c, b + d) if fmt == "xywh" else (a, b, c, d)
        out.append({"image": parts[0], "cls": parts[1], "score": score, "box": (x1, y1, x2, y2), "line": n})
    return out


def _coco(text: str, pred: bool) -> tuple[list[dict[str, Any]], dict[str, str]] | None:
    t = str(text or "").strip()
    if not t.startswith(("{", "[")):
        return None
    try:
        d = json.loads(t)
    except ValueError as e:
        raise DetectError(f"Not valid JSON: {e}.")
    names: dict[str, str] = {}
    if isinstance(d, dict):
        for c in d.get("categories") or []:
            names[str(c.get("id"))] = str(c.get("name") or c.get("id"))
        anns = d.get("annotations") or []
        files = {str(i.get("id")): str(i.get("file_name") or i.get("id")) for i in d.get("images") or []}
    else:
        anns, files = d, {}
    out = []
    for a in anns:
        bb = a.get("bbox")
        if not isinstance(bb, list) or len(bb) != 4:
            raise DetectError("Every annotation needs a bbox of [x, y, width, height].")
        x, y, w, h = map(float, bb)
        img = str(a.get("image_id"))
        out.append({"image": files.get(img, img), "img_id": img, "cls": str(a.get("category_id")), "score": float(a.get("score", 1.0)),
                    "box": (x, y, x + w, y + h), "crowd": bool(a.get("iscrowd")), "area": float(a.get("area") or w * h)})
    if isinstance(d, dict):
        seen = {o["img_id"] for o in out}
        out += [{"image": f, "img_id": i, "empty": True} for i, f in files.items() if i not in seen]
    return out, names


def _iou(a: np.ndarray, b: np.ndarray, crowd: np.ndarray | None = None) -> np.ndarray:
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    ab = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    union = aa[:, None] + ab[None, :] - inter
    if crowd is not None:
        union = np.where(crowd[None, :], aa[:, None], union)
    return np.where(union > 0, inter / np.maximum(union, 1e-12), 0.0)


def _match(dt: list[dict], gt: list[dict], thr: float, rng: tuple[float, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """One image, one class: per detection (score order) tp / fp / ignored, and the ground truth that counts."""
    gign = np.array([g.get("crowd", False) or not (rng[0] <= g["area"] < rng[1]) for g in gt], dtype=bool)
    order = np.argsort(gign, kind="stable")
    gt = [gt[i] for i in order]
    gign = gign[order]
    crowd = np.array([g.get("crowd", False) for g in gt], dtype=bool)
    dt = sorted(dt, key=lambda x: -x["score"])[:MAX_DET]
    ious = _iou(np.array([d["box"] for d in dt]).reshape(-1, 4), np.array([g["box"] for g in gt]).reshape(-1, 4), crowd)
    gm = np.zeros(len(gt), dtype=bool)
    tp = np.zeros(len(dt), dtype=bool)
    ign = np.zeros(len(dt), dtype=bool)
    for i in range(len(dt)):
        best, m = min(thr, 1 - 1e-10), -1
        for j in range(len(gt)):
            if gm[j] and not crowd[j]:
                continue
            if m > -1 and not gign[m] and gign[j]:
                break
            if ious[i, j] < best:
                continue
            best, m = ious[i, j], j
        if m == -1:
            a = (dt[i]["box"][2] - dt[i]["box"][0]) * (dt[i]["box"][3] - dt[i]["box"][1])
            ign[i] = not (rng[0] <= a < rng[1])
            continue
        gm[m] = True
        ign[i] = bool(gign[m])
        tp[i] = True
    return np.array([d["score"] for d in dt]), tp, ign, int((~gign).sum())


def _ap(scores: list, tps: list, igns: list, npos: int) -> tuple[float | None, np.ndarray, np.ndarray]:
    if npos == 0:
        return None, np.array([]), np.array([])
    s = np.concatenate(scores) if scores else np.array([])
    t = np.concatenate(tps) if tps else np.array([], dtype=bool)
    g = np.concatenate(igns) if igns else np.array([], dtype=bool)
    o = np.argsort(-s, kind="mergesort")
    t, g = t[o], g[o]
    keep = ~g
    tpc = np.cumsum(t & keep)
    fpc = np.cumsum(~t & keep)
    rc = tpc / npos
    pr = tpc / np.maximum(tpc + fpc, np.spacing(1))
    q = np.zeros(len(REC))
    if len(pr):
        p = pr.tolist()
        for i in range(len(p) - 1, 0, -1):
            if p[i] > p[i - 1]:
                p[i - 1] = p[i]
        idx = np.searchsorted(rc, REC, side="left")
        for k, i in enumerate(idx):
            if i < len(p):
                q[k] = p[i]
    return float(q.mean()), rc, pr


def evaluate(gt_text: str, pred_text: str, fmt: str = "xyxy", score_thr: float = 0.25, iou_thr: float = 0.5, names: str = "") -> dict[str, Any]:
    if fmt not in ("xyxy", "xywh"):
        raise DetectError("Box format: xyxy (x1 y1 x2 y2) or xywh (x y width height).")
    cg = _coco(gt_text, False)
    gt, cat = cg if cg else (_boxes_lines(gt_text, False, fmt), {})
    cp = _coco(pred_text, True)
    dt = cp[0] if cp else _boxes_lines(pred_text, True, fmt)
    gimg = {g["image"] for g in gt}
    gt = [g for g in gt if not g.get("empty")]
    if not gt:
        raise DetectError("No ground truth boxes found. One per line: image class x1 y1 x2 y2 - or COCO JSON with images, annotations, categories.")
    if not dt:
        raise DetectError("No predictions found. One per line: image class score x1 y1 x2 y2 - or a COCO results list.")
    if len(gt) + len(dt) > MAX_BOXES:
        raise DetectError(f"Up to {MAX_BOXES:,} boxes in all.")
    if cg and cp:
        fn = {str(i.get("id")): str(i.get("file_name") or i.get("id")) for i in (json.loads(gt_text).get("images") or [])}
        for d in dt:
            d["image"] = fn.get(d.get("img_id"), d["image"])
    for b in gt + dt:
        x1, y1, x2, y2 = b["box"]
        b.setdefault("area", max(0.0, x2 - x1) * max(0.0, y2 - y1))
    nm = dict(cat)
    for i, x in enumerate(n.strip() for n in str(names or "").split(",") if n.strip()):
        nm.setdefault(str(i), x)
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", fn="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": fn})   # noqa: E731
    bad_boxes = [b for b in gt + dt if b["box"][2] <= b["box"][0] or b["box"][3] <= b["box"][1]]
    if bad_boxes:
        add("bad", "Boxes", f"{len(bad_boxes)} box(es) have no width or height - check the box format ({fmt}).", "If x2 < x1 everywhere, the boxes are x y width height: switch the format.")
    dimg = {d["image"] for d in dt}
    stray = dimg - gimg
    if stray:
        add("warn", "Images", f"{len(stray)} image(s) have predictions but no ground truth ({', '.join(sorted(stray)[:4])}) - they are left out, since nothing says those images were annotated.",
            "Check the image names match; list an annotated image with no objects as a line with just its name.")
        dt = [d for d in dt if d["image"] in gimg]
    classes = sorted({g["cls"] for g in gt} | {d["cls"] for d in dt}, key=lambda c: (len(c), c))
    by: dict[tuple[str, str], dict[str, list]] = {}
    for g in gt:
        by.setdefault((g["image"], g["cls"]), {"g": [], "d": []})["g"].append(g)
    for d in dt:
        by.setdefault((d["image"], d["cls"]), {"g": [], "d": []})["d"].append(d)
    per: list[dict[str, Any]] = []
    table: dict[str, dict[str, Any]] = {}
    curves: dict[str, list] = {}
    for c in classes:
        keys = [k for k in by if k[1] == c]
        row: dict[str, Any] = {"cls": c, "name": nm.get(c, c), "gt": sum(sum(1 for g in by[k]["g"] if not g.get("crowd")) for k in keys),
                               "pred": sum(len(by[k]["d"]) for k in keys)}
        aps = {}
        for size, rng in SIZES.items():
            vals = []
            for t in IOUS:
                S, TP, IG, npos = [], [], [], 0
                for k in keys:
                    s, tp, ig, n = _match(by[k]["d"], by[k]["g"], float(t), rng)
                    S.append(s), TP.append(tp), IG.append(ig)
                    npos += n
                ap, rc, pr = _ap(S, TP, IG, npos)
                vals.append(ap)
                if size == "all" and abs(t - iou_thr) < 1e-9:
                    curves[c] = [[round(float(a), 4), round(float(b), 4)] for a, b in zip(rc[:: max(1, len(rc) // 200)], pr[:: max(1, len(pr) // 200)])]
            ok = [v for v in vals if v is not None]
            aps[size] = {"ap": float(np.mean(ok)) if ok else None, "ap50": vals[0], "ap75": vals[5]}
        row.update(ap=aps["all"]["ap"], ap50=aps["all"]["ap50"], ap75=aps["all"]["ap75"], small=aps["small"]["ap"], medium=aps["medium"]["ap"], large=aps["large"]["ap"])
        per.append(row)
        table[c] = row
    have = [r for r in per if r["gt"] > 0]
    mean = lambda k: float(np.mean([r[k] for r in have if r[k] is not None])) if [r for r in have if r[k] is not None] else None   # noqa: E731
    out: dict[str, Any] = {"map": mean("ap"), "map50": mean("ap50"), "map75": mean("ap75"), "small": mean("small"), "medium": mean("medium"), "large": mean("large"),
                           "classes": per, "iou": iou_thr, "images": len(gimg), "gt": sum(1 for g in gt if not g.get("crowd")), "pred": len(dt), "fmt": "COCO JSON" if cg else fmt}
    # at her operating point: precision / recall / F1, confusion, errors
    pts = []
    for thr in np.round(np.arange(0.05, 0.951, 0.05), 2):
        tp = fp = fn = 0
        for k, v in by.items():
            dd = [d for d in v["d"] if d["score"] >= thr]
            _, t_, _, n = _match(dd, [g for g in v["g"] if not g.get("crowd")], iou_thr, SIZES["all"])
            tp += int(t_.sum()); fp += int((~t_).sum()); fn += n - int(t_.sum())
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        pts.append({"thr": float(thr), "p": p, "r": r, "f1": 2 * p * r / (p + r) if p + r else 0.0, "tp": tp, "fp": fp, "fn": fn})
    best = max(pts, key=lambda x: x["f1"])
    at = min(pts, key=lambda x: abs(x["thr"] - score_thr))
    out.update(at=at, best=best, sweep=pts)
    conf: dict[tuple[str, str], int] = {}
    loc = dup = bg = miss = 0
    imgs: dict[str, dict[str, list]] = {}
    for g in gt:
        if not g.get("crowd"):
            imgs.setdefault(g["image"], {"g": [], "d": []})["g"].append(g)
    for d in dt:
        if d["score"] >= score_thr:
            imgs.setdefault(d["image"], {"g": [], "d": []})["d"].append(d)
    for v in imgs.values():
        G, D = v["g"], sorted(v["d"], key=lambda x: -x["score"])
        iou = _iou(np.array([d["box"] for d in D]).reshape(-1, 4), np.array([g["box"] for g in G]).reshape(-1, 4))
        used = np.zeros(len(G), dtype=bool)
        for i, d in enumerate(D):
            same = [j for j in range(len(G)) if G[j]["cls"] == d["cls"]]
            j = max(same, key=lambda j: iou[i, j], default=None)
            if j is not None and iou[i, j] >= iou_thr and not used[j]:
                used[j] = True
                continue
            if j is not None and iou[i, j] >= iou_thr:
                dup += 1
                continue
            jj = int(np.argmax(iou[i])) if len(G) else None
            if jj is not None and iou[i, jj] >= iou_thr and G[jj]["cls"] != d["cls"]:
                conf[(G[jj]["cls"], d["cls"])] = conf.get((G[jj]["cls"], d["cls"]), 0) + 1
            elif jj is not None and iou[i, jj] >= 0.1:
                loc += 1
            else:
                bg += 1
        miss += int((~used).sum())
    out["confusion"] = sorted([{"truth": nm.get(a, a), "said": nm.get(b, b), "n": n} for (a, b), n in conf.items()], key=lambda x: -x["n"])[:20]
    out["errors"] = {"wrong class": sum(conf.values()), "poorly placed box": loc, "duplicate": dup, "background": bg, "missed": miss}
    out["curves"] = {nm.get(c, c): v for c, v in curves.items()}
    for r in have:
        if r["ap50"] is not None and r["ap50"] < 0.3 and r["gt"] >= 5:
            add("warn", "Classes", f"{r['name']}: AP50 is {r['ap50'] * 100:.1f} on {r['gt']} objects - the model rarely finds it.", "More and more varied examples of it, or check its labels.", r["name"])
        if r["gt"] < 10:
            add("info", "Classes", f"{r['name']} has only {r['gt']} labelled object(s) here - its score swings a lot from one image to the next.", "", r["name"])
    no_gt = [r["name"] for r in per if r["gt"] == 0 and r["pred"]]
    if no_gt:
        add("warn", "Classes", f"The model predicts {', '.join(no_gt[:4])}, which never appears in the ground truth - left out of the mean.", "Check the class ids match between the files.")
    if out["small"] is not None and out["large"] is not None and out["small"] < 0.5 * out["large"]:
        add("warn", "Small objects", f"Small objects score {out['small'] * 100:.1f} against {out['large'] * 100:.1f} for large ones.", "A larger input size, tiling, or a model with a finer feature level.")
    e = out["errors"]
    tot = sum(e.values()) or 1
    top = max(e, key=lambda k: e[k])
    if e[top] / tot > 0.4 and e[top] > 3:
        tips = {"wrong class": "Look at the classes it confuses - similar classes may need merging or clearer labels.",
                "poorly placed box": "Boxes overlap the object but too loosely - check label tightness and train longer.",
                "duplicate": "Several boxes on one object - lower the NMS IoU threshold.", "background": "Boxes on empty background - raise the score threshold or add hard negatives.",
                "missed": "Objects not found - lower the score threshold, or add examples like the missed ones."}
        add("info", "Errors", f"Most errors at score {score_thr:g} are '{top}' ({e[top]} of {tot}).", tips[top])
    if abs(best["thr"] - at["thr"]) >= 0.1 and best["f1"] - at["f1"] > 0.03:
        add("info", "Threshold", f"A score threshold of {best['thr']:g} gives F1 {best['f1']:.3f} against {at['f1']:.3f} at {at['thr']:g}.", f"Try score_thr={best['thr']:g} (if precision and recall matter equally).")
    out["issues"] = issues
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    pc = lambda v: "—" if v is None else f"{v * 100:.1f}"   # noqa: E731
    out["verdict"] = f"mAP {pc(out['map'])} (IoU 0.50:0.95), AP50 {pc(out['map50'])}, AP75 {pc(out['map75'])} over {len(have)} class{'es' if len(have) != 1 else ''} and {len(gimg)} image{'s' if len(gimg) != 1 else ''}"
    out["note"] = ("Scored the COCO way (101-point interpolated AP, IoU 0.50:0.95, at most 100 detections an image, crowd regions ignored). "
                   "A score on a few hundred images moves a few points from one sample to the next; compare models on the same images.")
    return out
