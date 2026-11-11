/* Prayogshala studio module: moment of inertia of a flywheel (B.Sc. mechanics).
   A heavy cast-iron flywheel with four spokes turns in ball bearings on a wall plate. A cord is wound a measured number
   of turns on its axle and carries a hanger of slotted weights; a chalk mark on the rim is what you count rotations
   against, a steel tape beside the hanger measures the drop, and a digital stopwatch times the fall.
   The gloved hand winds the cord on the axle and sets the hanger free; the same press starts the stopwatch.
   Physics: the `flywheel` kernel of the mech_ug pack - a constant couple while the mass falls, friction alone after the
   cord slips off, so m g h = ½ m v² + ½ I ω² (1 + n/N). Everything is read from the lab's params. */
HoolaStudio.define('flywheel-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.flywheel;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('flywheel');
  var km = (S.lab.knobs || []).filter(function (q) { return q.param === 'm'; })[0] || { min: 0.2, max: 1.0, k: 1 };
  var MASSES = [0, 1, 2].map(function (i) {
    return Math.round((km.min * (km.k || 1) + (km.max - km.min) * (km.k || 1) * (i === 0 ? 0 : i === 1 ? 0.5 : 1)) * 100) / 100;
  });
  var kn = (S.lab.knobs || []).filter(function (q) { return q.param === 'n'; })[0] || { min: 3, max: 8, k: 1 };
  var NMIN = Math.round(kn.min * (kn.k || 1)), NMAX = Math.round(kn.max * (kn.k || 1));
  var st = { mi: 1, wound: false, running: false, stoppedAt: null, rot: 0, axleRead: null };
  p.m = MASSES[st.mi];
  var sim = K.init(p), ready = false, prevRot = 0;

  // ---------- geometry: the wheel turns about the z axis at (XW, YW, ZW); the cord hangs off the axle at x = XW + ra
  var XW = 0.0, YW = 0.62, ZW = -0.24, RW = 0.16, RA = Math.max(0.008, p.ra);
  function phi() { return 2 * Math.PI * p.n; }
  function hDrop() { return RA * phi(); }

  var plate = new T.Group(); S.scene.add(plate);
  var back = S.rounded(0.4, 0.78, 0.028, 0.012, M.iron); back.position.set(XW - 0.02, YW - 0.08, ZW - 0.1); plate.add(back);
  var brkt = S.rounded(0.09, 0.11, 0.1, 0.01, M.iron); brkt.position.set(XW, YW, ZW - 0.055); plate.add(brkt);
  var bear = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.03, 24), M.chrome); bear.rotation.x = Math.PI / 2; bear.position.set(XW, YW, ZW - 0.012); plate.add(bear);
  var stand = S.mesh(new T.CylinderGeometry(0.025, 0.03, YW - 0.44, 20), M.chrome); stand.position.set(XW - 0.02, (YW - 0.44) / 2 + 0.02, ZW - 0.1); plate.add(stand);
  var sfoot = S.rounded(0.34, 0.24, 0.03, 0.01, M.iron); sfoot.rotation.x = -Math.PI / 2; sfoot.position.set(XW - 0.02, 0.015, ZW - 0.08); plate.add(sfoot);
  S.contact(0.42, 0.3, XW - 0.02, ZW - 0.08, 0.55);
  var lbl = S.label('FLYWHEEL', { w: 0.1, ratio: 0.2, color: '#d7dbe0', weight: 700 });
  lbl.position.set(XW - 0.02, YW + 0.3, ZW - 0.085); plate.add(lbl);

  // the wheel itself: rim, web, four spokes, hub and the chalk mark
  var wheel = new T.Group(); S.scene.add(wheel);
  var ironM = new T.MeshStandardMaterial({ color: 0x4b5159, roughness: 0.6, metalness: 0.5 });
  var rim = S.mesh(new T.TorusGeometry(RW - 0.016, 0.016, 14, 56), ironM); wheel.add(rim);
  var rimFace = S.mesh(new T.CylinderGeometry(RW, RW - 0.03, 0.03, 56, 1, true), ironM, false); rimFace.rotation.x = Math.PI / 2; wheel.add(rimFace);
  var web = S.mesh(new T.CylinderGeometry(0.055, 0.055, 0.009, 36), ironM); web.rotation.x = Math.PI / 2; wheel.add(web);
  for (var k = 0; k < 4; k++) {
    var sp = S.mesh(new T.BoxGeometry(0.015, 2 * RW - 0.05, 0.015), ironM);
    sp.rotation.z = k * Math.PI / 4; wheel.add(sp);
  }
  var hub = S.mesh(new T.CylinderGeometry(0.038, 0.038, 0.05, 24), ironM); hub.rotation.x = Math.PI / 2; wheel.add(hub);
  var chalk = S.mesh(new T.BoxGeometry(0.014, 0.03, 0.032), new T.MeshStandardMaterial({ color: 0xf6f3ea, roughness: 0.9 }), false);
  chalk.position.set(0, RW - 0.004, 0.004); wheel.add(chalk);
  var axle = S.mesh(new T.CylinderGeometry(RA, RA, 0.12, 24), M.chrome); axle.rotation.x = Math.PI / 2; axle.position.z = 0.07; wheel.add(axle);
  var wound = S.mesh(new T.CylinderGeometry(RA + 0.0035, RA + 0.0035, 0.045, 20), new T.MeshStandardMaterial({ color: 0x8a7a5a, roughness: 0.9 }), false);
  wound.rotation.x = Math.PI / 2; wound.position.z = 0.072; wheel.add(wound);
  wheel.position.set(XW, YW, ZW);

  // the hanging cord and the slotted weights
  var cordM = new T.MeshStandardMaterial({ color: 0x6b6253, roughness: 0.95 });
  var cord = S.mesh(new T.CylinderGeometry(0.0011, 0.0011, 1, 8), cordM, false); S.scene.add(cord);
  var hang = new T.Group(); S.scene.add(hang);
  var hookM = S.mesh(new T.CylinderGeometry(0.0018, 0.0018, 0.04, 10), M.chrome, false); hookM.position.y = 0.02; hang.add(hookM);
  var plateW = S.mesh(new T.CylinderGeometry(0.032, 0.032, 0.008, 28), M.brass); hang.add(plateW);
  var discs = [];
  for (var d = 0; d < 3; d++) { var dm = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.011, 28), M.brass); dm.position.y = -0.008 - d * 0.012; hang.add(dm); discs.push(dm); }

  // a steel tape beside the hanger, zero at the top of its travel
  var TAPE = 0.62, TTOP = YW - 0.06, TX = XW + 0.1, TZ = ZW + 0.03;
  var tape = S.ruler(TAPE, { title: 'STEEL TAPE · cm', labelEvery: 10, width: 0.026 });
  tape.position.set(TX, TTOP - TAPE, TZ); S.scene.add(tape);
  var tclamp = S.mesh(new T.BoxGeometry(0.03, 0.02, 0.03), M.iron); tclamp.position.set(TX, TTOP - TAPE + 0.01, TZ - 0.012); S.scene.add(tclamp);
  var tfoot = S.rounded(0.08, 0.07, 0.03, 0.008, M.darkWood); tfoot.rotation.x = -Math.PI / 2;
  tfoot.position.set(TX, TTOP - TAPE + 0.015, TZ); S.scene.add(tfoot); S.contact(0.12, 0.11, TX, TZ, 0.5);

  var watch = S.stopwatch([XW + 0.5, 0.035, 0.12], [-1.15, -0.4, -0.1]);
  var vern = S.rounded(0.16, 0.05, 0.016, 0.004, M.chrome); vern.position.set(XW + 0.36, 0.012, 0.08); S.scene.add(vern);
  var vernL = S.label('VERNIER CALLIPER · LC 0.01 cm', { w: 0.15, ratio: 0.1, color: '#2b3138', bg: '#eef1f4' });
  vernL.rotation.x = -Math.PI / 2; vernL.position.set(XW + 0.36, 0.021, 0.08); S.scene.add(vernL);
  S.contact(0.2, 0.09, XW + 0.36, 0.08, 0.4);

  S.addApparatus('wheel', wheel, 'Cast-iron flywheel', 'Almost all of its mass is in the rim, so its moment of inertia is large and the run-down is slow.');
  S.addApparatus('axle', axle, 'Axle', 'Radius r = ' + (RA * 100).toFixed(2) + ' cm, measured with a vernier calliper. The cord is wound on it.');
  S.addApparatus('hang', hang, 'Hanger with slotted weights', 'The falling mass. Its weight supplies the couple that spins the wheel up.');
  S.addApparatus('tape', tape, 'Steel tape', 'Measures the drop h, which is also 2πnr: the two should agree.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Least count 0.01 s. It is started as the mass is let go and stopped as the cord slips off.');
  S.addApparatus('vern', vern, 'Vernier calliper', 'Measures the axle’s diameter. r comes in squared, so measure it in two directions and average.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudS = S.hudCard('Flywheel speed'), hudD = S.hudCard('Mass has fallen'), hudR = S.hudCard('Rotations after the drop');

  // ---------- state
  function reset() {
    sim = K.init(p); st.running = false; st.wound = false; st.stoppedAt = null; st.rot = 0; prevRot = 0;
    watch.on = false; watch.t = 0;
    pose();
  }
  function setMass(i) {
    if (S.hand.busy || st.running) { if (st.running) S.say('Wait for the wheel to come to rest.'); return Promise.resolve(); }
    st.mi = i; p.m = MASSES[i];
    discs.forEach(function (dm, j) { dm.visible = j < Math.round((p.m - MASSES[0]) / Math.max(1e-9, (MASSES[2] - MASSES[0])) * 2) + 1; });
    reset(); S.say('Hanger loaded to ' + (p.m * 1000).toFixed(0) + ' g. Wind the cord on again.');
    if (ready) S.render();
    return Promise.resolve();
  }
  function setTurns(n) {
    if (S.hand.busy || st.running) return Promise.resolve();
    p.n = n; reset(); S.say(n + ' turns of cord on the axle: the mass will fall ' + (hDrop() * 100).toFixed(1) + ' cm.');
    if (ready) S.render();
    return Promise.resolve();
  }
  function readAxle() {
    st.axleRead = Math.round(RA * 2 * 100000) / 100;                // the diameter in mm, to the calliper's least count
    S.say('Axle diameter ' + st.axleRead.toFixed(2) + ' mm, so r = ' + (RA * 1000).toFixed(2) + ' mm.');
    if (ready) S.render();
  }
  function windCord() {
    if (S.hand.busy || st.running) return Promise.resolve();
    var from = new T.Vector3(XW + RA + 0.02, YW - hDrop() + 0.02, ZW + 0.07);
    var to = new T.Vector3(XW + RA + 0.02, YW - 0.04, ZW + 0.07);
    return S.hand.pinchMove(from, function (kk) { return from.clone().lerp(to, kk); }, function (kk) {
      sim.t = 0; st.wound = true; hang.position.set(XW + RA, YW - 0.06 - hDrop() * (1 - kk), ZW + 0.07);
      wheel.rotation.z = -phi() * kk;
    }, { ms: 1400, hold: 200, mode: 'side' }).then(function () {
      reset(); st.wound = true; S.say('Cord wound ' + p.n + ' turns on the axle and the hanger held at the top.');
      S.render();
    });
  }
  function release() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.wound) { S.say('Wind the cord on the axle first.'); return Promise.resolve(); }
    if (st.running) { S.say('A run is already going on.'); return Promise.resolve(); }
    if (st.axleRead === null) { S.say('Measure the axle with the vernier calliper first.'); return Promise.resolve(); }
    return S.hand.tap(watch.start).then(function () {
      S.click(2400);
      sim = K.init(p); st.running = true; st.rot = 0; prevRot = 0; watch.t = 0; watch.on = true;
      S.say('Let go. Stop the watch at the moment the cord slips off the axle.');
      S.render();
    });
  }
  function stopWatch() {
    if (S.hand.busy || !watch.on) return Promise.resolve();
    return S.hand.tap(watch.start).then(function () {
      S.click(2400); watch.on = false;
      var v = K.view(sim, p), t1 = v.t1;
      st.stoppedAt = Math.round(watch.t * 100) / 100;
      if (Math.abs(watch.t - t1) > 0.2) {
        S.say('The watch was stopped ' + (watch.t < t1 ? 'before' : 'after') + ' the cord slipped off. Let this run finish and do it again.');
        st.stoppedAt = null;
      } else {
        S.say('Fall timed: ' + st.stoppedAt.toFixed(2) + ' s. Now count the rotations until the wheel stops.');
      }
      S.render();
    });
  }
  function recordRun() {
    if (st.running) { S.say('Wait: the wheel is still turning.'); return; }
    if (st.stoppedAt === null) { S.say('This run has no timing. Wind the cord on and run it again.'); return; }
    var N = st.rot;
    if (N < 1) { S.say('No rotations were counted after the drop.'); return; }
    S.addRow({ t1: st.stoppedAt, N: N, m: p.m, n: p.n });
    S.say('Written in your record book: ' + (p.m * 1000).toFixed(0) + ' g fell in ' + st.stoppedAt.toFixed(2)
      + ' s, and the wheel then made ' + N + ' rotations.');
    st.stoppedAt = null; st.wound = false;
    S.render();
  }
  function runOnce() {                                              // auto: one complete run through the real buttons
    return windCord().then(release).then(function () {
      S.advance(K.view(sim, p).t1 + 2, function () { return K.view(sim, p).phase >= 1; });
      return stopWatch();
    }).then(function () {
      S.advance(K.view(sim, p).t2 + 6, function () { return K.view(sim, p).phase >= 2; });
      recordRun();
      return Promise.resolve();
    });
  }
  function runsDone() { var o = {}; S.rows.forEach(function (r) { o[r.m + '/' + r.n] = 1; }); return Object.keys(o).length; }

  reset();

  var EXP = {
    camera: { pos: [0.85, 0.95, 1.5], look: [0.0, 0.45, -0.2] },
    views: {
      setup: [[0.82, 0.92, 1.45], [0.0, 0.45, -0.2]],
      wheel: [[0.58, 0.88, 1.0], [XW, YW - 0.02, -0.14]],
      axle: [[0.46, 0.72, 0.78], [XW + 0.04, YW - 0.06, -0.1]],
      hang: [[0.4, 0.42, 0.78], [XW + 0.06, 0.28, -0.18]],
      tape: [[0.36, 0.45, 0.72], [XW + 0.08, 0.33, -0.18]],
      vern: [[0.5, 0.35, 0.52], [XW + 0.34, 0.03, 0.06]],
      sw: [[0.82, 0.42, 0.56], [XW + 0.46, 0.08, 0.07]],
      book: [[-0.34, 0.5, 0.56], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'The falling mass does work on the system. Part of it becomes the kinetic energy of the mass, part the '
        + 'kinetic energy of the flywheel, and part is lost to friction at the bearings. The rotations the wheel makes on '
        + 'its own after the cord slips off measure that friction loss.',
      formula: 'm g h = ½ m v² + ½ I ω² (1 + n/N)',
      formulaNote: 'so I = m (2 g h − v²) r² / (v² (1 + n/N)), with h = 2π n r and ω = 2(2πn)/t₁, r = '
        + (RA * 1000).toFixed(2) + ' mm',
      more: ['The couple on the wheel is constant while the mass falls, so the angular acceleration is constant and ω = 2θ/t₁.',
        'During the fall the wheel turns n times and loses n W to friction; afterwards it turns N times on that same friction alone, so the loss while the mass fell is n/N of the wheel’s kinetic energy.',
        'Nothing here needs the mass of the wheel or the shape of its rim: the method measures I directly.'],
      precautions: 'Wind the cord in a single layer, with no overlap, and make the loop just slack enough to slip off by '
        + 'itself at the bottom. Start the watch at the moment of release and stop it as the cord leaves the axle. Count '
        + 'every rotation after that, right until the wheel stands still.'
    },
    book: {
      title: 'Expt. — Moment of inertia of a flywheel',
      lines: ['Aim: to find the moment of inertia of a flywheel and the work lost to friction.',
        'Axle radius r = ' + (RA * 1000).toFixed(2) + ' mm (vernier calliper)',
        'n turns of cord, so h = 2π n r', 'ω = 2(2πn)/t₁,  v = ω r',
        'I = m (2gh − v²) r² / (v² (1 + n/N))'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'm (g)', get: function (r) { return (r.m * 1000).toFixed(0); } },
        { label: 'n', get: function (r) { return r.n.toFixed(0); } },
        { label: 't₁ (s)', get: function (r) { return r.t1.toFixed(2); } },
        { label: 'N', get: function (r) { return r.N.toFixed(0); } }]
    },
    graph: {
      x: function (r) { return r.m * 1000; }, y: function (r) { return r.t1; },
      xlabel: 'm (g)', ylabel: 't₁ (s)', x0: 0, y0: 0, line: null
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var v = HK.CALCS.fly_I.fn(rows, p);
      if (!isFinite(v) || v <= 0) return null;
      return { label: 'I of the flywheel', value: v, unit: 'kg·m²', digits: 5, truth: p.I,
        note: 'Mean of m(2gh − v²)r² / (v²(1 + n/N)) over the runs.' };
    },
    tol: 0.02,
    chips: ['Why count the rotations after the drop?', 'Where does the energy go?', 'Check my readings',
      'Why must the cord be wound in one layer?', 'Why is the mass of the wheel not needed?'],
    viva: [['The rotations after the cord slips off are counted in order to measure',
      ['the work lost to friction', 'the mass of the wheel', 'the axle radius'], 0,
      'On that run-down the only couple acting is friction.'],
      ['Most of a flywheel’s mass is in the rim because', ['mass far from the axis adds most to I', 'it is cheaper', 'it looks better'], 0,
        'I = Σmr².']],
    askState: function () {
      var v = K.view(sim, p);
      return {
        falling_mass_g: +(p.m * 1000).toFixed(0), turns_of_cord: p.n, drop_h_cm: +(hDrop() * 100).toFixed(1),
        axle_diameter_mm: st.axleRead, cord_wound: st.wound, run_in_progress: st.running,
        wheel_speed_rev_min: +v.rpm.toFixed(0), phase: v.phase === 0 ? 'mass falling' : v.phase === 1 ? 'running down on friction' : 'at rest',
        rotations_counted_after_drop: st.rot, stopwatch_running: watch.on, stopwatch_s: +watch.t.toFixed(2),
        time_of_fall_recorded_s: st.stoppedAt
      };
    },

    steps: [
      { id: 'set', title: 'Set up', view: 'axle',
        render: function (u) {
          u.h2('Measure the axle and set the load');
          u.p('The axle’s radius comes into the answer squared, so measure its diameter with the vernier calliper first.');
          u.task('Measure the axle diameter', st.axleRead !== null, st.axleRead !== null ? st.axleRead.toFixed(2) + ' mm' : 'Not measured yet')
            .add(u.button('Measure it', function () { S.focus('vern'); readAxle(); }, st.axleRead === null, st.axleRead !== null));
          u.h3('Load on the hanger');
          var r = u.row();
          MASSES.forEach(function (m, i) {
            r.appendChild(u.button((m * 1000).toFixed(0) + ' g' + (st.mi === i ? ' ✓' : ''), function () { setMass(i); }, st.mi === i, S.hand.busy || st.running));
          });
          u.h3('Turns of cord on the axle');
          var r2 = u.row();
          for (var n = NMIN; n <= NMAX; n++) {
            (function (nn) { r2.appendChild(u.button(nn + (p.n === nn ? ' ✓' : ''), function () { setTurns(nn); }, p.n === nn, S.hand.busy || st.running)); })(n);
          }
          u.formula('h = 2π n r = ' + (hDrop() * 100).toFixed(1) + ' cm');
          u.note('Check that against the steel tape: the drop and 2πnr must agree.');
          u.next('Next: wind, release and time', st.axleRead !== null);
        },
        ok: function () { return st.axleRead !== null; },
        auto: function () { readAxle(); return setTurns(Math.max(NMIN, Math.min(NMAX, Math.round(p.n)))); } },

      { id: 'run', title: 'Run and count', view: 'setup',
        render: function (u) {
          u.h2('Wind the cord, let the mass fall, and count the rotations');
          u.p('Press START as the mass is let go and STOP as the cord slips off the axle. Then count the rotations the '
            + 'wheel makes on its own until it stands still.');
          var r = u.row();
          MASSES.forEach(function (m, i) {
            r.appendChild(u.button((m * 1000).toFixed(0) + ' g' + (st.mi === i ? ' ✓' : ''), function () { setMass(i); }, st.mi === i, S.hand.busy || st.running));
          });
          u.row(u.button(st.wound ? 'Wound ✓' : 'Wind the cord', function () { windCord().then(function () { S.focus('wheel'); }); }, !st.wound, S.hand.busy || st.running || st.wound),
            u.button(watch.on ? 'STOP (cord slips off)' : 'Release and START', function () { if (watch.on) stopWatch(); else release(); }, true, S.hand.busy || (!watch.on && !st.wound)),
            u.button('Record this run', function () { recordRun(); }, false, S.hand.busy || st.running || st.stoppedAt === null));
          u.live(function () {
            var v = K.view(sim, p);
            return (p.m * 1000).toFixed(0) + ' g · ' + p.n + ' turns · '
              + (v.phase === 0 ? 'falling' : v.phase === 1 ? 'running down' : 'at rest') + ' · '
              + v.rpm.toFixed(0) + ' rev/min · ' + st.rot + ' rotations · ' + watch.t.toFixed(2) + ' s';
          });
          u.h3('Observation table'); u.table();
          var n = runsDone();
          u.next('Next: work out I', n >= 2);
          if (n < 2) u.p(n + ' of at least 2 runs done. Change the load or the number of turns and run it again.');
        },
        ok: function () { return runsDone() >= 2; },
        auto: function () {
          return [2, 1, 0].reduce(function (pr, i) {
            return pr.then(function () { return setMass(i); }).then(runOnce);
          }, Promise.resolve());
        } }
    ],

    tick: function (dt) {
      if (st.running) {
        K.step(sim, p, dt);
        var v = K.view(sim, p);
        if (v.phase >= 1) {
          var done = Math.floor((v.ph - phi()) / (2 * Math.PI));
          if (done > prevRot) { st.rot = done; prevRot = done; }
        }
        if (v.phase >= 2) { st.running = false; if (watch.on) { watch.on = false; } S.render(); }
      }
      pose();
    },
    ready: function () { ready = true; }
  };
  function pose() {
    var v = K.view(sim, p), ph = st.running || sim.t > 0 ? v.ph : (st.wound ? phi() : 0);
    wheel.rotation.z = -(st.running ? v.ph : (st.wound ? phi() : 0));
    var drop = st.running ? v.drop : (st.wound ? 0 : hDrop());
    var yTop = YW - 0.06 - drop;
    hang.position.set(XW + RA, yTop, ZW + 0.07);
    var yAx = YW;
    cord.scale.y = Math.max(0.001, yAx - yTop - 0.02);
    cord.position.set(XW + RA, (yAx + yTop + 0.02) / 2, ZW + 0.07);
    hudS.set(v.rpm.toFixed(0) + ' rev/min');
    hudD.set(st.running || st.wound ? (drop * 100).toFixed(1) + ' cm' : '\u2014');
    hudR.set(String(st.rot));
  }
  pose();
  return EXP;
});
