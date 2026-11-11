/* Prayogshala studio rig `liquid-lens-plane-mirror`: the refractive index of a liquid by the no-parallax pin method,
   for the two set-ups of app/prayog/labs/engine_ug.py that put a layer of liquid on a mirror:
     mode 0  a convex lens lying on a plane mirror, a film of liquid between them (a plano-concave liquid lens);
     mode 1  a concave mirror with liquid poured in.
   A retort stand holds a pin point-down in a clamp that slides on the rod; the pin is moved until the pin tip and its
   own image tip coincide. Physics: the lab's own kernel (eng_liquid in packs/engine_ug.js), a surface-by-surface ray
   trace through the lens, the liquid and the mirror, never the lens formula. The hidden knob nl (the liquid's index)
   is what the student finds. */
HoolaStudio.define('liquid-lens-plane-mirror', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign, K = HK.K.eng_liquid;
  function labParams() {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor('eng_liquid', o);
  }
  var p = labParams();
  p.h = 0.004;                                                  // the pin's tip stands 4 mm off the axis
  var MODE = Math.round(p.mode);
  var VAR = S.lab.variant || {}, LIQUID = String(VAR.sample || '').replace(/^.*?:\s*/, '') || 'the liquid';
  var HMIN = 0.08, HMAX = 0.40;
  var AX = 0.0, AZ = -0.1;                                      // the axis of the lens or the mirror
  var st = { H: MODE === 0 ? 0.20 : 0.34, Hset: MODE === 0 ? 20 : 34, liq: false, dry: null, wet: null, rays: false, view: null };
  function sync() { p.H = st.H; p.liq = st.liq ? 1 : 0; return p; }

  // ---------- the base: wooden block, plane mirror or concave mirror
  var YREF, YM;
  var block = S.rounded(0.2, 0.2, 0.02, 0.006, M.darkWood); block.rotation.x = -Math.PI / 2; block.position.set(AX, 0.01, AZ); S.scene.add(block);
  S.contact(0.26, 0.26, AX, AZ, 0.5);
  var base = new T.Group(); S.scene.add(base);
  var filmMesh = null, lensMesh = null, mirrorMesh = null;
  if (MODE === 0) {
    YM = 0.024;
    var plate = S.rounded(0.13, 0.13, 0.004, 0.003, M.chrome); plate.rotation.x = -Math.PI / 2; plate.position.set(AX, YM - 0.002, AZ); base.add(plate);
    YREF = YM + p.d / 2;                                        // the lens centre
    var RIM = Math.sqrt(Math.max(p.R * p.d - p.d * p.d / 4, 1e-8)) * 0.96;
    var prof = [], NS = 22, i, rr, tt;
    for (i = 0; i <= NS; i++) { rr = RIM * i / NS; tt = Math.max(0.0001, p.d / 2 - (p.R - Math.sqrt(p.R * p.R - rr * rr))); prof.push(new T.Vector2(rr, -tt)); }
    for (i = NS; i >= 0; i--) { rr = RIM * i / NS; tt = Math.max(0.0001, p.d / 2 - (p.R - Math.sqrt(p.R * p.R - rr * rr))); prof.push(new T.Vector2(rr, tt)); }
    lensMesh = new T.Mesh(new T.LatheGeometry(prof, 64), new T.MeshPhysicalMaterial({ color: 0xdcefff, roughness: 0.02, transparent: true, opacity: 0.4, depthWrite: false, clearcoat: 1, side: T.DoubleSide }));
    lensMesh.position.set(AX, YREF, AZ); lensMesh.renderOrder = 3; S.scene.add(lensMesh);
    var ring = S.mesh(new T.TorusGeometry(RIM + 0.0012, 0.0016, 10, 48), M.bakelite); ring.rotation.x = Math.PI / 2; ring.position.set(AX, YREF, AZ); S.scene.add(ring);
    var fp = [new T.Vector2(0, 0)]; for (i = 0; i <= NS; i++) { rr = RIM * 0.98 * i / NS; fp.push(new T.Vector2(rr, p.R - Math.sqrt(p.R * p.R - rr * rr))); } fp.push(new T.Vector2(0, 0));
    // the film: the wedge between the lens's curved lower face and the mirror (gap = sag)
    var fprof = []; for (i = NS; i >= 0; i--) { rr = RIM * 0.98 * i / NS; fprof.push(new T.Vector2(rr, p.R - Math.sqrt(p.R * p.R - rr * rr))); }
    for (i = 0; i <= NS; i++) { rr = RIM * 0.98 * i / NS; fprof.push(new T.Vector2(rr, 0)); }
    filmMesh = new T.Mesh(new T.LatheGeometry(fprof, 48), new T.MeshPhysicalMaterial({ color: 0x9fd0e6, roughness: 0.05, transparent: true, opacity: 0.6, depthWrite: false, side: T.DoubleSide }));
    filmMesh.position.set(AX, YM, AZ); filmMesh.renderOrder = 4; filmMesh.visible = false; S.scene.add(filmMesh);
  } else {
    var RBOWL = 0.075, YP = 0.025, SAG = p.R - Math.sqrt(p.R * p.R - RBOWL * RBOWL);
    YREF = YP + p.t;                                            // the flat top of the liquid
    var bp = [], ii; for (ii = 0; ii <= 30; ii++) { rr = RBOWL * ii / 30; bp.push(new T.Vector2(rr, p.R - Math.sqrt(p.R * p.R - rr * rr))); }
    bp.push(new T.Vector2(RBOWL + 0.012, SAG)); bp.push(new T.Vector2(RBOWL + 0.012, SAG - 0.004));
    mirrorMesh = new T.Mesh(new T.LatheGeometry(bp, 72), new T.MeshStandardMaterial({ color: 0xdfe3e8, roughness: 0.04, metalness: 1, side: T.DoubleSide, envMapIntensity: 1.6 }));
    mirrorMesh.position.set(AX, YP, AZ); S.scene.add(mirrorMesh);
    var cup = S.mesh(new T.CylinderGeometry(RBOWL + 0.012, RBOWL + 0.006, 0.012, 48), M.iron); cup.position.set(AX, YP - 0.006, AZ); S.scene.add(cup);
    var rl = Math.sqrt(2 * p.R * p.t);                          // the radius where the liquid is as deep as the pole
    var lp = [new T.Vector2(0, p.t)]; for (ii = 0; ii <= 24; ii++) { rr = rl * (24 - ii) / 24; lp.push(new T.Vector2(rl * ii / 24, p.t)); }
    var lq = [new T.Vector2(0, p.t), new T.Vector2(rl, p.t)]; for (ii = 24; ii >= 0; ii--) { rr = rl * ii / 24; lq.push(new T.Vector2(rr, p.R - Math.sqrt(p.R * p.R - rr * rr))); }
    filmMesh = new T.Mesh(new T.LatheGeometry(lq, 48), new T.MeshPhysicalMaterial({ color: 0x9fd0e6, roughness: 0.05, transparent: true, opacity: 0.6, depthWrite: false, side: T.DoubleSide }));
    filmMesh.position.set(AX, YP, AZ); filmMesh.renderOrder = 4; filmMesh.visible = false; S.scene.add(filmMesh);
  }
  // ---------- retort stand with a sliding clamp and a pin held point-down
  var SX = AX - 0.2, RODH = 0.62;
  var sbase = S.rounded(0.2, 0.15, 0.02, 0.015, M.iron); sbase.rotation.x = -Math.PI / 2; sbase.position.set(SX + 0.04, 0.01, AZ); S.scene.add(sbase);
  var rod = S.mesh(new T.CylinderGeometry(0.007, 0.007, RODH, 32), M.chrome); rod.position.set(SX, RODH / 2 + 0.02, AZ); S.scene.add(rod);
  S.contact(0.3, 0.22, SX + 0.04, AZ, 0.5);
  var clamp = new T.Group(); S.scene.add(clamp);
  var boss = S.rounded(0.04, 0.036, 0.034, 0.006, M.alu); boss.position.set(SX, 0, AZ); clamp.add(boss);
  var thumb = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.03, 14), M.chrome); thumb.rotation.x = Math.PI / 2; thumb.position.set(SX, 0, AZ + 0.03); clamp.add(thumb);
  var knobT = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.008, 6), M.black); knobT.rotation.x = Math.PI / 2; knobT.position.set(SX, 0, AZ + 0.048); clamp.add(knobT);
  var arm = S.mesh(new T.CylinderGeometry(0.005, 0.005, AX - SX, 20), M.chrome); arm.rotation.z = Math.PI / 2; arm.position.set((SX + AX) / 2 + 0.0, 0, AZ); clamp.add(arm);
  var jaw = S.rounded(0.03, 0.026, 0.028, 0.005, M.alu); jaw.position.set(AX, -0.0, AZ); clamp.add(jaw);
  var cork = S.mesh(new T.CylinderGeometry(0.009, 0.008, 0.026, 20), M.cork); cork.position.set(AX + p.h, -0.026, AZ); clamp.add(cork);
  var PINL = 0.06;
  var pinG = new T.Group(); clamp.add(pinG);                    // the pin: its tip is the object
  var shaft = S.mesh(new T.CylinderGeometry(0.0006, 0.0004, PINL, 10), M.steel); shaft.position.set(0, PINL / 2, 0); pinG.add(shaft);
  var head = S.mesh(new T.SphereGeometry(0.0028, 14, 10), new T.MeshStandardMaterial({ color: 0xc23b30, roughness: 0.4 })); head.position.set(0, PINL + 0.0008, 0); pinG.add(head);
  pinG.position.set(AX + p.h, 0, AZ);
  var ghostMat = new T.MeshStandardMaterial({ color: 0xff6a3a, roughness: 0.4, transparent: true, opacity: 0.0, emissive: 0x802a10, emissiveIntensity: 0.6, depthWrite: false });
  var ghost = new T.Group(); S.scene.add(ghost);
  var gs = S.mesh(new T.CylinderGeometry(0.0004, 0.0006, PINL, 10), ghostMat, false, false); gs.position.y = -PINL / 2; ghost.add(gs);
  var gh = S.mesh(new T.SphereGeometry(0.0028, 14, 10), ghostMat, false, false); gh.position.y = -PINL - 0.0008; ghost.add(gh);
  // a vertical scale beside the pin, zero at the reference level (the lens centre, or the flat top of the liquid)
  var SCL = 0.46, scx = AX + 0.06, scTex = S.canvasTex(80, 1840, function (x, w, h) {
    x.fillStyle = '#f0ead8'; x.fillRect(0, 0, w, h); x.fillStyle = '#1a1a1a'; x.font = '600 26px sans-serif';
    for (var c = 0; c <= 46; c++) { var y = h - 14 - c * 40; x.fillRect(0, y - 1, c % 10 === 0 ? 38 : c % 5 === 0 ? 28 : 18, 2.4); if (c % 5 === 0) x.fillText(String(c), 42, y + 8); } });
  var scale = new T.Mesh(new T.PlaneGeometry(0.02, SCL + 0.01), new T.MeshStandardMaterial({ map: scTex, roughness: 0.6 })); scale.position.set(scx, YREF + SCL / 2 + 0.0, AZ + 0.01); S.scene.add(scale);
  var scPost = S.mesh(new T.BoxGeometry(0.004, SCL + 0.02, 0.004), M.iron); scPost.position.set(scx + 0.012, YREF + SCL / 2, AZ + 0.008); S.scene.add(scPost);
  var plate0 = S.label('SCALE · cm · zero at the ' + (MODE === 0 ? 'lens centre' : 'flat top of the liquid'), { w: 0.06, ratio: 0.14, color: '#e8e2cf' }); plate0.position.set(scx, YREF - 0.012, AZ + 0.0105); S.scene.add(plate0);
  var idx = S.mesh(new T.BoxGeometry(0.03, 0.0012, 0.003), M.red, false); idx.position.set(scx - 0.006, 0, AZ + 0.012); clamp.add(idx);
  // ---------- the dropper bottle and a cloth
  var DX = AX + 0.26, DZ = AZ + 0.04;
  var bottle = new T.Group(); S.scene.add(bottle); bottle.position.set(DX, 0, DZ);
  var bb = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.06, 28), new T.MeshPhysicalMaterial({ color: 0x6b3a1a, roughness: 0.18, transparent: true, opacity: 0.9 })); bb.position.y = 0.03; bottle.add(bb);
  var bn = S.mesh(new T.CylinderGeometry(0.008, 0.012, 0.012, 20), M.black); bn.position.y = 0.066; bottle.add(bn);
  var bt = S.mesh(new T.SphereGeometry(0.011, 16, 10), new T.MeshStandardMaterial({ color: 0x1b1b1d, roughness: 0.5 })); bt.position.y = 0.085; bt.scale.y = 1.5; bottle.add(bt);
  var bl = S.label(LIQUID.length > 18 ? 'LIQUID' : LIQUID.toUpperCase(), { w: 0.03, ratio: 0.3, color: '#f3ead2' }); bl.position.set(0, 0.03, 0.0202); bottle.add(bl);
  S.contact(0.07, 0.07, DX, DZ, 0.45);
  var cloth = S.mesh(new T.BoxGeometry(0.09, 0.006, 0.07), new T.MeshStandardMaterial({ color: 0xe9e4d6, roughness: 1 })); cloth.position.set(DX, 0.003, DZ + 0.1); cloth.rotation.y = 0.25; S.scene.add(cloth);

  S.addApparatus('stand', rod, 'Retort stand', 'A steel rod on a heavy base. The clamp slides up and down it and is fixed with the thumb screw.');
  S.addApparatus('pin', pinG, 'Pin in the clamp', 'A pin held point-down by a cork in the clamp. Its tip is the object; you move the clamp until the pin and its own image coincide.');
  S.addApparatus('scale', scale, 'Vertical scale', 'Centimetres, with its zero at the ' + (MODE === 0 ? 'centre of the lens' : 'flat top of the liquid') + '. The red index on the clamp reads the height of the pin tip.');
  S.addApparatus('mirror', MODE === 0 ? lensMesh : mirrorMesh, MODE === 0 ? 'Convex lens on a plane mirror' : 'Concave mirror, face up', MODE === 0 ? 'A thin biconvex glass lens lies on a plane mirror, touching it at the centre. Its lower face is curved, so a wedge of air is left between the lens and the mirror.' : 'A concave mirror lying face up. A little liquid poured in gives a flat top surface.');
  S.addApparatus('bottle', bottle, 'Dropper bottle', (VAR.sample ? VAR.sample + '. ' : '') + 'A few drops under the lens, or enough to cover the pole of the mirror.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudH = S.hudCard('Pin height H'), hudL = S.hudCard('Liquid'), hudG = S.hudCard('Pin and its image');

  // ---------- the kernel
  var view = null, ghostFor = '';
  function look() { sync(); view = K.view(null, p); return view; }
  function gapMm(H, liq) {                                       // the parallax the eye sees (mm), for a pin at H
    var q = assign(p, { H: H, liq: liq ? 1 : 0 }); return K.view(null, q).coin * 1000; }
  function layout() {
    var v = look(), ytip = YREF + st.H;
    clamp.position.set(0, ytip + PINL + 0.04, 0);               // the clamp sits above the pin; the pin hangs from it
    pinG.position.set(AX + p.h, -PINL - 0.04, AZ);
    cork.position.set(AX + p.h, -0.026, AZ);
    pinG.rotation.set(0, 0, 0); pinG.scale.y = 1;
    pinG.position.y = -(PINL + 0.04); pinG.children[0].position.y = PINL / 2; pinG.children[1].position.y = PINL + 0.0008;
    boss.position.set(SX, 0, AZ); jaw.position.set(AX, 0, AZ);
    idx.position.set(scx - 0.006, -(PINL + 0.04), AZ + 0.012);
    boss.position.y = 0; arm.position.y = 0;
    filmMesh.visible = st.liq;
    var showG = v.real > 0.5 && Math.abs(v.coin) < 0.08;
    ghost.visible = showG;
    ghostMat.opacity = showG ? 0.65 : 0;
    ghost.position.set(AX + v.img_y, YREF - v.img_x, AZ);
    hudH.set(fmt1(st.H * 100) + ' cm'); hudL.set(st.liq ? 'in' : 'dry'); hudG.set(gapWord(v));
  }
  function fmt1(x) { return (Math.round(x * 10) / 10).toFixed(1); }
  function gapWord(v) { var g = v.coin * 1000; if (!isFinite(g) || Math.abs(g) > 90 || !v.real) return 'no image yet'; return Math.abs(g) <= 1.2 ? 'together: no parallax' : 'image ' + fmt1(Math.abs(g)) + ' mm ' + (g > 0 ? 'below' : 'above') + ' the pin'; }
  function noParallax() { return Math.abs(look().coin * 1000) <= 1.2 && look().real > 0.5; }

  // ---------- human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function movePin(toCm) {
    if (S.hand.busy) return wait();
    toCm = Math.round(toCm * 10) / 10;
    if (!(toCm >= HMIN * 100 && toCm <= HMAX * 100)) { S.say('The rod holds the pin between ' + HMIN * 100 + ' cm and ' + HMAX * 100 + ' cm.'); return Promise.resolve(false); }
    var from = st.H * 100;
    if (Math.abs(toCm - from) < 0.04) return Promise.resolve(true);
    function at(k) { return (from + (toCm - from) * k) / 100; }
    return S.hand.pinchMove(new T.Vector3(SX + 0.02, YREF + from / 100 + PINL + 0.04, AZ + 0.04), function (k) { return new T.Vector3(SX + 0.02, YREF + at(k) + PINL + 0.04, AZ + 0.04); },
      function (k) { st.H = at(k); layout(); }, { ms: 500 + Math.abs(toCm - from) * 40, reachMs: 600 }).then(function () { st.H = toCm / 100; layout(); S.render(); return true; });
  }
  function addLiquid() {
    if (S.hand.busy) return wait();
    if (st.liq) return Promise.resolve(true);
    return S.hand.tap(bottle.children[2], 'top').then(function () {
      st.liq = true; layout();
      S.say(MODE === 0 ? 'A few drops run into the wedge under the lens and spread to a thin film.' : 'The liquid fills the bottom of the mirror; its top is flat.'); S.render(); return true; });
  }
  function wipe() {
    if (S.hand.busy) return wait();
    return S.hand.tap(cloth, 'top').then(function () { st.liq = false; st.dry = null; st.wet = null; layout(); S.say('The mirror and lens are wiped dry.'); S.render(); return true; });
  }
  function noteDry() {
    if (S.hand.busy) { wait(); return false; }
    if (st.liq) { S.say('Wipe the liquid off first: this reading is for the dry set-up.'); return false; }
    if (!noParallax()) { S.say('The pin and its image are not together yet. Move the pin up or down in small steps until there is no parallax.'); return false; }
    st.dry = Math.round(st.H * 1000) / 1000; S.say('H without the liquid = ' + fmt1(st.dry * 100) + ' cm.'); S.render(); return true;
  }
  function noteWet() {
    if (S.hand.busy) { wait(); return false; }
    if (st.dry === null) { S.say('Take the reading without the liquid first.'); return false; }
    if (!st.liq) { S.say('Put the liquid in first.'); return false; }
    if (!noParallax()) { S.say('The pin and its image are not together yet. Move the pin in small steps until there is no parallax.'); return false; }
    var wet = Math.round(st.H * 1000) / 1000;
    S.addRow({ Hd: st.dry, Hl: wet }); S.say('Written: H without the liquid = ' + fmt1(st.dry * 100) + ' cm, with the liquid = ' + fmt1(wet * 100) + ' cm.');
    st.wet = wet; return true;
  }
  function findNoParallax(lo, hi, liq) {                         // what a careful student converges to (reads to 1 mm)
    function g(H) { return gapMm(H, liq); }
    var a = lo, b = hi, ga = g(a), i, m, gm;
    for (i = 0; i < 40; i++) { m = (a + b) / 2; gm = g(m); if ((gm > 0) === (ga > 0)) { a = m; ga = gm; } else b = m; }
    return Math.round((a + b) / 2 * 1000) / 10;                  // cm, 1 mm
  }
  function bracket(liq) {                                        // where the careful student searches
    if (MODE === 0) { var Fg = p.R / (2 * (p.n - 1)); return liq ? [st.dry || Fg, 3 * (st.dry || Fg)] : [0.75 * Fg, 1.5 * Fg]; }
    return [0.58 * p.R, 1.15 * p.R];
  }
  function trial() {
    var b0 = bracket(false), d, w;
    return (st.liq ? wipe() : Promise.resolve()).then(function () {
      d = findNoParallax(b0[0], b0[1], false); return movePin(d); }).then(function () { noteDry(); return addLiquid(); }).then(function () {
      var b1 = bracket(true); w = findNoParallax(b1[0], b1[1], true); return movePin(w); }).then(function () { noteWet(); });
  }
  function nOf(rows) {
    var v = (rows || []).filter(function (r) { return r.Hl > 0; }).map(function (r) { return MODE === 0 ? 1 + 2 * (p.n - 1) * (1 - r.Hd / r.Hl) : r.Hd / r.Hl; });
    return v.length ? S.fit.mean(v) : NaN;
  }

  layout();
  S.tickers.push(function () { /* the scene is static except while the hand moves the clamp */ });
  var VIEWS = { bench: [[0.05, 0.55, 1.05], [-0.02, 0.24, -0.1]], pin: [[-0.05, YREF + 0.2, 0.3], [AX, YREF + 0.12, AZ]], lens: [[0.12, YREF + 0.1, 0.22], [AX, YREF, AZ]],
    scale: [[0.0, YREF + 0.25, 0.4], [scx, YREF + 0.22, AZ]], bottle: [[DX + 0.1, 0.16, DZ + 0.22], [DX, 0.04, DZ]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] };
  VIEWS.stand = VIEWS.pin; VIEWS.mirror = VIEWS.lens;

  return {
    camera: { pos: [0.05, 0.55, 1.05], look: [-0.02, 0.24, -0.1] },
    views: VIEWS,
    theory: MODE === 0 ? { principle: 'A convex lens on a plane mirror, with a film of liquid between them, is a convex lens and a plano-concave liquid lens in contact. The pin and its image coincide when the rays leave the lens parallel and strike the mirror normally: the pin is then at the focal length F of the combination.',
        formula: '1/F = 1/f1 + 1/f2', formulaNote: 'f1 = focal length of the lens alone (pin height without the liquid) · f2 = focal length of the liquid lens (negative) · n = 1 + 2(n_g − 1)(1 − f1/F)',
        more: ['The lens glass has n_g = ' + (+p.n.toFixed(4)) + ', so f1 = R / (2(n_g − 1)) gives the radius R of its faces. The liquid lens has f2 = −R / (n − 1), so n comes straight from f1 and F.'],
        precautions: 'Keep the eye above the pin and move the head slightly sideways: if the image moves against the pin there is parallax. Wipe the lens and the mirror dry before the first reading.' }
      : { principle: 'A concave mirror with the pin at its centre of curvature gives an image that coincides with the pin. When a liquid with a flat top covers the pole, the light from the pin is refracted at the top; the pin must seem to be at the centre of curvature, and the liquid makes an object x2 above its surface look n x2 deep.',
        formula: 'n = x1 / x2', formulaNote: 'x1 = pin height without the liquid (the centre of curvature) · x2 = pin height with the liquid, both read from the same level',
        more: ['Both heights are read on the scale whose zero is the flat top of the liquid, so the depth of the liquid at the pole cancels out of the ratio.'],
        precautions: 'Keep the eye above the pin and move the head sideways to look for parallax. The mirror must lie flat, and the liquid must cover the pole of the mirror.' },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim, MODE === 0 ? 'Lens glass n = ' + (+p.n.toFixed(4)) + ' (printed on the lens).' : 'Concave mirror lying face up.', 'H = height of the pin tip above the zero of the scale.', MODE === 0 ? 'n = 1 + 2(n_g − 1)(1 − H1/H2)' : 'n = H1 / H2', 'Precaution: no parallax, eye above the pin.'],
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'H1 dry (cm)', get: function (r) { return (r.Hd * 100).toFixed(1); } },
        { label: 'H2 with liquid (cm)', get: function (r) { return (r.Hl * 100).toFixed(1); } },
        { label: 'n', get: function (r) { return (MODE === 0 ? 1 + 2 * (p.n - 1) * (1 - r.Hd / r.Hl) : r.Hd / r.Hl).toFixed(3); } }] },
    graph: null,
    result: function (rows) { var n = nOf(rows); if (!isFinite(n) || rows.length < 2) return null;
      return { label: 'n', value: n, unit: '', digits: 3, truth: p.nl, note: 'Mean of ' + (MODE === 0 ? '1 + 2(n_g − 1)(1 − H1/H2)' : 'H1 / H2') + ' over ' + rows.length + ' trials.' }; },
    tol: 0.02,
    chips: ['What is parallax?', MODE === 0 ? 'Why is the liquid lens concave?' : 'Why does the pin come lower with the liquid?', 'Check my readings', 'Why is my n a little different?'],
    viva: MODE === 0 ? [['The liquid lens formed between the lens and the mirror is', ['plano-concave (diverging)', 'plano-convex (converging)', 'a flat plate'], 0, 'It is thick at the edges and thin at the centre, so it diverges.'],
        ['With the liquid, the pin has to be held', ['higher than before', 'lower than before', 'at the same height'], 0, 'The diverging liquid lens weakens the combination: F is longer than f1.']]
      : [['After the liquid is poured in, the pin has to be held', ['lower', 'higher', 'at the same height'], 0, 'The liquid makes the pin look deeper, so it must be brought nearer the surface.'],
        ['Why must both heights be read from the same level?', ['The ratio x1 / x2 would be wrong otherwise', 'To save time', 'The scale is short'], 0, 'n = x1 / x2 holds only if both heights are taken from the same level.']],
    askState: function () { var v = view || look(); return { mode: MODE === 0 ? 'convex lens on a plane mirror' : 'concave mirror', liquid_in: st.liq, pin_height_cm: fmt1(st.H * 100), pin_and_image: gapWord(v), parallax_mm: +(v.coin * 1000).toFixed(1),
      dry_reading_cm: st.dry === null ? null : fmt1(st.dry * 100), trials_recorded: S.rows.length }; },
    steps: [
      { id: 'find', title: 'Find the heights', view: 'bench', render: function (u) {
          u.h2(MODE === 0 ? 'Find the pin heights with and without the liquid' : 'Find the pin heights with and without the liquid');
          u.p('Move the clamp until the tip of the pin and the tip of its image are together, with no parallax: look from above and move your head a little to the side. Take the dry reading first, then the liquid, then repeat once more.');
          u.slider('Pin height', HMIN * 100, HMAX * 100, 0.1, function () { return st.Hset; }, function (x) { st.Hset = x; }, 'cm', 1);
          u.row(u.button('Move the pin there', function () { movePin(st.Hset); S.render(); }, true, S.hand.busy));
          function nudge(d) { return function () { var to = Math.round((st.H * 100 + d) * 10) / 10; st.Hset = to; movePin(to); S.render(); }; }
          u.row(u.button('− 1 cm', nudge(-1), false, S.hand.busy), u.button('− 1 mm', nudge(-0.1), false, S.hand.busy), u.button('+ 1 mm', nudge(0.1), false, S.hand.busy), u.button('+ 1 cm', nudge(1), false, S.hand.busy));
          u.live(function () { var v = view || look(); return 'H = ' + fmt1(st.H * 100) + ' cm   ·   ' + (st.liq ? 'liquid in' : 'dry') + '   ·   ' + gapWord(v); });
          u.task('1. Dry: pin and image together', st.dry !== null, st.dry === null ? 'Note H1 when there is no parallax' : 'H1 = ' + fmt1(st.dry * 100) + ' cm').add(u.button('Note H1 (dry)', function () { noteDry(); S.render(); }, st.dry === null, S.hand.busy));
          u.task('2. Put the liquid in', st.liq, st.liq ? 'Liquid in' : 'The hand squeezes the dropper').add(u.button(st.liq ? 'Liquid is in' : 'Add the liquid', function () { S.focus('bottle'); addLiquid(); }, !st.liq, S.hand.busy || st.dry === null || st.liq));
          u.task('3. With the liquid: pin and image together', st.wet !== null, st.wet === null ? 'Note H2 when there is no parallax' : 'H2 = ' + fmt1(st.wet * 100) + ' cm').add(u.button('Note H2 (with liquid)', function () { noteWet(); S.render(); }, st.wet === null, S.hand.busy));
          u.row(u.button('Wipe dry and repeat', function () { wipe(); }, false, S.hand.busy), u.button(st.rays ? 'Hide the light path' : 'Show the light path', function () { st.rays = !st.rays; S.render(); }));
          u.h3('Observation table'); u.table();
          u.next('Next: result', S.rows.length >= 2);
          if (S.rows.length < 2) u.p(S.rows.length + ' of 2 trials recorded.');
        },
        ok: function () { return S.rows.length >= 2; },
        auto: function () { return trial().then(function () { return wipe(); }).then(function () { return trial(); }); } },
    ],
    tick: function () { layout(); },
  };
});
