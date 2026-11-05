/* Prayogshala studio module: Convex lens, the image for each position of the object (NCERT Class X).
   A school optical bench: the lens in a holder at the 70 cm mark, a short lit candle on one side and a white screen
   on the other. Step 1 catches the image of a distant window to get f; step 2 puts the candle beyond 2F, just
   beyond 2F, between F and 2F, and inside F. Every number comes from the shared `lens` kernel's ray trace through
   both glass surfaces: img_x, img_h, real, sharp. */
HoolaStudio.define('school-convex-lens-images', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.lens;
  var p = window.HoolaKernels.paramsFor('lens', S.lab.params);
  var X0 = -0.72, LEN = 1.42, BZ = -0.14, AXY = 0.21, LENS = 70;     // bench start, length (m), z of the axis, axis height, lens mark (cm)
  var AP = 0.025, DIST = 20.0, CARD_W = 0.1, CARD_H = 0.12;
  var FCM = 1 / ((p.n - 1) * (2 / p.R)) * 100;                        // this lens's focal length in cm
  var SAMPLE = (S.lab.variant || {}).sample || '';
  var st = { lit: false, mode: 'bench', cPos: LENS - 3 * FCM, sPos: LENS + 1.5 * FCM, cSet: LENS - 3 * FCM,
    sSet: LENS + 1.5 * FCM, f0: null, insideF: false, rays: true };
  function xAt(cm) { return X0 + cm / 100; }
  function uCm() { return LENS - st.cPos; }
  function vCm() { return st.sPos - LENS; }
  function round1(v) { return Math.round(v * 10) / 10; }

  // ---------- bench and stands
  var bench = S.opticalBench({ len: LEN, x0: X0, z: BZ, start: 0 });
  bench.children.forEach(function (m) { if (m.geometry && m.geometry.type === 'ExtrudeGeometry') { m.scale.z = 0.25; m.position.y = 0.01; } });
  var plate = S.label('SCHOOL OPTICAL BENCH · cm', { w: 0.17, ratio: 0.1, color: '#e8e2cf', weight: 600 });
  plate.position.set(X0 + LEN - 0.14, 0.03, BZ + 0.0302); bench.add(plate);
  var toWin = S.label('← to the open window', { w: 0.13, ratio: 0.14, color: '#3d4350', weight: 600 });
  toWin.rotation.x = -Math.PI / 2; toWin.position.set(X0 + 0.14, 0.042, BZ - 0.05); S.scene.add(toWin);

  function stand(postTop, name) {
    var g = new T.Group(); S.scene.add(g); g.position.z = BZ;
    var sad = S.rounded(0.046, 0.044, 0.014, 0.003, M.alu); sad.rotation.x = -Math.PI / 2; sad.position.set(0, 0.048, -0.012); g.add(sad);
    var lip = S.rounded(0.046, 0.03, 0.006, 0.002, M.alu); lip.position.set(0, 0.036, 0.034); g.add(lip);
    var hair = S.mesh(new T.BoxGeometry(0.0008, 0.0004, 0.026), M.red, false); hair.position.set(0, 0.0458, 0.022); g.add(hair);
    var kn = S.mesh(new T.CylinderGeometry(0.0072, 0.0072, 0.009, 18), M.bakelite); kn.rotation.x = Math.PI / 2; kn.position.set(0, 0.036, -0.042); g.add(kn);
    var sock = S.mesh(new T.CylinderGeometry(0.009, 0.0105, 0.02, 20), M.alu); sock.position.set(0, 0.064, 0); g.add(sock);
    var post = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, Math.max(0.01, postTop - 0.07), 18), M.chrome);
    post.position.y = 0.07 + Math.max(0.01, postTop - 0.07) / 2; g.add(post);
    var sh = S.contact(0.08, 0.1, 0, BZ, 0.4, 0.04);
    g.setX = function (x, lift) { g.position.x = x; g.position.y = lift || 0; sh.position.x = x; sh.material.opacity = 0.4 * Math.max(0.15, 1 - (lift || 0) * 8); };
    g.userData.name = name; return g;
  }

  // ---------- the convex lens in its ring holder
  var LX = xAt(LENS);
  var lensStand = stand(AXY - AP - 0.014, 'lens'); lensStand.setX(LX);
  var lensG = new T.Group(); lensG.position.set(0, AXY, 0); lensStand.add(lensG);
  (function () {
    var pts = [], i, r, sag = function (rr) { return Math.sqrt(Math.max(1e-9, p.R * p.R - rr * rr)) - Math.sqrt(Math.max(1e-9, p.R * p.R - AP * AP)); };
    for (i = 0; i <= 14; i++) { r = AP * (1 - i / 14); pts.push(new T.Vector2(Math.max(0.00001, r), sag(r) + p.d / 2)); }
    for (i = 1; i <= 14; i++) { r = AP * i / 14; pts.push(new T.Vector2(Math.max(0.00001, r), -(sag(r) + p.d / 2))); }
    var glass = new T.MeshPhysicalMaterial({ color: 0xeef6f5, roughness: 0.03, metalness: 0, transmission: 0.93, thickness: 0.01, ior: p.n, transparent: true });
    var m = new T.Mesh(new T.LatheGeometry(pts, 48), glass); m.rotation.z = -Math.PI / 2; lensG.add(m);
  })();
  var ring = S.mesh(new T.TorusGeometry(AP + 0.003, 0.004, 10, 48), M.bakelite); ring.rotation.y = Math.PI / 2; lensG.add(ring);
  var lLab = S.label('CONVEX LENS', { w: 0.044, ratio: 0.18, color: '#c8ccd2', weight: 700 });
  lLab.position.set(0, -AP - 0.012, 0.004); lensG.add(lLab);

  // ---------- the short candle
  var canStand = stand(AXY - 0.004, 'candle');
  var candle = new T.Group(); candle.position.y = AXY; canStand.add(candle);
  var WAXH = 0.013, FLH = Math.max(0.005, p.h - WAXH);
  var dish = S.mesh(new T.CylinderGeometry(0.016, 0.014, 0.004, 28), M.brass); dish.position.y = -0.002; candle.add(dish);
  var waxM = new T.MeshStandardMaterial({ color: 0xf4ecd9, roughness: 0.5 });
  var wax = S.mesh(new T.CylinderGeometry(0.0072, 0.0076, WAXH, 28), waxM); wax.position.y = WAXH / 2; candle.add(wax);
  var wick = S.mesh(new T.CylinderGeometry(0.0005, 0.0006, 0.003, 6), M.black); wick.position.y = WAXH + 0.001; candle.add(wick);
  var flameTex = S.canvasTex(128, 128, function (x) { var gr = x.createRadialGradient(64, 64, 2, 64, 64, 62);
    gr.addColorStop(0, 'rgba(255,245,205,0.95)'); gr.addColorStop(0.3, 'rgba(255,170,70,0.5)'); gr.addColorStop(1, 'rgba(255,140,40,0)');
    x.fillStyle = gr; x.fillRect(0, 0, 128, 128); });
  var flame = new T.Group();
  var fcore = new T.Mesh(new T.ConeGeometry(0.0032, FLH, 14), new T.MeshBasicMaterial({ color: 0xfff0c8, transparent: true, opacity: 0.95, toneMapped: false, depthWrite: false }));
  fcore.position.y = FLH / 2; flame.add(fcore);
  var fglow = new T.Sprite(new T.SpriteMaterial({ map: flameTex, transparent: true, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending, opacity: 0.8 }));
  fglow.scale.set(0.026, 0.026, 1); fglow.position.y = FLH * 0.5; flame.add(fglow);
  flame.position.y = WAXH; flame.visible = false; candle.add(flame);
  var lamp = new T.PointLight(0xffa851, 0, 0.5, 2); lamp.position.y = WAXH + FLH; candle.add(lamp);

  // ---------- the screen
  var scrStand = stand(AXY - CARD_H - 0.006, 'screen');
  var screen = new T.Group(); screen.position.y = AXY; scrStand.add(screen);
  var card = S.mesh(new T.BoxGeometry(0.003, CARD_H, CARD_W), new T.MeshStandardMaterial({ color: 0xe4e2da, roughness: 0.95 }));
  card.position.y = -0.004 - CARD_H / 2; screen.add(card);
  var imgTex = S.liveTex(192, Math.round(192 * CARD_H / CARD_W)), PXM = 192 / CARD_W;
  var imgPlane = new T.Mesh(new T.PlaneGeometry(CARD_W, CARD_H), new T.MeshBasicMaterial({ map: imgTex, transparent: true, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending }));
  imgPlane.rotation.y = -Math.PI / 2; imgPlane.position.set(-0.0019, -0.004 - CARD_H / 2, 0); imgPlane.renderOrder = 4; screen.add(imgPlane);

  // ---------- rays
  var rayMat = new T.LineBasicMaterial({ color: 0xffc15a, transparent: true, opacity: 0.6, depthWrite: false, toneMapped: false });
  var rayDash = new T.LineDashedMaterial({ color: 0xffc15a, transparent: true, opacity: 0.35, dashSize: 0.006, gapSize: 0.005, depthWrite: false, toneMapped: false });
  var rayLines = [];
  for (var ri = 0; ri < 8; ri++) { var ln = new T.Line(new T.BufferGeometry(), rayMat); ln.visible = false; ln.renderOrder = 7; S.scene.add(ln); rayLines.push(ln); }

  S.addApparatus('bench', bench, 'School optical bench', 'A wooden bed with a centimetre scale (least count 1 mm). Each stand is read at its index mark.');
  S.addApparatus('lens', lensStand, 'Convex lens', (SAMPLE ? SAMPLE + '. ' : '') + 'A thin biconvex lens in a ring holder at the ' + LENS.toFixed(1) + ' cm mark; its focal length is about ' + FCM.toFixed(0) + ' cm.');
  S.addApparatus('candle', canStand, 'Candle on a stand', 'The lit flame is the object, standing just above the principal axis.');
  S.addApparatus('screen', scrStand, 'White screen', 'A white card just below the axis. Slide it until the inverted image is sharp.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudU = S.hudCard('u'), hudV = S.hudCard('Screen at'), hudI = S.hudCard('Image on the screen');

  var view = null;
  function look() {
    p.u = st.mode === 'distant' ? DIST : Math.max(0.005, uCm() / 100);
    p.scr = Math.max(0.005, vCm() / 100);
    view = K.view(null, p); return view;
  }
  function nature(v) {
    if (!st.lit && st.mode !== 'distant') return 'Candle not lit';
    if (!v.real) return 'Virtual, erect and larger: nothing on the screen';
    var m = Math.abs(v.img_h / p.h);
    return (v.sharp > 0.85 ? 'Sharp' : v.sharp > 0.45 ? 'Nearly sharp' : v.sharp > 0.12 ? 'Blurred' : 'Very blurred')
      + ' · inverted and ' + (m > 1.08 ? 'larger' : m < 0.92 ? 'smaller' : 'the same size');
  }
  function drawImage(v) {
    var real = (st.lit || st.mode === 'distant') && v.real && v.img_x > 0;
    var mag = real ? (v.img_h / p.h) * (p.scr / v.img_x) : 0;
    var blur = real ? 2 * AP * Math.sqrt(Math.max(0, 1 / Math.max(v.sharp, 1e-6) - 1)) * 0.004 / v.img_x : 0;
    imgTex.draw(function (x, w, h) {
      x.clearRect(0, 0, w, h);
      if (!real) return;
      var ax = -0.004 * PXM, cx = w / 2, k = Math.abs(mag) * PXM, sig = Math.min(60, blur * PXM * 0.5);
      x.save(); if (sig > 0.4) x.filter = 'blur(' + sig.toFixed(1) + 'px)';
      x.globalAlpha = Math.max(0.1, Math.min(1, 1.0 / (0.4 + Math.abs(mag))));
      x.translate(cx, ax + 2); x.scale(k, k);
      if (st.mode === 'distant') {
        x.fillStyle = 'rgba(255,235,180,0.85)'; x.fillRect(-0.012, 0.004, 0.024, 0.018);
        x.fillStyle = 'rgba(120,90,50,0.5)'; x.fillRect(-0.0012, 0.004, 0.0024, 0.018); x.fillRect(-0.012, 0.0118, 0.024, 0.002);
      } else {
        x.fillStyle = 'rgba(150,100,50,0.5)'; x.fillRect(-0.0074, 0, 0.0148, WAXH);
        var g1 = x.createRadialGradient(0, WAXH + FLH * 0.45, 0.0004, 0, WAXH + FLH * 0.5, FLH * 1.1);
        g1.addColorStop(0, 'rgba(255,250,225,1)'); g1.addColorStop(0.45, 'rgba(255,205,110,0.9)'); g1.addColorStop(1, 'rgba(255,130,40,0)');
        x.fillStyle = g1; x.beginPath(); x.ellipse(0, WAXH + FLH * 0.5, 0.0042, FLH * 0.8, 0, 0, Math.PI * 2); x.fill();
      }
      x.restore();
    });
  }
  function drawRays(v) {
    rayLines.forEach(function (l) { l.visible = false; });
    if (!st.rays || (st.mode === 'bench' && !st.lit)) return;
    var n = 0, endX = Math.min(LEN - LENS / 100 - 0.02, Math.max(p.scr, v.img_x > 0 ? v.img_x : 0.2) + 0.08);
    function put(pts, virt) {
      if (n >= rayLines.length) return;
      var l = rayLines[n++]; l.material = virt ? rayDash : rayMat;
      l.geometry.setFromPoints(pts.map(function (q) { return new T.Vector3(LX + q[0], AXY + q[1], BZ + 0.0006); }));
      if (virt) l.computeLineDistances(); l.visible = true;
    }
    if (st.mode === 'distant') {                                      // parallel light from the distant window, meeting at F
      [0.7, 0, -0.7].forEach(function (f) {
        var y = f * AP * 0.8;
        put([[-LENS / 100 + 0.03, y], [0, y], [FCM / 100, 0], [Math.max(endX, FCM / 100 + 0.04), -y * (Math.max(endX, FCM / 100 + 0.04) - FCM / 100) / (FCM / 100)]], false);
      });
      return;
    }
    (v.rays || []).forEach(function (r) {
      var pts = r.p.map(function (q) { return [q[0], q[1]]; });
      if (!r.v && pts.length === 4) {
        var a = pts[2], b = pts[3], dx = b[0] - a[0], t = dx > 1e-9 ? (endX - a[0]) / dx : 1;
        pts[3] = [a[0] + t * dx, a[1] + t * (b[1] - a[1])];
      }
      put(pts, !!r.v);
    });
  }
  function update() {
    canStand.setX(xAt(st.cPos), canStand.position.y); scrStand.setX(xAt(st.sPos), scrStand.position.y);
    candle.visible = st.mode === 'bench'; canStand.visible = st.mode === 'bench';
    var v = look(); drawImage(v); drawRays(v);
    VIEWS.screen[0][0] = xAt(st.sPos) - 0.2; VIEWS.screen[1][0] = xAt(st.sPos);
    VIEWS.candle[0][0] = xAt(st.cPos) + 0.14; VIEWS.candle[1][0] = xAt(st.cPos);
    hudU.set(st.mode === 'distant' ? 'a distant window' : uCm().toFixed(1) + ' cm');
    hudV.set(st.sPos.toFixed(1) + ' cm → v = ' + vCm().toFixed(1) + ' cm');
    hudI.set(nature(v));
  }

  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function lightCandle() {
    if (st.lit) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    S.say('Light the candle.');
    return S.hand.tap(wax).then(function () {
      st.lit = true; flame.visible = true; update(); S.render();
      S.say('The candle is lit. Its flame is the object.'); return true; });
  }
  function slide(which, toCm) {
    if (S.hand.busy) return wait();
    var g = which === 'c' ? canStand : scrStand, from = which === 'c' ? st.cPos : st.sPos;
    var lo = which === 'c' ? 3 : LENS + 3, hi = which === 'c' ? LENS - 4 : LEN * 100 - 3;
    toCm = round1(toCm);
    if (!(toCm >= lo && toCm <= hi)) { S.say((which === 'c' ? 'The candle' : 'The screen') + ' slides from ' + lo + ' cm to ' + hi + ' cm on this side of the lens.'); return Promise.resolve(false); }
    if (Math.abs(toCm - from) < 0.05) { if (which === 'c') st.cPos = toCm; else st.sPos = toCm; update(); return Promise.resolve(true); }
    function at(k) { return from + (toCm - from) * k; }
    var grabY = which === 'c' ? AXY - 0.06 : 0.09;
    return S.hand.pinchMove(new T.Vector3(xAt(from) + 0.005, grabY, BZ), function (k) { return new T.Vector3(xAt(at(k)) + 0.005, grabY, BZ); },
      function (k) { if (which === 'c') st.cPos = at(k); else st.sPos = at(k); g.setX(xAt(at(k)), 0); update(); },
      { ms: Math.min(1700, 420 + Math.abs(toCm - from) * 28), reachMs: 550, hold: 120 }).then(function () {
      if (which === 'c') st.cPos = toCm; else st.sPos = toCm; g.setX(xAt(toCm), 0); update(); S.render(); return true; });
  }
  function bestScreen() {
    var keep = p.scr, best = st.sPos, bs = -1, c;
    for (c = LENS + 3; c <= LEN * 100 - 3; c += 0.1) {
      p.scr = (c - LENS) / 100;
      var s = K.view(null, p).sharp;
      if (s > bs) { bs = s; best = c; }
    }
    p.scr = keep; return round1(best);
  }
  function recordDistant() {
    if (S.hand.busy) { wait(); return false; }
    var v = look();
    if (st.mode !== 'distant') { S.say('First point the lens at the open window.'); return false; }
    if (v.sharp < 0.5) { S.say('The patch on the screen is still blurred. Move the screen in 1 mm steps until it is smallest and sharpest.'); return false; }
    st.f0 = round1(vCm());
    S.say('The image of the window is sharp at ' + st.f0.toFixed(1) + ' cm from the lens, so f is about ' + st.f0.toFixed(1) + ' cm.');
    S.render(); return true;
  }
  function record() {
    if (S.hand.busy) { wait(); return false; }
    var v = look();
    if (!st.lit) { S.say('Light the candle first.'); return false; }
    if (!v.real || v.img_x <= 0) { S.say('The candle is inside the focus, so the image is virtual, erect and larger: there is nothing to catch on the screen. Note it down and move the candle beyond F.'); st.insideF = true; S.render(); return false; }
    if (v.sharp < 0.5) { S.say('The image is still blurred. Slide the screen in 1 mm steps until the flame looks sharpest.'); return false; }
    var u = round1(uCm()), vv = round1(vCm());
    if (S.rows.some(function (r) { return Math.abs(r.u - u) < 1; })) { S.say('You already have a reading near u = ' + u.toFixed(1) + ' cm. Move the candle to a new position.'); return false; }
    S.addRow({ u: u, v: vv, m: Math.abs(v.img_h / p.h), where: u > 2 * FCM + 1 ? 'beyond 2F' : u > 2 * FCM - 1 ? 'at 2F' : 'between F and 2F' });
    S.say('Written in your record book: u = ' + u.toFixed(1) + ' cm, v = ' + vv.toFixed(1) + ' cm.');
    return true;
  }

  var dragPlane = new T.Vector3(0, AXY, BZ), dragN = new T.Vector3(0, 0, 1);
  function dragFor(which, objs) {
    S.draggables.push({ objects: objs, enabled: function () { return S.steps[S.step].id === 'positions' && st.lit; },
      move: function (ray) {
        var pt = S.rayPlane(ray, dragPlane, dragN); if (!pt) return;
        var c = Math.round((pt.x - X0) * 1000) / 10;
        var lo = which === 'c' ? 3 : LENS + 3, hi = which === 'c' ? LENS - 4 : LEN * 100 - 3;
        c = Math.max(lo, Math.min(hi, c));
        if (which === 'c') { st.cPos = c; st.cSet = c; } else { st.sPos = c; st.sSet = c; }
        update();
      }, end: function () { S.render(); } });
  }
  dragFor('s', [card, scrStand]); dragFor('c', [wax, canStand]);

  var ft = 0;
  S.tickers.push(function (dt) {
    ft += dt; var f = 1 + 0.06 * Math.sin(ft * 21) + 0.03 * Math.sin(ft * 37 + 1.1);
    flame.scale.set(1, f, 1); fglow.material.opacity = 0.7 + 0.1 * Math.sin(ft * 17);
    lamp.intensity = st.lit ? 0.02 * f : 0;
  });

  var VIEWS = { bench: [[0.04, 0.78, 1.5], [0.0, 0.1, BZ]], lens: [[LX + 0.16, AXY + 0.05, BZ + 0.2], [LX, AXY, BZ]],
    candle: [[0, AXY + 0.05, BZ + 0.2], [0, AXY, BZ]], screen: [[0, AXY, BZ + 0.2], [0, AXY - 0.04, BZ]],
    along: [[X0 + LEN + 0.24, AXY + 0.14, BZ + 0.12], [LX, AXY - 0.02, BZ]],
    book: [[-0.4, 0.44, 0.5], [-0.5, 0.0, 0.08]] };
  update();

  function fMean(rows) {
    var fs = (rows || []).filter(function (r) { return r.u > 0 && r.v > 0; }).map(function (r) { return r.u * r.v / (r.u + r.v); });
    return fs.length ? S.fit.mean(fs) : NaN;
  }

  return {
    camera: { pos: [0.06, 0.82, 1.6], look: [0.0, 0.1, BZ] },
    views: VIEWS,
    theory: { principle: 'A convex lens bends the light from each point of the object back together again. Where the rays meet, a real inverted image forms, and a white screen held exactly there shows it sharply. Light from a very distant object arrives almost parallel, so it meets at the focus: that image distance is the focal length itself.',
      formula: '1/v + 1/u = 1/f',
      formulaNote: 'u, v = distances of the object and the image from the lens, both taken positive for a real image · f = uv/(u + v)',
      more: ['Object beyond 2F: the image lies between F and 2F, inverted and smaller. At 2F: at 2F, inverted, the same size. Between F and 2F: beyond 2F, inverted and larger. At F: no image at all. Inside F: virtual, erect and larger, so nothing can be caught on the screen.',
        'This lens has f about ' + FCM.toFixed(0) + ' cm, so 2F is ' + (2 * FCM).toFixed(0) + ' cm from it. Exactly at 2F the image is the same size as the object, which is a quick way to check f.',
        'Keep the flame, the centre of the lens and the screen at the same height, or the image slides off the card.'],
      precautions: 'Wipe the lens with a soft cloth only. Find the sharpest image by moving the screen both ways in small steps, and read each stand at its index mark with your eye straight above it. Never use a convex lens to look at the sun.' },
    book: { title: 'Expt. — Convex lens: images and f', lines: ['Aim: to see the image for each position of the object and find f.',
      'Lens at ' + LENS.toFixed(1) + ' cm on the bench scale.', 'u = lens − candle,  v = screen − lens',
      'From a distant object: v = f directly.', 'f = uv/(u + v).'],
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Position', get: function (r) { return r.where; } },
        { label: 'u (cm)', get: function (r) { return r.u.toFixed(1); } }, { label: 'v (cm)', get: function (r) { return r.v.toFixed(1); } },
        { label: 'm', get: function (r) { return r.m.toFixed(2); } }, { label: 'f (cm)', get: function (r) { return (r.u * r.v / (r.u + r.v)).toFixed(2); } }] },
    graph: { x: function (r) { return 100 / r.u; }, y: function (r) { return 100 / r.v; }, xlabel: '1/u (m⁻¹)', ylabel: '1/v (m⁻¹)', x0: 0, y0: 0,
      line: function (pts) { var L = S.fit.linear(pts); return L ? function (x) { return L.m * x + L.c; } : null; } },
    result: function (rows) {
      var f = fMean(rows); if (!isFinite(f) || (rows || []).length < 3) return null;
      return { label: 'f', value: f, unit: 'cm', digits: 1, truth: FCM,
        note: 'Mean of uv/(u + v)' + (st.f0 ? '; the distant window gave about ' + st.f0.toFixed(1) + ' cm' : '') + '.' };
    },
    tol: 0.03,
    chips: ['Why is the image inverted?', 'Where is the image when the object is at 2F?', 'Why is there no image inside F?', 'Check my readings', 'Why is my f a little different?'],
    viva: [['The object is at 2F of a convex lens. The image is?', ['At 2F, inverted, the same size', 'At F', 'Virtual and erect'], 0, 'u = 2f gives v = 2f.'],
      ['The image of a distant tree by a convex lens falls at?', ['The focus', 'The optical centre', '2F'], 0, 'Parallel light meets at F.'],
      ['Half the lens is covered with black paper. The image then?', ['Stays whole but gets dimmer', 'Is cut in half', 'Disappears'], 0, 'Every part of the lens makes the whole image; covering part only cuts the light.']],
    askState: function () {
      var v = view || look();
      return { lens_at_cm: LENS, focal_length_of_this_lens_cm: +FCM.toFixed(1), mode: st.mode === 'distant' ? 'image of a distant window' : 'candle on the bench',
        candle_at_cm: st.cPos, screen_at_cm: st.sPos, u_cm: st.mode === 'distant' ? null : +uCm().toFixed(1), v_cm: +vCm().toFixed(1),
        candle_lit: st.lit, f_from_distant_object_cm: st.f0, image_on_the_screen: nature(v),
        sharpness_0_to_1: +v.sharp.toFixed(2), image_is_real: !!v.real, tried_inside_F: st.insideF };
    },

    steps: [
      { id: 'distant', title: 'f from a distant object', view: 'along', render: function (u) {
          u.h2('Catch the image of a distant window');
          u.p('Turn the bench so the lens faces the open window. The light arrives almost parallel, so the image forms at the focus. Slide the screen until the small bright patch is sharpest and read the scale.');
          u.task('1. Point the lens at the window', st.mode === 'distant', st.mode === 'distant' ? 'Parallel light is falling on the lens' : 'The candle stand is taken off the bench')
            .add(u.button(st.mode === 'distant' ? 'Pointing at the window' : 'Point at the window', function () { st.mode = 'distant'; update(); S.focus('along'); S.render(); }, st.mode !== 'distant', st.mode === 'distant' || S.hand.busy));
          u.task('2. Slide the screen to the sharpest patch', st.f0 !== null, st.f0 !== null ? 'Sharp at ' + st.f0.toFixed(1) + ' cm, so f ≈ ' + st.f0.toFixed(1) + ' cm' : 'Screen at ' + st.sPos.toFixed(1) + ' cm → v = ' + vCm().toFixed(1) + ' cm');
          u.slider('Screen position', LENS + 3, Math.round(LEN * 100 - 3), 0.1, function () { return st.sSet; }, function (x) { st.sSet = x; }, 'cm', 1);
          u.row(u.button('Slide the screen there', function () { slide('s', st.sSet); S.render(); }, true, S.hand.busy),
            u.button('Look at the screen', function () { update(); S.focus('screen'); }));
          u.live(function () { var v = view || look(); return 'Patch on the screen: ' + (v.sharp > 0.85 ? 'sharp' : v.sharp > 0.45 ? 'nearly sharp' : 'blurred'); });
          u.row(u.button('Record f from the distant object', function () { recordDistant(); }, true, S.hand.busy || st.mode !== 'distant'));
          u.note('This is the quickest way to find a rough f before the real readings, and it is the Class X practical on its own.');
          u.next('Next: the candle on the bench', st.f0 !== null);
        },
        ok: function () { return st.f0 !== null; },
        auto: function () { st.mode = 'distant'; update(); return slide('s', bestScreen()).then(function () { recordDistant(); }); } },
      { id: 'positions', title: 'Each position of the object', view: 'screen', render: function (u) {
          u.h2('Put the candle at each position and find the image');
          u.p('Bring the candle back on the bench and light it. For each position slide the screen until the image is sharpest, then read u and v. Try beyond 2F, just beyond 2F, between F and 2F, and finally inside F.');
          u.task('Candle', st.lit, st.lit ? 'Lit, at ' + st.cPos.toFixed(1) + ' cm → u = ' + uCm().toFixed(1) + ' cm' : 'Not lit yet')
            .add(u.button(st.lit ? 'Candle lit' : 'Light the candle', function () { st.mode = 'bench'; update(); lightCandle(); }, !st.lit, st.lit || S.hand.busy));
          u.slider('Candle position', 3, LENS - 4, 0.5, function () { return st.cSet; }, function (x) { st.cSet = x; }, 'cm', 1);
          u.row(u.button('Move the candle there', function () { st.mode = 'bench'; slide('c', st.cSet); S.render(); }, true, S.hand.busy),
            u.button('Beyond 2F', function () { st.cSet = round1(LENS - 3 * FCM); S.render(); }),
            u.button('Just beyond 2F', function () { st.cSet = round1(LENS - 2.25 * FCM); S.render(); }),
            u.button('Between F and 2F', function () { st.cSet = round1(LENS - 1.5 * FCM); S.render(); }),
            u.button('Inside F', function () { st.cSet = round1(LENS - 0.6 * FCM); S.render(); }));
          u.task('Screen', true, 'At ' + st.sPos.toFixed(1) + ' cm → v = ' + vCm().toFixed(1) + ' cm');
          u.slider('Screen position', LENS + 3, Math.round(LEN * 100 - 3), 0.1, function () { return st.sSet; }, function (x) { st.sSet = x; }, 'cm', 1);
          u.row(u.button('Slide the screen there', function () { slide('s', st.sSet); S.render(); }, true, S.hand.busy),
            u.button('Find the sharpest', function () { st.sSet = bestScreen(); slide('s', st.sSet); S.render(); }, false, S.hand.busy));
          u.live(function () { var v = view || look(); return 'Image: ' + nature(v); });
          u.row(u.button('Record u and v', function () { record(); }, true, S.hand.busy),
            u.button(st.rays ? 'Hide the rays' : 'Show the rays', function () { st.rays = !st.rays; update(); S.render(); }));
          u.h3('Observation table'); u.table();
          if (!st.insideF) u.note('Do not forget the last position: bring the candle inside F and try to catch the image. Nothing falls on the screen, because the image is virtual.');
          u.next('Next: graph and result', S.rows.length >= 3 && st.insideF);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 positions recorded.');
        },
        ok: function () { return S.rows.length >= 3 && st.insideF; },
        auto: function () {
          st.mode = 'bench'; update();
          var us = [3, 2.25, 1.5].map(function (k) { return round1(LENS - k * FCM); });
          return lightCandle().then(function () {
            return us.reduce(function (pr, cm) {
              return pr.then(function () {
                st.cSet = cm;
                return slide('c', cm).then(function () { st.sSet = bestScreen(); return slide('s', st.sSet); }).then(function () { record(); });
              });
            }, Promise.resolve());
          }).then(function () { return slide('c', round1(LENS - 0.6 * FCM)).then(function () { record(); }); });
        } },
    ],

    tick: function () { update(); },
  };
});
