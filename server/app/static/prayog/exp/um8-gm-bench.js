/* Prayogshala studio RIG: the GM COUNTING BENCH of wave 8 (B.Sc. radiation physics).
   The lead castle with its shelf stand, an end-window GM tube and the scaler-timer serve two set-ups:
     um8-beta-absorption  a sealed Tl-204 beta source counted through aluminium foils of known areal density:
                          the mass absorption coefficient from ln(net rate), the range where the beta counts end;
     um8-k40-salt         a tray of a potassium salt under the tube: the count rate above background from K-40.
   Physics: the um8_beta / um8_k40 kernels of packs/ug_matter_w8.js - the same code the server checks. Counts are
   Poisson numbers from the lab's own seed (SIMULATED DATA); the dead time of the tube is corrected as N/(1 - N tau). */
HoolaStudio.define('um8-gm-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KNAME = S.lab.kernel, KN = HK.K[KNAME], BETA = KNAME === 'um8_beta';
  var p = HK.paramsFor(KNAME, S.lab.params);
  var V_ = S.lab.variant || {};
  var SRC = BETA ? (V_.sample || 'Sealed Tl-204 beta source') : (V_.sample || 'Potassium chloride (KCl), laboratory grade');
  var SALT = BETA ? '' : (/sulph/i.test(SRC) ? 'K₂SO₄' : /carbon/i.test(SRC) ? 'K₂CO₃' : 'KCl');
  var VMIN = 250, VMAX = 750, VSTEP = 10, VPLAT = 650;
  // foils of THIS source: a set reaching past its range, marked in mg/cm² as a real foil box is
  var RMG = BETA ? KN.rangeKP(p.E) * 1000 : 0;
  function foil(f) { return Math.round(RMG * f); }
  var COARSE = BETA ? [0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5].map(foil) : [];
  var FINE = BETA ? [0.86, 0.9, 0.93, 0.96, 0.98, 1.0, 1.02, 1.05, 1.1].map(foil) : [];
  var TAIL = BETA ? foil(1.5) : 0;
  var FOILS = COARSE.concat(FINE, [TAIL]);
  var T_FINE = 300, T_TAIL = 600;
  var st = { placed: false, V: 300, t: p.t, counting: false, count: 0, elapsed: 0, x: 0, bg: null, tail: null,
    idx: 0, done: {}, filled: false, reps: 0 };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function qAt(t) {
    if (BETA) return assign(p, { x: st.x / 1000, t: t, N0: st.placed ? p.N0 : 0.0, brem: st.placed ? p.brem : 0.0 });
    return assign(p, { t: t, on: st.filled ? 1.0 : 0.0 });
  }
  function drawCounts(t) { st.idx += 1; return KN.counts(qAt(t), st.idx); }
  function rateNow() { return KN.obsRate(qAt(st.t)); }
  function corr(n, t) { var r = n / t; return r / (1 - r * p.tau); }   // dead-time correction
  var castle = new T.Group(); S.scene.add(castle); castle.position.set(-0.26, 0, -0.14);
  var leadM = new T.MeshStandardMaterial({ color: 0x53565c, roughness: 0.72, metalness: 0.55 });
  function brick(x, y, z, w, h, d) { var b = S.rounded(w, d, h, 0.004, leadM); b.rotation.x = -Math.PI / 2;
    b.position.set(x, y + h / 2, z); castle.add(b); return b; }
  for (var r = 0; r < 4; r++) {                       // three walls of lead bricks, the front left open
    brick(-0.105, r * 0.045, 0, 0.05, 0.044, 0.22);
    brick(0.105, r * 0.045, 0, 0.05, 0.044, 0.22);
    brick(0, r * 0.045, -0.085, 0.16, 0.044, 0.05);
  }
  // a lintel across the back only: the castle is open at the front and the top, as a teaching one is, so the
  // tube and the source shelf can be seen
  var roof = brick(0, 0.18, -0.072, 0.26, 0.03, 0.095);
  var stand = new T.Group(); castle.add(stand);
  var sPost = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.17, 16), M.chrome); sPost.position.set(-0.052, 0.085, 0.05);
  stand.add(sPost);
  var sPost2 = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.17, 16), M.chrome); sPost2.position.set(0.052, 0.085, 0.05);
  stand.add(sPost2);
  var shelfY = [];
  for (var sh = 0; sh < 5; sh++) {
    var y = 0.03 + sh * 0.026; shelfY.push(y);
    var pl = S.mesh(new T.BoxGeometry(0.12, 0.0025, 0.07), M.alu); pl.position.set(0, y, 0.05); stand.add(pl);
    var hole = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.004, 20), new T.MeshStandardMaterial({ color: 0x1b1d20 }));
    hole.position.set(0, y + 0.0005, 0.05); stand.add(hole);
  }
  var base = S.rounded(0.18, 0.12, 0.01, 0.004, M.iron); base.rotation.x = -Math.PI / 2; base.position.set(0, 0.005, 0.05);
  stand.add(base);
  // the GM tube in its holder, window down
  var tubeG = new T.Group(); castle.add(tubeG); tubeG.position.set(0, 0.168, 0.05);
  var holder = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.03, 24), M.bakelite); holder.position.y = 0.018;
  tubeG.add(holder);
  var tubeM = new T.MeshStandardMaterial({ color: 0x9aa2ab, roughness: 0.32, metalness: 0.75 });
  var tubeB = S.mesh(new T.CylinderGeometry(0.0135, 0.0135, 0.05, 28), tubeM); tubeB.position.y = -0.016;
  tubeG.add(tubeB);
  var mica = S.mesh(new T.CylinderGeometry(0.0115, 0.0115, 0.0015, 28),
    new T.MeshStandardMaterial({ color: 0xd8d2bd, roughness: 0.5, transparent: true, opacity: 0.8 }));
  mica.position.y = -0.0415; tubeG.add(mica);
  var guard = S.mesh(new T.TorusGeometry(0.0125, 0.0015, 8, 28), tubeM); guard.rotation.x = Math.PI / 2;
  guard.position.y = -0.04; tubeG.add(guard);
  var tlbl = S.label('GM 10 mg/cm²', { w: 0.026, ratio: 0.3, color: '#2b2f36' });
  tlbl.position.set(0, -0.016, 0.0138); tubeG.add(tlbl);
  // the sealed source, its holder, and the lead pot it lives in
  var srcG = new T.Group(); S.scene.add(srcG);
  var srcDisc = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, 0.004, 24),
    new T.MeshStandardMaterial({ color: 0xb8322a, roughness: 0.4, metalness: 0.3 }));
  srcG.add(srcDisc);
  var srcRim = S.mesh(new T.TorusGeometry(0.0085, 0.0012, 8, 24), M.chrome); srcRim.rotation.x = Math.PI / 2;
  srcG.add(srcRim);
  var trefoil = S.canvasTex(128, 128, function (x, w, h) {
    x.fillStyle = '#f2d02a'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b1b1b';
    x.beginPath(); x.arc(w / 2, h / 2, 10, 0, Math.PI * 2); x.fill();
    for (var i = 0; i < 3; i++) { x.beginPath();
      x.arc(w / 2, h / 2, 46, i * 2.094 - 0.45, i * 2.094 + 0.45); x.arc(w / 2, h / 2, 18, i * 2.094 + 0.45, i * 2.094 - 0.45, true);
      x.closePath(); x.fill(); } });
  var trefM = new T.Mesh(new T.CircleGeometry(0.0082, 24), new T.MeshStandardMaterial({ map: trefoil, roughness: 0.6 }));
  trefM.rotation.x = -Math.PI / 2; trefM.position.y = 0.0021; srcG.add(trefM);
  var POT = new T.Vector3(0.0, 0.016, 0.16);
  srcG.position.copy(POT);
  var pot = new T.Group(); S.scene.add(pot); pot.position.set(0.0, 0, 0.16);
  var potB = S.mesh(new T.CylinderGeometry(0.03, 0.032, 0.03, 28), leadM); potB.position.y = 0.015; pot.add(potB);
  var potHole = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.022, 24), new T.MeshStandardMaterial({ color: 0x17181b }));
  potHole.position.y = 0.021; pot.add(potHole);
  var potLid = S.mesh(new T.CylinderGeometry(0.031, 0.031, 0.008, 28), leadM); potLid.position.set(0.055, 0.004, 0.02);
  pot.add(potLid);
  var potLbl = S.label('SEALED SOURCE STORE', { w: 0.05, ratio: 0.2, color: '#e8e8ea' });
  potLbl.rotation.x = -Math.PI / 2; potLbl.position.set(0.0, 0.0012, 0.215); S.scene.add(potLbl);
  // tongs
  var tongs = new T.Group(); S.scene.add(tongs); tongs.position.set(0.1, 0.004, 0.2); tongs.rotation.y = 0.4;
  [-1, 1].forEach(function (sg) {
    var armL = S.mesh(new T.BoxGeometry(0.17, 0.004, 0.005), M.chrome);
    armL.position.set(0, 0, sg * 0.006); armL.rotation.y = sg * 0.04; tongs.add(armL);
  });
  var hinge = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.016, 12), M.chrome); hinge.rotation.x = Math.PI / 2;
  hinge.position.set(0.06, 0, 0); tongs.add(hinge);
  S.contact(0.3, 0.26, -0.26, -0.14, 0.5);
  S.contact(0.1, 0.1, 0.0, 0.16, 0.45);

  // ================================================================ scaler - timer
  var unit = new T.Group(); S.scene.add(unit); unit.position.set(0.3, 0, -0.1); unit.rotation.y = -0.32;
  var UW = 0.36, UD = 0.24, UH = 0.13;
  var ucase = S.rounded(UW, UD, UH, 0.012, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5, metalness: 0.12 }));
  ucase.rotation.x = -Math.PI / 2; ucase.position.y = UH / 2 + 0.004; unit.add(ucase);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.004, 16), M.rubber);
    ft.position.set(f[0] * (UW / 2 - 0.02), 0.002, f[1] * (UD / 2 - 0.02)); unit.add(ft);
  });
  var FZ = UD / 2 + 0.0062, PW = UW - 0.014, PH = UH - 0.014, KX = 0.105, KY = -0.014;
  var uTex = S.canvasTex(1300, Math.round(1300 * PH / PW), function (x, w, h) {
    var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; }, k = w / PW;
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.font = '700 38px "Public Sans", sans-serif'; x.fillText('SCALER – TIMER', 32, 60);
    x.font = '500 24px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6';
    x.fillText('GM HIGH VOLTAGE ' + VMIN + ' – ' + VMAX + ' V  ·  PRESET TIME', 32, 96);
    var cx = X(KX), cy = Y(KY), R = 0.024 * k; x.strokeStyle = '#f1efe8'; x.fillStyle = '#f1efe8';
    for (var i = 0; i <= 25; i++) {
      var th = (225 - 270 * i / 25) * Math.PI / 180, big = i % 5 === 0;
      x.lineWidth = big ? 4 : 2; x.beginPath();
      x.moveTo(cx + Math.cos(th) * R, cy - Math.sin(th) * R);
      x.lineTo(cx + Math.cos(th) * (R + (big ? 20 : 11)), cy - Math.sin(th) * (R + (big ? 20 : 11))); x.stroke();
      if (big) { x.font = '600 20px "Public Sans", sans-serif'; x.textAlign = 'center';
        x.fillText(String(VMIN + (VMAX - VMIN) * i / 25), cx + Math.cos(th) * (R + 42), cy - Math.sin(th) * (R + 42) + 7); }
    }
    x.textAlign = 'center'; x.font = '700 24px "Public Sans", sans-serif'; x.fillText('E.H.T.  (VOLTS)', cx, Y(-0.048));
    x.fillText('COUNTS', X(-0.115), Y(0.042)); x.fillText('TIME (s)', X(-0.115), Y(-0.048));
    x.fillText('START', X(0.0), Y(-0.048)); x.fillText('RESET', X(0.04), Y(-0.048)); x.textAlign = 'left';
  });
  var ufac = S.mesh(new T.BoxGeometry(PW, PH, 0.004),
    [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: uTex, roughness: 0.45 }), M.grey]);
  ufac.position.set(0, 0.004 + UH / 2, FZ - 0.002); unit.add(ufac);
  function up(u, v, dz) { return new T.Vector3(u, 0.004 + UH / 2 + v, FZ + (dz || 0)); }
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  var knob = new T.Group(); knob.position.copy(up(KX, KY)); unit.add(knob);
  var skirt = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.004, 36), M.bakelite); skirt.rotation.x = Math.PI / 2;
  skirt.position.z = 0.002; knob.add(skirt);
  var kb = S.mesh(new T.CylinderGeometry(0.0145, 0.016, 0.016, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 }));
  kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; knob.add(kb);
  var kptr = S.mesh(new T.BoxGeometry(0.002, 0.016, 0.0012), M.white, false); kptr.position.set(0, 0.009, 0.0215);
  knob.add(kptr);
  function knobAngle(v) { return 3 * Math.PI / 4 - 1.5 * Math.PI * ((v - VMIN) / (VMAX - VMIN)); }
  knob.rotation.z = knobAngle(VMIN);
  var startB = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 20), M.green); startB.rotation.x = Math.PI / 2;
  startB.position.copy(up(0.0, -0.022, 0.004)); unit.add(startB);
  var resetB = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 20), M.grey); resetB.rotation.x = Math.PI / 2;
  resetB.position.copy(up(0.04, -0.022, 0.004)); unit.add(resetB);
  function lcd(cx, cy, wdt, hgt, big) {
    var tex = S.liveTex(512, 190), last = '';
    var bez = S.mesh(new T.BoxGeometry(wdt + 0.006, hgt + 0.006, 0.003), M.grey);
    bez.position.copy(up(cx, cy, 0.001)); unit.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(wdt, hgt), new T.MeshBasicMaterial({ map: tex, toneMapped: false }));
    scr.position.copy(up(cx, cy, 0.004)); unit.add(scr);
    return function (txt) {
      if (txt === last) return; last = txt;
      tex.draw(function (x) {
        var gr = x.createLinearGradient(0, 0, 0, 190); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
        x.fillStyle = gr; x.fillRect(0, 0, 512, 190);
        x.font = '700 ' + (big ? 100 : 88) + 'px "JetBrains Mono", monospace'; x.textAlign = 'right';
        x.fillStyle = 'rgba(0,0,0,.07)'; x.fillText(big ? '888888' : '8888', 460, 126);
        x.fillStyle = '#1b2116'; x.fillText(txt, 460, 126);
      });
    };
  }
  var showC = lcd(-0.115, 0.022, 0.11, 0.034, true), showT = lcd(-0.115, -0.022, 0.11, 0.034, false);
  showC('0'); showT('0');   // the displays read before the first tick
  S.contact(0.46, 0.32, 0.3, -0.1, 0.55);
  S.wire([[-0.26, 0.03, 0.0], [0.0, 0.02, 0.0], [0.2, 0.02, -0.04]], 'black');


  knob.rotation.z = knobAngle(st.V);
  S.addApparatus('castle', castle, 'Lead castle with the shelf stand',
    'Lead bricks keep the background down. The sample sits on the middle shelf, at a fixed distance below the tube, for every reading.');
  S.addApparatus('tube', tubeG, 'End-window GM tube',
    'A thin mica window lets beta particles in. Each particle that gets in starts an avalanche in the gas, and the scaler records one count. After each count the tube is dead for about 0.25 ms.');
  S.addApparatus('unit', unit, 'Scaler-timer', 'The knob sets the tube voltage; START counts for the preset time and then stops by itself.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var SH_Y = 0.03 + 3 * 0.026;                                     // the shelf above the source
  var MID_Y = 0.03 + 2 * 0.026;                                    // the middle shelf

  // ---------------------------------------------------------------- beta: the foil box and the foil on the shelf
  var absM = new T.MeshStandardMaterial({ color: 0xc3c8cf, roughness: 0.35, metalness: 0.7 });
  var foilG = new T.Group(); S.scene.add(foilG); foilG.position.set(-0.26, 0, -0.09);
  var foilM = S.mesh(new T.BoxGeometry(0.09, 0.0012, 0.055), absM);
  foilM.position.set(0, SH_Y + 0.0015, 0); foilG.add(foilM); foilM.visible = false;
  var fbox = new T.Group(); S.scene.add(fbox); fbox.position.set(0.12, 0, 0.17);
  var fboxB = S.rounded(0.15, 0.1, 0.016, 0.005, M.wood); fboxB.rotation.x = -Math.PI / 2; fboxB.position.y = 0.008; fbox.add(fboxB);
  for (var fi = 0; fi < 8; fi++) {
    var fl = S.mesh(new T.BoxGeometry(0.06, 0.0008, 0.04), absM);
    fl.position.set(-0.035 + (fi % 4) * 0.023, 0.0165 + fi * 0.0009, -0.022 + Math.floor(fi / 4) * 0.044); fl.rotation.y = 0.05 * fi;
    fbox.add(fl);
  }
  var fLbl = S.label('Al FOILS (mg/cm²)', { w: 0.07, ratio: 0.18, color: '#2b2f36' });
  fLbl.rotation.x = -Math.PI / 2; fLbl.position.set(0.12, 0.0012, 0.235); S.scene.add(fLbl);
  S.contact(0.2, 0.16, 0.12, 0.17, 0.45);

  // ---------------------------------------------------------------- K-40: the salt tray and the jar
  var trayG = new T.Group(); S.scene.add(trayG);
  var TRAY_STORE = new T.Vector3(0.0, 0.0, 0.16), TRAY_SHELF = new T.Vector3(-0.26, MID_Y + 0.0013, -0.09);
  trayG.position.copy(TRAY_STORE);
  var dish = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.008, 32, 1, true), M.alu); dish.position.y = 0.004; trayG.add(dish);
  var dishB = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.001, 32), M.alu); dishB.position.y = 0.0005; trayG.add(dishB);
  var saltM = new T.MeshStandardMaterial({ color: 0xf4f2ec, roughness: 0.95 });
  var salt = S.mesh(new T.CylinderGeometry(0.029, 0.029, 0.006, 32), saltM); salt.position.y = 0.004; trayG.add(salt);
  salt.visible = false;
  var jar = new T.Group(); S.scene.add(jar); jar.position.set(0.14, 0, 0.17);
  var jarB = S.mesh(new T.CylinderGeometry(0.026, 0.026, 0.07, 28), M.glass); jarB.position.y = 0.035; jar.add(jarB);
  var jarS = S.mesh(new T.CylinderGeometry(0.024, 0.024, 0.05, 28), saltM); jarS.position.y = 0.026; jar.add(jarS);
  var jarL = S.mesh(new T.CylinderGeometry(0.027, 0.027, 0.012, 28), M.bakelite); jarL.position.y = 0.076; jar.add(jarL);
  var jarT = S.label(SALT + ' ' + Math.round(p.m * 1000) + ' g', { w: 0.04, ratio: 0.3, color: '#2b2f36' });
  jarT.position.set(0, 0.035, 0.0265); jar.add(jarT);
  S.contact(0.07, 0.07, 0.14, 0.17, 0.4);

  if (BETA) {
    jar.visible = false; trayG.visible = false;
    S.addApparatus('src', srcG, SRC, 'A sealed disc source. It is moved only with the tongs, from behind the shield, and lives in the lead pot when it is not being counted.');
    S.addApparatus('pot', pot, 'Lead source store', 'The source is kept here, lid on, whenever a reading is not being taken.');
    S.addApparatus('tongs', tongs, 'Source tongs', 'Long tongs keep your hands away from the source.');
    S.addApparatus('abs', fbox, 'Box of aluminium foils',
      'Foils marked with their areal density in mg/cm² (mass per unit area): ' + FOILS.filter(function (v) { return v > 0; }).join(', ') + '. Areal density, not thickness, is what fixes the absorption of betas.');
  } else {
    srcG.visible = false; pot.visible = false; tongs.visible = false; potLbl.visible = false;
    fbox.visible = false; fLbl.visible = false;
    S.addApparatus('tray', trayG, 'Shallow aluminium tray', 'The same tray is counted empty for the background and filled for the salt, in exactly the same place.');
    S.addApparatus('jar', jar, SRC, 'A weighed ' + Math.round(p.m * 1000) + ' g of the salt. Natural potassium contains 0.0117 % of K-40.');
  }
  var hudA = S.hudCard(BETA ? 'Absorber' : 'Tray'), hudC = S.hudCard('Counts'), hudR = S.hudCard('Count rate');

  // ================================================================ human actions
  function carry(obj, from, to, after) {
    return S.hand.pinchMove(from, function (k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, Math.max(from.y, to.y) + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
    }, function (k) {
      obj.position.set(from.x + (to.x - from.x) * k, from.y + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
      if (BETA) tongs.position.set(srcG.position.x + 0.07, srcG.position.y, srcG.position.z + 0.05);
    }, { mode: 'side', ms: 1100, reachMs: 700 }).then(function () { obj.position.copy(to); after(); S.render(); });
  }
  function placeSource() {
    if (busy() || st.placed) return Promise.resolve();
    return carry(srcG, srcG.position.clone(), new T.Vector3(-0.26, shelfY[2] + 0.0025, -0.09), function () {
      st.placed = true;
      S.say('Source on the middle shelf, 3 cm below the window, with the tongs and from behind the shield. It stays exactly there for every reading.');
    });
  }
  function storeSource() {
    if (busy() || !st.placed) return Promise.resolve();
    return carry(srcG, srcG.position.clone(), POT.clone(), function () {
      st.placed = false; S.say('Source back in its lead store, lid on.');
    });
  }
  function placeTray() {
    if (busy() || st.placed) return Promise.resolve();
    return carry(trayG, trayG.position.clone(), TRAY_SHELF.clone(), function () {
      st.placed = true;
      S.say(st.filled ? 'The filled tray is on the middle shelf, in the same place as the empty one was.' : 'The empty tray is on the middle shelf under the tube.');
    });
  }
  function takeTray() {
    if (busy() || !st.placed) return Promise.resolve();
    return carry(trayG, trayG.position.clone(), TRAY_STORE.clone(), function () { st.placed = false; S.say('The tray is back on the bench.'); });
  }
  function fillTray() {
    if (busy()) return Promise.resolve();
    if (st.filled) return Promise.resolve();
    if (st.placed) { S.say('Take the tray off the shelf to fill it.'); return Promise.resolve(); }
    if (st.bg === null) { S.say('Count the empty tray first: the background must be taken with nothing in it.'); return Promise.resolve(); }
    var a = wpt(jar, 0, 0.08, 0), b = wpt(trayG, 0, 0.03, 0);
    return S.hand.pinchMove(a, function (k) { return new T.Vector3(a.x + (b.x - a.x) * k, a.y + 0.03 * Math.sin(Math.PI * k) + (b.y - a.y) * k, a.z + (b.z - a.z) * k); },
      function (k) { if (k > 0.6) { salt.visible = true; salt.scale.y = Math.max(0.05, (k - 0.6) / 0.4); } }, { mode: 'top', ms: 1400, reachMs: 600 })
      .then(function () {
        salt.visible = true; salt.scale.y = 1; st.filled = true;
        S.say('The ' + Math.round(p.m * 1000) + ' g of ' + SALT + ' is poured into the tray and levelled with a card, so the depth is the same everywhere.');
        S.render();
      });
  }
  function turnTo(v) {
    if (busy()) return Promise.resolve();
    if (!isFinite(v) || v < VMIN || v > VMAX + 1e-9) { S.say('The E.H.T. goes from ' + VMIN + ' to ' + VMAX + ' V only.'); return Promise.resolve(); }
    v = Math.round(v / VSTEP) * VSTEP;
    var v0 = st.V, a0 = knobAngle(v0), pt = wpt(unit, KX, 0.004 + UH / 2 + KY, FZ + 0.024);
    if (v === v0) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      st.V = v0 + (v - v0) * k; knob.rotation.z = knobAngle(st.V);
      S.hand.group.rotation.y = -(knobAngle(st.V) - a0) * 0.3;
    }, { mode: 'front', ms: 350 + 1.2 * Math.abs(v - v0), reachMs: 600 })
      .then(function () { st.V = v; knob.rotation.z = knobAngle(v); S.render(); });
  }
  function setTime(t) {
    if (!isFinite(t) || t < 10 || t > 3600) { S.say('The preset time goes from 10 s to 3600 s.'); return false; }
    st.t = Math.round(t); return true;
  }
  function count() {
    if (busy()) return Promise.resolve(false);
    if (st.V < 380 || st.V > VPLAT) { S.say('Set the tube on its plateau, about 450 V, before counting.'); return Promise.resolve(false); }
    st.counting = true; st.count = 0; st.elapsed = 0;
    var total = drawCounts(st.t);
    return S.hand.tap(startB, 'front').then(function () {
      return S.tween(1400, function (k) { st.elapsed = st.t * k; st.count = Math.round(total * k); });
    }).then(function () {
      st.counting = false; st.elapsed = st.t; st.count = total;
      S.say('Counted ' + total + ' in ' + st.t + ' s: ' + (total / st.t).toFixed(3) + ' counts per second.');
      S.render(); return true;
    });
  }
  function setFoil(mg) {
    if (busy()) return Promise.resolve(false);
    if (FOILS.indexOf(mg) < 0) { S.say('The box holds foils of ' + FOILS.join(', ') + ' mg/cm².'); return Promise.resolve(false); }
    if (mg === st.x) return Promise.resolve(true);
    var to = new T.Vector3(-0.26, SH_Y + 0.02, -0.04), from = new T.Vector3(0.12, 0.03, 0.17);
    return S.hand.pinchMove(from, function (k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.05 * Math.sin(Math.PI * k), from.z + (to.z - from.z) * k);
    }, function () {}, { mode: 'side', ms: 900, reachMs: 650 }).then(function () {
      st.x = mg; foilM.visible = mg > 0; foilM.scale.y = Math.max(0.6, mg / 60);
      S.say(mg === 0 ? 'No foil: the betas reach the window through air only.' : mg + ' mg/cm² of aluminium on the shelf between the source and the window.');
      S.render(); return true;
    });
  }
  function full() { return st.elapsed >= st.t - 1e-9 && !st.counting; }
  function recordBackground() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (BETA && st.placed) { S.say('The source must be back in its lead store for a background count.'); return false; }
    if (!BETA && (st.filled || !st.placed)) { S.say('The background is counted with the EMPTY tray on its shelf.'); return false; }
    if (!full()) { S.say('Press START and let the counter run its full time first.'); return false; }
    st.bg = corr(st.count, st.t); st.bgN = st.count; st.bgT = st.t;
    S.say('Background: ' + st.count + ' counts in ' + st.t + ' s, that is ' + st.bg.toFixed(3) + ' counts per second. It comes off every reading.');
    S.render(); return true;
  }
  function recordBeta() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (st.bg === null) { S.say('Take the background count first, with the source in its store.'); return false; }
    if (!st.placed) { S.say('Put the source back on its shelf first.'); return false; }
    if (!full()) { S.say('Press START and let the counter run its full time first.'); return false; }
    if (st.done[st.x]) { S.say('You already have a reading with ' + st.x + ' mg/cm². Change the foil.'); return false; }
    st.done[st.x] = true;
    var r = corr(st.count, st.t);
    if (st.x === TAIL) { st.tail = r - st.bg; st.tailN = st.count; }
    S.addRow({ x: st.x, xm: st.x / 1000, t: st.t, N: st.count, rate: rnd(r, 4), above: rnd(r - st.bg, 4) });
    S.say('Written: ' + st.x + ' mg/cm², ' + st.count + ' counts in ' + st.t + ' s, ' + (r - st.bg).toFixed(3) + ' per second above the background (dead time corrected).');
    return true;
  }
  function recordSalt() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (st.bg === null) { S.say('Count the empty tray first.'); return false; }
    if (!st.filled || !st.placed) { S.say('Fill the tray and put it on the shelf first.'); return false; }
    if (!full()) { S.say('Press START and let the counter run its full time first.'); return false; }
    if (st.lastN === st.idx) { S.say('That count is already written down. Press START for a new one.'); return false; }
    st.lastN = st.idx;
    var r = corr(st.count, st.t);
    S.addRow({ n: S.rows.length + 1, t: st.t, N: st.count, rate: rnd(r, 4), net: rnd(r - st.bg, 4) });
    S.say('Count ' + S.rows.length + ': ' + st.count + ' in ' + st.t + ' s, ' + (r - st.bg).toFixed(3) + ' per second above the background.');
    return true;
  }

  // ---------------------------------------------------------------- results
  function netRows(rows) {             // beta rate = above background - the bremsstrahlung tail
    var tail = st.tail === null ? null : st.tail;
    return rows.filter(function (r) { return r.x !== TAIL; }).map(function (r) {
      var b = tail === null ? null : r.above - tail;
      var sd = Math.sqrt(r.N) / r.t;
      return { x: r.x, xm: r.xm, beta: b, sig: b !== null && b > 3 * Math.sqrt(sd * sd + (st.bgN || 1) / Math.pow(st.bgT || 1, 2) + (st.tailN || 1) / (T_TAIL * T_TAIL)) };
    });
  }
  function rangeOf(rows) {
    var nr = netRows(rows).sort(function (a, b) { return a.x - b.x; });
    var last = -1, i;
    for (i = 0; i < nr.length; i++) if (nr[i].sig) last = i;
    if (last < 0 || last === nr.length - 1) return null;
    return (nr[last].x + nr[last + 1].x) / 2;
  }
  function muOf(rows) {
    var pts = netRows(rows).filter(function (r) { return r.beta !== null && r.beta > 0 && r.x <= 0.55 * RMG; })
      .map(function (r) { return [r.xm, Math.log(r.beta)]; });
    if (pts.length < 4) return null;
    var f = S.fit.linear(pts); return f && f.m < 0 ? -f.m : null;
  }
  function eFromRange(rg) {            // invert Katz-Penfold by bisection
    var lo = 0.01, hi = 2.5, i, mid;
    for (i = 0; i < 80; i++) { mid = (lo + hi) / 2; if (KN.rangeKP(mid) < rg) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }
  function result(rows) {
    if (BETA) {
      if (st.tail === null) return null;
      var rg = rangeOf(rows), mu = muOf(rows);
      if (rg === null || mu === null) return null;
      return { label: 'Range of the betas in aluminium', value: rg, unit: 'mg/cm²', digits: 0, truth: RMG,
        note: 'The beta counts end between the last foil that still shows them and the first that does not. Slope of ln(beta rate): μ_m = '
          + mu.toFixed(1) + ' cm²/g (the model\'s ' + KN.muM(p.E).toFixed(1) + '). Katz-Penfold turns the range into an end-point energy of '
          + eFromRange(rg / 1000).toFixed(3) + ' MeV. SIMULATED DATA.' };
    }
    var nets = rows.map(function (r) { return r.net; });
    if (nets.length < 3) return null;
    var mean = S.fit.mean(nets);
    var A = KN.activity(p);
    return { label: 'Count rate above background from the salt', value: mean, unit: 'counts/s', digits: 3,
      truth: KN.netRate(assign(p, { on: 1 })),
      note: 'The ' + Math.round(p.m * 1000) + ' g of ' + SALT + ' holds ' + (p.m * 1000 * p.fK).toFixed(1) + ' g of potassium, so its K-40 gives '
        + A.toFixed(0) + ' decays a second (' + (A / (p.m * 1000 * p.fK)).toFixed(1) + ' Bq per gram of potassium). The tube sees a small fraction of the betas. SIMULATED DATA.' };
  }

  // ---------------------------------------------------------------- the page
  var theoryB = {
    principle: 'Beta particles are emitted with every energy up to an end point E. In aluminium the count rate falls almost exponentially with the areal density of the foils, and beyond a definite range no betas get through at all: only bremsstrahlung X-rays and the background are left.',
    formula: 'N = N₀ e^(−μ_m x)  (x < R),   R = 0.412 E^(1.265 − 0.0954 ln E) g/cm²',
    formulaNote: 'x is the areal density (mass per unit area); μ_m ≈ 17 E^−1.14 cm²/g',
    more: ['Background first, with the source locked away; the bremsstrahlung tail is counted far behind the range and taken off too.',
      'Near the range the beta counts are a small excess over the tail: count longer there, and call a foil "still showing betas" only when the excess is more than three standard deviations.',
      'In this simulation the beta curve is cut off sharply at R; a real curve rounds off into the tail just before it, which is why real range readings are uncertain by several per cent.'],
    precautions: 'Keep the source, the tube and the shelf fixed; only the foil changes. Correct every rate for dead time. Stand behind the lead castle and return the source to its store at the end.' };
  var theoryK = {
    principle: 'Natural potassium contains 0.0117 % of K-40, half-life 1.248 × 10⁹ years. A gram of potassium holds about 1.8 × 10¹⁸ K-40 nuclei and gives about 31 decays a second, 89 % of them beta decays. A tray of a potassium salt is a weak but real source.',
    formula: 'A = (m f_K / M_K) N_A θ ln2 / T½,   net rate = ε × 0.893 A',
    formulaNote: 'ε is the fraction of the betas the tube sees from this tray (geometry and self-absorption)',
    more: ['The background is counted with the SAME tray, empty, in the same place: the tray itself and the room contribute to it.',
      'The signal is only a few counts a second, so long counts are needed: a count of N has an error of √N.',
      'The efficiency ε of this tray and tube is a design value of the simulation, not a material constant.'],
    precautions: 'Use the same tray, the same amount of salt, levelled to the same depth, and the same shelf for every count.' };

  var stepsB = [
    { id: 'bg', title: 'Background', view: 'unit', render: function (u) {
        u.h2('Count the background first');
        u.p('With the source locked in its lead store, set the tube on its plateau and count for ' + st.t + ' s.');
        u.task('Tube voltage', st.V >= 380 && st.V <= VPLAT, st.V + ' V').add(u.button('Set 450 V', function () { S.focus('unit'); turnTo(450); }, false, S.hand.busy));
        u.task('Background count', st.bg !== null, st.bg === null ? 'Not taken yet' : st.bg.toFixed(3) + ' counts per second')
          .add(u.row(u.button('START (' + st.t + ' s)', function () { count(); }, true, S.hand.busy),
            u.button('Record the background', function () { recordBackground(); }, false, S.hand.busy)));
        u.live(function () { return st.count + ' counts in ' + st.elapsed.toFixed(0) + ' s'; });
        u.next('Next: the foils', st.bg !== null);
      },
      ok: function () { return st.bg !== null; },
      auto: function () { setTime(300); return turnTo(450).then(function () { return count(); }).then(function () { recordBackground(); }); } },
    { id: 'foils', title: 'Foils', view: 'castle', render: function (u) {
        u.h2('Count through aluminium foils');
        u.p('Put the source on its shelf and count with no foil and with each thin foil up to about half the range, ' + p.t + ' s each.');
        u.task('Source on the shelf', st.placed, st.placed ? 'On the middle shelf' : 'In its store')
          .add(u.button('Lift it with the tongs', function () { S.focus('src'); placeSource(); }, true, st.placed || S.hand.busy));
        var sel = { i: 0 };
        u.slider('Foil from the box', 0, COARSE.length - 1, 1, function () { return sel.i; }, function (v) { sel.i = Math.round(v); }, '', 0);
        u.row(u.button('Lay on ' + COARSE[sel.i] + ' mg/cm²', function () { S.focus('abs'); setTime(p.t); setFoil(COARSE[sel.i]); }, true, S.hand.busy),
          u.button('START', function () { count(); }, false, S.hand.busy), u.button('Record', function () { recordBeta(); }, false, S.hand.busy));
        u.live(function () { return st.x + ' mg/cm²  ·  ' + st.count + ' counts in ' + st.t + ' s'; });
        u.h3('Observation table'); u.table();
        var n = S.rows.filter(function (r) { return COARSE.indexOf(r.x) >= 0; }).length;
        u.next('Next: near the range', n >= 6);
      },
      ok: function () { return S.rows.filter(function (r) { return COARSE.indexOf(r.x) >= 0; }).length >= 6; },
      auto: function () {
        setTime(p.t);
        return placeSource().then(function () {
          return COARSE.reduce(function (pr, mg) {
            return pr.then(function () { return setFoil(mg); }).then(function () { return count(); }).then(function () { recordBeta(); });
          }, Promise.resolve());
        });
      } },
    { id: 'end', title: 'End of the range', view: 'castle', render: function (u) {
        u.h2('Find where the beta counts end');
        u.p('Near the range the betas are only a small excess over the bremsstrahlung tail. Count the thick foils for ' + T_FINE + ' s each, and the thickest one, far behind the range, for ' + T_TAIL + ' s to measure the tail itself.');
        var sel = { i: 0 }, list = FINE.concat([TAIL]);
        u.slider('Foil from the box', 0, list.length - 1, 1, function () { return sel.i; }, function (v) { sel.i = Math.round(v); }, '', 0);
        u.row(u.button('Lay on ' + list[sel.i] + ' mg/cm²', function () { setTime(list[sel.i] === TAIL ? T_TAIL : T_FINE); setFoil(list[sel.i]); }, true, S.hand.busy),
          u.button('START', function () { count(); }, false, S.hand.busy), u.button('Record', function () { recordBeta(); }, false, S.hand.busy));
        u.live(function () { return st.x + ' mg/cm²  ·  ' + st.count + ' counts in ' + st.t + ' s'; });
        u.task('Tail behind the range', st.tail !== null, st.tail === null ? 'Count the ' + TAIL + ' mg/cm² foil' : st.tail.toFixed(3) + ' counts per second');
        u.table();
        var rg = rangeOf(S.rows);
        if (rg !== null) u.note('The beta counts end at about ' + rg.toFixed(0) + ' mg/cm².');
        u.next('Next: the result', st.tail !== null && rg !== null);
      },
      ok: function () { return st.tail !== null && rangeOf(S.rows) !== null; },
      auto: function () {
        return FINE.concat([TAIL]).reduce(function (pr, mg) {
          return pr.then(function () { setTime(mg === TAIL ? T_TAIL : T_FINE); return setFoil(mg); })
            .then(function () { return count(); }).then(function () { recordBeta(); });
        }, Promise.resolve()).then(function () { return setFoil(0); }).then(function () { return storeSource(); });
      } },
  ];
  var stepsK = [
    { id: 'bg', title: 'Empty tray', view: 'castle', render: function (u) {
        u.h2('Count the empty tray: the background');
        u.p('Put the empty tray on the middle shelf, set the tube on its plateau and count for 1200 s.');
        u.task('Tube voltage', st.V >= 380 && st.V <= VPLAT, st.V + ' V').add(u.button('Set 450 V', function () { S.focus('unit'); turnTo(450); }, false, S.hand.busy));
        u.task('Empty tray on the shelf', st.placed && !st.filled, st.placed ? 'On the shelf' : 'On the bench')
          .add(u.button('Put it on the shelf', function () { S.focus('tray'); placeTray(); }, true, st.placed || st.filled || S.hand.busy));
        u.task('Background count', st.bg !== null, st.bg === null ? 'Not taken yet' : st.bg.toFixed(3) + ' counts per second')
          .add(u.row(u.button('START (1200 s)', function () { setTime(1200); count(); }, true, S.hand.busy),
            u.button('Record the background', function () { recordBackground(); }, false, S.hand.busy)));
        u.live(function () { return st.count + ' counts in ' + st.elapsed.toFixed(0) + ' s'; });
        u.next('Next: the salt', st.bg !== null);
      },
      ok: function () { return st.bg !== null; },
      auto: function () { setTime(1200); return turnTo(450).then(function () { return placeTray(); }).then(function () { return count(); }).then(function () { recordBackground(); }); } },
    { id: 'salt', title: 'The salt', view: 'castle', render: function (u) {
        u.h2('Count the tray filled with ' + SALT);
        u.p('Take the tray down, fill it with the weighed salt, level it, and put it back in exactly the same place. Count for ' + p.t + ' s, three times or more.');
        u.task('Tray filled and on the shelf', st.filled && st.placed, st.filled ? (st.placed ? 'On the shelf' : 'Filled, on the bench') : 'Empty')
          .add(u.row(u.button('Take it down', function () { takeTray(); }, false, !st.placed || S.hand.busy),
            u.button('Fill it', function () { S.focus('jar'); fillTray(); }, false, st.filled || st.placed || S.hand.busy),
            u.button('Put it back', function () { placeTray(); }, true, st.placed || !st.filled || S.hand.busy)));
        u.row(u.button('START (' + p.t + ' s)', function () { setTime(p.t); count(); }, true, S.hand.busy),
          u.button('Record the count', function () { recordSalt(); }, false, S.hand.busy));
        u.live(function () { return st.count + ' counts in ' + st.elapsed.toFixed(0) + ' s'; });
        u.table();
        u.next('Next: the result', S.rows.length >= 3);
      },
      ok: function () { return S.rows.length >= 3; },
      auto: function () {
        setTime(p.t);
        return takeTray().then(function () { return fillTray(); }).then(function () { return placeTray(); }).then(function () {
          return [0, 1, 2, 3].reduce(function (pr) { return pr.then(function () { return count(); }).then(function () { recordSalt(); }); }, Promise.resolve());
        });
      } },
  ];

  return {
    camera: { pos: [-0.02, 0.95, 1.16], look: [-0.03, 0.1, -0.06] },
    views: { castle: [[-0.16, 0.46, 0.34], [-0.26, 0.09, -0.12]], tube: [[-0.16, 0.26, 0.08], [-0.26, 0.15, -0.09]],
      src: [[-0.18, 0.2, 0.06], [-0.26, 0.09, -0.09]], pot: [[0.06, 0.18, 0.3], [0.0, 0.02, 0.16]],
      abs: [[0.12, 0.24, 0.36], [0.12, 0.02, 0.17]], tongs: [[0.1, 0.2, 0.34], [0.1, 0.0, 0.2]],
      tray: [[-0.1, 0.3, 0.3], [-0.2, 0.06, 0.0]], jar: [[0.16, 0.22, 0.38], [0.14, 0.04, 0.17]],
      unit: [[0.36, 0.42, 0.36], [0.3, 0.06, -0.1]],
      bench: [[-0.02, 0.95, 1.16], [-0.03, 0.1, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: BETA ? theoryB : theoryK,
    book: BETA ? { title: 'Expt. — Absorption of beta particles in aluminium',
      lines: ['Aim: mass absorption coefficient and range.', 'Source: ' + SRC, 'Background first; tail behind the range.',
        'N = N₀ e^(−μ_m x);  R from Katz-Penfold', 'Rates corrected for dead time 0.25 ms.'],
      columns: [{ label: 'x (mg/cm²)', get: function (r) { return r.x; } }, { label: 't (s)', get: function (r) { return r.t; } },
        { label: 'Counts', get: function (r) { return r.N; } }, { label: 'Above bg (/s)', get: function (r) { return r.above.toFixed(3); } }] }
      : { title: 'Expt. — Radioactivity of ' + SALT,
        lines: ['Aim: count rate above background', 'from the K-40 in ' + Math.round(p.m * 1000) + ' g of ' + SALT + '.',
          'Background: the same tray, empty.', 'Rates corrected for dead time.'],
        columns: [{ label: 'No.', get: function (r) { return r.n; } }, { label: 't (s)', get: function (r) { return r.t; } },
          { label: 'Counts', get: function (r) { return r.N; } }, { label: 'Net (/s)', get: function (r) { return r.net.toFixed(3); } }] },
    graph: BETA ? { x: function (r) { return r.x; }, y: function (r) { var b = st.tail === null ? r.above : r.above - st.tail; return b > 0 ? Math.log(b) : -3; },
      xlabel: 'areal density x (mg/cm²)', ylabel: 'ln (beta rate)', x0: 0 }
      : { x: function (r) { return r.n; }, y: function (r) { return r.net; }, xlabel: 'count number', ylabel: 'net rate (/s)', x0: 0, y0: 0 },
    result: result,
    tol: BETA ? 0.03 : 0.06,
    resultNote: BETA ? 'Betas have a range and gamma rays do not: that difference is the whole point of this experiment.'
      : 'A plain salt from the shop is measurably radioactive: K-40 is one of the main sources of the natural background, inside our own bodies too.',
    chips: BETA ? ['Why use mg/cm² and not mm?', 'What is the bremsstrahlung tail?', 'How is the range read?', 'Check my readings']
      : ['Where does the activity come from?', 'Why such a long count?', 'Why count the empty tray?', 'Check my readings'],
    viva: BETA ? [['Absorber thickness for betas is quoted in', ['mg/cm²', 'mm only', 'half-value layers'], 0, 'Energy loss depends on the mass per area crossed.'],
      ['Behind the range the counter still counts', ['Bremsstrahlung X-rays and background', 'Nothing', 'Alpha particles'], 0, 'Slowing betas radiate X-rays.']]
      : [['K-40 is', ['A primordial radioisotope in all natural potassium', 'Made by the GM tube', 'A gamma-only emitter'], 0, 'Half-life 1.25 × 10⁹ years.'],
        ['The error of a count of 2500 is about', ['50', '2500', '5'], 0, '√2500 = 50.']],
    askState: function () {
      return BETA ? { experiment: 'absorption of beta particles in aluminium: mass absorption coefficient and range', source: SRC,
        source_on_shelf: st.placed, foil_mg_per_cm2: st.x, background_rate_per_s: st.bg, tail_rate_per_s: st.tail, counting_time_s: st.t,
        last_count: st.count, readings_taken: S.rows.length }
        : { experiment: 'count rate above background from a potassium salt (K-40)', salt: SRC, mass_g: p.m * 1000, tray_filled: st.filled,
          tray_on_shelf: st.placed, background_rate_per_s: st.bg, counting_time_s: st.t, last_count: st.count, counts_taken: S.rows.length };
    },
    steps: BETA ? stepsB : stepsK,
    tick: function () {
      showC(String(st.count));
      showT(st.elapsed.toFixed(0));
      hudA.set(BETA ? st.x + ' mg/cm²' : (st.filled ? SALT + ' ' + Math.round(p.m * 1000) + ' g' : 'empty'));
      hudC.set(String(st.count));
      hudR.set(rateNow().toFixed(3) + ' /s');
    },
  };
});
