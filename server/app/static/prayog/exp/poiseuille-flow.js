/* Prayogshala studio module: viscosity by capillary flow, Poiseuille's method (B.Sc. properties of matter).
   A constant-head reservoir is clamped on a retort stand: water runs into it and the surplus leaves by an overflow, so
   its level never moves while a reading is taken. A rubber tube takes the water down to a fine horizontal capillary
   clamped on the bench, and what comes out of the capillary is caught in a graduated measuring jar. A vertical scale
   reads the water surface and the capillary's axis, so the head h is their difference; a digital stopwatch times the
   collection of 10 ml.
   The gloved hand slides the reservoir's clamp up and down the stand to change the head and empties the jar.
   Physics: the `poiseuille` kernel of the mech_ug pack - Q = π ρ g h r⁴ / (8 η l). Everything comes from the lab's params. */
HoolaStudio.define('poiseuille-flow', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.poiseuille;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('poiseuille');
  var SAMPLE = String((S.lab.variant || {}).sample || '');
  var tcm = /(\d+(?:\.\d+)?)\s*°c/i.exec(SAMPLE), TC = tcm ? +tcm[1] : null;
  var LIQ = /glycer/i.test(SAMPLE) ? { name: 'glycerine solution', c: 0xdcc98a } : { name: 'water', c: 0x58a3c8 };
  var kh = (S.lab.knobs || []).filter(function (q) { return q.param === 'hh'; })[0] || { min: 10, max: 40, k: 0.01 };
  var HMIN = kh.min * (kh.k || 1), HMAX = kh.max * (kh.k || 1);
  var HEADS = [0, 1, 2, 3].map(function (i) { return Math.round((HMIN + (HMAX - HMIN) * i / 3) * 1000) / 1000; });
  var VT = p.Vt;
  var st = { hi: 1, read: [null, null], collecting: false, emptied: true };
  p.hh = HEADS[st.hi];
  var sim = K.init(p), ready = false;

  // ---------- geometry. The capillary's axis is at y = CAPY; the reservoir's water surface sits hh above it.
  var CAPY = 0.14, CAPX0 = -0.16, CAPL = 0.3, ZC = -0.14, TKX = -0.42, TKR = 0.055, TKH = 0.17;
  var stand = new T.Group(); S.scene.add(stand);
  var sbase = S.rounded(0.26, 0.17, 0.024, 0.008, M.iron); sbase.rotation.x = -Math.PI / 2; sbase.position.set(TKX - 0.02, 0.012, ZC - 0.07); stand.add(sbase);
  var srod = S.mesh(new T.CylinderGeometry(0.0075, 0.0085, 0.78, 20), M.chrome); srod.position.set(TKX - 0.09, 0.41, ZC - 0.07); stand.add(srod);
  S.contact(0.3, 0.22, TKX - 0.02, ZC - 0.07, 0.5);

  var boss = new T.Group(); S.scene.add(boss);
  var bb = S.rounded(0.05, 0.044, 0.04, 0.006, M.alu); boss.add(bb);
  var barm = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.1, 18), M.chrome); barm.rotation.z = Math.PI / 2; barm.position.x = 0.05; boss.add(barm);
  var bthumb = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 6), M.black); bthumb.rotation.x = Math.PI / 2; bthumb.position.z = 0.026; boss.add(bthumb);
  var bring = S.mesh(new T.TorusGeometry(TKR + 0.004, 0.0035, 8, 30), M.chrome, false); bring.rotation.x = Math.PI / 2; bring.position.x = 0.1 + TKR * 0.1; boss.add(bring);

  var tank = new T.Group(); S.scene.add(tank);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, metalness: 0, transparent: true, opacity: 0.2, clearcoat: 1, depthWrite: false, side: T.DoubleSide });
  var tprof = [[0, 0], [TKR, 0], [TKR, TKH], [TKR - 0.0025, TKH], [TKR - 0.0025, 0.0025], [0, 0.0025]].map(function (q) { return new T.Vector2(q[0], q[1]); });
  var tw = new T.Mesh(new T.LatheGeometry(tprof, 40), glassM); tw.renderOrder = 4; tank.add(tw);
  var liqM = new T.MeshStandardMaterial({ color: LIQ.c, roughness: 0.06, transparent: true, opacity: 0.5, depthWrite: false, side: T.DoubleSide });
  var tliq = S.mesh(new T.CylinderGeometry(TKR - 0.004, TKR - 0.004, 0.115, 36), liqM, false); tliq.position.y = 0.06; tank.add(tliq);
  var tsurf = new T.Mesh(new T.CircleGeometry(TKR - 0.004, 36), new T.MeshStandardMaterial({ color: LIQ.c, roughness: 0.03, transparent: true, opacity: 0.65, depthWrite: false }));
  tsurf.rotation.x = -Math.PI / 2; tsurf.position.y = 0.1175; tank.add(tsurf);
  var over = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.08, 14), glassM, false); over.rotation.z = 1.15; over.position.set(TKR + 0.02, 0.125, 0); tank.add(over);
  var feed = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.09, 12), glassM, false); feed.position.set(-0.02, TKH + 0.04, 0); tank.add(feed);
  var tLab = S.label('CONSTANT HEAD', { w: 0.07, ratio: 0.16, color: '#3b2a10', bg: '#f3ecd6' });
  tLab.position.set(0, 0.03, TKR + 0.002); tank.add(tLab);

  var tubeM = new T.MeshStandardMaterial({ color: 0x3f4248, roughness: 0.85 });
  var downTube = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 1, 12), tubeM, false); S.scene.add(downTube);
  var elbow = S.mesh(new T.SphereGeometry(0.0065, 14, 10), tubeM, false); S.scene.add(elbow);
  var feedTube = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.2, 12), tubeM, false);
  feedTube.rotation.z = Math.PI / 2; feedTube.position.set(CAPX0 - 0.1, CAPY, ZC); S.scene.add(feedTube);

  // the capillary: a fine glass tube clamped horizontally, with its bore drawn in the liquid's colour
  var cap = new T.Group(); S.scene.add(cap);
  var capGlass = S.mesh(new T.CylinderGeometry(0.0038, 0.0038, CAPL, 20), glassM, false); capGlass.rotation.z = Math.PI / 2; cap.add(capGlass);
  var capBore = S.mesh(new T.CylinderGeometry(0.0013, 0.0013, CAPL - 0.001, 14), liqM, false); capBore.rotation.z = Math.PI / 2; cap.add(capBore);
  cap.position.set(CAPX0 + CAPL / 2, CAPY, ZC);
  [-1, 1].forEach(function (s) {
    var cl = new T.Group(); S.scene.add(cl);
    var cb = S.rounded(0.05, 0.05, 0.03, 0.006, M.iron); cb.position.y = 0.015; cl.add(cb);
    var cpst = S.mesh(new T.CylinderGeometry(0.007, 0.008, CAPY - 0.02, 14), M.chrome); cpst.position.y = (CAPY - 0.02) / 2 + 0.03; cl.add(cpst);
    var cj = S.mesh(new T.BoxGeometry(0.02, 0.016, 0.02), M.alu); cj.position.y = CAPY - 0.009; cl.add(cj);
    cl.position.set(CAPX0 + CAPL / 2 + s * (CAPL / 2 - 0.04), 0, ZC);
    S.contact(0.07, 0.07, cl.position.x, ZC, 0.4);
  });

  // the graduated measuring jar
  var JX = CAPX0 + CAPL + 0.055, JR = 0.035, JH = 0.13, JY = 0.0;
  var jar = new T.Group(); S.scene.add(jar);
  var jprof = [[0, 0], [JR, 0], [JR, JH], [JR - 0.002, JH], [JR - 0.002, 0.003], [0, 0.003]].map(function (q) { return new T.Vector2(q[0], q[1]); });
  var jw = new T.Mesh(new T.LatheGeometry(jprof, 36), glassM); jw.renderOrder = 4; jar.add(jw);
  var jfoot = S.mesh(new T.CylinderGeometry(JR + 0.008, JR + 0.01, 0.006, 32), glassM, false); jar.add(jfoot);
  var jliq = S.mesh(new T.CylinderGeometry(JR - 0.003, JR - 0.003, 1, 30), liqM, false); jar.add(jliq);
  var jscaleTex = S.canvasTex(128, 512, function (x, w, h) {
    x.clearRect(0, 0, w, h); x.fillStyle = 'rgba(255,255,255,0.0)'; x.fillRect(0, 0, w, h);
    x.strokeStyle = '#2b3138'; x.fillStyle = '#2b3138'; x.font = '600 24px "Public Sans", sans-serif';
    for (var i = 0; i <= 20; i++) {
      var y = h - 30 - i / 20 * (h - 60), big = i % 5 === 0;
      x.fillRect(8, y, big ? 40 : 22, big ? 3 : 1.6);
      if (big) x.fillText(String(i), 54, y + 9);
    }
  });
  var jplate = new T.Mesh(new T.PlaneGeometry(0.022, JH * 0.92), new T.MeshBasicMaterial({ map: jscaleTex, transparent: true }));
  jplate.position.set(0, JH * 0.5, JR - 0.0005); jar.add(jplate);
  jar.position.set(JX, JY, ZC + 0.01); S.contact(0.1, 0.1, JX, ZC + 0.01, 0.45);
  var jmlLab = S.label('ml', { w: 0.014, ratio: 0.45, color: '#2b3138' }); jmlLab.position.set(0.012, JH * 0.97, JR + 0.0005); jar.add(jmlLab);

  // a vertical scale to read the water surface and the capillary's axis
  var RLEN = 0.7, RTOP = 0.72, RX = TKX + 0.13, RZ = ZC - 0.095;
  var ruler = S.ruler(RLEN, { title: 'VERTICAL SCALE · cm', labelEvery: 10, width: 0.026 });
  ruler.position.set(RX, RTOP - RLEN, RZ); S.scene.add(ruler);
  var rfoot = S.rounded(0.075, 0.07, 0.03, 0.008, M.darkWood); rfoot.rotation.x = -Math.PI / 2;
  rfoot.position.set(RX, RTOP - RLEN + 0.012, RZ); S.scene.add(rfoot); S.contact(0.11, 0.1, RX, RZ, 0.5);
  function cmAt(y) { return (RTOP - y) * 100; }

  var watch = S.stopwatch([JX + 0.2, 0.035, 0.1], [-1.15, -0.35, -0.12]);
  var therm = TC === null ? null : S.thermometer({ len: 0.22, min: 0, max: 50, value: TC, pos: [TKX + 0.02, 0.02, ZC + 0.06] });

  S.addApparatus('tank', tank, 'Constant-head reservoir', 'Water runs in at the top and the surplus leaves by the overflow, so the driving head does not fall while a reading is taken.');
  S.addApparatus('cap', cap, 'Capillary tube', 'Length l = ' + (p.lc * 100).toFixed(1) + ' cm, bore radius r = ' + (p.rc * 1000).toFixed(3)
    + ' mm measured with a travelling microscope. Q goes as r⁴, so r is the one measurement that must be right.');
  S.addApparatus('jar', jar, 'Measuring jar', 'Graduated in millilitres. One reading is the time to collect ' + (VT * 1e6).toFixed(0) + ' ml.');
  S.addApparatus('ruler', ruler, 'Vertical scale', 'Reads the water surface and the capillary’s axis: the head h is their difference.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Least count 0.01 s.');
  if (therm) S.addApparatus('therm', therm, 'Thermometer', 'Dipped in the liquid: ' + TC + ' °C. Viscosity falls fast as a liquid warms, so the temperature is part of the answer.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudH = S.hudCard('Head h'), hudV = S.hudCard('Collected'), hudQ = S.hudCard('Flow rate');

  // ---------- state
  function surfY() { return CAPY + p.hh; }
  function placeTank() {
    var sy = surfY(), bottom = sy - 0.1175;
    tank.position.set(TKX, bottom, ZC);
    boss.position.set(TKX - 0.145, bottom + 0.05, ZC - 0.07);
    var yA = bottom + 0.004, yB = CAPY;
    downTube.scale.y = Math.max(0.001, yA - yB);
    downTube.position.set(TKX, (yA + yB) / 2, ZC);
    elbow.position.set(TKX, CAPY, ZC);
    feedTube.scale.y = 1;
    feedTube.position.set((TKX + CAPX0) / 2, CAPY, ZC);
    feedTube.scale.x = 1; feedTube.scale.z = 1;
    feedTube.scale.y = Math.max(0.001, (CAPX0 - TKX)) / 0.2;
  }
  function setHead(i) {
    if (S.hand.busy) return Promise.resolve();
    if (st.collecting) { S.say('A reading is going on. Stop the watch first.'); return Promise.resolve(); }
    var y0 = surfY();
    st.hi = i; p.hh = HEADS[i];
    var y1 = surfY();
    st.read = [null, null];
    sim = K.init(p);
    return S.hand.pinchMove(new T.Vector3(TKX - 0.1, y0 - 0.05, ZC - 0.04), function (kk) {
      return new T.Vector3(TKX - 0.1, y0 - 0.05 + (y1 - y0) * kk, ZC - 0.04);
    }, function (kk) {
      p.hh = HEADS[st.hi] * kk + (y0 - CAPY) * (1 - kk);
      placeTank();
    }, { ms: 900, hold: 180, mode: 'side' }).then(function () {
      p.hh = HEADS[i]; placeTank(); sim = K.init(p);
      S.say('Reservoir clamped so the head is about ' + (p.hh * 100).toFixed(0) + ' cm. Read it on the scale.');
      S.render();
    });
  }
  function readLevel(which) {                      // 0 = the water surface, 1 = the capillary's axis
    var y = which === 0 ? surfY() : CAPY;
    st.read[which] = Math.round(cmAt(y) * 10) / 10;
    if (bothRead()) S.say('Surface at ' + st.read[0].toFixed(1) + ' cm, capillary axis at ' + st.read[1].toFixed(1) + ' cm, so h = ' + hCm().toFixed(1) + ' cm.');
    else S.say((which === 0 ? 'The water surface' : 'The capillary axis') + ' reads ' + st.read[which].toFixed(1) + ' cm.');
    if (ready) S.render();
  }
  function bothRead() { return st.read[0] !== null && st.read[1] !== null; }
  function hCm() { return bothRead() ? Math.round((st.read[1] - st.read[0]) * 10) / 10 : 0; }

  function emptyJar() {
    if (S.hand.busy || st.collecting) return Promise.resolve();
    var from = new T.Vector3(JX + JR, 0.06, ZC + 0.01);
    return S.hand.pinchMove(from, function (kk) { return from.clone().add(new T.Vector3(0.05 * kk, 0.05 * kk, 0.03 * kk)); },
      function (kk) { if (kk > 0.5) { sim = K.init(p); st.emptied = true; } }, { ms: 700, hold: 150, mode: 'side' })
      .then(function () { sim = K.init(p); st.emptied = true; watch.t = 0; S.say('Jar emptied and put back under the capillary.'); S.render(); });
  }
  function pressWatch() {
    if (S.hand.busy) return Promise.resolve();
    if (!bothRead()) { S.say('Measure the head on the scale first.'); return Promise.resolve(); }
    if (!watch.on && !st.emptied) { S.say('Empty the jar before you start a reading.'); return Promise.resolve(); }
    return S.hand.tap(watch.start).then(function () {
      S.click(2400);
      if (!watch.on) { watch.t = 0; watch.on = true; st.collecting = true; sim = K.init(p); st.emptied = false; S.say('Collecting. Stop the watch as the jar reaches ' + (VT * 1e6).toFixed(0) + ' ml.'); }
      else { watch.on = false; st.collecting = false; record(); }
      S.render();
    });
  }
  function record() {
    var v = K.view(sim, p), t = Math.round(watch.t * 100) / 100;
    if (Math.abs(v.V - VT) > VT * 0.03) {
      S.say('The jar held ' + v.V_ml.toFixed(2) + ' ml, not ' + (VT * 1e6).toFixed(0) + ' ml. Empty it and take the reading again.');
      return;
    }
    var Q = VT / watch.t;
    S.addRow({ hh: hCm() / 100, hcm: hCm(), t: t, Q: Q, Qml: Q * 1e6 });
    S.say('Written in your record book: h = ' + hCm().toFixed(1) + ' cm, ' + (VT * 1e6).toFixed(0) + ' ml in '
      + t.toFixed(2) + ' s, Q = ' + (Q * 1e6).toFixed(4) + ' ml/s.');
  }
  function collectOnce() {
    return emptyJar().then(pressWatch).then(function () {
      S.advance(K.view(sim, p).t_full + 10, function () { return K.view(sim, p).V >= VT; });
      return pressWatch();
    });
  }
  function headsDone() { var o = {}; S.rows.forEach(function (r) { o[r.hcm.toFixed(1)] = 1; }); return Object.keys(o).length; }

  placeTank();

  var EXP = {
    camera: { pos: [0.7, 0.72, 1.1], look: [-0.05, 0.25, -0.14] },
    views: {
      setup: [[0.68, 0.7, 1.05], [-0.05, 0.25, -0.14]],
      tank: [[0.1, 0.62, 0.48], [TKX + 0.03, 0.4, -0.14]],
      ruler: [[0.12, 0.6, 0.56], [TKX + 0.08, 0.36, -0.14]],
      cap: [[0.05, 0.34, 0.42], [CAPX0 + CAPL / 2, 0.15, -0.14]],
      jar: [[0.42, 0.3, 0.42], [JX, 0.09, -0.12]],
      sw: [[0.62, 0.34, 0.5], [JX + 0.16, 0.06, 0.05]],
      book: [[-0.34, 0.5, 0.56], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'A liquid driven slowly through a narrow tube moves in layers, each sliding over the next. The volume '
        + 'passing per second then depends on the fourth power of the bore, which is why a capillary makes such a sensitive '
        + 'viscometer.',
      formula: 'Q = π ρ g h r⁴ / (8 η l)',
      formulaNote: 'so η = π ρ g h r⁴ / (8 l Q), with r = ' + (p.rc * 1000).toFixed(3) + ' mm, l = '
        + (p.lc * 100).toFixed(1) + ' cm and ρ = ' + p.rho.toFixed(1) + ' kg/m³'
        + (TC === null ? '' : ' at ' + TC + ' °C'),
      more: ['Q is proportional to h: a graph of Q against h is a straight line through the origin, and η follows from its slope.',
        'Q goes as r⁴: a tube 1 % wider passes 4 % more liquid, so the bore must be measured with a travelling microscope at both ends and in two directions.',
        'Keep the head small enough for the flow to stay in layers. If it turns turbulent the line bends over and the formula no longer holds.'],
      precautions: 'Keep the capillary horizontal and free of air bubbles. Let the flow settle before you start timing. '
        + 'Note the temperature: the viscosity of water changes by about 2 % per degree.'
    },
    book: {
      title: 'Expt. — Viscosity by Poiseuille’s method',
      lines: ['Aim: to find the coefficient of viscosity of ' + LIQ.name + ' by capillary flow.',
        'Capillary: l = ' + (p.lc * 100).toFixed(1) + ' cm, r = ' + (p.rc * 1000).toFixed(3) + ' mm',
        'ρ = ' + p.rho.toFixed(1) + ' kg/m³' + (TC === null ? '' : ', temperature ' + TC + ' °C'),
        'h = (capillary axis reading) − (surface reading)', 'Q = V / t,  V = ' + (VT * 1e6).toFixed(0) + ' ml',
        'η = π ρ g h r⁴ / (8 l Q)'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'h (cm)', get: function (r) { return r.hcm.toFixed(1); } },
        { label: 't (s)', get: function (r) { return r.t.toFixed(2); } },
        { label: 'Q (ml/s)', get: function (r) { return r.Qml.toFixed(4); } }]
    },
    graph: {
      x: function (r) { return r.hcm; }, y: function (r) { return r.Qml; },
      xlabel: 'h (cm)', ylabel: 'Q (ml/s)', x0: 0, y0: 0,
      line: function (pts) { var s = S.fit.origin(pts); return function (x) { return s * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var v = HK.CALCS.pois_eta.fn(rows, p);
      if (!isFinite(v) || v <= 0) return null;
      return { label: 'η', value: v, unit: 'Pa·s', digits: 6, truth: p.eta,
        note: 'Mean of πρghr⁴/(8lQ) over the heads used.' };
    },
    tol: 0.02,
    chips: ['Why does the bore radius matter so much?', 'Why a constant-head reservoir?', 'Check my readings',
      'What if the flow becomes turbulent?', 'How does temperature change η?'],
    viva: [['The rate of flow through a capillary goes as', ['the fourth power of the bore radius', 'the radius', 'the square of the radius'], 0,
      'Q = πPr⁴/8ηl.'],
      ['The constant-head reservoir is used so that', ['the driving pressure stays the same during a reading', 'the water stays cool', 'the tube stays clean'], 0,
        'A falling level would change h, and so Q, while you were timing.']],
    askState: function () {
      var v = K.view(sim, p);
      return {
        head_set_cm: +(p.hh * 100).toFixed(1), measured_head_cm: bothRead() ? hCm() : null,
        surface_reading_cm: st.read[0], capillary_axis_reading_cm: st.read[1],
        collected_ml: +v.V_ml.toFixed(2), target_ml: +(VT * 1e6).toFixed(0),
        stopwatch_running: watch.on, stopwatch_s: +watch.t.toFixed(2),
        liquid: LIQ.name, temperature_C: TC
      };
    },

    steps: [
      { id: 'head', title: 'Set the head', view: 'ruler',
        render: function (u) {
          u.h2('Set the head and measure it');
          u.p('Slide the reservoir’s clamp up or down the stand. Then read the water surface and the capillary’s '
            + 'axis on the vertical scale: h is the difference.');
          var r = u.row();
          HEADS.forEach(function (h, i) {
            r.appendChild(u.button((h * 100).toFixed(0) + ' cm' + (st.hi === i ? ' ✓' : ''), function () { setHead(i).then(function () { S.focus('ruler'); }); }, st.hi === i, S.hand.busy || st.collecting));
          });
          u.task('1. Read the water surface', st.read[0] !== null, st.read[0] !== null ? st.read[0].toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read', function () { S.focus('tank'); readLevel(0); }, st.read[0] === null, st.read[0] !== null));
          u.task('2. Read the capillary axis', st.read[1] !== null, st.read[1] !== null ? st.read[1].toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read', function () { S.focus('cap'); readLevel(1); }, st.read[1] === null, st.read[1] !== null));
          if (bothRead()) u.formula('h = ' + st.read[1].toFixed(1) + ' − ' + st.read[0].toFixed(1) + ' = ' + hCm().toFixed(1) + ' cm');
          u.note('The overflow keeps the surface where it is, so h does not fall while you are timing.');
          u.next('Next: collect and time', bothRead());
        },
        ok: function () { return bothRead(); },
        auto: function () { readLevel(0); readLevel(1); return Promise.resolve(); } },

      { id: 'collect', title: 'Collect and time', view: 'jar',
        render: function (u) {
          u.h2('Collect ' + (VT * 1e6).toFixed(0) + ' ml and time it');
          u.p('Empty the jar, press START, and press STOP exactly as the jar reaches the ' + (VT * 1e6).toFixed(0)
            + ' ml mark. Then change the head and do it again.');
          var r = u.row();
          HEADS.forEach(function (h, i) {
            r.appendChild(u.button((h * 100).toFixed(0) + ' cm' + (st.hi === i ? ' ✓' : ''), function () { setHead(i).then(function () { S.focus('jar'); }); }, st.hi === i, S.hand.busy || st.collecting));
          });
          u.task('Measure the head for this setting', bothRead(), bothRead() ? 'h = ' + hCm().toFixed(1) + ' cm' : 'Not measured yet')
            .add(u.button('Measure it', function () { readLevel(0); readLevel(1); }, !bothRead(), bothRead()));
          u.row(u.button('Empty the jar', function () { emptyJar(); }, !st.emptied, S.hand.busy || st.collecting),
            u.button(watch.on ? 'STOP' : 'START', function () { pressWatch(); }, watch.on, S.hand.busy || !bothRead()));
          u.live(function () {
            var v = K.view(sim, p);
            return 'h = ' + (p.hh * 100).toFixed(0) + ' cm · ' + v.V_ml.toFixed(2) + ' of ' + (VT * 1e6).toFixed(0)
              + ' ml · ' + watch.t.toFixed(2) + ' s';
          });
          u.h3('Observation table'); u.table();
          var n = headsDone();
          u.next('Next: work out η', n >= 3);
          if (n < 3) u.p(n + ' of at least 3 heads done. Move the reservoir, measure h again and time another ' + (VT * 1e6).toFixed(0) + ' ml.');
        },
        ok: function () { return headsDone() >= 3; },
        auto: function () {
          return [3, 1, 0].reduce(function (pr, i) {
            return pr.then(function () { return setHead(i); })
              .then(function () { readLevel(0); readLevel(1); return collectOnce(); });
          }, Promise.resolve());
        } }
    ],

    tick: function (dt) {
      if (st.collecting) K.step(sim, p, dt);
      pose();
    },
    ready: function () { ready = true; }
  };
  function pose() {
    var v = K.view(sim, p), f = Math.max(0.0005, Math.min(1, v.V / (VT * 2)));
    jliq.scale.y = Math.max(0.001, f * JH * 0.9);
    jliq.position.y = f * JH * 0.9 / 2 + 0.004;
    hudH.set((p.hh * 100).toFixed(0) + ' cm');
    hudV.set(v.V_ml.toFixed(2) + ' ml');
    hudQ.set(v.Q_ml.toFixed(4) + ' ml/s');
  }
  pose();
  return EXP;
});
