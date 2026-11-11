/* Prayogshala studio module: radius of curvature of a spherical surface with a spherometer (NCERT Class XI, Section A).
   A brass spherometer - three legs on the corners of an equilateral triangle, a central screw of 1 mm pitch carrying a
   disc of 100 divisions, and a vertical millimetre scale beside the disc - stands first on a plane glass plate and then
   on a watch glass, convex side up and then concave side up. The gloved hand lifts the spherometer from one surface to
   the other, turns the disc until the tip just touches, and turns the watch glass over.
   Physics: the `spherometer` kernel of the mech11 pack - h = R - sqrt(R² - l²/3) and R = l²/(6h) + h/2. */
HoolaStudio.define('spherometer-radius', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.spherometer;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('spherometer');
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '') || 'Watch glass';
  var LC = p.pitch / p.ndiv;                                   // 0.01 mm
  var H = K.measure(p).h;                                      // the sagitta of this surface (what the student measures)
  var st = { place: 'plate', touching: false, zero: null, scr: 0, flipped: false, done: {} };
  // scr = height of the screw tip above the plane of the legs (positive = tip below? no: positive = tip DOWN)

  // ---------- geometry (the real instrument, 1:1 on the bench)
  var SZ = -0.05, PLATE = new T.Vector3(-0.11, 0, SZ), GLASSP = new T.Vector3(0.02, 0, SZ);
  var PLATE_T = 0.007, LEGS = 0.048, CIRC = p.l / Math.sqrt(3);
  var GR = 0.055;                                              // radius of the watch glass
  var SAG = p.R - Math.sqrt(Math.max(1e-9, p.R * p.R - GR * GR));

  // plane glass plate on a dark mat, so the glass can be seen
  var mat1 = S.mesh(new T.BoxGeometry(0.14, 0.002, 0.14), new T.MeshStandardMaterial({ color: 0x14161a, roughness: 0.9 }), false);
  mat1.position.set(PLATE.x, 0.001, PLATE.z); S.scene.add(mat1);
  var plate = S.mesh(new T.BoxGeometry(0.12, PLATE_T, 0.12), M.glassBlock, true, false);
  plate.position.set(PLATE.x, 0.002 + PLATE_T / 2, PLATE.z); S.scene.add(plate);
  S.contact(0.18, 0.18, PLATE.x, PLATE.z, 0.45);

  // the watch glass: a spherical cap that can be laid convex side up or concave side up
  var mat2 = S.mesh(new T.BoxGeometry(0.15, 0.002, 0.15), new T.MeshStandardMaterial({ color: 0x14161a, roughness: 0.9 }), false);
  mat2.position.set(GLASSP.x, 0.001, GLASSP.z); S.scene.add(mat2);
  var glass = new T.Group(); S.scene.add(glass);
  var capPts = [];
  for (var i = 0; i <= 24; i++) {
    var rr = GR * i / 24;
    capPts.push(new T.Vector2(rr, p.R - Math.sqrt(Math.max(0, p.R * p.R - rr * rr))));
  }
  var capG = new T.LatheGeometry(capPts, 48);
  var capM = new T.MeshPhysicalMaterial({ color: 0xe6f0f2, roughness: 0.05, metalness: 0, transmission: 0.82,
    thickness: 0.004, ior: 1.52, transparent: true, side: T.DoubleSide });
  var cap = S.mesh(capG, capM, true, false); glass.add(cap);
  var rim = S.mesh(new T.TorusGeometry(GR, 0.0016, 8, 56), capM, false, false); rim.rotation.x = Math.PI / 2; rim.position.y = SAG; glass.add(rim);
  glass.position.set(GLASSP.x, 0.002, GLASSP.z);              // convex side UP: the cap opens downward
  glass.rotation.x = Math.PI;                                  // lathe builds the cup opening up; flip for convex up
  glass.position.y = 0.002 + SAG;
  S.contact(0.18, 0.18, GLASSP.x, GLASSP.z, 0.45);

  // ---------- the spherometer
  var sph = new T.Group(); S.scene.add(sph);
  var legY = LEGS;                                             // the frame sits this high above the leg tips
  var legs = [0, 1, 2].map(function (k) {
    var a = -Math.PI / 2 + k * 2 * Math.PI / 3;
    var g = new T.Group();
    var rod = S.mesh(new T.CylinderGeometry(0.0016, 0.0009, legY, 14), M.chrome); rod.position.y = legY / 2; g.add(rod);
    g.position.set(Math.cos(a) * CIRC, 0, Math.sin(a) * CIRC);
    sph.add(g);
    return g;
  });
  var frameShape = new T.Shape();
  [0, 1, 2].forEach(function (k) {
    var a = -Math.PI / 2 + k * 2 * Math.PI / 3, x = Math.cos(a) * CIRC, z = Math.sin(a) * CIRC;
    if (k === 0) frameShape.moveTo(x, z); else frameShape.lineTo(x, z);
  });
  frameShape.closePath();
  var frame = S.mesh(new T.ExtrudeGeometry(frameShape, { depth: 0.005, bevelEnabled: true, bevelThickness: 0.0008, bevelSize: 0.0008, bevelSegments: 2 }), M.brass);
  frame.rotation.x = Math.PI / 2; frame.position.y = legY; sph.add(frame);
  var boss = S.mesh(new T.CylinderGeometry(0.007, 0.008, 0.016, 20), M.brass); boss.position.y = legY + 0.004; sph.add(boss);
  // the vertical millimetre scale, fixed to the frame beside the disc
  var vsTex = S.canvasTex(64, 320, function (x, w, h) {
    x.fillStyle = '#d9b154'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#2a1e06'; x.font = '600 20px "Public Sans", sans-serif'; x.textBaseline = 'middle';
    for (var i = 0; i <= 15; i++) { var y = h - 12 - i * (h - 24) / 15; x.fillRect(0, y - 1, i % 5 === 0 ? w * 0.5 : w * 0.3, 2); if (i % 5 === 0) x.fillText(String(i), w * 0.58, y); }
  });
  var vs = new T.Mesh(new T.PlaneGeometry(0.006, 0.03), new T.MeshStandardMaterial({ map: vsTex, roughness: 0.4 }));
  vs.position.set(0.0135, legY + 0.019, 0.0036); sph.add(vs);
  var vsBack = S.mesh(new T.BoxGeometry(0.008, 0.032, 0.003), M.brass); vsBack.position.set(0.0135, legY + 0.019, 0.002); sph.add(vsBack);

  var screw = new T.Group(); sph.add(screw);
  var shaft = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.065, 16), M.chrome); shaft.position.y = legY - 0.004; screw.add(shaft);
  var tip = S.mesh(new T.ConeGeometry(0.0018, 0.005, 14), M.chrome); tip.rotation.x = Math.PI; tip.position.y = legY - 0.0385; screw.add(tip);
  var discTex = S.canvasTex(1024, 1024, function (x, w) {
    var c = w / 2, R0 = c * 0.96;
    x.fillStyle = '#d9b154'; x.beginPath(); x.arc(c, c, R0, 0, Math.PI * 2); x.fill();
    x.fillStyle = '#2a1e06'; x.font = '600 30px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
    for (var i = 0; i < 100; i++) {
      var a = -Math.PI / 2 + i * Math.PI * 2 / 100, big = i % 5 === 0, L = big ? 44 : 24;
      x.save(); x.translate(c + Math.cos(a) * R0, c + Math.sin(a) * R0); x.rotate(a + Math.PI / 2);
      x.fillRect(-1.6, -L, big ? 3.6 : 2, L); x.restore();
      if (i % 10 === 0) x.fillText(String(i), c + Math.cos(a) * (R0 - 70), c + Math.sin(a) * (R0 - 70));
    }
    x.beginPath(); x.arc(c, c, R0 * 0.18, 0, Math.PI * 2); x.fillStyle = '#b8912f'; x.fill();
  });
  var disc = new T.Group(); screw.add(disc);
  var discM = S.mesh(new T.CylinderGeometry(0.023, 0.023, 0.005, 56), [new T.MeshStandardMaterial({ color: 0xd9b154, roughness: 0.3, metalness: 0.8 }),
    new T.MeshStandardMaterial({ map: discTex, roughness: 0.35, metalness: 0.6 }),
    new T.MeshStandardMaterial({ color: 0xc9a44a, roughness: 0.4, metalness: 0.7 })]);
  disc.add(discM);
  var knurl = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.008, 18), M.brass); knurl.position.y = 0.006; disc.add(knurl);
  disc.position.y = legY + 0.028;
  var idx = S.mesh(new T.BoxGeometry(0.004, 0.0012, 0.0012), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.4 }), false);
  idx.position.set(0.0125, legY + 0.0295, 0.0045); sph.add(idx);

  function placeSph() {
    var at = st.place === 'plate' ? PLATE : GLASSP;
    var baseY = st.place === 'plate' ? 0.002 + PLATE_T
      : (st.flipped ? 0.002 + SAG - legPlaneDrop() : 0.002 + legPlaneDrop2());
    sph.position.set(at.x, baseY, at.z);
  }
  function legPlaneDrop() { return 0; }
  function legPlaneDrop2() { return p.R - Math.sqrt(Math.max(1e-9, p.R * p.R - CIRC * CIRC)); }  // legs on the convex cap
  placeSph();

  S.addApparatus('sph', sph, 'Spherometer', 'Three legs on an equilateral triangle of side ' + (p.l * 1000).toFixed(1)
    + ' mm, and a central screw of pitch ' + (p.pitch * 1000).toFixed(1) + ' mm with ' + p.ndiv + ' divisions on the disc: least count '
    + (LC * 1000).toFixed(2) + ' mm.');
  S.addApparatus('plate', plate, 'Plane glass plate', 'A flat, thick glass plate: the zero reading of the screw is taken on it.');
  S.addApparatus('glass', glass, SAMPLE, 'The spherical surface whose radius of curvature you measure. It can be laid convex side up or concave side up.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudP = S.hudCard('Spherometer on'), hudR = S.hudCard('Screw reading'), hudH = S.hudCard('Sagitta h');

  // ---------- readings
  function touchScr() {                                        // the screw position (mm, downward positive) at contact
    if (st.place === 'plate') return 0;
    return st.flipped ? -H : H;                                // convex: the tip goes DOWN by h; concave: UP by h
  }
  function readingMm() { return Math.round(st.scr * 1000 * 100) / 100; }
  function turns() { return Math.floor(Math.abs(st.scr) / p.pitch + 1e-9) * (st.scr < 0 ? -1 : 1); }
  function divs() { return Math.round((Math.abs(st.scr) - Math.abs(turns()) * p.pitch) / LC); }

  function turnScrew() {
    if (S.hand.busy) return Promise.resolve();
    if (st.touching) { S.say('The tip is already just touching. Read the scale.'); return Promise.resolve(); }
    var s0 = st.scr, s1 = touchScr();
    var grip = new T.Vector3(sph.position.x + 0.024, sph.position.y + legY + 0.03, sph.position.z);
    return S.hand.pinchMove(grip, function () { return grip; },
      function (k) { st.scr = s0 + (s1 - s0) * k; }, { ms: 1500, mode: 'top', pose: 'pinch' })
      .then(function () {
        st.scr = s1; st.touching = true;
        S.say('The tip just touches ' + (st.place === 'plate' ? 'the plane glass plate' : 'the spherical surface')
          + ': the disc reads ' + Math.abs(divs()) + ' and the vertical scale shows ' + Math.abs(turns()) + ' whole turn'
          + (Math.abs(turns()) === 1 ? '' : 's') + '.');
        S.render();
      });
  }
  function readZero() {
    if (st.place !== 'plate') { S.say('The zero reading is taken on the plane glass plate.'); return; }
    if (!st.touching) { S.say('Turn the screw down until the tip just touches the plate.'); return; }
    st.zero = readingMm();
    S.say('Zero reading ' + st.zero.toFixed(2) + ' mm. Every sagitta is measured from this.');
    S.render();
  }
  function moveTo(place, flipped) {
    if (S.hand.busy) return Promise.resolve();
    var from = sph.position.clone();
    st.place = place; st.flipped = !!flipped; placeSph();
    var to = sph.position.clone();
    sph.position.copy(from);
    st.touching = false; st.scr = 0;
    function path(k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
    }
    var grip = new T.Vector3(0, legY + 0.03, 0);
    return S.hand.pinchMove(from.clone().add(grip), function (k) { return path(k).add(grip); },
      function (k) { sph.position.copy(path(k)); }, { ms: 1400, mode: 'top' })
      .then(function () {
        placeSph();
        S.say(place === 'plate' ? 'The spherometer stands on the plane glass plate.'
          : 'The three legs stand on the ' + (flipped ? 'concave' : 'convex') + ' side of the surface. Turn the screw until the tip just touches.');
        S.render();
      });
  }
  function flipGlass() {
    if (S.hand.busy) return Promise.resolve();
    if (st.place === 'glass') { S.say('Lift the spherometer off the surface before turning it over.'); return Promise.resolve(); }
    var a0 = glass.rotation.x, a1 = a0 === Math.PI ? 0 : Math.PI;
    var y0 = glass.position.y, y1 = a1 === 0 ? 0.002 : 0.002 + SAG;
    var grip = new T.Vector3(GLASSP.x + GR, 0.01, GLASSP.z);
    return S.hand.pinchMove(grip, function (k) { return new T.Vector3(GLASSP.x + GR * Math.cos(Math.PI * k), 0.01 + 0.05 * Math.sin(Math.PI * k), GLASSP.z); },
      function (k) { glass.rotation.x = a0 + (a1 - a0) * k; glass.position.y = y0 + (y1 - y0) * k + 0.05 * Math.sin(Math.PI * k); }, { ms: 1400, mode: 'top' })
      .then(function () {
        glass.rotation.x = a1; glass.position.y = y1;
        S.say('The surface is turned over: the ' + (a1 === 0 ? 'concave' : 'convex') + ' side is now uppermost.');
        S.render();
      });
  }
  function record(side) {
    if (S.hand.busy) return;
    if (st.zero === null) { S.say('Take the zero reading on the plane plate first.'); return; }
    if (st.place !== 'glass') { S.say('Put the spherometer on the spherical surface first.'); return; }
    if (!st.touching) { S.say('Turn the screw until the tip just touches the surface.'); return; }
    if (st.done[side]) { S.say('That side is already in the table.'); return; }
    var h = Math.abs(readingMm() - st.zero);
    if (h <= 0) { S.say('The reading has not changed. Turn the screw until it touches.'); return; }
    st.done[side] = true;
    S.addRow({ l: p.l, h: h / 1000, side: side, rd: readingMm() });
    S.say('Written in your record book: ' + side + ' side, reading ' + readingMm().toFixed(2) + ' mm, sagitta h = ' + h.toFixed(2) + ' mm.');
  }

  var CALC = HK.CALCS.sph_R;

  return {
    camera: { pos: [0.1, 0.17, 0.26], look: [-0.03, 0.045, -0.05] },
    views: {
      rig: [[0.1, 0.17, 0.26], [-0.03, 0.045, -0.05]],
      sph: [[0.07, 0.12, 0.13], [sph.position.x, 0.055, SZ]],
      plate: [[PLATE.x + 0.09, 0.15, PLATE.z + 0.2], [PLATE.x, 0.05, PLATE.z]],
      glass: [[GLASSP.x + 0.08, 0.15, GLASSP.z + 0.2], [GLASSP.x, 0.05, GLASSP.z]],
      disc: [[0.04, 0.12, 0.09], [0.0, 0.08, SZ]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'The three legs of a spherometer stand on a circle of radius l/√3, where l is the distance between two '
        + 'legs. When the tip of the central screw just touches the surface, the height of the tip above or below the '
        + 'plane of the legs is the sagitta h of that circle on the sphere.',
      formula: 'R = l² / (6h) + h / 2',
      formulaNote: 'h = reading on the surface − reading on the plane plate · l = mean distance between the legs',
      more: ['The screw has a pitch of ' + (p.pitch * 1000).toFixed(1) + ' mm and the disc ' + p.ndiv + ' divisions, so one '
        + 'division is ' + (LC * 1000).toFixed(2) + ' mm. The whole turns are read on the vertical scale and the fraction on the disc.',
        'On a convex surface the tip has to go below the plane of the legs, and on a concave surface above it; the two '
        + 'readings lie on opposite sides of the zero but give the same R.'],
      precautions: 'Turn the screw gently and stop the moment the tip touches: pressing harder lifts a leg and spoils the '
        + 'reading. Measure l from the marks the legs make on paper, and take the mean of the three sides.'
    },
    book: {
      title: 'Expt. — Radius of Curvature (Spherometer)',
      lines: ['Aim: radius of curvature of a spherical surface.',
        'Pitch = ' + (p.pitch * 1000).toFixed(1) + ' mm, divisions on the disc = ' + p.ndiv,
        'Least count = ' + (LC * 1000).toFixed(2) + ' mm',
        'Mean distance between the legs l = ' + (p.l * 1000).toFixed(1) + ' mm',
        'h = reading on the surface − reading on the plate', 'R = l²/(6h) + h/2',
        'Precautions: gentle contact, clean surfaces.'],
      columns: [{ label: 'Surface', get: function (r) { return r.side; } },
        { label: 'Reading (mm)', get: function (r) { return r.rd.toFixed(2); } },
        { label: 'h (mm)', get: function (r) { return (r.h * 1000).toFixed(2); } },
        { label: 'l (mm)', get: function (r) { return (r.l * 1000).toFixed(1); } },
        { label: 'R (cm)', get: function (r) { return ((r.l * r.l / (6 * r.h) + r.h / 2) * 100).toFixed(1); } }]
    },
    graph: null,
    result: function (rows) {
      if (!rows.length) return null;
      return { label: 'R (radius of curvature)', value: CALC.fn(rows, p), unit: 'm', digits: 3, truth: p.R,
        note: 'Mean of R = l²/(6h) + h/2 over the convex and concave readings.' };
    },
    resultNote: 'h appears in the denominator, so a small error in the sagitta makes a large error in R: that is why the '
      + 'screw must be stopped the moment it touches.',
    tol: 0.03,
    chips: ['Why is the least count 0.01 mm?', 'Why does a flatter surface give a smaller h?',
      'How is l measured?', 'Check my readings', 'What are the main sources of error?'],
    viva: [['What is measured on the plane glass plate?',
      ['The zero reading of the screw, when the tip and the legs are in one plane', 'The thickness of the plate',
        'The radius of the plate'], 0, 'Every sagitta is the difference from that zero reading.'],
      ['If l is measured 1 % too large, the radius comes out',
        ['About 2 % too large', 'About 1 % too small', 'Unchanged'], 0, 'R depends on l², so the error doubles.']],
    askState: function () {
      return { standing_on: st.place === 'plate' ? 'plane glass plate' : ((st.flipped ? 'concave' : 'convex') + ' side of the surface'),
        screw_reading_mm: readingMm(), zero_reading_mm: st.zero, tip_touching: st.touching,
        whole_turns: turns(), disc_division: divs(), leg_distance_mm: +(p.l * 1000).toFixed(1),
        least_count_mm: +(LC * 1000).toFixed(2), readings_taken: S.rows.length };
    },

    steps: [
      { id: 'zero', title: 'Zero reading', view: 'plate', render: function (u) {
          u.h2('Zero reading on the plane glass plate');
          u.p('Stand the spherometer on the plane glass plate and turn the disc until the tip just touches the glass - '
            + 'the moment it does, the instrument rocks on four points instead of three. Then read the screw.');
          u.task('1. Spherometer on the plate', st.place === 'plate', st.place === 'plate' ? 'Standing on the plate' : 'Lift it back onto the plate')
            .add(u.button('Put it on the plate', function () { moveTo('plate', st.flipped); }, false, S.hand.busy || st.place === 'plate'));
          u.task('2. Turn the screw until the tip just touches', st.touching, st.touching ? 'Touching' : 'Gently')
            .add(u.button('Turn the screw', function () { turnScrew(); }, !st.touching, S.hand.busy || st.touching));
          u.task('3. Read the screw', st.zero !== null, st.zero !== null ? 'Zero reading = ' + st.zero.toFixed(2) + ' mm' : 'Whole turns + disc divisions')
            .add(u.button('Read the screw', readZero, st.zero === null && st.touching, S.hand.busy || st.zero !== null || !st.touching));
          u.live(function () { return 'Screw ' + readingMm().toFixed(2) + ' mm · ' + Math.abs(turns()) + ' turns + ' + Math.abs(divs()) + ' divisions'; });
          u.next('Next: the convex side', st.zero !== null);
        },
        ok: function () { return st.zero !== null; },
        auto: function () { return turnScrew().then(function () { readZero(); }); } },

      { id: 'convex', title: 'Convex side', view: 'glass', render: function (u) {
          u.h2('Measure the sagitta on the convex side');
          u.p('Lift the spherometer onto the convex side of the ' + SAMPLE.toLowerCase() + '. Its three legs stand on the '
            + 'curved surface, so the tip must be screwed DOWN to reach it. The difference from the zero reading is h.');
          u.task('1. Spherometer on the surface', st.place === 'glass', st.place === 'glass' ? 'Standing on the surface' : 'On the plate just now')
            .add(u.button('Move it onto the surface', function () { moveTo('glass', false); }, st.place !== 'glass', S.hand.busy || st.place === 'glass'));
          u.task('2. Turn the screw until it just touches', st.touching, st.touching ? 'Touching' : 'Gently')
            .add(u.button('Turn the screw', function () { turnScrew(); }, !st.touching && st.place === 'glass', S.hand.busy || st.touching || st.place !== 'glass'));
          u.row(u.button('Record this reading', function () { record('convex'); }, true, S.hand.busy || !st.touching || st.place !== 'glass' || !!st.done.convex));
          u.live(function () {
            return 'Screw ' + readingMm().toFixed(2) + ' mm · zero ' + (st.zero === null ? '—' : st.zero.toFixed(2) + ' mm')
              + (st.touching && st.zero !== null ? ' · h = ' + Math.abs(readingMm() - st.zero).toFixed(2) + ' mm' : '');
          });
          u.h3('Observation table'); u.table();
          u.next('Next: the concave side', !!st.done.convex);
        },
        ok: function () { return !!st.done.convex; },
        auto: function () { return moveTo('glass', false).then(turnScrew).then(function () { record('convex'); }); } },

      { id: 'concave', title: 'Concave side', view: 'glass', render: function (u) {
          u.h2('Turn the surface over and measure again');
          u.p('Lift the spherometer off, turn the ' + SAMPLE.toLowerCase() + ' over, and stand the spherometer on the '
            + 'concave side. Now the tip must come UP to touch, so the reading lies on the other side of the zero - but '
            + 'the sagitta, and so the radius, is the same.');
          u.row(u.button('Lift it back onto the plate', function () { moveTo('plate', st.flipped); }, false, S.hand.busy || st.place === 'plate'),
            u.button('Turn the surface over', function () { flipGlass(); }, glass.rotation.x === Math.PI, S.hand.busy || st.place === 'glass'),
            u.button('Put it on the concave side', function () { moveTo('glass', true); }, glass.rotation.x === 0, S.hand.busy || glass.rotation.x !== 0));
          u.row(u.button('Turn the screw', function () { turnScrew(); }, !st.touching && st.place === 'glass', S.hand.busy || st.touching || st.place !== 'glass'),
            u.button('Record this reading', function () { record('concave'); }, true, S.hand.busy || !st.touching || st.place !== 'glass' || !!st.done.concave));
          u.live(function () {
            return (glass.rotation.x === 0 ? 'Concave side up' : 'Convex side up') + ' · screw ' + readingMm().toFixed(2) + ' mm';
          });
          u.h3('Observation table'); u.table();
          u.next('Next: the radius of curvature', S.rows.length >= 2);
        },
        ok: function () { return S.rows.length >= 2; },
        auto: function () {
          return moveTo('plate', false).then(flipGlass).then(function () { return moveTo('glass', true); })
            .then(turnScrew).then(function () { record('concave'); });
        } }
    ],

    tick: function () {
      screw.position.y = -st.scr;
      disc.rotation.y = -st.scr / p.pitch * Math.PI * 2;
      hudP.set(st.place === 'plate' ? 'plane plate' : (st.flipped ? 'concave side' : 'convex side'));
      hudR.set(readingMm().toFixed(2) + ' mm');
      hudH.set(st.zero === null || !st.touching || st.place === 'plate' ? '—' : Math.abs(readingMm() - st.zero).toFixed(2) + ' mm');
    }
  };
});
