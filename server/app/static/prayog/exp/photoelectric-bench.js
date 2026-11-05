/* Prayogshala studio module: PHOTOELECTRIC BENCH (B.Sc. modern physics).
   A high-pressure mercury lamp in a ventilated housing, a five-window interference filter wheel, an evacuated
   photocell in a light-tight hood, and a photoelectric control unit with a fine retarding-voltage knob, a digital
   voltmeter and a digital nano-ammeter. The hand turns the filter wheel and the voltage knob.
   Physics: the `photocell` kernel of packs/modern_ug.js on the lab's own params - the same code the server checks
   against Einstein's photoelectric equation. The filters' wavelengths are lam1..lam5 of the lab. */
HoolaStudio.define('photoelectric-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.photocell, assign = HK.assign;
  var p = HK.paramsFor('photocell', S.lab.params);
  var HPL = 6.62607015e-34, CL = 2.99792458e8, QEL = 1.602176634e-19;
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || 'Caesium-coated cathode';
  var LAMS = [p.lam1, p.lam2, p.lam3, p.lam4, p.lam5].filter(function (x) { return isFinite(x) && x > 1e-8; });
  var VLC = 0.01;                                   // the voltmeter's least count
  var st = { lamp: false, hooded: false, f: 0, V: 0, P: p.P, done: {} };

  function nm(lam) { return Math.round(lam * 1e9 * 10) / 10; }
  function freq(lam) { return CL / lam; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function at(lam, V, P) { var q = assign(p, { lam: lam, Vr: V, P: P === undefined ? st.P : P });
    return KN.view(KN.init(q, q), q, q); }
  function stopV(lam) { var q = assign(p, { lam: lam }); return KN.measure(q, q).Vs; }
  function readI() { var v = at(LAMS[st.f], st.V).I * 1e9; return rnd(st.lamp ? v : p.dark * 1e9, 2); }
  function readV() { return rnd(st.V, 2); }
  var BEAM_Y = 0.17;

  // ================================================================ mercury lamp in its housing
  var lampG = new T.Group(); S.scene.add(lampG); lampG.position.set(-0.52, 0, -0.1);
  var caseM = new T.MeshStandardMaterial({ color: 0x9aa2ab, roughness: 0.42, metalness: 0.5 });
  var hous = S.rounded(0.15, 0.15, 0.17, 0.012, caseM); hous.rotation.x = -Math.PI / 2; hous.position.y = BEAM_Y;
  lampG.add(hous);
  var legs = S.rounded(0.05, 0.05, BEAM_Y - 0.075, 0.006, M.iron); legs.rotation.x = -Math.PI / 2;
  legs.position.y = (BEAM_Y - 0.075) / 2; lampG.add(legs);
  var foot = S.rounded(0.13, 0.13, 0.014, 0.006, M.iron); foot.rotation.x = -Math.PI / 2; foot.position.y = 0.007;
  lampG.add(foot);
  for (var vi = 0; vi < 7; vi++) {                                     // ventilation slots on top
    var sl = S.mesh(new T.BoxGeometry(0.004, 0.0012, 0.08), M.black, false);
    sl.position.set(-0.03 + vi * 0.01, BEAM_Y + 0.0755, 0); lampG.add(sl);
  }
  var lampM = new T.MeshStandardMaterial({ color: 0xf2f0e4, roughness: 0.15, transparent: true, opacity: 0.6,
    emissive: 0x000000 });
  var arc = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.05, 20), lampM); arc.rotation.z = Math.PI / 2;
  arc.position.y = BEAM_Y; lampG.add(arc);
  var arcLight = new T.PointLight(0xdfe6ff, 0, 1.0); arcLight.position.set(0, BEAM_Y, 0); lampG.add(arcLight);
  var port = S.mesh(new T.CylinderGeometry(0.021, 0.021, 0.006, 28), new T.MeshStandardMaterial({ color: 0x1a1c20, roughness: 0.8 }));
  port.rotation.z = Math.PI / 2; port.position.set(0.076, BEAM_Y, 0); lampG.add(port);
  var panel = S.canvasTex(600, 220, function (x, w, h) {
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 3; x.strokeRect(8, 8, w - 16, h - 16);
    x.fillStyle = '#f1efe8'; x.font = '700 34px "Public Sans", sans-serif'; x.fillText('MERCURY LAMP', 26, 56);
    x.font = '500 24px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6';
    x.fillText('HIGH PRESSURE  ·  125 W  ·  UV HAZARD', 26, 94);
    x.font = '700 24px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8'; x.fillText('MAINS', 26, 170);
  });
  var pf = S.mesh(new T.BoxGeometry(0.13, 0.05, 0.003),
    [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: panel, roughness: 0.45 }), M.grey]);
  pf.position.set(0, BEAM_Y - 0.045, 0.0865); lampG.add(pf);
  var rocker = S.rounded(0.018, 0.026, 0.009, 0.003, M.bakelite); rocker.position.set(0.045, BEAM_Y - 0.045, 0.092);
  lampG.add(rocker);
  var rmk = S.mesh(new T.BoxGeometry(0.002, 0.009, 0.001), M.white, false); rmk.position.set(0, 0.007, 0.005);
  rocker.add(rmk);
  var pilotM = new T.MeshStandardMaterial({ color: 0x4a1410, roughness: 0.3, emissive: 0x000000 });
  var pilot = S.mesh(new T.SphereGeometry(0.005, 18, 12, 0, Math.PI * 2, 0, Math.PI / 2), pilotM);
  pilot.rotation.x = Math.PI / 2; pilot.position.set(-0.045, BEAM_Y - 0.02, 0.088); lampG.add(pilot);
  S.contact(0.2, 0.2, -0.52, -0.1, 0.55);

  // ================================================================ filter wheel
  var wheelG = new T.Group(); S.scene.add(wheelG); wheelG.position.set(-0.3, BEAM_Y, -0.1);
  var post = S.mesh(new T.CylinderGeometry(0.006, 0.006, BEAM_Y, 20), M.chrome);
  post.position.set(0, -BEAM_Y / 2 - 0.0, 0); wheelG.add(post);
  var wbase = S.rounded(0.1, 0.08, 0.012, 0.005, M.iron); wbase.rotation.x = -Math.PI / 2;
  wbase.position.y = -BEAM_Y + 0.006; wheelG.add(wbase);
  var FCOL = [0x8d6ad6, 0x6a5ae0, 0x3d6ae0, 0x3fb55a, 0xe8d23a];       // 365 405 436 546 578 nm, as the eye sees them
  var wheel = new T.Group(); wheelG.add(wheel);
  var discTex = S.canvasTex(700, 700, function (x, w, h) {
    x.fillStyle = '#23262b'; x.beginPath(); x.arc(w / 2, h / 2, w / 2 - 4, 0, Math.PI * 2); x.fill();
    x.strokeStyle = '#8c949e'; x.lineWidth = 4; x.beginPath(); x.arc(w / 2, h / 2, w / 2 - 6, 0, Math.PI * 2); x.stroke();
    x.textAlign = 'center';
    for (var i = 0; i < LAMS.length; i++) {
      var a = -Math.PI / 2 + i * 2 * Math.PI / LAMS.length, R = w * 0.33;
      var cx = w / 2 + Math.cos(a) * R, cy = h / 2 + Math.sin(a) * R;
      x.fillStyle = '#0f1013'; x.beginPath(); x.arc(cx, cy, w * 0.085, 0, Math.PI * 2); x.fill();
      x.fillStyle = '#f1efe8'; x.font = '700 30px "Public Sans", sans-serif';
      x.fillText(String(nm(LAMS[i])), cx, cy + w * 0.135);
      x.font = '500 22px "Public Sans", sans-serif'; x.fillStyle = '#aeb6c0';
      x.fillText('nm', cx, cy + w * 0.165);
    }
    x.fillStyle = '#f1efe8'; x.font = '700 26px "Public Sans", sans-serif'; x.fillText('FILTERS', w / 2, h / 2 + 10);
  });
  var disc = new T.Mesh(new T.CylinderGeometry(0.075, 0.075, 0.008, 48),
    [new T.MeshStandardMaterial({ color: 0x23262b, roughness: 0.5 }),
      new T.MeshStandardMaterial({ map: discTex, roughness: 0.5 }),
      new T.MeshStandardMaterial({ map: discTex, roughness: 0.5 })]);
  disc.rotation.x = Math.PI / 2; wheel.add(disc);
  var glasses = [];
  for (var fi = 0; fi < LAMS.length; fi++) {
    var ang = -Math.PI / 2 + fi * 2 * Math.PI / LAMS.length;
    var gm = new T.MeshStandardMaterial({ color: FCOL[fi % FCOL.length], roughness: 0.1, transparent: true,
      opacity: 0.72, emissive: 0x000000 });
    var gl = S.mesh(new T.CylinderGeometry(0.0115, 0.0115, 0.01, 28), gm);
    gl.rotation.x = Math.PI / 2; gl.position.set(Math.cos(ang) * 0.0455, -Math.sin(ang) * 0.0455, 0);
    wheel.add(gl); glasses.push(gm);
  }
  var hubK = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.016, 24), M.bakelite); hubK.rotation.x = Math.PI / 2;
  hubK.position.z = 0.012; wheel.add(hubK);
  var index = S.mesh(new T.ConeGeometry(0.005, 0.012, 14), M.red); index.rotation.x = Math.PI;
  index.position.set(0, 0.085, 0.006); wheelG.add(index);
  function wheelAngle(i) { return i * 2 * Math.PI / LAMS.length; }
  wheel.rotation.z = wheelAngle(0);
  S.contact(0.14, 0.12, -0.3, -0.1, 0.45);

  // ================================================================ photocell in a light-tight hood
  var cellG = new T.Group(); S.scene.add(cellG); cellG.position.set(-0.04, BEAM_Y, -0.1);
  var cpost = S.mesh(new T.CylinderGeometry(0.006, 0.006, BEAM_Y, 20), M.chrome); cpost.position.y = -BEAM_Y / 2;
  cellG.add(cpost);
  var cbase = S.rounded(0.11, 0.09, 0.012, 0.005, M.iron); cbase.rotation.x = -Math.PI / 2;
  cbase.position.y = -BEAM_Y + 0.006; cellG.add(cbase);
  var hoodM = new T.MeshStandardMaterial({ color: 0x14161a, roughness: 0.95, side: T.DoubleSide });
  var hood = S.mesh(new T.CylinderGeometry(0.038, 0.038, 0.12, 32, 1, true), hoodM);
  hood.rotation.z = Math.PI / 2; cellG.add(hood);
  var hoodBack = S.mesh(new T.CylinderGeometry(0.038, 0.038, 0.004, 32), hoodM); hoodBack.rotation.z = Math.PI / 2;
  hoodBack.position.x = 0.062; cellG.add(hoodBack);
  var apron = S.mesh(new T.CylinderGeometry(0.038, 0.038, 0.004, 32, 1, false, 0, Math.PI * 2), hoodM);
  apron.rotation.z = Math.PI / 2; apron.position.x = -0.062; cellG.add(apron);
  var aper = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 24), new T.MeshStandardMaterial({ color: 0x050506 }));
  aper.rotation.z = Math.PI / 2; aper.position.x = -0.064; cellG.add(aper);
  var bulbM = new T.MeshPhysicalMaterial({ color: 0xdfe5ea, roughness: 0.06, transmission: 0.6, thickness: 0.01,
    transparent: true, opacity: 0.55 });
  var bulb = S.mesh(new T.SphereGeometry(0.026, 28, 20), bulbM); cellG.add(bulb);
  var cath = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.03, 24, 1, true, 0.6, 3.9),
    new T.MeshStandardMaterial({ color: 0xb9a56a, roughness: 0.35, metalness: 0.8, side: T.DoubleSide }));
  cath.rotation.z = Math.PI / 2; cath.position.x = 0.004; cellG.add(cath);
  var ring = S.mesh(new T.TorusGeometry(0.009, 0.0012, 10, 28), M.brass); ring.rotation.y = Math.PI / 2;
  ring.position.x = -0.014; cellG.add(ring);
  var cellLbl = S.label('PHOTOCELL', { w: 0.05, ratio: 0.22, color: '#e8e8ea' });
  cellLbl.position.set(0.0, -0.03, 0.0385); cellG.add(cellLbl);
  var t1 = S.terminal([-0.04, 0.0015, -0.1 + 0.05], 'red'), t2 = S.terminal([-0.005, 0.0015, -0.1 + 0.05], 'black');
  S.contact(0.16, 0.12, -0.04, -0.1, 0.45);

  // ================================================================ the beam (only while the lamp is lit)
  function beam(x0, x1, col, r) {
    var m = new T.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.0, depthWrite: false,
      blending: T.AdditiveBlending });
    var g = S.mesh(new T.CylinderGeometry(r, r, x1 - x0, 20, 1, true), m, false, false);
    g.rotation.z = Math.PI / 2; g.position.set((x0 + x1) / 2, BEAM_Y, -0.1); S.scene.add(g);
    return { mesh: g, mat: m };
  }
  var beamA = beam(-0.444, -0.308, 0xeef0ff, 0.008), beamB = beam(-0.292, -0.106, 0xffffff, 0.0065);

  // ================================================================ photoelectric control unit
  var unit = new T.Group(); S.scene.add(unit); unit.position.set(0.36, 0, -0.1); unit.rotation.y = -0.34;
  var UW = 0.34, UD = 0.22, UH = 0.12;
  var ucase = S.rounded(UW, UD, UH, 0.012, new T.MeshStandardMaterial({ color: 0xd9d5cb, roughness: 0.5, metalness: 0.12 }));
  ucase.rotation.x = -Math.PI / 2; ucase.position.y = UH / 2 + 0.004; unit.add(ucase);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.004, 16), M.rubber);
    ft.position.set(f[0] * (UW / 2 - 0.02), 0.002, f[1] * (UD / 2 - 0.02)); unit.add(ft);
  });
  var FZ = UD / 2 + 0.0062, PW = UW - 0.014, PH = UH - 0.014, KX = 0.075, KY = -0.012;
  var uTex = S.canvasTex(1200, Math.round(1200 * PH / PW), function (x, w, h) {
    var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; }, k = w / PW;
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.font = '700 36px "Public Sans", sans-serif';
    x.fillText('PHOTOELECTRIC EFFECT APPARATUS', 34, 60);
    x.font = '500 24px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6';
    x.fillText('RETARDING VOLTAGE 0 – 3 V  ·  CURRENT 0 – 20 nA', 34, 96);
    var cx = X(KX), cy = Y(KY), R = 0.023 * k;
    x.strokeStyle = '#f1efe8'; x.fillStyle = '#f1efe8';
    for (var i = 0; i <= 30; i++) {
      var th = (225 - 270 * i / 30) * Math.PI / 180, big = i % 5 === 0, r0 = big ? R + 20 : R + 11;
      x.lineWidth = big ? 4 : 2; x.beginPath();
      x.moveTo(cx + Math.cos(th) * R, cy - Math.sin(th) * R); x.lineTo(cx + Math.cos(th) * r0, cy - Math.sin(th) * r0);
      x.stroke();
      if (big) { x.font = '600 22px "Public Sans", sans-serif'; x.textAlign = 'center';
        x.fillText(String(+(i / 10).toFixed(1)), cx + Math.cos(th) * (R + 42), cy - Math.sin(th) * (R + 42) + 8); }
    }
    x.textAlign = 'center'; x.font = '700 24px "Public Sans", sans-serif';
    x.fillText('RETARDING  VOLTAGE  (V)', cx, Y(-0.044));
    x.fillText('VOLTS', X(-0.1), Y(-0.044)); x.fillText('CURRENT  (nA)', X(-0.1), Y(0.04));
    x.textAlign = 'left';
  });
  var ufac = S.mesh(new T.BoxGeometry(PW, PH, 0.004),
    [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: uTex, roughness: 0.45 }), M.grey]);
  ufac.position.set(0, 0.004 + UH / 2, FZ - 0.002); unit.add(ufac);
  function up(u, v, dz) { return new T.Vector3(u, 0.004 + UH / 2 + v, FZ + (dz || 0)); }
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  var knob = new T.Group(); knob.position.copy(up(KX, KY)); unit.add(knob);
  var skirt = S.mesh(new T.CylinderGeometry(0.018, 0.019, 0.004, 36), M.bakelite); skirt.rotation.x = Math.PI / 2;
  skirt.position.z = 0.002; knob.add(skirt);
  var kb = S.mesh(new T.CylinderGeometry(0.0135, 0.015, 0.016, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 }));
  kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; knob.add(kb);
  var kptr = S.mesh(new T.BoxGeometry(0.002, 0.015, 0.0012), M.white, false); kptr.position.set(0, 0.008, 0.021);
  knob.add(kptr);
  function knobAngle(v) { return 3 * Math.PI / 4 - 1.5 * Math.PI * (v / 3); }
  knob.rotation.z = knobAngle(0);
  function lcd(cx, cy, wdt, hgt) {
    var tex = S.liveTex(512, 190), last = '';
    var bez = S.mesh(new T.BoxGeometry(wdt + 0.006, hgt + 0.006, 0.003), M.grey);
    bez.position.copy(up(cx, cy, 0.001)); unit.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(wdt, hgt), new T.MeshBasicMaterial({ map: tex, toneMapped: false }));
    scr.position.copy(up(cx, cy, 0.004)); unit.add(scr);
    return function (txt, unitTxt) {
      if (txt + unitTxt === last) return; last = txt + unitTxt;
      tex.draw(function (x) {
        var gr = x.createLinearGradient(0, 0, 0, 190); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
        x.fillStyle = gr; x.fillRect(0, 0, 512, 190);
        x.font = '700 96px "JetBrains Mono", monospace'; x.textAlign = 'right';
        x.fillStyle = 'rgba(0,0,0,.07)'; x.fillText('8.8.8.8', 420, 118);
        x.fillStyle = '#1b2116'; x.fillText(txt, 420, 118);
        x.textAlign = 'right'; x.font = '600 32px "Public Sans", sans-serif'; x.fillText(unitTxt, 494, 170);
      });
    };
  }
  var showV = lcd(-0.1, -0.012, 0.085, 0.032), showI = lcd(-0.1, 0.03, 0.085, 0.032);
  var tpos = S.terminal([0.36 - 0.08, 0.0015, -0.1 + 0.12], 'red');
  var tneg = S.terminal([0.36 - 0.045, 0.0015, -0.1 + 0.12], 'black');
  S.contact(0.42, 0.3, 0.36, -0.1, 0.55);

  // ================================================================ wiring, book
  S.wire([[-0.04, 0.012, -0.05], [0.1, 0.02, 0.0], [0.2, 0.02, 0.02], [0.28, 0.012, 0.02]], 'red');
  S.wire([[-0.005, 0.012, -0.05], [0.14, 0.014, 0.04], [0.24, 0.014, 0.05], [0.315, 0.012, 0.02]], 'black');
  S.wire([[-0.52, 0.01, 0.0], [-0.52, 0.006, 0.18], [-0.1, 0.006, 0.2]], 'black');

  S.addApparatus('lamp', lampG, 'Mercury lamp (125 W)', 'A high-pressure mercury lamp: its light is a few sharp lines. The rocker on the front switches it on; never look into the port.');
  S.addApparatus('wheel', wheelG, 'Interference filter wheel', 'Five filters: ' + LAMS.map(function (l) { return nm(l); }).join(', ') + ' nm. The index mark on top shows which one is in the beam.');
  S.addApparatus('cell', cellG, 'Photocell in its light-tight hood', SAMPLE + ' on the cathode, a ring anode in front of it, in an evacuated bulb. Only light through the aperture reaches it.');
  S.addApparatus('unit', unit, 'Photoelectric control unit', 'The knob sets the retarding voltage on the anode; the two displays read that voltage and the photocurrent in nanoamperes.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudF = S.hudCard('Filter'), hudV = S.hudCard('Retarding voltage'), hudI = S.hudCard('Photocurrent');

  // ================================================================ human actions
  function setLamp(on) {
    if (busy()) return Promise.resolve();
    if (on === st.lamp) return Promise.resolve();
    return S.hand.tap(rocker, 'front').then(function () {
      st.lamp = on;
      lampM.emissive = new T.Color(on ? 0xcfd9ff : 0x000000); lampM.emissiveIntensity = on ? 2.6 : 0;
      arcLight.intensity = on ? 0.7 : 0;
      pilotM.color.setHex(on ? 0x2fd05a : 0x4a1410); pilotM.emissive.setHex(on ? 0x2fd05a : 0x000000);
      pilotM.emissiveIntensity = on ? 2 : 0;
      S.click(820, 0.05);
      S.say(on ? 'Lamp on. It takes a minute to settle, and the filter in the beam glows in its own colour.'
        : 'Lamp off.');
      S.render();
    });
  }
  function turnWheel(i) {
    if (busy()) return Promise.resolve(false);
    if (!(i >= 0 && i < LAMS.length)) { S.say('There are only ' + LAMS.length + ' filters on the wheel.'); return Promise.resolve(false); }
    if (i === st.f) return Promise.resolve(true);
    var a0 = wheelAngle(st.f), a1 = wheelAngle(i), pt = wpt(wheelG, 0, 0, 0.02);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      wheel.rotation.z = a0 + (a1 - a0) * k;
    }, { mode: 'front', ms: 600, reachMs: 600 }).then(function () {
      st.f = i; wheel.rotation.z = a1; st.V = 0; knob.rotation.z = knobAngle(0);
      S.say('The ' + nm(LAMS[i]) + ' nm filter is in the beam. The retarding voltage is back at zero.');
      S.render(); return true;
    });
  }
  function turnTo(v) {
    if (busy()) return Promise.resolve();
    if (!isFinite(v) || v < 0 || v > 3 + 1e-9) { S.say('The retarding voltage knob goes from 0 to 3 V only.'); return Promise.resolve(); }
    v = rnd(Math.max(0, Math.min(3, v)), 2);
    var v0 = st.V, a0 = knobAngle(v0), pt = wpt(unit, KX, 0.004 + UH / 2 + KY, FZ + 0.022);
    if (Math.abs(v - v0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      st.V = v0 + (v - v0) * k; knob.rotation.z = knobAngle(st.V);
      S.hand.group.rotation.y = -(knobAngle(st.V) - a0) * 0.3;
    }, { mode: 'front', ms: 400 + 300 * Math.abs(v - v0), reachMs: 600 })
      .then(function () { st.V = v; knob.rotation.z = knobAngle(v); S.render(); });
  }
  /* The real procedure: creep the knob up in least-count steps until the current display reads zero. */
  function findCutOff() {
    if (busy()) return Promise.resolve(false);
    if (!st.lamp) { S.say('Switch the mercury lamp on first.'); return Promise.resolve(false); }
    var vs = stopV(LAMS[st.f]);
    if (vs <= VLC) {
      return turnTo(0).then(function () {
        S.say('No photocurrent at all with the ' + nm(LAMS[st.f]) + ' nm filter: this light is below the threshold frequency of the cathode. Turn the wheel to a shorter wavelength.');
        S.render(); return false;
      });
    }
    var target = Math.ceil((vs - 1e-9) / VLC) * VLC;                  // the first knob setting that reads 0.00 nA
    return turnTo(Math.max(0, target - 5 * VLC)).then(function () { return turnTo(rnd(target, 2)); })
      .then(function () {
        S.say('The current has just fallen to zero at ' + readV().toFixed(2) + ' V: that is the stopping potential for ' + nm(LAMS[st.f]) + ' nm.');
        S.render(); return true;
      });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.lamp) { S.say('Switch the mercury lamp on first.'); return false; }
    var lam = LAMS[st.f], vs = stopV(lam);
    if (vs <= VLC) { S.say('This filter gives no photocurrent, so it has no stopping potential to record.'); return false; }
    if (readI() > 0.0) { S.say('The current is still ' + readI().toFixed(2) + ' nA. Raise the retarding voltage until it reads zero.'); return false; }
    if (st.V > vs + 4 * VLC) { S.say('The voltage is well past the cut-off. Come back down until the current just reaches zero.'); return false; }
    if (st.done[nm(lam)]) { S.say('You already have the ' + nm(lam) + ' nm line. Turn the wheel to another filter.'); return false; }
    st.done[nm(lam)] = true;
    S.addRow({ nm: nm(lam), f: freq(lam), Vs: readV() });
    S.say('Written in your record book: ' + nm(lam) + ' nm, stopping potential ' + readV().toFixed(2) + ' V.');
    return true;
  }
  function intensityCheck() {
    if (busy()) return Promise.resolve();
    if (!st.lamp) { S.say('Switch the mercury lamp on first.'); return Promise.resolve(); }
    var lam = LAMS[st.f], full = at(lam, 0, 1.0).I * 1e9, half = at(lam, 0, 0.5).I * 1e9;
    var vsFull = stopV(lam);
    st.hooded = true;
    return turnTo(0).then(function () {
      S.say('Lamp pulled back to half the light: the current at zero volts falls from ' + full.toFixed(2) + ' to ' + half.toFixed(2) + ' nA, yet the cut-off stays at ' + vsFull.toFixed(2) + ' V. Brightness changes how MANY electrons come out, never how fast.');
      S.render();
    });
  }

  function result(rows) {
    var pts = rows.map(function (r) { return [r.f, r.Vs]; })
      .filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); });
    if (pts.length < 3) return null;
    var f = S.fit.linear(pts);
    if (!f) return null;
    return { label: 'Planck\'s constant h', value: QEL * f.m * 1e34, unit: '× 10⁻³⁴ J·s', digits: 3, truth: HPL * 1e34,
      note: 'Slope of the stopping potential against frequency is h/e = ' + f.m.toExponential(3) + ' V·s; the intercept gives a work function of ' + (-f.c).toFixed(2) + ' eV (true value ' + p.phi.toFixed(2) + ' eV).' };
  }

  return {
    camera: { pos: [0.0, 1.0, 1.3], look: [-0.04, 0.13, -0.08] },
    views: { lamp: [[-0.42, 0.34, 0.18], [-0.52, 0.17, -0.1]], wheel: [[-0.28, 0.3, 0.1], [-0.3, 0.17, -0.1]],
      cell: [[-0.02, 0.28, 0.08], [-0.04, 0.16, -0.1]], unit: [[0.4, 0.3, 0.18], [0.36, 0.08, -0.1]],
      bench: [[0.0, 1.0, 1.3], [-0.04, 0.13, -0.08]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'Light gives its energy to the electrons of a metal in whole photons of hf. An electron needs the work function of the metal to get out, so the fastest one leaves with hf minus that, and a retarding voltage on the anode turns back every electron slower than it. The current therefore stops at a definite voltage: the stopping potential.',
      formula: 'e V_s = h f − e φ',
      formulaNote: 'so a plot of V_s against f is a straight line of slope h/e, whatever the metal',
      more: ['The five interference filters pick out single mercury lines: ' + LAMS.map(function (l) { return nm(l); }).join(', ') + ' nm. Each one gives its own stopping potential.',
        'Making the light brighter raises the photocurrent but never the stopping potential - the strongest evidence there is that light arrives in photons.',
        'A line whose photon energy is below the work function gives no current at all, however bright it is. That is the threshold frequency.'],
      precautions: 'Let the lamp settle before reading. Keep the photocell hooded so that only the filtered beam reaches it. Creep up to the cut-off from below in steps of 0.01 V; a reading taken well past the cut-off is too high.' },
    book: { title: 'Expt. — Photoelectric effect (Planck\'s constant)',
      lines: ['Aim: stopping potential at four wavelengths; h and φ.', 'Cathode: ' + SAMPLE,
        'Mercury lamp with interference filters.', 'Retarding voltage 0–3 V, least count 0.01 V.',
        'e V_s = h f − e φ;  slope of V_s vs f = h/e.',
        'Precaution: find the cut-off from below, in 0.01 V steps.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'λ (nm)', get: function (r) { return r.nm.toFixed(1); } },
        { label: 'f (10¹⁴ Hz)', get: function (r) { return (r.f / 1e14).toFixed(3); } },
        { label: 'V_s (V)', get: function (r) { return r.Vs.toFixed(2); } }] },
    graph: { x: function (r) { return r.f / 1e14; }, y: function (r) { return r.Vs; },
      xlabel: 'f (10¹⁴ Hz)', ylabel: 'V_s (V)',
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.03,
    resultNote: 'The straight line is the whole point: its slope is h/e and does not depend on the metal, while where it crosses the voltage axis gives the work function of this cathode. The intercept on the frequency axis is the threshold frequency, below which no light of any brightness frees an electron.',
    chips: ['Why does brightness not change the stopping potential?', 'What is the threshold frequency?',
      'Why creep up to the cut-off from below?', 'Check my readings', 'Why use filters at all?'],
    viva: [['Raising the intensity of the light raises', ['The photocurrent only', 'The stopping potential only', 'Both'], 0,
      'More photons free more electrons, but each photon still carries hf.'],
      ['The slope of the stopping potential against frequency depends on', ['Nothing but h/e', 'The metal', 'The intensity'], 0,
        'eVs = hf − eφ: the metal only moves the line, never its slope.'],
      ['Light below the threshold frequency gives', ['No current, however bright', 'A small current', 'A delayed current'], 0,
        'One photon cannot pay the work function, and two photons do not add up here.']],
    askState: function () {
      return { experiment: 'photoelectric effect: stopping potential against frequency, for Planck\'s constant',
        cathode: SAMPLE, lamp_on: st.lamp, filter_nm: nm(LAMS[st.f]),
        filter_frequency_Hz: freq(LAMS[st.f]), retarding_voltage_V: readV(), photocurrent_nA: readI(),
        stopping_potential_here_V: +stopV(LAMS[st.f]).toFixed(3), readings_taken: S.rows.length };
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Line the bench up and switch the lamp on');
          u.p('Lamp, filter wheel and photocell are in one line, the photocell in its light-tight hood. The control unit\'s terminals go to the photocell: the anode to the positive side, so its voltage pushes the electrons back.');
          u.task('1. Switch the mercury lamp on', st.lamp, st.lamp ? 'Lamp on, pilot lit' : 'The hand presses the rocker on the lamp housing')
            .add(u.button(st.lamp ? 'Lamp is on' : 'Switch the lamp on', function () { S.focus('lamp'); setLamp(true); }, !st.lamp, st.lamp || S.hand.busy));
          u.task('2. Put the shortest wavelength in the beam', st.f === 0, 'Filter ' + nm(LAMS[st.f]) + ' nm in the beam')
            .add(u.button('Turn the wheel to ' + nm(LAMS[0]) + ' nm', function () { S.focus('wheel'); turnWheel(0); }, false, S.hand.busy));
          u.live(function () { return st.lamp ? 'Filter ' + nm(LAMS[st.f]) + ' nm  ·  retarding voltage ' + readV().toFixed(2) + ' V  ·  current ' + readI().toFixed(2) + ' nA' : 'Lamp off: the displays read zero'; });
          u.note('Never look into the lamp port: a mercury lamp gives strong ultraviolet light.');
          u.next('Next: find the stopping potentials', st.lamp);
        },
        ok: function () { return st.lamp; },
        auto: function () { return setLamp(true).then(function () { return turnWheel(0); }); } },

      { id: 'cutoff', title: 'Stopping potentials', view: 'unit', render: function (u) {
          u.h2('Find the cut-off voltage for each filter');
          u.p('For each filter, raise the retarding voltage in steps of 0.01 V until the current display just reads 0.00 nA, then record it. Take at least three filters; a line whose photons are too weak gives no current at all, which is itself a result.');
          var sel = { i: st.f };
          u.slider('Filter on the wheel', 1, LAMS.length, 1, function () { return sel.i + 1; },
            function (v) { sel.i = Math.round(v) - 1; }, '', 0);
          u.row(u.button('Turn the wheel', function () { S.focus('wheel'); turnWheel(sel.i); }, true, S.hand.busy),
            u.button('Creep up to the cut-off', function () { S.focus('unit'); findCutOff(); }, false, S.hand.busy));
          u.row(u.button('Record λ and V_s', function () { record(); }, false, S.hand.busy),
            u.button('Knob back to zero', function () { turnTo(0); }, false, S.hand.busy || st.V === 0));
          u.live(function () { return 'Filter ' + nm(LAMS[st.f]) + ' nm  ·  ' + readV().toFixed(2) + ' V  ·  ' + readI().toFixed(2) + ' nA'; });
          u.h3('Observation table'); u.table();
          u.task('Brightness check (no reading needed)', st.hooded, st.hooded ? 'Half the light: the current falls, the cut-off does not move' : 'Pull the lamp back and watch what changes')
            .add(u.button('Halve the light', function () { intensityCheck(); }, false, S.hand.busy));
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 filters recorded (four is better).');
          u.next('Next: plot V_s against frequency', S.rows.length >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          var order = [];
          for (var i = 0; i < LAMS.length; i++) order.push(i);
          return order.reduce(function (pr, i) {
            return pr.then(function () { return turnWheel(i); })
              .then(function () { return findCutOff(); })
              .then(function (ok) { if (ok) record(); });
          }, Promise.resolve()).then(function () { return intensityCheck(); });
        } },
    ],

    tick: function () {
      showV(st.lamp ? readV().toFixed(2) : '0.00', 'V');
      showI(st.lamp ? readI().toFixed(2) : '0.00', 'nA');
      for (var i = 0; i < glasses.length; i++) {
        var lit = st.lamp && i === st.f;
        glasses[i].emissive = new T.Color(lit ? FCOL[i % FCOL.length] : 0x000000);
        glasses[i].emissiveIntensity = lit ? 1.6 : 0;
      }
      var fc = FCOL[st.f % FCOL.length];
      beamA.mat.opacity = st.lamp ? 0.11 : 0;
      beamB.mat.color.setHex(fc); beamB.mat.opacity = st.lamp ? 0.16 : 0;
      hudF.set(nm(LAMS[st.f]) + ' nm');
      hudV.set(readV().toFixed(2) + ' V');
      hudI.set(st.lamp ? readI().toFixed(2) + ' nA' : '—');
    },
  };
});
