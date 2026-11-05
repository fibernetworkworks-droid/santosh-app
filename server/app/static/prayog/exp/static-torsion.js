/* Prayogshala studio module: modulus of rigidity by the statical (Barton's) method (B.Sc. properties of matter).
   A cast-iron bed carries a fixed chuck at one end and two bearings; the rod under test runs between them and ends in a
   torsion wheel. Two cords leave opposite sides of the wheel, pass over pulleys and carry equal scale pans, so the rod
   feels a pure couple and is twisted but not bent. A light pointer fixed to the wheel reads the twist on a printed
   circular scale graduated in degrees.
   The gloved hand puts equal weights on both pans and reads the circular scale.
   Physics: the `stattorsion` kernel of the mech_ug pack - θ = 4 m g a L / (π η r⁴). All numbers come from the lab's params. */
HoolaStudio.define('static-torsion', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.stattorsion;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('stattorsion');
  p.m = 0;
  var SAMPLE = String((S.lab.variant || {}).sample || '');
  var METALS = [[/brass/i, 'brass', 0xd4ad55, 0.3], [/copper/i, 'copper', 0xc8764a, 0.28], [/alumin/i, 'aluminium', 0xcdd2d6, 0.35]];
  var ROD = { name: 'steel', col: 0xc3c8ce, rough: 0.25 };
  METALS.forEach(function (w) { if (w[0].test(SAMPLE)) ROD = { name: w[1], col: w[2], rough: w[3] }; });
  var STEP = 0.2, NW = 5, LCDEG = 0.1;
  var st = { n: 0, dims: { d: null, L: null, a: null }, zeroed: false, read: null };
  var sim = K.init(p), ready = false;

  // ---------- geometry: the rod runs along x at y = RY, z = ZB; the wheel is at the right-hand end
  var RY = 0.11, ZB = -0.12, WX = 0.3, WR = Math.max(0.03, p.a), RODX0 = -0.3;
  var bed = S.rounded(0.95, 0.2, 0.03, 0.006, new T.MeshStandardMaterial({ color: 0x3a4149, roughness: 0.6, metalness: 0.35 }));
  bed.rotation.x = -Math.PI / 2; bed.position.set(0, 0.015, ZB); S.scene.add(bed);
  S.contact(1.0, 0.26, 0, ZB, 0.55);
  var chuck = new T.Group(); S.scene.add(chuck);
  var cb = S.rounded(0.07, 0.1, 0.09, 0.006, M.iron); cb.position.y = RY - 0.02; chuck.add(cb);
  var cj = S.mesh(new T.CylinderGeometry(0.024, 0.024, 0.03, 24), M.brass); cj.rotation.z = Math.PI / 2; cj.position.set(0.04, RY, 0); chuck.add(cj);
  [-1, 1].forEach(function (s) {
    var t2 = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.03, 12), M.chrome); t2.position.set(0.04, RY + s * 0.02, 0.016); t2.rotation.x = Math.PI / 2; chuck.add(t2);
  });
  chuck.position.set(RODX0 - 0.06, 0.03, ZB);

  var rodM = new T.MeshStandardMaterial({ color: ROD.col, roughness: ROD.rough, metalness: 0.9 });
  var rod = S.mesh(new T.CylinderGeometry(Math.max(0.0025, p.rr), Math.max(0.0025, p.rr), WX - RODX0 + 0.05, 28), rodM);
  rod.rotation.z = Math.PI / 2; rod.position.set((RODX0 + WX) / 2 + 0.02, RY, ZB); S.scene.add(rod);
  [-0.08, 0.14].forEach(function (bx) {
    var g = new T.Group(); S.scene.add(g);
    var bb = S.rounded(0.045, 0.09, 0.07, 0.005, M.iron); bb.position.y = RY - 0.025; g.add(bb);
    var br = S.mesh(new T.TorusGeometry(0.014, 0.004, 8, 24), M.chrome, false); br.rotation.y = Math.PI / 2; br.position.y = RY; g.add(br);
    g.position.set(bx, 0.03, ZB);
  });

  // the torsion wheel, its pointer and the printed circular scale
  var dialTex = S.canvasTex(640, 640, function (x, w, h) {
    var c = w / 2, R = w * 0.46;
    x.fillStyle = '#f7f4ea'; x.beginPath(); x.arc(c, c, R, 0, Math.PI * 2); x.fill();
    x.strokeStyle = '#1b1b1d'; x.fillStyle = '#1b1b1d'; x.lineWidth = 2;
    for (var i = 0; i < 360; i += 2) {
      var a = (i - 90) * Math.PI / 180, big = i % 30 === 0, mid = i % 10 === 0;
      var r0 = R - (big ? 34 : mid ? 22 : 12);
      x.lineWidth = big ? 3 : mid ? 2 : 1;
      x.beginPath(); x.moveTo(c + Math.cos(a) * R, c + Math.sin(a) * R); x.lineTo(c + Math.cos(a) * r0, c + Math.sin(a) * r0); x.stroke();
      if (big) { x.font = '600 26px "Public Sans", sans-serif'; x.textAlign = 'center';
        x.fillText(String(i), c + Math.cos(a) * (R - 52), c + Math.sin(a) * (R - 52) + 9); }
    }
    x.font = '600 24px "Public Sans", sans-serif'; x.textAlign = 'center';
    x.fillText('DEGREES · L.C. 0.1°', c, c + 56);
  });
  var dial = new T.Mesh(new T.CircleGeometry(WR + 0.035, 64), new T.MeshStandardMaterial({ map: dialTex, roughness: 0.55 }));
  dial.rotation.y = Math.PI / 2; dial.position.set(WX + 0.016, RY, ZB); S.scene.add(dial);
  var dialRim = S.mesh(new T.TorusGeometry(WR + 0.035, 0.0035, 8, 48), M.iron, false); dialRim.rotation.y = Math.PI / 2;
  dialRim.position.set(WX + 0.016, RY, ZB); S.scene.add(dialRim);
  var dpost = S.mesh(new T.CylinderGeometry(0.008, 0.01, RY - 0.03, 16), M.chrome); dpost.position.set(WX + 0.016, (RY - 0.03) / 2 + 0.03, ZB - WR - 0.03); S.scene.add(dpost);

  var wheel = new T.Group(); S.scene.add(wheel);
  var wrim = S.mesh(new T.CylinderGeometry(WR, WR, 0.012, 48), M.brass); wrim.rotation.z = Math.PI / 2; wheel.add(wrim);
  var whub = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.03, 20), M.brass); whub.rotation.z = Math.PI / 2; wheel.add(whub);
  var ptr = S.mesh(new T.BoxGeometry(0.003, WR + 0.03, 0.003), new T.MeshStandardMaterial({ color: 0xc0392b, roughness: 0.4 }), false);
  ptr.position.set(0.012, (WR + 0.03) / 2 - 0.005, 0); wheel.add(ptr);
  wheel.position.set(WX, RY, ZB);

  // the two cords, pulleys and pans
  var cordM = new T.MeshStandardMaterial({ color: 0x6b6253, roughness: 0.95 });
  var PUX = WX + 0.13;
  var pans = [-1, 1].map(function (s) {
    var pz = ZB + s * WR;
    var pul = new T.Group(); S.scene.add(pul);
    var pw = S.mesh(new T.TorusGeometry(0.018, 0.005, 10, 26), M.chrome, false); pw.rotation.y = Math.PI / 2; pul.add(pw);
    var pb = S.mesh(new T.BoxGeometry(0.02, 0.05, 0.016), M.iron); pb.position.y = -0.035; pul.add(pb);
    var pp = S.mesh(new T.CylinderGeometry(0.008, 0.009, RY - 0.03, 14), M.chrome); pp.position.y = -0.06 - (RY - 0.03) / 2; pul.add(pp);
    pul.position.set(PUX, RY + 0.02, pz);
    S.contact(0.06, 0.06, PUX, pz, 0.35);
    var cordTop = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 1, 8), cordM, false); S.scene.add(cordTop);
    var cordDown = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 1, 8), cordM, false); S.scene.add(cordDown);
    var pan = new T.Group(); S.scene.add(pan);
    var plate = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.007, 26), M.brass); pan.add(plate);
    var discs = [];
    for (var i = 0; i < NW; i++) { var dm = S.mesh(new T.CylinderGeometry(0.027, 0.027, 0.012, 26), M.brass); dm.position.y = 0.009 + i * 0.013; dm.visible = false; pan.add(dm); discs.push(dm); }
    pan.position.set(PUX + 0.02, 0.02, pz);
    return { z: pz, cordTop: cordTop, cordDown: cordDown, pan: pan, discs: discs, pulley: pul };
  });

  var kit = S.rounded(0.22, 0.12, 0.045, 0.006, M.darkWood); kit.position.set(-0.46, 0.023, 0.1); S.scene.add(kit);
  var kitL = S.label('WEIGHT BOX · SCREW GAUGE', { w: 0.18, ratio: 0.1, color: '#3b2a10', bg: '#f3ecd6' });
  kitL.rotation.x = -Math.PI / 2; kitL.position.set(-0.46, 0.046, 0.1); S.scene.add(kitL);
  S.contact(0.26, 0.16, -0.46, 0.1, 0.4);

  S.addApparatus('rod', rod, ROD.name.charAt(0).toUpperCase() + ROD.name.slice(1) + ' rod',
    'Radius r = ' + (p.rr * 1000).toFixed(2) + ' mm. It comes into the answer as r⁴, so measure it with a screw gauge at several places.');
  S.addApparatus('wheel', wheel, 'Torsion wheel', 'Radius a = ' + (p.a * 100).toFixed(1) + ' cm. Two cords leave opposite sides, so the pull is a pure couple 2 m g a.');
  S.addApparatus('dial', dial, 'Circular scale', 'Graduated in degrees, read to 0.1°. The pointer on the wheel reads the twist directly.');
  S.addApparatus('pan', pans[0].pan, 'Scale pans', 'Equal weights go on both pans. An unequal load would bend the rod as well as twist it.');
  S.addApparatus('chuck', chuck, 'Fixed chuck', 'Grips one end of the rod so it cannot turn: the twist is measured from here.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudW = S.hudCard('Weight on each pan'), hudT = S.hudCard('Twist'), hudC = S.hudCard('Couple');

  // ---------- state
  function load() { return st.n * STEP; }
  function settle() { S.advance(8, function () { return Math.abs(sim.th - K.measure(p).theta_eq) < 1e-9; }); }
  function setLoad(n) {
    if (S.hand.busy) return Promise.resolve();
    if (n < 0 || n > NW) return Promise.resolve();
    var from = new T.Vector3(-0.46, 0.08, 0.1), to = new T.Vector3(PUX + 0.02, 0.06, pans[0].z);
    return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); }, function (k) {
      if (k > 0.85) { st.n = n; p.m = load(); }
    }, { ms: 900, hold: 200, mode: 'side' }).then(function () {
      st.n = n; p.m = load();
      pans.forEach(function (q) { q.discs.forEach(function (dm, i) { dm.visible = i < st.n; }); });
      settle(); st.read = null;
      S.say(st.n === 0 ? 'Both pans empty.' : (load() * 1000).toFixed(0) + ' g on each pan. Let the pointer come to rest, then read the scale.');
      S.render();
      return Promise.resolve();
    });
  }
  function measureDim(which) {
    st.dims[which] = { d: p.rr * 2, L: p.Lr, a: p.a }[which];
    S.say(which === 'd' ? 'Rod diameter ' + (p.rr * 2000).toFixed(2) + ' mm (screw gauge), so r = ' + (p.rr * 1000).toFixed(2) + ' mm.'
      : which === 'L' ? 'Twisted length L = ' + (p.Lr * 100).toFixed(1) + ' cm, from the chuck to the wheel.'
        : 'Wheel radius a = ' + (p.a * 100).toFixed(1) + ' cm.');
    if (ready) S.render();
  }
  function dimsDone() { return st.dims.d !== null && st.dims.L !== null && st.dims.a !== null; }
  function setZero() {
    if (st.n !== 0) { S.say('Take the pans off before zeroing the pointer.'); return Promise.resolve(); }
    st.zeroed = true; S.say('Pointer set to zero on the circular scale with both pans empty.');
    if (ready) S.render();
    return Promise.resolve();
  }
  function readDial() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.zeroed) { S.say('Set the pointer to zero first, with no load.'); return Promise.resolve(); }
    var deg = sim.th * 180 / Math.PI;
    st.read = Math.floor(deg / LCDEG + 0.5) * LCDEG;
    S.say('Circular scale reads ' + st.read.toFixed(1) + '°.');
    S.render();
    return Promise.resolve();
  }
  function recordRow() {
    if (st.read === null) { S.say('Read the circular scale first.'); return; }
    if (st.n === 0) { S.say('With no load there is nothing to record: that reading is the zero.'); return; }
    S.addRow({ m: load(), theta: st.read * Math.PI / 180, deg: st.read });
    S.say('Written in your record book: ' + (load() * 1000).toFixed(0) + ' g on each pan, twist ' + st.read.toFixed(1) + '°.');
    st.read = null; S.render();
  }
  function loadsDone() { var o = {}; S.rows.forEach(function (r) { o[r.m.toFixed(2)] = 1; }); return Object.keys(o).length; }

  var EXP = {
    camera: { pos: [0.55, 0.52, 0.92], look: [0.02, 0.1, -0.1] },
    views: {
      setup: [[0.52, 0.5, 0.9], [0.02, 0.1, -0.1]],
      dial: [[0.62, 0.26, 0.34], [WX + 0.02, 0.11, -0.12]],
      wheel: [[0.5, 0.3, 0.4], [WX, 0.11, -0.12]],
      rod: [[0.0, 0.34, 0.48], [-0.05, 0.11, -0.12]],
      pan: [[0.58, 0.22, 0.42], [PUX, 0.05, -0.12]],
      chuck: [[-0.2, 0.3, 0.36], [RODX0 - 0.04, 0.1, -0.12]],
      book: [[-0.34, 0.5, 0.56], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'Two equal weights hanging from cords that leave opposite sides of a wheel apply a couple to the end of '
        + 'the rod and no resultant force at all, so the rod is twisted and not bent. The steady twist is proportional to '
        + 'the couple as long as the rod stays elastic.',
      formula: 'θ = 2 τ L / (π η r⁴),  τ = 2 m g a',
      formulaNote: 'so η = 4 m g a L / (π r⁴ θ), with r = ' + (p.rr * 1000).toFixed(2) + ' mm, L = '
        + (p.Lr * 100).toFixed(1) + ' cm and a = ' + (p.a * 100).toFixed(1) + ' cm',
      more: ['θ is proportional to the load: the θ-against-m graph is a straight line through the origin, and η follows from its slope.',
        'The radius comes in as r⁴. A rod of half the radius twists sixteen times as far under the same couple.',
        'Load and then unload in the same steps. If the pointer does not come back to zero, the rod has been overstrained and the readings are worthless.'],
      precautions: 'Keep the two pans equally loaded at every stage. Let the pointer come fully to rest before reading, '
        + 'and read it square on to the scale so that parallax does not creep in.'
    },
    book: {
      title: 'Expt. — Statical torsion',
      lines: ['Aim: to find the modulus of rigidity of the ' + ROD.name + ' rod.',
        'r = ' + (p.rr * 1000).toFixed(2) + ' mm (screw gauge), L = ' + (p.Lr * 100).toFixed(1) + ' cm',
        'Wheel radius a = ' + (p.a * 100).toFixed(1) + ' cm', 'Couple τ = 2 m g a',
        'η = 4 m g a L / (π r⁴ θ)', 'Circular scale L.C. 0.1°.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'm (g)', get: function (r) { return (r.m * 1000).toFixed(0); } },
        { label: 'θ (°)', get: function (r) { return r.deg.toFixed(1); } },
        { label: 'θ (rad)', get: function (r) { return r.theta.toFixed(4); } },
        { label: 'm/θ', get: function (r) { return (r.m / r.theta).toFixed(2); } }]
    },
    graph: {
      x: function (r) { return r.m * 1000; }, y: function (r) { return r.deg; },
      xlabel: 'm (g)', ylabel: 'θ (°)', x0: 0, y0: 0,
      line: function (pts) { var s = S.fit.origin(pts); return function (x) { return s * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var v = HK.CALCS.stat_eta.fn(rows, p);
      if (!isFinite(v) || v <= 0) return null;
      return { label: 'η of the ' + ROD.name + ' rod', value: v, unit: 'Pa', digits: 0, truth: p.eta,
        note: 'Mean of 4 m g a L / (π r⁴ θ) over the loads used.' };
    },
    tol: 0.02,
    chips: ['Why are two cords used?', 'Why does the radius matter so much?', 'Check my readings',
      'What if the pointer does not return to zero?', 'Why read the scale square on?'],
    viva: [['Two cords on opposite sides of the wheel are used in order to apply',
      ['a pure couple, with no resultant force', 'twice the weight', 'a bending moment'], 0,
      'Two equal opposite pulls have zero resultant but a couple 2 m g a.'],
      ['A rod of half the radius, under the same couple, twists', ['16 times as far', '4 times as far', 'twice as far'], 0,
        'θ goes as 1/r⁴.']],
    askState: function () {
      return {
        weight_on_each_pan_kg: load(), couple_N_m: +(2 * load() * p.g * p.a).toFixed(5),
        twist_now_deg: +(sim.th * 180 / Math.PI).toFixed(2), last_reading_deg: st.read,
        pointer_zeroed: st.zeroed, rod_diameter_mm: st.dims.d === null ? null : +(st.dims.d * 1000).toFixed(2),
        twisted_length_cm: st.dims.L === null ? null : +(st.dims.L * 100).toFixed(1),
        wheel_radius_cm: st.dims.a === null ? null : +(st.dims.a * 100).toFixed(1), rod_material: ROD.name
      };
    },

    steps: [
      { id: 'dims', title: 'Measure and zero', view: 'rod',
        render: function (u) {
          u.h2('Measure the rod and zero the pointer');
          u.p('The radius comes into the answer as the fourth power, so it is measured with a screw gauge at several '
            + 'places along the rod and in two directions at each.');
          [['d', 'Rod diameter (screw gauge)', function () { return (p.rr * 2000).toFixed(2) + ' mm'; }],
            ['L', 'Twisted length L (metre scale)', function () { return (p.Lr * 100).toFixed(1) + ' cm'; }],
            ['a', 'Wheel radius a', function () { return (p.a * 100).toFixed(1) + ' cm'; }]].forEach(function (q) {
              u.task(q[1], st.dims[q[0]] !== null, st.dims[q[0]] !== null ? q[2]() : 'Not measured yet')
                .add(u.button('Measure', function () { measureDim(q[0]); }, st.dims[q[0]] === null, st.dims[q[0]] !== null));
            });
          u.task('Set the pointer to zero (pans empty)', st.zeroed, st.zeroed ? 'Zeroed' : 'Not zeroed')
            .add(u.button('Set to zero', function () { S.focus('dial'); setZero(); }, !st.zeroed, S.hand.busy || st.zeroed));
          u.formula('η = 4 m g a L / (π r⁴ θ)');
          u.next('Next: load both pans', dimsDone() && st.zeroed);
        },
        ok: function () { return dimsDone() && st.zeroed; },
        auto: function () { ['d', 'L', 'a'].forEach(measureDim); return setZero(); } },

      { id: 'load', title: 'Load and read', view: 'dial',
        render: function (u) {
          u.h2('Load both pans equally and read the twist');
          u.p('Put the same weight on each pan, wait for the pointer to come to rest, and read the circular scale. '
            + 'Then add the next weight.');
          var r = u.row();
          for (var n = 0; n <= NW; n++) {
            (function (nn) {
              r.appendChild(u.button((nn * STEP).toFixed(1) + ' kg' + (st.n === nn ? ' ✓' : ''), function () { setLoad(nn).then(function () { S.focus('dial'); }); }, st.n === nn, S.hand.busy));
            })(n);
          }
          u.row(u.button('Read the circular scale', function () { readDial(); }, st.read === null, S.hand.busy || !st.zeroed),
            u.button('Write this reading down', function () { recordRow(); }, true, S.hand.busy || st.read === null || st.n === 0));
          u.live(function () {
            return (load() * 1000).toFixed(0) + ' g on each pan · couple ' + (2 * load() * p.g * p.a).toFixed(4)
              + ' N·m · twist ' + (sim.th * 180 / Math.PI).toFixed(2) + '°';
          });
          u.h3('Observation table'); u.table();
          var n = loadsDone();
          u.next('Next: work out η', n >= 3);
          if (n < 3) u.p(n + ' of at least 3 loads recorded.');
        },
        ok: function () { return loadsDone() >= 3; },
        auto: function () {
          var seq = Promise.resolve();
          for (var n = 1; n <= NW; n++) {
            (function (nn) { seq = seq.then(function () { return setLoad(nn); }).then(readDial).then(function () { recordRow(); }); })(n);
          }
          return seq;
        } }
    ],

    tick: function (dt) { K.step(sim, p, dt); pose(); },
    ready: function () { ready = true; }
  };
  function pose() {
    wheel.rotation.x = sim.th;
    pans.forEach(function (q, i) {
      var drop = sim.th * p.a * (i === 0 ? 1 : -1);
      var yTop = RY + 0.02, yPan = 0.02 - drop * 0 + Math.max(-0.01, Math.min(0.01, -drop));
      q.pan.position.set(PUX + 0.02, Math.max(0.012, yPan), q.z);
      var yA = RY, yB = q.pan.position.y + 0.02;
      q.cordDown.scale.y = Math.max(0.001, yTop - yB);
      q.cordDown.position.set(PUX + 0.02, (yTop + yB) / 2, q.z);
      q.cordTop.rotation.z = Math.PI / 2;
      q.cordTop.scale.y = Math.max(0.001, PUX - WX);
      q.cordTop.position.set((PUX + WX) / 2, yA + p.a * (i === 0 ? 1 : -1) * 0 + 0.02, q.z);
    });
    hudW.set((load() * 1000).toFixed(0) + ' g');
    hudT.set((sim.th * 180 / Math.PI).toFixed(2) + '°');
    hudC.set((2 * load() * p.g * p.a).toFixed(4) + ' N·m');
  }
  pose();
  return EXP;
});
