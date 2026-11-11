/* Prayogshala studio rig `bg-lamp-scale`: THE BALLISTIC GALVANOMETER BENCH (B.Sc. electricity and magnetism).
   A suspended-coil ballistic galvanometer with its mirror, a lamp and a translucent half-metre scale that the
   spot of light moves along, a tapping key and a damping key, and the accessory each set-up needs. Six set-ups
   of app/prayog/labs/ug_em_w7.py run on it, chosen by the lab's `mode`:
     0 constants of the instrument      1 high resistance by leakage      2 Rayleigh's method (self-inductance)
     3 mutual inductance (absolute)     4 earth inductor                  5 field along a solenoid (search coil,
                                                                            or a Hall-probe gaussmeter)
   Every throw comes from the kernel `w7_bg` (packs/ug_em_w7.js), which integrates the coil's equation of motion:
   the same code the server checks against the textbook formula. The scale is read to half a millimetre. */
HoolaStudio.define('bg-lamp-scale', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.w7_bg, assign = HK.assign;
  var p = HK.paramsFor('w7_bg', S.lab.params);
  var MODE = Math.round(p.mode), HALL = MODE === 5 && p.meth >= 0.5;
  var V_ = S.lab.variant || {};
  var st = { lamp: false, free: false, vals: {}, part: 0, spot: 0, swing: null, busyRead: false, gauss: null };
  var SCALE_HALF = 0.25;                                  // the scale runs from -250 mm to +250 mm

  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function mm(d) { return Math.round(d * 2000) / 2; }     // metres -> millimetres, read to 0.5 mm
  function busy() { if (S.hand.busy || st.busyRead) { S.say('Wait for the spot to settle.'); return true; } return false; }
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 28); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }
  function col(hex, rough, metal) { return new T.MeshStandardMaterial({ color: hex, roughness: rough === undefined ? 0.5 : rough, metalness: metal || 0 }); }
  // printed text that always fits its plate (long names are condensed, never cut off)
  function tag(text, w, fg, bg) { var hh = 112;
    var tex = S.canvasTex(512, hh, function (c) { if (bg) { c.fillStyle = bg; c.fillRect(0, 0, 512, hh); } c.fillStyle = fg; c.font = '600 62px "Public Sans", sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(text, 256, hh / 2, 488); });
    return new T.Mesh(new T.PlaneGeometry(w, w * 0.22), new T.MeshStandardMaterial({ map: tex, transparent: !bg, roughness: 0.6 })); }
  function plate(g, text, w, x, y, z, ry, bg, fg) { var l = tag(text, w, fg || '#1b1b1b', bg); l.position.set(x, y, z); if (ry !== undefined) l.rotation.y = ry; g.add(l); return l; }
  function flat(g, text, w, x, y, z, fg) { var l = tag(text, w, fg || '#f0e6c8'); l.rotation.x = -Math.PI / 2; l.position.set(x, y, z); g.add(l); return l; }
  function mean(a) { var s = 0, i; for (i = 0; i < a.length; i++) s += a[i]; return a.length ? s / a.length : 0; }
  function corr(r) { var lam = (r.d1 > 0 && r.d2 > 0) ? Math.log(r.d1 / r.d2) : 0; return r.d1 * (1 + lam / 2); }
  // the charge constant on the instrument's calibration card: coulombs per metre of scale (undamped)
  var KQ = KN.measure(assign(p, { mode: 0 })).T / (2 * Math.PI) * p.c / p.Kc / (2 * p.D);

  /* ================================================================ the galvanometer */
  var GX = 0.24, GZ = -0.64;
  var gal = new T.Group(); S.scene.add(gal); gal.position.set(GX, 0, GZ);
  mk(gal, cyl(0.075, 0.08, 0.014, 40), M.bakelite, 0, 0.012, 0);
  [0, 1, 2].forEach(function (i) { var a = i * 2.094 + 0.5; var f = mk(gal, cyl(0.009, 0.011, 0.012, 16), M.brass, Math.cos(a) * 0.066, 0.006, Math.sin(a) * 0.066); f.castShadow = true; });
  var gcase = mk(gal, cyl(0.05, 0.05, 0.13, 40), M.brass, 0, 0.084, 0);
  var win = mk(gal, new T.CylinderGeometry(0.0505, 0.0505, 0.05, 32, 1, true, -0.5, 1.0), M.glass, 0, 0.095, 0); win.rotation.y = Math.PI / 2 - 0.5 + Math.PI / 2;
  mk(gal, cyl(0.052, 0.052, 0.006, 40), M.bakelite, 0, 0.152, 0);
  mk(gal, cyl(0.009, 0.009, 0.2, 20), M.brass, 0, 0.255, 0);                      // the suspension tube
  mk(gal, cyl(0.014, 0.012, 0.016, 20), M.bakelite, 0, 0.36, 0);                 // torsion head
  var mirror = mk(gal, box(0.014, 0.014, 0.001), col(0xf4f7fa, 0.05, 1), 0, 0.095, 0.0508);
  [-0.03, 0.03].forEach(function (x, i) { var t = S.terminal([GX + x, 0.019, GZ + 0.07], i ? 'black' : 'red'); });
  plate(gal, 'BALLISTIC GALVANOMETER', 0.085, 0, 0.04, 0.0505, 0, '#1d2024', '#e9dfc2');
  S.contact(0.24, 0.24, GX, GZ, 0.55);

  /* ================================================================ lamp and scale */
  var SX = GX, SZ = -0.22, SW = 0.56, SY = 0.215;
  var lamp = new T.Group(); S.scene.add(lamp); lamp.position.set(SX, 0, SZ);
  mk(lamp, box(0.2, 0.012, 0.1), M.iron, 0, 0.006, 0);
  [-0.26, 0.26].forEach(function (x) { mk(lamp, cyl(0.005, 0.005, SY, 12), M.chrome, x, SY / 2, 0); mk(lamp, box(0.05, 0.008, 0.07), M.iron, x, 0.004, 0); });
  mk(lamp, cyl(0.006, 0.006, 0.1, 12), M.chrome, 0, 0.06, 0);
  var house = mk(lamp, box(0.07, 0.05, 0.06), col(0x23272d, 0.45, 0.3), 0, 0.125, 0.0);
  var lens = mk(lamp, cyl(0.014, 0.014, 0.012, 24), M.chrome, 0, 0.125, -0.034); lens.rotation.x = Math.PI / 2;
  var bulb = mk(lamp, cyl(0.011, 0.011, 0.004, 24), new T.MeshBasicMaterial({ color: 0x3a3a34 }), 0, 0.125, -0.041); bulb.rotation.x = Math.PI / 2;
  var lswitch = mk(lamp, cyl(0.006, 0.006, 0.008, 16), M.red, 0.022, 0.154, 0.012);
  plate(lamp, 'LAMP 6 V', 0.05, 0, 0.125, 0.0305, 0, '#23272d', '#d8d2bc');
  var scaleTex = S.liveTex(2048, 220), lastSpot = null;
  var scaleM = new T.Mesh(new T.PlaneGeometry(SW, 0.06), new T.MeshBasicMaterial({ map: scaleTex, side: T.DoubleSide, toneMapped: false }));
  scaleM.position.set(0, SY + 0.03, 0); lamp.add(scaleM);
  mk(lamp, box(SW + 0.02, 0.006, 0.01), M.darkWood, 0, SY - 0.003, 0); mk(lamp, box(SW + 0.02, 0.006, 0.01), M.darkWood, 0, SY + 0.063, 0);
  S.contact(0.66, 0.16, SX, SZ, 0.45);
  function drawScale(d, on) {
    var key = (on ? 1 : 0) + '|' + Math.round(d * 20000); if (key === lastSpot) return; lastSpot = key;
    scaleTex.draw(function (x, w, h) {
      x.fillStyle = '#efe9d6'; x.fillRect(0, 0, w, h);
      x.strokeStyle = '#22252a'; x.fillStyle = '#22252a'; x.textAlign = 'center';
      for (var i = -250; i <= 250; i += 1) {
        if (i % 5 && w < 3000 && i % 2) continue;
        var px = w / 2 + i / 250 * (w / 2 - 40), big = i % 50 === 0, mid = i % 10 === 0;
        x.lineWidth = big ? 4 : mid ? 2.5 : 1.2; x.beginPath(); x.moveTo(px, 0); x.lineTo(px, big ? 80 : mid ? 58 : (i % 5 === 0 ? 42 : 28)); x.stroke();
        if (big) { x.font = '700 54px "Public Sans", sans-serif'; x.fillText(String(Math.abs(i / 10)), px, 140); }
      }
      x.font = '600 34px "Public Sans", sans-serif'; x.fillText('cm', w / 2, 196);
      if (on) { var sx = w / 2 + Math.max(-1.04, Math.min(1.04, d / SCALE_HALF)) * (w / 2 - 40);
        var g2 = x.createRadialGradient(sx, 60, 2, sx, 60, 46); g2.addColorStop(0, 'rgba(255,214,90,.98)'); g2.addColorStop(1, 'rgba(255,214,90,0)');
        x.fillStyle = g2; x.fillRect(sx - 48, 0, 96, 130); x.fillStyle = '#1a1205'; x.fillRect(sx - 1.5, 4, 3, 112); }
    });
  }
  // the reflected beam: lens -> mirror -> spot
  var beamMat = new T.LineBasicMaterial({ color: 0xffd65a, transparent: true, opacity: 0.55 });
  var beamGeo = new T.BufferGeometry().setFromPoints([new T.Vector3(), new T.Vector3(), new T.Vector3()]);
  var beam = new T.Line(beamGeo, beamMat); beam.visible = false; S.scene.add(beam);
  function setBeam(d) {
    var a = new T.Vector3(SX, 0.125, SZ - 0.04), b = new T.Vector3(GX, 0.095, GZ + 0.052);
    var c = new T.Vector3(SX + Math.max(-1.04, Math.min(1.04, d / SCALE_HALF)) * (SW / 2 - 0.011), SY + 0.035, SZ - 0.002);
    beamGeo.setFromPoints([a, b, c]); mirror.rotation.y = d * 0.6;
  }

  /* ================================================================ keys (front right) */
  var KX = 0.6, KZ = 0.04;
  var keyG = new T.Group(); S.scene.add(keyG); keyG.position.set(KX, 0, KZ);
  var kb = S.rounded(0.1, 0.06, 0.014, 0.004, M.bakelite); kb.rotation.x = -Math.PI / 2; kb.position.y = 0.007; keyG.add(kb);
  var lever = new T.Group(); lever.position.set(-0.03, 0.02, 0); keyG.add(lever);
  mk(lever, box(0.07, 0.003, 0.012), M.brass, 0.035, 0, 0);
  var tapKnob = mk(lever, cyl(0.009, 0.009, 0.012, 20), M.blackPlastic, 0.066, 0.008, 0);
  mk(keyG, cyl(0.004, 0.004, 0.008, 12), M.brass, 0.036, 0.016, 0); mk(keyG, cyl(0.005, 0.005, 0.012, 12), M.brass, -0.03, 0.016, 0);
  lever.rotation.z = 0.12;
  flat(keyG, MODE === 2 ? 'BATTERY KEY' : MODE === 3 || MODE === 5 ? 'REVERSING KEY' : MODE === 4 ? 'RELEASE' : 'TAPPING KEY', 0.07, 0, 0.0145, 0.022);
  S.contact(0.14, 0.1, KX, KZ, 0.45);
  var damp = S.plugKey([KX - 0.16, 0, KZ + 0.01]); damp.set(true); var dl = S.label('DAMPING KEY', { w: 0.06, ratio: 0.2, color: '#e9dfc2' }); dl.rotation.x = -Math.PI / 2; dl.position.set(KX - 0.16, 0.0165, KZ + 0.034); S.scene.add(dl);
  S.wire([[GX - 0.03, 0.03, GZ + 0.07], [GX - 0.2, 0.004, GZ + 0.25], [KX - 0.2, 0.004, KZ - 0.1], [KX - 0.176, 0.02, KZ + 0.01]], 'red');
  S.wire([[GX + 0.03, 0.03, GZ + 0.07], [GX + 0.25, 0.004, GZ + 0.3], [KX - 0.1, 0.004, KZ - 0.12], [KX - 0.144, 0.02, KZ + 0.01]], 'black');

  /* ================================================================ the accessory of each set-up (back left) */
  var acc = new T.Group(), gaussG = null, supplyG = null; S.scene.add(acc);
  var AX = -0.5, AZ = -0.5, knobMesh = null, accName = '', accInfo = '', moveCoil = null, gaussTex = null, swTex = null;
  function capBox(x, z, text) { var g = new T.Group(); acc.add(g); g.position.set(x, 0, z);
    var b = S.rounded(0.11, 0.09, 0.06, 0.006, M.darkWood); b.rotation.x = -Math.PI / 2; b.position.y = 0.03; g.add(b);
    mk(g, box(0.1, 0.004, 0.08), M.bakelite, 0, 0.062, 0); flat(g, text, 0.085, 0, 0.0645, 0.012);
    mk(g, cyl(0.005, 0.006, 0.012, 12), M.brass, -0.03, 0.07, -0.02); mk(g, cyl(0.005, 0.006, 0.012, 12), M.brass, 0.03, 0.07, -0.02);
    S.contact(0.16, 0.14, x, z, 0.5); return g; }
  function knobOn(g, x, y, z) { var k = new T.Group(); k.position.set(x, y, z); g.add(k); mk(k, cyl(0.012, 0.014, 0.014, 28), M.bakelite); mk(k, box(0.002, 0.002, 0.012), M.white, 0, 0.008, -0.004); return k; }
  function coilRing(g, r, tube, x, y, z, mat) { var c = S.mesh(new T.TorusGeometry(r, tube, 14, 48), mat || M.copper); c.position.set(x, y, z); g.add(c); return c; }

  if (MODE === 0 || MODE === 1) {
    capBox(AX - 0.12, AZ, MODE ? 'STD CAPACITOR 0.5 µF' : 'STD CAPACITOR 0.1 µF');
    var cell = S.cell([AX - 0.12, 0, AZ + 0.16], { text: MODE ? '1 V' : '2 V' });
    if (MODE === 0) {
      var rb1 = S.resistanceBox([AX + 0.1, 0, AZ - 0.02]); rb1.show(88); var rb2 = S.resistanceBox([AX + 0.1, 0, AZ + 0.14]); rb2.show(35);
      var l1 = S.label('9999 Ω + 1 Ω', { w: 0.07, ratio: 0.2, color: '#f0e6c8' }); l1.rotation.x = -Math.PI / 2; l1.position.set(AX + 0.1, 0.054, AZ - 0.05); S.scene.add(l1);
      var l2 = S.label('SERIES BOX R', { w: 0.07, ratio: 0.2, color: '#f0e6c8' }); l2.rotation.x = -Math.PI / 2; l2.position.set(AX + 0.1, 0.054, AZ + 0.11); S.scene.add(l2);
      knobMesh = rb2; accName = 'Capacitor, cell and resistance boxes';
      accInfo = 'A 2 V cell across 9999 Ω and 1 Ω gives 0.2 mV for the steady deflection; the 0.1 µF standard capacitor gives the known charge.';
    } else {
      var hr = new T.Group(); acc.add(hr); hr.position.set(AX + 0.1, 0, AZ);
      mk(hr, box(0.16, 0.012, 0.06), M.bakelite, 0, 0.006, 0);
      var rod = mk(hr, cyl(0.008, 0.008, 0.11, 20), col(0x5a2f1c, 0.35), 0, 0.03, 0); rod.rotation.z = Math.PI / 2;
      [-0.06, 0.06].forEach(function (x) { mk(hr, cyl(0.004, 0.004, 0.03, 12), M.brass, x, 0.02, 0); });
      flat(hr, 'HIGH RESISTANCE X', 0.1, 0, 0.0125, 0.02); S.contact(0.2, 0.1, AX + 0.1, AZ, 0.45);
      var sw = S.stopwatch([AX + 0.12, 0.011, AZ + 0.18], [-Math.PI / 2, 0, 0]); knobMesh = sw.start;
      accName = 'Capacitor, high resistance and stop-watch'; accInfo = 'The charged capacitor leaks through the high resistance for a timed interval before it is discharged through the galvanometer.';
    }
  } else if (MODE === 2) {
    var br = new T.Group(); acc.add(br); br.position.set(AX - 0.06, 0, AZ + 0.02);
    var bb = S.rounded(0.3, 0.2, 0.05, 0.006, M.darkWood); bb.rotation.x = -Math.PI / 2; bb.position.y = 0.025; br.add(bb);
    var btex = S.canvasTex(900, 600, function (x, w, h) { x.fillStyle = '#17181b'; x.fillRect(0, 0, w, h); x.strokeStyle = '#e8e0c4'; x.lineWidth = 6; x.fillStyle = '#e8e0c4';
      x.beginPath(); x.moveTo(450, 70); x.lineTo(160, 300); x.lineTo(450, 530); x.lineTo(740, 300); x.closePath(); x.stroke(); x.beginPath(); x.moveTo(160, 300); x.lineTo(740, 300); x.stroke();
      x.font = '700 44px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText('P', 270, 165); x.fillText('Q', 630, 165); x.fillText('L, r', 250, 450); x.fillText('S', 650, 450); x.fillText('G', 450, 285);
      x.font = '600 30px "Public Sans", sans-serif'; x.fillText('RAYLEIGH BRIDGE', 450, 580); });
    var bt = S.mesh(box(0.29, 0.003, 0.19), [M.bakelite, M.bakelite, new T.MeshStandardMaterial({ map: btex, roughness: 0.5 }), M.bakelite, M.bakelite, M.bakelite]); bt.position.y = 0.052; br.add(bt);
    knobMesh = knobOn(br, 0.1, 0.06, 0.06); S.contact(0.36, 0.26, AX - 0.06, AZ + 0.02, 0.5);
    var cg = new T.Group(); acc.add(cg); cg.position.set(AX + 0.22, 0, AZ - 0.02);
    mk(cg, cyl(0.045, 0.045, 0.006, 32), M.bakelite, 0, 0.003, 0); mk(cg, cyl(0.045, 0.045, 0.006, 32), M.bakelite, 0, 0.063, 0);
    mk(cg, cyl(0.036, 0.036, 0.054, 32), new T.MeshStandardMaterial({ color: 0xb5622f, roughness: 0.35, metalness: 0.6 }), 0, 0.033, 0);
    flat(cg, 'COIL L', 0.05, 0, 0.0665, 0); S.contact(0.13, 0.13, AX + 0.22, AZ - 0.02, 0.5);
    S.cell([AX + 0.2, 0, AZ + 0.16], { text: '2 V' });
    accName = 'Bridge with the coil in its third arm'; accInfo = 'Equal ratio arms P and Q, the coil in the third arm and S balancing it. A small resistance r can be plugged into the coil arm.';
  } else if (MODE === 3) {
    var mg = new T.Group(); acc.add(mg); mg.position.set(AX - 0.04, 0, AZ);
    mk(mg, box(0.26, 0.012, 0.14), M.darkWood, 0, 0.006, 0);
    var prim = mk(mg, cyl(0.03, 0.03, 0.2, 32), new T.MeshStandardMaterial({ color: 0xb5622f, roughness: 0.35, metalness: 0.6 }), 0, 0.055, 0); prim.rotation.z = Math.PI / 2;
    var sec = mk(mg, cyl(0.042, 0.042, 0.07, 32), new T.MeshStandardMaterial({ color: 0x1f6b4a, roughness: 0.4, metalness: 0.3 }), 0, 0.055, 0); sec.rotation.z = Math.PI / 2;
    [-0.105, 0.105].forEach(function (x) { mk(mg, box(0.008, 0.09, 0.09), M.bakelite, x, 0.055, 0); });
    flat(mg, 'PRIMARY · SECONDARY', 0.14, 0, 0.0125, 0.058); S.contact(0.32, 0.2, AX - 0.04, AZ, 0.5);
    var rh = S.rheostat([AX - 0.04, 0, AZ + 0.17], 0.22); knobMesh = rh.userData.slider;
    var am = S.meter({ pos: [AX + 0.24, 0, AZ + 0.02], min: 0, max: 1, unit: 'A', symbol: 'A', caption: 'primary current' }); st.am = am;
    accName = 'Pair of coils, rheostat and ammeter'; accInfo = 'The primary carries a measured current that the reversing key reverses; the secondary is in series with the galvanometer.';
  } else if (MODE === 4) {
    var eg = new T.Group(); acc.add(eg); eg.position.set(AX, 0, AZ);
    mk(eg, cyl(0.1, 0.11, 0.016, 40), M.iron, 0, 0.008, 0);
    var frame = new T.Group(); frame.position.y = 0.016; eg.add(frame);
    [-0.125, 0.125].forEach(function (x) { mk(frame, box(0.012, 0.25, 0.02), M.darkWood, x, 0.125, 0); });
    mk(frame, box(0.262, 0.012, 0.02), M.darkWood, 0, 0.006, 0); mk(frame, box(0.262, 0.012, 0.02), M.darkWood, 0, 0.25, 0);
    var spin = new T.Group(); spin.position.y = 0.128; frame.add(spin);
    coilRing(spin, 0.1, 0.008, 0, 0, 0, new T.MeshStandardMaterial({ color: 0xb5622f, roughness: 0.35, metalness: 0.6 }));
    mk(spin, cyl(0.003, 0.003, 0.238, 10), M.steel, 0, 0, 0).rotation.z = Math.PI / 2;
    var handle = mk(frame, cyl(0.01, 0.01, 0.02, 16), M.blackPlastic, 0.14, 0.128, 0); handle.rotation.z = Math.PI / 2;
    plate(eg, 'EARTH INDUCTOR', 0.09, 0, 0.03, 0.105, 0, '#23272d', '#e9dfc2');
    S.contact(0.3, 0.3, AX, AZ, 0.55); knobMesh = handle;
    // vertical plane: the coil turns about the vertical axis; horizontal plane: about the horizontal axle
    moveCoil = function (part, k) { if (part) spin.rotation.set(Math.PI / 2 + Math.PI * k, 0, 0); else spin.rotation.set(0, Math.PI * k, 0); };
    moveCoil(0, 0);
    accName = 'Earth inductor'; accInfo = 'A coil of ' + Math.round(p.Ne) + ' turns, mean radius ' + rnd(p.re * 100, 1) + ' cm, that a spring turns through exactly 180 degrees.';
  } else {
    var sg = new T.Group(); acc.add(sg); sg.position.set(AX + 0.03, 0, AZ);
    var SL = 0.5;                                          // drawn length of the solenoid on the bench
    [-SL / 2, SL / 2].forEach(function (x) { mk(sg, box(0.012, 0.11, 0.09), M.darkWood, x, 0.055, 0); });
    mk(sg, box(SL + 0.06, 0.012, 0.11), M.darkWood, 0, 0.006, 0);
    var wtex = S.canvasTex(1024, 64, function (x, w, h) { x.fillStyle = '#b5622f'; x.fillRect(0, 0, w, h); x.strokeStyle = '#7a3c17'; x.lineWidth = 2; for (var i = 0; i < w; i += 6) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i + 2, h); x.stroke(); } });
    var sol = mk(sg, cyl(0.03, 0.03, SL, 36), new T.MeshStandardMaterial({ map: wtex, roughness: 0.35, metalness: 0.55, transparent: true, opacity: 0.92 }), 0, 0.07, 0); sol.rotation.z = Math.PI / 2;
    var rodG = new T.Group(); rodG.position.set(0, 0.07, 0); sg.add(rodG);
    var rd = mk(rodG, cyl(0.003, 0.003, 0.62, 10), HALL ? col(0x222428, 0.5) : M.wood, 0.31, 0, 0); rd.rotation.z = Math.PI / 2;
    var tip = mk(rodG, HALL ? box(0.02, 0.004, 0.008) : cyl(0.012, 0.012, 0.012, 20), HALL ? col(0x0f5fae, 0.4) : col(0x1f6b4a, 0.4, 0.3), 0, 0, 0); if (!HALL) tip.rotation.z = Math.PI / 2;
    var handleS = mk(rodG, cyl(0.008, 0.008, 0.05, 16), M.blackPlastic, 0.64, 0, 0); handleS.rotation.z = Math.PI / 2;
    var rule = S.ruler(0.5, {}); rule.rotation.set(-Math.PI / 2, 0, -Math.PI / 2); rule.position.set(AX + 0.03 - 0.25, 0.004, AZ + 0.09);
    flat(sg, 'SOLENOID  ' + Math.round(p.Ls * 100) + ' cm', 0.16, 0, 0.0125, 0.045);
    S.contact(SL + 0.12, 0.18, AX + 0.03, AZ, 0.5);
    moveCoil = function (x) { rodG.position.x = x / (p.Ls / 2) * (SL / 2); };
    moveCoil(0); knobMesh = handleS;
    supplyG = S.powerBox([AX - 0.14, 0, AZ + 0.24], 'DC SUPPLY 2 A');
    if (HALL) {
      var gm = new T.Group(); gaussG = gm; acc.add(gm); gm.position.set(AX + 0.28, 0, AZ + 0.2);
      var gb = S.rounded(0.16, 0.07, 0.1, 0.008, col(0xd7d3c9)); gb.rotation.x = -Math.PI / 2; gb.position.y = 0.05; gm.add(gb);
      gaussTex = S.liveTex(512, 180); var gs = new T.Mesh(new T.PlaneGeometry(0.1, 0.035), new T.MeshBasicMaterial({ map: gaussTex, toneMapped: false })); gs.position.set(0, 0.062, 0.0386); gm.add(gs);
      plate(gm, 'DIGITAL GAUSSMETER', 0.1, 0, 0.026, 0.0384, 0, '#2b323d', '#f1efe8'); S.contact(0.22, 0.14, AX + 0.28, AZ + 0.2, 0.5);
    }
    accName = HALL ? 'Solenoid with a Hall probe' : 'Solenoid with a search coil';
    accInfo = HALL ? 'The Hall probe slides along the axis; the gaussmeter reads the axial field directly.' : 'The search coil of ' + Math.round(p.Nc) + ' turns slides along the axis; reversing the solenoid current sends a charge through the galvanometer.';
  }
  function showGauss(b) { if (!gaussTex) return; var t = b === null ? '----' : (b * 1000).toFixed(2); if (t === st.gauss) return; st.gauss = t;
    gaussTex.draw(function (x) { x.fillStyle = '#a9b596'; x.fillRect(0, 0, 512, 180); x.fillStyle = '#1b2116'; x.font = '700 96px "JetBrains Mono", monospace'; x.textAlign = 'right'; x.fillText(t, 400, 120); x.font = '600 36px "Public Sans", sans-serif'; x.fillText('mT', 496, 150); }); }
  showGauss(null); drawScale(0, false);

  S.addApparatus('galvo', gal, 'Ballistic galvanometer', 'A coil hung on a fine strip between the poles of a magnet. Its period is long (about ' + rnd(KN.t0(p), 0) + ' s), so a quick charge gives it a kick and it swings out in a throw.');
  S.addApparatus('scale', lamp, 'Lamp and scale', 'The lamp throws a line of light on the coil\'s mirror; the reflected spot moves along the translucent scale, which is one metre of light path from the mirror. Read it to half a millimetre.');
  S.addApparatus('keys', keyG, 'Tapping key', 'Pressed for a moment to pass the charge (or to reverse or break the current). The damping key beside it short-circuits the coil to bring the spot to rest.');
  S.addApparatus('acc', acc, accName, accInfo);
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading is written here, as in a real practical file.');
  var hudD = S.hudCard(HALL ? 'Gaussmeter' : 'Spot on the scale'), hudS = S.hudCard('Setting');

  /* ================================================================ the plan of each set-up */
  var PLAN;
  function throwRow(q) { var m = KN.measure(q); return { m: m, d1: mm(m.d1), d2: mm(m.d2), ok: m.d1 <= SCALE_HALF && m.phi <= SCALE_HALF }; }
  if (MODE === 0) {
    PLAN = {
      parts: ['Steady deflection', 'Capacitor throw', 'Critical damping'],
      controls: [[{ key: 'R', label: 'Series box R', min: 300, max: 2000, step: 50, unit: 'Ω', digits: 0, def: 350 }],
        [{ key: 'Vq', label: 'Capacitor charged to', min: 0.5, max: 2.5, step: 0.1, unit: 'V', digits: 1, def: 2.0 }], []],
      act: ['Close the circuit and read', 'Charge and discharge', 'Find the critical resistance'],
      take: function (part, v) {
        var m;
        if (part === 0) { m = KN.measure(assign(p, { R: v.R })); if (m.phi > SCALE_HALF) return { err: 'The spot goes off the scale. Put more resistance in the series box.' };
          return { row: { part: 0, R: v.R, phi: mm(m.phi) }, steady: m.phi, say: 'Steady deflection ' + mm(m.phi) + ' mm with ' + v.R + ' Ω in the box.' }; }
        if (part === 1) { m = KN.measure(assign(p, { Vq: v.Vq })); if (m.d1 > SCALE_HALF) return { err: 'The throw goes off the scale. Charge the capacitor to a lower voltage.' };
          return { row: { part: 1, V: v.Vq, d1: mm(m.d1), d2: mm(m.d2) }, q: m.q, rq: 0, say: 'First throw ' + mm(m.d1) + ' mm, next throw ' + mm(m.d2) + ' mm on the other side.' }; }
        m = KN.measure(assign(p, { part: 2 }));
        return { row: { part: 2, Rc: Math.round(m.Rc) }, q: p.Cq * p.Vq, rq: m.Rc + p.G, say: 'With ' + Math.round(m.Rc) + ' Ω across the galvanometer the spot just returns to zero without crossing it.' };
      },
      cols: [{ label: 'part', get: function (r) { return ['steady', 'throw', 'CDR'][r.part]; } },
        { label: 'R (Ω) / V (V)', get: function (r) { return r.part === 0 ? r.R : r.part === 1 ? r.V.toFixed(1) : r.Rc; } },
        { label: 'd or d1 (mm)', get: function (r) { return r.part === 0 ? r.phi.toFixed(1) : r.part === 1 ? r.d1.toFixed(1) : '—'; } },
        { label: 'd2 (mm)', get: function (r) { return r.part === 1 ? r.d2.toFixed(1) : '—'; } }],
      ok: function (rows) { var a = rows.filter(function (r) { return r.part === 0; }), b = rows.filter(function (r) { return r.part === 1; }), c = rows.filter(function (r) { return r.part === 2; });
        return a.length >= 2 && a[0].R !== a[a.length - 1].R && b.length >= 2 && c.length >= 1; },
      needText: 'Take two steady deflections with different R, two capacitor throws and the critical resistance.',
      auto: [[0, { R: 350 }], [0, { R: 850 }], [1, { Vq: 2.0 }], [1, { Vq: 1.5 }], [1, { Vq: 2.5 }], [2, {}]],
      result: function (rows) {
        var a = rows.filter(function (r) { return r.part === 0; }), b = rows.filter(function (r) { return r.part === 1; }), c = rows.filter(function (r) { return r.part === 2; });
        if (!this.ok(rows)) return null;
        var sq = mean(b.map(function (r) { return corr(r) / (p.Cq * r.V * 1e6); }));           // mm per microcoulomb
        var lo = a[0], hi = a[0]; a.forEach(function (r) { if (r.R < lo.R) lo = r; if (r.R > hi.R) hi = r; });
        var G = (hi.R * hi.phi - lo.R * lo.phi) / (lo.phi - hi.phi), vr = p.E * p.r / (p.Rh + p.r);
        var si = mean(a.map(function (r) { return r.phi / (vr / (r.R + G) * 1e6); }));           // mm per microampere
        return { label: 'Charge sensitivity', value: sq, unit: 'mm/µC', digits: 1, truth: HK.TEXTBOOK.w7_bg_sq(p) * 1e-3,
          note: 'From the throws corrected by (1 + λ/2). The two steady deflections give the galvanometer resistance ' + rnd(G, 0) + ' Ω and the current sensitivity ' + rnd(si, 0) +
            ' mm/µA, so the period should be 2π Si / Sq = ' + rnd(2 * Math.PI * si / sq, 2) + ' s. Critical damping resistance: ' + c[c.length - 1].Rc + ' Ω.' };
      },
      graph: null, tol: 0.02,
      formula: 'Sq = d₁ (1 + λ/2) / (C V),   Si = d / i,   Sq = Si · 2π / T', formulaNote: 'λ = ln(d₁ / d₂), the logarithmic decrement per half swing'
    };
  } else if (MODE === 1) {
    PLAN = {
      parts: null,
      controls: [[{ key: 'tl', label: 'Leakage time', min: 0, max: 60, step: 5, unit: 's', digits: 0, def: 0 }]],
      act: ['Charge, leak and discharge'],
      take: function (part, v) { var m = KN.measure(assign(p, { tl: v.tl }));
        if (m.d1 > SCALE_HALF) return { err: 'The throw goes off the scale.' };
        if (mm(m.d1) < 5) return { err: 'Almost no charge is left after this time: the throw is too small to read. Use a shorter time.' };
        return { row: { t: v.tl, d: mm(m.d1) }, q: m.q, rq: 0, wait: v.tl, say: (v.tl ? 'After leaking for ' + v.tl + ' s the throw is ' : 'With no leakage the throw is ') + mm(m.d1) + ' mm.' }; },
      cols: [{ label: 't (s)', get: function (r) { return r.t; } }, { label: 'throw d (mm)', get: function (r) { return r.d.toFixed(1); } },
        { label: 'ln(d₀/d)', get: function (r) { var d0 = d0of(S.rows); return d0 && r.t > 0 ? Math.log(d0 / r.d).toFixed(3) : (r.t === 0 ? '0' : '—'); } }],
      ok: function (rows) { return !!d0of(rows) && rows.filter(function (r) { return r.t > 0; }).length >= 3; },
      needText: 'Take the throw with no leakage (t = 0) and at least three leakage times.',
      auto: [[0, { tl: 0 }], [0, { tl: 10 }], [0, { tl: 20 }], [0, { tl: 30 }], [0, { tl: 40 }]],
      result: function (rows) { var d0 = d0of(rows), sxx = 0, sxy = 0; if (!this.ok(rows)) return null;
        rows.forEach(function (r) { if (r.t > 0) { sxx += r.t * r.t; sxy += r.t * Math.log(d0 / r.d); } });
        return { label: 'High resistance', value: sxx / (p.Cl * sxy) / 1e6, unit: 'MΩ', digits: 1, truth: p.Rx / 1e6,
          note: 'From the slope of ln(d₀/d) against t, which is 1/(RC) with C = ' + rnd(p.Cl * 1e6, 2) + ' µF. The time constant RC is ' + rnd(sxx / sxy, 1) + ' s.' }; },
      graph: { x: function (r) { return r.t; }, y: function (r) { var d0 = d0of(S.rows); return d0 ? Math.log(d0 / r.d) : 0; }, xlabel: 'leakage time t (s)', ylabel: 'ln(d₀ / d)' },
      tol: 0.03, formula: 'R = t / (C ln(d₀ / d))', formulaNote: 'd₀ is the throw with no leakage, d the throw after leaking for t'
    };
  } else if (MODE === 2 || MODE === 3) {
    var RAY = MODE === 2;
    PLAN = {
      parts: null,
      controls: [[RAY ? { key: 'rs', label: 'Small resistance r in the coil arm', min: 0.02, max: 0.07, step: 0.01, unit: 'Ω', digits: 2, def: 0.05 }
        : { key: 'Ip', label: 'Primary current', min: 0.2, max: 0.9, step: 0.05, unit: 'A', digits: 2, def: 0.5 }]],
      act: [RAY ? 'Break the battery key, then read the steady deflection' : 'Reverse the current, then read the steady deflection'],
      take: function (part, v) { var m = KN.measure(assign(p, v));
        if (m.d1 > SCALE_HALF || m.phi > SCALE_HALF) return { err: 'The spot goes off the scale. ' + (RAY ? 'Use a smaller r.' : 'Reduce the primary current.') };
        var row = { set: RAY ? v.rs : v.Ip, d1: mm(m.d1), d2: mm(m.d2), phi: mm(m.phi), T: rnd(m.T, 2) };
        return { row: row, q: m.q, rq: KN.setup(assign(p, v)).rq, steady: m.phi, say: 'Throw ' + row.d1 + ' mm, next ' + row.d2 + ' mm; steady deflection ' + row.phi + ' mm; period on open circuit ' + row.T + ' s.' }; },
      cols: [{ label: RAY ? 'r (Ω)' : 'I (A)', get: function (r) { return r.set.toFixed(2); } }, { label: 'θ₁ (mm)', get: function (r) { return r.d1.toFixed(1); } },
        { label: 'θ₂ (mm)', get: function (r) { return r.d2.toFixed(1); } }, { label: 'φ (mm)', get: function (r) { return r.phi.toFixed(1); } }, { label: 'T (s)', get: function (r) { return r.T.toFixed(2); } }],
      ok: function (rows) { return rows.length >= 3; }, needText: 'Take at least three readings with different settings.',
      auto: RAY ? [[0, { rs: 0.03 }], [0, { rs: 0.05 }], [0, { rs: 0.07 }]] : [[0, { Ip: 0.4 }], [0, { Ip: 0.6 }], [0, { Ip: 0.8 }]],
      result: function (rows) { if (rows.length < 3) return null;
        var v = mean(rows.map(function (r) { return RAY ? r.set * r.T / (2 * Math.PI) * corr(r) / r.phi : p.r3 * r.T / (4 * Math.PI) * corr(r) / r.phi; })) * 1000;
        return { label: RAY ? 'Self-inductance of the coil' : 'Mutual inductance of the pair', value: v, unit: 'mH', digits: 2, truth: (RAY ? p.Lx : p.Mx) * 1000,
          note: RAY ? 'L = (r T / 2π)(θ₁ / φ)(1 + λ/2), the mean of ' + rows.length + ' readings.' : 'M = (T / 2π)(r / 2)(θ₁ / φ)(1 + λ/2) with the standard low resistance r = ' + p.r3 + ' Ω, the mean of ' + rows.length + ' readings.' }; },
      graph: null, tol: 0.02,
      formula: RAY ? 'L = (r T / 2π) (θ₁ / φ) (1 + λ/2)' : 'M = (T / 2π) (r / 2) (θ₁ / φ) (1 + λ/2)', formulaNote: 'θ₁ the throw, φ the steady deflection, λ = ln(θ₁ / θ₂), T the period on open circuit'
    };
  } else if (MODE === 4) {
    var AREA = Math.PI * p.re * p.re, RT = p.Rs2 + p.G;
    PLAN = {
      parts: ['Coil plane vertical (cuts the horizontal field)', 'Coil plane horizontal (cuts the vertical field)'],
      controls: [[], []], act: ['Release the coil and read the throw', 'Release the coil and read the throw'],
      take: function (part) { var m = KN.measure(assign(p, { axis: part }));
        if (m.d1 > SCALE_HALF) return { err: 'The throw goes off the scale.' };
        return { row: { part: part, d1: mm(m.d1), d2: mm(m.d2) }, q: m.q, rq: RT, flip: part, say: 'Throw ' + mm(m.d1) + ' mm, next ' + mm(m.d2) + ' mm on the other side.' }; },
      cols: [{ label: 'coil plane', get: function (r) { return r.part ? 'horizontal' : 'vertical'; } }, { label: 'θ₁ (mm)', get: function (r) { return r.d1.toFixed(1); } },
        { label: 'θ₂ (mm)', get: function (r) { return r.d2.toFixed(1); } }, { label: 'θ₁(1+λ/2) (mm)', get: function (r) { return corr(r).toFixed(1); } }],
      ok: function (rows) { return rows.filter(function (r) { return r.part === 0; }).length >= 2 && rows.filter(function (r) { return r.part === 1; }).length >= 2; },
      needText: 'Take at least two throws in each position of the coil.', repeat: true,
      auto: [[0, {}], [0, {}], [1, {}], [1, {}]],
      result: function (rows) { if (!this.ok(rows)) return null;
        var h = mean(rows.filter(function (r) { return r.part === 0; }).map(corr)), v = mean(rows.filter(function (r) { return r.part === 1; }).map(corr));
        var f = KQ * 1e-3 * RT / (2 * p.Ne * AREA) * 1e6;                                   // microtesla per corrected millimetre
        return { label: 'Angle of dip', value: Math.atan2(v, h) * 180 / Math.PI, unit: '°', digits: 1, truth: HK.TEXTBOOK.w7_bg_dip(p),
          note: 'tan δ = θ_V / θ_H. With the charge constant on the card (' + rnd(KQ * 1e6, 3) + ' nC per mm) the components are B_H = ' + rnd(h * f, 1) + ' µT and B_V = ' + rnd(v * f, 1) + ' µT.' }; },
      graph: null, tol: 0.02, formula: 'tan δ = θ_V / θ_H,   B = k_q θ (1 + λ/2) R / (2 N A)', formulaNote: 'N = ' + Math.round(p.Ne) + ' turns, A = π r², R = ' + Math.round(RT) + ' Ω in the galvanometer circuit'
    };
  } else {
    var FB = KQ * 1e-3 * (p.Rs2 + p.G) / (2 * p.Nc * Math.PI * p.rc * p.rc) * 1000;         // millitesla per corrected millimetre
    PLAN = {
      parts: null,
      controls: [[{ key: 'x', label: (HALL ? 'Hall probe' : 'Search coil') + ' position from the centre', min: -25, max: 25, step: 2.5, unit: 'cm', digits: 1, def: 0 }]],
      act: [HALL ? 'Read the gaussmeter' : 'Reverse the current and read the throw'],
      take: function (part, v) { var x = v.x / 100, m = KN.measure(assign(p, { x: x }));
        if (HALL) return { row: { x: v.x, B: rnd(m.B * 1000, 2) }, gauss: m.B, say: 'The gaussmeter reads ' + (m.B * 1000).toFixed(2) + ' mT at x = ' + v.x + ' cm.' };
        if (m.d1 > SCALE_HALF) return { err: 'The throw goes off the scale.' };
        var row = { x: v.x, d1: mm(m.d1), d2: mm(m.d2) }; row.B = corr(row) * FB;
        return { row: row, q: m.q, rq: p.Rs2 + p.G, say: 'Throw ' + row.d1 + ' mm, next ' + row.d2 + ' mm: B = ' + row.B.toFixed(2) + ' mT at x = ' + v.x + ' cm.' }; },
      cols: HALL ? [{ label: 'x (cm)', get: function (r) { return r.x.toFixed(1); } }, { label: 'B (mT)', get: function (r) { return r.B.toFixed(2); } }]
        : [{ label: 'x (cm)', get: function (r) { return r.x.toFixed(1); } }, { label: 'θ₁ (mm)', get: function (r) { return r.d1.toFixed(1); } }, { label: 'θ₂ (mm)', get: function (r) { return r.d2.toFixed(1); } }, { label: 'B (mT)', get: function (r) { return r.B.toFixed(2); } }],
      ok: function (rows) { return rows.length >= 7 && rows.some(function (r) { return r.x === 0; }) && rows.some(function (r) { return Math.abs(r.x) >= 20; }); },
      needText: 'Take at least seven positions, including the centre (x = 0) and one beyond the end (20 cm or more).',
      auto: [-25, -20, -15, -10, 0, 10, 15, 20, 25].map(function (x) { return [0, { x: x }]; }),
      result: function (rows) { if (!this.ok(rows)) return null;
        var c = rows.filter(function (r) { return r.x === 0; }), s = rows.slice().sort(function (a, b) { return a.x - b.x; }), g = 0, gx = 0, i, gg;
        for (i = 1; i < s.length; i++) { if (s[i].x === s[i - 1].x) continue; gg = Math.abs((s[i].B - s[i - 1].B) / (s[i].x - s[i - 1].x)); if (gg > g) { g = gg; gx = (s[i].x + s[i - 1].x) / 2; } }
        return { label: 'Field at the centre of the solenoid', value: mean(c.map(function (r) { return r.B; })), unit: 'mT', digits: 2, truth: HK.TEXTBOOK.w7_bg_bsol(assign(p, { x: 0 })) * 1000,
          note: 'The field is nearly uniform in the middle and falls towards the ends. The steepest gradient between your readings is ' + rnd(g, 3) + ' mT/cm, near x = ' + rnd(gx, 1) + ' cm (the end of the winding is at ' + rnd(p.Ls * 50, 0) + ' cm).' +
            (HALL ? '' : ' B = k_q θ₁(1 + λ/2) R / (2 N A) with k_q = ' + rnd(KQ * 1e6, 3) + ' nC per mm from the calibration card.') }; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.B; }, xlabel: 'position x (cm)', ylabel: 'B (mT)' },
      tol: 0.02, formula: 'B = (μ₀ n I / 2)(cos α₁ − cos α₂)', formulaNote: HALL ? 'read directly by the Hall-probe gaussmeter' : 'measured as B = k_q θ₁ (1 + λ/2) R / (2 N A) from the throw on reversing the current'
    };
  }
  function d0of(rows) { var z = rows.filter(function (r) { return r.t === 0; }); return z.length ? mean(z.map(function (r) { return r.d; })) : 0; }
  (PLAN.controls || []).forEach(function (cs) { cs.forEach(function (c) { st.vals[c.key] = c.def; }); });

  /* ================================================================ human actions */
  // the two set-up actions; with the Hall probe they are the gaussmeter and the solenoid supply instead
  function lampOn() { if (busy() || st.lamp) return Promise.resolve();
    if (HALL) return S.hand.tap(gaussG).then(function () { st.lamp = true; showGauss(0); S.say('The gaussmeter is on and reads zero with the probe far from the solenoid.'); S.render(); });
    return S.hand.tap(lswitch).then(function () { st.lamp = true; bulb.material.color.setHex(0xffe9a0); beam.visible = true; S.say('The lamp is on: the spot of light rests at zero on the scale.'); S.render(); }); }
  function freeCoil() { if (busy() || st.free) return Promise.resolve();
    if (!st.lamp) { S.say(HALL ? 'Switch the gaussmeter on first.' : 'Switch the lamp on first.'); return Promise.resolve(); }
    if (HALL) return S.hand.tap(supplyG.userData.knob).then(function () { st.free = true; S.say('The solenoid carries ' + p.Is + ' A.'); S.render(); });
    return S.hand.tap(damp.userData.plug).then(function () { st.free = true; damp.set(false); S.say('The damping key is open: the coil is free to swing.'); S.render(); }); }
  function swing(q, rq, steady) {                          // play the motion of the spot (at 8 times real speed)
    if (S.fast) { st.spot = 0; return Promise.resolve(); }
    var s = { t: 0, theta: 0, omega: p.Kc * q / p.Im, b: KN.damping(p, rq) }, T0 = KN.t0(p), last = 0;
    return S.tween(2600, function (k) { var t = k * T0 * 1.6, n = Math.max(1, Math.round((t - last) / (T0 / 400))), i, nx;
      for (i = 0; i < n; i++) { nx = KN.rk4(s.theta, s.omega, p, s.b, 0, (t - last) / n); s.theta = nx[0]; s.omega = nx[1]; } last = t; st.spot = 2 * p.D * s.theta; })
      .then(function () { if (steady === undefined) return S.tween(500, function (k) { st.spot = st.spot * (1 - k); });
        var a = st.spot; return S.tween(700, function (k) { st.spot = a + (steady - a) * k; }).then(function () { return S.wait(700); }).then(function () { return S.tween(400, function (k) { st.spot = steady * (1 - k); }); }); })
      .then(function () { st.spot = 0; });
  }
  function settle(d) { if (S.fast) return Promise.resolve(); return S.tween(900, function (k) { st.spot = d * (1 - Math.exp(-5 * k)); }).then(function () { return S.wait(700); }).then(function () { return S.tween(400, function (k) { st.spot = d * (1 - k); }); }); }
  function setVal(c, v) {
    if (busy()) return Promise.resolve();
    if (!(v >= c.min - 1e-9 && v <= c.max + 1e-9)) { S.say(c.label + ' runs from ' + c.min + ' to ' + c.max + ' ' + c.unit + '.'); return Promise.resolve(); }
    var a = st.vals[c.key];
    return (knobMesh ? S.hand.tap(knobMesh) : Promise.resolve()).then(function () { return S.tween(500, function (k) { st.vals[c.key] = a + (v - a) * k; if (MODE === 5 && moveCoil) moveCoil(st.vals.x / 100); }); })
      .then(function () { st.vals[c.key] = v; if (MODE === 5 && moveCoil) moveCoil(v / 100); if (st.am && c.key === 'Ip') st.am.set(v); S.render(); });
  }
  function take() {
    if (busy()) return Promise.resolve(null);
    if (!st.lamp || !st.free) { S.say('Finish the set-up step first.'); return Promise.resolve(null); }
    var part = st.part, v = assign(st.vals), r = PLAN.take(part, v), i;
    if (r.err) { S.say(r.err); return Promise.resolve(null); }
    if (!PLAN.repeat) for (i = 0; i < S.rows.length; i++) if (JSON.stringify(strip(S.rows[i])) === JSON.stringify(strip(r.row))) { S.say('You already have this reading. Change the setting first.'); return Promise.resolve(null); }
    st.busyRead = true;
    var seq = HALL ? S.hand.tap(gaussG) : S.hand.tap(tapKnob).then(function () { lever.rotation.z = 0; return S.wait(120); }).then(function () { lever.rotation.z = 0.12; });
    if (r.wait) seq = seq.then(function () { S.say('Leaking through the high resistance for ' + r.wait + ' s …'); return S.wait(900); });
    if (r.flip !== undefined && moveCoil) seq = seq.then(function () { return S.tween(260, function (k) { moveCoil(r.flip, k); }); });
    if (r.gauss !== undefined) seq = seq.then(function () { showGauss(r.gauss); return S.wait(300); });
    else if (r.q !== undefined) seq = seq.then(function () { return swing(r.q, r.rq, r.steady); });
    else if (r.steady !== undefined) seq = seq.then(function () { return settle(r.steady); });
    return seq.then(function () { st.busyRead = false; S.addRow(r.row); S.say(r.say); return r.row; }, function () { st.busyRead = false; return null; });
  }
  function strip(r) { var o = {}, k; for (k in r) o[k] = r[k]; return o; }
  function setPart(i) { if (busy()) return; st.part = i; if (MODE === 4 && moveCoil) moveCoil(i, 0); S.render(); }

  var plist = PLAN.parts || [''];
  return {
    camera: { pos: [0.12, 1.0, 1.3], look: [0.04, 0.08, -0.3] },
    views: { bench: [[0.12, 1.0, 1.3], [0.04, 0.08, -0.3]], galvo: [[GX + 0.1, 0.4, GZ + 0.62], [GX, 0.16, GZ]], scale: [[SX, 0.4, SZ + 0.62], [SX, SY, SZ]],
      acc: [[AX + 0.05, 0.5, AZ + 0.7], [AX + 0.02, 0.05, AZ]], keys: [[KX - 0.05, 0.3, KZ + 0.4], [KX - 0.06, 0.02, KZ]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: S.lab.theory, formula: PLAN.formula, formulaNote: PLAN.formulaNote,
      more: HALL ? ['A Hall probe gives a voltage proportional to the field through it; the gaussmeter shows that field directly, here to 0.01 mT.', 'Keep the flat of the probe at right angles to the axis, and check the zero with the probe far from the solenoid.', 'This bench uses an illustrative solenoid; its turns per metre are the lab\'s own hidden value.'] : ['The first throw is read as the spot turns round; the next throw on the other side gives the damping. The scale is read to half a millimetre.',
        'The galvanometer must be at rest before each reading: close the damping key to stop the coil, then open it again.',
        'This bench uses an illustrative instrument: its constants are the lab\'s own, not those of a named maker.' + (V_.note ? ' ' + V_.note : '')],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 120) + (S.lab.aim.length > 120 ? '…' : ''), HALL ? 'Gaussmeter read to 0.01 mT.' : 'Scale 1 m from the mirror, read to 0.5 mm.', PLAN.formula], columns: PLAN.cols },
    graph: PLAN.graph ? { x: PLAN.graph.x, y: PLAN.graph.y, xlabel: PLAN.graph.xlabel, ylabel: PLAN.graph.ylabel, line: function () { return null; } } : undefined,
    result: function (rows) { return PLAN.result(rows); },
    tol: PLAN.tol,
    chips: HALL ? ['How does a Hall probe work?', 'Why is the field half at the end?', 'Check my readings', 'Where is dB/dx greatest?'] : ['What is a ballistic throw?', 'Why correct by (1 + λ/2)?', 'Check my readings', 'What does the damping key do?'],
    viva: [],
    askState: function () { return { experiment: S.lab.title, lamp_on: st.lamp, coil_free: st.free, part: plist[st.part] || 'single part', settings: assign(st.vals), spot_mm: mm(st.spot), readings_taken: S.rows.length }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          if (HALL) {
            u.h2('Gaussmeter and solenoid');
            u.p('The Hall probe reads the field directly, so the ballistic galvanometer and its lamp stay unused on the bench. Switch the gaussmeter on, check its zero, then switch the solenoid current on.');
            u.task('1. Switch on and zero the gaussmeter', st.lamp, st.lamp ? 'Reads zero' : 'Off').add(u.button(st.lamp ? 'Gaussmeter on' : 'Switch the gaussmeter on', function () { S.focus('acc'); lampOn(); }, !st.lamp, st.lamp || S.hand.busy));
            u.task('2. Switch the solenoid current on', st.free, st.free ? 'Current on' : 'Supply off').add(u.button(st.free ? 'Current on' : 'Switch the current on', function () { S.focus('acc'); freeCoil(); }, st.lamp && !st.free, st.free || !st.lamp || S.hand.busy));
          } else {
          u.h2('Lamp, scale and galvanometer');
          u.p('The spot of light from the lamp is reflected by the coil\'s mirror on to the scale. Switch the lamp on, then open the damping key so the coil is free.');
          u.task('1. Switch the lamp on', st.lamp, st.lamp ? 'Spot at zero' : 'Lamp off').add(u.button(st.lamp ? 'Lamp on' : 'Switch the lamp on', function () { S.focus('scale'); lampOn(); }, !st.lamp, st.lamp || S.hand.busy));
          u.task('2. Open the damping key', st.free, st.free ? 'Coil free' : 'Coil short-circuited').add(u.button(st.free ? 'Key open' : 'Open the damping key', function () { S.focus('keys'); freeCoil(); }, st.lamp && !st.free, st.free || !st.lamp || S.hand.busy));
          }
          u.note(accName + ': ' + accInfo);
          u.next('Next: take the readings', st.lamp && st.free);
        }, ok: function () { return st.lamp && st.free; }, auto: function () { return lampOn().then(freeCoil); } },
      { id: 'read', title: 'Readings', view: HALL ? 'acc' : 'scale', render: function (u) {
          u.h2('Take the readings');
          if (PLAN.parts) { u.p('This experiment has ' + PLAN.parts.length + ' parts. Choose the part, then take its readings.');
            u.row.apply(u, PLAN.parts.map(function (t, i) { return u.button((i + 1) + '. ' + t, function () { setPart(i); }, st.part === i, S.hand.busy || st.busyRead); })); }
          var cs = PLAN.controls[st.part] || [];
          cs.forEach(function (c) { var tg = { v: st.vals[c.key] };
            u.slider(c.label, c.min, c.max, c.step, function () { return tg.v; }, function (v) { tg.v = v; }, c.unit, c.digits);
            u.row(u.button('Set it', function () { S.focus('acc'); setVal(c, tg.v); }, false, S.hand.busy || st.busyRead)); });
          u.row(u.button(PLAN.act[st.part], function () { S.focus(HALL ? 'acc' : 'scale'); take(); }, true, S.hand.busy || st.busyRead));
          u.live(function () { return HALL ? 'Probe at ' + rnd(st.vals.x, 1) + ' cm' : 'Spot at ' + mm(st.spot).toFixed(1) + ' mm'; });
          u.h3('Observations'); u.table();
          if (!PLAN.ok(S.rows)) u.p(PLAN.needText);
          u.next('Next: the result', PLAN.ok(S.rows));
        }, ok: function () { return PLAN.ok(S.rows); },
        auto: function () { return PLAN.auto.reduce(function (pr, a) { return pr.then(function () { st.part = a[0]; var cs = PLAN.controls[a[0]] || [];
          return cs.reduce(function (q, c) { return q.then(function () { return a[1][c.key] === undefined ? null : setVal(c, a[1][c.key]); }); }, Promise.resolve()).then(take); }); }, Promise.resolve()); } }
    ],
    tick: function () {
      drawScale(st.spot, st.lamp && !HALL); if (st.lamp && !HALL) setBeam(st.spot);
      hudD.set(HALL ? (st.gauss && st.gauss !== '----' ? st.gauss + ' mT' : '—') : (st.lamp ? mm(st.spot).toFixed(1) + ' mm' : 'lamp off'));
      var cs = PLAN.controls[st.part] || []; hudS.set(cs.length ? rnd(st.vals[cs[0].key], cs[0].digits) + ' ' + cs[0].unit : (PLAN.parts ? 'part ' + (st.part + 1) : '—'));
    }
  };
});
