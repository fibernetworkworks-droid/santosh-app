/* Prayogshala studio module: GRATING SPECTROMETER (B.Sc. modern physics).
   A spectrometer with a divided circle and vernier, a collimator, a plane transmission grating upright on the
   prism table, a telescope that swings round the circle, and a hydrogen discharge tube behind the slit.
   Physics: the `grating` kernel of packs/modern_ug.js on the lab's own params - the same code the server checks
   against Balmer's formula. The telescope's angle is read to one minute of arc, as on a real circle. */
HoolaStudio.define('grating-spectrometer', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.grating, assign = HK.assign;
  var p = HK.paramsFor('grating', S.lab.params);
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || 'Hydrogen discharge tube';
  var ARCMIN = Math.PI / 180 / 60, D2R = Math.PI / 180, R2D = 180 / Math.PI;
  var ORDER = p.order, NLINES = p.Nl;
  var LINES = [3, 4, 5, 6];
  var NAMES = { 3: 'Hα (red)', 4: 'Hβ (blue-green)', 5: 'Hγ (violet)', 6: 'Hδ (faint violet)' };
  var COLS = { 3: 0xd63a32, 4: 0x3fb5c6, 5: 0x6a5ae0, 6: 0x8d6ad6 };
  var BRIGHT = { 3: 1.0, 4: 0.55, 5: 0.28, 6: 0.14 };
  var st = { lit: false, th: 0, direct: null, done: {}, levelled: false };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function angleOf(n) { var q = assign(p, { nq: n }); return KN.angle(q); }          // radians, 0 if not diffracted
  function lamOf(n) { var q = assign(p, { nq: n }); return KN.wavelength(q); }
  function visible(n) { var s = lamOf(n) * ORDER * NLINES; return s > 0 && s < 1; }
  function readTh() { return Math.round(st.th / ARCMIN) * ARCMIN; }                  // vernier: one minute of arc
  function degMin(rad) { var d = Math.abs(rad) * R2D, dd = Math.floor(d), mm = Math.round((d - dd) * 60);
    if (mm === 60) { dd += 1; mm = 0; } return (rad < 0 ? '−' : '') + dd + '° ' + mm + "'"; }
  function fieldAt(th) {                                 // what the eyepiece shows at this setting
    var out = [], i, n, d;
    for (i = 0; i < LINES.length; i++) {
      n = LINES[i]; if (!visible(n)) continue;
      d = Math.abs(th - angleOf(n));
      if (d < 0.012) out.push({ n: n, I: BRIGHT[n] * Math.exp(-(d / 0.0035) * (d / 0.0035)) });
    }
    if (Math.abs(th) < 0.012) out.push({ n: 0, I: Math.exp(-(th / 0.0035) * (th / 0.0035)) });
    return out;
  }
  function brightest(th) { var f = fieldAt(th), b = null, i;
    for (i = 0; i < f.length; i++) if (!b || f[i].I > b.I) b = f[i]; return b; }

  // ================================================================ spectrometer base and divided circle
  var CX = 0.0, CZ = -0.1;
  var spec = new T.Group(); S.scene.add(spec); spec.position.set(CX, 0, CZ);
  var tri = S.mesh(new T.CylinderGeometry(0.1, 0.11, 0.03, 3), M.iron); tri.position.y = 0.015; spec.add(tri);
  var col = S.mesh(new T.CylinderGeometry(0.022, 0.026, 0.06, 24), M.iron); col.position.y = 0.05; spec.add(col);
  var circTex = S.canvasTex(1400, 1400, function (x, w, h) {
    var cx = w / 2, cy = h / 2, R = w / 2 - 20;
    x.fillStyle = '#c9a227'; x.beginPath(); x.arc(cx, cy, R, 0, Math.PI * 2); x.fill();
    x.fillStyle = '#9c7d1c'; x.beginPath(); x.arc(cx, cy, R * 0.62, 0, Math.PI * 2); x.fill();
    x.strokeStyle = '#1b1b1b'; x.fillStyle = '#1b1b1b'; x.textAlign = 'center';
    for (var i = 0; i < 360 * 2; i++) {
      var a = i * Math.PI / 360, big = i % 20 === 0, mid = i % 10 === 0;
      var r0 = R * (big ? 0.78 : mid ? 0.84 : 0.88);
      x.lineWidth = big ? 3 : 1.4; x.beginPath();
      x.moveTo(cx + Math.cos(a) * R * 0.95, cy + Math.sin(a) * R * 0.95);
      x.lineTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0); x.stroke();
      if (big) { x.font = '700 24px "Public Sans", sans-serif';
        x.fillText(String(i / 2), cx + Math.cos(a) * R * 0.71, cy + Math.sin(a) * R * 0.71 + 8); }
    }
    x.font = '700 30px "Public Sans", sans-serif'; x.fillText('DIVIDED CIRCLE  ·  VERNIER 1′', cx, cy - R * 0.3);
  });
  var circle = new T.Mesh(new T.CylinderGeometry(0.17, 0.17, 0.012, 64),
    [new T.MeshStandardMaterial({ color: 0xb08d1f, roughness: 0.4, metalness: 0.7 }),
      new T.MeshStandardMaterial({ map: circTex, roughness: 0.45, metalness: 0.5 }),
      new T.MeshStandardMaterial({ map: circTex, roughness: 0.45, metalness: 0.5 })]);
  circle.position.y = 0.086; spec.add(circle);
  var levellers = [0, 2.1, 4.2].map(function (a) {
    var k = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.012, 6), M.chrome);
    k.position.set(Math.cos(a) * 0.07, 0.006, Math.sin(a) * 0.07); spec.add(k); return k;
  });

  // collimator (fixed, pointing at the grating from +z)
  var collim = new T.Group(); spec.add(collim); collim.position.set(0, 0.11, 0);
  var ctube = S.mesh(new T.CylinderGeometry(0.021, 0.021, 0.2, 28), new T.MeshStandardMaterial({ color: 0x4a4f57, roughness: 0.42, metalness: 0.5 }));
  ctube.rotation.x = Math.PI / 2; ctube.position.z = 0.13; collim.add(ctube);
  var cring = S.mesh(new T.TorusGeometry(0.022, 0.0025, 8, 28), M.chrome); cring.position.z = 0.04; collim.add(cring);
  var slitH = S.mesh(new T.CylinderGeometry(0.019, 0.019, 0.016, 28), M.bakelite); slitH.rotation.x = Math.PI / 2;
  slitH.position.z = 0.238; collim.add(slitH);
  var slitM = new T.MeshBasicMaterial({ color: 0xffd0e0, transparent: true, opacity: 0 });
  var slit = S.mesh(new T.BoxGeometry(0.0012, 0.02, 0.001), slitM, false, false); slit.position.z = 0.247;
  collim.add(slit);
  var csup = S.mesh(new T.CylinderGeometry(0.007, 0.007, 0.07, 16), M.chrome); csup.position.set(0, -0.05, 0.16);
  collim.add(csup);
  var cbase = S.rounded(0.05, 0.05, 0.012, 0.004, M.iron); cbase.rotation.x = -Math.PI / 2;
  cbase.position.set(0, -0.08, 0.16); collim.add(cbase);

  // telescope on the rotating arm
  var arm = new T.Group(); spec.add(arm); arm.position.set(0, 0.095, 0);
  var armBar = S.mesh(new T.BoxGeometry(0.03, 0.008, 0.2), M.iron); armBar.position.z = -0.08; arm.add(armBar);
  var tele = new T.Group(); arm.add(tele); tele.position.set(0, 0.016, -0.02);
  var ttube = S.mesh(new T.CylinderGeometry(0.021, 0.021, 0.19, 28), new T.MeshStandardMaterial({ color: 0x4a4f57, roughness: 0.42, metalness: 0.5 }));
  ttube.rotation.x = Math.PI / 2; ttube.position.z = -0.12; tele.add(ttube);
  var obj = S.mesh(new T.CylinderGeometry(0.0195, 0.0195, 0.004, 28), M.glass); obj.rotation.x = Math.PI / 2;
  obj.position.z = -0.03; tele.add(obj);
  var eyep = S.mesh(new T.CylinderGeometry(0.012, 0.014, 0.03, 24), M.bakelite); eyep.rotation.x = Math.PI / 2;
  eyep.position.z = -0.225; tele.add(eyep);
  var tsup = S.mesh(new T.CylinderGeometry(0.007, 0.007, 0.06, 16), M.chrome); tsup.position.set(0, -0.04, -0.14);
  tele.add(tsup);
  var vern = S.mesh(new T.BoxGeometry(0.05, 0.004, 0.016), M.brass); vern.position.set(0, -0.012, -0.145);
  tele.add(vern);
  var tangK = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.012, 16), M.black); tangK.rotation.z = Math.PI / 2;
  tangK.position.set(0.03, -0.004, -0.16); tele.add(tangK);

  // the grating, upright on the prism table
  var table = new T.Group(); spec.add(table); table.position.set(0, 0.098, 0);
  var tbl = S.mesh(new T.CylinderGeometry(0.045, 0.045, 0.006, 32), M.brass); table.add(tbl);
  var gstand = S.mesh(new T.BoxGeometry(0.05, 0.004, 0.012), M.brass); gstand.position.y = 0.005; table.add(gstand);
  var gratM = new T.MeshPhysicalMaterial({ color: 0xdfe6ea, roughness: 0.12, transmission: 0.7, thickness: 0.002,
    transparent: true, opacity: 0.45 });
  var grat = S.mesh(new T.BoxGeometry(0.046, 0.042, 0.003), gratM); grat.position.y = 0.028; table.add(grat);
  var gframe = S.mesh(new T.BoxGeometry(0.05, 0.046, 0.001), M.black, false); gframe.position.set(0, 0.028, -0.0022);
  table.add(gframe);
  var glbl = S.label(Math.round(NLINES / 1000) + ' lines/mm', { w: 0.03, ratio: 0.25, color: '#1b1b1b' });
  glbl.position.set(0, 0.048, 0.002); table.add(glbl);

  // ================================================================ discharge tube and its supply
  var dis = new T.Group(); S.scene.add(dis); dis.position.set(CX, 0, CZ + 0.42);
  var dstand = S.rounded(0.09, 0.07, 0.012, 0.005, M.iron); dstand.rotation.x = -Math.PI / 2; dstand.position.y = 0.006;
  dis.add(dstand);
  var dpost = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.11, 16), M.chrome); dpost.position.y = 0.06; dis.add(dpost);
  var tubeM = new T.MeshPhysicalMaterial({ color: 0xe6c9d8, roughness: 0.08, transmission: 0.75, thickness: 0.004,
    transparent: true, opacity: 0.5, emissive: 0x000000 });
  var dtube = S.mesh(new T.CylinderGeometry(0.0075, 0.0075, 0.1, 24), tubeM); dtube.position.y = 0.16; dis.add(dtube);
  [-1, 1].forEach(function (sg) {
    var bulbE = S.mesh(new T.SphereGeometry(0.016, 20, 14), tubeM); bulbE.position.y = 0.16 + sg * 0.062; dis.add(bulbE);
    var cap = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.012, 16), M.brass); cap.position.y = 0.16 + sg * 0.082;
    dis.add(cap);
  });
  var clampD = S.mesh(new T.BoxGeometry(0.03, 0.01, 0.01), M.black); clampD.position.set(0, 0.115, 0); dis.add(clampD);
  var glowD = new T.PointLight(0xff93b4, 0, 0.6); glowD.position.set(0, 0.16, 0); dis.add(glowD);
  var hv = S.powerBox([0.34, 0, 0.24], 'E.H.T. 5 kV');
  var hvKnob = hv.userData.knob;
  S.wire([[CX, 0.02, CZ + 0.42], [0.18, 0.012, 0.34], [0.3, 0.02, 0.26]], 'red');
  S.wire([[CX + 0.02, 0.02, CZ + 0.42], [0.2, 0.012, 0.38], [0.38, 0.02, 0.26]], 'black');
  S.contact(0.4, 0.4, CX, CZ, 0.5);

  S.addApparatus('spec', spec, 'Spectrometer', 'A divided circle read by a vernier to one minute of arc, with a fixed collimator and a telescope that swings round it.');
  S.addApparatus('grating', table, 'Plane transmission grating (' + Math.round(NLINES / 1000) + ' lines/mm)',
    'Upright on the prism table and square to the collimator beam. It sends each wavelength out at its own angle: sin θ = m λ N.');
  S.addApparatus('tele', tele, 'Telescope with vernier', 'Swung round until a line sits on the cross-wires; the angle is then read on the circle.');
  S.addApparatus('dis', dis, SAMPLE, 'Hydrogen at low pressure glows pink. Its visible light is the Balmer series: four lines, not a continuous band.');
  S.addApparatus('hv', hv, 'E.H.T. supply (5 kV)', 'Runs the discharge tube. Switch it off before touching any lead.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard('Telescope'), hudL = S.hudCard('In the eyepiece'), hudW = S.hudCard('Wavelength');

  // ================================================================ human actions
  function strike(on) {
    if (busy()) return Promise.resolve();
    if (on === st.lit) return Promise.resolve();
    return S.hand.tap(hvKnob, 'front').then(function () {
      st.lit = on;
      tubeM.emissive = new T.Color(on ? 0xff6f9a : 0x000000); tubeM.emissiveIntensity = on ? 1.8 : 0;
      slitM.opacity = on ? 0.9 : 0; glowD.intensity = on ? 0.55 : 0;
      S.click(700, 0.06);
      S.say(on ? 'The tube strikes and glows pink. Through the eyepiece the light is not pink at all: it is four separate lines.'
        : 'E.H.T. off.');
      S.render();
    });
  }
  function level() {
    st.levelled = true; S.focus('spec');
    S.say('Circle levelled with the three screws, telescope focused on the slit, grating set square to the collimator. The direct reading is taken with the telescope straight through.');
    S.render();
  }
  function swing(th) {
    if (busy()) return Promise.resolve();
    if (!isFinite(th) || Math.abs(th) > 1.2) { S.say('The telescope only swings about 70° either side.'); return Promise.resolve(); }
    var t0 = st.th, pt = wpt(tele, 0, 0, -0.2);
    if (Math.abs(th - t0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      st.th = t0 + (th - t0) * k; arm.rotation.y = st.th;
    }, { mode: 'side', ms: 500 + 700 * Math.abs(th - t0), reachMs: 650 })
      .then(function () { st.th = th; arm.rotation.y = th; S.render(); });
  }
  /* Hunting a line the way a student does: swing until the line is brightest in the eyepiece, then set the
     cross-wires on it with the tangent screw. */
  function hunt(n) {
    if (busy()) return Promise.resolve(false);
    if (!st.lit) { S.say('Strike the discharge tube first.'); return Promise.resolve(false); }
    if (!visible(n)) {
      S.say('The ' + NAMES[n] + ' line is not diffracted at all in this order with this grating: m λ N is more than one. Use a coarser grating or the first order.');
      return Promise.resolve(false);
    }
    return swing(angleOf(n)).then(function () {
      S.say('The ' + NAMES[n] + ' line sits on the cross-wires. The vernier reads ' + degMin(readTh()) + '.');
      S.render(); return true;
    });
  }
  function takeDirect() {
    if (busy()) return Promise.resolve();
    return swing(0).then(function () {
      st.direct = readTh();
      S.say('Direct reading taken with the telescope straight through: ' + degMin(st.direct) + '. Every angle is measured from here.');
      S.render();
    });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.lit) { S.say('Strike the discharge tube first.'); return false; }
    if (st.direct === null) { S.say('Take the direct reading first: the circle\'s zero is not the straight-through direction.'); return false; }
    var b = brightest(st.th);
    if (!b || b.I < 0.5 * BRIGHT[b.n || 3] || !b.n) { S.say('No line is on the cross-wires. Hunt a line first.'); return false; }
    if (st.done[b.n]) { S.say('You already have the ' + NAMES[b.n] + ' line.'); return false; }
    var th = Math.abs(readTh() - st.direct);
    var lam = Math.sin(th) / (ORDER * NLINES);
    st.done[b.n] = true;
    S.addRow({ n: b.n, name: NAMES[b.n], th: th, lam: lam });
    S.say('Written in your record book: ' + NAMES[b.n] + ' at ' + degMin(th) + ', so λ = ' + (lam * 1e9).toFixed(2) + ' nm.');
    return true;
  }

  function result(rows) {
    var rs = rows.map(function (r) { return 1 / (r.lam * (0.25 - 1 / (r.n * r.n))); })
      .filter(function (x) { return isFinite(x) && x > 0; });
    if (rs.length < 3) return null;
    var R = S.fit.mean(rs);
    return { label: 'Rydberg constant of hydrogen', value: R / 1e7, unit: '× 10⁷ /m', digits: 4, truth: p.Rh / 1e7,
      note: 'Mean of 1/(λ(1/4 − 1/n²)) over ' + rs.length + ' Balmer lines, each wavelength taken from its own diffraction angle.' };
  }

  return {
    camera: { pos: [0.06, 0.78, 0.78], look: [0.0, 0.1, -0.06] },
    views: { spec: [[0.1, 0.42, 0.26], [0.0, 0.1, -0.1]], grating: [[0.06, 0.2, 0.02], [0.0, 0.12, -0.1]],
      tele: [[0.24, 0.26, 0.0], [0.0, 0.11, -0.12]], dis: [[0.16, 0.3, 0.46], [0.0, 0.16, 0.32]],
      hv: [[0.36, 0.26, 0.42], [0.34, 0.06, 0.24]],
      bench: [[0.06, 0.78, 0.78], [0.0, 0.1, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'Hydrogen\'s visible light is four sharp lines, the Balmer series: an electron falling from level n to level 2 gives out a photon of wavenumber R(1/4 − 1/n²). A plane transmission grating sends each wavelength out at its own angle, so reading that angle on the spectrometer circle measures the wavelength directly.',
      formula: 'sin θ = m λ N   and   1/λ = R (1/2² − 1/n²)',
      formulaNote: 'N = ' + Math.round(NLINES / 1000) + ' lines per mm, order m = ' + ORDER,
      more: ['The direct reading, with the telescope straight through, has to be taken first: the zero of the circle is not the straight-through direction, and every angle is measured from it.',
        'Each line gives its own value of the Rydberg constant; they are averaged.',
        'A higher order throws the same line out to a larger angle, so it can be read more accurately - but beyond sin θ = 1 that order does not exist at all.'],
      precautions: 'Level the circle, focus the telescope on the slit for parallel light, and set the grating square to the collimator. Read both verniers on a real instrument to cancel any eccentricity of the circle.' },
    book: { title: 'Expt. — Balmer lines and the Rydberg constant',
      lines: ['Aim: wavelengths of the Balmer lines; R.', 'Source: ' + SAMPLE,
        'Grating ' + Math.round(NLINES / 1000) + ' lines/mm, order m = ' + ORDER,
        'sin θ = m λ N;  1/λ = R(1/4 − 1/n²)', 'Vernier reads to one minute of arc.',
        'Direct reading taken before every line.'],
      columns: [{ label: 'Line', get: function (r) { return r.name; } },
        { label: 'n', get: function (r) { return r.n; } },
        { label: 'θ', get: function (r) { return degMin(r.th); } },
        { label: 'λ (nm)', get: function (r) { return (r.lam * 1e9).toFixed(2); } }] },
    graph: { x: function (r) { return 0.25 - 1 / (r.n * r.n); }, y: function (r) { return 1 / r.lam / 1e6; },
      xlabel: '1/4 − 1/n²', ylabel: '1/λ (10⁶ /m)', x0: 0, y0: 0,
      line: function (pts) { var m = S.fit.origin(pts); return isFinite(m) ? function (x) { return m * x; } : null; } },
    result: result,
    tol: 0.02,
    resultNote: 'One number, the Rydberg constant, fixes every line of hydrogen - and the straight line through the origin of 1/λ against (1/4 − 1/n²) is Balmer\'s formula drawn out of your own angles.',
    chips: ['Why take a direct reading?', 'Why is the grating set square to the beam?',
      'Why does hydrogen give lines and not a band?', 'Check my readings', 'What would a second order change?'],
    viva: [['The direct reading is needed because', ['The circle\'s zero is not the straight-through direction', 'The telescope is loose', 'The grating is thick'], 0,
      'Angles are measured from the straight-through position, so it has to be read first.'],
      ['In sin θ = m λ N, the line bent through the largest angle is', ['The longest wavelength', 'The shortest wavelength', 'The brightest'], 0,
        'sin θ is proportional to λ, so red is thrown out furthest.'],
      ['The Balmer series are the jumps ending on', ['n = 2', 'n = 1', 'n = 3'], 0,
        'That is why 1/λ = R(1/2² − 1/n²).']],
    askState: function () {
      var b = brightest(st.th);
      return { experiment: 'Balmer lines of hydrogen with a plane grating; the Rydberg constant',
        tube_lit: st.lit, grating_lines_per_mm: Math.round(NLINES / 1000), order: ORDER,
        telescope_angle: degMin(readTh()), direct_reading_taken: st.direct !== null,
        line_in_the_eyepiece: b && b.n ? NAMES[b.n] : (b ? 'the direct image of the slit' : 'nothing'),
        lines_recorded: S.rows.length };
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'spec', render: function (u) {
          u.h2('Level, focus, and take the direct reading');
          u.p('The grating stands square to the collimator on the prism table. Strike the discharge tube, then swing the telescope straight through and read the circle: that is the direct reading, from which every angle is measured.');
          u.task('1. Level and focus', st.levelled, st.levelled ? 'Circle levelled, telescope focused, grating square' : 'Three levelling screws and the tangent screw')
            .add(u.button(st.levelled ? 'Done' : 'Level and focus', level, !st.levelled, st.levelled));
          u.task('2. Strike the discharge tube', st.lit, st.lit ? 'Tube glowing pink' : 'E.H.T. off')
            .add(u.button(st.lit ? 'Tube is lit' : 'Switch the E.H.T. on', function () { S.focus('dis'); strike(true); }, !st.lit, st.lit || S.hand.busy));
          u.task('3. Direct reading', st.direct !== null, st.direct === null ? 'Telescope straight through' : 'Direct reading ' + degMin(st.direct))
            .add(u.button('Take the direct reading', function () { S.focus('tele'); takeDirect(); }, false, S.hand.busy));
          u.live(function () { var b = brightest(st.th);
            return 'Telescope ' + degMin(readTh()) + '  ·  ' + (b ? (b.n ? NAMES[b.n] : 'direct image of the slit') : 'dark field'); });
          u.note('The E.H.T. runs at a few kilovolts. Switch it off before touching any lead.');
          u.next('Next: measure the lines', st.levelled && st.lit && st.direct !== null);
        },
        ok: function () { return st.levelled && st.lit && st.direct !== null; },
        auto: function () { level(); return strike(true).then(function () { return takeDirect(); }); } },

      { id: 'lines', title: 'The Balmer lines', view: 'tele', render: function (u) {
          u.h2('Swing to each line and read the circle');
          u.p('Swing the telescope away from the direct position until a line appears in the eyepiece, set the cross-wires on it, read the vernier and record it. Take as many of the four lines as this grating and order will show.');
          var sel = { i: 0 };
          u.slider('Line to hunt (n)', 3, 6, 1, function () { return LINES[sel.i]; },
            function (v) { sel.i = Math.max(0, Math.min(3, Math.round(v) - 3)); }, '', 0);
          u.row(u.button('Hunt this line', function () { hunt(LINES[sel.i]); }, true, S.hand.busy),
            u.button('Record θ and λ', function () { record(); }, false, S.hand.busy));
          u.row(u.button('Back to the direct position', function () { swing(0); }, false, S.hand.busy || st.th === 0));
          u.live(function () { var b = brightest(st.th);
            return 'Telescope ' + degMin(readTh()) + '  ·  ' + (b ? (b.n ? NAMES[b.n] + ' on the cross-wires' : 'direct image') : 'dark field'); });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 lines recorded.');
          u.next('Next: the Rydberg constant', S.rows.length >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          return LINES.reduce(function (pr, n) {
            return pr.then(function () { return hunt(n); }).then(function (ok) { if (ok) record(); });
          }, Promise.resolve());
        } },
    ],

    tick: function () {
      var b = brightest(st.th);
      hudA.set(degMin(readTh()));
      hudL.set(b ? (b.n ? NAMES[b.n] : 'direct image') : 'dark field');
      hudW.set(b && b.n ? (lamOf(b.n) * 1e9).toFixed(1) + ' nm' : '—');
      if (b && b.n) { glowD.color.setHex(COLS[b.n]); }
    },
  };
});
