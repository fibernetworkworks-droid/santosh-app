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
Units: mm, N, MPa, tonne/mm³, W, W/(mm·K), °C. Validated in tests against beam theory and 1-D conduction.
Libraries: scikit-fem (BSD-3), SciPy (BSD), PyAMG (MIT, optional). DRAFT results for an engineer's review."""
from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

# E MPa, nu, rho t/mm³, yield MPa, k W/(mm·K), alpha 1/K
MATERIALS: dict[str, dict[str, float]] = {
    "steel":      {"E": 200000, "nu": 0.29, "rho": 7.85e-9, "yield": 250, "k": 0.050, "alpha": 12e-6},
    "mild steel": {"E": 200000, "nu": 0.29, "rho": 7.85e-9, "yield": 250, "k": 0.050, "alpha": 12e-6},
    "stainless":  {"E": 193000, "nu": 0.29, "rho": 8.00e-9, "yield": 215, "k": 0.016, "alpha": 17e-6},
    "aluminium":  {"E": 68900, "nu": 0.33, "rho": 2.70e-9, "yield": 276, "k": 0.167, "alpha": 23.6e-6},
    "aluminum":   {"E": 68900, "nu": 0.33, "rho": 2.70e-9, "yield": 276, "k": 0.167, "alpha": 23.6e-6},
    "brass":      {"E": 100000, "nu": 0.34, "rho": 8.50e-9, "yield": 200, "k": 0.109, "alpha": 19e-6},
    "copper":     {"E": 117000, "nu": 0.34, "rho": 8.96e-9, "yield": 70, "k": 0.385, "alpha": 17e-6},
    "titanium":   {"E": 113800, "nu": 0.34, "rho": 4.43e-9, "yield": 880, "k": 0.0067, "alpha": 8.6e-6},
    "cast iron":  {"E": 110000, "nu": 0.26, "rho": 7.20e-9, "yield": 130, "k": 0.052, "alpha": 10.5e-6},
    "abs":        {"E": 2100, "nu": 0.35, "rho": 1.04e-9, "yield": 40, "k": 0.00017, "alpha": 90e-6},
    "pla":        {"E": 3500, "nu": 0.36, "rho": 1.24e-9, "yield": 50, "k": 0.00013, "alpha": 68e-6},
    "petg":       {"E": 2100, "nu": 0.38, "rho": 1.27e-9, "yield": 45, "k": 0.00020, "alpha": 68e-6},
    "nylon":      {"E": 2700, "nu": 0.39, "rho": 1.14e-9, "yield": 70, "k": 0.00025, "alpha": 80e-6},
    "pom":        {"E": 2900, "nu": 0.35, "rho": 1.41e-9, "yield": 65, "k": 0.00031, "alpha": 110e-6},
    "polycarbonate": {"E": 2400, "nu": 0.37, "rho": 1.20e-9, "yield": 62, "k": 0.00020, "alpha": 65e-6},
    "wood":       {"E": 11000, "nu": 0.30, "rho": 0.60e-9, "yield": 40, "k": 0.00012, "alpha": 5e-6},
}


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
    """Points ON one face, no two triangle corners further than h apart (B-rep tessellation, then split long edges)."""
    vv, tt = face.tessellate(max(h * 0.15, 1e-3), 0.2)
    V = [np.array((p.x, p.y, p.z)) for p in vv]
    tris = [tuple(t) for t in tt]
    out = list(V)
    mids: dict[tuple[int, int], int] = {}
    guard = 0
    while tris and guard < 400000:
        guard += 1
        a, b, c = tris.pop()
        L = [np.linalg.norm(V[b] - V[a]), np.linalg.norm(V[c] - V[b]), np.linalg.norm(V[a] - V[c])]
        if max(L) <= h:
            continue
        k = int(np.argmax(L))
        tri = [a, b, c]
        i0, i1, i2 = tri[k], tri[(k + 1) % 3], tri[(k + 2) % 3]
        key = (min(i0, i1), max(i0, i1))
        if key not in mids:
            V.append((V[i0] + V[i1]) / 2)
            out.append(V[-1])
            mids[key] = len(V) - 1
        mi = mids[key]
        tris += [(i0, mi, i2), (mi, i1, i2)]
    return np.array(out)


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
def _static_once(shape, spec: dict, mat: dict, nodes: int) -> dict[str, Any]:
    import skfem
    from scipy.spatial import cKDTree
    from skfem.helpers import sym_grad
    from skfem.models.elasticity import lame_parameters, linear_elasticity, linear_stress
    msh = build_mesh(shape, nodes)
    m = skfem.MeshTet(msh["X"].T.copy(), msh["T"].T.copy())
    e = skfem.ElementVector(skfem.ElementTetP2())
    ib = skfem.Basis(m, e)
    E, nu = mat["E"], mat["nu"]
    K = skfem.asm(linear_elasticity(*lame_parameters(E, nu)), ib)
    f = np.zeros(K.shape[0])
    applied = np.zeros(3)
    faces = msh["faces"]
    fixed_idx = faces_of(shape, faces, spec.get("fixed"))
    fixed_nodes = _nodes_for(msh, fixed_idx)
    ff = _facets(m, fixed_nodes)
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
        fac = _facets(m, _nodes_for(msh, idx))
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
    res["surface"] = _surface(fine["m"], vm, lo, hi)
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
        fac = _facets(m, _nodes_for(msh, faces_of(shape, faces, hq.get("faces"))))
        fb = skfem.FacetBasis(m, e, facets=fac)
        area = float(skfem.asm(skfem.Functional(lambda w: 1.0 + 0 * w.x[0]), fb))
        q = float(hq.get("watts", 0)) / max(area, 1e-12)
        b += skfem.asm(skfem.LinearForm(lambda v, w, q=q: q * v), fb)
        heat_in += float(hq.get("watts", 0))
    for cv in spec.get("convection") or []:
        fac = _facets(m, _nodes_for(msh, faces_of(shape, faces, cv.get("faces"))))
        fb = skfem.FacetBasis(m, e, facets=fac)
        hc = float(cv.get("h", 10.0)) * 1e-6               # W/(m²K) -> W/(mm²K)
        ta = float(cv.get("t_amb", 25.0))
        A = A + skfem.asm(skfem.BilinearForm(lambda u, v, w, hc=hc: hc * u * v), fb)
        b += skfem.asm(skfem.LinearForm(lambda v, w, hc=hc, ta=ta: hc * ta * v), fb)
    D_list, xD = [], np.zeros(A.shape[0])
    for tf in spec.get("temps") or []:
        fac = _facets(m, _nodes_for(msh, faces_of(shape, faces, tf.get("faces"))))
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
        fac = _facets(m, _nodes_for(msh, faces_of(shape, msh["faces"], spec.get("fixed"))))
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


def run(shape, spec: dict) -> dict[str, Any]:
    kind = str(spec.get("kind") or "static").lower()
    fn = {"static": static, "stress": static, "thermal": thermal, "heat": thermal, "modal": modal,
          "vibration": modal}.get(kind)
    if fn is None:
        raise FeaError(f"analysis kind '{kind}' nahi hai (static / thermal / modal)")
    return fn(shape, spec)
