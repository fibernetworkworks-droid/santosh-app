/* Prayogshala kernel pack (JavaScript twin): school (Class 6-10) measurement, sound and heat physics.
   The exact twin of app/prayog/packs/wave_heat_school.py - same formulas, same loops, same numbers.
   Kernels: length_measure, conduction_fin, thermo_bath, wave_pulse. */
(function (root) {
  // in the browser the pack is appended to kernels.js (window.HoolaKernels); under node the merged file is one
  // module, so the shared api is module.exports by the time this runs
  var HK = (root && root.HoolaKernels) ||
    (typeof module !== 'undefined' && module.exports && module.exports.register ? module.exports : null);
  if (!HK) throw new Error('HoolaKernels is not loaded');

  function roundTo(value, lc) { if (lc <= 0) return value; return Math.floor(value / lc + 0.5) * lc; }
  function sub(dt, h) { var n = Math.max(1, Math.ceil(dt / h - 1e-9)); return [n, dt / n]; }
  function soundV(Tc) { return 331.3 * Math.sqrt(1 + Tc / 273.15); }

  // ------------------------------------------------------------------ measuring a length with a unit
  var LengthMeasure = {
    PARAMS: { L: 0.237, unit: 0.001, lc: 0.001, par: 0.0 },
    VARS: ['t', 'L', 'unit', 'lc', 'count', 'reading', 'par'],
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var reading = roundTo(p.L + p.par, p.lc);
      return { t: s.t || 0.0, L: p.L, unit: p.unit, lc: p.lc, count: p.unit ? p.L / p.unit : 0.0, reading: reading, par: p.par };
    },
    measure: function (p) {
      var v = LengthMeasure.view({ t: 0.0 }, p);
      return { reading: v.reading, count: v.count, units: p.unit ? v.reading / p.unit : 0.0 };
    },
  };

  // ------------------------------------------------------------------ conduction along a rod / spoon handle
  var ConductionFin = {
    PARAMS: { k: 401.0, d: 0.012, Lr: 0.3, Th: 95.0, Ts: 30.0, h: 12.0, alpha: 1.17e-4, Tmelt: 52.0, xm: 0.25, t0: 4.0 },
    VARS: ['t', 'Tx', 'Tend', 'Tmid', 'lam', 'Thot', 'frac'],
    lam: function (p) { return Math.sqrt(p.k * p.d / (4 * p.h)); },
    steady: function (p, x) {
      var lam = ConductionFin.lam(p);
      return p.Ts + (p.Th - p.Ts) * Math.cosh((p.Lr - x) / lam) / Math.cosh(p.Lr / lam);
    },
    tau: function (p, x) { return x * x / (4 * p.alpha) + p.t0; },
    at: function (p, x, t) {
      var ss = ConductionFin.steady(p, x);
      return p.Ts + (ss - p.Ts) * (1 - Math.exp(-t / ConductionFin.tau(p, x)));
    },
    melt_time: function (p, x) {
      var ss = ConductionFin.steady(p, x);
      if (ss <= p.Tmelt + 1e-9 || p.Tmelt <= p.Ts) return 0.0;
      return -ConductionFin.tau(p, x) * Math.log(1 - (p.Tmelt - p.Ts) / (ss - p.Ts));
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var t = s.t || 0.0;
      return { t: t, Tx: ConductionFin.at(p, p.xm, t), Tend: ConductionFin.at(p, p.Lr, t),
        Tmid: ConductionFin.at(p, p.Lr / 2, t), lam: ConductionFin.lam(p), Thot: p.Th,
        frac: 1 - Math.exp(-t / ConductionFin.tau(p, p.xm)) };
    },
    measure: function (p) {
      var s = ConductionFin.init(p);
      ConductionFin.step(s, p, 30 * ConductionFin.tau(p, p.Lr));
      var v = ConductionFin.view(s, p);
      return { Tx: v.Tx, Tend: v.Tend, lam: v.lam, t_melt: ConductionFin.melt_time(p, p.xm) };
    },
  };

  // ------------------------------------------------------------------ heating, melting, boiling
  var ThermoBath = {
    PARAMS: { T0: 28.0, Ts: 30.0, P: 0.0, C: 1256.0, hA: 2.0, Tp: 100.0, Q0: 0.0, lc: 0.5 },
    VARS: ['t', 'T', 'reading', 'Q', 'changing'],
    init: function (p) { return { t: 0.0, T: p.T0, Q: p.Q0 }; },
    step: function (s, p, dt) {
      var sb = sub(dt, 0.05), n = sb[0], h = sb[1], i, net;
      for (i = 0; i < n; i++) {
        net = p.P - p.hA * (s.T - p.Ts);
        if (s.Q > 0 && s.T >= p.Tp - 1e-9) {
          s.T = p.Tp;
          s.Q = s.Q - net * h;
          if (s.Q < 0) s.Q = 0.0;
        } else {
          s.T = s.T + net / p.C * h;
          if (s.Q > 0 && s.T > p.Tp) s.T = p.Tp;
        }
      }
      s.t += dt;
    },
    view: function (s, p) {
      var changing = (s.Q > 0 && Math.abs(s.T - p.Tp) < 1e-6) ? 1.0 : 0.0;
      return { t: s.t, T: s.T, reading: roundTo(s.T, p.lc), Q: s.Q, changing: changing };
    },
    measure: function (p) {
      var s = ThermoBath.init(p), hold = [], v, sum = 0, i;
      while (s.t < 6000.0 && hold.length < 5) {
        ThermoBath.step(s, p, 5.0);
        v = ThermoBath.view(s, p);
        if (v.changing > 0.5) hold.push(v.reading);
      }
      for (i = 0; i < hold.length; i++) sum += hold[i];
      var plateau = hold.length ? sum / hold.length : roundTo(p.Tp, p.lc);
      return { reading: roundTo(p.T0, p.lc), Tplateau: plateau, Tplateau_K: plateau + 273.15, T_end: s.T };
    },
  };

  // ------------------------------------------------------------------ a pulse on a slinky / string
  var WavePulse = {
    PARAMS: { Tn: 8.0, mu: 0.0725, Lspan: 3.0, nrefl: 4.0, mode: 0.0 },
    VARS: ['t', 'x', 'v', 'trips', 'running', 'mode'],
    init: function () { return { t: 0.0, d: 0.0, running: 0.0 }; },
    step: function (s, p, dt) {
      if (s.running > 0.5) s.d += Math.sqrt(p.Tn / p.mu) * dt;
      s.t += dt;
    },
    view: function (s, p) {
      var v = Math.sqrt(p.Tn / p.mu), trips = s.d / p.Lspan, leg = trips - Math.floor(trips);
      var x = (Math.floor(trips) % 2 === 0) ? leg * p.Lspan : (1 - leg) * p.Lspan;
      return { t: s.t, x: x, v: v, trips: trips, running: s.running, mode: p.mode };
    },
    measure: function (p) {
      var st = WavePulse.init(p);
      st.running = 1.0;
      var n = Math.round(p.nrefl), target = n * p.Lspan;
      while (st.d < target && st.t < 600.0) WavePulse.step(st, p, 0.001);
      return { t_trip: st.t, v_meas: st.t > 0 ? target / st.t : 0.0, v: Math.sqrt(p.Tn / p.mu) };
    },
  };

  HK.register({
    K: { length_measure: LengthMeasure, conduction_fin: ConductionFin, thermo_bath: ThermoBath, wave_pulse: WavePulse },
    TEXTBOOK: {
      length_true: function (p) { return p.L; },
      fin_Tx: function (p) { return ConductionFin.steady(p, p.xm); },
      phase_T_K: function (p) { return p.Tp + 273.15; },
      bath_T: function (p) { return p.T0; },
      wave_v: function (p) { return Math.sqrt(p.Tn / p.mu); },
    },
  });
})(typeof window !== 'undefined' ? window : this);
