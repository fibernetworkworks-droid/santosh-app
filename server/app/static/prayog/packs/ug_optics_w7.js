/* Kernel pack (browser twin of app/prayog/packs/ug_optics_w7.py): the B.Sc. / B.Tech applied-optics bench.
   Same formulas, same order of operations, so both sides give the same numbers. Every kernel is a "set the control,
   read the detector" instrument with read(p), plan(p) and calc(rows, p); measure(p) = plan -> read -> calc.
     w7_tir        n = sqrt(1 + ((sin e + cos A) / sin A)^2)            w7_wollaston  n = 1 / sin(half the angle between cut-offs)
     w7_nodal      F = f1 f2 / (f1 + f2 - d)                            w7_biprism    lambda = beta sqrt(d1 d2) / D
     w7_fringes    lambda = 2 dx / N (and air index, expansion)         w7_fabry      finesse = pi sqrt(R) / (1 - R)
     w7_fts        V(x) = exp(-2 pi^2 s^2 x^2)                          w7_corona     dark rings at the zeros of J1
     w7_resolve    lambda / a = s / D                                   w7_malus      I = Imin + (Imax - Imin) cos^2(theta - theta0)
     w7_babinet    sin 2chi = sin 2psi sin delta                        w7_nearfield  I(r) / I(0) = 1 - (r / a)^g
     w7_bend       Gloge's guided fraction on a bend                    w7_splice     overlap of two offset cores
     w7_mfd        MFD = 2 lambda / (pi theta0)                         w7_ld         P = eta (I - Ith)
   Deterministic: no randomness, no wall clock. */
