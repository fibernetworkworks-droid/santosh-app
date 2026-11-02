/* Prayogshala studio module: Faraday's law - a bar magnet pushed into a coil and pulled out (NCERT Class XII).
   Physics: the induction kernel from kernels.js (flat coil of N turns, radius a; dipole magnet of moment m on the axis)
   with the lab's params - the same emf the server checks. The magnet's axial position IS the kernel's z. */
HoolaStudio.define('electromagnetic-induction', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KI = HK.K.induction;
  var p = HK.paramsFor('induction', S.lab.params);
  var MU0 = 4e-7 * Math.PI;
  // the textbook peak (induct_peak): the emf is largest where the magnet is a/2 from the coil's plane
  var SLOPE_TRUE = p.N * 3 * MU0 * p.m * p.a * p.a * (p.a / 2) / (2 * Math.pow(p.a * p.a + p.a * p.a / 4, 2.5));
  var Z_OUT = -0.14, DZ = 0.0002;   // the magnet's start (14 cm from the coil's centre, inside the kernel's z0) and the sub-step
  var sim = KI.init(p); sim.z = Z_OUT; p.v = 0;
  var st = { speed: 0.5, fresh: false, recorded: false, last: null };
  var mot = null, emf = 0, dmm = { max: 0, min: 0 };
  function round(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function arr(v) { return [v.x, v.y, v.z]; }
  function wpos(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function rod(a, b, r, mat) { var d = b.clone().sub(a), m = S.mesh(new T.CylinderGeometry(r, r, d.length(), 8), mat); m.position.copy(a).add(b).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize()); S.scene.add(m); return m; }

  // ================================================================ coil: 200 turns of enamelled copper on a plastic former, axis along x
  var CX = 0.0, CZ = -0.12, AY = 0.047, BT = 0.014;
  var baseM = M.wood;
  var cbase = S.rounded(0.08, 0.1, BT, 0.005, baseM); cbase.rotation.x = -Math.PI / 2; cbase.position.set(CX, BT / 2, CZ); S.scene.add(cbase);
  var bl = new T.Mesh(new T.PlaneGeometry(0.07, 0.022), new T.MeshStandardMaterial({ map: S.canvasTex(512, 160, function (x, w, h) { x.fillStyle = '#efe6cf'; x.fillRect(0, 0, w, h);
    x.strokeStyle = '#7d6f55'; x.lineWidth = 4; x.strokeRect(4, 4, w - 8, h - 8); x.fillStyle = '#3d3528'; x.textAlign = 'center'; x.font = '700 46px "Public Sans", sans-serif'; x.fillText('COIL  ·  N = ' + Math.round(p.N) + ' turns', w / 2, 66);
    x.font = '600 34px "Public Sans", sans-serif'; x.fillText('radius 2.0 cm  ·  enamelled Cu', w / 2, 122); }), roughness: 0.7 }));
  bl.rotation.x = -Math.PI / 2; bl.position.set(CX, BT + 0.0004, CZ + 0.034); S.scene.add(bl);
  S.contact(0.13, 0.15, CX, CZ, 0.5);
  var coil = new T.Group(); S.scene.add(coil); coil.position.set(CX, AY, CZ);
  var formerM = new T.MeshStandardMaterial({ color: 0xf1e7cc, roughness: 0.45, side: T.DoubleSide });
  var tube = S.mesh(new T.CylinderGeometry(0.0152, 0.0152, 0.03, 40, 1, true), formerM); tube.rotation.z = Math.PI / 2; coil.add(tube);
  var bore = S.mesh(new T.CylinderGeometry(0.0136, 0.0136, 0.03, 40, 1, true), formerM); bore.rotation.z = Math.PI / 2; coil.add(bore);
  [-1, 1].forEach(function (s) { var fl = S.mesh(new T.RingGeometry(0.0136, 0.031, 48), formerM); fl.rotation.y = Math.PI / 2; fl.position.x = s * 0.0125; coil.add(fl);
    var fl2 = S.mesh(new T.RingGeometry(0.0136, 0.031, 48), formerM); fl2.rotation.y = Math.PI / 2; fl2.position.x = s * 0.0155; coil.add(fl2);
    var rimF = S.mesh(new T.CylinderGeometry(0.031, 0.031, 0.003, 48, 1, true), formerM); rimF.rotation.z = Math.PI / 2; rimF.position.x = s * 0.014; coil.add(rimF);
    var ends = S.mesh(new T.CylinderGeometry(0.0152, 0.0152, 0.0001, 4), formerM); ends.visible = false; coil.add(ends); });
  var windTex = S.canvasTex(512, 256, function (x, w, h) { x.fillStyle = '#b8642f'; x.fillRect(0, 0, w, h); for (var i = 0; i < h; i += 4) { x.fillStyle = i % 8 ? 'rgba(255,200,150,.22)' : 'rgba(60,20,0,.28)'; x.fillRect(0, i, w, 2); } });
  windTex.wrapS = windTex.wrapT = T.RepeatWrapping; windTex.repeat.set(1, 6);
  var windM = new T.MeshStandardMaterial({ map: windTex, color: 0xffffff, roughness: 0.28, metalness: 0.85 });
  var wind = S.mesh(new T.CylinderGeometry(0.0238, 0.0238, 0.0216, 64, 1, true), windM); wind.rotation.z = Math.PI / 2; coil.add(wind);
  [-1, 1].forEach(function (s) { var side = S.mesh(new T.RingGeometry(0.0152, 0.0238, 48), windM); side.rotation.y = Math.PI / 2; side.position.x = s * 0.0108; coil.add(side); });
  // outer layer of turns as a real helix of enamelled wire
  var helix = new T.Curve(); helix.getPoint = function (t, tgt) { var turns = 14, a = t * turns * Math.PI * 2; return (tgt || new T.Vector3()).set(-0.0102 + 0.0204 * t, Math.cos(a) * 0.0246, Math.sin(a) * 0.0246); };
  coil.add(S.mesh(new T.TubeGeometry(helix, 14 * 24, 0.00074, 6, false), new T.MeshStandardMaterial({ color: 0xc8703a, roughness: 0.22, metalness: 0.9 })));
  // two terminals at the back of the base, with the winding's ends brought down to them
  var termA = S.terminal([CX - 0.022, BT, CZ - 0.032], 'black'), termB = S.terminal([CX + 0.022, BT, CZ - 0.032], 'red');
  var cu = new T.MeshStandardMaterial({ color: 0xc8703a, roughness: 0.25, metalness: 0.9 });
  [-1, 1].forEach(function (s) { var top = new T.Vector3(CX + s * 0.0102, AY + 0.0246, CZ), mid = new T.Vector3(CX + s * 0.0102, AY + 0.021, CZ - 0.0255);
    rod(top, mid, 0.0006, cu); rod(mid, new T.Vector3(CX + s * 0.022, BT + 0.008, CZ - 0.032), 0.0006, cu); });
  // the former sits in a wooden cradle on the base
  var cradle = S.rounded(0.036, 0.044, 0.008, 0.002, M.darkWood); cradle.rotation.x = -Math.PI / 2; cradle.position.set(CX, BT + 0.004, CZ); S.scene.add(cradle);

  // ================================================================ guide: a wooden strip through the bore, on two posts; the magnet slides on it
  var MAGL = 0.05, MAGW = 0.012, GY = AY - MAGW / 2;   // the magnet's centre runs on the coil's axis
  var strip = S.mesh(new T.BoxGeometry(0.32, 0.003, 0.016), M.wood); strip.position.set(CX + 0.05, GY - 0.0015, CZ); S.scene.add(strip);
  [[CX - 0.095], [CX + 0.195]].forEach(function (q) { var post = S.rounded(0.02, 0.022, GY - 0.003, 0.003, M.darkWood); post.rotation.x = -Math.PI / 2; post.position.set(q[0], (GY - 0.003) / 2, CZ); S.scene.add(post);
    S.contact(0.05, 0.05, q[0], CZ, 0.45); });
  [-1, 1].forEach(function (s) { var lip = S.mesh(new T.BoxGeometry(0.1, 0.004, 0.0015), M.wood); lip.position.set(CX + 0.15, GY + 0.0005, CZ + s * 0.0075); S.scene.add(lip); });

  // ================================================================ bar magnet: red N half, blue S half, stamped letters
  var mag = new T.Group(); S.scene.add(mag); mag.rotation.z = -Math.PI / 2;   // local +y (S end) -> +x: the N pole faces the coil
  var redM = new T.MeshStandardMaterial({ color: 0xc8312a, roughness: 0.35, metalness: 0.2 }), blueM = new T.MeshStandardMaterial({ color: 0x2457b5, roughness: 0.35, metalness: 0.2 });
  var hN = S.rounded(MAGW, MAGL / 2, MAGW, 0.0015, redM); hN.position.y = -MAGL / 4; mag.add(hN);
  var hS = S.rounded(MAGW, MAGL / 2, MAGW, 0.0015, blueM); hS.position.y = MAGL / 4; mag.add(hS);
  function letter(t, y) { [[0, 0, MAGW / 2 + 0.0003, 0], [0, 0, -MAGW / 2 - 0.0003, Math.PI], [-MAGW / 2 - 0.0003, 0, 0, -Math.PI / 2]].forEach(function (f) {
    var l = S.label(t, { w: 0.009, ratio: 1, color: '#ffffff', weight: 800 }); l.position.set(f[0], y, f[2]); l.rotation.set(0, f[3], Math.PI / 2); mag.add(l); }); }
  letter('N', -MAGL / 2 + 0.007); letter('S', MAGL / 2 - 0.007);
  var magShadow = S.contact(0.07, 0.03, 0, CZ, 0.3, GY - 0.0012);
  function magX(z) { return CX - z; }
  function placeMag() { mag.position.set(magX(sim.z), AY, CZ); magShadow.position.x = mag.position.x; }
  placeMag();
  function grip() { return wpos(mag, 0, MAGL / 2 - 0.008, 0).add(new T.Vector3(0, MAGW / 2, 0)); }

  // ================================================================ zero-centre galvanometer + digital multimeter (MAX/MIN) across the coil
  var gal = S.meter({ min: -30, max: 30, ticks: 6, zeroCentre: true, unit: 'div', symbol: 'G', caption: 'GALVANOMETER  30–0–30  ·  10 mV / div', pos: [-0.25, 0, -0.33], rotY: 0.3 });
  var DMX = 0.3, DMZ = -0.31;
  var dm = new T.Group(); S.scene.add(dm); dm.position.set(DMX, 0, DMZ); dm.rotation.y = -0.28;
  var face = new T.Group(); face.rotation.x = -Math.PI / 2; face.position.y = 0.016; dm.add(face);   // face frame: x right, y up the face, z out (= world up)
  var holster = S.rounded(0.082, 0.15, 0.03, 0.012, new T.MeshStandardMaterial({ color: 0xf0b928, roughness: 0.75 })); face.add(holster);
  var dTex = S.canvasTex(560, 1000, function (x, w, h) { x.fillStyle = '#2b2e34'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#f2f2f2'; x.textAlign = 'center'; x.font = '700 40px "Public Sans", sans-serif'; x.fillText('DIGITAL MULTIMETER', w / 2, 60);
    x.fillStyle = '#1b1d21'; x.fillRect(40, 90, w - 80, 250);
    x.font = '700 30px "Public Sans", sans-serif'; x.fillStyle = '#f0b928'; x.fillText('MAX / MIN', w * 0.3, 410); x.fillStyle = '#f2f2f2'; x.fillText('HOLD', w * 0.7, 410);
    var cx = w / 2, cy = 640; x.strokeStyle = '#8b9099'; x.lineWidth = 4; x.beginPath(); x.arc(cx, cy, 150, 0, Math.PI * 2); x.stroke();
    [['OFF', -90], ['V⎓', -40], ['mV⎓', 0], ['V~', 40], ['Ω', 80], ['A⎓', 140], ['µA', 190]].forEach(function (k) { var a = (k[1] - 90) * Math.PI / 180;
      x.fillStyle = k[0] === 'mV⎓' ? '#f0b928' : '#f2f2f2'; x.font = '700 30px "Public Sans", sans-serif'; x.fillText(k[0], cx + Math.cos(a) * 196, cy + Math.sin(a) * 196 + 10); });
    x.font = '700 30px "Public Sans", sans-serif'; x.fillStyle = '#f2f2f2'; x.fillText('COM', w * 0.36, 930); x.fillStyle = '#ff7a6b'; x.fillText('VΩmA', w * 0.64, 930); });
  var dface = new T.Mesh(new T.PlaneGeometry(0.068, 0.124), new T.MeshStandardMaterial({ map: dTex, roughness: 0.5 })); dface.position.z = 0.0152; face.add(dface);
  var lcd = S.liveTex(512, 224);
  var lcdM = new T.Mesh(new T.PlaneGeometry(0.052, 0.0228), new T.MeshBasicMaterial({ map: lcd, toneMapped: false })); lcdM.position.set(0, 0.0473, 0.0156); face.add(lcdM);
  var lastLcd = '';
  function drawLcd() { var a = round(emf * 1000, 1), txt = (a < 0 ? '−' : ' ') + Math.abs(a).toFixed(1) + '|' + dmm.max + '|' + dmm.min; if (txt === lastLcd) return; lastLcd = txt;
    lcd.draw(function (x, w, h) { var g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#b9c4a7'); g.addColorStop(1, '#9eab8b'); x.fillStyle = g; x.fillRect(0, 0, w, h);
      x.fillStyle = '#1b2116'; x.font = '600 24px "Public Sans", sans-serif'; x.textAlign = 'left'; x.fillText('DC   mV', 18, 34); x.textAlign = 'right'; x.fillText('MAX/MIN', w - 18, 34);
      x.font = '700 92px "JetBrains Mono", monospace'; x.fillText((a < 0 ? '−' : '') + Math.abs(a).toFixed(1), w - 24, 128);
      x.font = '600 34px "JetBrains Mono", monospace'; x.textAlign = 'left'; x.fillText('MAX ' + (dmm.max >= 0 ? '+' : '') + dmm.max.toFixed(1), 18, 198);
      x.textAlign = 'right'; x.fillText('MIN ' + (dmm.min < 0 ? '−' : '+') + Math.abs(dmm.min).toFixed(1), w - 18, 198); }); }
  function btn(xx, mat) { var b = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.003, 24), mat); b.rotation.x = Math.PI / 2; b.position.set(xx, 0.015, 0.0165); face.add(b); return b; }
  var mmBtn = btn(-0.0136, new T.MeshStandardMaterial({ color: 0xf0b928, roughness: 0.5 })); btn(0.0136, M.grey);
  var sel = S.mesh(new T.CylinderGeometry(0.017, 0.018, 0.006, 40), M.blackPlastic); sel.rotation.x = Math.PI / 2; sel.position.set(0, -0.0195, 0.018); face.add(sel);
  var selP = S.mesh(new T.BoxGeometry(0.004, 0.026, 0.004), M.grey); selP.position.set(0, -0.0195, 0.022); face.add(selP);
  function jack(xx, mat) { var j = S.mesh(new T.CylinderGeometry(0.0042, 0.0042, 0.004, 20), mat); j.rotation.x = Math.PI / 2; j.position.set(xx, -0.0555, 0.0165); face.add(j);
    var plug = S.mesh(new T.CylinderGeometry(0.003, 0.0034, 0.016, 16), mat); plug.rotation.x = Math.PI / 2; plug.position.set(xx, -0.0555, 0.026); face.add(plug); return plug; }
  var jCom = jack(-0.0095, M.blackPlastic), jV = jack(0.0095, M.red);
  S.contact(0.13, 0.2, DMX, DMZ, 0.5);
  drawLcd();

  // ================================================================ wires: coil terminals to the galvanometer and the multimeter
  function tt(t, dy) { return new T.Vector3(t.position.x, t.position.y + 0.008 + (dy || 0), t.position.z); }
  function mt(m, which) { var w = new T.Vector3(); m.updateMatrixWorld(true); m.userData[which].getWorldPosition(w); w.y += 0.004; return w; }
  function jt(j) { var w = new T.Vector3(); dm.updateMatrixWorld(true); j.getWorldPosition(w); w.y += 0.008; return w; }
  var a1 = tt(termA), b1 = tt(termB), gP = mt(gal, 'plus'), gN = mt(gal, 'minus'), dC = jt(jCom), dV = jt(jV);
  S.wire([arr(a1), [a1.x - 0.01, 0.03, a1.z - 0.03], [gN.x + 0.03, 0.02, gN.z + 0.07], arr(gN)], 'black');
  S.wire([arr(tt(termB, 0.002)), [b1.x - 0.004, 0.03, b1.z - 0.04], [gP.x + 0.05, 0.02, gP.z + 0.05], arr(gP)], 'red');
  S.wire([arr(tt(termA, 0.002)), [a1.x + 0.005, 0.03, a1.z - 0.05], [dC.x - 0.05, 0.01, dC.z + 0.0], [dC.x - 0.01, 0.04, dC.z + 0.01], arr(dC)], 'black');
  S.wire([arr(tt(termB, 0.004)), [b1.x + 0.01, 0.03, b1.z - 0.03], [dV.x - 0.04, 0.01, dV.z + 0.03], [dV.x - 0.006, 0.045, dV.z + 0.01], arr(dV)], 'red');

  S.addApparatus('coil', coil, 'Coil (' + Math.round(p.N) + ' turns)', 'Enamelled copper wound on a plastic former, radius 2 cm. An emf appears across it whenever the flux through it changes.');
  S.addApparatus('mag', mag, 'Bar magnet', 'Red end = N pole, blue end = S pole. It slides along the guide through the coil.');
  S.addApparatus('guide', strip, 'Wooden guide', 'Keeps the magnet on the coil’s axis while it is pushed in and pulled out.');
  S.addApparatus('gal', gal, 'Zero-centre galvanometer', 'The needle swings one way as the magnet enters and the other way as it leaves (Lenz’s law). 10 mV per division.');
  S.addApparatus('dmm', dm, 'Digital multimeter (MAX/MIN)', 'On DC mV. MAX/MIN holds the largest + and − emf of the pass. Press it to clear before each pass.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudV = S.hudCard('Magnet speed'), hudE = S.hudCard('Emf now'), hudP = S.hudCard('Peaks (MIN / MAX)');

  // ================================================================ the motion (constant speed in, a short hold, constant speed out) - kernel z and v
  function motion(dt) {
    var t = dt, guard = 0;
    while (mot && mot.phase !== 'done' && t > 1e-12 && guard++ < 100000) {
      if (mot.phase === 'hold') { var hh = Math.min(t, mot.hold); mot.hold -= hh; t -= hh; p.v = 0; emf = 0; if (mot.hold <= 1e-12) mot.phase = 'out'; continue; }
      var inward = mot.phase === 'in', target = inward ? 0 : Z_OUT, sp = mot.v, rem = Math.abs(target - sim.z);
      if (rem < 1e-10) { sim.z = target; mot.phase = inward ? 'hold' : 'done'; p.v = 0; emf = 0; continue; }
      var h = Math.min(t, rem / sp, DZ / sp);
      p.v = inward ? sp : -sp; KI.step(sim, p, h);
      emf = KI.view(sim, p).emf; t -= h;
      var mv = emf * 1000; if (mv > dmm.max) dmm.max = mv; if (mv < dmm.min) dmm.min = mv;
    }
    if (mot && mot.phase === 'done') { sim.z = Z_OUT; p.v = 0; emf = 0; dmm.max = round(dmm.max, 1); dmm.min = round(dmm.min, 1); var m = mot; mot = null; st.fresh = true; st.recorded = false; if (m.done) m.done(); }
  }
  function clearDmm() { return S.hand.tap(mmBtn).then(function () { dmm.max = 0; dmm.min = 0; S.click(2600, 0.02); }); }
  function pass(v) {
    if (S.hand.busy || mot) { S.say('Wait for the hand to finish this pass.'); return Promise.resolve(); }
    if (!(v >= 0.2 - 1e-9 && v <= 1.0 + 1e-9)) { S.say('Choose a speed from 0.2 to 1.0 m/s: a hand cannot push steadily outside that.'); return Promise.resolve(); }
    v = round(v, 1); st.speed = v; st.fresh = false;
    return clearDmm().then(function () {
      S.hand.busy = true;
      var done = new Promise(function (res) { mot = { phase: 'in', v: v, hold: 0.45, done: res }; });
      var hold = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(grip().add(new T.Vector3(0, 0.03, 0)), 'top', 600); })
        .then(function () { return S.hand.reach(grip(), 'top', 220); }).then(function () { return S.hand.shape('pinch', 220); });
      if (S.fast) { return hold.then(function () { S.advance(5, function () { return !mot; }); return done; }).then(finish); }
      // in the live lab the push starts once the fingers hold the magnet; the hand rides along with it
      var paused = mot; mot = null;
      return hold.then(function () { mot = paused; var chase = function () { return mot ? S.hand.follow(grip, 'top', 160).then(chase) : Promise.resolve(); }; return Promise.all([done, chase()]); })
        .then(function () { return S.hand.follow(grip, 'top', 120); }).then(finish);
    });
    function finish() { return S.hand.shape('relaxed', 200).then(function () { return S.hand.away(450); }).then(function () { S.hand.busy = false;
      S.say('Pass done at ' + v.toFixed(1) + ' m/s: the multimeter holds MIN ' + dmm.min.toFixed(1) + ' mV (going in) and MAX +' + dmm.max.toFixed(1) + ' mV (coming out).'); S.render(); }); }
  }
  function record() {
    if (S.hand.busy || mot) { S.say('Wait for the pass to finish.'); return; }
    if (!st.fresh) { S.say('Push the magnet in and pull it out first: the meter has no fresh peaks.'); return; }
    if (st.recorded) { S.say('This pass is already written down. Do a new pass.'); return; }
    var pin = dmm.min, pout = dmm.max;
    S.addRow({ v: st.speed, ein: pin, eout: pout, e: (Math.abs(pin) + Math.abs(pout)) / 2 });
    st.recorded = true;
    S.say('Written in your record book: v = ' + st.speed.toFixed(1) + ' m/s, peaks ' + pin.toFixed(1) + ' / +' + pout.toFixed(1) + ' mV.');
  }
  function speeds() { var s = {}; S.rows.forEach(function (r) { s[r.v.toFixed(1)] = 1; }); return Object.keys(s).length; }

  return {
    camera: { pos: [0.12, 0.5, 0.78], look: [0.03, 0.03, -0.2] },
    views: { coil: [[0.08, 0.12, 0.06], [0.0, 0.04, -0.12]], mag: [[0.2, 0.12, 0.04], [0.14, 0.04, -0.12]], guide: [[0.1, 0.16, 0.12], [0.05, 0.04, -0.12]],
      gal: [[-0.2, 0.22, -0.06], [-0.25, 0.05, -0.32]], dmm: [[0.33, 0.24, -0.18], [0.3, 0.01, -0.31]], run: [[0.1, 0.3, 0.32], [0.06, 0.04, -0.18]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'When the magnetic flux through a coil changes, an emf is induced in it. Pushing the magnet in increases the flux; pulling it out decreases it, so the emf reverses (Lenz’s law). A faster magnet changes the flux faster.',
      formula: 'e = −N dΦ/dt', formulaNote: 'for a magnet moving at speed v the peak emf is proportional to v: e_peak = k v',
      more: ['The emf lasts only a fraction of a second, too quick to read off a swinging needle. So the multimeter on MAX/MIN holds the largest emf going in (−) and coming out (+). Plot the peak emf against v: a straight line through the origin; its slope is k.'],
      precautions: 'Push the magnet steadily along the guide, keeping it on the coil’s axis. Clear MAX/MIN before every pass. Keep the magnet away from the meters.' },
    book: { title: 'Expt. — Electromagnetic induction (Faraday)', lines: ['Aim: peak emf in a coil against the speed of a magnet.', 'Coil: N = ' + Math.round(p.N) + ' turns, radius 2.0 cm', 'Peaks held by the multimeter (MAX/MIN, DC mV)', 'In: emf −ve;  Out: emf +ve  (Lenz)', 'e_peak = k v   →   k = slope of e against v'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'v (m/s)', get: function (r) { return r.v.toFixed(1); } },
        { label: 'In (mV)', get: function (r) { return r.ein.toFixed(1); } }, { label: 'Out (mV)', get: function (r) { return '+' + r.eout.toFixed(1); } }, { label: 'e (mV)', get: function (r) { return r.e.toFixed(1); } }] },
    graph: { x: function (r) { return r.v; }, y: function (r) { return r.e; }, xlabel: 'v (m/s)', ylabel: 'peak emf (mV)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) { if (rows.length < 2) return null; var k = S.fit.origin(rows.map(function (r) { return [r.v, r.e / 1000]; }));
      return { label: 'k = e_peak / v', value: k, unit: 'V·s/m', digits: 4, truth: SLOPE_TRUE, note: 'From the slope of peak emf against speed.' }; },
    tol: 0.02,
    resultNote: 'The two peaks have opposite signs: entering, the flux grows; leaving, it falls. Both grow in proportion to the speed.',
    chips: ['Why does the needle swing both ways?', 'What is Lenz’s law?', 'Why use MAX/MIN?', 'Check my readings', 'What if the coil had more turns?'],
    viva: [['The magnet is pushed in twice as fast. The peak emf is?', ['Doubled', 'Halved', 'The same'], 0, 'The flux changes twice as fast, so dΦ/dt doubles.'],
      ['Why is the emf negative going in and positive coming out?', ['The flux increases and then decreases (Lenz)', 'The magnet turns round', 'The meter reverses'], 0, 'The induced emf opposes the change in flux, and the change reverses.']],
    askState: function () { return { magnet_speed_m_per_s: st.speed, magnet_distance_from_coil_centre_cm: +(-sim.z * 100).toFixed(1), moving: !!mot, emf_now_mV: round(emf * 1000, 1),
      dmm_max_mV: dmm.max, dmm_min_mV: dmm.min, coil_turns: Math.round(p.N), passes_recorded: S.rows.length }; },

    steps: [
      { id: 'look', title: 'See it happen', view: 'run', render: function (u) {
          u.h2('Push the magnet in and pull it out');
          u.p('Choose a speed. The hand clears MAX/MIN on the multimeter, holds the magnet, pushes it along the guide into the coil, stops for a moment, and pulls it back out. Watch the galvanometer swing one way, then the other.');
          u.slider('Speed of the magnet', 0.2, 1.0, 0.1, function () { return st.speed; }, function (v) { st.speed = round(v, 1); }, 'm/s', 1);
          u.row(u.button('Push in and pull out', function () { pass(st.speed); }, true, S.hand.busy || !!mot));
          u.live(function () { return 'emf ' + (emf * 1000).toFixed(1) + ' mV  ·  MIN ' + dmm.min.toFixed(1) + '  ·  MAX +' + dmm.max.toFixed(1) + ' mV'; });
          u.note('While the magnet is held still inside the coil the emf is zero: the flux is not changing.');
          u.next('Next: record peaks at several speeds', st.fresh);
        },
        ok: function () { return st.fresh; },
        auto: function () { return pass(0.5); } },
      { id: 'record', title: 'Record peaks', view: 'run', render: function (u) {
          u.h2('Peak emf at different speeds');
          u.p('For each speed: do one pass, then record the MIN (going in) and MAX (coming out) held by the multimeter. Use at least four speeds.');
          u.slider('Speed of the magnet', 0.2, 1.0, 0.1, function () { return st.speed; }, function (v) { st.speed = round(v, 1); }, 'm/s', 1);
          u.row(u.button('Push in and pull out', function () { pass(st.speed); }, true, S.hand.busy || !!mot),
            u.button('Record the peaks', function () { record(); }, false, S.hand.busy || !!mot || !st.fresh || st.recorded));
          u.live(function () { return 'MIN ' + dmm.min.toFixed(1) + ' mV  ·  MAX +' + dmm.max.toFixed(1) + ' mV'; });
          u.h3('Observation table'); u.table();
          if (speeds() < 4) u.p(speeds() + ' of at least 4 speeds recorded.');
          u.next('Next: plot emf against speed', speeds() >= 4);
        },
        ok: function () { return speeds() >= 4; },
        auto: function () { var vs = [0.2, 0.4, 0.6, 0.8, 1.0];
          return vs.reduce(function (pr, v) { return pr.then(function () { return pass(v).then(record); }); }, Promise.resolve()); } },
    ],

    tick: function (dt) {
      if (mot) motion(dt);
      placeMag();
      gal.set(emf * 1000 / 10); drawLcd();
      hudV.set(st.speed.toFixed(1) + ' m/s'); hudE.set((emf * 1000).toFixed(1) + ' mV'); hudP.set(dmm.min.toFixed(1) + ' / +' + dmm.max.toFixed(1));
    },
  };
});
