"""A URDF robot model checked the way the loaders and simulators will read it: one tree with one root, every joint's parent and child
existing, each link the child of at most one joint, limits on every moving joint, axes that are not zero, and links whose mass and
inertia a physics engine can use (positive mass, a positive inertia that obeys the triangle inequality). Meshes referenced are
listed so she can check they ship with the package. Xacro must be expanded first."""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from typing import Any


class UrdfError(ValueError):
    pass


TYPES = ("revolute", "continuous", "prismatic", "fixed", "floating", "planar")
MAX = 5_000_000


def _f(s: str | None, d: float = 0.0) -> float:
    try:
        return float(s) if s not in (None, "") else d
    except ValueError:
        return float("nan")


def _vec(s: str | None, n: int = 3, d: str = "0 0 0") -> list[float]:
    v = [_f(x) for x in (s or d).split()]
    return v if len(v) == n else [float("nan")] * n


def check(text: str) -> dict[str, Any]:
    text = str(text or "")
    if len(text) > MAX:
        raise UrdfError("Up to 5 MB of URDF.")
    if re.search(r"<!DOCTYPE|<!ENTITY", text, re.I):
        raise UrdfError("This file declares a DOCTYPE or ENTITY - Hoola does not read those. Remove them (URDF does not need them).")
    if "xacro:" in text or "$(" in text or "${" in text:
        raise UrdfError("This is xacro, not URDF yet. Expand it first: `xacro robot.urdf.xacro > robot.urdf` (or `ros2 run xacro xacro ...`) and paste the result.")
    try:
        root = ET.fromstring(text.strip())
    except ET.ParseError as e:
        raise UrdfError(f"Not valid XML: {e}.")
    if root.tag != "robot":
        raise UrdfError(f"The top element is <{root.tag}>, not <robot>.")
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", name="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": name})   # noqa: E731
    name = root.get("name") or ""
    if not name:
        add("warn", "Robot", "The robot has no name attribute.", "<robot name=\"my_robot\">")
    links: dict[str, dict[str, Any]] = {}
    meshes: list[dict[str, str]] = []
    total = 0.0
    for el in root.findall("link"):
        ln = el.get("name") or ""
        if not ln:
            add("bad", "Links", "A link has no name.", "Every <link> needs name=.")
            continue
        if ln in links:
            add("bad", "Links", f"Two links are named {ln}.", "Link names must be unique.", ln)
        inert = el.find("inertial")
        d: dict[str, Any] = {"name": ln, "visual": len(el.findall("visual")), "collision": len(el.findall("collision")), "mass": None, "inertia": None}
        for g in el.findall("visual") + el.findall("collision"):
            m = g.find("geometry/mesh")
            if m is not None and m.get("filename"):
                meshes.append({"link": ln, "file": m.get("filename") or "", "use": "visual" if g.tag == "visual" else "collision"})
        if inert is not None:
            mm = inert.find("mass")
            mass = _f(mm.get("value") if mm is not None else None, float("nan"))
            d["mass"] = mass
            ii = inert.find("inertia")
            if ii is None:
                add("bad", "Inertia", f"{ln} has an <inertial> with no <inertia>.", "Add ixx, iyy, izz (and ixy, ixz, iyz).", ln)
            else:
                I = {k: _f(ii.get(k)) for k in ("ixx", "iyy", "izz", "ixy", "ixz", "iyz")}
                d["inertia"] = I
                a, b, c = I["ixx"], I["iyy"], I["izz"]
                if any(math.isnan(v) for v in I.values()):
                    add("bad", "Inertia", f"{ln}: an inertia value is not a number.", "", ln)
                elif min(a, b, c) <= 0:
                    add("bad", "Inertia", f"{ln}: ixx, iyy and izz must all be above 0 (they are {a:g}, {b:g}, {c:g}).", "Work them out from the shape and mass, or from your CAD tool.", ln)
                elif a + b < c * (1 - 1e-6) or a + c < b * (1 - 1e-6) or b + c < a * (1 - 1e-6):
                    add("bad", "Inertia", f"{ln}: the inertia breaks the triangle inequality (each of ixx, iyy, izz must be at most the sum of the other two) - no real body has it, and simulators misbehave.", "Recompute the inertia; a common cause is a unit slip (g·mm² vs kg·m²).", ln)
                else:
                    det = a * (b * c - I["iyz"] ** 2) - I["ixy"] * (I["ixy"] * c - I["iyz"] * I["ixz"]) + I["ixz"] * (I["ixy"] * I["iyz"] - b * I["ixz"])
                    if det <= 0 or a * b - I["ixy"] ** 2 <= 0:
                        add("bad", "Inertia", f"{ln}: the products of inertia make the matrix not positive definite.", "Check the signs and sizes of ixy, ixz, iyz.", ln)
                    elif not math.isnan(mass) and mass > 0:
                        r = math.sqrt(max(a, b, c) / mass)
                        if r > 5 or r < 1e-4:
                            add("warn", "Inertia", f"{ln}: the inertia means a body about {r:.3g} m in radius for {mass:g} kg - check the units.", "", ln)
            if math.isnan(mass) or mass <= 0:
                add("bad", "Mass", f"{ln} has an <inertial> with mass {mm.get('value') if mm is not None else 'missing'} - it must be above 0.", "Give the link its mass in kg.", ln)
            else:
                total += mass
        links[ln] = d
    joints: list[dict[str, Any]] = []
    child_of: dict[str, str] = {}
    kids: dict[str, list[str]] = {}
    jnames: set[str] = set()
    for el in root.findall("joint"):
        jn, jt = el.get("name") or "", el.get("type") or ""
        p = el.find("parent")
        c = el.find("child")
        pn, cn = (p.get("link") if p is not None else "") or "", (c.get("link") if c is not None else "") or ""
        j: dict[str, Any] = {"name": jn, "type": jt, "parent": pn, "child": cn, "limit": None, "axis": None}
        if not jn:
            add("bad", "Joints", "A joint has no name.", "Every <joint> needs name=.")
        elif jn in jnames:
            add("bad", "Joints", f"Two joints are named {jn}.", "Joint names must be unique.", jn)
        jnames.add(jn)
        if jt not in TYPES:
            add("bad", "Joints", f"{jn} has type '{jt}', which is not a URDF joint type.", "Use one of: " + ", ".join(TYPES) + ".", jn)
        for lk, side in ((pn, "parent"), (cn, "child")):
            if not lk:
                add("bad", "Joints", f"{jn} has no {side} link.", f"<{side} link=\"...\"/>", jn)
            elif lk not in links:
                add("bad", "Joints", f"{jn}'s {side} link '{lk}' does not exist.", "Check the spelling, or add the link.", jn)
        if pn and pn == cn:
            add("bad", "Joints", f"{jn} joins {pn} to itself.", "", jn)
        if cn:
            if cn in child_of:
                add("bad", "Tree", f"{cn} is the child of two joints ({child_of[cn]} and {jn}) - URDF is a tree, a link has one parent.", "For a closed chain, keep one joint in URDF and close the loop in the controller or simulator.", jn)
            else:
                child_of[cn] = jn
                kids.setdefault(pn, []).append(cn)
        o = el.find("origin")
        if o is not None:
            for k in ("xyz", "rpy"):
                if any(math.isnan(v) for v in _vec(o.get(k))):
                    add("bad", "Joints", f"{jn}: origin {k} is not three numbers.", "", jn)
        if jt in ("revolute", "continuous", "prismatic", "planar"):
            ax = el.find("axis")
            v = _vec(ax.get("xyz") if ax is not None else None, 3, "1 0 0")
            j["axis"] = v
            n = math.sqrt(sum(x * x for x in v)) if not any(math.isnan(x) for x in v) else float("nan")
            if ax is None:
                add("warn", "Axis", f"{jn} has no <axis>: it defaults to x (1 0 0).", "Give the axis even when it is x, so nobody has to guess.", jn)
            if math.isnan(n) or n < 1e-9:
                add("bad", "Axis", f"{jn}'s axis is zero or not three numbers.", "", jn)
            elif abs(n - 1) > 1e-3:
                add("warn", "Axis", f"{jn}'s axis has length {n:.4g}, not 1.", "Normalise it.", jn)
        if jt in ("revolute", "prismatic"):
            lim = el.find("limit")
            if lim is None:
                add("bad", "Limits", f"{jn} is {jt} but has no <limit> - URDF requires lower, upper, effort and velocity.", f"<limit lower=\"..\" upper=\"..\" effort=\"..\" velocity=\"..\"/>", jn)
            else:
                lo, hi, ef, ve = (_f(lim.get(k), float("nan")) for k in ("lower", "upper", "effort", "velocity"))
                j["limit"] = {"lower": lo, "upper": hi, "effort": ef, "velocity": ve}
                if math.isnan(lo) or math.isnan(hi):
                    add("warn", "Limits", f"{jn}: lower or upper is missing (they default to 0, so the joint cannot move).", "", jn)
                elif lo >= hi:
                    add("bad", "Limits", f"{jn}: lower {lo:g} is not below upper {hi:g}.", "", jn)
                elif jt == "revolute" and (abs(lo) > 7 or abs(hi) > 7):
                    add("bad", "Limits", f"{jn}: limits {lo:g} to {hi:g} look like degrees - URDF limits are in radians.", f"lower=\"{math.radians(lo):.4f}\" upper=\"{math.radians(hi):.4f}\"", jn)
                elif jt == "revolute" and hi - lo > 2 * math.pi + 1e-6:
                    add("warn", "Limits", f"{jn} turns more than a full circle ({math.degrees(hi - lo):.0f}°) - is it continuous instead?", "", jn)
                if math.isnan(ef) or ef <= 0:
                    add("bad", "Limits", f"{jn}: effort must be above 0.", "The joint's peak torque (N·m) or force (N).", jn)
                if math.isnan(ve) or ve <= 0:
                    add("bad", "Limits", f"{jn}: velocity must be above 0.", "The joint's top speed (rad/s or m/s).", jn)
        mi = el.find("mimic")
        if mi is not None:
            j["mimic"] = mi.get("joint") or ""
        joints.append(j)
    for j in joints:
        if j.get("mimic") and j["mimic"] not in jnames:
            add("bad", "Joints", f"{j['name']} mimics '{j['mimic']}', which does not exist.", "", j["name"])
    roots = [ln for ln in links if ln not in child_of]
    if not links:
        raise UrdfError("No <link> found.")
    if len(roots) > 1:
        add("bad", "Tree", f"{len(roots)} links have no parent ({', '.join(roots[:6])}) - a URDF must be one tree with one root.", "Join the loose parts with fixed joints.")
    elif not roots:
        add("bad", "Tree", "Every link has a parent, so the joints form a loop.", "")
    seen: set[str] = set()

    def walk(n: str, depth: int, out: list) -> int:
        if n in seen:
            return depth
        seen.add(n)
        out.append({"name": n, "depth": depth, "joint": child_of.get(n), "type": next((j["type"] for j in joints if j["child"] == n), "")})
        return max([depth] + [walk(k, depth + 1, out) for k in sorted(kids.get(n, []))])

    tree: list[dict[str, Any]] = []
    depth = max([walk(r, 0, tree) for r in roots] or [0])
    loose = [ln for ln in links if ln not in seen]
    if loose and roots:
        add("bad", "Tree", f"{', '.join(loose[:6])} cannot be reached from the root (a loop in the joints).", "")
    if roots and roots[0] == "world" and len(roots) == 1:
        pass
    elif roots and links.get(roots[0], {}).get("mass"):
        add("info", "Tree", f"The root link {roots[0]} has mass: Gazebo and KDL ignore the root link's inertia.", "Add a massless base_link (or base_footprint) as the root with a fixed joint to it.", roots[0])
    moving = [j for j in joints if j["type"] not in ("fixed",)]
    for ln, d in links.items():
        has_move = any(j["child"] == ln and j["type"] != "fixed" for j in joints)
        if d["mass"] is None and has_move:
            add("bad", "Mass", f"{ln} moves on a joint but has no <inertial>: physics engines drop it or treat it as weightless.", "Give it mass and inertia.", ln)
        if d["visual"] and not d["collision"]:
            add("info", "Collision", f"{ln} is drawn but has no collision shape - it passes through things in simulation and planning.", "Add a <collision>, ideally a simple box / cylinder / convex mesh.", ln)
    for m in meshes:
        f = m["file"]
        if not re.match(r"^(package|file|model)://", f):
            add("warn", "Meshes", f"{m['link']}: mesh '{f}' is a plain path - other machines will not find it.", "Use package://your_package/meshes/...", m["link"])
        if m["use"] == "collision" and re.search(r"\.(dae)$", f, re.I):
            add("info", "Meshes", f"{m['link']}: a COLLADA (.dae) collision mesh is slow to check - a simplified STL is faster.", "", m["link"])
    out = {"name": name, "links": len(links), "joints": len(joints), "moving": len(moving), "depth": depth, "root": roots[0] if roots else "",
           "mass": round(total, 4), "tree": tree[:400], "joint_rows": joints[:400],
           "link_rows": [{"name": d["name"], "mass": d["mass"], "visual": d["visual"], "collision": d["collision"]} for d in links.values()][:400],
           "meshes": meshes[:400], "issues": issues}
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    b = out["counts"]["bad"]
    out["verdict"] = (f"{name or 'The robot'}: {len(links)} links, {len(moving)} moving joints, {total:g} kg - "
                      + (f"{b} problem{'s' if b > 1 else ''} a loader or simulator will hit" if b else "loads as one tree"))
    out["note"] = ("Read from the URDF text: this checks the structure and the numbers, not whether the meshes exist on disk or the robot "
                   "looks right - load it in RViz or a simulator for that. `check_urdf` (liburdfdom-tools) runs the official parser; the CI check can run it for you.")
    return out
