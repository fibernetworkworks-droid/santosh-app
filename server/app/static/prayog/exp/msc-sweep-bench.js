/* Prayogshala studio module: M.Sc. SWEEP BENCH (solid state transport and phase transitions).
   One bench, nine experiments: a sample goes into a chamber (furnace, cryostat, electromagnet, oil bath, hot stage or
   LCR fixture), the student sets ONE control (temperature, temperature difference, field or frequency), waits for it to
   settle and reads ONE meter. The kernel is the lab's own (msc_metal, msc_seebeck, msc_ionic, msc_super, msc_magres,
   msc_ferro, msc_curie, msc_lc, msc_diel in packs/msc_solid.js) - the same code the server checks against the closed
   formula. The hidden unknown (alpha, S, Ea, Tc, mu, ...) is never shown outside the result line. */
HoolaStudio.define('msc-sweep-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KNAME = S.lab.kernel, KN = HK.K[KNAME];
  var p = HK.paramsFor(KNAME, S.lab.params);
  var QEL = 1.602176634e-19, KBL = 1.380649e-23, E0 = 8.8541878128e-12;
  var V_ = S.lab.variant || {};
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function sig(v, n) { return v === 0 ? 0 : +v.toPrecision(n); }
  function lin(pts) { return S.fit.linear(pts); }
  function view(x) { var o = {}; o[SP.ctlKey] = SP.log ? Math.pow(10, x) : x; return KN.view({}, assign(p, o)); }

  // ================================================================ what each experiment reads and asks for
  var SPECS = {
    msc_metal: {
      scene: 'furnace', sample: V_.sample || 'Copper wire coil', ctlKey: 'T', ctlName: 'Oven temperature', unit: 'K', dig: 0,
      range: function () { return [293, 400, 1, 293]; },
      meter: { title: '4-WIRE OHMMETER', sub: 'resistance of the coil, 0.1 mΩ', unit: 'Ω', dp: 4 },
      read: function (x) { return rnd(view(x).R, 4); },
      row: function (x, v) { return { T: Math.round(x), R: v }; },
      cols: [['T (K)', function (r) { return r.T; }], ['R (Ω)', function (r) { return r.R.toFixed(4); }]],
      graph: { x: function (r) { return r.T; }, y: function (r) { return r.R; }, xlabel: 'T (K)', ylabel: 'R (Ω)' },
      auto: function () { return [293, 308, 323, 338, 353, 368, 383, 398]; }, nmin: 5,
      result: function (rows) {
        var f = lin(rows.map(function (r) { return [r.T, r.R]; })); if (!f || rows.length < 5) return null;
        return { label: 'Temperature coefficient of resistance', value: f.m / (f.c + f.m * p.Tref), unit: '/K', digits: 5, truth: p.alpha,
          note: 'Slope of R against T is ' + f.m.toFixed(5) + ' Ω/K; divided by the fitted resistance at ' + p.Tref + ' K (' + (f.c + f.m * p.Tref).toFixed(4) + ' Ω) it gives α. Taken from ' + rows.length + ' temperatures.' };
      },
      tol: 0.02, setupTitle: 'Coil in the oven, ohmmeter on',
      hint: 'Raise the oven in steps of about 15 K. At each step wait for the thermometer to settle, then read the four-wire ohmmeter.',
      formula: 'R = R₀ [1 + α (T − T₀)]', fnote: 'α = (dR/dT) / R(T₀)'
    },
    msc_seebeck: {
      scene: 'bath', sample: V_.sample || 'Thermocouple', ctlKey: 'dT', ctlName: 'Hot junction above cold (ΔT)', unit: 'K', dig: 0,
      range: function () { return [0, 100, 1, 0]; },
      meter: { title: 'MICROVOLTMETER', sub: 'thermo-EMF, 0.1 µV', unit: 'µV', dp: 1 },
      read: function (x) { return rnd(view(x).V, 1); },
      row: function (x, v) { return { dT: Math.round(x), V: v }; },
      cols: [['ΔT (K)', function (r) { return r.dT; }], ['EMF (µV)', function (r) { return r.V.toFixed(1); }]],
      graph: { x: function (r) { return r.dT; }, y: function (r) { return r.V; }, xlabel: 'ΔT (K)', ylabel: 'EMF (µV)' },
      auto: function () { return [10, 20, 30, 40, 50, 60, 70, 80, 90]; }, nmin: 5,
      result: function (rows) {
        var f = lin(rows.map(function (r) { return [r.dT, r.V]; })); if (!f || rows.length < 5) return null;
        return { label: 'Seebeck coefficient', value: f.m, unit: 'µV/K', digits: 2, truth: p.S,
          note: 'Slope of EMF against ΔT is ' + f.m.toFixed(2) + ' µV/K; the intercept ' + f.c.toFixed(1) + ' µV is the meter\'s zero error and does not enter the slope.' };
      },
      tol: 0.02, setupTitle: 'Junctions placed, meter zeroed',
      hint: 'Heat the oil bath in steps of 10 K. The cold junction stays in water at room temperature. At each step read the microvoltmeter.',
      formula: 'V = S ΔT', fnote: 'S in µV per kelvin'
    },
    msc_ionic: {
      scene: 'furnace', sample: V_.sample || 'Ionic crystal pellet', ctlKey: 'T', ctlName: 'Furnace temperature', unit: 'K', dig: 0,
      range: function () { return [400, 650, 1, 400]; },
      meter: { title: 'ELECTROMETER', sub: 'pellet resistance', unit: 'MΩ', dp: 0 },
      read: function (x) { return sig(view(x).R / 1e6, 4); },
      row: function (x, v) { var T0 = Math.round(x), sg = p.Lp / (v * 1e6 * p.Ap); return { T: T0, R: v, sigma: sg, invT: 1 / T0, lnsT: Math.log(sg * T0) }; },
      cols: [['T (K)', function (r) { return r.T; }], ['R (MΩ)', function (r) { return r.R; }], ['σ (S/m)', function (r) { return r.sigma.toExponential(2); }],
        ['1000/T (1/K)', function (r) { return (1000 * r.invT).toFixed(3); }], ['ln(σT)', function (r) { return r.lnsT.toFixed(3); }]],
      graph: { x: function (r) { return 1000 * r.invT; }, y: function (r) { return r.lnsT; }, xlabel: '1000/T (1/K)', ylabel: 'ln(σT)' },
      auto: function () { var a = [], t; for (t = 400; t <= 650; t += 25) a.push(t); return a; }, nmin: 6,
      result: function (rows) {
        var f = lin(rows.map(function (r) { return [r.invT, r.lnsT]; })); if (!f || rows.length < 6) return null;
        return { label: 'Activation energy', value: -KBL * f.m / QEL, unit: 'eV', digits: 3, truth: p.Ea,
          note: 'Slope of ln(σT) against 1/T is ' + f.m.toFixed(0) + ' K = −Ea/k, so Ea = k × |slope| ÷ e. Taken from ' + rows.length + ' temperatures.' };
      },
      tol: 0.03, setupTitle: 'Pellet in the holder, electrometer on',
      hint: 'Raise the furnace in 25 K steps, wait for the thermocouple to settle and read the pellet resistance. Then σ = L / (R A).',
      formula: 'σ T = A exp(−Ea / kT)', fnote: 'σ = L / (R A) for the pellet'
    },
    msc_super: {
      scene: 'cryo', sample: V_.sample || 'YBa₂Cu₃O₇ pellet', ctlKey: 'T', ctlName: 'Sample temperature', unit: 'K', dig: 1,
      range: function () { return [78, 140, 0.5, 78]; },
      meter: { title: 'NANOVOLTMETER', sub: 'across the inner leads, 10 mA through the outer', unit: 'µV', dp: 1 },
      read: function (x) { return rnd(view(x).V * 1e6, 1); },
      row: function (x, v) { return { T: rnd(x, 1), V: v, R: v / (p.I * 1e3) }; },
      cols: [['T (K)', function (r) { return r.T.toFixed(1); }], ['V (µV)', function (r) { return r.V.toFixed(1); }], ['R (mΩ)', function (r) { return r.R.toFixed(2); }]],
      graph: { x: function (r) { return r.T; }, y: function (r) { return r.R; }, xlabel: 'T (K)', ylabel: 'R (mΩ)' },
      auto: function () { return [-12, -7, -4, -2.5, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2.5, 4, 7, 12, 20, 30].map(function (o) { return rnd(p.Tc + o, 1); })
        .filter(function (t) { return t >= 78 && t <= 140; }); }, nmin: 10,
      result: function (rows) {
        var r = rows.slice().sort(function (a, b) { return a.T - b.T; }), n = r.length, i, f, fr, ta, tb, a, b;
        if (n < 10) return null;
        f = lin(r.slice(n - 4).map(function (q) { return [q.T, q.R]; })); if (!f) return null;
        fr = r.map(function (q) { return q.R / (f.c + f.m * q.T); });
        for (i = 0; i < n - 1; i++) if (fr[i] < 0.5 && fr[i + 1] >= 0.5) { a = r[i]; b = r[i + 1];
          return { label: 'Critical temperature Tc (midpoint)', value: a.T + (0.5 - fr[i]) * (b.T - a.T) / (fr[i + 1] - fr[i]), unit: 'K', digits: 1, truth: p.Tc,
            note: 'The normal-state line R = ' + f.c.toFixed(2) + ' + ' + f.m.toFixed(3) + ' T (mΩ) is extended through the transition; R falls to half of it between ' + a.T.toFixed(1) + ' K and ' + b.T.toFixed(1) + ' K.' }; }
        return null;
      },
      tol: 0.01, setupTitle: 'Sample cold, current on',
      hint: 'Let the sample warm slowly from liquid-nitrogen temperature. Take a reading every kelvin and every half kelvin through the fall.',
      formula: 'R(Tc) = ½ Rn(Tc)', fnote: 'Rn is the normal-state resistance extended down through the transition'
    },
    msc_magres: {
      scene: 'magnet', sample: V_.sample || 'Semiconductor bar', ctlKey: 'B', ctlName: 'Magnetic field in the gap', unit: 'T', dig: 2,
      range: function () { return [0, 0.8, 0.01, 0]; },
      meter: { title: 'DIGITAL OHMMETER', sub: 'resistance of the bar, 0.1 mΩ', unit: 'Ω', dp: 4 },
      read: function (x) { return rnd(view(x).R, 4); },
      row: function (x, v) { var b = rnd(x, 2); return { B: b, B2: b * b, R: v }; },
      cols: [['B (T)', function (r) { return r.B.toFixed(2); }], ['B² (T²)', function (r) { return r.B2.toFixed(4); }], ['R (Ω)', function (r) { return r.R.toFixed(4); }]],
      graph: { x: function (r) { return r.B2; }, y: function (r) { return r.R; }, xlabel: 'B² (T²)', ylabel: 'R (Ω)' },
      auto: function () { return [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]; }, nmin: 6,
      result: function (rows) {
        var f = lin(rows.map(function (r) { return [r.B2, r.R]; })); if (!f || rows.length < 6 || f.m <= 0 || f.c <= 0) return null;
        return { label: 'Carrier mobility', value: Math.sqrt(f.m / (p.xi * f.c)), unit: 'm²/V s', digits: 3, truth: p.mu,
          note: 'R = R₀ + R₀ μ² B²: slope ' + f.m.toFixed(4) + ' Ω/T², intercept R₀ = ' + f.c.toFixed(4) + ' Ω, so μ = √(slope / R₀). Taken from ' + rows.length + ' fields.' };
      },
      tol: 0.02, setupTitle: 'Bar in the gap, ohmmeter on',
      hint: 'Raise the field in 0.1 T steps. At each step read the gaussmeter and then the bar\'s resistance.',
      formula: 'ΔR / R₀ = (μ B)²', fnote: 'taking ξ = 1 for this lab'
    },
    msc_ferro: {
      scene: 'furnace', sample: V_.sample || 'Ferroelectric crystal plate (TGS)', ctlKey: 'T', ctlName: 'Hot-stage temperature', unit: 'K', dig: 1,
      range: function () { return [Math.round(p.Tc - 22), Math.round(p.Tc + 38), 0.1, Math.round(p.Tc - 22)]; },
      meter: { title: 'LCR METER · 1 kHz', sub: 'capacitance of the plate', unit: 'pF', dp: 2 },
      read: function (x) { return rnd(view(x).Cap * 1e12, 2); },
      row: function (x, v) { return { T: rnd(x, 1), C: v, eps: v * 1e-12 * p.d / (E0 * p.Ap) }; },
      cols: [['T (K)', function (r) { return r.T.toFixed(1); }], ['C (pF)', function (r) { return r.C.toFixed(2); }], ['ε', function (r) { return r.eps.toFixed(0); }],
        ['1/ε (10⁻³)', function (r) { return (1000 / r.eps).toFixed(3); }]],
      graph: { x: function (r) { return r.T; }, y: function (r) { return r.eps; }, xlabel: 'T (K)', ylabel: 'ε' },
      auto: function () { return [-20, -12, -6, -3, -1.2, 0, 0.4, 1.2, 3, 6, 10, 14, 18, 22, 26, 30, 35].map(function (o) { return rnd(p.Tc + o, 1); }); }, nmin: 12,
      result: function (rows) {
        var pk = rows[0], i, pts, f; if (rows.length < 12) return null;
        rows.forEach(function (r) { if (r.eps > pk.eps) pk = r; });
        pts = rows.filter(function (r) { return r.T >= pk.T + 5; }).map(function (r) { return [r.T, 1 / r.eps]; });
        if (pts.length < 4) return null; f = lin(pts); if (!f || f.m <= 0) return null;
        return { label: 'Curie-Weiss temperature', value: -f.c / f.m, unit: 'K', digits: 1, truth: p.Tc,
          note: 'The peak of ε is at ' + pk.T.toFixed(1) + ' K. Above it 1/ε against T is a line (' + pts.length + ' points, T ≥ peak + 5 K): it cuts zero at the Curie-Weiss temperature, and its slope gives C = ' + (1 / f.m).toFixed(0) + ' K.' };
      },
      tol: 0.01, setupTitle: 'Crystal on the stage, LCR meter on',
      hint: 'Heat slowly through the transition. Read every few kelvin, and every degree or less near the peak of the capacitance.',
      formula: 'ε = ε₀-free form: ε = C d / (ε₀ A);   ε = C / (T − Tc)', fnote: 'C is the Curie constant'
    },
    msc_curie: {
      scene: 'furnace', sample: V_.sample || 'Ferrite ring with a coil', ctlKey: 'T', ctlName: 'Furnace temperature', unit: 'K', dig: 1,
      range: function () { return [Math.round(p.Tc - 100), Math.round(p.Tc + 60), 0.5, Math.round(p.Tc - 100)]; },
      meter: { title: 'LCR METER · 1 kHz', sub: 'inductance of the coil', unit: 'mH', dp: 2 },
      read: function (x) { return rnd(view(x).L * 1e3, 2); },
      row: function (x, v) { return { T: rnd(x, 1), L: v }; },
      cols: [['T (K)', function (r) { return r.T.toFixed(1); }], ['L (mH)', function (r) { return r.L.toFixed(2); }]],
      graph: { x: function (r) { return r.T; }, y: function (r) { return r.L; }, xlabel: 'T (K)', ylabel: 'L (mH)' },
      auto: function () { return [-100, -75, -50, -35, -20, -14, -11, -8, -5, -2, 1, 4, 8, 14, 24, 40, 60].map(function (o) { return rnd(p.Tc + o, 1); }); }, nmin: 10,
      result: function (rows) {
        var r = rows.slice().sort(function (a, b) { return a.T - b.T; }), n = r.length, i, s, best = null, base, a, b;
        if (n < 10) return null;
        for (i = 0; i < n - 1; i++) { a = r[i]; b = r[i + 1]; s = (b.L - a.L) / (b.T - a.T);
          if (best === null || s < best.s) best = { s: s, t: (a.T + b.T) / 2, l: (a.L + b.L) / 2 }; }
        if (!best || best.s >= 0) return null;
        base = (r[n - 1].L + r[n - 2].L + r[n - 3].L) / 3;
        return { label: 'Curie temperature (tangent method)', value: best.t + (best.l - base) / -best.s, unit: 'K', digits: 1, truth: p.Tc,
          note: 'The steepest fall is near ' + best.t.toFixed(1) + ' K (slope ' + best.s.toFixed(2) + ' mH/K). The tangent there meets the high-temperature baseline (' + base.toFixed(2) + ' mH) at the Curie temperature.' };
      },
      tol: 0.01, setupTitle: 'Core in the furnace, LCR meter on',
      hint: 'Heat in steps and take smaller steps where the inductance falls fastest. Then draw the tangent at the steepest part and the baseline at high temperature.',
      formula: 'L = L₀ [1 + (μᵣ − 1) g(T)]', fnote: 'Tc: where the tangent at the steepest fall meets the baseline'
    },
    msc_lc: {
      scene: 'hotstage', sample: V_.sample || '5CB (4-cyano-4\'-pentylbiphenyl) cell', ctlKey: 'T', ctlName: 'Hot-stage temperature', unit: 'K', dig: 2,
      range: function () { return [rnd(p.Tni - 14, 0), rnd(p.Tni + 6, 0), 0.05, rnd(p.Tni - 14, 0)]; },
      meter: { title: 'PHOTODIODE AMPLIFIER', sub: 'light through the crossed polarisers', unit: 'mV', dp: 0 },
      read: function (x) { return Math.round(view(x).I * 1000); },
      row: function (x, v) { return { T: rnd(x, 2), I: v }; },
      cols: [['T (K)', function (r) { return r.T.toFixed(2); }], ['signal (mV)', function (r) { return r.I; }]],
      graph: { x: function (r) { return r.T; }, y: function (r) { return r.I; }, xlabel: 'T (K)', ylabel: 'signal (mV)' },
      autoRun: function (api) {
        var offs = [-12, -9, -6, -4, -2, 2, 4], lo = p.Tni - 2, hi = p.Tni + 2, k = 0;
        function bis() { if (k >= 5) return Promise.resolve(); var mid = rnd((lo + hi) / 2, 2);
          return api.go(mid).then(function () { var rr = api.rec(); if (rr && rr.I > 20) lo = mid; else hi = mid; k++; return bis(); }); }
        return offs.reduce(function (pr, o) { return pr.then(function () { return api.go(rnd(p.Tni + o, 2)); }).then(function () { api.rec(); }); }, Promise.resolve()).then(bis);
      }, nmin: 9,
      result: function (rows) {
        var r = rows.slice().sort(function (a, b) { return a.T - b.T; }), n = r.length, k = n, i;
        if (n < 9) return null;
        for (i = n - 1; i >= 0 && r[i].I < 20; i--) k = i;
        if (k === 0 || k >= n) return null;
        return { label: 'Nematic-isotropic transition temperature', value: (r[k - 1].T + r[k].T) / 2, unit: 'K', digits: 2, truth: p.Tni,
          note: 'The signal is still ' + r[k - 1].I + ' mV at ' + r[k - 1].T.toFixed(2) + ' K and is dark (' + r[k].I + ' mV) from ' + r[k].T.toFixed(2) + ' K on. The transition lies between them.' };
      },
      tol: 0.004, setupTitle: 'Cell on the stage, laser and photodiode on',
      hint: 'Heat slowly. The signal passes through bright and dark fringes. When it drops to the dark level and stays there, narrow the interval by halving it.',
      formula: 'I = I₀ sin²(π Δn d / λ)', fnote: 'Δn follows the order parameter S(T); at T_NI the order vanishes'
    },
    msc_diel: {
      scene: 'lcr', sample: V_.sample || 'Polar dielectric disc', ctlKey: 'f', ctlName: 'Meter frequency (log scale)', unit: 'Hz', dig: 0, log: true,
      range: function () { return [2, 6, 0.05, 3]; },
      meter: { title: 'LCR METER', sub: 'capacitance of the cell at the set frequency', unit: 'pF', dp: 2 },
      read: function (x) { return rnd(view(x).C_pF, 2); },
      row: function (x, v) { var f = Math.round(Math.pow(10, x)); var d = view(x); return { f: f, C: v, D: rnd(d.D, 4), er: v * 1e-12 * p.d / (E0 * p.Ap) }; },
      cols: [['f (Hz)', function (r) { return r.f; }], ['C (pF)', function (r) { return r.C.toFixed(2); }], ['tan δ', function (r) { return r.D.toFixed(4); }], ['ε′', function (r) { return r.er.toFixed(3); }]],
      graph: { x: function (r) { return Math.log10(r.f); }, y: function (r) { return r.er; }, xlabel: 'log₁₀ f', ylabel: 'ε′' },
      auto: function () { return [2, 2.30103, 2.69897, 3, 3.30103, 3.69897, 4, 4.30103, 4.69897, 5, 5.30103, 5.69897, 6]; }, nmin: 8,
      result: function (rows) {
        var lowr = rows.filter(function (r) { return r.f <= 1000; }); if (rows.length < 8 || lowr.length < 3) return null;
        return { label: 'Static dielectric constant', value: S.fit.mean(lowr.map(function (r) { return r.er; })), unit: '', digits: 3, truth: p.es,
          note: 'ε′ = C d / (ε₀ A) averaged over the readings at 1 kHz and below (' + lowr.length + ' of them), where the dipoles follow the field. At higher frequency ε′ ' +
            (p.fr < 1e8 ? 'falls round the relaxation frequency, and tan δ peaks there.' : 'stays flat: this solid has no relaxation in the meter\'s range.') };
      },
      tol: 0.02, setupTitle: 'Compensate the meter, clamp the sample',
      hint: 'Step the frequency from 100 Hz to 1 MHz (about five readings a decade is fine). At each one record C and tan δ; ε′ follows from the cell dimensions.',
      formula: 'ε′ = C d / (ε₀ A)', fnote: 'guarded plates: edge fields are not counted'
    }
  };
  var SP = SPECS[KNAME];
  var RANGE = SP.range(), CLO = RANGE[0], CHI = RANGE[1], CSTEP = RANGE[2];
  var st = { mounted: false, on: false, x: RANGE[3], settling: false, open: !SP.openShort, short: !SP.openShort, hot: 0 };
  if (SP.scene === 'lcr') { st.open = false; st.short = false; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function raw() { return st.on && st.mounted ? SP.read(st.x) : null; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }

  // ================================================================ shared little builders
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 24); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }
  var steelM = new T.MeshStandardMaterial({ color: 0x5a6069, roughness: 0.55, metalness: 0.45 });
  var glowM = new T.MeshBasicMaterial({ color: 0xff5a1e, transparent: true, opacity: 0, depthWrite: false, blending: T.AdditiveBlending });

  function instBox(x, z, rotY, title, sub, wdt) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = rotY;
    var W = wdt || 0.2, D = 0.15, Hh = 0.08;
    var cse = S.rounded(W, D, Hh, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 }));
    cse.rotation.x = -Math.PI / 2; cse.position.y = Hh / 2 + 0.003; g.add(cse);
    var FZ = D / 2 + 0.005, PW = W - 0.012, PH = Hh - 0.012;
    var tex = S.canvasTex(900, Math.round(900 * PH / PW), function (xx, w, h) {
      xx.fillStyle = '#2b323d'; xx.fillRect(0, 0, w, h);
      xx.strokeStyle = 'rgba(255,255,255,.12)'; xx.lineWidth = 3; xx.strokeRect(8, 8, w - 16, h - 16);
      xx.fillStyle = '#f1efe8'; xx.font = '700 34px "Public Sans", sans-serif'; xx.fillText(title, 26, 52);
      xx.font = '500 22px "Public Sans", sans-serif'; xx.fillStyle = '#c7ccd6'; xx.fillText(sub, 26, 88);
    });
    var fac = S.mesh(box(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]);
    fac.position.set(0, 0.003 + Hh / 2, FZ - 0.002); g.add(fac);
    var lcdT = S.liveTex(512, 180), last = '';
    var bez = S.mesh(box(PW * 0.52, PH * 0.42, 0.003), M.grey); bez.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.001); g.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(PW * 0.48, PH * 0.38), new T.MeshBasicMaterial({ map: lcdT, toneMapped: false }));
    scr.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(scr);
    var knobG = new T.Group(); knobG.position.set(-PW * 0.28, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(knobG);
    var kk = S.mesh(cyl(0.012, 0.013, 0.012, 28), M.bakelite); kk.rotation.x = Math.PI / 2; knobG.add(kk);
    var kp = S.mesh(box(0.0018, 0.012, 0.001), M.white, false); kp.position.set(0, 0.007, 0.007); knobG.add(kp);
    S.contact(W + 0.06, D + 0.06, x, z, 0.5);
    return { group: g, knob: knobG,
      show: function (txt, u2) {
        if (txt + u2 === last) return; last = txt + u2;
        lcdT.draw(function (xx) {
          var gr = xx.createLinearGradient(0, 0, 0, 180); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
          xx.fillStyle = gr; xx.fillRect(0, 0, 512, 180);
          xx.font = '700 ' + (txt.length > 7 ? 70 : 92) + 'px "JetBrains Mono", monospace'; xx.textAlign = 'right';
          xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 118);
          xx.font = '600 34px "Public Sans", sans-serif'; xx.fillText(u2, 496, 150);
        });
      } };
  }

  // ================================================================ the chamber of each scene
  var chamberG = new T.Group(); S.scene.add(chamberG);
  var sampleG = new T.Group(); S.scene.add(sampleG);
  var PARK = new T.Vector3(-0.06, 0.012, 0.17), MOUNT = new T.Vector3(-0.32, 0.085, -0.12);
  var chamberName = 'Chamber', chamberInfo = '', tickScene = function () {};
  var sampleMat = new T.MeshStandardMaterial({ color: 0x6e747c, roughness: 0.3, metalness: 0.8 });

  function furnace() {
    chamberG.position.set(-0.32, 0, -0.12);
    var OW = 0.22, OD = 0.2, OH = 0.17, WW = 0.1, WH = 0.07, WY = 0.09, TH = 0.007, FZP = OD / 2 - TH / 2;
    function panel(w, h, d, x, y, z) { return mk(chamberG, box(w, h, d), steelM, x, y, z); }
    panel(OW, TH, OD, 0, TH / 2 + 0.006, 0); panel(OW, OH, TH, 0, OH / 2 + 0.006, -OD / 2 + TH / 2);
    panel(TH, OH, OD, -OW / 2 + TH / 2, OH / 2 + 0.006, 0); panel(TH, OH, OD, OW / 2 - TH / 2, OH / 2 + 0.006, 0);
    panel(OW, TH, OD, 0, OH + 0.006 - TH / 2, 0);
    panel((OW - WW) / 2, OH, TH, -(WW + (OW - WW) / 2) / 2, OH / 2 + 0.006, FZP); panel((OW - WW) / 2, OH, TH, (WW + (OW - WW) / 2) / 2, OH / 2 + 0.006, FZP);
    panel(WW, OH - (WY + WH / 2), TH, 0, (WY + WH / 2 + OH) / 2 + 0.006, FZP); panel(WW, WY - WH / 2, TH, 0, (WY - WH / 2) / 2 + 0.006, FZP);
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) { mk(chamberG, cyl(0.008, 0.009, 0.006, 16), M.rubber, f[0] * (OW / 2 - 0.02), 0.003, f[1] * (OD / 2 - 0.02)); });
    var win = S.mesh(box(WW, WH, 0.0025), new T.MeshStandardMaterial({ color: 0xdfe6ea, roughness: 0.08, transparent: true, opacity: 0.16 }), false, false);
    win.position.set(0, WY + 0.006, OD / 2 - TH / 2); chamberG.add(win);
    var coil = S.mesh(new T.TorusGeometry(0.06, 0.004, 8, 32), glowM, false, false); coil.rotation.x = Math.PI / 2; coil.position.set(0, 0.06, 0); chamberG.add(coil);
    mk(chamberG, cyl(0.04, 0.045, 0.012, 28), M.iron, 0, 0.075, 0);
    mk(chamberG, cyl(0.0015, 0.0015, 0.08, 10), M.copper, 0.03, 0.1, 0.02);
    var lamp = new T.PointLight(0xfff0d8, 0.5, 0.5); lamp.position.set(0, 0.1, 0.06); chamberG.add(lamp);
    var lbl = S.label('FURNACE · 700 K', { w: 0.11, ratio: 0.14, color: '#e8eaec' }); lbl.position.set(0, 0.03, OD / 2 + 0.007); chamberG.add(lbl);
    S.contact(0.3, 0.28, -0.32, -0.12, 0.55);
    chamberName = 'Sample furnace'; chamberInfo = 'A small furnace with the sample stage inside it. It is heated slowly and held at each temperature until the thermocouple beside the sample is steady.';
    MOUNT.set(-0.32, 0.085, -0.12);
    // the sample on its stage
    if (KNAME === 'msc_metal') {
      var form = S.mesh(cyl(0.012, 0.012, 0.03, 20), new T.MeshStandardMaterial({ color: 0xe9dfcf, roughness: 0.8 })); sampleG.add(form);
      for (var i = 0; i < 9; i++) { var tor = S.mesh(new T.TorusGeometry(0.0135, 0.0012, 6, 20), M.copper); tor.rotation.x = Math.PI / 2; tor.position.y = -0.012 + i * 0.003; sampleG.add(tor); }
    } else if (KNAME === 'msc_curie') {
      var ring = S.mesh(new T.TorusGeometry(0.014, 0.006, 12, 28), new T.MeshStandardMaterial({ color: 0x2a2a2c, roughness: 0.35, metalness: 0.25 })); ring.rotation.x = Math.PI / 2; sampleG.add(ring);
      for (var j = 0; j < 14; j++) { var a = j / 14 * Math.PI * 2, w2 = S.mesh(new T.TorusGeometry(0.0072, 0.0007, 6, 12), M.copper);
        w2.position.set(Math.cos(a) * 0.014, 0, Math.sin(a) * 0.014); w2.rotation.set(0, -a, 0); sampleG.add(w2); }
    } else if (KNAME === 'msc_ionic') {
      var pel = S.mesh(cyl(0.013, 0.013, 0.004, 28), new T.MeshStandardMaterial({ color: 0xf0eee8, roughness: 0.7 })); sampleG.add(pel);
      var pl1 = S.mesh(cyl(0.015, 0.015, 0.002, 28), M.steel); pl1.position.y = 0.0032; sampleG.add(pl1);
      var pl2 = S.mesh(cyl(0.015, 0.015, 0.002, 28), M.steel); pl2.position.y = -0.0032; sampleG.add(pl2);
    } else {
      var cr = S.mesh(box(0.024, 0.0025, 0.02), new T.MeshStandardMaterial({ color: 0xe8f1ec, roughness: 0.1, transparent: true, opacity: 0.8 })); sampleG.add(cr);
      var e1 = S.mesh(box(0.024, 0.0007, 0.02), M.brass); e1.position.y = 0.0016; sampleG.add(e1);
      var e2 = S.mesh(box(0.024, 0.0007, 0.02), M.brass); e2.position.y = -0.0016; sampleG.add(e2);
    }
    tickScene = function () { var hot = Math.max(0, Math.min(1, (st.x - CLO) / Math.max(CHI - CLO, 1))); if (KNAME === 'msc_ferro' || KNAME === 'msc_curie') hot = Math.max(0, Math.min(1, (st.x - CLO) / 160));
      glowM.opacity = st.on && st.mounted ? hot * 0.45 : 0; };
  }

  function cryo() {
    chamberG.position.set(-0.32, 0, -0.12);
    var dew = mk(chamberG, cyl(0.07, 0.07, 0.2, 40), new T.MeshStandardMaterial({ color: 0xaeb4ba, roughness: 0.3, metalness: 0.9 }), 0, 0.1, 0);
    var neck = mk(chamberG, cyl(0.03, 0.03, 0.05, 32), M.alu, 0, 0.225, 0);
    var win = mk(chamberG, cyl(0.045, 0.045, 0.06, 32), new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, transmission: 0.9, thickness: 0.004, transparent: true, opacity: 0.35 }), 0, 0.28, 0);
    mk(chamberG, cyl(0.048, 0.048, 0.008, 32), M.alu, 0, 0.314, 0);
    mk(chamberG, cyl(0.006, 0.006, 0.12, 12), M.steel, 0, 0.37, 0);
    mk(chamberG, cyl(0.014, 0.014, 0.012, 20), M.copper, 0, 0.268, 0);                   // the copper cold block
    mk(chamberG, cyl(0.062, 0.062, 0.002, 32), M.black, 0, 0.202, 0);
    var frost = mk(chamberG, cyl(0.0145, 0.0145, 0.012, 20), new T.MeshStandardMaterial({ color: 0xf2f8ff, roughness: 0.9, transparent: true, opacity: 0.0 }), 0, 0.268, 0);
    var lbl = S.label('LN₂ CRYOSTAT  ·  77 K', { w: 0.1, ratio: 0.14, color: '#20252b', bg: '#d8dde2' }); lbl.position.set(0, 0.1, 0.0705); chamberG.add(lbl);
    S.contact(0.2, 0.2, -0.32, -0.12, 0.55);
    chamberName = 'Cryostat'; chamberInfo = 'A vacuum cryostat cooled by liquid nitrogen. The sample sits on a copper block whose temperature is read by a silicon diode; it warms slowly once the cooling is stopped.';
    MOUNT.set(-0.32, 0.292, -0.12);
    var pel = S.mesh(cyl(0.011, 0.011, 0.003, 24), new T.MeshStandardMaterial({ color: 0x15171a, roughness: 0.5, metalness: 0.2 })); sampleG.add(pel);
    for (var i = 0; i < 4; i++) { var c = S.mesh(cyl(0.0007, 0.0007, 0.012, 8), M.copper); c.position.set((i - 1.5) * 0.005, 0.003, 0); c.rotation.z = Math.PI / 2; sampleG.add(c); }
    tickScene = function () { frost.material.opacity = st.on && st.mounted ? Math.max(0, Math.min(0.9, (140 - st.x) / 60)) : 0; };
  }

  function magnet() {
    chamberG.position.set(-0.32, 0, -0.12);
    var yoke = new T.MeshStandardMaterial({ color: 0x3a4249, roughness: 0.5, metalness: 0.6 });
    mk(chamberG, box(0.3, 0.03, 0.06), yoke, 0, 0.215, 0); mk(chamberG, box(0.3, 0.03, 0.06), yoke, 0, 0.015, 0);
    mk(chamberG, box(0.03, 0.2, 0.06), yoke, -0.135, 0.115, 0); mk(chamberG, box(0.03, 0.2, 0.06), yoke, 0.135, 0.115, 0);
    var pole1 = mk(chamberG, cyl(0.035, 0.03, 0.04, 32), M.iron, 0, 0.18, 0), pole2 = mk(chamberG, cyl(0.03, 0.035, 0.04, 32), M.iron, 0, 0.05, 0);
    mk(chamberG, cyl(0.05, 0.05, 0.05, 32), M.copper, 0, 0.185, 0); mk(chamberG, cyl(0.05, 0.05, 0.05, 32), M.copper, 0, 0.045, 0);
    var lbl = S.label('ELECTROMAGNET', { w: 0.1, ratio: 0.14, color: '#e8eaec' }); lbl.position.set(0, 0.215, 0.0305); chamberG.add(lbl);
    S.contact(0.34, 0.12, -0.32, -0.12, 0.55);
    chamberName = 'Electromagnet'; chamberInfo = 'An iron yoke with two coils and flat pole pieces about 20 mm apart. The field in the gap follows the coil current and is read by the gaussmeter, never assumed.';
    MOUNT.set(-0.32, 0.115, -0.12);
    var bar = S.mesh(box(0.02, 0.0015, 0.012), new T.MeshStandardMaterial({ color: 0x7c828a, roughness: 0.25, metalness: 0.8 })); sampleG.add(bar);
    var stick = S.mesh(box(0.004, 0.003, 0.09), M.bakelite); stick.position.z = 0.05; sampleG.add(stick);
    for (var i = 0; i < 4; i++) { var w = S.mesh(cyl(0.0004, 0.0004, 0.05, 6), i % 2 ? M.copper : M.steel); w.rotation.x = Math.PI / 2; w.position.set((i - 1.5) * 0.004, 0.002, 0.03); sampleG.add(w); }
    tickScene = function () {};
  }

  function bath() {
    chamberG.position.set(-0.32, 0, -0.12);
    mk(chamberG, cyl(0.07, 0.07, 0.025, 36), M.alu, 0, 0.0125, 0);                      // the hot plate
    var knb = mk(chamberG, cyl(0.009, 0.009, 0.012, 20), M.bakelite, 0.04, 0.02, 0.066); knb.rotation.x = Math.PI / 2;
    var bk = S.beaker(0.05, 0.11, [-0.32, 0.026, -0.12], 0xe8d27a, 0.7); bk.scale.set(1, 1, 1);
    var cold = S.beaker(0.035, 0.08, [-0.18, 0.0, -0.2], 0x9fd0e6, 0.6);
    var hotT = mk(chamberG, cyl(0.002, 0.002, 0.16, 10), M.chrome, 0.03, 0.1, 0.02);
    var glowDot = mk(chamberG, new T.SphereGeometry(0.0035, 10, 10), new T.MeshBasicMaterial({ color: 0xff5a1e, transparent: true, opacity: 0 }), 0.03, 0.025, 0.02);
    var lbl = S.label('HOT PLATE + OIL BATH', { w: 0.1, ratio: 0.14, color: '#20252b', bg: '#d8dde2' }); lbl.position.set(0, 0.012, 0.0705); chamberG.add(lbl);
    S.contact(0.17, 0.17, -0.32, -0.12, 0.55);
    chamberName = 'Oil bath'; chamberInfo = 'Silicone oil on a stirred hot plate. The hot junction of the thermocouple dips into the oil; the cold junction stays in a beaker of water at room temperature.';
    MOUNT.set(-0.32, 0.055, -0.1);
    var j = S.mesh(new T.SphereGeometry(0.0035, 10, 10), M.copper); sampleG.add(j);
    var w1 = S.mesh(cyl(0.0006, 0.0006, 0.1, 6), M.copper); w1.position.set(0.002, 0.05, 0); sampleG.add(w1);
    var w2 = S.mesh(cyl(0.0006, 0.0006, 0.1, 6), M.brass); w2.position.set(-0.002, 0.05, 0); sampleG.add(w2);
    tickScene = function () { glowDot.material.opacity = st.on && st.mounted ? Math.min(0.5, st.x / 200) : 0; if (bk.setLevel) bk.setLevel(0.7); };
  }

  function hotstage() {
    chamberG.position.set(-0.32, 0, -0.12);
    var rail = mk(chamberG, box(0.5, 0.012, 0.02), M.alu, 0.0, 0.006, 0.0);
    var laser = mk(chamberG, cyl(0.014, 0.014, 0.11, 24), new T.MeshStandardMaterial({ color: 0x20262e, roughness: 0.4, metalness: 0.5 }), -0.2, 0.04, 0); laser.rotation.z = Math.PI / 2;
    mk(chamberG, cyl(0.002, 0.002, 0.005, 8), new T.MeshBasicMaterial({ color: 0xff2a1a }), -0.145, 0.04, 0).rotation.z = Math.PI / 2;
    function pol(x, deg) { var ring = mk(chamberG, new T.TorusGeometry(0.02, 0.003, 10, 28), M.bakelite, x, 0.04, 0); ring.rotation.y = Math.PI / 2;
      var f = mk(chamberG, cyl(0.019, 0.019, 0.002, 28), new T.MeshStandardMaterial({ color: 0x8a8d91, roughness: 0.3, transparent: true, opacity: 0.5 }), x, 0.04, 0); f.rotation.z = Math.PI / 2;
      mk(chamberG, cyl(0.004, 0.004, 0.04, 8), M.steel, x, 0.02, 0); return ring; }
    pol(-0.1, 0); pol(0.1, 90);
    var stage = mk(chamberG, box(0.05, 0.012, 0.05), M.copper, 0.0, 0.025, 0);
    mk(chamberG, cyl(0.004, 0.004, 0.03, 8), M.steel, 0, 0.012, 0);
    var pd = mk(chamberG, box(0.03, 0.03, 0.02), new T.MeshStandardMaterial({ color: 0x20262e, roughness: 0.4 }), 0.2, 0.04, 0);
    var beam = mk(chamberG, cyl(0.0008, 0.0008, 0.34, 6), new T.MeshBasicMaterial({ color: 0xff3a2a, transparent: true, opacity: 0.55 }), 0.0, 0.04, 0); beam.rotation.z = Math.PI / 2;
    var lbl = S.label('LASER · POLARISER · HOT STAGE · ANALYSER · PHOTODIODE', { w: 0.34, ratio: 0.06, color: '#e8eaec', bg: '#2b323d' }); lbl.position.set(0, 0.0125, 0.0105); chamberG.add(lbl);
    S.contact(0.55, 0.12, -0.32, -0.12, 0.5);
    chamberName = 'Polarising optics and hot stage'; chamberInfo = 'A red laser, a polariser, the heated cell with its optic axis at 45°, an analyser crossed with the polariser and a photodiode behind it.';
    MOUNT.set(-0.32, 0.036, -0.12);
    var cell = S.mesh(box(0.024, 0.002, 0.024), new T.MeshStandardMaterial({ color: 0xdfeaf0, roughness: 0.08, transparent: true, opacity: 0.55 })); sampleG.add(cell);
    var drop = S.mesh(box(0.012, 0.0022, 0.012), new T.MeshStandardMaterial({ color: 0xe9e4d6, roughness: 0.2, transparent: true, opacity: 0.8 })); sampleG.add(drop);
    var spot = S.mesh(cyl(0.012, 0.012, 0.0012, 24), new T.MeshBasicMaterial({ color: 0xff3020, transparent: true, opacity: 0.0 }), false, false); spot.position.y = 0.0022; sampleG.add(spot);
    tickScene = function () { var v = st.on && st.mounted ? view(st.x).I : 0; spot.material.opacity = Math.max(0, Math.min(0.9, v)); beam.material.opacity = st.on ? 0.55 : 0; };
  }

  function lcr() {
    chamberG.position.set(-0.32, 0, -0.12);
    var base = mk(chamberG, box(0.16, 0.012, 0.09), M.bakelite, 0, 0.006, 0);
    var post = mk(chamberG, cyl(0.007, 0.007, 0.12, 14), M.chrome, -0.06, 0.07, 0);
    var arm = mk(chamberG, box(0.1, 0.01, 0.014), M.alu, -0.01, 0.13, 0);
    var lowerP = mk(chamberG, cyl(0.026, 0.026, 0.004, 32), M.brass, 0.0, 0.032, 0);
    mk(chamberG, cyl(0.01, 0.01, 0.02, 14), M.bakelite, 0.0, 0.02, 0);
    var upper = new T.Group(); upper.position.set(0.0, 0.1, 0); chamberG.add(upper);
    mk(upper, cyl(0.026, 0.026, 0.004, 32), M.brass, 0, 0, 0); mk(upper, cyl(0.03, 0.03, 0.002, 32), M.brass, 0, 0, 0).material = M.chrome;
    mk(upper, cyl(0.004, 0.004, 0.03, 12), M.steel, 0, 0.017, 0);
    var mic = mk(chamberG, cyl(0.009, 0.009, 0.022, 18), M.steel, 0.0, 0.147, 0);
    var thimble = mk(chamberG, cyl(0.011, 0.011, 0.02, 20), M.bakelite, 0.0, 0.166, 0);
    var lbl = S.label('GUARDED CELL', { w: 0.08, ratio: 0.14, color: '#e8eaec' }); lbl.position.set(0, 0.006, 0.0455); chamberG.add(lbl);
    S.contact(0.2, 0.12, -0.32, -0.12, 0.5);
    chamberName = 'Dielectric cell'; chamberInfo = 'Two flat brass plates in a guarded holder. The upper plate is lowered with a micrometer screw until the sample disc is held between them.';
    MOUNT.set(-0.32, 0.0375, -0.12);
    var disc = S.mesh(cyl(0.022, 0.022, 0.0035, 36), new T.MeshStandardMaterial({ color: 0xece9e0, roughness: 0.6 })); sampleG.add(disc);
    tickScene = function () { upper.position.y = st.mounted ? 0.0415 : 0.1; thimble.position.y = st.mounted ? 0.1 : 0.166; mic.position.y = st.mounted ? 0.083 : 0.147; };
  }
  ({ furnace: furnace, cryo: cryo, magnet: magnet, bath: bath, hotstage: hotstage, lcr: lcr })[SP.scene]();
  // the lcr cell's moving parts are positioned from tick; the others sit still
  var tray = mk(S.scene, cyl(0.03, 0.03, 0.004, 28), M.alu, PARK.x, 0.002, PARK.z);
  S.contact(0.08, 0.08, PARK.x, PARK.z, 0.5);
  sampleG.position.copy(PARK);

  // ================================================================ the instruments
  var ctl = instBox(0.0, 0.1, -0.1, SP.ctlName.toUpperCase().slice(0, 28), 'sets the ' + (SP.scene === 'lcr' ? 'test frequency' : SP.scene === 'magnet' ? 'coil current' : 'chamber'), 0.22);
  var mtr = instBox(0.28, -0.06, -0.35, SP.meter.title, SP.meter.sub, 0.22);
  ctl.show(fx(st.x), SP.unit); mtr.show('----', SP.meter.unit);
  function fx(x) { return SP.log ? Math.round(Math.pow(10, x)) + '' : x.toFixed(SP.dig); }
  S.wire([[-0.3, 0.14, -0.04], [-0.14, 0.03, 0.04], [-0.04, 0.03, 0.06]], 'red');
  S.wire([[-0.26, 0.14, -0.04], [-0.1, 0.028, 0.08], [0.04, 0.03, 0.06]], 'black');
  S.wire([[-0.3, 0.1, -0.02], [-0.06, 0.026, -0.04], [0.22, 0.03, -0.1]], 'gold');
  S.wire([[-0.28, 0.1, -0.02], [-0.04, 0.024, -0.07], [0.32, 0.03, -0.1]], 'blue');
  S.addApparatus('chamber', chamberG, chamberName, chamberInfo);
  S.addApparatus('sample', sampleG, SP.sample, 'The sample under test. It sits on the tray until you mount it; the hidden property you are measuring is never printed anywhere on the bench.');
  S.addApparatus('ctl', ctl.group, SP.ctlName, 'Sets the one condition that is varied in this experiment. Wait for it to settle before reading the meter.');
  S.addApparatus('mtr', mtr.group, SP.meter.title.charAt(0) + SP.meter.title.slice(1).toLowerCase(), SP.meter.sub + '.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudC = S.hudCard(SP.ctlName), hudR = S.hudCard(SP.meter.title.charAt(0) + SP.meter.title.slice(1).toLowerCase());

  // ================================================================ human actions
  var DONE = { mount: false, on: false, open: false, short: false };
  function mountSample() {
    if (busy() || st.mounted) return Promise.resolve();
    if (SP.scene === 'lcr' && !(st.open && st.short)) { S.say('Compensate the LCR meter first: OPEN, then SHORT.'); return Promise.resolve(); }
    var a = sampleG.position.clone(), b = MOUNT.clone();
    return S.hand.pinchMove(a.clone().add(new T.Vector3(0, 0.01, 0)), function (k) {
      return new T.Vector3(a.x + (b.x - a.x) * k, a.y + 0.07 * Math.sin(Math.PI * k) + (b.y - a.y) * k + 0.01, a.z + (b.z - a.z) * k); },
    function (k) { sampleG.position.set(a.x + (b.x - a.x) * k, a.y + 0.07 * Math.sin(Math.PI * k) + (b.y - a.y) * k, a.z + (b.z - a.z) * k); },
    { mode: 'top', ms: 1300, reachMs: 650 }).then(function () {
      sampleG.position.copy(b); st.mounted = true; DONE.mount = true;
      S.say(SP.scene === 'lcr' ? 'The upper plate is screwed down on the disc until the micrometer just clicks.' : 'The sample is in place.'); S.render(); });
  }
  function switchOn() {
    if (busy() || st.on) return Promise.resolve();
    if (!st.mounted) { S.say('Mount the sample first.'); return Promise.resolve(); }
    return S.hand.tap(mtr.knob, 'front').then(function () { st.on = true; DONE.on = true; S.say(SP.meter.title.charAt(0) + SP.meter.title.slice(1).toLowerCase() + ' is on.'); S.click(880, 0.05); S.render(); });
  }
  function compensate(which) {
    if (busy() || st[which]) return Promise.resolve();
    return S.hand.tap(mtr.knob, 'front').then(function () { st[which] = true; S.say(which === 'open' ? 'OPEN compensation stored: the stray capacitance of the empty fixture is nulled.' : 'SHORT compensation stored: the lead inductance and resistance are nulled.'); S.click(660, 0.05); S.render(); });
  }
  function goTo(xv) {
    if (busy()) return Promise.resolve();
    if (!(xv >= CLO - 1e-9 && xv <= CHI + 1e-9)) { S.say('That is outside this set-up\'s range (' + fx(CLO) + ' to ' + fx(CHI) + ' ' + SP.unit + ').'); return Promise.resolve(); }
    if (!st.on) { S.say('Switch the meter on first.'); return Promise.resolve(); }
    var x0 = st.x; st.settling = true;
    return S.hand.tap(ctl.knob, 'front').then(function () {
      return S.tween(500 + Math.min(1500, 700 * Math.abs(xv - x0) / Math.max(CHI - CLO, 1e-9)), function (k) { st.x = x0 + (xv - x0) * k; });
    }).then(function () { st.x = xv; st.settling = false; S.say('Settled at ' + fx(xv) + ' ' + SP.unit + '. The reading is steady.'); S.render(); });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return null; }
    if (!st.on) { S.say('Switch the meter on first.'); return null; }
    if (st.settling) { S.say('Wait for the reading to settle.'); return null; }
    var key = SP.log ? Math.round(Math.pow(10, st.x) * 100) : Math.round(st.x * 100);
    for (var i = 0; i < S.rows.length; i++) {
      var rr = S.rows[i], k2 = SP.log ? Math.round(rr.f * 100) : Math.round((rr.T !== undefined ? rr.T : rr.dT !== undefined ? rr.dT : rr.B) * 100);
      if (k2 === key) { S.say('You already have a reading at ' + fx(st.x) + ' ' + SP.unit + '.'); return null; } }
    var row = SP.row(st.x, raw());
    S.addRow(row);
    S.say('Written in your record book: ' + SP.cols.map(function (c) { return c[0] + ' ' + c[1](row); }).join(', ') + '.');
    return row;
  }

  // ================================================================ the experiment
  var steps = [
    { id: 'setup', title: SP.setupTitle, view: 'chamber', render: function (u) {
        u.h2(SP.setupTitle);
        u.p('The sample is on its tray in front of the ' + chamberName.toLowerCase() + '. Mount it, then switch the meter on. Sample: ' + SP.sample + '.');
        if (SP.scene === 'lcr') {
          u.task('1. OPEN compensation', st.open, st.open ? 'Stored' : 'Empty fixture, plates apart').add(u.button(st.open ? 'Done' : 'Store OPEN', function () { S.focus('mtr'); compensate('open'); }, !st.open, st.open || S.hand.busy));
          u.task('2. SHORT compensation', st.short, st.short ? 'Stored' : 'Plates shorted').add(u.button(st.short ? 'Done' : 'Store SHORT', function () { S.focus('mtr'); compensate('short'); }, !st.short && st.open, st.short || !st.open || S.hand.busy));
        }
        u.task((SP.scene === 'lcr' ? '3. ' : '1. ') + 'Mount the sample', st.mounted, st.mounted ? 'In place' : 'Still on the tray')
          .add(u.button(st.mounted ? 'Mounted' : 'Mount the sample', function () { S.focus('chamber'); mountSample(); }, !st.mounted && (SP.scene !== 'lcr' || (st.open && st.short)), st.mounted || S.hand.busy || (SP.scene === 'lcr' && !(st.open && st.short))));
        u.task((SP.scene === 'lcr' ? '4. ' : '2. ') + 'Switch the meter on', st.on, st.on ? 'Reading' : 'Off')
          .add(u.button(st.on ? 'Meter is on' : 'Switch it on', function () { S.focus('mtr'); switchOn(); }, !st.on && st.mounted, st.on || !st.mounted || S.hand.busy));
        u.live(function () { return st.on ? SP.meter.title.charAt(0) + SP.meter.title.slice(1).toLowerCase() + ': ' + raw().toFixed(SP.meter.dp) + ' ' + SP.meter.unit : 'Meter off'; });
        u.next('Next: take readings', st.mounted && st.on);
      },
      ok: function () { return st.mounted && st.on; },
      auto: function () {
        var pr = Promise.resolve();
        if (SP.scene === 'lcr') pr = pr.then(function () { return compensate('open'); }).then(function () { return compensate('short'); });
        return pr.then(mountSample).then(switchOn);
      } },
    { id: 'sweep', title: 'Take readings', view: 'mtr', render: function (u) {
        u.h2('Set the condition, wait, read');
        u.p(SP.hint);
        var tg = { v: Math.max(CLO, Math.min(CHI, st.x)) };
        u.slider(SP.ctlName, CLO, CHI, CSTEP, function () { return tg.v; }, function (v) { tg.v = v; }, SP.log ? 'log₁₀ Hz' : SP.unit, SP.log ? 2 : SP.dig);
        u.row(u.button('Set and settle', function () { S.focus('ctl'); goTo(tg.v); }, true, S.hand.busy), u.button('Record the reading', function () { record(); }, false, S.hand.busy));
        u.live(function () { return fx(st.x) + ' ' + SP.unit + '  ·  ' + SP.meter.title.charAt(0) + SP.meter.title.slice(1).toLowerCase() + ' ' + (raw() === null ? '—' : raw().toFixed(SP.meter.dp) + ' ' + SP.meter.unit); });
        u.h3('Observation table'); u.table();
        if (S.rows.length < SP.nmin) u.p(S.rows.length + ' of at least ' + SP.nmin + ' readings taken.');
        u.next('Next: the result', S.rows.length >= SP.nmin);
      },
      ok: function () { return S.rows.length >= SP.nmin; },
      auto: function () {
        if (SP.autoRun) return SP.autoRun({ go: goTo, rec: record });
        return SP.auto().reduce(function (pr, xv) { return pr.then(function () { return goTo(xv); }).then(function () { record(); }); }, Promise.resolve());
      } }
  ];

  var tsym = SP.fnote;
  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { chamber: SP.scene === 'cryo' ? [[-0.3, 0.45, 0.42], [-0.32, 0.2, -0.12]] : [[-0.3, 0.3, 0.38], [-0.32, 0.12, -0.12]], sample: [[-0.12, 0.22, 0.34], [-0.1, 0.03, 0.12]], ctl: [[0.0, 0.26, 0.32], [0.0, 0.05, 0.1]],
      mtr: [[0.3, 0.24, 0.16], [0.28, 0.05, -0.06]], bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: S.lab.theory,
      formula: SP.formula, formulaNote: SP.fnote,
      more: ['Every reading is taken after the condition has settled: a moving temperature or field gives a reading that belongs to no particular value.',
        'The result comes from ALL the readings together (a fitted line or a located feature), never from one pair.',
        'This bench is a simulation of the textbook law; the sample\'s hidden property is the lab\'s own value' + (V_.source ? ', taken from: ' + (V_.source.title || '') : '') + '.'],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title,
      lines: ['Aim: ' + S.lab.aim.slice(0, 110) + (S.lab.aim.length > 110 ? '…' : ''), 'Sample: ' + SP.sample, SP.formula + '.'],
      columns: SP.cols.map(function (c) { return { label: c[0], get: c[1] }; }) },
    graph: { x: SP.graph.x, y: SP.graph.y, xlabel: SP.graph.xlabel, ylabel: SP.graph.ylabel,
      line: function (pts) { if (KNAME === 'msc_super' || KNAME === 'msc_lc' || KNAME === 'msc_curie' || KNAME === 'msc_ferro' || KNAME === 'msc_diel') return null;
        var f = lin(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: SP.result,
    tol: SP.tol,
    resultNote: 'The number came from your readings by the method in the theory, with the lab\'s true value alongside for comparison.',
    chips: ['Why wait for the reading to settle?', 'Explain the formula simply', 'Check my readings', 'What are the sources of error?'],
    viva: [],
    askState: function () {
      var o = { experiment: S.lab.title, sample: SP.sample, mounted: st.mounted, meter_on: st.on, readings_taken: S.rows.length };
      o[SP.ctlName] = fx(st.x) + ' ' + SP.unit; if (st.on && st.mounted) o[SP.meter.title.toLowerCase()] = raw().toFixed(SP.meter.dp) + ' ' + SP.meter.unit; return o;
    },
    steps: steps,
    tick: function () {
      ctl.show(fx(st.x), SP.unit);
      var r = raw(); mtr.show(r === null ? '----' : r.toFixed(SP.meter.dp), SP.meter.unit);
      hudC.set(fx(st.x) + ' ' + SP.unit); hudR.set(r === null ? '—' : r.toFixed(SP.meter.dp) + ' ' + SP.meter.unit);
      tickScene();
    },
  };
});
