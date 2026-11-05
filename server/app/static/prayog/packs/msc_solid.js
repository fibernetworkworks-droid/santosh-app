/* Kernel pack `msc_solid`: the exact JavaScript twin of app/prayog/packs/msc_solid.py - the M.Sc. benches for solid
   state, materials characterisation, vacuum and plasma. Same formulas, same algorithms, same numbers (the server's
   tests run both and compare). Deterministic: the only pseudo-noise is a hash of the X-ray scan step. */
(function (root) {
  'use strict';
  var H0 = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, QE = 1.602176634e-19, KB = 1.380649e-23, ME = 9.1093837015e-31, AMU = 1.66053906660e-27;
  var MU0 = 1.25663706212e-6, EPS0 = 8.8541878128e-12, GRAV = 9.80665, LN2 = Math.log(2.0);

  function line(pts) {
    var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, d, m;
    if (n < 2) return [0, 0];
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    d = n * sxx - sx * sx;
    if (d === 0) return [0, 0];
    m = (n * sxy - sx * sy) / d;
    return [m, (sy - m * sx) / n];
  }
  function slope(pts) { if (pts.length < 2) return 0; return line(pts)[0]; }
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
  function over(p, k, v) { var q = {}, i, ks = Object.keys(p); for (i = 0; i < ks.length; i++) q[ks[i]] = p[ks[i]]; q[k] = v; return q; }
  function init() { return { t: 0 }; }
  function step(s, p, dt) { s.t += dt; }
  function tOf(s) { return s.t || 0; }

  // ---------------------------------------------------------------- metal R(T)
  var metal = {
    PARAMS: { T: 293.0, R0: 1.2, alpha: 0.0039, Tref: 293.0, I: 0.01 }, VARS: ['t', 'R', 'V', 'T'], init: init, step: step,
    res: function (p) { return p.R0 * (1.0 + p.alpha * (p.T - p.Tref)); },
    view: function (s, p) { var r = metal.res(p); return { t: tOf(s), R: r, V: r * p.I, T: p.T }; },
    measure: function (p) {
      var r1 = metal.res(over(p, 'T', p.Tref)), r2 = metal.res(over(p, 'T', p.Tref + 100.0));
      return { alpha: (r2 - r1) / (r1 * 100.0), R: metal.res(p), T: p.T };
    }
  };
  function metal_alpha(p) { return p.alpha; }

  // ---------------------------------------------------------------- Seebeck
  var seebeck = {
    PARAMS: { dT: 50.0, S: 41.0, Voff: 1.5, Tcold: 293.0 }, VARS: ['t', 'V', 'dT', 'Th'], init: init, step: step,
    volts: function (p) { return p.Voff + p.S * p.dT; },
    view: function (s, p) { return { t: tOf(s), V: seebeck.volts(p), dT: p.dT, Th: p.Tcold + p.dT }; },
    measure: function (p) { var v1 = seebeck.volts(over(p, 'dT', 20.0)), v2 = seebeck.volts(over(p, 'dT', 80.0));
      return { S: (v2 - v1) / 60.0, V: seebeck.volts(p) }; }
  };
  function seebeck_S(p) { return p.S; }

  // ---------------------------------------------------------------- ionic conductivity
  var ionic = {
    PARAMS: { T: 500.0, Ea: 0.8, A: 4.0e7, Lp: 0.002, Ap: 1.0e-4 }, VARS: ['t', 'R', 'sigma', 'T', 'lnsT'], init: init, step: step,
    sigma: function (p) { return p.A / p.T * Math.exp(-p.Ea * QE / (KB * p.T)); },
    view: function (s, p) { var sg = ionic.sigma(p);
      return { t: tOf(s), R: p.Lp / (sg * p.Ap), sigma: sg, T: p.T, lnsT: Math.log(sg * p.T) }; },
    measure: function (p) {
      var t1 = 450.0, t2 = 650.0, a = Math.log(ionic.sigma(over(p, 'T', t1)) * t1), b = Math.log(ionic.sigma(over(p, 'T', t2)) * t2);
      return { Ea: -KB * (b - a) / (1.0 / t2 - 1.0 / t1) / QE, R: ionic.view({}, p).R };
    }
  };
  function ionic_Ea(p) { return p.Ea; }

  // ---------------------------------------------------------------- superconductor
  var sup = {
    PARAMS: { T: 100.0, Tc: 92.0, w: 1.2, Rn100: 0.06, I: 0.01 }, VARS: ['t', 'R', 'V', 'T'], init: init, step: step,
    frac: function (T, p) { return 0.5 * (1.0 + Math.tanh((T - p.Tc) / p.w)); },
    rn: function (T, p) { return p.Rn100 * T / 100.0; },
    res: function (p) { return sup.rn(p.T, p) * sup.frac(p.T, p); },
    view: function (s, p) { var r = sup.res(p); return { t: tOf(s), R: r, V: r * p.I, T: p.T }; },
    measure: function (p) {
      var lo = 40.0, hi = 200.0, i, mid, tm;
      for (i = 0; i < 100; i++) { mid = 0.5 * (lo + hi); if (sup.frac(mid, p) < 0.5) lo = mid; else hi = mid; }
      tm = 0.5 * (lo + hi); lo = 40.0; hi = 200.0;
      for (i = 0; i < 100; i++) { mid = 0.5 * (lo + hi); if (sup.frac(mid, p) < 0.01) lo = mid; else hi = mid; }
      return { Tc: tm, T0: 0.5 * (lo + hi), R: sup.res(p) };
    }
  };
  function sup_Tc(p) { return p.Tc; }

  // ---------------------------------------------------------------- magnetoresistance
  var magres = {
    PARAMS: { B: 0.0, mu: 7.7, R0: 2.0, xi: 1.0, I: 0.005 }, VARS: ['t', 'R', 'V', 'B', 'dRR'], init: init, step: step,
    res: function (p) { return p.R0 * (1.0 + p.xi * Math.pow(p.mu * p.B, 2)); },
    view: function (s, p) { var r = magres.res(p); return { t: tOf(s), R: r, V: r * p.I, B: p.B, dRR: r / p.R0 - 1.0 }; },
    measure: function (p) {
      var b1 = 0.2, b2 = 0.6, r1 = magres.res(over(p, 'B', b1)), r2 = magres.res(over(p, 'B', b2)),
        sl = (r2 - r1) / p.R0 / (b2 * b2 - b1 * b1);
      return { mu: sl > 0 ? Math.sqrt(sl / p.xi) : 0.0, R: magres.res(p) };
    }
  };
  function magres_mu(p) { return p.mu; }

  // ---------------------------------------------------------------- Curie-Weiss dielectric
  var ferro = {
    PARAMS: { T: 340.0, Tc: 322.15, C: 3000.0, eb: 5.0, dl: 0.6, Ap: 1.0e-4, d: 1.0e-3 }, VARS: ['t', 'eps', 'Cap', 'T', 'inv'], init: init, step: step,
    eps: function (T, p) { var x = T - p.Tc;
      if (x >= 0) return p.eb + p.C / Math.max(x, p.dl);
      return p.eb + p.C / (2.0 * Math.max(-x, p.dl)); },
    view: function (s, p) { var e = ferro.eps(p.T, p);
      return { t: tOf(s), eps: e, Cap: EPS0 * e * p.Ap / p.d, T: p.T, inv: 1.0 / e }; },
    measure: function (p) {
      var best = -1.0, n = 0, t0 = p.Tc - 20.0, vals = [], i, e, tot = 0.0;
      for (i = 0; i <= 800; i++) { e = ferro.eps(t0 + 0.05 * i, p); vals.push(e); if (e > best) best = e; }
      for (i = 0; i < vals.length; i++) if (vals[i] >= best * (1.0 - 1e-12)) { tot += t0 + 0.05 * i; n += 1; }
      return { Tc: tot / n, eps: ferro.eps(p.T, p), epsmax: best };
    }
  };
  function ferro_Tc(p) { return p.Tc; }

  // ---------------------------------------------------------------- Curie point (inductance)
  var curie = {
    PARAMS: { T: 300.0, Tc: 573.0, K: 40.0, L0: 2.0e-3, w: 3.0 }, VARS: ['t', 'L', 'L_mH', 'T'], init: init, step: step,
    ind: function (T, p) { var g = 1.0 / (1.0 + Math.exp((T - (p.Tc - 2.0 * p.w)) / p.w)); return p.L0 * (1.0 + p.K * g); },
    view: function (s, p) { var L = curie.ind(p.T, p); return { t: tOf(s), L: L, L_mH: L * 1e3, T: p.T }; },
    measure: function (p) {
      var t0 = p.Tc - 60.0, best = 0.0, bi = 0, i, t, sl, ts, base;
      for (i = 0; i <= 1200; i++) { t = t0 + 0.1 * i; sl = (curie.ind(t + 0.05, p) - curie.ind(t - 0.05, p)) / 0.1; if (sl < best) { best = sl; bi = i; } }
      ts = t0 + 0.1 * bi; base = curie.ind(p.Tc + 400.0, p);
      return { Tc: ts + (curie.ind(ts, p) - base) / -best, L: curie.ind(p.T, p) };
    }
  };
  function curie_Tc(p) { return p.Tc; }

  // ---------------------------------------------------------------- liquid crystal
  var lc = {
    PARAMS: { T: 300.0, Tni: 308.15, dn0: 0.32, d: 2.4e-6, lam: 6.328e-7, I0: 1.0, stray: 0.004 }, VARS: ['t', 'I', 'S', 'T'], init: init, step: step,
    order: function (T, p) { if (T >= p.Tni) return 0.0; return Math.pow(1.0 - 0.98 * T / p.Tni, 0.22); },
    light: function (T, p) { var dn = p.dn0 * lc.order(T, p); return p.I0 * Math.pow(Math.sin(PI * dn * p.d / p.lam), 2) + p.stray; },
    view: function (s, p) { return { t: tOf(s), I: lc.light(p.T, p), S: lc.order(p.T, p), T: p.T }; },
    measure: function (p) {
      var lo = p.Tni - 20.0, hi = p.Tni + 20.0, i, mid;
      for (i = 0; i < 100; i++) { mid = 0.5 * (lo + hi); if (lc.order(mid, p) > 0) lo = mid; else hi = mid; }
      return { Tni: 0.5 * (lo + hi), I: lc.light(p.T, p) };
    }
  };
  function lc_Tni(p) { return p.Tni; }

  // ---------------------------------------------------------------- dielectric / LCR
  var diel = {
    PARAMS: { f: 1000.0, es: 6.0, einf: 3.0, fr: 4.0e4, Ap: 9.6e-4, d: 1.0e-3 }, VARS: ['t', 'C', 'C_pF', 'D', 'f', 'er'], init: init, step: step,
    eps1: function (f, p) { var x = f / p.fr; return p.einf + (p.es - p.einf) / (1.0 + x * x); },
    eps2: function (f, p) { var x = f / p.fr; return (p.es - p.einf) * x / (1.0 + x * x); },
    view: function (s, p) { var e1 = diel.eps1(p.f, p), c = EPS0 * e1 * p.Ap / p.d;
      return { t: tOf(s), C: c, C_pF: c * 1e12, D: diel.eps2(p.f, p) / e1, f: p.f, er: e1 }; },
    measure: function (p) { var c = EPS0 * diel.eps1(p.f, p) * p.Ap / p.d;
      return { er: c * p.d / (EPS0 * p.Ap), C: c, D: diel.eps2(p.f, p) / diel.eps1(p.f, p) }; }
  };
  function diel_er(p) { return diel.eps1(p.f, p); }

  // ---------------------------------------------------------------- hysteresis loop
  var loop = {
    PARAMS: { H: 0.0, Ms: 1.5, Hc: 80.0, a: 32.0, H0: 400.0, br: 1.0, kind: 1.0 }, VARS: ['t', 'H', 'M', 'Hc_eff'], init: init, step: step,
    hcEff: function (p) { return p.Hc * (1.0 - Math.exp(-Math.pow(p.H0 / p.Hc, 2))); },
    m: function (h, br, p) { return p.Ms * Math.tanh((h - br * loop.hcEff(p)) / p.a); },
    view: function (s, p) { return { t: tOf(s), H: p.H, M: loop.m(p.H, p.br, p), Hc_eff: loop.hcEff(p) }; },
    measure: function (p) {
      var n = 2000, h0 = p.H0, hs = [], up = [], dn = [], i, hc = 0.0, area = 0.0;
      for (i = 0; i <= n; i++) { hs.push(-h0 + 2.0 * h0 * i / n); up.push(loop.m(hs[i], 1.0, p)); dn.push(loop.m(hs[i], -1.0, p)); }
      for (i = 0; i < n; i++) if (dn[i] < 0 && 0 <= dn[i + 1]) { hc = -(hs[i] + (hs[i + 1] - hs[i]) * dn[i] / (dn[i] - dn[i + 1])); break; }
      for (i = 0; i < n; i++) area += 0.5 * ((dn[i] - up[i]) + (dn[i + 1] - up[i + 1])) * (hs[i + 1] - hs[i]);
      return { Hc: hc, Mr: loop.m(0.0, -1.0, p), Ms: up[n], area: area };
    }
  };
  function loop_Hc(p) { return loop.hcEff(p); }

  // ---------------------------------------------------------------- X-ray powder diffraction
  function hklList(ltype, z1, z2, lam, a, tmax) {
    tmax = tmax === undefined ? 62.0 : tmax;
    var nmax = Math.floor(Math.pow(2.0 * a * Math.sin(tmax * PI / 180.0) / lam, 2)) + 1, out = [], n, mult, hit, seen, r, h, k, l, key, par, allsame, s, f2;
    for (n = 1; n <= nmax; n++) {
      mult = 0; hit = null; seen = {}; r = Math.floor(Math.sqrt(n)) + 1;
      for (h = -r; h <= r; h++) for (k = -r; k <= r; k++) for (l = -r; l <= r; l++) {
        if (h * h + k * k + l * l !== n) continue;
        key = h + ',' + k + ',' + l; if (seen[key]) continue; seen[key] = 1; mult += 1;
        if (hit === null) hit = [Math.abs(h), Math.abs(k), Math.abs(l)];
      }
      if (!mult) continue;
      h = hit[0]; k = hit[1]; l = hit[2];
      par = [h % 2, k % 2, l % 2]; allsame = par[0] === par[1] && par[1] === par[2]; s = h + k + l; f2 = null;
      if (ltype === 2) { f2 = (s % 2 === 0) ? 4.0 : null; }
      else if (ltype === 3) { f2 = allsame ? 16.0 : null; }
      else if (ltype === 4) { if (allsame) { if (par[0] === 1) f2 = 32.0; else if (s % 4 === 0) f2 = 64.0; } }
      else if (ltype === 5) { if (allsame) f2 = 16.0 * (par[0] === 0 ? Math.pow(z1 + z2, 2) : Math.pow(z1 - z2, 2)); }
      if (f2 === null) continue;
      out.push({ N: n, m: mult, f2: f2, hkl: [h, k, l] });
    }
    return out;
  }
  var xrd = {
    PARAMS: { tth: 30.0, lam: 1.5406e-10, a: 4.0495e-10, ltype: 3.0, Z1: 13.0, Z2: 0.0, Lx: 2.0e-7, eps: 0.0, binst: 0.1, K: 0.9, bg: 40.0, I0: 10000.0 },
    VARS: ['t', 'I', 'tth', 'd'], init: init, step: step,
    peaks: function (p) {
      var lam = p.lam, a = p.a, out = [], list = hklList(Math.round(p.ltype), p.Z1, p.Z2, lam, a), i, r, s, th, tth, bs, bi, beta, sl, ff, lp, amp, top = 1.0, mx = [];
      for (i = 0; i < list.length; i++) {
        r = list[i]; s = lam * Math.sqrt(r.N) / (2.0 * a); if (s >= 1.0) continue;
        th = Math.asin(s); tth = 2.0 * th * 180.0 / PI; if (tth > 125.0) continue;
        bs = p.K * lam / (p.Lx * Math.cos(th)) + 4.0 * p.eps * Math.tan(th); bi = p.binst * PI / 180.0;
        beta = Math.sqrt(bs * bs + bi * bi) * 180.0 / PI; sl = s / lam * 1e-10; ff = Math.exp(-5.0 * sl * sl);
        lp = (1.0 + Math.pow(Math.cos(2.0 * th), 2)) / (Math.pow(Math.sin(th), 2) * Math.cos(th)); amp = r.m * r.f2 * ff * ff * lp;
        out.push({ N: r.N, hkl: r.hkl, tth: tth, beta: beta, amp: amp, th: th }); mx.push(amp);
      }
      if (mx.length) { top = Math.max.apply(null, mx); }
      for (i = 0; i < out.length; i++) out[i].amp = out[i].amp / top;
      return out;
    },
    noise: function (x) { var i = Math.floor(x * 50.0 + 0.5), s = ((i + 1000) * 2654435761) % 2147483647;
      s = (s * 16807) % 2147483647; s = (s * 16807) % 2147483647; return s / 2147483647.0 - 0.5; },
    counts: function (x, p, pk) {
      pk = pk || xrd.peaks(p); var tot = 0.0, i, q, z, n;
      for (i = 0; i < pk.length; i++) { q = pk[i]; z = (x - q.tth) / q.beta; if (Math.abs(z) < 6.0) tot += q.amp * Math.exp(-4.0 * LN2 * z * z); }
      n = xrd.noise(x);
      return p.bg * (1.0 + 0.2 * n) + p.I0 * tot * (1.0 + 0.006 * n);
    },
    view: function (s, p) { var th = p.tth * PI / 360.0;
      return { t: tOf(s), I: xrd.counts(p.tth, p), tth: p.tth, d: th > 0 ? p.lam / (2.0 * Math.sin(th)) : 0.0 }; },
    seq: function (ltype) { return hklList(ltype, 1.0, 0.0, 1.5406e-10, 12e-10, 85.0).slice(0, 14).map(function (r) { return r.N; }); },
    scanPeaks: function (p, t0, t1, dt) {
      t0 = t0 === undefined ? 20.0 : t0; t1 = t1 === undefined ? 120.0 : t1; dt = dt === undefined ? 0.02 : dt;
      var n = Math.round((t1 - t0) / dt), pk = xrd.peaks(p), xs = [], ys = [], i, j, out = [], ymax, w, half, lo, hi, xl, xh, sw, sx, wgt, mx;
      for (i = 0; i <= n; i++) { xs.push(t0 + dt * i); ys.push(xrd.counts(xs[i], p, pk)); }
      ymax = Math.max.apply(null, ys); i = 3;
      while (i < n - 3) {
        w = ys.slice(i - 3, i + 4); mx = Math.max.apply(null, w);
        if (ys[i] === mx && ys[i] > p.bg * 1.5 + 0.03 * ymax) {
          half = p.bg + (ys[i] - p.bg) / 2.0; lo = i; while (lo > 0 && ys[lo] > half) lo -= 1;
          hi = i; while (hi < n && ys[hi] > half) hi += 1;
          xl = xs[lo] + (half - ys[lo]) * (xs[lo + 1] - xs[lo]) / (ys[lo + 1] - ys[lo]);
          xh = xs[hi - 1] + (ys[hi - 1] - half) * (xs[hi] - xs[hi - 1]) / (ys[hi - 1] - ys[hi]);
          sw = 0.0; sx = 0.0;
          for (j = lo + 1; j < hi; j++) { wgt = ys[j] - half; sw += wgt; sx += wgt * xs[j]; }
          out.push({ tth: sx / sw, fwhm: xh - xl, height: ys[i] }); i = hi + 1;
        } else i += 1;
      }
      return out;
    },
    index: function (peaks, lam) {
      if (!peaks.length) return { ltype: 0, N: [], a: 0.0 };
      var s2 = peaks.map(function (q) { return Math.pow(Math.sin(q.tth * PI / 360.0), 2); }), best = null, lts = [2, 3, 4], li, sq, ns, bad, i, v, target, nn, bd, k, seen, missing, score, c, x;
      for (li = 0; li < lts.length; li++) {
        sq = xrd.seq(lts[li]); ns = []; bad = 0.0;
        for (i = 0; i < s2.length; i++) {
          v = s2[i]; target = v / s2[0] * sq[0]; nn = sq[0]; bd = Math.abs(sq[0] - target);
          for (k = 1; k < sq.length; k++) if (Math.abs(sq[k] - target) < bd) { bd = Math.abs(sq[k] - target); nn = sq[k]; }
          bad += Math.abs(nn - target) / Math.max(nn, 1); ns.push(nn);
        }
        seen = {}; c = 0; for (i = 0; i < ns.length; i++) { if (!seen[ns[i]]) { seen[ns[i]] = 1; c++; } }
        if (c !== ns.length) continue;
        missing = 0; for (k = 0; k < sq.length; k++) { x = sq[k]; if (ns[0] < x && x < ns[ns.length - 1] && ns.indexOf(x) < 0) missing++; }
        score = bad + 0.05 * missing;
        if (best === null || score < best.bad - 1e-12) best = { ltype: lts[li], N: ns, bad: score };
      }
      if (best === null) return { ltype: 0, N: [], a: 0.0 };
      return { ltype: best.ltype, N: best.N, a: lam * Math.sqrt(best.N[best.N.length - 1]) / (2.0 * Math.sqrt(s2[s2.length - 1])) };
    },
    measure: function (p) {
      var pks = xrd.scanPeaks(p), ix = xrd.index(pks, p.lam), bi = p.binst * PI / 180.0, pts = [], i, th, bo, bsam, mc, c;
      for (i = 0; i < pks.length; i++) {
        th = pks[i].tth * PI / 360.0; bo = pks[i].fwhm * PI / 180.0;
        if (bo > bi) { bsam = Math.sqrt(bo * bo - bi * bi); pts.push([4.0 * Math.sin(th), bsam * Math.cos(th)]); }
      }
      mc = line(pts); c = mc[1];
      return { a: ix.a, ltype: ix.ltype, nlines: pks.length, L_wh: c > 0 ? p.K * p.lam / c : 0.0, eps_wh: mc[0] };
    }
  };
  function xrd_a(p) { return p.a; }
  function xrd_L(p) { return p.Lx; }

  // ---------------------------------------------------------------- Quincke
  var quincke = {
    PARAMS: { I: 0.0, kB: 0.4, c: 1.0, chim: 13660.0, chiw: -9.05e-6, rho: 1100.0 }, VARS: ['t', 'B', 'h', 'h_mm', 'chi'], init: init, step: step,
    chi: function (p) { return p.chiw + 4.0 * PI * p.chim * 1e-6 * p.c / 1000.0; },
    rise: function (p) { var b = p.kB * p.I; return quincke.chi(p) * b * b / (2.0 * MU0 * p.rho * GRAV); },
    view: function (s, p) { var h = quincke.rise(p); return { t: tOf(s), B: p.kB * p.I, h: h, h_mm: h * 1e3, chi: quincke.chi(p) }; },
    measure: function (p) {
      var q = over(p, 'I', 1.5), b = q.kB * q.I, chi = 2.0 * MU0 * p.rho * GRAV * quincke.rise(q) / (b * b);
      return { chi: chi, chim: p.c > 0 ? (chi - p.chiw) * 1000.0 / (4.0 * PI * p.c) * 1e6 : 0.0, h: quincke.rise(p) };
    }
  };
  function quincke_chi(p) { return quincke.chi(p); }

  // ---------------------------------------------------------------- vacuum
  var vac = {
    PARAMS: { t: 0.0, V: 0.05, S: 1.39e-3, Q: 7.0e-4, P0: 101325.0, Psat: 5000.0 }, VARS: ['t', 'P', 'Ppir', 'Pion', 'Pu'], init: init, step: step,
    press: function (t, p) { var pu = p.Q / p.S; return pu + (p.P0 - pu) * Math.exp(-p.S * t / p.V); },
    pirani: function (P, p) { var r = P / (1.0 + P / p.Psat); return r > 0.1 ? r : 0.1; },
    ion: function (P) { if (P > 0.1) return -1.0; return P > 1e-6 ? P : 1e-6; },
    view: function (s, p) { var t = p.t ? p.t : (s.t || 0), P = vac.press(t, p);
      return { t: t, P: P, Ppir: vac.pirani(P, p), Pion: vac.ion(P, p), Pu: p.Q / p.S }; },
    measure: function (p) {
      var pu = p.Q / p.S, p1 = 500.0, p2 = Math.max(5.0 * pu, 5.0), lo, hi, i, mid, t1, t2, s, pf;
      if (p2 >= p1 || pu >= p2) p2 = Math.max(pu * 4.0, 1e-9);
      lo = 0.0; hi = 1e6; for (i = 0; i < 200; i++) { mid = 0.5 * (lo + hi); if (vac.press(mid, p) > p1) lo = mid; else hi = mid; }
      t1 = 0.5 * (lo + hi);
      lo = 0.0; hi = 1e6; for (i = 0; i < 200; i++) { mid = 0.5 * (lo + hi); if (vac.press(mid, p) > p2) lo = mid; else hi = mid; }
      t2 = 0.5 * (lo + hi);
      s = p.V / (t2 - t1) * Math.log((p1 - pu) / (p2 - pu)); pf = vac.press(1e6, p);
      return { S: s, Pu: pu < 0.1 ? vac.ion(pf) : vac.pirani(pf, p), t1: t1, t2: t2 };
    }
  };
  function vac_S(p) { return p.S; }
  function vac_Pu(p) { return p.Q / p.S; }

  // ---------------------------------------------------------------- Langmuir probe
  var lang = {
    PARAMS: { V: 0.0, Te: 3.0, Vp: 8.0, ne: 1.0e16, Ap: 2.0e-6, M: 39.948 }, VARS: ['t', 'I', 'I_uA', 'V', 'Ies', 'Iis', 'Vf'], init: init, step: step,
    ies: function (p) { return QE * p.ne * p.Ap * Math.sqrt(QE * p.Te / (2.0 * PI * ME)); },
    iis: function (p) { return 0.61 * QE * p.ne * p.Ap * Math.sqrt(QE * p.Te / (p.M * AMU)); },
    cur: function (v, p) { var ie = lang.ies(p) * (v < p.Vp ? Math.exp((v - p.Vp) / p.Te) : 1.0); return ie - lang.iis(p); },
    view: function (s, p) { var i = lang.cur(p.V, p);
      return { t: tOf(s), I: i, I_uA: i * 1e6, V: p.V, Ies: lang.ies(p), Iis: lang.iis(p), Vf: p.Vp + p.Te * Math.log(lang.iis(p) / lang.ies(p)) }; },
    measure: function (p) {
      var v1 = p.Vp - 2.0 * p.Te, v2 = p.Vp - 0.5 * p.Te, i1 = lang.cur(v1, p) + lang.iis(p), i2 = lang.cur(v2, p) + lang.iis(p);
      return { Te: (v2 - v1) / Math.log(i2 / i1), Ies: lang.ies(p), I: lang.cur(p.V, p) };
    }
  };
  function lang_Te(p) { return p.Te; }

  // ---------------------------------------------------------------- calcs
  function wh(rows, p) { var c = line(rws(rows, ['x', 'y']))[1]; return c > 0 ? p.K * p.lam / c : 0.0; }
  function langTe(rows) {
    var pts = rws(rows, ['V', 'I']), i, ion, imax, sel = [], m;
    if (pts.length < 3) return 0.0;
    ion = -Math.min.apply(null, pts.map(function (x) { return x[1]; }));
    imax = Math.max.apply(null, pts.map(function (x) { return x[1]; })) + ion;
    for (i = 0; i < pts.length; i++) if (0.02 * imax < pts[i][1] + ion && pts[i][1] + ion < 0.5 * imax) sel.push([pts[i][0], Math.log(pts[i][1] + ion)]);
    m = slope(sel); return m > 0 ? 1.0 / m : 0.0;
  }
  function cw(rows) {
    var xs = rws(rows, ['T', 'eps']), pts = [], i, mc;
    for (i = 0; i < xs.length; i++) if (xs[i][1] > 0) pts.push([xs[i][0], 1.0 / xs[i][1]]);
    mc = line(pts); return mc[0] !== 0 ? -mc[1] / mc[0] : 0.0;
  }

  H0.register({
    K: { msc_metal: metal, msc_seebeck: seebeck, msc_ionic: ionic, msc_super: sup, msc_magres: magres, msc_ferro: ferro,
      msc_curie: curie, msc_lc: lc, msc_diel: diel, msc_loop: loop, msc_xrd: xrd, msc_quincke: quincke, msc_vac: vac, msc_langmuir: lang },
    TEXTBOOK: { msc_alpha: metal_alpha, msc_S: seebeck_S, msc_Ea: ionic_Ea, msc_Tc_sc: sup_Tc, msc_mu: magres_mu, msc_Tc_fe: ferro_Tc,
      msc_Tc_cu: curie_Tc, msc_Tni: lc_Tni, msc_er: diel_er, msc_Hc: loop_Hc, msc_a: xrd_a, msc_L: xrd_L, msc_chi: quincke_chi,
      msc_Spump: vac_S, msc_Pu: vac_Pu, msc_Te: lang_Te },
    CALCS: {
      msc_alpha: { label: 'temperature coefficient', unit: '1/K', needs: ['T', 'R'],
        fn: function (r, p) { var mc = line(rws(r, ['T', 'R'])), d = mc[1] + mc[0] * p.Tref; return d !== 0 ? mc[0] / d : 0.0; } },
      msc_seeb: { label: 'Seebeck coefficient', unit: 'uV/K', needs: ['dT', 'V'], fn: function (r) { return slope(rws(r, ['dT', 'V'])); } },
      msc_Eact: { label: 'activation energy', unit: 'eV', needs: ['invT', 'lnsT'], fn: function (r) { return -KB * slope(rws(r, ['invT', 'lnsT'])) / QE; } },
      msc_mob: { label: 'mobility', unit: 'm2/Vs', needs: ['B2', 'R'],
        fn: function (r, p) { var mc = line(rws(r, ['B2', 'R'])), q = mc[1] !== 0 ? mc[0] / (p.xi * mc[1]) : 0; return (mc[1] !== 0 && q > 0) ? Math.sqrt(q) : 0.0; } },
      msc_cw: { label: 'Curie-Weiss temperature', unit: 'K', needs: ['T', 'eps'], fn: cw },
      msc_wh: { label: 'crystallite size', unit: 'm', needs: ['x', 'y'], fn: wh },
      msc_chiq: { label: 'volume susceptibility', unit: '', needs: ['B2', 'h'],
        fn: function (r, p) { return 2.0 * MU0 * p.rho * GRAV * slope(rws(r, ['B2', 'h'])); } },
      msc_Tel: { label: 'electron temperature', unit: 'eV', needs: ['V', 'I'], fn: langTe },
      msc_pump: { label: 'pumping speed', unit: 'm3/s', needs: ['t', 'lnP'], fn: function (r, p) { return -p.V * slope(rws(r, ['t', 'lnP'])); } }
    }
  });
})(typeof window !== 'undefined' ? window : this);
