/* Kernel pack `sn_elec`: the exact JavaScript twin of app/prayog/packs/sn_elec.py. Same formulas, same algorithms, same
   numbers (the server's tests run both and compare). Sensor, instrument, analog and communication benches of the
   undergraduate syllabus. Deterministic: fixed sample counts, exact exponential steps between events, no randomness
   and no wall clock. Every kernel is prefixed `sn_`. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, VT = 0.025852, EPS0 = 8.8541878128e-12, QE = 1.602176634e-19, HP = 6.62607015e-34, CL = 2.99792458e8, NW = 2400;

  function sum(a) { var s = 0, i; for (i = 0; i < a.length; i++) s += a[i]; return s; }
  function maxOf(a) { var m = a[0], i; for (i = 1; i < a.length; i++) if (a[i] > m) m = a[i]; return m; }
  function minOf(a) { var m = a[0], i; for (i = 1; i < a.length; i++) if (a[i] < m) m = a[i]; return m; }
  function cross(y, dt, level, rising) {
    var out = [], i, a, b;
    for (i = 1; i < y.length; i++) {
      a = y[i - 1] - level; b = y[i] - level;
      if (rising && a < 0 && b >= 0 && b !== a) out.push((i - 1 + (0 - a) / (b - a)) * dt);
      else if (!rising && a >= 0 && b < 0) out.push((i - 1 + (0 - a) / (b - a)) * dt);
    }
    return out;
  }
  function stat(extra) {
    var o = { init: function () { return { t: 0.0 }; }, step: function (s, p, dt) { s.t += dt; } };
    var k; for (k in extra) o[k] = extra[k];
    return o;
  }

  // ===================================================================================== LVDT
  var sn_lvdt = stat({
    PARAMS: { x: 0.0, Vp: 3.0, fex: 2500.0, S: 20.0, xs: 0.05, Vq: 0.0015, xu: 0.0037 },
    VARS: ['t', 'x_mm', 'Vout_mV', 'Vpp_mV', 'phase'],
    NS: 400,
    wave: function (p) {
      var n = 400, vs = p.Vp * p.S * p.x / (1.0 + Math.pow(p.x / p.xs, 2)), a = Math.sqrt(2.0) * vs, q = Math.sqrt(2.0) * p.Vq, tt = [], vv = [], i, ph;
      for (i = 0; i < n; i++) {
        ph = 2.0 * PI * 2.0 * (i + 0.5) / n;
        tt.push((i + 0.5) / n * 2.0 / p.fex);
        vv.push(a * Math.sin(ph) + q * Math.cos(ph));
      }
      return [tt, vv];
    },
    read: function (p) {
      var w = sn_lvdt.wave(p), vv = w[1], n = vv.length, acc = 0, i, ph;
      for (i = 0; i < n; i++) { ph = 2.0 * PI * 2.0 * (i + 0.5) / n; acc += vv[i] * (Math.sin(ph) >= 0 ? 1.0 : -1.0); }
      return [(acc / n) * PI / (2.0 * Math.sqrt(2.0)), maxOf(vv) - minOf(vv)];
    },
    view: function (s, p) {
      var r = sn_lvdt.read(p);
      return { t: s.t || 0.0, x_mm: p.x * 1000.0, Vout_mV: r[0] * 1000.0, Vpp_mV: r[1] * 1000.0, phase: p.x >= 0 ? 0.0 : 180.0 };
    },
    measure: function (p) { var r = sn_lvdt.read(p); return { Vout: r[0], Vpp: r[1] }; }
  });
  function lvdt_v(p) { return p.Vp * p.S * p.x; }

  // ===================================================================================== strain gauge
  var sn_strain = stat({
    PARAMS: { m: 0.5, L: 0.2, b: 0.025, h: 0.002, E: 200.0e9, GF: 2.0, Vs: 5.0, Rg: 350.0, nb: 1.0, G: 100.0, Voff: 0.0032, g: 9.80665, mu: 0.773 },
    VARS: ['t', 'eps_ue', 'Vb_mV', 'Vout_V', 'dR'],
    strain: function (p) { return 6.0 * p.m * p.g * p.L / (p.E * p.b * p.h * p.h); },
    bridge: function (p) {
      var d = p.GF * sn_strain.strain(p), k = Math.round(p.nb);
      if (k === 1) return p.Vs * d / (2.0 * (2.0 + d));
      if (k === 2) return p.Vs * d / 2.0;
      return p.Vs * d;
    },
    view: function (s, p) {
      var e = sn_strain.strain(p), vb = sn_strain.bridge(p);
      return { t: s.t || 0.0, eps_ue: e * 1e6, Vb_mV: vb * 1000.0, Vout_V: p.G * vb + p.Voff, dR: p.Rg * p.GF * e };
    },
    measure: function (p) { var e = sn_strain.strain(p), vb = sn_strain.bridge(p); return { strain: e, Vb: vb, Vout: p.G * vb + p.Voff }; }
  });
  function strain_vb(p) { return p.Vs * Math.round(p.nb) * p.GF * sn_strain.strain(p) / 4.0; }

  // ===================================================================================== capacitive level
  var sn_capl = stat({
    PARAMS: { h: 0.1, H: 0.3, a: 0.003, b: 0.010, er: 80.2, Cs: 12.0e-12, hu: 0.137 },
    VARS: ['t', 'h_cm', 'C_pF'],
    cap: function (p, h) { return 2.0 * PI * EPS0 * (p.H + (p.er - 1.0) * h) / Math.log(p.b / p.a) + p.Cs; },
    view: function (s, p) { return { t: s.t || 0.0, h_cm: p.h * 100.0, C_pF: sn_capl.cap(p, p.h) * 1e12 }; },
    measure: function (p) { var d = 0.01; return { C: sn_capl.cap(p, p.h), dCdh: (sn_capl.cap(p, p.h + d) - sn_capl.cap(p, p.h)) / d }; }
  });
  function capl_slope(p) { return 2.0 * PI * EPS0 * (p.er - 1.0) / Math.log(p.b / p.a); }

  // ===================================================================================== ultrasonic ranging
  var sn_ultra = stat({
    PARAMS: { d: 0.5, T: 20.0, t0: 1.8e-4, f: 40000.0, A: 1.0, dx: 0.737 },
    VARS: ['t', 'd_cm', 'te_ms', 'c'],
    speed: function (T) { return 331.3 * Math.sqrt(1.0 + T / 273.15); },
    signal: function (p, t) {
      var ta = 2.0 * p.d / sn_ultra.speed(p.T) + p.t0;
      if (t < ta || t >= ta + 8.0 / p.f) return 0.0;
      return p.A * Math.sin(2.0 * PI * p.f * (t - ta));
    },
    echo_time: function (p) {
      var thr = 0.2 * p.A, tmax = 2.0 * 5.0 / sn_ultra.speed(p.T) + p.t0 + 1.0e-3, k = 0, step = 5.0e-6, lo, j;
      while (k * step < tmax) { if (Math.abs(sn_ultra.signal(p, k * step)) > thr) break; k++; }
      lo = Math.max(0.0, (k - 1) * step);
      j = 0;
      while (j < 51) { if (Math.abs(sn_ultra.signal(p, lo + j * 1.0e-7)) > thr) return lo + j * 1.0e-7; j++; }
      return lo + 50 * 1.0e-7;
    },
    view: function (s, p) { return { t: s.t || 0.0, d_cm: p.d * 100.0, te_ms: sn_ultra.echo_time(p) * 1000.0, c: sn_ultra.speed(p.T) }; },
    measure: function (p) { var te = sn_ultra.echo_time(p); return { te: te, d_est: sn_ultra.speed(p.T) * (te - p.t0) / 2.0 }; }
  });
  function ultra_d(p) { return p.d; }

  // ===================================================================================== temperature sensors
  var sn_tsens = stat({
    PARAMS: { dev: 0.0, T: 25.0, ge: 0.0, off: 0.0, R0: 100.0, Tu: 47.3 },
    VARS: ['t', 'T', 'reading'],
    A: 3.9083e-3, B: -5.775e-7,
    raw: function (p, T) {
      var te = T + p.off, k = Math.round(p.dev);
      if (k === 0) return (te + 273.15) * (1.0 + p.ge);
      if (k === 1) return 10.0 * te * (1.0 + p.ge);
      if (k === 2) return te * (1.0 + p.ge);
      return p.R0 * (1.0 + sn_tsens.A * te + sn_tsens.B * te * te) * (1.0 + p.ge);
    },
    reading: function (p, T) {
      var v = sn_tsens.raw(p, T);
      if (Math.round(p.dev) === 2) return Math.floor(v / 0.125 + 0.5) * 0.125;
      return v;
    },
    view: function (s, p) { return { t: s.t || 0.0, T: p.T, reading: sn_tsens.reading(p, p.T) }; },
    measure: function (p) { return { reading: sn_tsens.reading(p, p.T), slope: sn_tsens.raw(p, p.T + 0.5) - sn_tsens.raw(p, p.T - 0.5) }; }
  });
  function tsens_slope(p) {
    var k = Math.round(p.dev), g = 1.0 + p.ge;
    if (k === 0) return g;
    if (k === 1) return 10.0 * g;
    if (k === 2) return g;
    return p.R0 * (sn_tsens.A + 2.0 * sn_tsens.B * (p.T + p.off)) * g;
  }

  // ===================================================================================== photodiode
  var sn_photo = stat({
    PARAMS: { d: 0.10, Ie: 0.13, lam: 940.0e-9, eta: 0.8, A: 7.5e-6, Id: 2.0e-9 },
    VARS: ['t', 'd_cm', 'E', 'P_uW', 'I_uA'],
    resp: function (p) { return p.eta * p.lam * QE / (HP * CL); },
    view: function (s, p) {
      var e = p.Ie / (p.d * p.d), pw = e * p.A;
      return { t: s.t || 0.0, d_cm: p.d * 100.0, E: e, P_uW: pw * 1e6, I_uA: (sn_photo.resp(p) * pw + p.Id) * 1e6 };
    },
    measure: function (p) {
      var cur = function (d) { return sn_photo.resp(p) * (p.Ie / (d * d)) * p.A + p.Id; };
      var pw = function (d) { return (p.Ie / (d * d)) * p.A; };
      var d1 = p.d, d2 = p.d * 1.5;
      return { I: cur(d1), R: (cur(d1) - cur(d2)) / (pw(d1) - pw(d2)) };
    }
  });
  function photo_r(p) { return p.eta * p.lam * QE / (HP * CL); }

  // ===================================================================================== meter loading
  var sn_mload = stat({
    PARAMS: { Vs: 5.0, R1: 1.0e6, R2: 1.0e6, Rm: 1.0e7 },
    VARS: ['t', 'Vm', 'Vt', 'err_pct'],
    volts: function (p) { var rp = p.R2 * p.Rm / (p.R2 + p.Rm); return [p.Vs * rp / (p.R1 + rp), p.Vs * p.R2 / (p.R1 + p.R2)]; },
    view: function (s, p) { var v = sn_mload.volts(p); return { t: s.t || 0.0, Vm: v[0], Vt: v[1], err_pct: 100.0 * (v[0] - v[1]) / v[1] }; },
    measure: function (p) { var v = sn_mload.volts(p); return { Vm: v[0], Vt: v[1], err: 100.0 * (v[0] - v[1]) / v[1] }; }
  });
  function mload_err(p) { var rth = p.R1 * p.R2 / (p.R1 + p.R2); return -100.0 * rth / (rth + p.Rm); }

  // ===================================================================================== meter bandwidth
  var sn_mbw = stat({
    PARAMS: { f: 1000.0, V: 1.0, fc: 20000.0 },
    VARS: ['t', 'f_kHz', 'reading', 'err_pct'],
    reading: function (p, f) { return p.V / Math.sqrt(1.0 + Math.pow(f / p.fc, 2)); },
    view: function (s, p) { var r = sn_mbw.reading(p, p.f); return { t: s.t || 0.0, f_kHz: p.f / 1000.0, reading: r, err_pct: 100.0 * (r - p.V) / p.V }; },
    measure: function (p) {
      var lo = 1.0, hi = 1.0e9, tgt = p.V / Math.sqrt(2.0), i, mid;
      for (i = 0; i < 80; i++) { mid = Math.sqrt(lo * hi); if (sn_mbw.reading(p, mid) > tgt) lo = mid; else hi = mid; }
      return { f3: Math.sqrt(lo * hi), reading: sn_mbw.reading(p, p.f) };
    }
  });
  function mbw_f3(p) { return p.fc; }

  // ===================================================================================== rotary pump
  var sn_vac = stat({
    PARAMS: { t: 0.0, P0: 1013.25, Pu: 0.05, Vch: 0.02, S: 0.00167 },
    VARS: ['t', 'P'],
    pressure: function (p, t) {
      var k = p.S / p.Vch, P = p.P0, h = 0.01, n = Math.floor(t / h + 0.5), i, k1, k2, k3, k4;
      var f = function (x) { return -k * (x - p.Pu); };
      for (i = 0; i < n; i++) { k1 = f(P); k2 = f(P + 0.5 * h * k1); k3 = f(P + 0.5 * h * k2); k4 = f(P + h * k3); P += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0; }
      return P;
    },
    view: function (s, p) { return { t: s.t || 0.0, P: sn_vac.pressure(p, p.t) }; },
    measure: function (p) { return { P: sn_vac.pressure(p, p.t) }; }
  });
  function vac_p(p) { return p.Pu + (p.P0 - p.Pu) * Math.exp(-p.S * p.t / p.Vch); }

  // ===================================================================================== scope measurement
  var sn_scope = stat({
    PARAMS: { f: 1000.0, A: 2.0, Vdc: 0.5, R: 10000.0, C: 1.0e-8, n: 4.0 },
    VARS: ['t', 'T_ms', 'Vpp1', 'Vpp2', 'phase'],
    trace: function (p) {
      var n = Math.round(p.n), span = n / p.f, dt = span / NW, x = 2.0 * PI * p.f * p.R * p.C, g = 1.0 / Math.sqrt(1.0 + x * x), ph = Math.atan(x), a = [], b = [], i, wt;
      for (i = 0; i < NW; i++) {
        wt = 2.0 * PI * p.f * i * dt;
        a.push(p.Vdc + p.A * Math.sin(wt));
        b.push(p.Vdc + p.A * g * Math.sin(wt - ph));
      }
      return [dt, a, b];
    },
    analyse: function (p) {
      var tr = sn_scope.trace(p), dt = tr[0], a = tr[1], b = tr[2], ma = sum(a) / a.length, mb = sum(b) / b.length;
      var ca = cross(a, dt, ma, true), cb = cross(b, dt, mb, true), T = (ca[ca.length - 1] - ca[0]) / (ca.length - 1), lag = 0.0, i;
      for (i = 0; i < cb.length; i++) if (cb[i] >= ca[0] - 1e-12) { lag = cb[i] - ca[0]; break; }
      if (lag >= T) lag -= T;
      return { T: T, f: 1.0 / T, Vpp1: maxOf(a) - minOf(a), Vdc1: ma, Vpp2: maxOf(b) - minOf(b), phase: lag / T * 360.0 };
    },
    view: function (s, p) { var m = sn_scope.analyse(p); return { t: s.t || 0.0, T_ms: m.T * 1000.0, Vpp1: m.Vpp1, Vpp2: m.Vpp2, phase: m.phase }; },
    measure: function (p) { return sn_scope.analyse(p); }
  });
  function scope_phase(p) { return Math.atan(2.0 * PI * p.f * p.R * p.C) * 180 / PI; }

  // ===================================================================================== pulse timing
  function rampStage(y, u0, r, dt, tau) {
    var e = Math.exp(-dt / tau);
    return u0 + r * dt - r * tau + (y - u0 + r * tau) * e;
  }
  function rampCascade(y1, y2, u0, r, dt, t1, t2) {
    if (Math.abs(t1 - t2) < 1e-6 * t1) t2 = t1 * (1.0 + 1e-6);
    var alpha = u0 - r * t1, beta = y1 - alpha, e1 = Math.exp(-dt / t1), n1 = alpha + r * dt + beta * e1;
    var k = 1.0 / (1.0 - t2 / t1), gamma = y2 - (alpha - r * t2 + beta * k);
    var n2 = alpha + r * (dt - t2) + beta * k * e1 + gamma * Math.exp(-dt / t2);
    return [n1, n2];
  }
  var sn_pulse = stat({
    PARAMS: { R: 10000.0, C: 1.0e-9, tg: 5.0e-9, BW: 1.0e8, Vh: 5.0 },
    VARS: ['t', 'tr_us', 'tf_us', 'td_us'],
    trace: function (p) {
      var tau = p.R * p.C, ts = 1.0 / (2.0 * PI * p.BW), tt = tau + ts + p.tg, tOn = 2.0 * tt, width = 14.0 * tt, span = 30.0 * tt, dt0 = span / NW;
      var tg = p.tg, vh = p.Vh, corners = [tOn, tOn + tg, tOn + width, tOn + width + tg].sort(function (a, b) { return a - b; });
      var uAt = function (t) {
        if (t <= corners[0]) return 0.0;
        if (t < corners[1]) return vh * (t - corners[0]) / tg;
        if (t <= corners[2]) return vh;
        if (t < corners[3]) return vh * (1.0 - (t - corners[2]) / tg);
        return 0.0;
      };
      var ya = 0.0, yb = 0.0, yc = 0.0, a = [], b = [], t = 0.0, ci = 0, i, tend, nxt, h, r, u0, cc;
      for (i = 0; i < NW; i++) {
        tend = (i + 1) * dt0;
        while (t < tend - 1e-30) {
          nxt = tend;
          while (ci < corners.length && corners[ci] <= t + 1e-30) ci++;
          if (ci < corners.length && corners[ci] < nxt) nxt = corners[ci];
          h = nxt - t;
          if (h <= 0) break;
          r = (uAt(t + 0.75 * h) - uAt(t + 0.25 * h)) / (0.5 * h);
          u0 = uAt(t + 0.5 * h) - r * 0.5 * h;
          ya = rampStage(ya, u0, r, h, ts);
          cc = rampCascade(yb, yc, u0, r, h, tau, ts); yb = cc[0]; yc = cc[1];
          t = nxt;
        }
        a.push(ya); b.push(yc);
      }
      return [dt0, a, b];
    },
    analyse: function (p) {
      var tr = sn_pulse.trace(p), dt = tr[0], a = tr[1], b = tr[2], top = maxOf(b);
      var r10 = cross(b, dt, 0.1 * top, true), r90 = cross(b, dt, 0.9 * top, true), f90 = cross(b, dt, 0.9 * top, false), f10 = cross(b, dt, 0.1 * top, false);
      var r50a = cross(a, dt, 0.5 * maxOf(a), true), r50b = cross(b, dt, 0.5 * top, true);
      return { tr: r90[0] - r10[0], tf: f10[0] - f90[0], td: r50b[0] - r50a[0], top: top };
    },
    view: function (s, p) { var m = sn_pulse.analyse(p); return { t: s.t || 0.0, tr_us: m.tr * 1e6, tf_us: m.tf * 1e6, td_us: m.td * 1e6 }; },
    measure: function (p) { return sn_pulse.analyse(p); }
  });
  function pulse_tr(p) { return Math.log(9.0) * p.R * p.C; }

  // ===================================================================================== clipper / clamper
  var sn_shape = stat({
    PARAMS: { mode: 2.0, Vp: 5.0, f: 1000.0, R: 10000.0, C: 1.0e-6, RL: 10000000.0, Vb: 0.0, Vf: 0.65, rd: 5.0 },
    VARS: ['t', 'Vmax', 'Vmin', 'Vpp'],
    SPC: 200,
    trace: function (p) {
      var mode = Math.round(p.mode), spc = 200, dt = 1.0 / (p.f * spc), cyc = mode >= 2 ? 40 : 4, vin = [], vout = [], vo = 0.0, viPrev = 0.0, cdt = p.C / dt, k, vi, lim, src, g, v;
      for (k = 0; k < cyc * spc + 1; k++) {
        vi = p.Vp * Math.sin(2.0 * PI * p.f * k * dt);
        if (mode === 0) {
          lim = p.Vb + p.Vf;
          vo = vi <= lim ? vi : lim + (vi - lim) * p.rd / (p.R + p.rd);
        } else if (mode === 1) {
          lim = p.Vb - p.Vf;
          vo = vi >= lim ? vi : lim + (vi - lim) * p.rd / (p.R + p.rd);
        } else if (k > 0) {
          src = cdt * (vi - viPrev + vo);
          g = cdt + 1.0 / p.RL;
          v = src / g;
          if (mode === 2) { if (v < p.Vb - p.Vf) v = (src + (p.Vb - p.Vf) / p.rd) / (g + 1.0 / p.rd); }
          else { if (v > p.Vb + p.Vf) v = (src + (p.Vb + p.Vf) / p.rd) / (g + 1.0 / p.rd); }
          vo = v;
        }
        viPrev = vi;
        if (k > (cyc - 2) * spc) { vin.push(vi); vout.push(vo); }
      }
      return [dt, vin, vout];
    },
    levels: function (p) {
      var tr = sn_shape.trace(p), vout = tr[2], mode = Math.round(p.mode), hi = maxOf(vout), lo = minOf(vout);
      return { Vmax: hi, Vmin: lo, Vpp: hi - lo, Vdc: sum(vout) / vout.length, Vlvl: (mode === 0 || mode === 3) ? hi : lo };
    },
    view: function (s, p) { var m = sn_shape.levels(p); return { t: s.t || 0.0, Vmax: m.Vmax, Vmin: m.Vmin, Vpp: m.Vpp }; },
    measure: function (p) { return sn_shape.levels(p); }
  });
  function shape_lvl(p) { var mode = Math.round(p.mode); return (mode === 0 || mode === 3) ? p.Vb + p.Vf : p.Vb - p.Vf; }

  // ===================================================================================== 555 / UJT
  var sn_mv = stat({
    PARAMS: { kind: 0.0, R1: 1000.0, R2: 10000.0, C: 1.0e-7, Vcc: 9.0, eta: 0.65, Vd: 0.5, Vv: 1.0 },
    VARS: ['t', 'f', 'width', 'duty'],
    span: function (p) {
      var k = Math.round(p.kind);
      if (k === 0) return 4.4 * (p.R1 + 2.0 * p.R2) * p.C;
      if (k === 1) return 8.0 * p.R1 * p.C;
      return 5.5 * p.R1 * p.C;
    },
    trace: function (p) {
      var k = Math.round(p.kind), span = sn_mv.span(p), dt0 = span / NW, vcc = p.Vcc, vc = 0.0, hi = (k === 0), vcs = [], vos = [], vts = [];
      var tc = p.R1 * p.C, trig = [0.5 * tc, 4.5 * tc, 8.5 * tc], tw = 0.05 * tc, ti = 0, t = 0.0, i, tend, highT, rem, tau, thr, tgt, tcx, nxt, tt, low, q;
      for (i = 0; i < NW; i++) {
        tend = (i + 1) * dt0; highT = 0.0;
        while (t < tend) {
          rem = tend - t;
          if (k === 0) {
            if (hi) { tau = (p.R1 + p.R2) * p.C; thr = 2.0 * vcc / 3.0; tgt = vcc; tcx = vc < thr ? tau * Math.log((tgt - vc) / (tgt - thr)) : 0.0; }
            else { tau = p.R2 * p.C; thr = vcc / 3.0; tgt = 0.0; tcx = vc > thr ? tau * Math.log(vc / thr) : 0.0; }
            if (tcx <= rem) { vc = thr; if (hi) highT += tcx; t += tcx; hi = !hi; }
            else { vc = tgt + (vc - tgt) * Math.exp(-rem / tau); if (hi) highT += rem; t = tend; }
          } else if (k === 1) {
            nxt = ti < trig.length ? trig[ti] : 1e30;
            if (hi && nxt <= t) { ti++; nxt = ti < trig.length ? trig[ti] : 1e30; }
            if (hi) {
              tau = p.R1 * p.C; thr = 2.0 * vcc / 3.0; tcx = tau * Math.log((vcc - vc) / (vcc - thr));
              if (tcx <= rem) { highT += tcx; t += tcx; hi = false; vc = 0.0; }
              else { vc = vcc + (vc - vcc) * Math.exp(-rem / tau); highT += rem; t = tend; }
            } else if (nxt <= tend) { t = Math.max(t, nxt); hi = true; ti++; }
            else t = tend;
          } else {
            tau = p.R1 * p.C; tgt = vcc; thr = p.eta * vcc + p.Vd;
            tcx = vc < thr ? tau * Math.log((tgt - vc) / (tgt - thr)) : 0.0;
            if (tcx <= rem) { t += tcx; vc = p.Vv; }
            else { vc = tgt + (vc - tgt) * Math.exp(-rem / tau); t = tend; }
          }
        }
        vcs.push(vc);
        vos.push(k < 2 ? vcc * highT / dt0 : 0.0);
        tt = (i + 0.5) * dt0; low = 0.0;
        for (q = 0; q < trig.length; q++) if (trig[q] <= tt && tt < trig[q] + tw) low = 1.0;
        vts.push(vcc * (1.0 - low));
      }
      return [dt0, vcs, vos, vts];
    },
    analyse: function (p) {
      var k = Math.round(p.kind), tr = sn_mv.trace(p), dt = tr[0], vc = tr[1], vo = tr[2];
      var out = { f: 0.0, T: 0.0, width: 0.0, duty: 0.0, Thigh: 0.0, Tlow: 0.0, main: 0.0 }, lvl, r, fl, T, lows, i, prev, j, tl, w, use;
      if (k === 0) {
        lvl = 0.5 * p.Vcc; r = cross(vo, dt, lvl, true); fl = cross(vo, dt, lvl, false);
        T = (r[r.length - 1] - r[0]) / (r.length - 1); lows = [];
        for (i = 0; i < r.length; i++) {
          prev = []; for (j = 0; j < fl.length; j++) if (fl[j] < r[i]) prev.push(fl[j]);
          if (prev.length) lows.push(r[i] - prev[prev.length - 1]);
        }
        tl = sum(lows) / lows.length;
        out.T = T; out.f = 1.0 / T; out.Tlow = tl; out.Thigh = T - tl; out.duty = (T - tl) / T; out.main = 1.0 / T;
      } else if (k === 1) {
        lvl = 0.5 * p.Vcc; r = cross(vo, dt, lvl, true); fl = cross(vo, dt, lvl, false);
        w = fl[0] - r[0]; out.width = w; out.main = w;
      } else {
        lvl = 0.5 * (maxOf(vc) + minOf(vc)); r = cross(vc, dt, lvl, true);
        use = r.length >= 3 ? r.slice(1) : r;
        T = (use[use.length - 1] - use[0]) / (use.length - 1);
        out.T = T; out.f = 1.0 / T; out.main = 1.0 / T;
      }
      return out;
    },
    view: function (s, p) { var m = sn_mv.analyse(p); return { t: s.t || 0.0, f: m.f, width: m.width, duty: m.duty }; },
    measure: function (p) { return sn_mv.analyse(p); }
  });
  function mv_main(p) {
    var k = Math.round(p.kind), thr;
    if (k === 0) return 1.44 / ((p.R1 + 2.0 * p.R2) * p.C);
    if (k === 1) return 1.1 * p.R1 * p.C;
    thr = p.eta * p.Vcc + p.Vd;
    return 1.0 / (p.R1 * p.C * Math.log((p.Vcc - p.Vv) / (p.Vcc - thr)));
  }

  // ===================================================================================== CE amplifier
  function cMul(a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; }
  function cDiv(a, b) { var d = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; }
  function cAdd(a, b) { return [a[0] + b[0], a[1] + b[1]]; }
  function cPar(a, b) { return cDiv(cMul(a, b), cAdd(a, b)); }
  var sn_ce = stat({
    PARAMS: { Vcc: 12.0, R1: 47000.0, R2: 10000.0, Rc: 2200.0, Re: 680.0, RL: 10000.0, Rs: 50.0, Cin: 1.0e-6, CE: 220.0e-6, Cout: 1.0e-6,
      beta: 200.0, Vbe: 0.65, fT: 3.0e8, Cmu: 4.5e-12, stages: 1.0, f: 10000.0, fmid: 10000.0 },
    VARS: ['t', 'Ic_mA', 'Vce', 'gm_mS'],
    bias: function (p) {
      var vth = p.Vcc * p.R2 / (p.R1 + p.R2), rth = p.R1 * p.R2 / (p.R1 + p.R2), b = p.beta;
      var ic = (vth - p.Vbe) / (rth / b + p.Re * (b + 1.0) / b);
      return [ic, p.Vcc - ic * p.Rc - ic * (b + 1.0) / b * p.Re];
    },
    stage: function (p, w, rs, last, rlHf) {
      var ic = sn_ce.bias(p)[0], gm = ic / VT, rpi = p.beta / gm, cpi = gm / (2.0 * PI * p.fT) - p.Cmu, rb = p.R1 * p.R2 / (p.R1 + p.R2);
      var ze = cDiv([p.Re, 0.0], [1.0, w * p.Re * p.CE]);
      var zb = cAdd([rpi, 0.0], cMul([p.beta + 1.0, 0.0], ze));
      var zin = cPar([rb, 0.0], zb);
      var zcin = cDiv([1.0, 0.0], [0.0, w * p.Cin]);
      var vbvs = cDiv(zin, cAdd(cAdd([rs, 0.0], zcin), zin));
      var ibvs = cDiv(vbvs, zb), icvs = cMul([p.beta, 0.0], ibvs);
      var rlp = p.Rc * rlHf / (p.Rc + rlHf), cm = cpi + p.Cmu * (1.0 + gm * rlp), rthin = 1.0 / (1.0 / rs + 1.0 / rb + 1.0 / rpi);
      var hf = cDiv([1.0, 0.0], [1.0, w * rthin * cm]), zo, zco, zl, h;
      if (last) {
        zco = cDiv([1.0, 0.0], [0.0, w * p.Cout]); zl = cAdd([p.RL, 0.0], zco);
        zo = cMul(cPar([p.Rc, 0.0], zl), cDiv([p.RL, 0.0], zl));
      } else zo = [p.Rc, 0.0];
      h = cMul(cMul(icvs, hf), zo);
      return [-h[0], -h[1]];
    },
    resp: function (p, f) {
      var w = 2.0 * PI * f, ic = sn_ce.bias(p)[0], gm = ic / VT, rpi = p.beta / gm, rb = p.R1 * p.R2 / (p.R1 + p.R2), rin = rb * rpi / (rb + rpi);
      if (Math.round(p.stages) === 1) return sn_ce.stage(p, w, p.Rs, true, p.RL);
      return cMul(sn_ce.stage(p, w, p.Rs, false, rin), sn_ce.stage(p, w, p.Rc, true, p.RL));
    },
    gain: function (p, f) { var h = sn_ce.resp(p, f); return Math.sqrt(h[0] * h[0] + h[1] * h[1]); },
    phase: function (p, f) { var h = sn_ce.resp(p, f); return Math.atan2(h[1], h[0]) * 180 / PI; },
    scan: function (p) {
      var am = sn_ce.gain(p, p.fmid), tgt = am / Math.sqrt(2.0), n = 1000, fl = 0.0, fh = 0.0, prevF = 1.0, prevG = sn_ce.gain(p, 1.0), i, f, g;
      for (i = 1; i <= n; i++) {
        f = Math.pow(10.0, 10.0 * i / n); g = sn_ce.gain(p, f);
        if (fl === 0.0 && prevG < tgt && tgt <= g) fl = Math.pow(10.0, Math.log10(prevF) + (Math.log10(f) - Math.log10(prevF)) * (tgt - prevG) / (g - prevG));
        if (fl !== 0.0 && fh === 0.0 && prevG >= tgt && tgt > g) fh = Math.pow(10.0, Math.log10(prevF) + (Math.log10(f) - Math.log10(prevF)) * (prevG - tgt) / (prevG - g));
        prevF = f; prevG = g;
      }
      return { Amid: am, fL: fl, fH: fh };
    },
    view: function (s, p) { var b = sn_ce.bias(p); return { t: s.t || 0.0, Ic_mA: b[0] * 1000.0, Vce: b[1], gm_mS: b[0] / VT * 1000.0 }; },
    measure: function (p) { var m = sn_ce.scan(p); m.A = sn_ce.gain(p, p.f); m.phase = sn_ce.phase(p, p.f); return m; }
  });
  function ce_amid(p) {
    var ic = sn_ce.bias(p)[0], gm = ic / VT, rpi = p.beta / gm, rb = p.R1 * p.R2 / (p.R1 + p.R2), rin = rb * rpi / (rb + rpi);
    var a1 = gm * (p.Rc * p.RL / (p.Rc + p.RL)) * rin / (p.Rs + rin);
    if (Math.round(p.stages) === 1) return a1;
    return gm * p.Rc * rin / (p.Rs + rin) * (gm * (p.Rc * p.RL / (p.Rc + p.RL)) * rin / (p.Rc + rin));
  }

  // ===================================================================================== AM
  var sn_am = stat({
    PARAMS: { Vc: 2.0, Vm: 0.5, fc: 20000.0, fm: 500.0, ka: 0.4 },
    VARS: ['t', 'm', 'Vmax', 'Vmin'],
    NS: 6000,
    trace: function (p) {
      var n = 6000, span = 2.0 / p.fm, dt = span / n, m = p.ka * p.Vm, msg = [], am = [], i, t;
      for (i = 0; i < n; i++) {
        t = i * dt;
        msg.push(p.Vm * Math.sin(2.0 * PI * p.fm * t));
        am.push(p.Vc * (1.0 + m * Math.sin(2.0 * PI * p.fm * t)) * Math.sin(2.0 * PI * p.fc * t + 0.3));
      }
      return [dt, msg, am];
    },
    analyse: function (p) {
      var tr = sn_am.trace(p), am = tr[2], per = Math.round(6000 / (2.0 * p.fc / p.fm)), env = [], b, vmax, vmin;
      for (b = 0; b + per <= am.length; b += per) env.push(maxOf(am.slice(b, b + per)));
      vmax = maxOf(env); vmin = minOf(env);
      return { Vmax: vmax, Vmin: vmin, m: (vmax - vmin) / (vmax + vmin), Vc_est: 0.5 * (vmax + vmin) };
    },
    view: function (s, p) { var a = sn_am.analyse(p); return { t: s.t || 0.0, m: a.m, Vmax: a.Vmax, Vmin: a.Vmin }; },
    measure: function (p) { return sn_am.analyse(p); }
  });
  function am_m(p) { return p.ka * p.Vm; }

  // ===================================================================================== FM
  var sn_fm = stat({
    PARAMS: { Vc: 2.0, Vm: 1.0, fc: 20000.0, fm: 250.0, kf: 1500.0, kd: 1000.0 },
    VARS: ['t', 'df_kHz', 'beta', 'Vrec'],
    NS: 12000,
    trace: function (p) {
      var n = 12000, dt = 2.0 / p.fm / n, beta = p.kf * p.Vm / p.fm, msg = [], fm = [], i, t;
      for (i = 0; i < n; i++) {
        t = i * dt;
        msg.push(p.Vm * Math.sin(2.0 * PI * p.fm * t));
        fm.push(p.Vc * Math.sin(2.0 * PI * p.fc * t + beta * Math.sin(2.0 * PI * p.fm * t)));
      }
      return [dt, msg, fm];
    },
    analyse: function (p) {
      var tr = sn_fm.trace(p), cr = cross(tr[2], tr[0], 0.0, true), fs = [], i, hi, lo, df;
      for (i = 0; i < cr.length - 1; i++) fs.push(1.0 / (cr[i + 1] - cr[i]));
      hi = maxOf(fs); lo = minOf(fs); df = 0.5 * (hi - lo);
      return { df: df, fc_est: 0.5 * (hi + lo), beta: df / p.fm, Vrec: df / p.kd, bw: 2.0 * (df + p.fm) };
    },
    view: function (s, p) { var a = sn_fm.analyse(p); return { t: s.t || 0.0, df_kHz: a.df / 1000.0, beta: a.beta, Vrec: a.Vrec }; },
    measure: function (p) { return sn_fm.analyse(p); }
  });
  function fm_df(p) { return p.kf * p.Vm; }

  H.register({
    K: { sn_lvdt: sn_lvdt, sn_strain: sn_strain, sn_capl: sn_capl, sn_ultra: sn_ultra, sn_tsens: sn_tsens, sn_photo: sn_photo,
      sn_mload: sn_mload, sn_mbw: sn_mbw, sn_vac: sn_vac, sn_scope: sn_scope, sn_pulse: sn_pulse, sn_shape: sn_shape,
      sn_mv: sn_mv, sn_ce: sn_ce, sn_am: sn_am, sn_fm: sn_fm },
    TEXTBOOK: { sn_lvdt_v: lvdt_v, sn_strain_vb: strain_vb, sn_capl_slope: capl_slope, sn_ultra_d: ultra_d, sn_tsens_slope: tsens_slope,
      sn_photo_r: photo_r, sn_mload_err: mload_err, sn_mbw_f3: mbw_f3, sn_vac_p: vac_p, sn_scope_phase: scope_phase,
      sn_pulse_tr: pulse_tr, sn_shape_lvl: shape_lvl, sn_mv_main: mv_main, sn_ce_amid: ce_amid, sn_am_m: am_m, sn_fm_df: fm_df },
    CALCS: {}
  });
})(typeof window !== 'undefined' ? window : this);
