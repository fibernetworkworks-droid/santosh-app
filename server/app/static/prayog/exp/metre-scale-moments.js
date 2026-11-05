/* Prayogshala studio module: mass of a body with a metre scale and the principle of moments (NCERT Class XI).
   A metre scale rests on a steel knife edge fixed in a wooden stand, balanced at its own centre of gravity. The body of
   unknown mass hangs from a loop of thread on the left at a measured distance; a known mass hangs from a second loop on
   the right. The gloved hand slides the known loop along the scale, a centimetre and then a millimetre at a time, until
   the scale is level again, and moves the body to another distance for the next reading.
   Physics: the `moments` kernel of the mech11 pack - the scale settles at the tilt where the moments and the knife
   edge's own small restoring couple balance; the balance point is where m x = M y. */
HoolaStudio.define('metre-scale-moments', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.moments;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('moments');
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var BODYNAME = SAMPLE || 'Body of unknown mass';
  var XS = [p.x, Math.max(0.08, p.x * 0.65), Math.min(0.42, p.x * 1.4)].map(function (v) { return Math.round(v * 200) / 200; });
  var MG = Math.round(p.M * 1000);
  var sim = K.init(p);
  var st = { xi: 0, moved: 0, done: {} };

  // ---------- geometry
  var SY = 0.21, SZ = -0.08, LEN = 1.0, TH = 0.007, SW = 0.032;        // the scale: 1 m long, pivoted at its centre
  var KNY = SY - TH / 2;

  var stand = new T.Group(); S.scene.add(stand);
  var sbase = S.rounded(0.16, 0.13, 0.02, 0.005, M.darkWood); sbase.rotation.x = -Math.PI / 2; sbase.position.set(0, 0.01, SZ); stand.add(sbase);
  var scol = S.rounded(0.05, 0.17, 0.05, 0.006, M.darkWood); scol.position.set(0, 0.105, SZ); stand.add(scol);
  var knifeShape = new T.Shape();
  knifeShape.moveTo(-0.012, 0); knifeShape.lineTo(0.012, 0); knifeShape.lineTo(0, 0.016); knifeShape.lineTo(-0.012, 0);
  var knife = S.mesh(new T.ExtrudeGeometry(knifeShape, { depth: 0.07, bevelEnabled: false }), M.chrome);
  knife.rotation.y = 0; knife.position.set(0, KNY - 0.016, SZ - 0.035); stand.add(knife);
  S.contact(0.22, 0.18, 0, SZ, 0.55);

  var pivot = new T.Group(); pivot.position.set(0, SY, SZ); S.scene.add(pivot);
  var ruler = S.ruler(LEN, { title: 'METRE SCALE · cm', labelEvery: 10, width: SW, thick: TH });
  ruler.rotation.z = Math.PI / 2; ruler.position.set(LEN / 2, 0, 0);     // printed zero at the left end, 100 at the right
  pivot.add(ruler);
  var ridge = S.mesh(new T.BoxGeometry(0.02, 0.002, SW), M.chrome); ridge.position.set(0, -TH / 2, 0); pivot.add(ridge);

  // ---------- the two loops of thread, with the body and the known mass
  var thM = new T.MeshStandardMaterial({ color: 0xf0ece0, roughness: 0.9 });
  function loop(xLocal) {
    var g = new T.Group(); g.position.set(xLocal, 0, 0); pivot.add(g);
    [-0.012, 0.012].forEach(function (z) {
      var sm = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 0.05, 6), thM, true, false);
      sm.position.set(0, -0.026, z * 0.6); sm.rotation.x = Math.atan2(z * 0.6, 0.026); g.add(sm);
    });
    var hook = S.mesh(new T.TorusGeometry(0.005, 0.0012, 8, 18), M.chrome); hook.rotation.y = Math.PI / 2; hook.position.y = -0.052; g.add(hook);
    return g;
  }
  var loopL = loop(-p.x), loopR = loop(p.y);
  var bodyG = new T.Group(); loopL.add(bodyG); bodyG.position.y = -0.082;
  var bodyM = S.mesh(new T.DodecahedronGeometry(0.026, 0), new T.MeshStandardMaterial({ color: 0x6a6f76, roughness: 0.55, metalness: 0.5 }));
  bodyM.scale.set(1, 0.85, 0.9); bodyG.add(bodyM);
  var bodyEye = S.mesh(new T.TorusGeometry(0.005, 0.0012, 8, 18), M.chrome); bodyEye.rotation.y = Math.PI / 2; bodyEye.position.y = 0.026; bodyG.add(bodyEye);
  var knownG = new T.Group(); loopR.add(knownG); knownG.position.y = -0.068;
  var kDisc = S.mesh(new T.CylinderGeometry(0.019, 0.019, 0.013, 32), M.brass); knownG.add(kDisc);
  var kKnob = S.mesh(new T.SphereGeometry(0.005, 14, 10), M.brass); kKnob.position.y = 0.011; knownG.add(kKnob);
  var kLbl = S.label(MG + ' g', { w: 0.026, ratio: 0.35, color: '#4a3208' }); kLbl.position.set(0, 0, 0.0195); knownG.add(kLbl);

  // a card with what is known
  var card = S.label('Known mass ' + MG + ' g  ·  m x = M y', { w: 0.2, ratio: 0.1, color: '#2a2a2a', bg: '#f5f1e6' });
  card.rotation.x = -Math.PI / 2; card.position.set(0.34, 0.001, 0.14); S.scene.add(card);

  S.addApparatus('stand', stand, 'Stand with knife edge', 'A sharp steel edge on a wooden stand: the scale turns freely on it.');
  S.addApparatus('beam', ruler, 'Metre scale', 'Balanced at its own centre of gravity first, so its weight has no moment about the knife edge.');
  S.addApparatus('body', bodyG, BODYNAME, 'Hung from a loop of thread at a measured distance x on the left.');
  S.addApparatus('known', knownG, 'Known mass (' + MG + ' g)', 'Slid along the scale until the moments balance.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudX = S.hudCard('Body at x'), hudY = S.hudCard('Known mass at y'), hudT = S.hudCard('Scale');

  // ---------- actions
  function tiltDeg() { return sim.y[0] * 180 / Math.PI; }
  function level() { return Math.abs(sim.y[0]) < 0.004 && Math.abs(sim.y[1]) < 0.01; }
  function pointOn(xLocal) {                                  // world point of a mark on the tilted scale
    var c = Math.cos(sim.y[0]), s = Math.sin(sim.y[0]);
    return new T.Vector3(xLocal * c, SY + xLocal * s, SZ);
  }
  function slide(dy) {
    if (S.hand.busy) return Promise.resolve();
    var y1 = Math.round((p.y + dy) * 10000) / 10000;
    if (y1 < 0.02 || y1 > 0.48) { S.say('The known mass must stay on the scale, between 2 cm and 48 cm from the knife edge.'); return Promise.resolve(); }
    var y0 = p.y;
    function at(k) { return pointOn(y0 + (y1 - y0) * k).add(new T.Vector3(0, -0.06, 0)); }
    return S.hand.pinchMove(at(0), at, function (k) { p.y = y0 + (y1 - y0) * k; loopR.position.x = p.y; },
      { ms: Math.abs(dy) > 0.005 ? 900 : 550, mode: 'front' })
      .then(function () { p.y = y1; loopR.position.x = p.y; S.render(); });
  }
  function moveBody(i) {
    if (S.hand.busy) return Promise.resolve();
    var x1 = XS[i], x0 = p.x;
    function at(k) { return pointOn(-(x0 + (x1 - x0) * k)).add(new T.Vector3(0, -0.06, 0)); }
    return S.hand.pinchMove(at(0), at, function (k) { p.x = x0 + (x1 - x0) * k; loopL.position.x = -p.x; }, { ms: 1100 })
      .then(function () {
        p.x = x1; loopL.position.x = -p.x; st.xi = i; st.moved++;
        S.say('The body now hangs ' + (p.x * 100).toFixed(1) + ' cm from the knife edge. Balance the scale again.');
        S.render();
      });
  }
  function record() {
    if (S.hand.busy) return;
    if (!level()) { S.say('The scale is not level yet: slide the known mass until it is.'); return; }
    var key = (p.x * 1000).toFixed(0);
    if (st.done[key]) { S.say('This distance is already in the table. Move the body to another mark.'); return; }
    st.done[key] = true;
    S.addRow({ x: p.x, y: p.y, M: p.M });
    S.say('Written in your record book: x = ' + (p.x * 100).toFixed(1) + ' cm, y = ' + (p.y * 100).toFixed(1) + ' cm.');
  }
  function balanceAuto() {                                    // the real procedure: watch the tilt, slide, watch again
    function settle(sec) { S.advance(sec); }                  // no early exit: the scale must really come to rest
    function run(step, want, guard) {
      if (guard <= 0) return Promise.resolve();
      var th = sim.y[0];
      if (Math.abs(th) <= want) return Promise.resolve();
      return slide(th > 0 ? -step : step).then(function () { settle(2.5); return run(step, want, guard - 1); });
    }
    settle(2.5);
    return run(0.01, 0.01, 60).then(function () { return run(0.001, 0.0012, 40); }).then(function () { settle(6); });
  }

  var CALC = HK.CALCS.moments_m;

  return {
    camera: { pos: [0.08, 0.52, 0.86], look: [0.0, 0.17, -0.08] },
    views: {
      rig: [[0.06, 0.5, 0.84], [0.0, 0.17, -0.08]],
      stand: [[0.12, 0.3, 0.34], [0.0, 0.15, -0.08]],
      beam: [[0.0, 0.42, 0.62], [0.0, 0.2, -0.08]],
      body: [[-0.18, 0.28, 0.36], [-p.x, 0.12, -0.08]],
      known: [[0.24, 0.28, 0.36], [0.2, 0.13, -0.08]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'A body that does not turn has no net moment about the pivot. The metre scale is first balanced on the '
        + 'knife edge at its own centre of gravity, so its weight gives no moment. The body hangs on one side and a '
        + 'known mass on the other; when the scale is level again their moments are equal.',
      formula: 'm g x = M g y, so m = M y / x',
      formulaNote: 'x and y are measured from the knife edge, along the scale',
      more: ['Only the ratio of the distances matters, so the mass of the body can be found with nothing but a metre '
        + 'scale, a knife edge, a loop of thread and one known mass - no balance at all.',
        'Taking three different distances x and averaging guards against a knife edge that is not exactly at the centre '
        + 'of gravity.'],
      precautions: 'Balance the bare scale first. Keep the loops vertical and read the distances from the knife edge, '
        + 'not from the end of the scale. Let the scale come to rest before you decide it is level.'
    },
    book: {
      title: 'Expt. — Mass by the Principle of Moments',
      lines: ['Aim: mass of a body with a metre scale and a known mass.',
        'Known mass M = ' + MG + ' g', 'Knife edge at the centre of gravity of the scale',
        'x = distance of the body, y = distance of the known mass', 'At balance: m x = M y  →  m = M y / x',
        'Precautions: balance the bare scale first, vertical loops.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'x (cm)', get: function (r) { return (r.x * 100).toFixed(1); } },
        { label: 'y (cm)', get: function (r) { return (r.y * 100).toFixed(1); } },
        { label: 'M (g)', get: function (r) { return String(Math.round(r.M * 1000)); } },
        { label: 'm = M y / x (g)', get: function (r) { return (r.M * r.y / r.x * 1000).toFixed(1); } }]
    },
    graph: {
      x: function (r) { return r.x; }, y: function (r) { return r.y; },
      xlabel: 'Distance of the body x (m)', ylabel: 'Distance of the known mass y (m)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; }
    },
    result: function (rows) {
      if (!rows.length) return null;
      return { label: 'mass of the body', value: CALC.fn(rows, p) * 1000, unit: 'g', digits: 1, truth: p.m * 1000,
        note: 'Mean of m = M y / x over the distances used. The slope of y against x is m / M.' };
    },
    tol: 0.02,
    chips: ['What is a moment?', 'Why balance the bare scale first?', 'Why take three distances?', 'Check my readings',
      'What are the main sources of error?'],
    viva: [['Why must the scale be balanced at its centre of gravity before the experiment?',
      ['So that the weight of the scale itself has no moment about the knife edge', 'To make the scale lighter',
        'To keep the thread straight'], 0, 'The weight acts at the centre of gravity, so its distance from the pivot is zero.'],
      ['If the known mass is 50 g at 20.9 cm and the body hangs at 20.0 cm, the body\'s mass is about',
        ['52 g', '48 g', '50 g'], 0, 'm = M y / x = 50 × 20.9 / 20.0 g.']],
    askState: function () {
      return { known_mass_g: MG, body_distance_cm: +(p.x * 100).toFixed(1), known_distance_cm: +(p.y * 100).toFixed(1),
        tilt_deg: +tiltDeg().toFixed(2), is_level: level(), moment_left: +(p.m * p.x).toFixed(5),
        moment_right: +(p.M * p.y).toFixed(5), readings_taken: S.rows.length };
    },

    steps: [
      { id: 'balance', title: 'Balance it', view: 'rig', render: function (u) {
          u.h2('Balance the scale and take the first reading');
          u.p('The body hangs ' + (p.x * 100).toFixed(1) + ' cm to the left of the knife edge. Slide the ' + MG
            + ' g known mass along the right-hand arm until the scale is level, then record both distances.');
          var r1 = u.row();
          [[-0.01, '◀ 1 cm'], [-0.001, '◀ 1 mm'], [0.001, '1 mm ▶'], [0.01, '1 cm ▶']].forEach(function (q) {
            r1.appendChild(u.button(q[1], function () { slide(q[0]); }, false, S.hand.busy));
          });
          u.task('Scale level', level(), level() ? 'Level: the moments are equal' : 'Tilted ' + tiltDeg().toFixed(2) + '° ' + (tiltDeg() > 0 ? 'to the right' : 'to the left'));
          u.row(u.button('Record this reading', record, level(), S.hand.busy || !level()));
          u.live(function () { return 'x = ' + (p.x * 100).toFixed(1) + ' cm · y = ' + (p.y * 100).toFixed(1) + ' cm · tilt ' + tiltDeg().toFixed(2) + '°'; });
          u.h3('Observation table'); u.table();
          u.next('Next: move the body', S.rows.length >= 1);
        },
        ok: function () { return S.rows.length >= 1; },
        auto: function () { return balanceAuto().then(function () { record(); }); } },

      { id: 'again', title: 'Other distances', view: 'rig', render: function (u) {
          u.h2('Move the body and balance it again');
          u.p('Hang the body at another distance from the knife edge and find the new balancing position of the known '
            + 'mass. Three readings in all.');
          var r2 = u.row();
          XS.forEach(function (x, i) {
            r2.appendChild(u.button((i === st.xi ? '✓ ' : '') + 'Body at ' + (x * 100).toFixed(1) + ' cm',
              function () { moveBody(i); }, false, S.hand.busy || i === st.xi));
          });
          var r3 = u.row();
          [[-0.01, '◀ 1 cm'], [-0.001, '◀ 1 mm'], [0.001, '1 mm ▶'], [0.01, '1 cm ▶']].forEach(function (q) {
            r3.appendChild(u.button(q[1], function () { slide(q[0]); }, false, S.hand.busy));
          });
          u.row(u.button('Record this reading', record, level(), S.hand.busy || !level()));
          u.live(function () { return 'x = ' + (p.x * 100).toFixed(1) + ' cm · y = ' + (p.y * 100).toFixed(1) + ' cm · ' + (level() ? 'level' : 'tilted ' + tiltDeg().toFixed(2) + '°'); });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 3) u.p(S.rows.length + ' of 3 readings taken.');
          u.next('Next: the mass of the body', S.rows.length >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          var pr = Promise.resolve();
          [1, 2].forEach(function (i) {
            pr = pr.then(function () { return moveBody(i); }).then(balanceAuto).then(function () { record(); });
          });
          return pr;
        } }
    ],

    tick: function (dt) {
      K.step(sim, p, dt);
      pivot.rotation.z = sim.y[0];
      loopL.rotation.z = -sim.y[0];                            // the loops and their loads hang vertically
      loopR.rotation.z = -sim.y[0];
      hudX.set((p.x * 100).toFixed(1) + ' cm');
      hudY.set((p.y * 100).toFixed(1) + ' cm');
      hudT.set(level() ? 'level' : tiltDeg().toFixed(2) + '°');
    }
  };
});
