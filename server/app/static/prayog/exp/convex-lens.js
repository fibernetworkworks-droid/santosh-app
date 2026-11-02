/* Prayogshala studio module: Convex lens, f from u and v (NCERT Class XII). A lit candle, a biconvex lens and a white screen
   on an optical bench; the hand slides the uprights; the candle's inverted image is projected onto the screen, blurred or
   sharp exactly as the lens kernel's thick-lens ray trace says ('img_x', 'img_h', 'sharp'). f = uv / (u + v); true f from
   the lensmaker's formula (the kernel's 'f'). */
HoolaStudio.define('convex-lens', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.lens;
  var p = window.HoolaKernels.paramsFor('lens', S.lab.params);
  var X0 = -0.9, LEN = 1.8, BZ = -0.2, AXY = 0.24, MIR = 90;     // bench start x, length, z of the axis, axis height, lens mark (cm)
  var RIM = Math.sqrt(Math.max(p.R * p.d - p.d * p.d / 4, 1e-8)); // where the two curved faces meet: the lens's real edge
  var AP = RIM * 0.97;                                          // clear aperture radius
  var CARD_W = 0.11, CARD_H = 0.15, CARD_TOP = 0.03;            // white screen card, centred a little below the axis
  var st = { lit: false, cPos: 40, sPos: 125, cSet: 40, sSet: 125, rays: false, view: null };
  function xAt(cm) { return X0 + cm / 100; }
  function uCm() { return MIR - st.cPos; }
  function vCm() { return st.sPos - MIR; }

  // ---------- the optical bench and its uprights
  var bench = S.opticalBench({ len: LEN, x0: X0, z: BZ, start: 0 });
  // the engine's bench feet are 8 cm tall and poke up through the bed at both ends: tuck them under the bed
  bench.children.forEach(function (m) { if (m.geometry && m.geometry.type === 'ExtrudeGeometry') { m.scale.z = 0.25; m.position.y = 0.01; } });
  var plate = S.label('OPTICAL BENCH · scale in cm · LC 1 mm', { w: 0.2, ratio: 0.1, color: '#e8e2cf', weight: 600 });
  plate.position.set(X0 + LEN - 0.16, 0.03, BZ + 0.0302); bench.add(plate);

  function carriage(postTop, name) {
    var g = new T.Group(); S.scene.add(g); g.position.z = BZ;
    var top = S.rounded(0.044, 0.042, 0.012, 0.003, M.alu); top.rotation.x = -Math.PI / 2; top.position.set(0, 0.046, -0.013); g.add(top);
    var back = S.rounded(0.044, 0.034, 0.006, 0.002, M.alu); back.position.set(0, 0.035, -0.034); g.add(back);
    var front = S.rounded(0.044, 0.028, 0.005, 0.002, M.alu); front.position.set(0, 0.031, 0.0355); g.add(front);
    var tongue = S.mesh(new T.BoxGeometry(0.008, 0.003, 0.03), M.black); tongue.position.set(0, 0.0428, 0.022); g.add(tongue);
    var hair = S.mesh(new T.BoxGeometry(0.0008, 0.0004, 0.028), M.red, false); hair.position.set(0, 0.0445, 0.022); g.add(hair);
    var knob = S.mesh(new T.CylinderGeometry(0.0075, 0.0075, 0.01, 18), M.bakelite); knob.rotation.x = Math.PI / 2; knob.position.set(0, 0.034, -0.044); g.add(knob);
    var screw = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.008, 10), M.steel); screw.rotation.x = Math.PI / 2; screw.position.set(0, 0.034, -0.0385); g.add(screw);
    var sock = S.mesh(new T.CylinderGeometry(0.009, 0.0105, 0.022, 24), M.alu); sock.position.set(0, 0.063, 0); g.add(sock);
    var sk = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.012, 12), M.bakelite); sk.rotation.z = Math.PI / 2; sk.position.set(0.013, 0.066, 0); g.add(sk);
    var post = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, postTop - 0.07, 20), M.chrome); post.position.y = 0.07 + (postTop - 0.07) / 2; g.add(post);
    var sh = S.contact(0.075, 0.1, 0, BZ, 0.42, 0.04);
    g.setX = function (x, lift) { g.position.x = x; g.position.y = lift || 0; sh.position.x = x; sh.material.opacity = 0.42 * Math.max(0.15, 1 - (lift || 0) * 8); };
    g.userData.name = name; return g;
  }

  // ---------- flame (candle and match share it)
  var glowTex = S.canvasTex(128, 128, function (x) { var gr = x.createRadialGradient(64, 64, 2, 64, 64, 64);
    gr.addColorStop(0, 'rgba(255,214,140,0.9)'); gr.addColorStop(0.25, 'rgba(255,170,70,0.35)'); gr.addColorStop(1, 'rgba(255,140,40,0)'); x.fillStyle = gr; x.fillRect(0, 0, 128, 128); });
  function lathe(hgt, wid, seg) { var pts = []; for (var i = 0; i <= 16; i++) { var t = i / 16; pts.push(new T.Vector2(wid * Math.pow(Math.sin(Math.PI * Math.pow(t, 0.75)), 0.9) * (1 - 0.35 * t), t * hgt)); } return new T.LatheGeometry(pts, seg || 24); }
  function makeFlame(hgt, wid) {
    var g = new T.Group();
    var outer = new T.Mesh(lathe(hgt, wid), new T.MeshBasicMaterial({ color: 0xffa23a, transparent: true, opacity: 0.85, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending }));
    var inner = new T.Mesh(lathe(hgt * 0.62, wid * 0.55), new T.MeshBasicMaterial({ color: 0xfff3cf, transparent: true, opacity: 0.95, depthWrite: false, toneMapped: false }));
    inner.position.y = hgt * 0.06;
    var blue = new T.Mesh(new T.SphereGeometry(wid * 0.55, 12, 8), new T.MeshBasicMaterial({ color: 0x4a6cff, transparent: true, opacity: 0.45, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending }));
    blue.scale.y = 0.6; blue.position.y = hgt * 0.08;
    var glow = new T.Sprite(new T.SpriteMaterial({ map: glowTex, transparent: true, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending, opacity: 0.7 }));
    glow.scale.set(hgt * 4.2, hgt * 4.2, 1); glow.position.y = hgt * 0.45;
    [outer, inner, blue].forEach(function (m) { m.renderOrder = 5; g.add(m); }); glow.renderOrder = 6; g.add(glow);
    g.userData = { outer: outer, inner: inner, glow: glow, h: hgt };
    return g;
  }

  // ---------- the convex lens (centre at the 90.0 cm mark) in its ring holder
  var MX = xAt(MIR);
  var mirCar = carriage(AXY - RIM - 0.012, 'lens'); mirCar.setX(MX);
  var mirror = new T.Group(); mirror.position.set(0, AXY, 0); mirCar.add(mirror);
  var prof = [], NS = 24, rr, tt;
  for (var li = 0; li <= NS; li++) { rr = RIM * 0.995 * li / NS; tt = Math.max(0.00025, p.d / 2 - (p.R - Math.sqrt(p.R * p.R - rr * rr))); prof.push(new T.Vector2(rr, -tt)); }
  for (li = NS; li >= 0; li--) { rr = RIM * 0.995 * li / NS; tt = Math.max(0.00025, p.d / 2 - (p.R - Math.sqrt(p.R * p.R - rr * rr))); prof.push(new T.Vector2(rr, tt)); }
  var glass = new T.MeshPhysicalMaterial({ color: 0xf4fbff, roughness: 0.02, metalness: 0, transmission: 0.96, thickness: p.d, ior: p.n, transparent: true, opacity: 0.9,
    clearcoat: 1, clearcoatRoughness: 0.02, envMapIntensity: 1.4, side: T.DoubleSide });
  var face = new T.Mesh(new T.LatheGeometry(prof, 72), glass); face.rotation.z = Math.PI / 2; face.renderOrder = 3; mirror.add(face);
  var ring = S.mesh(new T.TorusGeometry(RIM + 0.0018, 0.0026, 12, 64), M.bakelite); ring.rotation.y = Math.PI / 2; mirror.add(ring);
  var ringB = S.mesh(new T.CylinderGeometry(RIM + 0.0042, RIM + 0.0042, 0.006, 64, 1, true), new T.MeshStandardMaterial({ color: 0x1b1c1f, roughness: 0.5, side: T.DoubleSide }));
  ringB.rotation.z = Math.PI / 2; mirror.add(ringB);
  var lug = S.mesh(new T.BoxGeometry(0.01, 0.012, 0.012), M.bakelite); lug.position.set(0, -RIM - 0.009, 0); mirror.add(lug);
  var tiltK = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.006, 16), M.bakelite); tiltK.rotation.x = Math.PI / 2; tiltK.position.set(0, -RIM - 0.009, 0.01); mirror.add(tiltK);
  var mLab = S.label('BICONVEX', { w: 0.03, ratio: 0.22, color: '#c8ccd2', weight: 700 }); mLab.position.set(0, -RIM - 0.009, 0.0062); mirror.add(mLab);

  // ---------- the candle on its upright
  var canCar = carriage(AXY - 0.004, 'candle');
  var candle = new T.Group(); candle.position.y = AXY; canCar.add(candle);
  var dish = S.mesh(new T.CylinderGeometry(0.019, 0.016, 0.004, 32), M.brass); dish.position.y = -0.002; candle.add(dish);
  var rim = S.mesh(new T.TorusGeometry(0.019, 0.0012, 8, 40), M.brass); rim.rotation.x = Math.PI / 2; candle.add(rim);
  var waxM = new T.MeshStandardMaterial({ color: 0xf4ecd9, roughness: 0.5, emissive: 0x000000 });
  var wax = S.mesh(new T.CylinderGeometry(0.0074, 0.0078, 0.034, 32), waxM); wax.position.y = 0.017; candle.add(wax);
  var pool = S.mesh(new T.CircleGeometry(0.0062, 24), new T.MeshStandardMaterial({ color: 0xe9dcc0, roughness: 0.15 })); pool.rotation.x = -Math.PI / 2; pool.position.y = 0.0341; candle.add(pool);
  var drip = S.mesh(new T.CapsuleGeometry(0.0012, 0.008, 4, 8), waxM); drip.position.set(0.0072, 0.027, 0.002); candle.add(drip);
  var wick = S.mesh(new T.CylinderGeometry(0.0005, 0.0006, 0.0045, 6), M.black); wick.position.y = 0.0362; wick.rotation.z = 0.15; candle.add(wick);
  var flame = makeFlame(p.h - 0.0365, 0.0034); flame.position.y = 0.0365; flame.visible = false; candle.add(flame);
  var lamp = new T.PointLight(0xffa851, 0, 0, 2); lamp.position.y = 0.043; candle.add(lamp);

  // ---------- the white screen on its upright
  var scrCar = carriage(AXY + CARD_TOP - CARD_H - 0.002, 'screen');
  var screen = new T.Group(); screen.position.y = AXY; scrCar.add(screen);
  var card = S.mesh(new T.BoxGeometry(0.003, CARD_H, CARD_W), new T.MeshStandardMaterial({ color: 0xe2e0d8, roughness: 0.95 }));
  card.position.y = CARD_TOP - CARD_H / 2; screen.add(card);
  [[0, CARD_TOP - CARD_H - 0.002, 0, 0.008, 0.005, CARD_W + 0.006], [0, CARD_TOP + 0.001, 0, 0.006, 0.003, CARD_W + 0.006]].forEach(function (a) {
    var b = S.mesh(new T.BoxGeometry(a[3], a[4], a[5]), M.black); b.position.set(a[0], a[1], a[2]); screen.add(b); });
  var imgTex = S.liveTex(256, Math.round(256 * CARD_H / CARD_W)), PXM = 256 / CARD_W;
  var img = new T.Mesh(new T.PlaneGeometry(CARD_W, CARD_H), new T.MeshBasicMaterial({ map: imgTex, transparent: true, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending }));
  img.rotation.y = -Math.PI / 2; img.position.set(-0.0019, CARD_TOP - CARD_H / 2, 0); img.renderOrder = 4; screen.add(img);

  // ---------- matchbox and a matchstick
  var MB = new T.Vector3(xAt(70), 0, BZ + 0.13);
  var box = new T.Group(); box.position.copy(MB); box.rotation.y = 0.25; S.scene.add(box);
  var tray = S.rounded(0.052, 0.036, 0.014, 0.002, new T.MeshStandardMaterial({ color: 0xd9c9a0, roughness: 0.8 })); tray.rotation.x = -Math.PI / 2; tray.position.y = 0.007; box.add(tray);
  var boxTex = S.canvasTex(256, 180, function (x, w, h) { x.fillStyle = '#c0392b'; x.fillRect(0, 0, w, h); x.fillStyle = '#f6d55c'; x.font = '700 46px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText('SAFETY', w / 2, 80); x.fillText('MATCHES', w / 2, 130); });
  var sleeve = S.mesh(new T.BoxGeometry(0.054, 0.015, 0.038), [new T.MeshStandardMaterial({ color: 0x5b3a26, roughness: 1 }), new T.MeshStandardMaterial({ color: 0x5b3a26, roughness: 1 }), new T.MeshStandardMaterial({ map: boxTex, roughness: 0.7 }), M.red, M.red, M.red]);
  sleeve.position.set(0.012, 0.0076, 0); box.add(sleeve);
  S.contact(0.09, 0.07, MB.x, MB.z, 0.45);
  var match = new T.Group(); S.scene.add(match);
  var stick = S.mesh(new T.BoxGeometry(0.044, 0.0022, 0.0022), new T.MeshStandardMaterial({ color: 0xe2c48c, roughness: 0.8 })); match.add(stick);
  var headM = new T.MeshStandardMaterial({ color: 0x9c2a1c, roughness: 0.6 });
  var head = S.mesh(new T.SphereGeometry(0.0022, 12, 8), headM); head.scale.set(1.5, 1, 1); head.position.x = -0.023; match.add(head);
  var mFlame = makeFlame(0.011, 0.0028); mFlame.rotation.z = -0.5; mFlame.position.set(-0.025, 0.001, 0); mFlame.visible = false; match.add(mFlame);
  var MATCH_REST = new T.Vector3(MB.x - 0.004, 0.0165, MB.z - 0.004);
  match.position.copy(MATCH_REST); match.rotation.y = 0.25;

  // ---------- kernel rays (faint lines the student can toggle)
  var rayMat = new T.LineBasicMaterial({ color: 0xffc15a, transparent: true, opacity: 0.55, depthWrite: false, toneMapped: false });
  var rayDash = new T.LineDashedMaterial({ color: 0xffc15a, transparent: true, opacity: 0.35, dashSize: 0.006, gapSize: 0.005, depthWrite: false, toneMapped: false });
  var rayLines = [];
  for (var ri = 0; ri < 6; ri++) { var ln = new T.Line(new T.BufferGeometry(), rayMat); ln.visible = false; ln.renderOrder = 7; S.scene.add(ln); rayLines.push(ln); }

  S.addApparatus('bench', bench, 'Optical bench', 'A rigid iron bed, 180 cm long, with a centimetre scale (least count 1 mm). Each upright has an index mark that you read on the scale.');
  S.addApparatus('lens', mirCar, 'Convex lens', 'A thin biconvex glass lens in a ring holder, clamped with its centre exactly at the 90.0 cm mark.');
  S.addApparatus('candle', canCar, 'Candle on an upright', 'The lit flame is the bright object, on the left of the lens, standing on the principal axis.');
  S.addApparatus('screen', scrCar, 'White screen', 'A white card on the right of the lens. Slide it until the inverted image of the flame is sharp.');
  S.addApparatus('box', box, 'Safety matches', 'To light the candle. Keep the box away from the flame.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudC = S.hudCard('Candle at'), hudS = S.hudCard('Screen at'), hudI = S.hudCard('Image on the screen');

  // ---------- physics from the kernel
  var view = null, lastKey = '';
  function look() {
    p.u = Math.max(0.001, uCm() / 100); p.scr = Math.max(0.001, vCm() / 100);
    view = K.view(null, p); return view;
  }
  function sharpWord(v) { if (!st.lit) return 'Candle not lit'; if (!v.real) return 'No image (it is virtual)'; var s = v.sharp;
    return s > 0.85 ? 'Sharp' : s > 0.45 ? 'Nearly sharp' : s > 0.12 ? 'Blurred' : 'Very blurred'; }
  function drawImage(v) {
    var real = st.lit && v.real && v.img_x > 0, scrM = p.scr;
    var mag = real ? (v.img_h / p.h) * (scrM / v.img_x) : 0;                       // projected size on the card (negative: inverted)
    var blurM = real ? 2 * AP * Math.sqrt(Math.max(0, 1 / Math.max(v.sharp, 1e-6) - 1)) * 0.004 / v.img_x : 0;   // blur circle from the kernel's sharpness
    var key = [st.lit ? 1 : 0, real ? 1 : 0, mag.toFixed(3), Math.min(blurM, 0.2).toFixed(4)].join('|');
    if (key === lastKey) return; lastKey = key;
    imgTex.draw(function (x, w, h) {
      x.clearRect(0, 0, w, h); if (!st.lit) return;
      var ax = CARD_TOP * PXM, cx = w / 2;                                          // the axis is just above the card's top edge
      if (!real) { var gg = x.createRadialGradient(cx, ax + 30, 4, cx, ax + 30, 150); gg.addColorStop(0, 'rgba(255,170,80,0.10)'); gg.addColorStop(1, 'rgba(255,170,80,0)'); x.fillStyle = gg; x.fillRect(0, 0, w, h); return; }
      var k = Math.abs(mag) * PXM, sig = Math.min(80, blurM * PXM * 0.5);
      var bright = Math.min(1, 1.1 / (0.35 + Math.abs(mag))) * (1 / (1 + Math.pow(sig / Math.max(6, k * 0.012), 2) * 0.05));
      x.save(); if (sig > 0.4) x.filter = 'blur(' + sig.toFixed(1) + 'px)';
      x.globalAlpha = Math.max(0.08, Math.min(1, bright));
      x.translate(cx, ax); x.scale(k, k);                                             // object metres -> card pixels, inverted (y down = below axis)
      x.fillStyle = 'rgba(150,95,45,0.55)'; x.fillRect(-0.0076, 0, 0.0152, 0.034);   // the candle body (lit only by its flame)
      x.fillStyle = 'rgba(180,120,60,0.35)'; x.fillRect(-0.019, -0.002, 0.038, 0.004);
      var fh = p.h - 0.0365, fy = 0.0365;
      var g1 = x.createRadialGradient(0, fy + fh * 0.5, 0.0003, 0, fy + fh * 0.55, fh * 0.75);
      g1.addColorStop(0, 'rgba(255,250,225,1)'); g1.addColorStop(0.45, 'rgba(255,205,110,0.95)'); g1.addColorStop(1, 'rgba(255,130,40,0)');
      x.fillStyle = g1; x.beginPath(); x.ellipse(0, fy + fh * 0.5, 0.0042, fh * 0.62, 0, 0, Math.PI * 2); x.fill(); x.fill();
      var g2 = x.createRadialGradient(0, fy + fh * 0.5, 0.0005, 0, fy + fh * 0.5, 0.016);
      g2.addColorStop(0, 'rgba(255,190,100,0.35)'); g2.addColorStop(1, 'rgba(255,150,60,0)'); x.fillStyle = g2; x.fillRect(-0.02, fy - 0.01, 0.04, 0.04);
      x.restore();
    });
  }
  function drawRays(v) {
    rayLines.forEach(function (l) { l.visible = false; });
    if (!st.rays || !st.lit) return;
    var n = 0, scrX = p.scr, endX = Math.min(LEN - MIR / 100 - 0.01, Math.max(p.scr, v.img_x > 0 ? v.img_x : 0) + 0.12);
    (v.rays || []).forEach(function (r) {
      if (n >= rayLines.length) return; var pts = r.p.map(function (q) { return [q[0], q[1]]; });
      if (!r.v && pts.length >= 3) {                                                // clip the emerging leg at the card or a little past the image
        var L = pts.length - 1, a = pts[L - 1], b = pts[L], dx = b[0] - a[0], t = dx > 1e-9 ? (scrX - a[0]) / dx : -1, yAt = a[1] + t * (b[1] - a[1]);
        if (t > 0 && t < 1 && yAt <= CARD_TOP && yAt >= CARD_TOP - CARD_H) pts[L] = [scrX, yAt];
        else { var t2 = dx > 1e-9 ? (endX - a[0]) / dx : 1; pts[L] = [a[0] + t2 * dx, a[1] + t2 * (b[1] - a[1])]; }
      }
      var l = rayLines[n++]; l.material = r.v ? rayDash : rayMat;
      l.geometry.setFromPoints(pts.map(function (q) { return new T.Vector3(MX + q[0], AXY + q[1], BZ + 0.0005); }));
      if (r.v) l.computeLineDistances(); l.visible = true; });
  }
  function update() {
    canCar.setX(xAt(st.cPos), canCar.position.y); scrCar.setX(xAt(st.sPos), scrCar.position.y);
    var v = look(); drawImage(v); drawRays(v);
    var sx = xAt(st.sPos);
    VIEWS.screen[0][0] = sx - 0.26; VIEWS.screen[0][1] = AXY + 0.03; VIEWS.screen[0][2] = BZ + 0.3; VIEWS.screen[1][0] = sx; VIEWS.screen[1][1] = AXY - 0.04; VIEWS.screen[1][2] = BZ;
    var cx = xAt(st.cPos); VIEWS.candle[0][0] = cx + 0.12; VIEWS.candle[1][0] = cx;
    hudC.set(st.cPos.toFixed(1) + ' cm'); hudS.set(st.sPos.toFixed(1) + ' cm'); hudI.set(sharpWord(v));
  }

  // ---------- human actions (each one by the hand)
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function lightCandle() {
    if (st.lit) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    var tail0 = new T.Vector3(MATCH_REST.x + 0.02, MATCH_REST.y + 0.002, MATCH_REST.z);
    var wk = new T.Vector3(xAt(st.cPos) + 0.048, AXY + 0.0405, BZ + 0.002);
    var mid = new T.Vector3((tail0.x + wk.x) / 2 + 0.03, AXY + 0.08, (tail0.z + wk.z) / 2);
    function path(k) { var a = 1 - k, q = new T.Vector3(); q.addScaledVector(tail0, a * a).addScaledVector(mid, 2 * a * k).addScaledVector(wk, k * k); return q; }
    function place(k) { var q = path(k); match.position.set(q.x - 0.02, q.y, q.z); match.rotation.set(0, 0.25 * (1 - k), 0.2 * k); mFlame.visible = k > 0.12; }
    S.say('Strike a match and bring it to the wick.');
    return S.hand.pinchMove(tail0, path, place, { ms: 1500, release: false, hold: 500 }).then(function () {
      st.lit = true; flame.visible = true; mFlame.visible = false; headM.color.setHex(0x1d1a18);
      match.position.set(MB.x + 0.05, 0.0012, MB.z + 0.02); match.rotation.set(0, -0.6, 0);
      update(); S.say('The candle is lit. The match is out and resting beside the box.'); S.render(); return true; });
  }
  function moveUpright(which, toCm) {
    if (S.hand.busy) return wait();
    var car = which === 'c' ? canCar : scrCar, other = which === 'c' ? st.sPos : st.cPos, from = which === 'c' ? st.cPos : st.sPos;
    var lo = which === 'c' ? 3 : MIR + 4, hi = which === 'c' ? MIR - 6 : LEN * 100 - 3;
    toCm = Math.round(toCm * 10) / 10;
    if (!(toCm >= lo && toCm <= hi)) { S.say((which === 'c' ? 'The candle' : 'The screen') + ' can go from ' + lo + ' cm to ' + hi + ' cm on this bench.'); return Promise.resolve(false); }
    if (Math.abs(toCm - from) < 0.05) return Promise.resolve(true);
    var pass = false;                                                               // the lens sits between them: they never cross
    var grabY = which === 'c' ? AXY - 0.07 : 0.072;
    function lift(k) { return pass ? 0.13 * Math.sin(Math.PI * Math.min(1, k)) : 0; }
    function at(k) { return from + (toCm - from) * k; }
    var ms = Math.min(1800, 450 + Math.abs(toCm - from) * 30) + (pass ? 600 : 0);
    return S.hand.pinchMove(new T.Vector3(xAt(from) + 0.006, grabY, BZ), function (k) { return new T.Vector3(xAt(at(k)) + 0.006, grabY + lift(k), BZ); },
      function (k) { if (which === 'c') st.cPos = at(k); else st.sPos = at(k); car.setX(xAt(at(k)), lift(k)); update(); },
      { ms: ms, reachMs: 600, hold: 120 }).then(function () {
      if (which === 'c') st.cPos = toCm; else st.sPos = toCm; car.setX(xAt(toCm), 0); update(); S.render(); return true; });
  }
  function record() {
    if (S.hand.busy) { wait(); return false; }
    var v = look();
    if (!st.lit) { S.say('Light the candle first.'); return false; }
    if (!v.real || v.img_x <= 0) { S.say('No real image forms: the candle is inside the focus. Move it further from the lens.'); return false; }
    if (v.img_x * 100 > LEN * 100 - 3 - MIR) { S.say('The image forms beyond the end of the bench. Move the candle further from the lens.'); return false; }
    if (v.sharp < 0.5) { S.say('The image on the screen is still blurred. Move the screen in small steps (1 mm) until the flame looks sharpest.'); return false; }
    var u = Math.round(uCm() * 10) / 10, vv = Math.round(vCm() * 10) / 10;
    if (S.rows.some(function (r) { return Math.abs(r.u - u) < 1; })) { S.say('You already have a reading near u = ' + u.toFixed(1) + ' cm. Move the candle to a new position.'); return false; }
    S.addRow({ m: MIR, c: st.cPos, s: st.sPos, u: u, v: vv });
    S.say('Written in your record book: u = ' + u.toFixed(1) + ' cm, v = ' + vv.toFixed(1) + ' cm.');
    return true;
  }
  function bestScreen() {                                                          // what a careful student converges to: the sharpest mark (1 mm steps)
    var best = st.sPos, bs = -1, keep = p.scr, c;
    for (c = MIR + 4; c <= LEN * 100 - 3; c += 0.1) { p.scr = (c - MIR) / 100; var s = K.view(null, p).sharp; if (s > bs) { bs = s; best = c; } }
    p.scr = keep; return Math.round(best * 10) / 10;
  }

  // ---------- drag the uprights yourself (pointer = your hand)
  var dragPlane = new T.Vector3(0, AXY, BZ), dragN = new T.Vector3(0, 0, 1);
  function dragFor(which, objs) { S.draggables.push({ objects: objs, enabled: function () { return S.steps[S.step].id === 'image' && st.lit; },
    move: function (ray) { var pt = S.rayPlane(ray, dragPlane, dragN); if (!pt) return; var c = Math.round((pt.x - X0) * 1000) / 10;
      var lo = which === 'c' ? 3 : MIR + 4, hi = which === 'c' ? MIR - 6 : LEN * 100 - 3;
      c = Math.max(lo, Math.min(hi, c));
      if (which === 'c') { st.cPos = c; st.cSet = c; } else { st.sPos = c; st.sSet = c; } update(); },
    end: function () { S.render(); } }); }
  dragFor('s', [card, scrCar]); dragFor('c', [wax, canCar]);

  // flame flicker + candle glow
  var ft = 0;
  S.tickers.push(function (dt) { ft += dt;
    var f = 1 + 0.05 * Math.sin(ft * 23) + 0.035 * Math.sin(ft * 37 + 1.3) + 0.02 * Math.sin(ft * 71);
    flame.scale.set(1 + 0.03 * Math.sin(ft * 19), f, 1 + 0.03 * Math.sin(ft * 17)); flame.rotation.z = 0.035 * Math.sin(ft * 2.1);
    lamp.intensity = st.lit ? 0.022 * f : 0; waxM.emissive.setRGB(st.lit ? 0.10 : 0, st.lit ? 0.055 : 0, st.lit ? 0.015 : 0);
    mFlame.scale.set(1, 1 + 0.08 * Math.sin(ft * 29), 1); });

  var VIEWS = { bench: [[-0.05, 0.62, 1.3], [-0.05, 0.16, -0.2]], lens: [[MX + 0.1, AXY + 0.03, BZ + 0.16], [MX, AXY - 0.005, BZ]],
    candle: [[0, AXY + 0.06, BZ + 0.22], [0, AXY, BZ]], screen: [[0, AXY, BZ + 0.21], [0, AXY - 0.05, BZ]],
    box: [[MB.x + 0.12, 0.16, MB.z + 0.22], [MB.x, 0.01, MB.z]], align: [[X0 - 0.1, AXY + 0.05, BZ + 0.03], [MX, AXY - 0.02, BZ]],
    book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] };
  update();

  return {
    camera: { pos: [0.0, 0.78, 1.42], look: [0.0, 0.1, -0.2] },
    views: VIEWS,
    theory: { principle: 'A convex lens bends the light from a bright object so that it meets again on the other side, forming a real, inverted image. A white screen placed exactly there shows a sharp image; anywhere else the light is spread into a blur.',
      formula: '1/v + 1/u = 1/f', formulaNote: 'u, v = distances of the object and the image from the lens (real image, both taken positive) · lensmaker: 1/f = (n − 1)(1/R₁ + 1/R₂)',
      more: ['With n = 1.5 and both faces R = 20 cm, the lensmaker’s formula gives f = 20 cm. A graph of 1/v against 1/u is a straight line cutting both axes at 1/f.',
        'The flame tip is a few centimetres off the axis, so keep u well beyond f (40 cm or more here): the image then stays close to the axis and the thin-lens formula holds closely.'],
      precautions: 'Keep the flame, the centre of the lens and the screen in one line along the bench. Find the sharpest image by moving the screen both ways in small steps. Read each upright at its index mark, with your eye straight above it. Keep paper and the matchbox away from the flame.' },
    book: { title: 'Expt. — Convex Lens (u–v)', lines: ['Aim: to find f of a convex lens.', 'Lens centre at 90.0 cm on the bench scale.', 'u = lens − candle,  v = screen − lens', '1/v + 1/u = 1/f  →  f = uv/(u + v)', 'Precaution: sharpest image, no parallax.'],
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Candle', get: function (r) { return r.c.toFixed(1); } },
        { label: 'Screen', get: function (r) { return r.s.toFixed(1); } }, { label: 'u (cm)', get: function (r) { return r.u.toFixed(1); } },
        { label: 'v (cm)', get: function (r) { return r.v.toFixed(1); } }, { label: 'f (cm)', get: function (r) { return (r.u * r.v / (r.u + r.v)).toFixed(2); } }] },
    graph: Object.defineProperties({ x: function (r) { return 100 / r.u; }, y: function (r) { return 100 / r.v; }, xlabel: '1/u (m⁻¹)', ylabel: '1/v (m⁻¹)', x0: 0, y0: 0,
      line: function (pts) { var L = S.fit.linear(pts); return L ? function (x) { return L.m * x + L.c; } : null; } }, {
      x1: { get: function () { var r = fMean(S.rows); return isFinite(r) ? 100 / r * 1.04 : 1; } }, y1: { get: function () { var r = fMean(S.rows); return isFinite(r) ? 100 / r * 1.04 : 1; } } }),
    result: function (rows) { var f = fMean(rows); if (!isFinite(f) || rows.length < 2) return null;
      return { label: 'f', value: f, unit: 'cm', digits: 1, truth: lensF() * 100, note: 'Mean of uv/(u + v). The straight line of 1/v against 1/u cuts each axis at 1/f.' }; },
    tol: 0.015,
    chips: ['Why is the image inverted?', 'How do I know the image is sharpest?', 'What happens when u is less than f?', 'Check my readings', 'Why is my f a little less than 20 cm?'],
    viva: [['Where must the candle be for an image the same size as the object?', ['At 2f', 'At f', 'Between f and the lens'], 0, 'At 2f the image also forms at 2f on the other side, inverted and the same size.'],
      ['If the lower half of the lens is covered, the image on the screen…', ['is complete but dimmer', 'loses its lower half', 'disappears'], 0, 'Every part of the lens forms the whole image; covering half only halves the light.']],
    askState: function () { var v = view || look(); return { lens_centre_at_cm: MIR, candle_at_cm: st.cPos, screen_at_cm: st.sPos, u_cm: +uCm().toFixed(1), v_screen_cm: +vCm().toFixed(1),
      candle_lit: st.lit, image_on_screen: sharpWord(v), image_sharpness_0_to_1: +v.sharp.toFixed(2), image_is_real: !!v.real, light_rays_shown: st.rays }; },

    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Set up the optical bench');
          u.p('The convex lens is clamped with its centre at the 90.0 cm mark. The candle stands on an upright on the left; the white screen is on the right, where the inverted image will fall.');
          u.task('1. Light the candle', st.lit, st.lit ? 'Lit. The flame is your bright object.' : 'Strike a match and bring it to the wick')
            .add(u.button(st.lit ? 'Candle lit' : 'Light the candle', function () { lightCandle(); }, !st.lit, st.lit || S.hand.busy));
          u.task('2. Check the heights', true, 'The flame, the centre of the lens and the screen are lined up along the bench')
            .add(u.button('Look along the bench', function () { S.focus('align'); }));
          u.note('Draw the curtains: a dim room makes the image on the screen much easier to see. Keep the matchbox and your notebook away from the flame.');
          u.next('Next: find the image', st.lit);
        },
        ok: function () { return st.lit; },
        auto: function () { return lightCandle(); } },
      { id: 'image', title: 'Find the image', view: 'screen', render: function (u) {
          u.h2('Find the sharp image, record u and v');
          u.p('Place the candle, then slide the screen towards or away from the lens until the flame’s image on it is sharpest. Read both index marks on the bench scale. Take at least 4 positions of the candle.');
          u.task('Candle (object)', true, 'At ' + st.cPos.toFixed(1) + ' cm → u = ' + uCm().toFixed(1) + ' cm');
          u.slider('Candle position', 3, MIR - 6, 0.5, function () { return st.cSet; }, function (x) { st.cSet = x; }, 'cm', 1);
          u.row(u.button('Move the candle there', function () { moveUpright('c', st.cSet); S.render(); }, true, S.hand.busy));
          u.task('Screen', true, 'At ' + st.sPos.toFixed(1) + ' cm → v = ' + vCm().toFixed(1) + ' cm');
          u.slider('Screen position', MIR + 4, LEN * 100 - 3, 0.1, function () { return st.sSet; }, function (x) { st.sSet = x; }, 'cm', 1);
          u.row(u.button('Slide the screen there', function () { moveUpright('s', st.sSet); S.render(); }, true, S.hand.busy));
          function nudge(d) { return function () { var to = Math.round((st.sPos + d) * 10) / 10; st.sSet = to; moveUpright('s', to); S.render(); }; }
          u.row(u.button('− 1 cm', nudge(-1), false, S.hand.busy), u.button('− 1 mm', nudge(-0.1), false, S.hand.busy), u.button('+ 1 mm', nudge(0.1), false, S.hand.busy), u.button('+ 1 cm', nudge(1), false, S.hand.busy));
          u.live(function () { var v = view || look(); return 'Image: ' + sharpWord(v); });
          u.row(u.button('Record u and v', function () { record(); }, true, S.hand.busy),
            u.button(st.rays ? 'Hide light rays' : 'Show light rays', function () { st.rays = !st.rays; update(); S.render(); }),
            u.button('Look at the screen', function () { update(); S.focus('screen'); }));
          u.note('Drag an upright with your mouse or finger to slide it yourself. If u is less than f no image forms on the screen at all: the image is virtual.');
          u.h3('Observation table'); u.table();
          u.next('Next: graph and result', S.rows.length >= 4);
          if (S.rows.length < 4) u.p(S.rows.length + ' of at least 4 positions recorded.');
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          return [45, 50, 60, 70, 80].reduce(function (pr, uu) { return pr.then(function () {
            st.cSet = MIR - uu; return moveUpright('c', MIR - uu).then(function () { st.sSet = bestScreen(); return moveUpright('s', st.sSet); }).then(function () { record(); }); }); }, Promise.resolve()); } },
    ],

    tick: function () { update(); },
  };

  function lensF() { var q = Object.assign({}, p); return K.view(null, q).f; }
  function fMean(rows) { var fs = (rows || []).filter(function (r) { return r.u > 0 && r.v > 0; }).map(function (r) { return r.u * r.v / (r.u + r.v); }); return fs.length ? S.fit.mean(fs) : NaN; }
});
