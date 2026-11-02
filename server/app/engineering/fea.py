"""v0.365 HOOLA ANALYSIS: real finite-element checks of the part Hoola just designed (stress, heat, vibration).

Runs in the analysis child (analysis_runner.py, same box limits as the CAD runner) on the part's own B-rep:
- mesh: the B-rep faces are sampled at spacing h (every point remembers its face), a jittered interior grid is
  added, Delaunay makes tetrahedra and only the ones whose centre is inside the solid are kept (OCC classifier).
  Quadratic tetrahedra (P2) so bending is not locked.
- loads / supports are named the CadQuery way (">Z", "<X", "%CYLINDER", "|Z" ...) and land on the exact mesh facets
  that came from those faces.
- static: linear elasticity, von Mises at the element vertices averaged per node (no quadrature spikes), peak +
  peak away from the supports (a clamped edge is a singularity in any FEA), safety factor vs yield, equilibrium
  check (reactions = loads) and a two-mesh convergence check.
- thermal: steady conduction with fixed temperatures, heat input (W) and convection.
- modal: natural frequencies (Hz) with the supports given, or free-free.
- buckling (v0.432): the load factor at which a slender part FOLDS instead of breaking (linear eigenvalue
  buckling on the real stress state); the perfect-shape ceiling, with the thin-wall knock-down said out loud.
Units: mm, N, MPa, tonne/mm³, W, W/(mm·K), °C. Validated in tests against beam theory and 1-D conduction.
Libraries: scikit-fem (BSD-3), SciPy (BSD), PyAMG (MIT, optional). DRAFT results for an engineer's review."""
from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

# E MPa, nu, rho t/mm³, yield MPa, k W/(mm·K), sut (ultimate) MPa, alpha 1/K
MATERIALS: dict[str, dict[str, float]] = {
    "steel":      {"E": 200000, "nu": 0.29, "rho": 7.85e-9, "yield": 250, "k": 0.050, "sut": 400, "alpha": 12e-6},
    "mild steel": {"E": 200000, "nu": 0.29, "rho": 7.85e-9, "yield": 250, "k": 0.050, "sut": 400, "alpha": 12e-6},
    "stainless":  {"E": 193000, "nu": 0.29, "rho": 8.00e-9, "yield": 215, "k": 0.016, "sut": 505, "alpha": 17e-6},
    "aluminium":  {"E": 68900, "nu": 0.33, "rho": 2.70e-9, "yield": 276, "k": 0.167, "sut": 310, "alpha": 23.6e-6},
    "aluminum":   {"E": 68900, "nu": 0.33, "rho": 2.70e-9, "yield": 276, "k": 0.167, "sut": 310, "alpha": 23.6e-6},
    "brass":      {"E": 100000, "nu": 0.34, "rho": 8.50e-9, "yield": 200, "k": 0.109, "sut": 340, "alpha": 19e-6},
    "copper":     {"E": 117000, "nu": 0.34, "rho": 8.96e-9, "yield": 70, "k": 0.385, "sut": 210, "alpha": 17e-6},
    "titanium":   {"E": 113800, "nu": 0.34, "rho": 4.43e-9, "yield": 880, "k": 0.0067, "sut": 950, "alpha": 8.6e-6},
    "cast iron":  {"E": 110000, "nu": 0.26, "rho": 7.20e-9, "yield": 130, "k": 0.052, "sut": 200, "alpha": 10.5e-6},
    "abs":        {"E": 2100, "nu": 0.35, "rho": 1.04e-9, "yield": 40, "k": 0.00017, "sut": 40, "alpha": 90e-6},
    "pla":        {"E": 3500, "nu": 0.36, "rho": 1.24e-9, "yield": 50, "k": 0.00013, "sut": 50, "alpha": 68e-6},
    "petg":       {"E": 2100, "nu": 0.38, "rho": 1.27e-9, "yield": 45, "k": 0.00020, "sut": 50, "alpha": 68e-6},
    "nylon":      {"E": 2700, "nu": 0.39, "rho": 1.14e-9, "yield": 70, "k": 0.00025, "sut": 75, "alpha": 80e-6},
    "pom":        {"E": 2900, "nu": 0.35, "rho": 1.41e-9, "yield": 65, "k": 0.00031, "sut": 70, "alpha": 110e-6},
    "polycarbonate": {"E": 2400, "nu": 0.37, "rho": 1.20e-9, "yield": 62, "k": 0.00020, "sut": 65, "alpha": 65e-6},
    "wood":       {"E": 11000, "nu": 0.30, "rho": 0.60e-9, "yield": 40, "k": 0.00012, "sut": 40, "alpha": 5e-6},
}


# ---------------------------------------------------------------- v0.381 fatigue (stress-life, Shigley / Marin)
FINISH = {"ground": (1.58, -0.085), "machined": (4.51, -0.265), "cold-drawn": (4.51, -0.265),
          "hot-rolled": (57.7, -0.718), "as-forged": (272.0, -0.995), "printed": (57.7, -0.718), "cast": (57.7, -0.718)}
RELIAB = {50: 1.0, 90: 0.897, 95: 0.868, 99: 0.814, 99.9: 0.753, 99.99: 0.702}


def endurance(mname: str, mat: dict, finish: str = "machined", d: float | None = None, reliability: float = 90,
              load: str = "bending") -> dict[str, float | str]:
    """Corrected endurance strength Se (MPa) and how it was built. Steels have a knee at 1e6 cycles; aluminium,
    copper alloys and plastics have none, so their 'Se' is the strength at 5e8 cycles (said in `basis`)."""
    sut = float(mat.get("sut") or mat["yield"] * 1.2)
    if mname in ("steel", "mild steel", "stainless", "titanium", "cast iron"):
        se0, basis = (0.5 * sut if sut <= 1400 else 700.0), "endurance limit (1e6 cycles)"
        if mname == "cast iron":
            se0 = 0.4 * sut
    elif mname in ("aluminium", "aluminum", "brass", "copper"):
        se0, basis = min(0.4 * sut, 130.0), "strength at 5e8 cycles (no true endurance limit)"
    else:
        se0, basis = 0.25 * sut, "rough polymer fatigue strength at 1e7 cycles (test the real print / moulding)"
    a, b = FINISH.get(str(finish).lower(), FINISH["machined"])
    ka = min(1.0, a * sut ** b)
    if d and d > 2.79:
        kb = 1.24 * d ** -0.107 if d <= 51 else 1.51 * d ** -0.157
    else:
        kb = 1.0
    kc = {"bending": 1.0, "axial": 0.85, "torsion": 0.59}.get(load, 1.0)
    ke = RELIAB.get(reliability, 0.897)
    return {"sut": sut, "se": se0 * ka * kb * kc * ke, "se_raw": se0, "ka": round(ka, 3), "kb": round(kb, 3),
            "kc": kc, "ke": ke, "basis": basis}


