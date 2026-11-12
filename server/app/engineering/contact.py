"""v0.386 HOOLA CONTACT: an assembly checked as SEPARATE parts that touch, can open, slide or stick, held by
preloaded bolts - not one glued body.

- Every part gets its own quadratic-tet mesh (fea.build_mesh); the global system is the parts side by side.
- Contact pairs are found from the B-rep: planar faces of two different parts, facing each other, in the same plane
  within a small gap, overlapping. Each pair is a Gauss-point-to-surface penalty pair: 3 Gauss points per facet of
  the first face, projected onto the second face's facets, both sides interpolated with the quadratic facet shape
  functions (so it is not node-to-node and works on non-matching meshes).
- Behaviour per pair: bonded (glued), frictionless (normal only, may OPEN), friction mu (stick / slip with Coulomb,
  may open). Open / closed and stick / slip are found by an active-set loop.
- Bolts: an axial connector from the ring under the head (RBE3-style average over the annulus) to the ring under the
  nut, or to the thread wall of a tapped hole; stiffness from the bolt's own shank + thread; PRELOAD calibrated so that
  with no outside load the bolt carries exactly the asked preload (the way bolt pretension works in commercial FEA).
- Weak springs (1e-10 E·h per node, only on parts with no support) only stop a free sliding part from making the system singular; a part that no
  support, contact or bolt connects is reported, never silently solved.
Results: every part's stress + safety factor, each bolt's force (preload -> loaded), each contact's max pressure,
open % and slipping %, whether the joint SEPARATED or SLIPPED. Units mm / N / MPa. Validated in tests against
stacked-beam theory (bonded = one beam, frictionless = 4x the deflection) and bolted-joint load sharing."""
from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

try:
    from . import calc, fea
    from . import parts as lib
except ImportError:                              # inside the analysis box: plain modules side by side
    import calc
    import fea
    import parts as lib


class ContactError(Exception):
    pass


# ---------------------------------------------------------------- one part
class _Part:
    def __init__(self, name: str, shape, nodes: int, mat: dict, offset: int):
        import skfem
        self.name, self.shape, self.mat = name, shape, mat
        self.msh = fea.build_mesh(shape, nodes)
        self.m = skfem.MeshTet(self.msh["X"].T.copy(), self.msh["T"].T.copy())
        self.e = skfem.ElementVector(skfem.ElementTetP2())
        self.ib = skfem.Basis(self.m, self.e)
        self.off = offset
        self.N = self.ib.N
        self.faces = self.msh["faces"]
        # edge index of a vertex pair, for the quadratic facet interpolation
        ed = self.m.edges
        self.edge_of = {(int(min(a, b)), int(max(a, b))): k for k, (a, b) in enumerate(ed.T)}
        self.vdof = self.ib.nodal_dofs                            # (3, n_vertices)
        self.edof = self.ib.edge_dofs                             # (3, n_edges) mid-edge nodes of P2

    def facet_nodes(self, fc: int) -> tuple[list[int], list[int]]:
        a, b, c = (int(x) for x in self.m.facets[:, fc])
        return [a, b, c], [self.edge_of[(min(a, b), max(a, b))], self.edge_of[(min(b, c), max(b, c))],
                           self.edge_of[(min(c, a), max(c, a))]]


def _shape6(l1, l2, l3) -> list[float]:
    """Quadratic triangle shape functions: 3 corners then edges (12, 23, 31)."""
    return [l1 * (2 * l1 - 1), l2 * (2 * l2 - 1), l3 * (2 * l3 - 1), 4 * l1 * l2, 4 * l2 * l3, 4 * l3 * l1]


def _interp_row(part: _Part, fc: int, bary: tuple[float, float, float], direction: np.ndarray, sign: float,
                cols: list, vals: list) -> None:
    vs, es = part.facet_nodes(fc)
    w = _shape6(*bary)
    for k in range(3):
        for c in range(3):
            if direction[c]:
                cols.append(part.off + part.vdof[c, vs[k]])
                vals.append(sign * w[k] * direction[c])
                cols.append(part.off + part.edof[c, es[k]])
                vals.append(sign * w[3 + k] * direction[c])


