/* Prayogshala studio module: Plane mirror - the law of reflection, the image, and two inclined mirrors
   (NCERT Class VII-VIII). A drawing board with a sheet of paper, a strip mirror standing on the ruled line, a ray
   box with a comb slit, a printed protractor, optical pins, and a second mirror hinged at the pole.
   Every number comes from the `planemirror` kernel: the reflected direction by vector reflection, the image where
   two reflected rays meet when produced back, and the count of images of two mirrors by repeated reflection. */
HoolaStudio.define('school-plane-mirror', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.planemirror;
  var p = window.HoolaKernels.paramsFor('planemirror', S.lab.params);
  var BY = 0.004, R2D = 180 / Math.PI, DEG = Math.PI / 180;          // the paper's surface height, degrees
  var st = { iDeg: 30, iSet: 30, dCm: 9, dSet: 9, thDeg: 60, thSet: 60, two: false, imgFound: false, beam: true, counts: [] };
  var BOOK = ['Aim: to check that r = i, to find the image of a pin, and to count the images in two mirrors.',
    'Mirror along the ruled line; the normal is drawn at the pole.', 'i and r are read on the protractor.', ''];
  function round1(v) { return Math.round(v * 10) / 10; }
  function sync() { p.i = st.iDeg * DEG; p.d = st.dCm / 100; p.theta = st.thDeg * DEG; return K.view(null, p); }

  // ---------- the drawing board and the sheet of paper
  var board = new T.Group(); S.scene.add(board); board.position.set(0, 0, -0.06);
  var ply = S.mesh(new T.BoxGeometry(0.56, 0.012, 0.42), M.darkWood); ply.position.y = -0.005; board.add(ply);
  var paperTex = S.canvasTex(1024, 768, function (x, w, h) {
    x.fillStyle = '#f7f4ec'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(40,45,60,0.55)'; x.lineWidth = 3; x.beginPath(); x.moveTo(w * 0.1, h * 0.5); x.lineTo(w * 0.9, h * 0.5); x.stroke();
    x.setLineDash([10, 8]); x.lineWidth = 2; x.beginPath(); x.moveTo(w * 0.5, h * 0.5); x.lineTo(w * 0.5, h * 0.12); x.stroke(); x.setLineDash([]);
    x.fillStyle = '#2b3240'; x.font = '600 26px "Public Sans", sans-serif';
    x.fillText('mirror line', w * 0.12, h * 0.47); x.fillText('normal', w * 0.515, h * 0.17); x.fillText('P (pole)', w * 0.52, h * 0.545);
  });
  var paper = S.mesh(new T.PlaneGeometry(0.5, 0.375), new T.MeshStandardMaterial({ map: paperTex, roughness: 0.92 }), false);
  paper.rotation.x = -Math.PI / 2; paper.position.y = BY; board.add(paper);
  [[-0.24, -0.17], [0.24, -0.17], [-0.24, 0.17], [0.24, 0.17]].forEach(function (c) {
    var pin = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.004, 12), M.chrome); pin.position.set(c[0], BY + 0.002, c[1]); board.add(pin);
  });
  S.contact(0.62, 0.48, 0, -0.06, 0.45);
  var POLE = new T.Vector3(0, BY, -0.06);                             // the pole, in world coordinates

  // ---------- the protractor (printed, lying on the paper)
  var protTex = S.canvasTex(768, 768, function (x, w, h) {
    x.clearRect(0, 0, w, h);
    var cx = w / 2, cy = h / 2, R = h * 0.46, a, i;
    x.strokeStyle = 'rgba(30,35,45,0.8)'; x.fillStyle = 'rgba(30,35,45,0.8)'; x.lineWidth = 2.5;
    x.beginPath(); x.arc(cx, cy, R, 0, Math.PI); x.stroke();                 // the arc lies in front of the mirror line
    x.beginPath(); x.moveTo(cx - R, cy); x.lineTo(cx + R, cy); x.stroke();
    for (i = 0; i <= 180; i += 1) {
      a = i * Math.PI / 180;
      var big = i % 10 === 0, mid = i % 5 === 0, L = big ? 26 : mid ? 16 : 9;
      x.lineWidth = big ? 2.4 : 1.1;
      x.beginPath(); x.moveTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); x.lineTo(cx + Math.cos(a) * (R - L), cy + Math.sin(a) * (R - L)); x.stroke();
      if (big) { x.font = '600 20px "Public Sans", sans-serif'; x.textAlign = 'center';
        x.fillText(String(i), cx + Math.cos(a) * (R - 46), cy + Math.sin(a) * (R - 46) + 7); }
    }
    x.beginPath(); x.arc(cx, cy, 4, 0, Math.PI * 2); x.fill();
  });
  var prot = new T.Mesh(new T.PlaneGeometry(0.27, 0.27), new T.MeshStandardMaterial({ map: protTex, transparent: true, roughness: 0.8 }));
  prot.rotation.x = -Math.PI / 2; prot.position.set(0, BY + 0.0016, 0); board.add(prot);      // centred on the pole

  // ---------- the strip mirror on the ruled line
  var mirror = new T.Group(); board.add(mirror); mirror.position.set(0, BY, 0);
  var glassM = new T.MeshStandardMaterial({ color: 0xdfe8ee, roughness: 0.06, metalness: 1, envMapIntensity: 1.2 });
  var mFace = S.mesh(new T.BoxGeometry(0.2, 0.05, 0.0035), glassM); mFace.position.set(0, 0.025, 0.0018); mirror.add(mFace);
  var mBack = S.mesh(new T.BoxGeometry(0.202, 0.052, 0.004), M.bakelite); mBack.position.set(0, 0.025, -0.0022); mirror.add(mBack);
  [-0.085, 0.085].forEach(function (x0) {
    var cl = S.mesh(new T.BoxGeometry(0.016, 0.01, 0.022), M.darkWood); cl.position.set(x0, 0.005, -0.002); mirror.add(cl); });

  // ---------- the second mirror, hinged at the pole
  var mirror2 = new T.Group(); board.add(mirror2); mirror2.position.set(0, BY, 0);
  var m2Face = S.mesh(new T.BoxGeometry(0.16, 0.05, 0.0035), glassM); m2Face.position.set(0.08, 0.025, 0.0018); mirror2.add(m2Face);
  var m2Back = S.mesh(new T.BoxGeometry(0.162, 0.052, 0.004), M.bakelite); m2Back.position.set(0.08, 0.025, -0.0022); mirror2.add(m2Back);
  var hinge = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.054, 14), M.brass); hinge.position.set(0, 0.027, 0); mirror2.add(hinge);
  mirror2.visible = false;

  // ---------- the ray box
  var rayBox = new T.Group(); S.scene.add(rayBox);
  var rbBody = S.rounded(0.085, 0.05, 0.06, 0.006, new T.MeshStandardMaterial({ color: 0x23262c, roughness: 0.5 }));
  rbBody.rotation.x = -Math.PI / 2; rbBody.position.y = 0.03; rayBox.add(rbBody);
  var rbWin = new T.Mesh(new T.PlaneGeometry(0.03, 0.016), new T.MeshBasicMaterial({ color: 0xfff1c6, toneMapped: false }));
  rbWin.position.set(0.0435, 0.03, 0); rbWin.rotation.y = Math.PI / 2; rayBox.add(rbWin);
  var comb = S.mesh(new T.BoxGeometry(0.004, 0.03, 0.04), M.black); comb.position.set(0.045, 0.03, 0); rayBox.add(comb);
  var rbLab = S.label('RAY BOX', { w: 0.05, ratio: 0.22, color: '#e6e8ec', weight: 700 });
  rbLab.rotation.x = -Math.PI / 2; rbLab.position.set(0, 0.0605, 0); rayBox.add(rbLab);
  var rbShadow = S.contact(0.14, 0.12, 0, 0, 0.45);

  // ---------- the pins
  function pinMesh(col, ghost) {
    var g = new T.Group();
    var sh = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 0.05, 10), ghost ? new T.MeshStandardMaterial({ color: 0xc23b30, roughness: 0.5, transparent: true, opacity: 0.45 }) : M.steel);
    sh.position.y = 0.025; g.add(sh);
    var hd = S.mesh(new T.SphereGeometry(0.0025, 12, 8), ghost ? new T.MeshStandardMaterial({ color: 0xc23b30, transparent: true, opacity: 0.5 }) : col);
    hd.position.y = 0.051; g.add(hd);
    return g;
  }
  var objPin = pinMesh(new T.MeshStandardMaterial({ color: 0x2c63c4, roughness: 0.4 }), false); board.add(objPin);
  var imgPin = pinMesh(null, true); board.add(imgPin); imgPin.visible = false;
  var multi = [];
  for (var mi = 0; mi < 12; mi++) { var mp = pinMesh(null, true); mp.visible = false; board.add(mp); multi.push(mp); }

  // ---------- the beam on the paper (two bright strips) and the sighting lines
  function strip(col, op) {
    var m = new T.Mesh(new T.PlaneGeometry(1, 0.004), new T.MeshBasicMaterial({ color: col, transparent: true, opacity: op, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending }));
    m.rotation.x = -Math.PI / 2; m.renderOrder = 6; board.add(m); return m;
  }
  function placeStrip(m, ax, az, bx, bz, w) {
    var dx = bx - ax, dz = bz - az, L = Math.hypot(dx, dz);
    m.scale.set(L, (w || 0.004) / 0.004, 1);
    m.position.set((ax + bx) / 2, BY + 0.0016, (az + bz) / 2);
    m.rotation.z = 0; m.rotation.y = Math.atan2(-dz, dx); m.visible = L > 1e-4;
  }
  var inStrip = strip(0xffd98a, 0.85), outStrip = strip(0xffd98a, 0.85);
  var dashMat = new T.LineDashedMaterial({ color: 0xc23b30, transparent: true, opacity: 0.6, dashSize: 0.006, gapSize: 0.005, depthWrite: false, toneMapped: false });
  var sight = [];
  for (var si = 0; si < 4; si++) { var l = new T.Line(new T.BufferGeometry(), dashMat); l.visible = false; l.renderOrder = 7; board.add(l); sight.push(l); }

  S.addApparatus('board', board, 'Drawing board with paper', 'The mirror line and the normal at the pole are drawn on the sheet; every ray is traced on it.');
  S.addApparatus('mirror', mirror, 'Plane mirror', 'A strip mirror standing on its edge, its silvered face exactly on the ruled line.');
  S.addApparatus('raybox', rayBox, 'Ray box', 'A lamp with a comb in front of it, which gives one narrow beam of light.');
  S.addApparatus('prot', prot, 'Protractor', 'Printed on the sheet, centred at the pole: read i on one side of the normal and r on the other.');
  S.addApparatus('pins', objPin, 'Optical pins', 'A pin stuck upright in front of the mirror is the object; its image is looked for behind the mirror.');
  S.addApparatus('mirror2', mirror2, 'Second mirror', 'Stand it against the first at an angle and count the images of one pin.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudI = S.hudCard('Angle of incidence i'), hudR = S.hudCard('Angle of reflection r'), hudX = S.hudCard('Image / images');

  // ---------- drawing the scene from the kernel's numbers
  var view = null, BEAM = 0.21;
  function update() {
    var v = sync(); view = v;
    var i = p.i, dx = Math.sin(i), dz = -Math.cos(i);                 // kernel (x, y) -> board (x, z)
    placeStrip(inStrip, -BEAM * dx, -BEAM * dz, 0, 0, 0.004);
    var rd = [Math.sin(v.r), Math.cos(v.r)];
    placeStrip(outStrip, 0, 0, BEAM * rd[0], BEAM * rd[1], 0.004);
    rayBox.position.set(-(BEAM + 0.055) * dx, 0, -0.06 - (BEAM + 0.055) * dz);
    rayBox.rotation.y = Math.atan2(dz, dx) + Math.PI;
    rbShadow.position.set(rayBox.position.x, 0.0008, rayBox.position.z);
    objPin.position.set(0, BY, p.d); objPin.visible = !st.two;
    imgPin.position.set(0, BY, -v.img); imgPin.visible = st.imgFound && !st.two;
    mirror2.visible = st.two; mirror2.rotation.y = -p.theta;
    multi.forEach(function (m) { m.visible = false; });
    if (st.two) {
      var n = Math.min(multi.length, Math.round(v.N));
      for (var k = 0; k < n; k++) {
        var a = p.theta / 2 + (k + 1) * p.theta;
        multi[k].position.set(p.d * Math.cos(a), BY, p.d * Math.sin(a)); multi[k].visible = true;
      }
    }
    sight.forEach(function (l) { l.visible = false; });
    if (st.imgFound && !st.two) {
      [[-p.sep, 1], [p.sep, 2]].forEach(function (q, k) {
        var hit = new T.Vector3(q[0], BY + 0.002, 0);
        var l = sight[k];
        l.geometry.setFromPoints([new T.Vector3(0, BY + 0.002, p.d), hit, new T.Vector3(0, BY + 0.002, -v.img)]);
        l.computeLineDistances(); l.visible = true;
      });
    }
    inStrip.visible = st.beam && !st.two; outStrip.visible = st.beam && !st.two;
    hudI.set(st.iDeg.toFixed(0) + '°'); hudR.set((v.r * R2D).toFixed(1) + '°');
    hudX.set(st.two ? Math.round(v.N) + ' images at ' + st.thDeg.toFixed(0) + '°' : (st.imgFound ? v.img * 100 + ' cm behind the mirror' : 'pin ' + st.dCm.toFixed(1) + ' cm in front'));
  }

  // ---------- the human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function turnBeam(toDeg) {
    if (S.hand.busy) return wait();
    toDeg = Math.round(toDeg);
    if (!(toDeg >= 10 && toDeg <= 80)) { S.say('Keep the angle of incidence between 10° and 80°, or the beam misses the mirror.'); return Promise.resolve(false); }
    var from = st.iDeg;
    if (Math.abs(toDeg - from) < 0.5) { st.iDeg = toDeg; update(); return Promise.resolve(true); }
    function at(k) { return from + (toDeg - from) * k; }
    function pos(k) { var a = at(k) * DEG; return new T.Vector3(-(BEAM + 0.09) * Math.sin(a), 0.05, -0.06 + (BEAM + 0.09) * Math.cos(a)); }
    return S.hand.pinchMove(pos(0), pos, function (k) { st.iDeg = at(k); update(); }, { ms: 900, reachMs: 550, hold: 150 })
      .then(function () { st.iDeg = toDeg; update(); S.render(); return true; });
  }
  function movePin(toCm) {
    if (S.hand.busy) return wait();
    toCm = round1(toCm);
    if (!(toCm >= 4 && toCm <= 14)) { S.say('Keep the pin between 4 cm and 14 cm in front of the mirror.'); return Promise.resolve(false); }
    var from = st.dCm;
    function at(k) { return from + (toCm - from) * k; }
    return S.hand.pinchMove(new T.Vector3(0, BY + 0.05, -0.06 + from / 100), function (k) { return new T.Vector3(0, BY + 0.05, -0.06 + at(k) / 100); },
      function (k) { st.dCm = at(k); update(); }, { mode: 'top', ms: 800, reachMs: 550, hold: 150 })
      .then(function () { st.dCm = toCm; update(); S.render(); return true; });
  }
  function findImage() {
    if (S.hand.busy) return wait();
    return S.hand.reach(new T.Vector3(0.04, BY + 0.06, -0.06 + 0.16), 'top', 600).then(function () { return S.hand.away(500); })
      .then(function () {
        st.imgFound = true; var v = sync(); update(); S.render();
        S.say('Looking from two sides, the image is in line with the pin at ' + (v.img * 100).toFixed(1) + ' cm behind the mirror: as far behind as the pin is in front.');
        return true;
      });
  }
  function setAngle(toDeg) {
    if (S.hand.busy) return wait();
    toDeg = Math.round(toDeg);
    if (!(toDeg >= 30 && toDeg <= 120)) { S.say('Set the two mirrors between 30° and 120°.'); return Promise.resolve(false); }
    var from = st.thDeg;
    function at(k) { return from + (toDeg - from) * k; }
    function pos(k) { var a = at(k) * DEG; return new T.Vector3(0.13 * Math.cos(a), 0.05, -0.06 + 0.13 * Math.sin(a)); }
    st.two = true;
    return S.hand.pinchMove(pos(0), pos, function (k) { st.thDeg = at(k); update(); }, { ms: 900, reachMs: 550, hold: 150 })
      .then(function () { st.thDeg = toDeg; update(); S.render(); return true; });
  }
  function recordAngle() {
    if (S.hand.busy) { wait(); return false; }
    var v = sync();
    var ai = Math.round(st.iDeg), ar = Math.round(v.r * R2D * 2) / 2;   // the protractor's least count is half a degree
    if (S.rows.some(function (r) { return Math.abs(r.i - ai) < 3; })) { S.say('You already have a reading near i = ' + ai + '°. Turn the ray box to a new angle.'); return false; }
    S.addRow({ i: ai, r: ar });
    S.say('Written in your record book: i = ' + ai + '°, r = ' + ar.toFixed(1) + '°.');
    return true;
  }
  function countImages() {
    if (S.hand.busy) { wait(); return false; }
    var v = sync(), n = Math.round(v.N);
    var line = 'Two mirrors at ' + st.thDeg.toFixed(0) + '°: ' + n + ' images (360/θ − 1 = ' + (360 / st.thDeg - 1).toFixed(0) + ').';
    if (st.counts.indexOf(st.thDeg) < 0) { st.counts.push(st.thDeg); BOOK.push(line); S.book.draw(); }
    S.say(line); S.render(); return true;
  }

  var ft = 0;
  S.tickers.push(function (dt) { ft += dt; var g = 0.8 + 0.06 * Math.sin(ft * 13);
    inStrip.material.opacity = st.two ? 0 : g; outStrip.material.opacity = st.two ? 0 : g; });

  var VIEWS = { board: [[0.0, 0.42, 0.42], [0, 0.0, -0.06]], mirror: [[0.1, 0.12, 0.16], [0, 0.02, -0.05]],
    raybox: [[-0.22, 0.2, 0.24], [-0.1, 0.02, -0.02]], prot: [[0.0, 0.3, 0.14], [0, 0.0, -0.02]],
    pins: [[0.12, 0.16, 0.2], [0, 0.02, -0.03]], mirror2: [[0.0, 0.34, 0.2], [0.02, 0.0, -0.06]],
    book: [[-0.4, 0.44, 0.5], [-0.5, 0.0, 0.08]] };
  update();

  function ratio(rows) {
    var rs = (rows || []).filter(function (r) { return r.i > 0; }).map(function (r) { return r.r / r.i; });
    return rs.length ? S.fit.mean(rs) : NaN;
  }

  return {
    camera: { pos: [0.02, 0.46, 0.52], look: [0, 0.0, -0.05] },
    views: VIEWS,
    theory: { principle: 'Light that falls on a plane mirror comes back into the same medium: it is reflected. The incident ray, the reflected ray and the normal at the point of incidence lie in one plane, and the angle of reflection is always equal to the angle of incidence. The reflected rays from a point object spread out, so they only seem to come from a point behind the mirror: the image is virtual, erect, the same size, and as far behind as the object is in front, with left and right interchanged.',
      formula: '∠i = ∠r   ·   image distance = object distance   ·   N = 360/θ − 1',
      formulaNote: 'i, r measured from the normal · N = the number of images of one object between two mirrors at θ',
      more: ['A ray box with a comb in front of it gives a narrow beam that can be traced on the paper; with pins, the same ray is fixed by sighting two pins in line and marking their feet.',
        'At θ = 60° the two mirrors give 5 images, which is what a kaleidoscope uses to make its pattern. The formula works for angles that divide 360 exactly.'],
      precautions: 'Stand the mirror exactly on the ruled line, with its silvered face on the line. Draw the normal at right angles to it. Keep your eye straight above the paper when you read the protractor, and press the pins upright.' },
    book: { title: 'Expt. — Plane mirror: reflection and image', lines: BOOK,
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'i (°)', get: function (r) { return r.i.toFixed(0); } },
        { label: 'r (°)', get: function (r) { return r.r.toFixed(1); } }, { label: 'r − i', get: function (r) { return (r.r - r.i).toFixed(1); } }] },
    graph: { x: function (r) { return r.i; }, y: function (r) { return r.r; }, xlabel: 'i (°)', ylabel: 'r (°)', x0: 0, y0: 0,
      line: function (pts) { var L = S.fit.linear(pts); return L ? function (x) { return L.m * x + L.c; } : null; } },
    result: function (rows) {
      var q = ratio(rows); if (!isFinite(q) || (rows || []).length < 4) return null;
      return { label: 'r / i', value: q, unit: '', digits: 3, truth: 1,
        note: 'The graph of r against i is a straight line through the origin at 45°, so r = i.' +
          (st.imgFound ? ' The image was found ' + (st.dCm).toFixed(1) + ' cm behind the mirror for a pin ' + st.dCm.toFixed(1) + ' cm in front.' : '') };
    },
    tol: 0.02,
    chips: ['Why is r always equal to i?', 'Why is the image virtual?', 'What is lateral inversion?', 'Why do two mirrors give many images?', 'Check my readings'],
    viva: [['A ray falls along the normal. The angle of reflection is?', ['0°', '90°', '180°'], 0, 'i = 0, so r = 0: the ray comes straight back.'],
      ['The image in a plane mirror is?', ['Virtual, erect and the same size', 'Real and inverted', 'Real and smaller'], 0, 'The reflected rays only appear to meet behind the mirror.'],
      ['Two mirrors at 60° give how many images of one object?', ['5', '3', '6'], 0, '360 ÷ 60 − 1 = 5.'],
      ['Why does AMBULANCE appear written backwards on the van?', ['So that a driver ahead reads it correctly in the mirror', 'To save paint', 'It is a mistake'], 0, 'A plane mirror interchanges left and right: lateral inversion.']],
    askState: function () {
      var v = view || sync();
      return { angle_of_incidence_deg: st.iDeg, angle_of_reflection_deg: +(v.r * R2D).toFixed(1),
        pin_in_front_cm: +st.dCm.toFixed(1), image_behind_cm: +(v.img * 100).toFixed(1), image_located: st.imgFound,
        two_mirrors: st.two, angle_between_mirrors_deg: st.thDeg, images_counted: st.two ? Math.round(v.N) : null,
        readings_taken: S.rows.length };
    },

    steps: [
      { id: 'reflection', title: 'The law of reflection', view: 'board', render: function (u) {
          u.h2('Measure i and r');
          u.p('The mirror stands on the ruled line and the normal is drawn at the pole. Turn the ray box so that the beam strikes the pole at the angle you want, then read the reflected beam on the protractor. Take at least four angles.');
          u.task('Ray box', true, 'Beam striking the pole at i = ' + st.iDeg.toFixed(0) + '°');
          u.slider('Angle of incidence i', 10, 80, 1, function () { return st.iSet; }, function (x) { st.iSet = x; }, '°', 0);
          u.row(u.button('Turn the ray box there', function () { turnBeam(st.iSet); S.render(); }, true, S.hand.busy),
            u.button(st.beam ? 'Switch the lamp off' : 'Switch the lamp on', function () { st.beam = !st.beam; update(); S.render(); }),
            u.button('Look from above', function () { S.focus('prot'); }));
          u.live(function () { var v = view || sync(); return 'Protractor: i = ' + st.iDeg.toFixed(0) + '°, r = ' + (v.r * R2D).toFixed(1) + '°'; });
          u.row(u.button('Record i and r', function () { recordAngle(); }, true, S.hand.busy));
          u.h3('Observation table'); u.table();
          u.next('Next: find the image', S.rows.length >= 4);
          if (S.rows.length < 4) u.p(S.rows.length + ' of at least 4 angles recorded.');
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          return [30, 40, 50, 60, 70].reduce(function (pr, a) {
            return pr.then(function () { st.iSet = a; return turnBeam(a); }).then(function () { recordAngle(); });
          }, Promise.resolve());
        } },
      { id: 'image', title: 'Where is the image?', view: 'pins', render: function (u) {
          u.h2('Find the image of a pin');
          u.p('Stick a pin upright in front of the mirror and look at its image from two different directions. Fix two more pins so that they are in line with the image each time; where the two lines cross is where the image is.');
          u.task('Object pin', true, st.dCm.toFixed(1) + ' cm in front of the mirror');
          u.slider('Pin in front of the mirror', 4, 14, 0.5, function () { return st.dSet; }, function (x) { st.dSet = x; }, 'cm', 1);
          u.row(u.button('Move the pin there', function () { st.imgFound = false; movePin(st.dSet); S.render(); }, true, S.hand.busy),
            u.button('Sight the image from two sides', function () { findImage(); }, true, S.hand.busy));
          u.live(function () { var v = view || sync(); return st.imgFound ? 'Image: ' + (v.img * 100).toFixed(1) + ' cm behind the mirror, erect and the same size' : 'Image not located yet'; });
          u.note('The image is virtual: it is behind the mirror, where no light actually reaches, so it cannot be caught on a screen. Hold up a page of writing and see how left and right are interchanged.');
          u.next('Next: two mirrors', st.imgFound);
        },
        ok: function () { return st.imgFound; },
        auto: function () { st.dSet = 9; return movePin(9).then(function () { return findImage(); }); } },
      { id: 'two', title: 'Two inclined mirrors', view: 'mirror2', render: function (u) {
          u.h2('Count the images in two mirrors');
          u.p('Stand the second mirror against the first so that they make an angle, and put the pin on the line that halves that angle. Count how many images you can see. A kaleidoscope is three such mirrors in a tube.');
          u.task('Angle between the mirrors', st.two, st.two ? 'Set at ' + st.thDeg.toFixed(0) + '°' : 'The second mirror is not up yet');
          u.slider('Angle between the mirrors', 30, 120, 1, function () { return st.thSet; }, function (x) { st.thSet = x; }, '°', 0);
          u.row(u.button('Set the mirrors at this angle', function () { setAngle(st.thSet); S.render(); }, true, S.hand.busy),
            u.button('60° (kaleidoscope)', function () { st.thSet = 60; S.render(); }), u.button('90°', function () { st.thSet = 90; S.render(); }),
            u.button('45°', function () { st.thSet = 45; S.render(); }));
          u.live(function () { var v = view || sync(); return st.two ? 'Images seen: ' + Math.round(v.N) : 'Set the mirrors first'; });
          u.row(u.button('Count the images', function () { countImages(); }, true, S.hand.busy || !st.two));
          if (st.counts.length) u.note('Counted so far: ' + st.counts.map(function (a) { return a + '°'; }).join(', ') + '. Each one agrees with 360 ÷ θ − 1.');
          u.next('Next: graph and result', st.counts.length >= 2);
          if (st.counts.length < 2) u.p(st.counts.length + ' of at least 2 angles counted.');
        },
        ok: function () { return st.counts.length >= 2; },
        auto: function () {
          return [60, 90, 45].reduce(function (pr, a) {
            return pr.then(function () { st.thSet = a; return setAngle(a); }).then(function () { countImages(); });
          }, Promise.resolve());
        } },
    ],

    tick: function () { update(); },
  };
});
