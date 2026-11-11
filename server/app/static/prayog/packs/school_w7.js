/* Prayogshala kernel pack (JavaScript twin): the school set-ups of wave 7.
   The exact twin of app/prayog/packs/school_w7.py - same formulas, same loops, same numbers. */
(function (root) {
  var HK = (root && root.HoolaKernels) ||
    (typeof module !== 'undefined' && module.exports && module.exports.register ? module.exports : null);
  if (!HK) throw new Error('HoolaKernels is not loaded');
  var PI = Math.PI, G = 9.8;

  function rt(v, lc) { if (lc <= 0) return v; return Math.floor(v / lc + 0.5) * lc; }
  function ix(p, key, n) { var i = Math.floor(p[key] + 0.5); return i < 0 ? 0 : (i > n - 1 ? n - 1 : i); }
  function cp(p) { var o = {}, k; for (k in p) if (Object.prototype.hasOwnProperty.call(p, k)) o[k] = p[k]; return o; }
  function mk(params, fn, meas) {
    var vars = Object.keys(fn(cp(params), 0.0)).filter(function (k) { return k !== 't'; }).sort();
    return { PARAMS: params, VARS: ['t'].concat(vars),
      init: function () { return { t: 0.0 }; },
      step: function (s, p, dt) { s.t += dt; },
      view: function (s, p) { var d = fn(p, s.t || 0.0); d.t = s.t || 0.0; return d; },
      measure: function (p) { return meas ? meas(p) : fn(p, 0.0); },
      fn: fn };
  }

  // ---------------------------------------------------------------------------------------------- motion
  function rollout(p) { var c = p['c' + ix(p, 'surf', 4)]; return { c: c, d: p.h / c, v0: Math.sqrt(10 * p.g * p.h / 7) }; }
  function rolloutM(p) {
    var c = p['c' + ix(p, 'surf', 4)], v = Math.sqrt(10 * p.g * p.h / 7), a = 5 * c * p.g / 7, x = 0.0, dt = 0.0005, i;
    for (i = 0; i < 400000; i++) {
      if (v - a * dt <= 0) { x += v * v / (2 * a); break; }
      x += v * dt - 0.5 * a * dt * dt; v -= a * dt;
    }
    return { d: x, c_meas: p.h / x };
  }
  function pull(p) { var mu = p.mode < 0.5 ? p.mu_s : p.mu_r, W = p.m * p.g; return { F: mu * W, W: W, mu: mu }; }
  function trolley(p) {
    var v = Math.sqrt(2 * p.g * p.h), u = p.M * v / (p.M + p.mb), s = (p.M + p.mb) * u * u / (2 * p.mu * p.mb * p.g);
    return { v: v, s: s, KE: 0.5 * p.M * v * v };
  }
  function roller(p) { var sn = Math.sin(p.ang * PI / 180); return { F: p.m * p.g * sn, sin: sn }; }
  function rollerM(p) {
    var sxy = 0.0, sxx = 0.0;
    [20.0, 30.0, 40.0, 50.0].forEach(function (a) { var q = cp(p); q.ang = a; var r = roller(q); sxy += r.F * r.sin; sxx += r.sin * r.sin; });
    return { W: sxy / sxx, F: roller(p).F };
  }
  function dincline(p) {
    var t1 = Math.tan(p.a1 * PI / 180), t2 = Math.tan(p.a2 * PI / 180), h2 = p.h1 * (1 - p.c / t1) / (1 + p.c / t2);
    return { h2: h2, ratio: h2 / p.h1 };
  }
  function proj(p) {
    var a = p.ang * PI / 180;
    return { R: p.v0 * p.v0 * Math.sin(2 * a) / p.g, Hmax: Math.pow(p.v0 * Math.sin(a), 2) / (2 * p.g), tf: 2 * p.v0 * Math.sin(a) / p.g };
  }
  function projM(p) {
    var best = -1.0, ang = 0.0, i, q, R;
    for (i = 1; i < 90; i++) { q = cp(p); q.ang = i; R = proj(q).R; if (R > best + 1e-12) { best = R; ang = i; } }
    return { ang_max: ang, R_max: best, R: proj(p).R };
  }
  function fall(p) {
    var b = ix(p, 'body', 3), tf, vt, A, Cd;
    if (b === 0) { tf = Math.sqrt(2 * p.h / p.g); vt = 0.0; }
    else {
      A = b === 1 ? p.A_flat : p.A_ball; Cd = b === 1 ? p.Cd_flat : p.Cd_ball;
      vt = Math.sqrt(2 * p.m_p * p.g / (p.rho_air * Cd * A));
      tf = vt / p.g * Math.acosh(Math.exp(p.g * p.h / (vt * vt)));
    }
    return { tf: tf, vt: vt, g_meas: 2 * p.h / (tf * tf) };
  }
  function crater(p) { var W = p.m * p.g, d = W * p.h / (p.F - W); return { d: d, PE: W * p.h, F_meas: W * (p.h + d) / d }; }
  function stairs(p) { var H = p.n * p.hs, work = p.m * p.g * H, tc = work / p.P; return { H: H, tclimb: tc, work: work, P_meas: work / tc }; }
  function pendAmpAfter(p, n) {
    var gl = p.g / p.L, b = p.b, h = 0.002, th = p.th0, om = 0.0, t = 0.0, count = 0, amp = p.th0, tn = 0.0, i;
    var k1a, k1w, k2a, k2w, k3a, k3w, k4a, k4w, th2, om2;
    for (i = 0; i < 4000000; i++) {
      if (count >= n) break;
      k1a = om; k1w = -gl * Math.sin(th) - b * om;
      k2a = om + 0.5 * h * k1w; k2w = -gl * Math.sin(th + 0.5 * h * k1a) - b * (om + 0.5 * h * k1w);
      k3a = om + 0.5 * h * k2w; k3w = -gl * Math.sin(th + 0.5 * h * k2a) - b * (om + 0.5 * h * k2w);
      k4a = om + h * k3w; k4w = -gl * Math.sin(th + h * k3a) - b * (om + h * k3w);
      th2 = th + h / 6 * (k1a + 2 * k2a + 2 * k3a + k4a);
      om2 = om + h / 6 * (k1w + 2 * k2w + 2 * k3w + k4w);
      t += h;
      if (om > 0 && om2 <= 0 && th2 > 0) { count += 1; amp = th2; tn = t; }
      th = th2; om = om2;
    }
    return [amp, tn];
  }
  function pend(p, t) {
    var w = Math.sqrt(Math.max(1e-9, p.g / p.L - p.b * p.b / 4)), env = p.th0 * Math.exp(-p.b * t / 2);
    return { theta: env * Math.cos(w * t), env: env };
  }
  function pendM(p) { var r = pendAmpAfter(p, Math.floor(p.nsw + 0.5)); return { A_n: r[0], t_n: r[1], gamma: Math.log(p.th0 / r[0]) / r[1] }; }

  // ---------------------------------------------------------------------------------------------- measuring
  function jet(p) {
    var y = p['y' + ix(p, 'hole', 3)], v = Math.sqrt(2 * p.g * (p.H - y)), tf = Math.sqrt(2 * (y + p.S) / p.g);
    return { x: v * tf, v: v, y: y, P: p.rho * p.g * (p.H - y), v_meas: v * tf / tf };
  }
  function cuboid(p) {
    var f = ix(p, 'face', 3), l1 = f === 2 ? p.b : p.a, l2 = f === 0 ? p.b : p.c, W = p.rho * p.a * p.b * p.c * p.g, A = l1 * l2;
    return { W: W, A: A, P: W / A, depth: p.ksand * W / A, l1: l1, l2: l2 };
  }
  function upthrust(p) {
    var U = p.rho * p.g * p.V * p.frac, Wt = p.mb * p.g, F = U > Wt ? U - Wt : 0.0;
    return { U: U, F: F, Wt: Wt, Vd: p.V * p.frac, U_meas: F + Wt };
  }
  function density(p) {
    var b = ix(p, 'body', 2), m = p['m' + b], rho = p['rho' + b], V = rt(m / rho, p.lcV);
    return { m: m, V: V, rho_meas: m / V, floats: rho < p.rho_w ? 1.0 : 0.0, sub: rho < p.rho_w ? rho / p.rho_w : 1.0 };
  }
  var WEIGHTS = [0.1, 0.05, 0.02, 0.02, 0.01, 0.005, 0.002, 0.002, 0.001, 0.0005, 0.0002, 0.0002, 0.0001, 0.00005, 0.00002, 0.00002, 0.00001];
  function balance(p) { var diff = p['m' + ix(p, 'body', 2)] - p.w, div = diff * 2000.0; return { diff: diff, div: div > 10 ? 10.0 : (div < -10 ? -10.0 : div) }; }
  function balanceM(p) { var m = p['m' + ix(p, 'body', 2)], tot = 0.0, i; for (i = 0; i < WEIGHTS.length; i++) if (tot + WEIGHTS[i] <= m + 1e-9) tot += WEIGHTS[i]; return { m_read: tot }; }
  function vessel(p) { var v = ix(p, 'vessel', 2), D = rt(p['D' + v], p.lc), dep = rt(p['h' + v], p.lc); return { D: D, dep: dep, V: PI * D * D * dep / 4 }; }
  function sheet(p) {
    if (ix(p, 'body', 2) === 0) return { th: rt(p.t0, p.lc), A: 0.0, V: 0.0 };
    var th = rt(p.t1, p.lc), A = rt(p.A1, p.lcA); return { th: th, A: A, V: A * th };
  }
  function pscale(p) { return { reading: rt(p.L, p.lc) }; }
  function lenscomb(p) { var F = p.f1 * p.f2 / (p.f1 + p.f2), v = p.u * F / (p.u - F); return { F: F, v: v, F_meas: p.u * v / (p.u + v) }; }

  // ---------------------------------------------------------------------------------------------- heat and sound
  function solidsound(p) {
    var m = ix(p, 'medium', 3), v = m === 2 ? 331.3 * Math.sqrt(1 + p.Tc / 273.15) : Math.sqrt(p['Y' + m] / p['rho' + m]);
    var dist = p['d' + m], dt = rt(dist / v, 1e-6);
    return { v: v, dist: dist, dt: dt, v_meas: dist / dt };
  }
  function echo(p) { var x = (p.r_deg - p.i_deg) / p.w; return { loud: Math.exp(-x * x) }; }
  function echoM(p) {
    var best = -1.0, r = 0.0, i, q, L;
    for (i = 10; i < 81; i++) { q = cp(p); q.r_deg = i; L = echo(q).loud; if (L > best + 1e-12) { best = L; r = i; } }
    return { r_peak: r, loud: echo(p).loud };
  }
  function tins(p) {
    var a = p['a' + ix(p, 'tin', 2)], dT = a * p.G * p.A / p.hA * (1 - Math.exp(-p.tm * p.hA / p.C)), T = rt(p.Ta + dT, 0.1);
    return { T: T, rise: T - p.Ta };
  }
  function tinsM(p) { var q0 = cp(p), q1 = cp(p); q0.tin = 0.0; q1.tin = 1.0; return { ratio: tins(q0).rise / tins(q1).rise, T: tins(p).T }; }
  function waxT(p, t) {
    var k = p.hA / (p.m * p.c), t1 = Math.log((p.T0 - p.Ts) / (p.Tm - p.Ts)) / k, tp = p.Lf * p.m / (p.hA * (p.Tm - p.Ts));
    if (t <= t1) return p.Ts + (p.T0 - p.Ts) * Math.exp(-k * t);
    if (t <= t1 + tp) return p.Tm;
    return p.Ts + (p.Tm - p.Ts) * Math.exp(-k * (t - t1 - tp));
  }
  function waxcool(p, t) { var T = waxT(p, t); return { T: T, reading: rt(T, p.lc) }; }
  function waxcoolM(p) {
    var got = p.T0, run = 0, last = -1e9, i, r;
    for (i = 0; i < 121; i++) {
      r = rt(waxT(p, 30.0 * i), p.lc);
      run = Math.abs(r - last) < 1e-9 ? run + 1 : 1; last = r;
      if (run >= 4) { got = r; break; }
    }
    return { Tm_meas: got, reading: rt(p.T0, p.lc) };
  }
  function bimetal(p) {
    var dT = p.T - p.T0, kap = 1.5 * (p.a1 - p.a2) * dT / p.ts, defl = Math.abs(kap) > 1e-9 ? (1 - Math.cos(kap * p.Ls)) / kap : 0.0;
    return { kap: kap, defl: defl, da_meas: dT !== 0 ? 4 * defl * p.ts / (3 * p.Ls * p.Ls * dT) : 0.0 };
  }
  function level(p) { var dT = p.T - p.T0, dh = p.V0 * (p.gam - p.gg) * dT / p.a; return { dh: dh, gapp_meas: dT !== 0 ? p.a * dh / (p.V0 * dT) : 0.0 }; }
  function loss(p, t) {
    var k = p.h * p.A * p.f / (p.m * p.c), lg = Math.log((p.T0 - p.Ts) / (p.T0 - p.drop - p.Ts)), td = rt(lg / k, 1.0);
    return { k: k, tdrop: td, k_meas: lg / td, T: p.Ts + (p.T0 - p.Ts) * Math.exp(-k * t) };
  }

  // ---------------------------------------------------------------------------------------------- electric
  function plating(p) { var Z = p.M / (p.n * p.F), dm = rt(Z * p.I * p.tm, p.lc); return { dm: dm, Q: p.I * p.tm, Z_meas: dm / (p.I * p.tm) }; }
  function liquid(p) {
    var s = p['s' + ix(p, 'liq', 5)], Rl = p.cellk / s, I = (p.V - p.Vf) / (p.Rs + Rl);
    return { I: I, Rl: Rl, glow: I > 2e-4 ? 1.0 : 0.0, s_meas: p.cellk / ((p.V - p.Vf) / I - p.Rs) };
  }
  function swing(p) {
    var F = p.B * p.I * p.Lr, a = Math.atan(F / (p.m * p.g)), sg = (p.sI >= 0 ? 1.0 : -1.0) * (p.sB >= 0 ? 1.0 : -1.0);
    return { ang: sg * a * 180 / PI, F: F, B_meas: p.m * p.g * Math.tan(a) / (p.I * p.Lr) };
  }
  function dmm(p) {
    var m = ix(p, 'mode', 5), r;
    if (m === 0) r = rt(p.R, 10.0); else if (m === 1) r = rt(p.E, 0.01); else if (m === 2) r = rt(p.Vac, 0.1);
    else if (m === 3) r = rt(p.E / p.R, 1e-5); else r = rt(p.Rc, 0.1);
    return { reading: r, beep: (m === 4 && p.Rc < 30) ? 1.0 : 0.0 };
  }
  function dtest(p) {
    var d = ix(p, 'dev', 2), Vf = p['n' + d] * p.Vt * Math.log(p.It / p['Is' + d] + 1), fwd = p.dir >= 0;
    return { reading: fwd ? rt(Vf, 0.001) : 0.0, ol: fwd ? 0.0 : 1.0, conducts: fwd ? 1.0 : 0.0 };
  }

  var K = {
    sw7_rollout: mk({ h: 0.03, surf: 2.0, c0: 0.03, c1: 0.04, c2: 0.08, c3: 0.30, g: G }, rollout, rolloutM),
    sw7_pull: mk({ m: 0.8, mu_s: 0.35, mu_r: 0.02, mode: 0.0, g: G }, pull),
    sw7_trolley: mk({ M: 0.5, mb: 0.2, mu: 0.4, h: 0.08, g: G }, trolley),
    sw7_roller: mk({ m: 0.25, ang: 30.0, g: G }, roller, rollerM),
    sw7_dincline: mk({ h1: 0.12, a1: 20.0, a2: 14.0, c: 0.01 }, dincline),
    sw7_proj: mk({ v0: 3.0, ang: 45.0, g: G }, proj, projM),
    sw7_fall: mk({ h: 2.0, g: G, body: 0.0, m_p: 0.00499, A_flat: 0.06237, Cd_flat: 1.28, A_ball: 0.002827, Cd_ball: 0.47, rho_air: 1.2 }, fall),
    sw7_crater: mk({ m: 0.2, h: 0.5, F: 40.0, g: G }, crater),
    sw7_stairs: mk({ m: 45.0, n: 20.0, hs: 0.17, P: 320.0, g: G }, stairs),
    sw7_pend_decay: mk({ L: 1.0, g: G, th0: 0.2618, b: 0.02, nsw: 20.0 }, pend, pendM),
    sw7_jet: mk({ H: 0.30, S: 0.30, y0: 0.05, y1: 0.12, y2: 0.20, hole: 0.0, g: G, rho: 998.0 }, jet),
    sw7_cuboid: mk({ a: 0.10, b: 0.05, c: 0.025, rho: 7874.0, face: 2.0, g: G, ksand: 2e-6 }, cuboid),
    sw7_upthrust: mk({ V: 0.001, mb: 0.03, rho: 998.0, frac: 1.0, g: G }, upthrust),
    sw7_density: mk({ body: 0.0, m0: 0.006, rho0: 240.0, m1: 0.03937, rho1: 7874.0, rho_w: 998.0, lcV: 5e-7 }, density),
    sw7_balance: mk({ m0: 0.0437, m1: 0.11826, body: 0.0, w: 0.0 }, balance, balanceM),
    sw7_vessel: mk({ vessel: 0.0, D0: 0.0652, h0: 0.0874, D1: 0.0486, h1: 0.0752, lc: 0.0001 }, vessel),
    sw7_sheet: mk({ body: 1.0, t0: 0.00046, t1: 0.00112, A1: 0.00236, lc: 0.00001, lcA: 0.00005 }, sheet),
    sw7_pscale: mk({ L: 0.1374, lc: 0.002 }, pscale),
    sw7_lenscomb: mk({ f1: 0.20, f2: 0.30, u: 0.40 }, lenscomb),
    sw7_solidsound: mk({ medium: 0.0, Y0: 1.1e10, rho0: 650.0, Y1: 3.0e9, rho1: 1150.0, Tc: 25.0, d0: 1.0, d1: 5.0, d2: 1.0 }, solidsound),
    sw7_echo: mk({ i_deg: 40.0, r_deg: 40.0, w: 6.0 }, echo, echoM),
    sw7_tins: mk({ tin: 0.0, a0: 0.95, a1: 0.25, G: 800.0, A: 0.006, hA: 0.35, C: 860.0, Ta: 30.0, tm: 2400.0 }, tins, tinsM),
    sw7_waxcool: mk({ T0: 80.0, Ts: 28.0, Tm: 57.0, hA: 0.3, m: 0.03, c: 2500.0, Lf: 2.0e5, lc: 0.5 }, waxcool, waxcoolM),
    sw7_bimetal: mk({ a1: 19e-6, a2: 11.8e-6, ts: 0.001, Ls: 0.15, T0: 25.0, T: 125.0 }, bimetal),
    sw7_level: mk({ V0: 1.0e-4, gam: 4.9e-4, gg: 2.55e-5, a: 7.07e-6, T0: 25.0, T: 45.0 }, level),
    sw7_loss: mk({ m: 0.15, c: 4186.0, A: 0.012, h: 12.0, f: 1.0, T0: 70.0, Ts: 28.0, drop: 5.0 }, loss),
    sw7_plating: mk({ I: 0.5, tm: 1200.0, M: 0.063546, n: 2.0, F: 96485.33212, lc: 1e-6 }, plating),
    sw7_liquid: mk({ liq: 0.0, s0: 0.05, s1: 1e-4, s2: 0.4, s3: 0.3, s4: 1.7, V: 6.0, cellk: 50.0, Rs: 330.0, Vf: 1.8 }, liquid),
    sw7_swing: mk({ B: 0.08, I: 2.0, Lr: 0.05, m: 0.004, g: G, sI: 1.0, sB: 1.0 }, swing),
    sw7_dmm: mk({ mode: 0.0, R: 4720.0, E: 9.24, Vac: 12.3, Rc: 0.4 }, dmm),
    sw7_dtest: mk({ dev: 0.0, dir: 1.0, It: 1e-3, n0: 1.8, Is0: 3e-9, n1: 2.0, Is1: 2e-18, Vt: 0.02585 }, dtest),
  };
  K.sw7_pend_decay.ampAfter = pendAmpAfter;
  K.sw7_balance.WEIGHTS = WEIGHTS;
  K.sw7_waxcool.Tat = waxT;
  HK.register({ K: K });
})(typeof window !== 'undefined' ? window : this);