GAUSS3 = [((2 / 3, 1 / 6, 1 / 6), 1 / 3), ((1 / 6, 2 / 3, 1 / 6), 1 / 3), ((1 / 6, 1 / 6, 2 / 3), 1 / 3)]


def _bary(p, a, b, c):
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    d20, d21 = v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-30:
        return None
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    return 1 - v - w, v, w


# ---------------------------------------------------------------- contact pairs
def find_pairs(parts: list[_Part], tol: float) -> list[dict[str, Any]]:
    """Planar faces of two parts that face each other in (nearly) the same plane and overlap."""
    out = []
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            A, B = parts[i], parts[j]
            for fa_i, fa in enumerate(A.faces):
                if fa.geomType() != "PLANE":
                    continue
                na, ca = fa.normalAt(), fa.Center()
                for fb_i, fb in enumerate(B.faces):
                    if fb.geomType() != "PLANE":
                        continue
                    nb, cb = fb.normalAt(), fb.Center()
                    if na.dot(nb) > -0.999:
                        continue
                    gap = (cb - ca).dot(na)
                    if abs(gap) > tol:
                        continue
                    try:
                        if fa.distance(fb) > tol:
                            continue
                    except Exception:
                        continue
                    out.append({"a": i, "fa": fa_i, "b": j, "fb": fb_i, "n": np.array(na.toTuple()), "gap0": float(gap)})
    return out


def _pair_rows(pair: dict, parts: list[_Part]) -> dict[str, Any] | None:
    """Node-to-surface: every surface node of A's face (with its share of the face area) projected onto B's face
    facets, B interpolated with the quadratic facet shape functions. One contact point per node keeps the
    constraint count below the unknowns, so the penalty does not lock (3 Gauss points per facet did: a bonded
    stack came out 40 % too stiff and got stiffer as the penalty rose)."""
    from scipy.spatial import cKDTree
    A, B = parts[pair["a"]], parts[pair["b"]]
    fa = _strict(A, pair["fa"])
    fb = fea._facets_for(B.msh, B.m, [pair["fb"]])
    if not len(fa) or not len(fb):
        return None
    PA, PB = A.m.p, B.m.p
    area = {}
    for fc in fa:
        v = [int(x) for x in A.m.facets[:, fc]]
        ar = 0.5 * np.linalg.norm(np.cross(PA[:, v[1]] - PA[:, v[0]], PA[:, v[2]] - PA[:, v[0]]))
        for x in v:
            area[x] = area.get(x, 0.0) + ar / 3
    triB = B.m.facets[:, fb].T
    cenB = np.array([PB[:, t].mean(1) for t in triB])
    tree = cKDTree(cenB)
    n = pair["n"]
    t1 = np.cross(n, [1, 0, 0] if abs(n[0]) < 0.9 else [0, 1, 0])
    t1 /= np.linalg.norm(t1)
    t2 = np.cross(n, t1)
    rows = {"n": ([], [], []), "t1": ([], [], []), "t2": ([], [], [])}
    weights, gap0, pts = [], [], []
    g = 0
    for node, wnode in area.items():
        x = PA[:, node]
        hit = None
        for k in np.atleast_1d(tree.query(x, k=min(10, len(triB)))[1]):
            ta, tb, tc = (PB[:, int(v)] for v in triB[k])
            bc = _bary(x - n * ((x - ta) @ n), ta, tb, tc)
            if bc is not None and min(bc) >= -1e-6:
                hit = (int(fb[k]), bc)
                break
        if hit is None:
            continue
        for key, d in (("n", n), ("t1", t1), ("t2", t2)):
            cols = [A.off + A.vdof[c, node] for c in range(3) if d[c]]
            vals = [float(d[c]) for c in range(3) if d[c]]
            _interp_row(B, hit[0], hit[1], d, -1.0, cols, vals)
            r, cc, vv = rows[key]
            r += [g] * len(cols)
            cc += cols
            vv += vals
        weights.append(wnode)
        gap0.append(pair["gap0"])
        pts.append(x)
        g += 1
    if not g:
        return None
    return {"G": {k: (v[0], v[1], v[2]) for k, v in rows.items()}, "w": np.array(weights), "gap0": np.array(gap0),
            "pts": np.array(pts), "count": g, "t1": t1, "t2": t2}