def fatigue_eval(sigma_max: float, sigma_min: float, en: dict, life: float = 1e6) -> dict[str, Any]:
    """Goodman mean-stress + Basquin S-N between 1e3 (f·Sut) and 1e6 (Se). Stresses in MPa."""
    sut, se = en["sut"], en["se"]
    sa = abs(sigma_max - sigma_min) / 2
    sm = (sigma_max + sigma_min) / 2
    f = 0.9 if sut < 490 else max(0.77, 0.9 - (sut - 490) * 0.00013)
    a = (f * sut) ** 2 / se
    b = -math.log10(f * sut / se) / 3
    sar = sa / max(1e-9, 1 - max(sm, 0) / sut)              # equivalent fully reversed amplitude (Goodman)
    if sar <= se:
        n_life = math.inf
    else:
        n_life = (sar / a) ** (1 / b) if b else math.inf
    s_life = se if life >= 1e6 else min(f * sut, a * max(life, 1e3) ** b)
    nf = 1 / max(1e-12, sa / s_life + max(sm, 0) / sut)
    return {"sigma_a_MPa": round(sa, 2), "sigma_m_MPa": round(sm, 2), "equivalent_reversed_MPa": round(sar, 2),
            "Se_MPa": round(se, 1), "strength_at_life_MPa": round(s_life, 1), "target_cycles": life,
            "predicted_cycles": "infinite (below the endurance strength)" if n_life == math.inf else f"{n_life:.3g}",
            "fatigue_sf": round(nf, 2), "basis": en.get("basis", ""), "marin": {k: en[k] for k in ("ka", "kb", "kc", "ke")},
            "method": "Goodman mean stress + Basquin S-N (Shigley); Marin surface / size / load / reliability"}


def material(name: str | None) -> tuple[str, dict[str, float]]:
    n = (name or "steel").lower().strip()
    for key in sorted(MATERIALS, key=len, reverse=True):
        if key in n:
            return key, MATERIALS[key]
    return "steel", MATERIALS["steel"]


class FeaError(Exception):
    pass


# ---------------------------------------------------------------- mesh
def _classifier(shape):
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN
    cls = BRepClass3d_SolidClassifier(shape.wrapped)

    def inside(p) -> bool:
        cls.Perform(gp_Pnt(float(p[0]), float(p[1]), float(p[2])), 1e-7)
        return cls.State() == TopAbs_IN
    return inside


def _sample_face(face, h: float) -> np.ndarray:
    """Points ON one face about h apart: its edges divided at h, plus an even (u, v) grid kept where it lies inside
    the face (2-D classifier) and not too close to an edge point. Even on long cylinders, where splitting the
    kernel's thin triangles made ~30x too many points (v0.381)."""
    from OCP.BRepTopAdaptor import BRepTopAdaptor_FClass2d
    from OCP.gp import gp_Pnt2d
    from OCP.TopAbs import TopAbs_IN
    from scipy.spatial import cKDTree
    pts = []
    for e in face.Edges():
        try:
            n = max(2, int(math.ceil(e.Length() / h)))
            pts += [tuple(e.positionAt(i / n)) for i in range(n + 1)]
        except Exception:
            continue
    B = np.array(pts) if pts else np.zeros((0, 3))
    u0, u1, v0, v1 = face._uvBounds()

    def at(u, v):
        p = face._geomAdaptor().Value(u, v)
        return np.array((p.X(), p.Y(), p.Z()))
    um, vm = (u0 + u1) / 2, (v0 + v1) / 2
    lu = sum(np.linalg.norm(at(u0 + (u1 - u0) * (i + 1) / 8, vm) - at(u0 + (u1 - u0) * i / 8, vm)) for i in range(8))
    lv = sum(np.linalg.norm(at(um, v0 + (v1 - v0) * (i + 1) / 8) - at(um, v0 + (v1 - v0) * i / 8)) for i in range(8))
    nu = max(1, min(400, int(math.ceil(lu / h))))
    nv = max(1, min(400, int(math.ceil(lv / h))))
    cls = BRepTopAdaptor_FClass2d(face.wrapped, 1e-7)
    G = []
    for i in range(nu):
        for j in range(nv):
            u = u0 + (u1 - u0) * (i + 0.5) / nu
            v = v0 + (v1 - v0) * (j + 0.5) / nv
            if cls.Perform(gp_Pnt2d(u, v)) == TopAbs_IN:
                G.append(at(u, v))
    G = np.array(G) if G else np.zeros((0, 3))
    if len(G) and len(B):
        d, _ = cKDTree(B).query(G)
        G = G[d > 0.5 * h]
    return np.vstack([B, G]) if len(G) else B


def pick_h(volume: float, area: float, nodes: int) -> float:
    h = (volume / max(nodes, 50)) ** (1 / 3)
    for _ in range(40):                              # vol/h³ + 2.3·area/h² ≈ nodes
        n = volume / h ** 3 + 2.3 * area / h ** 2
        h *= (n / nodes) ** 0.4
    return h


