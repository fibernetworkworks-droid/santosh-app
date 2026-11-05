/* Prayogshala studio module: the bar (compound) pendulum (B.Sc. mechanics).
   A heavy wall bracket on a steel pillar carries a hardened knife edge. A uniform metal bar about a metre long, drilled
   with holes every 5 cm, hangs on the knife edge through one of them; its centre of gravity is marked in red. A metre
   scale standing beside the bar reads the knife edge and the centre-of-gravity mark, so h is their difference. A
   telescope on a stand carries a vertical cross-wire to count the swings against, and a digital stopwatch times twenty.
   The gloved hand lifts the bar off the knife edge onto another hole and draws it aside to start it swinging.
   Physics: the `barpend` kernel of the mech_ug pack - T = 2π√((k² + h²)/(g h)) with k² = L²/12 for a uniform bar.
   Every number is read from the lab's params. */
HoolaStudio.define('bar-pendulum', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.barpend;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('barpend');
  var kh = (S.lab.knobs || []).filter(function (q) { return q.param === 'h'; })[0] || { min: 5, max: 45, k: 0.01 };
  var HMIN = Math.round(kh.min * (kh.k || 1) * 1000) / 1000, HMAX = Math.round(kh.max * (kh.k || 1) * 1000) / 1000;
  var STEP = 0.05;
  var HOLES = [];
  for (var hv = HMIN; hv <= HMAX + 1e-9; hv = Math.round((hv + STEP) * 1000) / 1000) HOLES.push(Math.round(hv * 1000) / 1000);
  if (HOLES.length < 3) HOLES = [HMIN, (HMIN + HMAX) / 2, HMAX];
  var AMP = Math.max(2, Math.min(10, Math.round(p.th0 * 180 / Math.PI)));
  var LB = p.Lb;
  var st = { hi: HOLES.indexOf(0.35) >= 0 ? HOLES.indexOf(0.35) : Math.floor(HOLES.length / 2), read: [null, null], cyc: 0, swinging: false };
  var sim, prevSign = 1, ready = false;
  p.h = HOLES[st.hi];

  // ---------- geometry. The knife edge is at (XP, PIV, ZP); the bar's centre of gravity hangs h below it.
  var XP = 0.05, ZP = -0.22, PIV = 1.1, BW = 0.03, BT = 0.009;
  var pillar = new T.Group(); S.scene.add(pillar);
  var foot = S.rounded(0.32, 0.24, 0.03, 0.01, M.iron); foot.rotation.x = -Math.PI / 2; foot.position.set(XP - 0.3, 0.015, ZP); pillar.add(foot);
  var post = S.mesh(new T.CylinderGeometry(0.02, 0.024, PIV + 0.1, 28), M.chrome); post.position.set(XP - 0.3, (PIV + 0.1) / 2 + 0.03, ZP); pillar.add(post);
  var brkt = S.mesh(new T.BoxGeometry(0.34, 0.035, 0.07), M.iron); brkt.position.set(XP - 0.13, PIV + 0.05, ZP); pillar.add(brkt);
  S.contact(0.46, 0.32, XP - 0.3, ZP, 0.55);
  var lbl = S.label('BAR  PENDULUM', { w: 0.12, ratio: 0.14, color: '#d7dbe0', weight: 700 });
  lbl.position.set(XP - 0.13, PIV + 0.085, ZP + 0.036); pillar.add(lbl);

  // the knife edge: a hardened steel wedge pointing up, with its own small clamp
  var knife = new T.Group(); S.scene.add(knife);
  var kb = S.mesh(new T.BoxGeometry(0.05, 0.03, 0.05), M.iron); kb.position.y = PIV - 0.028; knife.add(kb);
  var wedge = S.mesh(new T.ConeGeometry(0.009, 0.022, 4), new T.MeshStandardMaterial({ color: 0xd7dbe0, roughness: 0.08, metalness: 1 }));
  wedge.rotation.y = Math.PI / 4; wedge.position.y = PIV - 0.004; knife.add(wedge);
  knife.position.set(XP, 0, ZP);

  // the swinging bar: a group whose origin is the knife edge
  var swing = new T.Group(); swing.position.set(XP, PIV, ZP); S.scene.add(swing);
  var barM = new T.MeshStandardMaterial({ color: 0xb7bcc2, roughness: 0.3, metalness: 0.85 });
  var bar = S.mesh(new T.BoxGeometry(BW, LB, BT), barM); swing.add(bar);
  var holeM = new T.MeshStandardMaterial({ color: 0x23262b, roughness: 0.9 });
  var holes = [];
  for (var i = 0; i < Math.round(LB / STEP) - 1; i++) {
    var yy = -LB / 2 + STEP * (i + 1);
    var hm = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, BT + 0.002, 14), holeM, false);
    hm.rotation.x = Math.PI / 2; hm.position.set(0, yy, 0); swing.add(hm); holes.push(hm);
  }
  var cgM = new T.MeshStandardMaterial({ color: 0xc0392b, roughness: 0.5 });
  var cg = S.mesh(new T.BoxGeometry(BW + 0.004, 0.0035, BT + 0.004), cgM, false); swing.add(cg);
  var cgTag = S.label('C.G.', { w: 0.028, ratio: 0.32, color: '#c0392b', weight: 700 });
  swing.add(cgTag);
  var flag = S.mesh(new T.BoxGeometry(0.004, 0.05, BT + 0.004), new T.MeshStandardMaterial({ color: 0xf6f3ea, roughness: 0.9 }), false);
  swing.add(flag);

  // the vertical scale beside the bar: zero at the top (y = RTOP), so a mark at height y reads (RTOP - y) * 100 cm
  var RLEN = 1.28, RTOP = 1.3, RX = XP - 0.1, RZ = ZP - 0.02;
  var ruler = S.ruler(RLEN, { title: 'VERTICAL SCALE · cm · LC 1 mm', labelEvery: 10 });
  ruler.position.set(RX, RTOP - RLEN, RZ); S.scene.add(ruler);
  var rfoot = S.rounded(0.085, 0.075, 0.03, 0.008, M.darkWood); rfoot.rotation.x = -Math.PI / 2;
  rfoot.position.set(RX, 0.015, RZ); S.scene.add(rfoot); S.contact(0.13, 0.12, RX, RZ, 0.5);
  function cmAt(y) { return (RTOP - y) * 100; }

  // the telescope with a vertical cross-wire
  var tele = new T.Group(); S.scene.add(tele);
  var tfoot = S.rounded(0.1, 0.09, 0.025, 0.008, M.iron); tfoot.rotation.x = -Math.PI / 2; tfoot.position.y = 0.012; tele.add(tfoot);
  var tpost = S.mesh(new T.CylinderGeometry(0.009, 0.011, 0.5, 18), M.chrome); tpost.position.y = 0.27; tele.add(tpost);
  var ttube = S.mesh(new T.CylinderGeometry(0.017, 0.017, 0.16, 22), M.black); ttube.rotation.x = Math.PI / 2; ttube.position.set(0, 0.5, 0.0); tele.add(ttube);
  var teye = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.03, 18), M.blackPlastic || M.black); teye.rotation.x = Math.PI / 2; teye.position.set(0, 0.5, 0.095); tele.add(teye);
  tele.position.set(XP + 0.26, 0, 0.1); S.contact(0.14, 0.13, XP + 0.26, 0.1, 0.5);

  var watch = S.stopwatch([XP - 0.46, 0.035, 0.12], [-1.15, 0.25, -0.1]);

  S.addApparatus('pillar', pillar, 'Pillar and bracket', 'The knife edge must rest on something quite rigid: a support that gives way absorbs part of the swing.');
  S.addApparatus('knife', knife, 'Knife edge', 'A hardened steel wedge. The bar rests on it through one of its holes, and that line is the axis of suspension.');
  S.addApparatus('bar', swing, 'Uniform metal bar', 'A bar ' + (LB * 100).toFixed(0) + ' cm long with holes every ' + (STEP * 100).toFixed(0)
    + ' cm. For a uniform bar the radius of gyration about the centre is k = L/√12 = ' + (LB / Math.sqrt(12) * 100).toFixed(1) + ' cm.');
  S.addApparatus('ruler', ruler, 'Metre scale', 'Reads the knife edge and the centre-of-gravity mark: h is their difference. Least count 1 mm.');
  S.addApparatus('tele', tele, 'Telescope with a cross-wire', 'Gives you one fixed line to count against, so you are not fooled by your own parallax.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Least count 0.01 s. Twenty oscillations are timed, so the reaction time is divided by twenty.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudH = S.hudCard('h from the C.G.'), hudA = S.hudCard('Angle'), hudC = S.hudCard('Oscillations');

  // ---------- state
  function applyHole(i) {
    st.hi = i; p.h = HOLES[i];
    sim = K.init(p); sim.y = [0, 0];
    st.cyc = 0; st.swinging = false; st.read = [null, null];
    watch.on = false; watch.t = 0; prevSign = 1;
    bar.position.y = -p.h;
    cg.position.set(0, -p.h, 0);
    cgTag.position.set(0.034, -p.h, BT / 2 + 0.002);
    flag.position.set(0, -p.h - LB / 2 + 0.03, 0);
  }
  function Tcalc() { return 2 * Math.PI * Math.sqrt((LB * LB / 12 + p.h * p.h) / (p.g * p.h)); }
  function moving() { return Math.abs(sim.y[1]) > 0.01 || Math.abs(sim.y[0]) > 0.01; }

  function setHole(i) {
    if (S.hand.busy) return Promise.resolve();
    if (watch.on) { S.say('The stopwatch is running. Stop it first.'); return Promise.resolve(); }
    if (moving()) { S.say('Stop the bar before you lift it off the knife edge.'); return Promise.resolve(); }
    applyHole(i);
    S.say('The bar now hangs through the hole ' + (p.h * 100).toFixed(0) + ' cm from its centre of gravity. Measure h on the scale.');
    S.render();
    return Promise.resolve();
  }
  function readMark(which) {                      // 0 = the knife edge, 1 = the centre-of-gravity mark
    var y = which === 0 ? PIV : PIV - p.h;
    st.read[which] = Math.round(cmAt(y) * 10) / 10;
    if (bothRead()) S.say('Knife edge ' + st.read[0].toFixed(1) + ' cm, C.G. mark ' + st.read[1].toFixed(1) + ' cm, so h = ' + hCm().toFixed(1) + ' cm.');
    else S.say((which === 0 ? 'The knife edge' : 'The C.G. mark') + ' reads ' + st.read[which].toFixed(1) + ' cm on the scale.');
    if (ready) S.render();
  }
  function bothRead() { return st.read[0] !== null && st.read[1] !== null; }
  function hCm() { return bothRead() ? Math.round((st.read[1] - st.read[0]) * 10) / 10 : 0; }

  function startSwing() {
    if (S.hand.busy) return Promise.resolve();
    if (!bothRead()) { S.say('Measure h on the metre scale first.'); return Promise.resolve(); }
    if (Math.abs(sim.y[1]) > 0.02) { S.say('The bar is still swinging. Let it settle, or stop it by hand.'); return Promise.resolve(); }
    var a0 = sim.y[0], a1 = p.th0, R = p.h + LB / 2 - 0.05;
    function at(k) { var a = a0 + (a1 - a0) * k; return new T.Vector3(XP + Math.sin(a) * R, PIV - Math.cos(a) * R, ZP + BT / 2 + 0.01); }
    st.swinging = false;
    return S.hand.pinchMove(at(0), at, function (k) { sim.y = [a0 + (a1 - a0) * k, 0]; }, { ms: 1000, hold: 240, mode: 'front' })
      .then(function () {
        sim.y = [p.th0, 0]; st.swinging = true; st.cyc = 0; prevSign = 1;
        S.say('Drawn aside about ' + AMP + '° and let go. Count the swings past the cross-wire.');
        S.render();
      });
  }
  function stopBar() {
    if (S.hand.busy) return Promise.resolve();
    sim.y = [0, 0]; st.swinging = false; watch.on = false; watch.t = 0; st.cyc = 0; S.render();
    return Promise.resolve();
  }
  function pressWatch() {
    if (S.hand.busy) return Promise.resolve();
    if (!watch.on && !st.swinging) { S.say('Set the bar swinging first.'); return Promise.resolve(); }
    return S.hand.tap(watch.start).then(function () {
      S.click(2400);
      if (!watch.on) { watch.t = 0; watch.on = true; st.cyc = 0; S.say('Started. Count twenty complete oscillations.'); }
      else { watch.on = false; record(); }
      S.render();
    });
  }
  function record() {
    var t = Math.round(watch.t * 100) / 100;
    if (st.cyc < 20) { S.say('Only ' + st.cyc + ' oscillations were counted. Time a full twenty.'); return; }
    var Tp = watch.t / 20;
    S.addRow({ h: hCm() / 100, hcm: hCm(), t20: t, T: Tp });
    S.say('Written in your record book: h = ' + hCm().toFixed(1) + ' cm, 20 oscillations in ' + t.toFixed(2) + ' s, T = ' + Tp.toFixed(3) + ' s.');
  }
  function timeTwenty() {
    S.advance(4 * Tcalc() + 5, function () { return sim.y[0] < 0 && sim.y[1] < 0; });
    return pressWatch().then(function () {
      S.advance(22 * Tcalc() + 10, function () { return st.cyc >= 20; });
      return pressWatch();
    });
  }
  function holesDone() { var o = {}; S.rows.forEach(function (q) { o[q.hcm.toFixed(1)] = 1; }); return Object.keys(o).length; }
  function pickButtons(u, after) {
    var r = u.row();
    HOLES.forEach(function (h, i) {
      if (i % 2 && i !== HOLES.length - 1) return;                 // every second hole keeps the row readable
      r.appendChild(u.button((h * 100).toFixed(0) + ' cm' + (st.hi === i ? ' ✓' : ''), function () { setHole(i).then(after); }, st.hi === i, S.hand.busy || watch.on));
    });
    return r;
  }

  applyHole(st.hi);

  var EXP = {
    camera: { pos: [0.8, 0.8, 1.5], look: [0.0, 0.6, -0.2] },
    views: {
      setup: [[0.78, 0.78, 1.45], [0.0, 0.6, -0.2]],
      knife: [[0.3, 1.2, 0.5], [XP - 0.03, 1.08, -0.22]],
      ruler: [[0.3, 0.8, 0.6], [XP - 0.08, 0.72, -0.22]],
      bar: [[0.5, 0.65, 0.95], [XP, 0.62, -0.2]],
      tele: [[0.5, 0.6, 0.7], [XP + 0.2, 0.5, 0.02]],
      sw: [[-0.1, 0.4, 0.5], [XP - 0.42, 0.1, 0.06]],
      book: [[-0.34, 0.5, 0.56], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'A rigid body free to swing about a horizontal axis is a compound pendulum. Its period depends on the distance '
        + 'h of its centre of gravity below the axis and on its radius of gyration k about a parallel axis through the centre of gravity.',
      formula: 'T = 2π√((k² + h²) / g h),   k² = L²/12',
      formulaNote: 'so g = 4π²(k² + h²) / (T² h). For this bar L = ' + (LB * 100).toFixed(0) + ' cm, so k = '
        + (LB / Math.sqrt(12) * 100).toFixed(2) + ' cm.',
      more: ['The bar swings like a simple pendulum of length (k² + h²)/h, called the equivalent length.',
        'The period is least when h = k, and it grows again both near the centre of gravity and near the end of the bar.',
        'Two different holes give the same period: they are the centre of suspension and the centre of oscillation, and the distance between them is the equivalent length.'],
      precautions: 'Seat the knife edge in the hole before letting go. Keep the swing below about 5° so the simple-harmonic '
        + 'formula holds, and stop the bar from swinging sideways. Time twenty oscillations, not one.'
    },
    book: {
      title: 'Expt. — Bar pendulum',
      lines: ['Aim: to find g and the radius of gyration with a bar pendulum.',
        'Bar length L = ' + (LB * 100).toFixed(0) + ' cm, so k² = L²/12 = ' + (LB * LB / 12).toFixed(5) + ' m²',
        'h = (knife-edge reading) − (C.G. reading)', 'T = t₂₀ / 20',
        'g = 4π²(k² + h²) / (T² h)', 'Amplitude kept to about ' + AMP + '°.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'h (cm)', get: function (r) { return r.hcm.toFixed(1); } },
        { label: 't₂₀ (s)', get: function (r) { return r.t20.toFixed(2); } },
        { label: 'T (s)', get: function (r) { return r.T.toFixed(3); } },
        { label: 'L_eq (cm)', get: function (r) { return ((LB * LB / 12 + r.h * r.h) / r.h * 100).toFixed(1); } }]
    },
    graph: {
      x: function (r) { return r.hcm; }, y: function (r) { return r.T; },
      xlabel: 'h (cm)', ylabel: 'T (s)', x0: 0, y0: 0, line: null
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var v = HK.CALCS.bar_g.fn(rows, p);
      if (!isFinite(v) || v <= 0) return null;
      return { label: 'g', value: v, unit: 'm/s²', digits: 3, truth: p.g, note: 'Mean of 4π²(k² + h²)/(T²h) over the holes used.' };
    },
    tol: 0.02,
    chips: ['Why is the period least when h = k?', 'What is the equivalent length?', 'Check my readings',
      'Why keep the amplitude small?', 'Why time twenty oscillations?'],
    viva: [['For a uniform bar of length L the radius of gyration about its centre is', ['L/√12', 'L/2', 'L/√3'], 0,
      'k² = L²/12 for a thin uniform bar.'],
      ['The period of a bar pendulum is a minimum when', ['h = k', 'h = 0', 'h = L/2'], 0,
        'T = 2π√((k²+h²)/gh) is least at h = k.']],
    askState: function () {
      return {
        hole_in_use_cm_from_cg: +(p.h * 100).toFixed(1), measured_h_cm: bothRead() ? hCm() : null,
        knife_edge_reading_cm: st.read[0], cg_reading_cm: st.read[1],
        angle_now_deg: +(sim.y[0] * 180 / Math.PI).toFixed(2), oscillations_counted: st.cyc,
        stopwatch_running: watch.on, stopwatch_s: +watch.t.toFixed(2),
        bar_length_cm: +(LB * 100).toFixed(1)
      };
    },

    steps: [
      { id: 'h', title: 'Measure h', view: 'ruler',
        render: function (u) {
          u.h2('Hang the bar and measure h');
          u.p('Put the knife edge through one of the holes. Then read the knife edge and the red centre-of-gravity mark '
            + 'on the metre scale: h is the difference.');
          pickButtons(u, function () { S.focus('knife'); });
          u.task('1. Read the knife edge', st.read[0] !== null, st.read[0] !== null ? st.read[0].toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read', function () { S.focus('knife'); readMark(0); }, st.read[0] === null, st.read[0] !== null));
          u.task('2. Read the C.G. mark', st.read[1] !== null, st.read[1] !== null ? st.read[1].toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read', function () { S.focus('ruler'); readMark(1); }, st.read[1] === null, st.read[1] !== null));
          if (bothRead()) u.formula('h = ' + st.read[1].toFixed(1) + ' − ' + st.read[0].toFixed(1) + ' = ' + hCm().toFixed(1) + ' cm');
          u.note('The centre of gravity was found first by balancing the bar on a knife edge: it is the red mark.');
          u.next('Next: set it swinging', bothRead());
        },
        ok: function () { return bothRead(); },
        auto: function () { readMark(0); readMark(1); return Promise.resolve(); } },

      { id: 'time', title: 'Swing and time', view: 'bar',
        render: function (u) {
          u.h2('Time twenty oscillations');
          u.p('The hand draws the bar aside about ' + AMP + '° and lets it go. Press START as the bar crosses the '
            + 'cross-wire, count twenty complete oscillations, then press STOP. Then move to another hole.');
          pickButtons(u, function () { S.focus('bar'); });
          u.task('Measure h for this hole', bothRead(), bothRead() ? 'h = ' + hCm().toFixed(1) + ' cm' : 'Not measured yet')
            .add(u.button('Measure it', function () { readMark(0); readMark(1); }, !bothRead(), bothRead()));
          u.row(u.button(st.swinging ? 'Start it again' : 'Draw aside and release', function () { startSwing(); }, !st.swinging, S.hand.busy || watch.on || !bothRead()),
            u.button(watch.on ? 'STOP' : 'START', function () { pressWatch(); }, watch.on, S.hand.busy || (!watch.on && !st.swinging)),
            u.button('Stop the bar', function () { stopBar(); }, false, S.hand.busy || watch.on));
          u.live(function () {
            return 'h = ' + (p.h * 100).toFixed(0) + ' cm · angle ' + (sim.y[0] * 180 / Math.PI).toFixed(1) + '° · '
              + st.cyc + ' of 20 oscillations · ' + watch.t.toFixed(2) + ' s';
          });
          u.h3('Observation table'); u.table();
          var n = holesDone();
          u.next('Next: work out g', n >= 3);
          if (n < 3) u.p(n + ' of at least 3 holes timed. Move the bar to another hole, measure h again and time it.');
        },
        ok: function () { return holesDone() >= 3; },
        auto: function () {
          var pick = [HOLES.length - 1, Math.floor(HOLES.length / 2), 1].filter(function (i, k, a) { return a.indexOf(i) === k && i >= 0; });
          return pick.reduce(function (pr, i) {
            return pr.then(stopBar).then(function () { return setHole(i); })
              .then(function () { readMark(0); readMark(1); return startSwing(); })
              .then(timeTwenty);
          }, Promise.resolve());
        } }
    ],

    tick: function (dt) {
      K.step(sim, p, dt);
      var s = sim.y[0] >= 0 ? 1 : -1;
      if (prevSign > 0 && s < 0) st.cyc++;
      prevSign = s;
      pose();
    },
    ready: function () { ready = true; }
  };
  function pose() {
    swing.rotation.z = -sim.y[0];
    hudH.set((p.h * 100).toFixed(0) + ' cm');
    hudA.set((sim.y[0] * 180 / Math.PI).toFixed(1) + '°');
    hudC.set(st.cyc + ' / 20');
  }
  pose();
  return EXP;
});
