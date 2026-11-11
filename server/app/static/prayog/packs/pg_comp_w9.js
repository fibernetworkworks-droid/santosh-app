/* Kernel pack (browser twin of app/prayog/packs/pg_comp_w9.py): M.Sc. computational physics and materials
   characterisation practicals, wave 9. Same formulas, same order of operations, so both sides give the same numbers.
   Deterministic: anything random is the seeded Lehmer generator (16807, mod 2^31 - 1), never the clock.
     pc9_xcom (NIST mass attenuation, mixture rule - fetched tables)   pc9_qd (Tauc + Brus)   pc9_bet (BET + Gurvich)
     pc9_dsc (Tg / Tm / crystallinity)   pc9_tga (DTG steps, mass loss)   pc9_xrd (Williamson-Hall, Scherrer, lattice)
     pc9_tem (SAED d-spacings, grain size)   pc9_gas (sensor sensitivity, response / recovery)   pc9_film (XRR thickness + Scherrer)
   The analysis kernels run on SIMULATED DATA: the hidden sample value is what the student measures. */
(function (root) {
  'use strict';
  var PI = Math.PI, M31 = 2147483647;
  var NA = 6.02214076e23, QE = 1.602176634e-19, H = 6.62607015e-34, ME = 9.1093837015e-31, EPS0 = 8.8541878128e-12;
  var VSTP = 22414.0, SIG_N2 = 0.162e-18, RHO_LN2 = 0.808, M_N2 = 28.0134;

  function I(v) { return Math.floor(v + 0.5); }
  function errOf(val, exact) { return Math.abs(val - exact) / Math.max(Math.abs(exact), 1e-30); }
  function mod(a, b) { var r = a % b; return r < 0 ? r + b : r; }
  function lcg(seed) { var s = mod(I(seed), M31); return [s > 0 ? s : 1]; }
  function u(st) { st[0] = (st[0] * 16807) % M31; return st[0] / M31; }
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
  function base(val, exact, nused, cx, ce, cy, px, py, extra) {
    var s = { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: nused, cx: cx, ce: ce, cy: cy, px: px, py: py }, k;
    if (extra) for (k in extra) s[k] = extra[k];
    return s;
  }
  function copy(s) { var o = {}, k; for (k in s) o[k] = s[k]; return o; }
  function kernel(params, init) {
    var K = {
      PARAMS: params, VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'],
      init: init,
      step: function (s, p, dt) { s.t += dt; },
      view: function (s) { return copy(s); },
      measure: function (p) { var s = init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
    };
    return K;
  }

  // ====================================================================================== NIST attenuation (fetched)
  var XC = {
    E: [0.015, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0],
    water: [1.673, 0.8096, 0.3756, 0.2683, 0.2269, 0.2059, 0.1837, 0.1707, 0.1505, 0.137, 0.1186, 0.1061, 0.09687, 0.08956, 0.07865, 0.07072, 0.06323, 0.05754, 0.04942, 0.03969, 0.03403, 0.03031, 0.0277, 0.02429, 0.02219, 0.01941, 0.01813],
    bone: [9.032, 4.001, 1.331, 0.6655, 0.4242, 0.3148, 0.2229, 0.1855, 0.148, 0.1309, 0.1113, 0.09908, 0.09022, 0.08332, 0.07308, 0.06566, 0.05871, 0.05346, 0.04607, 0.03745, 0.03257, 0.02946, 0.02734, 0.02467, 0.02314, 0.02132, 0.02068],
    tissue: [1.699, 0.823, 0.379, 0.2688, 0.2264, 0.2048, 0.1823, 0.1693, 0.1492, 0.1358, 0.1175, 0.1052, 0.09598, 0.08873, 0.07793, 0.07006, 0.06265, 0.05701, 0.04895, 0.03931, 0.03369, 0.03, 0.02741, 0.02401, 0.02193, 0.01915, 0.01787],
    a150: [1.394, 0.7068, 0.3481, 0.2562, 0.2198, 0.2008, 0.1803, 0.168, 0.1485, 0.1353, 0.1173, 0.1049, 0.09579, 0.08857, 0.07777, 0.06992, 0.06253, 0.05691, 0.0488, 0.03907, 0.03335, 0.02958, 0.0269, 0.02338, 0.02117, 0.01819, 0.01675],
    z1: [0.3764, 0.3695, 0.357, 0.3458, 0.3355, 0.326, 0.3091, 0.2944, 0.2651, 0.2429, 0.2112, 0.1893, 0.1729, 0.1599, 0.1405, 0.1263, 0.1129, 0.1027, 0.08769, 0.06921, 0.05806, 0.05049, 0.04498, 0.03746, 0.03254, 0.02539, 0.02153],
    z6: [0.8071, 0.442, 0.2562, 0.2076, 0.1871, 0.1753, 0.161, 0.1514, 0.1347, 0.1229, 0.1066, 0.09546, 0.08715, 0.08058, 0.07076, 0.06361, 0.0569, 0.05179, 0.04442, 0.03562, 0.03047, 0.02708, 0.02469, 0.02154, 0.01959, 0.01698, 0.01575],
    z7: [1.236, 0.6178, 0.3066, 0.2288, 0.198, 0.1817, 0.1639, 0.1529, 0.1353, 0.1233, 0.1068, 0.09557, 0.08719, 0.08063, 0.07081, 0.06364, 0.05693, 0.0518, 0.0445, 0.03579, 0.03073, 0.02742, 0.02511, 0.02209, 0.02024, 0.01782, 0.01673],
    z8: [1.836, 0.8651, 0.3779, 0.2585, 0.2132, 0.1907, 0.1678, 0.1551, 0.1361, 0.1237, 0.107, 0.09566, 0.08729, 0.0807, 0.07087, 0.06372, 0.05697, 0.05185, 0.04459, 0.03597, 0.031, 0.02777, 0.02552, 0.02263, 0.02089, 0.01866, 0.0177],
    z9: [2.492, 1.133, 0.4487, 0.2828, 0.2214, 0.192, 0.1639, 0.1496, 0.1298, 0.1176, 0.1015, 0.09073, 0.08274, 0.07649, 0.06717, 0.06037, 0.05399, 0.04915, 0.04228, 0.03422, 0.0296, 0.02663, 0.02457, 0.02195, 0.02039, 0.01846, 0.01769],
    z11: [4.694, 2.057, 0.7197, 0.3969, 0.2804, 0.2268, 0.1796, 0.1585, 0.1335, 0.1199, 0.1029, 0.09185, 0.08372, 0.07736, 0.06788, 0.061, 0.05454, 0.04968, 0.04282, 0.03487, 0.03037, 0.02753, 0.02559, 0.02319, 0.02181, 0.02023, 0.0197],
    z12: [6.358, 2.763, 0.9306, 0.4881, 0.3292, 0.257, 0.1951, 0.1686, 0.1394, 0.1245, 0.1065, 0.09492, 0.08647, 0.07988, 0.07008, 0.06296, 0.05629, 0.05129, 0.04426, 0.03613, 0.03159, 0.02873, 0.02681, 0.02445, 0.02313, 0.02168, 0.02127],
    z15: [12.39, 5.352, 1.7, 0.8096, 0.4916, 0.3494, 0.2324, 0.1865, 0.1432, 0.125, 0.1055, 0.09359, 0.08511, 0.07854, 0.06884, 0.06182, 0.05526, 0.05039, 0.04358, 0.0359, 0.03172, 0.02915, 0.02747, 0.02552, 0.02452, 0.02364, 0.02363],
    z16: [15.5, 6.708, 2.113, 0.9872, 0.5849, 0.4053, 0.2585, 0.202, 0.1506, 0.1302, 0.1091, 0.09665, 0.08781, 0.08102, 0.07098, 0.06373, 0.05697, 0.05193, 0.04498, 0.03715, 0.03293, 0.03036, 0.02872, 0.02682, 0.02589, 0.02517, 0.02529],
    z17: [17.84, 7.739, 2.425, 1.117, 0.6483, 0.4395, 0.2696, 0.205, 0.148, 0.1266, 0.1054, 0.09311, 0.08453, 0.07795, 0.06826, 0.06128, 0.05478, 0.04994, 0.04328, 0.03585, 0.03188, 0.0295, 0.02798, 0.02628, 0.02549, 0.02496, 0.0252],
    z19: [25.03, 10.93, 3.413, 1.541, 0.8679, 0.5678, 0.3251, 0.2345, 0.1582, 0.1319, 0.108, 0.09495, 0.086, 0.07922, 0.06929, 0.06216, 0.05556, 0.05068, 0.04399, 0.03666, 0.03282, 0.03054, 0.02915, 0.02766, 0.02704, 0.02687, 0.02737],
    z20: [29.79, 13.06, 4.08, 1.83, 1.019, 0.6578, 0.3656, 0.2571, 0.1674, 0.1376, 0.1116, 0.09783, 0.08851, 0.08148, 0.07122, 0.06388, 0.05709, 0.05207, 0.04524, 0.0378, 0.03395, 0.0317, 0.03035, 0.02892, 0.02839, 0.02838, 0.02903],
    z26: [57.08, 25.68, 8.176, 3.629, 1.958, 1.205, 0.5952, 0.3717, 0.1964, 0.146, 0.1099, 0.094, 0.08414, 0.07704, 0.06699, 0.05995, 0.0535, 0.04883, 0.04265, 0.03621, 0.03312, 0.03146, 0.03057, 0.02991, 0.02994, 0.03092, 0.03224],
    z30: [81.17, 37.19, 12.07, 5.384, 2.892, 1.76, 0.8364, 0.4973, 0.2341, 0.1617, 0.1141, 0.09539, 0.0845, 0.07695, 0.06656, 0.05941, 0.05296, 0.04834, 0.04235, 0.03634, 0.0336, 0.03225, 0.0316, 0.03138, 0.03175, 0.03335, 0.03509],
    z82: [111.6, 86.36, 30.32, 14.36, 8.041, 5.021, 2.419, 5.549, 2.014, 0.9985, 0.4031, 0.2323, 0.1614, 0.1248, 0.0887, 0.07102, 0.05876, 0.05222, 0.04606, 0.04234, 0.04197, 0.04272, 0.04391, 0.04675, 0.04972, 0.05658, 0.06206]
  };
  var XC_COMP = [
    [[1, 0.111898], [8, 0.888102]],
    [[1, 0.034], [6, 0.155], [7, 0.042], [8, 0.435], [11, 0.001], [12, 0.002], [15, 0.103], [16, 0.003], [20, 0.225]],
    [[1, 0.102], [6, 0.143], [7, 0.034], [8, 0.708], [11, 0.002], [15, 0.003], [16, 0.003], [17, 0.002], [19, 0.003]],
    [[1, 0.10133], [6, 0.775498], [7, 0.035057], [8, 0.052315], [9, 0.017423], [20, 0.018377]],
    [[82, 1.0]]
  ];
  var XC_NAME = ['water', 'bone', 'tissue', 'a150', 'z82'];
  var XC_RHO = [1.0, 1.92, 1.06, 1.127, 11.35];
  function xcInterp(tab, ekev) {
    var G = XC.E, e = ekev / 1000.0, i = 0, f;
    if (e <= G[0]) return tab[0];
    if (e >= G[G.length - 1]) return tab[G.length - 1];
    while (i < G.length - 2 && G[i + 1] < e) i++;
    f = (Math.log(e) - Math.log(G[i])) / (Math.log(G[i + 1]) - Math.log(G[i]));
    return Math.exp(Math.log(tab[i]) + (Math.log(tab[i + 1]) - Math.log(tab[i])) * f);
  }
  function xcMix(mat, ekev) {
    var s = 0.0, j, c = XC_COMP[mat];
    for (j = 0; j < c.length; j++) s += c[j][1] * xcInterp(XC['z' + c[j][0]], ekev);
    return s;
  }
  function xcMat(p) { return Math.max(0, Math.min(4, I(p.mat))); }
  function xcExact(p) { return xcInterp(XC[XC_NAME[xcMat(p)]], p.n); }
  var PcXcom = kernel({ mat: 0.0, n: 662.0, method: 0.0, what: 0.0 }, function (p) {
    var mat = xcMat(p), ek = p.n, val = xcMix(mat, ek), ex = xcExact(p), cx = [], ce = [], cy = [], j, e;
    for (j = 0; j < XC.E.length; j++) {
      e = XC.E[j];
      cx.push(e * 1000.0);
      ce.push(Math.log10(xcInterp(XC[XC_NAME[mat]], e * 1000.0)));
      cy.push(Math.log10(xcMix(mat, e * 1000.0)));
    }
    var mu = val * XC_RHO[mat];
    return base(val, ex, XC_COMP[mat].length, cx, ce, cy, [ek], [Math.log10(val)], { mu: mu, hvl: Math.log(2.0) / mu, rho: XC_RHO[mat] });
  });

  // ====================================================================================== quantum dots (Brus)
  function qdAb(p) {
    var a = H * H / (8.0 * ME) * (1.0 / p.me + 1.0 / p.mh) / QE;
    var b = 1.786 * QE / (4.0 * PI * EPS0 * p.eps);
    return [a, b];
  }
  function qdE1(p) { var ab = qdAb(p), R = p.R * 1e-9; return p.Eg + ab[0] / (R * R) - ab[1] / R; }
  function qdRadius(p, E1) {
    var ab = qdAb(p), disc = ab[1] * ab[1] + 4.0 * ab[0] * (E1 - p.Eg), uu;
    if (disc < 0) return 0.0;
    uu = (ab[1] + Math.sqrt(disc)) / (2.0 * ab[0]);
    return 1e9 / uu;
  }
  function qdExact(p) { var w = I(p.what), E1 = qdE1(p); if (w === 1) return E1 - p.Eg; if (w === 2) return E1; return p.R; }
  var PcQd = kernel({ Eg: 2.42, me: 0.19, mh: 0.8, eps: 8.9, R: 2.0, what: 0.0, n: 160.0, method: 0.0, noise: 0.003, seed: 11.0 }, function (p) {
    var n = Math.max(8, I(p.n)), E1 = qdE1(p), lo = p.Eg - 0.15, hi = Math.max(p.Eg + 1.2, E1 + 0.9), st = lcg(p.seed);
    var Es = [], ys = [], k, E, d, al, ymax = 0.0, fx = [], fy = [];
    for (k = 0; k < n; k++) {
      E = lo + (hi - lo) * k / (n - 1);
      d = E - E1;
      al = d > 0 ? Math.sqrt(d) / E : 0.0;
      al = al * (1.0 + p.noise * (2.0 * u(st) - 1.0));
      Es.push(E); ys.push((al * E) * (al * E));
    }
    for (k = 0; k < ys.length; k++) if (ys[k] > ymax) ymax = ys[k];
    for (k = 0; k < n; k++) if (0.15 * ymax <= ys[k] && ys[k] <= 0.65 * ymax) { fx.push(Es[k]); fy.push(ys[k]); }
    var ln = line(fx, fy), E0 = ln[1] !== 0 ? -ln[0] / ln[1] : 0.0, w = I(p.what), val;
    if (w === 1) val = E0 - p.Eg; else if (w === 2) val = E0; else val = qdRadius(p, E0);
    return base(val, qdExact(p), fx.length, [E0, hi], [], [0.0, ln[0] + ln[1] * hi], thin(Es, 160), thin(ys, 160),
      { E0: E0, Eg: p.Eg, shift: E0 - p.Eg, Rfit: qdRadius(p, E0) });
  });

  // ====================================================================================== BET
  function betVm(p) { return p.S * VSTP / (NA * SIG_N2); }
  function betVplat(p) { var Vp = p.d * p.S * 1e-3 / 4.0; return Vp * VSTP * RHO_LN2 / M_N2; }
  function betV(p, x) {
    var vm = betVm(p), C = p.C;
    if (x <= 0.35) return vm * C * x / ((1.0 - x) * (1.0 - x + C * x));
    var v35 = vm * C * 0.35 / (0.65 * (0.65 + C * 0.35)), vp = betVplat(p);
    return v35 + (vp - v35) * (1.0 - Math.exp(-(x - 0.35) / 0.08));
  }
  function betExact(p) { return I(p.what) === 1 ? p.d : p.S; }
  var PcBet = kernel({ S: 250.0, C: 100.0, d: 6.0, what: 0.0, n: 48.0, method: 0.0, noise: 0.003, seed: 7.0 }, function (p) {
    var n = Math.max(8, I(p.n)), st = lcg(p.seed), xs = [], vs = [], k, x, v, fx = [], fy = [];
    for (k = 0; k < n; k++) {
      x = 0.02 + 0.97 * k / (n - 1);
      v = betV(p, x) * (1.0 + p.noise * (2.0 * u(st) - 1.0));
      xs.push(x); vs.push(v);
    }
    for (k = 0; k < n; k++) if (0.05 <= xs[k] && xs[k] <= 0.30) { fx.push(xs[k]); fy.push(xs[k] / (vs[k] * (1.0 - xs[k]))); }
    var ln = line(fx, fy);
    var vm = (ln[0] + ln[1]) !== 0 ? 1.0 / (ln[0] + ln[1]) : 0.0;
    var C = ln[0] !== 0 ? 1.0 + ln[1] / ln[0] : 0.0;
    var S = vm * NA * SIG_N2 / VSTP;
    var Vp = vs[n - 1] * M_N2 / (VSTP * RHO_LN2);
    var d = S > 0 ? 4.0 * Vp / S * 1e3 : 0.0;
    var val = I(p.what) === 1 ? d : S, cx = [], cy = [];
    for (k = 0; k < 31; k++) { x = 0.02 + 0.33 * k / 30; cx.push(x); cy.push(vm * C * x / ((1.0 - x) * (1.0 - x + C * x))); }
    return base(val, betExact(p), fx.length, cx, [], cy, xs, vs, { vm: vm, C: C, S: S, Vp: Vp, d: d });
  });

  // ====================================================================================== DSC
  function dscC(p, T) {
    var c = p.cp0 + p.slope * (T - p.T0) + p.dcp / (1.0 + Math.exp(-(T - p.Tg) / p.wg)), q;
    q = (T - p.Tm) / p.wm;
    c += p.dHm * Math.exp(-0.5 * Math.pow(q, 2)) / (p.wm * Math.sqrt(2.0 * PI));
    if (p.dHcc > 0) { q = (T - p.Tcc) / p.wcc; c -= p.dHcc * Math.exp(-0.5 * Math.pow(q, 2)) / (p.wcc * Math.sqrt(2.0 * PI)); }
    return c;
  }
  function dscExact(p) { var w = I(p.what); if (w === 1) return p.Tm; if (w === 2) return (p.dHm - p.dHcc) / p.H100; return p.Tg; }
  function dscArea(Ts, cs, lo, hi) {
    var idx = [], k, j, a, b, s = 0.0, b0, b1;
    for (k = 0; k < Ts.length; k++) if (lo <= Ts[k] && Ts[k] <= hi) idx.push(k);
    if (idx.length < 3) return 0.0;
    a = idx[0]; b = idx[idx.length - 1];
    for (j = 0; j < idx.length - 1; j++) {
      k = idx[j];
      b0 = cs[a] + (cs[b] - cs[a]) * (Ts[k] - Ts[a]) / (Ts[b] - Ts[a]);
      b1 = cs[a] + (cs[b] - cs[a]) * (Ts[k + 1] - Ts[a]) / (Ts[b] - Ts[a]);
      s += 0.5 * ((cs[k] - b0) + (cs[k + 1] - b1)) * (Ts[k + 1] - Ts[k]);
    }
    return s;
  }
  var PcDsc = kernel({ Tg: 78.0, dcp: 0.3, wg: 2.0, Tm: 255.0, dHm: 50.0, wm: 4.0, Tcc: 135.0, dHcc: 25.0, wcc: 4.0, H100: 140.0,
    cp0: 1.2, slope: 0.002, T0: 25.0, T1: 300.0, beta: 10.0, gl: 50.0, gh: 105.0, ml: 225.0, mh: 285.0, cl: 110.0, ch: 160.0,
    what: 0.0, n: 400.0, method: 0.0, noise: 0.001, seed: 5.0 }, function (p) {
    var n = Math.max(40, I(p.n)), st = lcg(p.seed), f = p.beta / 60.0, Ts = [], hf = [], cs = [], k, T, q;
    for (k = 0; k < n; k++) {
      T = p.T0 + (p.T1 - p.T0) * k / (n - 1);
      q = f * dscC(p, T) * (1.0 + p.noise * (2.0 * u(st) - 1.0));
      Ts.push(T); hf.push(q); cs.push(q / f);
    }
    var w = I(p.what), bx1 = [], by1 = [], bx2 = [], by2 = [];
    for (k = 0; k < n; k++) {
      if (p.gl <= Ts[k] && Ts[k] <= p.gl + 12.0) { bx1.push(Ts[k]); by1.push(cs[k]); }
      if (p.gh - 12.0 <= Ts[k] && Ts[k] <= p.gh) { bx2.push(Ts[k]); by2.push(cs[k]); }
    }
    var l1 = line(bx1, by1), l2 = line(bx2, by2), Tg = 0.0, m0, m1, d0, d1;
    for (k = 0; k < n - 1; k++) {
      if (Ts[k] < p.gl || Ts[k + 1] > p.gh) continue;
      m0 = 0.5 * (l1[0] + l1[1] * Ts[k] + l2[0] + l2[1] * Ts[k]);
      m1 = 0.5 * (l1[0] + l1[1] * Ts[k + 1] + l2[0] + l2[1] * Ts[k + 1]);
      d0 = cs[k] - m0; d1 = cs[k + 1] - m1;
      if (d0 < 0 && 0 <= d1) { Tg = Ts[k] + (Ts[k + 1] - Ts[k]) * (-d0) / (d1 - d0); break; }
    }
    var kb = -1;
    for (k = 1; k < n - 1; k++) if (p.ml <= Ts[k] && Ts[k] <= p.mh && (kb < 0 || cs[k] > cs[kb])) kb = k;
    var Tm = 0.0;
    if (kb > 0) {
      var y0 = cs[kb - 1], y1 = cs[kb], y2 = cs[kb + 1], den = y0 - 2.0 * y1 + y2;
      Tm = Ts[kb] + (den !== 0 ? 0.5 * (y0 - y2) / den : 0.0) * (Ts[kb + 1] - Ts[kb]);
    }
    var dHm = dscArea(Ts, cs, p.ml, p.mh);
    var dHcc = p.dHcc > 0 ? -dscArea(Ts, cs, p.cl, p.ch) : 0.0;
    var Xc = (dHm - dHcc) / p.H100;
    var val = w === 1 ? Tm : w === 2 ? Xc : Tg;
    return base(val, dscExact(p), n, thin(Ts, 200), [], thin(hf, 200), [], [], { Tg: Tg, Tm: Tm, dHm: dHm, dHcc: dHcc, Xc: Xc });
  });

  // ====================================================================================== TGA
  function tgaSteps(p) {
    var out = [], j;
    for (j = 1; j <= 3; j++) if (p['D' + j] > 0) out.push([p['T' + j], p['D' + j], p['w' + j]]);
    return out;
  }
  function tgaM(p, T) {
    var m = 100.0, ss = tgaSteps(p), j;
    for (j = 0; j < ss.length; j++) m -= ss[j][1] / (1.0 + Math.exp(-(T - ss[j][0]) / ss[j][2]));
    return m;
  }
  function tgaExact(p) {
    var w = I(p.what), ss = tgaSteps(p), k;
    if (w === 2) return ss.length;
    k = Math.max(1, Math.min(ss.length, I(p.k))) - 1;
    return w === 1 ? ss[k][0] : ss[k][1];
  }
  var PcTga = kernel({ T1: 95.0, D1: 14.43, w1: 2.5, T2: 125.0, D2: 14.43, w2: 2.5, T3: 255.0, D3: 7.215, w3: 4.0, T0: 30.0,
    Tend: 350.0, k: 1.0, what: 0.0, n: 640.0, method: 0.0, noise: 0.00002, seed: 3.0 }, function (p) {
    var n = Math.max(40, I(p.n)), st = lcg(p.seed), Ts = [], ms = [], k, j, T, dt = [], top = 0.0, peaks = [], ok;
    for (k = 0; k < n; k++) {
      T = p.T0 + (p.Tend - p.T0) * k / (n - 1);
      Ts.push(T); ms.push(tgaM(p, T) * (1.0 + p.noise * (2.0 * u(st) - 1.0)));
    }
    for (k = 0; k < n; k++) dt.push(0.0);
    for (k = 1; k < n - 1; k++) dt[k] = -(ms[k + 1] - ms[k - 1]) / (Ts[k + 1] - Ts[k - 1]);
    for (k = 0; k < n; k++) if (dt[k] > top) top = dt[k];
    for (k = 3; k < n - 3; k++) {
      if (dt[k] < 0.05 * top) continue;
      ok = true;
      for (j = k - 3; j < k + 4; j++) if ((j < k && dt[j] >= dt[k]) || (j > k && dt[j] > dt[k])) ok = false;
      if (ok) {
        var y0 = dt[k - 1], y1 = dt[k], y2 = dt[k + 1], den = y0 - 2.0 * y1 + y2;
        peaks.push(Ts[k] + (den !== 0 ? 0.5 * (y0 - y2) / den : 0.0) * (Ts[k + 1] - Ts[k]));
      }
    }
    var np = peaks.length;
    function mAt(T2) {
      for (var q = 0; q < n - 1; q++) if (Ts[q] <= T2 && T2 <= Ts[q + 1]) return ms[q] + (ms[q + 1] - ms[q]) * (T2 - Ts[q]) / (Ts[q + 1] - Ts[q]);
      return T2 < Ts[0] ? ms[0] : ms[n - 1];
    }
    var w = I(p.what), kk = Math.max(1, Math.min(Math.max(np, 1), I(p.k))) - 1, loss = 0.0, tpk = 0.0;
    if (np > 0) {
      var left = kk === 0 ? p.T0 : 0.5 * (peaks[kk - 1] + peaks[kk]);
      var right = kk === np - 1 ? p.Tend : 0.5 * (peaks[kk] + peaks[kk + 1]);
      loss = mAt(left) - mAt(right);
      tpk = peaks[kk];
    }
    var val = w === 2 ? np : w === 1 ? tpk : loss;
    return base(val, tgaExact(p), np, thin(Ts, 200), [], thin(ms, 200), thin(Ts, 200), thin(dt, 200),
      { peaks: peaks, loss: loss, tpk: tpk, nsteps: np });
  });

  // ====================================================================================== powder XRD
  function xrdRefl(p) {
    var lat = I(p.lat), a = p.a, c = p.c, lam = p.lam, out = [], h, k, l, inv, d, sn, tt, mult, N, seen = {};
    if (lat === 2) {
      for (h = 0; h < 4; h++) for (k = 0; k < h + 1; k++) for (l = 0; l < 5; l++) {
        if (h === 0 && k === 0 && l === 0) continue;
        if (l % 2 === 1 && (h - k) % 3 === 0) continue;
        inv = 4.0 / 3.0 * (h * h + h * k + k * k) / (a * a) + l * l / (c * c);
        d = 1.0 / Math.sqrt(inv);
        sn = lam / (2.0 * d);
        if (sn >= 1) continue;
        tt = 2.0 * Math.asin(sn) * 180.0 / PI;
        mult = h > 0 ? (h === k || k === 0 ? 6.0 : 12.0) * (l === 0 ? 1.0 : 2.0) : 2.0;
        out.push([tt, d, 0.0, mult]);
      }
    } else {
      for (h = 0; h < 7; h++) for (k = 0; k < h + 1; k++) for (l = 0; l < k + 1; l++) {
        if (h === 0) continue;
        N = h * h + k * k + l * l;
        if (lat === 0 && !((h % 2 === k % 2) && (k % 2 === l % 2))) continue;
        if (lat === 1 && (h + k + l) % 2 === 1) continue;
        d = a / Math.sqrt(N);
        sn = lam / (2.0 * d);
        if (sn >= 1) continue;
        if (seen[N] !== undefined) { out[seen[N]][3] += 8.0; continue; }
        seen[N] = out.length;
        out.push([2.0 * Math.asin(sn) * 180.0 / PI, d, N, 8.0]);
      }
    }
    var res = [], j;
    for (j = 0; j < out.length; j++) if (p.tt0 <= out[j][0] && out[j][0] <= p.tt1) res.push(out[j]);
    res.sort(function (x, y) { return x[0] - y[0]; });
    return res;
  }
  function xrdBeta(p, tt) {
    var th = tt * PI / 360.0;
    return (p.K * p.lam / (p.L * Math.cos(th)) + 4.0 * p.eps * Math.tan(th)) * 180.0 / PI + p.bi;
  }
  function xrdExact(p) { var w = I(p.what); if (w === 1) return p.eps; if (w === 2) return p.a; return p.L; }
  var PcXrd = kernel({ lat: 0.0, a: 0.35238, c: 0.0, L: 20.0, eps: 0.0, bi: 0.08, lam: 0.15406, K: 0.9, tt0: 30.0, tt1: 100.0,
    what: 0.0, n: 4000.0, method: 0.0, noise: 0.002, seed: 9.0 }, function (p) {
    var n = Math.max(200, I(p.n)), refl = xrdRefl(p), st = lcg(p.seed), I0 = [], top = 0.0, j, k, th, lp, bg, x, y, b;
    for (j = 0; j < refl.length; j++) {
      th = refl[j][0] * PI / 360.0;
      lp = (1.0 + Math.pow(Math.cos(2.0 * th), 2)) / (Math.pow(Math.sin(th), 2) * Math.cos(th));
      I0.push(refl[j][3] * lp);
      if (refl[j][3] * lp > top) top = refl[j][3] * lp;
    }
    bg = 0.02 * top;
    var xs = [], ys = [];
    for (k = 0; k < n; k++) {
      x = p.tt0 + (p.tt1 - p.tt0) * k / (n - 1);
      y = bg;
      for (j = 0; j < refl.length; j++) {
        b = xrdBeta(p, refl[j][0]);
        y += I0[j] * Math.exp(-4.0 * Math.log(2.0) * Math.pow(x - refl[j][0], 2) / (b * b));
      }
      ys.push(y * (1.0 + p.noise * (2.0 * u(st) - 1.0)));
      xs.push(x);
    }
    var lo = ys[0], z = [], zmax = 0.0;
    for (k = 0; k < n; k++) if (ys[k] < lo) lo = ys[k];
    for (k = 0; k < n; k++) z.push(ys[k] - lo);
    for (k = 0; k < n; k++) if (z[k] > zmax) zmax = z[k];
    var found = [], m = Math.max(2, I(0.15 / ((p.tt1 - p.tt0) / (n - 1)))), ok, i;
    for (k = m; k < n - m; k++) {
      if (z[k] < 0.04 * zmax) continue;
      ok = true;
      for (j = k - m; j < k + m + 1; j++) if ((j < k && z[j] >= z[k]) || (j > k && z[j] > z[k])) { ok = false; break; }
      if (ok && z[k - m] > 0 && z[k + m] > 0) {
        var l0 = Math.log(z[k - m]), l1 = Math.log(z[k]), l2 = Math.log(z[k + m]), den = l0 - 2.0 * l1 + l2;
        var dx = den !== 0 ? 0.5 * (l0 - l2) / den : 0.0;
        var hh = Math.exp(l1 - 0.25 * (l0 - l2) * dx);
        var cen = xs[k] + dx * (xs[k + m] - xs[k]);
        var half = 0.5 * hh, xl, xr;
        i = k;
        while (i > 0 && z[i] > half) i--;
        xl = xs[i] + (xs[i + 1] - xs[i]) * (half - z[i]) / (z[i + 1] - z[i]);
        i = k;
        while (i < n - 1 && z[i] > half) i++;
        xr = xs[i - 1] + (xs[i] - xs[i - 1]) * (z[i - 1] - half) / (z[i - 1] - z[i]);
        found.push([cen, xr - xl]);
      }
    }
    var X = [], Y = [], A = [], bb;
    for (j = 0; j < found.length; j++) {
      th = found[j][0] * PI / 360.0;
      bb = (found[j][1] - p.bi) * PI / 180.0;
      X.push(4.0 * Math.sin(th));
      Y.push(bb * Math.cos(th));
      if (j < refl.length && refl[j][2] > 0) A.push(p.lam / (2.0 * Math.sin(th)) * Math.sqrt(refl[j][2]));
    }
    var ln = line(X, Y);
    var Lwh = ln[0] > 0 ? p.K * p.lam / ln[0] : 0.0;
    var Lsch = Y.length > 0 && Y[0] > 0 ? p.K * p.lam / Y[0] : 0.0;
    var am = 0.0;
    for (j = 0; j < A.length; j++) am += A[j];
    am = A.length > 0 ? am / A.length : 0.0;
    var w = I(p.what), val = w === 1 ? ln[1] : w === 2 ? am : w === 3 ? Lsch : Lwh;
    var cx = [0.0, X.length ? X[X.length - 1] : 1.0], cy = [ln[0], ln[0] + ln[1] * cx[1]];
    return base(val, xrdExact(p), found.length, thin(xs, 400), [], thin(ys, 400), X, Y,
      { wh: [cx, cy], nfound: found.length, nrefl: refl.length, Lwh: Lwh, strain: ln[1], Lsch: Lsch, a_fit: am });
  });

  // ====================================================================================== TEM: SAED + grain size
  var C_LIGHT = 299792458.0;
  function temLambda(V) { return H / Math.sqrt(2.0 * ME * QE * V * (1.0 + QE * V / (2.0 * ME * C_LIGHT * C_LIGHT))); }
  function temN(lat, k) {
    var seq = lat === 0 ? [3.0, 4.0, 8.0, 11.0, 12.0, 16.0] : [2.0, 4.0, 6.0, 8.0, 10.0, 12.0];
    return seq[Math.max(0, Math.min(seq.length - 1, k - 1))];
  }
  function temGrains(p) {
    var st = lcg(p.seed), out = [], i, u1, u2, z;
    for (i = 0; i < I(p.Ng); i++) {
      u1 = u(st); u2 = u(st);
      z = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * PI * u2);
      out.push(p.D0 * Math.exp(p.sg * z));
    }
    return out;
  }
  function meanSd(xs) {
    var s = 0.0, q = 0.0, i, m;
    for (i = 0; i < xs.length; i++) s += xs[i];
    m = s / xs.length;
    for (i = 0; i < xs.length; i++) q += (xs[i] - m) * (xs[i] - m);
    return [m, Math.sqrt(q / xs.length)];
  }
  function temExact(p) {
    if (I(p.what) === 1) return p.a / Math.sqrt(temN(I(p.lat), I(p.k)));
    var ms = meanSd(temGrains(p));
    return I(p.what) === 2 ? ms[1] : ms[0];
  }
  var PcTem = kernel({ D0: 12.0, sg: 0.25, Ng: 300.0, V: 200000.0, Lc: 0.5, a: 0.40782, lat: 0.0, k: 1.0, what: 0.0, n: 1024.0,
    method: 0.0, seed: 61.0 }, function (p) {
    var n = Math.max(64, I(p.n)), w = I(p.what), lat = I(p.lat), k, i;
    if (w === 1) {
      var lam = temLambda(p.V), pix = 0.06 / n, rs = [], ds = [], rx = [], d, R, Rm;
      for (k = 1; k < 7; k++) {
        d = p.a / Math.sqrt(temN(lat, k)) * 1e-9;
        R = lam * p.Lc / d;
        Rm = I(R / pix) * pix;
        rx.push(k); rs.push(R * 1e3); ds.push(Rm > 0 ? lam * p.Lc / Rm * 1e9 : 0.0);
      }
      var kk = Math.max(1, Math.min(6, I(p.k)));
      return base(ds[kk - 1], temExact(p), n, rx, [], rs, rx, rs, { lam: lam, dsp: ds, Lc: p.Lc });
    }
    var gs = temGrains(p), pixg = 20.0 * p.D0 / n, meas = [], bins = [], top = 3.0 * p.D0, b, cx = [];
    for (i = 0; i < gs.length; i++) meas.push(I(gs[i] / pixg) * pixg);
    var ms = meanSd(meas);
    for (i = 0; i < 20; i++) bins.push(0.0);
    for (i = 0; i < meas.length; i++) { b = Math.floor(meas[i] / top * 20); if (b >= 0 && b < 20) bins[b] += 1.0; }
    for (i = 0; i < 20; i++) cx.push(top * (i + 0.5) / 20);
    return base(w === 2 ? ms[1] : ms[0], temExact(p), meas.length, cx, [], bins, [], [], { pix: pixg, mean: ms[0], sd: ms[1] });
  });

  // ====================================================================================== gas sensor transient
  function gasExact(p) { var w = I(p.what); if (w === 1) return p.tr * Math.log(10.0); if (w === 2) return p.td * Math.log(10.0); return p.Ra / p.Rg; }
  var PcGas = kernel({ Ra: 2.0e6, Rg: 1.0e5, tr: 8.0, td: 40.0, t1: 60.0, t2: 360.0, T: 900.0, what: 0.0, n: 900.0, method: 0.0,
    noise: 0.002, seed: 71.0 }, function (p) {
    var n = Math.max(50, I(p.n)), st = lcg(p.seed), Ra = p.Ra, Rg = p.Rg, k, t, R;
    var R2 = Rg + (Ra - Rg) * Math.exp(-(p.t2 - p.t1) / p.tr), ts = [], Rs = [];
    for (k = 0; k < n; k++) {
      t = p.T * k / (n - 1);
      if (t < p.t1) R = Ra;
      else if (t < p.t2) R = Rg + (Ra - Rg) * Math.exp(-(t - p.t1) / p.tr);
      else R = Ra + (R2 - Ra) * Math.exp(-(t - p.t2) / p.td);
      ts.push(t); Rs.push(R * (1.0 + p.noise * (2.0 * u(st) - 1.0)));
    }
    var sa = 0.0, na = 0, sg = 0.0, ng = 0;
    for (k = 0; k < n; k++) {
      if (ts[k] < p.t1) { sa += Rs[k]; na++; }
      else if (p.t2 - 0.1 * (p.t2 - p.t1) <= ts[k] && ts[k] < p.t2) { sg += Rs[k]; ng++; }
    }
    var ra = na ? sa / na : 0.0, rg = ng ? sg / ng : 0.0, lvl = ra - 0.9 * (ra - rg), tres = 0.0, trec = 0.0;
    for (k = 0; k < n - 1; k++) if (ts[k] >= p.t1 && Rs[k] > lvl && lvl >= Rs[k + 1]) { tres = ts[k] + (ts[k + 1] - ts[k]) * (Rs[k] - lvl) / (Rs[k] - Rs[k + 1]) - p.t1; break; }
    var lv2 = rg + 0.9 * (ra - rg);
    for (k = 0; k < n - 1; k++) if (ts[k] >= p.t2 && Rs[k] < lv2 && lv2 <= Rs[k + 1]) { trec = ts[k] + (ts[k + 1] - ts[k]) * (lv2 - Rs[k]) / (Rs[k + 1] - Rs[k]) - p.t2; break; }
    var w = I(p.what), sens = rg > 0 ? ra / rg : 0.0, val = w === 1 ? tres : w === 2 ? trec : sens;
    return base(val, gasExact(p), n, thin(ts, 300), [], thin(Rs.map(function (r) { return r / 1e3; }), 300), [], [],
      { Ra: ra, Rg: rg, sens: sens, tres: tres, trec: trec });
  });

  // ====================================================================================== sputtered film: XRR + XRD
  function xrrR(p, th) {
    var s2 = Math.sin(th) * Math.sin(th), k0 = Math.sqrt(s2), k1 = Math.sqrt(s2 - 2.0 * p.dl1), k2 = Math.sqrt(s2 - 2.0 * p.dl2);
    var r01 = (k0 - k1) / (k0 + k1), r12 = (k1 - k2) / (k1 + k2), ph = 4.0 * PI * k1 * p.d / p.lam, c = Math.cos(ph);
    return (r01 * r01 + r12 * r12 + 2.0 * r01 * r12 * c) / (1.0 + r01 * r01 * r12 * r12 + 2.0 * r01 * r12 * c);
  }
  function quad(xs, ys) {
    var s0 = xs.length, s1 = 0, s2 = 0, s3 = 0, s4 = 0, t0 = 0, t1 = 0, t2 = 0, k, x, D;
    for (k = 0; k < xs.length; k++) {
      x = xs[k]; s1 += x; s2 += x * x; s3 += x * x * x; s4 += x * x * x * x; t0 += ys[k]; t1 += x * ys[k]; t2 += x * x * ys[k];
    }
    D = s0 * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2);
    if (Math.abs(D) < 1e-300) return [0, 0, 0];
    return [(t0 * (s2 * s4 - s3 * s3) - s1 * (t1 * s4 - s3 * t2) + s2 * (t1 * s3 - s2 * t2)) / D,
      (s0 * (t1 * s4 - s3 * t2) - t0 * (s1 * s4 - s3 * s2) + s2 * (s1 * t2 - t1 * s2)) / D,
      (s0 * (s2 * t2 - t1 * s3) - s1 * (s1 * t2 - t1 * s2) + t0 * (s1 * s3 - s2 * s2)) / D];
  }
  function filmExact(p) { return I(p.what) === 1 ? p.L : p.d; }
  var PcFilmP = { d: 20.0, dl1: 2.2e-5, dl2: 7.6e-6, lam: 0.15406, th0: 0.5, th1: 2.5, noise: 0.003, lat: 0.0, a: 0.36149, c: 0.0,
    L: 15.0, eps: 0.0, bi: 0.08, K: 0.9, tt0: 30.0, tt1: 100.0, what: 0.0, n: 2000.0, method: 0.0, seed: 83.0 };
  var PcFilm = kernel(PcFilmP, function (p) {
    if (I(p.what) === 1) {
      var q = copy(p); q.what = 3.0; q.noise = 0.002;
      var sx = PcXrd.init(q);
      sx.exact = filmExact(p); sx.err = errOf(sx.val, sx.exact);
      return sx;
    }
    var n = Math.max(100, I(p.n)), st = lcg(p.seed), ths = [], lr = [], k, j, tdeg, R;
    for (k = 0; k < n; k++) {
      tdeg = p.th0 + (p.th1 - p.th0) * k / (n - 1);
      R = xrrR(p, tdeg * PI / 180.0) * (1.0 + p.noise * (2.0 * u(st) - 1.0));
      ths.push(tdeg); lr.push(Math.log10(R));
    }
    var step = (p.th1 - p.th0) / (n - 1), m = Math.max(2, I(0.02 / step)), mins = [], ok;
    for (k = m; k < n - m; k++) {
      ok = true;
      for (j = k - m; j < k + m + 1; j++) if ((j < k && lr[j] <= lr[k]) || (j > k && lr[j] < lr[k])) { ok = false; break; }
      if (ok) {
        var y0 = lr[k - 1], y1 = lr[k], y2 = lr[k + 1], den = y0 - 2.0 * y1 + y2;
        mins.push(ths[k] + (den !== 0 ? 0.5 * (y0 - y2) / den : 0.0) * step);
      }
    }
    var js = [], ys = [], s, val = 0.0, cf;
    for (j = 0; j < mins.length; j++) { s = Math.sin(mins[j] * PI / 180.0); js.push(j); ys.push(s * s); }
    if (js.length >= 3) { cf = quad(js, ys); if (cf[2] > 0) val = p.lam / (2.0 * Math.sqrt(cf[2])); }
    return base(val, filmExact(p), mins.length, thin(ths, 400), [], thin(lr, 400), js, ys, { mins: mins });
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
    K: { pc9_xcom: PcXcom, pc9_qd: PcQd, pc9_bet: PcBet, pc9_dsc: PcDsc, pc9_tga: PcTga, pc9_xrd: PcXrd, pc9_tem: PcTem, pc9_gas: PcGas,
      pc9_film: PcFilm },
    TEXTBOOK: { pc9_xcom_v: xcExact, pc9_qd_v: qdExact, pc9_bet_v: betExact, pc9_dsc_v: dscExact, pc9_tga_v: tgaExact, pc9_xrd_v: xrdExact,
      pc9_tem_v: temExact, pc9_gas_v: gasExact, pc9_film_v: filmExact },
    CALCS: {
      pc9_finest: { label: 'answer on the finest data', unit: '', needs: ['n', 'val'], fn: finest },
      pc9_best: { label: 'best value', unit: '', needs: ['n', 'val', 'err'], fn: best }
    }
  });
})(typeof window !== 'undefined' ? window : this);
