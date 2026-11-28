"""A labelled dataset checked before anyone trains on it: YOLO label files (pasted together, one '## path/file.txt' header each) or
a COCO JSON. Class counts per split and how lopsided they are, boxes outside the image or with no size, boxes too small to learn,
the same object labelled twice, one object given two classes, unknown class ids, images with no labels, object sizes small /
medium / large, and the same image in two splits (a leak that inflates every score). All read from the label text; no image is
opened."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any


class DatasetError(ValueError):
    pass


SPLITS = ("train", "val", "valid", "validation", "test")


def _split(path: str) -> str:
    for seg in re.split(r"[\\/]", path.lower()):
        if seg in SPLITS:
            return {"valid": "val", "validation": "val"}.get(seg, seg)
    return "all"


def _stem(path: str) -> str:
    return re.sub(r"\.[a-z0-9]+$", "", re.split(r"[\\/]", path)[-1].lower())


def _iou(a: tuple, b: tuple) -> float:
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0


def _yolo(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    images: list[dict[str, Any]] = []
    names: list[str] = []
    cur: dict[str, Any] | None = None
    in_names = False
    for n, raw in enumerate(str(text or "").splitlines(), 1):
        s = raw.strip()
        if not s:
            continue
        m = re.match(r"^(?:##|==>|---)\s*(.+?)\s*(?:<==)?$", s)
        if m:
            in_names = bool(re.search(r"(^|[\\/])(classes\.txt|[\w-]*\.names)$", m.group(1), re.I))
            if in_names:
                continue
            cur = {"name": m.group(1), "boxes": [], "line": n}
            images.append(cur)
            continue
        if in_names:
            names.append(s)
            continue
        if s.startswith("#"):
            continue
        p = s.split()
        if cur is None:
            cur = {"name": "labels.txt", "boxes": [], "line": n}
            images.append(cur)
        if len(p) not in (5, 6) and not (len(p) > 6 and len(p) % 2 == 1):
            raise DatasetError(f"Line {n}: a YOLO label is 'class cx cy w h' (normalised 0-1); paste each file under a '## path/name.txt' header.")
        try:
            nums = [float(x) for x in p[1:]]
        except ValueError:
            raise DatasetError(f"Line {n}: the numbers are not numbers.")
        if len(p) > 6:
            xs, ys = nums[0::2], nums[1::2]
            cx, cy, w, h = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)
        else:
            cx, cy, w, h = nums[:4]
        cur["boxes"].append({"cls": p[0], "box": (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), "w": w, "h": h, "line": n})
    return images, names


def _coco(d: dict) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    cats = {str(c.get("id")): str(c.get("name") or c.get("id")) for c in d.get("categories") or []}
    imgs = {str(i.get("id")): {"name": str(i.get("file_name") or i.get("id")), "W": i.get("width"), "H": i.get("height"), "boxes": []} for i in d.get("images") or []}
    probs: list[str] = []
    names = Counter(v["name"] for v in imgs.values())
    dupn = [k for k, v in names.items() if v > 1]
    if dupn:
        probs.append(f"dup:{len(dupn)}:{', '.join(dupn[:3])}")
    for a in d.get("annotations") or []:
        im = imgs.get(str(a.get("image_id")))
        if im is None:
            probs.append(f"noimg:{a.get('id')}")
            continue
        bb = a.get("bbox") or []
        if len(bb) != 4:
            probs.append(f"nobox:{a.get('id')}")
            continue
        x, y, w, h = map(float, bb)
        W, H = im["W"] or 1, im["H"] or 1
        im["boxes"].append({"cls": str(a.get("category_id")), "box": (x / W, y / H, (x + w) / W, (y + h) / H), "w": w / W, "h": h / H, "line": a.get("id"),
                            "crowd": bool(a.get("iscrowd")), "known": str(a.get("category_id")) in cats})
    return list(imgs.values()), cats, probs


def check(text: str, names: str = "", img_size: str = "", min_px: float = 8) -> dict[str, Any]:
    t = str(text or "").strip()
    if not t:
        raise DatasetError("Paste the label files (YOLO, one '## path/name.txt' header each) or a COCO JSON.")
    if len(t) > 50_000_000:
        raise DatasetError("Up to 50 MB of labels.")
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, txt, fix="", fn="": issues.append({"sev": sev, "area": area, "text": txt, "fix": fix, "fn": fn})   # noqa: E731
    W = H = None
    if str(img_size or "").strip():
        m = re.fullmatch(r"\s*(\d+)\s*[x×*,]\s*(\d+)\s*", str(img_size))
        if not m:
            raise DatasetError("Image size: width x height, e.g. 1920x1080.")
        W, H = int(m.group(1)), int(m.group(2))
    nm: dict[str, str] = {}
    if t.startswith("{"):
        try:
            d = json.loads(t)
        except ValueError as e:
            raise DatasetError(f"Not valid JSON: {e}.")
        imgs, nm, probs = _coco(d)
        fmt = "COCO JSON"
        for p in probs:
            k, _, rest = p.partition(":")
            if k == "noimg":
                add("bad", "Links", f"An annotation (id {rest}) points to an image that is not in the images list.", "Remove it or add the image.")
            elif k == "nobox":
                add("bad", "Boxes", f"An annotation (id {rest}) has no bbox of four numbers.", "")
            elif k == "dup":
                n_, _, ex = rest.partition(":")
                add("warn", "Images", f"{n_} file name(s) appear under two image ids ({ex}).", "One image, one id.")
        unknown = sum(1 for im in imgs for b in im["boxes"] if not b.get("known"))
        if unknown:
            add("bad", "Classes", f"{unknown} annotation(s) use a category id that is not in categories.", "Add the category or fix the id.")
        sized = all(im["W"] and im["H"] for im in imgs)
    else:
        imgs, found = _yolo(t)
        fmt = "YOLO"
        if found and not str(names or "").strip():
            names = ",".join(found)
        sized = W is not None
    for i, x in enumerate(n.strip() for n in re.split(r"[,\n]", str(names or "")) if n.strip()):
        nm.setdefault(str(i), x)
    if not imgs:
        raise DatasetError("No label files or images found.")
    split_of = {im["name"]: _split(im["name"]) for im in imgs}
    cls_count: Counter = Counter()
    cls_imgs: dict[str, set] = defaultdict(set)
    cls_split: dict[str, Counter] = defaultdict(Counter)
    sizes: dict[str, Counter] = defaultdict(Counter)
    per_img = []
    bad_out, zero, tiny, dup, clash, aspect, badcls = [], [], [], [], [], [], []
    for im in imgs:
        bx = im["boxes"]
        per_img.append(len(bx))
        sw, sh = (im.get("W") or W, im.get("H") or H) if fmt == "COCO JSON" else (W, H)
        for b in bx:
            c = b["cls"]
            if fmt == "YOLO":
                if not re.fullmatch(r"\d+", c):
                    badcls.append(f"{im['name']} line {b['line']}")
                elif nm and c not in nm:
                    badcls.append(f"{im['name']} line {b['line']} (class {c})")
            cls_count[c] += 1
            cls_imgs[c].add(im["name"])
            cls_split[c][split_of[im["name"]]] += 1
            x1, y1, x2, y2 = b["box"]
            where = f"{im['name']} {'line' if fmt == 'YOLO' else 'annotation'} {b['line']}"
            if b["w"] <= 0 or b["h"] <= 0:
                zero.append(where)
                continue
            if x1 < -0.002 or y1 < -0.002 or x2 > 1.002 or y2 > 1.002:
                bad_out.append(where)
            if sw and sh:
                pw, ph = b["w"] * sw, b["h"] * sh
                area = pw * ph
                sizes[c]["small" if area < 32 ** 2 else "medium" if area < 96 ** 2 else "large"] += 1
                if min(pw, ph) < min_px:
                    tiny.append(where)
                if max(pw, ph) / max(min(pw, ph), 1e-9) > 20:
                    aspect.append(where)
            elif min(b["w"], b["h"]) < 0.005:
                tiny.append(where)
        for i in range(len(bx)):
            for j in range(i + 1, len(bx)):
                if bx[i]["w"] > 0 and bx[j]["w"] > 0 and _iou(bx[i]["box"], bx[j]["box"]) > 0.9:
                    (dup if bx[i]["cls"] == bx[j]["cls"] else clash).append(f"{im['name']} ({nm.get(bx[i]['cls'], bx[i]['cls'])} / {nm.get(bx[j]['cls'], bx[j]['cls'])})")
    ex = lambda xs: ", ".join(xs[:4]) + (f" and {len(xs) - 4} more" if len(xs) > 4 else "")   # noqa: E731
    if badcls:
        add("bad", "Classes", f"{len(badcls)} label(s) use a class id that is not a whole number or not in the class list: {ex(badcls)}.", "Class ids run 0, 1, 2 ... in the order of the names in data.yaml.")
    if zero:
        add("bad", "Boxes", f"{len(zero)} box(es) have no width or height: {ex(zero)}.", "Delete them or redraw them.")
    if bad_out:
        add("bad", "Boxes", f"{len(bad_out)} box(es) reach outside the image: {ex(bad_out)}.", "Clip them to the image, or check the image size and coordinate format.")
    if dup:
        add("warn", "Boxes", f"{len(dup)} object(s) are labelled twice with the same class: {ex(dup)}.", "Keep one box per object - duplicates teach the model to fire twice.")
    if clash:
        add("bad", "Boxes", f"{len(clash)} object(s) carry two different classes on almost the same box: {ex(clash)}.", "Decide which class it is - the model cannot learn both.")
    if tiny:
        add("warn", "Boxes", f"{len(tiny)} box(es) are smaller than {min_px:g} pixels across{'' if sized else ' (0.5% of the image)'}: {ex(tiny)}.",
            "At the model's input size these may vanish; tile the images, raise the input size, or drop such tiny labels.")
    if aspect:
        add("info", "Boxes", f"{len(aspect)} box(es) are more than 20 times longer than wide: {ex(aspect)}.", "Fine for poles and cables; otherwise check them.")
    empty = [im["name"] for im in imgs if not im["boxes"]]
    n_img = len(imgs)
    if empty and len(empty) / n_img > 0.5:
        add("warn", "Images", f"{len(empty)} of {n_img} images have no labels at all.", "Some background images help; more than half usually means missing labels.")
    elif empty:
        add("info", "Images", f"{len(empty)} of {n_img} images have no labels (background images).", "Around 0-10% background images is usual.")
    real = {c: n for c, n in cls_count.items() if not nm or c in nm}
    if real:
        hi_c, lo_c = max(real, key=real.get), min(real, key=real.get)
        if real[hi_c] >= 10 * real[lo_c]:
            add("warn", "Balance", f"{nm.get(hi_c, hi_c)} has {real[hi_c]} boxes and {nm.get(lo_c, lo_c)} only {real[lo_c]} - the rare class will be found far less often.",
                "Collect more of the rare class, or oversample images that contain it.")
        for c, n_ in real.items():
            if n_ < 50:
                add("info", "Balance", f"{nm.get(c, c)} has only {n_} box(es) - most detectors want a few hundred per class.", "", nm.get(c, c))
    splits = Counter(split_of.values())
    if len(splits) > 1:
        by_stem: dict[str, set] = defaultdict(set)
        for im in imgs:
            by_stem[_stem(im["name"])].add(split_of[im["name"]])
        leaks = [s for s, sp in by_stem.items() if len(sp) > 1]
        if leaks:
            add("bad", "Leak", f"{len(leaks)} image(s) appear in more than one split ({ex(leaks)}) - the test score then measures memory, not skill.",
                "Keep each image (and its near copies, e.g. frames of the same video) in one split.")
        for s_ in ("val", "test"):
            if splits.get(s_):
                miss = [nm.get(c, c) for c in real if not cls_split[c].get(s_)]
                if miss:
                    add("warn", "Splits", f"The {s_} split has no {', '.join(miss[:5])} - those classes are never scored.", "Move some of their images into it.")
    elif n_img >= 20:
        add("info", "Splits", "No train / val / test folders in the paths, so splits and leaks were not checked.", "Paste the labels with their folders (train/..., val/...).")
    classes = [{"cls": c, "name": nm.get(c, c), "boxes": n_, "images": len(cls_imgs[c]), "share": n_ / max(1, sum(cls_count.values())),
                "splits": dict(cls_split[c]), "sizes": dict(sizes.get(c, {})), "unknown": c not in real} for c, n_ in sorted(cls_count.items(), key=lambda kv: -kv[1])]
    hist = Counter(min(k, 20) for k in per_img)
    out = {"format": fmt, "images": n_img, "boxes": sum(cls_count.values()), "classes": classes, "splits": dict(splits), "empty": len(empty),
           "per_image": {"max": max(per_img) if per_img else 0, "mean": sum(per_img) / max(1, n_img), "hist": sorted(hist.items())},
           "sized": bool(sized), "issues": issues}
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    b = out["counts"]["bad"]
    out["verdict"] = (f"{n_img:,} images, {out['boxes']:,} boxes in {len(classes)} class{'es' if len(classes) != 1 else ''} - "
                      + (f"{b} problem{'s' if b > 1 else ''} to fix before training" if b else "ready to train on"))
    out["note"] = ("Read from the label text only: wrong labels on the right shape (a cat boxed as a dog) are not visible here - look at a "
                   "sample of images with their boxes drawn, especially for the classes the model gets wrong.")
    return out
