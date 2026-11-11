/* Hoola Prayogshala kernels (v0.415): the TRUE behaviour of every lab, run on the learner's phone.
   Twin of server/app/prayog/kernels.py - the same algorithms step for step; the server's tests run both on the same
   inputs and demand the same numbers. Change one, change the other. No network, no model-written code. */
(function (root) {
  'use strict';
  var PI = Math.PI, MU0 = 4e-7 * PI, H = 0.0005, VT = 0.025852;
  function assign(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; if (b) for (k in b) o[k] = b[k]; return o; }

  function rk4(f, y, h) {
    var n = y.length, i, k1 = f(y), t = [], k2, k3, k4, out = [];
    for (i = 0; i < n; i++) t[i] = y[i] + h / 2 * k1[i]; k2 = f(t); t = [];
    for (i = 0; i < n; i++) t[i] = y[i] + h / 2 * k2[i]; k3 = f(t); t = [];
    for (i = 0; i < n; i++) t[i] = y[i] + h * k3[i]; k4 = f(t);
    for (i = 0; i < n; i++) out[i] = y[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]);
    return out;
  }
  function sub(dt, h) { var n = Math.max(1, Math.ceil(dt / h - 1e-9)); return [n, dt / n]; }
  function period(f, y0, h, tmax) {
    var y = y0.slice(), t = 0, cross = [], y2;
    while (t < tmax && cross.length < 2) {
      y2 = rk4(f, y, h);
      if (y[0] > 0 && 0 >= y2[0]) cross.push(t + h * y[0] / (y[0] - y2[0]));
      y = y2; t = t + h;
    }
    return cross.length === 2 ? cross[1] - cross[0] : 0;
  }
  function loop(s, dt, h, f) { var q = sub(dt, h), i; for (i = 0; i < q[0]; i++) s.y = rk4(f, s.y, q[1]); s.t += dt; }
  function noStep(s, p, dt) { s.t += dt; }
  function t0() { return { t: 0 }; }

  var K = {};

  // ------------------------------------------------------------------ mechanics
  function pendF(p) { var g = p.g, L = p.L, b = p.b; return function (y) { return [y[1], -(g / L) * Math.sin(y[0]) - b * y[1]]; }; }
  K.pendulum = {
    PARAMS: { L: 1.0, g: 9.8, theta0: 0.0873, b: 0.0 }, VARS: ['t', 'theta', 'bob_x', 'bob_y', 'omega'],
    init: function (p) { return { t: 0, y: [p.theta0, 0] }; },
    step: function (s, p, dt) { loop(s, dt, 0.002, pendF(p)); },
    view: function (s, p) { var th = s.y[0]; return { t: s.t, theta: th, omega: s.y[1], bob_x: p.L * Math.sin(th), bob_y: -p.L * Math.cos(th) }; },
    measure: function (p) { return { T: period(pendF(p), [p.theta0, 0], H, 60) }; }
  };

  function springF(p) { var k = p.k, m = p.m, c = p.c; return function (y) { return [y[1], -(k / m) * y[0] - (c / m) * y[1]]; }; }
  K.spring = {
    PARAMS: { k: 20.0, m: 0.2, c: 0.0, g: 9.8, x0: 0.03, L0: 0.15 }, VARS: ['t', 'x', 'ext', 'bob_y', 'v'],
    init: function (p) { return { t: 0, y: [p.x0, 0] }; },
    step: function (s, p, dt) { loop(s, dt, 0.002, springF(p)); },
    view: function (s, p) { var ext = p.m * p.g / p.k + s.y[0]; return { t: s.t, x: s.y[0], v: s.y[1], ext: ext, bob_y: -(p.L0 + ext) }; },
    measure: function (p) {
      var T = period(springF(p), [p.x0, 0], H, 60), q = assign(p, { c: 2 * Math.sqrt(p.k * p.m) }), y = [p.x0, 0], t = 0, f = springF(q);
      while (t < 20.0) { y = rk4(f, y, 0.002); t += 0.002; }
      return { T: T, ext: p.m * p.g / p.k + y[0] };
    }
  };

  function inclAdv(s, p, h) {
    var m = p.m, g = p.g, th = p.angle, mu = p.mu, F = p.F, drive = F - m * g * Math.sin(th), fr = mu * m * g * Math.cos(th), a, v2;
    if (s.v === 0) {
      if (Math.abs(drive) <= fr) { s.a = 0; return; }
      a = (drive - fr * (drive > 0 ? 1 : -1)) / m;
    } else a = (drive - fr * (s.v > 0 ? 1 : -1)) / m;
    v2 = s.v + a * h;
    if (s.v !== 0 && (v2 > 0) !== (s.v > 0)) { s.s += a !== 0 ? s.v * s.v / (-2 * a) : 0; s.v = 0; s.a = 0; return; }
    s.s += s.v * h + 0.5 * a * h * h; s.v = v2; s.a = a;
    if (s.s <= 0 || s.s >= p.len) { s.s = Math.min(Math.max(s.s, 0), p.len); s.v = 0; s.a = 0; }
  }
  function inclMoves(p, F) {
    var q = assign(p, { F: F, len: 1e6 }), s = { t: 0, s: 1, v: 0, a: 0 }, i;
    for (i = 0; i < 250; i++) inclAdv(s, q, 0.002);
    return s.s > 1 + 1e-9;
  }
  K.incline = {
    PARAMS: { angle: 0.5236, mu: 0.3, m: 1.0, F: 0.0, g: 9.8, len: 1.5 }, VARS: ['t', 's', 'v', 'a', 'px', 'py', 'moving'],
    init: function (p) { return { t: 0, s: p.len * 0.2, v: 0, a: 0 }; },
    step: function (s, p, dt) { var q = sub(dt, 0.002), i; for (i = 0; i < q[0]; i++) inclAdv(s, p, q[1]); s.t += dt; },
    view: function (s, p) { return { t: s.t, s: s.s, v: s.v, a: s.a, px: s.s * Math.cos(p.angle), py: s.s * Math.sin(p.angle), moving: s.v !== 0 ? 1 : 0 }; },
    measure: function (p) {
      var lo = 0, hi = 4 * p.m * p.g + 1, i, mid, q, s;
      for (i = 0; i < 60; i++) { mid = (lo + hi) / 2; if (inclMoves(p, mid)) hi = mid; else lo = mid; }
      q = assign(p, { len: 1e6 }); s = { t: 0, s: 1, v: 0, a: 0 };
      for (i = 0; i < 500; i++) inclAdv(s, q, 0.002);
      return { F_min: hi, a: 2 * (s.s - 1) };
    }
  };

  function stokesF(p) { var a0 = p.g * (1 - p.sigma / p.rho), b = 9 * p.eta / (2 * p.rho * p.r ** 2); return function (y) { return [y[1], a0 - b * y[1]]; }; }
  function stokesH(p) { var tau = 2 * p.rho * p.r ** 2 / (9 * p.eta); return [Math.min(0.002, tau / 20), tau]; }
  K.stokes = {
    PARAMS: { r: 0.001, rho: 7800.0, sigma: 1260.0, eta: 1.49, g: 9.8, depth: 0.8 }, VARS: ['t', 'y', 'v', 'ball_y'],
    init: function () { return { t: 0, y: [0, 0] }; },
    step: function (s, p, dt) {
      if (s.y[0] >= p.depth) { s.t += dt; return; }
      var q = sub(dt, stokesH(p)[0]), f = stokesF(p), i;
      for (i = 0; i < q[0]; i++) s.y = rk4(f, s.y, q[1]);
      if (s.y[0] >= p.depth) s.y = [p.depth, 0];
      s.t += dt;
    },
    view: function (s) { return { t: s.t, y: s.y[0], v: s.y[1], ball_y: -s.y[0] }; },
    measure: function (p) {
      var hh = stokesH(p), h = hh[0], tau = hh[1], y = [0, 0], t = 0, f = stokesF(p);
      while (t < 40 * tau + 0.01) { y = rk4(f, y, h); t += h; }
      return { v_t: y[1] };
    }
  };

  // ------------------------------------------------------------------ heat
  K.cooling = {
    PARAMS: { T0: 90.0, Ts: 30.0, k: 0.02 }, VARS: ['t', 'T'],
    init: function (p) { return { t: 0, y: [p.T0] }; },
    step: function (s, p, dt) { loop(s, dt, 0.05, function (y) { return [-p.k * (y[0] - p.Ts)]; }); },
    view: function (s) { return { t: s.t, T: s.y[0] }; },
    measure: function (p) { var s = K.cooling.init(p), i; for (i = 0; i < 60; i++) K.cooling.step(s, p, 1.0); return { T60: s.y[0] }; }
  };
  K.boyle = {
    PARAMS: { n: 0.004, Temp: 300.0, V: 1e-4, R: 8.314, area: 1e-3 }, VARS: ['P', 'P_kPa', 'V_mL', 'PV', 'piston_h'],
    init: t0, step: noStep,
    view: function (s, p) { var P = p.n * p.R * p.Temp / p.V; return { P: P, P_kPa: P / 1000, V_mL: p.V * 1e6, PV: P * p.V, piston_h: p.V / p.area }; },
    measure: function (p) { return { P: K.boyle.view({}, p).P }; }
  };
  function mixF(p) {
    var C1 = p.m1 * p.c1, C2 = p.m2 * p.c2 + p.mc * p.cc;
    return function (y) { return [-p.hA * (y[0] - y[1]) / C1, p.hA * (y[0] - y[1]) / C2]; };
  }
  K.mixtures = {
    PARAMS: { m1: 0.1, c1: 900.0, T1: 100.0, m2: 0.15, c2: 4186.0, T2: 25.0, mc: 0.05, cc: 385.0, hA: 5.0 }, VARS: ['t', 'Ts', 'Tw'],
    init: function (p) { return { t: 0, y: [p.T1, p.T2] }; },
    step: function (s, p, dt) { loop(s, dt, 0.1, mixF(p)); },
    view: function (s) { return { t: s.t, Ts: s.y[0], Tw: s.y[1] }; },
    measure: function (p) {
      var y = [p.T1, p.T2], t = 0, f = mixF(p);
      while (t < 3000.0 && Math.abs(y[0] - y[1]) > 1e-7) { y = rk4(f, y, 0.1); t += 0.1; }
      return { Tf: y[1] };
    }
  };

  // ------------------------------------------------------------------ waves
  function soundV(Tc) { return 331.3 * Math.sqrt(1 + Tc / 273.15); }
  function resLoud(p, h) { var k = 2 * PI * p.f / soundV(p.Tc), c = Math.cos(k * (h + 0.3 * p.d)); return p.damp / Math.sqrt(c * c + p.damp * p.damp); }
  K.resonance = {
    PARAMS: { f: 512.0, Tc: 20.0, d: 0.04, h: 0.12, damp: 0.03 }, VARS: ['loud', 'h', 'v', 'lambda', 'water_y'],
    init: t0, step: noStep,
    view: function (s, p) { var v = soundV(p.Tc); return { loud: resLoud(p, p.h), h: p.h, v: v, lambda: v / p.f, water_y: -p.h }; },
    measure: function (p) {
      var peaks = [], prev2 = 0, prev = 0, i = 0, h, cur;
      while (peaks.length < 2 && i < 20000) {
        h = 0.005 + i * 1e-4; cur = resLoud(p, h);
        if (i >= 2 && prev > prev2 && prev >= cur) peaks.push(h - 1e-4);
        prev2 = prev; prev = cur; i = i + 1;
      }
      if (peaks.length < 2) return { l1: 0, l2: 0, v_meas: 0 };
      return { l1: peaks[0], l2: peaks[1], v_meas: 2 * p.f * (peaks[1] - peaks[0]) };
    }
  };
  function sonoFw(p, l) { return Math.sqrt(p.Tn / p.mu) / (2 * l); }
  function sonoLoud(p, l) { var x = (sonoFw(p, l) ** 2 - p.f ** 2) / (p.f ** 2); return p.damp / Math.sqrt(x * x + p.damp * p.damp); }
  K.sonometer = {
    PARAMS: { Tn: 39.2, mu: 0.001, f: 256.0, l: 0.3, damp: 0.01 }, VARS: ['loud', 'fw', 'l', 'amp'],
    init: t0, step: noStep,
    view: function (s, p) { var loud = sonoLoud(p, p.l); return { loud: loud, fw: sonoFw(p, p.l), l: p.l, amp: 0.012 * loud * Math.sin(40 * s.t) }; },
    measure: function (p) {
      var best = -1, bl = 0, i = 0, l, v;
      while (i <= 95000) { l = 0.05 + i * 1e-5; v = sonoLoud(p, l); if (v > best) { best = v; bl = l; } i += 1; }
      return { l_res: bl };
    }
  };

  // ------------------------------------------------------------------ circuits (MNA)
  function val(spec, p) {
    if (typeof spec === 'number') return spec;
    if (typeof spec === 'string') return +p[spec];
    return +(spec.c || 0) + (spec.k === undefined ? 1 : +spec.k) * +p[spec.param];
  }
  function solve(A, b) {
    var n = b.length, M = [], c, r, k, piv, fct, tmp, x = [], acc;
    for (r = 0; r < n; r++) M.push(A[r].slice().concat([b[r]]));
    for (c = 0; c < n; c++) {
      piv = c;
      for (r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r;
      if (Math.abs(M[piv][c]) < 1e-300) throw new Error('circuit is not solvable (a node floats)');
      tmp = M[c]; M[c] = M[piv]; M[piv] = tmp;
      for (r = c + 1; r < n; r++) {
        fct = M[r][c] / M[c][c];
        if (fct !== 0) for (k = c; k < n + 1; k++) M[r][k] -= fct * M[c][k];
      }
    }
    for (r = n - 1; r >= 0; r--) { acc = M[r][n]; for (k = r + 1; k < n; k++) acc -= M[r][k] * x[k]; x[r] = acc / M[r][r]; }
    return x;
  }
  function node(s, i) { return i ? s.x[i - 1] : 0; }
  function solveAt(s, p, cfg, h) {
    var net = cfg.net, nn = net.nodes, els = net.els, nvs = 0, i, it, e, j, size, A, b, x = [], vd = {}, guess = s.vd || {}, worst, va, vb, nw, old, st;
    for (i = 0; i < els.length; i++) { if (els[i].kind === 'V') nvs++; if (els[i].kind === 'D') vd[els[i].id] = guess[els[i].id] !== undefined ? guess[els[i].id] : 0.6; }
    size = nn + nvs;
    var hasD = Object.keys(vd).length > 0;
    function g(a, bn, G) {
      if (a) A[a - 1][a - 1] += G;
      if (bn) A[bn - 1][bn - 1] += G;
      if (a && bn) { A[a - 1][bn - 1] -= G; A[bn - 1][a - 1] -= G; }
    }
    function inj(a, bn, I) { if (a) b[a - 1] -= I; if (bn) b[bn - 1] += I; }
    for (it = 0; it < 200; it++) {
      A = []; b = [];
      for (i = 0; i < size; i++) { A.push(new Array(size).fill(0)); b.push(0); }
      for (i = 0; i < nn; i++) A[i][i] += 1e-12;
      j = 0;
      for (i = 0; i < els.length; i++) {
        e = els[i];
        var k = e.kind, a = e.a, bn = e.b, G, Is, nv, v0, ex, Gd, Id, r;
        if (k === 'R') g(a, bn, 1.0 / Math.max(val(e.value, p), 1e-9));
        else if (k === 'S') g(a, bn, +p[e.param] >= 0.5 ? 1e6 : 1e-12);
        else if (k === 'C') {
          if (h > 0) { G = val(e.value, p) / h; g(a, bn, G); inj(a, bn, -G * s.vc[e.id]); } else g(a, bn, 1e-12);
        } else if (k === 'D') {
          Is = val(e.Is !== undefined ? e.Is : 1e-12, p); nv = val(e.n !== undefined ? e.n : 1.8, p) * VT; v0 = vd[e.id];
          ex = Math.exp(Math.min(v0 / nv, 80.0)); Gd = Is / nv * ex + 1e-12; Id = Is * (ex - 1);
          g(a, bn, Gd); inj(a, bn, Id - Gd * v0);
        } else if (k === 'V') {
          r = nn + j;
          if (a) { A[a - 1][r] += 1.0; A[r][a - 1] += 1.0; }
          if (bn) { A[bn - 1][r] -= 1.0; A[r][bn - 1] -= 1.0; }
          b[r] = val(e.value, p); j += 1;
        }
      }
      x = solve(A, b);
      if (!hasD) break;
      worst = 0;
      for (i = 0; i < els.length; i++) {
        e = els[i]; if (e.kind !== 'D') continue;
        va = e.a ? x[e.a - 1] : 0; vb = e.b ? x[e.b - 1] : 0; nw = va - vb; old = vd[e.id];
        st = Math.max(-0.1, Math.min(0.1, nw - old)); vd[e.id] = old + st;
        worst = Math.max(worst, Math.abs(nw - old));
      }
      if (worst < 1e-12) break;
    }
    s.x = x; s.vd = vd; s.h = h;
  }
  K.circuit = {
    PARAMS: {},
    vars: function (cfg) {
      var out = ['t'], i, els = cfg.net.els;
      for (i = 0; i < els.length; i++) out.push('I_' + els[i].id, 'V_' + els[i].id);
      for (i = 0; i <= cfg.net.nodes; i++) out.push('N_' + i);
      return out;
    },
    init: function (p, cfg) {
      var s = { t: 0, vc: {}, x: null, ic: {} }, i, els = cfg.net.els;
      for (i = 0; i < els.length; i++) if (els[i].kind === 'C') s.vc[els[i].id] = 0;
      solveAt(s, p, cfg, 0); return s;
    },
    step: function (s, p, dt, cfg) {
      if (!Object.keys(s.vc).length) { solveAt(s, p, cfg, 0); s.t += dt; return; }
      var q = sub(dt, 0.0005), n, i, e, vnew, els = cfg.net.els;
      for (n = 0; n < q[0]; n++) {
        solveAt(s, p, cfg, q[1]);
        for (i = 0; i < els.length; i++) {
          e = els[i];
          if (e.kind === 'C') { vnew = node(s, e.a) - node(s, e.b); s.ic[e.id] = val(e.value, p) * (vnew - s.vc[e.id]) / q[1]; s.vc[e.id] = vnew; }
        }
      }
      s.t += dt;
    },
    view: function (s, p, cfg) {
      var net = cfg.net, nn = net.nodes, j = 0, i, e, v, cur, out = { t: s.t }, Is, nv;
      if (s.x === null) solveAt(s, p, cfg, 0);
      if (!Object.keys(s.vc).length) solveAt(s, p, cfg, 0);
      for (i = 0; i <= nn; i++) out['N_' + i] = node(s, i);
      for (i = 0; i < net.els.length; i++) {
        e = net.els[i]; v = node(s, e.a) - node(s, e.b);
        if (e.kind === 'R') cur = v / Math.max(val(e.value, p), 1e-9);
        else if (e.kind === 'S') cur = v * (+p[e.param] >= 0.5 ? 1e6 : 1e-12);
        else if (e.kind === 'C') cur = s.ic[e.id] !== undefined ? s.ic[e.id] : 0;
        else if (e.kind === 'D') { Is = val(e.Is !== undefined ? e.Is : 1e-12, p); nv = val(e.n !== undefined ? e.n : 1.8, p) * VT; cur = Is * (Math.exp(Math.min(v / nv, 80.0)) - 1); }
        else { cur = -s.x[nn + j]; j += 1; }
        out['I_' + e.id] = cur; out['V_' + e.id] = v;
      }
      return out;
    },
    measure: function (p, cfg) {
      var m = cfg.measure || { mode: 'value' }, lo, hi, flo, i, mid, fm, s, vw, out = {}, fin, frac, pt, pv, v;
      if (m.mode === 'null') {
        lo = m.lo !== undefined ? +m.lo : 0.01; hi = m.hi !== undefined ? +m.hi : 0.99;
        var cur = function (x) { var q = assign(p), st; q[m.param] = x; st = K.circuit.init(q, cfg); return K.circuit.view(st, q, cfg)[m['var']]; };
        flo = cur(lo);
        for (i = 0; i < 60; i++) { mid = (lo + hi) / 2; fm = cur(mid); if ((fm > 0) === (flo > 0)) { lo = mid; flo = fm; } else hi = mid; }
        out[m.param] = (lo + hi) / 2; return out;
      }
      if (m.mode === 'time_to') {
        s = K.circuit.init(p, cfg); fin = +m.final; frac = m.frac !== undefined ? +m.frac : 0.632;
        pt = 0; pv = K.circuit.view(s, p, cfg)[m['var']];
        while (s.t < (m.tmax !== undefined ? +m.tmax : 60.0)) {
          K.circuit.step(s, p, 0.001, cfg); v = K.circuit.view(s, p, cfg)[m['var']];
          if (v >= frac * fin) { out['t_' + m['var']] = pt + 0.001 * (frac * fin - pv) / (v - pv); return out; }
          pt = s.t; pv = v;
        }
        out['t_' + m['var']] = 0; return out;
      }
      s = K.circuit.init(p, cfg); vw = K.circuit.view(s, p, cfg);
      (m.vars || []).forEach(function (k) { out[k] = vw[k]; });
      if (m.mode === 'ratio') out[m.as] = vw[m.den] !== 0 ? vw[m.num] / vw[m.den] : 0;
      return out;
    }
  };

  // ------------------------------------------------------------------ optics (2D, exact)
  function refract(d, n, n1, n2) {
    var cosi = -(d[0] * n[0] + d[1] * n[1]), r = n1 / n2, k = 1 - r * r * (1 - cosi * cosi), ct;
    if (k < 0) return null;
    ct = Math.sqrt(k);
    return [r * d[0] + (r * cosi - ct) * n[0], r * d[1] + (r * cosi - ct) * n[1]];
  }
  function circleHit(o, d, cx, R, nearLeft) {
    var ox = o[0] - cx, oy = o[1], bq = ox * d[0] + oy * d[1], cq = ox * ox + oy * oy - R * R, disc = bq * bq - cq, sq, ts, i, t, x;
    if (disc < 0) return null;
    sq = Math.sqrt(disc); ts = [-bq - sq, -bq + sq];
    for (i = 0; i < 2; i++) { t = ts[i]; if (t > 1e-12) { x = o[0] + t * d[0]; if ((x < cx) === nearLeft) return [x, o[1] + t * d[1]]; } }
    return null;
  }
  function norm(v) { var L = Math.hypot(v[0], v[1]); return [v[0] / L, v[1] / L]; }
  function sharp(scr, imgX) { var q; if (imgX <= 0) return 0; q = (scr - imgX) / 0.004; return 1 / (1 + q * q); }
  function meet(p1, d1, p2, d2) {
    var den = d1[0] * d2[1] - d1[1] * d2[0], t;
    if (Math.abs(den) < 1e-18) return null;
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den;
    return [p1[0] + t * d1[0], p1[1] + t * d1[1]];
  }
  function mirTrace(p, yAim) {
    var R = p.R, cx = p.convex < 0.5 ? R : -R, o = [p.u, p.h], d = norm([0 - o[0], yAim - o[1]]), hit = circleHit(o, d, cx, R, cx > 0), n, dot;
    if (hit === null) return null;
    n = norm([hit[0] - cx, hit[1]]); dot = d[0] * n[0] + d[1] * n[1];
    return [o, hit, [d[0] - 2 * dot * n[0], d[1] - 2 * dot * n[1]]];
  }
  function mirImage(p) { var a = mirTrace(p, -1e-4), b = mirTrace(p, 1e-4); if (!a || !b) return null; return meet(a[1], a[2], b[1], b[2]); }
  K.mirror = {
    PARAMS: { R: 0.3, u: 0.45, h: 0.03, convex: 0.0, scr: 0.3 }, VARS: ['rays', 'img_x', 'img_h', 'real', 'f', 'sharp'],
    init: t0, step: noStep,
    view: function (s, p) {
      var img = mirImage(p) || [0, 0], rays = [], aims = [p.h, 0, -p.h * 0.6], i, tr, o, hit, r, L = 2.0;
      for (i = 0; i < 3; i++) {
        tr = mirTrace(p, aims[i]); if (!tr) continue;
        o = tr[0]; hit = tr[1]; r = tr[2];
        rays.push({ p: [o, hit, [hit[0] + L * r[0], hit[1] + L * r[1]]], v: 0 });
        if (img[0] < 0) rays.push({ p: [hit, img], v: 1 });
      }
      return { rays: rays, img_x: img[0], img_h: img[1], real: img[0] > 0 ? 1 : 0, f: p.R / 2 * (p.convex < 0.5 ? 1 : -1), sharp: sharp(p.scr, img[0]) };
    },
    measure: function (p) { var q = assign(p, { h: 0.002 }), img = mirImage(q) || [0, 0]; return { v: img[0], m: img[1] / q.h }; }
  };
  function lensTrace(p, yAim) {
    var R = p.R, n = p.n, d = p.d, o = [-p.u, p.h], dr = norm([-d / 2 - o[0], yAim - o[1]]), c1 = -d / 2 + R, h1, d1, c2, h2, n2, d2;
    h1 = circleHit(o, dr, c1, R, true); if (h1 === null) return null;
    d1 = refract(dr, norm([h1[0] - c1, h1[1]]), 1.0, n); if (d1 === null) return null;
    c2 = d / 2 - R; h2 = circleHit(h1, d1, c2, R, false); if (h2 === null) return null;
    n2 = norm([h2[0] - c2, h2[1]]); d2 = refract(d1, [-n2[0], -n2[1]], n, 1.0); if (d2 === null) return null;
    return [o, h1, h2, d2];
  }
  function lensImage(p) { var a = lensTrace(p, -1e-4), b = lensTrace(p, 1e-4); if (!a || !b) return null; return meet(a[2], a[3], b[2], b[3]); }
  K.lens = {
    PARAMS: { R: 0.2, n: 1.5, d: 0.0025, u: 0.4, h: 0.03, ap: 0.04, scr: 0.3 }, VARS: ['rays', 'img_x', 'img_h', 'real', 'f', 'sharp'],
    init: t0, step: noStep,
    view: function (s, p) {
      var img = lensImage(p) || [0, 0], rays = [], edge = Math.sqrt(Math.max(p.R * p.d - p.d * p.d / 4, 0)) * 0.8, aims = [edge, 0, -edge], i, tr;
      for (i = 0; i < 3; i++) {
        tr = lensTrace(p, aims[i]); if (!tr) continue;
        rays.push({ p: [tr[0], tr[1], tr[2], [tr[2][0] + 2.0 * tr[3][0], tr[2][1] + 2.0 * tr[3][1]]], v: 0 });
        if (img[0] < 0) rays.push({ p: [tr[2], img], v: 1 });
      }
      return { rays: rays, img_x: img[0], img_h: img[1], real: img[0] > 0 ? 1 : 0, f: 1 / ((p.n - 1) * (2 / p.R)), sharp: sharp(p.scr, img[0]) };
    },
    measure: function (p) { var q = assign(p, { h: 0.002 }), img = lensImage(q) || [0, 0]; return { v: img[0], m: img[1] / q.h }; }
  };
  function prismAngles(p, i) {
    var r1 = Math.asin(Math.sin(i) / p.n), r2 = p.A - r1, x = p.n * Math.sin(r2), e;
    if (Math.abs(x) > 1) return null;
    e = Math.asin(x); return [r1, r2, e, i + e - p.A];
  }
  K.prism = {
    PARAMS: { A: 1.0472, n: 1.5, i: 0.8, side: 0.12 }, VARS: ['rays', 'dev', 'e', 'tir'],
    init: t0, step: noStep,
    view: function (s, p) {
      var A = p.A, S = p.side, apex = [0, S * Math.cos(A / 2)], br = [S * Math.sin(A / 2), 0], bl = [-S * Math.sin(A / 2), 0],
        ang = prismAngles(p, p.i), hit1 = [(apex[0] + bl[0]) / 2, (apex[1] + bl[1]) / 2], n1 = norm([-Math.cos(A / 2), Math.sin(A / 2)]),
        base = Math.atan2(-n1[1], -n1[0]) + p.i, din = [Math.cos(base), Math.sin(base)], start = [hit1[0] - 0.12 * din[0], hit1[1] - 0.12 * din[1]],
        d1, e2, hit2, n2, d2, end;
      if (ang === null) return { rays: [{ p: [start, hit1], v: 0 }], dev: 0, e: 0, tir: 1 };
      d1 = refract(din, n1, 1.0, p.n);
      e2 = [br[0] - apex[0], br[1] - apex[1]];
      hit2 = meet(hit1, d1, apex, e2) || hit1;
      n2 = norm([Math.cos(A / 2), Math.sin(A / 2)]);
      d2 = refract(d1, [-n2[0], -n2[1]], p.n, 1.0) || d1;
      end = [hit2[0] + 0.16 * d2[0], hit2[1] + 0.16 * d2[1]];
      return { rays: [{ p: [start, hit1, hit2, end], v: 0 }, { p: [hit1, [hit1[0] + 0.2 * din[0], hit1[1] + 0.2 * din[1]]], v: 1 }], dev: ang[3], e: ang[2], tir: 0 };
    },
    measure: function (p) {
      var best = 10.0, bi = 0, k = 0, i, a;
      while (k <= 6000) { i = (25 + k * 0.01) * PI / 180; a = prismAngles(p, i); if (a !== null && a[3] < best) { best = a[3]; bi = i; } k += 1; }
      return { dm: best, i_min: bi };
    }
  };
  function slabApp(p, ang) {
    var o = [0, -p.t], d = [Math.sin(ang), Math.cos(ang)], hit = [o[0] + p.t * Math.tan(ang), 0], out = refract(d, [0, -1], p.n, 1.0), k;
    if (out === null || Math.abs(out[0]) < 1e-18) return [null, hit, out];
    k = -hit[0] / out[0]; return [hit[1] + k * out[1], hit, out];
  }
  K.slab = {
    PARAMS: { t: 0.05, n: 1.5 }, VARS: ['rays', 'app', 'shift'],
    init: t0, step: noStep,
    view: function (s, p) {
      var rays = [], angs = [0.25, -0.25], i, r, y0, app;
      for (i = 0; i < 2; i++) {
        r = slabApp(p, angs[i]); if (r[2] === null) continue;
        rays.push({ p: [[0, -p.t], r[1], [r[1][0] + 0.15 * r[2][0], r[1][1] + 0.15 * r[2][1]]], v: 0 });
        rays.push({ p: [r[1], [0, r[0]]], v: 1 });
      }
      y0 = slabApp(p, 0.001)[0]; app = -(y0 || 0);
      return { rays: rays, app: app, shift: p.t - app };
    },
    measure: function (p) { var y = slabApp(p, 0.001)[0]; return { app: -(y || 0) }; }
  };

  // ------------------------------------------------------------------ EM induction
  function emf(p, z) { var a2 = p.a * p.a; return p.N * 3 * MU0 * p.m * a2 * z * p.v / (2 * (a2 + z * z) ** 2.5); }
  function indStart(p) { return p.v >= 0 ? -Math.abs(p.z0) : Math.abs(p.z0); }
  K.induction = {
    PARAMS: { N: 200.0, a: 0.02, m: 1.0, v: 0.5, z0: -0.15 }, VARS: ['t', 'z', 'emf', 'flux'],
    init: function (p) { return { t: 0, z: indStart(p) }; },
    step: function (s, p, dt) { s.z += p.v * dt; if (Math.abs(s.z) > Math.abs(p.z0)) s.z = indStart(p); s.t += dt; },
    view: function (s, p) { var a2 = p.a * p.a, z = s.z; return { t: s.t, z: z, emf: emf(p, z), flux: p.N * MU0 * p.m * a2 / (2 * (a2 + z * z) ** 1.5) }; },
    measure: function (p) {
      if (Math.abs(p.v) < 1e-9) return { emf_peak: 0 };
      var s = K.induction.init(p), best = 0, dt = 1e-5 / Math.abs(p.v), n = Math.trunc(Math.abs(p.z0) / 1e-5) + 2, i;
      for (i = 0; i < n; i++) { K.induction.step(s, p, dt); best = Math.max(best, Math.abs(emf(p, s.z))); }
      return { emf_peak: best };
    }
  };

  // ------------------------------------------------------------------ measuring instruments
  K.gauge = {
    PARAMS: { kind: 0.0, L: 0.02345, ze: 0.0, msd: 0.001, nv: 10.0, pitch: 0.0005, ndiv: 50.0 }, VARS: ['jaw', 'lc', 'main', 'div', 'reading'],
    init: t0, step: noStep,
    view: function (s, p) {
      var raw = p.L + p.ze, lc, unit, divN, main, div;
      if (p.kind < 0.5) { lc = p.msd / p.nv; unit = p.msd; divN = p.nv; } else { lc = p.pitch / p.ndiv; unit = p.pitch; divN = p.ndiv; }
      main = Math.floor(raw / unit + 1e-9) * unit;
      div = Math.floor((raw - main) / lc + 0.5);
      if (div >= divN) { main = main + unit; div = 0; }
      return { jaw: raw, lc: lc, main: main, div: div, reading: main + div * lc - p.ze };
    },
    measure: function (p) { return { reading: K.gauge.view({}, p).reading }; }
  };

  function varsOf(name, cfg) { var k = K[name]; return k.vars ? k.vars(cfg || {}) : k.VARS.slice(); }
  function paramsFor(name, over) { return assign(K[name].PARAMS, over || {}); }

  // ------------------------------------------------------------------ result from the learner's table
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0; }
  function rows(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) { v = rs[i][keys[j]]; if (v === undefined || v === null || v === '' || !isFinite(+v)) { ok = false; break; } vals.push(+v); }
      if (ok) out.push(vals);
    }
    return out;
  }
  function mapMean(rs, keys, fn, keep) { return mean(rows(rs, keys).filter(keep || function () { return true; }).map(fn)); }
  var CALCS = {
    pendulum_g: { label: 'g', unit: 'm/s²', needs: ['L', 'T'], fn: function (r, p) { return mapMean(r, ['L', 'T'], function (x) { return 4 * PI * PI * x[0] / (x[1] * x[1]); }, function (x) { return x[1] > 0; }); } },
    spring_k_static: { label: 'k', unit: 'N/m', needs: ['m', 'ext'], fn: function (r, p) { return mapMean(r, ['m', 'ext'], function (x) { return x[0] * p.g / x[1]; }, function (x) { return x[1] > 0; }); } },
    spring_k_shm: { label: 'k', unit: 'N/m', needs: ['m', 'T'], fn: function (r) { return mapMean(r, ['m', 'T'], function (x) { return 4 * PI * PI * x[0] / (x[1] * x[1]); }, function (x) { return x[1] > 0; }); } },
    incline_mu: { label: 'μ', unit: '', needs: ['angle', 'F'], fn: function (r, p) { return mapMean(r, ['angle', 'F'], function (x) { return (x[1] - p.m * p.g * Math.sin(x[0])) / (p.m * p.g * Math.cos(x[0])); }); } },
    stokes_eta: { label: 'η', unit: 'Pa·s', needs: ['r', 'v'], fn: function (r, p) { return mapMean(r, ['r', 'v'], function (x) { return 2 * x[0] * x[0] * (p.rho - p.sigma) * p.g / (9 * x[1]); }, function (x) { return x[1] > 0; }); } },
    cooling_k: { label: 'k', unit: '1/s', needs: ['t', 'T'], fn: function (r, p) { return mapMean(r, ['t', 'T'], function (x) { return -Math.log((x[1] - p.Ts) / (p.T0 - p.Ts)) / x[0]; }, function (x) { return x[0] > 0 && x[1] > p.Ts; }); } },
    boyle_pv: { label: 'PV', unit: 'J', needs: ['P', 'V'], fn: function (r) { return mapMean(r, ['P', 'V'], function (x) { return x[0] * x[1]; }); } },
    mix_c: { label: 'c (solid)', unit: 'J/(kg·K)', needs: ['Tf'], fn: function (r, p) { return mapMean(r, ['Tf'], function (x) { return (p.m2 * p.c2 + p.mc * p.cc) * (x[0] - p.T2) / (p.m1 * (p.T1 - x[0])); }, function (x) { return p.T1 !== x[0]; }); } },
    res_v: { label: 'v (sound)', unit: 'm/s', needs: ['h'], fn: function (r, p) { var hs = rows(r, ['h']).map(function (x) { return x[0]; }).sort(function (a, b) { return a - b; }); return hs.length >= 2 ? 2 * p.f * (hs[hs.length - 1] - hs[0]) : 0; } },
    sono_mu: { label: 'μ (wire)', unit: 'kg/m', needs: ['f', 'l', 'Tn'], fn: function (r) { return mapMean(r, ['f', 'l', 'Tn'], function (x) { return x[2] / (4 * x[1] * x[1] * x[0] * x[0]); }, function (x) { return x[1] > 0 && x[0] > 0; }); } },
    ohm_R: { label: 'R', unit: 'Ω', needs: ['V', 'I'], fn: function (r) { return mapMean(r, ['V', 'I'], function (x) { return x[0] / x[1]; }, function (x) { return x[1] !== 0; }); } },
    bridge_S: { label: 'S', unit: 'Ω', needs: ['R', 'l'], fn: function (r) { return mapMean(r, ['R', 'l'], function (x) { return x[0] * (1 - x[1]) / x[1]; }, function (x) { return x[1] > 0 && x[1] < 1; }); } },
    pot_r: { label: 'r (cell)', unit: 'Ω', needs: ['k2', 'l'], fn: function (r, p) { var rs = rows(r, ['k2', 'l']), l1 = mean(rs.filter(function (x) { return x[0] < 0.5; }).map(function (x) { return x[1]; })), l2 = mean(rs.filter(function (x) { return x[0] >= 0.5; }).map(function (x) { return x[1]; })); return l1 > 0 && l2 > 0 ? p.Rb * (l1 - l2) / l2 : 0; } },
    diode_knee: { label: 'knee voltage', unit: 'V', needs: ['V', 'I'], fn: function (r) { var v = rows(r, ['V', 'I']).filter(function (x) { return x[1] >= 0.001; }).map(function (x) { return x[0]; }); return v.length ? Math.min.apply(null, v) : 0; } },
    rc_tau: { label: 'τ', unit: 's', needs: ['tau'], fn: function (r) { return mapMean(r, ['tau'], function (x) { return x[0]; }); } },
    mirror_f: { label: 'f', unit: 'm', needs: ['u', 'v'], fn: function (r) { return mapMean(r, ['u', 'v'], function (x) { return x[0] * x[1] / (x[0] + x[1]); }, function (x) { return x[0] + x[1] !== 0; }); } },
    lens_f: { label: 'f', unit: 'm', needs: ['u', 'v'], fn: function (r) { return mapMean(r, ['u', 'v'], function (x) { return x[0] * x[1] / (x[0] + x[1]); }, function (x) { return x[0] + x[1] !== 0; }); } },
    prism_n: { label: 'n', unit: '', needs: ['i', 'd'], fn: function (r, p) { var d = rows(r, ['i', 'd']).map(function (x) { return x[1]; }); return d.length ? Math.sin((p.A + Math.min.apply(null, d)) / 2) / Math.sin(p.A / 2) : 0; } },
    slab_n: { label: 'n', unit: '', needs: ['t', 'a'], fn: function (r) { return mapMean(r, ['t', 'a'], function (x) { return x[0] / x[1]; }, function (x) { return x[1] > 0; }); } },
    induct_ratio: { label: 'emf / v', unit: 'V·s/m', needs: ['v', 'emf'], fn: function (r) { return mapMean(r, ['v', 'emf'], function (x) { return x[1] / x[0]; }, function (x) { return x[0] !== 0; }); } },
    gauge_mean: { label: 'mean size', unit: 'm', needs: ['reading'], fn: function (r) { return mapMean(r, ['reading'], function (x) { return x[0]; }); } }
  };

  var TEXTBOOK = {};          // the checks run on the server; a pack may still carry its formulas here
  // a kernel PACK adds physics without touching this file: packs/<name>.js calls HoolaKernels.register(...)
  function register(pack) {
    var i, k;
    for (i = 0, k = Object.keys(pack.K || {}); i < k.length; i++) {
      if (K[k[i]]) throw new Error('kernel ' + k[i] + ' is already taken');
      K[k[i]] = pack.K[k[i]];
    }
    for (i = 0, k = Object.keys(pack.CALCS || {}); i < k.length; i++) CALCS[k[i]] = pack.CALCS[k[i]];
    for (i = 0, k = Object.keys(pack.TEXTBOOK || {}); i < k.length; i++) TEXTBOOK[k[i]] = pack.TEXTBOOK[k[i]];
    return true;
  }
  var api = { K: K, CALCS: CALCS, varsOf: varsOf, paramsFor: paramsFor, assign: assign, register: register, TEXTBOOK: TEXTBOOK };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.HoolaKernels = api;
})(typeof window !== 'undefined' ? window : this);

