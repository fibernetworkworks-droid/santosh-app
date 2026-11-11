/* Prayogshala studio module: METRE BRIDGE, LAWS OF COMBINATION (NCERT Class XII, Section A).
   A wooden metre bridge with a 1 m manganin wire, thick copper strips and a metre scale; a four-dial resistance box
   in the left gap, and in the right gap a combination board carrying two coils R1 and R2 with three link keys, so
   that the gap can hold R1 alone, R2 alone, the two in series or the two in parallel. The galvanometer reads the
   circuit kernel (kernels.js, modified nodal analysis) on the lab's own net: the same numbers the server checks. */
HoolaStudio.define('bridge-combination', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KC = HK.K.circuit, CFG = S.lab.cfg;
  var p = HK.paramsFor('circuit', S.lab.params);
  var FOM = 20e-6;                                     // galvanometer: 20 µA per division (30-0-30 scale)
  var MODES = [{ k: 'r1', name: 'R₁ alone', keys: [1, 0, 0] }, { k: 'r2', name: 'R₂ alone', keys: [0, 1, 0] },
    { k: 'ser', name: 'R₁ and R₂ in series', keys: [0, 0, 1] }, { k: 'par', name: 'R₁ and R₂ in parallel', keys: [1, 1, 0] }];
  var st = { traced: false, key: false, mode: 'r1', R: 0 };
  var J = { l: 50, mode: 'rest', pressed: false };

  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function r1f(v) { return Math.round(v * 10) / 10; }
  function fnum(v, d) { return v.toFixed(d === undefined ? 1 : d); }

  // ---------------------------------------------------------------- the metre bridge
  var BZ = -0.4, TOP = 0.025, CU = 0.004, WZ = -0.32, WY = TOP + CU + 0.002, SZ = -0.28, SB = -0.47;
  var bridge = new T.Group(); S.scene.add(bridge);
  var bd = S.mesh(new T.BoxGeometry(1.22, TOP, 0.28), M.darkWood); bd.position.set(0, TOP / 2, BZ); bridge.add(bd);
  var trim = S.mesh(new T.BoxGeometry(1.224, 0.004, 0.284), M.darkWood); trim.position.set(0, 0.002, BZ); bridge.add(trim);
  [[-0.57, -0.52], [0.57, -0.52], [-0.57, -0.28], [0.57, -0.28]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.003, 16), M.rubber); ft.position.set(f[0], 0.0015, f[1]); bridge.add(ft); });
  function strip(x0, x1, z0, z1) { var b = S.mesh(new T.BoxGeometry(x1 - x0, CU, z1 - z0), M.copper);
    b.position.set((x0 + x1) / 2, TOP + CU / 2, (z0 + z1) / 2); bridge.add(b); return b; }
  strip(-0.54, -0.5, SB - 0.015, WZ + 0.012); strip(-0.54, -0.18, SB - 0.015, SB + 0.015);
  strip(0.5, 0.54, SB - 0.015, WZ + 0.012); strip(0.18, 0.54, SB - 0.015, SB + 0.015);
  strip(-0.12, 0.12, SB - 0.015, SB + 0.015);
  var wireMat = new T.MeshStandardMaterial({ color: 0xd9d3c4, roughness: 0.22, metalness: 1 });
  var mwire = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 1.0, 10), wireMat);
  mwire.rotation.z = Math.PI / 2; mwire.position.set(0, WY, WZ); bridge.add(mwire);
  [-0.515, 0.515].forEach(function (x) { var c = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.005, 8), M.brass); c.position.set(x, TOP + CU + 0.002, WZ); bridge.add(c); });
  var scaleTex = S.canvasTex(4096, 150, function (x, w, h) {
    x.drawImage(S.woodTex.image, 0, 0, w, h); x.fillStyle = 'rgba(255,248,230,.45)'; x.fillRect(0, 0, w, h);
    var k = (w - 48) / 1000; x.fillStyle = '#161616'; x.textAlign = 'center';
    for (var i = 0; i <= 1000; i++) { var xx = 24 + i * k, len = i % 100 === 0 ? 58 : i % 50 === 0 ? 44 : i % 10 === 0 ? 34 : 18;
      x.fillRect(xx - (i % 10 ? 0.7 : 1.2), 0, i % 10 ? 1.4 : 2.4, len);
      if (i % 10 === 0) { var big = i % 100 === 0; x.font = (big ? '700 40px' : '600 25px') + ' "Public Sans", sans-serif'; x.fillText(String(i / 10), xx, big ? 104 : 72); } }
    x.font = '600 22px "Public Sans", sans-serif'; x.fillStyle = '#6b4a14'; x.textAlign = 'left';
    x.fillText('METRE BRIDGE · cm · LC 1 mm', 60, 140); });
  var scl = S.mesh(new T.BoxGeometry(1.012, 0.004, 0.032), [M.wood, M.wood, new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.55 }), M.wood, M.wood, M.wood]);
  scl.position.set(0, TOP + 0.002, SZ); bridge.add(scl);
  S.contact(1.34, 0.36, 0, BZ, 0.55);
  function tag(t, x, z) { var l = S.label(t, { w: 0.028, ratio: 0.5, color: '#f3ead2' }); l.rotation.x = -Math.PI / 2;
    l.position.set(x, TOP + 0.0006, z); S.scene.add(l); }
  tag('R', -0.15, SB + 0.032); tag('X', 0.15, SB + 0.032); tag('A', -0.49, SB + 0.032); tag('C', 0.49, SB + 0.032);
  var Y0 = TOP + CU;
  var tLcell = post(-0.52, Y0, SB), tLgap = post(-0.2, Y0, SB), tM1 = post(-0.1, Y0, SB), tMg = post(0, Y0, SB),
    tM2 = post(0.1, Y0, SB), tRgap = post(0.2, Y0, SB), tRcell = post(0.52, Y0, SB);

  // ---------------------------------------------------------------- jockey
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
  var jLead = null, lastCap = '', galTop = new T.Vector3(-0.3, 0.1, 0.0);
  function apply(q) {
    jock.position.copy(q.pos); jock.rotation.set(0, 0, q.rz);
    jShadow.position.set(q.pos.x - 0.045 * Math.sin(q.rz), 0.0009, q.pos.z); jShadow.scale.setScalar(q.rz > 0.7 ? 1.4 : 0.8);
    var c = capOf(q), key2 = c.x.toFixed(4) + c.y.toFixed(4) + c.z.toFixed(4); if (key2 === lastCap) return; lastCap = key2;
    var g = galTop, pts = [[g.x, g.y, g.z], [g.x, g.y + 0.03, g.z], [g.x + 0.08, 0.16, g.z - 0.08], [(g.x + c.x) / 2, 0.2, (g.z + c.z) / 2 - 0.04], [c.x, Math.max(c.y + 0.04, 0.15), c.z - 0.03], [c.x, c.y, c.z]];
    if (!jLead) { jLead = S.wire(pts, 'black'); jLead.material.color.setHex(0x111113); jLead.material.roughness = 0.8; } else jLead.set(pts);
  }
  apply(REST);
  function moveJockey(l) {
    if (busy()) return Promise.resolve(false);
    if (!(l >= 1 && l <= 99)) { S.say('The jockey must touch the wire between 1 cm and 99 cm.'); return Promise.resolve(false); }
    l = r1f(l);
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

  // ---------------------------------------------------------------- four-dial resistance box in the left gap
  function decadeBox(x, z, muls, title) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z);
    var n = muls.length, W = 0.06 + n * 0.055, D = 0.13, H = 0.052;
    var body = S.rounded(W, D, H, 0.006, M.darkWood); body.rotation.x = -Math.PI / 2; body.position.y = H / 2; g.add(body);
    var dx = muls.map(function (m, i) { return -(n - 1) * 0.055 / 2 + i * 0.055; });
    var PW = W - 0.008, PD = D - 0.008;
    var tex = S.canvasTex(1400, Math.round(1400 * PD / PW), function (c, w, h) {
      var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (v / PD + 0.5) * h; }, k = w / PW;
      c.fillStyle = '#171a1f'; c.fillRect(0, 0, w, h);
      c.strokeStyle = 'rgba(255,255,255,.14)'; c.lineWidth = 3; c.strokeRect(10, 10, w - 20, h - 20);
      c.fillStyle = '#eceadf'; c.font = '700 ' + Math.round(k * 0.009) + 'px "Public Sans", sans-serif'; c.textAlign = 'left';
      c.fillText(title, 26, Math.round(k * 0.014));
      muls.forEach(function (m, i) {
        var cx = X(dx[i]), cy = Y(0.006), R = 0.027 * k;
        c.strokeStyle = '#8b9099'; c.lineWidth = 2; c.beginPath(); c.arc(cx, cy, R * 0.72, 0, Math.PI * 2); c.stroke();
        c.textAlign = 'center'; c.fillStyle = '#eceadf'; c.font = '600 ' + Math.round(k * 0.0075) + 'px "Public Sans", sans-serif';
        for (var d = 0; d < 10; d++) { var a = d * Math.PI / 5; c.fillText(String(d), cx + Math.sin(a) * R, cy + Math.cos(a) * R + k * 0.0026); }
        c.fillStyle = '#f0c36b'; c.font = '700 ' + Math.round(k * 0.007) + 'px "Public Sans", sans-serif';
        c.fillText('x ' + m, cx, Y(-0.05));
      });
    });
    var panel = new T.Mesh(new T.PlaneGeometry(PW, PD), new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }));
    panel.rotation.x = -Math.PI / 2; panel.position.y = H + 0.0006; g.add(panel);
    var knurl = S.canvasTex(256, 32, function (c, w, h) { c.fillStyle = '#15161a'; c.fillRect(0, 0, w, h); c.fillStyle = '#3b3e45'; for (var i = 0; i < w; i += 9) c.fillRect(i, 0, 3, h); });
    var dials = muls.map(function (m, i) {
      var d = new T.Group(); d.position.set(dx[i], H + 0.001, 0.006); g.add(d);
      var kb = S.mesh(new T.CylinderGeometry(0.0165, 0.018, 0.013, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.42 })); kb.position.y = 0.0065; d.add(kb);
      var cap2 = S.mesh(new T.CylinderGeometry(0.0125, 0.0125, 0.0015, 36), M.chrome); cap2.position.y = 0.0138; d.add(cap2);
      var ptr = S.mesh(new T.BoxGeometry(0.0022, 0.0012, 0.015), M.white, false); ptr.position.set(0, 0.0146, 0.0085); d.add(ptr);
      return { g: d, mul: m, digit: 0, top: new T.Vector3(x + dx[i], H + 0.016, z + 0.006) };
    });
    var tL = post(x - W / 2 + 0.014, H, z - D / 2 + 0.012), tR = post(x + W / 2 - 0.014, H, z - D / 2 + 0.012);
    S.contact(W + 0.06, D + 0.06, x, z, 0.5);
    return { group: g, dials: dials, tL: tL, tR: tR, muls: muls,
      value: function () { var v = 0; dials.forEach(function (d) { v += d.digit * d.mul; }); return v; },
      max: function () { var v = 0; dials.forEach(function (d) { v += 9 * d.mul; }); return v; },
      look: function () { dials.forEach(function (d) { d.g.rotation.y = d.digit * Math.PI / 5; }); } };
  }
  var rBox = decadeBox(-0.34, -0.68, [1000, 100, 10, 1], 'RESISTANCE BOX  R');
  function setBox(value) {
    if (busy()) return Promise.resolve(false);
    if (!(value >= 0 && value <= rBox.max())) { S.say('This box goes from 0 to ' + rBox.max() + ' ohms only.'); return Promise.resolve(false); }
    var left = Math.round(value), want = [];
    rBox.muls.forEach(function (m) { var d = Math.max(0, Math.min(9, Math.floor(left / m + 1e-9))); want.push(d); left -= d * m; });
    var jobs = [];
    want.forEach(function (d, i) { if (rBox.dials[i].digit !== d) jobs.push([i, d]); });
    return putDown().then(function () {
      return jobs.reduce(function (pr, j) {
        return pr.then(function () {
          var dl = rBox.dials[j[0]], a = dl.digit, b = j[1];
          return S.hand.pinchMove(dl.top, function () { return dl.top; }, function (k) { dl.digit = a + (b - a) * k; rBox.look(); },
            { mode: 'top', ms: 420 + 60 * Math.abs(b - a), reachMs: 520 })
            .then(function () { dl.digit = b; rBox.look(); S.click(1200, 0.02, 0.05); });
        });
      }, Promise.resolve());
    }).then(function () { st.R = rBox.value(); S.say('Resistance box set to ' + st.R + ' ohm in the left gap.'); S.render(); return true; });
  }

  // ---------------------------------------------------------------- the combination board: two coils and three link keys
  var CB = [0.3, -0.68];
  var comb = new T.Group(); S.scene.add(comb); comb.position.set(CB[0], 0, CB[1]);
  var cbase = S.rounded(0.34, 0.17, 0.016, 0.005, M.wood); cbase.rotation.x = -Math.PI / 2; cbase.position.y = 0.008; comb.add(cbase);
  function coil(cx, cz, label, tint) {
    var g = new T.Group(); comb.add(g);
    var former = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.08, 20), M.white); former.rotation.z = Math.PI / 2; former.position.set(cx, 0.034, cz); g.add(former);
    var pts = [], turns = 16;
    for (var i = 0; i <= turns * 20; i++) { var t = i / (turns * 20), a = t * turns * Math.PI * 2;
      pts.push(new T.Vector3(cx - 0.034 + t * 0.068, 0.034 + 0.009 * Math.cos(a), cz + 0.009 * Math.sin(a))); }
    g.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts), turns * 20, 0.0009, 6, false),
      new T.MeshStandardMaterial({ color: tint, roughness: 0.28, metalness: 0.9 })));
    [-1, 1].forEach(function (s) { var sp = S.rounded(0.012, 0.018, 0.02, 0.003, M.white); sp.position.set(cx + s * 0.046, 0.026, cz); g.add(sp); });
    var lb = S.label(label, { w: 0.02, ratio: 0.5, color: '#3a2a10' }); lb.rotation.x = -Math.PI / 2; lb.position.set(cx, 0.0165, cz + 0.022); g.add(lb);
    return g;
  }
  coil(-0.08, -0.045, 'R1', 0xc8764a); coil(0.08, -0.045, 'R2', 0xb08f72);
  var ZAX = new T.Vector3(0, 0, 1);
  function linkKey(x, z, name) {
    var key = S.plugKey([x, 0, z]), plug = key.userData.plug;
    var lb = S.label(name, { w: 0.02, ratio: 0.5, color: '#e9e4d6' }); lb.rotation.x = -Math.PI / 2;
    lb.position.set(x, 0.0165, z + 0.016); S.scene.add(lb);
    function pose(k) { return { x: 0.062 * (1 - k), y: 0.008 + 0.016 * k + 0.04 * Math.sin(Math.PI * k), z: 0.012 * (1 - k), rz: Math.PI / 2 * (1 - k) }; }
    function ap(k) { var q = pose(k); plug.position.set(q.x, q.y, q.z); plug.rotation.set(0, 0, q.rz); }
    function head(k) { var q = pose(k); return key.localToWorld(new T.Vector3(0, 0.013, 0).applyAxisAngle(ZAX, q.rz).add(new T.Vector3(q.x, q.y, q.z))); }
    ap(0);
    return { group: key, apply: ap, head: head, closed: false, name: name };
  }
  var links = [linkKey(CB[0] - 0.1, CB[1] + 0.045, 'A'), linkKey(CB[0], CB[1] + 0.045, 'B'), linkKey(CB[0] + 0.1, CB[1] + 0.045, 'S')];
  var cT1 = post(CB[0] - 0.16, 0.016, CB[1] - 0.06), cT2 = post(CB[0] + 0.16, 0.016, CB[1] - 0.06);
  S.contact(0.42, 0.24, CB[0], CB[1], 0.5);

  function toggleLink(i, on) {
    var k = links[i];
    if (!!on === k.closed) return Promise.resolve();
    if (busy()) return Promise.resolve();
    var a = k.closed ? 1 : 0, b = on ? 1 : 0;
    return S.hand.pinchMove(k.head(a), function (q) { return k.head(a + (b - a) * q); }, function (q) { k.apply(a + (b - a) * q); }, { ms: 750, mode: 'top' })
      .then(function () { k.apply(b); k.closed = !!on; S.click(1400, 0.04, 0.1); S.render(); });
  }
  function setMode(key) {
    var m = MODES.filter(function (q) { return q.k === key; })[0];
    if (!m) return Promise.resolve();
    if (busy()) return Promise.resolve();
    return putDown().then(function () {
      return [0, 1, 2].reduce(function (pr, i) { return pr.then(function () { return m.keys[i] ? null : toggleLink(i, false); }); }, Promise.resolve());
    }).then(function () {
      return [0, 1, 2].reduce(function (pr, i) { return pr.then(function () { return m.keys[i] ? toggleLink(i, true) : null; }); }, Promise.resolve());
    }).then(function () { st.mode = key; S.say('Link keys set: the right gap now holds ' + m.name + '.'); S.render(); });
  }

  // ---------------------------------------------------------------- accumulator, key K1, galvanometer
  var acc = new T.Group(); S.scene.add(acc); acc.position.set(-0.7, 0, -0.62);
  var accBody = S.rounded(0.07, 0.1, 0.06, 0.006, M.bakelite); accBody.position.y = 0.05; acc.add(accBody);
  var accLid = S.rounded(0.076, 0.012, 0.066, 0.004, M.blackPlastic); accLid.position.y = 0.104; acc.add(accLid);
  var vent = S.mesh(new T.CylinderGeometry(0.007, 0.007, 0.008, 18), new T.MeshStandardMaterial({ color: 0xd8862a, roughness: 0.5 })); vent.position.set(0, 0.114, 0); acc.add(vent);
  var accL = S.label('2 V', { w: 0.04, ratio: 0.45, color: '#f2f2f2' }); accL.position.set(0, 0.06, 0.0306); acc.add(accL);
  var accL2 = S.label('ACCUMULATOR', { w: 0.055, ratio: 0.16, color: '#c9ccd1' }); accL2.position.set(0, 0.035, 0.0306); acc.add(accL2);
  S.contact(0.12, 0.11, -0.7, -0.62, 0.55);
  var accP = post(-0.678, 0.11, -0.62, 'red'), accM = post(-0.722, 0.11, -0.62, 'black');
  var key1 = linkKey(0.08, 0.02, 'K1');
  var gal = S.meter({ min: -30, max: 30, zeroCentre: true, ticks: 6, unit: 'div', symbol: 'G', caption: 'GALVANOMETER 30–0–30', pos: [-0.3, 0, 0.02] });
  galTop = wpt(gal, 0.035, 0.082, -0.03);

  lead(accP.at, { x: 0.06, y: 0.031, z: 0.012 }, 'red', [[-0.72, -0.4], [-0.6, -0.12], [-0.2, 0.06]]);
  lead({ x: 0.1, y: 0.031, z: 0.012 }, tRcell.at, 'red', [[0.3, 0.04], [0.56, -0.2]]);
  lead(accM.at, tLcell.at, 'black', [[-0.74, -0.52], [-0.6, -0.48]]);
  lead(rBox.tL.at, tLgap.at, '#d9a520', [[-0.44, -0.6], [-0.26, -0.54]]);
  lead(rBox.tR.at, tM1.at, '#d9a520', [[-0.22, -0.62], [-0.12, -0.54]]);
  lead(cT1.at, tM2.at, 'blue', [[0.14, -0.6]], 0.01);
  lead(cT2.at, tRgap.at, 'blue', [[0.3, -0.58]], 0.01);
  lead(wpt(gal, -0.035, 0.082, -0.03), tMg.at, 'black', [[-0.26, -0.1], [-0.04, -0.4]]);

  S.addApparatus('bridge', bridge, 'Metre bridge', 'A 1 m manganin wire along a metre scale, with copper strips that form two gaps.');
  S.addApparatus('jockey', jock, 'Jockey', 'A knife-edge contact. Touch the wire gently; dragging it scrapes the wire and changes its resistance.');
  S.addApparatus('rb', rBox.group, 'Resistance box R (1–9999 Ω)', 'The known resistance in the left gap. Four dials: thousands, hundreds, tens and units.');
  S.addApparatus('comb', comb, 'Combination board (R₁, R₂ and three link keys)',
    'Link A puts R₁ into the gap, link B puts R₂ in, and link S joins the far ends of the two coils so that they are in series.');
  S.addApparatus('gal', gal, 'Galvanometer (30–0–30)', 'Zero-centre: it shows which way the current flows. At the null point it reads zero.');
  S.addApparatus('acc', acc, 'Accumulator (2 V)', 'Drives a steady current through the bridge wire.');
  S.addApparatus('key', key1.group, 'Plug key K₁', 'Insert the plug only while taking a reading; the wire heats up otherwise.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ---------------------------------------------------------------- physics
  function links3() { return { ka: links[0].closed ? 1 : 0, kb: links[1].closed ? 1 : 0, ser: links[2].closed ? 1 : 0 }; }
  function iGat(l) {
    if (!key1.closed) return 0;
    var q = HK.assign(p, links3());
    q.key = 1; q.Rk = Math.max(rBox.value(), 1e-6); q.lj = l / 100;
    return KC.view(KC.init(q, CFG), q, CFG).I_G;
  }
  function contact() { return key1.closed && J.mode === 'held' && J.pressed; }
  function divNow() { return contact() ? iGat(J.l) / FOM : 0; }
  function divText(d) {
    if (!contact()) return J.mode === 'held' ? 'jockey lifted' : 'jockey not touching the wire';
    var a = Math.abs(d);
    if (a < 0.25) return 'no deflection';
    return (a >= 30 ? 'off scale, ' : '') + Math.min(30, a).toFixed(1) + ' div to the ' + (d > 0 ? 'right' : 'left');
  }
  function modeName(k) { return MODES.filter(function (q) { return q.k === k; })[0].name; }
  function liveMode() {
    var l3 = links3();
    if (l3.ser) return 'ser';
    if (l3.ka && l3.kb) return 'par';
    if (l3.ka) return 'r1';
    if (l3.kb) return 'r2';
    return null;
  }
  var hudA = S.hudCard('Right gap holds'), hudB = S.hudCard('Jockey at'), hudC = S.hudCard('Galvanometer');

  function trace() {
    st.traced = true; S.focus('bridge');
    S.say('The accumulator and key K1 send a current along the whole wire. The resistance box is in the left gap and the combination board in the right gap; the galvanometer joins the centre strip to the jockey.');
    S.render();
  }
  function toggleK1(on) {
    if (!!on === key1.closed) return Promise.resolve();
    if (busy()) return Promise.resolve();
    return putDown().then(function () {
      var a = key1.closed ? 1 : 0, b = on ? 1 : 0;
      return S.hand.pinchMove(key1.head(a), function (q) { return key1.head(a + (b - a) * q); }, function (q) { key1.apply(a + (b - a) * q); }, { ms: 850, mode: 'top' })
        .then(function () { key1.apply(b); key1.closed = !!on; st.key = !!on; S.click(1400, 0.04, 0.1);
          S.say(on ? 'Key K1 closed: the accumulator drives a current through the bridge wire.' : 'Key K1 open: no current.'); S.render(); });
    });
  }
  function bestHere() { var d0 = Math.abs(iGat(J.l)), dm = Math.abs(iGat(J.l - 0.1)), dp = Math.abs(iGat(J.l + 0.1)); return d0 <= dm + 1e-15 && d0 <= dp + 1e-15; }
  function findNull() {
    var lo = 10, hi = 990, dlo, dhi;
    function probe(mmv) { return moveJockey(mmv / 10).then(function () { return iGat(J.l); }); }
    return probe(lo).then(function (d) { dlo = d; return probe(hi); }).then(function (d) {
      dhi = d;
      if (dlo * dhi > 0) { S.say('The needle swings the same way at both ends: change R so the balance point falls on the wire.'); return null; }
      function step() {
        if (hi - lo <= 1) return Promise.resolve();
        var mid = Math.round((lo + hi) / 2);
        return probe(mid).then(function (dm2) { if (dm2 === 0) { lo = hi = mid; return; }
          if ((dm2 > 0) === (dlo > 0)) { lo = mid; dlo = dm2; } else { hi = mid; dhi = dm2; } return step(); });
      }
      return step().then(function () { return probe(Math.abs(dlo) <= Math.abs(dhi) ? lo : hi); });
    });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!key1.closed) { S.say('Insert the plug key K1 first: no current flows.'); return false; }
    if (!(rBox.value() > 0)) { S.say('Set the resistance box first.'); return false; }
    var lm = liveMode();
    if (!lm) { S.say('No link key is in: there is nothing in the right gap. Choose one of the four settings.'); return false; }
    if (links3().ser && (links3().ka || links3().kb)) { S.say('Link S is for the series setting alone: take A and B out first.'); return false; }
    if (!contact()) { S.say('Touch the jockey on the wire and watch the galvanometer first.'); return false; }
    var d = divNow();
    if (Math.abs(d) >= 0.25 && !bestHere()) { S.say('The galvanometer still shows ' + divText(d) + '. Move the jockey until it reads zero.'); return false; }
    if (J.l < 25 || J.l > 75) { S.say('The null point is at ' + fnum(J.l) + ' cm, far from the middle. Change R so it comes nearer 50 cm.'); return false; }
    if (S.rows.some(function (r) { return r.mode === lm && r.R === rBox.value(); })) { S.say('You already have that setting at R = ' + rBox.value() + ' ohm.'); return false; }
    S.addRow({ mode: lm, R: rBox.value(), l: J.l });
    S.say('Written in your record book: ' + modeName(lm) + ', R = ' + rBox.value() + ' ohm, l = ' + fnum(J.l) + ' cm, so X = ' + (rBox.value() * (100 - J.l) / J.l).toFixed(2) + ' ohm.');
    return true;
  }
  function xOf(r) { return r.R * (100 - r.l) / r.l; }
  function xFor(mode) {
    var v = S.rows.filter(function (r) { return r.mode === mode; }).map(xOf);
    return v.length ? S.fit.mean(v) : NaN;
  }
  function result(rows) {
    var xs = xFor('ser');
    if (!isFinite(xs)) return null;
    var x1 = xFor('r1'), x2 = xFor('r2'), xp = xFor('par');
    var note = 'R₁ = ' + (isFinite(x1) ? x1.toFixed(2) : '—') + ' Ω, R₂ = ' + (isFinite(x2) ? x2.toFixed(2) : '—') + ' Ω.';
    if (isFinite(x1) && isFinite(x2)) {
      note += ' Series should be R₁ + R₂ = ' + (x1 + x2).toFixed(2) + ' Ω.';
      if (isFinite(xp)) note += ' Parallel measured ' + xp.toFixed(2) + ' Ω against R₁R₂/(R₁ + R₂) = ' + (x1 * x2 / (x1 + x2)).toFixed(2) + ' Ω.';
    }
    return { label: 'Series combination', value: xs, unit: 'Ω', digits: 2, truth: p.R1 + p.R2, note: note };
  }
  function haveAll() { return MODES.every(function (m) { return S.rows.some(function (r) { return r.mode === m.k; }); }); }

  return {
    camera: { pos: [-0.05, 1.3, 1.14], look: [-0.05, 0.02, -0.34] },
    views: { bench: [[-0.05, 1.22, 1.06], [-0.05, 0.02, -0.34]], bridge: [[0.0, 0.86, 0.3], [0.0, 0.02, -0.36]],
      jockey: [[0.0, 0.48, 0.0], [0.0, 0.02, -0.32]], gal: [[-0.3, 0.3, 0.3], [-0.3, 0.06, 0.02]],
      rb: [[-0.34, 0.3, -0.4], [-0.34, 0.03, -0.68]], comb: [[0.3, 0.32, -0.36], [0.3, 0.03, -0.68]],
      acc: [[-0.6, 0.34, -0.34], [-0.7, 0.06, -0.62]], key: [[0.08, 0.26, 0.26], [0.08, 0.02, 0.02]],
      book: [[0.66, 0.46, 0.44], [0.66, 0.0, -0.1]] },
    theory: {
      principle: 'A metre bridge is a Wheatstone bridge. The two parts of the uniform wire, l and (100 − l), are two of its arms; the known R and the unknown X in the gaps are the other two. At the null point no current flows through the galvanometer.',
      formula: 'X = R (100 − l) / l',
      formulaNote: 'measure R₁ and R₂ one at a time, then the two together, in series and in parallel',
      more: ['In series the same current passes through both coils and their potential differences add, so the combination should come out as R₁ + R₂, larger than either coil.',
        'In parallel the same potential difference is across both and the currents add, so 1/X = 1/R₁ + 1/R₂ and the combination is smaller than either coil.',
        'The bridge is most sensitive when the null point is near the middle of the wire, so R is changed to bring each balance into the 30 to 70 cm range.'],
      precautions: 'Keep every connection tight and the copper strips clean. Touch the jockey gently; never slide it along the wire while pressing. Only the links the setting calls for may be in at one time.' },
    book: { title: 'Expt. — Laws of combination of resistances', at: [0.66, 0.1, -0.12],
      lines: ['Aim: to verify the laws of combination (series', 'and parallel) of resistances with a metre bridge.',
        'Wire: 1 m manganin, scale LC 0.1 cm', 'X = R (100 − l) / l',
        'Series: X = R1 + R2', 'Parallel: 1/X = 1/R1 + 1/R2'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'In the gap', get: function (r) { return modeName(r.mode); } },
        { label: 'R (Ω)', get: function (r) { return r.R; } },
        { label: 'l (cm)', get: function (r) { return fnum(r.l); } },
        { label: 'X (Ω)', get: function (r) { return xOf(r).toFixed(2); } }] },
    graph: { x: function (r) { return r.l / (100 - r.l); }, y: function (r) { return r.R; },
      xlabel: 'l / (100 − l)', ylabel: 'R (Ω)', x0: 0, y0: 0 },
    result: result,
    tol: 0.02,
    resultNote: 'The series value comes out larger than either coil and the parallel value smaller than either: that is the whole content of the two laws.',
    chips: ['Why is the series value the largest?', 'What is the null point?', 'Check my readings', 'Why keep the null point near the middle?'],
    viva: [['In series the combined resistance is', ['Larger than either coil', 'Smaller than either coil', 'The average'], 0, 'X = R₁ + R₂.'],
      ['In parallel the combined resistance is', ['Smaller than either coil', 'Larger than either', 'The sum'], 0, '1/X = 1/R₁ + 1/R₂.'],
      ['Why is the bridge wire made of manganin?', ['Its resistance hardly changes with temperature', 'It is a very good conductor', 'It is cheap'], 0,
        'Manganin has a very low temperature coefficient of resistance.']],
    askState: function () {
      return { experiment: 'laws of combination of resistances with a metre bridge',
        key_K1_closed: key1.closed, resistance_box_R_ohm: rBox.value(),
        links_in: links.filter(function (k) { return k.closed; }).map(function (k) { return k.name; }),
        right_gap_holds: liveMode() ? modeName(liveMode()) : 'nothing',
        jockey_cm: J.mode === 'held' ? J.l : null, galvanometer: divText(divNow()), readings_taken: S.rows.length };
    },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Set up the bridge');
          u.p('The resistance box goes in the left gap and the combination board in the right gap. The three link keys choose what the right gap holds.');
          u.task('1. Trace the circuit', st.traced, st.traced ? 'Main circuit through the wire; R left, combination right' : 'Follow the leads from the accumulator')
            .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
          var t2 = u.task('2. Set the resistance box', rBox.value() > 0, rBox.value() > 0 ? 'R = ' + rBox.value() + ' Ω' : 'Every dial is at 0');
          var row = document.createElement('div'); row.className = 'row';
          [3, 4, 5, 6].forEach(function (v) { row.appendChild(u.button(v + ' Ω', function () { setBox(v); }, rBox.value() === v, S.hand.busy)); });
          t2.add(row);
          u.task('3. Insert the plug key K₁', key1.closed, key1.closed ? 'K₁ closed' : 'K₁ is open')
            .add(u.button(key1.closed ? 'K₁ is in' : 'Insert the plug in K₁', function () {
              if (!(rBox.value() > 0)) { S.say('Set the resistance box first.'); return; } toggleK1(true); }, !key1.closed, key1.closed || S.hand.busy));
          u.note('Start with R about equal to the coils, so that every null point falls near the middle of the wire.');
          u.next('Next: measure the four settings', st.traced && rBox.value() > 0 && key1.closed);
        },
        ok: function () { return st.traced && rBox.value() > 0 && key1.closed; },
        auto: function () { trace(); return setBox(4).then(function () { return toggleK1(true); }); } },
      { id: 'measure', title: 'Four settings', view: 'bridge', render: function (u) {
          u.h2('R₁, R₂, the two in series and the two in parallel');
          u.p('Choose a setting with the link keys, find the null point, and record it. Do all four.');
          var row = u.row();
          MODES.forEach(function (m) {
            var done = S.rows.some(function (r) { return r.mode === m.k; });
            row.appendChild(u.button(m.name + (done ? ' ✓' : ''), function () { setMode(m.k); }, liveMode() === m.k, S.hand.busy));
          });
          var sl = { v: J.l };
          u.slider('Jockey position from A', 1, 99, 0.1, function () { return sl.v; }, function (v) { sl.v = v; }, 'cm', 1);
          u.row(u.button('Touch the jockey here', function () { moveJockey(sl.v); }, true, S.hand.busy || !key1.closed),
            u.button('Find the null point', function () {
              if (!liveMode()) { S.say('Choose one of the four link settings first.'); return; } findNull(); }, false, S.hand.busy));
          u.row(u.button('−1 cm', function () { moveJockey(J.l - 1); }, false, S.hand.busy || J.mode !== 'held'),
            u.button('−1 mm', function () { moveJockey(J.l - 0.1); }, false, S.hand.busy || J.mode !== 'held'),
            u.button('+1 mm', function () { moveJockey(J.l + 0.1); }, false, S.hand.busy || J.mode !== 'held'),
            u.button('+1 cm', function () { moveJockey(J.l + 1); }, false, S.hand.busy || J.mode !== 'held'));
          u.live(function () { return (liveMode() ? 'Gap holds ' + modeName(liveMode()) : 'Nothing in the gap') + '  ·  ' +
            (J.mode === 'held' ? 'jockey at ' + fnum(J.l) + ' cm' : 'jockey on the bench') + '  ·  galvanometer: ' + divText(divNow()); });
          u.row(u.button('Record this null point', function () { record(); }, true, !contact()),
            u.button('Put the jockey down', function () { putDown(); }, false, J.mode !== 'held' || S.hand.busy),
            u.button(key1.closed ? 'Take K₁ out' : 'Insert K₁', function () { toggleK1(!key1.closed); }, false, S.hand.busy));
          u.h3('Observation table'); u.table();
          if (!haveAll()) u.p(S.rows.length + ' settings recorded; all four are needed.');
          u.next('Next: the two laws', haveAll());
        },
        ok: function () { return haveAll(); },
        auto: function () {
          return MODES.reduce(function (pr, m) {
            return pr.then(function () { return setMode(m.k); }).then(findNull).then(function () { record(); });
          }, Promise.resolve());
        } },
    ],
    tick: function () {
      var d = divNow();
      gal.set(Math.max(-31, Math.min(31, d)));
      hudA.set(liveMode() ? modeName(liveMode()) : 'nothing');
      hudB.set(J.mode === 'held' ? fnum(J.l) + ' cm' : '—');
      hudC.set(contact() ? (Math.abs(d) < 0.25 ? '0 div' : (Math.abs(d) >= 30 ? '>30' : Math.abs(d).toFixed(1)) + ' div ' + (d > 0 ? 'R' : 'L')) : '—');
    },
  };
});
