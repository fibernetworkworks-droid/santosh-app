/* Hoola Prayogshala kernels (v0.409): the TRUE behaviour of every lab, run on the learner's phone.
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

  var api = { K: K, CALCS: CALCS, varsOf: varsOf, paramsFor: paramsFor, assign: assign };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.HoolaKernels = api;
})(typeof window !== 'undefined' ? window : this);
