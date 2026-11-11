/* Prayogshala studio module: the path of a ray through a rectangular glass slab (NCERT Class X practical).
   A drawing board with a sheet of paper, the slab lying on its traced outline, four optical pins and a protractor.
   Two pins fix the incident ray; two more are fixed in line with their images seen through the slab; joining the
   feet gives the refracted path. Every number comes from the `slabray` kernel: Snell's law in vector form at both
   faces, the angle of refraction, the angle of emergence and the lateral displacement. */
HoolaStudio.define('school-glass-slab-ray', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.slabray;
  var p = window.HoolaKernels.paramsFor('slabray', S.lab.params);
  var BY = 0.004, R2D = 180 / Math.PI, DEG = Math.PI / 180;
  var BZ = -0.06, Z0 = 0.04;                                         // the board's centre z, and the point of incidence
  var SAMPLE = (S.lab.variant || {}).sample || 'Crown glass slab';
  var st = { iDeg: 30, iSet: 30, tCm: p.t * 100, tSet: p.t * 100, pinsBack: false, shifts: [] };
  var BOOK = ['Aim: to trace a ray through a rectangular glass slab and find n.',
    'Outline of the slab and the normals drawn on the paper.', 'P1, P2 fix the incident ray; P3, P4 are in line with their images.', ''];
  function round1(v) { return Math.round(v * 10) / 10; }
  function sync() { p.i = st.iDeg * DEG; p.t = st.tCm / 100; return K.view(null, p); }
  function w3(q) { return new T.Vector3(q[0], BY + 0.0022, Z0 + q[1]); }   // kernel (x, y) -> a point on the paper

  // ---------- the board and the sheet
  var board = new T.Group(); S.scene.add(board); board.position.set(0, 0, BZ);
  var ply = S.mesh(new T.BoxGeometry(0.52, 0.012, 0.42), M.darkWood); ply.position.y = -0.005; board.add(ply);
  var paperTex = S.canvasTex(1024, 820, function (x, w, h) {
    x.fillStyle = '#f7f4ec'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#2b3240'; x.font = '600 24px "Public Sans", sans-serif';
    x.fillText('outline of the slab', w * 0.07, h * 0.46);
  });
  var paper = S.mesh(new T.PlaneGeometry(0.46, 0.368), new T.MeshStandardMaterial({ map: paperTex, roughness: 0.92 }), false);
  paper.rotation.x = -Math.PI / 2; paper.position.y = BY; board.add(paper);
  [[-0.22, -0.17], [0.22, -0.17], [-0.22, 0.17], [0.22, 0.17]].forEach(function (c) {
    var pin = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.004, 12), M.chrome); pin.position.set(c[0], BY + 0.002, c[1]); board.add(pin); });
  S.contact(0.58, 0.48, 0, BZ, 0.45);

  // ---------- the slab (its near face through the point of incidence)
  var slab = new T.Group(); board.add(slab);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xd6ece8, roughness: 0.02, metalness: 0, transmission: 0.95, thickness: 0.004, ior: p.n, transparent: true, envMapIntensity: 1.2 });
  var slabBox = S.mesh(new T.BoxGeometry(0.12, 0.018, 1), glassM); slabBox.position.y = 0.009 + BY; slab.add(slabBox);
  var slabEdge = new T.LineSegments(new T.EdgesGeometry(new T.BoxGeometry(0.1203, 0.0183, 1)),
    new T.LineBasicMaterial({ color: 0x5d7f7a, transparent: true, opacity: 0.8, depthWrite: false }));
  slabEdge.position.y = 0.009 + BY; slabEdge.renderOrder = 6; slab.add(slabEdge);
  slab.position.x = 0.012;

  // ---------- the normals, the traced lines and the protractor
  var outline = [];
  for (var oi = 0; oi < 2; oi++) {
    var ln = new T.Mesh(new T.PlaneGeometry(0.14, 0.0009), new T.MeshBasicMaterial({ color: 0x2b3240, transparent: true, opacity: 0.75, depthWrite: false }));
    ln.rotation.x = -Math.PI / 2; ln.position.y = BY + 0.0018; board.add(ln); outline.push(ln);
  }
  var normals = [];
  for (var ni = 0; ni < 2; ni++) {
    var nl = new T.Line(new T.BufferGeometry(), new T.LineDashedMaterial({ color: 0x2b3240, transparent: true, opacity: 0.7, dashSize: 0.005, gapSize: 0.004, depthWrite: false }));
    nl.renderOrder = 6; board.add(nl); normals.push(nl);
  }
  var protTex = S.canvasTex(640, 640, function (x, w, h) {
    x.clearRect(0, 0, w, h);
    var cx = w / 2, cy = h / 2, R = h * 0.46, a, i;
    x.strokeStyle = 'rgba(30,35,45,0.75)'; x.fillStyle = 'rgba(30,35,45,0.75)'; x.lineWidth = 2.2;
    x.beginPath(); x.arc(cx, cy, R, 0, Math.PI); x.stroke();
    x.beginPath(); x.moveTo(cx - R, cy); x.lineTo(cx + R, cy); x.stroke();
    for (i = 0; i <= 180; i += 1) {
      a = i * Math.PI / 180;
      var big = i % 10 === 0, mid = i % 5 === 0, L = big ? 22 : mid ? 14 : 8;
      x.lineWidth = big ? 2.2 : 1;
      x.beginPath(); x.moveTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); x.lineTo(cx + Math.cos(a) * (R - L), cy + Math.sin(a) * (R - L)); x.stroke();
      if (big) { x.font = '600 18px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText(String(i), cx + Math.cos(a) * (R - 40), cy + Math.sin(a) * (R - 40) + 6); }
    }
  });
  var prot = new T.Mesh(new T.PlaneGeometry(0.2, 0.2), new T.MeshStandardMaterial({ map: protTex, transparent: true, roughness: 0.8 }));
  prot.rotation.x = -Math.PI / 2; prot.position.set(0, BY + 0.0016, Z0); board.add(prot);

  // ---------- the pins
  function pinMesh(col) {
    var g = new T.Group();
    var sh = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 0.05, 10), M.steel); sh.position.y = 0.025; g.add(sh);
    var hd = S.mesh(new T.SphereGeometry(0.0026, 12, 8), col); hd.position.y = 0.051; g.add(hd);
    g.position.y = BY; return g;
  }
  var blueM = new T.MeshStandardMaterial({ color: 0x2c63c4, roughness: 0.4 });
  var P1 = pinMesh(blueM), P2 = pinMesh(blueM), P3 = pinMesh(M.red), P4 = pinMesh(M.red);
  [P1, P2, P3, P4].forEach(function (g) { board.add(g); });
  P3.visible = false; P4.visible = false;

  // ---------- the traced ray on the paper
  var rayMat = new T.LineBasicMaterial({ color: 0xc0392b, transparent: true, opacity: 0.9, depthWrite: false, toneMapped: false });
  var dashMat = new T.LineDashedMaterial({ color: 0x8a94a6, transparent: true, opacity: 0.7, dashSize: 0.005, gapSize: 0.004, depthWrite: false, toneMapped: false });
  var shiftMat = new T.LineBasicMaterial({ color: 0x1f7a4d, transparent: true, opacity: 0.95, depthWrite: false, toneMapped: false });
  var rayLine = new T.Line(new T.BufferGeometry(), rayMat); rayLine.renderOrder = 7; board.add(rayLine);
  var contLine = new T.Line(new T.BufferGeometry(), dashMat); contLine.renderOrder = 7; board.add(contLine);
  var shiftLine = new T.Line(new T.BufferGeometry(), shiftMat); shiftLine.renderOrder = 8; board.add(shiftLine); shiftLine.visible = false;

  S.addApparatus('board', board, 'Drawing board with paper', 'The outline of the slab and the normals are drawn on the sheet; the whole path of the ray is traced on it.');
  S.addApparatus('slab', slab, 'Rectangular glass slab', SAMPLE + '. Its two long faces are flat and parallel, so the emergent ray comes out parallel to the incident ray.');
  S.addApparatus('pins', P1, 'Optical pins', 'P1 and P2 fix the incident ray. P3 and P4 are fixed on the other side, in line with the images of P1 and P2 seen through the slab.');
  S.addApparatus('prot', prot, 'Protractor', 'Centred at the point of incidence: i is read on one side of the normal, r on the other.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudI = S.hudCard('Angle of incidence i'), hudR = S.hudCard('Angle of refraction r'), hudS = S.hudCard('Lateral displacement');

  var view = null;
  function update() {
    var v = sync(); view = v;
    slabBox.scale.z = p.t; slabEdge.scale.z = p.t;
    slab.position.z = Z0 - p.t / 2;
    outline[0].scale.x = 1; outline[0].position.set(slab.position.x, BY + 0.0018, Z0);
    outline[1].position.set(slab.position.x, BY + 0.0018, Z0 - p.t);
    normals.forEach(function (nl, k) {
      var z = k === 0 ? Z0 : Z0 - p.t;
      nl.geometry.setFromPoints([new T.Vector3(0, BY + 0.002, z + (k === 0 ? 0.075 : 0)), new T.Vector3(0, BY + 0.002, z - (k === 0 ? 0 : 0.075))]);
      if (k === 1) nl.geometry.setFromPoints([new T.Vector3(v.rays.length ? p.t * Math.tan(v.r) : 0, BY + 0.002, z), new T.Vector3(v.rays.length ? p.t * Math.tan(v.r) : 0, BY + 0.002, z - 0.075)]);
      nl.computeLineDistances();
    });
    var legs = (v.rays[0] || {}).p || [[0, 0], [0, 0]];
    rayLine.geometry.setFromPoints(legs.map(w3));
    var d0 = [Math.sin(p.i), -Math.cos(p.i)];
    contLine.geometry.setFromPoints([w3([0, 0]), w3([0.16 * d0[0], 0.16 * d0[1]])]);
    contLine.computeLineDistances();
    // the two front pins sit on the incident ray, the two back pins on the emergent ray
    P1.position.set(-0.115 * d0[0], BY, Z0 - 0.115 * d0[1]);
    P2.position.set(-0.062 * d0[0], BY, Z0 - 0.062 * d0[1]);
    var exit = legs[2] || [0, 0], d2 = [Math.sin(v.e), -Math.cos(v.e)];
    P3.position.set(exit[0] + 0.035 * d2[0], BY, Z0 + exit[1] + 0.035 * d2[1]);
    P4.position.set(exit[0] + 0.085 * d2[0], BY, Z0 + exit[1] + 0.085 * d2[1]);
    P3.visible = st.pinsBack; P4.visible = st.pinsBack;
    if (st.pinsBack) {
      var a = [exit[0] + 0.055 * d2[0], exit[1] + 0.055 * d2[1]];
      var b = [a[0] - v.shift * Math.cos(p.i), a[1] - v.shift * Math.sin(p.i)];
      shiftLine.geometry.setFromPoints([w3(a), w3(b)]); shiftLine.visible = true;
    } else shiftLine.visible = false;
    hudI.set(st.iDeg.toFixed(0) + '°');
    hudR.set(st.pinsBack ? (v.r * R2D).toFixed(1) + '°' : 'fix the back pins first');
    hudS.set(st.pinsBack ? (v.shift * 1000).toFixed(1) + ' mm' : '—');
  }

  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function setAngle(toDeg) {
    if (S.hand.busy) return wait();
    toDeg = Math.round(toDeg);
    if (!(toDeg >= 20 && toDeg <= 70)) { S.say('Keep the angle of incidence between 20° and 70°: outside that the pins are hard to line up.'); return Promise.resolve(false); }
    var from = st.iDeg;
    st.pinsBack = false;
    function at(k) { return from + (toDeg - from) * k; }
    function pos(k) { var a = at(k) * DEG; return new T.Vector3(-0.115 * Math.sin(a) , BY + 0.05, BZ + Z0 + 0.115 * Math.cos(a)); }
    return S.hand.pinchMove(pos(0), pos, function (k) { st.iDeg = at(k); update(); }, { mode: 'top', ms: 900, reachMs: 550, hold: 150 })
      .then(function () { st.iDeg = toDeg; update(); S.render(); S.say('P1 and P2 are now on the ray that strikes the slab at ' + toDeg + '°.'); return true; });
  }
  function setThick(toCm) {
    if (S.hand.busy) return wait();
    toCm = round1(toCm);
    if (!(toCm >= 2 && toCm <= 8)) { S.say('The slabs in the box are between 2 cm and 8 cm thick.'); return Promise.resolve(false); }
    var from = st.tCm;
    st.pinsBack = false;
    function at(k) { return from + (toCm - from) * k; }
    return S.hand.pinchMove(new T.Vector3(0.012, BY + 0.02, BZ + Z0 - from / 200), function (k) { return new T.Vector3(0.012, BY + 0.02, BZ + Z0 - at(k) / 200); },
      function (k) { st.tCm = at(k); update(); }, { mode: 'top', ms: 800, reachMs: 550, hold: 150 })
      .then(function () { st.tCm = toCm; update(); S.render(); S.say('A ' + toCm.toFixed(1) + ' cm slab is on the outline now. Fix the back pins again.'); return true; });
  }
  function fixBackPins() {
    if (S.hand.busy) return wait();
    if (st.pinsBack) return Promise.resolve(true);
    var v = sync();
    return S.hand.reach(new T.Vector3(P3.position.x, BY + 0.055, BZ + P3.position.z), 'top', 600)
      .then(function () { return S.hand.reach(new T.Vector3(P4.position.x, BY + 0.055, BZ + P4.position.z), 'top', 450); })
      .then(function () { return S.hand.away(450); })
      .then(function () {
        st.pinsBack = true; update(); S.render();
        S.say('P3 and P4 are in line with the images of P1 and P2. Joining the feet gives the emergent ray: r = ' + (v.r * R2D).toFixed(1) + '°.');
        return true;
      });
  }
  function record() {
    if (S.hand.busy) { wait(); return false; }
    if (!st.pinsBack) { S.say('Fix P3 and P4 in line with the images first, or there is no refracted ray to measure.'); return false; }
    var v = sync(), ai = Math.round(st.iDeg), ar = Math.round(v.r * R2D * 2) / 2;    // protractor: half a degree
    if (S.rows.some(function (r) { return Math.abs(r.i - ai) < 3 && Math.abs(r.t - st.tCm) < 0.5; })) { S.say('You already have a reading at i = ' + ai + '° with this slab. Take a new angle.'); return false; }
    S.addRow({ i: ai, r: ar, e: Math.round(v.e * R2D * 2) / 2, t: round1(st.tCm), x: round1(v.shift * 1000) });
    S.say('Written in your record book: i = ' + ai + '°, r = ' + ar.toFixed(1) + '°, lateral shift = ' + (v.shift * 1000).toFixed(1) + ' mm.');
    return true;
  }
  function noteShift() {
    if (S.hand.busy) { wait(); return false; }
    if (!st.pinsBack) { S.say('Fix P3 and P4 first.'); return false; }
    var v = sync(), key = round1(st.tCm);
    if (st.shifts.indexOf(key) < 0) {
      st.shifts.push(key);
      BOOK.push('t = ' + key.toFixed(1) + ' cm at i = ' + st.iDeg.toFixed(0) + '°: lateral shift = ' + (v.shift * 1000).toFixed(1) + ' mm.');
      S.book.draw();
    }
    S.say('Lateral displacement with the ' + key.toFixed(1) + ' cm slab: ' + (v.shift * 1000).toFixed(1) + ' mm.');
    S.render(); return true;
  }

  var VIEWS = { board: [[0.0, 0.42, BZ + 0.46], [0, 0.0, BZ + 0.02]], slab: [[0.1, 0.16, BZ + 0.22], [0.01, 0.01, BZ + Z0 - 0.02]],
    pins: [[-0.12, 0.2, BZ + 0.28], [-0.02, 0.02, BZ + Z0]], prot: [[0.0, 0.3, BZ + 0.16], [0, 0.0, BZ + Z0 - 0.02]],
    book: [[-0.4, 0.44, 0.5], [-0.5, 0.0, 0.08]] };
  update();

  function nMean(rows) {
    var ns = (rows || []).filter(function (r) { return r.r > 0; }).map(function (r) { return Math.sin(r.i * DEG) / Math.sin(r.r * DEG); });
    return ns.length ? S.fit.mean(ns) : NaN;
  }

  return {
    camera: { pos: [0.04, 0.46, BZ + 0.56], look: [0, 0.0, BZ + 0.03] },
    views: VIEWS,
    theory: { principle: 'When a ray goes from air into glass it bends towards the normal, and when it comes out it bends away from the normal by the same amount. The two faces of a rectangular slab are parallel, so the emergent ray is parallel to the incident ray: it is only pushed sideways. The pins are used because the eye can line up P3 and P4 with the images of P1 and P2 seen through the glass; joining the four feet traces the whole path on the paper.',
      formula: 'n = sin i / sin r   ·   lateral shift = t sin(i − r) / cos r',
      formulaNote: 'i = angle of incidence, r = angle of refraction, e = angle of emergence (= i), t = thickness of the slab',
      more: ['The angle of emergence equals the angle of incidence, which is the quickest check that the tracing is right.',
        'The sideways shift grows with the thickness of the slab and with the angle of incidence; it is zero when the ray falls along the normal.',
        'This is Snell’s law: sin i / sin r is the same for every angle, and that constant is the refractive index of the glass.'],
      precautions: 'Draw the outline of the slab before you move it, and never move the slab while the pins are being fixed. Stick the pins upright and at least 5 cm apart. Keep your eye level with the pins and look at the images with one eye.' },
    book: { title: 'Expt. — Refraction through a glass slab', lines: BOOK,
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'i (°)', get: function (r) { return r.i.toFixed(0); } },
        { label: 'r (°)', get: function (r) { return r.r.toFixed(1); } }, { label: 'e (°)', get: function (r) { return r.e.toFixed(1); } },
        { label: 'shift (mm)', get: function (r) { return r.x.toFixed(1); } },
        { label: 'sin i / sin r', get: function (r) { return (Math.sin(r.i * DEG) / Math.sin(r.r * DEG)).toFixed(3); } }] },
    graph: { x: function (r) { return Math.sin(r.r * DEG); }, y: function (r) { return Math.sin(r.i * DEG); }, xlabel: 'sin r', ylabel: 'sin i', x0: 0, y0: 0,
      line: function (pts) { var m = S.fit.origin(pts); return isFinite(m) ? function (x) { return m * x; } : null; } },
    result: function (rows) {
      var n = nMean(rows); if (!isFinite(n) || (rows || []).length < 4) return null;
      return { label: 'n', value: n, unit: '', digits: 3, truth: p.n,
        note: 'Mean of sin i / sin r. The graph of sin i against sin r is a straight line through the origin whose slope is n.' };
    },
    tol: 0.02,
    chips: ['Why does the ray bend towards the normal?', 'Why is the emergent ray parallel?', 'What changes the lateral shift?', 'Check my readings', 'Why is my n a little different?'],
    viva: [['The emergent ray from a rectangular slab is?', ['Parallel to the incident ray', 'Along the normal', 'Bent towards the normal'], 0, 'The faces are parallel, so the two bendings cancel.'],
      ['A ray falls on the slab along the normal. It then?', ['Goes straight through', 'Bends towards the normal', 'Is reflected back'], 0, 'At i = 0 there is no bending at all.'],
      ['Two slabs of the same glass, one twice as thick, same i. The lateral shift?', ['Doubles', 'Stays the same', 'Halves'], 0, 'The shift is proportional to the thickness.']],
    askState: function () {
      var v = view || sync();
      return { sample: SAMPLE, angle_of_incidence_deg: st.iDeg, angle_of_refraction_deg: st.pinsBack ? +(v.r * R2D).toFixed(1) : null,
        angle_of_emergence_deg: st.pinsBack ? +(v.e * R2D).toFixed(1) : null, lateral_shift_mm: st.pinsBack ? +(v.shift * 1000).toFixed(1) : null,
        slab_thickness_cm: +st.tCm.toFixed(1), back_pins_fixed: st.pinsBack, readings_taken: S.rows.length,
        thicknesses_tried: st.shifts.slice() };
    },

    steps: [
      { id: 'trace', title: 'Trace the ray', view: 'board', render: function (u) {
          u.h2('Fix the pins and trace the path');
          u.p('The outline of the slab and the normal at the point of incidence are already drawn. Put P1 and P2 on the incident ray at the angle you want, then look through the slab from the other side and fix P3 and P4 in line with their images. Take at least four angles.');
          u.task('1. The incident ray', true, 'P1 and P2 at i = ' + st.iDeg.toFixed(0) + '°');
          u.slider('Angle of incidence i', 20, 70, 1, function () { return st.iSet; }, function (x) { st.iSet = x; }, '°', 0);
          u.row(u.button('Put P1 and P2 there', function () { setAngle(st.iSet); S.render(); }, true, S.hand.busy),
            u.button('Look from above', function () { S.focus('prot'); }));
          u.task('2. The emergent ray', st.pinsBack, st.pinsBack ? 'P3 and P4 are in line with the images' : 'Not fixed yet')
            .add(u.button('Fix P3 and P4', function () { fixBackPins(); }, !st.pinsBack, st.pinsBack || S.hand.busy));
          u.live(function () { var v = view || sync(); return st.pinsBack ? 'Protractor: i = ' + st.iDeg.toFixed(0) + '°, r = ' + (v.r * R2D).toFixed(1) + '°, e = ' + (v.e * R2D).toFixed(1) + '°' : 'Fix the back pins to get the refracted ray'; });
          u.row(u.button('Record i, r and e', function () { record(); }, true, S.hand.busy));
          u.h3('Observation table'); u.table();
          u.next('Next: the lateral shift', S.rows.length >= 4);
          if (S.rows.length < 4) u.p(S.rows.length + ' of at least 4 angles recorded.');
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          return [30, 40, 50, 60].reduce(function (pr, a) {
            return pr.then(function () { st.iSet = a; return setAngle(a); }).then(function () { return fixBackPins(); }).then(function () { record(); });
          }, Promise.resolve());
        } },
      { id: 'shift', title: 'The lateral shift', view: 'slab', render: function (u) {
          u.h2('How far is the ray pushed sideways?');
          u.p('The green line on the paper is the perpendicular distance between the incident ray produced and the emergent ray. Change the thickness of the slab, fix the back pins again, and see how the shift changes while i stays the same.');
          u.task('Slab', true, st.tCm.toFixed(1) + ' cm thick, at i = ' + st.iDeg.toFixed(0) + '°');
          u.slider('Thickness of the slab', 2, 8, 0.5, function () { return st.tSet; }, function (x) { st.tSet = x; }, 'cm', 1);
          u.row(u.button('Put that slab on the outline', function () { setThick(st.tSet); S.render(); }, true, S.hand.busy),
            u.button('Fix P3 and P4 again', function () { fixBackPins(); }, false, st.pinsBack || S.hand.busy));
          u.live(function () { var v = view || sync(); return st.pinsBack ? 'Lateral displacement: ' + (v.shift * 1000).toFixed(1) + ' mm' : 'Fix the back pins to measure it'; });
          u.row(u.button('Note the shift', function () { noteShift(); }, true, S.hand.busy || !st.pinsBack));
          if (st.shifts.length) u.note('Thicknesses noted: ' + st.shifts.map(function (a) { return a.toFixed(1) + ' cm'; }).join(', ') + '. The shift grows with the thickness.');
          u.next('Next: graph and result', st.shifts.length >= 2);
          if (st.shifts.length < 2) u.p(st.shifts.length + ' of at least 2 thicknesses noted.');
        },
        ok: function () { return st.shifts.length >= 2; },
        auto: function () {
          return [st.tCm, Math.min(8, Math.max(2, round1(st.tCm * 1.6)))].reduce(function (pr, t) {
            return pr.then(function () { st.tSet = t; return setThick(t); }).then(function () { return fixBackPins(); }).then(function () { noteShift(); });
          }, Promise.resolve());
        } },
    ],

    tick: function () { update(); },
  };
});
