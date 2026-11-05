/* Prayogshala studio module: GM COUNTING BENCH - counting statistics (B.Sc. nuclear physics).
   The same lead castle, end-window GM tube, sealed source and scaler-timer as the plateau experiment, but here
   nothing on the bench is touched at all: the same source is counted for the same time, over and over, and the
   only thing that changes is chance.
   Physics: the `gmtube` kernel of packs/modern_ug.js. Every count is a Poisson number drawn from the lab's own
   seed, so the same lab always gives the same fifty counts - and they scatter exactly as Poisson says. */
HoolaStudio.define('gm-statistics-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.gmtube, assign = HK.assign;
  var p = HK.paramsFor('gmtube', S.lab.params);
  var V_ = S.lab.variant || {}, SRC = V_.sample || 'Sealed Cs-137 check source, weak';
  var VMIN = 250, VMAX = 750, VSTEP = 10, VPLAT = p.Vp, NREP = Math.round(p.nrep);
  var st = { placed: false, shut: false, V: Math.round(p.V), t: p.t, counting: false, count: 0, elapsed: 0,
    taken: 0, done: {} };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function qAt(v, t) { return assign(p, { V: v, t: t === undefined ? st.t : t, N0: st.placed ? p.N0 : 0.0 }); }
  var SERIES = null;
  function series() { if (!SERIES) SERIES = KN.counts(qAt(st.V, st.t), NREP + 10); return SERIES; }
  function drawCounts(v, t) { var q = series(); return q[Math.min(q.length - 1, st.taken)]; }
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
    if (st.done[st.taken]) { S.say('That count is already written down. Press START for the next one.'); return false; }
    st.done[st.taken] = true;
    st.taken += 1;
    S.addRow({ i: st.taken, N: st.count });
    return true;
  }
  function stats(rows) {
    var ns = rows.map(function (r) { return r.N; }), i, m = S.fit.mean(ns), v = 0;
    for (i = 0; i < ns.length; i++) v += (ns[i] - m) * (ns[i] - m);
    v = ns.length > 1 ? v / (ns.length - 1) : 0;
    return { n: ns.length, mean: m, sd: Math.sqrt(v) };
  }

  function result(rows) {
    if (rows.length < 20) return null;
    var q = stats(rows);
    if (!(q.mean > 0)) return null;
    return { label: 'Standard deviation ÷ √(mean count)', value: q.sd / Math.sqrt(q.mean), unit: '', digits: 3,
      truth: 1.0,
      note: q.n + ' counts of ' + st.t + ' s: mean ' + q.mean.toFixed(1) + ', standard deviation ' + q.sd.toFixed(1)
        + ', and √(mean) = ' + Math.sqrt(q.mean).toFixed(1) + '. Poisson statistics say those last two should be the same.' };
  }

  return {
    camera: { pos: [-0.02, 0.95, 1.16], look: [-0.03, 0.1, -0.06] },
    views: { castle: [[-0.2, 0.36, 0.22], [-0.26, 0.1, -0.12]], tube: [[-0.16, 0.26, 0.08], [-0.26, 0.15, -0.09]],
      src: [[-0.18, 0.2, 0.06], [-0.26, 0.09, -0.09]], pot: [[0.06, 0.18, 0.3], [0.0, 0.02, 0.16]],
      tongs: [[0.1, 0.2, 0.34], [0.1, 0.0, 0.2]], unit: [[0.34, 0.32, 0.24], [0.3, 0.07, -0.1]],
      bench: [[-0.02, 0.95, 1.16], [-0.03, 0.1, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'Radioactive decay is random: every nucleus decides on its own, with no memory of what has gone before. The number of counts in a fixed time is therefore a Poisson number, whose standard deviation is the square root of its mean. That is why a count of N carries an uncertainty of √N.',
      formula: 'σ = √N̄',
      formulaNote: 'so the fractional uncertainty is 1/√N: counting four times as long halves it',
      more: ['Nothing on the bench is touched between the readings - the same source, the same shelf, the same counting time - so every bit of the scatter is the statistics of decay itself.',
        'For a mean above about twenty the Poisson distribution already looks like a Gaussian of the same width, which is why √N is used as the error bar on almost every count.',
        'A single count tells you both the number and its error: ' + 'N ± √N' + '.'],
      precautions: 'Do not move the source, the tube or the shelf between readings. Use the same preset time throughout, and take at least thirty counts before judging the scatter.' },
    book: { title: 'Expt. — Counting statistics with a GM counter',
      lines: ['Aim: show that the scatter of repeated counts', 'follows Poisson statistics (σ = √N̄).',
        'Source: ' + SRC, 'Working voltage ' + Math.round(p.V) + ' V, counting time ' + p.t + ' s.',
        'Nothing moved between readings.', 'Safety: tongs, shield, source back in its store.'],
      columns: [{ label: 'No.', get: function (r) { return r.i; } },
        { label: 'Counts N', get: function (r) { return r.N; } },
        { label: 'N − N̄', get: function (r, i) { var q = stats(S.rows); return (r.N - q.mean).toFixed(1); } }] },
    graph: { x: function (r) { return r.i; }, y: function (r) { return r.N; }, xlabel: 'reading number',
      ylabel: 'counts in ' + p.t + ' s',
      line: function (pts) { var m = S.fit.mean(pts.map(function (q) { return q[1]; }));
        return function () { return m; }; } },
    result: result,
    tol: 0.2,
    resultNote: 'The counts wander about their mean by roughly the square root of it, and no reading is "wrong": that scatter IS the measurement. It is also why a weak source needs a long count, and why the error on a count is quoted as √N.',
    chips: ['Why does the count change every time?', 'What is the error on a single count?',
      'Why count for longer?', 'Check my readings', 'Is a low count a mistake?'],
    viva: [['A count of 900 has a standard deviation of about', ['30', '900', '3'], 0, 'σ = √N = 30.'],
      ['Counting for nine times as long makes the fractional error', ['Three times smaller', 'Nine times smaller', 'Three times bigger'], 0,
        'The fractional error is 1/√N.'],
      ['The scatter in these readings comes from', ['The randomness of decay itself', 'A faulty timer', 'The source moving'], 0,
        'Nothing on the bench was touched between readings.']],
    askState: function () {
      var q = stats(S.rows);
      return { experiment: 'counting statistics: fifty counts of the same source for the same time',
        source: SRC, source_on_shelf: st.placed, tube_voltage_V: st.V, counting_time_s: st.t,
        counts_taken: S.rows.length, mean_count: +q.mean.toFixed(1), standard_deviation: +q.sd.toFixed(1),
        sqrt_of_mean: +Math.sqrt(Math.max(q.mean, 0)).toFixed(1) };
    },

    steps: [
      { id: 'place', title: 'Set up', view: 'castle', render: function (u) {
          u.h2('Place the source and set the working voltage');
          u.p('Put the source on the middle shelf with the tongs and set the tube to its working voltage, ' + Math.round(p.V) + ' V, found in the plateau experiment. After this, nothing on the bench is touched again.');
          u.task('1. Source on the middle shelf', st.placed, st.placed ? 'On the middle shelf' : 'In its lead store')
            .add(u.button(st.placed ? 'Source is in place' : 'Lift it with the tongs', function () { S.focus('src'); placeSource(); }, !st.placed, st.placed || S.hand.busy));
          u.task('2. Working voltage', st.V === Math.round(p.V), 'E.H.T. at ' + st.V + ' V')
            .add(u.button('Knob to ' + Math.round(p.V) + ' V', function () { S.focus('unit'); turnTo(Math.round(p.V)); }, false, S.hand.busy));
          u.live(function () { return st.placed ? 'Source on the shelf  ·  ' + st.V + ' V  ·  about ' + rateNow().toFixed(1) + ' counts per second' : 'Source in its lead store'; });
          u.note('From here on, do not move the source, the tube or the shelf. If you do, the experiment measures your hands, not the statistics.');
          u.next('Next: take the counts', st.placed);
        },
        ok: function () { return st.placed; },
        auto: function () { return placeSource().then(function () { return turnTo(Math.round(p.V)); }); } },

      { id: 'counts', title: 'Repeated counts', view: 'unit', render: function (u) {
          u.h2('Count for ' + st.t + ' s, over and over');
          u.p('Press START, wait for the preset time, write the count down, and do it again. Thirty counts are enough to see the pattern; fifty are better.');
          u.row(u.button('START (' + st.t + ' s)', function () { count(); }, true, S.hand.busy),
            u.button('Write this count down', function () { record(); }, false, S.hand.busy));
          u.row(u.button('Take ten counts', function () {
            var chain = Promise.resolve(), i;
            for (i = 0; i < 10; i++) { chain = chain.then(function () { return count(); }).then(function () { record(); }); }
            return chain;
          }, false, S.hand.busy));
          u.live(function () { var q = stats(S.rows);
            return S.rows.length + ' counts  ·  mean ' + q.mean.toFixed(1) + '  ·  s.d. ' + q.sd.toFixed(1)
              + '  ·  √mean ' + Math.sqrt(Math.max(q.mean, 0)).toFixed(1); });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 20) u.p(S.rows.length + ' of at least 20 counts taken (thirty or more is better).');
          u.next('Next: the scatter', S.rows.length >= 20);
        },
        ok: function () { return S.rows.length >= 20; },
        auto: function () {
          var chain = Promise.resolve(), i;
          for (i = 0; i < 30; i++) { chain = chain.then(function () { return count(); }).then(function () { record(); }); }
          return chain.then(function () { return storeSource(); });
        } },
    ],

    tick: function () {
      showC(String(st.count));
      showT(st.elapsed.toFixed(0));
      hudV.set(st.V + ' V');
      hudC.set(String(st.count));
      hudR.set(S.rows.length + ' counts taken');
    },
  };
});