/* Kernel pack (browser twin of app/prayog/packs/ug_optics_w7.py): the B.Sc. / B.Tech applied-optics bench.
   Same formulas, same order of operations, so both sides give the same numbers. Every kernel is a "set the control,
   read the detector" instrument with read(p), plan(p) and calc(rows, p); measure(p) = plan -> read -> calc.
     w7_tir        n = sqrt(1 + ((sin e + cos A) / sin A)^2)            w7_wollaston  n = 1 / sin(half the angle between cut-offs)
     w7_nodal      F = f1 f2 / (f1 + f2 - d)                            w7_biprism    lambda = beta sqrt(d1 d2) / D
     w7_fringes    lambda = 2 dx / N (and air index, expansion)         w7_fabry      finesse = pi sqrt(R) / (1 - R)
     w7_fts        V(x) = exp(-2 pi^2 s^2 x^2)                          w7_corona     dark rings at the zeros of J1
     w7_resolve    lambda / a = s / D                                   w7_malus      I = Imin + (Imax - Imin) cos^2(theta - theta0)
     w7_babinet    sin 2chi = sin 2psi sin delta                        w7_nearfield  I(r) / I(0) = 1 - (r / a)^g
     w7_bend       Gloge's guided fraction on a bend                    w7_splice     overlap of two offset cores
     w7_mfd        MFD = 2 lambda / (pi theta0)                         w7_ld         P = eta (I - Ith)
   Deterministic: no randomness, no wall clock. */
