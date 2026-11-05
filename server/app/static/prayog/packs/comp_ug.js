/* Kernel pack (browser twin of app/prayog/packs/comp_ug.py): the UG "Computational physics" practicals.
   Same formulas, same order of operations, so both sides give the same numbers. Deterministic throughout.
     cp_root    f(x) = 0 by bisection / Newton-Raphson / secant
     cp_quad    definite integral by trapezoid / Simpson 1/3 / Simpson 3/8 / Gauss-Legendre
     cp_ode1    first-order IVP by Euler / RK2 (Heun) / RK4
     cp_diff    derivative from tabulated values: forward / backward / central / five-point
     cp_approx  Taylor partial sum / Lagrange interpolating polynomial
   Every kernel reports val (numerical), exact (analytic), err, nused and the curves the monitor draws
   (cx / ce / cy and the nodes px / py). */
(function (root) {
  'use strict';
  var PI = Math.PI;

  function I(v) { return Math.round(v); }
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0; }
  function rows(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) { v = Number(rs[i][keys[j]]); if (rs[i][keys[j]] === '' || rs[i][keys[j]] === null || rs[i][keys[j]] === undefined || !isFinite(v)) { ok = false; break; } vals.push(v); }
      if (ok) out.push(vals);
    }
    return out;
  }
  function errOf(val, exact) { return Math.abs(val - exact) / Math.max(Math.abs(exact), 1e-30); }
  function grid(a, b, m) { var out = [], i; for (i = 0; i <= m; i++) out.push(a + (b - a) * i / m); return out; }
  function mapf(xs, f) { var out = [], i; for (i = 0; i < xs.length; i++) out.push(f(xs[i])); return out; }

  // ====================================================================================== root finding
  function rootF(cas, x, p) {
    if (cas === 1) { var R = p.R; return x * x * x - 3 * R * x * x + 4 * p.s * R * R * R; }
    if (cas === 2) return Math.tan(x) - x;
    return Math.pow(x, p.m) - p.a;
  }
  function rootDf(cas, x, p) {
    if (cas === 1) return 3 * x * x - 6 * p.R * x;
    if (cas === 2) { var t = Math.tan(x); return t * t; }
    return p.m * Math.pow(x, p.m - 1);
  }
  function bisect(cas, p, a, b, iters) {
    var fa = rootF(cas, a, p), out = [], i, mid, fm;
    for (i = 0; i < iters; i++) {
      mid = 0.5 * (a + b); fm = rootF(cas, mid, p); out.push(mid);
      if ((fm < 0) === (fa < 0)) { a = mid; fa = fm; } else { b = mid; }
    }
    return out;
  }
  function rootExact(p) {
    var cas = I(p.cas), s, xs;
    if (cas === 1) { s = Math.min(Math.max(p.s, 1e-9), 1 - 1e-9); return p.R * (1 + 2 * Math.cos(Math.acos(1 - 2 * s) / 3 + 4 * PI / 3)); }
    if (cas === 2) { xs = bisect(2, p, p.xa, p.xb, 200); return xs[xs.length - 1]; }
    return Math.pow(p.a, 1.0 / p.m);
  }
  var CpRoot = {
    PARAMS: { cas: 0.0, method: 0.0, n: 12.0, a: 2.0, m: 2.0, R: 0.05, s: 0.6, x0: 1.0, x1: 2.0, xa: 0.0, xb: 4.0 },
    VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'],
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), n = Math.max(2, I(p.n)), xa = p.xa, xb = p.xb, it, i, x, d, x0, x1, f0, f1, x2;
      if (meth === 0) it = bisect(cas, p, xa, xb, n);
      else if (meth === 1) {
        x = p.x0; it = [];
        for (i = 0; i < n; i++) { d = rootDf(cas, x, p); if (Math.abs(d) < 1e-14) break; x = x - rootF(cas, x, p) / d; it.push(x); }
      } else {
        x0 = p.x0; x1 = p.x1; it = []; f0 = rootF(cas, x0, p); f1 = rootF(cas, x1, p);
        for (i = 0; i < n; i++) {
          if (Math.abs(f1 - f0) < 1e-14) break;
          x2 = x1 - f1 * (x1 - x0) / (f1 - f0);
          x0 = x1; f0 = f1; x1 = x2; f1 = rootF(cas, x2, p); it.push(x1);
        }
      }
      var val = it.length ? it[it.length - 1] : p.x0, exact = rootExact(p), cx = grid(xa, xb, 60);
      return { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: it.length,
        cx: cx, ce: mapf(cx, function (z) { return rootF(cas, z, p); }), cy: [],
        px: it.slice(), py: mapf(it, function (z) { return rootF(cas, z, p); }) };
    },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s) { return Object.assign({}, s); },
    measure: function (p) { var s = CpRoot.init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
  };

  // ====================================================================================== quadrature
  function quadF(cas, x, p) {
    if (cas === 1) return p.A * Math.sin(p.w * x);
    if (cas === 2) return p.A * Math.pow(x, p.kk);
    if (cas === 3) { var e = p.eps; return e / (PI * (x * x + e * e)); }
    return 1.0 / x;
  }
  function quadExact(p) {
    var cas = I(p.cas), a = p.xa, b = p.xb, k;
    if (cas === 1) return p.A * (Math.cos(p.w * a) - Math.cos(p.w * b)) / p.w;
    if (cas === 2) { k = p.kk; return p.A * (Math.pow(b, k + 1) - Math.pow(a, k + 1)) / (k + 1); }
    if (cas === 3) return (Math.atan(b / p.eps) - Math.atan(a / p.eps)) / PI;
    return Math.log(b / a);
  }
  function gauleg(n, a, b) {
    var xs = [], ws = [], i, j, m = Math.floor((n + 1) / 2), xm = 0.5 * (b + a), xl = 0.5 * (b - a), z, z1, pp, p1, p2, p3, it;
    for (i = 0; i < n; i++) { xs.push(0.0); ws.push(0.0); }
    for (i = 1; i <= m; i++) {
      z = Math.cos(PI * (i - 0.25) / (n + 0.5)); pp = 1.0;
      for (it = 0; it < 60; it++) {
        p1 = 1.0; p2 = 0.0;
        for (j = 1; j <= n; j++) { p3 = p2; p2 = p1; p1 = ((2 * j - 1) * z * p2 - (j - 1) * p3) / j; }
        pp = n * (z * p1 - p2) / (z * z - 1.0);
        z1 = z; z = z1 - p1 / pp;
        if (Math.abs(z - z1) <= 3e-15) break;
      }
      xs[i - 1] = xm - xl * z; xs[n - i] = xm + xl * z;
      ws[i - 1] = 2 * xl / ((1 - z * z) * pp * pp); ws[n - i] = ws[i - 1];
    }
    return [xs, ws];
  }
  function nq(meth, n) {
    if (meth === 1) return Math.max(2, n - (n % 2));
    if (meth === 2) return Math.max(3, n - (n % 3));
    if (meth === 3) return Math.max(1, Math.min(64, n));   // Gauss-Legendre: real node tables stop well short of this
    return Math.max(1, n);
  }
  var CpQuad = {
    PARAMS: { cas: 0.0, method: 0.0, n: 8.0, xa: 1.0, xb: 2.0, A: 1.0, w: 1.0, kk: 2.0, eps: 0.2 },
    VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'],
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), n = nq(meth, Math.max(1, I(p.n))), a = p.xa, b = p.xb;
      var px = [], val = 0.0, gw, xs, ws, h, fs, i;
      if (meth === 3) {
        gw = gauleg(n, a, b); xs = gw[0]; ws = gw[1];
        for (i = 0; i < n; i++) val += ws[i] * quadF(cas, xs[i], p);
        px = xs.slice();
      } else {
        h = (b - a) / n; xs = []; for (i = 0; i <= n; i++) xs.push(a + h * i);
        fs = mapf(xs, function (z) { return quadF(cas, z, p); });
        if (meth === 0) {
          val = 0.5 * (fs[0] + fs[n]);
          for (i = 1; i < n; i++) val += fs[i];
          val *= h;
        } else if (meth === 1) {
          val = fs[0] + fs[n];
          for (i = 1; i < n; i++) val += (i % 2 === 1 ? 4.0 : 2.0) * fs[i];
          val *= h / 3.0;
        } else {
          val = fs[0] + fs[n];
          for (i = 1; i < n; i++) val += (i % 3 === 0 ? 2.0 : 3.0) * fs[i];
          val *= 3.0 * h / 8.0;
        }
        px = xs.slice();
      }
      var exact = quadExact(p), cx = grid(a, b, 60);
      return { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: n,
        cx: cx, ce: mapf(cx, function (z) { return quadF(cas, z, p); }), cy: [],
        px: px, py: mapf(px, function (z) { return quadF(cas, z, p); }) };
    },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s) { return Object.assign({}, s); },
    measure: function (p) { var s = CpQuad.init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
  };

  // ====================================================================================== first-order IVP
  function ode1F(cas, t, y, p) {
    if (cas === 1) return (p.Em - y / p.Cc) / p.Rr;
    if (cas === 2) return -p.kk * (y - p.Ts);
    if (cas === 3) return p.rr * y * (1 - y / p.Kk);
    return -p.lam * y;
  }
  function ode1Exact(cas, t, p) {
    var e;
    if (cas === 1) return p.Cc * p.Em * (1 - Math.exp(-t / (p.Rr * p.Cc))) + p.y0 * Math.exp(-t / (p.Rr * p.Cc));
    if (cas === 2) return p.Ts + (p.y0 - p.Ts) * Math.exp(-p.kk * t);
    if (cas === 3) { e = Math.exp(p.rr * t); return p.Kk * p.y0 * e / (p.Kk + p.y0 * (e - 1)); }
    return p.y0 * Math.exp(-p.lam * t);
  }
  var CpOde1 = {
    PARAMS: { cas: 0.0, method: 2.0, n: 20.0, y0: 1.0, tmax: 10.0, lam: 0.1, Rr: 1000.0, Cc: 0.001, Em: 5.0,
      kk: 0.02, Ts: 30.0, rr: 0.5, Kk: 1000.0 },
    VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'],
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), n = Math.max(1, I(p.n)), tmax = p.tmax, h = tmax / n;
      var t = 0.0, y = p.y0, px = [0.0], py = [y], i, k1, k2, k3, k4;
      for (i = 0; i < n; i++) {
        if (meth === 0) y = y + h * ode1F(cas, t, y, p);
        else if (meth === 1) {
          k1 = ode1F(cas, t, y, p); k2 = ode1F(cas, t + h, y + h * k1, p);
          y = y + h * 0.5 * (k1 + k2);
        } else {
          k1 = ode1F(cas, t, y, p);
          k2 = ode1F(cas, t + h / 2, y + h / 2 * k1, p);
          k3 = ode1F(cas, t + h / 2, y + h / 2 * k2, p);
          k4 = ode1F(cas, t + h, y + h * k3, p);
          y = y + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4);
        }
        t = t + h; px.push(t); py.push(y);
      }
      var exact = ode1Exact(cas, tmax, p), cx = grid(0.0, tmax, 60);
      return { t: 0.0, val: y, exact: exact, err: errOf(y, exact), nused: n,
        cx: cx, ce: mapf(cx, function (z) { return ode1Exact(cas, z, p); }), cy: py.slice(),
        px: px.slice(), py: py.slice() };
    },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s) { return Object.assign({}, s); },
    measure: function (p) { var s = CpOde1.init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
  };

  // ====================================================================================== differentiation
  function fdF(cas, x, p) {
    if (cas === 1) return p.A * Math.exp(p.w * x);
    if (cas === 2) return p.A * Math.pow(x, p.kk);
    return p.A * Math.sin(p.w * x);
  }
  function fdExact(p) {
    var cas = I(p.cas), x = p.x;
    if (cas === 1) return p.A * p.w * Math.exp(p.w * x);
    if (cas === 2) return p.A * p.kk * Math.pow(x, p.kk - 1);
    return p.A * p.w * Math.cos(p.w * x);
  }
  var CpDiff = {
    PARAMS: { cas: 0.0, method: 2.0, n: 10.0, x: 1.0, h0: 0.4, A: 1.0, w: 2.0, kk: 3.0 },
    VARS: ['t', 'val', 'exact', 'err', 'nused', 'hstep', 'cx', 'ce', 'cy', 'px', 'py'],
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), n = Math.max(1, I(p.n)), h = p.h0 / n, x = p.x, val, px;
      var f = function (z) { return fdF(cas, z, p); };
      if (meth === 0) { val = (f(x + h) - f(x)) / h; px = [x, x + h]; }
      else if (meth === 1) { val = (f(x) - f(x - h)) / h; px = [x - h, x]; }
      else if (meth === 2) { val = (f(x + h) - f(x - h)) / (2 * h); px = [x - h, x, x + h]; }
      else { val = (-f(x + 2 * h) + 8 * f(x + h) - 8 * f(x - h) + f(x - 2 * h)) / (12 * h); px = [x - 2 * h, x - h, x, x + h, x + 2 * h]; }
      var exact = fdExact(p), half = Math.max(2 * p.h0, Math.abs(x) * 0.6, 1e-6), cx = grid(x - half, x + half, 60);
      return { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: n, hstep: h,
        cx: cx, ce: mapf(cx, f), cy: mapf(cx, function (z) { return f(x) + exact * (z - x); }),
        px: px, py: mapf(px, f) };
    },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s) { return Object.assign({}, s); },
    measure: function (p) { var s = CpDiff.init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
  };

  // ====================================================================================== series / interpolation
  function apF(cas, x) {
    if (cas === 1) return Math.sin(x);
    if (cas === 2) return Math.cos(x);
    if (cas === 3) return Math.log(1 + x);
    return Math.exp(x);
  }
  function taylor(cas, x, n) {
    var s = 0.0, term, k, i;
    if (cas === 1 || cas === 2) {
      term = cas === 1 ? x : 1.0; k = cas === 1 ? 1 : 0;
      for (i = 0; i < n; i++) { s += term; term = -term * x * x / ((k + 1) * (k + 2)); k += 2; }
      return s;
    }
    if (cas === 3) {
      term = x;
      for (k = 1; k <= n; k++) { s += term / k; term = -term * x; }
      return s;
    }
    term = 1.0;
    for (k = 1; k <= n; k++) { s += term; term = term * x / k; }
    return s;
  }
  function lagrange(cas, x, p, n) {
    var nodes = grid(p.xa, p.xb, n), val = 0.0, i, j, term;
    for (i = 0; i <= n; i++) {
      term = apF(cas, nodes[i]);
      for (j = 0; j <= n; j++) if (j !== i) term *= (x - nodes[j]) / (nodes[i] - nodes[j]);
      val += term;
    }
    return [val, nodes];
  }
  var CpApprox = {
    PARAMS: { cas: 0.0, method: 0.0, n: 6.0, x: 1.0, xa: 0.0, xb: 2.0 },
    VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'],
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), n = Math.max(1, I(p.n)), val, px, lg;
      if (meth === 1) { lg = lagrange(cas, p.x, p, n); val = lg[0]; px = lg[1].slice(); }
      else { val = taylor(cas, p.x, n); px = [p.x]; }
      var exact = apF(cas, p.x), cx = grid(p.xa, p.xb, 60), cy;
      if (meth === 1) cy = mapf(cx, function (z) { return lagrange(cas, z, p, n)[0]; });
      else cy = mapf(cx, function (z) { return taylor(cas, z, n); });
      return { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: n,
        cx: cx, ce: mapf(cx, function (z) { return apF(cas, z); }), cy: cy,
        px: px, py: mapf(px, function (z) { return apF(cas, z); }) };
    },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s) { return Object.assign({}, s); },
    measure: function (p) { var s = CpApprox.init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
  };


  // ====================================================================================== second-order IVP
  function ode2Rates(p) { return [p.cc / (2 * p.mm), Math.sqrt(p.kk / p.mm)]; }
  function ode2Exact(t, p) {
    var gw = ode2Rates(p), g = gw[0], w0 = gw[1], x0 = p.x0, wd, rt, rp, rm, A, B;
    if (g <= 1e-12 * Math.max(w0, 1.0)) return x0 * Math.cos(w0 * t);
    if (Math.abs(g - w0) <= 1e-8 * w0) return x0 * Math.exp(-g * t) * (1 + g * t);
    if (g < w0) { wd = Math.sqrt(w0 * w0 - g * g); return x0 * Math.exp(-g * t) * (Math.cos(wd * t) + (g / wd) * Math.sin(wd * t)); }
    rt = Math.sqrt(g * g - w0 * w0); rp = -g + rt; rm = -g - rt;
    A = -x0 * rm / (rp - rm); B = x0 * rp / (rp - rm);
    return A * Math.exp(rp * t) + B * Math.exp(rm * t);
  }
  function ode2Amp(p) {
    var gw = ode2Rates(p), g = gw[0], w0 = gw[1], w = p.wf;
    return (p.FF / p.mm) / Math.sqrt(Math.pow(w0 * w0 - w * w, 2) + Math.pow(2 * g * w, 2));
  }
  function ode2Truth(p) { return I(p.cas) === 1 ? ode2Amp(p) : ode2Exact(p.tmax, p); }
  var CpOde2 = {
    PARAMS: { cas: 0.0, method: 2.0, n: 200.0, mm: 1.0, cc: 0.0, kk: 4.0, FF: 0.0, wf: 1.0, x0: 0.1, tmax: 10.0 },
    VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'],
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), n = Math.max(2, I(p.n)), h = p.tmax / n;
      var m = p.mm, c = p.cc, k = p.kk, F = p.FF, wf = p.wf, i, k1, k2, k3, k4, d, t0, amp, val, exact, ce = null;
      var f = function (t, y) { return [y[1], (F * Math.cos(wf * t) - c * y[1] - k * y[0]) / m]; };
      var y = [p.x0, 0.0], t = 0.0, px = [0.0], py = [y[0]];
      for (i = 0; i < n; i++) {
        if (meth === 0) { d = f(t, y); y = [y[0] + h * d[0], y[1] + h * d[1]]; }
        else if (meth === 1) {
          k1 = f(t, y); k2 = f(t + h, [y[0] + h * k1[0], y[1] + h * k1[1]]);
          y = [y[0] + h * 0.5 * (k1[0] + k2[0]), y[1] + h * 0.5 * (k1[1] + k2[1])];
        } else {
          k1 = f(t, y);
          k2 = f(t + h / 2, [y[0] + h / 2 * k1[0], y[1] + h / 2 * k1[1]]);
          k3 = f(t + h / 2, [y[0] + h / 2 * k2[0], y[1] + h / 2 * k2[1]]);
          k4 = f(t + h, [y[0] + h * k3[0], y[1] + h * k3[1]]);
          y = [y[0] + h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]),
            y[1] + h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])];
        }
        t += h; px.push(t); py.push(y[0]);
      }
      if (cas === 1) {
        t0 = p.tmax * 0.8; amp = 0.0;
        for (i = 0; i < px.length; i++) if (px[i] >= t0 && Math.abs(py[i]) > amp) amp = Math.abs(py[i]);
        val = amp; exact = ode2Amp(p);
        ce = []; for (i = 0; i < 61; i++) ce.push(ode2Amp(p));
      } else { val = y[0]; exact = ode2Exact(p.tmax, p); }
      var cx = grid(0.0, p.tmax, 60);
      if (ce === null) ce = mapf(cx, function (z) { return ode2Exact(z, p); });
      return { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: n,
        cx: cx, ce: ce, cy: py.slice(), px: px.slice(), py: py.slice() };
    },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s) { return Object.assign({}, s); },
    measure: function (p) { var s = CpOde2.init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
  };

  // ====================================================================================== Monte Carlo
  var LCG_M = 2147483647;
  function lcg(seed) { var s = I(seed) % LCG_M; return [s > 0 ? s : 1]; }
  function uni(st) { st[0] = (st[0] * 16807.0) % LCG_M; return st[0] / LCG_M; }
  function gauss2(st) {
    var u1 = uni(st), u2 = uni(st), r = Math.sqrt(-2.0 * Math.log(u1 > 1e-300 ? u1 : 1e-300));
    return [r * Math.cos(2 * PI * u2), r * Math.sin(2 * PI * u2)];
  }
  function binom(m, kk) {
    var c = 1.0, i;
    for (i = 1; i <= kk; i++) c = c * (m - kk + i) / i;
    return c / Math.pow(2.0, m);
  }
  function mcExact(p) {
    var cas = I(p.cas), sx, sy, rho, x0, y0;
    if (cas === 1) return Math.E - 1.0;
    if (cas === 2) return 0.5;
    if (cas === 3) return binom(I(p.mtoss), I(p.khead));
    if (cas === 4) return 1.0 / Math.sqrt(12.0 * I(p.mtoss));
    if (cas === 5) return 1.0 / p.rate;
    if (cas === 6) {
      sx = p.sx; sy = p.sy; rho = p.rho; x0 = p.mx; y0 = p.my;
      return Math.sqrt(y0 * y0 * sx * sx + x0 * x0 * sy * sy + 2 * x0 * y0 * rho * sx * sy);
    }
    return PI;
  }
  function mcRun(p, N, marks) {
    var cas = I(p.cas), st = lcg(p.seed), hit = 0.0, tot = 0.0, sq = 0.0, out = [], mi = 0;
    var m = Math.max(1, I(p.mtoss)), kk = I(p.khead), i, j, est = 0.0, x, y, h, g, v, z, xx, yy, fv;
    for (i = 1; i <= N; i++) {
      if (cas === 0) {
        x = uni(st); y = uni(st);
        if (x * x + y * y <= 1.0) hit += 1;
        est = 4.0 * hit / i;
      } else if (cas === 1) { tot += Math.exp(uni(st)); est = tot / i; }
      else if (cas === 2) { tot += uni(st); est = tot / i; }
      else if (cas === 3) {
        h = 0;
        for (j = 0; j < m; j++) if (uni(st) < 0.5) h += 1;
        if (h === kk) hit += 1;
        est = hit / i;
      } else if (cas === 4) {
        g = 0.0;
        for (j = 0; j < m; j++) g += uni(st);
        g = g / m; tot += g; sq += g * g;
        v = sq / i - (tot / i) * (tot / i);
        est = Math.sqrt(v > 0 ? v : 0.0);
      } else if (cas === 5) { tot += -Math.log(uni(st)) / p.rate; est = tot / i; }
      else {
        z = gauss2(st);
        xx = p.mx + p.sx * z[0];
        yy = p.my + p.sy * (p.rho * z[0] + Math.sqrt(1 - p.rho * p.rho) * z[1]);
        fv = xx * yy; tot += fv; sq += fv * fv;
        v = sq / i - (tot / i) * (tot / i);
        est = Math.sqrt(v > 0 ? v : 0.0);
      }
      while (mi < marks.length && marks[mi] === i) { out.push(est); mi++; }
    }
    while (out.length < marks.length) out.push(N > 0 ? est : 0.0);
    return [est, out];
  }
  function mcMarks(N) {
    var out = [], i, v;
    for (i = 1; i <= 60; i++) {
      v = I(Math.pow(N, i / 60.0));
      if (v < 1) v = 1;
      if (!out.length || v > out[out.length - 1]) out.push(v);
    }
    return out;
  }
  var CpMonteCarlo = {
    PARAMS: { cas: 0.0, method: 0.0, n: 4000.0, seed: 12345.0, mtoss: 10.0, khead: 5.0, rate: 0.5,
      mx: 4.0, my: 2.5, sx: 0.08, sy: 0.05, rho: 0.0 },
    VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'],
    init: function (p) {
      var N = Math.max(10, I(p.n)), marks = mcMarks(N), r = mcRun(p, N, marks), val = r[0], run = r[1];
      var exact = mcExact(p), cx = marks.slice(), i;
      for (i = 0; i < cx.length; i++) cx[i] = cx[i];
      return { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: N,
        cx: cx, ce: mapf(cx, function () { return exact; }), cy: run.slice(), px: [cx[cx.length - 1]], py: [val] };
    },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s) { return Object.assign({}, s); },
    measure: function (p) { var s = CpMonteCarlo.init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
  };

  // ====================================================================================== projectile
  function projExact(p) {
    var cas = I(p.cas), u = p.u, th = p.th, g = p.g;
    if (cas === 1) return u * u * Math.sin(th) * Math.sin(th) / (2 * g);
    if (cas === 2) return 2 * u * Math.sin(th) / g;
    return u * u * Math.sin(2 * th) / g;
  }
  var CpProjectile = {
    PARAMS: { cas: 0.0, method: 2.0, n: 100.0, u: 30.0, th: 0.7854, g: 9.8 },
    VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py', 'tflight', 'hmax', 'range_m'],
    init: function (p) {
      var cas = I(p.cas), meth = I(p.method), n = Math.max(4, I(p.n)), u = p.u, th = p.th, g = p.g;
      var tend = 2 * u * Math.sin(th) / g, h = (tend * 1.2) / n, i, j, k1, k2, k3, k4, d, prev, fr, tmp;
      var f = function (y) { return [y[2], y[3], 0.0, -g]; };
      var y = [0.0, 0.0, u * Math.cos(th), u * Math.sin(th)], px = [0.0], py = [0.0];
      var hmax = 0.0, tf = 0.0, rng = 0.0, t = 0.0;
      for (i = 0; i < n; i++) {
        prev = y.slice();
        if (meth === 0) { d = f(y); tmp = []; for (j = 0; j < 4; j++) tmp[j] = y[j] + h * d[j]; y = tmp; }
        else if (meth === 1) {
          k1 = f(y); tmp = []; for (j = 0; j < 4; j++) tmp[j] = y[j] + h * k1[j];
          k2 = f(tmp); tmp = []; for (j = 0; j < 4; j++) tmp[j] = y[j] + h * 0.5 * (k1[j] + k2[j]); y = tmp;
        } else {
          k1 = f(y); tmp = []; for (j = 0; j < 4; j++) tmp[j] = y[j] + h / 2 * k1[j];
          k2 = f(tmp); tmp = []; for (j = 0; j < 4; j++) tmp[j] = y[j] + h / 2 * k2[j];
          k3 = f(tmp); tmp = []; for (j = 0; j < 4; j++) tmp[j] = y[j] + h * k3[j];
          k4 = f(tmp); tmp = [];
          for (j = 0; j < 4; j++) tmp[j] = y[j] + h / 6 * (k1[j] + 2 * k2[j] + 2 * k3[j] + k4[j]);
          y = tmp;
        }
        t += h;
        if (y[1] > hmax) hmax = y[1];
        if (prev[1] >= 0 && y[1] < 0 && tf === 0.0) {
          fr = prev[1] / (prev[1] - y[1]);
          tf = t - h + fr * h;
          rng = prev[0] + fr * (y[0] - prev[0]);
        }
        if (tf === 0.0 || px.length < 2) { px.push(y[0]); py.push(y[1]); }
      }
      if (tf === 0.0) { tf = t; rng = y[0]; }
      var val = cas === 1 ? hmax : cas === 2 ? tf : rng;
      var exact = projExact(p), q = Object.assign({}, p); q.cas = 0.0;
      var R = projExact(q), cx = grid(0.0, R, 60);
      var ce = mapf(cx, function (z) { return z * Math.tan(th) - g * z * z / (2 * u * u * Math.cos(th) * Math.cos(th)); });
      return { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: n,
        cx: cx, ce: ce, cy: [], px: px.slice(), py: py.slice(), tflight: tf, hmax: hmax, range_m: rng };
    },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s) { return Object.assign({}, s); },
    measure: function (p) { var s = CpProjectile.init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
  };

  root.HoolaKernels.register({
    K: { cp_root: CpRoot, cp_quad: CpQuad, cp_ode1: CpOde1, cp_diff: CpDiff, cp_approx: CpApprox,
      cp_ode2: CpOde2, cp_mc: CpMonteCarlo, cp_proj: CpProjectile },
    TEXTBOOK: {
      cp_root_x: rootExact, cp_quad_I: quadExact, cp_diff_d: fdExact,
      cp_ode1_y: function (p) { return ode1Exact(I(p.cas), p.tmax, p); },
      cp_approx_f: function (p) { return apF(I(p.cas), p.x); },
      cp_ode2_x: ode2Truth, cp_mc_v: mcExact, cp_proj_v: projExact
    },
    CALCS: {
      cp_best: { label: 'best value', unit: '', needs: ['n', 'val'],
        fn: function (r) { var rs = rows(r, ['n', 'val']), i, best; if (!rs.length) return 0; best = rs[0];
          for (i = 0; i < rs.length; i++) if (rs[i][0] > best[0]) best = rs[i]; return best[1]; } },
      cp_order: { label: 'order of the method', unit: '', needs: ['n', 'err'],
        fn: function (r) { var rs = rows(r, ['n', 'err']), pts = [], i, sx = 0, sy = 0, sxx = 0, sxy = 0, den;
          for (i = 0; i < rs.length; i++) if (rs[i][0] > 0 && rs[i][1] > 0) pts.push([Math.log(rs[i][0]), Math.log(rs[i][1])]);
          if (pts.length < 2) return 0;
          for (i = 0; i < pts.length; i++) { sx += pts[i][0]; sy += pts[i][1]; sxx += pts[i][0] * pts[i][0]; sxy += pts[i][0] * pts[i][1]; }
          den = pts.length * sxx - sx * sx; if (Math.abs(den) < 1e-30) return 0;
          return -(pts.length * sxy - sx * sy) / den; } },
      cp_mean_val: { label: 'mean value', unit: '', needs: ['val'],
        fn: function (r) { var rs = rows(r, ['val']), xs = [], i; for (i = 0; i < rs.length; i++) xs.push(rs[i][0]); return mean(xs); } }
    }
  });
})(typeof window !== 'undefined' ? window : this);
