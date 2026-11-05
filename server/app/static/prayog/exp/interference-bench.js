/* Prayogshala studio module: THE TRAVELLING-MICROSCOPE INTERFERENCE BENCH. One rig for two B.Sc. set-ups - Newton's
   rings between a plano-convex lens and a plane plate, and the straight fringes of an air wedge between two flats
   held apart by a spacer. A sodium lamp lights a glass plate set at 45 degrees, which turns the light down onto the
   film; the fringes are looked at through a travelling microscope whose carriage is read on a scale with a vernier
   (least count 0.001 cm). The gloved hand lights the lamp, sets the 45 degree plate, focuses the microscope and
   slides the carriage from one fringe to the next. The pattern on the plate and the magnified field in the eyepiece
   are both drawn from the kernels' own intensity (`newtonrings`, `airwedge`), and each fringe is found where that
   intensity is least - never from the ring formula. */
HoolaStudio.define('interference-bench', function (S) {
  var T = S.T, M = S.M;
  var WEDGE = S.lab.kernel === 'airwedge';
  var K = WEDGE ? window.HoolaKernels.K.airwedge : window.HoolaKernels.K.newtonrings;
  var p = window.HoolaKernels.paramsFor(WEDGE ? 'airwedge' : 'newtonrings', S.lab.params);
  (S.lab.knobs || []).forEach(function (k) {
    if (k.hidden && isFinite(k.value) && p[k.param] !== undefined) p[k.param] = +k.value * (+k.k || 1);
  });
  var LC = 1e-5;                                        // travelling microscope: 0.001 cm
  var CX = 0.02, CZ = -0.17;                            // centre of the film
  var PLATE_Y = 0.042;                                  // top of the glass plate the pattern lives on
  var FIELD = WEDGE ? 0.004 : 0.008;                    // width of the microscope's field of view, metres
  var PAT = 0.03;                                       // the square of film the drawn pattern covers, metres
  var SAMPLE = (S.lab.variant || {}).sample || '';
  var LIQUID = p.mu > 1.02;
  var st = { lit: false, plate45: false, focused: false, x: WEDGE ? 0.003 : 0, xSet: WEDGE ? 0.003 : 0, hold: null, holdN: null };

  function fmt(v, d) { return (Math.round(v * Math.pow(10, d)) / Math.pow(10, d)).toFixed(d); }
  function roundLC(x) { return Math.round(x / LC) * LC; }
  function lamNm() { return p.lam * 1e9; }
  function colour() { var nm = lamNm();
    return nm < 460 ? [110, 120, 235] : nm < 500 ? [60, 160, 215] : nm < 565 ? [90, 205, 120] : nm < 600 ? [255, 206, 70] : [230, 90, 70]; }

  // ---------------------------------------------------------------- physics from the kernel
  function inten(x) {                                   // intensity at a distance x from the centre / contact edge
    return WEDGE ? K.intenAt(Math.max(x, 0), p) : K.intenAt(Math.abs(x), p);
  }
  function darkAt(n) { return WEDGE ? K.darkX(p, n) : K.darkR(p, n); }
  function ringsInView(xc) {                            // the dark fringes the cross-wire can reach
    var out = [], n;
    for (n = 1; n <= 40; n++) {
      var r = darkAt(n);
      if (WEDGE) { if (r < 0.03) out.push({ n: n, x: r }); }
      else { out.push({ n: n, x: r }); out.push({ n: n, x: -r }); }
      if (r > 0.03) break;
    }
    return out.filter(function (o) { return Math.abs(o.x - xc) < FIELD / 2; });
  }
  function nearestFringe() {
    var best = null;
    ringsInView(st.x).forEach(function (o) {
      var d = Math.abs(o.x - st.x);
      if (best === null || d < best.d) best = { n: o.n, x: o.x, d: d, side: o.x < 0 ? 'left' : 'right' };
    });
    return best && best.d < FIELD * 0.06 ? best : null;
  }

  // ---------------------------------------------------------------- the apparatus
  var bedW = 0.34;
  var micro = new T.Group(); micro.position.set(CX, 0, CZ - 0.0); S.scene.add(micro);
  var mBase = S.rounded(0.30, 0.15, 0.02, 0.008, M.iron); mBase.rotation.x = -Math.PI / 2;
  mBase.position.set(0, 0.01, -0.11); micro.add(mBase);
  [[-0.12, -0.15], [0.12, -0.15], [0, -0.06]].forEach(function (f) {
    var s2 = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.008, 16), M.brass); s2.position.set(f[0], 0.004, f[1]); micro.add(s2); });
  var bed = S.mesh(new T.BoxGeometry(bedW, 0.014, 0.05), M.iron); bed.position.set(0, 0.027, -0.11); micro.add(bed);
  var mScaleTex = S.canvasTex(2048, 128, function (x, w, h) {
    var cm = 30, k = w / cm, i, big;
    x.fillStyle = '#f0ead8'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#1a1a1a';
    for (i = 0; i <= cm * 10; i++) {
      big = i % 10 === 0;
      x.fillRect(i * k / 10, 0, big ? 4 : 2, big ? 54 : (i % 5 === 0 ? 38 : 22));
      if (big) { x.font = '600 40px sans-serif'; x.fillText(String(i / 10), i * k / 10 + 5, 100); }
    }
  });
  var mScale = new T.Mesh(new T.PlaneGeometry(bedW, 0.02), new T.MeshStandardMaterial({ map: mScaleTex, roughness: 0.55 }));
  mScale.rotation.x = -Math.PI / 2; mScale.position.set(0, 0.0345, -0.095); micro.add(mScale);

  var car = new T.Group(); micro.add(car);                    // the carriage: it carries the pillar and the tube
  var cBody = S.rounded(0.056, 0.05, 0.026, 0.004, M.alu); cBody.rotation.x = -Math.PI / 2;
  cBody.position.set(0, 0.047, -0.112); car.add(cBody);
  var cVern = S.mesh(new T.BoxGeometry(0.03, 0.004, 0.016), M.brass); cVern.position.set(0, 0.0355, -0.086); car.add(cVern);
  var cHair = S.mesh(new T.BoxGeometry(0.0008, 0.0012, 0.016), M.red, false); cHair.position.set(0, 0.0375, -0.086); car.add(cHair);
  var cKnob = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.012, 20), M.bakelite);
  cKnob.rotation.z = Math.PI / 2; cKnob.position.set(0.037, 0.047, -0.112); car.add(cKnob);
  var pillar = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.24, 24), M.chrome); pillar.position.set(0, 0.17, -0.112); car.add(pillar);
  var armB = S.mesh(new T.BoxGeometry(0.02, 0.026, 0.09), M.alu); armB.position.set(0, 0.2, -0.07); car.add(armB);
  var fineK = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.01, 18), M.bakelite);
  fineK.rotation.z = Math.PI / 2; fineK.position.set(0.018, 0.2, -0.112); car.add(fineK);
  var tube = new T.Group(); tube.position.set(0, 0, -0.032); car.add(tube);
  var tBody = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.1, 28), M.blackPlastic); tBody.position.y = 0.24; tube.add(tBody);
  var tDraw = S.mesh(new T.CylinderGeometry(0.0135, 0.0135, 0.05, 24), M.alu); tDraw.position.y = 0.305; tube.add(tDraw);
  var tEye = S.mesh(new T.CylinderGeometry(0.0125, 0.0145, 0.028, 22), M.bakelite); tEye.position.y = 0.338; tube.add(tEye);
  var tObj = S.mesh(new T.CylinderGeometry(0.011, 0.008, 0.022, 22), M.chrome); tObj.position.y = 0.18; tube.add(tObj);
  var tLens = new T.Mesh(new T.CircleGeometry(0.0075, 20), new T.MeshPhysicalMaterial({ color: 0xcfe6f5, roughness: 0.05, transparent: true, opacity: 0.45, side: T.DoubleSide }));
  tLens.rotation.x = -Math.PI / 2; tLens.position.y = 0.169; tube.add(tLens);
  S.contact(0.34, 0.2, CX, CZ - 0.11, 0.5);

  // the film: a glass plate on a small table, the lens (or the second flat) on it
  var stage = new T.Group(); stage.position.set(CX, 0, CZ); S.scene.add(stage);
  var sTable = S.rounded(0.13, 0.11, 0.03, 0.006, M.darkWood); sTable.rotation.x = -Math.PI / 2; sTable.position.y = 0.015; stage.add(sTable);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xd8ecf0, roughness: 0.03, metalness: 0, transparent: true,
    opacity: 0.4, depthWrite: false, clearcoat: 1, envMapIntensity: 1.6, side: T.DoubleSide });
  var flat = S.mesh(new T.BoxGeometry(0.1, 0.008, 0.08), glassM); flat.position.y = 0.038; flat.renderOrder = 2; stage.add(flat);
  if (!WEDGE) {
    var lensProf = [], NR = 18, rr, sag, RL = Math.max(p.R, 0.05), AP = 0.028;
    for (var li = 0; li <= NR; li++) { rr = AP * li / NR; sag = RL - Math.sqrt(Math.max(RL * RL - rr * rr, 0)); lensProf.push(new T.Vector2(rr, sag)); }
    for (li = NR; li >= 0; li--) { rr = AP * li / NR; lensProf.push(new T.Vector2(rr, AP * AP / (2 * RL) + 0.006)); }
    var lens = new T.Mesh(new T.LatheGeometry(lensProf, 48), glassM);
    lens.position.y = PLATE_Y; lens.renderOrder = 3; lens.castShadow = true; stage.add(lens);
    var lRim = S.mesh(new T.TorusGeometry(AP, 0.0006, 8, 48), new T.MeshStandardMaterial({ color: 0xe8eef2, roughness: 0.3 }));
    lRim.rotation.x = Math.PI / 2; lRim.position.y = PLATE_Y + 0.0002; stage.add(lRim);
  } else {
    var upper = S.mesh(new T.BoxGeometry(0.1, 0.006, 0.08), glassM);
    upper.position.set(0, PLATE_Y + 0.003, 0); upper.rotation.z = -Math.atan2(p.ts, p.L) * 6; upper.renderOrder = 3; stage.add(upper);
    var spacer = S.mesh(new T.BoxGeometry(0.004, 0.0006, 0.08), new T.MeshStandardMaterial({ color: 0xd8c49a, roughness: 0.9 }));
    spacer.position.set(-PAT / 2 + p.L, PLATE_Y + 0.0003, 0); stage.add(spacer);
    var sLab = S.label('spacer', { w: 0.016, ratio: 0.3, color: '#8a7a56', weight: 600 });
    sLab.position.set(-PAT / 2 + p.L, PLATE_Y + 0.001, 0.026); sLab.rotation.x = -Math.PI / 2; stage.add(sLab);
  }

  // the pattern itself, drawn at TRUE size on the film from the kernel's own intensity
  var patTex = S.liveTex(512, 512);
  var pat = new T.Mesh(new T.PlaneGeometry(PAT, PAT), new T.MeshBasicMaterial({ map: patTex, transparent: true, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending }));
  pat.rotation.x = -Math.PI / 2; pat.position.set(CX, PLATE_Y + 0.0012, CZ); pat.renderOrder = 6; S.scene.add(pat);
  var patKey = '';
  function drawPattern() {
    var key = [st.lit ? 1 : 0, st.plate45 ? 1 : 0, st.focused ? 1 : 0, p.lam, p.mu, WEDGE ? p.ts : p.R].join('|');
    if (key === patKey) return;
    patKey = key;
    patTex.draw(function (x, w, h) {
      x.clearRect(0, 0, w, h);
      if (!(st.lit && st.plate45)) return;
      var c = colour(), img = x.createImageData(w, h), i, j, xx, zz, I, a;
      for (j = 0; j < h; j++) {
        for (i = 0; i < w; i++) {
          xx = (i / w - 0.5) * PAT; zz = (j / h - 0.5) * PAT;
          I = WEDGE ? inten(xx + PAT / 2) : inten(Math.sqrt(xx * xx + zz * zz)) ;
          a = Math.min(1, I / 4) * 0.95;
          var o = (j * w + i) * 4;
          img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = a * 255;
        }
      }
      x.putImageData(img, 0, 0);
    });
  }

  // the glass plate at 45 degrees and the lamp
  var p45 = new T.Group(); p45.position.set(CX, 0.085, CZ); S.scene.add(p45);
  var gl45 = S.mesh(new T.BoxGeometry(0.05, 0.0015, 0.05), glassM); gl45.rotation.z = Math.PI / 4; gl45.renderOrder = 2; p45.add(gl45);
  var hold45 = S.mesh(new T.BoxGeometry(0.006, 0.05, 0.008), M.black); hold45.position.set(-0.03, -0.004, 0.026); p45.add(hold45);
  var stem45 = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.09, 14), M.chrome); stem45.position.set(-0.03, -0.045, 0.026); p45.add(stem45);
  var foot45 = S.mesh(new T.CylinderGeometry(0.022, 0.024, 0.008, 20), M.iron); foot45.position.set(-0.03, -0.086, 0.026); p45.add(foot45);
  p45.visible = false;

  var lampG = new T.Group(); lampG.position.set(CX - 0.21, 0, CZ); S.scene.add(lampG);
  var lBox = S.rounded(0.09, 0.12, 0.09, 0.01, M.iron); lBox.position.y = 0.07; lampG.add(lBox);
  var lHole = new T.Mesh(new T.CircleGeometry(0.014, 24), new T.MeshBasicMaterial({ color: 0x5c4a20, toneMapped: false }));
  lHole.rotation.y = Math.PI / 2; lHole.position.set(0.046, 0.085, 0); lampG.add(lHole);
  var lLab = S.label('SODIUM LAMP', { w: 0.062, ratio: 0.18, color: '#e8e2cf', weight: 700 });
  lLab.position.set(0, 0.115, 0.046); lampG.add(lLab);
  var lSwitch = S.mesh(new T.CylinderGeometry(0.007, 0.007, 0.008, 14), M.red); lSwitch.rotation.x = Math.PI / 2;
  lSwitch.position.set(0.02, 0.025, 0.046); lampG.add(lSwitch);
  var lamp = new T.PointLight(0xffc85a, 0, 0, 2); lamp.position.set(CX - 0.16, 0.085, CZ); S.scene.add(lamp);
  S.contact(0.13, 0.13, CX - 0.21, CZ, 0.5);
  var beam = new T.Mesh(new T.CylinderGeometry(0.012, 0.012, 0.16, 16, 1, true),
    new T.MeshBasicMaterial({ color: 0xffd98a, transparent: true, opacity: 0.12, depthWrite: false, side: T.DoubleSide, toneMapped: false }));
  beam.rotation.z = Math.PI / 2; beam.position.set(CX - 0.12, 0.085, CZ); beam.visible = false; S.scene.add(beam);
  var beamDn = new T.Mesh(new T.CylinderGeometry(0.012, 0.012, 0.045, 16, 1, true),
    new T.MeshBasicMaterial({ color: 0xffd98a, transparent: true, opacity: 0.12, depthWrite: false, side: T.DoubleSide, toneMapped: false }));
  beamDn.position.set(CX, 0.062, CZ); beamDn.visible = false; S.scene.add(beamDn);

  S.addApparatus('micro', micro, 'Travelling microscope',
    'The microscope rides on a screw along a centimetre scale read with a vernier: the least count is 0.001 cm. The cross-wire in the eyepiece is set on each fringe in turn.');
  S.addApparatus('film', stage, WEDGE ? 'The two flats and the spacer' : 'Plano-convex lens on a plane plate',
    WEDGE ? 'Two optical flats touching at one edge and held apart at the other by the paper or wire whose thickness you have to find.'
      : (SAMPLE ? SAMPLE + '. ' : '') + 'The curved face rests on the flat plate. The wedge of ' + (LIQUID ? 'liquid' : 'air') + ' between them is what gives the rings.');
  S.addApparatus('p45', p45, 'Glass plate at 45 degrees',
    'A plain glass plate held at 45 degrees over the film: it turns the light from the lamp down onto the film and still lets you look through it from above.');
  S.addApparatus('lamp', lampG, 'Sodium lamp', 'One yellow line at 589.3 nm, so the fringes stay sharp however many you count.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ---------------------------------------------------------------- the view in the eyepiece (HUD)
  var eyeCard = document.createElement('div'); eyeCard.className = 'card';
  eyeCard.appendChild(document.createTextNode('Through the microscope'));
  var eyeCan = document.createElement('canvas'); eyeCan.width = 220; eyeCan.height = 220;
  eyeCan.style.cssText = 'width:190px;height:190px;display:block;margin-top:4px;border-radius:8px';
  eyeCard.appendChild(eyeCan); S.hud.appendChild(eyeCard);
  var ectx = eyeCan.getContext('2d'), eyeKey = '';
  var hudX = S.hudCard('Microscope reads'), hudF = S.hudCard('On the cross-wire');
  function drawEye() {
    var key = [st.lit, st.plate45, st.focused, fmt(st.x, 6)].join('|');
    if (key === eyeKey) return; eyeKey = key;
    var w = eyeCan.width, h = eyeCan.height, c = w / 2, R = c - 6, i, j, col = colour();
    ectx.clearRect(0, 0, w, h);
    ectx.save(); ectx.beginPath(); ectx.arc(c, c, R, 0, Math.PI * 2); ectx.clip();
    ectx.fillStyle = '#07080a'; ectx.fillRect(0, 0, w, h);
    if (st.lit && st.plate45) {
      var img = ectx.createImageData(w, h), xx, zz, I, a, o, blur = st.focused ? 0 : 1;
      for (j = 0; j < h; j++) for (i = 0; i < w; i++) {
        xx = st.x + (i / w - 0.5) * FIELD; zz = (j / h - 0.5) * FIELD;
        I = WEDGE ? inten(xx) : inten(Math.sqrt(xx * xx + zz * zz));
        if (blur) I = 2;
        a = Math.min(1, I / 4);
        o = (j * w + i) * 4;
        img.data[o] = col[0]; img.data[o + 1] = col[1]; img.data[o + 2] = col[2]; img.data[o + 3] = a * 235;
      }
      ectx.putImageData(img, 0, 0);
    }
    ectx.strokeStyle = 'rgba(245,247,250,.92)'; ectx.lineWidth = 1.4;
    ectx.beginPath(); ectx.moveTo(c, c - R); ectx.lineTo(c, c + R); ectx.stroke();
    ectx.beginPath(); ectx.moveTo(c - R, c); ectx.lineTo(c + R, c); ectx.stroke();
    ectx.restore();
    ectx.strokeStyle = 'rgba(90,96,104,.9)'; ectx.lineWidth = 3;
    ectx.beginPath(); ectx.arc(c, c, R, 0, Math.PI * 2); ectx.stroke();
    ectx.fillStyle = '#9aa1ab'; ectx.font = '500 13px "Public Sans", sans-serif';
    ectx.fillText(st.focused ? 'field ' + fmt(FIELD * 1000, 1) + ' mm' : 'out of focus', 8, h - 8);
  }

  function carX(v) { return WEDGE ? v - PAT / 2 : v; }      // the wedge is measured from the contact edge
  function update() {
    car.position.x = carX(st.x);
    lamp.intensity = st.lit ? 0.03 : 0;
    lHole.material.color.setHex(st.lit ? 0xffd45e : 0x5c4a20);
    beam.visible = st.lit; beamDn.visible = st.lit && st.plate45;
    drawPattern(); drawEye();
    hudX.set(fmt((st.x + 0.15) * 100, 4) + ' cm');
    var f = nearestFringe();
    hudF.set(!st.focused ? 'focus first' : f ? (WEDGE ? 'dark fringe ' + f.n : 'dark ring ' + f.n + ', ' + f.side) : 'between fringes');
  }

  // ---------------------------------------------------------------- the human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function lightLamp() {
    if (st.lit) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    return S.hand.tap(lSwitch, 'front').then(function () {
      st.lit = true; update();
      S.say('The lamp is on. Give it a minute to warm up: the yellow line steadies.'); S.render(); return true; });
  }
  function set45() {
    if (st.plate45) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    if (!st.lit) { S.say('Switch the lamp on first.'); return Promise.resolve(false); }
    p45.visible = true; p45.rotation.z = 0.5;
    return S.hand.pinchMove(new T.Vector3(CX + 0.05, 0.12, CZ + 0.05),
      function (k) { return new T.Vector3(CX + 0.05 - 0.05 * k, 0.12 - 0.03 * k, CZ + 0.05 - 0.05 * k); },
      function (k) { p45.rotation.z = 0.5 * (1 - k); }, { ms: 1200, reachMs: 650, hold: 200, mode: 'top' })
      .then(function () { p45.rotation.z = 0; st.plate45 = true; update();
        S.say('The plate is at 45 degrees: it throws the light down onto the film and you still see through it.'); S.render(); return true; });
  }
  function focusMicro() {
    if (st.focused) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    if (!(st.lit && st.plate45)) { S.say('Light the film first: there is nothing to focus on.'); return Promise.resolve(false); }
    return S.hand.tap(fineK).then(function () {
      st.focused = true; update();
      S.say(WEDGE ? 'The straight fringes are sharp, parallel to the contact edge.'
        : 'The rings are sharp, with the dark centre in the middle of the field.'); S.render(); return true; });
  }
  function moveTo(x) {
    if (S.hand.busy) return wait();
    x = Math.max(WEDGE ? 0.0005 : -0.014, Math.min(WEDGE ? 0.029 : 0.014, roundLC(x)));
    var from = st.x;
    if (Math.abs(x - from) < 1e-9) { st.x = x; update(); return Promise.resolve(true); }
    function at(k) { return from + (x - from) * k; }
    var ms = Math.min(1600, 380 + Math.abs(x - from) * 24000);
    return S.hand.pinchMove(new T.Vector3(CX + carX(from) + 0.048, 0.05, CZ - 0.112),
      function (k) { return new T.Vector3(CX + carX(at(k)) + 0.048, 0.05, CZ - 0.112); },
      function (k) { st.x = at(k); update(); }, { ms: ms, reachMs: 600, hold: 140 })
      .then(function () { st.x = x; update(); S.render(); return true; });
  }
  function readScale() {
    if (S.hand.busy) return wait();
    return S.hand.tap(cVern, 'top').then(function () { return true; });
  }

  // ---------------------------------------------------------------- recording
  function record() {
    if (!st.focused) { S.say('Focus the microscope first.'); return false; }
    var f = nearestFringe();
    if (!f) { S.say('The cross-wire is between two fringes. Move the carriage until it sits on a dark ' + (WEDGE ? 'fringe' : 'ring') + '.'); return false; }
    if (WEDGE) {
      if (S.rows.some(function (r) { return r.n === f.n; })) { S.say('Fringe ' + f.n + ' is already in the table. Move on to another one.'); return false; }
      S.addRow({ n: f.n, x: roundLC(st.x) });
      S.say('Fringe ' + f.n + ' read at ' + fmt((roundLC(st.x) + 0.15) * 100, 4) + ' cm.');
      return true;
    }
    if (st.hold === null || st.holdN !== f.n) {
      st.hold = roundLC(st.x); st.holdN = f.n;
      S.say('Ring ' + f.n + ' on the ' + f.side + ' read at ' + fmt((st.hold + 0.15) * 100, 4) + ' cm. Now cross the centre and set the cross-wire on the same ring on the other side.');
      S.render(); return true;
    }
    var d = Math.abs(roundLC(st.x) - st.hold);
    if (d < 1e-6) { S.say('That is the same side again. Cross the centre to the other side of the ring.'); return false; }
    if (S.rows.some(function (r) { return r.n === f.n; })) { st.hold = null; st.holdN = null; S.say('Ring ' + f.n + ' is already in the table.'); return false; }
    S.addRow({ n: f.n, d: d, dsq: d * d });
    S.say('Ring ' + f.n + ': diameter ' + fmt(d * 1000, 3) + ' mm.');
    st.hold = null; st.holdN = null;
    return true;
  }

  function slopeOf(rows, yk) {
    var pts = rows.map(function (r) { return [r.n, r[yk]]; }), L = S.fit.linear(pts);
    return L ? L.m : NaN;
  }
  function resultFor(rows) {
    if (rows.length < 3) return null;
    if (WEDGE) {
      var b = slopeOf(rows, 'x');
      if (!isFinite(b) || b <= 0) return null;
      return { label: 'thickness of the spacer', value: p.lam * p.L / (2 * p.mu * b) * 1e6, unit: 'µm', digits: 2,
        truth: p.ts * 1e6, note: 'Fringe width from the slope of the fringe position against its number: ' + fmt(b * 1000, 4)
          + ' mm; thickness = wavelength x L / (2 mu x fringe width).' };
    }
    var m = slopeOf(rows, 'dsq');
    if (!isFinite(m) || m <= 0) return null;
    return { label: 'R', value: m * p.mu / (4 * p.lam) * 100, unit: 'cm', digits: 2, truth: p.R * 100,
      note: 'Slope of the diameter squared against the ring number is 4 x wavelength x R / mu.' };
  }

  var VIEWS = {
    micro: [[CX + 0.3, 0.42, CZ + 0.34], [CX, 0.16, CZ - 0.08]],
    film: [[CX + 0.1, 0.17, CZ + 0.2], [CX, 0.05, CZ]],
    p45: [[CX + 0.16, 0.2, CZ + 0.28], [CX, 0.085, CZ]],
    lamp: [[CX - 0.08, 0.22, CZ + 0.3], [CX - 0.2, 0.07, CZ]],
    wide: [[CX + 0.24, 0.6, CZ + 0.8], [CX - 0.02, 0.1, CZ - 0.04]],
    book: [[0.72, 0.46, 0.66], [0.7, 0.0, 0.16]]
  };
  update();

  return {
    camera: { pos: [CX + 0.26, 0.62, CZ + 0.88], look: [CX - 0.02, 0.1, CZ - 0.04] },
    views: VIEWS,
    theory: WEDGE ? {
      principle: 'Two optical flats touching at one edge and held apart at the other by a spacer enclose a wedge of '
        + 'air whose thickness grows along the plate. The light reflected from the two faces of that film interferes, '
        + 'and the reflection at the lower face brings an extra half wave, so the fringes are straight, parallel to '
        + 'the contact edge, and equally spaced.',
      formula: 'β = λ L / (2 μ t)',
      formulaNote: 'β = fringe width, L = contact edge to the spacer, t = thickness of the spacer',
      more: ['Measuring a fringe width of a quarter of a millimetre gives a thickness of a few microns, which no '
        + 'micrometer can reach.',
        'With L = ' + fmt(p.L * 100, 1) + ' cm and sodium light the fringe width here is about '
        + fmt(p.lam * p.L / (2 * p.mu * p.ts) * 1000, 3) + ' mm, so count ten fringes at a time.'],
      precautions: 'Do not press the flats together: a trapped grit scratches them. Set the cross-wire on the middle '
        + 'of a dark fringe and always turn the screw the same way, so that the backlash of the screw never enters a '
        + 'reading.'
    } : {
      principle: 'Between the curved face of the lens and the flat plate there is a film whose thickness grows as the '
        + 'square of the distance from the point of contact. The light reflected from its two faces interferes; the '
        + 'reflection at the lower face brings an extra half wave, so the point of contact is dark and the dark '
        + 'rings come where twice the optical thickness is a whole number of wavelengths.',
      formula: 'Dₙ² = 4 n λ R / μ',
      formulaNote: 'Dₙ = diameter of the n-th dark ring, R = radius of curvature, μ = index of the film',
      more: ['So a graph of the diameter squared against the ring number is a straight line through the origin, and '
        + 'its slope gives R. Taking the difference between two rings removes any error in finding the centre.',
        LIQUID ? 'The film here is a liquid of index ' + fmt(p.mu, 3) + ', so every ring comes in by the square root '
          + 'of that index.' : 'The rings crowd together as you go out, because the diameter grows only as the square '
          + 'root of the ring number.'],
      precautions: 'Never slide the lens on the plate. Set the cross-wire on the middle of a dark ring and turn the '
        + 'screw always the same way, so the backlash of the screw never enters a reading. Read the same ring on both '
        + 'sides of the centre.'
    },
    book: { title: WEDGE ? 'Expt. — Air wedge' : 'Expt. — Newton\'s rings',
      lines: ['Travelling microscope, least count 0.001 cm.',
        'Sodium light, wavelength ' + fmt(lamNm(), 1) + ' nm.',
        WEDGE ? 'beta = wavelength x L / (2 mu x t)' : 'D(n) squared = 4 n x wavelength x R / mu',
        'Turn the screw one way only.'],
      columns: WEDGE ? [
        { label: 'Fringe n', get: function (r) { return r.n; } },
        { label: 'Reading (cm)', get: function (r) { return fmt((r.x + 0.15) * 100, 4); } },
        { label: 'x from the edge (mm)', get: function (r) { return fmt(r.x * 1000, 3); } }] : [
        { label: 'Ring n', get: function (r) { return r.n; } },
        { label: 'Diameter (mm)', get: function (r) { return fmt(r.d * 1000, 3); } },
        { label: 'D² (mm²)', get: function (r) { return fmt(r.dsq * 1e6, 4); } }],
      at: [0.7, 0.1, 0.1] },
    graph: WEDGE ? { x: function (r) { return r.n; }, y: function (r) { return r.x * 1000; },
      xlabel: 'fringe number n', ylabel: 'position (mm)', x0: 0, y0: 0,
      line: function (pts) { var L = S.fit.linear(pts); return L ? function (x) { return L.m * x + L.c; } : null; } }
      : { x: function (r) { return r.n; }, y: function (r) { return r.dsq * 1e6; },
        xlabel: 'ring number n', ylabel: 'D² (mm²)', x0: 0, y0: 0,
        line: function (pts) { var L = S.fit.linear(pts); return L ? function (x) { return L.m * x + L.c; } : null; } },
    result: resultFor,
    tol: 0.01,
    chips: ['Why is the centre dark?', 'Why read the same ring on both sides?', 'What is backlash and why does it matter?',
      'Check my readings', WEDGE ? 'Why are the fringes straight?' : 'What happens if the film is a liquid?'],
    viva: WEDGE ? [['The fringes of an air wedge are straight because',
      ['the thickness grows evenly along the plate', 'the plates are square', 'the light is yellow'], 0,
      'Equal thickness means equal spacing, and lines of equal thickness run parallel to the contact edge.'],
      ['A thicker spacer makes the fringes', ['closer together', 'wider apart', 'unchanged'], 0,
        'The fringe width is inversely proportional to the thickness of the spacer.']]
      : [['The centre of the Newton\'s rings pattern is dark because',
        ['the reflection at the lower surface adds half a wave', 'the film is thickest there', 'the lens absorbs light'], 0,
        'At zero thickness the only path difference is that half wave, so the two reflections cancel.'],
        ['Why is the difference of two rings used rather than one ring alone?',
          ['It cancels any error in finding the centre', 'It is quicker', 'The rings are not round'], 0,
          'D(n)² - D(m)² = 4 (n - m) x wavelength x R removes the centre from the answer.']],
    askState: function () {
      var f = nearestFringe();
      return { set_up: WEDGE ? 'air wedge' : 'Newton rings', lamp_on: st.lit, plate_at_45: st.plate45,
        microscope_focused: st.focused, microscope_reads_cm: +((st.x + 0.15) * 100).toFixed(4),
        on_the_cross_wire: f ? ((WEDGE ? 'dark fringe ' : 'dark ring ') + f.n + (WEDGE ? '' : ', ' + f.side)) : 'between fringes',
        wavelength_nm: +lamNm().toFixed(1), film_index: p.mu, readings_taken: S.rows.length,
        held_first_side_cm: st.hold === null ? null : +((st.hold + 0.15) * 100).toFixed(4),
        least_count_cm: 0.001 };
    },
    steps: [
      { id: 'setup', title: 'Light the film', view: 'film', render: function (u) {
        u.h2('Light the film and focus the microscope');
        u.p('The sodium lamp shines sideways onto a glass plate held at 45 degrees over the film. The plate throws the '
          + 'light straight down onto the ' + (WEDGE ? 'wedge' : 'lens and plate') + ' and still lets the microscope '
          + 'look through it from above.');
        u.task('1. Switch the lamp on', st.lit, st.lit ? 'Warm and steady' : 'Press the switch on the lamp house')
          .add(u.button(st.lit ? 'Lamp on' : 'Switch the lamp on', function () { lightLamp(); }, !st.lit, st.lit || S.hand.busy));
        u.task('2. Set the plate at 45 degrees', st.plate45, st.plate45 ? 'The film is lit from above' : 'Swing the plate down over the film')
          .add(u.button(st.plate45 ? 'Set' : 'Set the 45 degree plate', function () { set45(); }, !st.plate45, st.plate45 || !st.lit || S.hand.busy));
        u.task('3. Focus the microscope', st.focused, st.focused ? (WEDGE ? 'Straight fringes, sharp' : 'Sharp rings with a dark centre') : 'Rack the tube down until the fringes are sharp')
          .add(u.button(st.focused ? 'Focused' : 'Focus the microscope', function () { focusMicro(); }, !st.focused, st.focused || !st.plate45 || S.hand.busy));
        u.note('The microscope reads on a centimetre scale through a vernier: the least count is 0.001 cm. Always turn '
          + 'the screw the same way while you take a set of readings, so the play in the screw never enters them.');
        u.next('Next: measure the fringes', st.lit && st.plate45 && st.focused);
      },
      ok: function () { return st.lit && st.plate45 && st.focused; },
      auto: function () { return lightLamp().then(set45).then(focusMicro); } },

      { id: 'measure', title: WEDGE ? 'Measure the fringes' : 'Measure the rings', view: 'micro', render: function (u) {
        u.h2(WEDGE ? 'Set the cross-wire on each dark fringe' : 'Measure the diameter of each dark ring');
        u.p(WEDGE ? 'Run the cross-wire along the fringes, setting it on the middle of every fifth dark fringe and '
          + 'reading the scale each time. The slope of the reading against the fringe number is the fringe width.'
          : 'Run the cross-wire out to a ring on one side of the centre and read the scale; cross the centre to the '
          + 'same ring on the other side and read again. The difference is the diameter of that ring.');
        u.slider('Move the carriage to', WEDGE ? 0.5 : -14, WEDGE ? 29 : 14, 0.001, function () { return st.xSet * 1000; },
          function (x) { st.xSet = x / 1000; }, 'mm', 3);
        u.row(u.button('Move the carriage', function () { moveTo(st.xSet); S.render(); }, true, S.hand.busy),
          u.button('Read the vernier', function () { readScale(); }, false, S.hand.busy));
        function nudge(d) { return function () { st.xSet = st.x + d; moveTo(st.x + d); S.render(); }; }
        u.row(u.button('− 0.1 mm', nudge(-1e-4), false, S.hand.busy), u.button('− 0.01 mm', nudge(-1e-5), false, S.hand.busy),
          u.button('+ 0.01 mm', nudge(1e-5), false, S.hand.busy), u.button('+ 0.1 mm', nudge(1e-4), false, S.hand.busy));
        u.row(u.button(WEDGE ? 'Go to the next fringe' : 'Go to the next ring', function () {
          var want = WEDGE ? [5, 10, 15, 20, 25] : [4, 6, 8, 10, 12, 14], i, got, target = null;
          for (i = 0; i < want.length; i++) {
            got = S.rows.some(function (r) { return r.n === want[i]; });
            if (!got) { target = want[i]; break; }
          }
          if (target === null) { S.say('You have all the readings you need.'); return; }
          var x0 = darkAt(target);
          moveTo(st.hold !== null && st.holdN === target ? -x0 : x0).then(function () { S.render(); });
        }, false, S.hand.busy));
        u.live(function () { var f = nearestFringe();
          return 'Reads ' + fmt((st.x + 0.15) * 100, 4) + ' cm · ' + (f ? ((WEDGE ? 'dark fringe ' : 'dark ring ') + f.n + (WEDGE ? '' : ' on the ' + f.side)) : 'between fringes'); });
        u.row(u.button('Set the cross-wire and record', function () { record(); S.render(); }, true, S.hand.busy));
        u.h3('Observation table'); u.table();
        u.next('Next: graph and result', S.rows.length >= 4);
        if (S.rows.length < 4) u.p(S.rows.length + ' of at least 4 ' + (WEDGE ? 'fringes' : 'rings') + ' recorded.');
      },
      ok: function () { return S.rows.length >= 4; },
      auto: function () {
        var want = WEDGE ? [5, 10, 15, 20, 25] : [4, 6, 8, 10, 12], seq = Promise.resolve();
        want.forEach(function (n) {
          seq = seq.then(function () {
            var x0 = darkAt(n);
            if (WEDGE) return moveTo(x0).then(readScale).then(function () { record(); });
            return moveTo(-x0).then(readScale).then(function () { record(); })
              .then(function () { return moveTo(x0); }).then(readScale).then(function () { record(); });
          });
        });
        return seq;
      } }
    ],
    tick: function () { update(); }
  };
});
