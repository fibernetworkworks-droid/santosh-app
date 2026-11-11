/* Prayogshala studio rig: what the resistance of a wire depends on (NCERT Science X, Electricity).
   A metre of resistance wire is stretched over a metre scale on a wooden board; a sliding clamp takes off whatever
   length is wanted, and that length is measured with an ammeter and a voltmeter in a real circuit. The wire's
   resistance comes from the `wirecircuit` kernel - R = rho L / A fed into the same MNA solver the server checks. */
HoolaStudio.define('resistance-factors', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KW = HK.K.wirecircuit;
  var p = HK.paramsFor('wirecircuit', S.lab.params);
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || '';
  var AREA = Math.PI * p.dia * p.dia / 4, L0 = p.Lw, LMIN = 0.2, LMAX = 1.0;
  var RH_MIN = 0.5, RH_MAX = 20, RH_LEN = 0.26;
  function Rw(L) { return p.rho * L / AREA; }
  function pick(list, need) { for (var i = 0; i < list.length; i++) if (list[i] >= need - 1e-9) return list[i]; return list[list.length - 1]; }
  var IMAX = p.Eb / (Rw(LMIN) + p.Rh + 0.01), AMAX = pick([0.2, 0.5, 1, 1.5, 2, 3, 5], IMAX * 1.2);
  var VMAX = pick([0.2, 0.5, 1, 2, 3, 5], p.Eb * Rw(LMAX) / (Rw(LMAX) + RH_MIN) * 1.2);
  var ARES = AMAX / 100, VRES = VMAX / 300;
  var IDIG = ARES < 0.005 ? 4 : 3, VDIG = VRES < 0.002 ? 4 : 3;
  function fmtN(v, d) { return String(+v.toFixed(d === undefined ? 2 : d)); }
  var st = { key: false, L: L0, targetL: L0, rh: 2, target: 2, traced: false, zero: false };
  var view = {};
  function solve() { p.key = st.key ? 1 : 0; p.Lw = st.L; p.Rh = st.rh; view = KW.view(KW.init(p), p); }
  function I() { return st.key ? view.I_AM : 0; }
  function Vr() { return st.key ? view.V_VM : 0; }
  function fI(v) { return (Math.round(v / ARES) * ARES).toFixed(IDIG); }
  function fV(v) { return (Math.round(v / VRES) * VRES).toFixed(VDIG); }

  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }

  // ---------- the wire board: a metre of wire over a printed metre scale (drawn to 0.8 of life size on the bench)
  var SC = 0.8, WB = [0.0, -0.44], BW = LMAX * SC + 0.12;
  var wboard = S.rounded(BW, 0.12, 0.016, 0.005, M.darkWood); wboard.rotation.x = -Math.PI / 2; wboard.position.set(WB[0], 0.008, WB[1]); S.scene.add(wboard);
  S.contact(BW + 0.06, 0.18, WB[0], WB[1], 0.45);
  var scaleTex = S.canvasTex(2048, 128, function (x, w, h) {
    x.fillStyle = '#f0ead8'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#1a1a1a';
    var cm = 100, k = w / cm;
    for (var i = 0; i <= cm; i++) {
      var xx = i * k, big = i % 10 === 0;
      x.fillRect(xx, 0, big ? 3 : 1.5, big ? 48 : (i % 5 === 0 ? 34 : 20));
      if (big) { x.font = '600 32px "Public Sans", sans-serif'; x.fillText(String(i), xx + 4, 88); }
    }
    x.font = '600 26px "Public Sans", sans-serif'; x.fillStyle = '#6b4a14'; x.fillText('cm', w - 56, 118);
  });
  var strip = new T.Mesh(new T.PlaneGeometry(LMAX * SC, 0.03), new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.6 }));
  strip.rotation.x = -Math.PI / 2; strip.position.set(WB[0], 0.0165, WB[1] + 0.03); S.scene.add(strip);
  function sx(L) { return WB[0] - LMAX * SC / 2 + L * SC; }
  var wireCol = /copper/i.test(SAMPLE) ? 0xc8703a : /constantan|eureka/i.test(SAMPLE) ? 0xc9b49a : /manganin/i.test(SAMPLE) ? 0xb08f72
    : /iron/i.test(SAMPLE) ? 0x8d9095 : 0xb4b2ae;
  var wireM = new T.MeshStandardMaterial({ color: wireCol, roughness: 0.3, metalness: 0.88 });
  var wireR = Math.max(0.0007, p.dia * 1.6);
  var wire = S.mesh(new T.CylinderGeometry(wireR, wireR, LMAX * SC, 10), wireM);
  wire.rotation.z = Math.PI / 2; wire.position.set(WB[0], 0.0235, WB[1] - 0.012); S.scene.add(wire);
  var endA = post(sx(0) - 0.022, 0.016, WB[1] - 0.04, 'red'), endB = post(sx(LMAX) + 0.022, 0.016, WB[1] - 0.04, 'black');
  [[sx(0), endA], [sx(LMAX), endB]].forEach(function (q) {
    S.scene.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3([new T.Vector3(q[0], 0.0235, WB[1] - 0.012),
      new T.Vector3((q[0] + q[1].at.x) / 2, 0.022, WB[1] - 0.026), new T.Vector3(q[1].at.x, 0.018, q[1].at.z)]), 16, wireR, 6, false), wireM));
  });
  // the sliding clamp that picks the length off the wire
  var clamp = new T.Group(); S.scene.add(clamp);
  clamp.add((function () { var b = S.rounded(0.018, 0.03, 0.022, 0.003, M.alu); b.rotation.x = -Math.PI / 2; b.position.y = 0.011; return b; })());
  clamp.add((function () { var k = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.008, 12), M.brass); k.position.y = 0.026; return k; })());
  var clampT = post(0, 0.016, WB[1] - 0.052, 'brass');
  function placeClamp() { clamp.position.set(sx(st.L), 0.016, WB[1] - 0.012); clampT.g.position.x = sx(st.L); clampT.at.x = sx(st.L); }
  placeClamp();
  var wtag = S.label((SAMPLE || 'Resistance wire') + '  ·  d = ' + fmtN(p.dia * 1000, 3) + ' mm',
    { w: 0.26, ratio: 0.08, color: '#f3ead2', bg: '#2b2b2b', px: 1024 });
  wtag.rotation.x = -Math.PI / 2; wtag.position.set(WB[0], 0.0165, WB[1] - 0.046); S.scene.add(wtag);

  // ---------- supply, key, rheostat, ammeter, voltmeter
  var PB = [-0.6, -0.06];
  var pb = S.powerBox([PB[0], 0, PB[1]], 'BATTERY ELIMINATOR');
  var pbV = S.label(fmtN(p.Eb, 1) + ' V DC', { w: 0.05, ratio: 0.3, color: '#f2f2f2' });
  pbV.position.set(PB[0] + 0.045, 0.034, PB[1] + 0.0405); S.scene.add(pbV);
  var pbPlus = { at: new T.Vector3(PB[0] + 0.04, 0.109, PB[1]) }, pbMinus = { at: new T.Vector3(PB[0] - 0.04, 0.109, PB[1]) };
  var KP = [-0.34, 0.0];
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
        S.say(on ? 'Key closed: both meters read.' : 'Key open. Keep it open between readings so the wire does not warm up.');
        S.render();
      });
  }
  var RHP = [-0.06, 0.04];
  var rh = S.rheostat([RHP[0], 0, RHP[1]], RH_LEN);
  var rhA = post(RHP[0] - RH_LEN / 2 - 0.01, 0.05, RHP[1], 'red'), rhC = post(RHP[0] + RH_LEN / 2 - 0.006, 0.065, RHP[1], 'black');
  function rhF(r) { return (RH_MAX - r) / (RH_MAX - RH_MIN); }
  function sliderTop(f) { return rh.localToWorld(new T.Vector3(-RH_LEN / 2 + 0.02 + f * (RH_LEN - 0.04), 0.074, 0)); }
  function setRh(r) { st.rh = Math.max(RH_MIN, Math.min(RH_MAX, r)); rh.setFraction(rhF(st.rh)); solve(); }
  setRh(p.Rh);
  function slide(target) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    target = Math.max(RH_MIN, Math.min(RH_MAX, target)); st.target = target;
    var r0 = st.rh; if (Math.abs(target - r0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(sliderTop(rhF(r0)), function (k) { return sliderTop(rhF(r0 + (target - r0) * k)); },
      function (k) { setRh(r0 + (target - r0) * k); }, { ms: 700, mode: 'top' }).then(function () { setRh(target); S.render(); });
  }
  var am = S.meter({ min: 0, max: AMAX, ticks: AMAX === 0.2 ? 4 : AMAX === 0.5 ? 5 : AMAX === 1 ? 10 : 6, unit: 'A', symbol: 'A',
    caption: 'DC AMMETER 0–' + fmtN(AMAX) + ' A', pos: [0.34, 0, -0.02] });
  var vmUnit = VMAX < 1 ? 'mV' : 'V', vmK = VMAX < 1 ? 1000 : 1;
  var vm = S.meter({ min: 0, max: VMAX * vmK, ticks: 5, unit: vmUnit, symbol: 'V',
    caption: 'DC VOLTMETER 0–' + fmtN(VMAX * vmK, VMAX < 1 ? 0 : 1) + ' ' + vmUnit, pos: [0.36, 0, -0.62] });
  var amP = { at: wpt(am, 0.035, 0.07, -0.03) }, amM = { at: wpt(am, -0.035, 0.07, -0.03) };
  var vmP = { at: wpt(vm, 0.035, 0.07, -0.03) }, vmM = { at: wpt(vm, -0.035, 0.07, -0.03) };

  lead(pbPlus.at, kL.at, 'red', [[-0.52, -0.12], [-0.44, -0.06]]);
  lead(kR.at, rhA.at, 'red', [[-0.26, -0.06], [-0.22, 0.01]]);
  lead(rhC.at, amP.at, 'red', [[0.14, 0.02], [0.3, -0.02]]);
  lead(amM.at, endB.at, 'yellow', [[0.3, -0.2], [0.46, -0.34]]);
  lead(endA.at, pbMinus.at, 'black', [[-0.54, -0.5], [-0.68, -0.26]]);
  lead(vmP.at, clampT.at, 'red', [[0.36, -0.56], [0.1, -0.54]], 0.012);
  lead(vmM.at, endA.at, 'black', [[0.26, -0.58], [-0.4, -0.54]], 0.012);

  S.addApparatus('wire', wire, SAMPLE ? 'Resistance wire: ' + SAMPLE : 'Resistance wire',
    'Stretched over a metre scale. The sliding clamp decides how much of it is in the circuit. Diameter ' + fmtN(p.dia * 1000, 3) + ' mm.');
  S.addApparatus('clamp', clamp, 'Sliding clamp', 'Slide it along the wire to take off exactly the length you want, read off the scale below.');
  S.addApparatus('pb', pb, 'Battery eliminator (' + fmtN(p.Eb, 1) + ' V)', 'A steady low-voltage supply.');
  S.addApparatus('key', key, 'Plug key K', 'Closes the circuit. Out between readings, so the wire stays cool.');
  S.addApparatus('rh', rh, 'Rheostat', 'Keeps the current small so the wire does not heat up and change its resistance.');
  S.addApparatus('am', am, 'Ammeter (0–' + fmtN(AMAX) + ' A)', 'In series with the wire.');
  S.addApparatus('vm', vm, 'Voltmeter', 'Across the length of wire between the end terminal and the clamp.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudL = S.hudCard('Length in circuit'), hudI = S.hudCard('Ammeter'), hudR = S.hudCard('R = V / I');
  solve();

  function trace() { st.traced = true; S.focus('wire');
    S.say('Supply, key, rheostat, ammeter and the length of wire between the end terminal and the clamp: one series loop, with the voltmeter across that length.');
    S.render(); }
  function zeroCheck() {
    if (st.key) { S.say('Take the key out first.'); return; }
    st.zero = true; S.focus('am'); S.say('With the key out both needles rest on zero: no zero error.'); S.render();
  }
  function setLen(L) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    L = Math.max(LMIN, Math.min(LMAX, Math.round(L * 100) / 100)); st.targetL = L;
    var L0b = st.L; if (Math.abs(L - L0b) < 1e-9) return Promise.resolve();
    var was = st.key;
    return (was ? setKey(false) : Promise.resolve()).then(function () {
      return S.hand.pinchMove(new T.Vector3(sx(L0b), 0.042, WB[1] - 0.012),
        function (k) { return new T.Vector3(sx(L0b + (L - L0b) * k), 0.042, WB[1] - 0.012); },
        function (k) { st.L = L0b + (L - L0b) * k; placeClamp(); solve(); }, { ms: 800, mode: 'top' });
    }).then(function () {
      st.L = L; placeClamp(); solve();
      S.say('The clamp is at ' + (L * 100).toFixed(0) + ' cm: that length of wire is now in the circuit.');
      return was ? setKey(true) : Promise.resolve();
    }).then(function () { S.render(); });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.key) { S.say('The key is open, so no current flows. Insert the plug first.'); return false; }
    var i = +fI(I()), v = +fV(Vr());
    if (i <= 0 || v <= 0) { S.say('A meter reads zero. Check the circuit.'); return false; }
    if (I() > AMAX * 1.02) { S.say('The ammeter is past its range. Put more of the rheostat in.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.L - st.L) < 0.005; })) { S.say('There is already a reading at this length. Move the clamp.'); return false; }
    if (S.rows.length >= 10) { S.say('Ten readings are plenty. Go on to the graph.'); return false; }
    S.addRow({ L: st.L, V: v, I: i });
    S.say('Written in your record book: L = ' + (st.L * 100).toFixed(0) + ' cm, V = ' + v.toFixed(VDIG) + ' V, I = ' + i.toFixed(IDIG) + ' A, R = ' + (v / i).toFixed(3) + ' Ω.');
    return true;
  }

  return {
    camera: { pos: [0.0, 1.42, 0.62], look: [0.0, 0.0, -0.3] },
    views: { wire: [[0.0, 0.34, -0.14], [0.0, 0.02, -0.44]], clamp: [[0.0, 0.2, -0.26], [0.0, 0.02, -0.44]],
      pb: [[-0.5, 0.32, 0.1], [-0.6, 0.04, -0.08]], key: [[-0.3, 0.24, 0.12], [-0.34, 0.02, 0.0]],
      rh: [[-0.04, 0.3, 0.22], [-0.06, 0.04, 0.02]], am: [[0.34, 0.26, 0.2], [0.34, 0.04, -0.03]],
      vm: [[0.36, 0.3, -0.3], [0.36, 0.04, -0.63]],
      circuit: [[0.0, 1.42, 0.62], [0.0, 0.0, -0.3]], work: [[0.0, 0.76, 0.06], [0.0, 0.0, -0.4]],
      book: [[-0.5, 0.45, 0.6], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'Take a length L of a uniform wire of area of cross-section A. Its resistance is R = rho L / A. '
        + 'The resistance grows in proportion to the length, falls as the wire is made thicker, and depends on what the wire is made of through its resistivity rho.',
      formula: 'R = ρ L / A',
      formulaNote: 'so a graph of R against L is a straight line of slope ρ / A',
      more: ['Measure R = V / I for four different lengths of the same wire. The points lie on a straight line through the origin, and its slope times the '
        + 'area of cross-section gives the resistivity of the material.',
        'A thicker wire of the same material and length has a smaller resistance, because the current has a wider road: doubling the diameter makes the area '
          + 'four times larger and the resistance a quarter.'],
      precautions: 'Keep the current small with the rheostat and take the key out between readings: a warm wire has a different resistance. Read the clamp '
        + 'position against the scale with your eye straight above it.' },
    book: { title: 'Expt. — Resistance of a wire',
      lines: ['Aim: ' + S.lab.aim].concat(SAMPLE ? ['Wire: ' + SAMPLE] : [])
        .concat(['Diameter d = ' + fmtN(p.dia * 1000, 3) + ' mm', 'Area A = πd²/4 = ' + (AREA * 1e6).toFixed(4) + ' mm²',
          'R = V / I for each length L', 'Slope of R against L = ρ / A']),
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'L (cm)', get: function (r) { return (r.L * 100).toFixed(0); } },
        { label: 'V (V)', get: function (r) { return r.V.toFixed(VDIG); } },
        { label: 'I (A)', get: function (r) { return r.I.toFixed(IDIG); } },
        { label: 'R (Ω)', get: function (r) { return (r.V / r.I).toFixed(3); } }] },
    graph: { x: function (r) { return r.L * 100; }, y: function (r) { return r.V / r.I; }, xlabel: 'L (cm)', ylabel: 'R (Ω)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) {
      if (rows.length < 4) return null;
      var k = S.fit.origin(rows.map(function (r) { return [r.L, r.V / r.I]; }));     // ohm per metre
      return { label: 'Resistivity of the wire', value: k * AREA * 1e8, unit: '×10⁻⁸ Ω·m', digits: 2, truth: p.rho * 1e8,
        note: 'Slope of R against L, times the area of cross-section.' };
    },
    tol: 0.05,
    resultNote: 'The graph was a straight line through the origin: the resistance of a uniform wire is proportional to its length.',
    chips: ['Why does a longer wire have more resistance?', 'What happens if the wire is made thicker?',
      'What is resistivity?', 'Check my readings', 'Why keep the current small?'],
    viva: [['A wire is drawn out to twice its length, the same material and the same volume. Its resistance becomes',
      ['4 times', '2 times', 'Half'], 0, 'The length doubles and the area halves, so R = ρL/A grows four times.'],
    ['Why is nichrome and not copper used for a heating element?',
      ['Its resistivity is much higher, so it gets hot', 'It is cheaper', 'It conducts better'], 0,
      'A high resistance turns electrical energy into heat; copper is used for leads exactly because it does not.']],
    askState: function () {
      return { wire: SAMPLE || 'resistance wire', diameter_mm: +fmtN(p.dia * 1000, 3), length_in_circuit_cm: +(st.L * 100).toFixed(0),
        key_closed: st.key, rheostat_ohm: +fmtN(st.rh, 1), ammeter_A: +fI(I()), voltmeter_V: +fV(Vr()),
        measured_R_ohm: I() > 0 ? +(Vr() / I()).toFixed(3) : null, readings_taken: S.rows.length };
    },
    steps: [
      { id: 'check', title: 'Check the circuit', view: 'circuit', render: function (u) {
          u.h2('Check the circuit');
          u.p('The wire is stretched over the metre scale. Only the length between the end terminal and the clamp is in the circuit.');
          u.task('1. Trace the circuit', st.traced, st.traced ? 'Supply, key, rheostat, ammeter, wire' : 'Follow the leads from the supply')
            .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
          u.task('2. Check the meter zeros', st.zero, st.zero ? 'Both needles on zero' : 'With the key open')
            .add(u.button(st.zero ? 'Checked' : 'Check the zeros', zeroCheck, !st.zero, st.zero));
          u.note('The voltmeter is across the clamped length only, so it reads the potential difference across exactly that piece of wire.');
          u.next('Next: close the key', st.traced && st.zero);
        },
        ok: function () { return st.traced && st.zero; },
        auto: function () { trace(); zeroCheck(); return Promise.resolve(); } },
      { id: 'on', title: 'Close the key', view: 'am', render: function (u) {
          u.h2('Close the key');
          u.p('With the rheostat well in, the current stays small and the wire stays cool.');
          u.task('Insert the plug', st.key, st.key ? 'Current ' + fI(I()) + ' A' : 'Key open')
            .add(u.row(u.button(st.key ? 'Key is in' : 'Insert the plug', function () { setKey(true); }, true, st.key || S.hand.busy),
              u.button('Take the plug out', function () { setKey(false); }, false, !st.key || S.hand.busy)));
          u.slider('Rheostat resistance', RH_MIN, RH_MAX, 0.5, function () { return st.target; }, function (v) { st.target = v; }, 'Ω', 1);
          u.row(u.button('Slide the contact', function () { slide(st.target); }, false, S.hand.busy));
          u.live(function () { return 'I ' + fI(I()) + ' A  ·  V ' + fV(Vr()) + ' V  ·  R = ' + (I() > 0 ? (Vr() / I()).toFixed(3) : '—') + ' Ω'; });
          u.next('Next: four lengths', st.key);
        },
        ok: function () { return st.key; },
        auto: function () { return setKey(true); } },
      { id: 'read', title: 'Measure four lengths', view: 'work', render: function (u) {
          u.h2('R for four different lengths');
          u.p('Slide the clamp to a new length, close the key, read both meters and record. Four lengths are enough.');
          u.slider('Length of wire in the circuit', LMIN, LMAX, 0.05, function () { return st.targetL; }, function (v) { st.targetL = v; }, 'm', 2);
          u.row(u.button('Move the clamp', function () { setLen(st.targetL); }, true, S.hand.busy),
            u.button('Record this reading', function () { record(); }, true, !st.key || S.hand.busy));
          u.live(function () { return 'L ' + (st.L * 100).toFixed(0) + ' cm  ·  I ' + fI(I()) + ' A  ·  V ' + fV(Vr()) + ' V  ·  R ' + (I() > 0 ? (Vr() / I()).toFixed(3) : '—') + ' Ω'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 4) u.p(S.rows.length + ' of at least 4 lengths recorded.');
          u.next('Next: plot R against L', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          return [1.0, 0.8, 0.6, 0.4].reduce(function (pr, L) {
            return pr.then(function () { return setLen(L).then(function () { S.advance(0.2); record(); }); });
          }, st.key ? Promise.resolve() : setKey(true));
        } },
    ],
    tick: function () {
      solve(); am.set(I()); vm.set(Vr() * vmK);
      hudL.set((st.L * 100).toFixed(0) + ' cm'); hudI.set(fI(I()) + ' A');
      hudR.set(I() > 0 ? (Vr() / I()).toFixed(3) + ' Ω' : '—');
    },
  };
});
