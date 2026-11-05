/* Prayogshala studio module: thermocouple calibration (B.Sc. Thermal Physics). One bench, two read-outs:
   - gain G = 0 (thermocouple-null-method): the thermo-emf is balanced on a potentiometer wire with a jockey and a galvanometer;
   - gain G > 0 (thermocouple-opamp): an op-amp amplifier and a digital voltmeter, to the neutral temperature.
   Physics: the hw_tcouple kernel (packs/heat_wave_ug) - the same numbers the server checks. The bath is a thermostat bath
   (the heater cycles so the bath settles at the chosen target). */
HoolaStudio.define('thermocouple-null-method', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.hw_tcouple;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('hw_tcouple');
  var AMP = p.G > 0.5, OIL = p.Tcap > 150;
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var PAIR = AMP ? 'copper-iron' : /iron/i.test(SAMPLE) ? 'iron-constantan' : 'copper-constantan';
  var TMIN = AMP ? 60 : 40, TMAX = AMP ? 330 : 90, TSTEP = AMP ? 30 : 10;
  function r1(v) { return Math.round(v * 10) / 10; }
  var sim = K.init(p);
  var X0 = 0.05, WL = 1.0;                                    // potentiometer wire from x = X0 to X0 + 1 m
  var st = { placed: false, std: false, on: false, speed: 30, target: TMIN, hold: 0, l: 50, dev: 0, shownV: 0, tconn: false };

  function labelTex(w, h, txt, size) { return S.canvasTex(w, h, function (x) { x.fillStyle = '#f4f1e6'; x.fillRect(0, 0, w, h); x.fillStyle = '#222'; x.font = '600 ' + size + 'px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(txt, w / 2, h / 2); }); }
  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'pinch', 320); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }

  // ---------- bath on a hot plate, thermometer, stirrer
  var BX = -0.85, BZ = -0.28, BR = 0.07, BH = 0.12;
  var hp = S.rounded(0.2, 0.2, 0.04, 0.012, new T.MeshStandardMaterial({ color: 0xe7e4dc, roughness: 0.5 })); hp.rotation.x = -Math.PI / 2; hp.position.set(BX, 0.02, BZ); S.scene.add(hp);
  var hsw = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.012, 24), M.red); hsw.rotation.x = Math.PI / 2; hsw.position.set(BX + 0.06, 0.02, BZ + 0.103); S.scene.add(hsw);
  var hlbl = S.label(OIL ? 'OIL BATH HEATER' : 'THERMOSTAT BATH', { w: 0.09, ratio: 0.13, color: '#3b3b3b' }); hlbl.position.set(BX - 0.02, 0.034, BZ + 0.1035); S.scene.add(hlbl);
  S.contact(0.26, 0.26, BX, BZ, 0.55);
  var bath = S.beaker(BR, BH, [BX, 0.04, BZ]);
  var liq = S.mesh(new T.CylinderGeometry(BR * 0.95, BR * 0.95, BH * 0.7, 40), new T.MeshStandardMaterial({ color: OIL ? 0xc9a227 : 0x6aaccc, roughness: 0.05, metalness: 0.08 }), false); liq.position.y = 0.002 + BH * 0.35; bath.add(liq);
  var stirrer = S.mesh(new T.CylinderGeometry(0.0015, 0.0015, 0.16, 8), M.steel); stirrer.position.set(BX + 0.035, 0.04 + 0.08, BZ + 0.0); S.scene.add(stirrer);
  var thermo = S.thermometer({ len: AMP ? 0.4 : 0.3, min: AMP ? 0 : 0, max: AMP ? 360 : 110, value: p.Ts, pos: [BX - 0.025, 0.04 + 0.014, BZ + 0.012] });
  // hot junction: a bead on two wires (copper and constantan / iron), lowered into the bath
  var hot = new T.Group(); S.scene.add(hot);
  var bead = S.mesh(new T.SphereGeometry(0.003, 12, 10), M.steel); hot.add(bead);
  var hw1 = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.2, 8), M.copper); hw1.position.set(-0.002, 0.1, 0); hot.add(hw1);
  var hw2 = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.2, 8), PAIR === 'copper-iron' ? M.iron : M.alu); hw2.position.set(0.002, 0.1, 0); hot.add(hw2);
  var HOT_UP = new T.Vector3(BX + 0.0, 0.04 + BH + 0.08, BZ - 0.02), HOT_DOWN = new T.Vector3(BX + 0.0, 0.04 + 0.025, BZ - 0.02);
  hot.position.copy(HOT_UP);
  // ---------- ice flask with the cold junction
  var IX = -0.5, IZ = -0.28;
  var ice = S.beaker(0.045, 0.1, [IX, 0, IZ]);
  var icelev = S.mesh(new T.CylinderGeometry(0.042, 0.042, 0.07, 32), new T.MeshStandardMaterial({ color: 0xcfe6ee, roughness: 0.2, transparent: true, opacity: 0.9 }), false); icelev.position.y = 0.04; ice.add(icelev);
  for (var ic = 0; ic < 9; ic++) { var cube = S.mesh(new T.BoxGeometry(0.014, 0.014, 0.014), new T.MeshStandardMaterial({ color: 0xf0f8fb, roughness: 0.1, transparent: true, opacity: 0.9 }), false);
    cube.position.set(Math.cos(ic * 1.9) * 0.025, 0.07 + (ic % 3) * 0.004, Math.sin(ic * 1.9) * 0.025); cube.rotation.set(ic, ic * 0.7, 0); ice.add(cube); }
  S.contact(0.12, 0.12, IX, IZ, 0.45);
  var cold = new T.Group(); S.scene.add(cold); cold.position.set(IX + 0.01, 0.045, IZ);
  var cb = S.mesh(new T.SphereGeometry(0.003, 12, 10), M.steel); cold.add(cb);
  var cw1 = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.12, 8), M.copper); cw1.position.set(-0.002, 0.06, 0); cold.add(cw1);
  var cw2 = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.12, 8), PAIR === 'copper-iron' ? M.iron : M.alu); cw2.position.set(0.002, 0.06, 0); cold.add(cw2);
  var iThermo = S.thermometer({ len: 0.25, min: -10, max: 40, value: 0, pos: [IX - 0.02, 0.014, IZ + 0.005] });
  var icelbl = S.label('MELTING ICE  0 °C', { w: 0.07, ratio: 0.13, color: '#235' }); icelbl.position.set(IX, 0.03, IZ + 0.046); S.scene.add(icelbl);

  // ---------- read-out: potentiometer (null method) or op-amp amplifier + voltmeter
  var board, wireBar, jockey, galv, dvm, dvmTex, ampBox, driver, scaleP;
  var PZ = -0.3, PY = 0.012;
  if (!AMP) {
    board = new T.Group(); S.scene.add(board);
    var bd = S.rounded(WL + 0.1, 0.12, 0.025, 0.006, M.wood); bd.rotation.x = -Math.PI / 2; bd.position.set(X0 + WL / 2, 0.0125, PZ); board.add(bd);
    wireBar = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, WL, 8), M.steel); wireBar.rotation.z = Math.PI / 2; wireBar.position.set(X0 + WL / 2, 0.0275, PZ - 0.02); board.add(wireBar);
    var sc = S.canvasTex(2048, 64, function (x, w, h) { x.fillStyle = '#fbfaf3'; x.fillRect(0, 0, w, h); x.fillStyle = '#222'; x.font = '600 24px sans-serif';
      for (var c = 0; c <= 100; c++) { var xx = c / 100 * (w - 4) + 2, big = c % 10 === 0; x.fillRect(xx, 0, big ? 3 : 1.5, big ? 30 : (c % 5 === 0 ? 22 : 14)); if (big) x.fillText(String(c), xx - 10, 52); } });
    scaleP = new T.Mesh(new T.PlaneGeometry(WL, 0.028), new T.MeshStandardMaterial({ map: sc, roughness: 0.6 })); scaleP.rotation.x = -Math.PI / 2; scaleP.position.set(X0 + WL / 2, 0.026, PZ + 0.02); board.add(scaleP);
    [X0 - 0.03, X0 + WL + 0.03].forEach(function (x) { var tm = S.terminal([x, 0.025, PZ - 0.02], 'red'); board.add(tm); });
    jockey = new T.Group(); S.scene.add(jockey);
    var jb = S.rounded(0.026, 0.022, 0.03, 0.004, M.bakelite); jb.position.set(0, 0.03, 0); jockey.add(jb); jb.rotation.x = 0;
    var jk = S.mesh(new T.BoxGeometry(0.003, 0.012, 0.003), M.steel); jk.position.set(0, 0.01, 0); jockey.add(jk);
    var jh = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.025, 12), M.brass); jh.position.set(0, 0.057, 0); jockey.add(jh);
    jockey.position.set(X0 + st.l / 100 * WL, 0.015, PZ - 0.02);
    var lab1 = S.label('POTENTIOMETER WIRE, 1 m  ·  ' + (p.kp * 1000).toFixed(2) + ' mV per m', { w: 0.34, ratio: 0.06, color: '#3b3b3b' }); lab1.rotation.x = -Math.PI / 2; lab1.position.set(X0 + 0.45, 0.0265, PZ + 0.045); board.add(lab1);
    galv = S.meter({ min: -1, max: 1, zeroCentre: true, unit: '', symbol: 'G', caption: 'GALVANOMETER', ticks: 10, pos: [0.15, 0, -0.12] });
    S.contact(WL + 0.14, 0.16, X0 + WL / 2, PZ, 0.5);
  } else {
    ampBox = new T.Group(); S.scene.add(ampBox);
    var ab = S.rounded(0.22, 0.09, 0.14, 0.01, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 })); ab.rotation.x = -Math.PI / 2; ab.position.set(-0.05, 0.045, PZ); ampBox.add(ab);
    var al = S.label('OP-AMP AMPLIFIER  G = ' + Math.round(p.G), { w: 0.16, ratio: 0.12, color: '#e8e8e8', bg: '#2b2f36' }); al.rotation.x = -Math.PI / 2; al.position.set(-0.05, 0.0905, PZ); ampBox.add(al);
    [-0.1, -0.075].forEach(function (dx) { var tm = S.terminal([-0.05 + dx, 0.09, PZ + 0.05], dx < -0.09 ? 'red' : 'black'); ampBox.add(tm); });
    var tout = S.terminal([0.0, 0.09, PZ + 0.05], 'red'); ampBox.add(tout);
    S.contact(0.28, 0.2, -0.05, PZ, 0.5);
    dvm = new T.Group(); S.scene.add(dvm);
    var db = S.rounded(0.2, 0.08, 0.1, 0.008, new T.MeshStandardMaterial({ color: 0xeceae3, roughness: 0.5 })); db.rotation.x = -Math.PI / 2; db.position.set(0.3, 0.04, PZ); dvm.add(db);
    dvmTex = S.liveTex(512, 160); var dm = new T.Mesh(new T.PlaneGeometry(0.15, 0.047), new T.MeshBasicMaterial({ map: dvmTex })); dm.rotation.x = -Math.PI / 2; dm.position.set(0.3, 0.0805, PZ + 0.0); dvm.add(dm);
    S.contact(0.26, 0.15, 0.3, PZ, 0.5);
  }
  var dvmLast = '';
  function drawDvm(v) { if (!dvmTex) return; var txt = (v * 1000).toFixed(1) + ' mV'; if (txt === dvmLast) return; dvmLast = txt;
    dvmTex.draw(function (x, w, h) { x.fillStyle = '#b9c4a7'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b2116'; x.font = '700 78px "JetBrains Mono", monospace'; x.textAlign = 'right'; x.fillText(txt, w - 16, h - 40); x.font = '600 20px sans-serif'; x.textAlign = 'left'; x.fillText('DC', 16, 30); }); }
  // connecting wires: hot junction -> readout, cold junction -> readout
  var rinA = AMP ? [-0.15, 0.1, PZ + 0.05] : [X0 - 0.03, 0.04, PZ - 0.02], rinB = AMP ? [-0.125, 0.1, PZ + 0.05] : [0.185, 0.075, -0.15];
  var wA = S.wire([[BX, 0.2, BZ - 0.02], [BX + 0.15, 0.1, BZ - 0.08], [IX - 0.05, 0.12, IZ - 0.05], rinA], 'red');
  var wB = S.wire([[IX + 0.01, 0.1, IZ], [IX + 0.1, 0.1, IZ + 0.02], rinB], 'black');
  var watch = S.stopwatch([0.3, 0.035, 0.17], [-1.15, 0, -0.2]);

  S.addApparatus('bath', bath, OIL ? 'Oil bath' : 'Water bath', (OIL ? 'Oil can be taken far above 100 °C. ' : '') + 'A thermostat on the heater plate keeps the bath at the temperature you choose. The hot junction sits in it.');
  S.addApparatus('thermo', thermo, OIL ? 'High-range thermometer' : 'Mercury thermometer', 'Reads the bath temperature, to 0.1 °C. The hot junction is beside its bulb.');
  S.addApparatus('hot', hot, 'Hot junction', 'The ' + PAIR + ' junction, in the bath.');
  S.addApparatus('ice', ice, 'Ice flask (cold junction)', 'The other junction is held at 0 °C in melting ice.');
  S.addApparatus('cold', cold, 'Cold junction', 'The other end of the ' + PAIR + ' pair, in the ice.');
  if (!AMP) {
    S.addApparatus('pot', board, 'Potentiometer', 'A 1 m wire carrying a steady current: the fall of potential is ' + (p.kp * 1000).toFixed(2) + ' mV for each metre. The jockey picks off the voltage that balances the thermo-emf.');
    S.addApparatus('jockey', jockey, 'Jockey', 'Touch the wire with the knife edge: the galvanometer shows which way the balance lies.');
    S.addApparatus('galv', galv, 'Zero-centre galvanometer', 'No deflection means the thermo-emf equals the potentiometer voltage, with no current drawn from the thermocouple.');
  } else {
    S.addApparatus('amp', ampBox, 'Op-amp amplifier', 'Non-inverting amplifier of gain G = 1 + Rf/R1 = ' + Math.round(p.G) + ' (Rf = ' + Math.round(p.G - 1) + ' kΩ, R1 = 1 kΩ).');
    S.addApparatus('dvm', dvm, 'Digital voltmeter', 'Reads the amplifier output to 0.1 mV.');
  }
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Handy for timing how long the bath has been steady.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var bookLines = ['Aim: to calibrate a ' + PAIR + ' thermocouple (cold junction in ice).', AMP ? 'Amplifier gain G = ' + Math.round(p.G) + ';  e = Vout / G' : 'Potentiometer: ' + (p.kp * 1000).toFixed(2) + ' mV per metre;  e = k l',
    AMP ? 'Neutral temperature Tn = top of the e–T parabola' : 'E–T curve; slope at 50 °C = thermo-emf per degree'];
  var hudT = S.hudCard('Bath'), hudE = S.hudCard(AMP ? 'Output' : 'Jockey'), hudN = S.hudCard('Readings');

  // ---------- the bath's thermostat and clock
  function runFor(sec) {                                   // the clock, in half-second steps, with the thermostat
    var n = Math.max(1, Math.round(sec / 0.5)), i, h = sec / n;
    for (i = 0; i < n; i++) {
      sim.on = (st.on && sim.T < st.target - 0.3) ? 1 : 0;
      K.step(sim, p, h);
      if (st.on && Math.abs(sim.T - st.target) <= 0.4) st.hold += h; else st.hold = 0;
    }
  }
  function ready() { return st.on && st.hold >= 60 && Math.abs(r1(sim.T) - st.target) <= 0.5; }
  function emfNow() { return K.view(sim, p).e; }
  function devNow() { return Math.max(-1, Math.min(1, (emfNow() - p.kp * st.l / 100) / 0.4e-3)); }
  function setL(l) { st.l = Math.max(0, Math.min(100, Math.round(l * 10) / 10)); if (jockey) jockey.position.x = X0 + st.l / 100 * WL; if (galv) galv.set(devNow()); }
  function placeJunctions() {
    if (S.hand.busy || st.placed) return Promise.resolve();
    return carry(HOT_UP.clone().add(new T.Vector3(0, 0.1, 0)), [{ ms: 1200, fn: function (k) { return HOT_UP.clone().lerp(HOT_DOWN, k).add(new T.Vector3(0, 0.1, 0)); }, onK: function (k) { hot.position.copy(HOT_UP.clone().lerp(HOT_DOWN, k)); } }], 'pinch')
      .then(function () { hot.position.copy(HOT_DOWN); st.placed = true; S.say('The hot junction is in the ' + (OIL ? 'oil' : 'water') + '. The cold junction is already in melting ice.'); S.render(); });
  }
  function standardise() { if (st.std) return; st.std = true; if (galv) S.focus('galv'); else S.focus('dvm');
    S.say(AMP ? 'Amplifier zeroed: with both ends of the input shorted, the output reads 0.0 mV.' : 'Potentiometer standardised: ' + (p.kp * 1000).toFixed(2) + ' mV per metre of wire.'); S.render(); }
  function heaterOn() { if (S.hand.busy || st.on) return Promise.resolve(); return S.hand.tap(hsw).then(function () { S.click(2000); st.on = true; S.say('Thermostat on. Choose a target temperature and let the bath settle.'); S.render(); }); }
  function setTarget(v) { st.target = Math.max(35, Math.min(p.Tcap - 5, Math.round(v / 5) * 5)); st.hold = 0; S.render(); }
  function record() {
    if (!ready()) { S.say('Let the bath settle at the target first (steady for a minute).'); return; }
    var v = K.view(sim, p), Tr = r1(sim.T);
    if (AMP) { var vo = Math.round(v.Vout * 1e4) / 1e4; S.addRow({ T: Tr, Vout: vo }); S.say('Written: T = ' + Tr.toFixed(1) + ' °C, output ' + (vo * 1000).toFixed(1) + ' mV.'); }
    else { if (Math.abs(devNow()) > 0.04) { S.say('The galvanometer is not at zero. Move the jockey until there is no deflection.'); return; }
      S.addRow({ T: Tr, l: st.l }); S.say('Written: T = ' + Tr.toFixed(1) + ' °C, balancing length ' + st.l.toFixed(1) + ' cm.'); }
  }
  function findNull() {                                    // the moves a student makes: halve the interval until the galvanometer rests, then trim by a millimetre
    var lo = 0, hi = 100, i, best, bd;
    for (i = 0; i < 24; i++) { var mid = (lo + hi) / 2; setL(mid); if (devNow() > 0) lo = mid; else hi = mid; }
    var c0 = Math.round((lo + hi) / 2 * 10) / 10; best = c0; bd = 9;
    for (i = -3; i <= 3; i++) { var c = Math.round((c0 + i * 0.1) * 10) / 10; setL(c); var d = Math.abs(devNow()); if (d < bd) { bd = d; best = c; } }
    setL(best);
  }
  function eOf(r) { return AMP ? r.Vout / p.G : p.kp * r.l / 100; }
  function setSpeed(v) { st.speed = v; S.render(); }
    var NEED = AMP ? 10 : 6;
  function rowsOK() { if (S.rows.length < NEED) return false; var ts = S.rows.map(function (r) { return r.T; }); return Math.max.apply(null, ts) - Math.min.apply(null, ts) >= (AMP ? 250 : 40); }
  function fit2(pts) {                                      // y = c0 + c1 x + c2 x² (least squares), same as the kernel calc
    var n = pts.length, s1 = 0, s2 = 0, s3 = 0, s4 = 0, t0 = 0, t1 = 0, t2 = 0, i, x, y;
    for (i = 0; i < n; i++) { x = pts[i][0]; y = pts[i][1]; s1 += x; s2 += x * x; s3 += x * x * x; s4 += x * x * x * x; t0 += y; t1 += x * y; t2 += x * x * y; }
    var det = n * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2); if (n < 3 || Math.abs(det) < 1e-300) return null;
    return [(t0 * (s2 * s4 - s3 * s3) - s1 * (t1 * s4 - s3 * t2) + s2 * (t1 * s3 - s2 * t2)) / det, (n * (t1 * s4 - s3 * t2) - t0 * (s1 * s4 - s3 * s2) + s2 * (s1 * t2 - t1 * s2)) / det,
      (n * (s2 * t2 - t1 * s3) - s1 * (s1 * t2 - t1 * s2) + t0 * (s1 * s3 - s2 * s2)) / det];
  }
  function curve(rows) { return fit2(rows.map(function (r) { return [r.T, eOf(r)]; })); }

  return {
    camera: { pos: [-0.2, 0.7, 1.75], look: [-0.15, 0.1, -0.25] },
    views: { bath: [[-0.7, 0.3, 0.3], [BX, 0.1, BZ]], thermo: [[-0.7, 0.3, 0.3], [BX - 0.025, 0.15, BZ]], hot: [[-0.7, 0.3, 0.3], [BX, 0.12, BZ - 0.02]], ice: [[-0.4, 0.25, 0.3], [IX, 0.06, IZ]], cold: [[-0.4, 0.25, 0.3], [IX, 0.07, IZ]],
      pot: [[0.5, 0.45, 0.4], [0.5, 0.02, PZ]], jockey: [[0.35, 0.2, 0.2], [X0 + 0.5, 0.02, PZ - 0.02]], galv: [[0.1, 0.22, 0.2], [0.15, 0.05, -0.12]], amp: [[0.0, 0.25, 0.3], [-0.05, 0.05, PZ]], dvm: [[0.3, 0.25, 0.3], [0.3, 0.04, PZ]],
      sw: [[-0.5, 0.4, 0.5], [-1.1, 0.05, -0.2]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'Two different metals joined at both ends make a thermocouple. When the junctions are at different temperatures a small emf appears. Here the cold junction stays in melting ice and the hot junction is in the bath.',
      formula: AMP ? 'e = a (T − Tc) + q (T² − Tc²),   Tn = −a / (2q)' : 'e = a ΔT + q (T² − Tc²),   e = k l at balance',
      formulaNote: AMP ? 'The amplifier output is Vout = G e. The emf rises to a maximum at the neutral temperature Tn, then falls.' : 'The potentiometer wire gives k volts for each metre; at the null point the jockey length l balances the emf, with no current drawn from the junction.',
      more: [AMP ? 'For a copper-iron couple the neutral temperature is about 270 °C; the inversion temperature, where the emf is zero again, is about twice that.' : 'The graph of e against T is nearly straight with a slight curve; its slope is the thermo-emf per degree.'],
      precautions: 'Keep the cold junction in melting ice, with the ice and water mixed. Stir the bath. Let the bath settle before each reading. ' + (AMP ? 'Heat oil slowly and keep water away from it.' : 'Keep the galvanometer shunted until you are near the null point.') },
    book: { title: 'Expt. — Thermocouple calibration', lines: bookLines,
      columns: AMP ? [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'T (°C)', get: function (r) { return r.T.toFixed(1); } }, { label: 'Vout (mV)', get: function (r) { return (r.Vout * 1000).toFixed(1); } },
        { label: 'e = Vout/G (µV)', get: function (r) { return (r.Vout / p.G * 1e6).toFixed(0); } }]
        : [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'T (°C)', get: function (r) { return r.T.toFixed(1); } }, { label: 'l (cm)', get: function (r) { return r.l.toFixed(1); } },
          { label: 'e = k l (µV)', get: function (r) { return (p.kp * r.l / 100 * 1e6).toFixed(0); } }] },
    graph: { x: function (r) { return r.T; }, y: function (r) { return eOf(r) * 1000; }, xlabel: 'T (°C)', ylabel: 'e (mV)', x0: 0, y0: 0,
      line: function () { var f = curve(S.rows); return f ? function (x) { return f[0] * 1000 + f[1] * 1000 * x + f[2] * 1000 * x * x; } : null; } },
    result: function (rows) {
      var f = curve(rows); if (!f) return null;
      if (AMP) { var Tn = f[2] !== 0 ? -f[1] / (2 * f[2]) : 0; return { label: 'Tn (neutral temperature)', value: Tn, unit: '°C', digits: 0, truth: -p.a / (2 * p.q), note: 'The highest point of the e–T parabola; e = ' + (f[0] * 1e6).toFixed(0) + ' + ' + (f[1] * 1e6).toFixed(2) + ' T ' + (f[2] < 0 ? '−' : '+') + ' ' + Math.abs(f[2] * 1e9).toFixed(1) + '×10⁻⁹ T² (µV).' }; }
      return { label: 'dE/dT at 50 °C', value: f[1] + 100 * f[2], unit: 'V/K', digits: 7, truth: p.a + 100 * p.q, note: 'The slope of the fitted E–T curve at 50 °C (' + PAIR + ').' };
    },
    tol: AMP ? 0.02 : 0.03,
    chips: ['Why keep the cold junction in ice?', AMP ? 'What is the neutral temperature?' : 'Why a potentiometer and not a voltmeter?', 'Why must the bath be steady?', 'Check my readings', 'Why is my slope different?'],
    viva: AMP ? [['At the neutral temperature, the thermo-emf', ['is at its maximum', 'is zero', 'is at its minimum'], 0, 'de/dT = a + 2qT = 0 there, so e is largest.'],
      ['Why is the emf amplified?', ['It is only a few millivolts, too small for a plain meter to read well', 'To make the bath hotter', 'To cancel the cold junction'], 0, 'A gain of 101 turns microvolts into a readable voltage.']]
      : [['Why does the potentiometer draw no current from the thermocouple at the null point?', ['The potentiometer voltage exactly opposes the emf', 'The galvanometer is broken', 'The wire is short'], 0, 'At balance the two voltages are equal and opposite, so no current flows.'],
        ['Which junction is kept at 0 °C?', ['The cold junction', 'The hot junction', 'Both'], 0, 'The cold junction stays in melting ice as the reference.']],
    askState: function () { return { junctions_placed: st.placed, calibrated: st.std, thermostat_on: st.on, target_C: st.target, bath_C: r1(sim.T), steady_for_s: Math.round(st.hold), jockey_cm: AMP ? null : st.l, galvanometer: AMP ? null : +devNow().toFixed(2), readings: S.rows.length, couple: PAIR }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bath', render: function (u) {
          u.h2('Junctions, instrument and heater');
          u.task('1. Lower the hot junction into the ' + (OIL ? 'oil' : 'water'), st.placed, st.placed ? 'In the bath; the cold junction is in melting ice' : 'The hand lowers it beside the thermometer')
            .add(u.button(st.placed ? 'In place' : 'Lower the hot junction', function () { placeJunctions(); }, !st.placed, st.placed || S.hand.busy));
          u.task('2. ' + (AMP ? 'Zero the amplifier' : 'Standardise the potentiometer'), st.std, st.std ? (AMP ? 'Output reads 0.0 mV' : (p.kp * 1000).toFixed(2) + ' mV per metre') : 'Short the input / use the standard cell')
            .add(u.button(st.std ? 'Done' : (AMP ? 'Zero it' : 'Standardise'), standardise, !st.std, st.std));
          u.task('3. Switch the thermostat on', st.on, st.on ? 'On' : 'The hand presses the heater switch')
            .add(u.button(st.on ? 'On' : 'Switch on', function () { heaterOn(); }, st.placed && st.std && !st.on, st.on || S.hand.busy));
          u.next('Next: take readings', st.placed && st.std && st.on);
        },
        ok: function () { return st.placed && st.std && st.on; },
        auto: function () { standardise(); return placeJunctions().then(function () { return heaterOn(); }); } },
      { id: 'readings', title: 'Readings', view: AMP ? 'dvm' : 'jockey', render: function (u) {
          u.h2('A reading at each bath temperature');
          u.p('Choose a target, wait until the bath is steady for a minute, then ' + (AMP ? 'read the amplifier output.' : 'move the jockey to the galvanometer null.') + ' Take at least ' + NEED + ' readings from ' + TMIN + ' to ' + TMAX + ' °C.');
          u.slider('Target temperature', 35, p.Tcap - 5, 5, function () { return st.target; }, function (v) { setTarget(v); }, '°C', 0);
          var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
          [1, 30, 120].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
          u.live(function () { return 'Bath ' + r1(sim.T).toFixed(1) + ' °C (target ' + st.target + ') · ' + (ready() ? 'STEADY' : st.hold > 0 ? 'settling ' + Math.round(st.hold) + ' s' : 'heating'); });
          if (!AMP) {
            u.slider('Jockey position l', 0, 100, 0.1, function () { return st.l; }, function (v) { setL(v); }, 'cm', 1);
            u.row(u.button('−1 cm', function () { setL(st.l - 1); S.render(); }, false, false), u.button('−1 mm', function () { setL(st.l - 0.1); S.render(); }, false, false),
              u.button('+1 mm', function () { setL(st.l + 0.1); S.render(); }, false, false), u.button('+1 cm', function () { setL(st.l + 1); S.render(); }, false, false));
            u.live(function () { var d = devNow(); return 'Galvanometer: ' + (Math.abs(d) < 0.04 ? 'at zero (balanced)' : d > 0 ? 'deflects right: move the jockey right' : 'deflects left: move the jockey left'); });
          } else u.live(function () { return 'Voltmeter: ' + (K.view(sim, p).Vout * 1000).toFixed(1) + ' mV'; });
          u.row(u.button('Write in the table', record, true, !ready()));
          u.h3('Observation table'); u.table();
          u.next('Next: plot the curve', rowsOK());
          if (!rowsOK()) u.p(S.rows.length + ' reading(s) so far. Need at least ' + NEED + ', spread over ' + (AMP ? '250' : '40') + ' °C or more.');
        },
        ok: function () { return rowsOK(); },
        auto: function () {
          for (var i = 0; i < NEED + 1; i++) {
            var tgt = TMIN + i * TSTEP; if (tgt > TMAX + 1 || tgt > p.Tcap - 5) break; setTarget(tgt);
            var n = 0; while (!ready() && n++ < 20000) runFor(2);
            if (!AMP) findNull(); record(); if (rowsOK()) break;
          }
          return Promise.resolve(); } },
    ],

    tick: function (dt) {
      if (st.on) runFor(Math.min(dt * st.speed, 8));
      var v = K.view(sim, p); thermo.set(sim.T); iThermo.set(0);
      if (galv) { st.dev = devNow(); galv.set(st.dev); } else { st.shownV += (v.Vout - st.shownV) * Math.min(1, dt * 5); drawDvm(st.placed ? st.shownV : 0); }
      hudT.set(r1(sim.T).toFixed(1) + ' °C'); hudE.set(AMP ? (st.placed ? (v.Vout * 1000).toFixed(1) + ' mV' : '—') : st.l.toFixed(1) + ' cm'); hudN.set(String(S.rows.length));
    },
  };
});
