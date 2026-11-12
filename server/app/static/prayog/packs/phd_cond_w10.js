/* Kernel pack (browser twin of app/prayog/packs/phd_cond_w10.py): Ph.D. research techniques of condensed matter,
   wave 10 (kernels pk10_*). Same formulas, same order of operations, so both sides give the same numbers.
   Every kernel is a SWEEP: read(p, s, x, k) gives the reading at setting x of stage s, plan(p) lists the settings,
   fit(rows, p) works the result out of the rows (never from the hidden unknown), measure(p) = fit(run(plan)).
   SIMULATED DATA from the published models named in the Python pack: noiseless, rounded to the least count. */
(function (root) {
  'use strict';
  var HK = (root && root.HoolaKernels) ||
    (typeof module !== 'undefined' && module.exports && module.exports.register ? module.exports : null);
  if (!HK) throw new Error('HoolaKernels is not loaded');
  var PI = Math.PI, H = 6.62607015e-34, QE = 1.602176634e-19, KB = 1.380649e-23, NA = 6.02214076e23;
  var HBAR = H / (2.0 * PI), MUB = 9.2740100783e-24, MUN = 5.0507837461e-27, ME = 9.1093837015e-31;
  var MU0 = 1.25663706212e-6, EPS0 = 8.8541878128e-12, C0 = 299792458.0, RGAS = NA * KB, RK = H / (QE * QE);
  var L0 = 2.44e-8, MU_G = 0.09044, MU_E = -0.1549, EGAM = 14412.5 * QE;

  function q_(v, q) { return Math.floor(v / q + 0.5) * q; }
  function erfc(x) {
    if (x < 0) return 2.0 - erfc(-x);
    var t = 1.0 / (1.0 + 0.3275911 * x);
    var poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))));
    return poly * Math.exp(-x * x);
  }
  function logi(u) { if (u >= 0) return 1.0 / (1.0 + Math.exp(-u)); var e = Math.exp(u); return e / (1.0 + e); }
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
  function bykey(a, b) { return a[0] - b[0]; }
  function pts_(rows, key) { key = key || 'y'; return rows.map(function (r) { return [Number(r.x), Number(r[key])]; }).sort(bykey); }
  function rng(a, b, d) { var n = Math.floor((b - a) / d + 0.5), out = [], i; for (i = 0; i <= n; i++) out.push(a + d * i); return out; }
  function grid(a, b, d) {
    var i0 = Math.ceil(a / d - 1e-9), i1 = Math.floor(b / d + 1e-9), out = [], i;
    for (i = i0; i <= i1; i++) out.push(d * i);
    return out;
  }
  function merge(a, b) {
    var all = a.concat(b).sort(function (x, y) { return x - y; }), out = [], i, v;
    for (i = 0; i < all.length; i++) { v = all[i]; if (!out.length || Math.abs(v - out[out.length - 1]) > 1e-9 * Math.max(1.0, Math.abs(v))) out.push(v); }
    return out;
  }
  function vertex(x0, y0, x1, y1, x2, y2) {
    var d = (x0 - x1) * (x0 - x2) * (x1 - x2), a, b;
    if (d === 0) return x1;
    a = (x2 * (y1 - y0) + x1 * (y0 - y2) + x0 * (y2 - y1)) / d;
    b = (x2 * x2 * (y0 - y1) + x1 * x1 * (y2 - y0) + x0 * x0 * (y1 - y2)) / d;
    if (a === 0) return x1;
    return -b / (2.0 * a);
  }
  function peakx(pts, sign) {
    sign = sign === undefined ? 1.0 : sign;
    if (pts.length < 3) return null;
    var ib = -1, best = -1e300, i, v, a, b, c;
    for (i = 0; i < pts.length; i++) { v = sign * pts[i][1]; if (v > best) { best = v; ib = i; } }
    if (ib <= 0 || ib >= pts.length - 1) return pts[ib][0];
    a = pts[ib - 1]; b = pts[ib]; c = pts[ib + 1];
    return vertex(a[0], a[1], b[0], b[1], c[0], c[1]);
  }
  function zerosDown(pts, frac, gap) {
    var big = 0.0, out = [], i, j, a, b, lo, hi, mx, mn;
    for (i = 0; i < pts.length; i++) if (Math.abs(pts[i][1]) > big) big = Math.abs(pts[i][1]);
    for (i = 0; i < pts.length - 1; i++) {
      a = pts[i]; b = pts[i + 1];
      if (a[1] > 0 && 0 >= b[1] && b[0] - a[0] <= gap) {
        lo = Math.max(0, i - 3); hi = Math.min(pts.length - 1, i + 4); mx = 0.0; mn = 0.0;
        for (j = lo; j <= hi; j++) { if (pts[j][1] > mx) mx = pts[j][1]; if (pts[j][1] < mn) mn = pts[j][1]; }
        if (mx > frac * big && -mn > frac * big) out.push(a[0] + (0.0 - a[1]) * (b[0] - a[0]) / (b[1] - a[1]));
      }
    }
    return out;
  }
  function bisect(f, lo, hi, n) {
    n = n === undefined ? 100 : n;
    var flo = f(lo), i, mid, fm;
    for (i = 0; i < n; i++) { mid = (lo + hi) / 2.0; fm = f(mid); if ((fm > 0) === (flo > 0)) { lo = mid; flo = fm; } else hi = mid; }
    return (lo + hi) / 2.0;
  }
  function typ(p) { return Math.floor(p.typ + 0.5); }
  function sweep(K) {
    K.VARS = ['t', 'x', 'y'];
    K.NST = K.NST || 1;
    if (!K.stages) K.stages = function () { var o = [], s; for (s = 0; s < K.NST; s++) o.push(s); return o; };
    K.plan = function (p) { var out = [], ss = K.stages(p), j, i, xs; for (j = 0; j < ss.length; j++) { xs = K.xs(p, ss[j]); for (i = 0; i < xs.length; i++) out.push([ss[j], xs[i]]); } return out; };
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

  // ================================================================ superconductor R(T)
  var SCRT = sweep({
    PARAMS: { x: 100.0, s: 0.0, Tc0: 92.0, Bc0: 120.0, w: 0.4, Rres: 0.005, a: 5.0e-5, B1: 7.0, R300: 0.02, lo: 15.0, hi: 25.0, dT: 1.0 },
    NST: 3,
    tcb: function (p, B) { var r = 1.0 - B / p.Bc0; return r > 0 ? p.Tc0 * Math.sqrt(r) : 0.0; },
    read: function (p, s, x) {
      if (s === 2) return { y: q_(1000.0 * p.R300, 1e-4) };
      var B = s === 1 ? p.B1 : 0.0;
      var R = (p.Rres + p.a * x) * logi((x - SCRT.tcb(p, B)) / p.w);
      return { y: q_(1000.0 * R, 1e-4) };
    },
    xs: function (p, s) {
      if (s === 2) return [300.0];
      var tc = SCRT.tcb(p, s === 1 ? p.B1 : 0.0);
      var a = grid(tc - p.lo, tc + p.hi, p.dT), b = grid(tc - 5.0 * p.w, tc + 5.0 * p.w, p.w / 4.0);
      return merge(a, b).filter(function (v) { return v > 0.3; });
    },
    tcOf: function (st) {
      var pts = pts_(st), f, rr, i, a, b;
      if (pts.length < 8) return 0.0;
      f = linfit(pts.slice(-5));
      if (!f) return 0.0;
      rr = pts.map(function (q) { return [q[0], q[1] / (f[0] * q[0] + f[1])]; });
      for (i = rr.length - 1; i > 0; i--) { a = rr[i - 1]; b = rr[i]; if (a[1] <= 0.5 && 0.5 < b[1]) return a[0] + (0.5 - a[1]) * (b[0] - a[0]) / (b[1] - a[1]); }
      return 0.0;
    },
    fit: function (rows) { return SCRT.tcOf(stage(rows, 0)); },
  });

  // ================================================================ critical current
  var SCJc = sweep({
    PARAMS: { x: 0.0, s: 0.0, Ic0: 2.0, Tc: 92.0, B0: 1.0, n: 15.0, L: 0.002, Ec: 1.0e-4, area: 2.0e-12, T1: 77.0, T2: 60.0, B1: 0.5 },
    NST: 3,
    ic: function (p, T, B) { var t = T / p.Tc; if (t >= 1) return 0.0; return p.Ic0 * Math.pow(1.0 - t * t, 1.5) / (1.0 + B / p.B0); },
    cond: function (p, s) { if (s === 1) return [p.T2, 0.0]; if (s === 2) return [p.T1, p.B1]; return [p.T1, 0.0]; },
    read: function (p, s, x) {
      var c = SCJc.cond(p, s), ic = SCJc.ic(p, c[0], c[1]);
      var v = (x <= 0 || ic <= 0) ? 0.0 : p.Ec * p.L * Math.pow(x / ic, p.n);
      return { y: q_(1.0e6 * v, 1e-4) };
    },
    xs: function (p, s) { var c = SCJc.cond(p, s), ic = SCJc.ic(p, c[0], c[1]), out = [], i; for (i = 0; i < 13; i++) out.push(ic * (0.6 + 0.05 * i)); return out; },
    icOf: function (st, vc) {
      var pts = pts_(st), i, a, b, la, lb;
      for (i = 0; i < pts.length - 1; i++) {
        a = pts[i]; b = pts[i + 1];
        if (a[1] > 0 && b[1] > 0 && a[1] <= vc && vc < b[1]) {
          la = Math.log(a[1]); lb = Math.log(b[1]);
          return Math.exp(Math.log(a[0]) + (Math.log(vc) - la) * (Math.log(b[0]) - Math.log(a[0])) / (lb - la));
        }
      }
      return 0.0;
    },
    fit: function (rows, p) { return SCJc.icOf(stage(rows, 0), 1.0e6 * p.Ec * p.L) / p.area; },
  });

  // ================================================================ magnetometry
  function cothx(u) { var e = Math.exp(-2.0 * Math.abs(u)), c = (1.0 + e) / (1.0 - e); return u > 0 ? c : -c; }
  var Magnet = sweep({
    PARAMS: { x: 0.0, s: 0.0, typ: 0.0, T0: 2.0, Bm: 5.0, Bf: 0.01, Tlo: 2.0, Thi: 300.0, nmol: 1.0e-5, g: 2.0, J: 3.5,
      N: 1.0e17, Ms: 4.8e5, V: 5.236e-25, K: 1.6e4, tm: 100.0, tau0: 1.0e-9, Bc: 0.02, Bw: 0.05,
      Vs: 1.0e-9, Tc: 9.25, fFC: 0.3, Bp: 0.1, ms0: 0.08, chi: 1.0e-5, mass: 1.0e-6, lcm: 1.0e-8 },
    NST: 4,
    brill: function (J, x) {
      var a = (2.0 * J + 1.0) / (2.0 * J), b = 1.0 / (2.0 * J), a2, b2;
      if (Math.abs(a * x) < 0.05) {
        a2 = a * a; b2 = b * b;
        return (a2 - b2) * x / 3.0 - (a2 * a2 - b2 * b2) * x * x * x / 45.0 + 2.0 * (a2 * a2 * a2 - b2 * b2 * b2) * Math.pow(x, 5) / 945.0;
      }
      return a * cothx(a * x) - b * cothx(b * x);
    },
    lang: function (x) {
      if (Math.abs(x) < 0.05) return x / 3.0 - x * x * x / 45.0 + 2.0 * Math.pow(x, 5) / 945.0;
      var e = Math.exp(-2.0 * Math.abs(x)), c = (1.0 + e) / (1.0 - e);
      return (x > 0 ? c : -c) - 1.0 / x;
    },
    tb: function (p) { return p.K * p.V / (KB * Math.log(p.tm / p.tau0)); },
    mSI: function (p, s, x) {
      var t = typ(p), B, T, mu, tb, ms, sh, tt, f, full, bp, sg, decay, r;
      if (s <= 1) { B = x; T = p.T0; } else { B = p.Bf; T = x; }
      if (t === 0) { mu = p.g * MUB * p.J; return p.nmol * NA * mu * Magnet.brill(p.J, mu * B / (KB * T)); }
      if (t === 1) {
        mu = p.Ms * p.V; tb = Magnet.tb(p);
        if (s <= 1) {
          if (T >= tb) return p.N * mu * Magnet.lang(mu * B / (KB * T));
          ms = p.N * mu; sh = s === 0 ? p.Bc : -p.Bc;
          return ms * Math.tanh((B + sh) / p.Bw);
        }
        if (T >= tb) return p.N * mu * Magnet.lang(mu * B / (KB * T));
        if (s === 2) return p.N * p.Ms * p.Ms * p.V / (3.0 * p.K) * B;
        return p.N * mu * Magnet.lang(mu * B / (KB * tb));
      }
      if (t === 2) {
        tt = T / p.Tc; f = tt < 1 ? 1.0 - tt * tt * tt * tt : 0.0;
        full = -1.5 * p.Vs * B / MU0 * f;
        if (s <= 1) {
          bp = p.Bp * f;
          if (Math.abs(B) <= bp) return full;
          if (bp <= 0) return 0.0;
          sg = B > 0 ? 1.0 : -1.0;
          decay = Math.exp(-(Math.abs(B) - bp) / bp);
          return -1.5 * p.Vs * sg * bp / MU0 * f * decay;
        }
        return s === 2 ? full : p.fFC * full;
      }
      r = 1.0 - T / p.Tc;
      ms = r > 0 ? p.ms0 * Math.sqrt(r) : 0.0;
      if (s === 0) return ms * Math.tanh((B + p.Bc) / p.Bw) + p.chi * B;
      if (s === 1) return ms * Math.tanh((B - p.Bc) / p.Bw) + p.chi * B;
      return ms * Math.tanh(B / p.Bw) + p.chi * B;
    },
    read: function (p, s, x) { return { y: q_(1000.0 * Magnet.mSI(p, s, x), p.lcm) }; },
    stages: function (p) { var t = typ(p); return (t === 3 || t === 4) ? [0, 1, 3] : [0, 1, 2, 3]; },
    xs: function (p, s) {
      var t = typ(p), bm, pts, i, tb, d;
      if (s <= 1) {
        bm = p.Bm; pts = [];
        for (i = 0; i < 21; i++) pts.push(bm * (1.0 - 0.1 * i));
        if (t === 1 || t === 3 || t === 4) pts = merge(pts, [-2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0].map(function (c) { return p.Bc * c; }));
        pts = pts.slice().sort(function (a, b) { return b - a; });
        return s === 0 ? pts : pts.slice().sort(function (a, b) { return a - b; });
      }
      if (t === 0) return merge(rng(2.0, 20.0, 2.0), rng(30.0, 300.0, 30.0));
      if (t === 1) { tb = Magnet.tb(p); return merge(rng(p.Tlo, p.Thi, 10.0), grid(0.8 * tb, 1.3 * tb, 1.0)); }
      if (t === 2) return rng(p.Tlo, 1.5 * p.Tc, p.Tc < 20 ? 0.5 : 4.0);
      d = q_(p.Tc / 80.0, 0.5);
      return merge(rng(300.0, 0.7 * p.Tc, 50.0), grid(0.75 * p.Tc, 1.05 * p.Tc, d));
    },
    fit: function (rows, p) {
      var t = typ(p), pts = [], st, i, x, y, f, c, fc, bgv, top;
      if (t === 0) {
        st = stage(rows, 3);
        for (i = 0; i < st.length; i++) { x = Number(st[i].x); y = Number(st[i].y); if (x >= 20.0 && y > 0) pts.push([x, 1.0 / y]); }
        f = linfit(pts);
        if (!f || f[0] <= 0) return 0.0;
        c = 1.0e-3 / (f[0] * p.Bf);
        return Math.sqrt(3.0 * KB * c / (p.nmol * NA)) / MUB;
      }
      if (t === 1) {
        fc = pts_(stage(rows, 3));
        if (fc.length < 4) return 0.0;
        return fc[fc.length - 1][1] * fc[fc.length - 1][0] / fc[0][1];
      }
      if (t === 2) {
        st = stage(rows, 2);
        for (i = 0; i < st.length; i++) { x = Number(st[i].x); y = Number(st[i].y); if (y < -20.0 * p.lcm) pts.push([x * x * x * x, y]); }
        f = linfit(pts);
        if (!f || f[0] <= 0 || f[1] >= 0) return 0.0;
        return Math.pow(-f[1] / f[0], 0.25);
      }
      if (t === 3) {
        st = stage(rows, 0);
        for (i = 0; i < st.length; i++) { x = Number(st[i].x); y = Number(st[i].y); if (x >= 0.6 * p.Bm) pts.push([x, y]); }
        f = linfit(pts);
        return f ? f[1] * 1.0e-3 / p.mass : 0.0;
      }
      st = pts_(stage(rows, 3));
      if (st.length < 4) return 0.0;
      bgv = st[st.length - 1][1]; top = st[0][1] - bgv;
      for (i = 0; i < st.length; i++) { y = st[i][1] - bgv; if (y > 1e-3 * top) pts.push([st[i][0], y * y]); }
      f = linfit(pts);
      if (!f || f[0] >= 0) return 0.0;
      return -f[1] / f[0];
    },
  });

  // ================================================================ dilution refrigerator
  var Dilution = sweep({
    PARAMS: { x: 0.0, s: 0.0, nd: 1.0e-4, Q0: 1.0e-7, cf: 84.0 },
    read: function (p, s, x) { var T = Math.sqrt((x * 1.0e-6 + p.Q0) / (p.cf * p.nd)); return { y: q_(1000.0 * T, 1e-3) }; },
    xs: function () { return [0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]; },
    fit: function (rows, p) {
      var f = linfit(stage(rows, 0).map(function (r) { return [Number(r.x) * 1.0e-6, Math.pow(Number(r.y) * 1.0e-3, 2)]; }));
      if (!f || f[0] <= 0) return 0.0;
      return 1.0 / (p.cf * f[0]);
    },
  });

  // ================================================================ relaxation calorimetry
  var HCRelax = sweep({
    PARAMS: { x: 4.0, s: 0.0, typ: 0.0, nmol: 1.0e-4, gam: 6.95e-4, ThD: 343.0, Tc: 9.25, a: 9.17, b: 1.5, D: 5.0, fr: 1.0,
      K0: 2.0e-7, P0: 2.0e-9, Tlo: 1.0, Thi: 10.0, dT: 0.5 },
    beta: function (p) { return 12.0 * Math.pow(PI, 4) * RGAS / (5.0 * Math.pow(p.ThD, 3)); },
    cmol: function (p, T) {
      var t = typ(p), lat = HCRelax.beta(p) * T * T * T, u, e;
      if (t === 0) return p.gam * T + lat;
      if (t === 1) { if (T >= p.Tc) return p.gam * T + lat; return p.a * p.gam * p.Tc * Math.exp(-p.b * p.Tc / T) + lat; }
      u = p.D / T; e = Math.exp(-u);
      return lat + p.fr * RGAS * u * u * e / ((1.0 + e) * (1.0 + e));
    },
    read: function (p, s, x) {
      var K = p.K0 * x / 2.0, C = p.nmol * HCRelax.cmol(p, x);
      return { y: q_(C / K, 1e-6), dT: q_(1000.0 * p.P0 / K, 1e-6) };
    },
    xs: function (p) {
      if (typ(p) === 1) return merge(rng(p.Tlo, p.Thi, p.dT), grid(p.Tc + 0.1, p.Tc + 6.0, 0.5));
      return rng(p.Tlo, p.Thi, p.dT);
    },
    cpts: function (rows, p) {
      var out = [], st = stage(rows, 0), i, T, tau, dT;
      for (i = 0; i < st.length; i++) { T = Number(st[i].x); tau = Number(st[i].y); dT = Number(st[i].dT); if (T > 0 && dT > 0) out.push([T, p.P0 / (dT * 1.0e-3) * tau / p.nmol]); }
      return out.sort(bykey);
    },
    schottkyFit: function (pts, lo, hi) {
      function ssr(D) {
        var s11 = 0.0, s12 = 0.0, s22 = 0.0, s1y = 0.0, s2y = 0.0, syy = 0.0, i, T, c, u, e, f1, f2, det, bb, aa;
        for (i = 0; i < pts.length; i++) {
          T = pts[i][0]; c = pts[i][1]; u = D / T; e = Math.exp(-u);
          f1 = T * T * T; f2 = u * u * e / ((1.0 + e) * (1.0 + e));
          s11 += f1 * f1; s12 += f1 * f2; s22 += f2 * f2; s1y += f1 * c; s2y += f2 * c; syy += c * c;
        }
        det = s11 * s22 - s12 * s12;
        if (det === 0) return 1e300;
        bb = (s1y * s22 - s2y * s12) / det; aa = (s2y * s11 - s1y * s12) / det;
        var res = 0.0, r;
        for (i = 0; i < pts.length; i++) {
          u = D / pts[i][0]; e = Math.exp(-u);
          r = pts[i][1] - bb * pts[i][0] * pts[i][0] * pts[i][0] - aa * u * u * e / ((1.0 + e) * (1.0 + e));
          res += r * r;
        }
        return res;
      }
      var g = (Math.sqrt(5.0) - 1.0) / 2.0, a = lo, b = hi, c = b - g * (b - a), d = a + g * (b - a), fc = ssr(c), fd = ssr(d), i;
      for (i = 0; i < 50; i++) {
        if (fc < fd) { b = d; d = c; fd = fc; c = b - g * (b - a); fc = ssr(c); }
        else { a = c; c = d; fc = fd; d = a + g * (b - a); fd = ssr(d); }
      }
      return (a + b) / 2.0;
    },
    fit: function (rows, p) {
      var t = typ(p), pts = HCRelax.cpts(rows, p), top, ln, f;
      if (pts.length < 4) return 0.0;
      if (t === 2) return HCRelax.schottkyFit(pts, 0.2, 40.0);
      if (t === 1) {
        top = pts[pts.length - 1][0];
        ln = pts.filter(function (q) { return q[0] >= top - 5.0; }).map(function (q) { return [q[0] * q[0], q[1] / q[0]]; });
        f = linfit(ln);
        return f ? f[1] : 0.0;
      }
      f = linfit(pts.map(function (q) { return [q[0] * q[0], q[1] / q[0]]; }));
      if (!f || f[0] <= 0) return 0.0;
      return Math.pow(12.0 * Math.pow(PI, 4) * RGAS / (5.0 * f[0]), 1.0 / 3.0);
    },
  });

  // ================================================================ thermal conductivity
  var KappaLT = sweep({
    PARAMS: { x: 2.0, s: 0.0, typ: 0.0, rho0: 1.0e-10, bet: 2.0e-5, c1: 0.06, c2: 1.1, ell: 1.0e-3, vs: 6.0e3, U: 1.0e-6,
      ThD: 1000.0, L: 0.02, A: 3.0e-6, P: 1.0e-6, Tlo: 1.0, Thi: 20.0, dT: 1.0 },
    kap: function (p, T) {
      var t = typ(p), ab;
      if (t === 0) return 1.0 / (p.rho0 / L0 / T + p.bet * T * T);
      if (t === 1) return p.c1 * Math.pow(T, p.c2);
      ab = 2.0 * PI * PI * Math.pow(KB, 4) * p.ell / (15.0 * Math.pow(HBAR, 3) * p.vs * p.vs);
      return 1.0 / (1.0 / (ab * T * T * T) + p.U * T * T * T * Math.exp(-p.ThD / (3.0 * T)));
    },
    heat: function (p, a, b) {
      var n = 64, h = (b - a) / n, s = KappaLT.kap(p, a) + KappaLT.kap(p, b), i;
      for (i = 1; i < n; i++) s += (i % 2 === 1 ? 4.0 : 2.0) * KappaLT.kap(p, a + i * h);
      return s * h / 3.0 * p.A / p.L;
    },
    read: function (p, s, x) {
      var k0 = KappaLT.kap(p, x), hi = x + 50.0 * p.P * p.L / (p.A * k0) + 1e-6;
      var th = bisect(function (T) { return KappaLT.heat(p, x, T) - p.P; }, x, hi, 80);
      return { y: q_(1000.0 * (th - x), 1e-5) };
    },
    xs: function (p) { return rng(p.Tlo, p.Thi, p.dT); },
    kpts: function (rows, p) {
      var out = [], st = stage(rows, 0), i, T, d;
      for (i = 0; i < st.length; i++) { T = Number(st[i].x); d = Number(st[i].y) * 1.0e-3; if (d > 0) out.push([T + d / 2.0, p.P * p.L / (p.A * d)]); }
      return out.sort(bykey);
    },
    fit: function (rows, p) {
      var t = typ(p), pts = KappaLT.kpts(rows, p), f, low, tot = 0.0, i, ab;
      if (pts.length < 4) return 0.0;
      if (t === 0) { f = linfit(pts.map(function (q) { return [q[0] * q[0] * q[0], q[0] / q[1]]; })); return f ? f[1] * L0 : 0.0; }
      if (t === 1) { f = linfit(pts.map(function (q) { return [Math.log(q[0]), Math.log(q[1])]; })); return f ? Math.exp(f[1] + f[0] * Math.log(4.2)) : 0.0; }
      low = pts.filter(function (q) { return q[0] <= 3.0; });
      if (!low.length) return 0.0;
      for (i = 0; i < low.length; i++) tot += low[i][1] / (low[i][0] * low[i][0] * low[i][0]);
      ab = tot / low.length;
      return ab * 15.0 * Math.pow(HBAR, 3) * p.vs * p.vs / (2.0 * PI * PI * Math.pow(KB, 4));
    },
  });

  // ================================================================ quantum Hall effect
  var QHall = sweep({
    PARAMS: { x: 0.0, s: 0.0, n: 3.0e15, gr: 0.0, mu: 100.0, G0: 0.12, gT: 0.02, LW: 3.0, T1: 1.5, T2: 0.3, Bmax: 9.0, dB: 0.1 },
    NST: 2,
    sig: function (p, B, T) {
      var nu = p.n * H / (QE * B), G = p.G0 / B + p.gT * T / B, s = 0.0, bump = 0.0, kmax, k, u, c, g4;
      if (p.gr < 0.5) {
        kmax = Math.floor(nu + 12.0 * G + 6.0);
        for (k = 1; k <= kmax; k++) { u = (nu - k + 0.5) / G; s += logi(u); if (Math.abs(u) < 60) { c = Math.cosh(u / 2.0); bump += 1.0 / (c * c); } }
        return [s, bump / (4.0 * G)];
      }
      g4 = 4.0 * G;
      kmax = Math.floor(nu / 4.0 + 12.0 * G + 6.0);
      s = 2.0 * logi(nu / g4);
      for (k = 1; k <= kmax; k++) { u = (nu - 4.0 * k) / g4; s += 4.0 * logi(u); if (Math.abs(u) < 60) { c = Math.cosh(u / 2.0); bump += 1.0 / (c * c); } }
      return [s, bump / (4.0 * G)];
    },
    read: function (p, s, x) {
      var T = s === 1 ? p.T2 : p.T1, rho0 = 1.0 / (p.n * QE * p.mu), sg;
      if (x <= 0) return { y: 0.0, y2: q_(rho0 * p.LW, 1e-3) };
      sg = QHall.sig(p, x, T);
      return { y: q_(RK / sg[0], 1e-3), y2: q_(rho0 * p.LW * sg[1], 1e-3) };
    },
    xs: function (p, s) { return rng(0.0, p.Bmax, s === 1 ? p.dB : 2.0 * p.dB); },
    fit: function (rows, p) {
      var st = stage(rows, 1), lo = [], i, x, f, n, pts, ref, tot = 0.0, cnt = 0, run = [], q, b, nu, inu, all;
      for (i = 0; i < st.length; i++) { x = Number(st[i].x); if (x > 0 && x <= 0.5) lo.push([x, Number(st[i].y)]); }
      f = linfit(lo);
      if (!f || f[0] <= 0) return 0.0;
      n = 1.0 / (QE * f[0]);
      pts = st.map(function (r) { return [Number(r.x), Number(r.y), Number(r.y2)]; }).sort(bykey);
      if (!pts.length || pts[0][0] > 0) return 0.0;
      ref = pts[0][2];
      all = pts.concat([[1e9, 0.0, 1e300]]);
      for (i = 0; i < all.length; i++) {
        q = all[i];
        if (q[0] > 1.0 && q[2] <= 1e-4 * ref) { run.push(q); continue; }
        if (run.length) {
          b = run[Math.floor(run.length / 2)];
          nu = n * H / (QE * b[0]);
          inu = p.gr < 0.5 ? Math.floor(nu + 0.5) : 4.0 * Math.floor((nu - 2.0) / 4.0 + 0.5) + 2.0;
          if (inu >= 1) { tot += inu * b[1]; cnt += 1; }
          run = [];
        }
      }
      return cnt ? tot / cnt : 0.0;
    },
  });

  // ================================================================ Shubnikov-de Haas
  var SdH = sweep({
    PARAMS: { x: 1.0, s: 0.0, typ: 0.0, n: 3.0e15, F: 6.3, ms: 0.067, tq: 1.0e-12, rho0: 10.0, T1: 1.5, Bf: 2.0, Bhi: 4.0, nper: 9.0 },
    NST: 2,
    freq: function (p) { var t = typ(p); if (t === 0) return p.n * H / (2.0 * QE); if (t === 1) return p.n * H / (4.0 * QE); return p.F; },
    amp: function (p, B, T) {
      var m = p.ms * ME, X = 2.0 * PI * PI * KB * T * m / (HBAR * QE * B), rt = X > 1e-6 ? X / Math.sinh(X) : 1.0, wc = QE * B / m;
      return 4.0 * p.rho0 * rt * Math.exp(-PI / (wc * p.tq));
    },
    read: function (p, s, x) {
      if (s === 1) return { y: q_(SdH.amp(p, p.Bf, x), 1e-5) };
      if (x <= 0) return { y: q_(p.rho0, 1e-5) };
      var F = SdH.freq(p);
      return { y: q_(p.rho0 + SdH.amp(p, x, p.T1) * Math.cos(2.0 * PI * F / x - PI), 1e-5) };
    },
    xs: function (p, s) {
      if (s === 1) return [0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0];
      var F = SdH.freq(p), u0 = 1.0 / p.Bhi, n = Math.floor(12.0 * p.nper + 0.5), out = [], i;
      for (i = 0; i <= n; i++) out.push(1.0 / (u0 + (n - i) / (12.0 * F)));
      return out;
    },
    ratio: function (p, m, T, T0) {
      function rt(t) { var X = 2.0 * PI * PI * KB * t * m * ME / (HBAR * QE * p.Bf); return X > 1e-6 ? X / Math.sinh(X) : 1.0; }
      return rt(T) / rt(T0);
    },
    massOf: function (rows, p) {
      var pts = pts_(stage(rows, 1)), T0, A0, tot = 0.0, n = 0, i, want, m;
      if (pts.length < 3 || pts[0][1] <= 0) return 0.0;
      T0 = pts[0][0]; A0 = pts[0][1];
      for (i = 1; i < pts.length; i++) {
        if (pts[i][1] <= 0) continue;
        want = pts[i][1] / A0;
        m = bisect((function (T) { return function (mm) { return SdH.ratio(p, mm, T, T0) - want; }; })(pts[i][0]), 1e-4, 3.0, 80);
        tot += m; n += 1;
      }
      return n ? tot / n : 0.0;
    },
    freqOf: function (rows, p) {
      var st = stage(rows, 0), pts = [], i, a, b, c, mx = [], f, xy = [];
      for (i = 0; i < st.length; i++) if (Number(st[i].x) > 0) pts.push([1.0 / Number(st[i].x), Number(st[i].y)]);
      pts.sort(bykey);
      for (i = 1; i < pts.length - 1; i++) {
        a = pts[i - 1]; b = pts[i]; c = pts[i + 1];
        if (b[1] > a[1] && b[1] >= c[1] && b[1] > p.rho0) mx.push(vertex(a[0], a[1], b[0], b[1], c[0], c[1]));
      }
      if (mx.length < 3) return 0.0;
      for (i = 0; i < mx.length; i++) xy.push([i, mx[i]]);
      f = linfit(xy);
      if (!f || f[0] === 0) return 0.0;
      return 1.0 / Math.abs(f[0]);
    },
    fit: function (rows, p) {
      var t = typ(p);
      if (t === 2) return SdH.massOf(rows, p);
      return SdH.freqOf(rows, p) * (t === 0 ? 2.0 : 4.0) * QE / H;
    },
  });

  // ================================================================ Hall bar + van der Pauw
  var HallMob = sweep({
    PARAMS: { x: 0.0, s: 0.0, ns: 3.0e18, muL: 0.14, al: 2.4, muI: 0.6, I: 1.0e-4, LW: 3.0, B1: 0.5, sgn: -1.0 },
    NST: 3,
    mu: function (p, T) { var t = T / 300.0; return 1.0 / (1.0 / (p.muL * Math.pow(t, -p.al)) + 1.0 / (p.muI * Math.pow(t, 1.5))); },
    read: function (p, s, x) {
      var rs, T, B;
      if (s === 1) { rs = 1.0 / (QE * p.ns * HallMob.mu(p, 300.0)); return { y: q_(rs * Math.log(2.0) / PI, 1e-4) }; }
      T = s === 2 ? x : 300.0; B = s === 2 ? p.B1 : x;
      rs = 1.0 / (QE * p.ns * HallMob.mu(p, T));
      return { y: q_(1.0e6 * p.sgn * p.I * B / (QE * p.ns), 1e-4), y2: q_(1.0e3 * p.I * rs * p.LW, 1e-5) };
    },
    xs: function (p, s) { if (s === 1) return [0.0, 1.0]; if (s === 2) return [20.0, 30.0, 50.0, 77.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0]; return rng(-1.0, 1.0, 0.25); },
    vdp: function (ra, rb) { return bisect(function (rs) { return Math.exp(-PI * ra / rs) + Math.exp(-PI * rb / rs) - 1.0; }, 0.1 * (ra + rb), 20.0 * (ra + rb), 100); },
    fit: function (rows, p) {
      var f = linfit(stage(rows, 0).map(function (r) { return [Number(r.x), Number(r.y) * 1.0e-6]; })), ns, r = [null, null], st, i, j;
      if (!f || f[0] === 0) return 0.0;
      ns = p.I / (QE * Math.abs(f[0]));
      st = stage(rows, 1);
      for (j = 0; j < st.length; j++) { i = Math.floor(Number(st[j].x) + 0.5); if (i === 0 || i === 1) r[i] = Number(st[j].y); }
      if (r[0] === null || r[1] === null) return 0.0;
      return 1.0 / (QE * ns * HallMob.vdp(r[0], r[1]));
    },
  });

  // ================================================================ Seebeck coefficient
  var Seebeck = sweep({
    PARAMS: { x: 0.0, s: 0.0, S: 2.0e-4, SCu: 1.83e-6, Voff: 3.2, rho: 1.0e-5, Ls: 0.005, As: 4.0e-6, dT0: 1.0 },
    NST: 3,
    read: function (p, s, x) {
      if (s === 2) return { y: q_(1.0e6 * x * 1.0e-3 * p.rho * p.Ls / p.As, 1e-3) };
      return { y: q_(p.Voff + 1.0e6 * (p.S - p.SCu) * x, 1e-3) };
    },
    xs: function (p, s) { if (s === 0) return [-p.dT0, p.dT0]; if (s === 1) return rng(-2.0, 2.0, 0.5); return [10.0, 20.0, 30.0, 40.0, 50.0]; },
    fit: function (rows, p) {
      var v = [null, null], st = stage(rows, 0), i, x;
      for (i = 0; i < st.length; i++) { x = Number(st[i].x); if (x < 0) v[0] = [x, Number(st[i].y)]; else if (x > 0) v[1] = [x, Number(st[i].y)]; }
      if (v[0] === null || v[1] === null) return 0.0;
      return (v[1][1] - v[0][1]) / (v[1][0] - v[0][0]) * 1.0e-6 + p.SCu;
    },
  });

  // ================================================================ DLTS
  var DLTS = sweep({
    PARAMS: { x: 200.0, s: 0.0, Ea: 0.55, sig: 1.0e-19, gam: 1.07e25, NT: 1.0e19, ND: 1.0e21, C0: 100.0, tw: 1.0e-3 },
    NST: 4,
    WIN: [1.0, 2.0, 5.0, 10.0],
    rate: function (p, T) { return p.sig * p.gam * T * T * Math.exp(-p.Ea * QE / (KB * T)); },
    t1: function (p, s) { return p.tw * DLTS.WIN[s]; },
    read: function (p, s, x) {
      var e = DLTS.rate(p, x), t1 = DLTS.t1(p, s), dc0 = 1000.0 * p.C0 * p.NT / (2.0 * p.ND);
      return { y: q_(dc0 * (Math.exp(-e * t1) - Math.exp(-e * 2.0 * t1)), 1e-4) };
    },
    tpeak: function (p, s) { var want = Math.log(2.0) / DLTS.t1(p, s); return bisect(function (T) { return DLTS.rate(p, T) - want; }, 20.0, 800.0, 80); },
    xs: function (p, s) { var tp = DLTS.tpeak(p, s); return grid(tp - 6.0, tp + 6.0, 0.5); },
    arr: function (rows, p) {
      var out = [], s, pk;
      for (s = 0; s < 4; s++) { pk = peakx(pts_(stage(rows, s))); if (pk) out.push([1.0 / pk, Math.log(Math.log(2.0) / DLTS.t1(p, s) / (pk * pk))]); }
      return out;
    },
    fit: function (rows, p) { var f = linfit(DLTS.arr(rows, p)); if (!f || f[0] >= 0) return 0.0; return -f[0] * KB / QE; },
  });

  // ================================================================ C-V profiling
  var CVProf = sweep({
    PARAMS: { x: 0.0, s: 0.0, typ: 0.0, ND: 1.0e22, NA: 1.0e25, Vbi: 0.6, A: 1.0e-6, er: 11.7, T: 300.0, ni: 1.0e16, tox: 1.0e-8,
      erox: 3.9, phims: -0.9, Qox: 5.0e-4, Vlo: -4.0, Vhi: 0.2 },
    vbi: function (p) { if (typ(p) === 1) return KB * p.T / QE * Math.log(p.NA * p.ND / (p.ni * p.ni)); return p.Vbi; },
    cox: function (p) { return p.erox * EPS0 * p.A / p.tox; },
    vfb: function (p) { return p.phims - p.Qox / (p.erox * EPS0 / p.tox); },
    cap: function (p, V) {
      var eps = p.er * EPS0, arg, cox, vfb, inv, c, phif, wmax, cmin;
      if (typ(p) < 2) {
        arg = CVProf.vbi(p) - V - KB * p.T / QE;
        if (arg <= 0) arg = 1e-6;
        return Math.sqrt(QE * eps * p.ND * p.A * p.A / (2.0 * arg));
      }
      cox = CVProf.cox(p); vfb = CVProf.vfb(p);
      if (V <= vfb) return cox;
      inv = 1.0 / (cox * cox) + 2.0 * (V - vfb) / (QE * eps * p.NA * p.A * p.A);
      c = 1.0 / Math.sqrt(inv);
      phif = KB * p.T / QE * Math.log(p.NA / p.ni);
      wmax = Math.sqrt(4.0 * eps * phif / (QE * p.NA));
      cmin = 1.0 / (1.0 / cox + wmax / (eps * p.A));
      return c > cmin ? c : cmin;
    },
    read: function (p, s, x) { return { y: q_(1.0e12 * CVProf.cap(p, x), 1e-4) }; },
    xs: function (p) { if (typ(p) === 2) { var v0 = CVProf.vfb(p); return rng(v0 - 2.0, v0 + 3.0, 0.1); } return rng(p.Vlo, p.Vhi, 0.2); },
    fit: function (rows, p) {
      var t = typ(p), eps = p.er * EPS0, pts = pts_(stage(rows, 0)), f, cmax, cmin, i, dep;
      if (pts.length < 4) return 0.0;
      if (t < 2) {
        f = linfit(pts.map(function (q) { return [q[0], 1.0 / Math.pow(q[1] * 1.0e-12, 2)]; }));
        if (!f || f[0] >= 0) return 0.0;
        if (t === 0) return -2.0 / (QE * eps * p.A * p.A * f[0]);
        return -f[1] / f[0] + KB * p.T / QE;
      }
      cmax = pts[0][1]; cmin = pts[0][1];
      for (i = 0; i < pts.length; i++) { cmax = Math.max(cmax, pts[i][1]); cmin = Math.min(cmin, pts[i][1]); }
      dep = pts.filter(function (q) { return 1.02 * cmin < q[1] && q[1] < 0.98 * cmax; }).map(function (q) { return [q[0], 1.0 / Math.pow(q[1] * 1.0e-12, 2)]; });
      f = linfit(dep);
      if (!f || f[0] <= 0) return 0.0;
      return (1.0 / Math.pow(cmax * 1.0e-12, 2) - f[1]) / f[0];
    },
  });

  // ================================================================ Haynes-Shockley
  var HaynesShockley = sweep({
    PARAMS: { x: 5.0, s: 0.0, mu: 0.19, T: 300.0, tau: 5.0e-5, E0: 4000.0, d0: 0.005, sc: 100.0 },
    NST: 2,
    prof: function (p, d, E, t) {
      var v = p.mu * E, D = p.mu * KB * p.T / QE;
      return Math.exp(-Math.pow(d - v * t, 2) / (4.0 * D * t) - t / p.tau) / Math.sqrt(t);
    },
    peak: function (p, d, E) {
      var v = p.mu * E, D = p.mu * KB * p.T / QE, a = v * v + 4.0 * D / p.tau;
      return (-D + Math.sqrt(D * D + d * d * a)) / a;
    },
    fwhm: function (p, d, E, t0) {
      var top = HaynesShockley.prof(p, d, E, t0);
      var lo = bisect(function (t) { return HaynesShockley.prof(p, d, E, t) - top / 2.0; }, t0 * 0.2, t0, 80);
      var hi = bisect(function (t) { return HaynesShockley.prof(p, d, E, t) - top / 2.0; }, t0, t0 * 5.0, 80);
      return hi - lo;
    },
    read: function (p, s, x) {
      var d = s === 0 ? x * 1.0e-3 : p.d0, E = s === 0 ? p.E0 : x * 100.0, t0 = HaynesShockley.peak(p, d, E);
      return { y: q_(1.0e6 * t0, 1e-4), y2: q_(1.0e6 * HaynesShockley.fwhm(p, d, E, t0), 1e-4),
        y3: q_(p.sc * Math.sqrt(1.0e-6) * HaynesShockley.prof(p, d, E, t0), 1e-4) };
    },
    xs: function (p, s) { return s === 0 ? [3.0, 4.0, 5.0, 6.0, 7.0, 8.0] : [10.0, 15.0, 20.0, 25.0, 30.0]; },
    fit: function (rows, p) {
      var f = linfit(stage(rows, 0).map(function (r) { return [Number(r.x) * 1.0e-3, Number(r.y) * 1.0e-6]; }));
      if (!f || f[0] <= 0) return 0.0;
      return 1.0 / (f[0] * p.E0);
    },
  });

  // ================================================================ solar cell EQE + dark I-V
  var SolarEQE = sweep({
    PARAMS: { x: 500.0, s: 0.0, Eg: 1.12, a0: 1.0e6, pw: 2.0, W: 1.8e-4, R: 0.05, eta: 0.95, nid: 1.3, I0: 1.0e-10, Rs: 0.1,
      Rsh: 1.0e8, T: 300.0, l0: 350.0, l1: 1200.0, Va: 0.05, Vb: 0.6 },
    NST: 2,
    eqe: function (p, lam) {
      var E, a;
      if (lam <= 0) return 0.0;
      E = 1239.84198 / lam;
      if (E <= p.Eg) return 0.0;
      a = p.a0 * Math.pow(E - p.Eg, p.pw);
      return p.eta * (1.0 - p.R) * (1.0 - Math.exp(-a * p.W));
    },
    cur: function (p, V) {
      var vt = p.nid * KB * p.T / QE;
      function g(I) { var vj = V - I * p.Rs; return p.I0 * (Math.exp(vj / vt) - 1.0) + vj / p.Rsh - I; }
      return bisect(g, 0.0, V > 0 ? V / p.Rs : 1e-9, 120);
    },
    read: function (p, s, x) { if (s === 0) return { y: q_(100.0 * SolarEQE.eqe(p, x), 1e-3) }; return { y: q_(1000.0 * SolarEQE.cur(p, x), 1e-7) }; },
    xs: function (p, s) { return s === 0 ? rng(p.l0, p.l1, 25.0) : rng(p.Va, p.Vb, 0.025); },
    fit: function (rows, p) {
      var pts = [], st = stage(rows, 1), i, I, f;
      for (i = 0; i < st.length; i++) { I = Number(st[i].y) * 1.0e-3; if (1.0e-6 <= I && I <= 1.0e-4) pts.push([Number(st[i].x), Math.log(I)]); }
      f = linfit(pts);
      if (!f || f[0] <= 0) return 0.0;
      return QE / (KB * p.T * f[0]);
    },
  });

  // ================================================================ Moessbauer
  var Moss = sweep({
    PARAMS: { x: 0.0, s: 0.0, typ: 0.0, B: 33.0, dIS: 0.0, eps: 0.0, QS: 0.0, G: 0.25, dep: 0.06, N0: 1.0e6, vmax: 10.0 },
    NST: 2,
    kv: function () { return MUN * C0 / EGAM * 1000.0; },
    lines: function (p) {
      var t = typ(p), ge, gg, out = [], trans, i, tr, v;
      if (t === 1) return [[p.dIS, 1.0]];
      if (t === 2) return [[p.dIS - p.QS / 2.0, 1.0], [p.dIS + p.QS / 2.0, 1.0]];
      ge = MU_E / 1.5; gg = MU_G / 0.5;
      trans = [[-1.5, -0.5, 3.0, 1.0], [-0.5, -0.5, 2.0, -1.0], [0.5, -0.5, 1.0, -1.0], [-0.5, 0.5, 1.0, -1.0], [0.5, 0.5, 2.0, -1.0], [1.5, 0.5, 3.0, 1.0]];
      for (i = 0; i < trans.length; i++) { tr = trans[i]; v = -(ge * tr[0] - gg * tr[1]) * p.B * Moss.kv(); out.push([p.dIS + v + tr[3] * p.eps, tr[2] / 3.0]); }
      return out.sort(bykey);
    },
    read: function (p, s, x) {
      var a = 0.0, hw = p.G / 2.0, ls = Moss.lines(p), i, u;
      for (i = 0; i < ls.length; i++) { u = (x - ls[i][0]) / hw; a += p.dep * ls[i][1] / (1.0 + u * u); }
      return { y: q_(p.N0 * (1.0 - a), 1.0) };
    },
    xs: function (p, s) {
      var out = [], st = p.G / 6.0, ls, i, vm;
      if (s === 0) { vm = typ(p) === 0 ? p.vmax : 4.0; return rng(-vm, vm, 0.25); }
      ls = Moss.lines(p);
      for (i = 0; i < ls.length; i++) out = merge(out, grid(ls[i][0] - p.G, ls[i][0] + p.G, st));
      return out;
    },
    centres: function (rows, p) {
      var pts = pts_(stage(rows, 1)), groups = [], cur = [], out = [], i, j, g, ib, ys;
      for (i = 0; i < pts.length; i++) {
        if (cur.length && pts[i][0] - cur[cur.length - 1][0] > p.G / 3.0) { groups.push(cur); cur = []; }
        cur.push(pts[i]);
      }
      if (cur.length) groups.push(cur);
      for (j = 0; j < groups.length; j++) {
        g = groups[j];
        if (g.length < 3) continue;
        ib = 0;
        for (i = 0; i < g.length; i++) if (g[i][1] < g[ib][1]) ib = i;
        if (ib === 0 || ib === g.length - 1) continue;
        ys = [g[ib - 1], g[ib], g[ib + 1]].map(function (q) { return 1.0 / Math.max(p.N0 - q[1], 1.0); });
        out.push(vertex(g[ib - 1][0], ys[0], g[ib][0], ys[1], g[ib + 1][0], ys[2]));
      }
      return out;
    },
    fit: function (rows, p) {
      var t = typ(p), c = Moss.centres(rows, p), k;
      if (t === 1) return c.length === 1 ? c[0] : 0.0;
      if (t === 2) return c.length === 2 ? c[1] - c[0] : 0.0;
      if (c.length !== 6) return 0.0;
      k = (-MU_E + MU_G) * Moss.kv();
      return (c[5] - c[0]) / (2.0 * k);
    },
  });

  // ================================================================ FMR
  var FMR = sweep({
    PARAMS: { x: 0.1, s: 0.0, typ: 0.0, g: 2.0, Ms: 0.0, alpha: 1.0e-4, dB0: 5.0e-5 },
    NST: 4,
    FR: [4.0e9, 8.0e9, 12.0e9, 16.0e9],
    gp: function (p) { return p.g * MUB / H; },
    br: function (p, f) { var b = f / FMR.gp(p), m; if (typ(p) === 0) return b; m = p.Ms; return (-m + Math.sqrt(m * m + 4.0 * b * b)) / 2.0; },
    dbpp: function (p, f) { return p.dB0 + 2.0 / Math.sqrt(3.0) * p.alpha * f / FMR.gp(p); },
    read: function (p, s, x) {
      var f = FMR.FR[s], u = (x - FMR.br(p, f)) / (Math.sqrt(3.0) / 2.0 * FMR.dbpp(p, f));
      return { y: q_(-1000.0 * 2.0 * u / Math.pow(1.0 + u * u, 2), 1e-3) };
    },
    xs: function (p, s) { var f = FMR.FR[s], b = FMR.br(p, f), w = FMR.dbpp(p, f), out = [], i; for (i = 0; i < 21; i++) out.push(b + w * (-2.0 + 0.2 * i)); return out; },
    res: function (rows) {
      var out = [], s, pts, z;
      for (s = 0; s < 4; s++) { pts = pts_(stage(rows, s)); if (pts.length < 5) continue; z = zerosDown(pts, 0.3, 1.0); if (z.length) out.push([FMR.FR[s], z[0]]); }
      return out;
    },
    fit: function (rows, p) {
      var r = FMR.res(rows, p), f;
      if (r.length < 3) return 0.0;
      if (typ(p) === 0) { f = linfit(r.map(function (q) { return [q[1], q[0]]; })); return f ? f[0] * H / MUB : 0.0; }
      f = linfit(r.map(function (q) { return [q[1], q[0] * q[0] / q[1]]; }));
      if (!f || f[0] <= 0) return 0.0;
      return f[1] / f[0];
    },
  });

  // ================================================================ ESR
  var ESR = sweep({
    PARAMS: { x: 330.0, s: 0.0, typ: 0.0, g: 2.0036, A: 0.0, I: 0.0, f: 9.5e9, dBpp: 0.15 },
    b0: function (p) { return H * p.f / (p.g * MUB) * 1000.0; },
    lines: function (p) {
      var b0 = ESR.b0(p), out = [], n = Math.floor(2.0 * p.I + 0.5), i, m;
      for (i = 0; i <= n; i++) { m = -p.I + i; out.push(b0 - p.A * m - p.A * p.A / (2.0 * b0) * (p.I * (p.I + 1.0) - m * m)); }
      return out.sort(function (a, b) { return a - b; });
    },
    read: function (p, s, x) {
      var hw = Math.sqrt(3.0) / 2.0 * p.dBpp, v = 0.0, ls = ESR.lines(p), i, u;
      for (i = 0; i < ls.length; i++) { u = (x - ls[i]) / hw; v += -2.0 * u / Math.pow(1.0 + u * u, 2); }
      return { y: q_(1000.0 * v, 1e-3) };
    },
    xs: function (p) {
      var out = [], w = p.dBpp, ls = ESR.lines(p), i, j, a;
      for (i = 0; i < ls.length; i++) { a = []; for (j = 0; j < 17; j++) a.push(ls[i] + w * (-2.0 + 0.25 * j)); out = merge(out, a); }
      return out;
    },
    fit: function (rows, p) {
      var z = zerosDown(pts_(stage(rows, 0)), 0.2, 0.5 * p.dBpp), t = typ(p), n;
      if (t === 0) { if (z.length !== 1) return 0.0; return H * p.f / (MUB * z[0] * 1.0e-3); }
      n = Math.floor(2.0 * p.I + 0.5) + 1;
      if (z.length !== n || n < 2) return 0.0;
      return (z[z.length - 1] - z[0]) / (n - 1);
    },
  });

  // ================================================================ positron annihilation
  var Positron = sweep({
    PARAMS: { x: 0.0, s: 0.0, typ: 0.0, t1: 0.165, t2: 0.4, t3: 2.5, i2: 0.0, i3: 0.0, sg: 0.106, tz: 2.0, Nt: 1.0e9, dt: 0.025,
      bg: 20.0, thF: 6.8, cw: 9.0, cf: 0.15, pw: 0.6, pf: 0.15, Na: 1.0e5 },
    NST: 2,
    emg: function (t, tau, sg) {
      var u = t / tau, z = (sg / tau - t / sg) / Math.sqrt(2.0);
      return 0.5 / tau * Math.exp(sg * sg / (2.0 * tau * tau) - u) * erfc(z);
    },
    read: function (p, s, x) {
      var th, par, v, t, i1, f;
      if (s === 1) {
        th = x;
        if (typ(p) === 0) {
          par = Math.abs(th) < p.thF ? (p.thF * p.thF - th * th) / (p.thF * p.thF) : 0.0;
          v = p.Na * ((1.0 - p.cf) * par + p.cf * Math.exp(-th * th / (2.0 * p.cw * p.cw)));
        } else {
          v = p.Na * (p.pf * Math.exp(-th * th / (2.0 * p.pw * p.pw)) + (1.0 - p.pf) * Math.exp(-th * th / (2.0 * p.cw * p.cw)));
        }
        return { y: q_(v, 1.0) };
      }
      t = x - p.tz; i1 = 1.0 - p.i2 - p.i3;
      f = i1 * Positron.emg(t, p.t1, p.sg);
      if (p.i2 > 0) f += p.i2 * Positron.emg(t, p.t2, p.sg);
      if (p.i3 > 0) f += p.i3 * Positron.emg(t, p.t3, p.sg);
      return { y: q_(p.Nt * p.dt * f + p.bg, 1.0) };
    },
    xs: function (p, s) {
      if (s === 1) return rng(-15.0, 15.0, 1.0);
      if (typ(p) === 0) return merge(rng(0.0, 1.5, 0.25), rng(1.5, 5.0, 0.05));
      return merge(rng(0.0, 1.5, 0.25), merge(rng(1.5, 4.0, 0.1), rng(4.0, 20.0, 0.5)));
    },
    fit: function (rows, p) {
      var pts = pts_(stage(rows, 0)), bg, ib = 0, i, tp, lo, hi, ln = [], f;
      if (pts.length < 10) return 0.0;
      bg = pts[0][1];
      for (i = 0; i < pts.length; i++) if (pts[i][1] > pts[ib][1]) ib = i;
      tp = pts[ib][0];
      if (typ(p) === 0) { lo = tp + 0.6; hi = tp + 2.6; } else { lo = tp + 6.0; hi = tp + 16.0; }
      for (i = 0; i < pts.length; i++) if (lo <= pts[i][0] && pts[i][0] <= hi && pts[i][1] - bg > 200.0) ln.push([pts[i][0], Math.log(pts[i][1] - bg)]);
      f = linfit(ln);
      if (!f || f[0] >= 0) return 0.0;
      return -1.0 / f[0];
    },
  });

  // ================================================================ MOKE
  var MOKE = sweep({
    PARAMS: { x: 0.0, s: 0.0, typ: 0.0, Bc: 2.0, Bw: 0.5, thK: 0.25, phE: 30.0, thP: 2.0, Bs: 1700.0, Bmax: 10.0 },
    NST: 4,
    read: function (p, s, x) {
      var v, a, r;
      if (s === 0) v = p.thK * Math.tanh((x + p.Bc) / p.Bw);
      else if (s === 1) v = p.thK * Math.tanh((x - p.Bc) / p.Bw);
      else if (s === 2) {
        a = (x - p.phE) * PI / 180.0;
        v = typ(p) === 2 ? p.thK * Math.max(Math.abs(Math.cos(a)), Math.abs(Math.sin(a))) : p.thK * Math.abs(Math.cos(a));
      } else { r = x / p.Bs; if (r > 1) r = 1.0; if (r < -1) r = -1.0; v = p.thP * r; }
      return { y: q_(v, 1e-5) };
    },
    xs: function (p, s) {
      var a, c, b, pts;
      if (s === 2) return rng(0.0, 180.0, 10.0);
      if (s === 3) return rng(-2.0 * p.Bs, 2.0 * p.Bs, 0.25 * p.Bs);
      a = rng(-p.Bmax, p.Bmax, p.Bmax / 5.0);
      c = s === 0 ? -p.Bc : p.Bc;
      b = grid(c - 2.0 * p.Bw, c + 2.0 * p.Bw, p.Bw / 4.0);
      pts = merge(a, b);
      return s === 0 ? pts.slice().sort(function (x, y) { return y - x; }) : pts;
    },
    zero: function (st) {
      var pts = pts_(st), i, a, b;
      for (i = 0; i < pts.length - 1; i++) { a = pts[i]; b = pts[i + 1]; if (a[1] < 0 && 0 <= b[1] && b[1] !== a[1]) return a[0] - a[1] * (b[0] - a[0]) / (b[1] - a[1]); }
      return null;
    },
    fit: function (rows) { var z0 = MOKE.zero(stage(rows, 0)), z1 = MOKE.zero(stage(rows, 1)); if (z0 === null || z1 === null) return 0.0; return (z1 - z0) / 2.0; },
  });

  function magTruth(p) {
    var t = typ(p);
    if (t === 0) return p.g * Math.sqrt(p.J * (p.J + 1.0));
    if (t === 1) return Magnet.tb(p);
    if (t === 2) return p.Tc;
    if (t === 3) return p.ms0 * Math.sqrt(1.0 - p.T0 / p.Tc) / p.mass;
    return p.Tc;
  }

  HK.register({
    K: { pk10_sctc: SCRT, pk10_jc: SCJc, pk10_mag: Magnet, pk10_dil: Dilution, pk10_hcr: HCRelax, pk10_ktc: KappaLT,
      pk10_qhe: QHall, pk10_sdh: SdH, pk10_hall: HallMob, pk10_seeb: Seebeck, pk10_dlts: DLTS, pk10_cv: CVProf,
      pk10_hs: HaynesShockley, pk10_eqe: SolarEQE, pk10_moss: Moss, pk10_fmr: FMR, pk10_esr: ESR, pk10_pos: Positron,
      pk10_moke: MOKE },
    TEXTBOOK: {
      pk10t_tc: function (p) { return p.Tc0; },
      pk10t_jc: function (p) { return SCJc.ic(p, p.T1, 0.0) / p.area; },
      pk10t_mag: magTruth,
      pk10t_nd: function (p) { return p.nd; },
      pk10t_hcr: function (p) { return [p.ThD, p.gam, p.D][typ(p)]; },
      pk10t_ktc: function (p) { return [p.rho0, p.c1 * Math.pow(4.2, p.c2), p.ell][typ(p)]; },
      pk10t_rk: function () { return RK; },
      pk10t_sdh: function (p) { return typ(p) === 2 ? p.ms : p.n; },
      pk10t_mu: function (p) { return HallMob.mu(p, 300.0); },
      pk10t_s: function (p) { return p.S; },
      pk10t_ea: function (p) { return p.Ea; },
      pk10t_cv: function (p) { return [p.ND, CVProf.vbi(p), CVProf.vfb(p)][typ(p)]; },
      pk10t_hs: function (p) { return p.mu; },
      pk10t_nid: function (p) { return p.nid; },
      pk10t_moss: function (p) { return [p.B, p.dIS, p.QS][typ(p)]; },
      pk10t_fmr: function (p) { return typ(p) === 0 ? p.g : p.Ms; },
      pk10t_esr: function (p) { return typ(p) === 0 ? p.g : p.A; },
      pk10t_pos: function (p) { return typ(p) === 0 ? p.t1 : p.t3; },
      pk10t_hc: function (p) { return p.Bc; },
    },
  });
  HK.PK10 = { RK: RK, MUB: MUB, H: H, QE: QE, KB: KB };
})(typeof window !== 'undefined' ? window : this);
