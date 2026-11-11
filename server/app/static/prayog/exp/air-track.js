/* Prayogshala studio module: collisions on an air track (B.Sc. mechanics).
   A two-metre aluminium track blown full of air lifts two gliders clear of the metal, so friction is almost nothing.
   Each glider carries a 10 cm flag; three photo-gates across the track feed a digital timer that reads how long a flag
   takes to cross, and the flag's length divided by that time is the glider's speed. Spring bumpers make the collision
   nearly elastic; wax pads make the gliders stick together.
   The gloved hand fits the bumpers and gives glider 1 its push through a spring launcher.
   Physics: the `collide1d` kernel of the mech_ug pack - m₁u₁ = m₁v₁ + m₂v₂ with e = 1 or 0.
   Everything is read from the lab's params. */
HoolaStudio.define('air-track', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.collide1d;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('collide1d');
  var ku = (S.lab.knobs || []).filter(function (q) { return q.param === 'u1'; })[0] || { min: 0.15, max: 0.6, k: 1 };
  var UMIN = ku.min * (ku.k || 1), UMAX = ku.max * (ku.k || 1);
  var PUSH = [0, 1, 2].map(function (i) { return Math.round((UMIN + (UMAX - UMIN) * i / 2) * 100) / 100; });
  var FLAG = 0.1, TLC = 1e-4;                           // flag length (m) and the timer's least count (s)
  var st = { ui: 1, weighed: false, levelled: false, running: false, done: false, res: null };
  p.u1 = PUSH[st.ui];
  var sim = K.init(p), ready = false;

  // ---------- geometry: the track runs along x at y = TY, z = ZT
  var TY = 0.1, ZT = -0.12, TLEN = 1.8, GH = 0.06;
  var trackM = new T.MeshStandardMaterial({ color: 0xaeb4ba, roughness: 0.3, metalness: 0.9 });
  var track = S.rounded(TLEN, 0.09, 0.055, 0.008, trackM);
  track.rotation.x = -Math.PI / 2; track.position.set(0, TY - 0.0275, ZT); S.scene.add(track);
  S.contact(TLEN + 0.1, 0.2, 0, ZT, 0.5);
  [-1, 1].forEach(function (s) {
    var leg = S.rounded(0.06, 0.1, 0.05, 0.006, M.iron); leg.position.set(s * (TLEN / 2 - 0.1), 0.025, ZT); S.scene.add(leg);
    var sc = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.03, 14), M.chrome); sc.position.set(s * (TLEN / 2 - 0.1), 0.012, ZT); S.scene.add(sc);
    var stop = S.mesh(new T.BoxGeometry(0.012, 0.07, 0.07), M.iron); stop.position.set(s * (TLEN / 2 - 0.01), TY + 0.015, ZT); S.scene.add(stop);
  });
  var holes = new T.Group(); S.scene.add(holes);
  for (var hx = -TLEN / 2 + 0.08; hx < TLEN / 2 - 0.08; hx += 0.04) {
    var hm = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, 0.003, 8), M.black, false);
    hm.position.set(hx, TY + 0.0005, ZT); holes.add(hm);
  }
  var blower = new T.Group(); S.scene.add(blower);
  var bb = S.rounded(0.17, 0.13, 0.15, 0.01, new T.MeshStandardMaterial({ color: 0x3a4149, roughness: 0.55 }));
  bb.position.y = 0.065; blower.add(bb);
  var bgrill = S.mesh(new T.CylinderGeometry(0.045, 0.045, 0.01, 24), M.black); bgrill.rotation.z = Math.PI / 2; bgrill.position.set(0.086, 0.07, 0); blower.add(bgrill);
  blower.position.set(-TLEN / 2 - 0.12, 0, ZT + 0.02); S.contact(0.22, 0.2, -TLEN / 2 - 0.12, ZT + 0.02, 0.5);
  var hose = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.16, 16), new T.MeshStandardMaterial({ color: 0x2b3138, roughness: 0.85 }));
  hose.rotation.z = Math.PI / 2; hose.position.set(-TLEN / 2 + 0.03, TY - 0.02, ZT + 0.02); S.scene.add(hose);

  function makeGlider(col, label) {
    var g = new T.Group(); S.scene.add(g);
    var body = S.mesh(new T.BoxGeometry(0.11, GH, 0.105), new T.MeshStandardMaterial({ color: col, roughness: 0.35, metalness: 0.7 }));
    body.position.y = GH / 2; g.add(body);
    var sk1 = S.mesh(new T.BoxGeometry(0.11, 0.05, 0.006), new T.MeshStandardMaterial({ color: col, roughness: 0.35, metalness: 0.7 }));
    sk1.position.set(0, 0.025, 0.052); g.add(sk1);
    var sk2 = sk1.clone(); sk2.position.z = -0.052; g.add(sk2);
    var flagM = S.mesh(new T.BoxGeometry(FLAG, 0.03, 0.002), new T.MeshStandardMaterial({ color: 0x1b1b1d, roughness: 0.8 }));
    flagM.position.set(0, GH + 0.018, 0); g.add(flagM);
    var tag = S.label(label, { w: 0.03, ratio: 0.5, color: '#1b1b1d', bg: '#f6f3ea', weight: 700 });
    tag.position.set(0, GH / 2, 0.054); g.add(tag);
    g.userData.bumper = null;
    return g;
  }
  var g1 = makeGlider(0xcdd2d7, '1'), g2 = makeGlider(0xd8c08a, '2');
  function bumperOn(g, elastic) {
    if (g.userData.bumper) { g.remove(g.userData.bumper); g.userData.bumper = null; }
    var b = elastic
      ? S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.022, 10), M.chrome, false)
      : S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.01, 14), new T.MeshStandardMaterial({ color: 0xe6d9a8, roughness: 0.95 }), false);
    b.rotation.z = Math.PI / 2;
    b.position.set(g === g1 ? 0.066 : -0.066, GH / 2, 0);
    g.add(b); g.userData.bumper = b;
  }

  function gate(x, n) {
    var g = new T.Group(); S.scene.add(g);
    var post = S.rounded(0.018, 0.16, 0.03, 0.004, new T.MeshStandardMaterial({ color: 0x2b3138, roughness: 0.6 }));
    post.position.y = 0.08; g.add(post);
    var arm = S.rounded(0.018, 0.03, 0.1, 0.004, new T.MeshStandardMaterial({ color: 0x2b3138, roughness: 0.6 }));
    arm.position.set(0, 0.15, 0.05); g.add(arm);
    var led = S.mesh(new T.SphereGeometry(0.004, 10, 8), new T.MeshStandardMaterial({ color: 0xc0392b, emissive: 0x7a1f1f, roughness: 0.4 }), false);
    led.position.set(0, 0.165, 0.0); g.add(led);
    var tag = S.label('G' + n, { w: 0.02, ratio: 0.5, color: '#e6e7ea', weight: 700 }); tag.position.set(0, 0.11, 0.016); g.add(tag);
    g.position.set(x, 0.02, ZT - 0.075);
    S.contact(0.06, 0.06, x, ZT - 0.075, 0.3);
    return g;
  }
  var GX = [-0.6, 0.12, 0.62];
  var gates = GX.map(function (x, i) { return gate(x, i + 1); });

  var tim = new T.Group(); S.scene.add(tim);
  var tbody = S.rounded(0.26, 0.15, 0.07, 0.008, new T.MeshStandardMaterial({ color: 0x1b1b1d, roughness: 0.5 }));
  tbody.rotation.x = -0.5; tbody.position.y = 0.035; tim.add(tbody);
  var lcd = S.liveTex(640, 200), last = '';
  function drawLcd(a, b, c) {
    var txt = a + '|' + b + '|' + c; if (txt === last) return; last = txt;
    lcd.draw(function (x) {
      var gr = x.createLinearGradient(0, 0, 0, 200); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
      x.fillStyle = gr; x.fillRect(0, 0, 640, 200);
      x.font = '700 46px "JetBrains Mono", monospace'; x.fillStyle = '#1b2116'; x.textAlign = 'left';
      x.fillText('G1  ' + a, 24, 62); x.fillText('G2  ' + b, 24, 118); x.fillText('G3  ' + c, 24, 174);
      x.font = '600 22px "Public Sans", sans-serif'; x.textAlign = 'right'; x.fillText('FLAG 10.0 cm', 616, 186);
    });
  }
  var scr = new T.Mesh(new T.PlaneGeometry(0.19, 0.06), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
  scr.rotation.x = -0.5; scr.position.set(0, 0.072, 0.024); tim.add(scr);
  tim.position.set(0.56, 0, 0.14); S.contact(0.3, 0.2, 0.56, 0.14, 0.5);

  var bal = S.rounded(0.16, 0.13, 0.05, 0.006, new T.MeshStandardMaterial({ color: 0x3a4149, roughness: 0.55 }));
  bal.position.set(0.0, 0.025, 0.16); S.scene.add(bal);
  var balL = S.label('BALANCE', { w: 0.07, ratio: 0.2, color: '#e6e7ea', weight: 600 }); balL.rotation.x = -Math.PI / 2;
  balL.position.set(0.0, 0.051, 0.16); S.scene.add(balL);
  S.contact(0.2, 0.17, 0.0, 0.16, 0.4);

  S.addApparatus('track', track, 'Air track', 'Air blown out of the holes lifts the gliders a fraction of a millimetre clear of the metal, so nothing along the track slows them.');
  S.addApparatus('g1', g1, 'Glider 1', 'The glider that is pushed. Its mass m₁ = ' + (p.m1 * 1000).toFixed(0) + ' g, weighed on the balance.');
  S.addApparatus('g2', g2, 'Glider 2', 'The glider that waits at rest. Its mass is the unknown of this experiment.');
  S.addApparatus('gates', gates[1], 'Photo-gates', 'Each gate times how long the 10 cm flag takes to cross it; flag length divided by that time is the speed.');
  S.addApparatus('tim', tim, 'Digital timer', 'Reads each gate to ' + (TLC * 1000).toFixed(1) + ' ms.');
  S.addApparatus('bal', bal, 'Balance', 'Weighs glider 1. The second glider’s mass is what the collision is used to find.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudU = S.hudCard('Push u₁'), hudB = S.hudCard('Bumpers'), hudP = S.hudCard('Momentum');

  // ---------- state
  function elastic() { return p.e >= 0.5; }
  function applyBumpers() { bumperOn(g1, elastic()); bumperOn(g2, elastic()); }
  function setBumper(e) {
    if (S.hand.busy || st.running) return Promise.resolve();
    var from = new T.Vector3(-0.1, 0.16, ZT + 0.1);
    return S.hand.pinchMove(from, function (k) { return from.clone().add(new T.Vector3(0.04 * k, -0.04 * k, -0.06 * k)); },
      function (k) { if (k > 0.7) { p.e = e; applyBumpers(); } }, { ms: 700, hold: 160, mode: 'top' })
      .then(function () {
        p.e = e; applyBumpers(); reset();
        S.say(elastic() ? 'Spring bumpers fitted: the collision will be nearly elastic.' : 'Wax pads fitted: the gliders will stick together.');
        S.render();
      });
  }
  function setPush(i) {
    if (S.hand.busy || st.running) return Promise.resolve();
    st.ui = i; p.u1 = PUSH[i]; reset();
    S.say('Launcher set to give glider 1 about ' + p.u1.toFixed(2) + ' m/s.');
    if (ready) S.render();
    return Promise.resolve();
  }
  function weigh() { st.weighed = true; S.say('Glider 1 weighs ' + (p.m1 * 1000).toFixed(0) + ' g on the balance.'); if (ready) S.render(); }
  function level() { st.levelled = true; S.say('Track levelled: a glider left alone does not drift either way.'); if (ready) S.render(); }
  function reset() {
    sim = K.init(p); st.running = false; st.done = false; st.res = null; drawLcd('-.----', '-.----', '-.----'); pose();
  }
  function speeds() {                                   // what the three gates actually read
    var v = K.view(sim, p);
    function t(u) { return Math.floor(Math.abs(FLAG / u) / TLC + 0.5) * TLC; }
    var u1 = p.u1, v1 = K.measure(p).v1, v2 = K.measure(p).v2;
    return { t1: t(u1), t2: v1 === 0 ? null : t(v1), t3: t(v2),
      u1: FLAG / t(u1), v1: v1 === 0 ? 0 : (v1 < 0 ? -1 : 1) * FLAG / t(v1), v2: FLAG / t(v2) };
  }
  function launch() {
    if (S.hand.busy || st.running) return Promise.resolve();
    if (!st.weighed || !st.levelled) { S.say('Weigh glider 1 and level the track first.'); return Promise.resolve(); }
    var from = new T.Vector3(-0.78, 0.14, ZT + 0.09);
    return S.hand.pinchMove(from, function (k) { return from.clone().add(new T.Vector3(0.07 * k, 0, 0)); },
      function () {}, { ms: 600, hold: 120, mode: 'side' }).then(function () {
        reset(); st.running = true;
        S.say('Glider 1 is away. Watch it through the gates.'); S.render();
      });
  }
  function recordRun() {
    if (!st.done || !st.res) { S.say('Run a collision first.'); return; }
    var r = st.res;
    S.addRow({ u1: r.u1, v1: r.v1, v2: r.v2, e: p.e });
    S.say('Written in your record book: u₁ = ' + r.u1.toFixed(3) + ', v₁ = ' + r.v1.toFixed(3)
      + ', v₂ = ' + r.v2.toFixed(3) + ' m/s.');
    st.done = false; st.res = null; S.render();
  }
  function runOnce() {
    return launch().then(function () {
      S.advance(30, function () { return st.done; });
      recordRun();
      return Promise.resolve();
    });
  }
  function runsDone() { return S.rows.length; }

  applyBumpers(); reset();

  var EXP = {
    camera: { pos: [0.3, 1.05, 1.95], look: [-0.12, 0.14, -0.1] },
    views: {
      setup: [[0.28, 1.0, 1.9], [-0.12, 0.14, -0.1]],
      track: [[0.0, 0.72, 1.3], [-0.15, 0.13, -0.1]],
      g1: [[-0.48, 0.4, 0.5], [-0.62, 0.13, -0.11]],
      gates: [[0.22, 0.52, 0.8], [0.0, 0.15, -0.11]],
      tim: [[0.78, 0.42, 0.62], [0.52, 0.07, 0.1]],
      bal: [[0.1, 0.36, 0.5], [0.0, 0.05, 0.14]],
      book: [[-0.34, 0.5, 0.56], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'Nothing pushes the pair along the track while they strike, so the total momentum of the two gliders '
        + 'cannot change, whatever happens to the kinetic energy.',
      formula: 'm₁u₁ = m₁v₁ + m₂v₂',
      formulaNote: 'so m₂ = m₁(u₁ − v₁)/v₂, with m₁ = ' + (p.m1 * 1000).toFixed(0)
        + ' g and each speed = 10 cm flag ÷ the gate time',
      more: ['With spring bumpers the collision is nearly elastic and the kinetic energy is almost unchanged; with wax pads the gliders stick and a definite amount of kinetic energy becomes heat.',
        'The coefficient of restitution e = (v₂ − v₁)/u₁ is 1 for the springs and 0 for the pads.',
        'A light glider striking a heavier one elastically comes back: v₁ = (m₁ − m₂)u₁/(m₁ + m₂) is then negative.'],
      precautions: 'Level the track before anything else: on a sloping track a glider accelerates and every speed is wrong. '
        + 'Push the glider once and let go cleanly - a hand still on it when it passes the first gate spoils u₁.'
    },
    book: {
      title: 'Expt. — Collisions on an air track',
      lines: ['Aim: to check the conservation of momentum and find the mass of the second glider.',
        'm₁ = ' + (p.m1 * 1000).toFixed(0) + ' g (balance)', 'Flag length = ' + (FLAG * 100).toFixed(1) + ' cm',
        'speed = flag length ÷ gate time', 'm₁u₁ = m₁v₁ + m₂v₂',
        'm₂ = m₁(u₁ − v₁)/v₂'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'u₁ (m/s)', get: function (r) { return r.u1.toFixed(3); } },
        { label: 'v₁ (m/s)', get: function (r) { return r.v1.toFixed(3); } },
        { label: 'v₂ (m/s)', get: function (r) { return r.v2.toFixed(3); } },
        { label: 'bumpers', get: function (r) { return r.e >= 0.5 ? 'springs' : 'wax'; } }]
    },
    graph: {
      x: function (r) { return r.u1; }, y: function (r) { return r.v2; },
      xlabel: 'u₁ (m/s)', ylabel: 'v₂ (m/s)', x0: 0, y0: 0,
      line: function (pts) { var s = S.fit.origin(pts); return function (x) { return s * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var v = HK.CALCS.coll_m2.fn(rows, p);
      if (!isFinite(v) || v <= 0) return null;
      return { label: 'm₂ of the second glider', value: v, unit: 'kg', digits: 4, truth: p.m2,
        note: 'Mean of m₁(u₁ − v₁)/v₂ over the runs.' };
    },
    tol: 0.02,
    chips: ['Why must the track be level?', 'What is conserved in a sticking collision?', 'Check my readings',
      'Why does glider 1 bounce back?', 'How is a speed got from a gate time?'],
    viva: [['In a perfectly inelastic collision what is conserved?',
      ['Momentum only', 'Kinetic energy only', 'Both', 'Neither'], 0,
      'No outside force acts along the track, so momentum is conserved; some kinetic energy becomes heat.'],
      ['A photo-gate gives a speed by', ['dividing the flag’s length by the time it blocks the beam', 'counting rotations', 'weighing the glider'], 0,
        'speed = flag length / gate time.']],
    askState: function () {
      var v = K.view(sim, p), r = st.res;
      return {
        push_u1_m_s: p.u1, bumpers: elastic() ? 'springs (elastic)' : 'wax pads (sticking)',
        glider1_weighed: st.weighed, track_levelled: st.levelled, run_in_progress: st.running,
        collision_happened: v.hit >= 1,
        momentum_before: +v.p_before.toFixed(4), momentum_after: +v.p_after.toFixed(4),
        gate_speeds: r ? { u1: +r.u1.toFixed(3), v1: +r.v1.toFixed(3), v2: +r.v2.toFixed(3) } : null
      };
    },

    steps: [
      { id: 'set', title: 'Set up', view: 'track',
        render: function (u) {
          u.h2('Level the track and weigh glider 1');
          u.p('On a sloping track a glider picks up speed on its own and every reading is wrong, so the track is levelled '
            + 'first with the screws in its feet.');
          u.task('Level the track', st.levelled, st.levelled ? 'A free glider does not drift' : 'Not levelled yet')
            .add(u.button('Level it', function () { S.focus('track'); level(); }, !st.levelled, st.levelled));
          u.task('Weigh glider 1', st.weighed, st.weighed ? (p.m1 * 1000).toFixed(0) + ' g' : 'Not weighed yet')
            .add(u.button('Weigh it', function () { S.focus('bal'); weigh(); }, !st.weighed, st.weighed));
          u.h3('Bumpers');
          u.row(u.button('Spring bumpers (elastic)' + (elastic() ? ' ✓' : ''), function () { setBumper(1); }, elastic(), S.hand.busy || st.running),
            u.button('Wax pads (sticking)' + (!elastic() ? ' ✓' : ''), function () { setBumper(0); }, !elastic(), S.hand.busy || st.running));
          u.next('Next: run the collision', st.levelled && st.weighed);
        },
        ok: function () { return st.levelled && st.weighed; },
        auto: function () { level(); weigh(); return Promise.resolve(); } },

      { id: 'run', title: 'Collide and time', view: 'gates',
        render: function (u) {
          u.h2('Push glider 1 into glider 2');
          u.p('The launcher gives glider 1 a steady push. The three gates read its speed before the collision and both '
            + 'gliders’ speeds after it.');
          var r = u.row();
          PUSH.forEach(function (q, i) {
            r.appendChild(u.button(q.toFixed(2) + ' m/s' + (st.ui === i ? ' ✓' : ''), function () { setPush(i); }, st.ui === i, S.hand.busy || st.running));
          });
          u.row(u.button('Spring bumpers' + (elastic() ? ' ✓' : ''), function () { setBumper(1); }, elastic(), S.hand.busy || st.running),
            u.button('Wax pads' + (!elastic() ? ' ✓' : ''), function () { setBumper(0); }, !elastic(), S.hand.busy || st.running));
          u.row(u.button(st.running ? 'Running…' : 'Push glider 1', function () { launch(); }, true, S.hand.busy || st.running),
            u.button('Write this run down', function () { recordRun(); }, false, S.hand.busy || !st.done));
          u.live(function () {
            var v = K.view(sim, p);
            return (v.hit >= 1 ? 'after the collision' : 'before the collision') + ' · momentum '
              + v.p_after.toFixed(4) + ' of ' + v.p_before.toFixed(4) + ' kg·m/s'
              + (st.res ? ' · u₁ ' + st.res.u1.toFixed(3) + ', v₁ ' + st.res.v1.toFixed(3) + ', v₂ ' + st.res.v2.toFixed(3) : '');
          });
          u.h3('Observation table'); u.table();
          u.next('Next: work out m₂', runsDone() >= 2);
          if (runsDone() < 2) u.p(runsDone() + ' of at least 2 runs recorded. Change the push or the bumpers and run it again.');
        },
        ok: function () { return runsDone() >= 2; },
        auto: function () {
          return [[2, 1], [1, 1], [1, 0]].reduce(function (pr, q) {
            return pr.then(function () { return setPush(q[0]); })
              .then(function () { return (q[1] >= 0.5) === elastic() ? Promise.resolve() : setBumper(q[1]); })
              .then(runOnce);
          }, Promise.resolve());
        } }
    ],

    tick: function (dt) {
      if (st.running) {
        K.step(sim, p, dt);
        var v = K.view(sim, p);
        if (v.hit >= 1 && !st.res) {
          st.res = speeds();
          drawLcd(st.res.t1.toFixed(4), st.res.t2 === null ? '--.----' : st.res.t2.toFixed(4), st.res.t3.toFixed(4));
        }
        if (v.x2 > TLEN / 2 - 0.3 || sim.t > 20) { st.running = false; st.done = !!st.res; S.render(); }
      }
      pose();
    },
    ready: function () { ready = true; }
  };
  function pose() {
    var v = K.view(sim, p);
    g1.position.set(-0.75 + v.x1, TY, ZT);
    g2.position.set(-0.75 + v.x2 + 0.12, TY, ZT);
    hudU.set(p.u1.toFixed(2) + ' m/s');
    hudB.set(elastic() ? 'springs' : 'wax');
    hudP.set(v.p_after.toFixed(4));
  }
  pose();
  return EXP;
});
