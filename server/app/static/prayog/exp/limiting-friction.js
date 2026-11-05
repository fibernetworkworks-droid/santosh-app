/* Prayogshala studio module: limiting friction on a horizontal surface (NCERT Class XI, Section A).
   A long wooden plank rests on two blocks so that its right-hand end overhangs; a pulley is clamped there. The body -
   a wooden block for sliding friction, a metal roller for rolling friction - lies on the plank with a thread from its
   hook running horizontally over the pulley to a scale pan. The gloved hand puts weights from the weight box into the
   pan, a few grams at a time, until the body just begins to move, and lays extra weights on the body to change the
   normal reaction. Both NCERT set-ups run on this one rig: the lab's own `mu` and mass decide which.
   Physics: the `friction` kernel of the mech11 pack - the body moves only when the pull passes μR. */
HoolaStudio.define('limiting-friction', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.friction;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('friction');
  p.F = 0; p.add = 0;
  var ROLLER = /roll/i.test(S.lab.id + ' ' + (S.lab.title || '') + ' ' + ((S.lab.variant || {}).sample || ''));
  var BODY = ROLLER ? 'roller' : 'block';
  var MG = Math.round(p.m * 1000);

  // ---------- the weights: a pan of 20 g, pan weights, and slabs that go on the body
  var PAN_G = 20, PAN_SET = [100, 50, 20, 20, 10, 10, 5, 5, 2, 2, 2], SLAB_G = ROLLER ? 500 : 100, NSLAB = 3;
  var STEP_G = 5;                                            // the hand adds the pan weights in 5 g steps
  var st = { pan: 0, slabs: 0, moved: false, lastSafe: 0, startX: 0, done: {} };
  function panLoadN(g) { return (PAN_G + g) * p.g / 1000; }
  var sim = K.init(p);

  // ---------- geometry
  var BY = 0.13, BL = 0.72, BT = 0.02, BW = 0.24, BZ = -0.08, BX = -0.02;    // the plank
  var TOPY = BY + BT / 2;
  var BODY_L = ROLLER ? 0.09 : 0.09, BODY_H = ROLLER ? 0.056 : 0.05, BODY_W = 0.07;
  var ROLL_R = BODY_H / 2;
  var X0 = BX - 0.26, TRAVEL = p.len;                                        // where the body starts, and how far it can go
  var PUX = BX + BL / 2 - 0.01, PUY = TOPY + (ROLLER ? ROLL_R : BODY_H / 2), PUR = 0.025;
  var PAN_Y = 0.055;

  var board = S.rounded(BL, BW, BT, 0.004, M.wood); board.rotation.x = -Math.PI / 2; board.position.set(BX, BY, BZ); S.scene.add(board);
  [[BX - BL / 2 + 0.05, 'left'], [BX + BL / 2 - 0.12, 'right']].forEach(function (q) {
    var sb = S.rounded(0.07, 0.2, BY - BT / 2, 0.005, M.darkWood); sb.rotation.x = -Math.PI / 2;
    sb.position.set(q[0], (BY - BT / 2) / 2, BZ); S.scene.add(sb);
    S.contact(0.12, 0.24, q[0], BZ, 0.5);
  });
  var surf = S.mesh(new T.BoxGeometry(BL - 0.02, 0.0012, BW - 0.02), new T.MeshStandardMaterial({ map: S.woodTex, color: 0xc9a46a, roughness: 0.75 }));
  surf.position.set(BX, TOPY + 0.0006, BZ); S.scene.add(surf);

  // the body
  var body = new T.Group(); S.scene.add(body);
  if (ROLLER) {
    var rollM = S.mesh(new T.CylinderGeometry(ROLL_R, ROLL_R, BODY_W, 40), M.brass); rollM.rotation.x = Math.PI / 2; body.add(rollM);
    [-1, 1].forEach(function (sg) {
      var rim = S.mesh(new T.TorusGeometry(ROLL_R, 0.0022, 10, 40), M.chrome); rim.position.z = sg * BODY_W / 2; body.add(rim);
      var axle = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.012, 14), M.chrome); axle.rotation.x = Math.PI / 2; axle.position.z = sg * (BODY_W / 2 + 0.006); body.add(axle);
    });
    var yoke = S.mesh(new T.TorusGeometry(0.006, 0.0014, 8, 20), M.chrome); yoke.rotation.y = Math.PI / 2; yoke.position.set(ROLL_R + 0.006, 0, 0); body.add(yoke);
  } else {
    var bm = S.rounded(BODY_L, BODY_H, BODY_W, 0.005, new T.MeshStandardMaterial({ map: S.woodTex, color: 0xb98a58, roughness: 0.62 }));
    bm.position.y = 0; body.add(bm);
    var eye = S.mesh(new T.TorusGeometry(0.004, 0.0012, 8, 20), M.brass); eye.rotation.y = Math.PI / 2; eye.position.set(BODY_L / 2 + 0.005, 0, 0); body.add(eye);
    var stub = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, 0.006, 8), M.brass); stub.rotation.z = Math.PI / 2; stub.position.set(BODY_L / 2 + 0.001, 0, 0); body.add(stub);
  }
  var bl = S.label(MG + ' g', { w: 0.035, ratio: 0.3, color: '#3a2410' });
  bl.position.set(0, ROLLER ? 0 : 0.004, BODY_W / 2 + 0.0012); body.add(bl);
  var bodyShadow = S.contact(BODY_L * 1.3, BODY_W * 1.3, 0, BZ, 0.4, TOPY);

  // pulley on a bracket at the overhanging end
  var pul = new T.Group(); S.scene.add(pul);
  var brkt = S.mesh(new T.BoxGeometry(0.012, 0.07, 0.03), M.iron); brkt.position.set(PUX, TOPY - 0.02, BZ); pul.add(brkt);
  var clampJaw = S.mesh(new T.BoxGeometry(0.05, 0.012, 0.04), M.iron); clampJaw.position.set(PUX - 0.02, TOPY - 0.052, BZ); pul.add(clampJaw);
  var wheel = S.mesh(new T.CylinderGeometry(PUR, PUR, 0.008, 40), M.alu); wheel.rotation.x = Math.PI / 2; wheel.position.set(PUX + 0.012, PUY, BZ); pul.add(wheel);
  var groove = S.mesh(new T.TorusGeometry(PUR, 0.0026, 10, 40), M.black); groove.position.set(PUX + 0.012, PUY, BZ); pul.add(groove);
  var axle2 = S.mesh(new T.CylinderGeometry(0.0028, 0.0028, 0.03, 12), M.chrome); axle2.rotation.x = Math.PI / 2; axle2.position.set(PUX + 0.012, PUY, BZ); pul.add(axle2);
  [-0.014, 0.014].forEach(function (z) { var ch = S.mesh(new T.BoxGeometry(0.03, 0.03, 0.003), M.alu); ch.position.set(PUX + 0.004, PUY - 0.004, BZ + z); pul.add(ch); });
  S.contact(0.12, 0.12, PUX, BZ, 0.3, BY - BT / 2);

  // thread + pan
  var thM = new T.MeshStandardMaterial({ color: 0xf0ece0, roughness: 0.9 });
  function segM() { var m = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 1, 6), thM, true, false); S.scene.add(m); return m; }
  var th1 = segM(), th2 = segM();
  var upV = new T.Vector3(0, 1, 0);
  function seg(m, a, b) { var d = b.clone().sub(a); m.position.copy(a).add(b).multiplyScalar(0.5); m.scale.set(1, Math.max(1e-4, d.length()), 1); m.quaternion.setFromUnitVectors(upV, d.clone().normalize()); }
  var pan = new T.Group(); S.scene.add(pan);
  var ring = S.mesh(new T.TorusGeometry(0.005, 0.0012, 8, 18), M.brass); pan.add(ring);
  var dish = S.mesh(new T.LatheGeometry([[0, 0], [0.038, 0], [0.042, 0.007], [0.0425, 0.0075], [0.039, 0.0012], [0, 0.0012]].map(function (q) { return new T.Vector2(q[0], q[1]); }), 44), M.brass);
  dish.position.y = -0.05; pan.add(dish);
  [0, 2.094, 4.189].forEach(function (a) {
    var m = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 1, 5), thM, true, false);
    seg(m, new T.Vector3(0, -0.004, 0), new T.Vector3(Math.cos(a) * 0.04, -0.043, Math.sin(a) * 0.04)); pan.add(m);
  });
  pan.position.set(PUX + 0.012 + PUR, PAN_Y, BZ);
  var panShadow = S.contact(0.1, 0.1, pan.position.x, BZ, 0.3);

  // tray of slotted pan weights (four piles) and the slabs that go on the body
  var BOX = new T.Vector3(0.56, 0, 0.1);
  var box = new T.Group(); box.position.copy(BOX); S.scene.add(box);
  var bxb = S.rounded(0.26, 0.12, 0.022, 0.005, M.darkWood); bxb.rotation.x = -Math.PI / 2; bxb.position.y = 0.011; box.add(bxb);
  var felt = S.mesh(new T.BoxGeometry(0.245, 0.001, 0.105), new T.MeshStandardMaterial({ color: 0x2c4f3a, roughness: 1 })); felt.position.y = 0.0225; box.add(felt);
  var lidLbl = S.label('PAN WEIGHTS  ·  2 g  5 g  10 g  20 g', { w: 0.17, ratio: 0.1, color: '#f1e3c0' });
  lidLbl.rotation.x = -Math.PI / 2; lidLbl.position.set(0, 0.0232, 0.044); box.add(lidLbl);
  S.contact(0.32, 0.18, BOX.x, BOX.z, 0.5);
  var PILES = [[2, 10], [5, 8], [10, 8], [20, 8]];
  var tray = {};
  PILES.forEach(function (q, pi) {
    var g = q[0], n = q[1], r = 0.006 + Math.pow(g, 1 / 3) * 0.0042, th = 0.0022 + g * 0.00012;
    var px = BOX.x - 0.085 + pi * 0.057, pz = BOX.z - 0.012;
    var tex = S.canvasTex(128, 64, function (x) { x.fillStyle = '#5a3d0c'; x.font = '700 40px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(g + ' g', 64, 34); });
    var mat = new T.MeshStandardMaterial({ map: tex, transparent: true, roughness: 0.5, depthWrite: false });
    var list = [];
    for (var k = 0; k < n; k++) {
      var gp = new T.Group();
      var disc = S.mesh(new T.CylinderGeometry(r, r, th, 30), M.brass); gp.add(disc);
      var tag = new T.Mesh(new T.PlaneGeometry(r * 1.3, r * 0.65), mat); tag.rotation.x = -Math.PI / 2; tag.position.y = th / 2 + 0.0003; tag.renderOrder = 2; gp.add(tag);
      gp.position.set(px, 0.0235 + th / 2 + k * th, pz);
      S.scene.add(gp);
      list.push({ g: g, grp: gp, home: gp.position.clone(), r: r, th: th });
    }
    tray[g] = list;
    var pl = S.label(g + ' g', { w: 0.022, ratio: 0.4, color: '#f1e3c0' }); pl.rotation.x = -Math.PI / 2;
    pl.position.set(px, 0.0233, pz - 0.03); box.add(pl);
  });
  var anyWeight = tray[2][0].grp;
  var inPan = [];
  var SLAB_T = 0.012;
  var slabs = [];
  for (var i = 0; i < NSLAB; i++) {
    var sg = new T.Group();
    var sb2 = S.rounded(BODY_L * 0.8, BODY_W * 0.8, SLAB_T, 0.003, M.iron); sb2.rotation.x = -Math.PI / 2; sg.add(sb2);
    var sl = S.label(SLAB_G + ' g', { w: 0.03, ratio: 0.3, color: '#e9eaec' }); sl.rotation.x = -Math.PI / 2; sl.position.y = SLAB_T / 2 + 0.0004; sg.add(sl);
    sg.position.set(0.2, SLAB_T / 2 + i * (SLAB_T + 0.001), 0.14);
    S.scene.add(sg); slabs.push(sg);
  }
  S.contact(0.1, 0.09, 0.2, 0.14, 0.5);

  S.addApparatus('board', board, 'Horizontal plank', 'A long wooden plank on two supports, its right end overhanging the bench with the pulley clamped to it.');
  S.addApparatus('body', body, ROLLER ? 'Metal roller (' + MG + ' g)' : 'Wooden block (' + MG + ' g)',
    ROLLER ? 'It rolls about the line where it touches the plank, so what resists it is rolling friction.'
      : 'It slides along the plank. Its weight, with anything on it, gives the normal reaction R.');
  S.addApparatus('pul', pul, 'Pulley', 'A light pulley clamped at the edge: it turns the horizontal pull into the weight hanging in the pan.');
  S.addApparatus('pan', pan, 'Scale pan (' + PAN_G + ' g)', 'Weights are added to it a few grams at a time until the body just begins to move.');
  S.addApparatus('box', box, 'Pan weights', 'Four piles of slotted brass weights: 2 g, 5 g, 10 g and 20 g.');
  S.addApparatus('slabs', slabs[0], 'Weights for the body', NSLAB + ' slabs of ' + SLAB_G + ' g that are laid on the body to change the normal reaction.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudR = S.hudCard('Normal reaction R'), hudF = S.hudCard('Pull from the pan'), hudM = S.hudCard(ROLLER ? 'Roller' : 'Block');

  // ---------- actions
  function R() { return (p.m + p.add) * p.g; }
  function moving() { return sim.v !== 0 || sim.s > 1e-5; }
  function resetBody() {
    sim = K.init(p); p.F = 0; st.pan = 0; st.moved = false; st.lastSafe = 0;
    inPan.forEach(function (w) { w.grp.position.copy(w.home); w.inPan = false; });
    inPan = [];
    S.render();
  }
  function freeOf(g) { var l = tray[g] || [], i; for (i = l.length - 1; i >= 0; i--) if (!l[i].inPan) return l[i]; return null; }
  function addToPan(g) {
    if (S.hand.busy) return Promise.resolve(false);
    if (st.moved) { S.say('The ' + BODY + ' has already moved. Record the reading, then set it back for the next load.'); return Promise.resolve(false); }
    var w = freeOf(g);
    if (!w) { S.say('No ' + g + ' g weights are left in the tray.'); return Promise.resolve(false); }
    var from = w.grp.position.clone(), n = inPan.length;
    var slot = new T.Vector3(pan.position.x + (n % 3 - 1) * 0.011, PAN_Y - 0.047 + w.th / 2 + Math.floor(n / 3) * w.th, BZ + (n % 2 ? 0.011 : -0.011));
    function path(k) {
      return new T.Vector3(from.x + (slot.x - from.x) * k, Math.max(from.y, slot.y) + 0.07 * Math.sin(Math.PI * k) + (from.y < slot.y ? 0 : 0) + (slot.y - from.y) * k * 0, from.z + (slot.z - from.z) * k);
    }
    function pt(k) { return new T.Vector3(from.x + (slot.x - from.x) * k, from.y + (slot.y - from.y) * k + 0.07 * Math.sin(Math.PI * k), from.z + (slot.z - from.z) * k); }
    var grip = new T.Vector3(w.r + 0.001, 0, 0);
    st.lastSafe = st.pan;
    return S.hand.pinchMove(from.clone().add(grip), function (k) { return pt(k).add(grip); },
      function (k) { w.grp.position.copy(pt(k)); }, { ms: 1000 })
      .then(function () {
        w.inPan = true; inPan.push(w); st.pan += w.g; p.F = panLoadN(st.pan);
        S.render();
        return true;
      });
  }
  function putSlab() {
    if (S.hand.busy) return Promise.resolve();
    if (st.slabs >= NSLAB) { S.say('All the slabs are already on the ' + BODY + '.'); return Promise.resolve(); }
    var g = slabs[NSLAB - 1 - st.slabs], from = g.position.clone(), n = st.slabs;
    var to = new T.Vector3(bodyX(), TOPY + (ROLLER ? ROLL_R * 2 : BODY_H) + SLAB_T / 2 + n * (SLAB_T + 0.001), BZ);
    function path(k) { return new T.Vector3(from.x + (to.x - from.x) * k, from.y + Math.sin(Math.PI * k) * 0.06 + (to.y - from.y) * k, from.z + (to.z - from.z) * k); }
    var grip = new T.Vector3(BODY_L * 0.4, 0.004, 0);
    return S.hand.pinchMove(from.clone().add(grip), function (k) { return path(k).add(grip); },
      function (k) { g.position.copy(path(k)); }, { ms: 1300 })
      .then(function () {
        st.slabs = n + 1; p.add = st.slabs * SLAB_G / 1000; g.userData.on = true;
        resetBody();
        S.say(SLAB_G + ' g more on the ' + BODY + ': the normal reaction is now ' + R().toFixed(2) + ' N. Start again with an empty pan.');
        S.render();
      });
  }
  function record() {
    if (S.hand.busy) return;
    if (!st.moved) { S.say('Add weights until the ' + BODY + ' just begins to move, then record.'); return; }
    var key = String(st.slabs);
    if (st.done[key]) { S.say('This load is already in the table. Put another weight on the ' + BODY + '.'); return; }
    var leastG = PAN_G + (st.lastSafe + st.pan) / 2;          // between the load that held and the load that moved it
    st.done[key] = true;
    S.addRow({ R: R(), F: leastG * p.g / 1000, panG: st.pan + PAN_G, addG: Math.round(p.add * 1000) });
    S.say('Written in your record book: R = ' + R().toFixed(2) + ' N, least pull ' + (leastG * p.g / 1000).toFixed(3) + ' N.');
  }
  function bodyX() { return X0 + sim.s; }

  function step_(g, guard) {                                   // add g-gram weights until it just moves
    if (st.moved || guard <= 0) return Promise.resolve();
    return addToPan(g).then(function (ok) {
      if (!ok) return;
      S.advance(1.0);
      if (!st.moved) return step_(g, guard - 1);
    });
  }
  function fill_(upto, g, guard) {                             // come back up to a load already known to be safe
    if (st.pan + g > upto || guard <= 0) return Promise.resolve();
    return addToPan(g).then(function (ok) { if (ok) return fill_(upto, g, guard - 1); });
  }
  function approach() {
    return step_(20, 40).then(function () {
      var low = st.lastSafe;                                   // the largest load that did NOT move it
      resetBody();
      return fill_(low, 20, 20).then(function () { return fill_(low, 5, 10); }).then(function () { return step_(2, 20); });
    }).then(function () { record(); });
  }

  var CALC = HK.CALCS.friction_mu;

  return {
    camera: { pos: [0.62, 0.5, 1.05], look: [0.12, 0.1, -0.04] },
    views: {
      rig: [[0.6, 0.48, 1.0], [0.12, 0.1, -0.04]],
      board: [[0.3, 0.38, 0.6], [BX, TOPY, BZ]],
      body: [[0.0, TOPY + 0.14, 0.3], [X0 + 0.05, TOPY + 0.02, BZ]],
      pul: [[0.52, 0.26, 0.42], [PUX, 0.1, BZ]],
      pan: [[0.56, 0.22, 0.4], [pan.position.x, PAN_Y - 0.03, BZ]],
      box: [[0.62, 0.3, 0.46], [BOX.x, 0.03, BOX.z]],
      slabs: [[0.34, 0.26, 0.4], [0.2, 0.03, 0.14]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: ROLLER
        ? 'A roller does not rub along the plank: it turns about the line where it touches. What holds it back is the '
          + 'slight flattening of the roller and the plank there, and it is far weaker than sliding friction. It still '
          + 'grows in proportion to the normal reaction.'
        : 'Friction between two surfaces at rest grows with the force that tries to move them, up to a greatest value '
          + 'called limiting friction. That greatest value is proportional to the normal reaction between the surfaces.',
      formula: ROLLER ? 'F = μ_r R' : 'F = μ R',
      formulaNote: 'R = weight of the ' + BODY + ' and of anything on it · the slope of F against R is the coefficient',
      more: ['The pull comes from the weight hanging in the pan, turned horizontal by the pulley. The least weight that '
        + 'just sets the body moving measures the limiting friction at that normal reaction.',
        'Putting weights on the body changes R without changing the surfaces. Plotting F against R gives a straight line '
        + 'through the origin, and its slope is the coefficient.'],
      precautions: 'Keep the thread horizontal and in line with the body. Add the weights gently, in small steps, and '
        + 'never jerk the pan. Set the body back to the same starting place each time.'
    },
    book: {
      title: ROLLER ? 'Expt. — Rolling Friction' : 'Expt. — Limiting Friction',
      lines: ['Aim: coefficient of ' + (ROLLER ? 'rolling' : 'limiting sliding') + ' friction between the ' + BODY + ' and the plank.',
        'Mass of the ' + BODY + ' = ' + MG + ' g,  pan = ' + PAN_G + ' g',
        'R = (mass of the ' + BODY + ' + weights on it) × g',
        'F = weight in the pan that just moves it', 'F = μ R  →  μ = slope of F against R',
        'Precautions: thread horizontal, weights added gently.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'On the ' + BODY + ' (g)', get: function (r) { return String(r.addG); } },
        { label: 'R (N)', get: function (r) { return r.R.toFixed(2); } },
        { label: 'Pan + weights (g)', get: function (r) { return String(Math.round(r.panG)); } },
        { label: 'F (N)', get: function (r) { return r.F.toFixed(3); } },
        { label: 'F / R', get: function (r) { return (r.F / r.R).toFixed(3); } }]
    },
    graph: {
      x: function (r) { return r.R; }, y: function (r) { return r.F; },
      xlabel: 'Normal reaction R (N)', ylabel: 'Least pull F (N)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      return { label: ROLLER ? 'μ (rolling)' : 'μ (limiting friction)', value: CALC.fn(rows, p), unit: '', digits: 3,
        truth: p.mu, note: 'From the slope of the straight line F against R through the origin.' };
    },
    resultNote: 'The least pull can only be found to within the smallest weight used, so each point carries a few per cent '
      + 'of uncertainty; the slope of the line is better than any single reading.',
    tol: 0.07,
    chips: ['Why does the area of contact not matter?', 'What is limiting friction?',
      ROLLER ? 'Why is rolling friction so small?' : 'Why is the graph a straight line?', 'Check my readings',
      'What are the main sources of error?'],
    viva: [['What does the slope of the F against R graph give?',
      ['The coefficient of friction', 'The weight of the ' + BODY, 'The value of g'], 0, 'F = μR, so F/R is the slope.'],
      ['The least pull is taken as the mean of the load that just held and the load that just moved the body, because',
        ['The true limiting value lies between them', 'The pan is light', 'Friction is not constant'], 0,
        'Weights come in steps, so the limiting value is bracketed by the two.']],
    askState: function () {
      return { body: BODY, mass_g: MG, weights_on_body_g: Math.round(p.add * 1000), normal_reaction_N: +R().toFixed(3),
        pan_total_g: PAN_G + st.pan, pull_N: +p.F.toFixed(3), has_moved: st.moved,
        moved_at_pan_g: st.moved ? PAN_G + st.pan : null, readings_taken: S.rows.length };
    },

    steps: [
      { id: 'first', title: 'Least pull', view: 'rig', render: function (u) {
          u.h2('Find the least pull that moves the ' + BODY);
          u.p('The ' + BODY + ' rests on the plank and the thread runs over the pulley to the pan. Put weights into the '
            + 'pan, large ones first and then small ones, until it just begins to move. Then set it back and come up to '
            + 'the same load in 2 g steps, so that you know the least pull to within 2 grams.');
          var r1 = u.row();
          [20, 10, 5, 2].forEach(function (g) {
            r1.appendChild(u.button('Add ' + g + ' g', function () { addToPan(g); }, g === 20, S.hand.busy || st.moved));
          });
          u.row(u.button('Set the ' + BODY + ' back and empty the pan', function () { resetBody(); S.say('Pan emptied and the ' + BODY + ' set back at the start.'); }, false, S.hand.busy),
            u.button('Record the least pull', record, st.moved, S.hand.busy || !st.moved));
          u.live(function () {
            return 'Pan ' + (PAN_G + st.pan) + ' g = ' + p.F.toFixed(3) + ' N · R = ' + R().toFixed(2) + ' N · '
              + (st.moved ? 'it has MOVED' : 'still at rest');
          });
          u.h3('Observation table'); u.table();
          u.next('Next: change the normal reaction', S.rows.length >= 1);
        },
        ok: function () { return S.rows.length >= 1; },
        auto: function () { return approach(); } },

      { id: 'loads', title: 'Change R', view: 'rig', render: function (u) {
          u.h2('Change the normal reaction and repeat');
          u.p('Lay a ' + SLAB_G + ' g weight on the ' + BODY + '. Its weight presses the surfaces together harder, so R grows. '
            + 'Find the least pull again for each load.');
          var r2 = u.row();
          r2.appendChild(u.button('Put ' + SLAB_G + ' g on the ' + BODY, function () { putSlab(); }, st.slabs < NSLAB && !!st.done[String(st.slabs)], S.hand.busy || st.slabs >= NSLAB));
          [20, 10, 5, 2].forEach(function (g) {
            r2.appendChild(u.button('+' + g + ' g', function () { addToPan(g); }, false, S.hand.busy || st.moved));
          });
          u.row(u.button('Set the ' + BODY + ' back and empty the pan', function () { resetBody(); }, false, S.hand.busy),
            u.button('Record the least pull', record, st.moved, S.hand.busy || !st.moved));
          u.live(function () {
            return 'On the ' + BODY + ': ' + Math.round(p.add * 1000) + ' g · R = ' + R().toFixed(2) + ' N · pan '
              + (PAN_G + st.pan) + ' g · ' + (st.moved ? 'it has MOVED' : 'at rest');
          });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 loads recorded.');
          u.next('Next: the graph and μ', S.rows.length >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          var pr = Promise.resolve();
          for (var n = 0; n < NSLAB; n++) pr = pr.then(function () { return putSlab(); }).then(function () { return approach(); });
          return pr;
        } }
    ],

    tick: function (dt) {
      K.step(sim, p, dt);
      if (sim.s > 1e-5 && !st.moved) { st.moved = true; S.render(); }
      var x = bodyX();
      body.position.set(x, TOPY + (ROLLER ? ROLL_R : BODY_H / 2), BZ);
      if (ROLLER) body.rotation.z = -sim.s / ROLL_R;
      bodyShadow.position.x = x;
      slabs.forEach(function (g, i) {
        if (g.userData.on) g.position.x = x;
      });
      var hook = new T.Vector3(x + (ROLLER ? ROLL_R + 0.006 : BODY_L / 2 + 0.005), PUY, BZ);
      var top = new T.Vector3(PUX + 0.012, PUY, BZ);
      seg(th1, hook, top);
      var panTop = new T.Vector3(PUX + 0.012 + PUR, PAN_Y, BZ);
      seg(th2, new T.Vector3(PUX + 0.012 + PUR, PUY, BZ), panTop);
      pan.position.set(panTop.x, PAN_Y - Math.min(0.03, sim.s * 1.0), BZ);
      inPan.forEach(function (w, i) {
        w.grp.position.set(pan.position.x + (i % 3 - 1) * 0.013, pan.position.y - 0.048 + 0.0012, BZ + (i % 2 ? 0.012 : -0.012));
      });
      panShadow.position.x = pan.position.x;
      hudR.set(R().toFixed(2) + ' N');
      hudF.set(p.F.toFixed(3) + ' N');
      hudM.set(st.moved ? 'has moved' : 'at rest');
    }
  };
});
