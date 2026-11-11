/* Kernel pack `ug_em_w7`: the exact JavaScript twin of app/prayog/packs/ug_em_w7.py. Same formulas, same
   algorithms, same step counts, same numbers (the server's tests run both and compare). The B.Sc. electricity
   and magnetism benches: the ballistic galvanometer and its six set-ups, Carey Foster's bridge, a low
   resistance on the potentiometer, Anderson's bridge, a universal R / L / C bridge, the Q-meter, RC and RL time
   constants, a transformer, a DC motor, a generator, a magnet falling through a coil, a galvanometer made into
   a meter, a regulated source, and the magnetometers. A reading is simulated (equation of motion integrated,
   network solved and searched for its null, flux differentiated numerically); the textbook formula is only
   what it is checked against. Deterministic: no randomness, no wall clock. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, MU0 = 4e-7 * PI, GOLD = 0.6180339887498949;
  function cp(p) { var o = {}, k; for (k in p) o[k] = p[k]; return o; }

  // ------------------------------------------------------------------ complex helpers
  function cdiv(ar, ai, br, bi) { var d = br * br + bi * bi; return [(ar * br + ai * bi) / d, (ai * br - ar * bi) / d]; }
  function cmul(ar, ai, br, bi) { return [ar * br - ai * bi, ar * bi + ai * br]; }
  function par(ar, ai, br, bi) { var n = cmul(ar, ai, br, bi); return cdiv(n[0], n[1], ar + br, ai + bi); }
  function solve(n, els) {
    var ar = [], ai = [], i, e, a, b, y, j, c, r, k, best, row, m, t, pr, pi_, f, mm, out = [], sr, si, x;
    for (i = 0; i < n; i++) { ar.push([]); ai.push([]); for (k = 0; k <= n; k++) { ar[i].push(0.0); ai[i].push(0.0); } }
    for (i = 0; i < els.length; i++) {
      e = els[i]; a = e[0]; b = e[1];
      y = cdiv(1.0, 0.0, e[2], e[3]);
      j = cmul(y[0], y[1], e[4], e[5]);
      if (a > 0) { ar[a - 1][a - 1] += y[0]; ai[a - 1][a - 1] += y[1]; ar[a - 1][n] -= j[0]; ai[a - 1][n] -= j[1]; }
      if (b > 0) { ar[b - 1][b - 1] += y[0]; ai[b - 1][b - 1] += y[1]; ar[b - 1][n] += j[0]; ai[b - 1][n] += j[1]; }
      if (a > 0 && b > 0) { ar[a - 1][b - 1] -= y[0]; ai[a - 1][b - 1] -= y[1]; ar[b - 1][a - 1] -= y[0]; ai[b - 1][a - 1] -= y[1]; }
    }
    for (c = 0; c < n; c++) {
      best = -1.0; row = c;
      for (r = c; r < n; r++) { m = ar[r][c] * ar[r][c] + ai[r][c] * ai[r][c]; if (m > best) { best = m; row = r; } }
      if (row !== c) { t = ar[c]; ar[c] = ar[row]; ar[row] = t; t = ai[c]; ai[c] = ai[row]; ai[row] = t; }
      pr = ar[c][c]; pi_ = ai[c][c];
      for (r = c + 1; r < n; r++) {
        f = cdiv(ar[r][c], ai[r][c], pr, pi_);
        if (f[0] === 0.0 && f[1] === 0.0) continue;
        for (k = c; k <= n; k++) { mm = cmul(f[0], f[1], ar[c][k], ai[c][k]); ar[r][k] -= mm[0]; ai[r][k] -= mm[1]; }
      }
    }
    for (i = 0; i <= n; i++) out.push([0.0, 0.0]);
    for (c = n - 1; c >= 0; c--) {
      sr = ar[c][n]; si = ai[c][n];
      for (k = c + 1; k < n; k++) { mm = cmul(ar[c][k], ai[c][k], out[k + 1][0], out[k + 1][1]); sr -= mm[0]; si -= mm[1]; }
      x = cdiv(sr, si, ar[c][c], ai[c][c]);
      out[c + 1][0] = x[0]; out[c + 1][1] = x[1];
    }
    return out;
  }
  function branch(v, e) { return cdiv(v[e[0]][0] - v[e[1]][0] + e[4], v[e[0]][1] - v[e[1]][1] + e[5], e[2], e[3]); }
  function golden(f, lo, hi, n) {
    var c = hi - GOLD * (hi - lo), d = lo + GOLD * (hi - lo), fc = f(c), fd = f(d), i;
    for (i = 0; i < n; i++) {
      if (fc < fd) { hi = d; d = c; fd = fc; c = hi - GOLD * (hi - lo); fc = f(c); }
      else { lo = c; c = d; fc = fd; d = lo + GOLD * (hi - lo); fd = f(d); }
    }
    return (lo + hi) / 2;
  }
  function zero(f, lo, hi, n) {
    var flo = f(lo), fhi = f(hi), i, mid, fm;
    if ((flo > 0) === (fhi > 0)) return -1.0;
    for (i = 0; i < n; i++) { mid = (lo + hi) / 2; fm = f(mid); if ((fm > 0) === (flo > 0)) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }

  // ------------------------------------------------------------------ ballistic galvanometer
  var Bg = {
    PARAMS: { mode: 0.0, Kc: 0.01, c: 4e-8, Im: 6.485e-8, b0: 2e-9, G: 150.0, D: 1.0,
      E: 2.0, Rh: 9999.0, r: 1.0, R: 350.0, Cq: 1e-7, Vq: 2.0, part: 0.0,
      Cl: 5e-7, Vl: 1.0, Rx: 5e7, tl: 0.0,
      Lx: 0.05, rl: 12.0, P: 10.0, Q: 10.0, Eb: 2.0, rs: 0.05, Rb: 2.0, Rser: 5000.0,
      Mx: 0.004, Ip: 0.5, Rs2: 9850.0, r3: 0.005,
      Ne: 800.0, re: 0.1, BH: 3.5e-5, BV: 3.2e-5, axis: 0.0,
      ns: 2000.0, Ls: 0.4, as_: 0.025, Is: 2.0, x: 0.0, Nc: 1000.0, rc: 0.01, meth: 0.0 },
    VARS: ['t', 'theta', 'd'],
    damping: function (p, rtot) { return p.b0 + (rtot > 0 ? p.Kc * p.Kc / rtot : 0.0); },
    t0: function (p) { return 2 * PI * Math.sqrt(p.Im / p.c); },
    rk4: function (th, om, p, b, drive, h) {
      var im = p.Im, c = p.c;
      var a1 = (drive - b * om - c * th) / im;
      var t2 = th + 0.5 * h * om, o2 = om + 0.5 * h * a1;
      var a2 = (drive - b * o2 - c * t2) / im;
      var t3 = th + 0.5 * h * o2, o3 = om + 0.5 * h * a2;
      var a3 = (drive - b * o3 - c * t3) / im;
      var t4 = th + h * o3, o4 = om + h * a3;
      var a4 = (drive - b * o4 - c * t4) / im;
      return [th + h * (om + 2 * o2 + 2 * o3 + o4) / 6, om + h * (a1 + 2 * a2 + 2 * a3 + a4) / 6];
    },
    throw_: function (p, q, rtot, periods, per) {
      var b = Bg.damping(p, rtot), h = Bg.t0(p) / per, n = Math.floor(periods * per);
      var th = 0.0, om = p.Kc * q / p.Im, sgn = om >= 0 ? 1.0 : -1.0;
      var th1 = 0.0, th2 = 0.0, t1 = 0.0, t2 = 0.0, found = 0, i, nx, tau;
      for (i = 0; i < n; i++) {
        nx = Bg.rk4(th, om, p, b, 0.0, h);
        if (found === 0 && om * sgn > 0 && nx[1] * sgn <= 0) { tau = om / (om - nx[1]) * h; th1 = th + 0.5 * om * tau; t1 = i * h + tau; found = 1; }
        else if (found === 1 && om * sgn < 0 && nx[1] * sgn >= 0) { tau = om / (om - nx[1]) * h; th2 = th + 0.5 * om * tau; t2 = i * h + tau; found = 2; }
        th = nx[0]; om = nx[1];
        if (found === 2) break;
      }
      if (found < 2 || th1 * th2 >= 0) return { th1: th1, th2: 0.0, half: 0.0 };
      return { th1: th1, th2: th2, half: t2 - t1 };
    },
    dscale: function (p, th) { return 2.0 * p.D * th; },
    divider: function (p) {
      var v = solve(2, [[0, 1, p.Rh, 0.0, p.E, 0.0], [1, 0, p.r, 0.0, 0.0, 0.0],
        [1, 2, p.R + 1e-9, 0.0, 0.0, 0.0], [2, 0, p.G, 0.0, 0.0, 0.0]]);
      return [v[2][0] / p.G, p.G + p.R + p.r * p.Rh / (p.r + p.Rh)];
    },
    rayleigh_net: function (p, s, extra, emf) {
      var els = [[0, 1, p.Rb, 0.0, p.Eb, 0.0], [1, 2, p.P, 0.0, 0.0, 0.0], [1, 3, p.Q, 0.0, 0.0, 0.0],
        [2, 0, p.rl + extra, 0.0, emf, 0.0], [3, 0, s, 0.0, 0.0, 0.0],
        [2, 3, p.G + p.Rser, 0.0, 0.0, 0.0]];
      var v = solve(3, els);
      return (v[2][0] - v[3][0]) / (p.G + p.Rser);
    },
    rayleigh: function (p) {
      var s = zero(function (x) { return Bg.rayleigh_net(p, x, 0.0, 0.0); }, 0.01, 500.0, 60);
      var els = [[0, 1, p.Rb, 0.0, p.Eb, 0.0], [1, 2, p.P, 0.0, 0.0, 0.0], [1, 3, p.Q, 0.0, 0.0, 0.0],
        [2, 0, p.rl, 0.0, 0.0, 0.0], [3, 0, s, 0.0, 0.0, 0.0],
        [2, 3, p.G + p.Rser, 0.0, 0.0, 0.0]];
      var v = solve(3, els), i0 = v[2][0] / p.rl;
      var open_els = [[1, 2, p.P, 0.0, 0.0, 0.0], [1, 3, p.Q, 0.0, 0.0, 0.0],
        [2, 0, p.rl, 0.0, 1.0, 0.0], [3, 0, s, 0.0, 0.0, 0.0],
        [2, 3, p.G + p.Rser, 0.0, 0.0, 0.0]];
      var vo = solve(3, open_els), g_per_volt = (vo[2][0] - vo[3][0]) / (p.G + p.Rser);
      var q = Math.abs(p.Lx * i0 * g_per_volt);
      var ig = Math.abs(Bg.rayleigh_net(p, s, p.rs, 0.0));
      var rdamp = p.G + p.Rser + (p.P + p.Q) * (p.rl + s) / (p.P + p.Q + p.rl + s);
      return { S: s, i0: i0, q: q, ig: ig, rdamp: rdamp };
    },
    sol_b: function (p, x) {
      var n = 400, dz = p.Ls / n, a2 = p.as_ * p.as_, tot = 0.0, i, z;
      for (i = 0; i < n; i++) {
        z = -p.Ls / 2 + (i + 0.5) * dz - x;
        tot += MU0 * (p.ns * dz * p.Is) * a2 / (2.0 * ((a2 + z * z) * Math.sqrt(a2 + z * z)));
      }
      return tot;
    },
    setup: function (p) {
      var m = Math.round(p.mode), d, q, k, h, i, k1, k2, k3, k4, r, rt, area, b;
      if (m === 0) { d = Bg.divider(p); return { q: p.Cq * p.Vq, ig: d[0], rq: 0.0 }; }
      if (m === 1) {
        q = p.Cl * p.Vl; k = 1.0 / (p.Rx * p.Cl); h = p.tl / 200.0;
        for (i = 0; i < 200; i++) {
          k1 = -k * q; k2 = -k * (q + 0.5 * h * k1); k3 = -k * (q + 0.5 * h * k2); k4 = -k * (q + h * k3);
          q += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6;
        }
        return { q: q, ig: 0.0, rq: 0.0 };
      }
      if (m === 2) { r = Bg.rayleigh(p); return { q: r.q, ig: r.ig, rq: r.rdamp }; }
      if (m === 3) { rt = p.Rs2 + p.G; return { q: 2.0 * p.Mx * p.Ip / rt, ig: p.Ip * p.r3 / (rt + p.r3), rq: rt }; }
      if (m === 4) {
        rt = p.Rs2 + p.G; area = PI * p.re * p.re; b = p.axis >= 0.5 ? p.BV : p.BH;
        return { q: 2.0 * p.Ne * area * b / rt, ig: 0.0, rq: rt };
      }
      rt = p.Rs2 + p.G;
      return { q: 2.0 * p.Nc * PI * p.rc * p.rc * Bg.sol_b(p, p.x) / rt, ig: 0.0, rq: rt };
    },
    cdr: function (p) {
      var q = p.Cq * p.Vq;
      return zero(function (rext) { var t = Bg.throw_(p, q, rext + p.G, 12.0, 400); return t.th2 !== 0.0 ? 1.0 : -1.0; }, 1.0, 50000.0, 40);
    },
    init: function (p) { var su = Bg.setup(p); return { t: 0.0, theta: 0.0, omega: p.Kc * su.q / p.Im, b: Bg.damping(p, su.rq) }; },
    step: function (s, p, dt) {
      var n = Math.max(1, Math.ceil(dt / (Bg.t0(p) / 400.0) - 1e-9)), h = dt / n, i, nx;
      for (i = 0; i < n; i++) { nx = Bg.rk4(s.theta, s.omega, p, s.b, 0.0, h); s.theta = nx[0]; s.omega = nx[1]; }
      s.t += dt;
    },
    view: function (s, p) { return { t: s.t, theta: s.theta, d: Bg.dscale(p, s.theta) }; },
    measure: function (p) {
      var m = Math.round(p.mode), su = Bg.setup(p), t = Bg.throw_(p, su.q, su.rq, 1.6, 2000);
      var d1 = Bg.dscale(p, t.th1), d2 = Math.abs(Bg.dscale(p, t.th2));
      var lam = (d1 > 0 && d2 > 0) ? Math.log(d1 / d2) : 0.0;
      var period = 2.0 * Bg.throw_(p, 1e-7, 0.0, 1.6, 2000).half;
      var phi = Bg.dscale(p, p.Kc * su.ig / p.c);
      var out = { q: su.q, d1: d1, d2: d2, lam: lam, T: period, phi: phi, ig: su.ig };
      var corr = d1 * (1.0 + lam / 2.0), q0, s0, t0, d0, o, so, to, dn, dv, dh, kq;
      if (m === 0) {
        out.Si = su.ig > 0 ? phi / su.ig : 0.0;
        out.Sq = su.q > 0 ? corr / su.q : 0.0;
        if (p.part >= 1.5) out.Rc = Bg.cdr(p);
      } else if (m === 1) {
        q0 = cp(p); q0.tl = 0.0; s0 = Bg.setup(q0); t0 = Bg.throw_(p, s0.q, 0.0, 1.6, 2000); d0 = Bg.dscale(p, t0.th1);
        out.d0 = d0;
        out.Rest = (p.tl > 0 && d1 > 0 && d0 > d1) ? p.tl / (p.Cl * Math.log(d0 / d1)) : 0.0;
      } else if (m === 2) {
        out.Lest = phi > 0 ? p.rs * period / (2 * PI) * corr / phi : 0.0;
      } else if (m === 3) {
        out.Mest = phi > 0 ? p.r3 * period / (4 * PI) * corr / phi : 0.0;
      } else if (m === 4) {
        o = cp(p); o.axis = 1.0 - (p.axis >= 0.5 ? 1.0 : 0.0);
        so = Bg.setup(o); to = Bg.throw_(p, so.q, so.rq, 1.6, 2000); dn = Bg.dscale(p, to.th1);
        if (p.axis >= 0.5) { dv = d1; dh = dn; } else { dv = dn; dh = d1; }
        out.dH = dh; out.dV = dv;
        out.dip = Math.atan2(dv, dh) * 180.0 / PI;
      } else {
        out.B = Bg.sol_b(p, p.x);
        kq = period / (2 * PI) * p.c / p.Kc / (2.0 * p.D);
        out.Best = kq * corr * (p.Rs2 + p.G) / (2.0 * p.Nc * PI * p.rc * p.rc);
      }
      return out;
    }
  };
  function bg_sq(p) { return 2.0 * p.D * p.Kc / Math.sqrt(p.Im * p.c); }
  function bg_si(p) { return 2.0 * p.D * p.Kc / p.c; }
  function bg_cdr(p) { return p.Kc * p.Kc / (2.0 * Math.sqrt(p.Im * p.c) - p.b0) - p.G; }
  function bg_dip(p) { return Math.atan2(p.BV, p.BH) * 180.0 / PI; }
  function bg_bsol(p) {
    var a = p.as_, half = p.Ls / 2, x = p.x;
    return MU0 * p.ns * p.Is / 2.0 * ((x + half) / Math.sqrt((x + half) * (x + half) + a * a) - (x - half) / Math.sqrt((x - half) * (x - half) + a * a));
  }

  // ------------------------------------------------------------------ Carey Foster bridge
  var Carey = {
    PARAMS: { XL: 0.5, YR: 0.0, P: 1.0, Q: 1.0, rho: 1.4, al: 0.004, be: 0.006, E: 2.0, Rb: 1.0, G: 80.0, l: 0.5, Xu: 0.37, std: 0.5 },
    VARS: ['t', 'I_G', 'l'],
    ig: function (p, l, xl, yr) {
      var els = [[0, 1, p.Rb, 0.0, p.E, 0.0], [1, 2, p.P, 0.0, 0.0, 0.0], [2, 0, p.Q, 0.0, 0.0, 0.0],
        [1, 4, xl + 1e-6, 0.0, 0.0, 0.0], [4, 3, p.al + p.rho * l, 0.0, 0.0, 0.0],
        [3, 5, p.be + p.rho * (1.0 - l), 0.0, 0.0, 0.0], [5, 0, yr + 1e-6, 0.0, 0.0, 0.0],
        [2, 3, p.G, 0.0, 0.0, 0.0]];
      var v = solve(5, els);
      return (v[2][0] - v[3][0]) / p.G;
    },
    null_: function (p, xl, yr) { return zero(function (l) { return Carey.ig(p, l, xl, yr); }, 0.0, 1.0, 50); },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, I_G: Carey.ig(p, p.l, p.XL, p.YR), l: p.l }; },
    measure: function (p) {
      var l1 = Carey.null_(p, p.XL, p.YR), l2 = Carey.null_(p, p.YR, p.XL);
      return { l1: l1, l2: l2, dl: l2 - l1, diff: (l1 >= 0 && l2 >= 0) ? p.rho * (l2 - l1) : 0.0 };
    }
  };

  // ------------------------------------------------------------------ potentiometer, low resistance
  var PotLow = {
    PARAMS: { E0: 2.0, Rh: 150.0, Rw: 12.0, Lw: 10.0, E2: 2.0, R2: 6.0, Rx: 0.27, Sd: 0.1, G: 80.0, sel: 0.0, l: 5.0 },
    VARS: ['t', 'I_G', 'l'],
    ig: function (p, l, sel) {
      var first = sel >= 0.5 ? p.Sd : p.Rx, second = sel >= 0.5 ? p.Rx : p.Sd, f = l / p.Lw;
      var els = [[0, 1, p.Rh, 0.0, p.E0, 0.0], [1, 2, p.Rw * f + 1e-9, 0.0, 0.0, 0.0],
        [2, 0, p.Rw * (1.0 - f) + 1e-9, 0.0, 0.0, 0.0], [1, 3, first, 0.0, 0.0, 0.0],
        [3, 4, second, 0.0, 0.0, 0.0], [4, 1, p.R2, 0.0, p.E2, 0.0], [3, 2, p.G, 0.0, 0.0, 0.0]];
      var v = solve(4, els);
      return (v[3][0] - v[2][0]) / p.G;
    },
    null_: function (p, sel) { return zero(function (l) { return PotLow.ig(p, l, sel); }, 0.0, p.Lw, 50); },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, I_G: PotLow.ig(p, p.l, p.sel), l: p.l }; },
    measure: function (p) {
      var l1 = PotLow.null_(p, 0.0), l2 = PotLow.null_(p, 1.0);
      return { l1: l1, l2: l2, Rest: (l1 > 0 && l2 > 0) ? p.Sd * l1 / l2 : 0.0 };
    }
  };

  // ------------------------------------------------------------------ Anderson's bridge
  var Anderson = {
    PARAMS: { Lx: 0.15, rl: 60.0, r1: 500.0, R2: 1000.0, R3: 1000.0, R4: 1000.0, r: 100.0, C: 1e-7, f: 1000.0, V: 5.0, Rg: 2000.0, Ro: 50.0 },
    VARS: ['t', 'I_G'],
    ig: function (p, r1, r) {
      var w = 2 * PI * p.f;
      var els = [[0, 1, p.Ro, 0.0, p.V, 0.0], [1, 2, p.rl + r1, w * p.Lx, 0.0, 0.0],
        [2, 0, p.R3, 0.0, 0.0, 0.0], [1, 3, p.R2, 0.0, 0.0, 0.0], [3, 0, p.R4, 0.0, 0.0, 0.0],
        [3, 4, r + 1e-6, 0.0, 0.0, 0.0], [4, 0, 0.0, -1.0 / (w * p.C), 0.0, 0.0],
        [2, 4, p.Rg, 0.0, 0.0, 0.0]];
      var v = solve(4, els), dr = v[2][0] - v[4][0], di = v[2][1] - v[4][1];
      return Math.sqrt(dr * dr + di * di) / p.Rg;
    },
    balance: function (p) {
      var r1 = p.r1, r = p.r, i;
      for (i = 0; i < 12; i++) {
        r1 = golden(function (x) { return Anderson.ig(p, x, r); }, 0.0, 5000.0, 70);
        r = golden(function (x) { return Anderson.ig(p, r1, x); }, 0.0, 5000.0, 70);
      }
      return [r1, r];
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, I_G: Anderson.ig(p, p.r1, p.r) }; },
    measure: function (p) {
      var b = Anderson.balance(p), r1 = b[0], r = b[1];
      var lest = p.C * p.R3 / p.R4 * (r * (p.R4 + p.R2) + p.R2 * p.R4);
      return { r1: r1, r: r, I_G: Anderson.ig(p, r1, r), Lest: lest, rlest: p.R2 * p.R3 / p.R4 - r1 };
    }
  };

  // ------------------------------------------------------------------ universal R / L / C bridge
  var UniBridge = {
    PARAMS: { fn: 1.0, Rx: 470.0, Lx: 0.082, Cx: 4.7e-8, rx: 35.0, Rr: 1000.0, Ra: 1000.0, Cs: 1e-7, Dm: 500.0, Dl: 5000.0, f: 1000.0, V: 5.0, Rg: 2000.0, Ro: 50.0 },
    VARS: ['t', 'I_G'],
    ig: function (p, dm, dl) {
      var w = 2 * PI * p.f, fn = Math.round(p.fn), zx, z3, z4;
      if (fn === 0) { zx = [p.Rx, 0.0]; z3 = [dm + 1e-6, 0.0]; z4 = [p.Ra, 0.0]; }
      else if (fn === 1) { zx = [p.rx, w * p.Lx]; z3 = [dm + 1e-6, 0.0]; z4 = par(dl + 1e-6, 0.0, 0.0, -1.0 / (w * p.Cs)); }
      else { zx = [p.rx, -1.0 / (w * p.Cx)]; z3 = [dl + 1e-6, -1.0 / (w * p.Cs)]; z4 = [dm + 1e-6, 0.0]; }
      var els = [[0, 1, p.Ro, 0.0, p.V, 0.0], [1, 2, zx[0], zx[1], 0.0, 0.0], [2, 0, p.Rr, 0.0, 0.0, 0.0],
        [1, 3, z3[0], z3[1], 0.0, 0.0], [3, 0, z4[0], z4[1], 0.0, 0.0], [2, 3, p.Rg, 0.0, 0.0, 0.0]];
      var v = solve(3, els), dr = v[2][0] - v[3][0], di = v[2][1] - v[3][1];
      return Math.sqrt(dr * dr + di * di) / p.Rg;
    },
    balance: function (p) {
      var fn = Math.round(p.fn), dm = p.Dm, dl = p.Dl, lo, hi, i;
      if (fn === 0) return [golden(function (x) { return UniBridge.ig(p, x, dl); }, 1.0, 11110.0, 80), dl];
      if (fn === 1) { lo = 10.0; hi = 1e6; } else { lo = 0.0; hi = 2000.0; }
      for (i = 0; i < 12; i++) {
        dm = golden(function (x) { return UniBridge.ig(p, x, dl); }, 1.0, 11110.0, 80);
        dl = golden(function (x) { return UniBridge.ig(p, dm, x); }, lo, hi, 80);
      }
      return [dm, dl];
    },
    value: function (p, dm, dl) {
      var fn = Math.round(p.fn);
      if (fn === 0) return p.Rr * dm / p.Ra;
      if (fn === 1) return p.Rr * dm * p.Cs;
      return p.Cs * dm / p.Rr;
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, I_G: UniBridge.ig(p, p.Dm, p.Dl) }; },
    measure: function (p) {
      var b = UniBridge.balance(p);
      return { Dm: b[0], Dl: b[1], I_G: UniBridge.ig(p, b[0], b[1]), val: UniBridge.value(p, b[0], b[1]) };
    }
  };
  function uni_truth(p) { var fn = Math.round(p.fn); return fn === 0 ? p.Rx : (fn === 1 ? p.Lx : p.Cx); }

  // ------------------------------------------------------------------ Q-meter
  var QMeter = {
    PARAMS: { L: 2.5e-4, R: 8.0, Cd: 8e-12, f: 1e6, C: 1e-10, e: 0.02, Rsh: 0.02 },
    VARS: ['t', 'Q', 'Vc'],
    vc: function (p, f, c) {
      var w = 2 * PI * f, z = par(p.R, w * p.L, 0.0, -1.0 / (w * p.Cd)), xc = -1.0 / (w * c);
      var i = cdiv(p.e, 0.0, p.Rsh + z[0], z[1] + xc), v = cmul(i[0], i[1], 0.0, xc);
      return Math.sqrt(v[0] * v[0] + v[1] * v[1]);
    },
    tune: function (p, f) { return golden(function (c) { return -QMeter.vc(p, f, c); }, 1e-11, 6e-10, 90); },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var v = QMeter.vc(p, p.f, p.C); return { t: s.t || 0.0, Vc: v, Q: v / p.e }; },
    measure: function (p) {
      var c1 = QMeter.tune(p, p.f), c2 = QMeter.tune(p, 2.0 * p.f), q1 = QMeter.vc(p, p.f, c1) / p.e;
      var cd = (c1 - 4.0 * c2) / 3.0, w = 2 * PI * p.f;
      return { C1: c1, C2: c2, Q: q1, Cdest: cd, Lest: 1.0 / (w * w * (c1 + cd)), Qtrue: q1 * (1.0 + cd / c1) };
    }
  };

  // ------------------------------------------------------------------ RC / RL time constant
  var Tau = {
    PARAMS: { mode: 0.0, R: 10000.0, C: 1e-7, L: 0.1, rl: 40.0, Rg: 50.0, V0: 4.0 },
    VARS: ['t', 'v'],
    rate: function (p) { return p.mode >= 0.5 ? (p.R + p.rl + p.Rg) / p.L : 1.0 / ((p.R + p.Rg) * p.C); },
    final_: function (p) { return p.mode >= 0.5 ? p.V0 * p.R / (p.R + p.rl + p.Rg) : p.V0; },
    run: function (p, frac) {
      var k = Tau.rate(p), h = 1.0 / (k * 400.0), y = 0.0, vf = Tau.final_(p), i, k1, k2, k3, k4, yn;
      for (i = 0; i < 4000; i++) {
        k1 = k * (vf - y); k2 = k * (vf - (y + 0.5 * h * k1)); k3 = k * (vf - (y + 0.5 * h * k2)); k4 = k * (vf - (y + h * k3));
        yn = y + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6;
        if (yn >= frac * vf) return (i + (frac * vf - y) / (yn - y)) * h;
        y = yn;
      }
      return 0.0;
    },
    init: function () { return { t: 0.0, v: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; s.v = Tau.final_(p) * (1.0 - Math.exp(-Tau.rate(p) * s.t)); },
    view: function (s) { return { t: s.t || 0.0, v: s.v || 0.0 }; },
    measure: function (p) { return { tau: Tau.run(p, 1.0 - Math.exp(-1.0)), thalf: Tau.run(p, 0.5), vf: Tau.final_(p) }; }
  };
  function tau_tb(p) { return p.mode >= 0.5 ? p.L / (p.R + p.rl + p.Rg) : (p.R + p.Rg) * p.C; }

  // ------------------------------------------------------------------ transformer
  var Xfmr = {
    PARAMS: { nr: 0.5, V1: 12.0, RL: 20.0, R1: 1.2, X1: 0.8, R2: 0.35, X2: 0.2, Rc: 900.0, Xm: 450.0 },
    VARS: ['t', 'V2', 'I1', 'I2', 'eta'],
    solve: function (p, rl) {
      var n2 = p.nr * p.nr, m = par(p.Rc, 0.0, 0.0, p.Xm), els, v, i1c, e, i1, pin, i2c, i2, v2, pout;
      if (rl > 0) {
        els = [[0, 1, 1e-6, 0.0, p.V1, 0.0], [1, 2, p.R1, p.X1, 0.0, 0.0],
          [2, 0, m[0], m[1], 0.0, 0.0], [2, 0, (p.R2 + rl) / n2, p.X2 / n2, 0.0, 0.0]];
      } else {
        els = [[0, 1, 1e-6, 0.0, p.V1, 0.0], [1, 2, p.R1, p.X1, 0.0, 0.0], [2, 0, m[0], m[1], 0.0, 0.0]];
      }
      v = solve(2, els);
      i1c = branch(v, els[1]);
      e = Math.sqrt(v[2][0] * v[2][0] + v[2][1] * v[2][1]);
      i1 = Math.sqrt(i1c[0] * i1c[0] + i1c[1] * i1c[1]);
      pin = v[1][0] * i1c[0] + v[1][1] * i1c[1];
      if (rl > 0) { i2c = branch(v, els[3]); i2 = Math.sqrt(i2c[0] * i2c[0] + i2c[1] * i2c[1]) / p.nr; v2 = i2 * rl; }
      else { i2 = 0.0; v2 = e * p.nr; }
      pout = rl > 0 ? i2 * i2 * rl : 0.0;
      return { V2: v2, I1: i1, I2: i2, Pin: pin, Pout: pout, eta: pin > 0 ? pout / pin : 0.0 };
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var r = Xfmr.solve(p, p.RL); return { t: s.t || 0.0, V2: r.V2, I1: r.I1, I2: r.I2, eta: r.eta }; },
    measure: function (p) {
      var r = Xfmr.solve(p, p.RL), o = Xfmr.solve(p, 0.0);
      r.V2open = o.V2; r.ratio = o.V2 / p.V1; r.P0 = o.Pin;
      return r;
    }
  };

  // ------------------------------------------------------------------ DC motor
  var Motor = {
    PARAMS: { V: 6.0, k: 0.012, Ra: 2.4, Tf: 0.0008, bv: 2e-6, J: 4e-6 },
    VARS: ['t', 'w', 'I', 'rpm'],
    acc: function (p, w) {
      var i = (p.V - p.k * w) / p.Ra, tq = p.k * i - p.bv * w;
      if (w <= 0 && tq <= p.Tf) return 0.0;
      return (tq - p.Tf) / p.J;
    },
    advance: function (p, w, h) {
      var k1 = Motor.acc(p, w), k2 = Motor.acc(p, w + 0.5 * h * k1), k3 = Motor.acc(p, w + 0.5 * h * k2), k4 = Motor.acc(p, w + h * k3);
      return Math.max(0.0, w + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6);
    },
    tm: function (p) { return p.J / (p.bv + p.k * p.k / p.Ra); },
    init: function () { return { t: 0.0, w: 0.0 }; },
    step: function (s, p, dt) {
      var n = Math.max(1, Math.ceil(dt / (Motor.tm(p) / 20.0) - 1e-9)), i;
      for (i = 0; i < n; i++) s.w = Motor.advance(p, s.w, dt / n);
      s.t += dt;
    },
    view: function (s, p) { var w = s.w || 0.0; return { t: s.t || 0.0, w: w, I: (p.V - p.k * w) / p.Ra, rpm: w * 60.0 / (2 * PI) }; },
    measure: function (p) {
      var w = 0.0, h = Motor.tm(p) / 40.0, j, i;
      for (j = 0; j < 1200; j++) w = Motor.advance(p, w, h);
      i = (p.V - p.k * w) / p.Ra;
      return { w: w, rpm: w * 60.0 / (2 * PI), I: i, kest: w > 0 ? (p.V - i * p.Ra) / w : 0.0 };
    }
  };
  function motor_w(p) { return Math.max(0.0, (p.k * p.V - p.Ra * p.Tf) / (p.k * p.k + p.Ra * p.bv)); }

  // ------------------------------------------------------------------ generator
  var Gen = {
    PARAMS: { mode: 0.0, N: 200.0, B: 0.05, A: 0.0012, f: 10.0 },
    VARS: ['t', 'emf', 'flux'],
    flux: function (p, t) { return p.N * p.B * p.A * Math.cos(2 * PI * p.f * t); },
    emf: function (p, t) {
      var h = 1.0 / (p.f * 20000.0), e = -(Gen.flux(p, t + h) - Gen.flux(p, t - h)) / (2 * h);
      return p.mode >= 0.5 ? Math.abs(e) : e;
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var t = s.t || 0.0; return { t: t, emf: Gen.emf(p, t), flux: Gen.flux(p, t) }; },
    measure: function (p) {
      var n = 2000, pk = 0.0, tot = 0.0, sq = 0.0, i, e;
      for (i = 0; i < n; i++) {
        e = Gen.emf(p, (i + 0.5) / (n * p.f));
        if (Math.abs(e) > pk) pk = Math.abs(e);
        tot += e; sq += e * e;
      }
      return { peak: pk, mean: tot / n, rms: Math.sqrt(sq / n), w: 2 * PI * p.f };
    }
  };
  function gen_peak(p) { return p.N * p.B * p.A * 2 * PI * p.f; }

  // ------------------------------------------------------------------ falling magnet
  var FallMag = {
    PARAMS: { m: 0.75, N: 500.0, a: 0.02, h: 0.4, g: 9.8, fs: 5000.0 },
    VARS: ['t', 'emf', 'z'],
    link: function (p, z) { var a2 = p.a * p.a; return p.N * MU0 * p.m * a2 / (2.0 * ((a2 + z * z) * Math.sqrt(a2 + z * z))); },
    zt: function (p, t) { return -p.h + 0.5 * p.g * t * t; },
    emf: function (p, t) { var d = 1e-6; return -(FallMag.link(p, FallMag.zt(p, t + d)) - FallMag.link(p, FallMag.zt(p, t - d))) / (2 * d); },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var t = s.t || 0.0; return { t: t, emf: FallMag.emf(p, t), z: FallMag.zt(p, t) }; },
    measure: function (p) {
      var tc = Math.sqrt(2.0 * p.h / p.g);
      var t0 = Math.sqrt(2.0 * Math.max(p.h - 6.0 * p.a, 0.0) / p.g), t1 = Math.sqrt(2.0 * (p.h + 6.0 * p.a) / p.g);
      var n = Math.floor((t1 - t0) * p.fs), lo = 0.0, hi = 0.0, tlo = 0.0, thi = 0.0, a1 = 0.0, a2 = 0.0, i, t, e, pk, v;
      for (i = 0; i <= n; i++) {
        t = t0 + i / p.fs; e = FallMag.emf(p, t);
        if (e < lo) { lo = e; tlo = t; }
        if (e > hi) { hi = e; thi = t; }
        if (t < tc) a1 += e / p.fs; else a2 += e / p.fs;
      }
      pk = (Math.abs(lo) + Math.abs(hi)) / 2; v = Math.sqrt(2.0 * p.g * p.h);
      return { pk1: tlo < thi ? lo : hi, pk2: tlo < thi ? hi : lo, pk: pk, dt: Math.abs(thi - tlo), area1: a1, area2: a2, v: v,
        mest: pk * p.a * p.a * 25.0 * Math.sqrt(5.0) / (24.0 * p.N * MU0 * v) };
    }
  };
  function fall_pk(p) { return 24.0 / (25.0 * Math.sqrt(5.0)) * p.N * MU0 * p.m * Math.sqrt(2.0 * p.g * p.h) / (p.a * p.a); }

  // ------------------------------------------------------------------ galvanometer into a meter
  var GConv = {
    PARAMS: { mode: 0.0, stage: 0.0, G: 96.0, kf: 2e-5, n: 30.0, E: 2.0, R: 4000.0, S: 96.0, Vr: 3.0, Ir: 0.3, Rs: 4904.0, Sh: 0.192, Vt: 2.0, It: 0.2 },
    VARS: ['t', 'theta', 'Ig'],
    ig: function (p) {
      var st = Math.round(p.stage), v;
      if (st === 0) { v = solve(1, [[0, 1, p.R, 0.0, p.E, 0.0], [1, 0, p.G, 0.0, 0.0, 0.0]]); return v[1][0] / p.G; }
      if (st === 1) { v = solve(1, [[0, 1, p.R, 0.0, p.E, 0.0], [1, 0, p.G, 0.0, 0.0, 0.0], [1, 0, p.S, 0.0, 0.0, 0.0]]); return v[1][0] / p.G; }
      if (p.mode < 0.5) { v = solve(2, [[0, 1, 1e-6, 0.0, p.Vt, 0.0], [1, 2, p.Rs, 0.0, 0.0, 0.0], [2, 0, p.G, 0.0, 0.0, 0.0]]); return v[2][0] / p.G; }
      v = solve(1, [[0, 1, 1e6, 0.0, p.It * 1e6, 0.0], [1, 0, p.G, 0.0, 0.0, 0.0], [1, 0, p.Sh, 0.0, 0.0, 0.0]]);
      return v[1][0] / p.G;
    },
    theta: function (p) { return GConv.ig(p) / p.kf; },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var i = GConv.ig(p); return { t: s.t || 0.0, Ig: i, theta: i / p.kf }; },
    measure: function (p) {
      var a = cp(p), b = cp(p), th0, sh, gest, kest, igf, need;
      a.stage = 0.0; th0 = GConv.theta(a); b.stage = 1.0;
      sh = zero(function (s) { b.S = s; return GConv.theta(b) - th0 / 2.0; }, 0.01, 1e5, 70);
      gest = p.R * sh / (p.R - sh); kest = p.E / ((p.R + gest) * th0); igf = p.n * kest;
      need = p.mode < 0.5 ? p.Vr / igf - gest : igf * gest / (p.Ir - igf);
      return { theta: GConv.theta(p), th0: th0, Shalf: sh, Gest: gest, kest: kest, need: need };
    }
  };
  function gconv_need(p) { var igf = p.n * p.kf; return p.mode < 0.5 ? p.Vr / igf - p.G : igf * p.G / (p.Ir - igf); }

  // ------------------------------------------------------------------ CV / CC source
  var SrcReg = {
    PARAMS: { mode: 0.0, V0: 9.0, ro: 0.25, Ilim: 1.0, I0: 0.01, Ro: 50000.0, Vmax: 12.0, RL: 30.0 },
    VARS: ['t', 'V', 'I'],
    vsrc: function (p, i) {
      var v;
      if (p.mode < 0.5) { v = p.V0 - p.ro * i; if (i > p.Ilim) v -= (i - p.Ilim) * 2000.0; return v; }
      v = (p.I0 - i) * p.Ro;
      return Math.min(v, p.Vmax + (p.I0 - i) * 1.0);
    },
    point: function (p, rl) {
      var top = p.mode < 0.5 ? (p.Ilim * 1.2 + p.V0 / 1000.0) : p.I0;
      var i = zero(function (x) { return SrcReg.vsrc(p, x) - x * rl; }, 0.0, top, 60);
      if (i < 0) i = top;
      return [i * rl, i];
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var q = SrcReg.point(p, p.RL); return { t: s.t || 0.0, V: q[0], I: q[1] }; },
    measure: function (p) {
      var a = SrcReg.point(p, p.RL), b = SrcReg.point(p, p.RL * 2.0);
      return { V: a[0], I: a[1], rout: b[1] !== a[1] ? -(b[0] - a[0]) / (b[1] - a[1]) : 0.0 };
    }
  };
  function src_rout(p) { return p.mode < 0.5 ? p.ro : p.Ro; }

  // ------------------------------------------------------------------ magnetometers
  var Magneto = {
    PARAMS: { M: 0.5, H: 3.6e-5, l: 0.04, d: 0.2, pos: 0.0, Im: 4.2e-5, amp: 5.0 },
    VARS: ['t', 'theta', 'B'],
    field: function (p) {
      var qm = p.M / (2.0 * p.l), k = MU0 / (4 * PI), r2;
      if (p.pos < 0.5) return k * qm * (1.0 / ((p.d - p.l) * (p.d - p.l)) - 1.0 / ((p.d + p.l) * (p.d + p.l)));
      r2 = p.d * p.d + p.l * p.l;
      return 2.0 * k * qm / r2 * (p.l / Math.sqrt(r2));
    },
    period: function (p) {
      var k = p.M * p.H / p.Im, tg = 2 * PI / Math.sqrt(k), h = tg / 2000.0;
      var th = p.amp * PI / 180.0, om = 0.0, crossings = 0, tprev = 0.0, tfirst = 0.0, i, a1, t2, o2, a2, t3, o3, a3, t4, o4, a4, thn, omn, tc;
      for (i = 0; i < 5000; i++) {
        a1 = -k * Math.sin(th);
        t2 = th + 0.5 * h * om; o2 = om + 0.5 * h * a1; a2 = -k * Math.sin(t2);
        t3 = th + 0.5 * h * o2; o3 = om + 0.5 * h * a2; a3 = -k * Math.sin(t3);
        t4 = th + h * o3; o4 = om + h * a3; a4 = -k * Math.sin(t4);
        thn = th + h * (om + 2 * o2 + 2 * o3 + o4) / 6;
        omn = om + h * (a1 + 2 * a2 + 2 * a3 + a4) / 6;
        if (th > 0 && 0 >= thn) {
          tc = (i + th / (th - thn)) * h; crossings += 1;
          if (crossings === 1) tfirst = tc; else { tprev = tc; break; }
        }
        th = thn; om = omn;
      }
      return crossings >= 2 ? tprev - tfirst : 0.0;
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var b = Magneto.field(p); return { t: s.t || 0.0, B: b, theta: Math.atan2(b, p.H) * 180.0 / PI }; },
    measure: function (p) {
      var b = Magneto.field(p), th = Math.atan2(b, p.H), t = Magneto.period(p), d = p.d, l = p.l, ratio, prod;
      if (p.pos < 0.5) ratio = 4 * PI / MU0 * ((d * d - l * l) * (d * d - l * l)) / (2.0 * d) * Math.tan(th);
      else ratio = 4 * PI / MU0 * (d * d + l * l) * Math.sqrt(d * d + l * l) * Math.tan(th);
      prod = t > 0 ? 4 * PI * PI * p.Im / (t * t) : 0.0;
      return { theta: th * 180.0 / PI, T: t, MbyH: ratio, MH: prod, Mest: Math.sqrt(ratio * prod), Hest: ratio > 0 ? Math.sqrt(prod / ratio) : 0.0 };
    }
  };

  H.register({
    K: { w7_bg: Bg, w7_carey: Carey, w7_potlow: PotLow, w7_anderson: Anderson, w7_unibridge: UniBridge, w7_qmeter: QMeter,
      w7_tau: Tau, w7_xfmr: Xfmr, w7_motor: Motor, w7_gen: Gen, w7_fallmag: FallMag, w7_gconv: GConv, w7_srcreg: SrcReg,
      w7_magneto: Magneto },
    CALCS: {},
    TEXTBOOK: {
      w7_bg_sq: bg_sq, w7_bg_si: bg_si, w7_bg_cdr: bg_cdr,
      w7_bg_rx: function (p) { return p.Rx; }, w7_bg_lx: function (p) { return p.Lx; }, w7_bg_mx: function (p) { return p.Mx; },
      w7_bg_dip: bg_dip, w7_bg_bsol: bg_bsol,
      w7_carey_diff: function (p) { return p.XL - p.YR; },
      w7_potlow_rx: function (p) { return p.Rx; },
      w7_anderson_l: function (p) { return p.Lx; },
      w7_uni_val: uni_truth,
      w7_q_l: function (p) { return p.L; },
      w7_tau: tau_tb,
      w7_xfmr_ratio: function (p) { return p.nr; },
      w7_motor_w: motor_w,
      w7_gen_peak: gen_peak,
      w7_fall_pk: fall_pk,
      w7_gconv_need: gconv_need,
      w7_src_rout: src_rout,
      w7_mag_h: function (p) { return p.H; }
    }
  });
})(typeof window !== 'undefined' ? window : this);
