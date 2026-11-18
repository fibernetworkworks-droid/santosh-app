/* Kernel pack `pg_elec_w9`: the exact JavaScript twin of app/prayog/packs/pg_elec_w9.py. Same formulas, same
   algorithms, same fixed sample and bisection counts, same numbers (the server's tests run both and compare). M.Sc.
   electronics set-ups (wave 9). Every kernel is prefixed `pe9_`; the rig `pe9-elec-bench` also calls the helper
   functions (out, dac, h, cur, gain, trace ...) of each kernel. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, VT = 0.025852;

  function bis(f, lo, hi, n) {
    var flo = f(lo), i, mid, fm;
    for (i = 0; i < n; i++) {
      mid = 0.5 * (lo + hi); fm = f(mid);
      if ((fm > 0.0) === (flo > 0.0)) { lo = mid; flo = fm; } else hi = mid;
    }
    return 0.5 * (lo + hi);
  }
  function gold(f, lo, hi, n) {
    var g = (Math.sqrt(5.0) - 1.0) / 2.0, a = lo, b = hi, c = b - g * (b - a), d = a + g * (b - a), fc = f(c), fd = f(d), i;
    for (i = 0; i < n; i++) {
      if (fc > fd) { b = d; d = c; fd = fc; c = b - g * (b - a); fc = f(c); }
      else { a = c; c = d; fc = fd; d = a + g * (b - a); fd = f(d); }
    }
    return 0.5 * (a + b);
  }
  function cross(y, dt, level, rising) {
    var out = [], i, a, b;
    for (i = 1; i < y.length; i++) {
      a = y[i - 1] - level; b = y[i] - level;
      if (rising && a < 0 && b >= 0 && b !== a) out.push((i - 1 + (0 - a) / (b - a)) * dt);
      else if (!rising && a >= 0 && b < 0) out.push((i - 1 + (0 - a) / (b - a)) * dt);
    }
    return out;
  }
  function maxv(a) { var m = a[0], i; for (i = 0; i < a.length; i++) if (a[i] > m) m = a[i]; return m; }
  function minv(a) { var m = a[0], i; for (i = 0; i < a.length; i++) if (a[i] < m) m = a[i]; return m; }
  function mean(a) { var s = 0.0, i; for (i = 0; i < a.length; i++) s += a[i]; return s / a.length; }
  function sinc(y, dt, f) {
    var s = 0.0, c = 0.0, n = y.length, i, th;
    for (i = 0; i < n; i++) { th = 2.0 * PI * f * i * dt; s += y[i] * Math.sin(th); c += y[i] * Math.cos(th); }
    return [2.0 * s / n, 2.0 * c / n];
  }
  function ols(xs, ys) {
    var n = xs.length, sx = 0.0, sy = 0.0, sxy = 0.0, sxx = 0.0, i, den, m;
    for (i = 0; i < n; i++) { sx += xs[i]; sy += ys[i]; sxy += xs[i] * ys[i]; sxx += xs[i] * xs[i]; }
    den = n * sxx - sx * sx;
    m = den === 0 ? 0.0 : (n * sxy - sx * sy) / den;
    return [m, (sy - m * sx) / n];
  }
  function cabs(re, im) { return Math.sqrt(re * re + im * im); }
  function cdiv(a, b) { var d = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; }
  function j0(x) { var s = 0.0, t = 1.0, q = -0.25 * x * x, k; for (k = 0; k < 40; k++) { s += t; t = t * q / ((k + 1.0) * (k + 1.0)); } return s; }
  function jn(n, x) {
    var t = 1.0, k, s = 0.0, q = -0.25 * x * x;
    for (k = 0; k < n; k++) t = t * (0.5 * x) / (k + 1.0);
    for (k = 0; k < 40; k++) { s += t; t = t * q / ((k + 1.0) * (k + 1.0 + n)); }
    return s;
  }
  function rnd(v) { return Math.round(v); }
  function pmod(a, b) { return a - b * Math.floor(a / b); }
  function stat(extra) {
    var o = { init: function () { return { t: 0.0 }; }, step: function (s, p, dt) { s.t += dt; } };
    var k; for (k in extra) o[k] = extra[k];
    return o;
  }

  // ===================================================================================== regulators
  var NR = 400;
  var pe9_reg = stat({
    PARAMS: { kind: 0.0, Vin: 15.0, IL: 0.02, Rs: 100.0, Vz: 6.2, rz: 5.0, beta: 100.0, Is: 1.0e-13, Vnom: 5.0, kl: 1.7e-4, Ro: 0.01, Vdo: 2.0, Vr: 1.0 },
    VARS: ['t', 'Vout'],
    out: function (p, vin, il) {
      var k = rnd(p.kind), rs, rz, idraw, v;
      if (k === 2) return Math.min(p.Vnom + p.kl * (vin - 10.0) - p.Ro * il, vin - p.Vdo);
      rs = p.Rs; rz = p.rz; idraw = k === 0 ? il : il / (p.beta + 1.0);
      v = (vin * rz + p.Vz * rs - idraw * rs * rz) / (rs + rz);
      if ((vin - v) / rs - idraw < 0.0) v = vin - idraw * rs;
      if (k === 0) return v;
      return v - VT * Math.log(il / p.Is + 1.0);
    },
    ripple: function (p, vin, il) {
      var dt = 0.01 / NR, a = [], b = [], i, x, tri, v;
      for (i = 0; i < NR; i++) {
        x = i / NR; tri = x < 0.5 ? 2.0 * x : 2.0 - 2.0 * x; v = vin + p.Vr * (tri - 0.5);
        a.push(v); b.push(pe9_reg.out(p, v, il));
      }
      return [a, b, dt];
    },
    run: function (p, vin, il) { var r = pe9_reg.ripple(p, vin, il); return { Vout: pe9_reg.out(p, vin, il), rin: maxv(r[0]) - minv(r[0]), rout: maxv(r[1]) - minv(r[1]) }; },
    view: function (s, p) { return { t: s.t || 0.0, Vout: pe9_reg.out(p, p.Vin, p.IL) }; },
    measure: function (p) {
      var r = pe9_reg.run(p, p.Vin, p.IL);
      r.line = (pe9_reg.out(p, p.Vin + 1.0, p.IL) - pe9_reg.out(p, p.Vin - 1.0, p.IL)) / 2.0;
      r.Rout = (pe9_reg.out(p, p.Vin, p.IL - 0.01) - pe9_reg.out(p, p.Vin, p.IL + 0.01)) / 0.02;
      return r;
    }
  });
  function reg_line(p) { return rnd(p.kind) === 2 ? p.kl : p.rz / (p.Rs + p.rz); }

  // ===================================================================================== converters
  var pe9_conv = stat({
    PARAMS: { kind: 0.0, D: 9.0, Vref: 5.0, R: 10000.0, Rf: 10000.0, e0: 0.004, e1: -0.003, e2: 0.002, e3: -0.001, Vin: 2.0, Voff: 0.004 },
    VARS: ['t', 'out'],
    dac: function (p, d) {
      var k = rnd(p.kind), es = [p.e0, p.e1, p.e2, p.e3], i = 0.0, b, ideal;
      for (b = 0; b < 4; b++) {
        if ((d >> (3 - b)) & 1) {
          if (k === 0) ideal = p.Vref / (2.0 * p.R) / Math.pow(2.0, b);
          else ideal = p.Vref / (p.R * Math.pow(2.0, b));
          i += ideal / (1.0 + es[b]);
        }
      }
      return i * p.Rf;
    },
    adc: function (p, vin) {
      var lsb = p.Vref / 256.0, code = 0, b, trial;
      for (b = 7; b >= 0; b--) { trial = code | (1 << b); if (vin - p.Voff >= (trial - 0.5) * lsb) code = trial; }
      return code;
    },
    dac_fit: function (p) {
      var xs = [], ys = [], d, f, inl = 0.0, e;
      for (d = 0; d < 16; d++) { xs.push(d); ys.push(pe9_conv.dac(p, d)); }
      f = ols(xs, ys);
      for (d = 0; d < 16; d++) { e = Math.abs(ys[d] - (f[0] * d + f[1])) / f[0]; if (e > inl) inl = e; }
      return { lsb: f[0], off: f[1], inl: inl, fs: ys[15] };
    },
    view: function (s, p) { return { t: s.t || 0.0, out: rnd(p.kind) === 2 ? pe9_conv.adc(p, p.Vin) : pe9_conv.dac(p, rnd(p.D)) }; },
    measure: function (p) {
      var r;
      if (rnd(p.kind) === 2) return { code: pe9_conv.adc(p, p.Vin), lsb: p.Vref / 256.0, main: pe9_conv.adc(p, p.Vin) };
      r = pe9_conv.dac_fit(p); r.Vout = pe9_conv.dac(p, rnd(p.D)); r.main = r.lsb;
      return r;
    }
  });
  function conv_main(p) {
    var k = rnd(p.kind), lsb;
    if (k === 2) { lsb = p.Vref / 256.0; return Math.max(0, Math.min(255, Math.floor((p.Vin - p.Voff) / lsb + 0.5))); }
    return p.Vref * p.Rf / (p.R * (k === 0 ? 16.0 : 8.0));
  }

  // ===================================================================================== passive filters
  function log10(x) { return Math.log10(x); }
  var pe9_filt = stat({
    PARAMS: { kind: 0.0, R: 10000.0, C: 1.0e-8, R2: 100000.0, C2: 1.0e-10, f: 1000.0, Vin: 1.0 },
    VARS: ['t', 'gain_db'],
    h: function (p, f) {
      var k = rnd(p.kind), w = 2.0 * PI * f, r1, c1, r2, c2;
      if (k === 0) return cdiv([1.0, 0.0], [1.0, w * p.R * p.C]);
      if (k === 1) return cdiv([0.0, w * p.R * p.C], [1.0, w * p.R * p.C]);
      r1 = p.R; c1 = p.C; r2 = p.R2; c2 = p.C2;
      return cdiv([0.0, w * r1 * c1], [1.0 - w * w * r1 * c1 * r2 * c2, w * (r1 * c1 + r2 * c2 + r1 * c2)]);
    },
    mag: function (p, f) { var a = pe9_filt.h(p, f); return cabs(a[0], a[1]); },
    db: function (p, f) { return 20.0 * log10(pe9_filt.mag(p, f)); },
    phase: function (p, f) { var a = pe9_filt.h(p, f); return Math.atan2(a[1], a[0]) * 180.0 / PI; },
    corners: function (p) {
      var k = rnd(p.kind), fn, fc, far, far2, roll, f0, hm, fl, fh;
      if (k < 2) {
        fn = 1.0 / (2.0 * PI * p.R * p.C);
        fc = Math.pow(10.0, bis(function (x) { return pe9_filt.mag(p, Math.pow(10.0, x)) - 1.0 / Math.sqrt(2.0); }, log10(fn) - 3.0, log10(fn) + 3.0, 80));
        far = k === 0 ? fc * 10.0 : fc / 10.0; far2 = k === 0 ? fc * 100.0 : fc / 100.0;
        roll = Math.abs(pe9_filt.db(p, far2) - pe9_filt.db(p, far));
        return { fc: fc, fL: fc, fH: fc, roll: roll };
      }
      f0 = 1.0 / (2.0 * PI * Math.sqrt(p.R * p.C * p.R2 * p.C2));
      hm = pe9_filt.mag(p, f0) / Math.sqrt(2.0);
      fl = Math.pow(10.0, bis(function (x) { return pe9_filt.mag(p, Math.pow(10.0, x)) - hm; }, log10(f0) - 4.0, log10(f0), 80));
      fh = Math.pow(10.0, bis(function (x) { return pe9_filt.mag(p, Math.pow(10.0, x)) - hm; }, log10(f0), log10(f0) + 4.0, 80));
      roll = Math.abs(pe9_filt.db(p, fh * 100.0) - pe9_filt.db(p, fh * 10.0));
      return { fc: Math.sqrt(fl * fh), fL: fl, fH: fh, roll: roll, Amax: pe9_filt.mag(p, f0) };
    },
    view: function (s, p) { return { t: s.t || 0.0, gain_db: pe9_filt.db(p, p.f) }; },
    measure: function (p) { var r = pe9_filt.corners(p); r.gain_db = pe9_filt.db(p, p.f); return r; }
  });
  function filt_fc(p) { return rnd(p.kind) < 2 ? 1.0 / (2.0 * PI * p.R * p.C) : 1.0 / (2.0 * PI * Math.sqrt(p.R * p.C * p.R2 * p.C2)); }

  // ===================================================================================== resonance
  var pe9_lcr = stat({
    PARAMS: { mode: 0.0, R: 47.0, L: 0.022, C: 4.7e-8, f: 1000.0, V: 1.0 },
    VARS: ['t', 'I_mA'],
    cur: function (p, f) {
      var w = 2.0 * PI * f, y;
      if (rnd(p.mode) === 0) return p.V / cabs(p.R, w * p.L - 1.0 / (w * p.C));
      y = cdiv([1.0, 0.0], [p.R, w * p.L]);
      return p.V * cabs(y[0], y[1] + w * p.C);
    },
    analyse: function (p) {
      var par = rnd(p.mode) === 1, f0 = 1.0 / (2.0 * PI * Math.sqrt(p.L * p.C)), sg = par ? -1.0 : 1.0, x0, fr, ir, lev, f1, f2;
      x0 = gold(function (x) { return sg * pe9_lcr.cur(p, Math.pow(10.0, x)); }, log10(f0) - 0.5, log10(f0) + 0.5, 120);
      fr = Math.pow(10.0, x0); ir = pe9_lcr.cur(p, fr);
      if (par) lev = function (x) { return 1.0 / pe9_lcr.cur(p, Math.pow(10.0, x)) - Math.sqrt(0.5) / ir; };
      else lev = function (x) { return pe9_lcr.cur(p, Math.pow(10.0, x)) - ir / Math.sqrt(2.0); };
      f1 = Math.pow(10.0, bis(lev, x0 - 1.0, x0, 80)); f2 = Math.pow(10.0, bis(lev, x0, x0 + 1.0, 80));
      return { fr: fr, Ir: ir, f1: f1, f2: f2, Q: fr / (f2 - f1) };
    },
    view: function (s, p) { return { t: s.t || 0.0, I_mA: pe9_lcr.cur(p, p.f) * 1000.0 }; },
    measure: function (p) { var r = pe9_lcr.analyse(p); r.I = pe9_lcr.cur(p, p.f); return r; }
  });
  function lcr_fr(p) { return rnd(p.mode) === 0 ? 1.0 / (2.0 * PI * Math.sqrt(p.L * p.C)) : Math.sqrt(1.0 / (p.L * p.C) - Math.pow(p.R / p.L, 2)) / (2.0 * PI); }
  function lcr_q(p) { return rnd(p.mode) === 0 ? Math.sqrt(p.L / p.C) / p.R : 2.0 * PI * lcr_fr(p) * p.L / p.R; }

  // ===================================================================================== op-amp linear
  var pe9_opl = stat({
    PARAMS: { kind: 0.0, R1: 10000.0, Rf: 100000.0, A0: 200000.0, fa: 5.0, V1: 0.05, V2: 0.03, f: 1000.0 },
    VARS: ['t', 'gain'],
    gng: function (p) {
      var k = rnd(p.kind), r = p.Rf / p.R1;
      if (k === 0) return [-r, 1.0 + r];
      if (k === 1) return [1.0 + r, 1.0 + r];
      if (k === 2 || k === 5) return [-r, 1.0 + 2.0 * r];
      if (k === 3) return [r, 1.0 + r];
      return [1.0, 1.0];
    },
    gain: function (p, f) { var q = pe9_opl.gng(p), a = cdiv([p.A0, 0.0], [1.0, f / p.fa]), d = cdiv([q[1], 0.0], a); return Math.abs(q[0]) / cabs(1.0 + d[0], d[1]); },
    dc_out: function (p) {
      var k = rnd(p.kind), q = pe9_opl.gng(p), lo = 1.0 / (1.0 + q[1] / p.A0);
      if (k === 2 || k === 5) return q[0] * (p.V1 + p.V2) * lo;
      if (k === 3) return q[0] * (p.V2 - p.V1) * lo;
      return q[0] * p.V1 * lo;
    },
    view: function (s, p) { return { t: s.t || 0.0, gain: pe9_opl.gain(p, p.f) }; },
    measure: function (p) {
      var q = pe9_opl.gng(p), g0 = pe9_opl.gain(p, 0.01), f3 = Math.pow(10.0, bis(function (x) { return pe9_opl.gain(p, Math.pow(10.0, x)) - g0 / Math.sqrt(2.0); }, 0.0, 9.0, 90));
      return { gain: g0, f3: f3, gbw: f3 * q[1], dc: pe9_opl.dc_out(p), at_f: pe9_opl.gain(p, p.f) };
    }
  });
  function opl_gain(p) { return Math.abs(pe9_opl.gng(p)[0]); }

  // ===================================================================================== integrator / differentiator
  var NID = 4000;
  var pe9_intdiff = stat({
    PARAMS: { kind: 0.0, wave: 0.0, R: 10000.0, C: 1.0e-8, Rf: 1.0e7, Rs: 1000.0, Vp: 1.0, f: 1000.0 },
    VARS: ['t', 'Vpp'],
    N: NID,
    x_at: function (p, i) {
      var w = rnd(p.wave), u = i / NID, q;
      if (w === 0) return u < 0.5 ? p.Vp : -p.Vp;
      if (w === 1) return p.Vp * Math.sin(2.0 * PI * u);
      q = u + 0.25; q = q - Math.floor(q);
      return p.Vp * (q < 0.5 ? 4.0 * q - 1.0 : 3.0 - 4.0 * q);
    },
    pass: function (p, s0) {
      var n = NID, k = rnd(p.kind), h = 1.0 / p.f / n, tau = k === 0 ? p.Rf * p.C : p.Rs * p.C, g = k === 0 ? -p.Rf / p.R : 1.0;
      var e = Math.exp(-h / tau), kk = tau / h * (1.0 - e), st = [s0], s = s0, xa = pe9_intdiff.x_at(p, 0) * g, xb, i;
      for (i = 0; i < n; i++) {
        xb = pe9_intdiff.x_at(p, (i + 1) % n) * g;
        s = xb + (s - xa) * e - (xb - xa) * kk;
        st.push(s); xa = xb;
      }
      return st;
    },
    trace: function (p) {
      var n = NID, k = rnd(p.kind), tau = k === 0 ? p.Rf * p.C : p.Rs * p.C, st = pe9_intdiff.pass(p, 0.0), y0, xs = [], ys = [], i, x;
      y0 = st[n] / (1.0 - Math.exp(-1.0 / p.f / tau));
      st = pe9_intdiff.pass(p, y0);
      for (i = 0; i < n; i++) { x = pe9_intdiff.x_at(p, i); xs.push(x); ys.push(k === 0 ? st[i] : -p.R * (x - st[i]) / p.Rs); }
      return [xs, ys, 1.0 / p.f / n];
    },
    analyse: function (p) {
      var tr = pe9_intdiff.trace(p), ys = tr[1], dt = tr[2], k = rnd(p.kind), w = rnd(p.wave), vpp = maxv(ys) - minv(ys), T = 1.0 / p.f, rc, dec = 0.0, n, j, pk, lev, i, a, b;
      if (k === 0) rc = w === 0 ? p.Vp * T / (2.0 * vpp) : (w === 1 ? 2.0 * p.Vp / (2.0 * PI * p.f * vpp) : p.Vp * T / (4.0 * vpp));
      else {
        if (w === 0) {
          n = ys.length; j = 0; pk = 0.0;
          for (i = 0; i < n; i++) if (Math.abs(ys[i]) > pk) { pk = Math.abs(ys[i]); j = i; }
          lev = pk / Math.E;
          for (i = j + 1; i < n; i++) if (Math.abs(ys[i]) <= lev) { a = Math.abs(ys[i - 1]); b = Math.abs(ys[i]); dec = (i - 1 + (a - lev) / (a - b) - j) * dt; break; }
          rc = dec * p.R / p.Rs;
        } else if (w === 1) rc = vpp / (2.0 * 2.0 * PI * p.f * p.Vp);
        else rc = vpp / (8.0 * p.Vp * p.f);
      }
      return { Vpp: vpp, tau: rc, decay: dec };
    },
    view: function (s) { return { t: s.t || 0.0, Vpp: 0.0 }; },
    measure: function (p) { return pe9_intdiff.analyse(p); }
  });
  function intdiff_rc(p) { return p.R * p.C; }

  // ===================================================================================== comparators etc.
  var NP = 8, NPER = 500;
  var pe9_cmp = stat({
    PARAMS: { kind: 0.0, Vin: 0.0, A0: 200000.0, Vos: 0.00184, Vsat: 13.0, Vp: 2.0, f: 1000.0, Ch: 1.0e-6, RL: 100000.0, R: 10000.0, Rg: 1000.0, Ra: 10000.0, Rb: 10000.0, eps: 0.002 },
    VARS: ['t', 'Vo'],
    zcd: function (p, vin) { var v = p.A0 * (vin - p.Vos); return Math.max(-p.Vsat, Math.min(p.Vsat, v)); },
    peak: function (p) {
      var n = NP * NPER, dt = 1.0 / p.f / NPER, e = Math.exp(-dt / (p.RL * p.Ch)), xs = [], ys = [], v = 0.0, i, x;
      for (i = 0; i < n; i++) { x = p.Vp * Math.sin(2.0 * PI * i / NPER); v = v * e; if (x > v) v = x; xs.push(x); ys.push(v); }
      return [xs.slice(n - NPER), ys.slice(n - NPER), dt];
    },
    ina: function (p, rg) {
      var g1 = 1.0 + 2.0 * p.R / rg, r1 = p.Ra, r2 = p.Rb, r3 = p.Ra, r4 = p.Rb * (1.0 + p.eps), kp = r4 / (r3 + r4);
      return [g1 * 0.5 * (r2 / r1 + kp * (1.0 + r2 / r1)), kp * (1.0 + r2 / r1) - r2 / r1];
    },
    view: function (s, p) { return { t: s.t || 0.0, Vo: pe9_cmp.zcd(p, p.Vin) }; },
    measure: function (p) {
      var k = rnd(p.kind), trip, pk, hi, lo, q;
      if (k === 0) { trip = bis(function (x) { return pe9_cmp.zcd(p, x); }, -0.1, 0.1, 100); return { trip: trip, Vo: pe9_cmp.zcd(p, p.Vin), main: trip }; }
      if (k === 1) { pk = pe9_cmp.peak(p); hi = maxv(pk[1]); lo = minv(pk[1]); return { Vpk: hi, ripple: hi - lo, Vdc: mean(pk[1]), main: hi }; }
      q = pe9_cmp.ina(p, p.Rg);
      return { Ad: q[0], Acm: q[1], cmrr_db: 20.0 * log10(q[0] / Math.abs(q[1])), main: q[1] };
    }
  });
  function cmp_main(p) {
    var k = rnd(p.kind), r4, kp;
    if (k === 0) return p.Vos;
    if (k === 1) return p.Vp;
    r4 = p.Rb * (1.0 + p.eps); kp = r4 / (p.Ra + r4);
    return kp * (1.0 + p.Rb / p.Ra) - p.Rb / p.Ra;
  }

  // ===================================================================================== triangle generator
  var NTR = 2000;
  var pe9_tri = stat({
    PARAMS: { R1: 10000.0, R2: 20000.0, R: 10000.0, C: 1.0e-8, Vsat: 13.0 },
    VARS: ['t', 'f'],
    trace: function (p) {
      var vth = p.Vsat * p.R1 / p.R2, T = 4.0 * vth * p.R * p.C / p.Vsat, dt = 2.0 * T / NTR, v = -vth, s = p.Vsat, ys = [], sq = [], i, dv, nv, over;
      for (i = 0; i < NTR; i++) {
        ys.push(v); sq.push(s);
        dv = s / (p.R * p.C) * dt; nv = v + dv;
        if (s > 0 && nv >= vth) { over = (nv - vth) / Math.abs(dv) * dt; s = -p.Vsat; nv = vth + s / (p.R * p.C) * over; }
        else if (s < 0 && nv <= -vth) { over = (-vth - nv) / Math.abs(dv) * dt; s = p.Vsat; nv = -vth + s / (p.R * p.C) * over; }
        v = nv;
      }
      return [ys, sq, dt];
    },
    analyse: function (p) {
      var tr = pe9_tri.trace(p), c = cross(tr[0], tr[2], 0.0, true), per = c.length > 1 ? c[1] - c[0] : 0.0;
      return { f: per > 0 ? 1.0 / per : 0.0, amp: 0.5 * (maxv(tr[0]) - minv(tr[0])) };
    },
    view: function (s, p) { return { t: s.t || 0.0, f: p.R2 / (4.0 * p.R1 * p.R * p.C) }; },
    measure: function (p) { return pe9_tri.analyse(p); }
  });
  function tri_f(p) { return p.R2 / (4.0 * p.R1 * p.R * p.C); }

  // ===================================================================================== sweep generators
  var NSW = 2000;
  var pe9_sweep = stat({
    PARAMS: { kind: 0.0, V: 20.0, R: 10000.0, C: 1.0e-7, Vs: 2.0, eta: 0.6, Vd: 0.6, Vv: 2.0, Vz: 5.6, Vbe: 0.6, ro: 1.0e6, A: 0.98, Vce: 0.2 },
    VARS: ['t', 'T'],
    levels: function (p) {
      var k = rnd(p.kind), rc = p.R * p.C, i;
      if (k === 0) return [0.0, p.Vs, p.V, rc];
      if (k === 1) { i = (p.Vz - p.Vbe) / p.R; return [p.Vv, p.eta * p.V + p.Vd, i * p.ro, p.ro * p.C]; }
      if (k === 2) return [p.Vv, p.eta * p.V + p.Vd, p.V, rc];
      if (k === 3) return [p.Vce, p.Vz + p.Vbe, p.V, rc];
      return [0.0, p.Vs, p.V / (1.0 - p.A), rc / (1.0 - p.A)];
    },
    period: function (p) { var l = pe9_sweep.levels(p); return l[3] * Math.log((l[2] - l[0]) / (l[2] - l[1])); },
    trace: function (p) {
      var l = pe9_sweep.levels(p), T = pe9_sweep.period(p), dt = 2.0 * T / NSW, ys = [], i, t;
      for (i = 0; i < NSW; i++) { t = i * dt; t = t - T * Math.floor(t / T); ys.push(l[2] - (l[2] - l[0]) * Math.exp(-t / l[3])); }
      return [ys, dt];
    },
    analyse: function (p) {
      var tr = pe9_sweep.trace(p), l = pe9_sweep.levels(p), c = cross(tr[0], tr[1], 0.5 * (l[0] + l[1]), true), per = c.length > 1 ? c[1] - c[0] : 0.0;
      return { T: per, es: (l[1] - l[0]) / (l[2] - l[0]), lo: l[0], hi: l[1] };
    },
    view: function (s, p) { return { t: s.t || 0.0, T: pe9_sweep.period(p) }; },
    measure: function (p) { return pe9_sweep.analyse(p); }
  });
  function sweep_t(p) { return pe9_sweep.period(p); }

  // ===================================================================================== tuned amplifiers
  var pe9_tuned = stat({
    PARAMS: { kind: 0.0, L: 1.0e-4, C: 1.0e-9, Q: 40.0, kq: 1.0, A0: 50.0, f: 500000.0 },
    VARS: ['t', 'gain'],
    gain: function (p, f) {
      var f0 = 1.0 / (2.0 * PI * Math.sqrt(p.L * p.C)), x = p.Q * (f / f0 - f0 / f), kq, a;
      if (rnd(p.kind) === 0) return p.A0 / Math.sqrt(1.0 + x * x);
      kq = p.kq; a = 1.0 + kq * kq - x * x;
      return p.A0 * 2.0 * kq / Math.sqrt(a * a + 4.0 * x * x);
    },
    analyse: function (p) {
      var f0 = 1.0 / (2.0 * PI * Math.sqrt(p.L * p.C)), gm = pe9_tuned.gain(p, f0), lev, x0, f1, f2;
      if (rnd(p.kind) === 1 && p.kq > 1.0) gm = p.A0;
      lev = function (x) { return pe9_tuned.gain(p, Math.pow(10.0, x)) - gm / Math.sqrt(2.0); };
      x0 = log10(f0);
      f1 = Math.pow(10.0, bis(lev, x0 - 1.0, x0, 80)); f2 = Math.pow(10.0, bis(lev, x0, x0 + 1.0, 80));
      return { f0: Math.sqrt(f1 * f2), f1: f1, f2: f2, bw: f2 - f1, Gmax: gm };
    },
    view: function (s, p) { return { t: s.t || 0.0, gain: pe9_tuned.gain(p, p.f) }; },
    measure: function (p) { return pe9_tuned.analyse(p); }
  });
  function tuned_f0(p) { return 1.0 / (2.0 * PI * Math.sqrt(p.L * p.C)); }

  // ===================================================================================== counters
  var pe9_cnt = stat({
    PARAMS: { kind: 0.0, N: 10.0, tpd: 2.5e-8, fclk: 1.0e5 },
    VARS: ['t', 'mod'],
    bits: function (p) { var n = rnd(p.N), b = 1; while ((1 << b) < n) b++; return b; },
    run: function (p) {
      var n = rnd(p.N), nb = pe9_cnt.bits(p), msb = 1 << (nb - 1), k = rnd(p.kind), c = 0, edges = 0, dmax = 0.0, seq = [], it, old, nxt, ch, last, i, d;
      for (it = 0; it < 4 * n; it++) {
        old = c; nxt = c + 1;
        if (k === 1 && c === n - 1) nxt = 0;
        if (k === 0) {
          ch = old ^ (nxt & ((1 << nb) - 1)); last = 0;
          for (i = 0; i < nb; i++) if ((ch >> i) & 1) last = i;
          d = (last + 1) * p.tpd;
          if (nxt === n) nxt = 0;
        } else d = old !== nxt ? p.tpd : 0.0;
        if ((old & msb) === 0 && (nxt & msb) !== 0) { edges++; if (d > dmax) dmax = d; }
        c = nxt;
        if (seq.length < n) seq.push(c);
      }
      return { mod: edges ? 4.0 * n / edges : 0.0, delay: dmax, seq: seq };
    },
    view: function (s, p) { return { t: s.t || 0.0, mod: p.N }; },
    measure: function (p) { var r = pe9_cnt.run(p); return { mod: r.mod, delay: r.delay, fout: r.mod ? p.fclk / r.mod : 0.0 }; }
  });
  function cnt_mod(p) { return rnd(p.N); }

  // ===================================================================================== AM / FM
  var SPC = 64;
  var pe9_amfm = stat({
    PARAMS: { kind: 0.0, Vc: 2.0, Vm: 0.5, fc: 20000.0, fm: 500.0, ka: 0.4, kf: 1500.0, kd: 0.001 },
    VARS: ['t', 'm'],
    signal: function (p) {
      var nc = rnd(p.fc / p.fm), n = nc * SPC, dt = 1.0 / p.fm / n, y = [], k = rnd(p.kind), i, t, beta;
      for (i = 0; i < n; i++) {
        t = i * dt;
        if (k === 0) y.push(p.Vc * (1.0 + p.ka * p.Vm * Math.sin(2.0 * PI * p.fm * t)) * Math.sin(2.0 * PI * p.fc * t));
        else { beta = p.kf * p.Vm / p.fm; y.push(p.Vc * Math.sin(2.0 * PI * p.fc * t + beta * Math.sin(2.0 * PI * p.fm * t))); }
      }
      return [y, dt];
    },
    lines: function (p) {
      var sg = pe9_amfm.signal(p), out = [], n, sc;
      for (n = -3; n < 4; n++) { sc = sinc(sg[0], sg[1], p.fc + n * p.fm); out.push(rnd(p.kind) === 1 ? sc[0] : cabs(sc[0], sc[1])); }
      return out;
    },
    view: function (s, p) { return { t: s.t || 0.0, m: p.ka * p.Vm }; },
    measure: function (p) {
      var k = rnd(p.kind), ln = pe9_amfm.lines(p), sg, y, hi, nc, mn, j, q, i, m;
      if (k === 0) {
        sg = pe9_amfm.signal(p); y = sg[0]; hi = maxv(y); nc = Math.floor(y.length / SPC); mn = 1e9;
        for (j = 0; j < nc; j++) { q = 0.0; for (i = j * SPC; i < (j + 1) * SPC; i++) if (y[i] > q) q = y[i]; if (q < mn) mn = q; }
        m = (hi - mn) / (hi + mn);
        return { m: m, usb: ln[4], lsb: ln[2], car: ln[3], demod: m * p.Vc, main: m };
      }
      return { car: ln[3], s1: ln[4], s2: ln[5], beta: p.kf * p.Vm / p.fm, demod: p.kd * p.kf * p.Vm, main: ln[3] / p.Vc };
    }
  });
  function amfm_main(p) { return rnd(p.kind) === 0 ? p.ka * p.Vm : j0(p.kf * p.Vm / p.fm); }

  // ===================================================================================== analog computer
  var NAC = 1500;
  var pe9_acomp = stat({
    PARAMS: { kind: 0.0, R: 100000.0, C: 1.0e-7, Vg: 1.0, V0: 5.0, a1: 2.0, b1: 1.0, c1: 5.0, a2: 1.0, b2: 3.0, c2: 10.0, z: 0.2 },
    VARS: ['t', 'main'],
    f: function (p, k, s) {
      var tau = p.R * p.C, w;
      if (k === 0) return [p.Vg / tau, -s[0] / tau];
      if (k === 1) return [(p.c1 - p.a1 * s[0] - p.b1 * s[1]) / tau, (p.c2 - p.a2 * s[0] - p.b2 * s[1]) / tau];
      w = 1.0 / tau;
      return [s[1], -2.0 * p.z * w * s[1] - w * w * s[0]];
    },
    run: function (p) {
      var k = rnd(p.kind), tau = p.R * p.C, span = k === 0 ? 2.0 * tau * Math.sqrt(2.0 * p.V0 / p.Vg) : (k === 1 ? 12.0 * tau : 6.0 * PI * tau);
      var dt = span / NAC, s = k === 0 ? [0.0, p.V0] : (k === 1 ? [0.0, 0.0] : [p.V0, 0.0]), a = [], b = [], i, k1, k2, k3, k4, F = pe9_acomp.f;
      for (i = 0; i < NAC; i++) {
        a.push(s[0]); b.push(s[1]);
        k1 = F(p, k, s);
        k2 = F(p, k, [s[0] + 0.5 * dt * k1[0], s[1] + 0.5 * dt * k1[1]]);
        k3 = F(p, k, [s[0] + 0.5 * dt * k2[0], s[1] + 0.5 * dt * k2[1]]);
        k4 = F(p, k, [s[0] + dt * k3[0], s[1] + dt * k3[1]]);
        s = [s[0] + dt / 6.0 * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0]), s[1] + dt / 6.0 * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])];
      }
      return [a, b, dt];
    },
    analyse: function (p) {
      var k = rnd(p.kind), r = pe9_acomp.run(p), a = r[0], b = r[1], dt = r[2], c, t0, per;
      if (k === 0) { c = cross(b, dt, 0.0, false); t0 = c.length ? c[0] : 0.0; return { T0: t0, main: t0, vland: p.Vg * t0 / (p.R * p.C) }; }
      if (k === 1) return { x: a[a.length - 1], y: b[b.length - 1], main: a[a.length - 1] };
      c = cross(a, dt, 0.0, false); per = c.length > 1 ? c[1] - c[0] : 0.0;
      return { fd: per > 0 ? 1.0 / per : 0.0, main: per > 0 ? 1.0 / per : 0.0 };
    },
    view: function (s) { return { t: s.t || 0.0, main: 0.0 }; },
    measure: function (p) { return pe9_acomp.analyse(p); }
  });
  function acomp_main(p) {
    var k = rnd(p.kind), tau = p.R * p.C;
    if (k === 0) return tau * Math.sqrt(2.0 * p.V0 / p.Vg);
    if (k === 1) return (p.c1 * p.b2 - p.b1 * p.c2) / (p.a1 * p.b2 - p.b1 * p.a2);
    return Math.sqrt(1.0 - p.z * p.z) / (2.0 * PI * tau);
  }

  // ===================================================================================== power amplifiers
  var NPA = 720;
  var pe9_pa = stat({
    PARAMS: { kind: 0.0, Vcc: 12.0, RL: 8.0, Vd: 3.0, Vg: 0.6 },
    VARS: ['t', 'eta'],
    wave: function (p) {
      var k = rnd(p.kind), vo = [], isup = [], i, vd, ic, a, v;
      for (i = 0; i < NPA; i++) {
        vd = p.Vd * Math.sin(2.0 * PI * i / NPA);
        if (k === 0) {
          ic = p.Vcc / (2.0 * p.RL) + vd / p.RL; ic = Math.max(0.0, Math.min(p.Vcc / p.RL, ic));
          vo.push((ic - p.Vcc / (2.0 * p.RL)) * p.RL); isup.push(ic);
        } else {
          a = Math.abs(vd) - p.Vg; v = a > 0.0 ? a : 0.0; v = Math.min(v, p.Vcc); v = vd >= 0.0 ? v : -v;
          vo.push(v); isup.push(Math.abs(v) / p.RL);
        }
      }
      return [vo, isup];
    },
    analyse: function (p) {
      var w = pe9_pa.wave(p), vo = w[0], n = NPA, m = 0.0, po = 0.0, pdc, h = [], k, s, c, i, th, hs = 0.0;
      for (i = 0; i < n; i++) m += vo[i];
      m /= n;
      for (i = 0; i < n; i++) po += (vo[i] - m) * (vo[i] - m);
      po = po / n / p.RL;
      pdc = p.Vcc * mean(w[1]);
      for (k = 1; k < 10; k++) {
        s = 0.0; c = 0.0;
        for (i = 0; i < n; i++) { th = 2.0 * PI * k * i / n; s += vo[i] * Math.sin(th); c += vo[i] * Math.cos(th); }
        h.push(cabs(2.0 * s / n, 2.0 * c / n));
      }
      for (k = 1; k < 9; k++) hs += h[k] * h[k];
      return { Po: po, Pdc: pdc, eta: pdc > 0 ? po / pdc : 0.0, Vo: h[0], thd: h[0] > 0 ? Math.sqrt(hs) / h[0] : 0.0 };
    },
    view: function (s) { return { t: s.t || 0.0, eta: 0.0 }; },
    measure: function (p) { return pe9_pa.analyse(p); }
  });
  function pa_eta(p) { return rnd(p.kind) === 0 ? Math.pow(p.Vd / p.Vcc, 2) : PI * p.Vd / (4.0 * p.Vcc); }

  // ===================================================================================== op-amp parameters
  var pe9_opp = stat({
    PARAMS: { test: 0.0, Vos: 1.0e-3, Ib: 8.0e-8, cmrr_db: 90.0, SR: 5.0e5, A0: 2.0e5, fa: 5.0, f: 1000.0 },
    VARS: ['t', 'Vo'],
    gain100: function (p, f) { var a = cdiv([p.A0, 0.0], [1.0, f / p.fa]), d = cdiv([101.0, 0.0], a); return 100.0 / cabs(1.0 + d[0], d[1]); },
    readings: function (p) {
      var cm = Math.pow(10.0, p.cmrr_db / 20.0), g0 = pe9_opp.gain100(p, 0.01);
      var f3 = Math.pow(10.0, bis(function (x) { return pe9_opp.gain100(p, Math.pow(10.0, x)) - g0 / Math.sqrt(2.0); }, 0.0, 9.0, 90));
      return { vo_off: 1001.0 * p.Vos + p.Ib * 1.0e5, vo_b0: p.Vos, vo_b1: p.Vos - p.Ib * 1.0e6, dvo_cm: 100.0 * 10.0 / cm, rise: 8.0 / p.SR, f3: f3, g_f: pe9_opp.gain100(p, p.f) };
    },
    view: function (s) { return { t: s.t || 0.0, Vo: 0.0 }; },
    measure: function (p) {
      var r = pe9_opp.readings(p);
      r.Vos_m = r.vo_off / 1001.0; r.Ib_m = (r.vo_b0 - r.vo_b1) / 1.0e6; r.cmrr_m = 20.0 * log10(100.0 * 10.0 / r.dvo_cm);
      r.SR_m = 8.0 / r.rise; r.gbw = r.f3 * 101.0;
      return r;
    }
  });
  function opp_gbw(p) { return p.A0 * p.fa; }

  // ===================================================================================== crystal oscillator
  var pe9_xtal = stat({
    PARAMS: { L1: 0.012, C1: 2.0e-14, C0: 5.0e-12, CL: 2.0e-11, T: 25.0, Ti: 25.0, a3: 1.0e-4, a1: -0.2 },
    VARS: ['t', 'f'],
    freq: function (p, cl, t) {
      var fs = 1.0 / (2.0 * PI * Math.sqrt(p.L1 * p.C1)), u = t - p.Ti;
      return fs * (1.0 + p.C1 / (2.0 * (p.C0 + cl))) * (1.0 + 1.0e-6 * (p.a3 * u * u * u + p.a1 * u));
    },
    view: function (s, p) { return { t: s.t || 0.0, f: pe9_xtal.freq(p, p.CL, p.T) }; },
    measure: function (p) {
      var fs = 1.0 / (2.0 * PI * Math.sqrt(p.L1 * p.C1));
      return { f: pe9_xtal.freq(p, p.CL, p.T), fs: fs, ppm: (pe9_xtal.freq(p, p.CL, p.T) / pe9_xtal.freq(p, p.CL, p.Ti) - 1.0) * 1e6 };
    }
  });
  function xtal_f(p) {
    var fs = 1.0 / (2.0 * PI * Math.sqrt(p.L1 * p.C1)), u = p.T - p.Ti;
    return fs * (1.0 + p.C1 / (2.0 * (p.C0 + p.CL))) * (1.0 + 1.0e-6 * (p.a3 * u * u * u + p.a1 * u));
  }

  // ===================================================================================== multivibrators
  var pe9_mv = stat({
    PARAMS: { tech: 0.0, mode: 0.0, R1: 10000.0, R2: 22000.0, R: 10000.0, C: 1.0e-7, Vcc: 9.0, Vbe: 0.65, Vce: 0.1, Vsat: 13.0, Vd: 0.7, ftrig: 1000.0 },
    VARS: ['t', 'main'],
    times: function (p) {
      var tech = rnd(p.tech), mode = rnd(p.mode), C = p.C, lg, a, b, t, w, bb;
      if (tech === 0) {
        lg = Math.log((2.0 * p.Vcc - p.Vce - p.Vbe) / (p.Vcc - p.Vbe));
        if (mode === 0) { a = p.R1 * C * lg; b = p.R2 * C * lg; return { main: a + b, duty: a / (a + b), thi: a, tlo: b }; }
        if (mode === 1) return { main: p.R * C * lg, duty: 0.0, thi: p.R * C * lg, tlo: 0.0 };
        return { main: 2.0 / p.ftrig, duty: 0.5, thi: 1.0 / p.ftrig, tlo: 1.0 / p.ftrig };
      }
      if (tech === 1) {
        if (mode === 0) { a = (p.R1 + p.R2) * C * Math.log(2.0); b = p.R2 * C * Math.log(2.0); return { main: a + b, duty: a / (a + b), thi: a, tlo: b }; }
        if (mode === 1) return { main: p.R * C * Math.log(3.0), duty: 0.0, thi: p.R * C * Math.log(3.0), tlo: 0.0 };
        return { main: 2.0 * p.Vcc / 3.0, duty: 0.5, thi: 2.0 * p.Vcc / 3.0, tlo: p.Vcc / 3.0 };
      }
      bb = p.R1 / (p.R1 + p.R2);
      if (mode === 0) { t = 2.0 * p.R * C * Math.log((1.0 + bb) / (1.0 - bb)); return { main: t, duty: 0.5, thi: 0.5 * t, tlo: 0.5 * t }; }
      if (mode === 1) { w = p.R * C * Math.log((1.0 + p.Vd / p.Vsat) / (1.0 - bb)); return { main: w, duty: 0.0, thi: w, tlo: 0.0 }; }
      return { main: bb * p.Vsat, duty: 0.5, thi: bb * p.Vsat, tlo: -bb * p.Vsat };
    },
    trace: function (p) {
      var tech = rnd(p.tech), mode = rnd(p.mode), t = pe9_mv.times(p), n = 1200, vp, dt, xs = [], ys = [], hi, i, u, x, per, vtop, vbot;
      if (mode === 2 && tech > 0) {
        vp = tech === 1 ? p.Vcc : 1.5 * t.thi; dt = 2.0e-3 / n; hi = true;
        for (i = 0; i < n; i++) {
          u = pmod(2.0 * i / n, 1.0);
          x = tech === 1 ? vp * (u < 0.5 ? 2.0 * u : 2.0 - 2.0 * u) : vp * (u < 0.5 ? 4.0 * u - 1.0 : 3.0 - 4.0 * u);
          if (x >= t.thi) hi = false;
          if (x <= t.tlo) hi = true;
          xs.push(x); ys.push(tech === 1 ? (hi ? p.Vcc : 0.0) : (hi ? p.Vsat : -p.Vsat));
        }
        return [xs, ys, dt];
      }
      per = mode !== 1 ? t.thi + t.tlo : 2.0 * t.thi; dt = 3.0 * per / n;
      for (i = 0; i < n; i++) {
        u = pmod(i * dt, per); hi = u < t.thi; vtop = tech === 2 ? p.Vsat : p.Vcc; vbot = tech === 2 ? -p.Vsat : 0.0;
        ys.push(hi ? vtop : vbot); xs.push(mode === 1 && u < dt * 4 ? vtop * 0.8 : 0.0);
      }
      return [xs, ys, dt];
    },
    view: function (s, p) { return { t: s.t || 0.0, main: pe9_mv.times(p).main }; },
    measure: function (p) { return pe9_mv.times(p); }
  });
  function mv_main(p) {
    var tech = rnd(p.tech), mode = rnd(p.mode), k, b;
    if (tech === 0) { k = Math.log((2.0 * p.Vcc - p.Vce - p.Vbe) / (p.Vcc - p.Vbe)); return mode === 0 ? (p.R1 + p.R2) * p.C * k : (mode === 1 ? p.R * p.C * k : 2.0 / p.ftrig); }
    if (tech === 1) return mode === 0 ? (p.R1 + 2.0 * p.R2) * p.C * Math.log(2.0) : (mode === 1 ? p.R * p.C * Math.log(3.0) : 2.0 * p.Vcc / 3.0);
    b = p.R1 / (p.R1 + p.R2);
    if (mode === 0) return 2.0 * p.R * p.C * Math.log((1.0 + b) / (1.0 - b));
    if (mode === 1) return p.R * p.C * Math.log((1.0 + p.Vd / p.Vsat) / (1.0 - b));
    return b * p.Vsat;
  }

  // ===================================================================================== CE amplifier design
  function cm(a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; }
  var pe9_ce = stat({
    PARAMS: { Vcc: 12.0, R1: 47000.0, R2: 10000.0, Rc: 2200.0, RL: 10000.0, Re1: 68.0, Re2: 932.0, beta: 200.0, Vbe: 0.65, Cin: 1.0e-5, CE: 1.0e-4, Co: 1.0e-5, Cx: 2.4e-11, f: 10000.0, Rx: 0.0 },
    VARS: ['t', 'gain'],
    bias: function (p) {
      var vth = p.Vcc * p.R2 / (p.R1 + p.R2), rth = p.R1 * p.R2 / (p.R1 + p.R2), ie = (vth - p.Vbe) / (p.Re1 + p.Re2 + rth / (p.beta + 1.0));
      return [ie, VT / ie, rth];
    },
    h: function (p, f, rx) {
      var b = pe9_ce.bias(p), re = b[1], rth = b[2], w = 2.0 * PI * f, zce = cdiv([1.0, 0.0], [0.0, w * p.CE]);
      var ze2 = cdiv(cm([p.Re2, 0.0], zce), [p.Re2 + zce[0], zce[1]]), ze = [p.Re1 + ze2[0], ze2[1]];
      var zb = [(p.beta + 1.0) * (re + ze[0]), (p.beta + 1.0) * ze[1]], zin = cdiv(cm([rth, 0.0], zb), [rth + zb[0], zb[1]]);
      var cin = cdiv([1.0, 0.0], [0.0, w * p.Cin]), div = cdiv(zin, [zin[0] + rx + cin[0], zin[1] + cin[1]]);
      var rp = p.Rc * p.RL / (p.Rc + p.RL), alpha = p.beta / (p.beta + 1.0), av = cdiv([alpha * rp, 0.0], [re + ze[0], ze[1]]);
      var to = w * p.Co * (p.Rc + p.RL), ho = cdiv([0.0, to], [1.0, to]), hh = cdiv([1.0, 0.0], [1.0, w * rp * p.Cx]);
      return cm(cm(div, av), cm(ho, hh));
    },
    gain: function (p, f, rx) { var a = pe9_ce.h(p, f, rx); return cabs(a[0], a[1]); },
    analyse: function (p) {
      var am = pe9_ce.gain(p, 10000.0, 0.0), lev = function (x) { return pe9_ce.gain(p, Math.pow(10.0, x), 0.0) - am / Math.sqrt(2.0); };
      var fl = Math.pow(10.0, bis(lev, -1.0, 4.0, 80)), fh = Math.pow(10.0, bis(lev, 4.0, 9.0, 80)), g1 = pe9_ce.gain(p, 10000.0, 1000.0);
      return { Amid: am, fL: fl, fH: fh, Zin: 1000.0 * g1 / (am - g1) };
    },
    view: function (s, p) { return { t: s.t || 0.0, gain: pe9_ce.gain(p, p.f, p.Rx) }; },
    measure: function (p) { return pe9_ce.analyse(p); }
  });
  function ce_amid(p) { var b = pe9_ce.bias(p), rp = p.Rc * p.RL / (p.Rc + p.RL); return p.beta / (p.beta + 1.0) * rp / (b[1] + p.Re1); }

  H.register({
    K: { pe9_reg: pe9_reg, pe9_conv: pe9_conv, pe9_filt: pe9_filt, pe9_lcr: pe9_lcr, pe9_opl: pe9_opl, pe9_intdiff: pe9_intdiff,
      pe9_cmp: pe9_cmp, pe9_tri: pe9_tri, pe9_sweep: pe9_sweep, pe9_tuned: pe9_tuned, pe9_cnt: pe9_cnt, pe9_amfm: pe9_amfm,
      pe9_acomp: pe9_acomp, pe9_pa: pe9_pa, pe9_opp: pe9_opp, pe9_xtal: pe9_xtal, pe9_mv: pe9_mv, pe9_ce: pe9_ce },
    TEXTBOOK: { pe9_reg_line: reg_line, pe9_conv_main: conv_main, pe9_filt_fc: filt_fc, pe9_lcr_fr: lcr_fr, pe9_lcr_q: lcr_q,
      pe9_opl_gain: opl_gain, pe9_intdiff_rc: intdiff_rc, pe9_cmp_main: cmp_main, pe9_tri_f: tri_f, pe9_sweep_t: sweep_t,
      pe9_tuned_f0: tuned_f0, pe9_cnt_mod: cnt_mod, pe9_amfm_main: amfm_main, pe9_acomp_main: acomp_main, pe9_pa_eta: pa_eta,
      pe9_opp_gbw: opp_gbw, pe9_xtal_f: xtal_f, pe9_mv_main: mv_main, pe9_ce_amid: ce_amid },
    CALCS: {}
  });
  void jn;
})(typeof window !== 'undefined' ? window : this);
