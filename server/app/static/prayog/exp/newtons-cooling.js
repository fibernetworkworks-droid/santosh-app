/* Prayogshala studio module: Newton's law of cooling (NCERT Class XI).
   Physics: the cooling kernel from kernels.js (dT/dt = -k (T - Ts), RK4) - the same numbers the server checks.
   The hidden knob k (vessel + air) is what the student measures, from the slope of ln(T - Ts) against t. */
HoolaStudio.define('newtons-cooling', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.cooling;
  var up = new T.Vector3(0, 1, 0);
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('cooling');
  // the liquid that cools: from the variant's sample line, water when there is no variant
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var LIQ = /glycer/i.test(SAMPLE) ? { name: 'glycerine', cap: 'Glycerine', tag: 'HOT GLYCERINE', col: 0xe4ecea, deep: 0xc9d8d6, op: 0.82 }
    : /olive/i.test(SAMPLE) ? { name: 'olive oil', cap: 'Olive oil', tag: 'HOT OLIVE OIL', col: 0xc9b247, deep: 0xb39a2c, op: 0.88 }
    : { name: 'water', cap: 'Water', tag: 'HOT WATER', col: 0x9cc6d6, deep: 0x6aaccc, op: 0.9 };
  // reading interval: 30 s as in the manual, shorter when the liquid would reach room temperature before 6 readings
  var DT0 = Math.max(1, p.T0 - p.Ts), EVERY = 30;
  if (DT0 * Math.exp(-p.k * 150) < 2) EVERY = Math.max(5, Math.floor(Math.log(DT0 / 2) / (5 * p.k) / 5) * 5);
  else if (p.k * 240 < 0.5) EVERY = 60;
  var SPAN = 4 * EVERY;                                       // the readings must cover at least this many seconds
  var LC = 0.5;                                               // thermometer least count (°C)
  function readT(v) { return Math.round(v / LC) * LC; }
  var sim = K.init(p), st = { roomRead: false, Ts: null, poured: false, speed: 5, autoNote: false, nextMark: EVERY, shown: p.Ts };

  // ---------- helpers (a hand that carries a thing along several legs, then lets go)
  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'grip', 320); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }
  function clampStand(jx, jz, armY, armLen, h) {     // a retort stand whose clamp jaw reaches (jx, armY, jz) from behind
    var g = S.stand({ x: 0, z: 0, armY: armY, armLen: armLen, h: h });
    var blob = S.scene.children[S.scene.children.length - 1], rotY = -Math.PI / 2;
    g.rotation.y = rotY; var j = new T.Vector3(-0.19 + armLen, 0, 0).applyAxisAngle(up, rotY);
    g.position.set(jx - j.x, 0, jz - j.z);
    var bc = new T.Vector3(-0.12, 0, 0).applyAxisAngle(up, rotY); blob.position.set(g.position.x + bc.x, blob.position.y, g.position.z + bc.z); blob.rotation.z = rotY;
    return g;
  }
  var waterM = new T.MeshStandardMaterial({ color: LIQ.col, roughness: 0.05, metalness: 0.1, transparent: true, opacity: LIQ.op });
  function vessel(r, h, mat) {                       // thin-walled open vessel with a rolled rim (lathe)
    var pts = [[0, 0.0005], [r - 0.005, 0.0005], [r, 0.005], [r, h], [r + 0.0018, h + 0.0012], [r - 0.0012, h + 0.0004], [r - 0.0012, 0.006], [r - 0.006, 0.0018], [0, 0.0018]]
      .map(function (a) { return new T.Vector2(a[0], a[1]); });
    var m = mat.clone(); m.side = T.DoubleSide;
    return S.mesh(new T.LatheGeometry(pts, 48), m);
  }

  // ---------- apparatus
  var CX = 0.08, CZ = -0.06, BLOCK_H = 0.035, CAL_R = 0.036, CAL_H = 0.085, CAL_Y = BLOCK_H;
  var block = new T.Group(); S.scene.add(block);
  var bw = S.rounded(0.13, 0.13, BLOCK_H, 0.008, M.wood); bw.rotation.x = -Math.PI / 2; bw.position.set(CX, BLOCK_H / 2, CZ); block.add(bw);
  var felt = S.mesh(new T.CylinderGeometry(CAL_R + 0.003, CAL_R + 0.003, 0.002, 40), M.cork); felt.position.set(CX, BLOCK_H + 0.001, CZ); block.add(felt);
  var blab = S.label('INSULATING STAND', { w: 0.07, ratio: 0.14, color: '#5a3b16' }); blab.position.set(CX, BLOCK_H / 2, CZ + 0.0655); block.add(blab);
  S.contact(0.2, 0.2, CX, CZ, 0.55);
  var cal = new T.Group(); cal.position.set(CX, CAL_Y + 0.002, CZ); S.scene.add(cal);
  cal.add(vessel(CAL_R, CAL_H, new T.MeshStandardMaterial({ color: 0xe39a68, roughness: 0.28, metalness: 0.6 })));
  var water = S.mesh(new T.CylinderGeometry(CAL_R - 0.0014, CAL_R - 0.0014, 1, 40), waterM, false); cal.add(water);
  var WATER_FULL = 0.066;
  function setCalWater(f) { var hh = Math.max(0.0005, WATER_FULL * f); water.scale.y = hh; water.position.y = 0.002 + hh / 2; water.visible = f > 0.01; }
  setCalWater(0);
  // stirrer: copper rod with a ring at the bottom, resting on the rim
  var stir = new T.Group(); cal.add(stir);
  var srod = S.mesh(new T.CylinderGeometry(0.0013, 0.0013, 0.13, 10), M.copper); srod.position.y = 0.065; stir.add(srod);
  var sring = S.mesh(new T.TorusGeometry(0.012, 0.0013, 8, 24), M.copper); sring.rotation.x = Math.PI / 2; stir.add(sring);
  stir.position.set(0.016, 0.006, 0.012); stir.rotation.z = -0.12;
  // thermometer through the clamp jaw, bulb in the water
  var TX = CX - 0.012, TZ = CZ - 0.004;
  var thermo = S.thermometer({ len: 0.3, min: -10, max: 110, value: p.Ts, pos: [TX, CAL_Y + 0.016, TZ] });
  var stand = clampStand(TX, TZ, 0.27, 0.3, 0.46);
  // hot water in a beaker beside it (from the kettle)
  var BK = { r: 0.042, h: 0.11, x: 0.33, z: -0.04, level: 0.68 };
  var beaker = S.beaker(BK.r, BK.h, [BK.x, 0, BK.z]);
  var bwater = S.mesh(new T.CylinderGeometry(BK.r * 0.95, BK.r * 0.95, 1, 36), new T.MeshStandardMaterial({ color: LIQ.deep, roughness: 0.05, metalness: 0.08 }), false); beaker.add(bwater);
  beaker.setLevel = function (f) { var hh = Math.max(0.001, BK.h * f); bwater.scale.y = hh; bwater.position.y = 0.002 + hh / 2; bwater.visible = f > 0.02; };   // opaque water shows through the beaker glass
  beaker.setLevel(BK.level);
  var bkShadow = S.contact(0.12, 0.12, BK.x, BK.z, 0.45);
  var bl = S.label(LIQ.tag, { w: LIQ.tag.length > 10 ? 0.064 : 0.05, ratio: 0.2, color: '#a3241b', weight: 700 }); bl.position.set(0, 0.04, BK.r + 0.0008); beaker.add(bl);
  var stream = S.mesh(new T.CylinderGeometry(0.0035, 0.0045, 1, 12), waterM, false); stream.visible = false; S.scene.add(stream);
  var watch = S.stopwatch([0.3, 0.035, 0.17], [-1.15, 0, -0.2]);
  // steam wisps over hot water
  var steamTex = S.canvasTex(128, 128, function (x) { var g = x.createRadialGradient(64, 64, 2, 64, 64, 62); g.addColorStop(0, 'rgba(255,255,255,.75)'); g.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = g; x.fillRect(0, 0, 128, 128); });
  var wisps = []; for (var i = 0; i < 6; i++) { var w = new T.Mesh(new T.PlaneGeometry(0.045, 0.045), new T.MeshBasicMaterial({ map: steamTex, transparent: true, opacity: 0, depthWrite: false }));
    w.userData.ph = i / 6; S.scene.add(w); wisps.push(w); }

  S.addApparatus('cal', cal, 'Copper calorimeter', 'Thin copper vessel: it takes up the ' + LIQ.name + ' temperature quickly. Holds the hot ' + LIQ.name + ' that cools.');
  S.addApparatus('block', block, 'Wooden insulating stand', 'Wood conducts heat poorly, so the ' + LIQ.name + ' loses heat mainly to the air around it.');
  S.addApparatus('thermo', thermo, 'Mercury thermometer', 'Range −10 to 110 °C, least count 0.5 °C. The bulb sits in the ' + LIQ.name + ', clear of the bottom.');
  S.addApparatus('stand', stand, 'Clamp stand', 'Holds the thermometer upright so the bulb never touches the copper.');
  S.addApparatus('stir', stir, 'Stirrer', 'Keeps the ' + LIQ.name + ' at one temperature throughout.');
  S.addApparatus('beaker', beaker, 'Beaker of hot ' + LIQ.name, LIQ.cap + ' at about ' + Math.round(p.T0) + ' °C' + (LIQ.name === 'water' ? ' from the kettle' : ', heated in a water bath') + '. Hold it by the side and pour slowly.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Least count 0.01 s. Read the temperature every ' + EVERY + ' s.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var bookLines = ['Aim: to study the cooling of hot ' + LIQ.name + ' and find k.', 'Room temperature Ts = ……', 'dT/dt = −k(T − Ts)', 'ln(T − Ts) = ln(T₀ − Ts) − kt', 'Readings every ' + EVERY + ' s, thermometer LC 0.5 °C.'];
  var hudT = S.hudCard('Thermometer'), hudt = S.hudCard('Stopwatch'), hudN = S.hudCard('Readings');

  // ---------- actions
  function Tnow() { return sim.y[0]; }
  function readRoom() {
    if (st.poured) { S.say('The ' + LIQ.name + ' is already in. Room temperature is read before pouring.'); return; }
    st.roomRead = true; st.Ts = readT(p.Ts); bookLines[1] = 'Room temperature Ts = ' + st.Ts.toFixed(1) + ' °C'; S.focus('thermo');
    S.say('Room temperature Ts = ' + st.Ts.toFixed(1) + ' °C (thermometer in air). Written in your record book.'); S.book.draw(); S.render();
  }
  var bTarget0 = new T.Vector3(0.20, 0.205, BK.z);   // lip position when the beaker starts to tilt
  var lipEnd = new T.Vector3(CX + 0.03, CAL_Y + CAL_H + 0.03, CZ + 0.01);
  function lipLocal(th) { return new T.Vector3(-BK.r * Math.cos(th) - BK.h * Math.sin(th), -BK.r * Math.sin(th) + BK.h * Math.cos(th), 0); }
  function gripLocal(th) { var gx = BK.r + 0.004, gy = 0.065; return new T.Vector3(gx * Math.cos(th) - gy * Math.sin(th), gx * Math.sin(th) + gy * Math.cos(th), 0); }
  var bk = { pos: new T.Vector3(BK.x, 0, BK.z), th: 0 };
  function placeBeaker(pos, th) { bk.pos.copy(pos); bk.th = th; beaker.position.copy(pos); beaker.rotation.z = th;
    bkShadow.position.set(pos.x + 0.02 * Math.sin(th), 0.0008, pos.z); bkShadow.material.opacity = Math.max(0.1, 0.45 - pos.y * 2); }
  function gripAt(pos, th) { return pos.clone().add(gripLocal(th)); }
  function pour() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.roomRead) { S.say('Read the room temperature first, with the thermometer still in air.'); return Promise.resolve(); }
    if (st.poured) { S.say('The calorimeter is already filled.'); return Promise.resolve(); }
    var start = new T.Vector3(BK.x, 0, BK.z), lifted = bTarget0.clone().sub(lipLocal(0)), TH = 1.72;
    function posAt(th, lip) { return lip.clone().sub(lipLocal(th)); }
    var legs = [
      { ms: 1100, fn: function (k) { return gripAt(start.clone().lerp(lifted, k), 0); }, onK: function (k) { placeBeaker(start.clone().lerp(lifted, k), 0); } },
      { ms: 2200, fn: function (k) { var th = TH * k; return gripAt(posAt(th, bTarget0.clone().lerp(lipEnd, k)), th); },
        onK: function (k) { var th = TH * k; placeBeaker(posAt(th, bTarget0.clone().lerp(lipEnd, k)), th);
          var f = Math.max(0, Math.min(1, (th - 1.0) / (TH - 1.0))); beaker.setLevel(BK.level * (1 - 0.92 * f)); setCalWater(f);
          if (f > 0 && f < 1 && !S.fast) { var lip = bk.pos.clone().add(lipLocal(th)), y0 = CAL_Y + 0.004 + WATER_FULL * f, len = Math.max(0.005, lip.y - y0);
            stream.visible = true; stream.scale.y = len; stream.position.set(lip.x - 0.004, y0 + len / 2, lip.z); } else stream.visible = false; } },
      { ms: 1400, fn: function (k) { var th = TH * (1 - k); return gripAt(posAt(TH, lipEnd).lerp(start, k), th); },
        onK: function (k) { stream.visible = false; placeBeaker(posAt(TH, lipEnd).lerp(start, k), TH * (1 - k)); } },
    ];
    return carry(gripAt(start, 0), legs, 'pinch').then(function () {
      placeBeaker(start, 0); beaker.setLevel(BK.level * 0.08); setCalWater(1); stream.visible = false;
      sim = K.init(p); st.poured = true; S.say('Hot ' + LIQ.name + ' poured. Stir gently and watch the thermometer rise to about ' + readT(p.T0).toFixed(0) + ' °C.'); S.render(); });
  }
  function pressWatch() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.poured) { S.say('Pour the hot ' + LIQ.name + ' in first.'); return Promise.resolve(); }
    if (!watch.on && S.rows.length) { S.say('This series is already timed. To start a fresh series, delete the readings in the table first.'); return Promise.resolve(); }
    return S.hand.tap(watch.start).then(function () {
      S.click(2400);
      if (!watch.on) { watch.t = 0; watch.on = true; st.nextMark = EVERY; note(true); }
      else { watch.on = false; S.say('Stopwatch stopped at ' + watch.t.toFixed(1) + ' s.'); }
      S.render(); });
  }
  function note(quiet) {
    if (!st.poured) { S.say('Pour the hot ' + LIQ.name + ' in first.'); return; }
    if (!watch.on) { S.say('Start the stopwatch first: every reading needs its time.'); return; }
    var t = Math.round(watch.t), Tr = readT(Tnow());
    if (S.rows.length && t - S.rows[S.rows.length - 1].t < Math.max(3, EVERY / 3)) { S.say('Wait for the next reading: about ' + EVERY + ' s apart.'); return; }
    if (Tr - st.Ts < 1) { S.say('The ' + LIQ.name + ' is almost at room temperature now. Stop: these readings are too close to Ts to use.'); return; }
    S.addRow({ t: t, T: Tr });
    if (!quiet) S.say('Written: t = ' + t + ' s, T = ' + Tr.toFixed(1) + ' °C.');
  }
  function setSpeed(v) { st.speed = v; S.render(); }

  // ---------- fit: ln(T - Ts) against t, weighted by (T - Ts)² (each point's reading error is the same 0.5 °C)
  function fit(rows) { var Ts = st.Ts === null ? readT(p.Ts) : st.Ts, sw = 0, sx = 0, sy = 0, sxx = 0, sxy = 0, n = 0;
    rows.forEach(function (r) { var d = r.T - Ts; if (d <= 0.4) return; var w = d * d, y = Math.log(d); sw += w; sx += w * r.t; sy += w * y; sxx += w * r.t * r.t; sxy += w * r.t * y; n++; });
    var den = sw * sxx - sx * sx; if (n < 3 || !den) return null; var m = (sw * sxy - sx * sy) / den; return { k: -m, A: Math.exp((sy - m * sx) / sw), Ts: Ts }; }

  return {
    camera: { pos: [0.62, 0.5, 1.08], look: [0.06, 0.12, -0.06] },
    views: { cal: [[0.3, 0.32, 0.45], [0.1, 0.1, -0.06]], block: [[0.25, 0.18, 0.35], [0.08, 0.04, -0.06]], thermo: [[0.16, 0.25, 0.2], [0.072, 0.17, -0.06]],
      stand: [[0.45, 0.45, 0.65], [0.05, 0.2, -0.2]], stir: [[0.18, 0.26, 0.2], [0.09, 0.1, -0.06]], beaker: [[0.45, 0.28, 0.45], [0.28, 0.08, -0.04]],
      pour: [[0.42, 0.34, 0.62], [0.17, 0.13, -0.05]], sw: [[0.42, 0.42, 0.62], [0.2, 0.1, 0.0]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A hot body loses heat to its surroundings at a rate proportional to the difference between its temperature and the room temperature, as long as the difference is not too large.',
      formula: 'dT/dt = −k (T − Ts)', formulaNote: 'so T − Ts = (T₀ − Ts) e^(−kt) and ln(T − Ts) = ln(T₀ − Ts) − k t',
      more: ['A graph of T against t is the cooling curve: steep at first, flatter later. A graph of ln(T − Ts) against t is a straight line; its slope is −k.'],
      precautions: 'Read the room temperature before pouring. Keep the bulb fully in the liquid and clear of the copper. Stir gently. Keep the calorimeter away from draughts and the window. Read the thermometer with your eye level with the mercury.' },
    book: { title: 'Expt. — Newton\'s Law of Cooling', lines: bookLines,
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 't (s)', get: function (r) { return String(r.t); } },
        { label: 'T (°C)', get: function (r) { return r.T.toFixed(1); } }, { label: 'T − Ts', get: function (r) { return (r.T - (st.Ts === null ? p.Ts : st.Ts)).toFixed(1); } },
        { label: 'ln(T − Ts)', get: function (r) { var d = r.T - (st.Ts === null ? p.Ts : st.Ts); return d > 0 ? Math.log(d).toFixed(3) : '—'; } }] },
    graph: { x: function (r) { return r.t; }, y: function (r) { return r.T; }, xlabel: 't (s)', ylabel: 'T (°C)', x0: 0, y0: Math.max(0, Math.floor(p.Ts / 5) * 5 - 5),
      line: function () { var f = fit(S.rows); return f ? function (x) { return f.Ts + f.A * Math.exp(-f.k * x); } : null; } },
    result: function (rows) { var f = fit(rows); if (!f) return null;
      return { label: 'k', value: f.k, unit: '1/s', digits: 4, truth: p.k, note: 'From the slope of ln(T − Ts) against t (Ts = ' + f.Ts.toFixed(1) + ' °C).' }; },
    tol: 0.03,
    chips: ['Why does it cool fast at first?', 'Why plot ln(T − Ts)?', 'Why the insulating stand?', 'Check my readings', 'Why is my k different?'],
    viva: [['Why is the calorimeter made of thin copper?', ['Copper conducts well, so the vessel and water share one temperature', 'Copper does not lose heat', 'It is cheap'], 0, 'Good conduction keeps the water and the vessel at the same temperature.'],
      ['What does the slope of ln(T − Ts) against t give?', ['−k', 'Ts', 'T₀'], 0, 'ln(T − Ts) = ln(T₀ − Ts) − kt is a straight line of slope −k.']],
    askState: function () { return { room_temperature_C: st.Ts, water_poured: st.poured, thermometer_C: readT(st.poured ? Tnow() : p.Ts), stopwatch_s: +watch.t.toFixed(1),
      stopwatch_running: watch.on, time_runs_faster_by: st.speed, readings_taken: S.rows.length, liquid: LIQ.name, reading_every_s: EVERY }; },

    steps: [
      { id: 'prepare', title: 'Set up', view: 'cal', render: function (u) {
          u.h2('Room temperature, then hot ' + LIQ.name);
          u.task('1. Read the room temperature', st.roomRead, st.roomRead ? 'Ts = ' + st.Ts.toFixed(1) + ' °C' : 'The thermometer is still in air: it shows the room temperature')
            .add(u.button(st.roomRead ? 'Read' : 'Read the thermometer', readRoom, !st.roomRead, st.roomRead || st.poured));
          u.task('2. Pour the hot ' + LIQ.name + ' into the calorimeter', st.poured, st.poured ? 'Filled to about two thirds' : 'The hand lifts the beaker by its side and pours slowly')
            .add(u.button(st.poured ? 'Poured' : 'Pour the hot ' + LIQ.name, function () { pour(); S.render(); }, st.roomRead && !st.poured, !st.roomRead || st.poured || S.hand.busy));
          u.live(function () { return 'Thermometer: ' + readT(st.shown).toFixed(1) + ' °C'; });
          u.note('Fill the calorimeter only about two thirds, so the ' + LIQ.name + ' does not spill when you stir.');
          u.next('Next: take the readings', st.roomRead && st.poured);
        },
        ok: function () { return st.roomRead && st.poured; },
        auto: function () { readRoom(); return pour(); } },
      { id: 'record', title: 'Readings', view: 'sw', render: function (u) {
          u.h2('Read T every ' + EVERY + ' seconds');
          u.p('Start the stopwatch: the first reading is written at t = 0. Then note the temperature every ' + EVERY + ' s. Keep going for at least ' + (6 * EVERY >= 120 ? Math.round(6 * EVERY / 60) + ' minutes' : 6 * EVERY + ' s') + '.');
          u.row(u.button(watch.on ? 'STOP the stopwatch' : 'START the stopwatch', function () { pressWatch(); }, true, !st.poured || S.hand.busy),
            u.button('Note the reading now', function () { note(); }, false, !watch.on));
          u.row(u.button((st.autoNote ? '✓ ' : '') + 'Note every ' + EVERY + ' s for me', function () { st.autoNote = !st.autoNote; if (st.autoNote && watch.on) st.nextMark = Math.ceil((watch.t + 1) / EVERY) * EVERY; S.render(); }, false, false));
          u.live(function () { return 't = ' + watch.t.toFixed(1) + ' s · T = ' + readT(st.poured ? Tnow() : p.Ts).toFixed(1) + ' °C'; });
          var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
          [1, 5, 10].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
          u.note('A real liquid takes many minutes; the clock can run faster. The stopwatch shows the lab time.');
          u.h3('Observation table'); u.table();
          var span = S.rows.length ? S.rows[S.rows.length - 1].t - S.rows[0].t : 0;
          u.next('Next: plot the cooling curve', S.rows.length >= 6 && span >= SPAN);
          if (S.rows.length < 6 || span < SPAN) u.p(S.rows.length + ' readings so far. Take at least 6, over at least ' + (SPAN % 60 === 0 ? SPAN / 60 + ' minute' + (SPAN === 60 ? '' : 's') : SPAN + ' s') + '.');
        },
        ok: function () { var span = S.rows.length ? S.rows[S.rows.length - 1].t - S.rows[0].t : 0; return S.rows.length >= 6 && span >= SPAN; },
        auto: function () {
          return pressWatch().then(function () {
            for (var i = 1; i <= 8; i++) { S.advance(400, function () { return watch.t >= EVERY * i; }); note(true); }
            return pressWatch(); }); } },
    ],

    tick: function (dt) {
      var sdt = dt * st.speed;
      if (st.poured) { K.step(sim, p, sdt); if (watch.on) watch.t += dt * (st.speed - 1); }
      var target = st.poured ? Tnow() : p.Ts; st.shown += (target - st.shown) * Math.min(1, dt * 4); thermo.set(st.shown);
      if (st.autoNote && watch.on && watch.t >= st.nextMark) { st.nextMark += EVERY; note(true); }
      // steam
      var hot = st.poured ? Math.max(0, Math.min(1, (Tnow() - 45) / 40)) : 0, now = (S._steamT = (S._steamT || 0) + dt);
      wisps.forEach(function (w) { var ph = (now * 0.25 + w.userData.ph) % 1; w.position.set(CX + Math.sin(ph * 6 + w.userData.ph * 9) * 0.012, CAL_Y + CAL_H + 0.01 + ph * 0.12, CZ + 0.005);
        w.quaternion.copy(S.camera.quaternion); w.scale.setScalar(0.6 + ph * 1.4); w.material.opacity = hot * 0.32 * Math.sin(ph * Math.PI); });
      hudT.set(readT(st.shown).toFixed(1) + ' °C'); hudt.set(watch.t.toFixed(1) + ' s'); hudN.set(String(S.rows.length));
    },
  };
});
