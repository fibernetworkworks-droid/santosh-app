/* Kernel pack `elec11`: the exact JavaScript twin of app/prayog/packs/elec11.py. Same formulas, same algorithms,
   same numbers (the server's tests run both and compare). Most Class XII electricity set-ups need no new kernel at
   all - the shared `circuit` kernel already solves them - so this pack carries their TEXTBOOK formulas plus the
   kernels the solver cannot do: a Zener diode in reverse breakdown, a common-emitter transistor, a light-dependent
   resistor, single-slit diffraction and Malus's law. Deterministic: no randomness, no wall clock. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, VT = 0.025852;

  // ------------------------------------------------------------------ TEXTBOOK (the circuit-kernel labs)
  function galv_half_ig(p) { return p.Eb * p.Sh / (p.Rh * (p.Rg + p.Sh) + p.Rg * p.Sh); }
  function galv_volt_ig(p) { return p.Eb / (p.Rint + p.Rser + p.Rg); }
  function galv_amm_ig(p) { return p.Eb * p.Sht / ((p.Rl + p.Ram) * (p.Rg + p.Sht) + p.Rg * p.Sht); }
  function pot_balance(p) { return p.Ec * (p.Rh + p.Rw) / (p.Rw * p.E0); }
  function pot_drop(p) { return p.E0 * p.Rw * p.lj / (p.Rh + p.Rw); }
  function bridge_comb_l(p) { var x = p.par < 0.5 ? p.R1 + p.R2 : p.R1 * p.R2 / (p.R1 + p.R2); return p.Rk / (p.Rk + x); }

  // ------------------------------------------------------------------ Zener diode
  var zener = {
    PARAMS: { Eb: -1.0, Rs: 1000.0, Vz: 5.1, Rz: 10.0, Is: 5e-9, nD: 1.8, knee: 0.02 },
    VARS: ['t', 'V_Z', 'I_Z', 'V_Rs', 'P_Z'],
    current: function (v, p) {
      var fwd = p.Is * (Math.exp(Math.min(v / (p.nD * VT), 80.0)) - 1.0);
      var u = -v - p.Vz, k = p.knee;
      var bd = (u + Math.sqrt(u * u + k * k)) / (2 * p.Rz);
      return fwd - bd;
    },
    solve: function (p) {
      var lo = -Math.abs(p.Vz) - Math.abs(p.Eb) - 5.0, hi = Math.abs(p.Eb) + 5.0, i, mid;
      for (i = 0; i < 200; i++) {
        mid = (lo + hi) / 2;
        if (zener.current(mid, p) * p.Rs + mid > p.Eb) hi = mid; else lo = mid;
      }
      return (lo + hi) / 2;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var v = zener.solve(p), i = zener.current(v, p);
      return { t: s.t || 0, V_Z: v, I_Z: i, V_Rs: p.Eb - v, P_Z: Math.abs(v * i) }; },
    measure: function (p) { var v = zener.solve(p); return { V_Z: v, I_Z: zener.current(v, p), Vz_mag: -v }; }
  };
  function zener_Vr(p) { var e = -p.Eb; return -(p.Vz + p.Rz * (e - p.Vz) / (p.Rs + p.Rz)); }

  // ------------------------------------------------------------------ transistor (common emitter)
  var transistor = {
    PARAMS: { Vbb: 2.0, Rb: 100000.0, Vcc: 6.0, Rc: 1000.0, beta: 200.0, VA: 80.0, Is: 1e-14, nB: 1.0, Vsat: 0.06 },
    VARS: ['t', 'I_b', 'I_c', 'V_be', 'V_ce', 'gain'],
    base: function (p) {
      var lo = 0, hi = Math.max(p.Vbb, 0) / Math.max(p.Rb, 1e-9) + 1e-12, i, mid, ib;
      for (i = 0; i < 200; i++) {
        mid = (lo + hi) / 2;
        if (mid * p.Rb + p.nB * VT * Math.log(mid / p.Is + 1.0) > p.Vbb) hi = mid; else lo = mid;
      }
      ib = (lo + hi) / 2;
      return [ib, p.nB * VT * Math.log(ib / p.Is + 1.0)];
    },
    icAt: function (vce, ib, p) {
      return p.beta * ib * (1 + Math.max(vce, 0) / p.VA) * (1 - Math.exp(-Math.max(vce, 0) / p.Vsat));
    },
    collector: function (p) {
      var ib = transistor.base(p)[0], lo = 0, hi = Math.max(p.Vcc, 0), i, mid, vce;
      for (i = 0; i < 200; i++) {
        mid = (lo + hi) / 2;
        if (mid + transistor.icAt(mid, ib, p) * p.Rc > p.Vcc) hi = mid; else lo = mid;
      }
      vce = (lo + hi) / 2;
      return [transistor.icAt(vce, ib, p), vce];
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var b = transistor.base(p), c = transistor.collector(p);
      return { t: s.t || 0, I_b: b[0], I_c: c[0], V_be: b[1], V_ce: c[1], gain: b[0] > 0 ? c[0] / b[0] : 0 };
    },
    measure: function (p) {
      var b = transistor.base(p), c = transistor.collector(p);
      return { I_b: b[0], I_c: c[0], V_be: b[1], V_ce: c[1] };
    }
  };
  function trans_ic(p) {
    var ib = transistor.base(p)[0], g = p.beta * ib;
    return g * (1 + p.Vcc / p.VA) / (1 + g * p.Rc / p.VA);
  }

  // ------------------------------------------------------------------ light-dependent resistor
  var ldr = {
    PARAMS: { d: 0.2, Iv: 2.0, Eamb: 5.0, A: 60000.0, gamma: 0.8, Eb: 5.0, Rs: 1000.0 },
    VARS: ['t', 'E_lux', 'R_ldr', 'I_c', 'V_ldr'],
    lux: function (p) { return p.Iv / (p.d * p.d) + p.Eamb; },
    res: function (p) { return p.A * Math.pow(ldr.lux(p), -p.gamma); },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var r = ldr.res(p), i = p.Eb / (p.Rs + r);
      return { t: s.t || 0, E_lux: ldr.lux(p), R_ldr: r, I_c: i, V_ldr: i * r }; },
    measure: function (p) { return { R_ldr: ldr.res(p), E_lux: ldr.lux(p) }; }
  };
  function ldr_R(p) { return p.A * Math.pow(p.Iv / (p.d * p.d) + p.Eamb, -p.gamma); }

  // ------------------------------------------------------------------ single-slit diffraction
  var diffraction = {
    PARAMS: { a: 0.0001, lam: 6.5e-7, D: 1.0, x: 0.0, I0: 1.0 },
    VARS: ['t', 'inten', 'theta', 'x_first_min', 'width'],
    intenAt: function (x, p) {
      var th = Math.atan2(x, p.D), b = PI * p.a * Math.sin(th) / p.lam;
      return Math.abs(b) < 1e-12 ? p.I0 : p.I0 * Math.pow(Math.sin(b) / b, 2);
    },
    xOfB: function (b, p) { var s = Math.min(b * p.lam / (PI * p.a), 0.999999); return p.D * Math.tan(Math.asin(s)); },
    minX: function (p, m) {
      m = m || 1;
      var lo = diffraction.xOfB((m - 0.5) * PI, p), hi = diffraction.xOfB((m + 0.5) * PI, p), i, a1, a2;
      for (i = 0; i < 200; i++) {
        a1 = lo + (hi - lo) / 3; a2 = hi - (hi - lo) / 3;
        if (diffraction.intenAt(a1, p) < diffraction.intenAt(a2, p)) hi = a2; else lo = a1;
      }
      return (lo + hi) / 2;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var x1 = diffraction.minX(p, 1);
      return { t: s.t || 0, inten: diffraction.intenAt(p.x, p), theta: Math.atan2(p.x, p.D), x_first_min: x1, width: 2 * x1 }; },
    measure: function (p) { return { x1: diffraction.minX(p, 1), x2: diffraction.minX(p, 2) }; }
  };
  function diff_x1(p) { return p.D * Math.tan(Math.asin(p.lam / p.a)); }

  // ------------------------------------------------------------------ polarisation (Malus)
  var polaroid = {
    PARAMS: { I0: 1000.0, theta: 0.0, theta0: 0.0, k1: 0.8, k2: 0.8, leak: 0.002 },
    VARS: ['t', 'inten', 'frac'],
    at: function (p, th) { var c = Math.cos(th - p.theta0); return p.I0 * 0.5 * p.k1 * p.k2 * (c * c + p.leak); },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var i = polaroid.at(p, p.theta); return { t: s.t || 0, inten: i, frac: i / Math.max(p.I0, 1e-12) }; },
    measure: function (p) { return { inten: polaroid.at(p, p.theta), imax: polaroid.at(p, p.theta0) }; }
  };
  function malus_I(p) { var c = Math.cos(p.theta - p.theta0); return p.I0 * 0.5 * p.k1 * p.k2 * (c * c + p.leak); }

  H.register({
    K: { zener: zener, transistor: transistor, ldr: ldr, diffraction: diffraction, polaroid: polaroid },
    TEXTBOOK: { galv_half_ig: galv_half_ig, galv_volt_ig: galv_volt_ig, galv_amm_ig: galv_amm_ig,
      pot_balance: pot_balance, pot_drop: pot_drop, bridge_comb_l: bridge_comb_l, zener_Vr: zener_Vr,
      trans_ic: trans_ic, ldr_R: ldr_R, diff_x1: diff_x1, malus_I: malus_I }
  });
})(typeof window !== 'undefined' ? window : this);
