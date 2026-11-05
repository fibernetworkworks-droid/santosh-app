/* Kernel pack `msc_elec`: the exact JavaScript twin of app/prayog/packs/msc_elec.py - the M.Sc. benches of
   nuclear spectroscopy, microwaves and advanced electronics. Same formulas, same algorithms, same numbers (the
   server's tests run both and compare). Deterministic: counting statistics come from a Lehmer generator seeded by
   the lab's own `seed`, never the clock. */
(function (root) {
  'use strict';
  var H0 = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, ME_KEV = 510.99895, C = 2.99792458e8, QE = 1.602176634e-19, ME = 9.1093837015e-31;
  var FW = 2.3548200450309493;

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
        hh, l, r, rough, j, bl, top, half, y0, y1, xl, fw, w, area;
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
      bl = (ex[j - 1] + ex[j] + ex[Math.min(n - 1, j + 1)]) / 3.0;
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

  function gs_cmp(p) { return p.pf662 > 0 ? gs_res(p) : gs_edge(p); }

  H0.register({
    K: { msc_gspec: msc_gspec },
    TEXTBOOK: { msc_gs_E: gs_E, msc_gs_fwhm: gs_fwhm, msc_gs_res: gs_res, msc_gs_eff: gs_eff, msc_gs_edge: gs_edge, msc_gs_cmp: gs_cmp },
    CALCS: {}
  });
})(typeof window !== 'undefined' ? window : this);
