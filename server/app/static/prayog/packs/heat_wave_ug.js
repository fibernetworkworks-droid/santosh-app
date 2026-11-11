/* Kernel pack (browser twin of app/prayog/packs/heat_wave_ug.py): the B.Sc. heat, thermoelectric, wave and
   ultrasound benches. Same formulas, same order of operations, so both sides give the same numbers.
     hw_searle     K = m c (Tout - Tin)(x2 - x1) / (t A (th1 - th2))      hw_lees      k = m s (dth/dt)(r + 2h)/(2r + 2h) d / (pi r^2 (th1 - th2))
     hw_tcouple    e = a (T - Tc) + q (T^2 - Tc^2)                        hw_rtd       R = R0 (1 + A t + B t^2)
     hw_melde      f = (p / l) sqrt(T / mu)                               hw_lissajous fy / fx = touches(top) / touches(side)
     hw_kundt      v_rod = v_air L_rod / d                                hw_usonic    v = 2 f d / n
   Deterministic: no randomness drawn from the system, no wall clock. */
(function (root) {
  'use strict';
  var HK = (root && root.HoolaKernels) ||
    (typeof module !== 'undefined' && module.exports && module.exports.register ? module.exports : null);
  if (!HK) throw new Error('HoolaKernels is not loaded');
  var PI = Math.PI;

  function sub(dt, h) { var n = Math.max(1, Math.ceil(dt / h - 1e-9)); return [n, dt / n]; }
  function roundTo(value, lc) { if (lc <= 0) return value; return Math.floor(value / lc + 0.5) * lc; }
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
  function gcd(a, b) { a = Math.abs(a); b = Math.abs(b); while (b) { var t = a % b; a = b; b = t; } return a ? a : 1; }
  function bath(s, p, dt) {
    var q = sub(dt, 0.05), n = q[0], h = q[1], i;
    for (i = 0; i < n; i++) {
      s.T = s.T + (p.P * s.on - p.hA * (s.T - p.Ts)) / p.C * h;
      if (s.T > p.Tcap) s.T = p.Tcap;
    }
    s.t += dt;
  }

  // ---------------------------------------------------------------------- Searle's apparatus
  var SearleBar = {
    PARAMS: { K: 401.0, r: 0.0125, x1: 0.12, x2: 0.22, Lb: 0.40, Th: 100.0, Tin: 26.0, mdot: 9.4e-4, eps: 0.9, cw: 4186.0, tau: 420.0, lc: 0.1 },
    VARS: ['t', 'th1', 'th2', 'Tin', 'Tout', 'H', 'grad', 'dth1'],
    steady: function (p) {
      var A = PI * p.r * p.r, KA = p.K * A, C = p.mdot * p.cw;
      var H = C * p.eps * (p.Th - p.Tin) / (1 + C * p.eps * p.Lb / KA), g = H / KA;
      return { A: A, H: H, g: g, th1: p.Th - g * p.x1, th2: p.Th - g * p.x2, Tout: p.Tin + H / C };
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var ss = SearleBar.steady(p), e = Math.exp(-s.t / p.tau), f = 1 - e;
      return { t: s.t, th1: p.Tin + (ss.th1 - p.Tin) * f, th2: p.Tin + (ss.th2 - p.Tin) * f, Tin: p.Tin,
        Tout: p.Tin + (ss.Tout - p.Tin) * f, H: ss.H * f, grad: ss.g * f, dth1: (ss.th1 - p.Tin) / p.tau * e };
    },
    measure: function (p) {
      var s = SearleBar.init(p);
      SearleBar.step(s, p, 30 * p.tau);
      var v = SearleBar.view(s, p), tRun = 300.0, m = p.mdot * tRun, A = PI * p.r * p.r;
      var K = m * p.cw * (v.Tout - v.Tin) * (p.x2 - p.x1) / (tRun * A * (v.th1 - v.th2));
      return { K: K, th1: v.th1, th2: v.th2, Tin: v.Tin, Tout: v.Tout, H: v.H, m: m };
    },
  };

  // ---------------------------------------------------------------------- Lee and Charlton's disc
  var LeesDisc = {
    PARAMS: { k: 1.05, d: 0.008, r: 0.025, h: 0.010, rho: 8500.0, s: 380.0, hc: 9.0, Th: 100.0, Ts: 30.0, T0: 30.0, mode: 0.0, lc: 0.1, Gd: 2.0 },
    VARS: ['t', 'T', 'th2', 'dTdt', 'mB', 'C'],
    mass: function (p) { return p.rho * PI * p.r * p.r * p.h; },
    conds: function (p) { return [p.k * PI * p.r * p.r / p.d, p.hc * PI * (p.r * p.r + 2 * p.r * p.h)]; },
    th2: function (p) { var g = LeesDisc.conds(p); return (g[0] * p.Th + g[1] * p.Ts) / (g[0] + g[1]); },
    init: function (p) { return { t: 0.0, T: p.T0 }; },
    step: function (s, p, dt) {
      var q = sub(dt, 0.05), n = q[0], h = q[1], C = LeesDisc.mass(p) * p.s, g = LeesDisc.conds(p), G1 = g[0], G2 = g[1];
      var Gb = p.hc * (2 * PI * p.r * p.r + 2 * PI * p.r * p.h), i, rate;
      for (i = 0; i < n; i++) {
        if (p.mode < 0.5) rate = (G1 * (p.Th - s.T) - G2 * (s.T - p.Ts)) / C;
        else if (p.mode < 1.5) rate = -Gb * (s.T - p.Ts) / C;
        else rate = (p.Gd * (p.Th - s.T) - Gb * (s.T - p.Ts)) / C;
        s.T = s.T + rate * h;
      }
      s.t += dt;
    },
    view: function (s, p) {
      var C = LeesDisc.mass(p) * p.s, g = LeesDisc.conds(p), G1 = g[0], G2 = g[1];
      var Gb = p.hc * (2 * PI * p.r * p.r + 2 * PI * p.r * p.h);
      var rate;
      if (p.mode < 0.5) rate = (G1 * (p.Th - s.T) - G2 * (s.T - p.Ts)) / C;
      else if (p.mode < 1.5) rate = -Gb * (s.T - p.Ts) / C;
      else rate = (p.Gd * (p.Th - s.T) - Gb * (s.T - p.Ts)) / C;
      return { t: s.t, T: s.T, th2: LeesDisc.th2(p), dTdt: rate, mB: LeesDisc.mass(p), C: C };
    },
    measure: function (p) {
      var a = HK.assign(p, { mode: 0.0 }), s = LeesDisc.init(a);
      LeesDisc.step(s, a, 20000.0);
      var th2 = s.T, b = HK.assign(p, { mode: 1.0 }), s2 = { t: 0.0, T: th2 };
      var rate = -LeesDisc.view(s2, b).dTdt, m = LeesDisc.mass(p);
      var k = (m * p.s * rate * (p.r + 2 * p.h) / (2 * p.r + 2 * p.h)) * p.d / (PI * p.r * p.r * (p.Th - th2));
      return { k: k, th2: th2, rate: rate, th1: p.Th };
    },
  };

  // ---------------------------------------------------------------------- thermocouple
  var ThermocoupleBath = {
    PARAMS: { a: 38.65e-6, q: 4.14e-8, Tc: 0.0, kp: 0.008, G: 0.0, P: 150.0, C: 1500.0, hA: 1.0, Ts: 30.0, T0: 30.0, on: 0.0, Tcap: 100.0, lc: 0.1, Th: 60.0 },
    VARS: ['t', 'T', 'reading', 'e', 'l', 'Vout', 'Tn'],
    emf: function (p, T) { return p.a * (T - p.Tc) + p.q * (T * T - p.Tc * p.Tc); },
    neutral: function (p) { return p.q < 0 ? -p.a / (2 * p.q) : 0.0; },
    init: function (p) { return { t: 0.0, T: p.T0, on: p.on }; },
    step: function (s, p, dt) { bath(s, p, dt); },
    view: function (s, p) {
      var e = ThermocoupleBath.emf(p, s.T);
      return { t: s.t, T: s.T, reading: roundTo(s.T, p.lc), e: e, l: e / p.kp, Vout: p.G * e, Tn: ThermocoupleBath.neutral(p) };
    },
    measure: function (p) {
      var s = { t: 0.0, T: p.Th, on: 0.0 }, v = ThermocoupleBath.view(s, p);
      return { e: v.e, l: v.l, Vout: v.Vout, slope: p.a + 2 * p.q * p.Th, Tn: v.Tn, emf: v.e };
    },
  };

  // ---------------------------------------------------------------------- resistance thermometer
  var ResistanceThermometer = {
    PARAMS: { R0: 100.0, A: 3.9083e-3, B: -5.775e-7, Rref: 100.0, Vs: 5.0, P: 150.0, C: 1500.0, hA: 1.0, Ts: 30.0, T0: 30.0, on: 0.0, Tcap: 100.0, lc: 0.1, Tm: 50.0, mode: 0.0 },
    VARS: ['t', 'T', 'reading', 'R', 'Vg'],
    res: function (p, T) { return p.R0 * (1 + p.A * T + p.B * T * T); },
    init: function (p) { return { t: 0.0, T: p.T0, on: p.on }; },
    step: function (s, p, dt) { bath(s, p, dt); },
    view: function (s, p) {
      var R = ResistanceThermometer.res(p, s.T);
      return { t: s.t, T: s.T, reading: roundTo(s.T, p.lc), R: R, Vg: p.Vs * (R / (R + p.Rref) - 0.5) };
    },
    measure: function (p) {
      var Rt = ResistanceThermometer.res, R0 = Rt(p, 0.0), R100 = Rt(p, 100.0), dt = 0.5;
      var slope = (Rt(p, p.Tm + dt) - Rt(p, p.Tm - dt)) / (2 * dt);
      return { alpha: (R100 - R0) / (100.0 * R0), R: Rt(p, p.Tm), slope: slope, R0: R0, R100: R100 };
    },
  };

  // ---------------------------------------------------------------------- Melde's experiment
  var MeldeString = {
    PARAMS: { f: 100.0, mu: 0.0011, L: 1.0, M: 0.07, g: 9.8, mode: 0.0, w: 0.012, p0: 4.0 },
    VARS: ['t', 'T', 'v', 'fs', 'loops', 'p', 'amp'],
    fs: function (p) { return p.mode < 0.5 ? p.f / 2 : p.f; },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var T = p.M * p.g, v = T > 0 ? Math.sqrt(T / p.mu) : 0.0, fs = MeldeString.fs(p);
      var loops = v > 0 ? 2 * p.L * fs / v : 0.0, pr = Math.floor(loops + 0.5), d = loops - pr;
      var amp = pr >= 1 ? 1 / (1 + Math.pow(d / p.w, 2)) : 0.0;
      return { t: s.t, T: T, v: v, fs: fs, loops: loops, p: pr, amp: amp };
    },
    measure: function (p) {
      var fs = MeldeString.fs(p), v = 2 * p.L * fs / p.p0, T = p.mu * v * v, M = T / p.g, k = p.mode < 0.5 ? 1.0 : 0.5;
      return { M: M, T: T, f: k * (p.p0 / p.L) * Math.sqrt(T / p.mu), v: v };
    },
  };

  // ---------------------------------------------------------------------- Lissajous figures
  var LissajousCRO = {
    PARAMS: { fx: 100.0, fy: 150.0, phi: 0.7854, ax: 1.0, ay: 1.0, mode: 0.0 },
    VARS: ['t', 'x', 'y', 'ratio', 'nt', 'ns', 'y0', 'ymax', 'phi_meas'],
    frac: function (p) {
      var a = Math.floor(p.fy * 10 + 0.5), b = Math.floor(p.fx * 10 + 0.5), g = gcd(a, b);
      return [Math.floor(a / g), Math.floor(b / g)];
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var f = LissajousCRO.frac(p), t = s.t, y0 = p.ay * Math.sin(p.phi);
      return { t: t, x: p.ax * Math.sin(2 * PI * p.fx * t), y: p.ay * Math.sin(2 * PI * p.fy * t + p.phi), ratio: p.fy / p.fx,
        nt: f[0], ns: f[1], y0: y0, ymax: p.ay, phi_meas: Math.asin(Math.max(-1.0, Math.min(1.0, y0 / p.ay))) };
    },
    measure: function (p) {
      var f = LissajousCRO.frac(p), v = LissajousCRO.view({ t: 0.0 }, p);
      return { fy: p.fx * f[0] / f[1], nt: f[0], ns: f[1], phi: v.phi_meas };
    },
  };

  // ---------------------------------------------------------------------- Kundt's tube
  var KundtTube = {
    PARAMS: { vr: 3436.0, Lr: 1.0, Tc: 25.0, rho: 8470.0, Lt: 1.0, w: 0.18, Lp: 0.5 },
    VARS: ['t', 'f', 'vair', 'd', 'clarity', 'n'],
    vair: function (p) { return 331.3 * Math.sqrt(1 + p.Tc / 273.15); },
    spacing: function (p) { return KundtTube.vair(p) * p.Lr / p.vr; },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var d = KundtTube.spacing(p), q = p.Lp / d, n = Math.floor(q + 0.5), off = q - n;
      var clarity = n >= 1 ? 1 / (1 + Math.pow(off / p.w, 2)) : 0.0;
      return { t: s.t, f: p.vr / (2 * p.Lr), vair: KundtTube.vair(p), d: d, clarity: clarity, n: n };
    },
    measure: function (p) {
      var d = KundtTube.spacing(p), xFirst = d, xLast = 8 * d, dMeas = (xLast - xFirst) / 7.0;
      var v = KundtTube.vair(p) * p.Lr / dMeas;
      return { vr: v, d: dMeas, Y: p.rho * v * v, vair: KundtTube.vair(p) };
    },
  };

  // ---------------------------------------------------------------------- ultrasonic interferometer
  var UltrasonicInterferometer = {
    PARAMS: { v: 1482.0, f: 2.0e6, rho: 998.2, x0: 0.00012, Ib: 40.0, Ia: 25.0, alpha: 20.0 },
    VARS: ['t', 'lam', 'I', 'x'],
    current: function (p, x) {
      var lam = p.v / p.f, c = Math.cos(2 * PI * (x - p.x0) / lam);
      return p.Ib + p.Ia * Math.exp(-p.alpha * x) * c * c;
    },
    init: function () { return { t: 0.0, x: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t, lam: p.v / p.f, I: UltrasonicInterferometer.current(p, s.x), x: s.x }; },
    measure: function (p) {
      var lam = p.v / p.f, xs = [], j;
      for (j = 0; j < 11; j++) xs.push(p.x0 + (j + 1) * lam / 2);
      var d = xs[10] - xs[0], v = 2 * p.f * d / 10.0;
      return { v: v, d: d, lam: 2 * d / 10.0, beta: 1 / (p.rho * v * v) };
    },
  };

  // ---------------------------------------------------------------------- calcs
  function fit2(xs, ys) {
    var n = xs.length, i, x, y, s1 = 0, s2 = 0, s3 = 0, s4 = 0, t0 = 0, t1 = 0, t2 = 0;
    if (n < 3) return null;
    for (i = 0; i < n; i++) s1 += xs[i];
    for (i = 0; i < n; i++) s2 += xs[i] * xs[i];
    for (i = 0; i < n; i++) s3 += xs[i] * xs[i] * xs[i];
    for (i = 0; i < n; i++) s4 += xs[i] * xs[i] * xs[i] * xs[i];
    for (i = 0; i < n; i++) t0 += ys[i];
    for (i = 0; i < n; i++) t1 += xs[i] * ys[i];
    for (i = 0; i < n; i++) t2 += xs[i] * xs[i] * ys[i];
    var det = n * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2);
    if (Math.abs(det) < 1e-300) return null;
    var d0 = t0 * (s2 * s4 - s3 * s3) - s1 * (t1 * s4 - s3 * t2) + s2 * (t1 * s3 - s2 * t2);
    var d1 = n * (t1 * s4 - s3 * t2) - t0 * (s1 * s4 - s3 * s2) + s2 * (s1 * t2 - t1 * s2);
    var d2 = n * (s2 * t2 - t1 * s3) - s1 * (s1 * t2 - t1 * s2) + t0 * (s1 * s3 - s2 * s2);
    x = y = 0;
    return [d0 / det, d1 / det, d2 / det];
  }
  function col(r, j, scale) { var out = [], i; for (i = 0; i < r.length; i++) out.push(r[i][j] * (scale === undefined ? 1 : scale)); return out; }
  function tcSlope(rs, p) {
    var r = rows(rs, ['T', 'l']), f = fit2(col(r, 0), col(r, 1, p.kp));
    return f ? f[1] + 2 * f[2] * 50.0 : 0.0;
  }
  function tcNeutral(rs, p) {
    var r = rows(rs, ['T', 'Vout']), g = p.G ? p.G : 1.0, ys = [], i;
    for (i = 0; i < r.length; i++) ys.push(r[i][1] / g);
    var f = fit2(col(r, 0), ys);
    return f && f[2] !== 0 ? -f[1] / (2 * f[2]) : 0.0;
  }
  function rtdSlope(rs, p) {
    var r = rows(rs, ['T', 'R']), f = fit2(col(r, 0), col(r, 1));
    return f ? f[1] + 2 * f[2] * 50.0 : 0.0;
  }
  function rtdAlpha(rs, p) {
    var r = rows(rs, ['T', 'R']), i, lo, hi;
    if (r.length < 2) return 0.0;
    lo = r[0]; hi = r[0];
    for (i = 1; i < r.length; i++) if (Math.abs(r[i][0]) < Math.abs(lo[0])) lo = r[i];
    for (i = 1; i < r.length; i++) if (Math.abs(r[i][0] - 100.0) < Math.abs(hi[0] - 100.0)) hi = r[i];
    if (lo[1] === 0 || hi[0] === lo[0]) return 0.0;
    return (hi[1] - lo[1]) / ((hi[0] - lo[0]) * lo[1]);
  }
  function mapMean(rs, keys, fn, keep) {
    var r = rows(rs, keys), out = [], i;
    for (i = 0; i < r.length; i++) if (!keep || keep(r[i])) out.push(fn(r[i]));
    return mean(out);
  }
  function lissFy(rs) { return mapMean(rs, ['fx', 'nt', 'ns'], function (x) { return x[0] * x[1] / x[2]; }, function (x) { return x[2] > 0; }); }
  function usonicV(rs, p) {
    var r = rows(rs, ['n', 'x']).sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
    if (r.length < 2 || r[r.length - 1][0] === r[0][0]) return 0.0;
    return 2 * p.f * (r[r.length - 1][1] - r[0][1]) / (r[r.length - 1][0] - r[0][0]);
  }

  HK.register({
    K: { hw_searle: SearleBar, hw_lees: LeesDisc, hw_tcouple: ThermocoupleBath, hw_rtd: ResistanceThermometer,
      hw_melde: MeldeString, hw_lissajous: LissajousCRO, hw_kundt: KundtTube, hw_usonic: UltrasonicInterferometer },
    CALCS: {
      hw_searle_K: { label: 'K (thermal conductivity)', unit: 'W/(m·K)', needs: ['m', 't', 'dTw', 'dth'],
        fn: function (r, p) { return mapMean(r, ['m', 't', 'dTw', 'dth'], function (x) { return x[0] * p.cw * x[2] * (p.x2 - p.x1) / (x[1] * PI * p.r * p.r * x[3]); }, function (x) { return x[1] > 0 && x[3] > 0; }); } },
      hw_lees_k: { label: 'k (thermal conductivity)', unit: 'W/(m·K)', needs: ['th1', 'th2', 'dtdt'],
        fn: function (r, p) { return mapMean(r, ['th1', 'th2', 'dtdt'], function (x) { return LeesDisc.mass(p) * p.s * x[2] * (p.r + 2 * p.h) / (2 * p.r + 2 * p.h) * p.d / (PI * p.r * p.r * (x[0] - x[1])); }, function (x) { return x[0] - x[1] > 0; }); } },
      hw_tc_slope: { label: 'dE/dT at 50 °C', unit: 'V/K', needs: ['T', 'l'], fn: tcSlope },
      hw_tc_neutral: { label: 'neutral temperature', unit: '°C', needs: ['T', 'Vout'], fn: tcNeutral },
      hw_rtd_slope: { label: 'dR/dt at 50 °C', unit: 'Ω/K', needs: ['T', 'R'], fn: rtdSlope },
      hw_rtd_alpha: { label: 'α (0 to 100 °C)', unit: '1/K', needs: ['T', 'R'], fn: rtdAlpha },
      hw_melde_f: { label: 'f (tuning fork)', unit: 'Hz', needs: ['M', 'p'],
        fn: function (r, p) { return mapMean(r, ['M', 'p'], function (x) { return (p.mode < 0.5 ? 1.0 : 0.5) * (x[1] / p.L) * Math.sqrt(x[0] * p.g / p.mu); }, function (x) { return x[0] > 0; }); } },
      hw_liss_fy: { label: 'f (unknown)', unit: 'Hz', needs: ['fx', 'nt', 'ns'], fn: lissFy },
      hw_liss_phi: { label: 'φ', unit: 'rad', needs: ['y0', 'ymax'],
        fn: function (r) { return mapMean(r, ['y0', 'ymax'], function (x) { return Math.asin(Math.max(-1.0, Math.min(1.0, x[0] / x[1]))); }, function (x) { return x[1] > 0; }); } },
      hw_kundt_v: { label: 'v (rod)', unit: 'm/s', needs: ['Lrod', 'dd'],
        fn: function (r, p) { return mapMean(r, ['Lrod', 'dd'], function (x) { return KundtTube.vair(p) * x[0] / x[1]; }, function (x) { return x[1] > 0; }); } },
      hw_usonic_v: { label: 'v (ultrasound)', unit: 'm/s', needs: ['n', 'x'], fn: usonicV },
    },
    TEXTBOOK: {
      hw_searle_K: function (p) { return p.K; },
      hw_lees_k: function (p) { return p.k; },
      hw_tc_emf: function (p) { return p.a * (p.Th - p.Tc) + p.q * (p.Th * p.Th - p.Tc * p.Tc); },
      hw_rtd_alpha: function (p) { return p.A + 100.0 * p.B; },
      hw_rtd_slope: function (p) { return p.R0 * (p.A + 2.0 * p.B * p.Tm); },
      hw_melde_f: function (p) { return p.f; },
      hw_liss_fy: function (p) { return p.fy; },
      hw_kundt_v: function (p) { return p.vr; },
      hw_usonic_v: function (p) { return p.v; },
    },
  });
})(typeof window !== 'undefined' ? window : this);
