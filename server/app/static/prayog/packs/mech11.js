/* Kernel pack (browser twin of app/prayog/packs/mech11.py): Class XI-XII mechanics, properties of matter and heat.
   Same formulas, same order of operations, so both sides give the same numbers.
     capillary    h = 2 T cosθ / (r ρ g)                 searle       e = 4 m g L / (π d² Y)
     friction     F = μ R, R = (m + added) g             moments      M y = m x
     beambend     δ = m g L³ / (3 Y I) or / (48 Y I)     vecforce     R² = P² + Q² + 2 P Q cos θ
     spherometer  R = l² / (6 h) + h / 2
   Deterministic: no randomness, no wall clock. */
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
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0; }
  function rows(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) { v = Number(rs[i][keys[j]]); if (rs[i][keys[j]] === '' || rs[i][keys[j]] === null || rs[i][keys[j]] === undefined || !isFinite(v)) { ok = false; break; } vals.push(v); }
      if (ok) out.push(vals);
    }
    return out;
  }
  function mapMean(rs, keys, fn, keep) {
    var r = rows(rs, keys), out = [], i;
    for (i = 0; i < r.length; i++) if (!keep || keep(r[i])) out.push(fn(r[i]));
    return mean(out);
  }

  // ----------------------------------------------------------------------------- surface tension: capillary rise
  function capH(p) { return 2 * p.T * Math.cos(p.theta) / (p.r * p.rho * p.g); }
  var Capillary = {
    PARAMS: { T: 0.07275, rho: 998.2, r: 0.00025, theta: 0.0, g: 9.8, tau: 1.6, h0: 0.0 },
    VARS: ['t', 'h', 'h_mm', 'h_cm', 'heq', 'rise'],
    init: function (p) { return { t: 0, h: p.h0 }; },
    step: function (s, p, dt) { s.h = relax(s.h, capH(p), dt, p.tau); s.t += dt; },
    view: function (s, p) { return { t: s.t, h: s.h, h_mm: s.h * 1000, h_cm: s.h * 100, heq: capH(p), rise: Math.abs(s.h - capH(p)) > 1e-5 ? 1 : 0 }; },
    measure: function (p) { var s = Capillary.init(p), i; for (i = 0; i < 240; i++) Capillary.step(s, p, 0.1); return { h: s.h, heq: capH(p) }; }
  };

  // ------------------------------------------------------------------------ Young's modulus: Searle's apparatus
  function searleE(p) { var a = PI * p.d * p.d / 4; return p.m * p.g * p.L / (a * p.Y); }
  var Searle = {
    PARAMS: { Y: 2.0e11, L: 1.5, d: 0.000559, m: 0.0, g: 9.8, tau: 0.9, e0: 0.0 },
    VARS: ['t', 'e', 'e_mm', 'stress', 'strain', 'load_N'],
    init: function (p) { return { t: 0, e: p.e0 }; },
    step: function (s, p, dt) { s.e = relax(s.e, searleE(p), dt, p.tau); s.t += dt; },
    view: function (s, p) { var a = PI * p.d * p.d / 4; return { t: s.t, e: s.e, e_mm: s.e * 1000, stress: p.m * p.g / a, strain: s.e / p.L, load_N: p.m * p.g }; },
    measure: function (p) { var s = Searle.init(p), i; for (i = 0; i < 200; i++) Searle.step(s, p, 0.1); return { e: s.e, e_eq: searleE(p) }; }
  };

  // ------------------------------------------------------------------------- limiting friction, horizontal plane
  var Friction = {
    PARAMS: { mu: 0.3, m: 0.2, add: 0.0, F: 0.0, g: 9.8, len: 0.3 },
    VARS: ['t', 's', 'v', 'a', 'moving', 'R', 'F_now'],
    init: function () { return { t: 0, s: 0, v: 0, a: 0 }; },
    adv: function (s, p, h) {
      var mass = p.m + p.add, drive = p.F, fr = p.mu * mass * p.g, a, v2;
      if (s.v === 0) {
        if (Math.abs(drive) <= fr) { s.a = 0; return; }
        a = (drive - fr * (drive > 0 ? 1 : -1)) / mass;
      } else a = (drive - fr * (s.v > 0 ? 1 : -1)) / mass;
      v2 = s.v + a * h;
      if (s.v !== 0 && (v2 > 0) !== (s.v > 0)) { s.s += a !== 0 ? s.v * s.v / (-2 * a) : 0; s.v = 0; s.a = 0; return; }
      s.s += s.v * h + 0.5 * a * h * h; s.v = v2; s.a = a;
      if (s.s <= 0 || s.s >= p.len) { s.s = Math.min(Math.max(s.s, 0), p.len); s.v = 0; s.a = 0; }
    },
    step: function (s, p, dt) { var sh = sub(dt, 0.002), i; for (i = 0; i < sh[0]; i++) Friction.adv(s, p, sh[1]); s.t += dt; },
    view: function (s, p) { return { t: s.t, s: s.s, v: s.v, a: s.a, moving: s.v !== 0 ? 1 : 0, R: (p.m + p.add) * p.g, F_now: p.F }; },
    moves: function (p, f) {
      var q = {}, k, s = { t: 0, s: 1, v: 0, a: 0 }, i;
      for (k in p) if (Object.prototype.hasOwnProperty.call(p, k)) q[k] = p[k];
      q.F = f; q.len = 1e6;
      for (i = 0; i < 250; i++) Friction.adv(s, q, 0.002);
      return s.s > 1 + 1e-9;
    },
    measure: function (p) {
      var lo = 0, hi = 4 * (p.m + p.add) * p.g + 1, i, mid;
      for (i = 0; i < 60; i++) { mid = (lo + hi) / 2; if (Friction.moves(p, mid)) hi = mid; else lo = mid; }
      return { F_min: hi, R: (p.m + p.add) * p.g };
    }
  };

  // ------------------------------------------------------------------------------------ principle of moments
  function momTilt(p, y) {
    var lo = -0.30, hi = 0.30, i, mid, th;
    for (i = 0; i < 50; i++) { mid = (lo + hi) / 2; if (p.g * (p.M * y - p.m * p.x) * Math.cos(mid) - p.k * mid > 0) lo = mid; else hi = mid; }
    th = (lo + hi) / 2;
    return Math.min(Math.max(th, -0.12), 0.12);
  }
  var Moments = {
    PARAMS: { m: 0.0523, M: 0.05, x: 0.2, y: 0.2, g: 9.8, k: 0.6, I: 0.004, c: 0.9 },
    VARS: ['t', 'th', 'tilt_deg', 'balanced', 'left_N', 'right_N'],
    init: function (p) { return { t: 0, y: [momTilt(p, p.y), 0] }; },
    f: function (p) { return function (y) { var tq = p.g * (p.M * p.y - p.m * p.x) * Math.cos(y[0]) - p.k * y[0]; return [y[1], tq / p.I - p.c * y[1]]; }; },
    step: function (s, p, dt) {
      var sh = sub(dt, 0.002), f = Moments.f(p), lim = 0.12, i;
      for (i = 0; i < sh[0]; i++) {
        s.y = rk4(f, s.y, sh[1]);
        if (s.y[0] > lim) s.y = [lim, Math.min(0, s.y[1])];
        else if (s.y[0] < -lim) s.y = [-lim, Math.max(0, s.y[1])];
      }
      s.t += dt;
    },
    view: function (s, p) { var th = s.y[0]; return { t: s.t, th: th, tilt_deg: th * 180 / PI, balanced: Math.abs(th) < 0.004 ? 1 : 0, left_N: p.m * p.g, right_N: p.M * p.g }; },
    measure: function (p) {
      var lo = 0, hi = 0.6, i, mid, y;
      for (i = 0; i < 60; i++) { mid = (lo + hi) / 2; if (momTilt(p, mid) < 0) lo = mid; else hi = mid; }
      y = (lo + hi) / 2;
      return { y: y, tilt: momTilt(p, y) };
    }
  };

  // --------------------------------------------------------------------------- depression of a loaded beam
  function beamI(p) { return p.b * Math.pow(p.t, 3) / 12; }
  function beamCf(p) { return p.mode < 0.5 ? 3.0 : 48.0; }
  function beamDelta(p) { return p.m * p.g * Math.pow(p.L, 3) / (beamCf(p) * p.Y * beamI(p)); }
  var BeamBend = {
    PARAMS: { Y: 1.0e10, b: 0.028, t: 0.005, L: 0.5, m: 0.0, g: 9.8, mode: 0.0, tau: 0.5, d0: 0.0 },
    VARS: ['t', 'delta', 'delta_mm', 'delta_cm', 'load_N'],
    init: function (p) { return { t: 0, d: p.d0 }; },
    step: function (s, p, dt) { s.d = relax(s.d, beamDelta(p), dt, p.tau); s.t += dt; },
    view: function (s, p) { return { t: s.t, delta: s.d, delta_mm: s.d * 1000, delta_cm: s.d * 100, load_N: p.m * p.g }; },
    measure: function (p) { var s = BeamBend.init(p), i; for (i = 0; i < 200; i++) BeamBend.step(s, p, 0.1); return { delta: s.d, delta_eq: beamDelta(p) }; }
  };

  // -------------------------------------------------------------------- parallelogram law (Gravesand's board)
  function vecBeta(p, a) { var s = p.P * Math.sin(a) / p.Q; return Math.asin(Math.min(1, Math.max(-1, s))); }
  function vecAlpha(p) {
    var lo = 1e-9, hi = PI / 2, i, mid;
    for (i = 0; i < 60; i++) { mid = (lo + hi) / 2; if (p.P * Math.cos(mid) + p.Q * Math.cos(vecBeta(p, mid)) > p.W) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }
  var VecForce = {
    PARAMS: { P: 1.47, Q: 1.47, W: 1.96, g: 9.8, tau: 0.8, a0: 0.05 },
    VARS: ['t', 'alpha', 'beta', 'theta', 'theta_deg', 'R', 'settled'],
    init: function (p) { return { t: 0, a: p.a0 }; },
    step: function (s, p, dt) { s.a = relax(s.a, vecAlpha(p), dt, p.tau); s.t += dt; },
    view: function (s, p) {
      var a = s.a, b = vecBeta(p, a), th = a + b;
      return { t: s.t, alpha: a, beta: b, theta: th, theta_deg: th * 180 / PI,
        R: Math.sqrt(p.P * p.P + p.Q * p.Q + 2 * p.P * p.Q * Math.cos(th)), settled: Math.abs(a - vecAlpha(p)) < 1e-4 ? 1 : 0 };
    },
    measure: function (p) {
      var a = vecAlpha(p), b = vecBeta(p, a), th = a + b;
      return { alpha: a, beta: b, theta: th, W_calc: Math.sqrt(p.P * p.P + p.Q * p.Q + 2 * p.P * p.Q * Math.cos(th)) };
    }
  };

  // ------------------------------------------------------------------------------------------ spherometer
  function sphH(p) { var d = p.R * p.R - p.l * p.l / 3; return d > 0 ? p.R - Math.sqrt(d) : p.R; }
  var Spherometer = {
    PARAMS: { R: 0.15, l: 0.045, pitch: 0.001, ndiv: 100.0, convex: 1.0, lc: 0.0 },
    VARS: ['h', 'h_mm', 'turns', 'div', 'R_meas', 'lc_mm'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var h = sphH(p), lc = p.pitch / p.ndiv, turns = Math.floor(h / p.pitch + 1e-9), div = Math.floor((h - turns * p.pitch) / lc + 0.5);
      if (div >= p.ndiv) { turns = turns + 1; div = 0; }
      return { h: h, h_mm: h * 1000, turns: turns, div: div, R_meas: h > 0 ? p.l * p.l / (6 * h) + h / 2 : 0, lc_mm: lc * 1000 };
    },
    measure: function (p) { var h = sphH(p); return { h: h, R: h > 0 ? p.l * p.l / (6 * h) + h / 2 : 0 }; }
  };

  root.HoolaKernels.register({
    K: { capillary: Capillary, searle: Searle, friction: Friction, moments: Moments, beambend: BeamBend,
      vecforce: VecForce, spherometer: Spherometer },
    TEXTBOOK: {
      cap_h: capH, searle_e: searleE,
      friction_Fmin: function (p) { return p.mu * (p.m + p.add) * p.g; },
      moments_y: function (p) { return p.m * p.x / p.M; },
      beam_delta: beamDelta,
      vec_W: function (p) { return p.W; },
      sph_R: function (p) { return p.R; }
    },
    CALCS: {
      cap_T: { label: 'T (surface tension)', unit: 'N/m', needs: ['r', 'h'],
        fn: function (r, p) { return mapMean(r, ['r', 'h'], function (x) { return x[1] * x[0] * p.rho * p.g / (2 * Math.cos(p.theta)); }, function (x) { return x[0] > 0; }); } },
      searle_Y: { label: "Y (Young's modulus)", unit: 'Pa', needs: ['m', 'e'],
        fn: function (r, p) { return mapMean(r, ['m', 'e'], function (x) { return 4 * x[0] * p.g * p.L / (PI * p.d * p.d * x[1]); }, function (x) { return x[1] > 0; }); } },
      friction_mu: { label: 'μ', unit: '', needs: ['R', 'F'],
        fn: function (r) { var rs = rows(r, ['R', 'F']), sxy = 0, sxx = 0, i; for (i = 0; i < rs.length; i++) { sxy += rs[i][0] * rs[i][1]; sxx += rs[i][0] * rs[i][0]; } return sxx > 0 ? sxy / sxx : 0; } },
      moments_m: { label: 'mass of the body', unit: 'kg', needs: ['x', 'y'],
        fn: function (r, p) { return mapMean(r, ['x', 'y'], function (x) { return p.M * x[1] / x[0]; }, function (x) { return x[0] > 0; }); } },
      beam_Y: { label: "Y (Young's modulus)", unit: 'Pa', needs: ['m', 'delta'],
        fn: function (r, p) { return mapMean(r, ['m', 'delta'], function (x) { return x[0] * p.g * Math.pow(p.L, 3) / (beamCf(p) * beamI(p) * x[1]); }, function (x) { return x[1] > 0; }); } },
      vec_W_calc: { label: 'weight of the body', unit: 'N', needs: ['P', 'Q', 'th'],
        fn: function (r) { return mapMean(r, ['P', 'Q', 'th'], function (x) { return Math.sqrt(x[0] * x[0] + x[1] * x[1] + 2 * x[0] * x[1] * Math.cos(x[2])); }); } },
      sph_R: { label: 'R (radius of curvature)', unit: 'm', needs: ['l', 'h'],
        fn: function (r) { return mapMean(r, ['l', 'h'], function (x) { return x[0] * x[0] / (6 * x[1]) + x[1] / 2; }, function (x) { return x[1] > 0; }); } },
      mix_c_liquid: { label: 'c (liquid)', unit: 'J/(kg·K)', needs: ['Tf'],
        fn: function (r, p) { return mapMean(r, ['Tf'], function (x) { return (p.m1 * p.c1 * (p.T1 - x[0]) - p.mc * p.cc * (x[0] - p.T2)) / (p.m2 * (x[0] - p.T2)); }, function (x) { return x[0] > p.T2; }); } }
    }
  });
})(typeof window !== 'undefined' ? window : this);
