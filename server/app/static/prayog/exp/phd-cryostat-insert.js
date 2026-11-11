/* Prayogshala studio module: CRYOSTAT-AND-INSERT RIG (low-temperature superconductivity and thermometry).
   One rig for a family of research benches. The lab's kernel (packs/phd_cond.js) gives every number; the adapter for
   that kernel (below) says what is swept, what is read and how the result is found from the student's own table or
   captured trace - peaks, plateaus, zero crossings, fitted decays - never by reading the formula back.
   Sample on a rod, lowered into the cryostat; the controller sets the temperature, a live screen plots the reading. */
HoolaStudio.define('phd-cryostat-insert', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KN = HK.K[S.lab.kernel], p = HK.paramsFor(S.lab.kernel, S.lab.params);
  var V_ = S.lab.variant || {}, CFG = S.lab.cfg || {};
  var H0 = 6.62607015e-34, HBAR = H0 / (2 * Math.PI), QE = 1.602176634e-19, MUB = 9.2740100783e-24, MUN = 5.0507837461e-27, PHI0 = H0 / (2 * QE);
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function sig(v, d) { return isFinite(v) ? Number(v).toPrecision(d || 4) : '—'; }
  function line(pts) {
    var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, d, m;
    if (n < 2) return [0, 0];
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    d = n * sxx - sx * sx; if (d === 0) return [0, 0];
    m = (n * sxy - sx * sy) / d; return [m, (sy - m * sx) / n];
  }
  function peaks(xs, ys, kind) {            // parabolic-refined local maxima (kind +1) or minima (kind -1)
    var out = [], i, a, b, c, d;
    for (i = 1; i < xs.length - 1; i++) {
      a = kind * ys[i - 1]; b = kind * ys[i]; c = kind * ys[i + 1];
      if (b > a && b >= c) { d = a - 2 * b + c; out.push(xs[i] + (d !== 0 ? (xs[i + 1] - xs[i - 1]) / 2 * 0.5 * (a - c) / d : 0)); }
    }
    return out;
  }
  function cross(xs, ys, level, dir) {     // linear-interpolated crossings of `level`; dir +1 rising, -1 falling
    var out = [], i, a, b;
    for (i = 0; i < xs.length - 1; i++) {
      a = ys[i] - level; b = ys[i + 1] - level;
      if ((dir > 0 && a < 0 && b >= 0) || (dir < 0 && a > 0 && b <= 0)) out.push(xs[i] + (xs[i + 1] - xs[i]) * a / (a - b));
    }
    return out;
  }
  function smooth(ys, k) { var o = [], i, j, s, n; for (i = 0; i < ys.length; i++) { s = 0; n = 0; for (j = Math.max(0, i - k); j <= Math.min(ys.length - 1, i + k); j++) { s += ys[j]; n++; } o.push(s / n); } return o; }
  function hash(seed, k) { var x = Math.sin(seed * 12.9898 + k * 78.233) * 43758.5453; return 2.0 * (x - Math.floor(x)) - 1.0; }
  var H = { hash: hash, rnd: rnd, sig: sig, line: line, peaks: peaks, cross: cross, smooth: smooth, H0: H0, HBAR: HBAR, QE: QE, MUB: MUB, MUN: MUN, PHI0: PHI0 };
  var ADAPT = {};
  // ======================================================================= adapters (one per kernel)
  var KJ = 2 * QE / H0;
  function lastRowKey(rows) { return rows.length ? rows[rows.length - 1]._k : null; }

  ADAPT.phd_scrt = function () {
    var BS = [0, 0.125, 0.25].map(function (m) { return rnd(m * p.Bc2, 3); }), TC = p.Tc0, HOT = 1.087 * TC;
    function q(x, tog) { return assign(p, { T: x, B: tog.B }); }
    function tcFrom(rows, B) {
      var rs = rows.filter(function (r) { return r.B === B; }).sort(function (a, b) { return a.T - b.T; }), hot = rs.filter(function (r) { return r.T >= HOT; }), mc, g, i, t;
      if (hot.length < 2) return null;
      mc = line(hot.map(function (r) { return [r.T, r.R]; }));
      g = rs.map(function (r) { return { T: r.T, f: r.R / (mc[0] * r.T + mc[1]) }; });
      for (i = 0; i < g.length - 1; i++) if (g[i].f < 0.5 && g[i + 1].f >= 0.5) {
        t = g[i].T + (0.5 - g[i].f) / (g[i + 1].f - g[i].f) * (g[i + 1].T - g[i].T);
        return { Tc: t, RRR: (mc[1] + mc[0] * 300) / mc[1] };
      }
      return null;
    }
    return {
      name: 'Four-probe resistance', xl: 'T (K)', yl: 'R (mΩ)', min: 6,
      toggles: [{ key: 'B', label: 'Applied field', def: 0, opts: BS.map(function (b) { return { v: b, l: b + ' T' }; }) }],
      range: function () { return { lo: rnd(0.76 * TC, 2), hi: rnd(1.42 * TC, 2), step: rnd(TC / 900, 4), def: rnd(1.087 * TC, 2), unit: 'K', dig: 2 }; },
      read: function (x, tog) { var r = KN.res(q(x, tog)); return { T: x, B: tog.B, R: r, V: r * p.I }; },
      curve: function (x, tog) { return KN.res(q(x, tog)) * 1000; },
      show: function (r, tog) { return r.B === tog.B; }, pt: function (r) { return [r.T, r.R * 1000]; },
      cols: [{ label: 'T (K)', get: function (r) { return r.T.toFixed(2); } }, { label: 'B (T)', get: function (r) { return String(r.B); } },
        { label: 'R (mΩ)', get: function (r) { return (r.R * 1000).toFixed(3); } }, { label: 'V (µV)', get: function (r) { return (r.V * 1e6).toFixed(2); } }],
      live: function (r) { return 'R = ' + (r.R * 1000).toFixed(3) + ' mΩ   V = ' + (r.V * 1e6).toFixed(2) + ' µV'; },
      plan: function () {
        var hot = [1.087, 1.196, 1.304, 1.413].map(function (m) { return rnd(m * TC, 3); }), w = p.w, tc10 = TC * (1 - Math.pow(BS[2] / p.Bc2, 2));
        return [{ tog: { B: 0 }, xs: hot.concat([-6, -4, -2, -1, -0.5, 0, 0.5, 1, 2, 4].map(function (d) { return rnd(TC + d * w, 4); })) },
          { tog: { B: BS[2] }, xs: hot.slice(0, 2).concat([-4, -2, -1, 0, 1, 2].map(function (d) { return rnd(tc10 + d * w, 4); })) }];
      },
      result: function (rows) {
        var r0 = tcFrom(rows, 0), r10 = tcFrom(rows, BS[2]), tc0 = KN.tc(q(0, { B: 0 }));
        if (!r0) return null;
        return { label: 'Critical temperature Tc (zero field)', value: r0.Tc, unit: 'K', digits: 2, truth: tc0,
          note: 'Taken where R has fallen to half the straight-line normal-state value. Residual resistance ratio R(300 K)/R(0 K, extrapolated) = ' + sig(r0.RRR, 3) + '.' +
            (r10 ? ' At ' + BS[2] + ' T the same method gives Tc = ' + sig(r10.Tc, 4) + ' K: the field has pushed the transition down by ' + sig(r0.Tc - r10.Tc, 3) + ' K.' : ' Record points at ' + BS[2] + ' T as well to see the transition move.') };
      },
      info: 'Four-lead resistance of the bar against temperature. The current leads and the voltage leads are separate, so the contact resistance does not count.'
    };
  };

  ADAPT.phd_scic = function () {
    var TS = [rnd(0.84 * p.Tc, 1), p.T, rnd(0.5 * p.Tc, 1)].filter(function (v, i, ar) { return ar.indexOf(v) === i; }), BS = [0, p.B0, 2 * p.B0];
    function q(x, tog) { return assign(p, { I: x, T: tog.T, B: tog.B }); }
    var vc = p.Ec * p.Lv;
    return {
      name: 'Critical-current I-V', xl: 'I (A)', yl: 'V (µV)', min: 5,
      toggles: [{ key: 'T', label: 'Temperature', def: p.T, opts: TS.map(function (t) { return { v: t, l: t + ' K' }; }) },
        { key: 'B', label: 'Field', def: 0, opts: BS.map(function (b) { return { v: b, l: b + ' T' }; }) }],
      range: function (tog) { return { lo: 0, hi: 1.4 * KN.ic(q(0, tog)), step: KN.ic(q(0, tog)) / 800, def: 0.5 * KN.ic(q(0, tog)), unit: 'A', dig: 3 }; },
      read: function (x, tog) { return { T: tog.T, B: tog.B, I: x, V: KN.volts(q(x, tog), x) }; },
      curve: function (x, tog) { return KN.volts(q(x, tog), x) * 1e6; },
      show: function (r, tog) { return r.T === tog.T && r.B === tog.B; }, pt: function (r) { return [r.I, r.V * 1e6]; },
      cols: [{ label: 'T (K)', get: function (r) { return String(r.T); } }, { label: 'B (T)', get: function (r) { return String(r.B); } },
        { label: 'I (A)', get: function (r) { return r.I.toFixed(4); } }, { label: 'V (µV)', get: function (r) { return (r.V * 1e6).toPrecision(4); } }],
      live: function (r) { return 'I = ' + r.I.toFixed(4) + ' A   V = ' + (r.V * 1e6).toPrecision(4) + ' µV   (criterion ' + (vc * 1e6).toFixed(2) + ' µV)'; },
      plan: function () {
        return [TS[0], p.T].map(function (t) { var ic = KN.ic(q(0, { T: t, B: 0 })); return { tog: { T: t, B: 0 }, xs: [0.7, 0.85, 0.95, 1.0, 1.05, 1.15, 1.3].map(function (m) { return rnd(ic * m, 4); }) }; });
      },
      result: function (rows) {
        var k = lastRowKey(rows), rs, i, a, b, ic, tog;
        if (!k) return null;
        rs = rows.filter(function (r) { return r._k === k && r.V > 0; }).sort(function (u, v) { return u.I - v.I; });
        for (i = 0; i < rs.length - 1; i++) if (rs[i].V < vc && rs[i + 1].V >= vc) {
          a = rs[i]; b = rs[i + 1];
          ic = Math.exp(Math.log(a.I) + (Math.log(vc) - Math.log(a.V)) / (Math.log(b.V) - Math.log(a.V)) * (Math.log(b.I) - Math.log(a.I)));
          tog = { T: a.T, B: a.B };
          return { label: 'Critical current Ic at ' + a.T + ' K, ' + a.B + ' T', value: ic, unit: 'A', digits: 3, truth: KN.ic(q(0, tog)),
            note: 'Where the voltage crosses ' + (vc * 1e6).toFixed(2) + ' µV (1 µV/cm over ' + (p.Lv * 100).toFixed(1) + ' cm), found between the neighbouring points on a log-log line. Critical current density Jc = Ic/A = ' + sig(ic / p.area / 1e4, 3) + ' A/cm².' };
        }
        return null;
      },
      info: 'Current leads carry the transport current; a nanovoltmeter reads the voltage on the inner pair.'
    };
  };

  ADAPT.phd_acsusc = function () {
    return {
      name: 'Two-coil susceptibility', xl: 'T (K)', yl: "chi' (blue), chi'' (amber)", min: 12,
      toggles: [],
      range: function () { return { lo: rnd(0.04 * p.Tc, 2), hi: rnd(1.2 * p.Tc, 1), step: rnd(p.Tc / 900, 4), def: rnd(0.55 * p.Tc, 2), unit: 'K', dig: 2 }; },
      read: function (x) { var q = assign(p, { T: x }); return { T: x, c1: KN.chi1(q), c2: KN.chi2(q) }; },
      curve: function (x) { return KN.chi1(assign(p, { T: x })); },
      curve2: function (x) { return KN.chi2(assign(p, { T: x })); },
      show: function () { return true; }, pt: function (r) { return [r.T, r.c1]; }, pt2: function (r) { return [r.T, r.c2]; },
      cols: [{ label: 'T (K)', get: function (r) { return r.T.toFixed(2); } }, { label: "chi'", get: function (r) { return r.c1.toFixed(5); } }, { label: "chi''", get: function (r) { return r.c2.toFixed(5); } }],
      live: function (r) { return "chi' = " + r.c1.toFixed(5) + "   chi'' = " + r.c2.toFixed(5); },
      plan: function () { return [{ tog: {}, xs: [0.054, 0.15, 0.3, 0.5, 0.7, 0.9].map(function (m) { return rnd(m * p.Tc, 2); }).concat([-6, -4, -2, -1, 0, 1, 2, 4, 6, 12, 20].map(function (d) { return rnd(p.Tc + d * p.w, 3); })) }]; },
      result: function (rows) {
        var rs = rows.slice().sort(function (a, b) { return a.T - b.T; }), i, bi = 0, tc, a, b, c, d, lo, f, lam, lam0, t4;
        if (rs.length < 8) return null;
        for (i = 1; i < rs.length; i++) if (rs[i].c2 > rs[bi].c2) bi = i;
        if (bi < 1 || bi > rs.length - 2) return null;
        a = rs[bi - 1].c2; b = rs[bi].c2; c = rs[bi + 1].c2; d = a - 2 * b + c;
        tc = d !== 0 && Math.abs(rs[bi + 1].T - rs[bi].T - (rs[bi].T - rs[bi - 1].T)) < 1e-9 ? rs[bi].T + (rs[bi + 1].T - rs[bi].T) * 0.5 * (a - c) / d : rs[bi].T;
        lo = rs[0]; if (lo.T > 0.2 * tc) return null;
        f = -lo.c1; lam = p.a * (1 - Math.pow(1 - f, 1 / 3)); t4 = Math.pow(lo.T / tc, 4); lam0 = lam * Math.sqrt(1 - t4);
        return { label: 'London penetration depth λ_L', value: lam0 * 1e9, unit: 'nm', digits: 1, truth: KN.lam0(p) * 1e9,
          note: "Tc = " + sig(tc, 4) + " K from the peak of chi''. At " + lo.T + " K the sphere shields a fraction f = " + sig(f, 4) + " of its volume, so the field reaches a depth λ = a[1 - (1 - f)^(1/3)] = " + sig(lam * 1e9, 3) + " nm; correcting for the (1 - t⁴) temperature factor gives λ_L." };
      },
      info: 'A drive coil and a pick-up coil surround the sphere. A shielding sample reduces the mutual inductance (chi\' < 0); dissipation shows as chi\'\'.'
    };
  };

  ADAPT.phd_therm = function () {
    var k = Math.round(p.sensor), U = { 1: { u: 'mV', k: 1e3, d: 3, n: 'silicon diode' }, 2: { u: 'Ω', k: 1, d: 4, n: 'platinum RTD' }, 3: { u: 'Ω', k: 1, d: 1, n: 'RuO2 resistor' }, 4: { u: 'µV', k: 1e6, d: 2, n: 'thermocouple' } }[k] || { u: '', k: 1, d: 3, n: 'sensor' };
    var R = { 1: [60, 300], 2: [70, 300], 3: [8, 100], 4: [30, 300] }[k] || [60, 300];
    function q(x, tog) { return assign(p, { T: x, I: p.I * tog.I }); }
    return {
      name: 'Sensor calibration (' + U.n + ')', xl: 'T (K)', yl: 'reading (' + U.u + ')', min: 6, unit: U,
      toggles: [{ key: 'I', label: 'Excitation', def: 1, opts: [{ v: 1, l: '1×' }, { v: 10, l: '10×' }, { v: 100, l: '100×' }] }],
      range: function () { return { lo: R[0], hi: R[1], step: 0.1, def: Math.max(R[0], Math.min(R[1], p.T)), unit: 'K', dig: 1 }; },
      read: function (x, tog) { var qq = q(x, tog); return { T: x, I: tog.I, X: KN.read(qq), dT: KN.dtheat(qq) }; },
      curve: function (x, tog) { return KN.read(q(x, tog)) * U.k; },
      show: function (r, tog) { return r.I === tog.I; }, pt: function (r) { return [r.T, r.X * U.k]; },
      cols: [{ label: 'T set (K)', get: function (r) { return r.T.toFixed(2); } }, { label: 'excitation', get: function (r) { return r.I + '×'; } },
        { label: 'reading (' + U.u + ')', get: function (r) { return (r.X * U.k).toFixed(U.d + 1); } }, { label: 'self-heating (mK)', get: function (r) { return (r.dT * 1000).toFixed(2); } }],
      live: function (r) { return 'reading = ' + (r.X * U.k).toFixed(U.d + 1) + ' ' + U.u + '   self-heating ≈ ' + (r.dT * 1000).toFixed(2) + ' mK'; },
      plan: function () {
        var t = p.T, xs = [t - 1, t, t + 1, t * 0.5, t * 1.5, t * 2.5].map(function (v) { return rnd(Math.max(R[0], Math.min(R[1], v)), 2); });
        return [{ tog: { I: 1 }, xs: xs }, { tog: { I: 100 }, xs: [t] }];
      },
      result: function (rows) {
        var rs = rows.filter(function (r) { return r.I === 1; }), lo = null, hi = null, i, hot = null;
        for (i = 0; i < rs.length; i++) { if (Math.abs(rs[i].T - (p.T - 1)) < 0.05) lo = rs[i]; if (Math.abs(rs[i].T - (p.T + 1)) < 0.05) hi = rs[i]; }
        if (!lo || !hi) return null;
        for (i = 0; i < rows.length; i++) if (rows[i].I > 1 && Math.abs(rows[i].T - p.T) < 0.05) hot = rows[i];
        return { label: 'Sensitivity dX/dT at ' + p.T + ' K', value: (hi.X - lo.X) / 2 * U.k, unit: U.u + '/K', digits: 4, truth: KN.slope_exact(p, p.T) * U.k,
          note: 'From the readings at ' + (p.T - 1) + ' K and ' + (p.T + 1) + ' K.' + (hot ? ' At ' + hot.I + '× excitation the sensor sits ' + sig(hot.dT * 1000, 3) + ' mK above the bath.' : ' Record one reading at a larger excitation to see the self-heating error.') };
      },
      info: U.n + ' on the insert, read at constant excitation. Self-heating is P/G.'
    };
  };


  // ======================================================================= the generic bench engine
  var A = ADAPT[S.lab.kernel]();
  var st = { mounted: false, on: false, tog: {}, x: 0, cap: null, prog: 1, busy: false };
  (A.toggles || []).forEach(function (t) { st.tog[t.key] = t.def; });
  if (!A.trace) st.x = A.range(st.tog).def;
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 24); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }
  function busy() { if (S.hand.busy || st.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function keyOf() { return JSON.stringify(st.tog); }
  function togText() { return (A.toggles || []).map(function (t) { var o = t.opts.filter(function (q) { return q.v === st.tog[t.key]; })[0]; return t.label + ': ' + (o ? o.l : st.tog[t.key]); }).join(' · '); }

  // ---------------- the live-trace screen
  var scopeG = new T.Group(); S.scene.add(scopeG); scopeG.position.set(0.3, 0, -0.1); scopeG.rotation.y = -0.28;
  var cs = S.rounded(0.27, 0.2, 0.2, 0.01, new T.MeshStandardMaterial({ color: 0xcfcbbf, roughness: 0.5 })); cs.rotation.x = -Math.PI / 2; cs.position.y = 0.103; scopeG.add(cs);
  var scrTex = S.liveTex(640, 480);
  mk(scopeG, box(0.2, 0.15, 0.004), M.grey, -0.02, 0.12, 0.1005);
  var scr = new T.Mesh(new T.PlaneGeometry(0.19, 0.14), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false })); scr.position.set(-0.02, 0.12, 0.1035); scopeG.add(scr);
  var pwr = new T.Group(); pwr.position.set(0.1, 0.17, 0.1035); scopeG.add(pwr);
  var pwm = mk(pwr, cyl(0.011, 0.012, 0.012, 24), M.bakelite); pwm.rotation.x = Math.PI / 2; mk(pwr, box(0.0018, 0.011, 0.001), M.white, 0, 0.006, 0.007);
  for (var kb = 0; kb < 3; kb++) { var kk = mk(scopeG, cyl(0.007, 0.008, 0.01, 18), M.bakelite, 0.1, 0.12 - kb * 0.03, 0.1035); kk.rotation.x = Math.PI / 2; }
  var scl = S.label(A.sim ? 'SIMULATED INSTRUMENT · ' + A.name.toUpperCase() : A.name.toUpperCase(), { w: 0.17, ratio: 0.09, color: A.sim ? '#8a1f1a' : '#20252b' }); scl.position.set(-0.02, 0.035, 0.1035); scopeG.add(scl);
  S.contact(0.34, 0.26, 0.3, -0.1, 0.5);

  var lastKey = '', curveCache = { k: '', pts: [], pts2: [] };
  function curveFor() {
    var rg = A.range(st.tog), k = keyOf(), n = A.npts || 160, i, x;
    if (curveCache.k === k) return curveCache;
    curveCache = { k: k, pts: [], pts2: [] };
    for (i = 0; i < n; i++) { x = rg.lo + (rg.hi - rg.lo) * i / (n - 1); curveCache.pts.push([x, A.curve(x, st.tog)]); if (A.curve2) curveCache.pts2.push([x, A.curve2(x, st.tog)]); }
    return curveCache;
  }
  function viewData() {
    var d = { xr: null, yr: null, s1: [], s2: [], dots: [], dots2: [], marks: [], cur: null, xl: A.xl, yl: A.yl, logx: !!A.logx }, rg, c, n, i, ys;
    if (A.trace) {
      c = st.cap; if (!c) return d;
      n = Math.max(2, Math.floor(c.xs.length * st.prog));
      for (i = 0; i < n; i++) { d.s1.push([c.xs[i], c.ys[i]]); if (c.ys2) d.s2.push([c.xs[i], c.ys2[i]]); }
      d.xr = [c.xs[0], c.xs[c.xs.length - 1]]; ys = c.ys.concat(c.ys2 || []);
      d.marks = st.prog >= 1 ? c.marks : [];
    } else {
      rg = A.range(st.tog); c = curveFor(); d.s1 = c.pts; d.s2 = c.pts2; d.xr = [rg.lo, rg.hi]; d.cur = st.x;
      S.rows.forEach(function (r) { if (A.show(r, st.tog)) { d.dots.push(A.pt(r)); if (A.pt2) d.dots2.push(A.pt2(r)); } });
      ys = c.pts.map(function (q) { return q[1]; }).concat(c.pts2.map(function (q) { return q[1]; }));
    }
    var lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys), pad = (hi - lo) * 0.08 || 1;
    d.yr = [lo - pad, hi + pad];
    return d;
  }
  function drawScreen() {
    var key = [st.on, st.x, keyOf(), S.rows.length, st.prog, st.cap ? 1 : 0].join('|');
    if (key === lastKey) return; lastKey = key;
    scrTex.draw(function (x, w, h) {
      x.fillStyle = '#06130a'; x.fillRect(0, 0, w, h);
      var L = 70, R = 18, Tp = 40, Bm = 56, i;
      x.strokeStyle = 'rgba(80,220,120,.22)'; x.lineWidth = 1;
      for (i = 0; i <= 10; i++) { x.beginPath(); x.moveTo(L + i * (w - L - R) / 10, Tp); x.lineTo(L + i * (w - L - R) / 10, h - Bm); x.stroke(); }
      for (i = 0; i <= 8; i++) { x.beginPath(); x.moveTo(L, Tp + i * (h - Tp - Bm) / 8); x.lineTo(w - R, Tp + i * (h - Tp - Bm) / 8); x.stroke(); }
      x.fillStyle = 'rgba(160,255,190,.85)'; x.font = '600 20px "JetBrains Mono", monospace';
      if (!st.on) { x.fillText('instrument off', L + 20, 90); return; }
      var d = viewData();
      if (!d.xr) { x.fillText('ready: start a sweep', L + 20, 90); x.fillText(togText(), L + 20, 124); return; }
      var X = function (v) { var a = d.logx ? Math.log(v) : v, lo = d.logx ? Math.log(d.xr[0]) : d.xr[0], hi = d.logx ? Math.log(d.xr[1]) : d.xr[1]; return L + (a - lo) / (hi - lo || 1) * (w - L - R); };
      var Y = function (v) { return h - Bm - (v - d.yr[0]) / (d.yr[1] - d.yr[0] || 1) * (h - Tp - Bm); };
      var path = function (pts, col) { if (pts.length < 2) return; x.strokeStyle = col; x.lineWidth = 3; x.shadowColor = col; x.shadowBlur = 7; x.beginPath(); pts.forEach(function (q, k) { if (k) x.lineTo(X(q[0]), Y(q[1])); else x.moveTo(X(q[0]), Y(q[1])); }); x.stroke(); x.shadowBlur = 0; };
      if (d.yr[0] < 0 && d.yr[1] > 0) { x.strokeStyle = 'rgba(80,220,120,.55)'; x.lineWidth = 1.5; x.beginPath(); x.moveTo(L, Y(0)); x.lineTo(w - R, Y(0)); x.stroke(); }
      path(d.s1, '#6dff9a'); path(d.s2, '#ffc24a');
      if (d.cur !== null) { x.strokeStyle = 'rgba(255,255,255,.55)'; x.lineWidth = 1.5; x.beginPath(); x.moveTo(X(d.cur), Tp); x.lineTo(X(d.cur), h - Bm); x.stroke(); }
      x.fillStyle = '#ffd24a'; x.strokeStyle = '#ffd24a'; x.lineWidth = 2;
      d.dots.forEach(function (q) { x.beginPath(); x.arc(X(q[0]), Y(q[1]), 5, 0, Math.PI * 2); x.fill(); });
      d.dots2.forEach(function (q) { x.beginPath(); x.arc(X(q[0]), Y(q[1]), 5, 0, Math.PI * 2); x.stroke(); });
      d.marks.forEach(function (q) { x.beginPath(); x.arc(X(q[0]), Y(q[1]), 7, 0, Math.PI * 2); x.stroke(); });
      x.fillStyle = 'rgba(160,255,190,.9)'; x.font = '600 19px "JetBrains Mono", monospace';
      x.fillText(d.yl, L, 26); x.fillText(sig(d.xr[0], 3), L, h - 30); x.textAlign = 'right'; x.fillText(sig(d.xr[1], 3), w - R, h - 30); x.fillText(d.xl, w - R, h - 8); x.textAlign = 'left';
      x.fillText(sig(d.yr[0], 3), 4, h - Bm); x.fillText(sig(d.yr[1], 3), 4, Tp + 14);
    });
  }

  // ---------------- the control unit
  var genG = new T.Group(); S.scene.add(genG); genG.position.set(0.02, 0, 0.1); genG.rotation.y = -0.1;
  var gc = S.rounded(0.22, 0.15, 0.08, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 })); gc.rotation.x = -Math.PI / 2; gc.position.y = 0.043; genG.add(gc);
  var gtex = S.canvasTex(900, 330, function (xx, w, h) { xx.fillStyle = '#2b323d'; xx.fillRect(0, 0, w, h); xx.strokeStyle = 'rgba(255,255,255,.12)'; xx.lineWidth = 3; xx.strokeRect(8, 8, w - 16, h - 16);
    xx.fillStyle = '#f1efe8'; xx.font = '700 32px "Public Sans", sans-serif'; xx.fillText(A.trace ? 'SWEEP CONTROL' : 'SET POINT', 24, 50); xx.font = '500 22px "Public Sans", sans-serif'; xx.fillStyle = '#c7ccd6'; xx.fillText(A.trace ? 'start a sweep and capture the trace' : 'turn the knob, then record the reading', 24, 86); });
  var gf = S.mesh(box(0.208, 0.068, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: gtex, roughness: 0.45 }), M.grey]); gf.position.set(0, 0.043, 0.0775); genG.add(gf);
  var lcd = S.liveTex(512, 180), lcdLast = '';
  mk(genG, box(0.1, 0.03, 0.003), M.grey, 0.04, 0.032, 0.08); var gsc = new T.Mesh(new T.PlaneGeometry(0.095, 0.026), new T.MeshBasicMaterial({ map: lcd, toneMapped: false })); gsc.position.set(0.04, 0.032, 0.0825); genG.add(gsc);
  var knobG = new T.Group(); knobG.position.set(-0.07, 0.032, 0.0825); genG.add(knobG);
  var gk = mk(knobG, cyl(0.012, 0.013, 0.012, 28), M.bakelite); gk.rotation.x = Math.PI / 2; mk(knobG, box(0.0018, 0.012, 0.001), M.white, 0, 0.007, 0.007);
  S.contact(0.28, 0.2, 0.02, 0.1, 0.5);
  function lcdShow(txt, u2) {
    if (txt + u2 === lcdLast) return; lcdLast = txt + u2;
    lcd.draw(function (xx) { var gr = xx.createLinearGradient(0, 0, 0, 180); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); xx.fillStyle = gr; xx.fillRect(0, 0, 512, 180);
      xx.font = '700 ' + (txt.length > 8 ? 52 : 80) + 'px "JetBrains Mono", monospace'; xx.textAlign = 'right'; xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 112); xx.font = '600 30px "Public Sans", sans-serif'; xx.fillText(u2, 498, 150); });
  }

  // ---------------- the equipment (rig specific)
    function equip(S, T, M, h) {
    var g = new T.Group(); S.scene.add(g); g.position.set(-0.32, 0, -0.12);
    h.mk(g, h.cyl(0.085, 0.085, 0.26, 40), M.steel, 0, 0.13, 0);
    h.mk(g, h.cyl(0.092, 0.092, 0.012, 40), M.chrome, 0, 0.266, 0);
    h.mk(g, h.cyl(0.022, 0.022, 0.07, 24), M.steel, 0, 0.305, 0);
    h.mk(g, h.cyl(0.032, 0.032, 0.008, 28), M.alu, 0, 0.343, 0);
    for (var i = 0; i < 6; i++) { var a = i / 6 * Math.PI * 2; h.mk(g, h.cyl(0.0035, 0.0035, 0.012, 8), M.chrome, Math.cos(a) * 0.026, 0.346, Math.sin(a) * 0.026); }
    var pt1 = h.mk(g, h.cyl(0.013, 0.013, 0.05, 20), M.steel, 0.1, 0.19, 0); pt1.rotation.z = Math.PI / 2;
    h.mk(g, h.cyl(0.018, 0.018, 0.006, 20), M.alu, 0.128, 0.19, 0).rotation.z = Math.PI / 2;
    var pt2 = h.mk(g, h.cyl(0.013, 0.013, 0.05, 20), M.steel, 0, 0.19, 0.1); pt2.rotation.x = Math.PI / 2;
    h.mk(g, h.cyl(0.018, 0.018, 0.006, 20), M.alu, 0, 0.19, 0.128).rotation.x = Math.PI / 2;
    h.mk(g, h.cyl(0.095, 0.1, 0.014, 40), M.iron, 0, 0.007, 0);
    var lb = S.label('LN2 CRYOSTAT · 77 K', { w: 0.1, ratio: 0.14, color: '#e8eaec' }); lb.position.set(0, 0.12, 0.0855); g.add(lb);
    var lb2 = S.label('COLD · FROST', { w: 0.06, ratio: 0.2, color: '#fff', bg: '#2a4f9c' }); lb2.position.set(0, 0.07, 0.0855); g.add(lb2);
    S.contact(0.24, 0.24, -0.32, -0.12, 0.5);
    var sg = new T.Group(); S.scene.add(sg);
    h.mk(sg, h.cyl(0.0035, 0.0035, 0.2, 12), M.steel, 0, 0.1, 0);
    h.mk(sg, h.cyl(0.015, 0.015, 0.032, 20), M.black, 0, 0.216, 0);
    h.mk(sg, h.box(0.03, 0.012, 0.02), M.bakelite, 0, 0.24, 0);
    h.mk(sg, h.cyl(0.011, 0.011, 0.012, 20), M.copper, 0, 0.0, 0);
    for (var k = 0; k < 4; k++) h.mk(sg, h.cyl(0.0012, 0.0012, 0.008, 6), M.brass, (k % 2 ? 1 : -1) * 0.005, -0.008, (k < 2 ? 1 : -1) * 0.005);
    sg.position.set(-0.22, 0.012, 0.13);
    var base = h.mk(S.scene, h.cyl(0.03, 0.03, 0.004, 24), M.alu, -0.22, 0.002, 0.13); S.contact(0.08, 0.08, -0.22, 0.13, 0.5);
    S.addApparatus('equip', g, 'Cryostat', 'A stainless-steel cryostat. The insert carries the sample and thermometers down into the cold space; the side ports are for pumping and the electrical feed-through.');
    S.addApparatus('insert', sg, 'Sample insert', 'A thin steel rod with a copper sample block at its foot (spring contacts and a diode thermometer) and a connector head at the top.');
    return { sample: sg, mountPos: new T.Vector3(-0.32, 0.215, -0.12), lift: 0.12, grip: 0.1, view: [[-0.3, 0.34, 0.55], [-0.28, 0.17, -0.1]],
      mountButton: 'Lower the insert', mountMsg: 'The insert is lowered into the cryostat neck and clamped; the sample is in the cold space.',
      setupText: 'The sample is on the copper block at the foot of the insert, with its spring contacts and thermometer. Lower the insert into the cryostat, then switch on the instrument.', formula: '' };
  }

  var EQ = equip(S, T, M, { mk: mk, cyl: cyl, box: box });
  st.mounted = !EQ.sample;
  S.addApparatus('scope', scopeG, A.sim ? 'Simulated instrument display' : 'Live trace display', A.info || 'The live trace of the measurement.');
  S.addApparatus('ctl', genG, A.trace ? 'Sweep control' : 'Set-point control', 'The knob sets the control variable; its display shows the value.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading or capture you take is written here, as in a real practical file.');
  var hudA = S.hudCard(A.trace ? 'Setting' : 'Set point'), hudB = S.hudCard('Reading');
  drawScreen();

  // ---------------- human actions
  function mount() {
    if (busy() || st.mounted || !EQ.sample) return Promise.resolve();
    var g = EQ.sample, a = g.position.clone(), b = EQ.mountPos.clone(), gr = EQ.grip || 0.1;
    function pos(k) { return new T.Vector3(a.x + (b.x - a.x) * k, a.y + (EQ.lift || 0.07) * Math.sin(Math.PI * k) + (b.y - a.y) * k, a.z + (b.z - a.z) * k); }
    return S.hand.pinchMove(pos(0).add(new T.Vector3(0, gr, 0)), function (k) { return pos(k).add(new T.Vector3(0, gr, 0)); }, function (k) { g.position.copy(pos(k)); }, { mode: 'top', ms: 1300, reachMs: 650 })
      .then(function () { g.position.copy(b); st.mounted = true; S.say(EQ.mountMsg); S.render(); });
  }
  function switchOn() {
    if (busy() || st.on) return Promise.resolve();
    if (!st.mounted) { S.say('Mount the sample first.'); return Promise.resolve(); }
    return S.hand.tap(pwr, 'front').then(function () { st.on = true; S.say(A.sim ? 'The simulated instrument is on.' : 'The instrument is on and the trace is live.'); S.click(880, 0.05); S.render(); });
  }
  function setX(x) {
    if (A.trace) return Promise.resolve();
    var rg = A.range(st.tog);
    if (!(x >= rg.lo - 1e-9 && x <= rg.hi + 1e-9)) { S.say('The set point runs from ' + sig(rg.lo, 4) + ' to ' + sig(rg.hi, 4) + ' ' + rg.unit + '.'); return Promise.resolve(); }
    if (busy()) return Promise.resolve();
    if (!st.on) { S.say('Switch the instrument on first.'); return Promise.resolve(); }
    var a = st.x;
    return S.hand.tap(knobG, 'front').then(function () { return S.tween(450, function (k) { st.x = a + (x - a) * k; }); })
      .then(function () { st.x = x; S.render(); });
  }
  function setTog(k, v) {
    if (busy()) return;
    st.tog[k] = v; st.cap = null; st.prog = 1; lastKey = '';
    if (!A.trace) st.x = A.range(st.tog).def;
    S.render();
  }
  function record() {
    if (busy()) return null;
    if (!st.on) { S.say('Switch the instrument on first.'); return null; }
    var k = keyOf(), x = st.x, i, row;
    for (i = 0; i < S.rows.length; i++) if (S.rows[i]._k === k && Math.abs(S.rows[i].x - x) <= 1e-9 * Math.max(1, Math.abs(x))) { S.say('You already recorded this set point. Change it first.'); return null; }
    row = A.read(x, st.tog, S.rows.length); row.x = x; row._k = k;
    S.addRow(row); S.say('Recorded: ' + A.live(row));
    return row;
  }
  function capture() {
    if (busy()) return Promise.resolve(null);
    if (!st.on) { S.say('Switch the instrument on first.'); return Promise.resolve(null); }
    var k = keyOf(), i;
    for (i = 0; i < S.rows.length; i++) if (S.rows[i]._k === k) { S.say('You already captured this setting. Change a setting first.'); return Promise.resolve(null); }
    var c = A.capture(st.tog); st.cap = c; st.prog = 0; st.busy = true; lastKey = '';
    return S.hand.tap(knobG, 'front').then(function () { return S.tween(1500, function (q) { st.prog = q; }); }).then(function () {
      st.prog = 1; st.busy = false; c.row._k = k; S.addRow(c.row); lastKey = ''; S.say('Captured ' + c.xs.length + ' points. ' + togText()); S.render(); return c.row;
    });
  }
  function runPlan() {
    var plan = A.plan(), chain = Promise.resolve();
    plan.forEach(function (item) {
      chain = chain.then(function () { Object.keys(item.tog).forEach(function (kk) { st.tog[kk] = item.tog[kk]; }); st.cap = null; st.prog = 1; lastKey = ''; if (!A.trace) st.x = A.range(st.tog).def; });
      if (A.trace) chain = chain.then(function () { return capture(); });
      else (item.xs || []).forEach(function (x) { chain = chain.then(function () { return setX(x); }).then(function () { record(); }); });
    });
    return chain;
  }

  function result(rows) { return A.result(rows); }
  var steps = [
    { id: 'setup', title: 'Set up', view: 'equip', render: function (u) {
        u.h2(A.sim ? 'Switch on the simulated instrument' : (EQ.sample ? 'Mount the sample, switch on' : 'Switch on'));
        if (A.sim) u.note('This is a SIMULATED INSTRUMENT: it cannot be handled in a student lab. The numbers come from the published model named in the lab\'s sources, not from a real device.');
        u.p(EQ.sample ? EQ.setupText : A.info);
        if (EQ.sample) u.task('1. Mount the sample', st.mounted, st.mounted ? 'In place' : 'Still on the tray').add(u.button(st.mounted ? 'Mounted' : EQ.mountButton, function () { S.focus('equip'); mount(); }, !st.mounted, st.mounted || S.hand.busy));
        u.task((EQ.sample ? '2. ' : '1. ') + 'Switch on', st.on, st.on ? 'Running' : 'Off').add(u.button(st.on ? 'Switched on' : 'Switch the instrument on', function () { S.focus('scope'); switchOn(); }, !st.on && st.mounted, st.on || !st.mounted || S.hand.busy));
        u.next('Next: take the data', st.mounted && st.on);
      },
      ok: function () { return st.mounted && st.on; }, auto: function () { return mount().then(switchOn); } },
    { id: 'measure', title: A.trace ? 'Sweep and capture' : 'Set and record', view: 'scope', render: function (u) {
        u.h2(A.trace ? 'Capture the traces' : 'Set the value, record the reading');
        u.p(A.trace ? 'Choose the settings below, then start the sweep. The trace is drawn as it is measured; the circles mark what the analysis found on it.' : 'Move the set-point with the slider, press Set, then Record. The dots on the screen are your readings.');
        (A.toggles || []).forEach(function (t) {
          var btns = t.opts.map(function (o) { return u.button(o.l, function () { setTog(t.key, o.v); }, st.tog[t.key] === o.v, S.hand.busy || st.busy); });
          u.p(t.label + ':'); u.row.apply(u, btns);
        });
        if (A.trace) {
          u.row(u.button('Start the sweep and capture', function () { S.focus('scope'); capture(); }, true, S.hand.busy || st.busy));
          u.live(function () { return st.cap ? (st.prog < 1 ? 'Sweeping… ' + Math.round(st.prog * 100) + ' %' : 'Captured. ' + togText()) : togText(); });
        } else {
          var rg = A.range(st.tog), tgt = { v: st.x };
          u.slider('Set point', rg.lo, rg.hi, rg.step, function () { return tgt.v; }, function (v) { tgt.v = v; }, rg.unit, rg.dig);
          u.row(u.button('Set', function () { S.focus('ctl'); setX(tgt.v); }, false, S.hand.busy || st.busy), u.button('Record the reading', function () { record(); }, true, S.hand.busy || st.busy));
          u.live(function () { return rnd(st.x, 6) + ' ' + A.range(st.tog).unit + '  →  ' + A.live(A.read(st.x, st.tog, -1)); });
        }
        u.h3('Your record'); u.table();
        var need = A.min || 1;
        if (S.rows.length < need) u.p(S.rows.length + ' of at least ' + need + ' ' + (A.trace ? 'captures' : 'readings') + ' taken.');
        else if (!result(S.rows)) u.p('The record is not yet enough to find the result. ' + (A.trace ? 'Capture the other settings.' : 'Add readings where the curve changes fastest, and the points the procedure asks for.'));
        u.next('Next: the result', S.rows.length >= need && !!result(S.rows));
      },
      ok: function () { return S.rows.length >= (A.min || 1) && !!result(S.rows); }, auto: function () { return runPlan(); } }
  ];

  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { equip: EQ.view, scope: [[0.34, 0.24, 0.3], [0.3, 0.12, -0.1]], ctl: [[0.02, 0.2, 0.36], [0.02, 0.04, 0.1]], bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: S.lab.theory,
      formula: EQ.formula || '',
      formulaNote: A.sim ? 'SIMULATED INSTRUMENT: a published model, not a device' : '',
      more: [A.info, V_.sample ? 'Sample in this run: ' + V_.sample + (V_.note ? '. ' + V_.note : '.') : 'The sample in the base run is the lab\'s own illustrative one.', 'The result is found by analysing your own table or captured trace (peaks, plateaus, crossings, fits), never by reading a formula back.'],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title,
      lines: ['Aim: ' + S.lab.aim.slice(0, 110) + (S.lab.aim.length > 110 ? '…' : ''), 'Sample: ' + (V_.sample || 'lab sample (illustrative)')],
      columns: A.cols },
    result: result,
    tol: A.tol || 0.02,
    chips: ['What does this instrument measure?', 'Check my readings', 'How is the result found?', 'What would change with another sample?'],
    viva: [],
    askState: function () { return { experiment: S.lab.title, simulated_instrument: !!A.sim, switched_on: st.on, settings: togText(), set_point: A.trace ? null : rnd(st.x, 6), records: S.rows.length }; },
    steps: steps,
    tick: function () {
      var rg = A.trace ? null : A.range(st.tog);
      lcdShow(A.trace ? (st.cap ? (st.prog < 1 ? Math.round(st.prog * 100) + '%' : 'done') : 'ready') : (st.on ? sig(st.x, 5) : '0'), A.trace ? '' : (rg ? rg.unit : ''));
      drawScreen();
      hudA.set(A.trace ? (togText() || '—') : (st.on ? sig(st.x, 5) + ' ' + rg.unit : '—'));
      hudB.set(!st.on ? '—' : (A.trace ? (st.cap ? 'trace captured' : 'idle') : A.live(A.read(st.x, st.tog, -1))));
    }
  };
});