def _strict(part: _Part, face_i: int) -> np.ndarray:
    """Boundary facets whose three corners all lie on this face (no facet cutting across an edge)."""
    nodes = part.msh["face_nodes"].get(face_i, set())
    bf = part.m.boundary_facets()
    arr = np.fromiter(nodes, dtype=np.int64) if nodes else np.zeros(0, np.int64)
    return bf[np.isin(part.m.facets[:, bf], arr).all(0)]


# ---------------------------------------------------------------- bolts
def _ring_nodes(part: _Part, center: np.ndarray, axis: np.ndarray, z: float, r_in: float, r_out: float,
                tol: float) -> np.ndarray:
    P = part.m.p.T
    rel = P - center
    along = rel @ axis
    radial = np.linalg.norm(rel - np.outer(along, axis), axis=1)
    bnd = np.unique(part.m.facets[:, part.m.boundary_facets()])
    sel = bnd[(np.abs(along[bnd] - z) < tol) & (radial[bnd] >= r_in - tol) & (radial[bnd] <= r_out + tol)]
    return sel


def _wall_nodes(part: _Part, center, axis, z_top, depth, r, tol) -> np.ndarray:
    P = part.m.p.T
    rel = P - center
    along = rel @ axis
    radial = np.linalg.norm(rel - np.outer(along, axis), axis=1)
    bnd = np.unique(part.m.facets[:, part.m.boundary_facets()])
    return bnd[(np.abs(radial[bnd] - r) < max(tol, 0.25 * r)) & (along[bnd] <= z_top + tol) & (along[bnd] >= z_top - depth - tol)]


def place_bolt(spec: dict, parts: list[_Part], tol: float) -> dict[str, Any]:
    """Find the hole stack of one bolt: head ring on the top part, nut ring on the bottom part (or the thread wall
    of a tapped bottom part). spec: m, at=[x, y] (or [x, y, z]), axis 'Z' | 'X' | 'Y', grade, preload_pct, tapped."""
    m = spec.get("m")
    if m not in calc.AS:
        raise ContactError(f"bolt M{m} is not in the table")
    axis = {"Z": np.array([0.0, 0, 1]), "X": np.array([1.0, 0, 0]), "Y": np.array([0.0, 1, 0])}[str(spec.get("axis", "Z")).upper()]
    at = [float(v) for v in spec.get("at", [0, 0])]
    center = np.zeros(3)
    free = [k for k in range(3) if not axis[k]]
    center[free[0]], center[free[1]] = at[0], at[1]
    hits = []
    for idx, p in enumerate(parts):
        P = p.m.p.T
        rel = P - center
        along = rel @ axis
        radial = np.linalg.norm(rel - np.outer(along, axis), axis=1)
        near = radial < 0.75 * m                                     # surface points of a hole near the axis
        bnd = np.unique(p.m.facets[:, p.m.boundary_facets()])
        hole = bnd[near[bnd]]
        if len(hole):
            hits.append((idx, float(along[hole].min()), float(along[hole].max()), float(np.median(radial[hole]))))
    if len(hits) < 2:
        raise ContactError(f"bolt at {at}: a hole is needed in two parts (found {len(hits)})")
    hits.sort(key=lambda h: h[2])
    top, bot = hits[-1], hits[0]
    pm = lib._m(m)
    r_hole = max(top[3], m / 2)
    r_head = max(pm[6] / 2, r_hole + 0.5)
    head = _ring_nodes(parts[top[0]], center, axis, top[2], r_hole, max(r_head, pm[11] / 2), tol)
    tapped = bool(spec.get("tapped"))
    if tapped:
        depth = min(1.5 * m, bot[2] - bot[1])
        nut = _wall_nodes(parts[bot[0]], center, axis, bot[2], depth, bot[3], tol)
        grip = top[2] - bot[2]
        nut_part = bot[0]
    else:
        nut = _ring_nodes(parts[bot[0]], center, axis, bot[1], max(bot[3], m / 2), pm[11] / 2, tol)
        grip = top[2] - bot[1]
        nut_part = bot[0]
    if not len(head) or not len(nut):
        raise ContactError(f"bolt M{m} at {at}: the head / nut seat was not found on the mesh")
    grade = str(spec.get("grade", "8.8"))
    j = calc.joint(m, grade, grip_mm=max(grip, 1.0), plates="steel")
    fi = float(spec.get("preload_N") or (float(spec.get("preload_pct", 75)) / 75.0) * j["preload_N"])
    return {"m": m, "grade": grade, "at": at, "axis": axis, "center": center, "head_part": top[0], "head": head,
            "nut_part": nut_part, "nut": nut, "tapped": tapped, "grip": grip, "kb": float(j["bolt_stiffness_N_mm"]),
            "preload": fi, "proof_N": calc.GRADES[grade][2] * calc.AS[m] if not (grade == "8.8" and m <= 16) else 580 * calc.AS[m]}


