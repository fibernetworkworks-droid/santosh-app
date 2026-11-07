/* Prayogshala studio module: Meter bridge (NCERT Class XII) - the resistance of a given wire. A wooden meter bridge with a
   1 m manganin wire, thick L-shaped copper strips and a metre scale; a resistance box R in the left gap, the unknown coil
   S in the right gap, a zero-centre galvanometer from the centre strip to a knife-edge jockey, and a 2 V accumulator with
   a plug key. The galvanometer reads the circuit kernel (kernels.js, MNA) with the lab's own net (S.lab.cfg): the same
   numbers the server checks. The hidden unknown is S (Sx). */
HoolaStudio.define('meter-bridge', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.circuit, CFG = S.lab.cfg;
  var p = window.HoolaKernels.paramsFor('circuit', S.lab.params);
  var FOM = 20e-6;                        // galvanometer figure of merit: 20 µA per division (30-0-30 scale)
  var st = { traced: false, key: false, R: 0, target: 50 };
  var J = { l: 50, mode: 'rest', pressed: false };
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || '';   // the given wire, when a family variant names it

  // ---------- helpers (kept inside this module)
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]); var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }

  // ---------- the meter bridge: board, copper strips, 1 m wire, metre scale
  var BZ = -0.31, TOP = 0.025, CU = 0.004, WZ = -0.215, WY = TOP + CU + 0.002, SZ = -0.187;
  var bridge = new T.Group(); S.scene.add(bridge);
  var board = S.mesh(new T.BoxGeometry(1.2, TOP, 0.28), M.darkWood); board.position.set(0, TOP / 2, BZ); bridge.add(board);
  var trim = S.mesh(new T.BoxGeometry(1.204, 0.004, 0.284), M.darkWood); trim.position.set(0, 0.002, BZ); bridge.add(trim);
  [[-0.56, -0.43], [0.56, -0.43], [-0.56, -0.19], [0.56, -0.19]].forEach(function (f) { var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.003, 16), M.rubber); ft.position.set(f[0], 0.0015, f[1]); bridge.add(ft); });
  function strip(x0, x1, z0, z1) { var b = S.mesh(new T.BoxGeometry(x1 - x0, CU, z1 - z0), M.copper); b.position.set((x0 + x1) / 2, TOP + CU / 2, (z0 + z1) / 2); bridge.add(b); return b; }
  var SB = -0.385;
  strip(-0.53, -0.5, SB - 0.015, WZ + 0.012); strip(-0.53, -0.17, SB - 0.015, SB + 0.015);       // left L
  strip(0.5, 0.53, SB - 0.015, WZ + 0.012); strip(0.17, 0.53, SB - 0.015, SB + 0.015);           // right L
  strip(-0.11, 0.11, SB - 0.015, SB + 0.015);                                                      // centre strip
  var wireMat = new T.MeshStandardMaterial({ color: 0xd9d3c4, roughness: 0.22, metalness: 1 });
  var mwire = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 1.0, 8), wireMat); mwire.rotation.z = Math.PI / 2; mwire.position.set(0, WY, WZ); bridge.add(mwire);
  [-0.515, 0.515].forEach(function (x) { var c = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.004, 6), M.brass); c.position.set(x, TOP + CU + 0.002, WZ); bridge.add(c); });
  var scaleTex = S.canvasTex(4096, 150, function (x, w, h) {
    x.drawImage(S.woodTex.image, 0, 0, w, h); x.fillStyle = 'rgba(255,248,230,.45)'; x.fillRect(0, 0, w, h);
    var k = (w - 48) / 1000; x.fillStyle = '#161616'; x.textAlign = 'center';
    for (var i = 0; i <= 1000; i++) { var xx = 24 + i * k, len = i % 100 === 0 ? 58 : i % 50 === 0 ? 44 : i % 10 === 0 ? 34 : 18; x.fillRect(xx - (i % 10 ? 0.7 : 1.2), 0, i % 10 ? 1.4 : 2.4, len);
      if (i % 10 === 0) { var big = i % 100 === 0; x.font = (big ? '700 40px' : '600 25px') + ' "Public Sans", sans-serif'; x.fillText(String(i / 10), xx, big ? 104 : 72); } }
    x.font = '600 22px "Public Sans", sans-serif'; x.fillStyle = '#6b4a14'; x.textAlign = 'left'; x.fillText('METRE BRIDGE · cm · LC 1 mm', 60, 140); });
  var scl = S.mesh(new T.BoxGeometry(1.0 + 0.012, 0.004, 0.032), [M.wood, M.wood, new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.55 }), M.wood, M.wood, M.wood]);
  scl.position.set(0, TOP + 0.002, SZ); bridge.add(scl);
  S.contact(1.32, 0.4, 0, BZ, 0.55);
  var gapTag = function (t, x) { var l = S.label(t, { w: 0.03, ratio: 0.5, color: '#f3ead2' }); l.rotation.x = -Math.PI / 2; l.position.set(x, TOP + 0.0005, SB + 0.032); S.scene.add(l); };
  gapTag('R', -0.14); gapTag('S', 0.14); gapTag('A', -0.515 + 0.03); gapTag('C', 0.515 - 0.03);
  var Y0 = TOP + CU;
  var tLcell = post(-0.515, Y0, -0.3), tLgap = post(-0.19, Y0, SB), tM1 = post(-0.09, Y0, SB), tMg = post(0, Y0, SB), tM2 = post(0.09, Y0, SB),
    tRgap = post(0.19, Y0, SB), tRcell = post(0.515, Y0, -0.3);

  // ---------- 2 V lead accumulator + plug key
  var AC = [-0.64, -0.62];
  var acc = new T.Group(); S.scene.add(acc);
  var accBody = S.rounded(0.07, 0.1, 0.06, 0.006, M.bakelite); accBody.position.y = 0.05; acc.add(accBody);
  var accLid = S.rounded(0.076, 0.012, 0.066, 0.004, M.blackPlastic); accLid.position.y = 0.104; acc.add(accLid);
  var vent = S.mesh(new T.CylinderGeometry(0.007, 0.007, 0.008, 18), new T.MeshStandardMaterial({ color: 0xd8862a, roughness: 0.5 })); vent.position.set(0, 0.114, 0); acc.add(vent);
  var accL = S.label('2 V', { w: 0.04, ratio: 0.45, color: '#f2f2f2' }); accL.position.set(0, 0.06, 0.0306); acc.add(accL);
  var accL2 = S.label('ACCUMULATOR', { w: 0.055, ratio: 0.16, color: '#c9ccd1' }); accL2.position.set(0, 0.035, 0.0306); acc.add(accL2);
  acc.position.set(AC[0], 0, AC[1]); S.contact(0.12, 0.11, AC[0], AC[1], 0.55);
  var accP = post(AC[0] + 0.022, 0.11, AC[1], 'red'), accM = post(AC[0] - 0.022, 0.11, AC[1], 'black');

  var KEYP = [-0.6, -0.07];
  var key = S.plugKey([KEYP[0], 0, KEYP[1]]); var plug = key.userData.plug;
  var kL = post(KEYP[0] - 0.02, 0.022, KEYP[1] - 0.008), kR = post(KEYP[0] + 0.02, 0.022, KEYP[1] - 0.008);
  var ZAX = new T.Vector3(0, 0, 1);
  function kPose(k) { return { x: 0.062 * (1 - k), y: 0.008 + 0.016 * k + 0.04 * Math.sin(Math.PI * k), z: 0.012 * (1 - k), rz: Math.PI / 2 * (1 - k) }; }
  function kApply(k) { var q = kPose(k); plug.position.set(q.x, q.y, q.z); plug.rotation.set(0, 0, q.rz); }
  function kHead(k) { var q = kPose(k); return key.localToWorld(new T.Vector3(0, 0.013, 0).applyAxisAngle(ZAX, q.rz).add(new T.Vector3(q.x, q.y, q.z))); }
  kApply(0);

  // ---------- resistance box R (the hand pulls brass plugs out to add resistance)
  var RB = [-0.3, -0.6];
  var rb = S.resistanceBox([RB[0], 0, RB[1]]);
  var rbPlugs = rb.children.filter(function (c) { return c.isGroup; }), VALS = [1, 2, 2, 5, 10, 20, 20, 50], out = VALS.map(function () { return false; });
  var rbL = post(RB[0] - 0.072, 0.053, RB[1] - 0.026), rbR = post(RB[0] + 0.072, 0.053, RB[1] - 0.026);
  var XAX = new T.Vector3(1, 0, 0);
  function pPose(i, k) { var x = -0.063 + i * 0.018, a = { y: 0.058, z: 0 }, b = { y: 0.0065, z: 0.064 };
    return { x: x, y: a.y + (b.y - a.y) * k + 0.05 * Math.sin(Math.PI * k), z: a.z + (b.z - a.z) * k, rx: Math.PI / 2 * k }; }
  function pApply(i, k) { var q = pPose(i, k); rbPlugs[i].position.set(q.x, q.y, q.z); rbPlugs[i].rotation.set(q.rx, 0, 0); }
  function pHead(i, k) { var q = pPose(i, k); return rb.localToWorld(new T.Vector3(0, 0.012, 0).applyAxisAngle(XAX, q.rx).add(new T.Vector3(q.x, q.y, q.z))); }
  rbPlugs.forEach(function (pl, i) { pApply(i, 0); });
  function plan(R) { var left = R, o = VALS.map(function () { return false; }); for (var i = VALS.length - 1; i >= 0; i--) if (VALS[i] <= left) { o[i] = true; left -= VALS[i]; } return o; }
  function boxValue() { return VALS.reduce(function (s, v, i) { return s + (out[i] ? v : 0); }, 0); }

  // ---------- the unknown coil S on its own small board
  var CB = [0.14, -0.56], CL = 0.12;
  var coil = new T.Group(); S.scene.add(coil);
  var cbase = S.rounded(CL + 0.09, 0.08, 0.016, 0.006, M.wood); cbase.rotation.x = -Math.PI / 2; cbase.position.set(0, 0.008, 0); coil.add(cbase);
  [-1, 1].forEach(function (s) { var sp = S.rounded(0.014, 0.02, 0.022, 0.003, M.white); sp.position.set(s * (CL / 2 + 0.006), 0.026, 0); coil.add(sp); });
  var former = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, CL + 0.02, 28), M.white); former.rotation.z = Math.PI / 2; former.position.y = 0.034; coil.add(former);
  var hpts = [], turns = 20;
  for (var i = 0; i <= turns * 24; i++) { var t = i / (turns * 24), a = t * turns * Math.PI * 2; hpts.push(new T.Vector3(-CL / 2 + 0.006 + t * (CL - 0.012), 0.034 + 0.0095 * Math.cos(a), 0.0095 * Math.sin(a))); }
  var cw = new T.MeshStandardMaterial({ color: /nichrome/i.test(SAMPLE) ? 0xb4b2ae : /constantan|eureka/i.test(SAMPLE) ? 0xc9b49a : /manganin/i.test(SAMPLE) ? 0xb08f72 : 0xb7a48c, roughness: 0.28, metalness: 0.9 });
  coil.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3(hpts), turns * 24, 0.0009, 6, false), cw));
  var cT1x = -(CL / 2 + 0.03), cT2x = CL / 2 + 0.03;
  [[hpts[0], cT1x], [hpts[hpts.length - 1], cT2x]].forEach(function (e) { var s0 = e[0];
    coil.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3([s0.clone(), new T.Vector3(s0.x + Math.sign(e[1]) * 0.008, 0.03, s0.z + 0.004), new T.Vector3(e[1], 0.026, 0.002)]), 16, 0.0009, 6, false), cw)); });
  var ctag = SAMPLE ? S.label('S: ' + SAMPLE, { w: 0.15, ratio: Math.min(0.1, 2.4 / (SAMPLE.length + 3)), px: 1024, color: '#3a2a10' }) : S.label('S  (unknown)', { w: 0.06, ratio: 0.2, color: '#3a2a10' });
  ctag.rotation.x = -Math.PI / 2; ctag.position.set(0, 0.0165, 0.028); coil.add(ctag);
  coil.position.set(CB[0], 0, CB[1]); S.contact(CL + 0.16, 0.14, CB[0], CB[1], 0.5);
  var cT1 = post(CB[0] + cT1x, 0.016, CB[1] + 0.002), cT2 = post(CB[0] + cT2x, 0.016, CB[1] + 0.002);

  // ---------- galvanometer (zero-centre, 30-0-30)
  var gal = S.meter({ min: -30, max: 30, zeroCentre: true, ticks: 6, unit: 'G', symbol: 'G', caption: 'GALVANOMETER 30–0–30', pos: [0, 0, -0.7] });
  var gP = { at: wpt(gal, 0.035, 0.07, -0.03) }, gM = { at: wpt(gal, -0.035, 0.07, -0.03) };

  // ---------- jockey: brass knife-edge on a bakelite handle; the hand holds it on the wire, or it lies on the bench
  var jock = new T.Group(); S.scene.add(jock);
  var jt = S.mesh(new T.ConeGeometry(0.0034, 0.012, 4), M.brass); jt.rotation.x = Math.PI; jt.position.y = 0.006; jt.scale.z = 0.35; jock.add(jt);
  var jc = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.008, 16), M.brass); jc.position.y = 0.015; jock.add(jc);
  var jh = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 0.064, 20), M.bakelite); jh.position.y = 0.051; jock.add(jh);
  var jcap = S.mesh(new T.CylinderGeometry(0.0042, 0.0042, 0.008, 16), M.brass); jcap.position.y = 0.087; jock.add(jcap);
  var jShadow = S.contact(0.05, 0.05, 0, 0, 0.35);
  var REST = { pos: new T.Vector3(0.3, 0.0066, -0.115), rz: Math.PI / 2 };
  function onWire(l, lift) { return { pos: new T.Vector3(-0.5 + l / 100, WY + 0.0006 + (lift || 0), WZ), rz: 0 }; }
  function cur() { return { pos: jock.position.clone(), rz: jock.rotation.z }; }
  function grip(q) { return q.pos.clone().add(new T.Vector3(-0.05 * Math.sin(q.rz), 0.05 * Math.cos(q.rz), 0)); }
  function capOf(q) { return q.pos.clone().add(new T.Vector3(-0.091 * Math.sin(q.rz), 0.091 * Math.cos(q.rz), 0)); }
  function path(a, b, k, lift) {
    var up = function (q) { return { pos: q.pos.clone().add(new T.Vector3(0, lift, 0)), rz: q.rz }; }, A1 = up(a), B1 = up(b); A1.rz = b.rz;
    function mix(x, y, t) { return { pos: x.pos.clone().lerp(y.pos, t), rz: x.rz + (y.rz - x.rz) * t }; }
    return k < 0.3 ? mix(a, A1, k / 0.3) : k < 0.75 ? mix(A1, B1, (k - 0.3) / 0.45) : mix(B1, b, (k - 0.75) / 0.25);
  }
  var jLead = null, lastCap = '';
  function apply(q) { jock.position.copy(q.pos); jock.rotation.set(0, 0, q.rz);
    jShadow.position.set(q.pos.x - 0.045 * Math.sin(q.rz), 0.0009, q.pos.z); jShadow.scale.setScalar(q.rz > 0.7 ? 1.4 : 0.8);
    var c = capOf(q), key2 = c.x.toFixed(4) + c.y.toFixed(4) + c.z.toFixed(4); if (key2 === lastCap) return; lastCap = key2;
    var g = gP.at, pts = [[g.x, g.y, g.z], [g.x, g.y + 0.03, g.z], [g.x + 0.1, 0.1, g.z], [(g.x + 0.1) * 0.6 + c.x * 0.4, 0.13, -0.5], [c.x, Math.max(c.y + 0.03, 0.115), c.z - 0.04], [c.x, c.y, c.z]];
    if (!jLead) { jLead = S.wire(pts, 'black'); jLead.material.color.setHex(0x111113); jLead.material.roughness = 0.8; } else jLead.set(pts); }
  apply(REST);

  function moveJockey(l) {
    if (busy()) return Promise.resolve(false);
    if (!(l >= 1 && l <= 99)) { S.say('The jockey must touch the wire between 1 cm and 99 cm.'); return Promise.resolve(false); }
    l = Math.round(l * 10) / 10;
    var a = cur(), b = onWire(l), held = J.mode === 'held';
    J.pressed = false; S.hand.busy = true;
    var pre = held ? Promise.resolve() : S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(grip(a), 'side', 700); }).then(function () { return S.hand.shape('pinch', 260); });
    var lift = held ? 0.018 : 0.07, ms = held ? 450 + Math.min(900, Math.abs(l - J.l) * 25) : 1100;
    return pre.then(function () { return S.hand.follow(function (k) { return grip(path(a, b, k, lift)); }, 'side', ms, function (k) { apply(path(a, b, k, lift)); }); })
      .then(function () { apply(b); J.l = l; J.mode = 'held'; J.pressed = true; S.hand.busy = false; S.click(700, 0.02, 0.05); S.render(); return true; },
        function (e) { S.hand.busy = false; throw e; });
  }
  function putDown() {
    if (J.mode !== 'held') return Promise.resolve();
    if (busy()) return Promise.resolve();
    var a = cur(); J.pressed = false; S.hand.busy = true;
    return S.hand.follow(function (k) { return grip(path(a, REST, k, 0.07)); }, 'side', 1000, function (k) { apply(path(a, REST, k, 0.07)); })
      .then(function () { return S.hand.shape('relaxed', 220); }).then(function () { return S.hand.away(); })
      .then(function () { apply(REST); J.mode = 'rest'; S.hand.busy = false; S.render(); }, function (e) { S.hand.busy = false; throw e; });
  }

  // ---------- leads: accumulator -> key -> A ... C -> accumulator; R across gap 1, S across gap 2; G from B to the jockey
  lead(accP.at, kL.at, 'red', [[-0.66, -0.52], [-0.68, -0.3], [-0.64, -0.1]]);
  lead(kR.at, tLcell.at, 'red', [[-0.57, -0.12], [-0.61, -0.19], [-0.58, -0.26, 0.032]]);
  lead(accM.at, tRcell.at, 'black', [[-0.6, -0.53], [-0.45, -0.475], [0.0, -0.48], [0.6, -0.47], [0.63, -0.33]]);
  lead(rbL.at, tLgap.at, 'yellow', [[-0.4, -0.55], [-0.24, -0.47]]);
  lead(rbR.at, tM1.at, 'yellow', [[-0.2, -0.6], [-0.11, -0.47]]);
  lead(cT1.at, tM2.at, 'blue', [[0.06, -0.5]], 0.01);
  lead(cT2.at, tRgap.at, 'blue', [[0.22, -0.5]], 0.01);
  lead(gM.at, tMg.at, 'black', [[-0.04, -0.62], [-0.01, -0.47]]);

  S.addApparatus('bridge', bridge, 'Meter bridge', 'A 1 m manganin wire stretched along a metre scale, with thick copper strips that form two gaps for R and S.');
  S.addApparatus('jockey', jock, 'Jockey', 'A knife-edge contact. Touch the wire gently; dragging it along the wire scrapes it and changes its resistance.');
  S.addApparatus('gal', gal, 'Galvanometer (30–0–30)', 'Zero-centre: it shows which way current flows. At the null point it reads zero. About 20 µA per division.');
  S.addApparatus('rb', rb, 'Resistance box R', 'Pull out brass plugs to put known resistances in the left gap. Every plug left in shorts its coil.');
  S.addApparatus('coil', coil, SAMPLE ? 'Unknown resistance S: ' + SAMPLE : 'Unknown resistance S', 'The coil of wire whose resistance S we find, in the right gap.');
  S.addApparatus('acc', acc, 'Lead accumulator (2 V)', 'Drives a steady current through the bridge wire.');
  S.addApparatus('key', key, 'Plug key K', 'Insert the plug only while taking a reading; the wire heats up otherwise.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  S.scene.children.slice().forEach(function (o) { if (o.isMesh && o.material && o.material.isMeshBasicMaterial && o.material.transparent && Math.abs(o.position.x + 0.5) < 1e-6 && Math.abs(o.position.z - 0.08) < 1e-6) S.scene.remove(o); });

  // ---------- physics: the kernel with the lab's net
  function iGat(l) { if (!st.key) return 0; p.key = 1; p.Rk = Math.max(st.R, 1e-6); p.lj = l / 100; var v = K.view(K.init(p, CFG), p, CFG); return v.I_G; }
  function contact() { return st.key && J.mode === 'held' && J.pressed; }
  function divNow() { return contact() ? iGat(J.l) / FOM : 0; }
  function divText(d) { var a = Math.abs(d); if (!contact()) return J.mode === 'held' ? 'jockey lifted' : 'jockey not touching the wire';
    if (a < 0.25) return 'no deflection'; return (a >= 30 ? 'off scale, ' : '') + Math.min(30, a).toFixed(1) + ' div to the ' + (d > 0 ? 'right' : 'left'); }
  var hudR = S.hudCard('Resistance box R'), hudL = S.hudCard('Jockey at'), hudG = S.hudCard('Galvanometer');

  function setKey(on) {
    if (!!on === st.key) return Promise.resolve();
    if (busy()) return Promise.resolve();
    return putDown().then(function () {
      var a = st.key ? 1 : 0, b = on ? 1 : 0; if (!on) st.key = false;
      return S.hand.pinchMove(kHead(a), function (k) { return kHead(a + (b - a) * k); }, function (k) { kApply(a + (b - a) * k); }, { ms: 900, mode: 'top' })
        .then(function () { kApply(b); st.key = !!on; S.click(1400, 0.04, 0.1); S.say(on ? 'Key closed: the accumulator drives a current through the bridge wire.' : 'Key open: no current.'); S.render(); });
    });
  }
  function setR(R) {
    if (busy()) return Promise.resolve();
    if (!(R >= 1 && R <= 110)) { S.say('Choose R between 1 Ω and 110 Ω.'); return Promise.resolve(); }
    var want = plan(R), idx = [];
    want.forEach(function (w, i) { if (w !== out[i]) idx.push(i); });
    if (!idx.length) { st.R = R; return Promise.resolve(); }
    return putDown().then(function () {
      return idx.reduce(function (pr, i) { return pr.then(function () { var a = out[i] ? 1 : 0, b = want[i] ? 1 : 0;
        return S.hand.pinchMove(pHead(i, a), function (k) { return pHead(i, a + (b - a) * k); }, function (k) { pApply(i, a + (b - a) * k); }, { ms: 750, mode: 'top', reachMs: 600 })
          .then(function () { pApply(i, b); out[i] = want[i]; st.R = boxValue(); S.click(1100, 0.03, 0.06); S.render(); }); }); }, Promise.resolve());
    }).then(function () { st.R = boxValue(); S.say('R = ' + st.R + ' Ω in the left gap (plugs out: ' + VALS.filter(function (v, i) { return out[i]; }).join(' + ') + ' Ω).'); S.render(); });
  }
  function bestHere() { var d0 = Math.abs(iGat(J.l)), dm = Math.abs(iGat(J.l - 0.1)), dp = Math.abs(iGat(J.l + 0.1)); return d0 <= dm + 1e-15 && d0 <= dp + 1e-15; }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.key) { S.say('Insert the plug key first: no current flows.'); return false; }
    if (!(st.R > 0)) { S.say('R is 0 Ω: take a plug out of the resistance box first.'); return false; }
    if (!contact()) { S.say('Touch the jockey on the wire and watch the galvanometer first.'); return false; }
    var d = divNow();
    if (Math.abs(d) >= 0.25 && !bestHere()) { S.say('The galvanometer still shows ' + divText(d) + '. Move the jockey until it reads zero.'); return false; }
    if (J.l < 30 || J.l > 70) { S.say('The null point is at ' + J.l.toFixed(1) + ' cm, outside 30–70 cm. Change R so that it comes nearer the middle, where the error is least.'); return false; }
    if (S.rows.some(function (r) { return r.R === st.R; })) { S.say('You already have a reading with R = ' + st.R + ' Ω. Change R for the next one.'); return false; }
    if (S.rows.length >= 10) { S.say('Ten readings are plenty. Go on to the result.'); return false; }
    S.addRow({ R: st.R, l: J.l });
    S.say('Written in your record book: R = ' + st.R + ' Ω, null point l = ' + J.l.toFixed(1) + ' cm.');
    return true;
  }
  function findNull() {   // what a student does: touch at both ends, then halve the gap until the needle stays at zero (to 1 mm)
    var probe = function (mm) { return moveJockey(mm / 10).then(function () { return divNow(); }); };
    var lo = 50, hi = 950, dlo, dhi;
    return probe(lo).then(function (d) { dlo = d; return probe(hi); }).then(function (d) { dhi = d;
      if (dlo * dhi > 0) { S.say('Same deflection at both ends: check the connections.'); return null; }
      function step() { if (hi - lo <= 1) return Promise.resolve();
        var mid = Math.round((lo + hi) / 2); return probe(mid).then(function (dm) { if (dm === 0) { lo = hi = mid; return; } if ((dm > 0) === (dlo > 0)) { lo = mid; dlo = dm; } else { hi = mid; dhi = dm; } return step(); }); }
      return step().then(function () { return probe(Math.abs(dlo) <= Math.abs(dhi) ? lo : hi); }); });
  }
  function trace() { st.traced = true; S.focus('bridge'); S.say((SAMPLE ? 'The wire in the right gap is ' + SAMPLE + '. ' : '') + 'Accumulator, key and the bridge wire A to C form the main circuit. R is in the left gap, S in the right gap, and the galvanometer joins the centre strip to the jockey.'); S.render(); }
  var WIDE = !!S.lab.variant;   // a family variant's wire can be a few ohms or a few tens of ohms: offer the whole box
  function rButtons(u) { var opts = WIDE ? [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40] : [2, 3, 4, 5, 6, 8, 10, 12, 15];
    var row = u.row(); opts.forEach(function (v) { row.appendChild(u.button(v + ' Ω', function () { setR(v); }, st.R === v, S.hand.busy)); }); return row; }

  return {
    camera: { pos: [0.1, 1.3, 1.3], look: [0.1, 0.0, -0.36] },
    views: { bridge: [[0.0, 1.0, 0.85], [0.0, 0.0, -0.36]], jockey: [[0.02, 0.62, 0.42], [0.0, 0.0, -0.42]], gal: [[0.02, 0.32, -0.36], [0.0, 0.05, -0.7]],
      rb: [[-0.26, 0.32, -0.3], [-0.3, 0.04, -0.6]], coil: [[0.18, 0.3, -0.3], [0.14, 0.02, -0.56]], acc: [[-0.56, 0.36, -0.22], [-0.64, 0.05, -0.58]],
      key: [[-0.54, 0.3, 0.16], [-0.6, 0.02, -0.07]], setup: [[-0.3, 0.95, 0.7], [-0.3, 0.0, -0.36]], book: [[0.6, 0.44, 0.52], [0.66, 0.0, 0.08]] },
    theory: { principle: 'A meter bridge is a Wheatstone bridge. The two parts of the uniform wire, l and (100 − l), act as two arms; R and S are the other two. At the null point no current flows through the galvanometer.',
      formula: 'R / S = l / (100 − l)', formulaNote: 'so S = R (100 − l) / l · l in cm, measured from end A',
      more: ['Because the wire is uniform, the resistance of each part is proportional to its length. The bridge is most sensitive when the null point lies near the middle of the wire (30–70 cm).'],
      precautions: 'Keep all connections tight and the copper strips clean. Touch the jockey gently; never slide it along the wire while pressing. Insert the key only while taking a reading. Choose R so the null point is between 30 cm and 70 cm.' },
    book: { title: 'Expt. — Meter bridge', at: [0.66, 0.08, -0.1],
      lines: ['Aim: to find the resistance S of a given wire.'].concat(SAMPLE ? ['Given wire: ' + SAMPLE] : []).concat(['Wire: 1 m manganin, scale LC 0.1 cm', 'R / S = l / (100 − l)', 'S = R (100 − l) / l', 'Precautions: null point 30–70 cm,', 'jockey touched gently.']),
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'R (Ω)', get: function (r) { return r.R; } }, { label: 'l (cm)', get: function (r) { return r.l.toFixed(1); } },
        { label: '100−l', get: function (r) { return (100 - r.l).toFixed(1); } }, { label: 'S (Ω)', get: function (r) { return (r.R * (100 - r.l) / r.l).toFixed(2); } }] },
    graph: { x: function (r) { return r.l / (100 - r.l); }, y: function (r) { return r.R; }, xlabel: 'l / (100 − l)', ylabel: 'R (Ω)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) { if (rows.length < 2) return null; var v = S.fit.mean(rows.map(function (r) { return r.R * (100 - r.l) / r.l; }));
      return { label: 'S', value: v, unit: 'Ω', digits: 2, truth: p.Sx, note: 'Mean of S = R(100 − l)/l. The graph of R against l/(100 − l) is a straight line of slope S.' }; },
    tol: 0.02,
    chips: ['What is the null point?', 'Why keep the null point near the middle?', 'Why must the jockey not slide on the wire?', 'Check my readings', 'What is end error?'],
    viva: [['Why is the meter bridge wire made of manganin?', ['Its resistance hardly changes with temperature', 'It is a very good conductor', 'It is cheap and soft'], 0, 'Manganin has a very low temperature coefficient of resistance and a high resistivity.'],
      ['If R and S are interchanged, the null point', ['Moves to (100 − l)', 'Stays at l', 'Disappears'], 0, 'The ratio is reversed, so the balance length from A becomes 100 − l.']],
    askState: function () { return { key_closed: st.key, resistance_box_R_ohm: st.R, jockey_cm: J.mode === 'held' ? J.l : null, jockey_touching_wire: contact(),
      galvanometer_div: +divNow().toFixed(1), galvanometer: divText(divNow()), given_wire: SAMPLE || 'unknown coil S', readings_taken: S.rows.length }; },

    steps: [
      { id: 'setup', title: 'Set up', view: 'setup', render: function (u) {
          u.h2('Set up the bridge');
          u.task('1. Trace the circuit', st.traced, st.traced ? 'Main circuit through the wire; R left gap, S right gap, G to the jockey' : 'Follow the leads from the accumulator')
            .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
          var t2 = u.task('2. Take a resistance out of the box', st.R > 0, st.R > 0 ? 'R = ' + st.R + ' Ω' : 'All plugs are in: R = 0 Ω');
          var opts = WIDE ? [1, 2, 4, 6, 10, 15, 20] : [2, 3, 4, 5, 6, 8, 10]; var row = document.createElement('div'); row.className = 'row';
          opts.forEach(function (v) { row.appendChild(u.button(v + ' Ω', function () { setR(v); }, st.R === v, S.hand.busy)); }); t2.add(row);
          u.task('3. Insert the plug key', st.key, st.key ? 'Key closed' : 'Key open').add(u.button(st.key ? 'Key is in' : 'Insert the plug', function () {
            if (!(st.R > 0)) { S.say('Take a plug out of the resistance box first.'); return; } setKey(true); }, true, st.key || S.hand.busy));
          u.note(SAMPLE ? 'Start with R about equal to the expected S (work it out roughly from the wire\'s length and gauge, or try a value and see where the null point falls), so the null point comes near the middle of the wire.'
            : 'Start with R about equal to the expected S (a few ohms), so the null point falls near the middle of the wire.');
          u.next('Next: find the null point', st.traced && st.R > 0 && st.key);
        },
        ok: function () { return st.traced && st.R > 0 && st.key; },
        auto: function () { trace(); return setR(4).then(function () { return setKey(true); }); } },
      { id: 'null', title: 'Null point', view: 'jockey', render: function (u) {
          u.h2('Find the null point');
          u.p('Let the hand touch the jockey on the wire and watch the galvanometer. Touch near both ends first: the needle swings opposite ways. Then close in until it reads zero, and record l from end A.');
          u.slider('Jockey position from A', 1, 99, 0.1, function () { return st.target; }, function (v) { st.target = v; }, 'cm', 1);
          u.row(u.button('Touch the jockey here', function () { moveJockey(st.target); }, true, S.hand.busy || !st.key));
          u.row(u.button('−1 cm', function () { moveJockey(J.l - 1); }, false, S.hand.busy || J.mode !== 'held'), u.button('−1 mm', function () { moveJockey(J.l - 0.1); }, false, S.hand.busy || J.mode !== 'held'),
            u.button('+1 mm', function () { moveJockey(J.l + 0.1); }, false, S.hand.busy || J.mode !== 'held'), u.button('+1 cm', function () { moveJockey(J.l + 1); }, false, S.hand.busy || J.mode !== 'held'));
          u.live(function () { return (J.mode === 'held' ? 'Jockey at ' + J.l.toFixed(1) + ' cm' : 'Jockey on the bench') + ' · Galvanometer: ' + divText(divNow()); });
          u.row(u.button('Record the null point', function () { record(); }, true, !contact()), u.button('Put the jockey down', function () { putDown(); }, false, J.mode !== 'held' || S.hand.busy),
            u.button(st.key ? 'Take the key out' : 'Insert the key', function () { setKey(!st.key); }, false, S.hand.busy));
          u.h3('Resistance box R (now ' + st.R + ' Ω)'); rButtons(u);
          u.note('Keep the null point between 30 and 70 cm. Take at least 3 readings with different R.');
          u.h3('Observation table'); u.table();
          u.next('Next: result', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 readings recorded.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          function one(R) { return setR(R).then(function () { return st.key ? null : setKey(true); }).then(findNull).then(function () { record(); }); }
          // what a student does: a first try with R = 4 Ω, then R values chosen so the null point stays in 30-70 cm
          return one(4).then(function () {
            var l0 = J.l, est = 4 * (100 - l0) / l0, inMid = function (R) { var l = 100 * R / (R + est); return l >= 31 && l <= 69; };
            var list = [3, 5, 6, 8];
            if (!list.every(inMid) || !inMid(4)) {
              list = []; [1, 0.8, 1.25, 0.65, 1.5, 0.55, 1.8].forEach(function (f) { var R = Math.max(1, Math.min(110, Math.round(est * f)));
                if (inMid(R) && list.indexOf(R) < 0 && !S.rows.some(function (r) { return r.R === R; })) list.push(R); });
              list = list.slice(0, 4);
            }
            return list.reduce(function (pr, R) { return pr.then(function () { return one(R); }); }, Promise.resolve()); }); } },
    ],

    tick: function () {
      var d = divNow(); gal.set(Math.max(-31, Math.min(31, d)));
      hudR.set(st.R + ' Ω'); hudL.set(J.mode === 'held' ? J.l.toFixed(1) + ' cm' : '—'); hudG.set(contact() ? (Math.abs(d) < 0.25 ? '0 div' : (Math.abs(d) >= 30 ? '>30' : Math.abs(d).toFixed(1)) + ' div ' + (d > 0 ? 'R' : 'L')) : '—');
    },
  };
});
