/* Prayogshala studio module: the SEMICONDUCTOR BENCH (NCERT Class XII, Section B). One apparatus, two set-ups:
     zener-characteristic           - the reverse characteristic of a Zener diode and its breakdown voltage,
     transistor-ce-characteristics  - an n-p-n transistor in common emitter and its current gain.
   A breadboard with the components pushed into it, variable DC supplies whose knobs the hand turns, and digital
   multimeters with real LCD read-outs. Every number comes from this lab's kernel (packs/elec11.js: the Zener's
   Shockley forward branch with a rounded breakdown knee, or the transistor's base and collector loops solved by
   bisection) - the same code the server checks against the textbook formula. */
HoolaStudio.define('semiconductor-board', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels;
  var ID = S.lab.id || '', MODE = /zener/.test(ID) ? 'zener' : 'trans';
  var KN = HK.K[MODE === 'zener' ? 'zener' : 'transistor'];
  var p = HK.paramsFor(MODE === 'zener' ? 'zener' : 'transistor', S.lab.params);
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || '';
  var PART = (SAMPLE.match(/\b(1N\d{4}A?|BC\d{3}[ABC]?|2N\d{4}A?)\b/i) || [])[0] || (MODE === 'zener' ? '1N4733A' : 'P2N2222A');
  var VCE_SET = 4.0;                                   // the fixed collector voltage the transistor readings are taken at
  var st = { traced: false, main: false, aux: false, E: 0, Eaux: 0.6 };

  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function arr(v) { return [v.x, v.y, v.z]; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }

  // ---------------------------------------------------------------- variable DC power supply (knob, rocker, lamp, posts)
  function supply(x, z, vmax, title, ry) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = ry || 0;
    var W = 0.2, H = 0.1, D = 0.14;
    var cs = S.rounded(W, D, H, 0.01, new T.MeshStandardMaterial({ color: 0xd9d5cb, roughness: 0.5, metalness: 0.15 }));
    cs.rotation.x = -Math.PI / 2; cs.position.y = H / 2 + 0.004; g.add(cs);
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) { var ft = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.004, 14), M.rubber);
      ft.position.set(f[0] * (W / 2 - 0.018), 0.002, f[1] * (D / 2 - 0.018)); g.add(ft); });
    var FZ = D / 2 + 0.006, PW = W - 0.012, PH = H - 0.012, KX = -0.03, KY = -0.006;
    var tex = S.canvasTex(1000, Math.round(1000 * PH / PW), function (c, w, h) {
      var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; }, k = w / PW;
      c.fillStyle = '#2b323d'; c.fillRect(0, 0, w, h);
      c.strokeStyle = 'rgba(255,255,255,.12)'; c.lineWidth = 3; c.strokeRect(9, 9, w - 18, h - 18);
      c.fillStyle = '#f1efe8'; c.font = '700 ' + Math.round(k * 0.013) + 'px "Public Sans", sans-serif'; c.textAlign = 'left';
      c.fillText(title, 26, Math.round(k * 0.019));
      c.font = '500 ' + Math.round(k * 0.009) + 'px "Public Sans", sans-serif'; c.fillStyle = '#c7ccd6';
      c.fillText('0 – ' + vmax + ' V  ·  0.5 A max', 26, Math.round(k * 0.03));
      var cx = X(KX), cy = Y(KY), R = 0.021 * k;
      c.strokeStyle = '#f1efe8'; c.fillStyle = '#f1efe8'; c.textAlign = 'center';
      for (var i = 0; i <= 20; i++) { var th = (225 - 270 * i / 20) * Math.PI / 180, big = i % 5 === 0;
        c.lineWidth = big ? 4 : 2; c.beginPath(); c.moveTo(cx + Math.cos(th) * R, cy - Math.sin(th) * R);
        c.lineTo(cx + Math.cos(th) * (R + (big ? 20 : 11)), cy - Math.sin(th) * (R + (big ? 20 : 11))); c.stroke();
        if (big) { c.font = '600 ' + Math.round(k * 0.0075) + 'px "Public Sans", sans-serif';
          c.fillText(String(Math.round(vmax * i / 20)), cx + Math.cos(th) * (R + 42), cy - Math.sin(th) * (R + 42) + k * 0.003); } }
      c.font = '700 ' + Math.round(k * 0.008) + 'px "Public Sans", sans-serif'; c.fillText('VOLTAGE', cx, Y(-0.04));
      c.fillText('POWER', X(-0.082), Y(-0.04));
      c.font = '700 ' + Math.round(k * 0.012) + 'px "Public Sans", sans-serif';
      c.fillStyle = '#9aa3b2'; c.fillText('−', X(0.052), Y(-0.034)); c.fillStyle = '#ff7a6b'; c.fillText('+', X(0.082), Y(-0.034));
      c.textAlign = 'left';
    });
    var fascia = S.mesh(new T.BoxGeometry(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]);
    fascia.position.set(0, 0.004 + H / 2, FZ - 0.002); g.add(fascia);
    function pp(u, v, dz) { return new T.Vector3(u, 0.004 + H / 2 + v, FZ + (dz || 0)); }
    var knurl = S.canvasTex(256, 32, function (c, w, h) { c.fillStyle = '#16171a'; c.fillRect(0, 0, w, h); c.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) c.fillRect(i, 0, 3, h); });
    var knob = new T.Group(); knob.position.copy(pp(KX, KY)); g.add(knob);
    var skirt = S.mesh(new T.CylinderGeometry(0.016, 0.017, 0.004, 32), M.bakelite); skirt.rotation.x = Math.PI / 2; skirt.position.z = 0.002; knob.add(skirt);
    var kb = S.mesh(new T.CylinderGeometry(0.0125, 0.0135, 0.014, 32), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.011; knob.add(kb);
    var kc = S.mesh(new T.CylinderGeometry(0.0115, 0.0115, 0.0015, 32), M.chrome); kc.rotation.x = Math.PI / 2; kc.position.z = 0.0185; knob.add(kc);
    var ptr = S.mesh(new T.BoxGeometry(0.002, 0.014, 0.0012), M.white, false); ptr.position.set(0, 0.008, 0.0195); knob.add(ptr);
    var rocker = S.rounded(0.014, 0.02, 0.008, 0.003, M.bakelite); rocker.position.copy(pp(-0.082, -0.016, 0.004)); g.add(rocker);
    var lampM = new T.MeshStandardMaterial({ color: 0x5a1410, roughness: 0.3 });
    var lamp = S.mesh(new T.SphereGeometry(0.005, 18, 12, 0, Math.PI * 2, 0, Math.PI / 2), lampM); lamp.rotation.x = Math.PI / 2; lamp.position.copy(pp(-0.082, 0.012, 0)); g.add(lamp);
    function postAt(u, mat) { var pg = new T.Group(); pg.position.copy(pp(u, -0.012)); g.add(pg);
      var stem = S.mesh(new T.CylinderGeometry(0.0026, 0.0026, 0.018, 14), M.brass); stem.rotation.x = Math.PI / 2; stem.position.z = 0.009; pg.add(stem);
      var cap = S.mesh(new T.CylinderGeometry(0.007, 0.008, 0.011, 20), mat); cap.rotation.x = Math.PI / 2; cap.position.z = 0.011; pg.add(cap); return pg; }
    var pNeg = postAt(0.052, M.blackPlastic), pPos = postAt(0.082, M.red);
    S.contact(W + 0.08, D + 0.08, x, z, 0.55);
    var api = { group: g, knob: knob, rocker: rocker, vmax: vmax, on: false, set: 0,
      angle: function (v) { return 3 * Math.PI / 4 - 1.5 * Math.PI * (v / vmax); },
      plus: wpt(pPos, 0, 0, 0.012), minus: wpt(pNeg, 0, 0, 0.012),
      front: function () { return wpt(knob, 0, 0, 0.008); },
      look: function () { knob.rotation.z = api.angle(api.set); rocker.rotation.x = api.on ? -0.22 : 0.22;
        lampM.color.setHex(api.on ? 0xff3b2a : 0x5a1410); lampM.emissive = new T.Color(api.on ? 0xff2a14 : 0x000000); lampM.emissiveIntensity = api.on ? 2.2 : 0; } };
    api.look();
    return api;
  }

  // ---------------------------------------------------------------- digital multimeter (real LCD read-out)
  function dmm(x, z, title, ry) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = ry || 0;
    var W = 0.1, D = 0.14, H = 0.03;
    var body = S.rounded(W, D, H, 0.008, new T.MeshStandardMaterial({ color: 0xe0a93c, roughness: 0.55 }));
    body.rotation.x = -Math.PI / 2; body.position.y = H / 2; g.add(body);
    var face = S.mesh(new T.BoxGeometry(W - 0.01, 0.002, D - 0.01), M.bakelite); face.position.y = H + 0.001; g.add(face);
    var lcd = S.liveTex(512, 220), last = '';
    var scr = new T.Mesh(new T.PlaneGeometry(W - 0.022, 0.03), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
    scr.rotation.x = -Math.PI / 2; scr.position.set(0, H + 0.0025, -D / 2 + 0.028); g.add(scr);
    var bez = S.mesh(new T.BoxGeometry(W - 0.016, 0.003, 0.036), M.grey); bez.position.set(0, H + 0.0015, -D / 2 + 0.028); g.add(bez);
    var sel = new T.Group(); sel.position.set(0, H + 0.004, 0.012); g.add(sel);
    var sb = S.mesh(new T.CylinderGeometry(0.016, 0.017, 0.008, 28), M.blackPlastic); sel.add(sb);
    var sp = S.mesh(new T.BoxGeometry(0.003, 0.002, 0.014), M.white, false); sp.position.set(0, 0.005, -0.008); sel.add(sp);
    var ring = S.canvasTex(256, 256, function (c, w, h) { c.clearRect(0, 0, w, h); c.strokeStyle = '#f0e9d8'; c.fillStyle = '#f0e9d8';
      c.font = '700 20px "Public Sans", sans-serif'; c.textAlign = 'center';
      ['V', 'mA', 'Ω', 'OFF', 'A', 'µA'].forEach(function (t, i) { var a = i * Math.PI / 3 - Math.PI / 2;
        c.fillText(t, w / 2 + Math.cos(a) * 96, h / 2 + Math.sin(a) * 96 + 7); }); });
    var rp = new T.Mesh(new T.PlaneGeometry(0.062, 0.062), new T.MeshStandardMaterial({ map: ring, transparent: true, roughness: 0.6 }));
    rp.rotation.x = -Math.PI / 2; rp.position.set(0, H + 0.0022, 0.012); g.add(rp);
    [-0.024, 0, 0.024].forEach(function (sx) { var sk = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.004, 16), sx < 0 ? M.blackPlastic : M.red);
      sk.position.set(sx, H + 0.001, D / 2 - 0.016); g.add(sk); });
    S.contact(W + 0.06, D + 0.06, x, z, 0.5);
    var api = { group: g, top: wpt(g, 0, H + 0.02, 0),
      show: function (txt, sub) { if (txt + sub === last) return; last = txt + sub;
        lcd.draw(function (c) { var gr = c.createLinearGradient(0, 0, 0, 220); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
          c.fillStyle = gr; c.fillRect(0, 0, 512, 220);
          c.font = '700 110px "JetBrains Mono", monospace'; c.textAlign = 'right'; c.fillStyle = 'rgba(0,0,0,.07)'; c.fillText('8.8.8.8.', 430, 132);
          c.fillStyle = '#1b2116'; c.fillText(txt, 430, 132);
          c.font = '600 42px "Public Sans", sans-serif'; c.textAlign = 'left'; c.fillText(sub, 20, 198);
          c.textAlign = 'right'; c.font = '600 30px "Public Sans", sans-serif'; c.fillText(title, 492, 198); }); } };
    api.show('----', '');
    return api;
  }

  // ---------------------------------------------------------------- the breadboard and the components on it
  var BX = 0.0, BZ = -0.08, BW = 0.3, BD = 0.17, BT = 0.014, LY = BT + 0.006;
  var bb = new T.Group(); S.scene.add(bb);
  var holes = S.canvasTex(1024, 580, function (c, w, h) {
    c.fillStyle = '#efece2'; c.fillRect(0, 0, w, h);
    c.fillStyle = '#bdb8aa'; c.fillRect(0, h * 0.47, w, 3);
    for (var r = 0; r < 10; r++) for (var i = 0; i < 46; i++) {
      var yy = h * (0.08 + r * 0.038 + (r > 4 ? 0.1 : 0)), xx = 24 + i * (w - 48) / 45;
      c.fillStyle = '#2b2b2e'; c.fillRect(xx - 3, yy - 3, 6, 6); }
    c.strokeStyle = '#c0392b'; c.lineWidth = 3; c.beginPath(); c.moveTo(20, 16); c.lineTo(w - 20, 16); c.stroke();
    c.strokeStyle = '#2c5fb4'; c.beginPath(); c.moveTo(20, h - 16); c.lineTo(w - 20, h - 16); c.stroke(); });
  var bbody = S.rounded(BW, BD, BT, 0.004, new T.MeshStandardMaterial({ color: 0xf2efe6, roughness: 0.6 }));
  bbody.rotation.x = -Math.PI / 2; bbody.position.set(BX, BT / 2, BZ); bb.add(bbody);
  var bface = new T.Mesh(new T.PlaneGeometry(BW - 0.006, BD - 0.006), new T.MeshStandardMaterial({ map: holes, roughness: 0.65 }));
  bface.rotation.x = -Math.PI / 2; bface.position.set(BX, BT + 0.0004, BZ); bb.add(bface);
  S.scene.add(bb); S.contact(BW + 0.07, BD + 0.07, BX, BZ, 0.5);
  var leadM = new T.MeshStandardMaterial({ color: 0xcfd3d6, roughness: 0.25, metalness: 1 });
  function rod(a, b, r, mat) { var d = b.clone().sub(a), m = S.mesh(new T.CylinderGeometry(r, r, d.length(), 8), mat || leadM);
    m.position.copy(a).add(b).multiplyScalar(0.5); m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize()); S.scene.add(m); return m; }
  function resistor(cx, cz, bands, label) {
    var g = new T.Group(); S.scene.add(g);
    var tex = S.canvasTex(64, 512, function (c, w, h) { c.fillStyle = '#d9bf8c'; c.fillRect(0, 0, w, h);
      bands.concat(['#c9a23a']).forEach(function (col, i) { c.fillStyle = col; c.fillRect(0, h * (0.74 - i * 0.13) - 20, w, 40); }); });
    var body = S.mesh(new T.CylinderGeometry(0.0028, 0.0028, 0.016, 20), new T.MeshStandardMaterial({ map: tex, roughness: 0.55 }));
    body.rotation.z = Math.PI / 2; g.add(body);
    g.position.set(cx, LY, cz);
    rod(new T.Vector3(cx - 0.008, LY, cz), new T.Vector3(cx - 0.03, BT, cz), 0.0004);
    rod(new T.Vector3(cx + 0.008, LY, cz), new T.Vector3(cx + 0.03, BT, cz), 0.0004);
    var lb = S.label(label, { w: 0.05, ratio: 0.22, px: 512, color: '#3a3528' }); lb.rotation.x = -Math.PI / 2;
    lb.position.set(cx, BT + 0.0008, cz + 0.016); S.scene.add(lb);
    return g;
  }
  var BAND = { 0: '#111111', 1: '#6b3a1e', 2: '#c4231c', 3: '#e8761e', 4: '#e9c81a', 5: '#2c8a3a', 6: '#2747a8', 9: '#f2f2f2' };
  var zener = null, tr = null;
  if (MODE === 'zener') {
    resistor(-0.085, BZ - 0.03, [BAND[1], BAND[0], BAND[2]], (p.Rs >= 1000 ? (p.Rs / 1000) + ' kΩ' : p.Rs + ' Ω'));
    zener = new T.Group(); S.scene.add(zener);
    var zt = S.canvasTex(256, 512, function (c, w, h) { c.fillStyle = '#1a1a1c'; c.fillRect(0, 0, w, h);
      c.fillStyle = '#d7dade'; c.fillRect(0, h * 0.08, w, h * 0.16);
      c.save(); c.translate(w * 0.5, h * 0.62); c.rotate(Math.PI / 2); c.fillStyle = '#9da3aa';
      c.font = '700 58px "Public Sans", sans-serif'; c.textAlign = 'center'; c.fillText(PART, 0, 20); c.restore(); });
    var zb = S.mesh(new T.CylinderGeometry(0.0026, 0.0026, 0.011, 24), new T.MeshStandardMaterial({ map: zt, roughness: 0.35 }));
    zb.rotation.z = -Math.PI / 2; zener.add(zb);              // the band end (-x of the texture) faces +x here: cathode to the + side
    zener.position.set(0.055, LY, BZ - 0.03);
    rod(new T.Vector3(0.0495, LY, BZ - 0.03), new T.Vector3(0.028, BT, BZ - 0.03), 0.0004);
    rod(new T.Vector3(0.0605, LY, BZ - 0.03), new T.Vector3(0.085, BT, BZ - 0.03), 0.0004);
    var zl = S.label('Zener  ' + PART + '  (reverse bias)', { w: 0.1, ratio: 0.13, px: 512, color: '#3a3528' });
    zl.rotation.x = -Math.PI / 2; zl.position.set(0.055, BT + 0.0008, BZ - 0.012); S.scene.add(zl);
  } else {
    resistor(-0.085, BZ + 0.035, [BAND[1], BAND[0], BAND[4]], '100 kΩ  (base)');
    resistor(0.085, BZ - 0.045, [BAND[1], BAND[0], BAND[2]], '1 kΩ  (collector)');
    tr = new T.Group(); S.scene.add(tr);
    var cap = S.mesh(new T.CylinderGeometry(0.0046, 0.0046, 0.005, 24, 1, false, -Math.PI / 2, Math.PI), M.blackPlastic);
    cap.rotation.x = Math.PI / 2; cap.position.z = 0.0; tr.add(cap);
    var flat = S.mesh(new T.BoxGeometry(0.0092, 0.005, 0.0012), M.blackPlastic); flat.position.z = -0.0006; tr.add(flat);
    var tl = S.label(PART, { w: 0.008, ratio: 0.45, px: 256, color: '#c9ccd0' }); tl.position.set(0, 0, -0.0014); tr.add(tl);
    tr.position.set(0.0, BT + 0.0075, BZ - 0.005);
    [-0.0025, 0, 0.0025].forEach(function (dx) { rod(new T.Vector3(dx, BT + 0.005, BZ - 0.005), new T.Vector3(dx * 3, BT - 0.002, BZ - 0.005), 0.00035); });
    var trl = S.label('n-p-n  ' + PART + '   E  B  C', { w: 0.09, ratio: 0.13, px: 512, color: '#3a3528' });
    trl.rotation.x = -Math.PI / 2; trl.position.set(0.0, BT + 0.0008, BZ + 0.012); S.scene.add(trl);
  }

  // ---------------------------------------------------------------- supplies and meters
  var main = supply(-0.44, -0.42, MODE === 'zener' ? 15 : 12, MODE === 'zener' ? 'REVERSE BIAS SUPPLY' : 'COLLECTOR SUPPLY  Vcc', 0.22);
  var aux = MODE === 'trans' ? supply(0.46, -0.42, 5, 'BASE SUPPLY  Vbb', -0.22) : null;
  var mV = dmm(MODE === 'zener' ? 0.3 : 0.26, -0.56, MODE === 'zener' ? 'VOLTS DC' : 'Vce  VOLTS', -0.12);
  var mA = dmm(MODE === 'zener' ? -0.08 : -0.06, -0.58, MODE === 'zener' ? 'mA  DC' : 'Ic  mA', 0.0);
  var mB = MODE === 'trans' ? dmm(-0.36, -0.54, 'Ib  µA', 0.14) : null;

  function wire(a, b, color, via) {
    var pts = [arr(a), [a.x, a.y + 0.02, a.z]];
    (via || []).forEach(function (v) { pts.push([v[0], 0.006, v[1]]); });
    pts.push([b.x, b.y + 0.02, b.z], arr(b));
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }
  function bbPin(x, z) { return new T.Vector3(x, BT + 0.004, z); }
  if (MODE === 'zener') {
    wire(main.plus, bbPin(-0.115, BZ - 0.03), 'red', [[-0.3, -0.28], [-0.16, -0.14]]);
    wire(bbPin(-0.055, BZ - 0.03), mA.top, '#d9a520', [[-0.1, -0.34]]);
    wire(mA.top, bbPin(0.028, BZ - 0.03), '#d9a520', [[0.0, -0.36]]);
    wire(bbPin(0.085, BZ - 0.03), main.minus, 'black', [[0.14, -0.22], [-0.2, -0.3]]);
    wire(bbPin(0.028, BZ - 0.03), mV.top, 'blue', [[0.16, -0.3]]);
    wire(bbPin(0.085, BZ - 0.03), mV.top, 'blue', [[0.2, -0.24]]);
  } else {
    wire(aux.plus, mB.top, '#d9a520', [[0.3, -0.5]]);
    wire(mB.top, bbPin(-0.115, BZ + 0.035), '#d9a520', [[-0.3, -0.36]]);
    wire(bbPin(-0.055, BZ + 0.035), bbPin(0.0, BZ - 0.005), '#d9a520', []);
    wire(main.plus, bbPin(0.115, BZ - 0.045), 'red', [[-0.26, -0.26], [0.1, -0.2]]);
    wire(bbPin(0.055, BZ - 0.045), mA.top, 'red', [[0.02, -0.34]]);
    wire(mA.top, bbPin(0.0075, BZ - 0.005), 'red', [[-0.02, -0.26]]);
    wire(bbPin(-0.0075, BZ - 0.005), main.minus, 'black', [[-0.1, -0.2], [-0.26, -0.3]]);
    wire(bbPin(-0.0075, BZ - 0.005), aux.minus, 'black', [[0.1, -0.16], [0.3, -0.34]]);
    wire(bbPin(0.0075, BZ - 0.005), mV.top, 'blue', [[0.14, -0.3]]);
    wire(bbPin(-0.0075, BZ - 0.005), mV.top, 'blue', [[0.2, -0.26]]);
  }

  S.addApparatus('bb', bb, 'Breadboard', 'The components are pushed into its rows of contacts, which join them underneath.');
  S.addApparatus('main', main.group, MODE === 'zener' ? 'Reverse-bias supply (0–15 V)' : 'Collector supply Vcc (0–12 V)',
    'Turn the VOLTAGE knob to change the voltage applied to the circuit.');
  if (aux) S.addApparatus('aux', aux.group, 'Base supply Vbb (0–5 V)', 'Sets the base current through the 100 kΩ resistor.');
  S.addApparatus('mv', mV.group, MODE === 'zener' ? 'Digital voltmeter' : 'Digital voltmeter (V_CE)',
    MODE === 'zener' ? 'Across the Zener diode. It reads to 0.01 V.' : 'Across the collector and the emitter. It reads to 0.01 V.');
  S.addApparatus('ma', mA.group, MODE === 'zener' ? 'Digital milliammeter' : 'Digital milliammeter (I_C)', 'In series with the diode or the collector. It reads to 0.01 mA.');
  if (mB) S.addApparatus('mb', mB.group, 'Digital microammeter (I_B)', 'In series with the base resistor. It reads to 0.1 µA.');
  if (zener) S.addApparatus('zd', zener, 'Zener diode ' + PART, 'The silver band is the cathode. Here it faces the positive terminal, so the diode is in reverse bias.');
  if (tr) S.addApparatus('tr', tr, 'n-p-n transistor ' + PART, 'Three leads: emitter, base and collector. The flat face carries the type number.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ---------------------------------------------------------------- physics
  function view(over) { var q = HK.assign(p, over || {}); return KN.view(KN.init(q, q), q, q); }
  function now() {
    if (MODE === 'zener') { if (!main.on) return { V: 0, I: 0 }; var v = view({ Eb: -main.set }); return { V: -v.V_Z, I: -v.I_Z }; }
    if (!main.on || !aux.on) return { Ib: 0, Ic: 0, Vce: 0, Vbe: 0 };
    var w = view({ Vcc: main.set, Vbb: aux.set });
    return { Ib: w.I_b, Ic: w.I_c, Vce: w.V_ce, Vbe: w.V_be };
  }
  function readV() { return rnd(now().V, 2); }
  function readI() { return rnd(now().I * 1000, 2); }
  function readIb() { return rnd(now().Ib * 1e6, 1); }
  function readIc() { return rnd(now().Ic * 1000, 2); }
  function readVce() { return rnd(now().Vce, 2); }
  var hudA = S.hudCard(MODE === 'zener' ? 'Supply setting' : 'Base supply'), hudB = S.hudCard(MODE === 'zener' ? 'Voltmeter' : 'I_B'),
    hudC = S.hudCard(MODE === 'zener' ? 'Milliammeter' : 'I_C / V_CE');

  // ---------------------------------------------------------------- human actions
  function trace() {
    st.traced = true; S.focus('bb');
    S.say(MODE === 'zener' ? 'Supply plus, the 1 kΩ resistor, the milliammeter and the Zener diode are in series; the diode\'s banded end faces the plus side, so it is in reverse bias. The voltmeter is across the diode alone.'
      : 'The base supply drives the base through 100 kΩ with the microammeter in series; the collector supply drives the collector through 1 kΩ with the milliammeter in series; the voltmeter reads from collector to emitter.');
    S.render();
  }
  function turn(s, v, name) {
    if (busy()) return Promise.resolve();
    if (!isFinite(v) || v < 0 || v > s.vmax + 1e-9) { S.say('The ' + name + ' goes from 0 to ' + s.vmax + ' V only.'); return Promise.resolve(); }
    v = rnd(clamp(v, 0, s.vmax), 2);
    var v0 = s.set, a0 = s.angle(v0), pt = s.front();
    if (Math.abs(v - v0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      s.set = v0 + (v - v0) * k; s.look(); S.hand.group.rotation.y = -(s.angle(s.set) - a0) * 0.3; },
      { mode: 'front', ms: 420 + 320 * Math.abs(v - v0) / s.vmax, reachMs: 600 })
      .then(function () { s.set = v; s.look(); S.hand.group.rotation.y = 0; S.render(); });
  }
  function power(s, on, name) {
    if (busy()) return Promise.resolve();
    if (on === s.on) return Promise.resolve();
    if (on && s.set > 0.001) { S.say('Turn the ' + name + ' knob back to zero before switching on.'); return Promise.resolve(); }
    return S.hand.tap(s.rocker, 'front').then(function () { s.on = on; s.look(); S.click(900, 0.05);
      S.say(name + (on ? ' switched on.' : ' switched off.')); S.render(); });
  }
  // the base settings that keep the collector current inside the milliammeter's range for THIS transistor
  function vbbFor(ibWant) {
    var lo = 0.3, hi = aux ? aux.vmax : 5, i, mid;
    for (i = 0; i < 60; i++) { mid = (lo + hi) / 2; if (view({ Vbb: mid }).I_b > ibWant) hi = mid; else lo = mid; }
    return rnd((lo + hi) / 2, 2);
  }
  function baseList() {
    var icMax = 0.005, ibMax = icMax / (1.05 * p.beta);
    return [0.25, 0.45, 0.65, 0.82, 1.0].map(function (f) { return Math.round(vbbFor(ibMax * f) / 0.05) * 0.05; });
  }
  // what a student does: turn the collector knob until the voltmeter reads 4.00 V
  function setVce(target) {
    var want = main.set;
    for (var i = 0; i < 40; i++) {
      var w = view({ Vcc: want, Vbb: aux.set });
      var err = target - w.V_ce;
      if (Math.abs(err) < 0.0005) break;
      want = clamp(want + err, 0, main.vmax);
    }
    return turn(main, rnd(want, 2), 'collector supply');
  }

  function recordZener() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!main.on) { S.say('Switch the supply on first.'); return false; }
    var V = readV(), I = readI();
    if (S.rows.some(function (r) { return Math.abs(r.E - main.set) < 0.05; })) { S.say('You already have a reading at ' + main.set.toFixed(2) + ' V. Turn the knob further.'); return false; }
    if (I > 20) { S.say('The current is past the diode\'s rating. Turn the supply down.'); return false; }
    S.addRow({ E: main.set, V: V, I: I });
    S.say('Written in your record book: V = ' + V.toFixed(2) + ' V, I = ' + I.toFixed(2) + ' mA.');
    return true;
  }
  function recordTrans() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!main.on || !aux.on) { S.say('Switch both supplies on first.'); return false; }
    var vce = readVce();
    if (Math.abs(vce - VCE_SET) > 0.02) { S.say('V_CE is ' + vce.toFixed(2) + ' V. Bring it back to ' + VCE_SET.toFixed(2) + ' V before reading.'); return false; }
    var ib = readIb(), ic = readIc();
    if (ib < 1) { S.say('The base current is too small to read. Raise the base supply.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.ib - ib) < 1; })) { S.say('You already have a reading near ' + ib.toFixed(1) + ' µA. Change the base supply.'); return false; }
    S.addRow({ vbb: aux.set, ib: ib, ic: ic, vce: vce });
    S.say('Written in your record book: I_B = ' + ib.toFixed(1) + ' µA, I_C = ' + ic.toFixed(2) + ' mA at V_CE = ' + vce.toFixed(2) + ' V.');
    return true;
  }

  // ---------------------------------------------------------------- result
  function result(rows) {
    if (MODE === 'zener') {
      var pts = rows.filter(function (r) { return r.I >= 0.5; }).map(function (r) { return [r.I / 1000, r.V]; });
      if (pts.length < 3) return null;
      var f = S.fit.linear(pts);
      if (!f) return null;
      return { label: 'Breakdown voltage Vz', value: f.c, unit: 'V', digits: 2, truth: p.Vz,
        note: 'Intercept of the steep part of the curve on the voltage axis. Its slope gives the dynamic resistance, about ' + f.m.toFixed(1) + ' Ω.' };
    }
    var q = rows.map(function (r) { return [r.ib / 1e6, r.ic / 1000]; });
    if (q.length < 3) return null;
    var g = S.fit.linear(q);
    if (!g) return null;
    return { label: 'Current gain β', value: g.m, unit: '', digits: 1, truth: p.beta * (1 + VCE_SET / p.VA) * (1 - Math.exp(-VCE_SET / p.Vsat)),
      note: 'Slope of the I_C against I_B graph at V_CE = ' + VCE_SET.toFixed(1) + ' V. The voltage gain of the stage would be β times the ratio of the collector resistance to the input resistance.' };
  }

  var stepsZener = [
    { id: 'setup', title: 'Set up', view: 'bb', render: function (u) {
        u.h2('Check the circuit and switch on');
        u.p('Supply (+) → 1 kΩ resistor → milliammeter → Zener diode (banded end, the cathode, towards the +) → supply (−). The voltmeter is across the diode alone.');
        u.task('1. Check that the diode is in reverse bias', st.traced, st.traced ? 'Cathode band towards the + terminal' : 'Look at the silver band')
          .add(u.button(st.traced ? 'Checked' : 'Trace the circuit', trace, !st.traced, st.traced));
        u.task('2. Knob at zero, then switch on', main.on, main.on ? 'Supply on at ' + main.set.toFixed(2) + ' V' : 'The hand presses the POWER rocker')
          .add(u.row(u.button(main.on ? 'Switch off' : 'Switch the supply on', function () { S.focus('main'); power(main, !main.on, 'Supply'); }, !main.on, S.hand.busy),
            u.button('Knob to zero', function () { turn(main, 0, 'supply'); }, false, S.hand.busy || main.set === 0)));
        u.note('The 1 kΩ resistor must always be in the circuit: past breakdown the Zener diode has almost no resistance of its own.');
        u.next('Next: take readings', st.traced && main.on);
      },
      ok: function () { return st.traced && main.on; },
      auto: function () { trace(); return turn(main, 0, 'supply').then(function () { return power(main, true, 'Supply'); }); } },
    { id: 'read', title: 'Readings', view: 'bench', render: function (u) {
        u.h2('Raise the reverse voltage and record V and I');
        u.p('Take steps of about 1 V, and smaller steps near the breakdown where the current starts to rise.');
        var tg = { v: Math.min(main.vmax, rnd(main.set + 1, 2)) };
        u.slider('Set the supply to', 0, main.vmax, 0.1, function () { return tg.v; }, function (v) { tg.v = v; }, 'V', 1);
        u.row(u.button('Turn the knob', function () { turn(main, tg.v, 'supply'); }, true, S.hand.busy),
          u.button('Record V and I', function () { recordZener(); }, false, S.hand.busy));
        u.live(function () { return 'Voltmeter ' + readV().toFixed(2) + ' V  ·  Milliammeter ' + readI().toFixed(2) + ' mA'; });
        u.h3('Observation table'); u.table();
        var steep = S.rows.filter(function (r) { return r.I >= 0.5; }).length;
        if (S.rows.length < 8) u.p(S.rows.length + ' of at least 8 readings recorded.');
        else if (steep < 3) u.note('Take a few more readings past breakdown, where the current is more than half a milliampere.');
        u.next('Next: the characteristic', S.rows.length >= 8 && steep >= 3);
      },
      ok: function () { return S.rows.length >= 8 && S.rows.filter(function (r) { return r.I >= 0.5; }).length >= 3; },
      auto: function () {
        return [1, 2, 3, 4, 4.5, 5, 5.5, 6, 6.5, 7, 8, 9, 10, 11, 12, 13, 14].map(function (v) { return Math.min(v, main.vmax); })
          .reduce(function (pr, v) { return pr.then(function () { return turn(main, v, 'supply'); }).then(function () { recordZener(); }); }, Promise.resolve());
      } },
  ];

  var stepsTrans = [
    { id: 'setup', title: 'Set up', view: 'bb', render: function (u) {
        u.h2('Check the circuit and switch both supplies on');
        u.p('Base supply → 100 kΩ → microammeter → base. Collector supply → 1 kΩ → milliammeter → collector. The emitter is the common point; the voltmeter reads from collector to emitter.');
        u.task('1. Trace the circuit', st.traced, st.traced ? 'Both loops traced, emitter common' : 'Follow the leads from each supply')
          .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
        u.task('2. Both knobs at zero, then switch on', main.on && aux.on, main.on && aux.on ? 'Both supplies on' : 'Collector ' + (main.on ? 'on' : 'off') + ', base ' + (aux.on ? 'on' : 'off'))
          .add(u.row(u.button(main.on ? 'Collector supply is on' : 'Switch the collector supply on', function () { S.focus('main'); power(main, true, 'Collector supply'); }, !main.on, main.on || S.hand.busy),
            u.button(aux.on ? 'Base supply is on' : 'Switch the base supply on', function () { S.focus('aux'); power(aux, true, 'Base supply'); }, !aux.on, aux.on || S.hand.busy)));
        u.note('Never join the base straight to a supply: the 100 kΩ resistor is what keeps the base current small.');
        u.next('Next: take readings', st.traced && main.on && aux.on);
      },
      ok: function () { return st.traced && main.on && aux.on; },
      auto: function () { trace();
        return turn(main, 0, 'collector supply').then(function () { return power(main, true, 'Collector supply'); })
          .then(function () { return turn(aux, 0, 'base supply'); }).then(function () { return power(aux, true, 'Base supply'); }); } },
    { id: 'read', title: 'Readings', view: 'bench', render: function (u) {
        u.h2('Read I_B and I_C at a fixed V_CE');
        u.p('Set a base current with the base supply, then turn the collector knob until the voltmeter reads ' + VCE_SET.toFixed(2) + ' V, and record both currents.');
        var tg = { v: Math.min(aux.vmax, rnd(aux.set + 0.5, 2)) };
        u.slider('Base supply', 0, aux.vmax, 0.05, function () { return tg.v; }, function (v) { tg.v = v; }, 'V', 2);
        u.row(u.button('Turn the base knob', function () { turn(aux, tg.v, 'base supply'); }, true, S.hand.busy),
          u.button('Bring V_CE to ' + VCE_SET.toFixed(1) + ' V', function () { setVce(VCE_SET); }, false, S.hand.busy),
          u.button('Record I_B and I_C', function () { recordTrans(); }, false, S.hand.busy));
        u.live(function () { var n = now(); return 'I_B ' + readIb().toFixed(1) + ' µA  ·  I_C ' + readIc().toFixed(2) + ' mA  ·  V_CE ' + readVce().toFixed(2) + ' V  ·  V_BE ' + n.Vbe.toFixed(3) + ' V'; });
        u.h3('Observation table'); u.table();
        if (S.rows.length < 5) u.p(S.rows.length + ' of at least 5 readings recorded.');
        u.next('Next: the gain', S.rows.length >= 5);
      },
      ok: function () { return S.rows.length >= 5; },
      auto: function () {
        return baseList().reduce(function (pr, v) {
          return pr.then(function () { return turn(aux, v, 'base supply'); })
            .then(function () { return setVce(VCE_SET); }).then(function () { recordTrans(); }); }, Promise.resolve());
      } },
  ];

  return {
    camera: { pos: [0.0, 1.0, 0.82], look: [0.0, 0.02, -0.42] },
    views: { bench: [[0.0, 0.96, 0.78], [0.0, 0.02, -0.42]], bb: [[0.0, 0.42, 0.3], [0.0, 0.02, -0.08]],
      main: [[-0.4, 0.3, -0.1], [-0.44, 0.06, -0.44]], aux: [[0.42, 0.3, -0.1], [0.46, 0.06, -0.44]],
      mv: [[0.28, 0.26, -0.28], [0.28, 0.03, -0.56]], ma: [[-0.06, 0.26, -0.3], [-0.06, 0.03, -0.58]],
      mb: [[-0.34, 0.26, -0.26], [-0.36, 0.03, -0.54]], book: [[0.7, 0.46, 0.46], [0.7, 0.0, -0.08]] },
    theory: MODE === 'zener' ? {
      principle: 'A Zener diode is doped so heavily that in reverse bias it breaks down at a low and sharply defined voltage. Below that voltage only a tiny leakage current flows; past it the current rises steeply while the voltage across the diode hardly changes.',
      formula: 'V = Vz + I rz',
      formulaNote: 'on the steep part · extended back to zero current it cuts the axis at the breakdown voltage Vz',
      more: ['That almost constant voltage is what makes a Zener diode a voltage regulator: whatever the supply does, the voltage across the diode stays near Vz as long as some current flows through it.',
        'The series resistor is not optional. Past breakdown the diode has only a few ohms of its own, so without the resistor the current would rise until the diode was destroyed.'],
      precautions: 'Always keep the series resistor in the circuit, start at zero volts, and keep the current well below the diode\'s power rating.' } : {
      principle: 'In common emitter the base-emitter junction is forward biased and the collector-base junction is reverse biased. A small base current controls a much larger collector current, and the ratio of the two is the current gain.',
      formula: 'β = ΔI_C / ΔI_B',
      formulaNote: 'measured at a fixed V_CE, from the slope of the I_C against I_B graph',
      more: ['Past the knee (about 0.3 V) the collector current depends very little on V_CE, which is why the transistor can work as an amplifier. All the readings are taken at one V_CE so that the gain belongs to one working point.',
        'The base current itself is set by the base supply and the 100 kΩ resistor: I_B = (V_BB − V_BE)/R_B, with V_BE near 0.6 V for a silicon transistor.'],
      precautions: 'The base resistor must always be in place. Switch both supplies on at zero and raise them slowly, and keep the collector current inside the meter\'s range.' },
    book: MODE === 'zener' ? { title: 'Expt. — Zener diode, reverse characteristic', at: [0.7, 0.1, -0.08],
      lines: ['Aim: to draw the reverse characteristic of a', 'Zener diode and find its breakdown voltage.',
        'Diode: ' + (SAMPLE || PART) + ',  series R = 1 kΩ', 'Digital meters: V to 0.01 V, I to 0.01 mA',
        'Past breakdown V = Vz + I rz', 'Precautions: series resistor always in,', 'start at zero volts.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Supply (V)', get: function (r) { return r.E.toFixed(1); } },
        { label: 'V reverse (V)', get: function (r) { return r.V.toFixed(2); } },
        { label: 'I reverse (mA)', get: function (r) { return r.I.toFixed(2); } }] }
      : { title: 'Expt. — Transistor in common emitter', at: [0.7, 0.1, -0.08],
        lines: ['Aim: to measure the base and collector currents', 'of an n-p-n transistor and find its current gain.',
          'Transistor: ' + (SAMPLE || PART), 'R_B = 100 kΩ,  R_C = 1 kΩ',
          'All readings at V_CE = ' + VCE_SET.toFixed(2) + ' V', 'β = ΔI_C / ΔI_B'],
        columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
          { label: 'V_BB (V)', get: function (r) { return r.vbb.toFixed(2); } },
          { label: 'I_B (µA)', get: function (r) { return r.ib.toFixed(1); } },
          { label: 'I_C (mA)', get: function (r) { return r.ic.toFixed(2); } },
          { label: 'I_C / I_B', get: function (r) { return r.ib ? (r.ic * 1000 / r.ib).toFixed(0) : '—'; } }] },
    graph: MODE === 'zener' ? { x: function (r) { return r.V; }, y: function (r) { return r.I; }, xlabel: 'Reverse voltage (V)', ylabel: 'Reverse current (mA)', x0: 0, y0: 0 }
      : { x: function (r) { return r.ib; }, y: function (r) { return r.ic; }, xlabel: 'I_B (µA)', ylabel: 'I_C (mA)', x0: 0, y0: 0,
        line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.02,
    resultNote: MODE === 'zener' ? 'The curve stays flat almost to the breakdown voltage and then turns sharply: that corner is what a Zener diode is made for.'
      : 'A straight line through the readings means the gain is the same over the whole range: that is what makes the transistor a faithful amplifier.',
    chips: MODE === 'zener' ? ['What is breakdown?', 'Why the series resistor?', 'Check my readings', 'How is a Zener diode used as a regulator?']
      : ['What is the current gain?', 'Why keep V_CE fixed?', 'Check my readings', 'What is the voltage gain?'],
    viva: MODE === 'zener' ? [
      ['Past breakdown, the voltage across a Zener diode', ['Stays nearly constant', 'Rises with the current', 'Falls to zero'], 0,
        'Which is exactly why it is used to hold a supply steady.'],
      ['A Zener diode in a regulator is joined', ['In reverse bias, across the load', 'In forward bias, in series', 'Either way'], 0,
        'It regulates only in reverse breakdown.']]
      : [['In common emitter the current gain β is', ['I_C / I_B', 'I_C / I_E', 'I_E / I_B'], 0, 'β is usually 100 or more.'],
        ['Why is the base made very thin and lightly doped?', ['So that most carriers reach the collector', 'To save material', 'To lower the voltage'], 0,
          'Only then is the collector current nearly the whole emitter current.']],
    askState: function () {
      var n = now();
      if (MODE === 'zener') return { experiment: 'reverse characteristic of a Zener diode', diode: SAMPLE || PART,
        supply_on: main.on, supply_setting_V: +main.set.toFixed(2), reverse_voltage_V: readV(), reverse_current_mA: readI(),
        series_resistor_ohm: p.Rs, readings_taken: S.rows.length };
      return { experiment: 'common-emitter characteristics of an n-p-n transistor', transistor: SAMPLE || PART,
        collector_supply_on: main.on, base_supply_on: aux.on, base_supply_V: +aux.set.toFixed(2),
        collector_supply_V: +main.set.toFixed(2), base_current_uA: readIb(), collector_current_mA: readIc(),
        Vce_V: readVce(), Vbe_V: +n.Vbe.toFixed(3), readings_wanted_at_Vce: VCE_SET, readings_taken: S.rows.length };
    },
    steps: MODE === 'zener' ? stepsZener : stepsTrans,
    tick: function () {
      if (MODE === 'zener') {
        mV.show(main.on ? readV().toFixed(2) : '----', main.on ? 'V' : '');
        mA.show(main.on ? readI().toFixed(2) : '----', main.on ? 'mA' : '');
        hudA.set(main.on ? main.set.toFixed(1) + ' V' : 'off');
        hudB.set(main.on ? readV().toFixed(2) + ' V' : '—');
        hudC.set(main.on ? readI().toFixed(2) + ' mA' : '—');
      } else {
        var on = main.on && aux.on;
        mV.show(on ? readVce().toFixed(2) : '----', on ? 'V' : '');
        mA.show(on ? readIc().toFixed(2) : '----', on ? 'mA' : '');
        mB.show(on ? readIb().toFixed(1) : '----', on ? 'uA' : '');
        hudA.set(aux.on ? aux.set.toFixed(2) + ' V' : 'off');
        hudB.set(on ? readIb().toFixed(1) + ' µA' : '—');
        hudC.set(on ? readIc().toFixed(2) + ' mA / ' + readVce().toFixed(2) + ' V' : '—');
      }
    },
  };
});
