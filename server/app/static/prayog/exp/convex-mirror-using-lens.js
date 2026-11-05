/* Prayogshala studio rig `convex-mirror-using-lens`: ONE optical bench for the two set-ups of
   app/prayog/labs/engine_ug.py that put a second optical element in the beam of a convex lens:
     eng_lensmirror  a convex mirror: slid in the converging beam until the pin and its own image coincide;
     eng_twolens     a concave lens: its virtual object is the image the convex lens would have made.
   A lit pin (an illuminated arrow), a biconvex lens on the 50 cm mark, the second element on its own upright, and a
   white screen, all on a 180 cm optical bench; the gloved hand slides the uprights.
   Physics: the lab's own two-element ray tracer (packs/engine_ug.js), surface by surface with vector Snell and
   reflection - never the lens or mirror formula. The hidden knob (Rm or R2) is what the student finds. */
HoolaStudio.define('convex-mirror-using-lens', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KN = S.lab.kernel, K = HK.K[KN], MIRM = KN === 'eng_lensmirror';
  function labParams() {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(KN, o);
  }
  var p = labParams();
  var P0 = { u: p.u, a: p.a, scr: p.scr };
  p.h = 0.012;                                                  // the lit pin is 12 mm tall: its tip is the object point
  var X0 = -0.9, LEN = 1.8, BZ = -0.2, AXY = 0.24, MIR = 50;     // bench start x, length, z of the axis, axis height, lens mark (cm)
  var MX = X0 + MIR / 100;
  var RIM = Math.sqrt(Math.max(p.R * p.d - p.d * p.d / 4, 1e-8));
  var CARD_W = 0.11, CARD_H = 0.15, CARD_TOP = 0.03;
  var FCM = p.R / (2 * (p.n - 1)) * 100;                        // f of the convex lens (cm): only for choosing sensible positions
  var st = { lit: false, oPos: MIR - Math.round(P0.u * 1000) / 10, ePos: MIR + Math.round(P0.a * 1000) / 10, sPos: MIR + Math.round(P0.scr * 1000) / 10,
    in2: false, rays: false, vNow: null };
  st.oSet = st.oPos; st.eSet = st.ePos; st.sSet = st.sPos;
  function xAt(cm) { return X0 + cm / 100; }
  function sync() { p.u = Math.max(0.001, (MIR - st.oPos) / 100); p.a = (st.ePos - MIR) / 100; p.scr = Math.max(0.001, (st.sPos - MIR) / 100); p.mir = st.in2 ? 1 : 0; return p; }
  function fmt1(v) { return (Math.round(v * 10) / 10).toFixed(1); }
  var GAPTOL = 2.5;                                             // mm: how close the pin and its image must look to count as "no parallax"

  // ---------- the optical bench and its uprights
  var bench = S.opticalBench({ len: LEN, x0: X0, z: BZ, start: 0 });
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
    var sock = S.mesh(new T.CylinderGeometry(0.009, 0.0105, 0.022, 24), M.alu); sock.position.set(0, 0.063, 0); g.add(sock);
    var post = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, postTop - 0.07, 20), M.chrome); post.position.y = 0.07 + (postTop - 0.07) / 2; g.add(post);
    var sh = S.contact(0.075, 0.1, 0, BZ, 0.42, 0.04);
    g.setX = function (x, lift, z) { g.position.x = x; g.position.y = lift || 0; g.position.z = z === undefined ? BZ : z; sh.position.x = x; sh.position.z = g.position.z; sh.material.opacity = 0.42 * Math.max(0.15, 1 - (lift || 0) * 8); };
    g.userData.name = name; return g;
  }
  // ---------- the lit pin: an illuminated arrow whose tip is the object point
  var pinCar = carriage(AXY - 0.004, 'pin');
  var pinG = new T.Group(); pinG.position.y = AXY; pinCar.add(pinG);
  var base = S.mesh(new T.CylinderGeometry(0.014, 0.016, 0.006, 28), M.brass); base.position.y = -0.003; pinG.add(base);
  var litM = new T.MeshStandardMaterial({ color: 0xcfa24a, roughness: 0.4, emissive: 0x000000 });
  var stem = S.mesh(new T.CylinderGeometry(0.0016, 0.0016, p.h - 0.004, 10), litM); stem.position.y = (p.h - 0.004) / 2; pinG.add(stem);
  var tipc = S.mesh(new T.ConeGeometry(0.0034, 0.008, 14), litM); tipc.position.y = p.h - 0.004 + 0.004; pinG.add(tipc);
  var pinLamp = new T.PointLight(0xffd99a, 0, 0, 2); pinLamp.position.y = p.h * 0.6; pinG.add(pinLamp);
  var lampBox = S.rounded(0.05, 0.036, 0.04, 0.006, M.bakelite); lampBox.position.set(xAt(MIR - 22), 0.02, BZ + 0.16); S.scene.add(lampBox);
  var lampSw = S.mesh(new T.BoxGeometry(0.012, 0.007, 0.012), M.red); lampSw.position.set(xAt(MIR - 22), 0.043, BZ + 0.16); S.scene.add(lampSw);
  var lampLab = S.label('PIN LAMP', { w: 0.04, ratio: 0.2, color: '#e8e2cf' }); lampLab.rotation.x = -Math.PI / 2; lampLab.position.set(xAt(MIR - 22), 0.0405, BZ + 0.178); S.scene.add(lampLab);
  S.contact(0.1, 0.07, xAt(MIR - 22), BZ + 0.16, 0.45);
  // ---------- the convex lens on its upright, centre on the 50 cm mark
  var lensCar = carriage(AXY - RIM - 0.012, 'lens'); lensCar.setX(MX);
  var lensG = new T.Group(); lensG.position.set(0, AXY, 0); lensCar.add(lensG);
  function lathe(R, d, rim, flip) {
    var prof = [], NS = 24, rr, tt, li;
    for (li = 0; li <= NS; li++) { rr = rim * 0.995 * li / NS; tt = flip ? d / 2 + (R - Math.sqrt(R * R - rr * rr)) : Math.max(0.00025, d / 2 - (R - Math.sqrt(R * R - rr * rr))); prof.push(new T.Vector2(rr, -tt)); }
    for (li = NS; li >= 0; li--) { rr = rim * 0.995 * li / NS; tt = flip ? d / 2 + (R - Math.sqrt(R * R - rr * rr)) : Math.max(0.00025, d / 2 - (R - Math.sqrt(R * R - rr * rr))); prof.push(new T.Vector2(rr, tt)); }
    return new T.LatheGeometry(prof, 72);
  }
  var glassM = new T.MeshPhysicalMaterial({ color: 0xdcefff, roughness: 0.02, metalness: 0, transparent: true, opacity: 0.32, depthWrite: false, clearcoat: 1, clearcoatRoughness: 0.02, specularIntensity: 1, envMapIntensity: 1.7, side: T.DoubleSide });
  function lensMesh(geo, rim, name) {
    var g = new T.Group(); var face = new T.Mesh(geo, glassM); face.rotation.z = Math.PI / 2; face.renderOrder = 3; g.add(face);
    var ring = S.mesh(new T.TorusGeometry(rim + 0.0018, 0.0026, 12, 64), M.bakelite); ring.rotation.y = Math.PI / 2; g.add(ring);
    var ringB = S.mesh(new T.CylinderGeometry(rim + 0.0042, rim + 0.0042, 0.006, 64, 1, true), new T.MeshStandardMaterial({ color: 0x1b1c1f, roughness: 0.5, side: T.DoubleSide })); ringB.rotation.z = Math.PI / 2; g.add(ringB);
    var lug = S.mesh(new T.BoxGeometry(0.01, 0.012, 0.012), M.bakelite); lug.position.set(0, -rim - 0.009, 0); g.add(lug);
    var lb = S.label(name, { w: 0.03, ratio: 0.22, color: '#c8ccd2', weight: 700 }); lb.position.set(0, -rim - 0.009, 0.0062); g.add(lb);
    return g;
  }
  lensG.add(lensMesh(lathe(p.R, p.d, RIM, false), RIM, 'BICONVEX'));
  // ---------- the second element: a convex mirror or a concave lens, with its own upright
  var R2RIM = MIRM ? 0.03 : 0.024;
  var elCar = carriage(AXY - R2RIM - 0.012, MIRM ? 'mirror' : 'concave lens');
  var elG = new T.Group(); elG.position.set(0, AXY, 0); elCar.add(elG);
  if (MIRM) {
    var capAng = Math.asin(Math.min(0.95, R2RIM / p.Rm));
    var cap = new T.Mesh(new T.SphereGeometry(p.Rm, 64, 20, 0, Math.PI * 2, 0, capAng), new T.MeshStandardMaterial({ color: 0xe6e9ee, roughness: 0.03, metalness: 1, envMapIntensity: 1.8, side: T.DoubleSide }));
    cap.rotation.z = Math.PI / 2; cap.position.x = p.Rm; elG.add(cap);       // the pole at the upright, the centre of curvature behind it
    var back = S.mesh(new T.CylinderGeometry(R2RIM + 0.003, R2RIM + 0.003, 0.006, 48), M.black); back.rotation.z = Math.PI / 2; back.position.x = 0.0032; elG.add(back);
    var rimM = S.mesh(new T.TorusGeometry(R2RIM + 0.0012, 0.0016, 10, 48), M.chrome); rimM.rotation.y = Math.PI / 2; elG.add(rimM);
    var ml = S.label('CONVEX MIRROR', { w: 0.05, ratio: 0.14, color: '#c8ccd2', weight: 700 }); ml.position.set(0, -R2RIM - 0.01, 0.0075); elG.add(ml);
  } else {
    elG.add(lensMesh(lathe(p.R2, p.d2, R2RIM, true), R2RIM, 'BICONCAVE'));
  }
  // parking tray for the second element when it is out of the beam
  var PARK = new T.Vector3(MX + 0.28, 0, BZ + 0.2);
  var tray = S.rounded(0.1, 0.08, 0.012, 0.004, new T.MeshStandardMaterial({ color: 0xcdbd95, roughness: 0.8 })); tray.rotation.x = -Math.PI / 2; tray.position.set(PARK.x, 0.006, PARK.z); S.scene.add(tray);
  S.contact(0.14, 0.12, PARK.x, PARK.z, 0.45);
  // ---------- the white screen
  var scrCar = carriage(AXY + CARD_TOP - CARD_H - 0.002, 'screen');
  var screen = new T.Group(); screen.position.y = AXY; scrCar.add(screen);
  var card = S.mesh(new T.BoxGeometry(0.003, CARD_H, CARD_W), new T.MeshStandardMaterial({ color: 0xe2e0d8, roughness: 0.95 })); card.position.y = CARD_TOP - CARD_H / 2; screen.add(card);
  [[0, CARD_TOP - CARD_H - 0.002, 0, 0.008, 0.005, CARD_W + 0.006], [0, CARD_TOP + 0.001, 0, 0.006, 0.003, CARD_W + 0.006]].forEach(function (a) {
    var b = S.mesh(new T.BoxGeometry(a[3], a[4], a[5]), M.black); b.position.set(a[0], a[1], a[2]); screen.add(b); });
  var imgTex = S.liveTex(256, Math.round(256 * CARD_H / CARD_W)), PXM = 256 / CARD_W;
  var img = new T.Mesh(new T.PlaneGeometry(CARD_W, CARD_H), new T.MeshBasicMaterial({ map: imgTex, transparent: true, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending }));
  img.rotation.y = -Math.PI / 2; img.position.set(-0.0019, CARD_TOP - CARD_H / 2, 0); img.renderOrder = 4; screen.add(img);
  // ---------- the image of the pin that the mirror throws back (a ghost arrow in the air)
  var ghostM = new T.MeshStandardMaterial({ color: 0xff6a3a, roughness: 0.4, transparent: true, opacity: 0, emissive: 0x802a10, emissiveIntensity: 0.7, depthWrite: false });
  var ghost = new T.Group(); S.scene.add(ghost);
  var gstem = S.mesh(new T.CylinderGeometry(0.0013, 0.0013, 1, 8), ghostM, false, false); ghost.add(gstem);
  var gtip = S.mesh(new T.ConeGeometry(0.003, 0.007, 12), ghostM, false, false); ghost.add(gtip);
  // ---------- kernel rays
  var rayMat = new T.LineBasicMaterial({ color: 0xffc15a, transparent: true, opacity: 0.6, depthWrite: false, toneMapped: false });
  var rayLines = [];
  for (var ri = 0; ri < 4; ri++) { var ln = new T.Line(new T.BufferGeometry(), rayMat); ln.visible = false; ln.renderOrder = 7; S.scene.add(ln); rayLines.push(ln); }

  S.addApparatus('bench', bench, 'Optical bench', 'A rigid iron bed, 180 cm long, with a centimetre scale (least count 1 mm). Each upright has an index mark that you read on the scale.');
  S.addApparatus('pin', pinCar, MIRM ? 'Lit pin' : 'Lit pin (the object)', 'A pin lit by its own lamp, 12 mm tall. Its tip is the object. It stands on the left of the lens.');
  S.addApparatus('lens', lensCar, 'Convex lens', 'A thin biconvex ' + (p.n > 1.55 ? 'flint' : 'crown') + ' glass lens (n = ' + (+p.n.toFixed(4)) + ', both faces R = ' + (+(p.R * 100).toFixed(2)) + ' cm), clamped with its centre exactly at the 50.0 cm mark.');
  S.addApparatus('elem', elCar, MIRM ? 'Convex mirror' : 'Concave lens', MIRM ? 'A small convex mirror on its own upright, silvered on the front. Its radius of curvature is what you find. It goes between the lens and the image.' : 'A biconcave lens on its own upright. Its focal length is what you find. It goes between the convex lens and its image.');
  S.addApparatus('screen', scrCar, 'White screen', 'A white card for catching a real image.');
  S.addApparatus('lamp', lampBox, 'Pin lamp', 'The switch lights the pin. Draw the curtains for a better view of the image.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudO = S.hudCard('Pin at'), hudE = S.hudCard(MIRM ? 'Mirror at' : 'Concave lens at'), hudS = S.hudCard(MIRM ? 'Screen / pin and image' : 'Screen at');

  // ---------- physics from the kernel
  var view = null, lastKey = '';
  function look() { sync(); view = K.view(null, p); return view; }
  function gapMm() { sync(); var q = assign(p, { h: 0.002 }); return K.view(null, q).coin * 1000; }
  function sharpWord(v) { if (!st.lit) return 'Pin not lit'; if (!v.real) return 'No real image'; var s = v.sharp; return s > 0.85 ? 'Sharp' : s > 0.45 ? 'Nearly sharp' : s > 0.12 ? 'Blurred' : 'Very blurred'; }
  function hudWord(v) { return MIRM && st.in2 ? (v.real ? (Math.abs(gapMm()) <= GAPTOL ? 'together: no parallax' : 'image ' + fmt1(Math.abs(gapMm())) + ' mm ' + (gapMm() > 0 ? 'behind' : 'in front of') + ' the pin') : 'no real image') : sharpWord(v); }
  function drawImage(v) {
    var onScr = !(MIRM && st.in2);
    var real = st.lit && onScr && v.real && v.img_x > 0, mag = real ? (v.img_y / p.h) : 0;
    var blurM = real ? 0.004 * Math.sqrt(Math.max(0, 1 / Math.max(v.sharp, 1e-6) - 1)) : 0;
    var key = [st.lit ? 1 : 0, real ? 1 : 0, mag.toFixed(3), Math.min(blurM, 0.2).toFixed(4)].join('|');
    if (key === lastKey) return; lastKey = key;
    imgTex.draw(function (x, w, h) {
      x.clearRect(0, 0, w, h); if (!real) return;
      var ax = CARD_TOP * PXM, cx = w / 2, sig = Math.min(80, blurM * PXM * 0.5), hh = Math.abs(v.img_y) * PXM, dir = v.img_y < 0 ? 1 : -1;
      x.save(); if (sig > 0.4) x.filter = 'blur(' + sig.toFixed(1) + 'px)';
      x.globalAlpha = Math.max(0.08, Math.min(1, 0.95 / (1 + sig * 0.05)));
      x.strokeStyle = 'rgba(255,214,120,1)'; x.lineWidth = Math.max(2.5, 0.0032 * PXM); x.beginPath(); x.moveTo(cx, ax); x.lineTo(cx, ax + dir * hh); x.stroke();
      x.fillStyle = 'rgba(255,236,170,1)'; x.beginPath(); x.arc(cx, ax + dir * hh, Math.max(4, 0.0034 * PXM), 0, Math.PI * 2); x.fill();
      x.restore();
    });
  }
  function drawRays(v) {
    rayLines.forEach(function (l) { l.visible = false; });
    if (!st.rays || !st.lit) return;
    var n = 0, lo = X0 - MX + 0.02, hi = X0 + LEN - MX - 0.02;
    (v.rays || []).forEach(function (r) {
      if (n >= rayLines.length) return; var pts = r.p.map(function (q) { return [q[0], q[1]]; }), L = pts.length - 1, a = pts[L - 1], b = pts[L], dx = b[0] - a[0], t;
      if (Math.abs(dx) > 1e-9) { var bound = dx > 0 ? hi : lo; t = (bound - a[0]) / dx; if (t < 1) pts[L] = [a[0] + t * dx, a[1] + t * (b[1] - a[1])]; }
      var l = rayLines[n++];
      l.geometry.setFromPoints(pts.map(function (q) { return new T.Vector3(MX + q[0], AXY + q[1], BZ + 0.0005); })); l.visible = true; });
  }
  function layout() {
    pinCar.setX(xAt(st.oPos), 0, BZ);
    if (st.in2) elCar.setX(xAt(st.ePos), 0, BZ); else elCar.setX(PARK.x, 0.012, PARK.z);
    elCar.rotation.y = st.in2 ? 0 : 1.2;
    scrCar.setX(xAt(st.sPos), 0, BZ);
  }
  function update() {
    layout();
    var v = look(); drawImage(v); drawRays(v);
    var showG = MIRM && st.in2 && st.lit && v.real > 0.5 && Math.abs(v.coin) < 0.1;
    ghostM.opacity = showG ? 0.7 : 0;
    if (showG) { var hgt = Math.max(0.004, Math.abs(v.img_y)); gstem.scale.y = hgt; gstem.position.y = (v.img_y < 0 ? -hgt / 2 : hgt / 2); gtip.position.y = v.img_y < 0 ? -hgt - 0.0035 : hgt + 0.0035; gtip.rotation.z = v.img_y < 0 ? Math.PI : 0;
      ghost.position.set(MX + v.img_x, AXY, BZ); }
    var f = 1 + 0.04 * Math.sin(performance.now() / 90);
    litM.emissive.setRGB(st.lit ? 1.0 * f : 0, st.lit ? 0.72 * f : 0, st.lit ? 0.3 * f : 0); pinLamp.intensity = st.lit ? 0.02 : 0;
    VIEWS.screen[0][0] = xAt(st.sPos) - 0.26; VIEWS.screen[0][1] = AXY + 0.03; VIEWS.screen[0][2] = BZ + 0.3; VIEWS.screen[1][0] = xAt(st.sPos); VIEWS.screen[1][1] = AXY - 0.04; VIEWS.screen[1][2] = BZ;
    VIEWS.pin[0][0] = xAt(st.oPos) + 0.14; VIEWS.pin[1][0] = xAt(st.oPos);
    VIEWS.elem[0][0] = xAt(st.in2 ? st.ePos : MIR + 8) + 0.14; VIEWS.elem[1][0] = xAt(st.in2 ? st.ePos : MIR + 8);
    hudO.set(fmt1(st.oPos) + ' cm'); hudE.set(st.in2 ? fmt1(st.ePos) + ' cm' : 'out of the beam'); hudS.set(hudWord(v));
  }

  // ---------- human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function lightPin() {
    if (st.lit) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    return S.hand.tap(lampSw, 'top').then(function () { st.lit = true; update(); S.say('The pin is lit.'); S.render(); return true; });
  }
  var LIM = { o: [3, MIR - 1.3 * FCM], s: [MIR + 3, LEN * 100 - 3] };
  function moveUpright(which, toCm) {
    if (S.hand.busy) return wait();
    var car = which === 'o' ? pinCar : which === 'e' ? elCar : scrCar, from = which === 'o' ? st.oPos : which === 'e' ? st.ePos : st.sPos;
    var lo = which === 'o' ? LIM.o[0] : which === 'e' ? MIR + 3 : Math.max(LIM.s[0], st.in2 ? st.ePos + 3 : 0), hi = which === 'o' ? LIM.o[1] : which === 'e' ? Math.min(LEN * 100 - 6, st.sPos - 3) : LIM.s[1];
    toCm = Math.round(toCm * 20) / 20;
    if (which === 'e' && !st.in2) { S.say('Put it on the bench first.'); return Promise.resolve(false); }
    if (!(toCm >= lo - 1e-9 && toCm <= hi + 1e-9)) { S.say('This upright can go from ' + fmt1(lo) + ' cm to ' + fmt1(hi) + ' cm here.'); return Promise.resolve(false); }
    if (Math.abs(toCm - from) < 0.02) return Promise.resolve(true);
    var grabY = which === 'o' ? AXY - 0.07 : 0.072;
    function at(k) { return from + (toCm - from) * k; }
    return S.hand.pinchMove(new T.Vector3(xAt(from) + 0.006, grabY, BZ), function (k) { return new T.Vector3(xAt(at(k)) + 0.006, grabY, BZ); },
      function (k) { if (which === 'o') st.oPos = at(k); else if (which === 'e') st.ePos = at(k); else st.sPos = at(k); update(); },
      { ms: Math.min(1800, 450 + Math.abs(toCm - from) * 30), reachMs: 600, hold: 120 }).then(function () {
      if (which === 'o') st.oPos = toCm; else if (which === 'e') st.ePos = toCm; else st.sPos = toCm; update(); S.render(); return true; });
  }
  function putElement(atCm) {
    if (S.hand.busy) return wait();
    if (st.in2) return Promise.resolve(true);
    atCm = Math.max(MIR + 3, Math.min(Math.min(LEN * 100 - 6, st.sPos - 3), atCm));
    var start = new T.Vector3(PARK.x, 0.07, PARK.z), end = new T.Vector3(xAt(atCm), 0.07, BZ);
    function path(k) { var q = new T.Vector3().lerpVectors(start, end, k); q.y += 0.12 * Math.sin(Math.PI * k); return q; }
    return S.hand.pinchMove(start, path, function (k) { var q = path(k); st.in2 = k >= 0.999; elCar.setX(q.x, Math.max(0, q.y - 0.07), PARK.z + (BZ - PARK.z) * k); elCar.rotation.y = 1.2 * (1 - k); }, { ms: 1400, reachMs: 600 }).then(function () {
      st.in2 = true; st.ePos = atCm; st.eSet = atCm; update(); S.say((MIRM ? 'The convex mirror' : 'The concave lens') + ' is in the beam at ' + fmt1(atCm) + ' cm.'); S.render(); return true; });
  }
  function takeElement() {
    if (S.hand.busy) return wait();
    if (!st.in2) return Promise.resolve(true);
    var start = new T.Vector3(xAt(st.ePos), 0.07, BZ), end = new T.Vector3(PARK.x, 0.07, PARK.z);
    function path(k) { var q = new T.Vector3().lerpVectors(start, end, k); q.y += 0.12 * Math.sin(Math.PI * k); return q; }
    return S.hand.pinchMove(start, path, function (k) { var q = path(k); st.in2 = k < 0.001; if (k > 0.001) { elCar.setX(q.x, Math.max(0, q.y - 0.07), BZ + (PARK.z - BZ) * k); elCar.rotation.y = 1.2 * k; } }, { ms: 1400, reachMs: 600 }).then(function () {
      st.in2 = false; update(); S.say((MIRM ? 'The mirror' : 'The concave lens') + ' is back on its tray.'); S.render(); return true; });
  }
  function noteV() {                                              // the image by the convex lens alone
    if (S.hand.busy) { wait(); return false; }
    if (!st.lit) { S.say('Light the pin first.'); return false; }
    if (st.in2) { S.say('Take the ' + (MIRM ? 'mirror' : 'concave lens') + ' out of the beam first: this reading is for the convex lens alone.'); return false; }
    var v = look();
    if (!v.real || v.img_x <= 0) { S.say('No real image forms: the pin is inside the focus of the lens. Move it further away.'); return false; }
    if (v.sharp < 0.5) { S.say('The image on the screen is still blurred. Move the screen in small steps until the pin looks sharpest.'); return false; }
    st.vNow = { u: Math.round((MIR - st.oPos) * 10) / 10, v: Math.round((st.sPos - MIR) * 10) / 10 };
    S.say('v = ' + fmt1(st.vNow.v) + ' cm for u = ' + fmt1(st.vNow.u) + ' cm.'); S.render(); return true;
  }
  function recordRow() {
    if (S.hand.busy) { wait(); return false; }
    if (!st.lit) { S.say('Light the pin first.'); return false; }
    if (!st.vNow) { S.say('Find v for the convex lens alone first (without the ' + (MIRM ? 'mirror' : 'concave lens') + ').'); return false; }
    if (!st.in2) { S.say('Put the ' + (MIRM ? 'mirror' : 'concave lens') + ' in the beam first.'); return false; }
    var u = Math.round((MIR - st.oPos) * 10) / 10;
    if (Math.abs(st.vNow.u - u) > 0.05) { S.say('The pin has moved since you found v. Take the ' + (MIRM ? 'mirror' : 'lens') + ' out and find v again for this position.'); return false; }
    var v = look();
    if (MIRM) {
      if (!v.real) { S.say('No image comes back to the pin. Move the mirror a little.'); return false; }
      if (Math.abs(gapMm()) > GAPTOL) { S.say('The pin and its image are not together yet. Slide the mirror until there is no parallax: the image should stay on the pin as you move your head.'); return false; }
      if (S.rows.some(function (r) { return Math.abs(r.u - u) < 1; })) { S.say('You already have a reading near u = ' + fmt1(u) + ' cm. Move the pin to a new position.'); return false; }
      S.addRow({ u: u / 100, v: st.vNow.v / 100, a: (st.ePos - MIR) / 100 });
      S.say('Written: u = ' + fmt1(u) + ' cm, v = ' + fmt1(st.vNow.v) + ' cm, mirror at a = ' + fmt1(st.ePos - MIR) + ' cm.'); return true;
    }
    if (!v.real) { S.say('No real image forms on the screen now. Slide the screen until you find one, or move the concave lens nearer the convex lens.'); return false; }
    if (v.sharp < 0.5) { S.say('The image on the screen is still blurred. Slide the screen in small steps until it is sharp.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.a - (st.ePos - MIR) / 100) < 0.01 && Math.abs(r.u - u / 100) < 0.01; })) { S.say('You already have that position. Move the concave lens or the pin.'); return false; }
    S.addRow({ u: u / 100, v1: st.vNow.v / 100, a: (st.ePos - MIR) / 100, xi: (st.sPos - MIR) / 100 });
    S.say('Written: v1 = ' + fmt1(st.vNow.v) + ' cm, concave lens at ' + fmt1(st.ePos - MIR) + ' cm, final image at ' + fmt1(st.sPos - MIR) + ' cm.'); return true;
  }
  // what a careful student converges to
  function bestScreen() {
    sync(); var keep = st.sPos, best = keep, bs = -1, c, s;
    for (c = MIR + 3; c <= LEN * 100 - 3; c += 0.5) { st.sPos = c; s = look().sharp; if (s > bs) { bs = s; best = c; } }
    var lo = best - 0.5, hi = best + 0.5; bs = -1; var b2 = best;
    for (c = lo; c <= hi + 1e-9; c += 0.05) { st.sPos = c; s = look().sharp; if (s > bs) { bs = s; b2 = c; } }
    st.sPos = keep; return Math.round(b2 * 20) / 20;
  }
  function bestMirror() {                                         // the first sign change of the parallax as the mirror comes in
    var keep = st.ePos, c, prev = null, pg = null, g, a, b, i, m, gm;
    for (c = MIR + 3; c <= st.sPos - 3; c += 0.5) { st.ePos = c; g = gapMm(); if (pg !== null && (g > 0) !== (pg > 0) && Math.abs(g) < 60 && Math.abs(pg) < 60) { a = prev; b = c; break; } prev = c; pg = g; }
    if (a === undefined) { st.ePos = keep; return keep; }
    st.ePos = a; var ga = gapMm();
    for (i = 0; i < 30; i++) { m = (a + b) / 2; st.ePos = m; gm = gapMm(); if ((gm > 0) === (ga > 0)) { a = m; ga = gm; } else b = m; }
    st.ePos = keep; return Math.round((a + b) / 2 * 20) / 20;
  }
  function autoU() {                                              // pin distances a careful student picks beyond 1.5 f (the image comes out well on the bench)
    if (MIRM) {
      var us = [], mult = [1.8, 2.1, 2.4], v, q = assign(p, { h: 0.002, mir: 0 }), k;
      for (k = 0; k < mult.length; k++) us.push(Math.round(mult[k] * FCM * 2) / 2);
      return us;
    }
    return [1.8, 2.1, 2.4].map(function (m) { return Math.round(m * FCM * 2) / 2; });
  }
  function trialA(u) {
    return (st.in2 ? takeElement() : Promise.resolve()).then(function () { st.oSet = MIR - u; return moveUpright('o', MIR - u); }).then(function () {
      st.in2 = false; var s = bestScreen(); st.sSet = s; return moveUpright('s', s); }).then(function () { noteV(); var a0 = Math.max(MIR + 4, st.sPos - 0.4 * (st.sPos - MIR)); return putElement(a0); }).then(function () {
      st.in2 = true; var a = bestMirror(); st.eSet = a; return moveUpright('e', a); }).then(function () { recordRow(); });
  }
  function trialB(u, d) {
    return (st.in2 ? takeElement() : Promise.resolve()).then(function () { st.oSet = MIR - u; return moveUpright('o', MIR - u); }).then(function () {
      st.in2 = false; var s = bestScreen(); st.sSet = s; return moveUpright('s', s); }).then(function () { noteV(); var a = Math.round((st.sPos - d) * 20) / 20; return putElement(a); }).then(function () {
      st.in2 = true; var s2 = bestScreen(); st.sSet = s2; return moveUpright('s', s2); }).then(function () { recordRow(); });
  }

  var VIEWS = { bench: [[-0.05, 0.74, 1.72], [-0.05, 0.12, -0.2]], lens: [[MX + 0.1, AXY + 0.03, BZ + 0.16], [MX, AXY - 0.005, BZ]],
    pin: [[0, AXY + 0.06, BZ + 0.22], [0, AXY, BZ]], elem: [[0, AXY + 0.05, BZ + 0.2], [0, AXY, BZ]], screen: [[0, AXY, BZ + 0.21], [0, AXY - 0.05, BZ]],
    lamp: [[xAt(MIR - 22) + 0.1, 0.14, BZ + 0.36], [xAt(MIR - 22), 0.03, BZ + 0.16]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] };
  VIEWS.mirror = VIEWS.elem; VIEWS.align = [[X0 - 0.1, AXY + 0.05, BZ + 0.03], [MX, AXY - 0.02, BZ]];
  update();

  function fOf(rows) {
    if (MIRM) { var fs = (rows || []).filter(function (r) { return r.v > r.a; }).map(function (r) { return (r.v - r.a) / 2; }); return fs.length ? S.fit.mean(fs) : NaN; }
    var gs = (rows || []).map(function (r) { var u2 = r.v1 - r.a, v2 = r.xi - r.a; return Math.abs(u2 - v2) > 1e-9 ? u2 * v2 / (u2 - v2) : NaN; }).filter(function (x) { return isFinite(x); });
    return gs.length ? S.fit.mean(gs) : NaN;
  }
  var TRUTH = MIRM ? p.Rm / 2 : -p.R2 / (2 * (p.n2 - 1));

  return {
    camera: { pos: [-0.04, 0.72, 1.62], look: [-0.04, 0.12, -0.2] },
    views: VIEWS,
    theory: MIRM ? { principle: 'A convex mirror cannot make a real image of a real object, so its focal length is found with the help of a convex lens. The lens makes a real image I of the pin. A convex mirror placed in the converging beam, in front of I, reflects the rays. When they are aimed at the mirror’s centre of curvature they strike it along a radius and return on their own path, so the pin and its image coincide.',
        formula: 'R = v − a,   f = R / 2', formulaNote: 'v = distance of the lens’s own image I from the lens · a = distance of the mirror from the lens · the centre of curvature of the mirror is at I',
        more: ['The lens has n = ' + (+p.n.toFixed(4)) + ' and faces of R = ' + (+(p.R * 100).toFixed(2)) + ' cm, so f of the lens is about ' + fmt1(FCM) + ' cm. Put the pin well beyond f, so that I is a clear distance in front of the mirror’s position.'],
        precautions: 'Keep the pin, the centre of the lens and the centre of the mirror at the same height on one line along the bench. Look for parallax with your eye a little above the line of the pin and its image. Read each upright at its index mark with your eye straight above it.' }
      : { principle: 'The convex lens alone would form a real image I of the pin, a distance v1 from it. The concave lens, placed in the beam before I, receives converging light: for it, I is a virtual object at u2 = v1 − a on the far side. It makes a real image further out, at v2. Both distances are positive on the side the light is going to, and f2 comes out negative.',
        formula: '1/v2 − 1/u2 = 1/f2', formulaNote: 'u2 = v1 − a  (virtual object) · v2 = distance of the final image from the concave lens · f2 = u2 v2 / (u2 − v2)',
        more: ['The concave lens must be placed closer to the convex lens than I, and u2 must be less than the focal length of the concave lens, or no real image forms.'],
        precautions: 'Keep the pin, both lenses and the screen at the same height on one line along the bench. Find the sharpest image by moving the screen both ways in small steps. Read each upright at its index mark with your eye straight above it.' },
    book: MIRM ? { title: 'Expt. — Convex mirror using a convex lens', lines: ['Aim: to find f of a convex mirror.', 'Lens centre at 50.0 cm on the bench scale.', 'v = image by the lens alone,  a = mirror distance', 'R = v − a,  f = R / 2', 'Precaution: no parallax between the pin and its image.'],
        columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'u (cm)', get: function (r) { return (r.u * 100).toFixed(1); } }, { label: 'v (cm)', get: function (r) { return (r.v * 100).toFixed(1); } },
          { label: 'a (cm)', get: function (r) { return (r.a * 100).toFixed(1); } }, { label: 'R = v − a (cm)', get: function (r) { return ((r.v - r.a) * 100).toFixed(1); } }, { label: 'f (cm)', get: function (r) { return ((r.v - r.a) * 50).toFixed(1); } }] }
      : { title: 'Expt. — Concave lens using a convex lens', lines: ['Aim: to find f of a concave lens.', 'Convex lens centre at 50.0 cm on the bench scale.', 'u2 = v1 − a  (virtual object),  v2 = final image − a', 'f2 = u2 v2 / (u2 − v2)', 'Precaution: sharpest image on the screen.'],
        columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'v1 (cm)', get: function (r) { return (r.v1 * 100).toFixed(1); } }, { label: 'a (cm)', get: function (r) { return (r.a * 100).toFixed(1); } },
          { label: 'v2 (cm)', get: function (r) { return ((r.xi - r.a) * 100).toFixed(1); } }, { label: 'f2 (cm)', get: function (r) { var u2 = r.v1 - r.a, v2 = r.xi - r.a; return (u2 * v2 / (u2 - v2) * 100).toFixed(1); } }] },
    graph: null,
    result: function (rows) { var f = fOf(rows); if (!isFinite(f) || (rows || []).length < 3) return null;
      return { label: MIRM ? 'f of the convex mirror' : 'f of the concave lens', value: f * 100, unit: 'cm', digits: 1, truth: TRUTH * 100, note: MIRM ? 'Mean of (v − a) / 2 over ' + rows.length + ' positions of the pin.' : 'Mean of u2 v2 / (u2 − v2) over ' + rows.length + ' positions; the negative sign means the lens is diverging.' }; },
    tol: MIRM ? 0.02 : 0.03,
    chips: MIRM ? ['Why is the lens needed?', 'What is parallax?', 'Why do the rays strike the mirror along its radius?', 'Check my readings'] : ['What is a virtual object?', 'Why does the screen have to move out?', 'Why is f negative?', 'Check my readings'],
    viva: MIRM ? [['At the position where the pin and its image coincide, the rays strike the mirror', ['along the radius, normally', 'at 45 degrees', 'parallel to the axis'], 0, 'Only rays along a radius retrace their path, so the image falls on the object.'],
        ['Why can a convex mirror not be used alone to find its focal length?', ['Its image of a real object is always virtual', 'It has no focus', 'It is too small'], 0, 'A real object always gives a virtual, diminished image behind a convex mirror.']]
      : [['The concave lens must be placed', ['between the convex lens and its image', 'beyond the image', 'in front of the pin'], 0, 'Only then does it receive the converging beam, making a virtual object.'],
        ['With the concave lens in, the image on the screen is', ['further from the lens than before', 'nearer than before', 'the same'], 0, 'A diverging lens reduces the convergence, so the rays meet later.']],
    askState: function () { var v = view || look(); return { pin_lit: st.lit, pin_at_cm: st.oPos, u_cm: +(MIR - st.oPos).toFixed(1), screen_at_cm: st.sPos, second_element_in_beam: st.in2, second_element_at_cm: st.in2 ? st.ePos : null,
      image_on_screen: sharpWord(v), v_noted_cm: st.vNow ? st.vNow.v : null, parallax_mm: MIRM && st.in2 ? +gapMm().toFixed(1) : null, readings_recorded: S.rows.length }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Set up the optical bench');
          u.p('The convex lens is clamped with its centre at the 50.0 cm mark. The pin stands on an upright on its left, the white screen on its right. The ' + (MIRM ? 'convex mirror' : 'concave lens') + ' waits on its tray at the front of the bench.');
          u.task('1. Light the pin', st.lit, st.lit ? 'Lit.' : 'The hand presses the lamp switch').add(u.button(st.lit ? 'Pin lit' : 'Light the pin', function () { S.focus('lamp'); lightPin(); }, !st.lit, st.lit || S.hand.busy));
          u.task('2. Check the heights', true, 'The tip of the pin, the centre of the lens and the screen are lined up along the bench').add(u.button('Look along the bench', function () { S.focus('align'); }));
          u.note('Draw the curtains: a dim room makes the image easier to see. Keep loose paper and the pin lamp’s lead away from the bench edge.');
          u.next('Next: take the readings', st.lit);
        },
        ok: function () { return st.lit; }, auto: function () { return lightPin(); } },
      { id: 'measure', title: MIRM ? 'Find f of the mirror' : 'Find f of the concave lens', view: 'screen', render: function (u) {
          u.h2(MIRM ? 'Find v, then slide the mirror until the pin and its image coincide' : 'Find v1, then put the concave lens in and find the new image');
          u.p(MIRM ? 'For each position of the pin: (1) with the mirror out, slide the screen until the image of the pin is sharp and note v; (2) put the mirror in front of that image and slide it until the pin and its own image are together with no parallax; (3) record. Take at least 3 positions of the pin.'
            : 'For each position of the pin: (1) with the concave lens out, slide the screen until the image is sharp and note v1; (2) put the concave lens between the convex lens and that image, then slide the screen out until the new image is sharp; (3) record. Take at least 3 positions.');
          var hi = LIM.o[1], lo = Math.max(3, MIR - 4.5 * FCM);
          u.task('Pin (object)', true, 'At ' + fmt1(st.oPos) + ' cm → u = ' + fmt1(MIR - st.oPos) + ' cm').add(u.slider('Pin position', lo, hi, 0.5, function () { return st.oSet; }, function (x) { st.oSet = x; }, 'cm', 1));
          u.row(u.button('Move the pin there', function () { st.in2 && S.say('Take the ' + (MIRM ? 'mirror' : 'concave lens') + ' out first, then move the pin.'); if (!st.in2) { st.vNow = null; moveUpright('o', st.oSet).then(function () { S.render(); }); } }, true, S.hand.busy));
          u.task('Screen', true, 'At ' + fmt1(st.sPos) + ' cm → ' + (st.in2 && !MIRM ? 'image at ' : 'v = ') + fmt1(st.sPos - MIR) + ' cm').add(u.slider('Screen position', MIR + 3, LEN * 100 - 3, 0.05, function () { return st.sSet; }, function (x) { st.sSet = x; }, 'cm', 2));
          u.row(u.button('Slide the screen there', function () { moveUpright('s', st.sSet).then(function () { S.render(); }); }, true, S.hand.busy));
          function nudge(d) { return function () { var to = Math.round((st.sPos + d) * 20) / 20; st.sSet = to; moveUpright('s', to).then(function () { S.render(); }); }; }
          u.row(u.button('− 1 cm', nudge(-1), false, S.hand.busy), u.button('− 1 mm', nudge(-0.1), false, S.hand.busy), u.button('+ 1 mm', nudge(0.1), false, S.hand.busy), u.button('+ 1 cm', nudge(1), false, S.hand.busy));
          u.row(u.button(MIRM ? 'Note v (mirror out)' : 'Note v1 (lens out)', function () { noteV(); S.render(); }, !st.vNow, S.hand.busy));
          u.task(MIRM ? 'Convex mirror' : 'Concave lens', st.in2, st.in2 ? 'In the beam at ' + fmt1(st.ePos) + ' cm → a = ' + fmt1(st.ePos - MIR) + ' cm' : 'On its tray')
            .add(u.button(st.in2 ? 'Take it out' : 'Put it in the beam', function () { S.focus('elem'); (st.in2 ? takeElement() : putElement(MIRM ? MIR + 8 : MIR + 13)).then(function () { S.render(); }); }, !st.in2, S.hand.busy));
          if (st.in2) {
            u.slider(MIRM ? 'Mirror position' : 'Concave lens position', MIR + 3, Math.min(LEN * 100 - 6, st.sPos - 3), 0.05, function () { return st.eSet; }, function (x) { st.eSet = x; }, 'cm', 2);
            u.row(u.button('Slide it there', function () { moveUpright('e', st.eSet).then(function () { S.render(); }); }, true, S.hand.busy));
            function nudgeE(d) { return function () { var to = Math.round((st.ePos + d) * 20) / 20; st.eSet = to; moveUpright('e', to).then(function () { S.render(); }); }; }
            u.row(u.button('− 1 cm', nudgeE(-1), false, S.hand.busy), u.button('− 1 mm', nudgeE(-0.1), false, S.hand.busy), u.button('+ 1 mm', nudgeE(0.1), false, S.hand.busy), u.button('+ 1 cm', nudgeE(1), false, S.hand.busy));
          }
          u.live(function () { var v = view || look(); return hudWord(v); });
          u.row(u.button('Record the row', function () { recordRow(); S.render(); }, true, S.hand.busy), u.button(st.rays ? 'Hide light rays' : 'Show light rays', function () { st.rays = !st.rays; update(); S.render(); }),
            u.button('Look at the screen', function () { update(); S.focus('screen'); }));
          u.h3('Observation table'); u.table();
          u.next('Next: result', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 positions recorded.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          var us = autoU(), seq = Promise.resolve();
          us.forEach(function (uu, i) { seq = seq.then(function () { return MIRM ? trialA(uu) : trialB(uu, [0.095, 0.115, 0.135][i % 3] * 100); }); });
          return seq;
        } },
    ],
    tick: function () { update(); },
  };
});
