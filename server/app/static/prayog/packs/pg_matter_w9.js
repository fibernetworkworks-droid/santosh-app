/* Kernel pack (browser twin of app/prayog/packs/pg_matter_w9.py): M.Sc. solid state, nuclear, modern, wave and
   microwave set-ups, wave 9 (kernels pm9_*). Same formulas, same order of operations, so both sides give the same
   numbers. Every kernel is a SWEEP: read(p, s, x, k) gives the reading at setting x of stage s, plan(p) lists the
   settings, fit(rows, p) works the result out of the rows, measure(p) = fit(run(plan)).
   Counts are Poisson draws from the lab's own seed (Gaussian approximation above 50): SIMULATED DATA. */
(function (root) {
  'use strict';
  var HK = (root && root.HoolaKernels) ||
    (typeof module !== 'undefined' && module.exports && module.exports.register ? module.exports : null);
  if (!HK) throw new Error('HoolaKernels is not loaded');
  var PI = Math.PI, LN2 = Math.log(2.0), NA = 6.02214076e23, KB_EV = 8.617333262e-5, QE = 1.602176634e-19;
  var YEAR = 3.15576e7, ME_KEV = 510.99895, ALPHA = 1.0 / 137.035999084, C0 = 299792458.0;
  var HC_EVNM = 1239.84198, HC_KEVA = 12.3984198;

  function q_(v, q) { return Math.floor(v / q + 0.5) * q; }
  function erfc(x) {
    if (x < 0) return 2.0 - erfc(-x);
    var t = 1.0 / (1.0 + 0.3275911 * x);
    var poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))));
    return poly * Math.exp(-x * x);
  }
  function Rnd(seed) { this.s = Math.floor(Math.abs(seed)) % 2147483646 + 1; }
  Rnd.prototype.next = function () { this.s = (this.s * 16807) % 2147483647; return this.s / 2147483647.0; };
  Rnd.prototype.count = function (mean) {
    if (mean <= 0) return 0.0;
    if (mean > 50) {
      var u1 = this.next(), u2 = this.next();
      var z = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * PI * u2);
      var n = Math.floor(mean + Math.sqrt(mean) * z + 0.5);
      return n > 0 ? n : 0.0;
    }
    var lim = Math.exp(-mean), k = 0, pr = 1.0;
    for (;;) { pr *= this.next(); if (pr <= lim) return k; k += 1; }
  };
  function cnt(p, k, mean) { return new Rnd(p.seed + 977.0 * k).count(mean); }
  function linfit(pts) {
    var n = pts.length, sx = 0.0, sy = 0.0, sxx = 0.0, sxy = 0.0, i, den, m;
    if (n < 2) return null;
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxx += pts[i][0] * pts[i][0]; sxy += pts[i][0] * pts[i][1]; }
    den = n * sxx - sx * sx;
    if (Math.abs(den) < 1e-300) return null;
    m = (n * sxy - sx * sy) / den;
    return [m, (sy - m * sx) / n];
  }
  function stage(rows, s) {
    var out = [], i, r;
    for (i = 0; i < (rows || []).length; i++) {
      r = rows[i];
      if (!r || r.s === undefined || r.s === null || r.x === undefined || r.x === null || r.y === undefined || r.y === null) continue;
      if (!isFinite(Number(r.s)) || !isFinite(Number(r.x)) || !isFinite(Number(r.y))) continue;
      if (Math.floor(Number(r.s) + 0.5) === s) out.push(r);
    }
    return out;
  }
  function half(pts, lvl, side, i0) {
    var i = i0, a, b;
    while (i + side >= 0 && i + side < pts.length) {
      a = pts[i]; b = pts[i + side];
      if ((a[1] - lvl) * (b[1] - lvl) <= 0 && a[1] !== b[1]) return a[0] + (lvl - a[1]) * (b[0] - a[0]) / (b[1] - a[1]);
      i += side;
    }
    return null;
  }
  function sortx(pts) { return pts.sort(function (a, b) { return a[0] - b[0]; }); }
  function sorted(rows, key) { key = key || 'y'; return sortx(rows.map(function (r) { return [Number(r.x), Number(r[key])]; })); }
  function peakwidth(pts, lo, hi, base) {
    var best = -1e300, ib = -1, i, lvl, a, b;
    for (i = 0; i < pts.length; i++) if (lo <= pts[i][0] && pts[i][0] <= hi && pts[i][1] > best) { best = pts[i][1]; ib = i; }
    if (ib < 0) return null;
    lvl = base + (best - base) / 2.0;
    a = half(pts, lvl, -1, ib); b = half(pts, lvl, 1, ib);
    if (a === null || b === null) return null;
    return [(a + b) / 2.0, b - a, best];
  }
  function rng(a, b, d) { var n = Math.floor((b - a) / d + 0.5), out = [], i; for (i = 0; i <= n; i++) out.push(a + d * i); return out; }
  function sweep(K) {
    K.VARS = ['t', 'x', 'y'];
    K.NST = K.NST || 1;
    if (!K.plan) K.plan = function (p) { var out = [], s, i, xs; for (s = 0; s < K.NST; s++) { xs = K.xs(p, s); for (i = 0; i < xs.length; i++) out.push([s, xs[i]]); } return out; };
    K.run = function (p) {
      var rows = [], pl = K.plan(p), i, r, row, key;
      for (i = 0; i < pl.length; i++) {
        r = K.read(p, pl[i][0], pl[i][1], i);
        row = { s: pl[i][0], x: pl[i][1] };
        for (key in r) if (Object.prototype.hasOwnProperty.call(r, key)) row[key] = r[key];
        rows.push(row);
      }
      return rows;
    };
    K.init = function () { return { t: 0.0 }; };
    K.step = function (st, p, dt) { st.t += dt; };
    K.view = function (st, p) { var r = K.read(p, Math.floor(p.s + 0.5), p.x, 0); return { t: st.t || 0.0, x: p.x, y: r.y }; };
    K.measure = function (p) { var rows = K.run(p); return { res: K.fit(rows, p), n: rows.length }; };
    return K;
  }
  function mapRows(rows, f) { var out = [], i; for (i = 0; i < rows.length; i++) out.push(f(rows[i])); return out; }

  // ================================================================ GM plateau + dead time
  var GMDead = sweep({
    PARAMS: { x: 0.0, s: 0.0, V: 450.0, Vs: 330.0, Vp: 700.0, slope: 0.04, n1: 1800.0, n2: 1500.0, nb: 0.8, tau: 3.0e-4, t: 1200.0, tp: 30.0, seed: 11.0 },
    NST: 2,
    eff: function (p, V) {
      if (V <= p.Vs) return 0.0;
      var r = Math.min(1.0, (V - p.Vs) / 30.0), g = 1.0 + p.slope * Math.max(V - p.Vs - 30.0, 0.0) / 100.0;
      if (V > p.Vp) g *= 1.0 + Math.pow((V - p.Vp) / 25.0, 2);
      return r * g;
    },
    read: function (p, s, x, k) {
      var n, m, c, f, i;
      if (s === 0) { n = (p.n1 + p.nb) * GMDead.eff(p, x); m = n / (1.0 + n * p.tau); c = cnt(p, k, m * p.tp); return { y: c / p.tp, N: c, T: p.tp }; }
      f = GMDead.eff(p, p.V); i = Math.floor(x + 0.5);
      n = p.nb + ((i === 1 || i === 2) ? p.n1 : 0.0) + ((i === 2 || i === 3) ? p.n2 : 0.0);
      n *= f; m = n / (1.0 + n * p.tau); c = cnt(p, k, m * p.t);
      return { y: c / p.t, N: c, T: p.t };
    },
    xs: function (p, s) { return s === 0 ? rng(300.0, 760.0, 20.0) : [0.0, 1.0, 2.0, 3.0]; },
    tauOf: function (m) {
      var mb = m[0], m1 = m[1], m12 = m[2], m2 = m[3], lo, hi, mid, i;
      if (Math.min(m1, m2, m12) <= 0) return 0.0;
      function g(tau) { function n(v) { return v / (1.0 - v * tau); } return n(m1) + n(m2) - n(m12) - n(mb); }
      lo = 0.0; hi = 0.999 / Math.max(m1, m2, m12);
      if (g(lo) <= 0) return 0.0;
      for (i = 0; i < 100; i++) { mid = (lo + hi) / 2.0; if (g(mid) > 0) lo = mid; else hi = mid; }
      return (lo + hi) / 2.0;
    },
    fit: function (rows) {
      var m = [null, null, null, null], st = stage(rows, 1), j, i;
      for (j = 0; j < st.length; j++) { i = Math.floor(Number(st[j].x) + 0.5); if (i >= 0 && i <= 3) m[i] = Number(st[j].y); }
      for (j = 0; j < 4; j++) if (m[j] === null) return 0.0;
      return GMDead.tauOf(m);
    },
  });

  // ================================================================ GM efficiency
  var GMEff = sweep({
    PARAMS: { x: 0.0, s: 0.0, A: 3700.0, yld: 2.0, eint: 0.9, a: 0.014, nb: 0.5, tau: 2.5e-4, t: 300.0, seed: 23.0 },
    NST: 2,
    geo: function (p, d) { return 0.5 * (1.0 - d / Math.sqrt(d * d + p.a * p.a)); },
    read: function (p, s, x, k) {
      var n = p.nb + (s === 1 ? p.A * p.yld * GMEff.geo(p, x) * p.eint : 0.0), m = n / (1.0 + n * p.tau), c = cnt(p, k, m * p.t);
      return { y: c / p.t, N: c, T: p.t };
    },
    xs: function (p, s) { return s === 0 ? [0.0] : [0.02, 0.03, 0.04, 0.05, 0.06]; },
    fit: function (rows, p) {
      var b = stage(rows, 0), mb, nb, tot = 0.0, k = 0, st, i, d, m, n;
      if (!b.length) return 0.0;
      mb = Number(b[0].y); nb = mb / (1.0 - mb * p.tau);
      st = stage(rows, 1);
      for (i = 0; i < st.length; i++) {
        d = Number(st[i].x); m = Number(st[i].y);
        if (d <= 0) continue;
        n = m / (1.0 - m * p.tau) - nb;
        tot += n / (p.A * p.yld * GMEff.geo(p, d)); k += 1;
      }
      return k ? tot / k : 0.0;
    },
  });

  // ================================================================ beta absorption, Feather's rule
  var BetaFeather = sweep({
    PARAMS: { x: 0.0, s: 0.0, E1: 2.2785, f1: 0.5, E2: 0.5459, f2: 0.5, N0: 600.0, brem: 0.6, bg: 0.5, tau: 2.5e-4, t: 200.0, tl: 1800.0, seed: 31.0 },
    NST: 2,
    rkp: function (E) { return 0.412 * Math.pow(E, 1.265 - 0.0954 * Math.log(E)); },
    mu: function (E) { return 17.0 * Math.pow(E, -1.14); },
    beta: function (p, x) {
      var r = 0.0, g = [[p.E1, p.f1], [p.E2, p.f2]], i;
      for (i = 0; i < 2; i++) if (g[i][1] > 0 && x < BetaFeather.rkp(g[i][0])) r += g[i][1] * Math.exp(-BetaFeather.mu(g[i][0]) * x);
      return p.N0 * r;
    },
    ctime: function (p, x) { return x > 0.6 * BetaFeather.rkp(p.E1) ? p.tl : p.t; },
    read: function (p, s, x, k) {
      var n = p.bg + (s === 1 ? p.brem + BetaFeather.beta(p, x) : 0.0), m = n / (1.0 + n * p.tau);
      var tt = s === 0 ? p.tl : BetaFeather.ctime(p, x), c = cnt(p, k, m * tt);
      return { y: c / tt, N: c, T: tt };
    },
    coarse: function () { return [0.0, 0.025, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0]; },
    plan: function (p) {
      var out = [[0, 0.0]], rows = [], r, k = 1, xs = BetaFeather.coarse(p), i, b, mid;
      r = BetaFeather.read(p, 0, 0.0, 0); r.s = 0; r.x = 0.0; rows.push(r);
      for (i = 0; i < xs.length; i++) { r = BetaFeather.read(p, 1, xs[i], k); k += 1; r.s = 1; r.x = xs[i]; rows.push(r); out.push([1, xs[i]]); }
      b = BetaFeather.bracket(rows, p);
      while (b[0] !== null && b[1] - b[0] > 0.0075) {
        mid = Math.floor((b[0] + b[1]) / 2.0 / 0.005 + 0.5) * 0.005;
        if (mid <= b[0] || mid >= b[1]) break;
        r = BetaFeather.read(p, 1, mid, k); k += 1; r.s = 1; r.x = mid; rows.push(r); out.push([1, mid]);
        b = BetaFeather.bracket(rows, p);
      }
      return out;
    },
    bracket: function (rows) {
      var bg = stage(rows, 0), foils = stage(rows, 1), tail = null, i, mt, st, pts, last = -1, q;
      for (i = 0; i < foils.length; i++) if (Math.abs(Number(foils[i].x) - 2.0) < 1e-9) tail = foils[i];
      if (!bg.length || tail === null) return [null, null];
      mt = Number(tail.y); st = Math.sqrt(Math.max(Number(tail.N), 1.0)) / Number(tail.T);
      pts = sortx(mapRows(foils, function (r) { return [Number(r.x), Number(r.y), Math.sqrt(Math.max(Number(r.N), 1.0)) / Number(r.T)]; }));
      for (i = 0; i < pts.length; i++) { q = pts[i]; if (q[1] - mt > 3.0 * Math.sqrt(q[2] * q[2] + st * st)) last = i; }
      if (last < 0 || last >= pts.length - 1) return [null, null];
      return [pts[last][0], pts[last + 1][0]];
    },
    fit: function (rows, p) { var b = BetaFeather.bracket(rows, p); return b[0] === null ? 0.0 : (b[0] + b[1]) / 2.0; },
    feather: function (R) { return (R + 0.160) / 0.543; },
  });

  // ================================================================ K-40 with a UX2 standard
  var K40Std = sweep({
    PARAMS: { x: 0.0, s: 0.0, m: 0.1, fK: 0.52445, MK: 39.0983, ab: 1.17e-4, T12: 1.248e9, br: 0.8928, Bstd: 1000.0, eps: 0.002, bg: 0.45, tau: 2.5e-4, t: 3600.0, seed: 41.0 },
    NST: 3,
    nk: function (p) { return p.m * 1000.0 * p.fK / p.MK * NA * p.ab; },
    abeta: function (p) { return K40Std.nk(p) * LN2 / (p.T12 * YEAR) * p.br; },
    read: function (p, s, x, k) {
      var n = p.bg + (s === 1 ? p.Bstd * p.eps : 0.0) + (s === 2 ? K40Std.abeta(p) * p.eps : 0.0), m = n / (1.0 + n * p.tau), c = cnt(p, k, m * p.t);
      return { y: c / p.t, N: c, T: p.t };
    },
    xs: function (p, s) { return s === 0 ? [1.0, 2.0] : [1.0, 2.0, 3.0]; },
    fit: function (rows, p) {
      function mean(s) { var v = stage(rows, s), tot = 0.0, i, m; if (!v.length) return null; for (i = 0; i < v.length; i++) { m = Number(v[i].y); tot += m / (1.0 - m * p.tau); } return tot / v.length; }
      var b = mean(0), sd = mean(1), kk = mean(2), eps, ab;
      if (b === null || sd === null || kk === null || sd - b <= 0 || kk - b <= 0) return 0.0;
      eps = (sd - b) / p.Bstd; ab = (kk - b) / eps;
      return K40Std.nk(p) * LN2 / ab / YEAR;
    },
  });

  // ================================================================ spark counter, alpha range
  var SparkAlpha = sweep({
    PARAMS: { x: 0.0, s: 0.0, E: 5.4857, N0: 60.0, sig: 0.015, Vth: 3200.0, Vd: 4900.0, V: 4100.0, bg: 0.02, t: 120.0, seed: 53.0 },
    NST: 2,
    rg: function (p) { return 0.318 * Math.pow(p.E, 1.5); },
    plateau: function (p, V) { if (V <= p.Vth) return 0.0; var f = Math.min(1.0, (V - p.Vth) / 250.0); if (V > p.Vd) f *= 1.0 + Math.pow((V - p.Vd) / 120.0, 2); return f; },
    alpha: function (p, d) { var R = SparkAlpha.rg(p); return p.N0 / (d * d) * 0.5 * erfc((d - R) / (Math.sqrt(2.0) * p.sig * R)); },
    read: function (p, s, x, k) {
      var n = s === 0 ? SparkAlpha.alpha(p, 1.0) * SparkAlpha.plateau(p, x) + p.bg : SparkAlpha.alpha(p, x) * SparkAlpha.plateau(p, p.V) + p.bg;
      var c = cnt(p, k, n * p.t);
      return { y: c / p.t, N: c, T: p.t };
    },
    xs: function (p, s) { return s === 0 ? rng(3000.0, 5100.0, 100.0) : [1.0, 1.5, 2.0, 2.5, 3.0, 3.5].concat(rng(3.6, 4.6, 0.1), [5.0]); },
    fit: function (rows, p) {
      var st = stage(rows, 1), pts, top = 0.0, i, v;
      if (st.length < 4) return 0.0;
      pts = sortx(mapRows(st, function (r) { return [Number(r.x), (Number(r.y) - p.bg) * Number(r.x) * Number(r.x)]; }));
      for (i = 0; i < Math.min(3, pts.length); i++) top += pts[i][1];
      top /= Math.min(3, pts.length);
      v = half(pts, top / 2.0, 1, 0);
      return v !== null ? v : 0.0;
    },
  });

  // ================================================================ proportional counter
  var PropCounter = sweep({
    PARAMS: { x: 0.0, s: 0.0, E: 5.895, Vop: 1700.0, V0: 1700.0, a: 0.009, kc: 33.9, W: 0.0262, F: 0.17, b: 0.5, esc: 0.12, L1: 0.0, L2: 0.0, Ntot: 3.0e6, seed: 61.0 },
    NST: 2,
    res: function (p, E) { return 2.355 * Math.sqrt((p.F + p.b) * p.W / E); },
    chan: function (p, E, V) { return p.kc * E * Math.exp(p.a * (V - p.V0)); },
    line: function (p, E, ch, V) { var c = PropCounter.chan(p, E, V), sg = PropCounter.res(p, E) * c / 2.355; return Math.exp(-0.5 * Math.pow((ch - c) / sg, 2)) / (sg * Math.sqrt(2.0 * PI)); },
    read: function (p, s, x, k) {
      if (s === 0) return { y: q_(PropCounter.chan(p, p.E, x), 0.1) };
      var V = p.Vop, d = PropCounter.line(p, p.E, x, V);
      if (p.E > 3.2) d += p.esc * PropCounter.line(p, p.E - 2.957, x, V);
      if (p.L1 > 0 || p.L2 > 0) d += p.L1 * PropCounter.line(p, 13.95, x, V) + p.L2 * PropCounter.line(p, 17.61, x, V);
      return { y: cnt(p, k, p.Ntot * d) };
    },
    xs: function (p, s) {
      if (s === 0) return rng(p.Vop - 150.0, p.Vop + 150.0, 25.0);
      var c = PropCounter.chan(p, p.E, p.Vop), w = PropCounter.res(p, p.E) * c;
      var lo = Math.floor((c - 1.6 * w) / 2.0) * 2.0, hi = Math.floor((c + 1.6 * w) / 2.0) * 2.0;
      return rng(Math.max(lo, 2.0), hi, 2.0);
    },
    fit: function (rows) {
      var st = stage(rows, 1), pts, pk;
      if (st.length < 5) return 0.0;
      pts = sorted(st); pk = peakwidth(pts, pts[0][0], pts[pts.length - 1][0], 0.0);
      if (pk === null || pk[0] <= 0) return 0.0;
      return 100.0 * pk[1] / pk[0];
    },
  });

  // ================================================================ beta spectrum, Kurie plot
  var Kurie = sweep({
    PARAMS: { x: 0.0, s: 0.0, m: 0.0, T1: 514.0, Z1: 56.0, f1: 1.0, T2: 1175.6, Z2: 56.0, f2: 0.0, Tc: 624.2, fc: 0.08, wc: 12.0, dT: 10.0, kI: 0.5, Rm: 0.02, Ntot: 4.0e6, seed: 71.0 },
    fermi: function (Z, W) { var pp = Math.sqrt(W * W - 1.0), eta = Z * ALPHA * W / pp; return 2.0 * PI * eta / (1.0 - Math.exp(-2.0 * PI * eta)); },
    shape: function (Z, T0, T) {
      if (T <= 0 || T >= T0) return 0.0;
      var W = 1.0 + T / ME_KEV, W0 = 1.0 + T0 / ME_KEV;
      return Kurie.fermi(Z, W) * Math.sqrt(W * W - 1.0) * W * Math.pow(W0 - W, 2);
    },
    norm: function (Z, T0) {
      var n = 400, h = T0 / n, tot = 0.0, i, w;
      for (i = 0; i <= n; i++) { w = (i === 0 || i === n) ? 1.0 : (i % 2 === 1 ? 4.0 : 2.0); tot += w * Kurie.shape(Z, T0, h * i); }
      return tot * h / 3.0;
    },
    dens: function (p, T) {
      var d = 0.0;
      if (p.f1 > 0) d += p.f1 * Kurie.shape(p.Z1, p.T1, T) / Kurie.norm(p.Z1, p.T1);
      if (p.f2 > 0) d += p.f2 * Kurie.shape(p.Z2, p.T2, T) / Kurie.norm(p.Z2, p.T2);
      if (p.fc > 0) d += p.fc * Math.exp(-0.5 * Math.pow((T - p.Tc) / p.wc, 2)) / (p.wc * Math.sqrt(2.0 * PI));
      return d;
    },
    kin: function (p, x) { if (p.m < 0.5) return x; var pp = p.kI * x; return (Math.sqrt(pp * pp + 1.0) - 1.0) * ME_KEV; },
    read: function (p, s, x, k) {
      var T = Kurie.kin(p, x), mean, pp, W;
      if (T <= 0) return { y: 0.0 };
      if (p.m < 0.5) mean = p.Ntot * Kurie.dens(p, T) * p.dT;
      else { pp = p.kI * x; W = 1.0 + T / ME_KEV; mean = p.Ntot * Kurie.dens(p, T) * (pp / W) * ME_KEV * p.Rm * pp; }
      return { y: cnt(p, k, mean) };
    },
    xs: function (p) {
      var Tm = Math.max(p.T1, p.f2 > 0 ? p.T2 : 0.0, p.fc > 0 ? p.Tc : 0.0), pmax;
      if (p.m < 0.5) return rng(p.dT, 1.15 * Tm, p.dT);
      pmax = Math.sqrt(Math.pow(1.0 + 1.15 * Tm / ME_KEV, 2) - 1.0);
      return rng(0.05, pmax / p.kI, 0.05);
    },
    kuriePts: function (rows, p) {
      var out = [], i, T, n, W, pp, F, K;
      for (i = 0; i < rows.length; i++) {
        T = Kurie.kin(p, Number(rows[i].x)); n = Number(rows[i].y);
        if (T <= 0 || n <= 0) continue;
        W = 1.0 + T / ME_KEV; pp = Math.sqrt(W * W - 1.0); F = Kurie.fermi(p.Z1, W);
        K = p.m < 0.5 ? Math.sqrt(n / (pp * W * F)) : Math.sqrt(n / (F * pp * pp * pp));
        out.push([W, K, T, n]);
      }
      return out;
    },
    window: function (rows, p) {
      var pts = sortx(mapRows(rows, function (r) { return [Kurie.kin(p, Number(r.x)), Number(r.y)]; })), best = -1.0, ib = -1, i;
      if (pts.length < 6) return null;
      var tlast = 0.0;
      for (i = 0; i < pts.length; i++) if (pts[i][1] > 0) tlast = pts[i][0];
      for (i = 0; i < pts.length; i++) if (pts[i][0] <= 0.6 * tlast && pts[i][1] > best) { best = pts[i][1]; ib = i; }
      if (ib < 0) return null;
      for (i = ib; i < pts.length; i++) if (pts[i][1] < 0.03 * best) return pts[i][0];
      return null;
    },
    fit: function (rows, p) {
      var st = stage(rows, 0), tend = Kurie.window(st, p), pts, f;
      if (!tend) return 0.0;
      pts = Kurie.kuriePts(st, p).filter(function (q) { return 0.35 * tend <= q[2] && q[2] <= 0.85 * tend; }).map(function (q) { return [q[0], q[1]]; });
      f = linfit(pts);
      if (!f || f[0] >= 0) return 0.0;
      return (-f[1] / f[0] - 1.0) * ME_KEV;
    },
  });

  // ================================================================ gamma-gamma angular correlation
  var AngCorr = sweep({
    PARAMS: { x: 90.0, s: 0.0, a2: 0.125, a4: 0.0416667, C0: 1000.0, ch: 5.0, t: 50000.0, seed: 83.0 },
    NST: 2,
    read: function (p, s, x, k) {
      var c = Math.cos(x * PI / 180.0), n = p.ch + (s === 1 ? p.C0 * (1.0 + p.a2 * c * c + p.a4 * c * c * c * c) : 0.0), N = cnt(p, k, n * p.t);
      return { y: N / p.t, N: N, T: p.t };
    },
    xs: function (p, s) { return s === 0 ? [90.0] : rng(90.0, 180.0, 15.0); },
    fit: function (rows) {
      var ch = stage(rows, 0), pr = stage(rows, 1), c0, w90 = null, i, c, u, v, y, s11 = 0.0, s12 = 0.0, s22 = 0.0, s1y = 0.0, s2y = 0.0, den;
      if (!ch.length || pr.length < 3) return 0.0;
      c0 = Number(ch[0].y);
      for (i = 0; i < pr.length; i++) if (Math.abs(Number(pr[i].x) - 90.0) < 1e-6) w90 = Number(pr[i].y) - c0;
      if (!w90 || w90 <= 0) return 0.0;
      for (i = 0; i < pr.length; i++) {
        c = Math.cos(Number(pr[i].x) * PI / 180.0); u = c * c; v = c * c * c * c;
        y = (Number(pr[i].y) - c0) / w90 - 1.0;
        s11 += u * u; s12 += u * v; s22 += v * v; s1y += u * y; s2y += v * y;
      }
      den = s11 * s22 - s12 * s12;
      if (Math.abs(den) < 1e-300) return 0.0;
      return (s1y * s22 - s2y * s12) / den;
    },
  });

  // ================================================================ Hall effect against temperature
  var HallT = sweep({
    PARAMS: { x: 300.0, s: 0.0, Eg0: 0.782, ni300: 2.33e19, N: 2.0e19, typ: 1.0, mun: 0.39, mup: 0.19, I: 1.0e-3, B: 0.3, d: 5.0e-4, w: 5.0e-3, L: 1.0e-2 },
    carriers: function (p, T) {
      var ni = p.ni300 * Math.pow(T / 300.0, 1.5) * Math.exp(-p.Eg0 / (2.0 * KB_EV) * (1.0 / T - 1.0 / 300.0));
      var maj = p.N / 2.0 + Math.sqrt(p.N * p.N / 4.0 + ni * ni), mino = ni * ni / maj;
      return p.typ > 0 ? [mino, maj] : [maj, mino];
    },
    rhSig: function (p, T) {
      var c = HallT.carriers(p, T), n = c[0], h = c[1], f = Math.pow(T / 300.0, -1.5), un = p.mun * f, up = p.mup * f;
      var sig = QE * (n * un + h * up), rh = (h * up * up - n * un * un) / (QE * Math.pow(h * up + n * un, 2));
      return [rh, sig];
    },
    read: function (p, s, x) {
      var r = HallT.rhSig(p, x), vh = r[0] * p.I * p.B / p.d * 1000.0, vs = p.I * p.L / (r[1] * p.w * p.d) * 1000.0;
      return { y: q_(vh, 0.001), y2: q_(vs, 0.01) };
    },
    xs: function () { return [77.0, 100.0, 150.0, 200.0, 250.0, 300.0, 320.0, 340.0, 360.0, 380.0, 390.0, 400.0, 410.0, 420.0]; },
    fit: function (rows, p) {
      var pts = [], st = stage(rows, 0), i, T, rh, f;
      for (i = 0; i < st.length; i++) {
        T = Number(st[i].x); rh = Math.abs(Number(st[i].y)) / 1000.0 * p.d / (p.I * p.B);
        if (T >= 375.0 && rh > 0) pts.push([1.0 / T, Math.log(rh * Math.pow(T, 1.5))]);
      }
      f = linfit(pts);
      return f ? 2.0 * KB_EV * f[0] : 0.0;
    },
  });

  // ================================================================ two-probe conductivity
  var TwoProbe = sweep({
    PARAMS: { x: 300.0, s: 0.0, mat: 0.0, Eg0: 0.782, ni300: 2.33e19, mun: 0.39, mup: 0.19, rhog: 1.0e-5, ag: -4.0e-4, L: 1.0e-2, A: 1.0e-6, Rc: 0.3, I: 1.0e-4 },
    sigma: function (p, T) {
      if (p.mat > 0.5) return 1.0 / (p.rhog * (1.0 + p.ag * (T - 300.0)));
      var ni = p.ni300 * Math.pow(T / 300.0, 1.5) * Math.exp(-p.Eg0 / (2.0 * KB_EV) * (1.0 / T - 1.0 / 300.0)), f = Math.pow(T / 300.0, -1.5);
      return QE * ni * (p.mun + p.mup) * f;
    },
    read: function (p, s, x) { var R = p.L / (TwoProbe.sigma(p, x) * p.A) + 2.0 * p.Rc; return { y: q_(p.I * R * 1000.0, 0.001) }; },
    xs: function () { return rng(300.0, 420.0, 10.0); },
    fit: function (rows, p) {
      var st = stage(rows, 0), i, R, pts = [], f;
      if (p.mat > 0.5) {
        for (i = 0; i < st.length; i++) if (Math.abs(Number(st[i].x) - 300.0) < 1e-6 && Number(st[i].y) > 0) { R = Number(st[i].y) / 1000.0 / p.I; return p.L / (R * p.A); }
        return 0.0;
      }
      for (i = 0; i < st.length; i++) if (Number(st[i].y) > 0) { R = Number(st[i].y) / 1000.0 / p.I; pts.push([1.0 / Number(st[i].x), Math.log(p.L / (R * p.A))]); }
      f = linfit(pts);
      return f ? -2.0 * KB_EV * f[0] : 0.0;
    },
  });

  // ================================================================ diode ideality + band gap
  var DiodeIV = sweep({
    PARAMS: { x: 300.0, s: 0.0, Eg0: 1.206, nid: 1.8, I300: 1.0e-11, I1: 1.0e-4, I2: 1.0e-3 },
    i0: function (p, T) { var c = p.I300 / (Math.pow(300.0, 3) * Math.exp(-p.Eg0 / (KB_EV * 300.0))); return c * T * T * T * Math.exp(-p.Eg0 / (KB_EV * T)); },
    volt: function (p, T, I) { return p.nid * KB_EV * T * Math.log(I / DiodeIV.i0(p, T) + 1.0); },
    read: function (p, s, x) { return { y: q_(DiodeIV.volt(p, x, p.I1) * 1000.0, 0.1), y2: q_(DiodeIV.volt(p, x, p.I2) * 1000.0, 0.1) }; },
    xs: function () { return rng(300.0, 380.0, 10.0); },
    ideal: function (p, r) { var T = Number(r.x), vt = KB_EV * T; return (Number(r.y2) - Number(r.y)) / 1000.0 / (vt * Math.log(p.I2 / p.I1)); },
    fit: function (rows, p) {
      var pts = [], st = stage(rows, 0), i, T, n, i0, f;
      for (i = 0; i < st.length; i++) {
        T = Number(st[i].x); n = DiodeIV.ideal(p, st[i]);
        if (n <= 0) continue;
        i0 = p.I1 / (Math.exp(Number(st[i].y) / 1000.0 / (n * KB_EV * T)) - 1.0);
        pts.push([1.0 / T, Math.log(i0 / (T * T * T))]);
      }
      f = linfit(pts);
      return f ? -KB_EV * f[0] : 0.0;
    },
  });

  // ================================================================ photoconductivity
  var PhotoCond = sweep({
    PARAMS: { x: 20.0, s: 0.0, Eg: 2.42, sw: 0.03, gam: 0.8, Ip: 80.0, d0: 20.0, Id: 0.05, Im: 40.0, Ion: 40.0, tau: 0.05, l1: 400.0, l2: 700.0 },
    NST: 4,
    read: function (p, s, x) {
      var v, E;
      if (s === 0) v = p.Ip * Math.pow(p.d0 / x, 2.0 * p.gam) + p.Id;
      else if (s === 1) { E = HC_EVNM / x; v = p.Im * 0.5 * erfc((p.Eg - E) / (Math.sqrt(2.0) * p.sw)) + p.Id; }
      else if (s === 2) v = p.Ion * (1.0 - Math.exp(-x / p.tau)) + p.Id;
      else v = p.Ion * Math.exp(-x / p.tau) + p.Id;
      return { y: q_(v, 0.01) };
    },
    xs: function (p, s) { return s === 0 ? [10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0] : s === 1 ? rng(p.l1, p.l2, 5.0) : rng(0.0, 0.25, 0.025); },
    fit: function (rows) {
      var st = stage(rows, 1), pts, dark = Infinity, top = -Infinity, ib = 0, i, lc;
      if (st.length < 5) return 0.0;
      pts = sorted(st);
      for (i = 0; i < pts.length; i++) { if (pts[i][1] < dark) dark = pts[i][1]; if (pts[i][1] > top) top = pts[i][1]; }
      for (i = 0; i < pts.length; i++) if (pts[i][1] === top) ib = i;
      lc = half(pts, dark + (top - dark) / 2.0, 1, ib);
      return lc ? HC_EVNM / lc : 0.0;
    },
  });

  // ================================================================ AC susceptibility of YBCO
  var ACSusc = sweep({
    PARAMS: { x: 100.0, s: 0.0, Tc: 92.0, dT: 1.2, V0: 50.0, Vl: 6.0, Voff: 2.0 },
    read: function (p, s, x) {
      var f = 0.5 * erfc((x - p.Tc) / (Math.sqrt(2.0) * p.dT));
      return { y: q_(p.Voff - p.V0 * f, 0.01), y2: q_(p.Vl * Math.exp(-0.5 * Math.pow((x - p.Tc) / p.dT, 2)), 0.01) };
    },
    xs: function () { return [80.0, 84.0, 86.0, 88.0].concat(rng(89.0, 96.0, 0.5), [98.0, 100.0, 105.0]); },
    fit: function (rows) {
      var pts = sorted(stage(rows, 0)), v;
      if (pts.length < 5) return 0.0;
      v = half(pts, (pts[0][1] + pts[pts.length - 1][1]) / 2.0, 1, 0);
      return v !== null ? v : 0.0;
    },
  });

  // ================================================================ LC lattice
  var LCLattice = sweep({
    PARAMS: { x: 1000.0, s: 0.0, d: 0.0, L: 1.0e-2, C: 1.0e-7, C1: 1.0e-7, C2: 4.7e-8 },
    phase: function (p, f) {
      var w = 2.0 * PI * f, r, r2, s;
      if (p.d < 0.5) { r = f * PI * Math.sqrt(p.L * p.C); r2 = r * r; }
      else { s = 1.0 / p.C1 + 1.0 / p.C2; r2 = p.C1 * p.C2 * p.L * w * w * (2.0 * s - w * w * p.L) / 4.0; }
      if (r2 >= 1.0) return 180.0;
      if (r2 <= 0) return 0.0;
      return 2.0 * Math.asin(Math.sqrt(r2)) * 180.0 / PI;
    },
    read: function (p, s, x) { return { y: q_(LCLattice.phase(p, x), 0.5) }; },
    xs: function (p) {
      var fc = p.d < 0.5 ? 1.0 / (PI * Math.sqrt(p.L * p.C)) : Math.sqrt(2.0 / (p.L * p.C1)) / (2.0 * PI), out = [], i;
      for (i = 1; i < 13; i++) out.push(Math.floor(fc * 0.075 * i / 50.0 + 0.5) * 50.0);
      if (p.d >= 0.5) [1.05, 1.2, 1.35, 1.5, 1.55, 1.6, 1.65, 1.7, 1.75].forEach(function (m) { out.push(Math.floor(fc * m / 50.0 + 0.5) * 50.0); });
      return out;
    },
    acoustic: function (rows) {
      var pts = sortx(mapRows(stage(rows, 0), function (r) { return [Number(r.x), Number(r.y)]; })), out = [], i;
      for (i = 0; i < pts.length; i++) { if (pts[i][1] >= 179.9) break; out.push(pts[i]); }
      return out;
    },
    fit: function (rows, p) {
      var pts = [], st = LCLattice.acoustic(rows), i, ph, f, sn, w2, sxy = 0.0, sxx = 0.0, ff, A, B, disc;
      for (i = 0; i < st.length; i++) {
        ph = st[i][1];
        if (ph > 5.0 && ph < 170.0) {
          f = st[i][0]; sn = Math.sin(ph / 2.0 * PI / 180.0);
          if (p.d < 0.5) pts.push([sn, f]); else { w2 = Math.pow(2.0 * PI * f, 2); pts.push([w2, sn * sn / w2]); }
        }
      }
      if (pts.length < 3) return 0.0;
      if (p.d < 0.5) { for (i = 0; i < pts.length; i++) { sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; } return sxy / sxx; }
      ff = linfit(pts);
      if (!ff || ff[0] >= 0 || ff[1] <= 0) return 0.0;
      A = ff[1]; B = -ff[0]; disc = A * A - 4.0 * B;
      if (disc < 0) return 0.0;
      return Math.sqrt((A - Math.sqrt(disc)) / (2.0 * B)) / (2.0 * PI);
    },
  });

  // ================================================================ pulse echo
  var PulseEcho = sweep({
    PARAMS: { x: 1.0, s: 0.0, v: 6320.0, d: 0.05, rho: 2700.0, att: 4.0 },
    read: function (p, s, x) { return { y: q_(2.0 * x * p.d / p.v * 1e6, 0.01), y2: q_(100.0 * Math.exp(-p.att * 2.0 * x * p.d), 0.1) }; },
    xs: function () { return [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]; },
    fit: function (rows, p) { var f = linfit(mapRows(stage(rows, 0), function (r) { return [Number(r.x), Number(r.y) * 1e-6]; })); return f && f[0] > 0 ? 2.0 * p.d / f[0] : 0.0; },
  });

  // ================================================================ velocity of sound, CRO phase method
  var SoundCRO = sweep({
    PARAMS: { x: 0.0, s: 0.0, f: 3000.0, tc: 27.0, x0: 62.0 },
    vel: function (p) { return 331.3 * Math.sqrt(1.0 + p.tc / 273.15); },
    read: function (p, s, x) { var lam = SoundCRO.vel(p) / p.f * 1000.0; return { y: q_(p.x0 + x * lam / 2.0, 0.5) }; },
    xs: function () { return [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]; },
    fit: function (rows, p) { var f = linfit(mapRows(stage(rows, 0), function (r) { return [Number(r.x), Number(r.y)]; })); return f ? 2.0 * f[0] / 1000.0 * p.f : 0.0; },
  });

  // ================================================================ Lecher wire
  var Lecher = sweep({
    PARAMS: { x: 0.0, s: 0.0, f: 6.0e8, eps: 2.2, x0: 8.0 },
    NST: 2,
    read: function (p, s, x) { var lam = C0 / p.f * 100.0; if (s === 1) lam /= Math.sqrt(p.eps); return { y: q_(p.x0 + x * lam / 2.0, 0.1) }; },
    xs: function (p, s) {
      var lam = C0 / p.f * 100.0, n, out = [], i;
      if (s === 1) lam /= Math.sqrt(p.eps);
      n = Math.floor((120.0 - p.x0) / (lam / 2.0));
      for (i = 0; i <= Math.min(n, 9); i++) out.push(i);
      return out;
    },
    lamOf: function (rows, s) { var f = linfit(mapRows(stage(rows, s), function (r) { return [Number(r.x), Number(r.y)]; })); return f ? 2.0 * f[0] : 0.0; },
    fit: function (rows) { var a = Lecher.lamOf(rows, 0), b = Lecher.lamOf(rows, 1); return a > 0 && b > 0 ? Math.pow(a / b, 2) : 0.0; },
  });

  // ================================================================ Fourier analysis
  var FourierW = sweep({
    PARAMS: { x: 1.0, s: 0.0, shape: 0.0, A: 2.0, M: 2000.0 },
    wave: function (p, u) {
      var sh = Math.floor(p.shape + 0.5), v;
      if (sh === 0) return u < 0.5 ? p.A : -p.A;
      if (sh === 1) { if (u < 0.25) return 4.0 * p.A * u; if (u < 0.75) return p.A * (2.0 - 4.0 * u); return p.A * (4.0 * u - 4.0); }
      v = Math.sin(2.0 * PI * u);
      return v > 0 ? p.A * v : 0.0;
    },
    coef: function (p, n) {
      var M = Math.floor(p.M + 0.5), a = 0.0, b = 0.0, i, u, w;
      for (i = 0; i < M; i++) { u = (i + 0.5) / M; w = FourierW.wave(p, u); a += w * Math.cos(2.0 * PI * n * u); b += w * Math.sin(2.0 * PI * n * u); }
      a *= 2.0 / M; b *= 2.0 / M;
      return Math.sqrt(a * a + b * b);
    },
    read: function (p, s, x) { return { y: q_(FourierW.coef(p, Math.floor(x + 0.5)), 0.001) }; },
    xs: function () { return [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]; },
    second: function (p) { return Math.floor(p.shape + 0.5) === 2 ? 2 : 3; },
    fit: function (rows, p) {
      var c1 = null, c2 = null, n2 = FourierW.second(p), st = stage(rows, 0), i, n;
      for (i = 0; i < st.length; i++) { n = Math.floor(Number(st[i].x) + 0.5); if (n === 1) c1 = Number(st[i].y); if (n === n2) c2 = Number(st[i].y); }
      return c1 && c2 !== null ? c2 / c1 : 0.0;
    },
  });

  // ================================================================ transducers
  var Transducer = sweep({
    PARAMS: { x: 0.0, s: 0.0, typ: 0.0, R25: 10000.0, Bt: 3950.0, GF: 2.0, Vex: 5.0, S: 50.0, c: 0.02, xr: 5.0, a1: 0.03996, a2: 1.0e-5 },
    read: function (p, s, x) {
      var t = Math.floor(p.typ + 0.5), T, e;
      if (t === 0) { T = x + 273.15; return { y: q_(p.R25 * Math.exp(p.Bt * (1.0 / T - 1.0 / 298.15)), 1.0) }; }
      if (t === 1) { e = x * 1e-6; return { y: q_(p.Vex * p.GF * e / (4.0 + 2.0 * p.GF * e) * 1000.0, 0.001) }; }
      if (t === 2) return { y: q_(p.S * x * (1.0 - p.c * Math.pow(x / p.xr, 2)), 0.1) };
      return { y: q_(p.a1 * x + p.a2 * x * x, 0.001) };
    },
    xs: function (p) { var t = Math.floor(p.typ + 0.5); return t === 0 ? rng(25.0, 85.0, 10.0) : t === 1 ? rng(0.0, 1000.0, 100.0) : t === 2 ? rng(-5.0, 5.0, 1.0) : rng(0.0, 100.0, 10.0); },
    fit: function (rows, p) {
      var t = Math.floor(p.typ + 0.5), st = stage(rows, 0), pts, f;
      if (t === 0) {
        pts = mapRows(st.filter(function (r) { return Number(r.y) > 0; }), function (r) { return [1.0 / (Number(r.x) + 273.15), Math.log(Number(r.y))]; });
        f = linfit(pts); return f ? f[0] : 0.0;
      }
      if (t === 2) pts = mapRows(st.filter(function (r) { return Math.abs(Number(r.x)) <= 2.0 + 1e-9; }), function (r) { return [Number(r.x), Number(r.y)]; });
      else pts = mapRows(st, function (r) { return [Number(r.x), Number(r.y)]; });
      f = linfit(pts);
      if (!f) return 0.0;
      if (t === 1) return f[0] * 1e6 * 4.0 / (p.Vex * 1000.0);
      if (t === 3) return f[0] * 1000.0;
      return f[0];
    },
  });

  // ================================================================ Stefan's constant
  var Stefan = sweep({
    PARAMS: { x: 0.0, s: 0.0, m: 0.0, sigma: 5.670374419e-8, mb: 0.06, cb: 385.0, Ab: 5.03e-3, eb: 0.97, T0: 300.0, Ti: 620.0, dt: 20.0, ew: 0.35, Af: 1.2e-5, R0: 1.0 },
    temp: function (p, t) {
      var n = Math.floor(t / p.dt + 0.5) * 100, h = n > 0 ? t / n : 0.0, T = p.Ti, k = p.sigma * p.eb * p.Ab / (p.mb * p.cb), T04 = Math.pow(p.T0, 4), i, k1, k2, k3, k4;
      function f(u) { return -k * (u * u * u * u - T04); }
      for (i = 0; i < n; i++) { k1 = f(T); k2 = f(T + 0.5 * h * k1); k3 = f(T + 0.5 * h * k2); k4 = f(T + h * k3); T += h * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0; }
      return T;
    },
    lampT: function (p, V) {
      var lo = p.T0, hi = 4000.0, i, mid, R;
      for (i = 0; i < 100; i++) { mid = (lo + hi) / 2.0; R = p.R0 * Math.pow(mid / p.T0, 1.2); if (V * V / R > p.sigma * p.ew * p.Af * Math.pow(mid, 4)) lo = mid; else hi = mid; }
      return (lo + hi) / 2.0;
    },
    read: function (p, s, x) {
      if (p.m < 0.5) return { y: q_(Stefan.temp(p, x) - 273.15, 0.1) };
      var T = Stefan.lampT(p, x), R = p.R0 * Math.pow(T / p.T0, 1.2);
      return { y: q_(x / R * 1000.0, 0.1) };
    },
    xs: function (p) { return p.m < 0.5 ? rng(0.0, 20.0 * p.dt, p.dt) : rng(2.0, 12.0, 1.0); },
    fit: function (rows, p) {
      var st = sortx(mapRows(stage(rows, 0), function (r) { return [Number(r.x), Number(r.y)]; })), sxy = 0.0, sxx = 0.0, i, dTdt, T, yv, xv, V, I, R;
      if (st.length < 4) return 0.0;
      if (p.m < 0.5) {
        for (i = 1; i < st.length - 1; i++) {
          dTdt = (st[i + 1][1] - st[i - 1][1]) / (st[i + 1][0] - st[i - 1][0]); T = st[i][1] + 273.15;
          yv = -dTdt * p.mb * p.cb / (p.eb * p.Ab); xv = Math.pow(T, 4) - Math.pow(p.T0, 4);
          sxy += xv * yv; sxx += xv * xv;
        }
        return sxx > 0 ? sxy / sxx : 0.0;
      }
      for (i = 0; i < st.length; i++) {
        V = st[i][0]; I = st[i][1] / 1000.0;
        if (I <= 0) continue;
        R = V / I; T = p.T0 * Math.pow(R / p.R0, 1.0 / 1.2); xv = p.ew * p.Af * Math.pow(T, 4);
        sxy += xv * V * I; sxx += xv * xv;
      }
      return sxx > 0 ? sxy / sxx : 0.0;
    },
  });

  // ================================================================ copper characteristic X-rays
  var CuXray = sweep({
    PARAMS: { x: 40.0, s: 0.0, V: 30.0, dc: 2.0135, la1: 1.540562, la2: 1.544390, lb: 1.392218, Ia: 1500.0, Ib: 300.0, Ic: 40.0, wd: 0.30, tn: 0.0018, rho: 8.908, muA: 49.3, muB: 276.0, edge: 1.48802, t: 10.0, seed: 97.0 },
    NST: 2,
    lam: function (p, tt) { return 2.0 * p.dc * Math.sin(tt / 2.0 * PI / 180.0); },
    ang: function (p, lam) { return 2.0 * Math.asin(lam / (2.0 * p.dc)) * 180.0 / PI; },
    trans: function (p, lam) { var mu = lam > p.edge ? p.muA * Math.pow(lam / 1.540562, 2.8) : p.muB * Math.pow(lam / 1.392218, 2.8); return Math.exp(-mu * p.rho * p.tn); },
    rate: function (p, s, tt) {
      var lam = CuXray.lam(p, tt), lmin = HC_KEVA / p.V, br = lam > lmin ? p.Ic * (lam / lmin - 1.0) / (lam * lam) : 0.0, sg = p.wd / 2.355, g = 0.0, L, i, n;
      L = [[p.la1, 1.0], [p.la2, 0.5], [p.lb, p.Ib / p.Ia]];
      for (i = 0; i < 3; i++) g += L[i][1] * Math.exp(-0.5 * Math.pow((tt - CuXray.ang(p, L[i][0])) / sg, 2));
      n = br + p.Ia * g;
      return s === 1 ? n * CuXray.trans(p, lam) : n;
    },
    read: function (p, s, x, k) { var c = cnt(p, k, CuXray.rate(p, s, x) * p.t); return { y: c / p.t, N: c }; },
    xs: function () { return rng(36.0, 50.0, 0.1); },
    fit: function (rows, p) {
      var pts = sorted(stage(rows, 0)), best = -1.0, ib = -1, i, lo, hi, base, sw = 0.0, swy = 0.0, q;
      if (pts.length < 10) return 0.0;
      for (i = 0; i < pts.length; i++) if (pts[i][1] > best) { best = pts[i][1]; ib = i; }
      lo = pts[Math.max(ib - 25, 0)][1]; hi = pts[Math.min(ib + 25, pts.length - 1)][1];
      base = lo < hi ? lo : hi;
      for (i = Math.max(ib - 12, 0); i < Math.min(ib + 13, pts.length); i++) { q = pts[i]; if (q[1] - base > (best - base) / 2.0) { sw += q[1] - base; swy += (q[1] - base) * q[0]; } }
      if (sw <= 0) return 0.0;
      return CuXray.lam(p, swy / sw);
    },
  });

  // ================================================================ microwave Bragg diffraction
  var MWBragg = sweep({
    PARAMS: { x: 10.0, s: 0.0, d: 0.040, lam: 0.02855, wb: 3.0, A1: 80.0, A2: 45.0, bk: 4.0 },
    read: function (p, s, x) {
      var sg = p.wb / 2.355, v = p.bk, L = [[1, p.A1], [2, p.A2]], i, r, th;
      for (i = 0; i < 2; i++) { r = L[i][0] * p.lam / (2.0 * p.d); if (r < 1.0) { th = Math.asin(r) * 180.0 / PI; v += L[i][1] * Math.exp(-0.5 * Math.pow((x - th) / sg, 2)); } }
      return { y: q_(v, 0.1) };
    },
    xs: function () { return rng(10.0, 60.0, 0.5); },
    peaks: function (rows, p) {
      var pts = sorted(stage(rows, 0)), out = [], i, pk;
      for (i = 1; i < pts.length - 1; i++) if (pts[i][1] > pts[i - 1][1] && pts[i][1] >= pts[i + 1][1] && pts[i][1] > 3.0 * p.bk) {
        pk = peakwidth(pts, pts[i][0] - 0.01, pts[i][0] + 0.01, p.bk); if (pk) out.push(pk[0]);
      }
      return out;
    },
    fit: function (rows, p) {
      var pk = MWBragg.peaks(rows, p), tot = 0.0, i;
      if (!pk.length) return 0.0;
      for (i = 0; i < Math.min(pk.length, 2); i++) tot += (i + 1) * p.lam / (2.0 * Math.sin(pk[i] * PI / 180.0));
      return tot / Math.min(pk.length, 2);
    },
  });

  // ================================================================ horn antenna pattern
  var HornPattern = sweep({
    PARAMS: { x: 0.0, s: 0.0, pl: 0.0, a: 0.070, b: 0.052, lam: 0.02855 },
    NST: 2,
    pat: function (p, th) {
      var sn = Math.sin(th * PI / 180.0), v, u, den;
      if (p.pl < 0.5) { v = PI * p.b * sn / p.lam; return Math.abs(v) < 1e-12 ? 1.0 : Math.sin(v) / v; }
      u = PI * p.a * sn / p.lam; den = 1.0 - Math.pow(2.0 * u / PI, 2);
      if (Math.abs(den) < 1e-9) return PI / 4.0;
      return Math.cos(u) / den;
    },
    read: function (p, s, x) {
      if (s === 1) { var g = HornPattern.gain(p) * p.lam / (4.0 * PI * x); return { y: q_(1000.0 * g * g, 0.001) }; }
      var f = HornPattern.pat(p, x); return { y: q_(100.0 * f * f, 0.1) };
    },
    xs: function (p, s) { return s === 0 ? rng(-40.0, 40.0, 1.0) : [0.6, 0.8, 1.0, 1.2]; },
    fit: function (rows) { var pk = peakwidth(sorted(stage(rows, 0)), -5.0, 5.0, 0.0); return pk ? pk[1] : 0.0; },
    gain: function (p) { return 8.0 / (PI * PI) * 4.0 * PI * p.a * p.b / (p.lam * p.lam); },
  });

  // ================================================================ coupled oscillators
  var Coupled = sweep({
    PARAMS: { x: 0.0, s: 0.0, m: 0.0, g: 9.81, L: 0.6, mb: 0.2, k: 1.0, Lc: 1.0e-2, C: 1.0e-6, Mu: 1.0e-3, nper: 10.0 },
    omegas: function (p) {
      if (p.m < 0.5) return [Math.sqrt(p.g / p.L), Math.sqrt(p.g / p.L + 2.0 * p.k / p.mb)];
      return [1.0 / Math.sqrt((p.Lc + p.Mu) * p.C), 1.0 / Math.sqrt((p.Lc - p.Mu) * p.C)];
    },
    read: function (p, s, x) {
      var w = Coupled.omegas(p), i = Math.floor(x + 0.5), t;
      if (i === 2) t = 2.0 * PI / (w[1] - w[0]); else t = p.nper * 2.0 * PI / (i === 0 ? w[0] : w[1]);
      if (p.m < 0.5) return { y: q_(t, 0.01) };
      return { y: q_(t * 1000.0, 0.001) };
    },
    xs: function () { return [0.0, 1.0, 2.0]; },
    fit: function (rows) {
      var t1 = null, t2 = null, st = stage(rows, 0), i, n;
      for (i = 0; i < st.length; i++) { n = Math.floor(Number(st[i].x) + 0.5); if (n === 0) t1 = Number(st[i].y); if (n === 1) t2 = Number(st[i].y); }
      if (!t1 || !t2) return 0.0;
      return (t1 * t1 - t2 * t2) / (t1 * t1 + t2 * t2);
    },
  });

  // ================================================================ gas-filled photocell
  var GasPhoto = sweep({
    PARAMS: { x: 0.0, s: 0.0, I0: 2.0, V0: 6.0, Vg: 35.0, al: 0.04, d0: 20.0, Vop: 60.0, Id: 0.002 },
    NST: 2,
    gain: function (p, V) { return V <= p.Vg ? 1.0 : Math.exp(p.al * (V - p.Vg)); },
    read: function (p, s, x) {
      var v;
      if (s === 0) v = p.I0 * (1.0 - Math.exp(-x / p.V0)) * GasPhoto.gain(p, x) + p.Id;
      else if (x <= 0) v = p.Id;
      else v = p.I0 * Math.pow(p.d0 / x, 2) * (1.0 - Math.exp(-p.Vop / p.V0)) * GasPhoto.gain(p, p.Vop) + p.Id;
      return { y: q_(v, 0.001) };
    },
    xs: function (p, s) { return s === 0 ? rng(0.0, 90.0, 5.0) : [0.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0]; },
    fit: function (rows) {
      var st = stage(rows, 1), dark = null, i, pts = [], f;
      for (i = 0; i < st.length; i++) if (Number(st[i].x) <= 0) dark = Number(st[i].y);
      if (dark === null) return 0.0;
      for (i = 0; i < st.length; i++) if (Number(st[i].x) > 0 && Number(st[i].y) - dark > 0) pts.push([Math.log(Number(st[i].x)), Math.log(Number(st[i].y) - dark)]);
      f = linfit(pts);
      return f ? f[0] : 0.0;
    },
  });

  function hpE(p) { return 2.0 * Math.asin(1.391557 * p.lam / (PI * p.b)) * 180.0 / PI; }
  function hpH(p) { return 2.0 * Math.asin(1.866585 * p.lam / (PI * p.a)) * 180.0 / PI; }

  HK.register({
    K: { pm9_gmdt: GMDead, pm9_gmeff: GMEff, pm9_betaf: BetaFeather, pm9_k40: K40Std, pm9_spark: SparkAlpha, pm9_prop: PropCounter,
      pm9_kurie: Kurie, pm9_angcorr: AngCorr, pm9_hallt: HallT, pm9_twop: TwoProbe, pm9_diode: DiodeIV, pm9_photoc: PhotoCond,
      pm9_acsusc: ACSusc, pm9_lclat: LCLattice, pm9_echo: PulseEcho, pm9_sound: SoundCRO, pm9_lecher: Lecher, pm9_fourier: FourierW,
      pm9_trans: Transducer, pm9_stefan: Stefan, pm9_cuxray: CuXray, pm9_mwbragg: MWBragg, pm9_horn: HornPattern,
      pm9_coupled: Coupled, pm9_gasphoto: GasPhoto },
    TEXTBOOK: {
      pm9_tau: function (p) { return p.tau; },
      pm9_eint: function (p) { return p.eint; },
      pm9_range: function (p) { return 0.412 * Math.pow(p.E1, 1.265 - 0.0954 * Math.log(p.E1)); },
      pm9_tbeta: function (p) { return p.T12 / p.br; },
      pm9_geiger: function (p) { return 0.318 * Math.pow(p.E, 1.5); },
      pm9_presol: function (p) { return 100.0 * 2.355 * Math.sqrt((p.F + p.b) * p.W / p.E); },
      pm9_endpoint: function (p) { return (p.f2 <= 0 || p.T1 >= p.T2) ? p.T1 : p.T2; },
      pm9_a2: function (p) { return p.a2; },
      pm9_eg0: function (p) { return p.Eg0; },
      pm9_twop: function (p) { return p.mat < 0.5 ? p.Eg0 : 1.0 / p.rhog; },
      pm9_egphoto: function (p) { return p.Eg; },
      pm9_tc: function (p) { return p.Tc; },
      pm9_lccut: function (p) { return p.d < 0.5 ? 1.0 / (PI * Math.sqrt(p.L * p.C)) : Math.sqrt(2.0 / (p.L * p.C1)) / (2.0 * PI); },
      pm9_v: function (p) { return p.v; },
      pm9_vsound: function (p) { return 331.3 * Math.sqrt(1.0 + p.tc / 273.15); },
      pm9_eps: function (p) { return p.eps; },
      pm9_fratio: function (p) { return [1.0 / 3.0, 1.0 / 9.0, 4.0 / (3.0 * PI)][Math.floor(p.shape + 0.5)]; },
      pm9_sens: function (p) { return [p.Bt, p.GF, p.S, 1000.0 * (p.a1 + 100.0 * p.a2)][Math.floor(p.typ + 0.5)]; },
      pm9_sigma: function (p) { return p.sigma; },
      pm9_kalpha: function (p) { return (2.0 * p.la1 + p.la2) / 3.0; },
      pm9_d: function (p) { return p.d; },
      pm9_hpbw: function (p) { return p.pl < 0.5 ? hpE(p) : hpH(p); },
      pm9_kappa: function (p) { return p.m < 0.5 ? p.k / (p.mb * p.g / p.L + p.k) : p.Mu / p.Lc; },
      pm9_isq: function () { return -2.0; },
    },
  });
  HK.PM9 = { erfc: erfc, Rnd: Rnd };
})(typeof window !== 'undefined' ? window : this);