(function (root) {
  'use strict';
  var HK = (root && root.HoolaKernels) ||
    (typeof module !== 'undefined' && module.exports && module.exports.register ? module.exports : null);
  if (!HK) throw new Error('HoolaKernels is not loaded');
  var PI = Math.PI;
  var J1_ZEROS = [3.8317059702075125, 7.015586669815619, 10.173468135062722];
  var SIG_FWHM = 2.3548200450309493;

  function fin(v) { v = Number(v); return isFinite(v) ? v : 0.0; }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function rows(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) {
        v = rs[i] ? rs[i][keys[j]] : undefined;
        if (v === undefined || v === null || v === '' || typeof v === 'boolean') { ok = false; break; }
        v = Number(v); if (!isFinite(v)) { ok = false; break; } vals.push(v);
      }
      if (ok) out.push(vals);
    }
    return out;
  }
  function mean(xs) { var s = 0.0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0.0; }
  function line(xs, ys) {
    var n = xs.length, sx = 0.0, sy = 0.0, sxx = 0.0, sxy = 0.0, i, den, m;
    if (n < 2) return [0.0, 0.0];
    for (i = 0; i < n; i++) { sx += xs[i]; sy += ys[i]; sxx += xs[i] * xs[i]; sxy += xs[i] * ys[i]; }
    den = n * sxx - sx * sx;
    if (den === 0.0) return [0.0, 0.0];
    m = (n * sxy - sx * sy) / den;
    return [m, (sy - m * sx) / n];
  }
  function sqrt(v) { return v > 0.0 ? Math.sqrt(v) : 0.0; }
  function asin(v) { return Math.asin(clamp(v, -1.0, 1.0)); }
  function acos(v) { return Math.acos(clamp(v, -1.0, 1.0)); }
  function ln(v) { return v > 0.0 ? Math.log(v) : 0.0; }
  function sinc2(u) { if (Math.abs(u) < 1e-9) return 1.0; var q = Math.sin(u) / u; return q * q; }
  function j1(u) {
    var h = u / 2.0, term = h, tot = h, k;
    for (k = 1; k < 40; k++) { term = -term * h * h / (k * (k + 1.0)); tot += term; }
    return tot;
  }
  function col(r, i) { var out = [], k; for (k = 0; k < r.length; k++) out.push(r[k][i]); return out; }
  function merge(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; for (k in b) o[k] = b[k]; return o; }
  function scan(K) {
    K.init = function () { return { t: 0.0 }; };
    K.step = function (s, p, dt) { s.t += dt; };
    K.view = function (s, p) { return K.read(p); };
    K.table = function (p) {
      var pl = K.plan(p), out = [], i;
      for (i = 0; i < pl.length; i++) out.push(merge(pl[i], K.read(merge(p, pl[i]))));
      return out;
    };
    K.measure = function (p) { var r = K.table(p); return { result: fin(K.calc(r, p)), rows: r.length }; };
    return K;
  }

  // ---------------------------------------------------------------------- critical emergence from a prism
  var Tir = scan({
    PARAMS: { A: PI / 3, n: 1.5168, nl: 1.0, mode: 0.0, x0: 0.6109, x: 0.6109, fov: 0.02 },
    VARS: ['x', 'bright', 'refl', 'e'],
    e: function (p) {
      var nout = p.mode > 0.5 ? p.nl : 1.0, r1 = asin(nout / p.n);
      return asin(p.n * Math.sin(p.A - r1));
    },
    read: function (p) {
      var e = Tir.e(p);
      return { x: p.x, bright: clamp(0.5 + (p.x - (p.x0 + e)) / p.fov, 0.0, 1.0), refl: 2.0 * (p.x - p.x0), e: e };
    },
    plan: function (p) { return [{ x: p.x0 + Tir.e(p) }, { x: p.x0 }]; },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'refl']), i, norm, edge, e, sa, ca, q2;
      if (r.length < 2) return 0.0;
      norm = r[0];
      for (i = 0; i < r.length; i++) if (Math.abs(r[i][1]) < Math.abs(norm[1])) norm = r[i];
      edge = r[0];
      for (i = 0; i < r.length; i++) if (Math.abs(r[i][0] - norm[0]) > Math.abs(edge[0] - norm[0])) edge = r[i];
      e = edge[0] - norm[0]; sa = Math.sin(p.A); ca = Math.cos(p.A);
      if (p.mode > 0.5) return fin(sa * sqrt(p.n * p.n - Math.sin(e) * Math.sin(e)) - ca * Math.sin(e));
      if (sa === 0.0) return 0.0;
      q2 = (Math.sin(e) + ca) / sa;
      return fin(sqrt(1.0 + q2 * q2));
    },
  });

  // ---------------------------------------------------------------------- Wollaston's air film
  var Wollaston = scan({
    PARAMS: { n: 1.3330, x0: 1.5708, x: 1.5708 },
    VARS: ['x', 'T'],
    read: function (p) {
      var th = p.x - p.x0, s = p.n * Math.sin(Math.abs(th)), ct, ci, rs, rp, R;
      if (s >= 1.0) return { x: p.x, T: 0.0 };
      ct = Math.sqrt(1.0 - s * s); ci = Math.cos(th);
      rs = (p.n * ci - ct) / (p.n * ci + ct); rp = (p.n * ct - ci) / (p.n * ct + ci);
      R = (rs * rs + rp * rp) / 2.0;
      return { x: p.x, T: (1.0 - R) * (1.0 - R) };
    },
    plan: function (p) { var c = asin(1.0 / p.n); return [{ x: p.x0 - c }, { x: p.x0 + c }]; },
    calc: function (rs, p) {
      var r = rows(rs, ['x']), lo, hi, i, s;
      if (r.length < 2) return 0.0;
      lo = hi = r[0][0];
      for (i = 0; i < r.length; i++) { lo = Math.min(lo, r[i][0]); hi = Math.max(hi, r[i][0]); }
      s = Math.sin((hi - lo) / 2.0);
      return s > 0.0 ? fin(1.0 / s) : 0.0;
    },
  });

  // ---------------------------------------------------------------------- the nodal slide
  var Nodal = scan({
    PARAMS: { f1: 0.15, f2: 0.20, d: 0.05, stage: 0.0, x: 0.02, rot: 0.0873, mode: 0.0 },
    VARS: ['x', 'shift', 'D', 'stage'],
    F: function (p) { var den = p.f1 + p.f2 - p.d; return den !== 0.0 ? p.f1 * p.f2 / den : 0.0; },
    h: function (p) { var front = p.stage > 0.5 ? p.f2 : p.f1; return front !== 0.0 ? Nodal.F(p) * p.d / front : 0.0; },
    read: function (p) {
      var h = Nodal.h(p);
      return { x: p.x, shift: (p.x - h) * Math.sin(p.rot), D: Nodal.F(p) + p.x - h, stage: p.stage };
    },
    plan: function (p) {
      return [{ stage: 0.0, x: Nodal.h(merge(p, { stage: 0.0 })) }, { stage: 1.0, x: Nodal.h(merge(p, { stage: 1.0 })) }];
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'x', 'shift', 'D']).filter(function (q) { return Math.abs(q[2]) <= 2e-4; });
      if (p.mode > 0.5) return mean(col(r.filter(function (q) { return q[0] < 0.5; }), 1));
      return mean(col(r, 3));
    },
  });

  // ---------------------------------------------------------------------- Fresnel's biprism
  var Biprism = scan({
    PARAMS: { lam: 5.893e-7, alpha: 0.0087266, nb: 1.5168, a: 0.10, D: 1.0, f: 0.20, t: 1.2e-5, mu: 1.58, stage: 0.0, x: 0.0, mode: 0.0 },
    VARS: ['x', 'N', 'I', 'stage'],
    geo: function (p) {
      var d = 2.0 * p.a * (p.nb - 1.0) * p.alpha, beta = d !== 0.0 ? p.lam * p.D / d : 0.0;
      var disc = sqrt(p.D * p.D - 4.0 * p.f * p.D), u1 = (p.D - disc) / 2.0, v1 = (p.D + disc) / 2.0;
      return { d: d, beta: beta, d1: u1 !== 0.0 ? d * v1 / u1 : 0.0, d2: v1 !== 0.0 ? d * u1 / v1 : 0.0,
        S: d !== 0.0 ? (p.mu - 1.0) * p.t * p.D / d : 0.0 };
    },
    read: function (p) {
      var g = Biprism.geo(p), st = p.stage, half, u, off, N, c;
      if (st > 0.5 && st < 2.5) {
        half = (st < 1.5 ? g.d1 : g.d2) / 2.0; u = (Math.abs(p.x) - half) / 3e-5;
        return { x: p.x, N: 0.0, I: Math.exp(-u * u), stage: st };
      }
      off = st > 2.5 ? g.S : 0.0;
      N = g.beta !== 0.0 ? (p.x - off) / g.beta : 0.0; c = Math.cos(PI * N);
      return { x: p.x, N: N, I: c * c, stage: st };
    },
    plan: function (p) {
      var g = Biprism.geo(p), out = [{ stage: 0.0, x: -10.0 * g.beta }, { stage: 0.0, x: 10.0 * g.beta }];
      if (p.mode > 0.5) { out.push({ stage: 3.0, x: g.S }); return out; }
      out.push({ stage: 1.0, x: -g.d1 / 2.0 }, { stage: 1.0, x: g.d1 / 2.0 }, { stage: 2.0, x: -g.d2 / 2.0 }, { stage: 2.0, x: g.d2 / 2.0 });
      return out;
    },
    span: function (r, st) {
      var xs = [], i, lo, hi;
      for (i = 0; i < r.length; i++) if (Math.abs(r[i][0] - st) < 0.5) xs.push(r[i][1]);
      if (xs.length < 2) return 0.0;
      lo = hi = xs[0];
      for (i = 0; i < xs.length; i++) { lo = Math.min(lo, xs[i]); hi = Math.max(hi, xs[i]); }
      return hi - lo;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'x', 'N']), f0 = r.filter(function (q) { return q[0] < 0.5; }), lo, hi, i, beta, c0, sh, d1, d2;
      if (f0.length < 2) return 0.0;
      lo = hi = f0[0];
      for (i = 0; i < f0.length; i++) { if (f0[i][1] < lo[1]) lo = f0[i]; if (f0[i][1] > hi[1]) hi = f0[i]; }
      if (hi[2] === lo[2]) return 0.0;
      beta = (hi[1] - lo[1]) / (hi[2] - lo[2]);
      if (p.mode > 0.5) {
        c0 = lo[1] - lo[2] * beta; sh = [];
        for (i = 0; i < r.length; i++) if (r[i][0] > 2.5) sh.push(r[i][1] - r[i][2] * beta - c0);
        if (!sh.length || beta === 0.0 || p.mu === 1.0) return 0.0;
        return fin(mean(sh) * p.lam / (beta * (p.mu - 1.0)));
      }
      d1 = Biprism.span(r, 1.0); d2 = Biprism.span(r, 2.0);
      return p.D !== 0.0 ? fin(beta * sqrt(d1 * d2) / p.D) : 0.0;
    },
  });

  // ---------------------------------------------------------------------- fringe counting
  var Fringes = scan({
    PARAMS: { lam: 6.328e-7, mode: 0.0, x: 0.0, L: 0.05, dn: 2.765e-4, P0: 101325.0, L0: 0.20, al: 5.5e-7, T0: 25.0 },
    VARS: ['x', 'N', 'I'],
    per: function (p) {
      if (p.mode < 0.5) return 2.0 / p.lam;
      if (p.mode < 1.5) return 2.0 * p.L * p.dn / (p.P0 * p.lam);
      return 2.0 * p.al * p.L0 / p.lam;
    },
    read: function (p) {
      var x = p.x - (p.mode > 1.5 ? p.T0 : 0.0), N = Fringes.per(p) * x, c = Math.cos(PI * N);
      return { x: p.x, N: N, I: c * c };
    },
    plan: function (p) {
      var per = Fringes.per(p), out = [], k;
      if (per === 0.0) return out;
      if (p.mode < 0.5) { for (k = 0; k < 5; k++) out.push({ x: 50.0 * k / per }); return out; }
      if (p.mode < 1.5) { for (k = 0; k < 8; k++) out.push({ x: 5.0 * k / per }); return out; }
      var nb = 5.0 * Math.max(1.0, Math.ceil(2.0 * per));
      for (k = 0; k < 6; k++) out.push({ x: p.T0 + nb * k / per });
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'N']), m = line(col(r, 0), col(r, 1))[0];
      if (m === 0.0) return 0.0;
      if (p.mode < 0.5) return fin(2.0 / m);
      if (p.mode < 1.5) return fin(m * p.lam * p.P0 / (2.0 * p.L));
      return fin(m * p.lam / (2.0 * p.L0));
    },
  });

  // ---------------------------------------------------------------------- Fabry-Perot
  var Fabry = scan({
    PARAMS: { lam: 6.328e-7, R: 0.90, mode: 0.0, x: 0.0 },
    VARS: ['x', 'N', 'I'],
    fc: function (p) { var q = 1.0 - p.R; return q !== 0.0 ? 4.0 * p.R / (q * q) : 0.0; },
    read: function (p) {
      var s = Math.sin(2.0 * PI * p.x / p.lam);
      return { x: p.x, N: 2.0 * p.x / p.lam, I: 1.0 / (1.0 + Fabry.fc(p) * s * s) };
    },
    plan: function (p) {
      var out = [], k, fc, hw, fsr;
      if (p.mode < 0.5) { for (k = 0; k < 5; k++) out.push({ x: 25.0 * k * p.lam }); return out; }
      fc = Fabry.fc(p); hw = fc > 0.0 ? p.lam / (2.0 * PI) * asin(1.0 / sqrt(fc)) : 0.0; fsr = p.lam / 2.0;
      return [{ x: -hw }, { x: hw }, { x: fsr - hw }, { x: fsr + hw }];
    },
    calc: function (rs, p) {
      var r, m, xs, w;
      if (p.mode < 0.5) {
        r = rows(rs, ['x', 'N']); m = line(col(r, 0), col(r, 1))[0];
        return m !== 0.0 ? fin(2.0 / m) : 0.0;
      }
      xs = col(rows(rs, ['x']), 0).sort(function (a, b) { return a - b; });
      if (xs.length < 4) return 0.0;
      w = ((xs[1] - xs[0]) + (xs[3] - xs[2])) / 2.0;
      if (w === 0.0) return 0.0;
      return fin(((xs[2] + xs[3]) / 2.0 - (xs[0] + xs[1]) / 2.0) / w);
    },
  });

  // ---------------------------------------------------------------------- Fourier-transform spectroscopy
  var Fts = scan({
    PARAMS: { lam0: 5.5e-7, fwhm: 1.0e-8, mode: 0.0, stage: 0.0, x: 0.0, XS: 6.0e-5, NS: 400.0 },
    VARS: ['x', 'N', 'V', 'I', 'T', 'stage'],
    s: function (p) { return p.fwhm / (p.lam0 * p.lam0) / SIG_FWHM; },
    vis: function (p, x) { var q = PI * Fts.s(p) * x; return Math.exp(-2.0 * q * q); },
    spec: function (p, lam) {
      var n = Math.trunc(p.NS), dx, tot = 0.0, j, x, w;
      if (n < 2 || lam <= 0.0) return 0.0;
      dx = p.XS / n;
      for (j = 0; j <= n; j++) {
        x = j * dx; w = (j === 0 || j === n) ? 0.5 : 1.0;
        tot += w * 0.5 * Fts.vis(p, x) * Math.cos(2.0 * PI * x / p.lam0) * Math.cos(2.0 * PI * x / lam);
      }
      return tot * dx;
    },
    read: function (p) {
      var pk, V;
      if (p.stage > 0.5) {
        pk = Fts.spec(p, p.lam0);
        return { x: p.x, N: 0.0, V: 0.0, I: 0.0, T: pk !== 0.0 ? Fts.spec(p, p.x) / pk : 0.0, stage: p.stage };
      }
      V = Fts.vis(p, p.x);
      return { x: p.x, N: p.x / p.lam0, V: V, I: 0.5 * (1.0 + V * Math.cos(2.0 * PI * p.x / p.lam0)), T: 0.0, stage: p.stage };
    },
    half: function (p, sign) {
      var pk = Fts.spec(p, p.lam0), lo = p.lam0, hi = p.lam0 + sign * 3.0 * p.fwhm, i, mid;
      for (i = 0; i < 50; i++) { mid = (lo + hi) / 2.0; if (Fts.spec(p, mid) > 0.5 * pk) lo = mid; else hi = mid; }
      return (lo + hi) / 2.0;
    },
    plan: function (p) {
      var out = [], k;
      if (p.mode > 0.5) return [{ stage: 1.0, x: Fts.half(p, -1.0) }, { stage: 1.0, x: Fts.half(p, 1.0) }];
      for (k = 0; k < 6; k++) out.push({ stage: 0.0, x: 5.0 * k * p.lam0 });
      return out;
    },
    calc: function (rs, p) {
      var xs, lo, hi, i, r, m, lam0, pts, k, s;
      if (p.mode > 0.5) {
        xs = col(rows(rs, ['stage', 'x']).filter(function (q) { return q[0] > 0.5; }), 1);
        if (xs.length < 2) return 0.0;
        lo = hi = xs[0];
        for (i = 0; i < xs.length; i++) { lo = Math.min(lo, xs[i]); hi = Math.max(hi, xs[i]); }
        return hi - lo;
      }
      r = rows(rs, ['stage', 'x', 'N', 'V']).filter(function (q) { return q[0] < 0.5; });
      m = line(col(r, 1), col(r, 2))[0];
      if (m === 0.0) return 0.0;
      lam0 = 1.0 / m;
      pts = r.filter(function (q) { return q[3] > 0.0 && q[3] < 1.0; });
      k = line(pts.map(function (q) { return q[1] * q[1]; }), pts.map(function (q) { return ln(q[3]); }))[0];
      if (k >= 0.0) return 0.0;
      s = sqrt(-k / 2.0) / PI;
      return fin(SIG_FWHM * s * lam0 * lam0);
    },
  });

  // ---------------------------------------------------------------------- the corona of lycopodium powder
  var Corona = scan({
    PARAMS: { dia: 3.2e-5, lam: 6.328e-7, D: 1.0, x: 0.0 },
    VARS: ['x', 'I'],
    read: function (p) {
      var th = Math.atan2(Math.abs(p.x), p.D), u = PI * p.dia * Math.sin(th) / p.lam, q;
      if (u < 1e-6) return { x: p.x, I: 1.0 };
      if (u > 15.0) return { x: p.x, I: 0.0 };
      q = 2.0 * j1(u) / u;
      return { x: p.x, I: q * q };
    },
    plan: function (p) {
      var out = [], i;
      for (i = 0; i < 2; i++) out.push({ x: p.D * Math.tan(asin(J1_ZEROS[i] * p.lam / (PI * p.dia))) });
      return out;
    },
    calc: function (rs, p) {
      var xs = col(rows(rs, ['x']), 0).map(Math.abs).sort(function (a, b) { return a - b; }), vals = [], i, s;
      for (i = 0; i < Math.min(3, xs.length); i++) {
        s = Math.sin(Math.atan2(xs[i], p.D));
        if (s > 0.0) vals.push(J1_ZEROS[i] * p.lam / (PI * s));
      }
      return mean(vals);
    },
  });

  // ---------------------------------------------------------------------- resolving power of a telescope
  var Resolve = scan({
    PARAMS: { s: 2.0e-3, D: 3.0, lam: 5.893e-7, x: 2.0e-3 },
    VARS: ['x', 'dip'],
    read: function (p) {
      var ang = p.s / p.D, mid = 2.0 * sinc2(PI * p.x * ang / (2.0 * p.lam)), pk = 1.0 + sinc2(PI * p.x * ang / p.lam);
      return { x: p.x, dip: Math.min(1.0, mid / pk) };
    },
    plan: function (p) { return [{ x: p.lam * p.D / p.s }]; },
    calc: function (rs, p) { return p.lam !== 0.0 ? mean(col(rows(rs, ['x']), 0)) / p.lam : 0.0; },
  });

  // ---------------------------------------------------------------------- Malus's law
  var Malus = scan({
    PARAMS: { th0: 0.6109, I0: 4.0e-4, ext: 0.002, mode: 0.0, x: 0.0 },
    VARS: ['x', 'I'],
    read: function (p) { var c = Math.cos(p.x - p.th0); return { x: p.x, I: p.I0 * (p.ext + (1.0 - p.ext) * c * c) }; },
    plan: function (p) {
      var out = [], k;
      if (p.mode > 1.5) return [{ x: p.th0 }, { x: p.th0 + PI / 2.0 }];
      for (k = 0; k < 9; k++) out.push({ x: k * PI / 9.0 });
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'I']), i, lo, hi, C = 0.0, S = 0.0, a = 0.0, th0, imin, xs = [], ys = [], c;
      if (r.length < 2) return 0.0;
      if (p.mode > 1.5) {
        lo = hi = r[0][1];
        for (i = 0; i < r.length; i++) { lo = Math.min(lo, r[i][1]); hi = Math.max(hi, r[i][1]); }
        return lo > 0.0 ? fin(hi / lo) : 0.0;
      }
      for (i = 0; i < r.length; i++) { C += r[i][1] * Math.cos(2.0 * r[i][0]); S += r[i][1] * Math.sin(2.0 * r[i][0]); a += r[i][1]; }
      a = a / r.length;
      th0 = 0.5 * Math.atan2(S, C);
      if (th0 < 0.0) th0 += PI;
      if (p.mode < 0.5) return th0;
      imin = a - 2.0 * sqrt(C * C + S * S) / r.length;
      for (i = 0; i < r.length; i++) {
        c = Math.abs(Math.cos(r[i][0] - th0));
        if (c * c > 0.15 && r[i][1] - imin > 0.0) { xs.push(ln(c)); ys.push(ln(r[i][1] - imin)); }
      }
      return line(xs, ys)[0];
    },
  });

  // ---------------------------------------------------------------------- Babinet compensator
  var Babinet = scan({
    PARAMS: { psi: 0.5236, del: 1.0472, beta: 2.0e-3, stage: 0.0, A: 2.3562, x: 0.0, mode: 0.0 },
    VARS: ['x', 'A', 'I', 'stage'],
    read: function (p) {
      var psi = p.stage > 0.5 ? p.psi : PI / 4.0, de = p.stage > 0.5 ? p.del : 0.0;
      var a = Math.cos(psi), b = Math.sin(psi), c = Math.cos(p.A), s = Math.sin(p.A), ph = de + 2.0 * PI * p.x / p.beta;
      return { x: p.x, A: p.A, I: c * a * c * a + s * b * s * b + 2.0 * c * s * a * b * Math.cos(ph), stage: p.stage };
    },
    plan: function (p) {
      var xs = p.beta * (1.0 - p.del / (2.0 * PI));
      return [{ stage: 0.0, A: 3.0 * PI / 4.0, x: 0.0 }, { stage: 0.0, A: 3.0 * PI / 4.0, x: p.beta },
        { stage: 1.0, A: 3.0 * PI / 4.0, x: xs }, { stage: 1.0, A: PI / 2.0 + p.psi, x: xs }];
    },
    ellipse: function (psi, de, mode) {
      if (mode < 0.5) return Math.abs(Math.tan(0.5 * asin(Math.sin(2.0 * psi) * Math.sin(de))));
      if (mode < 1.5) return 0.5 * Math.atan2(Math.sin(2.0 * psi) * Math.cos(de), Math.cos(2.0 * psi));
      return de;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'A', 'x']), c0 = [], t1 = [], i, lo, hi, beta, far, psi, frac, de;
      for (i = 0; i < r.length; i++) { if (r[i][0] < 0.5) c0.push(r[i][2]); if (r[i][0] > 0.5) t1.push(r[i]); }
      if (c0.length < 2 || !t1.length) return 0.0;
      lo = hi = c0[0];
      for (i = 0; i < c0.length; i++) { lo = Math.min(lo, c0[i]); hi = Math.max(hi, c0[i]); }
      beta = hi - lo;
      if (beta === 0.0) return 0.0;
      far = t1[0];
      for (i = 0; i < t1.length; i++) if (Math.abs(t1[i][1] - 3.0 * PI / 4.0) > Math.abs(far[1] - 3.0 * PI / 4.0)) far = t1[i];
      psi = far[1] - PI / 2.0;
      frac = (mean(col(t1, 2)) - lo) / beta;
      frac = frac - Math.floor(frac);
      de = 2.0 * PI * (1.0 - frac);
      return fin(Babinet.ellipse(psi, de, p.mode));
    },
  });

  // ---------------------------------------------------------------------- near field of a multimode fibre
  var NearField = scan({
    PARAMS: { g: 2.0, a: 2.5e-5, M: 400.0, P0: 1.0e-6, x: 0.0 },
    VARS: ['x', 'P'],
    read: function (p) {
      var u = Math.abs(p.x) / (p.M * p.a);
      return { x: p.x, P: u < 1.0 ? p.P0 * (1.0 - Math.pow(u, p.g)) : 0.0 };
    },
    plan: function (p) {
      var ks = [0.0, 0.3, 0.45, 0.6, 0.75, 0.9], out = [], i;
      for (i = 0; i < ks.length; i++) out.push({ x: p.M * p.a * ks[i] });
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'P']), pk, i, xs = [], ys = [], u;
      if (!r.length) return 0.0;
      pk = r[0][1];
      for (i = 0; i < r.length; i++) pk = Math.max(pk, r[i][1]);
      for (i = 0; i < r.length; i++) {
        u = Math.abs(r[i][0]) / (p.M * p.a);
        if (u > 0.0 && u < 1.0 && r[i][1] > 0.0 && r[i][1] < pk) { xs.push(ln(u)); ys.push(ln(1.0 - r[i][1] / pk)); }
      }
      return line(xs, ys)[0];
    },
  });

  // ---------------------------------------------------------------------- bend loss
  var Bend = scan({
    PARAMS: { Dl: 0.01, a: 2.5e-5, n2: 1.45, lam: 8.5e-7, P0: 1.0e-4, stage: 0.0, x: 0.03 },
    VARS: ['x', 'P', 'dB', 'stage'],
    term: function (p, R) { var k = 2.0 * PI / p.lam; return 2.0 * p.a / R + Math.pow(3.0 / (2.0 * p.n2 * k * R), 2.0 / 3.0); },
    read: function (p) {
      var f = 1.0;
      if (p.stage > 0.5 && p.x > 0.0) f = clamp(1.0 - Bend.term(p, p.x) / (2.0 * p.Dl), 0.0, 1.0);
      return { x: p.x, P: p.P0 * f, dB: f > 0.0 ? -10.0 * Math.log10(f) : 99.0, stage: p.stage };
    },
    plan: function () {
      var Rs = [0.03, 0.02, 0.012, 0.008, 0.006], out = [{ stage: 0.0, x: 0.03 }], i;
      for (i = 0; i < Rs.length; i++) out.push({ stage: 1.0, x: Rs[i] });
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'x', 'P']), ref, vals = [], i;
      ref = mean(col(r.filter(function (q) { return q[0] < 0.5; }), 2));
      if (ref <= 0.0) return 0.0;
      for (i = 0; i < r.length; i++) {
        if (r[i][0] > 0.5 && r[i][1] > 0.0 && r[i][2] > 0.0 && r[i][2] < ref) vals.push(Bend.term(p, r[i][1]) / (2.0 * (1.0 - r[i][2] / ref)));
      }
      return mean(vals);
    },
  });

  // ---------------------------------------------------------------------- splice loss
  var Splice = scan({
    PARAMS: { off: 1.0e-5, a: 2.5e-5, P0: 1.0e-4, stage: 0.0 },
    VARS: ['P', 'stage'],
    eta: function (p) { var u = clamp(p.off / (2.0 * p.a), 0.0, 1.0); return 2.0 / PI * (acos(u) - u * sqrt(1.0 - u * u)); },
    read: function (p) { return { P: p.P0 * (p.stage > 0.5 ? Splice.eta(p) : 1.0), stage: p.stage }; },
    plan: function () { return [{ stage: 0.0 }, { stage: 1.0 }]; },
    calc: function (rs) {
      var r = rows(rs, ['stage', 'P']);
      var ref = mean(col(r.filter(function (q) { return q[0] < 0.5; }), 1)), out = mean(col(r.filter(function (q) { return q[0] > 0.5; }), 1));
      if (ref <= 0.0 || out <= 0.0) return 0.0;
      return 10.0 * Math.log10(ref / out);
    },
  });

  // ---------------------------------------------------------------------- mode field diameter
  var Mfd = scan({
    PARAMS: { w0: 4.6e-6, lam: 1.31e-6, P0: 1.0e-6, x: 0.0 },
    VARS: ['x', 'P'],
    read: function (p) { var th0 = p.lam / (PI * p.w0), q = p.x / th0; return { x: p.x, P: p.P0 * Math.exp(-2.0 * q * q) }; },
    plan: function () { var out = [], k; for (k = 0; k < 5; k++) out.push({ x: k * 1.5 * PI / 180.0 }); return out; },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'P']).filter(function (q) { return q[1] > 0.0; });
      var m = line(r.map(function (q) { return q[0] * q[0]; }), r.map(function (q) { return ln(q[1]); }))[0];
      if (m >= 0.0) return 0.0;
      return fin(2.0 * p.lam / (PI * sqrt(-2.0 / m)));
    },
  });

  // ---------------------------------------------------------------------- laser diode
  var LaserDiode = scan({
    PARAMS: { Ith: 0.020, eta: 0.5, s: 0.012, mode: 0.0, x: 0.0 },
    VARS: ['x', 'P'],
    read: function (p) {
      var i = Math.max(0.0, p.x);
      if (i <= p.Ith) return { x: p.x, P: p.s * i };
      return { x: p.x, P: p.s * p.Ith + p.eta * (i - p.Ith) };
    },
    plan: function (p) {
      var ks = [0.3, 0.5, 0.7, 1.1, 1.2, 1.3, 1.4], out = [], i;
      for (i = 0; i < ks.length; i++) out.push({ x: p.Ith * ks[i] });
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'P']).sort(function (a, b) { return a[0] - b[0]; }), lo, hi, l1, l2;
      if (r.length < 7) return 0.0;
      lo = r.slice(0, 3); hi = r.slice(r.length - 4);
      l1 = line(col(lo, 0), col(lo, 1)); l2 = line(col(hi, 0), col(hi, 1));
      if (p.mode > 0.5) return l2[0];
      if (l2[0] === l1[0]) return 0.0;
      return fin((l1[1] - l2[1]) / (l2[0] - l1[0]));
    },
  });

  function calc(K) { return function (r, p) { return fin(K.calc(r, p)); }; }
  function splice(p) { var u = p.off / (2.0 * p.a); return -10.0 * Math.log10(2.0 / PI * (Math.acos(u) - u * Math.sqrt(1.0 - u * u))); }

  HK.register({
    K: { w7_tir: Tir, w7_wollaston: Wollaston, w7_nodal: Nodal, w7_biprism: Biprism, w7_fringes: Fringes, w7_fabry: Fabry,
      w7_fts: Fts, w7_corona: Corona, w7_resolve: Resolve, w7_malus: Malus, w7_babinet: Babinet, w7_nearfield: NearField,
      w7_bend: Bend, w7_splice: Splice, w7_mfd: Mfd, w7_ld: LaserDiode },
    CALCS: {
      w7_tir: { label: 'refractive index', unit: '', needs: ['x', 'refl'], fn: calc(Tir) },
      w7_wollaston: { label: 'refractive index', unit: '', needs: ['x'], fn: calc(Wollaston) },
      w7_nodal: { label: 'focal length / principal point', unit: 'm', needs: ['stage', 'x', 'shift', 'D'], fn: calc(Nodal) },
      w7_biprism: { label: 'wavelength / thickness', unit: 'm', needs: ['stage', 'x', 'N'], fn: calc(Biprism) },
      w7_fringes: { label: 'from the fringe count', unit: '', needs: ['x', 'N'], fn: calc(Fringes) },
      w7_fabry: { label: 'wavelength / finesse', unit: '', needs: ['x', 'N'], fn: calc(Fabry) },
      w7_fts: { label: 'width of the pass band', unit: 'm', needs: ['stage', 'x', 'N', 'V'], fn: calc(Fts) },
      w7_corona: { label: 'particle diameter', unit: 'm', needs: ['x'], fn: calc(Corona) },
      w7_resolve: { label: 'resolving power', unit: '', needs: ['x'], fn: calc(Resolve) },
      w7_malus: { label: 'from the analyser readings', unit: '', needs: ['x', 'I'], fn: calc(Malus) },
      w7_babinet: { label: 'the ellipse', unit: '', needs: ['stage', 'A', 'x'], fn: calc(Babinet) },
      w7_nearfield: { label: 'profile exponent g', unit: '', needs: ['x', 'P'], fn: calc(NearField) },
      w7_bend: { label: 'relative index difference', unit: '', needs: ['stage', 'x', 'P'], fn: calc(Bend) },
      w7_splice: { label: 'splice loss', unit: 'dB', needs: ['stage', 'P'], fn: calc(Splice) },
      w7_mfd: { label: 'mode field diameter', unit: 'm', needs: ['x', 'P'], fn: calc(Mfd) },
      w7_ld: { label: 'threshold / slope', unit: '', needs: ['x', 'P'], fn: calc(LaserDiode) },
    },
    TEXTBOOK: {
      w7_tir: function (p) { return p.mode > 0.5 ? p.nl : p.n; },
      w7_wollaston: function (p) { return p.n; },
      w7_nodal: function (p) { return (p.f1 * p.f2 / (p.f1 + p.f2 - p.d)) * (p.mode > 0.5 ? p.d / p.f1 : 1.0); },
      w7_biprism: function (p) { return p.mode > 0.5 ? p.t : p.lam; },
      w7_fringes: function (p) { return p.mode < 0.5 ? p.lam : (p.mode < 1.5 ? p.dn : p.al); },
      w7_fabry: function (p) { return p.mode < 0.5 ? p.lam : PI * Math.sqrt(p.R) / (1.0 - p.R); },
      w7_fts: function (p) { return p.fwhm; },
      w7_corona: function (p) { return p.dia; },
      w7_resolve: function (p) { return p.D / p.s; },
      w7_malus: function (p) { return p.mode < 0.5 ? p.th0 : (p.mode < 1.5 ? 2.0 : 1.0 / p.ext); },
      w7_babinet: function (p) { return Babinet.ellipse(p.psi, p.del, p.mode); },
      w7_nearfield: function (p) { return p.g; },
      w7_bend: function (p) { return p.Dl; },
      w7_splice: splice,
      w7_mfd: function (p) { return 2.0 * p.w0; },
      w7_ld: function (p) { return p.mode > 0.5 ? p.eta : p.Ith; },
    },
  });
})(typeof window !== 'undefined' ? window : this);
