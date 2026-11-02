/* Prayogshala studio module: Prism, angle of minimum deviation (NCERT Class XII). A drawing board with a sheet of white paper,
   a 60° glass prism, steel pins, a pencil and a protractor. The hand places the prism, traces it, draws the incident ray,
   pushes the pins in, sights the emergent pins and measures δ. Every ray and angle is the prism kernel's exact trace
   ('rays', 'dev', 'e'); the glass's n is the lab's hidden unknown. n = sin((A + δm)/2) / sin(A/2). */
HoolaStudio.define('prism-minimum-deviation', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.prism, DEG = Math.PI / 180;
  var p = window.HoolaKernels.paramsFor('prism', S.lab.params);
  (S.lab.knobs || []).forEach(function (k) { if (k.param === 'n' && isFinite(k.value)) p.n = +k.value; });   // the hidden glass
  var PX = 0.25, PZ = -0.21, BT = 0.018, PAPER_W = 0.40, PAPER_D = 0.28, KCX = 0.018, KCY = 0.012;   // board / paper / kernel centre
  var PY = BT + 0.0004;                                         // paper surface
  function W(q, y) { return new T.Vector3(PX + q[0] - KCX, y === undefined ? PY : y, PZ - (q[1] - KCY)); }   // kernel (x, y) on the paper -> world
  var st = { placed: false, traced: false, iSet: 40, cur: null, protOn: false, prismOn: false };

  // ---------- drawing board, paper, drawing pins
  var board = new T.Group(); S.scene.add(board);
  var bd = S.rounded(0.47, 0.35, BT, 0.006, M.wood); bd.rotation.x = -Math.PI / 2; bd.position.set(PX, BT / 2, PZ); board.add(bd);
  var cleat = S.mesh(new T.BoxGeometry(0.012, BT + 0.004, 0.35), M.darkWood); cleat.position.set(PX - 0.24, (BT + 0.004) / 2, PZ); board.add(cleat);
  S.contact(0.55, 0.43, PX, PZ, 0.5);
  var PXM = 4000, CW = Math.round(PAPER_W * PXM), CH = Math.round(PAPER_D * PXM);
  var paperTex = S.liveTex(CW, CH);
  var paper = new T.Mesh(new T.PlaneGeometry(PAPER_W, PAPER_D), new T.MeshStandardMaterial({ map: paperTex, roughness: 0.95 }));
  paper.rotation.x = -Math.PI / 2; paper.position.set(PX, PY, PZ); paper.receiveShadow = true; board.add(paper);
  [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(function (c) { var t = new T.Group();
    var head = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.0016, 20), M.brass); head.position.y = 0.0008; t.add(head);
    t.position.set(PX + c[0] * (PAPER_W / 2 - 0.012), PY, PZ + c[1] * (PAPER_D / 2 - 0.012)); board.add(t); });

  function C(q) { return [(q[0] - KCX + PAPER_W / 2) * PXM, (PAPER_D / 2 - (q[1] - KCY)) * PXM]; }
  var strokes = [], marks = [], words = [];
  function drawPaper() {
    paperTex.draw(function (x, w, h) {
      x.fillStyle = '#f7f6f1'; x.fillRect(0, 0, w, h);
      x.fillStyle = 'rgba(120,110,90,0.05)'; for (var i = 0; i < 400; i++) { var s0 = (i * 7919) % 997 / 997, s1 = (i * 104729) % 991 / 991; x.fillRect(s0 * w, s1 * h, 2, 2); }
      x.lineCap = 'round'; x.lineJoin = 'round';
      strokes.forEach(function (sk) { if (sk.frac <= 0) return; var pts = sk.pts, segs = pts.length - 1, upto = sk.frac * segs;
        x.strokeStyle = sk.color || 'rgba(38,38,44,0.92)'; x.lineWidth = (sk.w || 3) * 1.9; x.setLineDash(sk.dash ? [18, 14] : []);
        x.beginPath(); var a = C(pts[0]); x.moveTo(a[0], a[1]);
        for (var j = 1; j <= Math.ceil(upto); j++) { var q0 = pts[j - 1], q1 = pts[j], t = Math.min(1, upto - (j - 1)), q = [q0[0] + (q1[0] - q0[0]) * t, q0[1] + (q1[1] - q0[1]) * t], c = C(q); x.lineTo(c[0], c[1]); }
        x.stroke(); });
      x.setLineDash([]);
      marks.forEach(function (m) { var c = C(m); x.fillStyle = 'rgba(30,30,35,0.9)'; x.beginPath(); x.arc(c[0], c[1], 5, 0, Math.PI * 2); x.fill();
        x.strokeStyle = 'rgba(40,40,45,0.7)'; x.lineWidth = 2; x.beginPath(); x.arc(c[0], c[1], 14, 0, Math.PI * 2); x.stroke(); });
      words.forEach(function (t) { var c = C(t.at); x.fillStyle = t.color || 'rgba(40,40,48,0.92)'; x.font = Math.round((t.size || 44) * 1.35) + 'px "Caveat", "Comic Sans MS", cursive'; x.textAlign = 'center'; x.fillText(t.text, c[0], c[1]); });
    });
  }

  // ---------- the prism (kernel geometry: apex A up the page, base BC towards you)
  var A = p.A, SD = p.side, apex = [0, SD * Math.cos(A / 2)], bl = [-SD * Math.sin(A / 2), 0], br = [SD * Math.sin(A / 2), 0];
  var shape = new T.Shape(); shape.moveTo(apex[0], apex[1]); shape.lineTo(bl[0], bl[1]); shape.lineTo(br[0], br[1]); shape.closePath();
  var prismGeo = new T.ExtrudeGeometry(shape, { depth: 0.036, bevelEnabled: true, bevelThickness: 0.0008, bevelSize: 0.0008, bevelSegments: 2 });
  var prismMat = new T.MeshPhysicalMaterial({ color: 0xf6fffc, roughness: 0, metalness: 0, transmission: 1, thickness: 0.035, ior: 1.5, specularIntensity: 1,
    attenuationColor: new T.Color(0xa6dcca), attenuationDistance: 0.14, envMapIntensity: 1.2 });
  var prism = new T.Group(); S.scene.add(prism);
  var glassM = S.mesh(prismGeo, prismMat); glassM.rotation.x = -Math.PI / 2; glassM.position.y = 0.0008; glassM.renderOrder = 3; prism.add(glassM);
  var edgeG = new T.EdgesGeometry(prismGeo, 30), edges = new T.LineSegments(edgeG, new T.LineBasicMaterial({ color: 0x9fc9c0, transparent: true, opacity: 0.6 }));
  edges.rotation.x = -Math.PI / 2; edges.position.y = 0.0008; prism.add(edges);
  var prShadow = S.contact(0.13, 0.12, 0, 0, 0.22, PY);
  var PRISM_HOME = new T.Vector3(PX + 0.36, 0, PZ - 0.06), PRISM_ON = W([0, 0], PY);
  function setPrism(pos) { prism.position.copy(pos); var onB = Math.abs(pos.x - PRISM_ON.x) < 0.2 && Math.abs(pos.z - PRISM_ON.z) < 0.15; prShadow.position.set(pos.x, (onB ? PY : 0) + 0.0008, pos.z - SD * 0.3); prShadow.material.opacity = 0.22 * Math.max(0.2, 1 - Math.max(0, pos.y - (onB ? PY : 0)) * 12); }
  setPrism(PRISM_HOME);
  var hold = new T.Vector3(0, 0.036, -SD * Math.cos(A / 2) * 0.4);   // where the fingers hold it: top face, near the middle

  // ---------- steel pins in a pin cushion
  var cushion = new T.Group(); S.scene.add(cushion);
  var pad = S.rounded(0.07, 0.05, 0.02, 0.008, new T.MeshStandardMaterial({ color: 0xa8322a, roughness: 0.95 })); pad.rotation.x = -Math.PI / 2; pad.position.y = 0.01; cushion.add(pad);
  cushion.position.set(PX + 0.31, 0, PZ + 0.14); S.contact(0.1, 0.08, cushion.position.x, cushion.position.z, 0.45);
  var PIN_L = 0.04, pins = [], pinCols = [0x2e6fd6, 0x2e6fd6, 0xd8a21c, 0xd8a21c];
  for (var k = 0; k < 4; k++) { var g = new T.Group();
    var shaft = S.mesh(new T.CylinderGeometry(0.0005, 0.0005, PIN_L, 8), M.steel); shaft.position.y = PIN_L / 2; g.add(shaft);
    var hd = S.mesh(new T.SphereGeometry(0.0028, 16, 12), new T.MeshStandardMaterial({ color: pinCols[k], roughness: 0.3, metalness: 0.1 })); hd.position.y = PIN_L + 0.002; g.add(hd);
    S.scene.add(g); pins.push({ g: g, home: new T.Vector3(cushion.position.x - 0.022 + k * 0.015, 0.012, cushion.position.z), at: null }); g.position.copy(pins[k].home); }
  var pinSh = pins.map(function () { var m = S.contact(0.012, 0.012, 0, 0, 0.0, PY); return m; });
  function placePin(i, pos) { pins[i].g.position.copy(pos); var onPaper = Math.abs(pos.y - (PY - 0.006)) < 0.002; pinSh[i].position.set(pos.x + 0.004, PY + 0.0008, pos.z + 0.003); pinSh[i].material.opacity = onPaper ? 0.5 : 0; }

  // ---------- pencil and protractor
  var pencil = new T.Group(); S.scene.add(pencil);
  var pbody = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.13, 6), new T.MeshStandardMaterial({ color: 0xe8b024, roughness: 0.5 })); pbody.position.y = 0.0145 + 0.065; pencil.add(pbody);
  var pcone = S.mesh(new T.ConeGeometry(0.0035, 0.014, 12), M.wood); pcone.rotation.x = Math.PI; pcone.position.y = 0.007; pencil.add(pcone);
  var plead = S.mesh(new T.ConeGeometry(0.0011, 0.004, 8), M.black); plead.rotation.x = Math.PI; plead.position.y = 0.002; pencil.add(plead);
  var pend = S.mesh(new T.CylinderGeometry(0.0036, 0.0036, 0.008, 12), new T.MeshStandardMaterial({ color: 0xd88aa0, roughness: 0.8 })); pend.position.y = 0.1495; pencil.add(pend);
  var UP = new T.Vector3(0, 1, 0), WRITE = new T.Vector3(0.38, 0.88, 0.28).normalize(), REST_DIR = new T.Vector3(1, 0, 0.12).normalize();
  var PENCIL_REST = new T.Vector3(PX + 0.08, BT + 0.0036, PZ + 0.158);
  function setPencil(tip, dir) { pencil.position.copy(tip); pencil.quaternion.setFromUnitVectors(UP, dir); }
  setPencil(PENCIL_REST.clone().sub(REST_DIR.clone().multiplyScalar(0.0)), REST_DIR);

  var protTex = S.canvasTex(1024, 560, function (x, w) { var cx = w / 2, cy = 520, R = 480;
    x.fillStyle = 'rgba(225,240,255,0.22)'; x.beginPath(); x.moveTo(cx - R, cy); x.arc(cx, cy, R, Math.PI, 2 * Math.PI); x.closePath(); x.fill();
    x.strokeStyle = 'rgba(15,35,65,.92)'; x.fillStyle = 'rgba(15,35,65,.95)'; x.font = '600 22px "Public Sans", sans-serif'; x.textAlign = 'center';
    for (var d = 0; d <= 180; d++) { var a = Math.PI + Math.PI * d / 180, len = d % 10 === 0 ? 40 : d % 5 === 0 ? 26 : 14; x.lineWidth = d % 10 === 0 ? 2.4 : 1.2;
      x.beginPath(); x.moveTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); x.lineTo(cx + Math.cos(a) * (R - len), cy + Math.sin(a) * (R - len)); x.stroke();
      if (d % 10 === 0) x.fillText(String(d), cx + Math.cos(a) * (R - 64), cy + Math.sin(a) * (R - 64) + 8); }
    x.lineWidth = 1.5; x.beginPath(); x.moveTo(cx - R, cy); x.lineTo(cx + R, cy); x.moveTo(cx, cy); x.lineTo(cx, cy - 30); x.stroke(); });
  var prot = new T.Group(); S.scene.add(prot);
  var protM = new T.Mesh(new T.PlaneGeometry(0.1, 0.0547), new T.MeshStandardMaterial({ map: protTex, transparent: true, roughness: 0.15, depthWrite: false, side: T.DoubleSide }));
  protM.rotation.x = -Math.PI / 2; protM.position.set(0, 0.0012, -0.0547 / 2 + 0.0039); protM.renderOrder = 4; prot.add(protM);
  var PROT_HOME = new T.Vector3(PX - 0.16, 0.0006, PZ + 0.26), PROT_HOME_ROT = 0.3;
  prot.position.copy(PROT_HOME); prot.rotation.y = PROT_HOME_ROT;

  // ---------- kernel rays as faint light (optional)
  var rayLine = new T.Line(new T.BufferGeometry(), new T.LineBasicMaterial({ color: 0xff7a3a, transparent: true, opacity: 0.6, depthWrite: false, toneMapped: false }));
  rayLine.visible = false; rayLine.renderOrder = 7; S.scene.add(rayLine);

  S.addApparatus('board', board, 'Drawing board and white paper', 'A soft-wood board with a white sheet held by drawing pins. Pins push into it easily.');
  S.addApparatus('prism', prism, 'Glass prism', 'An equilateral prism, angle A = 60°. Its refractive index is what you will find.');
  S.addApparatus('pins', cushion, 'Steel pins', 'Two pins mark the incident ray; two more are fixed in line with their images, seen through the prism.');
  S.addApparatus('pencil', pencil, 'Sharp pencil', 'Fine lines give exact angles. Draw the outline, the normal and the rays with it.');
  S.addApparatus('prot', prot, 'Protractor', 'Sets the angle of incidence and measures the deviation. Least count 1°; read to half a degree.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudI = S.hudCard('Angle of incidence i'), hudD = S.hudCard('Deviation δ'), hudN = S.hudCard('Readings');

  // ---------- physics from the kernel
  function look(i) { p.i = i * DEG; return K.view(null, p); }
  function geo(i) {
    var v = look(i), r = v.rays[0].p, hit1 = r[1], din = [r[1][0] - r[0][0], r[1][1] - r[0][1]], L = Math.hypot(din[0], din[1]); din = [din[0] / L, din[1] / L];
    var o = { v: v, tir: !!v.tir, hit1: hit1, din: din, start: r[0], P1: [hit1[0] - 0.10 * din[0], hit1[1] - 0.10 * din[1]], P2: [hit1[0] - 0.045 * din[0], hit1[1] - 0.045 * din[1]] };
    if (!v.tir && r.length >= 4) { var hit2 = r[2], end = r[3], d2 = [end[0] - hit2[0], end[1] - hit2[1]], L2 = Math.hypot(d2[0], d2[1]); d2 = [d2[0] / L2, d2[1] / L2];
      o.hit2 = hit2; o.d2 = d2; o.end = end; o.P3 = [hit2[0] + 0.05 * d2[0], hit2[1] + 0.05 * d2[1]]; o.P4 = [hit2[0] + 0.12 * d2[0], hit2[1] + 0.12 * d2[1]];
      var den = din[0] * d2[1] - din[1] * d2[0], t = Math.abs(den) > 1e-12 ? ((hit2[0] - hit1[0]) * d2[1] - (hit2[1] - hit1[1]) * d2[0]) / den : 0.06;
      o.O = [hit1[0] + t * din[0], hit1[1] + t * din[1]]; }
    return o; }
  function half(x) { return Math.round(x * 2) / 2; }
  var n1 = [-Math.cos(A / 2), Math.sin(A / 2)], Q = [(apex[0] + bl[0]) / 2, (apex[1] + bl[1]) / 2];

  // ---------- human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function movePrism(on) {             // the hand carries the prism onto its outline (on) or off the paper
    var a = prism.position.clone(), b = (on ? PRISM_ON : PRISM_HOME).clone();
    function at(k) { var q = a.clone().lerp(b, k); q.y = (k < 1 ? 0.06 * Math.sin(Math.PI * k) : 0) + (b.y - a.y) * k + a.y; return q; }
    return S.hand.pinchMove(at(0).add(hold), function (k) { return at(k).add(hold); }, function (k) { setPrism(at(k)); }, { mode: 'top', ms: 1300, pose: 'grip' })
      .then(function () { setPrism(b); st.prismOn = on; });
  }
  function placePrism() {
    if (st.placed) return Promise.resolve(true); if (S.hand.busy) return wait();
    return movePrism(true).then(function () { st.placed = true; S.say('The prism stands on the paper, its base towards you.'); S.render(); return true; });
  }
  function pencilStroke(list, onDone) {        // list = [{pts, dash}] drawn one after another with the pencil
    var all = []; list.forEach(function (sk) { sk.frac = 0; strokes.push(sk); });
    var lens = list.map(function (sk) { var L = 0; for (var j = 1; j < sk.pts.length; j++) L += Math.hypot(sk.pts[j][0] - sk.pts[j - 1][0], sk.pts[j][1] - sk.pts[j - 1][1]); return L; }), tot = lens.reduce(function (a, b) { return a + b; }, 0) || 1;
    var startW = W(list[0].pts[0], PY + 0.0003), restTip = PENCIL_REST.clone();
    function tipAt(k) {
      if (k < 0.12) { var a = k / 0.12, q = restTip.clone().lerp(startW, a); q.y += 0.04 * Math.sin(Math.PI * a); return q; }
      if (k > 0.92) { var e = (k - 0.92) / 0.08, last = list[list.length - 1].pts, lw = W(last[last.length - 1], PY + 0.0003), q2 = lw.clone().lerp(restTip, e); q2.y += 0.04 * Math.sin(Math.PI * e); return q2; }
      var s = (k - 0.12) / 0.8 * tot, i;
      for (i = 0; i < list.length; i++) { if (s <= lens[i] || i === list.length - 1) break; s -= lens[i]; }
      var pts = list[i].pts, j; for (j = 1; j < pts.length; j++) { var sl = Math.hypot(pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]); if (s <= sl || j === pts.length - 1) { var t = sl > 0 ? Math.min(1, s / sl) : 1;
        return W([pts[j - 1][0] + (pts[j][0] - pts[j - 1][0]) * t, pts[j - 1][1] + (pts[j][1] - pts[j - 1][1]) * t], PY + 0.0003); } s -= sl; }
      return W(pts[pts.length - 1], PY + 0.0003); }
    function progress(k) { var s = Math.max(0, Math.min(1, (k - 0.12) / 0.8)) * tot; list.forEach(function (sk, i) { sk.frac = Math.max(0, Math.min(1, s / (lens[i] || 1))); s -= lens[i]; }); }
    function dirAt(k) { return k < 0.12 || k > 0.92 ? REST_DIR.clone().lerp(WRITE, k < 0.12 ? k / 0.12 : 1 - (k - 0.92) / 0.08).normalize() : WRITE; }
    function grip(k) { return tipAt(k).add(dirAt(k).multiplyScalar(0.035)); }
    var last = -1;
    return S.hand.pinchMove(grip(0), grip, function (k) { setPencil(tipAt(k), dirAt(k)); progress(k); if (Math.abs(k - last) > 0.015 || k === 1) { last = k; drawPaper(); } }, { mode: 'top', ms: 900 + tot * 9000, reachMs: 650 })
      .then(function () { list.forEach(function (sk) { sk.frac = 1; }); setPencil(PENCIL_REST, REST_DIR); drawPaper(); if (onDone) onDone(); return true; });
  }
  function traceOutline() {
    if (!st.placed) { S.say('Place the prism on the paper first.'); return Promise.resolve(false); }
    if (st.traced) return Promise.resolve(true); if (S.hand.busy) return wait();
    var nA = [Q[0] + 0.035 * n1[0], Q[1] + 0.035 * n1[1]], nB = [Q[0] - 0.05 * n1[0], Q[1] - 0.05 * n1[1]];
    return pencilStroke([{ pts: [apex, bl, br, apex] }, { pts: [nA, nB], dash: true, w: 2 }], function () {
      words.push({ text: 'A', at: [apex[0], apex[1] + 0.012] }, { text: 'B', at: [bl[0] - 0.01, bl[1] - 0.008] }, { text: 'C', at: [br[0] + 0.01, br[1] - 0.008] },
        { text: 'N', at: [nA[0] - 0.006, nA[1] + 0.005] }, { text: 'Q', at: [Q[0] + 0.009, Q[1] + 0.001] }, { text: 'A = 60°', at: [apex[0], apex[1] - 0.03], size: 36 });
      st.traced = true; drawPaper(); S.say('Outline traced, and the normal NQ drawn on face AB.'); S.render(); });
  }
  function clearReading() { if (!st.cur) return; strokes = strokes.filter(function (s) { return !s.reading; }); words = words.filter(function (t) { return !t.reading; }); marks = []; st.cur = null; rayLine.visible = false; }
  function drawIncident(i) {
    if (!st.traced) { S.say('Trace the prism and draw the normal first.'); return Promise.resolve(false); }
    if (st.cur && st.cur.phase > 0 && st.cur.phase < 4) { S.say('Finish this reading first (measure δ), then choose a new angle.'); return Promise.resolve(false); }
    if (S.hand.busy) return wait();
    if (!(i >= 30 && i <= 70)) { S.say('Choose i between 30° and 70°.'); return Promise.resolve(false); }
    if (S.rows.some(function (r) { return Math.abs(r.i - i) < 0.25; })) { S.say('You already have a reading at i = ' + i + '°. Choose another angle.'); return Promise.resolve(false); }
    clearReading();
    var g = geo(i); st.cur = { i: i, g: g, phase: 0 };
    return showProt(Q, Math.atan2(n1[1], n1[0])).then(function () {
      return pencilStroke([{ pts: [g.start, g.hit1], reading: true }], function () {
        words.push({ text: 'i = ' + i + '°', at: [g.hit1[0] - 0.05 * g.din[0] - 0.012, g.hit1[1] - 0.05 * g.din[1] + 0.01], size: 34, reading: true });
        st.cur.phase = 1; drawPaper(); S.say('Incident ray drawn at i = ' + i + '° to the normal. Now fix two pins on it.'); S.render(); });
    }).then(function () { return hideProt(); }).then(function () { return true; });
  }
  function movePin(idx, q) {
    var from = pins[idx].g.position.clone(), to = W(q, PY - 0.006), top = PIN_L + 0.002;
    function at(k) { var a = Math.min(1, k / 0.8), pos = from.clone().lerp(new T.Vector3(to.x, from.y, to.z), a); pos.y = from.y + (to.y - from.y) * (k < 0.8 ? 0 : (k - 0.8) / 0.2) + 0.05 * Math.sin(Math.PI * Math.min(1, k / 0.8)); return pos; }
    return S.hand.pinchMove(at(0).add(new T.Vector3(0, top, 0)), function (k) { return at(k).add(new T.Vector3(0, top, 0)); }, function (k) { placePin(idx, at(k)); }, { mode: 'top', ms: 900, reachMs: 550, hold: 120 })
      .then(function () { placePin(idx, to); pins[idx].at = q; marks.push(q); drawPaper(); });
  }
  function fixIncidentPins() {
    var c = st.cur; if (!c || c.phase < 1) { S.say('Draw the incident ray first.'); return Promise.resolve(false); }
    if (c.phase >= 2) return Promise.resolve(true); if (S.hand.busy) return wait();
    return movePin(0, c.g.P1).then(function () { return movePin(1, c.g.P2); }).then(function () {
      words.push({ text: 'P₁', at: [c.g.P1[0] - 0.008, c.g.P1[1] + 0.009], size: 34, reading: true }, { text: 'P₂', at: [c.g.P2[0] - 0.008, c.g.P2[1] + 0.009], size: 34, reading: true });
      c.phase = 2; drawPaper(); S.say('P1 and P2 are fixed upright on the incident ray.'); S.render(); return true; });
  }
  function fixEmergentPins() {
    var c = st.cur; if (!c || c.phase < 2) { S.say('Fix P1 and P2 first.'); return Promise.resolve(false); }
    if (c.phase >= 3) return Promise.resolve(true); if (S.hand.busy) return wait();
    if (c.g.tir) { S.say('Looking through face AC you cannot see P1 and P2 at all: the light is totally reflected inside the prism. Use a larger angle of incidence.'); return Promise.resolve(false); }
    S.focus('sight');
    return movePin(3, c.g.P4).then(function () { return movePin(2, c.g.P3); }).then(function () {
      words.push({ text: 'P₃', at: [c.g.P3[0] + 0.01, c.g.P3[1] + 0.008], size: 34, reading: true }, { text: 'P₄', at: [c.g.P4[0] + 0.01, c.g.P4[1] + 0.008], size: 34, reading: true });
      c.phase = 3; drawPaper(); S.say('P3 and P4 fixed: looking through face AC, P3, P4 and the images of P1, P2 are in one straight line.'); S.render(); return true; });
  }
  function showProt(at, arm) {            // arm = kernel direction of the protractor's 90° mark
    var to = W(at, PY + 0.0006), r1 = arm - Math.PI / 2;
    if (S.fast) { prot.position.copy(to); prot.rotation.y = r1; st.protOn = true; return Promise.resolve(); }
    var from = prot.position.clone(), r0 = prot.rotation.y;
    function pos(k) { var q = from.clone().lerp(to, k); q.y += 0.04 * Math.sin(Math.PI * k); return q; }
    var grabOff = new T.Vector3(0, 0.002, -0.03);
    return S.hand.pinchMove(pos(0).add(grabOff), function (k) { return pos(k).add(grabOff); }, function (k) { prot.position.copy(pos(k)); prot.rotation.y = r0 + (r1 - r0) * k; }, { mode: 'top', ms: 800, reachMs: 500, hold: 350 })
      .then(function () { prot.position.copy(to); prot.rotation.y = r1; st.protOn = true; });
  }
  function hideProt() {                 // the hand puts the protractor back beside the board
    if (!st.protOn) return Promise.resolve();
    var from = prot.position.clone(), r0 = prot.rotation.y, grabOff = new T.Vector3(0, 0.002, -0.03);
    function pos(k) { var q = from.clone().lerp(PROT_HOME, k); q.y += 0.04 * Math.sin(Math.PI * k); return q; }
    return S.hand.pinchMove(pos(0).add(grabOff), function (k) { return pos(k).add(grabOff); }, function (k) { prot.position.copy(pos(k)); prot.rotation.y = r0 + (PROT_HOME_ROT - r0) * k; }, { mode: 'top', ms: 700, reachMs: 450, hold: 100 })
      .then(function () { prot.position.copy(PROT_HOME); prot.rotation.y = PROT_HOME_ROT; st.protOn = false; }); }
  function measure() {
    var c = st.cur; if (!c || c.phase < 3) { S.say('Fix all four pins first.'); return Promise.resolve(false); }
    if (S.hand.busy) return wait();
    var g = c.g, ext = [g.O[0] + 0.05 * g.din[0], g.O[1] + 0.05 * g.din[1]], back = [g.O[0] - 0.0 * g.d2[0], g.O[1] - 0.0 * g.d2[1]];
    var d = half(g.v.dev / DEG), e = half(g.v.e / DEG);
    S.say('Lift the prism off its outline, then join the pins and produce the rays.');
    return movePrism(false).then(function () { return pencilStroke([{ pts: [g.P4, g.hit2], reading: true }, { pts: [g.hit1, g.hit2], reading: true, w: 2.5 }, { pts: [g.hit1, ext], dash: true, w: 2, reading: true }, { pts: [g.hit2, back], dash: true, w: 2, reading: true }]); })
      .then(function () { return showProt(g.O, Math.atan2(g.din[1], g.din[0]) - Math.PI / 2); })
      .then(function () {
        var a0 = Math.atan2(g.din[1], g.din[0]), a1 = Math.atan2(g.d2[1], g.d2[0]), arc = [];
        for (var j = 0; j <= 16; j++) { var a = a0 + (a1 - a0) * j / 16; arc.push([g.O[0] + 0.022 * Math.cos(a), g.O[1] + 0.022 * Math.sin(a)]); }
        strokes.push({ pts: arc, frac: 1, w: 2.5, reading: true, color: 'rgba(30,50,140,0.85)' });
        words.push({ text: 'δ = ' + d.toFixed(1) + '°', at: [g.O[0] + 0.045, g.O[1] - 0.01], size: 40, reading: true, color: 'rgba(30,50,140,0.92)' });
        drawPaper();
        S.addRow({ i: c.i, e: e, d: d });
        S.say('Measured with the protractor: δ = ' + d.toFixed(1) + '° (and e = ' + e.toFixed(1) + '°). Written in your record book.');
        return S.wait(900); })
      .then(function () { return hideProt(); }).then(function () { return movePrism(true); })
      .then(function () { c.phase = 4; S.render(); return true; });
  }
  function reading(i) { return drawIncident(i).then(function (ok) { return ok && fixIncidentPins(); }).then(function (ok) { return ok && fixEmergentPins(); }).then(function (ok) { return ok && measure(); }); }

  function uShape() { if (S.rows.length < 3) return false; var r = S.rows.slice().sort(function (a, b) { return a.i - b.i; }), m = 0;
    r.forEach(function (x, j) { if (x.d < r[m].d) m = j; }); return m > 0 && m < r.length - 1; }
  function nFrom(dm) { return Math.sin((A + dm * DEG) / 2) / Math.sin(A / 2); }
  function cubic(pts) {    // least-squares cubic through (i, δ) for the smooth graph line
    var n = 4, Mx = [], i, j, k2, X = function (x) { return (x - 50) / 10; };
    for (i = 0; i < n; i++) { Mx.push([]); for (j = 0; j <= n; j++) Mx[i].push(0); }
    pts.forEach(function (q) { var t = X(q[0]), pw = [1, t, t * t, t * t * t]; for (i = 0; i < n; i++) { for (j = 0; j < n; j++) Mx[i][j] += pw[i] * pw[j]; Mx[i][n] += pw[i] * q[1]; } });
    for (i = 0; i < n; i++) { var piv = i; for (k2 = i + 1; k2 < n; k2++) if (Math.abs(Mx[k2][i]) > Math.abs(Mx[piv][i])) piv = k2; var tmp = Mx[i]; Mx[i] = Mx[piv]; Mx[piv] = tmp;
      if (Math.abs(Mx[i][i]) < 1e-12) return null; for (k2 = 0; k2 < n; k2++) { if (k2 === i) continue; var f = Mx[k2][i] / Mx[i][i]; for (j = i; j <= n; j++) Mx[k2][j] -= f * Mx[i][j]; } }
    var c = Mx.map(function (r, ii) { return r[n] / r[ii]; });
    return function (x) { var t = X(x); return c[0] + c[1] * t + c[2] * t * t + c[3] * t * t * t; }; }
  function update() {
    var c = st.cur, i = c ? c.i : st.iSet, v = look(i);
    hudI.set(i.toFixed(1) + '°'); hudD.set(c && c.phase >= 4 ? half(v.dev / DEG).toFixed(1) + '°' : '—'); hudN.set(String(S.rows.length));
    if (st.rays && c) { var r = v.rays[0].p; rayLine.geometry.setFromPoints(r.map(function (q) { return W(q, PY + 0.012); })); rayLine.visible = true; } else rayLine.visible = false;
    var g = geo(i), at = g.hit2 ? W([g.hit2[0] + 0.30 * g.d2[0], g.hit2[1] + 0.30 * g.d2[1]], PY + 0.05) : W([0.2, -0.1], PY + 0.06), tg = W(g.hit1, PY + 0.02);
    VIEWS.sight[0][0] = at.x; VIEWS.sight[0][1] = at.y; VIEWS.sight[0][2] = at.z; VIEWS.sight[1][0] = tg.x; VIEWS.sight[1][1] = tg.y; VIEWS.sight[1][2] = tg.z;
  }

  var VIEWS = { board: [[PX - 0.02, 0.5, PZ + 0.38], [PX, 0.0, PZ - 0.01]], prism: [[PX + 0.05, 0.22, PZ + 0.24], [PX, 0.02, PZ - 0.02]],
    sight: [[0, 0, 0], [0, 0, 0]], pins: [[cushion.position.x + 0.1, 0.16, cushion.position.z + 0.18], [cushion.position.x, 0.02, cushion.position.z]],
    pencil: [[PX + 0.2, 0.2, PZ + 0.32], [PX + 0.18, 0.0, PZ + 0.13]], prot: [[PROT_HOME.x + 0.05, 0.22, PROT_HOME.z + 0.2], [PROT_HOME.x, 0, PROT_HOME.z]],
    book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] };
  drawPaper(); update();
  if (document.fonts && document.fonts.load) document.fonts.load('40px "Caveat"').then(function () { drawPaper(); }).catch(function () {});

  return {
    camera: { pos: [0.36, 0.6, 0.76], look: [0.3, 0.0, -0.2] },
    views: VIEWS,
    book: { title: 'Expt. — Prism: δ against i', lines: ['Aim: find δm and n of the prism glass.', 'Angle of prism A = 60°', 'i: protractor at the normal at Q', 'δ: between incident ray produced and', '      the emergent ray (protractor)', 'n = sin((A + δm)/2) / sin(A/2)'],
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'i (°)', get: function (r) { return r.i.toFixed(1); } },
        { label: 'e (°)', get: function (r) { return r.e.toFixed(1); } }, { label: 'δ (°)', get: function (r) { return r.d.toFixed(1); } }] },
    theory: { principle: 'A ray passing through a prism is bent twice, both times towards the base. The total deviation δ first falls as the angle of incidence i grows, reaches a least value δm, then rises again. At δm the ray inside the prism runs parallel to the base and i = e.',
      formula: 'n = sin((A + δm)/2) / sin(A/2)', formulaNote: 'A = angle of the prism (60°) · δm = angle of minimum deviation · also i + e = A + δ',
      more: ['You will draw the ray for one angle of incidence at a time: two pins on the incident ray, two pins sighted through the prism on the emergent ray, then δ measured with a protractor. A graph of δ against i is a U-shaped curve; its lowest point gives δm.'],
      precautions: 'Keep the pins upright and at least 6 cm apart. Look at the feet of the pins, not their heads, when lining them up. Draw thin pencil lines. Take extra readings close to the lowest point of the curve. Do not let the prism move between readings.' },
    graph: { x: function (r) { return r.i; }, y: function (r) { return r.d; }, xlabel: 'i (°)', ylabel: 'δ (°)', x0: 30, y0: 30, x1: 70, line: function (pts) { return pts.length >= 4 ? cubic(pts) : null; } },
    result: function (rows) { if (rows.length < 3) return null; var dm = Math.min.apply(null, rows.map(function (r) { return r.d; }));
      return { label: 'n', value: nFrom(dm), unit: '', digits: 3, truth: p.n, note: 'δm = ' + dm.toFixed(1) + '° from the lowest point of the δ–i curve; A = 60°.' }; },
    tol: 0.01,
    chips: ['Why does δ first fall and then rise?', 'Why is i = e at minimum deviation?', 'How do I line up the pins?', 'Check my readings', 'Why can I not see the pins at small i?'],
    viva: [['At minimum deviation, the ray inside the prism is…', ['parallel to the base', 'perpendicular to the base', 'along the normal'], 0, 'The path is symmetric, so the ray inside runs parallel to the base.'],
      ['Why do we look at the feet of the pins when lining them up?', ['The heads may be tilted; the feet mark the true points on the ray', 'The feet are brighter', 'It reduces glare'], 0, 'Only where the pins enter the paper are they exactly on the drawn line.']],
    askState: function () { var c = st.cur, v = look(c ? c.i : st.iSet); return { prism_angle_deg: 60, prism_on_paper: st.placed, outline_traced: st.traced, angle_of_incidence_deg: c ? c.i : st.iSet,
      pins_fixed: c ? Math.min(4, c.phase >= 3 ? 4 : c.phase >= 2 ? 2 : 0) : 0, deviation_deg: c && c.phase >= 4 ? half(v.dev / DEG) : null, light_totally_reflected: !!v.tir, readings: S.rows.length }; },

    steps: [
      { id: 'setup', title: 'Set up', view: 'board', render: function (u) {
          u.h2('Pin the paper, place and trace the prism');
          u.p('A white sheet is pinned on the drawing board. Stand the prism on it with its base towards you, trace its outline ABC with a sharp pencil, and draw the normal NQ at the middle of face AB.');
          u.task('1. Place the prism on the paper', st.placed, st.placed ? 'Placed, base BC towards you' : 'Not done yet')
            .add(u.button(st.placed ? 'Placed' : 'Place the prism', function () { placePrism(); }, !st.placed, st.placed || S.hand.busy));
          u.task('2. Trace the outline and draw the normal at Q', st.traced, st.traced ? 'Outline ABC and normal NQ drawn' : 'Keep the prism still while you trace')
            .add(u.button(st.traced ? 'Traced' : 'Trace with the pencil', function () { traceOutline(); }, !st.traced && st.placed, st.traced || !st.placed || S.hand.busy));
          u.note('Do not move the prism or the paper after tracing: every reading uses the same outline.');
          u.next('Next: trace the rays', st.traced);
        },
        ok: function () { return st.traced; },
        auto: function () { return placePrism().then(function () { return traceOutline(); }); } },
      { id: 'rays', title: 'Trace the rays', view: 'board', render: function (u) {
          var c = st.cur, ph = c ? c.phase : 0;
          u.h2('Trace the ray, measure δ');
          u.p('For each angle of incidence: draw the incident ray, fix pins P1 and P2 on it, look through face AC and fix P3 and P4 in line with the images of P1 and P2, then join them and measure the deviation δ.');
          u.slider('Angle of incidence i (protractor)', 30, 70, 1, function () { return st.iSet; }, function (x) { st.iSet = x; if (!st.cur || st.cur.phase >= 4) update(); }, '°', 0);
          u.task('1. Draw the incident ray at i = ' + (c && ph < 4 ? c.i : st.iSet) + '°', ph >= 1 && ph < 4, ph >= 1 && ph < 4 ? 'Drawn' : 'Protractor on the normal at Q')
            .add(u.button('Draw the incident ray', function () { drawIncident(st.iSet); }, ph === 0 || ph >= 4, S.hand.busy || (ph >= 1 && ph < 4)));
          u.task('2. Fix pins P1 and P2', ph >= 2 && ph < 4, ph >= 2 && ph < 4 ? 'Fixed upright on the incident ray' : 'Two pins, about 5 cm apart')
            .add(u.button('Fix P1 and P2', function () { fixIncidentPins(); }, ph === 1, S.hand.busy || ph !== 1));
          u.task('3. Sight through face AC, fix P3 and P4', ph >= 3 && ph < 4, ph >= 3 && ph < 4 ? 'All four in one line' : 'Eye at the level of the paper')
            .add(u.button('Look through the prism, fix P3 and P4', function () { fixEmergentPins(); }, ph === 2, S.hand.busy || ph !== 2));
          u.task('4. Join the pins and measure δ', ph >= 4, ph >= 4 ? 'δ = ' + S.rows[S.rows.length - 1].d.toFixed(1) + '° recorded' : 'Produce the incident ray; protractor at the meeting point')
            .add(u.button('Measure δ and record', function () { measure(); }, ph === 3, S.hand.busy || ph !== 3));
          u.row(u.button(st.rays ? 'Hide the light ray' : 'Show the light ray', function () { st.rays = !st.rays; update(); S.render(); }), u.button('Look at the board', function () { S.focus('board'); }));
          u.h3('Observation table'); u.table();
          var okU = uShape();
          u.next('Next: graph and result', S.rows.length >= 6 && okU);
          if (S.rows.length < 6) u.p(S.rows.length + ' of at least 6 angles recorded. Take some close to the lowest δ.');
          else if (!okU) u.note('Your smallest δ is at one end of your range. Take readings on both sides of it so the lowest point of the curve is clear.');
        },
        ok: function () { return S.rows.length >= 6 && uShape(); },
        auto: function () {
          return [35, 40, 45, 48, 50, 52, 55, 60, 65].reduce(function (pr, i) { return pr.then(function () { st.iSet = i; return reading(i); }); }, Promise.resolve())
            .then(function () { S.render(); }); } },
    ],

    tick: function () { update(); },
  };
});
