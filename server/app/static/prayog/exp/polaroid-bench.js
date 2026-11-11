/* Prayogshala studio module: POLARISATION WITH TWO POLAROIDS (NCERT Class XII, Section B activity).
   A lamp in a metal housing on an optical bench, a fixed polaroid (the polariser), a second polaroid in a graduated
   mount that the hand turns (the analyser), and a photocell with a digital light meter. The reading comes from this
   lab's kernel (packs/elec11.js: Malus's law with the real transmittances of the two films and the small leak no
   polaroid is free of) - the same code the server checks against the textbook formula. */
HoolaStudio.define('polaroid-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.polaroid;
  var p = HK.paramsFor('polaroid', S.lab.params);
  var DEG = Math.PI / 180, R2D = 180 / Math.PI;
  var st = { traced: false, lamp: false, th: 0 };      // th in degrees, as the analyser's scale reads

  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function norm(d) { var v = d % 360; return v < 0 ? v + 360 : v; }

  // ---------------------------------------------------------------- bench, lamp housing
  var BZ = -0.24, AY = 0.11;
  var bench = S.opticalBench({ len: 1.0, x0: -0.5, z: BZ });
  function upright(x, h) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, BZ);
    var sad = S.rounded(0.034, 0.03, 0.06, 0.004, M.alu); sad.rotation.x = -Math.PI / 2; sad.position.y = 0.045; g.add(sad);
    var post = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, h, 18), M.chrome); post.position.y = 0.045 + h / 2; g.add(post);
    var kn = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.008, 12), M.black); kn.rotation.x = Math.PI / 2; kn.position.set(0, 0.045, 0.034); g.add(kn);
    S.contact(0.1, 0.1, x, BZ, 0.45);
    return g;
  }
  var lampU = upright(-0.4, 0.05);
  var house = S.mesh(new T.CylinderGeometry(0.035, 0.035, 0.075, 28), new T.MeshStandardMaterial({ color: 0x3f4349, roughness: 0.5, metalness: 0.4 }));
  house.rotation.z = Math.PI / 2; house.position.y = AY; lampU.add(house);
  var cap = S.mesh(new T.CylinderGeometry(0.035, 0.035, 0.004, 28), M.blackPlastic); cap.rotation.z = Math.PI / 2; cap.position.set(-0.039, AY, 0); lampU.add(cap);
  var winM = new T.MeshBasicMaterial({ color: 0x6a6a6a });
  var win = new T.Mesh(new T.CircleGeometry(0.016, 26), winM); win.rotation.y = Math.PI / 2; win.position.set(0.0385, AY, 0); lampU.add(win);
  var glow = new T.PointLight(0xffe9b0, 0, 0.9); glow.position.set(0.05, AY, 0); lampU.add(glow);
  var lsw = S.mesh(new T.BoxGeometry(0.014, 0.007, 0.012), M.bakelite); lsw.position.set(0, AY + 0.038, 0); lampU.add(lsw);
  var lampTag = S.label('LAMP', { w: 0.03, ratio: 0.3, color: '#2b2f36' }); lampTag.rotation.x = -Math.PI / 2;
  lampTag.position.set(-0.4, 0.0012, BZ + 0.05); S.scene.add(lampTag);

  // ---------------------------------------------------------------- the two polaroids
  function film(parent, tint) {
    var ring = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.01, 34, 1, true), new T.MeshStandardMaterial({ color: 0x24262b, roughness: 0.5 }));
    ring.rotation.z = Math.PI / 2; ring.position.y = AY; parent.add(ring);
    var disc = new T.Mesh(new T.CircleGeometry(0.027, 34), new T.MeshPhysicalMaterial({ color: tint, roughness: 0.25, transmission: 0.55, thickness: 0.002, transparent: true, opacity: 0.85 }));
    disc.rotation.y = Math.PI / 2; disc.position.y = AY; parent.add(disc);
    return disc;
  }
  var polU = upright(-0.16, 0.05);
  film(polU, 0x5b5f6b);
  var pMark = S.mesh(new T.BoxGeometry(0.002, 0.05, 0.0014), new T.MeshBasicMaterial({ color: 0xf2f2f2 })); pMark.position.set(0.006, AY, 0); polU.add(pMark);
  var pTag = S.label('POLARISER  (fixed)', { w: 0.065, ratio: 0.14, color: '#2b2f36' }); pTag.rotation.x = -Math.PI / 2;
  pTag.position.set(-0.16, 0.0012, BZ + 0.055); S.scene.add(pTag);

  var anaU = upright(0.06, 0.05);
  var rim = new T.Group(); rim.position.y = AY; anaU.add(rim);
  var dial = S.canvasTex(2048, 128, function (c, w, h) {
    c.fillStyle = '#1d1f24'; c.fillRect(0, 0, w, h);
    for (var d = 0; d < 360; d += 5) { var x = w * (d / 360), big = d % 30 === 0;
      c.fillStyle = '#f0ece0'; c.fillRect(x - (big ? 2 : 1), 0, big ? 4 : 2, big ? 46 : d % 15 === 0 ? 32 : 20);
      if (big) { c.font = '700 34px "Public Sans", sans-serif'; c.textAlign = 'center'; c.fillText(String(d), x, 90); } }
  });
  var rimM = S.mesh(new T.CylinderGeometry(0.034, 0.034, 0.016, 48, 1, true), new T.MeshStandardMaterial({ map: dial, roughness: 0.5 }));
  rimM.rotation.z = Math.PI / 2; rim.add(rimM);
  var knurlM = S.mesh(new T.CylinderGeometry(0.0345, 0.0345, 0.004, 48), M.blackPlastic); knurlM.rotation.z = Math.PI / 2; knurlM.position.x = 0.01; rim.add(knurlM);
  film(anaU, 0x5b5f6b);
  var index = S.mesh(new T.ConeGeometry(0.003, 0.008, 14), M.red); index.position.set(0, AY + 0.04, 0); index.rotation.x = Math.PI; anaU.add(index);
  var aTag = S.label('ANALYSER  (turns)', { w: 0.065, ratio: 0.14, color: '#2b2f36' }); aTag.rotation.x = -Math.PI / 2;
  aTag.position.set(0.06, 0.0012, BZ + 0.055); S.scene.add(aTag);
  function placeAna(d) { rim.rotation.x = -d * DEG; }
  placeAna(0);

  // ---------------------------------------------------------------- photocell and the light meter
  var cellU = upright(0.3, 0.05);
  var ccase = S.rounded(0.012, 0.05, 0.05, 0.004, M.bakelite); ccase.position.set(0.004, AY, 0); cellU.add(ccase);
  var cface = new T.Mesh(new T.CircleGeometry(0.018, 26), new T.MeshStandardMaterial({ color: 0x2b3a4a, roughness: 0.3, metalness: 0.5 }));
  cface.rotation.y = -Math.PI / 2; cface.position.set(-0.003, AY, 0); cellU.add(cface);
  var cTag = S.label('PHOTOCELL', { w: 0.05, ratio: 0.18, color: '#2b2f36' }); cTag.rotation.x = -Math.PI / 2;
  cTag.position.set(0.3, 0.0012, BZ + 0.05); S.scene.add(cTag);

  var meter = (function () {
    var g = new T.Group(); S.scene.add(g); g.position.set(0.3, 0, 0.0); g.rotation.y = -0.2;
    var W = 0.12, D = 0.15, H = 0.034;
    var body = S.rounded(W, D, H, 0.008, new T.MeshStandardMaterial({ color: 0x2f3b4a, roughness: 0.5 }));
    body.rotation.x = -Math.PI / 2; body.position.y = H / 2; g.add(body);
    var lcd = S.liveTex(512, 220), last = '';
    var scr = new T.Mesh(new T.PlaneGeometry(W - 0.026, 0.034), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
    scr.rotation.x = -Math.PI / 2; scr.position.set(0, H + 0.0025, -D / 2 + 0.032); g.add(scr);
    var bez = S.mesh(new T.BoxGeometry(W - 0.02, 0.003, 0.04), M.grey); bez.position.set(0, H + 0.0015, -D / 2 + 0.032); g.add(bez);
    var kn = S.mesh(new T.CylinderGeometry(0.012, 0.013, 0.008, 24), M.blackPlastic); kn.position.set(-0.025, H + 0.004, 0.02); g.add(kn);
    var lb = S.label('LIGHT METER  ·  lux', { w: 0.07, ratio: 0.14, color: '#e6e7ea' }); lb.rotation.x = -Math.PI / 2;
    lb.position.set(0.012, H + 0.0022, 0.03); g.add(lb);
    S.contact(W + 0.06, D + 0.06, 0.3, 0.0, 0.5);
    return { group: g, top: wpt(g, 0, H + 0.02, 0),
      show: function (txt) { if (txt === last) return; last = txt;
        lcd.draw(function (c) { var gr = c.createLinearGradient(0, 0, 0, 220); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
          c.fillStyle = gr; c.fillRect(0, 0, 512, 220);
          c.font = '700 110px "JetBrains Mono", monospace'; c.textAlign = 'right'; c.fillStyle = 'rgba(0,0,0,.07)'; c.fillText('8888', 420, 134);
          c.fillStyle = '#1b2116'; c.fillText(txt, 420, 134);
          c.font = '600 40px "Public Sans", sans-serif'; c.textAlign = 'left'; c.fillText('lux', 24, 198); }); } };
  })();
  function lead(a, b, color, via) {
    var pts = [[a.x, a.y, a.z], [a.x, a.y + 0.02, a.z]];
    (via || []).forEach(function (v) { pts.push([v[0], 0.005, v[1]]); });
    pts.push([b.x, b.y + 0.02, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }
  lead(new T.Vector3(0.312, AY - 0.02, BZ), meter.top, 'red', [[0.36, -0.14]]);
  lead(new T.Vector3(0.308, AY - 0.024, BZ + 0.004), meter.top, 'black', [[0.26, -0.12]]);

  // ---------------------------------------------------------------- physics
  function view(over) { var q = HK.assign(p, over || {}); return KN.view(KN.init(q, q), q, q); }
  function lux(d) { return st.lamp ? view({ theta: (d === undefined ? st.th : d) * DEG }).inten : 0; }
  function readLux() { return Math.round(lux()); }
  function filmTint() {                                 // the analyser looks dark when its axis crosses the polariser's
    var f = st.lamp ? lux() / Math.max(view({ theta: p.theta0 }).inten, 1e-9) : 0;
    return 0.1 + 0.9 * f;
  }
  var hudA = S.hudCard('Analyser angle'), hudB = S.hudCard('Light meter'), hudC = S.hudCard('Readings');

  // ---------------------------------------------------------------- human actions
  function trace() {
    st.traced = true; S.focus('bench');
    S.say('The lamp, the fixed polariser, the analyser in its graduated mount and the photocell stand in one line. The meter reads the light that gets through both polaroids.');
    S.render();
  }
  function setLamp(on) {
    if (busy()) return Promise.resolve();
    if (on === st.lamp) return Promise.resolve();
    return S.hand.tap(lsw, 'top').then(function () {
      st.lamp = on;
      winM.color.setHex(on ? 0xfff3cf : 0x6a6a6a); glow.intensity = on ? 0.8 : 0;
      S.click(1000, 0.05); S.say(on ? 'The lamp is on. Its light is unpolarised until it reaches the first polaroid.' : 'Lamp off.');
      S.render();
    });
  }
  function turnTo(d) {
    if (busy()) return Promise.resolve(false);
    d = norm(Math.round(d));
    var d0 = st.th, step = ((d - d0 + 540) % 360) - 180;          // turn the short way round
    if (Math.abs(step) < 1e-9) return Promise.resolve(true);
    var at = wpt(anaU, 0, AY + 0.036, 0.0);
    return S.hand.pinchMove(at, function () { return at; }, function (k) {
      st.th = norm(d0 + step * k); placeAna(st.th); S.hand.group.rotation.z = step * k * DEG * 0.4; },
      { mode: 'top', ms: 420 + 420 * Math.abs(step) / 180, reachMs: 600 })
      .then(function () { st.th = d; placeAna(d); S.hand.group.rotation.z = 0; S.click(1300, 0.02, 0.05); S.render(); return true; });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.lamp) { S.say('Switch the lamp on first.'); return false; }
    if (S.rows.some(function (r) { return r.th === st.th; })) { S.say('You already have a reading at ' + st.th + ' degrees.'); return false; }
    S.addRow({ th: st.th, I: readLux() });
    S.say('Written in your record book: ' + st.th + '°, ' + readLux() + ' lux.');
    return true;
  }

  // ---------------------------------------------------------------- result: the angle of the polariser's own axis
  function axisFrom(rows) {
    var sn = 0, cs = 0;
    rows.forEach(function (r) { sn += r.I * Math.sin(2 * r.th * DEG); cs += r.I * Math.cos(2 * r.th * DEG); });
    if (!sn && !cs) return NaN;
    var a = 0.5 * Math.atan2(sn, cs) * R2D;             // I = A + B cos 2(th - th0): the phase of the second harmonic
    return norm(a) % 180;
  }
  function result(rows) {
    if (rows.length < 8) return null;
    var a = axisFrom(rows);
    if (!isFinite(a)) return null;
    var mx = Math.max.apply(null, rows.map(function (r) { return r.I; })), mn = Math.min.apply(null, rows.map(function (r) { return r.I; }));
    return { label: 'Polariser axis on the analyser\'s scale', value: a, unit: '°', digits: 1, truth: norm(p.theta0 * R2D) % 180,
      note: 'From the whole set of readings: the light follows A + B cos 2(θ − θ₀), and θ₀ is where it is brightest. Brightest ' + Math.round(mx) + ' lux, darkest ' + Math.round(mn) + ' lux, so the ratio is about ' + Math.round(mx / Math.max(mn, 1)) + ' to 1.' };
  }

  S.addApparatus('bench', bench, 'Optical bench', 'Carries the lamp, the two polaroids and the photocell in one straight line.');
  S.addApparatus('lamp', lampU, 'Lamp in its housing', 'An ordinary filament lamp. Its light vibrates in every direction across the beam: it is unpolarised.');
  S.addApparatus('pol', polU, 'Polariser (fixed)', 'The first polaroid. It passes only the vibrations along its own axis, so the light beyond it is plane polarised and half as bright.');
  S.addApparatus('ana', anaU, 'Analyser (turns on a 360° scale)', 'The second polaroid. The index mark on its mount reads the angle its axis has been turned to.');
  S.addApparatus('cell', cellU, 'Photocell', 'Turns the light that reaches it into a current the meter reads.');
  S.addApparatus('meter', meter.group, 'Digital light meter', 'Reads the light falling on the photocell, in lux, to the nearest lux.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  return {
    camera: { pos: [0.0, 0.78, 0.84], look: [-0.02, 0.09, -0.2] },
    views: { bench: [[0.0, 0.74, 0.8], [-0.02, 0.09, -0.2]], ana: [[0.06, 0.2, 0.02], [0.06, 0.11, -0.24]],
      pol: [[-0.16, 0.2, 0.02], [-0.16, 0.11, -0.24]], lamp: [[-0.4, 0.22, 0.0], [-0.4, 0.11, -0.24]],
      cell: [[0.3, 0.2, 0.02], [0.3, 0.11, -0.24]], meter: [[0.3, 0.26, 0.28], [0.3, 0.03, 0.0]],
      book: [[-0.5, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'Light from a lamp vibrates in every direction across the beam. The first polaroid passes only the vibrations along its own axis, so the light beyond it is plane polarised and half as bright. The second polaroid passes the component of that along ITS axis.',
      formula: 'I = I₀ cos² θ',
      formulaNote: 'θ is the angle between the two axes · this is Malus\'s law',
      more: ['Turning the analyser through a whole circle gives two maxima, where the axes are parallel, and two minima a quarter turn away, where they are crossed.',
        'The reading never falls quite to zero: real polaroid film passes a little of the wrong vibration, and the films absorb some of the right one as well, which is why the brightest reading is well under half the lamp\'s light.',
        'The analyser\'s scale has no reason to read zero when the axes are parallel, so the angle at which the light is brightest is itself something the experiment finds.'],
      precautions: 'Hold the polaroids by their mounts, keep the lamp at the same brightness all through, and turn the analyser in one direction only, so that any slack in the mount does not change the readings.' },
    book: { title: 'Expt. — Polarisation with two polaroids', at: [-0.5, 0.1, 0.1],
      lines: ['Aim: to study the light passed by two polaroids', 'as one of them is turned, and to verify Malus\'s law.',
        'Lamp, polariser, analyser on a 360° scale,', 'photocell and a digital light meter (1 lux).',
        'I = I₀ cos² (θ − θ₀)'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'θ (°)', get: function (r) { return r.th; } },
        { label: 'I (lux)', get: function (r) { return r.I; } },
        { label: 'cos² θ', get: function (r) { return Math.pow(Math.cos(r.th * DEG), 2).toFixed(3); } }] },
    graph: { x: function (r) { return r.th; }, y: function (r) { return r.I; }, xlabel: 'Analyser angle θ (°)', ylabel: 'Light (lux)', x0: 0, y0: 0,
      line: function (pts) {
        var sn = 0, cs = 0, sm = 0;
        pts.forEach(function (q) { sn += q[1] * Math.sin(2 * q[0] * DEG); cs += q[1] * Math.cos(2 * q[0] * DEG); sm += q[1]; });
        var A = sm / pts.length, B = 2 * Math.sqrt(sn * sn + cs * cs) / pts.length, ph = Math.atan2(sn, cs);
        return function (x) { return A + B * Math.cos(2 * x * DEG - ph); };
      } },
    result: result,
    tol: 0.02,
    resultNote: 'The curve is a cosine squared: brightest when the two axes are parallel, almost dark a quarter turn away, and brightest again half a turn on.',
    chips: ['Why does half the light go in the first polaroid?', 'What is Malus\'s law?', 'Check my readings', 'Why is the minimum not exactly zero?'],
    viva: [['When two polaroids are crossed, the light that gets through is', ['Almost nothing', 'Half', 'Unchanged'], 0, 'cos² 90° = 0.'],
      ['Unpolarised light passing through one polaroid loses', ['Half its intensity', 'All of it', 'None of it'], 0,
        'Averaged over every direction, cos² is one half.'],
      ['In one whole turn of the analyser the light is brightest', ['Twice', 'Once', 'Four times'], 0,
        'cos² θ has a period of 180 degrees.']],
    askState: function () {
      return { experiment: 'polarisation of light with two polaroids', lamp_on: st.lamp,
        analyser_angle_deg: st.th, light_meter_lux: readLux(), readings_taken: S.rows.length,
        note: 'the angle at which the two axes are parallel is what the experiment finds' };
    },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Line the bench up and switch the lamp on');
          u.p('Lamp, polariser, analyser and photocell, all at the same height and in one straight line.');
          u.task('1. Trace the set-up', st.traced, st.traced ? 'Lamp, polariser, analyser, photocell' : 'Follow the light from the lamp')
            .add(u.button(st.traced ? 'Traced' : 'Trace the set-up', trace, !st.traced, st.traced));
          u.task('2. Switch the lamp on', st.lamp, st.lamp ? 'Lamp lit; the meter is reading' : 'The lamp is off')
            .add(u.button(st.lamp ? 'Lamp is on' : 'Switch the lamp on', function () { S.focus('lamp'); setLamp(true); }, !st.lamp, st.lamp || S.hand.busy));
          u.row(u.button('Turn the analyser to 0°', function () { turnTo(0); }, false, S.hand.busy || st.th === 0));
          u.live(function () { return st.lamp ? 'Analyser at ' + st.th + '°  ·  meter ' + readLux() + ' lux' : 'Lamp off'; });
          u.note('The lamp must stay at the same brightness for every reading, or the comparison means nothing.');
          u.next('Next: turn the analyser', st.traced && st.lamp);
        },
        ok: function () { return st.traced && st.lamp; },
        auto: function () { trace(); return setLamp(true).then(function () { return turnTo(0); }); } },
      { id: 'read', title: 'Readings', view: 'ana', render: function (u) {
          u.h2('Turn the analyser and read the meter');
          u.p('Take the analyser round a whole circle in steps of 15°, and record the meter at each step.');
          var tg = { v: norm(st.th + 15) };
          u.slider('Turn the analyser to', 0, 345, 15, function () { return tg.v; }, function (v) { tg.v = v; }, '°', 0);
          u.row(u.button('Turn the analyser', function () { turnTo(tg.v); }, true, S.hand.busy),
            u.button('Record this reading', function () { record(); }, false, S.hand.busy));
          u.row(u.button('− 15°', function () { turnTo(st.th - 15); }, false, S.hand.busy),
            u.button('+ 15°', function () { turnTo(st.th + 15); }, false, S.hand.busy));
          u.live(function () { return 'Analyser at ' + st.th + '°  ·  meter ' + readLux() + ' lux'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 12) u.p(S.rows.length + ' of at least 12 readings recorded (a whole circle is 24).');
          u.next('Next: the result', S.rows.length >= 12);
        },
        ok: function () { return S.rows.length >= 12; },
        auto: function () {
          var list = [];
          for (var d = 0; d < 360; d += 15) list.push(d);
          return list.reduce(function (pr, d) { return pr.then(function () { return turnTo(d); }).then(function () { record(); }); }, Promise.resolve());
        } },
    ],
    tick: function () {
      meter.show(st.lamp ? String(readLux()) : '----');
      var f = filmTint();
      hudA.set(st.th + '°');
      hudB.set(st.lamp ? readLux() + ' lx' : '—');
      hudC.set(S.rows.length + ' of 24');
      if (glow) glow.intensity = st.lamp ? 0.8 : 0;
      cface.material.color.setRGB(0.17 + 0.5 * f, 0.23 + 0.5 * f, 0.29 + 0.45 * f);
    },
  };
});