def build_mesh(shape, nodes: int = 3500, seed: int = 1) -> dict[str, Any]:
    from scipy.spatial import Delaunay, cKDTree
    faces = shape.Faces()
    bb = shape.BoundingBox()
    vol, area = float(shape.Volume()), float(shape.Area())
    if vol <= 0:
        raise FeaError("solid ka volume 0 hai")
    h = pick_h(vol, area, nodes)
    pts, fid = [], []
    for i, f in enumerate(faces):
        P = _sample_face(f, h)
        pts.append(P)
        fid.append(np.full(len(P), i))
    P = np.vstack(pts)
    F = np.concatenate(fid)
    key = np.round(P / (h * 1e-3)).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    S = P[first]
    face_nodes: dict[int, set[int]] = {}
    for node, f in zip(inv.tolist(), F.tolist()):
        face_nodes.setdefault(f, set()).add(node)
    inside = _classifier(shape)
    axes = [np.arange(lo + h / 2, hi, h) for lo, hi in ((bb.xmin, bb.xmax), (bb.ymin, bb.ymax), (bb.zmin, bb.zmax))]
    G = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3) if all(len(a) for a in axes) else np.zeros((0, 3))
    if len(G):
        G = G + np.random.default_rng(seed).uniform(-0.15 * h, 0.15 * h, G.shape)   # breaks co-spherical grids
        d, _ = cKDTree(S).query(G)
        G = G[d > 0.5 * h]
        G = np.array([p for p in G if inside(p)]).reshape(-1, 3)
    X = np.vstack([S, G]) if len(G) else S
    if len(X) < 8:
        raise FeaError("mesh ke liye part bahut chhota / patla hai")
    T = Delaunay(X).simplices
    cen = X[T].mean(1)
    T = T[np.array([inside(p) for p in cen])]
    v6 = np.einsum("ij,ij->i", np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]]), X[T[:, 3]] - X[T[:, 0]])
    good = np.abs(v6) > 1e-7 * h ** 3
    T, v6 = T[good], v6[good]
    flip = v6 < 0
    T[flip] = T[flip][:, [0, 2, 1, 3]]
    used = np.unique(T)
    remap = -np.ones(len(X), dtype=np.int64)
    remap[used] = np.arange(len(used))
    X, T = X[used], remap[T]
    face_nodes = {f: {int(remap[n]) for n in ns if remap[n] >= 0} for f, ns in face_nodes.items()}
    mesh_vol = float(np.abs(v6).sum() / 6)
    return {"X": X, "T": T, "face_nodes": face_nodes, "h": h, "volume": vol, "mesh_volume": mesh_vol,
            "faces": faces}


# ---------------------------------------------------------------- selections
def faces_of(shape, faces: list, sel: Any) -> list[int]:
    """CadQuery selector(s) -> face indices of `faces`. 'all' = every face."""
    import cadquery as cq
    sels = sel if isinstance(sel, (list, tuple)) else [sel]
    out: list[int] = []
    for s in sels:
        if s in (None, ""):
            continue
        if str(s).lower() == "all":
            return list(range(len(faces)))
        try:
            picked = cq.Workplane("XY").add(shape).faces(str(s)).vals()
        except Exception as e:
            raise FeaError(f"face selector '{s}' samajh nahi aaya: {type(e).__name__}")
        for p in picked:
            for i, f in enumerate(faces):
                if f.isSame(p) and i not in out:
                    out.append(i)
    if not out:
        raise FeaError(f"selector {sel!r} ne koi face nahi chuna")
    return out


def _facets(m, nodes: set[int]) -> np.ndarray:
    bf = m.boundary_facets()
    tri = m.facets[:, bf]
    arr = np.fromiter(nodes, dtype=np.int64) if nodes else np.zeros(0, np.int64)
    ok = np.isin(tri, arr).all(0)
    return bf[ok]


def _facet_faces(msh: dict, m) -> np.ndarray:
    """v0.381 every boundary facet -> exactly one B-rep face: the face all three corners share; when they share
    none (a sliver across an edge), the nearest of their faces measured by the kernel. Cached on the mesh."""
    if msh.get("_ff") is not None:
        return msh["_ff"]
    mem: dict[int, set[int]] = {}
    for f, ns in msh["face_nodes"].items():
        for n in ns:
            mem.setdefault(n, set()).add(f)
    bf = m.boundary_facets()
    out = np.full(len(bf), -1, dtype=np.int64)
    for k, fc in enumerate(bf):
        a, b, c = (int(x) for x in m.facets[:, fc])
        common = mem.get(a, set()) & mem.get(b, set()) & mem.get(c, set())
        if common:
            out[k] = min(common)
            continue
        cand = mem.get(a, set()) | mem.get(b, set()) | mem.get(c, set())
        if not cand:
            continue
        cen = m.p[:, [a, b, c]].mean(1)
        import cadquery as cq
        v = cq.Vertex.makeVertex(*cen)
        out[k] = min(cand, key=lambda f: msh["faces"][f].distance(v))
    msh["_ff"] = out
    return out


def _facets_for(msh: dict, m, idx: list[int]) -> np.ndarray:
    ff = _facet_faces(msh, m)
    return m.boundary_facets()[np.isin(ff, np.array(idx, dtype=np.int64))]


def _nodes_for(msh: dict, idx: list[int]) -> set[int]:
    s: set[int] = set()
    for i in idx:
        s |= msh["face_nodes"].get(i, set())
    return s


def _surface(m, scalar: np.ndarray, lo: float, hi: float, X: np.ndarray | None = None) -> dict[str, Any]:
    """Boundary triangles coloured by a nodal scalar (blue -> red), for render.draw_view."""
    bf = m.boundary_facets()
    tri = m.facets[:, bf].T
    used = np.unique(tri)
    remap = -np.ones(m.p.shape[1], dtype=np.int64)
    remap[used] = np.arange(len(used))
    P = (X if X is not None else m.p.T)[used]
    vals = scalar[tri].mean(1)
    span = max(hi - lo, 1e-12)
    tc = [list(colormap((v - lo) / span)) for v in vals]
    return {"v": np.round(P, 4).tolist(), "t": remap[tri].tolist(), "tc": tc}


def colormap(x: float) -> tuple[float, float, float]:
    """0 blue -> cyan -> green -> yellow -> 1 red (the usual FEA scale)."""
    x = min(1.0, max(0.0, float(x)))
    stops = [(0.0, (0.13, 0.23, 0.80)), (0.25, (0.10, 0.65, 0.90)), (0.5, (0.20, 0.75, 0.30)),
             (0.75, (0.95, 0.80, 0.15)), (1.0, (0.85, 0.15, 0.12))]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if x <= b:
            f = (x - a) / (b - a)
            return tuple(round(ca[i] + (cb[i] - ca[i]) * f, 4) for i in range(3))
    return stops[-1][1]


def _solve(K, f, D, xyz=None):
    """Condensed solve: PyAMG-preconditioned CG when available (with rigid-body modes), else a direct solve."""
    import scipy.sparse.linalg as sl
    import skfem
    Kc, fc, _x, I = skfem.condense(K, f, D=D)
    Kc = Kc.tocsr()
    x = None
    try:
        import pyamg
        B = None
        if xyz is not None:
            comp = I % 3
            P = xyz[I]
            B = np.zeros((len(I), 6))
            for c in range(3):
                B[comp == c, c] = 1
            B[comp == 0, 3], B[comp == 1, 3] = -P[comp == 0, 1], P[comp == 1, 0]
            B[comp == 1, 4], B[comp == 2, 4] = -P[comp == 1, 2], P[comp == 2, 1]
            B[comp == 0, 5], B[comp == 2, 5] = P[comp == 0, 2], -P[comp == 2, 0]
        ml = pyamg.smoothed_aggregation_solver(Kc, B=B)
        x, info = sl.cg(Kc, fc, M=ml.aspreconditioner(), rtol=1e-9, maxiter=800)
        if info != 0:
            x = None
    except ImportError:
        pass
    if x is None:
        x = sl.spsolve(Kc.tocsc(), fc)
    u = np.zeros(K.shape[0])
    u[I] = x
    return u


