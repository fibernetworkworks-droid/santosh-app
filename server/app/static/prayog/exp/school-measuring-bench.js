/* Prayogshala studio module: the school measuring bench (NCERT Class VI, Measurement).
   One rig, three set-ups - the lab id picks the mode:
     school-length-nonstandard   lay a hand span / cubit / foot step along a strip of cloth
     school-length-ruler         measure a rod on the metre scale, with the eye right above the mark
     school-length-curve         lay a thread along a curved line, then straighten it on the scale
   Physics: the length_measure kernel from the wave_heat_school pack - the same numbers the server checks. The
   true length L is hidden; the reading is the length rounded to the method's least count. */
HoolaStudio.define('school-measuring-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.length_measure;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('length_measure');
  var ID = String(S.lab.rig === S.lab.id ? S.lab.id : (S.lab.variant && S.lab.variant.base) || S.lab.id);
  var MODE = /nonstandard/.test(ID) ? 'span' : /curve/.test(ID) ? 'curve' : 'ruler';
  var LTRUE = p.L;                                   // hidden from the student, used only to lay out the apparatus

  // the body units of the Class VI activity (a hand span, a cubit and a foot step differ from person to person)
  var UNITS = [{ key: 'span', name: 'hand span', unit: 0.22, lc: 0.055, note: 'the spread of your palm, little finger to thumb' },
    { key: 'cubit', name: 'cubit', unit: 0.45, lc: 0.1125, note: 'elbow to the tip of the middle finger' },
    { key: 'foot', name: 'foot step', unit: 0.60, lc: 0.15, note: 'one step, heel to heel' }];
  if (MODE === 'span') {                             // the lab's own unit leads the list (a variant may change it)
    var same = null, i0;
    for (i0 = 0; i0 < UNITS.length; i0++) if (Math.abs(UNITS[i0].unit - p.unit) < 0.005) same = UNITS[i0];
    if (!same) UNITS.unshift({ key: 'own', name: 'this unit', unit: p.unit, lc: p.lc, note: 'the unit printed on the card' });
    else UNITS.splice(UNITS.indexOf(same), 1), UNITS.unshift(same);
  }
  var st = { ui: 0, unit: MODE === 'span' ? UNITS[0] : null, laid: 0, marks: [], par: 0, placed: MODE !== 'ruler',
    start: 0, threadOn: 0, threadStraight: false, marked: false, note: '' };

  function readingFor(unit, lc, par) { p.unit = unit; p.lc = lc; p.par = par || 0; return K.view({ t: 0 }, p); }
  function cm(v) { return (v * 100).toFixed(1); }

  // ---------------------------------------------------------------- apparatus
  var BZ = -0.12, BOARD_H = 0.012, TOPY = BOARD_H;
  var board = new T.Group(); S.scene.add(board);
  var bw = S.rounded(Math.max(1.1, LTRUE + 0.14), 0.46, BOARD_H, 0.006, M.darkWood);
  bw.rotation.x = -Math.PI / 2; bw.position.set(0, BOARD_H / 2, BZ); board.add(bw);
  S.contact(Math.max(1.2, LTRUE + 0.2), 0.52, 0, BZ, 0.5);
  var blab = S.label('MEASURING BENCH', { w: 0.1, ratio: 0.13, color: '#e8d6b0' });
  blab.rotation.x = -Math.PI / 2; blab.position.set(-0.42, TOPY + 0.0006, BZ + 0.2); board.add(blab);

  // the metre scale, lying flat: a wooden strip with a printed cm / mm face, zero at x = X0
  var X0 = -0.5, SL = 1.0, SZ = 0.05;
  var scaleTex = S.canvasTex(4096, 220, function (x, w, h) {
    x.drawImage(S.woodTex.image, 0, 0, w, h);
    x.fillStyle = 'rgba(252,247,232,.92)'; x.fillRect(0, 0, w, h);
    var mm = 1000, k = w / mm;
    // the strip lies flat on the bench, so the texture reaches the reader turned about: the layout is mirrored
    // once and every glyph is turned back, which puts the numbers upright and in order for the camera
    function txt(str, px, py, align) { x.save(); x.textAlign = align || 'center'; x.fillText(str, px, py); x.restore(); }
    x.fillStyle = '#17171a';
    for (var i = 0; i <= mm; i++) {
      var xx = i * k, big = i % 10 === 0, mid = i % 5 === 0;
      x.fillRect(xx - (big ? 1.6 : 0.8), 0, big ? 3.2 : 1.6, big ? 74 : mid ? 52 : 32);
      if (big) { x.font = '600 44px "Public Sans", sans-serif'; txt(String(i / 10), xx, 118); }
    }
    x.font = '600 40px "Public Sans", sans-serif';
    x.fillStyle = '#6b4a14'; txt('METRE SCALE  ·  centimetres and millimetres  ·  least count 1 mm', 60, 180, 'left');
  });
  var scaleGrp = new T.Group(); S.scene.add(scaleGrp);
  var scaleBody = S.rounded(SL, 0.034, 0.007, 0.002, M.wood); scaleBody.rotation.x = -Math.PI / 2;
  scaleBody.position.set(X0 + SL / 2, TOPY + 0.0035, SZ); scaleGrp.add(scaleBody);
  var scaleFace = new T.Mesh(new T.PlaneGeometry(SL, 0.032), new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.55 }));
  scaleFace.rotation.x = -Math.PI / 2; scaleFace.position.set(X0 + SL / 2, TOPY + 0.0072, SZ); scaleGrp.add(scaleFace);

  // the object being measured
  var objZ = -0.1, obj = new T.Group(); S.scene.add(obj);
  var cloth = null, rod = null, card = null, curve = null, thread = null, threadMesh = null;
  var ARC = { R: 0.2, th: 2.4, cx: 0, cz: objZ, a0: 0 };

  function clothTex() {
    return S.canvasTex(1024, 128, function (x, w, h) {
      x.fillStyle = '#c3453c'; x.fillRect(0, 0, w, h);
      var i, j;
      for (i = 0; i < w; i += 7) { x.fillStyle = 'rgba(255,255,255,.07)'; x.fillRect(i, 0, 3, h); }
      for (j = 0; j < h; j += 7) { x.fillStyle = 'rgba(0,0,0,.07)'; x.fillRect(0, j, w, 3); }
      x.fillStyle = '#f0e2c8'; x.fillRect(0, 0, w, 6); x.fillRect(0, h - 6, w, 6);
    });
  }
  if (MODE === 'span') {
    var cm2 = new T.MeshStandardMaterial({ map: clothTex(), roughness: 0.9 });
    cloth = S.mesh(new T.BoxGeometry(LTRUE, 0.0022, 0.075), cm2);
    cloth.position.set(0, TOPY + 0.0011, objZ); obj.add(cloth);
    [-1, 1].forEach(function (s) {
      var f = S.mesh(new T.BoxGeometry(0.008, 0.0015, 0.075), new T.MeshStandardMaterial({ color: 0xf0e2c8, roughness: 0.95 }));
      f.position.set(s * (LTRUE / 2 + 0.004), TOPY + 0.0009, objZ); obj.add(f);
    });
    var cl = S.label('STRIP OF CLOTH', { w: 0.08, ratio: 0.14, color: '#fdf3df' });
    cl.rotation.x = -Math.PI / 2; cl.position.set(0, TOPY + 0.0024, objZ - 0.028); obj.add(cl);
  } else if (MODE === 'ruler') {
    rod = new T.Group(); obj.add(rod);
    var body = S.mesh(new T.CylinderGeometry(0.0062, 0.0062, LTRUE, 20), new T.MeshStandardMaterial({ color: 0xc08a3e, roughness: 0.6 }));
    body.rotation.z = Math.PI / 2; rod.add(body);
    [-1, 1].forEach(function (s) {
      var cap = S.mesh(new T.CylinderGeometry(0.0064, 0.0064, 0.008, 20), M.brass);
      cap.rotation.z = Math.PI / 2; cap.position.x = s * (LTRUE / 2 - 0.004); rod.add(cap);
    });
    rod.position.set(0, TOPY + 0.0062, objZ);
    var rl = S.label('WOODEN ROD', { w: 0.06, ratio: 0.16, color: '#6b4a14' });
    rl.rotation.x = -Math.PI / 2; rl.position.set(0, TOPY + 0.0005, objZ - 0.03); obj.add(rl);
  } else {
    ARC.R = Math.max(0.12, Math.min(0.3, LTRUE / 2.4)); ARC.th = LTRUE / ARC.R;
    ARC.a0 = -ARC.th / 2;
    var chord = 2 * ARC.R * Math.sin(Math.min(Math.PI / 2, ARC.th / 2)), sag = ARC.R * (1 - Math.cos(Math.min(Math.PI, ARC.th / 2)));
    var cw = Math.min(1.0, chord + 0.1), cd = Math.min(0.4, Math.max(0.2, sag + 0.09));
    ARC.cz = objZ - 0.02 - sag / 2 + sag / 2;
    var inkTex = S.canvasTex(1024, Math.round(1024 * cd / cw), function (x, w, h) {
      x.fillStyle = '#f7f3e6'; x.fillRect(0, 0, w, h);
      x.strokeStyle = '#d8cfb6'; x.lineWidth = 3; x.strokeRect(8, 8, w - 16, h - 16);
      x.strokeStyle = '#1b3a6b'; x.lineWidth = 7; x.lineCap = 'round'; x.beginPath();
      for (var i = 0; i <= 200; i++) {
        var a = ARC.a0 + ARC.th * i / 200, px = (ARC.R * Math.sin(a)) / cw * w + w / 2, py = h / 2 - (ARC.R * Math.cos(a) - ARC.R) / cd * h;
        if (i) x.lineTo(px, py); else x.moveTo(px, py);
      }
      x.stroke();
      x.fillStyle = '#1b3a6b'; x.font = '600 34px "Public Sans", sans-serif';
      x.fillText('A', (ARC.R * Math.sin(ARC.a0)) / cw * w + w / 2 - 34, h / 2 - (ARC.R * Math.cos(ARC.a0) - ARC.R) / cd * h + 10);
      x.fillText('B', (ARC.R * Math.sin(ARC.a0 + ARC.th)) / cw * w + w / 2 + 12, h / 2 - (ARC.R * Math.cos(ARC.a0 + ARC.th) - ARC.R) / cd * h + 10);
    });
    card = new T.Group(); obj.add(card);
    var cb = S.rounded(cw, cd, 0.004, 0.004, M.paper); cb.rotation.x = -Math.PI / 2; cb.position.set(0, TOPY + 0.002, ARC.cz); card.add(cb);
    var cf = new T.Mesh(new T.PlaneGeometry(cw, cd), new T.MeshStandardMaterial({ map: inkTex, roughness: 0.85 }));
    cf.rotation.x = -Math.PI / 2; cf.position.set(0, TOPY + 0.0042, ARC.cz); card.add(cf);
    ARC.cx = 0; ARC.cz = ARC.cz;
    curve = card;
  }
  // the thread and its ink mark (used by the curve set-up; it rests on the bench otherwise)
  var threadM = new T.MeshStandardMaterial({ color: 0xf6f1e2, roughness: 0.95 });
  threadMesh = S.mesh(new T.BufferGeometry(), threadM, false, false); S.scene.add(threadMesh);
  var knot = S.mesh(new T.SphereGeometry(0.0032, 14, 10), threadM); S.scene.add(knot);
  var inkMark = S.mesh(new T.SphereGeometry(0.0032, 12, 10), new T.MeshStandardMaterial({ color: 0x1b3a6b, roughness: 0.6 }));
  inkMark.visible = false; S.scene.add(inkMark);
  var spool = new T.Group(); S.scene.add(spool);
  var sp1 = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.022, 24), new T.MeshStandardMaterial({ color: 0xe9e2cf, roughness: 0.9 }));
  sp1.rotation.z = Math.PI / 2; spool.add(sp1); spool.position.set(0.58, TOPY + 0.018, 0.14);
  S.contact(0.06, 0.05, 0.58, 0.14, 0.4);

  function arcPoint(k) {                            // k = 0..1 along the curved line, in world space
    var a = ARC.a0 + ARC.th * k;
    return new T.Vector3(ARC.cx + ARC.R * Math.sin(a), TOPY + 0.006, ARC.cz - (ARC.R * Math.cos(a) - ARC.R));
  }
  function setThread(frac, straight) {
    var pts = [], i, n = 60;
    if (straight) {
      var len = p.L + st.par;
      for (i = 0; i <= 2; i++) pts.push(new T.Vector3(X0 + len * i / 2, TOPY + 0.0098, SZ - 0.026));
    } else if (MODE === 'curve') {
      if (frac <= 0.001) { threadMesh.visible = false; knot.visible = false; return; }
      for (i = 0; i <= n; i++) pts.push(arcPoint(frac * i / n));
    } else { threadMesh.visible = false; knot.visible = false; return; }
    threadMesh.visible = true; knot.visible = true;
    knot.position.copy(pts[0]);
    threadMesh.geometry.dispose();
    threadMesh.geometry = new T.TubeGeometry(new T.CatmullRomCurve3(pts), Math.max(24, pts.length * 2), 0.0012, 8, false);
  }
  threadMesh.visible = false; knot.visible = false;

  // the marks the hand chalks on the cloth, one for each unit laid
  var markMats = new T.MeshStandardMaterial({ color: 0xf7f7f2, roughness: 0.85 });
  var markMeshes = [];
  function showMarks(n, unit) {
    var i;
    for (i = 0; i < markMeshes.length; i++) markMeshes[i].visible = false;
    for (i = 1; i <= n; i++) {
      var m = markMeshes[i - 1];
      if (!m) { m = S.mesh(new T.BoxGeometry(0.0022, 0.0012, 0.079), markMats, false); S.scene.add(m); markMeshes[i - 1] = m; }
      m.visible = true; m.position.set(-LTRUE / 2 + unit * i, TOPY + 0.0028, objZ);
    }
  }
  // a pointer that shows which mark on the scale is being read
  var pointer = S.mesh(new T.ConeGeometry(0.006, 0.018, 14), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.4 }));
  pointer.rotation.x = Math.PI; pointer.position.set(X0, TOPY + 0.02, SZ - 0.03); pointer.visible = false; S.scene.add(pointer);

  S.addApparatus('scale', scaleGrp, 'Metre scale', 'A wooden metre scale with centimetre and millimetre divisions: its least count is 1 mm.');
  if (MODE === 'span') S.addApparatus('obj', obj, 'Strip of cloth', 'The length to be measured. Its true length is hidden: you measure it with your own body units.');
  if (MODE === 'ruler') S.addApparatus('obj', obj, 'Wooden rod', 'The rod to be measured. Lay it along the scale with one end on a clear mark.');
  if (MODE === 'curve') { S.addApparatus('obj', obj, 'Card with the curved line', 'The ink line from A to B curves, so a straight scale cannot measure it.');
    S.addApparatus('thread', spool, 'Thread and spool', 'Light thread that does not stretch. Laid along the line, marked with ink, then straightened on the scale.'); }
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudR = S.hudCard(MODE === 'span' ? 'Units laid' : 'Reading'), hudN = S.hudCard('Readings');

  // ---------------------------------------------------------------- actions
  function layUnits() {                              // the hand walks the unit along the cloth, marking as it goes
    if (S.hand.busy) return Promise.resolve();
    var u = st.unit, n = Math.floor(LTRUE / u.unit + 1e-9), frac = LTRUE / u.unit - n;
    st.laid = 0; showMarks(0, u.unit);
    var pr = Promise.resolve();
    function leg(i) {
      return function () {
        var from = new T.Vector3(-LTRUE / 2 + u.unit * (i - 1), TOPY + 0.02, objZ), to = new T.Vector3(-LTRUE / 2 + u.unit * i, TOPY + 0.02, objZ);
        return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); }, function () {}, { ms: 520, pose: 'open', reachMs: 420 })
          .then(function () { st.laid = i; showMarks(i, u.unit); S.click(900, 0.03, 0.05); });
      };
    }
    for (var i = 1; i <= n; i++) pr = pr.then(leg(i));
    return pr.then(function () {
      var v = readingFor(u.unit, u.lc, 0);
      st.note = n + ' whole ' + u.name + (n === 1 ? '' : 's') + (frac > 0.02 ? ' and about ' + (Math.round(frac * 4) / 4) + ' more' : '');
      S.say('Laid ' + st.note + ' along the cloth: ' + (v.reading / u.unit).toFixed(2) + ' ' + u.name + 's in all.');
      S.render();
    });
  }
  function recordSpan() {
    var u = st.unit;
    if (st.laid < 1) { S.say('Lay the ' + u.name + ' along the cloth first.'); return; }
    for (var i = S.rows.length - 1; i >= 0; i--) if (S.rows[i].key === u.key) S.rows.splice(i, 1);
    var v = readingFor(u.unit, u.lc, 0);
    S.rows.push({ key: u.key, name: u.name, unit: u.unit, units: v.reading / u.unit, reading: v.reading });
    S.book.draw();
    S.say('Written: ' + (v.reading / u.unit).toFixed(2) + ' ' + u.name + 's = ' + cm(v.reading) + ' cm, because one ' + u.name + ' is ' + cm(u.unit) + ' cm.');
    S.render();
  }
  function pickUnit(key) {
    if (S.hand.busy) return;
    for (var i = 0; i < UNITS.length; i++) if (UNITS[i].key === key) st.unit = UNITS[i];
    st.laid = 0; showMarks(0, st.unit.unit);
    S.say('Now measuring with your ' + st.unit.name + ' (' + st.unit.note + ').'); S.render();
  }

  function placeRod(startCm) {                        // slide the rod so its left end sits on a chosen mark
    if (S.hand.busy) return Promise.resolve();
    var fromX = rod.position.x, toX = X0 + startCm / 100 + LTRUE / 2;
    var gy = TOPY + 0.016;
    return S.hand.pinchMove(new T.Vector3(fromX, gy, objZ), function (k) { return new T.Vector3(fromX + (toX - fromX) * k, gy, objZ); },
      function (k) { rod.position.set(fromX + (toX - fromX) * k, TOPY + 0.0062, objZ + (SZ - 0.02 - objZ) * k); }, { ms: 900 })
      .then(function () { rod.position.set(toX, TOPY + 0.0062, SZ - 0.02); st.placed = true; st.start = startCm;
        S.say('The rod now starts at the ' + startCm + ' cm mark. Read the mark at its other end.'); S.render(); });
  }
  function readScale() {
    if (S.hand.busy) return Promise.resolve();
    var v = readingFor(p.unit, p.lc, st.par);
    var at = (MODE === 'ruler' ? st.start / 100 : 0) + v.reading;
    pointer.visible = true; pointer.position.set(X0 + at, TOPY + 0.02, SZ - 0.03);
    return S.hand.reach(new T.Vector3(X0 + at, TOPY + 0.03, SZ - 0.04), 'tap', 600).then(function () { return S.hand.away(400); })
      .then(function () {
        S.say(st.par ? 'From the side the end seems to fall at ' + cm(v.reading) + ' cm. Bring your eye straight above the mark.'
          : 'The far end falls at ' + cm(at) + ' cm, so the length is ' + cm(v.reading) + ' cm.');
        S.render();
      });
  }
  function recordScale() {
    if (MODE === 'ruler' && !st.placed) { S.say('Lay the rod along the scale first.'); return; }
    if (st.par) { S.say('That reading was taken from the side, so it carries a parallax error. Put the eye straight above the mark and read again.'); return; }
    if (MODE === 'curve' && !st.threadStraight) { S.say('Straighten the thread along the scale first.'); return; }
    var v = readingFor(p.unit, p.lc, 0);
    S.rows.push({ key: 'r' + (S.rows.length + 1), name: MODE === 'curve' ? 'thread on the scale' : 'from the ' + st.start + ' cm mark',
      unit: p.unit, units: v.reading / p.unit, reading: v.reading, start: st.start });
    S.book.draw(); S.say('Written: ' + cm(v.reading) + ' cm.'); S.render();
  }
  function setEye(side) { st.par = side ? p.par || 0.003 : 0; pointer.visible = false; S.say(side ? 'Eye to one side: watch the mark shift.' : 'Eye straight above the mark.'); S.render(); }

  function layThread() {
    if (S.hand.busy) return Promise.resolve();
    st.threadStraight = false; st.marked = false; setThread(0, false);
    var a = arcPoint(0);
    return S.hand.pinchMove(a.clone().add(new T.Vector3(0, 0.03, 0)), function (k) { return arcPoint(k).add(new T.Vector3(0, 0.012, 0)); },
      function (k) { setThread(Math.max(0.001, k), false); }, { ms: 2200, pose: 'point' })
      .then(function () { setThread(1, false); st.threadOn = 1;
        S.say('The thread lies along the line from A to B, following every bend. Now mark it with ink at B.'); S.render(); });
  }
  function markThread() {
    if (S.hand.busy) return Promise.resolve();
    if (st.threadOn < 1) { S.say('Lay the thread along the line first.'); return Promise.resolve(); }
    var b = arcPoint(1);
    S.hand.busy = true;
    return S.hand.shape('point', 180).then(function () { return S.hand.reach(b.clone().add(new T.Vector3(0, 0.012, 0)), 'tap', 520); })
      .then(function () { return S.hand.reach(b, 'tap', 160); })
      .then(function () { inkMark.visible = true; inkMark.position.copy(b); S.click(1200, 0.03, 0.04); return S.hand.away(420); })
      .then(function () {
        S.hand.busy = false; st.marked = true;
        S.say('Ink mark made where the line ends. The thread between the knot and the mark is the length of the line.'); S.render();
      }, function () { S.hand.busy = false; inkMark.visible = true; inkMark.position.copy(b); st.marked = true; });
  }
  function straighten() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.marked) { S.say('Mark the thread at B first, or you will not know where to read.'); return Promise.resolve(); }
    var from = arcPoint(0), to = new T.Vector3(X0, TOPY + 0.012, SZ - 0.026);
    return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); }, function (k) { if (k > 0.5) { setThread(1, true); } }, { ms: 1200 })
      .then(function () { setThread(1, true); st.threadStraight = true; inkMark.position.set(X0 + p.L, TOPY + 0.0098, SZ - 0.026);
        S.say('The thread is straight along the scale, knot on zero. Read the scale at the ink mark.'); S.render(); });
  }

  function mean(rows) { var s = 0, n = 0; rows.forEach(function (r) { if (isFinite(r.reading)) { s += r.reading; n++; } }); return n ? s / n : NaN; }

  // ---------------------------------------------------------------- steps
  var spanSteps = [
    { id: 'span1', title: 'Hand span', view: 'obj', render: function (u) {
        u.h2('Measure the cloth with your ' + st.unit.name);
        u.p('Lay the unit along the cloth end to end, with no gap and no overlap, and chalk a mark each time. Count the whole units, then estimate the last part.');
        var r = u.row();
        UNITS.forEach(function (un) { r.appendChild(u.button((st.unit.key === un.key ? '✓ ' : '') + un.name, function () { pickUnit(un.key); }, false, S.hand.busy)); });
        u.note('One ' + st.unit.name + ' here is ' + cm(st.unit.unit) + ' cm - ' + st.unit.note + '. Your own is not the same as your friend\'s.');
        u.row(u.button('Lay the ' + st.unit.name + ' along the cloth', function () { layUnits(); S.render(); }, true, S.hand.busy),
          u.button('Record this reading', function () { recordSpan(); }, false, st.laid < 1 || S.hand.busy));
        u.live(function () { return st.laid ? st.laid + ' whole ' + st.unit.name + (st.laid === 1 ? '' : 's') + ' laid' + (st.note ? ' · ' + st.note : '') : 'Nothing laid along the cloth yet'; });
        u.h3('Observation table'); u.table();
        u.next('Next: try another unit', S.rows.length >= 1);
      },
      ok: function () { return S.rows.length >= 1; },
      auto: function () { pickUnit(UNITS[0].key); return layUnits().then(function () { recordSpan(); }); } },
    { id: 'span2', title: 'Other units', view: 'obj', render: function (u) {
        u.h2('Now a cubit and a foot step');
        u.p('The same cloth, a different unit: the number of units changes but the cloth does not. Measure it with at least one more unit.');
        var r = u.row();
        UNITS.forEach(function (un) { r.appendChild(u.button((st.unit.key === un.key ? '✓ ' : '') + un.name, function () { pickUnit(un.key); }, false, S.hand.busy)); });
        u.row(u.button('Lay the ' + st.unit.name + ' along the cloth', function () { layUnits(); S.render(); }, true, S.hand.busy),
          u.button('Record this reading', function () { recordSpan(); }, false, st.laid < 1 || S.hand.busy));
        u.live(function () { return S.rows.length + ' unit' + (S.rows.length === 1 ? '' : 's') + ' recorded'; });
        u.h3('Observation table'); u.table();
        u.next('Next: work out the length', S.rows.length >= 2);
      },
      ok: function () { return S.rows.length >= 2; },
      auto: function () {
        var rest = UNITS.slice(1, 3), pr = Promise.resolve();
        rest.forEach(function (un) { pr = pr.then(function () { pickUnit(un.key); return layUnits(); }).then(function () { recordSpan(); }); });
        return pr; } },
  ];
  var rulerSteps = [
    { id: 'place', title: 'Lay the rod', view: 'scale', render: function (u) {
        u.h2('Lay the rod along the scale');
        u.p('Never measure from the worn end of a scale. Put one end of the rod exactly on a clear centimetre mark and read the mark at the other end.');
        u.row(u.button('Start at 0 cm', function () { placeRod(0); S.render(); }, st.start !== 0, S.hand.busy),
          u.button('Start at 5 cm', function () { placeRod(5); S.render(); }, false, S.hand.busy),
          u.button('Start at 10 cm', function () { placeRod(10); S.render(); }, false, S.hand.busy));
        u.live(function () { return st.placed ? 'The rod starts at the ' + st.start + ' cm mark' : 'The rod is still lying away from the scale'; });
        u.next('Next: read the scale', st.placed);
      },
      ok: function () { return st.placed; },
      auto: function () { return placeRod(0); } },
    { id: 'read', title: 'Read and record', view: 'read', render: function (u) {
        u.h2('Eye straight above the mark');
        u.p('Looking from the side shifts the mark: that is parallax error. Bring your eye vertically above the end of the rod, then read the centimetres and the millimetres after them.');
        u.row(u.button((st.par ? '' : '✓ ') + 'Eye straight above', function () { setEye(false); }, !st.par, S.hand.busy),
          u.button((st.par ? '✓ ' : '') + 'Eye to one side', function () { setEye(true); }, false, S.hand.busy));
        u.row(u.button('Read the scale', function () { readScale(); S.render(); }, true, S.hand.busy),
          u.button('Record this reading', function () { recordScale(); }, false, !st.placed || !!st.par || S.hand.busy));
        u.live(function () { var v = readingFor(p.unit, p.lc, st.par); return 'Scale shows ' + cm(v.reading) + ' cm' + (st.par ? ' (eye to the side: wrong)' : ''); });
        u.note('Take the measurement twice, from two different starting marks, and average the two.');
        u.h3('Observation table'); u.table();
        u.next('Next: work out the length', S.rows.length >= 2);
      },
      ok: function () { return S.rows.length >= 2; },
      auto: function () { setEye(false);
        return readScale().then(function () { recordScale(); return placeRod(5); }).then(readScale).then(function () { recordScale(); }); } },
  ];
  var curveSteps = [
    { id: 'lay', title: 'Lay the thread', view: 'obj', render: function (u) {
        u.h2('Lay the thread along the line');
        u.p('Hold the knot at A and press the thread down along the ink line with your finger, following every bend. Then mark the thread with ink where the line ends at B.');
        u.row(u.button('Lay the thread along the line', function () { layThread(); S.render(); }, true, S.hand.busy),
          u.button('Mark the thread at B', function () { markThread(); S.render(); }, false, st.threadOn < 1 || S.hand.busy));
        u.live(function () { return st.marked ? 'Thread laid and marked at B' : st.threadOn ? 'Thread laid from A to B, not yet marked' : 'Thread still on the spool'; });
        u.note('Do not stretch the thread: a stretched thread is longer than the line and the answer comes out too large.');
        u.next('Next: straighten it on the scale', st.marked);
      },
      ok: function () { return st.marked; },
      auto: function () { return layThread().then(markThread); } },
    { id: 'read', title: 'Read on the scale', view: 'scale', render: function (u) {
        u.h2('Straighten the thread on the scale');
        u.p('Put the knot on the zero mark, hold the thread straight along the scale and read the mark at the ink. Lay the thread again and read a second time.');
        u.row(u.button('Straighten it on the scale', function () { straighten(); S.render(); }, true, !st.marked || S.hand.busy),
          u.button('Read the scale', function () { readScale(); S.render(); }, false, !st.threadStraight || S.hand.busy),
          u.button('Record this reading', function () { recordScale(); }, false, !st.threadStraight || S.hand.busy));
        u.live(function () { return st.threadStraight ? 'Thread straight on the scale: ' + cm(readingFor(p.unit, p.lc, 0).reading) + ' cm' : 'Thread not on the scale yet'; });
        u.row(u.button('Lay the thread along the line again', function () { layThread().then(markThread); S.render(); }, false, S.hand.busy));
        u.h3('Observation table'); u.table();
        u.next('Next: work out the length', S.rows.length >= 2);
      },
      ok: function () { return S.rows.length >= 2; },
      auto: function () {
        return straighten().then(readScale).then(function () { recordScale(); return layThread(); }).then(markThread)
          .then(straighten).then(readScale).then(function () { recordScale(); }); } },
  ];

  var bookCols = MODE === 'span'
    ? [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'Unit used', get: function (r) { return r.name; } },
      { label: 'Units counted', get: function (r) { return r.units.toFixed(2); } },
      { label: 'One unit (cm)', get: function (r) { return cm(r.unit); } },
      { label: 'Length (cm)', get: function (r) { return cm(r.reading); } }]
    : [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'Measured', get: function (r) { return r.name; } },
      { label: 'Length (cm)', get: function (r) { return cm(r.reading); } },
      { label: 'In mm', get: function (r) { return (r.reading * 1000).toFixed(0); } }];

  return {
    camera: MODE === 'span' ? { pos: [0.34, 0.95, 1.62], look: [0, 0.0, -0.06] }
      : MODE === 'curve' ? { pos: [0.3, 0.86, 1.45], look: [0, 0.0, -0.08] } : { pos: [0.26, 0.8, 1.3], look: [-0.04, 0.0, -0.04] },
    views: { obj: MODE === 'span' ? [[0.18, 0.78, 1.15], [0, 0.01, -0.1]] : [[0.1, 0.6, 0.85], [0, 0.01, -0.12]],
      scale: [[-0.24, 0.52, 0.72], [-0.3, 0.01, 0.0]], read: [[-0.16, 0.34, 0.46], [-0.28, 0.012, 0.02]],
      thread: [[0.56, 0.34, 0.52], [0.58, 0.02, 0.13]],
      book: [[-0.8, 0.6, 0.66], [-0.84, 0.0, 0.1]] },
    theory: { principle: MODE === 'span'
        ? 'A length can be measured with any unit, but a hand span, a cubit and a foot step are different for every person, so the same cloth gives a different number to each of us. That is why one standard unit, the metre, was agreed upon.'
        : MODE === 'curve'
          ? 'A straight scale cannot follow a curve. A thread can: laid along the line it takes up the same length, and straightened on the scale that length can be read.'
          : 'A metre scale carries millimetre divisions, so its least count is 1 mm. Start from a clear mark, not the worn end, keep the eye vertically above the mark being read, and subtract the starting mark from the finishing mark.',
      formula: MODE === 'span' ? 'length = (number of units) × (size of one unit)' : 'length = finishing mark − starting mark',
      formulaNote: MODE === 'span' ? 'the bigger the unit, the smaller the number of units' : 'least count of a metre scale = 1 mm',
      more: MODE === 'ruler' ? ['Looking from one side makes the mark appear shifted. This parallax error is removed by bringing the eye straight above the mark.',
        'Measure twice, from two different starting marks, and take the average.']
        : MODE === 'curve' ? ['The thread must not stretch. Thread that stretches gives a length longer than the line.']
          : ['Record both the number of units and the size of the unit, or the reading cannot be shared with anybody.'],
      precautions: MODE === 'span' ? 'Lay the units end to end, without gaps and without overlapping, and estimate the last part of a unit to the nearest quarter.'
        : MODE === 'curve' ? 'Hold the knot exactly at A, follow every bend, do not stretch the thread, and put the knot on the zero mark when you read.'
          : 'Never measure from a broken end of the scale. Keep the rod touching the scale and the eye straight above the mark.' },
    book: { title: MODE === 'span' ? 'Expt. — Measuring with non-standard units' : MODE === 'curve' ? 'Expt. — Length of a curved line' : 'Expt. — Measuring length with a scale',
      lines: MODE === 'span'
        ? ['Aim: to measure a length with body units and see why they cannot be shared.', 'length = units counted × size of one unit',
          'Hand span ' + cm(UNITS[0].unit) + ' cm, cubit 45.0 cm, foot step 60.0 cm.', 'Least count of each method: a quarter of the unit.']
        : MODE === 'curve'
          ? ['Aim: to measure the length of a curved line with a thread.', 'Thread laid along the line, marked, then straightened on the scale.',
            'Metre scale least count 1 mm.', 'Mean of the readings = length of the line.']
          : ['Aim: to measure the length of a rod with a metre scale.', 'length = finishing mark − starting mark',
            'Metre scale least count 1 mm.', 'Eye straight above the mark: no parallax error.'],
      columns: bookCols, at: [-0.8, 0.06, 0.1] },
    graph: MODE === 'span' ? { x: function (r) { return r.unit * 100; }, y: function (r) { return r.units; },
      xlabel: 'size of one unit (cm)', ylabel: 'number of units counted', x0: 0, y0: 0 } : null,
    result: function (rows) {
      var m = mean(rows); if (!isFinite(m)) return null;
      return { label: MODE === 'curve' ? 'Length of the line' : MODE === 'span' ? 'Length of the cloth' : 'Length of the rod',
        value: m * 100, unit: 'cm', digits: 1, truth: p.L * 100,
        note: MODE === 'span' ? 'Each method gives a different number of units, but the same length in centimetres.' : 'Mean of the readings.' };
    },
    tol: MODE === 'span' ? 0.04 : 0.02,
    chips: MODE === 'span' ? ['Why do we need a standard unit?', 'Why estimate the last part of a unit?', 'Check my readings']
      : MODE === 'curve' ? ['Why use a thread for a curved line?', 'What if the thread stretches?', 'Check my readings']
        : ['What is parallax error?', 'Why not measure from the end of the scale?', 'Check my readings'],
    viva: MODE === 'span'
      ? [['Which gives the larger number for the same cloth, hand spans or cubits?', ['Hand spans', 'Cubits', 'Both the same'], 0,
        'A hand span is smaller, so more of them fit into the same length.'],
        ['Why is the metre used instead of a cubit?', ['It is the same for everybody', 'It is longer', 'It is easier to say'], 0,
          'A standard unit does not change from person to person.']]
      : MODE === 'curve'
        ? [['Why can a metre scale not measure a curved line directly?', ['The scale is straight and the line is not', 'The scale is too short', 'The ink is too thick'], 0,
          'A rigid straight scale cannot follow the bends; a thread can.'],
          ['The thread was stretched while laying it. The answer is', ['Too large', 'Too small', 'Right'], 0,
            'A stretched thread is longer than the line it was laid along.']]
        : [['The least count of a metre scale is', ['1 mm', '1 cm', '0.1 mm'], 0, 'The smallest printed division is one millimetre.'],
          ['Parallax error is removed by', ['Keeping the eye straight above the mark', 'Using a longer scale', 'Measuring faster'], 0,
            'From the side the mark appears shifted.']],
    askState: function () {
      var v = readingFor(p.unit, p.lc, st.par);
      return { set_up: MODE === 'span' ? 'body units' : MODE === 'curve' ? 'curved line and thread' : 'rod on the metre scale',
        unit_used_cm: +cm(st.unit ? st.unit.unit : p.unit), least_count_mm: +(p.lc * 1000).toFixed(1),
        units_laid: MODE === 'span' ? st.laid : null, scale_reading_cm: +cm(v.reading),
        eye_to_the_side: !!st.par, rod_start_mark_cm: MODE === 'ruler' ? st.start : null,
        thread_laid: MODE === 'curve' ? st.threadOn >= 1 : null, thread_marked: MODE === 'curve' ? st.marked : null,
        thread_on_the_scale: MODE === 'curve' ? st.threadStraight : null, readings_taken: S.rows.length };
    },
    steps: MODE === 'span' ? spanSteps : MODE === 'curve' ? curveSteps : rulerSteps,
    tick: function () {
      hudR.set(MODE === 'span' ? String(st.laid) : cm(readingFor(p.unit, p.lc, st.par).reading) + ' cm');
      hudN.set(String(S.rows.length));
    },
  };
});
