/* Kernel pack `ug_modern_w8`: the exact JavaScript twin of app/prayog/packs/ug_modern_w8.py. Same formulas, same
   search algorithms, same step counts, same numbers (the server's tests run both and compare). B.Sc. modern physics
   and microwaves: a vacuum diode (Richardson-Dushman), the ionisation of mercury, Thomson's crossed fields, the
   magnetron, helical focusing and the bar-magnet method, Millikan's oil drops, the normal Zeeman effect through a
   Fabry-Perot etalon, Planck's constant from a hot filament, and the 3 cm microwave optics bench.
   Deterministic: no randomness, no wall clock. Constants CODATA 2018. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, QE = 1.602176634e-19, ME = 9.1093837015e-31, HP = 6.62607015e-34, KB = 1.380649e-23,
    C = 2.99792458e8, MU0 = 1.25663706212e-6, EM = QE / ME, A0 = 4 * PI * ME * QE * KB * KB / (HP * HP * HP),
    DEG = PI / 180, GOLD = 0.6180339887498949;

  function fit(pts) {
    var n = pts.length, sx = 0.0, sy = 0.0, sxy = 0.0, sxx = 0.0, i, d, m;
    if (n < 2) return [0.0, 0.0];
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    d = n * sxx - sx * sx;
    if (d === 0) return [0.0, 0.0];
    m = (n * sxy - sx * sy) / d;
    return [m, (sy - m * sx) / n];
  }
  function rws(rows, keys) {
    var out = [], i, j, v, ok, vals;
    for (i = 0; i < (rows || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) {
        v = rows[i][keys[j]];
        if (v === null || v === undefined || v === '' || typeof v === 'boolean' || !isFinite(Number(v))) { ok = false; break; }
        vals.push(Number(v));
      }
      if (ok) out.push(vals);
    }
    return out;
  }
  function bisect(f, lo, hi, n) {
    var flo = f(lo), i, mid;
    if ((flo > 0) === (f(hi) > 0)) return -1.0;
    for (i = 0; i < n; i++) { mid = (lo + hi) / 2; if ((f(mid) > 0) === (flo > 0)) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }
  function goldenMax(f, lo, hi, n) {
    var c = hi - GOLD * (hi - lo), d = lo + GOLD * (hi - lo), fc = f(c), fd = f(d), i;
    for (i = 0; i < n; i++) {
      if (fc > fd) { hi = d; d = c; fd = fc; c = hi - GOLD * (hi - lo); fc = f(c); }
      else { lo = c; c = d; fc = fd; d = lo + GOLD * (hi - lo); fd = f(d); }
    }
    return (lo + hi) / 2;
  }
  function tick() {
    return { init: function () { return { t: 0.0 }; }, step: function (s, p, dt) { s.t += dt; } };
  }

  // ------------------------------------------------------------------ vacuum diode
  var Diode = {
    PARAMS: { If: 2.0, Va: 0.0, phi: 4.55, Sa: 2e-6, Kc: 1e-5, T0: 400.0, kT: 800.0, Vmax: 150.0 },
    VARS: ['t', 'T', 'Is', 'Ia', 'Ia_uA'],
    IFS: [2.0, 2.1, 2.2, 2.3, 2.4, 2.5],
    temp: function (p, i) { return p.T0 + p.kT * i; },
    sat: function (p, t) { return A0 * p.Sa * t * t * Math.exp(-p.phi * QE / (KB * t)); },
    anode: function (p, i, va) {
      if (va <= 0) return 0.0;
      var is = Diode.sat(p, Diode.temp(p, i)), isc = p.Kc * Math.pow(va, 1.5);
      return is / Math.pow(1.0 + Math.pow(is / isc, 6), 1.0 / 6.0);
    },
    init: tick().init, step: tick().step,
    view: function (s, p) {
      var t = Diode.temp(p, p.If), ia = Diode.anode(p, p.If, p.Va);
      return { t: s.t || 0.0, T: t, Is: Diode.sat(p, t), Ia: ia, Ia_uA: ia * 1e6 };
    },
    measure: function (p) {
      var pts = [], i, t;
      for (i = 0; i < Diode.IFS.length; i++) {
        t = Diode.temp(p, Diode.IFS[i]);
        pts.push([1.0 / t, Math.log(Diode.anode(p, Diode.IFS[i], p.Vmax) / (t * t))]);
      }
      return { phi: -fit(pts)[0] * KB / QE, T: Diode.temp(p, p.If), Ia: Diode.anode(p, p.If, p.Va) };
    }
  };

  // ------------------------------------------------------------------ mercury ionisation
  var Ion = {
    PARAMS: { V: 0.0, Ui: 10.4375, G: 2e-8, s: 0.15, leak: 2e-11, Vmax: 20.0 },
    VARS: ['t', 'I', 'I_nA'],
    VFIT: [14.0, 15.0, 16.0, 17.0, 18.0],
    current: function (p, v) {
      var x = (v - p.Ui) / p.s, sp = x > 0 ? x + Math.log1p(Math.exp(-x)) : Math.log1p(Math.exp(x));
      return p.leak + p.G * p.s * sp;
    },
    init: tick().init, step: tick().step,
    view: function (s, p) { var i = Ion.current(p, p.V); return { t: s.t || 0.0, I: i, I_nA: i * 1e9 }; },
    measure: function (p) {
      var f = fit(Ion.VFIT.map(function (v) { return [v, Ion.current(p, v)]; }));
      return { Vi: f[0] ? -f[1] / f[0] : 0.0, I: Ion.current(p, p.V) };
    }
  };

  // ------------------------------------------------------------------ Thomson e/m
  var Thomson = {
    PARAMS: { Va: 1500.0, Vp: 0.0, Ic: 0.0, em: EM, l: 0.02, d: 0.004, L: 0.15, kB: 4.2e-3 },
    VARS: ['t', 'y', 'y_mm', 'B', 'E'],
    defl: function (p, vp, b) {
      var v = Math.sqrt(2 * p.em * p.Va), g = p.l * (p.l / 2 + p.L);
      return (vp / p.d) * g / (2 * p.Va) - p.em * b * g / v;
    },
    init: tick().init, step: tick().step,
    view: function (s, p) {
      var y = Thomson.defl(p, p.Vp, p.kB * p.Ic);
      return { t: s.t || 0.0, y: y, y_mm: y * 1000, B: p.kB * p.Ic, E: p.Vp / p.d };
    },
    measure: function (p) {
      var vp = p.Vp > 0 ? p.Vp : 150.0, b = bisect(function (bb) { return Thomson.defl(p, vp, bb); }, 0.0, 0.05, 80), e = vp / p.d;
      return { em: b > 0 ? e * e / (2 * p.Va * b * b) : 0.0, Bbal: b, y: Thomson.defl(p, p.Vp, p.kB * p.Ic) };
    }
  };

  // ------------------------------------------------------------------ magnetron e/m
  var Mag = {
    PARAMS: { Va: 6.0, Is: 0.0, em: EM, a: 4e-3, b: 1e-4, n: 1e4, Kd: 1e-4, w: 0.04 },
    VARS: ['t', 'B', 'Ia', 'Ia_mA'],
    geo: function (p) { return p.a * p.a * Math.pow(1 - p.b * p.b / (p.a * p.a), 2); },
    bc: function (p, va) { return Math.sqrt(8 * va / (p.em * Mag.geo(p))); },
    current: function (p, va, b) {
      if (va <= 0) return 0.0;
      var bc = Mag.bc(p, va), x = (b - bc) / (p.w * bc);
      x = x > 60 ? 60.0 : x;
      return p.Kd * Math.pow(va, 1.5) / (1 + Math.exp(x));
    },
    init: tick().init, step: tick().step,
    view: function (s, p) { var b = MU0 * p.n * p.Is, i = Mag.current(p, p.Va, b); return { t: s.t || 0.0, B: b, Ia: i, Ia_mA: i * 1000 }; },
    measure: function (p) {
      var va = p.Va, half = p.Kd * Math.pow(va, 1.5) / 2,
        b = bisect(function (bb) { return Mag.current(p, va, bb) - half; }, 0.0, 0.05, 80);
      return { em: b > 0 ? 8 * va / (b * b * Mag.geo(p)) : 0.0, Bh: b, Ia: Mag.current(p, va, MU0 * p.n * p.Is) };
    }
  };

  // ------------------------------------------------------------------ focusing / bar magnet
  var Focus = {
    PARAMS: { meth: 0.0, Va: 800.0, Ic: 0.0, em: EM, L: 0.13, n: 1e4, len0: 0.02, x: 0.15, Mm: 1.0, BH: 3.5e-5 },
    VARS: ['t', 'B', 'ell_mm', 'y_mm', 'thm'],
    ell: function (p, b) {
      var v = Math.sqrt(2 * p.em * p.Va), th = p.em * b * p.L / v;
      if (th < 1e-9) return p.len0;
      return p.len0 * Math.abs(Math.sin(th / 2) / (th / 2));
    },
    barB: function (p, x) { return MU0 * p.Mm / (2 * PI * x * x * x); },
    barY: function (p, b) {
      if (b <= 0) return 0.0;
      var r = Math.sqrt(2 * p.Va / p.em) / b;
      if (r <= p.L) return r;
      return r - Math.sqrt(r * r - p.L * p.L);
    },
    init: tick().init, step: tick().step,
    view: function (s, p) {
      var b;
      if (p.meth > 0.5) {
        b = Focus.barB(p, p.x);
        return { t: s.t || 0.0, B: b, ell_mm: 0.0, y_mm: Focus.barY(p, b) * 1000, thm: Math.atan(b / p.BH) / DEG };
      }
      b = MU0 * p.n * p.Ic;
      return { t: s.t || 0.0, B: b, ell_mm: Focus.ell(p, b) * 1000, y_mm: 0.0, thm: 0.0 };
    },
    measure: function (p) {
      var b, y, ll, n = 4000, bmax = 0.03, prev = -1.0, prev2 = -1.0, found = -1.0, k, v, db;
      if (p.meth > 0.5) {
        b = Focus.barB(p, p.x); y = Focus.barY(p, b); ll = p.L * p.L + y * y;
        return { em: 8 * p.Va * y * y / (b * b * ll * ll), Bf: b, y: y };
      }
      for (k = 0; k <= n; k++) {
        v = Focus.ell(p, bmax * k / n);
        if (k >= 2 && prev < prev2 && prev <= v) { found = bmax * (k - 1) / n; break; }
        prev2 = prev; prev = v;
      }
      if (found < 0) return { em: 0.0, Bf: 0.0, y: 0.0 };
      db = bmax / n;
      b = goldenMax(function (bb) { return -Focus.ell(p, bb); }, found - db, found + db, 80);
      return { em: 8 * PI * PI * p.Va / (b * b * p.L * p.L), Bf: b, y: 0.0 };
    }
  };

  // ------------------------------------------------------------------ Millikan oil drop
  var Oil = {
    PARAMS: { meth: 0.0, drop: 0.0, V: 0.0, e: QE, eta: 1.81e-5, rho: 886.0, g: 9.81, d: 5e-3, s: 1e-3 },
    VARS: ['t', 'y', 'vel', 'a'],
    RAD: [0.62e-6, 0.71e-6, 0.80e-6, 0.66e-6, 0.75e-6],
    NQ: [1.0, 2.0, 4.0, 3.0, 5.0],
    idx: function (p) { var i = Math.floor(p.drop + 0.5); return i < 0 ? 0 : (i > 4 ? 4 : i); },
    vel: function (p, i, v) {
      var a = Oil.RAD[i], m = 4.0 / 3.0 * PI * a * a * a * p.rho, q = Oil.NQ[i] * p.e;
      return (q * v / p.d - m * p.g) / (6 * PI * p.eta * a);
    },
    radius: function (p, vg) { return Math.sqrt(9 * p.eta * vg / (2 * p.rho * p.g)); },
    init: function () { return { t: 0.0, y: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; s.y += Oil.vel(p, Oil.idx(p), p.V) * dt; },
    view: function (s, p) { var i = Oil.idx(p); return { t: s.t || 0.0, y: s.y || 0.0, vel: Oil.vel(p, i, p.V), a: Oil.RAD[i] }; },
    measure: function (p) {
      var i = Oil.idx(p), vg = -Oil.vel(p, i, 0.0), a = Oil.radius(p, vg), q, v, vr, vb;
      if (p.meth > 0.5) {
        v = p.V > 0 ? p.V : 500.0; vr = Oil.vel(p, i, v);
        q = 6 * PI * p.eta * a * (vg + vr) * p.d / v;
      } else {
        vb = bisect(function (vv) { return Oil.vel(p, i, vv); }, 0.0, 2000.0, 80);
        q = vb > 0 ? 4.0 / 3.0 * PI * a * a * a * p.rho * p.g * p.d / vb : 0.0;
      }
      return { e: q / Oil.NQ[i], e19: q / Oil.NQ[i] * 1e19, q: q, vg: vg };
    }
  };
  function oilE(rows) {
    var qs = rws(rows, ['q']).map(function (r) { return r[0]; }).filter(function (q) { return q > 0; }), q1, tot = 0.0, i, k;
    if (!qs.length) return 0.0;
    q1 = Math.min.apply(null, qs);
    for (i = 0; i < qs.length; i++) { k = Math.floor(qs[i] / q1 + 0.5); tot += qs[i] / (k > 0 ? k : 1); }
    return tot / qs.length;
  }

  // ------------------------------------------------------------------ Zeeman effect
  var Zee = {
    PARAMS: { B: 0.0, em: EM, lam: 6.4384696e-7, t: 3e-3, f: 0.3 },
    VARS: ['t', 'B', 'D2p', 'D2m', 'D3p', 'D3m'],
    diam: function (p, sig, ring) {
      var m = Math.floor(2 * p.t / p.lam) - ring + 1, c = m / (2 * p.t * sig);
      if (c >= 1) return 0.0;
      return 2 * p.f * Math.tan(Math.acos(c));
    },
    rings: function (p, b) {
      var s0 = 1.0 / p.lam, ds = p.em * b / (4 * PI * C);
      return [Zee.diam(p, s0 + ds, 2), Zee.diam(p, s0 - ds, 2), Zee.diam(p, s0 + ds, 3), Zee.diam(p, s0 - ds, 3)];
    },
    emFrom: function (p, b, r) {
      var d2 = ((r[2] * r[2] - r[0] * r[0]) + (r[3] * r[3] - r[1] * r[1])) / 2,
        dsig = ((r[0] * r[0] - r[1] * r[1]) + (r[2] * r[2] - r[3] * r[3])) / 2 / (4 * p.t * d2);
      return 4 * PI * C * dsig / b;
    },
    init: tick().init, step: tick().step,
    view: function (s, p) { var r = Zee.rings(p, p.B); return { t: s.t || 0.0, B: p.B, D2p: r[0], D2m: r[1], D3p: r[2], D3m: r[3] }; },
    measure: function (p) { var b = p.B > 0 ? p.B : 0.6; return { em: Zee.emFrom(p, b, Zee.rings(p, b)), B: b }; }
  };

  // ------------------------------------------------------------------ black-body Planck
  var BB = {
    PARAMS: { T: 2000.0, h: HP, lam: 6.5e-7, K: 1e-2 },
    VARS: ['t', 'I', 'I_nA'],
    TS: [1800.0, 1900.0, 2000.0, 2100.0, 2200.0, 2300.0, 2400.0, 2500.0, 2600.0],
    current: function (p, t) { return p.K / Math.expm1(p.h * C / (p.lam * KB * t)); },
    init: tick().init, step: tick().step,
    view: function (s, p) { var i = BB.current(p, p.T); return { t: s.t || 0.0, I: i, I_nA: i * 1e9 }; },
    measure: function (p) {
      var m = fit(BB.TS.map(function (t) { return [1.0 / t, Math.log(BB.current(p, t))]; }))[0];
      return { h: -m * p.lam * KB / C, h34: -m * p.lam * KB / C * 1e34, I: BB.current(p, p.T) };
    }
  };

  // ------------------------------------------------------------------ microwave optics
  var Mw = {
    PARAMS: { part: 0.0, th: 0.0, inc: 45.0, n: 1.5, A: 30.0, w: 8.0, phi: 0.0, lam: 0.02848, ds: 0.065, as_: 0.015, I0: 1.0 },
    VARS: ['t', 'I'],
    dev: function (p) { return Math.asin(p.n * Math.sin(p.A * DEG)) / DEG - p.A; },
    signal: function (p, part, th, phi) {
      var x, c, s, be, al, env, cb;
      if (part < 0.5) { x = (th - p.inc) / p.w; return p.I0 * Math.exp(-x * x); }
      if (part < 1.5) { x = (th - Mw.dev(p)) / p.w; return p.I0 * Math.exp(-x * x); }
      if (part < 2.5) { c = Math.cos(phi * DEG); return p.I0 * c * c; }
      s = Math.sin(th * DEG); be = PI * p.ds * s / p.lam; al = PI * p.as_ * s / p.lam;
      env = Math.abs(al) < 1e-12 ? 1.0 : Math.sin(al) / al; cb = Math.cos(be);
      return p.I0 * cb * cb * env * env;
    },
    init: tick().init, step: tick().step,
    view: function (s, p) { return { t: s.t || 0.0, I: Mw.signal(p, p.part, p.th, p.phi) }; },
    firstMax: function (p, part, lo, hi) {
      var n = Math.round((hi - lo) / 0.05), prev2 = -1.0, prev = -1.0, k, th, v, c;
      for (k = 0; k <= n; k++) {
        th = lo + 0.05 * k; v = Mw.signal(p, part, th, 0.0);
        if (k >= 2 && prev > prev2 && prev >= v) {
          c = lo + 0.05 * (k - 1);
          return goldenMax(function (tt) { return Mw.signal(p, part, tt, 0.0); }, c - 0.05, c + 0.05, 60);
        }
        prev2 = prev; prev = v;
      }
      return -1.0;
    },
    firstMin: function (p, part, lo, hi) {
      var n = Math.round((hi - lo) / 0.05), prev2 = -1.0, prev = -1.0, k, th, v, c;
      for (k = 0; k <= n; k++) {
        th = lo + 0.05 * k; v = Mw.signal(p, part, th, 0.0);
        if (k >= 2 && prev < prev2 && prev <= v) {
          c = lo + 0.05 * (k - 1);
          return goldenMax(function (tt) { return -Mw.signal(p, part, tt, 0.0); }, c - 0.05, c + 0.05, 60);
        }
        prev2 = prev; prev = v;
      }
      return -1.0;
    },
    measure: function (p) {
      var dv = Mw.firstMax(p, 1.0, 0.0, 70.0), th1 = Mw.firstMin(p, 3.0, 2.0, 60.0), rr = Mw.firstMax(p, 0.0, 0.0, 89.0);
      return { n: dv >= 0 ? Math.sin((p.A + dv) * DEG) / Math.sin(p.A * DEG) : 0.0,
        lam: th1 > 0 ? 2 * p.ds * Math.sin(th1 * DEG) : 0.0, r: rr, I: Mw.signal(p, p.part, p.th, p.phi) };
    }
  };

  H.register({
    K: { w8_diode: Diode, w8_ion: Ion, w8_thomson: Thomson, w8_mag: Mag, w8_focus: Focus, w8_oil: Oil, w8_zeeman: Zee,
      w8_bb: BB, w8_mw: Mw },
    CALCS: {
      w8_c_phi: { label: 'work function', unit: 'eV', needs: ['invT', 'lnIT2'],
        fn: function (r) { return -fit(rws(r, ['invT', 'lnIT2']))[0] * KB / QE; } },
      w8_c_ui: { label: 'ionisation potential', unit: 'V', needs: ['V', 'I'],
        fn: function (r) { var f = fit(rws(r, ['V', 'I'])); return f[0] ? -f[1] / f[0] : 0.0; } },
      w8_c_h: { label: "Planck's constant", unit: 'J s', needs: ['invT', 'lnI'],
        fn: function (r, p) { return -fit(rws(r, ['invT', 'lnI']))[0] * p.lam * KB / C; } },
      w8_c_e: { label: 'electronic charge', unit: 'C', needs: ['q'], fn: oilE }
    },
    TEXTBOOK: {
      w8_phi: function (p) { return p.phi; }, w8_ui: function (p) { return p.Ui; }, w8_em: function (p) { return p.em; },
      w8_e19: function (p) { return p.e * 1e19; }, w8_h34: function (p) { return p.h * 1e34; }, w8_n: function (p) { return p.n; },
      w8_lam: function (p) { return p.lam; }
    }
  });
})(typeof window !== 'undefined' ? window : this);
