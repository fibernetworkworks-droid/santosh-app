/* Prayogshala studio module: p-n junction diode, forward characteristic (NCERT Class XII).
   Physics: the circuit kernel from kernels.js (MNA with the Shockley diode) on the lab's own net and params - the same
   numbers the server checks. The milliammeter reads the series current I_R, the voltmeter reads V_VM across the diode. */
HoolaStudio.define('pn-junction-diode', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KC = HK.K.circuit, assign = HK.assign;
  var cfg = S.lab.cfg, p = HK.paramsFor('circuit', S.lab.params);
  var I_REF_MA = 10;
  // the diode on the board: a family variant names it (1N4148, germanium, LED...); the base lab is a 1N4007 silicon rectifier
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || '';
  var LED = /\bLED\b|light.emitting/i.test(SAMPLE), GLASS = !LED && /1N4148|1N914|1N34|OA\d|germanium|glass/i.test(SAMPLE);
  var LEDCOL = /green/i.test(SAMPLE) ? 0x2fc25b : /yellow|amber/i.test(SAMPLE) ? 0xf2c21b : /blue/i.test(SAMPLE) ? 0x3a6df0 : 0xe0261b;
  var PART = (SAMPLE.match(/\b(1N\d{3,4}A?|OA\d{2,3}|BAT\d+)\b/i) || [])[0] || (SAMPLE ? '' : '1N4007');
  var MAT = /germanium|\bGe\b/i.test(SAMPLE) ? 'germanium' : /schottky/i.test(SAMPLE) ? 'Schottky' : LED ? 'LED' : 'silicon';
  var DNAME = SAMPLE || 'Silicon diode 1N4007';
  var LOWV = MAT === 'germanium' ? '0.15' : MAT === 'Schottky' ? '0.1' : MAT === 'LED' ? (/blue/i.test(SAMPLE) ? '2.5' : '1.6') : '0.5';
  // supply range and voltmeter range follow the diode: an LED needs more than 3 V; a low-voltage diode is read on a 0-0.5 V meter
  function drop10(E) { var q = assign(p, { Eb: E }), v = KC.view(KC.init(q, cfg), q, cfg); return v; }
  var EMAX = (function () { var lo = 0, hi = 12, i, mid; for (i = 0; i < 50; i++) { mid = (lo + hi) / 2; if (drop10(mid).I_R < 0.02) lo = mid; else hi = mid; } return hi <= 3 ? 3 : 6; })();
  var VK = (function () { var lo = 0, hi = 12, i, mid; for (i = 0; i < 50; i++) { mid = (lo + hi) / 2; if (drop10(mid).I_R < 0.025) lo = mid; else hi = mid; } return drop10(hi).V_VM; })();
  var VMAX = VK <= 0.45 ? 0.5 : VK <= 0.95 ? 1 : VK <= 2.9 ? 3 : 5, VLC = VMAX === 0.5 ? 0.01 : VMAX === 1 ? 0.02 : VMAX === 3 ? 0.05 : 0.1, VRD = VLC / 2;
  var st = { set: 0, power: false, checked: false };
  var now = { V: 0, I: 0 };
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function round(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function solveFor(E) { var q = assign(p, { Eb: E }), s = KC.init(q, cfg), v = KC.view(s, q, cfg); return { V: v.V_VM, I: v.I_R }; }
  function solve() { var r = solveFor(st.power ? st.set : 0); now.V = r.V; now.I = r.I; }
  // the true knee voltage in this lab: the diode voltage at which the series current is exactly 10 mA (kernel, bisection on E)
  var TRUTH = (function () { var lo = 0.3, hi = EMAX, i, mid; for (i = 0; i < 60; i++) { mid = (lo + hi) / 2; if (solveFor(mid).I * 1000 < I_REF_MA) lo = mid; else hi = mid; } return solveFor((lo + hi) / 2).V; })();
  function readV() { return +(Math.round(now.V / VRD) * VRD).toFixed(4); }   // read to half a division: 0-1 V, LC 0.02 V -> 0.01 V
  var VDIG = VRD < 0.01 - 1e-12 ? 3 : 2;
  function fV(v) { return v.toFixed(VDIG); }
  function fmt(v) { return String(+v.toFixed(3)); }
  function readI() { return round(now.I * 1000, 1); }    // milliammeter 0-25 mA, read to 0.1 mA
  function wpos(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function arr(v) { return [v.x, v.y, v.z]; }
  function rod(a, b, r, mat) { var d = b.clone().sub(a), m = S.mesh(new T.CylinderGeometry(r, r, d.length(), 8), mat); m.position.copy(a).add(b).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize()); S.scene.add(m); return m; }

  // ================================================================ variable DC power supply (knob, rocker, lamp, binding posts)
  var PSW = 0.24, PSH = 0.12, PSD = 0.17, PW = PSW - 0.014, PH = PSH - 0.014;
  var psu = new T.Group(); S.scene.add(psu); psu.position.set(0.46, 0, -0.38); psu.rotation.y = -0.32;
  var caseM = new T.MeshStandardMaterial({ color: 0xd9d5cb, roughness: 0.5, metalness: 0.15 });
  var cs = S.rounded(PSW, PSD, PSH, 0.012, caseM); cs.rotation.x = -Math.PI / 2; cs.position.y = PSH / 2; psu.add(cs);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) { var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.004, 16), M.rubber); ft.position.set(f[0] * (PSW / 2 - 0.02), 0.002, f[1] * (PSD / 2 - 0.02)); psu.add(ft); });
  cs.position.y += 0.004;
  // vent slots on the top
  for (var vs = 0; vs < 9; vs++) { var sl = S.mesh(new T.BoxGeometry(0.004, 0.0012, 0.07), M.black, false); sl.position.set(-0.06 + vs * 0.015, PSH + 0.0045, -0.03); psu.add(sl); }
  var FZ = PSD / 2 + 0.0062;   // front of the fascia
  var KX = -0.018, KY = -0.008;   // knob centre on the panel (panel coordinates)
  var panelTex = S.canvasTex(1100, Math.round(1100 * PH / PW), function (x, w, h) {
    var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; }, k = w / PW;
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.font = '700 40px "Public Sans", sans-serif'; x.fillText('VARIABLE DC POWER SUPPLY', 40, 70);
    x.font = '500 26px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText('0 – ' + EMAX + ' V  ·  0.5 A max  ·  230 V AC input', 40, 108);
    // knob scale
    var cx = X(KX), cy = Y(KY), R = 0.025 * k; x.strokeStyle = '#f1efe8'; x.fillStyle = '#f1efe8';
    for (var i = 0; i <= 30; i++) { var th = (225 - 270 * i / 30) * Math.PI / 180, big = i % 5 === 0, r0 = big ? R + 22 : R + 12;
      x.lineWidth = big ? 4 : 2; x.beginPath(); x.moveTo(cx + Math.cos(th) * R, cy - Math.sin(th) * R); x.lineTo(cx + Math.cos(th) * r0, cy - Math.sin(th) * r0); x.stroke();
      if (big) { x.font = '600 26px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText(String(+(i / 10 * EMAX / 3).toFixed(1)), cx + Math.cos(th) * (R + 46), cy - Math.sin(th) * (R + 46) + 9); } }
    x.textAlign = 'center'; x.font = '700 26px "Public Sans", sans-serif'; x.fillText('VOLTAGE  (V)', cx, Y(-0.046));
    // power + lamp
    x.fillText('POWER', X(-0.088), Y(-0.046)); x.font = '600 22px "Public Sans", sans-serif'; x.fillText('ON', X(-0.088), Y(0.026));
    // output
    x.font = '700 26px "Public Sans", sans-serif'; x.fillText('OUTPUT', X(0.072), Y(0.022));
    x.font = '700 40px "Public Sans", sans-serif'; x.fillStyle = '#9aa3b2'; x.fillText('−', X(0.055), Y(-0.04)); x.fillStyle = '#ff7a6b'; x.fillText('+', X(0.09), Y(-0.04));
    x.textAlign = 'left'; });
  var fascia = S.mesh(new T.BoxGeometry(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: panelTex, roughness: 0.45 }), M.grey]);
  fascia.position.set(0, 0.004 + PSH / 2, FZ - 0.002); psu.add(fascia);
  function pp(u, v, dz) { return new T.Vector3(u, 0.004 + PSH / 2 + v, FZ + (dz || 0)); }   // panel point in the supply's frame
  // knob: knurled skirt + cap + white pointer line
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  var knob = new T.Group(); knob.position.copy(pp(KX, KY)); psu.add(knob);
  var skirt = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.004, 40), M.bakelite); skirt.rotation.x = Math.PI / 2; skirt.position.z = 0.002; knob.add(skirt);
  var kb = S.mesh(new T.CylinderGeometry(0.0145, 0.016, 0.016, 40), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; knob.add(kb);
  var kc = S.mesh(new T.CylinderGeometry(0.0135, 0.0135, 0.0015, 40), M.chrome); kc.rotation.x = Math.PI / 2; kc.position.z = 0.0205; knob.add(kc);
  var ptr = S.mesh(new T.BoxGeometry(0.0022, 0.016, 0.0012), M.white, false); ptr.position.set(0, 0.009, 0.0215); knob.add(ptr);
  function knobAngle(E) { return 3 * Math.PI / 4 - 1.5 * Math.PI * (E / EMAX); }
  knob.rotation.z = knobAngle(0);
  // rocker + pilot lamp
  var rocker = S.rounded(0.016, 0.024, 0.008, 0.003, M.bakelite); rocker.position.copy(pp(-0.088, -0.018, 0.004)); psu.add(rocker);
  var rmark = S.mesh(new T.BoxGeometry(0.0018, 0.008, 0.001), M.white, false); rmark.position.set(0, 0.006, 0.0045); rocker.add(rmark);
  var lampM = new T.MeshStandardMaterial({ color: 0x5a1410, roughness: 0.3, emissive: 0x000000 });
  var lamp = S.mesh(new T.SphereGeometry(0.0055, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2), lampM); lamp.rotation.x = Math.PI / 2; lamp.position.copy(pp(-0.088, 0.012, 0)); psu.add(lamp);
  var bez = S.mesh(new T.TorusGeometry(0.006, 0.0012, 8, 24), M.chrome); bez.position.copy(pp(-0.088, 0.012, 0.0005)); psu.add(bez);
  function setPowerLook() { rocker.rotation.x = st.power ? -0.22 : 0.22; lampM.color.setHex(st.power ? 0xff3b2a : 0x5a1410); lampM.emissive.setHex(st.power ? 0xff2a14 : 0x000000); lampM.emissiveIntensity = st.power ? 2.2 : 0; }
  setPowerLook();
  // binding posts on the front
  function post(u, mat) { var g = new T.Group(); g.position.copy(pp(u, -0.012)); psu.add(g);
    var stem = S.mesh(new T.CylinderGeometry(0.0028, 0.0028, 0.02, 16), M.brass); stem.rotation.x = Math.PI / 2; stem.position.z = 0.01; g.add(stem);
    var cap = S.mesh(new T.CylinderGeometry(0.0075, 0.0085, 0.012, 24), mat); cap.rotation.x = Math.PI / 2; cap.position.z = 0.012; g.add(cap);
    var nose = S.mesh(new T.CylinderGeometry(0.0045, 0.0055, 0.004, 20), mat); nose.rotation.x = Math.PI / 2; nose.position.z = 0.02; g.add(nose); return g; }
  var postNeg = post(0.055, M.blackPlastic), postPos = post(0.09, M.red);
  S.contact(0.34, 0.26, psu.position.x, psu.position.z, 0.55);

  // ================================================================ component board: R (100 Ω carbon) and D (1N4007) on brass terminals
  // colour code of the series resistor (E-series value, 4 bands, gold = 5 %)
  var BAND = ['#111111', '#6b3a1e', '#c4231c', '#e8761e', '#e9c81a', '#2c8a3a', '#2747a8', '#7a3aa8', '#8a8a8a', '#f2f2f2'];
  var RTXT = p.Rs >= 1000 ? fmt(p.Rs / 1000) + ' kΩ' : fmt(p.Rs) + ' Ω';
  var RB = (function () { var e = Math.floor(Math.log10(p.Rs)) - 1, d = Math.round(p.Rs / Math.pow(10, e)); if (d >= 100) { d = Math.round(d / 10); e += 1; }
    return [BAND[Math.floor(d / 10)], BAND[d % 10], BAND[Math.max(0, Math.min(9, e))]]; })();
  var BX = 0.0, BZ = -0.06, BW = 0.3, BD = 0.12, BT = 0.012, TZ = BZ + 0.012, LY = BT + 0.007;
  var boardM = new T.MeshStandardMaterial({ color: 0xe9e2cf, roughness: 0.7 });
  var board = S.rounded(BW, BD, BT, 0.006, boardM); board.rotation.x = -Math.PI / 2; board.position.set(BX, BT / 2, BZ); S.scene.add(board);
  var TXS = [-0.12, -0.05, 0.05, 0.12];   // T1 (cathode), T2 (anode), T3, T4 (to + supply)
  var boardTex = S.canvasTex(1200, 480, function (x, w, h) {
    var X = function (u) { return (u / (BW - 0.012) + 0.5) * w; }, Y = function (zz) { return (zz - (BZ - (BD - 0.012) / 2)) / (BD - 0.012) * h; };
    x.fillStyle = '#ece5d2'; x.fillRect(0, 0, w, h); x.strokeStyle = '#7d6f55'; x.lineWidth = 3; x.strokeRect(14, 14, w - 28, h - 28);
    x.fillStyle = '#3d3528'; x.textAlign = 'center'; x.font = '700 34px "Public Sans", sans-serif'; x.fillText('p-n JUNCTION DIODE  ·  FORWARD BIAS', w / 2, 62);
    x.font = '600 30px "Public Sans", sans-serif';
    x.fillText(PART ? 'D  (' + PART + ')' : (LED ? 'LED' : 'D'), X(0), Y(TZ + 0.03)); x.fillText('R = ' + RTXT, X(0.085), Y(TZ + 0.03));
    // little diode symbol between T1 and T2: arrow points to the cathode (left)
    var sx = X(-0.085), sy = Y(TZ - 0.03); x.lineWidth = 4; x.strokeStyle = '#3d3528'; x.beginPath(); x.moveTo(sx + 50, sy); x.lineTo(sx - 50, sy); x.stroke();
    x.beginPath(); x.moveTo(sx + 16, sy - 20); x.lineTo(sx + 16, sy + 20); x.lineTo(sx - 16, sy); x.closePath(); x.fill(); x.fillRect(sx - 20, sy - 22, 5, 44);
    x.font = '700 32px "Public Sans", sans-serif'; x.fillText('K', X(TXS[0]), Y(TZ + 0.017)); x.fillText('A', X(TXS[1]), Y(TZ + 0.017));
    x.fillText('−', X(TXS[0]), Y(TZ + 0.032)); x.fillText('+', X(TXS[3]), Y(TZ + 0.032));
    // zig-zag resistor symbol
    var rx = X(0.085), ry = Y(TZ - 0.03); x.beginPath(); x.moveTo(rx - 70, ry); for (var i = 0; i <= 6; i++) x.lineTo(rx - 45 + i * 15, ry + (i % 2 ? -14 : 14)); x.lineTo(rx + 70, ry); x.stroke();
    x.textAlign = 'left'; });
  var bplate = new T.Mesh(new T.PlaneGeometry(BW - 0.012, BD - 0.012), new T.MeshStandardMaterial({ map: boardTex, roughness: 0.75 })); bplate.rotation.x = -Math.PI / 2; bplate.position.set(BX, BT + 0.0003, BZ); S.scene.add(bplate);
  S.contact(BW + 0.06, BD + 0.06, BX, BZ, 0.5);
  var terms = TXS.map(function (tx) { return S.terminal([BX + tx, BT, TZ], 'brass'); });
  function tpt(i) { return new T.Vector3(BX + TXS[i], LY, TZ); }
  var leadM = new T.MeshStandardMaterial({ color: 0xcfd3d6, roughness: 0.25, metalness: 1 });
  // carbon resistor 100 Ω ±5 %: brown, black, brown, gold (lathe body with end caps)
  var RL = 0.016, RS = 1.4, prof = []; for (var ri = 0; ri <= 40; ri++) { var yy = RL * ri / 40, e = Math.min(yy, RL - yy);
    var ee = e / RS, rr = RS * (ee < 0.0004 ? 0.0009 + ee * 2.4 : ee < 0.0028 ? 0.0019 : ee < 0.0034 ? 0.0019 - (ee - 0.0028) * 0.5 : 0.00165); prof.push(new T.Vector2(rr, yy)); }
  prof.unshift(new T.Vector2(0, 0)); prof.push(new T.Vector2(0, RL));
  var resTex = S.canvasTex(64, 512, function (x, w, h) { x.fillStyle = '#d9bf8c'; x.fillRect(0, 0, w, h);
    for (var i = 0; i < 300; i++) { x.fillStyle = 'rgba(120,90,40,' + (Math.random() * 0.08) + ')'; x.fillRect(Math.random() * w, Math.random() * h, 2, 2); }
    [[0.22, RB[0]], [0.34, RB[1]], [0.46, RB[2]], [0.74, '#c9a23a']].forEach(function (b) { x.fillStyle = b[1]; x.fillRect(0, h * (1 - b[0]) - 22, w, 44); }); });
  var res = new T.Group(); S.scene.add(res);
  var rbody = S.mesh(new T.LatheGeometry(prof, 32), new T.MeshStandardMaterial({ map: resTex, roughness: 0.55 })); rbody.rotation.z = -Math.PI / 2; rbody.position.x = -RL / 2; res.add(rbody);
  var RCX = BX + (TXS[2] + TXS[3]) / 2; res.position.set(RCX, LY, TZ);
  rod(new T.Vector3(RCX - RL / 2 + 0.0004, LY, TZ), tpt(2), 0.0004, leadM); rod(new T.Vector3(RCX + RL / 2 - 0.0004, LY, TZ), tpt(3), 0.0004, leadM);
  // the diode body: black epoxy with a silver band (1N4007), glass with a black band (1N4148, germanium), or an LED dome
  var DL = 0.0085, DR = 0.0021;
  var dio = new T.Group(); S.scene.add(dio);
  if (LED) {
    var ledM = new T.MeshStandardMaterial({ color: LEDCOL, roughness: 0.15, transparent: true, opacity: 0.82, emissive: LEDCOL, emissiveIntensity: 0 });
    var dome = S.mesh(new T.CylinderGeometry(0.0025, 0.0025, 0.0045, 28), ledM); dome.rotation.z = Math.PI / 2; dio.add(dome);
    var tip = S.mesh(new T.SphereGeometry(0.0025, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), ledM); tip.rotation.z = -Math.PI / 2; tip.position.x = 0.00225; dio.add(tip);
    var flange = S.mesh(new T.CylinderGeometry(0.0029, 0.0029, 0.0008, 28), ledM); flange.rotation.z = Math.PI / 2; flange.position.x = -0.0026; dio.add(flange);
    dio.userData.led = ledM;
  } else if (GLASS) {
    var gl = S.mesh(new T.CylinderGeometry(DR * 0.8, DR * 0.8, DL * 0.85, 24), new T.MeshStandardMaterial({ color: 0xd88a3a, roughness: 0.08, transparent: true, opacity: 0.75 })); gl.rotation.z = Math.PI / 2; dio.add(gl);
    var cr = S.mesh(new T.CylinderGeometry(DR * 0.3, DR * 0.3, DL * 0.4, 12), new T.MeshStandardMaterial({ color: 0x6f6f72, roughness: 0.3, metalness: 0.8 })); cr.rotation.z = Math.PI / 2; dio.add(cr);
    var bnd = S.mesh(new T.CylinderGeometry(DR * 0.82, DR * 0.82, DL * 0.12, 24), M.black); bnd.rotation.z = Math.PI / 2; bnd.position.x = -DL * 0.32; dio.add(bnd);
  } else {
    var dTex = S.canvasTex(256, 512, function (x, w, h) { x.fillStyle = '#141416'; x.fillRect(0, 0, w, h);
      x.fillStyle = '#c9ccd0'; x.fillRect(0, h * 0.06, w, h * 0.17);
      x.save(); x.translate(w * 0.5, h * 0.62); x.rotate(Math.PI / 2); x.fillStyle = '#9da3aa'; x.font = '700 64px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText(PART || 'D', 0, 22); x.restore(); });
    var dbody = S.mesh(new T.CylinderGeometry(DR, DR, DL, 32), new T.MeshStandardMaterial({ map: dTex, roughness: 0.35 })); dbody.rotation.z = Math.PI / 2; dio.add(dbody);   // top (band) -> -x = cathode side
    [-1, 1].forEach(function (s) { var cap = S.mesh(new T.SphereGeometry(DR, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2), new T.MeshStandardMaterial({ color: s < 0 ? 0xc9ccd0 : 0x141416, roughness: 0.35 }));
      cap.scale.y = 0.25; cap.rotation.z = -s * Math.PI / 2; cap.position.x = s * DL / 2; dio.add(cap); });
  }
  var DCX = BX + (TXS[0] + TXS[1]) / 2; dio.position.set(DCX, LY, TZ);
  rod(new T.Vector3(DCX - DL / 2, LY, TZ), tpt(0), 0.0004, leadM); rod(new T.Vector3(DCX + DL / 2, LY, TZ), tpt(1), 0.0004, leadM);

  // ================================================================ meters
  var mA = S.meter({ min: 0, max: 25, ticks: 5, unit: 'mA', symbol: 'mA', caption: 'D.C. MILLIAMMETER  0–25 mA', pos: [0.02, 0, -0.32] });
  var vm = S.meter({ min: 0, max: VMAX, ticks: VMAX === 3 ? 6 : VMAX === 0.5 ? 5 : 10, unit: 'V', symbol: 'V', caption: 'D.C. VOLTMETER  0–' + VMAX + ' V', pos: [-0.27, 0, -0.3], rotY: 0.25 });
  function mt(m, which) { var w = new T.Vector3(); m.updateMatrixWorld(true); m.userData[which].getWorldPosition(w); w.y += 0.004; return w; }

  // ================================================================ wires (insulated, sagging, terminal to terminal)
  function lift(v, dy) { return new T.Vector3(v.x, v.y + dy, v.z); }
  var psPos = wpos(psu, 0.09, 0.004 + PSH / 2 - 0.012, FZ + 0.021), psNeg = wpos(psu, 0.055, 0.004 + PSH / 2 - 0.012, FZ + 0.021);
  var fwd = new T.Vector3(Math.sin(psu.rotation.y), 0, Math.cos(psu.rotation.y));
  function out(v, d) { return v.clone().add(fwd.clone().multiplyScalar(d)); }
  var t1 = tpt(0), t2 = tpt(1), t3 = tpt(2), t4 = tpt(3);
  S.wire([arr(psPos), arr(out(psPos, 0.03)), [t4.x + 0.03, 0.03, TZ - 0.07], [t4.x, 0.032, BZ - BD / 2 + 0.004], arr(lift(t4, 0.002))], 'red');
  S.wire([arr(psNeg), arr(out(psNeg, 0.025)), [0.2, 0.006, -0.2], [-0.03, 0.006, -0.2], [-0.16, 0.006, -0.17], [t1.x - 0.01, 0.03, BZ - BD / 2 + 0.004], arr(lift(t1, 0.002))], 'black');
  var aP = mt(mA, 'plus'), aN = mt(mA, 'minus'), vP = mt(vm, 'plus'), vN = mt(vm, 'minus');
  S.wire([arr(lift(t3, 0.002)), [t3.x, 0.032, BZ - BD / 2 + 0.004], [aP.x + 0.01, 0.03, aP.z + 0.06], arr(aP)], 'red');
  S.wire([arr(aN), [aN.x - 0.01, 0.03, aN.z + 0.06], [t2.x, 0.032, BZ - BD / 2 + 0.004], arr(lift(t2, 0.002))], 'black');
  S.wire([arr(vP), [vP.x + 0.04, 0.03, vP.z + 0.07], [t2.x - 0.012, 0.034, BZ - BD / 2 + 0.006], arr(lift(t2, 0.004))], 'yellow');
  S.wire([arr(vN), [vN.x + 0.03, 0.03, vN.z + 0.09], [t1.x - 0.016, 0.034, BZ - BD / 2 + 0.006], arr(lift(t1, 0.004))], 'blue');

  S.addApparatus('psu', psu, 'Variable DC power supply (0–' + EMAX + ' V)', 'Turn the VOLTAGE knob to raise the voltage applied to the circuit. Switch it on with the POWER rocker.');
  var BNAMES = ['black', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'violet', 'grey', 'white'];
  S.addApparatus('res', res, 'Carbon resistor ' + RTXT, 'Bands ' + RB.map(function (c) { return BNAMES[BAND.indexOf(c)]; }).join('-') + '-gold = ' + RTXT + ' ± 5 %. It limits the current so the diode cannot burn out.');
  S.addApparatus('dio', dio, DNAME, LED ? 'A light-emitting diode: the longer lead and the round side are the anode (+); the flat side of the rim marks the cathode. It glows once the current flows.'
    : GLASS ? 'A glass body; the black band marks the cathode (n-side). Anode to + for forward bias.' : 'Black body; the silver band marks the cathode (n-side). Anode to + for forward bias.');
  S.addApparatus('board', board, 'Component board', 'Brass terminals hold the resistor and the diode. The diode sits between K and A.');
  S.addApparatus('ma', mA, 'Milliammeter (0–25 mA)', 'In series with the diode: the whole current passes through it. Read to 0.1 mA.');
  S.addApparatus('vm', vm, 'Voltmeter (0–' + VMAX + ' V)', 'In parallel with the diode: the voltage across it. Least count ' + VLC + ' V.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudE = S.hudCard('Supply setting'), hudV = S.hudCard('Voltmeter V'), hudI = S.hudCard('Milliammeter I');

  // ================================================================ human actions
  function knobFront() { return wpos(psu, KX, 0.004 + PSH / 2 + KY, FZ + 0.024); }
  function turnTo(E) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!isFinite(E) || E < 0 || E > EMAX + 1e-9) { S.say('The supply goes from 0 to ' + EMAX + ' V only.'); return Promise.resolve(); }
    E = round(clamp(E, 0, EMAX), 2);
    var E0 = st.set, a0 = knobAngle(E0), pt = knobFront();
    if (Math.abs(E - E0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      st.set = E0 + (E - E0) * k; knob.rotation.z = knobAngle(st.set); S.hand.group.rotation.y = -(knobAngle(st.set) - a0) * 0.35; solve(); },
      { mode: 'front', ms: 500 + 450 * Math.abs(E - E0), reachMs: 650 })
      .then(function () { st.set = E; knob.rotation.z = knobAngle(E); solve(); S.render(); });
  }
  function togglePower(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (on === st.power) return Promise.resolve();
    if (on && st.set > 0.001) { S.say('Turn the VOLTAGE knob to zero before you switch on.'); return Promise.resolve(); }
    return S.hand.tap(rocker, 'front').then(function () { st.power = on; setPowerLook(); solve(); S.click(900, 0.05);
      S.say(on ? 'Supply on. The pilot lamp is lit.' : 'Supply off.'); S.render(); });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return; }
    if (!st.power) { S.say('Switch the supply on first.'); return; }
    var V = readV(), I = readI();
    if (S.rows.some(function (r) { return Math.abs(r.E - st.set) < 0.005; })) { S.say('You already have a reading at ' + st.set.toFixed(2) + ' V. Turn the knob to a new setting.'); return; }
    if (I > 25) { S.say('The current is beyond the milliammeter range. Turn the knob down.'); return; }
    S.addRow({ E: st.set, V: V, I: I });
    S.say('Written in your record book: V = ' + fV(V) + ' V, I = ' + I.toFixed(1) + ' mA.');
  }
  function bracket(rows) { var pts = rows.map(function (r) { return [r.V, r.I]; }).filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); }).sort(function (a, b) { return a[1] - b[1] || a[0] - b[0]; });
    for (var i = 0; i < pts.length - 1; i++) if (pts[i][1] <= I_REF_MA && pts[i + 1][1] >= I_REF_MA && pts[i + 1][1] > pts[i][1]) return [pts[i], pts[i + 1]];
    return null; }
  function enough() { return S.rows.length >= 8 && !!bracket(S.rows); }
  solve();

  return {
    camera: { pos: [0.24, 0.66, 1.0], look: [0.1, 0.02, -0.18] },
    views: { psu: [[0.62, 0.22, 0.02], [0.44, 0.07, -0.3]], res: [[0.11, 0.1, 0.07], [0.085, 0.01, -0.05]], dio: [[-0.07, 0.09, 0.06], [-0.085, 0.01, -0.05]],
      board: [[0.02, 0.3, 0.3], [0.02, 0.0, -0.08]], ma: [[0.05, 0.22, -0.04], [0.02, 0.05, -0.3]], vm: [[-0.2, 0.22, -0.02], [-0.27, 0.05, -0.29]],
      bench: [[0.2, 0.42, 0.62], [0.08, 0.03, -0.2]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A p-n junction conducts in forward bias (p-side to +). Below about ' + LOWV + ' V the current is almost zero; past the knee it rises steeply, while the voltage across the diode hardly changes.',
      formula: 'I = I_s (e^(V / nV_T) − 1)', formulaNote: 'V_T = kT/q ≈ 25.9 mV at room temperature · this diode: I_s = ' + (p.Is >= 1e-6 ? fmt(p.Is * 1e6) + ' µA' : p.Is >= 1e-9 ? fmt(p.Is * 1e9) + ' nA' : p.Is.toExponential(2) + ' A') + ', n = ' + fmt(p.nD) + (SAMPLE ? ' (' + (PART || MAT) + ')' : ' (like a 1N4007)'),
      more: ['The ' + RTXT + ' resistor in series limits the current. The milliammeter is in series with the diode; the voltmeter is across the diode only. In this lab the knee voltage V_K is read as the diode voltage at which the current reaches 10 mA.'],
      precautions: 'Start with the knob at zero. Raise the voltage in small steps; take more readings near the knee. Never exceed the milliammeter range. Switch off when done.' },
    book: { title: 'Expt. — p-n Junction Diode (forward bias)', lines: ['Aim: forward I–V characteristic and knee voltage.', 'Diode: ' + (SAMPLE || '1N4007 (Si)') + ',  series R = ' + RTXT, 'Milliammeter 0–25 mA,  Voltmeter 0–' + VMAX + ' V (LC ' + VLC + ' V)', 'Knee voltage V_K: V at I = 10 mA (from graph)', 'Precautions: start at 0 V, small steps near the knee.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'V (V)', get: function (r) { return fV(r.V); } }, { label: 'I (mA)', get: function (r) { return r.I.toFixed(1); } }] },
    graph: { x: function (r) { return r.V; }, y: function (r) { return r.I; }, xlabel: 'V (V)', ylabel: 'I (mA)', x0: 0, y0: 0,
      line: function (pts) { var q = pts.slice().sort(function (a, b) { return a[0] - b[0]; }), ymax = Math.max.apply(null, q.map(function (z) { return z[1]; })) * 1.08;
        return function (x) { if (x <= q[0][0]) return Math.max(0, q[0][1]); for (var i = 0; i < q.length - 1; i++) if (x <= q[i + 1][0]) { var a = q[i], b = q[i + 1]; return b[0] === a[0] ? b[1] : a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]); }
          var u = q[q.length - 2], w = q[q.length - 1]; return Math.min(ymax, w[0] === u[0] ? w[1] : w[1] + (w[1] - u[1]) * (x - w[0]) / (w[0] - u[0])); }; } },
    result: function (rows) { var b = bracket(rows); if (!b) return null; var a = b[0], c = b[1], V = a[0] + (c[0] - a[0]) * (I_REF_MA - a[1]) / (c[1] - a[1]);
      return { label: 'Knee voltage V_K', value: V, unit: 'V', digits: 3, truth: TRUTH, note: 'Diode voltage where I = 10 mA, read between your two nearest readings.' }; },
    tol: 0.02,
    resultNote: 'The curve stays almost flat until about ' + LOWV + ' V, then rises steeply: this is the knee. A silicon diode conducts at about 0.6–0.7 V; germanium at about 0.2–0.3 V.',
    chips: ['Why is the current zero at first?', 'What is the knee voltage?', 'Why the series resistor?', 'Check my readings', 'What happens in reverse bias?'],
    viva: [['Which end of the diode is marked by the silver band?', ['The cathode (n-side)', 'The anode (p-side)', 'Neither, it is decoration'], 0, 'The band marks the cathode. For forward bias the cathode goes to the negative terminal.'],
      ['Why is the milliammeter in series and the voltmeter in parallel with the diode?', ['To measure the current through it and the voltage across it', 'To protect the supply', 'Both must be in series'], 0, 'An ammeter must carry the same current; a voltmeter must sit across the two points.']],
    askState: function () { return { supply_on: st.power, supply_setting_V: +st.set.toFixed(2), diode_voltage_V: readV(), current_mA: readI(), readings_taken: S.rows.length,
      diode: (SAMPLE || '1N4007 silicon') + ', forward bias', series_resistor_ohm: p.Rs, supply_max_V: EMAX, voltmeter_range_V: VMAX }; },

    steps: [
      { id: 'setup', title: 'Set up', view: 'board', render: function (u) {
          u.h2('Check the circuit and switch on');
          u.p('Supply (+) → ' + RTXT + ' resistor → milliammeter → diode anode (A) → cathode (K, silver band) → supply (−). The voltmeter is across the diode.');
          u.task('1. Check the diode is in forward bias', st.checked, st.checked ? 'Anode to the + side, band (cathode) to the − side' : 'Look at the silver band')
            .add(u.button(st.checked ? 'Checked' : 'Check the diode polarity', function () { st.checked = true; S.focus('dio'); S.say(LED ? 'The LED\'s flat side (cathode) is at K, wired to the supply’s negative. The anode A goes to + through the milliammeter: forward bias.' : 'The ' + (GLASS ? 'black' : 'silver') + ' band (cathode) is at K, wired to the supply’s negative. The anode A goes to + through the milliammeter: forward bias.'); S.render(); }, !st.checked, st.checked));
          u.task('2. Knob at zero, then switch on', st.power, st.power ? 'Supply on, knob at ' + st.set.toFixed(2) + ' V' : 'The hand presses the POWER rocker')
            .add(u.row(u.button(st.power ? 'Switch off' : 'Switch on the supply', function () { S.focus('psu'); togglePower(!st.power); }, !st.power, S.hand.busy),
              u.button('Knob to zero', function () { S.focus('psu'); turnTo(0); }, false, S.hand.busy || st.set === 0)));
          u.note('Always start at zero volts. A diode switched on at a high voltage takes a large current at once.');
          u.next('Next: take readings', st.checked && st.power);
        },
        ok: function () { return st.checked && st.power; },
        auto: function () { st.checked = true; return turnTo(0).then(function () { return togglePower(true); }); } },
      { id: 'read', title: 'Readings', view: 'bench', render: function (u) {
          u.h2('Raise the voltage and record V and I');
          u.p('Choose a setting, let the hand turn the VOLTAGE knob, then read both meters. Take small steps ' + (SAMPLE ? 'where the current starts to rise (for a ' + MAT + ' diode, near ' + (MAT === 'germanium' || MAT === 'Schottky' ? '0.1-0.35 V' : MAT === 'LED' ? '1.5-3 V' : '0.5-0.8 V') + ' on the voltmeter).' : 'between 0.5 V and 0.8 V on the voltmeter, where the current starts to rise.'));
          var target = { v: Math.min(EMAX, round(st.set + 0.1, 2)) };
          u.slider('Set the supply to', 0, EMAX, 0.05, function () { return target.v; }, function (v) { target.v = v; }, 'V', 2);
          u.row(u.button('Turn the knob', function () { if (!st.power) { S.say('Switch the supply on first (step 1).'); return; } turnTo(target.v); }, true, S.hand.busy),
            u.button('Record V and I', function () { record(); }, false, S.hand.busy));
          u.live(function () { return 'Voltmeter ' + fV(readV()) + ' V  ·  Milliammeter ' + readI().toFixed(1) + ' mA'; });
          u.h3('Observation table'); u.table();
          var b = bracket(S.rows);
          if (S.rows.length < 8) u.p(S.rows.length + ' of at least 8 readings recorded (10 or more is better).');
          else if (!b) u.note('Take readings on both sides of 10 mA, so the knee voltage can be read from the graph.');
          u.next('Next: plot the characteristic', enough());
        },
        ok: function () { return enough(); },
        auto: function () { var list = [0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.3, 1.6, 1.8, 2.2, 2.6, 3.0].map(function (E) { return E * EMAX / 3; });
          return list.reduce(function (pr, E) { return pr.then(function () { return turnTo(E).then(record); }); }, Promise.resolve()); } },
    ],

    tick: function () {
      mA.set(now.I * 1000); vm.set(now.V);
      if (dio.userData.led) dio.userData.led.emissiveIntensity = Math.min(2.5, now.I * 1000 / 8);
      hudE.set(st.power ? st.set.toFixed(2) + ' V' : 'off'); hudV.set(fV(readV()) + ' V'); hudI.set(readI().toFixed(1) + ' mA');
    },
  };
});
