/* Prayogshala studio module: ultrasonic interferometer - velocity of ultrasound in a liquid (B.Sc. Waves / Engineering Physics).
   Physics: the hw_usonic kernel (packs/heat_wave_ug) - the same numbers the server checks: the crystal current
   I(x) = Ib + Ia exp(-alpha x) cos²(2 pi (x - x0) / lambda) peaks every lambda / 2 of reflector travel. v = 2 f d / n,
   beta = 1 / (rho v²). The hidden knob v (the liquid) is what the student finds. */
HoolaStudio.define('ultrasonic-interferometer', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.hw_usonic;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('hw_usonic');
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var LIQ = /kerosene/i.test(SAMPLE) ? { name: 'kerosene', col: 0xe6d37a, op: 0.75, tag: 'KEROSENE' } : /glycer/i.test(SAMPLE) ? { name: 'glycerol', col: 0xe9eeea, op: 0.8, tag: 'GLYCEROL' } : { name: 'water', col: 0x8fc2d6, op: 0.8, tag: 'DISTILLED WATER' };
  var LAM = p.v / p.f, HALF = LAM / 2, NEED = 8;
  function mm3(v) { return Math.round(v * 1e6) / 1e3; }          // micrometer reading in mm, to 0.001 mm
  var st = { filled: false, on: false, x: 0, n: 0, shown: 0, clock: 0, lastPeak: null };
  function Inow() { return K.current(p, st.x); }
  function peakIdx(x) { return Math.round((x - p.x0) / HALF); }
  function atPeak(x) { var j = peakIdx(x); return j >= 0 && Math.abs(x - (p.x0 + j * HALF)) <= 0.00001; }

  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'pinch', 320); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }
  // ---------- the measuring cell: steel base with the quartz crystal, a glass wall, the liquid, the reflector on a spindle, a micrometer head
  var CX = -0.12, CZ = -0.2, CR = 0.032, CH = 0.07;
  var cell = new T.Group(); S.scene.add(cell);
  var cbase = S.mesh(new T.CylinderGeometry(CR + 0.008, CR + 0.01, 0.022, 48), M.steel); cbase.position.set(CX, 0.011, CZ); cell.add(cbase);
  var crystal = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.002, 36), M.chrome); crystal.position.set(CX, 0.023, CZ); cell.add(crystal);
  var wall = S.mesh(new T.CylinderGeometry(CR, CR, CH, 48, 1, true), M.glass, false); wall.position.set(CX, 0.022 + CH / 2, CZ); cell.add(wall);
  var liquidM = new T.MeshStandardMaterial({ color: LIQ.col, roughness: 0.05, metalness: 0.05, transparent: true, opacity: LIQ.op });
  var liq = S.mesh(new T.CylinderGeometry(CR - 0.001, CR - 0.001, 1, 40), liquidM, false); cell.add(liq); liq.visible = false;
  function setLiquid(f) { var hh = Math.max(0.0005, (CH - 0.012) * f); liq.scale.y = hh; liq.position.set(CX, 0.0245 + hh / 2, CZ); liq.visible = f > 0.01; }
  var topc = S.mesh(new T.CylinderGeometry(CR + 0.004, CR + 0.004, 0.012, 48), M.steel); topc.position.set(CX, 0.022 + CH + 0.006, CZ); cell.add(topc);
  var refl = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.003, 36), M.chrome); cell.add(refl);
  var spindle = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 1, 14), M.steel); cell.add(spindle);
  var mic = new T.Group(); S.scene.add(mic);
  var barrel = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.07, 28), M.alu); barrel.position.set(CX, 0.022 + CH + 0.012 + 0.035, CZ); mic.add(barrel);
  var thimble = S.mesh(new T.CylinderGeometry(0.0155, 0.0155, 0.032, 32), M.black); thimble.position.set(CX, 0.022 + CH + 0.012 + 0.086, CZ); mic.add(thimble);
  var ratchet = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.014, 24), M.chrome); ratchet.position.set(CX, 0.022 + CH + 0.012 + 0.109, CZ); mic.add(ratchet);
  var dTex = S.liveTex(256, 80), dMesh = new T.Mesh(new T.PlaneGeometry(0.058, 0.0181), new T.MeshBasicMaterial({ map: dTex })); dMesh.position.set(CX, 0.022 + CH + 0.012 + 0.058, CZ + 0.0125); mic.add(dMesh);
  var dLast = '';
  function drawMic(x) { var txt = (x * 1000).toFixed(3); if (txt === dLast) return; dLast = txt; dTex.draw(function (c, w, h) { c.fillStyle = '#b9c4a7'; c.fillRect(0, 0, w, h); c.fillStyle = '#1b2116'; c.font = '700 44px "JetBrains Mono", monospace'; c.textAlign = 'right'; c.fillText(txt, w - 40, h - 20); c.font = '600 18px sans-serif'; c.fillText('mm', w - 8, h - 22); }); }
  var cl = S.label('2 MHz CELL', { w: 0.05, ratio: 0.15, color: '#223' }); cl.position.set(CX, 0.011, CZ + CR + 0.0105); cell.add(cl);
  S.contact(0.18, 0.18, CX, CZ, 0.55);
  // bottle of the liquid with a funnel
  var BX = -0.36, BZ = -0.2;
  var bottle = new T.Group(); S.scene.add(bottle);
  var bb = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.1, 32), M.glass, false); bb.position.set(0, 0.05, 0); bottle.add(bb);
  var bw = S.mesh(new T.CylinderGeometry(0.027, 0.027, 0.075, 32), new T.MeshStandardMaterial({ color: LIQ.col, roughness: 0.05, metalness: 0.05 }), false); bw.position.set(0, 0.04, 0); bottle.add(bw);
  var bn = S.mesh(new T.CylinderGeometry(0.012, 0.02, 0.03, 24), M.glass, false); bn.position.set(0, 0.115, 0); bottle.add(bn);
  var bcap = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.012, 24), M.red); bcap.position.set(0, 0.136, 0); bottle.add(bcap);
  var blb = S.label(LIQ.tag, { w: 0.05, ratio: 0.22, color: '#222', bg: '#f4f1e6' }); blb.position.set(0, 0.05, 0.0305); bottle.add(blb);
  bottle.position.set(BX, 0, BZ); S.contact(0.1, 0.1, BX, BZ, 0.5);
  var BOT_HOME = new T.Vector3(BX, 0, BZ);
  // generator with a current meter
  var GX = 0.3, GZ = -0.22;
  var gen = new T.Group(); S.scene.add(gen);
  var gb = S.rounded(0.3, 0.2, 0.14, 0.01, new T.MeshStandardMaterial({ color: 0xb9bec4, roughness: 0.45, metalness: 0.3 })); gb.rotation.x = -Math.PI / 2; gb.position.set(GX, 0.07, GZ); gen.add(gb);
  var gl = S.label('HIGH-FREQUENCY GENERATOR  2 MHz', { w: 0.24, ratio: 0.09, color: '#e8e8e8', bg: '#2b2f36' }); gl.position.set(GX, 0.12, GZ + 0.1005); gen.add(gl);
  var gsw = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.012, 20), M.red); gsw.rotation.x = Math.PI / 2; gsw.position.set(GX + 0.1, 0.05, GZ + 0.101); gen.add(gsw);
  var gmeter = S.meter({ min: 0, max: 100, unit: 'µA', symbol: 'µA', caption: 'CRYSTAL CURRENT', ticks: 10, pos: [GX - 0.08, 0.14, GZ + 0.0] });
  var cur = S.liveTex(256, 80), cm = new T.Mesh(new T.PlaneGeometry(0.07, 0.022), new T.MeshBasicMaterial({ map: cur })); cm.position.set(GX + 0.02, 0.07, GZ + 0.1005); gen.add(cm);
  var cLast = '';
  function drawCur(txt) { if (txt === cLast) return; cLast = txt; cur.draw(function (c, w, h) { c.fillStyle = '#b9c4a7'; c.fillRect(0, 0, w, h); c.fillStyle = '#1b2116'; c.font = '700 44px "JetBrains Mono", monospace'; c.textAlign = 'right'; c.fillText(txt, w - 10, h - 20); }); }
  S.contact(0.34, 0.2, GX, GZ, 0.5);
  var cable = S.wire([[CX + 0.034, 0.02, CZ], [0.0, 0.05, -0.18], [GX - 0.18, 0.06, GZ + 0.05], [GX - 0.15, 0.08, GZ + 0.09]], 'black');
  var watch = S.stopwatch([0.3, 0.035, 0.17], [-1.15, 0, -0.2]);
  var hudX = S.hudCard('Micrometer'), hudI = S.hudCard('Current'), hudN = S.hudCard('Maxima noted');

  S.addApparatus('cell', cell, 'Measuring cell', 'A steel cell with a 2 MHz quartz crystal at the bottom. The liquid fills the space between the crystal and a movable reflector.');
  S.addApparatus('mic', mic, 'Digital micrometer head', 'Moves the reflector up through the liquid. Reads to 0.001 mm.');
  S.addApparatus('bottle', bottle, 'Bottle of ' + LIQ.name, 'The liquid to test. Pour it in until the reflector is covered.');
  S.addApparatus('gen', gen, 'High-frequency generator', 'Drives the crystal at 2 MHz and measures the crystal current, which peaks when the standing wave reinforces the vibration.');
  S.addApparatus('meter', gmeter, 'Current meter', 'The needle rises and falls as the reflector moves; each peak marks a half wavelength.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Not needed here.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var bookLines = ['Aim: to find the velocity of ultrasound in ' + LIQ.name + ' and its compressibility.', 'f = ' + (p.f / 1e6).toFixed(3) + ' MHz,  ρ = ' + p.rho.toFixed(1) + ' kg/m³ (tables)', 'v = 2 f d / n,   β = 1 / (ρ v²)'];

  // ---------- actions
  function pourLiquid() {
    if (S.hand.busy || st.filled) return Promise.resolve();
    var a = BOT_HOME.clone(), b = new T.Vector3(CX - 0.05, 0.19, CZ), TH = 1.6;
    return carry(new T.Vector3(a.x + 0.034, 0.07, a.z), [
      { ms: 1000, fn: function (k) { var q = a.clone().lerp(new T.Vector3(b.x, 0.12, b.z), k); return new T.Vector3(q.x + 0.034, q.y + 0.05, q.z); }, onK: function (k) { var q = a.clone().lerp(new T.Vector3(b.x, 0.12, b.z), k); bottle.position.copy(q); } },
      { ms: 1800, fn: function (k) { return new T.Vector3(b.x + 0.034, 0.17 + 0.0, b.z); }, onK: function (k) { bottle.position.set(b.x, 0.12 + 0.0, b.z); bottle.rotation.z = TH * k; setLiquid(k); } },
      { ms: 1000, fn: function (k) { return new T.Vector3(b.x + 0.034 + (a.x - b.x) * k, 0.17 - 0.1 * k, b.z); }, onK: function (k) { bottle.rotation.z = TH * (1 - k); bottle.position.set(b.x + (a.x - b.x) * k, 0.12 - 0.12 * k, b.z); } }], 'grip')
      .then(function () { bottle.rotation.z = 0; bottle.position.copy(BOT_HOME); setLiquid(1); st.filled = true; S.say('The cell is full of ' + LIQ.name + ' and the reflector is covered.'); S.render(); });
  }
  function genOn() { if (S.hand.busy || st.on) return Promise.resolve(); return S.hand.tap(gsw).then(function () { S.click(2000); st.on = true; S.say('Generator on at ' + (p.f / 1e6).toFixed(3) + ' MHz. Turn the micrometer slowly and watch the current.'); S.render(); }); }
  function setX(mm) { st.x = Math.max(0, Math.min(0.025, Math.round(mm * 1000) / 1e6)); S.render(); }
  function turn(dmm) { if (S.hand.busy) return; setX(st.x * 1000 + dmm); }
  function nextMax() {                                           // turn up slowly until the current has peaked and fallen, then trim to the top
    if (!st.on) { S.say('Switch the generator on first.'); return; }
    var x = st.x, i, prev = K.current(p, x), up = false, guard = 0;
    for (; guard < 4000; guard++) { x = Math.round((x + 0.00001) * 1e6) / 1e6; var c = K.current(p, x); if (c > prev + 1e-9) up = true; else if (up && c < prev - 1e-9) break; prev = c; }
    var best = x, bc = -1; for (i = -30; i <= 30; i++) { var xx = Math.round((x - 0.00001 * 2 + i * 0.000001) * 1e6) / 1e6; var c2 = K.current(p, xx); if (c2 > bc) { bc = c2; best = xx; } }
    st.x = Math.min(0.025, best); S.render();
  }
  function peakNear() { var j = peakIdx(st.x), pk = p.x0 + j * HALF; return Math.abs(st.x - pk) <= 0.000012 && j >= 0 ? j : null; }
  function record() {
    if (!st.on) { S.say('Switch the generator on first.'); return; }
    var j = peakNear();
    if (j === null) { S.say('The current is not at a maximum here. Turn the micrometer slowly and use the top of the peak.'); return; }
    if (st.lastPeak !== null && j !== st.lastPeak + 1) { S.say(j <= st.lastPeak ? 'You already noted this maximum. Turn on to the next one.' : 'You skipped a maximum. Turn back one peak and note it first.'); return; }
    var n = S.rows.length + 1; S.addRow({ n: n, x: st.x }); st.lastPeak = j; S.say('Maximum no. ' + n + ' at ' + (st.x * 1000).toFixed(3) + ' mm.');
  }
  function vOf(rows) { var r = rows.slice().sort(function (a, b) { return a.n - b.n; }); if (r.length < 2) return null; return 2 * p.f * (r[r.length - 1].x - r[0].x) / (r[r.length - 1].n - r[0].n); }

  return {
    camera: { pos: [0.05, 0.4, 1.05], look: [0.05, 0.1, -0.2] },
    views: { cell: [[-0.12, 0.2, 0.3], [CX, 0.07, CZ]], mic: [[-0.12, 0.3, 0.3], [CX, 0.16, CZ]], bottle: [[-0.3, 0.2, 0.3], [BX, 0.06, BZ]], gen: [[0.25, 0.25, 0.35], [GX, 0.09, GZ]], meter: [[0.25, 0.3, 0.3], [GX - 0.08, 0.15, GZ]],
      sw: [[-0.5, 0.4, 0.5], [-1.1, 0.05, -0.2]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A 2 MHz quartz crystal sends ultrasonic waves up through the liquid to a movable reflector. When the distance between them is a whole number of half wavelengths, a standing wave forms and the crystal current is a maximum.',
      formula: 'v = f λ = 2 f d / n', formulaNote: 'Neighbouring maxima are λ/2 of reflector travel apart, so n maxima span d = n λ / 2. The adiabatic compressibility is β = 1 / (ρ v²).',
      more: ['The current peaks get lower farther up because the liquid absorbs some of the sound. Counting more maxima makes d large, so a reading error of 0.01 mm matters less.'],
      precautions: 'Never switch the generator on with an empty cell. Turn the micrometer slowly and in one direction, to avoid backlash. Note the reading at the very top of each peak. Keep the liquid at a steady temperature.' },
    book: { title: 'Expt. — Ultrasonic interferometer', lines: bookLines,
      columns: [{ label: 'Max no. n', get: function (r) { return String(r.n); } }, { label: 'x (mm)', get: function (r) { return (r.x * 1000).toFixed(3); } },
        { label: 'x − x₁ (mm)', get: function (r) { return ((r.x - (S.rows[0] ? S.rows[0].x : r.x)) * 1000).toFixed(3); } }] },
    graph: { x: function (r) { return r.n; }, y: function (r) { return r.x * 1000; }, xlabel: 'n', ylabel: 'x (mm)', x0: 0, y0: 0,
      line: function () { var rs = S.rows; if (rs.length < 2) return null; var v = vOf(rs), sl = v / (2 * p.f) * 1000, x1 = rs[0].x * 1000 - sl * rs[0].n; return function (x) { return x1 + sl * x; }; } },
    result: function (rows) { var v = vOf(rows); if (v === null) return null; var beta = 1 / (p.rho * v * v);
      return { label: 'v (ultrasound in ' + LIQ.name + ')', value: v, unit: 'm/s', digits: 0, truth: p.v, note: 'λ = ' + (v / p.f * 1000).toFixed(4) + ' mm. Adiabatic compressibility β = 1/(ρ v²) = ' + (beta * 1e10).toFixed(2) + '×10⁻¹⁰ Pa⁻¹ (ρ = ' + p.rho.toFixed(1) + ' kg/m³ from tables).' }; },
    tol: 0.02,
    chips: ['Why does the current peak?', 'Why measure across many maxima?', 'How do I get compressibility?', 'Check my readings', 'Why is my v different?'],
    viva: [['What is the distance between neighbouring maxima of the crystal current?', ['λ/2', 'λ', 'λ/4'], 0, 'The standing wave repeats every half wavelength of reflector travel.'],
      ['The adiabatic compressibility of the liquid is', ['1 / (ρ v²)', 'ρ v²', 'v / ρ'], 0, 'The bulk modulus is ρ v², its reciprocal is the compressibility.']],
    askState: function () { return { liquid: LIQ.name, cell_filled: st.filled, generator_on: st.on, micrometer_mm: +(st.x * 1000).toFixed(3), crystal_current_uA: st.on ? +Inow().toFixed(2) : null, maxima_noted: S.rows.length, frequency_MHz: p.f / 1e6 }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'cell', render: function (u) {
          u.h2('Fill the cell and switch on');
          u.task('1. Fill the cell with ' + LIQ.name, st.filled, st.filled ? 'The reflector is covered' : 'The hand pours from the bottle')
            .add(u.button(st.filled ? 'Filled' : 'Pour in the liquid', function () { pourLiquid(); }, !st.filled, st.filled || S.hand.busy));
          u.task('2. Switch the generator on', st.on, st.on ? (p.f / 1e6).toFixed(3) + ' MHz' : 'The hand presses the switch (the cell must be full)')
            .add(u.button(st.on ? 'On' : 'Switch on', function () { genOn(); }, st.filled && !st.on, st.on || !st.filled || S.hand.busy));
          u.next('Next: find the maxima', st.filled && st.on);
        },
        ok: function () { return st.filled && st.on; },
        auto: function () { return pourLiquid().then(function () { return genOn(); }); } },
      { id: 'scan', title: 'Maxima', view: 'meter', render: function (u) {
          u.h2('Note ' + NEED + ' successive maxima');
          u.p('Turn the micrometer slowly upward. The current rises and falls; at the top of each peak, write the reading. Do not skip a peak.');
          u.slider('Micrometer', 0, 25, 0.01, function () { return st.x * 1000; }, function (v) { setX(v); }, 'mm', 2);
          u.row(u.button('−0.1 mm', function () { turn(-0.1); }, false, false), u.button('−0.01 mm', function () { turn(-0.01); }, false, false), u.button('+0.01 mm', function () { turn(0.01); }, false, false), u.button('+0.1 mm', function () { turn(0.1); }, false, false));
          u.row(u.button('Turn slowly to the next peak', nextMax, false, false), u.button('Write this maximum in the table', record, true, false));
          u.live(function () { var c = Inow(); return 'x = ' + (st.x * 1000).toFixed(3) + ' mm · current ' + c.toFixed(2) + ' µA · ' + (peakNear() !== null ? 'AT A PEAK' : 'between peaks'); });
          u.h3('Observation table'); u.table();
          u.next('Next: work out v', S.rows.length >= NEED);
          if (S.rows.length < NEED) u.p(S.rows.length + ' maximum/maxima so far. Note at least ' + NEED + ' in a row.');
        },
        ok: function () { return S.rows.length >= NEED; },
        auto: function () { for (var i = 0; i < NEED + 1 && S.rows.length < NEED; i++) { nextMax(); record(); } return Promise.resolve(); } },
    ],

    tick: function (dt) {
      st.clock += dt; var c = st.on ? Inow() : 0; st.shown += (c - st.shown) * Math.min(1, dt * 8); gmeter.set(st.shown);
      drawMic(st.x); drawCur(st.on ? c.toFixed(2) + ' µA' : '0.00 µA');
      var yr = 0.0245 + 0.004 + st.x; refl.position.set(CX, yr, CZ); spindle.scale.y = (0.022 + CH + 0.012) - yr + 0.03; spindle.position.set(CX, yr + spindle.scale.y / 2, CZ); thimble.rotation.y = st.x * 1000 / 0.5 * Math.PI * 2;
      hudX.set((st.x * 1000).toFixed(3) + ' mm'); hudI.set(st.on ? c.toFixed(1) + ' µA' : '—'); hudN.set(String(S.rows.length));
    },
  };
});
