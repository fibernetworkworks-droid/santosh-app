/* Prayogshala studio module: Ohm's law (NCERT Class XII). Battery eliminator, plug key, ammeter, rheostat and a coil of
   resistance wire in series, a voltmeter across the coil. Every needle reads the circuit kernel (kernels.js, MNA) with the
   lab's own net (S.lab.cfg) - the same numbers the server checks. The hidden unknown is the coil's resistance Rx. */
HoolaStudio.define('ohms-law', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.circuit, CFG = S.lab.cfg;
  var p = window.HoolaKernels.paramsFor('circuit', S.lab.params);
  var RH_MAX = 20, RH_LEN = 0.3;
  // the sample on the bench (a family variant names it) and meter ranges that follow the lab's own numbers
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || '';
  function pick(list, need) { for (var i = 0; i < list.length; i++) if (list[i] >= need - 1e-9) return list[i]; return list[list.length - 1]; }
  var EB = p.Eb, VMAX = pick([1, 3, 5, 10, 15], EB), AMAX = pick([0.5, 1, 2, 3, 5], EB / (p.Rx + 0.5));
  var ARES = AMAX / 100, VRES = VMAX / 300;          // read to half a division: 0-1 A -> 0.01 A, 0-3 V -> 0.01 V
  function fmtN(v) { return String(+v.toFixed(2)); }
  var ATXT = AMAX < 1 ? Math.round(AMAX * 1000) + ' mA' : fmtN(AMAX) + ' A', VTXT = fmtN(VMAX) + ' V';
  var IDIG = ARES < 0.01 - 1e-12 ? 3 : 2;
  var st = { traced: false, zero: false, key: false, f: 1, target: 1 };
  var view = {};
  function solve() { p.key = st.key ? 1 : 0; p.Rh = RH_MAX * st.f; view = K.view(K.init(p, CFG), p, CFG); }
  function I() { return st.key ? view.I_AM : 0; }
  function V() { return st.key ? view.V_VM : 0; }
  function r2(v) { return Math.round(v * 100) / 100; }
  function rI(v) { return Math.round(v / ARES) * ARES; }
  function rV(v) { return Math.round(v / VRES) * VRES; }
  function fI(v) { return rI(v).toFixed(IDIG); }
  function fV(v) { return rV(v).toFixed(2); }

  // ---------- helpers (kept inside this module)
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {   // an insulated lead from terminal a to terminal b, lying on the bench in between
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]); var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }

  // ---------- battery eliminator (Eb DC)
  var PB = [-0.66, -0.5];
  var pb = S.powerBox([PB[0], 0, PB[1]], 'BATTERY ELIMINATOR');
  var pbV = S.label(fmtN(EB) + ' V DC', { w: 0.05, ratio: 0.3, color: '#f2f2f2' }); pbV.position.set(PB[0] + 0.045, 0.034, PB[1] + 0.0405); S.scene.add(pbV);
  var lamp = S.mesh(new T.SphereGeometry(0.004, 12, 10), new T.MeshStandardMaterial({ color: 0x3a0b08, emissive: 0x000000, roughness: 0.3 }));
  lamp.position.set(PB[0] - 0.05, 0.035, PB[1] + 0.041); S.scene.add(lamp);
  var pbPlus = { at: new T.Vector3(PB[0] + 0.04, 0.109, PB[1]) }, pbMinus = { at: new T.Vector3(PB[0] - 0.04, 0.109, PB[1]) };

  // ---------- plug key (the hand inserts / removes the brass plug)
  var KEYP = [-0.44, -0.2];
  var key = S.plugKey([KEYP[0], 0, KEYP[1]]); var plug = key.userData.plug;
  var kL = post(KEYP[0] - 0.02, 0.022, KEYP[1] - 0.008), kR = post(KEYP[0] + 0.02, 0.022, KEYP[1] - 0.008);
  var keyLbl = S.label('K', { w: 0.012, ratio: 1, color: '#f0e6c8' }); keyLbl.rotation.x = -Math.PI / 2; keyLbl.position.set(KEYP[0], 0.0165, KEYP[1] + 0.014); S.scene.add(keyLbl);
  var ZAX = new T.Vector3(0, 0, 1);
  function plugPose(k) { return { x: 0.062 * (1 - k), y: 0.008 + 0.016 * k + 0.04 * Math.sin(Math.PI * k), z: 0.012 * (1 - k), rz: Math.PI / 2 * (1 - k) }; }
  function plugApply(k) { var q = plugPose(k); plug.position.set(q.x, q.y, q.z); plug.rotation.set(0, 0, q.rz); }
  function plugHead(k) { var q = plugPose(k); return key.localToWorld(new T.Vector3(0, 0.013, 0).applyAxisAngle(ZAX, q.rz).add(new T.Vector3(q.x, q.y, q.z))); }
  plugApply(0);
  function setKey(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!!on === st.key) return Promise.resolve();
    var a = st.key ? 1 : 0, b = on ? 1 : 0;
    if (!on) { st.key = false; solve(); }
    return S.hand.pinchMove(plugHead(a), function (k) { return plugHead(a + (b - a) * k); }, function (k) { plugApply(a + (b - a) * k); }, { ms: 900, mode: 'top' })
      .then(function () { plugApply(b); st.key = !!on; solve(); S.click(1400, 0.04, 0.1);
        S.say(on ? 'Key closed: current flows. The ammeter and voltmeter needles move.' : 'Key open: no current. Both needles return to zero.'); S.render(); });
  }

  // ---------- ammeter (series) and voltmeter (across the coil)
  var am = S.meter({ min: 0, max: AMAX, ticks: AMAX === 0.5 ? 5 : AMAX === 1 ? 10 : AMAX === 3 ? 6 : AMAX === 5 ? 5 : 4, unit: 'A', symbol: 'A', caption: 'DC AMMETER 0–' + fmtN(AMAX) + ' A', pos: [-0.16, 0, -0.22] });
  var vm = S.meter({ min: 0, max: VMAX, ticks: VMAX === 1 ? 10 : VMAX === 3 ? 6 : 5, unit: 'V', symbol: 'V', caption: 'DC VOLTMETER 0–' + VTXT, pos: [0.3, 0, -0.73] });
  var amP = { at: wpt(am, 0.035, 0.07, -0.03) }, amM = { at: wpt(am, -0.035, 0.07, -0.03) };
  var vmP = { at: wpt(vm, 0.035, 0.07, -0.03) }, vmM = { at: wpt(vm, -0.035, 0.07, -0.03) };

  // ---------- rheostat (variable resistor: end A + the sliding contact's bar C)
  var RHP = [0.25, -0.16];
  var rh = S.rheostat([RHP[0], 0, RHP[1]], RH_LEN);
  var rhA = post(RHP[0] - RH_LEN / 2 - 0.008, 0.05, RHP[1]), rhB = post(RHP[0] + RH_LEN / 2 + 0.008, 0.05, RHP[1]);
  var rhC = post(RHP[0] + RH_LEN / 2 - 0.004, 0.065, RHP[1]);
  var rhPlate = S.label('RHEOSTAT 20 Ω · 2 A', { w: 0.08, ratio: 0.16, color: '#f3ead2', bg: '#2b2b2b' }); rhPlate.position.set(RHP[0] + RH_LEN / 2, 0.025, RHP[1] + 0.0105); S.scene.add(rhPlate);
  ['A', 'B'].forEach(function (t, i) { var l = S.label(t, { w: 0.012, ratio: 1, color: '#f3ead2' }); l.position.set(RHP[0] + (i ? 1 : -1) * RH_LEN / 2, 0.038, RHP[1] + 0.0105); S.scene.add(l); });
  var slider = rh.userData.slider;
  function sliderTop(f) { return rh.localToWorld(new T.Vector3(-RH_LEN / 2 + 0.02 + f * (RH_LEN - 0.04), 0.074, 0)); }
  function setF(f) { st.f = Math.max(0, Math.min(1, f)); rh.setFraction(st.f); solve(); }
  setF(1);
  function slide(target) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    target = Math.max(0, Math.min(1, target)); st.target = target; var f0 = st.f;
    if (Math.abs(target - f0) < 1e-6) return Promise.resolve();
    return S.hand.pinchMove(sliderTop(f0), function (k) { return sliderTop(f0 + (target - f0) * k); }, function (k) { setF(f0 + (target - f0) * k); },
      { ms: 500 + Math.abs(target - f0) * 1400, mode: 'top' }).then(function () { setF(target); S.render(); });
  }

  // ---------- the resistance wire: a coil wound on a porcelain former, mounted on a wooden board with two terminals
  var CB = [0.3, -0.52], CL = 0.17;
  var coil = new T.Group(); S.scene.add(coil);
  var cbase = S.rounded(CL + 0.09, 0.08, 0.016, 0.006, M.darkWood); cbase.rotation.x = -Math.PI / 2; cbase.position.set(0, 0.008, 0); coil.add(cbase);
  [-1, 1].forEach(function (s) { var sp = S.rounded(0.014, 0.02, 0.022, 0.003, M.white); sp.position.set(s * (CL / 2 + 0.006), 0.026, 0); coil.add(sp); });
  var former = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, CL + 0.02, 28), M.white); former.rotation.z = Math.PI / 2; former.position.y = 0.034; coil.add(former);
  var hpts = [], turns = 26;
  for (var i = 0; i <= turns * 24; i++) { var t = i / (turns * 24), a = t * turns * Math.PI * 2; hpts.push(new T.Vector3(-CL / 2 + 0.006 + t * (CL - 0.012), 0.034 + 0.0095 * Math.cos(a), 0.0095 * Math.sin(a))); }
  var wireCol = /nichrome/i.test(SAMPLE) ? 0xb4b2ae : /constantan|eureka/i.test(SAMPLE) ? 0xc9b49a : /manganin/i.test(SAMPLE) ? 0xb08f72 : 0xb7a48c;
  var wireM = new T.MeshStandardMaterial({ color: wireCol, roughness: 0.28, metalness: 0.9 });
  coil.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3(hpts), turns * 24, 0.0009, 6, false), wireM));
  var cT1x = -(CL / 2 + 0.03), cT2x = CL / 2 + 0.03;
  [[hpts[0], cT1x], [hpts[hpts.length - 1], cT2x]].forEach(function (e) { var s0 = e[0];
    var c = new T.CatmullRomCurve3([s0.clone(), new T.Vector3(s0.x + Math.sign(e[1]) * 0.008, 0.03, s0.z + 0.004), new T.Vector3(e[1], 0.026, 0.002)]);
    coil.add(S.mesh(new T.TubeGeometry(c, 16, 0.0009, 6, false), wireM)); });
  var ctag = SAMPLE ? S.label(SAMPLE + '  ·  R unknown', { w: 0.17, ratio: Math.min(0.09, 2.4 / (SAMPLE.length + 13)), px: 1024, color: '#f3ead2' }) : S.label('R  (unknown)', { w: 0.07, ratio: 0.2, color: '#f3ead2' });
  ctag.rotation.x = -Math.PI / 2; ctag.position.set(0, 0.0165, 0.028); coil.add(ctag);
  coil.position.set(CB[0], 0, CB[1]); S.contact(CL + 0.16, 0.14, CB[0], CB[1], 0.5);
  var cT1 = post(CB[0] + cT1x, 0.016, CB[1] + 0.002), cT2 = post(CB[0] + cT2x, 0.016, CB[1] + 0.002);

  // ---------- leads: the true series circuit + the voltmeter in parallel with the coil
  lead(pbPlus.at, kL.at, 'red', [[-0.6, -0.36], [-0.5, -0.24]]);
  lead(kR.at, amP.at, 'red', [[-0.36, -0.235], [-0.14, -0.27]]);
  lead(amM.at, rhA.at, 'yellow', [[-0.2, -0.29], [0.0, -0.24], [0.08, -0.17]]);
  lead(rhC.at, cT2.at, 'yellow', [[0.4, -0.3], [0.42, -0.45]], 0.01);
  lead(cT1.at, pbMinus.at, 'black', [[0.14, -0.6], [-0.2, -0.62], [-0.6, -0.6]]);
  lead(vmP.at, cT2.at, 'red', [[0.37, -0.68], [0.42, -0.6]]);
  lead(vmM.at, cT1.at, 'black', [[0.22, -0.68], [0.16, -0.58]]);

  S.addApparatus('pb', pb, 'Battery eliminator (' + fmtN(EB) + ' V DC)', 'Gives a steady ' + fmtN(EB) + ' V. Its + terminal (red) goes towards the key and the ammeter\'s + terminal.');
  S.addApparatus('key', key, 'Plug key K', 'Closes the circuit when the brass plug is pushed in. Take it out between readings so the wire does not heat up.');
  S.addApparatus('am', am, 'Ammeter (0–' + fmtN(AMAX) + ' A)', 'Connected in series, + to the battery side. Very low resistance. Least count ' + fmtN(ARES * 2) + ' A; read to ' + fmtN(ARES) + ' A.');
  S.addApparatus('rh', rh, 'Rheostat (20 Ω)', 'A variable resistor in series. Sliding the contact changes the current in the circuit.');
  S.addApparatus('coil', coil, SAMPLE ? 'Resistance wire: ' + SAMPLE : 'Resistance wire (coil)', 'The unknown resistance R: a coil of resistance wire between two terminals.');
  S.addApparatus('vm', vm, 'Voltmeter (0–' + VTXT + ')', 'Connected in parallel across the coil. Very high resistance, so it takes almost no current.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // the record book moves to the front right (book.at): drop the engine's shadow left at its default place
  S.scene.children.slice().forEach(function (o) { if (o.isMesh && o.material && o.material.isMeshBasicMaterial && o.material.transparent && Math.abs(o.position.x + 0.5) < 1e-6 && Math.abs(o.position.z - 0.08) < 1e-6) S.scene.remove(o); });
  var hudI = S.hudCard('Ammeter I'), hudV = S.hudCard('Voltmeter V'), hudK = S.hudCard('Key');
  solve();

  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.key) { S.say('The key is open, so no current flows. Insert the plug key first.'); return false; }
    var i = +fI(I()), v = +fV(V());
    if (i <= 0) { S.say('The ammeter reads zero. Check the key.'); return false; }
    if (I() > AMAX * 1.02) { S.say('The ammeter is beyond its range (' + fmtN(AMAX) + ' A). Slide the contact back towards end B.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.I - i) < ARES / 2; })) { S.say('You already have a reading at I = ' + i.toFixed(IDIG) + ' A. Move the rheostat contact for a new current.'); return false; }
    if (S.rows.length >= 12) { S.say('Twelve readings are plenty. Go on to the graph.'); return false; }
    S.addRow({ V: v, I: i });
    S.say('Written in your record book: V = ' + v.toFixed(2) + ' V, I = ' + i.toFixed(IDIG) + ' A.');
    return true;
  }
  function trace() { st.traced = true; S.focus('am'); S.say((SAMPLE ? 'The coil is ' + SAMPLE + '. ' : '') + 'Battery +, key, ammeter (+ to −), rheostat, coil, back to battery −: all in series. The voltmeter is across the coil, + to the side the current enters.'); S.render(); }
  function zeroCheck() {
    if (st.key) { S.say('Take the key out first: zero is checked with no current.'); return; }
    st.zero = true; S.focus('vm'); S.say('With the key open both needles rest exactly on zero: no zero error.'); S.render();
  }

  return {
    camera: { pos: [0.06, 1.2, 1.3], look: [0.06, 0.0, -0.33] },
    views: { pb: [[-0.48, 0.38, 0.0], [-0.64, 0.05, -0.48]], key: [[-0.36, 0.3, 0.12], [-0.44, 0.02, -0.2]], am: [[-0.12, 0.3, 0.12], [-0.16, 0.04, -0.23]],
      rh: [[0.32, 0.36, 0.2], [0.25, 0.04, -0.17]], coil: [[0.36, 0.34, -0.15], [0.3, 0.02, -0.53]], vm: [[0.34, 0.36, -0.38], [0.3, 0.04, -0.72]],
      circuit: [[0.06, 1.2, 1.3], [0.06, 0.0, -0.33]], work: [[0.1, 0.85, 0.72], [0.06, 0.0, -0.4]], book: [[0.6, 0.44, 0.52], [0.66, 0.0, 0.08]] },
    theory: { principle: 'At a constant temperature the current I through a metallic conductor is proportional to the potential difference V across it. The ratio V / I is its resistance R.',
      formula: 'V = I R', formulaNote: 'so R = V / I = slope of the V–I graph',
      more: ['The ammeter goes in series with the conductor (very low resistance); the voltmeter goes in parallel across it (very high resistance). The rheostat changes the current, and for each setting you record V and I. A graph of V against I is a straight line through the origin.'],
      precautions: 'Connections must be tight and clean. The + terminals of both meters go towards the + of the battery. Start with the rheostat at its maximum resistance. Take the plug out of the key between readings so the wire does not heat up.' },
    book: { title: "Expt. — Ohm's law", at: [0.66, 0.08, -0.1],
      lines: ['Aim: to verify Ohm\'s law and find R of the given wire.'].concat(SAMPLE ? ['Wire: ' + SAMPLE] : []).concat([ 'Ammeter: 0–' + fmtN(AMAX) + ' A, read to ' + fmtN(ARES) + ' A', 'Voltmeter: 0–' + VTXT + ', read to ' + fmtN(VRES < 0.01 ? 0.01 : VRES) + ' V', 'R = V / I  = slope of V–I graph', 'Precautions: start at max rheostat R,', 'key out between readings.']),
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'I (A)', get: function (r) { return r.I.toFixed(IDIG); } },
        { label: 'V (V)', get: function (r) { return r.V.toFixed(2); } }, { label: 'V/I (Ω)', get: function (r) { return (r.V / r.I).toFixed(2); } }] },
    graph: { x: function (r) { return r.I; }, y: function (r) { return r.V; }, xlabel: 'I (A)', ylabel: 'V (V)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) { if (rows.length < 3) return null; var k = S.fit.origin(rows.map(function (r) { return [r.I, r.V]; }));
      return { label: 'R', value: k, unit: 'Ω', digits: 2, truth: p.Rx, note: 'From the slope of the V–I graph (a straight line through the origin).' }; },
    tol: 0.02,
    chips: ['Why is the ammeter in series?', 'Why does the graph pass through the origin?', 'What does the rheostat do?', 'Check my readings', 'Why should the key be removed between readings?'],
    viva: [['Why should the voltmeter have a very high resistance?', ['So it draws almost no current from the circuit', 'So it reads larger voltages', 'So the ammeter reads correctly only then'], 0, 'A voltmeter in parallel must not change the current it is measuring across.'],
      ['The V–I graph of a metallic wire at constant temperature is', ['A straight line through the origin', 'A curve bending upwards', 'A horizontal line'], 0, 'V is proportional to I, so the graph is a straight line through the origin.']],
    askState: function () { return { key_closed: st.key, rheostat_contact_percent: Math.round(st.f * 100), ammeter_A: +fI(I()), voltmeter_V: +fV(V()),
      ammeter_range: '0-' + fmtN(AMAX) + ' A', voltmeter_range: '0-' + VTXT, battery_V: EB, wire: SAMPLE || 'resistance wire coil', readings_taken: S.rows.length }; },

    steps: [
      { id: 'check', title: 'Check circuit', view: 'circuit', render: function (u) {
          u.h2('Check the circuit');
          u.p('The circuit is wired on the bench. Before switching on, check it as your teacher would.');
          u.task('1. Trace the circuit', st.traced, st.traced ? 'Battery → key → ammeter → rheostat → coil → battery; voltmeter across the coil' : 'Follow the leads from the battery + terminal')
            .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
          u.task('2. Check the zero of both meters', st.zero, st.zero ? 'Both needles on zero: no zero error' : 'With the key open, both needles must rest on zero')
            .add(u.button(st.zero ? 'Checked' : 'Check the zeros', zeroCheck, !st.zero, st.zero));
          u.note('The ammeter is in series and the voltmeter in parallel. Both + terminals (red) face the battery\'s + side.');
          u.next('Next: close the key', st.traced && st.zero);
        },
        ok: function () { return st.traced && st.zero; },
        auto: function () { trace(); zeroCheck(); return Promise.resolve(); } },
      { id: 'key', title: 'Close the key', view: 'key', render: function (u) {
          u.h2('Close the key');
          u.p('The rheostat contact is at end B, so the full 20 Ω is in the circuit and the first current is small. Now let the hand push the brass plug into the key.');
          u.task('Insert the plug key', st.key, st.key ? 'Key closed: current is flowing' : 'Key open').add(u.row(
            u.button(st.key ? 'Key is in' : 'Insert the plug', function () {
              if (st.f < 0.9) { S.say('Slide the rheostat contact back to end B (maximum resistance) before closing the key.'); return; }
              setKey(true); }, true, st.key || S.hand.busy)));
          u.live(function () { return 'Ammeter ' + fI(I()) + ' A · Voltmeter ' + fV(V()) + ' V'; });
          u.next('Next: take readings', st.key);
        },
        ok: function () { return st.key; },
        auto: function () { setF(1); return setKey(true); } },
      { id: 'readings', title: 'Take readings', view: 'work', render: function (u) {
          u.h2('Record V and I');
          u.p('Choose where the sliding contact should go, let the hand slide it, then read both meters and record. Take at least 5 readings at different currents.');
          u.slider('Sliding contact from end A', 0, 100, 1, function () { return Math.round(st.target * 100); }, function (v) { st.target = v / 100; }, '%', 0);
          u.row(u.button('Slide the contact', function () { slide(st.target); }, true, S.hand.busy),
            u.button(st.key ? 'Take the key out' : 'Insert the key', function () { setKey(!st.key); }, false, S.hand.busy));
          u.live(function () { return 'Contact at ' + Math.round(st.f * 100) + '% · Ammeter ' + fI(I()) + ' A · Voltmeter ' + fV(V()) + ' V'; });
          u.row(u.button('Record this reading', function () { record(); }, true, !st.key));
          u.note('Moving the contact towards end A puts less of the rheostat in the circuit, so the current rises. Keep I under ' + fmtN(0.6 * AMAX) + ' A.');
          u.h3('Observation table'); u.table();
          u.next('Next: plot V against I', S.rows.length >= 5);
          if (S.rows.length < 5) u.p(S.rows.length + ' of at least 5 readings recorded.');
        },
        ok: function () { return S.rows.length >= 5; },
        auto: function () {
          return [0.95, 0.7, 0.5, 0.35, 0.2, 0.1].reduce(function (pr, f) { return pr.then(function () {
            return (st.key ? Promise.resolve() : setKey(true)).then(function () { return slide(f); }).then(function () { S.advance(0.3); record(); }); }); }, Promise.resolve()); } },
    ],

    tick: function () {
      solve();
      am.set(I()); vm.set(V());
      lamp.material.emissive.setRGB(0.9, 0.08, 0.04);
      hudI.set(fI(I()) + ' A'); hudV.set(fV(V()) + ' V'); hudK.set(st.key ? 'Closed' : 'Open');
    },
  };
});
