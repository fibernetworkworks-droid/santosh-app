/* Prayogshala kernel pack: Class 6-10 mechanics. JavaScript twin of app/prayog/packs/mech_school.py -
   the same algorithms step for step; the server's tests run both on the same inputs and demand the same numbers.
   Change one, change the other. Kernels: track, pullblock, buoy, sucker. */
(function (root) {
  'use strict';
  var HK = root.HoolaKernels;
  if (!HK) return;
  var PI = Math.PI;
  function assign(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; if (b) for (k in b) o[k] = b[k]; return o; }
  function sub(dt, h) { var n = Math.max(1, Math.ceil(dt / h - 1e-9)); return [n, dt / n]; }

  // ---------------------------------------------------------------------- motion on a track
  var Track = {
    PARAMS: { u: 0.25, acc: 0.0, len: 1.0, mark: 0.8 }, VARS: ['t', 's', 'v', 'car_x'],
    init: function (p) { return { t: 0, s: 0, v: p.u }; },
    step: function (s, p, dt) {
      s.t += dt;
      var x = p.u * s.t + 0.5 * p.acc * s.t * s.t;
      if (x >= p.len) { s.s = p.len; s.v = 0; } else { s.s = x; s.v = p.u + p.acc * s.t; }
    },
    view: function (s) { return { t: s.t, s: s.s, v: s.v, car_x: s.s }; },
    measure: function (p) {
      var mark = Math.min(p.mark, p.len), s = Track.init(p), h = 0.0002, t = 0, prev = 0;
      while (s.t < 30.0) {
        prev = s.s;
        Track.step(s, p, h);
        if (s.s >= mark) { t = s.t - h * (s.s - mark) / Math.max(s.s - prev, 1e-12); break; }
      }
      return { t_mark: t, v_mark: p.u + p.acc * t };
    }
  };

  // ---------------------------------------------------------------------- friction: pull a block
  function pullAdv(s, p, h) {
    var M = p.m + p.load, fr = p.mu * M * p.g, drive = p.P, a, v2;
    if (s.v === 0) {
      if (Math.abs(drive) <= fr) { s.a = 0; return; }
      a = (drive - fr * (drive > 0 ? 1 : -1)) / M;
    } else a = (drive - fr * (s.v > 0 ? 1 : -1)) / M;
    v2 = s.v + a * h;
    if (s.v !== 0 && (v2 > 0) !== (s.v > 0)) { s.s += a !== 0 ? s.v * s.v / (-2 * a) : 0; s.v = 0; s.a = 0; return; }
    s.s += s.v * h + 0.5 * a * h * h; s.v = v2; s.a = a;
    if (s.s <= 0 || s.s >= p.len) { s.s = Math.min(Math.max(s.s, 0), p.len); s.v = 0; s.a = 0; }
  }
  function pullMoves(p, P) {
    var q = assign(p, { P: P, len: 1e6 }), s = { t: 0, s: 1, v: 0, a: 0 }, i;
    for (i = 0; i < 250; i++) pullAdv(s, q, 0.002);
    return s.s > 1 + 1e-9;
  }
  var PullBlock = {
    PARAMS: { mu: 0.35, m: 0.5, load: 0.0, P: 0.0, g: 9.8, len: 0.3 },
    VARS: ['t', 's', 'v', 'a', 'moving', 'N', 'f', 'P'],
    init: function () { return { t: 0, s: 0, v: 0, a: 0 }; },
    step: function (s, p, dt) { var q = sub(dt, 0.002), i; for (i = 0; i < q[0]; i++) pullAdv(s, p, q[1]); s.t += dt; },
    view: function (s, p) {
      var M = p.m + p.load;
      return { t: s.t, s: s.s, v: s.v, a: s.a, moving: s.v !== 0 ? 1 : 0, N: M * p.g, f: p.mu * M * p.g, P: p.P };
    },
    measure: function (p) {
      var lo = 0, hi = 4 * (p.m + p.load) * p.g * Math.max(p.mu, 0.25) + 1.0, i, mid;
      for (i = 0; i < 60; i++) { mid = (lo + hi) / 2; if (pullMoves(p, mid)) hi = mid; else lo = mid; }
      return { P_min: hi, N: (p.m + p.load) * p.g };
    }
  };

  // ---------------------------------------------------------------------- upthrust and density
  var Buoy = {
    PARAMS: { rho_s: 2700.0, rho_l: 998.0, V: 1.2e-4, g: 9.8, frac: 0.0, Acyl: 1.264e-3 },
    VARS: ['W', 'U', 'Wapp', 'loss', 'frac_float', 'floats', 'dh', 'level'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var fr = Math.min(Math.max(p.frac, 0), 1), W = p.rho_s * p.V * p.g, U = p.rho_l * p.g * p.V * fr, Wapp = Math.max(0, W - U);
      return { W: W, U: U, Wapp: Wapp, loss: W - Wapp, frac_float: Math.min(1, p.rho_s / p.rho_l),
        floats: p.rho_s < p.rho_l ? 1 : 0, dh: p.V * fr / p.Acyl, level: p.V * fr / p.Acyl };
    },
    measure: function (p) {
      var W = p.rho_s * p.V * p.g, U = p.rho_l * p.g * p.V, Wapp = Math.max(0, W - U), dh = p.V / p.Acyl, Vm = p.Acyl * dh;
      return { W: W, U: U, Wapp: Wapp, loss: W - Wapp, dh: dh, rho: (W / p.g) / Vm, frac_float: Math.min(1, p.rho_s / p.rho_l) };
    }
  };

  // ---------------------------------------------------------------------- atmospheric pressure
  function suckHold(p) { return (p.Patm - p.Pin) * PI * p.d * p.d / 4; }
  var Sucker = {
    PARAMS: { Patm: 101325.0, Pin: 0.0, d: 0.01, P: 0.0, g: 9.8 }, VARS: ['t', 'P', 'A', 'F_hold', 'off'],
    init: function () { return { t: 0, off: 0 }; },
    step: function (s, p, dt) { if (p.P > suckHold(p)) s.off = 1; s.t += dt; },
    view: function (s, p) { return { t: s.t, P: p.P, A: PI * p.d * p.d / 4, F_hold: suckHold(p), off: s.off }; },
    measure: function (p) {
      var lo = 0, hi = 4 * suckHold(p) + 1.0, i, mid, s;
      for (i = 0; i < 60; i++) {
        mid = (lo + hi) / 2; s = Sucker.init(p); Sucker.step(s, assign(p, { P: mid }), 0.01);
        if (s.off > 0.5) hi = mid; else lo = mid;
      }
      return { F_off: hi, A: PI * p.d * p.d / 4 };
    }
  };

  HK.register({
    K: { track: Track, pullblock: PullBlock, buoy: Buoy, sucker: Sucker },
    CALCS: {},
    TEXTBOOK: {
      track_t: function (p) {
        var mk = Math.min(p.mark, p.len);
        return Math.abs(p.acc) < 1e-12 ? mk / p.u : (-p.u + Math.sqrt(p.u * p.u + 2 * p.acc * mk)) / p.acc;
      },
      friction_Pmin: function (p) { return p.mu * (p.m + p.load) * p.g; },
      arch_loss: function (p) { return p.rho_l * p.g * p.V; },
      solid_rho: function (p) { return p.rho_s; },
      sucker_F: function (p) { return (p.Patm - p.Pin) * PI * p.d * p.d / 4; }
    }
  });
})(typeof window !== 'undefined' ? window : this);
