/* Prayogshala studio module: THE ALTERNATING-CURRENT BRIDGE BENCH (B.Sc. electricity laboratory).
   A bakelite bridge box with the four arms printed on it as a diamond and a terminal pair for every arm, an
   audio oscillator across one diagonal and a tuned detector with headphones across the other, and two decade
   dials - resistance and capacitance - that are the variable arms. De Sauty's bridge (capacitance against a
   standard capacitor) and Owen's bridge (self-inductance against a capacitance) both run on this one box. The
   detector current comes from this lab's kernel (packs/em_ug.js: Thevenin's theorem applied to the bridge in
   complex numbers), which is the same code the server checks against the balance equations. Everything runs on
   the oscillator's few volts; nothing here is at mains voltage. */
HoolaStudio.define('ac-bridge', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.acbridge;
  var p = HK.paramsFor('acbridge', S.lab.params);
  var MODE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var OWEN = MODE === 'owen-bridge';
  var st = { traced: false, osc: false, f: p.f, R1: p.R1, R2: p.R2, C2: p.C2 };
  var R1_SETTINGS = [220, 470, 1000], F_SETTINGS = [1000, 2000, 500];

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function fHz(f) { return f >= 1000 ? (f / 1000).toFixed(1) + ' kHz' : Math.round(f) + ' Hz'; }

  /* ---------------------------------------------------------------- the bridge box */
  var BZ = -0.26, BW = 0.50, BD = 0.32, BH = 0.05;
  function W(u, v) { return new T.Vector3(u, BH + 0.002, BZ - v); }
  var NODE = { top: [0, 0.105], left: [-0.165, 0], right: [0.165, 0], bot: [0, -0.105] };
  var ARM = { a1: [-0.088, 0.055], a2: [0.088, 0.055], a3: [-0.088, -0.055], a4: [0.088, -0.055] };

  var boxTex = S.canvasTex(1800, Math.round(1800 * BD / BW), function (c, w, h) {
    var X = function (u) { return (u / BW + 0.5) * w; }, Y = function (v) { return (0.5 - v / BD) * h; }, k = w / BW;
    c.fillStyle = '#1b1d22'; c.fillRect(0, 0, w, h);
    for (var i = 0; i < 2200; i++) { c.fillStyle = 'rgba(255,255,255,' + (0.008 + (i % 5) * 0.004) + ')'; c.fillRect((i * 89) % w, (i * 53) % h, 2, 2); }
    c.strokeStyle = '#e8e4d8'; c.lineWidth = 0.004 * k; c.lineCap = 'round';
    function seg(a, b) { c.beginPath(); c.moveTo(X(a[0]), Y(a[1])); c.lineTo(X(b[0]), Y(b[1])); c.stroke(); }
    seg(NODE.top, NODE.left); seg(NODE.top, NODE.right); seg(NODE.left, NODE.bot); seg(NODE.right, NODE.bot);
    seg(NODE.left, NODE.right);
    [NODE.top, NODE.left, NODE.right, NODE.bot].forEach(function (n) {
      c.fillStyle = '#e8e4d8'; c.beginPath(); c.arc(X(n[0]), Y(n[1]), 0.005 * k, 0, Math.PI * 2); c.fill(); });
    // arm boxes
    c.lineWidth = 0.0035 * k;
    [['a1', 'ARM 1'], ['a2', 'ARM 2'], ['a3', 'ARM 3'], ['a4', 'ARM 4']].forEach(function (q) {
      var n = ARM[q[0]];
      c.fillStyle = '#2b2f36'; c.strokeStyle = '#f0ebdd';
      var ww = 0.062 * k, hh = 0.03 * k;
      c.save(); c.translate(X(n[0]), Y(n[1]));
      c.rotate(n[0] < 0 ? (n[1] > 0 ? -0.56 : 0.56) : (n[1] > 0 ? 0.56 : -0.56));
      c.fillRect(-ww / 2, -hh / 2, ww, hh); c.strokeRect(-ww / 2, -hh / 2, ww, hh);
      c.fillStyle = '#f0ebdd'; c.font = '700 ' + Math.round(0.012 * k) + 'px "Public Sans", sans-serif';
      c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(q[1], 0, 0); c.restore();
    });
    c.textBaseline = 'alphabetic'; c.textAlign = 'center';
    function text(t, u, v, px, col) { c.fillStyle = col || '#e8e4d8'; c.font = '700 ' + Math.round(px * k) + 'px "Public Sans", sans-serif'; c.fillText(t, X(u), Y(v)); }
    text('ALTERNATING-CURRENT BRIDGE', 0, 0.138, 0.0135, '#b9c7bd');
    text('OSCILLATOR', 0, -0.142, 0.011, '#9fb6a6');
    text('DETECTOR', -0.21, -0.012, 0.011, '#9fb6a6');
    text('A', 0, 0.122, 0.012, '#f0c36b'); text('B', -0.188, 0.012, 0.012, '#f0c36b');
    text('D', 0.19, 0.012, 0.012, '#f0c36b'); text('C', 0, -0.122, 0.012, '#f0c36b');
  });
  var box = new T.Group(); S.scene.add(box);
  var slab = S.rounded(BW, BD, BH, 0.006, M.bakelite); slab.rotation.x = -Math.PI / 2; slab.position.set(0, BH / 2, BZ); box.add(slab);
  var topFace = new T.Mesh(new T.PlaneGeometry(BW - 0.006, BD - 0.006), new T.MeshStandardMaterial({ map: boxTex, roughness: 0.4 }));
  topFace.rotation.x = -Math.PI / 2; topFace.position.set(0, BH + 0.0012, BZ); box.add(topFace);
  [[-0.22, -0.39], [0.22, -0.39], [-0.22, -0.13], [0.22, -0.13]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.004, 14), M.rubber); ft.position.set(f[0], 0.002, f[1]); box.add(ft); });
  S.contact(BW + 0.12, BD + 0.12, 0, BZ, 0.55);
  function socket(u, v) {
    var g = new T.Group(); S.scene.add(g); g.position.copy(W(u, v));
    var ring = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.004, 18), M.brass); ring.position.y = 0.002; g.add(ring);
    var hole = S.mesh(new T.CylinderGeometry(0.0027, 0.0027, 0.005, 14), M.black, false); hole.position.y = 0.0032; g.add(hole);
    return { g: g, at: W(u, v).add(new T.Vector3(0, 0.006, 0)) };
  }
  var TERM = {};
  Object.keys(ARM).forEach(function (k) {
    var n = ARM[k], dx = (n[0] < 0 ? 1 : -1) * 0.026, dz = (n[1] > 0 ? -1 : 1) * 0.022;
    TERM[k] = [socket(n[0] - dx * 0.6, n[1] - dz * 0.6), socket(n[0] + dx * 0.6, n[1] + dz * 0.6)];
  });
  var oscT = [socket(-0.03, -0.138), socket(0.03, -0.138)];
  var detT = [socket(-0.218, -0.04), socket(-0.218, 0.04)];

  /* the components clipped into the arms */
  function capCan(u, v, label, tint) {
    var g = new T.Group(); S.scene.add(g); g.position.copy(W(u, v)); g.rotation.y = (u < 0 ? 0.56 : -0.56) * (v > 0 ? 1 : -1);
    var can = S.mesh(new T.CylinderGeometry(0.0115, 0.0115, 0.034, 24), new T.MeshStandardMaterial({ color: tint, roughness: 0.4 }));
    can.rotation.z = Math.PI / 2; can.position.y = 0.014; g.add(can);
    [-1, 1].forEach(function (s) {
      var ld = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.016, 8), M.chrome);
      ld.rotation.z = Math.PI / 2; ld.position.set(s * 0.025, 0.014, 0); g.add(ld);
      var dn = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.012, 8), M.chrome); dn.position.set(s * 0.032, 0.008, 0); g.add(dn); });
    var lb = S.label(label, { w: 0.03, ratio: 0.3, color: '#f6f2e6' }); lb.rotation.x = -Math.PI / 2;
    lb.position.set(0, 0.027, 0.012); g.add(lb);
    return g;
  }
  function coilCan(u, v, label) {
    var g = new T.Group(); S.scene.add(g); g.position.copy(W(u, v)); g.rotation.y = (u < 0 ? 0.56 : -0.56) * (v > 0 ? 1 : -1);
    var former = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.044, 20), M.white); former.rotation.z = Math.PI / 2; former.position.y = 0.016; g.add(former);
    var pts = [], turns = 18;
    for (var i = 0; i <= turns * 18; i++) { var t = i / (turns * 18), a = t * turns * Math.PI * 2;
      pts.push(new T.Vector3(-0.019 + t * 0.038, 0.016 + 0.0095 * Math.cos(a), 0.0095 * Math.sin(a))); }
    g.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts), turns * 18, 0.0009, 6, false),
      new T.MeshStandardMaterial({ color: 0xc8764a, roughness: 0.28, metalness: 0.9 })));
    [-1, 1].forEach(function (s) { var sp = S.rounded(0.01, 0.018, 0.018, 0.003, M.white); sp.position.set(s * 0.026, 0.012, 0); g.add(sp); });
    var lb = S.label(label, { w: 0.03, ratio: 0.3, color: '#f6f2e6' }); lb.rotation.x = -Math.PI / 2;
    lb.position.set(0, 0.03, 0.014); g.add(lb);
    return g;
  }
  function resCan(u, v, label) {               // a wire-wound standard resistance in its own holder
    var g = new T.Group(); S.scene.add(g); g.position.copy(W(u, v)); g.rotation.y = (u < 0 ? 0.56 : -0.56) * (v > 0 ? 1 : -1);
    var body = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.036, 22), new T.MeshStandardMaterial({ color: 0xd8c6a0, roughness: 0.55 }));
    body.rotation.z = Math.PI / 2; body.position.y = 0.013; g.add(body);
    [-1, 1].forEach(function (sg) {
      var cap = S.mesh(new T.CylinderGeometry(0.0095, 0.0095, 0.004, 20), new T.MeshStandardMaterial({ color: 0x9aa0a6, roughness: 0.4, metalness: 0.7 }));
      cap.rotation.z = Math.PI / 2; cap.position.set(sg * 0.02, 0.013, 0); g.add(cap);
      var ld = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.014, 8), M.chrome);
      ld.rotation.z = Math.PI / 2; ld.position.set(sg * 0.029, 0.013, 0); g.add(ld);
      var dn = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.012, 8), M.chrome); dn.position.set(sg * 0.035, 0.007, 0); g.add(dn); });
    var lb = S.label(label, { w: 0.03, ratio: 0.3, color: '#f6f2e6' }); lb.rotation.x = -Math.PI / 2;
    lb.position.set(0, 0.025, 0.012); g.add(lb);
    return g;
  }
  var unknown = OWEN ? coilCan(ARM.a1[0], ARM.a1[1], 'COIL') : capCan(ARM.a3[0], ARM.a3[1], 'C3', 0x2f6f4e);
  var standard = capCan(ARM.a4[0], ARM.a4[1], 'C4', 0x8a6d2a);
  var fixedArm = OWEN ? resCan(ARM.a3[0], ARM.a3[1], 'R3') : resCan(ARM.a1[0], ARM.a1[1], 'R1');

  /* ---------------------------------------------------------------- oscillator and detector */
  var osc = (function () {
    var g = new T.Group(); S.scene.add(g); g.position.set(-0.52, 0, -0.46);
    var GW = 0.22, GD = 0.15, GH = 0.085;
    var body = S.rounded(GW, GD, GH, 0.006, new T.MeshStandardMaterial({ color: 0x8e949c, roughness: 0.5 }));
    body.rotation.x = -Math.PI / 2; body.position.y = GH / 2; g.add(body);
    var fascia = new T.Mesh(new T.PlaneGeometry(GW - 0.01, 0.07), new T.MeshStandardMaterial({ color: 0x23262b, roughness: 0.5 }));
    fascia.position.set(0, GH * 0.6, GD / 2 + 0.0012); g.add(fascia);
    var lcd = S.liveTex(440, 160), last = '';
    var scr = new T.Mesh(new T.PlaneGeometry(0.084, 0.03), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
    scr.position.set(-0.05, GH * 0.66, GD / 2 + 0.0022); g.add(scr);
    var knurl = S.canvasTex(256, 32, function (c, w, h) { c.fillStyle = '#17181c'; c.fillRect(0, 0, w, h); c.fillStyle = '#41454c'; for (var i = 0; i < w; i += 8) c.fillRect(i, 0, 3, h); });
    var dial = new T.Group(); dial.position.set(0.055, GH * 0.58, GD / 2 + 0.012); g.add(dial);
    var dk = S.mesh(new T.CylinderGeometry(0.02, 0.022, 0.02, 32), new T.MeshStandardMaterial({ map: knurl, roughness: 0.42 }));
    dk.rotation.x = Math.PI / 2; dial.add(dk);
    var dm = S.mesh(new T.BoxGeometry(0.0022, 0.014, 0.0014), M.red, false); dm.position.set(0, 0.01, 0.012); dial.add(dm);
    var rocker = S.mesh(new T.BoxGeometry(0.016, 0.01, 0.006), M.red); rocker.position.set(-0.088, GH * 0.28, GD / 2 + 0.004); g.add(rocker);
    var lamp = S.mesh(new T.SphereGeometry(0.004, 12, 10), new T.MeshStandardMaterial({ color: 0x3a1a16, roughness: 0.3 }));
    lamp.position.set(-0.088, GH * 0.52, GD / 2 + 0.004); g.add(lamp);
    var lb = S.label('AUDIO OSCILLATOR', { w: 0.1, ratio: 0.14, color: '#d7dbe0' }); lb.position.set(0, GH * 0.9, GD / 2 + 0.0022); g.add(lb);
    S.contact(GW + 0.08, GD + 0.08, -0.52, -0.46, 0.55);
    return { group: g, dial: dial, rocker: rocker, lamp: lamp,
      dialAt: wpt(g, 0.055, GH * 0.58, GD / 2 + 0.028), out: wpt(g, -0.05, GH * 0.2, GD / 2 + 0.012),
      turn: function (f) { dial.rotation.z = -Math.log(Math.max(f, 1) / 100) * 1.3; },
      lit: function (on) { lamp.material.color.setHex(on ? 0xff6b4a : 0x3a1a16);
        lamp.material.emissive = new T.Color(on ? 0xff5a3a : 0x000000); lamp.material.emissiveIntensity = on ? 2.4 : 0; },
      show: function (f, on) { var t = on ? (f >= 1000 ? (f / 1000).toFixed(2) + ' k' : Math.round(f) + ' ') : '--- ';
        if (t === last) return; last = t;
        lcd.draw(function (c, w, h) { c.fillStyle = '#0a1016'; c.fillRect(0, 0, w, h);
          c.fillStyle = '#ff9a3c'; c.font = '700 92px "JetBrains Mono", monospace'; c.textAlign = 'right';
          c.fillText(t + 'Hz', w - 14, 110); }); } };
  })();
  osc.turn(st.f); osc.lit(false);

  var det = (function () {
    var g = new T.Group(); S.scene.add(g); g.position.set(0.5, 0, -0.42);
    var DW = 0.19, DD = 0.14, DH = 0.075;
    var body = S.rounded(DW, DD, DH, 0.006, new T.MeshStandardMaterial({ color: 0x474c55, roughness: 0.52 }));
    body.rotation.x = -Math.PI / 2; body.position.y = DH / 2; g.add(body);
    var lb = S.label('TUNED DETECTOR', { w: 0.09, ratio: 0.14, color: '#d7dbe0' }); lb.position.set(0, DH * 0.86, DD / 2 + 0.0022); g.add(lb);
    var gain = S.mesh(new T.CylinderGeometry(0.012, 0.013, 0.012, 24), M.blackPlastic);
    gain.rotation.x = Math.PI / 2; gain.position.set(0.055, DH * 0.42, DD / 2 + 0.006); g.add(gain);
    var jack = S.mesh(new T.CylinderGeometry(0.007, 0.008, 0.01, 18), M.chrome);
    jack.rotation.x = Math.PI / 2; jack.position.set(-0.058, DH * 0.42, DD / 2 + 0.006); g.add(jack);
    S.contact(DW + 0.08, DD + 0.08, 0.5, -0.42, 0.55);
    return { group: g, gain: gain, jack: wpt(g, -0.058, DH * 0.42, DD / 2 + 0.012) };
  })();
  var nullMeter = S.meter({ min: 0, max: 50, ticks: 5, unit: 'µA', symbol: 'µA',
    caption: 'NULL DETECTOR', pos: [0.26, 0, 0.0], rotY: -0.25 });
  var phones = (function () {
    var g = new T.Group(); S.scene.add(g); g.position.set(0.52, 0, -0.12); g.rotation.y = -0.3;
    var band = S.mesh(new T.TorusGeometry(0.038, 0.004, 10, 28, Math.PI), M.blackPlastic);
    band.rotation.x = -0.3; band.position.y = 0.03; g.add(band);
    [-1, 1].forEach(function (s) {
      var cup = S.mesh(new T.CylinderGeometry(0.019, 0.021, 0.016, 24), M.blackPlastic);
      cup.rotation.z = Math.PI / 2; cup.position.set(s * 0.038, 0.016, 0); g.add(cup);
      var pad = S.mesh(new T.CylinderGeometry(0.019, 0.019, 0.004, 24), new T.MeshStandardMaterial({ color: 0x24262a, roughness: 0.9 }));
      pad.rotation.z = Math.PI / 2; pad.position.set(s * 0.029, 0.016, 0); g.add(pad); });
    S.contact(0.12, 0.09, 0.52, -0.12, 0.45);
    return g;
  })();

  /* ---------------------------------------------------------------- the two decade dials */
  function decade(x, z, muls, title, unit, fmt) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z);
    var n = muls.length, DW = 0.045 + n * 0.05, DD = 0.105, DH = 0.044;
    var body = S.rounded(DW, DD, DH, 0.005, M.darkWood); body.rotation.x = -Math.PI / 2; body.position.y = DH / 2; g.add(body);
    var dx = muls.map(function (m, i) { return -(n - 1) * 0.05 / 2 + i * 0.05; });
    var PWn = DW - 0.007, PDn = DD - 0.007;
    var tex = S.canvasTex(1100, Math.round(1100 * PDn / PWn), function (c, w, h) {
      var X = function (u) { return (u / PWn + 0.5) * w; }, Y = function (v) { return (v / PDn + 0.5) * h; }, k = w / PWn;
      c.fillStyle = '#191c21'; c.fillRect(0, 0, w, h);
      c.strokeStyle = 'rgba(255,255,255,.14)'; c.lineWidth = 3; c.strokeRect(9, 9, w - 18, h - 18);
      c.fillStyle = '#eceadf'; c.font = '700 ' + Math.round(k * 0.0082) + 'px "Public Sans", sans-serif'; c.textAlign = 'left';
      c.fillText(title, 20, Math.round(k * 0.0125));
      muls.forEach(function (m, i) {
        var cx = X(dx[i]), cy = Y(0.004), R = 0.023 * k;
        c.strokeStyle = '#8b9099'; c.lineWidth = 2; c.beginPath(); c.arc(cx, cy, R * 0.72, 0, Math.PI * 2); c.stroke();
        c.textAlign = 'center'; c.fillStyle = '#eceadf'; c.font = '600 ' + Math.round(k * 0.0064) + 'px "Public Sans", sans-serif';
        for (var d = 0; d < 10; d++) { var a = d * Math.PI / 5; c.fillText(String(d), cx + Math.sin(a) * R, cy + Math.cos(a) * R + k * 0.0023); }
        c.fillStyle = '#f0c36b'; c.font = '700 ' + Math.round(k * 0.0062) + 'px "Public Sans", sans-serif';
        c.fillText('x ' + fmt(m), cx, Y(-0.040));
      });
    });
    var pan = new T.Mesh(new T.PlaneGeometry(PWn, PDn), new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }));
    pan.rotation.x = -Math.PI / 2; pan.position.y = DH + 0.0006; g.add(pan);
    var knurl = S.canvasTex(256, 32, function (c, w, h) { c.fillStyle = '#15161a'; c.fillRect(0, 0, w, h); c.fillStyle = '#3b3e45'; for (var i = 0; i < w; i += 9) c.fillRect(i, 0, 3, h); });
    var dials = muls.map(function (m, i) {
      var d = new T.Group(); d.position.set(dx[i], DH + 0.001, 0.004); g.add(d);
      var kb = S.mesh(new T.CylinderGeometry(0.015, 0.0165, 0.012, 32), new T.MeshStandardMaterial({ map: knurl, roughness: 0.42 })); kb.position.y = 0.006; d.add(kb);
      var cap = S.mesh(new T.CylinderGeometry(0.0115, 0.0115, 0.0015, 32), M.chrome); cap.position.y = 0.0128; d.add(cap);
      var ptr = S.mesh(new T.BoxGeometry(0.0022, 0.0012, 0.013), M.white, false); ptr.position.set(0, 0.0136, 0.0075); d.add(ptr);
      return { g: d, mul: m, digit: 0, top: new T.Vector3(x + dx[i], DH + 0.015, z + 0.004) };
    });
    S.contact(DW + 0.06, DD + 0.06, x, z, 0.5);
    var api = { group: g, dials: dials, muls: muls, unit: unit, step: muls[muls.length - 1],
      value: function () { var v = 0; dials.forEach(function (d) { v += d.digit * d.mul; }); return Math.round(v / api.step) * api.step; },
      max: function () { var v = 0; dials.forEach(function (d) { v += 9 * d.mul; }); return v; },
      look: function () { dials.forEach(function (d) { d.g.rotation.y = d.digit * Math.PI / 5; }); },
      digitsFor: function (value) { var left = Math.round(value / api.step) * api.step, want = [];
        muls.forEach(function (m) { var d = Math.max(0, Math.min(9, Math.floor(left / m + 1e-9))); want.push(d); left -= d * m; });
        return want; },
      put: function (value) { api.digitsFor(value).forEach(function (d, i) { dials[i].digit = d; }); api.look(); } };
    return api;
  }
  var rDial = decade(-0.3, 0.1, [1000, 100, 10, 1], 'RESISTANCE ARM  R2', 'Ω', function (m) { return String(m); });
  var cDial = decade(0.04, 0.12, [1, 0.1, 0.01, 0.001], 'CAPACITANCE ARM  C2  µF', 'µF',
    function (m) { return m >= 1 ? String(m) : m.toFixed(3).replace(/0+$/, ''); });
  rDial.put(st.R2);
  cDial.put(st.C2 * 1e6);

  /* ---------------------------------------------------------------- leads */
  function lead(a, b, color, via, lift) {
    var up = lift === undefined ? 0.02 : lift, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.005, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color);
    if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; }
    return w;
  }
  lead(osc.out, oscT[0].at, 'red', [[-0.42, -0.5], [-0.16, -0.44]]);
  lead(new T.Vector3(osc.out.x + 0.03, osc.out.y, osc.out.z), oscT[1].at, 'black', [[-0.36, -0.52], [-0.08, -0.46]]);
  lead(detT[0].at, det.jack, 'blue', [[-0.34, -0.06], [0.1, 0.0], [0.42, -0.28]]);
  lead(detT[1].at, nullMeter.userData.plus.getWorldPosition(new T.Vector3()), 'black', [[-0.3, -0.16], [0.1, -0.06]]);
  lead(nullMeter.userData.minus.getWorldPosition(new T.Vector3()), det.jack, 'black', [[0.3, -0.18]]);
  lead(TERM.a2[0].at, new T.Vector3(-0.3 + 0.095, 0.045, 0.06), '#d9a520', [[0.12, -0.08]]);
  lead(TERM.a2[1].at, new T.Vector3(0.04 - 0.095, 0.045, 0.08), 'blue', [[0.0, -0.04]]);

  S.addApparatus('box', box, 'Alternating-current bridge box',
    'The four arms are printed on the panel as a diamond: arms 1 and 2 above, 3 and 4 below. The oscillator is across the top and bottom corners and the detector across the two side corners.');
  S.addApparatus('osc', osc.group, 'Audio oscillator', 'A few volts at an audio frequency, across one diagonal of the bridge. Its frequency dial is set once and left alone while the bridge is balanced.');
  S.addApparatus('det', det.group, 'Tuned detector and headphones', 'An amplifier tuned to the oscillator\'s note, a null meter and headphones. At balance the note dies away and the meter falls to zero.');
  S.addApparatus('meter', nullMeter, 'Null meter', 'Reads the current through the detector. The quietest point is a true null, not a small reading.');
  S.addApparatus('rdial', rDial.group, 'Variable resistance arm R₂', 'Four dials: thousands, hundreds, tens and units of ohms.');
  S.addApparatus('cdial', cDial.group, 'Variable capacitance arm C₂', 'Dials in microfarads down to a thousandth of a microfarad.');
  S.addApparatus('unk', unknown, OWEN ? 'The coil under test' : 'The unknown capacitor',
    OWEN ? 'Clipped into arm 1. Its self-inductance and its own resistance are what the bridge measures.'
      : 'Clipped into arm 3, against the standard capacitor in arm 4.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  /* ---------------------------------------------------------------- physics */
  function now(over) {
    var q = HK.assign(p, { f: st.f, R1: st.R1, R2: rDial.value(), C2: cDial.value() * 1e-6 });
    if (over) q = HK.assign(q, over);
    return q;
  }
  function detAt(over) { var q = now(over); return KN.view(KN.init(q, q), q, q).I_G; }
  function quiet() { return st.osc ? detAt() : 0; }
  function noteText() {
    if (!st.osc) return 'the oscillator is off';
    var i = quiet() * 1e6;
    return i < 0.05 ? 'silence: the bridge is balanced' : i < 1 ? 'a faint hum, ' + i.toFixed(2) + ' µA'
      : 'a clear note, ' + i.toFixed(1) + ' µA';
  }
  function bestOf(which, lo, hi) {               // turn one dial for the quietest detector (golden section)
    var g = 0.6180339887498949, c = hi - g * (hi - lo), d = lo + g * (hi - lo);
    function f(x) { var o = {}; o[which] = x; return detAt(o); }
    var fc = f(c), fd = f(d), i;
    for (i = 0; i < 80; i++) {
      if (fc < fd) { hi = d; d = c; fd = fc; c = hi - g * (hi - lo); fc = f(c); }
      else { lo = c; c = d; fc = fd; d = lo + g * (hi - lo); fd = f(d); }
    }
    return (lo + hi) / 2;
  }
  var hudA = S.hudCard('Detector'), hudB = S.hudCard('R₂ dial'), hudC = S.hudCard(OWEN ? 'C₂ dial' : 'Ratio arm R₁');

  /* ---------------------------------------------------------------- human actions */
  function trace() {
    st.traced = true; S.focus('box');
    S.say(OWEN
      ? 'The coil is in arm 1, the resistance and capacitance dials make up arm 2, the fixed resistance is arm 3 and the standard capacitor arm 4. The oscillator feeds the top and bottom corners; the detector listens across the sides.'
      : 'The fixed ratio arm is arm 1 and the resistance dial is arm 2; the unknown capacitor is arm 3 and the standard capacitor arm 4. The oscillator feeds the top and bottom corners; the detector listens across the sides.');
    S.render();
  }
  function switchOsc(on) {
    if (busy()) return Promise.resolve();
    if (on === st.osc) return Promise.resolve();
    return S.hand.tap(osc.rocker, 'front').then(function () {
      st.osc = on; osc.lit(on); S.click(900, 0.05);
      S.say(on ? 'The oscillator is on at ' + fHz(st.f) + ' and the detector has a note to work with.' : 'Oscillator off.');
      S.render();
    });
  }
  function setFreq(f) {
    if (busy()) return Promise.resolve(false);
    if (!(f >= 200 && f <= 5000)) { S.say('This oscillator covers 200 Hz to 5 kHz.'); return Promise.resolve(false); }
    var from = st.f;
    return S.hand.pinchMove(osc.dialAt, function () { return osc.dialAt; },
      function (k) { st.f = from + (f - from) * k; osc.turn(st.f); }, { mode: 'front', ms: 520, reachMs: 540 })
      .then(function () { st.f = f; osc.turn(f); S.say('Oscillator set to ' + fHz(f) + '.'); S.render(); return true; });
  }
  function turnDial(box2, value, what) {
    if (busy()) return Promise.resolve(false);
    if (!(value > 0 && value <= box2.max())) { S.say('That dial goes up to ' + box2.max() + ' ' + box2.unit + ' only.'); return Promise.resolve(false); }
    var want = box2.digitsFor(value), jobs = [];
    want.forEach(function (d, i) { if (Math.abs(box2.dials[i].digit - d) > 1e-9) jobs.push([i, d]); });
    return jobs.reduce(function (pr, j) {
      return pr.then(function () {
        var dl = box2.dials[j[0]], a = dl.digit, b = j[1];
        return S.hand.pinchMove(dl.top, function () { return dl.top; }, function (k) { dl.digit = a + (b - a) * k; box2.look(); },
          { mode: 'top', ms: 320 + 45 * Math.abs(b - a), reachMs: 420 })
          .then(function () { dl.digit = b; box2.look(); S.click(1200, 0.02, 0.05); });
      });
    }, Promise.resolve()).then(function () { S.say(what + ' now reads ' + box2.value() + ' ' + box2.unit + '.'); S.render(); return true; });
  }
  function setRatio(r1) {
    if (busy()) return Promise.resolve(false);
    var from = st.R1;
    return S.hand.pinchMove(TERM.a1[0].at.clone().add(new T.Vector3(0, 0.03, 0)),
      function () { return TERM.a1[0].at.clone().add(new T.Vector3(0, 0.03, 0)); },
      function (k) { st.R1 = from + (r1 - from) * k; }, { mode: 'top', ms: 520, reachMs: 520 })
      .then(function () { st.R1 = r1; S.say('The fixed ratio arm is now ' + r1 + ' ohm.'); S.render(); return true; });
  }
  function hunt() {
    if (busy()) return Promise.resolve(false);
    if (!st.osc) { S.say('Switch the oscillator on first: with no note there is nothing to balance.'); return Promise.resolve(false); }
    S.focus('rdial');
    var rounds = OWEN ? [0, 1, 2, 3] : [0];
    return rounds.reduce(function (pr, i) {
      return pr.then(function () { return turnDial(rDial, bestOf('R2', 1, rDial.max()), 'The resistance dial'); })
        .then(function () { if (!OWEN) return null;
          return turnDial(cDial, bestOf('C2', cDial.step * 1e-6, cDial.max() * 1e-6) * 1e6, 'The capacitance dial'); });
    }, Promise.resolve()).then(function () {
      S.say('The detector is at its quietest: ' + noteText() + '.'); S.render(); return true;
    });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.osc) { S.say('Switch the oscillator on first.'); return false; }
    var i = quiet() * 1e6;
    if (i > 0.6) { S.say('The detector still reads ' + i.toFixed(2) + ' µA. Turn the dials until it is quieter than that.'); return false; }
    var key = OWEN ? st.f : st.R1;
    if (S.rows.some(function (r) { return Math.abs(r.key - key) < 1e-6; })) {
      S.say(OWEN ? 'There is already a balance at ' + fHz(st.f) + '.' : 'There is already a balance with R₁ = ' + st.R1 + ' Ω.');
      return false;
    }
    S.addRow({ key: key, f: st.f, R1: st.R1, R2: rDial.value(), C2: cDial.value(), det: i });
    S.say('Written in your record book: balance at R₂ = ' + rDial.value() + ' Ω' +
      (OWEN ? ', C₂ = ' + cDial.value().toFixed(3) + ' µF, with the oscillator at ' + fHz(st.f) : ' against R₁ = ' + st.R1 + ' Ω') + '.');
    return true;
  }

  function mean(xs) { return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : NaN; }
  function result(rows) {
    if (rows.length < 2) return null;
    if (OWEN) {
      var Ls = rows.map(function (r) { return r.R2 * p.R3 * p.C4; });
      var Rs = rows.map(function (r) { return r.C2 > 0 ? p.R3 * p.C4 / (r.C2 * 1e-6) : NaN; }).filter(isFinite);
      return { label: 'Self-inductance of the coil', value: mean(Ls) * 1000, unit: 'mH', digits: 2,
        truth: p.L1 * 1000,
        note: 'L = R₂ R₃ C₄ with R₃ = ' + Math.round(p.R3) + ' Ω and C₄ = ' +
          (p.C4 * 1e6).toFixed(3) + ' µF. The coil’s own resistance, R₃C₄/C₂, comes out as ' +
          mean(Rs).toFixed(1) + ' Ω. The balances at ' + rows.length +
          ' different frequencies give the same inductance, which is the point of Owen’s bridge.' };
    }
    var Cs = rows.map(function (r) { return p.C4 * r.R2 / r.R1; });
    var spread = (Math.max.apply(null, Cs) - Math.min.apply(null, Cs)) / mean(Cs) * 100;
    return { label: 'The unknown capacitance', value: mean(Cs) * 1e6, unit: 'µF', digits: 4,
      truth: p.C3 * 1e6,
      note: 'C₃ = C₄ R₂/R₁ with the standard capacitor at ' + (p.C4 * 1e6).toFixed(3) +
        ' µF. The ' + rows.length + ' balances at different ratio arms agree to ' + spread.toFixed(2) +
        ' per cent, and none of them contains the frequency.' };
  }

  /* ---------------------------------------------------------------- steps */
  var SETTINGS = OWEN ? F_SETTINGS : R1_SETTINGS;
  return {
    camera: { pos: [0.0, 0.92, 0.84], look: [0, 0.04, -0.16] },
    views: { bench: [[0.0, 0.92, 0.84], [0, 0.04, -0.16]], box: [[0.0, 0.52, 0.16], [0, 0.05, -0.26]],
      osc: [[-0.4, 0.44, -0.1], [-0.52, 0.07, -0.46]], det: [[0.46, 0.42, -0.08], [0.5, 0.06, -0.42]],
      meter: [[0.26, 0.3, 0.26], [0.26, 0.05, 0.0]], rdial: [[-0.3, 0.3, 0.38], [-0.3, 0.03, 0.1]],
      cdial: [[0.04, 0.3, 0.4], [0.04, 0.03, 0.12]], book: [[-0.62, 0.46, 0.5], [-0.62, 0.0, 0.08]] },
    theory: {
      principle: S.lab.theory,
      formula: OWEN ? 'L₁ = R₂ R₃ C₄,   R₁ = R₃ C₄ / C₂'
        : 'C₃ = C₄ R₂ / R₁',
      formulaNote: 'the balance is hunted on the detector, and the formula only turns it into the answer',
      more: [
        'A bridge is balanced when the products of opposite arms are equal. That is one equation between complex numbers, so it is really two equations - one for the in-phase part and one for the quadrature part - and a bridge with a coil in it therefore needs two dials.',
        'A null method is accurate because nothing has to be calibrated except the standard arm: the detector only has to tell loud from quiet, and the ear is very good at that. The oscillator’s amplitude does not enter the answer at all.',
        OWEN ? 'Neither answer from Owen’s bridge contains the frequency, so balancing again at another frequency is a real check on the work rather than a repetition.'
          : 'The balance of De Sauty’s bridge contains no frequency either, so changing the ratio arm and balancing again is a real check. The simple form assumes both capacitors are loss-free.'],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, at: [-0.62, 0.08, 0.12],
      lines: OWEN
        ? ['Aim: to find the self-inductance of a coil', 'with Owen\'s bridge.',
          'Arm 1 the coil, arm 2 R2 in series with C2,', 'arm 3 R3 fixed, arm 4 the standard capacitor C4.',
          'L1 = R2 R3 C4,   R1 = R3 C4 / C2']
        : ['Aim: to compare two capacitances', 'with De Sauty\'s bridge.',
          'Arms 1 and 2 resistive, arms 3 and 4 the capacitors.', 'C3 = C4 R2 / R1',
          'The balance does not contain the frequency.'],
      columns: OWEN
        ? [{ label: 'S.No', get: function (r, i) { return i + 1; } },
          { label: 'f (Hz)', get: function (r) { return Math.round(r.f); } },
          { label: 'R₂ (Ω)', get: function (r) { return r.R2; } },
          { label: 'C₂ (µF)', get: function (r) { return r.C2.toFixed(3); } },
          { label: 'L (mH)', get: function (r) { return (r.R2 * p.R3 * p.C4 * 1000).toFixed(2); } }]
        : [{ label: 'S.No', get: function (r, i) { return i + 1; } },
          { label: 'R₁ (Ω)', get: function (r) { return r.R1; } },
          { label: 'R₂ (Ω)', get: function (r) { return r.R2; } },
          { label: 'Detector (µA)', get: function (r) { return r.det.toFixed(2); } },
          { label: 'C₃ (µF)', get: function (r) { return (p.C4 * r.R2 / r.R1 * 1e6).toFixed(4); } }] },
    graph: OWEN
      ? { x: function (r) { return r.f; }, y: function (r) { return r.R2 * p.R3 * p.C4 * 1000; },
        xlabel: 'f (Hz)', ylabel: 'L (mH)', x0: 0, y0: 0 }
      : { x: function (r) { return r.R1; }, y: function (r) { return r.R2; }, xlabel: 'R₁ (Ω)', ylabel: 'R₂ (Ω)', x0: 0, y0: 0 },
    result: result,
    tol: 0.02,
    resultNote: OWEN
      ? 'The inductance comes out the same at every frequency, which is what separates Owen’s bridge from the bridges whose balance drifts with the oscillator.'
      : 'Every ratio arm gives the same capacitance, and none of the answers contains the frequency: that is the mark of a properly balanced bridge.',
    chips: OWEN ? ['Why are two dials needed?', 'Check my readings', 'Why change the frequency?', 'What does the capacitance dial measure?']
      : ['Why is a null method accurate?', 'Check my readings', 'Why change the ratio arm?', 'What if a capacitor is lossy?'],
    viva: OWEN
      ? [['Owen’s bridge needs two dials because', ['A coil has resistance as well as reactance', 'The oscillator drifts', 'The ear is not sensitive'], 0, 'Both parts of the detector current must be killed.'],
        ['The inductance from Owen’s bridge depends on the frequency', ['Not at all', 'Directly', 'Inversely'], 0, 'L = R₂R₃C₄ has no ω in it.'],
        ['The coil’s own resistance comes from', ['The capacitance dial', 'The resistance dial', 'The null meter'], 0, 'R₁ = R₃C₄/C₂.']]
      : [['De Sauty’s bridge balances when', ['C₃ = C₄R₂/R₁', 'C₃ = C₄R₁/R₂', 'C₃ = C₄R₁R₂'], 0, 'Equal products of opposite arms.'],
        ['Its balance depends on the frequency', ['Not at all', 'Directly', 'As its square'], 0, 'ω cancels from both sides.'],
        ['A lossy capacitor in the bridge', ['Stops a true null being reached', 'Makes no difference', 'Doubles the reading'], 0, 'Its loss resistance has to be balanced too.']],
    askState: function () {
      return { experiment: S.lab.title, oscillator_on: st.osc, oscillator_frequency_hz: st.f,
        ratio_arm_R1_ohm: st.R1, resistance_dial_R2_ohm: rDial.value(),
        capacitance_dial_C2_uF: cDial.value(), detector: noteText(), balances_recorded: S.rows.length };
    },
    steps: [
      { id: 'setup', title: 'Set up', view: 'box', render: function (u) {
          u.h2('Set the bridge up');
          u.p(OWEN ? 'The coil goes into arm 1, the two dials make up arm 2, the fixed resistance is arm 3 and the standard capacitor arm 4.'
            : 'The unknown capacitor goes into arm 3 and the standard capacitor into arm 4; arms 1 and 2 are the two resistances.');
          u.task('1. Trace the bridge', st.traced, st.traced ? 'Four arms, oscillator across one diagonal, detector across the other' : 'Follow the leads from the oscillator')
            .add(u.button(st.traced ? 'Traced' : 'Trace the bridge', trace, !st.traced, st.traced));
          u.task('2. Switch the oscillator on', st.osc, st.osc ? 'On at ' + fHz(st.f) : 'The oscillator is off')
            .add(u.row(u.button(st.osc ? 'Oscillator is on' : 'Switch the oscillator on', function () { S.focus('osc'); switchOsc(true); }, !st.osc, st.osc || S.hand.busy),
              u.button('Set it to 1 kHz', function () { setFreq(1000); }, false, S.hand.busy)));
          u.live(function () { return 'Oscillator ' + (st.osc ? fHz(st.f) : 'off') + '  ·  detector: ' + noteText(); });
          u.note('Turn the detector’s gain down before putting the headphones on, and keep the oscillator at one frequency while you balance.');
          u.next('Next: balance the bridge', st.traced && st.osc);
        },
        ok: function () { return st.traced && st.osc; },
        auto: function () { trace(); return switchOsc(true).then(function () { return setFreq(1000); }); } },
      { id: 'balance', title: 'Balance', view: 'rdial', render: function (u) {
          u.h2(OWEN ? 'Balance the bridge at three frequencies' : 'Balance the bridge against three ratio arms');
          u.p(OWEN ? 'Turn the resistance dial for the quietest note, then the capacitance dial, and go back and forth until the detector is silent. Record the balance, then change the frequency and do it again.'
            : 'Turn the resistance dial until the note dies away, record the balance, then change the fixed ratio arm and balance again.');
          var row = u.row();
          SETTINGS.forEach(function (v) {
            var done = S.rows.some(function (r) { return Math.abs(r.key - v) < 1e-6; });
            row.appendChild(u.button((OWEN ? fHz(v) : v + ' Ω') + (done ? ' ✓' : ''), function () {
              (OWEN ? setFreq(v) : setRatio(v)); }, (OWEN ? st.f : st.R1) === v, S.hand.busy));
          });
          var sl = { v: rDial.value() };
          u.slider('Resistance dial R₂', 1, 9999, 1, function () { return sl.v; }, function (v) { sl.v = v; }, 'Ω', 0);
          u.row(u.button('Turn the dial here', function () { turnDial(rDial, sl.v, 'The resistance dial'); }, false, S.hand.busy),
            u.button('Hunt for the balance', function () { hunt(); }, true, S.hand.busy));
          if (OWEN) {
            var sc = { v: cDial.value() };
            u.slider('Capacitance dial C₂', 0.01, 9.999, 0.001, function () { return sc.v; }, function (v) { sc.v = v; }, 'µF', 3);
            u.row(u.button('Turn the capacitance dial here', function () { turnDial(cDial, sc.v, 'The capacitance dial'); }, false, S.hand.busy));
          }
          u.row(u.button('Record this balance', function () { record(); }, true, S.hand.busy));
          u.live(function () { return 'R₂ = ' + rDial.value() + ' Ω' + (OWEN ? ', C₂ = ' + cDial.value().toFixed(3) + ' µF' : ', R₁ = ' + st.R1 + ' Ω') +
            '  ·  ' + noteText(); });
          u.h3('Observation table'); u.table();
          u.next('Next: the result', S.rows.length >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          return SETTINGS.reduce(function (pr, v) {
            return pr.then(function () { return OWEN ? setFreq(v) : setRatio(v); })
              .then(hunt).then(function () { record(); });
          }, Promise.resolve());
        } }
    ],
    tick: function () {
      osc.show(st.f, st.osc);
      nullMeter.set(Math.min(50, quiet() * 1e6));
      hudA.set(st.osc ? (quiet() * 1e6).toFixed(2) + ' µA' : 'off');
      hudB.set(rDial.value() + ' Ω');
      hudC.set(OWEN ? cDial.value().toFixed(3) + ' µF' : st.R1 + ' Ω');
    }
  };
});
