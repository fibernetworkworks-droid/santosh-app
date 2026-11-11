/* Kernel pack (browser twin of app/prayog/packs/comp2_ug.py): the UG "Computational physics" practicals, second set.
   Same formulas, same order of operations, so both sides give the same numbers. Deterministic throughout; the
   chaotic kernels use only + - * / so the iterates are bit-identical in both languages. Every kernel is prefixed cq_. */
(function (root) {
  'use strict';
  var PI = Math.PI, EH_EV = 27.211386245981;

  function I(v) { return Math.floor(v + 0.5); }
  function errOf(val, exact) { return Math.abs(val - exact) / Math.max(Math.abs(exact), 1e-30); }
  function grid(a, b, m) { var out = [], i; for (i = 0; i <= m; i++) out.push(a + (b - a) * i / m); return out; }
  function sum(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return s; }
  function rep(v, n) { var o = [], i; for (i = 0; i < n; i++) o.push(v); return o; }
  function mapf(xs, f) { var o = [], i; for (i = 0; i < xs.length; i++) o.push(f(xs[i])); return o; }
  function sgn(v) { return v >= 0 ? 1.0 : -1.0; }
  function mk(params, run) {
    var K = {
      PARAMS: params, VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'],
      init: function (p) { return run(p); },
      step: function (s, p, dt) { s.t += dt; },
      view: function (s) { return Object.assign({}, s); },
      measure: function (p) { var s = run(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
    };
    return K;
  }
  function state(val, exact, nused, cx, ce, cy, px, py, more) {
    var d = { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: nused,
      cx: cx || [], ce: ce || [], cy: cy || [], px: px || [], py: py || [] };
    if (more) Object.keys(more).forEach(function (k) { d[k] = more[k]; });
    return d;
  }

  // ====================================================================================== Fourier coefficients
  var FOUR_LIST = [[[1, 1], [1, 3], [1, 5], [1, 7]], [[0, 1], [0, 3], [0, 5], [0, 7]],
    [[0, 0], [1, 1], [0, 2], [0, 4]], [[0, 0], [0, 2], [0, 4], [0, 6]]];
  function fourF(cas, t, A) {
    var u, s;
    t = t - 2 * PI * Math.floor(t / (2 * PI));
    if (cas === 0) {
      if (Math.abs(t) < 1e-12 || Math.abs(t - PI) < 1e-12) return 0.0;
      return t < PI ? A : -A;
    }
    if (cas === 1) { u = t <= PI ? t : 2 * PI - t; return A * (1.0 - 2.0 * u / PI); }
    s = Math.sin(t);
    if (cas === 2) return s > 0 ? A * s : 0.0;
    return A * Math.abs(s);
  }
  function fourExact(p) {
    var cas = I(p.cas), A = p.A, ak = FOUR_LIST[cas][I(p.cidx) % 4], ab = ak[0], k = ak[1];
    if (cas === 0) return 4 * A / (k * PI);
    if (cas === 1) return 8 * A / (k * k * PI * PI);
    if (cas === 2) { if (k === 0) return A / PI; if (ab === 1) return A / 2; return -2 * A / (PI * (k * k - 1)); }
    if (k === 0) return 2 * A / PI;
    return -4 * A / (PI * (k * k - 1));
  }
  function fourCoef(ab, k, N, fs) {
    var s = 0.0, j, t;
    for (j = 0; j < N; j++) { t = 2 * PI * j / N; s += fs[j] * (ab === 0 ? Math.cos(k * t) : Math.sin(k * t)); }
    return k === 0 ? s / N : 2.0 * s / N;
  }
  function fourRun(p) {
    var cas = I(p.cas), N = Math.max(8, I(p.n)), A = p.A, fs = [], j, ak, ab, k, val, exact, H = 9, coefs = [], kk, cx, ce, cy = [], st, px = [], py = [], i, t, s;
    for (j = 0; j < N; j++) fs.push(fourF(cas, 2 * PI * j / N, A));
    ak = FOUR_LIST[cas][I(p.cidx) % 4]; ab = ak[0]; k = ak[1];
    val = fourCoef(ab, k, N, fs); exact = fourExact(p);
    for (kk = 0; kk <= H; kk++) coefs.push([fourCoef(0, kk, N, fs), kk > 0 ? fourCoef(1, kk, N, fs) : 0.0]);
    cx = grid(0.0, 2 * PI, 120); ce = mapf(cx, function (z) { return fourF(cas, z, A); });
    for (i = 0; i < cx.length; i++) {
      t = cx[i]; s = coefs[0][0];
      for (kk = 1; kk <= H; kk++) s += coefs[kk][0] * Math.cos(kk * t) + coefs[kk][1] * Math.sin(kk * t);
      cy.push(s);
    }
    st = Math.max(1, Math.floor(N / 64));
    for (j = 0; j < N; j += st) { px.push(2 * PI * j / N); py.push(fs[j]); }
    return state(val, exact, N, cx, ce, cy, px, py);
  }
  var CqFourier = mk({ cas: 0.0, cidx: 0.0, n: 64.0, A: 1.0 }, fourRun);

  // ====================================================================================== DFT / FFT
  function dftBins(x, nb) {
    var N = x.length, out = [], m, j, re, im, a;
    for (m = 0; m < nb; m++) {
      re = 0.0; im = 0.0;
      for (j = 0; j < N; j++) { a = 2 * PI * ((j * m) % N) / N; re += x[j] * Math.cos(a); im -= x[j] * Math.sin(a); }
      out.push([re, im]);
    }
    return out;
  }
  function fft(x) {
    var N = x.length, re = x.slice(), im = rep(0.0, N), i, j = 0, bit, t, ln, ang, i0, k, wr, wi, a, b, tr, ti, out = [];
    for (i = 1; i < N; i++) {
      bit = N >> 1;
      while (j & bit) { j ^= bit; bit >>= 1; }
      j ^= bit;
      if (i < j) { t = re[i]; re[i] = re[j]; re[j] = t; }
    }
    ln = 2;
    while (ln <= N) {
      ang = -2 * PI / ln;
      for (i0 = 0; i0 < N; i0 += ln) {
        for (k = 0; k < ln / 2; k++) {
          wr = Math.cos(ang * k); wi = Math.sin(ang * k); a = i0 + k; b = i0 + k + ln / 2;
          tr = re[b] * wr - im[b] * wi; ti = re[b] * wi + im[b] * wr;
          re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] = re[a] + tr; im[a] = im[a] + ti;
        }
      }
      ln *= 2;
    }
    for (i = 0; i < N; i++) out.push([re[i], im[i]]);
    return out;
  }
  function dsinc(x, w) { if (Math.abs(x) < 1e-12) return w; return Math.sin(PI * w * x) / (PI * x); }
  function dftExactF(cas, nu, p) {
    if (cas === 0) return Math.abs(dsinc(nu, 2 * p.a));
    if (cas === 1) return Math.abs(dsinc(nu - p.f0, p.L) + dsinc(nu + p.f0, p.L)) / 2;
    return p.sg * Math.sqrt(2 * PI) * Math.exp(-2 * PI * PI * p.sg * p.sg * nu * nu);
  }
  function dirichlet4(w) { var s = Math.sin(w / 2); return Math.abs(s) < 1e-12 ? 4.0 : Math.abs(Math.sin(2 * w) / s); }
  function dftSideExact() {
    var best = 0.0, i, w, v;
    for (i = 0; i <= 4000; i++) { w = PI / 2 + (PI / 2) * i / 4000; v = dirichlet4(w); if (v > best) best = v; }
    return best;
  }
  function dftExact(p) {
    var cas = I(p.cas);
    if (cas === 3) return dftSideExact();
    return dftExactF(cas, I(p.nu * p.L) / p.L, p);
  }
  function dftRun(p) {
    var cas = I(p.cas), meth = I(p.method), N = Math.max(4, I(p.n)), L = p.L, x = [], j, X, nb, mags = [], k, val, cx, ce, px, py, ops, dt, a, t, m, nmax;
    if (cas === 3) {
      for (j = 0; j < N; j++) x.push(j < 4 ? 1.0 : 0.0);
      nb = Math.floor(N / 2) + 1;
      X = meth === 1 ? fft(x) : dftBins(x, nb);
      for (k = 0; k < nb; k++) mags.push(Math.hypot(X[k][0], X[k][1]));
      val = 0.0;
      for (k = Math.floor(N / 4) + 1; k < nb; k++) if (mags[k] > val) val = mags[k];
      cx = grid(0.0, 1.0, 200); ce = mapf(cx, function (c) { return dirichlet4(PI * c); });
      px = []; for (k = 0; k < nb; k++) px.push(2.0 * k / N);
      ops = meth === 1 ? N * Math.log2(N) : N * N;
      return state(val, dftSideExact(), ops, cx, ce, [], px, mags);
    }
    dt = L / N; a = p.a;
    for (j = 0; j < N; j++) {
      t = -L / 2 + dt * j;
      if (cas === 0) x.push(Math.abs(Math.abs(t) - a) < 1e-9 ? 0.5 : (Math.abs(t) < a ? 1.0 : 0.0));
      else if (cas === 1) x.push(Math.cos(2 * PI * p.f0 * t));
      else x.push(Math.exp(-t * t / (2 * p.sg * p.sg)));
    }
    m = I(p.nu * L); nmax = I(p.numax * L);
    nb = Math.min(Math.floor(N / 2), Math.max(nmax, m)) + 1;
    X = meth === 1 ? fft(x) : dftBins(x, nb);
    for (k = 0; k < nb; k++) mags.push(dt * Math.hypot(X[k][0], X[k][1]));
    val = m < nb ? mags[m] : 0.0;
    cx = grid(0.0, p.numax, 160); ce = mapf(cx, function (c) { return dftExactF(cas, c, p); });
    px = []; for (k = 0; k < nb; k++) if (k / L <= p.numax + 1e-9) px.push(k / L);
    py = mags.slice(0, px.length);
    ops = meth === 1 ? N * Math.log2(N) : N * N;
    return state(val, dftExactF(cas, m / L, p), ops, cx, ce, [], px, py);
  }
  var CqDft = mk({ cas: 0.0, method: 1.0, n: 64.0, L: 16.0, a: 1.0, f0: 0.55, sg: 0.5, nu: 0.25, numax: 1.0 }, dftRun);

  // ====================================================================================== Gauss quadrature
  function gauleg(n) {
    var xs = rep(0.0, n), ws = rep(0.0, n), i, z, pp = 1.0, it, p1, p2, p3, j, z1;
    for (i = 0; i < Math.floor((n + 1) / 2); i++) {
      z = Math.cos(PI * (i + 0.75) / (n + 0.5));
      for (it = 0; it < 100; it++) {
        p1 = 1.0; p2 = 0.0;
        for (j = 1; j <= n; j++) { p3 = p2; p2 = p1; p1 = ((2.0 * j - 1.0) * z * p2 - (j - 1.0) * p3) / j; }
        pp = n * (z * p1 - p2) / (z * z - 1.0);
        z1 = z; z = z1 - p1 / pp;
        if (Math.abs(z - z1) < 1e-15) break;
      }
      xs[i] = -z; xs[n - 1 - i] = z; ws[i] = 2.0 / ((1.0 - z * z) * pp * pp); ws[n - 1 - i] = ws[i];
    }
    return [xs, ws];
  }
  function gaulag(n) {
    var xs = rep(0.0, n), ws = rep(0.0, n), i, z = 0.0, ai, pp = 1.0, p2 = 1.0, it, p1, p3, j, z1;
    for (i = 0; i < n; i++) {
      if (i === 0) z = 3.0 / (1.0 + 2.4 * n);
      else if (i === 1) z += 15.0 / (1.0 + 2.5 * n);
      else { ai = i - 1; z += ((1.0 + 2.55 * ai) / (1.9 * ai) + 0.0) * (z - xs[i - 2]); }
      for (it = 0; it < 100; it++) {
        p1 = 1.0; p2 = 0.0;
        for (j = 1; j <= n; j++) { p3 = p2; p2 = p1; p1 = ((2.0 * j - 1.0 - z) * p2 - (j - 1.0) * p3) / j; }
        pp = (n * p1 - n * p2) / z;
        z1 = z; z = z1 - p1 / pp;
        if (Math.abs(z - z1) <= 1e-14 * Math.max(1.0, Math.abs(z))) break;
      }
      xs[i] = z; ws[i] = -1.0 / (pp * n * p2);
    }
    return [xs, ws];
  }
  function gauher(n) {
    var xs = rep(0.0, n), ws = rep(0.0, n), pim4 = 0.7511255444649425, z = 0.0, i, pp = 1.0, it, p1, p2, p3, j, z1;
    for (i = 0; i < Math.floor((n + 1) / 2); i++) {
      if (i === 0) z = Math.sqrt(2.0 * n + 1.0) - 1.85575 * Math.pow(2.0 * n + 1.0, -1.0 / 6.0);
      else if (i === 1) z -= 1.14 * Math.pow(n, 0.426) / z;
      else if (i === 2) z = 1.86 * z - 0.86 * xs[0];
      else if (i === 3) z = 1.91 * z - 0.91 * xs[1];
      else z = 2.0 * z - xs[i - 2];
      for (it = 0; it < 100; it++) {
        p1 = pim4; p2 = 0.0;
        for (j = 1; j <= n; j++) { p3 = p2; p2 = p1; p1 = z * Math.sqrt(2.0 / j) * p2 - Math.sqrt((j - 1.0) / j) * p3; }
        pp = Math.sqrt(2.0 * n) * p2;
        z1 = z; z = z1 - p1 / pp;
        if (Math.abs(z - z1) < 1e-14) break;
      }
      xs[i] = z; xs[n - 1 - i] = -z; ws[i] = 2.0 / (pp * pp); ws[n - 1 - i] = ws[i];
    }
    return [xs, ws];
  }
  function gqF(meth, x, p) {
    if (meth === 0) return 4.0 / (1.0 + x * x);
    if (meth === 1) return Math.sin(p.wl * x);
    return Math.cos(p.wh * x);
  }
  function gqExact(p) {
    var meth = I(p.method);
    if (meth === 0) return PI;
    if (meth === 1) return p.wl / (1.0 + p.wl * p.wl);
    return Math.sqrt(PI) * Math.exp(-p.wh * p.wh / 4.0);
  }
  function gqRun(p) {
    var meth = I(p.method), n = Math.max(1, Math.min(40, I(p.n))), r, xs, ws, lo, hi, val = 0.0, i, cx, ce, px, py;
    if (meth === 0) { r = gauleg(n); xs = mapf(r[0], function (x) { return 0.5 * (x + 1.0); }); ws = mapf(r[1], function (w) { return 0.5 * w; }); lo = 0.0; hi = 1.0; }
    else if (meth === 1) { r = gaulag(n); xs = r[0]; ws = r[1]; lo = 0.0; hi = 12.0; }
    else { r = gauher(n); xs = r[0]; ws = r[1]; lo = -6.0; hi = 6.0; }
    for (i = 0; i < xs.length; i++) val += ws[i] * gqF(meth, xs[i], p);
    cx = grid(lo, hi, 160);
    var w1 = function (c) { return meth === 0 ? gqF(0, c, p) : meth === 1 ? Math.exp(-c) * gqF(1, c, p) : Math.exp(-c * c) * gqF(2, c, p); };
    ce = mapf(cx, w1); px = xs.slice(); py = mapf(xs, w1);
    return state(val, gqExact(p), n, cx, ce, [], px, py, { wsum: sum(ws) });
  }
  var CqGauss = mk({ cas: 0.0, method: 0.0, n: 4.0, wl: 1.0, wh: 1.0 }, gqRun);

  // ====================================================================================== radial Schrodinger
  function sturm(d, e2, x) {
    var cnt = 0, q = d[0] - x, i;
    if (q < 0) cnt += 1;
    for (i = 1; i < d.length; i++) {
      if (q === 0) q = 1e-300;
      q = d[i] - x - e2 / q;
      if (q < 0) cnt += 1;
    }
    return cnt;
  }
  function triEig(d, e, k) {
    var lo = Math.min.apply(null, d) - 2 * Math.abs(e), hi = Math.max.apply(null, d) + 2 * Math.abs(e), it, mid;
    for (it = 0; it < 100; it++) { mid = 0.5 * (lo + hi); if (sturm(d, e * e, mid) > k) hi = mid; else lo = mid; }
    return 0.5 * (lo + hi);
  }
  function triSolve(d, e, rhs) {
    var n = d.length, c = rep(0.0, n), b = rep(0.0, n), den = d[0], i, x = rep(0.0, n);
    c[0] = e / den; b[0] = rhs[0] / den;
    for (i = 1; i < n; i++) {
      den = d[i] - e * c[i - 1];
      if (den === 0) den = 1e-300;
      c[i] = e / den; b[i] = (rhs[i] - e * b[i - 1]) / den;
    }
    x[n - 1] = b[n - 1];
    for (i = n - 2; i >= 0; i--) x[i] = b[i] - c[i] * x[i + 1];
    return x;
  }
  function triVec(d, e, lam) {
    var n = d.length, sh = lam - 1e-9 * Math.max(1.0, Math.abs(lam)), dd = mapf(d, function (x) { return x - sh; }), v = [], j, it, s;
    for (j = 0; j < n; j++) v.push(1.0 + 0.5 * Math.sin(0.37 * (j + 1)));
    for (it = 0; it < 3; it++) {
      v = triSolve(dd, e, v);
      s = Math.sqrt(v.reduce(function (a, x) { return a + x * x; }, 0));
      v = mapf(v, function (x) { return x / s; });
    }
    return v;
  }
  function schSetup(p) {
    var cas = I(p.cas), N = Math.max(20, I(p.n)), ll = I(p.ll), k = I(p.kst), h, xs = [], j, d = [], e, nq, unit, mu, rmax, g, xmax, lam, y0, y1, x;
    if (cas === 0) {
      mu = p.mu; rmax = p.rmax; h = rmax / (N + 1);
      for (j = 0; j < N; j++) xs.push(h * (j + 1));
      d = mapf(xs, function (x) { return 1.0 / (mu * h * h) + ll * (ll + 1) / (2 * mu * x * x) - 1.0 / x; });
      e = -1.0 / (2 * mu * h * h); nq = k + ll + 1;
      return { xs: xs, d: d, e: e, unit: EH_EV, ex: -mu / (2.0 * nq * nq) * EH_EV, h: h };
    }
    if (cas === 1) {
      g = p.g; xmax = p.rmax; h = xmax / (N + 1);
      for (j = 0; j < N; j++) xs.push(h * (j + 1));
      d = mapf(xs, function (x) { return 2.0 / (h * h) + ll * (ll + 1) / (x * x) - g / (Math.exp(x) - 1.0); });
      e = -1.0 / (h * h); unit = EH_EV / (2.0 * p.aa * p.aa); nq = k + 1;
      return { xs: xs, d: d, e: e, unit: unit, ex: -Math.pow((g - nq * nq) / (2.0 * nq), 2) * unit, h: h };
    }
    lam = p.lam; y0 = p.ymin; y1 = p.rmax; h = (y1 - y0) / (N + 1);
    for (j = 0; j < N; j++) xs.push(y0 + h * (j + 1));
    d = mapf(xs, function (x) { return 2.0 / (h * h) + lam * lam * (Math.exp(-2 * x) - 2 * Math.exp(-x)); });
    e = -1.0 / (h * h);
    return { xs: xs, d: d, e: e, unit: p.e0, ex: Math.pow(lam - k - 0.5, 2) * p.e0, h: h };
  }
  function schExactU(p, x) {
    var cas = I(p.cas), ll = I(p.ll), k = I(p.kst), mu, kap, xi;
    if (cas === 0) {
      mu = p.mu;
      if (ll === 0 && k === 0) return 2 * Math.pow(mu, 1.5) * x * Math.exp(-mu * x);
      if (ll === 0 && k === 1) return Math.pow(mu, 1.5) / (2 * Math.sqrt(2.0)) * x * (2 - mu * x) * Math.exp(-mu * x / 2);
      if (ll === 1 && k === 0) return Math.pow(mu, 2.5) / (2 * Math.sqrt(6.0)) * x * x * Math.exp(-mu * x / 2);
      return NaN;
    }
    if (cas === 1 && ll === 0 && k === 0) { kap = (p.g - 1.0) / 2.0; return (1.0 - Math.exp(-x)) * Math.exp(-kap * x); }
    if (cas === 2 && k === 0) { xi = 2 * p.lam * Math.exp(-x); return Math.pow(xi, p.lam - 0.5) * Math.exp(-xi / 2); }
    return NaN;
  }
  function schRun(p) {
    var cas = I(p.cas), S = schSetup(p), k = I(p.kst), lam = triEig(S.d, S.e, k), val = cas !== 2 ? lam * S.unit : -lam * S.unit,
      v = triVec(S.d, S.e, lam), h = S.h, sh = Math.sqrt(h), u = mapf(v, function (a) { return a / sh; }), big = 0.0, i, x0 = p.xd0, x1 = p.xd1,
      cx = grid(x0, x1, 200), raw = mapf(cx, function (c) { return schExactU(p, c); }), ce = [], s = 0.0, f, idx = [], st, px = [], py = [];
    for (i = 0; i < u.length; i++) if (Math.abs(u[i]) > big) big = Math.abs(u[i]);
    for (i = 0; i < u.length; i++) if (Math.abs(u[i]) > 0.05 * big) { if (u[i] < 0) u = mapf(u, function (b) { return -b; }); break; }
    if (raw.length && raw[0] === raw[0]) {
      for (i = 0; i < cx.length - 1; i++) s += 0.5 * (raw[i] * raw[i] + raw[i + 1] * raw[i + 1]) * (cx[i + 1] - cx[i]);
      f = 1.0 / Math.sqrt(s); ce = mapf(raw, function (r) { return r * f; });
    }
    for (i = 0; i < S.xs.length; i++) if (x0 <= S.xs[i] && S.xs[i] <= x1) idx.push(i);
    st = Math.max(1, Math.floor(idx.length / 90));
    for (i = 0; i < idx.length; i += st) { px.push(S.xs[idx[i]]); py.push(u[idx[i]]); }
    return state(val, S.ex, S.xs.length, cx, ce, [], px, py);
  }
  var CqSchro = mk({ cas: 0.0, kst: 0.0, ll: 0.0, n: 400.0, mu: 1.0, rmax: 40.0, g: 10.0, aa: 5.0, lam: 18.1357, ymin: -0.6, e0: 121.336,
    xd0: 0.0, xd1: 20.0 }, schRun);

  // ====================================================================================== special functions
  function legendreRec(n, x) {
    var p0 = 1.0, p1 = x, j, t;
    if (n === 0) return 1.0;
    for (j = 1; j < n; j++) { t = ((2.0 * j + 1.0) * x * p1 - j * p0) / (j + 1.0); p0 = p1; p1 = t; }
    return p1;
  }
  function binomial(m, k) { var c = 1.0, i; for (i = 1; i <= k; i++) c = c * (m - k + i) / i; return c; }
  function legendreSum(n, x) {
    var s = 0.0, k;
    for (k = 0; k <= Math.floor(n / 2); k++) s += Math.pow(-1.0, k) * binomial(n, k) * binomial(2 * n - 2 * k, n) * Math.pow(x, n - 2 * k);
    return s / Math.pow(2.0, n);
  }
  function laguerreRec(n, x) {
    var p0 = 1.0, p1 = 1.0 - x, j, t;
    if (n === 0) return 1.0;
    for (j = 1; j < n; j++) { t = ((2.0 * j + 1.0 - x) * p1 - j * p0) / (j + 1.0); p0 = p1; p1 = t; }
    return p1;
  }
  function laguerreSum(n, x) {
    var s = 0.0, f = 1.0, k;
    for (k = 0; k <= n; k++) { if (k > 0) f = f * k; s += Math.pow(-1.0, k) * binomial(n, k) * Math.pow(x, k) / f; }
    return s;
  }
  function hermiteRec(n, x) {
    var p0 = 1.0, p1 = 2.0 * x, j, t;
    if (n === 0) return 1.0;
    for (j = 1; j < n; j++) { t = 2.0 * x * p1 - 2.0 * j * p0; p0 = p1; p1 = t; }
    return p1;
  }
  function hermiteSum(n, x) {
    var s = 0.0, m, c, i;
    for (m = 0; m <= Math.floor(n / 2); m++) {
      c = 1.0;
      for (i = 1; i <= n; i++) c = c * i;
      for (i = 1; i <= m; i++) c = c / i;
      for (i = 1; i <= n - 2 * m; i++) c = c / i;
      s += Math.pow(-1.0, m) * c * Math.pow(2.0 * x, n - 2 * m);
    }
    return s;
  }
  function besselSeries(n, x) {
    var t = Math.pow(x / 2.0, n), i, s, k;
    for (i = 1; i <= n; i++) t = t / i;
    s = t;
    for (k = 1; k < 80; k++) { t = -t * (x / 2.0) * (x / 2.0) / (k * (k + n)); s += t; }
    return s;
  }
  function besselUp(n, x) {
    var j0, j1, j, t;
    if (Math.abs(x) < 1e-9) return besselSeries(n, x);
    j0 = besselSeries(0, x); j1 = besselSeries(1, x);
    if (n === 0) return j0;
    for (j = 1; j < n; j++) { t = (2.0 * j / x) * j1 - j0; j0 = j1; j1 = t; }
    return j1;
  }
  function besselDown(n, x) {
    var m, jp = 0.0, jc = 1e-30, ans = 0.0, norm = 0.0, j, jm;
    if (Math.abs(x) < 1e-9) return besselSeries(n, x);
    m = 2 * Math.floor((n + I(Math.sqrt(40.0 * n)) + 4) / 2);
    for (j = m; j > 0; j--) {
      jm = (2.0 * j / x) * jc - jp; jp = jc; jc = jm;
      if (Math.abs(jc) > 1e10) { jc *= 1e-10; jp *= 1e-10; ans *= 1e-10; norm *= 1e-10; }
      if (j - 1 === n) ans = jc;
      if ((j - 1) % 2 === 0 && j - 1 > 0) norm += 2.0 * jc;
    }
    norm += jc;
    return ans / norm;
  }
  function specFn(cas, meth, n, x) {
    if (cas === 0) return [legendreRec(n, x), legendreSum(n, x)];
    if (cas === 2) return [laguerreRec(n, x), laguerreSum(n, x)];
    if (cas === 3) return [hermiteRec(n, x), hermiteSum(n, x)];
    return [meth === 0 ? besselUp(n, x) : besselDown(n, x), besselSeries(n, x)];
  }
  function specExact(p) {
    var cas = I(p.cas);
    if (cas === 1) return 2.0 / (2 * I(p.deg) + 1);
    return specFn(cas, 0, I(p.n), p.x)[1];
  }
  function orthVal(meth, N, m1, m2) {
    var f = function (x) { return legendreRec(m1, x) * legendreRec(m2, x); }, r, xs, ws, i, h, ys, s;
    if (meth === 2) {
      r = gauleg(N); xs = r[0]; ws = r[1]; s = 0.0;
      for (i = 0; i < xs.length; i++) s += ws[i] * f(xs[i]);
      return [s, xs, mapf(xs, f)];
    }
    N = N + (N % 2); h = 2.0 / N; xs = []; ys = [];
    for (i = 0; i <= N; i++) { xs.push(-1.0 + h * i); ys.push(f(xs[i])); }
    if (meth === 0) {
      s = 0.5 * (ys[0] + ys[N]);
      for (i = 1; i < N; i++) s += ys[i];
      return [s * h, xs, ys];
    }
    s = ys[0] + ys[N];
    for (i = 1; i < N; i++) s += (i % 2 === 1 ? 4.0 : 2.0) * ys[i];
    return [s * h / 3.0, xs, ys];
  }
  function specRun(p) {
    var cas = I(p.cas), meth = I(p.method), n = Math.max(1, I(p.n)), deg, o, c, cx, ce, cy, r, x0;
    if (cas === 1) {
      deg = I(p.deg); o = orthVal(meth, n, deg, deg); c = orthVal(meth, n, deg, deg + 2);
      cx = grid(-1.0, 1.0, 120); ce = mapf(cx, function (z) { return Math.pow(legendreSum(deg, z), 2); });
      return state(o[0], 2.0 / (2 * deg + 1), n, cx, ce, [], o[1], o[2], { cross: Math.abs(c[0]) });
    }
    x0 = p.x; r = specFn(cas, meth, n, x0);
    cx = grid(p.xa, p.xb, 120);
    ce = mapf(cx, function (z) { return specFn(cas, meth, n, z)[1]; });
    cy = mapf(cx, function (z) { return specFn(cas, meth, n, z)[0]; });
    return state(r[0], r[1], n, cx, ce, cy, [x0], [r[0]]);
  }
  var CqSpecial = mk({ cas: 0.0, method: 0.0, n: 6.0, deg: 4.0, x: 0.6, xa: -1.0, xb: 1.0 }, specRun);

  // ====================================================================================== linear systems
  function det3(a) {
    return a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
      + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
  }
  function cramer(a, b) {
    var d = det3(a), out = [], c, r, cc, m;
    for (c = 0; c < 3; c++) {
      m = [];
      for (r = 0; r < 3; r++) { m.push([]); for (cc = 0; cc < 3; cc++) m[r].push(cc === c ? b[r] : a[r][cc]); }
      out.push(det3(m) / d);
    }
    return out;
  }
  function lsMatrix(p) {
    var a;
    if (I(p.cas) === 0) {
      a = [[p.r1 + p.rb + p.rf, -p.rb, -p.rf], [-p.rb, p.r2 + p.rb + p.rd, -p.rd], [-p.rf, -p.rd, p.r3 + p.rd + p.rf]];
      return [a, [p.e1, p.e2, p.e3]];
    }
    a = [[p.k1 + p.k2, -p.k2, 0.0], [-p.k2, p.k2 + p.k3, -p.k3], [0.0, -p.k3, p.k3 + p.k4]];
    return [a, [p.f1, p.f2, p.f3]];
  }
  function gaussElim(a, b) {
    var n = b.length, m = [], i, c, piv, r, f, cc, x = rep(0.0, n), s, t;
    for (i = 0; i < n; i++) m.push(a[i].concat([b[i]]));
    for (c = 0; c < n; c++) {
      piv = c;
      for (r = c + 1; r < n; r++) if (Math.abs(m[r][c]) > Math.abs(m[piv][c])) piv = r;
      t = m[c]; m[c] = m[piv]; m[piv] = t;
      for (r = c + 1; r < n; r++) { f = m[r][c] / m[c][c]; for (cc = c; cc <= n; cc++) m[r][cc] -= f * m[c][cc]; }
    }
    for (r = n - 1; r >= 0; r--) { s = m[r][n]; for (cc = r + 1; cc < n; cc++) s -= m[r][cc] * x[cc]; x[r] = s / m[r][r]; }
    return x;
  }
  function lsExact(p) { var ab = lsMatrix(p); return cramer(ab[0], ab[1])[I(p.pick)]; }
  function lsRun(p) {
    var meth = I(p.meth === undefined ? p.method : p.method), n = Math.max(1, I(p.n)), pick = I(p.pick), ab = lsMatrix(p), a = ab[0], b = ab[1],
      xe = cramer(a, b), exact = xe[pick], x, hist = [], it, i, j, s, cx;
    if (meth === 0) { x = gaussElim(a, b); return state(x[pick], exact, 9, [1.0, 2.0, 3.0], xe.slice(), x.slice(), [1.0, 2.0, 3.0], x.slice()); }
    x = [0.0, 0.0, 0.0];
    for (it = 0; it < n; it++) {
      for (i = 0; i < 3; i++) { s = b[i]; for (j = 0; j < 3; j++) if (j !== i) s -= a[i][j] * x[j]; x[i] = s / a[i][i]; }
      hist.push(x[pick]);
    }
    cx = []; for (i = 0; i < n; i++) cx.push(i + 1.0);
    return state(x[pick], exact, 9 * n, cx, rep(exact, n), hist.slice(), cx.slice(), hist.slice());
  }
  var CqLinsys = mk({ cas: 0.0, method: 1.0, n: 6.0, pick: 0.0, r1: 10.0, r2: 15.0, r3: 25.0, rb: 20.0, rd: 30.0, rf: 40.0,
    e1: 12.0, e2: 0.0, e3: -6.0, k1: 300.0, k2: 200.0, k3: 250.0, k4: 400.0, f1: 1.0, f2: 2.0, f3: 0.5 }, lsRun);

  // ====================================================================================== eigenvalues
  function chainExact(M, kk) { return 2.0 - 2.0 * Math.cos(kk * PI / (M + 1)); }
  function jacobiSweeps(a0, nsw) {
    var a = a0.map(function (r) { return r.slice(); }), hist = [Math.min(a[0][0], a[1][1], a[2][2])], s0, pq = [[0, 1], [0, 2], [1, 2]], q, pp, qq, th, t, c, s, k, akp, akq, apk, aqk;
    for (s0 = 0; s0 < nsw; s0++) {
      for (q = 0; q < 3; q++) {
        pp = pq[q][0]; qq = pq[q][1];
        if (Math.abs(a[pp][qq]) < 1e-300) continue;
        th = (a[qq][qq] - a[pp][pp]) / (2.0 * a[pp][qq]);
        t = (th >= 0 ? 1.0 : -1.0) / (Math.abs(th) + Math.sqrt(th * th + 1.0));
        c = 1.0 / Math.sqrt(t * t + 1.0); s = t * c;
        for (k = 0; k < 3; k++) { akp = a[k][pp]; akq = a[k][qq]; a[k][pp] = c * akp - s * akq; a[k][qq] = s * akp + c * akq; }
        for (k = 0; k < 3; k++) { apk = a[pp][k]; aqk = a[qq][k]; a[pp][k] = c * apk - s * aqk; a[qq][k] = s * apk + c * aqk; }
      }
      hist.push(Math.min(a[0][0], a[1][1], a[2][2]));
    }
    return hist;
  }
  function inertia(p) {
    var cas = I(p.cas), m = p.mass, a2, t, a, b, c, i1, i2, i3, c1, s1, c2, s2, c3, s3, rz, rx, rw, rzx, r, dg, i, j, k;
    if (cas === 1) {
      a2 = p.sa * p.sa;
      t = [[2.0 / 3, -0.25, -0.25], [-0.25, 2.0 / 3, -0.25], [-0.25, -0.25, 2.0 / 3]];
      return [t.map(function (row) { return row.map(function (v) { return m * a2 * v; }); }), m * a2 / 6.0];
    }
    a = p.sa; b = p.sb; c = p.sc;
    i1 = m * (b * b + c * c) / 12.0; i2 = m * (a * a + c * c) / 12.0; i3 = m * (a * a + b * b) / 12.0;
    c1 = Math.cos(p.th1); s1 = Math.sin(p.th1); c2 = Math.cos(p.th2); s2 = Math.sin(p.th2); c3 = Math.cos(p.th3); s3 = Math.sin(p.th3);
    rz = [[c1, -s1, 0.0], [s1, c1, 0.0], [0.0, 0.0, 1.0]];
    rx = [[1.0, 0.0, 0.0], [0.0, c2, -s2], [0.0, s2, c2]];
    rw = [[c3, -s3, 0.0], [s3, c3, 0.0], [0.0, 0.0, 1.0]];
    var mul = function (u, v) { var o = [], q, w, z, s; for (q = 0; q < 3; q++) { o.push([]); for (w = 0; w < 3; w++) { s = 0; for (z = 0; z < 3; z++) s += u[q][z] * v[z][w]; o[q].push(s); } } return o; };
    rzx = mul(rz, rx); r = mul(rzx, rw); dg = [i1, i2, i3]; t = [];
    for (i = 0; i < 3; i++) { t.push([]); for (j = 0; j < 3; j++) { var s = 0; for (k = 0; k < 3; k++) s += r[i][k] * dg[k] * r[j][k]; t[i].push(s); } }
    return [t, Math.min(i1, i2, i3)];
  }
  function eigRun(p) {
    var cas = I(p.cas), meth = I(p.method), n = Math.max(1, I(p.n)), ai, hist, cx = [], i, M, ex, v = [], d, est = 0.0, it, w, num, den, nr, j;
    if (cas !== 0) {
      ai = inertia(p); hist = jacobiSweeps(ai[0], n);
      for (i = 0; i <= n; i++) cx.push(i + 0.0);
      return state(hist[hist.length - 1], ai[1], n * 3, cx, rep(ai[1], n + 1), hist, cx.slice(), hist.slice());
    }
    M = I(p.mdim); ex = meth === 0 ? chainExact(M, M) : chainExact(M, 1);
    for (j = 0; j < M; j++) v.push(1.0 / (1.0 + 0.37 * j));
    d = rep(2.0, M); hist = [];
    for (it = 0; it < n; it++) {
      if (meth === 0) {
        w = []; for (j = 0; j < M; j++) w.push(2.0 * v[j] - (j > 0 ? v[j - 1] : 0.0) - (j < M - 1 ? v[j + 1] : 0.0));
        num = 0; den = 0; for (j = 0; j < M; j++) { num += w[j] * v[j]; den += v[j] * v[j]; }
        est = num / den;
      } else {
        w = triSolve(d, -1.0, v); num = 0; den = 0;
        for (j = 0; j < M; j++) { num += v[j] * v[j]; den += w[j] * v[j]; }
        est = num / den;
      }
      nr = 0; for (j = 0; j < M; j++) nr += w[j] * w[j]; nr = Math.sqrt(nr);
      v = mapf(w, function (a) { return a / nr; });
      hist.push(est);
    }
    for (i = 0; i < n; i++) cx.push(i + 1.0);
    return state(est, ex, n * M, cx, rep(ex, n), hist, cx.slice(), hist.slice());
  }
  function eigExact(p) {
    if (I(p.cas) !== 0) return inertia(p)[1];
    var M = I(p.mdim);
    return chainExact(M, I(p.method) === 0 ? M : 1);
  }
  var CqEig = mk({ cas: 0.0, method: 0.0, n: 10.0, mdim: 6.0, mass: 1.0, sa: 1.0, sb: 2.0, sc: 3.0, th1: 0.6, th2: 0.4, th3: 0.9 }, eigRun);

  // ====================================================================================== logistic map
  function lmSettled(r, T, per) {
    var x = 0.3, i, x0;
    for (i = 0; i < T; i++) x = r * x * (1.0 - x);
    x0 = x;
    for (i = 0; i < per; i++) x = r * x * (1.0 - x);
    return Math.abs(x - x0) < 1e-7;
  }
  function lmSuper(k, guess) {
    var r = guess, m = Math.pow(2, k), it, x, d, j, step;
    for (it = 0; it < 60; it++) {
      x = 0.5; d = 0.0;
      for (j = 0; j < m; j++) { d = x * (1.0 - x) + r * (1.0 - 2.0 * x) * d; x = r * x * (1.0 - x); }
      step = (x - 0.5) / d; r = r - step;
      if (Math.abs(step) < 1e-14) break;
    }
    return r;
  }
  function lmSeries(n) {
    var rs = [2.0, lmSuper(1, 3.2)], k, d;
    for (k = 2; k <= n; k++) { d = k === 2 ? 4.2 : 4.6692; rs.push(lmSuper(k, rs[k - 1] + (rs[k - 1] - rs[k - 2]) / d)); }
    return rs;
  }
  var FEIG = 4.669201609102990;
  function lmExact(p) { var cas = I(p.cas); if (cas === 0) return 3.0; if (cas === 1) return 1.0 + Math.sqrt(6.0); return FEIG; }
  function lmDiagram(r0, r1) {
    var bx = [], by = [], i, r, x, j;
    for (i = 0; i < 240; i++) {
      r = r0 + (r1 - r0) * i / 239.0; x = 0.3;
      for (j = 0; j < 400; j++) x = r * x * (1.0 - x);
      for (j = 0; j < 36; j++) { x = r * x * (1.0 - x); bx.push(r); by.push(x); }
    }
    return [bx, by];
  }
  function lmRun(p) {
    var cas = I(p.cas), n = Math.max(2, I(p.n)), rs, val, dg, lo, hi, per, it, mid, ex, py = [], i;
    if (cas === 2) {
      n = Math.min(n, 9); rs = lmSeries(n); val = (rs[n - 1] - rs[n - 2]) / (rs[n] - rs[n - 1]); dg = lmDiagram(2.9, 3.6);
      for (i = 0; i < rs.length; i++) py.push(0.5);
      return state(val, FEIG, n, [], [], [], rs, py, { bx: dg[0], by: dg[1], mx: [], my: [] });
    }
    lo = cas === 0 ? 2.9 : 3.40; hi = cas === 0 ? 3.1 : 3.50; per = cas === 0 ? 1 : 2;
    for (it = 0; it < 40; it++) { mid = 0.5 * (lo + hi); if (lmSettled(mid, n, per)) lo = mid; else hi = mid; }
    val = 0.5 * (lo + hi); ex = lmExact(p); dg = lmDiagram(2.9, 3.6);
    return state(val, ex, n * 40, [], [], [], [val], [0.5], { bx: dg[0], by: dg[1], mx: [ex], my: [0.5] });
  }
  var CqMap = mk({ cas: 0.0, n: 1000.0 }, lmRun);

  // ====================================================================================== Lorenz system
  function lzF(s, sg, rho, be) { return [sg * (s[1] - s[0]), s[0] * (rho - s[2]) - s[1], s[0] * s[1] - be * s[2]]; }
  function lzRk4(s, h, sg, rho, be) {
    var k1 = lzF(s, sg, rho, be), k2 = lzF([s[0] + 0.5 * h * k1[0], s[1] + 0.5 * h * k1[1], s[2] + 0.5 * h * k1[2]], sg, rho, be),
      k3 = lzF([s[0] + 0.5 * h * k2[0], s[1] + 0.5 * h * k2[1], s[2] + 0.5 * h * k2[2]], sg, rho, be),
      k4 = lzF([s[0] + h * k3[0], s[1] + h * k3[1], s[2] + h * k3[2]], sg, rho, be), o = [], i;
    for (i = 0; i < 3; i++) o.push(s[i] + h / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]));
    return o;
  }
  function lzG(w, sg, rho, be) {
    var x = w[0], y = w[1], z = w[2], out = [sg * (y - x), x * (rho - z) - y, x * y - be * z], i, j,
      jac = [[-sg, sg, 0.0], [rho - z, -1.0, -x], [y, x, -be]];
    for (i = 0; i < 3; i++) for (j = 0; j < 3; j++) out.push(jac[i][0] * w[3 + j] + jac[i][1] * w[6 + j] + jac[i][2] * w[9 + j]);
    return out;
  }
  function lzAdd(w, k, f) { var o = [], i; for (i = 0; i < 12; i++) o.push(w[i] + f * k[i]); return o; }
  function lzRun(p) {
    var sg = p.sg, rho = p.rho, be = p.be, T = p.T, n = Math.max(10, I(p.n)), h = T / n, w = [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
      it, k1, k2, k3, k4, i, val, ex, s, px = [], py = [], mx = [0.0], my = [0.0], c;
    for (it = 0; it < n; it++) {
      k1 = lzG(w, sg, rho, be); k2 = lzG(lzAdd(w, k1, 0.5 * h), sg, rho, be); k3 = lzG(lzAdd(w, k2, 0.5 * h), sg, rho, be); k4 = lzG(lzAdd(w, k3, h), sg, rho, be);
      for (i = 0; i < 12; i++) w[i] = w[i] + h / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]);
    }
    val = det3([[w[3], w[4], w[5]], [w[6], w[7], w[8]], [w[9], w[10], w[11]]]);
    ex = Math.exp(-(sg + 1.0 + be) * T);
    s = [1.0, 1.0, 1.0];
    for (i = 0; i < 2400; i++) { s = lzRk4(s, 0.01, sg, rho, be); if (i % 2 === 0 && i > 200) { px.push(s[0]); py.push(s[2]); } }
    if (rho > 1.0) { c = Math.sqrt(be * (rho - 1.0)); mx.push(c, -c); my.push(rho - 1.0, rho - 1.0); }
    return state(val, ex, n * 4, [], [], [], px, py, { mx: mx, my: my });
  }
  var CqLorenz = mk({ n: 20.0, sg: 10.0, rho: 28.0, be: 8.0 / 3.0, T: 1.0 }, lzRun);

  // ====================================================================================== boundary value problems
  function bvpExactAt(cas, x, L, B) { return cas === 0 ? B * Math.sin(x) / Math.sin(L) : B * Math.sinh(x) / Math.sinh(L); }
  function bvpExact(p) { return bvpExactAt(I(p.cas), p.L / 2.0, p.L, p.B); }
  function bvpRun(p) {
    var cas = I(p.cas), meth = I(p.method), n = Math.max(2, I(p.n)), L = p.L, B = p.B, h, q, xs = [], i, m, d, rhs, y, a0, a1, s, val, ex, cx;
    n += n % 2; h = L / n; q = cas === 0 ? 1.0 : -1.0;
    for (i = 0; i <= n; i++) xs.push(h * i);
    var shot = function (s0) {
      var yy = 0.0, v = s0, out = [0.0], j, k1y, k1v, k2y, k2v, k3y, k3v, k4y, k4v;
      for (j = 0; j < n; j++) {
        k1y = v; k1v = -q * yy;
        k2y = v + 0.5 * h * k1v; k2v = -q * (yy + 0.5 * h * k1y);
        k3y = v + 0.5 * h * k2v; k3v = -q * (yy + 0.5 * h * k2y);
        k4y = v + h * k3v; k4v = -q * (yy + h * k3y);
        yy += h / 6.0 * (k1y + 2 * k2y + 2 * k3y + k4y); v += h / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v);
        out.push(yy);
      }
      return out;
    };
    if (meth === 0) {
      m = n - 1; d = rep(q - 2.0 / (h * h), m); rhs = rep(0.0, m); rhs[m - 1] = -B / (h * h);
      y = [0.0].concat(triSolve(d, 1.0 / (h * h), rhs)).concat([B]);
    } else {
      a0 = shot(0.0); a1 = shot(1.0); s = (B - a0[n]) / (a1[n] - a0[n]); y = shot(s);
    }
    val = y[n / 2]; ex = bvpExactAt(cas, L / 2.0, L, B); cx = grid(0.0, L, 100);
    return state(val, ex, n, cx, mapf(cx, function (c) { return bvpExactAt(cas, c, L, B); }), [], xs, y);
  }
  var CqBvp = mk({ cas: 0.0, method: 0.0, n: 8.0, L: 1.5, B: 1.0 }, bvpRun);

  // ====================================================================================== PDEs
  function pdeExactAt(cas, x, y, p) {
    if (cas === 0) return Math.sin(PI * x) * Math.sinh(PI * y) / Math.sinh(PI);
    if (cas === 1) return Math.exp(-PI * PI * p.al * p.T) * Math.sin(PI * x);
    return Math.cos(PI * p.cw * p.T) * Math.sin(PI * x);
  }
  function pdeExact(p) { return pdeExactAt(I(p.cas), 0.5, 0.5, p); }
  function pdeRun(p) {
    var cas = I(p.cas), meth = I(p.method), n = Math.max(4, I(p.n)), h, xs = [], i, j, ex, m, u, w, sweeps, dm, nw, g, dv, val, cx, ce, row,
      T, al, dt, steps, r, old, mi, rhs, diag, off, sol, c, nu, tt, u0, u1, u2, ys;
    n += n % 2; h = 1.0 / n;
    for (i = 0; i <= n; i++) xs.push(h * i);
    ex = pdeExact(p);
    if (cas === 0) {
      m = n + 1; u = [];
      for (i = 0; i < m; i++) { row = rep(0.0, m); row[n] = Math.sin(PI * xs[i]); u.push(row); }
      w = 1.0; if (meth === 2) w = 2.0 / (1.0 + Math.sin(PI / n));
      for (sweeps = 1; sweeps <= 20000; sweeps++) {
        dm = 0.0;
        if (meth === 0) {
          nw = u.map(function (rw) { return rw.slice(); });
          for (i = 1; i < n; i++) for (j = 1; j < n; j++) { nw[i][j] = 0.25 * (u[i + 1][j] + u[i - 1][j] + u[i][j + 1] + u[i][j - 1]); dm = Math.max(dm, Math.abs(nw[i][j] - u[i][j])); }
          u = nw;
        } else {
          for (i = 1; i < n; i++) for (j = 1; j < n; j++) {
            g = 0.25 * (u[i + 1][j] + u[i - 1][j] + u[i][j + 1] + u[i][j - 1]); dv = w * (g - u[i][j]); u[i][j] += dv; dm = Math.max(dm, Math.abs(dv));
          }
        }
        if (dm < 1e-11) break;
      }
      if (sweeps > 20000) sweeps = 20000;
      val = u[n / 2][n / 2]; cx = grid(0.0, 1.0, 100); ce = mapf(cx, function (z) { return pdeExactAt(0, z, 0.5, p); });
      ys = []; for (i = 0; i < m; i++) ys.push(u[i][n / 2]);
      return state(val, ex, sweeps, cx, ce, [], xs, ys);
    }
    T = p.T;
    if (cas === 1) {
      al = p.al; dt = p.dt; steps = Math.max(1, I(T / dt)); dt = T / steps; r = al * dt / (h * h);
      u = mapf(xs, function (x) { return Math.sin(PI * x); }); mi = n - 1;
      for (i = 0; i < steps; i++) {
        old = u.slice();
        if (meth === 0) { for (j = 1; j < n; j++) u[j] = old[j] + r * (old[j + 1] - 2.0 * old[j] + old[j - 1]); }
        else {
          if (meth === 1) { rhs = old.slice(1, n); diag = rep(1.0 + 2.0 * r, mi); }
          else { rhs = []; for (j = 1; j < n; j++) rhs.push(old[j] + 0.5 * r * (old[j + 1] - 2.0 * old[j] + old[j - 1])); diag = rep(1.0 + r, mi); }
          off = meth === 1 ? -r : -0.5 * r;
          sol = triSolve(diag, off, rhs); u = [0.0].concat(sol).concat([0.0]);
        }
      }
      val = u[n / 2]; cx = grid(0.0, 1.0, 100); ce = mapf(cx, function (z) { return pdeExactAt(1, z, 0.0, p); });
      return state(val, ex, steps * n, cx, ce, [], xs, u, { rnum: r });
    }
    c = p.cw; nu = p.nu; dt = nu * h / c; steps = Math.max(1, I(T / dt));
    u0 = mapf(xs, function (x) { return Math.sin(PI * x); }); u1 = u0.slice();
    for (i = 1; i < n; i++) u1[i] = u0[i] + 0.5 * nu * nu * (u0[i + 1] - 2.0 * u0[i] + u0[i - 1]);
    for (j = 0; j < steps - 1; j++) {
      u2 = u1.slice();
      for (i = 1; i < n; i++) u2[i] = 2.0 * u1[i] - u0[i] + nu * nu * (u1[i + 1] - 2.0 * u1[i] + u1[i - 1]);
      u0 = u1; u1 = u2;
    }
    tt = steps * dt; val = u1[n / 2]; ex = Math.cos(PI * c * tt) * Math.sin(PI * 0.5);
    cx = grid(0.0, 1.0, 100); ce = mapf(cx, function (z) { return Math.cos(PI * c * tt) * Math.sin(PI * z); });
    return state(val, ex, steps * n, cx, ce, [], xs, u1, { tend: tt });
  }
  var CqPde = mk({ cas: 0.0, method: 2.0, n: 10.0, al: 1.0, dt: 0.002, T: 0.1, cw: 1.0, nu: 0.8 }, pdeRun);

  // ====================================================================================== Planck's law
  var H_SI = 6.62607015e-34, C_SI = 299792458.0, K_SI = 1.380649e-23;
  function plXstar() {
    var lo = 4.0, hi = 6.0, i, mid;
    for (i = 0; i < 200; i++) { mid = 0.5 * (lo + hi); if ((mid - 5.0) * Math.exp(mid) + 5.0 < 0) lo = mid; else hi = mid; }
    return 0.5 * (lo + hi);
  }
  function plM(lam, T) { return 2 * PI * H_SI * C_SI * C_SI / Math.pow(lam, 5) / (Math.exp(H_SI * C_SI / (lam * K_SI * T)) - 1.0); }
  function plExact(p) {
    var cas = I(p.cas), T = p.T, xs = plXstar();
    if (cas === 0) return 2 * Math.pow(PI, 5) * Math.pow(K_SI, 4) / (15 * Math.pow(H_SI, 3) * C_SI * C_SI) * Math.pow(T, 4);
    if (cas === 1) return H_SI * C_SI / (K_SI * xs * T);
    if (cas === 2) return (Math.exp(xs) - 1.0) / xs;
    return 1.0 - Math.exp(-xs);
  }
  function plPeak(T, n) {
    var g = 0.5 * (Math.sqrt(5.0) - 1.0), a = 0.2 * 2.9e-3 / T, b = 5.0 * 2.9e-3 / T, c = b - g * (b - a), d = a + g * (b - a), fc = plM(c, T), fd = plM(d, T), i;
    for (i = 0; i < n; i++) {
      if (fc > fd) { b = d; d = c; fd = fc; c = b - g * (b - a); fc = plM(c, T); }
      else { a = c; c = d; fc = fd; d = a + g * (b - a); fd = plM(d, T); }
    }
    return 0.5 * (a + b);
  }
  function plRun(p) {
    var cas = I(p.cas), n = Math.max(2, I(p.n)), T = p.T, exact = plExact(p), lp = 2.9e-3 / T, m, xmax, h, s, i, x, f, integral, val, lam, cx, ce, cy, mp, px, py, stp;
    if (cas === 0) {
      m = n + n % 2; xmax = 50.0; h = xmax / m; s = 0.0;
      for (i = 0; i <= m; i++) {
        x = h * i; f = i === 0 ? 0.0 : x * x * x / (Math.exp(x) - 1.0);
        s += f * (i === 0 || i === m ? 1.0 : (i % 2 === 1 ? 4.0 : 2.0));
      }
      integral = s * h / 3.0;
      val = 2 * PI * Math.pow(K_SI, 4) * Math.pow(T, 4) / (Math.pow(H_SI, 3) * C_SI * C_SI) * integral;
      cx = grid(0.0, 20.0, 120); ce = mapf(cx, function (c) { return c === 0 ? 0.0 : c * c * c / (Math.exp(c) - 1.0); });
      px = []; py = []; stp = Math.max(1, Math.floor(m / 40));
      for (i = 0; i <= m; i += stp) { px.push(h * i); py.push(i === 0 ? 0.0 : Math.pow(h * i, 3) / (Math.exp(h * i) - 1.0)); }
      return state(val, exact, m, cx, ce, [], px, py);
    }
    lam = plPeak(T, n); x = H_SI * C_SI / (lam * K_SI * T);
    val = cas === 1 ? lam : (cas === 2 ? (Math.exp(x) - 1.0) / x : 1.0 - Math.exp(-x));
    cx = grid(0.1 * lp, 5.0 * lp, 120); mp = plM(lp, T);
    ce = mapf(cx, function (c) { return plM(c, T) / mp; });
    cy = mapf(cx, function (c) { return Math.min(1.6, (2 * PI * C_SI * K_SI * T / Math.pow(c, 4)) / mp); });
    return state(val, exact, n, cx, ce, cy, [lam], [plM(lam, T) / mp]);
  }
  var CqPlanck = mk({ cas: 0.0, n: 40.0, T: 5772.0 }, plRun);

  // ====================================================================================== least-squares fitting
  function lcgSeed(seed) { var s = I(seed) % 2147483647; return [s > 0 ? s : 1.0]; }
  function lcgU(st) { st[0] = (st[0] * 16807.0) % 2147483647; return st[0] / 2147483647; }
  function fitTrue(cas, x, p) {
    if (cas === 0) return p.a0 + p.b0 * x;
    if (cas === 1) return p.a0 * Math.pow(x, p.b0);
    if (cas === 2) return p.a0 * Math.exp(-x / p.b0);
    return p.a0 + p.b0 * x + p.c0 * x * x;
  }
  function fitExact(p) { return I(p.cas) === 3 ? p.c0 : p.b0; }
  function fitSolve(rows, ys, wt) {
    var m = rows[0].length, ata = [], aty = rep(0.0, m), i, j, k, c, sd = [], e, col;
    for (i = 0; i < m; i++) ata.push(rep(0.0, m));
    for (k = 0; k < rows.length; k++) for (i = 0; i < m; i++) { aty[i] += wt[k] * rows[k][i] * ys[k]; for (j = 0; j < m; j++) ata[i][j] += wt[k] * rows[k][i] * rows[k][j]; }
    c = gaussElim(ata, aty);
    for (i = 0; i < m; i++) { e = []; for (j = 0; j < m; j++) e.push(j === i ? 1.0 : 0.0); col = gaussElim(ata, e); sd.push(Math.sqrt(col[i])); }
    return [c, sd];
  }
  function fitRun(p) {
    var cas = I(p.cas), N = Math.max(4, I(p.n)), wted = I(p.wt), sig = p.sig, st = lcgSeed(p.seed), xs = [], ys = [], ss = [], i, x, yt, u1, u2, g,
      ly = [], rows = [], wt = [], r, c, sd, val, unc, fitf, j, ssr, f, k, cx, stp, px = [], py = [];
    for (i = 0; i < N; i++) {
      x = p.x0 + (p.x1 - p.x0) * (i + 0.5) / N; yt = fitTrue(cas, x, p); u1 = lcgU(st); u2 = lcgU(st);
      g = Math.sqrt(-2.0 * Math.log(u1 > 1e-300 ? u1 : 1e-300)) * Math.cos(2 * PI * u2);
      xs.push(x); ys.push(yt * (1.0 + sig * g)); ss.push(sig * Math.abs(yt));
    }
    if (cas === 1 || cas === 2) {
      for (i = 0; i < N; i++) { ly.push(Math.log(ys[i])); rows.push(cas === 1 ? [1.0, Math.log(xs[i])] : [1.0, xs[i]]); wt.push(1.0); }
      r = fitSolve(rows, ly, wt); c = r[0]; sd = r[1];
      if (cas === 1) { val = c[1]; unc = sd[1] * sig; fitf = function (z) { return Math.exp(c[0]) * Math.pow(z, c[1]); }; }
      else { val = -1.0 / c[1]; unc = sd[1] * sig / (c[1] * c[1]); fitf = function (z) { return Math.exp(c[0] + c[1] * z); }; }
    } else {
      for (i = 0; i < N; i++) { rows.push(cas === 0 ? [1.0, xs[i]] : [1.0, xs[i], xs[i] * xs[i]]); wt.push(wted === 1 ? 1.0 / (ss[i] * ss[i]) : 1.0); }
      r = fitSolve(rows, ys, wt); c = r[0]; sd = r[1]; j = cas === 0 ? 1 : 2; val = c[j];
      if (wted === 1) unc = sd[j];
      else {
        ssr = 0.0;
        for (k = 0; k < N; k++) { f = 0.0; for (i = 0; i < c.length; i++) f += rows[k][i] * c[i]; ssr += (ys[k] - f) * (ys[k] - f); }
        unc = sd[j] * Math.sqrt(ssr / (N - c.length));
      }
      fitf = cas === 0 ? function (z) { return c[0] + c[1] * z; } : function (z) { return c[0] + c[1] * z + c[2] * z * z; };
    }
    cx = grid(p.x0, p.x1, 80); stp = Math.max(1, Math.floor(N / 60));
    for (i = 0; i < N; i += stp) { px.push(xs[i]); py.push(ys[i]); }
    return state(val, fitExact(p), N, cx, mapf(cx, function (z) { return fitTrue(cas, z, p); }), mapf(cx, fitf), px, py, { unc: unc });
  }
  var CqFit = mk({ cas: 0.0, wt: 1.0, n: 200.0, seed: 2024.0, sig: 0.04, x0: 1.0, x1: 10.0, a0: 2.0, b0: 3.0, c0: 0.5 }, fitRun);

  // ====================================================================================== calcs
  function rowsOf(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) { v = Number(rs[i][keys[j]]); if (rs[i][keys[j]] === '' || rs[i][keys[j]] === null || rs[i][keys[j]] === undefined || !isFinite(v)) { ok = false; break; } vals.push(v); }
      if (ok) out.push(vals);
    }
    return out;
  }
  function slope(pts) {
    var sx = 0, sy = 0, sxx = 0, sxy = 0, i, den;
    for (i = 0; i < pts.length; i++) { sx += pts[i][0]; sy += pts[i][1]; sxx += pts[i][0] * pts[i][0]; sxy += pts[i][0] * pts[i][1]; }
    den = pts.length * sxx - sx * sx;
    if (Math.abs(den) < 1e-30) return 0.0;
    return (pts.length * sxy - sx * sy) / den;
  }

  root.HoolaKernels.register({
    K: { cq_fourier: CqFourier, cq_dft: CqDft, cq_gauss: CqGauss, cq_schro: CqSchro, cq_special: CqSpecial, cq_linsys: CqLinsys, cq_eig: CqEig,
      cq_map: CqMap, cq_lorenz: CqLorenz, cq_bvp: CqBvp, cq_pde: CqPde, cq_planck: CqPlanck, cq_fit: CqFit },
    TEXTBOOK: {
      cq_fourier_c: fourExact, cq_dft_F: dftExact, cq_gauss_I: gqExact, cq_schro_E: function (p) { return schSetup(p).ex; },
      cq_special_v: specExact, cq_linsys_x: lsExact, cq_eig_l: eigExact,
      cq_map_r: lmExact, cq_lorenz_det: function (p) { return Math.exp(-(p.sg + 1.0 + p.be) * p.T); }, cq_bvp_y: bvpExact,
      cq_pde_u: pdeExact, cq_planck_v: plExact, cq_fit_p: fitExact
    },
    CALCS: {
      cq_best: { label: 'best value', unit: '', needs: ['n', 'val'],
        fn: function (r) { var rs = rowsOf(r, ['n', 'val']), i, best; if (!rs.length) return 0; best = rs[0];
          for (i = 0; i < rs.length; i++) if (rs[i][0] > best[0]) best = rs[i]; return best[1]; } },
      cq_order: { label: 'order of the method', unit: '', needs: ['n', 'err'],
        fn: function (r) { var rs = rowsOf(r, ['n', 'err']), pts = [], i;
          for (i = 0; i < rs.length; i++) if (rs[i][0] > 0 && rs[i][1] > 0) pts.push([Math.log(rs[i][0]), Math.log(rs[i][1])]);
          return -slope(pts); } },
      cq_ratio: { label: 'error factor per iteration', unit: '', needs: ['n', 'err'],
        fn: function (r) { var rs = rowsOf(r, ['n', 'err']), pts = [], i;
          for (i = 0; i < rs.length; i++) if (rs[i][1] > 1e-15) pts.push([rs[i][0], Math.log(rs[i][1])]);
          return pts.length >= 2 ? Math.exp(slope(pts)) : 0.0; } }
    }
  });
})(typeof window !== 'undefined' ? window : this);
