/* Prayogshala studio rig: two resistors in series or in parallel (NCERT Science X laboratory manual).
   The same board serves both set-ups: a battery, a plug key, a rheostat and an ammeter in the main line, two
   resistance coils on a mounting board, and a voltmeter across the pair. Which way the coils are linked is read
   from the lab, and every reading comes from the circuit kernel (MNA) run on the lab's own netlist. */
HoolaStudio.define('resistors-combination', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.circuit, CFG = S.lab.cfg;
  var p = window.HoolaKernels.paramsFor('circuit', S.lab.params);
  var V_ = S.lab.variant || {}, BASE = V_.base || S.lab.id, SAMPLE = V_.sample || '';
  var SER = BASE !== 'parallel-resistors';
  var R1 = p.R1, R2 = p.R2, REQ = SER ? R1 + R2 : R1 * R2 / (R1 + R2);
  var RH_MIN = 0.5, RH_MAX = 30, RH_LEN = 0.28;
  function pick(list, need) { for (var i = 0; i < list.length; i++) if (list[i] >= need - 1e-9) return list[i]; return list[list.length - 1]; }
  var IMAX = p.Eb / (REQ + RH_MIN), AMAX = pick([0.05, 0.1, 0.2, 0.5, 1, 1.5, 2, 3], IMAX * 1.25), VMAX = pick([1, 3, 5], p.Eb);
  var ARES = AMAX / 100, VRES = VMAX / 300, IDIG = ARES < 0.005 ? 4 : 3;
  function fmtN(v, d) { return String(+v.toFixed(d === undefined ? 2 : d)); }
  var st = { key: false, rh: RH_MAX, target: RH_MAX, traced: false, zero: false };
  var view = {};
  function solve() { p.key = st.key ? 1 : 0; p.Rh = st.rh; view = K.view(K.init(p, CFG), p, CFG); }
  function I() { return st.key ? view.I_AM : 0; }
  function Vr() { return st.key ? view.V_VM : 0; }
  function fI(v) { return (Math.round(v / ARES) * ARES).toFixed(IDIG); }
  function fV(v) { return (Math.round(v / VRES) * VRES).toFixed(2); }

  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }

  // ---------- supply, key, rheostat, ammeter
  var PB = [-0.6, -0.1];
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
  function setKey(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!!on === st.key) return Promise.resolve();
    var a = st.key ? 1 : 0, b = on ? 1 : 0;
    if (!on) { st.key = false; solve(); }
    return S.hand.pinchMove(plugHead(a), function (k) { return plugHead(a + (b - a) * k); }, function (k) { plugApply(a + (b - a) * k); },
      { ms: 850, mode: 'top' }).then(function () {
        plugApply(b); st.key = !!on; solve(); S.click(1500, 0.04, 0.09);
        S.say(on ? 'Key closed: the ammeter and the voltmeter both read.' : 'Key open: no current, so the coils stay cool.');
        S.render();
      });
  }

  var RHP = [-0.06, 0.02];
  var rh = S.rheostat([RHP[0], 0, RHP[1]], RH_LEN);
  var rhA = post(RHP[0] - RH_LEN / 2 - 0.01, 0.05, RHP[1], 'red'), rhC = post(RHP[0] + RH_LEN / 2 - 0.006, 0.065, RHP[1], 'black');
  var rhPlate = S.label('RHEOSTAT ' + RH_MAX + ' Ω', { w: 0.07, ratio: 0.16, color: '#f3ead2', bg: '#2b2b2b' });
  rhPlate.position.set(RHP[0] + RH_LEN / 2 - 0.035, 0.025, RHP[1] + 0.0105); S.scene.add(rhPlate);
  function rhF(r) { return (RH_MAX - r) / (RH_MAX - RH_MIN); }
  function sliderTop(f) { return rh.localToWorld(new T.Vector3(-RH_LEN / 2 + 0.02 + f * (RH_LEN - 0.04), 0.074, 0)); }
  function setRh(r) { st.rh = Math.max(RH_MIN, Math.min(RH_MAX, r)); rh.setFraction(rhF(st.rh)); solve(); }
  setRh(RH_MAX);
  function slide(target) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    target = Math.max(RH_MIN, Math.min(RH_MAX, target)); st.target = target;
    var r0 = st.rh; if (Math.abs(target - r0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(sliderTop(rhF(r0)), function (k) { return sliderTop(rhF(r0 + (target - r0) * k)); },
      function (k) { setRh(r0 + (target - r0) * k); }, { ms: 600 + Math.abs(rhF(target) - rhF(r0)) * 1100, mode: 'top' })
      .then(function () { setRh(target); S.render(); });
  }

  var am = S.meter({ min: 0, max: AMAX, ticks: AMAX === 0.05 ? 5 : AMAX === 0.1 ? 10 : AMAX === 0.2 ? 4 : AMAX === 0.5 ? 5 : AMAX === 1 ? 10 : 6, unit: 'A', symbol: 'A',
    caption: 'DC AMMETER 0–' + fmtN(AMAX) + ' A', pos: [0.3, 0, -0.06] });
  var vm = S.meter({ min: 0, max: VMAX, ticks: VMAX === 1 ? 10 : VMAX === 3 ? 6 : 5, unit: 'V', symbol: 'V',
    caption: 'DC VOLTMETER 0–' + fmtN(VMAX) + ' V', pos: [0.08, 0, -0.52] });
  var amP = { at: wpt(am, 0.035, 0.07, -0.03) }, amM = { at: wpt(am, -0.035, 0.07, -0.03) };
  var vmP = { at: wpt(vm, 0.035, 0.07, -0.03) }, vmM = { at: wpt(vm, -0.035, 0.07, -0.03) };

  // ---------- the two resistance coils on their mounting board
  var CB = [-0.3, -0.42], GAP = 0.26;
  var cboard = S.rounded(0.46, 0.17, 0.016, 0.005, M.darkWood); cboard.rotation.x = -Math.PI / 2; cboard.position.set(CB[0], 0.008, CB[1]); S.scene.add(cboard);
  S.contact(0.52, 0.23, CB[0], CB[1], 0.45);
  var coilT = [];
  [[-1, R1, '1'], [1, R2, '2']].forEach(function (q, idx) {
    var cx = CB[0] + q[0] * GAP / 2, CL = 0.11;
    var g = new T.Group(); S.scene.add(g); g.position.set(cx, 0.016, CB[1]);
    [-1, 1].forEach(function (s) { var sp = S.rounded(0.012, 0.018, 0.02, 0.002, M.white); sp.position.set(s * (CL / 2 + 0.005), 0.022, 0); g.add(sp); });
    var former = S.mesh(new T.CylinderGeometry(0.0075, 0.0075, CL + 0.014, 24), M.white); former.rotation.z = Math.PI / 2; former.position.y = 0.028; g.add(former);
    var pts = [], turns = 18;
    for (var i = 0; i <= turns * 20; i++) {
      var t = i / (turns * 20), a = t * turns * Math.PI * 2;
      pts.push(new T.Vector3(-CL / 2 + t * CL, 0.028 + 0.0085 * Math.cos(a), 0.0085 * Math.sin(a)));
    }
    g.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts), turns * 20, 0.0008, 6, false),
      new T.MeshStandardMaterial({ color: 0xb4b2ae, roughness: 0.3, metalness: 0.88 })));
    var tag = S.label('R' + q[2] + ' = ' + fmtN(q[1], 1) + ' Ω', { w: 0.07, ratio: 0.2, color: '#f3ead2', bg: '#2b2b2b', px: 512 });
    tag.rotation.x = -Math.PI / 2; tag.position.set(0, 0.0005, 0.045); g.add(tag);
    coilT.push({ g: g, L: post(cx - CL / 2 - 0.026, 0.016, CB[1] - 0.052, idx === 0 ? 'red' : 'brass'),
      R: post(cx + CL / 2 + 0.026, 0.016, CB[1] - 0.052, idx === 1 ? 'black' : 'brass') });
  });

  // the links that make it a series or a parallel combination
  if (SER) {
    lead(coilT[0].R.at, coilT[1].L.at, 'yellow', [[CB[0], -0.5]], 0.01);
  } else {
    lead(coilT[0].L.at, coilT[1].L.at, 'yellow', [[CB[0], -0.56]], 0.012);
    lead(coilT[0].R.at, coilT[1].R.at, 'yellow', [[CB[0], -0.3]], 0.012);
  }
  var inT = coilT[0].L, outT = SER ? coilT[1].R : coilT[1].R;

  // ---------- the leads of the main circuit
  lead(pbPlus.at, kL.at, 'red', [[-0.52, -0.16], [-0.44, -0.08]]);
  lead(kR.at, rhA.at, 'red', [[-0.26, -0.08], [-0.22, -0.01]]);
  lead(rhC.at, amP.at, 'red', [[0.12, 0.0], [0.26, -0.05]]);
  lead(amM.at, outT.at, 'yellow', [[0.2, -0.2], [-0.02, -0.34]]);
  lead(inT.at, pbMinus.at, 'black', [[-0.56, -0.52], [-0.66, -0.3]]);
  lead(vmP.at, outT.at, 'red', [[0.0, -0.46], [-0.1, -0.4]]);
  lead(vmM.at, inT.at, 'black', [[-0.08, -0.5], [-0.42, -0.46]]);

  S.addApparatus('pb', pb, 'Battery eliminator (' + fmtN(p.Eb, 1) + ' V)', 'A steady low-voltage supply for the circuit.');
  S.addApparatus('key', key, 'Plug key K', 'Closes the circuit. Take the plug out between readings so the coils do not warm up and change their resistance.');
  S.addApparatus('rh', rh, 'Rheostat', 'Changes the current so that several pairs of readings can be taken.');
  S.addApparatus('am', am, 'Ammeter (0–' + fmtN(AMAX) + ' A)', 'In the main line, so it reads the whole current drawn by the combination.');
  S.addApparatus('coils', coilT[0].g, 'Resistance coils R1 and R2', SER
    ? 'Joined end to end: the same current passes through both, one after the other.'
    : 'Both ends of R1 joined to both ends of R2: each has the whole potential difference across it.');
  S.addApparatus('vm', vm, 'Voltmeter (0–' + fmtN(VMAX) + ' V)', 'Across the combination. Its resistance is very high, so it takes almost no current.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudI = S.hudCard('Ammeter'), hudV = S.hudCard('Voltmeter'), hudR = S.hudCard('V / I');
  solve();

  function trace() {
    st.traced = true; S.focus('coils');
    S.say(SER ? 'R1 and R2 are joined end to end, and the ammeter is in the same line: one current through both.'
      : 'Both ends of R1 are joined to both ends of R2, so the same potential difference is across each, and the ammeter reads the two currents together.');
    S.render();
  }
  function zeroCheck() {
    if (st.key) { S.say('Take the key out first: the zeros are checked with no current.'); return; }
    st.zero = true; S.focus('am'); S.say('With the key out both needles rest exactly on zero: there is no zero error.'); S.render();
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.key) { S.say('The key is open, so no current flows. Insert the plug first.'); return false; }
    var i = +fI(I()), v = +fV(Vr());
    if (i <= 0) { S.say('The ammeter reads zero. Check the key.'); return false; }
    if (I() > AMAX * 1.02) { S.say('The ammeter is past its range. Put more of the rheostat in.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.I - i) < ARES / 2; })) { S.say('There is already a reading at I = ' + i.toFixed(IDIG) + ' A. Move the rheostat contact.'); return false; }
    if (S.rows.length >= 12) { S.say('Twelve readings are plenty. Go on to the graph.'); return false; }
    S.addRow({ I: i, V: v });
    S.say('Written in your record book: I = ' + i.toFixed(IDIG) + ' A, V = ' + v.toFixed(2) + ' V, so V / I = ' + (v / i).toFixed(2) + ' Ω.');
    return true;
  }

  return {
    camera: { pos: [0.0, 1.18, 0.5], look: [-0.06, 0.0, -0.26] },
    views: { pb: [[-0.5, 0.32, 0.06], [-0.6, 0.04, -0.12]], key: [[-0.3, 0.24, 0.1], [-0.34, 0.02, -0.02]],
      rh: [[-0.04, 0.3, 0.2], [-0.06, 0.04, 0.0]], am: [[0.3, 0.26, 0.16], [0.3, 0.04, -0.07]],
      coils: [[-0.3, 0.3, -0.14], [-0.3, 0.02, -0.44]], vm: [[0.08, 0.3, -0.2], [0.08, 0.04, -0.53]],
      circuit: [[0.0, 1.18, 0.5], [-0.06, 0.0, -0.26]], work: [[0.0, 0.82, 0.24], [-0.06, 0.0, -0.3]],
      book: [[-0.5, 0.45, 0.6], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: SER
        ? 'Joined in series, the two resistors carry the same current and their potential differences add: V = I R1 + I R2. '
          + 'So the pair behaves as a single resistor Rs = R1 + R2, larger than either of them.'
        : 'Joined in parallel, both resistors have the same potential difference and their currents add: I = V/R1 + V/R2. '
          + 'So 1/Rp = 1/R1 + 1/R2, and the pair behaves as a single resistor smaller than either of them.',
      formula: SER ? 'R_s = R₁ + R₂' : '1/R_p = 1/R₁ + 1/R₂',
      formulaNote: 'and the measured value is R = V / I, the slope of the V–I graph',
      more: [SER ? 'That is why the resistances of a torch bulb, the leads and the cell’s own internal resistance all add up to limit the current.'
        : 'Giving the current a second road always makes it easier for it to pass, so the equivalent resistance of a parallel pair is always less than the smaller one. '
          + 'That is why the appliances in a house are wired in parallel: each gets the full supply voltage and can be switched on its own.',
        'Take several pairs of readings at different currents. The V–I graph is a straight line through the origin and its slope is the equivalent resistance.'],
      precautions: 'Connections must be tight and clean, both + terminals must face the + of the supply, and the plug must come out of the key between readings: '
        + 'a warm coil is a different resistance.' },
    book: { title: 'Expt. — Resistors in ' + (SER ? 'series' : 'parallel'),
      lines: ['Aim: ' + S.lab.aim].concat(SAMPLE ? ['Coils: ' + SAMPLE] : [])
        .concat(['R₁ = ' + fmtN(R1, 1) + ' Ω,  R₂ = ' + fmtN(R2, 1) + ' Ω',
          'Ammeter 0–' + fmtN(AMAX) + ' A, read to ' + fmtN(ARES, 3) + ' A', 'Voltmeter 0–' + fmtN(VMAX) + ' V',
          'R = V / I = slope of the V–I graph',
          SER ? 'Expected: R₁ + R₂' : 'Expected: R₁R₂/(R₁+R₂)']),
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'I (A)', get: function (r) { return r.I.toFixed(IDIG); } },
        { label: 'V (V)', get: function (r) { return r.V.toFixed(2); } },
        { label: 'V/I (Ω)', get: function (r) { return (r.V / r.I).toFixed(2); } }] },
    graph: { x: function (r) { return r.I; }, y: function (r) { return r.V; }, xlabel: 'I (A)', ylabel: 'V (V)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) {
      if (rows.length < 4) return null;
      var k = S.fit.origin(rows.map(function (r) { return [r.I, r.V]; }));
      return { label: SER ? 'Equivalent resistance in series' : 'Equivalent resistance in parallel', value: k, unit: 'Ω', digits: 2,
        truth: REQ, note: 'Slope of the V–I graph, to be compared with ' + (SER ? 'R₁ + R₂ = ' : 'R₁R₂/(R₁+R₂) = ') + fmtN(REQ) + ' Ω.' };
    },
    tol: 0.03,
    resultNote: SER ? 'The pair came out larger than either coil: in series the resistances simply add.'
      : 'The pair came out smaller than either coil: a second road for the current always makes the resistance less.',
    chips: ['Why is the ammeter in the main line?', SER ? 'Why do the voltages add?' : 'Why do the currents add?',
      'What would three such coils give?', 'Check my readings', 'Why take the key out between readings?'],
    viva: [[SER ? 'Three 10 Ω coils in series behave as' : 'Two 10 Ω coils in parallel behave as',
      SER ? ['30 Ω', '10 Ω', '3.3 Ω'] : ['5 Ω', '20 Ω', '10 Ω'], 0,
      SER ? 'In series the resistances add.' : '1/Rp = 1/10 + 1/10 = 1/5.'],
    ['Why are the lights and fans of a house wired in parallel?',
      ['Each gets the full supply voltage and can be switched separately', 'It saves wire', 'It makes the current smaller'], 0,
      'In series one switch would turn everything off and each appliance would get only part of the voltage.']],
    askState: function () {
      return { combination: SER ? 'series' : 'parallel', key_closed: st.key, rheostat_ohm: +fmtN(st.rh, 1),
        ammeter_A: +fI(I()), voltmeter_V: +fV(Vr()), R1_ohm: R1, R2_ohm: R2,
        measured_R_ohm: I() > 0 ? +(Vr() / I()).toFixed(2) : null, readings_taken: S.rows.length };
    },
    steps: [
      { id: 'check', title: 'Check the circuit', view: 'circuit', render: function (u) {
          u.h2('Check the circuit');
          u.p('The two coils are already linked ' + (SER ? 'in series' : 'in parallel') + ' on their board. Check the circuit before switching on.');
          u.task('1. Trace the circuit', st.traced, st.traced ? (SER ? 'One current through both coils' : 'The same voltage across both coils') : 'Follow the leads from the supply’s + terminal')
            .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
          u.task('2. Check the meter zeros', st.zero, st.zero ? 'Both needles on zero' : 'With the key open both needles must rest on zero')
            .add(u.button(st.zero ? 'Checked' : 'Check the zeros', zeroCheck, !st.zero, st.zero));
          u.note('Start with the rheostat at its full ' + RH_MAX + ' Ω so the first current is small.');
          u.next('Next: close the key', st.traced && st.zero);
        },
        ok: function () { return st.traced && st.zero; },
        auto: function () { trace(); zeroCheck(); return Promise.resolve(); } },
      { id: 'on', title: 'Close the key', view: 'am', render: function (u) {
          u.h2('Close the key');
          u.p('The hand pushes the brass plug into the key. Both needles move together.');
          u.task('Insert the plug', st.key, st.key ? 'Key closed: current is flowing' : 'Key open')
            .add(u.row(u.button(st.key ? 'Key is in' : 'Insert the plug', function () { setKey(true); }, true, st.key || S.hand.busy),
              u.button('Take the plug out', function () { setKey(false); }, false, !st.key || S.hand.busy)));
          u.live(function () { return 'Ammeter ' + fI(I()) + ' A  ·  voltmeter ' + fV(Vr()) + ' V'; });
          u.next('Next: take the readings', st.key);
        },
        ok: function () { return st.key; },
        auto: function () { return setKey(true); } },
      { id: 'read', title: 'Take the readings', view: 'work', render: function (u) {
          u.h2('Read V and I at several currents');
          u.p('Move the rheostat contact, read both meters and record. Take at least four readings at different currents.');
          u.slider('Rheostat resistance', RH_MIN, RH_MAX, 0.5, function () { return st.target; }, function (v) { st.target = v; }, 'Ω', 1);
          u.row(u.button('Slide the contact', function () { slide(st.target); }, true, S.hand.busy),
            u.button(st.key ? 'Take the plug out' : 'Insert the plug', function () { setKey(!st.key); }, false, S.hand.busy));
          u.live(function () { return 'Rheostat ' + fmtN(st.rh, 1) + ' Ω  ·  I ' + fI(I()) + ' A  ·  V ' + fV(Vr()) + ' V  ·  V/I ' + (I() > 0 ? (Vr() / I()).toFixed(2) : '—') + ' Ω'; });
          u.row(u.button('Record this reading', function () { record(); }, true, !st.key || S.hand.busy));
          u.h3('Observation table'); u.table();
          if (S.rows.length < 4) u.p(S.rows.length + ' of at least 4 readings recorded.');
          u.next('Next: plot V against I', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          return [RH_MAX, RH_MAX * 0.6, RH_MAX * 0.3, RH_MAX * 0.12, RH_MIN].reduce(function (pr, r) {
            return pr.then(function () { return slide(r).then(function () { S.advance(0.2); record(); }); });
          }, st.key ? Promise.resolve() : setKey(true));
        } },
    ],
    tick: function () {
      solve(); am.set(I()); vm.set(Vr());
      hudI.set(fI(I()) + ' A'); hudV.set(fV(Vr()) + ' V');
      hudR.set(I() > 0 ? (Vr() / I()).toFixed(2) + ' Ω' : '—');
    },
  };
});
