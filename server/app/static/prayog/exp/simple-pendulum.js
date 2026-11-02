/* Prayogshala studio module: Simple pendulum (NCERT Class XI). The REFERENCE module every other experiment follows.
   Physics: the pendulum kernel from kernels.js (RK4, nonlinear) - the same numbers the server checks. */
HoolaStudio.define('simple-pendulum', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.pendulum;
  var BOB_R = 0.01, DEG = Math.PI / 180;
  var st = { threadCm: 79, diaDone: false, measured: false, target: 6 * DEG, released: false };
  var p = window.HoolaKernels.paramsFor('pendulum', { L: 0.8, theta0: 0, b: 0.004 });
  var sim = K.init(p), running = false, n = 0, halves = 0, lastSign = 0;
  function effL() { return st.threadCm / 100 + BOB_R; }

  // ---------- apparatus
  var stand = S.stand({ x: 0, z: 0, armY: 1.13 });
  var PIVOT = new T.Vector3(0, 1.088, 0);
  var cork = S.cork(new T.Vector3(0, 1.104, 0));
  var thread = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 1, 8), M.thread, true, false); S.scene.add(thread);
  var knot = S.mesh(new T.SphereGeometry(0.0016, 10, 8), M.thread); knot.position.copy(PIVOT); S.scene.add(knot);
  var bob = new T.Group(); S.scene.add(bob);
  var ball = S.mesh(new T.SphereGeometry(BOB_R, 64, 48), M.brass); bob.add(ball);
  var eye = S.mesh(new T.TorusGeometry(0.0026, 0.0007, 10, 24), M.brass); eye.position.y = BOB_R + 0.0022; bob.add(eye);
  var bobShadow = S.contact(0.05, 0.05, 0, 0, 0.35);
  var protTex = S.canvasTex(1024, 560, function (x, w) { var cx = w / 2, cy = 30, R = 480;
    x.fillStyle = 'rgba(225,240,255,0.18)'; x.beginPath(); x.moveTo(cx - R, cy); x.arc(cx, cy, R, 0, Math.PI); x.closePath(); x.fill();
    x.strokeStyle = 'rgba(15,35,65,.92)'; x.fillStyle = 'rgba(15,35,65,.95)'; x.font = '600 22px "Public Sans", sans-serif'; x.textAlign = 'center';
    for (var d = 0; d <= 180; d++) { var a = Math.PI * d / 180, len = d % 10 === 0 ? 40 : d % 5 === 0 ? 26 : 14; x.lineWidth = d % 10 === 0 ? 2.4 : 1.2;
      x.beginPath(); x.moveTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); x.lineTo(cx + Math.cos(a) * (R - len), cy + Math.sin(a) * (R - len)); x.stroke();
      if (d % 10 === 0 && d && d !== 180) x.fillText(String(Math.abs(90 - d)), cx + Math.cos(a) * (R - 64), cy + Math.sin(a) * (R - 64) + 8); }
    x.lineWidth = 1.5; x.beginPath(); x.moveTo(cx, cy); x.lineTo(cx, cy + R); x.stroke(); });
  var prot = new T.Mesh(new T.PlaneGeometry(0.3, 0.164), new T.MeshStandardMaterial({ map: protTex, transparent: true, roughness: 0.1, side: T.DoubleSide, depthWrite: false }));
  prot.position.set(0, PIVOT.y - 0.078, 0.014); prot.scale.y = -1; prot.renderOrder = 3; S.scene.add(prot);
  var ruler = S.ruler(1.0, { title: 'METRE SCALE · cm · LC 1 mm', labelEvery: 10 });
  ruler.position.set(0.075, PIVOT.y - 1.0, -0.03);   // zero (top) level with the point of suspension
  var rfoot = S.rounded(0.08, 0.05, 0.03, 0.008, M.black); rfoot.rotation.x = -Math.PI / 2; rfoot.position.set(0.075, 0.015, -0.03); S.scene.add(rfoot); S.contact(0.14, 0.1, 0.075, -0.03, 0.5);
  var watch = S.stopwatch([0.21, 0.035, 0.17], [-1.15, 0, 0.25]);
  // vernier callipers + spare bob (bob diameter)
  var vc = new T.Group(); S.scene.add(vc);
  var vb = S.mesh(new T.BoxGeometry(0.2, 0.004, 0.016), M.steel); vc.add(vb);
  [[-0.096, 0.026, 0.008, 0.045], [-0.064, 0.002, 0.04, 0.022], [-0.075, 0.026, 0.008, 0.045]].forEach(function (a) { var m = S.mesh(new T.BoxGeometry(a[2], 0.005, a[3]), M.steel); m.position.set(a[0], 0, a[1]); vc.add(m); });
  vc.position.set(0.33, 0.004, -0.06); vc.rotation.y = 0.45; S.contact(0.24, 0.08, 0.31, -0.05, 0.35);
  var spare = S.mesh(new T.SphereGeometry(BOB_R, 40, 30), M.brass); spare.position.set(0.25, BOB_R, -0.13); S.scene.add(spare);

  S.addApparatus('stand', stand, 'Retort stand', 'Heavy cast-iron base keeps the support rigid, so the pivot does not move.');
  S.addApparatus('cork', cork, 'Split cork', 'Grips the thread so the point of suspension is fixed and sharp.');
  S.addApparatus('bob', bob, 'Brass bob with hook', 'Heavy and small, so air drag is negligible. Diameter 2.00 cm.');
  S.addApparatus('thread', thread, 'Cotton thread', 'Light and inextensible: its length does not change while it swings.');
  S.addApparatus('ruler', ruler, 'Metre scale', 'Measures the thread length, zero at the point of suspension. Least count 1 mm.');
  S.addApparatus('prot', prot, 'Protractor', 'Reads the angle of displacement. Keep it under 10°.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Least count 0.01 s. Time 20 oscillations, not one.');
  S.addApparatus('vc', vc, 'Vernier callipers', 'Measures the bob diameter: 2.00 cm, so r = 1.00 cm.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudL = S.hudCard('Effective length L'), hudA = S.hudCard('Angle θ'), hudN = S.hudCard('Oscillations');
  var up = new T.Vector3(0, 1, 0);

  // ---------- drag the bob (only while setting the angle)
  S.draggables.push({ objects: [ball], enabled: function () { return S.steps[S.step].id === 'release' && !running; },
    move: function (ray) { var pt = S.rayPlane(ray, PIVOT, new T.Vector3(0, 0, 1)); if (!pt) return;
      var a = Math.max(-25 * DEG, Math.min(25 * DEG, Math.atan2(pt.x - PIVOT.x, PIVOT.y - pt.y))); sim.y = [a, 0]; st.target = Math.abs(a); } });

  function release(target) {
    if (S.hand.busy) return Promise.resolve();
    running = false; st.target = target;
    var L = effL(), bobAt = function (th) { return new T.Vector3(PIVOT.x + L * Math.sin(th), PIVOT.y - L * Math.cos(th), 0); };
    var th0 = sim.y[0];
    return S.hand.pinchMove(bobAt(th0).add(new T.Vector3(0, 0, 0.0)), function (k) { return bobAt(th0 + (target - th0) * k); },
      function (k) { sim.y = [th0 + (target - th0) * k, 0]; }, { ms: 1100 })
      .then(function () { sim.y = [target, 0]; running = true; st.released = true; S.render(); });
  }
  function stopBob() { running = false; sim.y = [0, 0]; st.released = false; }
  function pressWatch() {
    if (!running && !watch.on) { S.say('Release the bob first, then time it.'); return Promise.resolve(); }
    return S.hand.tap(watch.start).then(function () {
      S.click(2400);
      if (!watch.on) { watch.t = 0; n = 0; halves = 0; lastSign = Math.sign(sim.y[0]) || 1; watch.on = true; }
      else { watch.on = false; record(); }
      S.render(); });
  }
  function record() {
    if (n < 18 || n > 22) { S.say('You counted ' + n + ' oscillations. Stop the watch after exactly 20 for this reading.'); return; }
    var t = Math.round(watch.t * 100) / 100;
    S.addRow({ L: effL(), n: n, t: t, T: t / n });
    S.say('Written in your record book: L = ' + (effL() * 100).toFixed(1) + ' cm, ' + n + ' oscillations in ' + t.toFixed(2) + ' s.');
    stopBob(); S.focus('book');
  }

  return {
    camera: { pos: [0.78, 1.0, 1.75], look: [-0.05, 0.55, -0.15] },
    views: { stand: [[0.5, 0.75, 1.1], [-0.12, 0.55, 0]], cork: [[0.04, 1.12, 0.2], [0, 1.1, 0]], bob: [[0.1, 0.33, 0.26], [0, 0.28, 0]],
      thread: [[0.4, 0.75, 0.9], [0, 0.7, 0]], ruler: [[0.22, 0.72, 0.55], [0.07, 0.68, -0.03]], prot: [[0.04, 1.05, 0.4], [0, 1.03, 0]],
      swing: [[0.38, 0.6, 1.05], [0.07, 0.42, 0.0]], sw: [[0.5, 0.78, 1.2], [0.08, 0.3, 0.06]], vc: [[0.42, 0.25, 0.22], [0.31, 0.0, -0.06]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A heavy bob on a light, inextensible thread swings about a fixed point. For small angles the restoring force is proportional to the displacement, so the motion is simple harmonic.',
      formula: 'T = 2π √(L / g)', formulaNote: 'so g = 4π² L / T² · valid for angles under about 10°',
      more: ['L is the effective length: from the point of suspension to the centre of the bob, i.e. thread length + radius of the bob. A graph of L against T² is a straight line through the origin with slope g / 4π².'],
      precautions: 'Keep the angle small (under 10°). Let the bob swing in one vertical plane, without spinning. Start timing at the mean position. Time 20 oscillations to cut your reaction-time error.' },
    book: { title: 'Expt. — Simple Pendulum', lines: ['Aim: to find g using a simple pendulum.', 'Bob dia (vernier) = 2.00 cm,  r = 1.00 cm', 'L = thread length + r', 'T = 2π √(L/g)  →  g = 4π² L / T²', 'Precautions: θ < 10°, time 20 osc.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'L (cm)', get: function (r) { return (r.L * 100).toFixed(1); } },
        { label: 't₂₀ (s)', get: function (r) { return r.t.toFixed(2); } }, { label: 'T (s)', get: function (r) { return r.T.toFixed(3); } }, { label: 'T² (s²)', get: function (r) { return (r.T * r.T).toFixed(3); } }] },
    graph: { x: function (r) { return r.T * r.T; }, y: function (r) { return r.L; }, xlabel: 'T² (s²)', ylabel: 'L (m)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) { if (rows.length < 2) return null; var k = S.fit.origin(rows.map(function (r) { return [r.T * r.T, r.L]; }));
      return { label: 'g', value: 4 * Math.PI * Math.PI * k, unit: 'm/s²', digits: 2, truth: p.g, note: 'From the slope of L against T².' }; },
    tol: 0.02,
    chips: ['Why must the angle be small?', 'What is effective length?', 'Why time 20 oscillations?', 'Check my readings', 'Why is my g different from 9.8?'],
    viva: [['Why do we time 20 oscillations instead of one?', ['It reduces the effect of reaction-time error', 'The pendulum speeds up later', 'One oscillation cannot be timed'], 0, 'Your reaction error is shared over 20 oscillations.']],
    askState: function () { return { thread_length_cm: st.threadCm, effective_length_cm: +(effL() * 100).toFixed(1), bob_diameter_cm: 2.0, angle_now_deg: +(sim.y[0] / DEG).toFixed(1),
      swinging: running, stopwatch_running: watch.on, stopwatch_s: +watch.t.toFixed(2), oscillations_counted: n }; },

    steps: [
      { id: 'setup', title: 'Set up', view: 'ruler', render: function (u) {
          u.h2('Set up the pendulum');
          u.task('1. Measure the bob with the vernier callipers', st.diaDone, st.diaDone ? 'Diameter = 2.00 cm, radius r = 1.00 cm' : 'Not done yet')
            .add(u.button(st.diaDone ? 'Measured' : 'Measure the bob', function () { st.diaDone = true; S.focus('vc'); S.render(); }, !st.diaDone, st.diaDone));
          var t2 = u.task('2. Set the thread length', st.measured, st.measured ? 'Thread ' + st.threadCm.toFixed(1) + ' cm + r 1.0 cm = L ' + (effL() * 100).toFixed(1) + ' cm' : 'Pull the thread through the cork, then check it on the metre scale');
          u.slider('Thread length', 40, 98, 0.5, function () { return st.threadCm; }, function (v) { st.threadCm = v; st.measured = false; stopBob(); }, 'cm');
          u.row(u.button('Read it on the metre scale', function () { st.measured = true; S.focus('ruler'); S.render(); }));
          u.note('Effective length L = thread length + radius of the bob. Forgetting the radius makes g come out about 1–2% low.');
          u.next('Next: release the bob', st.diaDone && st.measured);
        },
        ok: function () { return st.diaDone && st.measured; },
        auto: function () { st.diaDone = true; st.threadCm = 79; st.measured = true; return Promise.resolve(); } },
      { id: 'release', title: 'Release', view: 'swing', render: function (u) {
          u.h2('Displace and release');
          u.p('Choose the angle, then let the hand pull the bob aside and let it go. You can also drag the bob yourself. Read the angle on the protractor.');
          var warn;
          u.slider('Angle to pull the bob to', 0, 25, 0.5, function () { return Math.round(st.target / DEG * 2) / 2; }, function (v) { st.target = v * DEG; if (warn) warn.hidden = v <= 10; }, '°');
          warn = u.note('Over 10° is too large: T = 2π√(L/g) holds only for small angles. Bring it under 10°.'); warn.hidden = st.target <= 10 * DEG;
          u.row(u.button(running ? 'Swinging…' : 'Pull and release the bob', function () {
              if (st.target < 0.03) { S.say('Choose an angle first (3° to 8° is ideal).'); return; }
              if (st.target > 10 * DEG + 1e-9) { S.say('That angle is over 10°. Bring it under 10° first.'); return; }
              release(st.target); S.render(); }, true, running || S.hand.busy),
            u.button('Stop the bob', function () { stopBob(); S.render(); }, false, !running));
          u.next('Next: time 20 oscillations', st.released);
        },
        ok: function () { return running; },
        auto: function () { st.target = 6 * DEG; return release(st.target); } },
      { id: 'time', title: 'Time it', view: 'sw', render: function (u) {
          u.h2('Time 20 oscillations');
          u.p('Press START on the stopwatch (tap the green button on the bench, or below) as the bob passes the mean position. Count 20 full oscillations, then press STOP.');
          u.live(function () { return watch.t.toFixed(2) + ' s · ' + n + ' oscillations'; });
          u.row(u.button(watch.on ? 'STOP' : 'START', function () { pressWatch(); }, true, !running && !watch.on), u.button('Reset', function () { if (!watch.on) { watch.t = 0; n = 0; } }, false, watch.on));
          if (!running && !watch.on) u.note('The bob is at rest. Change the length in step 2 and release it again for the next reading.');
          u.h3('Observation table'); u.table();
          u.row(u.button('Change the length for the next reading', function () { S.go(1); }));
          u.next('Next: plot the graph', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 lengths recorded (5 is better).');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          var lengths = [60, 70, 80, 90];
          return lengths.reduce(function (pr, Lc) { return pr.then(function () {
            st.threadCm = Lc; st.measured = true; stopBob();
            return release(6 * DEG).then(function () { S.advance(0.5); return pressWatch(); })
              .then(function () { S.advance(120, function () { return n >= 20; }); return pressWatch(); }); }); }, Promise.resolve()); } },
    ],

    tick: function (dt) {
      p.L = effL();
      if (running) { K.step(sim, p, dt);
        var s = Math.sign(sim.y[0]); if (s && s !== lastSign && watch.on) { halves++; if (halves % 2 === 0) n++; } if (s) lastSign = s; }
      var L = p.L, th = sim.y[0], bx = PIVOT.x + L * Math.sin(th), by = PIVOT.y - L * Math.cos(th);
      bob.position.set(bx, by, 0); bob.rotation.z = th;
      var top = PIVOT.clone(), bot = new T.Vector3(bx - (BOB_R + .0045) * Math.sin(th), by + (BOB_R + .0045) * Math.cos(th), 0), d = bot.clone().sub(top);
      thread.position.copy(top).add(bot).multiplyScalar(0.5); thread.scale.set(1, d.length(), 1); thread.quaternion.setFromUnitVectors(up, d.normalize());
      bobShadow.position.set(bx, 0.0009, 0); var hg = Math.max(0.05, by); bobShadow.scale.setScalar(0.6 + hg * 1.4); bobShadow.material.opacity = Math.max(0.05, 0.4 - hg * 0.35);
      hudL.set((effL() * 100).toFixed(1) + ' cm'); hudA.set((th / DEG).toFixed(1) + '°'); hudN.set(String(n));
    },
  };
});
