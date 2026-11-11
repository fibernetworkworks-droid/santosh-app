/* Prayogshala studio module: parallelogram law of vectors - the weight of a body (NCERT Class XI, Section A).
   Gravesand's apparatus: a vertical drawing board with a sheet of paper, two pulleys at its upper corners, and three
   threads tied in one knot. Two of them pass over the pulleys and carry the known weights P and Q; the third hangs
   straight down with the body of unknown weight. The gloved hand puts slotted weights on the hangers, taps the board so
   that the threads run free, pushes pins in to mark the three directions, and lays a protractor at the knot.
   Physics: the `vecforce` kernel of the mech11 pack - the knot settles where P, Q and W balance, and the angle θ
   between the upper threads gives R = √(P² + Q² + 2PQ cos θ), which must equal the weight of the body. */
HoolaStudio.define('parallelogram-law', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.vecforce;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('vecforce');
  var VAR = S.lab.variant || {}, BODYNAME = String(VAR.sample || '') || 'Body of unknown weight';
  var G = p.g;
  function grams(N) { return Math.round(N / G * 1000); }
  var P0 = grams(p.P), Q0 = grams(p.Q), W0 = grams(p.W);
  // the pairs of known weights the experiment is repeated with: both must be able to hold the body up
  function ok(Pg, Qg) {
    var a = Pg * G / 1000, b = Qg * G / 1000;
    return a + b > p.W * 1.04 && Math.abs(a - b) < p.W * 0.96;
  }
  var PAIRS = [[P0, Q0], [P0 + 50, Q0], [P0, Q0 + 50], [P0 + 50, Q0 + 50], [P0 - 20, Q0 + 40]].filter(function (q) {
    return q[0] >= 50 && q[1] >= 50 && ok(q[0], q[1]);
  }).slice(0, 3);
  if (PAIRS.length < 3) PAIRS = [[P0, Q0], [P0 + 50, Q0 + 50], [P0 + 100, Q0 + 100]].filter(function (q) { return ok(q[0], q[1]); });

  var sim = K.init(p);
  sim.a = K.measure(p).alpha * 0.82;                                     // hanging, but not yet settled: a tap frees the threads
  var st = { pair: 0, marked: false, measured: null, done: {}, settled: false };

  // ---------- geometry
  var BZ = -0.34, BW = 0.82, BH = 0.62, BY = 0.42;                       // the board (its centre at BY)
  var PX = 0.3, PY = 0.68, PR = 0.026;                                   // the pulleys
  var FZ = BZ + 0.012;                                                   // the plane the threads lie in

  var board = new T.Group(); S.scene.add(board);
  var bb = S.rounded(BW, BH, 0.018, 0.006, M.darkWood); bb.position.set(0, BY, BZ); board.add(bb);
  var paper = S.mesh(new T.BoxGeometry(BW - 0.1, BH - 0.08, 0.0012), M.paper); paper.position.set(0, BY, BZ + 0.0098); board.add(paper);
  [[-1, 1], [1, 1], [-1, -1], [1, -1]].forEach(function (q) {
    var pin = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.004, 12), M.chrome);
    pin.rotation.x = Math.PI / 2; pin.position.set(q[0] * (BW / 2 - 0.06), BY + q[1] * (BH / 2 - 0.05), BZ + 0.012); board.add(pin);
  });
  var foot = S.rounded(0.44, 0.18, 0.04, 0.006, M.iron); foot.rotation.x = -Math.PI / 2; foot.position.set(0, 0.02, BZ + 0.05); board.add(foot);
  [-0.16, 0.16].forEach(function (x) {
    var leg = S.mesh(new T.BoxGeometry(0.03, BY - 0.26, 0.03), M.iron); leg.position.set(x, (BY - 0.26) / 2 + 0.04, BZ + 0.03); board.add(leg);
  });
  S.contact(0.5, 0.24, 0, BZ + 0.05, 0.55);

  var pulleys = [-1, 1].map(function (sgn) {
    var g = new T.Group(); S.scene.add(g);
    var brk = S.mesh(new T.BoxGeometry(0.03, 0.05, 0.012), M.iron); brk.position.set(sgn * PX, PY - 0.03, BZ + 0.012); g.add(brk);
    var wh = S.mesh(new T.CylinderGeometry(PR, PR, 0.008, 36), M.alu); wh.rotation.x = Math.PI / 2; wh.position.set(sgn * PX, PY, FZ + 0.008); g.add(wh);
    var gr = S.mesh(new T.TorusGeometry(PR, 0.0026, 10, 36), M.black); gr.position.set(sgn * PX, PY, FZ + 0.008); g.add(gr);
    var ax = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.03, 12), M.chrome); ax.rotation.x = Math.PI / 2; ax.position.set(sgn * PX, PY, FZ + 0.008); g.add(ax);
    return g;
  });

  // threads + knot
  var thM = new T.MeshStandardMaterial({ color: 0x23242a, roughness: 0.9 });
  function segM() { var m = S.mesh(new T.CylinderGeometry(0.0008, 0.0008, 1, 6), thM, true, false); S.scene.add(m); return m; }
  var thL = segM(), thR = segM(), thW = segM(), thPL = segM(), thPR = segM();
  var upV = new T.Vector3(0, 1, 0);
  function seg(m, a, b) { var d = b.clone().sub(a); m.position.copy(a).add(b).multiplyScalar(0.5); m.scale.set(1, Math.max(1e-4, d.length()), 1); m.quaternion.setFromUnitVectors(upV, d.clone().normalize()); }
  var knot = S.mesh(new T.SphereGeometry(0.006, 16, 12), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.5 }));
  S.scene.add(knot);

  // hangers and the body
  function hanger(label) {
    var g = new T.Group(); S.scene.add(g);
    var hk = S.mesh(new T.TorusGeometry(0.005, 0.0014, 8, 18, Math.PI * 1.6), M.chrome); hk.rotation.set(0, Math.PI / 2, Math.PI * 0.7); g.add(hk);
    var stem = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.05, 12), M.chrome); stem.position.y = -0.028; g.add(stem);
    var disc = S.mesh(new T.CylinderGeometry(0.026, 0.026, 0.006, 32), M.brass); disc.position.y = -0.055; g.add(disc);
    var lb = S.label(label, { w: 0.03, ratio: 0.3, color: '#4a3208' }); lb.position.set(0, -0.055, 0.0265); g.add(lb);
    g.userData.lbl = lb;
    return g;
  }
  var hP = hanger('P'), hQ = hanger('Q');
  var discs = { P: [], Q: [] };
  var DT = 0.009, DR = 0.024;
  function restack(side, n) {
    var list = discs[side], g = side === 'P' ? hP : hQ;
    while (list.length < n) {
      var d = S.mesh(new T.CylinderGeometry(DR, DR, DT, 32), M.brass);
      g.add(d); list.push(d);
    }
    while (list.length > n) { var e = list.pop(); g.remove(e); }
    list.forEach(function (d, i) { d.position.y = -0.052 + 0.004 + DT / 2 + i * DT; });
  }
  var body = new T.Group(); S.scene.add(body);
  var bhk = S.mesh(new T.TorusGeometry(0.005, 0.0014, 8, 18, Math.PI * 1.6), M.chrome); bhk.rotation.set(0, Math.PI / 2, Math.PI * 0.7); body.add(bhk);
  var bst = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.04, 12), M.chrome); bst.position.y = -0.024; body.add(bst);
  var bbdy = S.mesh(new T.CylinderGeometry(0.028, 0.028, 0.05, 32), new T.MeshStandardMaterial({ color: 0x5f646b, roughness: 0.5, metalness: 0.6 }));
  bbdy.position.y = -0.07; body.add(bbdy);
  var blbl = S.label('W = ?', { w: 0.034, ratio: 0.3, color: '#eceef0' }); blbl.position.set(0, -0.07, 0.0285); body.add(blbl);

  // pins that mark the three directions, and the protractor
  var pins = [];
  for (var i = 0; i < 6; i++) {
    var pn = new T.Group();
    var sh = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.012, 10), M.chrome); sh.rotation.x = Math.PI / 2; pn.add(sh);
    var hd = S.mesh(new T.SphereGeometry(0.004, 12, 10), new T.MeshStandardMaterial({ color: i < 2 ? 0xc23b30 : i < 4 ? 0x2e9b5a : 0x2c63c4, roughness: 0.4 }));
    hd.position.z = 0.008; pn.add(hd);
    pn.visible = false; S.scene.add(pn); pins.push(pn);
  }
  var protTex = S.canvasTex(1024, 540, function (x, w, h) {
    x.clearRect(0, 0, w, h);
    var c = w / 2, cy = h - 24, R0 = h - 60;
    x.fillStyle = 'rgba(226,240,250,0.3)'; x.beginPath(); x.arc(c, cy, R0, Math.PI, 2 * Math.PI); x.closePath(); x.fill();
    x.strokeStyle = '#17304d'; x.fillStyle = '#17304d'; x.lineWidth = 2;
    x.beginPath(); x.arc(c, cy, R0, Math.PI, 2 * Math.PI); x.stroke();
    x.beginPath(); x.moveTo(c - R0, cy); x.lineTo(c + R0, cy); x.stroke();
    x.font = '600 22px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
    for (var d = 0; d <= 180; d += 1) {
      var a = Math.PI + d * Math.PI / 180, big = d % 10 === 0, mid = d % 5 === 0, L = big ? 26 : mid ? 16 : 9;
      x.lineWidth = big ? 2.4 : 1.2;
      x.beginPath(); x.moveTo(c + Math.cos(a) * R0, cy + Math.sin(a) * R0); x.lineTo(c + Math.cos(a) * (R0 - L), cy + Math.sin(a) * (R0 - L)); x.stroke();
      if (big) x.fillText(String(d), c + Math.cos(a) * (R0 - 46), cy + Math.sin(a) * (R0 - 46));
    }
  });
  var prot = new T.Mesh(new T.PlaneGeometry(0.17, 0.09), new T.MeshStandardMaterial({ map: protTex, transparent: true, roughness: 0.15, side: T.DoubleSide }));
  prot.position.set(0.3, 0.02, 0.1); prot.rotation.x = -Math.PI / 2; S.scene.add(prot);
  S.contact(0.19, 0.11, 0.3, 0.1, 0.4);

  S.addApparatus('board', board, 'Gravesand\'s drawing board', 'A vertical board with paper pinned to it; the three directions are marked on the paper.');
  S.addApparatus('pulL', pulleys[0], 'Left pulley', 'It turns freely, so the pull in the thread is exactly the weight hanging from it.');
  S.addApparatus('pulR', pulleys[1], 'Right pulley', 'The same on the right, for the weight Q.');
  S.addApparatus('hP', hP, 'Hanger with the weight P', 'The known weight on the left thread.');
  S.addApparatus('hQ', hQ, 'Hanger with the weight Q', 'The known weight on the right thread.');
  S.addApparatus('body', body, BODYNAME, 'Hangs from the third thread; its weight is what the experiment measures.');
  S.addApparatus('prot', prot, 'Protractor', 'Laid with its centre on the knot to read the angle between the two upper threads.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudP = S.hudCard('P'), hudQ = S.hudCard('Q'), hudA = S.hudCard('Angle θ');

  // ---------- where the knot hangs
  function knotPos() {
    var a = sim.a, b = (function () { var s = p.P * Math.sin(a) / p.Q; return Math.asin(Math.min(1, Math.max(-1, s))); })();
    var t = 2 * PX / (Math.sin(a) + Math.cos(a) * Math.tan(b));
    return new T.Vector3(-PX + t * Math.sin(a), PY - t * Math.cos(a), FZ);
  }
  function thetaDeg() { return K.view(sim, p).theta_deg; }
  function settled() { return Math.abs(sim.a - K.measure(p).alpha) < 2e-4; }
  function readTheta() { return Math.round(thetaDeg() * 2) / 2; }        // the protractor is read to half a degree

  function setPair(i) {
    var q = PAIRS[i];
    p.P = q[0] * G / 1000; p.Q = q[1] * G / 1000;
    restack('P', Math.max(1, Math.round(q[0] / 50)));
    restack('Q', Math.max(1, Math.round(q[1] / 50)));
    hP.userData.lbl.material.map = S.canvasTex(256, 96, function (x) {
      x.fillStyle = '#5a3d0c'; x.font = '700 54px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(q[0] + ' g', 128, 50);
    });
    hQ.userData.lbl.material.map = S.canvasTex(256, 96, function (x) {
      x.fillStyle = '#5a3d0c'; x.font = '700 54px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(q[1] + ' g', 128, 50);
    });
    hP.userData.lbl.material.needsUpdate = true; hQ.userData.lbl.material.needsUpdate = true;
  }
  setPair(0);

  // ---------- actions
  function changeWeights(i) {
    if (S.hand.busy) return Promise.resolve();
    if (i === st.pair) { S.say('Those weights are already on the hangers.'); return Promise.resolve(); }
    var side = PAIRS[i][0] !== PAIRS[st.pair][0] ? 'P' : 'Q';
    var g = side === 'P' ? hP : hQ, from = g.position.clone().add(new T.Vector3(0.04, 0.06, 0.03));
    return S.hand.pinchMove(from, function (k) { return from.clone().add(new T.Vector3(0, -0.03 * Math.sin(Math.PI * k), 0)); },
      function () {}, { ms: 1200, mode: 'front' })
      .then(function () {
        st.pair = i; setPair(i); st.marked = false; st.measured = null;
        pins.forEach(function (q) { q.visible = false; });
        prot.position.set(0.3, 0.02, 0.1); prot.rotation.set(-Math.PI / 2, 0, 0);
        S.say('The weights are now P = ' + PAIRS[i][0] + ' g and Q = ' + PAIRS[i][1] + ' g. Let the knot settle again.');
        S.render();
      });
  }
  function tapBoard() {
    if (S.hand.busy) return Promise.resolve();
    return S.hand.tap(board.children[0], 'front').then(function () {
      S.advance(6, settled);
      S.say('Tapped: the threads run free over the pulleys and the knot has taken up its true position.');
      S.render();
    });
  }
  function markDirections() {
    if (S.hand.busy) return Promise.resolve();
    if (!settled()) { S.say('Let the knot come to rest first, and tap the board so that nothing sticks.'); return Promise.resolve(); }
    var kp = knotPos();
    var dirs = [new T.Vector3(-PX, PY, FZ).sub(kp).normalize(), new T.Vector3(PX, PY, FZ).sub(kp).normalize(), new T.Vector3(0, -1, 0)];
    var pr = Promise.resolve();
    dirs.forEach(function (d, i) {
      [0.075, 0.14].forEach(function (r, j) {
        var at = kp.clone().addScaledVector(d, r), pn = pins[i * 2 + j];
        pr = pr.then(function () {
          return S.hand.pinchMove(at.clone().add(new T.Vector3(0, 0, 0.05)), function (k) { return at.clone().add(new T.Vector3(0, 0, 0.05 - 0.044 * k)); },
            function (k) { pn.visible = true; pn.position.copy(at).setZ(FZ + 0.012 - 0.004 * k); }, { ms: 450, mode: 'front' });
        });
      });
    });
    return pr.then(function () {
      st.marked = true;
      S.say('Two pins on each thread: joining each pair gives the direction of that force on the paper.');
      S.render();
    });
  }
  function measureAngle() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.marked) { S.say('Mark the three directions with pins first.'); return Promise.resolve(); }
    var kp = knotPos(), from = prot.position.clone();
    var to = kp.clone().setZ(FZ + 0.004);
    return S.hand.pinchMove(from.clone().add(new T.Vector3(0.06, 0.02, 0.02)),
      function (k) { return from.clone().lerp(to, k).add(new T.Vector3(0.06 * (1 - k), 0.02, 0.02)); },
      function (k) {
        prot.position.copy(from.clone().lerp(to, k));
        prot.rotation.x = -Math.PI / 2 * (1 - k);
      }, { ms: 1300, mode: 'front' })
      .then(function () {
        prot.position.copy(to); prot.rotation.set(0, 0, 0);
        st.measured = readTheta();
        S.say('The protractor is on the knot: the angle between the two upper threads reads ' + st.measured.toFixed(1) + '°.');
        S.render();
      });
  }
  function record() {
    if (S.hand.busy) return;
    if (st.measured === null) { S.say('Measure the angle with the protractor first.'); return; }
    var key = String(st.pair);
    if (st.done[key]) { S.say('This pair of weights is already in the table. Change them.'); return; }
    st.done[key] = true;
    S.addRow({ P: p.P, Q: p.Q, th: st.measured * Math.PI / 180, Pg: PAIRS[st.pair][0], Qg: PAIRS[st.pair][1], thd: st.measured });
    S.say('Written in your record book: P = ' + PAIRS[st.pair][0] + ' g, Q = ' + PAIRS[st.pair][1] + ' g, θ = ' + st.measured.toFixed(1) + '°.');
  }

  function pose() {
    var kp = knotPos();
    knot.position.copy(kp);
    var pl = new T.Vector3(-PX, PY, FZ), pr2 = new T.Vector3(PX, PY, FZ);
    seg(thL, kp, pl); seg(thR, kp, pr2); seg(thW, kp, new T.Vector3(kp.x, kp.y - 0.16, FZ));
    body.position.set(kp.x, kp.y - 0.16, FZ);
    var hpy = PY - 0.2 - (p.P / G) * 0.02, hqy = PY - 0.2 - (p.Q / G) * 0.02;
    hP.position.set(-PX - PR, Math.max(0.12, hpy), FZ + 0.008);
    hQ.position.set(PX + PR, Math.max(0.12, hqy), FZ + 0.008);
    seg(thPL, new T.Vector3(-PX - PR, PY, FZ + 0.008), hP.position.clone());
    seg(thPR, new T.Vector3(PX + PR, PY, FZ + 0.008), hQ.position.clone());
    hudP.set(PAIRS[st.pair][0] + ' g');
    hudQ.set(PAIRS[st.pair][1] + ' g');
    hudA.set(thetaDeg().toFixed(1) + '°');
  }
  pose();

  var CALC = HK.CALCS.vec_W_calc;

  return {
    camera: { pos: [0.0, 0.62, 1.0], look: [0.0, 0.44, -0.3] },
    views: {
      rig: [[0.0, 0.6, 0.95], [0.0, 0.44, -0.3]],
      board: [[0.0, 0.52, 0.56], [0.0, 0.44, -0.33]],
      knot: [[0.02, 0.5, 0.34], [0.0, 0.44, -0.32]],
      hP: [[-0.26, 0.34, 0.38], [-0.3, 0.26, -0.31]],
      hQ: [[0.26, 0.34, 0.38], [0.3, 0.26, -0.31]],
      body: [[0.0, 0.26, 0.34], [0.0, 0.18, -0.31]],
      prot: [[0.14, 0.5, 0.3], [0.0, 0.44, -0.3]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'Three forces that hold a point at rest add up to zero. Here they are the two known weights, pulling '
        + 'the knot along the threads towards the pulleys, and the weight of the body pulling straight down. So the '
        + 'resultant of the two known weights must be equal and opposite to the weight of the body.',
      formula: 'R = √(P² + Q² + 2 P Q cos θ)',
      formulaNote: 'θ is the angle between the threads carrying P and Q · at equilibrium R = weight of the body',
      more: ['The parallelogram law says the resultant of two forces drawn from a point is the diagonal of the '
        + 'parallelogram built on them. Drawing it on the paper to scale gives the same answer as the formula.',
        'Repeating with other pairs of weights gives the same unknown weight: that is the check that the law holds.'],
      precautions: 'The pulleys must turn freely and the threads must not touch the board. Tap the board gently before '
        + 'marking, so the knot takes its true place, and keep the eye square to the paper while marking the directions.'
    },
    book: {
      title: 'Expt. — Parallelogram Law of Vectors',
      lines: ['Aim: weight of a body by the parallelogram law.',
        'Gravesand\'s apparatus, protractor read to 0.5°', 'P and Q are known weights on the two threads',
        'Body hangs from the third thread', 'R = √(P² + Q² + 2PQ cos θ) = weight of the body',
        'Precautions: free pulleys, tap before marking.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'P (g)', get: function (r) { return String(r.Pg); } },
        { label: 'Q (g)', get: function (r) { return String(r.Qg); } },
        { label: 'θ (°)', get: function (r) { return r.thd.toFixed(1); } },
        { label: 'R (N)', get: function (r) { return Math.sqrt(r.P * r.P + r.Q * r.Q + 2 * r.P * r.Q * Math.cos(r.th)).toFixed(3); } },
        { label: 'W (g)', get: function (r) { return String(Math.round(Math.sqrt(r.P * r.P + r.Q * r.Q + 2 * r.P * r.Q * Math.cos(r.th)) / G * 1000)); } }]
    },
    graph: null,
    result: function (rows) {
      if (!rows.length) return null;
      return { label: 'weight of the body', value: CALC.fn(rows, p), unit: 'N', digits: 3, truth: p.W,
        note: 'Mean of R = √(P² + Q² + 2PQ cos θ) over the pairs of weights used. That is ' + grams(CALC.fn(rows, p)) + ' g.' };
    },
    resultNote: 'The angle is the only thing measured here, so everything depends on marking the directions well: a '
      + 'degree of error in θ is about half a per cent in the weight.',
    tol: 0.03,
    chips: ['Why must the pulleys turn freely?', 'Why tap the board before marking?',
      'How is the parallelogram drawn?', 'Check my readings', 'What are the main sources of error?'],
    viva: [['Why are three forces needed to keep the knot at rest?',
      ['Because their vector sum must be zero, and two unequal forces alone cannot balance', 'Because the board is vertical',
        'Because there are three threads'], 0, 'Equilibrium of a point means the vector sum of all forces on it is zero.'],
      ['If the two known weights are made equal and the angle between them is 90°, their resultant is',
        ['√2 times one of them', 'Twice one of them', 'Zero'], 0, 'R = √(P² + P²) = P√2 when cos θ = 0.']],
    askState: function () {
      return { P_g: PAIRS[st.pair][0], Q_g: PAIRS[st.pair][1], angle_now_deg: +thetaDeg().toFixed(2),
        knot_settled: settled(), directions_marked: st.marked, angle_measured_deg: st.measured,
        readings_taken: S.rows.length, pairs_available: PAIRS.map(function (q) { return q[0] + ' g & ' + q[1] + ' g'; }) };
    },

    steps: [
      { id: 'settle', title: 'Set it up', view: 'board', render: function (u) {
          u.h2('Let the knot take its place and mark the directions');
          u.p('The known weights ' + PAIRS[st.pair][0] + ' g and ' + PAIRS[st.pair][1] + ' g hang over the two pulleys, '
            + 'and the body hangs from the third thread. Tap the board so that nothing sticks, then push two pins into '
            + 'the paper along each thread.');
          u.task('1. Tap the board', settled(), settled() ? 'The knot is at rest' : 'The knot is still moving')
            .add(u.button('Tap the board', function () { tapBoard(); }, !settled(), S.hand.busy));
          u.task('2. Mark the three directions', st.marked, st.marked ? 'Six pins in, two on each thread' : 'Two pins on each thread')
            .add(u.button('Push in the pins', function () { markDirections(); }, settled() && !st.marked, S.hand.busy || !settled() || st.marked));
          u.live(function () { return 'Angle between the upper threads: ' + thetaDeg().toFixed(1) + '°' + (settled() ? ' · at rest' : ' · settling…'); });
          u.next('Next: measure the angle', st.marked);
        },
        ok: function () { return st.marked; },
        auto: function () { S.advance(10, settled); return tapBoard().then(markDirections); } },

      { id: 'angle', title: 'Measure θ', view: 'prot', render: function (u) {
          u.h2('Measure the angle between the two threads');
          u.p('Lay the protractor with its centre on the knot and its base along one of the marked directions. Read the '
            + 'angle to the other direction, to half a degree.');
          u.task('Protractor on the knot', st.measured !== null, st.measured !== null ? 'θ = ' + st.measured.toFixed(1) + '°' : 'Centre exactly on the knot')
            .add(u.button('Lay the protractor', function () { measureAngle(); }, st.measured === null, S.hand.busy || st.measured !== null));
          u.row(u.button('Record this reading', record, st.measured !== null, S.hand.busy || st.measured === null));
          u.h3('Observation table'); u.table();
          u.next('Next: other weights', S.rows.length >= 1);
        },
        ok: function () { return S.rows.length >= 1; },
        auto: function () { return measureAngle().then(function () { record(); }); } },

      { id: 'repeat', title: 'Other weights', view: 'rig', render: function (u) {
          u.h2('Change the known weights and repeat');
          u.p('The same body, held by a different pair of weights, must come out with the same weight. That is the test '
            + 'of the parallelogram law.');
          var r1 = u.row();
          PAIRS.forEach(function (q, i) {
            r1.appendChild(u.button((i === st.pair ? '✓ ' : '') + q[0] + ' g & ' + q[1] + ' g', function () { changeWeights(i); },
              false, S.hand.busy || i === st.pair));
          });
          u.row(u.button('Tap the board', function () { tapBoard(); }, false, S.hand.busy),
            u.button('Push in the pins', function () { markDirections(); }, false, S.hand.busy || st.marked),
            u.button('Lay the protractor', function () { measureAngle(); }, false, S.hand.busy || !st.marked),
            u.button('Record', record, true, S.hand.busy || st.measured === null));
          u.live(function () { return 'P ' + PAIRS[st.pair][0] + ' g · Q ' + PAIRS[st.pair][1] + ' g · θ ' + thetaDeg().toFixed(1) + '°'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 3) u.p(S.rows.length + ' of 3 pairs recorded.');
          u.next('Next: the weight of the body', S.rows.length >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          var pr = Promise.resolve();
          [1, 2].forEach(function (i) {
            pr = pr.then(function () { return changeWeights(i); })
              .then(function () { S.advance(10, settled); return tapBoard(); })
              .then(markDirections).then(measureAngle).then(function () { record(); });
          });
          return pr;
        } }
    ],

    tick: function (dt) {
      K.step(sim, p, dt);
      pose();
    }
  };
});