def _vm(s):
    return np.sqrt(0.5 * ((s[0, 0] - s[1, 1]) ** 2 + (s[1, 1] - s[2, 2]) ** 2 + (s[2, 2] - s[0, 0]) ** 2)
                   + 3 * (s[0, 1] ** 2 + s[1, 2] ** 2 + s[0, 2] ** 2))


def _vector_dofs_xyz(ib) -> np.ndarray:
    return ib.doflocs.T


# ---------------------------------------------------------------- static
def _assemble(shape, spec: dict, mat: dict, nodes: int) -> dict[str, Any]:
    """The mesh, the stiffness matrix, the load vector and the held dofs - shared by static and buckling."""
    import skfem
    msh = build_mesh(shape, nodes)
    m = skfem.MeshTet(msh["X"].T.copy(), msh["T"].T.copy())
    e = skfem.ElementVector(skfem.ElementTetP2())
    ib = skfem.Basis(m, e)
    E, nu = mat["E"], mat["nu"]
    from skfem.models.elasticity import lame_parameters, linear_elasticity
    K = skfem.asm(linear_elasticity(*lame_parameters(E, nu)), ib)
    f = np.zeros(K.shape[0])
    applied = np.zeros(3)
    faces = msh["faces"]
    fixed_idx = faces_of(shape, faces, spec.get("fixed"))
    fixed_nodes = _nodes_for(msh, fixed_idx)
    ff = _facets_for(msh, m, fixed_idx)
    if not len(ff):
        raise FeaError("support (fixed) faces mesh par nahi mile")
    D = ib.get_dofs(facets=ff).all()
    for ld in spec.get("loads") or []:
        if ld.get("gravity") or ld.get("accel"):
            g = np.array(ld.get("accel") or [0, 0, -9810.0 * float(ld.get("g") or 1)], dtype=float)   # mm/s²
            rho = mat["rho"]

            @skfem.LinearForm
            def body(v, w, g=g, rho=rho):
                return rho * (g[0] * v[0] + g[1] * v[1] + g[2] * v[2])
            f += skfem.asm(body, ib)
            applied += g * mat["rho"] * msh["volume"]
            continue
        idx = faces_of(shape, faces, ld.get("faces"))
        fac = _facets_for(msh, m, idx)
        if not len(fac):
            raise FeaError(f"load faces {ld.get('faces')!r} mesh par nahi mile")
        fb = skfem.FacetBasis(m, e, facets=fac)
        a_mesh = float(skfem.asm(skfem.Functional(lambda w: 1.0 + 0 * w.x[0]), fb))
        if "pressure" in ld:
            p = float(ld["pressure"])

            @skfem.LinearForm
            def press(v, w, p=p):
                return -p * (w.n[0] * v[0] + w.n[1] * v[1] + w.n[2] * v[2])
            f += skfem.asm(press, fb)
            applied += -p * np.array([float(skfem.asm(skfem.Functional(lambda w, k=k: w.n[k]), fb)) for k in range(3)])
        else:
            F = np.array(ld.get("force") or [0, 0, 0], dtype=float)
            t = F / max(a_mesh, 1e-12)

            @skfem.LinearForm
            def trac(v, w, t=t):
                return t[0] * v[0] + t[1] * v[1] + t[2] * v[2]
            f += skfem.asm(trac, fb)
            applied += F
    return {"msh": msh, "m": m, "ib": ib, "K": K, "f": f, "D": D, "applied": applied,
            "fixed_nodes": fixed_nodes, "E": E, "nu": nu}


def _static_once(shape, spec: dict, mat: dict, nodes: int) -> dict[str, Any]:
    import skfem
    from scipy.spatial import cKDTree
    from skfem.helpers import sym_grad
    from skfem.models.elasticity import lame_parameters, linear_stress
    A = _assemble(shape, spec, mat, nodes)
    msh, m, ib, K, f, D = A["msh"], A["m"], A["ib"], A["K"], A["f"], A["D"]
    E, nu, applied, fixed_nodes = A["E"], A["nu"], A["applied"], A["fixed_nodes"]
    e = skfem.ElementVector(skfem.ElementTetP2())
    xyz = _vector_dofs_xyz(ib)
    u = _solve(K, f, D, xyz)
    rsum = _reaction_sum(K, u, D)
    # stress at element vertices, averaged per node
    Xr = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)
    bv = skfem.Basis(m, e, quadrature=(Xr, np.ones(4) / 24))
    sv = linear_stress(*lame_parameters(E, nu))(sym_grad(bv.interpolate(u)))
    acc = np.zeros((3, 3, m.p.shape[1]))
    cnt = np.zeros(m.p.shape[1])
    vol = np.abs(np.linalg.det(np.stack([m.p[:, m.t[i]] - m.p[:, m.t[0]] for i in (1, 2, 3)], 1).transpose(2, 0, 1))) / 6
    q = vol / np.maximum(_edge_max(m) ** 3, 1e-30)      # flat sliver tets (Delaunay) get almost no say
    wgt = vol * np.clip(q / 0.1, 0.02, 1.0)
    for k in range(4):
        nd = m.t[k]
        for a in range(3):
            for b in range(3):
                np.add.at(acc[a, b], nd, sv[a, b, :, k] * wgt)
        np.add.at(cnt, nd, wgt)
    vm = _vm(acc / np.maximum(cnt, 1))
    disp = np.sqrt(sum(u[ib.nodal_dofs[k]] ** 2 for k in range(3)))
    h = msh["h"]
    fx = np.fromiter(fixed_nodes, dtype=np.int64)
    dist = cKDTree(m.p.T[fx]).query(m.p.T)[0] if len(fx) else np.full(m.p.shape[1], 1e9)
    away = dist > 2.0 * h
    peak = float(vm.max())
    peak_away = float(vm[away].max()) if away.any() else peak
    i_peak = int(np.argmax(np.where(away, vm, -1))) if away.any() else int(np.argmax(vm))
    i_disp = int(np.argmax(disp))
    return {"m": m, "vm": vm, "disp": disp, "peak": peak, "peak_away": peak_away, "max_disp": float(disp.max()),
            "at_peak": np.round(m.p[:, i_peak], 2).tolist(), "at_disp": np.round(m.p[:, i_disp], 2).tolist(),
            "applied": applied, "reaction": rsum, "h": h, "nodes": int(m.p.shape[1]), "elements": int(m.t.shape[1]),
            "dofs": int(K.shape[0]), "mesh_vol_ratio": msh["mesh_volume"] / msh["volume"]}


