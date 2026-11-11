/* Prayogshala studio module: the torsion bench (B.Sc. mechanics).
   A cast base and steel pillar carry a rigid bracket. A thin wire hangs from the upper chuck; the lower chuck grips a
   heavy brass disc (or, for the inertia table, a light table with an irregular body clamped on it). A chalk mark on the
   rim and a fixed pin on a small stand are the pair you count oscillations against; a metre scale standing beside the
   wire reads both chucks, and a digital stopwatch times twenty oscillations.
   The gloved hand resets the wire in the chuck, reads the chucks on the scale and gives the body its small twist.
   Physics: the `torsion` kernel of the mech_ug pack - T = 2π√(I/C) with C = π η r⁴ / 2L. One rig serves both labs: the
   lab's own table.calc says whether the unknown is the wire's rigidity modulus η or the body's moment of inertia I.
   Every number is read from the lab's params, so a family of wires and bodies needs no new rig. */
HoolaStudio.define('torsional-pendulum', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.torsion;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('torsion');
  var CALC = (S.lab.table || {}).calc === 'torsion_I' ? 'torsion_I' : 'torsion_eta';
  var FOR_I = CALC === 'torsion_I';
  var SAMPLE = String((S.lab.variant || {}).sample || '');
  var WIRES = [[/brass/i, 'brass', 0xd4ad55, 0.3], [/copper/i, 'copper', 0xc8764a, 0.28],
    [/alumin/i, 'aluminium', 0xcdd2d6, 0.35], [/phosphor/i, 'phosphor bronze', 0xc08a4a, 0.3]];
  var WIRE = { name: 'steel', col: 0xc9ced3, rough: 0.25 };
  WIRES.forEach(function (w) { if (w[0].test(SAMPLE)) WIRE = { name: w[1], col: w[2], rough: w[3] }; });
  var BODY = FOR_I ? 'inertia table' : 'brass disc';
  var kl = (S.lab.knobs || []).filter(function (q) { return q.param === 'Lw'; })[0] || { min: 40, max: 100, k: 0.01 };
  var LMIN = kl.min * (kl.k || 1), LMAX = kl.max * (kl.k || 1);
  var LENS = [0, 1, 2, 3, 4].map(function (i) { return Math.round((LMIN + (LMAX - LMIN) * i / 4) * 1000) / 1000; });
  var TW = Math.max(3, Math.min(30, Math.round(p.th0 * 180 / Math.PI)));
  var st = { li: 2, read: [null, null], cyc: 0, twisted: false };
  var sim, prevSign = 1, ready = false;

  // ---------- geometry. The wire hangs at (XW, ZW); its grip points are YTOP and YTOP - L, so the scale reads L exactly.
  var XW = 0.02, ZW = -0.2, YTOP = 1.33;
  var DISC_R = FOR_I ? 0.085 : 0.075, DISC_H = FOR_I ? 0.008 : 0.014;
  function yBot() { return YTOP - p.Lw; }
  function discY() { return yBot() - 0.026 - DISC_H / 2; }

  var pillar = new T.Group(); S.scene.add(pillar);
  var foot = S.rounded(0.3, 0.22, 0.03, 0.01, M.iron); foot.rotation.x = -Math.PI / 2; foot.position.set(XW - 0.28, 0.015, ZW); pillar.add(foot);
  var post = S.mesh(new T.CylinderGeometry(0.019, 0.022, YTOP + 0.06, 28), M.chrome); post.position.set(XW - 0.28, (YTOP + 0.06) / 2 + 0.03, ZW); pillar.add(post);
  var arm = S.mesh(new T.BoxGeometry(0.33, 0.028, 0.055), M.iron); arm.position.set(XW - 0.12, YTOP + 0.058, ZW); pillar.add(arm);
  S.contact(0.44, 0.3, XW - 0.28, ZW, 0.55);
  var lbl = S.label('TORSION  BENCH', { w: 0.11, ratio: 0.15, color: '#d7dbe0', weight: 700 });
  lbl.position.set(XW - 0.12, YTOP + 0.088, ZW + 0.028); pillar.add(lbl);

  function makeChuck() {
    var g = new T.Group(); S.scene.add(g);
    g.add(S.mesh(new T.CylinderGeometry(0.016, 0.018, 0.026, 24), M.brass));
    var c2 = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.012, 20), M.chrome); c2.position.y = 0.019; g.add(c2);
    [-1, 1].forEach(function (s) {
      var sc = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.028, 12), M.chrome); sc.rotation.z = Math.PI / 2; sc.position.set(s * 0.02, 0.002, 0); g.add(sc);
      var kb = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.006, 6), M.black); kb.rotation.z = Math.PI / 2; kb.position.set(s * 0.036, 0.002, 0); g.add(kb);
    });
    return g;
  }
  var chuckTop = makeChuck(); chuckTop.position.set(XW, YTOP + 0.013, ZW);
  var chuckBot = makeChuck(); chuckBot.rotation.z = Math.PI;
  var wireM = new T.MeshStandardMaterial({ color: WIRE.col, roughness: WIRE.rough, metalness: 0.85 });
  var wire = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 1, 10), wireM, false); S.scene.add(wire);

  var body = new T.Group(); S.scene.add(body);
  var discM = FOR_I ? new T.MeshStandardMaterial({ color: 0xb8bdc3, roughness: 0.35, metalness: 0.8 }) : M.brass;
  body.add(S.mesh(new T.CylinderGeometry(DISC_R, DISC_R, DISC_H, 56), discM));
  var rimg = S.mesh(new T.TorusGeometry(DISC_R - 0.001, 0.0022, 8, 56), discM, false); rimg.rotation.x = Math.PI / 2; rimg.position.y = DISC_H / 2; body.add(rimg);
  var hub = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.03, 20), M.chrome); hub.position.y = DISC_H / 2 + 0.014; body.add(hub);
  if (FOR_I) {
    var lump = S.mesh(new T.BoxGeometry(0.07, 0.05, 0.045), M.iron); lump.position.set(0.016, DISC_H / 2 + 0.025, 0.008); lump.rotation.y = 0.5; body.add(lump);
    var lump2 = S.mesh(new T.CylinderGeometry(0.018, 0.026, 0.04, 18), M.iron); lump2.position.set(-0.032, DISC_H / 2 + 0.02, -0.016); body.add(lump2);
    [-1, 1].forEach(function (s) { var cl = S.mesh(new T.BoxGeometry(0.012, 0.016, 0.075), M.chrome); cl.position.set(s * 0.052, DISC_H / 2 + 0.008, 0); body.add(cl); });
  }
  var markM = new T.MeshStandardMaterial({ color: 0xf6f3ea, roughness: 0.9 });
  var mark = S.mesh(new T.BoxGeometry(0.004, DISC_H + 0.002, 0.03), markM, false);
  mark.position.set(0, 0, DISC_R - 0.013); body.add(mark);
  var markTop = new T.Mesh(new T.PlaneGeometry(0.004, 0.028), markM); markTop.rotation.x = -Math.PI / 2;
  markTop.position.set(0, DISC_H / 2 + 0.0007, DISC_R - 0.024); body.add(markTop);

  // the fixed pointer: a red pin on a small stand, level with the rim
  var ptr = new T.Group(); S.scene.add(ptr);
  var pbase = S.rounded(0.075, 0.065, 0.016, 0.006, M.darkWood); pbase.rotation.x = -Math.PI / 2; pbase.position.y = 0.008; ptr.add(pbase);
  var PP0 = 0.5;
  var ppost = S.mesh(new T.CylinderGeometry(0.005, 0.006, PP0, 16), M.chrome); ptr.add(ppost);
  var pin = S.mesh(new T.ConeGeometry(0.0022, 0.035, 12), new T.MeshStandardMaterial({ color: 0xc0392b, roughness: 0.4 }), false);
  pin.rotation.x = -Math.PI / 2; ptr.add(pin);
  ptr.position.set(XW, 0, ZW + DISC_R + 0.05); S.contact(0.095, 0.085, XW, ZW + DISC_R + 0.05, 0.45);

  // the metre scale hangs with its zero at the top (y = RTOP), so a mark at height y reads (RTOP - y) * 100 cm
  var RLEN = 1.42, RTOP = 1.44, RX = XW - 0.09, RZ = ZW - 0.015;
  var ruler = S.ruler(RLEN, { title: 'VERTICAL SCALE · cm · LC 1 mm', labelEvery: 10 });
  ruler.position.set(RX, RTOP - RLEN, RZ); S.scene.add(ruler);
  var rfoot = S.rounded(0.085, 0.075, 0.035, 0.008, M.darkWood); rfoot.rotation.x = -Math.PI / 2;
  rfoot.position.set(RX, RTOP - RLEN + 0.01, RZ); S.scene.add(rfoot); S.contact(0.13, 0.12, RX, RZ, 0.5);
  function cmAt(y) { return (RTOP - y) * 100; }

  var watch = S.stopwatch([XW + 0.3, 0.035, 0.16], [-1.15, -0.25, -0.12]);
  var kit = S.rounded(0.21, 0.13, 0.05, 0.008, M.darkWood); kit.position.set(XW + 0.56, 0.025, 0.05); S.scene.add(kit);
  S.contact(0.25, 0.17, XW + 0.56, 0.05, 0.4);
  var kitL = S.label('SPARE  WIRES  ·  SCREW  GAUGE', { w: 0.165, ratio: 0.1, color: '#3b2a10', bg: '#f3ecd6' });
  kitL.rotation.x = -Math.PI / 2; kitL.position.set(XW + 0.56, 0.051, 0.05); S.scene.add(kitL);

  S.addApparatus('pillar', pillar, 'Rigid bracket and pillar', 'The wire must hang from something that cannot itself twist, or part of the twist is lost in the support.');
  S.addApparatus('wire', wire, WIRE.name.charAt(0).toUpperCase() + WIRE.name.slice(1) + ' suspension wire',
    'Radius r = ' + (p.rw * 1000).toFixed(3) + ' mm, measured with a screw gauge at several places. C = πηr⁴/2L, so r counts four times over.');
  S.addApparatus('body', body, FOR_I ? 'Inertia table with the body clamped on it' : 'Brass disc',
    FOR_I ? 'A light table on the wire. The irregular body is clamped at its centre, so the axis passes through both.'
      : 'A heavy brass disc of known mass and radius: its moment of inertia I = ½MR² is known.');
  S.addApparatus('ptr', ptr, 'Fixed pointer', 'A pin level with the rim. One oscillation is counted each time the chalk mark comes back past it going the same way.');
  S.addApparatus('ruler', ruler, 'Metre scale', 'Reads both chucks, so the wire’s effective length is their difference. Least count 1 mm.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Least count 0.01 s. Twenty oscillations are timed, not one, so the reaction time is divided by twenty.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudL = S.hudCard('Wire length L'), hudA = S.hudCard('Twist'), hudC = S.hudCard('Oscillations');

  // ---------- state
  function applyLen(i) {
    st.li = i; p.Lw = LENS[i];
    sim = K.init(p); sim.y = [0, 0];
    st.cyc = 0; st.twisted = false; st.read = [null, null];
    watch.on = false; watch.t = 0; prevSign = 1;
    var yb = yBot(), dy = discY();
    wire.scale.y = Math.max(0.001, p.Lw); wire.position.set(XW, (YTOP + yb) / 2, ZW);
    chuckBot.position.set(XW, yb - 0.013, ZW);
    body.position.set(XW, dy, ZW);
    var ph = Math.max(0.05, dy - 0.016);
    ppost.scale.y = ph / PP0; ppost.position.y = ph / 2 + 0.016;
    pin.position.set(0, dy + DISC_H / 2 - 0.002, -0.02);
  }
  function Tcalc() { var c = Math.PI * p.eta * Math.pow(p.rw, 4) / (2 * p.Lw); return 2 * Math.PI * Math.sqrt(p.I / c); }
  function moving() { return Math.abs(sim.y[1]) > 0.03 || Math.abs(sim.y[0]) > 0.03; }

  function setLen(i) {
    if (S.hand.busy) return Promise.resolve();
    if (watch.on) { S.say('The stopwatch is running. Stop it first.'); return Promise.resolve(); }
    if (moving()) { S.say('Stop the ' + BODY + ' before you change the wire.'); return Promise.resolve(); }
    applyLen(i);
    S.say('Wire reset in the chuck to about ' + (p.Lw * 100).toFixed(0) + ' cm. Read both chucks on the scale again.');
    S.render();
    return Promise.resolve();
  }
  function readChuck(which) {
    var y = which === 0 ? YTOP : yBot();
    st.read[which] = Math.round(cmAt(y) * 10) / 10;
    if (lengthOk()) S.say('Upper chuck ' + st.read[0].toFixed(1) + ' cm, lower chuck ' + st.read[1].toFixed(1) + ' cm, so L = ' + lengthCm().toFixed(1) + ' cm.');
    else S.say((which === 0 ? 'Upper' : 'Lower') + ' chuck reads ' + st.read[which].toFixed(1) + ' cm on the scale.');
    if (ready) S.render();
  }
  function lengthOk() { return st.read[0] !== null && st.read[1] !== null; }
  function lengthCm() { return lengthOk() ? Math.round((st.read[1] - st.read[0]) * 10) / 10 : 0; }

  function twist() {
    if (S.hand.busy) return Promise.resolve();
    if (!lengthOk()) { S.say('Read both chucks on the metre scale first.'); return Promise.resolve(); }
    if (Math.abs(sim.y[1]) > 0.05) { S.say('It is still swinging. Let it settle, or stop it by hand.'); return Promise.resolve(); }
    var a0 = sim.y[0], a1 = p.th0, R = DISC_R - 0.013, dy = discY();
    function at(k) { var a = a0 + (a1 - a0) * k; return new T.Vector3(XW + Math.sin(a) * R, dy + DISC_H / 2 + 0.005, ZW + Math.cos(a) * R); }
    st.twisted = false;
    return S.hand.pinchMove(at(0), at, function (k) { sim.y = [a0 + (a1 - a0) * k, 0]; }, { ms: 1100, hold: 260, mode: 'top' })
      .then(function () {
        sim.y = [p.th0, 0]; st.twisted = true; st.cyc = 0; prevSign = 1;
        S.say('Released from ' + TW + '°. Count an oscillation each time the chalk mark passes the pin the same way.');
        S.render();
      });
  }
  function stopBody() {
    if (S.hand.busy) return Promise.resolve();
    sim.y = [0, 0]; st.twisted = false; watch.on = false; watch.t = 0; st.cyc = 0; S.render();
    return Promise.resolve();
  }
  function pressWatch() {
    if (S.hand.busy) return Promise.resolve();
    if (!watch.on && !st.twisted) { S.say('Give it a twist first, then time twenty oscillations.'); return Promise.resolve(); }
    return S.hand.tap(watch.start).then(function () {
      S.click(2400);
      if (!watch.on) { watch.t = 0; watch.on = true; st.cyc = 0; S.say('Started. Count twenty complete oscillations.'); }
      else { watch.on = false; record(); }
      S.render();
    });
  }
  function record() {
    var t = Math.round(watch.t * 100) / 100;
    if (st.cyc < 20) { S.say('Only ' + st.cyc + ' oscillations were counted. Time a full twenty: twist it again and start afresh.'); return; }
    var Tp = watch.t / 20;
    S.addRow({ Lw: lengthCm() / 100, Lcm: lengthCm(), t20: t, T: Tp });
    S.say('Written in your record book: L = ' + lengthCm().toFixed(1) + ' cm, 20 oscillations in ' + t.toFixed(2) + ' s, T = ' + Tp.toFixed(3) + ' s.');
  }
  function timeTwenty() {
    S.advance(4 * Tcalc() + 5, function () { return sim.y[0] < 0 && sim.y[1] < 0; });
    return pressWatch().then(function () {
      S.advance(22 * Tcalc() + 10, function () { return st.cyc >= 20; });
      return pressWatch();
    });
  }
  function lengthsDone() { var o = {}; S.rows.forEach(function (q) { o[q.Lcm.toFixed(1)] = 1; }); return Object.keys(o).length; }

  applyLen(st.li);

  var EXP = {
    camera: { pos: [1.05, 1.15, 1.95], look: [-0.02, 0.66, -0.2] },
    views: {
      setup: [[1.0, 1.1, 1.9], [-0.02, 0.66, -0.2]],
      wire: [[0.42, 1.34, 0.6], [XW - 0.04, 1.26, -0.2]],
      ruler: [[0.95, 0.95, 1.6], [XW - 0.05, 0.7, -0.2]],
      body: [[0.42, 0.62, 0.62], [XW, 0.34, -0.18]],
      ptr: [[0.2, 0.44, 0.34], [XW, 0.3, -0.12]],
      sw: [[0.66, 0.42, 0.6], [XW + 0.28, 0.08, 0.1]],
      book: [[-0.34, 0.5, 0.56], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'A wire twisted through an angle θ pushes back with a couple Cθ. A body of moment of inertia I hung on it '
        + 'therefore performs simple harmonic torsional oscillations in its own plane, with no dependence on gravity at all.',
      formula: 'T = 2π√(I / C),   C = π η r⁴ / 2L',
      formulaNote: FOR_I
        ? 'so I = C T² / 4π², with η = ' + (p.eta / 1e9).toFixed(1) + ' GPa and r = ' + (p.rw * 1000).toFixed(3) + ' mm printed on the calibrated wire'
        : 'so η = 8π I L / (r⁴ T²), with I = ' + p.I.toFixed(5) + ' kg·m² for this disc and r = ' + (p.rw * 1000).toFixed(3) + ' mm',
      more: ['T² is proportional to L: a longer wire is easier to twist, so the oscillation is slower.',
        'The radius comes in as r⁴, so a 1 % error in it gives a 4 % error in the answer. Measure it with a screw gauge at several places and in two directions at each.',
        'Twenty oscillations are timed rather than one, so the observer’s reaction time is divided by twenty.'],
      precautions: 'Keep the twist small, well inside the elastic limit, or the wire keeps a permanent set. Let the body settle '
        + 'before timing: a sideways swing or a wobble is not a torsional oscillation. Count the mark going past the pin the same way each time.'
    },
    book: {
      title: FOR_I ? 'Expt. — Inertia table' : 'Expt. — Torsional pendulum',
      lines: FOR_I
        ? ['Aim: to find the moment of inertia of an irregular body.',
          'Calibrated wire: η = ' + (p.eta / 1e9).toFixed(1) + ' GPa, r = ' + (p.rw * 1000).toFixed(3) + ' mm',
          'C = π η r⁴ / 2L', 'T = 2π√(I/C)  ⇒  I = C T² / 4π²',
          'Twist kept to ' + TW + '°; 20 oscillations timed each time.']
        : ['Aim: to find the modulus of rigidity of the wire.',
          'Disc: I = ' + p.I.toFixed(5) + ' kg·m² (from its mass and radius)',
          'Wire radius r = ' + (p.rw * 1000).toFixed(3) + ' mm (screw gauge)',
          'T = 2π√(I/C), C = πηr⁴/2L', 'η = 8π I L / (r⁴ T²)',
          'Twist kept to ' + TW + '°; 20 oscillations timed each time.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'L (cm)', get: function (r) { return r.Lcm.toFixed(1); } },
        { label: 't₂₀ (s)', get: function (r) { return r.t20.toFixed(2); } },
        { label: 'T (s)', get: function (r) { return r.T.toFixed(3); } },
        { label: 'T² (s²)', get: function (r) { return (r.T * r.T).toFixed(3); } }]
    },
    graph: {
      x: function (r) { return r.Lcm; }, y: function (r) { return r.T * r.T; },
      xlabel: 'L (cm)', ylabel: 'T² (s²)', x0: 0, y0: 0,
      line: function (pts) { var s = S.fit.origin(pts); return function (x) { return s * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var v = HK.CALCS[CALC].fn(rows, p);
      if (!isFinite(v) || v <= 0) return null;
      return FOR_I
        ? { label: 'I of the body', value: v, unit: 'kg·m²', digits: 5, truth: p.I, note: 'Mean of C T² / 4π² over the wire lengths.' }
        : { label: 'η of the wire', value: v, unit: 'Pa', digits: 0, truth: p.eta, note: 'Mean of 8π I L / (r⁴ T²) over the wire lengths.' };
    },
    tol: 0.02,
    chips: ['Why time twenty oscillations?', 'Why does the wire radius matter so much?', 'Check my readings',
      'What if the body swings sideways as well?', 'Why must the twist be small?'],
    viva: [['The torsional constant of a wire goes as', ['the fourth power of its radius', 'its radius', 'the square of its radius'], 0,
      'C = πηr⁴/2L.'],
      ['Doubling the wire’s length changes the period by a factor', ['√2', '2', '4'], 0, 'C halves, and T goes as 1/√C.']],
    askState: function () {
      return {
        wire_length_set_cm: +(p.Lw * 100).toFixed(1), measured_length_cm: lengthOk() ? lengthCm() : null,
        upper_chuck_cm: st.read[0], lower_chuck_cm: st.read[1],
        twist_now_deg: +(sim.y[0] * 180 / Math.PI).toFixed(2), oscillations_counted: st.cyc,
        stopwatch_running: watch.on, stopwatch_s: +watch.t.toFixed(2),
        unknown_being_measured: FOR_I ? 'moment of inertia of the body' : 'modulus of rigidity of the wire'
      };
    },

    steps: [
      { id: 'len', title: 'Measure L', view: 'ruler',
        render: function (u) {
          u.h2('Measure the length of the wire');
          u.p('The effective length is the bit of wire between the chucks. Read each chuck on the metre scale with your eye level with it.');
          var r = u.row();
          LENS.forEach(function (L, i) {
            r.appendChild(u.button((L * 100).toFixed(0) + ' cm' + (st.li === i ? ' ✓' : ''), function () { setLen(i).then(function () { S.focus('wire'); }); }, st.li === i, S.hand.busy));
          });
          u.note('Loosen the upper chuck, pull the wire through to about this length and tighten it again.');
          u.task('1. Read the upper chuck', st.read[0] !== null, st.read[0] !== null ? st.read[0].toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read', function () { S.focus('wire'); readChuck(0); }, st.read[0] === null, st.read[0] !== null));
          u.task('2. Read the lower chuck', st.read[1] !== null, st.read[1] !== null ? st.read[1].toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read', function () { S.focus('body'); readChuck(1); }, st.read[1] === null, st.read[1] !== null));
          if (lengthOk()) u.formula('L = ' + st.read[1].toFixed(1) + ' − ' + st.read[0].toFixed(1) + ' = ' + lengthCm().toFixed(1) + ' cm');
          u.next('Next: twist and time', lengthOk());
        },
        ok: function () { return lengthOk(); },
        auto: function () { readChuck(0); readChuck(1); return Promise.resolve(); } },

      { id: 'time', title: 'Twist and time', view: 'body',
        render: function (u) {
          u.h2('Twist the ' + BODY + ' and time twenty oscillations');
          u.p('The hand turns it through about ' + TW + '° and lets go. Press START as the chalk mark passes the pin, count '
            + 'twenty complete oscillations, then press STOP. Then change the wire length and do it again.');
          var r = u.row();
          LENS.forEach(function (L, i) {
            r.appendChild(u.button((L * 100).toFixed(0) + ' cm' + (st.li === i ? ' ✓' : ''), function () { setLen(i).then(function () { S.focus('body'); }); }, st.li === i, S.hand.busy || watch.on));
          });
          u.task('Read both chucks for this length', lengthOk(), lengthOk() ? 'L = ' + lengthCm().toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read them', function () { readChuck(0); readChuck(1); }, !lengthOk(), lengthOk()));
          u.row(u.button(st.twisted ? 'Twist again' : 'Twist and release', function () { twist(); }, !st.twisted, S.hand.busy || watch.on || !lengthOk()),
            u.button(watch.on ? 'STOP' : 'START', function () { pressWatch(); }, watch.on, S.hand.busy || (!watch.on && !st.twisted)),
            u.button('Stop it by hand', function () { stopBody(); }, false, S.hand.busy || watch.on));
          u.live(function () {
            return (p.Lw * 100).toFixed(0) + ' cm wire · twist ' + (sim.y[0] * 180 / Math.PI).toFixed(1) + '° · '
              + st.cyc + ' of 20 oscillations · ' + watch.t.toFixed(2) + ' s';
          });
          u.h3('Observation table'); u.table();
          var n = lengthsDone();
          u.next('Next: work out the result', n >= 3);
          if (n < 3) u.p(n + ' of at least 3 wire lengths timed. Reset the wire, measure it again and time it.');
        },
        ok: function () { return lengthsDone() >= 3; },
        auto: function () {
          return [4, 2, 0].reduce(function (pr, i) {
            return pr.then(stopBody).then(function () { return setLen(i); })
              .then(function () { readChuck(0); readChuck(1); return twist(); })
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
    body.rotation.y = sim.y[0];
    hudL.set((p.Lw * 100).toFixed(0) + ' cm');
    hudA.set((sim.y[0] * 180 / Math.PI).toFixed(1) + '°');
    hudC.set(st.cyc + ' / 20');
  }
  pose();
  return EXP;
});
