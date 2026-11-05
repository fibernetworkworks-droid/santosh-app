/* Prayogshala studio module: the school conduction bench (NCERT Class VII, Heat).
   One rig, two set-ups - the lab id picks the mode:
     school-conduction-rod        a metal rod heated at one end, with wax-stuck pins that fall in turn
     school-spoons-conduction     spoons of different materials standing in hot water, butter on the handle
   Physics: the conduction_fin kernel from the wave_heat_school pack - the same numbers the server checks.
   The conductivity of the sample is the hidden knob; what the student measures is how hot the far point gets. */
HoolaStudio.define('school-conduction-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.conduction_fin;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('conduction_fin');
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var MODE = /spoon/.test(BASE) ? 'spoons' : 'rod';
  var SAMPLE = String((S.lab.variant && S.lab.variant.sample) || (MODE === 'spoons' ? 'Stainless steel spoon' : 'Copper rod'));
  // the metal the sample is made of decides only its colour and the word used on the bench
  var MAT = /copper/i.test(SAMPLE) ? { col: 0xc8764a, metal: 1, rough: 0.25, word: 'copper' }
    : /alumin/i.test(SAMPLE) ? { col: 0xc4c9ce, metal: 0.9, rough: 0.3, word: 'aluminium' }
      : /brass/i.test(SAMPLE) ? { col: 0xd6aa4c, metal: 1, rough: 0.2, word: 'brass' }
        : /glass/i.test(SAMPLE) ? { col: 0xdfe9ea, metal: 0, rough: 0.1, word: 'glass' }
          : /wood/i.test(SAMPLE) ? { col: 0xb5834a, metal: 0, rough: 0.8, word: 'wood' }
            : /plastic|nylon/i.test(SAMPLE) ? { col: 0xe8e3d6, metal: 0, rough: 0.55, word: 'plastic' }
              : { col: 0xd2d6d9, metal: 1, rough: 0.22, word: 'steel' };
  var PINS = MODE === 'rod' ? [0.05, 0.1, 0.15, 0.2, 0.25] : [];
  var EVERY = 1;
  var sim = { t: 0 };
  var st = { lit: MODE === 'spoons', poured: MODE === 'rod', speed: 20, xm: p.xm, touching: false, shown: p.Ts,
    fallen: [], butter: 1, watched: 0, settled: false, notes: [] };

  function Tat(x) { return K.at(p, x, sim.t); }
  function steadyAt(x) { return K.steady(p, x); }
  function readT(v) { return Math.round(v * 2) / 2; }                 // thermometer least count 0.5 degC
  function started() { return MODE === 'rod' ? st.lit : st.poured; }

  // ---------------------------------------------------------------- apparatus
  var X0 = -0.3, ROD_Y = 0.17, BZ = -0.1;                              // the hot end sits at x = X0
  var rodM = new T.MeshStandardMaterial({ color: MAT.col, roughness: MAT.rough, metalness: MAT.metal });
  var rig = new T.Group(); S.scene.add(rig);
  var sample = new T.Group(); rig.add(sample);
  var beaker = null, lamp = null, flame = null, butter = null, pinG = [];

  if (MODE === 'rod') {
    var rod = S.mesh(new T.CylinderGeometry(p.d / 2, p.d / 2, p.Lr, 28), rodM);
    rod.rotation.z = Math.PI / 2; rod.position.set(X0 + p.Lr / 2, ROD_Y, BZ); sample.add(rod);
    var slab = S.label(SAMPLE.toUpperCase(), { w: 0.07, ratio: 0.16, color: '#f3e8d2' });
    slab.position.set(X0 + p.Lr / 2, ROD_Y + 0.035, BZ + 0.002); sample.add(slab);
    // a clamp stand holds the cool end; the hot end is free over the lamp
    var stand = S.stand({ x: X0 + p.Lr + 0.19, z: BZ - 0.12, h: 0.42, armY: ROD_Y, armLen: 0.14 });
    // the spirit lamp under the hot end
    lamp = new T.Group(); rig.add(lamp); lamp.position.set(X0, 0, BZ);
    lamp.add(function () { var b = S.mesh(new T.CylinderGeometry(0.028, 0.03, 0.045, 28), M.brass); b.position.y = 0.0225; return b; }());
    lamp.add(function () { var c = S.mesh(new T.CylinderGeometry(0.009, 0.011, 0.016, 20), M.brass); c.position.y = 0.052; return c; }());
    lamp.add(function () { var w = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.01, 10), new T.MeshStandardMaterial({ color: 0x3a3a38, roughness: 1 })); w.position.y = 0.064; return w; }());
    var llab = S.label('SPIRIT LAMP', { w: 0.042, ratio: 0.2, color: '#5a3b16' }); llab.position.set(0, 0.026, 0.0305); lamp.add(llab);
    var flameTex = S.canvasTex(128, 256, function (x, w, h) {
      var g = x.createRadialGradient(w / 2, h * 0.7, 4, w / 2, h * 0.62, h * 0.45);
      g.addColorStop(0, 'rgba(255,246,205,.95)'); g.addColorStop(0.35, 'rgba(255,176,60,.75)'); g.addColorStop(1, 'rgba(255,120,20,0)');
      x.fillStyle = g; x.fillRect(0, 0, w, h);
    });
    flame = new T.Mesh(new T.PlaneGeometry(0.055, 0.09), new T.MeshBasicMaterial({ map: flameTex, transparent: true, depthWrite: false, depthTest: false, toneMapped: false }));
    flame.position.set(X0, 0.112, BZ); flame.renderOrder = 2; flame.visible = false; S.scene.add(flame);
    S.contact(0.12, 0.12, X0, BZ, 0.45);
    // wax-stuck pins hanging under the rod
    PINS.forEach(function (x, i) {
      var g = new T.Group(); rig.add(g); g.position.set(X0 + x, ROD_Y - p.d / 2, BZ);
      var wax = S.mesh(new T.SphereGeometry(0.0055, 14, 10), new T.MeshStandardMaterial({ color: 0xf2eadb, roughness: 0.75 }));
      wax.position.y = -0.002; g.add(wax);
      var pin = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.03, 10), M.chrome); pin.position.y = -0.019; g.add(pin);
      var head = S.mesh(new T.SphereGeometry(0.0022, 10, 8), M.chrome); head.position.y = -0.034; g.add(head);
      var lb = S.label(Math.round(x * 100) + ' cm', { w: 0.024, ratio: 0.3, color: '#5a3b16' });
      lb.position.set(0, -0.052, 0.004); g.add(lb);
      pinG.push({ g: g, x: x, y0: ROD_Y - p.d / 2, v: 0, down: 0 });
    });
  } else {
    // a beaker of hot water with the spoon standing in it
    var SBX = -0.1, SBR = 0.062, SBH = 0.14;
    beaker = S.beaker(SBR, SBH, [SBX, 0, BZ]);
    var hotw = S.mesh(new T.CylinderGeometry(SBR * 0.95, SBR * 0.95, 0.092, 36),
      new T.MeshStandardMaterial({ color: 0xa8d2e4, roughness: 0.06, metalness: 0.08 }), false);
    hotw.position.y = 0.048; beaker.add(hotw);
    var blab = S.label('HOT WATER', { w: 0.058, ratio: 0.2, color: '#a3241b', weight: 700 });
    blab.position.set(0, 0.038, SBR + 0.001); beaker.add(blab);
    S.contact(0.2, 0.2, SBX, BZ, 0.5);
    var TILT = 0.24;
    var handle = S.mesh(new T.BoxGeometry(0.014, p.Lr, 0.004), rodM);
    handle.position.set(SBX + Math.sin(TILT) * p.Lr / 2, 0.062 + Math.cos(TILT) * p.Lr / 2, BZ);
    handle.rotation.z = -TILT; sample.add(handle);
    var bowl = S.mesh(new T.SphereGeometry(0.02, 20, 14), rodM);
    bowl.scale.set(1, 0.4, 0.7); bowl.position.set(SBX - Math.sin(TILT) * 0.02, 0.05, BZ); sample.add(bowl);
    var slab2 = S.label(SAMPLE.toUpperCase(), { w: 0.08, ratio: 0.16, color: '#f3e8d2' });
    slab2.position.set(SBX + 0.1, 0.23, BZ - 0.01); sample.add(slab2);
    butter = S.mesh(new T.SphereGeometry(0.007, 14, 10), new T.MeshStandardMaterial({ color: 0xf5dd8a, roughness: 0.6 }));
    butter.position.set(SBX + Math.sin(TILT) * p.Lr, 0.062 + Math.cos(TILT) * p.Lr, BZ); sample.add(butter);
    var bl2 = S.label('BUTTER', { w: 0.032, ratio: 0.26, color: '#8a6a22' });
    bl2.position.set(butter.position.x + 0.034, butter.position.y + 0.008, BZ + 0.004); sample.add(bl2);
    st.spoon = { tilt: TILT, x0: SBX, y0: 0.062 };
  }
  function pointAt(x) {                                 // where distance x along the sample is, in world space
    if (MODE === 'rod') return new T.Vector3(X0 + x, ROD_Y - 0.002, BZ + 0.012);
    return new T.Vector3(st.spoon.x0 + Math.sin(st.spoon.tilt) * x + 0.012, st.spoon.y0 + Math.cos(st.spoon.tilt) * x, BZ + 0.01);
  }
  // the thermometer that is touched against the sample
  var RX = MODE === 'rod' ? 0.36 : 0.18;
  var rest = S.rounded(0.07, 0.07, 0.024, 0.006, M.darkWood); rest.rotation.x = -Math.PI / 2;
  rest.position.set(RX, 0.012, 0.1); S.scene.add(rest);
  var restN = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.03, 16), M.cork); restN.position.set(RX, 0.03, 0.1); S.scene.add(restN);
  S.contact(0.1, 0.1, RX, 0.1, 0.45);
  var thermo = S.thermometer({ len: 0.2, min: -10, max: 110, value: p.Ts, pos: [RX, 0.04, 0.1] });
  thermo.rotation.z = 0.22;
  var watch = S.stopwatch([0.56, 0.035, -0.04], [-1.2, -0.3, 0]);

  S.addApparatus('sample', sample, MODE === 'rod' ? SAMPLE : SAMPLE,
    MODE === 'rod' ? 'A rod ' + Math.round(p.Lr * 100) + ' cm long and ' + (p.d * 1000).toFixed(0) + ' mm thick. Its far end is clamped; its near end is heated.'
      : 'The spoon stands in the hot water with its handle up and clear of the glass.');
  if (MODE === 'rod') {
    S.addApparatus('lamp', lamp, 'Spirit lamp', 'The teacher lights it under the end of the rod and caps it afterwards.');
    S.addApparatus('pins', pinG[0].g, 'Wax-stuck pins', 'Each pin is stuck under the rod with a blob of wax. When the wax there melts, the pin falls.');
  } else {
    S.addApparatus('beaker', beaker, 'Beaker of hot water', 'The water is poured in by the teacher. It heats the lower end of the spoon.');
    S.addApparatus('butter', butter, 'Butter on the handle', 'A blob at the top of the handle. If the handle gets warm enough, it melts.');
  }
  S.addApparatus('thermo', thermo, 'Thermometer', 'Least count 0.5 °C. Touched against the sample at a measured distance and held until the thread stops.');
  S.addApparatus('sw', watch.group, 'Stopwatch', 'Started with the heating, so every event has its time.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudT = S.hudCard('Thermometer'), hudt = S.hudCard('Stopwatch'), hudN = S.hudCard('Readings');

  // ---------------------------------------------------------------- actions
  function startHeat() {
    if (S.hand.busy || started()) return Promise.resolve();
    var at = MODE === 'rod' ? new T.Vector3(X0 + 0.06, 0.08, BZ + 0.05) : new T.Vector3(X0 + 0.12, 0.12, BZ + 0.05);
    return S.hand.reach(at, 'side', 700).then(function () { return S.hand.away(400); }).then(function () {
      if (MODE === 'rod') { st.lit = true; if (flame) flame.visible = true; S.click(180, 0.12, 0.05);
        S.say('The teacher has lit the lamp under the end of the rod. Do not touch the rod anywhere near that end.'); }
      else { st.poured = true; S.click(300, 0.1, 0.05);
        S.say('Hot water poured in by the teacher. The lower end of the spoon is now at about ' + Math.round(p.Th) + ' °C.'); }
      sim.t = 0; if (!watch.on) { watch.t = 0; watch.on = true; }
      S.render();
    });
  }
  function moveThermo(x) {
    if (S.hand.busy) return Promise.resolve();
    if (!(x >= 0.02 && x <= p.Lr + 1e-9)) { S.say('Keep the bulb on the sample: between 2 cm and ' + Math.round(p.Lr * 100) + ' cm from the hot end.'); return Promise.resolve(); }
    var from = thermo.position.clone(), to = pointAt(x).add(new T.Vector3(0, 0.012, 0.004));
    return S.hand.pinchMove(from.clone().add(new T.Vector3(0.02, 0.06, 0.02)), function (k) { return from.clone().lerp(to, k).add(new T.Vector3(0, 0.06, 0.02)); },
      function (k) { thermo.position.copy(from.clone().lerp(to, k)); thermo.rotation.z = 0.25 * (1 - k) + (MODE === 'rod' ? 0 : -st.spoon.tilt) * k; }, { ms: 900 })
      .then(function () { thermo.position.copy(to); st.xm = x; st.touching = true; st.settled = false; st.shown = Math.max(p.Ts, st.shown);
        S.say('The bulb touches the sample ' + Math.round(x * 100) + ' cm from the hot end. Hold it until the thread stops moving.'); S.render(); });
  }
  function settle() {
    if (!st.touching) { S.say('Touch the thermometer against the sample first.'); return; }
    if (!started()) { S.say('The sample is not being heated yet.'); return; }
    var last = Tat(st.xm), i;
    for (i = 0; i < 500; i++) {                                     // hold it there until the thread stops rising
      S.advance(2.0);
      var now = Tat(st.xm);
      if (Math.abs(now - last) < 0.004) break;
      last = now;
    }
    st.settled = true; st.shown = Tat(st.xm);
    S.say('The thread has stopped at ' + readT(st.shown).toFixed(1) + ' °C, ' + Math.round(st.xm * 100) + ' cm from the hot end.');
    S.render();
  }
  function record() {
    if (!st.settled) { S.say('Wait until the thread stops moving before you write the reading down.'); return; }
    var x = Math.round(st.xm * 100) / 100;
    for (var i = S.rows.length - 1; i >= 0; i--) if (Math.abs(S.rows[i].x - x) < 1e-6) S.rows.splice(i, 1);
    S.rows.push({ x: x, reading: readT(Tat(x)), t: Math.round(watch.t), fell: fellAt(x) });
    S.rows.sort(function (a, b) { return a.x - b.x; });
    S.book.draw(); S.say('Written: ' + Math.round(x * 100) + ' cm, ' + readT(Tat(x)).toFixed(1) + ' °C.'); S.render();
  }
  function fellAt(x) { for (var i = 0; i < st.fallen.length; i++) if (Math.abs(st.fallen[i].x - x) < 1e-6) return st.fallen[i].t; return null; }
  function setSpeed(v) { st.speed = v; S.render(); }

  // ---------------------------------------------------------------- steps
  var steps = [
    { id: 'start', title: MODE === 'rod' ? 'Heat the end' : 'Stand it in hot water', view: MODE === 'rod' ? 'lamp' : 'beaker',
      render: function (u) {
        u.h2(MODE === 'rod' ? 'The teacher lights the lamp' : 'The teacher pours the hot water');
        u.p(MODE === 'rod'
          ? 'The rod is clamped level, with wax-stuck pins at 5, 10, 15, 20 and 25 cm from the end that is to be heated. Start the stopwatch at the moment the lamp is lit.'
          : 'The spoon stands in the beaker, handle up and clear of the glass, with a blob of butter at the top of the handle. Start the stopwatch when the water goes in.');
        u.row(u.button(started() ? (MODE === 'rod' ? 'The lamp is lit' : 'The water is in') : (MODE === 'rod' ? 'Ask the teacher to light the lamp' : 'Ask the teacher to pour the hot water'),
          function () { startHeat(); S.render(); }, !started(), started() || S.hand.busy));
        u.live(function () { return started() ? 't = ' + watch.t.toFixed(0) + ' s' : 'Not heating yet'; });
        u.note(MODE === 'rod' ? 'Never touch the rod near the flame, and let it cool on the stand before taking it off.'
          : 'Hot water can scald. The teacher pours it; hold the spoon only by its very top.');
        u.next(MODE === 'rod' ? 'Next: watch the pins' : 'Next: watch the butter', started());
      },
      ok: function () { return started(); },
      auto: function () { return startHeat(); } },
    { id: 'watch', title: MODE === 'rod' ? 'Watch the pins' : 'Watch the butter', view: 'sample', render: function (u) {
        u.h2(MODE === 'rod' ? 'Which pin falls first?' : 'Does the butter melt?');
        u.p(MODE === 'rod'
          ? 'The heat travels along the rod from particle to particle. The wax nearest the flame melts first, so that pin falls first. Note the time of each fall.'
          : 'If the handle carries heat well, the butter at the top melts; if the material is a poor conductor, the handle stays cool and the butter does not melt at all.');
        var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
        [5, 20, 60].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
        u.live(function () {
          return 't = ' + watch.t.toFixed(0) + ' s · '
            + (MODE === 'rod' ? st.fallen.length + ' of ' + PINS.length + ' pins have fallen'
              : st.butter < 0.2 ? 'the butter has melted away' : st.butter < 1 ? 'the butter is melting' : 'the butter is still solid')
            + ' · handle ' + readT(Tat(p.Lr)).toFixed(1) + ' °C';
        });
        if (st.notes.length) { u.h3('What happened'); st.notes.slice(-6).forEach(function (n) { u.p(n); }); }
        u.next('Next: measure the temperatures', st.watched >= 120);
        if (st.watched < 120) u.p('Watch it for a little longer: ' + Math.round(st.watched) + ' s of ' + 120 + ' s watched.');
      },
      ok: function () { return st.watched >= 120; },
      auto: function () { for (var i = 0; i < 200 && st.watched < 125; i++) S.advance(1.0); return Promise.resolve(); } },
    { id: 'measure', title: 'Measure', view: 'thermo', render: function (u) {
        u.h2('How hot is it at each distance?');
        u.p('Touch the thermometer against the sample, hold it until the thread stops, and write the temperature down. '
          + 'Take at least three distances, and be sure to take the point ' + Math.round(p.xm * 100) + ' cm from the hot end.');
        u.slider('Distance from the hot end', 2, Math.round(p.Lr * 100), 1, function () { return Math.round(st.xm * 100); },
          function (v) { st.xm = v / 100; }, 'cm', 0);
        u.row(u.button('Touch the thermometer here', function () { moveThermo(st.xm); S.render(); }, true, S.hand.busy),
          u.button('Hold it until the thread stops', function () { settle(); }, false, !st.touching || S.hand.busy),
          u.button('Record this reading', function () { record(); }, false, !st.settled || S.hand.busy));
        u.live(function () { return 'At ' + Math.round(st.xm * 100) + ' cm: ' + readT(st.touching ? st.shown : p.Ts).toFixed(1) + ' °C'
          + (st.settled ? ' (steady)' : ' (still changing)'); });
        u.h3('Observation table'); u.table();
        u.next('Next: work out the result', S.rows.length >= 3 && !!atPoint());
        if (!atPoint()) u.p('The reading ' + Math.round(p.xm * 100) + ' cm from the hot end is still missing.');
      },
      ok: function () { return S.rows.length >= 3 && !!atPoint(); },
      auto: function () {
        var xs = [0.05, Math.round(p.Lr * 50) / 100, p.xm], pr = Promise.resolve();
        xs.forEach(function (x) { pr = pr.then(function () { return moveThermo(x); }).then(function () { settle(); record(); }); });
        return pr; } },
  ];
  function atPoint() { for (var i = 0; i < S.rows.length; i++) if (Math.abs(S.rows[i].x - Math.round(p.xm * 100) / 100) < 1e-6) return S.rows[i]; return null; }

  return {
    camera: MODE === 'rod' ? { pos: [0.3, 0.6, 0.95], look: [-0.1, 0.12, -0.08] } : { pos: [0.26, 0.42, 0.66], look: [-0.04, 0.12, -0.07] },
    views: { sample: MODE === 'rod' ? [[0.1, 0.42, 0.62], [-0.14, 0.14, -0.1]] : [[0.16, 0.38, 0.52], [-0.16, 0.16, -0.1]],
      lamp: [[-0.08, 0.26, 0.34], [X0, 0.08, BZ]], pins: [[0.0, 0.3, 0.4], [-0.16, 0.12, -0.1]],
      beaker: [[0.06, 0.3, 0.4], [-0.1, 0.08, BZ]], butter: [[0.04, 0.42, 0.42], [-0.08, 0.2, -0.1]],
      thermo: [[0.2, 0.4, 0.58], [-0.06, 0.14, -0.06]], sw: [[0.46, 0.26, 0.3], [0.56, 0.03, -0.04]],
      book: [[-0.52, 0.56, 0.6], [-0.62, 0.0, 0.12]] },
    theory: { principle: 'In a solid, heat travels by conduction: each particle passes it on to the next without moving from its place. '
        + 'Along a rod heated at one end the temperature falls away from the hot end, because heat is also lost to the air on the way. '
        + 'A good conductor carries it far; a poor one hardly carries it at all.',
      formula: 'T(x) = Ts + (Th − Ts) cosh((L − x)/λ) / cosh(L/λ)',
      formulaNote: 'λ = √(k d / 4h): the better the conductor, the longer λ, and the hotter the far end',
      more: ['Metals are good conductors; wood, plastic, glass and still air are poor ones, which is why pans have wooden handles.',
        MODE === 'rod' ? 'The wax nearest the flame reaches its melting point first, so the pins fall in order, the nearest first.'
          : 'The butter at the top of the handle melts only if that handle carries the heat up to it.'],
      precautions: MODE === 'rod'
        ? 'The teacher lights and caps the lamp. Never touch the rod near the flame; let it cool on the stand before taking it off. Keep the pins hanging freely.'
        : 'Hot water can scald: the teacher pours it. Hold the spoon by its very top, keep it clear of the glass, and keep the beaker away from the edge of the bench.' },
    book: { title: MODE === 'rod' ? 'Expt. — Conduction along a metal rod' : 'Expt. — Conductors and insulators',
      lines: ['Aim: to see how heat is carried along ' + (MODE === 'rod' ? 'a rod' : 'a spoon handle') + ' and how hot the far end gets.',
        'Sample: ' + SAMPLE + '.', 'Hot end ' + Math.round(p.Th) + ' °C, room ' + Math.round(p.Ts) + ' °C.',
        'Thermometer least count 0.5 °C.'],
      at: [-0.62, 0.1, 0.12],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Distance (cm)', get: function (r) { return (r.x * 100).toFixed(0); } },
        { label: 'T (°C)', get: function (r) { return r.reading.toFixed(1); } },
        { label: MODE === 'rod' ? 'Pin fell at (s)' : 'Butter', get: function (r) { return r.fell === null ? '—' : Math.round(r.fell) + ' s'; } }] },
    graph: { x: function (r) { return r.x * 100; }, y: function (r) { return r.reading; },
      xlabel: 'distance from the hot end (cm)', ylabel: 'T (°C)', x0: 0, y0: Math.max(0, Math.round(p.Ts) - 10),
      line: function () { return function (xcm) { return steadyAt(Math.max(0, Math.min(p.Lr, xcm / 100))); }; } },
    result: function () {
      var row = atPoint(); if (!row) return null;
      return { label: 'Temperature ' + Math.round(p.xm * 100) + ' cm from the hot end', value: row.reading, unit: '°C', digits: 1,
        truth: steadyAt(p.xm), note: 'Steady reading on ' + SAMPLE.toLowerCase() + '; the curve drawn through the points is the fin equation.' };
    },
    tol: 0.03,
    chips: MODE === 'rod' ? ['Why does the nearest pin fall first?', 'Why does the far end never get as hot as the flame?', 'Check my readings']
      : ['Why is a cooking spoon wooden?', 'Why does the metal handle get hot?', 'Check my readings'],
    viva: [['Heat travels along a solid rod by', ['Conduction', 'Convection', 'Radiation'], 0,
      'The particles pass heat on without moving from their places.'],
      [MODE === 'rod' ? 'Why does the far end stay cooler than the heated end?' : 'Why does a wooden handle stay cool?',
        ['Heat is lost to the air on the way, and poor conductors pass on very little', 'Heat gets used up', 'The far end is thinner'], 0,
        'Along the rod heat leaks to the air, and in a poor conductor very little is passed on in the first place.']],
    askState: function () {
      return { set_up: MODE === 'rod' ? 'rod with wax-stuck pins' : 'spoons in hot water', sample: SAMPLE,
        heating: started(), stopwatch_s: +watch.t.toFixed(0), time_runs_faster_by: st.speed,
        thermometer_at_cm: Math.round(st.xm * 100), thermometer_C: +readT(st.touching ? st.shown : p.Ts).toFixed(1),
        reading_is_steady: st.settled, pins_fallen: MODE === 'rod' ? st.fallen.length : null,
        butter_left: MODE === 'spoons' ? +st.butter.toFixed(2) : null, readings_taken: S.rows.length };
    },
    steps: steps,
    tick: function (dt) {
      if (started()) {
        sim.t += dt * st.speed;
        if (watch.on) watch.t += dt * (st.speed - 1);
        st.watched += dt * st.speed;
      }
      // pins fall when the wax at their place reaches its melting point
      pinG.forEach(function (q) {
        var tm = K.melt_time(p, q.x);
        if (!q.down && tm > 0 && sim.t >= tm) {
          q.down = 1; st.fallen.push({ x: q.x, t: sim.t });
          st.notes.push('The pin ' + Math.round(q.x * 100) + ' cm from the hot end fell at ' + Math.round(sim.t) + ' s.');
          S.click(1600, 0.03, 0.05);
        }
        if (q.down) { q.v += 9.8 * dt; q.g.position.y = Math.max(0.012, q.g.position.y - q.v * dt);
          if (q.g.position.y <= 0.0121) { q.v = 0; q.g.rotation.z = 1.5708; } }
      });
      if (MODE === 'spoons' && butter) {
        var hot = Tat(p.Lr);
        if (hot >= p.Tmelt && st.butter > 0.05) { st.butter = Math.max(0.05, st.butter - dt * st.speed * 0.02);
          if (st.butter < 0.99 && !st.notes.length) st.notes.push('The butter at the top of the handle has started to melt.'); }
        butter.scale.set(1 + (1 - st.butter) * 0.6, Math.max(0.12, st.butter), 1 + (1 - st.butter) * 0.6);
      }
      if (flame) { flame.visible = st.lit; flame.quaternion.copy(S.camera.quaternion);
        if (st.lit) { var f = (S._fl = (S._fl || 0) + dt * 9); flame.scale.set(1 + 0.07 * Math.sin(f), 1 + 0.12 * Math.sin(f * 1.7), 1); } }
      var target = st.touching && started() ? Tat(st.xm) : p.Ts;
      st.shown += (target - st.shown) * Math.min(1, dt * 3);
      thermo.set(Math.max(-10, Math.min(110, st.shown)));
      hudT.set(readT(st.shown).toFixed(1) + ' °C'); hudt.set(watch.t.toFixed(0) + ' s'); hudN.set(String(S.rows.length));
    },
  };
});
