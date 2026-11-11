/* Prayogshala studio module: W8 MICROWAVE BENCH (B.Sc. electromagnetic theory lab, pack ug_modern_w8).
   A 3 cm microwave optics goniometer: a Gunn transmitter with a horn on the fixed arm, a receiving horn with a crystal
   detector on the swinging arm over a printed protractor, a turntable in the middle, and the detector meter.
     w8-microwave-reflect        metal reflector (angle of reflection = angle of incidence), then a wax prism (n)
     w8-microwave-interference   polarisation (Malus' law), then a double slit (wavelength from the minima)
   Every reading comes from the `w8_mw` kernel on the lab's own params. */
HoolaStudio.define('w8-microwave-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.w8_mw, assign = HK.assign;
  var p = HK.paramsFor('w8_mw', S.lab.params);
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var MODE = BASE === 'w8-microwave-interference' ? 'int' : 'ref';
  var DEG = Math.PI / 180;
  var st = { on: false, traced: false, part: MODE === 'int' ? 2 : 0, th: 0, inc: 45, phi: 0, obj: 'none' };

  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function wp(o) { var v = new T.Vector3(); o.updateMatrixWorld(true); o.getWorldPosition(v); return v; }
  function reading() { return st.on ? rnd(KN.signal(p, st.part, st.th, st.phi) * 100, 1) : 0; }

  // ================================================================ goniometer
  var CX = -0.2, CZ = -0.12, ARM = 0.34, HY = 0.11;
  var gon = new T.Group(); gon.position.set(CX, 0, CZ); S.scene.add(gon);
  var disc = S.canvasTex(1024, 1024, function (x, w) { x.fillStyle = '#f2ede0'; x.fillRect(0, 0, w, w); x.strokeStyle = '#222'; x.fillStyle = '#222';
    for (var a = 0; a < 360; a++) { var r1 = a % 10 ? 470 : (a % 30 ? 450 : 430), t = a * DEG; x.lineWidth = a % 10 ? 1.5 : 3;
      x.beginPath(); x.moveTo(512 + Math.cos(t) * 500, 512 - Math.sin(t) * 500); x.lineTo(512 + Math.cos(t) * r1, 512 - Math.sin(t) * r1); x.stroke(); }
    x.font = '600 30px "Public Sans", sans-serif'; x.textAlign = 'center';
    for (a = 0; a < 360; a += 30) { var tt = a * DEG, v = a <= 180 ? a : 360 - a; x.fillText(String(v), 512 + Math.cos(tt) * 395, 522 - Math.sin(tt) * 395); } });
  var table = S.mesh(new T.CylinderGeometry(0.2, 0.2, 0.012, 64), [new T.MeshStandardMaterial({ color: 0xcfc7b4 }), new T.MeshStandardMaterial({ map: disc, roughness: 0.6 }), M.grey]);
  table.position.y = 0.04; gon.add(table);
  var leg = S.mesh(new T.CylinderGeometry(0.03, 0.05, 0.034, 32), M.iron); leg.position.y = 0.017; gon.add(leg);
  var hub = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.02, 24), M.chrome); hub.position.y = 0.056; gon.add(hub);
  function horn(color) {
    var g = new T.Group(), bm = new T.MeshStandardMaterial({ color: color, metalness: 0.6, roughness: 0.35 });
    var box = S.mesh(new T.BoxGeometry(0.07, 0.04, 0.05), bm); box.position.x = -0.04; g.add(box);
    var h = S.mesh(new T.CylinderGeometry(0.055, 0.016, 0.09, 4, 1, true), new T.MeshStandardMaterial({ color: 0xa8adb3, metalness: 0.9, roughness: 0.3, side: T.DoubleSide }));
    h.rotation.z = -Math.PI / 2; h.rotation.x = Math.PI / 4; h.position.x = 0.04; g.add(h);
    return g;
  }
  // fixed arm: transmitter pointing at the centre along +x
  var tArm = S.mesh(new T.BoxGeometry(ARM, 0.012, 0.04), M.alu); tArm.position.set(-ARM / 2, 0.052, 0); gon.add(tArm);
  var tx = horn(0x2c5fb4); tx.position.set(-ARM + 0.08, HY, 0); gon.add(tx);
  var txPost = S.mesh(new T.CylinderGeometry(0.006, 0.006, HY - 0.06, 12), M.chrome); txPost.position.set(-ARM + 0.04, (HY + 0.06) / 2, 0); gon.add(txPost);
  var txl = S.label('GUNN TRANSMITTER 10.5 GHz', { w: 0.1, ratio: 0.12, color: '#fff' }); txl.position.set(-ARM + 0.04, HY + 0.021, 0); txl.rotation.x = -Math.PI / 2; gon.add(txl);
  // swinging arm with the receiver; its angle is measured from the straight-through direction
  var rArmG = new T.Group(); rArmG.position.y = 0.06; gon.add(rArmG);
  var rArm = S.mesh(new T.BoxGeometry(ARM, 0.012, 0.04), M.alu); rArm.position.set(ARM / 2, 0, 0); rArmG.add(rArm);
  var ptr = S.mesh(new T.ConeGeometry(0.008, 0.03, 3), M.red); ptr.rotation.z = Math.PI / 2; ptr.position.set(0.21, 0.006, 0); rArmG.add(ptr);
  var rxG = new T.Group(); rxG.position.set(ARM - 0.08, HY - 0.06, 0); rArmG.add(rxG);
  var rx = horn(0x2b2f36); rx.rotation.y = Math.PI; rxG.add(rx);
  var rxPost = S.mesh(new T.CylinderGeometry(0.006, 0.006, HY - 0.06, 12), M.chrome); rxPost.position.set(0.04, -(HY - 0.06) / 2, 0); rxG.add(rxPost);
  // objects on the turntable
  var plate = S.mesh(new T.BoxGeometry(0.004, 0.14, 0.16), M.alu); plate.position.set(0, 0.12, 0); gon.add(plate); plate.visible = false;
  var prism = new T.Group(); gon.add(prism); prism.visible = false;
  (function () {
    var A = p.A * DEG, sh = new T.Shape(); sh.moveTo(0, -0.07); sh.lineTo(0, 0.07); sh.lineTo(0.14 * Math.tan(A), -0.07); sh.lineTo(0, -0.07);
    var geo = new T.ExtrudeGeometry(sh, { depth: 0.1, bevelEnabled: false }); var m = S.mesh(geo, new T.MeshStandardMaterial({ color: 0xf2ead2, roughness: 0.8 }));
    m.rotation.x = -Math.PI / 2; m.position.set(-0.02, 0.046, 0.0); prism.add(m);
    var pl = S.label('PARAFFIN WAX  A = ' + p.A + ' deg', { w: 0.09, ratio: 0.14, color: '#333' }); pl.position.set(0.0, 0.148, 0.06); pl.rotation.x = -Math.PI / 2; prism.add(pl);
  })();
  var slit = new T.Group(); gon.add(slit); slit.visible = false;
  (function () {
    var hw = 0.16, gapC = p.ds, w = p.as_;
    var mid = S.mesh(new T.BoxGeometry(0.004, 0.16, gapC - w), M.alu); mid.position.set(-0.03, 0.13, 0); slit.add(mid);
    var side = (hw - (gapC + w) / 2);
    [-1, 1].forEach(function (sg) { var s = S.mesh(new T.BoxGeometry(0.004, 0.16, side), M.alu); s.position.set(-0.03, 0.13, sg * ((gapC + w) / 2 + side / 2)); slit.add(s); });
    var base = S.mesh(new T.BoxGeometry(0.03, 0.01, 0.3), M.iron); base.position.set(-0.03, 0.051, 0); slit.add(base);
  })();
  S.contact(0.8, 0.45, CX, CZ, 0.45);

  // ================================================================ detector meter
  var meter = S.meter({ min: 0, max: 100, unit: '%', symbol: 'µA', caption: 'CRYSTAL DETECTOR', ticks: 10, pos: [0.33, 0, -0.04], rotY: -0.35 });
  var oscBox = S.powerBox([0.3, 0, 0.14], 'GUNN SUPPLY 9 V');
  var swOn = oscBox.userData.knob;
  S.wire([[CX - ARM + 0.04, 0.03, CZ], [0.0, 0.012, 0.1], [0.26, 0.05, 0.14]], 'red');
  S.wire([[CX + 0.2, 0.03, CZ + 0.05], [0.2, 0.012, 0.0], [0.3, 0.06, -0.06]], 'black');
  S.addApparatus('gon', gon, 'Microwave optics goniometer', 'The transmitter horn on the fixed arm points at the centre; the receiving horn on the swinging arm reads its angle on the protractor through the red pointer.');
  S.addApparatus('meter', meter, 'Detector meter', 'Reads the crystal detector current as a percentage of the straight-through signal.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var hudA = S.hudCard('Receiver angle'), hudI = S.hudCard('Detector');

  function place() {             // arm angle in the room, from the measured angle of the present arrangement
    var a = st.part < 0.5 ? 180 - st.inc - st.th : st.th;
    rArmG.rotation.y = a * DEG;
    plate.rotation.y = -(90 - st.inc) * DEG;
    rxG.rotation.x = st.part > 1.5 && st.part < 2.5 ? st.phi * DEG : 0;
  }
  place();

  // ================================================================ actions
  function power() {
    if (busy()) return Promise.resolve();
    return S.hand.tap(swOn, 'front').then(function () { st.on = true; S.say('The Gunn oscillator is on. With nothing on the table, face the receiver straight at it and the meter reads full scale.'); S.click(820, 0.05); S.render(); });
  }
  function swing(th) {
    if (busy()) return Promise.resolve();
    var lim = st.part < 0.5 ? [0, 85] : [0, 70];
    if (!isFinite(th) || th < lim[0] || th > lim[1]) { S.say('The arm can be read from ' + lim[0] + ' to ' + lim[1] + ' degrees here.'); return Promise.resolve(); }
    th = Math.round(th * 2) / 2; var t0 = st.th; if (th === t0) return Promise.resolve();
    return S.hand.pinchMove(wp(rxG), function () { return wp(rxG); }, function (k) { st.th = t0 + (th - t0) * k; place(); }, { mode: 'top', ms: 400 + 15 * Math.abs(th - t0) })
      .then(function () { st.th = th; place(); S.render(); });
  }
  function setInc(i) {
    if (busy()) return Promise.resolve();
    var i0 = st.inc;
    return S.hand.pinchMove(wp(plate), function () { return wp(plate); }, function (k) { st.inc = i0 + (i - i0) * k; place(); }, { mode: 'side', ms: 500 })
      .then(function () { st.inc = i; place(); S.render(); });
  }
  function turnHorn(phi) {
    if (busy()) return Promise.resolve();
    var f0 = st.phi;
    return S.hand.pinchMove(wp(rxG), function () { return wp(rxG); }, function (k) { st.phi = f0 + (phi - f0) * k; place(); }, { mode: 'side', ms: 500 })
      .then(function () { st.phi = phi; place(); S.render(); });
  }
  function putOn(obj) {
    if (busy()) return Promise.resolve();
    var g = { plate: plate, prism: prism, slit: slit }[obj];
    var pt = wp(gon).add(new T.Vector3(0, 0.14, 0));
    return S.hand.pinchMove(pt.clone().add(new T.Vector3(0.1, 0.1, 0.25)), function (k) { return pt.clone().add(new T.Vector3(0.1 * (1 - k), 0.1 * (1 - k), 0.25 * (1 - k))); }, function () {}, { mode: 'top', ms: 600 })
      .then(function () {
        plate.visible = obj === 'plate'; prism.visible = obj === 'prism'; slit.visible = obj === 'slit'; st.obj = obj;
        st.part = { plate: 0, prism: 1, slit: 3 }[obj]; st.th = 0; st.phi = 0; place();
        S.say({ plate: 'The metal reflector stands on the turntable.', prism: 'The wax prism stands on the turntable, its first face square to the beam.', slit: 'The double slit stands in front of the transmitter.' }[obj]); S.render(); });
  }
  function hunt(dir) {           // swing the arm in 0.5 degree steps while the reading moves the wanted way
    var th = st.th, prev = KN.signal(p, st.part, th, st.phi), best = -1, moving = false, v, lim = st.part < 0.5 ? 85 : 70;
    var r0 = rnd(prev * 100, 1);
    while (th + 0.5 <= lim) {
      th += 0.5; v = rnd(KN.signal(p, st.part, th, st.phi) * 100, 1);
      if (dir > 0) { if (v > r0) moving = true; else if (v < r0 && moving) { best = th - 0.5; break; } }
      else { if (v < r0) moving = true; else if (v > r0 && moving) { best = th - 0.5; break; } }
      r0 = v;
    }
    return best;
  }
  function huntAndRecord(kind, dir) {
    if (busy()) return Promise.resolve(false);
    if (!st.on) { S.say('Switch the oscillator on first.'); return Promise.resolve(false); }
    var b = hunt(dir);
    if (b < 0) { S.say('No further ' + (dir > 0 ? 'maximum' : 'minimum') + ' within the arm\'s range.'); return Promise.resolve(false); }
    return swing(b).then(function () { record(kind); S.say((dir > 0 ? 'Largest' : 'Smallest') + ' reading at ' + st.th.toFixed(1) + ' degrees: ' + reading().toFixed(1) + ' %.'); return true; });
  }
  function record(kind) {
    if (!st.on) { S.say('Switch the oscillator on first.'); return false; }
    var row = { kind: kind, th: st.th, I: reading() };
    if (kind === 'refl') row.inc = st.inc;
    if (kind === 'pol') row.phi = st.phi;
    if (kind === 'min') row.m = S.rows.filter(function (r) { return r.kind === 'min'; }).length;
    S.addRow(row); return true;
  }
  function trace() { st.traced = true; S.focus('gon'); S.say('The transmitter horn is fixed; the receiver horn swings on its arm, and the red pointer reads its angle on the protractor.'); S.render(); }
  function count(k) { return S.rows.filter(function (r) { return r.kind === k; }).length; }

  // ================================================================ steps
  var steps = [{ id: 'on', title: 'Look and switch on', view: 'gon', render: function (u) {
      u.h2('Look at the goniometer, then switch the oscillator on');
      u.task('1. Trace the arms', st.traced, '').add(u.button('Look at the goniometer', trace, !st.traced, st.traced));
      u.task('2. Oscillator on', st.on, '').add(u.button('Switch on', power, !st.on, st.on || S.hand.busy));
      u.next('Next', st.traced && st.on);
    }, ok: function () { return st.traced && st.on; }, auto: function () { trace(); return power(); } }];
  function armUI(u) { var tg = { v: st.th }; u.slider('Swing the receiver arm to', 0, st.part < 0.5 ? 85 : 70, 0.5, function () { return tg.v; }, function (v) { tg.v = v; }, 'deg', 1); return u.button('Swing the arm', function () { swing(tg.v); }, false, S.hand.busy); }
  if (MODE === 'ref') {
    steps.push({ id: 'refl', title: 'Reflection', view: 'gon', render: function (u) {
        u.h2('Angle of reflection'); u.p('Put the metal plate on the table. Set the angle of incidence, then swing the receiver to the largest reading and record the angle of reflection. Use 30, 45 and 60 degrees.');
        if (st.obj !== 'plate') u.row(u.button('Put the metal plate on', function () { putOn('plate'); }, true, S.hand.busy));
        var tg = { v: st.inc };
        u.slider('Angle of incidence', 20, 70, 5, function () { return tg.v; }, function (v) { tg.v = v; }, 'deg', 0);
        u.row(u.button('Turn the plate', function () { setInc(tg.v); }, false, S.hand.busy || st.obj !== 'plate'), armUI(u));
        u.row(u.button('Find the largest reading', function () { st.th = 0; place(); huntAndRecord('refl', 1); }, true, S.hand.busy || st.obj !== 'plate'));
        u.live(function () { return 'i ' + st.inc + ' deg  ·  arm ' + st.th.toFixed(1) + ' deg  ·  ' + reading().toFixed(1) + ' %'; });
        u.table(); u.next('Next: refraction', count('refl') >= 3);
      }, ok: function () { return count('refl') >= 3; },
      auto: function () { var c = putOn('plate'); [30, 45, 60].forEach(function (i) { c = c.then(function () { return setInc(i); }).then(function () { return swing(0); }).then(function () { return huntAndRecord('refl', 1); }); }); return c; } });
    steps.push({ id: 'refr', title: 'Refraction by the prism', view: 'gon', render: function (u) {
        u.h2('Deviation by the wax prism'); u.p('Replace the plate by the prism, first face square to the beam. Swing the receiver to the largest reading: that angle is the deviation d.');
        if (st.obj !== 'prism') u.row(u.button('Put the prism on', function () { putOn('prism'); }, true, S.hand.busy));
        u.row(armUI(u), u.button('Find the largest reading', function () { st.th = 0; place(); huntAndRecord('refr', 1); }, true, S.hand.busy || st.obj !== 'prism'));
        u.live(function () { return 'arm ' + st.th.toFixed(1) + ' deg  ·  ' + reading().toFixed(1) + ' %'; });
        u.table(); u.next('Next: result', count('refr') >= 1);
      }, ok: function () { return count('refr') >= 1; },
      auto: function () { return putOn('prism').then(function () { return huntAndRecord('refr', 1); }); } });
  } else {
    steps.push({ id: 'pol', title: 'Polarisation', view: 'gon', render: function (u) {
        u.h2('Turn the receiving horn about the beam'); u.p('With the receiver straight opposite the transmitter, turn its horn in steps of 15 degrees and record the reading. It should follow cos^2.');
        var tg = { v: st.phi };
        u.slider('Horn rotation', 0, 90, 15, function () { return tg.v; }, function (v) { tg.v = v; }, 'deg', 0);
        u.row(u.button('Turn the horn', function () { turnHorn(tg.v); }, false, S.hand.busy), u.button('Record', function () { record('pol'); }, true, S.hand.busy));
        u.live(function () { return 'horn ' + st.phi + ' deg  ·  ' + reading().toFixed(1) + ' %  ·  cos^2 x 100 = ' + (Math.pow(Math.cos(st.phi * DEG), 2) * 100).toFixed(1); });
        u.table(); u.next('Next: double slit', count('pol') >= 4);
      }, ok: function () { return count('pol') >= 4; },
      auto: function () { var c = Promise.resolve(); [0, 15, 30, 45, 60, 75, 90].forEach(function (f) { c = c.then(function () { return turnHorn(f); }).then(function () { record('pol'); }); }); return c.then(function () { return turnHorn(0); }); } });
    steps.push({ id: 'slit', title: 'Double slit', view: 'gon', render: function (u) {
        u.h2('Find the minima of the pattern'); u.p('Put the double slit in front of the transmitter. Swing the receiver out from 0 degrees and mark every minimum of the reading.');
        if (st.obj !== 'slit') u.row(u.button('Put the double slit on', function () { putOn('slit'); }, true, S.hand.busy));
        u.row(armUI(u), u.button('Find the next minimum', function () { huntAndRecord('min', -1); }, true, S.hand.busy || st.obj !== 'slit'));
        u.live(function () { return 'arm ' + st.th.toFixed(1) + ' deg  ·  ' + reading().toFixed(1) + ' %'; });
        u.table(); u.next('Next: result', count('min') >= 2);
      }, ok: function () { return count('min') >= 2; },
      auto: function () { var c = putOn('slit'); for (var k = 0; k < 3; k++) c = c.then(function () { return huntAndRecord('min', -1); }); return c; } });
  }

  // ================================================================ result
  function result(rows) {
    if (MODE === 'ref') {
      var rr = rows.filter(function (r) { return r.kind === 'refr'; }); if (!rr.length) return null;
      var n = rr.map(function (r) { return Math.sin((p.A + r.th) * DEG) / Math.sin(p.A * DEG); }).reduce(function (a, b) { return a + b; }, 0) / rr.length;
      var rf = rows.filter(function (r) { return r.kind === 'refl'; });
      return { label: 'Refractive index of the wax prism', value: n, unit: '', digits: 3, truth: p.n,
        note: 'n = sin(A + d)/sin A with A = ' + p.A + ' deg.' + (rf.length ? ' Reflection: ' + rf.map(function (r) { return 'i ' + r.inc + ' / r ' + r.th.toFixed(1); }).join(', ') + ' degrees.' : '') };
    }
    var mn = rows.filter(function (r) { return r.kind === 'min'; }); if (mn.length < 2) return null;
    var f = S.fit.linear(mn.map(function (r, i) { return [i + 0.5, Math.sin(r.th * DEG)]; })); if (!f) return null;
    return { label: 'Wavelength of the microwaves', value: f.m * p.ds * 100, unit: 'cm', digits: 3, truth: p.lam * 100,
      note: 'Slope of sin(theta) against m + 1/2 over ' + mn.length + ' minima, times the slit spacing ' + (p.ds * 100).toFixed(1) + ' cm.' };
  }
  var columns = [{ label: 'S.No', get: function (r, i) { return i + 1; } },
    { label: 'What', get: function (r) { return { refl: 'reflection', refr: 'prism', pol: 'polarisation', min: 'minimum ' + (r.m + 1) }[r.kind]; } },
    { label: MODE === 'ref' ? 'i (deg)' : 'horn (deg)', get: function (r) { return r.kind === 'refl' ? String(r.inc) : r.kind === 'pol' ? String(r.phi) : '-'; } },
    { label: 'arm (deg)', get: function (r) { return r.th.toFixed(1); } },
    { label: 'reading (%)', get: function (r) { return r.I.toFixed(1); } }];

  return {
    camera: { pos: [0.0, 1.0, 1.35], look: [-0.08, 0.08, -0.1] },
    views: { gon: [[-0.2, 0.62, 0.55], [-0.2, 0.1, -0.12]], meter: [[0.36, 0.3, 0.3], [0.33, 0.05, -0.04]],
      bench: [[0.0, 1.0, 1.35], [-0.08, 0.08, -0.1]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: MODE === 'ref' ? 'Microwaves reflect from metal with r = i, and a prism deviates them: sin(A + d) = n sin A for normal incidence on the first face.'
      : 'The crystal detector reads cos^2 of the angle between the field and the horn (Malus). Two slits give minima where d sin(theta) = (m + 1/2) lam.',
      formula: MODE === 'ref' ? 'n = sin(A + d) / sin A' : 'lam = d x slope of sin(theta) against (m + 1/2)',
      formulaNote: MODE === 'ref' ? 'A = prism angle, d = deviation' : 'd = centre spacing of the slits (' + (p.ds * 100).toFixed(1) + ' cm)',
      more: ['The detector is square-law: its current is proportional to the power, not the field.', 'Reflections from the bench and walls can add false peaks: keep the space beyond the receiver clear.'],
      precautions: 'Read the arm angle with the eye straight above the pointer. Approach every peak or minimum in small steps.' },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 120)], columns: columns },
    graph: MODE === 'ref' ? { x: function (r) { return r.kind === 'refl' ? r.inc : NaN; }, y: function (r) { return r.kind === 'refl' ? r.th : NaN; }, xlabel: 'i (deg)', ylabel: 'r (deg)', x0: 0, y0: 0 }
      : { x: function (r) { return r.kind === 'pol' ? Math.pow(Math.cos(r.phi * DEG), 2) : NaN; }, y: function (r) { return r.kind === 'pol' ? r.I : NaN; }, xlabel: 'cos^2(horn angle)', ylabel: 'reading (%)', x0: 0, y0: 0 },
    result: result,
    tol: 0.02,
    chips: ['What am I measuring?', 'Check my readings', 'Why does the reading fall to zero?'],
    viva: [['A crystal detector reading is proportional to', ['The power of the wave', 'The field', 'The frequency'], 0, 'It is a square-law detector.']],
    askState: function () { return { experiment: S.lab.title, oscillator_on: st.on, on_table: st.obj, arm_angle_deg: st.th, incidence_deg: st.inc, horn_rotation_deg: st.phi, detector_percent: reading(), readings_taken: S.rows.length }; },
    steps: steps,
    tick: function () { meter.set(reading()); hudA.set(st.th.toFixed(1) + ' deg'); hudI.set(reading().toFixed(1) + ' %'); }
  };
});