def _edge_max(m) -> np.ndarray:
    P = m.p
    t = m.t
    L = [np.linalg.norm(P[:, t[a]] - P[:, t[b]], axis=0) for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))]
    return np.max(L, axis=0)


def _reaction_sum(K, u, D) -> np.ndarray:
    r = K @ u                                             # at the supports K·u = the support reaction
    comp = D % 3                                          # skfem vector dofs are interleaved x, y, z
    return np.array([r[D[comp == k]].sum() for k in range(3)])


def static(shape, spec: dict) -> dict[str, Any]:
    mname, mat = material(spec.get("material"))
    nodes = int(spec.get("nodes") or 3500)
    t0 = time.time()
    fine = _static_once(shape, spec, mat, nodes)
    conv = None
    if spec.get("converge", True):
        coarse = _static_once(shape, spec, mat, max(400, nodes // 3))
        dd = abs(fine["max_disp"] - coarse["max_disp"]) / max(fine["max_disp"], 1e-12)
        ds = abs(fine["peak_away"] - coarse["peak_away"]) / max(fine["peak_away"], 1e-12)
        conv = {"disp_change_pct": round(100 * dd, 1), "stress_change_pct": round(100 * ds, 1),
                "ok": dd < 0.05 and ds < 0.15}
    eq_err = float(np.linalg.norm(fine["applied"] + fine["reaction"]) / max(np.linalg.norm(fine["applied"]), 1e-12))
    sf = mat["yield"] / max(fine["peak_away"], 1e-12)
    min_sf = float(spec.get("min_sf") or 0) or None
    vm = fine["vm"]
    lo, hi = 0.0, max(float(np.percentile(vm, 99.5)), 1e-9)
    res = {"kind": "static", "material": mname, "E_MPa": mat["E"], "yield_MPa": mat["yield"],
           "max_disp_mm": round(fine["max_disp"], 5), "at_disp": fine["at_disp"],
           "peak_vm_MPa": round(fine["peak"], 2), "peak_vm_away_MPa": round(fine["peak_away"], 2),
           "at_peak": fine["at_peak"], "safety_factor": round(sf, 2), "min_sf": min_sf,
           "passes": (sf >= min_sf) if min_sf else None,
           "applied_N": np.round(fine["applied"], 3).tolist(), "equilibrium_error_pct": round(100 * eq_err, 3),
           "convergence": conv, "mesh": {"nodes": fine["nodes"], "elements": fine["elements"], "dofs": fine["dofs"],
                                         "h_mm": round(fine["h"], 3), "volume_match_pct": round(100 * fine["mesh_vol_ratio"], 2),
                                         "element": "quadratic tetra (P2)"},
           "scale": {"label": "von Mises stress (MPa)", "lo": lo, "hi": round(hi, 3)},
           "seconds": round(time.time() - t0, 1)}
    fat = spec.get("fatigue")
    if fat:                                              # v0.381 the same load, repeated: life at the hot spot
        fat = fat if isinstance(fat, dict) else {}
        kind = str(fat.get("load", "zero_to_max")).lower()
        smax = fine["peak_away"]
        smin = -smax if kind in ("reversed", "fully_reversed") else float(fat.get("R", 0.0)) * smax if kind == "ratio" else 0.0
        en = endurance(mname, mat, fat.get("finish", "machined"), fat.get("size_mm"), float(fat.get("reliability", 90)))
        fe = fatigue_eval(smax, smin, en, float(fat.get("life", 1e6)))
        need = float(fat.get("min_sf") or min_sf or 1.5)
        fe.update({"load": kind, "need_sf": need, "passes": fe["fatigue_sf"] >= need})
        res["fatigue"] = fe
    res["surface"] = _surface(fine["m"], vm, lo, hi)
    return res


# ---------------------------------------------------------------- v0.432 buckling (linear eigenvalue)
def buckling(shape, spec: dict) -> dict[str, Any]:
    """Does it FOLD before it breaks? The part is loaded once, the stress that comes out stiffens (or softens) it,
    and the load factor at which the softened part has no stiffness left in some shape is the buckling factor:
      (K + lambda Kg) phi = 0,  Kg = integral sigma_ij du_k/dx_i dv_k/dx_j dV   (the geometric stiffness)
    lambda = 1 means it buckles under exactly the load she gave; 3 means at three times it. Solved as the
    generalized symmetric problem (-Kg) phi = (1/lambda) K phi, so K stays positive definite and the FIRST
    (smallest positive) factor comes out first. Checked in tests against Euler's column (0.1 % on mode 1, and
    mode 2 at 9x as theory says). HONEST LIMIT: this is the PERFECT part. A real thin shell / tube dents first and
    buckles lower - the knock-down is said in the result, never hidden."""
    import scipy.sparse.linalg as sl
    import skfem
    from skfem.helpers import grad, sym_grad
    from skfem.models.elasticity import lame_parameters, linear_stress
    t0 = time.time()
    mname, mat = material(spec.get("material"))
    nodes = int(spec.get("nodes") or 3000)
    A = _assemble(shape, spec, mat, nodes)
    m, ib, K, f, D = A["m"], A["ib"], A["K"], A["f"], A["D"]
    E, nu, applied = A["E"], A["nu"], A["applied"]
    if not (spec.get("loads") or []):
        raise FeaError("buckling: loads chahiye (buckling ek compression ka load factor hai)")
    u = _solve(K, f, D, _vector_dofs_xyz(ib))
    sig = linear_stress(*lame_parameters(E, nu))(sym_grad(ib.interpolate(u)))

    @skfem.BilinearForm
    def kgeom(uu, vv, w):
        sg = w["sig"]
        return sum(sg[i][j] * sum(grad(uu)[k][i] * grad(vv)[k][j] for k in range(3))
                   for i in range(3) for j in range(3))
    Kg = skfem.asm(kgeom, ib, sig=sig)
    I = ib.complement_dofs(D)
    n = max(1, min(int(spec.get("modes") or 3), 6))
    lam, vec = sl.eigsh((-Kg)[I][:, I].tocsc(), k=min(n + 2, len(I) - 2), M=K[I][:, I].tocsc(), which="LA")
    order = np.argsort(-lam)
    lam, vec = lam[order], vec[:, order]
    pos = [(float(1.0 / x), k) for k, x in enumerate(lam) if x > 1e-12]
    comp = float(np.min(sig[0][0] + sig[1][1] + sig[2][2])) / 3.0        # most compressive mean stress (MPa)
    if not pos:
        return {"kind": "buckling", "material": mname, "load_factor": None, "buckles": False,
                "note": "nothing in this part is in compression under this load, so it cannot buckle - "
                        "the stress check is the one that matters here",
                "applied_N": np.round(applied, 3).tolist(), "mean_stress_min_MPa": round(comp, 3),
                "mesh": {"nodes": int(m.p.shape[1]), "elements": int(m.t.shape[1]), "h_mm": round(A["msh"]["h"], 3)},
                "seconds": round(time.time() - t0, 1)}
    factors = [round(p[0], 3) for p in pos[:n]]
    lf = pos[0][0]
    vmq = float(np.percentile(_vm(sig), 99.5))                           # 99.5 % so a clamp spike cannot lie
    yield_lf = mat["yield"] / max(vmq, 1e-12)                            # the factor at which it first yields
    uu = np.zeros(K.shape[0])
    uu[I] = vec[:, pos[0][1]]
    mag = np.sqrt(sum(uu[ib.nodal_dofs[k]] ** 2 for k in range(3)))
    mag = mag / max(mag.max(), 1e-12)
    need = float(spec.get("min_lf") or spec.get("min_sf") or 0) or 2.0
    given = bool(spec.get("min_lf") or spec.get("min_sf"))
    Fmag = float(np.linalg.norm(applied))
    res = {"kind": "buckling", "material": mname, "E_MPa": mat["E"], "load_factor": round(lf, 3),
           "factors": factors, "buckles": lf < 1.0, "need_lf": need, "need_given": given,
           "passes": lf >= need, "applied_N": np.round(applied, 3).tolist(),
           "critical_load_N": round(Fmag * lf, 2) if Fmag > 1e-9 else None,
           "mean_stress_min_MPa": round(comp, 3), "yield_factor": round(yield_lf, 3),
           "governs": "buckling" if lf < yield_lf else "strength",
           "mesh": {"nodes": int(m.p.shape[1]), "elements": int(m.t.shape[1]), "h_mm": round(A["msh"]["h"], 3),
                    "element": "quadratic tetra (P2)"},
           "scale": {"label": "Buckling mode 1 (relative)", "lo": 0, "hi": 1},
           "surface": _surface(m, mag, 0.0, 1.0),
           "note": ("this part is nowhere near folding - it would yield / break long before it buckles "
                    f"(yields at x{yield_lf:.3g}, folds at x{lf:.3g}), so the stress check is the one that "
                    "matters here" if lf > 20 * yield_lf else
                    "linear buckling of the PERFECT shape; a real thin wall / tube with a dent buckles lower "
                    "(thin shells 40-70 % of this), so treat the factor as the ceiling, not the promise"),
           "not_a_buckling_case": bool(lf > 20 * yield_lf),
           "seconds": round(time.time() - t0, 1)}
    if spec.get("converge", True) and nodes >= 1200:
        try:
            cs = dict(spec)
            cs["converge"] = False
            cs["nodes"] = max(500, nodes // 3)
            cs["modes"] = 1
            co = buckling(shape, cs)
            if co.get("load_factor"):
                ch = abs(lf - co["load_factor"]) / max(lf, 1e-12)
                res["convergence"] = {"coarse_lf": co["load_factor"], "change_pct": round(100 * ch, 1),
                                      "ok": ch < 0.10}
        except Exception:
            res["convergence"] = None
    return res


# ---------------------------------------------------------------- thermal
def thermal(shape, spec: dict) -> dict[str, Any]:
    import skfem
    from skfem.helpers import dot, grad
    t0 = time.time()
    mname, mat = material(spec.get("material"))
    k = float(spec.get("k") or mat["k"])
    msh = build_mesh(shape, int(spec.get("nodes") or 3500))
    m = skfem.MeshTet(msh["X"].T.copy(), msh["T"].T.copy())
    e = skfem.ElementTetP2()
    ib = skfem.Basis(m, e)

    @skfem.BilinearForm
    def cond(u, v, w):
        return k * dot(grad(u), grad(v))
    A = skfem.asm(cond, ib)
    b = np.zeros(A.shape[0])
    faces = msh["faces"]
    heat_in = 0.0
    for hq in spec.get("heat") or []:
        fac = _facets_for(msh, m, faces_of(shape, faces, hq.get("faces")))
        fb = skfem.FacetBasis(m, e, facets=fac)
        area = float(skfem.asm(skfem.Functional(lambda w: 1.0 + 0 * w.x[0]), fb))
        q = float(hq.get("watts", 0)) / max(area, 1e-12)
        b += skfem.asm(skfem.LinearForm(lambda v, w, q=q: q * v), fb)
        heat_in += float(hq.get("watts", 0))
    for cv in spec.get("convection") or []:
        fac = _facets_for(msh, m, faces_of(shape, faces, cv.get("faces")))
        fb = skfem.FacetBasis(m, e, facets=fac)
        hc = float(cv.get("h", 10.0)) * 1e-6               # W/(m²K) -> W/(mm²K)
        ta = float(cv.get("t_amb", 25.0))
        A = A + skfem.asm(skfem.BilinearForm(lambda u, v, w, hc=hc: hc * u * v), fb)
        b += skfem.asm(skfem.LinearForm(lambda v, w, hc=hc, ta=ta: hc * ta * v), fb)
    D_list, xD = [], np.zeros(A.shape[0])
    for tf in spec.get("temps") or []:
        fac = _facets_for(msh, m, faces_of(shape, faces, tf.get("faces")))
        dd = ib.get_dofs(facets=fac).all()
        xD[dd] = float(tf.get("temp", 25.0))
        D_list.append(dd)
    if not D_list and not spec.get("convection"):
        raise FeaError("thermal ke liye kam se kam ek fixed temperature ya convection face chahiye")
    import scipy.sparse.linalg as sl
    if D_list:
        D = np.unique(np.concatenate(D_list))
        T = skfem.solve(*skfem.condense(A, b, x=xD, D=D))
    else:
        T = sl.spsolve(A.tocsc(), b)
    Tn = T[ib.nodal_dofs[0]]
    lo, hi = float(Tn.min()), float(Tn.max())
    return {"kind": "thermal", "material": mname, "k_W_mmK": k, "t_max_C": round(hi, 2), "t_min_C": round(lo, 2),
            "heat_in_W": heat_in, "at_max": np.round(m.p[:, int(np.argmax(Tn))], 2).tolist(),
            "mesh": {"nodes": int(m.p.shape[1]), "elements": int(m.t.shape[1]), "h_mm": round(msh["h"], 3)},
            "scale": {"label": "Temperature (°C)", "lo": round(lo, 2), "hi": round(hi, 2)},
            "surface": _surface(m, Tn, lo, hi), "seconds": round(time.time() - t0, 1)}


# ---------------------------------------------------------------- modal
def modal(shape, spec: dict) -> dict[str, Any]:
    import scipy.sparse.linalg as sl
    import skfem
    from skfem.models.elasticity import lame_parameters, linear_elasticity
    t0 = time.time()
    mname, mat = material(spec.get("material"))
    msh = build_mesh(shape, int(spec.get("nodes") or 3000))
    m = skfem.MeshTet(msh["X"].T.copy(), msh["T"].T.copy())
    e = skfem.ElementVector(skfem.ElementTetP2())
    ib = skfem.Basis(m, e)
    K = skfem.asm(linear_elasticity(*lame_parameters(mat["E"], mat["nu"])), ib)
    rho = mat["rho"]
    M = skfem.asm(skfem.BilinearForm(lambda u, v, w: rho * (u[0] * v[0] + u[1] * v[1] + u[2] * v[2])), ib)
    n = max(1, min(int(spec.get("modes") or 6), 12))
    free = not spec.get("fixed")
    if free:
        I = np.arange(K.shape[0])
        Kc, Mc = K, M
        extra = 6
    else:
        fac = _facets_for(msh, m, faces_of(shape, msh["faces"], spec.get("fixed")))
        D = ib.get_dofs(facets=fac).all()
        I = ib.complement_dofs(D)
        Kc, Mc = K[I][:, I], M[I][:, I]
        extra = 0
    lam, vec = sl.eigsh(Kc.tocsc(), k=n + extra, M=Mc.tocsc(), sigma=-1.0 if free else 0.0, which="LM")
    order = np.argsort(lam)
    lam, vec = lam[order][extra:], vec[:, order][:, extra:]
    freqs = [round(float(math.sqrt(max(x, 0.0)) / (2 * math.pi)), 2) for x in lam]
    u = np.zeros(K.shape[0])
    u[I] = vec[:, 0]
    mag = np.sqrt(sum(u[ib.nodal_dofs[k]] ** 2 for k in range(3)))
    mag = mag / max(mag.max(), 1e-12)
    avoid = spec.get("avoid_hz")
    warn = None
    if avoid:
        lo_a, hi_a = (avoid if isinstance(avoid, (list, tuple)) else (0, float(avoid)))[:2]
        hits = [f for f in freqs if lo_a <= f <= hi_a]
        warn = {"band_hz": [lo_a, hi_a], "inside": hits, "ok": not hits}
    return {"kind": "modal", "material": mname, "frequencies_hz": freqs, "supports": "free-free" if free else spec.get("fixed"),
            "resonance": warn, "mesh": {"nodes": int(m.p.shape[1]), "elements": int(m.t.shape[1]), "h_mm": round(msh["h"], 3)},
            "scale": {"label": "Mode 1 shape (relative)", "lo": 0, "hi": 1},
            "surface": _surface(m, mag, 0.0, 1.0), "seconds": round(time.time() - t0, 1)}


# ---------------------------------------------------------------- v0.381 flow (laminar CFD)
FLUIDS = {"water": (1.0e-9, 1.0e-9), "air": (1.204e-12, 1.81e-11), "oil": (8.7e-10, 8.7e-8),
          "diesel": (8.32e-10, 2.4e-9), "glycerin": (1.26e-9, 1.41e-6)}      # rho t/mm³, mu N·s/mm² (20 °C)


def flow(shape, spec: dict) -> dict[str, Any]:
    """Steady incompressible flow through / around the FLUID body `shape` (Taylor-Hood P2-P1, Stokes then Picard
    Oseen steps for inertia). Inlet: a flow rate (L/min) or a mean speed (mm/s), spread evenly and scaled so the
    flux is exact; outlet: free (zero pressure); every other face a no-slip wall. Laminar only - above Re 2000 the
    result is flagged NOT valid (turbulence needs a RANS model; the pipe hand-calc is given instead)."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as sl
    import skfem
    from skfem.helpers import ddot, div, dot, grad
    t0 = time.time()
    fname = str(spec.get("fluid") or "water").lower()
    if fname not in FLUIDS:
        raise FeaError(f"fluid: {', '.join(FLUIDS)}")
    rho, mu = FLUIDS[fname]
    msh = build_mesh(shape, int(spec.get("nodes") or 3000))
    m = skfem.MeshTet(msh["X"].T.copy(), msh["T"].T.copy())
    eu, ep = skfem.ElementVector(skfem.ElementTetP2()), skfem.ElementTetP1()
    ub = skfem.Basis(m, eu)
    pb = skfem.Basis(m, ep, quadrature=ub.quadrature)
    faces = msh["faces"]
    in_idx = faces_of(shape, faces, spec.get("inlet"))
    out_idx = faces_of(shape, faces, spec.get("outlet"))
    wall_idx = [i for i in range(len(faces)) if i not in in_idx and i not in out_idx]
    fin = _facets_for(msh, m, in_idx)
    fout = _facets_for(msh, m, out_idx)
    ffc = _facet_faces(msh, m)                          # every other boundary facet is a no-slip wall
    fwall = m.boundary_facets()[~np.isin(ffc, np.array(in_idx + out_idx, dtype=np.int64))]
    del wall_idx
    if not len(fin) or not len(fout):
        raise FeaError("inlet / outlet faces mesh par nahi mile")
    fbin = skfem.FacetBasis(m, eu, facets=fin)
    area_in = float(skfem.asm(skfem.Functional(lambda w: 1.0 + 0 * w.x[0]), fbin))
    if spec.get("flow_lpm"):
        Q = float(spec["flow_lpm"]) * 1e6 / 60.0                   # mm³/s
    else:
        Q = float(spec.get("velocity_mm_s") or 100.0) * area_in
    nu_ = ub.N
    d_in = ub.get_dofs(facets=fin).all()
    d_wall = ub.get_dofs(facets=fwall).all() if len(fwall) else np.zeros(0, np.int64)
    # inflow direction = minus the inlet's outward normal (mean over the inlet)
    nvec = -np.array([float(skfem.asm(skfem.Functional(lambda w, k=k: w.n[k]), fbin)) for k in range(3)]) / area_in
    nvec /= max(np.linalg.norm(nvec), 1e-12)
    xD = np.zeros(nu_)
    comp = d_in % 3
    for k in range(3):
        xD[d_in[comp == k]] = nvec[k]
    xD[d_wall] = 0.0
    flux1 = float(skfem.asm(skfem.Functional(lambda w: -dot(w["u"], w.n)), fbin, u=fbin.interpolate(xD)))
    if flux1 <= 0:
        raise FeaError("inlet se flow andar nahi ja raha (inlet face check karo)")
    xD *= Q / flux1                                                  # exactly Q enters
    Dd = np.unique(np.concatenate([d_wall, d_in]))
    I = np.setdiff1d(np.arange(nu_), Dd)
    A = skfem.asm(skfem.BilinearForm(lambda u, v, w: mu * ddot(grad(u), grad(v))), ub)
    B = skfem.asm(skfem.BilinearForm(lambda u, q, w: -div(u) * q), ub, pb)
    Mp = skfem.asm(skfem.BilinearForm(lambda p, q, w: p * q / mu), pb)
    md = 1.0 / Mp.diagonal()
    u = xD.copy()
    p = np.zeros(pb.N)
    dh = float(spec.get("dh_mm") or 4 * area_in / max(_perimeter(shape, faces, in_idx), 1e-9))
    umean = Q / area_in
    re = rho * umean * dh / mu
    picard = 0 if (re < 1 or spec.get("inertia") is False) else min(25, int(spec.get("iterations") or 15))
    try:
        import pyamg
    except ImportError:
        pyamg = None
    hist = []
    for it in range(picard + 1):
        if it == 0:
            K_u = A
        else:
            wv = ub.interpolate(u)
            C = skfem.asm(skfem.BilinearForm(lambda uu, v, w: rho * dot(np.einsum("ij...,j...->i...", grad(uu), w["w"]), v)), ub, w=wv)
            K_u = A + C
        Kii = K_u[I][:, I].tocsr()
        Bi = B[:, I].tocsr()
        rhs = np.concatenate([-(K_u[I][:, Dd] @ xD[Dd]), -(B[:, Dd] @ xD[Dd])])
        K = sp.bmat([[Kii, Bi.T], [Bi, None]], "csr")
        if pyamg is not None:
            ml = (pyamg.smoothed_aggregation_solver(A[I][:, I].tocsr()) if it == 0 else
                  pyamg.smoothed_aggregation_solver(Kii, symmetry="nonsymmetric"))
            MA = ml.aspreconditioner(cycle="V")
            n_i = len(I)
            P = sl.LinearOperator(K.shape, matvec=lambda x: np.concatenate([MA @ x[:n_i], md * x[n_i:]]))
            x0 = np.concatenate([u[I], p])
            if it == 0:
                x, info = sl.minres(K, rhs, x0=x0, M=P, rtol=1e-9, maxiter=4000)
            else:
                x, info = sl.gmres(K, rhs, x0=x0, M=P, rtol=1e-7, restart=60, maxiter=6)
            if info != 0:
                x = sl.spsolve(K.tocsc(), rhs)
        else:
            x = sl.spsolve(K.tocsc(), rhs)
        unew = xD.copy()
        unew[I] = x[:len(I)]
        change = float(np.linalg.norm(unew - u) / max(np.linalg.norm(unew), 1e-12))
        u = unew if it == 0 else 0.7 * unew + 0.3 * u
        p = x[len(I):]
        hist.append(round(change, 5))
        if it > 0 and change < 1e-3:
            break
        if time.time() - t0 > float(spec.get("max_seconds") or 420):
            break
    converged = picard == 0 or (hist and hist[-1] < 5e-3)
    vert_in = np.unique(m.facets[:, fin])
    vert_out = np.unique(m.facets[:, fout])
    dp = float(p[vert_in].mean() - p[vert_out].mean()) * 1e6       # Pa
    fbo = skfem.FacetBasis(m, eu, facets=fout)
    q_out = float(skfem.asm(skfem.Functional(lambda w: dot(w["u"], w.n)), fbo, u=fbo.interpolate(u)))
    speed = np.sqrt(sum(u[ub.nodal_dofs[k]] ** 2 for k in range(3)))
    pn = p * 1e6
    lo, hi = float(pn.min()), float(pn.max())
    regime = "creeping (Stokes)" if re < 1 else "laminar" if re < 2000 else "transitional / turbulent - laminar result NOT valid"
    res = {"kind": "flow", "fluid": fname, "flow_mm3_s": round(Q, 3), "flow_lpm": round(Q * 60 / 1e6, 4),
           "mean_inlet_speed_mm_s": round(umean, 3), "max_speed_mm_s": round(float(speed.max()), 3),
           "pressure_drop_Pa": round(dp, 4), "reynolds": round(re, 1), "regime": regime, "valid": re < 2000,
           "hydraulic_diameter_mm": round(dh, 3), "mass_balance_pct": round(100 * q_out / Q, 2),
           "iterations": len(hist), "converged": bool(converged), "history": hist,
           "mesh": {"nodes": int(m.p.shape[1]), "elements": int(m.t.shape[1]), "h_mm": round(msh["h"], 3),
                    "element": "Taylor-Hood P2-P1"},
           "scale": {"label": "Pressure on the walls (Pa)", "lo": round(lo, 4), "hi": round(hi, 4)},
           "seconds": round(time.time() - t0, 1)}
    if spec.get("max_dp_pa") is not None:
        res["max_dp_pa"] = float(spec["max_dp_pa"])
        res["passes"] = dp <= float(spec["max_dp_pa"])
    if re >= 2000 and dh > 0:
        f = 0.25 / math.log10(5.74 / re ** 0.9) ** 2
        res["turbulent_estimate_Pa_per_m"] = round(f / (dh / 1000) * (rho * 1e12) * (umean / 1000) ** 2 / 2, 2)
    res["surface"] = _surface(m, pn, lo, hi)
    return res


def _perimeter(shape, faces, idx) -> float:
    return sum(sum(e.Length() for e in faces[i].outerWire().Edges()) for i in idx)


def run(shape, spec: dict) -> dict[str, Any]:
    kind = str(spec.get("kind") or "static").lower()
    fn = {"static": static, "stress": static, "thermal": thermal, "heat": thermal, "modal": modal,
          "vibration": modal, "flow": flow, "cfd": flow, "buckling": buckling, "buckle": buckling}.get(kind)
    if fn is None:
        raise FeaError(f"analysis kind '{kind}' nahi hai (static / thermal / modal / flow / buckling)")
    return fn(shape, spec)
