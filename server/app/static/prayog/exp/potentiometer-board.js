/* Prayogshala studio module: the POTENTIOMETER BOARD (NCERT Class XII, Section A). One apparatus, two set-ups:
     potentiometer-compare-emf    - the balancing length of each of two cells, so E1/E2 = l1/l2,
     potential-drop-with-length   - the potential difference across different lengths of the same wire.
   A one-metre uniform manganin wire on a wooden board with thick copper strips and a metre scale, a knife-edge
   jockey the hand holds on the wire, a 6 V driver battery with a rheostat and a plug key, a two-way key with the two
   cells under test and a centre-zero galvanometer, or a voltmeter joined between end A and the jockey. Every
   reading comes from the circuit kernel (kernels.js, modified nodal analysis) on the lab's own net and params. */
HoolaStudio.define('potentiometer-board', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KC = HK.K.circuit, CFG = S.lab.cfg;
  var p = HK.paramsFor('circuit', S.lab.params);
  var ID = S.lab.id || '', MODE = /compare/.test(ID) ? 'emf' : 'drop';
  var FOM = p.FOM || 1.6e-5, FS = 30;
  var st = { traced: false, key: MODE === 'drop' ? false : false, cell: 0, Rh: p.Rh, locked: false };
  var J = { l: 30, mode: 'rest', pressed: false };

  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function r1(v) { return Math.round(v * 10) / 10; }
  function fnum(v, d) { return v.toFixed(d === undefined ? 1 : d); }

  // ---------------------------------------------------------------- the potentiometer board: wire, strips, metre scale
  var BZ = -0.4, TOP = 0.024, CU = 0.004, WZ = -0.34, WY = TOP + CU + 0.002, SZ = -0.3;
  var bench = new T.Group(); S.scene.add(bench);
  var bd = S.mesh(new T.BoxGeometry(1.22, TOP, 0.24), M.darkWood); bd.position.set(0, TOP / 2, BZ); bench.add(bd);
  var trim = S.mesh(new T.BoxGeometry(1.224, 0.004, 0.244), M.darkWood); trim.position.set(0, 0.002, BZ); bench.add(trim);
  [[-0.56, -0.48], [0.56, -0.48], [-0.56, -0.32], [0.56, -0.32]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.003, 16), M.rubber); ft.position.set(f[0], 0.0015, f[1]); bench.add(ft); });
  function strip(x0, x1, z0, z1) { var b = S.mesh(new T.BoxGeometry(x1 - x0, CU, z1 - z0), M.copper);
    b.position.set((x0 + x1) / 2, TOP + CU / 2, (z0 + z1) / 2); bench.add(b); return b; }
  strip(-0.55, -0.49, WZ - 0.02, WZ + 0.02); strip(0.49, 0.55, WZ - 0.02, WZ + 0.02);
  var wireMat = new T.MeshStandardMaterial({ color: 0xd9d3c4, roughness: 0.22, metalness: 1 });
  var mwire = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 1.0, 10), wireMat);
  mwire.rotation.z = Math.PI / 2; mwire.position.set(0, WY, WZ); bench.add(mwire);
  [-0.515, 0.515].forEach(function (x) { var c = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.005, 8), M.brass); c.position.set(x, TOP + CU + 0.002, WZ); bench.add(c); });
  var scaleTex = S.canvasTex(4096, 150, function (x, w, h) {
    x.drawImage(S.woodTex.image, 0, 0, w, h); x.fillStyle = 'rgba(255,248,230,.45)'; x.fillRect(0, 0, w, h);
    var k = (w - 48) / 1000; x.fillStyle = '#161616'; x.textAlign = 'center';
    for (var i = 0; i <= 1000; i++) { var xx = 24 + i * k, len = i % 100 === 0 ? 58 : i % 50 === 0 ? 44 : i % 10 === 0 ? 34 : 18;
      x.fillRect(xx - (i % 10 ? 0.7 : 1.2), 0, i % 10 ? 1.4 : 2.4, len);
      if (i % 10 === 0) { var big = i % 100 === 0; x.font = (big ? '700 40px' : '600 25px') + ' "Public Sans", sans-serif'; x.fillText(String(i / 10), xx, big ? 104 : 72); } }
    x.font = '600 22px "Public Sans", sans-serif'; x.fillStyle = '#6b4a14'; x.textAlign = 'left';
    x.fillText('POTENTIOMETER  ·  1 m uniform wire  ·  cm  ·  LC 1 mm', 60, 140); });
  var scl = S.mesh(new T.BoxGeometry(1.012, 0.004, 0.032), [M.wood, M.wood, new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.55 }), M.wood, M.wood, M.wood]);
  scl.position.set(0, TOP + 0.002, SZ); bench.add(scl);
  S.contact(1.32, 0.32, 0, BZ, 0.55);
  function endTag(t, x) { var l = S.label(t, { w: 0.028, ratio: 0.5, color: '#f3ead2' }); l.rotation.x = -Math.PI / 2;
    l.position.set(x, TOP + 0.0006, WZ + 0.028); S.scene.add(l); }
  endTag('A', -0.52); endTag('B', 0.52);
  var tA = post(-0.552, TOP + CU, WZ - 0.03), tB = post(0.552, TOP + CU, WZ - 0.03);

  // ---------------------------------------------------------------- driver battery, rheostat, key K1
  var drv = new T.Group(); S.scene.add(drv); drv.position.set(-0.46, 0, -0.68);
  var dbody = S.rounded(0.14, 0.09, 0.07, 0.006, M.bakelite); dbody.position.y = 0.035; drv.add(dbody);
  var dlid = S.rounded(0.146, 0.012, 0.076, 0.004, M.blackPlastic); dlid.position.y = 0.073; drv.add(dlid);
  [-0.04, 0, 0.04].forEach(function (vx) { var v = S.mesh(new T.CylinderGeometry(0.007, 0.007, 0.008, 16), new T.MeshStandardMaterial({ color: 0xd8862a, roughness: 0.5 })); v.position.set(vx, 0.082, 0); drv.add(v); });
  var dL = S.label('6 V  BATTERY', { w: 0.1, ratio: 0.16, color: '#c9ccd1' }); dL.position.set(0, 0.04, 0.0356); drv.add(dL);
  S.contact(0.2, 0.12, -0.46, -0.68, 0.55);
  var drvP = post(-0.42, 0.078, -0.68, 'red'), drvM = post(-0.5, 0.078, -0.68, 'black');
  var rheo = S.rheostat([0.02, 0, -0.68], 0.24);
  var rhL = post(-0.1, 0.062, -0.68), rhR = post(0.14, 0.062, -0.68);

  var ZAX = new T.Vector3(0, 0, 1);
  function makeKey(x, z, name) {
    var key = S.plugKey([x, 0, z]), plug = key.userData.plug;
    var tl = post(x - 0.02, 0.022, z - 0.008), tr = post(x + 0.02, 0.022, z - 0.008);
    var lb = S.label(name, { w: 0.022, ratio: 0.5, color: '#e9e4d6' }); lb.rotation.x = -Math.PI / 2;
    lb.position.set(x, 0.0165, z + 0.016); S.scene.add(lb);
    function pose(k) { return { x: 0.062 * (1 - k), y: 0.008 + 0.016 * k + 0.04 * Math.sin(Math.PI * k), z: 0.012 * (1 - k), rz: Math.PI / 2 * (1 - k) }; }
    function apply(k) { var q = pose(k); plug.position.set(q.x, q.y, q.z); plug.rotation.set(0, 0, q.rz); }
    function head(k) { var q = pose(k); return key.localToWorld(new T.Vector3(0, 0.013, 0).applyAxisAngle(ZAX, q.rz).add(new T.Vector3(q.x, q.y, q.z))); }
    apply(0);
    return { group: key, tl: tl, tr: tr, apply: apply, head: head, closed: false };
  }
  var key1 = makeKey(0.44, -0.66, 'K1');
  function toggleKey(k, on, label) {
    if (busy()) return Promise.resolve();
    var a = k.closed ? 1 : 0, b = on ? 1 : 0;
    if (a === b) return Promise.resolve();
    return S.hand.pinchMove(k.head(a), function (q) { return k.head(a + (b - a) * q); }, function (q) { k.apply(a + (b - a) * q); }, { ms: 850, mode: 'top' })
      .then(function () { k.apply(b); k.closed = !!on; S.click(1400, 0.04, 0.1);
        S.say(on ? label + ' closed: a steady current now flows along the wire.' : label + ' open: no current.'); S.render(); });
  }

  // ---------------------------------------------------------------- the jockey (a knife edge the hand holds on the wire)
  var jock = new T.Group(); S.scene.add(jock);
  var jt = S.mesh(new T.ConeGeometry(0.0034, 0.012, 4), M.brass); jt.rotation.x = Math.PI; jt.position.y = 0.006; jt.scale.z = 0.35; jock.add(jt);
  var jc = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.008, 16), M.brass); jc.position.y = 0.015; jock.add(jc);
  var jh = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 0.064, 20), M.bakelite); jh.position.y = 0.051; jock.add(jh);
  var jcap = S.mesh(new T.CylinderGeometry(0.0042, 0.0042, 0.008, 16), M.brass); jcap.position.y = 0.087; jock.add(jcap);
  var jShadow = S.contact(0.05, 0.05, 0, 0, 0.35);
  var REST = { pos: new T.Vector3(0.3, 0.0066, -0.18), rz: Math.PI / 2 };
  function onWire(l, lift) { return { pos: new T.Vector3(-0.5 + l / 100, WY + 0.0007 + (lift || 0), WZ), rz: 0 }; }
  function cur() { return { pos: jock.position.clone(), rz: jock.rotation.z }; }
  function grip(q) { return q.pos.clone().add(new T.Vector3(-0.05 * Math.sin(q.rz), 0.05 * Math.cos(q.rz), 0)); }
  function capOf(q) { return q.pos.clone().add(new T.Vector3(-0.091 * Math.sin(q.rz), 0.091 * Math.cos(q.rz), 0)); }
  function path(a, b, k, lift) {
    var up = function (q) { return { pos: q.pos.clone().add(new T.Vector3(0, lift, 0)), rz: q.rz }; }, A1 = up(a), B1 = up(b); A1.rz = b.rz;
    function mix(x, y, t) { return { pos: x.pos.clone().lerp(y.pos, t), rz: x.rz + (y.rz - x.rz) * t }; }
    return k < 0.3 ? mix(a, A1, k / 0.3) : k < 0.75 ? mix(A1, B1, (k - 0.3) / 0.45) : mix(B1, b, (k - 0.75) / 0.25);
  }
  var jLead = null, lastCap = '', meterTop = new T.Vector3(-0.42, 0.1, -0.02);
  function apply(q) {
    jock.position.copy(q.pos); jock.rotation.set(0, 0, q.rz);
    jShadow.position.set(q.pos.x - 0.045 * Math.sin(q.rz), 0.0009, q.pos.z); jShadow.scale.setScalar(q.rz > 0.7 ? 1.4 : 0.8);
    var c = capOf(q), key2 = c.x.toFixed(4) + c.y.toFixed(4) + c.z.toFixed(4); if (key2 === lastCap) return; lastCap = key2;
    var g = meterTop, pts = [[g.x, g.y, g.z], [g.x, g.y + 0.03, g.z], [g.x + 0.06, 0.15, g.z - 0.06], [(g.x + c.x) / 2, 0.19, (g.z + c.z) / 2 - 0.04], [c.x, Math.max(c.y + 0.04, 0.14), c.z - 0.03], [c.x, c.y, c.z]];
    if (!jLead) { jLead = S.wire(pts, 'black'); jLead.material.color.setHex(0x111113); jLead.material.roughness = 0.8; } else jLead.set(pts);
  }
  apply(REST);
  function moveJockey(l) {
    if (busy()) return Promise.resolve(false);
    if (!(l >= 1 && l <= 99)) { S.say('The jockey must touch the wire between 1 cm and 99 cm.'); return Promise.resolve(false); }
    l = r1(l);
    var a = cur(), b = onWire(l), held = J.mode === 'held';
    J.pressed = false; S.hand.busy = true;
    var pre = held ? Promise.resolve() : S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(grip(a), 'side', 700); }).then(function () { return S.hand.shape('pinch', 260); });
    var lift = held ? 0.018 : 0.07, ms = held ? 420 + Math.min(900, Math.abs(l - J.l) * 22) : 1050;
    return pre.then(function () { return S.hand.follow(function (k) { return grip(path(a, b, k, lift)); }, 'side', ms, function (k) { apply(path(a, b, k, lift)); }); })
      .then(function () { apply(b); J.l = l; J.mode = 'held'; J.pressed = true; S.hand.busy = false; S.click(700, 0.02, 0.05); S.render(); return true; },
        function (e) { S.hand.busy = false; throw e; });
  }
  function putDown() {
    if (J.mode !== 'held' || busy()) return Promise.resolve();
    var a = cur(); J.pressed = false; S.hand.busy = true;
    return S.hand.follow(function (k) { return grip(path(a, REST, k, 0.07)); }, 'side', 950, function (k) { apply(path(a, REST, k, 0.07)); })
      .then(function () { return S.hand.shape('relaxed', 220); }).then(function () { return S.hand.away(); })
      .then(function () { apply(REST); J.mode = 'rest'; S.hand.busy = false; S.render(); }, function (e) { S.hand.busy = false; throw e; });
  }

  // ---------------------------------------------------------------- the measuring side
  var gal = null, vm = null, twoWay = null, cells = [];
  if (MODE === 'emf') {
    gal = S.meter({ min: -FS, max: FS, zeroCentre: true, ticks: 6, unit: 'div', symbol: 'G', caption: 'GALVANOMETER 30–0–30', pos: [-0.42, 0, -0.04] });
    meterTop = wpt(gal, 0.035, 0.082, -0.03);
    // two-way key: three brass blocks on a bakelite base, one plug for each cell
    twoWay = (function () {
      var g = new T.Group(); S.scene.add(g); g.position.set(-0.04, 0, 0.04);
      var base = S.rounded(0.13, 0.05, 0.016, 0.004, M.bakelite); base.rotation.x = -Math.PI / 2; base.position.y = 0.008; g.add(base);
      [-0.045, 0, 0.045].forEach(function (bx) { var b = S.mesh(new T.BoxGeometry(0.02, 0.008, 0.03), M.brass); b.position.set(bx, 0.019, 0); g.add(b); });
      var lb = S.label('1        2', { w: 0.07, ratio: 0.16, color: '#e9e4d6' }); lb.rotation.x = -Math.PI / 2; lb.position.set(0, 0.0165, 0.02); g.add(lb);
      var plugs = [0, 1].map(function (i) {
        var pg = new T.Group(); g.add(pg);
        var pb = S.mesh(new T.CylinderGeometry(0.0045, 0.003, 0.016, 16), M.brass); pg.add(pb);
        var ph = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.012, 20), M.blackPlastic); ph.position.y = 0.013; pg.add(ph);
        return pg;
      });
      S.contact(0.19, 0.1, -0.04, 0.04, 0.45);
      function pose(i, k) { var home = i ? 0.0225 : -0.0225;
        return { x: home + (i ? 0.05 : -0.05) * (1 - k), y: 0.0245 * k + 0.012 * (1 - k) + 0.035 * Math.sin(Math.PI * k), z: 0.03 * (1 - k), rz: Math.PI / 2 * (1 - k) }; }
      function apply2(i, k) { var q = pose(i, k); plugs[i].position.set(q.x, q.y, q.z); plugs[i].rotation.set(0, 0, q.rz); }
      function head(i, k) { var q = pose(i, k); return g.localToWorld(new T.Vector3(0, 0.014, 0).applyAxisAngle(ZAX, q.rz).add(new T.Vector3(q.x, q.y, q.z))); }
      apply2(0, 0); apply2(1, 0);
      return { group: g, apply: apply2, head: head, tA: post(-0.095, 0.016, 0.02), t1: post(0.01, 0.016, 0.065), t2: post(0.04, 0.016, 0.065) };
    })();
    // the two cells under test: a Leclanche cell and a Daniell cell, in their glass jars
    cells = [{ x: 0.22, z: -0.02, name: 'Leclanché cell', emf: p.Ec, rod: 0x2a2a2c, liq: 0xcfd8c8 },
      { x: 0.22, z: 0.14, name: 'Daniell cell', emf: p.Ec2, rod: 0xc8764a, liq: 0x7fb6e0 }].map(function (c) {
      var jar = S.beaker(0.035, 0.08, [c.x, 0, c.z], c.liq, 0.6);
      var rod = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.11, 16), new T.MeshStandardMaterial({ color: c.rod, roughness: 0.4, metalness: 0.6 }));
      rod.position.set(c.x - 0.012, 0.062, c.z); S.scene.add(rod);
      var zn = S.mesh(new T.BoxGeometry(0.008, 0.09, 0.02), new T.MeshStandardMaterial({ color: 0xb9bec4, roughness: 0.5, metalness: 0.7 }));
      zn.position.set(c.x + 0.014, 0.055, c.z); S.scene.add(zn);
      var lb = S.label(c.name, { w: 0.08, ratio: 0.16, px: 512, color: '#2b2f36' }); lb.rotation.x = -Math.PI / 2;
      lb.position.set(c.x, 0.0012, c.z + 0.045); S.scene.add(lb);
      S.contact(0.1, 0.1, c.x, c.z, 0.4);
      return { jar: jar, pos: new T.Vector3(c.x, 0.11, c.z), name: c.name };
    });
    lead(tA.at, twoWay.tA.at, '#d9a520', [[-0.5, -0.24], [-0.3, -0.04], [-0.14, 0.02]]);
    lead(twoWay.t1.at, { x: cells[0].pos.x - 0.012, y: 0.11, z: cells[0].pos.z }, '#d9a520', [[0.08, 0.08]]);
    lead(twoWay.t2.at, { x: cells[1].pos.x - 0.012, y: 0.11, z: cells[1].pos.z }, '#d9a520', [[0.1, 0.14]]);
    lead({ x: cells[0].pos.x + 0.014, y: 0.1, z: cells[0].pos.z }, { x: cells[1].pos.x + 0.014, y: 0.1, z: cells[1].pos.z }, 'blue', [[0.3, 0.06]]);
    lead({ x: cells[1].pos.x + 0.014, y: 0.1, z: cells[1].pos.z }, wpt(gal, -0.035, 0.082, -0.03), 'blue', [[0.0, 0.2], [-0.3, 0.14]]);
  } else {
    vm = S.meter({ min: 0, max: 3, ticks: 6, unit: 'V', symbol: 'V', caption: 'VOLTMETER 0–3 V', pos: [-0.42, 0, -0.04] });
    meterTop = wpt(vm, 0.035, 0.082, -0.03);
    lead(tA.at, wpt(vm, -0.035, 0.082, -0.03), 'blue', [[-0.56, -0.26], [-0.5, -0.12]]);
  }

  lead(drvP.at, tA.at, 'red', [[-0.52, -0.6], [-0.56, -0.44]]);
  lead(tB.at, rhR.at, 'red', [[0.56, -0.5], [0.3, -0.62]]);
  lead(rhL.at, key1.tr.at, 'black', [[-0.06, -0.74], [0.3, -0.74]]);
  lead(key1.tl.at, drvM.at, 'black', [[0.3, -0.78], [-0.2, -0.78], [-0.48, -0.74]]);

  S.addApparatus('bench', bench, 'Potentiometer board', 'A uniform manganin wire one metre long, stretched between thick copper strips beside a metre scale.');
  S.addApparatus('jockey', jock, 'Jockey', 'A knife-edge contact. Touch the wire gently; never drag it along, because scraping changes the wire.');
  S.addApparatus('drv', drv, 'Driver battery (6 V)', 'Sends a steady current through the whole potentiometer wire. Its emf must be larger than any cell under test.');
  S.addApparatus('rheo', rheo, 'Rheostat', 'Sets the current in the wire, and so the potential gradient along it.');
  S.addApparatus('key', key1.group, 'Plug key K₁', 'Insert the plug only while taking a reading.');
  if (MODE === 'emf') {
    S.addApparatus('gal', gal, 'Galvanometer (30–0–30)', 'At the balance point it reads zero: no current flows from the cell under test.');
    S.addApparatus('twk', twoWay.group, 'Two-way key', 'One plug for each cell. Only one plug may be in at a time.');
    S.addApparatus('cells', cells[0].jar, 'Cells under test', 'A Leclanché cell and a Daniell cell, each in its own jar.');
  } else {
    S.addApparatus('vm', vm, 'Voltmeter (0–3 V)', 'Reads the potential difference between end A and the jockey. Least count 0.1 V, read to 0.02 V.');
  }
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ---------------------------------------------------------------- physics
  function live() {
    var o = { lj: J.l / 100, Rh: st.Rh };
    if (MODE === 'emf') { o.sw1 = st.cell === 1 ? 1 : 0; o.sw2 = st.cell === 2 ? 1 : 0; }
    else { o.key = st.key ? 1 : 0; }
    return o;
  }
  function solveAt(l, over) {
    var q = HK.assign(p, live()); q.lj = l / 100; if (over) q = HK.assign(q, over);
    return KC.view(KC.init(q, CFG), q, CFG);
  }
  function contact() { return J.mode === 'held' && J.pressed; }
  function running() { return MODE === 'emf' ? key1.closed : (key1.closed && st.key); }
  function iG(l) { if (!key1.closed || !st.cell) return 0; return solveAt(l).I_G; }
  function defl() { return contact() ? iG(J.l) / FOM : 0; }
  function deflText(d) {
    if (!st.cell) return 'no cell in the circuit';
    if (!contact()) return J.mode === 'held' ? 'jockey lifted' : 'jockey not on the wire';
    var a = Math.abs(d);
    if (a < 0.25) return 'no deflection';
    return (a >= FS ? 'off scale, ' : '') + Math.min(FS, a).toFixed(1) + ' div to the ' + (d > 0 ? 'right' : 'left');
  }
  function voltAt(l) { return key1.closed ? solveAt(l).V_VM : 0; }
  function vRead() { return contact() && key1.closed ? Math.round(voltAt(J.l) / 0.02) * 0.02 : 0; }
  function gradient() { return p.E0 * p.Rw / (st.Rh + p.Rw); }      // volts per metre, from the lab's own params
  var hudA = S.hudCard('Jockey at'), hudB = S.hudCard(MODE === 'emf' ? 'Galvanometer' : 'Voltmeter'), hudC = S.hudCard(MODE === 'emf' ? 'Cell in circuit' : 'Rheostat');

  // ---------------------------------------------------------------- human actions
  function trace() {
    st.traced = true; S.focus('bench');
    S.say(MODE === 'emf' ? 'The 6 V battery, the rheostat and key K1 drive a steady current from end A to end B of the wire. Each cell can be joined, through the two-way key and the galvanometer, between end A and the jockey.'
      : 'The 6 V battery, the rheostat and key K1 drive a steady current along the whole wire. The voltmeter reads from end A to wherever the jockey touches.');
    S.render();
  }
  function setKey1(on) { return putDown().then(function () { return toggleKey(key1, on, 'Key K1'); }).then(function () { if (MODE === 'drop') st.key = key1.closed; S.render(); }); }
  function setCell(n) {
    if (busy()) return Promise.resolve();
    if (n === st.cell) return Promise.resolve();
    var seq = Promise.resolve();
    if (st.cell) { var old = st.cell - 1; seq = S.hand.pinchMove(twoWay.head(old, 1), function (k) { return twoWay.head(old, 1 - k); }, function (k) { twoWay.apply(old, 1 - k); }, { ms: 700, mode: 'top' })
      .then(function () { twoWay.apply(old, 0); st.cell = 0; }); }
    if (!n) return seq.then(function () { S.say('Both plugs out: no cell is in the circuit.'); S.render(); });
    return seq.then(function () {
      var i = n - 1;
      return S.hand.pinchMove(twoWay.head(i, 0), function (k) { return twoWay.head(i, k); }, function (k) { twoWay.apply(i, k); }, { ms: 750, mode: 'top' })
        .then(function () { twoWay.apply(i, 1); st.cell = n; S.click(1400, 0.04, 0.1);
          S.say(cells[i].name + ' is now in the circuit.'); S.render(); });
    });
  }
  function setRheo(R) {
    if (busy()) return Promise.resolve();
    var lo = MODE === 'emf' ? 1 : 2, hi = MODE === 'emf' ? 10 : 12;
    if (!(R >= lo && R <= hi)) { S.say('The rheostat goes from ' + lo + ' to ' + hi + ' ohm.'); return Promise.resolve(); }
    if (st.locked) { S.say('Do not change the current once the readings have started: the potential gradient would change.'); return Promise.resolve(); }
    var R0 = st.Rh, sl = rheo.userData.slider;
    return S.hand.pinchMove(wpt(sl, 0, 0.016, 0), function (k) { var f = (R0 + (R - R0) * k - lo) / (hi - lo); return new T.Vector3(0.02 - 0.1 + 0.2 * f, 0.078, -0.68); },
      function (k) { st.Rh = R0 + (R - R0) * k; rheo.setFraction((st.Rh - lo) / (hi - lo)); }, { mode: 'side', ms: 700, reachMs: 650 })
      .then(function () { st.Rh = Math.round(R * 2) / 2; rheo.setFraction((st.Rh - lo) / (hi - lo));
        S.say('Rheostat at ' + fnum(st.Rh) + ' ohm: the potential gradient is now about ' + gradient().toFixed(2) + ' volt per metre.'); S.render(); });
  }
  rheo.setFraction((p.Rh - (MODE === 'emf' ? 1 : 2)) / (MODE === 'emf' ? 9 : 10));

  // the human way to find a balance point: touch near both ends, see the needle swing opposite ways, halve the gap
  function findNull() {
    var lo = 10, hi = 990, dlo, dhi;
    function probe(mm) { return moveJockey(mm / 10).then(function () { return iG(J.l); }); }
    return probe(lo).then(function (d) { dlo = d; return probe(hi); }).then(function (d) {
      dhi = d;
      if (dlo * dhi > 0) { S.say('The needle goes the same way at both ends: the balance point is not on the wire. Change the rheostat.'); return null; }
      function step() {
        if (hi - lo <= 1) return Promise.resolve();
        var mid = Math.round((lo + hi) / 2);
        return probe(mid).then(function (dm) { if (dm === 0) { lo = hi = mid; return; }
          if ((dm > 0) === (dlo > 0)) { lo = mid; dlo = dm; } else { hi = mid; dhi = dm; } return step(); });
      }
      return step().then(function () { return probe(Math.abs(dlo) <= Math.abs(dhi) ? lo : hi); });
    });
  }
  function bestHere() { var d0 = Math.abs(iG(J.l)), dm = Math.abs(iG(J.l - 0.1)), dp = Math.abs(iG(J.l + 0.1)); return d0 <= dm + 1e-15 && d0 <= dp + 1e-15; }

  function recordEmf() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!key1.closed) { S.say('Insert the plug key K1 first: no current flows along the wire.'); return false; }
    if (!st.cell) { S.say('Put the plug in for one of the cells first.'); return false; }
    if (!contact()) { S.say('Touch the jockey on the wire and watch the galvanometer.'); return false; }
    var d = defl();
    if (Math.abs(d) >= 0.25 && !bestHere()) { S.say('The galvanometer still shows ' + deflText(d) + '. Move the jockey until it reads zero.'); return false; }
    st.locked = true;
    S.addRow({ cell: st.cell, Rh: st.Rh, l: J.l });
    S.say('Written in your record book: cell ' + st.cell + ', balancing length ' + fnum(J.l) + ' cm.');
    return true;
  }
  function recordDrop() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!key1.closed) { S.say('Insert the plug key K1 first.'); return false; }
    if (!contact()) { S.say('Touch the jockey on the wire first.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.l - J.l) < 1; })) { S.say('You already have a reading near ' + fnum(J.l) + ' cm. Move the jockey further.'); return false; }
    st.locked = true;
    S.addRow({ l: J.l, v: vRead(), Rh: st.Rh });
    S.say('Written in your record book: l = ' + fnum(J.l) + ' cm, V = ' + vRead().toFixed(2) + ' V.');
    return true;
  }

  // ---------------------------------------------------------------- result
  function lens(n) { return S.rows.filter(function (r) { return r.cell === n; }).map(function (r) { return r.l; }); }
  function result(rows) {
    if (MODE === 'emf') {
      var l1 = lens(1), l2 = lens(2);
      if (!l1.length || !l2.length) return null;
      return { label: 'E₁ / E₂', value: S.fit.mean(l1) / S.fit.mean(l2), unit: '', digits: 3, truth: p.Ec / p.Ec2,
        note: 'Mean l₁ = ' + S.fit.mean(l1).toFixed(1) + ' cm, mean l₂ = ' + S.fit.mean(l2).toFixed(1) + ' cm. With E₁ = ' + p.Ec.toFixed(2) + ' V this makes E₂ = ' + (p.Ec * S.fit.mean(l2) / S.fit.mean(l1)).toFixed(3) + ' V.' };
    }
    var pts = rows.map(function (r) { return [r.l / 100, r.v]; }).filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); });
    if (pts.length < 3) return null;
    return { label: 'Potential gradient', value: S.fit.origin(pts), unit: 'V/m', digits: 3, truth: gradient(),
      note: 'Slope of the V against l graph. Along a uniform wire the drop is the same for every centimetre.' };
  }

  // ---------------------------------------------------------------- steps
  var stepsEmf = [
    { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
        u.h2('Set up the potentiometer');
        u.p('The driver battery drives a steady current from end A to end B. Each cell is joined through the two-way key and the galvanometer to the jockey.');
        u.task('1. Trace the circuit', st.traced, st.traced ? 'Driver circuit and cell circuit traced' : 'Follow the leads from the battery')
          .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
        u.task('2. Insert the plug key K₁', key1.closed, key1.closed ? 'K₁ closed: a steady current flows along the wire' : 'K₁ is open')
          .add(u.button(key1.closed ? 'K₁ is in' : 'Insert the plug in K₁', function () { setKey1(true); }, !key1.closed, key1.closed || S.hand.busy));
        var rr = { v: st.Rh };
        u.slider('Rheostat', 1, 10, 0.5, function () { return rr.v; }, function (v) { rr.v = v; }, 'Ω', 1);
        u.row(u.button('Move the rheostat', function () { setRheo(rr.v); }, false, S.hand.busy));
        u.note('The driver emf (6 V) must be larger than either cell, or there is no balance point on the wire.');
        u.next('Next: find the balancing lengths', st.traced && key1.closed);
      },
      ok: function () { return st.traced && key1.closed; },
      auto: function () { trace(); return setKey1(true); } },
    { id: 'balance', title: 'Balancing lengths', view: 'bench', render: function (u) {
        u.h2('Find the balancing length of each cell');
        u.p('Put the plug in for one cell only. Touch the jockey near each end first: the needle swings opposite ways. Close in until it reads zero, and record the length.');
        u.task('1. Choose the cell', st.cell > 0, st.cell ? cells[st.cell - 1].name + ' is in the circuit' : 'Both plugs are out')
          .add(u.row(u.button('Cell 1 (' + cells[0].name + ')', function () { setCell(1); }, st.cell === 1, S.hand.busy),
            u.button('Cell 2 (' + cells[1].name + ')', function () { setCell(2); }, st.cell === 2, S.hand.busy)));
        var sl = { v: J.l };
        u.slider('Jockey position from A', 1, 99, 0.1, function () { return sl.v; }, function (v) { sl.v = v; }, 'cm', 1);
        u.row(u.button('Touch the jockey here', function () { moveJockey(sl.v); }, true, S.hand.busy || !key1.closed),
          u.button('Find the balance point', function () {
            if (!st.cell) { S.say('Put the plug in for one cell first.'); return; } findNull(); }, false, S.hand.busy));
        u.row(u.button('−1 cm', function () { moveJockey(J.l - 1); }, false, S.hand.busy || J.mode !== 'held'),
          u.button('−1 mm', function () { moveJockey(J.l - 0.1); }, false, S.hand.busy || J.mode !== 'held'),
          u.button('+1 mm', function () { moveJockey(J.l + 0.1); }, false, S.hand.busy || J.mode !== 'held'),
          u.button('+1 cm', function () { moveJockey(J.l + 1); }, false, S.hand.busy || J.mode !== 'held'));
        u.live(function () { return (J.mode === 'held' ? 'Jockey at ' + fnum(J.l) + ' cm' : 'Jockey on the bench') + '  ·  Galvanometer: ' + deflText(defl()); });
        u.row(u.button('Record this balancing length', function () { recordEmf(); }, true, !contact()),
          u.button('Put the jockey down', function () { putDown(); }, false, J.mode !== 'held' || S.hand.busy));
        u.h3('Observation table'); u.table();
        u.note('Take at least two balancing lengths for each cell, changing the rheostat between the pairs.');
        if (lens(1).length < 2 || lens(2).length < 2) u.p('Cell 1: ' + lens(1).length + ' of 2 readings · cell 2: ' + lens(2).length + ' of 2.');
        u.next('Next: result', lens(1).length >= 2 && lens(2).length >= 2);
      },
      ok: function () { return lens(1).length >= 2 && lens(2).length >= 2; },
      auto: function () {
        function pair() { return setCell(1).then(findNull).then(function () { recordEmf(); })
          .then(function () { return setCell(2); }).then(findNull).then(function () { recordEmf(); }); }
        return pair().then(function () { st.locked = false; return setRheo(4); }).then(pair);
      } },
  ];

  var stepsDrop = [
    { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
        u.h2('Send a steady current along the wire');
        u.p('The battery, the rheostat and key K₁ are in series with the whole wire. The voltmeter reads from end A to the jockey.');
        u.task('1. Trace the circuit', st.traced, st.traced ? 'Series circuit traced' : 'Follow the leads from the battery')
          .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
        u.task('2. Insert the plug key K₁', key1.closed, key1.closed ? 'K₁ closed' : 'K₁ is open')
          .add(u.button(key1.closed ? 'K₁ is in' : 'Insert the plug in K₁', function () { setKey1(true); }, !key1.closed, key1.closed || S.hand.busy));
        var rr = { v: st.Rh };
        u.slider('Rheostat', 2, 12, 0.5, function () { return rr.v; }, function (v) { rr.v = v; }, 'Ω', 1);
        u.row(u.button('Move the rheostat', function () { setRheo(rr.v); }, false, S.hand.busy || st.locked));
        u.note('Once the readings start, the current must not be changed: the whole point is that one current gives one gradient.');
        u.next('Next: take the readings', st.traced && key1.closed);
      },
      ok: function () { return st.traced && key1.closed; },
      auto: function () { trace(); return setKey1(true); } },
    { id: 'read', title: 'Readings', view: 'bench', render: function (u) {
        u.h2('Read V for several lengths');
        u.p('Touch the jockey at 20, 35, 50, 65, 80 and 95 cm, and record the voltmeter reading each time.');
        var sl = { v: J.l };
        u.slider('Jockey position from A', 5, 99, 1, function () { return sl.v; }, function (v) { sl.v = v; }, 'cm', 0);
        u.row(u.button('Touch the jockey here', function () { moveJockey(sl.v); }, true, S.hand.busy || !key1.closed),
          u.button('Record this reading', function () { recordDrop(); }, false, !contact()),
          u.button('Put the jockey down', function () { putDown(); }, false, J.mode !== 'held' || S.hand.busy));
        u.live(function () { return (J.mode === 'held' ? 'Jockey at ' + fnum(J.l) + ' cm' : 'Jockey on the bench') + '  ·  Voltmeter ' + vRead().toFixed(2) + ' V'; });
        u.h3('Observation table'); u.table();
        if (S.rows.length < 5) u.p(S.rows.length + ' of at least 5 readings recorded.');
        u.next('Next: result', S.rows.length >= 5);
      },
      ok: function () { return S.rows.length >= 5; },
      auto: function () {
        return [20, 35, 50, 65, 80, 95].reduce(function (pr, l) {
          return pr.then(function () { return moveJockey(l); }).then(function () { recordDrop(); }); }, Promise.resolve());
      } },
  ];

  return {
    camera: { pos: [0.0, 0.92, 0.6], look: [0.0, 0.02, -0.34] },
    views: { bench: [[0.0, 0.92, 0.6], [0.0, 0.02, -0.34]], jockey: [[0.0, 0.5, 0.06], [0.0, 0.02, -0.36]],
      gal: [[-0.42, 0.3, 0.28], [-0.42, 0.06, -0.04]], vm: [[-0.42, 0.3, 0.28], [-0.42, 0.06, -0.04]],
      twk: [[-0.04, 0.26, 0.3], [-0.04, 0.02, 0.04]], cells: [[0.22, 0.3, 0.42], [0.22, 0.05, 0.06]],
      drv: [[-0.46, 0.34, -0.3], [-0.46, 0.05, -0.7]], rheo: [[0.02, 0.32, -0.3], [0.02, 0.05, -0.68]],
      key: [[0.44, 0.28, -0.3], [0.44, 0.02, -0.66]], book: [[0.66, 0.46, 0.44], [0.66, 0.0, -0.1]] },
    theory: MODE === 'emf' ? {
      principle: 'The driver battery sends a steady current through the whole potentiometer wire, so the potential falls uniformly along it. At the balance point the galvanometer reads zero: no current flows from the cell under test, so the length balances the cell\'s full emf, not its terminal voltage.',
      formula: 'E₁ / E₂ = l₁ / l₂',
      formulaNote: 'the potential gradient cancels, so it never has to be measured',
      more: ['Because both cells are balanced against the same wire carrying the same current, the potential gradient k is common to both: E₁ = k l₁ and E₂ = k l₂.',
        'The driver emf must be larger than either cell, or the balance point falls off the end of the wire. Changing the rheostat changes both lengths but not their ratio, which is why the reading is repeated at a second current.'],
      precautions: 'Only one plug of the two-way key may be in at a time. Touch the jockey gently and never drag it along the wire. Take the plugs out between readings so the cells are not run down.' } : {
      principle: 'A uniform wire carrying a steady current has the same resistance per centimetre everywhere, so the potential falls uniformly from one end to the other. The drop across a length l is therefore proportional to l.',
      formula: 'V = k l', formulaNote: 'k, the potential gradient, is the slope of the V against l graph, in volts per metre',
      more: ['The current is fixed by the battery and the rheostat: V = I R l / L. If the rheostat is moved during the experiment the gradient changes and the points no longer lie on one line.',
        'The potential gradient is what every potentiometer measurement rests on: a smaller current means a smaller gradient, and a longer length for the same potential difference.'],
      precautions: 'Keep the current steady once the readings begin, touch the jockey gently, and open the key between readings so the wire does not heat up.' },
    book: MODE === 'emf' ? { title: 'Expt. — Comparison of the emfs of two cells', at: [0.66, 0.12, -0.12],
      lines: ['Aim: to compare the emfs of two primary cells', 'with a potentiometer.',
        'Driver 6 V, wire 1 m, scale LC 0.1 cm', 'At balance: E = k l', 'E1 / E2 = l1 / l2',
        'Precautions: one plug at a time;', 'jockey touched gently.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Cell', get: function (r) { return r.cell; } },
        { label: 'Rheostat (Ω)', get: function (r) { return fnum(r.Rh); } },
        { label: 'Balancing length (cm)', get: function (r) { return fnum(r.l); } }] }
      : { title: 'Expt. — Potential drop along a wire', at: [0.66, 0.12, -0.12],
        lines: ['Aim: to study how the potential drop varies', 'with the length of a wire carrying a steady current.',
          'Driver 6 V, wire 1 m, scale LC 0.1 cm', 'Voltmeter 0–3 V, read to 0.02 V', 'V = k l, k = potential gradient'],
        columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
          { label: 'l (cm)', get: function (r) { return fnum(r.l); } },
          { label: 'V (V)', get: function (r) { return r.v.toFixed(2); } },
          { label: 'V/l (V/cm)', get: function (r) { return r.l ? (r.v / r.l).toFixed(4) : '—'; } }] },
    graph: MODE === 'emf' ? { x: function (r) { return r.cell; }, y: function (r) { return r.l; }, xlabel: 'Cell', ylabel: 'Balancing length (cm)', x0: 0, y0: 0 }
      : { x: function (r) { return r.l; }, y: function (r) { return r.v; }, xlabel: 'l (cm)', ylabel: 'V (V)', x0: 0, y0: 0,
        line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: result,
    tol: 0.02,
    resultNote: MODE === 'emf' ? 'The same ratio should come out at both rheostat settings: the gradient changes, the ratio does not.'
      : 'A straight line through the origin is the proof that the wire is uniform.',
    chips: MODE === 'emf' ? ['Why does no current flow at balance?', 'Why must the driver emf be larger?', 'Check my readings', 'Why change the rheostat?']
      : ['What is the potential gradient?', 'Why must the current stay the same?', 'Check my readings', 'Why does the line pass through the origin?'],
    viva: MODE === 'emf' ? [
      ['At the balance point the current from the cell under test is', ['Zero', 'The largest', 'Equal to the driver current'], 0,
        'That is why a potentiometer measures the emf and not the terminal voltage.'],
      ['Why is a potentiometer better than a voltmeter for measuring emf?', ['It draws no current at balance', 'It is cheaper', 'It is quicker'], 0,
        'A voltmeter always draws some current, so it reads the terminal voltage, which is less than the emf.']]
      : [['The graph of V against l for a uniform wire is', ['A straight line through the origin', 'A curve', 'A horizontal line'], 0, 'V = k l.'],
        ['If the rheostat is moved during the experiment', ['The gradient changes and the points no longer lie on one line', 'Nothing changes', 'The wire burns'], 0,
          'The gradient is proportional to the current in the wire.']],
    askState: function () {
      var o = { experiment: MODE === 'emf' ? 'comparing the emfs of two cells on a potentiometer' : 'potential drop along a wire carrying a steady current',
        key_K1_closed: key1.closed, jockey_cm: J.mode === 'held' ? J.l : null, jockey_touching_wire: contact(),
        rheostat_ohm: st.Rh, readings_taken: S.rows.length };
      if (MODE === 'emf') { o.cell_in_circuit = st.cell ? cells[st.cell - 1].name : 'none'; o.galvanometer = deflText(defl()); }
      else { o.voltmeter_V = vRead(); o.potential_gradient_V_per_m = +gradient().toFixed(3); }
      return o;
    },
    steps: MODE === 'emf' ? stepsEmf : stepsDrop,
    tick: function () {
      if (gal) gal.set(Math.max(-FS - 1, Math.min(FS + 1, defl())));
      if (vm) vm.set(contact() ? voltAt(J.l) : 0);
      hudA.set(J.mode === 'held' ? fnum(J.l) + ' cm' : '—');
      hudB.set(MODE === 'emf' ? (contact() && st.cell ? deflText(defl()) : '—') : (contact() ? vRead().toFixed(2) + ' V' : '—'));
      hudC.set(MODE === 'emf' ? (st.cell ? 'cell ' + st.cell : 'none') : fnum(st.Rh) + ' Ω');
    },
  };
});
