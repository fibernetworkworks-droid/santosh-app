/* Kernel pack `msc_elec`: the exact JavaScript twin of app/prayog/packs/msc_elec.py - the M.Sc. benches of
   nuclear spectroscopy, microwaves and advanced electronics. Same formulas, same algorithms, same numbers (the
   server's tests run both and compare). Deterministic: counting statistics come from a Lehmer generator seeded by
   the lab's own `seed`, never the clock. */
(function (root) {
  'use strict';
  var H0 = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, ME_KEV = 510.99895, C = 2.99792458e8, QE = 1.602176634e-19, ME = 9.1093837015e-31;
  var FW = 2.3548200450309493, assign = H0.assign;

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
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

  // ------------------------------------------------------------------ gamma spectrometer
  var SRC = [
    ['Cs-137', [[661.657, 0.851, 1.0]]],
    ['Co-60', [[1173.228, 0.9985, 1.0], [1332.492, 0.999826, 1.0]]],
    ['Na-22', [[511.0, 1.806, 1.0], [1274.537, 0.99944, 1.0]]],
    ['Ba-133', [[80.998, 0.329, 1.0], [276.399, 0.07164, 1.0], [302.851, 0.1833, 1.0], [356.013, 0.6205, 1.0], [383.849, 0.0894, 1.0]]],
    ['Am-241', [[59.541, 0.359, 1.0]]],
    ['Eu-152', [[121.782, 0.2853, 1.0], [244.697, 0.0755, 1.0], [344.279, 0.2659, 1.0], [778.905, 0.1293, 1.0],
      [964.057, 0.1451, 1.0], [1085.837, 0.1011, 1.0], [1112.076, 0.1367, 1.0], [1408.013, 0.2087, 1.0]]],
    ['Soil', [[609.312, 0.4549, 35.0], [1120.287, 0.1492, 35.0], [1764.494, 0.1531, 35.0], [911.204, 0.258, 30.0],
      [968.971, 0.158, 30.0], [2614.511, 0.358, 30.0], [1460.822, 0.1066, 400.0]]]
  ];

  var msc_gspec = {
    PARAMS: { src: 0.0, gain: 2.0, off: 0.0, nch: 1024.0, R662: 0.07, w0: 0.0, pf662: 0.35, et662: 0.55, kE: 0.6,
      act: 37.0, d: 10.0, rad: 3.81, t: 100.0, seed: 5.0, bg: 0.0, task: 0.0 },
    VARS: ['t', 'rate', 'E0', 'fwhm0', 'omega'],
    SRC: SRC,
    fwhm: function (e, p) { return Math.sqrt(p.w0 * p.w0 + p.R662 * p.R662 * 662.0 * e); },
    pf: function (e, p) {
      if (p.pf662 <= 0.0) return 0.0;
      if (p.pf662 >= 1.0) return 1.0;
      return 1.0 / (1.0 + (e / 662.0) * (1.0 / p.pf662 - 1.0));
    },
    et: function (e, p) { return Math.min(0.98, p.et662 * Math.pow(662.0 / e, p.kE)); },
    omega: function (p) { return 0.5 * (1.0 - p.d / Math.sqrt(p.d * p.d + p.rad * p.rad)); },
    lines: function (p) {
      var idx = Math.round(p.src), om = msc_gspec.omega(p), out = [], i, L, e, n, pf;
      idx = idx < 0 ? 0 : (idx >= SRC.length ? SRC.length - 1 : idx);
      L = SRC[idx][1];
      for (i = 0; i < L.length; i++) {
        e = L[i][0];
        n = p.t * p.act * 1000.0 * L[i][2] * L[i][1] * om * msc_gspec.et(e, p);
        pf = msc_gspec.pf(e, p);
        out.push({ E: e, I: L[i][1], w: L[i][2], npk: n * pf, ncomp: n * (1.0 - pf) });
      }
      return out;
    },
    expected: function (p) {
      var n = Math.round(p.nch), gain = p.gain, off = p.off, ex = [], i, j, k, s2pi = Math.sqrt(2.0 * PI), ls, ln,
        e0, sg0, lo, hi, x, al, emin, raw, tot, tj, eps, cs, f, ei, sg, w, jlo, jhi, acc, xx;
      for (i = 0; i < n; i++) ex.push(p.bg * p.t * gain);
      ls = msc_gspec.lines(p);
      for (k = 0; k < ls.length; k++) {
        ln = ls[k]; e0 = ln.E; sg0 = msc_gspec.fwhm(e0, p) / FW;
        if (ln.npk > 0) {
          lo = Math.max(0, Math.floor((e0 - off) / gain - 6.0 * sg0 / gain));
          hi = Math.min(n - 1, Math.floor((e0 - off) / gain + 6.0 * sg0 / gain) + 1);
          for (i = lo; i <= hi; i++) {
            x = off + gain * (i + 0.5) - e0;
            ex[i] += ln.npk * gain * Math.exp(-0.5 * Math.pow(x / sg0, 2)) / (sg0 * s2pi);
          }
        }
        if (ln.ncomp > 0) {
          al = e0 / ME_KEV; emin = 1.0 / (1.0 + 2.0 * al); raw = []; tot = 0.0;
          for (j = 0; j < n; j++) {
            raw.push(0.0);
            tj = off + gain * (j + 0.5); eps = 1.0 - tj / e0;
            if (eps < emin || eps >= 1.0) continue;
            cs = 1.0 - (1.0 / eps - 1.0) / al;
            f = eps + 1.0 / eps - (1.0 - cs * cs);
            raw[j] = f; tot += f;
          }
          if (tot > 0) {
            for (j = 0; j < n; j++) if (raw[j] > 0) raw[j] = raw[j] / tot;
            for (i = 0; i < n; i++) {
              ei = off + gain * (i + 0.5);
              sg = msc_gspec.fwhm(ei > 1.0 ? ei : 1.0, p) / FW;
              w = Math.floor(4.0 * sg / gain) + 1;
              jlo = Math.max(0, i - w); jhi = Math.min(n - 1, i + w); acc = 0.0;
              for (j = jlo; j <= jhi; j++) {
                if (raw[j] > 0) { xx = (j - i) * gain; acc += raw[j] * Math.exp(-0.5 * Math.pow(xx / sg, 2)); }
              }
              ex[i] += ln.ncomp * acc * gain / (sg * s2pi);
            }
          }
        }
      }
      return ex;
    },
    counts: function (p) {
      var rnd = new Rnd(p.seed), ex = msc_gspec.expected(p), out = [], i;
      for (i = 0; i < ex.length; i++) out.push(rnd.poisson(ex[i]));
      return out;
    },
    mainLine: function (p) {
      var ls = msc_gspec.lines(p), best = null, bh = -1.0, i, h;
      for (i = 0; i < ls.length; i++) { h = ls[i].npk / msc_gspec.fwhm(ls[i].E, p); if (h > bh) { bh = h; best = ls[i]; } }
      return best || { E: 0.0, I: 0.0, w: 1.0, npk: 0.0, ncomp: 0.0 };
    },
    findPeak: function (ex, p) {
      var n = ex.length, gain = p.gain, off = p.off, i0 = 1, vmax = -1.0, i, a, b, c, la, lb, lc, den, dx, pos, epk,
        hh, l, r, rough, j, k, bl, top, half, y0, y1, xl, fw, w, area;
      for (i = 1; i < n - 1; i++) if (ex[i] > vmax) { vmax = ex[i]; i0 = i; }
      a = ex[i0 - 1]; b = ex[i0]; c = ex[i0 + 1];
      if (a > 0 && b > 0 && c > 0) {
        la = Math.log(a); lb = Math.log(b); lc = Math.log(c); den = la - 2.0 * lb + lc;
        dx = den !== 0 ? 0.5 * (la - lc) / den : 0.0;
      } else dx = 0.0;
      pos = i0 + dx; epk = off + gain * (pos + 0.5);
      hh = vmax / 2.0; l = i0;
      while (l > 0 && ex[l] > hh) l -= 1;
      r = i0;
      while (r < n - 1 && ex[r] > hh) r += 1;
      rough = Math.max(r - l, 2);
      j = Math.max(1, i0 - Math.floor(2.2 * rough));
      k = Math.min(n - 2, i0 + Math.floor(2.2 * rough));
      bl = Math.min((ex[j - 1] + ex[j] + ex[Math.min(n - 1, j + 1)]) / 3.0, (ex[k - 1] + ex[k] + ex[k + 1]) / 3.0);
      top = vmax - bl; half = top / 2.0; l = i0;
      while (l > 0 && ex[l] - bl > half) l -= 1;
      y0 = ex[l] - bl; y1 = ex[l + 1] - bl;
      if (y0 > 0 && y1 > 0 && y1 !== y0) xl = l + (Math.log(half) - Math.log(y0)) / (Math.log(y1) - Math.log(y0));
      else xl = y1 !== y0 ? l + (half - y0) / (y1 - y0) : l;
      fw = 2.0 * (pos - xl) * gain;
      w = Math.floor(1.25 * rough + 0.5); area = 0.0;
      for (i = Math.max(0, i0 - w); i <= Math.min(n - 1, i0 + w); i++) area += ex[i] - bl;
      return { chan: pos, E: epk, fwhm: fw, area: area, height: vmax };
    },
    edge: function (ex, p) {
      var n = ex.length, gain = p.gain, off = p.off, i0 = 1, vmax = -1.0, i, best = 0.0, bi, d;
      for (i = 1; i < n - 1; i++) if (ex[i] > vmax) { vmax = ex[i]; i0 = i; }
      bi = i0;
      for (i = i0; i < n - 1; i++) { d = ex[i + 1] - ex[i - 1]; if (d < best) { best = d; bi = i; } }
      return off + gain * (bi + 0.5);
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var ls = msc_gspec.lines(p), top = msc_gspec.mainLine(p), tot = 0, i;
      for (i = 0; i < ls.length; i++) tot += ls[i].npk + ls[i].ncomp;
      return { t: s.t || 0.0, rate: tot / Math.max(p.t, 1e-9), E0: top.E, fwhm0: msc_gspec.fwhm(top.E, p), omega: msc_gspec.omega(p) };
    },
    measure: function (p) {
      var ex = msc_gspec.expected(p), pk = msc_gspec.findPeak(ex, p), top = msc_gspec.mainLine(p),
        flux = p.t * p.act * 1000.0 * top.w * top.I;
      return { E_pk: pk.E, fwhm_pk: pk.fwhm, res_pk: pk.E > 0 ? pk.fwhm / pk.E : 0.0,
        eff_pk: flux > 0 ? pk.area / flux : 0.0, edge: msc_gspec.edge(ex, p), chan_pk: pk.chan,
        cmp_pk: p.pf662 > 0 ? (pk.E > 0 ? pk.fwhm / pk.E : 0.0) : msc_gspec.edge(ex, p) };
    }
  };
  function firstLine(p) { return SRC[Math.round(p.src)][1][0][0]; }
  function gs_E(p) { return msc_gspec.mainLine(p).E; }
  function gs_fwhm(p) { return msc_gspec.fwhm(msc_gspec.mainLine(p).E, p); }
  function gs_res(p) { var e = msc_gspec.mainLine(p).E; return msc_gspec.fwhm(e, p) / e; }
  function gs_eff(p) { var e = msc_gspec.mainLine(p).E; return msc_gspec.omega(p) * msc_gspec.et(e, p) * msc_gspec.pf(e, p); }
  function gs_edge(p) {
    var e = p.pf662 > 0 ? msc_gspec.mainLine(p).E : firstLine(p), al = e / ME_KEV;
    return 2.0 * al / (1.0 + 2.0 * al) * e;
  }

  // ------------------------------------------------------------------ microwave bench
  function beta(f, a, er) {
    var k0 = 2.0 * PI * f / C, v = (er === undefined ? 1.0 : er) * k0 * k0 - (PI / a) * (PI / a);
    return v > 0 ? Math.sqrt(v) : 0.0;
  }
  function erFromShift(delta, p) {
    var b = beta(p.f, p.a), k0 = 2.0 * PI * p.f / C, x = Math.tan(b * (p.ls - delta)),
      hi = (Math.pow(1.55 / p.ls, 2) + Math.pow(PI / p.a, 2)) / (k0 * k0), lo = 1.0001, i, mid, bd, f;
    for (i = 0; i < 80; i++) {
      mid = (lo + hi) / 2.0; bd = beta(p.f, p.a, mid);
      f = (b / bd) * Math.tan(bd * p.ls) - x;
      if (f > 0) hi = mid; else lo = mid;
    }
    return (lo + hi) / 2.0;
  }
  function pmod(a, h) { return ((a % h) + h) % h; }
  var msc_mwline = {
    PARAMS: { f: 9.5e9, a: 0.02286, g: 0.5, phi: 1.0, gs: 0.995, xl: 0.1105, x: 0.05, p0: 100.0, sam: 0.0, ls: 0.004, er: 2.6, task: 0.0 },
    VARS: ['t', 'I', 'x_mm', 'lam_g', 'vswr'],
    lamG: function (p) { return 2.0 * PI / beta(p.f, p.a); },
    gamma: function (p, short) {
      if (p.sam > 0) {
        var b = beta(p.f, p.a), bd = beta(p.f, p.a, p.er), xr = bd > 0 ? (b / bd) * Math.tan(bd * p.ls) : 0.0;
        return [p.gs, PI - 2.0 * Math.atan(xr)];
      }
      if (short) return [p.gs, PI];
      return [p.g, p.phi];
    },
    power: function (p, x, short) {
      var b = beta(p.f, p.a), gg = msc_mwline.gamma(p, short), s = p.xl - x - (p.sam > 0 ? p.ls : 0.0);
      return p.p0 * (1.0 + gg[0] * gg[0] + 2.0 * gg[0] * Math.cos(gg[1] - 2.0 * b * s)) / 4.0;
    },
    extrema: function (p, short, sign) {
      var n = 2000, xs = [], ys = [], out = [], i, lo, hi, c, d, fc, fd, k, gr = 0.6180339887498949;
      for (i = 0; i <= n; i++) { xs.push(0.1 * i / n); ys.push(sign * msc_mwline.power(p, xs[i], short)); }
      for (i = 1; i < n; i++) {
        if (ys[i] < ys[i - 1] && ys[i] <= ys[i + 1]) {
          lo = xs[i - 1]; hi = xs[i + 1];
          c = hi - gr * (hi - lo); d = lo + gr * (hi - lo);
          fc = sign * msc_mwline.power(p, c, short); fd = sign * msc_mwline.power(p, d, short);
          for (k = 0; k < 60; k++) {
            if (fc < fd) { hi = d; d = c; fd = fc; c = hi - gr * (hi - lo); fc = sign * msc_mwline.power(p, c, short); }
            else { lo = c; c = d; fc = fd; d = lo + gr * (hi - lo); fd = sign * msc_mwline.power(p, d, short); }
          }
          out.push((lo + hi) / 2.0);
        }
      }
      return out;
    },
    minima: function (p, short) { return msc_mwline.extrema(p, !!short, 1.0); },
    maxima: function (p, short) { return msc_mwline.extrema(p, !!short, -1.0); },
    width2min: function (p, xmin) {
      var pm = msc_mwline.power(p, xmin), tot = 0.0, dirs = [1.0, -1.0], j, k, lo, hi, mid;
      for (j = 0; j < 2; j++) {
        lo = 0.0; hi = 0.01;
        for (k = 0; k < 70; k++) { mid = (lo + hi) / 2.0;
          if (msc_mwline.power(p, xmin + dirs[j] * mid) < 2.0 * pm) lo = mid; else hi = mid; }
        tot += (lo + hi) / 2.0;
      }
      return tot;
    },
    zload: function (s, d, lam) {
      var t = Math.tan(2.0 * PI * d / lam), den = s * s + t * t;
      return [s * (1.0 + t * t) / den, t * (1.0 - s * s) / den];
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, I: msc_mwline.power(p, p.x), x_mm: p.x * 1000.0, lam_g: msc_mwline.lamG(p) * 1000.0, vswr: (1.0 + p.g) / (1.0 - p.g) }; },
    measure: function (p) {
      var mins = msc_mwline.minima(p), maxs = msc_mwline.maxima(p), lam = mins.length > 1 ? 2.0 * (mins[1] - mins[0]) : 0.0,
        pmin = 1e300, pmax = -1e300, i, v, vswr, half = lam / 2.0, ref, sh, er, delta, dmin, z, w, sdm, ti, res;
      for (i = 0; i < mins.length; i++) { v = msc_mwline.power(p, mins[i]); if (v < pmin) pmin = v; }
      for (i = 0; i < maxs.length; i++) { v = msc_mwline.power(p, maxs[i]); if (v > pmax) pmax = v; }
      vswr = Math.sqrt(pmax / pmin);
      if (p.sam > 0) {
        ref = msc_mwline.minima(assign(p, { sam: 0.0 }), true);
        sh = pmod(ref[0] - mins[0], half);
        if (sh > half / 2.0) sh -= half;
        er = erFromShift(sh, p);
        return { lam_g: lam, vswr: vswr, s_dm: 0.0, zr: 0.0, zi: 0.0, dmin: 0.0, er: er, shift: sh, res: er };
      }
      ref = msc_mwline.minima(p, true);
      delta = pmod(mins[0] - ref[0], half);
      dmin = pmod(half - delta, half);
      z = msc_mwline.zload(vswr, dmin, lam);
      w = msc_mwline.width2min(p, mins[0]);
      sdm = Math.sqrt(1.0 + 1.0 / Math.pow(Math.sin(PI * w / lam), 2));
      ti = Math.round(p.task); res = [lam, vswr, sdm, z[0]][ti < 4 ? ti : 0];
      return { lam_g: lam, vswr: vswr, s_dm: sdm, zr: z[0], zi: z[1], dmin: dmin, er: 0.0, shift: delta, res: res };
    }
  };
  msc_mwline.erFromShift = erFromShift;
  function mw_lamg(p) { return msc_mwline.lamG(p); }
  function mw_res(p) {
    var t = Math.round(p.task);
    if (p.sam > 0) return p.er;
    if (t === 0) return msc_mwline.lamG(p);
    if (t === 1 || t === 2) return (1.0 + p.g) / (1.0 - p.g);
    return (1.0 - p.g * p.g) / (1.0 + p.g * p.g - 2.0 * p.g * Math.cos(p.phi));
  }

  var msc_klys = {
    PARAMS: { V0: 300.0, L: 0.00126, f0: 9.0e9, Q: 400.0, vr: 180.0, P0: 30.0, mode: 2.0, task: 0.0 },
    VARS: ['t', 'P', 'f_GHz', 'N'],
    K: function (p) { return 2.0 * p.L * p.f0 * Math.sqrt(2.0 * ME * p.V0 / QE); },
    N: function (p, vr) { return msc_klys.K(p) / (p.V0 + vr); },
    locate: function (p, vr) { var n = msc_klys.N(p, vr), k = Math.floor(n - 0.75 + 0.5); return [k, n - (k + 0.75)]; },
    power: function (p, vr) {
      var l = msc_klys.locate(p, vr);
      if (l[0] < 1 || Math.abs(l[1]) >= 0.375) return 0.0;
      return p.P0 * (1.75 / (l[0] + 0.75)) * Math.pow(Math.cos(PI * l[1] / 0.75), 2);
    },
    freq: function (p, vr) {
      var l = msc_klys.locate(p, vr);
      if (l[0] < 1 || Math.abs(l[1]) >= 0.375) return p.f0;
      return p.f0 - p.f0 / (2.0 * p.Q) * (l[1] / 0.375);
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, P: msc_klys.power(p, p.vr), f_GHz: msc_klys.freq(p, p.vr) / 1e9, N: msc_klys.N(p, p.vr) }; },
    measure: function (p) {
      var m = Math.round(p.mode), best = -1.0, vc = 0.0, i, vr, pw, half, lo, hi;
      for (i = 1; i < 50000; i++) {
        vr = i * 0.01;
        if (msc_klys.locate(p, vr)[0] !== m) continue;
        pw = msc_klys.power(p, vr);
        if (pw > best) { best = pw; vc = vr; }
      }
      half = best / 2.0; lo = vc;
      while (lo > 0.01 && msc_klys.power(p, lo) > half) lo -= 0.01;
      hi = vc;
      while (msc_klys.locate(p, hi)[0] === m && msc_klys.power(p, hi) > half) hi += 0.01;
      return { vr_c: vc, P_c: best, f_c: msc_klys.freq(p, vc), et_range: Math.abs(msc_klys.freq(p, lo) - msc_klys.freq(p, hi)) };
    }
  };
  function ky_vr(p) { return msc_klys.K(p) / (Math.round(p.mode) + 0.75) - p.V0; }

  var msc_gunn = {
    PARAMS: { V: 8.0, Lg: 10.5e-6, vd: 1.0e5, Eth: 3.2e5, R0: 20.0, r: 0.7, Vk: 1.0, R1: 250.0, Pm: 15.0, k: 2.7, task: 0.0 },
    VARS: ['t', 'I_mA', 'P', 'f_GHz'],
    vth: function (p) { return p.Eth * p.Lg; },
    cur: function (p, v) {
      var vt = msc_gunn.vth(p);
      if (v <= vt) return v / p.R0;
      return vt / p.R0 * (p.r + (1.0 - p.r) * Math.exp(-(v - vt) / p.Vk)) + (v - vt) / p.R1;
    },
    power: function (p, v) {
      var vt = msc_gunn.vth(p), u;
      if (v <= vt) return 0.0;
      u = (v - vt) / ((p.k - 1.0) * vt);
      return p.Pm * u * Math.exp(1.0 - u);
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, I_mA: msc_gunn.cur(p, p.V) * 1000.0, P: msc_gunn.power(p, p.V), f_GHz: p.V > msc_gunn.vth(p) ? p.vd / p.Lg / 1e9 : 0.0 }; },
    measure: function (p) {
      var bi = -1.0, bv = 0.0, bp = -1.0, bpv = 0.0, i, v, c, pw;
      for (i = 0; i <= 12000; i++) {
        v = i * 0.001; c = msc_gunn.cur(p, v);
        if (c > bi) { bi = c; bv = v; }
        pw = msc_gunn.power(p, v);
        if (pw > bp) { bp = pw; bpv = v; }
      }
      return { vth_m: bv, I_pk: bi, v_opt: bpv, P_max: bp, f: p.vd / p.Lg };
    }
  };
  function gu_vth(p) { return p.Eth * p.Lg; }

  // ------------------------------------------------------------------ advanced electronics
  var msc_osc = {
    PARAMS: { kind: 1.0, R: 10000.0, C: 1.0e-8, L: 1.0e-3, C2: 1.0e-8, L2: 1.0e-3, M: 0.0, A: 3.5, Vsat: 12.0, t: 0.0, task: 0.0 },
    VARS: ['t', 'f_kHz', 'amin', 'vo'],
    zloop: function (p, w) {
      var k = Math.round(p.kind), a, x;
      if (k === 0) { a = 1.0 / (w * p.R * p.C); return [1.0 - 5.0 * a * a, -(6.0 * a - Math.pow(a, 3))]; }
      if (k === 1) { x = w * p.R * p.C; return [3.0, x - 1.0 / x]; }
      if (k === 2) return [p.C2 / p.C, w * p.L - 1.0 / (w * p.C) - 1.0 / (w * p.C2)];
      return [(p.L2 + p.M) / (p.L + p.M), w * (p.L + p.L2 + 2.0 * p.M) - 1.0 / (w * p.C)];
    },
    solve: function (p) {
      var loW = 1.0e2, hiW = 1.0e10, n = 4000, prevW = loW, prev = msc_osc.zloop(p, prevW)[1], i, w, cur, a, b, m, k, w0;
      for (i = 1; i <= n; i++) {
        w = loW * Math.pow(hiW / loW, i / n); cur = msc_osc.zloop(p, w)[1];
        if (((prev < 0) !== (cur < 0)) && prev !== 0) {
          a = prevW; b = w;
          for (k = 0; k < 80; k++) {
            m = Math.sqrt(a * b);
            if ((msc_osc.zloop(p, m)[1] < 0) === (msc_osc.zloop(p, a)[1] < 0)) a = m; else b = m;
          }
          w0 = Math.sqrt(a * b);
          return [w0, Math.abs(msc_osc.zloop(p, w0)[0])];
        }
        prevW = w; prev = cur;
      }
      return [0.0, 0.0];
    },
    amplitude: function (p) {
      var s = msc_osc.solve(p);
      if (s[0] <= 0 || p.A < s[1]) return 0.0;
      return p.Vsat * Math.tanh(2.5 * (p.A / s[1] - 1.0));
    },
    wave: function (p, t) { var s = msc_osc.solve(p); return msc_osc.amplitude(p) * Math.sin(s[0] * t); },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var q = msc_osc.solve(p); return { t: s.t || 0.0, f_kHz: q[0] / (2.0 * PI) / 1000.0, amin: q[1], vo: msc_osc.amplitude(p) }; },
    measure: function (p) { var q = msc_osc.solve(p); return { f: q[0] / (2.0 * PI), amin: q[1], vo: msc_osc.amplitude(p) }; }
  };
  function osc_f(p) {
    var k = Math.round(p.kind);
    if (k === 0) return 1.0 / (2.0 * PI * Math.sqrt(6.0) * p.R * p.C);
    if (k === 1) return 1.0 / (2.0 * PI * p.R * p.C);
    if (k === 2) return 1.0 / (2.0 * PI * Math.sqrt(p.L * p.C * p.C2 / (p.C + p.C2)));
    return 1.0 / (2.0 * PI * Math.sqrt((p.L + p.L2 + 2.0 * p.M) * p.C));
  }

  var msc_filt = {
    PARAMS: { kind: 0.0, R: 10000.0, C: 1.0e-8, K: 1.5858, R2: 1000.0, C2: 1.0e-8, f: 1000.0, task: 0.0 },
    VARS: ['t', 'gain', 'gain_db', 'phase'],
    h: function (p, f) {
      var w = 2.0 * PI * f, k = Math.round(p.kind), w0 = 1.0 / (p.R * p.C), nre, nim, dre, dim, a, b, den, re, im;
      if (k === 0 || k === 1) {
        dre = -w * w + w0 * w0; dim = (3.0 - p.K) * w0 * w;
        if (k === 0) { nre = p.K * w0 * w0; nim = 0.0; } else { nre = -p.K * w * w; nim = 0.0; }
      } else if (k === 2) {
        a = w * p.R * p.C; b = w * p.R2 * p.C2; nre = 0.0; nim = a; dre = 1.0 - a * b; dim = a + b;
      } else if (k === 3) {
        a = w * p.R * p.C; nre = 1.0; nim = -a; dre = 1.0; dim = a;
      } else if (k === 4) {
        a = w * p.R * p.C; nre = 1.0; nim = 0.0; dre = 1.0; dim = a;
      } else {
        a = w * p.R * p.C; nre = 0.0; nim = a; dre = 1.0; dim = a;
      }
      den = dre * dre + dim * dim;
      re = (nre * dre + nim * dim) / den; im = (nim * dre - nre * dim) / den;
      return [Math.sqrt(re * re + im * im), Math.atan2(im, re) * 180.0 / PI];
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var q = msc_filt.h(p, p.f); return { t: s.t || 0.0, gain: q[0], gain_db: 20.0 * Math.log(Math.max(q[0], 1e-12)) / Math.LN10, phase: q[1] }; },
    corner: function (p, falling, ref) {
      var n = 3000, target = ref / Math.sqrt(2.0), prevF = 0.1, prev = msc_filt.h(p, prevF)[0] - target, i, f, cur, a, b, m, c, k, hit;
      for (i = 1; i <= n; i++) {
        f = 0.1 * Math.pow(1.0e8, i / n); cur = msc_filt.h(p, f)[0] - target;
        hit = falling ? (prev > 0 && cur <= 0) : (prev < 0 && cur >= 0);
        if (hit) {
          a = prevF; b = f;
          for (k = 0; k < 80; k++) { m = Math.sqrt(a * b); c = msc_filt.h(p, m)[0] - target; if ((c > 0) === (prev > 0)) a = m; else b = m; }
          return Math.sqrt(a * b);
        }
        prevF = f; prev = cur;
      }
      return 0.0;
    },
    measure: function (p) {
      var k = Math.round(p.kind), a, b, m, i, h0, fc, g1, g2, fm, lo, hi;
      if (k === 3) {
        a = 0.1; b = 1.0e7;
        for (i = 0; i < 100; i++) { m = Math.sqrt(a * b); if (msc_filt.h(p, m)[1] > -90.0) a = m; else b = m; }
        return { fc: Math.sqrt(a * b), fh: 0.0, h0: 1.0, slope: 0.0 };
      }
      if (k === 0 || k === 4) {
        h0 = msc_filt.h(p, 0.1)[0]; fc = msc_filt.corner(p, true, h0);
        g1 = msc_filt.h(p, fc * 30.0)[0]; g2 = msc_filt.h(p, fc * 300.0)[0];
        return { fc: fc, fh: 0.0, h0: h0, slope: 20.0 * Math.log(g2 / g1) / Math.LN10 };
      }
      if (k === 1 || k === 5) {
        h0 = msc_filt.h(p, 1.0e7)[0]; fc = msc_filt.corner(p, false, h0);
        g1 = msc_filt.h(p, fc / 30.0)[0]; g2 = msc_filt.h(p, fc / 300.0)[0];
        return { fc: fc, fh: 0.0, h0: h0, slope: 20.0 * Math.log(g2 / g1) / Math.LN10 };
      }
      fm = Math.sqrt(1.0 / (p.R * p.C * p.R2 * p.C2)) / (2.0 * PI);
      h0 = msc_filt.h(p, fm)[0]; lo = msc_filt.corner(p, false, h0); hi = msc_filt.corner(p, true, h0);
      return { fc: lo, fh: hi, h0: h0, slope: 0.0 };
    }
  };
  function filt_fc(p) { return 1.0 / (2.0 * PI * p.R * p.C); }

  function gs_cmp(p) { return p.pf662 > 0 ? gs_res(p) : gs_edge(p); }

  H0.register({
    K: { msc_gspec: msc_gspec, msc_mwline: msc_mwline, msc_klys: msc_klys, msc_gunn: msc_gunn, msc_osc: msc_osc, msc_filt: msc_filt },
    TEXTBOOK: { msc_gs_E: gs_E, msc_gs_fwhm: gs_fwhm, msc_gs_res: gs_res, msc_gs_eff: gs_eff, msc_gs_edge: gs_edge, msc_gs_cmp: gs_cmp,
      msc_mw_lamg: mw_lamg, msc_mw_res: mw_res, msc_ky_vr: ky_vr, msc_gu_vth: gu_vth,
      msc_osc_f: osc_f, msc_filt_fc: filt_fc },
    CALCS: {}
  });
})(typeof window !== 'undefined' ? window : this);
