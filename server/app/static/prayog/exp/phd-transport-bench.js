/* Prayogshala studio module: TRANSPORT BENCH (Josephson, SQUID, quantum Hall, SdH, weak localisation, tunnelling).
   One rig for a family of research benches. The lab's kernel (packs/phd_cond.js) gives every number; the adapter for
   that kernel (below) says what is swept, what is read and how the result is found from the student's own table or
   captured trace - peaks, plateaus, zero crossings, fitted decays - never by reading the formula back.
   Every instrument here is a SIMULATED INSTRUMENT; the live screen draws the swept curve and the analysis marks what it found. */
HoolaStudio.define('phd-transport-bench', function (S) {
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

  ADAPT.phd_jj = function () {
    var N = 71, cache = {};
    function sweep(rf) {
      if (cache[rf]) return cache[rf];
      var ic = KN.ic(p), xs = [], ys = [], i;
      for (i = 0; i < N; i++) { xs.push(2.2 * ic * i / (N - 1)); ys.push(KN.volts(p, xs[i], rf)); }
      cache[rf] = { xs: xs, ys: ys }; return cache[rf];
    }
    return {
      trace: true, sim: true, name: 'Junction I-V', xl: 'I (mA)', yl: 'V (µV)', min: 2,
      toggles: [{ key: 'rf', label: 'Microwaves', def: 0, opts: [{ v: 0, l: 'off' }, { v: 1, l: 'on' }] }],
      capture: function (tog) {
        var s = sweep(tog.rf), xs = s.xs.map(function (v) { return v * 1e3; }), ys = s.ys.map(function (v) { return v * 1e6; }), i, icf = null, run = [], pl = null, j, ok;
        for (i = 0; i < ys.length; i++) if (ys[i] > 1.0) { icf = xs[i - 1 >= 0 ? i - 1 : 0]; break; }
        for (i = 1; i < ys.length && !pl; i++) {
          if (ys[i] > 1.0 && Math.abs(ys[i] - ys[i - 1]) < 0.003 * ys[i]) { j = i; while (j + 1 < ys.length && Math.abs(ys[j + 1] - ys[j]) < 0.003 * ys[j + 1]) j++; if (j - i + 1 >= 3) pl = { a: i - 1, b: j }; i = j; }
        }
        var v1 = null, marks = [];
        if (pl) { v1 = 0; for (i = pl.a; i <= pl.b; i++) { v1 += ys[i]; marks.push([xs[i], ys[i]]); } v1 /= (pl.b - pl.a + 1); }
        return { xs: xs, ys: ys, marks: marks, row: { rf: tog.rf, Ic: icf, V1: v1, np: pl ? pl.b - pl.a + 1 : 0 } };
      },
      cols: [{ label: 'microwaves', get: function (r) { return r.rf ? 'on, ' + (p.f / 1e9).toFixed(2) + ' GHz' : 'off'; } }, { label: 'Ic (mA, approx.)', get: function (r) { return r.Ic === null ? '—' : r.Ic.toFixed(3); } },
        { label: 'step points', get: function (r) { return String(r.np); } }, { label: 'step V (µV)', get: function (r) { return r.V1 === null ? '—' : r.V1.toFixed(3); } }],
      plan: function () { return [{ tog: { rf: 0 } }, { tog: { rf: 1 } }]; },
      result: function (rows) {
        var r = null, i;
        for (i = 0; i < rows.length; i++) if (rows[i].rf && rows[i].V1) r = rows[i];
        if (!r) return null;
        return { label: 'Josephson constant 2e/h (from the first Shapiro step)', value: p.f / (r.V1 * 1e-6) / 1e12, unit: 'MHz/µV', digits: 3, truth: 2 * QE / H0 / 1e12,
          note: 'The first plateau of the I-V curve with microwaves on sits at V = ' + sig(r.V1, 5) + ' µV, found as ' + r.np + ' consecutive points within 0.3 % of each other. With f = ' + (p.f / 1e9).toFixed(3) + ' GHz, 2e/h = f/V. The zero-voltage branch ends near Ic ≈ ' + (rows.filter(function (x) { return !x.rf && x.Ic; }).map(function (x) { return x.Ic.toFixed(3); })[0] || '(sweep once with microwaves off)') + ' mA.' };
      },
      info: 'A shunted tunnel junction at 4.2 K. SIMULATED INSTRUMENT: the voltage is computed by integrating the RSJ equation over whole microwave periods.'
    };
  };

  ADAPT.phd_dcsquid = function () {
    var IBS = [22e-6, 24e-6, 30e-6], N = 401;
    function q(tog) { return assign(p, { Ib: tog.Ib }); }
    return {
      trace: true, sim: true, name: 'SQUID V-Φ', xl: 'coil current (µA)', yl: 'V (µV)', min: 2,
      toggles: [{ key: 'Ib', label: 'Bias current', def: p.Ib, opts: IBS.map(function (b) { return { v: b, l: (b * 1e6) + ' µA' }; }) }],
      capture: function (tog) {
        var qq = q(tog), per0 = PHI0 / qq.Mi, xs = [], ys = [], i, sm, lvl, cr, vmax = -1e9, vmin = 1e9, sl = 0, dx, per, marks = [];
        for (i = 0; i < N; i++) { xs.push((-0.5 + 4.0 * i / (N - 1)) * per0); ys.push(KN.noisy(qq, xs[i], i)); }
        sm = smooth(ys, 2);
        for (i = 0; i < N; i++) { if (sm[i] > vmax) vmax = sm[i]; if (sm[i] < vmin) vmin = sm[i]; }
        lvl = 0.5 * (vmax + vmin);
        cr = cross(xs, sm, lvl, 1);
        per = cr.length > 1 ? (cr[cr.length - 1] - cr[0]) / (cr.length - 1) : 0;
        dx = xs[1] - xs[0];
        for (i = 2; i < N - 2; i++) sl = Math.max(sl, Math.abs(sm[i + 2] - sm[i - 2]) / (4 * dx * qq.Mi / PHI0));
        cr.forEach(function (c) { marks.push([c * 1e6, lvl * 1e6]); });
        return { xs: xs.map(function (v) { return v * 1e6; }), ys: ys.map(function (v) { return v * 1e6; }), marks: marks, row: { Ib: tog.Ib, per: per, dV: vmax - vmin, VPhi: sl, nc: cr.length, vn: qq.vn } };
      },
      cols: [{ label: 'bias (µA)', get: function (r) { return (r.Ib * 1e6).toFixed(1); } }, { label: 'crossings', get: function (r) { return String(r.nc); } }, { label: 'period (µA)', get: function (r) { return (r.per * 1e6).toFixed(3); } },
        { label: 'modulation (µV)', get: function (r) { return (r.dV * 1e6).toFixed(2); } }, { label: 'V_Φ (µV/Φ0)', get: function (r) { return (r.VPhi * 1e6).toFixed(1); } }],
      plan: function () { return [{ tog: { Ib: 30e-6 } }, { tog: { Ib: 24e-6 } }]; },
      result: function (rows) {
        var r = rows[rows.length - 1];
        if (!r || !r.per) return null;
        return { label: 'Flux quantum Φ0 = Mi × period', value: r.per * p.Mi * 1e15, unit: 'fWb (10⁻¹⁵ Wb)', digits: 4, truth: PHI0 * 1e15,
          note: 'The voltage crosses its mean level every ' + sig(r.per * 1e6, 4) + ' µA of coil current; with the coil\'s mutual inductance Mi = ' + sig(p.Mi, 3) + ' Wb/A that is one flux quantum. Modulation depth ' + sig(r.dV * 1e6, 3) + ' µV; steepest slope V_Φ = ' + sig(r.VPhi * 1e6, 3) + ' µV/Φ0, so the white noise of ' + sig(r.vn * 1e6, 2) + ' µV per reading is a flux noise of about ' + sig(r.vn / r.VPhi * 1e6, 2) + ' µΦ0 per reading.' };
      },
      info: 'A DC SQUID read at constant bias. SIMULATED INSTRUMENT: V = (Rn/2) sqrt(Ib² - Ic(Φ)²) with seeded white noise.'
    };
  };

  ADAPT.phd_qhe = function () {
    var TS = [1.5, 0.3], N = 551;
    function q(tog) { return assign(p, { T: tog.T }); }
    return {
      trace: true, sim: true, name: 'Hall resistance sweep', xl: 'B (T)', yl: 'Rxy (kΩ, blue); Rxx (Ω, amber, scaled)', min: 1,
      toggles: [{ key: 'T', label: 'Temperature', def: p.T, opts: TS.map(function (t) { return { v: t, l: t + ' K' }; }) }],
      capture: function (tog) {
        var qq = q(tog), xs = [], ys = [], y2 = [], i, fl = [], cl = [], cur = null, pl = [], rxx0, R1, n_est = [], marks = [], ok;
        for (i = 0; i < N; i++) { xs.push(1 + 11 * i / (N - 1)); ys.push(KN.rxy(qq, xs[i])); y2.push(KN.rxx(qq, xs[i])); }
        for (i = 0; i < N; i++) {
          ok = i > 1 && i < N - 2 && Math.abs(ys[i + 2] - ys[i - 2]) < 4e-4 * ys[i];
          if (ok) { if (!cur) { cur = []; cl.push(cur); } cur.push(i); } else cur = null;
        }
        cl.forEach(function (c) { if (c.length >= 8) pl.push({ B: xs[c[Math.floor(c.length / 2)]], R: ys[c[Math.floor(c.length / 2)]] }); });
        pl.sort(function (a, b) { return b.B - a.B; });
        R1 = pl.length ? pl[0].R : 0;
        pl.forEach(function (d) { d.i = Math.max(1, Math.round(R1 / d.R)); marks.push([d.B, d.R / 1000]); n_est.push(d.i * QE * d.B / H0); });
        var RK = pl.length ? pl.reduce(function (s, d) { return s + d.R * d.i; }, 0) / pl.length : 0;
        var nn = n_est.length ? n_est.reduce(function (s, v) { return s + v; }, 0) / n_est.length : 0;
        return { xs: xs, ys: ys.map(function (v) { return v / 1000; }), ys2: y2.map(function (v) { return v / 20; }), marks: marks, row: { T: tog.T, np: pl.length, idx: pl.map(function (d) { return d.i; }).join(','), RK: RK, n: nn } };
      },
      cols: [{ label: 'T (K)', get: function (r) { return String(r.T); } }, { label: 'plateaus', get: function (r) { return r.np + ' (i = ' + r.idx + ')'; } },
        { label: 'i × R_xy (Ω)', get: function (r) { return r.RK.toFixed(1); } }, { label: 'n (10^15 /m²)', get: function (r) { return (r.n / 1e15).toFixed(3); } }],
      plan: function () { return [{ tog: { T: 1.5 } }]; },
      result: function (rows) {
        var r = rows[rows.length - 1];
        if (!r || r.np < 3) return null;
        return { label: 'von Klitzing constant h/e² (i × plateau value)', value: r.RK, unit: 'Ω', digits: 2, truth: H0 / (QE * QE),
          note: r.np + ' plateaus were found where R_xy stays flat, numbered from the highest field (i = 1) by the ratio of their values; each i × R_xy gives h/e². From the fields at the plateau centres the electron density is n = ' + sig(r.n / 1e15, 4) + ' × 10^15 m⁻². R_xx nearly vanishes on each plateau.' };
      },
      info: 'A 2D electron gas in a 12 T magnet, current and voltage probes on a Hall bar. SIMULATED INSTRUMENT.'
    };
  };

  ADAPT.phd_sdh = function () {
    var TS = [1.5, 4.2], N = 1500;
    function q(tog) { return assign(p, { T: tog.T }); }
    return {
      trace: true, sim: true, name: 'Rxx against 1/B', xl: '1/B (1/T)', yl: 'Rxx (Ω)', min: 1,
      toggles: [{ key: 'T', label: 'Temperature', def: p.T, opts: TS.map(function (t) { return { v: t, l: t + ' K' }; }) }],
      capture: function (tog) {
        var qq = q(tog), xs = [], ys = [], i, pk, pts = [], mc, marks = [];
        for (i = 0; i <= N; i++) { xs.push(1 / 12 + (1 / 0.8 - 1 / 12) * i / N); ys.push(KN.rho(qq, 1 / xs[i])); }
        pk = peaks(xs, ys, 1);
        for (i = 0; i < pk.length; i++) { pts.push([i, pk[i]]); marks.push([pk[i], KN.rho(qq, 1 / pk[i])]); }
        mc = pk.length > 2 ? line(pts) : [0, 0];
        return { xs: xs, ys: ys, marks: marks, row: { T: tog.T, np: pk.length, per: mc[0], n: mc[0] > 0 ? 2 * QE / (H0 * mc[0]) : 0 } };
      },
      cols: [{ label: 'T (K)', get: function (r) { return String(r.T); } }, { label: 'maxima', get: function (r) { return String(r.np); } },
        { label: 'period Δ(1/B) (1/T)', get: function (r) { return r.per.toFixed(5); } }, { label: 'n (10^15 /m²)', get: function (r) { return (r.n / 1e15).toFixed(4); } }],
      plan: function () { return [{ tog: { T: 4.2 } }, { tog: { T: 1.5 } }]; },
      result: function (rows) {
        var r = rows[rows.length - 1];
        if (!r || r.np < 4) return null;
        return { label: 'Carrier density n = 2e/(h Δ(1/B))', value: r.n / 1e15, unit: '10^15 m⁻²', digits: 3, truth: p.n / 1e15,
          note: r.np + ' maxima spaced by Δ(1/B) = ' + sig(r.per, 5) + ' T⁻¹ (a straight-line fit of the maxima\'s positions), spin degeneracy 2. The oscillations are stronger at the lower temperature.' };
      },
      info: 'Longitudinal resistance of a 2D electron gas against 1/B. SIMULATED INSTRUMENT.'
    };
  };

  ADAPT.phd_weakloc = function () {
    var TS = [2, 4, 8], N = 70;
    function q(tog) { return assign(p, { T: tog.T }); }
    return {
      trace: true, sim: true, logx: true, name: 'Magnetoconductance', xl: 'B (mT, log)', yl: 'Δσ (µS)', min: 1,
      toggles: [{ key: 'T', label: 'Temperature', def: p.T, opts: TS.map(function (t) { return { v: t, l: t + ' K' }; }) }],
      capture: function (tog) {
        var qq = q(tog), xs = [], ys = [], pts = [], i, b, d, bp, lp, sc = QE * QE / (Math.PI * H0);
        for (i = 0; i < N; i++) { b = 1e-4 * Math.pow(1000, i / (N - 1)); d = KN.ds(qq, b) + qq.noise * sc * H.hash(qq.seed, i); xs.push(b * 1e3); ys.push(d * 1e6); pts.push([b, d]); }
        bp = KN.fit(pts); lp = Math.sqrt(HBAR / (4 * QE * bp));
        return { xs: xs, ys: ys, marks: [], row: { T: tog.T, Bphi: bp, Lphi: lp } };
      },
      cols: [{ label: 'T (K)', get: function (r) { return String(r.T); } }, { label: 'B_phi (mT)', get: function (r) { return (r.Bphi * 1e3).toFixed(4); } }, { label: 'L_phi (µm)', get: function (r) { return (r.Lphi * 1e6).toFixed(4); } }],
      plan: function () { return [{ tog: { T: 8 } }, { tog: { T: 2 } }]; },
      result: function (rows) {
        var r = rows[rows.length - 1], a = rows.filter(function (x) { return x.T !== r.T; })[0], ex = '';
        if (!r) return null;
        if (a) ex = ' L_phi ~ T^(-p/2) with p = ' + sig(-2 * Math.log(r.Lphi / a.Lphi) / Math.log(r.T / a.T), 3) + ' between ' + a.T + ' K and ' + r.T + ' K.';
        return { label: 'Phase coherence length L_phi at ' + r.T + ' K', value: r.Lphi * 1e6, unit: 'µm', digits: 4, truth: KN.Lphi(q({ T: r.T })) * 1e6,
          note: 'The Hikami-Larkin-Nagaoka form fitted to the captured points gives B_phi = ' + sig(r.Bphi * 1e3, 4) + ' mT, and L_phi = sqrt(hbar/(4 e B_phi)).' + ex };
      },
      info: 'Conductance of a thin film against a small field. SIMULATED INSTRUMENT (generated from the HLN formula with seeded noise).'
    };
  };

  ADAPT.phd_tunnel = function () {
    var TS = [0.9, 0.67, 0.33, 0.08].map(function (m) { return rnd(m * p.Tc, 3); }), N = 61, KBc = 1.380649e-23;
    function q(tog) { return assign(p, { T: tog.T }); }
    return {
      trace: true, sim: true, name: 'NIS tunnelling I-V', xl: 'V (mV)', yl: 'I (µA, blue); G/Gn (amber)', min: 1,
      toggles: [{ key: 'T', label: 'Temperature', def: p.T, opts: TS.map(function (t) { return { v: t, l: t + ' K' }; }) }],
      capture: function (tog) {
        var qq = q(tog), d0 = 1.764 * KBc * p.Tc / QE, vs = [], is = [], pts = [], i, g = [], gap;
        for (i = 0; i < N; i++) { vs.push(3 * d0 * i / (N - 1)); is.push(KN.cur(qq, vs[i])); pts.push([vs[i], is[i]]); }
        for (i = 0; i < N; i++) { var a = Math.max(0, i - 1), b = Math.min(N - 1, i + 1); g.push((is[b] - is[a]) / (vs[b] - vs[a]) / p.Gn); }
        gap = KN.fit(pts.slice(0), qq);
        return { xs: vs.map(function (v) { return v * 1e3; }), ys: is.map(function (v) { return v * 1e6; }), ys2: g, marks: [[gap * 1e3, 0]], row: { T: tog.T, gap: gap } };
      },
      cols: [{ label: 'T (K)', get: function (r) { return String(r.T); } }, { label: 'gap Δ (µeV)', get: function (r) { return (r.gap * 1e6).toFixed(2); } },
        { label: '2Δ/(k Tc)', get: function (r) { return (2 * r.gap * QE / (KBc * p.Tc)).toFixed(3); } }],
      plan: function () { return [{ tog: { T: TS[0] } }, { tog: { T: TS[2] } }, { tog: { T: TS[3] } }]; },
      result: function (rows) {
        var r = rows[rows.length - 1];
        if (!r) return null;
        return { label: 'Superconducting gap Δ at ' + r.T + ' K', value: r.gap * 1e6, unit: 'µeV', digits: 2, truth: KN.gap(q({ T: r.T })) / QE * 1e6,
          note: 'The BCS tunnelling current was fitted to the captured points at the junction temperature, with the film\'s Tc and the normal-state conductance known. At the lowest temperature 2Δ/(k Tc) = 3.53 and the gap falls towards zero as T approaches Tc.' };
      },
      info: 'Al-type film / oxide / normal metal junction in a dilution cryostat. SIMULATED INSTRUMENT.'
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
    var g = new T.Group(); S.scene.add(g); g.position.set(-0.3, 0, -0.14);
    h.mk(g, h.box(0.26, 0.012, 0.16), M.iron, 0, 0.006, 0);
    h.mk(g, h.box(0.012, 0.3, 0.14), M.grey, -0.125, 0.15, 0); h.mk(g, h.box(0.012, 0.3, 0.14), M.grey, 0.125, 0.15, 0);
    h.mk(g, h.box(0.26, 0.012, 0.14), M.grey, 0, 0.3, 0);
    var names = ['SOURCE-METER', 'LOCK-IN AMPLIFIER', 'MAGNET / FLUX SUPPLY'], i;
    for (i = 0; i < 3; i++) {
      var y = 0.05 + i * 0.085;
      h.mk(g, h.box(0.236, 0.075, 0.12), new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 }), 0, y + 0.04, 0);
      var l = S.label(names[i], { w: 0.12, ratio: 0.12, color: '#e8eaec' }); l.position.set(-0.05, y + 0.058, 0.0615); g.add(l);
      var l2 = S.label('SIMULATED', { w: 0.055, ratio: 0.2, color: '#fff', bg: '#8a1f1a' }); l2.position.set(0.075, y + 0.058, 0.0615); g.add(l2);
      var kn = h.mk(g, h.cyl(0.008, 0.009, 0.01, 18), M.bakelite, -0.09 + i * 0.01, y + 0.025, 0.065); kn.rotation.x = Math.PI / 2;
      h.mk(g, h.cyl(0.003, 0.003, 0.002, 10), new T.MeshStandardMaterial({ color: 0x59d98a, emissive: 0x1f8f4b }), 0.1, y + 0.022, 0.0615).rotation.x = Math.PI / 2;
    }
    var pb = h.mk(g, h.cyl(0.045, 0.05, 0.16, 32), M.steel, 0.2, 0.08, 0.0);
    var tl = S.label('SIMULATED CRYOSTAT', { w: 0.08, ratio: 0.15, color: '#fff', bg: '#8a1f1a' }); tl.position.set(0.2, 0.11, 0.0505); g.add(tl);
    h.mk(g, h.cyl(0.016, 0.016, 0.03, 20), M.chrome, 0.2, 0.175, 0);
    S.contact(0.5, 0.2, -0.3, -0.14, 0.5);
    S.addApparatus('equip', g, 'Instrument rack (simulated)', 'A rack of source-meter, lock-in amplifier and magnet or flux supply beside a cryostat. All of it is a simulation: the numbers come from a published model.');
    return { sample: null, view: [[-0.3, 0.38, 0.55], [-0.3, 0.15, -0.14]], setupText: '', formula: '' };
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
