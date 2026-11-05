/* Kernel pack `phd_cond`: exact JavaScript twin of app/prayog/packs/phd_cond.py - research-level condensed matter:
   low temperature and superconductivity, quantum transport, magnetic resonance and hyperfine methods. Same formulas,
   same algorithms, same numbers (the server tests run both and compare to 1e-9). SQUIDs, the dilution refrigerator
   free quantities, the Josephson junction, the quantum Hall sample, the tunnel junction and the Moessbauer
   spectrometer are SIMULATED INSTRUMENTS: published models, not devices. Noise is a hash of the `seed` parameter. */
(function (root) {
  'use strict';
  var H0 = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, H = 6.62607015e-34, HBAR = H / (2 * PI), QE = 1.602176634e-19, KB = 1.380649e-23, MUB = 9.2740100783e-24,
    MUN = 5.0507837461e-27, ME = 9.1093837015e-31, MU0 = 1.25663706212e-6, CLIGHT = 299792458.0, PHI0 = H / (2 * QE), RK = H / (QE * QE);

  function hash(seed, k) { var x = Math.sin(seed * 12.9898 + k * 78.233) * 43758.5453; return 2.0 * (x - Math.floor(x)) - 1.0; }
  function line(pts) {
    var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, d, m;
    if (n < 2) return [0, 0];
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    d = n * sxx - sx * sx;
    if (d === 0) return [0, 0];
    m = (n * sxy - sx * sy) / d;
    return [m, (sy - m * sx) / n];
  }
  function rws(rows, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rows || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) { v = rows[i][keys[j]];
        if (v === undefined || v === null || v === '' || !isFinite(+v)) { ok = false; break; } vals.push(+v); }
      if (ok) out.push(vals);
    }
    return out;
  }
  function cp(p) { var q = {}, k; for (k in p) q[k] = p[k]; return q; }
  function init() { return { t: 0 }; }
  function step(s, p, dt) { s.t += dt; }
  function tOf(s) { return s.t || 0; }
  function sech2(x) { var e = Math.exp(-2.0 * Math.abs(x)); return 4.0 * e / ((1.0 + e) * (1.0 + e)); }
  function digamma(x) {
    var r = 0.0, x2;
    while (x < 8.0) { r -= 1.0 / x; x += 1.0; }
    x2 = 1.0 / (x * x);
    return r + Math.log(x) - 0.5 / x - x2 * (1.0 / 12 - x2 * (1.0 / 120 - x2 * (1.0 / 252 - x2 * (1.0 / 240))));
  }
  var GR = (Math.sqrt(5.0) - 1.0) / 2.0;

  // ------------------------------------------------------------ superconductor R(T)
  var scrt = {
    PARAMS: { T: 100.0, B: 0.0, Tc0: 92.0, Bc2: 120.0, w: 0.6, Rres: 0.02, a: 0.0004, I: 0.001 }, VARS: ['t', 'R', 'V', 'T'], init: init, step: step,
    tc: function (p) { return p.Tc0 * (1.0 - Math.pow(p.B / p.Bc2, 2)); },
    rn: function (p, T) { return p.Rres + p.a * T; },
    res: function (p, T) { if (T === undefined) T = p.T; return scrt.rn(p, T) * 0.5 * (1.0 + Math.tanh((T - scrt.tc(p)) / p.w)); },
    view: function (s, p) { var r = scrt.res(p); return { t: tOf(s), R: r, V: r * p.I, T: p.T }; },
    measure: function (p) {
      var lo = 1.0, hi = 3.0 * p.Tc0, mid, i, t1, t2, r1, r2, m, r0;
      for (i = 0; i < 80; i++) { mid = 0.5 * (lo + hi); if (scrt.res(p, mid) / scrt.rn(p, mid) < 0.5) lo = mid; else hi = mid; }
      t1 = hi + 20 * p.w + 5.0; t2 = hi + 20 * p.w + 55.0;
      r1 = scrt.res(p, t1); r2 = scrt.res(p, t2); m = (r2 - r1) / (t2 - t1); r0 = r1 - m * t1;
      return { Tc: 0.5 * (lo + hi), RRR: r0 > 0 ? scrt.res(p, 300.0) / r0 : 0.0, R: scrt.res(p) };
    }
  };
  function scrt_Tc(p) { return scrt.tc(p); }

  // ------------------------------------------------------------ critical current
  var scic = {
    PARAMS: { I: 0.5, T: 20.0, B: 0.0, Tc: 92.0, Ic0: 2.0, B0: 1.0, n: 15.0, Lv: 0.002, Ec: 1e-4, area: 1.0e-9 }, VARS: ['t', 'V', 'I', 'Ic'], init: init, step: step,
    ic: function (p) { var t = p.T / p.Tc; return t >= 1 ? 0.0 : p.Ic0 * Math.pow(1.0 - t * t, 1.5) / (1.0 + p.B / p.B0); },
    volts: function (p, I) { if (I === undefined) I = p.I; var ic = scic.ic(p); return (ic <= 0 || I <= 0) ? 0.0 : p.Ec * p.Lv * Math.pow(I / ic, p.n); },
    view: function (s, p) { return { t: tOf(s), V: scic.volts(p), I: p.I, Ic: scic.ic(p) }; },
    measure: function (p) {
      var vc = p.Ec * p.Lv, lo = 0.0, hi = 10.0 * Math.max(scic.ic(p), 1e-12), mid, i, ic;
      for (i = 0; i < 100; i++) { mid = 0.5 * (lo + hi); if (scic.volts(p, mid) < vc) lo = mid; else hi = mid; }
      ic = 0.5 * (lo + hi);
      return { Ic: ic, Jc: ic / p.area, V: scic.volts(p) };
    }
  };
  function scic_Ic(p) { return scic.ic(p); }

  // ------------------------------------------------------------ AC susceptibility
  var acs = {
    PARAMS: { T: 50.0, Tc: 92.0, w: 0.5, a: 1.0e-6, ns: 2.0e28, chi2: 0.12 }, VARS: ['t', 'chi1', 'chi2', 'T'], init: init, step: step,
    lam0: function (p) { return Math.sqrt(ME / (MU0 * p.ns * QE * QE)); },
    lam: function (p, T) { var t = T / p.Tc; return t < 1 ? acs.lam0(p) / Math.sqrt(1.0 - Math.pow(t, 4)) : 1e30; },
    chi1: function (p, T) { if (T === undefined) T = p.T; var x = Math.min(acs.lam(p, T) / p.a, 1.0), f = 1.0 - Math.pow(1.0 - x, 3); return -f * 0.5 * (1.0 - Math.tanh((T - p.Tc) / p.w)); },
    chi2: function (p, T) { if (T === undefined) T = p.T; return p.chi2 * sech2((T - p.Tc) / p.w); },
    view: function (s, p) { return { t: tOf(s), chi1: acs.chi1(p), chi2: acs.chi2(p), T: p.T }; },
    measure: function (p) {
      var T0 = 0.05 * p.Tc, f = -acs.chi1(p, T0), lam = p.a * (1.0 - Math.pow(1.0 - f, 1.0 / 3.0)), lam0 = lam * Math.sqrt(1.0 - Math.pow(0.05, 4)),
        n = Math.floor(p.Tc * 0.2 / 0.01), best = -1.0, bt = 0.0, t0 = 0.9 * p.Tc, i, t, c, a, b, d, tc;
      for (i = 0; i < 2 * n + 1; i++) { t = t0 + 0.01 * i; c = acs.chi2(p, t); if (c > best) { best = c; bt = t; } }
      a = acs.chi2(p, bt - 0.01); b = best; c = acs.chi2(p, bt + 0.01); d = a - 2 * b + c;
      tc = bt + (d !== 0 ? 0.01 * 0.5 * (a - c) / d : 0.0);
      return { lam0: lam0, Tc: tc, f: f };
    }
  };
  function acs_lam0(p) { return Math.sqrt(ME / (MU0 * p.ns * QE * QE)); }

  // ------------------------------------------------------------ thermometers
  var CVD_A = 3.9083e-3, CVD_B = -5.775e-7, CVD_C = -4.183e-12, DIODE_EG = 1.17;
  var therm = {
    PARAMS: { T: 77.0, sensor: 1.0, I: 1.0e-5, G: 1.0e-3, R0: 100.0, Rinf: 1000.0, T0: 20.0, s0: 40.0e-6, Tk: 60.0, Tref: 300.0 }, VARS: ['t', 'X', 'T', 'dTheat'], init: init, step: step,
    cs: function (p) { var i0 = 1.0e-5, t0 = 300.0, v0 = 0.6; return i0 / Math.pow(t0, 3) * Math.exp(-(v0 - DIODE_EG) * QE / (KB * t0)); },
    bare: function (p, T) {
      var k = Math.round(p.sensor), t, c;
      if (k === 1) return DIODE_EG + (KB * T / QE) * (Math.log(p.I / therm.cs(p)) - 3.0 * Math.log(T));
      if (k === 2) { t = T - 273.15; c = t < 0 ? CVD_C * (t - 100.0) * Math.pow(t, 3) : 0.0; return p.R0 * (1.0 + CVD_A * t + CVD_B * t * t + c); }
      if (k === 3) return p.Rinf * Math.exp(Math.sqrt(p.T0 / T));
      return p.s0 * ((T - p.Tref) - p.Tk * Math.log((T + p.Tk) / (p.Tref + p.Tk)));
    },
    power: function (p, T) { var k = Math.round(p.sensor), x = therm.bare(p, T); if (k === 1) return p.I * x; if (k === 2 || k === 3) return p.I * p.I * x; return 0.0; },
    dtheat: function (p, T) { if (T === undefined) T = p.T; return therm.power(p, T) / p.G; },
    read: function (p, T) { if (T === undefined) T = p.T; return therm.bare(p, T + therm.dtheat(p, T)); },
    slope_exact: function (p, T) {
      var k = Math.round(p.sensor), t, d;
      if (k === 1) return (therm.bare(p, T) - DIODE_EG) / T - 3.0 * KB / QE;
      if (k === 2) { t = T - 273.15; d = CVD_A + 2 * CVD_B * t; if (t < 0) d += CVD_C * (4.0 * Math.pow(t, 3) - 300.0 * Math.pow(t, 2)); return p.R0 * d; }
      if (k === 3) return -therm.bare(p, T) * 0.5 * Math.sqrt(p.T0) / Math.pow(T, 1.5);
      return p.s0 * T / (T + p.Tk);
    },
    view: function (s, p) { return { t: tOf(s), X: therm.read(p), T: p.T, dTheat: therm.dtheat(p) }; },
    measure: function (p) { var a = therm.read(p, p.T - 1.0), b = therm.read(p, p.T + 1.0); return { S: (b - a) / 2.0, X: therm.read(p), dTheat: therm.dtheat(p) }; }
  };
  function therm_S(p) { return therm.slope_exact(p, p.T); }

  // ------------------------------------------------------------ Josephson (RSJ)
  var jj = {
    PARAMS: { I: 0.0, Delta: 1.4e-3, Tb: 4.2, Rn: 2.0, Rs: 0.04, f: 16.0e9, Irf: 4.2e-4, rf: 0.0 }, VARS: ['t', 'V', 'I', 'Ic'], init: init, step: step,
    icrn: function (p) { return PI * p.Delta / 2.0 * Math.tanh(p.Delta * QE / (2.0 * KB * p.Tb)); },
    ic: function (p) { return jj.icrn(p) / p.Rn; },
    omega: function (p) { return H * p.f / (2.0 * QE * jj.ic(p) * p.Rs); },
    volts: function (p, I, rf, nper, skip, spp) {
      var i, irf, om, dt, phi, t, tot, n, k, k1, k2, k3, k4, d, nsteps, per;
      if (I === undefined) I = p.I; if (rf === undefined) rf = p.rf; if (nper === undefined) nper = 40; if (skip === undefined) skip = 30; if (spp === undefined) spp = 40;
      i = I / jj.ic(p); irf = rf > 0.5 ? p.Irf / jj.ic(p) : 0.0; om = jj.omega(p);
      if (irf === 0.0) {
        dt = 0.05; phi = 0.0; n = 0; tot = 0.0; nsteps = 12000;
        for (k = 0; k < nsteps; k++) {
          k1 = i - Math.sin(phi); k2 = i - Math.sin(phi + 0.5 * dt * k1); k3 = i - Math.sin(phi + 0.5 * dt * k2); k4 = i - Math.sin(phi + dt * k3);
          d = dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0; phi += d;
          if (k >= Math.floor(nsteps / 2)) { tot += d; n += 1; }
        }
        return tot / (n * dt) * jj.ic(p) * p.Rs;
      }
      per = 2.0 * PI / om; dt = per / spp; phi = 0.0; t = 0.0; tot = 0.0;
      function fn(tt, ph) { return i + irf * Math.sin(om * tt) - Math.sin(ph); }
      for (k = 0; k < (nper + skip) * spp; k++) {
        k1 = fn(t, phi); k2 = fn(t + 0.5 * dt, phi + 0.5 * dt * k1); k3 = fn(t + 0.5 * dt, phi + 0.5 * dt * k2); k4 = fn(t + dt, phi + dt * k3);
        d = dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0; phi += d; t += dt;
        if (k >= skip * spp) tot += d;
      }
      return tot / (nper * per) * jj.ic(p) * p.Rs;
    },
    view: function (s, p) { return { t: tOf(s), V: jj.volts(p, p.I, p.rf, 4, 4, 20), I: p.I, Ic: jj.ic(p) }; },
    measure: function (p) {
      var ic = jj.ic(p), v1 = jj.volts(p, Math.sqrt(1.0 + Math.pow(jj.omega(p), 2)) * ic, 1.0);
      return { V1: v1, Ic: ic, f: 2.0 * QE * v1 / H };
    }
  };
  function jj_f(p) { return p.f; }

  // ------------------------------------------------------------ DC SQUID
  var sq = {
    PARAMS: { Icoil: 0.0, I0: 10.0e-6, Rn: 4.0, Ib: 24.0e-6, Mi: 2.0e-10, Poff: 0.1, vn: 0.0, seed: 3.0 }, VARS: ['t', 'V', 'Icoil', 'Phi'], init: init, step: step,
    volts: function (p, ic) {
      if (ic === undefined) ic = p.Icoil;
      var phi = p.Mi * ic + p.Poff * PHI0, icr = 2.0 * p.I0 * Math.abs(Math.cos(PI * phi / PHI0));
      return p.Ib > icr ? 0.5 * p.Rn * Math.sqrt(p.Ib * p.Ib - icr * icr) : 0.0;
    },
    noisy: function (p, ic, k) { return sq.volts(p, ic) + p.vn * hash(p.seed, k); },
    view: function (s, p) { return { t: tOf(s), V: sq.volts(p), Icoil: p.Icoil, Phi: (p.Mi * p.Icoil + p.Poff * PHI0) / PHI0 }; },
    measure: function (p) {
      var per0 = PHI0 / p.Mi, n = 800, xs = [], vs = [], i, pk = [], a, b, c, d, per, vmax = -1e300, vmin = 1e300, slope = 0.0, dphi;
      for (i = 0; i <= n; i++) { xs.push((-1.0 + 4.0 * i / n) * per0); vs.push(sq.volts(p, xs[i])); }
      for (i = 1; i < n; i++) {
        if (vs[i] > vs[i - 1] && vs[i] >= vs[i + 1]) { a = vs[i - 1]; b = vs[i]; c = vs[i + 1]; d = a - 2 * b + c; pk.push(xs[i] + (d !== 0 ? (xs[1] - xs[0]) * 0.5 * (a - c) / d : 0.0)); }
      }
      per = pk.length > 1 ? (pk[pk.length - 1] - pk[0]) / (pk.length - 1) : 0.0;
      for (i = 0; i <= n; i++) { if (vs[i] > vmax) vmax = vs[i]; if (vs[i] < vmin) vmin = vs[i]; }
      dphi = (xs[1] - xs[0]) * p.Mi / PHI0;
      for (i = 1; i < n; i++) slope = Math.max(slope, Math.abs(vs[i + 1] - vs[i - 1]) / (2.0 * dphi));
      return { Phi0: p.Mi * per, dV: vmax - vmin, VPhi: slope };
    }
  };
  function sq_Phi0() { return PHI0; }

  // ------------------------------------------------------------ quantum Hall
  var qhe = {
    PARAMS: { B: 6.0, n: 3.0e15, T: 1.5, w0: 0.05, wT: 0.012, rho0: 5.0, rhop: 0.4 }, VARS: ['t', 'rxy', 'rxx', 'B'], init: init, step: step,
    nu: function (p, B) { if (B === undefined) B = p.B; return p.n * H / (QE * B); },
    width: function (p) { return p.w0 + p.wT * p.T; },
    nueff: function (p, B) { var nu = qhe.nu(p, B), w = qhe.width(p), s = 0.0, k; for (k = 1; k <= 60; k++) s += 0.5 * (1.0 + Math.tanh((nu - (k - 0.5)) / w)); return s; },
    rxy: function (p, B) { if (B === undefined) B = p.B; var ne = qhe.nueff(p, B); return ne > 1e-9 ? RK / ne : 1e9; },
    rxx: function (p, B) { if (B === undefined) B = p.B; var nu = qhe.nu(p, B), w = qhe.width(p), s = 0.0, k; for (k = 1; k <= 60; k++) s += sech2((nu - (k - 0.5)) / w); return p.rho0 + p.rhop * RK / Math.max(nu, 1.0) * s; },
    view: function (s, p) { return { t: tOf(s), rxy: qhe.rxy(p), rxx: qhe.rxx(p), B: p.B }; },
    measure: function (p) {
      var b2 = p.n * H / (2.0 * QE), best = 1e300, bb = b2, i, b, d;
      for (i = -60; i <= 60; i++) { b = b2 * (1.0 + 0.15 * i / 60.0); d = Math.abs(qhe.rxy(p, b * 1.001) - qhe.rxy(p, b * 0.999)); if (d < best) { best = d; bb = b; } }
      return { RK: 2.0 * qhe.rxy(p, bb), B2: bb, n: 0.0 };
    }
  };
  function qhe_RK() { return RK; }

  // ------------------------------------------------------------ Shubnikov-de Haas
  var sdh = {
    PARAMS: { B: 5.0, n: 3.0e15, T: 1.5, mstar: 0.067, muq: 3.0, rho0: 50.0 }, VARS: ['t', 'rho', 'B', 'F'], init: init, step: step,
    F: function (p) { return p.n * H / (2.0 * QE); },
    amp: function (p, B, T) {
      if (B === undefined) B = p.B; if (T === undefined) T = p.T;
      var x = 2.0 * PI * PI * KB * T * p.mstar * ME / (HBAR * QE * B);
      return 2.0 * Math.exp(-PI / (p.muq * B)) * (x > 1e-9 ? x / Math.sinh(x) : 1.0);
    },
    rho: function (p, B, T) { if (B === undefined) B = p.B; return p.rho0 * (1.0 + sdh.amp(p, B, T) * Math.cos(2.0 * PI * sdh.F(p) / B + PI)); },
    view: function (s, p) { return { t: tOf(s), rho: sdh.rho(p), B: p.B, F: sdh.F(p) }; },
    measure: function (p) {
      var n = 3000, x0 = 1.0 / 12.0, x1 = 1.0 / 0.8, xs = [], ys = [], i, pk = [], dx, a, b, c, d, pts = [], mc;
      for (i = 0; i <= n; i++) { xs.push(x0 + (x1 - x0) * i / n); ys.push(sdh.rho(p, 1.0 / xs[i])); }
      dx = xs[1] - xs[0];
      for (i = 1; i < n; i++) {
        if (ys[i] > ys[i - 1] && ys[i] >= ys[i + 1]) { a = ys[i - 1]; b = ys[i]; c = ys[i + 1]; d = a - 2 * b + c; pk.push(xs[i] + (d !== 0 ? dx * 0.5 * (a - c) / d : 0.0)); }
      }
      for (i = 0; i < pk.length; i++) pts.push([i, pk[i]]);
      mc = pk.length > 2 ? line(pts) : [0.0, 0.0];
      return { n: mc[0] > 0 ? 2.0 * QE / (H * mc[0]) : 0.0, peaks: pk.length, F: sdh.F(p) };
    }
  };
  function sdh_n(p) { return p.n; }

  // ------------------------------------------------------------ weak localisation
  var wl = {
    PARAMS: { B: 0.01, T: 2.0, L1: 1.0e-6, pexp: 1.0, noise: 0.0, seed: 5.0 }, VARS: ['t', 'ds', 'B', 'Bphi'], init: init, step: step,
    Lphi: function (p) { return p.L1 * Math.pow(p.T, -0.5 * p.pexp); },
    Bphi: function (p) { return HBAR / (4.0 * QE * Math.pow(wl.Lphi(p), 2)); },
    ds: function (p, B, bphi) { if (B === undefined) B = p.B; if (bphi === undefined) bphi = wl.Bphi(p); var x = bphi / B; return (QE * QE / (PI * H)) * (digamma(0.5 + x) - Math.log(x)); },
    view: function (s, p) { return { t: tOf(s), ds: wl.ds(p), B: p.B, Bphi: wl.Bphi(p) }; },
    fit: function (pts) {
      function sse(bp) { var s = 0.0, i, e; for (i = 0; i < pts.length; i++) { e = pts[i][1] - (QE * QE / (PI * H)) * (digamma(0.5 + bp / pts[i][0]) - Math.log(bp / pts[i][0])); s += e * e; } return s; }
      var lo = 1e-6, hi = 1.0, r, rep, i, best, bb, bp, v;
      for (rep = 0; rep < 4; rep++) {
        best = 1e300; bb = lo;
        for (i = 0; i <= 40; i++) { bp = lo * Math.pow(hi / lo, i / 40.0); v = sse(bp); if (v < best) { best = v; bb = bp; } }
        r = Math.pow(hi / lo, 1.0 / 40.0); lo = bb / r; hi = bb * r;
      }
      return 0.5 * (lo + hi);
    },
    measure: function (p) {
      var bp = wl.Bphi(p), ms = [0.05, 0.1, 0.2, 0.4, 0.7, 1.0, 1.5, 2.5, 4.0, 6.0], pts = [], i, fb;
      for (i = 0; i < ms.length; i++) pts.push([bp * ms[i], wl.ds(p, bp * ms[i])]);
      fb = wl.fit(pts);
      return { Bphi: fb, Lphi: Math.sqrt(HBAR / (4.0 * QE * fb)) };
    }
  };
  function wl_Lphi(p) { return wl.Lphi(p); }

  // ------------------------------------------------------------ NIS tunnelling
  var tun = {
    PARAMS: { V: 0.0, Tc: 1.2, T: 0.1, Gn: 1.0e-3 }, VARS: ['t', 'I', 'V', 'Delta'], init: init, step: step,
    gap: function (p) {
      if (p._gap !== undefined) return p._gap;
      var t = p.T; if (t >= p.Tc) return 0.0;
      return 1.764 * KB * p.Tc * Math.tanh(1.74 * Math.sqrt(p.Tc / t - 1.0));
    },
    cur: function (p, V) {
      if (V === undefined) V = p.V;
      var d = tun.gap(p), kt = KB * p.T, ev = QE * V, umax, n, h, s, i, u, e, x1, x2, f1, f2, wgt;
      if (d <= 0) return p.Gn * V;
      umax = Math.acosh(Math.max((Math.abs(ev) + 40.0 * kt) / d, 1.0) + 1.0);
      n = 400; h = umax / n; s = 0.0;
      for (i = 0; i <= n; i++) {
        u = i * h; e = d * Math.cosh(u); x1 = (e - ev) / kt; x2 = (e + ev) / kt;
        f1 = x1 > 700 ? 0.0 : 1.0 / (Math.exp(x1) + 1.0); f2 = x2 > 700 ? 0.0 : 1.0 / (Math.exp(x2) + 1.0);
        wgt = (i === 0 || i === n) ? 1.0 : (i % 2 ? 4.0 : 2.0);
        s += wgt * e * (f1 - f2);
      }
      return p.Gn / QE * s * h / 3.0;
    },
    view: function (s, p) { return { t: tOf(s), I: tun.cur(p), V: p.V, Delta: tun.gap(p) }; },
    fit: function (pts, p) {
      var d0 = 1.764 * KB * p.Tc, sc = p.Gn * d0 / QE;
      function sse(d) { var q = cp(p), s2 = 0.0, i, e; q._gap = d; for (i = 0; i < pts.length; i++) { e = (tun.cur(q, pts[i][0]) - pts[i][1]) / sc; s2 += e * e; } return s2; }
      var lo = 0.5 * d0, hi = 1.5 * d0, a = hi - GR * (hi - lo), b = lo + GR * (hi - lo), fa = sse(a), fb = sse(b), i;
      for (i = 0; i < 40; i++) {
        if (fa < fb) { hi = b; b = a; fb = fa; a = hi - GR * (hi - lo); fa = sse(a); }
        else { lo = a; a = b; fa = fb; b = lo + GR * (hi - lo); fb = sse(b); }
      }
      return 0.5 * (lo + hi) / QE;
    },
    measure: function (p) {
      var d0 = tun.gap(p), ms = [0.6, 0.9, 1.0, 1.05, 1.1, 1.2, 1.4, 1.8, 2.4], pts = [], i, d;
      for (i = 0; i < ms.length; i++) pts.push([d0 / QE * ms[i], tun.cur(p, d0 / QE * ms[i])]);
      d = tun.fit(pts, p);
      return { Delta: d, Gap: d };
    }
  };
  function tun_gap(p) { return 1.764 * KB * p.Tc / QE; }

  // ------------------------------------------------------------ NMR (Bloch)
  var bloch = {
    PARAMS: { B: 0.5, gamma: 2.6752218744e8, T1: 1.5, T2: 0.4, M0: 1.0, fq: 2000.0, noise: 0.0, seed: 7.0, frf: 0.0, tau: 1.0, G: 0.0, Dm: 2.3e-9 }, VARS: ['t', 'S', 'f', 'M'], init: init, step: step,
    fL: function (p) { return p.gamma * p.B / (2.0 * PI); },
    resp: function (p, f) { var d = (f - bloch.fL(p)) / p.fq; return p.M0 / (1.0 + d * d); },
    ir: function (p, tau) { return p.M0 * (1.0 - 2.0 * Math.exp(-tau / p.T1)); },
    echo: function (p, tau) { return p.M0 * Math.exp(-2.0 * tau / p.T2 - (2.0 / 3.0) * Math.pow(p.gamma * p.G, 2) * p.Dm * Math.pow(tau, 3)); },
    cpmg: function (p, tau) { return p.M0 * Math.exp(-2.0 * tau / p.T2); },
    view: function (s, p) { return { t: tOf(s), S: bloch.resp(p, p.frf), f: bloch.fL(p), M: bloch.ir(p, p.tau) }; },
    measure: function (p) {
      var lo = bloch.fL(p) * 0.9, hi = bloch.fL(p) * 1.1, a = hi - GR * (hi - lo), b = lo + GR * (hi - lo), i, fl, t1 = [], t2 = [], ks1 = [0.1, 0.3, 0.6, 1.0, 1.6, 2.4], ks2 = [0.1, 0.2, 0.4, 0.7, 1.0], m1, m2;
      for (i = 0; i < 120; i++) {
        if (bloch.resp(p, a) > bloch.resp(p, b)) hi = b; else lo = a;
        a = hi - GR * (hi - lo); b = lo + GR * (hi - lo);
      }
      fl = 0.5 * (lo + hi);
      for (i = 0; i < ks1.length; i++) t1.push([p.T1 * ks1[i], Math.log(p.M0 - bloch.ir(p, p.T1 * ks1[i]))]);
      m1 = line(t1)[0];
      for (i = 0; i < ks2.length; i++) t2.push([2 * p.T2 * ks2[i], Math.log(bloch.echo(p, p.T2 * ks2[i]))]);
      m2 = line(t2)[0];
      return { fL: fl, gamma: 2.0 * PI * fl / p.B, T1: m1 < 0 ? -1.0 / m1 : 0.0, T2: m2 < 0 ? -1.0 / m2 : 0.0 };
    }
  };
  function bloch_gamma(p) { return p.gamma; }

  // ------------------------------------------------------------ PFG diffusion
  var pfg = {
    PARAMS: { g: 0.1, gamma: 2.6752218744e8, delta: 2.0e-3, Dl: 0.02, D: 2.3e-9, noise: 0.0, seed: 9.0 }, VARS: ['t', 'E', 'g', 'b'], init: init, step: step,
    bfac: function (p, g) { if (g === undefined) g = p.g; return Math.pow(p.gamma * g * p.delta, 2) * (p.Dl - p.delta / 3.0); },
    E: function (p, g) { return Math.exp(-p.D * pfg.bfac(p, g)); },
    view: function (s, p) { return { t: tOf(s), E: pfg.E(p), g: p.g, b: pfg.bfac(p) }; },
    measure: function (p) {
      var gs = [0.02, 0.05, 0.08, 0.12, 0.16, 0.2], pts = [], i;
      for (i = 0; i < gs.length; i++) pts.push([pfg.bfac(p, gs[i]), Math.log(pfg.E(p, gs[i]))]);
      return { D: -line(pts)[0] };
    }
  };
  function pfg_D(p) { return p.D; }

  // ------------------------------------------------------------ ESR
  var esr = {
    PARAMS: { B: 0.0005, f: 1.4e7, g: 2.0036, dB: 3.0e-5, amp: 1.0 }, VARS: ['t', 'S', 'B', 'B0'], init: init, step: step,
    B0: function (p) { return H * p.f / (p.g * MUB); },
    sig: function (p, B) { if (B === undefined) B = p.B; var x = (B - esr.B0(p)) / p.dB; return -2.0 * p.amp * x / Math.pow(1.0 + x * x, 2); },
    view: function (s, p) { return { t: tOf(s), S: esr.sig(p), B: p.B, B0: esr.B0(p) }; },
    measure: function (p) {
      var b0 = esr.B0(p), lo = b0 - 0.5 * p.dB, hi = b0 + 0.5 * p.dB, mid, i, bz, a, b, x1, x2, xl, xr;
      for (i = 0; i < 100; i++) { mid = 0.5 * (lo + hi); if (esr.sig(p, mid) > 0) lo = mid; else hi = mid; }
      bz = 0.5 * (lo + hi);
      a = bz - 3 * p.dB; b = bz; x1 = b - GR * (b - a); x2 = a + GR * (b - a);
      for (i = 0; i < 100; i++) { if (esr.sig(p, x1) > esr.sig(p, x2)) b = x2; else a = x1; x1 = b - GR * (b - a); x2 = a + GR * (b - a); }
      xl = 0.5 * (a + b);
      a = bz; b = bz + 3 * p.dB; x1 = b - GR * (b - a); x2 = a + GR * (b - a);
      for (i = 0; i < 100; i++) { if (esr.sig(p, x1) < esr.sig(p, x2)) b = x2; else a = x1; x1 = b - GR * (b - a); x2 = a + GR * (b - a); }
      xr = 0.5 * (a + b);
      return { g: H * p.f / (MUB * bz), B0: bz, dBpp: xr - xl };
    }
  };
  function esr_g(p) { return p.g; }

  // ------------------------------------------------------------ CW NMR
  var nmrcw = {
    PARAMS: { B: 0.3, f: 1.5e7, gamma: 2.6752218744e8, dB: 2.0e-5, amp: 1.0 }, VARS: ['t', 'S', 'B', 'B0'], init: init, step: step,
    B0: function (p) { return 2.0 * PI * p.f / p.gamma; },
    sig: function (p, B) { if (B === undefined) B = p.B; var x = (B - nmrcw.B0(p)) / p.dB; return -2.0 * p.amp * x / Math.pow(1.0 + x * x, 2); },
    view: function (s, p) { return { t: tOf(s), S: nmrcw.sig(p), B: p.B, B0: nmrcw.B0(p) }; },
    measure: function (p) {
      var b0 = nmrcw.B0(p), lo = b0 - 0.5 * p.dB, hi = b0 + 0.5 * p.dB, mid, i, bz, gam;
      for (i = 0; i < 100; i++) { mid = 0.5 * (lo + hi); if (nmrcw.sig(p, mid) > 0) lo = mid; else hi = mid; }
      bz = 0.5 * (lo + hi); gam = 2.0 * PI * p.f / bz;
      return { gamma: gam, B0: bz, gI: HBAR * gam / MUN };
    }
  };

  // ------------------------------------------------------------ Moessbauer 57Fe
  var EG = 14412.5, GG = 0.18124, GE = -0.10348;
  var MBL = [[-0.5, -1.5, 3.0], [-0.5, -0.5, 2.0], [-0.5, 0.5, 1.0], [0.5, -0.5, 1.0], [0.5, 0.5, 2.0], [0.5, 1.5, 3.0]];
  var mb = {
    PARAMS: { v: 0.0, Bhf: 33.0, delta: 0.0, eps: 0.0, wid: 0.25e-3, depth: 0.1 }, VARS: ['t', 'T', 'v'], init: init, step: step,
    pos: function (p) {
      var out = [], sh = [1.0, -1.0, 1.0, 1.0, -1.0, 1.0], k, e;
      for (k = 0; k < 6; k++) { e = MUN * p.Bhf * (GE * MBL[k][1] - GG * MBL[k][0]) / QE; out.push([p.delta + p.eps * sh[k] + CLIGHT * e / EG, MBL[k][2]]); }
      return out;
    },
    trans: function (p, v) {
      if (v === undefined) v = p.v;
      var s = 0.0, ps = mb.pos(p), k, d;
      for (k = 0; k < 6; k++) { d = (v - ps[k][0]) / (0.5 * p.wid); s += ps[k][1] / 12.0 / (1.0 + d * d); }
      return 1.0 - p.depth * s * 2.0;
    },
    view: function (s, p) { return { t: tOf(s), T: mb.trans(p), v: p.v }; },
    measure: function (p) {
      var n = 4800, vs = [], ts = [], i, dx, pk = [], a, b, c, d, coef, eps;
      for (i = 0; i <= n; i++) { vs.push(-12.0e-3 + 24.0e-3 * i / n); ts.push(mb.trans(p, vs[i])); }
      dx = vs[1] - vs[0];
      for (i = 1; i < n; i++) {
        if (ts[i] < ts[i - 1] && ts[i] <= ts[i + 1] && ts[i] < 1.0 - 0.1 * p.depth) { a = ts[i - 1]; b = ts[i]; c = ts[i + 1]; d = a - 2 * b + c; pk.push(vs[i] + (d !== 0 ? dx * 0.5 * (a - c) / d : 0.0)); }
      }
      if (pk.length < 6) return { Bhf: 0.0, delta: 0.0, eps: 0.0 };
      pk = pk.slice(0, 6);
      coef = CLIGHT * MUN / QE / EG * 2.0 * (1.5 * Math.abs(GE) + 0.5 * GG);
      eps = ((pk[0] + pk[5]) + (pk[2] + pk[3]) - 2.0 * (pk[1] + pk[4])) / 12.0;
      return { Bhf: (pk[5] - pk[0]) / coef, delta: (pk[0] + pk[1] + pk[2] + pk[3] + pk[4] + pk[5]) / 6.0 - eps / 3.0, eps: eps };
    }
  };
  function mb_B(p) { return p.Bhf; }

  H0.register({
    K: { phd_scrt: scrt, phd_scic: scic, phd_acsusc: acs, phd_therm: therm, phd_jj: jj, phd_dcsquid: sq, phd_qhe: qhe, phd_sdh: sdh,
      phd_weakloc: wl, phd_tunnel: tun, phd_bloch: bloch, phd_pfg: pfg, phd_esr: esr, phd_nmrcw: nmrcw, phd_mossbauer: mb },
    TEXTBOOK: { phd_Tc: scrt_Tc, phd_Ic: scic_Ic, phd_lam0: acs_lam0, phd_thermS: therm_S, phd_Phi0: sq_Phi0, phd_RK: qhe_RK, phd_sdhn: sdh_n,
      phd_Lphi: wl_Lphi, phd_gap: tun_gap, phd_gamma: bloch_gamma, phd_D: pfg_D, phd_g: esr_g, phd_Bhf: mb_B, phd_fJ: jj_f,
      phd_gI: function (p) { return HBAR * p.gamma / MUN; } },
    CALCS: {}
  });
})(typeof window !== 'undefined' ? window : this);