(function (root) {
  'use strict';
  var HK = (root && root.HoolaKernels) ||
    (typeof module !== 'undefined' && module.exports && module.exports.register ? module.exports : null);
  if (!HK) throw new Error('HoolaKernels is not loaded');
  var PI = Math.PI;
  var J1_ZEROS = [3.8317059702075125, 7.015586669815619, 10.173468135062722];
  var SIG_FWHM = 2.3548200450309493;

  function fin(v) { v = Number(v); return isFinite(v) ? v : 0.0; }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function rows(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) {
        v = rs[i] ? rs[i][keys[j]] : undefined;
        if (v === undefined || v === null || v === '' || typeof v === 'boolean') { ok = false; break; }
        v = Number(v); if (!isFinite(v)) { ok = false; break; } vals.push(v);
      }
      if (ok) out.push(vals);
    }
    return out;
  }
  function mean(xs) { var s = 0.0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0.0; }
  function line(xs, ys) {
    var n = xs.length, sx = 0.0, sy = 0.0, sxx = 0.0, sxy = 0.0, i, den, m;
    if (n < 2) return [0.0, 0.0];
    for (i = 0; i < n; i++) { sx += xs[i]; sy += ys[i]; sxx += xs[i] * xs[i]; sxy += xs[i] * ys[i]; }
    den = n * sxx - sx * sx;
    if (den === 0.0) return [0.0, 0.0];
    m = (n * sxy - sx * sy) / den;
    return [m, (sy - m * sx) / n];
  }
  function sqrt(v) { return v > 0.0 ? Math.sqrt(v) : 0.0; }
  function asin(v) { return Math.asin(clamp(v, -1.0, 1.0)); }
  function acos(v) { return Math.acos(clamp(v, -1.0, 1.0)); }
  function ln(v) { return v > 0.0 ? Math.log(v) : 0.0; }
  function sinc2(u) { if (Math.abs(u) < 1e-9) return 1.0; var q = Math.sin(u) / u; return q * q; }
  function j1(u) {
    var h = u / 2.0, term = h, tot = h, k;
    for (k = 1; k < 40; k++) { term = -term * h * h / (k * (k + 1.0)); tot += term; }
    return tot;
  }
  function col(r, i) { var out = [], k; for (k = 0; k < r.length; k++) out.push(r[k][i]); return out; }
  function merge(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; for (k in b) o[k] = b[k]; return o; }
  function scan(K) {
    K.init = function () { return { t: 0.0 }; };
    K.step = function (s, p, dt) { s.t += dt; };
    K.view = function (s, p) { return K.read(p); };
    K.table = function (p) {
      var pl = K.plan(p), out = [], i;
      for (i = 0; i < pl.length; i++) out.push(merge(pl[i], K.read(merge(p, pl[i]))));
      return out;
    };
    K.measure = function (p) { var r = K.table(p); return { result: fin(K.calc(r, p)), rows: r.length }; };
    return K;
  }

  // ---------------------------------------------------------------------- critical emergence from a prism
  var Tir = scan({
    PARAMS: { A: PI / 3, n: 1.5168, nl: 1.0, mode: 0.0, x0: 0.6109, x: 0.6109, fov: 0.02 },
    VARS: ['x', 'bright', 'refl', 'e'],
    e: function (p) {
      var nout = p.mode > 0.5 ? p.nl : 1.0, r1 = asin(nout / p.n);
      return asin(p.n * Math.sin(p.A - r1));
    },
    read: function (p) {
      var e = Tir.e(p);
      return { x: p.x, bright: clamp(0.5 + (p.x - (p.x0 + e)) / p.fov, 0.0, 1.0), refl: 2.0 * (p.x - p.x0), e: e };
    },
    plan: function (p) { return [{ x: p.x0 + Tir.e(p) }, { x: p.x0 }]; },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'refl']), i, norm, edge, e, sa, ca, q2;
      if (r.length < 2) return 0.0;
      norm = r[0];
      for (i = 0; i < r.length; i++) if (Math.abs(r[i][1]) < Math.abs(norm[1])) norm = r[i];
      edge = r[0];
      for (i = 0; i < r.length; i++) if (Math.abs(r[i][0] - norm[0]) > Math.abs(edge[0] - norm[0])) edge = r[i];
      e = edge[0] - norm[0]; sa = Math.sin(p.A); ca = Math.cos(p.A);
      if (p.mode > 0.5) return fin(sa * sqrt(p.n * p.n - Math.sin(e) * Math.sin(e)) - ca * Math.sin(e));
      if (sa === 0.0) return 0.0;
      q2 = (Math.sin(e) + ca) / sa;
      return fin(sqrt(1.0 + q2 * q2));
    },
  });

  // ---------------------------------------------------------------------- Wollaston's air film
  var Wollaston = scan({
    PARAMS: { n: 1.3330, x0: 1.5708, x: 1.5708 },
    VARS: ['x', 'T'],
    read: function (p) {
      var th = p.x - p.x0, s = p.n * Math.sin(Math.abs(th)), ct, ci, rs, rp, R;
      if (s >= 1.0) return { x: p.x, T: 0.0 };
      ct = Math.sqrt(1.0 - s * s); ci = Math.cos(th);
      rs = (p.n * ci - ct) / (p.n * ci + ct); rp = (p.n * ct - ci) / (p.n * ct + ci);
      R = (rs * rs + rp * rp) / 2.0;
      return { x: p.x, T: (1.0 - R) * (1.0 - R) };
    },
    plan: function (p) { var c = asin(1.0 / p.n); return [{ x: p.x0 - c }, { x: p.x0 + c }]; },
    calc: function (rs, p) {
      var r = rows(rs, ['x']), lo, hi, i, s;
      if (r.length < 2) return 0.0;
      lo = hi = r[0][0];
      for (i = 0; i < r.length; i++) { lo = Math.min(lo, r[i][0]); hi = Math.max(hi, r[i][0]); }
      s = Math.sin((hi - lo) / 2.0);
      return s > 0.0 ? fin(1.0 / s) : 0.0;
    },
  });

  // ---------------------------------------------------------------------- the nodal slide
  var Nodal = scan({
    PARAMS: { f1: 0.15, f2: 0.20, d: 0.05, stage: 0.0, x: 0.02, rot: 0.0873, mode: 0.0 },
    VARS: ['x', 'shift', 'D', 'stage'],
    F: function (p) { var den = p.f1 + p.f2 - p.d; return den !== 0.0 ? p.f1 * p.f2 / den : 0.0; },
    h: function (p) { var front = p.stage > 0.5 ? p.f2 : p.f1; return front !== 0.0 ? Nodal.F(p) * p.d / front : 0.0; },
    read: function (p) {
      var h = Nodal.h(p);
      return { x: p.x, shift: (p.x - h) * Math.sin(p.rot), D: Nodal.F(p) + p.x - h, stage: p.stage };
    },
    plan: function (p) {
      return [{ stage: 0.0, x: Nodal.h(merge(p, { stage: 0.0 })) }, { stage: 1.0, x: Nodal.h(merge(p, { stage: 1.0 })) }];
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'x', 'shift', 'D']).filter(function (q) { return Math.abs(q[2]) <= 2e-4; });
      if (p.mode > 0.5) return mean(col(r.filter(function (q) { return q[0] < 0.5; }), 1));
      return mean(col(r, 3));
    },
  });

  // ---------------------------------------------------------------------- Fresnel's biprism
  var Biprism = scan({
    PARAMS: { lam: 5.893e-7, alpha: 0.0087266, nb: 1.5168, a: 0.10, D: 1.0, f: 0.20, t: 1.2e-5, mu: 1.58, stage: 0.0, x: 0.0, mode: 0.0 },
    VARS: ['x', 'N', 'I', 'stage'],
    geo: function (p) {
      var d = 2.0 * p.a * (p.nb - 1.0) * p.alpha, beta = d !== 0.0 ? p.lam * p.D / d : 0.0;
      var disc = sqrt(p.D * p.D - 4.0 * p.f * p.D), u1 = (p.D - disc) / 2.0, v1 = (p.D + disc) / 2.0;
      return { d: d, beta: beta, d1: u1 !== 0.0 ? d * v1 / u1 : 0.0, d2: v1 !== 0.0 ? d * u1 / v1 : 0.0,
        S: d !== 0.0 ? (p.mu - 1.0) * p.t * p.D / d : 0.0 };
    },
    read: function (p) {
      var g = Biprism.geo(p), st = p.stage, half, u, off, N, c;
      if (st > 0.5 && st < 2.5) {
        half = (st < 1.5 ? g.d1 : g.d2) / 2.0; u = (Math.abs(p.x) - half) / 3e-5;
        return { x: p.x, N: 0.0, I: Math.exp(-u * u), stage: st };
      }
      off = st > 2.5 ? g.S : 0.0;
      N = g.beta !== 0.0 ? (p.x - off) / g.beta : 0.0; c = Math.cos(PI * N);
      return { x: p.x, N: N, I: c * c, stage: st };
    },
    plan: function (p) {
      var g = Biprism.geo(p), out = [{ stage: 0.0, x: -10.0 * g.beta }, { stage: 0.0, x: 10.0 * g.beta }];
      if (p.mode > 0.5) { out.push({ stage: 3.0, x: g.S }); return out; }
      out.push({ stage: 1.0, x: -g.d1 / 2.0 }, { stage: 1.0, x: g.d1 / 2.0 }, { stage: 2.0, x: -g.d2 / 2.0 }, { stage: 2.0, x: g.d2 / 2.0 });
      return out;
    },
    span: function (r, st) {
      var xs = [], i, lo, hi;
      for (i = 0; i < r.length; i++) if (Math.abs(r[i][0] - st) < 0.5) xs.push(r[i][1]);
      if (xs.length < 2) return 0.0;
      lo = hi = xs[0];
      for (i = 0; i < xs.length; i++) { lo = Math.min(lo, xs[i]); hi = Math.max(hi, xs[i]); }
      return hi - lo;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'x', 'N']), f0 = r.filter(function (q) { return q[0] < 0.5; }), lo, hi, i, beta, c0, sh, d1, d2;
      if (f0.length < 2) return 0.0;
      lo = hi = f0[0];
      for (i = 0; i < f0.length; i++) { if (f0[i][1] < lo[1]) lo = f0[i]; if (f0[i][1] > hi[1]) hi = f0[i]; }
      if (hi[2] === lo[2]) return 0.0;
      beta = (hi[1] - lo[1]) / (hi[2] - lo[2]);
      if (p.mode > 0.5) {
        c0 = lo[1] - lo[2] * beta; sh = [];
        for (i = 0; i < r.length; i++) if (r[i][0] > 2.5) sh.push(r[i][1] - r[i][2] * beta - c0);
        if (!sh.length || beta === 0.0 || p.mu === 1.0) return 0.0;
        return fin(mean(sh) * p.lam / (beta * (p.mu - 1.0)));
      }
      d1 = Biprism.span(r, 1.0); d2 = Biprism.span(r, 2.0);
      return p.D !== 0.0 ? fin(beta * sqrt(d1 * d2) / p.D) : 0.0;
    },
  });

  // ---------------------------------------------------------------------- fringe counting
  var Fringes = scan({
    PARAMS: { lam: 6.328e-7, mode: 0.0, x: 0.0, L: 0.05, dn: 2.765e-4, P0: 101325.0, L0: 0.20, al: 5.5e-7, T0: 25.0 },
    VARS: ['x', 'N', 'I'],
    per: function (p) {
      if (p.mode < 0.5) return 2.0 / p.lam;
      if (p.mode < 1.5) return 2.0 * p.L * p.dn / (p.P0 * p.lam);
      return 2.0 * p.al * p.L0 / p.lam;
    },
    read: function (p) {
      var x = p.x - (p.mode > 1.5 ? p.T0 : 0.0), N = Fringes.per(p) * x, c = Math.cos(PI * N);
      return { x: p.x, N: N, I: c * c };
    },
    plan: function (p) {
      var per = Fringes.per(p), out = [], k;
      if (per === 0.0) return out;
      if (p.mode < 0.5) { for (k = 0; k < 5; k++) out.push({ x: 50.0 * k / per }); return out; }
      if (p.mode < 1.5) { for (k = 0; k < 8; k++) out.push({ x: 5.0 * k / per }); return out; }
      var nb = 5.0 * Math.max(1.0, Math.ceil(2.0 * per));
      for (k = 0; k < 6; k++) out.push({ x: p.T0 + nb * k / per });
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'N']), m = line(col(r, 0), col(r, 1))[0];
      if (m === 0.0) return 0.0;
      if (p.mode < 0.5) return fin(2.0 / m);
      if (p.mode < 1.5) return fin(m * p.lam * p.P0 / (2.0 * p.L));
      return fin(m * p.lam / (2.0 * p.L0));
    },
  });

  // ---------------------------------------------------------------------- Fabry-Perot
  var Fabry = scan({
    PARAMS: { lam: 6.328e-7, R: 0.90, mode: 0.0, x: 0.0 },
    VARS: ['x', 'N', 'I'],
    fc: function (p) { var q = 1.0 - p.R; return q !== 0.0 ? 4.0 * p.R / (q * q) : 0.0; },
    read: function (p) {
      var s = Math.sin(2.0 * PI * p.x / p.lam);
      return { x: p.x, N: 2.0 * p.x / p.lam, I: 1.0 / (1.0 + Fabry.fc(p) * s * s) };
    },
    plan: function (p) {
      var out = [], k, fc, hw, fsr;
      if (p.mode < 0.5) { for (k = 0; k < 5; k++) out.push({ x: 25.0 * k * p.lam }); return out; }
      fc = Fabry.fc(p); hw = fc > 0.0 ? p.lam / (2.0 * PI) * asin(1.0 / sqrt(fc)) : 0.0; fsr = p.lam / 2.0;
      return [{ x: -hw }, { x: hw }, { x: fsr - hw }, { x: fsr + hw }];
    },
    calc: function (rs, p) {
      var r, m, xs, w;
      if (p.mode < 0.5) {
        r = rows(rs, ['x', 'N']); m = line(col(r, 0), col(r, 1))[0];
        return m !== 0.0 ? fin(2.0 / m) : 0.0;
      }
      xs = col(rows(rs, ['x']), 0).sort(function (a, b) { return a - b; });
      if (xs.length < 4) return 0.0;
      w = ((xs[1] - xs[0]) + (xs[3] - xs[2])) / 2.0;
      if (w === 0.0) return 0.0;
      return fin(((xs[2] + xs[3]) / 2.0 - (xs[0] + xs[1]) / 2.0) / w);
    },
  });

  // ---------------------------------------------------------------------- Fourier-transform spectroscopy
  var Fts = scan({
    PARAMS: { lam0: 5.5e-7, fwhm: 1.0e-8, mode: 0.0, stage: 0.0, x: 0.0, XS: 6.0e-5, NS: 400.0 },
    VARS: ['x', 'N', 'V', 'I', 'T', 'stage'],
    s: function (p) { return p.fwhm / (p.lam0 * p.lam0) / SIG_FWHM; },
    vis: function (p, x) { var q = PI * Fts.s(p) * x; return Math.exp(-2.0 * q * q); },
    spec: function (p, lam) {
      var n = Math.trunc(p.NS), dx, tot = 0.0, j, x, w;
      if (n < 2 || lam <= 0.0) return 0.0;
      dx = p.XS / n;
      for (j = 0; j <= n; j++) {
        x = j * dx; w = (j === 0 || j === n) ? 0.5 : 1.0;
        tot += w * 0.5 * Fts.vis(p, x) * Math.cos(2.0 * PI * x / p.lam0) * Math.cos(2.0 * PI * x / lam);
      }
      return tot * dx;
    },
    read: function (p) {
      var pk, V;
      if (p.stage > 0.5) {
        pk = Fts.spec(p, p.lam0);
        return { x: p.x, N: 0.0, V: 0.0, I: 0.0, T: pk !== 0.0 ? Fts.spec(p, p.x) / pk : 0.0, stage: p.stage };
      }
      V = Fts.vis(p, p.x);
      return { x: p.x, N: p.x / p.lam0, V: V, I: 0.5 * (1.0 + V * Math.cos(2.0 * PI * p.x / p.lam0)), T: 0.0, stage: p.stage };
    },
    half: function (p, sign) {
      var pk = Fts.spec(p, p.lam0), lo = p.lam0, hi = p.lam0 + sign * 3.0 * p.fwhm, i, mid;
      for (i = 0; i < 50; i++) { mid = (lo + hi) / 2.0; if (Fts.spec(p, mid) > 0.5 * pk) lo = mid; else hi = mid; }
      return (lo + hi) / 2.0;
    },
    plan: function (p) {
      var out = [], k;
      if (p.mode > 0.5) return [{ stage: 1.0, x: Fts.half(p, -1.0) }, { stage: 1.0, x: Fts.half(p, 1.0) }];
      for (k = 0; k < 6; k++) out.push({ stage: 0.0, x: 5.0 * k * p.lam0 });
      return out;
    },
    calc: function (rs, p) {
      var xs, lo, hi, i, r, m, lam0, pts, k, s;
      if (p.mode > 0.5) {
        xs = col(rows(rs, ['stage', 'x']).filter(function (q) { return q[0] > 0.5; }), 1);
        if (xs.length < 2) return 0.0;
        lo = hi = xs[0];
        for (i = 0; i < xs.length; i++) { lo = Math.min(lo, xs[i]); hi = Math.max(hi, xs[i]); }
        return hi - lo;
      }
      r = rows(rs, ['stage', 'x', 'N', 'V']).filter(function (q) { return q[0] < 0.5; });
      m = line(col(r, 1), col(r, 2))[0];
      if (m === 0.0) return 0.0;
      lam0 = 1.0 / m;
      pts = r.filter(function (q) { return q[3] > 0.0 && q[3] < 1.0; });
      k = line(pts.map(function (q) { return q[1] * q[1]; }), pts.map(function (q) { return ln(q[3]); }))[0];
      if (k >= 0.0) return 0.0;
      s = sqrt(-k / 2.0) / PI;
      return fin(SIG_FWHM * s * lam0 * lam0);
    },
  });

  // ---------------------------------------------------------------------- the corona of lycopodium powder
  var Corona = scan({
    PARAMS: { dia: 3.2e-5, lam: 6.328e-7, D: 1.0, x: 0.0 },
    VARS: ['x', 'I'],
    read: function (p) {
      var th = Math.atan2(Math.abs(p.x), p.D), u = PI * p.dia * Math.sin(th) / p.lam, q;
      if (u < 1e-6) return { x: p.x, I: 1.0 };
      if (u > 15.0) return { x: p.x, I: 0.0 };
      q = 2.0 * j1(u) / u;
      return { x: p.x, I: q * q };
    },
    plan: function (p) {
      var out = [], i;
      for (i = 0; i < 2; i++) out.push({ x: p.D * Math.tan(asin(J1_ZEROS[i] * p.lam / (PI * p.dia))) });
      return out;
    },
    calc: function (rs, p) {
      var xs = col(rows(rs, ['x']), 0).map(Math.abs).sort(function (a, b) { return a - b; }), vals = [], i, s;
      for (i = 0; i < Math.min(3, xs.length); i++) {
        s = Math.sin(Math.atan2(xs[i], p.D));
        if (s > 0.0) vals.push(J1_ZEROS[i] * p.lam / (PI * s));
      }
      return mean(vals);
    },
  });

  // ---------------------------------------------------------------------- resolving power of a telescope
  var Resolve = scan({
    PARAMS: { s: 2.0e-3, D: 3.0, lam: 5.893e-7, x: 2.0e-3 },
    VARS: ['x', 'dip'],
    read: function (p) {
      var ang = p.s / p.D, mid = 2.0 * sinc2(PI * p.x * ang / (2.0 * p.lam)), pk = 1.0 + sinc2(PI * p.x * ang / p.lam);
      return { x: p.x, dip: Math.min(1.0, mid / pk) };
    },
    plan: function (p) { return [{ x: p.lam * p.D / p.s }]; },
    calc: function (rs, p) { return p.lam !== 0.0 ? mean(col(rows(rs, ['x']), 0)) / p.lam : 0.0; },
  });

  // ---------------------------------------------------------------------- Malus's law
  var Malus = scan({
    PARAMS: { th0: 0.6109, I0: 4.0e-4, ext: 0.002, mode: 0.0, x: 0.0 },
    VARS: ['x', 'I'],
    read: function (p) { var c = Math.cos(p.x - p.th0); return { x: p.x, I: p.I0 * (p.ext + (1.0 - p.ext) * c * c) }; },
    plan: function (p) {
      var out = [], k;
      if (p.mode > 1.5) return [{ x: p.th0 }, { x: p.th0 + PI / 2.0 }];
      for (k = 0; k < 9; k++) out.push({ x: k * PI / 9.0 });
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'I']), i, lo, hi, C = 0.0, S = 0.0, a = 0.0, th0, imin, xs = [], ys = [], c;
      if (r.length < 2) return 0.0;
      if (p.mode > 1.5) {
        lo = hi = r[0][1];
        for (i = 0; i < r.length; i++) { lo = Math.min(lo, r[i][1]); hi = Math.max(hi, r[i][1]); }
        return lo > 0.0 ? fin(hi / lo) : 0.0;
      }
      for (i = 0; i < r.length; i++) { C += r[i][1] * Math.cos(2.0 * r[i][0]); S += r[i][1] * Math.sin(2.0 * r[i][0]); a += r[i][1]; }
      a = a / r.length;
      th0 = 0.5 * Math.atan2(S, C);
      if (th0 < 0.0) th0 += PI;
      if (p.mode < 0.5) return th0;
      imin = a - 2.0 * sqrt(C * C + S * S) / r.length;
      for (i = 0; i < r.length; i++) {
        c = Math.abs(Math.cos(r[i][0] - th0));
        if (c * c > 0.15 && r[i][1] - imin > 0.0) { xs.push(ln(c)); ys.push(ln(r[i][1] - imin)); }
      }
      return line(xs, ys)[0];
    },
  });

  // ---------------------------------------------------------------------- Babinet compensator
  var Babinet = scan({
    PARAMS: { psi: 0.5236, del: 1.0472, beta: 2.0e-3, stage: 0.0, A: 2.3562, x: 0.0, mode: 0.0 },
    VARS: ['x', 'A', 'I', 'stage'],
    read: function (p) {
      var psi = p.stage > 0.5 ? p.psi : PI / 4.0, de = p.stage > 0.5 ? p.del : 0.0;
      var a = Math.cos(psi), b = Math.sin(psi), c = Math.cos(p.A), s = Math.sin(p.A), ph = de + 2.0 * PI * p.x / p.beta;
      return { x: p.x, A: p.A, I: c * a * c * a + s * b * s * b + 2.0 * c * s * a * b * Math.cos(ph), stage: p.stage };
    },
    plan: function (p) {
      var xs = p.beta * (1.0 - p.del / (2.0 * PI));
      return [{ stage: 0.0, A: 3.0 * PI / 4.0, x: 0.0 }, { stage: 0.0, A: 3.0 * PI / 4.0, x: p.beta },
        { stage: 1.0, A: 3.0 * PI / 4.0, x: xs }, { stage: 1.0, A: PI / 2.0 + p.psi, x: xs }];
    },
    ellipse: function (psi, de, mode) {
      if (mode < 0.5) return Math.abs(Math.tan(0.5 * asin(Math.sin(2.0 * psi) * Math.sin(de))));
      if (mode < 1.5) return 0.5 * Math.atan2(Math.sin(2.0 * psi) * Math.cos(de), Math.cos(2.0 * psi));
      return de;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'A', 'x']), c0 = [], t1 = [], i, lo, hi, beta, far, psi, frac, de;
      for (i = 0; i < r.length; i++) { if (r[i][0] < 0.5) c0.push(r[i][2]); if (r[i][0] > 0.5) t1.push(r[i]); }
      if (c0.length < 2 || !t1.length) return 0.0;
      lo = hi = c0[0];
      for (i = 0; i < c0.length; i++) { lo = Math.min(lo, c0[i]); hi = Math.max(hi, c0[i]); }
      beta = hi - lo;
      if (beta === 0.0) return 0.0;
      far = t1[0];
      for (i = 0; i < t1.length; i++) if (Math.abs(t1[i][1] - 3.0 * PI / 4.0) > Math.abs(far[1] - 3.0 * PI / 4.0)) far = t1[i];
      psi = far[1] - PI / 2.0;
      frac = (mean(col(t1, 2)) - lo) / beta;
      frac = frac - Math.floor(frac);
      de = 2.0 * PI * (1.0 - frac);
      return fin(Babinet.ellipse(psi, de, p.mode));
    },
  });

  // ---------------------------------------------------------------------- near field of a multimode fibre
  var NearField = scan({
    PARAMS: { g: 2.0, a: 2.5e-5, M: 400.0, P0: 1.0e-6, x: 0.0 },
    VARS: ['x', 'P'],
    read: function (p) {
      var u = Math.abs(p.x) / (p.M * p.a);
      return { x: p.x, P: u < 1.0 ? p.P0 * (1.0 - Math.pow(u, p.g)) : 0.0 };
    },
    plan: function (p) {
      var ks = [0.0, 0.3, 0.45, 0.6, 0.75, 0.9], out = [], i;
      for (i = 0; i < ks.length; i++) out.push({ x: p.M * p.a * ks[i] });
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'P']), pk, i, xs = [], ys = [], u;
      if (!r.length) return 0.0;
      pk = r[0][1];
      for (i = 0; i < r.length; i++) pk = Math.max(pk, r[i][1]);
      for (i = 0; i < r.length; i++) {
        u = Math.abs(r[i][0]) / (p.M * p.a);
        if (u > 0.0 && u < 1.0 && r[i][1] > 0.0 && r[i][1] < pk) { xs.push(ln(u)); ys.push(ln(1.0 - r[i][1] / pk)); }
      }
      return line(xs, ys)[0];
    },
  });

  // ---------------------------------------------------------------------- bend loss
  var Bend = scan({
    PARAMS: { Dl: 0.01, a: 2.5e-5, n2: 1.45, lam: 8.5e-7, P0: 1.0e-4, stage: 0.0, x: 0.03 },
    VARS: ['x', 'P', 'dB', 'stage'],
    term: function (p, R) { var k = 2.0 * PI / p.lam; return 2.0 * p.a / R + Math.pow(3.0 / (2.0 * p.n2 * k * R), 2.0 / 3.0); },
    read: function (p) {
      var f = 1.0;
      if (p.stage > 0.5 && p.x > 0.0) f = clamp(1.0 - Bend.term(p, p.x) / (2.0 * p.Dl), 0.0, 1.0);
      return { x: p.x, P: p.P0 * f, dB: f > 0.0 ? -10.0 * Math.log10(f) : 99.0, stage: p.stage };
    },
    plan: function () {
      var Rs = [0.03, 0.02, 0.012, 0.008, 0.006], out = [{ stage: 0.0, x: 0.03 }], i;
      for (i = 0; i < Rs.length; i++) out.push({ stage: 1.0, x: Rs[i] });
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'x', 'P']), ref, vals = [], i;
      ref = mean(col(r.filter(function (q) { return q[0] < 0.5; }), 2));
      if (ref <= 0.0) return 0.0;
      for (i = 0; i < r.length; i++) {
        if (r[i][0] > 0.5 && r[i][1] > 0.0 && r[i][2] > 0.0 && r[i][2] < ref) vals.push(Bend.term(p, r[i][1]) / (2.0 * (1.0 - r[i][2] / ref)));
      }
      return mean(vals);
    },
  });

  // ---------------------------------------------------------------------- splice loss
  var Splice = scan({
    PARAMS: { off: 1.0e-5, a: 2.5e-5, P0: 1.0e-4, stage: 0.0 },
    VARS: ['P', 'stage'],
    eta: function (p) { var u = clamp(p.off / (2.0 * p.a), 0.0, 1.0); return 2.0 / PI * (acos(u) - u * sqrt(1.0 - u * u)); },
    read: function (p) { return { P: p.P0 * (p.stage > 0.5 ? Splice.eta(p) : 1.0), stage: p.stage }; },
    plan: function () { return [{ stage: 0.0 }, { stage: 1.0 }]; },
    calc: function (rs) {
      var r = rows(rs, ['stage', 'P']);
      var ref = mean(col(r.filter(function (q) { return q[0] < 0.5; }), 1)), out = mean(col(r.filter(function (q) { return q[0] > 0.5; }), 1));
      if (ref <= 0.0 || out <= 0.0) return 0.0;
      return 10.0 * Math.log10(ref / out);
    },
  });

  // ---------------------------------------------------------------------- mode field diameter
  var Mfd = scan({
    PARAMS: { w0: 4.6e-6, lam: 1.31e-6, P0: 1.0e-6, x: 0.0 },
    VARS: ['x', 'P'],
    read: function (p) { var th0 = p.lam / (PI * p.w0), q = p.x / th0; return { x: p.x, P: p.P0 * Math.exp(-2.0 * q * q) }; },
    plan: function () { var out = [], k; for (k = 0; k < 5; k++) out.push({ x: k * 1.5 * PI / 180.0 }); return out; },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'P']).filter(function (q) { return q[1] > 0.0; });
      var m = line(r.map(function (q) { return q[0] * q[0]; }), r.map(function (q) { return ln(q[1]); }))[0];
      if (m >= 0.0) return 0.0;
      return fin(2.0 * p.lam / (PI * sqrt(-2.0 / m)));
    },
  });

  // ---------------------------------------------------------------------- laser diode
  var LaserDiode = scan({
    PARAMS: { Ith: 0.020, eta: 0.5, s: 0.012, mode: 0.0, x: 0.0 },
    VARS: ['x', 'P'],
    read: function (p) {
      var i = Math.max(0.0, p.x);
      if (i <= p.Ith) return { x: p.x, P: p.s * i };
      return { x: p.x, P: p.s * p.Ith + p.eta * (i - p.Ith) };
    },
    plan: function (p) {
      var ks = [0.3, 0.5, 0.7, 1.1, 1.2, 1.3, 1.4], out = [], i;
      for (i = 0; i < ks.length; i++) out.push({ x: p.Ith * ks[i] });
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'P']).sort(function (a, b) { return a[0] - b[0]; }), lo, hi, l1, l2;
      if (r.length < 7) return 0.0;
      lo = r.slice(0, 3); hi = r.slice(r.length - 4);
      l1 = line(col(lo, 0), col(lo, 1)); l2 = line(col(hi, 0), col(hi, 1));
      if (p.mode > 0.5) return l2[0];
      if (l2[0] === l1[0]) return 0.0;
      return fin((l1[1] - l2[1]) / (l2[0] - l1[0]));
    },
  });

  function calc(K) { return function (r, p) { return fin(K.calc(r, p)); }; }
  function splice(p) { var u = p.off / (2.0 * p.a); return -10.0 * Math.log10(2.0 / PI * (Math.acos(u) - u * Math.sqrt(1.0 - u * u))); }

  HK.register({
    K: { w7_tir: Tir, w7_wollaston: Wollaston, w7_nodal: Nodal, w7_biprism: Biprism, w7_fringes: Fringes, w7_fabry: Fabry,
      w7_fts: Fts, w7_corona: Corona, w7_resolve: Resolve, w7_malus: Malus, w7_babinet: Babinet, w7_nearfield: NearField,
      w7_bend: Bend, w7_splice: Splice, w7_mfd: Mfd, w7_ld: LaserDiode },
    CALCS: {
      w7_tir: { label: 'refractive index', unit: '', needs: ['x', 'refl'], fn: calc(Tir) },
      w7_wollaston: { label: 'refractive index', unit: '', needs: ['x'], fn: calc(Wollaston) },
      w7_nodal: { label: 'focal length / principal point', unit: 'm', needs: ['stage', 'x', 'shift', 'D'], fn: calc(Nodal) },
      w7_biprism: { label: 'wavelength / thickness', unit: 'm', needs: ['stage', 'x', 'N'], fn: calc(Biprism) },
      w7_fringes: { label: 'from the fringe count', unit: '', needs: ['x', 'N'], fn: calc(Fringes) },
      w7_fabry: { label: 'wavelength / finesse', unit: '', needs: ['x', 'N'], fn: calc(Fabry) },
      w7_fts: { label: 'width of the pass band', unit: 'm', needs: ['stage', 'x', 'N', 'V'], fn: calc(Fts) },
      w7_corona: { label: 'particle diameter', unit: 'm', needs: ['x'], fn: calc(Corona) },
      w7_resolve: { label: 'resolving power', unit: '', needs: ['x'], fn: calc(Resolve) },
      w7_malus: { label: 'from the analyser readings', unit: '', needs: ['x', 'I'], fn: calc(Malus) },
      w7_babinet: { label: 'the ellipse', unit: '', needs: ['stage', 'A', 'x'], fn: calc(Babinet) },
      w7_nearfield: { label: 'profile exponent g', unit: '', needs: ['x', 'P'], fn: calc(NearField) },
      w7_bend: { label: 'relative index difference', unit: '', needs: ['stage', 'x', 'P'], fn: calc(Bend) },
      w7_splice: { label: 'splice loss', unit: 'dB', needs: ['stage', 'P'], fn: calc(Splice) },
      w7_mfd: { label: 'mode field diameter', unit: 'm', needs: ['x', 'P'], fn: calc(Mfd) },
      w7_ld: { label: 'threshold / slope', unit: '', needs: ['x', 'P'], fn: calc(LaserDiode) },
    },
    TEXTBOOK: {
      w7_tir: function (p) { return p.mode > 0.5 ? p.nl : p.n; },
      w7_wollaston: function (p) { return p.n; },
      w7_nodal: function (p) { return (p.f1 * p.f2 / (p.f1 + p.f2 - p.d)) * (p.mode > 0.5 ? p.d / p.f1 : 1.0); },
      w7_biprism: function (p) { return p.mode > 0.5 ? p.t : p.lam; },
      w7_fringes: function (p) { return p.mode < 0.5 ? p.lam : (p.mode < 1.5 ? p.dn : p.al); },
      w7_fabry: function (p) { return p.mode < 0.5 ? p.lam : PI * Math.sqrt(p.R) / (1.0 - p.R); },
      w7_fts: function (p) { return p.fwhm; },
      w7_corona: function (p) { return p.dia; },
      w7_resolve: function (p) { return p.D / p.s; },
      w7_malus: function (p) { return p.mode < 0.5 ? p.th0 : (p.mode < 1.5 ? 2.0 : 1.0 / p.ext); },
      w7_babinet: function (p) { return Babinet.ellipse(p.psi, p.del, p.mode); },
      w7_nearfield: function (p) { return p.g; },
      w7_bend: function (p) { return p.Dl; },
      w7_splice: splice,
      w7_mfd: function (p) { return 2.0 * p.w0; },
      w7_ld: function (p) { return p.mode > 0.5 ? p.eta : p.Ith; },
    },
  });
})(typeof window !== 'undefined' ? window : this);
