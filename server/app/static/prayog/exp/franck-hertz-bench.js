/* Prayogshala studio module: FRANCK-HERTZ BENCH (B.Sc. modern physics).
   The tube in its thermostatted oven with a glass window, and the Franck-Hertz control unit: an accelerating
   voltage knob, a digital voltmeter and an electrometer reading the collector current in nanoamperes.
   Physics: the `fhtube` kernel of packs/modern_ug.js on the lab's own params - the same code the server checks.
   The student hunts each current peak with the knob, exactly as in the real experiment, and the spacing of the
   peaks is the first excitation potential of the gas in the tube. */
HoolaStudio.define('franck-hertz-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.fhtube, assign = HK.assign;
  var p = HK.paramsFor('fhtube', S.lab.params);
  var V_ = S.lab.variant || {}, GAS = V_.sample || 'Mercury vapour tube';
  var VMAX = p.Vmax, VSTEP = 0.1, OVEN_SET = /neon/i.test(GAS) ? 25 : 180;   // neon needs no oven
  var NEON = /neon|argon/i.test(GAS);
  var st = { heat: false, warm: NEON, V: 0, traced: false, peaks: 0 };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function curAt(v) { return KN.current(v, p) * 1e9; }            // nanoamperes
  function readI() { return st.warm ? rnd(curAt(st.V), 3) : 0; }
  function readV() { return rnd(st.V, 1); }

  // ================================================================ oven with the tube inside
  var oven = new T.Group(); S.scene.add(oven); oven.position.set(-0.4, 0, -0.14);
  var OW = 0.24, OD = 0.22, OH = 0.26;
  var shellM = new T.MeshStandardMaterial({ color: 0x51575f, roughness: 0.55, metalness: 0.45 });
  /* The oven is built from real panels with a real opening in the front, so the tube can be seen through the
     window instead of the window being a patch painted on a solid box. */
  var WW = 0.13, WH = 0.15, WY = 0.14, TH = 0.008;
  var shell = new T.Group(); oven.add(shell);
  function panel(w, h, d, x, y, z) { var m = S.mesh(new T.BoxGeometry(w, h, d), shellM);
    m.position.set(x, y, z); shell.add(m); return m; }
  panel(OW, TH, OD, 0, TH / 2 + 0.004, 0);                                   // floor
  panel(OW, OH, TH, 0, OH / 2 + 0.004, -OD / 2 + TH / 2);                    // back
  panel(TH, OH, OD, -OW / 2 + TH / 2, OH / 2 + 0.004, 0);                    // left
  panel(TH, OH, OD, OW / 2 - TH / 2, OH / 2 + 0.004, 0);                     // right
  var FZP = OD / 2 - TH / 2;
  panel((OW - WW) / 2, OH, TH, -(WW + (OW - WW) / 2) / 2, OH / 2 + 0.004, FZP);   // front, left of the window
  panel((OW - WW) / 2, OH, TH, (WW + (OW - WW) / 2) / 2, OH / 2 + 0.004, FZP);    // front, right of the window
  panel(WW, OH - (WY + WH / 2), TH, 0, (WY + WH / 2 + OH) / 2 + 0.004, FZP);      // front, above the window
  panel(WW, WY - WH / 2, TH, 0, (WY - WH / 2) / 2 + 0.004, FZP);                  // front, below the window
  var lid = S.rounded(OW + 0.02, OD + 0.02, 0.016, 0.006, shellM); lid.rotation.x = -Math.PI / 2;
  lid.position.y = OH + 0.012; oven.add(lid);
  var handle = S.mesh(new T.TorusGeometry(0.022, 0.0035, 10, 24, Math.PI), M.chrome);
  handle.position.set(0, OH + 0.02, 0); handle.rotation.x = -Math.PI / 2; oven.add(handle);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.006, 16), M.rubber);
    ft.position.set(f[0] * (OW / 2 - 0.02), 0.003, f[1] * (OD / 2 - 0.02)); oven.add(ft);
  });
  var winM = new T.MeshStandardMaterial({ color: 0xdfe6ea, roughness: 0.08, metalness: 0.0,
    transparent: true, opacity: 0.16 });
  var win = S.mesh(new T.BoxGeometry(WW, WH, 0.003), winM, false, false);
  win.position.set(0, WY + 0.004, OD / 2 - TH / 2); oven.add(win);
  var frame = S.mesh(new T.TorusGeometry(0.088, 0.004, 8, 4), M.iron);
  frame.position.set(0, WY + 0.004, OD / 2 + 0.001); frame.rotation.z = Math.PI / 4; oven.add(frame);
  // the tube: cathode, grid, collector
  var tubeM = new T.MeshPhysicalMaterial({ color: 0xdfe5ea, roughness: 0.06, transmission: 0.7, thickness: 0.01,
    transparent: true, opacity: 0.4 });
  var tube = S.mesh(new T.CylinderGeometry(0.045, 0.045, 0.13, 32), tubeM); tube.position.set(0, 0.14, 0);
  oven.add(tube);
  var tcap = S.mesh(new T.SphereGeometry(0.045, 28, 16, 0, Math.PI * 2, 0, Math.PI / 2), tubeM);
  tcap.position.set(0, 0.205, 0); oven.add(tcap);
  var filM = new T.MeshStandardMaterial({ color: 0x6b5a2a, roughness: 0.4, emissive: 0x000000 });
  var fil = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.03, 12), filM); fil.position.set(0, 0.1, 0);
  oven.add(fil);
  var gridM = new T.MeshStandardMaterial({ color: 0xbfc5cc, roughness: 0.3, metalness: 0.9 });
  var grid = S.mesh(new T.TorusGeometry(0.026, 0.0012, 8, 28), gridM); grid.rotation.x = Math.PI / 2;
  grid.position.set(0, 0.15, 0); oven.add(grid);
  for (var gi = -2; gi <= 2; gi++) {
    var gw = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.05, 6), gridM);
    gw.rotation.z = Math.PI / 2; gw.position.set(0, 0.15, gi * 0.009); oven.add(gw);
  }
  var coll = S.mesh(new T.CylinderGeometry(0.026, 0.026, 0.002, 28), gridM); coll.position.set(0, 0.175, 0);
  oven.add(coll);
  var glowM = new T.MeshBasicMaterial({ color: NEON ? 0xff6a3a : 0x6fb2ff, transparent: true, opacity: 0,
    depthWrite: false, blending: T.AdditiveBlending });
  var glow = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.045, 24, 1, true), glowM, false, false);
  glow.position.set(0, 0.127, 0); oven.add(glow);
  var inside = new T.PointLight(0xfff0d8, 0.55, 0.6); inside.position.set(0, 0.15, 0.03); oven.add(inside);
  var ovenLbl = S.label(NEON ? 'FRANCK–HERTZ TUBE (NEON)' : 'FRANCK–HERTZ TUBE IN OVEN',
    { w: 0.17, ratio: 0.13, color: '#e8eaec' });
  ovenLbl.position.set(0, 0.03, OD / 2 + 0.006); oven.add(ovenLbl);
  var thermoM = new T.MeshStandardMaterial({ color: 0xb8322a, roughness: 0.4 });
  var thermo = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.12, 12), M.glass);
  thermo.position.set(0.085, 0.16, 0.04); oven.add(thermo);
  S.contact(0.34, 0.3, -0.4, -0.14, 0.55);

  // ================================================================ control unit
  var unit = new T.Group(); S.scene.add(unit); unit.position.set(0.26, 0, -0.06); unit.rotation.y = -0.3;
  var UW = 0.4, UD = 0.26, UH = 0.14;
  var ucase = S.rounded(UW, UD, UH, 0.012, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5, metalness: 0.12 }));
  ucase.rotation.x = -Math.PI / 2; ucase.position.y = UH / 2 + 0.004; unit.add(ucase);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.004, 16), M.rubber);
    ft.position.set(f[0] * (UW / 2 - 0.02), 0.002, f[1] * (UD / 2 - 0.02)); unit.add(ft);
  });
  var FZ = UD / 2 + 0.0062, PW = UW - 0.014, PH = UH - 0.014, KX = 0.1, KY = -0.016;
  var uTex = S.canvasTex(1400, Math.round(1400 * PH / PW), function (x, w, h) {
    var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; }, k = w / PW;
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.font = '700 40px "Public Sans", sans-serif';
    x.fillText('FRANCK – HERTZ CONTROL UNIT', 34, 62);
    x.font = '500 24px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6';
    x.fillText('ACCELERATING 0 – ' + VMAX + ' V  ·  ELECTROMETER 0 – 20 nA  ·  OVEN ' + OVEN_SET + ' °C', 34, 98);
    var cx = X(KX), cy = Y(KY), R = 0.026 * k; x.strokeStyle = '#f1efe8'; x.fillStyle = '#f1efe8';
    for (var i = 0; i <= 20; i++) {
      var th = (225 - 270 * i / 20) * Math.PI / 180, big = i % 5 === 0;
      x.lineWidth = big ? 4 : 2; x.beginPath();
      x.moveTo(cx + Math.cos(th) * R, cy - Math.sin(th) * R);
      x.lineTo(cx + Math.cos(th) * (R + (big ? 20 : 11)), cy - Math.sin(th) * (R + (big ? 20 : 11))); x.stroke();
      if (big) { x.font = '600 22px "Public Sans", sans-serif'; x.textAlign = 'center';
        x.fillText(String(Math.round(VMAX * i / 20)), cx + Math.cos(th) * (R + 42), cy - Math.sin(th) * (R + 42) + 8); }
    }
    x.textAlign = 'center'; x.font = '700 24px "Public Sans", sans-serif';
    x.fillText('ACCELERATING VOLTAGE', cx, Y(-0.05));
    x.fillText('VOLTS', X(-0.125), Y(-0.05)); x.fillText('COLLECTOR CURRENT (nA)', X(-0.125), Y(0.044));
    x.fillText('HEATER', X(0.012), Y(-0.05)); x.textAlign = 'left';
  });
  var ufac = S.mesh(new T.BoxGeometry(PW, PH, 0.004),
    [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: uTex, roughness: 0.45 }), M.grey]);
  ufac.position.set(0, 0.004 + UH / 2, FZ - 0.002); unit.add(ufac);
  function up(u, v, dz) { return new T.Vector3(u, 0.004 + UH / 2 + v, FZ + (dz || 0)); }
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  var knob = new T.Group(); knob.position.copy(up(KX, KY)); unit.add(knob);
  var skirt = S.mesh(new T.CylinderGeometry(0.021, 0.022, 0.004, 40), M.bakelite); skirt.rotation.x = Math.PI / 2;
  skirt.position.z = 0.002; knob.add(skirt);
  var kb = S.mesh(new T.CylinderGeometry(0.016, 0.018, 0.018, 40), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 }));
  kb.rotation.x = Math.PI / 2; kb.position.z = 0.013; knob.add(kb);
  var kptr = S.mesh(new T.BoxGeometry(0.0022, 0.018, 0.0012), M.white, false); kptr.position.set(0, 0.01, 0.0235);
  knob.add(kptr);
  function knobAngle(v) { return 3 * Math.PI / 4 - 1.5 * Math.PI * (v / VMAX); }
  knob.rotation.z = knobAngle(0);
  var heat = S.rounded(0.018, 0.026, 0.009, 0.003, M.bakelite); heat.position.copy(up(0.012, -0.022, 0.004));
  unit.add(heat);
  var hmk = S.mesh(new T.BoxGeometry(0.002, 0.009, 0.001), M.white, false); hmk.position.set(0, 0.007, 0.005);
  heat.add(hmk);
  var warmM = new T.MeshStandardMaterial({ color: 0x4a3410, roughness: 0.3, emissive: 0x000000 });
  var warmLamp = S.mesh(new T.SphereGeometry(0.005, 18, 12, 0, Math.PI * 2, 0, Math.PI / 2), warmM);
  warmLamp.rotation.x = Math.PI / 2; warmLamp.position.copy(up(0.012, 0.008, 0)); unit.add(warmLamp);
  function lcd(cx, cy, wdt, hgt) {
    var tex = S.liveTex(512, 190), last = '';
    var bez = S.mesh(new T.BoxGeometry(wdt + 0.006, hgt + 0.006, 0.003), M.grey);
    bez.position.copy(up(cx, cy, 0.001)); unit.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(wdt, hgt), new T.MeshBasicMaterial({ map: tex, toneMapped: false }));
    scr.position.copy(up(cx, cy, 0.004)); unit.add(scr);
    return function (txt, u2) {
      if (txt + u2 === last) return; last = txt + u2;
      tex.draw(function (x) {
        var gr = x.createLinearGradient(0, 0, 0, 190); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
        x.fillStyle = gr; x.fillRect(0, 0, 512, 190);
        x.font = '700 92px "JetBrains Mono", monospace'; x.textAlign = 'right';
        x.fillStyle = 'rgba(0,0,0,.07)'; x.fillText('88.888', 420, 118);
        x.fillStyle = '#1b2116'; x.fillText(txt, 420, 118);
        x.font = '600 32px "Public Sans", sans-serif'; x.fillText(u2, 494, 170);
      });
    };
  }
  var showV = lcd(-0.125, -0.02, 0.1, 0.034), showI = lcd(-0.125, 0.024, 0.1, 0.034);
  showV('0.0', 'V'); showI('0.000', 'nA');   // the displays read before the first tick
  S.contact(0.5, 0.34, 0.26, -0.06, 0.55);

  // ================================================================ cables
  S.wire([[-0.3, 0.03, -0.06], [-0.1, 0.02, 0.0], [0.12, 0.02, 0.02]], 'red');
  S.wire([[-0.3, 0.03, -0.1], [-0.08, 0.014, 0.06], [0.16, 0.014, 0.04]], 'black');
  S.wire([[-0.28, 0.03, -0.02], [-0.04, 0.01, 0.1], [0.2, 0.012, 0.06]], 'blue');

  S.addApparatus('oven', oven, NEON ? 'Franck-Hertz tube' : 'Franck-Hertz tube in its oven',
    GAS + '. Cathode, grid and collector stand in the vapour; electrons are accelerated to the grid and have to climb a small retarding voltage to be collected.');
  S.addApparatus('unit', unit, 'Franck-Hertz control unit',
    'The big knob sets the accelerating voltage; the two displays read that voltage and the collector current in nanoamperes. The small rocker switches the heater on.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudV = S.hudCard('Accelerating voltage'), hudI = S.hudCard('Collector current'), hudP = S.hudCard('Peaks marked');

  // ================================================================ human actions
  function setHeater(on) {
    if (busy()) return Promise.resolve();
    if (on === st.heat) return Promise.resolve();
    return S.hand.tap(heat, 'front').then(function () {
      st.heat = on;
      warmM.color.setHex(on ? 0xffb020 : 0x4a3410); warmM.emissive.setHex(on ? 0xffa000 : 0x000000);
      warmM.emissiveIntensity = on ? 2 : 0;
      filM.emissive = new T.Color(on ? 0xff9a3a : 0x000000); filM.emissiveIntensity = on ? 2.4 : 0;
      if (on) {
        st.warm = true;
        S.say(NEON ? 'Heater on: the cathode is hot and the tube is ready.'
          : 'Heater on. The oven climbs to ' + OVEN_SET + ' °C and is held there, so the vapour pressure stays the same through the whole sweep.');
      } else { S.say('Heater off.'); }
      S.click(820, 0.05); S.render();
    });
  }
  function turnTo(v) {
    if (busy()) return Promise.resolve();
    if (!isFinite(v) || v < 0 || v > VMAX + 1e-9) { S.say('The accelerating voltage goes from 0 to ' + VMAX + ' V only. Past that the tube strikes a continuous discharge.'); return Promise.resolve(); }
    v = rnd(Math.max(0, Math.min(VMAX, v)), 1);
    var v0 = st.V, a0 = knobAngle(v0), pt = wpt(unit, KX, 0.004 + UH / 2 + KY, FZ + 0.026);
    if (Math.abs(v - v0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      st.V = rnd(v0 + (v - v0) * k, 2); knob.rotation.z = knobAngle(st.V);
      S.hand.group.rotation.y = -(knobAngle(st.V) - a0) * 0.3;
    }, { mode: 'front', ms: 350 + 25 * Math.abs(v - v0), reachMs: 600 })
      .then(function () { st.V = v; knob.rotation.z = knobAngle(v); S.render(); });
  }
  function recordPoint() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.warm) { S.say('Switch the heater on and let the tube warm up first.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.V - st.V) < 0.05; })) { S.say('You already have a reading at ' + readV().toFixed(1) + ' V.'); return false; }
    S.addRow({ V: readV(), I: readI(), peak: false });
    return true;
  }
  /* Hunting a peak the way a student does: step the knob up while the display rises, stop when it falls. */
  function huntPeak() {
    if (busy()) return Promise.resolve(false);
    if (!st.warm) { S.say('Switch the heater on and let the tube warm up first.'); return Promise.resolve(false); }
    /* Step the knob up: through the dip first if the knob is already on a peak, then on to the top of the
       next rise, and stop the moment the display starts to fall again. */
    var v = st.V, prev = curAt(v), rising = false, best = -1, ii;
    while (v + VSTEP <= VMAX) {
      v = rnd(v + VSTEP, 2); ii = curAt(v);
      if (ii > prev) { rising = true; } else if (rising) { best = rnd(v - VSTEP, 2); break; }
      prev = ii;
    }
    if (best < 0) {
      S.say('No further peak above ' + readV().toFixed(1) + ' V within the tube\'s safe range.');
      return Promise.resolve(false);
    }
    return turnTo(best).then(function () {
      if (S.rows.some(function (r) { return r.peak && Math.abs(r.V - st.V) < 0.5; })) {
        S.say('This peak is already marked. Turn the knob past it and hunt the next one.'); S.render(); return false;
      }
      st.peaks += 1;
      S.addRow({ V: readV(), I: readI(), peak: true, n: st.peaks });
      S.say('Peak ' + st.peaks + ' marked at ' + readV().toFixed(1) + ' V, where the current reads ' + readI().toFixed(3) + ' nA and starts to fall.');
      S.render(); return true;
    });
  }
  function trace() {
    st.traced = true; S.focus('oven');
    S.say('Inside the tube: the hot cathode at the bottom, the grid across the middle, the collector plate above it. Electrons are pulled from the cathode to the grid by the accelerating voltage; only those still fast enough climb the small retarding voltage to the collector.');
    S.render();
  }

  function result(rows) {
    var pk = rows.filter(function (r) { return r.peak; })
      .map(function (r) { return r.V; }).sort(function (a, b) { return a - b; });
    if (pk.length < 3) return null;
    var pts = pk.map(function (v, i) { return [i + 1, v]; });
    var f = S.fit.linear(pts);
    if (!f) return null;
    return { label: 'First excitation potential', value: f.m, unit: 'V', digits: 2, truth: p.Ue,
      note: 'Slope of peak voltage against peak number, from ' + pk.length + ' peaks. The intercept, ' + f.c.toFixed(2) + ' V, is the contact potential of the electrodes, which is why the first peak is not at the excitation potential itself.' };
  }

  return {
    camera: { pos: [-0.04, 1.0, 1.24], look: [-0.06, 0.13, -0.08] },
    views: { oven: [[-0.22, 0.4, 0.46], [-0.4, 0.15, -0.14]], unit: [[0.3, 0.34, 0.3], [0.26, 0.08, -0.06]],
      bench: [[-0.04, 1.0, 1.24], [-0.06, 0.13, -0.08]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'An atom can only take energy from an electron in the exact amount of one of its own jumps. Below the first excitation energy every collision is elastic and the current climbs with the accelerating voltage; the moment an electron has gained that energy it can lose all of it in one collision, arrives too slow to climb the retarding voltage, and the current falls. The pattern repeats, so the current peaks are one excitation potential apart.',
      formula: 'ΔV = U₁  (the spacing of the peaks)',
      formulaNote: 'e U₁ is the energy of the atom\'s first excited state above its ground state',
      more: ['The whole curve is shifted along the voltage axis by the contact potential between the cathode and the grid, so only the SPACING of the peaks may be used, never the position of the first one.',
        NEON ? 'In a neon tube the glow between the grid and the cathode breaks into bright layers as the voltage is raised: each layer is a sheet of atoms being excited.'
          : 'The oven holds the mercury at a steady temperature. Too cold and the vapour is too thin to give deep dips; too hot and the electrons cannot reach the grid at all.',
        'The collector current is a few nanoamperes, so it is read on an electrometer, and the leads must be kept still while reading.'],
      precautions: 'Let the tube reach its working temperature before any reading. Never take the accelerating voltage past the maximum marked on the tube, or it strikes a continuous discharge and is destroyed. Hunt each peak from below, in steps of ' + VSTEP.toFixed(1) + ' V.' },
    book: { title: 'Expt. — Franck-Hertz experiment',
      lines: ['Aim: first excitation potential from the peak spacing.', 'Tube: ' + GAS,
        NEON ? 'No oven needed; cathode heater on.' : 'Oven held at ' + OVEN_SET + ' °C.',
        'Accelerating voltage 0–' + VMAX + ' V, knob step ' + VSTEP.toFixed(1) + ' V.',
        'Collector current read on the electrometer (nA).',
        'Spacing of the peaks = first excitation potential.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'V (V)', get: function (r) { return r.V.toFixed(1); } },
        { label: 'I (nA)', get: function (r) { return r.I.toFixed(3); } },
        { label: 'Peak', get: function (r) { return r.peak ? 'peak ' + r.n : ''; } }] },
    graph: { x: function (r) { return r.V; }, y: function (r) { return r.I; }, xlabel: 'V (V)', ylabel: 'I (nA)',
      x0: 0, y0: 0,
      line: function (pts) {
        var q = pts.slice().sort(function (a, b) { return a[0] - b[0]; });
        return function (x) {
          if (x <= q[0][0]) return q[0][1];
          for (var i = 0; i < q.length - 1; i++) {
            if (x <= q[i + 1][0]) { var a = q[i], b = q[i + 1];
              return b[0] === a[0] ? b[1] : a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]); }
          }
          return q[q.length - 1][1];
        };
      } },
    result: result,
    tol: 0.03,
    resultNote: 'Peaks at even spacings are the whole result: the atom accepts energy only in one fixed amount, which is exactly what Bohr had claimed and what Franck and Hertz showed in 1914 with electrons instead of light.',
    chips: ['Why does the current fall after each peak?', 'Why use only the spacing of the peaks?',
      'What does the oven temperature change?', 'Check my readings', 'What has this to do with Bohr?'],
    viva: [['The spacing of the current peaks gives', ['The first excitation potential', 'The ionisation potential', 'The work function'], 0,
      'Each dip is one inelastic collision in which the atom takes its first excitation energy.'],
      ['The position of the first peak is not the excitation potential because of', ['The contact potential', 'The oven', 'The electrometer'], 0,
        'The contact potential between the electrodes shifts the whole curve.'],
      ['The collisions below the first dip are', ['Elastic', 'Inelastic', 'Ionising'], 0,
        'The electron has too little energy to excite the atom, so it keeps its speed.']],
    askState: function () {
      return { experiment: 'Franck-Hertz: first excitation potential from the spacing of the current peaks',
        tube: GAS, heater_on: st.heat, warmed_up: st.warm, accelerating_voltage_V: readV(),
        collector_current_nA: readI(), peaks_marked: st.peaks, readings_taken: S.rows.length,
        voltage_limit_V: VMAX };
    },

    steps: [
      { id: 'warm', title: 'Warm up', view: 'oven', render: function (u) {
          u.h2('Look inside the tube, then switch the heater on');
          u.p(NEON ? 'A neon tube needs no oven: the gas is already there at its working pressure. The cathode heater still has to warm up.'
            : 'The tube stands in a thermostatted oven. The mercury inside must be at a steady temperature before any reading, or the vapour pressure changes under you as you sweep.');
          u.task('1. Trace the tube', st.traced, st.traced ? 'Cathode, grid, collector' : 'Look through the oven window')
            .add(u.button(st.traced ? 'Traced' : 'Look inside the tube', trace, !st.traced, st.traced));
          u.task('2. Switch the heater on', st.heat, st.heat ? (NEON ? 'Cathode hot' : 'Oven holding at ' + OVEN_SET + ' °C') : 'The hand presses the heater rocker')
            .add(u.button(st.heat ? 'Heater is on' : 'Switch the heater on', function () { S.focus('unit'); setHeater(true); }, !st.heat, st.heat || S.hand.busy));
          u.live(function () { return st.warm ? 'Ready  ·  ' + readV().toFixed(1) + ' V  ·  ' + readI().toFixed(3) + ' nA' : 'Tube cold: the electrometer reads nothing'; });
          u.note('Keep the accelerating voltage at zero while the tube warms up.');
          u.next('Next: sweep the accelerating voltage', st.traced && st.heat);
        },
        ok: function () { return st.traced && st.heat; },
        auto: function () { trace(); return setHeater(true); } },

      { id: 'sweep', title: 'Sweep and mark the peaks', view: 'unit', render: function (u) {
          u.h2('Raise the voltage and mark every current peak');
          u.p('Turn the knob up in small steps and watch the electrometer. Record points as you go for the curve, and when the current stops rising and begins to fall, mark that voltage as a peak.');
          var tg = { v: Math.min(VMAX, rnd(st.V + 1, 1)) };
          u.slider('Set the accelerating voltage to', 0, VMAX, VSTEP, function () { return tg.v; },
            function (v) { tg.v = v; }, 'V', 1);
          u.row(u.button('Turn the knob', function () { turnTo(tg.v); }, true, S.hand.busy),
            u.button('Record this point', function () { recordPoint(); }, false, S.hand.busy));
          u.row(u.button('Hunt the next peak', function () { huntPeak(); }, false, S.hand.busy),
            u.button('Knob back to zero', function () { turnTo(0); }, false, S.hand.busy || st.V === 0));
          u.live(function () { return readV().toFixed(1) + ' V  ·  ' + readI().toFixed(3) + ' nA  ·  ' + st.peaks + ' peaks marked'; });
          u.h3('Observation table'); u.table();
          if (st.peaks < 3) u.p(st.peaks + ' of at least 3 peaks marked.');
          u.next('Next: the peak spacing', st.peaks >= 3);
        },
        ok: function () { return st.peaks >= 3; },
        auto: function () {
          var chain = turnTo(0), v;
          for (v = 0; v <= VMAX - 0.5; v += VMAX / 24) {
            (function (vv) { chain = chain.then(function () { return turnTo(rnd(vv, 1)); })
              .then(function () { recordPoint(); }); })(v);
          }
          chain = chain.then(function () { return turnTo(0); });
          for (var k = 0; k < 8; k++) { chain = chain.then(function () { return huntPeak(); }); }
          return chain;
        } },
    ],

    tick: function () {
      showV(st.warm ? readV().toFixed(1) : '0.0', 'V');
      showI(st.warm ? readI().toFixed(3) : '0.000', 'nA');
      glowM.opacity = st.warm ? Math.min(0.5, 0.06 + st.V / VMAX * 0.5) : 0;
      hudV.set(readV().toFixed(1) + ' V');
      hudI.set(st.warm ? readI().toFixed(3) + ' nA' : '—');
      hudP.set(String(st.peaks));
    },
  };
});
