/* Kernel pack (browser twin of app/prayog/packs/phd_xfilm_w10.py): Ph.D. research techniques - X-ray and electron
   methods, thin films and vacuum, plasma diagnostics (wave 10). Same formulas, same order of operations, so both sides
   give the same numbers. Deterministic: anything random is the seeded Lehmer generator (16807, mod 2^31 - 1).
     px10_moseley (Moseley fit)   px10_ruth (Rutherford law)   px10_mwi (microwave interferometer)
     px10_profilo (step height, Rq)   px10_stoney (film stress)   px10_spin (Meyerhofer, Emslie-Bonner-Peck)
     px10_imp (impedance arcs, Arrhenius)   px10_rock (rocking curve)   px10_qcm (e-beam + Sauerbrey)
     px10_afm (thermal k, adhesion, Rq, step)   px10_saed (camera constant, d-spacings, size)   px10_stm (a, phi, onset)
   Every kernel analyses SIMULATED DATA: the hidden sample value is what the student measures. */
(function (root) {
  'use strict';
  var PI = Math.PI, M31 = 2147483647;
  var QE = 1.602176634e-19, H = 6.62607015e-34, HBAR = H / (2.0 * PI), KB = 1.380649e-23, ME = 9.1093837015e-31;
  var EPS0 = 8.8541878128e-12, C_LIGHT = 299792458.0, RE = 2.8179403262e-15;

  function I(v) { return Math.floor(v + 0.5); }
  function errOf(val, exact) { return Math.abs(val - exact) / Math.max(Math.abs(exact), 1e-30); }
  function mod(a, b) { var r = a % b; return r < 0 ? r + b : r; }
  function lcg(seed) { var s = mod(I(seed), M31); return [s > 0 ? s : 1]; }
  function u(st) { st[0] = (st[0] * 16807) % M31; return st[0] / M31; }
  function gauss(st) { var u1 = u(st), u2 = u(st); return Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * PI * u2); }
  function thin(xs, m) {
    var n = xs.length, out = [], i;
    if (n <= m + 1) return xs.slice();
    for (i = 0; i <= m; i++) out.push(xs[I(i * (n - 1) / m)]);
    return out;
  }
  function line(xs, ys) {
    var n = xs.length, sx = 0, sy = 0, sxx = 0, sxy = 0, k, den, b;
    if (n < 2) return [0, 0];
    for (k = 0; k < n; k++) { sx += xs[k]; sy += ys[k]; sxx += xs[k] * xs[k]; sxy += xs[k] * ys[k]; }
    den = n * sxx - sx * sx;
    if (Math.abs(den) < 1e-300) return [0, 0];
    b = (n * sxy - sx * sy) / den;
    return [(sy - b * sx) / n, b];
  }
  function solve3(A, b) {
    var m = [], r, c, k, piv, f, t, x = [0, 0, 0], s;
    for (r = 0; r < 3; r++) m.push([A[r][0], A[r][1], A[r][2], b[r]]);
    for (c = 0; c < 3; c++) {
      piv = c;
      for (r = c + 1; r < 3; r++) if (Math.abs(m[r][c]) > Math.abs(m[piv][c])) piv = r;
      if (piv !== c) { t = m[c]; m[c] = m[piv]; m[piv] = t; }
      if (Math.abs(m[c][c]) < 1e-300) return [0, 0, 0];
      for (r = c + 1; r < 3; r++) {
        f = m[r][c] / m[c][c];
        for (k = c; k < 4; k++) m[r][k] -= f * m[c][k];
      }
    }
    for (r = 2; r >= 0; r--) {
      s = m[r][3];
      for (k = r + 1; k < 3; k++) s -= m[r][k] * x[k];
      x[r] = s / m[r][r];
    }
    return x;
  }
  function quad(xs, ys) {
    var s0 = 0, s1 = 0, s2 = 0, s3 = 0, s4 = 0, t0 = 0, t1 = 0, t2 = 0, k, x, y, x2;
    for (k = 0; k < xs.length; k++) {
      x = xs[k]; y = ys[k]; x2 = x * x;
      s0 += 1.0; s1 += x; s2 += x2; s3 += x2 * x; s4 += x2 * x2; t0 += y; t1 += x * y; t2 += x2 * y;
    }
    return solve3([[s0, s1, s2], [s1, s2, s3], [s2, s3, s4]], [t0, t1, t2]);
  }
  function peak(xs, ys, k, m, logp) {
    var n = ys.length, a, b, c, den, dx, top;
    if (k - m < 0 || k + m > n - 1) return [xs[k], ys[k]];
    a = ys[k - m]; b = ys[k]; c = ys[k + m];
    if (logp) {
      if (a <= 0 || b <= 0 || c <= 0) return [xs[k], ys[k]];
      a = Math.log(a); b = Math.log(b); c = Math.log(c);
    }
    den = a - 2.0 * b + c;
    dx = den !== 0 ? 0.5 * (a - c) / den : 0.0;
    if (dx > 1.0) dx = 1.0;
    if (dx < -1.0) dx = -1.0;
    top = b - 0.25 * (a - c) * dx;
    if (logp) top = Math.exp(top);
    return [xs[k] + dx * (xs[k + m] - xs[k]), top];
  }
  function argmax(ys, lo, hi) { var b = lo, k; for (k = lo; k <= hi; k++) if (ys[k] > ys[b]) b = k; return b; }
  function gfit(xs, ys, k, bg) {
    var n = ys.length, half = bg + 0.5 * (ys[k] - bg), lo = k, hi = k, X = [], Y = [], j, c, x0, top;
    while (lo > 0 && ys[lo - 1] > half) lo -= 1;
    while (hi < n - 1 && ys[hi + 1] > half) hi += 1;
    if (hi - lo < 2) { lo = Math.max(0, k - 1); hi = Math.min(n - 1, k + 1); }
    for (j = lo; j <= hi; j++) if (ys[j] - bg > 0) { X.push(xs[j] - xs[k]); Y.push(Math.log(ys[j] - bg)); }
    c = quad(X, Y);
    if (c[2] >= 0) return [xs[k], 0.0, ys[k]];
    x0 = -c[1] / (2.0 * c[2]);
    top = Math.exp(c[0] - c[1] * c[1] / (4.0 * c[2])) + bg;
    return [xs[k] + x0, Math.sqrt(-4.0 * Math.log(2.0) / c[2]), top];
  }
  function base(val, exact, nused, cx, cy, px, py, extra) {
    var s = { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: nused, cx: cx, ce: [], cy: cy, px: px, py: py }, k;
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
  function clampi(v, lo, hi) { return Math.max(lo, Math.min(hi, I(v))); }

  // ====================================================================================== Moseley
  var MOS_Z = [29.0, 30.0, 40.0, 42.0, 47.0];
  var MOS_KA = [8.04778, 8.63886, 15.77508, 17.47934, 22.16292];
  var MOS_KE = [8.97890, 9.65860, 17.99760, 19.99950, 25.51400];
  function mosFit(Es, edge) {
    var xs = MOS_Z.slice(), ys = Es.map(function (e) { return Math.sqrt(e * 1000.0); }), ln = line(xs, ys), b = ln[1];
    var sig = b !== 0 ? -ln[0] / b : 0.0;
    return [sig, edge ? b * b : 4.0 * b * b / 3.0];
  }
  function mosExact(p) {
    var w = I(p.what), edge, f;
    if (w === 2) return MOS_KE[clampi(p.k, 0, 4)];
    edge = I(p.method) === 1;
    f = mosFit(edge ? MOS_KE : MOS_KA, edge);
    return w === 1 ? f[1] : f[0];
  }
  function mosSpec(p, j, edge, n, st) {
    var Em = p.Emax, xs = [], ys = [], c, E, Ek, mu, y;
    for (c = 0; c < n; c++) {
      E = Em * (c + 0.5) / n;
      if (edge) {
        Ek = MOS_KE[j];
        mu = p.mt * Math.pow(E / Ek, -2.7) * (1.0 + (p.rj - 1.0) * 0.5 * (1.0 + Math.tanh((E - Ek) / (p.fw / 3.0))));
        y = Math.exp(-mu);
      } else {
        y = 0.02 + Math.exp(-4.0 * Math.log(2.0) * Math.pow(E - MOS_KA[j], 2) / (p.fw * p.fw));
      }
      xs.push(E);
      ys.push(y * (1.0 + p.noise * (2.0 * u(st) - 1.0)));
    }
    return [xs, ys];
  }
  function mosFind(p, xs, ys, edge) {
    var n = xs.length, dE = xs[1] - xs[0], d, c, lo, k, m, z, i;
    if (edge) {
      d = [];
      for (c = 0; c < n; c++) d.push(0.0);
      for (c = 1; c < n - 1; c++) {
        if (ys[c - 1] > 1e-200 && ys[c + 1] > 1e-200) d[c] = (Math.log(ys[c - 1]) - Math.log(ys[c + 1])) / (2.0 * dE);
      }
      lo = Math.max(1, I(4.0 / dE));
      k = argmax(d, lo, n - 2);
      m = Math.max(1, I(0.25 * p.fw / dE));
      return peak(xs, d, k, m, false)[0];
    }
    lo = ys[0];
    for (i = 0; i < ys.length; i++) if (ys[i] < lo) lo = ys[i];
    z = ys.map(function (y) { return y - lo; });
    k = argmax(z, 0, n - 1);
    m = Math.max(1, I(0.4 * p.fw / dE));
    return peak(xs, z, k, m, true)[0];
  }
  var PxMoseley = kernel({ what: 0.0, k: 0.0, method: 0.0, n: 2048.0, Emax: 30.0, fw: 0.16, mt: 0.6, rj: 7.0, noise: 0.01, seed: 11.0 },
    function (p) {
      var n = Math.max(64, I(p.n)), w = I(p.what), edge = w === 2 || I(p.method) === 1, st = lcg(p.seed), Es = [], last = [[], []], j, sp, f, val, px, py, b, fx, fy;
      for (j = 0; j < 5; j++) {
        sp = mosSpec(p, j, edge, n, st);
        Es.push(mosFind(p, sp[0], sp[1], edge));
        if (w === 2 && j === clampi(p.k, 0, 4)) last = sp;
        else if (w !== 2 && j === 4) last = sp;
      }
      f = mosFit(Es, edge);
      val = w === 2 ? Es[clampi(p.k, 0, 4)] : w === 1 ? f[1] : f[0];
      px = MOS_Z.slice();
      py = Es.map(function (e) { return Math.sqrt(e * 1000.0); });
      b = Math.sqrt(edge ? f[1] : 0.75 * f[1]);
      fx = [MOS_Z[0] - 2.0, MOS_Z[4] + 2.0];
      fy = [b * (fx[0] - f[0]), b * (fx[1] - f[0])];
      return base(val, mosExact(p), n, thin(last[0], 400), thin(last[1], 400), px, py, { fit: [fx, fy], energies: Es, sigma: f[0], R: f[1] });
    });

  // ====================================================================================== Rutherford
  function ruthDs(Z, E, th) {
    var a = 2.0 * Z * QE * QE / (16.0 * PI * EPS0 * E * 1.0e6 * QE);
    return a * a / Math.pow(Math.sin(th / 2.0), 4);
  }
  var RUTH_TH = [20.0, 30.0, 45.0, 60.0, 75.0, 90.0, 120.0, 150.0];
  function ruthCounts(p, Z, nt, st) {
    var T = p.n * 3600.0, out = [], i, lam, c;
    for (i = 0; i < RUTH_TH.length; i++) {
      lam = p.N0 * nt * ruthDs(Z, p.E, RUTH_TH[i] * PI / 180.0) * p.dO * T;
      c = lam + Math.sqrt(lam) * gauss(st);
      out.push(c > 1.0 ? c : 1.0);
    }
    return out;
  }
  function ruthExact(p) { return I(p.what) === 1 ? p.Z : 4.0; }
  var PxRuth = kernel({ what: 0.0, Z: 79.0, nt: 1.181e23, ntr: 1.181e23, E: 5.486, N0: 1.0e7, dO: 0.01, n: 4.0, seed: 5.0 },
    function (p) {
      var st = lcg(p.seed), C = ruthCounts(p, p.Z, p.nt, st), xs, ys, ln, m, Zf = p.Z, Cr, s, k, val, cx, cy;
      xs = RUTH_TH.map(function (th) { return Math.log(Math.sin(th * PI / 360.0)); });
      ys = C.map(function (c) { return Math.log(c); });
      ln = line(xs, ys);
      m = -ln[1];
      if (I(p.what) === 1) {
        Cr = ruthCounts(p, 79.0, p.ntr, st);
        s = 0.0;
        for (k = 0; k < C.length; k++) s += (C[k] / p.nt) / (Cr[k] / p.ntr);
        Zf = 79.0 * Math.sqrt(s / C.length);
      }
      val = I(p.what) === 1 ? Zf : m;
      cx = [xs[0] - 0.1, xs[xs.length - 1] + 0.05];
      cy = [ln[0] + ln[1] * cx[0], ln[0] + ln[1] * cx[1]];
      return base(val, ruthExact(p), C.length, cx, cy, xs, ys, { counts: C, slope: ln[1], Zfit: Zf });
    });

  // ====================================================================================== microwave interferometer
  function mwiNc(f) { var w = 2.0 * PI * f; return EPS0 * ME * w * w / (QE * QE); }
  var PxMwi = kernel({ NL: 5.0e17, L: 0.10, f: 35.0e9, tau: 0.002, T: 0.2, t0: 0.02, phi0: 0.7, n: 2000.0, noise: 0.02, seed: 7.0 },
    function (p) {
      var n = Math.max(20, I(p.n)), st = lcg(p.seed), nc = mwiNc(p.f), lam = C_LIGHT / p.f, n0 = p.NL / p.L;
      var ts = [], ph = [], prev = 0.0, acc = 0.0, k, t, dens, phi, Iq, Qq, a, d, m0, m1, a0, a1, dphi, q, NL, approx;
      for (k = 0; k < n; k++) {
        t = p.T * k / (n - 1);
        dens = t > p.t0 ? n0 * (1.0 - Math.exp(-(t - p.t0) / p.tau)) : 0.0;
        phi = p.phi0 + 2.0 * PI / lam * p.L * (1.0 - Math.sqrt(1.0 - dens / nc));
        Iq = Math.cos(phi) + p.noise * gauss(st);
        Qq = Math.sin(phi) + p.noise * gauss(st);
        a = Math.atan2(Qq, Iq);
        if (k === 0) acc = a;
        else {
          d = a - prev;
          while (d > PI) d -= 2.0 * PI;
          while (d < -PI) d += 2.0 * PI;
          acc += d;
        }
        prev = a;
        ts.push(t); ph.push(acc);
      }
      m0 = Math.max(1, Math.floor(n / 20)); m1 = Math.max(1, Math.floor(n / 10));
      a0 = 0.0; for (k = 0; k < m0; k++) a0 += ph[k]; a0 /= m0;
      a1 = 0.0; for (k = n - m1; k < n; k++) a1 += ph[k]; a1 /= m1;
      dphi = a1 - a0;
      q = 1.0 - dphi * lam / (2.0 * PI * p.L);
      dens = q > 0 ? nc * (1.0 - q * q) : nc;
      NL = dens * p.L;
      approx = dphi / (RE * lam);
      return base(NL, p.NL, n, thin(ts, 400), thin(ph, 400), [], [], { dphi: dphi, approx: approx, nc: nc, fringes: dphi / (2.0 * PI) });
    });

  // ====================================================================================== stylus profilometry
  var PRO_W = [7.3, 11.9, 17.1, 23.7, 31.3], PRO_A = [1.0, 0.8, 0.6, 0.5, 0.4];
  function proSurface(p) {
    var st = lcg(p.seed), s2 = 0.0, i, sc, amp = [], ph = [];
    for (i = 0; i < PRO_A.length; i++) s2 += PRO_A[i] * PRO_A[i] / 2.0;
    sc = p.rq / Math.sqrt(s2);
    for (i = 0; i < PRO_A.length; i++) amp.push(PRO_A[i] * sc);
    for (i = 0; i < PRO_A.length; i++) ph.push(2.0 * PI * u(st));
    return [amp, ph];
  }
  function proZ(p, sf, x) {
    var z = p.tilt * x + (x > p.xs ? p.h : 0.0), j;
    for (j = 0; j < PRO_W.length; j++) z += sf[0][j] * Math.sin(2.0 * PI * x / PRO_W[j] + sf[1][j]);
    return z;
  }
  function proExact(p) { return I(p.what) === 1 ? p.rq : p.h; }
  function zeros3() { return [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]; }
  var PxProfilo = kernel({ what: 0.0, h: 100.0, rq: 1.2, tilt: 0.2, xs: 1000.0, Lscan: 2000.0, lc: 0.1, n: 4000.0, seed: 13.0 },
    function (p) {
      var n = Math.max(50, I(p.n)), sf = proSurface(p), L = p.Lscan, xs = [], zs = [], k, x, A = zeros3(), b = [0.0, 0.0, 0.0], used = [], s, v, r, c, q, rq, val, lev = [];
      for (k = 0; k < n; k++) { x = L * k / (n - 1); xs.push(x); zs.push(p.lc * I(proZ(p, sf, x) / p.lc)); }
      for (k = 0; k < n; k++) {
        x = xs[k];
        if ((0.05 * L <= x && x <= p.xs - 0.05 * L) || (p.xs + 0.05 * L <= x && x <= 0.95 * L)) {
          s = x > p.xs ? 1.0 : 0.0;
          v = [1.0, s, x];
          for (r = 0; r < 3; r++) { for (c = 0; c < 3; c++) A[r][c] += v[r] * v[c]; b[r] += v[r] * zs[k]; }
          used.push(k);
        }
      }
      c = solve3(A, b);
      q = 0.0;
      for (k = 0; k < used.length; k++) {
        s = xs[used[k]] > p.xs ? 1.0 : 0.0;
        r = zs[used[k]] - c[0] - c[1] * s - c[2] * xs[used[k]];
        q += r * r;
      }
      rq = used.length ? Math.sqrt(q / used.length) : 0.0;
      val = I(p.what) === 1 ? rq : c[1];
      for (k = 0; k < n; k++) lev.push(zs[k] - c[2] * xs[k] - c[0]);
      return base(val, proExact(p), used.length, thin(xs, 400), thin(lev, 400), [], [], { step: c[1], Rq: rq, slope: c[2] });
    });

  // ====================================================================================== Stoney
  var STO_T = [25.0, 75.0, 125.0, 175.0, 225.0];
  function stoSigma(p, T) { return p.sig - p.Mf * 1000.0 * p.daf * (T - p.T0); }
  function stoK(p, sigma) { return 6.0 * sigma * 1.0e6 * p.tf * 1.0e-6 / (p.Ms * 1.0e9 * Math.pow(p.ts * 1.0e-6, 2)); }
  function stoRead(p, kappa, n, st) {
    var xs, zs, k, x, c, s, D;
    if (I(p.method) === 1) {
      xs = []; zs = [];
      for (k = 0; k < n; k++) {
        x = -0.04 + 0.08 * k / (n - 1);
        xs.push(x);
        zs.push(kappa * x * x / 2.0 + 1.0e-4 * x + 2.0e-9 * gauss(st));
      }
      c = quad(xs, zs);
      return 2.0 * c[2];
    }
    s = 0.0;
    for (k = 0; k < n; k++) s += p.d + 2.0 * p.Ls * p.d * kappa + 2.0e-5 * gauss(st);
    D = s / n;
    return (D - p.d) / (2.0 * p.Ls * p.d);
  }
  function stoExact(p) { return I(p.what) === 1 ? -p.Mf * 1000.0 * p.daf : p.sig; }
  var PxStoney = kernel({ what: 0.0, method: 0.0, sig: -250.0, tf: 0.5, ts: 525.0, Ms: 180.5, Mf: 107.7, daf: 2.05e-5, T0: 25.0, k0: 0.0125, d: 0.02, Ls: 2.0, n: 1280.0, seed: 17.0 },
    function (p) {
      var n = Math.max(5, I(p.n)), st = lcg(p.seed), fac, k0, Ts, sig = [], i, k, ln, val, cx, cy;
      fac = p.Ms * 1.0e9 * Math.pow(p.ts * 1.0e-6, 2) / (6.0 * p.tf * 1.0e-6) / 1.0e6;
      k0 = stoRead(p, p.k0, n, st);
      Ts = I(p.what) === 0 ? [p.T0] : STO_T.slice();
      for (i = 0; i < Ts.length; i++) {
        k = stoRead(p, p.k0 + stoK(p, stoSigma(p, Ts[i])), n, st);
        sig.push(fac * (k - k0));
      }
      if (I(p.what) === 1) {
        ln = line(Ts, sig);
        val = ln[1];
        cx = [Ts[0], Ts[Ts.length - 1]];
        cy = [ln[0] + ln[1] * cx[0], ln[0] + ln[1] * cx[1]];
      } else {
        val = sig[0];
        cx = [0.0, 1.0];
        cy = [sig[0], sig[0]];
      }
      return base(val, stoExact(p), n, cx, cy, Ts.slice(), sig, { k0: k0, fac: fac });
    });

  // ====================================================================================== spin coating
  var SPIN_W = [1000.0, 1500.0, 2000.0, 3000.0, 4000.0, 6000.0];
  function spinH(p, w) { return p.K * Math.pow(w / 1000.0, -0.5); }
  function ebpR0(p, r, Kf, t) {
    var lo = 0.0, hi = r, i, mid, h0, rr;
    for (i = 0; i < 60; i++) {
      mid = 0.5 * (lo + hi);
      h0 = p.H0 * 1.0e-6 * (1.0 + p.a * (1.0 - Math.pow(mid / p.R, 2)));
      rr = mid * Math.pow(1.0 + 4.0 * Kf * h0 * h0 * t, 0.75);
      if (rr < r) lo = mid; else hi = mid;
    }
    return 0.5 * (lo + hi);
  }
  function ebpH(p, r) {
    var w = 2.0 * PI * p.w / 60.0, Kf = p.rho * w * w / (3.0 * p.eta), r0 = ebpR0(p, r, Kf, p.tf);
    var h0 = p.H0 * 1.0e-6 * (1.0 + p.a * (1.0 - Math.pow(r0 / p.R, 2)));
    return h0 / Math.sqrt(1.0 + 4.0 * Kf * h0 * h0 * p.tf);
  }
  function spinUnif(p, m) {
    var hs = [], rs = [], k, r, lo, hi, s = 0.0, h;
    for (k = 0; k < m; k++) { r = 0.9 * p.R * k / (m - 1); rs.push(r); hs.push(ebpH(p, r)); }
    lo = hs[0]; hi = hs[0];
    for (k = 0; k < hs.length; k++) { h = hs[k]; if (h < lo) lo = h; if (h > hi) hi = h; s += h; }
    return [100.0 * (hi - lo) / (s / m), rs, hs];
  }
  function spinExact(p) {
    var w = I(p.what);
    if (w === 1) return 0.5;
    if (w === 2) return spinUnif(p, 401)[0];
    return spinH(p, p.w);
  }
  var PxSpin = kernel({ what: 0.0, K: 520.0, w: 3000.0, H0: 20.0, a: 0.5, R: 0.0254, rho: 1000.0, eta: 0.1, tf: 1.0, n: 400.0, seed: 19.0 },
    function (p) {
      var n = Math.max(5, I(p.n)), w = I(p.what), uu, st, xs = [], ys = [], hs = [], i, k, s, h, ln, beta, hw, val, cx, cy;
      if (w === 2) {
        uu = spinUnif(p, n);
        return base(uu[0], spinExact(p), n, uu[1].map(function (r) { return r * 1000.0; }), uu[2].map(function (hh) { return hh * 1.0e6; }), [], [], { unif: uu[0] });
      }
      st = lcg(p.seed);
      for (i = 0; i < SPIN_W.length; i++) {
        s = 0.0;
        for (k = 0; k < n; k++) s += spinH(p, SPIN_W[i]) + 1.5 * gauss(st);
        h = s / n;
        hs.push(h);
        xs.push(Math.log(SPIN_W[i] / 1000.0));
        ys.push(Math.log(h));
      }
      ln = line(xs, ys);
      beta = -ln[1];
      hw = Math.exp(ln[0] + ln[1] * Math.log(p.w / 1000.0));
      val = w === 1 ? beta : hw;
      cx = [xs[0], xs[xs.length - 1]];
      cy = [ln[0] + ln[1] * cx[0], ln[0] + ln[1] * cx[1]];
      return base(val, spinExact(p), n, cx, cy, xs, ys, { beta: beta, hw: hw, hs: hs });
    });

  // ====================================================================================== impedance
  var IMP_T = [523.0, 548.0, 573.0, 598.0, 623.0], KB_EV = KB / QE;
  function impR(R, Ea, T, Tr) { return R * Math.exp(Ea / KB_EV * (1.0 / T - 1.0 / Tr)); }
  function impZ(p, T, f) {
    var w = 2.0 * PI * f, re = 0.0, im = 0.0, arcs = [[impR(p.Rb, p.Ea, T, p.Tr), p.Cb]], i, x;
    if (I(p.arcs) === 2) arcs.push([impR(p.Rgb, p.Eg, T, p.Tr), p.Cgb]);
    for (i = 0; i < arcs.length; i++) {
      x = w * arcs[i][0] * arcs[i][1];
      re += arcs[i][0] / (1.0 + x * x);
      im -= arcs[i][0] * x / (1.0 + x * x);
    }
    return [re, im];
  }
  function impScan(p, T, n, st) {
    var lf0 = Math.log10(p.fmin), lf1 = Math.log10(p.fmax), m = Math.max(3, I((lf1 - lf0) * n)) + 1, ls = [], re = [], mi = [], k, lf, z, g;
    for (k = 0; k < m; k++) {
      lf = lf0 + (lf1 - lf0) * k / (m - 1);
      z = impZ(p, T, Math.pow(10.0, lf));
      g = 1.0 + p.noise * (2.0 * u(st) - 1.0);
      ls.push(lf); re.push(z[0] * g); mi.push(-z[1] * g);
    }
    return [ls, re, mi];
  }
  function impPeaks(ls, mi, m) {
    var out = [], n = mi.length, k, j, ok;
    for (k = n - 2; k > 0; k--) {
      ok = true;
      for (j = Math.max(0, k - m); j <= Math.min(n - 1, k + m); j++) {
        if ((j < k && mi[j] >= mi[k]) || (j > k && mi[j] > mi[k])) { ok = false; break; }
      }
      if (ok) out.push(peak(ls, mi, k, Math.max(1, Math.floor(m / 2)), false));
    }
    return out;
  }
  function impExact(p) {
    var w = I(p.what), T = p.T, Rb;
    if (w === 3) return p.Ea;
    if (w === 1) return impR(p.Rgb, p.Eg, T, p.Tr);
    if (w === 4) return impR(p.Rgb, p.Eg, T, p.Tr) * p.Cgb;
    Rb = impR(p.Rb, p.Ea, T, p.Tr);
    if (w === 2) return Rb * p.Cb;
    return Rb;
  }
  var PxImp = kernel({ what: 0.0, arcs: 2.0, Rb: 1.0e5, Cb: 5.0e-12, Rgb: 4.0e5, Cgb: 2.0e-8, Ea: 0.95, Eg: 1.10, T: 573.0, Tr: 573.0, fmin: 0.01, fmax: 1.0e7, n: 20.0, noise: 0.002, seed: 23.0 },
    function (p) {
      var n = Math.max(2, I(p.n)), w = I(p.what), st = lcg(p.seed), xs = [], ys = [], i, sc, pk, Rb, ln, Ea, cx, cy, j, R, tau, val;
      if (w === 3) {
        for (i = 0; i < IMP_T.length; i++) {
          sc = impScan(p, IMP_T[i], n, st);
          pk = impPeaks(sc[0], sc[2], Math.max(1, I(0.5 * n)));
          Rb = pk.length ? 2.0 * pk[0][1] : 1.0;
          xs.push(1000.0 / IMP_T[i]);
          ys.push(Math.log(Rb));
        }
        ln = line(xs, ys);
        Ea = ln[1] * 1000.0 * KB_EV;
        cx = [xs[xs.length - 1], xs[0]];
        cy = [ln[0] + ln[1] * cx[0], ln[0] + ln[1] * cx[1]];
        return base(Ea, impExact(p), xs.length, cx, cy, xs, ys, { Ea: Ea });
      }
      sc = impScan(p, p.T, n, st);
      pk = impPeaks(sc[0], sc[2], Math.max(1, I(0.5 * n)));
      j = (w === 1 || w === 4) ? 1 : 0;
      if (j < pk.length) { R = 2.0 * pk[j][1]; tau = 1.0 / (2.0 * PI * Math.pow(10.0, pk[j][0])); } else { R = 0.0; tau = 0.0; }
      val = (w === 2 || w === 4) ? tau : R;
      return base(val, impExact(p), sc[0].length, thin(sc[1], 400), thin(sc[2], 400), [], [], { npeaks: pk.length, R: R, tau: tau });
    });

  // ====================================================================================== rocking curve
  function rockThB(p) { return Math.asin(p.lam / (2.0 * p.d)) * 180.0 / PI; }
  function rockExact(p) {
    var w = I(p.what), thB;
    if (w === 1) return p.mos * 3600.0;
    if (w === 2) return p.ws * 3600.0;
    thB = rockThB(p) * PI / 180.0;
    return -(p.dw * PI / 180.0) / Math.tan(thB);
  }
  var PxRock = kernel({ what: 0.0, sub: 0.0, lam: 0.1540562, d: 0.1357755, dw: -0.30, wf: 0.02, mos: 0.05, ws: 0.006, If: 0.25, n: 2400.0, noise: 0.02, seed: 29.0 },
    function (p) {
      var n = Math.max(60, I(p.n)), st = lcg(p.seed), thB = rockThB(p), wfm = Math.sqrt(p.wf * p.wf + p.mos * p.mos), xs = [], ys = [], k, x, y, dx, ks, gs, val, strain = 0.0, mos = 0.0, nf = 1, cut, kf, gf;
      for (k = 0; k < n; k++) {
        x = -0.8 + 1.2 * k / (n - 1);
        y = 1.0e-4 + Math.exp(-4.0 * Math.log(2.0) * x * x / (p.ws * p.ws));
        if (I(p.sub) === 0) y += p.If * Math.exp(-4.0 * Math.log(2.0) * Math.pow(x - p.dw, 2) / (wfm * wfm));
        xs.push(x);
        ys.push(y * (1.0 + p.noise * (2.0 * u(st) - 1.0)));
      }
      dx = xs[1] - xs[0];
      ks = argmax(ys, 0, n - 1);
      gs = gfit(xs, ys, ks, 1.0e-4);
      val = gs[1] * 3600.0;
      if (I(p.sub) === 0) {
        cut = Math.max(1, ks - I(4.0 * p.ws / dx));
        kf = argmax(ys, 0, cut);
        gf = gfit(xs, ys, kf, 1.0e-4);
        strain = -((gf[0] - gs[0]) * PI / 180.0) / Math.tan(thB * PI / 180.0);
        mos = Math.sqrt(Math.max(0.0, gf[1] * gf[1] - p.wf * p.wf)) * 3600.0;
        nf = 2;
        val = I(p.what) === 1 ? mos : I(p.what) === 0 ? strain : val;
      }
      return base(val, rockExact(p), nf, thin(xs, 600), thin(ys, 600), [], [], { thB: thB, strain: strain, mosaic: mos, wsub: gs[1] * 3600.0 });
    });

  // ====================================================================================== e-beam + QCM
  var QCM_RHOQ = 2648.0, QCM_MUQ = 2.947e10, QCM_P = [1.0, 1.5, 2.0, 2.5, 3.0];
  function qcmRate(p, P) { return p.r0 * Math.exp(-p.Pa / P); }
  function qcmCf(p) { return 2.0 * p.f0 * p.f0 / Math.sqrt(QCM_RHOQ * QCM_MUQ); }
  function qcmExact(p) {
    var s = 0.0, i;
    if (I(p.what) === 1) { for (i = 0; i < QCM_P.length; i++) s += qcmRate(p, QCM_P[i]) * p.Tst; return s; }
    return qcmRate(p, QCM_P[clampi(p.k, 0, 4)]);
  }
  var PxQcm = kernel({ what: 0.0, k: 2.0, rho: 4506.0, f0: 6.0e6, tool: 1.15, r0: 6.0, Pa: 3.5, Tst: 120.0, n: 240.0, seed: 31.0 },
    function (p) {
      var n = Math.max(4, I(p.n)), st = lcg(p.seed), Cf = qcmCf(p), f = p.f0, ts = [], fs = [], rates = [], tot = 0.0, t0 = 0.0, i, rc, xs, ys, k, t, fr, ln, r, val;
      for (i = 0; i < QCM_P.length; i++) {
        rc = qcmRate(p, QCM_P[i]) / p.tool * 1.0e-9;
        xs = []; ys = [];
        for (k = 0; k < n; k++) {
          t = p.Tst * k / (n - 1);
          fr = f - Cf * p.rho * rc * t + 0.05 * gauss(st);
          xs.push(t); ys.push(fr); ts.push(t0 + t); fs.push(fr);
        }
        ln = line(xs, ys);
        r = -ln[1] / (Cf * p.rho) * p.tool * 1.0e9;
        rates.push(r);
        tot += r * p.Tst;
        f = f - Cf * p.rho * rc * p.Tst;
        t0 += p.Tst;
      }
      val = I(p.what) === 1 ? tot : rates[clampi(p.k, 0, 4)];
      return base(val, qcmExact(p), n, thin(ts, 400), thin(fs, 400), QCM_P.slice(), rates, { rates: rates, thick: tot, Cf: Cf });
    });

  // ====================================================================================== AFM
  function afmExact(p) {
    var w = I(p.what);
    if (w === 1) return p.Fad;
    if (w === 2) return p.rq;
    if (w === 3) return p.h;
    return p.k;
  }
  var PxAfm = kernel({ what: 0.0, k: 2.0, inv: 50.0, T: 296.15, Fad: 15.0, rq: 0.8, h: 0.65, n: 131072.0, seed: 37.0 },
    function (p) {
      var n = Math.max(64, I(p.n)), w = I(p.what), st = lcg(p.seed), zs = [], vs = [], nc = Math.min(n, 4096), k, z, ln, inv;
      var m, sf, xs, hs, j, A, b, s, v, r, c, q, rq, val, lev, zp, rz, rv, vmin, F, sdz, mth, s2, kfit;
      for (k = 0; k < nc; k++) { z = 20.0 + 80.0 * k / (nc - 1); zs.push(z); vs.push((z - 20.0) / p.inv + 0.005 * gauss(st)); }
      ln = line(zs, vs);
      inv = 1.0 / ln[1];
      if (w === 2 || w === 3) {
        m = n < 8192 ? n : 8192;
        sf = proSurface({ rq: p.rq, seed: p.seed });
        xs = []; hs = [];
        for (k = 0; k < m; k++) {
          var x = 4000.0 * k / (m - 1);
          z = 0.002 * x + ((w === 3 && x > 2000.0) ? p.h : 0.0);
          for (j = 0; j < PRO_W.length; j++) z += sf[0][j] * Math.sin(2.0 * PI * x / (PRO_W[j] * 1.5) + sf[1][j]);
          xs.push(x); hs.push(0.01 * I(z / 0.01));
        }
        A = zeros3(); b = [0.0, 0.0, 0.0];
        for (k = 0; k < m; k++) {
          s = (w === 3 && xs[k] > 2000.0) ? 1.0 : 0.0;
          v = [1.0, s, xs[k]];
          for (r = 0; r < 3; r++) { for (c = 0; c < 3; c++) A[r][c] += v[r] * v[c]; b[r] += v[r] * hs[k]; }
        }
        if (w === 2) A[1][1] = 1.0;
        c = solve3(A, b);
        q = 0.0;
        for (k = 0; k < m; k++) {
          s = (w === 3 && xs[k] > 2000.0) ? 1.0 : 0.0;
          r = hs[k] - c[0] - c[1] * s - c[2] * xs[k];
          q += r * r;
        }
        rq = Math.sqrt(q / m);
        val = w === 2 ? rq : c[1];
        lev = [];
        for (k = 0; k < m; k++) lev.push(hs[k] - c[0] - c[2] * xs[k]);
        return base(val, afmExact(p), m, thin(xs, 400), thin(lev, 400), [], [], { inv: inv, Rq: rq, step: c[1] });
      }
      if (w === 1) {
        m = n < 8192 ? n : 8192;
        zp = 20.0 - p.Fad * 1.0e-9 / p.k * 1.0e9;
        rz = []; rv = []; vmin = 0.0;
        for (k = 0; k < m; k++) {
          z = 60.0 - 60.0 * k / (m - 1);
          v = z >= zp ? (z - 20.0) / p.inv : 0.0;
          rz.push(z); rv.push(v);
          if (v < vmin) vmin = v;
        }
        F = p.k * inv * 1.0e-9 * (-vmin) * 1.0e9;
        return base(F, afmExact(p), m, thin(rz, 400), thin(rv, 400), [], [], { inv: inv, kfit: p.k, Fad: F });
      }
      sdz = Math.sqrt(KB * p.T / p.k) * 1.0e9;
      mth = n;
      s2 = 0.0;
      for (k = 0; k < mth; k++) { v = sdz / p.inv * gauss(st); s2 += v * v; }
      kfit = KB * p.T / ((s2 / mth) * Math.pow(inv * 1.0e-9, 2));
      return base(kfit, afmExact(p), mth, thin(zs, 400), thin(vs, 400), [], [], { inv: inv, kfit: kfit });
    });

  // ====================================================================================== TEM / SAED
  function saedLambda(V) { return 1.0e9 * H / Math.sqrt(2.0 * ME * QE * V * (1.0 + QE * V / (2.0 * ME * C_LIGHT * C_LIGHT))); }
  var SAED_N = [3.0, 4.0, 8.0, 11.0, 12.0, 16.0];
  function saedExact(p) {
    var w = I(p.what), st, s, m, i;
    if (w === 0) return saedLambda(p.V) * p.L;
    if (w === 1) return p.aS / Math.sqrt(SAED_N[clampi(p.k - 1, 0, 5)]);
    if (w === 2) return p.aF * Math.sqrt(3.0) / 2.0;
    st = lcg(p.seed); s = 0.0; m = I(p.Ng);
    for (i = 0; i < m; i++) s += p.D0 * Math.exp(p.sg * gauss(st));
    return s / m;
  }
  var PxSaed = kernel({ what: 0.0, k: 1.0, V: 200.0e3, L: 800.0, aG: 0.40782, aS: 0.40495, aF: 0.3160, W: 60.0, D0: 12.0, sg: 0.25, Ng: 200.0, n: 2048.0, seed: 41.0 },
    function (p) {
      var n = Math.max(64, I(p.n)), w = I(p.what), lam = saedLambda(p.V), pix = p.W / n, lamL = lam * p.L;
      var st, ipix, m, s, ds, i, d, dm, hx, hy, bb, lo, hi, c, Rg, cal, j, R, val, px, py, ang, gx, gy;
      if (w === 3) {
        st = lcg(p.seed); ipix = 20.0 * p.D0 / n; m = I(p.Ng); s = 0.0; ds = [];
        for (i = 0; i < m; i++) { d = p.D0 * Math.exp(p.sg * gauss(st)); dm = ipix * I(d / ipix); ds.push(dm); s += dm; }
        hx = []; hy = [];
        for (bb = 0; bb < 16; bb++) {
          lo = 3.0 * p.D0 * bb / 16.0; hi = 3.0 * p.D0 * (bb + 1) / 16.0; c = 0;
          for (i = 0; i < ds.length; i++) if (lo <= ds[i] && ds[i] < hi) c += 1;
          hx.push(0.5 * (lo + hi)); hy.push(c);
        }
        return base(s / m, saedExact(p), m, hx, hy, [], [], { pix: ipix, lam: lam });
      }
      Rg = []; cal = 0.0;
      for (j = 0; j < 4; j++) {
        d = p.aG / Math.sqrt(SAED_N[j]);
        R = pix * I((lamL / d) / pix);
        Rg.push(R);
        cal += R * d;
      }
      cal /= 4.0;
      val = cal;
      px = [1.0, 2.0, 3.0, 4.0];
      py = Rg.slice();
      if (w === 1) {
        ds = []; py = [];
        for (j = 0; j < 6; j++) {
          d = p.aS / Math.sqrt(SAED_N[j]);
          R = pix * I((lamL / d) / pix);
          py.push(R);
          ds.push(cal / R);
        }
        px = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0];
        val = ds[clampi(p.k - 1, 0, 5)];
      } else if (w === 2) {
        d = p.aF * Math.sqrt(3.0) / 2.0; s = 0.0; px = []; py = [];
        for (j = 0; j < 6; j++) {
          ang = PI / 3.0 * j + 0.31;
          gx = pix * I((lamL / d) * Math.cos(ang) / pix);
          gy = pix * I((lamL / d) * Math.sin(ang) / pix);
          px.push(gx); py.push(gy);
          s += Math.sqrt(gx * gx + gy * gy);
        }
        val = cal / (s / 6.0);
      }
      return base(val, saedExact(p), n, [], [], px, py, { cal: cal, lam: lam, pix: pix });
    });

  // ====================================================================================== STM
  function lncosh(x) { var a = Math.abs(x); return a + Math.log1p(Math.exp(-2.0 * a)) - Math.log(2.0); }
  function stmI(p, V) { return V + 0.3 * (V + p.wE * (lncosh((V - p.E0) / p.wE) - lncosh(-p.E0 / p.wE))); }
  function stmExact(p) { var w = I(p.what); if (w === 1) return p.phi; if (w === 2) return p.E0; return p.a; }
  var PxStm = kernel({ what: 0.0, a: 0.288, phi: 4.5, E0: -0.487, wE: 0.03, n: 1200.0, seed: 43.0 },
    function (p) {
      var n = Math.max(20, I(p.n)), w = I(p.what), st = lcg(p.seed), xs = [], ys = [], k, j, z, Iz, ln, kap, kf, phi, cx, cy;
      var vs, Is, V, g, X, Y, gl, cl, gh, ch, half, E0, zs, x, m, win, peaks, ok, idx;
      if (w === 1) {
        kap = Math.sqrt(2.0 * ME * p.phi * QE) / HBAR * 1.0e-9;
        for (k = 0; k < n; k++) {
          z = 0.3 * k / (n - 1);
          Iz = Math.exp(-2.0 * kap * z) * (1.0 + 0.02 * (2.0 * u(st) - 1.0));
          xs.push(z); ys.push(Math.log(Iz));
        }
        ln = line(xs, ys);
        kf = -ln[1] / 2.0 * 1.0e9;
        phi = HBAR * HBAR * kf * kf / (2.0 * ME) / QE;
        cx = [0.0, 0.3];
        cy = [ln[0], ln[0] + ln[1] * 0.3];
        return base(phi, stmExact(p), n, cx, cy, thin(xs, 200), thin(ys, 200), { kappa: kf });
      }
      if (w === 2) {
        vs = []; Is = [];
        for (k = 0; k < n; k++) {
          V = -1.0 + 2.0 * k / (n - 1);
          vs.push(V);
          Is.push(stmI(p, V) * (1.0 + 0.002 * (2.0 * u(st) - 1.0)));
        }
        g = [];
        for (k = 0; k < n; k++) {
          X = []; Y = [];
          for (j = 0; j < n; j++) if (Math.abs(vs[j] - vs[k]) <= 0.04) { X.push(vs[j]); Y.push(Is[j]); }
          g.push(line(X, Y)[1]);
        }
        gl = 0.0; cl = 0; gh = 0.0; ch = 0;
        for (k = 1; k < n - 1; k++) {
          if (vs[k] < -0.85) { gl += g[k]; cl += 1; }
          if (-0.3 < vs[k] && vs[k] < -0.1) { gh += g[k]; ch += 1; }
        }
        gl = cl ? gl / cl : 1.0;
        gh = ch ? gh / ch : 1.0;
        half = 0.5 * (gl + gh);
        E0 = vs[0];
        for (k = 1; k < n - 1; k++) {
          if (g[k] < half && half <= g[k + 1]) { E0 = vs[k] + (vs[k + 1] - vs[k]) * (half - g[k]) / (g[k + 1] - g[k]); break; }
        }
        return base(E0, stmExact(p), n, thin(vs, 400), thin(g, 400), [], [], { onset: E0 });
      }
      zs = [];
      for (k = 0; k < n; k++) {
        x = 6.0 * k / (n - 1);
        xs.push(x);
        zs.push(0.02 * Math.cos(2.0 * PI * x / p.a) + 0.0015 * gauss(st));
      }
      m = Math.max(1, I(0.15 * p.a / (xs[1] - xs[0])));
      win = Math.max(1, I(0.4 * p.a / (xs[1] - xs[0])));
      peaks = [];
      for (k = m; k < n - m; k++) {
        if (zs[k] < 0.01) continue;
        ok = true;
        for (j = Math.max(0, k - win); j <= Math.min(n - 1, k + win); j++) {
          if ((j < k && zs[j] >= zs[k]) || (j > k && zs[j] > zs[k])) { ok = false; break; }
        }
        if (ok) peaks.push(peak(xs, zs, k, m, false)[0]);
      }
      idx = peaks.map(function (_, i2) { return i2; });
      ln = line(idx, peaks);
      return base(ln[1], stmExact(p), peaks.length, thin(xs, 600), thin(zs, 600), [], [], { npk: peaks.length });
    });

  // ====================================================================================== PLD + RHEED
  function pldExact(p) { return I(p.what) === 1 ? p.mos * 3600.0 : p.c / p.npm; }
  var PxPld = kernel({ what: 0.0, c: 1.168, npm: 28.0, f: 2.0, Np: 600.0, n: 10.0, noise: 0.02, seed: 47.0, d: 0.19525, dw: -0.25, wf: 0.02, mos: 0.08, ws: 0.006 },
    function (p) {
      var q, s, k, st, T, m, ts = [], ys = [], t, th, mean, cr, Pest, win, mx = [], j, ok, idx, ln, per, rate;
      if (I(p.what) === 1) {
        q = {}; for (k in PxRock.PARAMS) q[k] = PxRock.PARAMS[k];
        q.what = 1.0; q.d = p.d; q.dw = p.dw; q.wf = p.wf; q.mos = p.mos; q.ws = p.ws; q.n = p.n * 192.0; q.seed = p.seed;
        s = PxRock.init(q);
        s.exact = pldExact(p);
        s.err = errOf(s.val, s.exact);
        return s;
      }
      st = lcg(p.seed);
      T = p.Np / p.f;
      m = Math.max(20, I(T * p.n));
      for (k = 0; k < m; k++) {
        t = T * k / (m - 1);
        th = p.f * t / p.npm;
        ts.push(t);
        ys.push(0.3 + 0.6 * Math.exp(-th / 12.0) * Math.cos(2.0 * PI * th) + p.noise * gauss(st));
      }
      mean = 0.0;
      for (k = 0; k < m; k++) mean += ys[k];
      mean /= m;
      cr = 0;
      var low = false;
      for (k = 0; k < m; k++) {
        if (ys[k] < mean - 0.05) low = true;
        else if (low && ys[k] > mean + 0.05) { cr += 1; low = false; }
      }
      Pest = cr > 0 ? T / cr : T;
      win = Math.max(1, I(0.3 * Pest / (ts[1] - ts[0])));
      for (k = 1; k < m - 1; k++) {
        if (ys[k] < mean) continue;
        ok = true;
        for (j = Math.max(0, k - win); j <= Math.min(m - 1, k + win); j++) {
          if ((j < k && ys[j] >= ys[k]) || (j > k && ys[j] > ys[k])) { ok = false; break; }
        }
        if (ok) mx.push(peak(ts, ys, k, Math.max(1, Math.floor(win / 3)), false)[0]);
      }
      idx = mx.map(function (_, i2) { return i2; });
      ln = line(idx, mx);
      per = ln[1];
      rate = per > 0 ? p.c / (per * p.f) : 0.0;
      return base(rate, pldExact(p), mx.length, thin(ts, 600), thin(ys, 600), [], [], { period: per, ppu: per * p.f, nmax: mx.length });
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

  root.HoolaKernels.register({
    K: { px10_moseley: PxMoseley, px10_ruth: PxRuth, px10_mwi: PxMwi, px10_profilo: PxProfilo, px10_stoney: PxStoney,
      px10_spin: PxSpin, px10_imp: PxImp, px10_rock: PxRock, px10_qcm: PxQcm, px10_afm: PxAfm, px10_saed: PxSaed, px10_stm: PxStm, px10_pld: PxPld },
    TEXTBOOK: { px10_moseley_v: mosExact, px10_ruth_v: ruthExact, px10_mwi_v: function (p) { return p.NL; }, px10_profilo_v: proExact,
      px10_stoney_v: stoExact, px10_spin_v: spinExact, px10_imp_v: impExact, px10_rock_v: rockExact, px10_qcm_v: qcmExact,
      px10_afm_v: afmExact, px10_saed_v: saedExact, px10_stm_v: stmExact, px10_pld_v: pldExact },
    CALCS: {
      px10_finest: { label: 'answer on the most data', unit: '', needs: ['n', 'val'], fn: finest }
    }
  });
})(typeof window !== 'undefined' ? window : this);
