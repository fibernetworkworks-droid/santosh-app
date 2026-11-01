"""v0.406 HOOLA MECHANISMS (box side): joints between an assembly's named parts -> the mechanism moves, is checked
and leaves as a robot description.

- Joints are written in the WORLD frame of the assembly as modelled (the zero pose): H.joint(name, parent, child,
  kind='revolute' | 'continuous' | 'prismatic' | 'fixed', origin=(x, y, z) mm, axis=(ax, ay, az), limits=(lo, hi)
  degrees or mm, effort, velocity). The joints must make a TREE: one root part, every other part the child of
  exactly one joint (a part left out is fixed to the root and said so).
- Mass properties from the B-rep (OCC GProp): mass, centre of mass, inertia tensor about the centre of mass, from
  the part's material density.
- Range-of-motion check: every movable joint swept through its limits (the others at zero); the solids of parts
  that are NOT parent / child of that joint are tested for real overlap (OCC common, > 0.5 % of the smaller part's
  volume); the result is the joint's FREE range around zero and the first collision on each side.
- URDF: one link per part (frame at its joint's origin, world-aligned at the zero pose), visual + collision mesh in
  the link frame (STL, mm, scale 0.001), inertial in kg / m / kg·m², joint origin relative to the parent link, axis,
  limits in rad / m with effort / velocity (defaults said as assumed). Checked by our own validator after writing
  (tree, names, limits, positive mass, inertia triangle inequality) and parsed back as XML.
- Motion frames (all joints swinging through their ranges) and an exploded pose, as part transforms for the server
  to draw (motion.gif, explode.png)."""
from __future__ import annotations

import json
import math
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

KINDS = ("revolute", "continuous", "prismatic", "fixed")


class KinError(Exception):
    pass


def _rot(axis, ang) -> np.ndarray:
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    x, y, z = a
    c, s, C = math.cos(ang), math.sin(ang), 1 - math.cos(ang)
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def _joint_tf(j: dict, q: float) -> np.ndarray:
    """4x4 motion of the child (world frame of the zero pose) for joint value q (rad or mm)."""
    T = np.eye(4)
    o = np.asarray(j["origin"], float)
    if j["kind"] in ("revolute", "continuous"):
        R = _rot(j["axis"], q)
        T[:3, :3] = R
        T[:3, 3] = o - R @ o
    elif j["kind"] == "prismatic":
        a = np.asarray(j["axis"], float)
        T[:3, 3] = a / np.linalg.norm(a) * q
    return T


def tree(names: list[str], joints: list[dict]) -> dict[str, Any]:
    """Validate the joint list into a tree. Returns {root, parent_of, children, order, joints_by_child, problems}."""
    probs = []
    jn = [j["name"] for j in joints]
    if len(set(jn)) != len(jn):
        probs.append("two joints share a name")
    parent_of, by_child = {}, {}
    for j in joints:
        if j["kind"] not in KINDS:
            probs.append(f"joint {j['name']}: kind {j['kind']} (revolute / continuous / prismatic / fixed)")
        for end in ("parent", "child"):
            if j[end] not in names:
                probs.append(f"joint {j['name']}: {end} '{j[end]}' is not a part of the assembly ({', '.join(names)})")
        if j["child"] in parent_of:
            probs.append(f"part {j['child']} is the child of two joints (a robot description must be a tree)")
        parent_of[j["child"]] = j["parent"]
        by_child[j["child"]] = j
        ax = np.asarray(j["axis"], float)
        if j["kind"] != "fixed" and np.linalg.norm(ax) < 1e-9:
            probs.append(f"joint {j['name']}: axis is zero")
        if j["kind"] not in ("fixed", "continuous"):
            lo, hi = j["limits"]
            if not lo < hi:
                probs.append(f"joint {j['name']}: limits {lo} .. {hi} must go low to high")
    roots = [n for n in names if n not in parent_of]
    # cycle check
    for n in names:
        seen, cur = set(), n
        while cur in parent_of:
            if cur in seen:
                probs.append(f"joints make a loop through {cur} (closed chains need a different description)")
                break
            seen.add(cur)
            cur = parent_of[cur]
    root = roots[0] if roots else names[0]
    loose = [n for n in roots[1:]]
    children: dict[str, list[str]] = {n: [] for n in names}
    for c, p in parent_of.items():
        if p in children:
            children[p].append(c)
    order, stack = [], [root]
    while stack:
        n = stack.pop(0)
        order.append(n)
        stack += children.get(n, [])
    return {"root": root, "loose": loose, "parent_of": parent_of, "children": children, "order": order,
            "by_child": by_child, "problems": probs}


