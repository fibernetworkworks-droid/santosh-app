/* Prayogshala studio module: the school slinky bench (NCERT Class IX Sound, Laboratory Manual Science IX).
   One rig, two set-ups - the lab id picks what is asked for:
     school-slinky-waves   a push along the slinky and a shake across it: the two kinds of wave
     school-pulse-speed    time a pulse over several lengths and work out v = sqrt(T / mu)
   Physics: the wave_pulse kernel from the wave_heat_school pack - the same numbers the server checks.
   The mass per metre of the slinky is the hidden knob; what the student measures is the speed of the pulse. */
HoolaStudio.define('school-slinky-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.wave_pulse;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('wave_pulse');
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var MODE = /wave-types/.test(BASE) || /slinky-waves/.test(BASE) ? 'types' : 'speed';
  var SAMPLE = String((S.lab.variant && S.lab.variant.sample) || 'Steel slinky');
  var L = p.Lspan, X0 = -L / 2, Y = 0.075, BZ = -0.08;
  var sim = K.init(p);
  var st = { kind: p.mode > 0.5 ? 'across' : 'along', running: false, speed: 1, n: Math.round(p.nrefl),
    flicked: false, spanRead: false, trips0: 0, amp: 0 };

  function vTrue() { return Math.sqrt(p.Tn / p.mu); }
  function view() { return K.view(sim, p); }

  // ---------------------------------------------------------------- apparatus
  var bench = new T.Group(); S.scene.add(bench);
  // two clamps on wooden blocks hold the ends of the slinky
  function clamp(x) {
    var g = new T.Group(); bench.add(g); g.position.set(x, 0, BZ);
    var blk = S.rounded(0.07, 0.07, 0.05, 0.006, M.darkWood); blk.rotation.x = -Math.PI / 2; blk.position.y = 0.025; g.add(blk);
    var post = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.07, 16), M.chrome); post.position.y = 0.075; g.add(post);
    var jaw = S.rounded(0.03, 0.026, 0.028, 0.005, M.alu); jaw.position.set(0, Y + 0.012, 0); g.add(jaw);
    var thumb = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 6), M.black); thumb.rotation.x = Math.PI / 2;
    thumb.position.set(0, Y + 0.012, 0.018); g.add(thumb);
    S.contact(0.11, 0.11, x, BZ, 0.5);
    return g;
  }
  var clampL = clamp(X0), clampR = clamp(X0 + L);
  // the slinky itself: a row of low-poly coils that are moved by the pulse
  var COILS = 72, coilM = new T.MeshStandardMaterial({ color: 0xd2d6d9, roughness: 0.3, metalness: 0.9 });
  var coilGeo = new T.TorusGeometry(0.026, 0.0022, 6, 18);
  var coils = [];
  for (var i = 0; i < COILS; i++) {
    var c = S.mesh(coilGeo, coilM, true, false); c.rotation.y = Math.PI / 2;
    c.position.set(X0 + L * i / (COILS - 1), Y, BZ); bench.add(c); coils.push(c);
  }
  var slab = S.label(SAMPLE.toUpperCase(), { w: 0.07, ratio: 0.16, color: '#4a4f55' });
  slab.position.set(0, Y + 0.05, BZ - 0.02); bench.add(slab);
  // a red paper rider marks one coil so the student can see what the coils themselves do
  var rider = S.mesh(new T.BoxGeometry(0.005, 0.03, 0.012), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.5 }));
  rider.position.set(X0 + L * 0.5, Y + 0.03, BZ); bench.add(rider);
  // the measuring tape along the bench, in centimetres
  var tapeTex = S.canvasTex(4096, 160, function (x, w, h) {
    x.fillStyle = '#f6e8b8'; x.fillRect(0, 0, w, h);
    var cm = Math.round(L * 100), k = w / cm;
    x.fillStyle = '#17171a';
    for (var i = 0; i <= cm; i++) {
      var xx = i * k, big = i % 10 === 0;
      x.fillRect(xx - (big ? 1.4 : 0.7), 0, big ? 2.8 : 1.4, big ? 56 : i % 5 === 0 ? 40 : 24);
      if (big && i % 20 === 0) { x.font = '600 40px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText(String(i), xx, 104); }
    }
    x.font = '600 34px "Public Sans", sans-serif'; x.textAlign = 'left'; x.fillStyle = '#6b4a14';
    x.fillText('MEASURING TAPE · centimetres', 40, 148);
  });
  var tape = new T.Mesh(new T.PlaneGeometry(L, 0.035), new T.MeshStandardMaterial({ map: tapeTex, roughness: 0.7 }));
  tape.rotation.x = -Math.PI / 2; tape.position.set(X0 + L / 2, 0.003, BZ + 0.1); S.scene.add(tape);
  var watch = S.stopwatch([0.62, 0.035, 0.16], [-1.2, -0.35, 0]);

  S.addApparatus('slinky', bench, SAMPLE, 'A soft steel spring stretched between two clamps. Its mass per metre is what makes the pulse slow enough to time.');
  S.addApparatus('clampL', clampL, 'Far clamp', 'The far end is held fast, so a pulse that reaches it turns back.');
  S.addApparatus('clampR', clampR, 'Near clamp', 'The near end is held too; the pulse is given just beside it.');
  S.addApparatus('tape', tape, 'Measuring tape', 'Laid along the bench to measure the span L between the clamps.');
  S.addApparatus('sw', watch.group, 'Stopwatch', 'Least count 0.01 s. Started with the flick and stopped after the counted lengths.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudX = S.hudCard('Pulse at'), hudT = S.hudCard('Stopwatch'), hudN = S.hudCard('Readings');

  // ---------------------------------------------------------------- the pulse drawn on the coils
  function shape(d) { return Math.exp(-(d / 0.13) * (d / 0.13)); }       // the pulse is a smooth hump 13 cm wide
  function drawPulse() {
    var v = view(), xp = X0 + v.x, i, c, x0, d, g;
    for (i = 0; i < COILS; i++) {
      c = coils[i]; x0 = X0 + L * i / (COILS - 1); d = x0 - xp; g = shape(d) * st.amp;
      if (st.kind === 'across') { c.position.set(x0, Y, BZ + 0.075 * g); c.rotation.z = 0; }
      else { c.position.set(x0 - 0.055 * g * (d >= 0 ? 1 : -1), Y, BZ); c.rotation.z = 0; }
      c.scale.setScalar(st.kind === 'along' ? 1 - 0.12 * g : 1);
    }
    var xr = X0 + L * 0.5, dr = xr - xp, gr = shape(dr) * st.amp;
    rider.position.set(st.kind === 'along' ? xr - 0.055 * gr * (dr >= 0 ? 1 : -1) : xr, Y + 0.03,
      BZ + (st.kind === 'across' ? 0.075 * gr : 0));
  }
  drawPulse();

  // ---------------------------------------------------------------- actions
  function readSpan() {
    if (S.hand.busy) return Promise.resolve();
    return S.hand.reach(new T.Vector3(X0 + 0.04, 0.03, BZ + 0.1), 'top', 600)
      .then(function () { return S.hand.reach(new T.Vector3(X0 + L - 0.04, 0.03, BZ + 0.1), 'top', 900); })
      .then(function () { return S.hand.away(400); })
      .then(function () { st.spanRead = true; S.focus('tape');
        S.say('The span between the clamps reads ' + (L * 100).toFixed(0) + ' cm on the tape, that is ' + L.toFixed(2) + ' m.'); S.render(); });
  }
  function setKind(k) {
    if (st.running) { S.say('Wait until this run is finished.'); return; }
    st.kind = k; p.mode = k === 'across' ? 1 : 0;
    S.say(k === 'across' ? 'Ready to shake the end sideways: that makes a transverse pulse.'
      : 'Ready to push the end along the slinky: that makes a longitudinal pulse, like sound in air.');
    S.render();
  }
  function flick() {
    if (S.hand.busy || st.running) return Promise.resolve();
    if (!st.spanRead) { S.say('Measure the span on the tape first: the speed needs L.'); return Promise.resolve(); }
    var near = new T.Vector3(X0 + L - 0.05, Y + 0.02, BZ);
    var to = st.kind === 'across' ? near.clone().add(new T.Vector3(0, 0, 0.07)) : near.clone().add(new T.Vector3(-0.06, 0, 0));
    sim = K.init(p); st.amp = 0; st.trips0 = 0;
    return S.hand.pinchMove(near, function (k) { return near.clone().lerp(to, Math.sin(k * Math.PI)); },
      function (k) { st.amp = Math.sin(k * Math.PI); drawPulse(); }, { ms: 520, hold: 0 })
      .then(function () {
        st.amp = 1; sim.running = 1.0; st.running = true; st.flicked = true;
        watch.t = 0; watch.on = true;
        S.click(700, 0.04, 0.05);
        S.say('Pulse sent. Count the lengths it covers, there and back.'); S.render();
      });
  }
  function stopAfter() {
    if (!st.running) { S.say('Send a pulse first.'); return; }
    var v = view();
    if (v.trips < st.n - 1e-9) { S.say('The pulse has covered ' + v.trips.toFixed(1) + ' lengths. Wait for ' + st.n + '.'); return; }
    st.running = false; sim.running = 0.0; watch.on = false;
    S.say('Stopped after ' + st.n + ' lengths at ' + watch.t.toFixed(2) + ' s.'); S.render();
  }
  function record() {
    if (st.running) { S.say('Stop the watch after the counted lengths first.'); return; }
    if (!st.flicked || watch.t <= 0) { S.say('There is nothing timed yet.'); return; }
    var t = watch.t, speed = st.n * L / t;
    S.addRow({ kind: st.kind, n: st.n, t: t, reading: speed, Tn: p.Tn });
    S.say('Written: ' + st.n + ' lengths in ' + t.toFixed(2) + ' s, so v = ' + speed.toFixed(2) + ' m/s.');
  }
  function setSpeed(v) { st.speed = v; S.render(); }
  function setTension(v) { if (st.running) { S.say('Wait until this run is finished.'); return; } p.Tn = v; S.render(); }
  function runTo(n) {                                 // let the pulse travel, and stop the moment it has covered n lengths
    for (var i = 0; i < 400 && view().trips < n; i++) S.advance(0.5, function () { return view().trips >= n; });
    return Promise.resolve();
  }
  function has(kind) { for (var i = 0; i < S.rows.length; i++) if (S.rows[i].kind === kind) return true; return false; }
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : NaN; }

  // ---------------------------------------------------------------- steps
  var stepSpan = { id: 'span', title: 'The span', view: 'tape', render: function (u) {
      u.h2('Measure the span between the clamps');
      u.p('The slinky is stretched along the bench and held at both ends. Read the span L on the tape: every speed worked out below needs it.');
      u.row(u.button(st.spanRead ? 'Span measured' : 'Measure the span on the tape', function () { readSpan(); S.render(); }, !st.spanRead, st.spanRead || S.hand.busy));
      u.live(function () { return st.spanRead ? 'L = ' + L.toFixed(2) + ' m' : 'The span has not been read yet'; });
      u.note('Never let a stretched slinky go: hold both ends and keep it flat on the bench.');
      u.next(MODE === 'types' ? 'Next: the two kinds of pulse' : 'Next: time the pulse', st.spanRead);
    },
    ok: function () { return st.spanRead; },
    auto: function () { return readSpan(); } };

  function timingUi(u) {
    var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
    [0.25, 0.5, 1].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
    u.slider('Lengths to count', 2, 12, 1, function () { return st.n; }, function (v) { st.n = v; }, '', 0);
    u.row(u.button(st.kind === 'along' ? 'Push the end along (longitudinal)' : 'Shake the end sideways (transverse)',
      function () { flick(); S.render(); }, true, S.hand.busy || st.running),
      u.button('Stop after ' + st.n + ' lengths', function () { stopAfter(); }, false, !st.running),
      u.button('Record this run', function () { record(); }, false, st.running || !st.flicked));
    u.live(function () { var v = view();
      return 'Pulse ' + (v.x * 100).toFixed(0) + ' cm from the near end · ' + v.trips.toFixed(1) + ' lengths covered · t = ' + watch.t.toFixed(2) + ' s'; });
  }

  var typeSteps = [stepSpan,
    { id: 'along', title: 'Push along', view: 'slinky', render: function (u) {
        u.h2('A push along the slinky: a longitudinal wave');
        u.p('Push the near end sharply along the line of the slinky and let go. A squeeze runs along it: the coils move back and forth '
          + 'along the same line the pulse travels, exactly as air does when sound passes. Watch the red rider in the middle.');
        u.row(u.button((st.kind === 'along' ? '✓ ' : '') + 'Push along (longitudinal)', function () { setKind('along'); }, st.kind !== 'along', st.running),
          u.button((st.kind === 'across' ? '✓ ' : '') + 'Shake across (transverse)', function () { setKind('across'); }, false, st.running));
        timingUi(u);
        u.h3('Observation table'); u.table();
        u.next('Next: shake it across', has('along'));
      },
      ok: function () { return has('along'); },
      auto: function () { setKind('along'); return flick().then(function () { return runTo(st.n); }).then(function () { stopAfter(); record(); }); } },
    { id: 'across', title: 'Shake across', view: 'slinky', render: function (u) {
        u.h2('A shake across the slinky: a transverse wave');
        u.p('Now shake the near end sideways instead. A hump runs along the slinky: the coils move across the line of travel. '
          + 'Time the same number of lengths and compare the speed with the push.');
        u.row(u.button((st.kind === 'along' ? '✓ ' : '') + 'Push along (longitudinal)', function () { setKind('along'); }, false, st.running),
          u.button((st.kind === 'across' ? '✓ ' : '') + 'Shake across (transverse)', function () { setKind('across'); }, st.kind !== 'across', st.running));
        timingUi(u);
        u.h3('Observation table'); u.table();
        u.next('Next: compare the two', has('along') && has('across'));
      },
      ok: function () { return has('along') && has('across'); },
      auto: function () { setKind('across'); return flick().then(function () { return runTo(st.n); }).then(function () { stopAfter(); record(); }); } },
  ];
  var speedSteps = [stepSpan,
    { id: 'time', title: 'Time the pulse', view: 'slinky', render: function (u) {
        u.h2('Time the pulse over several lengths');
        u.p('Flick the near end, start the clock at that moment, count the lengths the pulse covers there and back, and stop '
          + 'the clock after the number you chose. Doing several lengths instead of one makes the timing error small.');
        timingUi(u);
        u.h3('Observation table'); u.table();
        u.next('Next: stretch it harder', S.rows.length >= 2);
        if (S.rows.length < 2) u.p('Two runs at this stretch, please: one slip of the thumb should not decide the answer.');
      },
      ok: function () { return S.rows.length >= 2; },
      auto: function () {
        return flick().then(function () { return runTo(st.n); }).then(function () { stopAfter(); record(); return flick(); })
          .then(function () { return runTo(st.n); }).then(function () { stopAfter(); record(); }); } },
    { id: 'tension', title: 'Stretch it harder', view: 'slinky', render: function (u) {
        u.h2('Does the stretch change the speed?');
        u.p('Stretch the slinky harder: the tension T goes up and the pulse should travel faster, as √T. Time it again at the new stretch '
          + 'and then go back to the first stretch for the result.');
        u.slider('Tension', 0.4, 4, 0.1, function () { return p.Tn; }, function (v) { setTension(v); }, 'N', 1);
        timingUi(u);
        u.h3('Observation table'); u.table();
        u.next('Next: work out the speed', S.rows.length >= 3);
      },
      ok: function () { return S.rows.length >= 3; },
      auto: function () {
        var T0 = p.Tn;
        setTension(Math.min(4, Math.round(T0 * 2 * 10) / 10));
        return flick().then(function () { return runTo(st.n); }).then(function () { stopAfter(); record(); setTension(T0); }); } },
  ];

  return {
    camera: { pos: [0.3, 0.95, 1.55], look: [0, 0.05, -0.05] },
    views: { slinky: [[0.2, 0.72, 1.2], [0, 0.07, -0.06]], tape: [[-0.5, 0.5, 0.75], [-0.4, 0.02, 0.0]],
      clampL: [[X0 + 0.22, 0.3, 0.34], [X0, 0.06, BZ]], clampR: [[X0 + L - 0.1, 0.3, 0.38], [X0 + L, 0.06, BZ]],
      sw: [[0.5, 0.3, 0.44], [0.62, 0.03, 0.16]], book: [[-0.4, 0.52, 0.56], [-0.5, 0.0, 0.08]] },
    theory: { principle: MODE === 'types'
        ? 'In a longitudinal wave the coils move along the same line as the wave travels, so a squeeze runs along the slinky; that is how sound travels in air. In a transverse wave the coils move across that line, so a hump runs along. Both kinds travel along the same slinky at the same speed, because the speed is set by the tension and the mass per metre, not by how the pulse was made.'
        : 'A pulse on a stretched slinky travels at a steady speed and turns back at a fixed end, so the length it covers can be counted. Stretching it harder raises the tension and the pulse travels faster; a heavier slinky carries it more slowly.',
      formula: 'v = √(T / μ)',
      formulaNote: 'v = (lengths counted × L) ÷ time, with L the span between the clamps',
      more: ['Counting several lengths instead of one makes the timing error small: the same slip of the thumb is spread over a longer run.',
        'The pulse keeps its shape as it goes; only its height falls, because the slinky is not quite free of friction.'],
      precautions: 'Keep the slinky flat on the bench, hold both ends, and never let a stretched slinky go. Start the clock at the flick itself, not when the pulse is already on its way.' },
    book: { title: MODE === 'types' ? 'Expt. — Longitudinal and transverse waves' : 'Expt. — Speed of a pulse on a slinky',
      lines: ['Aim: ' + (MODE === 'types' ? 'to see the two kinds of wave and time each one.' : 'to find the speed of a pulse on a stretched slinky.'),
        'Span between the clamps L = ' + L.toFixed(2) + ' m.', 'v = (lengths × L) ÷ time', 'Pulse timed over several lengths, there and back.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Pulse', get: function (r) { return r.kind === 'across' ? 'transverse' : 'longitudinal'; } },
        { label: 'Lengths', get: function (r) { return String(r.n); } },
        { label: 't (s)', get: function (r) { return r.t.toFixed(2); } },
        { label: 'v (m/s)', get: function (r) { return r.reading.toFixed(2); } },
        { label: 'T (N)', get: function (r) { return r.Tn.toFixed(1); } }] },
    graph: { x: function (r) { return r.Tn; }, y: function (r) { return r.reading; },
      xlabel: 'tension T (N)', ylabel: 'v (m/s)', x0: 0, y0: 0,
      line: function () { var mu = p.mu; return function (t) { return Math.sqrt(Math.max(0, t) / mu); }; } },
    result: function (rows) {
      var at = rows.filter(function (r) { return Math.abs(r.Tn - p.Tn) < 1e-9; }).map(function (r) { return r.reading; });
      var use = at.length ? at : rows.map(function (r) { return r.reading; });
      var m = mean(use);
      if (!isFinite(m)) return null;
      return { label: 'Speed of the pulse', value: m, unit: 'm/s', digits: 2, truth: vTrue(),
        note: 'Mean of the ' + use.length + ' run' + (use.length === 1 ? '' : 's') + ' at a tension of ' + p.Tn.toFixed(1) + ' N.' };
    },
    tol: 0.03,
    chips: MODE === 'types' ? ['What is the difference between the two kinds of wave?', 'Which kind is sound?', 'Check my readings']
      : ['Why count several lengths?', 'What happens if I stretch it harder?', 'Check my readings'],
    viva: MODE === 'types'
      ? [['In a transverse wave the coils move', ['Across the line of travel', 'Along the line of travel', 'Not at all'], 0,
        'The movement is at right angles to the direction the pulse goes.'],
        ['Sound travels through air as a', ['Longitudinal wave', 'Transverse wave', 'Water wave'], 0,
          'Air is squeezed and stretched along the direction of travel.']]
      : [['If the tension is made four times larger, the pulse travels', ['Twice as fast', 'Four times as fast', 'At the same speed'], 0,
        'v = √(T/μ).'],
        ['Several lengths are timed instead of one because', ['It makes the timing error small', 'The pulse gets faster', 'The slinky warms up'], 0,
          'The same reaction-time slip is spread over a longer run.']],
    askState: function () {
      var v = view();
      return { set_up: 'slinky stretched between two clamps', span_m: +L.toFixed(2), tension_N: +p.Tn.toFixed(2),
        pulse_kind: st.kind === 'across' ? 'transverse' : 'longitudinal', pulse_at_cm: +(v.x * 100).toFixed(0),
        lengths_covered: +v.trips.toFixed(2), lengths_to_count: st.n, stopwatch_s: +watch.t.toFixed(2),
        pulse_running: st.running, span_measured: st.spanRead, readings_taken: S.rows.length };
    },
    steps: MODE === 'types' ? typeSteps : speedSteps,
    tick: function (dt) {
      if (st.running) {
        K.step(sim, p, dt * st.speed);
        watch.t += dt * (st.speed - 1);
        var v = view();
        if (v.trips >= st.n + 2) { st.running = false; sim.running = 0.0; watch.on = false; }   // never run away
        st.amp = Math.max(0.25, 1 - v.trips * 0.04);
      }
      drawPulse();
      var vv = view();
      hudX.set((vv.x * 100).toFixed(0) + ' cm'); hudT.set(watch.t.toFixed(2) + ' s'); hudN.set(String(S.rows.length));
    },
  };
});
