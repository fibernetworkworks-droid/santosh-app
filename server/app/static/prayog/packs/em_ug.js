/* Kernel pack `em_ug`: the exact JavaScript twin of app/prayog/packs/em_ug.py. Same formulas, same algorithms,
   same iteration counts, same numbers (the server's tests run both and compare). The undergraduate electricity,
   magnetism, AC-circuit, network and instrumentation physics: the DC network theorems need no kernel at all (the
   shared `circuit` kernel solves the trainer panel), so they are textbook formulas plus one table calculation;
   the alternating-current work is phasor algebra in complex numbers, because the circuit solver has no inductor
   and no sinusoidal source. Deterministic: no randomness, no wall clock. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI;

  // ------------------------------------------------------------------ DC network trainer panel (circuit kernel)
  function net_rp(p) { return 1.0 / (1.0 / p.R1 + 1.0 / p.R2 + 1.0 / p.R3); }
  function net_rth(p) { return p.R4 + net_rp(p); }
  function net_voc(p) { return (p.E1 / p.R1 + p.E2 / p.R2) * net_rp(p); }
  function net_il(p) { return net_voc(p) / (net_rth(p) + p.RL); }
  function net_isc(p) { return net_voc(p) / net_rth(p); }
  function net_vl(p) { return net_voc(p) * p.RL / (net_rth(p) + p.RL); }
  function net_i3(p) {
    var g = 1.0 / p.R1 + 1.0 / p.R2 + 1.0 / p.R3 + 1.0 / (p.R4 + p.RL);
    return (p.E1 / p.R1 + p.E2 / p.R2) / g / p.R3;
  }
  function calc_net_rth(rows, p) {
    var voc = 0, nv = 0, isc = 0, ni = 0, i, r, k, v, c;
    for (i = 0; i < (rows || []).length; i++) {
      r = rows[i]; k = Number(r.kind); v = Number(r.V); c = Number(r.I);
      if (!isFinite(k) || !isFinite(v) || !isFinite(c)) continue;
      if (k < 0.5) { voc += v; nv += 1; } else { isc += c; ni += 1; }
    }
    if (!nv || !ni || isc === 0) return 0.0;
    return (voc / nv) / (isc / ni);
  }

  // ------------------------------------------------------------------ series / parallel LCR (AC)
  var lcr = {
    PARAMS: { R: 50.0, L: 0.01, C: 1e-7, f: 5000.0, V: 1.0, mode: 0.0 },
    VARS: ['t', 'Z', 'I', 'V_R', 'V_L', 'V_C', 'phase', 'gain'],
    zser: function (p, f) { var w = 2 * PI * f; return [p.R, w * p.L - 1.0 / (w * p.C)]; },
    zpar: function (p, f) {
      var w = 2 * PI * f, a = p.R, b = w * p.L, d = a * a + b * b;
      var ya = a / d, yb = -b / d + w * p.C, dy = ya * ya + yb * yb;
      return [ya / dy, -yb / dy];
    },
    z: function (p, f) { return p.mode >= 0.5 ? lcr.zpar(p, f) : lcr.zser(p, f); },
    current: function (p, f) { var z = lcr.z(p, f); return p.V / Math.sqrt(z[0] * z[0] + z[1] * z[1]); },
    peak: function (p) {
      var f0 = 1.0 / (2 * PI * Math.sqrt(p.L * p.C)), lo = f0 / 4.0, hi = f0 * 4.0;
      var wantMax = p.mode < 0.5, g = 0.6180339887498949, i, better;
      var c = hi - g * (hi - lo), d = lo + g * (hi - lo), fc = lcr.current(p, c), fd = lcr.current(p, d);
      for (i = 0; i < 120; i++) {
        better = wantMax ? (fc > fd) : (fc < fd);
        if (better) { hi = d; d = c; fd = fc; c = hi - g * (hi - lo); fc = lcr.current(p, c); }
        else { lo = c; c = d; fc = fd; d = lo + g * (hi - lo); fd = lcr.current(p, d); }
      }
      return (lo + hi) / 2;
    },
    half: function (p, fr, ipk, lo, hi) {
      var want = ipk / Math.sqrt(2.0), i, mid, above;
      for (i = 0; i < 120; i++) {
        mid = (lo + hi) / 2;
        above = lcr.current(p, mid) > want;
        if ((mid < fr) === above) hi = mid; else lo = mid;
      }
      return (lo + hi) / 2;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var z = lcr.z(p, p.f), zmag = Math.sqrt(z[0] * z[0] + z[1] * z[1]), i = p.V / zmag, w = 2 * PI * p.f;
      return { t: s.t || 0, Z: zmag, I: i, V_R: i * p.R, V_L: i * w * p.L, V_C: i / (w * p.C),
        phase: Math.atan2(z[1], z[0]), gain: p.R / zmag };
    },
    measure: function (p) {
      var fr = lcr.peak(p), ipk = lcr.current(p, fr), f1, f2, bw;
      if (p.mode < 0.5) {
        f1 = lcr.half(p, fr, ipk, fr / 8.0, fr);
        f2 = lcr.half(p, fr, ipk, fr, fr * 8.0);
        bw = f2 - f1;
        return { fr: fr, f1: f1, f2: f2, bw: bw, Q: bw > 0 ? fr / bw : 0.0, Ipk: ipk, Zr: p.V / ipk };
      }
      return { fr: fr, Ipk: ipk, Zr: p.V / ipk, Q: p.R > 0 ? 2 * PI * fr * p.L / p.R : 0.0 };
    }
  };
  function lcr_fr(p) { return 1.0 / (2 * PI * Math.sqrt(p.L * p.C)); }
  function lcr_far(p) {
    var w02 = 1.0 / (p.L * p.C), k = p.R * p.R / (p.L * p.L);
    return Math.sqrt(Math.sqrt(w02 * w02 + 2 * w02 * k) - k) / (2 * PI);
  }
  function lcr_bw(p) { return p.R / (2 * PI * p.L); }

  // ------------------------------------------------------------------ RC filter (AC)
  var rcfilter = {
    PARAMS: { R: 1000.0, C: 1e-7, f: 1000.0, V: 1.0, mode: 0.0 },
    VARS: ['t', 'Z', 'I', 'gain', 'dB', 'phase', 'V_R', 'V_C'],
    gainAt: function (p, f) {
      var x = 1.0 / (2 * PI * f * p.C), z = Math.sqrt(p.R * p.R + x * x);
      return (p.mode < 0.5 ? x : p.R) / z;
    },
    cut: function (p) {
      var f0 = 1.0 / (2 * PI * p.R * p.C), lo = f0 / 20.0, hi = f0 * 20.0;
      var want = 1.0 / Math.sqrt(2.0), rising = p.mode >= 0.5, i, mid;
      for (i = 0; i < 140; i++) {
        mid = (lo + hi) / 2;
        if ((rcfilter.gainAt(p, mid) > want) === rising) hi = mid; else lo = mid;
      }
      return (lo + hi) / 2;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var x = 1.0 / (2 * PI * p.f * p.C), z = Math.sqrt(p.R * p.R + x * x), i = p.V / z, g = rcfilter.gainAt(p, p.f);
      return { t: s.t || 0, Z: z, I: i, gain: g, dB: 20 * Math.log10(g),
        phase: p.mode < 0.5 ? Math.atan2(x, p.R) : Math.atan2(p.R, x), V_R: i * p.R, V_C: i * x };
    },
    measure: function (p) {
      return { fc: rcfilter.cut(p), gain: rcfilter.gainAt(p, p.f), Zc: 1.0 / (2 * PI * p.f * p.C) };
    }
  };
  function rc_fc(p) { return 1.0 / (2 * PI * p.R * p.C); }

  // ------------------------------------------------------------------ four-arm alternating-current bridge
  var acbridge = {
    PARAMS: { f: 1000.0, V: 5.0, Rg: 1000.0,
      R1: 1000.0, L1: 0.0, C1: 0.0, R2: 1000.0, L2: 0.0, C2: 0.0,
      R3: 0.0, L3: 0.0, C3: 1e-7, R4: 0.0, L4: 0.0, C4: 1e-7, bal: 1000.0 },
    VARS: ['t', 'I_G', 'V_G', 'Z1', 'Z2', 'Z3', 'Z4'],
    arm: function (p, n) {
      var w = 2 * PI * p.f, r = p['R' + n], l = p['L' + n], c = p['C' + n], x = w * l;
      if (c > 0) x -= 1.0 / (w * c);
      return [r, x];
    },
    div: function (a, b) {
      var d = b[0] * b[0] + b[1] * b[1];
      return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d];
    },
    mul: function (a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; },
    ig: function (p) {
      var z1 = acbridge.arm(p, 1), z2 = acbridge.arm(p, 2), z3 = acbridge.arm(p, 3), z4 = acbridge.arm(p, 4);
      var s13 = [z1[0] + z3[0], z1[1] + z3[1]], s24 = [z2[0] + z4[0], z2[1] + z4[1]];
      var d13 = acbridge.div(z3, s13), d24 = acbridge.div(z4, s24);
      var vth = [p.V * (d13[0] - d24[0]), p.V * (d13[1] - d24[1])];
      var p13 = acbridge.div(acbridge.mul(z1, z3), s13), p24 = acbridge.div(acbridge.mul(z2, z4), s24);
      var zth = [p13[0] + p24[0] + p.Rg, p13[1] + p24[1]];
      return acbridge.div(vth, zth);
    },
    detector: function (p, which, value) {
      var q = {}, k;
      for (k in p) q[k] = p[k];
      q[which] = value;
      var g = acbridge.ig(q);
      return Math.sqrt(g[0] * g[0] + g[1] * g[1]);
    },
    turn: function (p, which, lo, hi) {
      var g = 0.6180339887498949, i;
      var c = hi - g * (hi - lo), d = lo + g * (hi - lo);
      var fc = acbridge.detector(p, which, c), fd = acbridge.detector(p, which, d);
      for (i = 0; i < 100; i++) {
        if (fc < fd) { hi = d; d = c; fd = fc; c = hi - g * (hi - lo); fc = acbridge.detector(p, which, c); }
        else { lo = c; c = d; fc = fd; d = lo + g * (hi - lo); fd = acbridge.detector(p, which, d); }
      }
      return (lo + hi) / 2;
    },
    balance: function (p, cfg) {
      var m = (cfg || {}).measure || {}, one = m.param || 'bal';
      var lo = Number(m.lo === undefined ? 1.0 : m.lo), hi = Number(m.hi === undefined ? 1e5 : m.hi);
      var two = m.param2, q = {}, k, i, lo2, hi2, out, g;
      for (k in p) q[k] = p[k];
      if (!two) {
        q[one] = acbridge.turn(q, one, lo, hi);
      } else {
        lo2 = Number(m.lo2 === undefined ? 1.0 : m.lo2); hi2 = Number(m.hi2 === undefined ? 1e5 : m.hi2);
        for (i = 0; i < 14; i++) {
          q[one] = acbridge.turn(q, one, lo, hi);
          q[two] = acbridge.turn(q, two, lo2, hi2);
        }
      }
      g = acbridge.ig(q);
      out = { bal: q[one], I_G: Math.sqrt(g[0] * g[0] + g[1] * g[1]) };
      out[one] = q[one];
      if (two) { out[two] = q[two]; out.bal2 = q[two]; }
      return out;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var g = acbridge.ig(p), mag = Math.sqrt(g[0] * g[0] + g[1] * g[1]), out = { t: s.t || 0, I_G: mag, V_G: mag * p.Rg }, n, a;
      for (n = 1; n <= 4; n++) { a = acbridge.arm(p, n); out['Z' + n] = Math.sqrt(a[0] * a[0] + a[1] * a[1]); }
      return out;
    },
    measure: function (p, cfg) { return acbridge.balance(p, cfg); }
  };
  function desauty_c(p) { return p.C4 * p.R2 / p.R1; }
  function desauty_r2(p) { return p.R1 * p.C3 / p.C4; }
  function owen_l(p) { return p.R2 * p.R3 * p.C4; }
  function owen_r2(p) { return p.L1 / (p.R3 * p.C4); }
  function owen_c2(p) { return p.R3 * p.C4 / p.R1; }
  function uni_r2(p) { return p.R1 * p.R4 / p.R3; }

  H.register({
    K: { lcr: lcr, rcfilter: rcfilter, acbridge: acbridge },
    TEXTBOOK: { net_rth: net_rth, net_voc: net_voc, net_isc: net_isc, net_il: net_il, net_vl: net_vl,
      net_i3: net_i3, lcr_fr: lcr_fr, lcr_far: lcr_far, lcr_bw: lcr_bw, rc_fc: rc_fc,
      desauty_c: desauty_c, desauty_r2: desauty_r2, owen_l: owen_l, owen_r2: owen_r2, owen_c2: owen_c2,
      uni_r2: uni_r2 },
    CALCS: { net_rth: { label: 'Rth', unit: 'Ω', needs: ['V', 'I', 'kind'], fn: calc_net_rth } }
  });
})(typeof window !== 'undefined' ? window : this);
