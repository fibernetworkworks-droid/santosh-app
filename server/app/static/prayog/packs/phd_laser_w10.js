/* Kernel pack (browser twin of app/prayog/packs/phd_laser_w10.py): Ph.D. laser spectroscopy, atomic physics,
   interferometry and quantum optics, wave 10 (kernels pl10_*). Same formulas, same order of operations, so both sides
   give the same numbers. Every kernel is a SWEEP: read(p, s, x, k) gives the reading at setting x of stage s, xs(p, s)
   lists the settings, fit(rows, p) works the result out of the rows, measure(p) = fit(run(plan)).
   Photon counts are Poisson draws from the lab's own seed (Gaussian approximation above 50): SIMULATED DATA. */
(function (root) {
  'use strict';
  var HK = (root && root.HoolaKernels) ||
    (typeof module !== 'undefined' && module.exports && module.exports.register ? module.exports : null);
  if (!HK) throw new Error('HoolaKernels is not loaded');
  var PI = Math.PI, LN2 = Math.log(2.0), C0 = 299792458.0, H = 6.62607015e-34, HBAR = H / (2.0 * PI);
  var KB = 1.380649e-23, MUB = 9.2740100783e-24, MU0 = 1.25663706212e-6, AMU = 1.66053906660e-27;
  var RINF = 10973731.568160, ME_MP = 1.0 / 1836.15267343, ZETA3 = 1.2020569031595942;

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
  function rng(a, b, d) { var n = Math.floor((b - a) / d + 0.5), out = [], i; for (i = 0; i <= n; i++) out.push(a + d * i); return out; }
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
  function peakwidth(pts, base) {
    var best = -1e300, ib = -1, i, lvl, a, b;
    for (i = 0; i < pts.length; i++) if (pts[i][1] > best) { best = pts[i][1]; ib = i; }
    if (ib < 0) return null;
    lvl = base + (best - base) / 2.0;
    a = half(pts, lvl, -1, ib); b = half(pts, lvl, 1, ib);
    if (a === null || b === null) return null;
    return [(a + b) / 2.0, b - a, best];
  }
  function pk(fn, x, w, d) {
    var n = Math.floor(2.0 * w / d + 0.5), best = -1e300, xb = x, i, v, y, y0, y1, y2, den, c;
    for (i = 0; i <= n; i++) { v = x - w + d * i; y = fn(v); if (y > best) { best = y; xb = v; } }
    y0 = fn(xb - d); y1 = fn(xb); y2 = fn(xb + d);
    den = y0 - 2.0 * y1 + y2;
    c = xb + (den < 0 ? d * (y0 - y2) / (2.0 * den) : 0.0);
    return [c, fn(c)];
  }
  function bisect(fn, a, b, lvl) {
    var fa = fn(a) - lvl, i, m, fm;
    for (i = 0; i < 60; i++) {
      m = (a + b) / 2.0; fm = fn(m) - lvl;
      if ((fa <= 0) === (fm <= 0)) { a = m; fa = fm; } else b = m;
    }
    return (a + b) / 2.0;
  }
  function det3(m) {
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
      + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]));
  }
  function fit3(pts) {
    var s = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], t = [0.0, 0.0, 0.0], k, i, j, v, d0, out = [], c, m;
    for (k = 0; k < pts.length; k++) {
      v = [1.0, Math.cos(pts[k][0]), Math.sin(pts[k][0])];
      for (i = 0; i < 3; i++) { t[i] += v[i] * pts[k][1]; for (j = 0; j < 3; j++) s[i][j] += v[i] * v[j]; }
    }
    d0 = det3(s);
    if (Math.abs(d0) < 1e-300) return null;
    for (c = 0; c < 3; c++) {
      m = [];
      for (i = 0; i < 3; i++) { m.push([]); for (j = 0; j < 3; j++) m[i].push(j === c ? t[i] : s[i][j]); }
      out.push(det3(m) / d0);
    }
    return out;
  }
  function gmin(fn, lo, hi, n, lg) {
    var a = lg ? Math.log(lo) : lo, b = lg ? Math.log(hi) : hi, d = (b - a) / n, best = 1e300, ib = 1, i, u, v, u0, u2, y0, y2, den;
    for (i = 1; i < n; i++) { u = a + d * i; v = fn(lg ? Math.exp(u) : u); if (v < best) { best = v; ib = i; } }
    u0 = a + d * (ib - 1); u = a + d * ib; u2 = a + d * (ib + 1);
    y0 = fn(lg ? Math.exp(u0) : u0); y2 = fn(lg ? Math.exp(u2) : u2);
    den = y0 - 2.0 * best + y2;
    u = u + (den > 0 ? d * (y0 - y2) / (2.0 * den) : 0.0);
    return lg ? Math.exp(u) : u;
  }
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
  function qi(p) { return Math.floor(p.q + 0.5); }
  function num(r, k) { return Number(r[k]); }

  // ================================================================ saturated absorption
  var SatAbs = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, T: 296.0, d87a: 266.650, d87b: 156.947, d85a: 120.640, d85b: 63.401, G: 6.0666, lw: 1.0, s0: 0.5, lam: 780.241 },
    NST: 3,
    dop: function (p, m) { var nu = C0 / (p.lam * 1e-9); return nu * Math.sqrt(8.0 * KB * p.T * LN2 / (m * AMU * C0 * C0)) / 1e6; },
    dens: function (p) { return Math.pow(10.0, 7.738 - 4215.0 / p.T) / p.T / (Math.pow(10.0, 7.738 - 4215.0 / 296.0) / 296.0); },
    lines: function (p, s) {
      var a, b, m, S, nu, D, out = [], i, j, dv;
      if (s === 1) { a = p.d85a; b = p.d85b; m = 84.911789738; S = [0.5556, 0.3194, 0.125]; }
      else { a = p.d87a; b = p.d87b; m = 86.909180527; S = [0.7, 0.25, 0.05]; }
      nu = [0.0, -a, -(a + b)];
      D = SatAbs.dop(p, m);
      for (i = 0; i < 3; i++) out.push([nu[i], S[i]]);
      for (i = 0; i < 3; i++) for (j = i + 1; j < 3; j++) {
        dv = (nu[i] - nu[j]) / 2.0;
        out.push([(nu[i] + nu[j]) / 2.0, 2.0 * Math.sqrt(S[i] * S[j]) * Math.exp(-4.0 * LN2 * (dv / D) * (dv / D))]);
      }
      return out;
    },
    width: function (p, s0) { return p.G * Math.sqrt(1.0 + s0) + p.lw; },
    sig: function (p, s, v, s0) {
      var w = SatAbs.width(p, s0), amp = 0.05 * SatAbs.dens(p) * s0 / (1.0 + s0), tot = 0.0, L = SatAbs.lines(p, s), i, u;
      for (i = 0; i < L.length; i++) { u = 2.0 * (v - L[i][0]) / w; tot += L[i][1] / (1.0 + u * u); }
      return amp * tot;
    },
    read: function (p, s, x) {
      var c, hf, a, b;
      if (s < 2) { c = pk(function (v) { return SatAbs.sig(p, s, v, p.s0); }, x, 10.0, 0.05); return { y: q_(c[0], 0.01), h: q_(c[1] * 1000.0, 0.001) }; }
      c = pk(function (v) { return SatAbs.sig(p, 0, v, x); }, 0.0, 4.0, 0.05);
      hf = c[1] / 2.0;
      a = bisect(function (v) { return -SatAbs.sig(p, 0, v, x); }, c[0] - 60.0, c[0], -hf);
      b = bisect(function (v) { return SatAbs.sig(p, 0, v, x); }, c[0], c[0] + 60.0, hf);
      return { y: q_(b - a, 0.01), h: q_(c[1] * 1000.0, 0.001) };
    },
    xs: function (p, s) { if (s === 2) return [0.25, 0.5, 1.0, 2.0, 3.0, 4.0]; return SatAbs.lines(p, s).map(function (l) { return q_(l[0], 2.0); }); },
    fit: function (rows, p) {
      var q = qi(p), c, f;
      if (q < 2) {
        c = stage(rows, q).map(function (r) { return num(r, 'y'); }).sort(function (a, b) { return a - b; });
        if (c.length < 6) return 0.0;
        return c[5] - c[2];
      }
      f = linfit(stage(rows, 2).map(function (r) { return [Math.sqrt(1.0 + num(r, 'x')), num(r, 'y')]; }));
      return f ? f[0] : 0.0;
    },
  });

  // ================================================================ optical pumping
  var OptPump = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, I85: 2.5, I87: 1.5, gJ: 2.00233113, Be: 3.6e-5, N: 135.0, R: 0.275, tau: 8.0, A: 0.2 },
    NST: 3,
    k: function (p) { return Math.pow(0.8, 1.5) * MU0 * p.N / p.R; },
    gf: function (p, I) { return p.gJ / (2.0 * I + 1.0); },
    cur: function (p, s, f, I) { var B = H * f * 1000.0 / (OptPump.gf(p, I) * MUB); return s === 0 ? (B - p.Be) / OptPump.k(p) : (B + p.Be) / OptPump.k(p); },
    read: function (p, s, x) {
      if (s < 2) return { y: q_(OptPump.cur(p, s, x, p.I87) * 1000.0, 0.01), y2: q_(OptPump.cur(p, s, x, p.I85) * 1000.0, 0.01) };
      return { y: q_(1.0 - p.A * Math.exp(-x / p.tau), 0.0001) };
    },
    xs: function (p, s) { return s === 2 ? [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 14.0, 18.0, 24.0, 80.0] : [600.0, 800.0, 1000.0, 1200.0, 1400.0]; },
    lines: function (rows, key) {
      return [linfit(stage(rows, 0).map(function (r) { return [num(r, 'x'), num(r, key)]; })),
        linfit(stage(rows, 1).map(function (r) { return [num(r, 'x'), num(r, key)]; }))];
    },
    fit: function (rows, p) {
      var q = qi(p), k = OptPump.k(p), ab, a, b, m, g, st, inf = null, i, pts = [], f;
      if (q < 3) {
        ab = OptPump.lines(rows, q === 0 ? 'y' : 'y2'); a = ab[0]; b = ab[1];
        if (!a || !b) return 0.0;
        m = (a[0] + b[0]) / 2.0;
        if (m <= 0) return 0.0;
        g = H * 1000.0 / (MUB * k * m / 1000.0);
        if (q === 0) return g;
        if (q === 1) return (p.gJ / g - 1.0) / 2.0;
        return k * (b[1] - a[1]) / 2.0 / 1000.0 * 1e6;
      }
      st = stage(rows, 2);
      if (st.length < 4) return 0.0;
      for (i = 0; i < st.length; i++) if (inf === null || num(st[i], 'x') > inf[0]) inf = [num(st[i], 'x'), num(st[i], 'y')];
      for (i = 0; i < st.length; i++) if (num(st[i], 'x') < inf[0] && inf[1] - num(st[i], 'y') > 0.01) pts.push([num(st[i], 'x'), Math.log(inf[1] - num(st[i], 'y'))]);
      f = linfit(pts);
      return f && f[0] < 0 ? -1.0 / f[0] : 0.0;
    },
  });

  // ================================================================ H / D isotope shift
  var HE = [447.1479, 501.5678, 587.5621, 667.8151, 706.5188];
  var HDShift = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, a: 2.0e-4, b: 0.35, rd: 1.99900750139, nair: 1.000277 },
    NST: 3,
    HE: HE,
    lam: function (p, n, deut) { var me_m = deut ? ME_MP / p.rd : ME_MP, R = RINF / (1.0 + me_m); return 1e9 / (R * (0.25 - 1.0 / (n * n))) / p.nair; },
    read: function (p, s, x) { var la = s === 0 ? HE[Math.floor(x + 0.5)] : HDShift.lam(p, x, s === 2); return { y: q_(la * (1.0 + p.a) + p.b, 0.0002) }; },
    xs: function (p, s) { return s === 0 ? [0.0, 1.0, 2.0, 3.0, 4.0] : [3.0, 4.0, 5.0, 6.0]; },
    ryd: function (rows, p, s, cal) {
      var sxy = 0.0, sxx = 0.0, st = stage(rows, s), i, n, la, u;
      for (i = 0; i < st.length; i++) {
        n = num(st[i], 'x'); la = (num(st[i], 'y') - cal[1]) / cal[0] * p.nair * 1e-9; u = 0.25 - 1.0 / (n * n);
        sxy += u / la; sxx += u * u;
      }
      return sxx > 0 ? sxy / sxx : 0.0;
    },
    fit: function (rows, p) {
      var pts = [], st = stage(rows, 0), i, j, cal, rh, rD, me_md;
      for (i = 0; i < st.length; i++) { j = Math.floor(num(st[i], 'x') + 0.5); if (j >= 0 && j < 5) pts.push([HE[j], num(st[i], 'y')]); }
      cal = linfit(pts);
      if (!cal || stage(rows, 1).length < 2) return 0.0;
      rh = HDShift.ryd(rows, p, 1, cal);
      if (qi(p) === 0) return rh;
      if (stage(rows, 2).length < 2) return 0.0;
      rD = HDShift.ryd(rows, p, 2, cal);
      me_md = (1.0 + ME_MP) * rh / rD - 1.0;
      return me_md > 0 ? ME_MP / me_md : 0.0;
    },
  });

  // ================================================================ diode laser
  var DiodeLaser = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, Ith: 32.5, eta: 0.82, beta: 1.0e-4, T0: 60.0, lam0: 780.0, dlI: 0.0065, dlT: 0.27, Iop: 60.0, Imax: 90.0 },
    NST: 3,
    power: function (p, I, T) {
      var ith = p.Ith * Math.exp((T - 25.0) / p.T0), r = I / ith;
      var s = ((r - 1.0) + Math.sqrt((r - 1.0) * (r - 1.0) + 4.0 * p.beta * r)) / 2.0;
      return p.eta * ith * s;
    },
    read: function (p, s, x) {
      if (s === 0) return { y: q_(DiodeLaser.power(p, x, 25.0), 0.01) };
      if (s === 1) return { y: q_(p.lam0 + p.dlI * (x - p.Iop), 0.0001) };
      return { y: q_(p.lam0 + p.dlT * (x - 25.0), 0.0001) };
    },
    xs: function (p, s) { if (s === 0) return rng(0.0, p.Imax, p.Imax / 18.0); if (s === 1) return rng(p.Iop - 20.0, p.Iop + 20.0, 5.0); return rng(15.0, 35.0, 2.5); },
    fit: function (rows, p) {
      var q = qi(p), st, top = 0.0, i, pts = [], f;
      if (q < 2) {
        st = stage(rows, 0);
        for (i = 0; i < st.length; i++) top = Math.max(top, num(st[i], 'y'));
        for (i = 0; i < st.length; i++) if (num(st[i], 'y') > 0.25 * top) pts.push([num(st[i], 'x'), num(st[i], 'y')]);
        f = linfit(pts);
        if (!f || f[0] <= 0) return 0.0;
        return q === 0 ? -f[1] / f[0] : f[0];
      }
      f = linfit(stage(rows, q - 1).map(function (r) { return [num(r, 'x'), num(r, 'y')]; }));
      return f ? f[0] : 0.0;
    },
  });

  // ================================================================ frequency lock
  var FreqLock = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, m: 0.0, Gd: 12.0, Hd: 0.8, a: 1.0, Ki: 3.0e5, S0: 2.0e5, rin: 1.0e-10 },
    NST: 3,
    slope: function (p) { return p.m < 0.5 ? p.Hd / p.Gd : 8.0 * p.a * p.Hd / (p.Gd * p.Gd); },
    fu: function (p) { return FreqLock.slope(p) * p.Ki; },
    err: function (p, d) {
      var u;
      if (p.m < 0.5) { u = 2.0 * (d + p.Gd / 2.0) / p.Gd; return p.Hd / (1.0 + u * u) - p.Hd / 2.0; }
      u = 2.0 * d / p.Gd;
      return -p.a * p.Hd * 8.0 * d / (p.Gd * p.Gd) / ((1.0 + u * u) * (1.0 + u * u));
    },
    sigma: function (p, B) {
      var fu = FreqLock.fu(p), v = p.S0 * (B - fu * Math.atan(B / fu)), D;
      if (p.m < 0.5) { D = FreqLock.slope(p) / 1e6; v += (p.Hd / 2.0) * (p.Hd / 2.0) * p.rin / (D * D) * fu * Math.atan(B / fu); }
      return Math.sqrt(v);
    },
    read: function (p, s, x) {
      var fu;
      if (s === 0) return { y: q_(FreqLock.err(p, x), 0.0001) };
      if (s === 1) { fu = FreqLock.fu(p); return { y: q_(x / Math.sqrt(x * x + fu * fu), 0.0001) }; }
      return { y: q_(FreqLock.sigma(p, x) / 1000.0, 0.01) };
    },
    xs: function (p, s) { if (s === 0) return rng(-0.5, 0.5, 0.25); if (s === 1) return [1000.0, 3000.0, 10000.0, 30000.0, 100000.0, 300000.0]; return [1000.0, 10000.0, 100000.0]; },
    fit: function (rows, p) {
      var f = linfit(stage(rows, 0).map(function (r) { return [num(r, 'x'), num(r, 'y')]; })), D, st, i, g, pts = [];
      if (!f || f[0] === 0) return 0.0;
      D = Math.abs(f[0]);
      if (qi(p) === 1) {
        st = stage(rows, 2);
        for (i = 0; i < st.length; i++) if (Math.abs(num(st[i], 'x') - 100000.0) < 1.0) return num(st[i], 'y');
        return 0.0;
      }
      st = stage(rows, 1);
      for (i = 0; i < st.length; i++) if (num(st[i], 'y') > 0) pts.push([1.0 / (num(st[i], 'x') * num(st[i], 'x')), 1.0 / (num(st[i], 'y') * num(st[i], 'y'))]);
      g = linfit(pts);
      if (!g || g[0] <= 0) return 0.0;
      return D > 0 ? Math.sqrt(g[0]) : 0.0;
    },
  });

  // ================================================================ second harmonic
  function sell(cry, lam) {
    var l2 = lam * lam, no, ne;
    if (cry < 0.5) {
      no = 2.259276 + 0.01008956 / (l2 - 0.012942625) + 13.00522 * l2 / (l2 - 400.0);
      ne = 2.132668 + 0.008637494 / (l2 - 0.012281043) + 3.2279924 * l2 / (l2 - 400.0);
    } else {
      no = 2.7359 + 0.01878 / (l2 - 0.01822) - 0.01354 * l2;
      ne = 2.3753 + 0.01224 / (l2 - 0.01667) - 0.01516 * l2;
    }
    return [Math.sqrt(no), Math.sqrt(ne)];
  }
  var SHG = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, cry: 1.0, lam: 1.064, L: 5.0, thc: 22.5, eta: 1.0e-4, Pf: 2.0, span: 0.5 },
    NST: 2,
    theta_pm: function (p) {
      var w = sell(p.cry, p.lam), v = sell(p.cry, p.lam / 2.0);
      var s2 = (1.0 / (w[0] * w[0]) - 1.0 / (v[0] * v[0])) / (1.0 / (v[1] * v[1]) - 1.0 / (v[0] * v[0]));
      return Math.asin(Math.sqrt(s2)) * 180.0 / PI;
    },
    internal: function (p, x) { var n = sell(p.cry, p.lam)[0]; return p.thc + Math.asin(Math.sin(x * PI / 180.0) / n) * 180.0 / PI; },
    ext_of: function (p, th) { var n = sell(p.cry, p.lam)[0]; return Math.asin(n * Math.sin((th - p.thc) * PI / 180.0)) * 180.0 / PI; },
    eff: function (p, x) {
      var th = SHG.internal(p, x) * PI / 180.0, w = sell(p.cry, p.lam), v = sell(p.cry, p.lam / 2.0);
      var ne = 1.0 / Math.sqrt(Math.cos(th) * Math.cos(th) / (v[0] * v[0]) + Math.sin(th) * Math.sin(th) / (v[1] * v[1]));
      var dk = 4.0 * PI / (p.lam * 1e-6) * (ne - w[0]), u = dk * p.L * 1e-3 / 2.0;
      return Math.abs(u) < 1e-12 ? 1.0 : (Math.sin(u) / u) * (Math.sin(u) / u);
    },
    read: function (p, s, x) {
      var v = s === 0 ? p.eta * x * x * SHG.eff(p, SHG.ext_of(p, SHG.theta_pm(p))) : p.eta * p.Pf * p.Pf * SHG.eff(p, x);
      return { y: q_(v * 1000.0, 0.0001) };
    },
    xs: function (p, s) {
      if (s === 0) return [0.5, 1.0, 1.5, 2.0, 3.0, 4.0];
      var c = q_(SHG.ext_of(p, SHG.theta_pm(p)), 0.05);
      return rng(c - p.span, c + p.span, p.span / 25.0);
    },
    fit: function (rows, p) {
      var pts = [], st, i, f, pw;
      if (qi(p) === 0) {
        st = stage(rows, 0);
        for (i = 0; i < st.length; i++) if (num(st[i], 'x') > 0 && num(st[i], 'y') > 0) pts.push([Math.log(num(st[i], 'x')), Math.log(num(st[i], 'y'))]);
        f = linfit(pts);
        return f ? f[0] : 0.0;
      }
      pw = peakwidth(sorted(stage(rows, 1)), 0.0);
      if (!pw) return 0.0;
      return SHG.internal(p, pw[0]);
    },
  });

  // ================================================================ z-scan
  var ZScan = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, n2: 3.0e-18, beta: 0.0, I0: 1.0e13, w0: 20.0, lam: 532.0, Ls: 1.0, alpha: 10.0 },
    NST: 2,
    z0: function (p) { return PI * p.w0 * 1e-6 * p.w0 * 1e-6 / (p.lam * 1e-9) * 1000.0; },
    leff: function (p) { var L = p.Ls * 1e-3; return p.alpha <= 0 ? L : (1.0 - Math.exp(-p.alpha * L)) / p.alpha; },
    topen: function (q0, x) { var tot = 0.0, m; for (m = 0; m < 30; m++) tot += Math.pow(-q0, m) / (Math.pow(m + 1.0, 1.5) * Math.pow(1.0 + x * x, m)); return tot; },
    fclose: function (x) { return 4.0 * x / ((x * x + 9.0) * (x * x + 1.0)); },
    read: function (p, s, x) {
      var u = x / ZScan.z0(p), q0 = p.beta * p.I0 * ZScan.leff(p), to = ZScan.topen(q0, u), dp;
      if (s === 0) return { y: q_(to, 0.0001) };
      dp = 2.0 * PI / (p.lam * 1e-9) * p.n2 * p.I0 * ZScan.leff(p);
      return { y: q_(to * (1.0 + dp * ZScan.fclose(u)), 0.0001), y2: q_(to, 0.0001) };
    },
    xs: function (p) { var z0 = ZScan.z0(p); return rng(-6.0, 6.0, 0.5).map(function (u) { return q_(z0 * u, 0.1); }); },
    fit: function (rows, p) {
      var z0 = ZScan.z0(p), st, i, sfy = 0.0, sff = 0.0, fx, dp;
      if (qi(p) === 1) {
        st = stage(rows, 0);
        if (st.length < 5) return 0.0;
        var err = function (q0) { var e = 0.0, j, d; for (j = 0; j < st.length; j++) { d = ZScan.topen(q0, num(st[j], 'x') / z0) - num(st[j], 'y'); e += d * d; } return e; };
        return gmin(err, 0.0, 0.95, 95, false) / (p.I0 * ZScan.leff(p));
      }
      st = stage(rows, 1);
      for (i = 0; i < st.length; i++) {
        if (num(st[i], 'y2') <= 0) continue;
        fx = ZScan.fclose(num(st[i], 'x') / z0);
        sfy += fx * (num(st[i], 'y') / num(st[i], 'y2') - 1.0); sff += fx * fx;
      }
      if (sff <= 0) return 0.0;
      dp = sfy / sff;
      return dp / (2.0 * PI / (p.lam * 1e-9) * p.I0 * ZScan.leff(p));
    },
  });

  // ================================================================ TCSPC
  function emg(t, tau, sig) {
    if (sig <= 0) return t >= 0 ? Math.exp(-t / tau) : 0.0;
    var a = sig / tau - t / sig;
    return Math.exp(sig * sig / (2.0 * tau * tau) - t / tau) * 0.5 * erfc(a / Math.sqrt(2.0));
  }
  var TCSPC = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, t1: 4.08, t2: 20.0, a2: 0.0, tz: 3.0, irf: 0.1, bw: 0.5, Np: 200000.0, bg: 20.0, span: 40.0, seed: 7.0, ms: 0.0 },
    shape: function (p, t) { var u = t - p.tz; return (1.0 - p.a2) * emg(u, p.t1, p.irf) + p.a2 * emg(u, p.t2, p.irf); },
    read: function (p, s, x, k) { var mean = p.Np * TCSPC.shape(p, x + p.bw / 2.0) + p.bg; return { y: cnt(p, k, mean) }; },
    xs: function (p) { return rng(0.0, p.span, p.span / 60.0); },
    tail: function (pts, bg) {
      var sw = 0.0, sx = 0.0, sy = 0.0, sxx = 0.0, sxy = 0.0, i, v, w, y, den, m;
      for (i = 0; i < pts.length; i++) {
        v = pts[i][1] - bg;
        if (v <= 0) continue;
        w = v; y = Math.log(v);
        sw += w; sx += w * pts[i][0]; sy += w * y; sxx += w * pts[i][0] * pts[i][0]; sxy += w * pts[i][0] * y;
      }
      den = sw * sxx - sx * sx;
      if (sw <= 0 || Math.abs(den) < 1e-300) return null;
      m = (sw * sxy - sx * sy) / den;
      return [m, (sy - m * sx) / sw];
    },
    fit: function (rows, p) {
      var pts = stage(rows, 0).map(function (r) { return [num(r, 'x') + p.bw / 2.0, num(r, 'y')]; });
      var pre = [], i, bg = 0.0, t0, q, f, sel = [];
      for (i = 0; i < pts.length; i++) if (pts[i][0] < p.tz - 4.0 * p.irf - p.bw) pre.push(pts[i][1]);
      if (pre.length) { for (i = 0; i < pre.length; i++) bg += pre[i]; bg = bg / pre.length; }
      t0 = p.tz + 5.0 * p.irf + p.bw;
      q = qi(p);
      if (q === 0) {
        for (i = 0; i < pts.length; i++) if (pts[i][0] > t0) sel.push(pts[i]);
        f = TCSPC.tail(sel, bg);
        return f && f[0] < 0 ? -1.0 / f[0] : 0.0;
      }
      for (i = 0; i < pts.length; i++) if (pts[i][0] > t0) sel.push(pts[i]);
      f = TCSPC.fit2(sel, bg, p.span);
      if (!f) return 0.0;
      return q === 1 ? f[0] : f[1];
    },
    chi: function (pts, bg, t1, t2) {
      var s11 = 0.0, s12 = 0.0, s22 = 0.0, b1 = 0.0, b2 = 0.0, i, w, e1, e2, y, den, a1, a2, c = 0.0, d;
      for (i = 0; i < pts.length; i++) {
        w = 1.0 / Math.max(pts[i][1], 1.0); e1 = Math.exp(-pts[i][0] / t1); e2 = Math.exp(-pts[i][0] / t2); y = pts[i][1] - bg;
        s11 += w * e1 * e1; s12 += w * e1 * e2; s22 += w * e2 * e2; b1 += w * e1 * y; b2 += w * e2 * y;
      }
      den = s11 * s22 - s12 * s12;
      if (Math.abs(den) < 1e-300) return 1e300;
      a1 = (b1 * s22 - b2 * s12) / den; a2 = (s11 * b2 - s12 * b1) / den;
      for (i = 0; i < pts.length; i++) { d = pts[i][1] - bg - a1 * Math.exp(-pts[i][0] / t1) - a2 * Math.exp(-pts[i][0] / t2); c += d * d / Math.max(pts[i][1], 1.0); }
      return c;
    },
    best1: function (pts, bg, t2, span) { return gmin(function (t1) { return TCSPC.chi(pts, bg, t1, t2); }, span / 400.0, t2 * 0.6, 50, true); },
    fit2: function (pts, bg, span) {
      if (pts.length < 6) return null;
      var t2 = gmin(function (u) { return TCSPC.chi(pts, bg, TCSPC.best1(pts, bg, u, span), u); }, span / 100.0, span, 50, true);
      return [TCSPC.best1(pts, bg, t2, span), t2];
    },
  });

  // ================================================================ pump-probe
  var PumpProbe = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, A: 40.0, tc: 1.6, sig: 0.08, xz: 25.0, lb: 870.0, wb: 28.0, td: 0.5 },
    NST: 2,
    delay: function (p, x) { return 2.0 * (x - p.xz) * 1e-3 / C0 * 1e12; },
    read: function (p, s, x) {
      var v, u;
      if (s === 0) v = p.A * emg(PumpProbe.delay(p, x), p.tc, p.sig);
      else { u = (x - p.lb) / p.wb; v = p.A * emg(p.td, p.tc, p.sig) * Math.exp(-4.0 * LN2 * u * u); }
      return { y: q_(v, 0.001) };
    },
    xs: function (p, s) {
      var step, out = [], i;
      if (s === 0) { step = p.tc * C0 * 1e-12 / 2.0 * 1e3 / 4.0; for (i = 0; i < 26; i++) out.push(q_(p.xz - 3.0 * step + step * i, 0.0001)); return out; }
      return rng(p.lb - 1.5 * p.wb, p.lb + 1.5 * p.wb, p.wb / 10.0);
    },
    fit: function (rows, p) {
      var st, top = null, i, pts = [], f, pw;
      if (qi(p) === 1) { pw = peakwidth(sorted(stage(rows, 1)), 0.0); return pw ? pw[0] : 0.0; }
      st = stage(rows, 0);
      for (i = 0; i < st.length; i++) if (top === null || num(st[i], 'y') > top[1]) top = [num(st[i], 'x'), num(st[i], 'y')];
      if (top === null) return 0.0;
      for (i = 0; i < st.length; i++) if (num(st[i], 'x') > top[0] + 0.03 && num(st[i], 'y') > 0.02 * top[1]) pts.push([2.0 * num(st[i], 'x') * 1e-3 / C0 * 1e12, Math.log(num(st[i], 'y'))]);
      f = linfit(pts);
      return f && f[0] < 0 ? -1.0 / f[0] : 0.0;
    },
  });

  // ================================================================ magneto-optical trap
  var M87 = 86.909180527 * AMU;
  var MOT = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, Tk: 120.0, vc: 25.0, tl: 1.5, G: 6.0666, st: 3.0, det: -12.0, eta: 0.004, resp: 0.5, Rf: 1.0e6, sig0: 0.6, nv: 1.0e14, d: 0.02, Tr: 296.0 },
    NST: 3,
    M87: M87,
    scat: function (p) { var g = 2.0 * PI * p.G * 1e6, dd = p.det / p.G; return g / 2.0 * p.st / (1.0 + p.st + 4.0 * dd * dd); },
    ephot: function () { return H * C0 / 780.241e-9; },
    volt: function (p, n) { return n * MOT.scat(p) * MOT.ephot() * p.eta * p.resp * p.Rf; },
    rate: function (p) { return 0.5 * p.nv * p.d * p.d * Math.pow(p.vc, 4.0) * Math.pow(M87 / (2.0 * KB * p.Tr), 1.5); },
    read: function (p, s, x) {
      var t, sg, n;
      if (s === 0) return { y: q_(MOT.volt(p, MOT.rate(p) * p.tl), 0.0001) };
      if (s === 1) { t = x * 1e-3; sg = Math.sqrt(p.sig0 * p.sig0 * 1e-6 + KB * p.Tk * 1e-6 * t * t / M87); return { y: q_(sg * 1000.0, 0.001) }; }
      n = MOT.rate(p) * p.tl * (1.0 - Math.exp(-x / p.tl));
      return { y: q_(MOT.volt(p, n), 0.0001) };
    },
    xs: function (p, s) { if (s === 0) return [1.0, 2.0, 3.0]; if (s === 1) return [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]; return [0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 3.0, 15.0]; },
    fit: function (rows, p) {
      var q = qi(p), per = MOT.volt(p, 1.0), st, tot = 0.0, i, f, end = null, pts = [], tl, R;
      if (q === 0) { st = stage(rows, 0); if (!st.length) return 0.0; for (i = 0; i < st.length; i++) tot += num(st[i], 'y'); return tot / st.length / per; }
      if (q === 1) {
        f = linfit(stage(rows, 1).map(function (r) { return [(num(r, 'x') * 1e-3) * (num(r, 'x') * 1e-3), (num(r, 'y') * 1e-3) * (num(r, 'y') * 1e-3)]; }));
        return f ? f[0] * M87 / KB * 1e6 : 0.0;
      }
      st = stage(rows, 2);
      if (st.length < 4) return 0.0;
      for (i = 0; i < st.length; i++) if (end === null || num(st[i], 'x') > end[0]) end = [num(st[i], 'x'), num(st[i], 'y')];
      for (i = 0; i < st.length; i++) if (num(st[i], 'x') < end[0] && num(st[i], 'y') < 0.97 * end[1]) pts.push([num(st[i], 'x'), Math.log(1.0 - num(st[i], 'y') / end[1])]);
      f = linfit(pts);
      if (!f || f[0] >= 0) return 0.0;
      tl = -1.0 / f[0]; R = end[1] / per / tl;
      return Math.pow(R / (0.5 * p.nv * p.d * p.d * Math.pow(M87 / (2.0 * KB * p.Tr), 1.5)), 0.25);
    },
  });

  // ================================================================ BEC
  var BEC = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, fx: 30.0, fy: 30.0, fz: 120.0, eta: 10.0, Ni: 3.0e6, Ti: 1200.0, ga: 0.6, Nref: 1.0e6 },
    wbar: function (p) { return 2.0 * PI * Math.pow(p.fx * p.fy * p.fz, 1.0 / 3.0); },
    tc: function (p, n) { return Math.pow(ZETA3, -1.0 / 3.0) * HBAR * BEC.wbar(p) * Math.pow(n, 1.0 / 3.0) / KB * 1e9; },
    shot: function (p, x) {
      var T = H * x * 1000.0 / (p.eta * KB) * 1e9, n = p.Ni * Math.pow(T / p.Ti, p.ga), tc = BEC.tc(p, n);
      var f = T < tc ? 1.0 - Math.pow(T / tc, 3.0) : 0.0;
      return [T, n, f];
    },
    read: function (p, s, x) { var r = BEC.shot(p, x); return { y: q_(r[0], 0.1), N: q_(r[1], 100.0), f: q_(r[2], 0.001) }; },
    xs: function () { return [60.0, 52.0, 46.0, 42.0, 38.0, 34.0, 30.0, 26.0, 22.0, 18.0]; },
    fit: function (rows, p) {
      var tot = 0.0, k = 0, st = stage(rows, 0), i, f, tc;
      for (i = 0; i < st.length; i++) {
        f = num(st[i], 'f');
        if (f > 0.05 && f < 0.95) { tc = num(st[i], 'y') / Math.pow(1.0 - f, 1.0 / 3.0); tot += tc * Math.pow(p.Nref / num(st[i], 'N'), 1.0 / 3.0); k += 1; }
      }
      return k ? tot / k : 0.0;
    },
  });

  // ================================================================ Michelson metrology
  var MichMetro = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, cal: 1.0237, lh: 632.816, ll: 625.0, dl: 17.0, l1: 588.995, l2: 589.592, dn: 1.7 },
    NST: 3,
    vled: function (p, x) { var dnu = C0 * p.dl * 1e-9 / (p.ll * 1e-9 * p.ll * 1e-9), a = PI * dnu * x * 1e-6 / C0; return Math.exp(-a * a / (4.0 * LN2)); },
    vna: function (p, x) {
      var ds = 1.0 / (p.l1 * 1e-9) - 1.0 / (p.l2 * 1e-9), a = PI * p.dn * 1e9 * x * 1e-6 / C0;
      return Math.abs(Math.cos(PI * x * 1e-6 * ds)) * Math.exp(-a * a / (4.0 * LN2));
    },
    beat: function (p) { return 1.0 / (1.0 / (p.l1 * 1e-9) - 1.0 / (p.l2 * 1e-9)) * 1e6; },
    read: function (p, s, x) {
      if (s === 0) return { y: Math.floor(2.0 * p.cal * x * 1000.0 / p.lh) };
      if (s === 1) return { y: q_(MichMetro.vled(p, x), 0.001) };
      return { y: q_(MichMetro.vna(p, x), 0.001) };
    },
    xs: function (p, s) {
      var lc, b, out = [], i;
      if (s === 0) return [20.0, 40.0, 60.0, 80.0, 100.0];
      if (s === 1) { lc = 4.0 * LN2 * p.ll * p.ll / (PI * p.dl) / 1000.0; return rng(0.0, 1.2, 0.05).map(function (u) { return q_(lc * u, 0.01); }); }
      b = MichMetro.beat(p);
      for (i = 0; i < 7; i++) out.push(q_(b * 50.0 * i, 0.1));
      return out;
    },
    fit: function (rows, p) {
      var q = qi(p), st, i, pts = [], pw, f;
      if (q === 0) {
        st = stage(rows, 0);
        for (i = 0; i < st.length; i++) if (Math.abs(num(st[i], 'x') - 100.0) < 1e-6) return num(st[i], 'y') * p.lh / 2.0 / 1000.0;
        return 0.0;
      }
      if (q === 1 || q === 3) {
        st = stage(rows, 1);
        for (i = 0; i < st.length; i++) pts.push([-num(st[i], 'x'), num(st[i], 'y')]);
        for (i = 0; i < st.length; i++) if (num(st[i], 'x') > 0) pts.push([num(st[i], 'x'), num(st[i], 'y')]);
        pts.sort(function (a, b) { return a[0] - b[0]; });
        pw = peakwidth(pts, 0.0);
        if (!pw) return 0.0;
        return q === 1 ? pw[1] : 4.0 * LN2 * p.ll * p.ll / (PI * pw[1] * 1000.0);
      }
      st = stage(rows, 2);
      for (i = 0; i < st.length; i++) if (num(st[i], 'y') > 0) pts.push([num(st[i], 'x') * 1e-6 * (num(st[i], 'x') * 1e-6), Math.log(num(st[i], 'y'))]);
      f = linfit(pts);
      if (!f || f[0] >= 0) return 0.0;
      return Math.sqrt(-f[0] * 4.0 * LN2) * C0 / PI / 1e9;
    },
  });

  // ================================================================ Hong-Ou-Mandel
  var HOM = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, lam: 810.0, dl: 5.0, V0: 0.96, th: 0.0, C0: 1200.0, t: 60.0, acc: 2.0, seed: 31.0 },
    w: function (p) { return 4.0 * LN2 * p.lam * p.lam / (PI * p.dl) / 1000.0; },
    vis: function (p) { var c = Math.cos(p.th * PI / 180.0); return p.V0 * c * c; },
    read: function (p, s, x, k) {
      var u = x / HOM.w(p), mean = (p.C0 * (1.0 - HOM.vis(p) * Math.exp(-4.0 * LN2 * u * u)) + p.acc) * p.t;
      return { y: cnt(p, k, mean), T: p.t };
    },
    xs: function (p) { var w = HOM.w(p); return rng(-3.0, 3.0, 0.25).map(function (u) { return q_(w * u, 0.5); }); },
    fit: function (rows, p) {
      var st = stage(rows, 0), w = 0.0, i, far = [], c0 = 0.0, pts = [], d, f;
      for (i = 0; i < st.length; i++) w = Math.max(w, Math.abs(num(st[i], 'x')));
      for (i = 0; i < st.length; i++) if (Math.abs(num(st[i], 'x')) > 0.66 * w) far.push(num(st[i], 'y') / num(st[i], 'T') - p.acc);
      if (!far.length) return 0.0;
      for (i = 0; i < far.length; i++) c0 += far[i];
      c0 = c0 / far.length;
      for (i = 0; i < st.length; i++) {
        d = 1.0 - (num(st[i], 'y') / num(st[i], 'T') - p.acc) / c0;
        if (d > 0.2) pts.push([num(st[i], 'x') * num(st[i], 'x'), Math.log(d)]);
      }
      f = linfit(pts);
      if (!f || f[0] >= 0) return 0.0;
      return qi(p) === 0 ? Math.exp(f[1]) : 2.0 * Math.sqrt(LN2 / -f[0]);
    },
  });

  // ================================================================ CHSH
  var CA = [0.0, 45.0, 90.0, 135.0], CB = [22.5, 67.5, 112.5, 157.5];
  var CHSH = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, V: 0.93, R0: 4000.0, acc: 3.0, t: 30.0, seed: 41.0 },
    NST: 2,
    A: CA, B: CB,
    ab: function (s, x) { var i = Math.floor(x + 0.5); if (s === 0) return [i < 9 ? 0.0 : 45.0, 22.5 * (i % 9)]; return [CA[Math.floor(i / 4)], CB[i % 4]]; },
    read: function (p, s, x, k) {
      var ab = CHSH.ab(s, x), mean = (p.R0 / 4.0 * (1.0 + p.V * Math.cos(2.0 * (ab[0] - ab[1]) * PI / 180.0)) + p.acc) * p.t;
      return { y: cnt(p, k, mean), T: p.t };
    },
    xs: function (p, s) { var out = [], i, n = s === 0 ? 18 : 16; for (i = 0; i < n; i++) out.push(i); return out; },
    fit: function (rows, p) {
      var n = function (r) { return num(r, 'y') / num(r, 'T') - p.acc; };
      var vs = [], hf, st, hi, lo, i, N = {}, cnt16 = 0, E, tot = 0.0;
      if (qi(p) === 1) {
        for (hf = 0; hf < 2; hf++) {
          st = stage(rows, 0).filter(function (r) { return (Math.floor(num(r, 'x') + 0.5) >= 9) === (hf === 1); });
          if (!st.length) continue;
          hi = -1e300; lo = 1e300;
          for (i = 0; i < st.length; i++) { hi = Math.max(hi, n(st[i])); lo = Math.min(lo, n(st[i])); }
          vs.push((hi - lo) / (hi + lo));
        }
        if (!vs.length) return 0.0;
        for (i = 0; i < vs.length; i++) tot += vs[i];
        return tot / vs.length;
      }
      st = stage(rows, 1);
      for (i = 0; i < st.length; i++) { var key = Math.floor(num(st[i], 'x') + 0.5); if (!(key in N)) cnt16 += 1; N[key] = n(st[i]); }
      if (cnt16 < 16) return 0.0;
      E = function (a, b) {
        var pp = N[4 * a + b], mm = N[4 * (a + 2) + b + 2], pm = N[4 * a + b + 2], mp = N[4 * (a + 2) + b];
        return (pp + mm - pm - mp) / (pp + mm + pm + mp);
      };
      return E(0, 0) - E(0, 1) + E(1, 0) + E(1, 1);
    },
  });

  // ================================================================ quantum eraser
  var Eraser = sweep({
    PARAMS: { x: 0.0, s: 0.0, q: 0.0, V0: 0.94, psi: 90.0, Rc: 20000.0, t: 10.0, Vf: 4.0, seed: 53.0 },
    NST: 3,
    vis: function (p, s) { return s === 1 ? p.V0 * Math.abs(Math.cos(p.psi * PI / 180.0)) : p.V0; },
    read: function (p, s, x, k) {
      var ph = 2.0 * PI * x / p.Vf, c = Math.cos(p.psi * PI / 360.0), r = p.Rc * (s === 2 ? c * c : 1.0);
      var mean = r * p.t * (1.0 + Eraser.vis(p, s) * Math.cos(ph)) / 2.0;
      return { y: cnt(p, k, mean), T: p.t };
    },
    xs: function (p) { return rng(0.0, 2.0 * p.Vf, p.Vf / 8.0); },
    fit: function (rows, p) {
      var s = qi(p) === 0 ? 2 : 1, pts = stage(rows, s).map(function (r) { return [2.0 * PI * num(r, 'x') / p.Vf, num(r, 'y')]; }), c;
      if (pts.length < 4) return 0.0;
      c = fit3(pts);
      if (!c || c[0] <= 0) return 0.0;
      return Math.sqrt(c[1] * c[1] + c[2] * c[2]) / c[0];
    },
  });

  HK.register({
    K: { pl10_satabs: SatAbs, pl10_oppump: OptPump, pl10_hdshift: HDShift, pl10_diodelaser: DiodeLaser, pl10_freqlock: FreqLock,
      pl10_shg: SHG, pl10_zscan: ZScan, pl10_tcspc: TCSPC, pl10_pumpprobe: PumpProbe, pl10_mot: MOT, pl10_bec: BEC,
      pl10_michmetro: MichMetro, pl10_hom: HOM, pl10_chsh: CHSH, pl10_eraser: Eraser },
    TEXTBOOK: {
      pl10_sat: function (p) { return [p.d87a, p.d85a, p.G][qi(p)]; },
      pl10_pump: function (p) { var q = qi(p); if (q === 0) return p.gJ / (2.0 * p.I87 + 1.0); if (q === 1) return p.I85; if (q === 2) return p.Be * 1e6; return p.tau; },
      pl10_ryd: function (p) { return qi(p) === 0 ? RINF / (1.0 + ME_MP) : p.rd; },
      pl10_diode: function (p) { return [p.Ith, p.eta, p.dlI, p.dlT][qi(p)]; },
      pl10_lock: function (p) { return qi(p) === 0 ? FreqLock.fu(p) : FreqLock.sigma(p, 100000.0) / 1000.0; },
      pl10_shgpm: function (p) { return qi(p) === 0 ? 2.0 : SHG.theta_pm(p); },
      pl10_nl: function (p) { return qi(p) === 0 ? p.n2 : p.beta; },
      pl10_life: function (p) { return qi(p) < 2 ? p.t1 : p.t2; },
      pl10_relax: function (p) { return qi(p) === 0 ? p.tc : p.lb; },
      pl10_motq: function (p) { return [MOT.rate(p) * p.tl, p.Tk, p.vc][qi(p)]; },
      pl10_tc: function (p) { return BEC.tc(p, p.Nref); },
      pl10_mich: function (p) { return [p.cal * 100.0, 4.0 * LN2 * p.ll * p.ll / (PI * p.dl) / 1000.0, p.dn, p.dl][qi(p)]; },
      pl10_homv: function (p) { return qi(p) === 0 ? HOM.vis(p) : HOM.w(p); },
      pl10_bell: function (p) { return qi(p) === 0 ? 2.0 * Math.sqrt(2.0) * p.V : p.V; },
      pl10_erase: function (p) { return qi(p) === 0 ? p.V0 : p.V0 * Math.abs(Math.cos(p.psi * PI / 180.0)); },
    },
  });
  HK.PL10 = { erfc: erfc, emg: emg, pk: pk };
})(typeof window !== 'undefined' ? window : this);
