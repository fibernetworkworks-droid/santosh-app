/* Kernel pack `ph3_nuc`: the exact JavaScript twin of app/prayog/packs/ph3_nuc.py - PhD / M.Sc. benches of nuclear,
   particle and cosmic-ray physics and of astrophysical data analysis. Same formulas, same algorithms, same numbers
   (the server's tests run both and compare). Deterministic: every counting or noisy process comes from a Lehmer
   generator seeded by the lab's own `seed`, never the clock. The transit light curve and the 21 cm spectra are
   SIMULATED from a stated model. */
(function (root) {
  'use strict';
  var H0 = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, C = 2.99792458e8, ME_KEV = 510.99895, RE = 2.8179403262e-15, FWHM_K = 2.3548200450309493;
  var G_SI = 6.6743e-11;

  function lin(pts) {
    var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, d, m;
    if (n < 2) return [0, 0];
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    d = n * sxx - sx * sx;
    if (d === 0) return [0, 0];
    m = (n * sxy - sx * sy) / d;
    return [m, (sy - m * sx) / n];
  }
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0; }
  function sumOf(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return s; }
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
  function R(seed) { var s = Math.floor(Math.abs(seed)) % 2147483646; this.s = s + 1; }
  R.prototype.next = function () { this.s = (this.s * 16807) % 2147483647; return this.s / 2147483647; };
  R.prototype.poisson = function (m) {
    if (m <= 0) return 0;
    if (m > 400) { var kk = Math.floor(m / 400) + 1, total = 0, j;
      for (j = 0; j < kk; j++) total += this.poisson(m / kk);
      return total; }
    var lim = Math.exp(-m), k = 0, p = 1;
    for (;;) { p *= this.next(); if (p <= lim) return k; k += 1; if (k > 100000) return k; }
  };
  R.prototype.gauss = function () {
    var u1 = this.next(), u2 = this.next();
    if (u1 < 1e-12) u1 = 1e-12;
    return Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * PI * u2);
  };

  // ============================================================ coincidence bench
  var ph3_coinc = {
    PARAMS: { A1: 1.5e5, A2: 1.2e5, b1: 100.0, b2: 80.0, tau: 3.0e-8, k: 1.0, Rt: 0.0, t: 10.0, seed: 31.0, j: 0.0 },
    VARS: ['t', 'r1', 'r2', 'rc', 'acc'],
    r1: function (p) { return p.A1 + p.b1; },
    r2: function (p) { return p.A2 + p.b2; },
    acc: function (p) { return 2.0 * p.k * p.tau * ph3_coinc.r1(p) * ph3_coinc.r2(p); },
    rc: function (p) { return p.Rt + ph3_coinc.acc(p); },
    counts: function (p) {
      var rnd = new R(p.seed + 977.0 * p.j), t = Math.max(p.t, 0.0);
      var a = rnd.poisson(ph3_coinc.r1(p) * t), b = rnd.poisson(ph3_coinc.r2(p) * t), c = rnd.poisson(ph3_coinc.rc(p) * t);
      return [a, b, c];
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, r1: ph3_coinc.r1(p), r2: ph3_coinc.r2(p), rc: ph3_coinc.rc(p), acc: ph3_coinc.acc(p) }; },
    fit: function (rows) {
      if (rows.length < 2) return { tau: 0.0, Rt: 0.0 };
      var pts = [], rr = [], i, mc;
      for (i = 0; i < rows.length; i++) { pts.push([rows[i][0], rows[i][3]]); rr.push(rows[i][1] * rows[i][2]); }
      mc = lin(pts);
      var m = mean(rr);
      return { tau: m > 0 ? mc[0] / (2.0 * m) : 0.0, Rt: mc[1] };
    },
    measure: function (p) {
      var rows = [], ks = [1.0, 2.0, 3.0, 4.0], i, q, f;
      for (i = 0; i < ks.length; i++) { q = cp(p); q.k = ks[i]; rows.push([ks[i], ph3_coinc.r1(q), ph3_coinc.r2(q), ph3_coinc.rc(q)]); }
      f = ph3_coinc.fit(rows);
      return { tau_fit: f.tau, Rt_fit: f.Rt, rc: ph3_coinc.rc(p), r1: ph3_coinc.r1(p), r2: ph3_coinc.r2(p) };
    }
  };
  function coinc_tau(p) { return p.tau; }
  function coinc_rt(p) { return p.Rt; }

  // ============================================================ Compton scattering
  var ph3_compton = {
    PARAMS: { E0: 661.657, Ig: 0.851, act: 3.7e7, D: 0.25, Dd: 0.30, rad: 0.0254, ne25: 2.77, th: 90.0, gain: 2.0,
      off: 0.0, nch: 512.0, R662: 0.075, pf662: 0.35, et662: 0.55, kE: 0.6, t: 600.0, bg: 0.01, seed: 17.0, task: 0.0, j: 0.0, coin: 0.0 },
    VARS: ['t', 'Ep', 'dsig', 'rate', 'fwhm'],
    CAL_AM: 59.5409,
    ANGLES: [20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0],
    eprime: function (e0, th) { return e0 / (1.0 + (e0 / ME_KEV) * (1.0 - Math.cos(th * PI / 180.0))); },
    kn: function (e0, thd) {
      var th = thd * PI / 180.0, r = 1.0 / (1.0 + (e0 / ME_KEV) * (1.0 - Math.cos(th))), s2 = Math.pow(Math.sin(th), 2);
      return 0.5 * RE * RE * r * r * (r + 1.0 / r - s2);
    },
    kn_total: function (e0) {
      var a = e0 / ME_KEV, l = Math.log(1.0 + 2.0 * a);
      return 2.0 * PI * RE * RE * ((1.0 + a) / (a * a) * (2.0 * (1.0 + a) / (1.0 + 2.0 * a) - l / a) +
        l / (2.0 * a) - (1.0 + 3.0 * a) / Math.pow(1.0 + 2.0 * a, 2));
    },
    fwhm: function (e, p) { return p.R662 * Math.sqrt(662.0 * e); },
    pf: function (e, p) { return 1.0 / (1.0 + (e / 662.0) * (1.0 / p.pf662 - 1.0)); },
    et: function (e, p) { return Math.min(0.98, p.et662 * Math.pow(662.0 / e, p.kE)); },
    eff: function (e, p) { return ph3_compton.et(e, p) * ph3_compton.pf(e, p); },
    omega: function (p) { return PI * p.rad * p.rad / (p.Dd * p.Dd); },
    flux: function (p) { return p.act * p.Ig / (4.0 * PI * p.D * p.D); },
    npk: function (p) {
      var K = ph3_compton, ep = K.eprime(p.E0, p.th);
      return p.t * K.flux(p) * p.ne25 * 1e25 * K.kn(p.E0, p.th) * K.omega(p) * K.eff(ep, p);
    },
    line_spec: function (p, e, npk) {
      var K = ph3_compton, n = Math.round(p.nch), gain = p.gain, off = p.off, ex = [], i, j, x;
      for (i = 0; i < n; i++) ex.push(p.bg * (1.0 - 0.98 * p.coin) * p.t * gain);
      var s2pi = Math.sqrt(2.0 * PI), sg0 = K.fwhm(e, p) / FWHM_K;
      var lo = Math.max(0, Math.floor((e - off) / gain - 6.0 * sg0 / gain)), hi = Math.min(n - 1, Math.floor((e - off) / gain + 6.0 * sg0 / gain) + 1);
      for (i = lo; i <= hi; i++) { x = off + gain * (i + 0.5) - e; ex[i] += npk * gain * Math.exp(-0.5 * Math.pow(x / sg0, 2)) / (sg0 * s2pi); }
      var pfv = K.pf(e, p), ncomp = npk * (1.0 - pfv) / pfv, al = e / ME_KEV, emin = 1.0 / (1.0 + 2.0 * al), raw = [], tot = 0.0, tj, eps, cs, f;
      for (j = 0; j < n; j++) raw.push(0.0);
      for (j = 0; j < n; j++) {
        tj = off + gain * (j + 0.5); eps = 1.0 - tj / e;
        if (eps < emin || eps >= 1.0) continue;
        cs = 1.0 - (1.0 / eps - 1.0) / al; f = eps + 1.0 / eps - (1.0 - cs * cs);
        raw[j] = f; tot += f;
      }
      if (tot > 0) for (j = 0; j < n; j++) if (raw[j] > 0) ex[j] += ncomp * raw[j] / tot;
      return ex;
    },
    expected: function (p) { var K = ph3_compton; return K.line_spec(p, K.eprime(p.E0, p.th), K.npk(p)); },
    direct: function (p, e, n) { return ph3_compton.line_spec(p, e, n); },
    counts: function (ex, seed) { var rnd = new R(seed), out = [], i; for (i = 0; i < ex.length; i++) out.push(rnd.poisson(ex[i])); return out; },
    find_peak: function (c, p) {
      var n = c.length, sm = [], i, vm = -1.0, i0 = 8;
      for (i = 0; i < n; i++) sm.push(0.0);
      for (i = 3; i < n - 3; i++) sm[i] = (c[i - 3] + c[i - 2] + c[i - 1] + c[i] + c[i + 1] + c[i + 2] + c[i + 3]) / 7.0;
      for (i = 8; i < n - 4; i++) if (sm[i] > vm) { vm = sm[i]; i0 = i; }
      var far = Math.min(n - 4, i0 + 40), hb = far > i0 ? sm[far] : 0.0, half = hb + 0.5 * (vm - hb);
      var a = i0; while (a > 3 && sm[a] > half) a -= 1;
      var b = i0; while (b < n - 4 && sm[b] > half) b += 1;
      var w = Math.max(3.0, b - a), sd = w / FWHM_K;
      var lo = Math.max(4, Math.floor(i0 - 3.0 * sd)), hi = Math.min(n - 5, Math.floor(i0 + 3.0 * sd + 0.999));
      var blk = Math.max(3, Math.floor(sd));
      var l0 = Math.max(blk, lo - 2 * blk) + Math.floor(blk / 2), r0 = Math.min(n - blk - 1, hi + 2 * blk) - Math.floor(blk / 2);
      var bl = 0.0, br = 0.0;
      for (i = l0 - blk; i <= l0 + blk; i++) bl += c[i];
      for (i = r0 - blk; i <= r0 + blk; i++) br += c[i];
      bl /= (2 * blk + 1); br /= (2 * blk + 1);
      var xl = l0, xr = r0, s = 0.0, sx = 0.0, base, y;
      for (i = lo; i <= hi; i++) {
        base = xr !== xl ? bl + (br - bl) * (i - xl) / (xr - xl) : bl;
        y = c[i] - base; s += y; sx += y * (i + 0.5);
      }
      return { ch: s > 0 ? sx / s : i0 + 0.5, fwhm_ch: w, area: s / 0.9973, i0: i0 };
    },
    calibrate: function (p) {
      var K = ph3_compton, na = 2.0e4;
      var ca = K.find_peak(K.direct(p, K.CAL_AM, na), p), cb = K.find_peak(K.direct(p, p.E0, na), p);
      var b = (p.E0 - K.CAL_AM) / (cb.ch - ca.ch);
      return [K.CAL_AM - b * ca.ch, b];
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var K = ph3_compton, ep = K.eprime(p.E0, p.th);
      return { t: s.t || 0.0, Ep: ep, dsig: K.kn(p.E0, p.th), rate: K.npk(p) / Math.max(p.t, 1e-9), fwhm: K.fwhm(ep, p) };
    },
    card: function (p) { var out = [], i, e; for (i = 0; i < 27; i++) { e = 50.0 + 25.0 * i; out.push([e, ph3_compton.eff(e, p)]); } return out; },
    eff_card: function (card, e) {
      var i, x0, x1, y0, y1;
      if (e <= card[0][0]) return card[0][1];
      for (i = 1; i < card.length; i++) if (e <= card[i][0]) {
        x0 = Math.log(card[i - 1][0]); x1 = Math.log(card[i][0]); y0 = Math.log(card[i - 1][1]); y1 = Math.log(card[i][1]);
        return Math.exp(y0 + (y1 - y0) * (Math.log(e) - x0) / (x1 - x0));
      }
      return card[card.length - 1][1];
    },
    analyse: function (p, peaks) {
      var K = ph3_compton, i, pts = [];
      if (peaks.length < 3) return { mc2: 0.0, sigma: 0.0, ratio: 0.0 };
      for (i = 0; i < peaks.length; i++) pts.push([1.0 - Math.cos(peaks[i][0] * PI / 180.0), 1.0 / peaks[i][1]]);
      var m = lin(pts)[0], card = K.card(p), pref = p.t * K.flux(p) * p.ne25 * 1e25 * K.omega(p), ds = [], ratios = [];
      for (i = 0; i < peaks.length; i++) { ds.push(peaks[i][2] / (pref * K.eff_card(card, peaks[i][1]))); ratios.push(ds[i] / K.kn(p.E0, peaks[i][0])); }
      var rm = mean(ratios), srt = [];
      for (i = 0; i < peaks.length; i++) srt.push([peaks[i][0], ds[i]]);
      srt.sort(function (a, b) { return a[0] - b[0]; });
      var tot = 0.0, f0, f1, a, nend = 40, k;
      for (i = 1; i < srt.length; i++) {
        f0 = Math.sin(srt[i - 1][0] * PI / 180.0) * srt[i - 1][1]; f1 = Math.sin(srt[i][0] * PI / 180.0) * srt[i][1];
        tot += 0.5 * (f0 + f1) * (srt[i][0] - srt[i - 1][0]) * PI / 180.0;
      }
      var amin = srt[0][0], amax = srt[srt.length - 1][0];
      for (k = 0; k < nend; k++) {
        a = amin * (k + 0.5) / nend;
        tot += rm * K.kn(p.E0, a) * Math.sin(a * PI / 180.0) * (amin / nend) * PI / 180.0;
        a = amax + (180.0 - amax) * (k + 0.5) / nend;
        tot += rm * K.kn(p.E0, a) * Math.sin(a * PI / 180.0) * ((180.0 - amax) / nend) * PI / 180.0;
      }
      return { mc2: m > 0 ? 1.0 / m : 0.0, sigma: 2.0 * PI * tot / 1e-28, ratio: rm };
    },
    measure: function (p) {
      var K = ph3_compton, cal = K.calibrate(p), peaks = [], i, q, pk;
      for (i = 0; i < K.ANGLES.length; i++) {
        q = cp(p); q.th = K.ANGLES[i]; pk = K.find_peak(K.expected(q), q);
        peaks.push([K.ANGLES[i], cal[0] + cal[1] * pk.ch, pk.area]);
      }
      var r = K.analyse(p, peaks);
      return { mc2: r.mc2, sigma: r.sigma, ratio: r.ratio, Ep: K.eprime(p.E0, p.th) };
    }
  };
  function compton_mc2() { return ME_KEV; }
  function compton_sigma(p) { return ph3_compton.kn_total(p.E0) / 1e-28; }

  // ============================================================ alpha spectrometry
  var ph3_alpha = {
    PARAMS: { src: 0.0, pr: 0.0, d: 0.03, tf: 0.0, Af: 197.0, a: 0.318, w0: 18.0, ks: 30.0, gain: 5.0, off: 0.0,
      nch: 1200.0, rate: 400.0, t: 120.0, bg: 0.0005, seed: 41.0 },
    VARS: ['t', 'E1', 'x', 'fwhm'],
    LINES: [[[5485.56, 0.848], [5442.80, 0.131], [5388.23, 0.0166]], [[5156.59, 0.7077], [5144.3, 0.1711], [5105.5, 0.1194]]],
    lines: function (p) { var i = Math.round(p.src), L = ph3_alpha.LINES; return L[i < 0 ? 0 : (i >= L.length ? L.length - 1 : i)]; },
    xair: function (p) {
      var foil = p.tf > 0 ? p.tf / (0.56 * Math.pow(p.Af, 1.0 / 3.0)) : 0.0;
      return p.d * 100.0 * p.pr / 1013.25 + foil;
    },
    energy: function (e0, x, a) { var e = e0 / 1000.0, r = Math.pow(e, 1.5) - x / a; return r > 0 ? 1000.0 * Math.pow(r, 2.0 / 3.0) : 0.0; },
    fwhm: function (p) { return Math.sqrt(p.w0 * p.w0 + p.ks * p.ks * ph3_alpha.xair(p)); },
    expected: function (p) {
      var K = ph3_alpha, n = Math.round(p.nch), gain = p.gain, off = p.off, ex = [], i, l, ls = K.lines(p);
      for (i = 0; i < n; i++) ex.push(p.bg * p.t * gain);
      var x = K.xair(p), sg = K.fwhm(p) / FWHM_K, s2pi = Math.sqrt(2.0 * PI), geo = Math.pow(0.03 / p.d, 2), e, area, lo, hi, xx;
      for (l = 0; l < ls.length; l++) {
        e = K.energy(ls[l][0], x, p.a);
        if (e <= 0.0) continue;
        area = p.rate * geo * p.t * ls[l][1];
        lo = Math.max(0, Math.floor((e - off) / gain - 6.0 * sg / gain)); hi = Math.min(n - 1, Math.floor((e - off) / gain + 6.0 * sg / gain) + 1);
        for (i = lo; i <= hi; i++) { xx = off + gain * (i + 0.5) - e; ex[i] += area * gain * Math.exp(-0.5 * Math.pow(xx / sg, 2)) / (sg * s2pi); }
      }
      return ex;
    },
    counts: function (p, k) { var rnd = new R(p.seed + 977.0 * (k || 0)), ex = ph3_alpha.expected(p), out = [], i; for (i = 0; i < ex.length; i++) out.push(rnd.poisson(ex[i])); return out; },
    find_peak: function (c, p) {
      var n = c.length, sm = [], i, vm = -1.0, i0 = 6;
      for (i = 0; i < n; i++) sm.push(0.0);
      for (i = 2; i < n - 2; i++) sm[i] = (c[i - 2] + c[i - 1] + c[i] + c[i + 1] + c[i + 2]) / 5.0;
      for (i = 6; i < n - 3; i++) if (sm[i] > vm) { vm = sm[i]; i0 = i; }
      var half = 0.5 * vm, a = i0, b = i0;
      while (a > 3 && sm[a] > half) a -= 1;
      while (b < n - 4 && sm[b] > half) b += 1;
      var xa = sm[a + 1] !== sm[a] ? a + (half - sm[a]) / (sm[a + 1] - sm[a]) : a;
      var xb = sm[b - 1] !== sm[b] ? b - 1 + (sm[b - 1] - half) / (sm[b - 1] - sm[b]) : b;
      var w = Math.max(2.0, xb - xa), lo = Math.max(2, Math.floor(i0 - 1.5 * w)), hi = Math.min(n - 3, Math.floor(i0 + 1.5 * w + 0.999)), s = 0.0, sx = 0.0;
      for (i = lo; i <= hi; i++) { s += c[i]; sx += c[i] * (i + 0.5); }
      return { ch: s > 0 ? sx / s : i0 + 0.5, fwhm_ch: w, area: s, i0: i0 };
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var K = ph3_alpha, ln = K.lines(p)[0], x = K.xair(p);
      return { t: s.t || 0.0, E1: K.energy(ln[0], x, p.a), x: x, fwhm: K.fwhm(p) };
    },
    range_fit: function (pts) {
      var q = [], i;
      for (i = 0; i < pts.length; i++) if (pts[i][1] > 0) q.push([pts[i][0], Math.pow(pts[i][1], 1.5)]);
      var mc = lin(q);
      return mc[0] < 0 ? -mc[1] / mc[0] : 0.0;
    },
    measure: function (p) {
      var K = ph3_alpha, cal = [], s_i, q, pk, i, pts = [], prs = [0, 100, 200, 300, 400, 500, 600, 700];
      for (s_i = 0; s_i < 2; s_i++) {
        q = cp(p); q.src = s_i; q.pr = 0.0; q.tf = 0.0;
        pk = K.find_peak(K.expected(q), q);
        cal.push([pk.ch, K.LINES[s_i][0][0]]);
      }
      var b = (cal[0][1] - cal[1][1]) / (cal[0][0] - cal[1][0]), a0 = cal[0][1] - b * cal[0][0];
      for (i = 0; i < prs.length; i++) {
        q = cp(p); q.pr = prs[i]; q.tf = 0.0;
        pk = K.find_peak(K.expected(q), q);
        pts.push([q.d * 100.0 * prs[i] / 1013.25, (a0 + b * pk.ch) / 1000.0]);
      }
      var q0 = cp(p); q0.pr = 0.0; q0.tf = 0.0;
      return { range: K.range_fit(pts), res: K.fwhm(q0), E0: pts[0][1] };
    }
  };
  function alpha_range(p) { return p.a * Math.pow(ph3_alpha.lines(p)[0][0] / 1000.0, 1.5); }

  // ============================================================ muon lifetime
  var ph3_muon = {
    PARAMS: { tp: 2.1969811, tm: 2.026, r: 1.27, Rs: 150.0, bgr: 0.03, T0: 0.4, dt: 1.0, nb: 24.0, h: 12.0, j: 0.0, seed: 53.0, tfit: 12.5, nbg: 5.0 },
    VARS: ['t', 'n', 'tau'],
    expected: function (p, hours) {
      var hh = (hours === undefined || hours < 0) ? p.h : hours, wp = 1.0 / (1.0 + p.r), wm = p.r / (1.0 + p.r), out = [], i, t0, t1, sig;
      for (i = 0; i < Math.round(p.nb); i++) {
        t0 = p.T0 + i * p.dt; t1 = t0 + p.dt;
        sig = wp * (Math.exp(-t0 / p.tp) - Math.exp(-t1 / p.tp)) + wm * (p.tm / p.tp) * (Math.exp(-t0 / p.tm) - Math.exp(-t1 / p.tm));
        out.push(p.Rs * hh * sig + p.bgr * hh * p.dt);
      }
      return out;
    },
    chunk: function (p) { var rnd = new R(p.seed + 977.0 * p.j), ex = ph3_muon.expected(p), out = [], i; for (i = 0; i < ex.length; i++) out.push(rnd.poisson(ex[i])); return out; },
    fit_life: function (c, p) {
      var nb = c.length, nbg = Math.round(p.nbg), bgv = 0.0, i, tc, y, w, ly, sw = 0, swx = 0, swy = 0, swxx = 0, swxy = 0, tot = 0;
      if (nbg > 0 && nb > nbg) { for (i = nb - nbg; i < nb; i++) bgv += c[i]; bgv /= nbg; }
      for (i = 0; i < nb; i++) tot += c[i];
      for (i = 0; i < nb; i++) {
        tc = p.T0 + (i + 0.5) * p.dt;
        if (tc > p.tfit) break;
        y = c[i] - bgv;
        if (y <= 0.0 || c[i] <= 0.0) continue;
        w = y * y / c[i]; ly = Math.log(y);
        sw += w; swx += w * tc; swy += w * ly; swxx += w * tc * tc; swxy += w * tc * ly;
      }
      var d = sw * swxx - swx * swx;
      if (d === 0.0 || sw === 0.0) return { tau: 0.0, bg: bgv, n: 0.0 };
      var m = (sw * swxy - swx * swy) / d;
      return { tau: m < 0 ? -1.0 / m : 0.0, bg: bgv, n: tot };
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var ex = ph3_muon.expected(p); return { t: s.t || 0.0, n: sumOf(ex), tau: ph3_muon.fit_life(ex, p).tau }; },
    measure: function (p) { var f = ph3_muon.fit_life(ph3_muon.expected(p), p); return { tau_fit: f.tau, bg: f.bg, tau_free: p.tp }; }
  };
  function muon_free(p) { return p.tp; }

  // ============================================================ transit light curve
  var ph3_transit = {
    PARAMS: { P: 3.2, k: 0.1, b: 0.3, rho: 1410.0, u: 0.0, t0: 1.3, sig: 4.0e-4, cad: 0.0069444, span: 27.4, seed: 61.0, tr: 0.0 },
    VARS: ['t', 'depth', 'dur', 'aRs'],
    NRING: 60,
    ars: function (p) { var per = p.P * 86400.0; return Math.pow(G_SI * p.rho * per * per / (3.0 * PI), 1.0 / 3.0); },
    dur: function (p) {
      var a = ph3_transit.ars(p), arg = Math.sqrt(Math.max(Math.pow(1.0 + p.k, 2) - p.b * p.b, 0.0)) / Math.sqrt(Math.max(a * a - p.b * p.b, 1e-12));
      return p.P / PI * Math.asin(Math.min(1.0, arg));
    },
    blocked: function (z, k, u) {
      if (z >= 1.0 + k) return 0.0;
      var n = ph3_transit.NRING, rmin = Math.max(0.0, z - k), rmax = Math.min(1.0, z + k);
      if (rmax <= rmin) return 0.0;
      var dr = (rmax - rmin) / n, tot = 0.0, i, r, arc, cs, mu;
      for (i = 0; i < n; i++) {
        r = rmin + (i + 0.5) * dr;
        if (r <= 0.0) continue;
        if (z < 1e-12) arc = r < k ? 2.0 * PI * r : 0.0;
        else if (r + z <= k) arc = 2.0 * PI * r;
        else { cs = (r * r + z * z - k * k) / (2.0 * r * z); cs = cs < -1.0 ? -1.0 : (cs > 1.0 ? 1.0 : cs); arc = 2.0 * r * Math.acos(cs); }
        mu = Math.sqrt(Math.max(0.0, 1.0 - r * r));
        tot += (1.0 - u * (1.0 - mu)) * arc * dr;
      }
      return tot / (PI * (1.0 - u / 3.0));
    },
    flux: function (p, t) {
      var a = ph3_transit.ars(p), ph = 2.0 * PI * (t - p.t0) / p.P, cpv = Math.cos(ph);
      if (cpv <= 0.0) return 1.0;
      var ci = p.b / a, z = a * Math.sqrt(Math.pow(Math.sin(ph), 2) + Math.pow(ci * cpv, 2));
      return 1.0 - ph3_transit.blocked(z, p.k, p.u);
    },
    times: function (p) { var n = Math.floor(p.span / p.cad), out = [], i; for (i = 0; i < n; i++) out.push((i + 0.5) * p.cad); return out; },
    curve: function (p, noise) {
      var rnd = new R(p.seed), ts = ph3_transit.times(p), out = [], i, f;
      for (i = 0; i < ts.length; i++) { f = ph3_transit.flux(p, ts[i]); if (noise) f += p.sig * rnd.gauss(); out.push(f); }
      return out;
    },
    bls: function (t, f, p0, p1, step, nbin) {
      nbin = nbin || 160;
      var n = t.length, mn = mean(f), out = [], npg = Math.floor((p1 - p0) / step + 0.5) + 1, mmax = Math.max(2, Math.floor(0.14 * nbin));
      var ip, i, per, sm, ct, ph, b, best, s0, sin, nin, m, j, pw;
      for (ip = 0; ip < npg; ip++) {
        per = p0 + ip * step; sm = []; ct = [];
        for (b = 0; b < nbin; b++) { sm.push(0.0); ct.push(0); }
        for (i = 0; i < n; i++) {
          ph = t[i] / per; ph -= Math.floor(ph); b = Math.floor(ph * nbin);
          if (b >= nbin) b = nbin - 1;
          sm[b] += f[i] - mn; ct[b] += 1;
        }
        best = 0.0;
        for (s0 = 0; s0 < nbin; s0++) {
          sin = 0.0; nin = 0;
          for (m = 1; m <= mmax; m++) {
            j = (s0 + m - 1) % nbin; sin += sm[j]; nin += ct[j];
            if (nin > 0 && n - nin > 0) { pw = sin * sin * n / (nin * (n - nin)); if (sin < 0 && pw > best) best = pw; }
          }
        }
        out.push([per, best]);
      }
      return out;
    },
    best_period: function (t, f) {
      var K = ph3_transit, c = K.bls(t, f, 0.8, 14.0, 0.02), i, bi = 0, pk, fi, bj = 0;
      for (i = 1; i < c.length; i++) if (c[i][1] > c[bi][1]) bi = i;
      pk = c[bi][0]; fi = K.bls(t, f, pk - 0.04, pk + 0.04, 0.0005, 400);
      for (i = 1; i < fi.length; i++) if (fi[i][1] > fi[bj][1]) bj = i;
      return fi[bj][0];
    },
    fold: function (t, f, per, tref, half, nb) {
      var s = [], c = [], i, b, x, out = [];
      for (b = 0; b < nb; b++) { s.push(0.0); c.push(0); }
      for (i = 0; i < t.length; i++) {
        x = (t[i] - tref) / per; x = (x - Math.floor(x + 0.5)) * per;
        if (-half <= x && x < half) { b = Math.floor((x + half) / (2.0 * half) * nb); b = b >= nb ? nb - 1 : b; s[b] += f[i]; c[b] += 1; }
      }
      for (b = 0; b < nb; b++) out.push([-half + (b + 0.5) * (2.0 * half / nb), c[b] ? s[b] / c[b] : 1.0, c[b]]);
      return out;
    },
    depth_of: function (fold, tdur) {
      var sm = 0.0, n = 0.0, i;
      for (i = 0; i < fold.length; i++) if (Math.abs(fold[i][0]) <= 0.25 * tdur && fold[i][2] > 0) { sm += fold[i][1] * fold[i][2]; n += fold[i][2]; }
      return n > 0 ? 1.0 - sm / n : 0.0;
    },
    duration_of: function (fold, depth) {
      var best = 1e30, bd = 0.0, i, fi, frs = [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5], dur, ing, ss, ax, m, q;
      for (i = 1; i < 80; i++) {
        dur = 0.02 + i * 0.004;
        for (fi = 0; fi < frs.length; fi++) {
          ing = frs[fi] * dur; ss = 0.0;
          for (q = 0; q < fold.length; q++) {
            ax = Math.abs(fold[q][0]);
            if (ax >= dur / 2) m = 1.0;
            else if (ax <= dur / 2 - ing) m = 1.0 - depth;
            else m = 1.0 - depth * (dur / 2 - ax) / ing;
            ss += fold[q][2] * (fold[q][1] - m) * (fold[q][1] - m);
          }
          if (ss < best) { best = ss; bd = dur; }
        }
      }
      return bd;
    },
    epoch: function (t, f, per) {
      var nb = 240, sm = [], ct = [], i, b, ph, w, best = 1e30, bj = 0, j, m, k, s_, n_, v, tref, it, sx, sw, x, wt;
      for (b = 0; b < nb; b++) { sm.push(0.0); ct.push(0); }
      for (i = 0; i < t.length; i++) { ph = t[i] / per; ph -= Math.floor(ph); b = Math.min(nb - 1, Math.floor(ph * nb)); sm[b] += f[i]; ct[b] += 1; }
      w = Math.max(3, Math.floor(0.08 * nb));
      for (j = 0; j < nb; j++) {
        s_ = 0.0; n_ = 0;
        for (m = 0; m < w; m++) { k = (j + m) % nb; s_ += sm[k]; n_ += ct[k]; }
        v = n_ > 0 ? s_ / n_ : 1e30;
        if (v < best) { best = v; bj = j; }
      }
      tref = ((bj + 0.5 * w) % nb) / nb * per;
      for (it = 0; it < 2; it++) {
        sx = 0.0; sw = 0.0;
        for (i = 0; i < t.length; i++) {
          x = (t[i] - tref) / per; x = (x - Math.floor(x + 0.5)) * per;
          if (Math.abs(x) < 0.08 * per) { wt = 1.0 - f[i]; sx += wt * x; sw += wt; }
        }
        if (sw > 0) tref += sx / sw;
      }
      return tref;
    },
    analyse: function (p, t, f, per) {
      var K = ph3_transit, a = K.ars(p), tref = K.epoch(t, f, per), half = Math.min(0.5, 0.1 * per), fd = K.fold(t, f, per, tref, half, 100), mn = 1.0, i, m3;
      for (i = 1; i < fd.length - 1; i++) { m3 = (fd[i - 1][1] + fd[i][1] + fd[i + 1][1]) / 3.0; if (m3 < mn) mn = m3; }
      var dd = K.duration_of(fd, 1.0 - mn), dep = K.depth_of(fd, dd);
      dd = K.duration_of(fd, dep);
      var b2 = Math.pow(1.0 + Math.sqrt(Math.max(dep, 0.0)), 2) - Math.pow(a * Math.sin(PI * dd / per), 2);
      var bb = b2 > 0 ? Math.sqrt(b2) : 0.0, mu = Math.sqrt(Math.max(1.0 - bb * bb, 0.0)), u = p.u;
      var k = Math.sqrt(Math.max(dep * (1.0 - u / 3.0) / (1.0 - u * (1.0 - mu)), 0.0)), cosi = Math.min(1.0, bb / a);
      return { depth: dep, k: k, dur: dd, b: bb, inc: Math.acos(cosi) * 180.0 / PI, aRs: a, t0: tref };
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var K = ph3_transit; return { t: s.t || 0.0, depth: 1.0 - K.flux(p, p.t0), dur: K.dur(p), aRs: K.ars(p) }; },
    measure: function (p) {
      var K = ph3_transit, q = cp(p), t = K.times(q), f = K.curve(q, false), r = K.analyse(q, t, f, p.P);
      return { k_fit: r.k, depth: r.depth, dur: r.dur, inc_fit: r.inc, inc_true: Math.acos(p.b / K.ars(p)) * 180.0 / PI };
    }
  };
  function transit_k(p) { return p.k; }

  // ============================================================ 21 cm hydrogen line
  var ph3_hi = {
    PARAMS: { l: 40.0, Th0: 220.0, R0: 8.5, Rc: 1.5, Rd: 6.0, sv: 6.0, Tsc: 4.0, vc: 12.0, bw: 2.4e6, nch: 512.0, sig: 0.25, seed: 71.0, task: 0.0 },
    VARS: ['t', 'vt', 'R', 'Th'],
    F0: 1420.405751768e6, NH_K: 1.823e18, LS: [30.0, 40.0, 50.0, 60.0, 70.0], EDGE_K: 0.63,
    theta: function (p, r) { var tinf = p.Th0 * Math.sqrt(p.R0 * p.R0 + p.Rc * p.Rc) / p.R0; return tinf * r / Math.sqrt(r * r + p.Rc * p.Rc); },
    dv: function (p) { return C * (p.bw / p.nch) / ph3_hi.F0 / 1000.0; },
    vtan: function (p) { var sl = Math.sin(p.l * PI / 180.0); return ph3_hi.theta(p, p.R0 * sl) - p.Th0 * sl; },
    profile: function (p, v) {
      var K = ph3_hi, l = p.l * PI / 180.0, sl = Math.sin(l), cl = Math.cos(l), tot = 0.0, ds = 0.05, s2pi = Math.sqrt(2.0 * PI), i, s, r, vr, x;
      for (i = 0; i < 600; i++) {
        s = (i + 0.5) * ds; r = Math.sqrt(p.R0 * p.R0 + s * s - 2.0 * p.R0 * s * cl);
        if (r > 25.0 || r < 0.3) continue;
        vr = (K.theta(p, r) * p.R0 / r - p.Th0) * sl; x = (v - vr) / p.sv;
        if (Math.abs(x) > 6.0) continue;
        tot += Math.exp(-r / p.Rd) * Math.exp(-0.5 * x * x) / (p.sv * s2pi) * ds;
      }
      return p.Tsc * tot * 25.0;
    },
    vlsr: function (p, i) { return (i + 0.5 - p.nch / 2.0) * ph3_hi.dv(p) + p.vc; },
    expected: function (p) { var out = [], i, n = Math.round(p.nch); for (i = 0; i < n; i++) out.push(ph3_hi.profile(p, ph3_hi.vlsr(p, i))); return out; },
    spectrum: function (p, noise) {
      var ex = ph3_hi.expected(p), rnd, i;
      if (noise === false) return ex;
      rnd = new R(p.seed + 977.0 * Math.floor(p.l + 0.5));
      for (i = 0; i < ex.length; i++) ex[i] = ex[i] + p.sig * rnd.gauss();
      return ex;
    },
    freq: function (p, i) { return ph3_hi.F0 + p.bw / 2.0 - (i + 0.5) * (p.bw / p.nch); },
    edge: function (p, tb) {
      var K = ph3_hi, n = tb.length, sm = [], i, pk, half, hi = 2, v0;
      for (i = 0; i < n; i++) sm.push(0.0);
      for (i = 2; i < n - 2; i++) sm[i] = (tb[i - 2] + tb[i - 1] + tb[i] + tb[i + 1] + tb[i + 2]) / 5.0;
      pk = sm[0]; for (i = 1; i < n; i++) if (sm[i] > pk) pk = sm[i];
      half = 0.5 * pk;
      for (i = 2; i < n - 2; i++) if (sm[i] > half) hi = i;
      v0 = K.vlsr(p, hi);
      if (hi + 1 < n && sm[hi] !== sm[hi + 1]) v0 += K.dv(p) * (sm[hi] - half) / (sm[hi] - sm[hi + 1]);
      return v0 - K.EDGE_K * p.sv;
    },
    nh: function (p, tb) { return ph3_hi.NH_K * sumOf(tb) * ph3_hi.dv(p); },
    rotation: function (p, tb) { var sl = Math.sin(p.l * PI / 180.0); return [p.R0 * sl, ph3_hi.edge(p, tb) + p.Th0 * sl]; },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var K = ph3_hi, sl = Math.sin(p.l * PI / 180.0); return { t: s.t || 0.0, vt: K.vtan(p), R: p.R0 * sl, Th: K.theta(p, p.R0 * sl) }; },
    measure: function (p) {
      var K = ph3_hi, th = [], i, q;
      for (i = 0; i < K.LS.length; i++) { q = cp(p); q.l = K.LS[i]; th.push(K.rotation(q, K.expected(q))[1]); }
      return { theta_fit: mean(th), nh: K.nh(p, K.expected(p)) };
    }
  };
  function hi_theta(p) {
    var K = ph3_hi, xs = [], i;
    for (i = 0; i < K.LS.length; i++) xs.push(K.theta(p, p.R0 * Math.sin(K.LS[i] * PI / 180.0)));
    return mean(xs);
  }

  H0.register({
    K: { ph3_coinc: ph3_coinc, ph3_compton: ph3_compton, ph3_alpha: ph3_alpha, ph3_muon: ph3_muon, ph3_transit: ph3_transit, ph3_hi: ph3_hi },
    TEXTBOOK: { ph3_coinc_tau: coinc_tau, ph3_coinc_rt: coinc_rt, ph3_compton_mc2: compton_mc2, ph3_compton_sigma: compton_sigma,
      ph3_alpha_range: alpha_range, ph3_muon_free: muon_free, ph3_transit_k: transit_k, ph3_hi_theta: hi_theta },
    CALCS: {
      ph3_coinc_tau: { label: 'resolving time', unit: 's', needs: ['k', 'r1', 'r2', 'rc'],
        fn: function (r) { return ph3_coinc.fit(rws(r, ['k', 'r1', 'r2', 'rc'])).tau; } },
      ph3_coinc_rt: { label: 'true coincidence rate', unit: '1/s', needs: ['k', 'r1', 'r2', 'rc'],
        fn: function (r) { return ph3_coinc.fit(rws(r, ['k', 'r1', 'r2', 'rc'])).Rt; } },
      ph3_compton_mc2: { label: 'electron rest energy', unit: 'keV', needs: ['th', 'Ep'],
        fn: function (r) { var xs = rws(r, ['th', 'Ep']), pts = [], i, m;
          for (i = 0; i < xs.length; i++) if (xs[i][1] > 0) pts.push([1.0 - Math.cos(xs[i][0] * PI / 180.0), 1.0 / xs[i][1]]);
          m = lin(pts)[0]; return m > 0 ? 1.0 / m : 0.0; } },
      ph3_alpha_range: { label: 'range in air', unit: 'cm', needs: ['x', 'E'],
        fn: function (r) { return ph3_alpha.range_fit(rws(r, ['x', 'E'])); } },
      ph3_muon_life: { label: 'mean life', unit: 'us', needs: ['tc', 'n'],
        fn: function (r) { var xs = rws(r, ['tc', 'n']), pts = [], i, m;
          for (i = 0; i < xs.length; i++) if (xs[i][1] > 0) pts.push([xs[i][0], Math.log(xs[i][1])]);
          m = lin(pts)[0]; return m < 0 ? -1.0 / m : 0.0; } }
    }
  });
})(typeof window !== 'undefined' ? window : this);
