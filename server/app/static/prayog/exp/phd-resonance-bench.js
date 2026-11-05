/* Prayogshala studio module: MAGNETIC-RESONANCE BENCH (pulsed NMR, PFG, ESR, CW NMR, Moessbauer).
   One rig for a family of research benches. The lab's kernel (packs/phd_cond.js) gives every number; the adapter for
   that kernel (below) says what is swept, what is read and how the result is found from the student's own table or
   captured trace - peaks, plateaus, zero crossings, fitted decays - never by reading the formula back.
   Electromagnet and probe with a live scope or spectrum drawn on the screen. */
HoolaStudio.define('phd-resonance-bench', function (S) {
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

  ADAPT.phd_bloch = function () {
    var MODE = CFG.measure || 't1', fL = KN.fL(p);
    var MODES = [{ v: 'tune', l: 'tune RF' }, { v: 'ir', l: 'inversion recovery' }, { v: 'echo', l: 'Hahn echo' }, { v: 'cpmg', l: 'CPMG' }];
    function nz(k) { return p.noise * p.M0 * (Math.sin(p.seed * 12.9898 + k * 78.233) * 43758.5453 - Math.floor(Math.sin(p.seed * 12.9898 + k * 78.233) * 43758.5453) - 0.5) * 2; }
    function val(x, tog, k) {
      if (tog.mode === 'tune') return KN.resp(p, x * 1e6) + nz(k);
      if (tog.mode === 'ir') return KN.ir(p, x) + nz(k);
      if (tog.mode === 'echo') return KN.echo(p, x) + nz(k);
      return KN.cpmg(p, x) + nz(k);
    }
    function fitIR(rs) {
      var mx = Math.max.apply(null, rs.map(function (r) { return r.S; })), best = null, i, m, sse, pts, mc, e, j;
      for (i = 0; i < 400; i++) {
        m = mx * (1.0005 + 0.4 * i / 399); pts = rs.filter(function (r) { return m - r.S > 1e-3 * m; }).map(function (r) { return [r.x, Math.log(m - r.S)]; });
        if (pts.length < 4) continue; mc = line(pts); sse = 0;
        for (j = 0; j < pts.length; j++) { e = pts[j][1] - (mc[0] * pts[j][0] + mc[1]); sse += e * e; }
        if (!best || sse < best.sse) best = { sse: sse, T1: mc[0] < 0 ? -1 / mc[0] : 0 };
      }
      return best ? best.T1 : 0;
    }
    function fitEcho(rs) {
      var pts = rs.filter(function (r) { return r.S > 0.06; }).map(function (r) { return [2 * r.x, Math.log(r.S)]; }), mc;
      if (pts.length < 4) return 0; mc = line(pts); return mc[0] < 0 ? -1 / mc[0] : 0;
    }
    function tuneF(rs) {
      var s = rs.slice().sort(function (a, b) { return b.S - a.S; }), top = s[0], i, a, b, c, d, nb;
      var byx = rs.slice().sort(function (u, v) { return u.x - v.x; }); i = byx.indexOf(top);
      if (i < 1 || i > byx.length - 2) return top.x * 1e6;
      a = byx[i - 1]; b = byx[i]; c = byx[i + 1];
      // vertex of the parabola through three points (unequal spacing allowed)
      var x1 = a.x, x2 = b.x, x3 = c.x, y1 = a.S, y2 = b.S, y3 = c.S;
      var num = (x2 - x1) * (x2 - x1) * (y2 - y3) - (x2 - x3) * (x2 - x3) * (y2 - y1), den = (x2 - x1) * (y2 - y3) - (x2 - x3) * (y2 - y1);
      return (den !== 0 ? x2 - 0.5 * num / den : x2) * 1e6;
    }
    return {
      name: 'Pulsed NMR', xl: 'RF (MHz) or delay (s)', yl: 'signal', min: 12,
      toggles: [{ key: 'mode', label: 'Measurement', def: 'tune', opts: MODES }],
      range: function (tog) {
        if (tog.mode === 'tune') return { lo: rnd(fL / 1e6 - 0.02, 4), hi: rnd(fL / 1e6 + 0.02, 4), step: 0.0001, def: rnd(fL / 1e6 - 0.02, 4), unit: 'MHz', dig: 4 };
        if (tog.mode === 'ir') return { lo: 0, hi: 5 * p.T1, step: p.T1 / 100, def: p.T1, unit: 's', dig: 3 };
        return { lo: 0, hi: 1.6 * p.T2, step: p.T2 / 100, def: 0.5 * p.T2, unit: 's', dig: 3 };
      },
      read: function (x, tog, k) { return { mode: tog.mode, x: x, S: val(x, tog, k) }; },
      curve: function (x, tog) { return val(x, tog, 0) - nz(0); },
      show: function (r, tog) { return r.mode === tog.mode; }, pt: function (r) { return [r.x, r.S]; },
      cols: [{ label: 'measurement', get: function (r) { return r.mode; } }, { label: 'x (MHz / s)', get: function (r) { return r.mode === 'tune' ? r.x.toFixed(4) : r.x.toFixed(3); } }, { label: 'signal', get: function (r) { return r.S.toFixed(4); } }],
      live: function (r) { return 'signal = ' + r.S.toFixed(4); },
      plan: function () {
        var tn = [-8, -4, -2, -1, 0, 1, 2, 4, 8].map(function (d) { return rnd((fL + d * 1000) / 1e6, 4); }), pl = [{ tog: { mode: 'tune' }, xs: tn }];
        if (MODE === 't1') pl.push({ tog: { mode: 'ir' }, xs: [0.1, 0.25, 0.5, 0.8, 1.2, 1.8, 2.5, 3.5, 5].map(function (m) { return rnd(m * p.T1, 4); }) });
        else pl.push({ tog: { mode: MODE === 'cpmg' ? 'cpmg' : 'echo' }, xs: [0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.4].map(function (m) { return rnd(m * p.T2, 4); }) });
        return pl;
      },
      result: function (rows) {
        var tn = rows.filter(function (r) { return r.mode === 'tune'; }), ir = rows.filter(function (r) { return r.mode === 'ir'; }), ec = rows.filter(function (r) { return r.mode === 'echo'; }), cp = rows.filter(function (r) { return r.mode === 'cpmg'; });
        if (tn.length < 5) return null;
        var fl = tuneF(tn), gam = 2 * Math.PI * fl / p.B, g = ' The probe resonates at ' + sig(fl / 1e6, 6) + ' MHz, so gamma = 2π f/B = ' + sig(gam / 1e8, 5) + ' × 10^8 rad/(s T).';
        if (MODE === 't1') { if (ir.length < 7) return null; return { label: 'Spin-lattice time T1 (inversion recovery)', value: fitIR(ir), unit: 's', digits: 4, truth: p.T1, note: 'The recovery ln(M∞ - M) against delay is a straight line of slope -1/T1; M∞ is found by the fit.' + g }; }
        if (MODE === 'cpmg') { if (cp.length < 6) return null; return { label: 'Spin-spin time T2 (CPMG)', value: fitEcho(cp), unit: 's', digits: 4, truth: p.T2, note: 'ln(echo height) against the echo time 2τ has slope -1/T2.' + (p.G > 0 ? ' The closely spaced π pulses of the CPMG train refocus the diffusion loss that a single Hahn echo would suffer in this field gradient.' : '') + g }; }
        if (ec.length < 6) return null;
        return { label: 'Spin-spin time T2 (Hahn echo)', value: fitEcho(ec), unit: 's', digits: 4, truth: p.T2, note: 'ln(echo height) against 2τ has slope -1/T2.' + g };
      },
      info: 'A permanent-magnet NMR spectrometer; the probe is tuned by stepping the RF frequency. Pulse sequences are evaluated from the Bloch relaxation formulas, with 0.2 % seeded noise.'
    };
  };

  ADAPT.phd_pfg = function () {
    var gmax = Math.sqrt(3 / (p.D * (p.Dl - p.delta / 3))) / (p.gamma * p.delta), nzk = 0;
    function nz(k) { var s = Math.sin(p.seed * 12.9898 + k * 78.233) * 43758.5453; return p.noise * (2 * (s - Math.floor(s)) - 1); }
    return {
      name: 'Diffusion echo attenuation', xl: 'g (T/m)', yl: 'echo height E', min: 7,
      toggles: [],
      range: function () { return { lo: 0, hi: rnd(1.2 * gmax, 3), step: 0.001, def: rnd(0.3 * gmax, 3), unit: 'T/m', dig: 3 }; },
      read: function (x, tog, k) { var qq = assign(p, { g: x }); return { g: x, b: KN.bfac(qq), E: Math.max(1e-4, KN.E(qq) * (1 + nz(k))) }; },
      curve: function (x) { return KN.E(assign(p, { g: x })); },
      show: function () { return true; }, pt: function (r) { return [r.g, r.E]; },
      cols: [{ label: 'g (T/m)', get: function (r) { return r.g.toFixed(3); } }, { label: 'b (10^9 s/m²)', get: function (r) { return (r.b / 1e9).toFixed(4); } }, { label: 'E', get: function (r) { return r.E.toFixed(4); } }, { label: 'ln E', get: function (r) { return Math.log(r.E).toFixed(4); } }],
      live: function (r) { return 'b = ' + (r.b / 1e9).toFixed(4) + ' × 10^9 s/m²   E = ' + r.E.toFixed(4); },
      plan: function () { return [{ tog: {}, xs: [0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0].map(function (m) { return rnd(m * gmax, 4); }) }]; },
      result: function (rows) {
        var pts = rows.filter(function (r) { return r.E > 0.02; }).map(function (r) { return [r.b, Math.log(r.E)]; }), mc;
        if (pts.length < 6) return null; mc = line(pts);
        return { label: 'Self-diffusion coefficient D', value: -mc[0] * 1e9, unit: '10⁻⁹ m²/s', digits: 4, truth: p.D * 1e9,
          note: 'Slope of the straight line ln E against b, using the gradient pulse length δ = ' + (p.delta * 1e3).toFixed(1) + ' ms and diffusion time Δ = ' + (p.Dl * 1e3).toFixed(0) + ' ms.' };
      },
      info: 'Pulsed-field-gradient spin echo. Echo heights come from the Stejskal-Tanner formula with 0.2 % seeded noise.'
    };
  };

  ADAPT.phd_esr = function () {
    var MULT = [0.7, 1, 1.3], N = 1401;
    function fmt(f) { return f >= 1e9 ? (f / 1e9).toFixed(3) + ' GHz' : (f / 1e6).toFixed(2) + ' MHz'; }
    function q(tog) { return assign(p, { f: tog.f }); }
    return {
      trace: true, name: 'ESR derivative line', xl: 'B (mT)', yl: 'dχ″/dB (arb.)', min: 3,
      toggles: [{ key: 'f', label: 'RF frequency', def: p.f, opts: MULT.map(function (m) { return { v: p.f * m, l: fmt(p.f * m) }; }) }],
      capture: function (tog) {
        var qq = q(tog), b0n = H0 * tog.f / (2 * MUB), xs = [], ys = [], i, cz, mx, mn, b0, w, marks = [];
        for (i = 0; i < N; i++) { xs.push(b0n * (0.88 + 0.24 * i / (N - 1))); ys.push(KN.sig(qq, xs[i])); }
        mx = peaks(xs, ys, 1)[0]; mn = peaks(xs, ys, -1)[0];
        cz = cross(xs, ys, 0, -1); b0 = cz.length ? cz[0] : 0; w = (mn !== undefined && mx !== undefined) ? Math.abs(mn - mx) : 0;
        marks.push([b0 * 1e3, 0]);
        return { xs: xs.map(function (v) { return v * 1e3; }), ys: ys, marks: marks, row: { f: tog.f, B0: b0, dBpp: w } };
      },
      cols: [{ label: 'frequency', get: function (r) { return fmt(r.f); } }, { label: 'B0 (mT)', get: function (r) { return (r.B0 * 1e3).toFixed(4); } }, { label: 'ΔBpp (µT)', get: function (r) { return (r.dBpp * 1e6).toFixed(2); } },
        { label: 'g at this f', get: function (r) { return (H0 * r.f / (MUB * r.B0)).toFixed(4); } }],
      plan: function () { return MULT.map(function (m) { return { tog: { f: p.f * m } }; }); },
      result: function (rows) {
        var pts = rows.filter(function (r) { return r.B0 > 0; }).map(function (r) { return [r.f, r.B0]; }), mc, last, ge, t2;
        if (pts.length < 3) return null; mc = line(pts); last = rows[rows.length - 1];
        ge = H0 / (MUB * mc[0]); t2 = 2 / (Math.sqrt(3) * ge * MUB / HBAR * last.dBpp);
        return { label: 'g-factor from the slope of B0 against f', value: ge, unit: '', digits: 4, truth: p.g,
          note: 'The resonance field is proportional to the frequency, B0 = (h/(g μB)) f. Line width: ΔBpp = ' + sig(last.dBpp * 1e6, 3) + ' µT, so T2* = 2/(√3 γe ΔBpp) = ' + sig(t2 * 1e9, 3) + ' ns (simple Lorentzian line).' };
      },
      info: 'Sample in an RF coil between Helmholtz coils; the field is modulated and read by a lock-in, giving the derivative of the absorption.'
    };
  };

  ADAPT.phd_nmrcw = function () {
    var MULT = [0.8, 1, 1.25], N = 1201;
    function q(tog) { return assign(p, { f: tog.f }); }
    return {
      trace: true, name: 'CW NMR derivative line', xl: 'B (T)', yl: 'dχ″/dB (arb.)', min: 3,
      toggles: [{ key: 'f', label: 'RF frequency', def: p.f, opts: MULT.map(function (m) { return { v: p.f * m, l: (p.f * m / 1e6).toFixed(2) + ' MHz' }; }) }],
      capture: function (tog) {
        var qq = q(tog), b0n = 2 * Math.PI * tog.f / 2.6752218744e8, xs = [], ys = [], i, cz, b0;
        for (i = 0; i < N; i++) { xs.push(b0n * (0.85 + 0.3 * i / (N - 1))); ys.push(KN.sig(qq, xs[i])); }
        cz = cross(xs, ys, 0, -1); b0 = cz.length ? cz[0] : 0;
        return { xs: xs, ys: ys, marks: [[b0, 0]], row: { f: tog.f, B0: b0 } };
      },
      cols: [{ label: 'frequency (MHz)', get: function (r) { return (r.f / 1e6).toFixed(2); } }, { label: 'B0 (T)', get: function (r) { return r.B0.toFixed(5); } }, { label: 'γ at this f (10^8 rad/s T)', get: function (r) { return (2 * Math.PI * r.f / r.B0 / 1e8).toFixed(4); } }],
      plan: function () { return MULT.map(function (m) { return { tog: { f: p.f * m } }; }); },
      result: function (rows) {
        var pts = rows.filter(function (r) { return r.B0 > 0; }).map(function (r) { return [r.f, r.B0]; }), mc, gam;
        if (pts.length < 3) return null; mc = line(pts); gam = 2 * Math.PI / mc[0];
        return { label: 'Nuclear g-factor g_I = ħγ/μN', value: HBAR * gam / MUN, unit: '', digits: 4, truth: HBAR * p.gamma / MUN,
          note: 'The slope of B0 against f is 2π/γ, so γ = ' + sig(gam / 1e8, 5) + ' × 10^8 rad/(s T). The proton value is 5.5857.' };
      },
      info: 'Sample in an RF coil in the magnet gap; the field is modulated and read by a lock-in. The line width here is the magnet\'s inhomogeneity.'
    };
  };

  ADAPT.phd_mossbauer = function () {
    var N = 601;
    return {
      trace: true, sim: true, name: 'Moessbauer spectrum', xl: 'velocity (mm/s)', yl: 'transmission (%)', min: 1,
      toggles: [],
      capture: function () {
        var vs = [], ts = [], i, pk, marks = [], coef, eps, GE = -0.10348, GG = 0.18124, EG = 14412.5, C = 299792458;
        for (i = 0; i < N; i++) { vs.push(-12e-3 + 24e-3 * i / (N - 1)); ts.push(KN.trans(p, vs[i])); }
        pk = peaks(vs, ts, -1).filter(function (v) { return KN.trans(p, v) < 1 - 0.1 * p.depth; }).slice(0, 6);
        if (pk.length < 6) return { xs: vs.map(function (v) { return v * 1e3; }), ys: ts.map(function (v) { return v * 100; }), marks: [], row: { n: pk.length, Bhf: 0, delta: 0, eps: 0 } };
        pk.forEach(function (v) { marks.push([v * 1e3, KN.trans(p, v) * 100]); });
        coef = C * MUN / QE / EG * 2 * (1.5 * Math.abs(GE) + 0.5 * GG);
        eps = ((pk[0] + pk[5]) + (pk[2] + pk[3]) - 2 * (pk[1] + pk[4])) / 12;
        return { xs: vs.map(function (v) { return v * 1e3; }), ys: ts.map(function (v) { return v * 100; }), marks: marks, row: { n: 6, Bhf: (pk[5] - pk[0]) / coef, delta: (pk[0] + pk[1] + pk[2] + pk[3] + pk[4] + pk[5]) / 6 - eps / 3, eps: eps, lines: pk } };
      },
      cols: [{ label: 'lines found', get: function (r) { return String(r.n); } }, { label: 'B_hf (T)', get: function (r) { return r.Bhf.toFixed(3); } }, { label: 'isomer shift (mm/s)', get: function (r) { return (r.delta * 1e3).toFixed(3); } }, { label: 'quadrupole shift (mm/s)', get: function (r) { return (r.eps * 1e3).toFixed(3); } }],
      plan: function () { return [{ tog: {} }]; },
      result: function (rows) {
        var r = rows[rows.length - 1];
        if (!r || r.n < 6) return null;
        return { label: 'Hyperfine field B_hf from the outer lines', value: r.Bhf, unit: 'T', digits: 3, truth: p.Bhf,
          note: 'The six dip positions were found on the captured spectrum (parabola through each minimum); their spacing converts to a field with the 57Fe nuclear g-factors (unsourced / illustrative). Isomer shift ' + sig(r.delta * 1e3, 3) + ' mm/s, quadrupole shift ' + sig(r.eps * 1e3, 3) + ' mm/s. No counting noise is simulated.' };
      },
      info: 'A 57Co source on a constant-acceleration drive, an absorber and a gamma detector. SIMULATED INSTRUMENT.'
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
    function equipMb(S, T, M, h) {
    var g = new T.Group(); S.scene.add(g); g.position.set(-0.32, 0, -0.12);
    h.mk(g, h.box(0.32, 0.012, 0.12), M.iron, 0, 0.006, 0);
    var dr = h.mk(g, h.cyl(0.036, 0.036, 0.1, 32), M.steel, -0.09, 0.05, 0); dr.rotation.z = Math.PI / 2;
    var cap = h.mk(g, h.cyl(0.03, 0.03, 0.01, 32), M.chrome, -0.145, 0.05, 0); cap.rotation.z = Math.PI / 2;
    var dl = S.label('DOPPLER DRIVE', { w: 0.07, ratio: 0.14, color: '#e8eaec' }); dl.position.set(-0.09, 0.05, 0.037); g.add(dl);
    var rod = h.mk(g, h.cyl(0.004, 0.004, 0.05, 12), M.steel, -0.025, 0.05, 0); rod.rotation.z = Math.PI / 2;
    h.mk(g, h.box(0.03, 0.05, 0.05), M.grey, -0.005, 0.05, 0);
    var sl = S.label('SOURCE · SIMULATED (none present)', { w: 0.05, ratio: 0.25, color: '#fff', bg: '#8a1f1a' }); sl.position.set(-0.005, 0.085, 0.0255); g.add(sl);
    h.mk(g, h.box(0.012, 0.07, 0.012), M.black, 0.03, 0.045, 0.03); h.mk(g, h.box(0.012, 0.07, 0.012), M.black, 0.03, 0.045, -0.03);
    var dt = h.mk(g, h.cyl(0.024, 0.024, 0.06, 28), M.black, 0.1, 0.05, 0); dt.rotation.z = Math.PI / 2;
    var pm = h.mk(g, h.cyl(0.017, 0.017, 0.07, 24), M.steel, 0.145, 0.05, 0); pm.rotation.z = Math.PI / 2;
    var tl = S.label('DETECTOR', { w: 0.05, ratio: 0.2, color: '#e8eaec' }); tl.position.set(0.1, 0.05, 0.0245); g.add(tl);
    h.mk(g, h.box(0.03, 0.05, 0.05), M.grey, 0.065, 0.05, 0);
    S.contact(0.36, 0.16, -0.32, -0.12, 0.5);
    var sg = new T.Group(); S.scene.add(sg);
    h.mk(sg, h.box(0.004, 0.032, 0.032), M.bakelite, 0, 0, 0); h.mk(sg, h.box(0.0035, 0.022, 0.022), M.alu, 0.0005, 0, 0);
    sg.position.set(-0.2, 0.019, 0.13);
    h.mk(S.scene, h.box(0.07, 0.006, 0.05), M.bakelite, -0.2, 0.003, 0.13); S.contact(0.1, 0.08, -0.2, 0.13, 0.5);
    S.addApparatus('equip', g, 'Moessbauer spectrometer (simulated)', 'A Doppler drive moves the gamma source; the gamma rays cross the absorber and are counted by the detector. No radioactive source is present: this is a simulation.');
    S.addApparatus('sample', sg, 'Absorber foil', 'A thin iron foil in a holder.');
    return { sample: sg, mountPos: new T.Vector3(-0.29, 0.05, -0.12), lift: 0.1, grip: 0.06, view: [[-0.3, 0.26, 0.45], [-0.32, 0.05, -0.12]],
      mountButton: 'Fit the absorber foil', mountMsg: 'The absorber foil is in its holder between the source and the detector.',
      setupText: 'The absorber foil is on its tray. Fit it in the holder between the source and the detector, then switch on the instrument.', formula: '' };
  }
  function equip(S, T, M, h) {
    if (S.lab.kernel === 'phd_mossbauer') return equipMb(S, T, M, h);
    var g = new T.Group(); S.scene.add(g); g.position.set(-0.32, 0, -0.12);
    h.mk(g, h.box(0.3, 0.02, 0.19), M.iron, 0, 0.01, 0);
    h.mk(g, h.box(0.3, 0.03, 0.05), M.iron, 0, 0.215, -0.07);
    h.mk(g, h.box(0.035, 0.2, 0.05), M.iron, -0.13, 0.115, -0.07); h.mk(g, h.box(0.035, 0.2, 0.05), M.iron, 0.13, 0.115, -0.07);
    var p1 = h.mk(g, h.cyl(0.04, 0.032, 0.05, 32), M.steel, -0.075, 0.115, -0.07); p1.rotation.z = Math.PI / 2;
    var p2 = h.mk(g, h.cyl(0.04, 0.032, 0.05, 32), M.steel, 0.075, 0.115, -0.07); p2.rotation.z = -Math.PI / 2;
    var c1 = S.mesh(new T.TorusGeometry(0.047, 0.016, 12, 36), M.copper), c2 = S.mesh(new T.TorusGeometry(0.047, 0.016, 12, 36), M.copper);
    c1.rotation.y = Math.PI / 2; c1.position.set(-0.1, 0.115, -0.07); c2.rotation.y = Math.PI / 2; c2.position.set(0.1, 0.115, -0.07); g.add(c1); g.add(c2);
    h.mk(g, h.cyl(0.011, 0.011, 0.16, 18), M.glass, 0, 0.1, -0.07);
    var coil = S.mesh(new T.TorusGeometry(0.012, 0.0015, 8, 20), M.copper); coil.position.set(0, 0.115, -0.07); coil.rotation.x = Math.PI / 2; g.add(coil);
    h.mk(g, h.box(0.07, 0.04, 0.05), new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 }), 0.09, 0.04, 0.05);
    var rl = S.label('RF · LOCK-IN', { w: 0.06, ratio: 0.2, color: '#e8eaec' }); rl.position.set(0.09, 0.045, 0.0755); g.add(rl);
    var ml = S.label('MAGNET', { w: 0.08, ratio: 0.12, color: '#e8eaec' }); ml.position.set(0, 0.215, -0.043); g.add(ml);
    S.contact(0.34, 0.22, -0.32, -0.12, 0.5);
    var sg = new T.Group(); S.scene.add(sg);
    h.mk(sg, h.cyl(0.0085, 0.0085, 0.05, 18), new T.MeshStandardMaterial({ color: 0xeaeef0, roughness: 0.15, transparent: true, opacity: 0.75 }), 0, 0.025, 0);
    h.mk(sg, h.cyl(0.0068, 0.0068, 0.028, 18), new T.MeshStandardMaterial({ color: 0x3a2a14, roughness: 0.6 }), 0, 0.016, 0);
    h.mk(sg, h.cyl(0.009, 0.009, 0.008, 18), M.black, 0, 0.054, 0);
    sg.position.set(-0.2, 0.0, 0.13);
    h.mk(S.scene, h.box(0.07, 0.006, 0.05), M.bakelite, -0.2, 0.003, 0.13); S.contact(0.1, 0.08, -0.2, 0.13, 0.5);
    S.addApparatus('equip', g, 'Electromagnet and probe', 'Two pole pieces with coils and an iron yoke. The sample tube sits in the RF coil in the centre of the gap; the field is set by the magnet current.');
    S.addApparatus('sample', sg, 'Sample tube', 'A small sample tube (cap on top) that is placed in the probe coil.');
    return { sample: sg, mountPos: new T.Vector3(-0.32, 0.075, -0.19), lift: 0.12, grip: 0.07, view: [[-0.3, 0.3, 0.5], [-0.32, 0.12, -0.14]],
      mountButton: 'Place the sample tube', mountMsg: 'The sample tube is in the probe coil, in the middle of the magnet gap.',
      setupText: 'The sample tube is on its tray. Place it in the probe coil in the middle of the magnet gap, then switch on the instrument.', formula: '' };
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
