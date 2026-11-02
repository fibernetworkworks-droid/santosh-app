/* Prayogshala studio module: charging a capacitor through a resistor, τ = RC (NCERT Class XII).
   Physics: the circuit kernel from kernels.js (MNA, capacitor transient) on the lab's own net - the same numbers the
   server checks. The voltmeter reads V_C1; the stopwatch runs on the same simulated clock. */
HoolaStudio.define('rc-charging', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KC = HK.K.circuit;
  var cfg = S.lab.cfg, p = HK.paramsFor('circuit', S.lab.params);
  var E = 5.0, TARGET = 0.632 * E;
  var CAPS = [{ uF: 100, r: 0.0041, h: 0.0145 }, { uF: 220, r: 0.0052, h: 0.0152 }, { uF: 470, r: 0.0065, h: 0.0205 }];
  var st = { R: Math.round(p.Rr / 1000), boxR: 0, rTarget: Math.round(p.Rr / 1000), cap: -1, closed: false, discharged: false, capV: [0, 0, 0] };
  p.key = 0; p.Rr = 1000; p.Cc = 1e-4;
  var sim = KC.init(p, cfg), vc = 0;
  function refresh() { if (st.cap < 0) { vc = 0; return; } KC.step(sim, p, 1e-5, cfg); vc = KC.view(sim, p, cfg).V_C1; }   // re-read V_C after a change of state
  function round(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function readV() { return round(vc, 2); }
  function watchRead() { return Math.floor(watch.t * 100 + 1e-6) / 100; }   // what the LCD shows (it truncates)
  function wpos(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function arr(v) { return [v.x, v.y, v.z]; }
  function rod(a, b, r, mat, parent) { var d = b.clone().sub(a), m = S.mesh(new T.CylinderGeometry(r, r, d.length(), 8), mat); m.position.copy(a).add(b).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize()); (parent || S.scene).add(m); return m; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function seq(fn) { S.hand.busy = true; return fn().then(function () { return S.hand.away(380); }, function (e) { console.error(e); }).then(function () { S.hand.busy = false; S.render(); }); }

  // ================================================================ 5 V DC supply (regulated, front binding posts, lamp on)
  var PSW = 0.18, PSH = 0.09, PSD = 0.13, PW = PSW - 0.012, PH = PSH - 0.012, FZ = PSD / 2 + 0.006;
  var psu = new T.Group(); S.scene.add(psu); psu.position.set(-0.44, 0, -0.44); psu.rotation.y = 0.12;
  var cs = S.rounded(PSW, PSD, PSH, 0.01, new T.MeshStandardMaterial({ color: 0xd9d5cb, roughness: 0.5, metalness: 0.15 })); cs.rotation.x = -Math.PI / 2; cs.position.y = PSH / 2 + 0.004; psu.add(cs);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) { var ft = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.004, 16), M.rubber); ft.position.set(f[0] * (PSW / 2 - 0.018), 0.002, f[1] * (PSD / 2 - 0.018)); psu.add(ft); });
  var pTex = S.canvasTex(1000, Math.round(1000 * PH / PW), function (x, w, h) { var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; };
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.font = '700 46px "Public Sans", sans-serif'; x.fillText('DC POWER SUPPLY', 36, 72);
    x.font = '500 30px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText('REGULATED  5 V  ·  1 A', 36, 116);
    x.textAlign = 'center'; x.fillStyle = '#f1efe8'; x.font = '600 26px "Public Sans", sans-serif'; x.fillText('ON', X(-0.06), Y(0.0));
    x.font = '700 28px "Public Sans", sans-serif'; x.fillText('OUTPUT 5 V', X(0.045), Y(0.005));
    x.font = '700 44px "Public Sans", sans-serif'; x.fillStyle = '#9aa3b2'; x.fillText('−', X(0.025), Y(-0.033)); x.fillStyle = '#ff7a6b'; x.fillText('+', X(0.065), Y(-0.033)); });
  var fascia = S.mesh(new T.BoxGeometry(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: pTex, roughness: 0.45 }), M.grey]); fascia.position.set(0, 0.004 + PSH / 2, FZ - 0.002); psu.add(fascia);
  function pp(u, v, dz) { return new T.Vector3(u, 0.004 + PSH / 2 + v, FZ + (dz || 0)); }
  var lamp = S.mesh(new T.SphereGeometry(0.005, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2), new T.MeshStandardMaterial({ color: 0xff3b2a, emissive: 0xff2a14, emissiveIntensity: 2.2, roughness: 0.3 }));
  lamp.rotation.x = Math.PI / 2; lamp.position.copy(pp(-0.06, -0.015)); psu.add(lamp);
  function post(u, mat) { var g = new T.Group(); g.position.copy(pp(u, -0.014)); psu.add(g);
    var stem = S.mesh(new T.CylinderGeometry(0.0028, 0.0028, 0.02, 16), M.brass); stem.rotation.x = Math.PI / 2; stem.position.z = 0.01; g.add(stem);
    var cap = S.mesh(new T.CylinderGeometry(0.0072, 0.0082, 0.012, 24), mat); cap.rotation.x = Math.PI / 2; cap.position.z = 0.012; g.add(cap); return g; }
  post(0.025, M.blackPlastic); post(0.065, M.red);
  S.contact(0.27, 0.21, psu.position.x, psu.position.z, 0.55);

  // ================================================================ toggle switch (key K): bakelite base, chrome lever, screw terminals
  var SWX = -0.17, SWZ = -0.21;
  var sw = new T.Group(); sw.position.set(SWX, 0, SWZ); S.scene.add(sw);
  var swBase = S.rounded(0.07, 0.04, 0.014, 0.005, M.bakelite); swBase.rotation.x = -Math.PI / 2; swBase.position.y = 0.007; sw.add(swBase);
  var swPlate = new T.Mesh(new T.PlaneGeometry(0.03, 0.03), new T.MeshStandardMaterial({ map: S.canvasTex(256, 256, function (x, w, h) { x.fillStyle = '#c9ccd1'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#1b1b1b'; x.font = '700 50px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText('OFF', 62, 150); x.fillText('ON', 196, 150); x.font = '600 34px "Public Sans", sans-serif'; x.fillText('KEY  K', 128, 60); }), roughness: 0.4, metalness: 0.5 }));
  swPlate.rotation.x = -Math.PI / 2; swPlate.position.y = 0.0142; sw.add(swPlate);
  var bush = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.006, 6), M.chrome); bush.position.y = 0.017; sw.add(bush);
  var lever = new T.Group(); lever.position.y = 0.02; sw.add(lever);
  var LL = 0.022; var lv = S.mesh(new T.CylinderGeometry(0.0014, 0.0019, LL, 16), M.chrome); lv.position.y = LL / 2; lever.add(lv);
  var ball = S.mesh(new T.SphereGeometry(0.003, 16, 12), M.chrome); ball.position.y = LL + 0.002; lever.add(ball);
  var OFF_A = 0.42, ON_A = -0.42; lever.rotation.z = OFF_A;
  var swT = [S.terminal([SWX - 0.026, 0.014, SWZ], 'brass'), S.terminal([SWX + 0.026, 0.014, SWZ], 'brass')];
  S.contact(0.12, 0.08, SWX, SWZ, 0.5);
  function leverTip(a) { return wpos(sw, -Math.sin(a) * (LL + 0.002), 0.02 + Math.cos(a) * (LL + 0.002), 0); }

  // ================================================================ resistance box, values in kΩ (plugs pulled out = in circuit)
  var RBX = 0.07, RBZ = -0.38;
  var rbox = S.resistanceBox([RBX, 0, RBZ]);
  var plugs = rbox.children.filter(function (c) { return c.isGroup; }), PV = [1, 2, 2, 5, 10, 20, 20, 50];
  var rbl = S.label('RESISTANCE BOX  ·  kΩ', { w: 0.12, ratio: 0.14, color: '#f0e6c8', bg: '#3a2214' }); rbl.position.set(0, 0.026, 0.0435); rbox.add(rbl);
  var rbT = [S.terminal([RBX - 0.068, 0.053, RBZ - 0.024], 'brass'), S.terminal([RBX + 0.068, 0.053, RBZ - 0.024], 'brass')];
  var plugOut = PV.map(function () { return false; });
  function plugLook(i, f) { plugs[i].position.y = 0.058 + 0.017 * f; plugs[i].rotation.z = 0.5 * f; plugs[i].position.x = -0.063 + i * 0.018 + 0.004 * f; }
  function plan(value) { var left = Math.round(value), out = PV.map(function () { return false; }); for (var i = PV.length - 1; i >= 0; i--) if (PV[i] <= left) { out[i] = true; left -= PV[i]; } return out; }
  function boxValue() { var s = 0; plugOut.forEach(function (o, i) { if (o) s += PV[i]; }); return s; }

  // ================================================================ capacitor board: socket for the electrolytic, terminals, DISCHARGE button
  var CBX = 0.33, CBZ = -0.13, CBW = 0.17, CBD = 0.1, CBT = 0.012;
  var cb = S.rounded(CBW, CBD, CBT, 0.006, new T.MeshStandardMaterial({ color: 0xe9e2cf, roughness: 0.7 })); cb.rotation.x = -Math.PI / 2; cb.position.set(CBX, CBT / 2, CBZ); S.scene.add(cb);
  var cbTex = S.canvasTex(900, Math.round(900 * (CBD - 0.012) / (CBW - 0.012)), function (x, w, h) { var X = function (u) { return (u / (CBW - 0.012) + 0.5) * w; }, Y = function (zz) { return (zz / (CBD - 0.012) + 0.5) * h; };
    x.fillStyle = '#ece5d2'; x.fillRect(0, 0, w, h); x.strokeStyle = '#7d6f55'; x.lineWidth = 3; x.strokeRect(12, 12, w - 24, h - 24);
    x.fillStyle = '#3d3528'; x.textAlign = 'center'; x.font = '700 34px "Public Sans", sans-serif'; x.fillText('CAPACITOR  C', w / 2, 56);
    x.font = '700 40px "Public Sans", sans-serif'; x.fillText('+', X(-0.062), Y(0.03)); x.fillText('−', X(0.062), Y(0.03));
    x.font = '600 26px "Public Sans", sans-serif'; x.fillText('DISCHARGE (10 Ω)', X(0.0), Y(0.04));
    x.fillText('+', X(-0.009), Y(-0.012)); x.fillText('−', X(0.009), Y(-0.012)); });
  var cbp = new T.Mesh(new T.PlaneGeometry(CBW - 0.012, CBD - 0.012), new T.MeshStandardMaterial({ map: cbTex, roughness: 0.75 })); cbp.rotation.x = -Math.PI / 2; cbp.position.set(CBX, CBT + 0.0003, CBZ); S.scene.add(cbp);
  S.contact(CBW + 0.06, CBD + 0.06, CBX, CBZ, 0.5);
  var cbT = [S.terminal([CBX - 0.062, CBT, CBZ - 0.012], 'red'), S.terminal([CBX + 0.062, CBT, CBZ - 0.012], 'black')];
  var sock = S.rounded(0.022, 0.01, 0.007, 0.002, M.blackPlastic); sock.rotation.x = -Math.PI / 2; sock.position.set(CBX, CBT + 0.0035, CBZ - 0.012); S.scene.add(sock);
  var SOCK = new T.Vector3(CBX, CBT + 0.007, CBZ - 0.012);
  // push button across the socket (through a 10 Ω resistor printed on the board)
  var pbBase = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.006, 28), M.bakelite); pbBase.position.set(CBX, CBT + 0.003, CBZ + 0.022); S.scene.add(pbBase);
  var pbBtn = S.mesh(new T.CylinderGeometry(0.0062, 0.0066, 0.006, 28), new T.MeshStandardMaterial({ color: 0xd2382c, roughness: 0.35 })); pbBtn.position.set(CBX, CBT + 0.009, CBZ + 0.022); S.scene.add(pbBtn);
  // board copper links under the print, shown as thin tracks
  var trk = new T.MeshStandardMaterial({ color: 0xb87333, roughness: 0.35, metalness: 0.9 });
  [[[CBX - 0.062, CBZ - 0.012], [CBX - 0.0045, CBZ - 0.012]], [[CBX + 0.0045, CBZ - 0.012], [CBX + 0.062, CBZ - 0.012]],
    [[CBX - 0.03, CBZ - 0.012], [CBX - 0.03, CBZ + 0.022], [CBX - 0.007, CBZ + 0.022]], [[CBX + 0.03, CBZ - 0.012], [CBX + 0.03, CBZ + 0.022], [CBX + 0.007, CBZ + 0.022]]].forEach(function (path) {
    for (var i = 0; i < path.length - 1; i++) rod(new T.Vector3(path[i][0], CBT + 0.0006, path[i][1]), new T.Vector3(path[i + 1][0], CBT + 0.0006, path[i + 1][1]), 0.0008, trk); });

  // electrolytic capacitors: blue PVC sleeve, polarity stripe, printed value, aluminium top with vent, rubber bung, two leads
  var tray = S.rounded(0.085, 0.045, 0.012, 0.004, M.wood); tray.rotation.x = -Math.PI / 2; tray.position.set(0.36, 0.006, 0.03); S.scene.add(tray);
  var foam = S.mesh(new T.BoxGeometry(0.075, 0.004, 0.035), new T.MeshStandardMaterial({ color: 0x2a2d33, roughness: 0.95 })); foam.position.set(0.36, 0.0135, 0.03); S.scene.add(foam);
  S.contact(0.13, 0.09, 0.36, 0.03, 0.45);
  var TRAY = [new T.Vector3(0.337, 0.0155, 0.03), new T.Vector3(0.36, 0.0155, 0.03), new T.Vector3(0.384, 0.0155, 0.03)];
  var LEAD = 0.004;   // visible lead length below the bung
  var leadM = new T.MeshStandardMaterial({ color: 0xcfd3d6, roughness: 0.25, metalness: 1 });
  var capObjs = CAPS.map(function (c) {
    var g = new T.Group(); S.scene.add(g);
    var tex = S.canvasTex(512, 256, function (x, w, h) { x.fillStyle = '#2456a8'; x.fillRect(0, 0, w, h);
      var gr = x.createLinearGradient(0, 0, w, 0); gr.addColorStop(0, 'rgba(255,255,255,.0)'); gr.addColorStop(0.5, 'rgba(255,255,255,.1)'); gr.addColorStop(1, 'rgba(0,0,0,.1)'); x.fillStyle = gr; x.fillRect(0, 0, w, h);
      x.fillStyle = '#c9d8ee'; x.fillRect(w * 0.0, 0, w * 0.16, h); x.fillStyle = '#2456a8'; x.font = '700 70px "Public Sans", sans-serif'; x.textAlign = 'center';
      for (var k = 0; k < 3; k++) x.fillText('−', w * 0.08, 70 + k * 80);
      x.fillStyle = '#f1f4fa'; x.font = '700 50px "Public Sans", sans-serif'; x.fillText(c.uF + 'µF', w * 0.5, h * 0.42); x.font = '600 38px "Public Sans", sans-serif'; x.fillText('25V  105°C', w * 0.5, h * 0.66);
      x.font = '600 26px "Public Sans", sans-serif'; x.fillText('M  ±20%', w * 0.5, h * 0.85); });
    var sleeve = S.mesh(new T.CylinderGeometry(c.r, c.r, c.h, 40, 1, true), new T.MeshStandardMaterial({ map: tex, roughness: 0.35 })); sleeve.position.y = c.h / 2; g.add(sleeve);
    var topTex = S.canvasTex(128, 128, function (x, w, h) { x.fillStyle = '#c8ccd0'; x.fillRect(0, 0, w, h); x.strokeStyle = '#8e949a'; x.lineWidth = 5; x.beginPath(); x.moveTo(64, 20); x.lineTo(64, 108); x.moveTo(26, 86); x.lineTo(64, 64); x.lineTo(102, 86); x.stroke(); });
    var topD = S.mesh(new T.CircleGeometry(c.r * 0.86, 32), new T.MeshStandardMaterial({ map: topTex, roughness: 0.3, metalness: 0.8 })); topD.rotation.x = -Math.PI / 2; topD.position.y = c.h - 0.0004; g.add(topD);
    var rim = S.mesh(new T.TorusGeometry(c.r * 0.93, c.r * 0.08, 8, 32), new T.MeshStandardMaterial({ color: 0x2456a8, roughness: 0.35 })); rim.rotation.x = Math.PI / 2; rim.position.y = c.h - 0.0002; g.add(rim);
    var bung = S.mesh(new T.CylinderGeometry(c.r * 0.92, c.r * 0.92, 0.0008, 32), M.rubber); bung.position.y = 0.0004; g.add(bung);
    [-1, 1].forEach(function (s) { rod(new T.Vector3(s * 0.0025, 0.0004, 0), new T.Vector3(s * 0.0025, -LEAD, 0), 0.00028, leadM, g); });
    g.userData.cap = c; return g; });
  // the stripe (−) faces +x on the board so the + lead goes to the + terminal
  function placeCap(i, pos) { capObjs[i].position.set(pos.x, pos.y + LEAD, pos.z); capObjs[i].rotation.y = Math.PI; }
  CAPS.forEach(function (c, i) { placeCap(i, TRAY[i]); });
  var capShadow = S.contact(0.03, 0.03, SOCK.x, SOCK.z, 0.0);

  // ================================================================ meters + stopwatch
  var vm = S.meter({ min: 0, max: 5, ticks: 5, unit: 'V', symbol: 'V', caption: 'D.C. VOLTMETER  0–5 V', pos: [0.36, 0, -0.34], rotY: -0.18 });
  (function marker() {   // a red set-mark at 63 % of 5 V (3.16 V), as students stick on the glass
    var face = vm.children[1], f = TARGET / 5, ang = -(f - 0.5) * 1.6, r = 0.047;
    var mk = S.mesh(new T.BoxGeometry(0.0014, 0.007, 0.0005), new T.MeshStandardMaterial({ color: 0xd11f1f, roughness: 0.4 }), false);
    mk.position.set(-Math.sin(ang) * r, -0.0315 + Math.cos(ang) * r, 0.0262); mk.rotation.z = ang; face.add(mk); })();
  var watch = S.stopwatch([0.1, 0.035, 0.1], [-1.15, 0, -0.15]);
  function mt(m, which) { var w = new T.Vector3(); m.updateMatrixWorld(true); m.userData[which].getWorldPosition(w); w.y += 0.004; return w; }

  // ================================================================ wires
  function tt(t) { return new T.Vector3(t.position.x, t.position.y + 0.008, t.position.z); }
  var psPos = wpos(psu, 0.065, 0.004 + PSH / 2 - 0.014, FZ + 0.02), psNeg = wpos(psu, 0.025, 0.004 + PSH / 2 - 0.014, FZ + 0.02);
  var fwd = new T.Vector3(Math.sin(psu.rotation.y), 0, Math.cos(psu.rotation.y));
  function out(v, d) { return v.clone().add(fwd.clone().multiplyScalar(d)); }
  var s0 = tt(swT[0]), s1 = tt(swT[1]), r0 = tt(rbT[0]), r1 = tt(rbT[1]), cP = tt(cbT[0]), cN = tt(cbT[1]), vP = mt(vm, 'plus'), vN = mt(vm, 'minus');
  S.wire([arr(psPos), arr(out(psPos, 0.03)), [s0.x - 0.04, 0.01, s0.z - 0.03], [s0.x - 0.012, 0.03, s0.z], arr(s0)], 'red');
  S.wire([arr(s1), [s1.x + 0.012, 0.03, s1.z], [r0.x - 0.03, 0.01, r0.z + 0.05], [r0.x - 0.01, 0.06, r0.z], arr(r0)], 'red');
  S.wire([arr(r1), [r1.x + 0.012, 0.06, r1.z], [r1.x + 0.05, 0.01, r1.z + 0.05], [cP.x - 0.01, 0.03, cP.z - 0.05], arr(cP)], 'red');
  S.wire([arr(cN), [cN.x + 0.012, 0.03, cN.z - 0.02], [cN.x + 0.01, 0.006, -0.25], [0.2, 0.006, -0.27], [-0.06, 0.006, -0.28], [-0.3, 0.006, -0.32], arr(out(psNeg, 0.04)), arr(psNeg)], 'black');
  S.wire([arr(vP), [vP.x - 0.01, 0.03, vP.z + 0.04], [cP.x + 0.002, 0.03, cP.z - 0.04], arr(lift(cP, 0.002))], 'yellow');
  S.wire([arr(vN), [vN.x, 0.03, vN.z + 0.05], [cN.x + 0.002, 0.03, cN.z - 0.04], arr(lift(cN, 0.002))], 'blue');
  function lift(v, dy) { return new T.Vector3(v.x, v.y + dy, v.z); }

  S.addApparatus('psu', psu, 'DC power supply (5 V)', 'A regulated 5 V supply: the charging emf E.');
  S.addApparatus('sw', sw, 'Toggle switch (key K)', 'Closing it connects the supply: charging starts at that instant.');
  S.addApparatus('rbox', rbox, 'Resistance box (kΩ)', 'Pull out plugs to put resistance in the circuit. The plugs pulled out add up to R.');
  S.addApparatus('cap', capObjs[0], 'Electrolytic capacitors 100, 220, 470 µF', 'Blue sleeve; the stripe with − marks is the negative lead. Its + lead goes to the + terminal.');
  S.addApparatus('cb', cb, 'Capacitor board', 'The socket holds the capacitor. The red DISCHARGE button shorts it through 10 Ω.');
  S.addApparatus('vm', vm, 'Voltmeter (0–5 V)', 'Across the capacitor. The red mark is at 3.16 V = 63 % of 5 V.');
  S.addApparatus('watch', watch.group, 'Digital stopwatch', 'Least count 0.01 s. Start it as the switch closes; stop it at the red mark.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudR = S.hudCard('R × C'), hudV = S.hudCard('V across C'), hudT = S.hudCard('Stopwatch');

  // ================================================================ human actions
  function setR(R) {
    if (busy()) return Promise.resolve();
    R = Math.round(R);
    if (!(R >= 1 && R <= 20)) { S.say('Choose R from 1 to 20 kΩ.'); return Promise.resolve(); }
    if (st.closed) { S.say('Open the switch before you change the resistance.'); return Promise.resolve(); }
    var want = plan(R), idx = []; want.forEach(function (w, i) { if (w !== plugOut[i]) idx.push(i); });
    if (!idx.length) { st.R = R; return Promise.resolve(); }
    if (S.fast) { idx.forEach(function (i) { plugOut[i] = want[i]; plugLook(i, want[i] ? 1 : 0); }); st.R = R; st.boxR = boxValue(); p.Rr = st.boxR * 1000; return Promise.resolve(); }
    return seq(function () { return idx.reduce(function (pr, i) { return pr.then(function () {
      var top = function () { var w = new T.Vector3(); plugs[i].getWorldPosition(w); w.y += 0.016; return w; }, f0 = plugOut[i] ? 1 : 0, f1 = want[i] ? 1 : 0;
      return S.hand.shape('relaxed', 120).then(function () { return S.hand.reach(top().add(new T.Vector3(0, 0.02, 0)), 'top', 450); })
        .then(function () { return S.hand.reach(top(), 'top', 180); }).then(function () { return S.hand.shape('pinch', 180); })
        .then(function () { return S.hand.follow(function (k) { plugLook(i, f0 + (f1 - f0) * k); return top(); }, 'top', 380); })
        .then(function () { S.click(1500, 0.02); plugOut[i] = want[i]; st.boxR = boxValue(); p.Rr = st.boxR * 1000; return S.hand.shape('relaxed', 150); }); }); }, Promise.resolve())
      .then(function () { st.R = R; S.say('Resistance box set: R = ' + st.boxR + ' kΩ.'); }); });
  }
  function capTop(i) { var g = capObjs[i]; return new T.Vector3(g.position.x, g.position.y + CAPS[i].h + 0.006, g.position.z); }
  function moveCap(i, to) {   // pinch the capacitor from above, lift it, carry it, push it down onto `to`
    var from = capObjs[i].position.clone(), dest = new T.Vector3(to.x, to.y + LEAD, to.z);
    return S.hand.reach(capTop(i).add(new T.Vector3(0, 0.025, 0)), 'top', 500).then(function () { return S.hand.reach(capTop(i), 'top', 200); })
      .then(function () { return S.hand.shape('pinch', 200); })
      .then(function () { return S.hand.follow(function (k) { var q = from.clone().lerp(dest, k); q.y += Math.sin(Math.PI * k) * 0.05; capObjs[i].position.copy(q); return capTop(i); }, 'top', 900); })
      .then(function () { S.click(700, 0.03); return S.hand.shape('relaxed', 180); });
  }
  function setC(i) {
    if (busy()) return Promise.resolve();
    if (!(i >= 0 && i < CAPS.length)) return Promise.resolve();
    if (st.closed) { S.say('Open the switch before you change the capacitor.'); return Promise.resolve(); }
    if (st.cap === i) return Promise.resolve();
    var old = st.cap;
    function remove() { if (old < 0) return Promise.resolve(); st.capV[old] = vc; st.cap = -1; vc = 0; capShadow.material.opacity = 0; return S.fast ? (placeCap(old, TRAY[old]), Promise.resolve()) : moveCap(old, TRAY[old]); }
    function insert() { return (S.fast ? (placeCap(i, SOCK), Promise.resolve()) : moveCap(i, SOCK)).then(function () {
      st.cap = i; p.Cc = CAPS[i].uF * 1e-6; sim = KC.init(p, cfg); sim.vc.C1 = st.capV[i]; refresh(); capShadow.material.opacity = 0.45; st.discharged = st.capV[i] < 0.05;
      S.say(CAPS[i].uF + ' µF capacitor in the socket, + lead to the + terminal.'); }); }
    if (S.fast) return remove().then(insert);
    return seq(function () { return remove().then(insert); });
  }
  function discharge() {
    if (busy()) return Promise.resolve();
    if (st.cap < 0) { S.say('Put a capacitor in the socket first.'); return Promise.resolve(); }
    if (st.closed) { S.say('Open the switch first: never short the capacitor while the supply is connected.'); return Promise.resolve(); }
    return S.hand.tap(pbBtn).then(function () { pbBtn.position.y = CBT + 0.009; sim = KC.init(p, cfg); refresh(); st.capV[st.cap] = 0; st.discharged = true; S.click(600, 0.06);
      watch.t = 0; watch.on = false; S.say('Capacitor discharged: the voltmeter reads 0 V. The stopwatch is reset.'); S.render(); });
  }
  function flip(on) {
    var a0 = on ? OFF_A : ON_A, a1 = on ? ON_A : OFF_A;
    return S.hand.pinchMove(leverTip(a0), function (k) { return leverTip(a0 + (a1 - a0) * k); }, function (k) { lever.rotation.z = a0 + (a1 - a0) * k; },
      { mode: 'side', ms: 260, reachMs: 650, hold: 120 }).then(function () { lever.rotation.z = a1; });
  }
  function closeAndStart() {
    if (busy()) return Promise.resolve();
    if (st.closed) { S.say('The switch is already closed.'); return Promise.resolve(); }
    if (st.cap < 0) { S.say('Put a capacitor in the socket first.'); return Promise.resolve(); }
    if (st.boxR < 1) { S.say('Set the resistance box first: with no plug out, R is zero.'); return Promise.resolve(); }
    if (vc > 0.05) { S.say('The capacitor still holds ' + readV().toFixed(2) + ' V. Press DISCHARGE first, so it starts from 0 V.'); return Promise.resolve(); }
    // the closing click and START happen together (the other hand presses START as the switch snaps on)
    return flip(true).then(function () { st.closed = true; p.key = 1; S.click(1800, 0.04); watch.t = 0; watch.on = true; st.discharged = false;
      S.say('Switch closed and stopwatch started. Watch the needle; stop the watch when it reaches the red mark (3.16 V).'); S.render(); });
  }
  function stopWatch() {
    if (!watch.on) { S.say('The stopwatch is not running.'); return Promise.resolve(); }
    var t = watchRead(), v = vc; watch.on = false;   // the moment you decided to stop
    var tap = S.hand.busy ? Promise.resolve() : S.hand.tap(watch.start);
    return tap.then(function () {
      if (v < TARGET - 0.12 || v > TARGET + 0.12) { S.say('You stopped at ' + v.toFixed(2) + ' V, not at the 3.16 V mark. Open the switch, discharge, and try again.'); S.render(); return; }
      var R = st.boxR, C = CAPS[st.cap].uF;
      S.addRow({ R: R, C: C, RC: R * 1000 * C * 1e-6, tau: t });
      S.say('Written in your record book: R = ' + R + ' kΩ, C = ' + C + ' µF, τ = ' + t.toFixed(2) + ' s.'); });
  }
  function openSwitch() {
    if (busy()) return Promise.resolve();
    if (!st.closed) return Promise.resolve();
    if (watch.on) watch.on = false;
    return flip(false).then(function () { st.closed = false; p.key = 0; S.click(1400, 0.03); S.say('Switch open. The capacitor keeps its charge until you discharge it.'); S.render(); });
  }
  function distinct() { var s = {}; S.rows.forEach(function (r) { s[r.RC.toFixed(3)] = 1; }); return Object.keys(s).length; }
  function ready() { return st.cap >= 0 && st.boxR >= 1 && vc < 0.05 && !st.closed; }

  return {
    camera: { pos: [0.1, 0.66, 1.0], look: [0.02, 0.02, -0.18] },
    views: { psu: [[-0.36, 0.2, -0.12], [-0.44, 0.05, -0.42]], sw: [[-0.12, 0.13, -0.08], [-0.17, 0.01, -0.21]], rbox: [[0.1, 0.2, -0.17], [0.07, 0.04, -0.38]],
      cb: [[0.36, 0.14, 0.0], [0.33, 0.01, -0.13]], cap: [[0.4, 0.1, -0.02], [0.33, 0.015, -0.13]], vm: [[0.4, 0.2, -0.14], [0.36, 0.05, -0.33]],
      watch: [[0.14, 0.2, 0.3], [0.1, 0.03, 0.08]], bench: [[0.06, 0.5, 0.66], [0.04, 0.02, -0.2]], run: [[0.24, 0.36, 0.46], [0.18, 0.03, -0.17]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'When the switch closes, charge flows through R onto the capacitor. Its voltage rises quickly at first and then more and more slowly, because the current falls as the capacitor fills.',
      formula: 'V_C = E (1 − e^(−t / RC))', formulaNote: 'at t = RC, V_C = 0.632 E · the time constant τ = RC (ohms × farads = seconds)',
      more: ['With E = 5 V, τ is the time for the voltmeter to reach 3.16 V. Measure τ for several R and C, then plot τ against RC: it is a straight line through the origin with slope 1.'],
      precautions: 'Discharge the capacitor before each reading. Start the stopwatch exactly when the switch closes. Connect the electrolytic the right way round: + lead to the + terminal. Open the switch before changing R or C.' },
    book: { title: 'Expt. — Charging of a capacitor (τ = RC)', lines: ['Aim: to find the time constant τ of an RC circuit.', 'E = 5.0 V,  63 % of E = 3.16 V', 'τ = time for V_C to reach 3.16 V', 'Theory: τ = RC', 'Precautions: discharge before each reading.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'R (kΩ)', get: function (r) { return String(r.R); } }, { label: 'C (µF)', get: function (r) { return String(r.C); } },
        { label: 'RC (s)', get: function (r) { return r.RC.toFixed(2); } }, { label: 'τ (s)', get: function (r) { return r.tau.toFixed(2); } }] },
    graph: { x: function (r) { return r.RC; }, y: function (r) { return r.tau; }, xlabel: 'RC (s)', ylabel: 'τ measured (s)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) { if (distinct() < 2) return null; var k = S.fit.origin(rows.map(function (r) { return [r.RC, r.tau]; }));
      return { label: 'Slope of τ against RC', value: k, unit: '', digits: 3, truth: 1, note: 'Slope 1 means τ = RC.' }; },
    tol: 0.02,
    resultNote: 'Your human reaction time adds a small error to each τ. It matters most for the shortest time constants, so long τ readings give the better slope.',
    chips: ['Why 63 %?', 'Why discharge before each reading?', 'Why is the charging fast at first?', 'Check my readings', 'What if the capacitor is reversed?'],
    viva: [['After a time 5RC, the capacitor voltage is about?', ['99 % of E', '63 % of E', '50 % of E'], 0, 'V = E(1 − e^−5) = 0.993 E.'],
      ['Why must the capacitor be discharged before each reading?', ['So it starts from 0 V and the 63 % mark means t = RC', 'To protect the voltmeter', 'It has no effect'], 0, 'The formula V = E(1 − e^(−t/RC)) assumes V = 0 at t = 0.']],
    askState: function () { return { switch_closed: st.closed, R_kohm: st.boxR, C_uF: st.cap >= 0 ? CAPS[st.cap].uF : null, RC_s: st.cap >= 0 ? +(st.boxR * CAPS[st.cap].uF / 1000).toFixed(3) : null,
      capacitor_voltage_V: readV(), stopwatch_running: watch.on, stopwatch_s: watchRead(), supply_V: E }; },

    steps: [
      { id: 'setup', title: 'Set R and C', view: 'bench', render: function (u) {
          u.h2('Set R and C, then discharge');
          var t1 = u.task('1. Resistance on the box', st.boxR >= 1, st.boxR >= 1 ? 'R = ' + st.boxR + ' kΩ (plugs pulled out add up to it)' : 'No plug pulled out yet: R = 0');
          u.slider('Resistance R', 1, 20, 1, function () { return st.rTarget; }, function (v) { st.rTarget = v; }, 'kΩ', 0);
          t1.add(u.row(u.button('Set the resistance box', function () { S.focus('rbox'); setR(st.rTarget); }, st.boxR !== st.rTarget, S.hand.busy || st.closed)));
          var t2 = u.task('2. Capacitor in the socket', st.cap >= 0, st.cap >= 0 ? 'C = ' + CAPS[st.cap].uF + ' µF' : 'Pick one from the tray');
          t2.add(u.row.apply(null, CAPS.map(function (c, i) { return u.button(c.uF + ' µF', function () { S.focus('cb'); setC(i); }, st.cap < 0 && i === 0, S.hand.busy || st.closed || st.cap === i); })));
          u.task('3. Discharge the capacitor', st.cap >= 0 && vc < 0.05, st.cap < 0 ? 'Needs a capacitor' : 'Now ' + readV().toFixed(2) + ' V')
            .add(u.row(u.button('Press DISCHARGE', function () { S.focus('cb'); discharge(); }, false, S.hand.busy || st.cap < 0 || st.closed)));
          if (st.closed) u.note('The switch is closed. Open it in the next step before changing R or C.');
          if (st.cap >= 0 && st.boxR >= 1) u.formula('RC = ' + st.boxR + ' kΩ × ' + CAPS[st.cap].uF + ' µF = ' + (st.boxR * CAPS[st.cap].uF / 1000).toFixed(2) + ' s');
          u.next('Next: charge and time it', ready());
        },
        ok: function () { return ready(); },
        auto: function () { return setR(10).then(function () { return setC(0); }).then(function () { return discharge(); }); } },
      { id: 'charge', title: 'Charge and time', view: 'run', render: function (u) {
          u.h2('Close the switch and time τ');
          u.p('Close the switch and start the stopwatch together. When the needle reaches the red mark (3.16 V), stop the watch. Then open the switch and discharge for the next reading.');
          u.live(function () { return 'V_C = ' + readV().toFixed(2) + ' V  ·  stopwatch ' + watchRead().toFixed(2) + ' s'; });
          u.row(u.button('Close the switch + START', function () { closeAndStart(); }, true, S.hand.busy || st.closed || !ready()),
            u.button('STOP at 3.16 V', function () { stopWatch().then(function () { S.render(); }); }, true, !watch.on),
            u.button('Open the switch', function () { openSwitch(); }, false, S.hand.busy || !st.closed));
          u.row(u.button('Discharge', function () { discharge(); }, false, S.hand.busy || st.closed || st.cap < 0),
            u.button('Change R or C', function () { if (st.closed) { S.say('Open the switch first.'); return; } S.go(1); }, false, S.hand.busy));
          if (!st.closed && st.cap >= 0 && vc >= 0.05) u.note('The capacitor holds charge. Discharge it before the next reading.');
          u.h3('Observation table'); u.table();
          var d = distinct();
          if (S.rows.length < 3 || d < 2) u.p(S.rows.length + ' of at least 3 readings, with at least 2 different RC values.');
          u.next('Next: plot τ against RC', S.rows.length >= 3 && d >= 2);
        },
        ok: function () { return S.rows.length >= 3 && distinct() >= 2; },
        auto: function () {
          var combos = [[10, 0], [10, 1], [20, 1], [10, 2]];
          return combos.reduce(function (pr, c) { return pr.then(function () {
            return openSwitch().then(function () { return setR(c[0]); }).then(function () { return setC(c[1]); }).then(function () { return discharge(); })
              .then(function () { return closeAndStart(); })
              .then(function () { S.advance(80, function () { return vc >= TARGET; }); return stopWatch(); })
              .then(function () { return openSwitch(); }); }); }, Promise.resolve()); } },
    ],

    tick: function (dt) {
      if (st.cap >= 0) { KC.step(sim, p, dt, cfg); vc = KC.view(sim, p, cfg).V_C1; } else vc = 0;
      vm.set(vc);
      hudR.set(st.cap >= 0 && st.boxR ? (st.boxR * CAPS[st.cap].uF / 1000).toFixed(2) + ' s' : '—'); hudV.set(readV().toFixed(2) + ' V'); hudT.set(watchRead().toFixed(2) + ' s');
    },
  };
});
