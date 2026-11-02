/* Prayogshala studio module: Inclined plane and friction (NCERT Class XI).
   A hinged wooden plank on a base board with a clear acrylic angle quadrant and a wing-nut clamp; a wooden block with a
   hook rests against a stop at the lower end; a thread from the hook runs over a pulley at the top end to a scale pan.
   The gloved hand lifts the plank to the angle, then puts weights from a weight box into the pan one at a time until
   the block just starts to slide up. Physics: the incline kernel from kernels.js decides when and how the block moves. */
HoolaStudio.define('inclined-plane-friction', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.incline, DEG = Math.PI / 180;
  function hidden(id, dflt) { var k = (S.lab.knobs || []).filter(function (q) { return q.id === id; })[0]; return k ? k.value * (k.k || 1) : dflt; }
  var p = window.HoolaKernels.paramsFor('incline', S.lab.params);
  p.mu = hidden('mu', 0.3); p.m = 0.5; p.F = 0;            // a 500 g wooden block (weighed on a balance: given)
  var PAN = 50, SET = [200, 100, 100, 50, 20, 20, 10, 5, 2, 2, 1];   // pan 50 g + a standard 1–200 g weight box
  var st = { deg: 15, clamped: true, moved: false, movedLoad: null, held: false };
  p.angle = st.deg * DEG;
  var sim = K.init(p); sim.s = 0; sim.v = 0; sim.a = 0;

  // ---------- geometry
  var BT = 0.025, HX = -0.3, PL = 0.8, PT = 0.018, PW = 0.16, BL = 0.1, BH = 0.06, BW = 0.08, XS = 0.04 + BL / 2;
  var PR = 0.02, PCX = PL + 0.03, PCY = PT + BH / 2 - PR, LH0 = 0.1, THR = 0.07, QZ = 0.094, QR = 0.295;
  function loadG() { var g = PAN; W.forEach(function (w) { if (w.inPan) g += w.g; }); return g; }
  function pulleyC(th) { th = th === undefined ? p.angle : th; return new T.Vector3(HX + PCX * Math.cos(th) - PCY * Math.sin(th), BT + PCX * Math.sin(th) + PCY * Math.cos(th), 0); }
  function travel(th) { return Math.max(0.01, Math.min(pulleyC(th).y - LH0 - 0.076, PCX - (XS + BL / 2 + 0.008) - 0.1)); }
  p.len = travel();

  var board = S.rounded(0.62, 0.26, BT, 0.01, M.darkWood); board.rotation.x = -Math.PI / 2; board.position.set(HX + 0.25, BT / 2, 0); S.scene.add(board);
  S.contact(0.72, 0.36, HX + 0.25, 0, 0.55);
  var hinge = new T.Group(); S.scene.add(hinge);
  [-0.06, 0.06].forEach(function (z) { var h = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.05, 16), M.brass); h.rotation.x = Math.PI / 2; h.position.set(HX, BT + 0.004, z); hinge.add(h);
    var lf = S.mesh(new T.BoxGeometry(0.03, 0.0015, 0.05), M.brass); lf.position.set(HX - 0.016, BT + 0.0008, z); hinge.add(lf); });
  var plank = new T.Group(); plank.position.set(HX, BT, 0); S.scene.add(plank);
  var pm = S.rounded(PL, PT, PW, 0.004, M.wood); pm.position.set(PL / 2, PT / 2, 0); plank.add(pm);
  var face = S.mesh(new T.BoxGeometry(PL - 0.06, 0.0008, PW - 0.02), new T.MeshStandardMaterial({ color: 0xc9a46a, roughness: 0.75 })); face.position.set(PL / 2 + 0.02, PT + 0.0003, 0); plank.add(face);
  var stop = S.rounded(0.02, 0.03, PW - 0.02, 0.003, M.darkWood); stop.position.set(0.03, PT + 0.015, 0); plank.add(stop);
  var idx = S.mesh(new T.BoxGeometry(0.003, PT * 0.8, 0.0015), M.red); idx.position.set(QR, PT / 2, PW / 2 + 0.0008); plank.add(idx);
  // pulley at the top end, on a bracket
  var pul = new T.Group(); pul.position.set(PCX, PCY, 0); plank.add(pul);
  var wheel = S.mesh(new T.CylinderGeometry(PR, PR, 0.008, 40), M.alu); wheel.rotation.x = Math.PI / 2; pul.add(wheel);
  var groove = S.mesh(new T.TorusGeometry(PR, 0.0028, 10, 40), M.black); pul.add(groove);
  var axle = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.034, 12), M.chrome); axle.rotation.x = Math.PI / 2; pul.add(axle);
  [-0.016, 0.016].forEach(function (z) { var ch = S.mesh(new T.BoxGeometry(0.05, 0.034, 0.003), M.iron); ch.position.set(-0.012, -0.004, z); pul.add(ch); });
  var brk = S.mesh(new T.BoxGeometry(0.05, 0.004, 0.04), M.iron); brk.position.set(PL - 0.012, PT + 0.002, 0); plank.add(brk);
  // the block with its hook
  var block = new T.Group(); plank.add(block);
  var bm = S.rounded(BL, BH, BW, 0.006, new T.MeshStandardMaterial({ map: S.woodTex, color: 0xb98a58, roughness: 0.6 })); bm.position.y = BH / 2; block.add(bm);
  var bl = S.label('500 g', { w: 0.04, ratio: 0.3, color: '#3a2410' }); bl.position.set(0, BH / 2, BW / 2 + 0.0008); block.add(bl);
  var eye = S.mesh(new T.TorusGeometry(0.004, 0.0012, 8, 20), M.brass); eye.position.set(BL / 2 + 0.005, BH / 2, 0); block.add(eye);
  var eyeS = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, 0.006, 8), M.brass); eyeS.rotation.z = Math.PI / 2; eyeS.position.set(BL / 2 + 0.001, BH / 2, 0); block.add(eyeS);
  var blockShadow = new T.Mesh(new T.PlaneGeometry(BL * 1.25, BW * 1.3), new T.MeshBasicMaterial({ transparent: true, opacity: 0.45, depthWrite: false, map: (function () { var c = S.contact(0.01, 0.01, 0, -5, 0); c.visible = false; return c.material.map; })() }));
  blockShadow.rotation.x = -Math.PI / 2; blockShadow.position.set(0, PT + 0.0012, 0); blockShadow.renderOrder = 1; block.add(blockShadow);
  // the clear acrylic angle quadrant with its wing-nut clamp
  var qTex = S.canvasTex(1024, 1024, function (x, w) { var c = w / 2, sc = c / 0.33;
    x.fillStyle = 'rgba(230,242,255,0.22)'; x.beginPath(); x.arc(c, c, 0.33 * sc, -42 * DEG, 0); x.arc(c, c, 0.255 * sc, 0, -42 * DEG, true); x.closePath(); x.fill();
    x.strokeStyle = 'rgba(12,30,60,.95)'; x.fillStyle = 'rgba(12,30,60,.95)'; x.font = '600 20px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
    for (var d = 0; d <= 40; d++) { var a = -d * DEG, L = d % 5 === 0 ? 0.022 : 0.012; x.lineWidth = d % 5 === 0 ? 2.6 : 1.4;
      x.beginPath(); x.moveTo(c + Math.cos(a) * 0.326 * sc, c + Math.sin(a) * 0.326 * sc); x.lineTo(c + Math.cos(a) * (0.326 - L) * sc, c + Math.sin(a) * (0.326 - L) * sc); x.stroke();
      if (d % 5 === 0) { x.save(); x.translate(c + Math.cos(a) * 0.29 * sc, c + Math.sin(a) * 0.29 * sc); x.rotate(a + Math.PI / 2); x.fillText(d + '°', 0, 0); x.restore(); } }
    x.lineWidth = 1.2; x.beginPath(); x.arc(c, c, 0.268 * sc, -40 * DEG, 0); x.stroke(); });
  var quad = new T.Group(); quad.position.set(HX, BT, QZ); S.scene.add(quad);
  var qp = new T.Mesh(new T.RingGeometry(0.255, 0.33, 96, 1, 0, 42 * DEG), new T.MeshStandardMaterial({ map: qTex, transparent: true, roughness: 0.08, side: T.DoubleSide, depthWrite: false }));
  qp.renderOrder = 3; quad.add(qp);
  var qRim = S.mesh(new T.TorusGeometry(0.33, 0.0018, 6, 96, 42 * DEG), new T.MeshPhysicalMaterial({ color: 0xdfeefa, roughness: 0.05, transparent: true, opacity: 0.6 })); quad.add(qRim);
  var qFoot = S.rounded(0.09, 0.012, 0.03, 0.003, M.alu); qFoot.position.set(0.292, 0.006, -0.004); quad.add(qFoot);
  var qPost = S.mesh(new T.BoxGeometry(0.004, 0.004, 0.02), M.alu); qPost.position.set(0.29, 0.012, -0.012); quad.add(qPost);
  var wing = new T.Group(); quad.add(wing);
  var wn = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.008, 6), M.chrome); wn.rotation.x = Math.PI / 2; wn.position.z = 0.006; wing.add(wn);
  [-1, 1].forEach(function (sg) { var f = S.rounded(0.012, 0.016, 0.002, 0.004, M.chrome); f.position.set(sg * 0.01, 0.002, 0.008); wing.add(f); });
  // thread: block hook -> over the pulley -> down to the pan
  var thM = new T.MeshStandardMaterial({ color: 0xf0ece0, roughness: 0.9 });
  function segM() { var m = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 1, 6), thM, true, false); S.scene.add(m); return m; }
  var th1 = segM(), th2 = segM(), wrap = S.mesh(new T.TorusGeometry(PR + 0.0005, 0.0007, 6, 24, 1), thM, false, false); S.scene.add(wrap);
  var up = new T.Vector3(0, 1, 0);
  function seg(m, a, b) { var d = b.clone().sub(a); m.position.copy(a).add(b).multiplyScalar(0.5); m.scale.set(1, Math.max(1e-4, d.length()), 1); m.quaternion.setFromUnitVectors(up, d.normalize()); }
  // scale pan: ring, three threads, brass dish
  var pan = new T.Group(); S.scene.add(pan);
  var ring = S.mesh(new T.TorusGeometry(0.006, 0.0014, 8, 20), M.brass); pan.add(ring);
  var dish = S.mesh(new T.LatheGeometry([[0, 0], [0.045, 0.0], [0.05, 0.008], [0.0505, 0.0085], [0.046, 0.0012], [0, 0.0012]].map(function (q) { return new T.Vector2(q[0], q[1]); }), 48), M.brass);
  dish.position.y = -THR - 0.006; pan.add(dish);
  [0, 2.094, 4.189].forEach(function (a) { var m = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 1, 5), thM, true, false); seg(m, new T.Vector3(0, -0.004, 0), new T.Vector3(Math.cos(a) * 0.047, -THR - 0.006 + 0.008, Math.sin(a) * 0.047)); pan.add(m); });
  var panShadow = S.contact(0.13, 0.13, 0, 0, 0.3);
  // the weight box and its brass weights
  var BOX = new T.Vector3(0.8, 0, 0.06);
  var box = new T.Group(); box.position.copy(BOX); S.scene.add(box);
  var bxb = S.rounded(0.26, 0.11, 0.028, 0.006, M.darkWood); bxb.rotation.x = -Math.PI / 2; bxb.position.y = 0.014; box.add(bxb);
  var lid = S.rounded(0.26, 0.11, 0.012, 0.006, M.darkWood); lid.rotation.x = -Math.PI / 2; lid.rotation.z = 0; lid.position.set(0, 0.006, -0.125); box.add(lid);
  var lidLbl = S.label('WEIGHT BOX  1 g – 200 g', { w: 0.15, ratio: 0.12, color: '#f1e3c0' }); lidLbl.rotation.x = -Math.PI / 2; lidLbl.position.set(0, 0.0125, -0.125); box.add(lidLbl);
  var felt = S.mesh(new T.BoxGeometry(0.24, 0.001, 0.09), new T.MeshStandardMaterial({ color: 0x2c4f3a, roughness: 1 })); felt.position.y = 0.0285; box.add(felt);
  S.contact(0.32, 0.3, BOX.x, BOX.z - 0.06, 0.5);
  var ringSlots = [[0, 0]].concat([0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(function (i) { var a = i * 36 * DEG; return [Math.cos(a) * 0.033, Math.sin(a) * 0.033]; }));
  var panSlotOf = [0, 1, 3, 5, 2, 4, 7, 6, 8, 10, 9];   // 200 in the centre; big and small alternate round the ring
  var boxXZ = [[-0.095, -0.02], [-0.06, -0.025], [-0.03, -0.025], [-0.0, -0.025], [0.025, -0.025], [0.05, -0.025], [0.072, -0.025], [0.092, -0.025], [0.06, 0.02], [0.08, 0.02], [0.1, 0.02]];
  var W = SET.map(function (g, i) {
    var d = Math.pow(4 * (g / 8.5) / (Math.PI * 1.3), 1 / 3) / 100, h = d * 1.3, gp = new T.Group();
    var body = S.mesh(new T.CylinderGeometry(d / 2, d / 2, h * 0.8, 28), M.brass); body.position.y = h * 0.4; gp.add(body);
    var neck = S.mesh(new T.CylinderGeometry(d * 0.18, d * 0.22, h * 0.12, 16), M.brass); neck.position.y = h * 0.86; gp.add(neck);
    var knob = S.mesh(new T.SphereGeometry(d * 0.3, 16, 12), M.brass); knob.position.y = h * 0.92 + d * 0.22; gp.add(knob);
    var lb = S.label(String(g), { w: d * 0.9, ratio: 0.45, color: '#4a3208' }); lb.rotation.x = -Math.PI / 2; lb.position.y = h * 0.8 + 0.0003; lb.scale.set(0.6, 0.6, 1); if (g >= 20) gp.add(lb);
    var top = h * 0.92 + d * 0.5;
    var home = new T.Vector3(BOX.x + boxXZ[i][0], 0.0285, BOX.z + boxXZ[i][1]);
    gp.position.copy(home); S.scene.add(gp);
    return { g: g, i: i, grp: gp, top: top, home: home, inPan: false, slot: ringSlots[panSlotOf[i]] };
  });
  var inPan = [];   // order the weights went into the pan

  S.addApparatus('plank', plank, 'Inclined plane', 'A smooth wooden plank hinged to a base board. Lift its upper end to set the angle θ.');
  S.addApparatus('quad', quad, 'Angle quadrant with clamp', 'A clear acrylic scale marked in degrees. The wing nut clamps the plank at the angle you set.');
  S.addApparatus('block', block, 'Wooden block (500 g)', 'Mass m = 500 g, weighed on a balance. A hook on its upper face takes the thread.');
  S.addApparatus('pulley', pul, 'Pulley', 'A light, smooth pulley at the top of the plank, so the thread pulls the block straight up the slope.');
  S.addApparatus('pan', pan, 'Scale pan (50 g)', 'The pan itself is 50 g. Its weight and the weights in it pull the block up the plane.');
  S.addApparatus('box', box, 'Weight box', 'Brass weights 200, 100, 100, 50, 20, 20, 10, 5, 2, 2 and 1 g. Lift them by the knob.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard('Angle θ'), hudL = S.hudCard('Load (pan + weights)'), hudB = S.hudCard('Block');

  // ---------- helpers
  function along(pts) { var L = [0]; for (var i = 1; i < pts.length; i++) L.push(L[i - 1] + pts[i].distanceTo(pts[i - 1]));
    return function (k) { var d = Math.max(0, Math.min(1, k)) * L[L.length - 1]; for (var i = 1; i < pts.length; i++) if (d <= L[i] || i === pts.length - 1) { var f = (d - L[i - 1]) / Math.max(1e-9, L[i] - L[i - 1]); return pts[i - 1].clone().lerp(pts[i], Math.min(1, f)); } }; }
  function local(x, y, z) { plank.updateMatrixWorld(true); return plank.localToWorld(new T.Vector3(x, y, z)); }
  function panPos() { var C = pulleyC(); return new T.Vector3(C.x + PR, C.y - LH0 - sim.s, 0); }
  function slotWorld(w) { var pp = panPos(); return new T.Vector3(pp.x + w.slot[0], pp.y - THR - 0.006 + 0.0012, pp.z + w.slot[1]); }
  function moving() { return sim.v !== 0; }
  function atBottom() { return sim.s < 1e-6 && sim.v === 0; }

  function setAngle(deg) {
    if (S.hand.busy) return Promise.resolve();
    deg = Math.round(deg);
    if (deg < 15 || deg > 35) { S.say('Use an angle from 15° to 35°. Below 15° the pan has no room to fall; above 35° the block may tip over.'); return Promise.resolve(); }
    if (inPan.length) { S.say('Take the weights off the pan before you change the angle.'); return Promise.resolve(); }
    if (!atBottom()) { S.say('Bring the block back down to the stop first.'); return Promise.resolve(); }
    var a0 = p.angle, a1 = deg * DEG; st.clamped = false; st.held = true;
    function apply(k) { p.angle = a0 + (a1 - a0) * k; st.deg = Math.round(p.angle / DEG * 10) / 10; sim.s = 0; sim.v = 0; pose(); }
    function grip(a) { var c = Math.cos(a), s = Math.sin(a), lx = PL - 0.07, ly = PT; return new T.Vector3(HX + lx * c - ly * s, BT + lx * s + ly * c, PW / 2 - 0.01); }
    return S.hand.pinchMove(grip(a0), function (k) { return grip(a0 + (a1 - a0) * k); }, apply, { ms: 1300, pose: 'grip' })
      .then(function () { p.angle = a1; st.deg = deg; p.len = travel(); pose(); return S.hand.tap(wing, 'front'); })
      .then(function () { st.held = false; st.clamped = true; st.moved = false; st.movedLoad = null; S.render(); S.say('The plank is clamped at θ = ' + deg + '°.'); });
  }
  function addWeight(i) {
    var w = W[i];
    if (S.hand.busy || !w || w.inPan) return Promise.resolve();
    if (!st.clamped) { S.say('Clamp the plank first.'); return Promise.resolve(); }
    if (st.moved) { S.say('The block has already moved. Take off the last weight and bring the block back down first.'); return Promise.resolve(); }
    var from = w.home.clone(), to = slotWorld(w), G = new T.Vector3(0, w.top - 0.002, 0);
    var path = along([from, from.clone().setY(0.13), to.clone().setY(to.y + 0.08), to.clone().setY(to.y + 0.004), to]);
    return S.hand.pinchMove(from.clone().add(G), function (k) { return path(k).add(G); }, function (k) { w.grp.position.copy(path(k)); }, { ms: 1500 })
      .then(function () { w.inPan = true; inPan.push(w); p.F = loadG() / 1000 * p.g; S.render(); });
  }
  function removeWeight(i) {
    var w = W[i];
    if (S.hand.busy || !w || !w.inPan) return Promise.resolve();
    var taken = false, path = null, G = new T.Vector3(0, w.top - 0.002, 0);
    return S.hand.pinchMove(slotWorld(w).add(G), function (k) { return (path ? path(k) : slotWorld(w)).add(G); }, function (k) {
      if (!taken) { taken = true; w.inPan = false; inPan.splice(inPan.indexOf(w), 1); p.F = loadG() / 1000 * p.g;
        var f = w.grp.position.clone(); path = along([f, f.clone().setY(f.y + 0.06), w.home.clone().setY(0.13), w.home]); }
      w.grp.position.copy(path(k)); }, { ms: 1300 })
      .then(function () { S.render(); });
  }
  function removeLast() { if (!inPan.length) { S.say('The pan is empty.'); return Promise.resolve(); } return removeWeight(inPan[inPan.length - 1].i); }
  function emptyPan() { var pr = Promise.resolve(); inPan.slice().reverse().forEach(function (w) { pr = pr.then(function () { return removeWeight(w.i); }); }); return pr; }
  function resetBlock() {
    if (S.hand.busy) return Promise.resolve();
    if (atBottom()) { st.moved = false; st.movedLoad = null; return Promise.resolve(); }
    var s0 = sim.s; st.held = true;
    function grip(s) { return local(XS + s, PT + BH + 0.002, 0); }
    return S.hand.pinchMove(grip(s0), function (k) { return grip(s0 * (1 - k)); }, function (k) { sim.s = s0 * (1 - k); sim.v = 0; sim.a = 0; pose(); }, { ms: 1100, mode: 'top', pose: 'grip' })
      .then(function () { sim.s = 0; sim.v = 0; st.held = false; st.moved = false; st.movedLoad = null; S.render(); });
  }
  function record() {
    if (S.hand.busy) return;
    if (!st.moved) { S.say('The block has not moved yet. Add weights until it just starts to slide up, then record.'); return; }
    if (st.movedLoad !== loadG()) { S.say('Record the load with which the block just started to move: put back the weights that were in the pan then.'); return; }
    if (S.rows.some(function (r) { return r.deg === st.deg; })) { S.say('You already have a reading at ' + st.deg + '°. Change the angle for the next one.'); return; }
    var L = st.movedLoad, th = st.deg * DEG, F = L / 1000 * p.g;
    S.addRow({ deg: st.deg, angle: th, L: L, F: F, R: p.m * p.g * Math.cos(th), f: F - p.m * p.g * Math.sin(th) });
    S.say('Written in your record book: θ = ' + st.deg + '°, least load = ' + L + ' g.');
  }
  // auto: the standard weighing order - try each weight from the largest down, keep it only if the block stays at rest
  function moves() { return S.advance(1.5, function () { return st.moved; }); }
  function greedyRep(g) { var out = []; SET.forEach(function (v, i) { if (v <= g) { out.push(i); g -= v; } }); return out; }
  function findLeast() {
    var pr = Promise.resolve();
    SET.forEach(function (v, i) { pr = pr.then(function () { return addWeight(i); }).then(function () { moves(); if (st.moved) return removeWeight(i).then(resetBlock); }); });
    return pr.then(function () {   // now the pan holds the most that does not move it: go up by 1 g
      var want = greedyRep(loadG() - PAN + 1), have = inPan.map(function (w) { return w.i; }), q = Promise.resolve();
      have.filter(function (i) { return want.indexOf(i) < 0; }).forEach(function (i) { q = q.then(function () { return removeWeight(i); }); });
      want.filter(function (i) { return have.indexOf(i) < 0; }).forEach(function (i) { q = q.then(function () { return addWeight(i); }); });
      return q.then(function () { moves(); record(); });
    });
  }

  var EXP = {
    camera: { pos: [0.55, 0.74, 1.7], look: [0.3, 0.15, -0.02] },
    views: { plank: [[0.2, 0.5, 1.1], [0.05, 0.15, 0]], quad: [[-0.05, 0.28, 0.62], [-0.08, 0.12, 0.09]], block: [[0.05, 0.3, 0.55], [-0.15, 0.1, 0]],
      pulley: [[0.75, 0.42, 0.5], [0.45, 0.28, 0]], pan: [[0.8, 0.35, 0.65], [0.5, 0.18, 0]], box: [[0.95, 0.32, 0.45], [0.78, 0.02, 0.04]],
      angle: [[0.32, 0.5, 1.2], [0.1, 0.17, 0.02]], load: [[0.78, 0.48, 0.92], [0.46, 0.17, 0.0]],
      book: [[-0.56, 0.44, 0.5], [-0.66, 0.0, 0.06]] },
    theory: { principle: 'A block on an inclined plane is pulled up the slope by a thread over a pulley. It starts to move when the pull just exceeds the component of its weight down the slope plus the limiting friction μ R, where R = mg cos θ.',
      formula: 'F = mg (sin θ + μ cos θ)', formulaNote: 'so μ = (F − mg sin θ) / (mg cos θ) · F = least load × g',
      more: ['The least load includes the pan (50 g). In this lab the static and kinetic friction coefficients are taken as the same μ. A graph of limiting friction (F − mg sin θ) against normal reaction (mg cos θ) is a straight line through the origin with slope μ.'],
      precautions: 'Keep the plank and the block clean and dry. Keep the thread parallel to the plank. Add weights gently, the smallest last, and bring the block back to the same starting place each time.' },
    book: { at: [-0.66, 0.06, 0.1], title: 'Expt. — Friction on an inclined plane', lines: ['Aim: to find μ between the block and the plank.', 'Block m = 500 g, pan = 50 g, g = 9.8 m/s²', 'F = least load × g', 'μ = (F − mg sinθ) / (mg cosθ)', 'Precautions: thread parallel to plank, add weights gently.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'θ (°)', get: function (r) { return String(r.deg); } },
        { label: 'Load (g)', get: function (r) { return String(r.L); } }, { label: 'F (N)', get: function (r) { return r.F.toFixed(3); } },
        { label: 'μ', get: function (r) { return (r.f / r.R).toFixed(3); } }] },
    graph: { x: function (r) { return r.R; }, y: function (r) { return r.f; }, xlabel: 'Normal reaction R = mg cos θ (N)', ylabel: 'Friction F − mg sin θ (N)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) { if (rows.length < 2) return null;
      return { label: 'μ', value: S.fit.mean(rows.map(function (r) { return r.f / r.R; })), unit: '', digits: 3, truth: p.mu, note: 'Mean of μ = (F − mg sin θ) / (mg cos θ) over your angles.' }; },
    tol: 0.02,
    chips: ['Why does the pan mass count in the load?', 'What is limiting friction?', 'Why add the smallest weights last?', 'Check my readings', 'Why does a bigger angle need more load?'],
    viva: [['Why is the pan\'s own mass added to the load?', ['The pan pulls on the thread too', 'To make the numbers bigger', 'It does not matter'], 0, 'The thread carries the weight of the pan and everything in it.'],
      ['Does μ depend on the angle of the plane?', ['No, it depends on the two surfaces', 'Yes, it grows with the angle', 'Yes, it falls with the angle'], 0, 'μ is a property of the pair of surfaces; F changes with θ, μ does not.']],
    askState: function () { return { angle_deg: st.deg, plank_clamped: st.clamped, load_in_pan_g: loadG(), weights_in_pan_g: inPan.map(function (w) { return w.g; }),
      block_moving: moving(), block_has_moved: st.moved, load_when_it_moved_g: st.movedLoad, block_mass_g: 500, pan_mass_g: PAN }; },

    steps: [
      { id: 'angle', title: 'Set the angle', view: 'angle', render: function (u) {
          u.h2('Set the angle of the plane');
          u.p('The hand lifts the upper end of the plank to the angle you choose and tightens the wing nut. Read the angle on the quadrant.');
          var tgt = st.deg;
          u.slider('Angle θ', 15, 35, 1, function () { return Math.round(st.deg); }, function (v) { tgt = v; }, '°', 0);
          u.row(u.button('Lift and clamp the plank', function () { setAngle(tgt); }, true, S.hand.busy));
          u.live(function () { return 'θ = ' + st.deg.toFixed(0) + '° · ' + (st.clamped ? 'clamped' : 'not clamped'); });
          if (inPan.length || !atBottom()) u.row(u.button('Take all weights off', function () { emptyPan(); }, false, S.hand.busy || !inPan.length), u.button('Bring the block back', function () { resetBlock(); }, false, S.hand.busy || atBottom()));
          u.note('Start at 20°. The block rests against the stop at the lower end of the plank.');
          u.next('Next: add weights', st.clamped && !S.hand.busy);
        },
        ok: function () { return st.clamped; },
        auto: function () { return setAngle(20); } },
      { id: 'load', title: 'Load the pan', view: 'load', render: function (u) {
          u.h2('Add weights until the block just moves');
          u.p('Take weights from the box with the hand and put them in the pan, largest first. If the block moves, take the last weight off, bring the block back and try a smaller one. Record the least load that just starts the block moving up.');
          var r = u.row(); W.forEach(function (w) { if (!w.inPan) r.appendChild(u.button('+' + w.g + ' g', function () { addWeight(w.i); }, false, S.hand.busy || st.moved)); });
          u.row(u.button('Take off the last weight', function () { removeLast(); }, false, S.hand.busy || !inPan.length),
            u.button('Bring the block back', function () { resetBlock(); }, false, S.hand.busy || atBottom()));
          u.live(function () { return 'θ = ' + st.deg.toFixed(0) + '° · load ' + loadG() + ' g · block ' + (moving() ? 'sliding up' : st.moved ? 'has moved (with ' + st.movedLoad + ' g)' : 'at rest'); });
          u.row(u.button('Record the least load', function () { record(); }, true, S.hand.busy || !st.moved));
          u.h3('Observation table'); u.table();
          u.row(u.button('Change the angle for the next reading', function () { S.go(1); }));
          u.next('Next: result', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of 3 angles recorded (try 20°, 25° and 30°).');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () { return findLeast().then(function () { return [25, 30].reduce(function (pr, d) { return pr.then(function () { return emptyPan(); }).then(resetBlock)
          .then(function () { return setAngle(d); }).then(findLeast); }, Promise.resolve()); }); } },
    ],

    tick: function (dt) {
      if (!st.held) { K.step(sim, p, dt);
        if (!st.moved && (sim.v !== 0 || sim.s > 1e-6)) { st.moved = true; st.movedLoad = loadG(); if (!S.fast) { S.say('The block has started to slide up with ' + loadG() + ' g in the pan.'); S.render(); } } }
      pose();
    },
  };
  function pose() {
    plank.rotation.z = p.angle;
    block.position.set(XS + sim.s, PT, 0);
    var a = p.angle, C = pulleyC(), hook = local(XS + sim.s + BL / 2 + 0.009, PT + BH / 2, 0), tan1 = local(PCX, PT + BH / 2, 0), tan2 = new T.Vector3(C.x + PR, C.y, 0);
    seg(th1, hook, tan1); var pp = panPos(); seg(th2, tan2, pp.clone().setY(pp.y + 0.005));
    wrap.position.copy(C); if (wrap.userData.a !== a) { wrap.userData.a = a; wrap.geometry.dispose(); wrap.geometry = new T.TorusGeometry(PR + 0.0005, 0.0007, 6, 16, Math.PI / 2 + a); }
    pan.position.copy(pp);
    var pb = pp.y - THR - 0.006; panShadow.position.set(pp.x, 0.0009, 0); panShadow.material.opacity = Math.max(0.12, 0.45 - pb * 1.2);
    W.forEach(function (w) { if (w.inPan) w.grp.position.copy(slotWorld(w)); });
    wing.position.set(Math.cos(a) * QR, Math.sin(a) * QR, 0.006); wing.rotation.z = a;
    hudA.set(st.deg.toFixed(0) + '°'); hudL.set(loadG() + ' g'); hudB.set(moving() ? 'sliding' : st.moved ? 'moved' : 'at rest');
  }
  pose();
  return EXP;
});
