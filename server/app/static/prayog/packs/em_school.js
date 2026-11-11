/* Prayogshala kernel pack (JavaScript twin of app/prayog/packs/em_school.py): school electricity, magnetism and
   static electricity. The same algorithms step for step - the server's test suite runs both on the same inputs and
   demands the same numbers. No window, no document, no network: this file also loads inside node. */
(function (root) {
  'use strict';
  var HK = root.HoolaKernels || (typeof module !== 'undefined' && module.exports);
  if (!HK || !HK.register) return;
  var PI = Math.PI, MU0 = 4e-7 * PI, EPS0 = 8.8541878128e-12, KE = 1.0 / (4 * PI * EPS0);
  var SEGS = 2000, HSTEP = 0.0005;

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
      if (y[0] > 0 && 0 >= y2[0]) cross.push(t + h * y[0] / (y[0] - y2[0]));
      y = y2; t = t + h;
    }
    return cross.length === 2 ? cross[1] - cross[0] : 0;
  }
  function bisect(f, lo, hi, n) {
    var flo = f(lo), i, mid, fm;
    for (i = 0; i < (n || 80); i++) {
      mid = (lo + hi) / 2; fm = f(mid);
      if ((fm > 0) === (flo > 0)) { lo = mid; flo = fm; } else { hi = mid; }
    }
    return (lo + hi) / 2;
  }
  function area(dia) { return PI * dia * dia / 4; }

  /* ------------------------------------------------------------------ the field of a current */
  var coilfield = {
    PARAMS: { kind: 0.0, Eb: 3.0, Rs: 6.0, d: 0.03, N: 1.0, a: 0.05, Lsol: 0.30, nsol: 1000.0,
      mur: 1.0, BH: 4.0e-5, rev: 1.0, wireL: 1.0, key: 1.0 },
    VARS: ['t', 'I', 'B', 'theta', 'tan_theta'],
    current: function (p) { return (p.Eb / Math.max(p.Rs, 1e-9)) * (p.key >= 0.5 ? 1.0 : 0.0) * (p.rev >= 0 ? 1.0 : -1.0); },
    field: function (p) {
      var I = Math.abs(coilfield.current(p)), B = 0, i, L, d, dx, x, r2, a, z, dl, turns;
      if (I === 0.0) return 0.0;
      if (p.kind < 0.5) {
        L = p.wireL; d = Math.max(p.d, 1e-6); dx = L / SEGS;
        for (i = 0; i < SEGS; i++) {
          x = -L / 2 + (i + 0.5) * dx; r2 = x * x + d * d;
          B += MU0 * I * dx * d / (4 * PI * r2 * Math.sqrt(r2));
        }
        return B;
      }
      if (p.kind < 1.5) {
        a = p.a; z = p.d; dl = 2 * PI * a / SEGS; r2 = a * a + z * z;
        for (i = 0; i < SEGS; i++) B += MU0 * I * dl * a / (4 * PI * r2 * Math.sqrt(r2));
        return B * p.N;
      }
      a = p.a; L = p.Lsol; turns = Math.max(1, Math.round(p.nsol * L));
      for (i = 0; i < turns; i++) {
        z = -L / 2 + (i + 0.5) * (L / turns); r2 = a * a + z * z;
        B += MU0 * I * a * a / (2 * r2 * Math.sqrt(r2));
      }
      return B * p.mur;
    },
    init: function (p) { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var B = coilfield.field(p), sgn = coilfield.current(p) >= 0 ? 1.0 : -1.0, tt = sgn * B / Math.max(p.BH, 1e-12);
      return { t: s.t, I: coilfield.current(p), B: sgn * B, tan_theta: tt, theta: Math.atan(tt) };
    },
    measure: function (p) {
      var B = coilfield.field(p), tt = B / Math.max(p.BH, 1e-12);
      return { B: B, I: Math.abs(coilfield.current(p)), tan_theta: tt, theta: Math.atan(tt) };
    }
  };

  /* ------------------------------------------------------------------ a bar magnet */
  var barmagnet = {
    PARAMS: { m: 1.0, Lbar: 0.05, wbar: 0.01, mass: 0.03, BH: 4.0e-5, d: 0.07, theta0: 0.1745, dnp: 0.13 },
    VARS: ['t', 'theta', 'omega', 'B_eq', 'np_d', 'F'],
    qm: function (p) { return p.m / Math.max(p.Lbar, 1e-9); },
    b_eq: function (p, d) {
      var q = barmagnet.qm(p), l = p.Lbar / 2, r = Math.sqrt(l * l + d * d), bx = 0, i, sgn, k;
      for (i = 0; i < 2; i++) {
        sgn = i === 0 ? 1.0 : -1.0;
        k = MU0 * (sgn * q) / (4 * PI * r * r * r);
        bx += k * (0.0 - sgn * l);
      }
      return Math.abs(bx);
    },
    inertia: function (p) { return p.mass * (p.Lbar * p.Lbar + p.wbar * p.wbar) / 12; },
    force: function (p, d) {
      var q = barmagnet.qm(p), l = p.Lbar / 2, f = 0, A = [[1.0, l], [-1.0, -l]], Bp = [[1.0, d - l], [-1.0, d + l]], i, j, r;
      for (i = 0; i < 2; i++) for (j = 0; j < 2; j++) {
        r = Bp[j][1] - A[i][1];
        f += MU0 * (A[i][0] * q) * (Bp[j][0] * q) / (4 * PI * r * r);
      }
      return f;
    },
    ode: function (p) { var w2 = p.m * p.BH / barmagnet.inertia(p); return function (y) { return [y[1], -w2 * Math.sin(y[0])]; }; },
    init: function (p) { return { t: 0.0, y: [p.theta0, 0.0] }; },
    step: function (s, p, dt) {
      var f = barmagnet.ode(p), n = Math.max(1, Math.ceil(dt / HSTEP - 1e-9)), h = dt / n, i;
      for (i = 0; i < n; i++) s.y = rk4(f, s.y, h);
      s.t += dt;
    },
    view: function (s, p) {
      return { t: s.t, theta: s.y[0], omega: s.y[1], B_eq: barmagnet.b_eq(p, p.dnp), np_d: 0.0, F: barmagnet.force(p, p.d) };
    },
    measure: function (p) {
      var d = bisect(function (x) { return barmagnet.b_eq(p, x) - p.BH; }, 0.005, 2.0);
      var T = period(barmagnet.ode(p), [p.theta0, 0.0], HSTEP, 120.0);
      return { np_d: d, T: T, F: barmagnet.force(p, p.d), B_eq: barmagnet.b_eq(p, p.dnp) };
    }
  };

  /* ------------------------------------------------------------------ static electricity */
  var estatic = {
    PARAMS: { q: 3.4e-9, Lth: 0.2, mass: 1.0e-4, g: 9.8, charged: 1.0 },
    VARS: ['t', 'theta', 'r', 'F', 'q'],
    theta: function (p) {
      if (p.charged < 0.5 || p.q === 0.0) return 0.0;
      var kq2 = KE * p.q * p.q, mg = p.mass * p.g;
      return bisect(function (th) { var r = 2 * p.Lth * Math.sin(th); return Math.tan(th) - kq2 / (r * r * mg); }, 1e-5, PI / 2 - 1e-4);
    },
    init: function (p) { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var th = estatic.theta(p), r = 2 * p.Lth * Math.sin(th), F = r > 0 ? KE * p.q * p.q / (r * r) : 0.0;
      return { t: s.t, theta: th, r: r, F: F, q: p.q };
    },
    measure: function (p) { var v = estatic.view({ t: 0.0 }, p); return { r: v.r, theta: v.theta, F: v.F }; }
  };

  /* ------------------------------------------------------------------ heating effect of a current */
  var jouleheat = {
    PARAMS: { Eb: 6.0, rint: 0.5, rho: 1.09e-6, Lw: 0.5, dia: 0.000559, mw: 0.1, cw: 4186.0,
      hloss: 0.0, Ta: 28.0, tsec: 180.0, key: 1.0 },
    VARS: ['t', 'T', 'dT', 'I', 'R', 'P'],
    wire_r: function (p) { return p.rho * p.Lw / area(p.dia); },
    current: function (p) { return p.key < 0.5 ? 0.0 : p.Eb / (jouleheat.wire_r(p) + p.rint); },
    power: function (p) { var I = jouleheat.current(p); return I * I * jouleheat.wire_r(p); },
    init: function (p) { return { t: 0.0, T: p.Ta }; },
    step: function (s, p, dt) {
      var n = Math.max(1, Math.ceil(dt / 0.01 - 1e-9)), h = dt / n, cap = p.mw * p.cw, i;
      for (i = 0; i < n; i++) s.T += h * (jouleheat.power(p) - p.hloss * (s.T - p.Ta)) / cap;
      s.t += dt;
    },
    view: function (s, p) {
      return { t: s.t, T: s.T, dT: s.T - p.Ta, I: jouleheat.current(p), R: jouleheat.wire_r(p), P: jouleheat.power(p) };
    },
    measure: function (p) {
      var s = jouleheat.init(p), left = p.tsec, h;
      while (left > 1e-9) { h = Math.min(1.0, left); jouleheat.step(s, p, h); left -= h; }
      return { dT: s.T - p.Ta, T: s.T, I: jouleheat.current(p), R: jouleheat.wire_r(p), P: jouleheat.power(p) };
    }
  };

  /* ------------------------------------------------------------------ a real wire, measured in a real circuit */
  var WNET = { net: { nodes: 4, els: [
    { id: 'E', kind: 'V', a: 1, b: 0, value: 'Eb' },
    { id: 'K', kind: 'S', a: 1, b: 4, param: 'key' },
    { id: 'AM', kind: 'R', a: 4, b: 2, value: 0.01 },
    { id: 'RH', kind: 'R', a: 2, b: 3, value: { param: 'Rh', k: 1, c: 0.01 } },
    { id: 'RX', kind: 'R', a: 3, b: 0, value: 'Rxcalc' },
    { id: 'VM', kind: 'R', a: 3, b: 0, value: 1000000.0 }] } };

  var wirecircuit = {
    PARAMS: { Eb: 3.0, rho: 1.09e-6, Lw: 1.0, dia: 0.000559, Rh: 2.0, key: 1.0 },
    VARS: ['t', 'I_AM', 'V_VM', 'R', 'Rwire'],
    wire_r: function (p) { return p.rho * p.Lw / area(p.dia); },
    _p: function (p) { var q = HK.assign(p, { Rxcalc: wirecircuit.wire_r(p) }); return q; },
    init: function (p) { return HK.K.circuit.init(wirecircuit._p(p), WNET); },
    step: function (s, p, dt) { HK.K.circuit.step(s, wirecircuit._p(p), dt, WNET); },
    view: function (s, p) {
      var v = HK.K.circuit.view(s, wirecircuit._p(p), WNET), i = v.I_AM;
      return { t: v.t, I_AM: i, V_VM: v.V_VM, R: i !== 0 ? v.V_VM / i : 0.0, Rwire: wirecircuit.wire_r(p) };
    },
    measure: function (p) {
      var q = wirecircuit._p(p), s = HK.K.circuit.init(q, WNET), v = HK.K.circuit.view(s, q, WNET), i = v.I_AM;
      return { R: i !== 0 ? v.V_VM / i : 0.0, I_AM: i, V_VM: v.V_VM };
    }
  };

  function cfield_B(p) {
    var I = Math.abs(p.Eb / Math.max(p.Rs, 1e-9)) * (p.key >= 0.5 ? 1.0 : 0.0), L, d, a, z;
    if (p.kind < 0.5) { L = p.wireL; d = Math.max(p.d, 1e-6); return MU0 * I / (2 * PI * d) * (L / 2) / Math.sqrt(d * d + L * L / 4); }
    if (p.kind < 1.5) { a = p.a; z = p.d; return MU0 * p.N * I * a * a / (2 * Math.pow(a * a + z * z, 1.5)); }
    a = p.a; L = p.Lsol;
    return MU0 * p.mur * p.nsol * I * (L / 2) / Math.sqrt(a * a + L * L / 4);
  }

  HK.register({
    K: { coilfield: coilfield, barmagnet: barmagnet, estatic: estatic, jouleheat: jouleheat, wirecircuit: wirecircuit },
    TEXTBOOK: {
      ser_R: function (p) { return p.R1 + p.R2; },
      par_R: function (p) { return p.R1 * p.R2 / (p.R1 + p.R2); },
      bulb_I: function (p) { return p.Eb / (p.Rb + p.rint); },
      tester_I: function (p) { return p.Eb / (p.Rb + p.rint + p.Rsam); },
      cfield_B: cfield_B,
      cfield_tan: function (p) { return cfield_B(p) / p.BH; },
      bm_npeq: function (p) { return Math.sqrt(Math.pow(MU0 * p.m / (4 * PI * p.BH), 2.0 / 3.0) - Math.pow(p.Lbar / 2, 2)); },
      bm_T: function (p) { return 2 * PI * Math.sqrt(barmagnet.inertia(p) / (p.m * p.BH)); },
      bm_F: function (p) {
        return MU0 * Math.pow(barmagnet.qm(p), 2) / (4 * PI)
          * (1 / Math.pow(p.d - p.Lbar, 2) - 2 / Math.pow(p.d, 2) + 1 / Math.pow(p.d + p.Lbar, 2));
      },
      es_r: function (p) { return Math.pow(2 * KE * p.q * p.q * p.Lth / (p.mass * p.g), 1.0 / 3.0); },
      joule_dT: function (p) { return jouleheat.power(p) * p.tsec / (p.mw * p.cw); },
      wire_R: function (p) { return p.rho * p.Lw / area(p.dia); }
    }
  });
})(typeof window !== 'undefined' ? window : this);