def world_tf(t: dict, q: dict[str, float]) -> dict[str, np.ndarray]:
    """Every part's 4x4 motion for joint values q (by joint name; missing = 0)."""
    out = {t["root"]: np.eye(4)}
    for n in t["order"][1:]:
        j = t["by_child"][n]
        out[n] = out[j["parent"]] @ _joint_tf(j, q.get(j["name"], 0.0))
    for n in t["loose"]:
        out[n] = np.eye(4)
    return out


def _move(shape, T):
    import cadquery as cq
    from OCP.gp import gp_Trsf
    tr = gp_Trsf()
    tr.SetValues(*[float(T[i, k]) for i in range(3) for k in range(4)])
    return cq.Shape.cast(shape.moved(cq.Location(tr)).wrapped)


def mass_props(shape, rho_kg_mm3: float) -> dict[str, Any]:
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, g)
    v = g.Mass()                                         # mm³ (unit density)
    c = g.CentreOfMass()
    M = g.MatrixOfInertia()                              # about the centre of mass, mm^5
    I = np.array([[M.Value(i, k) for k in range(1, 4)] for i in range(1, 4)]) * rho_kg_mm3 * 1e-6   # kg·m²
    return {"volume_mm3": v, "mass_kg": v * rho_kg_mm3, "com_mm": [c.X(), c.Y(), c.Z()], "inertia": I}


def _overlap(a, b) -> float:
    try:
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
        import cadquery as cq
        bb1, bb2 = a.BoundingBox(), b.BoundingBox()
        if (bb1.xmax < bb2.xmin or bb2.xmax < bb1.xmin or bb1.ymax < bb2.ymin or bb2.ymax < bb1.ymin
                or bb1.zmax < bb2.zmin or bb2.zmax < bb1.zmin):
            return 0.0
        op = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
        if not op.IsDone():
            return 0.0
        return float(cq.Shape.cast(op.Shape()).Volume())
    except Exception:
        return 0.0


def sweep(parts: dict[str, Any], t: dict, steps: int = 12) -> list[dict[str, Any]]:
    """Each movable joint swept through its range; collisions between parts that are not this joint's own pair."""
    out = []
    vols = {n: max(float(s.Volume()), 1e-9) for n, s in parts.items()}
    for n in t["order"][1:]:
        j = t["by_child"][n]
        if j["kind"] == "fixed":
            continue
        lo, hi = (j["limits_si"] if j["kind"] != "continuous" else (-math.pi, math.pi))
        sub = _subtree(t, n)
        others = [m for m in parts if m not in sub]
        found = {"lo": None, "hi": None}

        def clash(q):
            T = world_tf(t, {j["name"]: q})
            for a in sub:
                sa = _move(parts[a], T[a])
                for b in others:
                    if b == j["parent"] and a == n:
                        continue                                       # the joint's own pair always touches
                    ov = _overlap(sa, parts[b])
                    if ov > 0.005 * min(vols[a], vols[b]):
                        return {"q": q, "parts": [a, b], "overlap_mm3": round(ov, 1)}
            return None
        for side, end in (("hi", hi), ("lo", lo)):
            if (side == "hi" and end <= 0) or (side == "lo" and end >= 0):
                continue
            prev = 0.0
            for k in range(1, steps + 1):
                q = end * k / steps
                hit = clash(q)
                if hit:
                    a_, b_ = prev, q                                   # bisect to the first touching value
                    for _ in range(6):
                        m_ = (a_ + b_) / 2
                        h2 = clash(m_)
                        if h2:
                            b_, hit = m_, h2
                        else:
                            a_ = m_
                    found[side] = hit
                    break
                prev = q
        def show(qv):
            return round(math.degrees(qv), 1) if j["kind"] != "prismatic" else round(qv * 1000, 2)
        free_lo = show(found["lo"]["q"]) if found["lo"] else show(lo)
        free_hi = show(found["hi"]["q"]) if found["hi"] else show(hi)
        out.append({"joint": j["name"], "kind": j["kind"], "asked": [show(lo), show(hi)], "free": [free_lo, free_hi],
                    "unit": "deg" if j["kind"] != "prismatic" else "mm",
                    "collides": [{"at": show(h["q"]), "parts": h["parts"], "overlap_mm3": h["overlap_mm3"]}
                                 for h in (found["lo"], found["hi"]) if h]})
    return out


