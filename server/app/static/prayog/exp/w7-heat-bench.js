/* Prayogshala studio rig: the B.Sc. heat bench (pack ug_mech_w7). Five set-ups share the bench, the digital meters,
   the data logger and the record book:
     w7_stefan    a vacuum tungsten lamp on a variable supply: V and I give the filament's R, T and radiated power
     w7_cbarnes   Callendar and Barnes' constant-flow tube: steady rise of the water for two rates of flow
     w7_angstrom  Angstrom's bar: a periodic heater, two thermocouples and a two-channel logger
     w7_cool      the method of cooling: water and a liquid in twin calorimeters inside one enclosure
     cooling      a hot block, a thermocouple and a data logger (Newton's law of cooling; the shipped kernel)
   Every number comes from the lab's kernel and params. The hidden knob (Stefan's constant, J, the diffusivity, the
   liquid's specific heat, the cooling constant) is what the student measures. */
HoolaStudio.define('w7-heat-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = S.lab.kernel, K = HK.K[KN], PI = Math.PI;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams(KN);
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var st = { dims: false, speed: 1, on: false };
  var ZB = -0.36;

  function cyl(r, h, mat, seg) { return S.mesh(new T.CylinderGeometry(r, r, h, seg || 24), mat); }
  function box(w, h, d, mat) { return S.mesh(new T.BoxGeometry(w, h, d), mat); }
  function put(o, x, y, z, parent) { o.position.set(x, y, z); (parent || S.scene).add(o); return o; }
  function rnd(v, lc) { return Math.round(v / lc) * lc; }
  function mean(xs) { return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : NaN; }
  function post(x, z, h) { var g = new T.Group(); S.scene.add(g); var b = S.rounded(0.09, 0.07, 0.016, 0.006, M.iron); b.rotation.x = -PI / 2; b.position.set(x, 0.008, z); g.add(b);
    var r = cyl(0.005, h, M.chrome); r.position.set(x, h / 2 + 0.012, z); g.add(r); var c = box(0.03, 0.022, 0.03, M.alu); c.position.set(x, h, z); g.add(c); S.contact(0.14, 0.11, x, z, 0.45); return g; }
  function hose(pts, r, col) { var m = S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts.map(function (a) { return new T.Vector3(a[0], a[1], a[2]); })), 40, r, 8, false), new T.MeshStandardMaterial({ color: col || 0x8a3b2a, roughness: 0.7 }), true, false); S.scene.add(m); return m; }
  // a bench digital meter: a case with a liquid-crystal display the code writes on
  function dmm(pos, title, col) {
    var g = new T.Group(); S.scene.add(g); var b = S.rounded(0.12, 0.07, 0.07, 0.008, new T.MeshStandardMaterial({ color: col || 0xd9a520, roughness: 0.5 })); b.position.y = 0.035; g.add(b);
    var tex = S.liveTex(384, 128), last = null;
    var scr = new T.Mesh(new T.PlaneGeometry(0.094, 0.031), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); scr.position.set(0, 0.045, 0.0355); g.add(scr);
    var l = S.label(title, { w: 0.09, ratio: 0.18, color: '#1b1b1b' }); l.position.set(0, 0.017, 0.0356); g.add(l);
    g.position.set(pos[0], 0, pos[2]); S.contact(0.17, 0.12, pos[0], pos[2], 0.5);
    g.set = function (txt) { if (txt === last) return; last = txt; tex.draw(function (x) { x.fillStyle = '#b9c4a7'; x.fillRect(0, 0, 384, 128); x.fillStyle = '#1b2116'; x.font = '700 76px "JetBrains Mono", monospace'; x.textAlign = 'right'; x.fillText(txt, 368, 92); }); };
    g.set('—'); return g; }
  // a data logger: a box with a screen that plots the traces it is given
  function logger(pos, title) {
    var g = new T.Group(); S.scene.add(g); var b = S.rounded(0.26, 0.18, 0.1, 0.01, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 })); b.position.y = 0.09; g.add(b);
    var tex = S.liveTex(512, 320), frames = 0;
    var scr = new T.Mesh(new T.PlaneGeometry(0.22, 0.1375), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); scr.position.set(0, 0.098, 0.0505); g.add(scr);
    var l = S.label(title, { w: 0.16, ratio: 0.14, color: '#e6e7ea' }); l.position.set(0, 0.017, 0.0506); g.add(l);
    g.position.set(pos[0], 0, pos[2]); S.contact(0.32, 0.16, pos[0], pos[2], 0.5);
    g.plot = function (traces, lo, hi, tspan, text, force) {     // traces: [{pts: [[t, v]...], color}], time axis ends at the newest point
      if (S.fast && !force) return; if (!force && (frames++ % 12)) return;
      tex.draw(function (x) { x.fillStyle = '#0d1b14'; x.fillRect(0, 0, 512, 320); x.strokeStyle = 'rgba(120,200,150,.25)'; x.lineWidth = 1;
        for (var i = 1; i < 8; i++) { x.beginPath(); x.moveTo(i * 64, 0); x.lineTo(i * 64, 320); x.stroke(); } for (i = 1; i < 5; i++) { x.beginPath(); x.moveTo(0, i * 64); x.lineTo(512, i * 64); x.stroke(); }
        var tend = 0; traces.forEach(function (tr) { if (tr.pts.length) tend = Math.max(tend, tr.pts[tr.pts.length - 1][0]); });
        traces.forEach(function (tr) { x.strokeStyle = tr.color; x.lineWidth = 3; x.beginPath(); var started = false;
          tr.pts.forEach(function (q) { var px = 512 - (tend - q[0]) / tspan * 512, py = 300 - (q[1] - lo) / (hi - lo) * 280; if (px < 0) return; if (!started) { x.moveTo(px, py); started = true; } else x.lineTo(px, py); }); x.stroke(); });
        x.fillStyle = '#d7f5e2'; x.font = '600 26px "JetBrains Mono", monospace'; x.textAlign = 'left'; x.fillText(text || '', 12, 30); }); };
    g.plot([], 0, 1, 1, 'READY', true); return g; }
  function speedRow(u, list) { var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: ')); list.forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { st.speed = v; S.render(); }, false, false)); }); }
  function tap(obj) { return S.hand.busy ? Promise.resolve() : S.hand.tap(obj); }
  var COL_NO = { label: 'S.No', get: function (r, i) { return i + 1; } };
  function col(l, f) { return { label: l, get: f }; }
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  function measure(text) { if (st.dims) return; st.dims = true; S.say(text + ' Written in your record book.'); S.book.draw(); S.render(); }
  function setupStep(E, title, intro, taskTitle, hint) { return { id: 'setup', title: 'Set up', view: 'main', render: function (u) { u.h2(title); u.p(intro);
      u.task(taskTitle, st.dims, st.dims ? E.dims : hint).add(u.button(st.dims ? 'Noted' : 'Measure and note', function () { measure(E.dims); }, !st.dims, st.dims));
      if (SAMPLE) u.note('Sample: ' + SAMPLE + '.'); u.next('Next: take the readings', st.dims); },
    ok: function () { return st.dims; }, auto: function () { measure(E.dims); return Promise.resolve(); } }; }

  // ================================================================== Stefan's law: a tungsten lamp
  function stefan() {
    var sim = K.init(p), Vset = p.V, lit = false, last = null;
    var sup = S.powerBox([-0.15, 0, ZB], 'DC SUPPLY 0–12 V'), am = dmm([0.15, 0, ZB + 0.02], 'AMMETER  A'), vm = dmm([0.5, 0, ZB - 0.2], 'VOLTMETER  V', 0xc2523a);
    var LX = 0.5, LZ = ZB + 0.06; var blk = S.rounded(0.1, 0.09, 0.02, 0.006, M.darkWood); blk.rotation.x = -PI / 2; blk.position.set(LX, 0.01, LZ); S.scene.add(blk); S.contact(0.15, 0.13, LX, LZ, 0.5);
    var hold = cyl(0.016, 0.03, M.bakelite); put(hold, LX, 0.035, LZ); var cap = cyl(0.011, 0.016, M.brass); put(cap, LX, 0.058, LZ);
    var bulb = S.mesh(new T.SphereGeometry(0.027, 40, 28), M.glass, false); put(bulb, LX, 0.094, LZ);
    var filM = new T.MeshBasicMaterial({ color: 0x3a2a22 }); var fil = S.mesh(new T.TorusGeometry(0.006, 0.0009, 8, 24, PI), filM, false, false); put(fil, LX, 0.09, LZ);
    [-0.006, 0.006].forEach(function (dx) { var lead = cyl(0.0005, 0.024, M.steel, 6); put(lead, LX + dx, 0.078, LZ); });
    var glow = new T.PointLight(0xffb060, 0, 0.6, 2); glow.position.set(LX, 0.094, LZ); S.scene.add(glow);
    var t1 = S.terminal([LX - 0.03, 0.02, LZ + 0.03], 'red'), t2 = S.terminal([LX + 0.03, 0.02, LZ + 0.03], 'black');
    S.wire([[-0.11, 0.1, ZB], [0.11, 0.06, ZB + 0.06]], 'red'); S.wire([[0.19, 0.06, ZB + 0.06], [LX - 0.03, 0.03, LZ + 0.03]], 'red'); S.wire([[LX + 0.03, 0.03, LZ + 0.03], [0.3, 0.01, ZB + 0.16], [-0.19, 0.1, ZB]], 'black');
    S.wire([[LX - 0.03, 0.03, LZ + 0.03], [LX - 0.06, 0.02, LZ - 0.1], [LX - 0.03, 0.05, ZB - 0.16]], 'yellow'); S.wire([[LX + 0.03, 0.03, LZ + 0.03], [LX + 0.07, 0.02, LZ - 0.1], [LX + 0.03, 0.05, ZB - 0.16]], 'blue');
    S.addApparatus('lamp', bulb, 'Vacuum tungsten lamp', 'A 12 V lamp with a straight-coil tungsten filament in vacuum: it loses heat by radiation only. Filament area A = ' + (p.A * 1e6).toFixed(1) + ' mm², emissivity ' + p.em.toFixed(2) + ' (data card).');
    S.addApparatus('sup', sup, 'Variable DC supply', 'Turn its knob to set the lamp voltage.');
    S.addApparatus('am', am, 'Digital ammeter', 'In series with the lamp. Reads to 1 mA.');
    S.addApparatus('vm', vm, 'Digital voltmeter', 'Across the lamp. Reads to 0.01 V.');
    function calc(r) { var R = r.V / r.I, Tm = p.T0 * Math.pow(R / p.R0, 1 / p.nR), P = r.V * r.I; return { R: R, T: Tm, P: P, sig: P / (p.em * p.A * (Math.pow(Tm, 4) - Math.pow(p.T0, 4))) }; }
    function setV() { if (S.hand.busy) return Promise.resolve(); return tap(sup.userData.knob).then(function () { p.V = Vset; lit = true; last = null; S.click(1800); S.say('Lamp at ' + p.V.toFixed(2) + ' V. Let the filament settle, then read the meters.'); S.render(); }); }
    function read() { if (!lit) { S.say('Set a voltage on the supply first.'); return; } if (S.rows.some(function (r) { return Math.abs(r.V - p.V) < 1e-9; })) { S.say('You already have a reading at this voltage. Change the voltage.'); return; }
      var v = K.view(sim, p); S.addRow({ V: rnd(p.V, 0.01), I: rnd(v.I, 0.001) }); S.say('V = ' + p.V.toFixed(2) + ' V, I = ' + v.I.toFixed(3) + ' A. Written in the table.'); }
    var E = { name: 'Stefan\'s law', dims: 'Room temperature T0 = ' + p.T0.toFixed(0) + ' K. Cold resistance of the lamp R0 = ' + p.R0.toFixed(3) + ' Ω (bridge, very small current). Filament: A = ' + (p.A * 1e6).toFixed(1) + ' mm², emissivity e = ' + p.em.toFixed(2) + '.',
      camera: { pos: [0.35, 0.5, 0.85], look: [0.2, 0.05, ZB] },
      views: { main: [[0.3, 0.45, 0.7], [0.2, 0.05, ZB]], lamp: [[LX + 0.1, 0.2, 0.05], [LX, 0.08, LZ]], sup: [[-0.1, 0.3, 0.1], [-0.15, 0.06, ZB]], am: [[0.2, 0.25, 0.05], [0.15, 0.04, ZB]], vm: [[LX + 0.1, 0.3, 0.0], [0.5, 0.04, ZB - 0.2]] },
      formula: 'V I = e σ A (T⁴ − T0⁴)', formulaNote: 'T = T0 (R / R0)^(1/1.2) with R = V / I. The slope of log P against log T is the exponent of T.',
      book: ['Aim: to verify Stefan\'s law and find σ with a tungsten lamp.', 'T0 = ' + p.T0.toFixed(0) + ' K,  R0 = ' + p.R0.toFixed(3) + ' Ω,  A = ' + (p.A * 1e6).toFixed(1) + ' mm²,  e = ' + p.em.toFixed(2), 'R = V/I,  T = T0 (R/R0)^(1/1.2),  P = V I', 'σ = P / (e A (T⁴ − T0⁴))'],
      columns: [COL_NO, col('V (V)', function (r) { return r.V.toFixed(2); }), col('I (A)', function (r) { return r.I.toFixed(3); }), col('R (Ω)', function (r) { return calc(r).R.toFixed(2); }), col('T (K)', function (r) { return calc(r).T.toFixed(0); }), col('P (W)', function (r) { return calc(r).P.toFixed(2); })],
      graph: { x: function (r) { return Math.log10(calc(r).T); }, y: function (r) { return Math.log10(calc(r).P); }, xlabel: 'log T', ylabel: 'log P', line: function (pts) { var f = S.fit.linear(pts); return function (x) { return f.m * x + f.c; }; } },
      result: function (rows) { if (rows.length < 3) return null; var f = S.fit.linear(rows.map(function (r) { var c = calc(r); return [Math.log(c.T), Math.log(c.P)]; }));
        return { label: 'σ (Stefan\'s constant)', value: mean(rows.map(function (r) { return calc(r).sig; })) * 1e8, unit: '×10⁻⁸ W/(m²·K⁴)', digits: 3, truth: p.sigma * 1e8, note: 'Exponent of T from the slope of log P against log T: ' + (f ? f.m.toFixed(2) : '—') + ' (Stefan\'s law: 4).' }; },
      tol: 0.03, chips: ['Why is the lamp evacuated?', 'How is the filament temperature found?', 'Check my readings', 'Why is my exponent not exactly 4?'],
      viva: [['The slope of log P against log T should be', ['4', '2', '1'], 0, 'Stefan\'s law: the power radiated is proportional to T⁴.']],
      askState: function () { var v = K.view(sim, p); return { lamp_lit: lit, lamp_voltage_V: lit ? +p.V.toFixed(2) : 0, lamp_current_A: lit ? +v.I.toFixed(3) : 0, readings: S.rows.length }; },
      tick: function () { var v = K.view(sim, p); am.set(lit ? v.I.toFixed(3) : '0.000'); vm.set(lit ? p.V.toFixed(2) : '0.00');
        var f = lit ? Math.max(0, Math.min(1, (v.T - 900) / 1800)) : 0; filM.color.setRGB(0.23 + 0.77 * f, 0.16 + 0.75 * f * f, 0.13 + 0.6 * f * f * f); glow.intensity = lit ? 0.4 * f : 0;
        hud1.set(lit ? p.V.toFixed(2) + ' V' : 'off'); hud2.set(lit ? v.I.toFixed(3) + ' A' : '—'); } };
    var hud1 = S.hudCard('Voltmeter'), hud2 = S.hudCard('Ammeter');
    E.steps = [setupStep(E, 'Note the lamp\'s data', 'The filament temperature will come from its resistance, so its cold resistance and the room temperature are needed first.', 'Room temperature, cold resistance, lamp data', 'Thermometer, bridge and the lamp\'s data card'),
      { id: 'read', title: 'Readings', view: 'main', render: function (u) { u.h2('Raise the voltage in steps');
          u.slider('Supply voltage', 2, 12, 0.5, function () { return Vset; }, function (v) { Vset = v; }, 'V');
          u.row(u.button('Turn the knob to this voltage', function () { setV(); }, true, S.hand.busy), u.button('Read V and I', read, false, !lit));
          u.live(function () { var v = K.view(sim, p); return lit ? 'V = ' + p.V.toFixed(2) + ' V · I = ' + v.I.toFixed(3) + ' A' : 'Lamp off'; });
          u.h3('Observation table'); u.table(); if (S.rows.length < 5) u.p(S.rows.length + ' of at least 5 voltages read.'); u.next('Next: work out σ', S.rows.length >= 5); },
        ok: function () { return S.rows.length >= 5; },
        auto: function () { return [4, 6, 8, 10, 12].reduce(function (pr, v) { return pr.then(function () { Vset = v; return setV(); }).then(function () { read(); }); }, Promise.resolve()); } }];
    return E;
  }

  // ================================================================== Callendar and Barnes
  function cbarnes() {
    var sim = K.init(p), flowSet = p.mdot, Vset = p.V, collected = 0;
    var TY = 0.24, XL = -0.32, XR = 0.38;
    post(XL + 0.08, ZB - 0.06, TY); post(XR - 0.08, ZB - 0.06, TY);
    var jacket = S.mesh(new T.CylinderGeometry(0.024, 0.024, XR - XL - 0.06, 32, 1, true), M.glass, false); jacket.rotation.z = PI / 2; put(jacket, (XL + XR) / 2, TY, ZB);
    var inner = S.mesh(new T.CylinderGeometry(0.008, 0.008, XR - XL, 20, 1, true), M.glass, false); inner.rotation.z = PI / 2; put(inner, (XL + XR) / 2, TY, ZB);
    var water = cyl(0.0068, XR - XL, new T.MeshStandardMaterial({ color: 0x6fb6de, transparent: true, opacity: 0.55, roughness: 0.2 }), 16); water.rotation.z = PI / 2; put(water, (XL + XR) / 2, TY, ZB);
    var wireM = new T.MeshStandardMaterial({ color: 0xc8764a, roughness: 0.3, metalness: 1, emissive: 0x000000 }); var hw = cyl(0.0012, XR - XL - 0.02, wireM, 8); hw.rotation.z = PI / 2; put(hw, (XL + XR) / 2, TY, ZB);
    [XL + 0.03, XR - 0.03].forEach(function (x) { var bung = cyl(0.025, 0.014, M.rubber); bung.rotation.z = PI / 2; put(bung, x, TY, ZB); });
    var thA = S.thermometer({ len: 0.24, min: 15, max: 45, value: p.Tin, pos: [XL + 0.005, TY - 0.004, ZB] }), thB = S.thermometer({ len: 0.24, min: 15, max: 45, value: p.Tin, pos: [XR - 0.005, TY - 0.004, ZB] });
    var tankBlock = S.rounded(0.16, 0.16, 0.3, 0.008, M.wood); tankBlock.position.set(-0.72, 0.15, ZB); S.scene.add(tankBlock); S.contact(0.22, 0.22, -0.72, ZB, 0.55);
    var tank = S.beaker(0.06, 0.12, [-0.72, 0.3, ZB], 0x6fb6de, 0.8);
    hose([[-0.67, 0.31, ZB], [-0.56, 0.2, ZB + 0.03], [XL - 0.06, TY - 0.03, ZB], [XL, TY, ZB]], 0.005);
    var valve = cyl(0.011, 0.012, M.red); valve.rotation.x = PI / 2; put(valve, -0.56, 0.2, ZB + 0.04);
    hose([[XR, TY, ZB], [XR + 0.08, TY - 0.02, ZB], [XR + 0.16, 0.14, ZB + 0.02]], 0.005);
    var jar = S.beaker(0.045, 0.1, [XR + 0.17, 0, ZB + 0.03], 0x6fb6de, 0.02); S.contact(0.13, 0.13, XR + 0.17, ZB + 0.03, 0.5);
    var sup = S.powerBox([-0.06, 0, -0.02], 'HEATER SUPPLY'), am = dmm([0.16, 0, 0.0], 'AMMETER  A'), vm = dmm([0.34, 0, 0.0], 'VOLTMETER  V', 0xc2523a), dtm = dmm([0.56, 0, -0.02], 'ΔT  K (Pt pair)', 0x5a8f6a);
    S.wire([[-0.02, 0.1, -0.02], [-0.1, 0.02, -0.14], [XL + 0.03, TY - 0.03, ZB + 0.02]], 'red'); S.wire([[-0.1, 0.1, -0.02], [0.3, 0.02, -0.18], [XR - 0.03, TY - 0.03, ZB + 0.02]], 'black');
    var watch = S.stopwatch([0.78, 0.035, 0.1], [-1.15, 0, -0.3]);
    S.addApparatus('tube', jacket, 'Flow tube in a vacuum jacket', 'Water runs through the narrow inner tube along the heater wire. The evacuated glass jacket keeps the heat loss small.');
    S.addApparatus('tank', tank, 'Constant-head tank', 'Keeps the pressure, and so the rate of flow, steady. The red tap sets the flow.');
    S.addApparatus('jar', jar, 'Collecting beaker', 'The water that flows out in a timed interval is collected here and weighed.');
    S.addApparatus('th', thB, 'Inlet and outlet thermometers', 'A pair of platinum thermometers at the two ends gives the rise Δθ directly to 0.01 K on the green meter.');
    S.addApparatus('sup', sup, 'Heater supply and meters', 'The supply drives the heater wire (' + p.Rh.toFixed(1) + ' Ω); the meters read V and I.');
    S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Times the collection of the water.');
    function steady() { return st.on && Math.abs(sim.dT - K.steady(p, p.V, p.mdot)) < 0.002; }
    function apply() { if (S.hand.busy) return Promise.resolve(); return tap(valve).then(function () { return tap(sup.userData.knob); }).then(function () { p.mdot = flowSet; p.V = Vset; st.on = true; S.click(1800); S.say('Flow ' + p.mdot.toFixed(2) + ' g/s, heater at ' + p.V.toFixed(2) + ' V. Wait for the steady state.'); S.render(); }); }
    function waitSteady() { if (!st.on) { S.say('Start the water and the heater first.'); return; } K.step(sim, p, 12 * p.tau); S.render(); }
    function collect() { if (!steady()) { S.say('The readings are still changing. Wait for the steady state.'); return; }
      K.step(sim, p, 60); collected = Math.min(1, collected + p.mdot * 60 / 400); jar.setLevel(collected); watch.t = 60;
      var r = { m: rnd(p.mdot * 60, 0.1), t: 60, V: rnd(p.V, 0.01), I: rnd(p.V / p.Rh, 0.001), dT: rnd(sim.dT, 0.01) }; S.addRow(r); S.say('Collected ' + r.m.toFixed(1) + ' g in 60 s. V = ' + r.V.toFixed(2) + ' V, I = ' + r.I.toFixed(3) + ' A, Δθ = ' + r.dT.toFixed(2) + ' K.'); }
    function pair(rows) { for (var i = 0; i < rows.length; i++) for (var j = i + 1; j < rows.length; j++) if (Math.abs(rows[i].m - rows[j].m) > 5 && Math.abs(rows[i].dT - rows[j].dT) <= 0.03) return [rows[i], rows[j]]; return null; }
    function need(rows) { if (rows.length < 2) return 'Take a run at each of two rates of flow.'; return pair(rows) ? '' : 'The two runs must have the same rise Δθ (within 0.03 K) and different flows. Adjust the voltage and take the second run again.'; }
    var hud1 = S.hudCard('Rise Δθ'), hud2 = S.hudCard('Heater'), hud3 = S.hudCard('State');
    var E = { name: 'Callendar and Barnes', dims: 'Specific heat of water s = ' + p.s.toFixed(1) + ' cal/(g K). Heater wire about ' + p.Rh.toFixed(1) + ' Ω. Inlet water at ' + p.Tin.toFixed(1) + ' °C. The beaker is weighed empty.',
      camera: { pos: [0.02, 0.68, 1.55], look: [0.0, 0.12, ZB + 0.1] },
      views: { main: [[0.02, 0.65, 1.5], [0.0, 0.12, ZB + 0.1]], tube: [[0.1, 0.4, 0.3], [0.03, TY, ZB]], tank: [[-0.5, 0.5, 0.3], [-0.72, 0.3, ZB]], jar: [[XR + 0.3, 0.3, 0.15], [XR + 0.17, 0.05, ZB]], th: [[XR + 0.1, 0.45, 0.1], [XR, 0.35, ZB]],
        sup: [[0.2, 0.35, 0.5], [0.2, 0.04, -0.02]], sw: [[0.8, 0.3, 0.5], [0.78, 0.03, 0.1]] },
      formula: 'J = (V1 I1 − V2 I2) t / ((m1 − m2) s Δθ)', formulaNote: 'Two rates of flow with the same rise Δθ: the heat loss is the same in both and cancels.',
      book: ['Aim: J by Callendar and Barnes\' constant-flow method.', 's = ' + p.s.toFixed(1) + ' cal/(g K),  t = 60 s for each run', 'V I t = J (m s Δθ + h)', 'J = (V1I1 − V2I2) t / ((m1 − m2) s Δθ)'],
      columns: [COL_NO, col('m (g)', function (r) { return r.m.toFixed(1); }), col('t (s)', function (r) { return String(r.t); }), col('V (V)', function (r) { return r.V.toFixed(2); }), col('I (A)', function (r) { return r.I.toFixed(3); }), col('Δθ (K)', function (r) { return r.dT.toFixed(2); })],
      result: function (rows) { var q = pair(rows); if (!q) return null; var a = q[0], b = q[1], dT = (a.dT + b.dT) / 2, J = (a.V * a.I - b.V * b.I) * a.t / ((a.m - b.m) * p.s * dT);
        return { label: 'J (mechanical equivalent of heat)', value: J, unit: 'J/cal', digits: 3, truth: p.J, note: 'From the runs with ' + a.m.toFixed(1) + ' g and ' + b.m.toFixed(1) + ' g in 60 s, both with Δθ = ' + dT.toFixed(2) + ' K. A single run, ignoring the loss, would give ' + (a.V * a.I * a.t / (a.m * p.s * a.dT)).toFixed(2) + ' J/cal.' }; },
      tol: 0.03, chips: ['Why two rates of flow?', 'Why keep Δθ the same?', 'Check my readings', 'Why is my J different?'],
      viva: [['In the steady state the heat capacity of the tube', ['does not matter', 'must be added to the water', 'doubles the loss'], 0, 'Nothing in the apparatus is changing temperature, so it takes in no heat.']],
      askState: function () { return { water_and_heater_on: st.on, flow_g_per_s: +p.mdot.toFixed(2), heater_V: +p.V.toFixed(2), heater_I_A: +(p.V / p.Rh).toFixed(3), rise_K: +sim.dT.toFixed(2), steady: steady(), runs: S.rows.length, still_needed: need(S.rows) || 'nothing' }; },
      tick: function (dt) { if (st.on) K.step(sim, p, dt * st.speed); thA.set(p.Tin); thB.set(p.Tin + sim.dT); am.set(st.on ? (p.V / p.Rh).toFixed(3) : '0.000'); vm.set(st.on ? p.V.toFixed(2) : '0.00'); dtm.set(sim.dT.toFixed(2));
        hud1.set(sim.dT.toFixed(2) + ' K'); hud2.set(st.on ? p.V.toFixed(2) + ' V · ' + (p.V / p.Rh).toFixed(3) + ' A' : 'off'); hud3.set(!st.on ? 'off' : steady() ? 'STEADY' : 'changing'); } };
    E.steps = [setupStep(E, 'Get the apparatus ready', 'Fill the constant-head tank, check that water runs through the tube with no air bubbles, and weigh the empty beaker.', 'Note the constants', 'Balance, thermometer'),
      { id: 'runs', title: 'Two runs', view: 'main', render: function (u) { u.h2('Two rates of flow, the same rise');
          u.slider('Rate of flow (tap)', 0.6, 2.0, 0.1, function () { return flowSet; }, function (v) { flowSet = v; }, 'g/s');
          u.slider('Heater voltage', 3, 9, 0.01, function () { return Vset; }, function (v) { Vset = v; }, 'V');
          u.row(u.button('Set the tap and the supply', function () { apply(); }, true, S.hand.busy), u.button('Wait for the steady state', waitSteady, false, !st.on), u.button('Collect water for 60 s and record', collect, false, !st.on));
          speedRow(u, [1, 10, 30]);
          u.live(function () { return 'Δθ = ' + sim.dT.toFixed(2) + ' K · ' + (!st.on ? 'off' : steady() ? 'STEADY' : 'still changing'); });
          if (S.rows.length) u.note('For the second run change the flow, then adjust the voltage until Δθ again reads ' + S.rows[0].dT.toFixed(2) + ' K.');
          u.h3('Observation table'); u.table(); var nd = need(S.rows); if (nd) u.p(nd); u.next('Next: work out J', !nd); },
        ok: function () { return !need(S.rows); },
        auto: function () { flowSet = 1.5; Vset = 6.0;
          return apply().then(function () { waitSteady(); collect(); var target = S.rows[0].dT, lo = 3, hi = 9, i = 0;
            function tryV() { flowSet = 0.9; Vset = Math.round((lo + hi) / 2 * 100) / 100; return apply().then(function () { waitSteady(); var d = rnd(sim.dT, 0.01);
              if (Math.abs(d - target) <= 0.01 || ++i > 14) { collect(); return null; } if (d < target) lo = Vset; else hi = Vset; return tryV(); }); }
            return tryV(); }); } }];
    return E;
  }

  // ================================================================== Angstrom's method
  function angstrom() {
    var sim = K.init(p), tauSet = p.tau, log = null, buf1 = [], buf2 = [], nextSample = 0;
    var BY = 0.16, X0 = -0.45, LEN = 0.6;
    post(X0 + 0.12, ZB - 0.05, BY - 0.012); post(X0 + LEN - 0.06, ZB - 0.05, BY - 0.012);
    var bar = cyl(0.011, LEN, M.copper, 32); bar.rotation.z = PI / 2; put(bar, X0 + LEN / 2, BY, ZB);
    var htM = new T.MeshStandardMaterial({ color: 0x3a3a3c, roughness: 0.6, emissive: 0x000000 }); var heater = cyl(0.02, 0.07, htM, 28); heater.rotation.z = PI / 2; put(heater, X0 + 0.02, BY, ZB);
    for (var i = 0; i < 5; i++) { var rg = S.mesh(new T.TorusGeometry(0.0205, 0.0012, 6, 24), M.copper); rg.rotation.y = PI / 2; put(rg, X0 - 0.008 + i * 0.014, BY, ZB); }
    var lag = S.mesh(new T.CylinderGeometry(0.019, 0.019, LEN - 0.1, 28, 1, true, 0.6, PI * 1.6), new T.MeshStandardMaterial({ color: 0xd9d2c0, roughness: 0.95, side: T.DoubleSide })); lag.rotation.z = PI / 2; put(lag, X0 + LEN / 2 + 0.04, BY, ZB);
    var XH = X0 + 0.055, xs = [XH + p.x1, XH + p.x2];
    var lg = logger([0.55, 0, ZB + 0.02], 'TWO-CHANNEL TEMPERATURE LOGGER');
    xs.forEach(function (x, j) { var jn = cyl(0.002, 0.02, M.steel, 8); put(jn, x, BY + 0.018, ZB); S.wire([[x, BY + 0.028, ZB], [x + 0.1, 0.3, ZB + 0.05], [0.45 + j * 0.04, 0.19, ZB + 0.02]], j ? 'blue' : 'yellow'); });
    var ctl = S.powerBox([-0.78, 0, ZB + 0.06], 'PERIODIC HEATER'); S.wire([[-0.74, 0.1, ZB + 0.06], [X0 - 0.1, 0.05, ZB + 0.08], [X0 + 0.02, BY - 0.02, ZB + 0.01]], 'red');
    var ruler = S.ruler(0.3, { title: 'cm', labelEvery: 10 }), rg2 = new T.Group(); S.scene.add(rg2); rg2.add(ruler); ruler.rotation.z = PI / 2; rg2.rotation.x = -PI / 2; rg2.position.set(XH + 0.3, 0.004, ZB + 0.09); S.contact(0.34, 0.06, XH + 0.15, ZB + 0.09, 0.4);
    S.addApparatus('bar', bar, 'Copper bar', 'A long copper rod, lagged along its length. The heater at the left end is switched on and off with the chosen period.');
    S.addApparatus('heater', heater, 'Heater coil', 'On for half of each period and off for the other half, so a temperature wave runs down the bar.');
    S.addApparatus('lg', lg, 'Two-channel temperature logger', 'Records the two thermocouples: yellow at ' + (p.x1 * 100).toFixed(1) + ' cm and blue at ' + (p.x2 * 100).toFixed(1) + ' cm from the heater.');
    S.addApparatus('ctl', ctl, 'Periodic heater supply', 'A timer switches the heater with the period you set.');
    function setTau() { if (log) { S.say('Wait for the record to finish.'); return Promise.resolve(); } if (S.hand.busy) return Promise.resolve();
      return tap(ctl.userData.knob).then(function () { p.tau = tauSet; sim = K.init(p); buf1 = []; buf2 = []; nextSample = 0; st.on = true; S.click(1800); S.say('Heater period ' + p.tau.toFixed(0) + ' s. Let a few periods pass, then record one full period.'); S.render(); }); }
    function record() { if (!st.on) { S.say('Switch the periodic heater on first.'); return; } if (log) return; if (S.rows.some(function (r) { return r.tau === p.tau; })) { S.say('You already have this period. Choose another.'); return; }
      log = { t0: sim.t, hi1: -1e9, lo1: 1e9, t1: 0, hi2: -1e9, lo2: 1e9, t2: 0 }; S.say('Recording one full period…'); S.render(); }
    function stepOnce(dt) { K.step(sim, p, dt); var v = K.view(sim, p);
      if (sim.t >= nextSample) { nextSample = sim.t + p.tau / 150; buf1.push([sim.t, v.T1]); buf2.push([sim.t, v.T2]); if (buf1.length > 420) { buf1.shift(); buf2.shift(); } }
      if (!log) return;
      if (v.T1 > log.hi1) { log.hi1 = v.T1; log.t1 = sim.t; } if (v.T1 < log.lo1) log.lo1 = v.T1; if (v.T2 > log.hi2) { log.hi2 = v.T2; log.t2 = sim.t; } if (v.T2 < log.lo2) log.lo2 = v.T2;
      if (sim.t - log.t0 >= p.tau) { var lagT = log.t2 - log.t1; if (lagT < 0) lagT += p.tau; var r = { tau: p.tau, A1: rnd((log.hi1 - log.lo1) / 2, 0.01), A2: rnd((log.hi2 - log.lo2) / 2, 0.01), lag: rnd(lagT, 0.1) }; log = null; S.addRow(r);
        S.say('Amplitudes ' + r.A1.toFixed(2) + ' K and ' + r.A2.toFixed(2) + ' K; the far peak lags by ' + r.lag.toFixed(1) + ' s.'); } }
    var dx = p.x2 - p.x1; function Dof(r) { return dx * dx / (2 * r.lag * Math.log(r.A1 / r.A2)); }
    var hud1 = S.hudCard('Thermocouple 1'), hud2 = S.hudCard('Thermocouple 2'), hud3 = S.hudCard('Lab time');
    var E = { name: 'Angstrom\'s method', dims: 'Thermocouples ' + (p.x1 * 100).toFixed(1) + ' cm and ' + (p.x2 * 100).toFixed(1) + ' cm from the heater: Δx = ' + (dx * 100).toFixed(1) + ' cm. Copper: ρ = ' + p.rho.toFixed(0) + ' kg/m³, c = ' + p.cp.toFixed(0) + ' J/(kg K) (tables).',
      camera: { pos: [-0.05, 0.62, 1.4], look: [-0.05, 0.1, ZB] },
      views: { main: [[-0.05, 0.6, 1.35], [-0.05, 0.1, ZB]], bar: [[-0.1, 0.35, 0.2], [X0 + 0.3, BY, ZB]], heater: [[X0 + 0.1, 0.3, 0.1], [X0 + 0.02, BY, ZB]], lg: [[0.55, 0.3, 0.3], [0.55, 0.1, ZB]], ctl: [[-0.6, 0.3, 0.2], [-0.78, 0.05, ZB + 0.06]] },
      formula: 'D = Δx² / (2 Δt ln(A1 / A2))', formulaNote: 'A1, A2: amplitudes of the temperature waves at the two points; Δt: the time by which the far peak lags. Then K = D ρ c.',
      book: ['Aim: thermal diffusivity and conductivity of copper (Angstrom).', 'Δx = ' + (dx * 100).toFixed(1) + ' cm,  ρ = ' + p.rho.toFixed(0) + ' kg/m³,  c = ' + p.cp.toFixed(0) + ' J/(kg K)', 'D = Δx² / (2 Δt ln(A1/A2)),   K = D ρ c'],
      columns: [COL_NO, col('Period (s)', function (r) { return r.tau.toFixed(0); }), col('A1 (K)', function (r) { return r.A1.toFixed(2); }), col('A2 (K)', function (r) { return r.A2.toFixed(2); }), col('Δt (s)', function (r) { return r.lag.toFixed(1); }), col('D (cm²/s)', function (r) { return (Dof(r) * 1e4).toFixed(3); })],
      result: function (rows) { if (!rows.length) return null; var D = mean(rows.map(Dof));
        return { label: 'D (thermal diffusivity of copper)', value: D * 1e4, unit: 'cm²/s', digits: 3, truth: p.D * 1e4, note: 'Thermal conductivity K = D ρ c = ' + (D * p.rho * p.cp).toFixed(0) + ' W/(m·K) (true ' + (p.D * p.rho * p.cp).toFixed(0) + ').' }; },
      tol: 0.04, chips: ['What is a temperature wave?', 'Why does the far peak come later?', 'Check my readings', 'Why does the surface loss not matter?'],
      viva: [['A longer heating period makes the temperature wave', ['reach further along the bar', 'die out sooner', 'travel faster'], 0, 'The decay constant falls as the frequency falls, so slow waves penetrate further.']],
      askState: function () { var v = K.view(sim, p); return { heater_period_s: p.tau, heater_running: st.on, thermocouple1_C: +v.T1.toFixed(2), thermocouple2_C: +v.T2.toFixed(2), recording: !!log, rows: S.rows.length }; },
      tick: function (dt) { if (st.on) for (var i = 0; i < st.speed; i++) stepOnce(dt); var v = K.view(sim, p), onHalf = st.on && Math.sin(2 * PI * sim.t / p.tau + 0.9) > 0; htM.emissive.setHex(onHalf ? 0x7a1c08 : 0x000000);
        lg.plot([{ pts: buf1, color: '#f2c94c' }, { pts: buf2, color: '#5fa8ff' }], p.Tm - p.A0 * 0.75, p.Tm + p.A0 * 0.75, 2.5 * p.tau, 'τ = ' + p.tau.toFixed(0) + ' s' + (log ? '  REC' : ''));
        hud1.set(st.on ? v.T1.toFixed(2) + ' °C' : '—'); hud2.set(st.on ? v.T2.toFixed(2) + ' °C' : '—'); hud3.set(Math.floor(sim.t) + ' s'); } };
    E.steps = [setupStep(E, 'Measure the bar', 'The two thermocouples are fixed in small holes in the bar. Measure how far apart they are.', 'Distance between the thermocouples', 'The scale under the bar'),
      { id: 'rec', title: 'Records', view: 'main', render: function (u) { u.h2('Record the temperature waves');
          u.slider('Heating period', 60, 240, 60, function () { return tauSet; }, function (v) { tauSet = v; }, 's');
          u.row(u.button('Set this period on the heater', function () { setTau(); }, true, S.hand.busy || !!log), u.button(log ? 'Recording…' : 'Record one full period', record, false, !st.on || !!log));
          speedRow(u, [1, 20, 60]);
          u.live(function () { var v = K.view(sim, p); return st.on ? 'T1 ' + v.T1.toFixed(2) + ' °C · T2 ' + v.T2.toFixed(2) + ' °C · lab time ' + Math.floor(sim.t) + ' s' : 'Heater off'; });
          u.h3('Observation table'); u.table(); if (S.rows.length < 3) u.p(S.rows.length + ' of 3 periods recorded.'); u.next('Next: work out D and K', S.rows.length >= 3 && !log); },
        ok: function () { return S.rows.length >= 3 && !log; },
        auto: function () { return [120, 180, 240].reduce(function (pr, t) { return pr.then(function () { tauSet = t; return setTau(); }).then(function () { S.advance(5); record(); S.advance(t + 5, function () { return !log; }); }); }, Promise.resolve()); } }];
    return E;
  }

  // ================================================================== specific heat by the method of cooling
  function cooling() {
    var LIQ = /turpentine/i.test(SAMPLE) ? { name: 'turpentine', col: 0xd8cf9a } : { name: 'kerosene', col: 0xb9c7e0 };
    var pw = {}, pl = {}; Object.keys(p).forEach(function (k) { pw[k] = p[k]; pl[k] = p[k]; }); pw.which = 0; pl.which = 1;
    var sw = K.init(pw), sl = K.init(pl); sw.T = p.Ts; sl.T = p.Ts;
    var ranges = [[65, 55], [60, 50]], sel = 0, run = null, W = p.mc * p.cc, mw = p.rhow * p.Vol, ml = p.rhol * p.Vol;
    var CX = 0.05;
    var outer = S.mesh(new T.CylinderGeometry(0.17, 0.17, 0.11, 48, 1, true), new T.MeshStandardMaterial({ color: 0xc4c9ce, roughness: 0.35, metalness: 0.8, side: T.DoubleSide })); put(outer, CX, 0.055, ZB);
    var innerW = S.mesh(new T.CylinderGeometry(0.145, 0.145, 0.105, 48, 1, true), new T.MeshStandardMaterial({ color: 0x9aa1a8, roughness: 0.5, metalness: 0.6, side: T.DoubleSide })); put(innerW, CX, 0.056, ZB);
    var rim = S.mesh(new T.RingGeometry(0.145, 0.17, 48), new T.MeshStandardMaterial({ color: 0x6fb6de, transparent: true, opacity: 0.7, roughness: 0.2, side: T.DoubleSide })); rim.rotation.x = -PI / 2; put(rim, CX, 0.1, ZB);
    var floor = cyl(0.168, 0.004, M.alu, 48); put(floor, CX, 0.002, ZB); S.contact(0.4, 0.4, CX, ZB, 0.55);
    var blackM = new T.MeshStandardMaterial({ color: 0x151515, roughness: 0.9 });
    function calo(x, name, colr) { var g = new T.Group(); g.position.set(x, 0.006, ZB); S.scene.add(g); var c = cyl(0.032, 0.075, blackM, 36); c.position.y = 0.0375; g.add(c);
      var liq = cyl(0.029, 0.002, new T.MeshStandardMaterial({ color: colr, roughness: 0.2 }), 32); liq.position.y = 0.0755; g.add(liq); var lid = S.mesh(new T.CylinderGeometry(0.033, 0.033, 0.004, 36, 1, false, 0.5, PI * 1.5), M.wood); lid.position.y = 0.079; g.add(lid);
      var stir = cyl(0.0012, 0.11, M.copper, 8); stir.position.set(0.016, 0.085, 0.012); g.add(stir); var l = S.label(name, { w: 0.05, ratio: 0.25, color: '#f1f1f1', bg: '#444' }); l.position.set(0, 0.04, 0.0325); g.add(l);
      var th = S.thermometer({ len: 0.26, min: 20, max: 80, value: p.Ts }); th.position.set(-0.008, 0.02, -0.004); g.add(th); g.userData.th = th; return g; }
    var cw = calo(CX - 0.062, 'WATER', 0x6fb6de), cl = calo(CX + 0.062, LIQ.name.toUpperCase(), LIQ.col);
    var bathX = -0.5; var hot = S.rounded(0.18, 0.16, 0.04, 0.01, new T.MeshStandardMaterial({ color: 0xe7e4dc, roughness: 0.5 })); hot.rotation.x = -PI / 2; hot.position.set(bathX, 0.02, ZB); S.scene.add(hot); S.contact(0.24, 0.22, bathX, ZB, 0.5);
    var bath = S.beaker(0.065, 0.11, [bathX, 0.04, ZB], 0x6fb6de, 0.6); var hl = S.label('WATER BATH', { w: 0.09, ratio: 0.2, color: '#333' }); hl.position.set(bathX, 0.02, ZB + 0.081); S.scene.add(hl);
    var w1 = S.stopwatch([0.42, 0.035, 0.08], [-1.15, 0, -0.2]), w2 = S.stopwatch([0.56, 0.035, 0.08], [-1.15, 0, -0.2]);
    S.addApparatus('enc', outer, 'Double-walled enclosure', 'Water between the walls keeps the inside at ' + p.Ts.toFixed(0) + ' °C, so both calorimeters cool into the same surroundings.');
    S.addApparatus('cw', cw, 'Calorimeter with water', 'Blackened copper, ' + (p.mc * 1000).toFixed(0) + ' g, holding ' + (p.Vol * 1e6).toFixed(0) + ' ml of water.');
    S.addApparatus('cl', cl, 'Calorimeter with ' + LIQ.name, 'An identical calorimeter holding the same volume of ' + LIQ.name + '.');
    S.addApparatus('bath', bath, 'Water bath', 'Both liquids are warmed here to about ' + p.T0.toFixed(0) + ' °C. No flame near ' + LIQ.name + '.');
    S.addApparatus('sw', w1.group, 'Two stopwatches', 'One for each calorimeter: started as its thermometer passes the upper mark, stopped at the lower mark.');
    function fill() { if (S.hand.busy || run) return Promise.resolve(); return tap(cw).then(function () { return tap(cl); }).then(function () { pw.Ta = pl.Ta = ranges[sel][0]; pw.Tb = pl.Tb = ranges[sel][1]; sw = K.init(pw); sl = K.init(pl);
      run = { a: [-1, -1], b: [-1, -1] }; w1.t = 0; w2.t = 0; st.on = true; S.say('Both calorimeters filled at ' + p.T0.toFixed(0) + ' °C and covered. Each stopwatch runs from ' + ranges[sel][0] + ' °C to ' + ranges[sel][1] + ' °C.'); S.render(); }); }
    function track(s, q, T0, tPrev, dt, tm, w) { if (tm[0] < 0 && T0 >= q.Ta && s.T < q.Ta) { tm[0] = tPrev + dt * (T0 - q.Ta) / (T0 - s.T); w.on = true; w.t = s.t - tm[0]; }
      if (tm[0] >= 0 && tm[1] < 0 && T0 >= q.Tb && s.T < q.Tb) { tm[1] = tPrev + dt * (T0 - q.Tb) / (T0 - s.T); w.on = false; w.t = Math.round(tm[1] - tm[0]); } else if (tm[0] >= 0 && tm[1] < 0) w.t = s.t - tm[0]; }
    function stepOnce(dt) { var a0 = sw.T, b0 = sl.T, t0 = sw.t; K.step(sw, pw, dt); K.step(sl, pl, dt); if (!run) return; track(sw, pw, a0, t0, dt, run.a, w1); track(sl, pl, b0, t0, dt, run.b, w2);
      if (run.a[1] >= 0 && run.b[1] >= 0) { var r = { Ta: pw.Ta, Tb: pw.Tb, tw: Math.round(run.a[1] - run.a[0]), tl: Math.round(run.b[1] - run.b[0]) }; run = null; S.addRow(r); S.say('Water took ' + r.tw + ' s and ' + LIQ.name + ' ' + r.tl + ' s to cool from ' + r.Ta + ' to ' + r.Tb + ' °C.'); } }
    function cOf(r) { return ((mw * p.cw + W) * r.tl / r.tw - W) / ml; }
    var hud1 = S.hudCard('Water'), hud2 = S.hudCard(LIQ.name.charAt(0).toUpperCase() + LIQ.name.slice(1)), hud3 = S.hudCard('Lab time');
    var E = { name: 'Method of cooling', dims: 'Each calorimeter with stirrer: ' + (p.mc * 1000).toFixed(1) + ' g of copper, so W = ' + W.toFixed(2) + ' J/K. Water: ' + (mw * 1000).toFixed(1) + ' g. ' + LIQ.name.charAt(0).toUpperCase() + LIQ.name.slice(1) + ': ' + (ml * 1000).toFixed(1) + ' g (equal volumes, ' + (p.Vol * 1e6).toFixed(0) + ' ml).',
      camera: { pos: [0.1, 0.62, 0.75], look: [0.05, 0.08, ZB] },
      views: { main: [[0.1, 0.6, 0.7], [0.05, 0.08, ZB]], enc: [[0.1, 0.5, 0.4], [CX, 0.05, ZB]], cw: [[CX - 0.1, 0.4, 0.05], [CX - 0.06, 0.1, ZB]], cl: [[CX + 0.15, 0.4, 0.05], [CX + 0.06, 0.1, ZB]], bath: [[bathX + 0.1, 0.4, 0.2], [bathX, 0.08, ZB]], sw: [[0.5, 0.35, 0.5], [0.49, 0.03, 0.08]] },
      formula: '(m_l c_l + W) / (m_w c_w + W) = t_l / t_w', formulaNote: 'so c_l = ((m_w c_w + W) t_l / t_w − W) / m_l, with c_w = ' + p.cw.toFixed(0) + ' J/(kg K).',
      book: ['Aim: specific heat of ' + LIQ.name + ' by the method of cooling.', 'm_w = ' + (mw * 1000).toFixed(1) + ' g,  m_l = ' + (ml * 1000).toFixed(1) + ' g,  W = ' + W.toFixed(2) + ' J/K', 'c_l = ((m_w c_w + W) t_l/t_w − W) / m_l'],
      columns: [COL_NO, col('Fall (°C)', function (r) { return r.Ta + ' → ' + r.Tb; }), col('t water (s)', function (r) { return String(r.tw); }), col('t liquid (s)', function (r) { return String(r.tl); }), col('c (J/kg·K)', function (r) { return cOf(r).toFixed(0); })],
      result: function (rows) { if (!rows.length) return null; return { label: 'c (' + LIQ.name + ')', value: mean(rows.map(cOf)), unit: 'J/(kg·K)', digits: 0, truth: p.cl, note: 'Mean of ' + rows.length + ' temperature ranges. Water cools more slowly because its heat capacity is larger.' }; },
      tol: 0.04, chips: ['Why identical calorimeters?', 'Why equal volumes?', 'Check my readings', 'Why is my c different?'],
      viva: [['The two liquids are timed over the same fall of temperature because', ['the rate of loss depends on the temperature excess', 'the stopwatch needs it', 'they have the same mass'], 0, 'Only over the same range do both lose heat at the same average rate.']],
      askState: function () { return { liquid: LIQ.name, cooling: st.on, water_C: +sw.T.toFixed(1), liquid_C: +sl.T.toFixed(1), range_C: ranges[sel].join(' to '), timing: !!run, rows: S.rows.length }; },
      tick: function (dt) { if (st.on) for (var i = 0; i < st.speed; i++) stepOnce(dt); cw.userData.th.set(sw.T); cl.userData.th.set(sl.T);
        hud1.set(sw.T.toFixed(1) + ' °C'); hud2.set(sl.T.toFixed(1) + ' °C'); hud3.set(Math.floor(sw.t) + ' s'); } };
    E.steps = [setupStep(E, 'Weigh the calorimeters', 'Weigh each calorimeter with its stirrer empty, then with its liquid: both must hold the same volume.', 'Masses of the calorimeters and the liquids', 'Balance and measuring cylinder'),
      { id: 'cool', title: 'Cooling', view: 'main', render: function (u) { u.h2('Time the cooling of both');
          var r0 = u.row(); ranges.forEach(function (q, i) { r0.appendChild(u.button((sel === i ? '✓ ' : '') + q[0] + ' °C → ' + q[1] + ' °C', function () { if (run) { S.say('Finish this run first.'); return; } sel = i; S.render(); }, false, !!run)); });
          u.row(u.button(run ? 'Cooling…' : 'Fill both hot and start', function () { fill(); }, true, !!run || S.hand.busy));
          speedRow(u, [1, 10, 30]);
          u.live(function () { return 'Water ' + sw.T.toFixed(1) + ' °C (' + w1.t.toFixed(0) + ' s) · ' + LIQ.name + ' ' + sl.T.toFixed(1) + ' °C (' + w2.t.toFixed(0) + ' s)'; });
          u.h3('Observation table'); u.table(); if (S.rows.length < 2) u.p(S.rows.length + ' of 2 temperature ranges timed.'); u.next('Next: work out c', S.rows.length >= 2 && !run); },
        ok: function () { return S.rows.length >= 2 && !run; },
        auto: function () { return [0, 1].reduce(function (pr, i) { return pr.then(function () { sel = i; return fill(); }).then(function () { S.advance(4000, function () { return !run; }); }); }, Promise.resolve()); } }];
    return E;
  }

  // ================================================================== a hot block, a thermocouple and a logger
  function daq() {
    var sim = K.init(p); sim.y = [p.Ts]; var placed = false, logging = false, t0 = 0, nextAt = 0, buf = [], STEP = 30, TOTAL = 600, roomRead = false;
    var BX = 0.0, bathX = -0.5;
    var standB = cyl(0.045, 0.012, M.cork, 36); put(standB, BX, 0.006, ZB); S.contact(0.13, 0.13, BX, ZB, 0.5);
    var hot = S.rounded(0.18, 0.16, 0.04, 0.01, new T.MeshStandardMaterial({ color: 0xe7e4dc, roughness: 0.5 })); hot.rotation.x = -PI / 2; hot.position.set(bathX, 0.02, ZB); S.scene.add(hot); S.contact(0.24, 0.22, bathX, ZB, 0.5);
    var bath = S.beaker(0.065, 0.11, [bathX, 0.04, ZB], 0x6fb6de, 0.7);
    var block = new T.Group(); S.scene.add(block); var bm = cyl(0.03, 0.06, M.brass, 40); block.add(bm); var hole = cyl(0.003, 0.004, M.black, 12); hole.position.y = 0.0305; block.add(hole);
    var IN = new T.Vector3(bathX, 0.08, ZB), OUT = new T.Vector3(BX, 0.042, ZB); block.position.copy(IN);
    var lg = logger([0.5, 0, ZB + 0.02], 'THERMOCOUPLE DATA LOGGER'), tcw = S.wire([[BX, 0.08, ZB], [0.2, 0.2, ZB + 0.05], [0.4, 0.19, ZB + 0.02]], 'yellow');
    var probe = cyl(0.0015, 0.05, M.steel, 8); S.scene.add(probe);
    function wireTo(v) { probe.position.set(v.x, v.y + 0.05, v.z); tcw.set([[v.x, v.y + 0.075, v.z], [0.2, 0.22, ZB + 0.05], [0.4, 0.19, ZB + 0.02]]); }
    wireTo(new T.Vector3(BX + 0.1, 0.0, ZB + 0.1));
    S.addApparatus('block', block, 'Brass block', 'A small brass cylinder with a hole for the thermocouple. It is heated in the water bath.');
    S.addApparatus('stand', standB, 'Insulating stand', 'A cork mat: the block loses heat to the air, not to the bench.');
    S.addApparatus('lg', lg, 'Thermocouple amplifier and data logger', 'Reads the thermocouple to 0.1 °C and records a sample every ' + STEP + ' s.');
    S.addApparatus('bath', bath, 'Hot water bath', 'Heats the block to about ' + p.T0.toFixed(0) + ' °C.');
    function readRoom() { roomRead = true; measure('Thermocouple in the air reads the room temperature Ts = ' + p.Ts.toFixed(1) + ' °C.'); }
    function place() { if (S.hand.busy || placed) return Promise.resolve(); if (!st.dims) { S.say('Read the room temperature first.'); return Promise.resolve(); }
      return S.hand.pinchMove(IN.clone(), function (k) { var q = IN.clone().lerp(OUT, k); q.y += Math.sin(k * PI) * 0.15; return q; }, function (k) { var q = IN.clone().lerp(OUT, k); q.y += Math.sin(k * PI) * 0.15; block.position.copy(q); }, { ms: 1500 })
        .then(function () { block.position.copy(OUT); wireTo(OUT); sim = K.init(p); placed = true; st.on = true; S.say('The block is on the stand at ' + p.T0.toFixed(0) + ' °C with the thermocouple in it. Start the logger.'); S.render(); }); }
    function startLog() { if (!placed) { S.say('Put the hot block on the stand first.'); return Promise.resolve(); } if (logging || S.rows.length) { S.say('The record is already taken.'); return Promise.resolve(); }
      return tap(lg).then(function () { logging = true; t0 = sim.t; nextAt = 0; S.click(2200); S.render(); }); }
    function stepOnce(dt) { K.step(sim, p, dt); if (!logging) return; var tt = sim.t - t0;
      if (tt >= nextAt - 1e-9) { var Tn = rnd(sim.y[0], 0.1); S.addRow({ t: nextAt, T: Tn }); buf.push([nextAt, Tn]); nextAt += STEP; if (nextAt > TOTAL) { logging = false; S.say('Ten minutes logged: ' + S.rows.length + ' samples. Plot ln(T − Ts) against t.'); S.render(); } } }
    var hud1 = S.hudCard('Thermocouple'), hud2 = S.hudCard('Lab time');
    var E = { name: 'Cooling curve with a logger', dims: 'Thermocouple in the air reads the room temperature Ts = ' + p.Ts.toFixed(1) + ' °C.',
      camera: { pos: [0.22, 0.52, 1.05], look: [0.22, 0.08, ZB] },
      views: { main: [[0.22, 0.5, 1.0], [0.22, 0.08, ZB]], block: [[0.1, 0.25, 0.0], [BX, 0.04, ZB]], stand: [[0.1, 0.25, 0.0], [BX, 0.02, ZB]], lg: [[0.5, 0.3, 0.3], [0.5, 0.1, ZB]], bath: [[bathX + 0.1, 0.4, 0.2], [bathX, 0.08, ZB]] },
      formula: 'T − Ts = (T0 − Ts) exp(−k t)', formulaNote: 'so ln(T − Ts) against t is a straight line of slope −k.',
      book: ['Aim: cooling constant of a hot block (Newton\'s law).', 'Room temperature Ts = ' + p.Ts.toFixed(1) + ' °C', 'ln(T − Ts) = ln(T0 − Ts) − k t'],
      columns: [COL_NO, col('t (s)', function (r) { return String(r.t); }), col('T (°C)', function (r) { return r.T.toFixed(1); }), col('ln(T − Ts)', function (r) { return Math.log(r.T - p.Ts).toFixed(3); })],
      graph: { x: function (r) { return r.t; }, y: function (r) { return Math.log(r.T - p.Ts); }, xlabel: 't (s)', ylabel: 'ln(T − Ts)', line: function (pts) { var f = S.fit.linear(pts); return function (x) { return f.m * x + f.c; }; } },
      result: function (rows) { if (rows.length < 4) return null; var f = S.fit.linear(rows.map(function (r) { return [r.t, Math.log(r.T - p.Ts)]; })); if (!f) return null;
        return { label: 'k (cooling constant)', value: -f.m, unit: '1/s', digits: 5, truth: p.k, note: 'From the slope of ln(T − Ts) against t over ' + rows.length + ' logged samples. Time constant 1/k = ' + (-1 / f.m).toFixed(0) + ' s.' }; },
      tol: 0.03, chips: ['What is Newton\'s law of cooling?', 'Why plot ln(T − Ts)?', 'Check my readings', 'Why use a thermocouple?'],
      viva: [['Newton\'s law of cooling holds well when', ['the temperature excess is small', 'the body is very hot', 'there is no air'], 0, 'For a small excess the loss by convection and radiation is nearly proportional to it.']],
      askState: function () { return { room_C: p.Ts, block_on_stand: placed, thermocouple_C: +sim.y[0].toFixed(1), logging: logging, samples: S.rows.length }; },
      tick: function (dt) { if (st.on) for (var i = 0; i < st.speed; i++) stepOnce(dt);
        lg.plot([{ pts: buf, color: '#f2c94c' }], p.Ts - 2, p.T0 + 4, TOTAL, (placed ? sim.y[0] : p.Ts).toFixed(1) + ' °C' + (logging ? '  REC' : ''));
        hud1.set((placed ? sim.y[0] : p.Ts).toFixed(1) + ' °C'); hud2.set(placed ? Math.floor(sim.t) + ' s' : '—'); } };
    E.steps = [{ id: 'setup', title: 'Set up', view: 'main', render: function (u) { u.h2('Room temperature, then the hot block');
          u.task('1. Read the room temperature with the thermocouple', st.dims, st.dims ? 'Ts = ' + p.Ts.toFixed(1) + ' °C' : 'The junction hangs in the air')
            .add(u.button(st.dims ? 'Noted' : 'Read and note', readRoom, !st.dims, st.dims));
          u.task('2. Move the hot block to the stand', placed, placed ? 'On the stand, thermocouple in' : 'The hand lifts it out of the bath')
            .add(u.button(placed ? 'Placed' : 'Place the block', function () { place(); }, st.dims && !placed, placed || S.hand.busy));
          u.next('Next: log the cooling', st.dims && placed); },
        ok: function () { return st.dims && placed; }, auto: function () { readRoom(); return place(); } },
      { id: 'log', title: 'Logging', view: 'lg', render: function (u) { u.h2('Let the logger record');
          u.p('The logger takes a sample every ' + STEP + ' s for ' + (TOTAL / 60) + ' minutes. Keep the block away from draughts.');
          u.row(u.button(logging ? 'Logging…' : 'Start the logger', function () { startLog(); }, true, logging || S.rows.length > 0 || S.hand.busy));
          speedRow(u, [1, 10, 60]);
          u.live(function () { return 'Thermocouple ' + sim.y[0].toFixed(1) + ' °C · ' + S.rows.length + ' samples'; });
          u.h3('Logged samples'); u.table(); u.next('Next: work out k', !logging && S.rows.length >= 10); },
        ok: function () { return !logging && S.rows.length >= 10; },
        auto: function () { return startLog().then(function () { S.advance(TOTAL + 10, function () { return !logging; }); }); } }];
    return E;
  }

  var E = KN === 'w7_stefan' ? stefan() : KN === 'w7_cbarnes' ? cbarnes() : KN === 'w7_angstrom' ? angstrom() : KN === 'w7_cool' ? cooling() : daq();
  E.views.book = [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]];
  return {
    camera: E.camera, views: E.views,
    theory: { principle: S.lab.theory, formula: E.formula, formulaNote: E.formulaNote, more: [S.lab.aim], precautions: S.lab.safety + ' Take readings only when they have stopped drifting.' },
    book: { title: 'Expt. — ' + E.name, lines: E.book, columns: E.columns },
    graph: E.graph, result: E.result, tol: E.tol, chips: E.chips, viva: E.viva, askState: E.askState,
    steps: E.steps, tick: E.tick,
  };
});
