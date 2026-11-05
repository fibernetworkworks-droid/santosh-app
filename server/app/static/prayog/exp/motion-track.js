/* Prayogshala studio rig: motion on a straight track (NCERT Class VII / IX, chapter Motion).
   A 1.1 m grooved wooden track on two pedestals, with a printed centimetre scale along its front edge (zero at the
   starting line, 100 cm at the far end), a padded buffer at the near end, a digital stopwatch (least count 0.01 s),
   and the body that runs on it: a battery motor car for UNIFORM motion (level track) or a free trolley for UNIFORMLY
   ACCELERATED motion (far end lifted on a wooden block). The gloved hand sets the track up, brings the body back to
   the starting line, starts the watch as it is released and stops it as the body's front reaches the chosen mark.
   Physics: the `track` kernel of the mech_school pack. Every number is read from S.lab.params. */
HoolaStudio.define('motion-track', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.track;
  var p = window.HoolaKernels.paramsFor('track', S.lab.params);
  var ACC = Math.abs(p.acc) > 1e-9;                      // an accelerated run, or a steady speed?
  var vs = (S.lab.variant || {}).sample || '';

  // ---------- geometry. The track is built in its own frame: local x runs -TL..0, and the RIGHT end is the pivot.
  var TL = 1.1, TW = 0.11, TH = 0.014, X0 = -1.05, SPAN = 1.0;   // X0 = the zero mark, SPAN = the printed metre
  var PX = 0.55, PY = 0.052, PZ = -0.2;                          // the pivot, in world space
  var BL = 0.095, BH = 0.042, BW = 0.07;                         // the body on the track
  var RISE = ACC ? TL * (p.acc / 9.8 + 0.02) : 0;                // lift of the far end (slope + rolling friction)
  var TILT = Math.asin(Math.min(0.25, RISE / TL));
  var MARKS = [0.2, 0.4, 0.6, 0.8];
  var LC = 0.01;                                                 // stopwatch least count, seconds
  var FAR_X = PX - TL + 0.05, NEAR_X = PX - 0.06;                // where the two pedestals stand

  var st = { set: false, motor: false, tilt: 0, cross: null, running: false, onCross: null, mark: 0.8, prevS: 0, prevT: 0 };
  var sim = K.init(p); sim.s = 0; sim.t = 0; sim.v = 0;

  var track = new T.Group(); track.position.set(PX, PY, PZ); S.scene.add(track);
  var bed = S.rounded(TL, TH, TW, 0.004, M.wood); bed.position.set(-TL / 2, -TH / 2, 0); track.add(bed);
  [-1, 1].forEach(function (sg) {                                // the guide rails that make the groove
    var r = S.rounded(TL, 0.012, 0.009, 0.003, M.darkWood); r.position.set(-TL / 2, 0.006, sg * (TW / 2 - 0.006)); track.add(r);
  });
  var scaleTex = S.canvasTex(4096, 128, function (x, w, h) {
    x.fillStyle = '#f2ecd9'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#17181a'; x.font = '700 42px "Public Sans", sans-serif'; x.textAlign = 'center';
    for (var i = 0; i <= 100; i++) {
      var px = 20 + i / 100 * (w - 40), big = i % 10 === 0, mid = i % 5 === 0;
      x.fillRect(px - (big ? 1.7 : 0.9), 0, big ? 3.4 : 1.8, big ? 54 : mid ? 38 : 24);
      if (big) x.fillText(String(i), px, 104);
    }
    x.textAlign = 'left'; x.font = '600 32px "Public Sans", sans-serif'; x.fillStyle = '#6b4a14'; x.fillText('cm', 8, 104);
  });
  var strip = new T.Mesh(new T.PlaneGeometry(SPAN + 0.04, 0.042), new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.55 }));
  strip.rotation.x = -Math.PI / 2; strip.position.set(X0 + SPAN / 2, 0.0013, TW / 2 - 0.028); track.add(strip);
  var zero = S.mesh(new T.BoxGeometry(0.0025, 0.005, TW - 0.016), M.red); zero.position.set(X0, 0.002, 0); track.add(zero);
  var bufBody = S.rounded(0.022, 0.05, TW, 0.004, M.iron); bufBody.position.set(-0.011, 0.025, 0); track.add(bufBody);
  var bufPad = S.mesh(new T.BoxGeometry(0.006, 0.04, TW - 0.02), M.rubber); bufPad.position.set(-0.025, 0.025, 0); track.add(bufPad);

  // pedestals (world space: they do not tilt with the track)
  [FAR_X, NEAR_X].forEach(function (x) {
    var ped = S.rounded(0.075, PY - TH, 0.095, 0.006, M.darkWood);
    ped.position.set(x, (PY - TH) / 2, PZ); S.scene.add(ped);
    S.contact(0.14, 0.16, x, PZ, 0.45);
  });

  // the wooden block that lifts the far end (accelerated run only)
  var BLOCK_HOME = new T.Vector3(-0.08, 0, 0.13);
  var BH2 = Math.max(0.014, RISE);
  var block = new T.Group(); S.scene.add(block);
  var blm = S.rounded(0.09, BH2, 0.095, 0.005, new T.MeshStandardMaterial({ map: S.woodTex, color: 0x9a6a3a, roughness: 0.72 }));
  blm.position.y = BH2 / 2; block.add(blm);
  var blLbl = S.label(Math.round(RISE * 1000) + ' mm', { w: 0.05, ratio: 0.3, color: '#3a2410' });
  blLbl.position.set(0, BH2 / 2, 0.0485); block.add(blLbl);
  block.position.copy(BLOCK_HOME); block.visible = ACC;
  var blockShadow = S.contact(0.16, 0.16, BLOCK_HOME.x, BLOCK_HOME.z, ACC ? 0.45 : 0);

  // the body that runs on the track
  var car = new T.Group(); track.add(car);
  var shell = S.rounded(BL, BH, BW, 0.008, new T.MeshStandardMaterial({ color: ACC ? 0x7a4e2c : 0x1f4f8c, roughness: 0.45, metalness: 0.1 }));
  shell.position.y = 0.016 + BH / 2; car.add(shell);
  var nose = S.mesh(new T.BoxGeometry(0.004, BH * 0.7, BW - 0.012), M.red); nose.position.set(BL / 2 + 0.002, 0.016 + BH / 2, 0); car.add(nose);
  [[-0.03, -1], [-0.03, 1], [0.03, -1], [0.03, 1]].forEach(function (q) {
    var w = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.008, 20), M.black);
    w.rotation.x = Math.PI / 2; w.position.set(q[0], 0.016, q[1] * (BW / 2 - 0.003)); car.add(w);
    var hub = S.mesh(new T.CylinderGeometry(0.0048, 0.0048, 0.009, 10), M.chrome); hub.rotation.x = Math.PI / 2; hub.position.copy(w.position); car.add(hub);
  });
  var sw = null;
  if (!ACC) {                                                    // a motor car carries a battery box and a switch
    var batt = S.rounded(0.05, 0.016, 0.042, 0.003, M.black); batt.position.set(-0.012, 0.016 + BH + 0.008, 0); car.add(batt);
    sw = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.007, 16), M.green);
    sw.position.set(0.028, 0.016 + BH + 0.004, 0); car.add(sw);
    var swl = S.label('ON', { w: 0.024, ratio: 0.4, color: '#e8eef6' });
    swl.rotation.x = -Math.PI / 2; swl.position.set(0.028, 0.016 + BH + 0.009, 0.018); car.add(swl);
  }
  var carLbl = S.label(ACC ? 'TROLLEY' : 'MOTOR CAR', { w: 0.058, ratio: 0.2, color: '#f2f4f8' });
  carLbl.position.set(0, 0.016 + BH / 2, BW / 2 + 0.0009); car.add(carLbl);

  var watch = S.stopwatch([0.42, 0, 0.12], [0, -0.4, 0]);

  S.addApparatus('track', track, 'Grooved track (1.1 m)', 'A straight wooden track with a shallow groove and a printed centimetre scale. Its zero mark is the starting line.');
  S.addApparatus('car', car, ACC ? 'Trolley' : 'Battery motor car',
    ACC ? 'A free-running trolley. Released from rest on the slope, it speeds up steadily.' : 'A battery car that runs at a steady speed. That speed is what you measure.');
  if (ACC) S.addApparatus('block', block, 'Wooden block (' + Math.round(RISE * 1000) + ' mm)', 'Placed on the far pedestal to give the track a gentle slope.');
  S.addApparatus('watch', watch.group, 'Digital stopwatch', 'Least count 0.01 s. Started as the body is released, stopped as its front reaches the mark.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudD = S.hudCard('Distance'), hudT = S.hudCard('Stopwatch'), hudV = S.hudCard(ACC ? 'Speed now' : 'Motor');

  // ---------- helpers
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
  function gripPoint(s) {                                        // where the hand holds the body, in world space
    track.updateMatrixWorld(true);
    return track.localToWorld(new T.Vector3(X0 + s - BL / 2, 0.016 + BH + 0.004, 0));
  }
  function atStart() { return sim.s < 1e-6; }
  function pose() {
    track.rotation.z = -st.tilt;
    car.position.set(X0 + sim.s - BL / 2, 0, 0);
    block.visible = ACC && st.set;
    blockShadow.material.opacity = (ACC && st.set) ? 0.3 : 0;
    hudD.set((sim.s * 100).toFixed(1) + ' cm');
    hudT.set(watch.t.toFixed(2) + ' s');
    hudV.set(ACC ? sim.v.toFixed(3) + ' m/s' : (st.motor ? 'on' : 'off'));
  }

  // ---------- the actions the buttons call (the walk-through uses exactly these)
  function setUp() {
    if (S.hand.busy || st.set) return Promise.resolve();
    if (!ACC) {
      return S.hand.tap(sw, 'tap').then(function () {
        st.motor = true; st.set = true; sw.material = M.red; pose(); S.render();
        S.say('The motor is on. The car is held at the zero mark until you release it.');
      });
    }
    var from = BLOCK_HOME.clone(), to = new T.Vector3(FAR_X, PY - TH, PZ);
    var path = along([from, from.clone().setY(0.2), to.clone().setY(0.2), to]);
    var G = new T.Vector3(0, BH2 + 0.004, 0);
    return S.hand.pinchMove(from.clone().add(G), function (k) { return path(k).add(G); },
      function (k) { block.position.copy(path(k)); blockShadow.position.set(block.position.x, 0.0009, block.position.z); }, { ms: 1500 })
      .then(function () {
        block.position.copy(to); blockShadow.position.set(to.x, 0.0009, to.z); st.set = true;
        return S.tween(700, function (k) { st.tilt = TILT * k; pose(); });
      })
      .then(function () {
        st.tilt = TILT; pose(); S.render();
        S.say('The far end of the track now rests on the ' + Math.round(RISE * 1000) + ' mm block. The trolley will run down the slope.');
      });
  }
  function resetCar() {
    if (S.hand.busy || atStart()) return Promise.resolve();
    var s0 = sim.s;
    return S.hand.pinchMove(gripPoint(s0), function (k) { return gripPoint(s0 * (1 - k)); },
      function (k) { sim.s = s0 * (1 - k); sim.v = 0; pose(); }, { ms: 1100, mode: 'top', pose: 'grip' })
      .then(function () { sim = K.init(p); sim.s = 0; sim.t = 0; sim.v = 0; st.cross = null; pose(); S.render(); });
  }
  function waitCross() {
    if (S.fast) { S.advance(60, function () { return st.cross !== null; }); return Promise.resolve(); }
    return new Promise(function (res) { st.onCross = res; });
  }
  function runTo(mark) {
    if (S.hand.busy || st.running) return Promise.resolve();
    if (!st.set) { S.say(ACC ? 'Put the block under the far end of the track first.' : 'Switch the car\'s motor on first.'); return Promise.resolve(); }
    if (S.rows.some(function (r) { return Math.abs(r.s - mark) < 1e-6; })) {
      S.say('You already have a reading at ' + Math.round(mark * 100) + ' cm. Choose another mark.');
      return Promise.resolve();
    }
    return resetCar().then(function () {
      st.mark = mark; p.mark = mark; st.cross = null; st.prevS = 0; st.prevT = 0;
      sim = K.init(p); sim.s = 0; sim.t = 0; sim.v = ACC ? 0 : p.u;
      watch.t = 0; watch.on = false; watch.draw();
      return S.hand.tap(watch.reset, 'tap');
    }).then(function () { return S.hand.tap(watch.start, 'tap'); })
      .then(function () {
        watch.on = true; st.running = true; pose();
        S.say('Released at the zero mark, watch started.');
        return waitCross();
      })
      .then(function () { return S.hand.tap(watch.start, 'tap'); })
      .then(function () {
        watch.on = false; st.running = false;
        watch.t = Math.round(st.cross / LC) * LC;                // read off the display, to its least count
        watch.draw(); pose(); S.render();
        S.say('Stopwatch: ' + watch.t.toFixed(2) + ' s over ' + Math.round(mark * 100) + ' cm.');
      });
  }
  function record() {
    if (S.hand.busy) return;
    if (st.cross === null) { S.say('Time a run first, then record the reading.'); return; }
    var mark = st.mark, t = watch.t;
    if (S.rows.some(function (r) { return Math.abs(r.s - mark) < 1e-6; })) { S.say('That mark is already in the table.'); return; }
    if (!(t > 0)) { S.say('The stopwatch reads zero. Time the run again.'); return; }
    S.addRow({ s: mark, cm: Math.round(mark * 100), t: t, t2: t * t, v: mark / t });
    st.cross = null;
    S.say('Written in your record book: ' + Math.round(mark * 100) + ' cm in ' + t.toFixed(2) + ' s.');
  }

  var EXP = {
    camera: { pos: [0.3, 0.8, 1.15], look: [-0.02, 0.1, -0.14] },
    views: {
      track: [[0.1, 0.55, 0.78], [-0.05, 0.08, -0.18]],
      car: [[-0.4, 0.3, 0.14], [-0.52, 0.07, -0.19]],
      block: [[-0.3, 0.28, 0.22], [-0.5, 0.05, -0.2]],
      watch: [[0.46, 0.3, 0.44], [0.42, 0.03, 0.1]],
      setup: [[0.02, 0.6, 0.92], [-0.14, 0.08, -0.18]],
      run: [[0.18, 0.66, 1.0], [-0.02, 0.07, -0.16]],
      book: [[-0.56, 0.46, 0.52], [-0.64, 0.0, 0.08]]
    },
    theory: {
      principle: ACC
        ? 'A trolley released from rest on a gently sloping track speeds up steadily: its acceleration is constant. '
          + 'The distance it covers grows with the square of the time, so the distance-time graph is a curve, while a '
          + 'graph of distance against the square of the time is a straight line through the origin.'
        : 'A body in uniform motion covers equal distances in equal intervals of time. Its speed is distance divided '
          + 'by time, so the distance-time graph is a straight line through the origin whose slope is the speed.',
      formula: ACC ? 's = ½ a t²' : 'v = s / t',
      formulaNote: ACC ? 'so a = 2 × slope of the s against t² graph' : 'so v = slope of the s against t graph',
      more: [ACC
        ? 'The slope of the track and the rolling friction of the wheels together fix the acceleration. The same '
          + 'acceleration comes out at every mark, and that is what "uniformly accelerated" means.'
        : 'The car is held at the zero mark with its motor already running, so it is at its steady speed from the '
          + 'first moment. Each mark then gives the same speed.',
        'The stopwatch reads to 0.01 s and the scale to 1 mm, so the shortest run carries the largest percentage '
        + 'error. That is why four marks are timed and one straight line is drawn through all four points.'],
      precautions: 'Keep the track straight and the scale\'s zero exactly at the starting line. Release the body '
        + 'without a push. Start and stop the watch at the instant the front of the body crosses a mark. Read the '
        + 'scale with your eye straight above the mark.'
    },
    book: {
      at: [-0.58, 0.1, 0.1],
      title: ACC ? 'Expt. — Distance-time graph of an accelerating trolley' : 'Expt. — Speed of a body in uniform motion',
      lines: ['Aim: ' + S.lab.aim, 'Track 1.1 m, printed scale 0–100 cm, zero at the starting line.',
        'Stopwatch least count 0.01 s.',
        ACC ? 's = ½ a t²   so   a = 2 × slope of (s against t²)' : 'v = s / t   so   v = slope of (s against t)',
        'Precautions: release without a push; eye straight above the mark.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 's (cm)', get: function (r) { return String(r.cm); } },
        { label: 't (s)', get: function (r) { return r.t.toFixed(2); } },
        ACC ? { label: 't² (s²)', get: function (r) { return r.t2.toFixed(3); } }
          : { label: 's/t (m/s)', get: function (r) { return r.v.toFixed(3); } },
        { label: ACC ? '2s/t² (m/s²)' : 's/t (cm/s)', get: function (r) { return ACC ? (2 * r.s / r.t2).toFixed(3) : (r.v * 100).toFixed(1); } }]
    },
    graph: {
      x: function (r) { return ACC ? r.t2 : r.t; }, y: function (r) { return r.s; },
      xlabel: ACC ? 'time squared t² (s²)' : 'time t (s)', ylabel: 'distance s (m)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var pts = rows.map(function (r) { return [ACC ? r.t2 : r.t, r.s]; }), k = S.fit.origin(pts);
      return ACC
        ? { label: 'a', value: 2 * k, unit: 'm/s²', digits: 3, truth: p.acc, note: 'Twice the slope of the distance against t² graph.' }
        : { label: 'v', value: k, unit: 'm/s', digits: 3, truth: p.u, note: 'Slope of the distance against time graph.' };
    },
    tol: 0.03,
    chips: ACC
      ? ['Why plot distance against t² ?', 'What makes the trolley accelerate?', 'Check my readings', 'Why is the first reading the least accurate?']
      : ['How do I know the motion is uniform?', 'Check my readings', 'Why time four marks and not one?', 'Where do the errors come from?'],
    viva: ACC
      ? [['The distance-time graph of this trolley is', ['a curve bending upwards', 'a straight line', 'a horizontal line'], 0,
        'Distance grows as the square of the time, so the slope keeps increasing.'],
      ['Doubling the time from rest makes the distance', ['four times as large', 'twice as large', 'the same'], 0, 's = ½ a t², and 2² = 4.']]
      : [['Equal distances in equal times means the motion is', ['uniform', 'accelerated', 'circular'], 0,
        'That is the definition of uniform motion.'],
      ['The slope of a distance-time graph is', ['the speed', 'the acceleration', 'the distance'], 0,
        'Slope = change in distance ÷ change in time.']],
    askState: function () {
      return { kind: ACC ? 'uniformly accelerated trolley' : 'uniform motion, battery motor car', sample: vs,
        track_set_up: st.set, body_at_cm: +(sim.s * 100).toFixed(1), stopwatch_s: +watch.t.toFixed(2),
        mark_being_timed_cm: Math.round(st.mark * 100), marks_recorded_cm: S.rows.map(function (r) { return r.cm; }),
        scale_least_count_mm: 1, stopwatch_least_count_s: LC };
    },

    steps: [
      { id: 'setup', title: 'Set the track up', view: 'setup',
        render: function (u) {
          u.h2('Set the track up');
          u.p(ACC
            ? 'The track must slope gently, so the trolley speeds up steadily. The hand puts the wooden block on the far pedestal and lets the track down on it.'
            : 'The track stays flat. The hand switches the car\'s motor on, so the car is already at its steady speed when it is released.');
          u.row(u.button(ACC ? 'Put the block under the far end' : 'Switch the motor on', function () { setUp(); }, true, S.hand.busy || st.set));
          u.task('Track ready', st.set, st.set ? (ACC ? 'far end lifted ' + Math.round(RISE * 1000) + ' mm' : 'motor running') : 'not ready yet');
          u.live(function () { return 'Body at ' + (sim.s * 100).toFixed(1) + ' cm · ' + (st.set ? 'ready' : 'not ready'); });
          u.note('The printed scale reads 0 at the starting line and 100 cm at the far end. Read it to 1 mm.');
          u.next('Next: time the runs', st.set && !S.hand.busy);
        },
        ok: function () { return st.set; },
        auto: function () { return setUp(); } },

      { id: 'run', title: 'Time the runs', view: 'run',
        render: function (u) {
          u.h2('Time the body to each mark');
          u.p('Choose a mark. The hand brings the body back to the zero mark, resets the watch, starts it as the body is released and stops it as the front of the body reaches that mark. Then record the reading.');
          var r = u.row();
          MARKS.forEach(function (m) {
            var done = S.rows.some(function (q) { return Math.abs(q.s - m) < 1e-6; });
            r.appendChild(u.button((done ? '✓ ' : '') + Math.round(m * 100) + ' cm', function () { runTo(m); }, false, S.hand.busy || st.running || done));
          });
          u.row(u.button('Record the reading', function () { record(); }, true, S.hand.busy || st.cross === null),
            u.button('Bring the body back', function () { resetCar(); }, false, S.hand.busy || atStart()));
          u.live(function () {
            return 'Stopwatch ' + watch.t.toFixed(2) + ' s · body at ' + (sim.s * 100).toFixed(1) + ' cm · '
              + (st.running ? 'running' : st.cross !== null ? 'timed ' + Math.round(st.mark * 100) + ' cm, not yet recorded' : 'at rest');
          });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 4) u.p(S.rows.length + ' of 4 marks timed.');
          u.next('Next: graph and result', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          return MARKS.reduce(function (pr, m) {
            return pr.then(function () { return runTo(m); }).then(function () { record(); });
          }, Promise.resolve());
        } }
    ],

    tick: function (dt) {
      if (st.running) {
        st.prevS = sim.s; st.prevT = sim.t;
        K.step(sim, p, dt);
        if (sim.s >= st.mark && st.cross === null) {
          var d = sim.s - st.prevS;
          st.cross = d > 1e-12 ? st.prevT + dt * (st.mark - st.prevS) / d : sim.t;
          sim.s = st.mark; sim.v = p.u + p.acc * st.cross;
          st.running = false; watch.on = false;
          if (st.onCross) { var f = st.onCross; st.onCross = null; f(); }
        }
      }
      pose();
    }
  };
  pose();
  return EXP;
});
