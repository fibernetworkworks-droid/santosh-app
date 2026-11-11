/* Kernel pack `modern_ug`: the exact JavaScript twin of app/prayog/packs/modern_ug.py - the B.Sc. benches for
   modern / atomic physics, nuclear and radiation physics, solid state physics and nanomaterials. Same formulas,
   same algorithms, same numbers (the server's tests run both and compare). Deterministic: no randomness from the
   clock - a counting experiment draws its Poisson numbers from a Lehmer generator seeded by the lab's own `seed`,
   so the same lab always gives the same counts in both twins. */
(function (root) {
  'use strict';
  var H0 = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI;
  var H = 6.62607015e-34, C = 2.99792458e8, QE = 1.602176634e-19, KB = 1.380649e-23;
  var VT = 0.025852, LN2 = Math.log(2.0);

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function slope(pts) {
    var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, d;
    if (n < 2) return 0;
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    d = n * sxx - sx * sx;
    return d === 0 ? 0 : (n * sxy - sx * sy) / d;
  }
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0; }
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
  function Rnd(seed) { var s = Math.floor(Math.abs(seed)) % 2147483646; this.s = s + 1; }
  Rnd.prototype.next = function () { this.s = (this.s * 16807) % 2147483647; return this.s / 2147483647; };
  Rnd.prototype.poisson = function (m) {
    if (m <= 0) return 0;
    if (m > 400) { var kk = Math.floor(m / 400) + 1, total = 0, j;
      for (j = 0; j < kk; j++) total += this.poisson(m / kk);
      return total; }
    var lim = Math.exp(-m), k = 0, p = 1;
    for (;;) { p *= this.next(); if (p <= lim) return k; k += 1; if (k > 100000) return k; }
  };
  function over(p, k, v) { var q = {}, i, ks = Object.keys(p); for (i = 0; i < ks.length; i++) q[ks[i]] = p[ks[i]]; q[k] = v; return q; }

  // ------------------------------------------------------------------ photoelectric effect
  var photocell = {
    PARAMS: { lam: 5.461e-7, phi: 2.14, Vr: 0.0, P: 1.0, Isat0: 1.2e-9, dark: 2.0e-12,
      lam1: 3.6502e-7, lam2: 4.0466e-7, lam3: 4.3583e-7, lam4: 5.4607e-7, lam5: 5.7907e-7 },
    VARS: ['t', 'I', 'I_nA', 'V', 'Vs', 'Isat', 'E_ph'],
    stopV: function (p) { return H * C / (p.lam * QE) - p.phi; },
    frac: function (v, vs) { if (vs <= 0) return 0; if (v <= 0) return 1; if (v >= vs) return 0; return Math.pow(1 - v / vs, 1.5); },
    current: function (v, p) { return p.dark + p.Isat0 * Math.max(p.P, 0) * photocell.frac(v, photocell.stopV(p)); },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var vs = photocell.stopV(p);
      return { t: s.t || 0, I: photocell.current(p.Vr, p), I_nA: photocell.current(p.Vr, p) * 1e9, V: p.Vr, Vs: vs,
        Isat: p.dark + p.Isat0 * Math.max(p.P, 0), E_ph: H * C / (p.lam * QE) }; },
    measure: function (p) {
      var lo = 0, hi = 12, i, mid;
      if (photocell.frac(0, photocell.stopV(p)) <= 0) return { Vs: 0, I: photocell.current(p.Vr, p) };
      for (i = 0; i < 200; i++) { mid = (lo + hi) / 2; if (photocell.frac(mid, photocell.stopV(p)) > 0) lo = mid; else hi = mid; }
      return { Vs: (lo + hi) / 2, I: photocell.current(p.Vr, p) };
    }
  };
  function photo_Vs(p) { return H * C / (p.lam * QE) - p.phi; }

  // ------------------------------------------------------------------ LED band gap (Planck's constant)
  var ledgap = {
    PARAMS: { lam: 6.3e-7, Iref: 0.001, nD: 2.0, Rs: 220.0, Eb: 3.0,
      lam1: 6.3e-7, lam2: 5.9e-7, lam3: 5.25e-7, lam4: 4.7e-7, lam5: 4.05e-7 },
    VARS: ['t', 'V', 'I', 'V0', 'lam_nm'],
    gapV: function (p) { return H * C / (QE * p.lam); },
    iSat: function (p) { return p.Iref * Math.exp(-ledgap.gapV(p) / (p.nD * VT)); },
    current: function (v, p) { return ledgap.iSat(p) * (Math.exp(Math.min(v / (p.nD * VT), 90)) - 1); },
    solve: function (p) { var lo = 0, hi = Math.max(p.Eb, 0), i, mid;
      for (i = 0; i < 200; i++) { mid = (lo + hi) / 2; if (mid + ledgap.current(mid, p) * p.Rs > p.Eb) hi = mid; else lo = mid; }
      return (lo + hi) / 2; },
    turnOn: function (p) { var lo = 0, hi = 10, i, mid;
      for (i = 0; i < 200; i++) { mid = (lo + hi) / 2; if (ledgap.current(mid, p) < p.Iref) lo = mid; else hi = mid; }
      return (lo + hi) / 2; },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var v = ledgap.solve(p);
      return { t: s.t || 0, V: v, I: ledgap.current(v, p), V0: ledgap.turnOn(p), lam_nm: p.lam * 1e9 }; },
    measure: function (p) { var v = ledgap.solve(p);
      return { V0: ledgap.turnOn(p), V: v, I: ledgap.current(v, p) }; }
  };
  function led_V0(p) { return H * C / (QE * p.lam); }

  // ------------------------------------------------------------------ Franck-Hertz tube
  var fhtube = {
    PARAMS: { Vg: 0.0, Ue: 4.9, Vc: 1.5, V0: 7.0, Vmid: 20.0, damp: 0.85, Iscale: 1.0e-9, Ioff: 1.0e-11,
      Vmax: 32.0, Vt: 0.0 },
    VARS: ['t', 'I', 'I_nA', 'V', 'n_peaks'],
    current: function (v, p) {
      if (v < 0) v = 0;
      var vt = p.Vt > 0 ? p.Vt : p.Vc + 0.5 * p.Ue;
      if (v <= vt) return p.Ioff;
      var on = 1 - Math.exp(-(v - vt) / 0.5);
      var env = Math.exp(clamp((v - p.Vmid) / Math.max(p.V0, 1e-9), -60, 60));
      var per = 1 + p.damp * Math.cos(2 * PI * (v - p.Vc) / Math.max(p.Ue, 1e-9));
      return p.Ioff + p.Iscale * on * env * per / (1 + p.damp);
    },
    peaks: function (p) {
      var out = [], ue = Math.max(p.Ue, 1e-9), n = 1, centre, lo, hi, i, a1, a2;
      for (;;) {
        centre = p.Vc + n * ue; lo = centre - ue / 2; hi = centre + ue / 2;
        if (lo < 0.5) { n += 1; if (centre > p.Vmax) break; continue; }
        if (hi > p.Vmax) break;
        for (i = 0; i < 200; i++) { a1 = lo + (hi - lo) / 3; a2 = hi - (hi - lo) / 3;
          if (fhtube.current(a1, p) < fhtube.current(a2, p)) lo = a1; else hi = a2; }
        out.push((lo + hi) / 2); n += 1;
      }
      return out;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0, I: fhtube.current(p.Vg, p), I_nA: fhtube.current(p.Vg, p) * 1e9,
      V: p.Vg, n_peaks: fhtube.peaks(p).length }; },
    measure: function (p) { var pk = fhtube.peaks(p), pts = [], i;
      for (i = 0; i < pk.length; i++) pts.push([i + 1, pk[i]]);
      return { spacing: slope(pts), n_peaks: pk.length, V1: pk.length ? pk[0] : 0, I: fhtube.current(p.Vg, p) }; }
  };
  function fh_spacing(p) { return p.Ue; }

  // ------------------------------------------------------------------ grating spectrometer
  var grating = {
    PARAMS: { Nl: 600000.0, order: 1.0, nq: 3.0, nl: 2.0, Rh: 10967758.3 },
    VARS: ['t', 'lam', 'theta', 'lam_nm'],
    wavelength: function (p) { var inv = p.Rh * (1 / (p.nl * p.nl) - 1 / (p.nq * p.nq)); return inv > 0 ? 1 / inv : 0; },
    angle: function (p) { var s = grating.wavelength(p) * p.order * p.Nl; return (s >= -1 && s <= 1) ? Math.asin(s) : 0; },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var lam = grating.wavelength(p);
      return { t: s.t || 0, lam: lam, theta: grating.angle(p), lam_nm: lam * 1e9 }; },
    measure: function (p) { var th = grating.angle(p);
      return { lam: (p.order * p.Nl !== 0) ? Math.sin(th) / (p.order * p.Nl) : 0, theta: th }; }
  };
  function balmer_lam(p) { return 1 / (p.Rh * (1 / (p.nl * p.nl) - 1 / (p.nq * p.nq))); }

  // ------------------------------------------------------------------ GM counter (plateau, dead time, statistics)
  var gmtube = {
    PARAMS: { V: 450.0, Vs: 330.0, Vp: 650.0, slope: 0.03, rise: 25.0, N0: 60.0, bg: 0.5,
      tau: 2.5e-4, t: 10.0, nrep: 50.0, seed: 7.0 },
    VARS: ['t', 'rate', 'rate_true', 'counts', 'V'],
    plateau: function (p) {
      var v = p.V, f, d;
      if (v <= p.Vs) return 0;
      f = (1 - Math.exp(-(v - p.Vs) / Math.max(p.rise, 1e-9))) * (1 + p.slope * (v - p.Vs) / 100);
      if (v > p.Vp) { d = (v - p.Vp) / 40; f *= 1 + d * d; }
      return f;
    },
    trueRate: function (p) { return (p.N0 + p.bg) * gmtube.plateau(p); },
    obsRate: function (p) { var r = gmtube.trueRate(p); return r / (1 + r * p.tau); },
    counts: function (p, n) { var rnd = new Rnd(p.seed), m = gmtube.obsRate(p) * Math.max(p.t, 0), out = [], i;
      for (i = 0; i < Math.max(0, n); i++) out.push(rnd.poisson(m)); return out; },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0, rate: gmtube.obsRate(p), rate_true: gmtube.trueRate(p),
      counts: gmtube.obsRate(p) * p.t, V: p.V }; },
    measure: function (p) {
      var obs = gmtube.obsRate(p), cs = gmtube.counts(p, Math.floor(p.nrep)), i, m, sq = [], v = 0;
      m = mean(cs);
      for (i = 0; i < cs.length; i++) sq.push((cs[i] - m) * (cs[i] - m));
      if (cs.length > 1) v = mean(sq) * (cs.length / (cs.length - 1));
      return { rate: obs, rate_corr: obs / (1 - obs * p.tau), mean_counts: m, sd_counts: Math.sqrt(v),
        ratio: m > 0 ? Math.sqrt(v) / Math.sqrt(m) : 0 };
    }
  };
  function gm_true_rate(p) {
    var v = p.V, f;
    if (v <= p.Vs) return 0;
    f = (1 - Math.exp((p.Vs - v) / p.rise)) * (1 + p.slope * (v - p.Vs) / 100);
    if (v > p.Vp) f = f * (1 + Math.pow((v - p.Vp) / 40, 2));
    return (p.N0 + p.bg) * f;
  }

  // ------------------------------------------------------------------ absorption of gamma rays
  var gmabsorb = {
    PARAMS: { x: 0.0, mu: 20.14, N0: 80.0, bg: 0.5, tau: 2.5e-4, t: 60.0, seed: 11.0 },
    VARS: ['t', 'rate', 'net', 'x_mm'],
    trueRate: function (p) { return p.bg + p.N0 * Math.exp(-p.mu * Math.max(p.x, 0)); },
    obsRate: function (p) { var r = gmabsorb.trueRate(p); return r / (1 + r * p.tau); },
    counts: function (p, k) { var rnd = new Rnd(p.seed + 977 * (k || 0));
      return rnd.poisson(gmabsorb.obsRate(p) * Math.max(p.t, 0)); },
    halfThickness: function (p) {
      var n0 = gmabsorb.trueRate(over(p, 'x', 0)) - p.bg, lo = 0, hi = 1, i, mid;
      for (i = 0; i < 200; i++) { mid = (lo + hi) / 2;
        if (gmabsorb.trueRate(over(p, 'x', mid)) - p.bg > n0 / 2) lo = mid; else hi = mid; }
      return (lo + hi) / 2;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0, rate: gmabsorb.obsRate(p), net: gmabsorb.obsRate(p) - p.bg, x_mm: p.x * 1000 }; },
    measure: function (p) { return { rate: gmabsorb.obsRate(p), x_half: gmabsorb.halfThickness(p),
      net: gmabsorb.obsRate(p) - p.bg }; }
  };
  function gm_hvl(p) { return LN2 / p.mu; }

  // ------------------------------------------------------------------ half-life of a short-lived source
  var gmdecay = {
    PARAMS: { t: 0.0, T: 3257.4, N0: 120.0, bg: 0.5, tau: 2.5e-4, tc: 60.0, seed: 13.0 },
    VARS: ['t', 'rate', 'net', 'frac'],
    trueRate: function (p) { return p.bg + p.N0 * Math.exp(-LN2 * Math.max(p.t, 0) / Math.max(p.T, 1e-9)); },
    obsRate: function (p) { var r = gmdecay.trueRate(p); return r / (1 + r * p.tau); },
    counts: function (p, k) { var rnd = new Rnd(p.seed + 977 * (k || 0));
      return rnd.poisson(gmdecay.obsRate(p) * Math.max(p.tc, 0)); },
    halfTime: function (p) {
      var lo = 0, hi = Math.max(p.T, 1e-9) * 20, i, mid;
      for (i = 0; i < 200; i++) { mid = (lo + hi) / 2;
        if (gmdecay.trueRate(over(p, 't', mid)) - p.bg > p.N0 / 2) lo = mid; else hi = mid; }
      return (lo + hi) / 2;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var q = over(p, 't', p.t + (s.t || 0));
      return { t: s.t || 0, rate: gmdecay.obsRate(q), net: gmdecay.obsRate(q) - p.bg,
        frac: Math.exp(-LN2 * Math.max(q.t, 0) / Math.max(p.T, 1e-9)) }; },
    measure: function (p) { return { t_half: gmdecay.halfTime(p), rate: gmdecay.obsRate(p), net: gmdecay.obsRate(p) - p.bg }; }
  };
  function decay_T(p) { return p.T; }

  // ------------------------------------------------------------------ four-probe resistivity and band gap
  var fourprobe = {
    PARAMS: { T: 300.0, Eg: 0.67, rho300: 0.46, I: 0.002, s: 0.002, w: 0.0005 },
    VARS: ['t', 'V', 'rho', 'T', 'lnrho'],
    rho: function (p) { return p.rho300 * Math.exp(p.Eg * QE / (2 * KB) * (1 / Math.max(p.T, 1e-9) - 1 / 300)); },
    probeV: function (p) { return p.I * fourprobe.rho(p) * LN2 / (PI * p.w); },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0, V: fourprobe.probeV(p), rho: fourprobe.rho(p), T: p.T,
      lnrho: Math.log(Math.max(fourprobe.rho(p), 1e-300)) }; },
    measure: function (p) { var v = fourprobe.probeV(p);
      return { V: v, rho: PI * p.w * v / (LN2 * p.I), T: p.T }; }
  };
  function fourprobe_rho(p) { return p.rho300 * Math.exp(p.Eg * QE / (2 * KB) * (1 / p.T - 1 / 300)); }

  // ------------------------------------------------------------------ Hall effect
  var hallbar = {
    PARAMS: { B: 0.2, I: 0.005, th: 0.0005, n21: 2.0, sg: -1.0, rho: 0.02, wid: 0.004 },
    VARS: ['t', 'Vh', 'RH', 'B', 'I'],
    hallV: function (p) { return p.sg * p.I * p.B / (p.n21 * 1e21 * QE * p.th); },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var vh = hallbar.hallV(p);
      return { t: s.t || 0, Vh: vh, RH: (p.I * p.B !== 0) ? vh * p.th / (p.I * p.B) : 0, B: p.B, I: p.I }; },
    measure: function (p) { var vh = hallbar.hallV(p), rh = (p.I * p.B !== 0) ? vh * p.th / (p.I * p.B) : 0;
      return { Vh: vh, RH: rh, mu: p.rho > 0 ? Math.abs(rh) / p.rho : 0 }; }
  };
  function hall_vh(p) { return p.sg * p.I * p.B / (p.n21 * 1e21 * QE * p.th); }

  // ------------------------------------------------------------------ UV-visible spectrum of a gold colloid
  var B1 = 3.00, B2 = 2.20;
  var colloid = {
    PARAMS: { d: 20.0, conc: 1.0, lam: 5.2e-7, A450: 0.5, wid: 60.0, bgdecay: 120.0 },
    VARS: ['t', 'A', 'lam_nm', 'lam_spr', 'A_spr'],
    B1: B1, B2: B2,
    lamSpr: function (p) { return 512 + 6.53 * Math.exp(0.0216 * p.d); },
    ratio: function (p) { return (Math.log(Math.max(p.d, 1e-6)) + B2) / B1; },
    coef: function (p) {
      var ls = colloid.lamSpr(p), a450 = p.A450 * Math.max(p.conc, 0), aspr = colloid.ratio(p) * a450;
      var hw = Math.max(p.wid, 1e-6) / 2;
      var l450 = 1 / (1 + Math.pow((450 - ls) / hw, 2));
      var bspr = Math.exp(-(ls - 450) / Math.max(p.bgdecay, 1e-6));
      var det = l450 * bspr - 1;
      if (Math.abs(det) < 1e-12) return [0, a450];
      return [(a450 * bspr - aspr) / det, (aspr * l450 - a450) / det];
    },
    absorbance: function (lamNm, p) {
      var ab = colloid.coef(p), ls = colloid.lamSpr(p), hw = Math.max(p.wid, 1e-6) / 2;
      var lor = 1 / (1 + Math.pow((lamNm - ls) / hw, 2));
      var bg = Math.exp(-(lamNm - 450) / Math.max(p.bgdecay, 1e-6));
      return ab[0] * lor + ab[1] * bg;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0, A: colloid.absorbance(p.lam * 1e9, p), lam_nm: p.lam * 1e9,
      lam_spr: colloid.lamSpr(p), A_spr: colloid.absorbance(colloid.lamSpr(p), p) }; },
    peakNm: function (p) { var lo = 450, hi = 750, i, a1, a2;
      for (i = 0; i < 200; i++) { a1 = lo + (hi - lo) / 3; a2 = hi - (hi - lo) / 3;
        if (colloid.absorbance(a1, p) < colloid.absorbance(a2, p)) lo = a1; else hi = a2; }
      return (lo + hi) / 2; },
    measure: function (p) {
      var ls = colloid.lamSpr(p), a450 = colloid.absorbance(450, p), aspr = colloid.absorbance(ls, p);
      return { d_est: a450 > 0 ? Math.exp(B1 * (aspr / a450) - B2) : 0, A450: a450, A_spr: aspr,
        lam_spr: ls, peak_nm: colloid.peakNm(p) };
    }
  };
  function colloid_d(p) { return p.d; }

  H0.register({
    K: { photocell: photocell, ledgap: ledgap, fhtube: fhtube, grating: grating, gmtube: gmtube,
      gmabsorb: gmabsorb, gmdecay: gmdecay, fourprobe: fourprobe, hallbar: hallbar, colloid: colloid },
    TEXTBOOK: { photo_Vs: photo_Vs, led_V0: led_V0, fh_spacing: fh_spacing, balmer_lam: balmer_lam,
      gm_true_rate: gm_true_rate, gm_hvl: gm_hvl, decay_T: decay_T, fourprobe_rho: fourprobe_rho,
      hall_vh: hall_vh, colloid_d: colloid_d },
    CALCS: {
      photo_h: { label: 'h (Planck)', unit: 'J·s', needs: ['f', 'Vs'],
        fn: function (r) { return QE * slope(rws(r, ['f', 'Vs'])); } },
      led_h: { label: 'h (Planck)', unit: 'J·s', needs: ['f', 'V0'],
        fn: function (r) { return QE * slope(rws(r, ['f', 'V0'])); } },
      fh_Ue: { label: 'first excitation potential', unit: 'V', needs: ['n', 'Vp'],
        fn: function (r) { return slope(rws(r, ['n', 'Vp'])); } },
      balmer_R: { label: 'Rydberg constant', unit: '1/m', needs: ['nq', 'lam'],
        fn: function (r, p) { var xs = rws(r, ['nq', 'lam']), out = [], i;
          for (i = 0; i < xs.length; i++) if (xs[i][1] > 0 && xs[i][0] * xs[i][0] !== p.nl * p.nl)
            out.push(1 / (xs[i][1] * (1 / (p.nl * p.nl) - 1 / (xs[i][0] * xs[i][0]))));
          return mean(out); } },
      gm_mu: { label: 'attenuation coefficient', unit: '1/m', needs: ['x', 'net'],
        fn: function (r) { var xs = rws(r, ['x', 'net']), out = [], i;
          for (i = 0; i < xs.length; i++) if (xs[i][1] > 0) out.push([xs[i][0], Math.log(xs[i][1])]);
          return -slope(out); } },
      decay_half: { label: 'half-life', unit: 's', needs: ['t', 'net'],
        fn: function (r) { var xs = rws(r, ['t', 'net']), out = [], i, m;
          for (i = 0; i < xs.length; i++) if (xs[i][1] > 0) out.push([xs[i][0], Math.log(xs[i][1])]);
          m = slope(out); return m < 0 ? LN2 / -m : 0; } },
      bandgap_Eg: { label: 'band gap', unit: 'eV', needs: ['invT', 'lnrho'],
        fn: function (r) { return 2 * KB * slope(rws(r, ['invT', 'lnrho'])) / QE; } },
      hall_RH: { label: 'Hall coefficient', unit: 'm³/C', needs: ['B', 'Vh'],
        fn: function (r, p) { var xs = rws(r, ['B', 'Vh']), out = [], i;
          for (i = 0; i < xs.length; i++) if (xs[i][0] !== 0 && p.I !== 0) out.push(xs[i][1] * p.th / (p.I * xs[i][0]));
          return mean(out); } },
      nano_d: { label: 'particle diameter', unit: 'nm', needs: ['A450', 'Aspr'],
        fn: function (r) { var xs = rws(r, ['A450', 'Aspr']), out = [], i;
          for (i = 0; i < xs.length; i++) if (xs[i][0] > 0) out.push(Math.exp(B1 * (xs[i][1] / xs[i][0]) - B2));
          return mean(out); } }
    }
  });
})(typeof window !== 'undefined' ? window : this);
