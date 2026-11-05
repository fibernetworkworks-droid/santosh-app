/* Prayogshala kernel pack: M.Sc. OPTICS, INTERFEROMETRY AND SPECTROSCOPY - the JavaScript twin of
   server/app/prayog/packs/msc_optics.py, step for step. Kernels: msc_michelson, msc_gascell (the interferometer rig),
   msc_iodine, msc_rovib, msc_raman, msc_fluor, msc_tauc, msc_varshni, msc_decay, msc_glow, msc_beer (the spectrograph rig).
   Deterministic: no randomness, no wall clock. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels;
  if (!H) throw new Error('kernels.js must load before its packs');
  var PI = Math.PI, HC_EV_NM = 1239.84198, KB_EV = 8.617333262e-5, C2_CMK = 1.438777;
  var C_LIGHT = 2.99792458e8, AMU = 1.66053906660e-27;

  function ternMax(f, lo, hi, iters) {
    var n = iters === undefined ? 80 : iters, a1, a2, i;
    for (i = 0; i < n; i++) {
      a1 = lo + (hi - lo) / 3.0; a2 = hi - (hi - lo) / 3.0;
      if (f(a1) > f(a2)) hi = a2; else lo = a1;
    }
    return (lo + hi) / 2.0;
  }
  function ternMin(f, lo, hi, iters) { return ternMax(function (x) { return -f(x); }, lo, hi, iters); }
  function bisect(f, lo, hi, iters) {
    var n = iters === undefined ? 80 : iters, flo = f(lo), mid, i;
    for (i = 0; i < n; i++) {
      mid = (lo + hi) / 2.0;
      if (flo * f(mid) <= 0) hi = mid; else { lo = mid; flo = f(lo); }
    }
    return (lo + hi) / 2.0;
  }
  function rows(rs, keys) {
    var out = [], i, j, v, vals, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) {
        v = rs[i][keys[j]];
        if (v === undefined || v === null || v === '' || !isFinite(+v)) { ok = false; break; }
        vals.push(+v);
      }
      if (ok) out.push(vals);
    }
    return out;
  }
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0; }
  function slope(pts) {
    var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, den;
    if (n < 2) return 0;
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    den = n * sxx - sx * sx;
    return den ? (n * sxy - sx * sy) / den : 0;
  }
  function line(pts) {
    var n = pts.length, m, sx = 0, sy = 0, i;
    if (n < 2) return [0, 0];
    m = slope(pts);
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; }
    return [m, (sy - m * sx) / n];
  }
  function peaks(f, lo, hi, n, thr) {
    var step = (hi - lo) / n, ys = [], i, top = -Infinity, out = [], x;
    for (i = 0; i <= n; i++) { ys.push(f(lo + i * step)); if (ys[i] > top) top = ys[i]; }
    for (i = 1; i < n; i++) {
      if (ys[i] > ys[i - 1] && ys[i] >= ys[i + 1] && ys[i] > thr * top) {
        x = ternMax(f, lo + (i - 1) * step, lo + (i + 1) * step, 60);
        out.push([x, f(x)]);
      }
    }
    return out;
  }
  function gauss(u, u0, sg) { var z = (u - u0) / sg; return Math.exp(-0.5 * z * z); }
  function base() { return { init: function () { return { t: 0 }; }, step: function (s, p, dt) { s.t += dt; } }; }
  function mk(o) { var b = base(); for (var k in o) b[k] = o[k]; return b; }

  // ================================================================== Michelson
  var NU_WHITE = 1.0 / 5.7e-7, SIG_WHITE = 2.2e5;
  var Mich = mk({
    PARAMS: { lam: 6.328e-7, lam2: 0.0, np: 1.5168, tp: 1.0e-3, z0: 1.0e-3, src: 0.0, ins: 0.0, x: 1.0e-3, D: 2.0e-4 },
    VARS: ['inten', 'vis', 'delta'],
    delta: function (p, x, ins) {
      var i = ins === undefined || ins === null ? p.ins : ins;
      return 2.0 * (x - p.z0 - i * (p.np - 1.0) * p.tp);
    },
    vis_at: function (p, x, src, ins) {
      var s = Math.floor(src === undefined || src === null ? p.src : src), d = Mich.delta(p, x, ins);
      if (s === 0) return 1.0;
      if (s === 1) {
        if (p.lam2 <= 0) return 1.0;
        return Math.abs(Math.cos(PI * d * (1.0 / p.lam - 1.0 / p.lam2)));
      }
      return Math.exp(-2.0 * PI * PI * SIG_WHITE * SIG_WHITE * d * d);
    },
    inten_at: function (p, x, src, ins) {
      var s = Math.floor(src === undefined || src === null ? p.src : src), d = Mich.delta(p, x, ins), v;
      if (s === 0) return 0.5 * (1.0 - Math.cos(2 * PI * d / p.lam));
      if (s === 1) {
        if (p.lam2 <= 0) return 0.5 * (1.0 - Math.cos(2 * PI * d / p.lam));
        return 0.5 * (1.0 - 0.5 * (Math.cos(2 * PI * d / p.lam) + Math.cos(2 * PI * d / p.lam2)));
      }
      v = Math.exp(-2.0 * PI * PI * SIG_WHITE * SIG_WHITE * d * d);
      return 0.5 * (1.0 - v * Math.cos(2 * PI * NU_WHITE * d));
    },
    count: function (p, x0, dist) {
      var step = p.lam / 40.0, n = Math.floor(dist / step), prev2 = null, prev = null, c = 0, i, v;
      for (i = 0; i <= n; i++) {
        v = Mich.inten_at(p, x0 + i * step, 0, 0);
        if (prev2 !== null && prev > prev2 && prev >= v) c++;
        prev2 = prev; prev = v;
      }
      return c;
    },
    minima: function (p, lo, hi, step) {
      var n = Math.floor((hi - lo) / step), f = function (x) { return Mich.vis_at(p, x, 1, 0); }, vs = [], out = [], i;
      for (i = 0; i <= n; i++) vs.push(f(lo + i * step));
      for (i = 1; i < n; i++) {
        if (vs[i] < vs[i - 1] && vs[i] <= vs[i + 1]) out.push(ternMin(f, lo + (i - 1) * step, lo + (i + 1) * step, 60));
      }
      return out;
    },
    zpd: function (p, ins, lo, hi, step) {
      lo = lo === undefined ? 0.0 : lo; hi = hi === undefined ? 4e-3 : hi; step = step === undefined ? 2.5e-7 : step;
      var n = Math.floor((hi - lo) / step), f = function (x) { return Mich.vis_at(p, x, 2, ins); }, bi = 0, bv = -1.0, i, v;
      for (i = 0; i <= n; i++) { v = f(lo + i * step); if (v > bv) { bi = i; bv = v; } }
      return ternMax(f, lo + (bi - 1) * step, lo + (bi + 1) * step, 80);
    },
    view: function (s, p) {
      return { inten: Mich.inten_at(p, p.x), vis: Mich.vis_at(p, p.x), delta: Mich.delta(p, p.x) };
    },
    measure: function (p) {
      var n = Mich.count(p, p.z0 + 5e-4, p.D), lam = n > 0 ? 2.0 * p.D / n : 0.0, dl = 0.0, mins, sp, lm, z1, z2;
      if (p.lam2 > 0) {
        mins = Mich.minima(p, p.z0, p.z0 + 1.6e-3, 2e-6);
        if (mins.length >= 3) { sp = (mins[2] - mins[0]) / 2.0; lm = 0.5 * (p.lam + p.lam2); dl = lm * lm / (2.0 * sp); }
      }
      z1 = Mich.zpd(p, 0.0); z2 = Mich.zpd(p, 1.0);
      return { lam: lam, N: n, dlam: dl, dz: z2 - z1, n: 1.0 + (z2 - z1) / p.tp };
    }
  });

  // ================================================================== gas cell
  var Gas = mk({
    PARAMS: { lam: 6.328e-7, L: 0.25, dn1: 2.7651e-4, arms: 1.0, arch: 0.0, P: 0.0 },
    VARS: ['inten', 'phase'],
    phase: function (p, P) { return 2.0 * PI * p.arms * p.dn1 * P * p.L / p.lam; },
    inten_at: function (p, P) { return 0.5 * (1.0 + Math.cos(Gas.phase(p, P))); },
    fringes: function (p, P1) {
      var total = Gas.phase(p, P1) / (2 * PI), n = Math.floor(total * 40) + 40, step = P1 / n, vs = [], mx = [], i, m, prev;
      var f = function (q) { return Gas.inten_at(p, q); };
      for (i = 0; i <= n; i++) vs.push(f(i * step));
      for (i = 1; i < n; i++) {
        if (vs[i] > vs[i - 1] && vs[i] >= vs[i + 1]) mx.push(ternMax(f, (i - 1) * step, (i + 1) * step, 60));
      }
      m = mx.length;
      if (m === 0) return 0.0;
      prev = m >= 2 ? mx[m - 2] : 0.0;
      return m + (P1 - mx[m - 1]) / (mx[m - 1] - prev);
    },
    view: function (s, p) { return { inten: Gas.inten_at(p, p.P), phase: Gas.phase(p, p.P) }; },
    measure: function (p) {
      var N = Gas.fringes(p, 1.0);
      return { N: N, dn1: N * p.lam / (p.arms * p.L) };
    }
  });

  // ================================================================== spectra
  var specView = function () { return { sig: 0.0 }; };

  var Iodine = mk({
    PARAMS: { Te: 15769.01, we1: 125.69, wx1: 0.764, we0: 214.50, wx0: 0.607, vlo: 8.0, vhi: 40.0, sig: 3.0 },
    VARS: ['sig'], MODES: [], CONTROL: null, view: specView,
    nu_band: function (p, v) {
      return p.Te + p.we1 * (v + 0.5) - p.wx1 * Math.pow(v + 0.5, 2) - (p.we0 * 0.5 - p.wx0 * 0.25);
    },
    axis: function () { return { lo: 500.0, hi: 620.0, n: 6000, xlabel: 'Wavelength (nm)', unit: 'nm', ylabel: 'Absorbance', ymax: 1.15 }; },
    profile: function (x, p) {
      var nu = 1.0e7 / x, tot = 0.0, v = Math.floor(p.vlo), env;
      while (v <= Math.floor(p.vhi)) {
        env = Math.exp(-0.5 * Math.pow((v - 24.0) / 11.0, 2));
        tot += env * gauss(nu, Iodine.nu_band(p, v), p.sig);
        v += 1;
      }
      return tot;
    },
    lines: function (p) {
      var pk = peaks(function (x) { return Iodine.profile(x, p); }, 500.0, 620.0, 6000, 0.03);
      pk.sort(function (a, b) { return -a[0] - (-b[0]); });
      return pk.map(function (a, i) { return { k: i + 1, x: a[0], y: a[1] }; });
    },
    measure: function (p) {
      var ls = Iodine.lines(p), nus = ls.map(function (l) { return 1.0e7 / l.x; }), pts = [], i;
      for (i = 0; i < nus.length - 1; i++) pts.push([i + 0.5, nus[i + 1] - nus[i]]);
      return { wx1: -slope(pts) / 2.0, nbands: ls.length };
    }
  });

  var Rovib = mk({
    PARAMS: { we: 2990.946, wx: 52.8186, Be: 10.59341, ae: 0.30718, m1: 1.00782503, m2: 34.96885268, m3: 36.96590259,
      w2: 0.3198, T: 300.0, fwhm: 0.6, Jmax: 22.0, lo: 2600.0, hi: 3120.0 },
    VARS: ['sig'], MODES: [], CONTROL: null, view: specView,
    mu: function (m1, m2) { return m1 * m2 / (m1 + m2); },
    rho: function (p) {
      if (p.m3 <= 0) return 1.0;
      return Math.sqrt(Rovib.mu(p.m1, p.m2) / Rovib.mu(p.m1, p.m3));
    },
    B0: function (p) { return p.Be - 0.5 * p.ae; },
    B1: function (p) { return p.Be - 1.5 * p.ae; },
    line_list: function (p, minor) {
      var r = minor ? Rovib.rho(p) : 1.0, nu0 = (p.we - 2 * p.wx) * r, b0 = Rovib.B0(p) * r * r, b1 = Rovib.B1(p) * r * r;
      var w = minor ? p.w2 : 1.0, out = [], j, bz;
      for (j = 0; j <= Math.floor(p.Jmax); j++) {
        bz = Math.exp(-C2_CMK * b0 * j * (j + 1) / p.T);
        out.push([nu0 + (b1 + b0) * (j + 1) + (b1 - b0) * Math.pow(j + 1, 2), w * (j + 1) * bz]);
        if (j > 0) out.push([nu0 - (b1 + b0) * j + (b1 - b0) * j * j, w * j * bz]);
      }
      return out;
    },
    axis: function (p) {
      return { lo: p.lo, hi: p.hi, n: 8000, xlabel: 'Wavenumber (cm⁻¹)', unit: 'cm⁻¹', ylabel: 'Absorbance', ymax: 1.15 };
    },
    profile: function (x, p, mode, majorOnly) {
      var sg = p.fwhm / 2.354820045, tot = 0.0, sets = [Rovib.line_list(p, false)], a, i, ls;
      if (p.m3 > 0 && !majorOnly) sets.push(Rovib.line_list(p, true));
      for (a = 0; a < sets.length; a++) {
        ls = sets[a];
        for (i = 0; i < ls.length; i++) if (Math.abs(x - ls[i][0]) < 8 * sg) tot += ls[i][1] * gauss(x, ls[i][0], sg);
      }
      return tot;
    },
    lines: function (p) {
      var pk = peaks(function (x) { return Rovib.profile(x, p, 0, true); }, p.lo, p.hi, 8000, 0.02), gi = 0, best = -1, i, out = [];
      pk.sort(function (a, b) { return a[0] - b[0]; });
      if (pk.length < 3) return [];
      for (i = 0; i < pk.length - 1; i++) if (pk[i + 1][0] - pk[i][0] > best) { best = pk[i + 1][0] - pk[i][0]; gi = i; }
      for (i = gi + 1; i < pk.length; i++) out.push({ k: i - gi, x: pk[i][0], y: pk[i][1] });
      for (i = gi; i >= 0; i--) out.push({ k: -(gi - i + 1), x: pk[i][0], y: pk[i][1] });
      return out;
    },
    kforce: function (p, nu) {
      var mu = Rovib.mu(p.m1, p.m2) * AMU;
      return 4 * PI * PI * Math.pow(C_LIGHT * 100.0 * nu, 2) * mu;
    },
    measure: function (p) {
      var ls = Rovib.lines(p), d = {}, num = 0.0, den = 0.0, j, xj, b0, mid;
      ls.forEach(function (l) { d[l.k] = l.x; });
      for (j = 1; j < 6; j++) {
        if (d[j] !== undefined && d[-(j + 1)] !== undefined) { xj = j + 0.5; num += xj * (d[j] - d[-(j + 1)]); den += xj * xj; }
      }
      b0 = den ? num / den / 4.0 : 0.0;
      mid = 0.5 * ((d[1] === undefined ? 0.0 : d[1]) + (d[-1] === undefined ? 0.0 : d[-1]));
      return { B0: b0, numid: mid, kf: mid ? Rovib.kforce(p, mid) : 0.0 };
    }
  });

  var Raman = mk({
    PARAMS: { s1: 459.0, a1: 1.0, s2: 314.0, a2: 0.45, s3: 218.0, a3: 0.35, T: 300.0, lamL: 532.0, sig: 4.0 },
    VARS: ['sig'], MODES: [], CONTROL: null, view: specView,
    components: function (p) {
      var nuL = 1.0e7 / p.lamL, out = [], L = [[p.s1, p.a1], [p.s2, p.a2], [p.s3, p.a3]], i, s, a;
      for (i = 0; i < 3; i++) {
        s = L[i][0]; a = L[i][1];
        if (s > 0 && a > 0) {
          out.push([s, a]);
          out.push([-s, a * Math.pow((nuL + s) / (nuL - s), 4) * Math.exp(-C2_CMK * s / p.T)]);
        }
      }
      return out;
    },
    axis: function (p) {
      var top = Math.max(p.s1, p.s2, p.s3) + 150.0;
      return { lo: -top, hi: top, n: 6000, xlabel: 'Raman shift (cm⁻¹)', unit: 'cm⁻¹', ylabel: 'Counts (relative)', ymax: 1.15 };
    },
    profile: function (x, p) {
      var tot = 0.0, c = Raman.components(p), i;
      for (i = 0; i < c.length; i++) tot += c[i][1] * gauss(x, c[i][0], p.sig);
      return tot;
    },
    lines: function (p) {
      var ax = Raman.axis(p), pk = peaks(function (x) { return Raman.profile(x, p); }, ax.lo, ax.hi, ax.n, 0.002);
      var st = pk.filter(function (a) { return a[0] > 0; }).sort(function (a, b) { return -a[1] - (-b[1]); });
      var out = st.map(function (a, i) { return { k: i + 1, x: a[0], y: a[1] }; }), best, near;
      if (st.length) {
        best = st[0][0];
        near = pk.filter(function (a) { return a[0] < 0 && Math.abs(a[0] + best) < 25.0; });
        if (near.length) out.push({ k: -1, x: near[0][0], y: near[0][1] });
      }
      return out;
    },
    measure: function (p) {
      var ls = Raman.lines(p), d = {}, s1 = 0.0, T = 0.0, nuL, s, ratio;
      ls.forEach(function (l) { d[l.k] = l; });
      if (d[1]) s1 = d[1].x;
      if (d[1] && d[-1] && d[-1].y > 0) {
        nuL = 1.0e7 / p.lamL; s = d[1].x;
        ratio = Math.pow((nuL + s) / (nuL - s), 4) * d[1].y / d[-1].y;
        T = ratio > 1 ? C2_CMK * s / Math.log(ratio) : 0.0;
      }
      return { s1: s1, T: T };
    }
  });

  var Fluor = mk({
    PARAMS: { abs: 347.5, em: 450.0, sa: 2000.0, se: 1500.0 },
    VARS: ['sig'], MODES: ['Absorption', 'Emission'], CONTROL: null, view: specView,
    axis: function (p) {
      var lo = Math.floor((Math.min(p.abs, p.em) - 90.0) / 10.0) * 10.0, hi = Math.ceil((Math.max(p.abs, p.em) + 110.0) / 10.0) * 10.0;
      return { lo: lo, hi: hi, n: 4000, xlabel: 'Wavelength (nm)', unit: 'nm', ylabel: 'Signal (relative)', ymax: 1.15 };
    },
    profile: function (x, p, mode) {
      var nu = 1.0e7 / x;
      if (Math.floor(mode || 0) === 0) return gauss(nu, 1.0e7 / p.abs, p.sa);
      return gauss(nu, 1.0e7 / p.em, p.se);
    },
    lines: function (p, mode) {
      var ax = Fluor.axis(p), m = Math.floor(mode || 0);
      var pk = peaks(function (x) { return Fluor.profile(x, p, m); }, ax.lo, ax.hi, ax.n, 0.3);
      return pk.slice(0, 1).map(function (a) { return { k: m + 1, x: a[0], y: a[1] }; });
    },
    measure: function (p) {
      var a = Fluor.lines(p, 0), e = Fluor.lines(p, 1), xa = a.length ? a[0].x : 0.0, xe = e.length ? e[0].x : 0.0;
      return { abs: xa, em: xe, stokes: (xa && xe) ? (1.0e7 / xa - 1.0e7 / xe) : 0.0 };
    }
  });

  var Tauc = mk({
    PARAMS: { Eg: 2.42, B2: 1.7e11, t: 4.0e-5 },
    VARS: ['sig'], MODES: [], CONTROL: null, view: specView,
    alpha: function (p, E) { return E > p.Eg ? Math.sqrt(p.B2 * (E - p.Eg)) / E : 0.0; },
    axis: function (p) {
      var edge = HC_EV_NM / p.Eg;
      return { lo: Math.floor(edge * 0.75 / 10.0) * 10.0, hi: Math.ceil(edge * 1.25 / 10.0) * 10.0, n: 3000,
        xlabel: 'Wavelength (nm)', unit: 'nm', ylabel: 'Transmittance', ymax: 1.05 };
    },
    profile: function (x, p) { return Math.exp(-Tauc.alpha(p, HC_EV_NM / x) * p.t); },
    measure: function (p) {
      var ax = Tauc.axis(p), pts = [], i, e, T, a, lc;
      var x90 = bisect(function (x) { return Tauc.profile(x, p) - 0.9; }, ax.lo, ax.hi);
      var x03 = bisect(function (x) { return Tauc.profile(x, p) - 0.03; }, ax.lo, ax.hi);
      var e1 = HC_EV_NM / x90, e2 = HC_EV_NM / x03;
      for (i = 0; i < 12; i++) {
        e = e1 + (e2 - e1) * i / 11.0; T = Tauc.profile(HC_EV_NM / e, p); a = -Math.log(T) / p.t;
        pts.push([e, Math.pow(a * e, 2)]);
      }
      lc = line(pts);
      return { Eg: lc[0] ? -lc[1] / lc[0] : 0.0 };
    }
  });

  var Varshni = mk({
    PARAMS: { Eg0: 1.519, al: 5.405e-4, be: 204.0, T: 300.0 },
    VARS: ['sig'], MODES: [], view: specView,
    CONTROL: { param: 'T', label: 'Sample temperature', unit: 'K', values: [300.0, 77.0], digits: 0, scale: 1.0 },
    gap: function (p, T) { return p.Eg0 - p.al * T * T / (T + p.be); },
    axis: function () { return { lo: 780.0, hi: 920.0, n: 3000, xlabel: 'Wavelength (nm)', unit: 'nm', ylabel: 'Luminescence (relative)', ymax: 1.15 }; },
    profile: function (x, p) { return gauss(HC_EV_NM / x, Varshni.gap(p, p.T), 0.8 * KB_EV * p.T); },
    lines: function (p) {
      var ax = Varshni.axis(p), pk = peaks(function (x) { return Varshni.profile(x, p); }, ax.lo, ax.hi, ax.n, 0.3);
      return pk.slice(0, 1).map(function (a) { return { k: 1, x: a[0], y: a[1] }; });
    },
    measure: function (p) {
      var e = {}, Ts = [300.0, 77.0], i, q, ls;
      for (i = 0; i < 2; i++) {
        q = {}; for (var k in p) q[k] = p[k]; q.T = Ts[i];
        ls = Varshni.lines(q); e[Ts[i]] = ls.length ? HC_EV_NM / ls[0].x : 0.0;
      }
      return { E300: e[300], E77: e[77], dE: e[77] - e[300] };
    }
  });

  var Decay = mk({
    PARAMS: { tau: 3.0e-3, V0: 1.0 },
    VARS: ['sig'], MODES: [], CONTROL: null, view: specView,
    axis: function (p) { return { lo: 0.0, hi: 6000.0 * p.tau, n: 1200, xlabel: 'Time (ms)', unit: 'ms', ylabel: 'Signal (V)', ymax: 1.1 * p.V0 }; },
    profile: function (x, p) { return p.V0 * Math.exp(-x * 1.0e-3 / p.tau); },
    measure: function (p) {
      var ax = Decay.axis(p), t = bisect(function (x) { return Decay.profile(x, p) - p.V0 / Math.E; }, 0.0, ax.hi);
      return { tau: t * 1.0e-3 };
    }
  });

  var Glow = mk({
    PARAMS: { E: 1.0, s: 1.0e12, beta: 1.0, T0: 300.0 },
    VARS: ['sig'], MODES: [], view: specView,
    CONTROL: { param: 'beta', label: 'Heating rate', unit: 'K/s', values: [0.5, 1.0, 2.0, 4.0], digits: 1, scale: 1.0 },
    _f: function (p, T) { return Math.exp(-p.E / (KB_EV * T)); },
    integral: function (p, T) {
      if (T <= p.T0) return 0.0;
      var n = 2 * Math.max(1, Math.ceil((T - p.T0) / 1.0)), h = (T - p.T0) / n, s = Glow._f(p, p.T0) + Glow._f(p, T), i;
      for (i = 1; i < n; i++) s += (i % 2 ? 4 : 2) * Glow._f(p, p.T0 + i * h);
      return s * h / 3.0;
    },
    axis: function () { return { lo: 300.0, hi: 520.0, n: 220, xlabel: 'Temperature (K)', unit: 'K', ylabel: 'TL intensity (relative)', ymax: 1.15 }; },
    profile: function (x, p) { return p.s * Glow._f(p, x) * Math.exp(-(p.s / p.beta) * Glow.integral(p, x)); },
    ln_i: function (p, T) { return Math.log(p.s) - p.E / (KB_EV * T) - (p.s / p.beta) * Glow.integral(p, T); },
    peak: function (p) {
      var g = function (T) { return Glow.ln_i(p, T + 0.05) - Glow.ln_i(p, T - 0.05); };
      return bisect(g, p.T0 + 10.0, 520.0, 80);
    },
    lines: function (p) { var t = Glow.peak(p); return [{ k: 1, x: t, y: Glow.profile(t, p) }]; },
    measure: function (p) {
      var pts = [], bs = [0.5, 1.0, 2.0, 4.0], i, q, tm, k, q1;
      for (i = 0; i < 4; i++) {
        q = {}; for (k in p) q[k] = p[k]; q.beta = bs[i];
        tm = Glow.peak(q); pts.push([1.0 / tm, Math.log(tm * tm / bs[i])]);
      }
      q1 = {}; for (k in p) q1[k] = p[k]; q1.beta = 1.0;
      return { E: slope(pts) * KB_EV, Tm1: Glow.peak(q1) };
    }
  });

  var Beer = mk({
    PARAMS: { eps: 116000.0, lam0: 529.8, sg: 600.0, c: 5.0e-6, l: 1.0 },
    VARS: ['sig'], MODES: [], view: specView,
    CONTROL: { param: 'c', label: 'Concentration', unit: 'µM', values: [1e-6, 2e-6, 3e-6, 4e-6, 5e-6, 6e-6], digits: 0, scale: 1.0e6 },
    axis: function () { return { lo: 420.0, hi: 640.0, n: 2200, xlabel: 'Wavelength (nm)', unit: 'nm', ylabel: 'Absorbance', ymax: 0.8 }; },
    profile: function (x, p) { return p.eps * p.c * p.l * gauss(1.0e7 / x, 1.0e7 / p.lam0, p.sg); },
    lines: function (p) {
      var ax = Beer.axis(p), pk = peaks(function (x) { return Beer.profile(x, p); }, ax.lo, ax.hi, ax.n, 0.3);
      return pk.slice(0, 1).map(function (a) { return { k: 1, x: a[0], y: a[1] }; });
    },
    measure: function (p) {
      var cs = [1e-6, 2e-6, 3e-6, 4e-6, 5e-6], num = 0.0, den = 0.0, i, q, k, ls;
      for (i = 0; i < cs.length; i++) {
        q = {}; for (k in p) q[k] = p[k]; q.c = cs[i];
        ls = Beer.lines(q); num += cs[i] * ls[0].y; den += cs[i] * cs[i];
      }
      return { eps: den ? num / den / p.l : 0.0 };
    }
  });

  // ================================================================== textbook + calcs
  function byK(rs) {
    var d = {}; rows(rs, ['k', 'x']).forEach(function (r) { d[r[0]] = r[1]; }); return d;
  }
  function meanWhere(rs, kk, cond) { return mean(rows(rs, kk).filter(cond).map(function (r) { return r[1]; })); }

  H.register({
    K: { msc_michelson: Mich, msc_gascell: Gas, msc_iodine: Iodine, msc_rovib: Rovib, msc_raman: Raman, msc_fluor: Fluor,
      msc_tauc: Tauc, msc_varshni: Varshni, msc_decay: Decay, msc_glow: Glow, msc_beer: Beer },
    TEXTBOOK: {
      msc_mich_lam: function (p) { return p.lam; },
      msc_mich_dline: function (p) { return Math.abs(p.lam2 - p.lam); },
      msc_mich_n: function (p) { return p.np; },
      msc_gas_dn1: function (p) { return p.dn1; },
      msc_iod_wx: function (p) { return p.wx1; },
      msc_rv_b0: function (p) { return p.Be - 0.5 * p.ae; },
      msc_rv_kf: function (p) { return Rovib.kforce(p, p.we - 2 * p.wx); },
      msc_ram_s1: function (p) { return p.s1; },
      msc_fl_stokes: function (p) { return 1.0e7 / p.abs - 1.0e7 / p.em; },
      msc_tauc_eg: function (p) { return p.Eg; },
      msc_vs_dE: function (p) { return Varshni.gap(p, 77.0) - Varshni.gap(p, 300.0); },
      msc_dec_tau: function (p) { return p.tau; },
      msc_tl_E: function (p) { return p.E; },
      msc_beer_eps: function (p) { return p.eps; }
    },
    CALCS: {
      msc_c_mich_lam: { label: 'wavelength', unit: 'm', needs: ['d', 'N'],
        fn: function (r) { return mean(rows(r, ['d', 'N']).filter(function (x) { return x[1] > 0; }).map(function (x) { return 2.0 * x[0] / x[1]; })); } },
      msc_c_mich_dline: { label: 'D-line separation', unit: 'm', needs: ['k', 'x'],
        fn: function (r, p) {
          var pts = rows(r, ['k', 'x']).sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
          var sp = slope(pts), lm;
          if (sp <= 0 || p.lam2 <= 0) return 0.0;
          lm = 0.5 * (p.lam + p.lam2);
          return lm * lm / (2.0 * sp);
        } },
      msc_c_mich_n: { label: 'n of the plate', unit: '', needs: ['k', 'x'],
        fn: function (r, p) {
          var z1 = meanWhere(r, ['k', 'x'], function (x) { return x[0] === 0; });
          var z2 = meanWhere(r, ['k', 'x'], function (x) { return x[0] === 1; });
          if (!z1 || !z2 || p.tp <= 0) return 0.0;
          return 1.0 + (z2 - z1) / p.tp;
        } },
      msc_c_gas_dn1: { label: 'n - 1 at 1 atm', unit: '', needs: ['P', 'N'],
        fn: function (r, p) {
          var pts = rows(r, ['P', 'N']), num = 0, den = 0, i;
          for (i = 0; i < pts.length; i++) { num += pts[i][0] * pts[i][1]; den += pts[i][0] * pts[i][0]; }
          if (den <= 0 || p.arms <= 0 || p.L <= 0) return 0.0;
          return num / den * p.lam / (p.arms * p.L);
        } },
      msc_c_iod_wx: { label: "wexe'", unit: 'cm-1', needs: ['k', 'x'],
        fn: function (r) {
          var pts = rows(r, ['k', 'x']).sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
          var nus = pts.filter(function (x) { return x[1] > 0; }).map(function (x) { return [x[0], 1.0e7 / x[1]]; }), sl = [], i;
          for (i = 0; i < nus.length - 1; i++) {
            if (Math.abs(nus[i + 1][0] - nus[i][0] - 1.0) < 1e-9) sl.push([0.5 * (nus[i][0] + nus[i + 1][0]), nus[i + 1][1] - nus[i][1]]);
          }
          return -slope(sl) / 2.0;
        } },
      msc_c_rot_b: { label: 'B0', unit: 'cm-1', needs: ['k', 'x'],
        fn: function (r) {
          var d = byK(r), num = 0, den = 0, j, xj;
          for (j = 1; j < 8; j++) {
            if (d[j] !== undefined && d[-(j + 1)] !== undefined) { xj = j + 0.5; num += xj * (d[j] - d[-(j + 1)]); den += xj * xj; }
          }
          return den ? num / den / 4.0 : 0.0;
        } },
      msc_c_force: { label: 'force constant', unit: 'N/m', needs: ['k', 'x'],
        fn: function (r, p) {
          var d = byK(r);
          if (d[1] !== undefined && d[-1] !== undefined) return Rovib.kforce(p, 0.5 * (d[1] + d[-1]));
          return 0.0;
        } },
      msc_c_raman_s: { label: 'Raman shift', unit: 'cm-1', needs: ['k', 'x'],
        fn: function (r) { return meanWhere(r, ['k', 'x'], function (x) { return x[0] === 1; }); } },
      msc_c_stokes: { label: 'Stokes shift', unit: 'cm-1', needs: ['k', 'x'],
        fn: function (r) {
          var xa = meanWhere(r, ['k', 'x'], function (x) { return x[0] === 1; });
          var xe = meanWhere(r, ['k', 'x'], function (x) { return x[0] === 2; });
          return (xa > 0 && xe > 0) ? 1.0e7 / xa - 1.0e7 / xe : 0.0;
        } },
      msc_c_tauc: { label: 'optical gap', unit: 'eV', needs: ['x', 'y'],
        fn: function (r, p) {
          var pts = [], lc;
          rows(r, ['x', 'y']).forEach(function (q) {
            var e, a;
            if (q[0] > 0 && q[1] > 0.005 && q[1] < 0.995 && p.t > 0) {
              e = HC_EV_NM / q[0]; a = -Math.log(q[1]) / p.t; pts.push([e, Math.pow(a * e, 2)]);
            }
          });
          lc = line(pts);
          return lc[0] ? -lc[1] / lc[0] : 0.0;
        } },
      msc_c_varshni: { label: 'gap shift', unit: 'eV', needs: ['c', 'x'],
        fn: function (r) {
          var rr = rows(r, ['c', 'x']);
          var a = mean(rr.filter(function (x) { return x[0] === 77.0 && x[1] > 0; }).map(function (x) { return HC_EV_NM / x[1]; }));
          var b = mean(rr.filter(function (x) { return x[0] === 300.0 && x[1] > 0; }).map(function (x) { return HC_EV_NM / x[1]; }));
          return (a && b) ? a - b : 0.0;
        } },
      msc_c_decay: { label: 'lifetime', unit: 's', needs: ['x', 'y'],
        fn: function (r) {
          var pts = rows(r, ['x', 'y']).filter(function (x) { return x[1] > 0; }).map(function (x) { return [x[0], Math.log(x[1])]; });
          var m = slope(pts);
          return m < 0 ? -1.0e-3 / m : 0.0;
        } },
      msc_c_glow: { label: 'trap depth', unit: 'eV', needs: ['c', 'x'],
        fn: function (r) {
          var pts = rows(r, ['c', 'x']).filter(function (x) { return x[1] > 0 && x[0] > 0; })
            .map(function (x) { return [1.0 / x[1], Math.log(x[1] * x[1] / x[0])]; });
          return slope(pts) * KB_EV;
        } },
      msc_c_beer: { label: 'molar absorptivity', unit: 'L/(mol cm)', needs: ['c', 'y'],
        fn: function (r, p) {
          var pts = rows(r, ['c', 'y']), num = 0, den = 0, i;
          for (i = 0; i < pts.length; i++) { num += pts[i][0] * pts[i][1]; den += pts[i][0] * pts[i][0]; }
          return (den && p.l) ? num / den / p.l : 0.0;
        } }
    }
  });
})(typeof window !== 'undefined' ? window : this);
