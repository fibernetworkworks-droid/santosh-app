/* Prayogshala studio module: the school heat bench (NCERT Class VI Temperature, Class IX Laboratory Manual).
   One rig, two set-ups - the lab id picks the mode:
     school-thermometer-read   read a clinical thermometer and a laboratory thermometer, eye level with the thread
     school-melting-boiling    heat the beaker and watch the temperature hold while the state changes
   Physics: the thermo_bath kernel from the wave_heat_school pack - the same numbers the server checks.
   The lamp is lit by the teacher, never by the student: that is how the real manual has it. */
HoolaStudio.define('school-heat-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.thermo_bath;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('thermo_bath');
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var MODE = /thermometer-read/.test(BASE) ? 'read' : 'phase';
  var ICE = MODE === 'phase' && p.Tp < 50;                   // melting ice, as against boiling water
  var EVERY = 30;                                            // one reading every 30 s of lab time, as in the manual
  var SAMPLE = String((S.lab.variant && S.lab.variant.sample) || (ICE ? 'Ice and water' : MODE === 'read' ? 'Water' : 'Water'));
  var CLINICAL = { key: 'clinical', name: 'clinical thermometer', min: 35, max: 42, lc: 0.1, len: 0.14 };
  var LABT = { key: 'lab', name: 'laboratory thermometer', min: -10, max: 110, lc: 0.5, len: 0.3 };
  var sim = K.init(p);
  var st = { lit: false, speed: MODE === 'phase' ? 20 : 2, shown: MODE === 'read' ? p.Ts : p.T0, chosen: MODE === 'read' ? null : LABT,
    dipped: MODE !== 'read', settled: MODE !== 'read', nextMark: EVERY, auto: true, flame: 0 };

  function readT(v, lc) { return Math.floor(v / (lc || p.lc) + 0.5) * (lc || p.lc); }
  function Tnow() { return MODE === 'read' ? p.T0 : sim.T; }
  function changing() { return sim.Q > 0 && Math.abs(sim.T - p.Tp) < 1e-6; }

  // ---------------------------------------------------------------- apparatus
  var BX = 0, BZ = -0.08, GAUZE_Y = 0.101, BK = { r: 0.05, h: 0.12 };
  // tripod stand: three legs, a ring and the wire gauze
  var tripod = new T.Group(); S.scene.add(tripod);
  var ring = S.mesh(new T.TorusGeometry(0.068, 0.004, 10, 36), M.iron); ring.rotation.x = Math.PI / 2;
  ring.position.set(BX, GAUZE_Y - 0.006, BZ); tripod.add(ring);
  [0.6, 2.7, 4.5].forEach(function (a) {
    var leg = S.mesh(new T.CylinderGeometry(0.004, 0.005, GAUZE_Y, 12), M.iron);
    leg.position.set(BX + Math.cos(a) * 0.066, GAUZE_Y / 2 - 0.004, BZ + Math.sin(a) * 0.066); tripod.add(leg);
  });
  var gauzeTex = S.canvasTex(256, 256, function (x, w, h) {
    x.fillStyle = '#b9bec4'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(40,44,48,.55)'; x.lineWidth = 2;
    for (var i = 0; i <= w; i += 9) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i, h); x.stroke(); x.beginPath(); x.moveTo(0, i); x.lineTo(w, i); x.stroke(); }
    x.fillStyle = '#d9d3c6'; x.beginPath(); x.arc(w / 2, h / 2, w * 0.2, 0, Math.PI * 2); x.fill();
  });
  var gauze = new T.Mesh(new T.BoxGeometry(0.15, 0.002, 0.15), new T.MeshStandardMaterial({ map: gauzeTex, roughness: 0.8 }));
  gauze.position.set(BX, GAUZE_Y, BZ); gauze.castShadow = true; gauze.receiveShadow = true; tripod.add(gauze);
  S.contact(0.24, 0.24, BX, BZ, 0.5);

  // spirit lamp under the gauze
  var lamp = new T.Group(); S.scene.add(lamp); lamp.position.set(BX, 0, BZ);
  var lbody = S.mesh(new T.CylinderGeometry(0.028, 0.03, 0.045, 28), M.brass); lbody.position.y = 0.0225; lamp.add(lbody);
  var lcap = S.mesh(new T.CylinderGeometry(0.009, 0.011, 0.016, 20), M.brass); lcap.position.y = 0.052; lamp.add(lcap);
  var wick = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.01, 10), new T.MeshStandardMaterial({ color: 0x3a3a38, roughness: 1 }));
  wick.position.y = 0.064; lamp.add(wick);
  var flameTex = S.canvasTex(128, 256, function (x, w, h) {
    var g = x.createRadialGradient(w / 2, h * 0.68, 4, w / 2, h * 0.62, h * 0.42);
    g.addColorStop(0, 'rgba(255,245,200,.95)'); g.addColorStop(0.35, 'rgba(255,176,60,.75)'); g.addColorStop(1, 'rgba(255,120,20,0)');
    x.fillStyle = g; x.fillRect(0, 0, w, h);
  });
  var flame = new T.Mesh(new T.PlaneGeometry(0.06, 0.09), new T.MeshBasicMaterial({ map: flameTex, transparent: true, depthWrite: false, depthTest: false, toneMapped: false }));
  flame.position.set(BX, 0.082, BZ); flame.renderOrder = 2; flame.visible = false; S.scene.add(flame);
  var llab = S.label('SPIRIT LAMP', { w: 0.042, ratio: 0.2, color: '#5a3b16' }); llab.position.set(0, 0.026, 0.0305); lamp.add(llab);

  // beaker with its liquid (and ice when the ice is being melted)
  var beaker = S.beaker(BK.r, BK.h, [BX, GAUZE_Y + 0.002, BZ]);
  var waterM = new T.MeshStandardMaterial({ color: 0xa8d2e4, roughness: 0.06, metalness: 0.08 });
  var water = S.mesh(new T.CylinderGeometry(BK.r * 0.95, BK.r * 0.95, 0.072, 36), waterM, false);
  water.position.y = 0.038; beaker.add(water);
  var blab = S.label(SAMPLE.toUpperCase(), { w: 0.05, ratio: 0.2, color: '#1b3a6b', weight: 700 });
  blab.position.set(0, 0.03, BK.r + 0.001); beaker.add(blab);
  var iceM = new T.MeshPhysicalMaterial({ color: 0xeaf6ff, roughness: 0.25, transmission: 0.6, thickness: 0.01, transparent: true, opacity: 0.85 });
  var ice = [];
  if (ICE) {
    [[0.012, 0.016], [-0.018, -0.006], [0.004, -0.02], [-0.008, 0.022]].forEach(function (o, i) {
      var c = S.rounded(0.018, 0.018, 0.015, 0.003, iceM);
      c.rotation.set(0.2 + i, 0.4 * i, 0.1 * i); c.position.set(BX + o[0], GAUZE_Y + 0.052, BZ + o[1]); S.scene.add(c); ice.push(c);
    });
  }
  var stir = S.mesh(new T.CylinderGeometry(0.0016, 0.0016, 0.17, 10), M.chrome);
  stir.position.set(BX - 0.03, GAUZE_Y + 0.085, BZ + 0.02); stir.rotation.z = 0.16; S.scene.add(stir);

  // the laboratory thermometer, clamped in a retort stand over the beaker
  var TX = BX + 0.015, TZ = BZ - 0.004, TBULB = GAUZE_Y + 0.016;
  var labTh = S.thermometer({ len: LABT.len, min: LABT.min, max: LABT.max, value: p.T0, pos: [TX, TBULB, TZ] });
  var stand = S.stand({ x: TX - 0.3 + 0.19, z: TZ, h: 0.62, armY: 0.3, armLen: 0.3 });
  stand.rotation.y = 0;
  // the clinical thermometer, resting in its case on the bench
  var caseG = new T.Group(); S.scene.add(caseG); caseG.position.set(0.3, 0, 0.06);
  var cbox = S.rounded(0.19, 0.045, 0.018, 0.006, new T.MeshStandardMaterial({ color: 0xe8e3d6, roughness: 0.7 }));
  cbox.rotation.x = -Math.PI / 2; cbox.position.y = 0.009; caseG.add(cbox);
  var clab = S.label('CLINICAL THERMOMETER  35 - 42 °C', { w: 0.14, ratio: 0.12, color: '#2b3a4a' });
  clab.rotation.x = -Math.PI / 2; clab.position.set(0, 0.0185, 0.012); caseG.add(clab);
  var clinTh = S.thermometer({ len: CLINICAL.len, min: CLINICAL.min, max: CLINICAL.max, value: 35.2, pos: [0, 0, 0] });
  clinTh.rotation.z = Math.PI / 2; clinTh.position.set(-0.075, 0.026, 0); caseG.add(clinTh);
  S.contact(0.24, 0.1, 0.3, 0.06, 0.45);
  var watch = S.stopwatch([0.52, 0.035, -0.02], [-1.2, -0.3, 0]);

  // steam over boiling water
  var steamTex = S.canvasTex(128, 128, function (x) { var g = x.createRadialGradient(64, 64, 2, 64, 64, 62);
    g.addColorStop(0, 'rgba(255,255,255,.7)'); g.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = g; x.fillRect(0, 0, 128, 128); });
  var wisps = [];
  for (var wi = 0; wi < 6; wi++) {
    var w3 = new T.Mesh(new T.PlaneGeometry(0.05, 0.05), new T.MeshBasicMaterial({ map: steamTex, transparent: true, opacity: 0, depthWrite: false }));
    w3.userData.ph = wi / 6; S.scene.add(w3); wisps.push(w3);
  }

  S.addApparatus('beaker', beaker, 'Beaker', 'A glass beaker on the wire gauze, filled only about half way so that it cannot spill over.');
  S.addApparatus('tripod', tripod, 'Tripod stand and wire gauze', 'The gauze spreads the flame so the beaker is warmed evenly and the glass does not crack.');
  S.addApparatus('lamp', lamp, 'Spirit lamp', 'The teacher lights it and puts it out with its cap. Never blow it out.');
  S.addApparatus('labth', labTh, 'Laboratory thermometer', 'Range -10 to 110 °C, least count 0.5 °C. Its bulb must be in the liquid, clear of the bottom.');
  S.addApparatus('clin', caseG, 'Clinical thermometer', 'Range 35 to 42 °C, least count 0.1 °C. It is made for body temperature and would burst in boiling water.');
  S.addApparatus('stand', stand, 'Clamp stand', 'Holds the thermometer upright so that nobody has to hold it in hot water.');
  S.addApparatus('sw', watch.group, 'Stopwatch', 'Least count 0.01 s. One reading every ' + EVERY + ' s.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudT = S.hudCard('Thermometer'), hudt = S.hudCard(MODE === 'phase' ? 'Stopwatch' : 'Least count'), hudN = S.hudCard('Readings');

  // ---------------------------------------------------------------- actions
  function pick(kind) {
    if (S.hand.busy) return Promise.resolve();
    var th = kind === 'clinical' ? CLINICAL : LABT;
    if (th === CLINICAL && (p.T0 < CLINICAL.min + 0.05 || p.T0 > CLINICAL.max - 0.05)) {
      S.say('A clinical thermometer only reads 35 to 42 °C. This temperature is outside that range, so it cannot be used - and in hot water it would burst.');
      return Promise.resolve();
    }
    st.chosen = th; p.lc = th.lc; st.dipped = false; st.settled = false; st.shown = p.Ts;
    S.say('Taking the ' + th.name + ': range ' + th.min + ' to ' + th.max + ' °C, least count ' + th.lc.toFixed(1) + ' °C.');
    S.focus(th === CLINICAL ? 'clin' : 'labth'); S.render(); return Promise.resolve();
  }
  function dip() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.chosen) { S.say('Choose a thermometer first.'); return Promise.resolve(); }
    if (st.dipped) { S.say('The bulb is already in the liquid. Wait for the thread to stop moving.'); return Promise.resolve(); }
    var from = st.chosen === CLINICAL ? new T.Vector3(0.22, 0.05, 0.06) : new T.Vector3(TX, TBULB + 0.22, TZ);
    var to = new T.Vector3(TX, TBULB + 0.03, TZ);
    return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); }, function (k) {
      if (st.chosen === CLINICAL) { clinTh.rotation.z = Math.PI / 2 * (1 - k); clinTh.position.set(-0.075 + (TX - 0.3 + 0.075) * k, 0.026 + (TBULB - 0.026) * k, (TZ - 0.06) * k); }
    }, { ms: 1200 }).then(function () {
      st.dipped = true;
      S.say('The bulb is in the liquid, clear of the bottom. Wait until the thread stops moving.'); S.render();
    });
  }
  function settle() {
    if (!st.dipped) { S.say('Put the bulb in the liquid first.'); return Promise.resolve(); }
    S.advance(6, function () { return Math.abs(st.shown - Tnow()) < 0.02; });
    st.settled = true; st.shown = Tnow();
    S.say('The thread has stopped. Read it with your eye level with its end.'); S.render();
    return Promise.resolve();
  }
  function readOut() {
    if (MODE === 'read' && !st.settled) { S.say('Wait until the thread stops moving.'); return; }
    var lc = st.chosen ? st.chosen.lc : p.lc;
    S.say('The thread ends at ' + readT(Tnow(), lc).toFixed(1) + ' °C (least count ' + lc.toFixed(1) + ' °C).');
    S.render();
  }
  function record() {
    var lc = st.chosen ? st.chosen.lc : p.lc;
    if (MODE === 'read') {
      if (!st.settled) { S.say('Wait until the thread stops moving, then record.'); return; }
      S.addRow({ name: st.chosen.name, reading: readT(Tnow(), lc), lc: lc });
      S.say('Written: ' + readT(Tnow(), lc).toFixed(1) + ' °C with the ' + st.chosen.name + '.');
      return;
    }
    if (!st.lit) { S.say('The lamp is not lit yet: there is nothing to follow.'); return; }
    if (!watch.on) { S.say('Start the stopwatch first: every reading needs its time.'); return; }
    var t = Math.round(watch.t);
    if (S.rows.length && t - S.rows[S.rows.length - 1].t < Math.max(3, EVERY / 3)) { S.say('Wait for the next reading: they go about ' + EVERY + ' s apart.'); return; }
    S.addRow({ t: t, reading: readT(sim.T, lc), hold: changing() });
  }
  function lightLamp() {
    if (S.hand.busy || st.lit) return Promise.resolve();
    return S.hand.reach(new T.Vector3(BX + 0.06, 0.07, BZ + 0.05), 'side', 700).then(function () { return S.hand.away(400); })
      .then(function () {
        st.lit = true; flame.visible = true; S.click(180, 0.12, 0.05);
        S.say('The teacher has lit the lamp. Do not lean over the beaker, and never blow the flame out - it is capped.');
        S.render();
      });
  }
  function pressWatch() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.lit) { S.say('The lamp is not lit yet.'); return Promise.resolve(); }
    return S.hand.tap(watch.start).then(function () {
      S.click(2400);
      if (!watch.on) { watch.t = 0; watch.on = true; st.nextMark = EVERY; record(); }
      else { watch.on = false; S.say('Stopwatch stopped at ' + watch.t.toFixed(0) + ' s.'); }
      S.render();
    });
  }
  function setSpeed(v) { st.speed = v; S.render(); }
  function holdRows() { return S.rows.filter(function (r) { return r.hold; }); }
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : NaN; }

  // ---------------------------------------------------------------- steps
  var readSteps = [
    { id: 'choose', title: 'Choose', view: 'clin', render: function (u) {
        u.h2('Which thermometer, and what is its least count?');
        u.p('A thermometer can only read inside its own range. Look at the range printed on each one and at its smallest division.');
        u.row(u.button((st.chosen === CLINICAL ? '✓ ' : '') + 'Clinical: 35 to 42 °C, 0.1 °C', function () { pick('clinical'); }, st.chosen !== CLINICAL, S.hand.busy),
          u.button((st.chosen === LABT ? '✓ ' : '') + 'Laboratory: -10 to 110 °C, 0.5 °C', function () { pick('lab'); }, false, S.hand.busy));
        u.live(function () { return st.chosen ? 'Chosen: the ' + st.chosen.name + ', least count ' + st.chosen.lc.toFixed(1) + ' °C' : 'No thermometer picked up yet'; });
        u.note('A clinical thermometer is made for body temperature only. In boiling water it would burst.');
        u.next('Next: read it', !!st.chosen);
      },
      ok: function () { return !!st.chosen; },
      auto: function () { return pick(p.T0 >= CLINICAL.min + 0.05 && p.T0 <= CLINICAL.max - 0.05 ? 'clinical' : 'lab'); } },
    { id: 'read', title: 'Read and record', view: 'labth', render: function (u) {
        u.h2('Read the end of the mercury thread');
        u.p('Put the bulb where the temperature is to be measured, wait until the thread stops, then read it with your eye level with the end of the thread.');
        u.row(u.button(st.dipped ? 'Bulb is in' : 'Put the bulb in', function () { dip(); S.render(); }, !st.dipped, st.dipped || S.hand.busy),
          u.button('Wait for the thread to stop', function () { settle(); }, false, !st.dipped || st.settled));
        u.row(u.button('Read the thermometer', function () { readOut(); }, true, !st.settled),
          u.button('Record this reading', function () { record(); }, false, !st.settled));
        u.live(function () { return 'Thermometer: ' + readT(st.shown, st.chosen ? st.chosen.lc : p.lc).toFixed(1) + ' °C'; });
        u.h3('Observation table'); u.table();
        u.next('Next: work out the temperature', S.rows.length >= 2);
      },
      ok: function () { return S.rows.length >= 2; },
      auto: function () { return dip().then(settle).then(function () { readOut(); record(); record(); }); } },
  ];
  var phaseSteps = [
    { id: 'heat', title: 'Heat it', view: 'beaker', render: function (u) {
        u.h2(ICE ? 'Warm the ice and water gently' : 'Heat the water');
        u.p('The beaker is half full on the wire gauze and the thermometer hangs with its bulb in the liquid, clear of the bottom. '
          + 'The teacher lights the lamp; start the stopwatch at the same moment.');
        u.row(u.button(st.lit ? 'The lamp is lit' : 'Ask the teacher to light the lamp', function () { lightLamp(); S.render(); }, !st.lit, st.lit || S.hand.busy),
          u.button(watch.on ? 'STOP the stopwatch' : 'START the stopwatch', function () { pressWatch(); }, st.lit && !watch.on, !st.lit || S.hand.busy));
        u.live(function () { return 't = ' + watch.t.toFixed(0) + ' s · thermometer ' + readT(sim.T, p.lc).toFixed(1) + ' °C'; });
        u.note('Stir gently with the stirrer so that the whole liquid is at one temperature.');
        u.next('Next: follow the temperature', st.lit && watch.on);
      },
      ok: function () { return st.lit && watch.on; },
      auto: function () { return lightLamp().then(pressWatch); } },
    { id: 'follow', title: 'Follow it', view: 'labth', render: function (u) {
        u.h2('A reading every ' + EVERY + ' seconds');
        u.p('Keep noting the temperature. It climbs at first. Then, although the flame is still burning, it stops climbing: '
          + 'that is the temperature of the change of state. Note at least three readings there.');
        u.row(u.button('Note the reading now', function () { record(); }, true, !watch.on),
          u.button((st.auto ? '✓ ' : '') + 'Note every ' + EVERY + ' s for me', function () { st.auto = !st.auto; if (st.auto && watch.on) st.nextMark = Math.ceil((watch.t + 1) / EVERY) * EVERY; S.render(); }, false, !watch.on));
        var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
        [5, 20, 60].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
        u.live(function () { return 't = ' + watch.t.toFixed(0) + ' s · ' + readT(sim.T, p.lc).toFixed(1) + ' °C · '
          + (changing() ? (ICE ? 'the ice is melting' : 'the water is boiling') : sim.Q > 0 ? 'still climbing' : ICE ? 'all melted, climbing again' : 'boiled away'); });
        u.h3('Observation table'); u.table();
        var h = holdRows().length;
        u.next('Next: work out the temperature of the change', h >= 3 && S.rows.length >= 6);
        if (h < 3) u.p(h + ' reading' + (h === 1 ? '' : 's') + ' taken while the state changes. Three are needed.');
      },
      ok: function () { return holdRows().length >= 3 && S.rows.length >= 6; },
      auto: function () {
        for (var i = 0; i < 400 && (holdRows().length < 4 || S.rows.length < 7); i++) S.advance(1.0);
        return Promise.resolve(); } },
  ];

  var bookCols = MODE === 'read'
    ? [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'Thermometer', get: function (r) { return r.name; } },
      { label: 'Least count (°C)', get: function (r) { return r.lc.toFixed(1); } },
      { label: 'Reading (°C)', get: function (r) { return r.reading.toFixed(1); } }]
    : [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 't (s)', get: function (r) { return String(r.t); } },
      { label: 'T (°C)', get: function (r) { return r.reading.toFixed(1); } },
      { label: 'State', get: function (r) { return r.hold ? (ICE ? 'melting' : 'boiling') : 'warming'; } }];

  return {
    camera: MODE === 'read' ? { pos: [0.42, 0.42, 0.72], look: [0.1, 0.12, -0.02] } : { pos: [0.46, 0.46, 0.82], look: [0.0, 0.16, -0.06] },
    views: { beaker: [[0.26, 0.3, 0.42], [BX, GAUZE_Y + 0.05, BZ]], tripod: [[0.24, 0.22, 0.38], [BX, 0.06, BZ]],
      lamp: [[0.2, 0.16, 0.34], [BX, 0.05, BZ]], labth: [[0.24, 0.34, 0.44], [TX, GAUZE_Y + 0.1, TZ]],
      clin: [[0.34, 0.26, 0.34], [0.3, 0.03, 0.06]], stand: [[0.1, 0.5, 0.66], [-0.1, 0.24, -0.16]],
      sw: [[0.42, 0.26, 0.34], [0.52, 0.03, -0.02]], book: [[-0.4, 0.52, 0.56], [-0.5, 0.0, 0.08]] },
    theory: { principle: MODE === 'read'
        ? 'A thermometer is read at the end of the mercury thread, with the eye level with it. A clinical thermometer covers only 35 to 42 °C, because body temperature lies in that range, and a kink in its tube holds the thread until it is shaken down. A laboratory thermometer covers -10 to 110 °C, so its divisions are coarser.'
        : 'While a substance changes state, the heat going in does not raise its temperature: it is latent heat, spent on the change itself. So melting ice holds at 0 °C and boiling water holds at 100 °C under one atmosphere, however big the flame.',
      formula: MODE === 'read' ? 'least count = one small division of the scale' : 'heat in = latent heat of the change,  temperature holds',
      formulaNote: MODE === 'read' ? 'clinical 0.1 °C · laboratory 0.5 °C' : ICE ? 'ice melts at 0 °C at one atmosphere' : 'water boils at 100 °C at one atmosphere',
      more: MODE === 'read'
        ? ['The bulb must be fully in whatever is being measured and must not touch the vessel.',
          'Wait until the thread stops moving: a reading taken too early is too low.']
        : ['On the temperature-time graph the change of state is a flat part: time passes, the flame burns, the temperature does not move.',
          'A bigger flame does not make the water hotter than its boiling point; it only boils it away faster.'],
      precautions: MODE === 'read'
        ? 'Never put a clinical thermometer in hot water, and never shake a laboratory thermometer. Read with the eye level with the end of the thread.'
        : 'The teacher lights and caps the lamp. Keep the beaker half full on the wire gauze, stir gently, and never lean over boiling water. Use a laboratory thermometer, never a clinical one.' },
    book: { title: MODE === 'read' ? 'Expt. — Reading a thermometer' : ICE ? 'Expt. — Melting point of ice' : 'Expt. — Boiling point of water',
      lines: MODE === 'read'
        ? ['Aim: to read a clinical and a laboratory thermometer.', 'Clinical: 35 to 42 °C, least count 0.1 °C.',
          'Laboratory: -10 to 110 °C, least count 0.5 °C.', 'Eye level with the end of the thread.']
        : ['Aim: to find the temperature at which the state changes.', 'Readings every ' + EVERY + ' s, thermometer least count ' + p.lc.toFixed(1) + ' °C.',
          'While the state changes the temperature does not rise.', 'Mean of the flat readings = ' + (ICE ? 'melting' : 'boiling') + ' point.'],
      columns: bookCols },
    graph: MODE === 'phase' ? { x: function (r) { return r.t; }, y: function (r) { return r.reading; },
      xlabel: 't (s)', ylabel: 'T (°C)', x0: 0, y0: Math.min(0, Math.floor(p.T0 / 10) * 10) } : null,
    result: function (rows) {
      if (MODE === 'read') {
        var m = mean(rows.map(function (r) { return r.reading; }));
        if (!isFinite(m)) return null;
        return { label: 'Temperature', value: m, unit: '°C', digits: 1, truth: p.T0, note: 'Mean of the readings.' };
      }
      var h = rows.filter(function (r) { return r.hold; }).map(function (r) { return r.reading; });
      if (h.length < 1) return null;
      return { label: ICE ? 'Melting point' : 'Boiling point', value: mean(h), unit: '°C', digits: 1, truth: p.Tp,
        note: 'Mean of the ' + h.length + ' readings taken while the state was changing.' };
    },
    tol: 0.02,
    chips: MODE === 'read' ? ['Why does a clinical thermometer stop at 42 °C?', 'What is the least count here?', 'Check my readings']
      : ['Why does the temperature stop rising?', 'What is latent heat?', 'Would a bigger flame change the answer?', 'Check my readings'],
    viva: MODE === 'read'
      ? [['Why is a clinical thermometer not used for boiling water?', ['Its range ends at 42 °C and it would burst', 'It is too short', 'It reads too slowly'], 0,
        'A thermometer can only be used inside its own range.'],
        ['The least count of a laboratory thermometer here is', ['0.5 °C', '0.1 °C', '1 mm'], 0, 'Its smallest division is half a degree.']]
      : [['While the state changes, the heat going in is spent on', ['The change of state', 'Raising the temperature', 'Nothing'], 0,
        'That heat is the latent heat of the change.'],
        ['A bigger flame under boiling water makes it', ['Boil away faster at the same temperature', 'Hotter than 100 °C', 'Stop boiling'], 0,
          'The boiling point does not depend on the size of the flame.']],
    askState: function () {
      return { set_up: MODE === 'read' ? 'reading thermometers' : ICE ? 'melting ice' : 'boiling water',
        thermometer: st.chosen ? st.chosen.name : null, least_count_C: st.chosen ? st.chosen.lc : p.lc,
        thermometer_C: +readT(MODE === 'read' ? st.shown : sim.T, st.chosen ? st.chosen.lc : p.lc).toFixed(1),
        lamp_lit: st.lit, stopwatch_s: +watch.t.toFixed(0), stopwatch_running: watch.on,
        state_changing_now: MODE === 'phase' ? changing() : null, time_runs_faster_by: st.speed,
        readings_taken: S.rows.length, readings_while_changing: MODE === 'phase' ? holdRows().length : null };
    },
    steps: MODE === 'read' ? readSteps : phaseSteps,
    tick: function (dt) {
      if (MODE === 'phase') {
        if (st.lit) { K.step(sim, p, dt * st.speed); if (watch.on) watch.t += dt * (st.speed - 1); }
        if (st.auto && watch.on && watch.t >= st.nextMark) { st.nextMark += EVERY; record(); }
        st.shown += (sim.T - st.shown) * Math.min(1, dt * 5);
        if (ICE) { var left = p.Q0 > 0 ? Math.max(0, Math.min(1, sim.Q / p.Q0)) : 0;
          ice.forEach(function (c, i) { var s = Math.max(0.05, left - i * 0.02); c.scale.setScalar(s); c.visible = s > 0.08; }); }
        flame.visible = st.lit; flame.quaternion.copy(S.camera.quaternion);
        if (st.lit) { st.flame += dt * 9; flame.scale.set(1 + 0.06 * Math.sin(st.flame), 1 + 0.1 * Math.sin(st.flame * 1.7), 1); }
        var hot = Math.max(0, Math.min(1, (sim.T - 70) / 30)), now = (S._steam = (S._steam || 0) + dt);
        wisps.forEach(function (w, i) { var ph = (now * 0.3 + w.userData.ph) % 1;
          w.position.set(BX + Math.sin(ph * 6 + i) * 0.013, GAUZE_Y + BK.h + 0.01 + ph * 0.13, BZ + 0.004);
          w.quaternion.copy(S.camera.quaternion); w.scale.setScalar(0.6 + ph * 1.5);
          w.material.opacity = hot * 0.3 * Math.sin(ph * Math.PI); });
      } else {
        var target = st.dipped ? p.T0 : p.Ts;
        st.shown += (target - st.shown) * Math.min(1, dt * 2.2);
      }
      var shownT = MODE === 'read' ? st.shown : sim.T;
      labTh.set(Math.max(LABT.min, Math.min(LABT.max, shownT)));
      clinTh.set(Math.max(CLINICAL.min, Math.min(CLINICAL.max, st.chosen === CLINICAL ? st.shown : 35.2)));
      hudT.set(readT(shownT, st.chosen ? st.chosen.lc : p.lc).toFixed(1) + ' °C');
      hudt.set(MODE === 'phase' ? watch.t.toFixed(0) + ' s' : (st.chosen ? st.chosen.lc.toFixed(1) : p.lc.toFixed(1)) + ' °C');
      hudN.set(String(S.rows.length));
    },
  };
});
