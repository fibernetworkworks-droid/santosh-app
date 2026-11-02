/* Prayogshala studio module: Boyle's law (NCERT Class XI, Kinetic Theory).
   Physics: the boyle kernel from kernels.js (P = nRT / V at constant temperature) - the same numbers the server checks.
   A glass syringe of air, clamped nozzle-down, is joined by rubber tubing to a Bourdon pressure gauge. The hand
   closes the pinch clip, then pushes / pulls the plunger; the gauge reads P. PV = nRT comes from the slope of P on 1/V. */
HoolaStudio.define('boyles-law', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.boyle;
  var up = new T.Vector3(0, 1, 0);
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('boyle');
  var VMIN = 20, VMAX = 200, PMAX = 600;
  var st = { V: Math.round(p.V * 1e6), target: 60, clip: false, shownP: 0 };
  function view() { p.V = st.V * 1e-6; return K.view({}, p); }
  function readP() { return Math.round(view().P_kPa); }             // gauge read to the nearest 1 kPa

  function clampStand(jx, jz, armY, armLen, h) {
    var g = S.stand({ x: 0, z: 0, armY: armY, armLen: armLen, h: h });
    var blob = S.scene.children[S.scene.children.length - 1], rotY = -Math.PI / 2;
    g.rotation.y = rotY; var j = new T.Vector3(-0.19 + armLen, 0, 0).applyAxisAngle(up, rotY);
    g.position.set(jx - j.x, 0, jz - j.z);
    var bc = new T.Vector3(-0.12, 0, 0).applyAxisAngle(up, rotY); blob.position.set(g.position.x + bc.x, blob.position.y, g.position.z + bc.z); blob.rotation.z = rotY;
    return g;
  }

  // ---------- the syringe (inner area = the kernel's piston area, so 1 cm of travel = 10 mL)
  var AREA = p.area, RIN = Math.sqrt(AREA / Math.PI), ROUT = RIN + 0.0028, SX = -0.06, SZ = -0.08, YB = 0.17, BL = 0.222;
  var syr = new T.Group(); S.scene.add(syr);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xf2f8fa, roughness: 0.04, metalness: 0, transparent: true, opacity: 0.2, clearcoat: 1, clearcoatRoughness: 0.04, envMapIntensity: 1.6, depthWrite: false, side: T.DoubleSide });
  var barrel = S.mesh(new T.CylinderGeometry(ROUT, ROUT, BL, 48, 1, true), glassM, false, false); barrel.position.set(SX, YB + BL / 2 - 0.004, SZ); syr.add(barrel);
  var inner = S.mesh(new T.CylinderGeometry(RIN, RIN, BL, 48, 1, true), glassM, false, false); inner.position.copy(barrel.position); syr.add(inner);
  var floor = S.mesh(new T.CylinderGeometry(ROUT, ROUT * 0.55, 0.008, 40), glassM, false); floor.position.set(SX, YB - 0.008, SZ); syr.add(floor);
  var nozzle = S.mesh(new T.CylinderGeometry(0.0045, 0.0032, 0.03, 20), glassM, false); nozzle.position.set(SX, YB - 0.027, SZ); syr.add(nozzle);
  var grip = S.rounded(0.085, 0.045, 0.007, 0.012, glassM); grip.rotation.x = -Math.PI / 2; grip.position.set(SX, YB + BL - 0.004, SZ); syr.add(grip);
  var gradTex = S.canvasTex(512, 2048, function (x, w, h) { x.clearRect(0, 0, w, h); x.fillStyle = 'rgba(20,32,60,.95)'; x.font = '700 64px "Public Sans", sans-serif'; x.textAlign = 'left';
    var y0 = h - 60, k = (h - 120) / 210;          // 0..210 mL; zero near the bottom of the canvas
    for (var v = 0; v <= 200; v += 2) { var y = y0 - v * k, big = v % 10 === 0; x.fillRect(150, y - (big ? 3 : 1.5), v % 20 === 0 ? 150 : big ? 100 : 60, big ? 6 : 3); if (v % 20 === 0) x.fillText(String(v), 320, y + 22); }
    x.font = '700 54px "Public Sans", sans-serif'; x.fillText('mL', 320, y0 - 205 * k + 22); });
  var span = (2048 - 120) / 2048;  // fraction of the texture used by 0..210 mL
  var gradMesh = new T.Mesh(new T.CylinderGeometry(ROUT + 0.0004, ROUT + 0.0004, 1, 32, 1, true, -0.55, 1.1),
    new T.MeshStandardMaterial({ map: gradTex, transparent: true, roughness: 0.5, depthWrite: false }));
  var mlPerM = 1 / (AREA * 1e6);    // metres of travel per mL
  var texH = 210 * mlPerM / span;   // the cylinder height that makes 1 mL on the print = 1 mL of travel
  gradMesh.scale.y = texH; gradMesh.position.set(SX, YB - (60 / 2048) * texH + texH / 2, SZ); gradMesh.renderOrder = 4; syr.add(gradMesh);
  var plunger = new T.Group(); S.scene.add(plunger);
  var head = S.mesh(new T.CylinderGeometry(RIN - 0.0003, RIN - 0.0003, 0.012, 40), M.rubber); head.position.y = 0.006; plunger.add(head);
  [0.003, 0.009].forEach(function (y) { var r = S.mesh(new T.TorusGeometry(RIN - 0.0006, 0.0009, 8, 40), M.rubber); r.rotation.x = Math.PI / 2; r.position.y = y; plunger.add(r); });
  var prod = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.24, 20), glassM, false); prod.position.y = 0.012 + 0.12; plunger.add(prod);
  var thumb = S.mesh(new T.CylinderGeometry(0.022, 0.022, 0.006, 40), glassM); thumb.position.y = 0.255; plunger.add(thumb);
  plunger.position.set(SX, 0, SZ);
  // clamp: an aluminium strap round the barrel, bolted to the stand's jaw behind it
  var strap = S.mesh(new T.TorusGeometry(ROUT + 0.002, 0.0028, 10, 40), M.alu); strap.rotation.x = Math.PI / 2; strap.position.set(SX, 0.33, SZ); syr.add(strap);
  var lug = S.rounded(0.012, 0.012, 0.03, 0.003, M.alu); lug.position.set(SX, 0.33, SZ - ROUT - 0.016); syr.add(lug);
  var stand = clampStand(SX, SZ - ROUT - 0.04, 0.33, 0.3, 0.62);
  var sylab = S.label('100 mL ≡ 10.0 cm', { w: 0.04, ratio: 0.14, color: '#2a3b5c' }); sylab.position.set(SX - 0.02, YB + BL - 0.02, SZ + ROUT + 0.0015); syr.add(sylab);

  // ---------- Bourdon gauge on a wooden block
  var GX = 0.2, GY = 0.15, GZ = -0.08, GR = 0.058, SWEEP = 1.5 * Math.PI, A0 = 0.75 * Math.PI;
  var gauge = new T.Group(); gauge.position.set(GX, GY, GZ); S.scene.add(gauge);
  var case_ = S.mesh(new T.CylinderGeometry(GR, GR, 0.034, 56), M.black); case_.rotation.x = Math.PI / 2; gauge.add(case_);
  var bezel = S.mesh(new T.TorusGeometry(GR, 0.0045, 14, 56), M.chrome); bezel.position.z = 0.017; gauge.add(bezel);
  var dialTex = S.canvasTex(1024, 1024, function (x, w) { var c = w / 2, R = 430; x.fillStyle = '#fbfaf5'; x.beginPath(); x.arc(c, c, 500, 0, Math.PI * 2); x.fill();
    x.strokeStyle = '#141414'; x.fillStyle = '#141414'; x.textAlign = 'center';
    for (var v = 0; v <= PMAX; v += 5) { var a = A0 + SWEEP * v / PMAX, big = v % 50 === 0, mid = v % 10 === 0, len = v % 100 === 0 ? 60 : big ? 46 : mid ? 30 : 18;
      x.lineWidth = v % 100 === 0 ? 7 : big ? 5 : 2.5; x.beginPath(); x.moveTo(c + Math.cos(a) * R, c + Math.sin(a) * R); x.lineTo(c + Math.cos(a) * (R - len), c + Math.sin(a) * (R - len)); x.stroke();
      if (v % 100 === 0) { x.font = '700 64px "Public Sans", sans-serif'; x.fillText(String(v), c + Math.cos(a) * (R - 112), c + Math.sin(a) * (R - 112) + 22); } }
    x.lineWidth = 4; x.beginPath(); x.arc(c, c, R, A0, A0 + SWEEP); x.stroke();
    x.font = '700 70px "Newsreader", Georgia, serif'; x.fillText('kPa', c, c + 190);
    x.font = '600 34px "Public Sans", sans-serif'; x.fillText('ABSOLUTE PRESSURE', c, c + 250); x.fillText('BOURDON GAUGE · 0–600', c, c - 170);
    x.fillStyle = '#b3261e'; x.font = '600 30px "Public Sans", sans-serif'; x.fillText('estimate to 1 kPa', c, c + 300); });
  var face = new T.Mesh(new T.CircleGeometry(GR - 0.002, 64), new T.MeshStandardMaterial({ map: dialTex, roughness: 0.55 })); face.position.z = 0.0172; gauge.add(face);
  var needle = new T.Group(); needle.position.z = 0.0195; gauge.add(needle);
  var nd = S.mesh(new T.BoxGeometry(0.046, 0.0016, 0.0008), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.4 }), false); nd.position.x = 0.018; needle.add(nd);
  var tail = S.mesh(new T.BoxGeometry(0.012, 0.0028, 0.0008), M.black, false); tail.position.x = -0.006; needle.add(tail);
  var hub = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.003, 20), M.brass, false); hub.rotation.x = Math.PI / 2; needle.add(hub);
  var gglass = new T.Mesh(new T.CircleGeometry(GR, 48), glassM); gglass.position.z = 0.0215; gauge.add(gglass);
  function needleAngle(Pk) { var f = Math.max(0, Math.min(1.02, Pk / PMAX)); return -(A0 + SWEEP * f); }   // canvas y runs down, so the angle flips
  var socket = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.03, 6), M.brass); socket.position.set(GX, GY - GR - 0.012, GZ); S.scene.add(socket);
  var stem = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, GY - GR - 0.03, 16), M.brass); stem.position.set(GX, (GY - GR - 0.025) / 2 + 0.04, GZ); S.scene.add(stem);
  var gblock = S.rounded(0.1, 0.07, 0.045, 0.006, M.darkWood); gblock.rotation.x = -Math.PI / 2; gblock.position.set(GX, 0.0225, GZ); S.scene.add(gblock);
  var elbow = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.03, 16), M.brass); elbow.rotation.z = Math.PI / 2; elbow.position.set(GX - 0.065, 0.055, GZ); S.scene.add(elbow);
  var stemLow = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.012, 16), M.brass); stemLow.position.set(GX, 0.05, GZ); S.scene.add(stemLow);
  var hose = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.05, 16), M.brass); hose.rotation.z = Math.PI / 2; hose.position.set(GX - 0.03, 0.055, GZ); S.scene.add(hose);
  S.contact(0.16, 0.12, GX, GZ, 0.55);
  // rubber tube: nozzle -> down -> along the bench -> gauge inlet
  var rubberM = new T.MeshStandardMaterial({ color: 0x8e3a26, roughness: 0.62 });
  var tubeCurve = new T.CatmullRomCurve3([[SX, YB - 0.045], [SX, YB - 0.075], [SX + 0.012, 0.045], [SX + 0.07, 0.012], [GX - 0.13, 0.014], [GX - 0.085, 0.055]].map(function (a) { return new T.Vector3(a[0], a[1], SZ); }));
  var rtube = S.mesh(new T.TubeGeometry(tubeCurve, 80, 0.0055, 14, false), rubberM); S.scene.add(rtube);
  var rshadow = S.contact(0.18, 0.04, (SX + GX) / 2 - 0.02, SZ, 0.35);
  // pinch clip on the tube just below the nozzle
  var clip = new T.Group(); clip.position.set(SX, YB - 0.085, SZ); S.scene.add(clip);
  var jawA = S.mesh(new T.BoxGeometry(0.004, 0.006, 0.05), M.steel), jawB = jawA.clone(); clip.add(jawA); clip.add(jawB);
  var spring = S.mesh(new T.TorusGeometry(0.006, 0.0014, 8, 20), M.steel); spring.rotation.y = Math.PI / 2; spring.position.z = -0.03; clip.add(spring);
  var pad = S.mesh(new T.BoxGeometry(0.012, 0.007, 0.014), M.red); pad.position.set(0, 0, 0.024); clip.add(pad);
  function showClip() { var s = st.clip ? 0.0068 : 0.013; jawA.position.x = -s; jawB.position.x = s; jawA.rotation.y = st.clip ? 0 : 0.18; jawB.rotation.y = st.clip ? 0 : -0.18; }
  showClip();
  var room = S.label('Room 27 °C · keep the barrel out of the sun', { w: 0.13, ratio: 0.09, color: '#3c3c3c', bg: '#f3efe2' }); room.rotation.x = -Math.PI / 2 + 0.25; room.position.set(GX, 0.047, GZ + 0.04); S.scene.add(room);

  S.addApparatus('syr', syr, 'Glass syringe', 'Holds a fixed mass of air. Printed scale in mL: 1 cm of plunger travel = 10 mL.');
  S.addApparatus('plunger', plunger, 'Plunger', 'Push it down to squeeze the air, pull it up to let it expand.');
  S.addApparatus('gauge', gauge, 'Bourdon pressure gauge', 'Reads the absolute pressure of the trapped air, 0–600 kPa. Estimate to 1 kPa.');
  S.addApparatus('tube', rtube, 'Thick rubber tubing', 'Joins the syringe to the gauge. Its small volume is part of the trapped air.');
  S.addApparatus('clip', clip, 'Pinch clip', 'Closing it traps the air: from then on the mass of gas is fixed.');
  S.addApparatus('stand', stand, 'Clamp stand', 'Holds the syringe upright and steady.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudV = S.hudCard('Volume V'), hudP = S.hudCard('Pressure P'), hudN = S.hudCard('Readings');

  // ---------- actions
  function pistonY(V) { return YB + V * 1e-6 / AREA; }
  function setV(V) { st.V = V; plunger.position.y = pistonY(V); }
  setV(st.V);
  function closeClip() {
    if (S.hand.busy) return Promise.resolve();
    return S.hand.tap(pad, 'tap').then(function () { st.clip = !st.clip; showClip(); S.click(900, 0.05);
      S.say(st.clip ? 'Pinch clip closed: ' + st.V + ' mL of air is trapped.' : 'Clip opened: the air can leave now.'); S.render(); });
  }
  function movePlunger(target) {
    if (S.hand.busy) return Promise.resolve();
    target = Math.round(target);
    if (!(target >= VMIN && target <= VMAX)) { S.say('Keep the volume between ' + VMIN + ' and ' + VMAX + ' mL: below that the gauge goes off scale.'); return Promise.resolve(); }
    if (!st.clip) { S.say('Close the pinch clip first, or the air simply escapes through the tube.'); return Promise.resolve(); }
    var V0 = st.V; if (V0 === target) { S.say('The plunger is already at ' + target + ' mL.'); return Promise.resolve(); }
    var pt = function (k) { return new T.Vector3(SX, pistonY(V0 + (target - V0) * k) + 0.262, SZ); };
    return S.hand.pinchMove(pt(0), pt, function (k) { setV(V0 + (target - V0) * k); }, { mode: 'top', ms: 600 + Math.abs(target - V0) * 12, pose: 'pinch' })
      .then(function () { setV(target); S.say((target < V0 ? 'Pushed in' : 'Pulled out') + ' to ' + target + ' mL. Wait for the needle to settle, then read P.'); S.render(); });
  }
  function record() {
    if (!st.clip) { S.say('Close the pinch clip first.'); return; }
    if (S.hand.busy) { S.say('Let go of the plunger first.'); return; }
    if (S.rows.some(function (r) { return r.V_mL === st.V; })) { S.say('You already have a reading at ' + st.V + ' mL. Move the plunger to a new volume.'); return; }
    var P = readP(); S.addRow({ V_mL: st.V, P_kPa: P, V: st.V * 1e-6, P: P * 1000 });
    S.say('Written: V = ' + st.V + ' mL, P = ' + P + ' kPa, PV = ' + (P * st.V / 1000).toFixed(2) + ' J.');
  }
  function slope(rows) { return S.fit.origin(rows.map(function (r) { return [1000 / r.V_mL, r.P_kPa]; })); }

  return {
    camera: { pos: [0.42, 0.52, 1.1], look: [0.04, 0.22, -0.1] },
    views: { syr: [[0.12, 0.36, 0.42], [SX, 0.27, SZ]], plunger: [[0.12, 0.5, 0.45], [SX, 0.4, SZ]], gauge: [[0.24, 0.17, 0.2], [GX, GY, GZ]],
      tube: [[0.2, 0.2, 0.45], [0.06, 0.06, SZ]], clip: [[0.04, 0.12, 0.2], [SX, YB - 0.08, SZ]], stand: [[0.4, 0.5, 0.7], [SX, 0.3, -0.2]],
      work: [[0.22, 0.38, 0.62], [0.07, 0.24, SZ]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'For a fixed mass of gas at constant temperature, the pressure is inversely proportional to the volume. Squeeze the air into half the room and its molecules hit the walls twice as often.',
      formula: 'P V = constant  (= nRT)', formulaNote: 'so P against 1/V is a straight line through the origin; its slope is PV',
      more: ['A graph of P against V is a rectangular hyperbola. In kPa and litres, the product P × V comes out directly in joules (1 kPa · L = 1 J).'],
      precautions: 'Close the pinch clip before you move the plunger, so no air leaks. Move the plunger slowly and wait a few seconds: a quick squeeze warms the air. Read the gauge with your eye square to the dial. Do not take the volume below 20 mL.' },
    book: { title: 'Expt. — Boyle\'s Law', lines: ['Aim: to verify PV = constant at constant T.', 'Air in a glass syringe, room 27 °C', 'Gauge: absolute pressure, kPa', 'P ∝ 1/V  →  PV = nRT', '1 kPa × 1 L = 1 J'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'V (mL)', get: function (r) { return String(r.V_mL); } },
        { label: 'P (kPa)', get: function (r) { return String(r.P_kPa); } }, { label: '1/V (L⁻¹)', get: function (r) { return (1000 / r.V_mL).toFixed(2); } },
        { label: 'PV (J)', get: function (r) { return (r.P_kPa * r.V_mL / 1000).toFixed(2); } }] },
    graph: { x: function (r) { return 1000 / r.V_mL; }, y: function (r) { return r.P_kPa; }, xlabel: '1/V (L⁻¹)', ylabel: 'P (kPa)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) { if (rows.length < 3) return null; return { label: 'PV', value: slope(rows), unit: 'J', digits: 2, truth: p.n * p.R * p.Temp, note: 'From the slope of P against 1/V.' }; },
    tol: 0.02,
    chips: ['Why close the pinch clip?', 'Why plot P against 1/V?', 'Why move the plunger slowly?', 'Check my readings', 'What would change at a higher temperature?'],
    viva: [['Why must the plunger be moved slowly?', ['A fast squeeze warms the air, and Boyle\'s law needs constant temperature', 'The gauge would break', 'Air would leak'], 0, 'Squeezing does work on the gas; give it time to return to room temperature.'],
      ['What does the slope of P against 1/V give?', ['PV, which equals nRT', 'The temperature', 'The volume of the tube'], 0, 'P = (nRT)·(1/V): a line through the origin with slope nRT.']],
    askState: function () { return { volume_mL: st.V, gauge_kPa: readP(), pinch_clip_closed: st.clip, temperature_K: p.Temp, readings_taken: S.rows.length }; },

    steps: [
      { id: 'trap', title: 'Trap the air', view: 'clip', render: function (u) {
          u.h2('Trap a fixed mass of air');
          u.p('The plunger stands at ' + st.V + ' mL and the gauge reads the room pressure. Close the pinch clip on the rubber tube so no air can get in or out.');
          u.task('Close the pinch clip', st.clip, st.clip ? 'Closed: the air is trapped' : 'Open: air can escape')
            .add(u.button(st.clip ? 'Closed' : 'Close the pinch clip', function () { closeClip(); }, !st.clip, st.clip || S.hand.busy));
          u.live(function () { return 'V = ' + st.V + ' mL · P = ' + readP() + ' kPa'; });
          u.next('Next: change the volume', st.clip);
        },
        ok: function () { return st.clip; },
        auto: function () { return st.clip ? Promise.resolve() : closeClip(); } },
      { id: 'readings', title: 'Readings', view: 'work', render: function (u) {
          u.h2('Change V, read P');
          u.p('Choose a volume, let the hand move the plunger, wait for the needle to settle, then record P and V. Take at least 5 readings from 40 to 200 mL.');
          u.slider('Volume to set', VMIN, VMAX, 5, function () { return st.target; }, function (v) { st.target = v; }, 'mL', 0);
          u.row(u.button(S.hand.busy ? 'Moving…' : 'Move the plunger', function () { movePlunger(st.target); S.render(); }, true, S.hand.busy || !st.clip),
            u.button('Record P and V', function () { record(); }, false, S.hand.busy));
          u.live(function () { return 'Barrel: V = ' + Math.round(st.V) + ' mL · gauge: P = ' + Math.round(st.shownP) + ' kPa'; });
          u.h3('Observation table'); u.table();
          var vs = S.rows.map(function (r) { return r.V_mL; }), wide = vs.length && Math.max.apply(null, vs) >= 2 * Math.min.apply(null, vs);
          u.next('Next: plot P against 1/V', S.rows.length >= 5 && wide);
          if (S.rows.length < 5 || !wide) u.p(S.rows.length + ' readings so far. Take at least 5, with the largest volume at least twice the smallest.');
        },
        ok: function () { var vs = S.rows.map(function (r) { return r.V_mL; }); return S.rows.length >= 5 && Math.max.apply(null, vs) >= 2 * Math.min.apply(null, vs); },
        auto: function () {
          return [100, 80, 60, 50, 40, 140, 200].reduce(function (pr, v) { return pr.then(function () {
            return (st.V === v ? Promise.resolve() : movePlunger(v)).then(function () { S.advance(1); record(); }); }); }, Promise.resolve()); } },
    ],

    tick: function (dt) {
      var P = view().P_kPa; st.shownP += (P - st.shownP) * Math.min(1, dt * 5);
      needle.rotation.z = needleAngle(st.shownP);
      hudV.set(Math.round(st.V) + ' mL'); hudP.set(Math.round(st.shownP) + ' kPa'); hudN.set(String(S.rows.length));
    },
  };
});
