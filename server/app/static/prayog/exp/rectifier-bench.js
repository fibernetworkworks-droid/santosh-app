/* Prayogshala studio rig `rectifier-bench`: the power-supply bench - an enclosed bench transformer with a
   centre-tapped low-voltage secondary, a board of four rectifier diodes, the filter capacitor on a link, a load
   resistance box, a true-RMS digital multimeter and an oscilloscope whose screen is drawn from the simulation.
   Physics: the `rectifier` kernel from packs/elec_ug.js on the lab's own params. The DC reading is the mean of the
   output over one cycle and the AC reading is the RMS of the ripple alone, which is exactly what a true-RMS meter
   on DC volts and on AC volts shows; the trace on the screen is the same waveform those averages are taken from.
   Safety: only the low-voltage secondary is ever handled. The mains side is inside the transformer's case. */
HoolaStudio.define('rectifier-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KK = HK.K.rectifier, p = HK.paramsFor('rectifier', S.lab.params);
  var KIND = Math.round(p.kind), CFIL = p.C;
  var KNAME = KIND === 1 ? 'half-wave' : KIND === 2 ? 'full-wave, centre tap' : 'bridge';
  var NDIODE = KIND === 1 ? 1 : KIND === 2 ? 2 : 4;
  var LOADS = [p.RL, Math.round(p.RL / 2), Math.round(p.RL / 5), Math.round(p.RL * 2)];

  function fmt(v, d) { return (isFinite(v) ? v : 0).toFixed(d); }
  function round(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function ohm(r) { return r >= 1000 ? String(+(r / 1000).toFixed(1)) + ' kΩ' : String(Math.round(r)) + ' Ω'; }
  function wpos(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function arr(v) { return [v.x, v.y, v.z]; }

  var st = { power: false, checked: false, load: 0, func: 'DC V' };
  function q() { return assign(p, { RL: LOADS[st.load] }); }

  // ---------- the measurement: the kernel's own averages, which is what the meter reads
  var CACHE = {};
  function stats() {
    var key = st.load;
    if (!CACHE[key]) CACHE[key] = KK.measure(q());
    return CACHE[key];
  }
  // one settled waveform, two cycles of it, for the screen
  var TRACE = {};
  function trace() {
    var key = st.load;
    if (TRACE[key]) return TRACE[key];
    var qq = q(), h = 1 / (qq.f * 2000), s = KK.init(qq, null), i, out = [];
    for (i = 0; i < 40 * 2000; i++) KK.step(s, qq, h, null);
    for (i = 0; i < 800; i++) {
      out.push([KK.view(s, qq, null).V_o, qq.Vp * Math.sin(2 * Math.PI * qq.f * s.t)]);
      KK.step(s, qq, h * 5, null);
    }
    TRACE[key] = out;
    return out;
  }
  var VDIV = (function () { var pk = p.Vp, d = [0.5, 1, 2, 5, 10], i;
    for (i = 0; i < d.length; i++) if (pk / d[i] <= 4.2) return d[i];
    return 10; })();

  // =============================================================================================== apparatus
  // ---------- enclosed bench transformer
  var tx = new T.Group(); S.scene.add(tx); tx.position.set(-0.4, 0, -0.26); tx.rotation.y = 0.28;
  var TXW = 0.17, TXD = 0.14, TXH = 0.11;
  var txCase = S.rounded(TXW, TXD, TXH, 0.01, new T.MeshStandardMaterial({ color: 0x3a4049, roughness: 0.55 }));
  txCase.rotation.x = -Math.PI / 2; txCase.position.y = TXH / 2 + 0.003; tx.add(txCase);
  var txTex = S.canvasTex(760, 500, function (x, w, h) {
    x.fillStyle = '#2a2f37'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 4; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.font = '700 40px "Public Sans", sans-serif'; x.fillText('BENCH TRANSFORMER', 32, 70);
    x.font = '500 26px "Public Sans", sans-serif'; x.fillStyle = '#c0c6d0';
    x.fillText('230 V primary, ENCLOSED  ·  secondary 0 – 9 – 18 V', 32, 110);
    x.fillText('safety isolated  ·  do not open the case', 32, 146);
    x.font = '700 30px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8';
    x.fillText('SECONDARY', 32, 232); x.textAlign = 'center';
    x.fillStyle = '#ff7a6b'; x.fillText('A', 160, 330); x.fillStyle = '#9aa3b2'; x.fillText('CT', 330, 330);
    x.fillStyle = '#ff7a6b'; x.fillText('B', 500, 330);
    x.textAlign = 'left';
  });
  var txTop = new T.Mesh(new T.PlaneGeometry(TXW - 0.01, TXD - 0.01), new T.MeshStandardMaterial({ map: txTex, roughness: 0.6 }));
  txTop.rotation.x = -Math.PI / 2; txTop.position.set(0, TXH + 0.0038, 0); tx.add(txTop);
  [-0.045, 0, 0.045].forEach(function (dx, i) {
    var g = new T.Group(); g.position.set(dx, TXH + 0.004, 0.025); tx.add(g);
    var stem = S.mesh(new T.CylinderGeometry(0.0026, 0.0026, 0.012, 12), M.brass); stem.position.y = 0.006; g.add(stem);
    var cap = S.mesh(new T.CylinderGeometry(0.006, 0.0068, 0.009, 18), i === 1 ? M.blackPlastic : M.red);
    cap.position.y = 0.014; g.add(cap);
  });
  var mains = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.3, 10), new T.MeshStandardMaterial({ color: 0x1a1a1c, roughness: 0.7 }));
  mains.rotation.z = Math.PI / 2; mains.position.set(-0.24, 0.004, -0.06); S.scene.add(mains);
  var txRocker = S.rounded(0.016, 0.022, 0.008, 0.003, M.bakelite);
  txRocker.position.copy(wpos(tx, 0.058, TXH + 0.006, -0.04)); S.scene.add(txRocker);
  var txMark = S.mesh(new T.BoxGeometry(0.0018, 0.001, 0.009), M.white, false); txMark.position.set(0, 0.0045, -0.004); txRocker.add(txMark);
  var pilotM = new T.MeshStandardMaterial({ color: 0x5a1410, roughness: 0.3 });
  var pilot = S.mesh(new T.SphereGeometry(0.005, 18, 12), pilotM);
  pilot.position.copy(wpos(tx, 0.058, TXH + 0.008, 0.0)); S.scene.add(pilot);
  function setPowerLook() {
    txRocker.rotation.x = st.power ? -0.3 : 0.3;
    pilotM.color.setHex(st.power ? 0xff3b2a : 0x5a1410);
    pilotM.emissive.setHex(st.power ? 0xff2a14 : 0x000000);
    pilotM.emissiveIntensity = st.power ? 2.0 : 0;
  }
  setPowerLook();
  S.contact(0.26, 0.22, tx.position.x, tx.position.z, 0.55);

  // ---------- diode board
  var BW = 0.27, BD = 0.13, BT = 0.012, BX = 0.0, BZ = -0.02;
  var boardTex = S.canvasTex(1300, 620, function (x, w, h) {
    x.fillStyle = '#ece5d2'; x.fillRect(0, 0, w, h);
    x.strokeStyle = '#7d6f55'; x.lineWidth = 4; x.strokeRect(14, 14, w - 28, h - 28);
    x.fillStyle = '#3d3528'; x.textAlign = 'center';
    x.font = '700 40px "Public Sans", sans-serif'; x.fillText('RECTIFIER BOARD  ·  4 × 1N4007', w / 2, 62);
    x.font = '600 30px "Public Sans", sans-serif';
    x.fillText('WIRED AS: ' + KNAME.toUpperCase() + '  (' + NDIODE + ' diode' + (NDIODE > 1 ? 's' : '') + ' in use)', w / 2, 104);
    // four diode symbols
    [[0.26, 0.42], [0.58, 0.42], [0.26, 0.74], [0.58, 0.74]].forEach(function (c, i) {
      var cx = c[0] * w, cy = c[1] * h, on = i < NDIODE;
      x.strokeStyle = on ? '#3d3528' : '#b3a98f'; x.fillStyle = on ? '#3d3528' : '#b3a98f'; x.lineWidth = 5;
      x.beginPath(); x.moveTo(cx - 64, cy); x.lineTo(cx + 64, cy); x.stroke();
      x.beginPath(); x.moveTo(cx - 20, cy - 24); x.lineTo(cx - 20, cy + 24); x.lineTo(cx + 20, cy); x.closePath(); x.fill();
      x.fillRect(cx + 20, cy - 26, 6, 52);
      x.font = '700 26px "Public Sans", sans-serif'; x.fillText('D' + (i + 1), cx, cy - 40);
    });
    x.fillStyle = '#3d3528'; x.font = '700 28px "Public Sans", sans-serif';
    x.fillText('C', 0.86 * w, 0.42 * h); x.fillText('R_L', 0.86 * w, 0.74 * h);
    x.textAlign = 'left';
  });
  var bb = S.rounded(BW, BD, BT, 0.005, new T.MeshStandardMaterial({ color: 0xe9e2cf, roughness: 0.7 }));
  bb.rotation.x = -Math.PI / 2; bb.position.set(BX, BT / 2, BZ); S.scene.add(bb);
  var bbTop = new T.Mesh(new T.PlaneGeometry(BW - 0.008, BD - 0.008), new T.MeshStandardMaterial({ map: boardTex, roughness: 0.75 }));
  bbTop.rotation.x = -Math.PI / 2; bbTop.position.set(BX, BT + 0.0004, BZ); S.scene.add(bbTop);
  S.contact(BW + 0.08, BD + 0.08, BX, BZ, 0.5);
  var LY = BT + 0.006;

  // real diode bodies on brass terminals
  var diodes = new T.Group(); S.scene.add(diodes);
  [[-0.063, -0.03], [0.022, -0.03], [-0.063, 0.03], [0.022, 0.03]].forEach(function (c, i) {
    var g = new T.Group(); diodes.add(g); g.position.set(BX + c[0], LY, BZ + c[1]);
    var dim = i >= NDIODE;
    var dTex = S.canvasTex(160, 420, function (x, w, h) {
      x.fillStyle = dim ? '#2a2a2e' : '#141416'; x.fillRect(0, 0, w, h);
      x.fillStyle = '#c9ccd0'; x.fillRect(0, h * 0.06, w, h * 0.16);
      x.save(); x.translate(w * 0.5, h * 0.62); x.rotate(Math.PI / 2);
      x.fillStyle = '#9da3aa'; x.font = '700 52px "Public Sans", sans-serif'; x.textAlign = 'center';
      x.fillText('1N4007', 0, 18); x.restore();
    });
    var body = S.mesh(new T.CylinderGeometry(0.0024, 0.0024, 0.0098, 24), new T.MeshStandardMaterial({ map: dTex, roughness: 0.35 }));
    body.rotation.z = Math.PI / 2; g.add(body);
    [-1, 1].forEach(function (sg) {
      var ld = S.mesh(new T.CylinderGeometry(0.00045, 0.00045, 0.011, 8), M.chrome, false);
      ld.rotation.z = Math.PI / 2; ld.position.x = sg * 0.0104; g.add(ld);
      var dn = S.mesh(new T.CylinderGeometry(0.00045, 0.00045, 0.007, 8), M.chrome, false);
      dn.position.set(sg * 0.0155, -0.0035, 0); g.add(dn);
      S.terminal([BX + c[0] + sg * 0.0155, BT, BZ + c[1]], 'brass');
    });
  });

  // electrolytic capacitor on a link, and the load box
  var cap = new T.Group(); S.scene.add(cap); cap.position.set(BX + 0.1, BT, BZ - 0.03);
  var capTex = S.canvasTex(420, 560, function (x, w, h) {
    x.fillStyle = '#1b2d6b'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#d8dce6'; x.fillRect(0, 0, w * 0.22, h);
    x.fillStyle = '#9aa6c4'; x.font = '700 44px "Public Sans", sans-serif'; var i;
    for (i = 0; i < 8; i++) x.fillText('−', w * 0.08, 70 + i * 66);
    x.fillStyle = '#f1efe8'; x.font = '700 60px "Public Sans", sans-serif';
    x.fillText(CFIL > 0 ? String(Math.round(CFIL * 1e6)) + 'µF' : 'OUT', w * 0.3, h * 0.42);
    x.font = '600 40px "Public Sans", sans-serif'; x.fillText('35 V', w * 0.3, h * 0.56);
  });
  var canM = new T.MeshStandardMaterial({ map: capTex, roughness: 0.4 });
  var can = S.mesh(new T.CylinderGeometry(0.0115, 0.0115, 0.028, 28), [canM, new T.MeshStandardMaterial({ color: 0xb9bfcc, roughness: 0.4 }), new T.MeshStandardMaterial({ color: 0x16254f, roughness: 0.45 })]);
  can.position.y = 0.014; cap.add(can);
  [-1, 1].forEach(function (sg) {
    var ld = S.mesh(new T.CylinderGeometry(0.0005, 0.0005, 0.008, 8), M.chrome, false);
    ld.position.set(sg * 0.004, -0.004, 0); cap.add(ld);
  });
  var linkG = new T.Group(); S.scene.add(linkG); linkG.position.set(BX + 0.1, BT + 0.002, BZ - 0.058);
  var link = S.mesh(new T.BoxGeometry(0.018, 0.0022, 0.0035), M.brass);
  link.position.y = 0.0011; linkG.add(link);
  link.visible = CFIL > 0;
  S.terminal([BX + 0.092, BT, BZ - 0.058], 'brass'); S.terminal([BX + 0.108, BT, BZ - 0.058], 'brass');

  var loadBox = new T.Group(); S.scene.add(loadBox); loadBox.position.set(BX + 0.19, 0, BZ + 0.01);
  var lbCase = S.rounded(0.1, 0.08, 0.045, 0.008, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 }));
  lbCase.rotation.x = -Math.PI / 2; lbCase.position.y = 0.0245; loadBox.add(lbCase);
  var lbTex = S.liveTex(520, 420);
  var lbTop = new T.Mesh(new T.PlaneGeometry(0.094, 0.074), new T.MeshStandardMaterial({ map: lbTex, roughness: 0.55 }));
  lbTop.rotation.x = -Math.PI / 2; lbTop.position.set(0, 0.0472, 0); loadBox.add(lbTop);
  var lbKnob = new T.Group(); lbKnob.position.set(0, 0.048, 0.012); loadBox.add(lbKnob);
  var lbK = S.mesh(new T.CylinderGeometry(0.013, 0.014, 0.011, 28), new T.MeshStandardMaterial({ color: 0x1b1d22, roughness: 0.45 }));
  lbK.position.y = 0.0055; lbKnob.add(lbK);
  var lbM = S.mesh(new T.BoxGeometry(0.0018, 0.0012, 0.013), M.white, false); lbM.position.set(0, 0.0112, 0.007); lbKnob.add(lbM);
  function drawLoad() {
    lbTex.draw(function (x, w, h) {
      x.fillStyle = '#272b33'; x.fillRect(0, 0, w, h);
      x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 4; x.strokeRect(10, 10, w - 20, h - 20);
      x.fillStyle = '#f1efe8'; x.font = '700 38px "Public Sans", sans-serif'; x.textAlign = 'center';
      x.fillText('LOAD', w / 2, 62);
      x.font = '700 54px "JetBrains Mono", monospace'; x.fillStyle = '#ffd37a';
      x.fillText(ohm(LOADS[st.load]), w / 2, 136);
      x.font = '600 26px "Public Sans", sans-serif'; x.fillStyle = '#b9c0cb';
      x.fillText('2 W wirewound  ·  ' + LOADS.length + ' steps', w / 2, 176);
      x.textAlign = 'left';
    });
  }
  drawLoad();
  function setLoadLook() { lbKnob.rotation.y = -1.4 * st.load; drawLoad(); }
  setLoadLook();
  S.contact(0.15, 0.13, loadBox.position.x, loadBox.position.z, 0.5);

  // ---------- true-RMS multimeter with a function switch the hand turns
  var dmm = new T.Group(); S.scene.add(dmm); dmm.position.set(-0.22, 0, -0.33); dmm.rotation.y = 0.3;
  var DW = 0.14, DD = 0.17, DH = 0.052;
  var dbody = S.rounded(DW, DD, DH, 0.01, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 }));
  dbody.rotation.x = -Math.PI / 2; dbody.position.y = DH / 2 + 0.002; dmm.add(dbody);
  var dboot = S.rounded(DW + 0.012, DD + 0.012, 0.012, 0.012, new T.MeshStandardMaterial({ color: 0xd9682a, roughness: 0.8 }));
  dboot.rotation.x = -Math.PI / 2; dboot.position.y = 0.007; dmm.add(dboot);
  var FUNCS = ['OFF', 'DC V', 'AC V', 'Hz'];
  var lcd = S.liveTex(640, 260);
  var dface = new T.Group(); dface.rotation.x = -0.5; dface.position.set(0, DH + 0.004, 0); dmm.add(dface);
  var dplate = S.canvasTex(700, 900, function (x, w, h) {
    x.fillStyle = '#30353d'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#f1efe8'; x.font = '700 32px "Public Sans", sans-serif'; x.textAlign = 'center';
    x.fillText('TRUE-RMS MULTIMETER', w / 2, 54);
    x.font = '500 24px "Public Sans", sans-serif'; x.fillStyle = '#aab1bc';
    x.fillText('AC volts shows the ripple alone', w / 2, 90);
    x.strokeStyle = '#8d949f'; x.lineWidth = 4; x.beginPath(); x.arc(w / 2, h * 0.63, 150, 0, Math.PI * 2); x.stroke();
    x.font = '700 30px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8';
    FUNCS.forEach(function (t, i) {
      var a = -Math.PI / 2 + (i - 1.5) * 0.7;
      x.fillText(t, w / 2 + Math.cos(a) * 196, h * 0.63 + Math.sin(a) * 196 + 10);
    });
    x.fillStyle = '#ff7a6b'; x.beginPath(); x.arc(w * 0.68, h * 0.95, 26, 0, Math.PI * 2); x.fill();
    x.fillStyle = '#1b1b1b'; x.beginPath(); x.arc(w * 0.32, h * 0.95, 26, 0, Math.PI * 2); x.fill();
    x.textAlign = 'left';
  });
  var dpf = new T.Mesh(new T.PlaneGeometry(0.128, 0.165), new T.MeshStandardMaterial({ map: dplate, roughness: 0.5 }));
  dpf.position.set(0, 0, 0.0005); dface.add(dpf);
  var dscr = new T.Mesh(new T.PlaneGeometry(0.1, 0.041), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
  dscr.position.set(0, 0.052, 0.0012); dface.add(dscr);
  var dbez = S.mesh(new T.BoxGeometry(0.108, 0.048, 0.002), new T.MeshStandardMaterial({ color: 0x15171b, roughness: 0.5 }), false);
  dbez.position.set(0, 0.052, 0.0002); dface.add(dbez);
  var fsw = new T.Group(); fsw.position.set(0, -0.004, 0.0015); dface.add(fsw);
  var fk = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.006, 30), new T.MeshStandardMaterial({ color: 0x1b1d22, roughness: 0.45 }));
  fk.rotation.x = Math.PI / 2; fk.position.z = 0.003; fsw.add(fk);
  var fkm = S.mesh(new T.BoxGeometry(0.0028, 0.016, 0.001), M.white, false); fkm.position.set(0, 0.009, 0.0065); fsw.add(fkm);
  var dred = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.006, 18), M.red); dred.rotation.x = Math.PI / 2; dred.position.set(0.018, -0.0655, 0.003); dface.add(dred);
  var dblk = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.006, 18), M.blackPlastic); dblk.rotation.x = Math.PI / 2; dblk.position.set(-0.018, -0.0655, 0.003); dface.add(dblk);
  function setFuncLook() { fsw.rotation.z = -(FUNCS.indexOf(st.func) - 1.5) * 0.7; }
  setFuncLook();
  S.contact(0.19, 0.22, dmm.position.x, dmm.position.z, 0.5);
  var lcdLast = '';
  function meterRead() {
    var m = stats();
    if (!st.power) return 0;
    return st.func === 'DC V' ? round(m.V_dc / 0.001, 0) * 0.001 : st.func === 'AC V' ? round(m.V_ac / 0.0001, 0) * 0.0001 : 2 * p.f / (KIND === 1 ? 2 : 1);
  }
  function drawLcd() {
    var txt = !st.power ? '— — —' : st.func === 'OFF' ? '' : st.func === 'Hz' ? fmt(meterRead(), 1) : fmt(meterRead(), st.func === 'AC V' ? 4 : 3);
    var key = txt + '|' + st.func + '|' + st.power;
    if (key === lcdLast) return;
    lcdLast = key;
    lcd.draw(function (x, w, h) {
      var gr = x.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#c3ccb0'); gr.addColorStop(1, '#a3b092');
      x.fillStyle = gr; x.fillRect(0, 0, w, h);
      if (st.func === 'OFF') { x.fillStyle = '#6e7a62'; x.font = '600 44px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText('OFF', w / 2, h / 2 + 16); return; }
      x.font = '700 106px "JetBrains Mono", monospace'; x.textAlign = 'right';
      x.fillStyle = 'rgba(0,0,0,.07)'; x.fillText('8.8888', w - 150, 158);
      x.fillStyle = '#171d13'; x.fillText(txt, w - 150, 158);
      x.textAlign = 'left'; x.font = '700 42px "Public Sans", sans-serif';
      x.fillText(st.func === 'Hz' ? 'Hz' : 'V', w - 140, 158);
      x.font = '600 30px "Public Sans", sans-serif'; x.fillStyle = '#2c3526';
      x.fillText(st.func === 'AC V' ? 'AC  TRUE RMS' : st.func === 'DC V' ? 'DC' : 'FREQ', 24, 52);
    });
  }

  // ---------- oscilloscope, with a screen drawn from the simulated waveform
  var cro = new T.Group(); S.scene.add(cro); cro.position.set(0.3, 0, -0.38); cro.rotation.y = -0.26;
  var CW = 0.3, CD = 0.24, CH = 0.2;
  var croCase = S.rounded(CW, CD, CH, 0.012, new T.MeshStandardMaterial({ color: 0xd9d5cb, roughness: 0.5 }));
  croCase.rotation.x = -Math.PI / 2; croCase.position.y = CH / 2 + 0.004; cro.add(croCase);
  var CFZ = CD / 2 + 0.006;
  var croTex = S.canvasTex(900, Math.round(900 * (CH - 0.014) / (CW - 0.014)), function (x, w, h) {
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(8, 8, w - 16, h - 16);
    x.fillStyle = '#f1efe8'; x.font = '700 28px "Public Sans", sans-serif'; x.fillText('OSCILLOSCOPE  20 MHz', 28, 46);
    x.font = '500 20px "Public Sans", sans-serif'; x.fillStyle = '#c0c6d0';
    x.fillText('CH1  DC coupled  ·  ' + VDIV + ' V / div  ·  5 ms / div', 28, 74);
    x.fillStyle = '#f1efe8'; x.font = '700 22px "Public Sans", sans-serif';
    x.fillText('VOLTS / DIV', w * 0.72, h - 112); x.fillText('TIME / DIV', w * 0.72, h - 42);
  });
  var croFas = S.mesh(new T.BoxGeometry(CW - 0.014, CH - 0.014, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: croTex, roughness: 0.45 }), M.grey]);
  croFas.position.set(0, CH / 2 + 0.004, CFZ - 0.002); cro.add(croFas);
  var scrTex = S.liveTex(900, 700);
  var scr = new T.Mesh(new T.PlaneGeometry(0.17, 0.132), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false }));
  scr.position.set(-0.044, CH / 2 + 0.008, CFZ + 0.0012); cro.add(scr);
  var scrBez = S.mesh(new T.BoxGeometry(0.182, 0.144, 0.003), new T.MeshStandardMaterial({ color: 0x15171b, roughness: 0.5 }), false);
  scrBez.position.set(-0.044, CH / 2 + 0.008, CFZ + 0.0002); cro.add(scrBez);
  [[0.062, -0.024], [0.062, -0.058]].forEach(function (c) {
    var k = S.mesh(new T.CylinderGeometry(0.013, 0.014, 0.012, 26), new T.MeshStandardMaterial({ color: 0x1b1d22, roughness: 0.45 }));
    k.rotation.x = Math.PI / 2; k.position.set(c[0], CH / 2 + 0.004 + c[1], CFZ + 0.006); cro.add(k);
    var mk = S.mesh(new T.BoxGeometry(0.0018, 0.012, 0.001), M.white, false);
    mk.position.set(c[0], CH / 2 + 0.004 + c[1] + 0.007, CFZ + 0.013); cro.add(mk);
  });
  S.contact(0.4, 0.34, cro.position.x, cro.position.z, 0.55);
  var scrLast = '';
  function drawScreen() {
    var key = st.power ? 'on' + st.load : 'off';
    if (key === scrLast) return;
    scrLast = key;
    var tr = st.power ? trace() : null, m = st.power ? stats() : null;
    scrTex.draw(function (x, w, h) {
      x.fillStyle = '#0b1410'; x.fillRect(0, 0, w, h);
      var i, gx, gy;
      x.strokeStyle = 'rgba(120,220,160,.18)'; x.lineWidth = 1;
      for (i = 0; i <= 10; i++) { gx = i * w / 10; x.beginPath(); x.moveTo(gx, 0); x.lineTo(gx, h); x.stroke(); }
      for (i = 0; i <= 8; i++) { gy = i * h / 8; x.beginPath(); x.moveTo(0, gy); x.lineTo(w, gy); x.stroke(); }
      x.strokeStyle = 'rgba(120,220,160,.4)'; x.lineWidth = 2;
      x.beginPath(); x.moveTo(0, h * 7 / 8); x.lineTo(w, h * 7 / 8); x.stroke();
      if (!tr) {
        x.fillStyle = '#5c7a68'; x.font = '600 34px "Public Sans", sans-serif'; x.textAlign = 'center';
        x.fillText('no signal', w / 2, h / 2); x.textAlign = 'left'; return;
      }
      // the output waveform: 0 V on the bottom-but-one graticule line, VDIV volts per division
      var y0 = h * 7 / 8, pxPerV = (h / 8) / VDIV;
      x.strokeStyle = 'rgba(140,255,190,.35)'; x.lineWidth = 2;
      x.beginPath();
      for (i = 0; i < tr.length; i++) {
        var xx = i / (tr.length - 1) * w, yy = y0 - tr[i][1] * pxPerV;
        if (i === 0) x.moveTo(xx, yy); else x.lineTo(xx, yy);
      }
      x.stroke();
      x.shadowColor = '#7dffb0'; x.shadowBlur = 14;
      x.strokeStyle = '#8affc0'; x.lineWidth = 4;
      x.beginPath();
      for (i = 0; i < tr.length; i++) {
        var x2 = i / (tr.length - 1) * w, y2 = y0 - tr[i][0] * pxPerV;
        if (i === 0) x.moveTo(x2, y2); else x.lineTo(x2, y2);
      }
      x.stroke(); x.shadowBlur = 0;
      x.setLineDash([8, 8]); x.strokeStyle = '#ffd37a'; x.lineWidth = 2;
      x.beginPath(); x.moveTo(0, y0 - m.V_dc * pxPerV); x.lineTo(w, y0 - m.V_dc * pxPerV); x.stroke();
      x.setLineDash([]);
      x.fillStyle = '#9affc8'; x.font = '600 26px "Public Sans", sans-serif';
      x.fillText(KNAME + (CFIL > 0 ? ', ' + Math.round(CFIL * 1e6) + ' µF filter' : ', no filter'), 18, 36);
      x.fillStyle = '#ffd37a'; x.fillText('mean ' + fmt(m.V_dc, 2) + ' V', 18, 68);
      x.fillStyle = '#8fd0ff'; x.fillText('peak-to-peak ripple ' + fmt(m.V_pp, 3) + ' V', 18, 100);
    });
  }
  drawScreen();

  // ---------- wiring
  var txA = wpos(tx, -0.045, TXH + 0.018, 0.025), txCT = wpos(tx, 0, TXH + 0.018, 0.025), txB = wpos(tx, 0.045, TXH + 0.018, 0.025);
  S.wire([arr(txA), [txA.x + 0.04, 0.04, txA.z + 0.05], [BX - 0.085, BT + 0.004, BZ - BD / 2 + 0.006]], 'red');
  S.wire([arr(txCT), [txCT.x + 0.05, 0.03, txCT.z + 0.08], [BX - 0.02, BT + 0.004, BZ + BD / 2 - 0.006]], 'black');
  if (KIND !== 1) S.wire([arr(txB), [txB.x + 0.05, 0.036, txB.z + 0.03], [BX - 0.085, BT + 0.004, BZ + BD / 2 - 0.006]], 'blue');
  S.wire([[BX + 0.05, BT + 0.004, BZ - BD / 2 + 0.006], [BX + 0.12, 0.03, BZ - 0.07], [loadBox.position.x - 0.03, 0.048, loadBox.position.z - 0.02]], 'red');
  S.wire([[BX + 0.05, BT + 0.004, BZ + BD / 2 - 0.006], [BX + 0.13, 0.02, BZ + 0.05], [loadBox.position.x - 0.03, 0.048, loadBox.position.z + 0.02]], 'black');
  var dmP = wpos(dmm, 0.018, DH + 0.004, -0.058), dmN = wpos(dmm, -0.018, DH + 0.004, -0.058);
  S.wire([arr(dmP), [dmP.x + 0.03, 0.03, dmP.z + 0.08], [BX + 0.06, BT + 0.004, BZ - BD / 2 + 0.006]], 'gold');
  S.wire([arr(dmN), [dmN.x + 0.02, 0.02, dmN.z + 0.1], [BX + 0.06, BT + 0.004, BZ + BD / 2 - 0.006]], 'black');
  var croIn = wpos(cro, -0.044 - 0.0, CH / 2 + 0.004 - 0.09, CFZ + 0.004);
  S.wire([[BX + 0.08, BT + 0.004, BZ - BD / 2 + 0.006], [BX + 0.18, 0.05, BZ - 0.16], arr(croIn)], 'blue');

  S.addApparatus('tx', tx, 'Bench transformer (enclosed, centre-tapped secondary)', 'The mains side is sealed inside the case and is never probed. Only the low-voltage secondary, 9 V either side of the centre tap, comes out to the terminals.');
  S.addApparatus('bb', bb, 'Rectifier board — wired as ' + KNAME, NDIODE + ' of the four 1N4007 diodes are in the circuit. Each conducting diode costs about 0.7 V, and the bridge has two of them in the path at any instant.');
  S.addApparatus('cap', cap, CFIL > 0 ? 'Filter capacitor ' + Math.round(CFIL * 1e6) + ' µF, 35 V' : 'Filter capacitor (out of the circuit)', 'An electrolytic capacitor across the load. The striped side is the negative lead; it must go in the right way round and be discharged before it is touched. The brass link puts it in or out of the circuit.');
  S.addApparatus('load', loadBox, 'Load resistance box', 'Four wirewound steps. A heavier load (smaller resistance) takes more current, so a filtered supply droops and its ripple grows.');
  S.addApparatus('dmm', dmm, 'True-RMS digital multimeter', 'On DC volts it shows the average of the output; on AC volts it shows the RMS of the ripple alone. The ripple factor is one divided by the other.');
  S.addApparatus('cro', cro, 'Oscilloscope', 'The output waveform against time, with the fainter trace showing the transformer secondary for comparison and the dashed line marking the mean.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudV = S.hudCard('Multimeter'), hudR = S.hudCard('Ripple factor'), hudL = S.hudCard('Load');

  // =============================================================================================== human actions
  function togglePower(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (on === st.power) return Promise.resolve();
    return S.hand.tap(txRocker, 'tap').then(function () {
      st.power = on; setPowerLook(); S.click(900, 0.05);
      S.say(on ? 'Transformer on. The waveform is on the screen.' : 'Transformer off.');
      S.render();
    });
  }
  function turnFunc(f) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (st.func === f) return Promise.resolve();
    var pt = wpos(dmm, 0, DH + 0.004, 0.012);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      var a0 = -(FUNCS.indexOf(st.func) - 1.5) * 0.7, a1 = -(FUNCS.indexOf(f) - 1.5) * 0.7;
      fsw.rotation.z = a0 + (a1 - a0) * k;
    }, { mode: 'front', ms: 420, reachMs: 520 }).then(function () { st.func = f; setFuncLook(); S.render(); });
  }
  function turnLoad(i) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (i === st.load) return Promise.resolve();
    var pt = new T.Vector3(loadBox.position.x, 0.062, loadBox.position.z + 0.012);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      lbKnob.rotation.y = -1.4 * (st.load + (i - st.load) * k);
    }, { mode: 'top', ms: 460, reachMs: 560 }).then(function () { st.load = i; setLoadLook(); S.render(); });
  }
  function measureHere() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!st.power) { S.say('Switch the transformer on first.'); return Promise.resolve(); }
    var i;
    for (i = 0; i < S.rows.length; i++) if (S.rows[i].RL === LOADS[st.load]) { S.say('This load is already in your record book. Turn the load knob to another step.'); return Promise.resolve(); }
    var m = stats();
    return turnFunc('DC V').then(function () {
      var vdc = meterRead();
      return turnFunc('AC V').then(function () {
        var vac = meterRead();
        var vpp = round(m.V_pp, 3);     // read off the screen on AC coupling, at a volts/div small enough to see the ripple
        S.addRow({ RL: LOADS[st.load], Vdc: vdc, Vac: vac, Vpp: vpp, r: vdc > 0 ? vac / vdc : 0 });
        S.say('Load ' + ohm(LOADS[st.load]) + ': DC ' + fmt(vdc, 3) + ' V, ripple ' + fmt(vac, 4) + ' V RMS.');
        S.render();
      });
    });
  }
  function enough() { return S.rows.length >= 3; }

  return {
    camera: { pos: [0.12, 0.66, 0.78], look: [0.02, 0.05, -0.2] },
    views: {
      tx: [[-0.34, 0.24, 0.0], [-0.4, 0.08, -0.24]], bb: [[0.0, 0.26, 0.2], [0.0, 0.01, -0.03]],
      cap: [[0.1, 0.1, 0.06], [0.1, 0.02, -0.05]], load: [[0.2, 0.16, 0.1], [0.19, 0.03, -0.01]],
      dmm: [[-0.2, 0.24, -0.02], [-0.22, 0.05, -0.32]], cro: [[0.26, 0.3, -0.02], [0.3, 0.12, -0.36]],
      bench: [[0.1, 0.5, 0.74], [0.02, 0.04, -0.22]], book: [[-0.42, 0.44, 0.52], [-0.5, 0.0, 0.08]],
    },
    theory: {
      principle: 'A rectifier turns alternating current into one-way current, but not into a steady voltage. ' +
        'This bench is wired as a ' + KNAME + ' rectifier' + (CFIL > 0 ? ' with a ' + Math.round(CFIL * 1e6) + ' µF capacitor filter' : ' with no filter') +
        '. What is left of the alternating input is the ripple, and the ripple factor is its RMS divided by the DC level.',
      formula: 'r = V_ac(rms) / V_dc' + (CFIL > 0 ? '' : ',   V_dc = ' + (KIND === 1 ? 'V_p/π' : '2V_p/π')),
      formulaNote: 'Secondary peak ' + fmt(p.Vp, 1) + ' V at ' + fmt(p.f, 0) + ' Hz; ' + NDIODE +
        ' conducting diode' + (NDIODE > 1 ? 's' : '') + ' at about ' + fmt(p.Vd, 1) + ' V each.',
      more: [S.lab.theory,
        'The multimeter does the arithmetic for you: on DC volts it averages the output over many cycles, and on ' +
        'AC volts a true-RMS meter blocks the DC and shows the RMS of what is left. Older average-reading meters ' +
        'are calibrated for a sine wave and read a saw-tooth ripple wrongly, which is why the meter on this bench ' +
        'says TRUE RMS on its front.'],
      precautions: S.lab.safety,
    },
    book: {
      title: 'Expt. — ' + S.lab.title,
      lines: ['Aim: ' + S.lab.aim,
        'Circuit: ' + KNAME + ' rectifier, ' + (CFIL > 0 ? Math.round(CFIL * 1e6) + ' µF capacitor filter' : 'no filter') + '.',
        'Transformer secondary: ' + fmt(p.Vp, 1) + ' V peak at ' + fmt(p.f, 0) + ' Hz.',
        'Meter: true RMS, DC volts to 1 mV and AC volts to 0.1 mV.',
        'Precautions: only the secondary is handled; switch off before rewiring; discharge the capacitor.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'R_L (Ω)', get: function (r) { return String(r.RL); } },
        { label: 'V_dc (V)', get: function (r) { return fmt(r.Vdc, 3); } },
        { label: 'V_ac rms (V)', get: function (r) { return fmt(r.Vac, 4); } },
        { label: 'V_pp, AC coupled (V)', get: function (r) { return fmt(r.Vpp, 3); } },
        { label: 'r = V_ac/V_dc', get: function (r) { return fmt(r.r, 4); } }],
      at: [-0.52, 0.1, 0.1],
    },
    graph: {
      x: function (r) { return r.RL; }, y: function (r) { return r.r; },
      xlabel: 'R_L (Ω)', ylabel: 'ripple factor', y0: 0,
      line: function (pts) {
        var qq = pts.slice().sort(function (a, b) { return a[0] - b[0]; });
        return function (x) {
          var i;
          if (x <= qq[0][0]) return qq[0][1];
          for (i = 0; i < qq.length - 1; i++) {
            if (x <= qq[i + 1][0]) {
              var a = qq[i], b = qq[i + 1];
              return b[0] === a[0] ? b[1] : a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]);
            }
          }
          return qq[qq.length - 1][1];
        };
      },
    },
    result: function (rows) {
      var i, r0 = null;
      for (i = 0; i < rows.length; i++) if (rows[i].RL === LOADS[0]) r0 = rows[i];
      if (!r0 || !r0.Vdc) return null;
      var m0 = KK.measure(assign(p, { RL: LOADS[0] }));
      return { label: 'Ripple factor at ' + ohm(LOADS[0]), value: r0.Vac / r0.Vdc, unit: '', digits: 5,
        truth: m0.ripple,
        note: 'From your own two readings at that load: ' + fmt(r0.Vac, 4) + ' V RMS of ripple on ' + fmt(r0.Vdc, 3) + ' V of DC.' };
    },
    tol: 0.03,
    resultNote: CFIL > 0
      ? 'With the capacitor in the circuit the output sits close to the peak and the ripple is a small saw-tooth, ' +
        'so the ripple factor is a fraction of a per cent. Load the supply more heavily and the capacitor ' +
        'discharges further between peaks: the DC level droops and the ripple grows, which is what your table shows.'
      : 'With no filter the ripple is enormous: a half-wave output is about 1.21 times its own DC level in ripple ' +
        'and a full-wave one about 0.48, because what is left after averaging a rectified sine is most of the ' +
        'waveform. That is why no real supply is used without a filter.',
    chips: ['Why does the capacitor cut the ripple?', 'What is the DC output here?',
      'Why is a true-RMS meter needed?', 'What happens with a heavier load?', 'Check my readings'],
    viva: [['The ripple factor of a supply is', ['the RMS of the ripple divided by the DC level',
      'the peak divided by the average', 'the ripple frequency divided by the mains frequency'], 0,
      'It is a pure ratio: how much hum rides on the DC.'],
      ['A full-wave rectifier gives twice the DC output of a half-wave one because',
        ['it uses both halves of every cycle', 'its diodes drop less', 'its ripple frequency is higher'], 0,
        'The average of a fully rectified sine is twice the average of one half alone.'],
      ['Making the load heavier (smaller R_L) in a filtered supply',
        ['lowers the DC level and raises the ripple', 'raises the DC level', 'changes nothing'], 0,
        'The capacitor discharges further between peaks, so it droops and the saw-tooth grows.']],
    askState: function () {
      var m = st.power ? stats() : null;
      return {
        transformer_on: st.power, rectifier: KNAME, diodes_in_use: NDIODE,
        filter: CFIL > 0 ? Math.round(CFIL * 1e6) + ' µF' : 'none',
        load_ohm: LOADS[st.load], meter_function: st.func,
        meter_reading: st.power ? round(meterRead(), 5) : 0,
        dc_output_V: m ? round(m.V_dc, 4) : 0, ripple_rms_V: m ? round(m.V_ac, 5) : 0,
        peak_to_peak_ripple_V: m ? round(m.V_pp, 4) : 0,
        readings_taken: S.rows.length,
      };
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'bb', render: function (u) {
          u.h2('Check the circuit and switch the transformer on');
          u.p('The board is wired as a ' + KNAME + ' rectifier using ' + NDIODE + ' of its four 1N4007 diodes' +
            (CFIL > 0 ? ', with the ' + Math.round(CFIL * 1e6) + ' µF capacitor linked across the load' : ', with the capacitor link open so there is no filter') + '.');
          u.task('1. Check the circuit and the capacitor\'s polarity', st.checked,
            st.checked ? 'Diodes and link in place; the striped lead is on the negative side' : 'Look over the board')
            .add(u.button(st.checked ? 'Checked' : 'Check the board', function () {
              st.checked = true; S.focus('cap');
              S.say(CFIL > 0 ? 'The link is closed, so the ' + Math.round(CFIL * 1e6) + ' µF capacitor is across the load, striped lead to the negative rail.'
                : 'The link is open: no filter, so the raw rectified waveform reaches the load.');
              S.render();
            }, !st.checked, st.checked));
          u.task('2. Switch the transformer on', st.power, st.power ? 'The waveform is on the screen' : 'The hand presses the rocker')
            .add(u.button(st.power ? 'Switch off' : 'Switch on the transformer', function () {
              S.focus('tx'); togglePower(!st.power);
            }, !st.power, S.hand.busy));
          if (st.power) u.row(u.button('Look at the oscilloscope', function () { S.focus('cro'); }, false, false));
          u.note('Only the low-voltage secondary is ever touched. The mains side stays inside the case, and the ' +
            'supply is switched off before anything is rewired.');
          u.next('Next: measure the output and the ripple', st.checked && st.power);
        },
        ok: function () { return st.checked && st.power; },
        auto: function () { st.checked = true; return togglePower(true); } },
      { id: 'read', title: 'Readings', view: 'bench', render: function (u) {
          u.h2('Read the DC level and the ripple at each load');
          u.p('For each step of the load box the hand turns the meter to DC volts and then to AC volts, so both ' +
            'the average output and the RMS of the ripple go into the record book. At least three loads are needed.');
          u.row.apply(u, LOADS.map(function (R, i) {
            return u.button(ohm(R), function () { turnLoad(i); }, i === st.load, S.hand.busy);
          }));
          u.row(u.button('Measure at this load', function () { measureHere(); }, true, S.hand.busy),
            u.button('Look at the screen', function () { S.focus('cro'); }, false, false));
          u.live(function () {
            var m = st.power ? stats() : null;
            return 'Load ' + ohm(LOADS[st.load]) + '  ·  meter on ' + st.func + ': ' +
              (st.power ? fmt(meterRead(), st.func === 'AC V' ? 4 : 3) + ' V' : '— — —') +
              (m ? '  ·  screen: mean ' + fmt(m.V_dc, 2) + ' V, ripple ' + fmt(m.V_pp, 3) + ' V peak to peak' : '');
          });
          u.h3('Observation table'); u.table();
          if (!enough()) u.p(S.rows.length + ' of at least 3 loads measured.');
          u.next('Next: work out the ripple factor', enough());
        },
        ok: function () { return enough(); },
        auto: function () {
          return LOADS.reduce(function (pr, R, i) {
            return pr.then(function () { return turnLoad(i); }).then(measureHere);
          }, Promise.resolve());
        } },
    ],

    tick: function () {
      drawLcd(); drawScreen();
      hudV.set(st.power ? fmt(meterRead(), st.func === 'AC V' ? 4 : 3) + ' V ' + st.func : 'off');
      var m = st.power ? stats() : null;
      hudR.set(m && m.V_dc > 0 ? fmt(m.V_ac / m.V_dc, 4) : '—');
      hudL.set(ohm(LOADS[st.load]));
    },
  };
});