def _bolt_row(b: dict, parts: list[_Part]):
    """Axial elongation of the bolt = mean(head ring u.d) - mean(nut side u.d) -> one sparse row."""
    cols, vals = [], []
    d = b["axis"]
    for nodes, part_i, sign in ((b["head"], b["head_part"], 1.0), (b["nut"], b["nut_part"], -1.0)):
        P = parts[part_i]
        for nd in nodes:
            for c in range(3):
                if d[c]:
                    cols.append(P.off + P.vdof[c, nd])
                    vals.append(sign * d[c] / len(nodes))
    return cols, vals


# ---------------------------------------------------------------- solve
def solve(part_shapes: list[tuple[str, Any]], spec: dict) -> dict[str, Any]:
    import scipy.sparse as sp
    import scipy.sparse.linalg as sl
    import skfem
    from skfem.helpers import sym_grad
    from skfem.models.elasticity import lame_parameters, linear_elasticity, linear_stress
    t0 = time.time()
    if len(part_shapes) < 2:
        raise ContactError("contact needs at least 2 parts")
    if len(part_shapes) > 12:
        raise ContactError("contact analysis takes up to 12 parts (check a big assembly in sections)")
    mats = spec.get("materials") or {}
    mname0, _ = fea.material(spec.get("material"))
    total_nodes = int(spec.get("nodes") or 2400)
    vols = [max(float(s.Volume()), 1e-9) for _n, s in part_shapes]
    parts: list[_Part] = []
    off = 0
    for (name, shp), v in zip(part_shapes, vols):
        mname, mat = fea.material(mats.get(name) or spec.get("material"))
        nn = max(350, int(total_nodes * v / sum(vols)))
        p = _Part(name, shp, nn, mat, off)
        p.mname = mname
        parts.append(p)
        off += p.N
    ndof = off
    size = max(max(s.BoundingBox().xlen, s.BoundingBox().ylen, s.BoundingBox().zlen) for _n, s in part_shapes)
    tol = max(0.02, 2e-3 * size)
    # stiffness, block-diagonal
    blocks = []
    for p in parts:
        blocks.append(skfem.asm(linear_elasticity(*lame_parameters(p.mat["E"], p.mat["nu"])), p.ib))
    K0 = sp.block_diag(blocks, format="csr")
    h_min = min(p.msh["h"] for p in parts)
    E_max = max(p.mat["E"] for p in parts)
    stab = np.zeros(ndof)                                                     # filled once supports are known
    # supports + loads on the whole assembly's faces -> owning part
    import cadquery as cq
    comp = cq.Compound.makeCompound([s for _n, s in part_shapes])

    def owners(sel) -> list[tuple[int, int]]:
        picked = cq.Workplane("XY").add(comp).faces(str(sel)).vals() if str(sel).lower() != "all" else comp.Faces()
        out = []
        for f in picked:
            for pi, p in enumerate(parts):
                for fi, pf in enumerate(p.faces):
                    if pf.isSame(f):
                        out.append((pi, fi))
        if not out:
            raise ContactError(f"selector {sel!r} picked no face")
        return out
    fixed_dofs = []
    fixed_parts = set()
    for sel in (spec.get("fixed") if isinstance(spec.get("fixed"), list) else [spec.get("fixed")]):
        for pi, fi in owners(sel):
            p = parts[pi]
            fac = fea._facets_for(p.msh, p.m, [fi])
            fixed_dofs.append(p.off + p.ib.get_dofs(facets=fac).all())
            fixed_parts.add(pi)
    if not fixed_dofs:
        raise ContactError("fixed (support) faces are needed")
    D = np.unique(np.concatenate(fixed_dofs))
    for pi, p in enumerate(parts):              # only a part with no support of its own gets the (very weak) springs
        if pi not in fixed_parts:
            stab[p.off:p.off + p.N] = 1e-10 * E_max * h_min
    K0 = K0 + sp.diags(stab, format="csr")
    f = np.zeros(ndof)
    applied = np.zeros(3)
    for ld in spec.get("loads") or []:
        if ld.get("gravity"):
            for p in parts:
                g = np.array([0, 0, -9810.0])

                @skfem.LinearForm
                def body(v, w, g=g, rho=p.mat["rho"]):
                    return rho * (g[0] * v[0] + g[1] * v[1] + g[2] * v[2])
                f[p.off:p.off + p.N] += skfem.asm(body, p.ib)
                applied += g * p.mat["rho"] * float(p.shape.Volume())
            continue
        own = owners(ld.get("faces"))
        areas = []
        for pi, fi in own:
            p = parts[pi]
            fb = skfem.FacetBasis(p.m, p.e, facets=fea._facets_for(p.msh, p.m, [fi]))
            areas.append(float(skfem.asm(skfem.Functional(lambda w: 1.0 + 0 * w.x[0]), fb)))
        tot = max(sum(areas), 1e-12)
        F = np.array(ld.get("force") or [0, 0, 0], float)
        for (pi, fi), ar in zip(own, areas):
            p = parts[pi]
            fb = skfem.FacetBasis(p.m, p.e, facets=fea._facets_for(p.msh, p.m, [fi]))
            if "pressure" in ld:
                pr = float(ld["pressure"])

                @skfem.LinearForm
                def press(v, w, pr=pr):
                    return -pr * (w.n[0] * v[0] + w.n[1] * v[1] + w.n[2] * v[2])
                f[p.off:p.off + p.N] += skfem.asm(press, fb)
            else:
                t = F / tot

                @skfem.LinearForm
                def trac(v, w, t=t):
                    return t[0] * v[0] + t[1] * v[1] + t[2] * v[2]
                f[p.off:p.off + p.N] += skfem.asm(trac, fb)
        if "pressure" not in ld:
            applied += F
    # contact pairs
    behaviour = str(spec.get("contact", "friction")).lower()
    mu = float(spec.get("friction", 0.2))
    pairs = []
    for pr in find_pairs(parts, tol):
        rows = _pair_rows(pr, parts)
        if rows:
            G = {k: sp.csr_matrix((v[2], (v[0], v[1])), shape=(rows["count"], ndof)) for k, v in rows["G"].items()}
            pairs.append({**pr, **rows, "G": G})
    kpen = float(spec.get("penalty") or 5.0) * E_max / h_min
    # bolts
    bolts = [place_bolt(b, parts, max(tol, 0.35 * h_min)) for b in (spec.get("bolts") or [])]
    Brows = []
    for b in bolts:
        cols, vals = _bolt_row(b, parts)
        Brows.append(sp.csr_matrix((vals, ([0] * len(cols), cols)), shape=(1, ndof)))
    # connectivity: every part must reach a support through a contact pair or a bolt
    link = {i: set() for i in range(len(parts))}
    for pr in pairs:
        link[pr["a"]].add(pr["b"])
        link[pr["b"]].add(pr["a"])
    for b in bolts:
        link[b["head_part"]].add(b["nut_part"])
        link[b["nut_part"]].add(b["head_part"])
    seen, stack = set(fixed_parts), list(fixed_parts)
    while stack:
        x = stack.pop()
        for y in link[x] - seen:
            seen.add(y)
            stack.append(y)
    floating = [parts[i].name for i in range(len(parts)) if i not in seen]
    if floating:
        raise ContactError("these parts are not held by any support / contact / bolt: " + ", ".join(floating)
                           + " (they need touching faces or a bolt)")

    def system(state: list[dict], bolt_k: list[float]):
        K = K0.copy()
        for pr, st in zip(pairs, state):
            w = pr["w"] * kpen
            act_n = np.ones_like(st["closed"]) if behaviour == "bonded" else st["closed"]
            Gn = pr["G"]["n"]
            K = K + Gn.T @ sp.diags(w * act_n) @ Gn
            if behaviour == "frictionless":
                continue
            stick = np.ones_like(act_n) if behaviour == "bonded" else (act_n * st["stick"])
            for key in ("t1", "t2"):
                Gt = pr["G"][key]
                K = K + Gt.T @ sp.diags(w * stick) @ Gt
        for Bk, kb in zip(Brows, bolt_k):
            K = K + Bk.T @ Bk * kb
        return K

    def solve_lin(K, rhs):
        x = np.zeros(ndof)
        I = np.setdiff1d(np.arange(ndof), D)
        Kc = K[I][:, I].tocsc()
        x[I] = sl.spsolve(Kc, rhs[I])
        return x

    last: dict[str, Any] = {}

    def run(load: np.ndarray, pre_scale: list[float], max_it: int = 30):
        state = [{"closed": np.ones(pr["count"]), "stick": np.ones(pr["count"]), "slip_force": np.zeros(ndof)}
                 for pr in pairs]
        u = np.zeros(ndof)
        hist = []
        for it in range(max_it):
            K = system(state, [b["kb"] for b in bolts])
            rhs = load.copy()
            for Bk, b, s in zip(Brows, bolts, pre_scale):
                rhs -= (Bk.T @ np.array([b["kb"] * s])).ravel()        # initial shortening -> preload
            for pr, st in zip(pairs, state):
                act = np.ones(pr["count"]) if behaviour == "bonded" else st["closed"]
                rhs += pr["G"]["n"].T @ (pr["w"] * kpen * act * pr["gap0"])   # an initial gap stays a gap
                if behaviour == "friction":
                    rhs -= st["slip_force"]
            u = solve_lin(K, rhs)
            last["K"], last["rhs"] = K, rhs
            changed = 0
            for pr, st in zip(pairs, state):
                pen = pr["G"]["n"] @ u - pr["gap0"]                      # > 0 = the faces press into each other
                pn = kpen * pen * (np.ones_like(pen) if behaviour == "bonded" else st["closed"])   # pressure, MPa
                closed = (pen >= 0).astype(float) if behaviour != "bonded" else np.ones_like(pen)
                if behaviour == "friction":
                    gt1, gt2 = pr["G"]["t1"] @ u, pr["G"]["t2"] @ u
                    tt = kpen * np.hypot(gt1, gt2)                        # stick shear (MPa)
                    lim = mu * np.maximum(pn, 0)
                    was = st["stick"]                                       # hysteresis stops stick / slip flip-flop
                    stick = np.where(was > 0, tt <= 1.05 * lim + 1e-12, tt <= 0.95 * lim).astype(float) * closed
                    slipping = closed * (1 - stick)
                    nrm = np.maximum(np.hypot(gt1, gt2), 1e-30)
                    fs1 = slipping * lim * pr["w"] * gt1 / nrm
                    fs2 = slipping * lim * pr["w"] * gt2 / nrm
                    sf = pr["G"]["t1"].T @ fs1 + pr["G"]["t2"].T @ fs2
                    changed += int(np.sum(stick != st["stick"]))
                    st["stick"] = stick
                    st["slip_force"] = 0.5 * st["slip_force"] + 0.5 * sf
                changed += int(np.sum(closed != st["closed"]))
                st["closed"] = closed
                st["pn"] = np.maximum(pn, 0)
            hist.append(changed)
            total = sum(pr["count"] for pr in pairs) or 1
            if it > 0 and changed <= max(0, int(0.002 * total)):
                break
        return u, state, hist

    # bolt pretension calibration: with no outside load each bolt must carry exactly its preload
    scale = [0.0 for _ in bolts]
    if bolts:
        u1, _st1, _h1 = run(np.zeros(ndof), [1.0 for _ in bolts], max_it=12)
        for k, (Bk, b) in enumerate(zip(Brows, bolts)):
            f1 = b["kb"] * (float((Bk @ u1)[0]) + 1.0)                   # tension from a unit shortening
            if f1 <= 0:
                raise ContactError(f"bolt M{b['m']} at {b['at']} is not clamping anything")
            scale[k] = b["preload"] / f1
        u_pre, _sp, _hp = run(np.zeros(ndof), scale, max_it=12)
        pre_forces = [b["kb"] * (float((Bk @ u_pre)[0]) + s) for Bk, b, s in zip(Brows, bolts, scale)]
    else:
        pre_forces = []
    u, state, hist = run(f, scale)
    # results per part
    Xr = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)
    surf_v, surf_t, surf_s, part_rows = [], [], [], []
    vm_all = []
    for p in parts:
        up = u[p.off:p.off + p.N]
        bv = skfem.Basis(p.m, p.e, quadrature=(Xr, np.ones(4) / 24))
        sv = linear_stress(*lame_parameters(p.mat["E"], p.mat["nu"]))(sym_grad(bv.interpolate(up)))
        acc = np.zeros((3, 3, p.m.p.shape[1]))
        cnt = np.zeros(p.m.p.shape[1])
        for k in range(4):
            nd = p.m.t[k]
            for a in range(3):
                for b_ in range(3):
                    np.add.at(acc[a, b_], nd, sv[a, b_, :, k])
            np.add.at(cnt, nd, 1)
        vm = fea._vm(acc / np.maximum(cnt, 1))
        disp = np.sqrt(sum(up[p.ib.nodal_dofs[k]] ** 2 for k in range(3)))
        # judge strength away from supports, bolt rings and contact edges (ideal-contact singularities)
        from scipy.spatial import cKDTree
        hot = []
        Dp = D[(D >= p.off) & (D < p.off + p.N)] - p.off
        if len(Dp):
            vt = np.isin(p.ib.nodal_dofs[0], Dp) | np.isin(p.ib.nodal_dofs[1], Dp) | np.isin(p.ib.nodal_dofs[2], Dp)
            hot.append(p.m.p.T[vt])
        for b in bolts:
            if b["head_part"] == parts.index(p):
                hot.append(p.m.p.T[b["head"]])
            if b["nut_part"] == parts.index(p):
                hot.append(p.m.p.T[b["nut"]])
        away = np.ones(p.m.p.shape[1], bool)
        if hot:
            H = np.vstack(hot)
            away = cKDTree(H).query(p.m.p.T)[0] > 2.0 * p.msh["h"]
        peak_away = float(vm[away].max()) if away.any() else float(vm.max())
        sf = p.mat["yield"] / max(peak_away, 1e-12)
        part_rows.append({"part": p.name, "material": p.mname, "max_disp_mm": round(float(disp.max()), 5),
                          "peak_vm_MPa": round(float(vm.max()), 2), "peak_vm_away_MPa": round(peak_away, 2),
                          "safety_factor": round(sf, 2), "nodes": int(p.m.p.shape[1])})
        vm_all.append(vm)
        bf = p.m.boundary_facets()
        tri = p.m.facets[:, bf].T
        base = sum(len(x) for x in surf_v)
        used = np.unique(tri)
        remap = -np.ones(p.m.p.shape[1], np.int64)
        remap[used] = np.arange(len(used)) + base
        surf_v.append(p.m.p.T[used])
        surf_t.append(remap[tri])
        surf_s.append(vm[tri].mean(1))
    vmax = max(float(np.percentile(np.concatenate(vm_all), 99.5)), 1e-9)
    tri_s = np.concatenate(surf_s)
    surface = {"v": np.round(np.vstack(surf_v), 4).tolist(), "t": np.vstack(surf_t).tolist(),
               "tc": [list(fea.colormap(s / vmax)) for s in tri_s]}
    # contacts + bolts
    contact_rows = []
    separated = slipped = False
    for pr, st in zip(pairs, state):
        closed = st["closed"]
        open_pct = 100 * (1 - closed.mean())
        slip_pct = 100 * float(np.mean(closed * (1 - st["stick"]))) if behaviour == "friction" else 0.0
        contact_rows.append({"between": f"{parts[pr['a']].name} / {parts[pr['b']].name}",
                             "max_pressure_MPa": round(float(st.get("pn", np.zeros(1)).max()), 3),
                             "open_pct": round(open_pct, 1), "slipping_pct": round(slip_pct, 1)})
        if open_pct > 90:
            separated = True
        if open_pct < 100 and slip_pct / (100 - open_pct) > 0.9:     # every touching point is sliding
            slipped = True
    bolt_rows = []
    for k, (Bk, b) in enumerate(zip(Brows, bolts)):
        force = b["kb"] * (float((Bk @ u)[0]) + scale[k])
        bolt_rows.append({"bolt": f"M{b['m']} {b['grade']} at {b['at']}", "preload_N": round(pre_forces[k]),
                          "loaded_N": round(force), "change_N": round(force - pre_forces[k]),
                          "proof_N": round(b["proof_N"]), "yield_sf": round(b["proof_N"] / max(force, 1e-9), 2),
                          "tapped": b["tapped"], "grip_mm": round(b["grip"], 2)})
    # equilibrium on the supports
    react = last["K"] @ u - last["rhs"]                 # what the supports push back with, from the solve itself
    comp_ = D % 3
    rsum = np.array([react[D[comp_ == c]].sum() for c in range(3)])
    eq = float(np.linalg.norm(applied + rsum) / max(np.linalg.norm(applied), 1e-12)) if np.linalg.norm(applied) else 0.0
    worst = min(part_rows, key=lambda r: r["safety_factor"])
    min_sf = float(spec.get("min_sf") or 0) or None
    bolt_ok = all(b["yield_sf"] >= 1.0 for b in bolt_rows)
    if slipped:   # the parts slide until the bolt shank bears in its hole (bearing is not modelled): numbers not valid
        for r_ in part_rows:
            r_["max_disp_mm"] = None
    res = {"kind": "static", "contact": behaviour, "friction": mu if behaviour == "friction" else None,
           "parts": part_rows, "contacts": contact_rows, "bolts": bolt_rows,
           "separated": separated, "slipped": slipped, "equilibrium_error_pct": round(100 * eq, 3),
           "applied_N": np.round(applied, 3).tolist(), "active_set_rounds": len(hist),
           "max_disp_mm": None if slipped else max(r["max_disp_mm"] for r in part_rows),
           "valid": not slipped,
           "peak_vm_away_MPa": worst["peak_vm_away_MPa"], "peak_vm_MPa": max(r["peak_vm_MPa"] for r in part_rows),
           "at_peak": worst["part"], "safety_factor": worst["safety_factor"], "min_sf": min_sf,
           "passes": ((worst["safety_factor"] >= min_sf) if min_sf else True) and bolt_ok and not separated and not slipped,
           "material": worst["material"], "E_MPa": None, "yield_MPa": None, "at_disp": None, "convergence": None,
           "mesh": {"nodes": sum(r["nodes"] for r in part_rows), "elements": sum(int(p.m.t.shape[1]) for p in parts),
                    "h_mm": round(h_min, 3), "element": "quadratic tetra (P2), per part"},
           "scale": {"label": "von Mises stress (MPa)", "lo": 0.0, "hi": round(vmax, 3)},
           "seconds": round(time.time() - t0, 1), "surface": surface}
    return res
