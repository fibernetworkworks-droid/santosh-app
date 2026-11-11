/* Prayogshala studio module: W8 ELECTRON BENCH (B.Sc. modern physics, pack ug_modern_w8).
   One bench for the vacuum-tube and electron-beam set-ups:
     w8-diode-work-function   directly heated diode, filament and anode supplies, microammeter, optical pyrometer
     w8-mercury-ionisation    mercury-vapour tube with an ion collector and its control unit
     w8-em-thomson            cathode-ray tube between Helmholtz coils, plate and coil supplies
     w8-em-magnetron          cylindrical diode inside a solenoid
     w8-em-focusing           cathode-ray tube inside a long solenoid; its family variant uses a bar magnet and a
                              deflection magnetometer instead (meth = 1)
   Every number comes from the lab's kernel (HoolaKernels.K[S.lab.kernel]) on the lab's own params. */
HoolaStudio.define('w8-electron-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K[S.lab.kernel], assign = HK.assign;
  var p = HK.paramsFor(S.lab.kernel, S.lab.params);
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var MODE = { 'w8-diode-work-function': 'diode', 'w8-mercury-ionisation': 'ion', 'w8-em-thomson': 'thomson',
    'w8-em-magnetron': 'mag', 'w8-em-focusing': 'focus' }[BASE] || 'diode';
  if (MODE === 'focus' && p.meth > 0.5) MODE = 'bar';
  var MU0 = 1.25663706212e-6, KB = 1.380649e-23, QE = 1.602176634e-19, PI = Math.PI;

  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function wp(o) { var v = new T.Vector3(); o.updateMatrixWorld(true); o.getWorldPosition(v); return v; }

  // ================================================================ controls of each set-up
  var CTRL = {
    diode: [{ k: 'If', label: 'FILAMENT A', min: 1.8, max: 2.6, step: 0.01, d: 2, unit: 'A', v: 1.8 },
      { k: 'Va', label: 'ANODE V', min: 0, max: 150, step: 1, d: 0, unit: 'V', v: 0 }],
    ion: [{ k: 'V', label: 'ACCEL. V', min: 0, max: 20, step: 0.1, d: 1, unit: 'V', v: 0 }],
    thomson: [{ k: 'Vp', label: 'PLATES V', min: 0, max: 200, step: 1, d: 0, unit: 'V', v: 0 },
      { k: 'Ic', label: 'COIL A', min: 0, max: 1, step: 0.001, d: 3, unit: 'A', v: 0 }],
    mag: [{ k: 'Va', label: 'ANODE V', min: 2, max: 12, step: 0.5, d: 1, unit: 'V', v: p.Va },
      { k: 'Is', label: 'SOLENOID A', min: 0, max: 1, step: 0.01, d: 2, unit: 'A', v: 0 }],
    focus: [{ k: 'Va', label: 'ACCEL. V', min: 400, max: 1200, step: 10, d: 0, unit: 'V', v: p.Va },
      { k: 'Ic', label: 'SOLENOID A', min: 0, max: 1, step: 0.001, d: 3, unit: 'A', v: 0 }],
    bar: [{ k: 'x', label: 'MAGNET cm', min: 12, max: 25, step: 0.5, d: 1, unit: 'cm', v: 25 }]
  }[MODE];
  var st = { on: false, warm: false, traced: false };
  CTRL.forEach(function (c) { st[c.k] = c.v; });
  st.place = 'tube';               // bar method: 'tube' or 'meter' at the test position
  st.flip = 1;                     // bar method: which pole faces the tube

  function q() {                   // the kernel's params at the present settings (SI)
    var o = {};
    CTRL.forEach(function (c) { o[c.k] = c.k === 'x' ? st[c.k] / 100 : st[c.k]; });
    return assign(p, o);
  }
  function view() { return KN.view(KN.init(q(), {}), q(), {}); }

  // ================================================================ readings, rounded to each instrument
  function read() {
    var v = view();
    if (MODE === 'diode') return { T: st.on ? Math.round(v.T) : 300, Ia: st.on ? rnd(v.Ia * 1e6, 2) : 0 };
    if (MODE === 'ion') return { I: st.warm ? rnd(v.I_nA, 2) : 0 };
    if (MODE === 'thomson') return { y: st.on ? rnd(v.y_mm * 2, 0) / 2 : 0 };
    if (MODE === 'mag') return { Ia: st.on ? rnd(v.Ia_mA, 3) : 0 };
    if (MODE === 'focus') return { ell: st.on ? rnd(v.ell_mm * 2, 0) / 2 : 0 };
    return { y2: st.on ? rnd(2 * v.y_mm * 2, 0) / 2 : 0, th: rnd(v.thm * 2, 0) / 2 };
  }

  // ================================================================ the tube on the left
  var tubeG = new T.Group(); S.scene.add(tubeG);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xe6edf1, roughness: 0.05, transmission: 0.75, thickness: 0.01,
    transparent: true, opacity: 0.35 });
  var filM = new T.MeshStandardMaterial({ color: 0x6b5a2a, roughness: 0.4, emissive: 0x000000 });
  var glowM = new T.MeshBasicMaterial({ color: 0x6fb2ff, transparent: true, opacity: 0, depthWrite: false, blending: T.AdditiveBlending });
  var spotM = new T.MeshBasicMaterial({ color: 0x7dff9a, transparent: true, opacity: 0, depthWrite: false });
  var spot = null, line = null, screenX = 0;
  var coilParts = [];

  function valve(x, z, kind) {
    var g = new T.Group(); g.position.set(x, 0, z); tubeG.add(g);
    var base = S.rounded(0.16, 0.16, 0.03, 0.01, M.bakelite); base.rotation.x = -Math.PI / 2; base.position.y = 0.015; g.add(base);
    var sock = S.mesh(new T.CylinderGeometry(0.032, 0.034, 0.03, 32), M.blackPlastic); sock.position.y = 0.045; g.add(sock);
    var bulb = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.12, 32), glassM); bulb.position.y = 0.12; g.add(bulb);
    var top = S.mesh(new T.SphereGeometry(0.03, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), glassM); top.position.y = 0.18; g.add(top);
    var tip = S.mesh(new T.ConeGeometry(0.004, 0.012, 12), glassM); tip.position.y = 0.214; g.add(tip);
    var anode = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.07, 28, 1, true), new T.MeshStandardMaterial({ color: 0x8c9096, roughness: 0.45, metalness: 0.8, side: T.DoubleSide }));
    anode.position.y = 0.12; g.add(anode);
    var fil = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, 0.08, 8), filM); fil.position.y = 0.12; g.add(fil);
    var glow = S.mesh(new T.CylinderGeometry(0.015, 0.015, 0.07, 20, 1, true), glowM, false, false); glow.position.y = 0.12; g.add(glow);
    if (kind === 'ion') {
      glowM.color.setHex(0x8fb8ff);
      var hg = S.mesh(new T.SphereGeometry(0.004, 12, 8), M.chrome); hg.position.set(0.012, 0.064, 0.01); g.add(hg);
      var col = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.002, 20), M.steel); col.position.y = 0.17; g.add(col);
    }
    for (var i = 0; i < 4; i++) { var pin = S.terminal([0, 0, 0], i % 2 ? 'black' : 'red'); g.add(pin); pin.position.set(-0.06 + i * 0.04, 0.03, 0.06); }
    var lb = S.label(kind === 'ion' ? 'Hg VAPOUR TUBE' : 'DIODE VALVE', { w: 0.1, ratio: 0.18, color: '#e9e9e9' });
    lb.position.set(0, 0.016, 0.081); g.add(lb);
    S.contact(0.22, 0.22, x, z, 0.5);
    return g;
  }
  function coilRing(r, w, nTurn, color) {        // a wound coil: a stack of copper turns on a former
    var g = new T.Group(); var cu = new T.MeshStandardMaterial({ color: color || 0xb8733a, roughness: 0.35, metalness: 0.85 });
    for (var i = 0; i < nTurn; i++) { var t = S.mesh(new T.TorusGeometry(r, w / nTurn / 2, 8, 40), cu); t.position.y = (i - (nTurn - 1) / 2) * w / nTurn; t.rotation.x = Math.PI / 2; g.add(t); }
    return g;
  }
  function crt(x0, x1, z, y) {                    // a cathode-ray tube lying along x, screen at x1
    var g = new T.Group(); tubeG.add(g);
    var len = x1 - x0, neck = S.mesh(new T.CylinderGeometry(0.018, 0.018, len * 0.62, 28), glassM);
    neck.rotation.z = Math.PI / 2; neck.position.set(x0 + len * 0.31, y, z); g.add(neck);
    var cone = S.mesh(new T.CylinderGeometry(0.045, 0.018, len * 0.33, 32, 1, true), glassM);
    cone.rotation.z = -Math.PI / 2; cone.position.set(x0 + len * 0.785, y, z); g.add(cone);
    var scrM = new T.MeshStandardMaterial({ color: 0x1c3324, roughness: 0.6, emissive: 0x0a1a10 });
    var scr = S.mesh(new T.CylinderGeometry(0.045, 0.045, 0.004, 40), scrM); scr.rotation.z = Math.PI / 2; scr.position.set(x1, y, z); g.add(scr);
    var grat = S.canvasTex(256, 256, function (cx, w, h) { cx.clearRect(0, 0, w, h); cx.strokeStyle = 'rgba(200,255,210,.55)'; cx.lineWidth = 1;
      for (var i = 0; i <= 20; i++) { var u = 28 + i * 10; cx.beginPath(); cx.moveTo(u, 120); cx.lineTo(u, i % 5 ? 136 : 144); cx.stroke(); cx.beginPath(); cx.moveTo(120, u); cx.lineTo(i % 5 ? 136 : 144, u); cx.stroke(); }
      cx.beginPath(); cx.moveTo(28, 128); cx.lineTo(228, 128); cx.moveTo(128, 28); cx.lineTo(128, 228); cx.stroke(); });
    var gp = new T.Mesh(new T.CircleGeometry(0.043, 40), new T.MeshBasicMaterial({ map: grat, transparent: true }));
    gp.rotation.y = Math.PI / 2; gp.position.set(x1 + 0.0025, y, z); g.add(gp);
    spot = S.mesh(new T.CircleGeometry(0.0022, 20), spotM, false, false); spot.rotation.y = Math.PI / 2; spot.position.set(x1 + 0.003, y, z); g.add(spot);
    line = S.mesh(new T.PlaneGeometry(0.0016, 1), spotM, false, false); line.rotation.y = Math.PI / 2; line.position.set(x1 + 0.003, y, z); line.visible = false; g.add(line);
    screenX = x1;
    var gun = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.05, 16), M.steel); gun.rotation.z = Math.PI / 2; gun.position.set(x0 + 0.04, y, z); g.add(gun);
    var cap = S.mesh(new T.CylinderGeometry(0.022, 0.022, 0.03, 24), M.bakelite); cap.rotation.z = Math.PI / 2; cap.position.set(x0 - 0.01, y, z); g.add(cap);
    [x0 + 0.05, x1 - 0.06].forEach(function (cx) {
      var cr = S.rounded(0.05, 0.07, 0.03, 0.006, M.darkWood); cr.rotation.x = -Math.PI / 2; cr.position.set(cx, 0.015, z); g.add(cr);
      var post = S.mesh(new T.BoxGeometry(0.012, y - 0.03, 0.04), M.darkWood); post.position.set(cx, (y - 0.03) / 2 + 0.03, z); g.add(post);
    });
    S.contact(len + 0.1, 0.14, (x0 + x1) / 2, z, 0.45);
    return g;
  }

  var TZ = -0.12, TY = 0.11, pyro = null, magnet = null, mmeter = null, mmNeedle = null;
  if (MODE === 'diode' || MODE === 'ion' || MODE === 'mag') {
    var vg = valve(-0.36, TZ, MODE === 'ion' ? 'ion' : 'diode');
    if (MODE === 'mag') {
      var former = S.mesh(new T.CylinderGeometry(0.06, 0.06, 0.2, 40, 1, true), new T.MeshStandardMaterial({ color: 0xd9c9a3, roughness: 0.7, side: T.DoubleSide }));
      former.position.set(-0.36, 0.14, TZ); tubeG.add(former);
      var wind = coilRing(0.062, 0.18, 18); wind.position.set(-0.36, 0.14, TZ); tubeG.add(wind);
      var flange = S.mesh(new T.TorusGeometry(0.066, 0.005, 8, 40), M.bakelite); flange.rotation.x = Math.PI / 2; flange.position.set(-0.36, 0.235, TZ); tubeG.add(flange);
      var sl = S.label('SOLENOID  n = ' + Math.round(p.n) + ' /m', { w: 0.12, ratio: 0.14, color: '#2a1a0a', bg: '#e9dcb8' });
      sl.position.set(-0.36, 0.05, TZ + 0.0635); tubeG.add(sl);
    }
    if (MODE === 'diode') {       // optical pyrometer on a stand, aimed at the filament
      pyro = new T.Group(); pyro.position.set(-0.12, 0, 0.05); S.scene.add(pyro);
      var pb = S.rounded(0.08, 0.08, 0.012, 0.006, M.iron); pb.rotation.x = -Math.PI / 2; pb.position.y = 0.006; pyro.add(pb);
      var pr = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.12, 12), M.chrome); pr.position.y = 0.066; pyro.add(pr);
      var scope = S.mesh(new T.CylinderGeometry(0.016, 0.018, 0.14, 24), new T.MeshStandardMaterial({ color: 0x2f3a46, roughness: 0.4, metalness: 0.5 }));
      scope.rotation.z = Math.PI / 2; scope.position.set(0, 0.128, 0); pyro.add(scope); pyro.rotation.y = 0.62;
      var pl = S.label('OPTICAL PYROMETER', { w: 0.08, ratio: 0.16, color: '#eef' }); pl.position.set(0, 0.148, 0.0); pl.rotation.x = -Math.PI / 2; pyro.add(pl);
      S.contact(0.12, 0.12, -0.12, 0.05, 0.4);
    }
  } else {
    crt(-0.62, -0.08, TZ, TY);
    if (MODE === 'thomson') {
      [-0.38, -0.27].forEach(function (cx) {
        var hc = coilRing(0.07, 0.02, 5); hc.rotation.z = Math.PI / 2; hc.position.set(cx, TY, TZ); tubeG.add(hc);
        var leg = S.mesh(new T.BoxGeometry(0.02, TY - 0.07 + 0.01, 0.03), M.bakelite); leg.position.set(cx, (TY - 0.06) / 2, TZ); tubeG.add(leg);
      });
      var plates = S.mesh(new T.BoxGeometry(0.02, 0.012, 0.001), M.steel); plates.position.set(-0.42, TY, TZ + 0.003); tubeG.add(plates);
      var hl = S.label('HELMHOLTZ COILS 4.2 mT/A', { w: 0.13, ratio: 0.12, color: '#222', bg: '#e9dcb8' }); hl.position.set(-0.325, 0.012, TZ + 0.06); hl.rotation.x = -Math.PI / 2; tubeG.add(hl);
    } else if (MODE === 'focus') {
      var sol = S.mesh(new T.CylinderGeometry(0.06, 0.06, 0.34, 40, 1, true), new T.MeshStandardMaterial({ color: 0xd9c9a3, roughness: 0.7, side: T.DoubleSide }));
      sol.rotation.z = Math.PI / 2; sol.position.set(-0.33, TY, TZ); tubeG.add(sol);
      var w2 = coilRing(0.062, 0.32, 26); w2.rotation.z = Math.PI / 2; w2.position.set(-0.33, TY, TZ); tubeG.add(w2);
      var fl = S.label('LONG SOLENOID  n = ' + Math.round(p.n) + ' /m', { w: 0.14, ratio: 0.12, color: '#2a1a0a', bg: '#e9dcb8' });
      fl.position.set(-0.33, 0.012, TZ + 0.075); fl.rotation.x = -Math.PI / 2; tubeG.add(fl);
    } else {                      // bar magnet on a scale east of the tube, and the deflection magnetometer
      magnet = new T.Group(); S.scene.add(magnet);
      var mn = S.mesh(new T.BoxGeometry(0.05, 0.012, 0.012), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.4, metalness: 0.4 })); mn.position.x = 0.025; magnet.add(mn);
      var ms = S.mesh(new T.BoxGeometry(0.05, 0.012, 0.012), new T.MeshStandardMaterial({ color: 0x2c5fb4, roughness: 0.4, metalness: 0.4 })); ms.position.x = -0.025; magnet.add(ms);
      var nl = S.label('N', { w: 0.01, ratio: 1, color: '#fff' }); nl.position.set(0.04, 0.0065, 0); nl.rotation.x = -Math.PI / 2; magnet.add(nl);
      magnet.position.set(-0.35, 0.008, TZ - 0.25);
      mmeter = new T.Group(); mmeter.position.set(-0.08, 0, 0.12); S.scene.add(mmeter);
      var box = S.mesh(new T.CylinderGeometry(0.05, 0.052, 0.02, 40), M.darkWood); box.position.y = 0.01; mmeter.add(box);
      var dial = S.canvasTex(256, 256, function (cx, w, h) { cx.fillStyle = '#f6f2e6'; cx.fillRect(0, 0, w, h); cx.strokeStyle = '#222'; cx.fillStyle = '#222';
        for (var a = 0; a < 360; a += 5) { var r = a % 30 ? 110 : 100, t = a * Math.PI / 180; cx.beginPath(); cx.moveTo(128 + Math.cos(t) * 118, 128 + Math.sin(t) * 118); cx.lineTo(128 + Math.cos(t) * r, 128 + Math.sin(t) * r); cx.stroke(); }
        cx.font = '600 16px sans-serif'; cx.textAlign = 'center'; [0, 30, 60, 90].forEach(function (d) { [1, -1].forEach(function (s2) { var t = (s2 * d - 90) * Math.PI / 180; cx.fillText(String(d), 128 + Math.cos(t) * 84, 134 + Math.sin(t) * 84); }); }); });
      var df = new T.Mesh(new T.CircleGeometry(0.045, 48), new T.MeshStandardMaterial({ map: dial })); df.rotation.x = -Math.PI / 2; df.position.y = 0.0205; mmeter.add(df);
      mmNeedle = S.mesh(new T.BoxGeometry(0.0015, 0.001, 0.08), new T.MeshStandardMaterial({ color: 0x1b1b1b })); mmNeedle.position.y = 0.023; mmeter.add(mmNeedle);
      var cover = S.mesh(new T.CylinderGeometry(0.046, 0.046, 0.002, 40), M.glass); cover.position.y = 0.026; mmeter.add(cover);
      var ml = S.label('DEFLECTION MAGNETOMETER', { w: 0.1, ratio: 0.12, color: '#eee' }); ml.position.set(0, 0.01, 0.0525); mmeter.add(ml);
      S.contact(0.13, 0.13, -0.08, 0.12, 0.4);
    }
  }

  // ================================================================ the control unit on the right
  var unit = new T.Group(); S.scene.add(unit); unit.position.set(0.32, 0, -0.06); unit.rotation.y = -0.28;
  var UW = 0.42, UD = 0.26, UH = 0.15, FZ = UD / 2 + 0.006;
  var ucase = S.rounded(UW, UD, UH, 0.012, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5, metalness: 0.12 }));
  ucase.rotation.x = -Math.PI / 2; ucase.position.y = UH / 2 + 0.004; unit.add(ucase);
  var TITLE = { diode: 'DIODE CHARACTERISTICS UNIT', ion: 'IONISATION POTENTIAL UNIT', thomson: 'e/m THOMSON UNIT',
    mag: 'MAGNETRON e/m UNIT', focus: 'e/m MAGNETIC FOCUSING UNIT', bar: 'CRT SUPPLY  ' + Math.round(p.Va) + ' V' }[MODE];
  var face = S.canvasTex(1024, 360, function (x, w, h) { x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 3; x.strokeRect(8, 8, w - 16, h - 16);
    x.fillStyle = '#f1efe8'; x.font = '700 38px "Public Sans", sans-serif'; x.fillText(TITLE, 28, 56);
    x.font = '500 22px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText('POWER', 900, 320); });
  var panel = S.mesh(new T.BoxGeometry(UW - 0.014, UH - 0.014, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: face, roughness: 0.45 }), M.grey]);
  panel.position.set(0, 0.004 + UH / 2, FZ - 0.002); unit.add(panel);
  function up(u, v, dz) { return new T.Vector3(u, 0.004 + UH / 2 + v, FZ + (dz || 0)); }
  function lcd(cx, cy, wd, hg) {
    var tex = S.liveTex(512, 190), last = '';
    var bez = S.mesh(new T.BoxGeometry(wd + 0.006, hg + 0.006, 0.003), M.grey); bez.position.copy(up(cx, cy, 0.001)); unit.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(wd, hg), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); scr.position.copy(up(cx, cy, 0.004)); unit.add(scr);
    return function (txt, u2) { if (txt + u2 === last) return; last = txt + u2;
      tex.draw(function (x) { var gr = x.createLinearGradient(0, 0, 0, 190); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
        x.fillStyle = gr; x.fillRect(0, 0, 512, 190); x.font = '700 84px "JetBrains Mono", monospace'; x.textAlign = 'right';
        x.fillStyle = '#1b2116'; x.fillText(txt, 400, 116); x.font = '600 34px "Public Sans", sans-serif'; x.fillText(u2, 496, 170); }); };
  }
  function plabel(text, u, v) { var l = S.label(text, { w: 0.09, ratio: 0.16, color: '#f1efe8' }); l.position.copy(up(u, v, 0.0025)); unit.add(l); }
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  var KNOBS = [];
  CTRL.forEach(function (c, i) {
    var u = -0.12 + i * 0.12;
    var kg = new T.Group(); kg.position.copy(up(u, -0.03)); unit.add(kg);
    var sk = S.mesh(new T.CylinderGeometry(0.02, 0.021, 0.004, 40), M.bakelite); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; kg.add(sk);
    var kb = S.mesh(new T.CylinderGeometry(0.015, 0.017, 0.018, 40), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.013; kg.add(kb);
    var ptr = S.mesh(new T.BoxGeometry(0.002, 0.016, 0.0012), M.white, false); ptr.position.set(0, 0.009, 0.0228); kg.add(ptr);
    plabel(c.label, u, -0.06);
    KNOBS.push({ c: c, g: kg, show: lcd(u, 0.022, 0.1, 0.034) });
  });
  var meterShow = lcd(0.15, 0.022, 0.11, 0.036); meterShow('0.0', '');
  KNOBS.forEach(function (k) { k.show(k.c.v.toFixed(k.c.d), k.c.unit); });
  plabel({ diode: 'ANODE µA', ion: 'ION nA', thomson: 'SPOT mm', mag: 'ANODE mA', focus: 'LINE mm', bar: 'DEFL. 2y mm' }[MODE], 0.15, -0.006);
  var sw = S.rounded(0.02, 0.028, 0.01, 0.003, M.bakelite); sw.position.copy(up(0.17, -0.045, 0.004)); unit.add(sw);
  var lampM = new T.MeshStandardMaterial({ color: 0x4a1a10, roughness: 0.3, emissive: 0x000000 });
  var lamp = S.mesh(new T.SphereGeometry(0.005, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), lampM); lamp.rotation.x = Math.PI / 2; lamp.position.copy(up(0.14, -0.045)); unit.add(lamp);
  function kAngle(c, v) { return 3 * Math.PI / 4 - 1.5 * Math.PI * (v - c.min) / (c.max - c.min); }
  KNOBS.forEach(function (k) { k.g.rotation.z = kAngle(k.c, st[k.c.k]); });
  S.contact(0.52, 0.34, 0.32, -0.06, 0.55);
  S.wire([[-0.28, 0.03, -0.06], [-0.04, 0.016, 0.02], [0.14, 0.016, 0.05]], 'red');
  S.wire([[-0.28, 0.03, -0.1], [-0.02, 0.012, 0.07], [0.18, 0.012, 0.07]], 'black');

  var TUBE_NAME = { diode: 'Directly heated vacuum diode', ion: 'Mercury-vapour tube with an ion collector', thomson: 'Cathode-ray tube between Helmholtz coils',
    mag: 'Cylindrical diode in a solenoid', focus: 'Cathode-ray tube in a long solenoid', bar: 'Cathode-ray tube, bar magnet and deflection magnetometer' }[MODE];
  S.addApparatus('tube', tubeG, TUBE_NAME, S.lab.variant && S.lab.variant.sample ? S.lab.variant.sample : TUBE_NAME + '.');
  S.addApparatus('unit', unit, 'Supply and meter unit', 'The knobs set the supplies; the displays read each setting and the measured current or deflection.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var hud1 = S.hudCard(CTRL[0].label), hud2 = S.hudCard('Reading');

  // ================================================================ human actions
  function power(on) {
    if (busy()) return Promise.resolve();
    if (st.on === on) return Promise.resolve();
    return S.hand.tap(sw, 'front').then(function () {
      st.on = on; st.warm = on;
      lampM.emissive.setHex(on ? 0xff3010 : 0); lampM.emissiveIntensity = on ? 2 : 0;
      filM.emissive = new T.Color(on ? 0xff9a3a : 0); filM.emissiveIntensity = on ? 2.2 : 0;
      S.say(on ? { diode: 'Supplies on: the filament glows and the pyrometer reads its temperature.', ion: 'Heater on: the tube warms and the mercury vapour reaches its working pressure.',
        thomson: 'High tension on at ' + p.Va + ' V: a green spot appears at the centre of the screen.', mag: 'Filament on: the anode current flows.',
        focus: 'High tension on and a small AC voltage on the X plates: a short green line appears on the screen.', bar: 'High tension on at ' + p.Va + ' V: the spot sits at the centre with the magnet far away.' }[MODE] : 'Supplies off.');
      S.click(820, 0.05); S.render();
    });
  }
  function ctrlOf(k) { for (var i = 0; i < KNOBS.length; i++) if (KNOBS[i].c.k === k) return KNOBS[i]; return null; }
  function setTo(k, v) {
    if (busy()) return Promise.resolve();
    var kn = ctrlOf(k), c = kn.c;
    if (!isFinite(v) || v < c.min - 1e-9 || v > c.max + 1e-9) { S.say(c.label + ' goes from ' + c.min + ' to ' + c.max + ' ' + c.unit + ' only.'); return Promise.resolve(); }
    v = rnd(Math.round(v / c.step) * c.step, c.d);
    var v0 = st[k]; if (Math.abs(v - v0) < 1e-12) return Promise.resolve();
    if (k === 'x' && magnet) {                              // the bar magnet is slid along the scale
      var a = wp(magnet);
      return S.hand.pinchMove(a, function (t) { return new T.Vector3(-0.35, 0.02, TZ - (v0 + (v - v0) * t) / 100); }, function (t) {
        st.x = rnd(v0 + (v - v0) * t, 2); magnet.position.z = TZ - st.x / 100; }, { mode: 'top', ms: 600 }).then(function () { st.x = v; magnet.position.z = TZ - v / 100; S.render(); });
    }
    var pt = wp(kn.g).add(new T.Vector3(0, 0, 0.02));
    return S.hand.pinchMove(pt, function () { return pt; }, function (t) {
      st[k] = v0 + (v - v0) * t; kn.g.rotation.z = kAngle(c, st[k]); }, { mode: 'front', ms: 450, reachMs: 500 })
      .then(function () { st[k] = v; kn.g.rotation.z = kAngle(c, v); S.render(); });
  }
  function swapPlace() {                                  // bar method: the tube and the magnetometer change places
    if (busy()) return Promise.resolve();
    var to = st.place === 'tube' ? 'meter' : 'tube';
    var A = to === 'meter' ? [-0.08, 0.12] : [-0.35, TZ], Bp = to === 'meter' ? [-0.35, TZ] : [-0.08, 0.12];
    return S.hand.pinchMove(wp(mmeter), function () { return wp(mmeter); }, function (t) {
      mmeter.position.set(A[0] + (Bp[0] - A[0]) * t, 0, A[1] + (Bp[1] - A[1]) * t); tubeG.visible = to === 'tube' ? t > 0.5 : t < 0.5; }, { mode: 'top', ms: 700 }).then(function () {
      st.place = to; tubeG.visible = to === 'tube'; mmeter.position.set(Bp[0], 0, Bp[1]);
      S.say(to === 'meter' ? 'The tube is lifted away and the magnetometer stands in its place, its arm east-west. Read the needle.' : 'The tube is back in its place.'); S.render(); });
  }
  function flipMagnet() {
    if (busy()) return Promise.resolve();
    return S.hand.pinchMove(wp(magnet), function () { return wp(magnet); }, function (t) { magnet.rotation.y = (st.flip > 0 ? 0 : Math.PI) + Math.PI * t; }, { mode: 'top', ms: 500 })
      .then(function () { st.flip = -st.flip; magnet.rotation.y = st.flip > 0 ? 0 : Math.PI; S.say('Magnet turned round: the spot moves to the other side.'); S.render(); });
  }
  function trace() {
    st.traced = true; S.focus('tube');
    S.say({ diode: 'A straight tungsten filament runs along the axis of a nickel cylinder, the anode. The pyrometer looks at the filament through the glass.',
      ion: 'The cathode is at the bottom, the grid across the middle and a small collector plate at the top; a drop of mercury lies in the bulb.',
      thomson: 'The electron gun on the left, the deflecting plates just after it, the coils around the plates, and the screen with its millimetre graticule on the right.',
      mag: 'The diode stands on the axis of the solenoid: its filament on the axis, the anode a cylinder around it.',
      focus: 'The tube lies on the axis of the long solenoid; only the screen sticks out at the right.',
      bar: 'The tube points north-south; the bar magnet slides along an east-west line behind its middle, end-on to the tube.' }[MODE]);
    S.render();
  }

  // ================================================================ recording
  function record(extra) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.on) { S.say('Switch the supplies on first.'); return false; }
    var r = read(), row = assign({ kind: 'pt' }, extra || {});
    CTRL.forEach(function (c) { row[c.k] = st[c.k]; });
    Object.keys(r).forEach(function (k) { row[k] = r[k]; });
    S.addRow(row); return true;
  }

  // ---------- each set-up's procedure
  function autoGrid(k, vals, extra) {
    var chain = Promise.resolve();
    vals.forEach(function (v) { chain = chain.then(function () { return setTo(k, v); }).then(function () { record(extra); }); });
    return chain;
  }
  function balanceIc() {        // Thomson: approach the centre from both sides, take the mean current
    var lo = -1, hi = -1, i, v, c = ctrlOf('Ic').c;
    for (i = 0; i <= 1000; i++) { st.Ic = i * c.step; v = read().y; if (v === 0) { if (lo < 0) lo = st.Ic; hi = st.Ic; } else if (lo >= 0) break; }
    return lo < 0 ? -1 : rnd((lo + hi) / 2, 3);
  }
  function focusIc() {          // raise the current slowly and stop where the line is shortest
    var best = -1, bl = 1e9, i, l, c = ctrlOf('Ic').c, raw;
    for (i = 0; i <= 1000; i++) { st.Ic = i * c.step; raw = view().ell_mm; if (raw < bl) { bl = raw; best = st.Ic; } else if (raw > bl * 1.5 && best > 0) break; }
    l = best; return rnd(l, 3);
  }

  // ================================================================ results
  function result(rows) {
    var pts, f;
    if (MODE === 'diode') {
      pts = rows.filter(function (r) { return r.kind === 'sat' && r.Ia > 0; }).map(function (r) { return [1 / r.T, Math.log(r.Ia * 1e-6 / (r.T * r.T))]; });
      if (pts.length < 4) return null; f = S.fit.linear(pts); if (!f) return null;
      return { label: 'Work function of the filament', value: -f.m * KB / QE, unit: 'eV', digits: 2, truth: p.phi,
        note: 'Slope of ln(Is/T^2) against 1/T = ' + f.m.toFixed(0) + ' K, from ' + pts.length + ' temperatures; phi = -slope x k / e.' };
    }
    if (MODE === 'ion') {
      var mx = Math.max.apply(null, rows.map(function (r) { return r.I; }).concat([0]));
      pts = rows.filter(function (r) { return r.I > 0.3 * mx; }).map(function (r) { return [r.V, r.I]; });
      if (pts.length < 4) return null; f = S.fit.linear(pts); if (!f || !f.m) return null;
      return { label: 'Ionisation potential of mercury', value: -f.c / f.m, unit: 'V', digits: 2, truth: p.Ui,
        note: 'The straight part (' + pts.length + ' points above 30 % of the largest current) extended to zero current.' };
    }
    if (MODE === 'thomson') {
      var b = rows.filter(function (r) { return r.kind === 'bal' && r.Ic > 0; });
      if (b.length < 3) return null;
      var em = S.fit.mean(b.map(function (r) { var E = r.Vp / p.d, B = p.kB * r.Ic; return E * E / (2 * p.Va * B * B); }));
      return { label: 'e/m of the electron', value: em / 1e11, unit: 'x 1e11 C/kg', digits: 3, truth: p.em / 1e11,
        note: 'Mean of ' + b.length + ' balances; e/m = E^2 / (2 Va B^2) with E = Vp/d and B = k I.' };
    }
    if (MODE === 'mag') {
      var runs = {}, ems = [];
      rows.forEach(function (r) { (runs[r.Va] = runs[r.Va] || []).push(r); });
      Object.keys(runs).forEach(function (va) {
        var rr = runs[va].slice().sort(function (a, c) { return a.Is - c.Is; }), i0 = null, i;
        rr.forEach(function (r) { if (r.Is === 0) i0 = r.Ia; });
        if (i0 === null || rr.length < 8) return;
        for (i = 1; i < rr.length; i++) {
          if (rr[i - 1].Ia >= i0 / 2 && rr[i].Ia < i0 / 2) {
            var is = rr[i - 1].Is + (rr[i - 1].Ia - i0 / 2) / (rr[i - 1].Ia - rr[i].Ia) * (rr[i].Is - rr[i - 1].Is), B = MU0 * p.n * is;
            ems.push(8 * Number(va) / (B * B * p.a * p.a * Math.pow(1 - p.b * p.b / (p.a * p.a), 2))); break;
          }
        }
      });
      if (!ems.length) return null;
      return { label: 'e/m of the electron', value: S.fit.mean(ems) / 1e11, unit: 'x 1e11 C/kg', digits: 3, truth: p.em / 1e11,
        note: 'Critical field at half the zero-field current, ' + ems.length + ' run(s); e/m = 8 Va / (Bc^2 a^2 (1 - b^2/a^2)^2).' };
    }
    if (MODE === 'focus') {
      var fr = rows.filter(function (r) { return r.kind === 'focus' && r.Ic > 0; });
      if (fr.length < 2) return null;
      var e2 = S.fit.mean(fr.map(function (r) { var B = MU0 * p.n * r.Ic; return 8 * PI * PI * r.Va / (B * B * p.L * p.L); }));
      return { label: 'e/m of the electron', value: e2 / 1e11, unit: 'x 1e11 C/kg', digits: 3, truth: p.em / 1e11,
        note: 'Mean of ' + fr.length + ' first focuses; e/m = 8 pi^2 Va / (B^2 L^2), B = mu0 n I.' };
    }
    var br = rows.filter(function (r) { return r.kind === 'bar' && r.y2 > 0 && r.th > 0; });
    if (br.length < 3) return null;
    var e3 = S.fit.mean(br.map(function (r) { var y = r.y2 / 2000, B = p.BH * Math.tan(r.th * PI / 180), ll = p.L * p.L + y * y; return 8 * p.Va * y * y / (B * B * ll * ll); }));
    return { label: 'e/m of the electron', value: e3 / 1e11, unit: 'x 1e11 C/kg', digits: 3, truth: p.em / 1e11,
      note: 'Mean of ' + br.length + ' magnet positions; B = BH tan(theta) with BH = ' + (p.BH * 1e6).toFixed(1) + ' µT; e/m = 8 Va y^2 / (B^2 (L^2 + y^2)^2). This is a low-precision method.' };
  }

  // ================================================================ steps
  var steps = [];
  function stepOn(title, why) {
    return { id: 'on', title: 'Look and switch on', view: 'tube', render: function (u) {
        u.h2(title); u.p(why);
        u.task('1. Trace the apparatus', st.traced, st.traced ? 'Seen' : 'Look at the tube').add(u.button(st.traced ? 'Traced' : 'Look at the tube', trace, !st.traced, st.traced));
        u.task('2. Switch on', st.on, st.on ? 'On' : 'The hand presses the power switch').add(u.button(st.on ? 'On' : 'Switch on', function () { S.focus('unit'); power(true); }, !st.on, st.on || S.hand.busy));
        u.next('Next', st.traced && st.on);
      }, ok: function () { return st.traced && st.on; }, auto: function () { trace(); return power(true); } };
  }
  function ctrlUI(u, k) {
    var c = ctrlOf(k).c, tg = { v: st[k] };
    u.slider('Set ' + c.label.toLowerCase() + ' to', c.min, c.max, c.step, function () { return tg.v; }, function (v) { tg.v = v; }, c.unit, c.d);
    return u.button('Turn the knob', function () { setTo(k, tg.v); }, false, S.hand.busy);
  }
  function liveLine() { var r = read(); return CTRL.map(function (c) { return c.label + ' ' + st[c.k].toFixed(c.d) + ' ' + c.unit; }).join('  ·  ') + '  ·  ' + Object.keys(r).map(function (k) { return k + ' ' + r[k]; }).join('  ·  '); }
  function count(kind) { return S.rows.filter(function (r) { return r.kind === kind; }).length; }

  if (MODE === 'diode') {
    steps.push(stepOn('Look at the diode, then switch the supplies on', 'The filament supply heats the tungsten; the anode supply pulls the electrons across. Keep both knobs low at first.'));
    steps.push({ id: 'char', title: 'Plate characteristic', view: 'unit', render: function (u) {
        u.h2('Find the saturation'); u.p('With the filament at 2.40 A, raise the anode voltage in steps and record the current. It rises (space charge) and then levels off: saturation.');
        u.row(ctrlUI(u, 'If'), ctrlUI(u, 'Va'));
        u.row(u.button('Record this point', function () { record({ kind: 'char' }); }, true, S.hand.busy));
        u.live(liveLine); u.h3('Observation table'); u.table();
        u.next('Next: saturation currents', count('char') >= 5);
      }, ok: function () { return count('char') >= 5; },
      auto: function () { return setTo('If', 2.4).then(function () { return autoGrid('Va', [5, 10, 20, 40, 80, 120, 150], { kind: 'char' }); }); } });
    steps.push({ id: 'sat', title: 'Saturation current at each temperature', view: 'unit', render: function (u) {
        u.h2('Is and T at six filament currents'); u.p('Keep the anode at 150 V. For each filament current read the pyrometer (T) and the anode current (Is) and record them.');
        u.row(ctrlUI(u, 'If'), ctrlUI(u, 'Va'));
        u.row(u.button('Record a saturation reading', function () { if (st.Va < 120) { S.say('Raise the anode voltage into saturation (at least 120 V) first.'); return; } record({ kind: 'sat' }); }, true, S.hand.busy));
        u.live(liveLine); u.table();
        u.next('Next: result', count('sat') >= 4);
      }, ok: function () { return count('sat') >= 4; },
      auto: function () { return setTo('Va', 150).then(function () { return autoGrid('If', [2.0, 2.1, 2.2, 2.3, 2.4, 2.5], { kind: 'sat' }); }); } });
  } else if (MODE === 'ion') {
    steps.push(stepOn('Look at the tube, then switch the heater on', 'The mercury must be warm enough to give a steady vapour before any reading.'));
    steps.push({ id: 'sweep', title: 'Ion current against voltage', view: 'unit', render: function (u) {
        u.h2('Raise the voltage and record the ion current'); u.p('Take readings from 6 V to 19 V in steps of 0.5 V. Nothing flows until the electrons can ionise the atoms; then the current climbs in a straight line.');
        u.row(ctrlUI(u, 'V'), u.button('Record this point', function () { record(); }, true, S.hand.busy));
        u.live(liveLine); u.table();
        u.next('Next: result', S.rows.length >= 10);
      }, ok: function () { return S.rows.length >= 10; },
      auto: function () { var v = [], x; for (x = 6; x <= 19.01; x += 0.5) v.push(rnd(x, 1)); return autoGrid('V', v); } });
  } else if (MODE === 'thomson') {
    steps.push(stepOn('Look at the tube, then switch the high tension on', 'The spot must sit at the centre of the graticule with no field on.'));
    steps.push({ id: 'bal', title: 'Deflect, then balance', view: 'tube', render: function (u) {
        u.h2('Balance the electric deflection with the coils'); u.p('Set a plate voltage and note the deflection. Then raise the coil current until the spot is back at zero; approach from both sides and record the mean current. Do this for three plate voltages.');
        u.row(ctrlUI(u, 'Vp'), ctrlUI(u, 'Ic'));
        u.row(u.button('Record the balance', function () { if (read().y !== 0) { S.say('The spot is not at the centre yet.'); return; } record({ kind: 'bal' }); }, true, S.hand.busy));
        u.live(liveLine); u.table();
        u.next('Next: result', count('bal') >= 3);
      }, ok: function () { return count('bal') >= 3; },
      auto: function () {
        var chain = Promise.resolve();
        [90, 120, 150].forEach(function (vp) {
          chain = chain.then(function () { return setTo('Ic', 0); }).then(function () { return setTo('Vp', vp); }).then(function () { record({ kind: 'defl' }); })
            .then(function () { var keep = st.Ic, ic = balanceIc(); st.Ic = keep; return setTo('Ic', ic); }).then(function () { record({ kind: 'bal' }); });
        });
        return chain;
      } });
  } else if (MODE === 'mag') {
    steps.push(stepOn('Look at the diode in the solenoid, then switch on', 'With no current in the solenoid every electron reaches the anode.'));
    steps.push({ id: 'cut', title: 'Anode current against field', view: 'unit', render: function (u) {
        u.h2('Raise the solenoid current and watch the cut-off'); u.p('At 6 V, record the anode current from 0 to 0.60 A of solenoid current in steps of 0.02 A. Repeat at 9 V.');
        u.row(ctrlUI(u, 'Va'), ctrlUI(u, 'Is'));
        u.row(u.button('Record this point', function () { record(); }, true, S.hand.busy));
        u.live(liveLine); u.table();
        u.next('Next: result', S.rows.length >= 16);
      }, ok: function () { return S.rows.length >= 16; },
      auto: function () {
        var chain = Promise.resolve(), g = [], x; for (x = 0; x <= 0.6001; x += 0.02) g.push(rnd(x, 2));
        [6, 9].forEach(function (va) { chain = chain.then(function () { return setTo('Is', 0); }).then(function () { return setTo('Va', va); }).then(function () { return autoGrid('Is', g); }); });
        return chain;
      } });
  } else if (MODE === 'focus') {
    steps.push(stepOn('Look at the tube in the solenoid, then switch on', 'A short line is drawn on the screen by the AC voltage on the X plates.'));
    steps.push({ id: 'focus', title: 'Find the first focus', view: 'tube', render: function (u) {
        u.h2('Shrink the line to a point'); u.p('Raise the solenoid current slowly: the line turns and shrinks. Record the current at which it is shortest. Do this at 600, 800 and 1000 V.');
        u.row(ctrlUI(u, 'Va'), ctrlUI(u, 'Ic'));
        u.row(u.button('Record the focus', function () { record({ kind: 'focus' }); }, true, S.hand.busy));
        u.live(liveLine); u.table();
        u.next('Next: result', count('focus') >= 2);
      }, ok: function () { return count('focus') >= 2; },
      auto: function () {
        var chain = Promise.resolve();
        [600, 800, 1000].forEach(function (va) {
          chain = chain.then(function () { return setTo('Ic', 0); }).then(function () { return setTo('Va', va); })
            .then(function () { var keep = st.Ic, ic = focusIc(); st.Ic = keep; return setTo('Ic', ic); }).then(function () { record({ kind: 'focus' }); });
        });
        return chain;
      } });
  } else {
    steps.push(stepOn('Look at the tube and the magnet, then switch on', 'The tube lies along the magnetic meridian, so the earth\'s horizontal field runs along it and does not deflect the spot.'));
    steps.push({ id: 'bar', title: 'Deflection and field', view: 'tube', render: function (u) {
        u.h2('Deflect the spot with the magnet, then measure its field'); u.p('Slide the magnet to a position, read the deflection 2y with the magnet one way and the other. Then put the magnetometer where the tube was and read theta. Record and repeat at four positions.');
        u.row(ctrlUI(u, 'x'), u.button('Turn the magnet round', flipMagnet, false, S.hand.busy));
        u.row(u.button(st.place === 'tube' ? 'Put the magnetometer in place' : 'Put the tube back', swapPlace, false, S.hand.busy),
          u.button('Record this position', function () { record({ kind: 'bar' }); }, true, S.hand.busy));
        u.live(liveLine); u.table();
        u.next('Next: result', count('bar') >= 3);
      }, ok: function () { return count('bar') >= 3; },
      auto: function () {
        var chain = Promise.resolve();
        [15, 16, 17, 18].forEach(function (x) {
          chain = chain.then(function () { return setTo('x', x); }).then(function () { return flipMagnet(); }).then(function () { return flipMagnet(); })
            .then(function () { return swapPlace(); }).then(function () { return swapPlace(); }).then(function () { record({ kind: 'bar' }); });
        });
        return chain;
      } });
  }

  // ================================================================ book, graph, theory
  var COLS = { diode: [['If (A)', 'If', 2], ['Va (V)', 'Va', 0], ['T (K)', 'T', 0], ['Ia (µA)', 'Ia', 2]],
    ion: [['V (V)', 'V', 1], ['I (nA)', 'I', 2]], thomson: [['Vp (V)', 'Vp', 0], ['Ic (A)', 'Ic', 3], ['y (mm)', 'y', 1]],
    mag: [['Va (V)', 'Va', 1], ['Is (A)', 'Is', 2], ['Ia (mA)', 'Ia', 3]], focus: [['Va (V)', 'Va', 0], ['Ic (A)', 'Ic', 3], ['line (mm)', 'ell', 1]],
    bar: [['x (cm)', 'x', 1], ['2y (mm)', 'y2', 1], ['theta (deg)', 'th', 1]] }[MODE];
  var columns = [{ label: 'S.No', get: function (r, i) { return i + 1; } }].concat(COLS.map(function (c) {
    return { label: c[0], get: function (r) { return typeof r[c[1]] === 'number' ? r[c[1]].toFixed(c[2]) : ''; } }; }));
  columns.push({ label: 'Note', get: function (r) { return r.kind === 'pt' ? '' : r.kind; } });
  var GRAPH = {
    diode: { x: function (r) { return r.kind === 'sat' ? 1e4 / r.T : NaN; }, y: function (r) { return r.kind === 'sat' ? Math.log(r.Ia * 1e-6 / (r.T * r.T)) : NaN; }, xlabel: '10^4 / T (1/K)', ylabel: 'ln(Is/T^2)' },
    ion: { x: function (r) { return r.V; }, y: function (r) { return r.I; }, xlabel: 'V (V)', ylabel: 'I (nA)', x0: 0, y0: 0 },
    thomson: { x: function (r) { return r.Vp; }, y: function (r) { return r.kind === 'bal' ? r.Ic : NaN; }, xlabel: 'Vp (V)', ylabel: 'Ic at balance (A)', x0: 0, y0: 0 },
    mag: { x: function (r) { return r.Is; }, y: function (r) { return r.Ia; }, xlabel: 'Is (A)', ylabel: 'Ia (mA)', x0: 0, y0: 0 },
    focus: { x: function (r) { return Math.sqrt(r.Va); }, y: function (r) { return r.kind === 'focus' ? r.Ic : NaN; }, xlabel: 'sqrt(Va)', ylabel: 'Ic at focus (A)', x0: 0, y0: 0 },
    bar: { x: function (r) { return r.x; }, y: function (r) { return r.y2; }, xlabel: 'x (cm)', ylabel: '2y (mm)' } }[MODE];
  var TH = {
    diode: ['Richardson-Dushman: Is = A S T^2 exp(-e phi / k T). The slope of ln(Is/T^2) against 1/T is -e phi / k.', 'ln(Is/T^2) = ln(A S) - e phi / (k T)'],
    ion: ['No ions form until the electrons carry the ionisation energy; above it the ion current grows linearly with the excess energy.', 'I = G (V - Vi)  for V above Vi'],
    thomson: ['At the balance e E = e v B, and e Va = m v^2 / 2.', 'e/m = E^2 / (2 Va B^2)'],
    mag: ['At the critical field the electron paths just graze the anode.', 'e/m = 8 Va / (Bc^2 a^2 (1 - b^2/a^2)^2)'],
    focus: ['One turn of the helix takes 2 pi m/(e B); at the first focus that equals L/v.', 'e/m = 8 pi^2 Va / (B^2 L^2)'],
    bar: ['The beam follows a circle of radius r = m v/(e B); y = L^2/(2r) for a small deflection.', 'e/m = 8 Va y^2 / (B^2 (L^2 + y^2)^2),  B = BH tan(theta)'] }[MODE];

  return {
    camera: { pos: [0.0, 1.0, 1.4], look: [-0.06, 0.08, -0.1] },
    views: { tube: [[-0.3, 0.42, 0.5], [-0.33, 0.1, -0.1]], unit: [[0.36, 0.36, 0.36], [0.32, 0.08, -0.06]],
      bench: [[-0.02, 0.85, 1.15], [-0.06, 0.1, -0.08]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: TH[0], formula: TH[1], formulaNote: 'Constants: CODATA 2018. Instrument values are those printed on the apparatus.',
      more: ['Read each meter to its least count and never guess between marks you cannot see.', 'Every number on this bench comes from the physical model of the tube, run with the lab\'s own values.'],
      precautions: 'Make connections with the supplies off. Raise voltages slowly; never exceed the ratings printed on the tube.' },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 120), 'Apparatus: ' + TUBE_NAME + '.'], columns: columns },
    graph: GRAPH,
    result: result,
    tol: MODE === 'bar' ? 0.03 : 0.02,
    chips: ['What am I measuring?', 'Check my readings', 'Why is this the right formula?'],
    viva: [['The charge-to-mass ratio of the electron is about', ['1.76e11 C/kg', '9.1e-31 kg', '1.6e-19 C'], 0, 'e / m = 1.602e-19 / 9.109e-31.']],
    askState: function () { var o = { experiment: S.lab.title, switched_on: st.on, readings_taken: S.rows.length }; CTRL.forEach(function (c) { o[c.k + '_' + c.unit] = st[c.k]; }); var r = read(); Object.keys(r).forEach(function (k) { o['reading_' + k] = r[k]; }); return o; },
    steps: steps,
    tick: function () {
      var r = read(), v = view();
      KNOBS.forEach(function (k) { k.show(st[k.c.k].toFixed(k.c.d), k.c.unit); });
      var key = Object.keys(r)[MODE === 'bar' ? 0 : (MODE === 'diode' ? 1 : 0)], val = r[key];
      meterShow(typeof val === 'number' ? val.toFixed(MODE === 'mag' ? 3 : (MODE === 'diode' || MODE === 'ion') ? 2 : 1) : '-', MODE === 'diode' ? 'µA' : MODE === 'ion' ? 'nA' : MODE === 'mag' ? 'mA' : 'mm');
      glowM.opacity = st.on ? 0.25 : 0;
      if (spot) {
        spotM.opacity = st.on && tubeG.visible ? 0.95 : 0;
        var yy = 0;
        if (MODE === 'thomson') yy = Math.max(-0.04, Math.min(0.04, v.y));
        if (MODE === 'bar') yy = st.on ? st.flip * Math.max(-0.04, Math.min(0.04, v.y_mm / 1000)) : 0;
        spot.position.z = TZ + yy;
        if (MODE === 'focus') { var L = st.on ? Math.max(0.002, v.ell_mm / 1000) : 0.001; line.visible = st.on; line.scale.y = L; spot.visible = false;
          line.rotation.x = (st.on ? p.em * v.B * p.L / Math.sqrt(2 * p.em * st.Va) : 0) / 2; }
      }
      if (mmNeedle) mmNeedle.rotation.y = st.place === 'meter' ? -st.flip * view().thm * PI / 180 : 0;
      hud1.set(st[CTRL[0].k].toFixed(CTRL[0].d) + ' ' + CTRL[0].unit);
      hud2.set(typeof val === 'number' ? String(val) : '-');
    }
  };
});
