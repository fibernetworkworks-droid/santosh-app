/* Prayogshala studio module: GM HALF-LIFE BENCH (B.Sc. nuclear physics).
   The lead castle, end-window GM tube, sealed source store and scaler-timer of the counting bench, with a
   laboratory clock: a freshly activated short-lived source is counted at regular intervals while it decays.
   Physics: the `gmdecay` kernel of packs/modern_ug.js - exponential decay with the tube's dead time, checked on
   the server against the half-life itself. Counts are Poisson numbers from the lab's own seed. */
HoolaStudio.define('gm-halflife-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.gmdecay, assign = HK.assign;
  var p = HK.paramsFor('gmdecay', S.lab.params);
  var V_ = S.lab.variant || {}, SRC = V_.sample || 'Freshly activated indium-116m foil';
  var VMIN = 250, VMAX = 750, VSTEP = 10, VPLAT = 650;
  var GAP = Math.max(15, Math.round(p.T / 6 / 15) * 15);           // one reading about every sixth of a half-life
  var st = { placed: false, shut: false, V: 450, t: p.tc, counting: false, count: 0, elapsed: 0,
    clock: 0, bg: null, idx: 0, mid: 0, done: {} };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function mmss(s) { var m = Math.floor(s / 60), ss = Math.round(s - m * 60);
    return m + ' min ' + (ss < 10 ? '0' : '') + ss + ' s'; }
  function qAt(v, t) { return assign(p, { t: st.clock + (t === undefined ? st.t : t) / 2,
    tc: t === undefined ? st.t : t, N0: st.placed ? p.N0 : 0.0 }); }
  function drawCounts(v, t) { st.idx += 1; st.mid = st.clock + (t === undefined ? st.t : t) / 2;
    return KN.counts(qAt(v, t), st.idx); }
  function rateNow() { return KN.obsRate(assign(p, { t: st.clock, N0: st.placed ? p.N0 : 0.0 })); }

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
  // a lintel across the back only: the castle is open at the front and the top, as a teaching one is, so the
  // tube and the source shelf can be seen
  var roof = brick(0, 0.18, -0.072, 0.26, 0.03, 0.095);
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
  var unit = new T.Group(); S.scene.add(unit); unit.position.set(0.3, 0, -0.1); unit.rotation.y = -0.32;
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
  showC('0'); showT('0');   // the displays read before the first tick
  S.contact(0.46, 0.32, 0.3, -0.1, 0.55);
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
  var hudV = S.hudCard('Clock'), hudC = S.hudCard('Counts'), hudR = S.hudCard('Count rate');


  // ---------------------------------------------------------------- the laboratory clock
  var clockG = new T.Group(); S.scene.add(clockG); clockG.position.set(0.1, 0, -0.26); clockG.rotation.x = -0.5;
  var cBody = S.mesh(new T.CylinderGeometry(0.05, 0.05, 0.016, 36), M.bakelite); cBody.rotation.x = Math.PI / 2;
  cBody.position.y = 0.055; clockG.add(cBody);
  var cStand = S.rounded(0.07, 0.05, 0.012, 0.004, M.iron); cStand.rotation.x = -Math.PI / 2;
  cStand.position.set(0, 0.006, 0.02); clockG.add(cStand);
  var cTex = S.liveTex(320, 320), cLast = '';
  var cFace = new T.Mesh(new T.CircleGeometry(0.045, 40), new T.MeshBasicMaterial({ map: cTex, toneMapped: false }));
  cFace.position.set(0, 0.055, 0.009); clockG.add(cFace);
  function drawClock(sec) {
    var txt = mmss(sec); if (txt === cLast) return; cLast = txt;
    cTex.draw(function (x, w, h) {
      x.fillStyle = '#fbfaf3'; x.fillRect(0, 0, w, h);
      x.strokeStyle = '#1b1b1b'; x.lineWidth = 6; x.beginPath(); x.arc(w / 2, h / 2, w / 2 - 8, 0, Math.PI * 2); x.stroke();
      var a = (sec % 60) / 60 * Math.PI * 2;
      x.lineWidth = 4; x.beginPath(); x.moveTo(w / 2, h / 2);
      x.lineTo(w / 2 + Math.sin(a) * (w / 2 - 34), h / 2 - Math.cos(a) * (w / 2 - 34)); x.stroke();
      x.fillStyle = '#1b2116'; x.textAlign = 'center'; x.font = '700 42px "JetBrains Mono", monospace';
      x.fillText(txt, w / 2, h * 0.76);
      x.font = '600 24px "Public Sans", sans-serif'; x.fillStyle = '#6b6f75';
      x.fillText('SINCE THE SOURCE WAS MADE', w / 2, h * 0.3);
    });
  }
  drawClock(0);
  S.addApparatus('clock', clockG, 'Laboratory clock',
    'Started the moment the freshly activated source is put on the shelf. Each count is plotted against the MIDDLE of its counting interval.');

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

  function recordBackground() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (st.placed) { S.say('The source must be in its store for a background count.'); return false; }
    if (st.elapsed < st.t - 1e-9) { S.say('Press START and let the counter run its full ' + st.t + ' s first.'); return false; }
    st.bg = st.count / st.t;
    S.say('Background: ' + st.bg.toFixed(3) + ' counts per second. It is taken off every reading from here on.');
    S.render(); return true;
  }
  function wait(sec) {
    if (busy()) return Promise.resolve();
    return S.tween(500, function (k) { drawClock(st.clock + sec * k); }).then(function () {
      st.clock += sec; drawClock(st.clock);
      S.say('Waited to ' + mmss(st.clock) + ' on the clock.'); S.render();
    });
  }
  function countInterval() {
    return count().then(function (ok) {
      if (ok) { st.clock += st.t; drawClock(st.clock); }
      return ok;
    });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (st.bg === null) { S.say('Take the background count first, with the source in its store.'); return false; }
    if (!st.placed) { S.say('Put the source on its shelf first.'); return false; }
    if (st.elapsed < st.t - 1e-9) { S.say('Press START and let the counter run its full ' + st.t + ' s first.'); return false; }
    if (st.done[Math.round(st.mid)]) { S.say('That interval is already written down.'); return false; }
    st.done[Math.round(st.mid)] = true;
    var net = st.count / st.t - st.bg;
    S.addRow({ t: rnd(st.mid, 1), N: st.count, rate: rnd(st.count / st.t, 3), net: rnd(net, 3) });
    S.say('Written in your record book: middle time ' + mmss(st.mid) + ', ' + st.count + ' counts, net ' + net.toFixed(2) + ' per second.');
    return true;
  }

  function result(rows) {
    var pts = rows.filter(function (r) { return r.net > 0; })
      .map(function (r) { return [r.t, Math.log(r.net)]; });
    if (pts.length < 6) return null;
    var f = S.fit.linear(pts);
    if (!f || f.m >= 0) return null;
    return { label: 'Half-life', value: Math.log(2) / (-f.m) / 60, unit: 'min', digits: 2, truth: p.T / 60,
      note: 'Slope of ln(net rate) against time is −λ, so λ = ' + (-f.m).toExponential(3) + ' per second and the half-life is ln2/λ. Taken from ' + pts.length + ' intervals, each plotted at its middle time.' };
  }

  return {
    camera: { pos: [-0.02, 0.95, 1.16], look: [-0.03, 0.1, -0.06] },
    views: { castle: [[-0.16, 0.46, 0.34], [-0.26, 0.09, -0.12]], tube: [[-0.16, 0.26, 0.08], [-0.26, 0.15, -0.09]],
      src: [[-0.18, 0.2, 0.06], [-0.26, 0.09, -0.09]], pot: [[0.06, 0.18, 0.3], [0.0, 0.02, 0.16]],
      clock: [[0.1, 0.24, 0.02], [0.1, 0.05, -0.26]], tongs: [[0.1, 0.2, 0.34], [0.1, 0.0, 0.2]],
      unit: [[0.36, 0.42, 0.36], [0.3, 0.06, -0.1]],
      bench: [[-0.02, 0.95, 1.16], [-0.03, 0.1, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'Every nucleus of the same kind has the same chance of decaying in the next second, whatever has happened before. So the number left, and with it the activity, falls exponentially, and the time in which half of them have gone is the same at any point in the decay.',
      formula: 'N = N₀ e^(−λt),   T½ = ln2 / λ',
      formulaNote: 'so ln(net rate) against time is a straight line of slope −λ',
      more: ['A count taken over an interval is the average over that interval, so it is plotted against the MIDDLE of the interval, not its start.',
        'The background does not decay and has to be taken off every reading before the logarithm is taken.',
        'Readings are carried on for at least three half-lives: over a short run an exponential and a straight line look alike.'],
      precautions: 'Start the clock the moment the source goes on the shelf. Keep the source, the tube and the shelf fixed. A freshly activated source is at its most active at the start: keep behind the shield and use the tongs.' },
    book: { title: 'Expt. — Half-life of a short-lived source',
      lines: ['Aim: half-life from the decay of the count rate.', 'Source: ' + SRC,
        'Background counted first with the source stored.', 'Counting time ' + p.tc + ' s per reading.',
        'N = N₀e^(−λt);  T½ = ln2/λ', 'Each reading plotted at the middle of its interval.'],
      columns: [{ label: 't (min)', get: function (r) { return (r.t / 60).toFixed(1); } },
        { label: 'Counts', get: function (r) { return r.N; } },
        { label: 'Net (/s)', get: function (r) { return r.net.toFixed(2); } },
        { label: 'ln(net)', get: function (r) { return r.net > 0 ? Math.log(r.net).toFixed(3) : ''; } }] },
    graph: { x: function (r) { return r.t / 60; }, y: function (r) { return r.net > 0 ? Math.log(r.net) : 0; },
      xlabel: 't (min)', ylabel: 'ln (net rate)',
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.05,
    resultNote: 'The straight line on a logarithmic plot is the signature of radioactive decay: the same fraction goes in every equal interval, so the half-life is the same whether it is measured at the start of the run or at the end.',
    chips: ['Why plot at the middle of the interval?', 'Why take the background off?',
      'How long should the run be?', 'Check my readings', 'What is the decay constant?'],
    viva: [['In three half-lives the activity falls to', ['One eighth', 'One third', 'Nothing'], 0,
      'Each half-life halves it: 1/2 × 1/2 × 1/2.'],
      ['A count taken over an interval is plotted against', ['The middle of the interval', 'Its start', 'Its end'], 0,
        'The rate measured is the average over the interval.'],
      ['The decay constant λ and the half-life are related by', ['T½ = ln2/λ', 'T½ = 1/λ', 'T½ = λ/2'], 0,
        'Setting N = N₀/2 in N = N₀e^(−λt) gives t = ln2/λ.']],
    askState: function () {
      return { experiment: 'half-life of a short-lived source from its decaying count rate',
        source: SRC, source_on_shelf: st.placed, clock_s: Math.round(st.clock),
        background_rate_per_s: st.bg, counting_time_s: st.t, last_count: st.count,
        present_rate_per_s: +rateNow().toFixed(2), readings_taken: S.rows.length };
    },

    steps: [
      { id: 'bg', title: 'Background', view: 'unit', render: function (u) {
          u.h2('Count the background before the source arrives');
          u.p('With the store closed, count for ' + st.t + ' s. This has to be done first: once the fresh source is on the shelf there is no quiet moment left.');
          u.task('1. Source in its store', !st.placed, !st.placed ? 'In the lead pot' : 'On the shelf - take it back first')
            .add(u.button('Put it back in the store', function () { S.focus('pot'); storeSource(); }, false, !st.placed || S.hand.busy));
          u.task('2. Background count', st.bg !== null, st.bg === null ? 'Not taken yet' : st.bg.toFixed(3) + ' counts per second')
            .add(u.row(u.button('START (' + st.t + ' s)', function () { count(); }, true, S.hand.busy),
              u.button('Record the background', function () { recordBackground(); }, false, S.hand.busy)));
          u.live(function () { return st.count + ' counts in ' + st.elapsed.toFixed(0) + ' s'; });
          u.next('Next: follow the decay', st.bg !== null);
        },
        ok: function () { return st.bg !== null; },
        auto: function () { return turnTo(450).then(function () { return count(); })
          .then(function () { recordBackground(); }); } },

      { id: 'decay', title: 'Follow the decay', view: 'castle', render: function (u) {
          u.h2('Count at regular intervals while it decays');
          u.p('Put the fresh source on the shelf and start the clock. Count for ' + st.t + ' s, wait, and count again - about every ' + Math.round(GAP / 60) + ' minutes, for at least three half-lives. Nothing else on the bench may move.');
          u.task('Source on the shelf, clock started', st.placed, st.placed ? 'Clock at ' + mmss(st.clock) : 'In its store')
            .add(u.button(st.placed ? 'Source is in place' : 'Lift it with the tongs', function () { S.focus('src'); placeSource(); }, !st.placed, st.placed || S.hand.busy));
          u.row(u.button('START (' + st.t + ' s)', function () { countInterval(); }, true, S.hand.busy),
            u.button('Record this interval', function () { record(); }, false, S.hand.busy));
          u.row(u.button('Wait ' + Math.round(GAP / 60) + ' min', function () { wait(GAP); }, false, S.hand.busy),
            u.button('Source back to its store', function () { storeSource(); }, false, !st.placed || S.hand.busy));
          u.live(function () { return 'Clock ' + mmss(st.clock) + '  ·  ' + st.count + ' counts  ·  net '
            + (st.bg === null ? '—' : (st.count / st.t - st.bg).toFixed(2)) + ' per second'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 6) u.p(S.rows.length + ' of at least 6 intervals recorded.');
          u.next('Next: the half-life', S.rows.length >= 6);
        },
        ok: function () { return S.rows.length >= 6; },
        auto: function () {
          var chain = placeSource(), i;
          var nread = Math.max(6, Math.min(18, Math.ceil(3 * p.T / (st.t + GAP))));
          for (i = 0; i < nread; i++) {
            chain = chain.then(function () { return countInterval(); })
              .then(function () { record(); })
              .then(function () { return wait(GAP); });
          }
          return chain.then(function () { return storeSource(); });
        } },
    ],

    tick: function () {
      showC(String(st.count));
      showT(st.elapsed.toFixed(0));
      hudV.set(mmss(st.clock));
      hudC.set(String(st.count));
      hudR.set(st.placed ? rateNow().toFixed(2) + ' /s' : 'background only');
    },
  };
});
