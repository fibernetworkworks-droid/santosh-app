/* Prayogshala studio module: Young's modulus by uniform bending (B.Sc. properties of matter).
   A rectangular beam rests freely on two hardened knife edges a measured distance apart, and equal loads hang from
   hooks a measured distance beyond each edge. The bending moment between the edges is then the same everywhere, so the
   beam bends into an arc of one radius and its middle rises. A fine pin stands upright on the middle, and a travelling
   microscope on its pillar follows the pin's tip to 0.001 cm.
   The gloved hand hangs the slotted weights on both hooks and runs the microscope's fine screw onto the pin.
   Physics: the `unibend` kernel of the mech_ug pack - δ = 3 m g a L² / (2 Y b d³). Everything is read from the lab's
   params, so a family of beams needs no new rig. */
HoolaStudio.define('uniform-bending', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.unibend;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('unibend');
  p.m = 0;
  var SAMPLE = String((S.lab.variant || {}).sample || '');
  var METALS = [[/brass/i, 'brass', 0xd4ad55, 0.3], [/copper/i, 'copper', 0xc8764a, 0.28],
    [/alumin/i, 'aluminium', 0xcdd2d6, 0.35], [/wood|scale/i, 'wood', 0xd8c08a, 0.62]];
  var BEAM = { name: 'steel', col: 0xb7bcc2, rough: 0.3 };
  METALS.forEach(function (w) { if (w[0].test(SAMPLE)) BEAM = { name: w[1], col: w[2], rough: w[3] }; });
  var km = (S.lab.knobs || []).filter(function (q) { return q.param === 'm'; })[0] || { min: 0, max: 2.5, k: 1 };
  var STEP = 0.5, NW = Math.max(3, Math.round((km.max * (km.k || 1)) / STEP));
  var LC = 1e-5;                                     // the microscope's least count: 0.001 cm
  var st = { n: 0, dims: { b: null, d: null, L: null, a: null }, zero: null, read: null };
  var sim = K.init(p), ready = false;

  // ---------- geometry. The knife edges are at x = ±L/2 and the beam's underside sits at y = BY.
  var BY = 0.1, ZB = -0.12, KE_H = 0.1;
  function L() { return p.L; }
  function A() { return p.a; }
  function delta() { return sim.d; }
  var TOT = L() + 2 * A() + 0.06;

  var tableTop = S.rounded(Math.min(1.9, TOT + 0.2), 0.3, 0.02, 0.006, M.darkWood);
  tableTop.rotation.x = -Math.PI / 2; tableTop.position.set(0, 0.01, ZB); S.scene.add(tableTop);
  S.contact(Math.min(2.0, TOT + 0.26), 0.36, 0, ZB, 0.5);

  var knives = [];
  [-1, 1].forEach(function (s) {
    var g = new T.Group(); S.scene.add(g);
    var blk = S.rounded(0.05, KE_H - 0.02, 0.075, 0.004, M.iron); blk.position.y = (KE_H - 0.02) / 2 + 0.02; g.add(blk);
    var wedge = S.mesh(new T.ConeGeometry(0.012, 0.022, 4), new T.MeshStandardMaterial({ color: 0xd7dbe0, roughness: 0.08, metalness: 1 }));
    wedge.rotation.y = Math.PI / 4; wedge.position.y = KE_H - 0.001; wedge.scale.z = 3.2; g.add(wedge);
    g.position.set(s * L() / 2, 0.02, ZB);
    knives.push(g);
  });

  var beamM = new T.MeshStandardMaterial({ color: BEAM.col, roughness: BEAM.rough, metalness: BEAM.name === 'wood' ? 0.05 : 0.85 });
  var SEG = 72;
  var beamG = new T.BoxGeometry(TOT, p.d, p.b, SEG, 1, 1);
  var basePos = beamG.attributes.position.array.slice();
  var beam = S.mesh(beamG, beamM); beam.position.set(0, BY + p.d / 2, ZB); S.scene.add(beam);
  function shape(x, dl) {                            // the beam's own curve: an arc between the knife edges, straight outside
    var half = L() / 2;
    if (Math.abs(x) <= half) return dl * (1 - (x / half) * (x / half));
    return -(2 * dl / half) * (Math.abs(x) - half);
  }
  function bend() {
    var pos = beam.geometry.attributes.position.array, dl = delta();
    for (var i = 0; i < pos.length; i += 3) pos[i + 1] = basePos[i + 1] + shape(basePos[i], dl);
    beam.geometry.attributes.position.needsUpdate = true;
    beam.geometry.computeVertexNormals();
  }

  // the pin at the middle, and the hangers at the two overhangs
  var pin = S.mesh(new T.CylinderGeometry(0.0007, 0.0004, 0.035, 10), M.chrome, false); S.scene.add(pin);
  var pinFoot = S.mesh(new T.CylinderGeometry(0.004, 0.005, 0.004, 14), M.brass, false); S.scene.add(pinFoot);
  var hangers = [-1, 1].map(function (s) {
    var g = new T.Group(); S.scene.add(g);
    var hook = S.mesh(new T.TorusGeometry(0.008, 0.0016, 8, 20), M.chrome, false); hook.rotation.y = Math.PI / 2; g.add(hook);
    var stem = S.mesh(new T.CylinderGeometry(0.0016, 0.0016, 0.05, 10), M.chrome, false); stem.position.y = -0.03; g.add(stem);
    var plate = S.mesh(new T.CylinderGeometry(0.034, 0.034, 0.008, 28), M.brass); plate.position.y = -0.058; g.add(plate);
    g.userData.discs = [];
    for (var i = 0; i < NW; i++) {
      var dm = S.mesh(new T.CylinderGeometry(0.031, 0.031, 0.013, 28), M.brass); dm.position.y = -0.068 - i * 0.014; dm.visible = false;
      g.add(dm); g.userData.discs.push(dm);
    }
    return g;
  });

  // the travelling microscope
  var MX = 0.16, MZ = 0.12;
  var micro = new T.Group(); S.scene.add(micro);
  var mbase = S.rounded(0.14, 0.12, 0.022, 0.006, new T.MeshStandardMaterial({ color: 0x343a41, roughness: 0.55, metalness: 0.4 }));
  mbase.rotation.x = -Math.PI / 2; mbase.position.y = 0.011; micro.add(mbase);
  var mpill = S.rounded(0.04, 0.04, 0.32, 0.005, new T.MeshStandardMaterial({ color: 0x343a41, roughness: 0.5, metalness: 0.45 }));
  mpill.position.set(0, 0.18, 0); micro.add(mpill);
  var mscale = S.ruler(0.26, { title: 'VERTICAL · mm', labelEvery: 10, width: 0.022, thick: 0.003 });
  mscale.position.set(0, 0.04, 0.021); micro.add(mscale);
  var mcar = new T.Group(); micro.add(mcar);
  var mbody = S.rounded(0.05, 0.05, 0.05, 0.005, new T.MeshStandardMaterial({ color: 0x3d434a, roughness: 0.45, metalness: 0.55 }));
  mcar.add(mbody);
  var mvern = S.rounded(0.02, 0.03, 0.004, 0.002, M.brass); mvern.position.set(0, 0, 0.027); mcar.add(mvern);
  var mtube = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.13, 22), M.black); mtube.rotation.z = Math.PI / 2; mtube.position.set(-0.08, 0, 0); mcar.add(mtube);
  var meye = S.mesh(new T.CylinderGeometry(0.011, 0.012, 0.03, 18), new T.MeshStandardMaterial({ color: 0x17181a, roughness: 0.4 }));
  meye.rotation.z = Math.PI / 2; meye.position.set(0.0, 0, 0); mcar.add(meye);
  var mscrew = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.01, 20), M.brass); mscrew.rotation.z = Math.PI / 2; mscrew.position.set(0.034, -0.03, 0); mcar.add(mscrew);
  mcar.position.set(0, BY + p.d + 0.03, 0);
  micro.position.set(MX, 0, MZ); S.contact(0.18, 0.16, MX, MZ, 0.45);

  // the instrument box on the bench
  var kit = S.rounded(0.22, 0.12, 0.045, 0.006, M.darkWood); kit.position.set(-0.5, 0.023, 0.1); S.scene.add(kit);
  var kitL = S.label('VERNIER · SCREW GAUGE · WEIGHTS', { w: 0.19, ratio: 0.09, color: '#3b2a10', bg: '#f3ecd6' });
  kitL.rotation.x = -Math.PI / 2; kitL.position.set(-0.5, 0.046, 0.1); S.scene.add(kitL);
  S.contact(0.26, 0.16, -0.5, 0.1, 0.4);

  S.addApparatus('beam', beam, BEAM.name.charAt(0).toUpperCase() + BEAM.name.slice(1) + ' beam',
    'Breadth b = ' + (p.b * 100).toFixed(2) + ' cm, depth d = ' + (p.d * 1000).toFixed(2) + ' mm. d comes in cubed, so it is the measurement to be careful with.');
  S.addApparatus('knife', knives[0], 'Knife edges', 'The beam only rests on them. Nothing is clamped, so the ends are free to turn and the bending stays uniform.');
  S.addApparatus('hang', hangers[0], 'Weight hangers', 'Equal loads hang a distance a = ' + (p.a * 100).toFixed(1) + ' cm beyond each knife edge, so the moment between the edges is constant.');
  S.addApparatus('pin', pin, 'Pin at the middle', 'A fine pin standing on the middle of the beam. The microscope follows its tip.');
  S.addApparatus('micro', micro, 'Travelling microscope', 'Reads the pin’s height to ' + (LC * 100).toFixed(4) + ' cm.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudW = S.hudCard('Load on each hanger'), hudD = S.hudCard('Rise of the middle'), hudR = S.hudCard('Microscope');

  // ---------- state
  function load() { return st.n * STEP; }
  function setLoad(n) {
    if (S.hand.busy) return Promise.resolve();
    if (n < 0 || n > NW) return Promise.resolve();
    var from = new T.Vector3(-0.5, 0.08, 0.1);
    var to = new T.Vector3(-(L() / 2 + A()), 0.02, ZB);
    var old = st.n;
    return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); }, function (k) {
      if (k > 0.8) { st.n = n; p.m = load(); }
    }, { ms: 800, hold: 200, mode: 'side' }).then(function () {
      st.n = n; p.m = load();
      hangers.forEach(function (g) { g.userData.discs.forEach(function (dm, i) { dm.visible = i < st.n; }); });
      S.advance(6, function () { return Math.abs(sim.d - K.measure(p).delta_eq) < 1e-9; });
      st.read = null;
      S.say(st.n === 0 ? 'Both hangers unloaded.' : (load() * 1000).toFixed(0) + ' g on each hanger. Wait for the beam to settle, then read the pin.');
      if (old !== n) S.render();
      return Promise.resolve();
    });
  }
  function measureDim(which) {
    var v = { b: p.b, d: p.d, L: p.L, a: p.a }[which];
    st.dims[which] = v;
    var txt = which === 'b' ? 'Breadth b = ' + (v * 100).toFixed(2) + ' cm (vernier calliper)'
      : which === 'd' ? 'Depth d = ' + (v * 1000).toFixed(2) + ' mm (screw gauge, mean of five places)'
        : which === 'L' ? 'Knife edges L = ' + (v * 100).toFixed(1) + ' cm apart'
          : 'Overhang a = ' + (v * 100).toFixed(1) + ' cm';
    S.say(txt);
    if (ready) S.render();
  }
  function dimsDone() { return st.dims.b !== null && st.dims.d !== null && st.dims.L !== null && st.dims.a !== null; }

  function readPin() {
    if (S.hand.busy) return Promise.resolve();
    if (!dimsDone()) { S.say('Measure the beam and the distances first.'); return Promise.resolve(); }
    var from = new T.Vector3(MX + 0.05, mcar.position.y + 0.02, MZ + 0.02);
    return S.hand.pinchMove(from, function (k) { return from.clone().lerp(from.clone().add(new T.Vector3(0, 0.012, 0)), k); },
      function () {}, { ms: 600, hold: 150, mode: 'side' }).then(function () {
        var pinTop = BY + p.d + shape(0, delta()) + 0.035;
        var r = Math.floor(pinTop / LC + 0.5) * LC;
        st.read = r;
        if (st.n === 0) { st.zero = r; S.say('Zero reading with no load: ' + (r * 100).toFixed(4) + ' cm.'); }
        else S.say('Microscope reads ' + (r * 100).toFixed(4) + ' cm.');
        S.render();
      });
  }
  function recordRow() {
    if (st.read === null) { S.say('Read the pin with the microscope first.'); return; }
    if (st.zero === null) { S.say('Take the zero reading with no load first.'); return; }
    if (st.n === 0) { S.say('The no-load reading is the zero, not a row of the table.'); return; }
    var d = st.read - st.zero;
    if (d <= 0) { S.say('The middle has not risen. Check the loads are on both hangers.'); return; }
    S.addRow({ m: load(), delta: d });
    S.say('Written in your record book: ' + (load() * 1000).toFixed(0) + ' g on each hanger, rise δ = ' + (d * 1000).toFixed(3) + ' mm.');
    st.read = null;
    S.render();
  }
  function loadsDone() { var o = {}; S.rows.forEach(function (r) { o[r.m.toFixed(2)] = 1; }); return Object.keys(o).length; }

  bend();

  var EXP = {
    camera: { pos: [0.42, 0.5, 0.95], look: [0.0, 0.1, -0.1] },
    views: {
      setup: [[0.4, 0.48, 0.92], [0.0, 0.1, -0.1]],
      beam: [[0.3, 0.34, 0.55], [0.0, 0.12, -0.1]],
      knife: [[-0.18, 0.28, 0.3], [-L() / 2, 0.1, -0.12]],
      hang: [[-0.3, 0.3, 0.46], [-(L() / 2 + A()), 0.04, -0.12]],
      micro: [[0.42, 0.33, 0.5], [MX - 0.02, 0.17, 0.0]],
      pin: [[0.2, 0.25, 0.32], [0.0, 0.14, -0.06]],
      book: [[-0.34, 0.5, 0.56], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'With equal loads hanging beyond the two knife edges, the bending moment everywhere between them is the '
        + 'same, so the beam bends into an arc of one radius. The middle therefore rises above the line of the knife edges '
        + 'by an amount that can be measured with a travelling microscope.',
      formula: 'δ = 3 m g a L² / (2 Y b d³)',
      formulaNote: 'so Y = 3 m g a L² / (2 b d³ δ), with b = ' + (p.b * 100).toFixed(2) + ' cm, d = '
        + (p.d * 1000).toFixed(2) + ' mm, L = ' + (p.L * 100).toFixed(1) + ' cm, a = ' + (p.a * 100).toFixed(1) + ' cm',
      more: ['δ is proportional to the load, so the δ-against-m graph is a straight line through the origin and Y follows from its slope.',
        'The depth comes in as d³: a 1 % error in d gives a 3 % error in Y. Measure d with a screw gauge at five places and average.',
        'Load and then unload in the same steps. If the two sets of readings do not agree, the beam has been strained past its elastic limit.'],
      precautions: 'Add and remove the loads on both hangers together, or the beam tips off its knife edges. Let the beam '
        + 'settle before each reading, and always turn the microscope’s screw the same way.'
    },
    book: {
      title: 'Expt. — Young’s modulus by uniform bending',
      lines: ['Aim: to find Young’s modulus of the ' + BEAM.name + ' beam.',
        'b = ' + (p.b * 100).toFixed(2) + ' cm, d = ' + (p.d * 1000).toFixed(2) + ' mm',
        'L = ' + (p.L * 100).toFixed(1) + ' cm, a = ' + (p.a * 100).toFixed(1) + ' cm',
        'Microscope L.C. = ' + (LC * 100).toFixed(4) + ' cm', 'δ = (loaded reading) − (zero reading)',
        'Y = 3 m g a L² / (2 b d³ δ)'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'm (kg)', get: function (r) { return r.m.toFixed(1); } },
        { label: 'δ (mm)', get: function (r) { return (r.delta * 1000).toFixed(3); } },
        { label: 'm/δ (kg/mm)', get: function (r) { return (r.m / (r.delta * 1000)).toFixed(2); } }]
    },
    graph: {
      x: function (r) { return r.m; }, y: function (r) { return r.delta * 1000; },
      xlabel: 'm (kg)', ylabel: 'δ (mm)', x0: 0, y0: 0,
      line: function (pts) { var s = S.fit.origin(pts); return function (x) { return s * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var v = HK.CALCS.uni_Y.fn(rows, p);
      if (!isFinite(v) || v <= 0) return null;
      return { label: 'Y of the ' + BEAM.name + ' beam', value: v, unit: 'Pa', digits: 0, truth: p.Y,
        note: 'Mean of 3 m g a L² / (2 b d³ δ) over the loads used.' };
    },
    tol: 0.02,
    chips: ['Why is this called uniform bending?', 'Why does the depth matter most?', 'Check my readings',
      'Why is the beam not clamped?', 'What if the loads are unequal?'],
    viva: [['In uniform bending the bending moment between the knife edges is', ['the same everywhere', 'greatest at the middle', 'zero'], 0,
      'Equal loads beyond the supports give a constant moment W a.'],
      ['A 1 % error in the depth d gives an error in Y of about', ['3 %', '1 %', '0.3 %'], 0, 'Y goes as 1/d³.']],
    askState: function () {
      return {
        load_on_each_hanger_kg: load(), rise_of_middle_mm: +(delta() * 1000).toFixed(4),
        zero_reading_cm: st.zero === null ? null : +(st.zero * 100).toFixed(4),
        last_reading_cm: st.read === null ? null : +(st.read * 100).toFixed(4),
        measured_b_cm: st.dims.b === null ? null : +(st.dims.b * 100).toFixed(2),
        measured_d_mm: st.dims.d === null ? null : +(st.dims.d * 1000).toFixed(2),
        knife_edge_separation_cm: st.dims.L === null ? null : +(st.dims.L * 100).toFixed(1),
        overhang_cm: st.dims.a === null ? null : +(st.dims.a * 100).toFixed(1),
        beam_material: BEAM.name
      };
    },

    steps: [
      { id: 'dims', title: 'Measure the beam', view: 'beam',
        render: function (u) {
          u.h2('Measure the beam and the distances');
          u.p('Three of these four numbers come into the answer as powers, so take them carefully before any load goes on.');
          [['b', 'Breadth b (vernier calliper)', function () { return (p.b * 100).toFixed(2) + ' cm'; }],
            ['d', 'Depth d (screw gauge, five places)', function () { return (p.d * 1000).toFixed(2) + ' mm'; }],
            ['L', 'Knife edges L apart (metre scale)', function () { return (p.L * 100).toFixed(1) + ' cm'; }],
            ['a', 'Overhang a of each load', function () { return (p.a * 100).toFixed(1) + ' cm'; }]].forEach(function (q) {
              u.task(q[1], st.dims[q[0]] !== null, st.dims[q[0]] !== null ? q[2]() : 'Not measured yet')
                .add(u.button('Measure', function () { measureDim(q[0]); }, st.dims[q[0]] === null, st.dims[q[0]] !== null));
            });
          u.formula('Y = 3 m g a L² / (2 b d³ δ)');
          u.next('Next: load it and read the pin', dimsDone());
        },
        ok: function () { return dimsDone(); },
        auto: function () { ['b', 'd', 'L', 'a'].forEach(measureDim); return Promise.resolve(); } },

      { id: 'load', title: 'Load and read', view: 'micro',
        render: function (u) {
          u.h2('Load both hangers and read the rise');
          u.p('Take the zero reading with no load. Then add equal weights to both hangers, let the beam settle, and read '
            + 'the pin each time. The rise δ is the difference from the zero reading.');
          var r = u.row();
          for (var n = 0; n <= NW; n++) {
            (function (nn) {
              r.appendChild(u.button((nn * STEP).toFixed(1) + ' kg' + (st.n === nn ? ' ✓' : ''), function () { setLoad(nn).then(function () { S.focus('hang'); }); }, st.n === nn, S.hand.busy));
            })(n);
          }
          u.task('Zero reading (no load)', st.zero !== null, st.zero !== null ? (st.zero * 100).toFixed(4) + ' cm' : 'Not taken yet')
            .add(u.button('Take it', function () { setLoad(0).then(readPin); }, st.zero === null, S.hand.busy || st.zero !== null));
          u.row(u.button('Read the pin', function () { S.focus('pin'); readPin(); }, st.read === null, S.hand.busy || !dimsDone()),
            u.button('Write this reading down', function () { recordRow(); }, true, S.hand.busy || st.read === null || st.n === 0));
          u.live(function () {
            return (load() * 1000).toFixed(0) + ' g on each hanger · rise ' + (delta() * 1000).toFixed(3) + ' mm'
              + (st.read === null ? '' : ' · reading ' + (st.read * 100).toFixed(4) + ' cm');
          });
          u.h3('Observation table'); u.table();
          var n = loadsDone();
          u.next('Next: work out Y', n >= 3);
          if (n < 3) u.p(n + ' of at least 3 loads recorded.');
        },
        ok: function () { return loadsDone() >= 3; },
        auto: function () {
          var seq = setLoad(0).then(readPin);
          for (var n = 2; n <= NW; n++) {
            (function (nn) { seq = seq.then(function () { return setLoad(nn); }).then(readPin).then(function () { recordRow(); }); })(n);
          }
          return seq;
        } }
    ],

    tick: function (dt) {
      K.step(sim, p, dt);
      bend();
      pose();
    },
    ready: function () { ready = true; }
  };
  function pose() {
    var dl = delta();
    var yTop = BY + p.d + shape(0, dl);
    pin.position.set(0, yTop + 0.0175, ZB); pinFoot.position.set(0, yTop + 0.002, ZB);
    hangers.forEach(function (g, i) {
      var s = i === 0 ? -1 : 1, x = s * (L() / 2 + A());
      g.position.set(x, BY + shape(x, dl) - 0.006, ZB);
    });
    mcar.position.y = yTop + 0.03;
    hudW.set((load() * 1000).toFixed(0) + ' g');
    hudD.set((dl * 1000).toFixed(3) + ' mm');
    hudR.set(st.read === null ? '—' : (st.read * 100).toFixed(4) + ' cm');
  }
  pose();
  return EXP;
});
