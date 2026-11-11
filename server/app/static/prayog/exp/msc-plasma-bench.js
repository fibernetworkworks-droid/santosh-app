/* Prayogshala studio module: GLOW DISCHARGE AND LANGMUIR PROBE.
   A glass discharge tube with an anode, a cathode and a small cylindrical probe wire, a gas inlet, and a source-meter that
   sets the probe voltage and reads the current. The `msc_langmuir` kernel (packs/msc_solid.js) gives I(V): the Bohm ion current
   at the far negative end, the exponential electron-retarding region of slope 1/Te in volts, and electron saturation above
   the plasma potential. The student sweeps the probe voltage, adds the ion current back to get the electron current, plots
   its logarithm and finds Te from the slope; the plasma potential comes from the knee and the density from the electron
   saturation current. The gas (argon, neon, helium or hydrogen) sets the ion mass and the colour of the glow. */
HoolaStudio.define('msc-plasma-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.msc_langmuir, assign = HK.assign;
  var p = HK.paramsFor('msc_langmuir', S.lab.params);
  var V_ = S.lab.variant || {};
  var SAMPLE = V_.sample || 'Argon, violet-blue glow';
  var GAS = /neon/i.test(SAMPLE) ? 'neon' : /helium/i.test(SAMPLE) ? 'helium' : /hydrogen/i.test(SAMPLE) ? 'hydrogen' : 'argon';
  var COL = { argon: 0x8a7cff, neon: 0xff6a2a, helium: 0xffb6dc, hydrogen: 0xe04fc4 }[GAS];
  var QEL = 1.602176634e-19, MEL = 9.1093837015e-31;
  var VLO = -40, VHI = 20;
  var st = { gas: false, lit: false, V: 0, settling: false };
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 24); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }
  function curUA(V) { return Math.round(KN.cur(V, p) * 1e7) / 10; }

  // ================================================================ the tube
  var tubeG = new T.Group(); S.scene.add(tubeG); tubeG.position.set(-0.26, 0.07, -0.15);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.04, transmission: 0.92, thickness: 0.003, transparent: true, opacity: 0.3 });
  var barrel = mk(tubeG, cyl(0.035, 0.035, 0.3, 40), glassM, 0, 0, 0); barrel.rotation.z = Math.PI / 2;
  var glowM = new T.MeshBasicMaterial({ color: COL, transparent: true, opacity: 0, depthWrite: false, blending: T.AdditiveBlending });
  var glow = mk(tubeG, cyl(0.03, 0.03, 0.22, 36), glowM, 0.01, 0, 0); glow.rotation.z = Math.PI / 2;
  mk(tubeG, cyl(0.037, 0.037, 0.012, 40), M.alu, -0.156, 0, 0).rotation.z = Math.PI / 2; mk(tubeG, cyl(0.037, 0.037, 0.012, 40), M.alu, 0.156, 0, 0).rotation.z = Math.PI / 2;
  var anode = mk(tubeG, cyl(0.022, 0.022, 0.003, 30), M.steel, -0.135, 0, 0); anode.rotation.z = Math.PI / 2;
  var cathode = mk(tubeG, cyl(0.024, 0.024, 0.004, 30), M.alu, 0.135, 0, 0); cathode.rotation.z = Math.PI / 2;
  mk(tubeG, cyl(0.0022, 0.0022, 0.05, 8), M.copper, -0.15, 0, 0).rotation.z = Math.PI / 2; mk(tubeG, cyl(0.0022, 0.0022, 0.05, 8), M.copper, 0.16, 0, 0).rotation.z = Math.PI / 2;
  var stemP = mk(tubeG, cyl(0.004, 0.004, 0.07, 10), M.chrome, 0.0, 0.05, 0);
  var tipP = mk(tubeG, cyl(0.0004, 0.0004, 0.02, 8), M.steel, 0.0, 0.0, 0); tipP.rotation.z = Math.PI / 2; tipP.position.set(0.01, 0.0, 0);
  mk(tubeG, cyl(0.0012, 0.0012, 0.03, 8), M.steel, 0.0, 0.016, 0);
  var tl = S.label('DISCHARGE TUBE · ' + GAS.toUpperCase(), { w: 0.16, ratio: 0.09, color: '#e8eaec', bg: '#2b323d' }); tl.position.set(-0.26, 0.0045, -0.1095); S.scene.add(tl);
  var stand = mk(S.scene, box(0.34, 0.008, 0.08), M.bakelite, -0.26, 0.004, -0.15);
  mk(S.scene, box(0.012, 0.05, 0.06), M.wood, -0.41, 0.03, -0.15); mk(S.scene, box(0.012, 0.05, 0.06), M.wood, -0.11, 0.03, -0.15);
  var vlg = new T.Group(); vlg.position.set(-0.11, 0.1, -0.1); S.scene.add(vlg);
  mk(vlg, cyl(0.006, 0.006, 0.05, 12), M.steel, 0, 0, 0); var vkn = mk(vlg, box(0.03, 0.006, 0.008), M.green, 0, 0.03, 0);
  var gasLbl = S.label(GAS.toUpperCase() + ' · NEEDLE VALVE', { w: 0.07, ratio: 0.14, color: '#e8eaec' }); gasLbl.position.set(0, -0.045, 0.012); vlg.add(gasLbl);
  mk(S.scene, cyl(0.018, 0.018, 0.12, 20), new T.MeshStandardMaterial({ color: 0xb8bcc0, roughness: 0.3, metalness: 0.9 }), -0.07, 0.06, -0.06);
  var lamp = new T.PointLight(COL, 0, 0.6); lamp.position.set(-0.26, 0.1, -0.12); S.scene.add(lamp);
  S.contact(0.36, 0.1, -0.26, -0.15, 0.5);

  function instBox(x, z, rotY, title, sub, wdt) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = rotY;
    var W = wdt || 0.2, Dd = 0.15, Hh = 0.08;
    var cse = S.rounded(W, Dd, Hh, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 })); cse.rotation.x = -Math.PI / 2; cse.position.y = Hh / 2 + 0.003; g.add(cse);
    var FZ = Dd / 2 + 0.005, PW = W - 0.012, PH = Hh - 0.012;
    var tex = S.canvasTex(900, Math.round(900 * PH / PW), function (xx, w, h) { xx.fillStyle = '#2b323d'; xx.fillRect(0, 0, w, h); xx.strokeStyle = 'rgba(255,255,255,.12)'; xx.lineWidth = 3; xx.strokeRect(8, 8, w - 16, h - 16);
      xx.fillStyle = '#f1efe8'; xx.font = '700 34px "Public Sans", sans-serif'; xx.fillText(title, 26, 52); xx.font = '500 22px "Public Sans", sans-serif'; xx.fillStyle = '#c7ccd6'; xx.fillText(sub, 26, 88); });
    var fac = S.mesh(box(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]); fac.position.set(0, 0.003 + Hh / 2, FZ - 0.002); g.add(fac);
    var lcdT = S.liveTex(512, 180), last = '';
    var bez = S.mesh(box(PW * 0.52, PH * 0.42, 0.003), M.grey); bez.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.001); g.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(PW * 0.48, PH * 0.38), new T.MeshBasicMaterial({ map: lcdT, toneMapped: false })); scr.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(scr);
    var knobG = new T.Group(); knobG.position.set(-PW * 0.28, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(knobG);
    var kk = S.mesh(cyl(0.012, 0.013, 0.012, 28), M.bakelite); kk.rotation.x = Math.PI / 2; knobG.add(kk);
    var kp = S.mesh(box(0.0018, 0.012, 0.001), M.white, false); kp.position.set(0, 0.007, 0.007); knobG.add(kp);
    S.contact(W + 0.06, Dd + 0.06, x, z, 0.5);
    return { group: g, knob: knobG, show: function (txt, u2) { if (txt + u2 === last) return; last = txt + u2;
      lcdT.draw(function (xx) { var gr = xx.createLinearGradient(0, 0, 0, 180); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); xx.fillStyle = gr; xx.fillRect(0, 0, 512, 180);
        xx.font = '700 ' + (txt.length > 7 ? 70 : 92) + 'px "JetBrains Mono", monospace'; xx.textAlign = 'right'; xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 118); xx.font = '600 34px "Public Sans", sans-serif'; xx.fillText(u2, 496, 150); }); } };
  }
  var hv = instBox(0.0, 0.1, -0.1, 'DISCHARGE SUPPLY', '600 V · current limited · strikes the glow', 0.22);
  var smuV = instBox(0.28, -0.06, -0.35, 'SOURCE-METER · PROBE', 'sets the probe voltage and reads its current', 0.22);
  var smuI = instBox(0.04, -0.26, 0.1, 'PROBE CURRENT', 'autoranging, 0.1 µA', 0.2);
  hv.show('OFF', ''); smuV.show('0.0', 'V'); smuI.show('----', 'µA');
  S.wire([[-0.4, 0.07, -0.15], [-0.2, 0.03, -0.02], [-0.02, 0.03, 0.06]], 'red');
  S.wire([[-0.12, 0.07, -0.15], [-0.04, 0.03, -0.02], [0.04, 0.03, 0.06]], 'black');
  S.wire([[-0.26, 0.12, -0.15], [-0.1, 0.05, -0.1], [0.24, 0.03, -0.1]], 'gold');
  S.addApparatus('tube', tubeG, 'Discharge tube (' + GAS + ')', 'A glass tube with a disc anode and a disc cathode. The gas is at a few pascals; the glow is the gas excited by the electrons crossing the tube.');
  S.addApparatus('probe', stemP, 'Langmuir probe', 'A fine tungsten wire sealed in glass, with only its tip exposed (area ' + (p.Ap * 1e6).toFixed(1) + ' mm²). Its voltage is varied and the current it collects is read.');
  S.addApparatus('valve', vlg, 'Gas needle valve', 'Lets ' + GAS + ' into the tube at a steady rate; the pump behind it holds the pressure at a few pascals.');
  S.addApparatus('hv', hv.group, 'Discharge supply', 'A current-limited high-voltage supply that strikes and sustains the glow.');
  S.addApparatus('smu', smuV.group, 'Source-meter', 'Sets the probe voltage relative to the anode and reads the current it draws.');
  S.addApparatus('smuI', smuI.group, 'Probe current display', 'The current collected by the probe. Electrons count positive.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudV = S.hudCard('Probe voltage'), hudI = S.hudCard('Probe current');

  function openGas() {
    if (busy() || st.gas) return Promise.resolve();
    return S.hand.tap(vkn, 'top').then(function () { st.gas = true; vkn.rotation.y = Math.PI / 2; S.say('The needle valve is open: ' + GAS + ' flows in. The pressure settles at a few pascals.'); S.click(660, 0.05); S.render(); });
  }
  function strike() {
    if (busy() || st.lit) return Promise.resolve();
    if (!st.gas) { S.say('Admit the gas first: a discharge will not strike in a vacuum.'); return Promise.resolve(); }
    return S.hand.tap(hv.knob, 'front').then(function () { st.lit = true; S.say('The discharge strikes: a ' + GAS + ' glow fills the tube.'); S.click(880, 0.05); S.render(); });
  }
  function setV(v) {
    if (busy()) return Promise.resolve();
    if (!(v >= VLO - 1e-9 && v <= VHI + 1e-9)) { S.say('The source-meter sweeps from ' + VLO + ' V to +' + VHI + ' V.'); return Promise.resolve(); }
    if (!st.lit) { S.say('Strike the discharge first.'); return Promise.resolve(); }
    var a = st.V; st.settling = true;
    return S.hand.tap(smuV.knob, 'front').then(function () { return S.tween(300 + 5 * Math.abs(v - a), function (k) { st.V = a + (v - a) * k; }); })
      .then(function () { st.V = v; st.settling = false; S.say('Probe at ' + v.toFixed(1) + ' V: ' + curUA(v).toFixed(1) + ' µA.'); S.render(); });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return null; }
    if (!st.lit) { S.say('Strike the discharge first.'); return null; }
    if (st.settling) { S.say('Wait for the current to settle.'); return null; }
    for (var i = 0; i < S.rows.length; i++) if (Math.abs(S.rows[i].V - st.V) < 1e-6) { S.say('You already have a reading at ' + st.V.toFixed(1) + ' V.'); return null; }
    var row = { V: rnd(st.V, 1), I: curUA(st.V) };
    S.addRow(row); S.say('Written in your record book: ' + row.V.toFixed(1) + ' V, ' + row.I.toFixed(1) + ' µA.');
    return row;
  }
  function analysis(rows) {
    var r = rows.slice().sort(function (a, b) { return a.V - b.V; });
    if (r.length < 10) return null;
    var ion = -Math.min.apply(null, r.map(function (x) { return x.I; })), imax = Math.max.apply(null, r.map(function (x) { return x.I; })) + ion, sel = r.filter(function (x) { return x.I + ion > 0.02 * imax && x.I + ion < 0.5 * imax; });
    if (sel.length < 4) return null;
    var f = S.fit.linear(sel.map(function (x) { return [x.V, Math.log(x.I + ion)]; })); if (!f || f.m <= 0) return null;
    var ies = imax;
    var vp = (Math.log(ies) - f.c) / f.m;                                         // where the exponential reaches the saturation current
    var Te = 1 / f.m, ne = (ies * 1e-6) / (QEL * p.Ap * Math.sqrt(QEL * Te / (2 * Math.PI * MEL)));
    return { Te: Te, ion: ion, ies: ies, vp: vp, ne: ne, n: sel.length };
  }
  function result(rows) {
    var a = analysis(rows); if (!a) return null;
    return { label: 'Electron temperature', value: a.Te, unit: 'eV', digits: 3, truth: p.Te,
      note: 'Ion saturation current ' + a.ion.toFixed(1) + ' µA added back; ln(I_e) against V over ' + a.n + ' points has slope 1/Te. The knee, where that line reaches the saturation current ' + a.ies.toFixed(0) + ' µA, is at V_p ≈ ' + a.vp.toFixed(1) + ' V, and the electron saturation current gives n_e ≈ ' + a.ne.toExponential(1) + ' m⁻³.' };
  }

  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { tube: [[-0.26, 0.25, 0.25], [-0.26, 0.07, -0.15]], probe: [[-0.2, 0.2, 0.0], [-0.26, 0.1, -0.15]], valve: [[-0.1, 0.2, 0.1], [-0.11, 0.1, -0.1]], hv: [[0.0, 0.26, 0.32], [0.0, 0.05, 0.1]], smu: [[0.3, 0.24, 0.16], [0.28, 0.05, -0.06]], smuI: [[0.04, 0.25, 0.3], [0.04, 0.05, -0.26]],
      bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: S.lab.theory,
      formula: 'I_e = I_es exp[(V − V_p) / T_e],   ln I_e = const + V / T_e',
      formulaNote: 'T_e in electron-volts when V is in volts; I_e is the probe current plus the ion saturation current',
      more: ['Far below the plasma potential only the heavy ions reach the probe: the current is flat and small (Bohm ion current).', 'Between the floating potential and the plasma potential the probe repels most electrons; only those with enough energy get in, which gives the exponential.', 'The sweep has to be fast enough that the probe does not become dirty, and slow enough for the current to settle at each step; this simulation settles instantly.'],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 110) + (S.lab.aim.length > 110 ? '…' : ''), 'Gas: ' + GAS + ' (ion mass ' + p.M + ' u). Probe area ' + (p.Ap * 1e6).toFixed(1) + ' mm².', 'Electrons count positive.'],
      columns: [{ label: 'V (V)', get: function (r) { return r.V.toFixed(1); } }, { label: 'I (µA)', get: function (r) { return r.I.toFixed(1); } }] },
    graph: { x: function (r) { return r.V; }, y: function (r) { return r.I; }, xlabel: 'V (V)', ylabel: 'I (µA)', line: function () { return null; } },
    result: result,
    tol: 0.03,
    resultNote: 'Te came from the slope of the logarithm of your electron current, with the lab\'s true value alongside. A real probe reads Te to within the usual 10 to 30 % of the method.',
    chips: ['Why add the ion current back?', 'Where is the plasma potential?', 'Check my readings', 'Why does the gas change the ion current?'],
    viva: [],
    askState: function () { var a = analysis(S.rows); return { experiment: S.lab.title, gas: GAS, gas_open: st.gas, discharge_on: st.lit, probe_voltage_V: rnd(st.V, 1), probe_current_uA: st.lit ? curUA(st.V) : 0, readings_taken: S.rows.length, estimate: a ? { Te_eV: rnd(a.Te, 2), Vp_V: rnd(a.vp, 1) } : 'not enough readings yet' }; },
    steps: [
      { id: 'strike', title: 'Strike the discharge', view: 'tube', render: function (u) {
          u.h2('Admit the gas, strike the discharge');
          u.p('The tube is pumped down. Open the needle valve to let ' + GAS + ' in, then switch the discharge supply on. The glow shows the plasma.');
          u.task('1. Admit the gas', st.gas, st.gas ? 'Gas flowing' : 'Valve closed').add(u.button(st.gas ? 'Gas admitted' : 'Open the needle valve', function () { S.focus('valve'); openGas(); }, !st.gas, st.gas || S.hand.busy));
          u.task('2. Strike the discharge', st.lit, st.lit ? 'Glowing' : 'Off').add(u.button(st.lit ? 'Discharge on' : 'Switch the supply on', function () { S.focus('hv'); strike(); }, !st.lit && st.gas, st.lit || !st.gas || S.hand.busy));
          u.note('The supply is high voltage. Keep the tube cover on and never touch the electrodes.');
          u.next('Next: sweep the probe', st.gas && st.lit);
        },
        ok: function () { return st.gas && st.lit; }, auto: function () { return openGas().then(strike); } },
      { id: 'sweep', title: 'Probe sweep', view: 'smu', render: function (u) {
          u.h2('Sweep the probe voltage');
          u.p('Step the probe voltage from −40 V to +20 V and record the current at each step. Take readings far on each side, and close together between about −10 V and +8 V, where the current rises exponentially.');
          var tg = { v: st.V };
          u.slider('Probe voltage', VLO, VHI, 0.5, function () { return tg.v; }, function (v) { tg.v = v; }, 'V', 1);
          u.row(u.button('Set the voltage', function () { S.focus('smu'); setV(tg.v); }, true, S.hand.busy), u.button('Record the current', function () { S.focus('smuI'); record(); }, false, S.hand.busy));
          u.live(function () { return st.lit ? st.V.toFixed(1) + ' V  ·  ' + curUA(st.V).toFixed(1) + ' µA' : 'Discharge off'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 10) u.p(S.rows.length + ' of at least 10 readings taken.');
          u.next('Next: the result', S.rows.length >= 10);
        },
        ok: function () { return S.rows.length >= 10; },
        auto: function () { return [-40, -30, -20, -14, -10, -7, -5, -3, -1, 1, 3, 5, 7, 9, 12, 16, 20].reduce(function (pr, v) { return pr.then(function () { return setV(v); }).then(function () { record(); }); }, Promise.resolve()); } }
    ],
    tick: function () {
      hv.show(st.lit ? '600' : 'OFF', st.lit ? 'V' : ''); smuV.show(st.V.toFixed(1), 'V'); smuI.show(st.lit ? curUA(st.V).toFixed(1) : '----', 'µA');
      glowM.opacity = st.lit ? 0.5 : 0; lamp.intensity = st.lit ? 0.35 : 0;
      hudV.set(st.V.toFixed(1) + ' V'); hudI.set(st.lit ? curUA(st.V).toFixed(1) + ' µA' : '—');
    },
  };
});
