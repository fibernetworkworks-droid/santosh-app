/* Kernel pack `ug_analog_w8`: the exact JavaScript twin of app/prayog/packs/ug_analog_w8.py. Same formulas, same
   algorithms, same fixed sample and bisection counts, same numbers (the server's tests run both and compare). Analog
   electronics, devices and instrument set-ups of the undergraduate syllabus (wave 8). Every kernel is prefixed `u8_`;
   the rig `ug8-analog-bench` also calls the helper functions (trace, gain, solve ...) of each kernel. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, KB = 1.380649e-23, QE = 1.602176634e-19, VT300 = 0.025852, NS = 2400;

  function bis(f, lo, hi, n) {
    var flo = f(lo), i, mid, fm;
    for (i = 0; i < n; i++) {
      mid = 0.5 * (lo + hi); fm = f(mid);
      if ((fm > 0.0) === (flo > 0.0)) { lo = mid; flo = fm; } else hi = mid;
    }
    return 0.5 * (lo + hi);
  }
  function ols(xs, ys) {
    var n = xs.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, den;
    for (i = 0; i < n; i++) sx += xs[i];
    for (i = 0; i < n; i++) sy += ys[i];
    for (i = 0; i < n; i++) sxy += xs[i] * ys[i];
    for (i = 0; i < n; i++) sxx += xs[i] * xs[i];
    den = n * sxx - sx * sx;
    return den === 0 ? 0.0 : (n * sxy - sx * sy) / den;
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
  function cmul(a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; }
  function cdiv(a, b) { var d = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; }
  function cabs(a) { return Math.sqrt(a[0] * a[0] + a[1] * a[1]); }
  function maxOf(a) { var m = a[0], i; for (i = 1; i < a.length; i++) if (a[i] > m) m = a[i]; return m; }
  function minOf(a) { var m = a[0], i; for (i = 1; i < a.length; i++) if (a[i] < m) m = a[i]; return m; }
  function deg(r) { return r * 180 / PI; }
  function stat(extra) {
    var o = { init: function () { return { t: 0.0 }; }, step: function (s, p, dt) { s.t += dt; } };
    var k; for (k in extra) o[k] = extra[k];
    return o;
  }

  // ===================================================================================== p-n diode / LED
  var KB_VS = [0.60, 0.65, 0.70, 0.75, 0.80, 0.90, 1.00, 1.10, 1.20, 1.35, 1.50], DLSB = 1.1 / 1024.0;
  var u8_diode = stat({
    PARAMS: { Vs: 1.0, Rser: 100.0, Is: 7.03e-9, n: 1.80, Rs: 0.034, Rsh: 1.0e9, T: 300.0, kB: KB, adc: 0.0 },
    VARS: ['t', 'V', 'I_mA'],
    vt: function (p) { return p.kB * p.T / QE; },
    i_of: function (p, vj) { return p.Is * (Math.exp(vj / (p.n * u8_diode.vt(p))) - 1.0) + vj / p.Rsh; },
    solve: function (p, vs) {
      var r = p.Rser + p.Rs, lo = Math.min(vs, 0.0) - 1.0, hi = Math.max(vs, 0.0) + 1.0;
      var vj = bis(function (x) { return vs - u8_diode.i_of(p, x) * r - x; }, lo, hi, 100), i = u8_diode.i_of(p, vj);
      return [vj + i * p.Rs, i];
    },
    v_at: function (p, i) { var vj = bis(function (x) { return u8_diode.i_of(p, x) - i; }, -2.0, 4.0, 100); return vj + i * p.Rs; },
    read: function (p, vs) {
      var r = u8_diode.solve(p, vs), v = r[0], i = r[1], vr;
      if (Math.round(p.adc) === 1) {
        v = Math.floor(v / DLSB) * DLSB;
        vr = Math.floor(i * p.Rser / DLSB) * DLSB;
        i = vr / p.Rser;
      }
      return [v, i];
    },
    kfit: function (p) {
      var xs = [], ys = [], j, r, m;
      for (j = 0; j < KB_VS.length; j++) { r = u8_diode.read(p, KB_VS[j]); if (r[1] > 0) { xs.push(r[0]); ys.push(Math.log(r[1])); } }
      m = ols(xs, ys);
      return m > 0 ? QE / (p.n * p.T * m) : 0.0;
    },
    view: function (s, p) { var r = u8_diode.solve(p, p.Vs); return { t: s.t || 0.0, V: r[0], I_mA: r[1] * 1000.0 }; },
    measure: function (p) {
      var r = u8_diode.read(p, p.Vs);
      return { V: r[0], I: r[1], Vcut: u8_diode.v_at(p, 1.0e-3), rd: (u8_diode.v_at(p, 0.0105) - u8_diode.v_at(p, 0.0095)) / 0.001,
        Irev: -u8_diode.i_of(p, -5.0), kfit: u8_diode.kfit(p) };
    }
  });
  function diode_vcut(p) { var vt = p.kB * p.T / QE; return p.n * vt * Math.log(1.0e-3 / p.Is + 1.0) + 1.0e-3 * p.Rs; }
  function diode_kb(p) { return p.kB; }

  // ===================================================================================== tunnel diode
  var u8_tunnel = stat({
    PARAMS: { V: 0.1, Ip: 1.0e-3, Vp: 0.065, Iv: 1.2e-4, Vv: 0.35, A2: 15.0, Is: 1.0e-12, n: 1.0 },
    VARS: ['t', 'V', 'I_mA'],
    i_of: function (p, v) {
      return (p.Ip * (v / p.Vp) * Math.exp(1.0 - v / p.Vp) + p.Iv * Math.exp(p.A2 * (v - p.Vv)) + p.Is * (Math.exp(v / (p.n * VT300)) - 1.0));
    },
    scan: function (p) {
      var n = 6001, ii = [], k, kp = 0, kv, ipk, smin = 0.0, s;
      for (k = 0; k < n; k++) ii.push(u8_tunnel.i_of(p, 0.0001 * k));
      while (kp < n - 1 && ii[kp + 1] >= ii[kp]) kp += 1;
      kv = kp;
      while (kv < n - 1 && ii[kv + 1] <= ii[kv]) kv += 1;
      ipk = ii[kp];
      for (k = kp + 1; k < kv + 1; k++) { s = (ii[k] - ii[k - 1]) / 0.0001; if (s < smin) smin = s; }
      return { Ipk: ipk, Vpk: 0.0001 * kp, Ival: ii[kv], Vval: 0.0001 * kv, pvr: ipk / ii[kv], Rneg: smin < 0 ? 1.0 / smin : 0.0 };
    },
    view: function (s, p) { return { t: s.t || 0.0, V: p.V, I_mA: u8_tunnel.i_of(p, p.V) * 1000.0 }; },
    measure: function (p) { var m = u8_tunnel.scan(p); m.I = u8_tunnel.i_of(p, p.V); return m; }
  });
  function tunnel_ip(p) { return p.Ip; }

  // ===================================================================================== BJT
  var u8_bjt = stat({
    PARAMS: { Ib: 2.0e-5, Vce: 5.0, Is: 1.0e-14, bF: 250.0, VA: 80.0, VAr: 150.0, Vsat: 0.05, Vin: 0.0, Vcc: 5.0, Rb: 10000.0, Rc: 1000.0, dIb: 5.0e-6, dVce: 1.0 },
    VARS: ['t', 'Vbe', 'Ic_mA', 'Vout'],
    vbe: function (p, ib, vce) { return VT300 * Math.log(ib * p.bF * (1.0 + vce / p.VAr) / p.Is + 1.0); },
    ic: function (p, ib, vce) { var x = u8_bjt.vbe(p, ib, vce); return p.Is * (Math.exp(x / VT300) - 1.0) * (1.0 + vce / p.VA) * (1.0 - Math.exp(-vce / p.Vsat)); },
    hparams: function (p) {
      var ib = p.Ib, vce = p.Vce, d = p.dIb, dv = p.dVce, B = u8_bjt;
      return { hie: (B.vbe(p, ib + d, vce) - B.vbe(p, ib - d, vce)) / (2.0 * d), hfe: (B.ic(p, ib + d, vce) - B.ic(p, ib - d, vce)) / (2.0 * d),
        hoe: (B.ic(p, ib, vce + dv) - B.ic(p, ib, vce - dv)) / (2.0 * dv), hre: (B.vbe(p, ib, vce + dv) - B.vbe(p, ib, vce - dv)) / (2.0 * dv) };
    },
    ib_in: function (p, vin, vce) {
      if (vin <= 0.0) return 0.0;
      var k = p.Is / p.bF / (1.0 + vce / p.VAr);
      var x = bis(function (v) { return vin - p.Rb * k * (Math.exp(v / VT300) - 1.0) - v; }, 0.0, vin, 80);
      return k * (Math.exp(x / VT300) - 1.0);
    },
    vout: function (p, vin) {
      return bis(function (vce) {
        var ib = u8_bjt.ib_in(p, vin, vce);
        if (ib <= 0.0) return p.Vcc - vce;
        return p.Vcc - u8_bjt.ic(p, ib, vce) * p.Rc - vce;
      }, 1.0e-9, p.Vcc, 60);
    },
    vth: function (p) {
      var vce = 0.5 * p.Vcc, ic = (p.Vcc - vce) / p.Rc;
      var e = ic / (p.Is * (1.0 + vce / p.VA) * (1.0 - Math.exp(-vce / p.Vsat))) + 1.0;
      var ib = p.Is / p.bF * (e - 1.0) / (1.0 + vce / p.VAr);
      return VT300 * Math.log(e) + p.Rb * ib;
    },
    view: function (s, p) { return { t: s.t || 0.0, Vbe: u8_bjt.vbe(p, p.Ib, p.Vce), Ic_mA: u8_bjt.ic(p, p.Ib, p.Vce) * 1000.0, Vout: p.Vcc }; },
    measure: function (p) {
      var m = u8_bjt.hparams(p);
      m.Vbe = u8_bjt.vbe(p, p.Ib, p.Vce); m.Ic = u8_bjt.ic(p, p.Ib, p.Vce); m.Vout = u8_bjt.vout(p, p.Vin); m.Vth = u8_bjt.vth(p);
      return m;
    }
  });
  function bjt_hfe(p) { var v = p.Vce; return p.bF * (1.0 + v / p.VA) * (1.0 + v / p.VAr) * (1.0 - Math.exp(-v / p.Vsat)); }
  function bjt_vth(p) { var ic = 0.5 * p.Vcc / p.Rc; return VT300 * Math.log(ic / p.Is) + p.Rb * ic / p.bF; }

  // ===================================================================================== push-pull
  var u8_pp = stat({
    PARAMS: { Vp: 3.0, Vg: 0.6, Vbias: 0.55, mode: 0.0, RL: 8.0, f: 1000.0 },
    VARS: ['t', 'Vop', 'thd_pct'],
    dz: function (p) { return Math.round(p.mode) === 1 ? Math.max(0.0, p.Vg - p.Vbias) : p.Vg; },
    wave: function (p) {
      var d = u8_pp.dz(p), out = [], i, v;
      for (i = 0; i < NS; i++) { v = p.Vp * Math.sin(2.0 * PI * (i + 0.5) / NS); out.push(v > d ? v - d : v < -d ? v + d : 0.0); }
      return out;
    },
    analyse: function (p) {
      var y = u8_pp.wave(p), b1 = 0.0, ms = 0.0, i, thd;
      for (i = 0; i < NS; i++) { b1 += y[i] * Math.sin(2.0 * PI * (i + 0.5) / NS); ms += y[i] * y[i]; }
      b1 = 2.0 * b1 / NS; ms = ms / NS;
      thd = b1 > 0 ? Math.sqrt(Math.max(0.0, 2.0 * ms / (b1 * b1) - 1.0)) : 0.0;
      return { Vop: maxOf(y), b1: b1, rms: Math.sqrt(ms), thd: thd, Pout: ms / p.RL };
    },
    view: function (s, p) { var a = u8_pp.analyse(p); return { t: s.t || 0.0, Vop: a.Vop, thd_pct: a.thd * 100.0 }; },
    measure: function (p) { return u8_pp.analyse(p); }
  });
  function pp_thd(p) {
    var vp = p.Vp, vg = u8_pp.dz(p), d = vg / vp, t0 = Math.asin(d), c = Math.cos(t0);
    var b1 = vp / PI * (PI - 2.0 * t0 - 2.0 * d * c);
    var ms = (vp * vp * ((PI - 2.0 * t0) / 2.0 + d * c) - 4.0 * vp * vg * c + vg * vg * (PI - 2.0 * t0)) / PI;
    return Math.sqrt(Math.max(0.0, 2.0 * ms / (b1 * b1) - 1.0));
  }

  // ===================================================================================== op-amp frequency response
  var u8_opa = stat({
    PARAMS: { A0: 2.0e5, fa: 5.0, R1: 1000.0, Rf: 10000.0, cfg: 0.0, f: 1000.0, Vin: 0.01 },
    VARS: ['t', 'gain', 'ph'],
    h: function (p, f) {
      var a = cdiv([p.A0, 0.0], [1.0, f / p.fa]), b = p.R1 / (p.R1 + p.Rf), cl = cdiv(a, [1.0 + a[0] * b, a[1] * b]), k;
      if (Math.round(p.cfg) === 0) { k = -p.Rf / (p.R1 + p.Rf); return [cl[0] * k, cl[1] * k]; }
      return cl;
    },
    gain: function (p, f) { return cabs(u8_opa.h(p, f)); },
    f3: function (p) {
      var t = u8_opa.gain(p, 1.0e-3) / Math.sqrt(2.0);
      return Math.pow(10.0, bis(function (x) { return u8_opa.gain(p, Math.pow(10.0, x)) - t; }, -1.0, 9.0, 80));
    },
    view: function (s, p) { var hh = u8_opa.h(p, p.f); return { t: s.t || 0.0, gain: cabs(hh), ph: deg(Math.atan2(hh[1], hh[0])) }; },
    measure: function (p) {
      var f3 = u8_opa.f3(p), hh = u8_opa.h(p, p.f);
      return { G0: u8_opa.gain(p, 1.0e-3), f3: f3, gbw: f3 * (1.0 + p.Rf / p.R1), gain: cabs(hh), ph: deg(Math.atan2(hh[1], hh[0])) };
    }
  });
  function opa_gbw(p) { return p.A0 * p.fa; }

  // ===================================================================================== difference amplifier
  var u8_diff = stat({
    PARAMS: { R1: 10000.0, R2: 100000.0, R3: 10000.0, R4: 100000.0, eps: 0.004, A0: 2.0e5, Vd: 0.1, Vc: 1.0, mode: 0.0 },
    VARS: ['t', 'Vout'],
    out: function (p, v1, v2) {
      var r4 = p.R4 * (1.0 + p.eps), b = p.R1 / (p.R1 + p.R2);
      return p.A0 * (v2 * r4 / (p.R3 + r4) - v1 * p.R2 / (p.R1 + p.R2)) / (1.0 + p.A0 * b);
    },
    gains: function (p) {
      var ad = (u8_diff.out(p, -0.5 * p.Vd, 0.5 * p.Vd)) / p.Vd, acm = u8_diff.out(p, p.Vc, p.Vc) / p.Vc, cm = acm !== 0 ? Math.abs(ad / acm) : 0.0;
      return { Ad: ad, Acm: acm, cmrr: cm, cmrr_db: cm > 0 ? 20.0 * Math.log10(cm) : 0.0 };
    },
    view: function (s, p) {
      var v = Math.round(p.mode) === 0 ? u8_diff.out(p, -0.5 * p.Vd, 0.5 * p.Vd) : u8_diff.out(p, p.Vc, p.Vc);
      return { t: s.t || 0.0, Vout: v };
    },
    measure: function (p) { return u8_diff.gains(p); }
  });
  function diff_acm(p) { var r4 = p.R4 * (1.0 + p.eps); return r4 / (p.R3 + r4) * (1.0 + p.R2 / p.R1) - p.R2 / p.R1; }

  // ===================================================================================== analog computer
  var u8_acomp = stat({
    PARAMS: { cfg: 2.0, R: 100000.0, C: 1.0e-7, a1: 2.0, b1: 1.0, c1: 5.0, a2: 1.0, b2: 3.0, c2: 10.0, V0: 5.0, z: 0.2 },
    VARS: ['t', 'rc'],
    simul: function (p, keep) {
      var rc = p.R * p.C, dt = rc / 50.0, x = 0.0, y = 0.0, i, k1, k2, k3, k4, xs = [], ys = [];
      function d(x, y) { return [(p.c1 - p.a1 * x - p.b1 * y) / rc, (p.c2 - p.a2 * x - p.b2 * y) / rc]; }
      for (i = 0; i < 1500; i++) {
        if (keep) { xs.push(x); ys.push(y); }
        k1 = d(x, y); k2 = d(x + 0.5 * dt * k1[0], y + 0.5 * dt * k1[1]); k3 = d(x + 0.5 * dt * k2[0], y + 0.5 * dt * k2[1]); k4 = d(x + dt * k3[0], y + dt * k3[1]);
        x += dt / 6.0 * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0]);
        y += dt / 6.0 * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1]);
      }
      return keep ? [x, y, xs, ys, dt] : [x, y];
    },
    first: function (p) {
      var rc = p.R * p.C, dt = 5.0 * rc / NS, v = p.V0, ys = [], i, k1, k2, k3, k4, c;
      for (i = 0; i < NS; i++) {
        ys.push(v);
        k1 = -v / rc; k2 = -(v + 0.5 * dt * k1) / rc; k3 = -(v + 0.5 * dt * k2) / rc; k4 = -(v + dt * k3) / rc;
        v += dt / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4);
      }
      c = cross(ys, dt, p.V0 / Math.E, false);
      return [ys, dt, c.length ? c[0] : 0.0];
    },
    second: function (p) {
      var w = 1.0 / (p.R * p.C), dt = 3.0 * (2.0 * PI / w) / NS, x = p.V0, v = 0.0, ys = [], z = p.z, i, k1x, k1v, k2x, k2v, k3x, k3v, k4x, k4v, dn;
      function a(x, v) { return -2.0 * z * w * v - w * w * x; }
      for (i = 0; i < NS; i++) {
        ys.push(x);
        k1x = v; k1v = a(x, v);
        k2x = v + 0.5 * dt * k1v; k2v = a(x + 0.5 * dt * k1x, v + 0.5 * dt * k1v);
        k3x = v + 0.5 * dt * k2v; k3v = a(x + 0.5 * dt * k2x, v + 0.5 * dt * k2v);
        k4x = v + dt * k3v; k4v = a(x + dt * k3x, v + dt * k3v);
        x += dt / 6.0 * (k1x + 2.0 * k2x + 2.0 * k3x + k4x);
        v += dt / 6.0 * (k1v + 2.0 * k2v + 2.0 * k3v + k4v);
      }
      dn = cross(ys, dt, 0.0, false);
      return [ys, dt, dn.length >= 2 ? 1.0 / (dn[1] - dn[0]) : 0.0];
    },
    view: function (s, p) { return { t: s.t || 0.0, rc: p.R * p.C }; },
    measure: function (p) {
      var a = u8_acomp.simul(p), b = u8_acomp.first(p), c = u8_acomp.second(p);
      return { x: a[0], y: a[1], tau: b[2], fd: c[2] };
    }
  });
  function acomp_fd(p) { return Math.sqrt(1.0 - p.z * p.z) / (2.0 * PI * p.R * p.C); }
  function acomp_x(p) { return (p.c1 * p.b2 - p.b1 * p.c2) / (p.a1 * p.b2 - p.b1 * p.a2); }

  // ===================================================================================== active filters
  var u8_filt = stat({
    PARAMS: { kind: 0.0, R: 10000.0, C: 1.0e-8, K: 1.586, Q: 2.0, f: 1000.0 },
    VARS: ['t', 'gain', 'f0'],
    f0: function (p) { return 1.0 / (2.0 * PI * p.R * p.C); },
    q: function (p) { return Math.round(p.kind) <= 1 ? 1.0 / (3.0 - p.K) : p.Q; },
    h: function (p, f) {
      var x = f / u8_filt.f0(p), k = Math.round(p.kind), d = [1.0 - x * x, x / u8_filt.q(p)], num;
      if (k === 0) num = [p.K, 0.0];
      else if (k === 1) num = [-p.K * x * x, 0.0];
      else if (k === 2) num = [0.0, x / u8_filt.q(p)];
      else num = [1.0 - x * x, 0.0];
      return cdiv(num, d);
    },
    ref: function (p) { return Math.round(p.kind) <= 1 ? p.K : 1.0; },
    edges: function (p) {
      var f0 = u8_filt.f0(p), t = u8_filt.ref(p) / Math.sqrt(2.0), k = Math.round(p.kind), lf0 = Math.log10(f0);
      function g(x) { return cabs(u8_filt.h(p, Math.pow(10.0, x))) - t; }
      if (k <= 1) return [Math.pow(10.0, bis(g, lf0 - 2.0, lf0 + 2.0, 80)), 0.0];
      return [Math.pow(10.0, bis(g, lf0 - 2.0, lf0, 80)), Math.pow(10.0, bis(g, lf0, lf0 + 2.0, 80))];
    },
    view: function (s, p) { return { t: s.t || 0.0, gain: cabs(u8_filt.h(p, p.f)), f0: u8_filt.f0(p) }; },
    measure: function (p) {
      var e = u8_filt.edges(p), hh = u8_filt.h(p, p.f);
      return { fc: e[0], fc2: e[1], f0: u8_filt.f0(p), gain: cabs(hh), ph: deg(Math.atan2(hh[1], hh[0])) };
    }
  });
  function filt_fc(p) {
    var f0 = 1.0 / (2.0 * PI * p.R * p.C), k = Math.round(p.kind), q, a, u;
    if (k <= 1) {
      q = 1.0 / (3.0 - p.K); a = 2.0 - 1.0 / (q * q); u = (a + Math.sqrt(a * a + 4.0)) / 2.0;
      return k === 0 ? f0 * Math.sqrt(u) : f0 / Math.sqrt(u);
    }
    q = p.Q;
    return f0 * (Math.sqrt(1.0 + 1.0 / (4.0 * q * q)) - 1.0 / (2.0 * q));
  }

  // ===================================================================================== JFET common source
  var u8_jfet = stat({
    PARAMS: { Vdd: 15.0, Idss: 0.010, Vp: -4.0, Rs: 680.0, Rd: 2200.0, RL: 10000.0, Rg: 1.0e6, Rsig: 10000.0, Cin: 1.0e-7, Cout: 1.0e-6, Cs: 2.2e-5, Cgs: 4.0e-12, Cgd: 1.0e-12, f: 10000.0 },
    VARS: ['t', 'Id_mA', 'Vgs', 'Vds', 'gm_mS'],
    bias: function (p) {
      var a = Math.abs(p.Vp), hi = Math.min(p.Idss, a / p.Rs);
      var idd = bis(function (i) { return p.Idss * Math.pow(1.0 - i * p.Rs / a, 2) - i; }, 0.0, hi, 100);
      return [idd, 2.0 * Math.sqrt(idd * p.Idss) / a];
    },
    h: function (p, f) {
      var b = u8_jfet.bias(p), gm = b[1], rl = p.Rd * p.RL / (p.Rd + p.RL), am = gm * rl * p.Rg / (p.Rg + p.Rsig);
      var f1 = 1.0 / (2.0 * PI * (p.Rsig + p.Rg) * p.Cin), f2 = 1.0 / (2.0 * PI * (p.Rd + p.RL) * p.Cout);
      var fz = 1.0 / (2.0 * PI * p.Rs * p.Cs), fp = (1.0 + gm * p.Rs) * fz, rp = p.Rsig * p.Rg / (p.Rsig + p.Rg);
      var fh = 1.0 / (2.0 * PI * rp * (p.Cgs + p.Cgd * (1.0 + gm * rl)));
      var hh = [-am, 0.0];
      hh = cmul(hh, cdiv([0.0, f / f1], [1.0, f / f1]));
      hh = cmul(hh, cdiv([0.0, f / f2], [1.0, f / f2]));
      hh = cmul(hh, cdiv([1.0, f / fz], [1.0 + gm * p.Rs, (1.0 + gm * p.Rs) * f / fp]));
      hh = cdiv(hh, [1.0, f / fh]);
      return hh;
    },
    gain: function (p, f) { return cabs(u8_jfet.h(p, f)); },
    scan: function (p) {
      var best = 0.0, lb = 0.0, i, lf, g, t;
      for (i = 0; i < 321; i++) { lf = 8.0 * i / 320.0; g = u8_jfet.gain(p, Math.pow(10.0, lf)); if (g > best) { best = g; lb = lf; } }
      t = best / Math.sqrt(2.0);
      function e(x) { return u8_jfet.gain(p, Math.pow(10.0, x)) - t; }
      return { Amid: best, fL: Math.pow(10.0, bis(e, 0.0, lb, 80)), fH: Math.pow(10.0, bis(e, lb, 8.0, 80)) };
    },
    view: function (s, p) { var b = u8_jfet.bias(p); return { t: s.t || 0.0, Id_mA: b[0] * 1000.0, Vgs: -b[0] * p.Rs, Vds: p.Vdd - b[0] * (p.Rd + p.Rs), gm_mS: b[1] * 1000.0 }; },
    measure: function (p) {
      var m = u8_jfet.scan(p), b = u8_jfet.bias(p), hh = u8_jfet.h(p, p.f);
      m.Id = b[0]; m.gm = b[1]; m.A = cabs(hh); m.ph = deg(Math.atan2(hh[1], hh[0]));
      return m;
    }
  });
  function jfet_amid(p) {
    var a = Math.abs(p.Vp), k = p.Rs / a, aa = p.Idss * k * k, bb = -(2.0 * p.Idss * k + 1.0);
    var idd = (-bb - Math.sqrt(bb * bb - 4.0 * aa * p.Idss)) / (2.0 * aa), gm = 2.0 * p.Idss / a * (1.0 - idd * p.Rs / a);
    return gm * (p.Rd * p.RL / (p.Rd + p.RL)) * p.Rg / (p.Rg + p.Rsig);
  }

  // ===================================================================================== R-2R DAC
  var u8_dac = stat({
    PARAMS: { D: 9.0, Vref: 5.0, R: 10000.0, Rf: 6200.0, Rg: 10000.0 },
    VARS: ['t', 'Vout'],
    node: function (p, code) {
      var n = 4, r = p.R, g2 = 1.0 / (2.0 * r), g1 = 1.0 / r, a = [], b = [], c = [], d = [], k, bit, diag, m;
      for (k = 0; k < n; k++) {
        bit = (code >> k) & 1;
        diag = g2 + (k === 0 ? g2 : g1) + (k < n - 1 ? g1 : 0.0);
        a.push(k > 0 ? -g1 : 0.0); b.push(diag); c.push(k < n - 1 ? -g1 : 0.0); d.push(g2 * p.Vref * bit);
      }
      for (k = 1; k < n; k++) { m = a[k] / b[k - 1]; b[k] -= m * c[k - 1]; d[k] -= m * d[k - 1]; }
      return d[n - 1] / b[n - 1];
    },
    vout: function (p, code) { return u8_dac.node(p, code) * (1.0 + p.Rf / p.Rg); },
    view: function (s, p) { return { t: s.t || 0.0, Vout: u8_dac.vout(p, Math.round(p.D)) }; },
    measure: function (p) { var fs = u8_dac.vout(p, 15); return { Vout: u8_dac.vout(p, Math.round(p.D)), lsb: (fs - u8_dac.vout(p, 0)) / 15.0, fs: fs }; }
  });
  function dac_v(p) { return p.Vref * (1.0 + p.Rf / p.Rg) * Math.round(p.D) / 16.0; }

  // ===================================================================================== SAR ADC
  var u8_adc = stat({
    PARAMS: { Vin: 2.0, Vref: 5.0 },
    VARS: ['t', 'code'],
    code: function (p, vin) {
      var lsb = p.Vref / 256.0, c = 0, b, trial;
      for (b = 7; b >= 0; b--) { trial = c | (1 << b); if (vin >= (trial - 0.5) * lsb) c = trial; }
      return c;
    },
    view: function (s, p) { return { t: s.t || 0.0, code: u8_adc.code(p, p.Vin) }; },
    measure: function (p) { return { code: u8_adc.code(p, p.Vin), lsb: p.Vref / 256.0 }; }
  });
  function adc_code(p) { return Math.max(0, Math.min(255, Math.floor(p.Vin / (p.Vref / 256.0) + 0.5))); }

  // ===================================================================================== sample and hold
  var u8_sh = stat({
    PARAMS: { Vs: 2.0, Rsrc: 1000.0, Ron: 125.0, Ch: 1.0e-8, Ileak: 1.0e-9 },
    VARS: ['t', 'tau_us'],
    trace: function (p) {
      var tau = (p.Rsrc + p.Ron) * p.Ch, span = 10.0 * tau, dt = span / NS, e = Math.exp(-dt / tau), sw = [], vc = [], v = 0.0, i, t, on;
      for (i = 0; i < NS; i++) {
        t = i * dt; on = t < 6.0 * tau ? 1.0 : 0.0;
        sw.push(5.0 * on); vc.push(v);
        if (on > 0) v = p.Vs + (v - p.Vs) * e; else v -= p.Ileak / p.Ch * dt;
      }
      return [sw, vc, dt];
    },
    analyse: function (p) {
      var tr = u8_sh.trace(p), vc = tr[1], dt = tr[2], a = cross(vc, dt, 0.1 * p.Vs, true), b = cross(vc, dt, 0.9 * p.Vs, true);
      var tacq = a.length && b.length ? b[0] - a[0] : 0.0, k1 = Math.floor(7.0 / 10.0 * NS), k2 = Math.floor(9.5 / 10.0 * NS);
      return { tacq: tacq, tau: tacq / Math.log(9.0), droop: (vc[k1] - vc[k2]) / ((k2 - k1) * dt) };
    },
    view: function (s, p) { return { t: s.t || 0.0, tau_us: (p.Rsrc + p.Ron) * p.Ch * 1e6 }; },
    measure: function (p) { return u8_sh.analyse(p); }
  });
  function sh_tau(p) { return (p.Rsrc + p.Ron) * p.Ch; }

  // ===================================================================================== 7805 supply
  var u8_reg = stat({
    PARAMS: { Vsec: 15.0, f: 50.0, Cf: 2.2e-3, Io: 0.5, Iq: 0.005, Vf: 0.85, Vnom: 5.0, kl: 1.7e-4, Ro: 0.01, Vdo: 2.0 },
    VARS: ['t', 'Vin', 'Vout'],
    run: function (p, vsec, io, keep) {
      var vm = Math.sqrt(2.0) * vsec - 2.0 * p.Vf, w = 2.0 * PI * p.f, th = 0.5 / p.f, it = io + p.Iq, si = 0.0, so = 0.0;
      var vmin = 1e9, vmax = -1e9, omin = 1e9, omax = -1e9, i, t, vin, vo, ins = [], outs = [];
      for (i = 0; i < NS; i++) {
        t = (i + 0.5) / NS * th;
        vin = Math.max(vm - it * t / p.Cf, vm * Math.abs(Math.cos(w * t)));
        vo = Math.min(p.Vnom + p.kl * (vin - 10.0) - p.Ro * io, vin - p.Vdo);
        si += vin; so += vo;
        vmin = Math.min(vmin, vin); vmax = Math.max(vmax, vin); omin = Math.min(omin, vo); omax = Math.max(omax, vo);
        if (keep) { ins.push(vin); outs.push(vo); }
      }
      var r = { Vin: si / NS, Vout: so / NS, Vmin: vmin, rin: vmax - vmin, rout: omax - omin };
      if (keep) { r.ins = ins; r.outs = outs; r.dt = th / NS; }
      return r;
    },
    view: function (s, p) { var r = u8_reg.run(p, p.Vsec, p.Io); return { t: s.t || 0.0, Vin: r.Vin, Vout: r.Vout }; },
    measure: function (p) {
      var R = u8_reg.run, r = R(p, p.Vsec, p.Io), a = R(p, p.Vsec - 1.0, p.Io), b = R(p, p.Vsec + 1.0, p.Io), c = R(p, p.Vsec, p.Io - 0.1), d = R(p, p.Vsec, p.Io + 0.1);
      r.line = (b.Vout - a.Vout) / (b.Vin - a.Vin);
      r.Rout = (c.Vout - d.Vout) / 0.2;
      return r;
    }
  });
  function reg_line(p) { return p.kl; }

  // ===================================================================================== PLL
  var u8_pll = stat({
    PARAMS: { R1: 6800.0, C1: 1.0e-8, C2: 1.0e-6, V: 10.0, fin: 4500.0, mode: 0.0 },
    VARS: ['t', 'f0'],
    f0: function (p) { return 0.3 / (p.R1 * p.C1); },
    run: function (p, df, th, vc, nTau) {
      var kf = 8.0 * u8_pll.f0(p) / p.V, tau = 3600.0 * p.C2, dt = 1.0 / (40.0 * kf), n = Math.floor(nTau * tau / dt), w = 2.0 * PI, i, k1, k2, k3, k4;
      var tail = Math.floor(n * 0.6), tha = th;
      function d(th, vc) { return [w * (df - kf * vc), (Math.sin(th) - vc) / tau]; }
      for (i = 0; i < n; i++) {
        k1 = d(th, vc); k2 = d(th + 0.5 * dt * k1[0], vc + 0.5 * dt * k1[1]); k3 = d(th + 0.5 * dt * k2[0], vc + 0.5 * dt * k2[1]); k4 = d(th + dt * k3[0], vc + dt * k3[1]);
        th += dt / 6.0 * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0]);
        vc += dt / 6.0 * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1]);
        if (i === tail) tha = th;
      }
      return Math.abs(th - tha) < 0.25 * PI;
    },
    locked: function (p, df, mode) {
      var kf = 8.0 * u8_pll.f0(p) / p.V, s;
      if (mode === 0) {
        s = (Math.abs(df) - 0.002 * kf) / kf;
        s = Math.max(0.0, Math.min(0.999, s)) * (df >= 0 ? 1.0 : -1.0);
        return u8_pll.run(p, df, Math.asin(s), s, 12.0);
      }
      return u8_pll.run(p, df, 0.0, 0.0, 60.0);
    },
    edge: function (p, mode) {
      var kf = 8.0 * u8_pll.f0(p) / p.V, lo = 0.0, hi = 1.5 * kf, i, mid;
      for (i = 0; i < 14; i++) { mid = 0.5 * (lo + hi); if (u8_pll.locked(p, mid, mode)) lo = mid; else hi = mid; }
      return 0.5 * (lo + hi);
    },
    view: function (s, p) { return { t: s.t || 0.0, f0: u8_pll.f0(p) }; },
    measure: function (p) { return { f0: u8_pll.f0(p), lock: u8_pll.edge(p, 0), capture: u8_pll.edge(p, 1) }; }
  });
  function pll_lock(p) { return 8.0 * (0.3 / (p.R1 * p.C1)) / p.V; }
  function pll_capture(p) { var fl = pll_lock(p); return Math.sqrt(2.0 * PI * fl / (3600.0 * p.C2)) / (2.0 * PI); }

  // ===================================================================================== universal counter
  var u8_count = stat({
    PARAMS: { f: 1234.5678, ph: 0.37, ps: 0.61, fclk: 1.0e7, Tg: 1.0, Np: 1.0 },
    VARS: ['t', 'f'],
    freq: function (p, tg) { var n = Math.floor(p.f * tg + p.ph) - Math.floor(p.ph); return [n / tg, n]; },
    period: function (p, np) { var m = Math.floor(p.fclk * np / p.f + p.ps) - Math.floor(p.ps); return [m / (p.fclk * np), m]; },
    view: function (s, p) { return { t: s.t || 0.0, f: u8_count.freq(p, p.Tg)[0] }; },
    measure: function (p) {
      var a = u8_count.freq(p, p.Tg), b = u8_count.period(p, p.Np);
      return { fF: a[0], N: a[1], Tp: b[0], M: b[1], f1: u8_count.freq(p, 1.0)[0] };
    }
  });
  function count_f(p) { return p.f; }

  // ===================================================================================== distortion factor meter
  var u8_dfm = stat({
    PARAMS: { V1: 1.0, h2: 0.03, h3: 0.02, h4: 0.005, h5: 0.004, f0: 100000.0, Q: 10.0, fn: 100000.0 },
    VARS: ['t', 'D_pct'],
    rms: function (p, fn, notch) {
      var amp = [p.V1, p.V1 * p.h2, p.V1 * p.h3, p.V1 * p.h4, p.V1 * p.h5], mag = [], ph = [], n, x, hh, s = 0.0, i, k, th, v;
      for (n = 1; n < 6; n++) {
        if (notch) { x = n * p.f0 / fn; hh = cdiv([1.0 - x * x, 0.0], [1.0 - x * x, x / p.Q]); mag.push(cabs(hh)); ph.push(Math.atan2(hh[1], hh[0])); }
        else { mag.push(1.0); ph.push(0.0); }
      }
      for (i = 0; i < NS; i++) {
        th = 4.0 * PI * (i + 0.5) / NS; v = 0.0;
        for (k = 0; k < 5; k++) v += amp[k] * mag[k] * Math.sin((k + 1) * th + ph[k]);
        s += v * v;
      }
      return Math.sqrt(s / NS);
    },
    view: function (s, p) { return { t: s.t || 0.0, D_pct: 100.0 * u8_dfm.rms(p, p.fn, true) / u8_dfm.rms(p, p.fn, false) }; },
    measure: function (p) {
      var tot = u8_dfm.rms(p, p.fn, false), res = u8_dfm.rms(p, p.fn, true), best = u8_dfm.rms(p, p.f0, true);
      return { Vtot: tot, Vres: res, D: res / tot, Dbest: best / tot };
    }
  });
  function dfm_d(p) { var hs = Math.pow(p.h2, 2) + Math.pow(p.h3, 2) + Math.pow(p.h4, 2) + Math.pow(p.h5, 2); return Math.sqrt(hs) / Math.sqrt(1.0 + hs); }

  // ===================================================================================== thermostat
  var u8_tstat = stat({
    PARAMS: { D: 50.0, a: 1.5, b: 0.97, H: 3.0, P: 500.0, hA: 10.0, Cth: 4186.0, Ta: 25.0 },
    VARS: ['t', 'Tset'],
    DT: 0.5,
    run: function (p, keep) {
      var ts = p.a + p.b * p.D, ton = ts - 0.5 * p.H, toff = ts + 0.5 * p.H, tinf = p.Ta + p.P / p.hA, tau = p.Cth / p.hA, DT = 0.5;
      var e = Math.exp(-DT / tau), t = 0.0, temp = p.Ta, heat = true, ev = [], i, tgt, nt, thr, tc, tt = [], hh = [];
      for (i = 0; i < 40000; i++) {
        if (keep) { tt.push(temp); hh.push(heat ? 1 : 0); }
        tgt = heat ? tinf : p.Ta;
        nt = tgt + (temp - tgt) * e;
        thr = heat ? toff : ton;
        if ((heat && nt >= thr) || (!heat && nt <= thr)) {
          tc = -tau * Math.log((thr - tgt) / (temp - tgt));
          ev.push([t + tc, thr, heat ? 0 : 1]);
          heat = !heat;
          tgt = heat ? tinf : p.Ta;
          nt = tgt + (thr - tgt) * Math.exp(-(DT - tc) / tau);
        }
        temp = nt; t += DT;
        if (ev.length >= 5) break;
      }
      var out = { Ton: ton, Toff: toff, theat: 0.0, tcool: 0.0, ev: ev };
      if (ev.length >= 4) { out.tcool = ev[1][0] - ev[0][0]; out.theat = ev[2][0] - ev[1][0]; }
      if (keep) { out.temps = tt; out.heats = hh; out.dt = DT; }
      return out;
    },
    view: function (s, p) { return { t: s.t || 0.0, Tset: p.a + p.b * p.D }; },
    measure: function (p) { var r = u8_tstat.run(p); return { Ton: r.Ton, Toff: r.Toff, theat: r.theat, tcool: r.tcool }; }
  });
  function tstat_theat(p) {
    var ts = p.a + p.b * p.D, ton = ts - 0.5 * p.H, toff = ts + 0.5 * p.H, tinf = p.Ta + p.P / p.hA;
    return p.Cth / p.hA * Math.log((tinf - ton) / (tinf - toff));
  }

  // ===================================================================================== cable noise pick-up
  var u8_noise = stat({
    PARAMS: { V1: 10.0, f: 10000.0, R: 10000.0, C12: 5.0e-12, C2g: 1.0e-10, k: 1.0, sg: 1.0 },
    VARS: ['t', 'VN_mV'],
    ceff: function (p) { return p.C12 * (Math.round(p.sg) === 1 ? p.k : 1.0); },
    hv: function (p) { var w = 2.0 * PI * p.f, c = u8_noise.ceff(p); return cdiv([0.0, w * p.R * c * p.V1], [1.0, w * p.R * (c + p.C2g)]); },
    wave: function (p) {
      var hh = u8_noise.hv(p), a = cabs(hh), ph = Math.atan2(hh[1], hh[0]), dt = 3.0 / p.f / NS, src = [], vn = [], i, th;
      for (i = 0; i < NS; i++) { th = 2.0 * PI * p.f * i * dt; src.push(p.V1 * Math.sin(th)); vn.push(a * Math.sin(th + ph)); }
      return [src, vn, dt];
    },
    view: function (s, p) { return { t: s.t || 0.0, VN_mV: cabs(u8_noise.hv(p)) * 1000.0 }; },
    measure: function (p) { var w = u8_noise.wave(p); return { VN: 0.5 * (maxOf(w[1]) - minOf(w[1])), Ceff: u8_noise.ceff(p) }; }
  });
  function noise_vn(p) {
    var w = 2.0 * PI * p.f, c = p.C12 * (Math.round(p.sg) === 1 ? p.k : 1.0);
    return w * p.R * c * p.V1 / Math.sqrt(1.0 + Math.pow(w * p.R * (c + p.C2g), 2));
  }

  H.register({
    K: { u8_diode: u8_diode, u8_tunnel: u8_tunnel, u8_bjt: u8_bjt, u8_pp: u8_pp, u8_opa: u8_opa, u8_diff: u8_diff, u8_acomp: u8_acomp,
      u8_filt: u8_filt, u8_jfet: u8_jfet, u8_dac: u8_dac, u8_adc: u8_adc, u8_sh: u8_sh, u8_reg: u8_reg, u8_pll: u8_pll, u8_count: u8_count,
      u8_dfm: u8_dfm, u8_tstat: u8_tstat, u8_noise: u8_noise },
    TEXTBOOK: { u8_diode_vcut: diode_vcut, u8_diode_kb: diode_kb, u8_tunnel_ip: tunnel_ip, u8_bjt_hfe: bjt_hfe, u8_bjt_vth: bjt_vth,
      u8_pp_thd: pp_thd, u8_opa_gbw: opa_gbw, u8_diff_acm: diff_acm, u8_acomp_fd: acomp_fd, u8_acomp_x: acomp_x, u8_filt_fc: filt_fc,
      u8_jfet_amid: jfet_amid, u8_dac_v: dac_v, u8_adc_code: adc_code, u8_sh_tau: sh_tau, u8_reg_line: reg_line, u8_pll_lock: pll_lock,
      u8_pll_capture: pll_capture, u8_count_f: count_f, u8_dfm_d: dfm_d, u8_tstat_theat: tstat_theat, u8_noise_vn: noise_vn },
    CALCS: {}
  });
})(typeof window !== 'undefined' ? window : this);
