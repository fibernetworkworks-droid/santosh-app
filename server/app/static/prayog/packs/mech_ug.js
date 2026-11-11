/* Kernel pack (browser twin of app/prayog/packs/mech_ug.py): the classic B.Sc. mechanics, measurement and
   properties-of-matter benches. Same formulas, same order of operations, so both sides give the same numbers.
     torsion      T = 2π√(I / C), C = π η r⁴ / (2 L)      stattorsion  θ = 4 m g a L / (π η r⁴)
     flywheel     t₁ = √(2 φ (I + m r²) / (m g r − τf))    barpend      T = 2π√((k² + h²) / (g h))
     poiseuille   Q = π ρ g h r⁴ / (8 η l)                 jaeger       H = (2T/(r g) + h ρl) / ρm
     unibend      δ = 3 m g a L² / (2 Y b d³)              travmicro    mean of the repeated readings
     freefall     t = √(2 h / g)                           collide1d    v₂ = m₁(1 + e) u₁ / (m₁ + m₂)
   Deterministic: no randomness drawn from the system, no wall clock. */
(function (root) {
  'use strict';
  var PI = Math.PI;

  function sub(dt, h) { var n = Math.max(1, Math.ceil(dt / h - 1e-9)); return [n, dt / n]; }
  function relax(x, target, dt, tau) {
    var sh = sub(dt, 0.005), n = sh[0], h = sh[1], t = Math.max(tau, 1e-6), i;
    for (i = 0; i < n; i++) x += (target - x) * (h / t);
    return x;
  }
  function rk4(f, y, h) {
    var n = y.length, i, k1 = f(y), t = [], k2, k3, k4, out = [];
    for (i = 0; i < n; i++) t[i] = y[i] + h / 2 * k1[i]; k2 = f(t); t = [];
    for (i = 0; i < n; i++) t[i] = y[i] + h / 2 * k2[i]; k3 = f(t); t = [];
    for (i = 0; i < n; i++) t[i] = y[i] + h * k3[i]; k4 = f(t);
    for (i = 0; i < n; i++) out[i] = y[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]);
    return out;
  }
  function period(f, y0, h, tmax) {
    var y = y0.slice(), t = 0, cross = [], y2;
    while (t < tmax && cross.length < 2) {
      y2 = rk4(f, y, h);
      if (y[0] > 0 && y2[0] <= 0) cross.push(t + h * y[0] / (y[0] - y2[0]));
      y = y2; t = t + h;
    }
    return cross.length === 2 ? cross[1] - cross[0] : 0;
  }
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0; }
  function rows(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) { v = Number(rs[i][keys[j]]); if (!isFinite(v)) { ok = false; break; } vals.push(v); }
      if (ok) out.push(vals);
    }
    return out;
  }
  function mapMean(rs, keys, fn, keep) {
    var r = rows(rs, keys), out = [], i;
    for (i = 0; i < r.length; i++) if (!keep || keep(r[i])) out.push(fn(r[i]));
    return mean(out);
  }

  // ---------------------------------------------------------------------- torsional pendulum / inertia table
  function torsC(p) { return PI * p.eta * Math.pow(p.rw, 4) / (2 * p.Lw); }
  function torsT(p) { var c = torsC(p); return c > 0 && p.I > 0 ? 2 * PI * Math.sqrt(p.I / c) : 0; }
  function torsF(p) { var c = torsC(p) / p.I, b = p.b; return function (y) { return [y[1], -c * y[0] - b * y[1]]; }; }
  var Torsion = {
    PARAMS: { eta: 8.0e10, rw: 0.0004, Lw: 0.8, I: 0.0012, th0: 0.35, b: 0.0 },
    VARS: ['t', 'th', 'th_deg', 'om', 'C', 'T_calc', 'amp_deg'],
    init: function (p) { return { t: 0, y: [p.th0, 0] }; },
    step: function (s, p, dt) { var q = sub(dt, 0.002), f = torsF(p), i; for (i = 0; i < q[0]; i++) s.y = rk4(f, s.y, q[1]); s.t += dt; },
    view: function (s, p) {
      return { t: s.t, th: s.y[0], th_deg: s.y[0] * 180 / PI, om: s.y[1], C: torsC(p), T_calc: torsT(p),
        amp_deg: p.th0 * 180 / PI };
    },
    measure: function (p) { return { T: period(torsF(p), [p.th0, 0], 0.0005, 400.0), C: torsC(p) }; }
  };

  // ---------------------------------------------------------------------- statical torsion (Barton's apparatus)
  function statTheta(p) { return 4 * p.m * p.g * p.a * p.Lr / (PI * p.eta * Math.pow(p.rr, 4)); }
  var StatTorsion = {
    PARAMS: { eta: 8.0e10, rr: 0.002, Lr: 0.6, a: 0.05, m: 0.0, g: 9.8, tau: 0.6, th0: 0.0 },
    VARS: ['t', 'th', 'th_deg', 'couple', 'th_eq_deg'],
    init: function (p) { return { t: 0, th: p.th0 }; },
    step: function (s, p, dt) { s.th = relax(s.th, statTheta(p), dt, p.tau); s.t += dt; },
    view: function (s, p) {
      return { t: s.t, th: s.th, th_deg: s.th * 180 / PI, couple: 2 * p.m * p.g * p.a, th_eq_deg: statTheta(p) * 180 / PI };
    },
    measure: function (p) { var s = StatTorsion.init(p), i; for (i = 0; i < 200; i++) StatTorsion.step(s, p, 0.1);
      return { theta: s.th, theta_eq: statTheta(p) }; }
  };

  // ---------------------------------------------------------------------- moment of inertia of a flywheel
  function flyPhi(p) { return 2 * PI * p.n; }
  function flyA1(p) { return (p.m * p.g * p.ra - p.tf) / (p.I + p.m * p.ra * p.ra); }
  function flyT1(p) { var a = flyA1(p); return a > 0 ? Math.sqrt(2 * flyPhi(p) / a) : 0; }
  function flyState(p, t) {
    var a1 = flyA1(p), phi = flyPhi(p), t1 = flyT1(p), om0, a2, td, tstop;
    if (t <= t1) return [0.5 * a1 * t * t, a1 * t, 0];
    om0 = a1 * t1; a2 = p.tf / p.I; td = t - t1; tstop = a2 > 0 ? om0 / a2 : 1e9;
    if (td >= tstop) return [phi + om0 * tstop - 0.5 * a2 * tstop * tstop, 0, 2];
    return [phi + om0 * td - 0.5 * a2 * td * td, om0 - a2 * td, 1];
  }
  function flyIOne(p, m, n, t1, N) {
    var phi = 2 * PI * n, h = p.ra * phi, v = 2 * phi * p.ra / t1;
    return m * (2 * p.g * h - v * v) * p.ra * p.ra / (v * v * (1 + n / N));
  }
  var Flywheel = {
    PARAMS: { I: 0.012, m: 0.5, ra: 0.012, n: 8.0, tf: 0.012, g: 9.8 },
    VARS: ['t', 'ph', 'om', 'rpm', 'drop', 'phase', 'turns', 't1', 'om1', 'N', 't2', 'v'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var q = flyState(p, s.t), ph = q[0], om = q[1], phase = q[2], phi = flyPhi(p), t1 = flyT1(p),
        om1 = flyA1(p) * t1, a2 = p.tf / p.I;
      return { t: s.t, ph: ph, om: om, rpm: om * 60 / (2 * PI), drop: p.ra * Math.min(ph, phi), phase: phase,
        turns: ph / (2 * PI), t1: t1, om1: om1, N: a2 > 0 ? om1 * om1 / (2 * a2) / (2 * PI) : 0,
        t2: a2 > 0 ? om1 / a2 : 0, v: om * p.ra };
    },
    measure: function (p) {
      var t1 = flyT1(p), om1 = flyA1(p) * t1, a2 = p.tf / p.I;
      return { t1: t1, om1: om1, v: om1 * p.ra, N: a2 > 0 ? om1 * om1 / (2 * a2) / (2 * PI) : 0,
        t2: a2 > 0 ? om1 / a2 : 0, h: p.ra * flyPhi(p) };
    }
  };

  // ---------------------------------------------------------------------- bar (compound) pendulum
  function barK2(p) { return p.Lb * p.Lb / 12; }
  function barT(p) { var k2 = barK2(p); return p.h > 0 ? 2 * PI * Math.sqrt((k2 + p.h * p.h) / (p.g * p.h)) : 0; }
  function barF(p) {
    var k2 = barK2(p), c = p.g * p.h / (k2 + p.h * p.h), b = p.b;
    return function (y) { return [y[1], -c * Math.sin(y[0]) - b * y[1]]; };
  }
  var BarPendulum = {
    PARAMS: { Lb: 1.0, h: 0.35, g: 9.8, th0: 0.0873, b: 0.0 },
    VARS: ['t', 'th', 'th_deg', 'om', 'k2', 'T_calc', 'L_eq'],
    init: function (p) { return { t: 0, y: [p.th0, 0] }; },
    step: function (s, p, dt) { var q = sub(dt, 0.002), f = barF(p), i; for (i = 0; i < q[0]; i++) s.y = rk4(f, s.y, q[1]); s.t += dt; },
    view: function (s, p) {
      var k2 = barK2(p);
      return { t: s.t, th: s.y[0], th_deg: s.y[0] * 180 / PI, om: s.y[1], k2: k2, T_calc: barT(p),
        L_eq: p.h > 0 ? (k2 + p.h * p.h) / p.h : 0 };
    },
    measure: function (p) { return { T: period(barF(p), [p.th0, 0], 0.0005, 200.0), T_small: barT(p) }; }
  };

  // ---------------------------------------------------------------------- viscosity by capillary flow
  function poisQ(p) { return PI * p.rho * p.g * p.hh * Math.pow(p.rc, 4) / (8 * p.eta * p.lc); }
  var Poiseuille = {
    PARAMS: { eta: 0.001002, rho: 998.2, rc: 0.0005, lc: 0.15, hh: 0.25, g: 9.8, Vt: 1.0e-5 },
    VARS: ['t', 'V', 'V_ml', 'Q', 'Q_ml', 'full', 't_full'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var q = poisQ(p), v = q * s.t;
      return { t: s.t, V: v, V_ml: v * 1e6, Q: q, Q_ml: q * 1e6, full: v >= p.Vt ? 1 : 0, t_full: q > 0 ? p.Vt / q : 0 };
    },
    measure: function (p) { var q = poisQ(p); return { Q: q, t_full: q > 0 ? p.Vt / q : 0, Q_ml: q * 1e6 }; }
  };

  // ---------------------------------------------------------------------- Jaeger's bubble method
  function jaegerH(p) { return (2 * p.Tst / (p.r * p.g) + p.hd * p.rhol) / p.rhom; }
  var Jaeger = {
    PARAMS: { Tst: 0.07275, r: 0.0003, hd: 0.04, rhol: 998.2, rhom: 998.2, g: 9.8, tau: 1.2, H0: 0.0 },
    VARS: ['t', 'H', 'H_cm', 'H_eq_cm', 'p_bubble', 'steady'],
    init: function (p) { return { t: 0, H: p.H0 }; },
    step: function (s, p, dt) { s.H = relax(s.H, jaegerH(p), dt, p.tau); s.t += dt; },
    view: function (s, p) {
      var heq = jaegerH(p);
      return { t: s.t, H: s.H, H_cm: s.H * 100, H_eq_cm: heq * 100, p_bubble: s.H * p.rhom * p.g,
        steady: Math.abs(s.H - heq) < 1e-5 ? 1 : 0 };
    },
    measure: function (p) { var s = Jaeger.init(p), i; for (i = 0; i < 300; i++) Jaeger.step(s, p, 0.1);
      return { H: s.H, H_eq: jaegerH(p) }; }
  };

  // ---------------------------------------------------------------------- uniform bending of a beam
  function uniDelta(p) { return 3 * p.m * p.g * p.a * p.L * p.L / (2 * p.Y * p.b * Math.pow(p.d, 3)); }
  var UniBend = {
    PARAMS: { Y: 2.0e11, b: 0.025, d: 0.005, L: 0.7, a: 0.12, m: 0.0, g: 9.8, tau: 0.5, d0: 0.0 },
    VARS: ['t', 'delta', 'delta_mm', 'delta_eq_mm', 'load_N', 'I_beam'],
    init: function (p) { return { t: 0, d: p.d0 }; },
    step: function (s, p, dt) { s.d = relax(s.d, uniDelta(p), dt, p.tau); s.t += dt; },
    view: function (s, p) {
      return { t: s.t, delta: s.d, delta_mm: s.d * 1000, delta_eq_mm: uniDelta(p) * 1000, load_N: p.m * p.g,
        I_beam: p.b * Math.pow(p.d, 3) / 12 };
    },
    measure: function (p) { var s = UniBend.init(p), i; for (i = 0; i < 200; i++) UniBend.step(s, p, 0.1);
      return { delta: s.d, delta_eq: uniDelta(p) }; }
  };

  // ---------------------------------------------------------------------- travelling microscope + repeated readings
  function lehmer(seed) { return (seed * 16807) % 2147483647; }
  function tmZ(p, i) {
    var s = (Math.floor(p.seed) + 1) * 7919 + (i + 1) * 104729, u = 0.0, j;
    s = s % 2147483647;
    if (s === 0) s = 1;
    for (j = 0; j < 12; j++) { s = lehmer(s); u += s / 2147483647; }
    return u - 6.0;
  }
  function tmLc(p) { return p.pitch / p.ndiv; }
  function tmRead(p, i) {
    var lc = tmLc(p), x = p.L + p.ze + p.sigma * tmZ(p, i);
    return Math.floor(x / lc + 0.5) * lc;
  }
  function tmMean(p) {
    var n = Math.max(1, Math.floor(p.nrep)), s = 0, i;
    for (i = 0; i < n; i++) s += tmRead(p, i);
    return s / n;
  }
  var TravMicro = {
    PARAMS: { L: 0.025, pitch: 0.0005, ndiv: 50.0, ze: 0.0, sigma: 0.00008, idx: 0.0, nrep: 10.0, seed: 7.0 },
    VARS: ['x', 'x_mm', 'x_cm', 'msr_mm', 'vsd', 'lc_mm', 'lc_cm', 'mean_mm', 'sd_mm'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var lc = tmLc(p), x = tmRead(p, Math.floor(p.idx)), nd = Math.floor(x / lc + 0.5), whole = Math.floor(nd / p.ndiv);
      return { x: x, x_mm: x * 1000, x_cm: x * 100, msr_mm: whole * p.pitch * 1000, vsd: nd - whole * p.ndiv,
        lc_mm: lc * 1000, lc_cm: lc * 100, mean_mm: tmMean(p) * 1000, sd_mm: TravMicro.measure(p).sd * 1000 };
    },
    measure: function (p) {
      var n = Math.max(1, Math.floor(p.nrep)), xs = [], s = 0, v = 0, i, mn;
      for (i = 0; i < n; i++) { xs.push(tmRead(p, i)); s += xs[i]; }
      mn = s / n;
      if (n > 1) { for (i = 0; i < n; i++) v += (xs[i] - mn) * (xs[i] - mn); v = v / (n - 1); } else v = 0;
      return { mean: mn, sd: Math.sqrt(v), se: Math.sqrt(v) / Math.sqrt(n), x: tmRead(p, Math.floor(p.idx)), lc: tmLc(p) };
    }
  };

  // ---------------------------------------------------------------------- free fall between two photo-gates
  function ffT(p) { return Math.sqrt(2 * p.h / p.g); }
  var FreeFall = {
    PARAMS: { g: 9.8, h: 0.5, t0: 0.0 },
    VARS: ['t', 'y', 'v', 'landed', 't_fall', 'v_end'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var tf = ffT(p), t = Math.min(Math.max(s.t - p.t0, 0.0), tf);
      return { t: s.t, y: 0.5 * p.g * t * t, v: p.g * t, landed: s.t - p.t0 >= tf ? 1 : 0, t_fall: tf, v_end: p.g * tf };
    },
    measure: function (p) {
      var tf = ffT(p);
      return { t: tf, v: p.g * tf, v_mid: Math.sqrt(p.g * p.h / 2) * Math.sqrt(2) };
    }
  };

  // ---------------------------------------------------------------------- collisions on an air track
  function collV1(p) { return ((p.m1 - p.e * p.m2) * p.u1) / (p.m1 + p.m2); }
  function collV2(p) { return (p.m1 * (1 + p.e) * p.u1) / (p.m1 + p.m2); }
  var Collide1D = {
    PARAMS: { m1: 0.2, m2: 0.3, u1: 0.4, e: 1.0, gap: 0.4, x20: 0.4 },
    VARS: ['t', 'x1', 'x2', 'v1', 'v2', 'hit', 'tc', 'p_before', 'p_after'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var tc = p.u1 > 0 ? p.gap / p.u1 : 1e9, v1 = collV1(p), v2 = collV2(p), x1, x2, a, b, hit, td;
      if (s.t <= tc) { x1 = p.u1 * s.t; x2 = p.x20; a = p.u1; b = 0.0; hit = 0.0; }
      else { td = s.t - tc; x1 = p.u1 * tc + v1 * td; x2 = p.x20 + v2 * td; a = v1; b = v2; hit = 1.0; }
      return { t: s.t, x1: x1, x2: x2, v1: a, v2: b, hit: hit, tc: tc, p_before: p.m1 * p.u1,
        p_after: p.m1 * a + p.m2 * b };
    },
    measure: function (p) {
      return { u1: p.u1, v1: collV1(p), v2: collV2(p), tc: p.u1 > 0 ? p.gap / p.u1 : 0 };
    }
  };

  root.HoolaKernels.register({
    K: { torsion: Torsion, stattorsion: StatTorsion, flywheel: Flywheel, barpend: BarPendulum,
      poiseuille: Poiseuille, jaeger: Jaeger, unibend: UniBend, travmicro: TravMicro, freefall: FreeFall,
      collide1d: Collide1D },
    TEXTBOOK: {
      torsion_T: torsT, stat_theta: statTheta, fly_t1: flyT1, bar_T: barT, pois_Q: poisQ, jaeger_H: jaegerH,
      uni_delta: uniDelta, tm_L: function (p) { return p.L + p.ze; }, ff_t: ffT, coll_v2: collV2
    },
    CALCS: {
      torsion_eta: { label: 'η (modulus of rigidity)', unit: 'Pa', needs: ['Lw', 'T'],
        fn: function (r, p) { return mapMean(r, ['Lw', 'T'], function (x) { return 8 * PI * p.I * x[0] / (Math.pow(p.rw, 4) * x[1] * x[1]); }, function (x) { return x[1] > 0; }); } },
      torsion_I: { label: 'I (moment of inertia)', unit: 'kg·m²', needs: ['Lw', 'T'],
        fn: function (r, p) { return mapMean(r, ['Lw', 'T'], function (x) { return p.eta * Math.pow(p.rw, 4) * x[1] * x[1] / (8 * PI * x[0]); }, function (x) { return x[0] > 0; }); } },
      stat_eta: { label: 'η (modulus of rigidity)', unit: 'Pa', needs: ['m', 'theta'],
        fn: function (r, p) { return mapMean(r, ['m', 'theta'], function (x) { return 4 * x[0] * p.g * p.a * p.Lr / (PI * Math.pow(p.rr, 4) * x[1]); }, function (x) { return x[1] > 0; }); } },
      fly_I: { label: 'I (moment of inertia)', unit: 'kg·m²', needs: ['m', 'n', 't1', 'N'],
        fn: function (r, p) { return mapMean(r, ['m', 'n', 't1', 'N'], function (x) { return flyIOne(p, x[0], x[1], x[2], x[3]); }, function (x) { return x[2] > 0 && x[3] > 0; }); } },
      bar_g: { label: 'g (acceleration due to gravity)', unit: 'm/s²', needs: ['h', 'T'],
        fn: function (r, p) { return mapMean(r, ['h', 'T'], function (x) { return 4 * PI * PI * (p.Lb * p.Lb / 12 + x[0] * x[0]) / (x[1] * x[1] * x[0]); }, function (x) { return x[1] > 0 && x[0] > 0; }); } },
      pois_eta: { label: 'η (coefficient of viscosity)', unit: 'Pa·s', needs: ['hh', 'Q'],
        fn: function (r, p) { return mapMean(r, ['hh', 'Q'], function (x) { return PI * p.rho * p.g * x[0] * Math.pow(p.rc, 4) / (8 * p.lc * x[1]); }, function (x) { return x[1] > 0; }); } },
      jaeger_T: { label: 'T (surface tension)', unit: 'N/m', needs: ['hd', 'H'],
        fn: function (r, p) { return mapMean(r, ['hd', 'H'], function (x) { return p.r * p.g * (x[1] * p.rhom - x[0] * p.rhol) / 2; }); } },
      uni_Y: { label: "Y (Young's modulus)", unit: 'Pa', needs: ['m', 'delta'],
        fn: function (r, p) { return mapMean(r, ['m', 'delta'], function (x) { return 3 * x[0] * p.g * p.a * p.L * p.L / (2 * p.b * Math.pow(p.d, 3) * x[1]); }, function (x) { return x[1] > 0; }); } },
      tm_mean: { label: 'mean reading', unit: 'm', needs: ['x'],
        fn: function (r) { return mapMean(r, ['x'], function (x) { return x[0]; }); } },
      ff_g: { label: 'g (acceleration due to gravity)', unit: 'm/s²', needs: ['h', 't'],
        fn: function (r) { return mapMean(r, ['h', 't'], function (x) { return 2 * x[0] / (x[1] * x[1]); }, function (x) { return x[1] > 0; }); } },
      coll_m2: { label: 'm₂ (mass of the second glider)', unit: 'kg', needs: ['u1', 'v1', 'v2'],
        fn: function (r, p) { return mapMean(r, ['u1', 'v1', 'v2'], function (x) { return p.m1 * (x[0] - x[1]) / x[2]; }, function (x) { return x[2] !== 0; }); } }
    }
  });
})(typeof window !== 'undefined' ? window : this);
