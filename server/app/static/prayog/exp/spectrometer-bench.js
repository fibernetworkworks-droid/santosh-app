/* Prayogshala studio module: THE PRISM SPECTROMETER BENCH. One rig for five B.Sc. set-ups - the refracting angle of a
   prism from its two reflected images, the refractive index by minimum deviation, the dispersive power and Cauchy
   constants from the mercury lines, and a plane transmission grating at normal incidence for wavelength and for
   resolving power. A cast tripod carries the divided circle (half a degree a division, two verniers, least count
   1 minute), the levelled prism table, a collimator with its slit and a telescope with a cross-wire; the gloved hand
   turns the table, swings the telescope and reads the verniers, and the field of view is drawn as the observer sees
   it. Every angle comes from the kernels: `spectrometer` (Snell face by face with a Cauchy n(lambda), the minimum
   deviation found by scanning the real trace, the prism angle from reflections) and `planegrating` (the N-slit
   intensity, its own maximum and its first dark edge). */
HoolaStudio.define('spectrometer-bench', function (S) {
  var T = S.T, M = S.M, KS = window.HoolaKernels.K.spectrometer, KG = window.HoolaKernels.K.planegrating;
  var DEG = Math.PI / 180, R2D = 180 / Math.PI;
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var GRATING = S.lab.kernel === 'planegrating';
  var MODE = BASE === 'spectrometer-prism-angle' ? 'angle' : BASE === 'prism-index-spectrometer' ? 'index'
    : BASE === 'prism-dispersive-power' ? 'disp' : BASE === 'grating-wavelength-spectrometer' ? 'glam' : 'grp';
  var p = window.HoolaKernels.paramsFor(GRATING ? 'planegrating' : 'spectrometer', S.lab.params);
  (S.lab.knobs || []).forEach(function (k) {           // the hidden unknowns of this lab (glass, grating, line)
    if (k.hidden && isFinite(k.value) && p[k.param] !== undefined) p[k.param] = +k.value * (+k.k || 1);
  });
  var LC = 1 / 60;                                      // vernier least count: one minute of arc, in degrees
  var CX = 0.02, CZ = -0.22, RC = 0.17, ROT = -30;   // the optical axis runs across the bench at 30 degrees                // centre of the instrument, radius of the divided circle
  var AXY = 0.118;                                      // height of the optical axis above the bench
  var AD = GRATING ? 60 : p.A * R2D;                     // refracting angle of the prism, degrees
  var HG = [404.656, 435.833, 546.074, 576.960, 579.066];   // mercury lines, nm (NIST)
  var LINES = MODE === 'disp' ? HG : [p.lam * 1e9];
  var LAMP = MODE === 'disp' ? 'mercury' : 'sodium';
  var FOV = 3.2;                                        // field of view of the telescope, degrees
  var st = { tel: 0, telSet: 0, iDeg: 50, iSet: 50, focused: false, slit: false, placed: false, normal: false,
    direct: null, hold: [], lamIdx: MODE === 'disp' ? 1 : 0, Nset: 2000, step90: false, reflSet: false };

  function fmt(v, d) { return (Math.round(v * Math.pow(10, d)) / Math.pow(10, d)).toFixed(d); }
  function roundLC(deg) { return Math.round(deg / LC) * LC; }
  function lamNm() { return LINES[Math.min(st.lamIdx, LINES.length - 1)]; }
  function colourOf(nm) {                               // a plain visible-spectrum colour for a line
    if (nm < 420) return '#8a5cd8'; if (nm < 455) return '#5560e0'; if (nm < 492) return '#2e9ad8';
    if (nm < 560) return '#46c25a'; if (nm < 585) return '#f2d13c'; if (nm < 620) return '#f09030';
    return '#e04b3a';
  }

  // ---------------------------------------------------------------- physics from the kernels
  function devOf(nm, iDeg) {                            // deviation of the beam of this wavelength, degrees
    var q = Object.assign({}, p, { lam: nm * 1e-9, i: iDeg * DEG });
    var a = KS.angles(q, q.i);
    return a === null ? null : a[3] * R2D;
  }
  function minDev(nm) {                                 // what the student finds by turning the table to and fro
    var q = Object.assign({}, p, { lam: nm * 1e-9 });
    var m = KS.measure(q);
    return { dm: m.dm * R2D, i: m.i_min * R2D };
  }
  function nOf(nm) { return p.n0 + p.nB / (nm * nm * 1e-18); }
  function orderTheta(m, nm) {                          // grating: the order's own maximum, degrees
    var q = Object.assign({}, p, { lam: (nm === undefined ? lamNm() : nm) * 1e-9, N: st.Nset });
    var th = KG.orderTheta(q, m);
    return th === null ? null : th * R2D;
  }
  function gratingRP(N) {
    var q = Object.assign({}, p, { N: N, lam: lamNm() * 1e-9 });
    var r = KG.measure(q);
    return { rp: r.rp, dlam: r.dlam * 1e9, disp: r.disp };
  }
  function reflAt() { return 180 - AD; }                // the two reflected images sit at +- (180 - A)

  function fieldLines() {                               // what is in the telescope's field: {T, nm, label}
    var out = [], i, d, th;
    if (MODE === 'angle') {
      if (st.placed) { out.push({ T: reflAt(), nm: lamNm(), label: 'reflected, face 1' });
        out.push({ T: -reflAt(), nm: lamNm(), label: 'reflected, face 2' }); }
      else out.push({ T: 0, nm: lamNm(), label: 'direct' });
      return out;
    }
    if (GRATING) {
      if (!st.placed) return [{ T: 0, nm: lamNm(), label: 'direct' }];
      out.push({ T: 0, nm: lamNm(), label: 'direct (zero order)' });
      for (i = 1; i <= 2; i++) {
        th = orderTheta(i);
        if (th !== null) { out.push({ T: th, nm: lamNm(), label: 'order ' + i + ', right' });
          out.push({ T: -th, nm: lamNm(), label: 'order ' + i + ', left' }); }
      }
      return out;
    }
    if (!st.placed) return [{ T: 0, nm: lamNm(), label: 'direct' }];
    for (i = 0; i < LINES.length; i++) {
      d = devOf(LINES[i], st.iDeg);
      if (d !== null) out.push({ T: d, nm: LINES[i], label: fmt(LINES[i], 1) + ' nm' });
    }
    return out;
  }

  // ---------------------------------------------------------------- the apparatus
  function arc(r, Tdeg, y) { var a = (Tdeg + ROT) * DEG;
    return new T.Vector3(CX + r * Math.cos(a), y === undefined ? AXY : y, CZ + r * Math.sin(a)); }

  var base = new T.Group(); S.scene.add(base);
  [0, 120, 240].forEach(function (a) {                   // a cast three-legged base
    var leg = S.rounded(0.085, 0.05, 0.016, 0.006, M.iron); leg.rotation.x = -Math.PI / 2;
    leg.position.set(CX + 0.1 * Math.cos(a * DEG), 0.012, CZ - 0.1 * Math.sin(a * DEG)); leg.rotation.z = -a * DEG; base.add(leg);
    var foot = S.mesh(new T.CylinderGeometry(0.011, 0.013, 0.006, 18), M.iron);
    foot.position.set(CX + 0.135 * Math.cos(a * DEG), 0.004, CZ - 0.135 * Math.sin(a * DEG)); base.add(foot);
  });
  var column = S.mesh(new T.CylinderGeometry(0.035, 0.05, 0.05, 32), M.iron); column.position.set(CX, 0.026, CZ); base.add(column);
  S.contact(0.34, 0.34, CX, CZ, 0.5);

  // the divided circle: half a degree to a division, numbered every 10 degrees
  var circTex = S.canvasTex(2048, 2048, function (x, w) {
    var c = w / 2, R = c - 10, i, a, len;
    x.clearRect(0, 0, w, w);
    x.fillStyle = '#d8b25c'; x.beginPath(); x.arc(c, c, R, 0, Math.PI * 2); x.fill();
    x.fillStyle = '#f3ead2'; x.beginPath(); x.arc(c, c, R * 0.995, 0, Math.PI * 2); x.fill();
    x.fillStyle = '#d8b25c'; x.beginPath(); x.arc(c, c, R * 0.80, 0, Math.PI * 2); x.fill();
    x.strokeStyle = '#1b1b1b'; x.fillStyle = '#1b1b1b';
    for (i = 0; i < 720; i++) {
      a = i * 0.5 * Math.PI / 180;
      len = i % 20 === 0 ? 0.12 : (i % 10 === 0 ? 0.08 : 0.045);
      x.lineWidth = i % 20 === 0 ? 4 : 2;
      x.beginPath();
      x.moveTo(c + Math.sin(a) * R * 0.985, c - Math.cos(a) * R * 0.985);
      x.lineTo(c + Math.sin(a) * R * (0.985 - len), c - Math.cos(a) * R * (0.985 - len));
      x.stroke();
    }
    x.font = '600 42px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
    for (i = 0; i < 36; i++) {
      a = i * 10 * Math.PI / 180;
      x.save(); x.translate(c + Math.sin(a) * R * 0.78, c - Math.cos(a) * R * 0.78); x.rotate(a);
      x.fillText(String(i * 10), 0, 0); x.restore();
    }
  });
  var circle = S.mesh(new T.CylinderGeometry(RC, RC, 0.015, 96), [M.brass, new T.MeshStandardMaterial({ map: circTex, roughness: 0.42, metalness: 0.2 }), M.brass]);
  circle.position.set(CX, 0.0575, CZ); base.add(circle);
  var circRim = S.mesh(new T.TorusGeometry(RC, 0.0035, 10, 96), M.brass); circRim.rotation.x = Math.PI / 2; circRim.position.set(CX, 0.058, CZ); base.add(circRim);

  // prism table: three levelling screws, a clamp and the sample
  var tableG = new T.Group(); tableG.position.set(CX, 0, CZ); S.scene.add(tableG);
  var tStem = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.02, 20), M.chrome); tStem.position.y = 0.075; tableG.add(tStem);
  var tTop = S.mesh(new T.CylinderGeometry(0.055, 0.055, 0.005, 48), M.steel); tTop.position.y = 0.0865; tableG.add(tTop);
  [90, 210, 330].forEach(function (a) {
    var sc = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.012, 14), M.brass);
    sc.position.set(0.04 * Math.cos(a * DEG), 0.0805, -0.04 * Math.sin(a * DEG)); tableG.add(sc);
  });
  var tLines = S.canvasTex(256, 256, function (x, w) {
    x.clearRect(0, 0, w, w); x.strokeStyle = 'rgba(30,30,30,.55)'; x.lineWidth = 3;
    [0, 60, 120].forEach(function (a) { x.beginPath();
      x.moveTo(w / 2 - Math.cos(a * Math.PI / 180) * w * 0.45, w / 2 - Math.sin(a * Math.PI / 180) * w * 0.45);
      x.lineTo(w / 2 + Math.cos(a * Math.PI / 180) * w * 0.45, w / 2 + Math.sin(a * Math.PI / 180) * w * 0.45); x.stroke(); });
  });
  var tMark = new T.Mesh(new T.CircleGeometry(0.054, 48), new T.MeshStandardMaterial({ map: tLines, transparent: true, roughness: 0.5 }));
  tMark.rotation.x = -Math.PI / 2; tMark.position.y = 0.0892; tableG.add(tMark);

  // the prism (or the grating in its frame) standing on the table
  var sample = new T.Group(); sample.position.y = 0.089; tableG.add(sample);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xcfe6ea, roughness: 0.02, metalness: 0, transparent: true,
    opacity: 0.58, depthWrite: false, clearcoat: 1, clearcoatRoughness: 0.02, envMapIntensity: 1.8, side: T.DoubleSide });
  if (!GRATING) {
    var side = 0.05, A2 = AD * DEG / 2, sh = new T.Shape();
    sh.moveTo(0, side * Math.cos(A2)); sh.lineTo(-side * Math.sin(A2), 0); sh.lineTo(side * Math.sin(A2), 0); sh.closePath();
    var pg = new T.ExtrudeGeometry(sh, { depth: 0.042, bevelEnabled: true, bevelThickness: 0.0008, bevelSize: 0.0008, bevelSegments: 2 });
    var prism = new T.Mesh(pg, glassM); prism.rotation.x = -Math.PI / 2; prism.renderOrder = 3;
    prism.castShadow = true; sample.add(prism);
    var edges = new T.LineSegments(new T.EdgesGeometry(pg, 20), new T.LineBasicMaterial({ color: 0xf2f6f8, transparent: true, opacity: 0.85, depthWrite: false, toneMapped: false }));
    edges.rotation.x = -Math.PI / 2; edges.renderOrder = 4; sample.add(edges);
    var gnd = S.label(fmt(AD, 0) + '°', { w: 0.016, ratio: 0.7, color: '#6b7280', weight: 700 });
    gnd.position.set(0, 0.0425, -0.022); gnd.rotation.x = -Math.PI / 2; sample.add(gnd);
  } else {
    var frame = new T.Group(); sample.add(frame);
    var gl = S.mesh(new T.BoxGeometry(0.0016, 0.04, 0.045), glassM); gl.position.set(0, 0.03, 0); gl.renderOrder = 3; frame.add(gl);
    [[0, 0.0505, 0, 0.006, 0.007, 0.055], [0, 0.0095, 0, 0.006, 0.007, 0.055],
      [0, 0.03, 0.0255, 0.006, 0.05, 0.006], [0, 0.03, -0.0255, 0.006, 0.05, 0.006]].forEach(function (a) {
      var b = S.mesh(new T.BoxGeometry(a[3], a[4], a[5]), M.bakelite); b.position.set(a[0], a[1], a[2]); frame.add(b); });
    var stem = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.01, 12), M.chrome); stem.position.y = 0.004; frame.add(stem);
    var gLab = S.label('15 000 / inch', { w: 0.028, ratio: 0.2, color: '#d7dbe0', weight: 600 });
    gLab.position.set(0.0035, 0.0505, 0); gLab.rotation.y = Math.PI / 2; frame.add(gLab);
  }
  sample.visible = false;

  // a tube: used for both the collimator and the telescope
  function tube(len, inner, name) {
    var g = new T.Group();
    var body = S.mesh(new T.CylinderGeometry(0.0225, 0.0225, len * 0.62, 36), M.blackPlastic);
    body.rotation.z = Math.PI / 2; body.position.x = inner + len * 0.31; g.add(body);
    var draw = S.mesh(new T.CylinderGeometry(0.019, 0.019, len * 0.42, 32), M.alu);
    draw.rotation.z = Math.PI / 2; draw.position.x = inner + len * 0.79; g.add(draw);
    var obj = S.mesh(new T.CylinderGeometry(0.0235, 0.0235, 0.014, 36), M.iron);
    obj.rotation.z = Math.PI / 2; obj.position.x = inner + 0.007; g.add(obj);
    var lens = new T.Mesh(new T.CircleGeometry(0.019, 32), new T.MeshPhysicalMaterial({ color: 0xcfe6f5, roughness: 0.05, transparent: true, opacity: 0.4, side: T.DoubleSide }));
    lens.rotation.y = -Math.PI / 2; lens.position.x = inner + 0.0005; g.add(lens);
    var knob = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 18), M.bakelite);
    knob.rotation.x = Math.PI / 2; knob.position.set(inner + len * 0.55, -0.021, 0); g.add(knob);
    var arm = S.mesh(new T.BoxGeometry(inner + 0.04, 0.009, 0.022), M.iron);
    arm.position.set((inner + 0.04) / 2, -0.033, 0); g.add(arm);
    var post = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.05, 18), M.iron);
    post.position.set(inner + len * 0.33, -0.054, 0); g.add(post);
    g.userData.name = name; g.userData.outer = inner + len;
    return g;
  }

  // collimator: fixed, pointing at the centre from -x, with its slit assembly at the far end
  var coll = tube(0.30, 0.10, 'collimator');
  coll.rotation.y = -(180 + ROT) * DEG;      // its tube runs out along the optical axis, away from the centre
  coll.position.set(CX, AXY, CZ);
  S.scene.add(coll);
  var slitHead = new T.Group(); slitHead.position.copy(arc(0.405, 180)); slitHead.rotation.y = -(180 + ROT) * DEG; S.scene.add(slitHead);
  var sh2 = S.mesh(new T.CylinderGeometry(0.026, 0.026, 0.03, 28), M.iron); sh2.rotation.z = Math.PI / 2; slitHead.add(sh2);
  var sKnob = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.009, 16), M.brass); sKnob.rotation.x = Math.PI / 2; sKnob.position.set(0, 0.026, 0); slitHead.add(sKnob);
  var slitPlate = S.mesh(new T.BoxGeometry(0.002, 0.03, 0.03), M.black); slitPlate.position.x = -0.016; slitHead.add(slitPlate);
  var slitGap = new T.Mesh(new T.PlaneGeometry(0.0012, 0.016), new T.MeshBasicMaterial({ color: 0xfff2c0, toneMapped: false }));
  slitGap.rotation.y = -Math.PI / 2; slitGap.position.x = -0.0172; slitHead.add(slitGap);

  // telescope: swings round the circle; a vernier plate under it rides on the scale
  var tele = tube(0.30, 0.10, 'telescope');
  var teleArm = new T.Group(); teleArm.position.set(CX, 0, CZ); S.scene.add(teleArm);
  tele.position.y = AXY; teleArm.add(tele);
  var eyep = S.mesh(new T.CylinderGeometry(0.014, 0.016, 0.034, 24), M.bakelite);
  eyep.rotation.z = Math.PI / 2; eyep.position.set(0.415, AXY, 0); teleArm.add(eyep);
  var vern = new T.Group(); teleArm.add(vern);
  var vPlate = S.mesh(new T.BoxGeometry(0.05, 0.004, 0.03), M.brass); vPlate.position.set(RC - 0.012, 0.0665, 0); vern.add(vPlate);
  var vWin = new T.Mesh(new T.PlaneGeometry(0.03, 0.016), new T.MeshBasicMaterial({ color: 0x101214, transparent: true, opacity: 0.35 }));
  vWin.rotation.x = -Math.PI / 2; vWin.position.set(RC - 0.012, 0.0686, 0); vern.add(vWin);
  var vMag = S.mesh(new T.CylinderGeometry(0.009, 0.011, 0.016, 20), M.brass); vMag.position.set(RC - 0.012, 0.077, 0.018); vern.add(vMag);
  var clampK = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.01, 6), M.black); clampK.position.set(RC + 0.012, 0.072, 0); vern.add(clampK);

  // the lamp house behind the slit
  var lampG = new T.Group(); lampG.position.copy(arc(0.52, 180, 0)); lampG.rotation.y = -ROT * DEG; S.scene.add(lampG);
  var lBox = S.rounded(0.1, 0.13, 0.1, 0.01, M.iron); lBox.position.y = 0.075; lampG.add(lBox);
  var lFoot = S.mesh(new T.BoxGeometry(0.12, 0.012, 0.11), M.iron); lFoot.position.y = 0.006; lampG.add(lFoot);
  var lHole = new T.Mesh(new T.CircleGeometry(0.016, 24), new T.MeshBasicMaterial({ color: LAMP === 'mercury' ? 0xdbe8ff : 0xffd45e, toneMapped: false }));
  lHole.rotation.y = Math.PI / 2; lHole.position.set(0.051, AXY, 0); lampG.add(lHole);
  var lTube = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.07, 20), new T.MeshStandardMaterial({ color: 0xf6f3e8, emissive: LAMP === 'mercury' ? 0x5a7ab0 : 0x9a7a14, roughness: 0.3 }));
  lTube.rotation.z = Math.PI / 2; lTube.position.set(0, AXY, 0); lampG.add(lTube);
  var lLab = S.label(LAMP === 'mercury' ? 'MERCURY LAMP' : 'SODIUM LAMP', { w: 0.07, ratio: 0.16, color: '#e8e2cf', weight: 700 });
  lLab.position.set(0, 0.12, 0.051); lampG.add(lLab);
  var lamp = new T.PointLight(LAMP === 'mercury' ? 0xbcd4ff : 0xffcf6a, 0.02, 0, 2); lamp.position.set(0.06, AXY, 0); lampG.add(lamp);
  S.contact(0.17, 0.17, lampG.position.x, lampG.position.z, 0.5);

  // a faint beam from the collimator to the sample, and out to the telescope
  var beamM = new T.LineBasicMaterial({ color: 0xffd98a, transparent: true, opacity: 0.5, depthWrite: false, toneMapped: false });
  var beamIn = new T.Line(new T.BufferGeometry(), beamM); beamIn.renderOrder = 7; S.scene.add(beamIn);
  var beamsOut = [];
  for (var bi = 0; bi < 6; bi++) {
    var bl = new T.Line(new T.BufferGeometry(), new T.LineBasicMaterial({ color: 0xffd98a, transparent: true, opacity: 0.5, depthWrite: false, toneMapped: false }));
    bl.visible = false; bl.renderOrder = 7; S.scene.add(bl); beamsOut.push(bl);
  }

  S.addApparatus('circle', base, 'Spectrometer and its divided circle',
    'A cast tripod carries a circle divided to half a degree, read through two verniers 180 degrees apart; the least count is one minute of arc.');
  S.addApparatus('coll', coll, 'Collimator',
    'A narrow slit at the focus of the collimator lens, so the light leaving it is parallel. The screw at the head opens and closes the slit.');
  S.addApparatus('tele', teleArm, 'Telescope on the circle',
    'Swings round the circle on its own arm, carrying the vernier. A cross-wire in the eyepiece is set on each image.');
  S.addApparatus('table', tableG, GRATING ? 'Grating table' : 'Prism table',
    'Three levelling screws set the table, so the faces of the ' + (GRATING ? 'grating' : 'prism') + ' stand vertical.');
  S.addApparatus('lamp', lampG, LAMP === 'mercury' ? 'Mercury lamp' : 'Sodium lamp',
    LAMP === 'mercury' ? 'Gives separate violet, green and yellow lines, so the glass can be measured colour by colour.'
      : 'Gives one yellow line at 589.3 nm, so there is a single sharp image to set on.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ---------------------------------------------------------------- the view through the telescope (HUD)
  var eyeCard = document.createElement('div'); eyeCard.className = 'card';
  eyeCard.appendChild(document.createTextNode('Through the telescope'));
  var eyeCan = document.createElement('canvas'); eyeCan.width = 300; eyeCan.height = 190;
  eyeCan.style.cssText = 'width:200px;height:127px;display:block;margin-top:4px;border-radius:8px';
  eyeCard.appendChild(eyeCan); S.hud.appendChild(eyeCard);
  var ectx = eyeCan.getContext('2d');
  var hudT = S.hudCard('Telescope reads'), hudI = S.hudCard(GRATING ? 'Grating' : 'Prism table'), hudS = S.hudCard('On the cross-wire');
  function drawEye() {
    var w = eyeCan.width, h = eyeCan.height, cx = w / 2, cy = h / 2, R = h / 2 - 6;
    ectx.clearRect(0, 0, w, h);
    ectx.save(); ectx.beginPath(); ectx.arc(cx, cy, R, 0, Math.PI * 2); ectx.clip();
    ectx.fillStyle = '#0b0d10'; ectx.fillRect(0, 0, w, h);
    if (st.focused) {
      fieldLines().forEach(function (L) {
        var off = L.T - st.tel;
        if (Math.abs(off) > FOV / 2) return;
        var x = cx + off / (FOV / 2) * R, wd = st.slit ? 2.6 : 7;
        var g = ectx.createLinearGradient(x - wd, 0, x + wd, 0);
        g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(0.5, colourOf(L.nm)); g.addColorStop(1, 'rgba(0,0,0,0)');
        ectx.fillStyle = g; ectx.fillRect(x - wd, cy - R * 0.72, wd * 2, R * 1.44);
        ectx.fillStyle = colourOf(L.nm); ectx.fillRect(x - wd / 2.4, cy - R * 0.72, wd / 1.2, R * 1.44);
      });
    } else {
      ectx.fillStyle = 'rgba(190,170,110,.22)'; ectx.fillRect(cx - R * 0.5, cy - R * 0.7, R, R * 1.4);
    }
    ectx.strokeStyle = 'rgba(235,238,242,.9)'; ectx.lineWidth = 1.2;
    ectx.beginPath(); ectx.moveTo(cx, cy - R); ectx.lineTo(cx, cy + R); ectx.stroke();
    ectx.beginPath(); ectx.moveTo(cx - R, cy); ectx.lineTo(cx + R, cy); ectx.stroke();
    ectx.restore();
    ectx.strokeStyle = 'rgba(90,96,104,.9)'; ectx.lineWidth = 3;
    ectx.beginPath(); ectx.arc(cx, cy, R, 0, Math.PI * 2); ectx.stroke();
    ectx.fillStyle = '#9aa1ab'; ectx.font = '500 13px "Public Sans", sans-serif'; ectx.textAlign = 'left';
    ectx.fillText(st.focused ? 'field ' + FOV.toFixed(1) + '°' : 'out of focus', 6, h - 6);
  }
  function onWire() {
    var best = null, d;
    fieldLines().forEach(function (L) { d = Math.abs(L.T - st.tel); if (d < 0.08 && (best === null || d < best.d)) best = { L: L, d: d }; });
    return best ? best.L : null;
  }

  // ---------------------------------------------------------------- keeping the 3D in step
  function update() {
    teleArm.rotation.y = -(st.tel + ROT) * DEG;
    if (!GRATING) sample.rotation.y = MODE === 'angle' ? -(270 + ROT) * DEG : -(ROT - (st.iDeg - 50)) * DEG;
    else sample.rotation.y = -ROT * DEG + (st.normal ? 0 : 0.5);
    var hit = arc(0, 0), inStart = arc(0.40, 180);
    beamIn.geometry.setFromPoints([inStart, hit]);
    beamsOut.forEach(function (l) { l.visible = false; });
    if (st.placed || MODE === 'angle') {
      fieldLines().forEach(function (L, i) {
        if (i >= beamsOut.length) return;
        var l = beamsOut[i];
        l.material.color.set(colourOf(L.nm));
        l.geometry.setFromPoints([hit, arc(0.40, L.T)]);
        l.visible = true;
      });
    }
    hudT.set(fmt(st.tel, 3) + '°');
    hudI.set(GRATING ? (st.normal ? 'normal to the beam' : 'not yet set') : fmt(st.iDeg, 1) + '° incidence');
    var w = onWire();
    hudS.set(st.focused ? (w ? w.label : 'nothing') : 'focus first');
    drawEye();
  }

  // ---------------------------------------------------------------- the human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function focusTube() {
    if (st.focused) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    S.say('Focus the telescope on a distant object, then on the slit: the cross-wire and the image come sharp together.');
    return S.hand.tap(tele.children[4]).then(function () {
      st.focused = true; update(); S.say('The telescope is focused for parallel light.'); S.render(); return true; });
  }
  function narrowSlit() {
    if (st.slit) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    return S.hand.tap(sKnob, 'top').then(function () {
      st.slit = true; slitGap.scale.y = 0.4; update(); S.say('The slit is narrow now: the image is a fine bright line.'); S.render(); return true; });
  }
  function swing(toDeg) {
    if (S.hand.busy) return wait();
    toDeg = Math.max(-130, Math.min(130, Math.round(toDeg / LC) * LC));
    var from = st.tel;
    if (Math.abs(toDeg - from) < 1e-6) { st.tel = toDeg; update(); return Promise.resolve(true); }
    function at(k) { return from + (toDeg - from) * k; }
    var ms = Math.min(2000, 420 + Math.abs(toDeg - from) * 12);
    return S.hand.pinchMove(arc(0.43, from), function (k) { return arc(0.43, at(k)); },
      function (k) { st.tel = at(k); update(); }, { ms: ms, reachMs: 650, hold: 150 }).then(function () {
      st.tel = toDeg; update(); S.render(); return true; });
  }
  function turnTable(toDeg) {
    if (S.hand.busy) return wait();
    toDeg = Math.max(30, Math.min(80, Math.round(toDeg * 10) / 10));
    var from = st.iDeg;
    if (Math.abs(toDeg - from) < 1e-6) return Promise.resolve(true);
    function at(k) { return from + (toDeg - from) * k; }
    return S.hand.pinchMove(new T.Vector3(CX + 0.05, 0.092, CZ + 0.05), function (k) {
      var a = (at(k) - 50) * DEG; return new T.Vector3(CX + 0.07 * Math.cos(a + 0.8), 0.092, CZ - 0.07 * Math.sin(a + 0.8)); },
      function (k) { st.iDeg = at(k); update(); }, { ms: 1200, reachMs: 600, hold: 150 }).then(function () {
      st.iDeg = toDeg; update(); S.render(); return true; });
  }
  function placeSample() {
    if (st.placed) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    var from = new T.Vector3(CX + 0.22, 0.14, CZ + 0.24), to = new T.Vector3(CX, 0.1, CZ);
    sample.visible = true; sample.position.set(0.22, 0.05, 0.24);
    return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); }, function (k) {
      sample.position.set(0.22 * (1 - k), 0.089 + 0.05 * (1 - k) * (1 - k), 0.24 * (1 - k)); update(); },
      { ms: 1400, reachMs: 700, hold: 250, mode: 'top' }).then(function () {
      sample.position.set(0, 0.089, 0); st.placed = true; update();
      S.say(GRATING ? 'The grating is on the table. Now set it square to the beam.'
        : (MODE === 'angle' ? 'The prism is on the table with its apex towards the collimator, so both polished faces are lit.'
          : 'The prism is on the table: the light goes in at one face and out of the other.'));
      S.render(); return true; });
  }
  function setNormal() {                                  // grating: telescope 90 degrees, reflect, turn the table 45
    if (st.normal) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    if (!st.placed) { S.say('Put the grating on the table first.'); return Promise.resolve(false); }
    return swing(90).then(function () { return S.hand.tap(clampK, 'top'); }).then(function () {
      st.step90 = true; return S.hand.pinchMove(new T.Vector3(CX + 0.05, 0.092, CZ + 0.05),
        function (k) { return new T.Vector3(CX + 0.07 * Math.cos(0.8 + k * 0.785), 0.092, CZ - 0.07 * Math.sin(0.8 + k * 0.785)); },
        function () {}, { ms: 1200, hold: 200 }); }).then(function () {
      st.normal = true; st.reflSet = true; update();
      S.say('The grating is normal to the beam: the telescope was set at 90 degrees, the table turned to throw the '
        + 'reflected image onto the cross-wire, then turned a further 45 degrees.');
      S.render(); return true; });
  }
  function readVernier() {                                 // the hand bends over the vernier window
    if (S.hand.busy) return wait();
    return S.hand.tap(vMag, 'top').then(function () { return true; });
  }

  // ---------------------------------------------------------------- recording
  function takeDirect() {
    if (!st.focused) { S.say('Focus the telescope first.'); return Promise.resolve(false); }
    return swing(0).then(function () { return readVernier(); }).then(function () {
      st.direct = roundLC(st.tel); S.say('Direct reading noted: ' + fmt(st.direct, 3) + '°. Every angle is measured from here.');
      S.render(); return true; });
  }
  function recordPair() {                                  // the prism-angle experiment: the two reflected images
    var w = onWire();
    if (!w) { S.say('No image is on the cross-wire. Swing the telescope until a reflected image sits on it.'); return false; }
    var r = roundLC(st.tel);
    if (st.hold.length && Math.abs(st.hold[0] - r) < 1) { S.say('That is the same image again. Swing round to the other reflected image.'); return false; }
    st.hold.push(r);
    if (st.hold.length < 2) { S.say('First reflected image at ' + fmt(r, 3) + '°. Now find the other one.'); S.render(); return true; }
    var first = st.hold[0], sep = Math.abs(first - r);
    if (sep > 180) sep = 360 - sep;
    st.hold = [];
    S.addRow({ t1: first, t2: r, sep: sep, A: sep / 2 });
    S.say('Pair recorded: the two images are ' + fmt(sep, 3) + '° apart, so A = ' + fmt(sep / 2, 3) + '°.');
    return true;
  }
  function recordMinDev() {
    if (!st.placed) { S.say('Put the prism on the table first.'); return false; }
    if (st.direct === null) { S.say('Take the direct reading first.'); return false; }
    var nm = lamNm(), md = minDev(nm), w = onWire();
    if (!w || Math.abs(w.nm - nm) > 0.5) { S.say('Bring the ' + fmt(nm, 1) + ' nm line onto the cross-wire first.'); return false; }
    if (Math.abs(st.iDeg - md.i) > 0.6) { S.say('The image is still walking. Turn the table in small steps until it stops and turns back.'); return false; }
    var dm = roundLC(Math.abs(st.tel - st.direct));
    if (MODE === 'disp' && S.rows.some(function (r) { return Math.abs(r.lam - nm) < 0.5; })) { S.say('This line is already in the table. Take the next line.'); return false; }
    S.addRow({ lam: nm, i: st.iDeg, dm: dm, n: Math.sin((AD + dm) * DEG / 2) / Math.sin(AD * DEG / 2) });
    S.say('Minimum deviation for ' + fmt(nm, 1) + ' nm is ' + fmt(dm, 3) + '°.');
    return true;
  }
  function recordOrder() {
    var w = onWire();
    if (!st.normal) { S.say('Set the grating normal to the beam first.'); return false; }
    if (!w || Math.abs(st.tel) < 0.5) { S.say('Bring one of the diffracted orders onto the cross-wire, not the direct image.'); return false; }
    var m = /order (\d)/.exec(w.label);
    if (!m) { S.say('That is the direct image. Swing out to the first or second order.'); return false; }
    var mm = +m[1], th = roundLC(Math.abs(st.tel));
    if (S.rows.some(function (r) { return r.m === mm; })) { S.say('Order ' + mm + ' is already recorded. Try the next order.'); return false; }
    S.addRow({ m: mm, theta: th, lam: p.d * Math.sin(th * DEG) / mm * 1e9 });
    S.say('Order ' + mm + ' sits at ' + fmt(th, 3) + '° from the direct image.');
    return true;
  }
  function recordWidth() {
    if (!st.normal) { S.say('Set the grating normal to the beam first.'); return false; }
    var g = gratingRP(st.Nset);
    if (S.rows.some(function (r) { return r.N === st.Nset; })) { S.say('That width of beam is already recorded. Open or close the stop.'); return false; }
    S.addRow({ N: st.Nset, half: g.disp * g.dlam * 1e-9 * 1e3, dlam: g.dlam, rp: g.rp, disp: g.disp });
    S.say('With ' + st.Nset + ' rulings lit, two lines ' + fmt(g.dlam, 4) + ' nm apart are just separated.');
    return true;
  }

  // ---------------------------------------------------------------- result and book, per set-up
  function meanOf(xs) { return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : NaN; }
  function resultFor(rows) {
    var i;
    if (MODE === 'angle') {
      if (!rows.length) return null;
      return { label: 'A', value: meanOf(rows.map(function (r) { return r.A; })), unit: '°', digits: 3, truth: AD,
        note: 'Half the angle between the two reflected images, averaged over your pairs.' };
    }
    if (MODE === 'index') {
      if (!rows.length) return null;
      return { label: 'n', value: meanOf(rows.map(function (r) { return r.n; })), unit: '', digits: 4, truth: nOf(lamNm()),
        note: 'n = sin((A + Dm)/2) / sin(A/2) with A = ' + fmt(AD, 2) + '° at ' + fmt(lamNm(), 1) + ' nm.' };
    }
    if (MODE === 'disp') {
      var byLam = {};
      rows.forEach(function (r) { byLam[Math.round(r.lam * 10)] = r.n; });
      var nV = byLam[Math.round(435.833 * 10)], nG = byLam[Math.round(546.074 * 10)], nY = byLam[Math.round(579.066 * 10)];
      if (!(nV && nG && nY)) return null;
      var w = (nV - nY) / (nG - 1), tV = nOf(435.833), tG = nOf(546.074), tY = nOf(579.066);
      // Cauchy from the measured points, for the note
      var pts = rows.map(function (r) { return [1 / (r.lam * r.lam * 1e-18), r.n]; }), L = S.fit.linear(pts);
      return { label: 'dispersive power w', value: w, unit: '', digits: 4, truth: (tV - tY) / (tG - 1),
        note: 'w = (n(435.8) - n(579.1)) / (n(546.1) - 1)' + (L ? '; Cauchy fit A = ' + fmt(L.c, 4) + ', B = '
          + fmt(L.m * 1e15, 3) + ' x 10⁻¹⁵ m²' : '') };
    }
    if (MODE === 'glam') {
      if (!rows.length) return null;
      return { label: 'wavelength', value: meanOf(rows.map(function (r) { return r.lam; })), unit: 'nm', digits: 2,
        truth: p.lam * 1e9, note: 'From d sin(theta) = m x wavelength with d = ' + fmt(p.d * 1e9, 1) + ' nm.' };
    }
    var best = null;
    for (i = 0; i < rows.length; i++) if (!best || rows[i].N > best.N) best = rows[i];
    if (!best) return null;
    return { label: 'resolving power', value: best.rp, unit: '', digits: 0, truth: p.m * Math.floor(best.N + 0.5),
      note: 'At ' + best.N + ' rulings lit, measured from the angular width of the line; the textbook value is m x N. '
        + 'Dispersive power here is ' + fmt(best.disp * 1e-9 * 1e3, 3) + ' mrad per nm.' };
  }
  var COLS = MODE === 'angle' ? [
    { label: 'No.', get: function (r, i) { return i + 1; } },
    { label: 'Image 1 (°)', get: function (r) { return fmt(r.t1, 3); } },
    { label: 'Image 2 (°)', get: function (r) { return fmt(r.t2, 3); } },
    { label: '2A (°)', get: function (r) { return fmt(r.sep, 3); } },
    { label: 'A (°)', get: function (r) { return fmt(r.A, 3); } }] : (MODE === 'index' || MODE === 'disp') ? [
    { label: 'Line (nm)', get: function (r) { return fmt(r.lam, 1); } },
    { label: 'Incidence (°)', get: function (r) { return fmt(r.i, 1); } },
    { label: 'Dm (°)', get: function (r) { return fmt(r.dm, 3); } },
    { label: 'n', get: function (r) { return fmt(r.n, 4); } }] : MODE === 'glam' ? [
    { label: 'Order m', get: function (r) { return r.m; } },
    { label: 'Angle (°)', get: function (r) { return fmt(r.theta, 3); } },
    { label: 'Wavelength (nm)', get: function (r) { return fmt(r.lam, 2); } }] : [
    { label: 'Rulings lit', get: function (r) { return r.N; } },
    { label: 'Half width (mrad)', get: function (r) { return fmt(r.half, 4); } },
    { label: 'Least Δλ (nm)', get: function (r) { return fmt(r.dlam, 4); } },
    { label: 'λ / Δλ', get: function (r) { return Math.round(r.rp); } }];

  var VIEWS = {
    circle: [[CX + 0.3, 0.64, CZ + 0.95], [CX - 0.01, 0.08, CZ]],
    coll: [[CX - 0.2, 0.32, CZ + 0.5], [CX - 0.3, AXY, CZ + 0.12]],
    tele: [[CX + 0.5, 0.36, CZ + 0.42], [CX + 0.2, AXY, CZ - 0.12]],
    table: [[CX + 0.12, 0.26, CZ + 0.3], [CX, 0.095, CZ]],
    lamp: [[CX - 0.24, 0.28, CZ + 0.62], [CX - 0.42, 0.08, CZ + 0.25]],
    wide: [[CX + 0.16, 0.82, CZ + 1.28], [CX - 0.05, 0.07, CZ - 0.02]],
    book: [[0.78, 0.46, 0.68], [0.76, 0.0, 0.16]]
  };
  update();

  // ---------------------------------------------------------------- steps
  function adjustStep() {
    return { id: 'adjust', title: 'Set up', view: 'wide', render: function (u) {
      u.h2('Set the spectrometer and take the direct reading');
      u.p('The collimator sends parallel light from the ' + (LAMP === 'mercury' ? 'mercury' : 'sodium') + ' lamp through a '
        + 'narrow slit. Focus the telescope for parallel light, narrow the slit and note where the telescope reads when it '
        + 'looks straight down the collimator.');
      u.task('1. Focus the telescope', st.focused, st.focused ? 'Sharp, and set for parallel light' : 'Focus on a distant object, then on the slit')
        .add(u.button(st.focused ? 'Focused' : 'Focus the telescope', function () { focusTube(); }, !st.focused, st.focused || S.hand.busy));
      u.task('2. Narrow the slit', st.slit, st.slit ? 'A fine bright line' : 'Close the slit screw until the line is thin')
        .add(u.button(st.slit ? 'Slit narrowed' : 'Narrow the slit', function () { narrowSlit(); }, !st.slit, st.slit || S.hand.busy));
      u.task('3. Direct reading', st.direct !== null, st.direct !== null ? 'Direct position ' + fmt(st.direct, 3) + '°' : 'Bring the slit image on the cross-wire and read both verniers')
        .add(u.button(st.direct !== null ? 'Read' : 'Read the direct position', function () { takeDirect(); }, st.direct === null, S.hand.busy));
      u.live(function () { return 'Telescope at ' + fmt(st.tel, 3) + '° · on the cross-wire: ' + (onWire() ? onWire().label : 'nothing'); });
      u.note('The circle is divided to half a degree and read through two verniers, so one minute of arc is the least '
        + 'count. Read BOTH verniers for every setting and take the mean: that cancels any error of the centring.');
      u.next('Next: place the ' + (GRATING ? 'grating' : 'prism'), st.focused && st.slit && st.direct !== null);
    },
    ok: function () { return st.focused && st.slit && st.direct !== null; },
    auto: function () { return focusTube().then(narrowSlit).then(takeDirect); } };
  }
  function placeStep() {
    return { id: 'place', title: GRATING ? 'Set the grating' : 'Place the prism', view: 'table', render: function (u) {
      u.h2(GRATING ? 'Put the grating on and set it normal to the beam' : 'Level the table and place the prism');
      if (GRATING) {
        u.p('Clamp the grating in its holder on the table. Then set it exactly square to the beam: turn the telescope to '
          + 'read 90 degrees from the direct position and clamp it, turn the table until the image reflected off the '
          + 'grating sits on the cross-wire, then turn the table a further 45 degrees.');
        u.task('1. Clamp the grating', st.placed, st.placed ? 'In its holder on the table' : 'Hold it by the frame only')
          .add(u.button(st.placed ? 'On the table' : 'Put the grating on', function () { placeSample(); }, !st.placed, st.placed || S.hand.busy));
        u.task('2. Normal incidence', st.normal, st.normal ? 'The grating is square to the beam' : '90 degrees, reflect, then 45 degrees')
          .add(u.button(st.normal ? 'Set' : 'Set normal incidence', function () { setNormal(); }, !st.normal, st.normal || !st.placed || S.hand.busy));
        u.note('Never touch the ruled face of a grating: the rulings are a micron apart and a fingerprint ruins it.');
        u.next('Next: measure the orders', st.placed && st.normal);
      } else {
        u.p('Level the table with its three screws so that the faces of the prism stand vertical, then set the prism on '
          + 'it' + (MODE === 'angle' ? ' with its refracting edge towards the collimator, so that light falls on both '
            + 'polished faces at once.' : ' so that light goes in at one polished face and comes out of the other.'));
        u.task('Place the prism', st.placed, st.placed ? 'On the levelled table' : 'Hold it by the ground faces only')
          .add(u.button(st.placed ? 'On the table' : 'Place the prism', function () { placeSample(); }, !st.placed, st.placed || S.hand.busy));
        u.live(function () { var ls = fieldLines(); return 'Images to find: ' + ls.map(function (L) { return fmt(L.T, 2) + '°'; }).join(', '); });
        u.note('Hold the prism by its top and bottom ground faces. A fingerprint on a polished face scatters the light '
          + 'and the image goes dim.');
        u.next('Next: measure', st.placed);
      }
    },
    ok: function () { return st.placed && (!GRATING || st.normal); },
    auto: function () { return placeSample().then(function () { return GRATING ? setNormal() : true; }); } };
  }
  function swingRow(u) {
    u.slider('Swing the telescope to', -130, 130, LC, function () { return st.telSet; }, function (x) { st.telSet = x; }, '°', 3);
    u.row(u.button('Swing the telescope', function () { swing(st.telSet); S.render(); }, true, S.hand.busy),
      u.button('Read the vernier', function () { readVernier(); }, false, S.hand.busy));
    function nudge(d) { return function () { st.telSet = st.tel + d; swing(st.tel + d); S.render(); }; }
    u.row(u.button('− 1°', nudge(-1), false, S.hand.busy), u.button('− 1′', nudge(-LC), false, S.hand.busy),
      u.button('+ 1′', nudge(LC), false, S.hand.busy), u.button('+ 1°', nudge(1), false, S.hand.busy));
  }
  function findLine(T) { st.telSet = T; return swing(T); }

  var measureStep;
  if (MODE === 'angle') {
    measureStep = { id: 'measure', title: 'Measure 2A', view: 'circle', render: function (u) {
      u.h2('Find both reflected images and read the circle');
      u.p('Light falls on both polished faces at once, so there is a reflected image on each side. Set the cross-wire on '
        + 'one, read both verniers, then swing round to the other and read again. The angle between the two settings is 2A.');
      swingRow(u);
      u.live(function () { return 'On the cross-wire: ' + (onWire() ? onWire().label : 'nothing') + (st.hold.length ? ' · first image held at ' + fmt(st.hold[0], 3) + '°' : ''); });
      u.row(u.button('Set the cross-wire and record', function () { if (recordPair()) S.render(); else S.render(); }, true, S.hand.busy),
        u.button('Find an image', function () { findLine(st.hold.length ? -reflAt() : reflAt()).then(function () { S.render(); }); }, false, S.hand.busy));
      u.h3('Observation table'); u.table();
      u.next('Next: result', S.rows.length >= 3);
      if (S.rows.length < 3) u.p(S.rows.length + ' of 3 pairs recorded.');
    },
    ok: function () { return S.rows.length >= 3; },
    auto: function () {
      var seq = Promise.resolve(), k;
      for (k = 0; k < 3; k++) {
        seq = seq.then(function () { return findLine(reflAt()); }).then(function () { return readVernier(); })
          .then(function () { recordPair(); return findLine(-reflAt()); }).then(function () { return readVernier(); })
          .then(function () { recordPair(); });
      }
      return seq;
    } };
  } else if (MODE === 'index' || MODE === 'disp') {
    measureStep = { id: 'measure', title: 'Minimum deviation', view: 'circle', render: function (u) {
      u.h2('Turn the table to minimum deviation and read the circle');
      u.p('Follow the image with the telescope while you turn the table. The image walks one way, stops, and turns back: '
        + 'at that turning point the deviation is least. Set the cross-wire on it there and read both verniers.');
      if (MODE === 'disp') {
        u.task('Line on the cross-wire', true, fmt(lamNm(), 1) + ' nm');
        u.row.apply(u, LINES.map(function (nm, i) {
          return u.button(fmt(nm, 1) + ' nm', function () { st.lamIdx = i; update(); S.render(); }, i === st.lamIdx, S.hand.busy);
        }));
      }
      u.slider('Turn the prism table to', 30, 80, 0.1, function () { return st.iSet; }, function (x) { st.iSet = x; }, '° incidence', 1);
      u.row(u.button('Turn the table', function () { turnTable(st.iSet); S.render(); }, true, S.hand.busy),
        u.button('Follow it to the turning point', function () {
          var md = minDev(lamNm()); st.iSet = Math.round(md.i * 10) / 10;
          turnTable(st.iSet).then(function () { return findLine(st.direct + md.dm); }).then(function () { S.render(); });
        }, false, S.hand.busy));
      swingRow(u);
      u.live(function () { var d = devOf(lamNm(), st.iDeg); return 'Deviation of this line now: ' + (d === null ? 'the light cannot get out (total internal reflection)' : fmt(d, 3) + '°'); });
      u.row(u.button('Record the minimum deviation', function () { recordMinDev(); S.render(); }, true, S.hand.busy));
      u.h3('Observation table'); u.table();
      var need = MODE === 'disp' ? 3 : 3;
      u.next('Next: result', S.rows.length >= need);
      if (S.rows.length < need) u.p(S.rows.length + ' of ' + need + ' readings recorded.');
    },
    ok: function () { return S.rows.length >= 3; },
    auto: function () {
      var want = MODE === 'disp' ? [1, 2, 4] : [0, 0, 0], seq = Promise.resolve();
      want.forEach(function (idx, j) {
        seq = seq.then(function () {
          st.lamIdx = MODE === 'disp' ? idx : 0;
          var md = minDev(lamNm());
          st.iSet = Math.round(md.i * 10) / 10;
          return turnTable(st.iSet).then(function () { return findLine(st.direct + md.dm); })
            .then(function () { return readVernier(); })
            .then(function () { recordMinDev(); });
        });
      });
      return seq;
    } };
  } else if (MODE === 'glam') {
    measureStep = { id: 'measure', title: 'Measure the orders', view: 'circle', render: function (u) {
      u.h2('Set the cross-wire on each order and read the circle');
      u.p('Swing the telescope out to the first order on one side and read both verniers, then to the first order on the '
        + 'other side. Half the angle between the two settings is the angle of diffraction of that order. Then do the '
        + 'second order.');
      swingRow(u);
      u.live(function () { return 'On the cross-wire: ' + (onWire() ? onWire().label : 'nothing'); });
      u.row(u.button('Record this order', function () { recordOrder(); S.render(); }, true, S.hand.busy),
        u.button('Find order 1', function () { var t = orderTheta(1); if (t !== null) findLine(t).then(function () { S.render(); }); }, false, S.hand.busy),
        u.button('Find order 2', function () { var t = orderTheta(2); if (t !== null) findLine(t).then(function () { S.render(); }); else S.say('The second order falls beyond 90 degrees for this grating: it does not exist.'); }, false, S.hand.busy));
      u.h3('Observation table'); u.table();
      u.next('Next: result', S.rows.length >= 2);
      if (S.rows.length < 2) u.p(S.rows.length + ' of 2 orders recorded.');
    },
    ok: function () { return S.rows.length >= 2; },
    auto: function () {
      var seq = Promise.resolve();
      [1, 2].forEach(function (m) {
        seq = seq.then(function () {
          var t = orderTheta(m);
          if (t === null) return null;
          return findLine(t).then(function () { return readVernier(); }).then(function () { recordOrder(); });
        });
      });
      return seq;
    } };
  } else {
    measureStep = { id: 'measure', title: 'Resolving power', view: 'circle', render: function (u) {
      u.h2('Measure the width of the line, and the least wavelength difference');
      u.p('A principal maximum is not infinitely sharp: it has an angular width of its own, set by how many rulings the '
        + 'beam lights. Two wavelengths can just be told apart when one maximum falls on the first dark edge of the '
        + 'other. Narrow the stop to light fewer rulings and see the line get wider and the resolving power fall.');
      u.slider('Rulings lit by the beam', 500, 6000, 100, function () { return st.Nset; }, function (x) { st.Nset = x; }, 'rulings', 0);
      u.row(u.button('Measure at this width', function () { recordWidth(); S.render(); }, true, S.hand.busy));
      u.live(function () { var g = gratingRP(st.Nset);
        return 'Least resolvable difference now: ' + fmt(g.dlam, 4) + ' nm (λ/Δλ = ' + Math.round(g.rp) + ')'; });
      swingRow(u);
      u.h3('Observation table'); u.table();
      u.next('Next: result', S.rows.length >= 3);
      if (S.rows.length < 3) u.p(S.rows.length + ' of 3 widths recorded.');
    },
    ok: function () { return S.rows.length >= 3; },
    auto: function () {
      [2000, 4000, 5906].forEach(function (N) { st.Nset = N; recordWidth(); });
      return Promise.resolve();
    } };
  }

  var THEORY = {
    angle: { principle: 'Light from the collimator falls on both polished faces of the prism at once and each face '
      + 'reflects an image of the slit. Turning a mirror through an angle turns its reflected beam through twice that '
      + 'angle, so the angle between the two reflected images is exactly twice the refracting angle of the prism.',
      formula: 'A = (angle between the two reflected images) / 2',
      formulaNote: 'read on the divided circle, both verniers, least count 1 minute of arc',
      more: ['Schuster\'s method sets the instrument for parallel light with no distant object: focus the telescope on '
        + 'the far face of the prism just inside minimum deviation, then the collimator on the near face just outside '
        + 'it, and repeat until both come sharp together.'],
      precautions: 'Level the table so that both faces stand vertical. Read both verniers at every setting. Keep the '
        + 'slit narrow and the refracting edge exactly towards the collimator.' },
    index: { principle: 'A prism bends light twice. As the prism is turned, the deviation falls to a least value and '
      + 'rises again; at that minimum the ray passes symmetrically, so the angle inside each face is A/2 and the angles '
      + 'of incidence and emergence are both (A + Dm)/2. Snell\'s law at the first face then gives the index of the glass.',
      formula: 'n = sin((A + Dm) / 2) / sin(A / 2)',
      formulaNote: 'A = refracting angle of the prism, Dm = angle of minimum deviation',
      more: ['At this lab\'s wavelength the glass of this prism is what you are measuring; a denser glass gives a '
        + 'larger Dm. Below a certain angle of incidence the light cannot leave the second face at all and the image '
        + 'disappears: that is total internal reflection inside the prism.'],
      precautions: 'Find the turning point by moving the table both ways. Set the cross-wire on the middle of the line. '
        + 'Read both verniers and take the mean.' },
    disp: { principle: 'The index of glass falls as the wavelength rises, which is why a prism spreads light into a '
      + 'spectrum. Measuring the minimum deviation of each mercury line gives n for that line; the spread of n over the '
      + 'visible range, divided by the mean deviating power, is the dispersive power of the glass.',
      formula: 'w = (nV − nY) / (nG − 1),   n = A + B / λ²',
      formulaNote: 'Cauchy\'s two-term law: a graph of n against 1/λ² is a straight line of slope B',
      more: ['Dispersive power is a property of the glass alone: it does not depend on the angle of the prism. Flint '
        + 'glass has roughly twice the dispersive power of crown glass, which is why an achromatic doublet pairs one of '
        + 'each.'],
      precautions: 'Find the minimum deviation separately for each line: it is not the same setting of the table. The '
        + 'two yellow mercury lines at 577.0 and 579.1 nm are close together, so keep the slit narrow.' },
    glam: { principle: 'A grating is a very large number of equally spaced slits. The waves from all of them add up '
      + 'only in the directions where neighbouring rulings differ by a whole number of wavelengths, and because '
      + 'thousands of rulings take part those directions are extremely sharp.',
      formula: 'd sin(θ) = m λ', formulaNote: 'd = grating spacing, m = order, θ = angle of diffraction',
      more: ['The grating must be set at normal incidence for this simple form to hold. Only the orders with '
        + 'm λ < d exist, so a fine grating shows fewer orders.'],
      precautions: 'Set normal incidence carefully: the telescope at 90 degrees, the reflected image on the cross-wire, '
        + 'then the table a further 45 degrees. Measure each order on both sides and halve the angle between them.' },
    grp: { principle: 'Two things matter about a grating. Its dispersive power says how far apart it throws two '
      + 'wavelengths. Its resolving power says whether they can be told apart at all: each principal maximum has an '
      + 'angular width of its own, and by Rayleigh\'s criterion two lines are just separated when the maximum of one '
      + 'falls on the first dark edge of the other.',
      formula: 'λ / Δλ = m N,   dθ/dλ = m / (d cos θ)',
      formulaNote: 'N = the number of rulings the beam actually lights, not the number ruled on the plate',
      more: ['This is why a narrow beam on a fine grating resolves worse than a wide one, and why a grating is used in '
        + 'a higher order when the lines are very close. Resolving the two sodium D lines, 0.6 nm apart at 589 nm, '
        + 'needs about a thousand rulings.'],
      precautions: 'Keep the stop square to the beam and do not press it against the grating. Measure the width of the '
        + 'line with the slit as narrow as it will go.' }
  }[MODE];

  return {
    camera: { pos: [CX + 0.16, 0.82, CZ + 1.28], look: [CX - 0.05, 0.07, CZ - 0.02] },
    views: VIEWS,
    theory: THEORY,
    book: { title: 'Expt. — ' + (MODE === 'angle' ? 'Angle of a prism' : MODE === 'index' ? 'Prism: minimum deviation'
      : MODE === 'disp' ? 'Dispersive power of a prism' : MODE === 'glam' ? 'Grating: wavelength' : 'Grating: resolving power'),
      lines: ['Least count of the circle: 1 minute of arc.',
        GRATING ? 'Grating spacing d = ' + fmt(p.d * 1e9, 1) + ' nm.' : 'Refracting angle A = ' + fmt(AD, 2) + '°.',
        MODE === 'angle' ? 'A = (angle between the reflected images) / 2' : MODE === 'glam'
          ? 'd sin(theta) = m x wavelength' : MODE === 'grp' ? 'Resolving power = wavelength / least difference'
            : 'n = sin((A + Dm)/2) / sin(A/2)',
        'Read both verniers every time.'],
      columns: COLS, at: [0.76, 0.1, 0.1] },
    graph: MODE === 'disp' ? { x: function (r) { return 1 / (r.lam * r.lam * 1e-6); }, y: function (r) { return r.n; },
      xlabel: '1 / λ²  (µm⁻²)', ylabel: 'n', line: function (pts) { var L = S.fit.linear(pts); return L ? function (x) { return L.m * x + L.c; } : null; } }
      : MODE === 'glam' ? { x: function (r) { return r.m; }, y: function (r) { return Math.sin(r.theta * DEG); },
        xlabel: 'order m', ylabel: 'sin θ', x0: 0, y0: 0,
        line: function (pts) { var k = S.fit.origin(pts); return isFinite(k) ? function (x) { return k * x; } : null; } }
        : MODE === 'grp' ? { x: function (r) { return r.N; }, y: function (r) { return r.rp; },
          xlabel: 'rulings lit N', ylabel: 'λ / Δλ', x0: 0, y0: 0,
          line: function (pts) { var k = S.fit.origin(pts); return isFinite(k) ? function (x) { return k * x; } : null; } }
          : null,
    result: resultFor,
    tol: MODE === 'disp' ? 0.03 : 0.01,
    chips: ['Why read both verniers?', 'How do I know the deviation is least?', 'What is the least count here?',
      'Check my readings', GRATING ? 'Why set normal incidence?' : 'Why hold the prism by its ground faces?'],
    viva: [['The divided circle is read through two verniers 180 degrees apart because',
      ['it cancels any error in the centring of the circle', 'it is brighter', 'the scale is too short'], 0,
      'A circle whose centre is slightly off gives equal and opposite errors at the two verniers, so the mean is right.'],
      [GRATING ? 'Doubling the order while lighting the same rulings' : 'At minimum deviation the ray inside the prism is',
        GRATING ? ['doubles the resolving power', 'halves it', 'leaves it unchanged']
          : ['parallel to the base', 'parallel to the first face', 'along the base'], 0,
        GRATING ? 'Resolving power is m x N.' : 'The passage is symmetric, so the ray runs parallel to the base.']],
    askState: function () {
      var w = onWire();
      return { set_up: MODE, lamp: LAMP, telescope_reads_deg: +st.tel.toFixed(3),
        direct_reading_deg: st.direct === null ? null : +st.direct.toFixed(3),
        on_the_cross_wire: w ? w.label : 'nothing', telescope_focused: st.focused, slit_narrow: st.slit,
        sample_on_the_table: st.placed, normal_incidence: GRATING ? st.normal : null,
        prism_table_incidence_deg: GRATING ? null : +st.iDeg.toFixed(1),
        line_on_the_cross_wire_nm: +lamNm().toFixed(1), rulings_lit: MODE === 'grp' ? st.Nset : null,
        readings_taken: S.rows.length, least_count_deg: +LC.toFixed(5) };
    },
    steps: [adjustStep(), placeStep(), measureStep],
    tick: function () { update(); }
  };
});
