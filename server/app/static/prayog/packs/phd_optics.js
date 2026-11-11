/* Kernel pack `phd_optics`: the exact JavaScript twin of app/prayog/packs/phd_optics.py - Ph.D. laser spectroscopy,
   interferometry, photon statistics, signal recovery and plasma diagnostics. Same formulas, same algorithms, same
   numbers (the server's tests run both and compare to 1e-9). Deterministic: every noisy or counting process is drawn
   from a Lehmer generator seeded by the lab's own `seed` parameter, never from the clock. */
(function (root) {
  'use strict';
  var H0 = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI;
  var C = 2.99792458e8, QE = 1.602176634e-19, KB = 1.380649e-23, ME = 9.1093837015e-31, AMU = 1.66053906660e-27;

  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0; }
  function lsq(xs, ys) {                                  // y = a + b x -> [a, b]
    var n = xs.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, d, b;
    if (n < 2) return [0, 0];
    for (i = 0; i < n; i++) { sx += xs[i]; sy += ys[i]; sxy += xs[i] * ys[i]; sxx += xs[i] * xs[i]; }
    d = n * sxx - sx * sx;
    if (d === 0) return [0, 0];
    b = (n * sxy - sx * sy) / d;
    return [(sy - b * sx) / n, b];
  }
  function Rnd(seed) { var s = Math.floor(Math.abs(seed)) % 2147483646; this.s = s + 1; this.has = false; this.z1 = 0; }
  Rnd.prototype.next = function () { this.s = (this.s * 16807) % 2147483647; return this.s / 2147483647; };
  Rnd.prototype.gauss = function () {
    if (this.has) { this.has = false; return this.z1; }
    var u1 = this.next(), u2 = this.next(), r = Math.sqrt(-2 * Math.log(u1));
    this.z1 = r * Math.sin(2 * PI * u2); this.has = true;
    return r * Math.cos(2 * PI * u2);
  };
  Rnd.prototype.poisson = function (m) {
    if (m <= 0) return 0;
    if (m >= 400) { var v = Math.floor(m + Math.sqrt(m) * this.gauss() + 0.5); return v > 0 ? v : 0; }
    var lim = Math.exp(-m), k = 0, p = 1;
    for (;;) { p *= this.next(); if (p <= lim) return k; k += 1; if (k > 100000) return k; }
  };
  function fft(re, im, inverse) {
    var n = re.length, j = 0, i, bit, t, length, sgn = inverse ? 1 : -1, ang, half, wr, wi, k, s, a, b, tr, ti;
    for (i = 1; i < n; i++) {
      bit = n >> 1;
      while (j & bit) { j ^= bit; bit >>= 1; }
      j ^= bit;
      if (i < j) { t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
    }
    for (length = 2; length <= n; length *= 2) {
      ang = sgn * 2 * PI / length; half = length / 2; wr = []; wi = [];
      for (k = 0; k < half; k++) { wr.push(Math.cos(ang * k)); wi.push(Math.sin(ang * k)); }
      for (s = 0; s < n; s += length) for (k = 0; k < half; k++) {
        a = s + k; b = a + half;
        tr = re[b] * wr[k] - im[b] * wi[k]; ti = re[b] * wi[k] + im[b] * wr[k];
        re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
      }
    }
  }
  function zeros(n) { var o = [], i; for (i = 0; i < n; i++) o.push(0); return o; }

  // ------------------------------------------------------------------ lock-in amplifier
  var lockin = {
    PARAMS: { A: 2.0e-5, f: 137.0, phi: 35.0, en: 3.0e-7, tc: 3.0, phr: 0.0, dual: 1.0, seed: 5.0 },
    VARS: ['t', 'X', 'Y', 'R', 'theta', 'sigma'],
    read: function (p, tc, phr, k) {
      var f = p.f, dt = 1 / (10 * f), nset = Math.floor(8 * tc / dt), navg = Math.floor(4 * tc / dt),
        alpha = 1 - Math.exp(-dt / tc), rnd = new Rnd(p.seed + 101 * k), srms = p.en * Math.sqrt(10 * f / 2),
        w = 2 * PI * f, ph = p.phi * PI / 180, pr = phr * PI / 180, x = 0, y = 0, sx = 0, sy = 0, n, t, v;
      for (n = 0; n < nset + navg; n++) {
        t = n * dt;
        v = p.A * Math.cos(w * t + ph) + srms * rnd.gauss();
        x += alpha * (2 * v * Math.cos(w * t + pr) - x);
        y += alpha * (-2 * v * Math.sin(w * t + pr) - y);
        if (n >= nset) { sx += x; sy += y; }
      }
      return [sx / navg, sy / navg];
    },
    sigma: function (p, tc) { return p.en / (2 * Math.sqrt(tc)); },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var d = (p.phi - p.phr) * PI / 180;
      return { t: s.t || 0, X: p.A * Math.cos(d), Y: p.A * Math.sin(d), R: p.A, theta: p.phi - p.phr, sigma: lockin.sigma(p, p.tc) };
    },
    measure: function (p) {
      var xy, a = 0, b = 0, j, ph, xj;
      if (p.dual >= 0.5) {
        xy = lockin.read(p, p.tc, p.phr, 0);
        return { R: Math.sqrt(xy[0] * xy[0] + xy[1] * xy[1]), theta: Math.atan2(xy[1], xy[0]) * 180 / PI + p.phr, X: xy[0], Y: xy[1] };
      }
      for (j = 0; j < 6; j++) {
        ph = 60 * j; xj = lockin.read(p, p.tc, ph, j)[0];
        a += xj * Math.cos(ph * PI / 180) / 3; b += xj * Math.sin(ph * PI / 180) / 3;
      }
      return { R: Math.sqrt(a * a + b * b), theta: -Math.atan2(b, a) * 180 / PI, X: a, Y: b };
    }
  };
  function phd_lockin_A(p) { return p.A; }

  // ------------------------------------------------------------------ Johnson noise
  var johnson = {
    PARAMS: { T: 300.0, df: 10000.0, G: 1000.0, en: 2.0e-9, n: 100000.0, seed: 3.0, R: 10000.0 },
    VARS: ['t', 'v2', 'vrms', 'vn_th'],
    RS: [0.0, 1.0e3, 2.0e3, 5.0e3, 1.0e4, 2.0e4, 5.0e4, 1.0e5],
    v2True: function (p, r) { return p.G * p.G * p.df * (4 * KB * p.T * r + p.en * p.en); },
    msq: function (p, r, k) {
      var rnd = new Rnd(p.seed + 977 * k), sd = Math.sqrt(johnson.v2True(p, r)), n = Math.floor(p.n), s = 0, v, i;
      for (i = 0; i < n; i++) { v = sd * rnd.gauss(); s += v * v; }
      return s / n;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var v2 = johnson.v2True(p, p.R);
      return { t: s.t || 0, v2: v2, vrms: Math.sqrt(v2), vn_th: Math.sqrt(4 * KB * p.T * p.R * p.df) };
    },
    measure: function (p) {
      var xs = [], ys = [], i, ab, e2;
      for (i = 0; i < johnson.RS.length; i++) { xs.push(johnson.RS[i]); ys.push(johnson.msq(p, johnson.RS[i], i)); }
      ab = lsq(xs, ys); e2 = ab[0] / (p.G * p.G * p.df);
      var kb = ab[1] / (4 * p.T * p.df * p.G * p.G);
      return { kB: kb, kB23: kb * 1.0e23, en: e2 > 0 ? Math.sqrt(e2) : 0 };
    }
  };
  function phd_kB() { return KB * 1.0e23; }

  // ------------------------------------------------------------------ shot noise
  var shot = {
    PARAMS: { Rf: 1.0e4, df: 20000.0, n: 40000.0, seed: 11.0, T: 300.0, I: 2.0e-4, q: QE, Iscale: 1.0 },
    VARS: ['t', 'v2', 'vrms', 'i_shot'],
    IS: [0.0, 5.0e-5, 1.0e-4, 2.0e-4, 5.0e-4, 1.0e-3, 2.0e-3],
    v2True: function (p, i) { return p.Rf * p.Rf * p.df * (2 * p.q * i + 4 * KB * p.T / p.Rf); },
    msq: function (p, i, k) {
      var rnd = new Rnd(p.seed + 977 * k), sd = Math.sqrt(shot.v2True(p, i)), n = Math.floor(p.n), s = 0, v, j;
      for (j = 0; j < n; j++) { v = sd * rnd.gauss(); s += v * v; }
      return s / n;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var v2 = shot.v2True(p, p.I);
      return { t: s.t || 0, v2: v2, vrms: Math.sqrt(v2), i_shot: Math.sqrt(2 * p.q * p.I * p.df) };
    },
    measure: function (p) {
      var xs = [], ys = [], j, ab;
      for (j = 0; j < shot.IS.length; j++) { xs.push(shot.IS[j] * p.Iscale); ys.push(shot.msq(p, shot.IS[j] * p.Iscale, j)); }
      ab = lsq(xs, ys);
      var q = ab[1] / (2 * p.Rf * p.Rf * p.df);
      return { q: q, q19: q * 1.0e19, floor: ab[0] };
    }
  };
  function phd_qe() { return QE * 1.0e19; }

  // ------------------------------------------------------------------ noise spectra
  var psd = {
    PARAMS: { T: 300.0, R: 10000.0, en: 5.0e-9, fc: 150.0, fs: 8000.0, N: 256.0, nseg: 256.0, seed: 17.0 },
    VARS: ['t', 'Sw', 'Sf_low'],
    sw: function (p) { return 4 * KB * p.T * p.R + p.en * p.en; },
    spec: function (p, f) { return psd.sw(p) * (1 + p.fc / f); },
    record: function (p, rnd) {
      var n = Math.floor(p.N), re = zeros(n), im = zeros(n), half = n / 2, k, c, g1, g2, out = [], i;
      for (k = 1; k < half; k++) {
        c = Math.sqrt(psd.spec(p, k * p.fs / n) * p.fs * n / 4);
        g1 = rnd.gauss(); g2 = rnd.gauss();
        re[k] = c * g1; im[k] = c * g2; re[n - k] = c * g1; im[n - k] = -c * g2;
      }
      re[half] = Math.sqrt(psd.spec(p, half * p.fs / n) * p.fs * n / 2) * rnd.gauss();
      fft(re, im, true);
      for (i = 0; i < n; i++) out.push(re[i] / n);
      return out;
    },
    spectrum: function (p, nseg) {
      var n = Math.floor(p.N), ns = nseg === undefined || nseg === null ? Math.floor(p.nseg) : nseg, rnd = new Rnd(p.seed),
        win = [], sw2 = 0, acc = zeros(n / 2), s, i, k, x, re, im, out = [];
      for (i = 0; i < n; i++) win.push(0.5 - 0.5 * Math.cos(2 * PI * i / n));
      for (i = 0; i < n; i++) sw2 += win[i] * win[i];
      for (s = 0; s < ns; s++) {
        x = psd.record(p, rnd); re = []; im = zeros(n);
        for (i = 0; i < n; i++) re.push(x[i] * win[i]);
        fft(re, im, false);
        for (k = 1; k < n / 2; k++) acc[k] += re[k] * re[k] + im[k] * im[k];
      }
      for (k = 1; k < n / 2; k++) out.push([k * p.fs / n, 2 * acc[k] / (ns * p.fs * sw2)]);
      return out;
    },
    fit: function (sp) {
      var m = 0, a, b, it, i, s11, s12, s22, r1, r2, mod, w, d;
      for (i = 0; i < sp.length; i++) m += sp[i][1];
      m = m / sp.length; a = m; b = 0;
      for (it = 0; it < 4; it++) {
        s11 = 0; s12 = 0; s22 = 0; r1 = 0; r2 = 0;
        for (i = 0; i < sp.length; i++) {
          mod = a + b / sp[i][0]; if (mod <= 0) mod = m;
          w = 1 / (mod * mod);
          s11 += w; s12 += w / sp[i][0]; s22 += w / (sp[i][0] * sp[i][0]);
          r1 += w * sp[i][1]; r2 += w * sp[i][1] / sp[i][0];
        }
        d = s11 * s22 - s12 * s12;
        if (d === 0) break;
        a = (r1 * s22 - r2 * s12) / d; b = (s11 * r2 - s12 * r1) / d;
      }
      return [a, b];
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0, Sw: psd.sw(p), Sf_low: psd.spec(p, p.fs / p.N) }; },
    measure: function (p) {
      var ab = psd.fit(psd.spectrum(p));
      return { floor: ab[0], floor18: ab[0] * 1.0e18, fc: ab[0] > 0 ? ab[1] / ab[0] : 0 };
    }
  };
  function phd_psd_floor(p) { return (4 * KB * p.T * p.R + p.en * p.en) * 1.0e18; }

  // ------------------------------------------------------------------ boxcar averager
  var boxcar = {
    PARAMS: { tau: 2.0e-6, A: 1.0, vn: 3.0e-4, w: 5.0e-7, td: 0.0, nav: 20000.0, seed: 23.0 },
    VARS: ['t', 'sig', 'sigma1', 'snr'],
    NDEL: 8,
    sig: function (p, td) { return p.A * (p.tau / p.w) * (1 - Math.exp(-p.w / p.tau)) * Math.exp(-td / p.tau); },
    sigma1: function (p) { return p.vn / Math.sqrt(2 * p.w); },
    output: function (p, td, nav, rnd) {
      var s = boxcar.sig(p, td), sg = boxcar.sigma1(p), acc = 0, i;
      for (i = 0; i < nav; i++) acc += s + sg * rnd.gauss();
      return acc / nav;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var sig = boxcar.sig(p, p.td), sg = boxcar.sigma1(p) / Math.sqrt(Math.max(p.nav, 1));
      return { t: s.t || 0, sig: sig, sigma1: boxcar.sigma1(p), snr: sig / sg };
    },
    measure: function (p) {
      var rnd = new Rnd(p.seed), xs = [], ys = [], j, td, y, b;
      for (j = 0; j < boxcar.NDEL; j++) {
        td = 0.3 * p.tau * j; y = boxcar.output(p, td, Math.floor(p.nav), rnd);
        if (y > 0) { xs.push(td); ys.push(Math.log(y)); }
      }
      b = lsq(xs, ys)[1];
      return { tau: b < 0 ? -1 / b : 0 };
    }
  };
  function phd_boxcar_tau(p) { return p.tau; }

  // ------------------------------------------------------------------ Hanbury Brown-Twiss
  var g2k = {
    PARAMS: { tc: 5.0e-5, kind: 1.0, R1: 2.0e5, R2: 2.0e5, Ts: 30.0, nb: 81.0, bw: 6.25e-6, seed: 9.0 },
    VARS: ['t', 'g2_0', 'Cinf'],
    g2: function (p, tau) { if (p.kind < 0.5) return 1; return 1 + Math.exp(-(tau / p.tc) * (tau / p.tc)); },
    hist: function (p, ts) {
      var nb = Math.floor(p.nb), T = ts === undefined || ts === null ? p.Ts : ts, rnd = new Rnd(p.seed), out = [], i, tau;
      for (i = 0; i < nb; i++) {
        tau = (i - Math.floor((nb - 1) / 2)) * p.bw;
        out.push(rnd.poisson(p.R1 * p.R2 * T * p.bw * g2k.g2(p, tau)));
      }
      return out;
    },
    analyse: function (p, h) {
      var nb = h.length, mid = Math.floor((nb - 1) / 2), far = [], i, cinf, g20, xs = [], ys = [], tau, b, tce;
      for (i = 0; i < nb; i++) if (Math.abs(i - mid) * p.bw > 3 * p.tc) far.push(h[i]);
      cinf = mean(far); g20 = cinf > 0 ? h[mid] / cinf : 0;
      for (i = 0; i < nb; i++) {
        tau = (i - mid) * p.bw;
        if (Math.abs(tau) < 1.5 * p.tc && cinf > 0 && h[i] / cinf - 1 > 0.05) { xs.push(tau * tau); ys.push(Math.log(h[i] / cinf - 1)); }
      }
      b = lsq(xs, ys)[1]; tce = b < 0 ? 1 / Math.sqrt(-b) : 0;
      return [g20, tce, cinf];
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0, g2_0: g2k.g2(p, 0), Cinf: p.R1 * p.R2 * p.Ts * p.bw }; },
    measure: function (p) { var a = g2k.analyse(p, g2k.hist(p)); return { g2_0: a[0], tc: a[1], Cinf: a[2] }; }
  };
  function phd_g2_zero(p) { return 1 + (p.kind >= 0.5 ? 1 : 0); }

  // ------------------------------------------------------------------ Poisson counting
  var poisson = {
    PARAMS: { rate: 200.0, td: 1.0e-5, tw: 1.0, nwin: 1000.0, seed: 13.0 },
    VARS: ['t', 'mean', 'fano', 'gap'],
    stream: function (p) {
      var nwin = Math.floor(p.nwin), tot = nwin * p.tw, rnd = new Rnd(p.seed), counts = [], t = 0, ev = 0, gaps = [], g, i;
      for (i = 0; i < nwin; i++) counts.push(0);
      for (;;) {
        g = p.td - Math.log(rnd.next()) / p.rate; t += g;
        if (t >= tot) break;
        counts[Math.floor(t / p.tw)] += 1; ev += 1;
        if (gaps.length < 20000) gaps.push(g);
      }
      return { counts: counts, events: ev, total: tot, gaps: gaps };
    },
    stats: function (counts) {
      var n = counts.length, s = 0, i, m, v = 0;
      for (i = 0; i < n; i++) s += counts[i];
      m = n ? s / n : 0;
      for (i = 0; i < n; i++) v += (counts[i] - m) * (counts[i] - m);
      v = n > 1 ? v / (n - 1) : 0;
      return [m, v];
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var r = p.rate, f = 1 / (1 + r * p.td);
      return { t: s.t || 0, mean: p.tw * r / (1 + r * p.td), fano: f * f, gap: 1 / r + p.td };
    },
    measure: function (p) {
      var st = poisson.stream(p), mv = poisson.stats(st.counts);
      return { mean: mv[0], var: mv[1], fano: mv[0] > 0 ? mv[1] / mv[0] : 0, gap: st.events > 0 ? st.total / st.events : 0 };
    }
  };
  function phd_poisson_gap(p) { return 1 / p.rate + p.td; }

  // ------------------------------------------------------------------ heralded single photons
  var antibunch = {
    PARAMS: { q: 0.02, eta: 0.5, NG: 4.0e8, seed: 21.0 },
    VARS: ['t', 'alpha'],
    probs: function (p) {
      var e = p.eta, q = p.q, pt1 = e / 2, pt2 = 1 - (1 - e / 2) * (1 - e / 2),
        pb2 = 1 - 2 * (1 - e / 2) * (1 - e / 2) + (1 - e) * (1 - e);
      return [(1 - q) * pt1 + q * pt2, q * pb2];
    },
    alphaExact: function (p) { var a = antibunch.probs(p); return a[0] > 0 ? a[1] / (a[0] * a[0]) : 0; },
    counts: function (p) {
      var a = antibunch.probs(p), rnd = new Rnd(p.seed), ng = p.NG, c1 = rnd.poisson(ng * a[0]), c2 = rnd.poisson(ng * a[0]), c3 = rnd.poisson(ng * a[1]);
      return [ng, c1, c2, c3];
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0, alpha: antibunch.alphaExact(p) }; },
    measure: function (p) { var c = antibunch.counts(p); return { alpha: c[1] > 0 && c[2] > 0 ? c[0] * c[3] / (c[1] * c[2]) : 0 }; }
  };
  function phd_antibunch_alpha(p) { return antibunch.alphaExact(p); }

  // ------------------------------------------------------------------ Fabry-Perot
  var fp = {
    PARAMS: { L: 0.15, R: 0.95, lam: 6.328e-7, kz: 1.0e-8, dnu: 0.0, amp2: 0.0, Vmax: 120.0 },
    VARS: ['t', 'fsr_hz', 'fsr_v'],
    NPT: 12000,
    trans: function (p, v) {
      var fco = 4 * p.R / ((1 - p.R) * (1 - p.R)), nu0 = C / p.lam, d1 = 4 * PI * (p.L + p.kz * v) * nu0 / C, s1 = Math.sin(d1 / 2),
        y = 1 / (1 + fco * s1 * s1), d2, s2;
      if (p.amp2 > 0) { d2 = 4 * PI * (p.L + p.kz * v) * (nu0 + p.dnu) / C; s2 = Math.sin(d2 / 2); y += p.amp2 / (1 + fco * s2 * s2); }
      return y;
    },
    trace: function (p) { var n = fp.NPT, o = [], i; for (i = 0; i < n; i++) o.push(fp.trans(p, p.Vmax * i / (n - 1))); return o; },
    peaks: function (p, y) {
      var n = y.length, dv = p.Vmax / (n - 1), hm = 0, i, j, k, m, a, b, pos = [], wid = [];
      for (i = 0; i < n; i++) if (y[i] > hm * 2) hm = y[i] / 2;
      i = 0;
      while (i < n) {
        if (y[i] > hm) {
          j = i; while (j < n && y[j] > hm) j++;
          if (i > 0 && j < n) {
            k = i; for (m = i; m < j; m++) if (y[m] > y[k]) k = m;
            a = (i - 1) + (hm - y[i - 1]) / (y[i] - y[i - 1]);
            b = (j - 1) + (hm - y[j - 1]) / (y[j] - y[j - 1]);
            pos.push(k * dv); wid.push((b - a) * dv);
          }
          i = j;
        } else i++;
      }
      return { pos: pos, wid: wid };
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0, fsr_hz: C / (2 * p.L), fsr_v: p.lam / (2 * p.kz) }; },
    measure: function (p) {
      var pk = fp.peaks(p, fp.trace(p)), ps = pk.pos, ws = pk.wid, fsrv;
      if (ps.length < 2) return { finesse: 0, fsr_v: 0, fsr_hz: 0 };
      fsrv = (ps[ps.length - 1] - ps[0]) / (ps.length - 1);
      return { finesse: fsrv / mean(ws), fsr_v: fsrv, fsr_hz: C / (2 * p.L) };
    }
  };
  function phd_fp_finesse(p) { return PI * Math.sqrt(p.R) / (1 - p.R); }

  // ------------------------------------------------------------------ Langmuir probe
  var lang = {
    PARAMS: { Te: 3.0, ne: 1.0e16, Vp: 8.0, M: 39.948, Ap: 2.0e-6, noise: 0.003, seed: 31.0, W: 4.5, Ar: 6.0e5, Kh: 250.0, V: 0.0 },
    VARS: ['t', 'I', 'Iis', 'Ies', 'Vf'],
    iis: function (p) { return Math.exp(-0.5) * QE * p.ne * p.Ap * Math.sqrt(QE * p.Te / (p.M * AMU)); },
    ies: function (p) { return 0.25 * QE * p.ne * Math.sqrt(8 * QE * p.Te / (PI * ME)) * p.Ap; },
    single: function (p, v) { var e = lang.ies(p) * (v < p.Vp ? Math.exp((v - p.Vp) / p.Te) : 1); return e - lang.iis(p); },
    dbl: function (p, v) { return lang.iis(p) * Math.tanh(v / (2 * p.Te)); },
    iem: function (p, ih) { var tw = 300 + p.Kh * ih * ih; return p.Ar * tw * tw * p.Ap * Math.exp(-p.W * QE / (KB * tw)); },
    vfloat: function (p, ih) { var tot = lang.iis(p) + lang.iem(p, ih), ies = lang.ies(p); return tot < ies ? p.Vp + p.Te * Math.log(tot / ies) : p.Vp; },
    sweepSingle: function (p) {
      var rnd = new Rnd(p.seed), out = [], k, v; for (k = 0; k < 241; k++) { v = -40 + 0.25 * k; out.push([v, lang.single(p, v) * (1 + p.noise * rnd.gauss())]); } return out;
    },
    sweepDouble: function (p) {
      var rnd = new Rnd(p.seed + 1), out = [], k, v; for (k = 0; k < 241; k++) { v = -30 + 0.25 * k; out.push([v, lang.dbl(p, v) * (1 + p.noise * rnd.gauss())]); } return out;
    },
    sweepEmissive: function (p) {
      var rnd = new Rnd(p.seed + 2), out = [], k; for (k = 0; k < 36; k++) out.push([0.1 * k, lang.vfloat(p, 0.1 * k) + 0.05 * rnd.gauss()]); return out;
    },
    fitSingle: function (p, sw) {
      var i, s = 0, iis, imax, xs = [], ys = [], ie, ab, te, vp, ne;
      for (i = 0; i < 20; i++) s += sw[i][1];
      iis = -s / 20; s = 0;
      for (i = sw.length - 15; i < sw.length; i++) s += sw[i][1];
      imax = s / 15 + iis;
      for (i = 0; i < sw.length; i++) { ie = sw[i][1] + iis; if (ie > 0.02 * imax && ie < 0.5 * imax) { xs.push(sw[i][0]); ys.push(Math.log(ie)); } }
      ab = lsq(xs, ys); te = ab[1] > 0 ? 1 / ab[1] : 0; vp = ab[1] > 0 ? (Math.log(imax) - ab[0]) / ab[1] : 0;
      ne = te > 0 ? iis / (Math.exp(-0.5) * QE * p.Ap * Math.sqrt(QE * te / (p.M * AMU))) : 0;
      return { Te: te, Vp: vp, ne: ne, Iis: iis, a: ab[0], imax: imax };
    },
    fitDouble: function (p, sw) {
      var i, s = 0, n = 0, sat, num = 0, den = 0, te, ne;
      for (i = 0; i < sw.length; i++) if (Math.abs(sw[i][0]) >= 25) { s += Math.abs(sw[i][1]); n++; }
      sat = n ? s / n : 0;
      for (i = 0; i < sw.length; i++) if (Math.abs(sw[i][1]) < 0.7 * sat) { num += sw[i][0] * atanh(sw[i][1] / sat); den += sw[i][0] * sw[i][0]; }
      te = num > 0 ? den / (2 * num) : 0;
      ne = te > 0 ? sat / (Math.exp(-0.5) * QE * p.Ap * Math.sqrt(QE * te / (p.M * AMU))) : 0;
      return { Te: te, ne: ne, Iis: sat };
    },
    fitEmissive: function (sw) { var s = 0, i; for (i = sw.length - 6; i < sw.length; i++) s += sw[i][1]; return s / 6; },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      return { t: s.t || 0, I: lang.single(p, p.V), Iis: lang.iis(p), Ies: lang.ies(p), Vf: p.Vp + p.Te * Math.log(lang.iis(p) / lang.ies(p)) };
    },
    measure: function (p) {
      var a = lang.fitSingle(p, lang.sweepSingle(p)), b = lang.fitDouble(p, lang.sweepDouble(p));
      return { Te: a.Te, Te_double: b.Te, Vp: a.Vp, ne: a.ne, ne_double: b.ne, Vp_emissive: lang.fitEmissive(lang.sweepEmissive(p)) };
    }
  };
  function atanh(x) { return 0.5 * Math.log((1 + x) / (1 - x)); }
  function phd_lang_te(p) { return p.Te; }
  function phd_lang_vp(p) { return p.Vp; }

  // ------------------------------------------------------------------ Paschen curve
  var paschen = {
    PARAMS: { A: 15.0, B: 365.0, gam: 0.01, noise: 0.003, seed: 41.0, pd: 1.0 },
    VARS: ['t', 'Vb', 'pdmin', 'Vmin'],
    NPT: 121,
    vb: function (p, pd) { var den = Math.log(p.A * pd) - Math.log(Math.log(1 + 1 / p.gam)); return den > 0 ? p.B * pd / den : 0; },
    grid: function (p) {
      var lo = Math.exp(1) * Math.log(1 + 1 / p.gam) / p.A * 0.3 * 1.6, out = [], i;
      for (i = 0; i < paschen.NPT; i++) out.push(lo * Math.exp(Math.log(300 / lo) * i / (paschen.NPT - 1)));
      return out;
    },
    scan: function (p) {
      var rnd = new Rnd(p.seed), g = paschen.grid(p), out = [], i;
      for (i = 0; i < g.length; i++) out.push([g[i], paschen.vb(p, g[i]) * (1 + p.noise * rnd.gauss())]);
      return out;
    },
    minimum: function (sc) {
      var k = 0, i, lo, hi, pts = [], n, xs = [], ys = [], m = 0, x, s0, s1 = 0, s2 = 0, s3 = 0, s4 = 0, t0 = 0, t1 = 0, t2 = 0, d, da, db, dc, a, b, c, x0;
      for (i = 0; i < sc.length; i++) if (sc[i][1] > 0 && (sc[k][1] <= 0 || sc[i][1] < sc[k][1])) k = i;
      lo = Math.max(0, k - 4); hi = Math.min(sc.length, k + 5);
      for (i = lo; i < hi; i++) if (sc[i][1] > 0) pts.push(sc[i]);
      n = pts.length;
      for (i = 0; i < n; i++) { xs.push(Math.log(pts[i][0])); ys.push(pts[i][1]); }
      m = mean(xs);
      for (i = 0; i < n; i++) xs[i] = xs[i] - m;
      s0 = n;
      for (i = 0; i < n; i++) {
        x = xs[i]; s1 += x; s2 += x * x; s3 += x * x * x; s4 += x * x * x * x;
        t0 += ys[i]; t1 += x * ys[i]; t2 += x * x * ys[i];
      }
      d = s0 * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2);
      if (d === 0) return [sc[k][0], sc[k][1]];
      da = t0 * (s2 * s4 - s3 * s3) - s1 * (t1 * s4 - s3 * t2) + s2 * (t1 * s3 - s2 * t2);
      db = s0 * (t1 * s4 - s3 * t2) - t0 * (s1 * s4 - s3 * s2) + s2 * (s1 * t2 - t1 * s2);
      dc = s0 * (s2 * t2 - t1 * s3) - s1 * (s1 * t2 - t1 * s2) + t0 * (s1 * s3 - s2 * s2);
      a = da / d; b = db / d; c = dc / d;
      if (c <= 0) return [sc[k][0], sc[k][1]];
      x0 = -b / (2 * c);
      return [Math.exp(x0 + m), a + b * x0 + c * x0 * x0];
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var e = Math.exp(1) * Math.log(1 + 1 / p.gam) / p.A;
      return { t: s.t || 0, Vb: paschen.vb(p, p.pd), pdmin: e, Vmin: p.B * e };
    },
    measure: function (p) { var mn = paschen.minimum(paschen.scan(p)); return { pdmin: mn[0], Vmin: mn[1] }; }
  };
  function phd_paschen_vmin(p) { return Math.exp(1) * p.B * Math.log(1 + 1 / p.gam) / p.A; }

  // ------------------------------------------------------------------ optical tweezers
  var tweezers = {
    PARAMS: { a: 5.0e-7, eta: 1.0e-3, T: 295.0, kp: 2.0e-6, P: 5.0, fs: 5000.0, N: 262144.0, seg: 2048.0, nseg: 32.0, v: 1.0e-4, Td: 10.0, seed: 71.0 },
    VARS: ['t', 'kappa', 'fc', 'gamma', 'xrms'],
    gamma: function (p) { return 6 * PI * p.eta * p.a; },
    kappa: function (p) { return p.kp * p.P; },
    record: function (p, n, seedAdd, drift) {
      var k = tweezers.kappa(p), tau = tweezers.gamma(p) / k, dt = 1 / p.fs, a = Math.exp(-dt / tau), sd = Math.sqrt(KB * p.T / k * (1 - a * a)),
        rnd = new Rnd(p.seed + seedAdd), x = Math.sqrt(KB * p.T / k) * rnd.gauss(), out = [], i;
      for (i = 0; i < n; i++) { x = a * x + sd * rnd.gauss(); out.push(x + drift); }
      return out;
    },
    spectrum: function (p, xs, nseg) {
      var sg = Math.floor(p.seg), ns = nseg === undefined || nseg === null ? Math.floor(p.nseg) : nseg, win = [], sw2 = 0, acc = zeros(sg / 2), s, i, k, m, re, im, out = [];
      ns = Math.min(ns, Math.floor(xs.length / sg));
      for (i = 0; i < sg; i++) win.push(0.5 - 0.5 * Math.cos(2 * PI * i / sg));
      for (i = 0; i < sg; i++) sw2 += win[i] * win[i];
      for (s = 0; s < ns; s++) {
        m = mean(xs.slice(s * sg, (s + 1) * sg)); re = []; im = zeros(sg);
        for (i = 0; i < sg; i++) re.push((xs[s * sg + i] - m) * win[i]);
        fft(re, im, false);
        for (k = 1; k < sg / 2; k++) acc[k] += re[k] * re[k] + im[k] * im[k];
      }
      for (k = 1; k < sg / 2; k++) out.push([k * p.fs / sg, 2 * acc[k] / (ns * p.fs * sw2)]);
      return out;
    },
    corner: function (sp, fs) {
      var c0 = 1 / sp[0][1], c1 = -0.5 * c0, it, i, s11, s12, s22, r1, r2, u, mod, w, y, d, q, a;
      if (fs === undefined) fs = 5000;
      for (it = 0; it < 5; it++) {
        s11 = 0; s12 = 0; s22 = 0; r1 = 0; r2 = 0;
        for (i = 0; i < sp.length; i++) {
          u = Math.cos(2 * PI * sp[i][0] / fs); mod = 1 / (c0 + c1 * u); if (mod <= 0) mod = sp[i][1];
          w = mod * mod; y = 1 / sp[i][1];
          s11 += w; s12 += w * u; s22 += w * u * u; r1 += w * y; r2 += w * u * y;
        }
        d = s11 * s22 - s12 * s12;
        if (d === 0) break;
        c0 = (r1 * s22 - r2 * s12) / d; c1 = (s11 * r2 - s12 * r1) / d;
      }
      if (c1 >= 0 || c0 <= 0) return 0;
      q = c0 / (-c1);
      if (q <= 1) return 0;
      a = q - Math.sqrt(q * q - 1);
      return -Math.log(a) * fs / (2 * PI);
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var k = tweezers.kappa(p), g = tweezers.gamma(p); return { t: s.t || 0, kappa: k, fc: k / (2 * PI * g), gamma: g, xrms: Math.sqrt(KB * p.T / k) }; },
    measure: function (p) {
      var n = Math.floor(p.N), xs = tweezers.record(p, n, 0, 0), m = mean(xs), x2 = 0, i, kEq, fc, g, nd, xd, kDr;
      for (i = 0; i < xs.length; i++) x2 += (xs[i] - m) * (xs[i] - m);
      x2 = x2 / xs.length; kEq = KB * p.T / x2;
      fc = tweezers.corner(tweezers.spectrum(p, xs), p.fs); g = tweezers.gamma(p);
      nd = Math.floor(p.Td * p.fs); xd = mean(tweezers.record(p, nd, 1, g * p.v / tweezers.kappa(p))) - m;
      kDr = xd > 0 ? g * p.v / xd : 0;
      return { k_eq: kEq, k_eq_u: kEq * 1.0e6, k_psd: 2 * PI * g * fc, k_drag: kDr, fc: fc, kB_est: kDr * x2 / p.T, eta_est: fc > 0 ? kEq / (2 * PI * fc * 6 * PI * p.a) : 0 };
    }
  };
  function phd_tw_kappa(p) { return p.kp * p.P * 1.0e6; }

  H0.register({
    K: { phd_lockin: lockin, phd_johnson: johnson, phd_shot: shot, phd_psd: psd, phd_boxcar: boxcar, phd_g2: g2k,
      phd_poisson: poisson, phd_antibunch: antibunch, phd_fp: fp, phd_langmuir: lang, phd_paschen: paschen, phd_tweezers: tweezers },
    TEXTBOOK: { phd_lockin_A: phd_lockin_A, phd_o_kB: phd_kB, phd_o_qe: phd_qe, phd_psd_floor: phd_psd_floor,
      phd_boxcar_tau: phd_boxcar_tau, phd_g2_zero: phd_g2_zero, phd_poisson_gap: phd_poisson_gap,
      phd_antibunch_alpha: phd_antibunch_alpha, phd_fp_finesse: phd_fp_finesse, phd_lang_te: phd_lang_te,
      phd_lang_vp: phd_lang_vp, phd_paschen_vmin: phd_paschen_vmin, phd_tw_kappa: phd_tw_kappa },
    CALCS: {}
  });
})(typeof window !== 'undefined' ? window : this);
