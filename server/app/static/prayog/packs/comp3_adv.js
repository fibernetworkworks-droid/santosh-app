/* Kernel pack (browser twin of app/prayog/packs/comp3_adv.py): the M.Sc. / Ph.D. "Computational physics" practicals.
   Same formulas, same order of operations, so both sides give the same numbers. Deterministic throughout: anything
   random is a seeded Lehmer generator (16807, mod 2^31 - 1), never the clock.
     cr_interp cr_pde cr_fem cr_fit cr_mle cr_dev cr_walk cr_decay cr_twolevel cr_mcint cr_scatter cr_poly cr_photon
     cr_ising cr_binder cr_tb cr_schro cr_nbody cr_spin cr_ed cr_mcmc cr_fdtd cr_pic
   Every kernel reports val (numerical), exact (the reference), err, nused and the curves the monitor draws. */
(function (root) {
  'use strict';
  var PI = Math.PI, M31 = 2147483647;

  function I(v) { return Math.floor(v + 0.5); }
  function errOf(val, exact) { return Math.abs(val - exact) / Math.max(Math.abs(exact), 1e-30); }
  function grid(a, b, m) { var out = [], i; for (i = 0; i <= m; i++) out.push(a + (b - a) * i / m); return out; }
  function zeros(n) { var o = [], i; for (i = 0; i < n; i++) o.push(0.0); return o; }
  function fill(n, v) { var o = [], i; for (i = 0; i < n; i++) o.push(v); return o; }
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
  function mod(a, b) { var r = a % b; return r < 0 ? r + b : r; }
  function lcg(seed) { var s = mod(I(seed), M31); return [s > 0 ? s : 1]; }
  function u(st) { st[0] = (st[0] * 16807) % M31; return st[0] / M31; }
  function gauss(st) {
    var u1 = u(st), u2 = u(st);
    return Math.sqrt(-2.0 * Math.log(u1 > 1e-300 ? u1 : 1e-300)) * Math.cos(2 * PI * u2);
  }
  function marksOf(N) {
    var out = [], i, v;
    for (i = 1; i <= 60; i++) {
      v = I(Math.pow(N, i / 60.0)); if (v < 1) v = 1;
      if (!out.length || v > out[out.length - 1]) out.push(v);
    }
    return out;
  }
  function erf(x) {
    var sg = 1.0, term, s, n;
    if (x < 0) { x = -x; sg = -1.0; }
    if (x > 6.0) return sg;
    term = x; s = x; n = 0;
    while (n < 400) {
      n += 1; term = term * 2.0 * x * x / (2 * n + 1); s += term;
      if (term < 1e-17 * s) break;
    }
    return sg * 2.0 / Math.sqrt(PI) * Math.exp(-x * x) * s;
  }
  function solve(A, b) {
    var n = b.length, Mx = [], c, r, k, piv, d, f, x, s, t;
    for (r = 0; r < n; r++) { Mx.push(A[r].slice()); Mx[r].push(b[r]); }
    for (c = 0; c < n; c++) {
      piv = c;
      for (r = c + 1; r < n; r++) if (Math.abs(Mx[r][c]) > Math.abs(Mx[piv][c])) piv = r;
      t = Mx[c]; Mx[c] = Mx[piv]; Mx[piv] = t;
      d = Mx[c][c]; if (Math.abs(d) < 1e-300) d = 1e-300;
      for (r = c + 1; r < n; r++) {
        f = Mx[r][c] / d;
        for (k = c; k <= n; k++) Mx[r][k] -= f * Mx[c][k];
      }
    }
    x = zeros(n);
    for (r = n - 1; r >= 0; r--) {
      s = Mx[r][n];
      for (k = r + 1; k < n; k++) s -= Mx[r][k] * x[k];
      d = Mx[r][r]; if (Math.abs(d) < 1e-300) d = 1e-300;
      x[r] = s / d;
    }
    return x;
  }
  function tri(a, b, c, d) {
    var n = d.length, cp = zeros(n), dp = zeros(n), x = zeros(n), i, m;
    cp[0] = c[0] / b[0]; dp[0] = d[0] / b[0];
    for (i = 1; i < n; i++) {
      m = b[i] - a[i] * cp[i - 1];
      cp[i] = i < n - 1 ? c[i] / m : 0.0;
      dp[i] = (d[i] - a[i] * dp[i - 1]) / m;
    }
    x[n - 1] = dp[n - 1];
    for (i = n - 2; i >= 0; i--) x[i] = dp[i] - cp[i] * x[i + 1];
    return x;
  }
  function base(val, exact, nused, cx, ce, cy, px, py, extra) {
    var s = { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: nused, cx: cx, ce: ce, cy: cy, px: px, py: py }, k;
    if (extra) for (k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) s[k] = extra[k];
    return s;
  }
  var VARS = ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'];
  function kernel(def) {
    def.VARS = VARS;
    def.step = function (s, p, dt) { s.t += dt; };
    def.view = function (s) { return Object.assign({}, s); };
    def.measure = function (p) { var s = def.init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; };
    return def;
  }
  function maxAbs(a) { var m = 0, i; for (i = 0; i < a.length; i++) if (Math.abs(a[i]) > m) m = Math.abs(a[i]); return m; }
  function fsum(a) { var s = 0, i; for (i = 0; i < a.length; i++) s += a[i]; return s; }

  // ====================================================================================== interpolation
  function ipF(cas, x) { if (cas === 1) return 1.0 / (1.0 + 25.0 * x * x); return Math.sin(x); }
  function ipDf(cas, x) { if (cas === 1) { var d = 1.0 + 25.0 * x * x; return -50.0 * x / (d * d); } return Math.cos(x); }
  function lagr(xs, ys, x) {
    var tot = 0.0, i, j, L;
    for (i = 0; i < xs.length; i++) {
      L = 1.0;
      for (j = 0; j < xs.length; j++) if (j !== i) L = L * (x - xs[j]) / (xs[i] - xs[j]);
      tot += ys[i] * L;
    }
    return tot;
  }
  function splineFit(xs, ys, d0, d1) {
    var n = xs.length - 1, h = xs[1] - xs[0], a = zeros(n + 1), b = zeros(n + 1), c = zeros(n + 1), d = zeros(n + 1), i;
    b[0] = h / 3.0; c[0] = h / 6.0; d[0] = (ys[1] - ys[0]) / h - d0;
    for (i = 1; i < n; i++) { a[i] = h / 6.0; b[i] = 2.0 * h / 3.0; c[i] = h / 6.0; d[i] = (ys[i + 1] - 2.0 * ys[i] + ys[i - 1]) / h; }
    a[n] = h / 6.0; b[n] = h / 3.0; d[n] = d1 - (ys[n] - ys[n - 1]) / h;
    return tri(a, b, c, d);
  }
  function splineAt(xs, ys, Mm, x) {
    var n = xs.length - 1, h = xs[1] - xs[0], j = Math.floor((x - xs[0]) / h), l, r;
    if (j < 0) j = 0; if (j > n - 1) j = n - 1;
    l = xs[j + 1] - x; r = x - xs[j];
    return (Mm[j] * l * l * l + Mm[j + 1] * r * r * r) / (6.0 * h) + (ys[j] / h - Mm[j] * h / 6.0) * l + (ys[j + 1] / h - Mm[j + 1] * h / 6.0) * r;
  }
  var CrInterp = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 8.0, x: 1.3, xa: 0.0, xb: PI },
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), n = Math.max(2, I(p.n)), xa = p.xa, xb = p.xb, xs = grid(xa, xb, n), ys = [], i, ev, Mm, cx, ce = [], cy = [];
      for (i = 0; i < xs.length; i++) ys.push(ipF(cas, xs[i]));
      if (meth === 0) ev = function (q) { return lagr(xs, ys, q); };
      else { Mm = splineFit(xs, ys, ipDf(cas, xa), ipDf(cas, xb)); ev = function (q) { return splineAt(xs, ys, Mm, q); }; }
      var val = ev(p.x), exact = ipF(cas, p.x);
      cx = grid(xa, xb, 120);
      for (i = 0; i < cx.length; i++) { ce.push(ipF(cas, cx[i])); cy.push(ev(cx[i])); }
      return base(val, exact, n + 1, cx, ce, cy, xs, ys);
    }
  });
  function ipExact(p) { return ipF(I(p.cas), p.x); }

  // ====================================================================================== finite differences
  function hat(y) { return y <= 0.5 ? 2.0 * y : 2.0 * (1.0 - y); }
  function hatExt(x) { var y = x - 2.0 * Math.floor((x + 1.0) / 2.0); return y < 0 ? -hat(-y) : hat(y); }
  function pdeExactAt(p, x) {
    var cas = I(p.cas), t = p.tend, tot = 0.0, m = 1, b;
    if (cas === 1) return 0.5 * (hatExt(x - p.c * t) + hatExt(x + p.c * t));
    while (m <= 61) {
      b = 8.0 / (m * m * PI * PI) * ((m % 4) === 1 ? 1.0 : -1.0);
      tot += b * Math.sin(m * PI * x) * Math.exp(-p.c * m * m * PI * PI * t);
      m += 2;
    }
    return tot;
  }
  function lap(uu) { var n = uu.length, out = zeros(n), j; for (j = 1; j < n - 1; j++) out[j] = uu[j + 1] - 2.0 * uu[j] + uu[j - 1]; return out; }
  function implicitSolve(rhs, coef, diag) {
    var n = rhs.length, m = n - 2, a = fill(m, coef), b = fill(m, diag), c = fill(m, coef), d = [], j, x;
    for (j = 0; j < m; j++) d.push(rhs[j + 1]);
    x = tri(a, b, c, d);
    return [0.0].concat(x, [0.0]);
  }
  var CrPde = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 40.0, tend: 0.5, c: 0.1, r: 0.4, xp: 0.3 },
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), nx = Math.max(10, I(p.n)), dx = 1.0 / nx, dt0, n, dt, xs = grid(0.0, 1.0, nx), uu = [], j, blown = 0.0, stab, r, L, rhs, Lp, nu, n2, un, up, k, ce = [];
      dt0 = cas === 0 ? p.r * dx * dx / p.c : p.r * dx / p.c;
      n = Math.max(2, I(p.tend / dt0)); dt = p.tend / n;
      for (j = 0; j < xs.length; j++) uu.push(hat(xs[j]));
      if (cas === 0) {
        r = p.c * dt / (dx * dx); stab = r;
        for (k = 0; k < n; k++) {
          L = lap(uu);
          if (meth === 0) { un = []; for (j = 0; j <= nx; j++) un.push(uu[j] + r * L[j]); uu = un; }
          else { rhs = []; for (j = 0; j <= nx; j++) rhs.push(uu[j] + 0.5 * r * L[j]); uu = implicitSolve(rhs, -0.5 * r, 1.0 + r); }
          if (maxAbs(uu) > 1e9) { blown = 1.0; break; }
        }
      } else {
        nu = p.c * dt / dx; stab = nu; n2 = nu * nu;
        L = lap(uu);
        if (meth === 0) { un = []; for (j = 0; j <= nx; j++) un.push(uu[j] + 0.5 * n2 * L[j]); }
        else { rhs = []; for (j = 0; j <= nx; j++) rhs.push(uu[j] + 0.25 * n2 * L[j]); un = implicitSolve(rhs, -0.25 * n2, 1.0 + 0.5 * n2); }
        up = uu; uu = un;
        for (k = 0; k < n - 1; k++) {
          L = lap(uu); Lp = lap(up);
          if (meth === 0) { un = []; for (j = 0; j <= nx; j++) un.push(2.0 * uu[j] - up[j] + n2 * L[j]); }
          else { rhs = []; for (j = 0; j <= nx; j++) rhs.push(2.0 * uu[j] - up[j] + 0.25 * n2 * (2.0 * L[j] + Lp[j])); un = implicitSolve(rhs, -0.25 * n2, 1.0 + 0.5 * n2); }
          up = uu; uu = un;
          if (maxAbs(uu) > 1e9) { blown = 1.0; break; }
        }
      }
      var jp = I(p.xp * nx), val = uu[jp], exact = pdeExactAt(p, jp * dx);
      for (j = 0; j < xs.length; j++) ce.push(pdeExactAt(p, xs[j]));
      return base(val, exact, nx, xs, ce, uu.slice(), [jp * dx], [val], { stab: stab, steps: n, blown: blown });
    }
  });
  function pdeExact(p) { var nx = Math.max(10, I(p.n)); return pdeExactAt(p, I(p.xp * nx) / nx); }

  // ====================================================================================== finite elements
  function femF(cas, x) { return cas === 1 ? 1.0 : PI * PI * Math.sin(PI * x); }
  function femExactAt(cas, x) { return cas === 1 ? 0.5 * x * (1.0 - x) : Math.sin(PI * x); }
  var CrFem = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 8.0, xp: 0.4 },
    init: function (p) {
      var cas = I(p.cas), n = Math.max(2, I(p.n)), h = 1.0 / n, g = 0.5773502691896257, b = zeros(n - 1), e, x0, x1, xm, gi, x, f, w, gp, m = n - 1, a, d, c, uu, xs, xp, j, val, exact, cx, cy = [], ce = [], q, jj, i;
      for (e = 0; e < n; e++) {
        x0 = e * h; x1 = x0 + h; xm = 0.5 * (x0 + x1);
        for (gi = 0; gi < 2; gi++) {
          gp = gi === 0 ? -g : g;
          x = xm + gp * 0.5 * h; f = femF(cas, x); w = 0.5 * h;
          if (e - 1 >= 0 && e - 1 < n - 1) b[e - 1] += f * w * (x1 - x) / h;
          if (e < n - 1) b[e] += f * w * (x - x0) / h;
        }
      }
      a = fill(m, -1.0 / h); d = fill(m, 2.0 / h); c = fill(m, -1.0 / h);
      uu = [0.0].concat(tri(a, d, c, b), [0.0]);
      xs = grid(0.0, 1.0, n); xp = p.xp;
      j = Math.floor(xp / h); if (j > n - 1) j = n - 1;
      val = uu[j] + (uu[j + 1] - uu[j]) * (xp - xs[j]) / h;
      exact = femExactAt(cas, xp);
      cx = grid(0.0, 1.0, 100);
      for (i = 0; i < cx.length; i++) {
        q = cx[i]; jj = Math.floor(q / h); if (jj > n - 1) jj = n - 1;
        cy.push(uu[jj] + (uu[jj + 1] - uu[jj]) * (q - xs[jj]) / h);
        ce.push(femExactAt(cas, q));
      }
      return base(val, exact, n, cx, ce, cy, xs, uu);
    }
  });
  function femExact(p) { return femExactAt(I(p.cas), p.xp); }

  // ====================================================================================== least squares
  function fitDesign(cas, x) { return cas === 2 ? [1.0, x, x * x] : [1.0, x]; }
  function fitTruth(p) { return I(p.cas) === 2 ? p.c : p.a; }
  var CrFit = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 200.0, seed: 4242.0, a: 2.0, b: 1.0, c: -0.3, sig: 0.5, xmax: 10.0 },
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), n = Math.max(5, I(p.n)), st = lcg(p.seed), xs = [], ys = [], sg = [], i, x, s, y, m = cas === 2 ? 3 : 2, w = [], A = [], bv = zeros(m), r, q, row, beta, rss = 0.0, chi2 = 0.0, f, covd = [], e, scale, k, perr, val, cx, ce = [], cy = [], stride, px = [], py = [];
      for (i = 0; i < n; i++) {
        x = p.xmax * i / (n - 1);
        s = cas === 1 ? p.sig * (0.25 + 1.5 * x / p.xmax) : p.sig;
        y = p.b + p.a * x + (cas === 2 ? p.c * x * x : 0.0) + s * gauss(st);
        xs.push(x); ys.push(y); sg.push(s);
      }
      for (i = 0; i < n; i++) w.push(meth === 1 ? 1.0 / (sg[i] * sg[i]) : 1.0);
      for (r = 0; r < m; r++) A.push(zeros(m));
      for (i = 0; i < n; i++) {
        row = fitDesign(cas, xs[i]);
        for (r = 0; r < m; r++) { bv[r] += w[i] * row[r] * ys[i]; for (q = 0; q < m; q++) A[r][q] += w[i] * row[r] * row[q]; }
      }
      beta = solve(A, bv);
      for (i = 0; i < n; i++) {
        row = fitDesign(cas, xs[i]); f = 0.0;
        for (r = 0; r < m; r++) f += beta[r] * row[r];
        rss += (ys[i] - f) * (ys[i] - f);
        chi2 += (ys[i] - f) * (ys[i] - f) / (sg[i] * sg[i]);
      }
      for (r = 0; r < m; r++) { e = zeros(m); e[r] = 1.0; covd.push(solve(A, e)[r]); }
      scale = meth === 1 ? 1.0 : rss / Math.max(1, n - m);
      k = m - 1; perr = Math.sqrt(Math.max(covd[k] * scale, 0.0)); val = beta[k];
      cx = grid(0.0, p.xmax, 60);
      for (i = 0; i < cx.length; i++) {
        x = cx[i]; ce.push(p.b + p.a * x + (cas === 2 ? p.c * x * x : 0.0));
        row = fitDesign(cas, x); f = 0.0; for (r = 0; r < m; r++) f += beta[r] * row[r]; cy.push(f);
      }
      stride = Math.max(1, Math.floor((n + 119) / 120));
      for (i = 0; i < n; i += stride) { px.push(xs[i]); py.push(ys[i]); }
      return base(val, fitTruth(p), n, cx, ce, cy, px, py, { chi2r: chi2 / Math.max(1, n - m), perr: perr });
    }
  });
  function fitExact(p) { return fitTruth(p); }

  // ====================================================================================== maximum likelihood
  function goldenMax(f, a, b, iters) {
    var gr = 0.6180339887498949, c = b - gr * (b - a), d = a + gr * (b - a), fc = f(c), fd = f(d), i, t;
    for (i = 0; i < iters; i++) {
      if (fc > fd) { b = d; d = c; fd = fc; c = b - gr * (b - a); fc = f(c); }
      else { a = c; c = d; fc = fd; d = a + gr * (b - a); fd = f(d); }
    }
    return 0.5 * (a + b);
  }
  var CrMle = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 1000.0, seed: 777.0, lam: 4.0, sg: 2.0, mu: 10.0, tau: 2.2 },
    init: function (p) {
      var cas = I(p.cas), N = Math.max(10, I(p.n)), st = lcg(p.seed), NB = 20, est, truth, cx, ce, pf, obs, i, j, k, bw, lo, hi, S1, S2, lam, K, cnt, e0, uu, pk, cum, vals, mean, mu, sg, tau, chi2 = 0.0, nb = 0, dof, tot;
      function pmf(l) { var out = [], pk2 = Math.exp(-l), tot2 = 0.0, kk; for (kk = 0; kk < K; kk++) { out.push(pk2); tot2 += pk2; pk2 = pk2 * l / (kk + 1); } out.push(Math.max(1.0 - tot2, 0.0)); return out; }
      function cdf(q, m_, s_) { return 0.5 * (1.0 + erf((q - m_) / (s_ * Math.sqrt(2.0)))); }
      function binpG(m_, s_) { var out = [cdf(lo, m_, s_)], jj; for (jj = 0; jj < NB; jj++) out.push(cdf(lo + (jj + 1) * bw, m_, s_) - cdf(lo + jj * bw, m_, s_)); out.push(1.0 - cdf(hi, m_, s_)); return out; }
      function binpE(t_) { var out = [], jj; for (jj = 0; jj < NB; jj++) out.push(Math.exp(-jj * bw / t_) - Math.exp(-(jj + 1) * bw / t_)); out.push(Math.exp(-hi / t_)); return out; }
      function scaleN(a) { var o = [], q; for (q = 0; q < a.length; q++) o.push(N * a[q]); return o; }
      if (cas === 0) {
        lam = p.lam; K = I(lam + 4.0 * Math.sqrt(lam)) + 2; cnt = zeros(K + 1); S1 = 0.0; e0 = Math.exp(-lam);
        for (i = 0; i < N; i++) {
          uu = u(st); k = 0; pk = e0; cum = pk;
          while (uu > cum && k < 200) { k += 1; pk = pk * lam / k; cum += pk; }
          S1 += k; cnt[k < K ? k : K] += 1.0;
        }
        est = goldenMax(function (q) { return S1 * Math.log(q) - N * q; }, 1e-3, 4.0 * (S1 / N + 1.0), 80);
        truth = lam; cx = []; for (k = 0; k <= K; k++) cx.push(k);
        ce = scaleN(pmf(truth)); pf = scaleN(pmf(est)); obs = cnt;
      } else if (cas === 1) {
        mu = p.mu; sg = p.sg; vals = [];
        for (i = 0; i < N; i++) vals.push(mu + sg * gauss(st));
        mean = fsum(vals) / N; S2 = 0.0;
        for (i = 0; i < N; i++) S2 += (vals[i] - mean) * (vals[i] - mean);
        est = goldenMax(function (q) { return -N * Math.log(q) - S2 / (2.0 * q * q); }, 1e-3, 5.0 * Math.sqrt(S2 / N) + 1.0, 80);
        truth = sg; lo = mu - 4.0 * sg; hi = mu + 4.0 * sg; bw = (hi - lo) / NB; obs = zeros(NB + 2);
        for (i = 0; i < N; i++) { j = Math.floor((vals[i] - lo) / bw) + 1; obs[j < 0 ? 0 : (j > NB ? NB + 1 : j)] += 1.0; }
        cx = []; for (j = 0; j < NB + 2; j++) cx.push(lo + (j - 0.5) * bw);
        ce = scaleN(binpG(mu, truth)); pf = scaleN(binpG(mean, est));
      } else {
        tau = p.tau; S1 = 0.0; hi = 5.0 * tau; bw = hi / NB; obs = zeros(NB + 1); lo = 0.0;
        for (i = 0; i < N; i++) {
          uu = u(st); var xx = -tau * Math.log(uu > 1e-300 ? uu : 1e-300);
          S1 += xx; j = Math.floor(xx / bw); obs[j < NB ? j : NB] += 1.0;
        }
        est = goldenMax(function (q) { return -N * Math.log(q) - S1 / q; }, 1e-3, 4.0 * (S1 / N + 1.0), 80);
        truth = tau; cx = []; for (j = 0; j < NB + 1; j++) cx.push((j + 0.5) * bw);
        ce = scaleN(binpE(truth)); pf = scaleN(binpE(est));
      }
      for (j = 0; j < obs.length; j++) if (pf[j] > 5.0) { chi2 += (obs[j] - pf[j]) * (obs[j] - pf[j]) / pf[j]; nb += 1; }
      dof = Math.max(1, nb - 2);
      return base(est, truth, N, cx, ce, obs.slice(), cx, pf, { chi2r: chi2 / dof, dof: dof });
    }
  });
  function mleExact(p) { var cas = I(p.cas); return cas === 0 ? p.lam : (cas === 1 ? p.sg : p.tau); }

  // ====================================================================================== random deviates
  function normTable(m, lim) { var xs = grid(-lim, lim, m), tc = [], i; for (i = 0; i < xs.length; i++) tc.push(0.5 * (1.0 + erf(xs[i] / Math.sqrt(2.0)))); return [xs, tc]; }
  function binPmf() {
    var out = [], k, c, i;
    for (k = 0; k < 6; k++) { c = 1.0; for (i = 1; i <= k; i++) c = c * (5 - k + i) / i; out.push(c * Math.pow(0.3, k) * Math.pow(0.7, 5 - k)); }
    return out;
  }
  function devExact(p) {
    var cas = I(p.cas);
    if (cas === 1) return erf(p.xb / Math.sqrt(2.0));
    if (cas === 2) return binPmf()[I(p.kb)];
    return 1.0 - Math.exp(-p.lam * p.xb);
  }
  var CrDev = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 20000.0, seed: 31415.0, lam: 1.0, xb: 1.0, kb: 1.0 },
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), N = Math.max(100, I(p.n)), st = lcg(p.seed), lam = p.lam, NB = 20, trials = 0, i, k, c, q, pm, pmax, cum, obs, val, cx, ce, lo, hi, bw, inside = 0.0, tx, tc, tt, x, uu, a, b, mid, j, chi2 = 0.0, nb = 0;
      if (cas === 2) {
        pm = binPmf(); pmax = Math.max.apply(null, pm); cum = []; c = 0.0;
        for (q = 0; q < pm.length; q++) { c += pm[q]; cum.push(c); }
        obs = zeros(6);
        for (i = 0; i < N; i++) {
          if (meth === 0) { uu = u(st); trials += 1; k = 0; while (k < 5 && uu > cum[k]) k++; }
          else {
            while (true) { trials += 1; k = Math.floor(u(st) * 6.0); if (k > 5) k = 5; if (u(st) * pmax < pm[k]) break; }
          }
          obs[k] += 1.0;
        }
        cx = [0, 1, 2, 3, 4, 5]; ce = []; for (q = 0; q < 6; q++) ce.push(N * pm[q]);
        val = obs[I(p.kb)] / N;
      } else {
        if (cas === 1) { lo = -4.0; hi = 4.0; tt = normTable(4000, 8.0); tx = tt[0]; tc = tt[1]; }
        else { lo = 0.0; hi = 6.0 / lam; }
        bw = (hi - lo) / NB; obs = zeros(NB);
        for (i = 0; i < N; i++) {
          if (cas === 0) {
            if (meth === 0) { uu = u(st); trials += 1; x = -Math.log(uu > 1e-300 ? uu : 1e-300) / lam; }
            else { while (true) { trials += 1; x = u(st) * 10.0 / lam; if (u(st) < Math.exp(-lam * x)) break; } }
          } else if (meth === 0) {
            uu = u(st); trials += 1; a = 0; b = tx.length - 1;
            while (b - a > 1) { mid = Math.floor((a + b) / 2); if (tc[mid] <= uu) a = mid; else b = mid; }
            x = tx[a] + (tx[b] - tx[a]) * (uu - tc[a]) / (tc[b] - tc[a]);
          } else {
            while (true) { trials += 1; x = -6.0 + 12.0 * u(st); if (u(st) < Math.exp(-0.5 * x * x)) break; }
          }
          if ((cas === 1 && Math.abs(x) < p.xb) || (cas === 0 && x < p.xb)) inside += 1.0;
          j = Math.floor((x - lo) / bw);
          if (j >= 0 && j < NB) obs[j] += 1.0;
        }
        val = inside / N; cx = []; ce = [];
        for (j = 0; j < NB; j++) {
          cx.push(lo + (j + 0.5) * bw);
          if (cas === 1) ce.push(N * 0.5 * (erf((lo + (j + 1) * bw) / Math.sqrt(2.0)) - erf((lo + j * bw) / Math.sqrt(2.0))));
          else ce.push(N * (Math.exp(-lam * (lo + j * bw)) - Math.exp(-lam * (lo + (j + 1) * bw))));
        }
      }
      for (j = 0; j < obs.length; j++) if (ce[j] > 5.0) { chi2 += (obs[j] - ce[j]) * (obs[j] - ce[j]) / ce[j]; nb += 1; }
      return base(val, devExact(p), N, cx, ce, obs.slice(), [], [], { chi2r: chi2 / Math.max(1, nb - 1), eff: N / Math.max(trials, 1) });
    }
  });

  // ====================================================================================== random walk
  function retProb(d, N) {
    if (N % 2 === 1) return 0.0;
    var h = N / 2, fact = [1.0], i, tot = 0.0;
    for (i = 1; i <= N; i++) fact.push(fact[fact.length - 1] * i);
    function rec(k, left, acc) {
      var a;
      if (k === d - 1) { tot += acc / (fact[left] * fact[left]); return; }
      for (a = 0; a <= left; a++) rec(k + 1, left - a, acc / (fact[a] * fact[a]));
    }
    rec(0, h, fact[N]);
    return tot / Math.pow(2.0 * d, N);
  }
  function walkExact(p) {
    var N = Math.max(2, I(p.steps));
    if (I(p.cas) === 1) return retProb(Math.max(1, I(p.dim)), N);
    return N;
  }
  var CrWalk = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 4000.0, seed: 2718.0, dim: 2.0, steps: 16.0 },
    init: function (p) {
      var cas = I(p.cas), W = Math.max(10, I(p.n)), d = Math.max(1, I(p.dim)), N = Math.max(2, I(p.steps)), st = lcg(p.seed), r2m = zeros(N + 1), home = 0.0, path = [zeros(d)], w, m, pos, k, r2, q, ab, val, cx = [], ce = [], px = [], py = [], i;
      for (w = 0; w < W; w++) {
        pos = zeros(d);
        for (m = 1; m <= N; m++) {
          k = Math.floor(u(st) * 2 * d); if (k > 2 * d - 1) k = 2 * d - 1;
          pos[Math.floor(k / 2)] += (k % 2) === 0 ? 1 : -1;
          r2 = 0; for (q = 0; q < d; q++) r2 += pos[q] * pos[q];
          r2m[m] += r2;
          if (w === 0) path.push(pos.slice());
        }
        ab = 0; for (q = 0; q < d; q++) ab += Math.abs(pos[q]);
        if (ab === 0) home += 1.0;
      }
      for (m = 0; m <= N; m++) r2m[m] /= W;
      val = cas === 1 ? home / W : r2m[N];
      for (m = 0; m <= N; m++) { cx.push(m); ce.push(m); }
      if (d >= 2) { for (i = 0; i < path.length; i++) { px.push(path[i][0]); py.push(path[i][1]); } }
      else { for (i = 0; i < path.length; i++) { px.push(i); py.push(path[i][0]); } }
      return base(val, walkExact(p), W, cx, ce, r2m, px, py, { path_dim: Math.min(d, 2) });
    }
  });

  // ====================================================================================== decay chain
  function bateman(p, t) {
    var l1 = p.l1, l2 = p.l2, a = Math.exp(-l1 * t);
    if (Math.abs(l2 - l1) < 1e-12) return [a, l1 * t * a];
    return [a, l1 / (l2 - l1) * (a - Math.exp(-l2 * t))];
  }
  function decayExact(p) {
    var cas = I(p.cas), ab = bateman(p, p.tend);
    if (cas === 0) return ab[0];
    if (cas === 1) return ab[1];
    return ab[1] / ab[0];
  }
  var CrDecay = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 20000.0, seed: 1234.0, l1: 0.5, l2: 1.5, tend: 3.0 },
    init: function (p) {
      var cas = I(p.cas), N = Math.max(100, I(p.n)), st = lcg(p.seed), NT = 40, tend = p.tend, dtb = tend / NT, d1 = zeros(NT + 2), d2 = zeros(NT + 2), i, uu, t1, t2, j1, j2, cx = [], k, parents = [], daughters = [], c1 = 0.0, c2 = 0.0, ex = [], val, ce = [], cy = [];
      for (i = 0; i < N; i++) {
        uu = u(st); t1 = -Math.log(uu > 1e-300 ? uu : 1e-300) / p.l1;
        j1 = Math.floor(t1 / dtb); d1[j1 <= NT ? j1 : NT + 1] += 1.0;
        if (cas > 0) {
          uu = u(st); t2 = t1 - Math.log(uu > 1e-300 ? uu : 1e-300) / p.l2;
          j2 = Math.floor(t2 / dtb); d2[j2 <= NT ? j2 : NT + 1] += 1.0;
        }
      }
      for (k = 0; k <= NT; k++) cx.push(dtb * k);
      for (k = 0; k <= NT; k++) { parents.push((N - c1) / N); daughters.push((c1 - c2) / N); c1 += d1[k]; c2 += d2[k]; }
      for (k = 0; k <= NT; k++) ex.push(bateman(p, cx[k]));
      if (cas === 0) { val = parents[NT]; for (k = 0; k <= NT; k++) ce.push(ex[k][0]); cy = parents; }
      else if (cas === 1) { val = daughters[NT]; for (k = 0; k <= NT; k++) ce.push(ex[k][1]); cy = daughters; }
      else {
        val = parents[NT] > 0 ? daughters[NT] / parents[NT] : 0.0;
        for (k = 0; k <= NT; k++) { ce.push(ex[k][1] / ex[k][0]); cy.push(parents[k] > 0 ? daughters[k] / parents[k] : 0.0); }
      }
      return base(val, decayExact(p), N, cx, ce, cy, [cx[NT]], [val], { parent_frac: parents[NT], daughter_frac: daughters[NT] });
    }
  });

  // ====================================================================================== two-level spins
  function twoExactAt(cas, x) {
    if (cas === 1) { var ch = Math.cosh(x); return x * x / (ch * ch); }
    return Math.tanh(x);
  }
  function twoRun(cas, x, ns, sweeps, st) {
    var s = fill(ns, 1.0), burn = Math.floor(sweeps / 5) + 50, b, j, dE, sm = 0.0, se = 0.0, se2 = 0.0, tot, e, m, cnt, c;
    for (b = 0; b < burn; b++) for (j = 0; j < ns; j++) { dE = 2.0 * s[j] * x; if (dE <= 0.0 || u(st) < Math.exp(-dE)) s[j] = -s[j]; }
    for (b = 0; b < sweeps; b++) {
      for (j = 0; j < ns; j++) { dE = 2.0 * s[j] * x; if (dE <= 0.0 || u(st) < Math.exp(-dE)) s[j] = -s[j]; }
      tot = 0.0;
      for (j = 0; j < ns; j++) { tot += s[j]; e = -s[j] * x; se += e; se2 += e * e; }
      sm += tot / ns;
    }
    m = sm / sweeps; cnt = sweeps * ns; c = se2 / cnt - (se / cnt) * (se / cnt);
    return [cas === 1 ? c : m, s];
  }
  function twoExact(p) { return twoExactAt(I(p.cas), p.x); }
  var CrTwoLevel = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 4000.0, seed: 9001.0, x: 1.0, ns: 40.0 },
    init: function (p) {
      var cas = I(p.cas), ns = Math.max(4, I(p.ns)), sw = Math.max(100, I(p.n)), st = lcg(p.seed), r = twoRun(cas, p.x, ns, sw, st), xs = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0], px = [], py = [], i, v, cx, ce = [];
      for (i = 0; i < xs.length; i++) { v = twoRun(cas, xs[i], ns, Math.floor(sw / 6) + 20, st); px.push(xs[i]); py.push(v[0]); }
      cx = grid(0.0, 3.2, 64);
      for (i = 0; i < cx.length; i++) ce.push(twoExactAt(cas, cx[i]));
      return base(r[0], twoExactAt(cas, p.x), sw, cx, ce, [], px, py, { lat: r[1].slice(), lw: ns, lh: 1.0 });
    }
  });

  // ====================================================================================== Monte Carlo integration
  function mcintExact(p) { return I(p.cas) === 1 ? 0.5 * Math.sqrt(PI) * erf(1.0) : 2.0; }
  var CrMcInt = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 20000.0, seed: 24680.0 },
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), N = Math.max(10, I(p.n)), st = lcg(p.seed), marks = marksOf(N), mi = 0, run = [], hit = 0.0, tot = 0.0, sq = 0.0, a = 0.0, b, top = 1.0, area, c1 = 1.0 - Math.exp(-1.0), est = 0.0, i, x, y, f, g, uu, pdf, ph, se, mean, vr, cx = [], ex, ce = [];
      b = cas === 1 ? 1.0 : PI; area = (b - a) * top;
      for (i = 1; i <= N; i++) {
        if (meth === 0) {
          x = a + (b - a) * u(st); y = top * u(st);
          f = cas === 1 ? Math.exp(-x * x) : Math.sin(x);
          if (y <= f) hit += 1.0;
          est = area * hit / i;
        } else {
          if (meth === 1) { x = a + (b - a) * u(st); g = (b - a) * (cas === 1 ? Math.exp(-x * x) : Math.sin(x)); }
          else if (cas === 1) { x = -Math.log(1.0 - u(st) * c1); g = c1 * Math.exp(x - x * x); }
          else {
            uu = u(st);
            if (uu < 0.5) { x = PI * Math.sqrt(uu / 2.0); pdf = 4.0 * x / (PI * PI); }
            else { x = PI * (1.0 - Math.sqrt((1.0 - uu) / 2.0)); pdf = 4.0 * (PI - x) / (PI * PI); }
            g = pdf > 1e-300 ? Math.sin(x) / pdf : 0.0;
          }
          tot += g; sq += g * g; est = tot / i;
        }
        while (mi < marks.length && marks[mi] === i) { run.push(est); mi++; }
      }
      if (meth === 0) { ph = hit / N; se = area * Math.sqrt(Math.max(ph * (1.0 - ph), 0.0) / N); }
      else { mean = tot / N; vr = sq / N - mean * mean; se = Math.sqrt(Math.max(vr, 0.0) / N); }
      for (i = 0; i < marks.length; i++) cx.push(marks[i]);
      ex = mcintExact(p); for (i = 0; i < cx.length; i++) ce.push(ex);
      return base(est, ex, N, cx, ce, run, [cx[cx.length - 1]], [est], { se: se });
    }
  });

  // ====================================================================================== scattering
  function scatterExact(p) {
    var cas = I(p.cas), w = I(p.what), b0;
    if (cas === 0) return w === 0 ? PI * p.a * p.a : 0.5;
    b0 = 0.5 * p.a / Math.tan(0.5 * p.thmin);
    return PI * b0 * b0;
  }
  var CrScatter = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 50000.0, seed: 8128.0, a: 1.0, R: 1.5, thmin: 1.0471975511965976, what: 0.0 },
    init: function (p) {
      var cas = I(p.cas), w = I(p.what), N = Math.max(100, I(p.n)), st = lcg(p.seed), a = p.a, R = p.R, NB = 20, obs = zeros(NB), cmin = Math.cos(p.thmin), nhit = 0.0, nback = 0.0, ncut = 0.0, i, b2, c, q, j, val, cx = [], ce = [], lo, hi, fF;
      for (i = 0; i < N; i++) {
        b2 = R * R * u(st);
        if (cas === 0) {
          if (b2 < a * a) { nhit += 1.0; c = 2.0 * b2 / (a * a) - 1.0; } else continue;
        } else {
          q = 0.25 * a * a; c = (b2 - q) / (b2 + q); nhit += 1.0;
          if (c < cmin) ncut += 1.0;
        }
        if (c < 0.0) nback += 1.0;
        j = Math.floor((c + 1.0) * 0.5 * NB);
        obs[j < NB ? j : NB - 1] += 1.0;
      }
      if (cas === 0) val = w === 0 ? PI * R * R * nhit / N : nback / Math.max(nhit, 1.0);
      else val = PI * R * R * ncut / N;
      q = 0.25 * a * a;
      fF = function (cc) { return cc < 1.0 ? Math.min(1.0, q * (1.0 + cc) / (1.0 - cc + 1e-300) / (R * R)) : 1.0; };
      for (j = 0; j < NB; j++) {
        cx.push(-1.0 + (j + 0.5) * 2.0 / NB);
        lo = -1.0 + j * 2.0 / NB; hi = lo + 2.0 / NB;
        if (cas === 0) ce.push(N * (a * a / (R * R)) / NB);
        else ce.push(N * (fF(hi) - fF(lo)));
      }
      return base(val, scatterExact(p), N, cx, ce, obs.slice(), [], [], { nhit: nhit });
    }
  });

  // ====================================================================================== polynomial roots
  function horner(co, x) { var r = 0.0, k; for (k = co.length - 1; k >= 0; k--) r = r * x + co[k]; return r; }
  function dhorner(co, x) { var r = 0.0, k; for (k = co.length - 1; k >= 1; k--) r = r * x + k * co[k]; return r; }
  function polyCo(cas) { if (cas === 1) return [-5.0, -2.0, 0.0, 1.0]; if (cas === 2) return [2.0, -3.0, 0.0, 1.0]; return [-6.0, 11.0, -6.0, 1.0]; }
  function polyRoot(cas) {
    if (cas === 1) { var D = Math.sqrt(6.25 - 8.0 / 27.0); return Math.pow(2.5 + D, 1.0 / 3.0) + Math.pow(2.5 - D, 1.0 / 3.0); }
    if (cas === 2) return 1.0;
    return 3.0;
  }
  var CrPoly = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 8.0, xa: 2.5, xb: 3.5, x0: 3.4, x1: 3.3, gx0: 0.5, gx1: 3.6 },
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), n = Math.max(1, I(p.n)), co = polyCo(cas), f = function (q) { return horner(co, q); }, it = [], k, a, b, fa, mid, fm, mult, x, d, x0, x1, f0, f1, x2, val, cx, ce = [], py = [];
      if (cas !== 2 && meth === 0) {
        a = p.xa; b = p.xb; fa = f(a);
        for (k = 0; k < n; k++) {
          mid = 0.5 * (a + b); fm = f(mid); it.push(mid);
          if ((fm < 0) === (fa < 0)) { a = mid; fa = fm; } else b = mid;
        }
      } else if ((cas !== 2 && meth === 1) || (cas === 2 && meth <= 1)) {
        mult = (cas === 2 && meth === 1) ? 2.0 : 1.0; x = p.x0;
        for (k = 0; k < n; k++) { d = dhorner(co, x); if (Math.abs(d) < 1e-14) break; x = x - mult * f(x) / d; it.push(x); }
      } else {
        x0 = p.x0; x1 = p.x1; f0 = f(x0); f1 = f(x1);
        for (k = 0; k < n; k++) {
          if (Math.abs(f1 - f0) < 1e-14) break;
          x2 = x1 - f1 * (x1 - x0) / (f1 - f0);
          x0 = x1; f0 = f1; x1 = x2; f1 = f(x2); it.push(x1);
        }
      }
      val = it.length ? it[it.length - 1] : p.x0;
      cx = grid(p.gx0, p.gx1, 80);
      for (k = 0; k < cx.length; k++) ce.push(f(cx[k]));
      for (k = 0; k < it.length; k++) py.push(f(it[k]));
      return base(val, polyRoot(cas), it.length, cx, ce, [], it.slice(), py);
    }
  });
  function polyExact(p) { return polyRoot(I(p.cas)); }

  // ====================================================================================== photons in a slab
  function photonExact(p) {
    var cas = I(p.cas), mut = p.mus + p.mua, e = Math.exp(-mut * p.d);
    if (cas === 0) return e;
    if (cas === 1) return p.mus / mut;
    return (1.0 / mut - (p.d + 1.0 / mut) * e) / (1.0 - e);
  }
  var CrPhoton = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 20000.0, seed: 5551.0, d: 2.0, mus: 0.6, mua: 0.15 },
    init: function (p) {
      var cas = I(p.cas), N = Math.max(100, I(p.n)), st = lcg(p.seed), d = p.d, mut = p.mus + p.mua, pabs = p.mua / mut, NB = 20, first = zeros(NB), dose = zeros(NB), prim = 0.0, ninter = 0.0, nscat1 = 0.0, zsum = 0.0, T = 0.0, Rf = 0.0, Af = 0.0, i, z, uz, nsc, firstev, s_, uu, s, j, val, bw, cx = [], ce = [];
      for (i = 0; i < N; i++) {
        z = 0.0; uz = 1.0; nsc = 0; firstev = true;
        for (s_ = 0; s_ < 10000; s_++) {
          uu = u(st); s = -Math.log(uu > 1e-300 ? uu : 1e-300) / mut; z = z + uz * s;
          if (z < 0.0) { Rf += 1.0; break; }
          if (z > d) { T += 1.0; if (nsc === 0) prim += 1.0; break; }
          j = Math.floor(z / d * NB);
          if (firstev) { firstev = false; first[j < NB ? j : NB - 1] += 1.0; ninter += 1.0; zsum += z; }
          if (u(st) < pabs) { Af += 1.0; dose[j < NB ? j : NB - 1] += 1.0; break; }
          if (nsc === 0) nscat1 += 1.0;
          nsc += 1; uz = 2.0 * u(st) - 1.0;
        }
      }
      if (cas === 0) val = prim / N; else if (cas === 1) val = nscat1 / Math.max(ninter, 1.0); else val = zsum / Math.max(ninter, 1.0);
      bw = d / NB;
      for (j = 0; j < NB; j++) { cx.push((j + 0.5) * bw); ce.push(N * (Math.exp(-mut * j * bw) - Math.exp(-mut * (j + 1) * bw))); }
      return base(val, photonExact(p), N, cx, ce, first.slice(), [], [], { cy2: dose.slice(), Tf: T / N, Rf: Rf / N, Af: Af / N, prim: prim / N });
    }
  });

  // ====================================================================================== Ising model
  var TC2 = 2.0 / Math.log(1.0 + Math.sqrt(2.0));
  function ellipk(k) {
    var a = 1.0, b = Math.sqrt(Math.max(1.0 - k * k, 0.0)), i, t;
    for (i = 0; i < 40; i++) { t = a; a = 0.5 * (a + b); b = Math.sqrt(t * b); if (Math.abs(a - b) < 1e-15) break; }
    return PI / (2.0 * a);
  }
  function isingE1(T, L) { var t = Math.tanh(1.0 / T); return -(t + Math.pow(t, L - 1)) / (1.0 + Math.pow(t, L)); }
  function isingE2(T) {
    var K = 1.0 / T, s2 = Math.sinh(2.0 * K), c2 = Math.cosh(2.0 * K), k = 2.0 * s2 / (c2 * c2), th = s2 / c2;
    return -(c2 / s2) * (1.0 + (2.0 / PI) * (2.0 * th * th - 1.0) * ellipk(k));
  }
  function isingM2(T) { var s2 = Math.sinh(2.0 / T); if (s2 <= 1.0) return 0.0; return Math.pow(1.0 - Math.pow(s2, -4.0), 0.125); }
  function isingC(ef, T) { var h = 1e-5; return (ef(T + h) - ef(T - h)) / (2.0 * h); }
  function isingExact(p) {
    var d = I(p.dim), w = I(p.what), T = p.T, L = Math.max(4, I(p.L));
    if (d === 1) {
      if (w === 1) return isingE1(T, L);
      if (w === 2) return isingC(function (q) { return isingE1(q, L); }, T);
      return 0.0;
    }
    if (w === 0) return isingM2(T);
    if (w === 1) return isingE2(T);
    return isingC(isingE2, T);
  }
  function isingSim(d, L, T, meth, sweeps, st, marks, what) {
    var N = d === 1 ? L : L * L, nbr = [], i, x, y, s = fill(N, 1), padd = 1.0 - Math.exp(-2.0 / T), burn = Math.floor(sweeps / 5) + 30, ncl = [1], b, k, j, mi = 0, run = [], am = 0.0, m2 = 0.0, m4 = 0.0, se = 0.0, se2 = 0.0, M, m, bond, e, est, mean, n, e1, flips, cnt, done, sz, q;
    for (i = 0; i < N; i++) {
      if (d === 1) nbr.push([(i + 1) % L, (i - 1 + L) % L]);
      else { x = i % L; y = Math.floor(i / L); nbr.push([y * L + (x + 1) % L, y * L + (x - 1 + L) % L, ((y + 1) % L) * L + x, ((y - 1 + L) % L) * L + x]); }
    }
    function cluster() {
      var seed = Math.floor(u(st) * N), sp, stack, size, ii, jj, nb2, a;
      if (seed > N - 1) seed = N - 1;
      sp = s[seed]; s[seed] = -sp; stack = [seed]; size = 1;
      while (stack.length) {
        ii = stack.pop(); nb2 = nbr[ii];
        for (a = 0; a < nb2.length; a++) {
          jj = nb2[a];
          if (s[jj] === sp && u(st) < padd) { s[jj] = -sp; stack.push(jj); size += 1; }
        }
      }
      return size;
    }
    function sweep() {
      var t, ii, tot, a, dE;
      if (meth === 0) {
        for (t = 0; t < N; t++) {
          ii = Math.floor(u(st) * N); if (ii > N - 1) ii = N - 1;
          tot = 0; for (a = 0; a < nbr[ii].length; a++) tot += s[nbr[ii][a]];
          dE = 2 * s[ii] * tot;
          if (dE <= 0 || u(st) < Math.exp(-dE / T)) s[ii] = -s[ii];
        }
      } else for (t = 0; t < ncl[0]; t++) cluster();
    }
    if (meth === 1) {
      flips = 0; cnt = 0;
      for (b = 0; b < burn; b++) { done = 0; while (done < N) { sz = cluster(); done += sz; flips += sz; cnt += 1; } }
      ncl[0] = Math.max(1, I(N * cnt / Math.max(flips, 1)));
    } else for (b = 0; b < burn; b++) sweep();
    for (k = 1; k <= sweeps; k++) {
      sweep();
      M = 0; for (j = 0; j < N; j++) M += s[j];
      m = M / N; bond = 0;
      for (i = 0; i < N; i++) bond += s[i] * (d === 1 ? s[nbr[i][0]] : s[nbr[i][0]] + s[nbr[i][2]]);
      e = -bond / N;
      am += Math.abs(m); m2 += m * m; m4 += m * m * m * m; se += e; se2 += e * e;
      if (marks) {
        if (what === 0) est = am / k;
        else if (what === 1) est = se / k;
        else { mean = se / k; est = N * (se2 / k - mean * mean) / (T * T); }
        while (mi < marks.length && marks[mi] === k) { run.push(est); mi++; }
      }
    }
    n = sweeps; e1 = se / n;
    return { am: am / n, m2: m2 / n, m4: m4 / n, e: e1, C: N * (se2 / n - e1 * e1) / (T * T), lat: s.slice(), run: run, N: N };
  }
  var CrIsing = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 1000.0, seed: 60221.0, dim: 2.0, L: 16.0, T: 1.8, what: 0.0 },
    init: function (p) {
      var d = I(p.dim), L = Math.max(4, I(p.L)), n = Math.max(20, I(p.n)), w = I(p.what), st = lcg(p.seed), marks = marksOf(n), r = isingSim(d, L, p.T, I(p.method), n, st, marks, w), val = w === 0 ? r.am : (w === 1 ? r.e : r.C), ex = isingExact(p), cx = [], ce = [], i;
      for (i = 0; i < marks.length; i++) { cx.push(marks[i]); ce.push(ex); }
      return base(val, ex, n, cx, ce, r.run, [cx[cx.length - 1]], [val], { lat: r.lat, lw: L, lh: d === 1 ? 1 : L, m2: r.m2, m4: r.m4, am: r.am, en: r.e, cv: r.C });
    }
  });
  var CrBinder = kernel({
    PARAMS: { cas: 0.0, method: 1.0, n: 600.0, seed: 1066.0, L1: 8.0, L2: 16.0, Tlo: 2.1, Thi: 2.45, nT: 6.0 },
    init: function (p) {
      var n = Math.max(20, I(p.n)), nT = Math.max(3, I(p.nT)), meth = I(p.method), st = lcg(p.seed), Ts = grid(p.Tlo, p.Thi, nT - 1), U1 = [], U2 = [], lat = [], lw = 0, k, a, Ls, L, r, val, found = 0.0, d0, d1, ce = [];
      for (k = 0; k < nT; k++) {
        Ls = [I(p.L1), I(p.L2)];
        for (a = 0; a < 2; a++) {
          L = Ls[a]; r = isingSim(2, L, Ts[k], meth, n, st);
          (a === 0 ? U1 : U2).push(r.m2 > 0 ? 1.0 - r.m4 / (3.0 * r.m2 * r.m2) : 0.0);
          lat = r.lat; lw = L;
        }
      }
      val = Ts[Math.floor(nT / 2)];
      for (k = 0; k < nT - 1; k++) {
        d0 = U2[k] - U1[k]; d1 = U2[k + 1] - U1[k + 1];
        if (d0 > 0.0 && d1 <= 0.0) { val = Ts[k] + (Ts[k + 1] - Ts[k]) * d0 / (d0 - d1); found = 1.0; break; }
      }
      if (found === 0.0) val = U2[0] - U1[0] <= 0.0 ? Ts[0] : Ts[nT - 1];
      return base(val, TC2, n, Ts, ce, U1, [val], [0.0], { cy2: U2, lat: lat, lw: lw, lh: lw, vline: TC2, found: found });
    }
  });
  function binderExact() { return TC2; }

  // ====================================================================================== tight binding
  function jacobiEig(a0) {
    var n = a0.length, a = [], i, j, p, q, k, sw, off, apq, theta, t, c, s, akp, akq, apk, aqk, out = [];
    for (i = 0; i < n; i++) a.push(a0[i].slice());
    for (sw = 0; sw < 60; sw++) {
      off = 0.0;
      for (i = 0; i < n; i++) for (j = i + 1; j < n; j++) off += a[i][j] * a[i][j];
      if (off < 1e-26) break;
      for (p = 0; p < n - 1; p++) for (q = p + 1; q < n; q++) {
        apq = a[p][q];
        if (Math.abs(apq) < 1e-14) continue;
        theta = (a[q][q] - a[p][p]) / (2.0 * apq);
        t = (theta >= 0.0 ? 1.0 : -1.0) / (Math.abs(theta) + Math.sqrt(theta * theta + 1.0));
        c = 1.0 / Math.sqrt(t * t + 1.0); s = t * c;
        for (k = 0; k < n; k++) { akp = a[k][p]; akq = a[k][q]; a[k][p] = c * akp - s * akq; a[k][q] = s * akp + c * akq; }
        for (k = 0; k < n; k++) { apk = a[p][k]; aqk = a[q][k]; a[p][k] = c * apk - s * aqk; a[q][k] = s * apk + c * aqk; }
      }
    }
    for (i = 0; i < n; i++) out.push(a[i][i]);
    out.sort(function (x, y) { return x - y; });
    return out;
  }
  function zmat(N) { var H = [], i; for (i = 0; i < N; i++) H.push(zeros(N)); return H; }
  function tbRing(N, t) { var H = zmat(N), i; for (i = 0; i < N; i++) { H[i][(i + 1) % N] -= t; H[(i + 1) % N][i] -= t; } return H; }
  function tbTorus(L, t) {
    var N = L * L, H = zmat(N), x, y, i, a, j, js;
    for (y = 0; y < L; y++) for (x = 0; x < L; x++) {
      i = y * L + x; js = [y * L + (x + 1) % L, ((y + 1) % L) * L + x];
      for (a = 0; a < 2; a++) { j = js[a]; H[i][j] -= t; H[j][i] -= t; }
    }
    return H;
  }
  function grFk(kx, ky) { return [1.0 + Math.cos(kx) + Math.cos(ky), Math.sin(kx) + Math.sin(ky)]; }
  function grBands(kx, ky, t) {
    var f = grFk(kx, ky), re = f[0], im = f[1], H = [[0.0, 0.0, -t * re, t * im], [0.0, 0.0, -t * im, -t * re], [-t * re, -t * im, 0.0, 0.0], [t * im, -t * re, 0.0, 0.0]], ev = jacobiEig(H);
    return [ev[0], ev[3]];
  }
  function sqDosBin(t, lo, hi) {
    var tot = 0.0, m = 40, q, e, x;
    for (q = 0; q < m; q++) {
      e = lo + (hi - lo) * (q + 0.5) / m; x = Math.abs(e) / (4.0 * t);
      if (x >= 1.0) continue;
      tot += ellipk(Math.sqrt(1.0 - x * x)) / (2.0 * PI * PI * t) * (hi - lo) / m;
    }
    return tot;
  }
  function tbExact(p) {
    var cas = I(p.cas), w = I(p.what), t = p.t;
    if (w === 1) return cas === 0 ? -4.0 * t / PI : -16.0 * t / (PI * PI);
    return [4.0, 8.0, 6.0][cas] * t;
  }
  var CrTb = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 16.0, t: 1.0, what: 0.0 },
    init: function (p) {
      var cas = I(p.cas), w = I(p.what), t = p.t, n = Math.max(4, I(p.n)), NBIN = 24, ev, N, a, b, bb, val, s, k, Emax, bw, cnt, j, cx = [], cy = [], ce = [], lo, hi, NK = 60, bk = [], e1 = [], e2 = [], n1 = [], n2 = [], i, uu, kx, ky, f, re, im, r, ff;
      if (cas === 0) { ev = jacobiEig(tbRing(n, t)); N = n; }
      else if (cas === 1) { ev = jacobiEig(tbTorus(n, t)); N = n * n; }
      else {
        ev = [];
        for (a = 0; a < n; a++) for (b = 0; b < n; b++) { bb = grBands(2 * PI * a / n, 2 * PI * b / n, t); ev.push(bb[0]); ev.push(bb[1]); }
        ev.sort(function (x, y) { return x - y; }); N = 2 * n * n;
      }
      if (w === 1) { s = 0.0; for (k = 0; k < Math.floor(N / 2); k++) s += 2.0 * ev[k]; val = s / N; }
      else val = ev[ev.length - 1] - ev[0];
      Emax = [2.0, 4.0, 3.0][cas] * t; bw = 2.0 * Emax / NBIN; cnt = zeros(NBIN);
      for (i = 0; i < ev.length; i++) { j = Math.floor((ev[i] + Emax) / bw); cnt[j < 0 ? 0 : (j >= NBIN ? NBIN - 1 : j)] += 1.0; }
      for (j = 0; j < NBIN; j++) { cx.push(-Emax + (j + 0.5) * bw); cy.push(cnt[j] / (ev.length * bw)); }
      if (cas === 0) {
        for (j = 0; j < NBIN; j++) {
          lo = Math.max(-1.0, Math.min(1.0, (-Emax + j * bw) / (2.0 * t)));
          hi = Math.max(-1.0, Math.min(1.0, (-Emax + (j + 1) * bw) / (2.0 * t)));
          ce.push((Math.asin(hi) - Math.asin(lo)) / PI / bw);
        }
      } else if (cas === 1) for (j = 0; j < NBIN; j++) ce.push(sqDosBin(t, -Emax + j * bw, -Emax + (j + 1) * bw) / bw);
      for (i = 0; i <= NK; i++) bk.push(i / NK);
      for (i = 0; i <= NK; i++) {
        uu = bk[i];
        if (cas === 0) {
          kx = -PI + 2.0 * PI * uu; e1.push(-2.0 * t * Math.cos(kx)); n1.push(jacobiEig([[-2.0 * t * Math.cos(kx)]])[0]);
        } else if (cas === 1) {
          if (uu < 1.0 / 3.0) { kx = PI * 3.0 * uu; ky = 0.0; }
          else if (uu < 2.0 / 3.0) { kx = PI; ky = PI * (3.0 * uu - 1.0); }
          else { kx = PI * (3.0 - 3.0 * uu); ky = kx; }
          e1.push(-2.0 * t * (Math.cos(kx) + Math.cos(ky))); n1.push(jacobiEig([[-2.0 * t * (Math.cos(kx) + Math.cos(ky))]])[0]);
        } else {
          if (uu < 1.0 / 3.0) { kx = PI * 3.0 * uu; ky = 0.0; }
          else if (uu < 2.0 / 3.0) { kx = PI + (2.0 * PI / 3.0 - PI) * (3.0 * uu - 1.0); ky = (2.0 * PI / 3.0) * (3.0 * uu - 1.0); }
          else { ff = 3.0 - 3.0 * uu; kx = 2.0 * PI / 3.0 * ff; ky = 2.0 * PI / 3.0 * ff; }
          f = grFk(kx, ky); re = f[0]; im = f[1]; r = Math.sqrt(re * re + im * im);
          e1.push(t * r); e2.push(-t * r); bb = grBands(kx, ky, t); n1.push(bb[1]); n2.push(bb[0]);
        }
      }
      return base(val, tbExact(p), n, cx, ce, cy, [], [], { bk: bk, be1: e1, be2: e2, bn1: n1, bn2: n2, nlevels: ev.length });
    }
  });

  // ====================================================================================== Schrodinger equation
  function fft(re, im, inv) {
    var n = re.length, j = 0, i, bit, t, ln, ang, wr, wi, k, cr, ci, a, b, tr, ti, nc;
    for (i = 1; i < n; i++) {
      bit = n >> 1;
      while (j & bit) { j ^= bit; bit >>= 1; }
      j ^= bit;
      if (i < j) { t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
    }
    ln = 2;
    while (ln <= n) {
      ang = 2.0 * PI / ln * (inv ? 1.0 : -1.0); wr = Math.cos(ang); wi = Math.sin(ang);
      for (i = 0; i < n; i += ln) {
        cr = 1.0; ci = 0.0;
        for (k = 0; k < ln / 2; k++) {
          a = i + k; b = a + ln / 2;
          tr = re[b] * cr - im[b] * ci; ti = re[b] * ci + im[b] * cr;
          re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
          nc = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = nc;
        }
      }
      ln <<= 1;
    }
  }
  function numerovNodes(kfun, h, n, u1) {
    var uu = zeros(n + 1), h2 = h * h / 12.0, km = kfun(0), kc = kfun(1), nodes = 0, i, kp;
    uu[1] = u1;
    for (i = 1; i < n; i++) {
      kp = kfun(i + 1);
      uu[i + 1] = (2.0 * (1.0 - 5.0 * h2 * kc) * uu[i] - (1.0 + h2 * km) * uu[i - 1]) / (1.0 + h2 * kp);
      if (uu[i + 1] * uu[i] < 0.0) nodes += 1;
      km = kc; kc = kp;
    }
    return [nodes, uu];
  }
  function schroExact(p) {
    var cas = I(p.cas), lev = I(p.lev), nn;
    if (cas === 1) return (lev + 1) * (lev + 1) * PI * PI / 2.0;
    if (cas === 2) { nn = lev + I(p.ell) + 1; return -1.0 / (2.0 * nn * nn); }
    return lev + 0.5;
  }
  function schroShoot(cas, lev, ell, n) {
    var xm = 8.0, h, lo, hi, kf, u1, it, mid, nodes, E, res, xs = [], i, rm, L2;
    if (cas === 0) {
      h = 2.0 * xm / n; lo = 0.0; hi = lev + 3.0;
      kf = function (E_) { return function (i_) { return 2.0 * (E_ - 0.5 * (-xm + i_ * h) * (-xm + i_ * h)); }; };
      u1 = 1e-6;
    } else if (cas === 1) {
      h = 1.0 / n; lo = 0.0; hi = (lev + 2) * (lev + 2) * PI * PI / 2.0;
      kf = function (E_) { return function () { return 2.0 * E_; }; };
      u1 = h;
    } else {
      rm = 40.0 + 6.0 * lev; h = rm / n; L2 = ell * (ell + 1);
      lo = -0.6; hi = -0.5 / ((lev + ell + 3) * (lev + ell + 3));
      kf = function (E_) { return function (i_) { var r = i_ * h; if (i_ === 0) return 0.0; return 2.0 * (E_ + 1.0 / r) - L2 / (r * r); }; };
      u1 = Math.pow(h, ell + 1);
    }
    for (it = 0; it < 60; it++) {
      mid = 0.5 * (lo + hi); res = numerovNodes(kf(mid), h, n, u1);
      if (res[0] > lev) hi = mid; else lo = mid;
    }
    E = 0.5 * (lo + hi); res = numerovNodes(kf(E), h, n, u1);
    for (i = 0; i <= n; i++) xs.push(cas === 0 ? -xm + i * h : i * h);
    return [E, xs, res[1]];
  }
  function schroSplit(lev, n, dtau) {
    var Ng = 64, Lh = 7.0, dx = 2.0 * Lh / Ng, xs = [], V = [], ks = [], eV = [], eT = [], found = [], E = 0.0, psi = [], i, kk, ll, re, im, it, f, ov, nrm, r2, i2, T, tot, w, Vv, q;
    for (i = 0; i < Ng; i++) xs.push(-Lh + i * dx);
    for (i = 0; i < Ng; i++) V.push(0.5 * xs[i] * xs[i]);
    for (i = 0; i < Ng; i++) { kk = i < Ng / 2 ? i : i - Ng; ks.push(2.0 * PI * kk / (Ng * dx)); }
    for (i = 0; i < Ng; i++) { eV.push(Math.exp(-0.5 * dtau * V[i])); eT.push(Math.exp(-0.5 * dtau * ks[i] * ks[i])); }
    for (ll = 0; ll <= lev; ll++) {
      re = []; im = zeros(Ng);
      for (i = 0; i < Ng; i++) { q = xs[i]; re.push(Math.exp(-0.5 * q * q * 0.3) * (1.0 + 0.3 * q * (ll + 1) + 0.1 * q * q * q * (ll % 2))); }
      for (it = 0; it < n; it++) {
        for (i = 0; i < Ng; i++) { re[i] = re[i] * eV[i]; im[i] = im[i] * eV[i]; }
        fft(re, im, false);
        for (i = 0; i < Ng; i++) { re[i] = re[i] * eT[i]; im[i] = im[i] * eT[i]; }
        fft(re, im, true);
        for (i = 0; i < Ng; i++) { re[i] = re[i] / Ng * eV[i]; im[i] = im[i] / Ng * eV[i]; }
        for (f = 0; f < found.length; f++) {
          ov = 0.0; for (i = 0; i < Ng; i++) ov += found[f][i] * re[i] * dx;
          for (i = 0; i < Ng; i++) re[i] = re[i] - ov * found[f][i];
        }
        nrm = 0.0; for (i = 0; i < Ng; i++) nrm += re[i] * re[i] * dx;
        nrm = Math.sqrt(nrm);
        for (i = 0; i < Ng; i++) re[i] = re[i] / nrm;
      }
      r2 = re.slice(); i2 = zeros(Ng); fft(r2, i2, false);
      T = 0.0; tot = 0.0;
      for (i = 0; i < Ng; i++) { w = r2[i] * r2[i] + i2[i] * i2[i]; T += 0.5 * ks[i] * ks[i] * w; tot += w; }
      T /= tot; Vv = 0.0;
      for (i = 0; i < Ng; i++) Vv += V[i] * re[i] * re[i] * dx;
      E = T + Vv; found.push(re); psi = re;
    }
    return [E, xs, psi, V];
  }
  var CrSchro = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 400.0, lev: 0.0, ell: 0.0 },
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), lev = I(p.lev), ell = I(p.ell), n = Math.max(8, I(p.n)), ex = schroExact(p), E, xs, psi, V, ce = [], cy = [], cx, r, hh, nrm, i, q, uu;
      if (cas === 0 && meth === 1) {
        r = schroSplit(lev, n, 0.04); E = r[0]; xs = r[1]; psi = r[2]; V = r[3];
        for (i = 0; i < psi.length; i++) cy.push(E + 0.6 * psi[i]);
        ce = V; cx = xs;
      } else {
        r = schroShoot(cas, lev, ell, n); E = r[0]; xs = r[1]; uu = r[2]; hh = xs[1] - xs[0]; nrm = 0.0;
        for (i = 0; i < uu.length; i++) nrm += uu[i] * uu[i] * hh;
        nrm = Math.sqrt(nrm);
        for (i = 0; i < uu.length; i++) uu[i] = uu[i] / nrm;
        for (i = 0; i < xs.length; i++) {
          q = xs[i];
          if (cas === 0) { ce.push(0.5 * q * q); cy.push(E + 0.6 * uu[i]); }
          else if (cas === 1) { ce.push(0.0); cy.push(E + 0.5 * ex / 3.0 * uu[i] / 1.5); }
          else { ce.push(q > 0.2 ? (-1.0 / q + ell * (ell + 1) / (2.0 * q * q)) : 0.0); cy.push(E + 0.25 * uu[i]); }
        }
        cx = xs;
      }
      return base(E, ex, n, cx, ce, cy, [cx[0], cx[cx.length - 1]], [E, E], { hl1: E, hl2: ex });
    }
  });

  // ====================================================================================== N-body
  function keplerAcc(x, y) { var r2 = x * x + y * y, r3 = r2 * Math.sqrt(r2); return [-x / r3, -y / r3]; }
  function clusterAcc(pos, m, eps2) {
    var n = pos.length, acc = [], virial = 0.0, i, j, dx, dy, dz, r2, inv, fx, fy, fz;
    for (i = 0; i < n; i++) acc.push([0.0, 0.0, 0.0]);
    for (i = 0; i < n; i++) for (j = i + 1; j < n; j++) {
      dx = pos[j][0] - pos[i][0]; dy = pos[j][1] - pos[i][1]; dz = pos[j][2] - pos[i][2];
      r2 = dx * dx + dy * dy + dz * dz + eps2; inv = 1.0 / (r2 * Math.sqrt(r2));
      fx = m * dx * inv; fy = m * dy * inv; fz = m * dz * inv;
      acc[i][0] += fx; acc[i][1] += fy; acc[i][2] += fz; acc[j][0] -= fx; acc[j][1] -= fy; acc[j][2] -= fz;
      virial -= m * m * (dx * dx + dy * dy + dz * dz) * inv;
    }
    return [acc, virial];
  }
  function nbodyExact(p) { return I(p.cas) === 1 ? 1.0 : 2.0 * PI; }
  function keplerRun(p) {
    var meth = I(p.method), n = Math.max(8, I(p.n)), e = p.ecc, T = 2.0 * PI, dt = T / n, x = 1.0 - e, y = 0.0, vx = 0.0, vy = Math.sqrt((1.0 + e) / (1.0 - e)),
      E0 = 0.5 * (vx * vx + vy * vy) - 1.0 / Math.sqrt(x * x + y * y), ts = [0.0], Es = [0.0], trail = [x, y], t = 0.0, tc = 0.0, prevVr = 0.0, prevT = 0.0, seenNeg = false, k, a, r, vr, En, s0, k1, k2, k3, k4, i, s1;
    function f(s) { var aa = keplerAcc(s[0], s[1]); return [s[2], s[3], aa[0], aa[1]]; }
    function adv(s, k_, h) { var o = [], q; for (q = 0; q < 4; q++) o.push(s[q] + h * k_[q]); return o; }
    for (k = 0; k < 4 * n; k++) {
      if (meth === 0) { a = keplerAcc(x, y); vx = vx + dt * a[0]; vy = vy + dt * a[1]; x = x + dt * vx; y = y + dt * vy; }
      else if (meth === 1) {
        a = keplerAcc(x, y); vx += 0.5 * dt * a[0]; vy += 0.5 * dt * a[1]; x += dt * vx; y += dt * vy;
        a = keplerAcc(x, y); vx += 0.5 * dt * a[0]; vy += 0.5 * dt * a[1];
      } else {
        s0 = [x, y, vx, vy]; k1 = f(s0); k2 = f(adv(s0, k1, 0.5 * dt)); k3 = f(adv(s0, k2, 0.5 * dt)); k4 = f(adv(s0, k3, dt));
        s1 = []; for (i = 0; i < 4; i++) s1.push(s0[i] + dt / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]));
        x = s1[0]; y = s1[1]; vx = s1[2]; vy = s1[3];
      }
      t += dt; r = Math.sqrt(x * x + y * y); vr = (x * vx + y * vy) / r;
      En = 0.5 * (vx * vx + vy * vy) - 1.0 / r;
      ts.push(t); Es.push((En - E0) / Math.abs(E0)); trail.push(x); trail.push(y);
      if (vr < 0.0) seenNeg = true;
      if (seenNeg && prevVr < 0.0 && 0.0 <= vr && tc === 0.0) tc = prevT + dt * (-prevVr) / (vr - prevVr);
      prevVr = vr; prevT = t;
      if (tc > 0.0 && t > 1.3 * tc) break;
    }
    if (tc === 0.0) tc = t;
    return [tc, ts, Es, trail, E0];
  }
  function clusterRun(p) {
    var meth = I(p.method), n = Math.max(20, I(p.n)), ns = Math.max(4, I(p.ns)), st = lcg(p.seed), m = 1.0 / ns, eps2 = 0.01, pos = [], vel = [], i, k, q, g, j, v, cm, cv, acc, W, K, sc, tend = p.tend, dt = tend / n, ts = [], run = [], inst = [], sK = 0.0, sW = 0.0, step, acc2, ab;
    while (pos.length < ns) {
      q = [2.0 * u(st) - 1.0, 2.0 * u(st) - 1.0, 2.0 * u(st) - 1.0];
      if (q[0] * q[0] + q[1] * q[1] + q[2] * q[2] <= 1.0) pos.push(q);
    }
    for (i = 0; i < ns; i++) {
      v = [];
      for (k = 0; k < 3; k++) { g = 0.0; for (j = 0; j < 12; j++) g += u(st); v.push(g - 6.0); }
      vel.push(v);
    }
    for (k = 0; k < 3; k++) {
      cm = 0.0; cv = 0.0;
      for (i = 0; i < ns; i++) { cm += pos[i][k]; cv += vel[i][k]; }
      cm /= ns; cv /= ns;
      for (i = 0; i < ns; i++) { pos[i][k] -= cm; vel[i][k] -= cv; }
    }
    ab = clusterAcc(pos, m, eps2); acc = ab[0]; W = ab[1]; K = 0.0;
    for (i = 0; i < ns; i++) K += 0.5 * m * (vel[i][0] * vel[i][0] + vel[i][1] * vel[i][1] + vel[i][2] * vel[i][2]);
    sc = Math.sqrt(Math.abs(W) / (2.0 * K));
    for (i = 0; i < ns; i++) for (k = 0; k < 3; k++) vel[i][k] *= sc;
    for (step = 0; step <= n; step++) {
      ab = clusterAcc(pos, m, eps2); acc = ab[0]; W = ab[1]; K = 0.0;
      for (i = 0; i < ns; i++) K += 0.5 * m * (vel[i][0] * vel[i][0] + vel[i][1] * vel[i][1] + vel[i][2] * vel[i][2]);
      sK += 2.0 * K; sW += -W; ts.push(step * dt); run.push(sK / sW); inst.push(2.0 * K / (-W));
      if (step === n) break;
      if (meth === 0) {
        for (i = 0; i < ns; i++) for (k = 0; k < 3; k++) { vel[i][k] += dt * acc[i][k]; pos[i][k] += dt * vel[i][k]; }
      } else {
        for (i = 0; i < ns; i++) for (k = 0; k < 3; k++) { vel[i][k] += 0.5 * dt * acc[i][k]; pos[i][k] += dt * vel[i][k]; }
        acc2 = clusterAcc(pos, m, eps2)[0];
        for (i = 0; i < ns; i++) for (k = 0; k < 3; k++) vel[i][k] += 0.5 * dt * acc2[i][k];
      }
    }
    return [sK / sW, ts, run, inst, pos];
  }
  var CrNbody = kernel({
    PARAMS: { cas: 0.0, method: 1.0, n: 200.0, ecc: 0.5, seed: 1999.0, tend: 20.0, ns: 16.0 },
    init: function (p) {
      var cas = I(p.cas), ex = nbodyExact(p), r, i, pts = [], stride, tx = [], ty = [], tr = [], tl, ce = [], ones = [], ts, trail, cnt;
      if (cas === 1) {
        r = clusterRun(p);
        for (i = 0; i < r[4].length; i++) { pts.push(r[4][i][0]); pts.push(r[4][i][1]); }
        for (i = 0; i < r[1].length; i++) ones.push(1.0);
        return base(r[0], ex, I(p.n), r[1], ones, r[2], [], [], { cy2: r[3], pts: pts, pw: 2.0 });
      }
      r = keplerRun(p); ts = r[1]; trail = r[3];
      stride = Math.max(1, Math.floor(ts.length / 300));
      for (i = 0; i < ts.length; i += stride) { tx.push(ts[i]); ty.push(r[2][i]); ce.push(0.0); }
      cnt = trail.length / 2; tl = Math.max(1, Math.floor(cnt / 300));
      for (i = 0; i < cnt; i += tl) { tr.push(trail[2 * i]); tr.push(trail[2 * i + 1]); }
      return base(r[0], ex, I(p.n), tx, ce, ty, [], [], { pts: [trail[trail.length - 2], trail[trail.length - 1]], pw: 2.0, trail: tr, dE: r[2][r[2].length - 1] });
    }
  });

  // ====================================================================================== XY and Heisenberg spins
  function spinExact(p) {
    var cas = I(p.cas), w = I(p.what), T = p.T, L = Math.max(3, I(p.L)), N;
    if (cas === 0) {
      N = L * L;
      if (w === 1) return 1.0 - T / 4.0 * (1.0 - 1.0 / N);
      return -2.0 + 0.5 * T * (N - 1.0) / N;
    }
    N = L * L * L;
    return -3.0 + T * (N - 1.0) / N;
  }
  var CrSpin = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 800.0, seed: 4711.0, L: 8.0, T: 0.2, what: 0.0 },
    init: function (p) {
      var cas = I(p.cas), w = I(p.what), T = p.T, L = Math.max(3, I(p.L)), n = Math.max(20, I(p.n)), st = lcg(p.seed), dim = cas === 0 ? 2 : 3, N = Math.pow(L, dim), nbr = [], i, x, y, z, sp = [], delta, marks, mi = 0, se = 0.0, sy = 0.0, run = [], k, e, s, t2, jj, ex_, cur, est, val, ex, cx = [], lat = [], b;
      N = Math.round(N);
      for (i = 0; i < N; i++) {
        if (dim === 2) { x = i % L; y = Math.floor(i / L); nbr.push([y * L + (x + 1) % L, y * L + (x - 1 + L) % L, ((y + 1) % L) * L + x, ((y - 1 + L) % L) * L + x]); }
        else {
          x = i % L; y = Math.floor(i / L) % L; z = Math.floor(i / (L * L));
          nbr.push([z * L * L + y * L + (x + 1) % L, z * L * L + y * L + (x - 1 + L) % L, z * L * L + ((y + 1) % L) * L + x, z * L * L + ((y - 1 + L) % L) * L + x,
            ((z + 1) % L) * L * L + y * L + x, ((z - 1 + L) % L) * L * L + y * L + x]);
        }
        sp.push([1.0, 0.0, 0.0]);
      }
      delta = T < 0.5 ? 0.5 : 1.0;
      delta = T < 0.5 ? delta * Math.sqrt(T) * 2.0 : delta;
      function sweep() {
        var t, ii, a_, b_, c_, s_, nx, ny, nz, nn, hx, hy, hz, q, j2, dE;
        for (t = 0; t < N; t++) {
          ii = Math.floor(u(st) * N); if (ii > N - 1) ii = N - 1;
          while (true) {
            a_ = 2.0 * u(st) - 1.0; b_ = 2.0 * u(st) - 1.0; c_ = dim === 3 ? (2.0 * u(st) - 1.0) : 0.0;
            if (a_ * a_ + b_ * b_ + c_ * c_ <= 1.0) break;
          }
          s_ = sp[ii]; nx = s_[0] + delta * a_; ny = s_[1] + delta * b_; nz = dim === 3 ? s_[2] + delta * c_ : 0.0;
          nn = Math.sqrt(nx * nx + ny * ny + nz * nz); nx = nx / nn; ny = ny / nn; nz = nz / nn;
          hx = 0.0; hy = 0.0; hz = 0.0;
          for (q = 0; q < nbr[ii].length; q++) { j2 = nbr[ii][q]; hx += sp[j2][0]; hy += sp[j2][1]; hz += sp[j2][2]; }
          dE = -((nx - s_[0]) * hx + (ny - s_[1]) * hy + (nz - s_[2]) * hz);
          if (dE <= 0.0 || u(st) < Math.exp(-dE / T)) sp[ii] = [nx, ny, nz];
        }
      }
      for (b = 0; b < Math.floor(n / 5) + 40; b++) sweep();
      marks = marksOf(n);
      for (k = 1; k <= n; k++) {
        sweep(); e = 0.0;
        for (i = 0; i < N; i++) {
          s = sp[i];
          for (jj = 0; jj < nbr[i].length; jj += 2) { t2 = sp[nbr[i][jj]]; e -= s[0] * t2[0] + s[1] * t2[1] + s[2] * t2[2]; }
        }
        e /= N; se += e;
        if (cas === 0) {
          ex_ = 0.0; cur = 0.0;
          for (i = 0; i < N; i++) { s = sp[i]; t2 = sp[nbr[i][0]]; ex_ += s[0] * t2[0] + s[1] * t2[1]; cur += s[1] * t2[0] - s[0] * t2[1]; }
          sy += ex_ / N - cur * cur / (T * N);
        }
        est = w === 0 ? se / k : sy / k;
        while (mi < marks.length && marks[mi] === k) { run.push(est); mi++; }
      }
      val = w === 0 ? se / n : sy / n; ex = spinExact(p);
      var ce = [];
      for (i = 0; i < marks.length; i++) { cx.push(marks[i]); ce.push(ex); }
      for (i = 0; i < L * L; i++) { s = sp[i]; lat.push(cas === 0 ? Math.atan2(s[1], s[0]) : s[2]); }
      return base(val, ex, n, cx, ce, run, [cx[cx.length - 1]], [val], { lat: lat, lw: L, lh: L, latkind: cas });
    }
  });

  // ====================================================================================== exact diagonalisation
  function triMin(al, be) {
    var n = al.length, r = 0.0, i, lo, hi, mid, cnt, q, it;
    for (i = 0; i < be.length; i++) r = Math.max(r, Math.abs(be[i]));
    lo = Math.min.apply(null, al) - 2.0 * r - 1.0; hi = Math.max.apply(null, al) + 2.0 * r + 1.0;
    for (it = 0; it < 100; it++) {
      mid = 0.5 * (lo + hi); cnt = 0; q = al[0] - mid;
      if (q < 0.0) cnt += 1;
      for (i = 1; i < n; i++) {
        if (Math.abs(q) < 1e-300) q = 1e-300;
        q = al[i] - mid - be[i - 1] * be[i - 1] / q;
        if (q < 0.0) cnt += 1;
      }
      if (cnt >= 1) hi = mid; else lo = mid;
    }
    return 0.5 * (lo + hi);
  }
  function dot(a, b) { var r = 0.0, i; for (i = 0; i < a.length; i++) r += a[i] * b[i]; return r; }
  function lanczos(apply, dim, iters) {
    var v = [], i, nrm, vp = zeros(dim), beta = 0.0, al = [], be = [], best = null, k, w, a, b, e;
    for (i = 0; i < dim; i++) v.push(1.0 + 0.01 * ((i * 7919) % 101));
    nrm = Math.sqrt(dot(v, v));
    for (i = 0; i < dim; i++) v[i] = v[i] / nrm;
    for (k = 0; k < iters; k++) {
      w = apply(v); a = dot(w, v);
      for (i = 0; i < dim; i++) w[i] = w[i] - a * v[i] - beta * vp[i];
      al.push(a); b = Math.sqrt(dot(w, w));
      if (k % 5 === 4 || b < 1e-12) {
        e = triMin(al, be);
        if (best !== null && Math.abs(e - best) < 1e-12) return e;
        best = e;
      }
      if (b < 1e-12 || al.length >= dim) break;
      be.push(b); vp = v; v = []; for (i = 0; i < dim; i++) v.push(w[i] / b);
      beta = b;
    }
    return triMin(al, be.slice(0, al.length - 1));
  }
  function edTfim(N, h) {
    var dim = 1 << N, dg = [], s, i, d, a, b;
    for (s = 0; s < dim; s++) {
      d = 0.0;
      for (i = 0; i < N; i++) { a = 1.0 - 2.0 * ((s >> i) & 1); b = 1.0 - 2.0 * ((s >> ((i + 1) % N)) & 1); d -= a * b; }
      dg.push(d);
    }
    function apply(v) {
      var w = [], ss, x, ii;
      for (ss = 0; ss < dim; ss++) w.push(dg[ss] * v[ss]);
      for (ss = 0; ss < dim; ss++) { x = v[ss]; for (ii = 0; ii < N; ii++) w[ss ^ (1 << ii)] -= h * x; }
      return w;
    }
    return lanczos(apply, dim, 120);
  }
  function tfimExact(N, h) {
    var tot = 0.0, m, k;
    for (m = 0; m < N; m++) { k = (2 * m + 1) * PI / N; tot += Math.sqrt(1.0 + h * h - 2.0 * h * Math.cos(k)); }
    return -tot;
  }
  function edHeis(N) {
    var states = [], idx = {}, s, c, i, dim, dg = [], flips = [], d, fl, j, a, b;
    for (s = 0; s < (1 << N); s++) { c = 0; for (i = 0; i < N; i++) c += (s >> i) & 1; if (c === N / 2) states.push(s); }
    for (i = 0; i < states.length; i++) idx[states[i]] = i;
    dim = states.length;
    for (c = 0; c < dim; c++) {
      s = states[c]; d = 0.0; fl = [];
      for (i = 0; i < N; i++) {
        j = (i + 1) % N; a = (s >> i) & 1; b = (s >> j) & 1;
        if (a === b) d += 0.25; else { d -= 0.25; fl.push(idx[s ^ (1 << i) ^ (1 << j)]); }
      }
      dg.push(d); flips.push(fl);
    }
    function apply(v) {
      var w = [], k, x, t;
      for (k = 0; k < dim; k++) w.push(dg[k] * v[k]);
      for (k = 0; k < dim; k++) { x = 0.5 * v[k]; for (t = 0; t < flips[k].length; t++) w[flips[k][t]] += x; }
      return w;
    }
    return lanczos(apply, dim, 120);
  }
  function edExact(p) {
    if (I(p.cas) === 1) return 0.25 - Math.log(2.0);
    var N = Math.max(4, I(p.n));
    return tfimExact(N, p.h) / N;
  }
  var CrEd = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 8.0, h: 1.0 },
    init: function (p) {
      var cas = I(p.cas), N = Math.max(4, I(p.n)), sizes = [], k, e = {}, val, ex, cx = [], ce = [], cy = [], ed = [], h = p.h, i, ones = [];
      if (cas === 1) {
        N -= N % 2;
        for (k = 4; k <= N; k += 2) sizes.push(k);
        for (i = 0; i < sizes.length; i++) e[sizes[i]] = edHeis(sizes[i]) / sizes[i];
        if (N >= 6) val = (N * N * e[N] - (N - 2) * (N - 2) * e[N - 2]) / (N * N - (N - 2) * (N - 2)); else val = e[N];
        ex = edExact(p);
        for (i = 0; i < sizes.length; i++) { cx.push(1.0 / (sizes[i] * sizes[i])); ce.push(ex); cy.push(e[sizes[i]]); }
        return base(val, ex, N, cx, ce, cy, cx.slice(), cy.slice(), { eN: e[N] });
      }
      for (k = 4; k <= N; k += 2) sizes.push(k);
      for (i = 0; i < sizes.length; i++) { ed.push(edTfim(sizes[i], h) / sizes[i]); ce.push(tfimExact(sizes[i], h) / sizes[i]); cx.push(sizes[i]); }
      return base(ed[ed.length - 1], ce[ce.length - 1], N, cx, ce, ed, cx.slice(), ed.slice());
    }
  });

  // ====================================================================================== MCMC fitting
  function trapShape(t) { var a = Math.abs(t); if (a >= 0.25) return 0.0; if (a <= 0.15) return 1.0; return (0.25 - a) / 0.10; }
  function ssq(d) { var r = 0.0, i; for (i = 0; i < d.length; i++) r += d[i] * d[i]; return r; }
  function mcmcSetup(p) {
    var cas = I(p.cas), sig = p.sig, st = lcg(p.seed), M, xs = [], ys = [], i, A0, x00, w, tau0, d0, model;
    if (cas === 0) {
      M = 30; for (i = 0; i < M; i++) xs.push(-3.0 + 6.0 * i / (M - 1));
      A0 = 2.0; x00 = 0.3; w = 0.6;
      for (i = 0; i < M; i++) ys.push(A0 * Math.exp(-(xs[i] - x00) * (xs[i] - x00) / (2 * w * w)) + sig * gauss(st));
      model = function (q, a, b) { return a * Math.exp(-(q - b) * (q - b) / (2 * w * w)); };
      return { cas: cas, xs: xs, ys: ys, sig: sig, model: model, ra: [0.0, 5.0], rb: [-2.0, 2.0], truth: A0 };
    }
    if (cas === 1) {
      M = 30; for (i = 0; i < M; i++) xs.push(5.0 * i / (M - 1));
      A0 = 3.0; tau0 = 1.5;
      for (i = 0; i < M; i++) ys.push(A0 * Math.exp(-xs[i] / tau0) + sig * gauss(st));
      model = function (q, a, b) { return a * Math.exp(-q / b); };
      return { cas: cas, xs: xs, ys: ys, sig: sig, model: model, ra: [0.0, 8.0], rb: [0.4, 5.0], truth: tau0 };
    }
    M = 60; for (i = 0; i < M; i++) xs.push(-0.5 + i / (M - 1));
    d0 = 0.01;
    for (i = 0; i < M; i++) ys.push(1.0 - d0 * trapShape(xs[i]) + sig * gauss(st));
    return { cas: cas, xs: xs, ys: ys, sig: sig, model: null, ra: [0.0, 0.05], rb: null, truth: d0 };
  }
  var CrMcmc = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 20000.0, seed: 3003.0, what: 0.0, sig: 0.3 },
    init: function (p) {
      var n = Math.max(200, I(p.n)), w = I(p.what), S = mcmcSetup(p), cas = S.cas, xs = S.xs, ys = S.ys, sig = S.sig, model = S.model, ra = S.ra, rb = S.rb, M = xs.length,
        st = lcg(p.seed + 17.0), i, j, k, a, b, gm, gs, ex, lo, hi, post = null, logp, th, step, sm = 0.0, sy = 0.0, m_,
        GA = 120, GB = 120, ga = [], gb = [], lp = [], best = -1e300, row, s, d, v, wgt, primVals, marg = [], tot, primW, other, om = [], ot, omean, osd, margIdx, d_;
      if (cas === 2) {
        for (i = 0; i < M; i++) { m_ = trapShape(xs[i]); sm += m_ * m_; sy += m_ * (1.0 - ys[i]); }
        gm = sy / sm; gs = sig / Math.sqrt(sm); lo = gm - 4.0 * gs; hi = gm + 4.0 * gs;
        post = function (q) { return Math.exp(-0.5 * (q - gm) * (q - gm) / (gs * gs)) / (gs * Math.sqrt(2 * PI)); };
        logp = function (t_) { var dd = [], q; for (q = 0; q < M; q++) dd.push(ys[q] - (1.0 - t_[0] * trapShape(xs[q]))); return -0.5 * ssq(dd) / (sig * sig); };
        th = [gm]; step = [2.4 * gs]; ex = w === 0 ? gm : gs;
      } else {
        for (i = 0; i < GA; i++) ga.push(ra[0] + (ra[1] - ra[0]) * (i + 0.5) / GA);
        for (i = 0; i < GB; i++) gb.push(rb[0] + (rb[1] - rb[0]) * (i + 0.5) / GB);
        for (i = 0; i < GA; i++) {
          row = [];
          for (j = 0; j < GB; j++) {
            s = 0.0;
            for (k = 0; k < M; k++) { d = ys[k] - model(xs[k], ga[i], gb[j]); s += d * d; }
            v = -0.5 * s / (sig * sig); row.push(v); if (v > best) best = v;
          }
          lp.push(row);
        }
        wgt = [];
        for (i = 0; i < GA; i++) { row = []; for (j = 0; j < GB; j++) row.push(Math.exp(lp[i][j] - best)); wgt.push(row); }
        primVals = cas === 0 ? ga : gb;
        for (k = 0; k < primVals.length; k++) {
          s = 0.0;
          if (cas === 0) { for (j = 0; j < GB; j++) s += wgt[k][j]; } else { for (i = 0; i < GA; i++) s += wgt[i][k]; }
          marg.push(s);
        }
        tot = fsum(marg); s = 0.0;
        for (k = 0; k < primVals.length; k++) s += primVals[k] * marg[k];
        gm = s / tot; s = 0.0;
        for (k = 0; k < primVals.length; k++) s += (primVals[k] - gm) * (primVals[k] - gm) * marg[k];
        gs = Math.sqrt(s / tot);
        ex = w === 0 ? gm : gs; primW = primVals[1] - primVals[0]; lo = gm - 4.0 * gs; hi = gm + 4.0 * gs;
        other = cas === 0 ? gb : ga;
        for (k = 0; k < other.length; k++) {
          s = 0.0;
          if (cas === 0) { for (i = 0; i < GA; i++) s += wgt[i][k]; } else { for (j = 0; j < GB; j++) s += wgt[k][j]; }
          om.push(s);
        }
        ot = fsum(om); s = 0.0;
        for (k = 0; k < other.length; k++) s += other[k] * om[k];
        omean = s / ot; s = 0.0;
        for (k = 0; k < other.length; k++) s += (other[k] - omean) * (other[k] - omean) * om[k];
        osd = Math.sqrt(s / ot);
        if (cas === 0) { step = [2.0 * gs, 2.0 * osd]; th = [gm, omean]; } else { step = [2.0 * osd, 2.0 * gs]; th = [omean, gm]; }
        logp = function (t_) {
          var dd = [], q;
          if (!(ra[0] < t_[0] && t_[0] < ra[1] && rb[0] < t_[1] && t_[1] < rb[1])) return -1e300;
          for (q = 0; q < M; q++) dd.push(ys[q] - model(xs[q], t_[0], t_[1]));
          return -0.5 * ssq(dd) / (sig * sig);
        };
      }
      var k0 = cas !== 1 ? 0 : 1, cur = logp(th), burn = Math.floor(n / 5), marks = marksOf(n), mi = 0, s1 = 0.0, s2 = 0.0, cnt = 0, run = [], NH = 30, hist = zeros(NH), acc = 0.0, est = 0.0, it, prop, lq, mean, jj;
      for (it = 1; it <= n + burn; it++) {
        prop = [];
        for (j = 0; j < th.length; j++) prop.push(th[j] + step[j] * (2.0 * u(st) - 1.0) * 1.7320508075688772);
        if (cas === 2 && !(0.0 < prop[0] && prop[0] < 0.05)) lq = -1e300; else lq = logp(prop);
        if (lq >= cur || u(st) < Math.exp(lq - cur)) { th = prop; cur = lq; acc += 1.0; }
        if (it > burn) {
          v = th[k0]; cnt += 1; s1 += v; s2 += v * v;
          jj = Math.floor((v - lo) / (hi - lo) * NH);
          if (jj >= 0 && jj < NH) hist[jj] += 1.0;
          mean = s1 / cnt;
          est = w === 0 ? mean : Math.sqrt(Math.max(s2 / cnt - mean * mean, 0.0));
          while (mi < marks.length && marks[mi] === cnt) { run.push(est); mi++; }
        }
      }
      var bw = (hi - lo) / NH, hx = [], hy = [], hz = [], q, cx = [], ce = [];
      for (j = 0; j < NH; j++) { hx.push(lo + (j + 0.5) * bw); hy.push(hist[j] / (cnt * bw)); }
      if (post !== null) { for (j = 0; j < NH; j++) hz.push(post(hx[j])); }
      else for (j = 0; j < NH; j++) { k = Math.floor((hx[j] - primVals[0]) / primW + 0.5); hz.push(k >= 0 && k < marg.length ? marg[k] / (tot * primW) : 0.0); }
      for (j = 0; j < marks.length; j++) { cx.push(marks[j]); ce.push(ex); }
      return base(est, ex, n, cx, ce, run, [cx[cx.length - 1]], [est], { hx: hx, hy: hy, hz: hz, accept: acc / (n + burn), truth: S.truth, dx: xs.slice(), dy: ys.slice() });
    }
  });
  function mcmcExact(p) { var q = Object.assign({}, p); q.n = 200.0; return CrMcmc.init(q).exact; }

  // ====================================================================================== FDTD (1-D)
  function tmT(layers, w) {
    var aR = 1.0, aI = 0.0, bR = 0.0, bI = 0.0, cR = 0.0, cI = 0.0, dR = 1.0, dI = 0.0, i, nr, th, dl, cs, sn, m12i, m21i, naR, naI, nbR, nbI, ncR, ncI, ndR, ndI, sr, si;
    for (i = 0; i < layers.length; i++) {
      nr = layers[i][0]; th = layers[i][1]; dl = nr * w * th; cs = Math.cos(dl); sn = Math.sin(dl);
      m12i = -sn / nr; m21i = -nr * sn;
      naR = aR * cs - bI * m21i; naI = aI * cs + bR * m21i;
      nbR = aR * 0.0 - aI * m12i + bR * cs; nbI = aR * m12i + aI * 0.0 + bI * cs;
      ncR = cR * cs - dI * m21i; ncI = cI * cs + dR * m21i;
      ndR = -cI * m12i + dR * cs; ndI = cR * m12i + dI * cs;
      aR = naR; aI = naI; bR = nbR; bI = nbI; cR = ncR; cI = ncI; dR = ndR; dI = ndI;
    }
    sr = aR + bR + cR + dR; si = aI + bI + cI + dI;
    return 4.0 / (sr * sr + si * si);
  }
  function fdtdLayers(p) {
    var cas = I(p.cas), n = Math.max(10, I(p.n)), nr, nh, nl, dh, dl, out = [], k;
    if (cas === 0) { nr = p.n1; return [[nr, Math.max(1, I(n / (4.0 * nr)))]]; }
    nh = p.n1; nl = p.n2; dh = Math.max(1, I(n / (4.0 * nh))); dl = Math.max(1, I(n / (4.0 * nl)));
    for (k = 0; k < I(p.np); k++) { out.push([nh, dh]); out.push([nl, dl]); }
    return out;
  }
  function fdtdRun(layers, n, freqs) {
    var pad = 30, total = 0, i, N, eps, pos, E, H, wc, tau, t0, xs, xp, steps, cr, ci, sr, si, cw, sw, e1Old, eNOld, t, tt, v, j, nr, th, q, out = [], nc;
    for (i = 0; i < layers.length; i++) total += layers[i][1];
    N = pad + total + pad + 10; eps = fill(N + 1, 1.0); pos = pad;
    for (i = 0; i < layers.length; i++) { nr = layers[i][0]; th = layers[i][1]; for (q = 0; q < th; q++) { eps[pos] = nr * nr; pos += 1; } }
    E = zeros(N + 1); H = zeros(N + 1); wc = 2.0 * PI / n; tau = 1.2 * n; t0 = 4.0 * tau; xs = 6; xp = N - 8;
    steps = Math.floor(t0 * 2.0 + 40 * n);
    cr = fill(freqs.length, 1.0); ci = zeros(freqs.length); sr = zeros(freqs.length); si = zeros(freqs.length); cw = []; sw = [];
    for (j = 0; j < freqs.length; j++) { cw.push(Math.cos(wc * freqs[j])); sw.push(Math.sin(wc * freqs[j])); }
    for (t = 0; t < steps; t++) {
      for (i = 0; i < N; i++) H[i] += E[i + 1] - E[i];
      e1Old = E[1]; eNOld = E[N - 1];
      for (i = 1; i < N; i++) E[i] += (H[i] - H[i - 1]) / eps[i];
      tt = t - t0;
      E[xs] += Math.exp(-(tt / tau) * (tt / tau)) * Math.cos(wc * tt);
      E[0] = e1Old; E[N] = eNOld; v = E[xp];
      for (j = 0; j < freqs.length; j++) {
        sr[j] += v * cr[j]; si[j] -= v * ci[j];
        nc = cr[j] * cw[j] - ci[j] * sw[j]; ci[j] = cr[j] * sw[j] + ci[j] * cw[j]; cr[j] = nc;
      }
    }
    for (j = 0; j < freqs.length; j++) out.push(sr[j] * sr[j] + si[j] * si[j]);
    return out;
  }
  function fdtdExact(p) { return tmT(fdtdLayers(p), 2.0 * PI / Math.max(10, I(p.n)) * p.wr); }
  var CrFdtd = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 40.0, n1: 2.0, n2: 1.5, np: 3.0, wr: 0.8 },
    init: function (p) {
      var n = Math.max(10, I(p.n)), layers = fdtdLayers(p), grid2 = [], j, freqs, ref, out, wc = 2.0 * PI / n, Tn = [], ex = [], nc = 0;
      for (j = 0; j < 34; j++) grid2.push(0.45 + 1.1 * j / 33.0);
      freqs = [p.wr].concat(grid2);
      ref = fdtdRun([], n, freqs); out = fdtdRun(layers, n, freqs);
      for (j = 0; j < freqs.length; j++) { Tn.push(ref[j] > 0 ? out[j] / ref[j] : 0.0); ex.push(tmT(layers, wc * freqs[j])); }
      for (j = 0; j < layers.length; j++) nc += layers[j][1];
      return base(Tn[0], ex[0], n, grid2, ex.slice(1), Tn.slice(1), [p.wr], [Tn[0]], { ncells: nc });
    }
  });

  // ====================================================================================== particle-in-cell
  function twoStreamGamma(k, v0) {
    var a = k * k * v0 * v0, W = ((2.0 * a + 1.0) - Math.sqrt(1.0 + 8.0 * a)) / 2.0;
    return W < 0.0 ? Math.sqrt(-W) : 0.0;
  }
  function picExact(p) { return I(p.cas) === 1 ? twoStreamGamma(p.kk, p.v0) : 1.0; }
  var CrPic = kernel({
    PARAMS: { cas: 0.0, method: 0.0, n: 32.0, np: 800.0, kk: 0.6123724356957945, v0: 1.0, amp: 0.001 },
    init: function (p) {
      var cas = I(p.cas), n = Math.max(8, I(p.n)), Np = Math.max(100, I(p.np)), Ng = 32, k1 = cas === 0 ? 1.0 : p.kk, L = 2.0 * PI / k1, dx = L / Ng, dt = 2.0 * PI / n,
        amp = cas === 0 ? p.amp : 1e-5, x = [], v = [], i, x0, v0, xx, wq = L / Np, E, A0, ts, As, tmax, nsteps, t = 0.0, s, a, ex = picExact(p), stride, val = 0.0, cx = [], cy = [], ce = [], crossings = [], j;
      function field(xp) {
        var ne = zeros(Ng), g, jj, f, ee = zeros(Ng), run = 0.0, mean, q;
        for (q = 0; q < xp.length; q++) {
          g = xp[q] / dx; jj = Math.floor(g); f = g - jj;
          ne[mod(jj, Ng)] += (1.0 - f) * wq / dx; ne[mod(jj + 1, Ng)] += f * wq / dx;
        }
        for (jj = 0; jj < Ng; jj++) { run += dx * (1.0 - ne[jj]); ee[jj] = run; }
        mean = fsum(ee) / Ng;
        for (jj = 0; jj < Ng; jj++) ee[jj] = ee[jj] - mean;
        return ee;
      }
      function gather(Ef, xx2) {
        var g = xx2 / dx - 0.5, jj = Math.floor(g), f = g - jj;
        return (1.0 - f) * Ef[mod(jj, Ng)] + f * Ef[mod(jj + 1, Ng)];
      }
      function modeAmp(Ef) { var aa = 0.0, jj; for (jj = 0; jj < Ng; jj++) aa += Ef[jj] * Math.sin(k1 * (jj + 0.5) * dx); return 2.0 * aa / Ng; }
      for (i = 0; i < Np; i++) {
        x0 = (i + 0.5) * L / Np; v0 = 0.0;
        if (cas === 1) v0 = (i % 2) === 0 ? p.v0 : -p.v0;
        xx = x0 + amp * Math.sin(k1 * x0) / (cas === 0 ? k1 : 1.0);
        x.push(mod(xx, L)); v.push(v0);
      }
      E = field(x);
      for (i = 0; i < Np; i++) v[i] += 0.5 * dt * gather(E, x[i]);
      A0 = modeAmp(E); ts = [0.0]; As = [A0];
      tmax = cas === 0 ? 6.0 * 2.0 * PI : 70.0; nsteps = Math.floor(tmax / dt);
      for (s = 0; s < nsteps; s++) {
        for (i = 0; i < Np; i++) { v[i] -= dt * gather(E, x[i]); x[i] = mod(x[i] + dt * v[i], L); }
        t += dt; E = field(x); a = modeAmp(E); ts.push(t); As.push(a);
        if (cas === 1 && Math.abs(a) > 0.03) break;
      }
      stride = Math.max(1, Math.floor(ts.length / 240));
      if (cas === 0) {
        for (i = 1; i < ts.length; i++) if ((As[i - 1] > 0.0 && 0.0 >= As[i]) || (As[i - 1] < 0.0 && 0.0 <= As[i])) crossings.push(ts[i - 1] + dt * As[i - 1] / (As[i - 1] - As[i]));
        val = crossings.length >= 3 ? PI * (crossings.length - 1) / (crossings[crossings.length - 1] - crossings[0]) : 0.0;
        for (i = 0; i < ts.length; i += stride) { cx.push(ts[i]); cy.push(As[i] / A0); }
        for (i = 0; i < cx.length; i++) ce.push(Math.cos(cx[i] * ex));
      } else {
        var sx = 0.0, sy = 0.0, sxx = 0.0, sxy = 0.0, m_ = 0, aa, ly, den, t0w = 0.0, ly0 = Math.log(1e-3);
        for (i = 0; i < ts.length; i++) {
          aa = Math.abs(As[i]);
          if (1e-3 <= aa && aa <= 2e-2) { ly = Math.log(aa); sx += ts[i]; sy += ly; sxx += ts[i] * ts[i]; sxy += ts[i] * ly; m_ += 1; }
        }
        den = m_ * sxx - sx * sx;
        val = (m_ >= 3 && Math.abs(den) > 1e-12) ? (m_ * sxy - sx * sy) / den : 0.0;
        for (i = 0; i < ts.length; i += stride) { cx.push(ts[i]); cy.push(Math.log(Math.max(Math.abs(As[i]), 1e-12))); }
        for (i = 0; i < ts.length; i++) if (Math.abs(As[i]) >= 1e-3) { t0w = ts[i]; break; }
        for (i = 0; i < cx.length; i++) ce.push(ly0 + ex * (cx[i] - t0w));
      }
      var pts = [], vm = 0.0;
      for (i = 0; i < Np; i += Math.max(1, Math.floor(Np / 300))) { pts.push(x[i] / L); pts.push(v[i]); }
      for (i = 0; i < Np; i++) vm = Math.max(vm, Math.abs(v[i]));
      return base(val, ex, n, cx, ce, cy, [], [], { pts: pts, pw: 1.0, ptskind: 1.0, vmax: vm + 0.2 });
    }
  });

  // ====================================================================================== calcs
  function best(r) {
    var rs = rowsOf(r, ['n', 'val']), i, b;
    if (!rs.length) return 0;
    b = rs[0]; for (i = 0; i < rs.length; i++) if (rs[i][0] > b[0]) b = rs[i];
    return b[1];
  }
  function order(r) {
    var rs = rowsOf(r, ['n', 'err']), pts = [], i, sx = 0, sy = 0, sxx = 0, sxy = 0, den;
    for (i = 0; i < rs.length; i++) if (rs[i][0] > 0 && rs[i][1] > 0) pts.push([Math.log(rs[i][0]), Math.log(rs[i][1])]);
    if (pts.length < 2) return 0;
    for (i = 0; i < pts.length; i++) { sx += pts[i][0]; sy += pts[i][1]; sxx += pts[i][0] * pts[i][0]; sxy += pts[i][0] * pts[i][1]; }
    den = pts.length * sxx - sx * sx;
    if (Math.abs(den) < 1e-30) return 0;
    return -(pts.length * sxy - sx * sy) / den;
  }

  root.HoolaKernels.register({
    K: { cr_interp: CrInterp, cr_pde: CrPde, cr_fem: CrFem, cr_fit: CrFit, cr_mle: CrMle, cr_dev: CrDev, cr_walk: CrWalk,
      cr_decay: CrDecay, cr_twolevel: CrTwoLevel, cr_mcint: CrMcInt, cr_scatter: CrScatter, cr_poly: CrPoly,
      cr_photon: CrPhoton, cr_ising: CrIsing, cr_binder: CrBinder, cr_tb: CrTb, cr_schro: CrSchro, cr_nbody: CrNbody,
      cr_spin: CrSpin, cr_ed: CrEd, cr_mcmc: CrMcmc, cr_fdtd: CrFdtd, cr_pic: CrPic },
    TEXTBOOK: {
      cr_interp_f: ipExact, cr_pde_u: pdeExact, cr_fem_u: femExact, cr_fit_p: fitExact, cr_mle_p: mleExact,
      cr_dev_f: devExact, cr_walk_v: walkExact, cr_decay_v: decayExact, cr_two_v: twoExact, cr_mcint_I: mcintExact,
      cr_scatter_s: scatterExact, cr_poly_x: polyExact, cr_photon_v: photonExact, cr_ising_v: isingExact,
      cr_binder_T: binderExact, cr_tb_E: tbExact, cr_schro_E: schroExact, cr_nbody_v: nbodyExact, cr_spin_v: spinExact,
      cr_ed_E: edExact, cr_mcmc_v: mcmcExact, cr_fdtd_T: fdtdExact, cr_pic_v: picExact
    },
    CALCS: {
      cr_best: { label: 'best value', unit: '', needs: ['n', 'val'], fn: best },
      cr_order: { label: 'order of the method', unit: '', needs: ['n', 'err'], fn: order }
    }
  });
})(typeof window !== 'undefined' ? window : this);
