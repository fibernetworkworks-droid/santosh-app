/* Prayogshala studio module: a coin in water looks raised and a pencil looks bent (NCERT Class X).
   A glass trough on the bench, a coin lying at the bottom, a pencil standing in the water, and a travelling
   microscope on its stand above. The microscope is focused on the coin and then on the surface, and the difference
   is the apparent depth. Every number comes from the shared `slab` kernel (app, shift): the ray from the coin is
   refracted at the water surface and produced back to the axis. */
HoolaStudio.define('school-water-refraction', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.slab;
  var p = window.HoolaKernels.paramsFor('slab', S.lab.params);
  var TZ = -0.1, TW = 0.2, TD = 0.12, TH = 0.15;                     // the trough: z, width, depth, height
  var SAMPLE = (S.lab.variant || {}).sample || 'Clean water';
  var st = { tCm: p.t * 100, tSet: p.t * 100, poured: false, looked: false, focus: 'none' };
  function round1(v) { return Math.round(v * 10) / 10; }
  function round2(v) { return Math.round(v * 100) / 100; }
  function sync() { p.t = Math.max(0.02, st.tCm / 100); return K.view(null, p); }

  // ---------- the trough
  var troughG = new T.Group(); S.scene.add(troughG); troughG.position.set(0, 0, TZ);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xeaf4f6, roughness: 0.04, metalness: 0, transmission: 0.9, thickness: 0.006, ior: 1.5, transparent: true });
  [[0, 0, -TD / 2, TW, TH, 0.004], [0, 0, TD / 2, TW, TH, 0.004], [-TW / 2, 0, 0, 0.004, TH, TD], [TW / 2, 0, 0, 0.004, TH, TD]].forEach(function (a) {
    var m = S.mesh(new T.BoxGeometry(a[3], a[4], a[5]), glassM); m.position.set(a[0], a[4] / 2, a[2]); troughG.add(m); });
  var base = S.mesh(new T.BoxGeometry(TW, 0.005, TD), glassM); base.position.y = 0.0025; troughG.add(base);
  var rim = new T.LineSegments(new T.EdgesGeometry(new T.BoxGeometry(TW, TH, TD)), new T.LineBasicMaterial({ color: 0x7e9aa2, transparent: true, opacity: 0.7 }));
  rim.position.y = TH / 2; troughG.add(rim);
  S.contact(0.3, 0.22, 0, TZ, 0.45);

  var waterM = new T.MeshPhysicalMaterial({ color: 0x86c6e4, roughness: 0.05, metalness: 0, transmission: 0.55, thickness: 0.06, ior: 1.333, transparent: true, opacity: 0.85 });
  var water = S.mesh(new T.BoxGeometry(TW - 0.009, 1, TD - 0.009), waterM); troughG.add(water);
  var surf = new T.Mesh(new T.PlaneGeometry(TW - 0.009, TD - 0.009), new T.MeshPhysicalMaterial({ color: 0xbfe6f4, roughness: 0.02, transmission: 0.4, transparent: true, opacity: 0.7 }));
  surf.rotation.x = -Math.PI / 2; troughG.add(surf);

  // ---------- the coin and where it appears
  var coinM = new T.MeshStandardMaterial({ color: 0xc9a227, roughness: 0.3, metalness: 1 });
  var coin = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.0016, 28), coinM); coin.position.set(-0.03, 0.0062, 0); troughG.add(coin);
  var ghost = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.0012, 28), new T.MeshStandardMaterial({ color: 0xc23b30, roughness: 0.4, transparent: true, opacity: 0.45 }), false);
  ghost.position.set(-0.03, 0.02, 0); troughG.add(ghost); ghost.visible = false;

  // ---------- the pencil, leaning in the water (the part under water APPEARS raised, so it looks broken)
  var pencilG = new T.Group(); troughG.add(pencilG);
  var PB = { x: 0.055, z: 0.012 }, LEAN = 0.32, UPL = 0.14;          // where its tip rests, its lean, the part above water
  var pMat = new T.MeshStandardMaterial({ color: 0xe8b024, roughness: 0.5 });
  var pencilLow = S.mesh(new T.CylinderGeometry(0.004, 0.004, 1, 12), pMat);
  var pencilUp = S.mesh(new T.CylinderGeometry(0.004, 0.004, UPL, 12), pMat);
  var tip = S.mesh(new T.ConeGeometry(0.004, 0.012, 12), M.wood);
  pencilG.add(pencilLow); pencilG.add(pencilUp); pencilG.add(tip);

  // ---------- the travelling microscope
  var micG = new T.Group(); S.scene.add(micG); micG.position.set(0.16, 0, TZ - 0.02);
  var mBase = S.rounded(0.1, 0.09, 0.018, 0.004, M.iron); mBase.rotation.x = -Math.PI / 2; mBase.position.y = 0.009; micG.add(mBase);
  var mPost = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.3, 20), M.chrome); mPost.position.y = 0.16; micG.add(mPost);
  var mScaleTex = S.canvasTex(96, 1024, function (x, w, h) {
    x.fillStyle = '#f2eee1'; x.fillRect(0, 0, w, h); x.fillStyle = '#1a1a1a';
    var mm = 160, k = h / mm, i;
    for (i = 0; i <= mm; i++) { var yy = h - i * k, big = i % 10 === 0;
      x.fillRect(0, yy - 1, big ? 40 : (i % 5 === 0 ? 26 : 16), big ? 2.6 : 1.3);
      if (big) { x.font = '600 20px sans-serif'; x.fillText(String(i / 10), 44, yy + 7); } }
  });
  var mScale = new T.Mesh(new T.PlaneGeometry(0.02, 0.28), new T.MeshStandardMaterial({ map: mScaleTex, roughness: 0.6 }));
  mScale.position.set(-0.013, 0.16, 0.001); micG.add(mScale);
  var carriage = new T.Group(); micG.add(carriage);
  var cBody = S.rounded(0.05, 0.04, 0.03, 0.004, M.alu); cBody.position.set(0.012, 0, 0); carriage.add(cBody);
  var tube = S.mesh(new T.CylinderGeometry(0.013, 0.015, 0.1, 20), new T.MeshStandardMaterial({ color: 0x23262c, roughness: 0.4, metalness: 0.4 }));
  tube.rotation.z = Math.PI / 2; tube.position.set(-0.07, 0.006, 0); carriage.add(tube);
  var eyep = S.mesh(new T.CylinderGeometry(0.009, 0.011, 0.03, 18), M.bakelite); eyep.rotation.z = Math.PI / 2; eyep.position.set(-0.004, 0.006, 0); carriage.add(eyep);
  var objl = S.mesh(new T.CylinderGeometry(0.008, 0.01, 0.022, 18), M.brass); objl.rotation.z = Math.PI / 2; objl.position.set(-0.132, 0.006, 0); carriage.add(objl);
  var focusKnob = S.mesh(new T.CylinderGeometry(0.013, 0.013, 0.012, 20), M.bakelite); focusKnob.rotation.x = Math.PI / 2; focusKnob.position.set(0.03, 0, 0.022); carriage.add(focusKnob);
  var mLab = S.label('TRAVELLING MICROSCOPE · LC 0.01 cm', { w: 0.08, ratio: 0.1, color: '#e3e6ea', weight: 600 });
  mLab.position.set(0.02, 0.028, 0.016); carriage.add(mLab);
  carriage.position.y = 0.26;
  S.contact(0.16, 0.14, 0.16, TZ - 0.02, 0.45);

  // ---------- the rays from the coin
  var rayMat = new T.LineBasicMaterial({ color: 0xffc15a, transparent: true, opacity: 0.75, depthWrite: false, toneMapped: false });
  var dashMat = new T.LineDashedMaterial({ color: 0xc23b30, transparent: true, opacity: 0.6, dashSize: 0.004, gapSize: 0.003, depthWrite: false, toneMapped: false });
  var rayLines = [];
  for (var ri = 0; ri < 6; ri++) { var l = new T.Line(new T.BufferGeometry(), rayMat); l.visible = false; l.renderOrder = 7; troughG.add(l); rayLines.push(l); }

  S.addApparatus('trough', troughG, 'Glass trough', 'A rectangular glass trough. ' + SAMPLE + ' is poured into it to the depth you want.');
  S.addApparatus('coin', coin, 'Coin', 'The coin lies flat on the floor of the trough and is looked at from straight above.');
  S.addApparatus('pencil', pencilG, 'Pencil', 'A pencil standing in the water looks broken at the surface, for the same reason.');
  S.addApparatus('mic', micG, 'Travelling microscope', 'Its carriage slides along a scale with a vernier, least count 0.01 cm. Focus on the coin, then on the surface: the difference is the apparent depth.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudT = S.hudCard('Real depth'), hudA = S.hudCard('Apparent depth'), hudR = S.hudCard('How much the coin rose');

  var view = null;
  function update() {
    var v = sync(); view = v;
    var t = p.t, app = v.app;
    water.scale.y = st.poured ? t : 0.0001; water.position.y = st.poured ? t / 2 + 0.004 : 0;
    surf.position.y = st.poured ? t + 0.004 : 0.004; surf.visible = st.poured;
    ghost.position.y = 0.004 + (st.poured ? t - app : 0.002); ghost.visible = st.poured && st.looked;
    // the pencil: above the surface it is straight; below it, every point appears raised, so the lower part looks tilted
    var ap = st.poured ? app : t;                                     // with no water the pencil looks straight
    var sx = PB.x - t * Math.tan(LEAN), sy = 0.004 + t;               // where the pencil crosses the surface
    pencilUp.rotation.z = LEAN;
    pencilUp.position.set(sx - Math.sin(LEAN) * UPL / 2, sy + Math.cos(LEAN) * UPL / 2, PB.z);
    var dx = sx - PB.x, dy = Math.max(0.002, ap), len = Math.hypot(dx, dy), th = Math.atan2(-dx, dy);
    pencilLow.scale.y = len; pencilLow.rotation.z = th;
    pencilLow.position.set((sx + PB.x) / 2, sy - ap / 2, PB.z);
    tip.rotation.z = th + Math.PI;
    tip.position.set(PB.x, sy - ap + 0.006, PB.z);
    rayLines.forEach(function (l) { l.visible = false; });
    if (st.poured && st.looked) {
      var n = 0;
      (v.rays || []).forEach(function (r) {
        if (n >= rayLines.length) return;
        var l = rayLines[n++]; l.material = r.v ? dashMat : rayMat;
        l.geometry.setFromPoints(r.p.map(function (q) { return new T.Vector3(-0.03 + q[0], 0.004 + t + q[1], 0); }));
        if (r.v) l.computeLineDistances();
        l.visible = true;
      });
    }
    carriage.position.y = st.focus === 'coin' ? 0.2 + (t - app) : st.focus === 'surface' ? 0.2 + t : 0.26;
    hudT.set(st.poured ? (t * 100).toFixed(1) + ' cm' : 'the trough is empty');
    hudA.set(st.poured && st.looked ? (app * 100).toFixed(2) + ' cm' : '—');
    hudR.set(st.poured && st.looked ? (v.shift * 100).toFixed(2) + ' cm' : '—');
  }

  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function pour(toCm) {
    if (S.hand.busy) return wait();
    toCm = round1(toCm);
    if (!(toCm >= 4 && toCm <= 12)) { S.say('Fill the trough between 4 cm and 12 cm deep.'); return Promise.resolve(false); }
    var from = st.poured ? st.tCm : 0;
    st.looked = false; st.focus = 'none';
    function at(k) { return from + (toCm - from) * k; }
    return S.hand.pinchMove(new T.Vector3(-TW / 2 - 0.03, 0.16, TZ), function (k) { return new T.Vector3(-TW / 2 - 0.03 + 0.02 * k, 0.16, TZ); },
      function (k) { st.poured = true; st.tCm = Math.max(0.5, at(k)); update(); }, { ms: 1100, reachMs: 600, hold: 200 })
      .then(function () { st.tCm = toCm; st.poured = true; update(); S.render();
        S.say('The trough is filled to ' + toCm.toFixed(1) + ' cm. Look down at the coin: it seems to have come up.'); return true; });
  }
  function lookDown() {
    if (S.hand.busy) return wait();
    if (!st.poured) { S.say('Pour the water in first.'); return Promise.resolve(false); }
    var v = sync();
    st.looked = true; update(); S.render(); S.focus('coin');
    S.say('Seen from straight above, the coin appears ' + (v.shift * 100).toFixed(2) + ' cm higher than it really is, and the pencil looks broken at the surface.');
    return Promise.resolve(true);
  }
  function focusOn(what) {
    if (S.hand.busy) return wait();
    if (!st.poured) { S.say('Pour the water in first.'); return Promise.resolve(false); }
    return S.hand.tap(focusKnob).then(function () {
      st.focus = what; st.looked = true; update(); S.render();
      var v = sync();
      S.say(what === 'coin' ? 'The coin is in focus. The microscope reads where the coin APPEARS to be, ' + (v.app * 100).toFixed(2) + ' cm below the surface.'
        : 'The water surface is in focus: that reading is the zero for the depth.');
      return true;
    });
  }
  function record() {
    if (S.hand.busy) { wait(); return false; }
    if (!st.poured || !st.looked) { S.say('Pour the water and focus the microscope on the coin first.'); return false; }
    var v = sync(), t = round1(st.tCm), a = round2(v.app * 100);        // the vernier reads to 0.01 cm
    if (S.rows.some(function (r) { return Math.abs(r.t - t) < 0.5; })) { S.say('You already have a reading at ' + t.toFixed(1) + ' cm. Change the depth of the water.'); return false; }
    S.addRow({ t: t, a: a });
    S.say('Written in your record book: real depth ' + t.toFixed(1) + ' cm, apparent depth ' + a.toFixed(2) + ' cm.');
    return true;
  }

  var VIEWS = { trough: [[0.26, 0.24, TZ + 0.4], [0, 0.05, TZ]], coin: [[0.0, 0.26, TZ + 0.12], [-0.03, 0.03, TZ]],
    pencil: [[0.16, 0.12, TZ + 0.26], [0.03, 0.06, TZ]], mic: [[0.3, 0.3, TZ + 0.3], [0.12, 0.2, TZ]],
    book: [[-0.4, 0.44, 0.5], [-0.5, 0.0, 0.08]] };
  update();

  function nMean(rows) {
    var ns = (rows || []).filter(function (r) { return r.a > 0; }).map(function (r) { return r.t / r.a; });
    return ns.length ? S.fit.mean(ns) : NaN;
  }

  return {
    camera: { pos: [0.44, 0.44, TZ + 0.66], look: [0.07, 0.11, TZ] },
    views: VIEWS,
    theory: { principle: 'A ray leaving the water meets the surface and bends away from the normal, because it passes into a rarer medium. The eye above follows the rays back in straight lines, so the coin seems to lie higher than it really does. Looked at from straight above, the real depth and the apparent depth are in the ratio of the refractive index.',
      formula: 'n = real depth / apparent depth',
      formulaNote: 'measured from straight above · the coin seems to rise by (real − apparent) depth',
      more: ['The same bending makes a pencil standing in a glass of water look broken at the surface, and makes a pond look shallower than it is.',
        'A travelling microscope is used because the eye alone cannot judge where the image is: focusing on the coin and then on the surface gives the apparent depth to a hundredth of a centimetre.',
        'The deeper the water, the more the coin seems to rise, but the ratio stays the same: that is the point of taking several depths.'],
      precautions: 'Keep the microscope straight above the coin; looking from the side gives a different answer. Let the water be still before focusing, and read the vernier with your eye straight on.' },
    book: { title: 'Expt. — A coin under water: apparent depth', lines: ['Aim: to find the refractive index from the real and apparent depths.',
      'The coin lies on the floor of the trough; the microscope looks straight down.', 'Real depth = depth of the water.',
      'Apparent depth = where the coin appears, below the surface.', 'n = real depth / apparent depth.'],
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Real depth (cm)', get: function (r) { return r.t.toFixed(1); } },
        { label: 'Apparent (cm)', get: function (r) { return r.a.toFixed(2); } }, { label: 'Risen by (cm)', get: function (r) { return (r.t - r.a).toFixed(2); } },
        { label: 'n', get: function (r) { return (r.t / r.a).toFixed(3); } }] },
    graph: { x: function (r) { return r.a; }, y: function (r) { return r.t; }, xlabel: 'apparent depth (cm)', ylabel: 'real depth (cm)', x0: 0, y0: 0,
      line: function (pts) { var m = S.fit.origin(pts); return isFinite(m) ? function (x) { return m * x; } : null; } },
    result: function (rows) {
      var n = nMean(rows); if (!isFinite(n) || (rows || []).length < 2) return null;
      return { label: 'n', value: n, unit: '', digits: 3, truth: p.n,
        note: 'Mean of real depth ÷ apparent depth. The graph of real against apparent depth is a straight line through the origin of slope n.' };
    },
    tol: 0.02,
    chips: ['Why does the coin look raised?', 'Why does the pencil look bent?', 'Why look from straight above?', 'Check my readings', 'Is a pond deeper than it looks?'],
    viva: [['A pond 2 m deep, seen from above, appears about?', ['1.5 m deep', '2.7 m deep', 'Exactly 2 m deep'], 0, '2 ÷ 1.33 = 1.5 m.'],
      ['The coin appears raised because the ray, on leaving the water,', ['bends away from the normal', 'bends towards the normal', 'is reflected'], 0, 'It passes into a rarer medium.'],
      ['If the water is made deeper, the apparent depth?', ['Also grows, in the same ratio', 'Stays the same', 'Gets smaller'], 0, 'Apparent = real ÷ n always.']],
    askState: function () {
      var v = view || sync();
      return { liquid: SAMPLE, water_poured: st.poured, real_depth_cm: +(p.t * 100).toFixed(1),
        apparent_depth_cm: st.looked ? +(v.app * 100).toFixed(2) : null, coin_risen_cm: st.looked ? +(v.shift * 100).toFixed(2) : null,
        microscope_focused_on: st.focus, readings_taken: S.rows.length };
    },

    steps: [
      { id: 'look', title: 'The coin and the pencil', view: 'trough', render: function (u) {
          u.h2('Pour the water and look from above');
          u.p('The coin is lying on the floor of the empty trough. Pour water in and look straight down at it: the coin seems to have come up. The pencil standing in the water looks broken at the surface for the same reason.');
          u.task('1. Pour the water in', st.poured, st.poured ? 'Filled to ' + st.tCm.toFixed(1) + ' cm' : 'The trough is empty');
          u.slider('Depth of the water', 4, 12, 0.5, function () { return st.tSet; }, function (x) { st.tSet = x; }, 'cm', 1);
          u.row(u.button('Pour to that depth', function () { pour(st.tSet); S.render(); }, true, S.hand.busy));
          u.task('2. Look straight down at the coin', st.looked, st.looked ? 'It appears raised' : 'Not looked yet')
            .add(u.button('Look down at the coin', function () { lookDown(); }, !st.looked, S.hand.busy || !st.poured));
          u.live(function () { var v = view || sync(); return st.looked ? 'The coin appears ' + (v.shift * 100).toFixed(2) + ' cm higher than it is' : 'Pour the water and look'; });
          u.row(u.button('Look at the pencil', function () { S.focus('pencil'); }));
          u.note('Look from the side instead and the coin seems to move: that is why the measurement is always made from straight above.');
          u.next('Next: measure with the microscope', st.poured && st.looked);
        },
        ok: function () { return st.poured && st.looked; },
        auto: function () { return pour(8).then(function () { return lookDown(); }); } },
      { id: 'measure', title: 'Measure the apparent depth', view: 'mic', render: function (u) {
          u.h2('Focus the microscope and take the readings');
          u.p('Focus the microscope on the coin, then on the water surface. The difference between the two readings is the apparent depth, and the depth of the water itself is the real depth. Take at least two depths.');
          u.task('Focus on the coin', st.focus === 'coin', st.focus === 'coin' ? 'The coin is in focus' : 'Turn the focusing knob')
            .add(u.button('Focus on the coin', function () { focusOn('coin'); }, st.focus !== 'coin', S.hand.busy || !st.poured));
          u.task('Focus on the surface', st.focus === 'surface', st.focus === 'surface' ? 'The surface is in focus' : 'A little chalk powder on the water makes it easy to see')
            .add(u.button('Focus on the surface', function () { focusOn('surface'); }, st.focus !== 'surface', S.hand.busy || !st.poured));
          u.live(function () { var v = view || sync(); return 'Real depth ' + (p.t * 100).toFixed(1) + ' cm · apparent depth ' + (v.app * 100).toFixed(2) + ' cm'; });
          u.row(u.button('Record this depth', function () { record(); }, true, S.hand.busy));
          u.slider('Change the depth of the water', 4, 12, 0.5, function () { return st.tSet; }, function (x) { st.tSet = x; }, 'cm', 1);
          u.row(u.button('Pour to that depth', function () { pour(st.tSet); S.render(); }, false, S.hand.busy));
          u.h3('Observation table'); u.table();
          u.next('Next: graph and result', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 depths recorded.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          return [6, 8, 10, 12].reduce(function (pr, t) {
            return pr.then(function () { st.tSet = t; return pour(t); }).then(function () { return focusOn('coin'); }).then(function () { record(); });
          }, Promise.resolve());
        } },
    ],

    tick: function () { update(); },
  };
});
