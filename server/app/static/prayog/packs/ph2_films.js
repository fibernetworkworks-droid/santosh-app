/* Kernel pack `ph2_films`: the exact JavaScript twin of app/prayog/packs/ph2_films.py - thin-film, vacuum, X-ray and
   semiconductor-characterisation benches. Same formulas, same algorithms, same numbers (the server's tests run both
   and compare). Deterministic: the only pseudo-noise is a hash of the sample index and a lab seed. */
(function (root) {
  'use strict';
  var H0 = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, QE = 1.602176634e-19, KB = 1.380649e-23, NA = 6.02214076e23, RE = 2.8179403262e-15, AMU = 1.66053906660e-27;
  var D2R = PI / 180.0;

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
  function over(p, k, v) { var q = {}, i, ks = Object.keys(p); for (i = 0; i < ks.length; i++) q[ks[i]] = p[ks[i]]; q[k] = v; return q; }
  function withp(p, o) { var q = {}, i, ks = Object.keys(p); for (i = 0; i < ks.length; i++) q[ks[i]] = p[ks[i]]; ks = Object.keys(o); for (i = 0; i < ks.length; i++) q[ks[i]] = o[ks[i]]; return q; }
  function init() { return { t: 0 }; }
  function step(s, p, dt) { s.t += dt; }
  function tOf(s) { return s.t || 0; }
  function rd(x) { return Math.round(x); }   // x is never exactly .5 in the half-away vs half-even sense used below

  function hh(i, seed) {
    var x = (Math.imul(i, 374761393) + Math.imul(seed, 668265263)) >>> 0;
    x = Math.imul((x ^ (x >>> 13)) >>> 0, 1274126177) >>> 0;
    x = (x ^ (x >>> 16)) >>> 0;
    return x / 4294967296.0;
  }
  function gg(i, seed) { var s = hh(i * 4, seed) + hh(i * 4 + 1, seed) + hh(i * 4 + 2, seed) + hh(i * 4 + 3, seed); return (s - 2.0) * 1.7320508075688772; }
  // Python's round() is half-to-even; JS Math.round is half-up. Match Python exactly.
  function pyround(x) { var f = Math.floor(x), d = x - f; if (d < 0.5) return f; if (d > 0.5) return f + 1; return (f % 2 === 0) ? f : f + 1; }

  // ---------------------------------------------------------------- X-ray powder diffraction
  var FCC = [[0, 0, 0], [0, 0.5, 0.5], [0.5, 0, 0.5], [0.5, 0.5, 0]];
  var NOMINAL_A = { 1: 5.431, 2: 3.905, 3: 8.39 };
  var ZMV = { 1: [8.0, 28.0855], 2: [1.0, 183.484], 3: [8.0, 234.619] };

  function atoms(t, ox) {
    var basis, out = [], i, j, x;
    if (t === 2) return [[38, 0, 0, 0], [22, 0.5, 0.5, 0.5], [8, 0.5, 0.5, 0], [8, 0.5, 0, 0.5], [8, 0, 0.5, 0.5]];
    if (t === 1) basis = [[14, 0, 0, 0], [14, 0.25, 0.25, 0.25]];
    else {
      x = ox;
      basis = [[26, 0.125, 0.125, 0.125], [26, 0.875, 0.375, 0.375],
        [26.5, 0.5, 0.5, 0.5], [26.5, 0.25, 0.75, 0.0], [26.5, 0.75, 0.0, 0.25], [26.5, 0.0, 0.25, 0.75],
        [8, x, x, x], [8, -x + 0.75, -x + 0.25, x + 0.5], [8, -x + 0.25, x + 0.5, -x + 0.75],
        [8, x + 0.5, -x + 0.75, -x + 0.25], [8, -x, -x, -x], [8, x + 0.25, x + 0.75, -x + 0.5],
        [8, x + 0.75, -x + 0.5, x + 0.25], [8, -x + 0.5, x + 0.25, x + 0.75]];
    }
    for (i = 0; i < FCC.length; i++) for (j = 0; j < basis.length; j++) out.push([basis[j][0], basis[j][1] + FCC[i][0], basis[j][2] + FCC[i][1], basis[j][3] + FCC[i][2]]);
    return out;
  }
  function mult(h, k, l) {
    var nz = (h ? 1 : 0) + (k ? 1 : 0) + (l ? 1 : 0), perms;
    if (h === k && k === l) perms = 1; else if (h === k || k === l || h === l) perms = 3; else perms = 6;
    return perms * (1 << nz);
  }
  function nsf(t, a, nmax, ox) {
    var at = atoms(t, ox === undefined ? 0.256 : ox), sz = 0, out = {}, i, hmax, h, k, l, n, sa, ff, re, im, ph, f2;
    for (i = 0; i < at.length; i++) sz += at[i][0];
    hmax = Math.floor(Math.sqrt(nmax)) + 1;
    for (h = 0; h <= hmax; h++) for (k = 0; k <= h; k++) for (l = 0; l <= k; l++) {
      n = h * h + k * k + l * l;
      if (n === 0 || n > nmax) continue;
      sa = Math.sqrt(n) / (2.0 * a); ff = Math.exp(-2.0 * sa * sa); re = 0; im = 0;
      for (i = 0; i < at.length; i++) {
        ph = 2.0 * PI * (h * at[i][1] + k * at[i][2] + l * at[i][3]);
        re += at[i][0] * ff * Math.cos(ph); im += at[i][0] * ff * Math.sin(ph);
      }
      f2 = re * re + im * im;
      if (f2 < 1e-6 * sz * sz * ff * ff) continue;
      out[n] = (out[n] || 0) + mult(h, k, l) * f2;
    }
    return out;
  }
  function sortedKeys(o) { return Object.keys(o).map(Number).sort(function (a, b) { return a - b; }); }
  function refl(t, a, lam, tmin, tmax) {
    var nmax = Math.floor(Math.pow(2.0 * a / lam, 2)) + 1, ns = nsf(t, a, nmax), ks = sortedKeys(ns), out = [], i, n, s, th, tth, c2, lp;
    for (i = 0; i < ks.length; i++) {
      n = ks[i]; s = lam * Math.sqrt(n) / (2.0 * a);
      if (s >= 1.0) continue;
      th = Math.asin(s); tth = 2.0 * th / D2R;
      if (tth < tmin || tth > tmax) continue;
      c2 = Math.cos(2.0 * th); lp = (1.0 + c2 * c2) / (s * s * Math.cos(th));
      out.push({ N: n, tth: tth, sf: ns[n], lp: lp, G: ns[n] * lp / Math.pow(a, 6) });
    }
    return out;
  }
  function phaseList(p) {
    var out = [[pyround(p.t1), p.a1 * 1e10, p.w1]];
    if (pyround(p.t2) > 0) out.push([pyround(p.t2), p.a2 * 1e10, 1.0 - p.w1]);
    return out;
  }
  function xrdPeaks(p) {
    var lam = p.lam * 1e10, pk = [], ph = phaseList(p), i, j, t, a, w, zm, sp, rs, r, th, bs, beta;
    for (i = 0; i < ph.length; i++) {
      t = ph[i][0]; a = ph[i][1]; w = ph[i][2]; zm = ZMV[t];
      sp = w * 1.0e4 / (zm[0] * zm[1] * Math.pow(a, 3));
      rs = refl(t, a, lam, p.tmin - 2.0, p.tmax + 2.0);
      for (j = 0; j < rs.length; j++) {
        r = rs[j]; th = r.tth * D2R / 2.0;
        bs = 0.9 * p.lam / (p.Lx * Math.cos(th)) / D2R; beta = Math.sqrt(p.binst * p.binst + bs * bs);
        pk.push({ tth: r.tth, area: p.I0 * sp * r.G, beta: beta });
      }
    }
    return pk;
  }
  function xrdCounts(x, p, pk, i) {
    var base = p.bg, c = 2.0 * Math.sqrt(Math.log(2.0) / PI), j, q, d, v;
    for (j = 0; j < pk.length; j++) {
      q = pk[j]; d = x - q.tth;
      if (Math.abs(d) < 5.0 * q.beta) base += q.area * c / q.beta * Math.exp(-4.0 * Math.log(2.0) * d * d / (q.beta * q.beta));
    }
    v = base + Math.sqrt(Math.max(base, 1.0)) * gg(i, Math.trunc(p.seed));
    return v > 0.0 ? v : 0.0;
  }
  function xrdScan(p) {
    var pk = xrdPeaks(p), n = pyround((p.tmax - p.tmin) / 0.02) + 1, xs = [], ys = [], i, x;
    for (i = 0; i < n; i++) { x = p.tmin + 0.02 * i; xs.push(x); ys.push(xrdCounts(x, p, pk, i)); }
    return [xs, ys];
  }
  function smooth5(y) {
    var n = y.length, out = [], i, lo, hi, s, j;
    for (i = 0; i < n; i++) { lo = Math.max(0, i - 2); hi = Math.min(n - 1, i + 2); s = 0; for (j = lo; j <= hi; j++) s += y[j]; out.push(s / (hi - lo + 1)); }
    return out;
  }
  function findLines(xs, ys) {
    var n = ys.length, out = [], sm, low, bg, thr, step, w = 7, i, j, v, ok, half, l, r, xl, xr, fw, sw, sx, wt, c, area, k;
    if (n < 20) return out;
    sm = smooth5(ys);
    low = sm.slice().sort(function (a, b) { return a - b; }).slice(0, Math.max(1, Math.floor(n / 5)));
    bg = 0; for (k = 0; k < low.length; k++) bg += low[k]; bg /= low.length;
    thr = bg + 10.0 * Math.sqrt(bg); step = xs[1] - xs[0];
    for (i = w; i < n - w; i++) {
      v = sm[i]; if (v < thr) continue;
      ok = true;
      for (j = i - w; j < i; j++) if (sm[j] >= v) { ok = false; break; }
      if (ok) for (j = i + 1; j < i + w + 1; j++) if (sm[j] > v) { ok = false; break; }
      if (!ok) continue;
      half = bg + 0.5 * (v - bg);
      l = i; while (l > 0 && sm[l] > half) l--;
      r = i; while (r < n - 1 && sm[r] > half) r++;
      xl = sm[l + 1] !== sm[l] ? xs[l] + (half - sm[l]) / (sm[l + 1] - sm[l]) * step : xs[l];
      xr = sm[r - 1] !== sm[r] ? xs[r] - (half - sm[r]) / (sm[r - 1] - sm[r]) * step : xs[r];
      fw = xr - xl; sw = 0; sx = 0;
      for (j = l; j <= r; j++) { wt = ys[j] - bg; if (wt > 0) { sw += wt; sx += wt * xs[j]; } }
      c = sw > 0 ? sx / sw : xs[i];
      area = 0; for (j = 0; j < n; j++) if (Math.abs(xs[j] - c) <= 2.0 * fw) area += (ys[j] - bg) * step;
      out.push({ tth: c, fwhm: fw, area: area, height: v - bg });
    }
    return out;
  }
  function indexPhase(lines, lam, t, used) {
    var ns = nsf(t, NOMINAL_A[t], 140, undefined), allowed = sortedKeys(ns), free = [], i, a, b, j, k, best = null, si, n0, ac, pairs, res, sj, est, bn, bd, d, nk, sk, dt, pred, th, tk, c2, top, miss, seen, sc, e, sn, sd, s2, kk;
    for (i = 0; i < lines.length; i++) if (!used[i]) free.push(i);
    for (a = 0; a < Math.min(5, free.length); a++) {
      i = free[a]; si = Math.sin(lines[i].tth * D2R / 2.0);
      for (b = 0; b < Math.min(8, allowed.length); b++) {
        n0 = allowed[b]; ac = lam * Math.sqrt(n0) / (2.0 * si); pairs = []; res = 0;
        for (e = 0; e < free.length; e++) {
          j = free[e]; sj = Math.sin(lines[j].tth * D2R / 2.0); est = Math.pow(2.0 * ac * sj / lam, 2); bn = 0; bd = 1e9;
          for (k = 0; k < allowed.length; k++) { d = Math.abs(allowed[k] - est); if (d < bd) { bd = d; bn = allowed[k]; } }
          sk = lam * Math.sqrt(bn) / (2.0 * ac);
          if (sk >= 1.0) continue;
          dt = Math.abs(lines[j].tth - 2.0 * Math.asin(sk) / D2R);
          if (dt < 0.12) { pairs.push([j, bn]); res += dt * dt; }
        }
        pred = [];
        for (k = 0; k < allowed.length; k++) {
          nk = allowed[k]; sk = lam * Math.sqrt(nk) / (2.0 * ac);
          if (sk >= 1.0) break;
          th = Math.asin(sk); tk = 2.0 * th / D2R;
          if (tk < 20.0 || tk > 100.0) continue;
          c2 = Math.cos(2.0 * th); pred.push([tk, ns[nk] * (1.0 + c2 * c2) / (sk * sk * Math.cos(th))]);
        }
        top = 0; for (k = 0; k < pred.length; k++) if (pred[k][1] > top) top = pred[k][1];
        miss = 0;
        for (k = 0; k < pred.length; k++) if (pred[k][1] >= 0.05 * top) {
          seen = false;
          for (e = 0; e < free.length; e++) if (Math.abs(lines[free[e]].tth - pred[k][0]) < 0.15) { seen = true; break; }
          if (!seen) miss++;
        }
        sc = pairs.length - 2 * miss;
        if (best === null || sc > best[0] || (sc === best[0] && ac < best[3] - 1e-9)) best = [sc, res, pairs, ac];
      }
    }
    if (best === null || best[2].length < 3) return null;
    sn = 0; sd = 0;
    for (k = 0; k < best[2].length; k++) { s2 = Math.pow(Math.sin(lines[best[2][k][0]].tth * D2R / 2.0), 2); sn += best[2][k][1] * s2; sd += best[2][k][1] * best[2][k][1]; }
    kk = sn / sd;
    return { a: lam / (2.0 * Math.sqrt(kk)), pairs: best[2], n: best[2].length };
  }
  function xrdFit(p) {
    var lam = p.lam * 1e10, sc = xrdScan(p), lines = findLines(sc[0], sc[1]), used = [], i, ph = phaseList(p), sw = [], out, idx, t, r, j, a, rl, map, sg, sgg, q, g, sp, zm, jl, th, bo, bi, tot, k, best;
    for (i = 0; i < lines.length; i++) used.push(false);
    out = { a: 0.0, a2: 0.0, w1: 1.0, L: 0.0, n1: 0.0, n2: 0.0, lines: lines.length };
    for (idx = 0; idx < ph.length; idx++) {
      t = ph[idx][0]; r = indexPhase(lines, lam, t, used);
      if (r === null) { sw.push(0.0); continue; }
      for (j = 0; j < r.pairs.length; j++) used[r.pairs[j][0]] = true;
      a = r.a; rl = refl(t, a, lam, p.tmin - 2.0, p.tmax + 2.0); map = {};
      for (j = 0; j < rl.length; j++) map[rl[j].N] = rl[j];
      sg = 0; sgg = 0;
      for (j = 0; j < r.pairs.length; j++) {
        q = map[r.pairs[j][1]]; if (q === undefined) continue;
        g = q.sf * q.lp / Math.pow(a, 6); sg += lines[r.pairs[j][0]].area * g; sgg += g * g;
      }
      sp = sgg > 0 ? sg / (p.I0 * sgg) : 0.0; zm = ZMV[t];
      sw.push(sp * zm[0] * zm[1] * Math.pow(a, 3));
      out[idx === 0 ? 'a' : 'a2'] = a * 1e-10; out[idx === 0 ? 'n1' : 'n2'] = r.n;
      if (idx === 0) {
        best = r.pairs[0];
        for (k = 1; k < r.pairs.length; k++) if (lines[r.pairs[k][0]].tth > lines[best[0]].tth) best = r.pairs[k];
        jl = best[0]; th = lines[jl].tth * D2R / 2.0; bo = lines[jl].fwhm * D2R; bi = p.binst * D2R;
        if (bo > bi) out.L = 0.9 * p.lam / (Math.sqrt(bo * bo - bi * bi) * Math.cos(th));
      }
    }
    tot = 0; for (k = 0; k < sw.length; k++) tot += sw[k];
    out.w1 = (tot > 0 && sw.length > 0) ? sw[0] / tot : 1.0;
    return out;
  }
  var xrd = {
    PARAMS: { tth: 30.0, lam: 1.5406e-10, a1: 5.43102e-10, t1: 1.0, a2: 0.0, t2: 0.0, w1: 1.0, Lx: 5.0e-8, binst: 0.08, bg: 30.0, I0: 60.0, seed: 7.0, tmin: 20.0, tmax: 100.0 },
    VARS: ['t', 'I', 'tth'], init: init, step: step,
    view: function (s, p) { var pk = xrdPeaks(p), i = pyround((p.tth - p.tmin) / 0.02); return { t: tOf(s), I: xrdCounts(p.tth, p, pk, i), tth: p.tth }; },
    measure: function (p) { var r = xrdFit(p); return { a: r.a, a2: r.a2, w1: r.w1, L: r.L, n1: r.n1, n2: r.n2, lines: r.lines }; },
    peaks: xrdPeaks, counts: xrdCounts, scan: xrdScan, findLines: findLines, indexPhase: indexPhase, refl: refl, nsf: nsf, ZMV: ZMV, fit: xrdFit
  };
  function xrd_a(p) { return p.a1; }
  function lsqA(rows, p) {
    var pts = rws(rows, ['N', 's2']), sn = 0, sd = 0, i;
    for (i = 0; i < pts.length; i++) { sn += pts[i][0] * pts[i][1]; sd += pts[i][0] * pts[i][0]; }
    if (sn <= 0 || sd <= 0) return 0.0;
    return p.lam / (2.0 * Math.sqrt(sn / sd));
  }

  // ---------------------------------------------------------------- X-ray reflectivity (Parratt)
  function delta(rho, ze, lam) { return RE * lam * lam * (NA * rho * 1000.0 * ze) / (2.0 * PI); }
  function csqrt(re, im) {
    var m = Math.sqrt(re * re + im * im), sr = Math.sqrt((m + re) / 2.0), si = Math.sqrt(Math.max((m - re) / 2.0, 0.0));
    return [sr, im < 0 ? -si : si];
  }
  function cmul(a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; }
  function cdiv(a, b) { var d = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; }
  function cexp(a) { var e = Math.exp(a[0]); return [e * Math.cos(a[1]), e * Math.sin(a[1])]; }
  function xrrLayers(p) {
    var lam = p.lam, df = delta(p.rho_f, p.ze_f, lam), db = delta(p.rho_b, p.ze_b, lam), ds = delta(p.rho_s, p.ze_s, lam), bf = p.bfrac, out = [], i, n;
    if (pyround(p.kind) === 1) return [[df, df * bf, p.d1], [ds, ds * bf, 0.0]];
    n = pyround(p.nrep);
    for (i = 0; i < n; i++) { out.push([df, df * bf, p.d1 * p.fa]); out.push([db, db * bf, p.d1 * (1.0 - p.fa)]); }
    out.push([ds, ds * bf, 0.0]);
    return out;
  }
  function parratt(theta, lay, lam, sig) {
    var k = 2.0 * PI / lam, s2 = Math.pow(Math.sin(theta), 2), kz = [], c, i, n = lay.length, x = [0, 0], j, num, den, r, ph, rx, e;
    c = csqrt(s2, 0.0); kz.push([k * c[0], k * c[1]]);
    for (i = 0; i < n; i++) { c = csqrt(s2 - 2.0 * lay[i][0], 2.0 * lay[i][1]); kz.push([k * c[0], k * c[1]]); }
    for (j = n - 1; j >= 0; j--) {
      num = [kz[j][0] - kz[j + 1][0], kz[j][1] - kz[j + 1][1]]; den = [kz[j][0] + kz[j + 1][0], kz[j][1] + kz[j + 1][1]];
      e = cmul(kz[j], kz[j + 1]);
      r = cmul(cdiv(num, den), cexp([-2.0 * e[0] * sig * sig, -2.0 * e[1] * sig * sig]));
      if (j + 1 <= n - 1) { var z = cmul(kz[j + 1], [0, 2.0 * lay[j][2]]); ph = cexp(z); } else ph = [0, 0];
      rx = cmul(x, ph);
      x = cdiv([r[0] + rx[0], r[1] + rx[1]], [1.0 + (r[0] * rx[0] - r[1] * rx[1]), r[0] * rx[1] + r[1] * rx[0]]);
    }
    return x[0] * x[0] + x[1] * x[1];
  }
  function peakpos(y, i, w) {
    var s2 = 0, s4 = 0, n = 2 * w + 1, sy = 0, suy = 0, su2y = 0, u, v, c1, c2, off;
    for (u = -w; u <= w; u++) { s2 += u * u; s4 += Math.pow(u, 4); }
    for (u = -w; u <= w; u++) { v = y[i + u]; sy += v; suy += u * v; su2y += u * u * v; }
    c1 = suy / s2; c2 = (n * su2y - s2 * sy) / (n * s4 - s2 * s2);
    if (c2 >= 0) return i;
    off = -c1 / (2.0 * c2);
    if (off > w) off = w; if (off < -w) off = -w;
    return i + off;
  }
  function xrrScan(p) {
    var lay = xrrLayers(p), n = pyround((p.tmax - p.tmin) / 0.01) + 1, xs = [], ys = [], i, x, r;
    for (i = 0; i < n; i++) {
      x = p.tmin + 0.01 * i; r = parratt(x * D2R / 2.0, lay, p.lam, p.sig);
      r = r * (1.0 + 0.004 * gg(i, Math.trunc(p.seed))) + p.bgr; xs.push(x); ys.push(r);
    }
    return [xs, ys];
  }
  function xrrFit(p) {
    var sc = xrrScan(p), xs = sc[0], ys = sc[1], n = ys.length, ly = [], i, j, tthc = xs[0], w = 4, mx = [], v, ok, kind = pyround(p.kind), keep, dom, out, pos = [], tlist = [], q, i0, fr, t, best = null, h2, m0, pts, ab, sse, k, bb;
    for (i = 0; i < n; i++) ly.push(Math.log(Math.max(ys[i], 1e-12)) / Math.LN10);
    for (i = 0; i < n; i++) if (ys[i] < 0.5) { tthc = xs[i]; break; }
    for (i = w; i < n - w; i++) {
      v = ly[i]; ok = true;
      for (j = i - w; j < i; j++) if (ly[j] >= v) { ok = false; break; }
      if (ok) for (j = i + 1; j < i + w + 1; j++) if (ly[j] > v) { ok = false; break; }
      if (ok && xs[i] > 1.3 * tthc) mx.push(i);
    }
    if (kind === 2 && mx.length) {
      keep = [];
      for (i = 0; i < mx.length; i++) {
        dom = true;
        for (j = 0; j < mx.length; j++) if (mx[j] !== mx[i] && Math.abs(xs[mx[j]] - xs[mx[i]]) <= 0.5 && ys[mx[j]] * 3.0 > ys[mx[i]]) { dom = false; break; }
        if (dom) keep.push(mx[i]);
      }
      mx = keep;
    }
    out = { d: 0.0, rho: 0.0, m0: 0.0, peaks: mx.length, tthc: tthc };
    if (mx.length < 3) return out;
    for (k = 0; k < mx.length; k++) {
      q = peakpos(ly, mx[k], 3); i0 = Math.floor(q); fr = q - i0; t = xs[i0] + fr * 0.01;
      pos.push(Math.pow(Math.sin(t * D2R / 2.0), 2)); tlist.push(t);
    }
    out.tths = tlist;
    for (h2 = 0; h2 <= 120; h2++) {
      m0 = h2 * 0.5; pts = [];
      for (k = 0; k < pos.length; k++) pts.push([Math.pow(m0 + k, 2), pos[k]]);
      ab = line(pts); if (ab[0] <= 0) continue;
      sse = 0; for (k = 0; k < pts.length; k++) sse += Math.pow(pts[k][1] - ab[0] * pts[k][0] - ab[1], 2);
      if (best === null || sse < best[0] - 1e-18) best = [sse, m0, ab[0], ab[1]];
    }
    if (best === null) return out;
    bb = best[3];
    out.m0 = best[1]; out.d = p.lam / (2.0 * Math.sqrt(best[2]));
    out.rho = bb > 0 ? (bb / 2.0) * 2.0 * PI / (RE * p.lam * p.lam * NA * 1000.0 * p.ze_f) / 1000.0 : 0.0;
    return out;
  }
  var xrr = {
    PARAMS: { tth: 2.0, lam: 1.5406e-10, kind: 1.0, d1: 4.0e-8, fa: 0.4, nrep: 10.0, rho_f: 19300.0, ze_f: 0.40106, rho_b: 2329.0, ze_b: 0.49848, rho_s: 2329.0, ze_s: 0.49848, sig: 4.0e-10, bfrac: 0.05, bgr: 1.0e-8, seed: 11.0, tmin: 0.1, tmax: 5.0 },
    VARS: ['t', 'R', 'logR', 'tth'], init: init, step: step,
    view: function (s, p) { var r = parratt(p.tth * D2R / 2.0, xrrLayers(p), p.lam, p.sig) + p.bgr; return { t: tOf(s), R: r, logR: Math.log(Math.max(r, 1e-12)) / Math.LN10, tth: p.tth }; },
    measure: function (p) { var r = xrrFit(p); return { d: r.d, rho: r.rho, m0: r.m0, peaks: r.peaks, tthc: r.tthc }; },
    refl: function (tth, p) { return parratt(tth * D2R / 2.0, xrrLayers(p), p.lam, p.sig); },
    scan: xrrScan, fit: xrrFit
  };
  function xrr_d(p) { return p.d1; }
  function fringeD(rows, p) {
    var pts = rws(rows, ['m', 's2']), q = [], i, ab;
    for (i = 0; i < pts.length; i++) q.push([pts[i][0] * pts[i][0], pts[i][1]]);
    ab = line(q); return ab[0] > 0 ? p.lam / (2.0 * Math.sqrt(ab[0])) : 0.0;
  }

  // ---------------------------------------------------------------- quartz crystal monitor
  var qcm = {
    PARAMS: { t: 0.0, f0: 6.0e6, rho_f: 19300.0, rate: 2.0e-10, tool: 0.8, Tdep: 300.0, rho_q: 2648.0, mu_q: 2.947e10, seed: 5.0 },
    VARS: ['t', 'f', 'df', 'thick_nm'], init: init, step: step,
    sens: function (p) { return 2.0 * p.f0 * p.f0 / Math.sqrt(p.rho_q * p.mu_q); },
    freq: function (p, t) { var th = p.rate * t; return p.f0 - qcm.sens(p) * p.rho_f * th + 0.4 * gg(pyround(t * 10.0), Math.trunc(p.seed)); },
    view: function (s, p) { var f = qcm.freq(p, p.t); return { t: tOf(s), f: f, df: f - p.f0, thick_nm: p.rate * p.t * 1e9 }; },
    measure: function (p) {
      var pts = [], i, m, rate, step, tool;
      for (i = 1; i < 9; i++) pts.push([10.0 * i, qcm.freq(p, 10.0 * i)]);
      m = line(pts)[0]; rate = -m / (qcm.sens(p) * p.rho_f); step = p.tool * p.rate * p.Tdep;
      tool = rate !== 0 ? step / (rate * p.Tdep) : 0.0;
      return { rate: rate, tool: tool, thick: rate * p.Tdep, step: step };
    }
  };
  function qcm_rate(p) { return p.rate; }
  function qcmCalc(rows, p) { var m = line(rws(rows, ['t', 'f']))[0], d = qcm.sens(p) * p.rho_f; return d !== 0 ? -m / d : 0.0; }

  // ---------------------------------------------------------------- high-vacuum pump-down
  var vac = {
    PARAMS: { t: 0.0, stage: 1.0, V: 0.05, Sr: 0.0028, Sp: 0.20, dt: 0.04, Lt: 0.30, T: 293.0, Mgas: 28.96, Pat: 101325.0, Px: 10.0, Pur: 1.0, QL: 5.0e-6, QO: 1.0e-4, tauo: 120.0, tc: 900.0 },
    VARS: ['t', 'P', 'logP', 'S', 'C'], init: init, step: step,
    cond: function (p) { var vb = Math.sqrt(8.0 * KB * p.T / (PI * p.Mgas * AMU)); return PI / 12.0 * vb * Math.pow(p.dt, 3) / p.Lt; },
    seff: function (p) { var c = vac.cond(p); return p.Sp * c / (p.Sp + c); },
    p1: function (p, t) {
      var s = vac.seff(p), lam = s / p.V, pinf = p.QL / s, a = p.QO / (p.V * (lam - 1.0 / p.tauo));
      return pinf + (p.Px - pinf - a) * Math.exp(-lam * t) + a * Math.exp(-t / p.tauo);
    },
    pressure: function (p) {
      var st = pyround(p.stage), t = p.t, pc;
      if (st === 0) return p.Pur + (p.Pat - p.Pur) * Math.exp(-p.Sr * t / p.V);
      if (st === 1) return vac.p1(p, t);
      pc = vac.p1(p, p.tc);
      return pc + p.QL / p.V * t + p.QO * p.tauo / p.V * Math.exp(-p.tc / p.tauo) * (1.0 - Math.exp(-t / p.tauo));
    },
    view: function (s, p) { var pr = vac.pressure(p); return { t: tOf(s), P: pr, logP: Math.log(pr) / Math.LN10, S: vac.seff(p), C: vac.cond(p) }; },
    measure: function (p) {
      var q = over(p, 'stage', 1.0), pts = [], i, m, sEff, inv, c, late, pl = [], u, ql, early, pe = [], qe, us;
      for (i = 1; i < 7; i++) { q.t = i; pts.push([i, Math.log(vac.pressure(q))]); }
      m = line(pts)[0]; sEff = -p.V * m; inv = 1.0 / sEff - 1.0 / p.Sp; c = inv > 0 ? 1.0 / inv : 0.0;
      late = withp(p, { stage: 2.0, tc: 1800.0 }); us = [20.0, 60.0, 100.0, 140.0];
      for (i = 0; i < us.length; i++) { late.t = us[i]; pl.push([us[i], vac.pressure(late)]); }
      ql = p.V * line(pl)[0];
      early = withp(p, { stage: 2.0, tc: 200.0 }); us = [10.0, 30.0, 50.0];
      for (i = 0; i < us.length; i++) { early.t = us[i]; pe.push([us[i], vac.pressure(early)]); }
      qe = p.V * line(pe)[0];
      return { C: c, S: sEff, QL: ql, Qout: qe - ql };
    }
  };
  function vac_C(p) { return vac.cond(p); }
  function vacCalc(rows, p) {
    var m = line(rws(rows, ['t', 'lnP']))[0], s = -p.V * m, inv = s !== 0 ? (1.0 / s - 1.0 / p.Sp) : 0.0;
    return inv > 0 ? 1.0 / inv : 0.0;
  }

  // ---------------------------------------------------------------- sheet resistance
  function vdpX(rs, r) {
    var lo = 0.0, hi = rs, i, mid;
    for (i = 0; i < 200; i++) { mid = 0.5 * (lo + hi); if (Math.exp(-PI * r * mid / rs) + Math.exp(-PI * mid / rs) - 1.0 > 0.0) lo = mid; else hi = mid; }
    return 0.5 * (lo + hi);
  }
  function vdpSolve(r1, r2) {
    var s = r1 + r2, lo, hi, i, mid;
    if (s <= 0) return 0.0;
    lo = 0.01 * s; hi = 100.0 * s;
    for (i = 0; i < 200; i++) { mid = 0.5 * (lo + hi); if (Math.exp(-PI * r1 / mid) + Math.exp(-PI * r2 / mid) - 1.0 > 0.0) hi = mid; else lo = mid; }
    return 0.5 * (lo + hi);
  }
  var sheet = {
    PARAMS: { mode: 0.0, sel: 0.0, Rs: 95.0, t: 5.25e-4, r: 1.18, I: 1.0e-3, Voff: 3.5e-6 },
    VARS: ['t', 'V', 'Vrev', 'R'], init: init, step: step,
    res: function (p) {
      var x;
      if (pyround(p.mode) === 1) return p.Rs * Math.log(2.0) / PI;
      x = vdpX(p.Rs, p.r); return pyround(p.sel) === 0 ? p.r * x : x;
    },
    view: function (s, p) { var r = sheet.res(p), v = p.I * r + p.Voff, vr = -p.I * r + p.Voff; return { t: tOf(s), V: v, Vrev: vr, R: (v - vr) / (2.0 * p.I) }; },
    measure: function (p) {
      var rs, pts = [], i, q, v, a, b;
      if (pyround(p.mode) === 1) {
        for (i = 1; i < 6; i++) { q = over(p, 'I', 1.0e-3 * i); v = sheet.view({}, q); pts.push([q.I, v.V]); }
        rs = line(pts)[0] * PI / Math.log(2.0);
      } else {
        a = sheet.view({}, over(p, 'sel', 0.0)).R; b = sheet.view({}, over(p, 'sel', 1.0)).R; rs = vdpSolve(a, b);
      }
      return { Rs: rs, rho: rs * p.t };
    }
  };
  function sheet_Rs(p) { return p.Rs; }
  function vdpCalc(rows) {
    var pts = rws(rows, ['R1', 'R2']), r1 = 0, r2 = 0, i;
    if (!pts.length) return 0.0;
    for (i = 0; i < pts.length; i++) { r1 += pts[i][0]; r2 += pts[i][1]; }
    r1 /= pts.length; r2 /= pts.length;
    return (r1 > 0 && r2 > 0) ? vdpSolve(r1, r2) : 0.0;
  }
  function fppCalc(rows) { return line(rws(rows, ['I', 'V']))[0] * PI / Math.log(2.0); }

  // ---------------------------------------------------------------- Haynes-Shockley
  var hs = {
    PARAMS: { t: 0.0, L: 0.01, E: 2000.0, mu: 0.19, T: 300.0, tau: 1.0e-4, N: 1.0e-3, gain: 50.0 },
    VARS: ['t', 'V', 'td'], init: init, step: step,
    diff: function (p) { return p.mu * KB * p.T / QE; },
    sig: function (p, t) {
      var d, v, n;
      if (t <= 0) return 0.0;
      d = hs.diff(p); v = p.mu * p.E;
      n = p.N * Math.exp(-t / p.tau) / Math.sqrt(4.0 * PI * d * t) * Math.exp(-Math.pow(p.L - v * t, 2) / (4.0 * d * t));
      return p.gain * n;
    },
    view: function (s, p) { return { t: tOf(s), V: hs.sig(p, p.t), td: p.L / (p.mu * p.E) }; },
    pulse: function (p) {
      var td0 = p.L / (p.mu * p.E), n = 2400, t0 = 0.3 * td0, t1 = 2.2 * td0, dt = (t1 - t0) / (n - 1), ts = [], ys = [], i, im = 0, y0, y1, y2, den, off, tpk, hm, l, r, tl, tr, area = 0;
      for (i = 0; i < n; i++) { ts.push(t0 + dt * i); ys.push(hs.sig(p, ts[i])); }
      for (i = 0; i < n; i++) if (ys[i] > ys[im]) im = i;
      im = Math.min(Math.max(im, 1), n - 2);
      y0 = ys[im - 1]; y1 = ys[im]; y2 = ys[im + 1]; den = y0 - 2.0 * y1 + y2;
      off = den !== 0 ? 0.5 * (y0 - y2) / den : 0.0; tpk = ts[im] + off * dt; hm = 0.5 * y1;
      l = im; while (l > 0 && ys[l] > hm) l--;
      r = im; while (r < n - 1 && ys[r] > hm) r++;
      tl = ts[l] + (hm - ys[l]) / (ys[l + 1] - ys[l]) * dt; tr = ts[r] - (hm - ys[r]) / (ys[r - 1] - ys[r]) * dt;
      for (i = 0; i < n - 1; i++) area += 0.5 * (ys[i] + ys[i + 1]) * dt;
      return { tpk: tpk, fwhm: tr - tl, area: area, peak: y1 };
    },
    measure: function (p) {
      var se = 0, sv = 0, tdl = [], lav = [], dres = 0, es = [1000.0, 1500.0, 2000.0, 2500.0, 3000.0], i, e, q, r, v, sg, pts = [], m, mu, tau;
      for (i = 0; i < es.length; i++) {
        e = es[i]; q = over(p, 'E', e); r = hs.pulse(q); v = p.L / r.tpk;
        se += e * e; sv += v * e; tdl.push(r.tpk); lav.push(Math.log(r.area * v));
        if (e === 2000.0) { sg = r.fwhm / 2.3548200450309493; dres = sg * sg * v * v / (2.0 * r.tpk); }
      }
      mu = sv / se;
      for (i = 0; i < tdl.length; i++) pts.push([tdl[i], lav[i]]);
      m = line(pts)[0]; tau = m < 0 ? -1.0 / m : 0.0;
      return { mu: mu, D: dres, tau: tau };
    }
  };
  function hs_mu(p) { return p.mu; }
  function hsCalc(rows) {
    var pts = rws(rows, ['E', 'v']), se = 0, sv = 0, i;
    for (i = 0; i < pts.length; i++) { se += pts[i][0] * pts[i][0]; sv += pts[i][1] * pts[i][0]; }
    return se > 0 ? sv / se : 0.0;
  }

  // ---------------------------------------------------------------- solar cell
  function scCur(v, p) {
    var vt = KB * p.T / QE, iph = p.Jsc1 * p.A * p.G / 1000.0, i0 = p.J0 * p.A, rs = p.rs / p.A, rsh = p.rsh / p.A, lo = -100.0, hi = iph + 1.0, k, mid, ex, f;
    for (k = 0; k < 200; k++) {
      mid = 0.5 * (lo + hi); ex = (v + mid * rs) / (p.n * vt); if (ex > 700.0) ex = 700.0;
      f = iph - i0 * (Math.exp(ex) - 1.0) - (v + mid * rs) / rsh - mid;
      if (f > 0.0) lo = mid; else hi = mid;
    }
    return 0.5 * (lo + hi);
  }
  function scSweep(p, dv) {
    var i0 = scCur(0.0, p), vs = [0.0], is = [i0], voc = 0, k = 0, v, i, pi_, vi_, pw = [], j, im = 0, y0, y1, y2, den, off, pmax;
    for (;;) {
      k++; v = dv * k; i = scCur(v, p);
      if (i <= 0.0 || k > 4000) { pi_ = is[is.length - 1]; vi_ = vs[vs.length - 1]; voc = pi_ !== i ? vi_ + pi_ / (pi_ - i) * dv : vi_; break; }
      vs.push(v); is.push(i);
    }
    for (j = 0; j < vs.length; j++) pw.push(vs[j] * is[j]);
    for (j = 0; j < pw.length; j++) if (pw[j] > pw[im]) im = j;
    im = Math.min(Math.max(im, 1), pw.length - 2);
    y0 = pw[im - 1]; y1 = pw[im]; y2 = pw[im + 1]; den = y0 - 2.0 * y1 + y2;
    off = den !== 0 ? 0.5 * (y0 - y2) / den : 0.0; pmax = y1 - 0.25 * (y0 - y2) * off;
    return { Voc: voc, Isc: i0, Pmax: pmax, FF: pmax / (voc * i0), eta: pmax / (p.G * p.A), Vmp: vs[im] + off * dv };
  }
  var solar = {
    PARAMS: { V: 0.0, G: 1000.0, A: 4.0e-4, Jsc1: 400.0, n: 1.2, J0: 1.0e-7, rs: 5.0e-5, rsh: 0.1, T: 300.0 },
    VARS: ['t', 'I', 'Pw', 'V'], init: init, step: step,
    view: function (s, p) { var i = scCur(p.V, p); return { t: tOf(s), I: i, Pw: p.V * i, V: p.V }; },
    measure: function (p) { var r = scSweep(p, 0.0025); return { Voc: r.Voc, Isc: r.Isc, Pmax: r.Pmax, FF: r.FF, eta: r.eta }; },
    exact: function (p) { return scSweep(p, 0.0005); }
  };
  function sc_Voc(p) { var vt = KB * p.T / QE; return p.n * vt * Math.log(p.Jsc1 * p.G / 1000.0 / p.J0 + 1.0); }
  function scEta(rows, p) {
    var pts = rws(rows, ['V', 'I']), pm = 0, i;
    for (i = 0; i < pts.length; i++) if (pts[i][0] * pts[i][1] > pm) pm = pts[i][0] * pts[i][1];
    return p.G * p.A > 0 ? pm / (p.G * p.A) : 0.0;
  }

  H0.register({
    K: { ph2_xrd: xrd, ph2_xrr: xrr, ph2_qcm: qcm, ph2_vac: vac, ph2_sheet: sheet, ph2_hs: hs, ph2_solar: solar },
    TEXTBOOK: { ph2_a: xrd_a, ph2_d: xrr_d, ph2_rate: qcm_rate, ph2_C: vac_C, ph2_Rs: sheet_Rs, ph2_mu: hs_mu, ph2_Voc: sc_Voc },
    CALCS: {
      ph2_lsq_a: { label: 'lattice parameter', unit: 'm', needs: ['N', 's2'], fn: lsqA },
      ph2_fringe: { label: 'film thickness', unit: 'm', needs: ['m', 's2'], fn: fringeD },
      ph2_sauerbrey: { label: 'deposition rate', unit: 'm/s', needs: ['t', 'f'], fn: qcmCalc },
      ph2_conductance: { label: 'tube conductance', unit: 'm3/s', needs: ['t', 'lnP'], fn: vacCalc },
      ph2_vdp: { label: 'sheet resistance', unit: 'ohm', needs: ['R1', 'R2'], fn: vdpCalc },
      ph2_fpp: { label: 'sheet resistance', unit: 'ohm', needs: ['I', 'V'], fn: fppCalc },
      ph2_drift: { label: 'drift mobility', unit: 'm2/Vs', needs: ['E', 'v'], fn: hsCalc },
      ph2_eta: { label: 'efficiency', unit: '', needs: ['V', 'I'], fn: scEta }
    }
  });
})(typeof window !== 'undefined' ? window : this);
