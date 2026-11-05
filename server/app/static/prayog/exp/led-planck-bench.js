/* Prayogshala studio module: LED PLANCK BENCH (B.Sc. modern physics).
   A fine variable DC supply, a board of five LEDs of known peak wavelength (each with its own 220 ohm series
   resistor) under a black viewing shroud, a rotary selector that puts one LED in circuit, a digital voltmeter
   across the LED and a milliammeter in series with it.
   Physics: the `ledgap` kernel of packs/modern_ug.js on the lab's own params - the same code the server checks
   against e V0 = h c / lambda. The LEDs' peak wavelengths are lam1..lam5 of the lab. */
HoolaStudio.define('led-planck-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.ledgap, assign = HK.assign;
  var p = HK.paramsFor('ledgap', S.lab.params);
  var HPL = 6.62607015e-34, CL = 2.99792458e8, QEL = 1.602176634e-19;
  var LAMS = [p.lam1, p.lam2, p.lam3, p.lam4, p.lam5].filter(function (x) { return isFinite(x) && x > 1e-8; });
  var IREF_MA = p.Iref * 1000;
  var EMAX = 5, VLC = 0.001, ILC = 0.01;            // supply 0-5 V; voltmeter 1 mV; milliammeter 0.01 mA
  var st = { power: false, sel: 0, set: 0, traced: false, done: {} };

  function nm(lam) { return Math.round(lam * 1e9); }
  function colOf(lam) {
    var n = nm(lam);
    return n > 600 ? 0xe0261b : n > 570 ? 0xf2a51b : n > 495 ? 0x2fc25b : n > 440 ? 0x3a6df0 : 0x8a3ad0;
  }
  function nameOf(lam) {
    var n = nm(lam);
    return n > 600 ? 'Red' : n > 570 ? 'Amber' : n > 495 ? 'Green' : n > 440 ? 'Blue' : 'Violet';
  }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function atE(E, i) { var q = assign(p, { Eb: E, lam: LAMS[i === undefined ? st.sel : i] });
    var v = KN.view(KN.init(q, q), q, q); return { V: v.V, I: v.I }; }
  function now() { return st.power ? atE(st.set) : { V: 0, I: 0 }; }
  function readV() { return rnd(now().V, 3); }
  function readI() { return rnd(now().I * 1000, 2); }
  function turnOn(i) { var q = assign(p, { lam: LAMS[i] }); return KN.measure(q, q).V0; }

  // ================================================================ variable DC supply
  var psu = new T.Group(); S.scene.add(psu); psu.position.set(-0.46, 0, -0.18); psu.rotation.y = 0.26;
  var PW = 0.24, PD = 0.17, PH = 0.12;
  var cs = S.rounded(PW, PD, PH, 0.012, new T.MeshStandardMaterial({ color: 0xd9d5cb, roughness: 0.5, metalness: 0.15 }));
  cs.rotation.x = -Math.PI / 2; cs.position.y = PH / 2 + 0.004; psu.add(cs);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.004, 16), M.rubber);
    ft.position.set(f[0] * (PW / 2 - 0.02), 0.002, f[1] * (PD / 2 - 0.02)); psu.add(ft);
  });
  var FZ = PD / 2 + 0.0062, FW = PW - 0.014, FH = PH - 0.014, KX = -0.02, KY = -0.01;
  var psTex = S.canvasTex(1100, Math.round(1100 * FH / FW), function (x, w, h) {
    var X = function (u) { return (u / FW + 0.5) * w; }, Y = function (v) { return (0.5 - v / FH) * h; }, k = w / FW;
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.font = '700 38px "Public Sans", sans-serif'; x.fillText('REGULATED DC SUPPLY', 32, 62);
    x.font = '500 24px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText('0 – 5 V  ·  FINE  ·  0.5 A', 32, 98);
    var cx = X(KX), cy = Y(KY), R = 0.024 * k; x.strokeStyle = '#f1efe8'; x.fillStyle = '#f1efe8';
    for (var i = 0; i <= 25; i++) {
      var th = (225 - 270 * i / 25) * Math.PI / 180, big = i % 5 === 0;
      x.lineWidth = big ? 4 : 2; x.beginPath();
      x.moveTo(cx + Math.cos(th) * R, cy - Math.sin(th) * R);
      x.lineTo(cx + Math.cos(th) * (R + (big ? 20 : 11)), cy - Math.sin(th) * (R + (big ? 20 : 11))); x.stroke();
      if (big) { x.font = '600 24px "Public Sans", sans-serif'; x.textAlign = 'center';
        x.fillText(String(i / 5), cx + Math.cos(th) * (R + 44), cy - Math.sin(th) * (R + 44) + 8); }
    }
    x.textAlign = 'center'; x.font = '700 24px "Public Sans", sans-serif'; x.fillText('VOLTAGE  (V)', cx, Y(-0.046));
    x.fillText('POWER', X(-0.088), Y(-0.046)); x.fillText('OUTPUT', X(0.072), Y(0.022));
    x.font = '700 38px "Public Sans", sans-serif'; x.fillStyle = '#9aa3b2'; x.fillText('−', X(0.055), Y(-0.04));
    x.fillStyle = '#ff7a6b'; x.fillText('+', X(0.09), Y(-0.04)); x.textAlign = 'left';
  });
  var fascia = S.mesh(new T.BoxGeometry(FW, FH, 0.004),
    [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: psTex, roughness: 0.45 }), M.grey]);
  fascia.position.set(0, 0.004 + PH / 2, FZ - 0.002); psu.add(fascia);
  function pp(u, v, dz) { return new T.Vector3(u, 0.004 + PH / 2 + v, FZ + (dz || 0)); }
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  var knob = new T.Group(); knob.position.copy(pp(KX, KY)); psu.add(knob);
  var skirt = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.004, 40), M.bakelite); skirt.rotation.x = Math.PI / 2;
  skirt.position.z = 0.002; knob.add(skirt);
  var kb = S.mesh(new T.CylinderGeometry(0.0145, 0.016, 0.016, 40), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 }));
  kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; knob.add(kb);
  var kptr = S.mesh(new T.BoxGeometry(0.0022, 0.016, 0.0012), M.white, false); kptr.position.set(0, 0.009, 0.0215);
  knob.add(kptr);
  function knobAngle(E) { return 3 * Math.PI / 4 - 1.5 * Math.PI * (E / EMAX); }
  knob.rotation.z = knobAngle(0);
  var rocker = S.rounded(0.016, 0.024, 0.008, 0.003, M.bakelite); rocker.position.copy(pp(-0.088, -0.018, 0.004));
  psu.add(rocker);
  var rmk = S.mesh(new T.BoxGeometry(0.0018, 0.008, 0.001), M.white, false); rmk.position.set(0, 0.006, 0.0045);
  rocker.add(rmk);
  var lampM = new T.MeshStandardMaterial({ color: 0x5a1410, roughness: 0.3, emissive: 0x000000 });
  var pilot = S.mesh(new T.SphereGeometry(0.0055, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2), lampM);
  pilot.rotation.x = Math.PI / 2; pilot.position.copy(pp(-0.088, 0.012, 0)); psu.add(pilot);
  function post(u, mat) {
    var g = new T.Group(); g.position.copy(pp(u, -0.012)); psu.add(g);
    var stem = S.mesh(new T.CylinderGeometry(0.0028, 0.0028, 0.02, 16), M.brass); stem.rotation.x = Math.PI / 2;
    stem.position.z = 0.01; g.add(stem);
    var cap = S.mesh(new T.CylinderGeometry(0.0075, 0.0085, 0.012, 24), mat); cap.rotation.x = Math.PI / 2;
    cap.position.z = 0.012; g.add(cap); return g;
  }
  post(0.055, M.blackPlastic); post(0.09, M.red);
  function setPowerLook() {
    rocker.rotation.x = st.power ? -0.22 : 0.22;
    lampM.color.setHex(st.power ? 0xff3b2a : 0x5a1410); lampM.emissive.setHex(st.power ? 0xff2a14 : 0x000000);
    lampM.emissiveIntensity = st.power ? 2.2 : 0;
  }
  setPowerLook();
  S.contact(0.34, 0.26, -0.46, -0.18, 0.55);

  // ================================================================ LED board with its rotary selector
  var BX = 0.0, BZ = -0.08, BW = 0.34, BD = 0.16, BT = 0.012;
  var boardTex = S.canvasTex(1300, 620, function (x, w, h) {
    x.fillStyle = '#17572f'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.22)'; x.lineWidth = 3; x.strokeRect(14, 14, w - 28, h - 28);
    x.fillStyle = '#eef3ee'; x.textAlign = 'center'; x.font = '700 36px "Public Sans", sans-serif';
    x.fillText('LED BOARD  ·  PEAK WAVELENGTHS FROM THE DATASHEET', w / 2, 58);
    for (var i = 0; i < LAMS.length; i++) {
      var cx = w * (0.12 + 0.19 * i);
      x.font = '700 34px "Public Sans", sans-serif'; x.fillStyle = '#eef3ee';
      x.fillText(String(nm(LAMS[i])) + ' nm', cx, h * 0.52);
      x.font = '500 26px "Public Sans", sans-serif'; x.fillStyle = '#bcd6c4';
      x.fillText(nameOf(LAMS[i]), cx, h * 0.62);
      x.fillText('220 Ω', cx, h * 0.76);
    }
    x.textAlign = 'left';
  });
  var board = S.rounded(BW, BD, BT, 0.006, new T.MeshStandardMaterial({ color: 0x17572f, roughness: 0.65 }));
  board.rotation.x = -Math.PI / 2; board.position.set(BX, BT / 2, BZ); S.scene.add(board);
  var bplate = new T.Mesh(new T.PlaneGeometry(BW - 0.014, BD - 0.014),
    new T.MeshStandardMaterial({ map: boardTex, roughness: 0.7 }));
  bplate.rotation.x = -Math.PI / 2; bplate.position.set(BX, BT + 0.0004, BZ); S.scene.add(bplate);
  S.contact(BW + 0.06, BD + 0.06, BX, BZ, 0.5);
  var ledsG = new T.Group(); S.scene.add(ledsG);
  var ledMats = [], ledX = [];
  for (var li = 0; li < LAMS.length; li++) {
    var x0 = BX - BW / 2 + BW * (0.12 + 0.19 * li); ledX.push(x0);
    var col = colOf(LAMS[li]);
    var lm = new T.MeshStandardMaterial({ color: col, roughness: 0.14, transparent: true, opacity: 0.8,
      emissive: col, emissiveIntensity: 0 });
    var body = S.mesh(new T.CylinderGeometry(0.0025, 0.0025, 0.006, 24), lm);
    body.position.set(x0, BT + 0.004, BZ - 0.022); ledsG.add(body);
    var tip = S.mesh(new T.SphereGeometry(0.0025, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), lm);
    tip.position.set(x0, BT + 0.007, BZ - 0.022); ledsG.add(tip);
    var flange = S.mesh(new T.CylinderGeometry(0.0029, 0.0029, 0.0008, 24), lm);
    flange.position.set(x0, BT + 0.0014, BZ - 0.022); ledsG.add(flange);
    var res = S.mesh(new T.CylinderGeometry(0.0016, 0.0016, 0.009, 16),
      new T.MeshStandardMaterial({ color: 0xd9bf8c, roughness: 0.55 }));
    res.rotation.z = Math.PI / 2; res.position.set(x0, BT + 0.003, BZ + 0.03); ledsG.add(res);
    ledMats.push(lm);
  }
  // black viewing shroud over the LEDs, so a dim LED can still be seen
  var shroud = S.mesh(new T.BoxGeometry(BW - 0.02, 0.05, 0.05),
    new T.MeshStandardMaterial({ color: 0x15171a, roughness: 0.95, side: T.DoubleSide, transparent: true, opacity: 0.55 }));
  shroud.position.set(BX, BT + 0.026, BZ - 0.022); S.scene.add(shroud);
  // rotary selector
  var selG = new T.Group(); S.scene.add(selG); selG.position.set(BX - BW / 2 + 0.028, BT, BZ + 0.052);
  var selBase = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.006, 32), M.bakelite); selBase.position.y = 0.003;
  selG.add(selBase);
  var selKnob = new T.Group(); selKnob.position.y = 0.008; selG.add(selKnob);
  selKnob.add(S.mesh(new T.CylinderGeometry(0.014, 0.015, 0.012, 28), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })));
  var selPtr = S.mesh(new T.BoxGeometry(0.0022, 0.0015, 0.014), M.white, false); selPtr.position.set(0, 0.0065, -0.008);
  selKnob.add(selPtr);
  function selAngle(i) { return -0.9 + i * 1.8 / Math.max(1, LAMS.length - 1); }
  selKnob.rotation.y = selAngle(0);
  var selLbl = S.label('LED SELECT', { w: 0.05, ratio: 0.22, color: '#eef3ee' }); selLbl.rotation.x = -Math.PI / 2;
  selLbl.position.set(BX - BW / 2 + 0.028, BT + 0.0006, BZ + 0.072); S.scene.add(selLbl);

  // ================================================================ meters
  var mA = S.meter({ min: 0, max: 5, ticks: 5, unit: 'mA', symbol: 'mA', caption: 'D.C. MILLIAMMETER  0–5 mA',
    pos: [-0.16, 0, 0.14], rotY: 0.2 });
  var dmm = (function () {
    var g = new T.Group(); S.scene.add(g); g.position.set(0.3, 0, 0.08); g.rotation.y = -0.3;
    var W = 0.12, D = 0.16, Hh = 0.034;
    var body = S.rounded(W, D, Hh, 0.008, new T.MeshStandardMaterial({ color: 0xe0a93c, roughness: 0.55 }));
    body.rotation.x = -Math.PI / 2; body.position.y = Hh / 2; g.add(body);
    var faceP = S.mesh(new T.BoxGeometry(W - 0.01, 0.002, D - 0.01), M.bakelite); faceP.position.y = Hh + 0.001; g.add(faceP);
    var lcd = S.liveTex(512, 220), last = '';
    var scr = new T.Mesh(new T.PlaneGeometry(W - 0.024, 0.034), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
    scr.rotation.x = -Math.PI / 2; scr.position.set(0, Hh + 0.0025, -D / 2 + 0.032); g.add(scr);
    var bez = S.mesh(new T.BoxGeometry(W - 0.018, 0.003, 0.04), M.grey); bez.position.set(0, Hh + 0.0015, -D / 2 + 0.032);
    g.add(bez);
    var sel = new T.Group(); sel.position.set(0, Hh + 0.004, 0.016); g.add(sel);
    sel.add(S.mesh(new T.CylinderGeometry(0.016, 0.017, 0.008, 28), M.blackPlastic));
    var sp = S.mesh(new T.BoxGeometry(0.003, 0.002, 0.014), M.white, false); sp.position.set(0, 0.005, -0.009); sel.add(sp);
    [-0.024, 0.024].forEach(function (sx) {
      var sk = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.004, 16), sx < 0 ? M.blackPlastic : M.red);
      sk.position.set(sx, Hh + 0.001, D / 2 - 0.018); g.add(sk);
    });
    S.contact(W + 0.06, D + 0.06, 0.3, 0.08, 0.5);
    return { group: g, top: wpt(g, 0, Hh + 0.02, 0),
      show: function (txt) {
        if (txt === last) return; last = txt;
        lcd.draw(function (x) {
          var gr = x.createLinearGradient(0, 0, 0, 220); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
          x.fillStyle = gr; x.fillRect(0, 0, 512, 220);
          x.font = '700 100px "JetBrains Mono", monospace'; x.textAlign = 'right';
          x.fillStyle = 'rgba(0,0,0,.07)'; x.fillText('8.8.8.8', 430, 128);
          x.fillStyle = '#1b2116'; x.fillText(txt, 430, 128);
          x.font = '600 34px "Public Sans", sans-serif'; x.textAlign = 'left'; x.fillText('DC', 22, 198);
          x.textAlign = 'right'; x.fillText('VOLTS', 492, 198);
        });
      } };
  })();

  // ================================================================ wiring
  function mt(m, which) { var w = new T.Vector3(); m.updateMatrixWorld(true); m.userData[which].getWorldPosition(w);
    w.y += 0.004; return w; }
  var aP = mt(mA, 'plus'), aN = mt(mA, 'minus');
  S.wire([[-0.37, 0.03, -0.1], [-0.3, 0.025, 0.0], [aP.x - 0.02, 0.03, aP.z + 0.05], [aP.x, aP.y, aP.z]], 'red');
  S.wire([[aN.x, aN.y, aN.z], [aN.x - 0.02, 0.03, aN.z + 0.05], [-0.1, 0.02, -0.02], [BX - BW / 2 + 0.01, 0.02, BZ + 0.06]], 'black');
  S.wire([[BX + BW / 2 - 0.01, 0.02, BZ + 0.06], [0.2, 0.02, 0.0], [dmm.top.x - 0.01, 0.02, dmm.top.z], [dmm.top.x, dmm.top.y, dmm.top.z]], 'gold');
  S.wire([[-0.41, 0.03, -0.1], [-0.3, 0.012, 0.12], [0.1, 0.012, 0.18], [dmm.top.x + 0.01, 0.02, dmm.top.z + 0.01]], 'blue');

  S.addApparatus('psu', psu, 'Regulated DC supply (0–5 V)', 'A fine voltage knob: turned up slowly from zero so that the LED is never driven hard.');
  S.addApparatus('board', board, 'LED board', 'Five LEDs of known peak wavelength, each with its own 220 Ω series resistor. The rotary switch puts one of them in circuit.');
  S.addApparatus('leds', ledsG, 'The five LEDs', LAMS.map(function (l) { return nameOf(l) + ' ' + nm(l) + ' nm'; }).join(', ') + '. The black shroud over them lets you see the moment one just begins to glow.');
  S.addApparatus('sel', selG, 'LED selector', 'Turn it to put the LED you want in circuit. Only one LED carries current at a time.');
  S.addApparatus('ma', mA, 'Milliammeter (0–5 mA)', 'In series with the LED: the whole LED current goes through it.');
  S.addApparatus('dmm', dmm.group, 'Digital voltmeter', 'Across the LED alone, not across the resistor. It reads to a millivolt.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudL = S.hudCard('LED'), hudV = S.hudCard('Voltage across the LED'), hudI = S.hudCard('Current');

  // ================================================================ human actions
  function togglePower(on) {
    if (busy()) return Promise.resolve();
    if (on === st.power) return Promise.resolve();
    if (on && st.set > 0.001) { S.say('Turn the voltage knob back to zero before switching on.'); return Promise.resolve(); }
    return S.hand.tap(rocker, 'front').then(function () {
      st.power = on; setPowerLook(); S.click(900, 0.05);
      S.say(on ? 'Supply on, knob at zero.' : 'Supply off.'); S.render();
    });
  }
  function turnTo(E) {
    if (busy()) return Promise.resolve();
    if (!isFinite(E) || E < 0 || E > EMAX + 1e-9) { S.say('The supply goes from 0 to ' + EMAX + ' V only.'); return Promise.resolve(); }
    E = rnd(Math.max(0, Math.min(EMAX, E)), 3);
    var E0 = st.set, a0 = knobAngle(E0), pt = wpt(psu, KX, 0.004 + PH / 2 + KY, FZ + 0.024);
    if (Math.abs(E - E0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      st.set = E0 + (E - E0) * k; knob.rotation.z = knobAngle(st.set);
      S.hand.group.rotation.y = -(knobAngle(st.set) - a0) * 0.3;
    }, { mode: 'front', ms: 400 + 350 * Math.abs(E - E0), reachMs: 620 })
      .then(function () { st.set = E; knob.rotation.z = knobAngle(E); S.render(); });
  }
  function select(i) {
    if (busy()) return Promise.resolve(false);
    if (!(i >= 0 && i < LAMS.length)) { S.say('There are ' + LAMS.length + ' LEDs on the board.'); return Promise.resolve(false); }
    if (i === st.sel) return Promise.resolve(true);
    var a0 = selAngle(st.sel), a1 = selAngle(i), pt = wpt(selG, 0, 0.02, 0);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { selKnob.rotation.y = a0 + (a1 - a0) * k; },
      { mode: 'top', ms: 600, reachMs: 600 })
      .then(function () {
        st.sel = i; selKnob.rotation.y = a1;
        return turnTo(0).then(function () {
          S.say('The ' + nameOf(LAMS[i]).toLowerCase() + ' LED (' + nm(LAMS[i]) + ' nm) is in circuit, with the supply back at zero.');
          S.render(); return true;
        });
      });
  }
  /* The real procedure: creep the supply up until the milliammeter reads the reference current. */
  function raiseToRef() {
    if (busy()) return Promise.resolve(false);
    if (!st.power) { S.say('Switch the supply on first.'); return Promise.resolve(false); }
    var lo = 0, hi = EMAX, i, mid;
    for (i = 0; i < 60; i++) { mid = (lo + hi) / 2; if (atE(mid).I * 1000 < IREF_MA) lo = mid; else hi = mid; }
    var target = rnd((lo + hi) / 2, 3);
    if (atE(target).I * 1000 < IREF_MA - ILC) { S.say('Even at ' + EMAX + ' V this LED does not reach ' + IREF_MA.toFixed(2) + ' mA.'); return Promise.resolve(false); }
    return turnTo(Math.max(0, target - 0.25)).then(function () { return turnTo(target); })
      .then(function () {
        S.say('The milliammeter reads ' + readI().toFixed(2) + ' mA; the voltmeter across the LED reads ' + readV().toFixed(3) + ' V.');
        S.render(); return true;
      });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.power) { S.say('Switch the supply on first.'); return false; }
    var lam = LAMS[st.sel];
    if (Math.abs(readI() - IREF_MA) > ILC + 1e-9) { S.say('Set the current to ' + IREF_MA.toFixed(2) + ' mA first: it reads ' + readI().toFixed(2) + ' mA.'); return false; }
    if (st.done[nm(lam)]) { S.say('You already have the ' + nm(lam) + ' nm LED. Turn the selector to another one.'); return false; }
    st.done[nm(lam)] = true;
    S.addRow({ nm: nm(lam), inv: 1 / lam, V0: readV() });
    S.say('Written in your record book: ' + nm(lam) + ' nm, turn-on voltage ' + readV().toFixed(3) + ' V.');
    return true;
  }
  function trace() {
    st.traced = true; S.focus('board');
    S.say('Supply (+) to the milliammeter, on to the selector, through the chosen LED and its 220 Ω resistor, back to the supply (−). The voltmeter is across the LED alone.');
    S.render();
  }

  function result(rows) {
    var pts = rows.map(function (r) { return [r.inv, r.V0]; })
      .filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); });
    if (pts.length < 3) return null;
    var f = S.fit.linear(pts);
    if (!f) return null;
    return { label: 'Planck\'s constant h', value: QEL * f.m / CL * 1e34, unit: '× 10⁻³⁴ J·s', digits: 3,
      truth: HPL * 1e34,
      note: 'Slope of V₀ against 1/λ is ' + f.m.toExponential(3) + ' V·m = hc/e; multiplying by e/c gives h.' };
  }

  return {
    camera: { pos: [-0.02, 0.86, 1.02], look: [-0.06, 0.06, -0.06] },
    views: { psu: [[-0.4, 0.3, 0.1], [-0.46, 0.08, -0.18]], board: [[0.0, 0.3, 0.14], [0.0, 0.02, -0.07]],
      leds: [[-0.06, 0.12, 0.06], [-0.06, 0.02, -0.1]], sel: [[-0.14, 0.16, 0.06], [-0.14, 0.02, -0.03]],
      ma: [[-0.16, 0.24, 0.36], [-0.16, 0.05, 0.14]], dmm: [[0.3, 0.24, 0.3], [0.3, 0.03, 0.08]],
      bench: [[-0.02, 0.86, 1.02], [-0.06, 0.06, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A light-emitting diode gives out one photon of its own colour for every electron that crosses the junction, so the junction cannot pass a current until the applied voltage can pay for that photon. The voltage at which it just begins to conduct therefore measures the photon energy.',
      formula: 'e V₀ = h c / λ',
      formulaNote: 'so V₀ against 1/λ is a straight line of slope hc/e; multiply the slope by e/c to get h',
      more: ['The LEDs on this board are ' + LAMS.map(function (l) { return nameOf(l).toLowerCase() + ' ' + nm(l) + ' nm'; }).join(', ') + ', each with its own 220 Ω series resistor.',
        'The turn-on voltage is taken at one fixed small current - here ' + IREF_MA.toFixed(2) + ' mA - for every LED, so that all five are compared in the same way.',
        'The voltmeter must sit across the LED alone. Across the LED and resistor together it would read the supply voltage and the answer would be nonsense.'],
      precautions: 'Start at zero volts and come up slowly. Keep the series resistor in circuit. Use the same reference current for every LED, and read the voltmeter to the millivolt.' },
    book: { title: 'Expt. — Planck\'s constant from LEDs',
      lines: ['Aim: turn-on voltage of five LEDs; h from the slope.', 'Reference current for every LED: ' + IREF_MA.toFixed(2) + ' mA.',
        'Series resistor 220 Ω; voltmeter across the LED only.', 'e V₀ = h c / λ;  slope of V₀ vs 1/λ = hc/e.',
        'Peak wavelengths from the makers\' datasheets.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'λ (nm)', get: function (r) { return r.nm; } },
        { label: '1/λ (10⁶ /m)', get: function (r) { return (r.inv / 1e6).toFixed(3); } },
        { label: 'V₀ (V)', get: function (r) { return r.V0.toFixed(3); } }] },
    graph: { x: function (r) { return r.inv / 1e6; }, y: function (r) { return r.V0; },
      xlabel: '1/λ (10⁶ /m)', ylabel: 'V₀ (V)',
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.03,
    resultNote: 'Five LEDs, five colours, one straight line: the energy of a photon is proportional to its frequency, and the constant of proportionality is Planck\'s constant. A real board gives h a few per cent out, because the peak wavelength of an LED is a band and not a line.',
    chips: ['Why does a blue LED need more voltage?', 'Why the same current for every LED?',
      'Why is the voltmeter across the LED only?', 'Check my readings', 'What does the intercept mean?'],
    viva: [['An LED lights only above a certain voltage because', ['Each electron must pay for one photon of hc/λ', 'The resistor blocks it', 'The meter is slow'], 0,
      'The junction cannot conduct until the applied energy per electron reaches the photon energy.'],
      ['Of these LEDs, the largest turn-on voltage belongs to', ['The shortest wavelength', 'The longest wavelength', 'The brightest'], 0,
        'V₀ = hc/eλ, so the smallest λ needs the largest V₀.'],
      ['The voltmeter is put across the LED alone because', ['The resistor also drops voltage', 'It reads faster', 'The LED has no resistance'], 0,
        'Across both, it would read the supply voltage, not the junction voltage.']],
    askState: function () {
      return { experiment: 'Planck\'s constant from the turn-on voltages of LEDs of five colours',
        supply_on: st.power, supply_setting_V: +st.set.toFixed(3),
        led: nameOf(LAMS[st.sel]) + ' ' + nm(LAMS[st.sel]) + ' nm',
        voltage_across_led_V: readV(), current_mA: readI(), reference_current_mA: IREF_MA,
        turn_on_voltage_here_V: +turnOn(st.sel).toFixed(3), readings_taken: S.rows.length };
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'board', render: function (u) {
          u.h2('Trace the circuit and switch on');
          u.p('Supply (+) → milliammeter → selector → the chosen LED and its 220 Ω resistor → supply (−). The voltmeter sits across the LED alone.');
          u.task('1. Trace the circuit', st.traced, st.traced ? 'Meter in series, voltmeter across the LED' : 'Follow the leads from the supply')
            .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
          u.task('2. Knob to zero, then switch on', st.power, st.power ? 'Supply on at ' + st.set.toFixed(2) + ' V' : 'The hand presses the POWER rocker')
            .add(u.row(u.button(st.power ? 'Switch off' : 'Switch the supply on', function () { S.focus('psu'); togglePower(!st.power); }, !st.power, S.hand.busy),
              u.button('Knob to zero', function () { S.focus('psu'); turnTo(0); }, false, S.hand.busy || st.set === 0)));
          u.task('3. Put the red LED in circuit', st.sel === 0, 'Selector on ' + nm(LAMS[st.sel]) + ' nm')
            .add(u.button('Selector to ' + nm(LAMS[0]) + ' nm', function () { S.focus('sel'); select(0); }, false, S.hand.busy));
          u.live(function () { return st.power ? 'LED ' + nm(LAMS[st.sel]) + ' nm  ·  ' + readV().toFixed(3) + ' V  ·  ' + readI().toFixed(2) + ' mA' : 'Supply off'; });
          u.note('Always come up from zero volts: an LED switched straight to a high voltage is destroyed at once.');
          u.next('Next: measure the turn-on voltages', st.traced && st.power);
        },
        ok: function () { return st.traced && st.power; },
        auto: function () { trace(); return turnTo(0).then(function () { return togglePower(true); })
          .then(function () { return select(0); }); } },

      { id: 'read', title: 'Turn-on voltages', view: 'board', render: function (u) {
          u.h2('Set the same current in every LED and read its voltage');
          u.p('For each LED, raise the supply until the milliammeter reads ' + IREF_MA.toFixed(2) + ' mA, then read the voltmeter and record it. Under the black shroud you can see the LED just beginning to glow at that point.');
          var sel = { i: st.sel };
          u.slider('LED on the selector', 1, LAMS.length, 1, function () { return sel.i + 1; },
            function (v) { sel.i = Math.round(v) - 1; }, '', 0);
          u.row(u.button('Turn the selector', function () { S.focus('sel'); select(sel.i); }, true, S.hand.busy),
            u.button('Raise to ' + IREF_MA.toFixed(2) + ' mA', function () { S.focus('psu'); raiseToRef(); }, false, S.hand.busy));
          u.row(u.button('Record λ and V₀', function () { record(); }, false, S.hand.busy),
            u.button('Knob to zero', function () { turnTo(0); }, false, S.hand.busy || st.set === 0));
          u.live(function () { return nameOf(LAMS[st.sel]) + ' ' + nm(LAMS[st.sel]) + ' nm  ·  ' + readV().toFixed(3) + ' V  ·  ' + readI().toFixed(2) + ' mA'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 4) u.p(S.rows.length + ' of at least 4 LEDs recorded (all five is better).');
          u.next('Next: plot V₀ against 1/λ', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          var order = [];
          for (var i = 0; i < LAMS.length; i++) order.push(i);
          return order.reduce(function (pr, i) {
            return pr.then(function () { return select(i); })
              .then(function () { return raiseToRef(); })
              .then(function (ok) { if (ok) record(); });
          }, Promise.resolve());
        } },
    ],

    tick: function () {
      var cur = now();
      mA.set(cur.I * 1000);
      dmm.show(st.power ? readV().toFixed(3) : '0.000');
      for (var i = 0; i < ledMats.length; i++) {
        ledMats[i].emissiveIntensity = (i === st.sel) ? Math.min(2.6, cur.I * 1000 / 1.2) : 0;
      }
      hudL.set(nameOf(LAMS[st.sel]) + ' ' + nm(LAMS[st.sel]) + ' nm');
      hudV.set(st.power ? readV().toFixed(3) + ' V' : '—');
      hudI.set(st.power ? readI().toFixed(2) + ' mA' : '—');
    },
  };
});
