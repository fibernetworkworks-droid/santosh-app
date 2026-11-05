/* Prayogshala studio module: DIFFRACTION AT A SINGLE SLIT (NCERT Class XII, Section B activity).
   A laser on an optical bench, a narrow slit in a metal slide, and a white screen that slides along the bench. The
   pattern drawn on the screen is the real intensity from this lab's kernel (packs/elec11.js: the Fraunhofer
   sinc-squared, traced to the screen through the true angle, never through the small-angle formula), and the dark
   fringes are found on that same intensity, with a travelling microscope the hand slides across the screen. */
HoolaStudio.define('laser-diffraction', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.diffraction;
  var p = HK.paramsFor('diffraction', S.lab.params);
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || '';
  var LAM_NM = Math.round(p.lam * 1e9 * 10) / 10;
  var RED = /63[23]|6[45]\d|7\d\d/.test(String(LAM_NM)) || LAM_NM > 600;
  var BEAM = LAM_NM < 500 ? 0x4a6bff : LAM_NM < 560 ? 0x36d94a : LAM_NM < 600 ? 0xf2c21b : 0xe02718;
  var XL = -0.6, DMIN = 0.5, DMAX = 1.0;             // the slit sits at x = XL; the screen at x = XL + D
  var st = { traced: false, on: false, D: p.D, cur: 0.0, left: null, right: null, order: 1 };

  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function mm(v) { return (v * 1000).toFixed(2); }

  // ---------------------------------------------------------------- bench, laser, slit
  var BZ = -0.26, BY = 0.03;
  var bench = S.opticalBench({ len: 1.5, x0: -0.75, z: BZ });
  var laser = new T.Group(); S.scene.add(laser); laser.position.set(XL - 0.14, 0, BZ);
  var lsad = S.rounded(0.034, 0.03, 0.06, 0.004, M.alu); lsad.rotation.x = -Math.PI / 2; lsad.position.y = 0.045; laser.add(lsad);
  var lpost = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.05, 18), M.chrome); lpost.position.y = 0.08; laser.add(lpost);
  var ltube = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.1, 28), new T.MeshStandardMaterial({ color: 0x2a2d33, roughness: 0.4, metalness: 0.5 }));
  ltube.rotation.z = Math.PI / 2; ltube.position.y = 0.105; laser.add(ltube);
  var lhead = S.mesh(new T.CylinderGeometry(0.009, 0.011, 0.012, 24), M.chrome); lhead.rotation.z = Math.PI / 2; lhead.position.set(0.055, 0.105, 0); laser.add(lhead);
  var llab = S.label(LAM_NM + ' nm', { w: 0.05, ratio: 0.28, color: '#e6e7ea' }); llab.position.set(-0.01, 0.105, 0.0142); laser.add(llab);
  var lampM = new T.MeshStandardMaterial({ color: 0x3a1410, roughness: 0.4 });
  var pilot = S.mesh(new T.SphereGeometry(0.004, 14, 10), lampM); pilot.position.set(-0.03, 0.118, 0.012); laser.add(pilot);
  var lsw = S.mesh(new T.BoxGeometry(0.012, 0.006, 0.01), M.bakelite); lsw.position.set(-0.03, 0.118, -0.012); laser.add(lsw);
  S.contact(0.14, 0.1, XL - 0.14, BZ, 0.5);

  var slit = new T.Group(); S.scene.add(slit); slit.position.set(XL, 0, BZ);
  var ssad = S.rounded(0.034, 0.03, 0.06, 0.004, M.alu); ssad.rotation.x = -Math.PI / 2; ssad.position.y = 0.045; slit.add(ssad);
  var spost = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.05, 18), M.chrome); spost.position.y = 0.08; slit.add(spost);
  var plate = S.mesh(new T.BoxGeometry(0.0015, 0.06, 0.05), new T.MeshStandardMaterial({ color: 0x3c4046, roughness: 0.35, metalness: 0.8 }));
  plate.position.y = 0.105; slit.add(plate);
  var gap = S.mesh(new T.BoxGeometry(0.002, 0.03, 0.0012), new T.MeshBasicMaterial({ color: 0x101014 })); gap.position.y = 0.105; slit.add(gap);
  var slab2 = S.label('SINGLE SLIT', { w: 0.04, ratio: 0.16, color: '#2b2f36' }); slab2.rotation.x = -Math.PI / 2;
  slab2.position.set(XL, 0.0012, BZ + 0.05); S.scene.add(slab2);
  S.contact(0.1, 0.1, XL, BZ, 0.45);

  // ---------------------------------------------------------------- the screen, with the pattern drawn on its face
  var SW = 0.1, SH = 0.08;                            // screen face: SW across (z), SH high (y)
  var screen = new T.Group(); S.scene.add(screen);
  var csad = S.rounded(0.034, 0.03, 0.07, 0.004, M.alu); csad.rotation.x = -Math.PI / 2; csad.position.y = 0.045; screen.add(csad);
  var cpost = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.06, 18), M.chrome); cpost.position.y = 0.075; screen.add(cpost);
  var frame = S.mesh(new T.BoxGeometry(0.004, SH + 0.012, SW + 0.012), M.blackPlastic); frame.position.y = 0.112; screen.add(frame);
  var patTex = S.liveTex(1024, 512);
  var faceM = new T.MeshBasicMaterial({ map: patTex, toneMapped: false });
  var faceP = new T.Mesh(new T.PlaneGeometry(SW, SH), faceM);
  faceP.rotation.y = -Math.PI / 2; faceP.position.set(-0.0025, 0.112, 0); screen.add(faceP);
  // the travelling microscope: a carriage on the screen's own rail, reading to 0.01 mm
  var carr = new T.Group(); screen.add(carr);
  var rail = S.mesh(new T.BoxGeometry(0.008, 0.006, SW + 0.02), M.alu); rail.position.set(-0.012, 0.064, 0); screen.add(rail);
  var cbody = S.rounded(0.016, 0.02, 0.012, 0.002, M.brass); cbody.position.set(-0.014, 0.072, 0); carr.add(cbody);
  var cline = S.mesh(new T.BoxGeometry(0.001, SH, 0.0008), new T.MeshBasicMaterial({ color: 0x101014 })); cline.position.set(-0.004, 0.112, 0); carr.add(cline);
  var cknob = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.006, 16), M.blackPlastic); cknob.rotation.x = Math.PI / 2; cknob.position.set(-0.014, 0.082, 0); carr.add(cknob);
  var sShadow = S.contact(0.12, 0.12, 0, BZ, 0.45);
  function placeScreen(D) { screen.position.set(XL + D, 0, BZ); sShadow.position.x = XL + D; }
  function placeCursor(x) { carr.position.set(0, 0, x); }
  placeScreen(st.D); placeCursor(0);

  // the beam from the laser to the slit (a thin line: in a real dark room only its ends are seen)
  var beam = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 0.13, 10), new T.MeshBasicMaterial({ color: BEAM, transparent: true, opacity: 0 }));
  beam.rotation.z = Math.PI / 2; beam.position.set(XL - 0.07, 0.105, BZ); S.scene.add(beam);
  var spot = new T.Mesh(new T.CircleGeometry(0.0035, 20), new T.MeshBasicMaterial({ color: BEAM, transparent: true, opacity: 0 }));
  spot.rotation.y = -Math.PI / 2; spot.position.set(XL - 0.0012, 0.105, BZ); S.scene.add(spot);

  // ---------------------------------------------------------------- physics: the lab's own kernel
  function view(over) { var q = HK.assign(p, over || {}); return KN.view(KN.init(q, q), q, q); }
  // the brightness at one point of the screen, straight from the kernel's own intensity (no need for the whole view)
  function inten(x) { return KN.intenAt(x, HK.assign(p, { D: st.D })); }
  var patKey = '';
  function drawPattern() {
    var k = st.D.toFixed(4) + st.on;
    if (k === patKey) return; patKey = k;
    patTex.draw(function (c, w, h) {
      c.fillStyle = '#f2f0ea'; c.fillRect(0, 0, w, h);
      if (!st.on) { c.fillStyle = '#9aa0a8'; c.font = '600 30px "Public Sans", sans-serif'; c.textAlign = 'center';
        c.fillText('laser off', w / 2, h / 2 + 10); return; }
      var col = new T.Color(BEAM);
      for (var i = 0; i < w; i++) {
        var x = (i / (w - 1) - 0.5) * SW;             // the screen face is SW wide; the texture's +u is +z
        var I = Math.min(1, inten(x));
        var g = Math.pow(I, 0.42);                     // the eye sees faint fringes far better than a linear scale shows
        c.fillStyle = 'rgb(' + Math.round(242 + (col.r * 255 - 242) * g) + ',' + Math.round(240 + (col.g * 255 - 240) * g) + ',' + Math.round(234 + (col.b * 255 - 234) * g) + ')';
        c.fillRect(i, h * 0.18, 1, h * 0.64);
      }
      c.fillStyle = 'rgba(20,20,22,.5)'; c.fillRect(0, h * 0.82, w, 2);
      c.font = '600 22px "Public Sans", sans-serif'; c.fillStyle = '#4a4f57'; c.textAlign = 'center';
      c.fillText('SCREEN  ' + Math.round(SW * 1000) + ' mm across', w / 2, h * 0.95);
    });
  }
  // the dark fringes, read off the pattern on the screen (a scan for the band, then the darkest point inside it)
  function minima() {
    var out = [], step = 0.00005, prev2 = inten(-SW / 2), prev = inten(-SW / 2 + step), x;
    for (var i = 2; i * step - SW / 2 <= SW / 2; i++) {
      x = -SW / 2 + i * step;
      var now2 = inten(x);
      if (prev < prev2 && prev <= now2) out.push(x - step);
      prev2 = prev; prev = now2;
    }
    return out;
  }
  function refine(x0) {                                 // the darkest point of that band, to the microscope's 0.01 mm
    var lo = x0 - 0.00008, hi = x0 + 0.00008, a1, a2;
    for (var i = 0; i < 60; i++) {
      a1 = lo + (hi - lo) / 3; a2 = hi - (hi - lo) / 3;
      if (inten(a1) < inten(a2)) hi = a2; else lo = a1;
    }
    return rnd((lo + hi) / 2, 5);
  }
  function bandAt(m, side) {
    var all = minima().filter(function (x) { return side < 0 ? x < -1e-6 : x > 1e-6; });
    all.sort(function (a, b) { return Math.abs(a) - Math.abs(b); });
    return all.length >= m ? refine(all[m - 1]) : null;
  }
  var hudA = S.hudCard('Screen distance D'), hudB = S.hudCard('Microscope at'), hudC = S.hudCard('Brightness there');

  // ---------------------------------------------------------------- human actions
  function trace() {
    st.traced = true; S.focus('bench');
    S.say('The laser lights the single slit from the left; the pattern falls on the screen ' + Math.round(st.D * 100) + ' centimetres beyond it. The microscope on the screen reads across the pattern to 0.01 mm.');
    S.render();
  }
  function setLaser(on) {
    if (busy()) return Promise.resolve();
    if (on === st.on) return Promise.resolve();
    return S.hand.tap(lsw, 'top').then(function () {
      st.on = on;
      lampM.color.setHex(on ? 0xff3b2a : 0x3a1410); lampM.emissive = new T.Color(on ? 0xff2a14 : 0x000000); lampM.emissiveIntensity = on ? 2.4 : 0;
      beam.material.opacity = on ? 0.5 : 0; spot.material.opacity = on ? 0.9 : 0;
      drawPattern(); S.click(1100, 0.04); S.say(on ? 'The laser is on. Never look into the beam.' : 'Laser off.'); S.render();
    });
  }
  function setD(D) {
    if (busy()) return Promise.resolve(false);
    if (!(D >= DMIN && D <= DMAX)) { S.say('Keep the screen between ' + Math.round(DMIN * 100) + ' cm and ' + Math.round(DMAX * 100) + ' cm from the slit.'); return Promise.resolve(false); }
    D = rnd(D, 3);
    var D0 = st.D;
    return S.hand.pinchMove(new T.Vector3(XL + D0, 0.05, BZ + 0.03), function (k) { return new T.Vector3(XL + D0 + (D - D0) * k, 0.05, BZ + 0.03); },
      function (k) { st.D = D0 + (D - D0) * k; placeScreen(st.D); }, { mode: 'top', ms: 800, reachMs: 650 })
      .then(function () { st.D = D; placeScreen(D); st.left = st.right = null; drawPattern();
        S.say('Screen at ' + Math.round(D * 100) + ' cm from the slit.'); S.render(); return true; });
  }
  function setCursor(x) {
    if (busy()) return Promise.resolve(false);
    if (!(x >= -SW / 2 && x <= SW / 2)) { S.say('The microscope runs across the screen only.'); return Promise.resolve(false); }
    var x0 = st.cur;
    return S.hand.pinchMove(wpt(screen, -0.014, 0.086, x0), function (k) { return wpt(screen, -0.014, 0.086, x0 + (x - x0) * k); },
      function (k) { st.cur = x0 + (x - x0) * k; placeCursor(st.cur); }, { mode: 'top', ms: 600, reachMs: 600 })
      .then(function () { st.cur = rnd(x, 5); placeCursor(st.cur); S.render(); return true; });
  }
  function seek(m, side) {
    var x = bandAt(m, side);
    if (x === null) { S.say('That dark fringe is beyond the edge of the screen. Bring the screen nearer.'); return Promise.resolve(false); }
    return setCursor(x);
  }
  function mark(side) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.on) { S.say('Switch the laser on first.'); return false; }
    if (side < 0 && st.cur > 0) { S.say('That is on the right of the centre. Move the microscope to the left side.'); return false; }
    if (side > 0 && st.cur < 0) { S.say('That is on the left of the centre. Move the microscope to the right side.'); return false; }
    if (side < 0) st.left = st.cur; else st.right = st.cur;
    S.say((side < 0 ? 'Left' : 'Right') + ' reading noted: ' + mm(st.cur) + ' mm.');
    S.render(); return true;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (st.left === null || st.right === null) { S.say('Note the fringe on both sides of the centre first.'); return false; }
    var half = (st.right - st.left) / 2;
    if (!(half > 0.0002)) { S.say('The two readings are too close together: check that they are the same dark fringe on opposite sides.'); return false; }
    if (S.rows.some(function (r) { return r.m === st.order && Math.abs(r.D - st.D) < 0.005; })) { S.say('You already have fringe ' + st.order + ' at this screen distance.'); return false; }
    S.addRow({ D: st.D, m: st.order, xl: st.left, xr: st.right });
    S.say('Written in your record book: fringe ' + st.order + ', left ' + mm(st.left) + ' mm, right ' + mm(st.right) + ' mm.');
    st.left = st.right = null;
    return true;
  }
  function aOf(r) { return r.m * p.lam * r.D / ((r.xr - r.xl) / 2); }
  function result(rows) {
    var vs = rows.map(aOf).filter(isFinite);
    if (vs.length < 3) return null;
    return { label: 'Slit width a', value: S.fit.mean(vs) * 1000, unit: 'mm', digits: 4, truth: p.a * 1000,
      note: 'Mean of a = m λ D / x over your readings, with λ = ' + LAM_NM + ' nm. The fringes move out in proportion to D, which is the check that the pattern really is diffraction.' };
  }

  S.addApparatus('bench', bench, 'Optical bench', 'Carries the laser, the slit and the screen in one straight line.');
  S.addApparatus('laser', laser, 'Laser (' + LAM_NM + ' nm)' + (SAMPLE ? ' — ' + SAMPLE : ''), 'A single wavelength, which is what makes the fringes sharp. Never look into the beam.');
  S.addApparatus('slit', slit, 'Single slit', 'A narrow slit cut in a metal slide. Its width is what the experiment measures.');
  S.addApparatus('screen', screen, 'Screen with a travelling microscope', 'The pattern falls here. The microscope slides across it and reads to 0.01 mm.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  return {
    camera: { pos: [-0.15, 1.02, 1.0], look: [-0.15, 0.08, -0.24] },
    views: { bench: [[-0.15, 0.96, 0.94], [-0.15, 0.08, -0.24]],
      screen: [[-0.14, 0.2, 0.06], [0.24, 0.112, -0.26]],
      slit: [[XL - 0.12, 0.17, -0.02], [XL, 0.105, -0.26]],
      laser: [[XL - 0.3, 0.2, 0.0], [XL - 0.14, 0.1, -0.26]],
      book: [[-0.5, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A slit narrow enough to be comparable with the wavelength spreads light instead of casting a sharp shadow. Light from the two halves of the slit arrives at the screen along slightly different paths, and in the directions where the extra path across the whole slit is a whole number of wavelengths the waves cancel completely.',
      formula: 'a sin θ = m λ,  so  a = m λ D / x',
      formulaNote: 'x is the m-th dark fringe\'s distance from the centre, taken as half the distance between the two sides',
      more: ['The central bright band is twice as wide as the others, and the bands further out are much fainter: the pattern on the screen is the real sinc-squared curve, not a row of equal fringes.',
        'Because x grows in proportion to D, moving the screen back is the simplest way to check that the pattern is diffraction and not a shadow.'],
      precautions: 'Never look into the laser beam or at a reflection of it. Darken the room, keep the screen square to the beam, and always measure the same fringe on both sides of the centre, so that a slightly off-centre pattern cancels out.' },
    book: { title: 'Expt. — Diffraction at a single slit', at: [-0.5, 0.1, 0.1],
      lines: ['Aim: to study diffraction at a single slit', 'and to find the width of the slit.',
        'Laser ' + LAM_NM + ' nm' + (SAMPLE ? ' (' + SAMPLE + ')' : ''), 'Microscope on the screen reads to 0.01 mm',
        'a sin θ = m λ,   a = m λ D / x', 'x = (right − left) / 2'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'D (cm)', get: function (r) { return Math.round(r.D * 100); } },
        { label: 'Fringe m', get: function (r) { return r.m; } },
        { label: 'Left (mm)', get: function (r) { return mm(r.xl); } },
        { label: 'Right (mm)', get: function (r) { return mm(r.xr); } },
        { label: 'a (mm)', get: function (r) { return (aOf(r) * 1000).toFixed(4); } }] },
    graph: { x: function (r) { return r.m * r.D; }, y: function (r) { return (r.xr - r.xl) / 2 * 1000; },
      xlabel: 'm × D (m)', ylabel: 'x (mm)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: result,
    tol: 0.02,
    resultNote: 'Every fringe and every screen distance should give the same slit width: that is what the straight line through the origin shows.',
    chips: ['Why does the light spread at all?', 'Why is the central band the widest?', 'Check my readings', 'What happens with a narrower slit?'],
    viva: [['If the slit is made narrower, the pattern', ['Spreads out', 'Shrinks', 'Does not change'], 0, 'x = mλD/a.'],
      ['Why is the central maximum twice as wide as the others?', ['It runs from the first dark fringe on one side to the first on the other', 'The slit is wider there', 'The laser is brighter at the centre'], 0,
        'The first minima lie at ±λD/a, so the central band is 2λD/a wide.'],
      ['Why must the same fringe be measured on both sides?', ['So that an off-centre pattern cancels out', 'To save time', 'Because one side is brighter'], 0,
        'Half the distance between the two readings is the true x, whatever the zero of the scale.']],
    askState: function () {
      return { experiment: 'diffraction of laser light at a single slit', wavelength_nm: LAM_NM,
        laser_on: st.on, screen_distance_cm: Math.round(st.D * 100), microscope_mm: +mm(st.cur),
        brightness_at_the_cursor: +inten(st.cur).toFixed(4), fringe_being_measured: st.order,
        left_reading_mm: st.left === null ? null : +mm(st.left), right_reading_mm: st.right === null ? null : +mm(st.right),
        readings_taken: S.rows.length };
    },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Line the bench up and switch the laser on');
          u.p('The laser, the slit and the screen stand in one straight line. The room is dark, so only the pattern is seen.');
          u.task('1. Trace the set-up', st.traced, st.traced ? 'Laser, slit and screen in line' : 'Follow the beam from the laser')
            .add(u.button(st.traced ? 'Traced' : 'Trace the set-up', trace, !st.traced, st.traced));
          u.task('2. Switch the laser on', st.on, st.on ? 'The pattern is on the screen' : 'The laser is off')
            .add(u.button(st.on ? 'Laser is on' : 'Switch the laser on', function () { S.focus('laser'); setLaser(true); }, !st.on, st.on || S.hand.busy));
          var sd = { v: Math.round(st.D * 100) };
          u.slider('Screen distance from the slit', Math.round(DMIN * 100), Math.round(DMAX * 100), 1, function () { return sd.v; }, function (v) { sd.v = v; }, 'cm', 0);
          u.row(u.button('Slide the screen there', function () { setD(sd.v / 100); }, false, S.hand.busy),
            u.button('Look at the screen', function () { S.focus('screen'); }, false, false));
          u.note('Never look into the beam. Keep the screen square to it, or one side of the pattern comes out longer than the other.');
          u.next('Next: measure the fringes', st.traced && st.on);
        },
        ok: function () { return st.traced && st.on; },
        auto: function () { trace(); return setLaser(true).then(function () { return setD(0.6); }); } },
      { id: 'measure', title: 'Measure', view: 'screen', render: function (u) {
          u.h2('Measure the dark fringes');
          u.p('Slide the microscope to a dark fringe on the left of the centre and note the reading, then to the same fringe on the right, and record the pair.');
          var row = u.row();
          [1, 2, 3].forEach(function (m) { row.appendChild(u.button('Fringe ' + m, function () { st.order = m; st.left = st.right = null; S.render(); }, st.order === m, S.hand.busy)); });
          u.row(u.button('Go to fringe ' + st.order + ' on the left', function () { seek(st.order, -1); }, true, S.hand.busy || !st.on),
            u.button('Note as left', function () { mark(-1); }, false, S.hand.busy));
          u.row(u.button('Go to fringe ' + st.order + ' on the right', function () { seek(st.order, 1); }, true, S.hand.busy || !st.on),
            u.button('Note as right', function () { mark(1); }, false, S.hand.busy));
          var cu = { v: +mm(st.cur) };
          u.slider('Microscope by hand', -Math.round(SW * 500), Math.round(SW * 500), 0.05, function () { return cu.v; }, function (v) { cu.v = v; }, 'mm', 2);
          u.row(u.button('Slide the microscope here', function () { setCursor(cu.v / 1000); }, false, S.hand.busy),
            u.button('Record this fringe', function () { record(); }, true, S.hand.busy));
          u.live(function () { return 'Microscope at ' + mm(st.cur) + ' mm  ·  brightness there ' + inten(st.cur).toFixed(4)
            + (st.left === null ? '' : '  ·  left ' + mm(st.left) + ' mm') + (st.right === null ? '' : '  ·  right ' + mm(st.right) + ' mm'); });
          u.h3('Observation table'); u.table();
          var sd2 = { v: Math.round(st.D * 100) };
          u.h3('Move the screen and do it again');
          u.slider('Screen distance', Math.round(DMIN * 100), Math.round(DMAX * 100), 5, function () { return sd2.v; }, function (v) { sd2.v = v; }, 'cm', 0);
          u.row(u.button('Slide the screen', function () { setD(sd2.v / 100); }, false, S.hand.busy));
          if (S.rows.length < 4) u.p(S.rows.length + ' of at least 4 readings recorded.');
          u.next('Next: the slit width', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          function sweep() {
            return [1, 2, 3].reduce(function (pr, m) {
              return pr.then(function () { st.order = m; st.left = st.right = null; return seek(m, -1); })
                .then(function () { mark(-1); return seek(m, 1); })
                .then(function () { mark(1); record(); });
            }, Promise.resolve());
          }
          return sweep().then(function () { return setD(0.9); }).then(sweep);
        } },
    ],
    tick: function () {
      drawPattern();
      hudA.set(Math.round(st.D * 100) + ' cm');
      hudB.set(mm(st.cur) + ' mm');
      hudC.set(st.on ? inten(st.cur).toFixed(4) : 'dark');
    },
  };
});
