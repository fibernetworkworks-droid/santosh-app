/* Prayogshala studio module: Glass slab, real and apparent depth with a travelling microscope (NCERT Class XII).
   The hand turns the rack-and-pinion knob to focus on an ink mark (R1), on the same mark seen through a glass slab (R2) and on
   lycopodium powder sprinkled on top of the slab (R3). The mark's apparent rise comes from the slab kernel's exact trace
   ('app'); the glass's n is the lab's unknown. n = (R3 − R1) / (R3 − R2). */
HoolaStudio.define('glass-slab-apparent-depth', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.slab;
  var p = window.HoolaKernels.paramsFor('slab', S.lab.params);
  (S.lab.knobs || []).forEach(function (k) { if (k.param === 'n' && isFinite(k.value)) p.n = +k.value; });   // the glass under test
  var MX = 0.2, MZ = -0.32, BASE_TOP = 0.034, PAPER_Y = BASE_TOP + 0.0004, WD = 0.06, OBJ_Z = MZ + 0.05;
  var Y_ZERO = PAPER_Y + WD + 0.06 - 0.05;                       // the main scale's zero: reading R (cm) = 100 (F + 0.05)
  var SLABS = [{ id: 'A', t: 0.02 }, { id: 'B', t: 0.03 }, { id: 'C', t: 0.04 }, { id: 'D', t: 0.05 }];
  var SW = 0.07, SDp = 0.05;
  var SAMPLE = ((S.lab.variant || {}).sample || '');
  var MAT = /dense flint|sf10/i.test(SAMPLE) ? ['Dense flint glass', 0xd9d6a6, 'DENSE FLINT'] : /flint/i.test(SAMPLE) ? ['Flint glass', 0xe0dcae, 'FLINT GLASS'] :
    /acrylic|pmma|perspex/i.test(SAMPLE) ? ['Acrylic (PMMA)', 0xb9dcef, 'ACRYLIC'] : /polycarbonate/i.test(SAMPLE) ? ['Polycarbonate', 0xc6d7ea, 'POLYCARBONATE'] :
    /quartz|silica/i.test(SAMPLE) ? ['Fused quartz', 0xe6f2f4, 'FUSED QUARTZ'] : /crown|bk7/i.test(SAMPLE) ? ['Crown glass', 0x9fdcc6, 'CROWN GLASS'] : ['Glass', 0x9fdcc6, ''];
  var GLASSY = /glass|quartz/i.test(MAT[0]);                                     // slab length (x) and width (z)
  var st = { eyeFocused: false, F: 0.012, slab: null, onMark: null, powder: false, R1: null, R2: null, R3: null, pick: 'A' };

  // ---------- the travelling microscope
  var micro = new T.Group(); S.scene.add(micro);
  var base = S.rounded(0.27, 0.2, 0.03, 0.012, M.iron); base.rotation.x = -Math.PI / 2; base.position.set(MX, 0.019, MZ); micro.add(base);
  [[-0.115, -0.08], [0.115, -0.08], [0.1, 0.085]].forEach(function (f) { var s = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.004, 18), M.brass); s.position.set(MX + f[0], 0.002, MZ + f[1]); micro.add(s);
    var kn = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.006, 20), M.bakelite); kn.position.set(MX + f[0], BASE_TOP + 0.003, MZ + f[1]); micro.add(kn); });
  var bubble = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.004, 20), M.glass); bubble.position.set(MX + 0.07, BASE_TOP + 0.002, MZ - 0.07); micro.add(bubble);
  S.contact(0.36, 0.28, MX, MZ, 0.55);
  var PIL_X = MX - 0.075, PIL_Z = OBJ_Z, PIL_W = 0.03, PIL_H = 0.33, FACE = PIL_Z + PIL_W / 2;
  var pillar = S.mesh(new T.BoxGeometry(PIL_W, PIL_H, PIL_W), M.steel); pillar.position.set(PIL_X, BASE_TOP + PIL_H / 2, PIL_Z); micro.add(pillar);
  var cap = S.mesh(new T.BoxGeometry(PIL_W + 0.006, 0.008, PIL_W + 0.006), M.iron); cap.position.set(PIL_X, BASE_TOP + PIL_H + 0.004, PIL_Z); micro.add(cap);
  var foot = S.rounded(0.05, 0.05, 0.012, 0.004, M.iron); foot.rotation.x = -Math.PI / 2; foot.position.set(PIL_X, BASE_TOP + 0.006, PIL_Z); micro.add(foot);
  // main scale on the pillar's front face (right half): 0.5 mm divisions, numbered every cm; ticks meet the vernier on their left
  var SC_LEN = 0.2, scTex = S.canvasTex(160, 4096, function (x, w, h) { x.fillStyle = '#e9ebe6'; x.fillRect(0, 0, w, h); x.fillStyle = '#121212';
    var k = h / (SC_LEN * 2000 + 10); x.font = '600 30px "Public Sans", sans-serif'; x.textAlign = 'right';
    for (var i = 0; i <= SC_LEN * 2000; i++) { var y = h - (5 + i) * k, len = i % 20 === 0 ? 74 : i % 10 === 0 ? 56 : i % 2 === 0 ? 40 : 26; x.fillRect(0, y - 1.2, len, 2.4);
      if (i % 20 === 0) x.fillText(String(i / 20), w - 6, y + 11); } });
  var scale = new T.Mesh(new T.PlaneGeometry(0.0142, SC_LEN * (1 + 10 / (SC_LEN * 2000))), new T.MeshStandardMaterial({ map: scTex, roughness: 0.5, metalness: 0.15 }));
  scale.position.set(PIL_X + 0.0076, Y_ZERO + SC_LEN / 2, FACE + 0.0004); micro.add(scale);
  var scLab = S.label('cm · MSD 0.5 mm', { w: 0.026, ratio: 0.22, color: '#20242a' }); scLab.position.set(PIL_X, Y_ZERO - 0.012, FACE + 0.0004); micro.add(scLab);

  // carriage (wraps the pillar's back and sides), vernier on the left half of the front face, arm to the tube, knob on the left
  var car = new T.Group(); micro.add(car);
  var body = S.mesh(new T.BoxGeometry(0.05, 0.06, 0.036), M.iron); body.position.set(PIL_X, 0, PIL_Z - 0.003); car.add(body);
  var vTex = S.canvasTex(128, 1024, function (x, w, h) { x.fillStyle = '#e4e6e1'; x.fillRect(0, 0, w, h); x.fillStyle = '#111'; x.font = '600 26px "Public Sans", sans-serif';
    var k = h / 34, y0 = h - 4.5 * k;                       // 50 vernier divisions over 24.5 mm; its zero is the index
    for (var i = 0; i <= 50; i++) { var y = y0 - i * 0.49 * k, len = i % 10 === 0 ? 70 : i % 5 === 0 ? 50 : 34; x.fillRect(w - len, y - 1, len, 2); if (i % 10 === 0) x.fillText(String(i), 4, y + 9); } });
  var vPlate = S.mesh(new T.BoxGeometry(0.0152, 0.04, 0.002), M.alu); vPlate.position.set(PIL_X - 0.0076, 0.034 / 2 - 0.0045, FACE + 0.0012); car.add(vPlate);
  var vern = new T.Mesh(new T.PlaneGeometry(0.0145, 0.034), new T.MeshStandardMaterial({ map: vTex, roughness: 0.45, metalness: 0.15 }));
  vern.position.set(PIL_X - 0.0076, 0.034 / 2 - 0.0045, FACE + 0.0023); car.add(vern);
  var ARM0 = PIL_X + 0.025, ARM1 = MX - 0.012;
  var arm = S.mesh(new T.BoxGeometry(ARM1 - ARM0 + 0.004, 0.018, 0.022), M.iron); arm.position.set((ARM0 + ARM1) / 2, 0, PIL_Z); car.add(arm);
  var clampR = S.mesh(new T.CylinderGeometry(0.017, 0.017, 0.024, 28), M.iron); clampR.position.set(MX, 0, OBJ_Z); car.add(clampR);
  var tubeM = new T.MeshStandardMaterial({ color: 0x1e2126, roughness: 0.35, metalness: 0.4 });
  var tube = S.mesh(new T.CylinderGeometry(0.0115, 0.0115, 0.15, 32), tubeM); tube.position.set(MX, 0.015, OBJ_Z); car.add(tube);   // y −0.06 … +0.09 from the index
  var objL = S.mesh(new T.CylinderGeometry(0.0075, 0.0095, 0.018, 24), M.brass); objL.position.set(MX, -0.06 + 0.009, OBJ_Z); car.add(objL);
  var lensF = S.mesh(new T.CircleGeometry(0.006, 24), new T.MeshStandardMaterial({ color: 0x223344, roughness: 0.05, metalness: 0.6 })); lensF.rotation.x = Math.PI / 2; lensF.position.set(MX, -0.0601, OBJ_Z); car.add(lensF);
  var eyeG = new T.Group(); eyeG.position.set(MX, 0.09 + 0.013, OBJ_Z); car.add(eyeG);
  var eyeP = S.mesh(new T.CylinderGeometry(0.0105, 0.0105, 0.026, 28), M.black); eyeG.add(eyeP);
  for (var r = 0; r < 18; r++) { var rib = S.mesh(new T.BoxGeometry(0.0016, 0.024, 0.0012), M.bakelite); var a = r / 18 * Math.PI * 2; rib.position.set(Math.cos(a) * 0.0108, 0, Math.sin(a) * 0.0108); rib.rotation.y = -a; eyeG.add(rib); }
  var eyeLens = S.mesh(new T.CircleGeometry(0.007, 24), new T.MeshStandardMaterial({ color: 0x2b3d55, roughness: 0.05, metalness: 0.7 })); eyeLens.rotation.x = -Math.PI / 2; eyeLens.position.y = 0.0131; eyeG.add(eyeLens);
  var knob = new T.Group(); knob.position.set(PIL_X - 0.042, -0.004, PIL_Z); car.add(knob);
  var kShaft = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.02, 12), M.steel); kShaft.rotation.z = Math.PI / 2; kShaft.position.x = 0.012; knob.add(kShaft);
  var kWheel = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.012, 32), M.bakelite); kWheel.rotation.z = Math.PI / 2; knob.add(kWheel);
  for (r = 0; r < 24; r++) { var kr = S.mesh(new T.BoxGeometry(0.012, 0.002, 0.0015), M.black); var b = r / 24 * Math.PI * 2; kr.position.set(0, Math.cos(b) * 0.0162, Math.sin(b) * 0.0162); kr.rotation.x = b; knob.add(kr); }
  var kDot = S.mesh(new T.CircleGeometry(0.003, 16), M.red); kDot.rotation.y = -Math.PI / 2; kDot.position.set(-0.0062, 0.009, 0); knob.add(kDot);
  var lockS = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.014, 12), M.bakelite); lockS.rotation.x = Math.PI / 2; lockS.position.set(PIL_X, 0.012, PIL_Z - 0.028); car.add(lockS);
  function idxY() { return PAPER_Y + st.F + WD + 0.06; }
  function setCar() { car.position.y = idxY(); }
  function reading() { return Math.round((st.F + 0.05) * 100 * 1000) / 1000; }     // to the least count 0.001 cm
  function split(R) { var msr = Math.floor(R / 0.05 + 1e-9) * 0.05, vsr = Math.round((R - msr) / 0.001); if (vsr >= 50) { msr += 0.05; vsr = 0; } return { msr: msr, vsr: vsr }; }

  // ---------- paper with an ink mark under the objective
  var markTex = S.canvasTex(512, 384, function (x, w, h) { x.fillStyle = '#f6f4ec'; x.fillRect(0, 0, w, h); x.strokeStyle = '#1b2a6b'; x.lineWidth = 5; x.lineCap = 'round';
    x.beginPath(); x.moveTo(w / 2 - 22, h / 2); x.lineTo(w / 2 + 22, h / 2); x.moveTo(w / 2, h / 2 - 22); x.lineTo(w / 2, h / 2 + 22); x.stroke(); });
  var paper = new T.Mesh(new T.PlaneGeometry(0.1, 0.08), new T.MeshStandardMaterial({ map: markTex, roughness: 0.9 }));
  paper.rotation.x = -Math.PI / 2; paper.position.set(MX, PAPER_Y, OBJ_Z); paper.receiveShadow = true; S.scene.add(paper);

  // ---------- glass slabs on a cloth, and the lycopodium sprinkler
  var cloth = S.mesh(new T.BoxGeometry(0.4, 0.002, 0.11), new T.MeshStandardMaterial({ color: 0x2f5d87, roughness: 1 })); cloth.position.set(0.66, 0.001, -0.13); S.scene.add(cloth);
  var slabMat = new T.MeshPhysicalMaterial({ color: 0xf6fffc, roughness: 0, metalness: 0, transmission: 1, thickness: 0.03, ior: p.n, specularIntensity: 1,
    attenuationColor: new T.Color(MAT[1]), attenuationDistance: 0.12, envMapIntensity: 1.2 });
  var edgeMat = new T.LineBasicMaterial({ color: 0x8fc8b6, transparent: true, opacity: 0.75 });
  SLABS.forEach(function (sl, i) { var g = new T.Group(); S.scene.add(g);
    var geo = new T.BoxGeometry(SW, sl.t, SDp); var m = S.mesh(geo, slabMat); m.position.y = sl.t / 2; m.renderOrder = 3; g.add(m);
    var e = new T.LineSegments(new T.EdgesGeometry(geo), edgeMat); e.position.y = sl.t / 2; g.add(e);
    sl.g = g; sl.home = new T.Vector3(0.5 + i * 0.1, 0.002, -0.14); g.position.copy(sl.home);
    var tag = S.label('Slab ' + sl.id, { w: 0.03, ratio: 0.32, color: '#1b2a6b', bg: '#f6f2e4', weight: 700 }); tag.rotation.x = -Math.PI / 2; tag.position.set(sl.home.x, 0.0024, -0.072); S.scene.add(tag);
    sl.sh = S.contact(SW + 0.03, SDp + 0.03, sl.home.x, sl.home.z, 0.35, 0.002); });
  if (MAT[2]) { var mLab = S.label(MAT[2], { w: 0.07, ratio: 0.16, color: '#f6f2e4', bg: '#1b2a6b', weight: 700 }); mLab.rotation.x = -Math.PI / 2; mLab.position.set(0.66, 0.0012, -0.05); S.scene.add(mLab); }
  var grains = (function () { var n = 260, pos = new Float32Array(n * 3), i; for (i = 0; i < n; i++) { var rr = Math.sqrt(S.rnd()) * 0.016, a = S.rnd() * Math.PI * 2; pos[i * 3] = Math.cos(a) * rr; pos[i * 3 + 1] = 0.0004; pos[i * 3 + 2] = Math.sin(a) * rr * 0.8; }
    var gg = new T.BufferGeometry(); gg.setAttribute('position', new T.BufferAttribute(pos, 3));
    var pm = new T.Points(gg, new T.PointsMaterial({ color: 0xe9cf5a, size: 0.0011, sizeAttenuation: true })); pm.visible = false; S.scene.add(pm); return pm; })();
  var shaker = new T.Group(); S.scene.add(shaker);
  var sb = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.05, 24), new T.MeshPhysicalMaterial({ color: 0xf6e9a8, roughness: 0.2, transmission: 0.5, thickness: 0.01 })); sb.position.y = 0.025; shaker.add(sb);
  var sp = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.03, 24), new T.MeshStandardMaterial({ color: 0xe0c24a, roughness: 0.9 })); sp.position.y = 0.016; shaker.add(sp);
  var sc = S.mesh(new T.CylinderGeometry(0.0145, 0.0145, 0.01, 24), M.alu); sc.position.y = 0.055; shaker.add(sc);
  var sLab = S.label('LYCOPODIUM', { w: 0.026, ratio: 0.3, color: '#5a3d0a', bg: '#fff8dc', weight: 700 }); sLab.position.set(0, 0.03, 0.0142); shaker.add(sLab);
  var SHAKER_HOME = new T.Vector3(0.44, 0, -0.03); shaker.position.copy(SHAKER_HOME); S.contact(0.05, 0.05, SHAKER_HOME.x, SHAKER_HOME.z, 0.45);

  S.addApparatus('micro', micro, 'Travelling microscope', 'Moves up and down a pillar by a rack and pinion. Main scale 0.5 mm, vernier 50 divisions: least count 0.001 cm.');
  S.addApparatus('knob', knob, 'Focusing knob', 'Turn it to raise or lower the microscope until the object is sharp, with no parallax against the cross-wires.');
  S.addApparatus('mark', paper, 'Ink mark on paper', 'A fine cross drawn in ink: the object whose real and apparent depths you compare.');
  S.addApparatus('slabs', cloth, (GLASSY ? MAT[0].replace('Glass', 'Glass') : MAT[0]) + ' slabs A–D', (SAMPLE ? SAMPLE + '. ' : '') + 'Four slabs of the same ' + (GLASSY ? MAT[0].toLowerCase().replace(/^glass$/, 'glass') : MAT[0].toLowerCase().replace(' (pmma)', ' (PMMA)')) + ', of different thicknesses. You measure each thickness with the microscope.');
  S.addApparatus('powder', shaker, 'Lycopodium powder', 'A fine yellow powder sprinkled on top of the slab, so the microscope can focus on the top surface.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudR = S.hudCard('Microscope reading'), hudF = S.hudCard('In focus'), hudN = S.hudCard('Slabs done');

  // ---------- optics: the kernel's apparent depth
  function app(t) { var q = Object.assign({}, p, { t: t }); return K.view(null, q).app; }
  function layers() {     // what lies under the objective, at the height it APPEARS to be (m above the paper)
    var L = [{ k: 'mark', h: 0 }];
    if (st.onMark) { var t = st.onMark.t; L[0].h = t - app(t); L[0].glass = true; if (st.powder) L.push({ k: 'powder', h: t }); L.push({ k: 'top', h: t }); }
    return L; }
  function defocus(k) { var l = layers().filter(function (x) { return x.k === k; })[0]; return l ? Math.abs(st.F - l.h) : Infinity; }
  function inFocus() { var best = null; layers().forEach(function (l) { if (l.k === 'top') return; var d = Math.abs(st.F - l.h); if (d < 0.00003 && (!best || d < best.d)) best = { k: l.k, d: d }; }); return best; }
  function focusWord() { if (!st.eyeFocused) return 'Eyepiece not set'; var f = inFocus(); if (f) return f.k === 'mark' ? (st.onMark ? 'Mark (through the slab)' : 'Ink mark') : 'Powder on top';
    var near = layers().filter(function (l) { return l.k !== 'top'; }).reduce(function (m, l) { return Math.min(m, Math.abs(st.F - l.h)); }, Infinity);
    return near < 0.0003 ? 'Nearly' : 'Nothing sharp'; }

  // ---------- the view in the eyepiece (a canvas in the side panel)
  var eye = document.createElement('canvas'); eye.width = 300; eye.height = 300; eye.setAttribute('role', 'img'); eye.setAttribute('aria-label', 'View through the microscope eyepiece');
  eye.style.cssText = 'width:220px;height:220px;align-self:center;border-radius:50%;background:#111;box-shadow:0 0 0 6px #1c1c1f, 0 0 0 8px #444;';
  var grainPts = []; for (var gi = 0; gi < 90; gi++) grainPts.push([S.rnd() * 300, S.rnd() * 300, 2 + S.rnd() * 3]);
  var fibre = []; for (gi = 0; gi < 160; gi++) fibre.push([S.rnd() * 300, S.rnd() * 300, S.rnd() * Math.PI, 8 + S.rnd() * 26]);
  var lastEye = '';
  function blurPx(d) { return 34 * d / (d + 0.0012); }
  function drawEye() {
    var key = [st.F.toFixed(6), st.eyeFocused, st.onMark && st.onMark.id, st.powder].join('|'); if (key === lastEye) return; lastEye = key;
    var x = eye.getContext('2d'), w = 300, h = 300; x.save(); x.clearRect(0, 0, w, h); x.beginPath(); x.arc(150, 150, 150, 0, Math.PI * 2); x.clip();
    var L = layers(), mk = L[0], dm = Math.abs(st.F - mk.h);
    x.save(); x.filter = 'blur(' + blurPx(dm).toFixed(2) + 'px)';
    x.fillStyle = mk.glass ? '#e6efe9' : '#f3f0e6'; x.fillRect(-20, -20, w + 40, h + 40);
    x.strokeStyle = 'rgba(150,140,120,0.35)'; x.lineWidth = 1.2; fibre.forEach(function (f) { x.beginPath(); x.moveTo(f[0], f[1]); x.lineTo(f[0] + Math.cos(f[2]) * f[3], f[1] + Math.sin(f[2]) * f[3]); x.stroke(); });
    x.strokeStyle = mk.glass ? 'rgba(27,42,107,0.85)' : '#1b2a6b'; x.lineWidth = 14; x.lineCap = 'round';
    x.beginPath(); x.moveTo(40, 158); x.lineTo(268, 158); x.moveTo(158, 40); x.lineTo(158, 268); x.stroke(); x.restore();
    if (st.onMark && st.powder) { var dp = Math.abs(st.F - st.onMark.t); x.save(); x.filter = 'blur(' + blurPx(dp).toFixed(2) + 'px)';
      grainPts.forEach(function (g) { x.fillStyle = 'rgba(214,170,40,0.95)'; x.beginPath(); x.arc(g[0], g[1], g[2], 0, Math.PI * 2); x.fill(); x.fillStyle = 'rgba(255,240,170,0.9)'; x.beginPath(); x.arc(g[0] - g[2] * 0.3, g[1] - g[2] * 0.3, g[2] * 0.35, 0, Math.PI * 2); x.fill(); }); x.restore(); }
    var vg = x.createRadialGradient(150, 150, 90, 150, 150, 152); vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,0.75)'); x.fillStyle = vg; x.fillRect(0, 0, w, h);
    x.save(); if (!st.eyeFocused) x.filter = 'blur(3px)'; x.strokeStyle = 'rgba(10,10,10,0.9)'; x.lineWidth = 1.5; x.beginPath(); x.moveTo(150, 10); x.lineTo(150, 290); x.moveTo(10, 150); x.lineTo(290, 150); x.stroke(); x.restore();
    x.restore(); }

  // ---------- human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function knobWorld() { var v = new T.Vector3(); knob.getWorldPosition(v); return v.add(new T.Vector3(0, 0, 0.017)); }
  function focusEyepiece() {
    if (st.eyeFocused) return Promise.resolve(true); if (S.hand.busy) return wait();
    var w = new T.Vector3(); eyeG.getWorldPosition(w); w.y += 0.006; w.x += 0.011;
    return S.hand.pinchMove(w, function () { return w; }, function (k) { eyeG.rotation.y = -k * 2.2; }, { ms: 900, reachMs: 700 })
      .then(function () { st.eyeFocused = true; lastEye = ''; drawEye(); S.say('The cross-wires look sharp and black. Now focus only with the rack-and-pinion knob.'); S.render(); return true; });
  }
  function turn(dM) {     // turn the focusing knob: the microscope moves up (+) or down (−) by dM metres
    if (S.hand.busy) return wait();
    if (!st.eyeFocused) { S.say('First focus the eyepiece on the cross-wires.'); return Promise.resolve(false); }
    var F0 = st.F, F1 = Math.round((F0 + dM) * 1e5) / 1e5;
    if (F1 < -0.004 || F1 > 0.12) { S.say('The microscope has reached the end of its travel.'); return Promise.resolve(false); }
    if (st.onMark && F1 + WD < st.onMark.t + 0.004) { S.say('Stop: the objective would touch the slab. Focus by raising it, not lowering.'); return Promise.resolve(false); }
    var ms = Math.min(1600, 500 + Math.abs(dM) * 40000), rot0 = knob.rotation.x;
    function at(k) { return F0 + (F1 - F0) * k; }
    return S.hand.pinchMove(knobWorld(), function (k) { var keep = st.F; st.F = at(k); setCar(); var q = knobWorld(); st.F = keep; return q; },
      function (k) { st.F = at(k); setCar(); knob.rotation.x = rot0 - (F1 - F0) * k * 400; drawEye(); }, { ms: ms, reachMs: 500, hold: 80, mode: 'front' })
      .then(function () { st.F = F1; setCar(); drawEye(); S.render(); return true; });
  }
  function focusOn(h) { return turn(Math.round((h - st.F) * 1e5) / 1e5); }   // used by the walk-through: the same knob, turned to the right place
  function slabPath(sl, from, to) { return function (k) { var q = from.clone().lerp(to, k); q.y += 0.03 * Math.sin(Math.PI * k); return q; }; }
  function placeSlab() {
    if (S.hand.busy) return wait();
    if (st.onMark) { S.say('Slab ' + st.onMark.id + ' is already on the mark. Remove it first.'); return Promise.resolve(false); }
    var sl = SLABS.filter(function (s) { return s.id === st.pick; })[0];
    if (st.F + WD < sl.t + 0.006) { S.say('Raise the microscope first, so the slab fits under the objective.'); return Promise.resolve(false); }
    var to = new T.Vector3(MX, PAPER_Y + 0.0002, OBJ_Z), path = slabPath(sl, sl.home.clone(), to), grip = new T.Vector3(SW / 2 + 0.002, sl.t * 0.6, 0);
    st.R2 = null; st.R3 = null;
    return S.hand.pinchMove(path(0).add(grip), function (k) { return path(k).add(grip); }, function (k) { var q = path(k); sl.g.position.copy(q); sl.sh.position.set(q.x, (k > 0.5 ? PAPER_Y : 0.002) + 0.0008, q.z); }, { ms: 1400, pose: 'grip' })
      .then(function () { sl.g.position.copy(to); sl.sh.position.set(to.x, PAPER_Y + 0.0008, to.z); st.onMark = sl; lastEye = ''; drawEye(); S.say('Slab ' + sl.id + ' is on the mark. The mark now looks blurred: it seems to have risen.'); S.render(); return true; });
  }
  function removeSlab() {
    if (S.hand.busy) return wait(); var sl = st.onMark; if (!sl) return Promise.resolve(true);
    var from = sl.g.position.clone(), path = slabPath(sl, from, sl.home.clone()), grip = new T.Vector3(SW / 2 + 0.002, sl.t * 0.6, 0);
    return S.hand.pinchMove(path(0).add(grip), function (k) { return path(k).add(grip); }, function (k) { var q = path(k); sl.g.position.copy(q); sl.sh.position.set(q.x, (k < 0.5 ? PAPER_Y : 0.002) + 0.0008, q.z); if (k > 0.05) grains.visible = false; }, { ms: 1300, pose: 'grip' })
      .then(function () { sl.g.position.copy(sl.home); sl.sh.position.set(sl.home.x, 0.0028, sl.home.z); st.onMark = null; st.powder = false; grains.visible = false; st.R1 = null; st.R2 = null; st.R3 = null; lastEye = ''; drawEye(); S.say('Slab ' + sl.id + ' wiped and put back on the cloth.'); S.render(); return true; });
  }
  function sprinkle() {
    if (S.hand.busy) return wait();
    if (!st.onMark) { S.say('Put a slab on the mark first.'); return Promise.resolve(false); }
    if (st.powder) return Promise.resolve(true);
    var top = st.onMark.t, over = new T.Vector3(MX + 0.05, PAPER_Y + top + 0.035, OBJ_Z + 0.012), from = SHAKER_HOME.clone();
    function at(k) { if (k < 0.6) { var a = k / 0.6, q = from.clone().lerp(over, a); q.y += 0.04 * Math.sin(Math.PI * a); return q; } return over.clone(); }
    var grip = new T.Vector3(0.016, 0.03, 0);
    return S.hand.pinchMove(at(0).add(grip), function (k) { return at(k).add(grip); }, function (k) { shaker.position.copy(at(k)); shaker.rotation.z = k < 0.6 ? 0 : Math.sin((k - 0.6) / 0.4 * Math.PI) * 1.9 + 0.05 * Math.sin(k * 90);
        if (k > 0.75) { grains.visible = true; grains.position.set(MX, PAPER_Y + top + 0.0002, OBJ_Z); } }, { ms: 1500, pose: 'grip', hold: 100 })
      .then(function () { shaker.position.copy(SHAKER_HOME); shaker.rotation.z = 0; grains.visible = true; grains.position.set(MX, PAPER_Y + top + 0.0002, OBJ_Z); st.powder = true; lastEye = ''; drawEye(); S.say('A thin layer of powder lies on the top of the slab.'); S.render(); return true; });
  }
  function take(which) {
    if (S.hand.busy) { wait(); return false; }
    var f = inFocus();
    if (!st.eyeFocused) { S.say('First focus the eyepiece on the cross-wires.'); return false; }
    if (which === 'R1') { if (st.onMark) { S.say('R1 is the mark with no slab on it. Remove the slab first.'); return false; }
      if (!f || f.k !== 'mark') { S.say('The ink mark is not in sharp focus yet. Turn the knob in small steps.'); return false; } }
    if (which === 'R2') { if (st.R1 === null) { S.say('Take R1 first, with no slab on the mark.'); return false; } if (!st.onMark) { S.say('Place the slab on the mark first.'); return false; }
      if (!f || f.k !== 'mark') { S.say('Focus on the mark seen through the slab: it is now higher than before. Raise the microscope.'); return false; } }
    if (which === 'R3') { if (st.R2 === null) { S.say('Take R2 first.'); return false; } if (!st.powder) { S.say('Sprinkle a little lycopodium powder on the slab first.'); return false; }
      if (!f || f.k !== 'powder') { S.say('Focus on the powder grains on top of the slab.'); return false; } }
    var R = reading(), sp = split(R); st[which] = R;
    S.say(which + ' = ' + sp.msr.toFixed(2) + ' cm + ' + sp.vsr + ' × 0.001 cm = ' + R.toFixed(3) + ' cm.');
    if (which === 'R3') {
      if (S.rows.some(function (r) { return r.slab === st.onMark.id; })) S.say('You already have slab ' + st.onMark.id + ' in the table; this set replaces nothing. Use another slab.');
      else S.addRow({ slab: st.onMark.id, R1: st.R1, R2: st.R2, R3: st.R3 });
    }
    S.render(); return true;
  }
  function doSlab(sl) {
    st.pick = sl.id;
    return removeSlab().then(function () { return focusOn(0); }).then(function () { take('R1'); return placeSlab(); }).then(function () { return focusOn(sl.t - app(sl.t)); }).then(function () { take('R2'); return sprinkle(); })
      .then(function () { return focusOn(sl.t); }).then(function () { take('R3'); }); }

  var VIEWS = { micro: [[MX + 0.32, 0.36, MZ + 0.5], [MX, 0.13, MZ]], knob: [[PIL_X - 0.12, 0.22, PIL_Z + 0.2], [PIL_X - 0.04, 0.15, PIL_Z]],
    scale: [[0, 0, 0], [0, 0, 0]], stage: [[MX + 0.16, 0.13, MZ + 0.3], [MX, 0.04, OBJ_Z]], mark: [[MX + 0.12, 0.16, MZ + 0.26], [MX, 0.03, OBJ_Z]],
    slabs: [[0.66, 0.2, 0.18], [0.66, 0.01, -0.13]], powder: [[SHAKER_HOME.x + 0.1, 0.14, SHAKER_HOME.z + 0.18], [SHAKER_HOME.x, 0.03, SHAKER_HOME.z]],
    book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] };
  function update() {
    setCar(); drawEye();
    var y = idxY(); VIEWS.scale[0][0] = PIL_X + 0.025; VIEWS.scale[0][1] = y + 0.02; VIEWS.scale[0][2] = FACE + 0.11; VIEWS.scale[1][0] = PIL_X; VIEWS.scale[1][1] = y + 0.006; VIEWS.scale[1][2] = FACE;
    hudR.set(reading().toFixed(3) + ' cm'); hudF.set(focusWord()); hudN.set(S.rows.length + ' of 4');
  }
  function nFrom(r) { return (r.R3 - r.R1) / (r.R3 - r.R2); }
  update();

  return {
    camera: { pos: [0.55, 0.55, 0.62], look: [0.3, 0.1, -0.22] },
    views: VIEWS,
    theory: { principle: 'Light from a mark under a glass slab bends away from the normal as it leaves the glass, so the mark seems to be raised. Seen from straight above, real depth / apparent depth = n. A travelling microscope measures both depths as differences of its readings.',
      formula: 'n = (R₃ − R₁) / (R₃ − R₂)', formulaNote: 'R₁: mark without the slab · R₂: mark seen through the slab · R₃: powder on top of the slab · real depth = R₃ − R₁, apparent depth = R₃ − R₂',
      more: ['Least count = value of one main-scale division / number of vernier divisions = 0.5 mm / 50 = 0.01 mm = 0.001 cm. Reading = main scale + vernier division in line × 0.001 cm.'],
      precautions: 'Focus the eyepiece on the cross-wires first. Move the microscope in one direction only (upwards) while taking a set of readings, to avoid backlash. Focus until there is no parallax between the image and the cross-wires. Use only a thin layer of powder.' },
    book: { title: 'Expt. — Glass slab (travelling microscope)', lines: ['Aim: n of ' + (MAT[2] ? MAT[0].toLowerCase().replace(' (pmma)', ' (PMMA)') : 'glass') + ' by real and apparent depth.', 'LC = 0.5 mm / 50 = 0.001 cm', 'R1: mark;  R2: mark through slab;', 'R3: powder on top of slab', 'n = (R3 − R1) / (R3 − R2)'],
      columns: [{ label: 'Slab', get: function (r) { return r.slab; } }, { label: 'R1 (cm)', get: function (r) { return r.R1.toFixed(3); } }, { label: 'R2 (cm)', get: function (r) { return r.R2.toFixed(3); } },
        { label: 'R3 (cm)', get: function (r) { return r.R3.toFixed(3); } }, { label: 'Real', get: function (r) { return (r.R3 - r.R1).toFixed(3); } }, { label: 'App.', get: function (r) { return (r.R3 - r.R2).toFixed(3); } },
        { label: 'n', get: function (r) { return nFrom(r).toFixed(3); } }] },
    graph: { x: function (r) { return r.R3 - r.R2; }, y: function (r) { return r.R3 - r.R1; }, xlabel: 'apparent depth (cm)', ylabel: 'real depth (cm)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) { var ns = (rows || []).map(nFrom).filter(isFinite); if (ns.length < 2) return null;
      return { label: 'n', value: S.fit.mean(ns), unit: '', digits: 3, truth: p.n, note: 'Mean of (R₃ − R₁)/(R₃ − R₂). The slope of real depth against apparent depth is n too.' }; },
    tol: 0.01,
    chips: ['Why does the mark seem raised?', 'How do I read the vernier?', 'Why sprinkle lycopodium powder?', 'Check my readings', 'What is backlash error?'],
    viva: [['Why is lycopodium powder sprinkled on the slab?', ['To mark the top surface so the microscope can focus on it', 'To make the glass opaque', 'To reduce reflection'], 0, 'Clean glass has nothing to focus on; the fine grains show where the top surface is.'],
      ['If the slab were thicker, the apparent rise of the mark would be…', ['larger', 'smaller', 'the same'], 0, 'Shift = t(1 − 1/n): it grows with the thickness.']],
    askState: function () { var sp = split(reading()); return { microscope_reading_cm: reading(), main_scale_cm: +sp.msr.toFixed(2), vernier_division: sp.vsr, least_count_cm: 0.001, eyepiece_focused: st.eyeFocused,
      in_sharp_focus: focusWord(), slab_on_mark: st.onMark ? st.onMark.id : null, powder_on_slab: st.powder, R1_cm: st.R1, R2_cm: st.R2, R3_cm: st.R3, sets_recorded: S.rows.length }; },

    steps: [
      { id: 'setup', title: 'Set up', view: 'micro', render: function (u) {
          u.h2('Set up the travelling microscope');
          u.p('The microscope stands over a sheet of paper with a fine ink cross. Level the base, then turn the eyepiece until the cross-wires look sharp and black. From then on, focus only with the rack-and-pinion knob.');
          u.task('1. Focus the eyepiece on the cross-wires', st.eyeFocused, st.eyeFocused ? 'Cross-wires sharp' : 'Turn the eyepiece slowly')
            .add(u.button(st.eyeFocused ? 'Done' : 'Turn the eyepiece', function () { focusEyepiece(); }, !st.eyeFocused, st.eyeFocused || S.hand.busy));
          u.el(eye); drawEye();
          u.task('2. Find the least count', true, 'Main scale 0.5 mm, vernier 50 divisions → LC = 0.001 cm').add(u.button('Look at the scales', function () { update(); S.focus('scale'); }));
          u.next('Next: take the readings', st.eyeFocused);
        },
        ok: function () { return st.eyeFocused; },
        auto: function () { return focusEyepiece(); } },
      { id: 'read', title: 'Readings', view: 'stage', render: function (u) {
          var sp = split(reading());
          u.h2('R1, R2 and R3 for each slab');
          u.p('R1: focus on the ink mark. Then place a slab on it and focus on the mark again (R2). Sprinkle powder on the slab and focus on the grains (R3). Repeat with at least three slabs.');
          u.el(eye); drawEye();
          u.live(function () { var s2 = split(reading()); return 'Reading ' + reading().toFixed(3) + ' cm  ·  ' + s2.msr.toFixed(2) + ' + ' + s2.vsr + ' × 0.001'; });
          u.live(function () { return 'In focus: ' + focusWord(); }, 'live small');
          function tb(lbl, d) { return u.button(lbl, function () { turn(d); }, false, S.hand.busy); }
          u.h3('Focusing knob');
          u.row(tb('▲ 1 cm', 0.01), tb('▲ 1 mm', 0.001), tb('▲ 0.1 mm', 0.0001), tb('▲ 0.01 mm', 0.00001));
          u.row(tb('▼ 1 cm', -0.01), tb('▼ 1 mm', -0.001), tb('▼ 0.1 mm', -0.0001), tb('▼ 0.01 mm', -0.00001));
          u.h3('Slab');
          var pickRow = u.row(); SLABS.forEach(function (sl) { var done = S.rows.some(function (r) { return r.slab === sl.id; });
            var b = u.button('Slab ' + sl.id + (done ? ' ✓' : ''), function () { st.pick = sl.id; S.render(); }, st.pick === sl.id, !!st.onMark || S.hand.busy); pickRow.appendChild(b); });
          u.row(u.button('Place it on the mark', function () { placeSlab(); }, false, !!st.onMark || S.hand.busy), u.button('Sprinkle powder', function () { sprinkle(); }, false, !st.onMark || st.powder || S.hand.busy),
            u.button('Remove the slab', function () { removeSlab(); }, false, !st.onMark || S.hand.busy));
          u.task('Readings for slab ' + (st.onMark ? st.onMark.id : st.pick), st.R3 !== null, 'R1 ' + (st.R1 === null ? '—' : st.R1.toFixed(3)) + '  ·  R2 ' + (st.R2 === null ? '—' : st.R2.toFixed(3)) + '  ·  R3 ' + (st.R3 === null ? '—' : st.R3.toFixed(3)) + ' cm')
            .add(u.row(u.button('Take R1', function () { take('R1'); }, true, S.hand.busy), u.button('Take R2', function () { take('R2'); }, true, S.hand.busy), u.button('Take R3', function () { take('R3'); }, true, S.hand.busy)));
          u.row(u.button('Look at the scales', function () { update(); S.focus('scale'); }), u.button('Look at the slab', function () { S.focus('stage'); }));
          u.note('Main scale ' + sp.msr.toFixed(2) + ' cm + vernier ' + sp.vsr + ' × 0.001 cm. Raise the microscope through each set (R1 → R2 → R3) so the rack’s backlash never enters.');
          u.h3('Observation table'); u.table();
          u.next('Next: graph and result', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 slabs measured.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () { return SLABS.reduce(function (pr, sl) { return pr.then(function () { return doSlab(sl); }); }, Promise.resolve()).then(function () { return removeSlab(); }); } },
    ],

    tick: function () { update(); },
  };
});
