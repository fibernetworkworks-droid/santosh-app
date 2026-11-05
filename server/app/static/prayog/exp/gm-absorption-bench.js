/* Prayogshala studio module: GM ABSORPTION BENCH (B.Sc. nuclear physics).
   The lead castle, end-window GM tube, sealed gamma source and scaler-timer of the counting bench, with a tray of
   measured absorber sheets that slide in between the source and the window.
   Physics: the `gmabsorb` kernel of packs/modern_ug.js - the attenuation law with the tube's dead time, checked
   on the server against the half-value thickness ln2 / mu. Counts are Poisson numbers from the lab's own seed. */
HoolaStudio.define('gm-absorption-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.gmabsorb, assign = HK.assign;
  var p = HK.paramsFor('gmabsorb', S.lab.params);
  var V_ = S.lab.variant || {}, SRC = V_.sample || 'Sealed Cs-137 gamma source with aluminium absorbers';
  var MAT = (/lead/i.test(SRC) ? 'lead' : /copper/i.test(SRC) ? 'copper' : 'aluminium');
  var MATCOL = MAT === 'lead' ? 0x6c6f76 : MAT === 'copper' ? 0xb06a3a : 0xb8bec6;
  var VMIN = 250, VMAX = 750, VSTEP = 10, VPLAT = 650;
  // the tray holds sheets scaled to THIS absorber: a lead sheet of 40 mm would stop the beam altogether
  var HVL = Math.log(2) / p.mu * 1000;                             // half-value thickness in millimetres
  function step(f) { var x = HVL * f, m = x >= 20 ? 5 : x >= 8 ? 2 : x >= 3 ? 1 : 0.5;
    return Math.round(x / m) * m; }
  var SHEETS = [0, step(0.25), step(0.5), step(0.9), step(1.3), step(1.8), step(2.3), step(3.0)];
  var st = { placed: false, shut: false, V: 450, t: p.t, counting: false, count: 0, elapsed: 0,
    x: 0, bg: null, idx: 0, done: {} };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function qAt(v, t) { return assign(p, { x: st.x / 1000, t: t === undefined ? st.t : t,
    N0: st.placed ? p.N0 : 0.0 }); }
  function drawCounts(v, t) { st.idx += 1; return KN.counts(qAt(v, t), st.idx); }
  function rateNow() { return KN.obsRate(qAt(st.V)); }

  // ================================================================ lead castle and shelf stand
  var castle = new T.Group(); S.scene.add(castle); castle.position.set(-0.26, 0, -0.14);
  var leadM = new T.MeshStandardMaterial({ color: 0x53565c, roughness: 0.72, metalness: 0.55 });
  function brick(x, y, z, w, h, d) { var b = S.rounded(w, d, h, 0.004, leadM); b.rotation.x = -Math.PI / 2;
    b.position.set(x, y + h / 2, z); castle.add(b); return b; }
  for (var r = 0; r < 4; r++) {                       // three walls of lead bricks, the front left open
    brick(-0.105, r * 0.045, 0, 0.05, 0.044, 0.22);
    brick(0.105, r * 0.045, 0, 0.05, 0.044, 0.22);
    brick(0, r * 0.045, -0.085, 0.16, 0.044, 0.05);
  }
  var roof = brick(0, 0.18, 0, 0.26, 0.03, 0.24);
  var stand = new T.Group(); castle.add(stand);
  var sPost = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.17, 16), M.chrome); sPost.position.set(-0.052, 0.085, 0.05);
  stand.add(sPost);
  var sPost2 = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.17, 16), M.chrome); sPost2.position.set(0.052, 0.085, 0.05);
  stand.add(sPost2);
  var shelfY = [];
  for (var sh = 0; sh < 5; sh++) {
    var y = 0.03 + sh * 0.026; shelfY.push(y);
    var pl = S.mesh(new T.BoxGeometry(0.12, 0.0025, 0.07), M.alu); pl.position.set(0, y, 0.05); stand.add(pl);
    var hole = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.004, 20), new T.MeshStandardMaterial({ color: 0x1b1d20 }));
    hole.position.set(0, y + 0.0005, 0.05); stand.add(hole);
  }
  var base = S.rounded(0.18, 0.12, 0.01, 0.004, M.iron); base.rotation.x = -Math.PI / 2; base.position.set(0, 0.005, 0.05);
  stand.add(base);
  // the GM tube in its holder, window down
  var tubeG = new T.Group(); castle.add(tubeG); tubeG.position.set(0, 0.168, 0.05);
  var holder = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.03, 24), M.bakelite); holder.position.y = 0.018;
  tubeG.add(holder);
  var tubeM = new T.MeshStandardMaterial({ color: 0x9aa2ab, roughness: 0.32, metalness: 0.75 });
  var tubeB = S.mesh(new T.CylinderGeometry(0.0135, 0.0135, 0.05, 28), tubeM); tubeB.position.y = -0.016;
  tubeG.add(tubeB);
  var mica = S.mesh(new T.CylinderGeometry(0.0115, 0.0115, 0.0015, 28),
    new T.MeshStandardMaterial({ color: 0xd8d2bd, roughness: 0.5, transparent: true, opacity: 0.8 }));
  mica.position.y = -0.0415; tubeG.add(mica);
  var guard = S.mesh(new T.TorusGeometry(0.0125, 0.0015, 8, 28), tubeM); guard.rotation.x = Math.PI / 2;
  guard.position.y = -0.04; tubeG.add(guard);
  var tlbl = S.label('GM 10 mg/cm²', { w: 0.026, ratio: 0.3, color: '#2b2f36' });
  tlbl.position.set(0, -0.016, 0.0138); tubeG.add(tlbl);
  // the sealed source, its holder, and the lead pot it lives in
  var srcG = new T.Group(); S.scene.add(srcG);
  var srcDisc = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, 0.004, 24),
    new T.MeshStandardMaterial({ color: 0xb8322a, roughness: 0.4, metalness: 0.3 }));
  srcG.add(srcDisc);
  var srcRim = S.mesh(new T.TorusGeometry(0.0085, 0.0012, 8, 24), M.chrome); srcRim.rotation.x = Math.PI / 2;
  srcG.add(srcRim);
  var trefoil = S.canvasTex(128, 128, function (x, w, h) {
    x.fillStyle = '#f2d02a'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b1b1b';
    x.beginPath(); x.arc(w / 2, h / 2, 10, 0, Math.PI * 2); x.fill();
    for (var i = 0; i < 3; i++) { x.beginPath();
      x.arc(w / 2, h / 2, 46, i * 2.094 - 0.45, i * 2.094 + 0.45); x.arc(w / 2, h / 2, 18, i * 2.094 + 0.45, i * 2.094 - 0.45, true);
      x.closePath(); x.fill(); } });
  var trefM = new T.Mesh(new T.CircleGeometry(0.0082, 24), new T.MeshStandardMaterial({ map: trefoil, roughness: 0.6 }));
  trefM.rotation.x = -Math.PI / 2; trefM.position.y = 0.0021; srcG.add(trefM);
  var POT = new T.Vector3(0.0, 0.016, 0.16);
  srcG.position.copy(POT);
  var pot = new T.Group(); S.scene.add(pot); pot.position.set(0.0, 0, 0.16);
  var potB = S.mesh(new T.CylinderGeometry(0.03, 0.032, 0.03, 28), leadM); potB.position.y = 0.015; pot.add(potB);
  var potHole = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.022, 24), new T.MeshStandardMaterial({ color: 0x17181b }));
  potHole.position.y = 0.021; pot.add(potHole);
  var potLid = S.mesh(new T.CylinderGeometry(0.031, 0.031, 0.008, 28), leadM); potLid.position.set(0.055, 0.004, 0.02);
  pot.add(potLid);
  var potLbl = S.label('SEALED SOURCE STORE', { w: 0.05, ratio: 0.2, color: '#e8e8ea' });
  potLbl.rotation.x = -Math.PI / 2; potLbl.position.set(0.0, 0.0012, 0.215); S.scene.add(potLbl);
  // tongs
  var tongs = new T.Group(); S.scene.add(tongs); tongs.position.set(0.1, 0.004, 0.2); tongs.rotation.y = 0.4;
  [-1, 1].forEach(function (sg) {
    var armL = S.mesh(new T.BoxGeometry(0.17, 0.004, 0.005), M.chrome);
    armL.position.set(0, 0, sg * 0.006); armL.rotation.y = sg * 0.04; tongs.add(armL);
  });
  var hinge = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.016, 12), M.chrome); hinge.rotation.x = Math.PI / 2;
  hinge.position.set(0.06, 0, 0); tongs.add(hinge);
  S.contact(0.3, 0.26, -0.26, -0.14, 0.5);
  S.contact(0.1, 0.1, 0.0, 0.16, 0.45);

  // ================================================================ scaler - timer
  var unit = new T.Group(); S.scene.add(unit); unit.position.set(0.34, 0, -0.12); unit.rotation.y = -0.3;
  var UW = 0.36, UD = 0.24, UH = 0.13;
  var ucase = S.rounded(UW, UD, UH, 0.012, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5, metalness: 0.12 }));
  ucase.rotation.x = -Math.PI / 2; ucase.position.y = UH / 2 + 0.004; unit.add(ucase);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.004, 16), M.rubber);
    ft.position.set(f[0] * (UW / 2 - 0.02), 0.002, f[1] * (UD / 2 - 0.02)); unit.add(ft);
  });
  var FZ = UD / 2 + 0.0062, PW = UW - 0.014, PH = UH - 0.014, KX = 0.105, KY = -0.014;
  var uTex = S.canvasTex(1300, Math.round(1300 * PH / PW), function (x, w, h) {
    var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; }, k = w / PW;
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.font = '700 38px "Public Sans", sans-serif'; x.fillText('SCALER – TIMER', 32, 60);
    x.font = '500 24px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6';
    x.fillText('GM HIGH VOLTAGE ' + VMIN + ' – ' + VMAX + ' V  ·  PRESET TIME', 32, 96);
    var cx = X(KX), cy = Y(KY), R = 0.024 * k; x.strokeStyle = '#f1efe8'; x.fillStyle = '#f1efe8';
    for (var i = 0; i <= 25; i++) {
      var th = (225 - 270 * i / 25) * Math.PI / 180, big = i % 5 === 0;
      x.lineWidth = big ? 4 : 2; x.beginPath();
      x.moveTo(cx + Math.cos(th) * R, cy - Math.sin(th) * R);
      x.lineTo(cx + Math.cos(th) * (R + (big ? 20 : 11)), cy - Math.sin(th) * (R + (big ? 20 : 11))); x.stroke();
      if (big) { x.font = '600 20px "Public Sans", sans-serif'; x.textAlign = 'center';
        x.fillText(String(VMIN + (VMAX - VMIN) * i / 25), cx + Math.cos(th) * (R + 42), cy - Math.sin(th) * (R + 42) + 7); }
    }
    x.textAlign = 'center'; x.font = '700 24px "Public Sans", sans-serif'; x.fillText('E.H.T.  (VOLTS)', cx, Y(-0.048));
    x.fillText('COUNTS', X(-0.115), Y(0.042)); x.fillText('TIME (s)', X(-0.115), Y(-0.048));
    x.fillText('START', X(0.0), Y(-0.048)); x.fillText('RESET', X(0.04), Y(-0.048)); x.textAlign = 'left';
  });
  var ufac = S.mesh(new T.BoxGeometry(PW, PH, 0.004),
    [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: uTex, roughness: 0.45 }), M.grey]);
  ufac.position.set(0, 0.004 + UH / 2, FZ - 0.002); unit.add(ufac);
  function up(u, v, dz) { return new T.Vector3(u, 0.004 + UH / 2 + v, FZ + (dz || 0)); }
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  var knob = new T.Group(); knob.position.copy(up(KX, KY)); unit.add(knob);
  var skirt = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.004, 36), M.bakelite); skirt.rotation.x = Math.PI / 2;
  skirt.position.z = 0.002; knob.add(skirt);
  var kb = S.mesh(new T.CylinderGeometry(0.0145, 0.016, 0.016, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 }));
  kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; knob.add(kb);
  var kptr = S.mesh(new T.BoxGeometry(0.002, 0.016, 0.0012), M.white, false); kptr.position.set(0, 0.009, 0.0215);
  knob.add(kptr);
  function knobAngle(v) { return 3 * Math.PI / 4 - 1.5 * Math.PI * ((v - VMIN) / (VMAX - VMIN)); }
  knob.rotation.z = knobAngle(VMIN);
  var startB = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 20), M.green); startB.rotation.x = Math.PI / 2;
  startB.position.copy(up(0.0, -0.022, 0.004)); unit.add(startB);
  var resetB = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 20), M.grey); resetB.rotation.x = Math.PI / 2;
  resetB.position.copy(up(0.04, -0.022, 0.004)); unit.add(resetB);
  function lcd(cx, cy, wdt, hgt, big) {
    var tex = S.liveTex(512, 190), last = '';
    var bez = S.mesh(new T.BoxGeometry(wdt + 0.006, hgt + 0.006, 0.003), M.grey);
    bez.position.copy(up(cx, cy, 0.001)); unit.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(wdt, hgt), new T.MeshBasicMaterial({ map: tex, toneMapped: false }));
    scr.position.copy(up(cx, cy, 0.004)); unit.add(scr);
    return function (txt) {
      if (txt === last) return; last = txt;
      tex.draw(function (x) {
        var gr = x.createLinearGradient(0, 0, 0, 190); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
        x.fillStyle = gr; x.fillRect(0, 0, 512, 190);
        x.font = '700 ' + (big ? 100 : 88) + 'px "JetBrains Mono", monospace'; x.textAlign = 'right';
        x.fillStyle = 'rgba(0,0,0,.07)'; x.fillText(big ? '888888' : '8888', 460, 126);
        x.fillStyle = '#1b2116'; x.fillText(txt, 460, 126);
      });
    };
  }
  var showC = lcd(-0.115, 0.022, 0.11, 0.034, true), showT = lcd(-0.115, -0.022, 0.11, 0.034, false);
  S.contact(0.46, 0.32, 0.34, -0.12, 0.55);
  S.wire([[-0.26, 0.03, 0.0], [0.0, 0.02, 0.0], [0.2, 0.02, -0.04]], 'black');

  S.addApparatus('castle', castle, 'Lead castle with the shelf stand',
    'Lead bricks keep the background down and keep the radiation in. The source sits on one of the five shelves, at a fixed distance below the tube.');
  S.addApparatus('tube', tubeG, 'End-window GM tube',
    'A thin mica window lets even beta particles in. Each particle that gets in starts an avalanche in the gas, and the scaler records one count.');
  S.addApparatus('src', srcG, SRC,
    'A sealed disc source. It is moved only with the tongs, from behind the shield, and it lives in the lead pot when it is not being counted.');
  S.addApparatus('pot', pot, 'Lead source store', 'The source is kept here, lid on, whenever a reading is not being taken.');
  S.addApparatus('tongs', tongs, 'Source tongs', 'Long tongs keep your hands away from the source: distance is the cheapest shielding there is.');
  S.addApparatus('unit', unit, 'Scaler-timer', 'The knob sets the tube voltage; START counts for the preset time and then stops by itself.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudV = S.hudCard('Tube voltage'), hudC = S.hudCard('Counts'), hudR = S.hudCard('Count rate');


  // ---------------------------------------------------------------- the absorber stack and its tray
  var absG = new T.Group(); S.scene.add(absG); absG.position.set(-0.26, 0, -0.09);
  var absM = new T.MeshStandardMaterial({ color: MATCOL, roughness: 0.4, metalness: 0.65 });
  var SH_Y = 0.03 + 3 * 0.026;                                     // the shelf above the source
  var sheetM = S.mesh(new T.BoxGeometry(0.09, 0.002, 0.055), absM);
  sheetM.position.set(0, SH_Y + 0.002, 0); absG.add(sheetM);
  sheetM.visible = false;
  var tray = new T.Group(); S.scene.add(tray); tray.position.set(0.12, 0, 0.17);
  var trayBox = S.rounded(0.15, 0.1, 0.018, 0.005, M.wood); trayBox.rotation.x = -Math.PI / 2;
  trayBox.position.y = 0.009; tray.add(trayBox);
  for (var si = 0; si < 6; si++) {
    var sht = S.mesh(new T.BoxGeometry(0.1, 0.0015 + si * 0.0012, 0.05), absM);
    sht.position.set(-0.03 + (si % 3) * 0.03, 0.019 + si * 0.001, -0.02 + Math.floor(si / 3) * 0.045);
    sht.rotation.y = 0.1 * si; tray.add(sht);
  }
  var trayLbl = S.label(MAT.toUpperCase() + ' ABSORBERS (mm)', { w: 0.08, ratio: 0.18, color: '#2b2f36' });
  trayLbl.rotation.x = -Math.PI / 2; trayLbl.position.set(0.12, 0.0012, 0.235); S.scene.add(trayLbl);
  var mic = S.mesh(new T.BoxGeometry(0.07, 0.012, 0.025), M.chrome); mic.position.set(0.26, 0.006, 0.2);
  mic.rotation.y = -0.3; S.scene.add(mic);
  S.contact(0.2, 0.16, 0.12, 0.17, 0.45);
  function showStack() {
    sheetM.visible = st.x > 0;
    if (st.x > 0) { sheetM.scale.y = Math.max(0.5, st.x / 2); sheetM.position.y = SH_Y + st.x / 2000; }
  }
  S.addApparatus('abs', tray, 'Tray of ' + MAT + ' absorbers',
    'Sheets of measured thickness, from 2 mm up to 60 mm. Their thickness is checked with the screw gauge beside the tray before they are used.');

  // ================================================================ human actions
  function placeSource() {
    if (busy()) return Promise.resolve();
    if (st.placed) return Promise.resolve();
    var from = srcG.position.clone();
    var to = new T.Vector3(-0.26, shelfY[2] + 0.0025, -0.14 + 0.05);
    return S.hand.pinchMove(from, function (k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, Math.max(from.y, to.y) + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
    }, function (k) {
      srcG.position.set(from.x + (to.x - from.x) * k,
        from.y + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
      tongs.position.set(srcG.position.x + 0.07, srcG.position.y, srcG.position.z + 0.05);
    }, { mode: 'side', ms: 1100, reachMs: 700 }).then(function () {
      srcG.position.copy(to); st.placed = true;
      S.say('Source on the middle shelf, 3 cm below the window, with the tongs and from behind the shield. It stays exactly there for every reading: the geometry must not change.');
      S.render();
    });
  }
  function storeSource() {
    if (busy()) return Promise.resolve();
    if (!st.placed) return Promise.resolve();
    var from = srcG.position.clone(), to = POT.clone();
    return S.hand.pinchMove(from, function (k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
    }, function (k) {
      srcG.position.set(from.x + (to.x - from.x) * k,
        from.y + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
      tongs.position.set(srcG.position.x + 0.07, srcG.position.y, srcG.position.z + 0.05);
    }, { mode: 'side', ms: 1100, reachMs: 700 }).then(function () {
      srcG.position.copy(POT); st.placed = false;
      S.say('Source back in its lead store, lid on. That is where it belongs the moment the counting is over.');
      S.render();
    });
  }
  function turnTo(v) {
    if (busy()) return Promise.resolve();
    if (!isFinite(v) || v < VMIN || v > VMAX + 1e-9) { S.say('The E.H.T. goes from ' + VMIN + ' to ' + VMAX + ' V only.'); return Promise.resolve(); }
    v = Math.round(v / VSTEP) * VSTEP;
    var v0 = st.V, a0 = knobAngle(v0), pt = wpt(unit, KX, 0.004 + UH / 2 + KY, FZ + 0.024);
    if (v === v0) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      st.V = v0 + (v - v0) * k; knob.rotation.z = knobAngle(st.V);
      S.hand.group.rotation.y = -(knobAngle(st.V) - a0) * 0.3;
    }, { mode: 'front', ms: 350 + 1.2 * Math.abs(v - v0), reachMs: 600 })
      .then(function () { st.V = v; knob.rotation.z = knobAngle(v); S.render(); });
  }
  function count() {
    if (busy()) return Promise.resolve(false);
    if (st.V > VPLAT + 60) { S.say('That is far past the end of the plateau: a tube left in continuous discharge is ruined. Turn the voltage down.'); return Promise.resolve(false); }
    st.counting = true; st.count = 0; st.elapsed = 0;
    var total = drawCounts(st.V, st.t);
    return S.hand.tap(startB, 'front').then(function () {
      return S.tween(1400, function (k) { st.elapsed = st.t * k; st.count = Math.round(total * k); });
    }).then(function () {
      st.counting = false; st.elapsed = st.t; st.count = total;
      S.say('Counted ' + total + ' in ' + st.t + ' s at ' + st.V + ' V: ' + (total / st.t).toFixed(2) + ' counts per second.');
      S.render(); return true;
    });
  }

  function setAbsorber(mm) {
    if (busy()) return Promise.resolve(false);
    if (SHEETS.indexOf(mm) < 0) { S.say('The tray holds ' + SHEETS.join(', ') + ' mm of ' + MAT + '.'); return Promise.resolve(false); }
    if (mm === st.x) return Promise.resolve(true);
    var to = new T.Vector3(-0.26, SH_Y + 0.02, -0.04), from = new T.Vector3(0.12, 0.03, 0.17);
    return S.hand.pinchMove(from, function (k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.05 * Math.sin(Math.PI * k), from.z + (to.z - from.z) * k);
    }, function () {}, { mode: 'side', ms: 900, reachMs: 650 }).then(function () {
      st.x = mm; showStack();
      S.say(mm === 0 ? 'All the absorbers taken out: the beam reaches the window unshielded.'
        : mm + ' mm of ' + MAT + ' on the shelf between the source and the window.');
      S.render(); return true;
    });
  }
  function recordBackground() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (st.placed) { S.say('The source must be back in its lead store for a background count.'); return false; }
    if (st.elapsed < st.t - 1e-9) { S.say('Press START and let the counter run its full ' + st.t + ' s first.'); return false; }
    st.bg = st.count / st.t;
    S.say('Background: ' + st.count + ' counts in ' + st.t + ' s, that is ' + st.bg.toFixed(3) + ' counts per second. It is taken off every reading from here on.');
    S.render();
    return true;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (st.bg === null) { S.say('Take the background count first, with the source in its store.'); return false; }
    if (!st.placed) { S.say('Put the source back on its shelf first.'); return false; }
    if (st.elapsed < st.t - 1e-9) { S.say('Press START and let the counter run its full ' + st.t + ' s first.'); return false; }
    if (st.done[st.x]) { S.say('You already have a reading at ' + st.x + ' mm. Change the absorber.'); return false; }
    st.done[st.x] = true;
    var net = st.count / st.t - st.bg;
    S.addRow({ x: st.x, N: st.count, rate: rnd(st.count / st.t, 3), net: rnd(net, 3) });
    S.say('Written in your record book: ' + st.x + ' mm, ' + st.count + ' counts, net ' + net.toFixed(2) + ' per second.');
    return true;
  }

  function result(rows) {
    var pts = rows.filter(function (r) { return r.net > 0; })
      .map(function (r) { return [r.x / 1000, Math.log(r.net)]; });
    if (pts.length < 4) return null;
    var f = S.fit.linear(pts);
    if (!f || f.m >= 0) return null;
    var mu = -f.m;
    return { label: 'Half-value thickness of ' + MAT, value: Math.log(2) / mu * 1000, unit: 'mm', digits: 2,
      truth: Math.log(2) / p.mu * 1000,
      note: 'Slope of ln(net rate) against thickness is −μ, so μ = ' + mu.toFixed(1) + ' per metre ('
        + (mu / 100).toFixed(4) + ' per cm) and the half-value thickness is ln2/μ.' };
  }

  return {
    camera: { pos: [-0.02, 0.84, 0.96], look: [-0.04, 0.1, -0.08] },
    views: { castle: [[-0.2, 0.36, 0.22], [-0.26, 0.1, -0.12]], tube: [[-0.16, 0.26, 0.08], [-0.26, 0.15, -0.09]],
      src: [[-0.18, 0.2, 0.06], [-0.26, 0.09, -0.09]], pot: [[0.06, 0.18, 0.3], [0.0, 0.02, 0.16]],
      abs: [[0.12, 0.24, 0.36], [0.12, 0.02, 0.17]], tongs: [[0.1, 0.2, 0.34], [0.1, 0.0, 0.2]],
      unit: [[0.38, 0.3, 0.2], [0.34, 0.07, -0.12]],
      bench: [[-0.02, 0.84, 0.96], [-0.04, 0.1, -0.08]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A gamma photon is not slowed down as it goes through matter: it is either scattered, or absorbed, or it passes untouched. The chance of being removed in a thin layer is the same everywhere, so the surviving rate falls exponentially with thickness.',
      formula: 'N = N₀ e^(−μ x),   x½ = ln2 / μ',
      formulaNote: 'so ln(net rate) against thickness is a straight line of slope −μ',
      more: ['The background is counted first, with the source locked away, and taken off every reading: the sheets do not shield the background.',
        'Gamma rays have no range. However much ' + MAT + ' is used, something always gets through - which is why shielding is quoted as a half-value thickness and never as a thickness that "stops" the rays.',
        'The counting time must be long enough that the thickest absorber still gives a few thousand counts, or the statistics swamp the slope.'],
      precautions: 'Keep the source, the tube and the shelf fixed; only the absorber changes. Measure each sheet with the screw gauge. Stand behind the lead castle while counting, and put the source back in its store at the end.' },
    book: { title: 'Expt. — Attenuation of gamma rays in ' + MAT,
      lines: ['Aim: linear attenuation coefficient and', 'half-value thickness.', 'Source: ' + SRC,
        'Background counted first with the source stored.', 'N = N₀ e^(−μx);  x½ = ln2/μ',
        'Counting time ' + p.t + ' s at each thickness.'],
      columns: [{ label: 'x (mm)', get: function (r) { return r.x; } },
        { label: 'Counts', get: function (r) { return r.N; } },
        { label: 'Rate (/s)', get: function (r) { return r.rate.toFixed(2); } },
        { label: 'Net (/s)', get: function (r) { return r.net.toFixed(2); } }] },
    graph: { x: function (r) { return r.x; }, y: function (r) { return r.net > 0 ? Math.log(r.net) : 0; },
      xlabel: 'thickness x (mm)', ylabel: 'ln (net rate)',
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.05,
    resultNote: 'A straight line on a logarithmic plot is the proof that the law is exponential; its slope is the attenuation coefficient of this material at this photon energy, and ln2 over it is the thickness that halves the beam.',
    chips: ['Why take the background off?', 'Why is there no range for gamma rays?',
      'What does the half-value thickness mean?', 'Check my readings', 'Why plot a logarithm?'],
    viva: [['A plot of ln(net rate) against absorber thickness is', ['A straight line of slope −μ', 'A curve ending at the range', 'Flat'], 0,
      'N = N₀e^(−μx).'],
      ['The half-value thickness is', ['ln2/μ', '1/μ', '2/μ'], 0, 'Set N = N₀/2 in the attenuation law.'],
      ['The background is subtracted because', ['The absorbers do not shield it', 'It is zero anyway', 'The timer counts it twice'], 0,
        'Cosmic rays and the walls go on counting whatever is on the shelf.']],
    askState: function () {
      return { experiment: 'attenuation of gamma rays: linear attenuation coefficient and half-value thickness',
        source: SRC, absorber: MAT, source_on_shelf: st.placed, absorber_thickness_mm: st.x,
        background_rate_per_s: st.bg, counting_time_s: st.t, last_count: st.count,
        readings_taken: S.rows.length };
    },

    steps: [
      { id: 'bg', title: 'Background', view: 'unit', render: function (u) {
          u.h2('Count the background first');
          u.p('With the source still locked in its lead store, count for ' + st.t + ' s. Cosmic rays and the walls of the room go on counting whatever is on the shelf, and that has to come off every later reading.');
          u.task('1. Source in its store', !st.placed, !st.placed ? 'In the lead pot, lid on' : 'On the shelf - take it back first')
            .add(u.button('Put it back in the store', function () { S.focus('pot'); storeSource(); }, false, !st.placed || S.hand.busy));
          u.task('2. Background count', st.bg !== null, st.bg === null ? 'Not taken yet' : st.bg.toFixed(3) + ' counts per second')
            .add(u.row(u.button('START (' + st.t + ' s)', function () { count(); }, true, S.hand.busy),
              u.button('Record the background', function () { recordBackground(); }, false, S.hand.busy)));
          u.live(function () { return st.count + ' counts in ' + st.elapsed.toFixed(0) + ' s'; });
          u.next('Next: the absorbers', st.bg !== null);
        },
        ok: function () { return st.bg !== null; },
        auto: function () { return turnTo(450).then(function () { return count(); })
          .then(function () { recordBackground(); }); } },

      { id: 'absorb', title: 'Absorbers', view: 'castle', render: function (u) {
          u.h2('Count through ' + MAT + ' of measured thickness');
          u.p('Put the source back on its shelf, then count with no absorber and with each sheet in turn. The source, the tube and the shelf stay exactly where they are: only the thickness changes.');
          u.task('Source on the shelf', st.placed, st.placed ? 'On the middle shelf' : 'In its store')
            .add(u.button(st.placed ? 'Source is in place' : 'Lift it with the tongs', function () { S.focus('src'); placeSource(); }, !st.placed, st.placed || S.hand.busy));
          var sel = { i: 0 };
          u.slider('Absorber from the tray', 0, SHEETS.length - 1, 1, function () { return sel.i; },
            function (v) { sel.i = Math.round(v); }, 'mm', 0);
          u.row(u.button('Slide in ' + SHEETS[sel.i] + ' mm', function () { S.focus('abs'); setAbsorber(SHEETS[sel.i]); }, true, S.hand.busy),
            u.button('START (' + st.t + ' s)', function () { count(); }, false, S.hand.busy));
          u.row(u.button('Record x and counts', function () { record(); }, false, S.hand.busy),
            u.button('Source back to its store', function () { storeSource(); }, false, !st.placed || S.hand.busy));
          u.live(function () { return st.x + ' mm of ' + MAT + '  ·  ' + st.count + ' counts  ·  net ' + (st.bg === null ? '—' : (st.count / st.t - st.bg).toFixed(2)) + ' per second'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 5) u.p(S.rows.length + ' of at least 5 thicknesses recorded.');
          u.next('Next: the attenuation coefficient', S.rows.length >= 5);
        },
        ok: function () { return S.rows.length >= 5; },
        auto: function () {
          return placeSource().then(function () {
            return SHEETS.slice(0, 7).reduce(function (pr, mm) {
              return pr.then(function () { return setAbsorber(mm); })
                .then(function () { return count(); })
                .then(function () { record(); });
            }, Promise.resolve());
          }).then(function () { return setAbsorber(0); }).then(function () { return storeSource(); });
        } },
    ],

    tick: function () {
      showC(String(st.count));
      showT(st.elapsed.toFixed(0));
      hudV.set(st.x + ' mm of ' + MAT);
      hudC.set(String(st.count));
      hudR.set(st.placed ? rateNow().toFixed(2) + ' /s' : 'background only');
    },
  };
});
