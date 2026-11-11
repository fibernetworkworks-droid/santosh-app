/* Prayogshala studio rig: the heating effect of an electric current (NCERT Science VII / X).
   A nichrome coil in a lagged copper calorimeter holding a weighed mass of water, with a battery eliminator, a plug
   key and an ammeter in series, a thermometer and a stirrer. The temperature comes from the `jouleheat` kernel of
   packs/em_school.js, which integrates m c dT/dt = I²R - the Joule's law the server checks. */
HoolaStudio.define('heating-effect-wire', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KJ = HK.K.jouleheat;
  var p = HK.paramsFor('jouleheat', S.lab.params);
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || '';
  var RW = KJ.wire_r(p), TOT = p.tsec, STEP = Math.max(15, Math.round(TOT / 6 / 5) * 5);
  function pick(list, need) { for (var i = 0; i < list.length; i++) if (list[i] >= need - 1e-9) return list[i]; return list[list.length - 1]; }
  var AMAX = pick([0.5, 1, 1.5, 2, 3, 5], (p.Eb / (RW + p.rint)) * 1.25), ARES = AMAX / 100;
  var sim = KJ.init(p);
  var st = { key: false, running: false, mult: 1, traced: false, zero: false, next: 0 };
  function solve() { p.key = st.key ? 1 : 0; }
  function Tnow() { return sim.T; }
  function Inow() { return st.key ? KJ.current(p) : 0; }
  function Pnow() { return st.key ? KJ.power(p) : 0; }
  function fI(v) { return (Math.round(v / ARES) * ARES).toFixed(2); }
  function fT(v) { return (Math.round(v * 10) / 10).toFixed(1); }
  function fmtN(v, d) { return String(+v.toFixed(d === undefined ? 2 : d)); }

  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }

  // ---------- the calorimeter: a copper vessel inside a lagged wooden jacket, with a lid
  var CX = 0.12, CZ = -0.3, CR = 0.052, CH = 0.09;
  var jacket = S.mesh(new T.CylinderGeometry(CR + 0.022, CR + 0.022, CH + 0.02, 36, 1, true), M.darkWood);
  jacket.position.set(CX, (CH + 0.02) / 2, CZ); S.scene.add(jacket);
  var jbase = S.mesh(new T.CylinderGeometry(CR + 0.022, CR + 0.022, 0.008, 36), M.darkWood); jbase.position.set(CX, 0.004, CZ); S.scene.add(jbase);
  var vessel = S.mesh(new T.CylinderGeometry(CR, CR, CH, 36, 1, true), M.copper); vessel.position.set(CX, 0.012 + CH / 2, CZ); S.scene.add(vessel);
  var vbot = S.mesh(new T.CylinderGeometry(CR, CR, 0.003, 36), M.copper); vbot.position.set(CX, 0.013, CZ); S.scene.add(vbot);
  var water = S.mesh(new T.CylinderGeometry(CR - 0.003, CR - 0.003, 0.05, 36),
    new T.MeshPhysicalMaterial({ color: 0xbfe0ee, transmission: 0.6, roughness: 0.08, thickness: 0.03, transparent: true, opacity: 0.8 }), false);
  water.position.set(CX, 0.04, CZ); S.scene.add(water);
  var lid = S.mesh(new T.CylinderGeometry(CR + 0.024, CR + 0.024, 0.006, 36), M.bakelite); lid.position.set(CX, CH + 0.026, CZ); S.scene.add(lid);
  S.contact(0.17, 0.17, CX, CZ, 0.5);
  var ctag = S.label('CALORIMETER  ·  ' + fmtN(p.mw * 1000, 0) + ' g WATER', { w: 0.1, ratio: 0.12, color: '#f3ead2', bg: '#2b2b2b', px: 768 });
  ctag.position.set(CX, 0.05, CZ + CR + 0.0225); S.scene.add(ctag);

  // the nichrome heating coil, hanging in the water
  var coil = new T.Group(); S.scene.add(coil); coil.position.set(CX, 0.045, CZ);
  var hpts = [], turns = 9;
  for (var i = 0; i <= turns * 24; i++) {
    var t = i / (turns * 24), a = t * turns * Math.PI * 2;
    hpts.push(new T.Vector3(Math.cos(a) * 0.022, -0.016 + t * 0.03, Math.sin(a) * 0.022));
  }
  var nicM = new T.MeshStandardMaterial({ color: 0xb4b2ae, emissive: new T.Color(0, 0, 0), roughness: 0.32, metalness: 0.85 });
  coil.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3(hpts), turns * 24, 0.0009, 6, false), nicM));
  [-1, 1].forEach(function (s) {
    var st2 = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.085, 8), nicM);
    st2.position.set(s * 0.012, 0.045, 0); coil.add(st2);
  });
  var cpost = post(CX + 0.07, 0.012, CZ + 0.055, 'red'), cpost2 = post(CX - 0.07, 0.012, CZ + 0.055, 'black');
  [[0.012, cpost], [-0.012, cpost2]].forEach(function (q) {
    S.scene.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3([new T.Vector3(CX + q[0], 0.088, CZ),
      new T.Vector3(CX + q[0] * 4, 0.1, CZ + 0.04), new T.Vector3(q[1].at.x, 0.02, q[1].at.z)]), 20, 0.0011, 6, false),
      new T.MeshStandardMaterial({ color: 0xb8322a, roughness: 0.45 })));
  });
  var rtag = S.label('NICHROME  R = ' + fmtN(RW, 2) + ' Ω', { w: 0.08, ratio: 0.14, color: '#f3ead2', bg: '#2b2b2b', px: 640 });
  rtag.rotation.x = -Math.PI / 2; rtag.position.set(CX, CH + 0.03, CZ + 0.03); S.scene.add(rtag);

  // thermometer and stirrer through the lid
  var therm = S.thermometer({ len: 0.2, min: 20, max: 60, pos: [CX - 0.022, 0.03, CZ - 0.012], value: p.Ta });
  var stir = S.mesh(new T.CylinderGeometry(0.0016, 0.0016, 0.13, 10), M.chrome); stir.position.set(CX + 0.03, 0.08, CZ - 0.01); S.scene.add(stir);
  var stirR = S.mesh(new T.TorusGeometry(0.012, 0.0016, 8, 20), M.chrome); stirR.rotation.x = Math.PI / 2; stirR.position.set(CX + 0.03, 0.022, CZ - 0.01); S.scene.add(stirR);

  // ---------- supply, key, ammeter
  var PB = [-0.52, -0.08];
  var pb = S.powerBox([PB[0], 0, PB[1]], 'BATTERY ELIMINATOR');
  var pbV = S.label(fmtN(p.Eb, 1) + ' V DC', { w: 0.05, ratio: 0.3, color: '#f2f2f2' });
  pbV.position.set(PB[0] + 0.045, 0.034, PB[1] + 0.0405); S.scene.add(pbV);
  var pbPlus = { at: new T.Vector3(PB[0] + 0.04, 0.109, PB[1]) }, pbMinus = { at: new T.Vector3(PB[0] - 0.04, 0.109, PB[1]) };
  var KP = [-0.34, -0.02];
  var key = S.plugKey([KP[0], 0, KP[1]]), plug = key.userData.plug;
  var kLbl = S.label('K', { w: 0.013, ratio: 1, color: '#f0e6c8' }); kLbl.rotation.x = -Math.PI / 2; kLbl.position.set(KP[0], 0.0175, KP[1] + 0.016); S.scene.add(kLbl);
  var kL = post(KP[0] - 0.042, 0, KP[1] - 0.04, 'red'), kR = post(KP[0] + 0.042, 0, KP[1] - 0.04, 'black');
  var ZAX = new T.Vector3(0, 0, 1);
  function plugPose(k) { return { x: 0.062 * (1 - k), y: 0.008 + 0.016 * k + 0.04 * Math.sin(Math.PI * k), z: 0.012 * (1 - k), rz: Math.PI / 2 * (1 - k) }; }
  function plugApply(k) { var q = plugPose(k); plug.position.set(q.x, q.y, q.z); plug.rotation.set(0, 0, q.rz); }
  function plugHead(k) { var q = plugPose(k); return key.localToWorld(new T.Vector3(0, 0.013, 0).applyAxisAngle(ZAX, q.rz).add(new T.Vector3(q.x, q.y, q.z))); }
  plugApply(0);
  var am = S.meter({ min: 0, max: AMAX, ticks: AMAX === 0.5 ? 5 : AMAX === 1 ? 10 : 6, unit: 'A', symbol: 'A',
    caption: 'DC AMMETER 0–' + fmtN(AMAX) + ' A', pos: [-0.3, 0, -0.4] });
  var amP = { at: wpt(am, 0.035, 0.07, -0.03) }, amM = { at: wpt(am, -0.035, 0.07, -0.03) };
  var watch = S.stopwatch([0.44, 0, 0.04], [0, -0.4, 0]);
  lead(pbPlus.at, kL.at, 'red', [[-0.46, -0.14], [-0.4, -0.08]]);
  lead(kR.at, cpost.at, 'red', [[-0.26, -0.08], [0.0, -0.16]]);
  lead(cpost2.at, amP.at, 'yellow', [[-0.1, -0.28], [-0.26, -0.34]]);
  lead(amM.at, pbMinus.at, 'black', [[-0.46, -0.4], [-0.6, -0.26]]);

  S.addApparatus('cal', vessel, 'Calorimeter with ' + fmtN(p.mw * 1000, 0) + ' g of water',
    'A copper vessel in a lagged jacket, so that nearly all the heat made in the coil stays in the water.');
  S.addApparatus('coil', coil, 'Nichrome heating coil (' + fmtN(RW, 2) + ' Ω)',
    'Nichrome is used because its resistivity is high: the current does most of its work here and not in the leads.');
  S.addApparatus('therm', therm, 'Thermometer', 'Reads to 0.1 °C. Stir before every reading so the whole of the water is at one temperature.');
  S.addApparatus('pb', pb, 'Battery eliminator (' + fmtN(p.Eb, 1) + ' V)', 'A low-voltage DC supply. Never do this experiment on the mains.');
  S.addApparatus('key', key, 'Plug key K', 'The stopwatch is started at the same moment as the key is closed.');
  S.addApparatus('am', am, 'Ammeter (0–' + fmtN(AMAX) + ' A)', 'In series with the coil: it reads the current that is doing the heating.');
  S.addApparatus('watch', watch.group, 'Stopwatch', 'Started with the key; the temperature is read every ' + STEP + ' seconds.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudT = S.hudCard('Thermometer'), hudI = S.hudCard('Ammeter'), hudC = S.hudCard('Stopwatch');
  solve();

  function setKey(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!!on === st.key) return Promise.resolve();
    var a = st.key ? 1 : 0, b = on ? 1 : 0;
    if (!on) { st.key = false; st.running = false; solve(); }
    return S.hand.pinchMove(plugHead(a), function (k) { return plugHead(a + (b - a) * k); }, function (k) { plugApply(a + (b - a) * k); },
      { ms: 850, mode: 'top' }).then(function () {
        plugApply(b); st.key = !!on; solve(); S.click(1500, 0.04, 0.09);
        if (on) { st.running = true; watch.on = true; }
        S.say(on ? 'Key closed and the stopwatch started together: ' + fI(Inow()) + ' A is passing through the coil.'
          : 'Key open: the heating has stopped.');
        S.render();
      });
  }
  function trace() { st.traced = true; S.focus('circuit');
    S.say('Supply, key, the heating coil and the ammeter in one series loop. The coil is right under the water, and the thermometer and stirrer go through the lid.');
    S.render(); }
  function zeroCheck() {
    if (st.key) { S.say('Take the key out first.'); return; }
    st.zero = true; S.focus('therm');
    S.say('The water has been weighed (' + fmtN(p.mw * 1000, 0) + ' g) and left to settle: it starts at ' + fT(p.Ta) + ' °C, the temperature of the room.');
    S.render();
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.key && sim.t <= 0) { S.say('Close the key and start the stopwatch first.'); return false; }
    var tt = Math.round(sim.t), tmp = +fT(Tnow());
    if (S.rows.some(function (r) { return Math.abs(r.t - tt) < STEP * 0.5; })) { S.say('A reading was taken at about this time. Wait for the next ' + STEP + ' seconds.'); return false; }
    if (S.rows.length >= 10) { S.say('Ten readings are plenty. Go on to the graph.'); return false; }
    S.addRow({ t: tt, T: tmp });
    S.say('Written in your record book: at ' + tt + ' s the thermometer reads ' + tmp.toFixed(1) + ' °C.');
    return true;
  }
  function slope(rows) { var f = S.fit.linear(rows.map(function (r) { return [r.t, r.T]; })); return f ? f.m : NaN; }

  return {
    camera: { pos: [0.0, 1.36, 0.6], look: [0.0, 0.02, -0.24] },
    views: { cal: [[0.14, 0.34, -0.02], [0.12, 0.05, -0.3]], coil: [[0.12, 0.26, -0.1], [0.12, 0.05, -0.3]],
      therm: [[0.06, 0.34, -0.06], [0.1, 0.08, -0.3]], pb: [[-0.44, 0.32, 0.08], [-0.52, 0.04, -0.1]],
      key: [[-0.3, 0.24, 0.1], [-0.34, 0.02, -0.02]], am: [[-0.3, 0.26, -0.14], [-0.3, 0.04, -0.42]],
      watch: [[0.44, 0.26, 0.26], [0.44, 0.02, 0.04]],
      circuit: [[0.0, 1.36, 0.6], [0.0, 0.02, -0.24]], work: [[0.1, 0.62, 0.14], [0.1, 0.05, -0.28]],
      book: [[-0.5, 0.45, 0.6], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A current does work against the resistance of a wire, and all of that work appears as heat: H = I²Rt. '
        + 'If the coil is under water in a lagged calorimeter, that heat goes into the water and its temperature rises steadily.',
      formula: 'I²R t = m c ΔT',
      formulaNote: 'so the specific heat capacity of water is c = I²R / (m × dT/dt)',
      more: ['The graph of temperature against time is a straight line while the water is still near room temperature: the coil pours in heat at a steady '
        + 'I²R watts and almost none escapes. The slope of that line is all you need.',
        'This is why a heater element is nichrome and the leads are copper: heat is made where the resistance is.'],
      precautions: 'Use a low-voltage supply, never the mains. The coil must stay under water the whole time, stir before every reading, and keep the key out '
        + 'when you are not taking readings.' },
    book: { title: 'Expt. — Heating effect of a current',
      lines: ['Aim: ' + S.lab.aim].concat(SAMPLE ? ['Coil: ' + SAMPLE] : [])
        .concat(['Water: ' + fmtN(p.mw * 1000, 0) + ' g, starting at ' + fT(p.Ta) + ' °C',
          'Coil resistance R = ' + fmtN(RW, 2) + ' Ω', 'Reading every ' + STEP + ' s for ' + TOT + ' s',
          'c = I²R / (m × slope of T against t)']),
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 't (s)', get: function (r) { return r.t; } },
        { label: 'T (°C)', get: function (r) { return r.T.toFixed(1); } },
        { label: 'Rise (°C)', get: function (r) { return (r.T - p.Ta).toFixed(1); } }] },
    graph: { x: function (r) { return r.t; }, y: function (r) { return r.T; }, xlabel: 't (s)', ylabel: 'T (°C)', x0: 0,
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: function (rows) {
      if (rows.length < 4) return null;
      var m = slope(rows);
      if (!isFinite(m) || m <= 0) return null;
      var I = KJ.current(HK.assign(p, { key: 1 }));
      return { label: 'Specific heat capacity of water', value: I * I * RW / (p.mw * m), unit: 'J/(kg·K)', digits: 0,
        truth: p.cw, note: 'From I²R ÷ (mass × slope of the temperature-time graph).' };
    },
    tol: 0.05,
    resultNote: 'The electrical energy put in and the heat taken up by the water agree: energy has only changed its form.',
    chips: ['Why does the wire get hot?', 'Why is the calorimeter lagged?', 'What would double the heating?',
      'Check my readings', 'Why nichrome and not copper?'],
    viva: [['The same coil is run at twice the voltage for the same time. The heat produced becomes',
      ['4 times', '2 times', 'The same'], 0, 'H = V²t/R, so doubling V gives four times the heat.'],
    ['Why must the coil stay under the water?',
      ['Otherwise the heat goes into the air and the coil may burn out', 'Otherwise the current stops',
        'Otherwise the ammeter cannot read'], 0, 'A heating coil run dry gets red hot and fails.']],
    askState: function () {
      return { water_g: +fmtN(p.mw * 1000, 0), coil_resistance_ohm: +fmtN(RW, 2), key_closed: st.key,
        ammeter_A: +fI(Inow()), power_W: +fmtN(Pnow(), 2), elapsed_s: Math.round(sim.t),
        temperature_C: +fT(Tnow()), rise_C: +fT(Tnow() - p.Ta), time_speed: st.mult + '×', readings_taken: S.rows.length };
    },
    steps: [
      { id: 'check', title: 'Set it up', view: 'cal', render: function (u) {
          u.h2('Set the calorimeter up');
          u.p('The weighed water is in the lagged calorimeter, with the coil under the surface and the thermometer and stirrer through the lid.');
          u.task('1. Trace the circuit', st.traced, st.traced ? 'Supply, key, coil, ammeter: one loop' : 'Follow the leads from the supply')
            .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
          u.task('2. Note the starting temperature', st.zero, st.zero ? 'Water at ' + fT(p.Ta) + ' °C' : 'Let the water settle to room temperature')
            .add(u.button(st.zero ? 'Noted' : 'Read the thermometer', zeroCheck, !st.zero, st.zero));
          u.note('The coil must be completely under the water before the key goes in.');
          u.next('Next: switch the current on', st.traced && st.zero);
        },
        ok: function () { return st.traced && st.zero; },
        auto: function () { trace(); zeroCheck(); return Promise.resolve(); } },
      { id: 'on', title: 'Switch on', view: 'am', render: function (u) {
          u.h2('Close the key and start the stopwatch');
          u.p('Both at the same moment, so that the time on the watch is the time the current has been flowing.');
          u.task('Key in, watch running', st.key, st.key ? fI(Inow()) + ' A, ' + Math.round(sim.t) + ' s elapsed' : 'Key open')
            .add(u.row(u.button(st.key ? 'Running' : 'Close the key and start', function () { setKey(true); }, true, st.key || S.hand.busy),
              u.button('Take the plug out', function () { setKey(false); }, false, !st.key || S.hand.busy)));
          u.live(function () { return 'I ' + fI(Inow()) + ' A  ·  power ' + fmtN(Pnow(), 2) + ' W  ·  ' + Math.round(sim.t) + ' s  ·  ' + fT(Tnow()) + ' °C'; });
          u.note('The power going into the water is I²R = ' + fmtN(Pnow(), 2) + ' W. Nothing of it escapes, so the temperature climbs in a straight line.');
          u.next('Next: read the temperature every ' + STEP + ' s', st.key);
        },
        ok: function () { return st.key; },
        auto: function () { return setKey(true); } },
      { id: 'read', title: 'Read every ' + STEP + ' s', view: 'work', render: function (u) {
          u.h2('Temperature against time');
          u.p('Stir, read the thermometer every ' + STEP + ' seconds and record it, until ' + TOT + ' seconds have passed.');
          u.slider('Watch the clock at', 1, 60, 1, function () { return st.mult; }, function (v) { st.mult = Math.round(v); }, '× real time', 0);
          u.row(u.button('Record this reading', function () { record(); }, true, S.hand.busy),
            u.button(st.key ? 'Take the plug out' : 'Close the key', function () { setKey(!st.key); }, false, S.hand.busy));
          u.live(function () { return Math.round(sim.t) + ' s  ·  ' + fT(Tnow()) + ' °C  ·  risen ' + fT(Tnow() - p.Ta) + ' °C  ·  I ' + fI(Inow()) + ' A'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 4) u.p(S.rows.length + ' of at least 4 readings recorded.');
          u.next('Next: plot T against t', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          st.mult = 1;
          var jobs = [];
          for (var k = 0; k <= 5; k++) jobs.push(k);
          return jobs.reduce(function (pr, k) {
            return pr.then(function () { if (k > 0) S.advance(STEP); record(); });
          }, st.key ? Promise.resolve() : setKey(true));
        } },
    ],
    tick: function (dt) {
      solve();
      if (st.running && st.key) { KJ.step(sim, p, dt * st.mult); }
      watch.on = st.running && st.key; watch.t = sim.t;
      am.set(Inow()); therm.set(Tnow());
      var g = Math.max(0, Math.min(1, (Tnow() - p.Ta) / 40));
      nicM.emissive.setRGB(0.35 * g, 0.08 * g, 0.02 * g);
      hudT.set(fT(Tnow()) + ' °C'); hudI.set(fI(Inow()) + ' A'); hudC.set(Math.round(sim.t) + ' s');
    },
  };
});
