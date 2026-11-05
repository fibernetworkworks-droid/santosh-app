/* Prayogshala kernel pack: UNDERGRADUATE WAVE OPTICS - the JavaScript twin of
   server/app/prayog/packs/optics_ug.py, step for step. Nine kernels: spectrometer (prism on the spectrometer table,
   Cauchy dispersion, minimum deviation by scanning the real trace, the prism's angle from the two reflected beams),
   grating (the N-slit intensity, its maximum, its first dark edge, dispersive and Rayleigh resolving power),
   newtonrings, airwedge, doubleslit, gratingscreen, fibrecone, fresnelrefl (Brewster) and polarimeter.
   SI, deterministic: no randomness, no wall clock. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels;
  if (!H) throw new Error('kernels.js must load before its packs');
  var PI = Math.PI, R2D = 180 / PI;

  // ------------------------------------------------------------------ small helpers
  function ternMin(f, lo, hi, iters) {
    var n = iters === undefined ? 120 : iters, a1, a2, i;
    for (i = 0; i < n; i++) {
      a1 = lo + (hi - lo) / 3.0;
      a2 = hi - (hi - lo) / 3.0;
      if (f(a1) < f(a2)) hi = a2; else lo = a1;
    }
    return (lo + hi) / 2.0;
  }
  function ternMax(f, lo, hi, iters) { return ternMin(function (x) { return -f(x); }, lo, hi, iters); }
  function bisect(f, lo, hi, iters) {
    var n = iters === undefined ? 100 : iters, flo = f(lo), mid, i;
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

  // ================================================================== the spectrometer
  var Spectrometer = {
    PARAMS: { A: PI / 3, n0: 1.504518, nB: 4.2211e-15, lam: 5.893e-7, i: 0.8, tel: 0.0, side: 0.12 },
    VARS: ['rays', 'dev', 'e', 'r1', 'tir', 'refl_sep'],
    nlam: function (p) { return p.n0 + p.nB / (p.lam * p.lam); },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    angles: function (p, i) {
      var n = Spectrometer.nlam(p), x1 = Math.sin(i) / n, r1, r2, x2, e;
      if (Math.abs(x1) > 1) return null;
      r1 = Math.asin(x1);
      r2 = p.A - r1;
      x2 = n * Math.sin(r2);
      if (Math.abs(x2) > 1) return null;
      e = Math.asin(x2);
      return [r1, r2, e, i + e - p.A];
    },
    reflSep: function (p) {
      var h = p.A / 2, n1 = [-Math.cos(h), Math.sin(h)], n2 = [Math.cos(h), Math.sin(h)], d = [1.0, 0.0];
      var out = [], i, nn, dot, c;
      for (i = 0; i < 2; i++) {
        nn = i ? n2 : n1;
        dot = d[0] * nn[0] + d[1] * nn[1];
        out.push([d[0] - 2 * dot * nn[0], d[1] - 2 * dot * nn[1]]);
      }
      c = out[0][0] * out[1][0] + out[0][1] * out[1][1];
      return Math.acos(Math.max(-1, Math.min(1, c)));
    },
    view: function (s, p) {
      var A = p.A, S = p.side, apex = [0.0, S * Math.cos(A / 2)], bl = [-S * Math.sin(A / 2), 0.0], br = [S * Math.sin(A / 2), 0.0];
      var ang = Spectrometer.angles(p, p.i), hit1 = [(apex[0] + bl[0]) / 2, (apex[1] + bl[1]) / 2], face2, start, rays, dev;
      if (ang === null) {
        return { rays: [{ p: [[hit1[0] - 0.12, hit1[1]], hit1], v: 0 }], dev: 0.0, e: 0.0, r1: 0.0, tir: 1.0,
          refl_sep: Spectrometer.reflSep(p) };
      }
      dev = ang[3];
      face2 = [(apex[0] + br[0]) / 2, (apex[1] + br[1]) / 2];
      start = [hit1[0] - 0.12 * Math.cos(p.i), hit1[1] - 0.12 * Math.sin(p.i)];
      rays = [{ p: [start, hit1, face2, [face2[0] + 0.16, face2[1] - 0.16 * Math.tan(dev)]], v: 0 }];
      return { rays: rays, dev: dev, e: ang[2], r1: ang[0], tir: 0.0, refl_sep: Spectrometer.reflSep(p) };
    },
    measure: function (p) {
      var best = 10.0, bi = 0.0, k = 0, i, a;
      while (k <= 6000) {
        i = (25.0 + k * 0.01) / R2D;
        a = Spectrometer.angles(p, i);
        if (a !== null && a[3] < best) { best = a[3]; bi = i; }
        k += 1;
      }
      return { dm: best, i_min: bi, refl_sep: Spectrometer.reflSep(p) };
    }
  };

  // ================================================================== the plane grating
  var Grating = {
    PARAMS: { d: 1.6933333e-6, a: 8.4666667e-7, N: 5906.0, lam: 5.893e-7, m: 1.0, tel: 0.0 },
    VARS: ['inten', 'theta', 'tir'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    rulings: function (p) { return Math.floor(p.N + 0.5); },
    detune: function (th, p) {
      var g = PI * p.d * Math.sin(th) / p.lam;
      return g - PI * Math.floor(g / PI + 0.5);
    },
    intenAt: function (th, p) {
      var u = Grating.detune(th, p), N = Grating.rulings(p), su = Math.sin(u), arr, b, sc;
      arr = Math.abs(su) < 1e-12 ? N : Math.sin(N * u) / su;
      b = PI * p.a * Math.sin(th) / p.lam;
      sc = Math.abs(b) < 1e-12 ? 1.0 : Math.sin(b) / b;
      return sc * sc * arr * arr / (N * N);
    },
    orderTheta: function (p, m, lam) {
      var q = lam === undefined || lam === null ? p : Object.assign({}, p, { lam: lam });
      var s = m * q.lam / q.d, th0, w;
      if (Math.abs(s) >= 1) return null;
      th0 = Math.asin(s);
      w = 0.5 * q.lam / (Grating.rulings(q) * q.d * Math.cos(th0));
      return ternMax(function (th) { return Grating.intenAt(th, q); }, th0 - w, th0 + w);
    },
    firstZero: function (p, m) {
      var th = Grating.orderTheta(p, m), N, wz, f, lo, hi;
      if (th === null) return null;
      N = Grating.rulings(p);
      wz = p.lam / (N * p.d * Math.cos(th));
      f = function (x) { return Math.sin(N * Grating.detune(x, p)); };
      lo = th + 1e-3 * wz; hi = th + 1.6 * wz;
      if (f(lo) * f(hi) > 0) return th + wz;
      return bisect(f, lo, hi);
    },
    resolving: function (p, m) {
      var th = Grating.orderTheta(p, m), z = Grating.firstZero(p, m), gap, f, dl, lim, hi;
      if (th === null || z === null) return null;
      gap = z - th;
      f = function (dl2) { return (Grating.orderTheta(p, m, p.lam + dl2) - th) - gap; };
      lim = p.d / m - p.lam;
      hi = Math.min(p.lam * 0.5, lim * 0.9);
      if (hi <= 0 || f(hi) < 0) return null;
      dl = bisect(f, 0.0, hi);
      return { dlam: dl, rp: dl > 0 ? p.lam / dl : 0.0 };
    },
    view: function (s, p) {
      var th = Grating.orderTheta(p, p.m);
      return { inten: Grating.intenAt(p.tel, p), theta: th === null ? 0.0 : th, tir: th === null ? 1.0 : 0.0 };
    },
    measure: function (p) {
      var th = Grating.orderTheta(p, p.m), t1 = Grating.orderTheta(p, 1.0), t2 = Grating.orderTheta(p, 2.0);
      var h = p.lam * 1e-2, a = Grating.orderTheta(p, p.m, p.lam + h), b = Grating.orderTheta(p, p.m, p.lam - h);
      var disp = (a !== null && b !== null) ? (a - b) / (2 * h) : 0.0;
      var R = Grating.resolving(p, p.m) || { dlam: 0.0, rp: 0.0 };
      return { theta: th === null ? 0.0 : th, theta1: t1 === null ? 0.0 : t1, theta2: t2 === null ? 0.0 : t2,
        disp: disp, rp: R.rp, dlam: R.dlam };
    }
  };

  // ================================================================== Newton's rings
  var NewtonRings = {
    PARAMS: { R: 0.1, lam: 5.893e-7, mu: 1.0, n: 10.0, I0: 1.0, r: 0.0 },
    VARS: ['inten', 'tfilm', 'rn', 'dn'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    thickness: function (r, p) { return r * r / (2 * p.R); },
    intenAt: function (r, p) {
      var d = 2 * PI * (2 * p.mu * NewtonRings.thickness(r, p)) / p.lam + PI, c = Math.cos(d / 2);
      return 4 * p.I0 * c * c;
    },
    darkR: function (p, n) {
      var k = p.lam * p.R / Math.max(p.mu, 1e-12);
      var lo = Math.sqrt(Math.max(n - 0.45, 0.0) * k), hi = Math.sqrt((n + 0.45) * k);
      return ternMin(function (r) { return NewtonRings.intenAt(r, p); }, lo, hi);
    },
    view: function (s, p) {
      var r = NewtonRings.darkR(p, p.n);
      return { inten: NewtonRings.intenAt(p.r, p), tfilm: NewtonRings.thickness(p.r, p), rn: r, dn: 2 * r };
    },
    measure: function (p) { var r = NewtonRings.darkR(p, p.n); return { rn: r, dn: 2 * r }; }
  };

  // ================================================================== the air wedge
  var AirWedge = {
    PARAMS: { lam: 5.893e-7, mu: 1.0, ts: 5e-5, L: 0.05, n: 10.0, x: 0.0, I0: 1.0 },
    VARS: ['inten', 'tfilm', 'xn', 'beta'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    thickness: function (x, p) { return p.ts * x / p.L; },
    intenAt: function (x, p) {
      var d = 2 * PI * (2 * p.mu * AirWedge.thickness(x, p)) / p.lam + PI, c = Math.cos(d / 2);
      return 4 * p.I0 * c * c;
    },
    darkX: function (p, n) {
      var k = p.lam * p.L / (2 * p.mu * Math.max(p.ts, 1e-12));
      var lo = Math.max(n - 0.45, 0.0) * k, hi = (n + 0.45) * k;
      return ternMin(function (x) { return AirWedge.intenAt(x, p); }, lo, hi);
    },
    view: function (s, p) {
      var x = AirWedge.darkX(p, p.n), b = (AirWedge.darkX(p, p.n + 10) - x) / 10.0;
      return { inten: AirWedge.intenAt(p.x, p), tfilm: AirWedge.thickness(p.x, p), xn: x, beta: b };
    },
    measure: function (p) {
      var x = AirWedge.darkX(p, p.n);
      return { xn: x, beta: (AirWedge.darkX(p, p.n + 10) - x) / 10.0 };
    }
  };

  // ================================================================== the double slit
  var DoubleSlit = {
    PARAMS: { a: 4e-5, d: 5e-4, D: 1.5, lam: 6.328e-7, I0: 1.0, x: 0.0, k: 4.0 },
    VARS: ['inten', 'beta', 'xk'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    intenAt: function (x, p) {
      var st = Math.sin(Math.atan2(x, p.D)), b = PI * p.a * st / p.lam, g = PI * p.d * st / p.lam, sc, c;
      sc = Math.abs(b) < 1e-12 ? 1.0 : Math.sin(b) / b;
      c = Math.cos(g);
      return p.I0 * sc * sc * c * c;
    },
    brightX: function (p, k) {
      var beta = p.lam * p.D / p.d, x0 = k * beta;
      return ternMax(function (x) { return DoubleSlit.intenAt(x, p); }, x0 - 0.4 * beta, x0 + 0.4 * beta);
    },
    view: function (s, p) {
      var k = Math.max(1.0, Math.floor(p.k + 0.5)), xp = DoubleSlit.brightX(p, k), xm = DoubleSlit.brightX(p, -k);
      return { inten: DoubleSlit.intenAt(p.x, p), beta: (xp - xm) / (2 * k), xk: xp };
    },
    measure: function (p) { var v = DoubleSlit.view({}, p); return { beta: v.beta, xk: v.xk }; }
  };

  // ================================================================== grating + screen
  var GratingScreen = {
    PARAMS: { d: 1.6666667e-6, a: 8.3333333e-7, N: 1000.0, D: 0.5, lam: 6.328e-7, m: 1.0, x: 0.0 },
    VARS: ['inten', 'theta', 'xm', 'tir'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    gparams: function (p, m) {
      return Object.assign({}, Grating.PARAMS, { d: p.d, a: p.a, N: p.N, lam: p.lam }, { m: m });
    },
    orderTheta: function (p, m) { return Grating.orderTheta(GratingScreen.gparams(p, m), m); },
    spotX: function (p, m) {
      var th = GratingScreen.orderTheta(p, m);
      return th === null ? null : p.D * Math.tan(th);
    },
    view: function (s, p) {
      var th = GratingScreen.orderTheta(p, p.m), g = GratingScreen.gparams(p, p.m);
      return { inten: Grating.intenAt(Math.atan2(p.x, p.D), g), theta: th === null ? 0.0 : th,
        xm: th === null ? 0.0 : p.D * Math.tan(th), tir: th === null ? 1.0 : 0.0 };
    },
    measure: function (p) {
      var out = {}, ms = [1.0, 2.0], i, x;
      for (i = 0; i < ms.length; i++) {
        x = GratingScreen.spotX(p, ms[i]);
        out['x' + ms[i].toFixed(0)] = x === null ? 0.0 : x;
      }
      x = GratingScreen.spotX(p, p.m);
      out.xm = x === null ? 0.0 : x;
      return out;
    }
  };

  // ================================================================== optical fibre
  var FibreCone = {
    PARAMS: { n1: 1.492, n2: 1.402, dz: 0.02, dcore: 0.001, nout: 1.0 },
    VARS: ['na', 'theta_a', 'W'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    thetaA: function (p) {
      var na = Math.sqrt(Math.max(p.n1 * p.n1 - p.n2 * p.n2, 0.0));
      return Math.asin(Math.min(1.0, na / p.nout));
    },
    spot: function (p) { return p.dcore + 2 * p.dz * Math.tan(FibreCone.thetaA(p)); },
    view: function (s, p) {
      var W = FibreCone.spot(p), th = Math.atan2(W - p.dcore, 2 * p.dz);
      return { na: Math.sin(th) * p.nout, theta_a: FibreCone.thetaA(p), W: W };
    },
    measure: function (p) {
      var W = FibreCone.spot(p), th = Math.atan2(W - p.dcore, 2 * p.dz);
      return { W: W, na: Math.sin(th) * p.nout };
    }
  };

  // ================================================================== Brewster's angle
  var FresnelRefl = {
    PARAMS: { n: 1.5168, nout: 1.0, th: 0.9, I0: 1.0 },
    VARS: ['Rs', 'Rp', 'Itot', 'thb'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    coef: function (th, p) {
      var n1 = p.nout, n2 = p.n, st = n1 * Math.sin(th) / n2, ct, ci, rs, rp;
      if (Math.abs(st) > 1) return [1.0, 1.0];
      ct = Math.sqrt(Math.max(1 - st * st, 0.0));
      ci = Math.cos(th);
      rs = (n1 * ci - n2 * ct) / (n1 * ci + n2 * ct);
      rp = (n1 * ct - n2 * ci) / (n1 * ct + n2 * ci);
      return [rs * rs, rp * rp];
    },
    brewster: function (p) { return ternMin(function (th) { return FresnelRefl.coef(th, p)[1]; }, 0.05, 1.5); },
    view: function (s, p) {
      var c = FresnelRefl.coef(p.th, p);
      return { Rs: c[0], Rp: c[1], Itot: p.I0 * (c[0] + c[1]) / 2, thb: FresnelRefl.brewster(p) };
    },
    measure: function (p) {
      var th = FresnelRefl.brewster(p), c = FresnelRefl.coef(th, p);
      return { thb: th, Rp_min: c[1], Rs_at: c[0] };
    }
  };

  // ================================================================== the polarimeter
  var Polarimeter = {
    PARAMS: { alpha: 66.5, Ldm: 2.0, conc: 0.1, lam: 5.893e-7, beta: 0.05236, phi: 1.5708, I0: 1.0 },
    VARS: ['il', 'ir', 'itot', 'match'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    rotation: function (p) { return p.alpha * p.Ldm * p.conc / R2D; },
    halves: function (p, phi, conc) {
      var th = p.alpha * p.Ldm * conc / R2D, cl = Math.cos(phi - th - p.beta), cr = Math.cos(phi - th + p.beta);
      return [p.I0 * cl * cl, p.I0 * cr * cr];
    },
    matchAt: function (p, conc) {
      return ternMin(function (phi) { var h = Polarimeter.halves(p, phi, conc); return h[0] + h[1]; },
        PI / 2 - 0.2, PI / 2 + 1.2);
    },
    view: function (s, p) {
      var h = Polarimeter.halves(p, p.phi, p.conc);
      return { il: h[0], ir: h[1], itot: h[0] + h[1], match: Polarimeter.matchAt(p, p.conc) };
    },
    measure: function (p) {
      var zero = Polarimeter.matchAt(p, 0.0), full = Polarimeter.matchAt(p, p.conc);
      return { phi0: zero, phi: full, rot: full - zero };
    }
  };

  H.register({
    K: { spectrometer: Spectrometer, grating: Grating, newtonrings: NewtonRings, airwedge: AirWedge,
      doubleslit: DoubleSlit, gratingscreen: GratingScreen, fibrecone: FibreCone, fresnelrefl: FresnelRefl,
      polarimeter: Polarimeter },
    TEXTBOOK: {
      spect_dm: function (p) {
        var n = p.n0 + p.nB / (p.lam * p.lam);
        return 2 * Math.asin(Math.min(1.0, n * Math.sin(p.A / 2))) - p.A;
      },
      spect_sep: function (p) { return 2 * p.A; },
      grating_theta: function (p) { return Math.asin(Math.min(1.0, p.m * p.lam / p.d)); },
      grating_disp: function (p) {
        var th = Math.asin(Math.min(1.0, p.m * p.lam / p.d));
        return p.m / (p.d * Math.cos(th));
      },
      grating_rp: function (p) { return p.m * Math.floor(p.N + 0.5); },
      rings_dn: function (p) { return 2 * Math.sqrt(p.n * p.lam * p.R / p.mu); },
      wedge_beta: function (p) { return p.lam * p.L / (2 * p.mu * p.ts); },
      dslit_beta: function (p) { return p.lam * p.D / p.d; },
      gscreen_x: function (p) { return p.D * Math.tan(Math.asin(Math.min(1.0, p.m * p.lam / p.d))); },
      fibre_na: function (p) { return Math.sqrt(Math.max(p.n1 * p.n1 - p.n2 * p.n2, 0.0)); },
      brewster_th: function (p) { return Math.atan(p.n / p.nout); },
      polari_rot: function (p) { return p.alpha * p.Ldm * p.conc / R2D; }
    },
    CALCS: {
      spect_n: { label: 'n', unit: '', needs: ['dm'],
        fn: function (r, p) { return mean(rows(r, ['dm']).map(function (x) { return Math.sin((p.A + x[0]) / 2) / Math.sin(p.A / 2); })); } },
      spect_prism_A: { label: 'A', unit: 'rad', needs: ['sep'],
        fn: function (r) { return mean(rows(r, ['sep']).map(function (x) { return x[0] / 2; })); } },
      grating_lam: { label: 'wavelength', unit: 'm', needs: ['m', 'theta'],
        fn: function (r, p) { return mean(rows(r, ['m', 'theta']).filter(function (x) { return x[0]; })
          .map(function (x) { return p.d * Math.sin(x[1]) / x[0]; })); } },
      grating_R: { label: 'resolving power', unit: '', needs: ['rp'],
        fn: function (r) { return mean(rows(r, ['rp']).map(function (x) { return x[0]; })); } },
      rings_R: { label: 'R (lens)', unit: 'm', needs: ['n', 'dsq'],
        fn: function (r, p) { return slope(rows(r, ['n', 'dsq'])) * p.mu / (4 * p.lam); } },
      wedge_t: { label: 'thickness', unit: 'm', needs: ['n', 'x'],
        fn: function (r, p) { var m = slope(rows(r, ['n', 'x'])); return m > 0 ? p.lam * p.L / (2 * p.mu * m) : 0.0; } },
      dslit_lam: { label: 'wavelength', unit: 'm', needs: ['beta'],
        fn: function (r, p) { return mean(rows(r, ['beta']).map(function (x) { return x[0] * p.d / p.D; })); } },
      gscreen_lam: { label: 'wavelength', unit: 'm', needs: ['m', 'x'],
        fn: function (r, p) { return mean(rows(r, ['m', 'x']).filter(function (x) { return x[0]; })
          .map(function (x) { return p.d * Math.sin(Math.atan2(x[1], p.D)) / x[0]; })); } },
      gscreen_d: { label: 'grating spacing', unit: 'm', needs: ['m', 'x'],
        fn: function (r, p) { return mean(rows(r, ['m', 'x']).filter(function (x) { return x[1] > 0; })
          .map(function (x) { return x[0] * p.lam / Math.sin(Math.atan2(x[1], p.D)); })); } },
      fibre_NA: { label: 'NA', unit: '', needs: ['dz', 'W'],
        fn: function (r, p) { return mean(rows(r, ['dz', 'W']).filter(function (x) { return x[0] > 0; })
          .map(function (x) { return Math.sin(Math.atan2(x[1] - p.dcore, 2 * x[0])); })); } },
      brewster_n: { label: 'n', unit: '', needs: ['thb'],
        fn: function (r, p) { return mean(rows(r, ['thb']).map(function (x) { return Math.tan(x[0]) * p.nout; })); } },
      polari_alpha: { label: 'specific rotation', unit: 'deg/(dm·g/mL)', needs: ['c', 'rot'],
        fn: function (r, p) { return mean(rows(r, ['c', 'rot']).filter(function (x) { return x[0] > 0; })
          .map(function (x) { return x[1] * R2D / (x[0] * p.Ldm); })); } }
    }
  });
})(typeof window !== 'undefined' ? window : this);
