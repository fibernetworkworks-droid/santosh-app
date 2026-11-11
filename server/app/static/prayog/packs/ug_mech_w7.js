/* Kernel pack (browser twin of app/prayog/packs/ug_mech_w7.py): B.Sc. oscillation, elasticity, heat-flow and
   harmonic-analysis benches. Same formulas, same order of operations, so both sides give the same numbers.
     w7_pend      T = 2π√(Leq/g)(1 + θ0²/16), A = A0 exp(−γt)     w7_kater    Bessel's formula for g
     w7_coupled   κ = (ω2² − ω1²)/(ω2² + ω1²)                      w7_spring   T = 2π√((m + ms/3)/k), k = ηr⁴/(4NR³)
     w7_torsion   Maxwell's needle, Searle's two bars              w7_stefan   P = eσA(T⁴ − T0⁴)
     w7_cbarnes   J = (V1I1 − V2I2)/((m1 − m2) s ΔT)               w7_angstrom D = Δx²/(2 Δt ln(A1/A2))
     w7_cool      (ml cl + W)/(mw cw + W) = tl/tw                  w7_fourier  harmonic amplitudes by the Fourier integral
   Deterministic: no randomness, no wall clock. */
(function (root) {
  'use strict';
  var PI = Math.PI;

  function sub(dt, h) { var n = Math.max(1, Math.ceil(dt / h - 1e-9)); return [n, dt / n]; }
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
  function decay(f, y0, h, npk, tmax) {
    var y = y0.slice(), t = 0, pk = [], y2, fr, last;
    while (t < tmax && pk.length < npk) {
      y2 = rk4(f, y, h);
      if (y[1] > 0 && y2[1] <= 0 && y[0] > 0) { fr = y[1] / (y[1] - y2[1]); pk.push([t + h * fr, y[0] + fr * (y2[0] - y[0])]); }
      y = y2; t = t + h;
    }
    if (pk.length < 2) return 0;
    last = pk[pk.length - 1];
    if (last[1] <= 0 || last[0] <= pk[0][0]) return 0;
    return Math.log(pk[0][1] / last[1]) / (last[0] - pk[0][0]);
  }
  function copy(p) { var o = {}, k; for (k in p) if (Object.prototype.hasOwnProperty.call(p, k)) o[k] = p[k]; return o; }

  // ---------------------------------------------------------------------- simple / bar pendulum, damped
  function pendLeq(p) { if (p.kind < 0.5) return p.L; return p.h > 0 ? (p.Lb * p.Lb / 12 + p.h * p.h) / p.h : 0; }
  function pendF(p) { var c = p.g / pendLeq(p), b = 2 * p.gam; return function (y) { return [y[1], -c * Math.sin(y[0]) - b * y[1]]; }; }
  function pendT0(p) { return 2 * PI * Math.sqrt(pendLeq(p) / p.g); }
  function pendLimSeries(p) { var a = 11.0 / 3072.0, b = 1.0 / 16.0; return Math.sqrt((-b + Math.sqrt(b * b + 4 * a * p.eps)) / (2 * a)); }
  var Pendulum = {
    PARAMS: { kind: 0.0, L: 1.0, Lb: 1.0, h: 0.3, g: 9.8, th0: 0.0873, gam: 0.0, eps: 0.01, mode: 0.0 },
    VARS: ['t', 'th', 'th_deg', 'om', 'Leq', 'T0'],
    leq: pendLeq, T0: pendT0,
    init: function (p) { return { t: 0, y: [p.th0, 0] }; },
    step: function (s, p, dt) { var q = sub(dt, 0.002), f = pendF(p), i; for (i = 0; i < q[0]; i++) s.y = rk4(f, s.y, q[1]); s.t += dt; },
    view: function (s, p) { return { t: s.t, th: s.y[0], th_deg: s.y[0] * 180 / PI, om: s.y[1], Leq: pendLeq(p), T0: pendT0(p) }; },
    measure: function (p) {
      var f = pendF(p), T = period(f, [p.th0, 0], 0.0005, 200.0), q, fq, Tsmall, lo, hi, mid, i;
      var out = { T: T, T0: pendT0(p), g: T > 0 ? 4 * PI * PI * pendLeq(p) / (T * T) : 0, gam: 0, th_lim: 0 };
      if (p.mode > 0.5 && p.mode < 1.5) out.gam = decay(f, [p.th0, 0], 0.001, 11, 400.0);
      if (p.mode > 1.5) {
        q = copy(p); q.gam = 0; fq = pendF(q); Tsmall = period(fq, [0.02, 0], 0.001, 200.0); lo = 0.05; hi = 1.2;
        for (i = 0; i < 14; i++) { mid = (lo + hi) / 2; if (period(fq, [mid, 0], 0.001, 200.0) > (1 + p.eps) * Tsmall) hi = mid; else lo = mid; }
        out.th_lim = (lo + hi) / 2;
      }
      return out;
    },
  };

  // ---------------------------------------------------------------------- Kater's reversible pendulum
  function katerF(p, h) { var c = p.g * h / (p.k2 + h * h); return function (y) { return [y[1], -c * Math.sin(y[0])]; }; }
  var Kater = {
    PARAMS: { h1: 0.60, h2: 0.35, k2: 0.21, g: 9.8, th0: 0.05, side: 0.0 },
    VARS: ['t', 'th', 'th_deg', 'om', 'T_calc'],
    hh: function (p) { return p.side < 0.5 ? p.h1 : p.h2; },
    init: function (p) { return { t: 0, y: [p.th0, 0] }; },
    step: function (s, p, dt) { var q = sub(dt, 0.002), f = katerF(p, Kater.hh(p)), i; for (i = 0; i < q[0]; i++) s.y = rk4(f, s.y, q[1]); s.t += dt; },
    view: function (s, p) { var h = Kater.hh(p); return { t: s.t, th: s.y[0], th_deg: s.y[0] * 180 / PI, om: s.y[1], T_calc: 2 * PI * Math.sqrt((p.k2 + h * h) / (p.g * h)) }; },
    measure: function (p) {
      var T1 = period(katerF(p, p.h1), [p.th0, 0], 0.0005, 200.0), T2 = period(katerF(p, p.h2), [p.th0, 0], 0.0005, 200.0);
      var den = (T1 * T1 + T2 * T2) / (p.h1 + p.h2) + (T1 * T1 - T2 * T2) / (p.h1 - p.h2);
      return { T1: T1, T2: T2, g: den > 0 ? 8 * PI * PI / den : 0 };
    },
  };

  // ---------------------------------------------------------------------- two coupled oscillators
  function cplW(p) {
    var w1, w2;
    if (p.kind < 0.5) { w1 = p.g / p.L; w2 = w1 + 2 * p.kc * p.a * p.a / (p.m * p.L * p.L); }
    else { w1 = p.k / p.m; w2 = (p.k + 2 * p.kc) / p.m; }
    return [w1, w2];
  }
  function cplF(p) { var w = cplW(p), w1 = w[0], c = (w[1] - w[0]) / 2, b = 2 * p.gam;
    return function (y) { return [y[1], -w1 * y[0] - c * (y[0] - y[2]) - b * y[1], y[3], -w1 * y[2] - c * (y[2] - y[0]) - b * y[3]]; }; }
  function cplY0(p, mode) { if (mode < 0.5) return [p.A0, 0, p.A0, 0]; if (mode < 1.5) return [p.A0, 0, -p.A0, 0]; return [p.A0, 0, 0, 0]; }
  function cplKappa(p) { var w = cplW(p); return (w[1] - w[0]) / (w[1] + w[0]); }
  var Coupled = {
    PARAMS: { kind: 0.0, L: 0.6, g: 9.8, a: 0.3, m: 0.2, kc: 2.0, k: 4.0, gam: 0.0, mode: 0.0, A0: 0.08 },
    VARS: ['t', 'x1', 'x2', 'v1', 'v2', 'w1', 'w2'],
    w: cplW, y0: cplY0,
    init: function (p) { return { t: 0, y: cplY0(p, p.mode) }; },
    step: function (s, p, dt) { var q = sub(dt, 0.002), f = cplF(p), i; for (i = 0; i < q[0]; i++) s.y = rk4(f, s.y, q[1]); s.t += dt; },
    view: function (s, p) { var w = cplW(p); return { t: s.t, x1: s.y[0], x2: s.y[2], v1: s.y[1], v2: s.y[3], w1: Math.sqrt(w[0]), w2: Math.sqrt(w[1]) }; },
    measure: function (p) {
      var f = cplF(p), T1 = period(f, cplY0(p, 0.0), 0.0005, 200.0), T2 = period(f, cplY0(p, 1.0), 0.0005, 200.0);
      var kap = T1 > 0 && T2 > 0 ? (T1 * T1 - T2 * T2) / (T1 * T1 + T2 * T2) : 0;
      var gam = p.gam > 0 ? decay(f, cplY0(p, 0.0), 0.001, 11, 400.0) : 0;
      return { T1: T1, T2: T2, kappa: kap, Tb: T1 > T2 ? T1 * T2 / (T1 - T2) : 0, gam: gam };
    },
  };

  // ---------------------------------------------------------------------- loaded helical spring(s)
  function sprK1(p) { if (p.geo > 0.5) return p.eta * Math.pow(p.rw, 4) / (4 * p.Nt * Math.pow(p.Rc, 3)); return p.k1; }
  function sprKeff(p) { var k1 = sprK1(p); if (p.mode < 0.5) return k1; if (p.mode < 1.5) return k1 * p.k2 / (k1 + p.k2); return k1 + p.k2; }
  var SpringLoad = {
    PARAMS: { k1: 20.0, k2: 30.0, mode: 0.0, ms: 0.03, m: 0.2, g: 9.8, x0: 0.02, geo: 0.0, eta: 7.93e10, rw: 0.0005, Rc: 0.01, Nt: 60.0 },
    VARS: ['t', 'x', 'v', 'ext', 'keff'],
    keff: sprKeff,
    f: function (p) { var c = sprKeff(p) / (p.m + p.ms / 3); return function (y) { return [y[1], -c * y[0]]; }; },
    init: function (p) { return { t: 0, y: [p.x0, 0] }; },
    step: function (s, p, dt) { var q = sub(dt, 0.002), f = SpringLoad.f(p), i; for (i = 0; i < q[0]; i++) s.y = rk4(f, s.y, q[1]); s.t += dt; },
    view: function (s, p) { var k = sprKeff(p); return { t: s.t, x: s.y[0], v: s.y[1], ext: p.m * p.g / k, keff: k }; },
    measure: function (p) {
      var T = period(SpringLoad.f(p), [p.x0, 0], 0.0002, 100.0), k = T > 0 ? 4 * PI * PI * (p.m + p.ms / 3) / (T * T) : 0;
      return { T: T, ext: p.m * p.g / sprKeff(p), k: k, eta: 4 * p.Nt * Math.pow(p.Rc, 3) * k / Math.pow(p.rw, 4) };
    },
  };

  // ---------------------------------------------------------------------- Maxwell's needle / Searle's two bars
  function torI(p, pos) {
    var mo, mi;
    if (p.kind < 0.5) { mo = pos < 0.5 ? p.ms : p.mh; mi = pos < 0.5 ? p.mh : p.ms;
      return p.I0 + 2 * mo * Math.pow(3 * p.Ln / 8, 2) + 2 * mi * Math.pow(p.Ln / 8, 2); }
    return p.Mb * (p.Lbar * p.Lbar + p.wb * p.wb) / 12;
  }
  function torC(p, pos) { var mod = (p.kind > 0.5 && pos < 0.5) ? p.Y : p.eta; return PI * mod * Math.pow(p.rw, 4) / (2 * p.lw); }
  function torF(p, pos) { var c = torC(p, pos) / torI(p, pos); return function (y) { return [y[1], -c * y[0]]; }; }
  var TorsionRig = {
    PARAMS: { kind: 0.0, eta: 8.22e10, Y: 2.119e11, rw: 0.0004, lw: 0.5, Ln: 0.4, ms: 0.25, mh: 0.06, I0: 0.002, Mb: 0.45, Lbar: 0.3, wb: 0.012, pos: 0.0, th0: 0.2 },
    VARS: ['t', 'th', 'th_deg', 'om', 'T_calc'],
    inertia: torI,
    init: function (p) { return { t: 0, y: [p.th0, 0] }; },
    step: function (s, p, dt) { var q = sub(dt, 0.002), f = torF(p, p.pos), i; for (i = 0; i < q[0]; i++) s.y = rk4(f, s.y, q[1]); s.t += dt; },
    view: function (s, p) { return { t: s.t, th: s.y[0], th_deg: s.y[0] * 180 / PI, om: s.y[1], T_calc: 2 * PI * Math.sqrt(torI(p, p.pos) / torC(p, p.pos)) }; },
    measure: function (p) {
      var T1 = period(torF(p, 0.0), [p.th0, 0], 0.0005, 400.0), T2 = period(torF(p, 1.0), [p.th0, 0], 0.0005, 400.0), r4 = Math.pow(p.rw, 4), eta, inert;
      if (p.kind < 0.5) { eta = 2 * PI * p.lw * (p.ms - p.mh) * p.Ln * p.Ln / (r4 * (T1 * T1 - T2 * T2)); return { T1: T1, T2: T2, eta: eta, Y: 0, sigma: 0 }; }
      inert = torI(p, 0.0);
      return { T1: T1, T2: T2, Y: 8 * PI * inert * p.lw / (T1 * T1 * r4), eta: 8 * PI * inert * p.lw / (T2 * T2 * r4), sigma: T2 * T2 / (2 * T1 * T1) - 1 };
    },
  };

  // ---------------------------------------------------------------------- Stefan's law with a tungsten lamp
  function stefT(p, V) {
    var lo = p.T0, hi = 4000.0, mid, R, i;
    for (i = 0; i < 60; i++) { mid = (lo + hi) / 2; R = p.R0 * Math.pow(mid / p.T0, p.nR);
      if (V * V / R > p.em * p.sigma * p.A * (Math.pow(mid, 4) - Math.pow(p.T0, 4))) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }
  function stefRead(p, V) { var T = stefT(p, V), R = p.R0 * Math.pow(T / p.T0, p.nR), cur = V / R, Tm = p.T0 * Math.pow((V / cur) / p.R0, 1 / p.nR); return [cur, V / cur, Tm, V * cur]; }
  var StefanLamp = {
    PARAMS: { sigma: 5.670374e-8, em: 0.35, A: 2.0e-5, T0: 300.0, R0: 1.0, nR: 1.2, V: 6.0 },
    VARS: ['t', 'V', 'I', 'R', 'T', 'P'],
    read: stefRead,
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var r = stefRead(p, p.V); return { t: s.t, V: p.V, I: r[0], R: r[1], T: r[2], P: r[3] }; },
    measure: function (p) { var a = stefRead(p, p.V), b = stefRead(p, 1.5 * p.V);
      return { sigma: a[3] / (p.em * p.A * (Math.pow(a[2], 4) - Math.pow(p.T0, 4))), n: Math.log(b[3] / a[3]) / Math.log(b[2] / a[2]), T: a[2], P: a[3], I: a[0] }; },
  };

  // ---------------------------------------------------------------------- Callendar and Barnes' continuous flow
  function cbDT(p, V, mdot) { return (V * V / p.Rh) / (p.J * p.s * mdot + p.hl); }
  var CallendarBarnes = {
    PARAMS: { J: 4.1855, s: 1.0, hl: 0.25, mdot: 1.5, mdot2: 0.9, V: 6.0, Rh: 2.0, Tin: 25.0, tau: 40.0 },
    VARS: ['t', 'dT', 'I', 'P', 'Tout'],
    steady: cbDT,
    init: function () { return { t: 0, dT: 0 }; },
    step: function (s, p, dt) { var q = sub(dt, 0.05), tgt = cbDT(p, p.V, p.mdot), i; for (i = 0; i < q[0]; i++) s.dT = s.dT + (tgt - s.dT) * (q[1] / p.tau); s.t += dt; },
    view: function (s, p) { return { t: s.t, dT: s.dT, I: p.V / p.Rh, P: p.V * p.V / p.Rh, Tout: p.Tin + s.dT }; },
    measure: function (p) {
      var d1 = cbDT(p, p.V, p.mdot), lo = 0.0, hi = p.V * 3, mid, i, V2, P1, P2;
      for (i = 0; i < 50; i++) { mid = (lo + hi) / 2; if (cbDT(p, mid, p.mdot2) < d1) lo = mid; else hi = mid; }
      V2 = (lo + hi) / 2; P1 = p.V * p.V / p.Rh; P2 = V2 * V2 / p.Rh;
      return { J: (P1 - P2) / ((p.mdot - p.mdot2) * p.s * d1), dT: d1, V2: V2, P1: P1, P2: P2 };
    },
  };

  // ---------------------------------------------------------------------- Angstrom's method
  function angAB(p) { var w = 2 * PI / p.tau, r = Math.sqrt(p.mu * p.mu + w * w) / p.D; return [Math.sqrt((r + p.mu / p.D) / 2), Math.sqrt((r - p.mu / p.D) / 2), w]; }
  function angT(p, x, t) { var ab = angAB(p); return p.Tm + p.A0 * Math.exp(-ab[0] * x) * Math.sin(ab[2] * t - ab[1] * x); }
  function angScan(p, x) {
    var n = 3600, hi = -1e30, lo = 1e30, tpk = 0, i, t, v;
    for (i = 0; i < n; i++) { t = p.tau * i / n; v = angT(p, x, t); if (v > hi) { hi = v; tpk = t; } if (v < lo) lo = v; }
    return [(hi - lo) / 2, tpk];
  }
  var AngstromBar = {
    PARAMS: { D: 1.1625e-4, tau: 120.0, x1: 0.05, x2: 0.15, mu: 0.002, A0: 20.0, Tm: 60.0, rho: 8960.0, cp: 385.0 },
    VARS: ['t', 'T1', 'T2'],
    temp: angT,
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t, T1: angT(p, p.x1, s.t), T2: angT(p, p.x2, s.t) }; },
    measure: function (p) {
      var s1 = angScan(p, p.x1), s2 = angScan(p, p.x2), lag = s2[1] - s1[1], dx, D;
      if (lag < 0) lag += p.tau;
      dx = p.x2 - p.x1; D = dx * dx / (2 * lag * Math.log(s1[0] / s2[0]));
      return { D: D, K: D * p.rho * p.cp, A1: s1[0], A2: s2[0], lag: lag };
    },
  };

  // ---------------------------------------------------------------------- specific heat by cooling
  function coolC(p, which) { var W = p.mc * p.cc; if (which < 0.5) return p.rhow * p.Vol * p.cw + W; return p.rhol * p.Vol * p.cl + W; }
  function coolTime(p, which) {
    var C = coolC(p, which), T = p.T0, t = 0.0, h = 0.05, ta = -1.0, T2;
    while (t < 1.0e5) {
      T2 = T - p.hA * (T - p.Ts) / C * h;
      if (ta < 0 && T >= p.Ta && T2 < p.Ta) ta = t + h * (T - p.Ta) / (T - T2);
      if (T >= p.Tb && T2 < p.Tb) return t + h * (T - p.Tb) / (T - T2) - ta;
      T = T2; t = t + h;
    }
    return 0.0;
  }
  var CoolingPair = {
    PARAMS: { cl: 2010.0, rhol: 810.0, Vol: 6.0e-5, cw: 4186.0, rhow: 998.2, mc: 0.05, cc: 385.0, hA: 0.35, Ts: 28.0, T0: 72.0, Ta: 65.0, Tb: 55.0, which: 0.0 },
    VARS: ['t', 'T', 'C'],
    heatCap: coolC,
    init: function (p) { return { t: 0, T: p.T0 }; },
    step: function (s, p, dt) { var q = sub(dt, 0.05), C = coolC(p, p.which), i; for (i = 0; i < q[0]; i++) s.T = s.T - p.hA * (s.T - p.Ts) / C * q[1]; s.t += dt; },
    view: function (s, p) { return { t: s.t, T: s.T, C: coolC(p, p.which) }; },
    measure: function (p) { var tw = coolTime(p, 0.0), tl = coolTime(p, 1.0), W = p.mc * p.cc, mw = p.rhow * p.Vol, ml = p.rhol * p.Vol;
      return { tw: tw, tl: tl, cl: ((mw * p.cw + W) * tl / tw - W) / ml }; },
  };

  // ---------------------------------------------------------------------- harmonics of a complex wave
  function wave(p, ph) {
    var v;
    ph = ph - Math.floor(ph);
    if (p.shape < 0.5) return ph < 0.5 ? 1.0 : -1.0;
    if (p.shape < 1.5) { if (ph < 0.25) return 4 * ph; if (ph < 0.75) return 2 - 4 * ph; return 4 * ph - 4; }
    v = Math.sin(2 * PI * ph);
    if (v > p.clip) return p.clip;
    if (v < -p.clip) return -p.clip;
    return v;
  }
  function harm(p, n) { var N = 4096, acc = 0.0, i, ph; for (i = 0; i < N; i++) { ph = (i + 0.5) / N; acc += wave(p, ph) * Math.sin(2 * PI * n * ph); } return p.A * 2 * acc / N; }
  function harmExact(p, n) {
    var al, first;
    if (p.shape < 0.5) return p.A * 4 / (n * PI);
    if (p.shape < 1.5) return p.A * 8 / (n * n * PI * PI) * Math.sin(n * PI / 2);
    al = Math.asin(p.clip);
    if (n < 1.5) first = (al - Math.sin(2 * al) / 2) / 2;
    else first = (Math.sin((n - 1) * al) / (n - 1) - Math.sin((n + 1) * al) / (n + 1)) / 2;
    return p.A * 4 / PI * (first + p.clip * Math.cos(n * al) / n);
  }
  var Harmonics = {
    PARAMS: { shape: 0.0, A: 2.0, f0: 1000.0, clip: 0.5, n: 3.0 },
    VARS: ['t', 'y', 'an', 'a1', 'ratio'],
    wave: wave, harm: harm,
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var an = harm(p, p.n), a1 = harm(p, 1.0); return { t: s.t, y: p.A * wave(p, s.t * p.f0), an: an, a1: a1, ratio: Math.abs(an / a1) }; },
    measure: function (p) { var an = harm(p, p.n), a1 = harm(p, 1.0); return { an: Math.abs(an), a1: Math.abs(a1), ratio: Math.abs(an / a1) }; },
  };

  // ---------------------------------------------------------------------- trolley on an inclined plane
  function trolMu(p) { return p.lock > 0.5 ? p.mus : p.mur; }
  function trolA(p) { var a = p.g * (Math.sin(p.angle) - trolMu(p) * Math.cos(p.angle)); return a > 0 ? a : 0.0; }
  var Trolley = {
    PARAMS: { angle: 0.4363, mus: 0.3, mur: 0.012, lock: 1.0, g: 9.8, d: 1.0 },
    VARS: ['t', 's', 'v', 'a'],
    acc: trolA, mu: trolMu,
    init: function () { return { t: 0.0, s: 0.0, v: 0.0 }; },
    step: function (s, p, dt) { var a = trolA(p); s.s += s.v * dt + 0.5 * a * dt * dt; s.v += a * dt; s.t += dt; },
    view: function (s, p) { return { t: s.t, s: s.s, v: s.v, a: trolA(p) }; },
    measure: function (p) { var a = trolA(p), tg; if (a <= 0) return { a: 0.0, tg: 0.0, mu: 0.0 }; tg = Math.sqrt(2 * p.d / a);
      return { a: a, tg: tg, mu: Math.tan(p.angle) - 2 * p.d / (p.g * Math.cos(p.angle) * tg * tg) }; },
  };

  // ---------------------------------------------------------------------- two-dimensional collision of two pucks
  function c2Geo(p) { var D = 2 * p.R, b = p.b, cx = -Math.sqrt(D * D - b * b); return [(cx - p.x0) / p.u, cx, [-cx / D, -b / D]]; }
  function c2After(p) { var g = c2Geo(p), n = g[2], un = p.u * n[0], m1 = p.m1, m2 = p.m2, e = p.e, j = (1 + e) * m1 * m2 / (m1 + m2) * un;
    return [[p.u - j / m1 * n[0], -j / m1 * n[1]], [j / m2 * n[0], j / m2 * n[1]]]; }
  function c2Pos(p, t) { var g = c2Geo(p), tc = g[0], cx = g[1], v, d; if (t <= tc) return [[p.x0 + p.u * t, p.b], [0.0, 0.0]];
    v = c2After(p); d = t - tc; return [[cx + v[0][0] * d, p.b + v[0][1] * d], [v[1][0] * d, v[1][1] * d]]; }
  function c2Ke(p) { var n = c2Geo(p)[2]; return 1 - (1 - p.e * p.e) * p.m2 / (p.m1 + p.m2) * n[0] * n[0]; }
  var Collision2D = {
    PARAMS: { m1: 0.2, m2: 0.3, u: 0.5, b: 0.03, R: 0.04, e: 1.0, x0: -0.4 },
    VARS: ['t', 'x1', 'y1', 'x2', 'y2'],
    geo: c2Geo, pos: c2Pos,
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var q = c2Pos(p, s.t); return { t: s.t, x1: q[0][0], y1: q[0][1], x2: q[1][0], y2: q[1][1] }; },
    measure: function (p) { var v = c2After(p), v1 = v[0], v2 = v[1], px = p.m1 * v1[0] + p.m2 * v2[0], py = p.m1 * v1[1] + p.m2 * v2[1];
      var ke = (p.m1 * (v1[0] * v1[0] + v1[1] * v1[1]) + p.m2 * (v2[0] * v2[0] + v2[1] * v2[1])) / (p.m1 * p.u * p.u);
      return { px: px / (p.m1 * p.u), py: py / (p.m1 * p.u), ke: ke, v1x: v1[0], v1y: v1[1], v2x: v2[0], v2y: v2[1] }; },
  };

  root.HoolaKernels.register({
    K: { w7_pend: Pendulum, w7_kater: Kater, w7_coupled: Coupled, w7_spring: SpringLoad, w7_torsion: TorsionRig, w7_stefan: StefanLamp,
      w7_cbarnes: CallendarBarnes, w7_angstrom: AngstromBar, w7_cool: CoolingPair, w7_fourier: Harmonics, w7_trolley: Trolley, w7_coll2d: Collision2D },
    CALCS: {},
    TEXTBOOK: {
      w7_pend_T: function (p) { return pendT0(p) * (1 + p.th0 * p.th0 / 16); },
      w7_pend_g: function (p) { return p.g; },
      w7_pend_gam: function (p) { return p.gam; },
      w7_pend_lim: pendLimSeries,
      w7_kater_g: function (p) { return p.g; },
      w7_coupled_kappa: cplKappa,
      w7_coupled_gam: function (p) { return p.gam; },
      w7_spring_T: function (p) { return 2 * PI * Math.sqrt((p.m + p.ms / 3) / sprKeff(p)); },
      w7_spring_k: sprKeff,
      w7_spring_eta: function (p) { return p.eta; },
      w7_tors_eta: function (p) { return p.eta; },
      w7_tors_Y: function (p) { return p.Y; },
      w7_tors_sigma: function (p) { return p.Y / (2 * p.eta) - 1; },
      w7_stefan_sigma: function (p) { return p.sigma; },
      w7_stefan_n: function () { return 4.0; },
      w7_cbarnes_J: function (p) { return p.J; },
      w7_angstrom_D: function (p) { return p.D; },
      w7_cool_cl: function (p) { return p.cl; },
      w7_fourier_ratio: function (p) { return Math.abs(harmExact(p, p.n) / harmExact(p, 1.0)); },
      w7_trolley_mu: trolMu,
      w7_trolley_t: function (p) { var a = trolA(p); return a > 0 ? Math.sqrt(2 * p.d / a) : 0.0; },
      w7_coll2d_ke: c2Ke,
      w7_coll2d_px: function () { return 1.0; },
    },
  });
})(typeof window !== 'undefined' ? window : this);
