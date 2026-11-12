/* Kernel pack (browser twin of app/prayog/packs/phd_astro_w10.py): PhD nuclear / particle / cosmic-ray, radio
   astronomy / astrophysics data and computational research techniques, wave 10. Same formulas, same order of
   operations, so both sides give the same numbers. Deterministic: anything random is the seeded Lehmer generator
   (16807, mod 2^31 - 1) and Box-Muller, never the clock.
     pa10_tof (muon time of flight)   pa10_zenith (cos^n zenith law)   pa10_reldyn (relativistic beta electrons)
     pa10_cher (Cherenkov threshold, Frank-Tamm)   pa10_sipm (CTR with CFD / walk-corrected LE; finger spectrum)
     pa10_radio (drift-scan beam, Y-factor, source flux)   pa10_hubble (Hubble constant)   pa10_cmd (cluster distance, turn-off age)
     pa10_lsp (Lomb-Scargle / PDM period, amplitude, P-L distance)   pa10_schro (Numerov shooting, split-step tunnelling)
   Detector, telescope and archive data are SIMULATED DATA from a hidden value. */
(function (root) {
  'use strict';
  var PI = Math.PI, M31 = 2147483647;
  var C_SI = 299792458.0, C_NS = 0.299792458, C_KMS = 299792.458, KB = 1.380649e-23, FT = 369.81;
  var HARTREE_EV = 27.211386245988, SIDEREAL = 0.25068, FW = 2.0 * Math.sqrt(2.0 * Math.log(2.0));

  function I(v) { return Math.floor(v + 0.5); }
  function errOf(val, exact) { return Math.abs(val - exact) / Math.max(Math.abs(exact), 1e-30); }
  function mod(a, b) { var r = a % b; return r < 0 ? r + b : r; }
  function lcg(seed) { var s = mod(I(seed), M31); return [s > 0 ? s : 1]; }
  function u(st) { st[0] = (st[0] * 16807) % M31; return st[0] / M31; }
  function g(st) { var a = u(st), b = u(st); return Math.sqrt(-2.0 * Math.log(a)) * Math.cos(2.0 * PI * b); }
  function poisson(st, mu) {
    var lim = Math.exp(-mu), k = 0, q = u(st);
    while (q > lim) { k += 1; q *= u(st); }
    return k;
  }
  function thin(xs, m) {
    var n = xs.length, out = [], i;
    if (n <= m + 1) return xs.slice();
    for (i = 0; i <= m; i++) out.push(xs[I(i * (n - 1) / m)]);
    return out;
  }
  function wline(xs, ys, ws) {
    var n = xs.length, sw = 0, sx = 0, sy = 0, sxx = 0, sxy = 0, k, w, den, b;
    if (n < 2) return [0, 0];
    for (k = 0; k < n; k++) {
      w = ws[k]; sw += w; sx += w * xs[k]; sy += w * ys[k]; sxx += w * xs[k] * xs[k]; sxy += w * xs[k] * ys[k];
    }
    den = sw * sxx - sx * sx;
    if (Math.abs(den) < 1e-300) return [0, 0];
    b = (sw * sxy - sx * sy) / den;
    return [(sy - b * sx) / sw, b];
  }
  function line(xs, ys) { var ws = [], k; for (k = 0; k < xs.length; k++) ws.push(1.0); return wline(xs, ys, ws); }
  function hist(vals, lo, hi, nb) {
    var cx = [], cy = [], k, i;
    for (k = 0; k < nb; k++) { cx.push(lo + (hi - lo) * (k + 0.5) / nb); cy.push(0.0); }
    for (i = 0; i < vals.length; i++) {
      k = Math.floor((vals[i] - lo) / (hi - lo) * nb);
      if (k >= 0 && k < nb) cy[k] += 1.0;
    }
    return [cx, cy];
  }
  function solve(A, b) {
    var n = b.length, M = [], r, c, k, piv, d, f, x, s, tmp;
    for (r = 0; r < n; r++) M.push(A[r].slice().concat([b[r]]));
    for (c = 0; c < n; c++) {
      piv = c;
      for (r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r;
      if (piv !== c) { tmp = M[c]; M[c] = M[piv]; M[piv] = tmp; }
      d = M[c][c];
      if (Math.abs(d) < 1e-300) { x = []; for (k = 0; k < n; k++) x.push(0.0); return x; }
      for (r = c + 1; r < n; r++) {
        f = M[r][c] / d;
        if (f !== 0.0) for (k = c; k < n + 1; k++) M[r][k] -= f * M[c][k];
      }
    }
    x = []; for (k = 0; k < n; k++) x.push(0.0);
    for (r = n - 1; r >= 0; r--) {
      s = M[r][n];
      for (k = r + 1; k < n; k++) s -= M[r][k] * x[k];
      x[r] = s / M[r][r];
    }
    return x;
  }
  function base(val, exact, nused, cx, ce, cy, px, py, extra) {
    var s = { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: nused, cx: cx, ce: ce, cy: cy, px: px, py: py }, k;
    if (extra) for (k in extra) s[k] = extra[k];
    return s;
  }
  function copy(s) { var o = {}, k; for (k in s) o[k] = s[k]; return o; }
  function kernel(params, init) {
    return {
      PARAMS: params, VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'],
      init: init,
      step: function (s, p, dt) { s.t += dt; },
      view: function (s) { return copy(s); },
      measure: function (p) { var s = init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
    };
  }

  // ====================================================================================== muon time of flight
  function tofExact(p) { return p.beta; }
  var PaTof = kernel({ beta: 0.9965, t0: 12.0, sig: 0.8, dmax: 2.5, nd: 6.0, n: 3200.0, what: 0.0, method: 0.0, seed: 101.0 }, function (p) {
    var n = Math.max(5, I(p.n)), nd = Math.max(3, I(p.nd)), st = lcg(p.seed), xs = [], ys = [], k, j, d, s;
    for (k = 0; k < nd; k++) {
      d = p.dmax * k / (nd - 1); s = 0.0;
      for (j = 0; j < n; j++) s += p.t0 + d / (p.beta * C_NS) + p.sig * g(st);
      xs.push(d); ys.push(s / n);
    }
    var ab = line(xs, ys), b = ab[1], v = b > 0 ? 1.0 / b : 0.0, val = v / C_NS;
    return base(val, tofExact(p), nd * n, [0.0, p.dmax], [], [ab[0], ab[0] + b * p.dmax], xs, ys, { slope: b, offset: ab[0], v: v });
  });

  // ====================================================================================== cosmic-ray zenith law
  function zenExact(p) {
    var w = I(p.what);
    if (w === 1) return p.I0;
    if (w === 2) return p.I0 * 2.0 * PI / (p.nexp + 2.0);
    return p.nexp;
  }
  var PaZenith = kernel({ nexp: 2.0, I0: 70.0, A: 0.09, D: 1.0, eff: 0.95, amax: 75.0, na: 6.0, n: 960.0, what: 0.0, method: 0.0, seed: 103.0 }, function (p) {
    var na = Math.max(3, I(p.na)), T = Math.max(1.0, p.n) * 60.0, st = lcg(p.seed), G = p.A * p.A / (p.D * p.D);
    var xs = [], ys = [], ws = [], px = [], py = [], k, th, c, mu, N;
    for (k = 0; k < na; k++) {
      th = p.amax * k / (na - 1); c = Math.cos(th * PI / 180.0);
      mu = p.eff * p.I0 * G * Math.pow(c, p.nexp) * T;
      N = Math.max(1, I(mu + Math.sqrt(mu) * g(st)));
      xs.push(Math.log(c)); ys.push(Math.log(N / T)); ws.push(N); px.push(th); py.push(N / T * 60.0);
    }
    var ab = wline(xs, ys, ws), nf = ab[1], I0 = Math.exp(ab[0]) / (p.eff * G), J = I0 * 2.0 * PI / (nf + 2.0);
    var w = I(p.what), val = w === 1 ? I0 : w === 2 ? J : nf, cx = [], cy = [];
    for (k = 0; k < 31; k++) { th = p.amax * k / 30.0; cx.push(th); cy.push(Math.exp(ab[0]) * Math.pow(Math.cos(th * PI / 180.0), nf) * 60.0); }
    return base(val, zenExact(p), na * p.n, cx, [], cy, px, py, { nfit: nf, I0fit: I0, J: J });
  });

  // ====================================================================================== relativistic dynamics
  function relExact(p) {
    if (I(p.what) === 1) return C_SI * C_SI / (p.mc2 * 1.0e6) / 1.0e11;
    return p.mc2;
  }
  var PaReldyn = kernel({ r: 0.2, mc2: 0.51099895, Bmin: 0.004, Bmax: 0.016, nb: 7.0, sT: 0.05, sv: 0.004, n: 640.0, what: 0.0, method: 0.0, seed: 107.0 }, function (p) {
    var n = Math.max(2, I(p.n)), nb = Math.max(3, I(p.nb)), st = lcg(p.seed);
    var xs = [], ys = [], Bs = [], ems = [], k, j, B, pc, E, T, beta, sT, sb, Tm, bm;
    for (k = 0; k < nb; k++) {
      B = p.Bmin + (p.Bmax - p.Bmin) * k / (nb - 1);
      pc = C_SI * B * p.r / 1.0e6; E = Math.sqrt(pc * pc + p.mc2 * p.mc2); T = E - p.mc2; beta = pc / E;
      sT = 0.0; sb = 0.0;
      for (j = 0; j < n; j++) { sT += T * (1.0 + p.sT * g(st)); sb += beta * (1.0 + p.sv * g(st)); }
      Tm = sT / n; bm = Math.min(sb / n, 0.999999);
      xs.push(Tm); ys.push(pc * pc - Tm * Tm); Bs.push(B * 1000.0);
      ems.push(bm * C_SI / Math.sqrt(1.0 - bm * bm) / (B * p.r) / 1.0e11);
    }
    var ab = line(xs, ys), mfit = ab[1] / 2.0, em = 0.0, val, px, py, cx, cy;
    for (k = 0; k < ems.length; k++) em += ems[k];
    em = em / nb;
    if (I(p.what) === 1) { val = em; px = Bs; py = ems; cx = [Bs[0], Bs[nb - 1]]; cy = [em, em]; }
    else { val = mfit; px = xs; py = ys; cx = [0.0, xs[nb - 1]]; cy = [ab[0], ab[0] + ab[1] * xs[nb - 1]]; }
    return base(val, relExact(p), nb * n, cx, [], cy, px, py, { mfit: mfit, em: em });
  });

  // ====================================================================================== Cherenkov threshold
  function cherExact(p) {
    if (I(p.what) === 1) return p.eps * FT * p.dE * (1.0 - 1.0 / (p.nidx * p.nidx));
    return 1.0 / p.nidx;
  }
  var PaCher = kernel({ nidx: 1.333, L: 10.0, mass: 139.57039, pmin: 250.0, pmax: 2000.0, np: 8.0, eps: 0.08, dE: 1.0, n: 400.0, what: 0.0, method: 0.0, seed: 109.0 }, function (p) {
    var n = Math.max(2, I(p.n)), npnt = Math.max(3, I(p.np)), st = lcg(p.seed), K = p.eps * FT * p.dE * p.L;
    var xs = [], ys = [], k, j, pm, beta, mu, s, v;
    for (k = 0; k < npnt; k++) {
      pm = p.pmin + (p.pmax - p.pmin) * k / (npnt - 1);
      beta = pm / Math.sqrt(pm * pm + p.mass * p.mass);
      mu = K * (1.0 - 1.0 / (beta * beta * p.nidx * p.nidx));
      if (mu < 0.0) mu = 0.0;
      s = 0.0;
      for (j = 0; j < n; j++) { v = mu + Math.sqrt(mu) * g(st); s += v > 0.0 ? v : 0.0; }
      xs.push(1.0 / (beta * beta)); ys.push(s / n);
    }
    var ab = line(xs, ys), a = ab[0], b = ab[1], bth = (a > 0 && b < 0) ? Math.sqrt(-b / a) : 0.0, yl = (a + b) / p.L;
    var val = I(p.what) === 1 ? yl : bth, x0 = 1.0, x1 = xs[0];
    return base(val, cherExact(p), npnt * n, [x0, x1], [], [a + b * x0, a + b * x1], xs, ys, { bth: bth, yld: yl, nfit: bth > 0 ? 1.0 / bth : 0.0 });
  });

  // ====================================================================================== SiPM timing
  function sipmExact(p) {
    if (I(p.what) === 1) return p.mu;
    return FW * Math.sqrt(2.0) * p.sig * 1000.0;
  }
  var PaSipm = kernel({ sig: 0.09, tr: 1.2, Am: 100.0, thr: 0.1, mu: 1.5, gain: 1.0, enc: 0.08, n: 20000.0, what: 0.0, method: 0.0, seed: 113.0 }, function (p) {
    var n = Math.max(20, I(p.n)), st = lcg(p.seed), j, k, h;
    if (I(p.what) === 1) {
      var qs = [], n0 = 0, q, kk;
      for (j = 0; j < n; j++) {
        kk = poisson(st, p.mu); q = p.gain * kk + p.enc * g(st); qs.push(q);
        if (q < 0.5 * p.gain) n0 += 1;
      }
      var mu = n0 > 0 ? -Math.log(n0 / n) : 0.0, hi = p.mu + 4.0 * Math.sqrt(p.mu) + 1.5;
      h = hist(qs, -0.5, hi, 80);
      return base(mu, sipmExact(p), n, h[0], [], h[1], [], [], { n0: n0, mufit: mu });
    }
    var lev = p.thr * p.Am, le = I(p.method) === 1, ds = [], xs = [], a1, a2, t1, t2;
    for (j = 0; j < n; j++) {
      a1 = p.Am * (0.3 + 0.7 * u(st)); a2 = p.Am * (0.3 + 0.7 * u(st));
      t1 = p.sig * g(st); t2 = p.sig * g(st);
      if (le) { ds.push((t1 + p.tr * lev / a1) - (t2 + p.tr * lev / a2)); xs.push(1.0 / a1 - 1.0 / a2); }
      else { ds.push(t1 - t2); xs.push(0.0); }
    }
    var slope = 0.0, m = 0.0, v = 0.0, rs = [], r;
    if (le) slope = line(xs, ds)[1];
    for (k = 0; k < n; k++) m += ds[k] - slope * xs[k];
    m = m / n;
    for (k = 0; k < n; k++) { r = (ds[k] - slope * xs[k] - m) * 1000.0; rs.push(r); v += r * r; }
    var sd = Math.sqrt(v / (n - 1)), ctr = FW * sd;
    h = hist(rs, -4.0 * sd, 4.0 * sd, 41);
    return base(ctr, sipmExact(p), n, h[0], [], h[1], [], [], { walk: slope, sd: sd });
  });

  // ====================================================================================== radio telescope
  function radExact(p) {
    var w = I(p.what);
    if (w === 1) return p.Trx + p.Tcold;
    if (w === 2) return p.S;
    return p.fwhm;
  }
  var PaRadio = kernel({ fwhm: 6.0, dec: -10.0, ssun: 0.53, Tpk: 250.0, Tb: 120.0, sig: 3.0, Thot: 290.0, Tcold: 8.0, Trx: 95.0, bw: 1.0e6,
    S: 1500.0, D: 2.3, eta: 0.6, sdec: 58.8, sigf: 0.15, n: 16.0, what: 0.0, method: 0.0, seed: 127.0 }, function (p) {
    var n = Math.max(1.0, p.n), st = lcg(p.seed), w = I(p.what), k, t, m = 400, ts = [], ys = [], cy = [];
    if (w === 1) {
      var r = 1.0 / Math.sqrt(p.bw * n);
      var Ph = (p.Trx + p.Thot) * (1.0 + r * g(st)), Pc = (p.Trx + p.Tcold) * (1.0 + r * g(st));
      var Y = Ph / Pc, trx = (p.Thot - Y * p.Tcold) / (Y - 1.0), tsy = trx + p.Tcold, gg = (Ph - Pc) / (p.Thot - p.Tcold);
      var cx1 = [-trx * 1.2, p.Thot];
      return base(tsy, radExact(p), n, cx1, [], [Pc + gg * (cx1[0] - p.Tcold), Pc + gg * (cx1[1] - p.Tcold)], [p.Tcold, p.Thot], [Pc, Ph], { Y: Y, Trx: trx });
    }
    if (w === 2) {
      var wt2 = p.fwhm / (SIDEREAL * Math.cos(p.sdec * PI / 180.0)), Ae = p.eta * PI * p.D * p.D / 4.0;
      var Ta = p.S * 1.0e-26 * Ae / (2.0 * KB), sg2 = p.sigf / Math.sqrt(n), gs = [], gb;
      for (k = 0; k < m; k++) {
        t = -3.0 * wt2 + 6.0 * wt2 * k / (m - 1);
        gb = Math.exp(-4.0 * Math.log(2.0) * t * t / (wt2 * wt2));
        ts.push(t); gs.push(gb); ys.push(p.Tb + Ta * gb + sg2 * g(st));
      }
      var s1 = m, sg1 = 0.0, sgg = 0.0, sy = 0.0, sgy = 0.0;
      for (k = 0; k < m; k++) { sg1 += gs[k]; sgg += gs[k] * gs[k]; sy += ys[k]; sgy += gs[k] * ys[k]; }
      var den = s1 * sgg - sg1 * sg1, a = (s1 * sgy - sg1 * sy) / den, c = (sy - a * sg1) / s1, S = 2.0 * KB * a / Ae / 1.0e-26;
      for (k = 0; k < m; k++) cy.push(c + a * gs[k]);
      return base(S, radExact(p), m * n, thin(ts, 200), [], thin(cy, 200), thin(ts, 200), thin(ys, 200), { Ta: a, base: c, Ae: Ae });
    }
    var weff = Math.sqrt(p.fwhm * p.fwhm + p.ssun * p.ssun), cd = Math.cos(p.dec * PI / 180.0), wt = weff / (SIDEREAL * cd), sg = p.sig / Math.sqrt(n);
    for (k = 0; k < m; k++) {
      t = -3.0 * wt + 6.0 * wt * k / (m - 1);
      ts.push(t); ys.push(p.Tb + p.Tpk * Math.exp(-4.0 * Math.log(2.0) * t * t / (wt * wt)) + sg * g(st));
    }
    var e = Math.floor(m / 8), bl = 0.0, top = 0.0, A = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], bb = [0, 0, 0], used = 0, y, row, ly, i2, j2;
    for (k = 0; k < e; k++) bl += ys[k] + ys[m - 1 - k];
    bl = bl / (2 * e);
    for (k = 0; k < m; k++) if (ys[k] - bl > top) top = ys[k] - bl;
    for (k = 0; k < m; k++) {
      y = ys[k] - bl;
      if (y > 0.5 * top) {
        t = ts[k]; row = [1.0, t, t * t]; ly = Math.log(y);
        for (i2 = 0; i2 < 3; i2++) { for (j2 = 0; j2 < 3; j2++) A[i2][j2] += row[i2] * row[j2]; bb[i2] += row[i2] * ly; }
        used += 1;
      }
    }
    var c3 = solve(A, bb), ww = c3[2] < 0 ? FW * Math.sqrt(-1.0 / (2.0 * c3[2])) : 0.0, sky = ww * SIDEREAL * cd;
    var beam = sky > p.ssun ? Math.sqrt(sky * sky - p.ssun * p.ssun) : 0.0;
    for (k = 0; k < m; k++) { t = ts[k]; cy.push(bl + Math.exp(c3[0] + c3[1] * t + c3[2] * t * t)); }
    return base(beam, radExact(p), used, thin(ts, 200), [], thin(cy, 200), thin(ts, 200), thin(ys, 200), { wtime: ww, sky: sky, base: bl });
  });

  // ====================================================================================== Hubble's law
  var H_LINES = [6562.80, 4861.33, 5006.84];
  function hubExact(p) { return p.H0; }
  var PaHubble = kernel({ H0: 70.0, dmin: 20.0, dmax: 400.0, sv: 300.0, sl: 1.0, n: 200.0, what: 0.0, method: 0.0, seed: 131.0 }, function (p) {
    var n = Math.max(3, I(p.n)), st = lcg(p.seed), ds = [], vs = [], zfar = 0.0, dfar = 0.0, j, k, d, vt, z, zs, zm;
    for (j = 0; j < n; j++) {
      d = p.dmin + (p.dmax - p.dmin) * u(st);
      vt = p.H0 * d + p.sv * g(st); z = vt / C_KMS; zs = 0.0;
      for (k = 0; k < H_LINES.length; k++) zs += (H_LINES[k] * (1.0 + z) + p.sl * g(st)) / H_LINES[k] - 1.0;
      zm = zs / H_LINES.length;
      ds.push(d); vs.push(C_KMS * zm);
      if (d > dfar) { dfar = d; zfar = zm; }
    }
    var sdv = 0.0, sdd = 0.0;
    for (k = 0; k < n; k++) { sdv += ds[k] * vs[k]; sdd += ds[k] * ds[k]; }
    var H = sdv / sdd;
    return base(H, hubExact(p), n, [0.0, p.dmax], [], [0.0, H * p.dmax], thin(ds, 300), thin(vs, 300), { zfar: zfar, dfar: dfar });
  });

  // ====================================================================================== cluster colour-magnitude
  function cmdExact(p) { return I(p.what) === 1 ? p.age : p.dist; }
  var PaCmd = kernel({ dist: 400.0, age: 0.8, Mlo: 0.6, Mhi: 6.0, alpha: 2.35, sp: 0.04, sg: 0.003, MGsun: 4.67, n: 4000.0, what: 0.0, method: 0.0, seed: 137.0 }, function (p) {
    var n = Math.max(10, I(p.n)), st = lcg(p.seed), e = 1.0 - p.alpha, lo = Math.pow(p.Mlo, e), hi = Math.pow(p.Mhi, e);
    var dm = 5.0 * Math.log10(p.dist) - 5.0, pis = [], cs = [], gs = [], gmin = 99.0, j, M, life, pp, gg;
    for (j = 0; j < n; j++) {
      M = Math.pow(lo + u(st) * (hi - lo), 1.0 / e);
      life = 10.0 * Math.pow(M, -2.5);
      pp = 1000.0 / p.dist + p.sp * g(st);
      gg = p.MGsun - 2.5 * 3.5 * Math.log10(M) + dm + p.sg * g(st);
      if (life < p.age) continue;
      pis.push(pp); cs.push(0.82 - 0.95 * Math.log10(M)); gs.push(gg);
      if (gg < gmin) gmin = gg;
    }
    var s = 0.0, k;
    for (k = 0; k < pis.length; k++) s += pis[k];
    var dist = pis.length ? 1000.0 / (s / pis.length) : 0.0;
    var MG = dist > 0 ? gmin - 5.0 * Math.log10(dist) + 5.0 : 0.0, L = Math.pow(10.0, -0.4 * (MG - p.MGsun));
    var Mt = Math.pow(L, 1.0 / 3.5), age = 10.0 * Math.pow(Mt, -2.5), val = I(p.what) === 1 ? age : dist;
    var py = [], c0 = 1e30, c1 = -1e30;
    for (k = 0; k < gs.length; k++) py.push(-gs[k]);
    for (k = 0; k < cs.length; k++) { if (cs[k] < c0) c0 = cs[k]; if (cs[k] > c1) c1 = cs[k]; }
    if (!cs.length) { c0 = 0.0; c1 = 1.0; }
    return base(val, cmdExact(p), pis.length, [c0, c1], [], [-gmin, -gmin], thin(cs, 600), thin(py, 600), { dfit: dist, agefit: age, Mto: Mt, nmem: pis.length });
  });

  // ====================================================================================== variable-star period
  function lspShape(kind, ph) {
    var a = 2.0 * PI * ph, d1, d2;
    if (kind === 1) return -(Math.sin(a) + 0.5 * Math.sin(2 * a) + 0.3 * Math.sin(3 * a) + 0.15 * Math.sin(4 * a));
    if (kind === 2) {
      d1 = ph - Math.floor(ph + 0.5); d2 = ph - 0.5 - Math.floor(ph);
      return Math.exp(-d1 * d1 / 0.0018) + 0.4 * Math.exp(-d2 * d2 / 0.0018);
    }
    return -(Math.sin(a) + 0.35 * Math.sin(2 * a) + 0.12 * Math.sin(3 * a));
  }
  function lspNorm(kind) {
    var lo = 1e30, hi = -1e30, k, s;
    for (k = 0; k < 2000; k++) { s = lspShape(kind, k / 2000.0); lo = Math.min(lo, s); hi = Math.max(hi, s); }
    return [lo, hi - lo];
  }
  function lspAbsmag(p, P) { return p.plA * (Math.log10(P) - 1.0) + p.plB; }
  function lspM0(p) {
    if (I(p.kind) === 0) return lspAbsmag(p, p.P) + 5.0 * Math.log10(p.dist) - 5.0;
    return p.mag;
  }
  function lspExact(p) {
    var w = I(p.what);
    if (w === 1) return p.A;
    if (w === 2) return p.dist;
    return p.P;
  }
  function lsPower(ts, ys, f) {
    var w = 2.0 * PI * f, s2 = 0.0, c2 = 0.0, k, tau, yc = 0.0, ys2 = 0.0, cc = 0.0, ss = 0.0, c, s;
    for (k = 0; k < ts.length; k++) { s2 += Math.sin(2.0 * w * ts[k]); c2 += Math.cos(2.0 * w * ts[k]); }
    tau = Math.atan2(s2, c2) / (2.0 * w);
    for (k = 0; k < ts.length; k++) {
      c = Math.cos(w * (ts[k] - tau)); s = Math.sin(w * (ts[k] - tau));
      yc += ys[k] * c; ys2 += ys[k] * s; cc += c * c; ss += s * s;
    }
    return 0.5 * (yc * yc / cc + ys2 * ys2 / ss);
  }
  function pdmTheta(ts, ys, f, v, nb) {
    var sm = [], sq = [], nn = [], k, ph, b, num = 0.0, dof = 0;
    for (k = 0; k < nb; k++) { sm.push(0.0); sq.push(0.0); nn.push(0); }
    for (k = 0; k < ts.length; k++) {
      ph = ts[k] * f; ph = ph - Math.floor(ph); b = Math.floor(ph * nb);
      if (b >= nb) b = nb - 1;
      sm[b] += ys[k]; sq[b] += ys[k] * ys[k]; nn[b] += 1;
    }
    for (b = 0; b < nb; b++) if (nn[b] > 1) { num += sq[b] - sm[b] * sm[b] / nn[b]; dof += nn[b] - 1; }
    if (dof <= 0 || v <= 0) return 1.0;
    return (num / dof) / v;
  }
  function lspFit(ts, ys, f) {
    var H = 4, nc = 2 * H + 1, A = [], bv = [], rows = [], i2, j2, k, h, ph, row, co, r2 = 0.0, v;
    for (i2 = 0; i2 < nc; i2++) { row = []; for (j2 = 0; j2 < nc; j2++) row.push(0.0); A.push(row); bv.push(0.0); }
    for (k = 0; k < ts.length; k++) {
      ph = 2.0 * PI * ts[k] * f; row = [1.0];
      for (h = 1; h <= H; h++) { row.push(Math.cos(h * ph)); row.push(Math.sin(h * ph)); }
      rows.push(row);
      for (i2 = 0; i2 < nc; i2++) { for (j2 = 0; j2 < nc; j2++) A[i2][j2] += row[i2] * row[j2]; bv[i2] += row[i2] * ys[k]; }
    }
    co = solve(A, bv);
    for (k = 0; k < ts.length; k++) { v = 0.0; for (i2 = 0; i2 < nc; i2++) v += co[i2] * rows[k][i2]; r2 += (ys[k] - v) * (ys[k] - v); }
    return [co, r2];
  }
  var PaLsp = kernel({ P: 5.37, A: 0.8, kind: 0.0, dist: 1500.0, mag: 12.0, plA: -2.43, plB: -4.05, span: 120.0, sig: 0.02,
    fmin: 0.05, fmax: 2.5, nbin: 10.0, n: 200.0, what: 0.0, method: 0.0, seed: 139.0 }, function (p) {
    var n = Math.max(20, I(p.n)), st = lcg(p.seed), kind = I(p.kind), nrm = lspNorm(kind), m0 = lspM0(p), ts = [], ys = [], j, k, t, s;
    for (j = 0; j < n; j++) {
      t = p.span * u(st);
      s = (lspShape(kind, t / p.P) - (kind === 2 ? nrm[0] : 0.0)) / nrm[1];
      ts.push(t); ys.push(m0 + p.A * s + p.sig * g(st));
    }
    var mean = 0.0, yc = [], v = 0.0;
    for (k = 0; k < n; k++) mean += ys[k];
    mean = mean / n;
    for (k = 0; k < n; k++) yc.push(ys[k] - mean);
    for (k = 0; k < n; k++) v += yc[k] * yc[k];
    v = v / (n - 1);
    var pdm = I(p.method) === 1, nbin = Math.max(5, I(p.nbin));
    function score(f) { return pdm ? -pdmTheta(ts, yc, f, v, nbin) : lsPower(ts, yc, f); }
    var df = 1.0 / (5.0 * p.span), nf = Math.floor((p.fmax - p.fmin) / df) + 1, fs = [], sc = [], bi = 0, f, val;
    for (k = 0; k < nf; k++) { f = p.fmin + df * k; val = score(f); fs.push(f); sc.push(val); if (val > sc[bi]) bi = k; }
    var f0 = fs[bi], d2 = df / 20.0, best = sc[bi], fb = f0, vals = [];
    for (k = -20; k <= 20; k++) { f = f0 + d2 * k; val = score(f); vals.push(val); if (val > best) { best = val; fb = f; } }
    var kb = I((fb - f0) / d2) + 20;
    if (kb > 0 && kb < 40) {
      var a = vals[kb - 1], b = vals[kb], c = vals[kb + 1], den = a - 2.0 * b + c;
      if (den < 0) fb = fb + 0.5 * d2 * (a - c) / den;
    }
    var bq = 1e300, kq = 0, chis = [], c2, fq;
    for (k = 0; k < 13; k++) { f = fb + 0.5 * d2 * (k - 6); c2 = lspFit(ts, ys, f)[1]; chis.push(c2); if (c2 < bq) { bq = c2; kq = k; } }
    fq = fb + 0.5 * d2 * (kq - 6);
    if (kq > 0 && kq < 12) {
      var qa = chis[kq - 1], qb = chis[kq], qc = chis[kq + 1], qd = qa - 2.0 * qb + qc;
      if (qd > 0) fq = fq + 0.25 * d2 * (qa - qc) / qd;
    }
    fb = fq;
    var P = 1.0 / fb, H = 4, ph, h;
    var co = lspFit(ts, ys, fb)[0], lo = 1e30, hi = -1e30, mx = [], my = [], vv;
    for (k = 0; k < 400; k++) {
      ph = k / 400.0; vv = co[0];
      for (h = 1; h <= H; h++) vv += co[2 * h - 1] * Math.cos(2.0 * PI * h * ph) + co[2 * h] * Math.sin(2.0 * PI * h * ph);
      lo = Math.min(lo, vv); hi = Math.max(hi, vv);
      if (k % 4 === 0) { mx.push(ph); my.push(vv); }
    }
    var amp = hi - lo, Mv = lspAbsmag(p, P), dist = Math.pow(10.0, (co[0] - Mv + 5.0) / 5.0), w = I(p.what);
    var out = w === 1 ? amp : w === 2 ? dist : P;
    if (w === 0) return base(out, lspExact(p), n, thin(fs, 400), [], thin(sc, 400), [], [], { Pfit: P, amp: amp, dfit: dist, fbest: fb });
    var px = [], q;
    for (k = 0; k < ts.length; k++) { q = ts[k] / P; px.push(q - Math.floor(q)); }
    return base(out, lspExact(p), n, mx, [], my, thin(px, 300), thin(ys, 300), { Pfit: P, amp: amp, dfit: dist, fbest: fb });
  });

  // ====================================================================================== Schrodinger equation
  function schPot(p, x) {
    if (I(p.pot) === 1) { var q = x / p.a; return p.V0 * (q * q - 1.0) * (q * q - 1.0); }
    return 0.5 * x * x;
  }
  function schNodes(p, E, n) {
    var hyd = I(p.pot) === 2, h, l, x0;
    if (hyd) { h = p.rmax / n; l = I(p.l); x0 = 0.0; } else { h = 2.0 * p.L / n; x0 = -p.L; l = 0; }
    var h12 = h * h / 12.0;
    function f(x) { return hyd ? l * (l + 1) / (x * x) - 2.0 / x - 2.0 * E : 2.0 * (schPot(p, x) - E); }
    var y0 = 0.0, y1 = hyd ? Math.pow(h, l + 1) : 1e-6, f1 = f(x0 + h), nodes = 0, fprev = 0.0, i, x2, f2, term0, y2;
    for (i = 1; i < n; i++) {
      x2 = x0 + (i + 1) * h; f2 = f(x2);
      term0 = (hyd && i === 1) ? 0.0 : (1.0 - h12 * fprev) * y0;
      y2 = (2.0 * (1.0 + 5.0 * h12 * f1) * y1 - term0) / (1.0 - h12 * f2);
      if (((y2 < 0) !== (y1 < 0)) && y2 !== 0.0) nodes += 1;
      y0 = y1; y1 = y2; fprev = f1; f1 = f2;
      if (Math.abs(y1) > 1e200) { y0 *= 1e-200; y1 *= 1e-200; }
    }
    return nodes;
  }
  function schShoot(p, n, k) {
    var lo, hi, it, mid;
    if (I(p.pot) === 2) { lo = -0.6; hi = -1e-6; } else { lo = 0.0; hi = 40.0; }
    for (it = 0; it < 64; it++) { mid = 0.5 * (lo + hi); if (schNodes(p, mid, n) <= k) lo = mid; else hi = mid; }
    return 0.5 * (lo + hi);
  }
  function fdCount(p, N, E) {
    var h = 2.0 * p.L / (N + 1), off = -0.5 / (h * h), cnt = 0, q = 1.0, i, x, d;
    for (i = 0; i < N; i++) {
      x = -p.L + (i + 1) * h; d = 1.0 / (h * h) + schPot(p, x) - E;
      q = d - (i > 0 ? off * off / q : 0.0);
      if (q === 0.0) q = 1e-300;
      if (q < 0) cnt += 1;
    }
    return cnt;
  }
  function fdEig(p, N, k) {
    var lo = 0.0, hi = 40.0, it, mid;
    for (it = 0; it < 64; it++) { mid = 0.5 * (lo + hi); if (fdCount(p, N, mid) <= k) lo = mid; else hi = mid; }
    return 0.5 * (lo + hi);
  }
  function dwRef(p, k) {
    var e1 = fdEig(p, 1500, k), e2 = fdEig(p, 3000, k), h1 = 2.0 * p.L / 1501.0, h2 = 2.0 * p.L / 3001.0;
    return (e2 * h1 * h1 - e1 * h2 * h2) / (h1 * h1 - h2 * h2);
  }
  function schExact(p) {
    var pot = I(p.pot), k = I(p.k), nq;
    if (I(p.method) === 1) return PI / (dwRef(p, 1) - dwRef(p, 0));
    if (pot === 0) return k + 0.5;
    if (pot === 2) { nq = k + I(p.l) + 1; return -0.5 / (nq * nq) * HARTREE_EV; }
    return dwRef(p, k);
  }
  function fft(re, im, inv) {
    var n = re.length, j = 0, i, bit, t, ln, ang, wr, wi, cr, ci, k, a, b, tr, ti;
    for (i = 1; i < n; i++) {
      bit = n >> 1;
      while (j & bit) { j ^= bit; bit >>= 1; }
      j ^= bit;
      if (i < j) { t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
    }
    for (ln = 2; ln <= n; ln <<= 1) {
      ang = (inv ? 2.0 : -2.0) * PI / ln; wr = Math.cos(ang); wi = Math.sin(ang);
      for (i = 0; i < n; i += ln) {
        cr = 1.0; ci = 0.0;
        for (k = 0; k < ln / 2; k++) {
          a = i + k; b = a + ln / 2;
          tr = re[b] * cr - im[b] * ci; ti = re[b] * ci + im[b] * cr;
          re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
          t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
        }
      }
    }
    if (inv) for (i = 0; i < n; i++) { re[i] /= n; im[i] /= n; }
  }
  function fdVec(p, N, E) {
    var h = 2.0 * p.L / (N + 1), off = -0.5 / (h * h), sh = E - 1e-7 * (1.0 + Math.abs(E)), dg = [], v = [], i, x, it, cp, dp, m, y, s;
    for (i = 0; i < N; i++) { x = -p.L + (i + 1) * h; dg.push(1.0 / (h * h) + schPot(p, x) - sh); v.push(1.0 + x); }
    for (it = 0; it < 3; it++) {
      cp = []; dp = []; for (i = 0; i < N; i++) { cp.push(0.0); dp.push(0.0); }
      cp[0] = off / dg[0]; dp[0] = v[0] / dg[0];
      for (i = 1; i < N; i++) { m = dg[i] - off * cp[i - 1]; cp[i] = off / m; dp[i] = (v[i] - off * dp[i - 1]) / m; }
      y = []; for (i = 0; i < N; i++) y.push(0.0);
      y[N - 1] = dp[N - 1];
      for (i = N - 2; i >= 0; i--) y[i] = dp[i] - cp[i] * y[i + 1];
      s = 0.0; for (i = 0; i < N; i++) s += y[i] * y[i];
      s = Math.sqrt(s);
      v = []; for (i = 0; i < N; i++) v.push(y[i] / s);
    }
    return v;
  }
  function schSplit(p) {
    var n = Math.max(1, I(p.n)), N = 128, L = p.L, dx = 2.0 * L / N, Nf = 3000;
    var e0 = fdEig(p, Nf, 0), e1 = fdEig(p, Nf, 1), v0 = fdVec(p, Nf, e0), v1 = fdVec(p, Nf, e1), hf = 2.0 * L / (Nf + 1);
    var n0 = 0.0, n1 = 0.0, i, j, x, q, i0, fr, a;
    for (i = 0; i < Nf; i++) { n0 += v0[i] * v0[i]; n1 += v1[i] * v1[i]; }
    var s0 = 1.0 / Math.sqrt(n0), s1 = 1.0 / Math.sqrt(n1), sgn = v1[Math.floor(Nf / 4)] * v0[Math.floor(Nf / 4)] > 0 ? 1.0 : -1.0;
    var re = [], im = [], xs = [];
    for (j = 0; j < N; j++) {
      x = -L + j * dx; xs.push(x);
      q = (x + L) / hf - 1.0; i0 = Math.floor(q); fr = q - i0; a = 0.0;
      if (i0 >= 0 && i0 < Nf - 1) a = (v0[i0] * s0 + sgn * v1[i0] * s1) * (1.0 - fr) + (v0[i0 + 1] * s0 + sgn * v1[i0 + 1] * s1) * fr;
      re.push(a); im.push(0.0);
    }
    var nn = 0.0;
    for (j = 0; j < N; j++) nn += re[j] * re[j];
    nn = Math.sqrt(nn);
    for (j = 0; j < N; j++) re[j] /= nn;
    var dt = 1.0 / n, tmax = 1.4 * PI / (e1 - e0), steps = Math.floor(tmax / dt) + 1, vhc = [], vhs = [], kc = [], ks = [], kk, b2;
    for (j = 0; j < N; j++) {
      a = -schPot(p, xs[j]) * dt / 2.0; vhc.push(Math.cos(a)); vhs.push(Math.sin(a));
      kk = 2.0 * PI * (j < N / 2 ? j : j - N) / (2.0 * L); b2 = -0.5 * kk * kk * dt;
      kc.push(Math.cos(b2)); ks.push(Math.sin(b2));
    }
    function right() { var s = 0.0, jj; for (jj = N / 2; jj < N; jj++) s += re[jj] * re[jj] + im[jj] * im[jj]; return s; }
    var tsr = [0.0], prs = [right()], stp, r, qq;
    for (stp = 1; stp <= steps; stp++) {
      for (j = 0; j < N; j++) { r = re[j]; qq = im[j]; re[j] = r * vhc[j] - qq * vhs[j]; im[j] = r * vhs[j] + qq * vhc[j]; }
      fft(re, im, false);
      for (j = 0; j < N; j++) { r = re[j]; qq = im[j]; re[j] = r * kc[j] - qq * ks[j]; im[j] = r * ks[j] + qq * kc[j]; }
      fft(re, im, true);
      for (j = 0; j < N; j++) { r = re[j]; qq = im[j]; re[j] = r * vhc[j] - qq * vhs[j]; im[j] = r * vhs[j] + qq * vhc[j]; }
      tsr.push(stp * dt); prs.push(right());
    }
    var kb = 0;
    for (i = 0; i < prs.length; i++) if (prs[i] > prs[kb]) kb = i;
    var T = tsr[kb];
    if (kb > 0 && kb < prs.length - 1) {
      var aa = prs[kb - 1], bb = prs[kb], cc = prs[kb + 1], den = aa - 2.0 * bb + cc;
      if (den < 0) T = T + 0.5 * dt * (aa - cc) / den;
    }
    var dE = e1 - e0, tt = thin(tsr, 300), ce = [];
    for (i = 0; i < tt.length; i++) ce.push(0.5 * (1.0 - Math.cos(dE * tt[i])));
    return base(T, schExact(p), steps, tt, ce, thin(prs, 300), [], [], { E: dE, steps: steps });
  }
  var PaSchro = kernel({ pot: 0.0, k: 0.0, L: 8.0, V0: 4.0, a: 1.5, l: 0.0, rmax: 60.0, n: 400.0, what: 0.0, method: 0.0, seed: 0.0 }, function (p) {
    if (I(p.method) === 1) return schSplit(p);
    var n = Math.max(20, I(p.n)), k = I(p.k), E = schShoot(p, n, k), hyd = I(p.pot) === 2;
    var val = hyd ? E * HARTREE_EV : E, ex = schExact(p), cx = [], ce = [], cy = [], m = 200;
    var h = (hyd ? p.rmax : 2.0 * p.L) / m, x0 = hyd ? 0.0 : -p.L, l = I(p.l), h12 = h * h / 12.0;
    var ys = [0.0, hyd ? Math.pow(h, l + 1) : 1e-6], i, x1, x2, fp, t0, x, yv;
    function f(xx) { return hyd ? l * (l + 1) / (xx * xx) - 2.0 / xx - 2.0 * E : 2.0 * (schPot(p, xx) - E); }
    for (i = 1; i < m; i++) {
      x1 = x0 + i * h; x2 = x0 + (i + 1) * h;
      fp = !(hyd && i === 1) ? f(x0 + (i - 1) * h) : 0.0;
      t0 = (hyd && i === 1) ? 0.0 : (1.0 - h12 * fp) * ys[i - 1];
      ys.push((2.0 * (1.0 + 5.0 * h12 * f(x1)) * ys[i] - t0) / (1.0 - h12 * f(x2)));
    }
    var best = 0.0;
    for (i = 0; i <= m; i++) if (Math.abs(ys[i]) > best && i < m * 0.85) best = Math.abs(ys[i]);
    for (i = 0; i <= m; i++) {
      x = x0 + i * h; cx.push(x);
      yv = best > 0 ? ys[i] / best : 0.0;
      cy.push(Math.max(-1.5, Math.min(1.5, yv)));
      if (hyd) ce.push(Math.max(-1.5, x > 0 ? (l * (l + 1) / (x * x) - 2.0 / x) * 0.5 : -1.5));
      else ce.push(Math.min(1.5, schPot(p, x) / Math.max(Math.abs(E), 1e-9) * 0.5));
    }
    return base(val, ex, n, cx, ce, cy, [], [], { E: E });
  });

  // ====================================================================================== calcs
  function rowsOf(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) {
        v = Number(rs[i][keys[j]]);
        if (rs[i][keys[j]] === '' || rs[i][keys[j]] === null || rs[i][keys[j]] === undefined || !isFinite(v)) { ok = false; break; }
        vals.push(v);
      }
      if (ok) out.push(vals);
    }
    return out;
  }
  function finest(r) {
    var rs = rowsOf(r, ['n', 'val']), i, b;
    if (!rs.length) return 0;
    b = rs[0];
    for (i = 0; i < rs.length; i++) if (rs[i][0] >= b[0]) b = rs[i];
    return b[1];
  }
  function best(r) {
    var rs = rowsOf(r, ['n', 'val', 'err']), i, b;
    if (!rs.length) return 0;
    b = rs[0];
    for (i = 0; i < rs.length; i++) if (rs[i][2] < b[2] || (rs[i][2] === b[2] && rs[i][0] > b[0])) b = rs[i];
    return b[1];
  }

  root.HoolaKernels.register({
    K: { pa10_tof: PaTof, pa10_zenith: PaZenith, pa10_reldyn: PaReldyn, pa10_cher: PaCher, pa10_sipm: PaSipm, pa10_radio: PaRadio,
      pa10_hubble: PaHubble, pa10_cmd: PaCmd, pa10_lsp: PaLsp, pa10_schro: PaSchro },
    TEXTBOOK: { pa10_tof_v: tofExact, pa10_zenith_v: zenExact, pa10_reldyn_v: relExact, pa10_cher_v: cherExact, pa10_sipm_v: sipmExact,
      pa10_radio_v: radExact, pa10_hubble_v: hubExact, pa10_cmd_v: cmdExact, pa10_lsp_v: lspExact, pa10_schro_v: schExact },
    CALCS: {
      pa10_finest: { label: 'answer on the most data', unit: '', needs: ['n', 'val'], fn: finest },
      pa10_best: { label: 'best value', unit: '', needs: ['n', 'val', 'err'], fn: best }
    }
  });
})(typeof window !== 'undefined' ? window : this);