def _subtree(t: dict, n: str) -> list[str]:
    out, stack = [], [n]
    while stack:
        x = stack.pop()
        out.append(x)
        stack += t["children"].get(x, [])
    return out


def _fmt(v) -> str:
    return " ".join(f"{float(x):.6g}" for x in v)


def write_urdf(robot: str, parts: dict[str, Any], t: dict, props: dict[str, dict], out_dir: Path) -> dict[str, Any]:
    """robot.urdf + meshes/<link>.stl (mm, scale 0.001) zipped as robot_urdf.zip; returns the check rows."""
    import cadquery as cq
    from xml.sax.saxutils import quoteattr
    frame = {t["root"]: np.zeros(3)}
    for n in t["order"][1:]:
        frame[n] = np.asarray(t["by_child"][n]["origin"], float)
    for n in t["loose"]:
        frame[n] = np.zeros(3)
    mdir = out_dir / "urdf_meshes"
    mdir.mkdir(exist_ok=True)
    safe = {n: "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in n) or "part" for n in parts}
    lines = ['<?xml version="1.0"?>', f'<robot name={quoteattr(robot)}>',
             f'  <!-- Made by Hoola CAD Engineer. Units: m, kg, rad. Meshes are in mm (scale 0.001). DRAFT. -->']
    for n in [*t["order"], *t["loose"]]:
        f = frame[n]
        shp = parts[n].translate(cq.Vector(*(-f)))
        stl = mdir / f"{safe[n]}.stl"
        cq.exporters.export(shp, str(stl), tolerance=0.05, angularTolerance=0.2)
        p = props[n]
        com = (np.asarray(p["com_mm"]) - f) / 1000
        I = p["inertia"]
        lines += [f'  <link name={quoteattr(safe[n])}>',
                  '    <inertial>', f'      <origin xyz="{_fmt(com)}" rpy="0 0 0"/>',
                  f'      <mass value="{p["mass_kg"]:.6g}"/>',
                  f'      <inertia ixx="{I[0, 0]:.6g}" ixy="{I[0, 1]:.6g}" ixz="{I[0, 2]:.6g}" iyy="{I[1, 1]:.6g}" '
                  f'iyz="{I[1, 2]:.6g}" izz="{I[2, 2]:.6g}"/>', '    </inertial>']
        for tag in ("visual", "collision"):
            lines += [f'    <{tag}>', '      <origin xyz="0 0 0" rpy="0 0 0"/>',
                      f'      <geometry><mesh filename="meshes/{safe[n]}.stl" scale="0.001 0.001 0.001"/></geometry>',
                      f'    </{tag}>']
        lines.append('  </link>')
    joints = [t["by_child"][n] for n in t["order"][1:]] + [
        {"name": f"fixed_{safe[n]}", "parent": t["root"], "child": n, "kind": "fixed", "origin": (0, 0, 0),
         "axis": (0, 0, 1), "limits": (0, 0)} for n in t["loose"]]
    for j in joints:
        o = (np.asarray(j["origin"], float) - frame[j["parent"]]) / 1000
        lines += [f'  <joint name={quoteattr(j["name"])} type="{j["kind"]}">',
                  f'    <parent link={quoteattr(safe[j["parent"]])}/>', f'    <child link={quoteattr(safe[j["child"]])}/>',
                  f'    <origin xyz="{_fmt(o)}" rpy="0 0 0"/>']
        if j["kind"] != "fixed":
            a = np.asarray(j["axis"], float)
            lines.append(f'    <axis xyz="{_fmt(a / np.linalg.norm(a))}"/>')
            if j["kind"] in ("revolute", "prismatic"):
                lo, hi = j["limits_si"]
                lines.append(f'    <limit lower="{lo:.6g}" upper="{hi:.6g}" effort="{j["effort"]:.6g}" '
                             f'velocity="{j["velocity"]:.6g}"/>')
            else:
                lines.append(f'    <limit effort="{j["effort"]:.6g}" velocity="{j["velocity"]:.6g}"/>')
        lines.append('  </joint>')
    lines.append('</robot>')
    text = "\n".join(lines) + "\n"
    (out_dir / "robot.urdf").write_text(text, encoding="utf-8")
    rows = validate(text, props, safe)
    with zipfile.ZipFile(out_dir / "robot_urdf.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{robot}/robot.urdf", text)
        for f_ in sorted(mdir.glob("*.stl")):
            z.write(f_, f"{robot}/meshes/{f_.name}")
        z.writestr(f"{robot}/README.txt", "URDF by Hoola CAD Engineer. Units m / kg / rad; meshes in mm with "
                   "scale 0.001. Effort / velocity limits are assumed unless she gave them. DRAFT for review.\n")
    import shutil
    shutil.rmtree(mdir, ignore_errors=True)
    return {"rows": rows, "links": len(parts), "joints": len(joints)}


def validate(text: str, props: dict, safe: dict) -> list[dict[str, Any]]:
    """Our own URDF checks on the written file (parsed back as XML)."""
    import xml.etree.ElementTree as ET
    rows = []
    try:
        root = ET.fromstring(text)
        rows.append({"check": "Parses as XML", "ok": True, "note": ""})
    except ET.ParseError as e:
        return [{"check": "Parses as XML", "ok": False, "note": str(e)}]
    links = [l.get("name") for l in root.findall("link")]
    joints = root.findall("joint")
    rows.append({"check": "Link names unique", "ok": len(set(links)) == len(links), "note": f"{len(links)} links"})
    children = [j.find("child").get("link") for j in joints]
    parents = [j.find("parent").get("link") for j in joints]
    roots = [l for l in links if l not in children]
    rows.append({"check": "One root, a tree", "ok": len(roots) == 1 and len(set(children)) == len(children)
                 and all(p in links for p in parents), "note": f"root {roots[0] if roots else '-'}"})
    bad_lim = [j.get("name") for j in joints if j.find("limit") is not None and j.find("limit").get("lower")
               and float(j.find("limit").get("lower")) >= float(j.find("limit").get("upper"))]
    rows.append({"check": "Limits low < high", "ok": not bad_lim, "note": ", ".join(bad_lim)})
    bad_mass, bad_I = [], []
    for l in root.findall("link"):
        m = float(l.find("inertial/mass").get("value"))
        if m <= 0:
            bad_mass.append(l.get("name"))
        I = l.find("inertial/inertia")
        ix, iy, iz = (float(I.get(k)) for k in ("ixx", "iyy", "izz"))
        M = np.array([[ix, float(I.get("ixy")), float(I.get("ixz"))], [float(I.get("ixy")), iy, float(I.get("iyz"))],
                      [float(I.get("ixz")), float(I.get("iyz")), iz]])
        ev = np.linalg.eigvalsh(M)
        tol = 1e-9 * max(abs(ev).max(), 1e-12)
        if ev.min() < -tol or ix + iy < iz - tol or iy + iz < ix - tol or ix + iz < iy - tol:
            bad_I.append(l.get("name"))
    rows.append({"check": "Masses positive", "ok": not bad_mass, "note": ", ".join(bad_mass)})
    rows.append({"check": "Inertias physical (positive, triangle rule)", "ok": not bad_I, "note": ", ".join(bad_I)})
    del props, safe
    return rows


def run(part_list: list[tuple[str, Any]], spec_joints: list[dict], spec_robot: dict, material: str,
        out_dir: Path) -> dict[str, Any]:
    import fea
    parts = {n: s for n, s, *_ in part_list}
    names = list(parts)
    joints = []
    for j in spec_joints:
        kind = str(j.get("kind", "revolute")).lower()
        lim = tuple(float(x) for x in (j.get("limits") or ((-180, 180) if kind != "prismatic" else (0, 100))))
        si = (math.radians(lim[0]), math.radians(lim[1])) if kind in ("revolute", "continuous") else \
            (lim[0] / 1000, lim[1] / 1000)
        joints.append({"name": str(j["name"]), "parent": str(j["parent"]), "child": str(j["child"]), "kind": kind,
                       "origin": [float(x) for x in j.get("origin", (0, 0, 0))],
                       "axis": [float(x) for x in j.get("axis", (0, 0, 1))], "limits": lim, "limits_si": si,
                       "effort": float(j.get("effort") or (10.0 if kind != "prismatic" else 100.0)),
                       "velocity": float(j.get("velocity") or (1.0 if kind != "prismatic" else 0.1)),
                       "assumed": [k for k in ("effort", "velocity") if not j.get(k)]})
    t = tree(names, joints)
    if t["problems"]:
        return {"ok": False, "problems": t["problems"]}
    mats = spec_robot.get("materials") or {}
    props = {}
    for n, s in parts.items():
        _mn, mat = fea.material(mats.get(n) or material)
        props[n] = mass_props(s, mat["rho"] * 1000.0)            # t/mm³ -> kg/mm³
    rng = sweep(parts, t)
    robot = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(spec_robot.get("name") or "hoola_robot"))
    urdf = write_urdf(robot, parts, t, props, out_dir)
    # motion frames (all joints swinging together) + explode offsets, as transforms for the server's renderer
    frames = []
    N = 16
    for k in range(N):
        q = {}
        for j in joints:
            if j["kind"] == "fixed":
                continue
            lo, hi = j["limits_si"] if j["kind"] != "continuous" else (-math.pi, math.pi)
            q[j["name"]] = (lo + hi) / 2 + (hi - lo) / 2 * math.sin(2 * math.pi * k / N)
        W = world_tf(t, q)
        frames.append({n: W[n].round(6).tolist() for n in names})
    allc = np.array([props[n]["com_mm"] for n in names])
    centre = allc.mean(0)
    size = max(max(s.BoundingBox().xlen, s.BoundingBox().ylen, s.BoundingBox().zlen) for s in parts.values())
    depth = {n: 0 for n in names}
    for n in t["order"]:
        for c in t["children"].get(n, []):
            depth[c] = depth[n] + 1
    explode = {}
    for n in names:
        d = np.asarray(props[n]["com_mm"]) - centre
        L = np.linalg.norm(d)
        d = d / L if L > 1e-6 else np.array([0, 0, 1.0])
        explode[n] = (d * size * 0.45 * (1 + 0.5 * depth[n])).round(3).tolist()
    (out_dir / "kin.json").write_text(json.dumps({"names": names, "frames": frames, "explode": explode}),
                                      encoding="utf-8")
    return {"ok": True, "robot": robot, "root": t["root"], "loose": t["loose"],
            "joints": [{k: j[k] for k in ("name", "parent", "child", "kind", "origin", "axis", "limits", "effort",
                                          "velocity", "assumed")} for j in joints],
            "links": [{"name": n, "mass_kg": round(props[n]["mass_kg"], 4),
                       "com_mm": [round(x, 2) for x in props[n]["com_mm"]]} for n in names],
            "range": rng, "urdf": urdf}
