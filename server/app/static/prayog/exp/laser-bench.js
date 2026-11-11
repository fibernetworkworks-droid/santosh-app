/* Prayogshala studio module: THE LASER BENCH. One rig for three B.Sc. set-ups - the wavelength of a laser from
   double-slit fringes, the wavelength and angular spread from a plane grating, and the track spacing of a compact
   disc used as a reflection grating. A low-power laser is clamped on an optical rail at bench height (never at eye
   level), the slide sits in a holder, and the pattern falls on a white screen carrying a scale and a vernier cursor.
   The gloved hand switches the laser on, drops the slide into the holder, slides the screen along the rail and runs
   the cursor from one fringe to the next. Both the pattern on the screen and the magnified strip in the HUD are
   drawn from the kernels' own intensity (`doubleslit` = the single-slit envelope times the two-slit term,
   `gratingscreen` = the N-slit intensity), and every fringe is found where that intensity is greatest. */
HoolaStudio.define('laser-bench', function (S) {
  var T = S.T, M = S.M;
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var MODE = BASE === 'laser-double-slit' ? 'dslit' : BASE === 'cd-track-spacing' ? 'cd' : 'grating';
  var DSLIT = MODE === 'dslit';
  var K = DSLIT ? window.HoolaKernels.K.doubleslit : window.HoolaKernels.K.gratingscreen;
  var p = window.HoolaKernels.paramsFor(DSLIT ? 'doubleslit' : 'gratingscreen', S.lab.params);
  (S.lab.knobs || []).forEach(function (k) {
    if (k.hidden && isFinite(k.value) && p[k.param] !== undefined) p[k.param] = +k.value * (+k.k || 1);
  });
  var LC = DSLIT ? 5e-5 : 5e-4;                         // cursor: a vernier slide (0.05 mm) or a millimetre scale
  var AXY = 0.145, BZ = -0.26, X0 = -0.92, RAIL = 1.84; // beam height, rail z, rail start and length
  var CDM = MODE === 'cd';
  var SLIDE_X = CDM ? 0.55 : X0 + 0.1;                  // where the slit, grating or disc stands
  var SIGN = CDM ? -1 : 1;                              // a disc throws its orders BACK, onto a screen in front of it
  var MULTI = DSLIT || CDM;                             // these two are measured at several screen distances
  var HALF = 0.19;                                      // half width of the screen card
  function scrX() { return SLIDE_X + SIGN * st.D; }
  var st = { on: false, placed: false, aligned: false, D: p.D, DSet: p.D, c: 0, cSet: 0, hold: null, holdK: null };

  function fmt(v, d) { return (Math.round(v * Math.pow(10, d)) / Math.pow(10, d)).toFixed(d); }
  function roundLC(x) { return Math.round(x / LC) * LC; }
  function lamNm() { return p.lam * 1e9; }
  function beamColour() { var nm = lamNm();
    return nm < 500 ? 0x4466ee : nm < 560 ? 0x3fd06a : 0xff2d2d; }
  function cssColour() { var nm = lamNm();
    return nm < 500 ? [80, 110, 240] : nm < 560 ? [70, 215, 110] : [255, 60, 50]; }

  // ---------------------------------------------------------------- physics from the kernel
  function P() { return Object.assign({}, p, { D: st.D }); }
  var SPOT = 6e-4;                                      // the laser beam's own width on the screen, metres
  function inten(x) {
    if (DSLIT) return K.intenAt(x, P());
    // an order is as wide as the beam, not as the grating's own razor-thin maximum: draw each located order as a
    // spot of the beam's width, as bright as the single ruling's envelope makes it
    var tot = 0;
    orders().forEach(function (o) {
      var th = Math.atan2(o.x, st.D), b = Math.PI * p.a * Math.sin(th) / p.lam;
      var env = Math.abs(b) < 1e-12 ? 1 : Math.pow(Math.sin(b) / b, 2);
      var u = (x - o.x) / SPOT;
      tot += env * Math.exp(-u * u / 2);
    });
    return Math.min(1, tot);
  }
  function fringeAt(k) {                                // the k-th bright fringe / order, in metres on the screen
    if (DSLIT) return K.brightX(P(), k);
    if (k === 0) return 0;
    var x = K.spotX(P(), Math.abs(k));
    return x === null ? null : (k < 0 ? -x : x);
  }
  function GratingScreen_theta1() {                     // where the first order of this disc or grating comes out
    var th = K.orderTheta ? K.orderTheta(P(), 1) : null;
    return th === null ? 0.4 : th;
  }
  function orders() {
    var out = [{ k: 0, x: 0 }], k, x;
    for (k = 1; k <= (DSLIT ? 9 : 3); k++) {
      x = fringeAt(k);
      if (x === null || Math.abs(x) > HALF) break;
      out.push({ k: k, x: x }); out.push({ k: -k, x: -x });
    }
    return out;
  }
  function nearestFringe() {
    var best = null;
    orders().forEach(function (o) {
      var d = Math.abs(o.x - st.c);
      if (best === null || d < best.d) best = { k: o.k, x: o.x, d: d };
    });
    var lim = DSLIT ? 3e-4 : 2e-3;
    return best && best.d < lim ? best : null;
  }

  // ---------------------------------------------------------------- the apparatus
  var bench = S.opticalBench({ len: RAIL, x0: X0, z: BZ, start: 0 });
  bench.children.forEach(function (m) { if (m.geometry && m.geometry.type === 'ExtrudeGeometry') { m.scale.z = 0.25; m.position.y = 0.01; } });

  function carriage(topY) {
    var g = new T.Group(); S.scene.add(g); g.position.z = BZ;
    var saddle = S.rounded(0.05, 0.046, 0.014, 0.003, M.alu); saddle.rotation.x = -Math.PI / 2; saddle.position.set(0, 0.048, -0.012); g.add(saddle);
    var clampK = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.01, 16), M.bakelite); clampK.rotation.x = Math.PI / 2; clampK.position.set(0, 0.04, -0.04); g.add(clampK);
    var post = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, Math.max(topY - 0.05, 0.01), 20), M.chrome);
    post.position.y = 0.05 + Math.max(topY - 0.05, 0.01) / 2; g.add(post);
    var sh = S.contact(0.08, 0.1, 0, BZ, 0.4);
    g.setX = function (x) { g.position.x = x; sh.position.x = x; };
    return g;
  }

  // the laser
  var laserCar = carriage(AXY - 0.018); laserCar.setX(X0 + 0.02);
  var lBody = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.13, 28), M.blackPlastic);
  lBody.rotation.z = Math.PI / 2; lBody.position.y = AXY; laserCar.add(lBody);
  var lHead = S.mesh(new T.CylinderGeometry(0.009, 0.012, 0.02, 22), M.alu);
  lHead.rotation.z = Math.PI / 2; lHead.position.set(0.072, AXY, 0); laserCar.add(lHead);
  var lSw = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.006, 14), M.red);
  lSw.rotation.x = Math.PI / 2; lSw.position.set(-0.03, AXY + 0.012, 0.019); laserCar.add(lSw);
  var lWarn = S.label('LASER · DO NOT LOOK INTO THE BEAM', { w: 0.085, ratio: 0.13, color: '#f2d04a', weight: 700 });
  lWarn.position.set(0, AXY + 0.021, 0.001); lWarn.rotation.x = -Math.PI / 2; laserCar.add(lWarn);

  // the slide holder with the slit, the grating or the compact disc
  var slideCar = carriage(AXY - 0.03); slideCar.setX(SLIDE_X);
  var holder = new T.Group(); holder.position.y = AXY; slideCar.add(holder);
  [[0, -0.028, 0, 0.012, 0.008, 0.05], [0, 0.028, 0, 0.012, 0.008, 0.05]].forEach(function (a) {
    var b = S.mesh(new T.BoxGeometry(a[3], a[4], a[5]), M.bakelite); b.position.set(a[0], a[1], a[2]); holder.add(b); });
  var jaw = S.mesh(new T.BoxGeometry(0.008, 0.052, 0.006), M.bakelite); jaw.position.set(0, 0, 0.026); holder.add(jaw);
  var slide = new T.Group(); slide.visible = false; holder.add(slide);
  if (CDM) {
    var disc = S.mesh(new T.CylinderGeometry(0.06, 0.06, 0.0012, 64), new T.MeshStandardMaterial({ color: 0xd8dde3, roughness: 0.12, metalness: 0.9 }));
    disc.rotation.z = Math.PI / 2; slide.add(disc);
    var hole = S.mesh(new T.CylinderGeometry(0.0075, 0.0075, 0.002, 28), M.blackPlastic); hole.rotation.z = Math.PI / 2; slide.add(hole);
    var ring = S.mesh(new T.TorusGeometry(0.023, 0.0008, 8, 48), new T.MeshStandardMaterial({ color: 0xb9c0c8, roughness: 0.3, metalness: 0.8 }));
    ring.rotation.y = Math.PI / 2; slide.add(ring);
  } else {
    var frameM = new T.MeshStandardMaterial({ color: 0x15171a, roughness: 0.5 });
    var sFrame = S.mesh(new T.BoxGeometry(0.003, 0.05, 0.05), frameM); slide.add(sFrame);
    var win = new T.Mesh(new T.PlaneGeometry(0.018, 0.012), new T.MeshBasicMaterial({ color: 0x0b0c0e }));
    win.rotation.y = Math.PI / 2; win.position.x = 0.0017; slide.add(win);
    var sLab = S.label(DSLIT ? 'DOUBLE SLIT' : fmt(1e-3 / p.d, 0) + ' / mm', { w: 0.034, ratio: 0.22, color: '#dfe3e8', weight: 700 });
    sLab.position.set(0.0018, -0.018, 0); sLab.rotation.y = Math.PI / 2; slide.add(sLab);
  }

  // the screen with its scale and vernier cursor
  var scrCar = carriage(0.02); scrCar.setX(scrX());
  var screen = new T.Group(); screen.position.y = 0; scrCar.add(screen);
  var card = S.mesh(new T.BoxGeometry(0.004, 0.26, HALF * 2), new T.MeshStandardMaterial({ color: 0xeceadf, roughness: 0.95 }));
  card.position.y = AXY + 0.06; screen.add(card);
  var frame2 = S.mesh(new T.BoxGeometry(0.01, 0.02, HALF * 2 + 0.02), M.iron); frame2.position.y = AXY - 0.08; screen.add(frame2);
  var postS = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.07, 18), M.chrome); postS.position.y = AXY - 0.11; screen.add(postS);
  var scaleTex = S.canvasTex(2048, 96, function (x, w, h) {
    var mm = 380, mid = 190, k = w / mm, i, big;
    x.fillStyle = '#f3eedd'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#17181a';
    for (i = 0; i <= mm; i++) {
      big = i % 10 === 0;
      x.fillRect(i * k, 0, big ? 3 : 1.5, big ? 40 : (i % 5 === 0 ? 28 : 16));
      if (big) { x.font = '600 30px sans-serif'; x.textAlign = 'center'; x.fillText(String(Math.abs(i - mid) / 10), i * k, 76); }
    }
  });
  var scaleM = new T.Mesh(new T.PlaneGeometry(HALF * 2, 0.016), new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.6 }));
  scaleM.rotation.y = -Math.PI / 2 * SIGN; scaleM.position.set(-0.0045 * SIGN, AXY - 0.062, 0); screen.add(scaleM);
  var patTex = S.liveTex(1024, 256);
  var patM = new T.Mesh(new T.PlaneGeometry(HALF * 2, 0.08), new T.MeshBasicMaterial({ map: patTex, transparent: true, depthWrite: false, toneMapped: false }));
  patM.rotation.y = -Math.PI / 2 * SIGN; patM.position.set(-0.0045 * SIGN, AXY, 0); patM.renderOrder = 5; screen.add(patM);
  var cursor = new T.Group(); screen.add(cursor);
  var cBody = S.mesh(new T.BoxGeometry(0.006, 0.05, 0.016), M.bakelite); cBody.position.set(-0.006 * SIGN, AXY - 0.055, 0); cursor.add(cBody);
  var cHair = S.mesh(new T.BoxGeometry(0.001, 0.07, 0.0006), M.red, false); cHair.position.set(-0.0075 * SIGN, AXY - 0.03, 0); cursor.add(cHair);
  var cGrip = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.01, 14), M.chrome); cGrip.rotation.z = Math.PI / 2; cGrip.position.set(-0.014 * SIGN, AXY - 0.07, 0); cursor.add(cGrip);

  // the beams
  var beamM = new T.LineBasicMaterial({ color: beamColour(), transparent: true, opacity: 0.85, depthWrite: false, toneMapped: false });
  var beamIn = new T.Line(new T.BufferGeometry(), beamM); beamIn.renderOrder = 7; S.scene.add(beamIn);
  var outLines = [];
  for (var oi = 0; oi < 8; oi++) {
    var ln = new T.Line(new T.BufferGeometry(), new T.LineBasicMaterial({ color: beamColour(), transparent: true, opacity: 0.5, depthWrite: false, toneMapped: false }));
    ln.visible = false; ln.renderOrder = 7; S.scene.add(ln); outLines.push(ln);
  }

  S.addApparatus('laser', laserCar, 'Laser on the rail',
    'A low-power laser clamped so that the beam runs along the rail at bench height, well below eye level. Switch it off before you lean over the bench.');
  S.addApparatus('slide', slideCar, CDM ? 'Compact disc in its holder' : DSLIT ? 'Double slit' : 'Plane transmission grating',
    CDM ? 'The spiral of pits on the disc is a reflection grating; the spacing between its tracks is what you have to find.'
      : DSLIT ? 'Two slits, each ' + fmt(p.a * 1e6, 0) + ' microns wide, their centres ' + fmt(p.d * 1e6, 0) + ' microns apart.'
        : 'Ruled ' + fmt(1e-3 / p.d, 0) + ' lines to the millimetre and held square to the beam.');
  S.addApparatus('screen', scrCar, 'Screen with a scale and cursor',
    'A white screen carrying a millimetre scale; the cursor slides along it and is read to ' + (DSLIT ? '0.05 mm on its vernier' : '0.5 mm') + '.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ---------------------------------------------------------------- what the screen shows (HUD)
  var eyeCard = document.createElement('div'); eyeCard.className = 'card';
  eyeCard.appendChild(document.createTextNode('On the screen'));
  var eyeCan = document.createElement('canvas'); eyeCan.width = 300; eyeCan.height = 130;
  eyeCan.style.cssText = 'width:200px;height:87px;display:block;margin-top:4px;border-radius:8px';
  eyeCard.appendChild(eyeCan); S.hud.appendChild(eyeCard);
  var ectx = eyeCan.getContext('2d'), eyeKey = '';
  var hudC = S.hudCard('Cursor reads'), hudD = S.hudCard('Slide to screen'), hudF = S.hudCard('On the cursor');
  function viewHalf() { return DSLIT ? 0.016 : HALF; }
  function drawStrip() {
    var key = [st.on, st.placed, st.aligned, fmt(st.c, 6), fmt(st.D, 4)].join('|');
    if (key === eyeKey) return; eyeKey = key;
    var w = eyeCan.width, h = eyeCan.height, i, col = cssColour(), half = viewHalf();
    ectx.fillStyle = '#0a0b0d'; ectx.fillRect(0, 0, w, h);
    if (st.on && st.placed && st.aligned) {
      for (i = 0; i < w; i++) {
        var x = (i / w - 0.5) * 2 * half, I = Math.min(1, inten(x) / (DSLIT ? p.I0 : 1));
        var a = Math.pow(I, 0.45);
        ectx.fillStyle = 'rgba(' + col[0] + ',' + col[1] + ',' + col[2] + ',' + a.toFixed(3) + ')';
        ectx.fillRect(i, 10, 1, h - 40);
      }
    }
    ectx.strokeStyle = 'rgba(240,244,248,.9)'; ectx.lineWidth = 1;
    var cx = w / 2 + st.c / (2 * half) * w;
    if (cx > 0 && cx < w) { ectx.beginPath(); ectx.moveTo(cx, 4); ectx.lineTo(cx, h - 24); ectx.stroke(); }
    ectx.fillStyle = '#9aa1ab'; ectx.font = '500 13px "Public Sans", sans-serif'; ectx.textAlign = 'left';
    ectx.fillText(fmt(half * 2000, 0) + ' mm across', 6, h - 7);
  }
  var patKey = '';
  function drawPattern() {
    var key = [st.on, st.placed, st.aligned, fmt(st.D, 4)].join('|');
    if (key === patKey) return; patKey = key;
    patTex.draw(function (x, w, h) {
      x.clearRect(0, 0, w, h);
      if (!(st.on && st.placed && st.aligned)) return;
      var col = cssColour(), i;
      for (i = 0; i < w; i++) {
        var xx = (i / w - 0.5) * 2 * HALF, I = Math.min(1, inten(xx) / (DSLIT ? p.I0 : 1));
        var a = Math.pow(I, 0.4);
        if (a < 0.015) continue;
        var g = x.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, 'rgba(' + col[0] + ',' + col[1] + ',' + col[2] + ',0)');
        g.addColorStop(0.5, 'rgba(' + col[0] + ',' + col[1] + ',' + col[2] + ',' + a.toFixed(3) + ')');
        g.addColorStop(1, 'rgba(' + col[0] + ',' + col[1] + ',' + col[2] + ',0)');
        x.fillStyle = g; x.fillRect(SIGN > 0 ? w - 1 - i : i, 0, 1, h);
      }
    });
  }

  function update() {
    scrCar.setX(scrX());
    slide.visible = st.placed;
    cursor.position.z = -st.c;                        // the card's local z runs the other way to the scale
    var src = new T.Vector3(X0 + 0.02 + 0.082, AXY, BZ), hit = new T.Vector3(SLIDE_X, AXY, BZ);
    beamIn.geometry.setFromPoints([src, st.placed ? hit : new T.Vector3(scrX() - 0.004 * SIGN, AXY, BZ)]);
    beamIn.visible = st.on;
    outLines.forEach(function (l) { l.visible = false; });
    if (st.on && st.placed && st.aligned) {
      orders().slice(0, outLines.length).forEach(function (o, i) {
        var l = outLines[i];
        l.geometry.setFromPoints([hit, new T.Vector3(scrX() - 0.004 * SIGN, AXY, BZ - o.x)]);
        l.visible = true;
      });
    }
    drawPattern(); drawStrip();
    hudC.set(fmt(st.c * 1000, DSLIT ? 2 : 1) + ' mm');
    hudD.set(fmt(st.D * 100, 1) + ' cm');
    var f = nearestFringe();
    hudF.set(!st.on ? 'laser off' : !st.placed ? 'no slide in the holder' : f
      ? (f.k === 0 ? 'the straight-through spot' : (DSLIT ? 'bright fringe ' : 'order ') + (f.k > 0 ? '+' : '') + f.k)
      : 'between fringes');
  }

  // ---------------------------------------------------------------- the human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function switchOn() {
    if (st.on) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    return S.hand.tap(lSw, 'top').then(function () {
      st.on = true; update();
      S.say('The laser is on. The beam stays at bench height: never bring your eye down to it.'); S.render(); return true; });
  }
  function placeSlide() {
    if (st.placed) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    var from = new T.Vector3(SLIDE_X + 0.1, AXY + 0.14, BZ + 0.16), to = new T.Vector3(SLIDE_X, AXY + 0.01, BZ);
    slide.visible = true; slide.position.set(0.1, 0.14, 0.16);
    return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); },
      function (k) { slide.position.set(0.1 * (1 - k), 0.14 * (1 - k), 0.16 * (1 - k)); },
      { ms: 1300, reachMs: 700, hold: 220, mode: 'top' }).then(function () {
      slide.position.set(0, 0, 0); st.placed = true; update();
      S.say(CDM ? 'The disc is in its holder, facing the beam.' : 'The slide is in the holder, square to the beam.');
      S.render(); return true; });
  }
  function align() {
    if (st.aligned) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    if (!(st.on && st.placed)) { S.say('Switch the laser on and put the slide in the holder first.'); return Promise.resolve(false); }
    return S.hand.tap(jaw, 'top').then(function () {
      st.aligned = true; update();
      S.say(CDM ? 'The orders come back and fall on the screen on either side of the hole.'
        : 'The beam is centred on the slide and the pattern is out on the screen.'); S.render(); return true; });
  }
  function moveScreen(toM) {
    if (S.hand.busy) return wait();
    toM = Math.max(CDM ? 0.05 : 0.4, Math.min(CDM ? 0.5 : 1.6, Math.round(toM * 1000) / 1000));
    var from = st.D;
    if (Math.abs(toM - from) < 1e-6) return Promise.resolve(true);
    function at(k) { return from + (toM - from) * k; }
    return S.hand.pinchMove(new T.Vector3(SLIDE_X + SIGN * from, 0.055, BZ + 0.03),
      function (k) { return new T.Vector3(SLIDE_X + SIGN * at(k), 0.055, BZ + 0.03); },
      function (k) { st.D = at(k); update(); syncScreenView(); }, { ms: Math.min(1800, 500 + Math.abs(toM - from) * 900), reachMs: 650, hold: 160 })
      .then(function () { st.D = toM; update(); syncScreenView(); S.render(); return true; });
  }
  function moveCursor(toM) {
    if (S.hand.busy) return wait();
    toM = Math.max(-HALF + 0.005, Math.min(HALF - 0.005, roundLC(toM)));
    var from = st.c;
    if (Math.abs(toM - from) < 1e-9) { st.c = toM; update(); return Promise.resolve(true); }
    function at(k) { return from + (toM - from) * k; }
    function pt(v) { return new T.Vector3(scrX() - 0.015 * SIGN, AXY - 0.07, BZ - v); }
    return S.hand.pinchMove(pt(from), function (k) { return pt(at(k)); },
      function (k) { st.c = at(k); update(); }, { ms: Math.min(1500, 380 + Math.abs(toM - from) * 3000), reachMs: 600, hold: 140 })
      .then(function () { st.c = toM; update(); S.render(); return true; });
  }

  // ---------------------------------------------------------------- recording
  function record() {
    if (!(st.on && st.placed && st.aligned)) { S.say('Set the laser, the slide and the screen first.'); return false; }
    var f = nearestFringe();
    if (!f) { S.say('The cursor is between two fringes. Run it onto the middle of a bright one.'); return false; }
    if (f.k === 0) { S.say('That is the straight-through spot. Move out to a fringe on one side.'); return false; }
    if (st.hold === null || st.holdK !== Math.abs(f.k)) {
      st.hold = roundLC(st.c); st.holdK = Math.abs(f.k);
      S.say((DSLIT ? 'Fringe ' : 'Order ') + f.k + ' read at ' + fmt(st.hold * 1000, DSLIT ? 2 : 1) + ' mm. Now go to the same one on the other side.');
      S.render(); return true;
    }
    var other = roundLC(st.c);
    if (other * st.hold > 0) { S.say('That is the same side again. Cross the centre to the matching fringe.'); return false; }
    var sep = Math.abs(other - st.hold), kk = Math.abs(f.k);
    if (MULTI && S.rows.some(function (r) { return Math.abs(r.D - st.D) < 0.01; })) { st.hold = null; st.holdK = null; S.say('There is already a reading at this screen distance. Move the screen.'); return false; }
    if (DSLIT) {
      var beta = sep / (2 * kk);
      S.addRow({ D: st.D, k: kk, sep: sep, beta: beta, lam: beta * p.d / st.D * 1e9 });
      S.say('Fringe width ' + fmt(beta * 1000, 4) + ' mm at D = ' + fmt(st.D * 100, 1) + ' cm.');
    } else {
      if (!MULTI && S.rows.some(function (r) { return r.m === kk; })) { st.hold = null; st.holdK = null; S.say('Order ' + kk + ' is already in the table.'); return false; }
      var x = sep / 2, th = Math.atan2(x, st.D);
      S.addRow({ m: kk, D: st.D, x: x, theta: th * 180 / Math.PI,
        lam: p.d * Math.sin(th) / kk * 1e9, d: kk * p.lam / Math.sin(th) * 1e6 });
      S.say('Order ' + kk + ' sits ' + fmt(x * 1000, 1) + ' mm from the centre, at ' + fmt(th * 180 / Math.PI, 2) + '°.');
    }
    st.hold = null; st.holdK = null;
    return true;
  }
  function meanOf(xs) { return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : NaN; }
  function resultFor(rows) {
    if (rows.length < 2) return null;
    if (CDM) {
      return { label: 'track spacing', value: meanOf(rows.map(function (r) { return r.d; })), unit: 'µm', digits: 3,
        truth: p.d * 1e6, note: 'From d sin(theta) = m x wavelength with the laser at ' + fmt(lamNm(), 1) + ' nm.' };
    }
    return { label: 'wavelength', value: meanOf(rows.map(function (r) { return r.lam; })), unit: 'nm', digits: 1,
      truth: lamNm(), note: DSLIT ? 'From fringe width x d / D, averaged over your screen distances.'
        : 'From d sin(theta) = m x wavelength, averaged over the orders.' };
  }

  var VIEWS = {
    laser: [[X0 + 0.24, AXY + 0.2, BZ + 0.44], [X0 + 0.06, AXY, BZ]],
    slide: [[SLIDE_X + 0.28, AXY + 0.18, BZ + 0.42], [SLIDE_X + 0.02, AXY - 0.01, BZ]],
    screen: [[SLIDE_X + SIGN * 0.4, AXY + 0.05, BZ + 0.16], [SLIDE_X + SIGN * 0.4, AXY, BZ]],
    wide: [[0.05, 1.15, BZ + 2.45], [-0.02, 0.12, BZ]],
    book: [[-0.5, 0.46, 0.56], [-0.5, 0.0, 0.1]]
  };
  function syncScreenView() {
    var sx = scrX();
    VIEWS.screen[0][0] = sx - 0.55 * SIGN; VIEWS.screen[1][0] = sx;
  }
  update(); syncScreenView();

  return {
    camera: { pos: [0.05, 1.15, BZ + 2.45], look: [-0.02, 0.12, BZ] },
    views: VIEWS,
    theory: DSLIT ? {
      principle: 'Each slit spreads the laser light by diffraction and the two spread beams overlap on the screen. '
        + 'Where their paths differ by a whole number of wavelengths the waves add, so the screen carries a set of '
        + 'equally spaced bright fringes.',
      formula: 'β = λ D / d',
      formulaNote: 'β = fringe width, d = distance between the slits, D = slits to screen',
      more: ['The single slit\'s own diffraction pattern rides over the fringes as a broad envelope and makes the far '
        + 'ones faint; where d / a is a whole number a fringe is missing altogether.',
        'Counting out the same number of fringes on each side of the centre cancels the small inward pull of that '
        + 'envelope, so measure from fringe −k to fringe +k and divide by 2k.'],
      precautions: 'Keep the beam horizontal at bench level and never at eye height. Never look into the beam or at a '
        + 'mirror-like reflection of it. Take your watch off. Switch the laser off before leaning over the bench.'
    } : CDM ? {
      principle: 'The data on a compact disc lies in a spiral of pits, and neighbouring turns of that spiral are '
        + 'equally spaced, so the disc works as a reflection grating. At normal incidence the orders that come back '
        + 'obey the same grating equation as a ruled grating.',
      formula: 'd sin(θ) = m λ',
      formulaNote: 'd = track spacing, θ = angle of the returning order, measured from x and D',
      more: ['A known laser wavelength and a measured angle give the track spacing straight away. A CD comes out near '
        + '1.6 microns; a DVD, whose tracks are much closer, throws its orders out much wider.'],
      precautions: 'A disc is a mirror as well as a grating, so the reflected light comes back towards the laser. '
        + 'Work out where every order goes before switching on, keep the whole path at bench level, and never look '
        + 'into the returning beam.'
    } : {
      principle: 'A grating sends the beam out only in those directions where neighbouring rulings differ by a whole '
        + 'number of wavelengths. Because thousands of rulings take part, each order is a sharp bright spot.',
      formula: 'd sin(θ) = m λ,   x = D tan(θ)',
      formulaNote: 'd = grating spacing, m = order, D = grating to screen',
      more: ['The orders are at large angles here, so the distance on the screen is not proportional to the angle: '
        + 'turn x into an angle with x = D tan(theta) before using the grating equation.',
        'Only the orders with m x wavelength less than d exist at all, so a fine grating shows fewer of them.'],
      precautions: 'Keep the beam horizontal at bench level and never at eye height. A grating throws several bright '
        + 'orders out at once: check where each of them goes before you lean over the bench.'
    },
    book: { title: DSLIT ? 'Expt. — Laser double slit' : CDM ? 'Expt. — Track spacing of a CD' : 'Expt. — Laser and grating',
      lines: [DSLIT ? 'Slit separation d = ' + fmt(p.d * 1e6, 0) + ' microns.' : 'Laser wavelength ' + fmt(lamNm(), 1) + ' nm.',
        'Cursor read to ' + (DSLIT ? '0.05 mm' : '0.5 mm') + '.',
        DSLIT ? 'beta = wavelength x D / d' : 'd sin(theta) = m x wavelength',
        'Measure the same fringe on both sides of the centre.'],
      columns: DSLIT ? [
        { label: 'D (cm)', get: function (r) { return fmt(r.D * 100, 1); } },
        { label: 'Fringe ±k', get: function (r) { return r.k; } },
        { label: 'Separation (mm)', get: function (r) { return fmt(r.sep * 1000, 3); } },
        { label: 'β (mm)', get: function (r) { return fmt(r.beta * 1000, 4); } },
        { label: 'λ (nm)', get: function (r) { return fmt(r.lam, 1); } }] : [
        { label: 'Order m', get: function (r) { return r.m; } },
        { label: 'x (mm)', get: function (r) { return fmt(r.x * 1000, 1); } },
        { label: 'θ (°)', get: function (r) { return fmt(r.theta, 2); } },
        { label: CDM ? 'd (µm)' : 'λ (nm)', get: function (r) { return CDM ? fmt(r.d, 3) : fmt(r.lam, 1); } }],
      at: [-0.5, 0.1, 0.1] },
    graph: DSLIT ? { x: function (r) { return r.D * 100; }, y: function (r) { return r.beta * 1000; },
      xlabel: 'D (cm)', ylabel: 'β (mm)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return isFinite(k) ? function (x) { return k * x; } : null; } }
      : { x: function (r) { return r.m; }, y: function (r) { return Math.sin(r.theta * Math.PI / 180); },
        xlabel: 'order m', ylabel: 'sin θ', x0: 0, y0: 0,
        line: function (pts) { var k = S.fit.origin(pts); return isFinite(k) ? function (x) { return k * x; } : null; } },
    result: resultFor,
    tol: 0.02,
    chips: ['Why measure on both sides of the centre?', 'Why is a far fringe faint?', 'What is the safe way to use this laser?',
      'Check my readings', DSLIT ? 'What happens if I move the screen further?' : 'Why turn x into an angle first?'],
    viva: DSLIT ? [['The screen is moved twice as far away. The fringe width',
      ['doubles', 'halves', 'does not change'], 0, 'The fringe width is proportional to D.'],
      ['The far fringes are faint because', ['the single-slit envelope falls away', 'the laser is weak', 'they are wider'], 0,
        'The diffraction pattern of one slit limits how far the fringes carry.']]
      : [[CDM ? 'A DVD throws its orders out further than a CD because' : 'The orders of a grating are sharp because',
        CDM ? ['its tracks are closer together', 'it is thicker', 'it spins faster']
          : ['thousands of rulings interfere', 'the laser is bright', 'the screen is white'], 0,
        CDM ? 'sin(theta) = m x wavelength / d grows as d falls.' : 'The width of a principal maximum falls as 1 / N.'],
        ['Why is x = D tan(theta) used rather than x proportional to theta?',
          ['The orders are at large angles', 'The screen is tilted', 'It makes no difference'], 0,
          'At 20 degrees and more the small-angle shortcut is badly wrong.']],
    askState: function () {
      var f = nearestFringe();
      return { set_up: MODE, laser_on: st.on, slide_in_the_holder: st.placed, beam_centred: st.aligned,
        slide_to_screen_cm: +(st.D * 100).toFixed(1), cursor_reads_mm: +(st.c * 1000).toFixed(3),
        on_the_cursor: f ? (f.k === 0 ? 'the straight-through spot' : (DSLIT ? 'fringe ' : 'order ') + f.k) : 'between fringes',
        held_first_side_mm: st.hold === null ? null : +(st.hold * 1000).toFixed(3),
        wavelength_nm_known: CDM ? +lamNm().toFixed(1) : null, readings_taken: S.rows.length };
    },
    steps: [
      { id: 'setup', title: 'Set up the bench', view: 'wide', render: function (u) {
        u.h2('Switch the laser on and put the slide in');
        u.p('The laser is clamped on the rail so that the beam runs along it at bench height. Drop the '
          + (CDM ? 'disc' : 'slide') + ' into the holder and centre the beam on it; the pattern then falls '
          + 'on the screen further down the rail.');
        u.task('1. Switch the laser on', st.on, st.on ? 'The beam runs along the rail' : 'Press the switch on the laser')
          .add(u.button(st.on ? 'Laser on' : 'Switch the laser on', function () { switchOn(); }, !st.on, st.on || S.hand.busy));
        u.task('2. Put the ' + (CDM ? 'disc' : 'slide') + ' in', st.placed, st.placed ? 'Square to the beam' : 'Hold it by the frame')
          .add(u.button(st.placed ? 'In the holder' : 'Put it in the holder', function () { placeSlide(); }, !st.placed, st.placed || S.hand.busy));
        u.task('3. Centre the beam on it', st.aligned, st.aligned ? 'The pattern is out on the screen' : 'Nudge the holder until the beam is on the middle')
          .add(u.button(st.aligned ? 'Centred' : 'Centre the beam', function () { align(); }, !st.aligned, st.aligned || !st.placed || S.hand.busy));
        u.note('Laser safety: the beam stays horizontal at bench level, never at eye height. Never look into the beam '
          + 'or at a reflection of it, take off your watch and rings, and switch the laser off before leaning over the '
          + 'bench.');
        u.next('Next: measure the pattern', st.on && st.placed && st.aligned);
      },
      ok: function () { return st.on && st.placed && st.aligned; },
      auto: function () { return switchOn().then(placeSlide).then(align); } },

      { id: 'measure', title: DSLIT ? 'Measure the fringes' : 'Measure the orders', view: 'screen', render: function (u) {
        u.h2(DSLIT ? 'Measure the fringe width at several screen distances' : 'Measure how far each order lands from the centre');
        u.p(DSLIT ? 'Run the cursor out to a bright fringe on one side of the centre and read its vernier, then to the '
          + 'matching fringe on the other side. Divide the distance between them by twice the fringe number. Repeat at '
          + 'two more screen distances.'
          : 'Run the cursor to an order on one side and read the scale, then to the same order on the other side. Half '
          + 'the distance between them is x for that order; the angle follows from x and the distance to the screen.');
        if (MULTI) {
          u.slider('Move the screen to', CDM ? 5 : 60, CDM ? 50 : 160, 1, function () { return st.DSet * 100; }, function (x) { st.DSet = x / 100; }, 'cm', 0);
          u.row(u.button('Move the screen', function () { moveScreen(st.DSet).then(function () { syncScreenView(); S.focus('screen'); S.render(); }); }, true, S.hand.busy));
        }
        u.slider('Move the cursor to', -150, 150, DSLIT ? 0.05 : 0.5, function () { return st.cSet * 1000; },
          function (x) { st.cSet = x / 1000; }, 'mm', DSLIT ? 2 : 1);
        u.row(u.button('Move the cursor', function () { moveCursor(st.cSet); S.render(); }, true, S.hand.busy),
          u.button(DSLIT ? 'Go to the next fringe' : 'Go to the next order', function () {
            var want = DSLIT ? [4] : CDM ? [1] : [1, 2], i, target = null, x;
            for (i = 0; i < want.length; i++) {
              if (MULTI) { target = want[i]; break; }
              if (!S.rows.some(function (r) { return r.m === want[i]; })) { target = want[i]; break; }
            }
            if (target === null) { S.say('You have all the orders this grating shows on the screen.'); return; }
            x = fringeAt(st.hold !== null && st.holdK === target ? -target : target);
            if (x === null) { S.say('That order falls beyond the screen.'); return; }
            moveCursor(x).then(function () { S.render(); });
          }, false, S.hand.busy));
        u.live(function () { var f = nearestFringe();
          return 'Cursor at ' + fmt(st.c * 1000, DSLIT ? 2 : 1) + ' mm · '
            + (f ? (f.k === 0 ? 'the straight-through spot' : (DSLIT ? 'fringe ' : 'order ') + (f.k > 0 ? '+' : '') + f.k) : 'between fringes'); });
        u.row(u.button('Set the cursor and record', function () { record(); S.render(); }, true, S.hand.busy));
        u.h3('Observation table'); u.table();
        var need = 2;
        u.next('Next: graph and result', S.rows.length >= need);
        if (S.rows.length < need) u.p(S.rows.length + ' of ' + need + ' readings recorded.');
      },
      ok: function () { return S.rows.length >= 2; },
      auto: function () {
        var seq = Promise.resolve();
        if (MULTI) {
          var th1 = GratingScreen_theta1(), dmax = Math.min(0.5, 0.86 * (HALF - 0.01) / Math.tan(th1));
          (DSLIT ? [1.0, 1.25, 1.5] : [dmax * 0.7, dmax * 0.85, dmax]).forEach(function (D) {
            var kk = DSLIT ? 4 : 1;
            seq = seq.then(function () { return moveScreen(D); })
              .then(function () { return moveCursor(fringeAt(kk)); }).then(function () { record(); })
              .then(function () { return moveCursor(fringeAt(-kk)); }).then(function () { record(); });
          });
        } else {
          [1, 2].forEach(function (m) {
            seq = seq.then(function () {
              var x = fringeAt(m);
              if (x === null) return null;
              return moveCursor(x).then(function () { record(); })
                .then(function () { return moveCursor(fringeAt(-m)); }).then(function () { record(); });
            });
          });
        }
        return seq;
      } }
    ],
    tick: function () { update(); }
  };
});
