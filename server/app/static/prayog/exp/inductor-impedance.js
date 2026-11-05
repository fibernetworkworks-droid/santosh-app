/* Prayogshala studio rig `inductor-impedance`: the resistance and impedance of a coil, with and without an iron core
   (CBSE Class XII, Alternating Current). A coil of many turns with a removable iron core, two cells for the direct
   current, the 3 / 6 / 9 V secondary of a step-down transformer for the alternating current, a two-way selector, two
   digital multimeters (volts and milliamps) and an oscilloscope whose screen is drawn from the waveform the AC phasor
   engine gives (packs/engine_ug.js: the coil as a complex impedance, with a time-domain trace of v and i).
   Nothing here is at mains voltage: the student touches only the low-voltage secondary. */
HoolaStudio.define('inductor-impedance', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign, K = HK.K.eng_acphasor;
  function labParams() {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor('eng_acphasor', o);
  }
  var p = labParams();
  p.topo = 2;
  var RT2 = Math.SQRT2, VDC = 3.0;
  var st = { checked: false, power: false, ac: false, core: false, tap: 6, scope: false, Rdc: null, view: null };
  function fmt(v, d) { return (isFinite(v) ? v : 0).toFixed(d); }
  function sync() { p.V = st.tap * RT2; p.core = st.core ? 1 : 0; return p; }
  function look() { sync(); st.view = K.view(null, p); return st.view; }
  function vAc() { return st.tap; }                               // volts rms on the voltmeter
  function iAc() { return look().I / RT2; }                       // amps rms on the ammeter
  function iDc() { return VDC / p.r; }                            // a steady current meets only the resistance
  function meters() {
    if (!st.power) return { v: null, i: null };
    return st.ac ? { v: vAc(), i: iAc() * 1000 } : { v: VDC, i: iDc() * 1000 };
  }

  // ---------- bench pieces
  var tx = new T.Group(); S.scene.add(tx); tx.position.set(-0.5, 0, -0.1);
  var txb = S.rounded(0.15, 0.11, 0.1, 0.008, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 })); txb.rotation.x = -Math.PI / 2; txb.position.y = 0.05; tx.add(txb);
  var lam = S.mesh(new T.BoxGeometry(0.15, 0.012, 0.11), M.iron); lam.position.y = 0.106; tx.add(lam);
  var txl = S.label('STEP-DOWN TRANSFORMER', { w: 0.12, ratio: 0.11, color: '#e8e2cf', weight: 700 }); txl.position.set(0, 0.075, 0.0555); tx.add(txl);
  var txl2 = S.label('230 V in  ·  3 · 6 · 9 V out  ·  50 Hz', { w: 0.12, ratio: 0.1, color: '#b9bec6' }); txl2.position.set(0, 0.058, 0.0555); tx.add(txl2);
  var rocker = S.rounded(0.02, 0.014, 0.01, 0.003, M.bakelite); rocker.position.set(-0.05, 0.035, 0.058); tx.add(rocker);
  var tapDial = new T.Group(); tapDial.position.set(0.0, 0.032, 0.058); tx.add(tapDial);
  var tapK = S.mesh(new T.CylinderGeometry(0.014, 0.015, 0.012, 28), M.black); tapK.rotation.x = Math.PI / 2; tapDial.add(tapK);
  var tapM = S.mesh(new T.BoxGeometry(0.002, 0.012, 0.0014), M.red, false); tapM.position.set(0, 0.007, 0.0072); tapDial.add(tapM);
  var sRed = S.terminal([0.04, 0.0, 0.0], 'red'), sBlk = S.terminal([0.062, 0.0, 0.0], 'black');
  [sRed, sBlk].forEach(function (t, i) { t.position.set(-0.5 + 0.04 + i * 0.022, 0.033, -0.1 + 0.058); t.rotation.x = Math.PI / 2; });
  var pilotM = new T.MeshStandardMaterial({ color: 0x14401c, roughness: 0.3 });
  var pilot = S.mesh(new T.SphereGeometry(0.0045, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), pilotM); pilot.position.set(-0.03, 0.044, 0.056); pilot.rotation.x = Math.PI / 2; tx.add(pilot);
  S.contact(0.22, 0.17, -0.5, -0.1, 0.5);
  function setTap() { tapDial.rotation.z = -((st.tap - 6) / 3) * 0.9; }
  function setPilot() { pilotM.color.setHex(st.power ? 0x3ae05a : 0x14401c); pilotM.emissive.setHex(st.power ? 0x2ad04a : 0x000000); pilotM.emissiveIntensity = st.power ? 2 : 0; rocker.rotation.x = st.power ? -0.25 : 0.25; }
  setTap(); setPilot();

  var cells = [S.cell([-0.5, 0, 0.1], { text: '1.5 V' }), S.cell([-0.5, 0, 0.17], { text: '1.5 V', color: 0x7a2a1e })];

  // the two-way selector: DC (cells) or AC (transformer secondary)
  var sel = new T.Group(); S.scene.add(sel); sel.position.set(-0.28, 0, 0.12);
  var selb = S.rounded(0.12, 0.08, 0.03, 0.006, M.bakelite); selb.rotation.x = -Math.PI / 2; selb.position.y = 0.015; sel.add(selb);
  var selTex = S.canvasTex(384, 192, function (x, w, h) { x.fillStyle = '#23262b'; x.fillRect(0, 0, w, h); x.fillStyle = '#e8e2cf'; x.font = '700 38px "Public Sans", sans-serif'; x.textAlign = 'center';
    x.fillText('DC  (cells)', w * 0.2, 56); x.fillText('AC  (6 V)', w * 0.8, 56); x.font = '600 28px "Public Sans", sans-serif'; x.fillStyle = '#b9bec6'; x.fillText('TWO-WAY SELECTOR', w / 2, h - 28); });
  var selp = new T.Mesh(new T.PlaneGeometry(0.11, 0.055), new T.MeshStandardMaterial({ map: selTex, roughness: 0.6 })); selp.rotation.x = -Math.PI / 2; selp.position.set(0, 0.0305, 0.0); sel.add(selp);
  var lever = new T.Group(); lever.position.set(0, 0.034, 0.012); sel.add(lever);
  var lv = S.mesh(new T.BoxGeometry(0.008, 0.026, 0.008), M.chrome); lv.position.y = 0.013; lever.add(lv);
  var lk = S.mesh(new T.SphereGeometry(0.007, 14, 10), M.black); lk.position.y = 0.028; lever.add(lk);
  function setLever() { lever.rotation.z = st.ac ? -0.6 : 0.6; }
  setLever();
  S.contact(0.17, 0.13, -0.28, 0.12, 0.45);

  // the coil with its iron core
  var CX = 0.0, CZ = 0.05, COILR = 0.045, COILL = 0.11, BORE = 0.017;
  var coil = new T.Group(); S.scene.add(coil); coil.position.set(CX, COILR + 0.012, CZ);
  var windTex = S.canvasTex(256, 64, function (x, w, h) { x.fillStyle = '#9a5a2a'; x.fillRect(0, 0, w, h); for (var i = 0; i < w; i += 3) { x.fillStyle = (i % 6 === 0) ? '#c98a4e' : '#7a4520'; x.fillRect(i, 0, 2, h); } });
  windTex.wrapS = T.RepeatWrapping;
  var wind = S.mesh(new T.CylinderGeometry(COILR, COILR, COILL, 72, 1, true), new T.MeshStandardMaterial({ map: windTex, roughness: 0.4, metalness: 0.5, side: T.DoubleSide })); wind.rotation.z = Math.PI / 2; coil.add(wind);
  [-1, 1].forEach(function (s) { var fl = S.mesh(new T.CylinderGeometry(COILR + 0.004, COILR + 0.004, 0.006, 72), M.bakelite); fl.rotation.z = Math.PI / 2; fl.position.x = s * (COILL / 2 + 0.003); coil.add(fl); });
  var bore = S.mesh(new T.CylinderGeometry(BORE, BORE, COILL + 0.016, 40, 1, true), new T.MeshStandardMaterial({ color: 0x151515, roughness: 0.9, side: T.DoubleSide }), false); bore.rotation.z = Math.PI / 2; coil.add(bore);
  var cL = S.terminal([0, 0, 0], 'red'), cR = S.terminal([0, 0, 0], 'black');
  cL.position.set(CX - 0.035, 0.0, CZ + 0.07); cR.position.set(CX + 0.035, 0.0, CZ + 0.07);
  var stand0 = S.rounded(0.15, 0.06, 0.012, 0.004, M.darkWood); stand0.rotation.x = -Math.PI / 2; stand0.position.set(CX, 0.006, CZ); S.scene.add(stand0);
  var cl = S.label('COIL', { w: 0.04, ratio: 0.2, color: '#f3ead2', weight: 700 }); cl.position.set(0, 0, COILR + 0.007); coil.add(cl);
  S.contact(0.2, 0.12, CX, CZ, 0.5);
  var coreTex = S.canvasTex(256, 64, function (x, w, h) { x.fillStyle = '#6d727b'; x.fillRect(0, 0, w, h); for (var i = 0; i < w; i += 4) { x.fillStyle = (i % 8 === 0) ? '#8b919b' : '#575c64'; x.fillRect(i, 0, 3, h); } });
  var core = new T.Group(); S.scene.add(core);
  var corem = S.mesh(new T.CylinderGeometry(0.0145, 0.0145, 0.19, 36), new T.MeshStandardMaterial({ map: coreTex, roughness: 0.4, metalness: 0.8 })); corem.rotation.z = Math.PI / 2; core.add(corem);
  var CORE_OUT = new T.Vector3(CX + 0.2, 0.03, CZ + 0.12), CORE_IN = new T.Vector3(CX, COILR + 0.012, CZ);
  function placeCore() { core.position.copy(st.core ? CORE_IN : CORE_OUT); core.rotation.y = st.core ? 0 : 0.5; }
  placeCore();
  var coreRest = S.rounded(0.22, 0.04, 0.012, 0.004, M.darkWood); coreRest.rotation.x = -Math.PI / 2; coreRest.position.set(CORE_OUT.x, 0.006, CORE_OUT.z); coreRest.rotation.z = 0.5; S.scene.add(coreRest);

  // two digital multimeters
  function dmm(x, z, name) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z);
    var bd = S.rounded(0.1, 0.17, 0.045, 0.008, new T.MeshStandardMaterial({ color: 0xe3a21e, roughness: 0.5 })); bd.rotation.x = -Math.PI / 2 + 0.7; bd.position.y = 0.085; g.add(bd);
    var face = new T.Group(); face.rotation.x = -Math.PI / 2 + 0.7; face.position.set(0, 0.085, 0); g.add(face);
    var lcd = S.liveTex(400, 180), scr = new T.Mesh(new T.PlaneGeometry(0.076, 0.034), new T.MeshBasicMaterial({ map: lcd, toneMapped: false })); scr.position.set(0, 0.052, 0.0262); face.add(scr);
    var bz = S.mesh(new T.BoxGeometry(0.082, 0.04, 0.003), M.black); bz.position.set(0, 0.052, 0.0235); face.add(bz);
    var dial = S.mesh(new T.CylinderGeometry(0.02, 0.022, 0.012, 36), M.blackPlastic); dial.rotation.x = Math.PI / 2; dial.position.set(0, -0.012, 0.027); face.add(dial);
    var dm = S.mesh(new T.BoxGeometry(0.002, 0.02, 0.0014), M.white, false); dm.position.set(0, -0.012 + 0.008, 0.0335); face.add(dm);
    var lb = S.label(name, { w: 0.06, ratio: 0.14, color: '#1a1a1a', weight: 700 }); lb.position.set(0, 0.0785, 0.0243); face.add(lb);
    [[-0.026, 'black'], [0.0, 'red'], [0.026, 'red']].forEach(function (q) { var j = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.01, 16), q[1] === 'red' ? M.red : M.blackPlastic); j.rotation.x = Math.PI / 2; j.position.set(q[0], -0.058, 0.026); face.add(j); });
    S.contact(0.14, 0.18, x, z, 0.5);
    return { group: g, lcd: lcd, key: '' };
  }
  var dmV = dmm(-0.15, -0.26, 'TRUE RMS · VOLTS'), dmA = dmm(0.02, -0.26, 'TRUE RMS · MILLIAMPS');
  function showDmm(d, val, unit, dp) {
    var txt = val === null ? '' : fmt(val, dp), mode = st.ac ? 'AC' : 'DC', key = txt + unit + mode + st.power;
    if (d.key === key) return; d.key = key;
    d.lcd.draw(function (c, w, h) { c.fillStyle = '#b9c4a7'; c.fillRect(0, 0, w, h); c.fillStyle = 'rgba(0,0,0,.07)'; c.font = '700 96px "JetBrains Mono", monospace'; c.textAlign = 'right'; c.fillText('8888.8', w - 90, 124);
      c.fillStyle = '#1b2116'; c.fillText(txt, w - 90, 124); c.font = '600 40px "Public Sans", sans-serif'; c.textAlign = 'left'; c.fillText(unit, w - 82, 124); c.font = '600 30px "Public Sans", sans-serif'; c.fillText(val === null ? 'OFF' : mode, 16, 40); });
  }

  // the oscilloscope: its screen is drawn from the engine's v(t) and i(t)
  var sc = new T.Group(); S.scene.add(sc); sc.position.set(0.4, 0, -0.26);
  var scb = S.rounded(0.3, 0.24, 0.28, 0.01, new T.MeshStandardMaterial({ color: 0x8e949c, roughness: 0.5 })); scb.rotation.x = -Math.PI / 2; scb.position.y = 0.12; sc.add(scb);
  var bezel = S.mesh(new T.BoxGeometry(0.21, 0.165, 0.006), M.black); bezel.position.set(-0.03, 0.14, 0.1425); sc.add(bezel);
  var scrTex = S.liveTex(600, 480); var scrM = new T.Mesh(new T.PlaneGeometry(0.2, 0.16), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false })); scrM.position.set(-0.03, 0.14, 0.1458); sc.add(scrM);
  var scLab = S.label('OSCILLOSCOPE · 2 CHANNEL', { w: 0.14, ratio: 0.08, color: '#d7dbe0', weight: 700 }); scLab.position.set(-0.03, 0.235, 0.1427); sc.add(scLab);
  var scPow = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.008, 20), M.red); scPow.rotation.x = Math.PI / 2; scPow.position.set(0.105, 0.19, 0.145); sc.add(scPow);
  [0.15, 0.115, 0.08].forEach(function (y) { var k = S.mesh(new T.CylinderGeometry(0.011, 0.012, 0.012, 24), M.blackPlastic); k.rotation.x = Math.PI / 2; k.position.set(0.105, y - 0.04, 0.145); sc.add(k); });
  S.contact(0.36, 0.3, 0.4, -0.26, 0.5);
  var scKey = '';
  var VDIVS = [0.5, 1, 2, 5, 10], IDIVS = [1, 2, 5, 10, 20, 50, 100, 200];
  function pick(list, peak) { for (var i = 0; i < list.length; i++) if (peak / list[i] <= 3.5) return list[i]; return list[list.length - 1]; }
  function drawScope() {
    var v = st.view || look(), key = [st.scope, st.power, st.ac, st.tap, st.core, p.f].join('|'); if (key === scKey) return; scKey = key;
    scrTex.draw(function (c, w, h) {
      c.fillStyle = '#06130c'; c.fillRect(0, 0, w, h);
      var dx = w / 10, dy = h / 8, i;
      c.strokeStyle = 'rgba(80,200,120,.22)'; c.lineWidth = 1; for (i = 0; i <= 10; i++) { c.beginPath(); c.moveTo(i * dx, 0); c.lineTo(i * dx, h); c.stroke(); } for (i = 0; i <= 8; i++) { c.beginPath(); c.moveTo(0, i * dy); c.lineTo(w, i * dy); c.stroke(); }
      c.strokeStyle = 'rgba(80,200,120,.5)'; c.beginPath(); c.moveTo(0, h / 2); c.lineTo(w, h / 2); c.stroke();
      if (!st.scope) { c.fillStyle = '#2f5a3e'; c.font = '600 28px "Public Sans", sans-serif'; c.fillText('OFF', 24, 50); return; }
      if (!st.power || !st.ac) { c.fillStyle = '#9fe2b4'; c.font = '600 22px "JetBrains Mono", monospace'; c.fillText(st.power ? 'DC: a flat line' : 'no signal', 16, 34); c.strokeStyle = '#ffd24a'; c.lineWidth = 2.5; c.beginPath(); c.moveTo(0, h / 2 - (st.power ? 3 * dy / 1 * 0.0 : 0)); c.lineTo(w, h / 2); c.stroke(); return; }
      var vd = pick(VDIVS, st.tap * RT2), idv = pick(IDIVS, v.I * 1000), n = v.vs.length, tms = 5e-3 * 10;
      function plot(arr, scale, col) { c.strokeStyle = col; c.lineWidth = 2.6; c.beginPath();
        for (var k = 0; k <= 400; k++) { var t = tms * k / 400, idx = Math.floor(((t / (2 / p.f)) % 1) * n), yv = arr[idx % n] / scale; var X = k / 400 * w, Y = h / 2 - yv * dy; if (k === 0) c.moveTo(X, Y); else c.lineTo(X, Y); }
        c.stroke(); }
      plot(v.vs, vd, '#ffd24a'); plot(v.ic.map(function (q) { return q * 1000; }), idv, '#5bd8ff');
      c.font = '600 21px "JetBrains Mono", monospace'; c.fillStyle = '#ffd24a'; c.fillText('CH1 ' + vd + ' V/div', 14, 28); c.fillStyle = '#5bd8ff'; c.fillText('CH2 ' + idv + ' mA/div', 14, 54);
      c.fillStyle = '#9fe2b4'; c.textAlign = 'right'; c.fillText('5 ms/div', w - 14, 28); c.fillText('f = ' + fmt(p.f, 0) + ' Hz', w - 14, 54); c.textAlign = 'left';
    });
  }

  // wires
  S.wire([[-0.5 + 0.04, 0.04, -0.04], [-0.4, 0.03, 0.05], [-0.31, 0.034, 0.11]], 'red');
  S.wire([[-0.5 + 0.062, 0.04, -0.04], [-0.38, 0.025, 0.06], [-0.27, 0.034, 0.13]], 'black');
  S.wire([[-0.5, 0.045, 0.1], [-0.4, 0.03, 0.1], [-0.31, 0.034, 0.12]], 'yellow');
  S.wire([[-0.24, 0.034, 0.1], [-0.12, 0.03, 0.12], [CX - 0.035, 0.012, CZ + 0.07]], 'red');
  S.wire([[-0.24, 0.034, 0.13], [0.1, 0.03, 0.16], [CX + 0.035, 0.012, CZ + 0.07]], 'black');
  S.wire([[CX - 0.035, 0.012, CZ + 0.07], [-0.1, 0.05, -0.08], [-0.15, 0.07, -0.2]], 'blue');
  S.wire([[CX + 0.035, 0.012, CZ + 0.07], [0.02, 0.05, -0.08], [0.02, 0.07, -0.2]], 'yellow');
  S.wire([[CX + 0.035, 0.012, CZ + 0.07], [0.25, 0.04, -0.05], [0.38, 0.06, -0.15]], 'blue');

  S.addApparatus('tx', tx, 'Step-down transformer', 'It changes the 230 V mains to a safe 3, 6 or 9 V. Only this low-voltage secondary is connected to the coil, never the mains.');
  S.addApparatus('cells', cells[0], 'Two dry cells', 'Together they give a steady 3 V for the direct-current measurement.');
  S.addApparatus('sel', sel, 'Two-way selector', 'It connects the coil either to the cells (DC) or to the transformer (AC).');
  S.addApparatus('coil', coil, 'Coil', 'Many turns of enamelled copper wire on a bobbin, with a hole through its middle for the iron core.');
  S.addApparatus('core', core, 'Iron core', 'A bundle of soft-iron wires that slides into the coil. It concentrates the magnetic field and raises the inductance several times.');
  S.addApparatus('dmmV', dmV.group, 'Voltmeter', 'A true-RMS multimeter on its volts range, across the coil. It reads DC or AC as set.');
  S.addApparatus('dmmA', dmA.group, 'Milliammeter', 'A true-RMS multimeter on its milliamp range, in series with the coil.');
  S.addApparatus('scope', sc, 'Oscilloscope', 'Channel 1 (yellow) shows the voltage across the coil, channel 2 (blue) the current. With AC the current lags the voltage.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudS = S.hudCard('Source'), hudV = S.hudCard('Voltmeter'), hudI = S.hudCard('Milliammeter');

  // ---------- human actions
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function power(on) {
    if (busy()) return Promise.resolve();
    if (on === st.power && (!on || st.scope)) return Promise.resolve();
    return S.hand.tap(rocker, 'front').then(function () { st.power = on; setPilot(); S.click(900, 0.05);
      if (on) return S.hand.tap(scPow, 'front').then(function () { st.scope = true; S.say('The transformer and the scope are on. The pilot lamp is lit.'); });
      st.scope = false; return null; }).then(function () { S.render(); });
  }
  function setSource(ac) {
    if (busy()) return Promise.resolve();
    if (st.ac === ac) return Promise.resolve();
    return S.hand.tap(lk, 'front').then(function () { st.ac = ac; setLever(); S.click(1200, 0.04); S.say(ac ? 'The coil is on the 6 V secondary: alternating current.' : 'The coil is on the cells: direct current.'); S.render(); });
  }
  function setTapTo(v) {
    if (busy()) return Promise.resolve();
    if (st.tap === v) return Promise.resolve();
    return S.hand.tap(tapK, 'front').then(function () { st.tap = v; setTap(); S.click(1000, 0.04); S.render(); });
  }
  function moveCore(inside) {
    if (busy()) return Promise.resolve();
    if (st.core === inside) return Promise.resolve();
    var a = inside ? CORE_OUT.clone() : CORE_IN.clone(), b = inside ? CORE_IN.clone() : CORE_OUT.clone();
    return S.hand.pinchMove(a, function (k) { var q = new T.Vector3().lerpVectors(a, b, k); q.y += 0.04 * Math.sin(Math.PI * k); return q; },
      function (k) { var q = new T.Vector3().lerpVectors(a, b, k); core.position.copy(q); core.rotation.y = inside ? 0.5 * (1 - k) : 0.5 * k; st.core = inside ? k > 0.999 : k < 0.001; }, { ms: 1500, reachMs: 600 }).then(function () {
      st.core = inside; placeCore(); S.say(inside ? 'The iron core is inside the coil.' : 'The iron core is out of the coil.'); S.render(); });
  }
  function noteR() {
    if (busy()) return false;
    if (!st.power) { S.say('Switch the transformer and the scope on first.'); return false; }
    if (st.ac) { S.say('Put the selector on DC: the resistance is found with a steady current.'); return false; }
    var m = meters(), V = Math.round(m.v * 100) / 100, I = Math.round(m.i * 10) / 10;
    st.Rdc = Math.round(V / (I / 1000) * 10) / 10; S.say('R = V / I = ' + fmt(V, 2) + ' / ' + fmt(I / 1000, 4) + ' = ' + fmt(st.Rdc, 1) + ' ohm.'); S.render(); return true;
  }
  function record() {
    if (busy()) return false;
    if (!st.power) { S.say('Switch on first.'); return false; }
    if (!st.ac) { S.say('Put the selector on AC to take an impedance reading.'); return false; }
    if (st.Rdc === null) { S.say('Find the resistance R with direct current first.'); return false; }
    if (S.rows.some(function (r) { return r.core === (st.core ? 1 : 0) && r.tap === st.tap; })) { S.say('You already have a reading with this voltage and this core. Change the voltage or the core.'); return false; }
    var m = meters(), V = Math.round(m.v * 100) / 100, I = Math.round(m.i * 10) / 10;
    S.addRow({ core: st.core ? 1 : 0, tap: st.tap, V: V, I: I / 1000, r: st.Rdc });
    S.say('Written: ' + (st.core ? 'with' : 'without') + ' the core, V = ' + fmt(V, 2) + ' V, I = ' + fmt(I, 1) + ' mA.'); return true;
  }
  function Lof(r) { var Z = r.V / r.I; return Math.sqrt(Math.max(Z * Z - r.r * r.r, 0)) / (2 * Math.PI * p.f); }
  function airRows(rows) { return (rows || []).filter(function (r) { return !r.core; }); }
  function enough() { return airRows(S.rows).length >= 2 && S.rows.filter(function (r) { return r.core; }).length >= 2; }

  var VIEWS = { bench: [[0.0, 0.62, 1.1], [-0.05, 0.08, -0.05]], tx: [[-0.4, 0.26, 0.3], [-0.5, 0.05, -0.1]], sel: [[-0.2, 0.22, 0.4], [-0.28, 0.02, 0.12]], coil: [[0.1, 0.22, 0.35], [CX, 0.05, CZ]],
    core: [[CX + 0.3, 0.2, CZ + 0.4], [CX + 0.1, 0.04, CZ + 0.08]], dmmV: [[-0.15, 0.2, 0.1], [-0.15, 0.08, -0.26]], dmmA: [[0.02, 0.2, 0.1], [0.02, 0.08, -0.26]],
    scope: [[0.4, 0.22, 0.28], [0.4, 0.14, -0.26]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] };
  var rc = null;
  function refresh() {
    var m = meters(); showDmm(dmV, m.v, 'V', 2); showDmm(dmA, m.i, 'mA', 1); drawScope();
    hudS.set(!st.power ? 'off' : st.ac ? 'AC ' + st.tap + ' V' : 'DC 3 V (cells)'); hudV.set(m.v === null ? '—' : fmt(m.v, 2) + ' V'); hudI.set(m.i === null ? '—' : fmt(m.i, 1) + ' mA');
  }
  refresh();

  return {
    camera: { pos: [0.0, 0.62, 1.1], look: [-0.05, 0.08, -0.05] },
    views: VIEWS,
    theory: { principle: 'A coil has resistance R and inductance L in series. A steady current meets only R. An alternating current also meets the reactance X = 2πfL, and the two add at right angles: Z = √(R² + X²). The voltage leads the current by tan φ = X / R. An iron core concentrates the magnetic field, so L, and so Z, rises several times.',
      formula: 'Z = V / I = √(R² + (2πfL)²)', formulaNote: 'R from the DC readings · V and I are the AC voltmeter and milliammeter readings (rms) · f = ' + fmt(p.f, 0) + ' Hz · L = √(Z² − R²) / 2πf',
      more: ['With the core in, the same voltage drives a much smaller current. The scope shows the current lagging the voltage by nearly a quarter of a cycle, since R is small compared with the reactance.'],
      precautions: 'Use only the low-voltage secondary of the step-down transformer; never connect the coil to the mains. Switch the supply off before changing the circuit. Read both meters at the same moment.' },
    book: { title: 'Expt. — Resistance and impedance of a coil', lines: ['Aim: R and L of a coil, with and without an iron core.', 'DC: R = V / I.  AC (f = ' + fmt(p.f, 0) + ' Hz): Z = V / I.', 'L = √(Z² − R²) / (2πf)', 'Supply: 3 / 6 / 9 V secondary of a step-down transformer only.'],
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Core', get: function (r) { return r.core ? 'in' : 'out'; } }, { label: 'V (V)', get: function (r) { return r.V.toFixed(2); } },
        { label: 'I (mA)', get: function (r) { return (r.I * 1000).toFixed(1); } }, { label: 'Z (Ω)', get: function (r) { return (r.V / r.I).toFixed(1); } }, { label: 'L (mH)', get: function (r) { return (Lof(r) * 1000).toFixed(1); } }] },
    graph: null,
    result: function (rows) { var a = airRows(rows); if (a.length < 2) return null; var ls = a.map(Lof), L = S.fit.mean(ls), withCore = (rows || []).filter(function (r) { return r.core; });
      var note = 'Mean of √(Z² − R²) / 2πf without the core, with R = ' + fmt(a[0].r, 1) + ' Ω.'; if (withCore.length) note += ' With the core the same formula gives about ' + fmt(S.fit.mean(withCore.map(Lof)) * 1000, 0) + ' mH.';
      return { label: 'L of the coil without the core', value: L * 1000, unit: 'mH', digits: 1, truth: p.L * 1000, note: note }; },
    tol: 0.02,
    chips: ['Why does the iron core raise the impedance?', 'Why is R found with DC?', 'What does the phase shift on the scope mean?', 'Check my readings'],
    viva: [['The iron core is pushed into the coil. The current from the AC source', ['falls', 'rises', 'stays the same'], 0, 'The inductance, and so the reactance and the impedance, rise.'],
      ['The same coil on a battery draws a much larger current than on AC of the same voltage because', ['only its resistance limits a steady current', 'AC is weaker', 'the battery is bigger'], 0, 'A steady current has no reactance.']],
    askState: function () { var m = meters(), v = st.view || look(); return { supply_on: st.power, source: st.ac ? 'AC from the ' + st.tap + ' V secondary' : 'DC from two cells', iron_core: st.core ? 'in' : 'out', voltmeter: m.v === null ? null : +fmt(m.v, 2), milliammeter: m.i === null ? null : +fmt(m.i, 1),
      R_dc_noted_ohm: st.Rdc, frequency_Hz: p.f, phase_of_voltage_ahead_deg: st.ac && st.power ? +(v.phi * 180 / Math.PI).toFixed(1) : null, readings_recorded: S.rows.length }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Check the circuit and switch on');
          u.p('The coil is in series with the milliammeter, and the voltmeter is across it. A two-way selector connects it to the two cells or to the 6 V secondary of the step-down transformer. The scope shows the voltage and the current.');
          u.task('1. Check the connections', st.checked, st.checked ? 'Coil, meters and selector are connected' : 'Look over the circuit').add(u.button(st.checked ? 'Checked' : 'Check the circuit', function () { st.checked = true; S.focus('sel'); S.say('The meters are in the right places and every terminal is tight.'); S.render(); }, !st.checked, st.checked));
          u.task('2. Switch on the transformer and the scope', st.power && st.scope, st.power && st.scope ? 'Pilot lamp lit, scope on' : 'The hand presses the rocker, then the scope switch').add(u.button(st.power ? 'Switch off' : 'Switch on', function () { S.focus('tx'); power(!st.power); }, !st.power, S.hand.busy));
          u.note('Only the low-voltage secondary (3, 6 or 9 V) is connected to the coil. Never connect the coil to the mains. Switch off before changing the circuit.');
          u.next('Next: direct current', st.checked && st.power && st.scope);
        },
        ok: function () { return st.checked && st.power && st.scope; }, auto: function () { st.checked = true; return power(true); } },
      { id: 'dc', title: 'DC resistance', view: 'dmmV', render: function (u) {
          u.h2('Find the resistance R of the coil with direct current');
          u.p('Put the selector on DC. The cells drive a steady current through the coil. Read the voltmeter and the milliammeter and work out R = V / I.');
          u.task('Selector', !st.ac, st.ac ? 'On AC' : 'On DC').add(u.button('Selector to DC', function () { S.focus('sel'); setSource(false); }, st.ac, S.hand.busy || !st.ac));
          u.live(function () { var m = meters(); return 'V = ' + (m.v === null ? '—' : fmt(m.v, 2) + ' V') + '   I = ' + (m.i === null ? '—' : fmt(m.i, 1) + ' mA') + (st.Rdc !== null ? '   R = ' + fmt(st.Rdc, 1) + ' Ω' : ''); });
          u.row(u.button('Note R = V / I', function () { noteR(); S.render(); }, st.Rdc === null, S.hand.busy), u.button('Look at the meters', function () { S.focus('dmmV'); }));
          u.next('Next: alternating current', st.Rdc !== null);
        },
        ok: function () { return st.Rdc !== null; }, auto: function () { return setSource(false).then(function () { noteR(); }); } },
      { id: 'ac', title: 'AC impedance', view: 'scope', render: function (u) {
          u.h2('Read V and I with alternating current, without and with the core');
          u.p('Put the selector on AC. For each setting of the transformer, read V and I and record. Do it for two voltages without the core, then push the core in and repeat. Watch the scope: the current lags the voltage.');
          u.task('Selector', st.ac, st.ac ? 'On AC' : 'On DC').add(u.button('Selector to AC', function () { S.focus('sel'); setSource(true); }, !st.ac, S.hand.busy || st.ac));
          u.row(u.button('3 V', function () { setTapTo(3); S.render(); }, st.tap === 3, S.hand.busy), u.button('6 V', function () { setTapTo(6); S.render(); }, st.tap === 6, S.hand.busy), u.button('9 V', function () { setTapTo(9); S.render(); }, st.tap === 9, S.hand.busy));
          u.task('Iron core', st.core, st.core ? 'Inside the coil' : 'Outside the coil').add(u.button(st.core ? 'Take the core out' : 'Push the core in', function () { S.focus('core'); moveCore(!st.core); }, !st.core, S.hand.busy));
          u.live(function () { var m = meters(); return (st.ac ? 'AC ' : 'DC ') + (m.v === null ? '—' : fmt(m.v, 2) + ' V') + '   ' + (m.i === null ? '' : fmt(m.i, 1) + ' mA') + '   core ' + (st.core ? 'in' : 'out'); });
          u.row(u.button('Record this reading', function () { record(); S.render(); }, true, S.hand.busy), u.button('Look at the scope', function () { S.focus('scope'); }));
          u.h3('Observation table'); u.table();
          u.next('Next: result', enough());
          u.p(airRows(S.rows).length + ' without the core and ' + S.rows.filter(function (r) { return r.core; }).length + ' with it recorded (2 of each needed).');
        },
        ok: enough,
        auto: function () {
          return setSource(true).then(function () { return setTapTo(6); }).then(function () { record(); }).then(function () { return setTapTo(9); }).then(function () { record(); })
            .then(function () { return moveCore(true); }).then(function () { return setTapTo(6); }).then(function () { record(); }).then(function () { return setTapTo(9); }).then(function () { record(); });
        } },
    ],
    tick: function () { look(); refresh(); },
  };
});
