/* Prayogshala studio module: GM COUNTING BENCH - the plateau (B.Sc. nuclear physics).
   A lead castle with a shelf stand, an end-window Geiger-Muller tube in its holder, a sealed disc source kept in
   a lead pot and moved only with tongs, and a scaler-timer with a high-voltage knob.
   Physics: the `gmtube` kernel of packs/modern_ug.js on the lab's own params - the same code the server checks.
   Every count is a Poisson number drawn from the lab's own seed, so the same lab always gives the same counts. */
HoolaStudio.define('gm-plateau-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.gmtube, assign = HK.assign;
  var p = HK.paramsFor('gmtube', S.lab.params);
  var V_ = S.lab.variant || {}, SRC = V_.sample || 'Sealed Cs-137 check source, 5 kBq';
  var VMIN = 250, VMAX = 750, VSTEP = 10, VPLAT = p.Vp;
  var st = { placed: false, shut: false, V: VMIN, t: p.t, counting: false, count: 0, elapsed: 0, done: {} };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function qAt(v, t) { return assign(p, { V: v, t: t === undefined ? st.t : t, N0: st.placed ? p.N0 : 0.0 }); }
  function drawCounts(v, t) { return KN.counts(qAt(v, t), 1)[0]; }
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
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (st.elapsed < st.t - 1e-9) { S.say('Press START and let the counter run its full ' + st.t + ' s first.'); return false; }
    if (st.done[st.V]) { S.say('You already have a reading at ' + st.V + ' V. Turn the knob to a new voltage.'); return false; }
    st.done[st.V] = true;
    S.addRow({ V: st.V, N: st.count, t: st.t, rate: rnd(st.count / st.t, 3) });
    S.say('Written in your record book: ' + st.V + ' V, ' + st.count + ' counts in ' + st.t + ' s.');
    return true;
  }

  function result(rows) {
    var q = rows.slice().sort(function (a, b) { return a.V - b.V; });
    var zero = null, first = null, i;
    for (i = 0; i < q.length; i++) {
      if (q[i].N === 0) { zero = q[i].V; } else if (first === null) { first = q[i].V; break; }
    }
    if (zero === null || first === null) return null;
    var plat = q.filter(function (r) { return r.V >= first + 60 && r.V <= first + 260 && r.rate > 0; });
    var sl = null;
    if (plat.length >= 2) {
      var a = plat[0], b = plat[plat.length - 1];
      sl = (b.rate - a.rate) / a.rate * 100 * 100 / Math.max(1, b.V - a.V);
    }
    return { label: 'Starting voltage of the tube', value: (zero + first) / 2, unit: 'V', digits: 0, truth: p.Vs,
      note: 'Halfway between the last voltage that gave no counts (' + zero + ' V) and the first that did (' + first + ' V).'
        + (sl === null ? '' : ' The plateau rises by about ' + sl.toFixed(1) + ' % per 100 V, so the working voltage is set near ' + Math.round(first + 90) + ' V.') };
  }

  return {
    camera: { pos: [-0.02, 0.84, 0.96], look: [-0.04, 0.1, -0.08] },
    views: { castle: [[-0.2, 0.36, 0.22], [-0.26, 0.1, -0.12]], tube: [[-0.16, 0.26, 0.08], [-0.26, 0.15, -0.09]],
      src: [[-0.18, 0.2, 0.06], [-0.26, 0.09, -0.09]], pot: [[0.06, 0.18, 0.3], [0.0, 0.02, 0.16]],
      tongs: [[0.1, 0.2, 0.34], [0.1, 0.0, 0.2]], unit: [[0.38, 0.3, 0.2], [0.34, 0.07, -0.12]],
      bench: [[-0.02, 0.84, 0.96], [-0.04, 0.1, -0.08]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A Geiger-Muller tube only counts once its voltage is high enough for a single ion pair to set off a full avalanche. Above that starting voltage nearly every particle that enters is counted, so the rate hardly changes with voltage: that flat stretch is the plateau. Past its end the gas discharges continuously and the tube is destroyed.',
      formula: 'N = N_obs / (1 − N_obs τ)',
      formulaNote: 'every count leaves the tube dead for τ, so the observed rate is always a little low',
      more: ['The plateau of a good tube rises by only two or three per cent per hundred volts. A steep plateau means the tube is ageing.',
        'The working voltage is set in the first third of the plateau: the rate is steady there and the tube is well clear of the discharge region.',
        'The source must stay on the same shelf for every reading. Moving it even a centimetre changes the count rate far more than the voltage does.'],
      precautions: 'Raise the voltage in small steps and stop at the end of the plateau. Keep the source on one shelf throughout, and take it back to its lead store as soon as the readings are finished.' },
    book: { title: 'Expt. — GM tube: plateau and operating voltage',
      lines: ['Aim: counting curve of a GM tube; starting voltage,', 'plateau and working voltage.',
        'Source: ' + SRC, 'Middle shelf of the lead castle, unchanged throughout.',
        'Counting time ' + p.t + ' s at each voltage.', 'Safety: tongs, shield, source back in its store.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'V (V)', get: function (r) { return r.V; } },
        { label: 'Counts', get: function (r) { return r.N; } },
        { label: 'Rate (/s)', get: function (r) { return r.rate.toFixed(2); } }] },
    graph: { x: function (r) { return r.V; }, y: function (r) { return r.rate; }, xlabel: 'V (V)',
      ylabel: 'counts per second', y0: 0,
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
    resultNote: 'The counting curve is the tube\'s own character: nothing, then a steep rise, then the plateau that makes a GM tube so easy to use, and finally the discharge region that must never be entered.',
    chips: ['Why does the plateau exist at all?', 'Where should the working voltage be set?',
      'What is dead time?', 'Check my readings', 'Why must the source stay on one shelf?'],
    viva: [['The working voltage of a GM tube is set', ['In the first third of the plateau', 'Just past the starting voltage', 'At the end of the plateau'], 0,
      'There the rate is steady and the tube is safe.'],
      ['A plateau sloping steeply means', ['The tube is ageing', 'The source is strong', 'The timer is wrong'], 0,
        'A good tube\'s plateau rises only a few per cent per 100 V.'],
      ['Dead time makes the observed count rate', ['A little too low', 'A little too high', 'Unchanged'], 0,
        'Particles arriving while the tube is dead are not counted.']],
    askState: function () {
      return { experiment: 'GM tube counting curve: starting voltage, plateau and working voltage',
        source: SRC, source_on_shelf: st.placed, tube_voltage_V: st.V, counting_time_s: st.t,
        last_count: st.count, count_rate_per_s: +rateNow().toFixed(2), readings_taken: S.rows.length };
    },

    steps: [
      { id: 'place', title: 'Place the source', view: 'castle', render: function (u) {
          u.h2('Put the source on its shelf, with the tongs');
          u.p('Stand behind the lead castle. Lift the source out of its store with the tongs and set it on the middle shelf, 3 cm below the tube window. It stays there, untouched, for every reading.');
          u.task('1. Source on the middle shelf', st.placed, st.placed ? 'On the middle shelf, under the window' : 'In its lead store')
            .add(u.row(u.button(st.placed ? 'Source is in place' : 'Lift it with the tongs', function () { S.focus('src'); placeSource(); }, !st.placed, st.placed || S.hand.busy),
              u.button('Put it back in the store', function () { storeSource(); }, false, !st.placed || S.hand.busy)));
          u.task('2. Set the voltage to the bottom of the range', st.V === VMIN, 'E.H.T. at ' + st.V + ' V')
            .add(u.button('Knob to ' + VMIN + ' V', function () { S.focus('unit'); turnTo(VMIN); }, false, S.hand.busy));
          u.live(function () { return st.placed ? 'Source on the shelf  ·  E.H.T. ' + st.V + ' V' : 'Source in its lead store'; });
          u.note('Tongs, shield, distance: never a sealed source in your fingers, and never pointed at anyone.');
          u.next('Next: the counting curve', st.placed);
        },
        ok: function () { return st.placed; },
        auto: function () { return placeSource().then(function () { return turnTo(VMIN); }); } },

      { id: 'curve', title: 'Counting curve', view: 'unit', render: function (u) {
          u.h2('Count for ' + st.t + ' s at each voltage');
          u.p('Raise the E.H.T. in steps of ' + VSTEP + ' V while the tube is still silent - that is where the starting voltage is found - and in larger steps once the plateau is reached. At each step press START, let the preset time run out, and write down the count.');
          var tg = { v: Math.min(VMAX, st.V + VSTEP) };
          u.slider('Set the E.H.T. to', VMIN, VMAX, VSTEP, function () { return tg.v; }, function (v) { tg.v = v; }, 'V', 0);
          u.row(u.button('Turn the knob', function () { turnTo(tg.v); }, true, S.hand.busy),
            u.button('START (' + st.t + ' s)', function () { count(); }, false, S.hand.busy));
          u.row(u.button('Record V and counts', function () { record(); }, false, S.hand.busy),
            u.button('Source back to its store', function () { storeSource(); }, false, !st.placed || S.hand.busy));
          u.live(function () { return st.V + ' V  ·  ' + st.count + ' counts in ' + st.elapsed.toFixed(0) + ' s'; });
          u.h3('Observation table'); u.table();
          var zero = S.rows.some(function (r) { return r.N === 0; }), some = S.rows.some(function (r) { return r.N > 0; });
          if (!zero || !some) u.note('You need readings on both sides of the starting voltage: at least one with no counts at all and one with counts.');
          if (S.rows.length < 8) u.p(S.rows.length + ' of at least 8 voltages recorded.');
          u.next('Next: the result', S.rows.length >= 8 && zero && some);
        },
        ok: function () { return S.rows.length >= 8 && S.rows.some(function (r) { return r.N === 0; })
          && S.rows.some(function (r) { return r.N > 0; }); },
        auto: function () {
          /* 10 V steps while the tube is still coming on (that is where the starting voltage is found),
             20 V steps along the plateau. */
          var vs = [], v;
          for (v = VMIN; v <= 420; v += 10) vs.push(v);
          for (v = 440; v <= 700; v += 20) vs.push(v);
          return vs.reduce(function (pr, vv) {
            return pr.then(function () { return turnTo(vv); }).then(function () { return count(); })
              .then(function () { record(); });
          }, Promise.resolve()).then(function () { return turnTo(450); }).then(function () { return storeSource(); });
        } },
    ],

    tick: function () {
      showC(String(st.count));
      showT(st.elapsed.toFixed(0));
      hudV.set(st.V + ' V');
      hudC.set(String(st.count));
      hudR.set(st.placed ? rateNow().toFixed(2) + ' /s' : 'background only');
    },
  };
});
