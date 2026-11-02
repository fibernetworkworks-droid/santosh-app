/* Prayogshala studio module: Potentiometer - internal resistance of a cell (NCERT Class XII). A four-wire potentiometer
   (4 × 1 m joined in series by copper strips, a scale under each wire), a 6 V driver supply with key K₁ and a rheostat,
   a Leclanché cell under test with a resistance box R and key K₂ across it, a zero-centre galvanometer and a jockey.
   The galvanometer reads the circuit kernel (kernels.js, MNA) with the lab's own net (S.lab.cfg): the same numbers the
   server checks. K₁ is not in the net: an open K₁ is the same net with its driver branch broken (E0 = 0, Rh open).
   The hidden unknown is the cell's internal resistance r (r_int). */
HoolaStudio.define('potentiometer-internal-resistance', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.circuit, CFG = S.lab.cfg;
  var p = HK.paramsFor('circuit', S.lab.params);
  var FOM = 20e-6, LEN = 400, LMIN = 4, LMAX = 396;
  var st = { traced: false, k1: false, k2: false, R: 0, target: 150, endA: 0, endB: 0, pend: null };
  var J = { l: 150, mode: 'rest', pressed: false };

  // ---------- helpers (kept inside this module)
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]); return S.wire(pts, color);
  }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  var ZAX = new T.Vector3(0, 0, 1), XAX = new T.Vector3(1, 0, 0);
  function plugKeyAt(x, z, name) {   // a plug key with terminal screws; the hand moves its plug: set(on) -> Promise
    var key = S.plugKey([x, 0, z]), plug = key.userData.plug, on = false;
    var l = S.label(name, { w: 0.016, ratio: 0.7, color: '#f0e6c8' }); l.rotation.x = -Math.PI / 2; l.position.set(x, 0.0165, z + 0.014); S.scene.add(l);
    function pose(k) { return { x: 0.062 * (1 - k), y: 0.008 + 0.016 * k + 0.04 * Math.sin(Math.PI * k), z: 0.012 * (1 - k), rz: Math.PI / 2 * (1 - k) }; }
    function put(k) { var q = pose(k); plug.position.set(q.x, q.y, q.z); plug.rotation.set(0, 0, q.rz); }
    function head(k) { var q = pose(k); return key.localToWorld(new T.Vector3(0, 0.013, 0).applyAxisAngle(ZAX, q.rz).add(new T.Vector3(q.x, q.y, q.z))); }
    put(0);
    return { g: key, L: post(x - 0.02, 0.022, z - 0.008), R: post(x + 0.02, 0.022, z - 0.008), isOn: function () { return on; },
      move: function (want) { var a = on ? 1 : 0, b = want ? 1 : 0; if (!want) on = false;
        return S.hand.pinchMove(head(a), function (k) { return head(a + (b - a) * k); }, function (k) { put(a + (b - a) * k); }, { ms: 900, mode: 'top' })
          .then(function () { put(b); on = !!want; S.click(1400, 0.04, 0.1); }); } };
  }

  // ---------- the potentiometer: four 1 m wires in series on a wooden board, a scale under each wire
  var BZ = -0.38, TOP = 0.025, WY = TOP + 0.006, WZS = [-0.505, -0.425, -0.345, -0.265];
  var pot = new T.Group(); S.scene.add(pot);
  var board = S.mesh(new T.BoxGeometry(1.2, TOP, 0.36), M.darkWood); board.position.set(0, TOP / 2, BZ); pot.add(board);
  [[-0.56, -0.54], [0.56, -0.54], [-0.56, -0.22], [0.56, -0.22]].forEach(function (f) { var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.003, 16), M.rubber); ft.position.set(f[0], 0.0015, f[1]); pot.add(ft); });
  var wireMat = new T.MeshStandardMaterial({ color: 0xd9d3c4, roughness: 0.22, metalness: 1 });
  WZS.forEach(function (z, i) {
    var w = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 1.0, 8), wireMat); w.rotation.z = Math.PI / 2; w.position.set(0, WY, z); pot.add(w);
    var tex = S.canvasTex(4096, 120, function (x, W, H) {
      x.drawImage(S.woodTex.image, 0, 0, W, H); x.fillStyle = 'rgba(255,248,230,.5)'; x.fillRect(0, 0, W, H);
      var k = (W - 48) / 1000; x.fillStyle = '#161616'; x.textAlign = 'center';
      for (var m = 0; m <= 1000; m++) { var cm = i % 2 ? 100 * i + (1000 - m) / 10 : 100 * i + m / 10, xx = 24 + m * k, n = Math.round(cm * 10);
        var len = n % 100 === 0 ? 50 : n % 50 === 0 ? 38 : n % 10 === 0 ? 28 : 14; x.fillRect(xx - (n % 10 ? 0.7 : 1.2), 0, n % 10 ? 1.4 : 2.4, len);
        if (n % 100 === 0) { var big = n % 500 === 0; x.font = (big ? '700 44px' : '600 34px') + ' "Public Sans", sans-serif'; x.fillText(String(Math.round(cm)), xx, big ? 100 : 84); } }
    });
    var sc = S.mesh(new T.BoxGeometry(1.012, 0.003, 0.026), [M.wood, M.wood, new T.MeshStandardMaterial({ map: tex, roughness: 0.55 }), M.wood, M.wood, M.wood]);
    sc.position.set(0, TOP + 0.0015, z + 0.027); pot.add(sc);
  });
  function strip(x, z0, z1) { var b = S.mesh(new T.BoxGeometry(0.03, 0.005, z1 - z0 + 0.02), M.copper); b.position.set(x, TOP + 0.0025, (z0 + z1) / 2); pot.add(b);
    [z0, z1].forEach(function (z) { var c = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.004, 6), M.brass); c.position.set(x, TOP + 0.007, z); pot.add(c); }); }
  strip(0.515, WZS[0], WZS[1]); strip(-0.515, WZS[1], WZS[2]); strip(0.515, WZS[2], WZS[3]);
  [WZS[0], WZS[3]].forEach(function (z) { var b = S.mesh(new T.BoxGeometry(0.03, 0.005, 0.03), M.copper); b.position.set(-0.53, TOP + 0.0025, z); pot.add(b); });
  var plate = S.label('POTENTIOMETER · 4 × 100 cm', { w: 0.2, ratio: 0.1, color: '#f3ead2' }); plate.rotation.x = -Math.PI / 2; plate.position.set(0.0, TOP + 0.0005, -0.545); pot.add(plate);
  S.contact(1.32, 0.48, 0, BZ, 0.55);
  var tA = post(-0.535, TOP + 0.005, WZS[0]), tB = post(-0.535, TOP + 0.005, WZS[3]);
  [['A', WZS[0]], ['B', WZS[3]]].forEach(function (a) { var l = S.label(a[0], { w: 0.016, ratio: 1, color: '#f3ead2' }); l.rotation.x = -Math.PI / 2; l.position.set(-0.575, TOP + 0.0005, a[1]); S.scene.add(l); });

  // ---------- driver circuit: 6 V supply, key K1, rheostat (set once, not touched again)
  var PB = [-0.85, -0.68];
  var pb = S.powerBox([PB[0], 0, PB[1]], 'BATTERY ELIMINATOR');
  var pbV = S.label('6 V DC', { w: 0.05, ratio: 0.3, color: '#f2f2f2' }); pbV.position.set(PB[0] + 0.045, 0.034, PB[1] + 0.0405); S.scene.add(pbV);
  var lamp = S.mesh(new T.SphereGeometry(0.004, 12, 10), new T.MeshStandardMaterial({ color: 0x3a0b08, emissive: 0xe0140a, roughness: 0.3 })); lamp.position.set(PB[0] - 0.05, 0.035, PB[1] + 0.041); S.scene.add(lamp);
  var pbPlus = { at: new T.Vector3(PB[0] + 0.04, 0.109, PB[1]) }, pbMinus = { at: new T.Vector3(PB[0] - 0.04, 0.109, PB[1]) };
  var K1 = plugKeyAt(-0.84, -0.44, 'K₁');
  var RHL = 0.24, RHP = [-0.45, -0.69], RH_TOTAL = 10;
  var rh = S.rheostat([RHP[0], 0, RHP[1]], RHL); rh.setFraction(p.Rh / RH_TOTAL);
  var rhA = post(RHP[0] - RHL / 2 - 0.008, 0.05, RHP[1]); post(RHP[0] + RHL / 2 + 0.008, 0.05, RHP[1]);
  var rhC = post(RHP[0] + RHL / 2 - 0.004, 0.065, RHP[1]);
  var rhPlate = S.label('RHEOSTAT 10 Ω', { w: 0.06, ratio: 0.18, color: '#f3ead2', bg: '#2b2b2b' }); rhPlate.position.set(RHP[0] + RHL / 2, 0.025, RHP[1] + 0.0105); S.scene.add(rhPlate);

  // ---------- Leclanché cell: glass jar of ammonium chloride, porous pot with a carbon rod (+), zinc rod (-)
  var CC = [0.62, -0.66];
  var cell = S.beaker(0.036, 0.1, [CC[0], 0, CC[1]], 0xe9ecdf, 0.62);
  var pp = S.mesh(new T.CylinderGeometry(0.017, 0.017, 0.095, 28), new T.MeshStandardMaterial({ color: 0xb46a3c, roughness: 0.92 })); pp.position.set(-0.008, 0.0525, 0); cell.add(pp);
  var ppTop = S.mesh(new T.CylinderGeometry(0.0172, 0.0172, 0.006, 28), M.black); ppTop.position.set(-0.008, 0.101, 0); cell.add(ppTop);
  var carbon = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.05, 16), new T.MeshStandardMaterial({ color: 0x1f1f22, roughness: 0.7 })); carbon.position.set(-0.008, 0.12, 0); cell.add(carbon);
  var zinc = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.125, 14), new T.MeshStandardMaterial({ color: 0x9ea4a8, roughness: 0.45, metalness: 0.7 })); zinc.position.set(0.022, 0.0675, 0.004); cell.add(zinc);
  S.contact(0.11, 0.11, CC[0], CC[1], 0.5);
  var cPlus = post(CC[0] - 0.008, 0.145, CC[1], 'red'), cMinus = post(CC[0] + 0.022, 0.13, CC[1] + 0.004, 'black');

  // ---------- galvanometer, resistance box R and key K2
  var gal = S.meter({ min: -30, max: 30, zeroCentre: true, ticks: 6, unit: 'G', symbol: 'G', caption: 'GALVANOMETER 30–0–30', pos: [0.33, 0, -0.7] });
  var gP = { at: wpt(gal, 0.035, 0.07, -0.03) }, gM = { at: wpt(gal, -0.035, 0.07, -0.03) };
  var RB = [0.8, -0.44];
  var rb = S.resistanceBox([RB[0], 0, RB[1]]);
  var rbPlugs = rb.children.filter(function (c) { return c.isGroup; }), VALS = [1, 2, 2, 5, 10, 20, 20, 50], out = VALS.map(function () { return false; });
  var rbL = post(RB[0] - 0.072, 0.053, RB[1] - 0.026), rbR = post(RB[0] + 0.072, 0.053, RB[1] - 0.026);
  function pPose(i, k) { return { x: -0.063 + i * 0.018, y: 0.058 + (0.0065 - 0.058) * k + 0.05 * Math.sin(Math.PI * k), z: 0.064 * k, rx: Math.PI / 2 * k }; }
  function pApply(i, k) { var q = pPose(i, k); rbPlugs[i].position.set(q.x, q.y, q.z); rbPlugs[i].rotation.set(q.rx, 0, 0); }
  function pHead(i, k) { var q = pPose(i, k); return rb.localToWorld(new T.Vector3(0, 0.012, 0).applyAxisAngle(XAX, q.rx).add(new T.Vector3(q.x, q.y, q.z))); }
  rbPlugs.forEach(function (pl, i) { pApply(i, 0); });
  function plan(R) { var left = R, o = VALS.map(function () { return false; }); for (var i = VALS.length - 1; i >= 0; i--) if (VALS[i] <= left) { o[i] = true; left -= VALS[i]; } return o; }
  function boxValue() { return VALS.reduce(function (s, v, i) { return s + (out[i] ? v : 0); }, 0); }
  var K2 = plugKeyAt(0.79, -0.22, 'K₂');

  // ---------- jockey (knife-edge on a bakelite handle)
  var jock = new T.Group(); S.scene.add(jock);
  var jt = S.mesh(new T.ConeGeometry(0.0034, 0.012, 4), M.brass); jt.rotation.x = Math.PI; jt.position.y = 0.006; jt.scale.z = 0.35; jock.add(jt);
  var jc = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.008, 16), M.brass); jc.position.y = 0.015; jock.add(jc);
  var jh = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 0.064, 20), M.bakelite); jh.position.y = 0.051; jock.add(jh);
  var jcap = S.mesh(new T.CylinderGeometry(0.0042, 0.0042, 0.008, 16), M.brass); jcap.position.y = 0.087; jock.add(jcap);
  var jShadow = S.contact(0.05, 0.05, 0, 0, 0.35);
  var REST = { pos: new T.Vector3(0.28, 0.0066, -0.13), rz: Math.PI / 2 };
  function wirePoint(l) { var w = Math.min(3, Math.floor(l / 100)), d = l - 100 * w; return new T.Vector3(w % 2 ? 0.5 - d / 100 : -0.5 + d / 100, WY + 0.0006, WZS[w]); }
  function onWire(l) { return { pos: wirePoint(l), rz: 0 }; }
  function cur() { return { pos: jock.position.clone(), rz: jock.rotation.z }; }
  function grip(q) { return q.pos.clone().add(new T.Vector3(-0.05 * Math.sin(q.rz), 0.05 * Math.cos(q.rz), 0)); }
  function capOf(q) { return q.pos.clone().add(new T.Vector3(-0.091 * Math.sin(q.rz), 0.091 * Math.cos(q.rz), 0)); }
  function path(a, b, k, lift) {
    var A1 = { pos: a.pos.clone().add(new T.Vector3(0, lift, 0)), rz: b.rz }, B1 = { pos: b.pos.clone().add(new T.Vector3(0, lift, 0)), rz: b.rz };
    function mix(x, y, t) { return { pos: x.pos.clone().lerp(y.pos, t), rz: x.rz + (y.rz - x.rz) * t }; }
    return k < 0.3 ? mix(a, A1, k / 0.3) : k < 0.75 ? mix(A1, B1, (k - 0.3) / 0.45) : mix(B1, b, (k - 0.75) / 0.25);
  }
  var jLead = null, lastCap = '';
  function apply(q) { jock.position.copy(q.pos); jock.rotation.set(0, 0, q.rz);
    jShadow.position.set(q.pos.x - 0.045 * Math.sin(q.rz), 0.0009, q.pos.z); jShadow.scale.setScalar(q.rz > 0.7 ? 1.4 : 0.8);
    var c = capOf(q), key2 = c.x.toFixed(4) + c.y.toFixed(4) + c.z.toFixed(4); if (key2 === lastCap) return; lastCap = key2;
    var g = gP.at, pts = [[g.x, g.y, g.z], [g.x, g.y + 0.03, g.z], [g.x * 0.6 + c.x * 0.4, 0.13, -0.6], [c.x, Math.max(c.y + 0.03, 0.115), c.z - 0.035], [c.x, c.y, c.z]];
    if (!jLead) jLead = S.wire(pts, 'black'); else jLead.set(pts); }
  apply(REST);
  function moveJockey(l) {
    if (busy()) return Promise.resolve(false);
    if (!(l >= LMIN && l <= LMAX)) { S.say('Touch the wire between ' + LMIN + ' cm and ' + LMAX + ' cm.'); return Promise.resolve(false); }
    l = Math.round(l * 10) / 10;
    var a = cur(), b = onWire(l), held = J.mode === 'held', dist = a.pos.distanceTo(b.pos);
    J.pressed = false; S.hand.busy = true;
    var pre = held ? Promise.resolve() : S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(grip(a), 'side', 700); }).then(function () { return S.hand.shape('pinch', 260); });
    var lift = held ? 0.02 : 0.07, ms = held ? Math.min(1400, 420 + dist * 1800) : 1150;
    return pre.then(function () { return S.hand.follow(function (k) { return grip(path(a, b, k, lift)); }, 'side', ms, function (k) { apply(path(a, b, k, lift)); }); })
      .then(function () { apply(b); J.l = l; J.mode = 'held'; J.pressed = true; S.hand.busy = false; S.click(700, 0.02, 0.05); S.render(); return true; },
        function (e) { S.hand.busy = false; throw e; });
  }
  function putDown() {
    if (J.mode !== 'held' || S.hand.busy) return Promise.resolve();
    var a = cur(); J.pressed = false; S.hand.busy = true;
    return S.hand.follow(function (k) { return grip(path(a, REST, k, 0.07)); }, 'side', 1000, function (k) { apply(path(a, REST, k, 0.07)); })
      .then(function () { return S.hand.shape('relaxed', 220); }).then(function () { return S.hand.away(); })
      .then(function () { apply(REST); J.mode = 'rest'; S.hand.busy = false; S.render(); }, function (e) { S.hand.busy = false; throw e; });
  }

  // ---------- leads (NCERT circuit): driver: + -> K1 -> rheostat -> A ... B -> -.  Cell: + -> A, - -> G -> jockey.  R + K2 across the cell.
  lead(pbPlus.at, K1.L.at, 'red', [[-0.82, -0.58], [-0.86, -0.5]]);
  lead(K1.R.at, rhA.at, 'red', [[-0.76, -0.47], [-0.64, -0.6], [-0.6, -0.68]]);
  lead(rhC.at, tA.at, 'red', [[-0.3, -0.64], [-0.5, -0.585]], 0.012);
  lead(pbMinus.at, tB.at, 'black', [[-0.94, -0.6], [-0.94, -0.3], [-0.64, -0.265]]);
  lead(cPlus.at, tA.at, 'yellow', [[0.56, -0.6], [0.0, -0.59], [-0.45, -0.575]]);
  lead(cMinus.at, gM.at, 'blue', [[0.52, -0.73]]);
  lead(rbL.at, cPlus.at, 'yellow', [[0.7, -0.52], [0.64, -0.6]]);
  lead(rbR.at, K2.R.at, 'blue', [[0.9, -0.4], [0.86, -0.25]]);
  lead(K2.L.at, cMinus.at, 'blue', [[0.7, -0.24], [0.68, -0.5]]);

  S.addApparatus('pot', pot, 'Potentiometer (4 wires × 1 m)', 'Four uniform wires joined in series by copper strips: 400 cm from A to B, with a scale under each wire.');
  S.addApparatus('jockey', jock, 'Jockey', 'A knife-edge contact. Touch the wire gently; do not slide it while pressed.');
  S.addApparatus('gal', gal, 'Galvanometer (30–0–30)', 'Zero-centre. At balance no current flows through it. About 20 µA per division.');
  S.addApparatus('cell', cell, 'Leclanché cell (under test)', 'Carbon rod in a porous pot (+), zinc rod (−), in ammonium chloride. Its internal resistance r is what we measure.');
  S.addApparatus('pb', pb, 'Driver supply (6 V DC)', 'Keeps a steady current in the potentiometer wire. Its emf must be more than the cell\'s.');
  S.addApparatus('k1', K1.g, 'Key K₁', 'Switches the driver current through the potentiometer wire.');
  S.addApparatus('rh', rh, 'Rheostat', 'Sets the current in the wire. Once set, do not move it: the potential gradient must stay the same.');
  S.addApparatus('rb', rb, 'Resistance box R', 'The shunt across the cell. Pull out plugs to choose R.');
  S.addApparatus('k2', K2.g, 'Key K₂', 'Puts R across the cell. Close it only while finding l₂; the cell runs down otherwise.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  S.scene.children.slice().forEach(function (o) { if (o.isMesh && o.material && o.material.isMeshBasicMaterial && o.material.transparent && Math.abs(o.position.x + 0.5) < 1e-6 && Math.abs(o.position.z - 0.08) < 1e-6) S.scene.remove(o); });

  // ---------- physics: the lab's net
  function iGat(l) { var q = HK.assign(p, { lj: l / LEN, k2: K2.isOn() ? 1 : 0, Rb: Math.max(st.R, 1e-6) });
    if (!K1.isOn()) { q.E0 = 0; q.Rh = 1e9; }
    return K.view(K.init(q, CFG), q, CFG).I_G; }
  function contact() { return J.mode === 'held' && J.pressed; }
  function divNow() { return contact() ? iGat(J.l) / FOM : 0; }
  function divText(d) { var a = Math.abs(d); if (!contact()) return J.mode === 'held' ? 'jockey lifted' : 'jockey not touching the wire';
    if (a < 0.25) return 'no deflection'; return (a >= 30 ? 'off scale, ' : '') + Math.min(30, a).toFixed(1) + ' div to the ' + (d > 0 ? 'right' : 'left'); }
  function bestHere() { var d0 = Math.abs(iGat(J.l)); return d0 <= Math.abs(iGat(J.l - 0.1)) + 1e-15 && d0 <= Math.abs(iGat(J.l + 0.1)) + 1e-15; }
  var hudL = S.hudCard('Jockey at'), hudG = S.hudCard('Galvanometer'), hudK = S.hudCard('K₁ · K₂ · R');

  function setKey(which, on) {
    var kk = which === 1 ? K1 : K2;
    if (!!on === kk.isOn()) return Promise.resolve();
    if (busy()) return Promise.resolve();
    if (which === 2 && on && !(st.R > 0)) { S.say('R is 0 Ω: closing K₂ now would short-circuit the cell. Take a plug out of the resistance box first.'); return Promise.resolve(); }
    return putDown().then(function () { return kk.move(on); }).then(function () {
      S.say(which === 1 ? (on ? 'K₁ closed: a steady current flows along the potentiometer wire.' : 'K₁ open: no current in the wire.')
        : (on ? 'K₂ closed: the cell now sends a current through R, so its terminal voltage falls below its emf.' : 'K₂ open: the cell gives no current; balance now measures its emf.'));
      S.render(); });
  }
  function setR(R) {
    if (busy()) return Promise.resolve();
    if (K2.isOn()) { S.say('Open K₂ before changing R.'); return Promise.resolve(); }
    var want = plan(R), idx = [];
    want.forEach(function (w, i) { if (w !== out[i]) idx.push(i); });
    if (!idx.length) { st.R = boxValue(); return Promise.resolve(); }
    return putDown().then(function () {
      return idx.reduce(function (pr, i) { return pr.then(function () { var a = out[i] ? 1 : 0, b = want[i] ? 1 : 0;
        return S.hand.pinchMove(pHead(i, a), function (k) { return pHead(i, a + (b - a) * k); }, function (k) { pApply(i, a + (b - a) * k); }, { ms: 750, mode: 'top', reachMs: 600 })
          .then(function () { pApply(i, b); out[i] = want[i]; st.R = boxValue(); S.click(1100, 0.03, 0.06); }); }); }, Promise.resolve());
    }).then(function () { st.R = boxValue(); S.say('R = ' + st.R + ' Ω (plugs out: ' + VALS.filter(function (v, i) { return out[i]; }).join(' + ') + ' Ω).'); S.render(); });
  }
  function endTest(which) {
    if (!K1.isOn()) { S.say('Close K₁ first, so a current flows in the wire.'); return Promise.resolve(); }
    if (K2.isOn()) { S.say('Keep K₂ open for this check.'); return Promise.resolve(); }
    return moveJockey(which === 'A' ? 5 : 395).then(function (ok) { if (!ok) return; var d = divNow(); if (which === 'A') st.endA = d; else st.endB = d;
      if (st.endA && st.endB) S.say(st.endA * st.endB < 0 ? 'Opposite deflections at the two ends: the balance point lies on the wire.' : 'Deflections are the same way at both ends: no balance point. Check that K₁ is closed and the + terminals both go to A.');
      S.render(); });
  }
  function endsOk() { return st.endA * st.endB < 0; }
  function recordL1() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!K1.isOn()) { S.say('Close K₁ first.'); return false; }
    if (K2.isOn()) { S.say('l₁ is found with K₂ open. Open K₂ first.'); return false; }
    if (!contact()) { S.say('Touch the jockey on the wire first.'); return false; }
    if (Math.abs(divNow()) >= 0.25 && !bestHere()) { S.say('The galvanometer still shows ' + divText(divNow()) + '. Move the jockey until it reads zero.'); return false; }
    st.pend = { l1: J.l }; S.say('l₁ = ' + J.l.toFixed(1) + ' cm noted (K₂ open). Now choose R, close K₂ and find the new balance l₂.'); S.render(); return true;
  }
  function recordL2() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.pend) { S.say('Find and note l₁ with K₂ open first.'); return false; }
    if (!K2.isOn()) { S.say('l₂ is found with K₂ closed. Close K₂ first.'); return false; }
    if (!contact()) { S.say('Touch the jockey on the wire first.'); return false; }
    if (Math.abs(divNow()) >= 0.25 && !bestHere()) { S.say('The galvanometer still shows ' + divText(divNow()) + '. Move the jockey until it reads zero.'); return false; }
    if (!(J.l < st.pend.l1)) { S.say('With K₂ closed the balance must come before l₁ = ' + st.pend.l1.toFixed(1) + ' cm. Look again.'); return false; }
    if (S.rows.some(function (r) { return r.R === st.R; })) { S.say('You already have a reading with R = ' + st.R + ' Ω. Open K₂ and change R.'); return false; }
    if (S.rows.length >= 8) { S.say('Eight readings are plenty. Go on to the result.'); return false; }
    S.addRow({ R: st.R, l1: st.pend.l1, l2: J.l }); st.pend = null;
    S.say('Written: R = ' + S.rows[S.rows.length - 1].R + ' Ω, l₁ = ' + S.rows[S.rows.length - 1].l1.toFixed(1) + ' cm, l₂ = ' + J.l.toFixed(1) + ' cm. Open K₂ now so the cell does not run down.');
    return true;
  }
  function findNull() {
    var probe = function (mm) { return moveJockey(mm / 10).then(function () { return divNow(); }); };
    var lo = LMIN * 10, hi = LMAX * 10, dlo, dhi;
    return probe(lo).then(function (d) { dlo = d; return probe(hi); }).then(function (d) { dhi = d;
      if (dlo * dhi > 0) { S.say('Same deflection at both ends: there is no balance point on the wire.'); return null; }
      function step() { if (hi - lo <= 1) return Promise.resolve();
        var mid = Math.round((lo + hi) / 2); return probe(mid).then(function (dm) { if (dm === 0) { lo = hi = mid; return; } if ((dm > 0) === (dlo > 0)) { lo = mid; dlo = dm; } else { hi = mid; dhi = dm; } return step(); }); }
      return step().then(function () { return probe(Math.abs(dlo) <= Math.abs(dhi) ? lo : hi); }); });
  }
  function trace() { st.traced = true; S.focus('pot'); S.say('Driver: supply +, K₁ and the rheostat to A, the wire to B, back to −. The cell\'s + also goes to A; its − goes through the galvanometer to the jockey. R and K₂ are across the cell.'); S.render(); }
  function jockeyControls(u) {
    u.slider('Jockey position from A', LMIN, LMAX, 0.1, function () { return st.target; }, function (v) { st.target = v; }, 'cm', 1);
    var hb = S.hand.busy, nh = J.mode !== 'held';
    u.row(u.button('Touch the jockey here', function () { moveJockey(st.target); }, true, hb));
    u.row(u.button('−1 cm', function () { moveJockey(J.l - 1); }, false, hb || nh), u.button('−1 mm', function () { moveJockey(J.l - 0.1); }, false, hb || nh),
      u.button('+1 mm', function () { moveJockey(J.l + 0.1); }, false, hb || nh), u.button('+1 cm', function () { moveJockey(J.l + 1); }, false, hb || nh));
    u.live(function () { return (J.mode === 'held' ? 'Jockey at ' + J.l.toFixed(1) + ' cm' : 'Jockey on the bench') + ' · Galvanometer: ' + divText(divNow()); });
  }
  function rRow(u) { var row = u.row(); [2, 4, 5, 8, 10].forEach(function (v) { row.appendChild(u.button(v + ' Ω', function () { setR(v); }, st.R === v, S.hand.busy || K2.isOn())); }); }

  return {
    camera: { pos: [0.0, 1.5, 1.45], look: [0.0, 0.0, -0.42] },
    views: { pot: [[0.0, 1.1, 0.8], [0.0, 0.0, -0.4]], jockey: [[0.0, 0.85, 0.55], [0.05, 0.0, -0.45]], driver: [[-0.5, 1.0, 0.55], [-0.55, 0.0, -0.5]],
      gal: [[0.36, 0.32, -0.35], [0.33, 0.05, -0.7]], cell: [[0.66, 0.32, -0.32], [0.62, 0.07, -0.66]], pb: [[-0.74, 0.4, -0.3], [-0.85, 0.05, -0.66]],
      k1: [[-0.78, 0.3, -0.18], [-0.84, 0.02, -0.44]], rh: [[-0.42, 0.34, -0.38], [-0.45, 0.04, -0.69]], rb: [[0.82, 0.32, -0.12], [0.8, 0.03, -0.42]],
      k2: [[0.8, 0.28, 0.02], [0.79, 0.02, -0.22]], right: [[0.55, 0.8, 0.3], [0.55, 0.0, -0.45]], book: [[0.6, 0.44, 0.52], [0.66, 0.0, 0.08]] },
    theory: { principle: 'A potentiometer measures a potential difference without drawing current. With K₂ open the cell gives no current, so the balance length l₁ measures its emf E. With R across the cell (K₂ closed) a current flows and the balance l₂ measures the smaller terminal voltage V.',
      formula: 'r = R (l₁ − l₂) / l₂', formulaNote: 'since E / V = l₁ / l₂ and r = R (E / V − 1)',
      more: ['The driver current in the wire is kept the same throughout (K₁ closed, rheostat not touched), so the fall of potential per cm, k, is constant: E = k l₁ and V = k l₂.'],
      precautions: 'The driver emf must be more than the cell\'s. Check that the jockey gives opposite deflections at the two ends before you start. Do not move the rheostat during the experiment. Close K₂ only while finding l₂. Touch the jockey gently.' },
    book: { title: 'Expt. — Potentiometer: r of a cell', at: [0.66, 0.08, -0.1],
      lines: ['Aim: to find the internal resistance r of a cell.', 'Potentiometer wire: 400 cm, scale LC 0.1 cm', 'E = k l₁ (K₂ open),  V = k l₂ (K₂ closed)', 'r = R (l₁ − l₂) / l₂', 'Precautions: rheostat fixed, K₂ closed', 'only while balancing.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'R (Ω)', get: function (r) { return r.R; } }, { label: 'l₁ (cm)', get: function (r) { return r.l1.toFixed(1); } },
        { label: 'l₂ (cm)', get: function (r) { return r.l2.toFixed(1); } }, { label: 'r (Ω)', get: function (r) { return (r.R * (r.l1 - r.l2) / r.l2).toFixed(3); } }] },
    graph: { x: function (r) { return 1 / r.R; }, y: function (r) { return r.l1 / r.l2; }, xlabel: '1/R (1/Ω)', ylabel: 'l₁ / l₂', x0: 0, y0: 0,
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: function (rows) { if (rows.length < 2) return null; var v = S.fit.mean(rows.map(function (r) { return r.R * (r.l1 - r.l2) / r.l2; }));
      return { label: 'r', value: v, unit: 'Ω', digits: 2, truth: p.r_int, note: 'Mean of r = R(l₁ − l₂)/l₂. On the graph l₁/l₂ = 1 + r (1/R): intercept 1, slope r.' }; },
    tol: 0.03,
    chips: ['Why must the driver emf be larger than the cell\'s?', 'Why does l₂ come out smaller than l₁?', 'Why must the rheostat not be moved?', 'Check my readings', 'Why close K₂ only briefly?'],
    viva: [['Why is a potentiometer better than a voltmeter for measuring emf?', ['At balance it draws no current from the cell', 'It has a bigger scale', 'It needs no battery'], 0, 'A voltmeter draws some current, so it reads the terminal voltage, not the emf.'],
      ['If the jockey gives deflections in the same direction at both ends, the likely cause is', ['The driver emf is less than the cell\'s, or a polarity is reversed', 'The galvanometer is too sensitive', 'R is too large'], 0, 'With no point on the wire at the cell\'s potential there can be no balance.']],
    askState: function () { return { K1_closed: K1.isOn(), K2_closed: K2.isOn(), resistance_box_R_ohm: st.R, jockey_cm: J.mode === 'held' ? J.l : null, jockey_touching_wire: contact(),
      galvanometer_div: +divNow().toFixed(1), galvanometer: divText(divNow()), noted_l1_cm: st.pend ? st.pend.l1 : null, readings_taken: S.rows.length, driver_emf_V: 6 }; },

    steps: [
      { id: 'driver', title: 'Driver circuit', view: 'driver', render: function (u) {
          u.h2('Switch on the driver circuit');
          u.task('1. Trace the circuit', st.traced, st.traced ? 'Driver through A → B; cell + to A, − through G to the jockey; R + K₂ across the cell' : 'Follow the leads')
            .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
          u.task('2. Close key K₁', K1.isOn(), K1.isOn() ? 'A steady current flows in the wire' : 'Key open').add(u.button(K1.isOn() ? 'K₁ is in' : 'Insert the plug in K₁', function () { setKey(1, true); }, true, K1.isOn() || S.hand.busy));
          var t3 = u.task('3. Check the two ends (K₂ open)', endsOk(), endsOk() ? 'Opposite deflections: a balance point exists' : 'Touch the jockey near A and near the far end, and compare the needle');
          var row = document.createElement('div'); row.className = 'row';
          row.appendChild(u.button('Touch near A (5 cm)', function () { endTest('A'); }, false, S.hand.busy || !K1.isOn()));
          row.appendChild(u.button('Touch near the end (395 cm)', function () { endTest('B'); }, false, S.hand.busy || !K1.isOn())); t3.add(row);
          u.live(function () { return 'Galvanometer: ' + divText(divNow()); });
          u.note('The rheostat is already set. Do not move it during the experiment: the fall of potential per cm must stay the same.');
          u.next('Next: find the balance points', st.traced && K1.isOn() && endsOk());
        },
        ok: function () { return st.traced && K1.isOn() && endsOk(); },
        auto: function () { trace(); return setKey(1, true).then(function () { return endTest('A'); }).then(function () { return endTest('B'); }); } },
      { id: 'balance', title: 'Balance l₁, l₂', view: 'pot', render: function (u) {
          u.h2(st.pend ? 'Find l₂ with K₂ closed' : 'Find l₁ with K₂ open');
          u.p(st.pend ? 'l₁ = ' + st.pend.l1.toFixed(1) + ' cm is noted. Choose R, close K₂, then find the new balance point (it comes earlier) and record l₂.'
            : 'With K₂ open the cell gives no current. Touch the jockey along the wires until the galvanometer reads zero, then note l₁.');
          jockeyControls(u);
          if (!st.pend) u.row(u.button('Note l₁ (K₂ open)', function () { recordL1(); }, true, !contact()));
          else u.row(u.button('Record l₂ (K₂ closed)', function () { recordL2(); }, true, !contact() || !K2.isOn()));
          u.row(u.button(K2.isOn() ? 'Open K₂' : 'Close K₂', function () { setKey(2, !K2.isOn()); }, false, S.hand.busy), u.button('Put the jockey down', function () { putDown(); }, false, J.mode !== 'held' || S.hand.busy));
          u.h3('Resistance box R (now ' + st.R + ' Ω)' + (K2.isOn() ? ' · open K₂ to change it' : '')); rRow(u);
          u.h3('Observation table'); u.table();
          u.next('Next: result', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 sets (l₁, l₂) recorded, each with a different R.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          return [10, 5, 4].reduce(function (pr, R) { return pr.then(function () {
            return setKey(2, false).then(findNull).then(function () { recordL1(); return setR(R); }).then(function () { return setKey(2, true); })
              .then(findNull).then(function () { recordL2(); return setKey(2, false); }); }); }, Promise.resolve()); } },
    ],

    tick: function () {
      var d = divNow(); gal.set(Math.max(-31, Math.min(31, d)));
      hudL.set(J.mode === 'held' ? J.l.toFixed(1) + ' cm' : '—'); hudG.set(contact() ? (Math.abs(d) < 0.25 ? '0 div' : (Math.abs(d) >= 30 ? '>30' : Math.abs(d).toFixed(1)) + ' div ' + (d > 0 ? 'R' : 'L')) : '—');
      hudK.set((K1.isOn() ? 'in' : 'out') + ' · ' + (K2.isOn() ? 'in' : 'out') + ' · ' + st.R + ' Ω');
    },
  };
});
