/* Prayogshala studio rig: friction between two surfaces (NCERT Class VIII, chapter Friction).
   A flat test surface laid on the laboratory table, a 500 g wooden block with a hook on it, a horizontal thread from
   the hook to a spring balance (0-10 N, least count 0.05 N) whose ring the gloved hand pulls very slowly, and a stand
   of slotted weights that go on top of the block to change the normal reaction. The largest reading on the balance
   just before the block starts to move is the limiting friction. Four loads give four points, and the slope of
   limiting friction against normal reaction is the coefficient of friction.
   Physics: the `pullblock` kernel of the mech_school pack. Every number is read from S.lab.params. */
HoolaStudio.define('friction-pull', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.pullblock;
  var p = window.HoolaKernels.paramsFor('pullblock', S.lab.params);
  p.P = 0; p.load = 0;
  var MG = Math.round(p.m * 1000);
  var FULL = 10, LC = 0.05, RATE = 2.5;                   // spring balance: full scale, least count; pull rate N/s

  // the pair of surfaces comes from the variant's sample (default: the bare wooden block on a wooden board)
  var vs = ((S.lab.variant || {}).sample || '').toLowerCase();
  var OILED = /lubricat|oil/.test(vs);
  function faceOf(txt) {
    if (/glass/.test(txt)) return { c: 0xbfd8e4, r: 0.06, m: 0.1, name: 'glass' };
    if (/alumini/.test(txt)) return { c: 0xc8cdd2, r: 0.3, m: 0.9, name: 'aluminium' };
    if (/copper/.test(txt)) return { c: 0xc27a4a, r: 0.25, m: 0.95, name: 'copper' };
    if (/steel|metal|iron/.test(txt)) return { c: 0xa9aeb4, r: OILED ? 0.1 : 0.3, m: 0.95, name: 'steel' };
    if (/rubber/.test(txt)) return { c: 0x2a2a2c, r: 0.85, m: 0.0, name: 'rubber' };
    return { c: 0xc9a46a, r: 0.75, m: 0.0, name: 'wood' };
  }
  var FACE = faceOf(vs || 'wood');
  var SURF_NAME = FACE.name.charAt(0).toUpperCase() + FACE.name.slice(1) + ' surface' + (OILED ? ' (oiled)' : '');

  // ---------- the load set: slotted weights chosen so the largest reading fits the balance
  var QSET = [0.05, 0.1, 0.2, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0];
  var Q = QSET[0];
  QSET.forEach(function (q) { if (p.mu * (p.m + 3 * q) * p.g <= 9.0) Q = q; });
  var QG = Q >= 1 ? (Q % 1 === 0 ? Q + ' kg' : Q + ' kg') : Math.round(Q * 1000) + ' g';
  var LOADS = [0, 1, 2, 3];

  var st = { ready: false, n: 0, pulling: false, moved: false, done: false, reading: 0, hold: 0, onDone: null, busy: false };
  var sim = K.init(p); sim.s = 0; sim.v = 0; sim.a = 0;

  // ---------- geometry
  var SX = 0.02, SZ = -0.06, SL = 0.64, SW = 0.24, ST = 0.005;      // the test surface
  var BL = 0.1, BH = 0.06, BW = 0.08, SX0 = -0.22;                  // the block, and where it starts
  var CL = 0.19, ROD0 = 0.022, THR = 0.055;                         // balance case, hook rod, thread
  var BY = ST + BH / 2;                                             // the block's centre height

  var sheet = S.rounded(SL, ST, SW, 0.004, new T.MeshStandardMaterial({ color: FACE.c, roughness: FACE.r, metalness: FACE.m }));
  sheet.rotation.x = -Math.PI / 2; sheet.position.set(SX, ST / 2, SZ); S.scene.add(sheet);
  S.contact(SL + 0.08, SW + 0.08, SX, SZ, 0.5);
  if (OILED) {                                                      // a thin film of oil, and the oil can beside it
    var film = new T.Mesh(new T.PlaneGeometry(SL - 0.06, SW - 0.04),
      new T.MeshPhysicalMaterial({ color: 0xcaa54a, roughness: 0.04, metalness: 0.0, transparent: true, opacity: 0.35 }));
    film.rotation.x = -Math.PI / 2; film.position.set(SX, ST + 0.0008, SZ); film.renderOrder = 2; S.scene.add(film);
    var can = new T.Group(); can.position.set(0.48, 0, -0.2); S.scene.add(can);
    can.add(S.mesh(new T.CylinderGeometry(0.028, 0.032, 0.075, 24), new T.MeshStandardMaterial({ color: 0x1d4f3a, roughness: 0.4, metalness: 0.3 })));
    can.children[0].position.y = 0.0375;
    var spout = S.mesh(new T.CylinderGeometry(0.0035, 0.006, 0.07, 12), M.chrome); spout.position.set(0.012, 0.1, 0); spout.rotation.z = -0.45; can.add(spout);
    var cl = S.label('OIL', { w: 0.032, ratio: 0.45, color: '#eef3ee' }); cl.position.set(0, 0.045, 0.0325); can.add(cl);
    S.contact(0.12, 0.12, 0.48, -0.2, 0.5);
  }
  var srfLbl = S.label(SURF_NAME, { w: 0.13, ratio: 0.16, color: '#2a2f36' });
  srfLbl.rotation.x = -Math.PI / 2; srfLbl.position.set(SX - 0.2, ST + 0.0012, SZ + SW / 2 - 0.022); S.scene.add(srfLbl);

  var block = new T.Group(); S.scene.add(block);
  var bm = S.rounded(BL, BH, BW, 0.006, new T.MeshStandardMaterial({ map: S.woodTex, color: 0xb98a58, roughness: 0.6 }));
  bm.position.y = BH / 2; block.add(bm);
  if (FACE.name !== 'wood') {                                       // the block carries the same facing as the surface
    var fp = S.mesh(new T.BoxGeometry(BL - 0.002, 0.0014, BW - 0.002), new T.MeshStandardMaterial({ color: FACE.c, roughness: FACE.r, metalness: FACE.m }));
    fp.position.y = 0.0007; block.add(fp); bm.position.y = BH / 2 + 0.0014;
  }
  var blbl = S.label(MG + ' g', { w: 0.042, ratio: 0.3, color: '#3a2410' }); blbl.position.set(0, BH / 2, BW / 2 + 0.0009); block.add(blbl);
  var eye = S.mesh(new T.TorusGeometry(0.0045, 0.0013, 8, 20), M.brass); eye.position.set(BL / 2 + 0.005, BH / 2, 0); eye.rotation.y = Math.PI / 2; block.add(eye);
  var eyeS = S.mesh(new T.CylinderGeometry(0.0013, 0.0013, 0.007, 8), M.brass); eyeS.rotation.z = Math.PI / 2; eyeS.position.set(BL / 2 + 0.002, BH / 2, 0); block.add(eyeS);
  var blockShadow = S.contact(BL * 1.35, BW * 1.4, 0, 0, 0.4, ST);

  // the slotted weights: three on the stand, lifted one at a time on to the block
  var STAND = new T.Vector3(0.52, 0, 0.06);
  var post = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.12, 16), M.chrome); post.position.set(STAND.x, 0.06, STAND.z); S.scene.add(post);
  var foot = S.rounded(0.13, 0.012, 0.11, 0.004, M.iron); foot.rotation.x = -Math.PI / 2; foot.position.set(STAND.x, 0.006, STAND.z); S.scene.add(foot);
  S.contact(0.2, 0.18, STAND.x, STAND.z, 0.5);
  var WR = 0.034, WT = 0.016;
  var W = [0, 1, 2].map(function (i) {
    var g = new T.Group();
    var d = S.mesh(new T.CylinderGeometry(WR, WR, WT, 32), M.iron); d.position.y = WT / 2; g.add(d);
    var hole = S.mesh(new T.TorusGeometry(0.008, 0.0022, 8, 22), M.chrome); hole.rotation.x = Math.PI / 2; hole.position.y = WT; g.add(hole);
    var l = S.label(QG, { w: WR * 1.3, ratio: 0.4, color: '#e9edf2' }); l.rotation.x = -Math.PI / 2; l.position.y = WT + 0.0004; g.add(l);
    g.position.set(STAND.x, 0.012 + i * WT, STAND.z); S.scene.add(g);
    return { grp: g, home: g.position.clone(), on: false };
  });

  // the spring balance: case with a printed newton scale, a pointer, a hook rod and a pull ring
  var bal = new T.Group(); S.scene.add(bal);
  var caseM = S.rounded(CL, 0.032, 0.03, 0.006, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.45, metalness: 0.3 }));
  caseM.position.set(-CL / 2, 0, 0); bal.add(caseM);
  var scaleTex = S.canvasTex(2048, 220, function (x, w, h) {
    x.fillStyle = '#f4efe0'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#17181a'; x.font = '700 54px "Public Sans", sans-serif'; x.textAlign = 'center';
    for (var i = 0; i <= FULL * 20; i++) {
      var px = 40 + i / (FULL * 20) * (w - 80), big = i % 20 === 0, mid = i % 10 === 0;
      x.fillRect(px - (big ? 2 : 1), 0, big ? 4 : 2, big ? 64 : mid ? 44 : 26);
      if (big) x.fillText(String(i / 20), px, 128);
    }
    x.font = '600 44px "Public Sans", sans-serif'; x.fillStyle = '#6b4a14'; x.fillText('NEWTON   0 – ' + FULL + ' N   l.c. 0.05 N', w / 2, 196);
  });
  var face = new T.Mesh(new T.PlaneGeometry(CL - 0.012, 0.024), new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.5 }));
  face.position.set(-CL / 2, 0.0005, 0.0152); bal.add(face);
  var ptr = S.mesh(new T.BoxGeometry(0.0022, 0.03, 0.002), M.red); ptr.position.set(0, 0.001, 0.0166); bal.add(ptr);
  var rod = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 1, 12), M.chrome, true, false); rod.rotation.z = Math.PI / 2; bal.add(rod);
  var bhook = S.mesh(new T.TorusGeometry(0.006, 0.0016, 8, 22), M.chrome); bhook.rotation.y = Math.PI / 2; bal.add(bhook);
  var ring = S.mesh(new T.TorusGeometry(0.013, 0.0028, 10, 26), M.chrome); ring.rotation.y = Math.PI / 2; bal.add(ring);
  var thM = new T.MeshStandardMaterial({ color: 0xf0ece0, roughness: 0.9 });
  var thread = S.mesh(new T.CylinderGeometry(0.0008, 0.0008, 1, 6), thM, true, false); thread.rotation.z = Math.PI / 2; S.scene.add(thread);

  S.addApparatus('surface', sheet, SURF_NAME, 'The surface the block is dragged over. The pair of surfaces in contact is what the coefficient of friction belongs to.');
  S.addApparatus('block', block, 'Wooden block (' + MG + ' g)', 'Mass ' + MG + ' g, weighed on a balance. A hook on its side takes the thread; slotted weights go on top.');
  S.addApparatus('balance', bal, 'Spring balance (0–' + FULL + ' N)', 'Least count 0.05 N. Pulled horizontally, it shows the force on the block. Read the largest value just before the block moves.');
  S.addApparatus('weights', W[0].grp, 'Slotted weights (' + QG + ' each)', 'Put on the block to press it harder against the surface, so the normal reaction grows.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudL = S.hudCard('Load on block'), hudP = S.hudCard('Balance reads'), hudB = S.hudCard('Block');

  // ---------- helpers
  function ext() { return (p.P / FULL) * 0.03; }                    // how far the spring has stretched
  function blockX() { return SX0 + sim.s; }
  function hookX() { return blockX() + BL / 2 + 0.008; }
  function balHookX() { return hookX() + THR; }
  function ringX() { return balHookX() + ROD0 + ext() + CL + 0.012; }
  function ringWorld() { return new T.Vector3(ringX(), BY, SZ); }
  function totalN() { return (p.m + p.load) * p.g; }
  function along(pts) {
    var L = [0], i;
    for (i = 1; i < pts.length; i++) L.push(L[i - 1] + pts[i].distanceTo(pts[i - 1]));
    return function (k) {
      var d = Math.max(0, Math.min(1, k)) * L[L.length - 1], j, f;
      for (j = 1; j < pts.length; j++) if (d <= L[j] || j === pts.length - 1) {
        f = (d - L[j - 1]) / Math.max(1e-9, L[j] - L[j - 1]);
        return pts[j - 1].clone().lerp(pts[j], Math.min(1, f));
      }
      return pts[pts.length - 1].clone();
    };
  }
  function pose() {
    block.position.set(blockX(), ST, SZ);
    blockShadow.position.set(blockX(), ST + 0.0009, SZ);
    var rx = ringX(), hx = balHookX(), rodLen = ROD0 + ext();
    bal.position.set(rx - 0.012, BY, SZ);
    rod.position.set(-(CL + rodLen / 2) + 0.0, 0, 0); rod.scale.set(1, Math.max(1e-4, rodLen), 1);
    rod.position.x = -CL - rodLen / 2;
    bhook.position.set(-CL - rodLen - 0.006, 0, 0);
    ring.position.set(0.013, 0, 0);
    ptr.position.x = -CL + 0.006 + (p.P / FULL) * (CL - 0.012);
    var a = new T.Vector3(hookX(), BY, SZ), b = new T.Vector3(hx - 0.004, BY, SZ);
    thread.position.set((a.x + b.x) / 2, BY, SZ); thread.scale.set(1, Math.max(1e-4, b.x - a.x), 1);
    W.forEach(function (w, i) {
      if (w.on) w.grp.position.set(blockX(), ST + BH + i * WT, SZ);
    });
    hudL.set(p.load > 0 ? Math.round(p.load * 1000) + ' g' : 'none');
    hudP.set(p.P.toFixed(2) + ' N');
    hudB.set(sim.v !== 0 ? 'sliding' : st.moved ? 'has moved' : 'at rest');
  }

  // ---------- the actions the buttons call
  function addWeight() {
    var w = W.filter(function (q) { return !q.on; })[0];
    if (S.hand.busy || st.busy || !w) return Promise.resolve();
    return resetBlock().then(function () {
      var i = W.filter(function (q) { return q.on; }).length;
      var from = w.home.clone(), to = new T.Vector3(blockX(), ST + BH + i * WT, SZ);
      var path = along([from, from.clone().setY(0.2), to.clone().setY(0.2), to]);
      var G = new T.Vector3(0, WT + 0.004, 0);
      return S.hand.pinchMove(from.clone().add(G), function (k) { return path(k).add(G); },
        function (k) { w.grp.position.copy(path(k)); }, { ms: 1500 });
    })
      .then(function () {
        w.on = true; st.n = W.filter(function (q) { return q.on; }).length; p.load = st.n * Q;
        st.moved = false; st.done = false; st.reading = 0; pose(); S.render();
        S.say('Load on the block: ' + Math.round(p.load * 1000) + ' g. The normal reaction is now ' + totalN().toFixed(2) + ' N.');
      });
  }
  function clearWeights() {
    if (S.hand.busy || st.busy) return Promise.resolve();
    var on = W.filter(function (q) { return q.on; });
    return resetBlock().then(function () { return on.reverse().reduce(function (pr, w) {
      return pr.then(function () {
        var from = w.grp.position.clone(), to = w.home.clone();
        var path = along([from, from.clone().setY(0.2), to.clone().setY(0.2), to]);
        var G = new T.Vector3(0, WT + 0.004, 0);
        return S.hand.pinchMove(from.clone().add(G), function (k) { return path(k).add(G); },
          function (k) { w.grp.position.copy(path(k)); }, { ms: 1200 })
          .then(function () { w.on = false; w.grp.position.copy(to); });
      });
    }, Promise.resolve()); }).then(function () {
      st.n = 0; p.load = 0; st.moved = false; st.done = false; st.reading = 0; pose(); S.render();
    });
  }
  function resetBlock() {
    if (S.hand.busy || st.busy || sim.s < 1e-6) return Promise.resolve();
    var s0 = sim.s;
    function grip(s) { return new T.Vector3(SX0 + s, ST + BH + 0.004 + (st.n * WT), SZ); }
    return S.hand.pinchMove(grip(s0), function (k) { return grip(s0 * (1 - k)); },
      function (k) { sim.s = s0 * (1 - k); sim.v = 0; sim.a = 0; pose(); }, { ms: 1100, mode: 'top', pose: 'grip' })
      .then(function () { sim.s = 0; sim.v = 0; sim.a = 0; st.moved = false; st.done = false; p.P = 0; pose(); S.render(); });
  }
  function waitDone() {
    if (S.fast) { S.advance(40, function () { return st.done; }); return Promise.resolve(); }
    return new Promise(function (res) { st.onDone = res; });
  }
  function pull() {
    if (S.hand.busy || st.busy || st.pulling) return Promise.resolve();
    if (S.rows.some(function (r) { return r.n === st.n; })) {
      S.say('You already have a reading with this load. Change the load for the next one.'); return Promise.resolve();
    }
    return resetBlock().then(function () {
      st.busy = true;
      p.P = 0; st.moved = false; st.done = false; st.reading = 0;
      sim = K.init(p); sim.s = 0; sim.v = 0; sim.a = 0; pose();
      return S.hand.reach(ringWorld(), 'side', 800);
    }).then(function () { return S.hand.shape('grip', 300); })
      .then(function () {
        st.pulling = true;
        S.hand.follow(function () { return ringWorld(); }, 'side', 6000);
        return waitDone();
      })
      .then(function () { return S.hand.away(500); })
      .then(function () {
        st.busy = false; st.pulling = false; p.P = 0; pose(); S.render();
        if (st.moved) S.say('The block began to move at ' + st.reading.toFixed(2) + ' N on the balance.');
        else S.say('The balance reached full scale and the block still did not move. Take some weights off.');
      });
  }
  function record() {
    if (S.hand.busy || st.busy) return;
    if (!st.moved) { S.say('Pull the block until it just begins to move, then record the reading.'); return; }
    if (S.rows.some(function (r) { return r.n === st.n; })) { S.say('That load is already in the table.'); return; }
    S.addRow({ n: st.n, load: p.load, N: totalN(), P: st.reading });
    S.say('Written in your record book: load ' + Math.round(p.load * 1000) + ' g, limiting friction ' + st.reading.toFixed(2) + ' N.');
  }

  var EXP = {
    camera: { pos: [0.35, 0.6, 0.85], look: [0.02, 0.05, -0.05] },
    views: {
      surface: [[0.1, 0.4, 0.5], [0.0, 0.02, -0.06]],
      block: [[-0.14, 0.26, 0.2], [-0.21, 0.04, -0.06]],
      balance: [[0.15, 0.28, 0.26], [0.05, 0.04, -0.06]],
      weights: [[0.46, 0.3, 0.32], [0.52, 0.04, 0.05]],
      setup: [[0.1, 0.42, 0.55], [-0.08, 0.04, -0.06]],
      pull: [[0.12, 0.44, 0.62], [0.0, 0.04, -0.06]],
      book: [[-0.56, 0.46, 0.54], [-0.64, 0.0, 0.1]]
    },
    theory: {
      principle: 'A block lying on a surface does not move until the pull on it is larger than the friction between '
        + 'the two surfaces. The largest friction that can act before sliding begins is called limiting friction, and '
        + 'it is proportional to the normal reaction N pressing the surfaces together.',
      formula: 'f = μ N,   N = (m + load) g',
      formulaNote: 'so μ = slope of the graph of limiting friction against normal reaction',
      more: ['The coefficient of friction μ belongs to the PAIR of surfaces, not to either one alone, and it does not '
        + 'change when the load changes: a bigger load gives a bigger friction, but the ratio stays the same.',
        OILED
          ? 'A lubricant keeps a thin layer of oil between the two surfaces, so they no longer rub metal against '
            + 'metal. The friction, and with it μ, drops sharply.'
          : 'Rougher surfaces grip each other more strongly and give a larger μ. Polishing or oiling the surfaces '
            + 'lowers it.',
        'The reading is taken at the moment the block just begins to move, because after that the surfaces are '
        + 'sliding and the friction is a little smaller.'],
      precautions: 'Keep the thread horizontal and in line with the block, pull very slowly and steadily, and keep '
        + 'the surfaces clean. A jerk gives a reading that is too high. Bring the block back to the same starting '
        + 'mark before every pull.'
    },
    book: {
      at: [-0.6, 0.12, 0.1],
      title: 'Expt. — Friction between two surfaces',
      lines: ['Aim: ' + S.lab.aim, 'Block m = ' + MG + ' g, slotted weights ' + QG + ' each, g = 9.8 m/s²',
        'Surfaces: ' + SURF_NAME + (OILED ? ', with oil between them' : ''),
        'N = (m + load) g,   f = limiting friction,   μ = f / N',
        'Spring balance 0–' + FULL + ' N, least count 0.05 N.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Load (g)', get: function (r) { return String(Math.round(r.load * 1000)); } },
        { label: 'N (N)', get: function (r) { return r.N.toFixed(2); } },
        { label: 'f (N)', get: function (r) { return r.P.toFixed(2); } },
        { label: 'μ = f/N', get: function (r) { return (r.P / r.N).toFixed(3); } }]
    },
    graph: {
      x: function (r) { return r.N; }, y: function (r) { return r.P; },
      xlabel: 'normal reaction N (N)', ylabel: 'limiting friction f (N)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var k = S.fit.origin(rows.map(function (r) { return [r.N, r.P]; }));
      return { label: 'μ', value: k, unit: '', digits: 3, truth: p.mu,
        note: 'Slope of the limiting friction against normal reaction graph, drawn through the origin.' };
    },
    tol: 0.05,
    chips: ['Why must the thread be horizontal?', 'What is limiting friction?', 'Check my readings',
      'Why does the graph pass through the origin?', OILED ? 'How does oil reduce friction?' : 'Does μ depend on the area of contact?'],
    viva: [['The coefficient of friction belongs to', ['the pair of surfaces', 'the block alone', 'the spring balance'], 0,
      'μ describes how two particular surfaces grip each other.'],
    ['Adding weights on the block changes', ['the normal reaction, and so the friction', 'only the mass, not the friction', 'nothing'], 0,
      'N = (m + load) g, and f = μ N.'],
    ['The reading is taken', ['just as the block begins to move', 'after it has slid across', 'before the thread is taut'], 0,
      'That reading is the limiting friction; once it slides, friction is a little less.']],
    askState: function () {
      return { surfaces: SURF_NAME + (OILED ? ' with oil between them' : ''), sample: (S.lab.variant || {}).sample || '',
        block_mass_g: MG, weight_each: QG, weights_on_block: st.n, load_g: Math.round(p.load * 1000),
        normal_reaction_N: +totalN().toFixed(2), balance_reads_N: +p.P.toFixed(2), block_moved: st.moved,
        reading_when_it_moved_N: st.reading, balance_full_scale_N: FULL, balance_least_count_N: LC };
    },

    steps: [
      { id: 'setup', title: 'Set the block up', view: 'setup',
        render: function (u) {
          u.h2('Put the block on the surface');
          u.p('The block rests on the ' + SURF_NAME.toLowerCase() + ', with its hook towards the spring balance. The '
            + 'thread from the hook to the balance must be horizontal, so the whole pull acts along the surface.');
          u.row(u.button('Check the thread and the balance', function () {
            st.ready = true; S.render();
            S.say('The thread is horizontal and the balance reads zero. You can start pulling.');
          }, true, S.hand.busy || st.ready));
          u.task('Ready to pull', st.ready, st.ready ? 'thread horizontal, balance at zero' : 'not checked yet');
          u.live(function () { return 'Balance reads ' + p.P.toFixed(2) + ' N · block ' + (sim.v !== 0 ? 'sliding' : 'at rest'); });
          u.note('Block ' + MG + ' g. Slotted weights of ' + QG + ' each are on the stand; they go on the block in the next step.');
          u.next('Next: pull and read', st.ready && !S.hand.busy);
        },
        ok: function () { return st.ready; },
        auto: function () { st.ready = true; S.render(); return Promise.resolve(); } },

      { id: 'pull', title: 'Pull and read', view: 'pull',
        render: function (u) {
          u.h2('Pull until the block just moves');
          u.p('The hand grips the ring and pulls slowly. Watch the balance: the reading climbs, and the largest value '
            + 'it reaches just before the block slides is the limiting friction for this load.');
          u.row(u.button('Add a ' + QG + ' weight', function () { addWeight(); }, false, S.hand.busy || st.busy || st.n >= 3),
            u.button('Take the weights off', function () { clearWeights(); }, false, S.hand.busy || st.busy || st.n === 0));
          u.row(u.button('Pull the block', function () { pull(); }, true, S.hand.busy || st.busy || S.rows.some(function (r) { return r.n === st.n; })),
            u.button('Record the reading', function () { record(); }, true, S.hand.busy || st.busy || !st.moved));
          u.live(function () {
            return 'Load ' + (p.load > 0 ? Math.round(p.load * 1000) + ' g' : 'none') + ' · N = ' + totalN().toFixed(2)
              + ' N · balance ' + p.P.toFixed(2) + ' N · ' + (st.pulling ? 'pulling' : st.moved ? 'moved at ' + st.reading.toFixed(2) + ' N' : 'at rest');
          });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 4) u.p(S.rows.length + ' of 4 loads done (none, one, two and three weights).');
          u.next('Next: graph and result', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          return LOADS.reduce(function (pr, n) {
            return pr.then(function () {
              var need = n - W.filter(function (q) { return q.on; }).length, q = Promise.resolve(), i;
              for (i = 0; i < need; i++) q = q.then(addWeight);
              return q;
            }).then(function () { return pull(); }).then(function () { record(); });
          }, Promise.resolve());
        } }
    ],

    tick: function (dt) {
      if (st.pulling) {
        if (!st.moved) {
          p.P = Math.min(FULL, p.P + RATE * dt);
          K.step(sim, p, dt);
          if (sim.v !== 0) { st.moved = true; st.reading = Math.round(p.P / LC) * LC; }
          else if (p.P >= FULL - 1e-9) { st.pulling = false; st.done = true; p.P = 0; if (st.onDone) { var f0 = st.onDone; st.onDone = null; f0(); } }
        } else {
          if (sim.s < 0.045) p.P = Math.min(FULL, p.P + RATE * dt);
          else p.P = 0;
          K.step(sim, p, dt);
          if (p.P === 0 && sim.v === 0) {
            st.pulling = false; st.done = true;
            if (st.onDone) { var f1 = st.onDone; st.onDone = null; f1(); }
          }
        }
      }
      pose();
    }
  };
  pose();
  return EXP;
});
