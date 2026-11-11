/* Prayogshala studio module: THE POLARISATION BENCH. One rig for two B.Sc. set-ups on the same divided circle -
   Brewster's angle (a polarised beam on a blackened glass plate, a photocell on a swinging arm and a microammeter,
   so the angle at which the reflection of the parallel component vanishes is SEARCHED for and the index of the glass
   follows from n = tan θ_B), and the specific rotation of sugar in a half-shade polarimeter (sodium lamp, polariser
   and half-shade, the solution in a 20 cm tube, the analyser on the divided circle). The gloved hand switches the
   source on, turns the plate and the arm, fills the tube and turns the analyser; the field of view is drawn as the
   observer sees it. Every reading comes from the kernels `fresnelrefl` and `polarimeter`. */
HoolaStudio.define('polar-bench', function (S) {
  var T = S.T, M = S.M;
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var POLARI = BASE === 'polarimeter-sugar';
  var K = POLARI ? window.HoolaKernels.K.polarimeter : window.HoolaKernels.K.fresnelrefl;
  var p = window.HoolaKernels.paramsFor(POLARI ? 'polarimeter' : 'fresnelrefl', S.lab.params);
  (S.lab.knobs || []).forEach(function (k) {
    if (k.hidden && isFinite(k.value) && p[k.param] !== undefined) p[k.param] = +k.value * (+k.k || 1);
  });
  var DEG = Math.PI / 180, R2D = 180 / Math.PI;
  var LC = POLARI ? 0.05 : 0.1;                         // the analyser circle / the plate circle, in degrees
  var CX = 0.0, CZ = -0.2, RC = 0.15;
  var AXY = 0.115;
  var CONCS = [0.05, 0.10, 0.15, 0.20];                 // the solutions made up by weighing sugar into water
  var MATCH = 5e-4;                                     // how close the two halves must be to call it a match
  var st = { on: false, polSet: false, th: 50, thSet: 50, arm: 100, phi: 90, phiSet: 90, ci: -1, filled: false,
    zero: null, reading: null };

  function fmt(v, d) { return (Math.round(v * Math.pow(10, d)) / Math.pow(10, d)).toFixed(d); }
  function roundLC(v) { return Math.round(v / LC) * LC; }
  function conc() { return st.ci < 0 ? 0 : CONCS[st.ci]; }

  // ---------------------------------------------------------------- physics from the kernels
  function coefs(thDeg) { return K.coef(thDeg * DEG, p); }           // [Rs, Rp]
  function halves(phiDeg) { return K.halves(p, phiDeg * DEG, conc()); }
  function matchDeg(c) { return K.matchAt(p, c) * R2D; }

  // ---------------------------------------------------------------- shared parts: the divided circle
  var base = new T.Group(); S.scene.add(base);
  [0, 120, 240].forEach(function (a) {
    var leg = S.rounded(0.08, 0.05, 0.015, 0.006, M.iron); leg.rotation.x = -Math.PI / 2;
    leg.position.set(CX + 0.095 * Math.cos(a * DEG), 0.011, CZ - 0.095 * Math.sin(a * DEG)); leg.rotation.z = -a * DEG; base.add(leg);
  });
  var col = S.mesh(new T.CylinderGeometry(0.032, 0.045, 0.045, 28), M.iron); col.position.set(CX, 0.024, CZ); base.add(col);
  var circTex = S.canvasTex(1536, 1536, function (x, w) {
    var c = w / 2, R = c - 8, i, a, len;
    x.clearRect(0, 0, w, w);
    x.fillStyle = '#d8b25c'; x.beginPath(); x.arc(c, c, R, 0, Math.PI * 2); x.fill();
    x.fillStyle = '#f3ead2'; x.beginPath(); x.arc(c, c, R * 0.993, 0, Math.PI * 2); x.fill();
    x.fillStyle = '#d8b25c'; x.beginPath(); x.arc(c, c, R * 0.78, 0, Math.PI * 2); x.fill();
    x.strokeStyle = '#1b1b1b';
    for (i = 0; i < 720; i++) {
      a = i * 0.5 * Math.PI / 180;
      len = i % 20 === 0 ? 0.13 : (i % 10 === 0 ? 0.085 : 0.05);
      x.lineWidth = i % 20 === 0 ? 3.5 : 1.8;
      x.beginPath();
      x.moveTo(c + Math.sin(a) * R * 0.985, c - Math.cos(a) * R * 0.985);
      x.lineTo(c + Math.sin(a) * R * (0.985 - len), c - Math.cos(a) * R * (0.985 - len));
      x.stroke();
    }
    x.fillStyle = '#1b1b1b'; x.font = '600 36px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
    for (i = 0; i < 36; i++) {
      a = i * 10 * Math.PI / 180;
      x.save(); x.translate(c + Math.sin(a) * R * 0.75, c - Math.cos(a) * R * 0.75); x.rotate(a);
      x.fillText(String(i * 10), 0, 0); x.restore();
    }
  });
  var circle = S.mesh(new T.CylinderGeometry(RC, RC, 0.013, 96),
    [M.brass, new T.MeshStandardMaterial({ map: circTex, roughness: 0.42, metalness: 0.2 }), M.brass]);
  circle.position.set(CX, 0.053, CZ); base.add(circle);
  S.contact(0.32, 0.32, CX, CZ, 0.5);

  function arc(r, Tdeg, y) {
    return new T.Vector3(CX + r * Math.cos(Tdeg * DEG), y === undefined ? AXY : y, CZ + r * Math.sin(Tdeg * DEG));
  }

  // ---------------------------------------------------------------- Brewster: plate, polariser, photocell arm
  var plateG, armG, cellG, meterNeedle, beamIn, beamOut, polG, srcG, tubeG, analG, liquid, hudA, hudB;
  var LAMP_T = 180;                                      // the source sits on the far side of the circle
  if (!POLARI) {
    var tableG = new T.Group(); tableG.position.set(CX, 0, CZ); S.scene.add(tableG);
    var tTop = S.mesh(new T.CylinderGeometry(0.05, 0.05, 0.005, 40), M.steel); tTop.position.y = 0.078; tableG.add(tTop);
    var tStem = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.02, 18), M.chrome); tStem.position.y = 0.068; tableG.add(tStem);
    plateG = new T.Group(); plateG.position.y = 0.0805; tableG.add(plateG);
    var glassM = new T.MeshPhysicalMaterial({ color: 0xd6eaee, roughness: 0.02, metalness: 0, transparent: true,
      opacity: 0.5, depthWrite: false, clearcoat: 1, envMapIntensity: 1.6, side: T.DoubleSide });
    var plate = S.mesh(new T.BoxGeometry(0.004, 0.05, 0.05), glassM); plate.position.y = 0.025; plate.renderOrder = 3; plateG.add(plate);
    var backing = S.mesh(new T.BoxGeometry(0.002, 0.05, 0.05), new T.MeshStandardMaterial({ color: 0x07080a, roughness: 0.95 }));
    backing.position.set(-0.0035, 0.025, 0); plateG.add(backing);
    var pFoot = S.mesh(new T.BoxGeometry(0.02, 0.006, 0.05), M.bakelite); pFoot.position.y = 0.003; plateG.add(pFoot);

    srcG = new T.Group(); srcG.position.copy(arc(0.3, LAMP_T, 0)); S.scene.add(srcG);
    var lBody = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.12, 26), M.blackPlastic);
    lBody.rotation.z = Math.PI / 2; lBody.position.y = AXY; srcG.add(lBody);
    var lPost = S.mesh(new T.CylinderGeometry(0.006, 0.006, AXY - 0.02, 18), M.chrome); lPost.position.y = (AXY - 0.02) / 2; srcG.add(lPost);
    var lFoot = S.mesh(new T.CylinderGeometry(0.03, 0.032, 0.012, 24), M.iron); lFoot.position.y = 0.006; srcG.add(lFoot);
    var lSw = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.005, 14), M.red);
    lSw.rotation.x = Math.PI / 2; lSw.position.set(-0.03, AXY + 0.014, 0.016); srcG.add(lSw);
    srcG.userData.sw = lSw;
    polG = new T.Group(); polG.position.copy(arc(0.17, LAMP_T)); S.scene.add(polG);
    var pRing = S.mesh(new T.TorusGeometry(0.019, 0.004, 10, 36), M.bakelite); pRing.rotation.y = Math.PI / 2; polG.add(pRing);
    var pDisc = new T.Mesh(new T.CircleGeometry(0.018, 32), new T.MeshBasicMaterial({ color: 0x241f2b, transparent: true, opacity: 0.55, side: T.DoubleSide }));
    pDisc.rotation.y = Math.PI / 2; polG.add(pDisc);
    var pPost = S.mesh(new T.CylinderGeometry(0.005, 0.005, AXY - 0.02, 16), M.chrome); pPost.position.y = -(AXY - 0.02) / 2 - 0.01; polG.add(pPost);
    var pLab = S.label('POLARISER', { w: 0.03, ratio: 0.22, color: '#d7dbe0', weight: 700 });
    pLab.position.set(0, 0.026, 0); pLab.rotation.x = -Math.PI / 2; polG.add(pLab);
    S.contact(0.09, 0.09, polG.position.x, polG.position.z, 0.4);
    S.contact(0.1, 0.1, srcG.position.x, srcG.position.z, 0.45);

    armG = new T.Group(); armG.position.set(CX, 0, CZ); S.scene.add(armG);
    var arm = S.mesh(new T.BoxGeometry(0.2, 0.008, 0.02), M.iron); arm.position.set(0.1, 0.068, 0); armG.add(arm);
    cellG = new T.Group(); cellG.position.set(0.2, AXY, 0); armG.add(cellG);
    var cBox = S.rounded(0.04, 0.036, 0.03, 0.004, M.blackPlastic); cBox.position.set(0.01, 0, 0); cellG.add(cBox);
    var cWin = new T.Mesh(new T.CircleGeometry(0.011, 24), new T.MeshBasicMaterial({ color: 0x1b2430 }));
    cWin.rotation.y = -Math.PI / 2; cWin.position.set(-0.011, 0, 0); cellG.add(cWin);
    var cPost = S.mesh(new T.CylinderGeometry(0.005, 0.005, AXY - 0.07, 16), M.chrome); cPost.position.y = -(AXY - 0.07) / 2 - 0.012; cellG.add(cPost);

    var meterG = new T.Group(); meterG.position.set(CX + 0.3, 0, CZ + 0.14); S.scene.add(meterG);
    var mBox = S.rounded(0.11, 0.075, 0.09, 0.008, M.blackPlastic); mBox.position.y = 0.0375; mBox.rotation.x = -0.25; meterG.add(mBox);
    var mFace = new T.Mesh(new T.PlaneGeometry(0.09, 0.055), new T.MeshStandardMaterial({
      map: S.canvasTex(512, 320, function (x, w, h) {
        x.fillStyle = '#f6f3ea'; x.fillRect(0, 0, w, h);
        x.strokeStyle = '#1b1b1b'; x.lineWidth = 2;
        var i, a, cx2 = w / 2, cy = h * 0.95, R = h * 0.76;
        for (i = 0; i <= 20; i++) {
          a = (-0.6 + i / 20 * 1.2);
          x.lineWidth = i % 5 === 0 ? 3 : 1.5;
          x.beginPath();
          x.moveTo(cx2 + Math.sin(a) * R, cy - Math.cos(a) * R);
          x.lineTo(cx2 + Math.sin(a) * R * (i % 5 === 0 ? 0.86 : 0.92), cy - Math.cos(a) * R * (i % 5 === 0 ? 0.86 : 0.92));
          x.stroke();
        }
        x.fillStyle = '#1b1b1b'; x.font = '600 30px "Public Sans", sans-serif'; x.textAlign = 'center';
        x.fillText('MICROAMMETER', cx2, 46); x.font = '500 22px "Public Sans", sans-serif';
        x.fillText('reflected light', cx2, 78);
      })
    })); mFace.position.set(0, 0.052, 0.046); mFace.rotation.x = -0.25; meterG.add(mFace);
    meterNeedle = S.mesh(new T.BoxGeometry(0.0012, 0.045, 0.0008), M.red, false);
    meterNeedle.position.set(0, 0.038, 0.0475); meterG.add(meterNeedle);
    S.contact(0.14, 0.12, CX + 0.3, CZ + 0.14, 0.5);
    S.addApparatus('plate', tableG, 'Glass plate on the table',
      'A plain glass plate, blackened behind so that only its front surface reflects. Its index is what you have to find.');
    S.addApparatus('src', srcG, 'Laser and polariser',
      'The source sends a polarised beam at the plate; the polariser is turned so that the electric field lies in the plane of incidence.');
    S.addApparatus('cell', armG, 'Photocell on the swinging arm',
      'It catches the reflected beam and feeds the microammeter, so the brightness of the reflection is a number, not a guess.');
    beamIn = new T.Line(new T.BufferGeometry(), new T.LineBasicMaterial({ color: 0xff3028, transparent: true, opacity: 0.85, depthWrite: false, toneMapped: false }));
    beamOut = new T.Line(new T.BufferGeometry(), new T.LineBasicMaterial({ color: 0xff6a58, transparent: true, opacity: 0.6, depthWrite: false, toneMapped: false }));
    beamIn.renderOrder = 7; beamOut.renderOrder = 7; S.scene.add(beamIn); S.scene.add(beamOut);
    S.addApparatus('meter', meterG, 'Microammeter', 'Reads the current from the photocell: the more light, the larger the reading.');
  }

  // ---------------------------------------------------------------- polarimeter: lamp, half-shade, tube, analyser
  if (POLARI) {
    srcG = new T.Group(); srcG.position.set(CX - 0.42, 0, CZ); S.scene.add(srcG);
    var sBox = S.rounded(0.09, 0.12, 0.09, 0.01, M.iron); sBox.position.y = 0.07; srcG.add(sBox);
    var sHole = new T.Mesh(new T.CircleGeometry(0.013, 22), new T.MeshBasicMaterial({ color: 0x5c4a20, toneMapped: false }));
    sHole.rotation.y = Math.PI / 2; sHole.position.set(0.046, AXY, 0); srcG.add(sHole);
    srcG.userData.hole = sHole;
    var sLab2 = S.label('SODIUM LAMP', { w: 0.062, ratio: 0.18, color: '#e8e2cf', weight: 700 });
    sLab2.position.set(0, 0.115, 0.046); srcG.add(sLab2);
    var sSw2 = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.006, 14), M.red);
    sSw2.rotation.x = Math.PI / 2; sSw2.position.set(0.02, 0.028, 0.046); srcG.add(sSw2);
    srcG.userData.sw = sSw2;
    S.contact(0.13, 0.13, CX - 0.42, CZ, 0.5);

    polG = new T.Group(); polG.position.set(CX - 0.27, 0, CZ); S.scene.add(polG);
    var hBody = S.mesh(new T.CylinderGeometry(0.026, 0.026, 0.05, 28), M.blackPlastic);
    hBody.rotation.z = Math.PI / 2; hBody.position.y = AXY; polG.add(hBody);
    var hPost = S.mesh(new T.CylinderGeometry(0.006, 0.006, AXY - 0.02, 16), M.chrome); hPost.position.y = (AXY - 0.02) / 2; polG.add(hPost);
    var hFoot = S.mesh(new T.CylinderGeometry(0.028, 0.03, 0.012, 22), M.iron); hFoot.position.y = 0.006; polG.add(hFoot);
    var hLab = S.label('HALF SHADE', { w: 0.036, ratio: 0.2, color: '#d7dbe0', weight: 700 });
    hLab.position.set(0, AXY + 0.027, 0); hLab.rotation.x = -Math.PI / 2; polG.add(hLab);
    S.contact(0.1, 0.1, CX - 0.27, CZ, 0.45);

    tubeG = new T.Group(); tubeG.position.set(CX - 0.12, 0, CZ); S.scene.add(tubeG);
    var tGlass = new T.MeshPhysicalMaterial({ color: 0xdfeef2, roughness: 0.03, transparent: true, opacity: 0.3,
      depthWrite: false, clearcoat: 1, side: T.DoubleSide });
    var tBody = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.2, 28, 1, true), tGlass);
    tBody.rotation.z = Math.PI / 2; tBody.position.y = AXY; tBody.renderOrder = 3; tubeG.add(tBody);
    liquid = S.mesh(new T.CylinderGeometry(0.0135, 0.0135, 0.19, 24),
      new T.MeshPhysicalMaterial({ color: 0xf2e3b8, roughness: 0.1, transmission: 0.6, thickness: 0.02, transparent: true, opacity: 0.75 }));
    liquid.rotation.z = Math.PI / 2; liquid.position.y = AXY; liquid.visible = false; tubeG.add(liquid);
    [[-0.1, 0], [0.1, 0]].forEach(function (e) {
      var cap = S.mesh(new T.CylinderGeometry(0.019, 0.019, 0.012, 24), M.brass);
      cap.rotation.z = Math.PI / 2; cap.position.set(e[0], AXY, 0); tubeG.add(cap);
    });
    var bulge = S.mesh(new T.SphereGeometry(0.014, 20, 14), tGlass); bulge.position.set(0, AXY + 0.014, 0); bulge.renderOrder = 3; tubeG.add(bulge);
    [[-0.06, 0], [0.06, 0]].forEach(function (e) {
      var cr = S.mesh(new T.BoxGeometry(0.016, 0.018, 0.05), M.bakelite); cr.position.set(e[0], AXY - 0.024, 0); tubeG.add(cr);
      var pst = S.mesh(new T.CylinderGeometry(0.005, 0.005, AXY - 0.04, 14), M.chrome); pst.position.set(e[0], (AXY - 0.04) / 2, 0); tubeG.add(pst);
    });
    S.contact(0.24, 0.1, CX - 0.12, CZ, 0.45);

    analG = new T.Group(); analG.position.set(CX, 0, CZ); S.scene.add(analG);
    var aBody = S.mesh(new T.CylinderGeometry(0.024, 0.024, 0.04, 28), M.blackPlastic);
    aBody.rotation.z = Math.PI / 2; aBody.position.y = AXY; analG.add(aBody);
    var aDrum = S.mesh(new T.CylinderGeometry(0.052, 0.052, 0.012, 48), M.brass);
    aDrum.rotation.z = Math.PI / 2; aDrum.position.set(0.028, AXY, 0); analG.add(aDrum);
    var aMark = new T.Group(); aMark.position.set(0.035, AXY, 0); analG.add(aMark);
    var pointer = S.mesh(new T.BoxGeometry(0.0012, 0.05, 0.0012), M.red, false); pointer.position.y = 0.026; aMark.add(pointer);
    analG.userData.mark = aMark;
    var eye = S.mesh(new T.CylinderGeometry(0.013, 0.016, 0.03, 22), M.bakelite);
    eye.rotation.z = Math.PI / 2; eye.position.set(0.07, AXY, 0); analG.add(eye);
    var aPost = S.mesh(new T.CylinderGeometry(0.006, 0.006, AXY - 0.06, 16), M.chrome); aPost.position.y = (AXY - 0.06) / 2; analG.add(aPost);
    var aLab = S.label('ANALYSER', { w: 0.032, ratio: 0.2, color: '#d7dbe0', weight: 700 });
    aLab.position.set(0, AXY + 0.026, 0); aLab.rotation.x = -Math.PI / 2; analG.add(aLab);

    var flask = new T.Group(); flask.position.set(CX - 0.3, 0, CZ + 0.22); S.scene.add(flask);
    var fBody = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.075, 28), new T.MeshPhysicalMaterial({ color: 0xe8f2f4, roughness: 0.05, transparent: true, opacity: 0.3, side: T.DoubleSide }));
    fBody.position.y = 0.038; flask.add(fBody);
    var fLiq = S.mesh(new T.CylinderGeometry(0.027, 0.027, 0.05, 24), new T.MeshPhysicalMaterial({ color: 0xf0e0b0, roughness: 0.15, transparent: true, opacity: 0.8 }));
    fLiq.position.y = 0.027; flask.add(fLiq);
    var fNeck = S.mesh(new T.CylinderGeometry(0.009, 0.012, 0.03, 20), new T.MeshPhysicalMaterial({ color: 0xe8f2f4, roughness: 0.05, transparent: true, opacity: 0.3, side: T.DoubleSide }));
    fNeck.position.y = 0.09; flask.add(fNeck);
    flask.userData.liq = fLiq;
    S.contact(0.1, 0.1, CX - 0.3, CZ + 0.22, 0.45);
    S.addApparatus('src', srcG, 'Sodium lamp', 'Specific rotation is quoted at the sodium D line, so the measurement is made in its yellow light.');
    S.addApparatus('pol', polG, 'Polariser and half-shade plate',
      'Half the field is turned a few degrees from the other, so the eye matches two halves instead of hunting for a darkest point.');
    S.addApparatus('tube', tubeG, 'Polarimeter tube',
      'A glass tube ' + fmt(p.Ldm, 1) + ' dm long holding the solution. The bulge at the top traps any air bubble out of the light path.');
    S.addApparatus('anal', analG, 'Analyser on the divided circle',
      'Turned until the two halves of the field look equally dim; its circle is read to ' + fmt(LC, 2) + ' degree.');
    S.addApparatus('flask', flask, 'Flask of sugar solution', 'Made up by weighing sugar into a measured volume of water.');
  }
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ---------------------------------------------------------------- the field of view / the meter (HUD)
  var eyeCard = document.createElement('div'); eyeCard.className = 'card';
  eyeCard.appendChild(document.createTextNode(POLARI ? 'Through the eyepiece' : 'The reflected beam'));
  var eyeCan = document.createElement('canvas'); eyeCan.width = 220; eyeCan.height = POLARI ? 220 : 150;
  eyeCan.style.cssText = 'width:' + (POLARI ? 170 : 200) + 'px;height:' + (POLARI ? 170 : 136) + 'px;display:block;margin-top:4px;border-radius:8px';
  eyeCard.appendChild(eyeCan); S.hud.appendChild(eyeCard);
  var ectx = eyeCan.getContext('2d'), eyeKey = '';
  hudA = S.hudCard(POLARI ? 'Analyser reads' : 'Angle of incidence');
  hudB = S.hudCard(POLARI ? 'The two halves' : 'Reflected light (parallel)');
  function drawEye() {
    var key = [st.on, st.polSet, st.filled, st.ci, fmt(st.phi, 3), fmt(st.th, 3)].join('|');
    if (key === eyeKey) return; eyeKey = key;
    var w = eyeCan.width, h = eyeCan.height;
    ectx.clearRect(0, 0, w, h);
    if (POLARI) {
      var c = w / 2, R = w / 2 - 8, hv = halves(st.phi);
      ectx.fillStyle = '#0a0b0d'; ectx.fillRect(0, 0, w, h);
      ectx.save(); ectx.beginPath(); ectx.arc(c, h / 2, R, 0, Math.PI * 2); ectx.clip();
      [0, 1].forEach(function (s) {
        var I = st.on ? hv[s] : 0, a = Math.min(1, Math.pow(I / p.I0, 0.32));
        ectx.fillStyle = 'rgba(255,205,70,' + a.toFixed(3) + ')';
        ectx.fillRect(s ? c : 0, 0, c, h);
      });
      ectx.strokeStyle = 'rgba(12,12,14,.85)'; ectx.lineWidth = 2;
      ectx.beginPath(); ectx.moveTo(c, 0); ectx.lineTo(c, h); ectx.stroke();
      ectx.restore();
      ectx.strokeStyle = 'rgba(90,96,104,.9)'; ectx.lineWidth = 3;
      ectx.beginPath(); ectx.arc(c, h / 2, R, 0, Math.PI * 2); ectx.stroke();
      ectx.fillStyle = '#9aa1ab'; ectx.font = '500 12px "Public Sans", sans-serif';
      ectx.fillText(st.on ? (Math.abs(hv[0] - hv[1]) < MATCH ? 'the halves match' : 'the halves differ') : 'lamp off', 8, h - 8);
      return;
    }
    var Rs = coefs(st.th)[0], Rp = coefs(st.th)[1], i;
    ectx.fillStyle = '#12141a'; ectx.fillRect(0, 0, w, h);
    ectx.fillStyle = '#9aa1ab'; ectx.font = '500 12px "Public Sans", sans-serif';
    ectx.fillText('field in the plane of incidence', 8, 16);
    var bw = w - 50, x0 = 34, y0 = 36, bh = 18;
    [[Rp, '#ff5a4a', 'R∥'], [Rs, '#49a7ff', 'R⊥']].forEach(function (b, k) {
      var y = y0 + k * 34;
      ectx.fillStyle = 'rgba(255,255,255,.08)'; ectx.fillRect(x0, y, bw, bh);
      ectx.fillStyle = b[1]; ectx.fillRect(x0, y, Math.max(1, bw * Math.min(1, b[0] / 0.3)), bh);
      ectx.fillStyle = '#e7eaee'; ectx.font = '600 12px "Public Sans", sans-serif';
      ectx.fillText(b[2], 8, y + 13);
      ectx.fillText(fmt(b[0] * 100, 3) + ' %', x0 + bw - 46, y + 13);
    });
    ectx.fillStyle = '#9aa1ab'; ectx.font = '500 12px "Public Sans", sans-serif';
    ectx.fillText('incidence ' + fmt(st.th, 1) + '°', 8, h - 10);
  }

  function update() {
    if (POLARI) {
      if (srcG.userData.hole) srcG.userData.hole.material.color.setHex(st.on ? 0xffd45e : 0x5c4a20);
      liquid.visible = st.filled;
      analG.userData.mark.rotation.x = -(st.phi - 90) * DEG;
      hudA.set(fmt(st.phi, 2) + '°');
      var hv = halves(st.phi);
      hudB.set(!st.on ? 'lamp off' : Math.abs(hv[0] - hv[1]) < MATCH ? 'equally dim' : (hv[0] > hv[1] ? 'left is brighter' : 'right is brighter'));
    } else {
      plateG.rotation.y = -(st.th - 50) * DEG;
      armG.rotation.y = -st.arm * DEG;
      beamIn.geometry.setFromPoints([arc(0.3, 180), arc(0, 0)]);
      beamOut.geometry.setFromPoints([arc(0, 0), arc(0.19, st.arm)]);
      beamIn.visible = st.on; beamOut.visible = st.on;
      var Rp = coefs(st.th)[1];
      meterNeedle.rotation.z = -(-0.6 + Math.min(1, Rp / 0.3) * 1.2);
      hudA.set(fmt(st.th, 2) + '°');
      hudB.set(st.on ? fmt(Rp * 100, 3) + ' %' : 'laser off');
    }
    drawEye();
  }

  // ---------------------------------------------------------------- the human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function switchOn() {
    if (st.on) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    return S.hand.tap(srcG.userData.sw, 'front').then(function () {
      st.on = true; update();
      S.say(POLARI ? 'The lamp is on. Give it a minute: the yellow line steadies.' : 'The laser is on; the beam runs at bench height.');
      S.render(); return true; });
  }
  function setPolariser() {
    if (st.polSet) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    return S.hand.tap(polG.children[0], 'top').then(function () {
      st.polSet = true; update();
      S.say(POLARI ? 'The polariser and its half-shade are set; the field is split in two.'
        : 'The polariser is set with the electric field in the plane of incidence - the only setting at which the reflection can vanish.');
      S.render(); return true; });
  }
  function turnPlate(toDeg) {
    if (S.hand.busy) return wait();
    toDeg = Math.max(20, Math.min(80, roundLC(toDeg)));
    var from = st.th;
    if (Math.abs(toDeg - from) < 1e-9) { st.th = toDeg; st.arm = 2 * toDeg; update(); return Promise.resolve(true); }
    function at(k) { return from + (toDeg - from) * k; }
    return S.hand.pinchMove(arc(0.055, 40, 0.1), function (k) { return arc(0.055, 40 + (at(k) - from), 0.1); },
      function (k) { st.th = at(k); st.arm = 2 * at(k); update(); },
      { ms: Math.min(1600, 420 + Math.abs(toDeg - from) * 26), reachMs: 620, hold: 150 })
      .then(function () { st.th = toDeg; st.arm = 2 * toDeg; update(); S.render(); return true; });
  }
  function turnAnalyser(toDeg) {
    if (S.hand.busy) return wait();
    toDeg = Math.max(70, Math.min(160, roundLC(toDeg)));
    var from = st.phi;
    if (Math.abs(toDeg - from) < 1e-9) { st.phi = toDeg; update(); return Promise.resolve(true); }
    function at(k) { return from + (toDeg - from) * k; }
    function pt(v) { return new T.Vector3(CX + 0.028, AXY + 0.052 * Math.cos((v - 90) * DEG), CZ - 0.052 * Math.sin((v - 90) * DEG)); }
    return S.hand.pinchMove(pt(from), function (k) { return pt(at(k)); },
      function (k) { st.phi = at(k); update(); },
      { ms: Math.min(1600, 420 + Math.abs(toDeg - from) * 22), reachMs: 620, hold: 150 })
      .then(function () { st.phi = toDeg; update(); S.render(); return true; });
  }
  function fillTube(ci) {
    if (S.hand.busy) return wait();
    var from = new T.Vector3(CX - 0.3, 0.12, CZ + 0.22), to = new T.Vector3(CX - 0.12, 0.17, CZ);
    return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); }, function () {},
      { ms: 1300, reachMs: 700, hold: 300, mode: 'top' }).then(function () {
      st.ci = ci; st.filled = true; st.reading = null; update();
      S.say(ci < 0 ? 'The tube is filled with distilled water, with no bubble in the light path.'
        : 'The tube is filled with the ' + fmt(CONCS[ci], 2) + ' g/mL solution.');
      S.render(); return true; });
  }
  function readMeter() {
    if (S.hand.busy) return wait();
    return S.hand.tap(POLARI ? analG.userData.mark.children[0] : meterNeedle, 'top').then(function () { return true; });
  }

  // ---------------------------------------------------------------- recording
  function recordBrewster() {
    if (!(st.on && st.polSet)) { S.say('Switch the laser on and set the polariser first.'); return false; }
    var th = roundLC(st.th), Rp = coefs(th)[1], Rs = coefs(th)[0];
    if (S.rows.some(function (r) { return Math.abs(r.th - th) < 1e-9; })) { S.say('That angle is already in the table. Move the plate on.'); return false; }
    S.addRow({ th: th, Rp: Rp * 100, Rs: Rs * 100 });
    S.say('At ' + fmt(th, 1) + '° the photocell reads ' + fmt(Rp * 100, 3) + ' %.');
    return true;
  }
  function recordRotation() {
    if (!st.filled) { S.say('Fill the tube first.'); return false; }
    var hv = halves(st.phi);
    if (Math.abs(hv[0] - hv[1]) > MATCH) { S.say('The two halves are not equally dim yet. Turn the analyser in small steps.'); return false; }
    var phi = roundLC(st.phi);
    if (st.ci < 0) { st.zero = phi; S.say('Zero of the instrument: ' + fmt(phi, 2) + '°. Every rotation is measured from here.'); S.render(); return true; }
    if (st.zero === null) { S.say('Take the zero with water in the tube first.'); return false; }
    var c = conc();
    if (S.rows.some(function (r) { return Math.abs(r.c - c) < 1e-9; })) { S.say('That solution is already in the table. Fill the tube with the next one.'); return false; }
    S.addRow({ c: c, phi: phi, rot: phi - st.zero, alpha: (phi - st.zero) / (c * p.Ldm) });
    S.say('At ' + fmt(c, 2) + ' g/mL the plane is turned by ' + fmt(phi - st.zero, 2) + '°.');
    return true;
  }
  function parabolaMin(rows) {                           // the vertex of a parabola through the three lowest readings
    var r = rows.slice().sort(function (a, b) { return a.Rp - b.Rp; }).slice(0, 3)
      .sort(function (a, b) { return a.th - b.th; });
    if (r.length < 3) return null;
    var x1 = r[0].th, x2 = r[1].th, x3 = r[2].th, y1 = r[0].Rp, y2 = r[1].Rp, y3 = r[2].Rp;
    var d1 = (x1 - x2) * (x1 - x3), d2 = (x2 - x1) * (x2 - x3), d3 = (x3 - x1) * (x3 - x2);
    if (!d1 || !d2 || !d3) return null;
    var A = y1 / d1 + y2 / d2 + y3 / d3;
    var B = -(y1 * (x2 + x3) / d1 + y2 * (x1 + x3) / d2 + y3 * (x1 + x2) / d3);
    return A > 0 ? -B / (2 * A) : null;
  }
  function meanOf(xs) { return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : NaN; }

  var VIEWS = POLARI ? {
    src: [[CX - 0.3, 0.3, CZ + 0.34], [CX - 0.42, 0.08, CZ]],
    pol: [[CX - 0.18, 0.24, CZ + 0.26], [CX - 0.27, AXY, CZ]],
    tube: [[CX - 0.1, 0.28, CZ + 0.34], [CX - 0.12, AXY, CZ]],
    anal: [[CX + 0.2, 0.26, CZ + 0.28], [CX + 0.02, AXY, CZ]],
    flask: [[CX - 0.22, 0.2, CZ + 0.4], [CX - 0.3, 0.05, CZ + 0.22]],
    wide: [[CX + 0.14, 0.66, CZ + 0.96], [CX - 0.12, 0.08, CZ]],
    book: [[0.66, 0.46, 0.64], [0.64, 0.0, 0.16]]
  } : {
    plate: [[CX + 0.26, 0.36, CZ + 0.44], [CX, 0.08, CZ]],
    src: [[CX - 0.22, 0.3, CZ + 0.34], [CX - 0.3, AXY, CZ]],
    cell: [[CX + 0.3, 0.3, CZ + 0.36], [CX + 0.1, AXY, CZ + 0.06]],
    meter: [[CX + 0.34, 0.26, CZ + 0.42], [CX + 0.3, 0.06, CZ + 0.14]],
    wide: [[CX + 0.16, 0.7, CZ + 0.95], [CX - 0.04, 0.08, CZ]],
    book: [[0.66, 0.46, 0.64], [0.64, 0.0, 0.16]]
  };
  update();

  var brewsterSteps = [
    { id: 'setup', title: 'Set up', view: 'wide', render: function (u) {
      u.h2('Switch the laser on and set the polariser');
      u.p('The beam falls on a glass plate blackened behind, so only its front surface reflects. The polariser is '
        + 'turned so that the electric field lies in the plane of incidence: that is the only setting at which the '
        + 'reflection can fall to nothing.');
      u.task('1. Switch the laser on', st.on, st.on ? 'The beam is on the plate' : 'Press the switch on the laser')
        .add(u.button(st.on ? 'Laser on' : 'Switch the laser on', function () { switchOn(); }, !st.on, st.on || S.hand.busy));
      u.task('2. Set the polariser', st.polSet, st.polSet ? 'Field in the plane of incidence' : 'Turn it until the reflection is weakest near 56 degrees')
        .add(u.button(st.polSet ? 'Set' : 'Set the polariser', function () { setPolariser(); }, !st.polSet, st.polSet || !st.on || S.hand.busy));
      u.note('Laser safety: the plate reflects the beam, so work out where the reflection goes before switching on. '
        + 'Keep the whole path at bench level and never at eye height, and never look into the beam or its reflection.');
      u.next('Next: find the angle', st.on && st.polSet);
    },
    ok: function () { return st.on && st.polSet; },
    auto: function () { return switchOn().then(setPolariser); } },

    { id: 'measure', title: 'Find Brewster\'s angle', view: 'plate', render: function (u) {
      u.h2('Turn the plate and watch the microammeter');
      u.p('Turn the plate and the photocell arm together, so that the cell always catches the reflected beam, and '
        + 'read the meter at each setting. The reading falls almost to zero at one angle and rises again: that is '
        + 'Brewster\'s angle, and the index of the glass is its tangent.');
      u.slider('Turn the plate to', 20, 80, 0.5, function () { return st.thSet; }, function (x) { st.thSet = x; }, '° incidence', 1);
      u.row(u.button('Turn the plate and the arm', function () { turnPlate(st.thSet); S.render(); }, true, S.hand.busy),
        u.button('Read the meter', function () { readMeter(); }, false, S.hand.busy));
      function nudge(d) { return function () { st.thSet = st.th + d; turnPlate(st.th + d); S.render(); }; }
      u.row(u.button('− 2°', nudge(-2), false, S.hand.busy), u.button('− 0.5°', nudge(-0.5), false, S.hand.busy),
        u.button('+ 0.5°', nudge(0.5), false, S.hand.busy), u.button('+ 2°', nudge(2), false, S.hand.busy));
      u.live(function () { return 'At ' + fmt(st.th, 1) + '° the cell reads ' + fmt(coefs(st.th)[1] * 100, 3)
        + ' % (across the plane it would read ' + fmt(coefs(st.th)[0] * 100, 2) + ' %)'; });
      u.row(u.button('Record this reading', function () { recordBrewster(); S.render(); }, true, S.hand.busy));
      u.h3('Observation table'); u.table();
      u.next('Next: graph and result', S.rows.length >= 5);
      if (S.rows.length < 5) u.p(S.rows.length + ' of at least 5 angles recorded.');
    },
    ok: function () { return S.rows.length >= 5; },
    auto: function () {
      var seq = Promise.resolve();
      [48, 52, 54, 56, 58, 60, 62, 64].forEach(function (a) {
        seq = seq.then(function () { return turnPlate(a); }).then(readMeter).then(function () { recordBrewster(); });
      });
      return seq;
    } }
  ];

  var polariSteps = [
    { id: 'setup', title: 'Set up and take the zero', view: 'wide', render: function (u) {
      u.h2('Light the instrument and find its zero');
      u.p('Switch the sodium lamp on and set the polariser with its half-shade plate. Fill the tube with distilled '
        + 'water, put it in, and turn the analyser until the two halves of the field look equally dim. That setting is '
        + 'the zero of the instrument.');
      u.task('1. Switch the lamp on', st.on, st.on ? 'Steady yellow light' : 'Press the switch on the lamp house')
        .add(u.button(st.on ? 'Lamp on' : 'Switch the lamp on', function () { switchOn(); }, !st.on, st.on || S.hand.busy));
      u.task('2. Set the polariser and half-shade', st.polSet, st.polSet ? 'The field is split in two' : 'Turn the half-shade into the beam')
        .add(u.button(st.polSet ? 'Set' : 'Set the half-shade', function () { setPolariser(); }, !st.polSet, st.polSet || !st.on || S.hand.busy));
      u.task('3. Fill the tube with water', st.filled && st.ci < 0, st.filled && st.ci < 0 ? 'No bubble in the light path' : 'Rinse and fill with distilled water')
        .add(u.button(st.filled && st.ci < 0 ? 'Filled' : 'Fill with water', function () { fillTube(-1); }, !(st.filled && st.ci < 0), !st.polSet || S.hand.busy));
      u.slider('Turn the analyser to', 70, 160, LC, function () { return st.phiSet; }, function (x) { st.phiSet = x; }, '°', 2);
      u.row(u.button('Turn the analyser', function () { turnAnalyser(st.phiSet); S.render(); }, true, S.hand.busy),
        u.button('Find the match', function () { var m = matchDeg(0); st.phiSet = roundLC(m); turnAnalyser(st.phiSet).then(function () { S.render(); }); }, false, S.hand.busy),
        u.button('Read the circle', function () { readMeter(); }, false, S.hand.busy));
      u.live(function () { var hv = halves(st.phi);
        return 'Left ' + fmt(hv[0] / p.I0 * 100, 1) + ' % · right ' + fmt(hv[1] / p.I0 * 100, 1) + ' %'; });
      u.task('4. Record the zero', st.zero !== null, st.zero !== null ? 'Zero at ' + fmt(st.zero, 2) + '°' : 'Both halves equally dim, then record')
        .add(u.button('Record the zero', function () { recordRotation(); S.render(); }, st.zero === null, S.hand.busy));
      u.note('The eye cannot tell when one field is darkest, but it is very good at telling two halves apart: that is '
        + 'what the half-shade plate is for.');
      u.next('Next: the solutions', st.zero !== null);
    },
    ok: function () { return st.zero !== null; },
    auto: function () {
      return switchOn().then(setPolariser).then(function () { return fillTube(-1); })
        .then(function () { return turnAnalyser(roundLC(matchDeg(0))); }).then(readMeter)
        .then(function () { recordRotation(); });
    } },

    { id: 'measure', title: 'Measure the rotation', view: 'anal', render: function (u) {
      u.h2('Fill the tube with each solution and find the new match');
      u.p('Rinse the tube and fill it with a solution of known strength. The plane of polarisation is turned, so the '
        + 'halves no longer match; turn the analyser until they do again. The difference from the zero is the '
        + 'rotation for that concentration.');
      u.row.apply(u, CONCS.map(function (c, i) {
        return u.button(fmt(c, 2) + ' g/mL', function () { fillTube(i); }, i === st.ci, S.hand.busy);
      }));
      u.task('Tube', st.filled && st.ci >= 0, st.ci < 0 ? 'Water (the zero)' : fmt(conc(), 2) + ' g/mL sugar solution');
      u.slider('Turn the analyser to', 70, 160, LC, function () { return st.phiSet; }, function (x) { st.phiSet = x; }, '°', 2);
      u.row(u.button('Turn the analyser', function () { turnAnalyser(st.phiSet); S.render(); }, true, S.hand.busy),
        u.button('Find the match', function () { var m = matchDeg(conc()); st.phiSet = roundLC(m); turnAnalyser(st.phiSet).then(function () { S.render(); }); }, false, S.hand.busy),
        u.button('Read the circle', function () { readMeter(); }, false, S.hand.busy));
      function nudge(d) { return function () { st.phiSet = st.phi + d; turnAnalyser(st.phi + d); S.render(); }; }
      u.row(u.button('− 1°', nudge(-1), false, S.hand.busy), u.button('− 0.05°', nudge(-LC), false, S.hand.busy),
        u.button('+ 0.05°', nudge(LC), false, S.hand.busy), u.button('+ 1°', nudge(1), false, S.hand.busy));
      u.live(function () { var hv = halves(st.phi);
        return 'Left ' + fmt(hv[0] / p.I0 * 100, 1) + ' % · right ' + fmt(hv[1] / p.I0 * 100, 1) + ' %'
          + (st.zero === null ? '' : ' · rotation so far ' + fmt(st.phi - st.zero, 2) + '°'); });
      u.row(u.button('Record this solution', function () { recordRotation(); S.render(); }, true, S.hand.busy));
      u.h3('Observation table'); u.table();
      u.next('Next: graph and result', S.rows.length >= 3);
      if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 solutions recorded.');
    },
    ok: function () { return S.rows.length >= 3; },
    auto: function () {
      var seq = Promise.resolve();
      [0, 1, 2, 3].forEach(function (i) {
        seq = seq.then(function () { return fillTube(i); })
          .then(function () { return turnAnalyser(roundLC(matchDeg(CONCS[i]))); })
          .then(readMeter).then(function () { recordRotation(); });
      });
      return seq;
    } }
  ];

  return {
    camera: { pos: VIEWS.wide[0], look: VIEWS.wide[1] },
    views: VIEWS,
    theory: POLARI ? {
      principle: 'Cane sugar is optically active: its molecules turn the plane of polarisation of the light going '
        + 'through the solution. The rotation is proportional to the length of the column and to the concentration, '
        + 'so measuring it for solutions of known strength gives the specific rotation of the substance - and then an '
        + 'unknown solution can be read off the same straight line.',
      formula: 'θ = [α] × L(dm) × c(g/mL)',
      formulaNote: '[α] for sucrose at the sodium D line and 20 °C is +66.5 degrees per dm per g/mL',
      more: ['A half-shade plate covers half the field and turns its plane a few degrees, so the two halves are '
        + 'equally dim at one setting only. The eye judges a match far better than it judges a minimum.',
        'The rotation depends strongly on the wavelength, which is why the specific rotation is always quoted at a '
        + 'named line - here the sodium D line.'],
      precautions: 'Fill the tube with no air bubble in the light path: run any bubble up into the bulge. Rinse the '
        + 'tube with the next solution before filling it. Keep the temperature steady; the specific rotation is '
        + 'quoted at 20 degrees Celsius.'
    } : {
      principle: 'When light is reflected off glass, the two polarisations behave differently. Fresnel\'s formulae '
        + 'give the reflected fractions, and the one with its electric field in the plane of incidence falls all the '
        + 'way to zero at one angle, where the reflected and refracted beams are at right angles to each other. At '
        + 'that angle the reflected light is completely polarised.',
      formula: 'tan(θ_B) = n',
      formulaNote: 'θ_B = the angle at which the reflection of the parallel component vanishes',
      more: ['The component across the plane of incidence never vanishes, so the minimum appears only when the '
        + 'polariser puts the field in the plane of incidence.',
        'This is why polaroid sunglasses cut glare from water and from a road: that glare is reflected light, '
        + 'polarised mostly across the plane of incidence.'],
      precautions: 'Blacken the back of the plate so that there is no second reflection from it. Turn the plate and '
        + 'the arm together, so the photocell always catches the beam, and take small steps near the minimum.'
    },
    book: { title: POLARI ? 'Expt. — Specific rotation of sugar' : 'Expt. — Brewster\'s angle',
      lines: POLARI ? ['Tube length ' + fmt(p.Ldm, 1) + ' dm; sodium D line.',
        'Analyser circle read to ' + fmt(LC, 2) + ' degree.',
        'rotation = [alpha] x L(dm) x c(g/mL)', 'Zero taken with distilled water.']
        : ['Divided circle read to ' + fmt(LC, 1) + ' degree.',
          'Photocell + microammeter on the reflected beam.',
          'n = tan(Brewster angle)', 'Plate blackened behind.'],
      columns: POLARI ? [
        { label: 'c (g/mL)', get: function (r) { return fmt(r.c, 2); } },
        { label: 'Analyser (°)', get: function (r) { return fmt(r.phi, 2); } },
        { label: 'Rotation (°)', get: function (r) { return fmt(r.rot, 2); } },
        { label: '[α] (°/dm/(g/mL))', get: function (r) { return fmt(r.alpha, 2); } }] : [
        { label: 'Incidence (°)', get: function (r) { return fmt(r.th, 1); } },
        { label: 'R∥ (%)', get: function (r) { return fmt(r.Rp, 3); } },
        { label: 'R⊥ (%)', get: function (r) { return fmt(r.Rs, 2); } }],
      at: [0.64, 0.1, 0.12] },
    graph: POLARI ? { x: function (r) { return r.c; }, y: function (r) { return r.rot; },
      xlabel: 'concentration (g/mL)', ylabel: 'rotation (°)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return isFinite(k) ? function (x) { return k * x; } : null; } }
      : { x: function (r) { return r.th; }, y: function (r) { return r.Rp; },
        xlabel: 'angle of incidence (°)', ylabel: 'R∥ (%)', y0: 0,
        line: function (pts) { return null; } },
    result: function (rows) {
      if (POLARI) {
        if (rows.length < 3) return null;
        var k = S.fit.origin(rows.map(function (r) { return [r.c, r.rot]; }));
        if (!isFinite(k)) return null;
        return { label: 'specific rotation', value: k / p.Ldm, unit: '°/dm/(g/mL)', digits: 2, truth: p.alpha,
          note: 'Slope of the rotation against the concentration, divided by the length of the tube in decimetres.' };
      }
      if (rows.length < 5) return null;
      var thb = parabolaMin(rows);
      if (thb === null) return null;
      return { label: 'n', value: Math.tan(thb * DEG) * p.nout, unit: '', digits: 4, truth: p.n,
        note: 'Brewster\'s angle ' + fmt(thb, 2) + '°, from a parabola through the three lowest readings; n = tan of it.' };
    },
    tol: 0.02,
    chips: POLARI ? ['Why a half-shade plate?', 'Why take a zero with water?', 'What if there is a bubble in the tube?',
      'Check my readings', 'Why is the wavelength always stated?']
      : ['Why must the polariser be set first?', 'Why blacken the back of the plate?', 'How do I find the minimum carefully?',
        'Check my readings', 'What is polarised about the reflected light?'],
    viva: POLARI ? [['Why is a half-shade plate used?',
      ['The eye judges two halves equal better than it judges one field darkest', 'It makes the field brighter', 'It polarises the light'], 0,
      'A match between two halves is far more sensitive than an absolute minimum.'],
      ['A tube twice as long gives a rotation that is', ['twice as large', 'half as large', 'the same'], 0,
        'The rotation is proportional to the length of the column.']]
      : [['At Brewster\'s angle the reflected light is',
        ['completely polarised across the plane of incidence', 'completely polarised in the plane of incidence', 'unpolarised'], 0,
        'The parallel component is not reflected at all there.'],
        ['For glass of index 1.5 Brewster\'s angle is about', ['56 degrees', '34 degrees', '45 degrees'], 0,
          'arctan(1.5) = 56.3 degrees.']],
    askState: function () {
      if (POLARI) {
        var hv = halves(st.phi);
        return { set_up: 'half-shade polarimeter', lamp_on: st.on, half_shade_set: st.polSet,
          tube_filled_with: !st.filled ? 'nothing' : st.ci < 0 ? 'distilled water' : fmt(conc(), 2) + ' g/mL sugar solution',
          analyser_reads_deg: +st.phi.toFixed(2), zero_of_the_instrument_deg: st.zero,
          left_half_percent: +(hv[0] / p.I0 * 100).toFixed(1), right_half_percent: +(hv[1] / p.I0 * 100).toFixed(1),
          tube_length_dm: p.Ldm, readings_taken: S.rows.length, least_count_deg: LC };
      }
      return { set_up: 'Brewster angle', laser_on: st.on, polariser_set: st.polSet,
        angle_of_incidence_deg: +st.th.toFixed(2), photocell_arm_deg: +st.arm.toFixed(2),
        reflected_parallel_percent: +(coefs(st.th)[1] * 100).toFixed(4),
        reflected_perpendicular_percent: +(coefs(st.th)[0] * 100).toFixed(3),
        readings_taken: S.rows.length, least_count_deg: LC };
    },
    steps: POLARI ? polariSteps : brewsterSteps,
    tick: function () { update(); }
  };
});
