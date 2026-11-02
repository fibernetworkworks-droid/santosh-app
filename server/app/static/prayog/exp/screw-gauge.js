/* Prayogshala studio module: Screw gauge (NCERT Class XI, Units and Measurement).
   A micrometer screw gauge at TRUE size (pitch 0.5 mm, 50 thimble divisions, least count 0.01 mm) held in a bench
   micrometer stand: enamelled U-frame, anvil, spindle, sleeve with the linear (pitch) scale, a thimble whose 50 printed
   divisions turn with the spindle, and a ratchet. A thin copper wire is measured at three places along its length.
   Numbers: K.gauge from kernels.js (kind 1) with the lab's params - the same PSR / thimble division / reading the server
   checks. The thimble sits exactly where the kernel's reading puts it (rounded to the least count), so the division on
   the datum line is the kernel's division. The student reads and TYPES the zero error, PSR and HSR. */
HoolaStudio.define('screw-gauge', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.gauge;
  var lp = S.lab.params || {};
  var p = window.HoolaKernels.paramsFor('gauge', lp); p.kind = 1;
  if (lp.ze === undefined) p.ze = 0.00003;           // this gauge's own zero error (+0.03 mm)
  function r6(v) { return Math.round(v * 1e6) / 1e6; }
  var KV = K.view({}, p), KZ = K.view({}, Object.assign({}, p, { L: 0 }));
  var LC = r6(KV.lc * 1000), PITCH = r6(p.pitch * 1000), NDIV = p.ndiv;
  var ZR = r6((KZ.main + KZ.div * KZ.lc) * 1000);              // zero reading, faces touching (mm)
  var PSR = r6(KV.main * 1000), HSR = KV.div;                   // what the scales show on the wire
  var OBS = r6(PSR + HSR * LC), WD = r6(OBS - ZR);              // observed reading; gap between the faces on the wire (mm)
  var KREAD = r6(K.measure(p).reading * 1000);
  var FONT = '"Public Sans", Arial, Helvetica, sans-serif';
  var GX = -0.01, GZ = -0.03, AXY = 0.062;                      // world: anvil face on the spindle axis
  var SLV0 = 42;                                                // sleeve zero line, mm from the anvil face
  var OPEN = Math.max(1.5, Math.ceil((WD + 0.7) / PITCH - 1e-9) * PITCH);   // open far enough for this wire to slip in
  function fmt(v) { return String(+(+v).toFixed(4)); }
  var PS = fmt(PITCH) + ' mm', LS = fmt(LC) + ' mm';
  // the wire under test: its metal from the variant's sample line (copper by default)
  var SAMPLE = ((S.lab.variant || {}).sample || '');
  var WIRES = [[/constantan|eureka/i, 'Constantan wire', 'Cu-Ni', 0xbdb3a6, '#a99f92'], [/manganin/i, 'Manganin wire', 'Mn', 0xc29878, '#a87e5f'],
    [/nichrome/i, 'Nichrome wire', 'Ni-Cr', 0xa9abad, '#8f9294'], [/steel/i, 'Steel wire', 'Steel', 0xb7bcc1, '#9aa0a6'],
    [/brass/i, 'Brass wire', 'Brass', 0xcaa44c, '#b08a35'], [/alumin/i, 'Aluminium wire', 'Al', 0xd5d9dc, '#bfc4c8'], [/./, 'Copper wire', 'Cu', 0xc8764a, '#b8683d']];
  var WL = WIRES.filter(function (w) { return w[0].test(SAMPLE || 'copper'); })[0];
  var WNAME = WL[1], WSYM = WL[2];
  var SWG = (SAMPLE.match(/SWG\s*(\d+)/i) || [])[1];
  var ZS = [-14, 0, 14];                                        // three places along the wire (mm)

  var st = { gap: 3.0, wire: 'bench', zi: 0, wk: 1, placedFor: -1, lcOk: false, zeroOk: false, tries: { zero: 0, read: 0 },
    inp: { lc: '', zero: '', psr: '', hsr: '' }, acting: false };

  // ---------------------------------------------------------------- helpers
  var G = new T.Group(); G.scale.setScalar(0.001); G.position.set(GX, AXY, GZ); S.scene.add(G);
  var MOV = new T.Group(); G.add(MOV);                         // moves with the spindle: origin on the spindle face
  var SPIN = new T.Group(); MOV.add(SPIN);                     // turns with the screw (about the axis)
  var enamel = new T.MeshStandardMaterial({ color: 0x1f3d36, roughness: 0.32, metalness: 0.2 });
  var satin = new T.MeshStandardMaterial({ color: 0xd2d6d9, roughness: 0.3, metalness: 0.85 });
  var texes = [];
  function liveCanvas(w, h, draw) { var t = S.liveTex(w, h); t.anisotropy = 16; t.paint = function () { t.draw(draw); }; t.paint(); texes.push(t); return t; }
  function printMat(tex) { return new T.MeshStandardMaterial({ map: tex, roughness: 0.4, metalness: 0.4 }); }
  function brushed(x, w, h, base, vertical) { x.fillStyle = base; x.fillRect(0, 0, w, h); var sd = 5;
    for (var i = 0; i < (vertical ? w : h); i += 2) { sd = (sd * 16807) % 2147483647; var a = (sd / 2147483647) * 0.06; x.fillStyle = 'rgba(' + (i % 4 ? '255,255,255' : '40,45,50') + ',' + a + ')';
      if (vertical) x.fillRect(i, 0, 1, h); else x.fillRect(0, i, w, 1); } }
  // cylinders along the spindle axis: geometry made about local y, then turned so y -> +x; UVs re-mapped so a canvas reads
  // like the surface unrolled from the front: canvas X = along the axis (left -> right), canvas Y = angle (up -> down)
  function axial(g, len, a0, a1, th0, thLen) {
    var pos = g.attributes.position, uv = g.attributes.uv;
    for (var i = 0; i < pos.count; i++) { var a = th0 + uv.getX(i) * thLen; uv.setXY(i, (pos.getY(i) + len[0]) / len[1], 1 - (a - a0) / (a1 - a0)); }
    uv.needsUpdate = true; return g; }
  function alongX(m) { m.rotation.z = -Math.PI / 2; return m; }
  function knurlTex() { return S.canvasTex(256, 256, function (x, w, h) { x.fillStyle = '#c3c8cc'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(40,44,48,.7)'; x.lineWidth = 3;
    for (var i = -w; i < 2 * w; i += 12) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i + h, h); x.stroke(); x.beginPath(); x.moveTo(i, h); x.lineTo(i + h, 0); x.stroke(); } }); }
  var knurl = knurlTex(); knurl.wrapS = knurl.wrapT = T.RepeatWrapping;

  // ---------------------------------------------------------------- U-frame (enamelled), anvil, sleeve with the pitch scale
  (function () { var s = new T.Shape();
    s.moveTo(-20, 7); s.lineTo(-20, -24); s.quadraticCurveTo(-20, -34, -10, -34); s.lineTo(30, -34); s.quadraticCurveTo(40, -34, 40, -24); s.lineTo(40, 8);
    s.lineTo(30, 8); s.lineTo(30, -18); s.quadraticCurveTo(30, -24, 24, -24); s.lineTo(-2, -24); s.quadraticCurveTo(-8, -24, -8, -18); s.lineTo(-8, 7); s.closePath();
    var g = new T.ExtrudeGeometry(s, { depth: 6, bevelEnabled: true, bevelThickness: 1, bevelSize: 0.9, bevelSegments: 3, curveSegments: 16 }); g.translate(0, 0, -3);
    var f = S.mesh(g, enamel); G.add(f); })();
  var plate = S.label('0–25 mm   LC ' + LS, { w: 26, ratio: 0.14, color: '#e9ede6', weight: 600 }); plate.position.set(10, -29.2, 4.05); G.add(plate);
  var anvil = alongX(S.mesh(new T.CylinderGeometry(3.25, 3.25, 9, 40), satin)); anvil.position.set(-4.5, 0, 0); G.add(anvil);
  var aface = alongX(S.mesh(new T.CylinderGeometry(3.0, 3.0, 0.3, 40), new T.MeshStandardMaterial({ color: 0x9aa0a6, roughness: 0.2, metalness: 1 }))); aface.position.set(-0.15, 0, 0); G.add(aface);
  var boss = alongX(S.mesh(new T.CylinderGeometry(6.5, 6.5, 4, 32), enamel)); boss.position.set(35, 0, 0); G.add(boss);
  var sleeve = alongX(S.mesh(new T.CylinderGeometry(5.5, 5.5, 30, 64), satin)); sleeve.position.set(55, 0, 0); G.add(sleeve);
  // printed band on the front of the sleeve: datum line, mm marks above, half-mm marks below
  var BA = 1.2, SPX = 100, SR = 5.53;
  var sTex = liveCanvas(30 * SPX, Math.round(2 * BA * SR * SPX), function (x, w, h) {
    brushed(x, w, h, '#d9dcdf');
    var X = function (mm) { return (mm - 40) * SPX; }, Y = function (arc) { return (arc / SR + BA) / (2 * BA) * h; };   // arc mm from the front, + = down
    var lw = 0.12 * SPX; x.fillStyle = '#121416';
    x.fillRect(X(40.4), Y(0) - lw / 2, X(70) - X(40.4), lw);
    for (var n = 0; n <= 27; n++) { var big = n % 5 === 0, L1 = big ? 2.2 : 1.6; x.fillRect(X(SLV0 + n) - lw / 2, Y(-L1), lw, Y(0) - Y(-L1));
      if (big) { x.font = '600 ' + Math.round(1.55 * SPX) + 'px ' + FONT; x.textAlign = 'center'; x.textBaseline = 'alphabetic'; x.fillText(String(n), X(SLV0 + n), Y(-2.55)); }
      var hx = SLV0 + n + 0.5; if (hx < 69.8) x.fillRect(X(hx) - lw / 2, Y(0), lw, Y(1.35) - Y(0)); }
    x.font = '500 ' + Math.round(0.9 * SPX) + 'px ' + FONT; x.textAlign = 'left'; x.textBaseline = 'top'; x.fillText('mm', X(40.45), Y(0.35)); });
  var sBand = alongX(S.mesh(axial(new T.CylinderGeometry(SR, SR, 30, 48, 1, true, -BA, 2 * BA), [15, 30], -BA, BA, -BA, 2 * BA), printMat(sTex), false));
  sBand.position.set(55, 0, 0); G.add(sBand);
  // spindle lock lever on top of the frame arm
  var lk = S.mesh(new T.CylinderGeometry(2.4, 2.4, 3.2, 20), new T.MeshStandardMaterial({ map: knurl, roughness: 0.4, metalness: 0.8 })); lk.position.set(35, 9.4, 0); G.add(lk);
  var lkt = S.mesh(new T.BoxGeometry(1.2, 1.2, 7), satin); lkt.position.set(35, 11.3, 2.2); G.add(lkt);

  // ---------------------------------------------------------------- spindle, thimble (50 divisions), ratchet
  var spindle = alongX(S.mesh(new T.CylinderGeometry(3.25, 3.25, 46, 40), satin)); spindle.position.set(23, 0, 0); SPIN.add(spindle);
  var sface = alongX(S.mesh(new T.CylinderGeometry(3.0, 3.0, 0.3, 40), new T.MeshStandardMaterial({ color: 0x9aa0a6, roughness: 0.2, metalness: 1 }))); sface.position.set(0.15, 0, 0); SPIN.add(sface);
  var TH0 = SLV0 + ZR;                                           // thimble edge, from the spindle face
  var TLEN = 22.6, TPX = 1536 / TLEN;
  var thTex = liveCanvas(1536, 3072, function (x, w, h) {
    brushed(x, w, h, '#d6d9dc', true);
    var X = function (al) { return al * TPX; }, Y = function (a) { return (a + Math.PI) / (2 * Math.PI) * h; };
    // knurled grip
    x.save(); x.beginPath(); x.rect(X(11.6), 0, X(TLEN) - X(11.6), h); x.clip(); x.fillStyle = '#b4b9be'; x.fillRect(X(11.6), 0, X(TLEN), h);
    x.strokeStyle = 'rgba(35,38,42,.75)'; x.lineWidth = 5; for (var i = -h; i < h + w; i += 22) { x.beginPath(); x.moveTo(X(11.6) + i, 0); x.lineTo(X(11.6) + i - h, h); x.stroke(); x.beginPath(); x.moveTo(X(11.6) + i - h, 0); x.lineTo(X(11.6) + i, h); x.stroke(); }
    x.restore();
    x.fillStyle = '#121416'; var lw = 9;
    for (var d = 0; d < NDIV; d++) { var a = -d * 2 * Math.PI / NDIV, big = d % 5 === 0, L1 = big ? 3.3 : 2.3;
      [-h, 0, h].forEach(function (off) { var yy = Y(a) + off; if (yy < -200 || yy > h + 200) return;
        x.fillRect(X(0.12), yy - lw / 2, X(L1) - X(0.12), lw);
        if (big) { x.font = '600 ' + Math.round(1.7 * TPX) + 'px ' + FONT; x.textAlign = 'left'; x.textBaseline = 'middle'; x.fillText(String(d), X(3.75), yy); } }); }
  });
  var thProfile = [[5.62, 0], [7.35, 3.2], [7.6, 3.55], [7.6, 11.4], [7.85, 11.6], [7.85, TLEN - 0.5], [7.4, TLEN], [4.6, TLEN]].map(function (q) { return new T.Vector2(q[0], q[1]); });
  var thG = new T.LatheGeometry(thProfile, 128, -Math.PI, 2 * Math.PI);
  axial(thG, [0, TLEN], -Math.PI, Math.PI, -Math.PI, 2 * Math.PI);
  var thimble = alongX(S.mesh(thG, printMat(thTex))); thimble.position.set(TH0, 0, 0); SPIN.add(thimble);
  var thBack = alongX(S.mesh(new T.CylinderGeometry(5.6, 5.6, 0.2, 40), satin)); thBack.position.set(TH0 + 0.05, 0, 0); SPIN.add(thBack);
  var rk = knurl.clone(); rk.needsUpdate = true; rk.repeat.set(6, 1); rk.wrapS = rk.wrapT = T.RepeatWrapping;
  var ratchet = alongX(S.mesh(new T.CylinderGeometry(4.6, 4.6, 10, 48), [new T.MeshStandardMaterial({ map: rk, roughness: 0.4, metalness: 0.8 }), satin, satin])); ratchet.position.set(TH0 + TLEN + 5.6, 0, 0); SPIN.add(ratchet);
  var rneck = alongX(S.mesh(new T.CylinderGeometry(3.4, 3.4, 1.4, 32), satin)); rneck.position.set(TH0 + TLEN + 0.3, 0, 0); SPIN.add(rneck);
  var rcap = S.mesh(new T.SphereGeometry(4.6, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), satin); rcap.rotation.z = -Math.PI / 2; rcap.scale.set(1, 0.35, 1); rcap.position.set(TH0 + TLEN + 10.6, 0, 0); SPIN.add(rcap);
  var RAT_END = TH0 + TLEN + 11.8;

  // ---------------------------------------------------------------- micrometer stand (cast-iron base, rubber-lined clamp on the frame)
  var base = S.rounded(72, 46, 12, 4, M.iron); base.rotation.x = -Math.PI / 2; base.position.set(11, -AXY * 1000 + 6, 0); G.add(base);
  function box(w, h, d, mat, x, y, z) { var m = S.mesh(new T.BoxGeometry(w, h, d), mat); m.position.set(x, y, z); G.add(m); return m; }
  box(12, 12, 15, M.iron, 11, -45, 0);
  [-1, 1].forEach(function (sg) { box(22, 20, 3, M.iron, 11, -31, sg * 6.1); box(20, 9, 0.5, M.rubber, 11, -29, sg * 4.35); });
  var cscr = S.mesh(new T.CylinderGeometry(1.4, 1.4, 6, 14), M.chrome); cscr.rotation.x = Math.PI / 2; cscr.position.set(11, -36, 10); G.add(cscr);
  var cknob = S.mesh(new T.CylinderGeometry(4.5, 4.5, 3.2, 6), M.black); cknob.rotation.x = Math.PI / 2; cknob.position.set(11, -36, 13.6); G.add(cknob);
  S.contact(0.11, 0.075, GX + 0.011, GZ, 0.55);

  // ---------------------------------------------------------------- the wire + its reel on the bench
  var wireMat = new T.MeshStandardMaterial({ color: WL[3], roughness: 0.28, metalness: 1 });
  var wire = S.mesh(new T.BufferGeometry(), wireMat, true, false); G.add(wire);
  var tagTex = S.canvasTex(256, 128, function (x, w, h) { x.fillStyle = '#f4efe2'; x.fillRect(0, 0, w, h); x.fillStyle = '#7a2f1b'; x.font = '700 ' + (WSYM.length > 3 ? 38 : 46) + 'px ' + FONT; x.textAlign = 'center'; x.fillText(WSYM, w / 2, 60);
    x.font = '500 28px ' + FONT; x.fillStyle = '#333'; x.fillText(SWG ? 'SWG ' + SWG : 'SWG wire', w / 2, 104); });
  var tag = new T.Mesh(new T.PlaneGeometry(9, 4.5), new T.MeshStandardMaterial({ map: tagTex, roughness: 0.9, side: T.DoubleSide })); G.add(tag);
  var wireShadow = S.contact(0.09, 0.03, 0, 0, 0.3);
  var BY = -AXY * 1000;                                          // the bench, in gauge mm
  var ARCH_Y = [BY + WD / 2, -46, -16, -2.2, -0.25, 0, -0.25, -2.2, -16, -46, BY + WD / 2], ARCH_Z = [72, 55, 33, 15, 5, 0, -5, -15, -33, -55, -72];
  function archPts(zs, lift) { return ARCH_Z.map(function (z, i) { var l = lift * (i === 0 || i === 10 ? 0.6 : 1); return new T.Vector3(WD / 2, ARCH_Y[i] + l, z + zs); }); }
  function lyingPts() { var out = []; for (var i = 0; i < 11; i++) out.push(new T.Vector3(78 + 7.5 * i, BY + WD / 2, 70 + 7 * Math.sin(i * 0.55))); return out; }
  function transit(k, zs) {   // bench -> held above the gauge -> lowered between the anvil and the spindle
    var LIFT = 42, a = lyingPts(), b = archPts(zs, LIFT);
    if (k < 0.58) { var t = k / 0.58; return a.map(function (q, i) { var v = new T.Vector3().lerpVectors(q, b[i], t); v.y += Math.sin(t * Math.PI) * 12; return v; }); }
    return archPts(zs, LIFT * (1 - (k - 0.58) / 0.42)); }
  function setWire(pts) { var c = new T.CatmullRomCurve3(pts); wire.geometry.dispose(); wire.geometry = new T.TubeGeometry(c, 180, WD / 2, 8, false);
    var tp = c.getPoint(0.06), tq = c.getPoint(0.09); tag.position.set(tp.x + 4.8, tp.y + 0.3, tp.z); tag.lookAt(G.localToWorld(new T.Vector3(tp.x + 4.8, tp.y + 0.3, tp.z + 10)));
    var mid = c.getPoint(0.5); G.updateMatrixWorld(true); var wm = G.localToWorld(mid.clone());
    wireShadow.position.set(wm.x, 0.0009, wm.z); wireShadow.rotation.z = st.wire === 'gauge' ? Math.PI / 2 : 0; st.wpts = pts; }
  var reel = new T.Group(); reel.position.set(0.19, 0, -0.17); S.scene.add(reel);
  [0.003, 0.033].forEach(function (y) { var f = S.mesh(new T.CylinderGeometry(0.024, 0.024, 0.003, 40), new T.MeshStandardMaterial({ color: 0x2b3a67, roughness: 0.5 })); f.position.y = y; reel.add(f); });
  var coilTex = S.canvasTex(512, 128, function (x, w, h) { x.fillStyle = WL[4]; x.fillRect(0, 0, w, h); for (var i = 0; i < h; i += 3) { x.fillStyle = i % 6 ? 'rgba(255,220,180,.35)' : 'rgba(80,30,10,.35)'; x.fillRect(0, i, w, 1.4); } });
  var coil = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.027, 40), new T.MeshStandardMaterial({ map: coilTex, roughness: 0.3, metalness: 0.9 })); coil.position.y = 0.018; reel.add(coil);
  S.contact(0.07, 0.07, 0.19, -0.17, 0.5);

  S.addApparatus('sg', G, 'Screw gauge', 'Micrometer screw gauge in a bench stand. Pitch ' + PS + ', ' + NDIV + ' thimble divisions: least count ' + LS + '.');
  S.addApparatus('thimble', thimble, 'Thimble', 'Turns with the spindle. ' + NDIV + ' divisions round it; one turn moves the spindle ' + PS + '.');
  S.addApparatus('ratchet', ratchet, 'Ratchet', 'Slips with a click once the faces grip, so every reading uses the same gentle pressure.');
  S.addApparatus('wire', wire, WNAME + (SWG ? ' (SWG ' + SWG + ')' : ''), 'The wire to measure. Its true diameter is hidden: you find it.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudLC = S.hudCard('Least count'), hudS = S.hudCard('Spindle'), hudN = S.hudCard('Readings');

  // ---------------------------------------------------------------- state -> 3D
  function raw() { return st.gap + ZR; }
  function place() { MOV.position.x = st.gap; SPIN.rotation.x = 2 * Math.PI * raw() / PITCH; }
  function wpt(x, y, z) { G.updateMatrixWorld(true); return G.localToWorld(new T.Vector3(x, y, z)); }
  function ratchetPt(g) { return wpt(g + RAT_END - 0.6, 0, 0); }
  var VIEWS = { sg: [[GX + 0.035, 0.125, GZ + 0.2], [GX + 0.032, 0.05, GZ]], act: [[GX + 0.17, 0.15, GZ + 0.24], [GX + 0.035, 0.05, GZ]],
    gap: [[GX + 0.022, AXY + 0.012, GZ + 0.045], [GX + 0.002, AXY - 0.002, GZ]], read: [[0, AXY + 0.003, GZ + 0.06], [0, AXY + 0.001, GZ]],
    lens: [[0, AXY + 0.0015, GZ + 0.032], [0, AXY + 0.0005, GZ]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] };
  function updViews() { var ex = GX + (SLV0 + raw()) / 1000; VIEWS.read[0][0] = VIEWS.read[1][0] = ex + 0.003; VIEWS.lens[0][0] = VIEWS.lens[1][0] = ex + 0.0025; }
  function sState() { if (st.wire === 'gauge' && Math.abs(st.gap - WD) < 1e-6) return 'wire'; if (st.gap < 1e-6) return 'closed'; return 'open'; }

  // ---------------------------------------------------------------- human actions
  function busy() { if (st.acting || S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function run(fn) { st.acting = true; S.render(); S.focus('act'); return Promise.resolve().then(fn).catch(function (e) { console.warn(e); })
    .then(function () { st.acting = false; place(); S.render(); }); }
  function clicks() { var pr = Promise.resolve(); [0, 1, 2].forEach(function () { pr = pr.then(function () { S.click(3400, 0.012, 0.08); return S.wait(130); }); }); return pr; }
  function turnTo(g1, ms) {   // fingers turn the ratchet (or the thimble); the screw advances one pitch a turn
    var g0 = st.gap; if (Math.abs(g1 - g0) < 1e-9) return Promise.resolve();
    var turns = Math.abs(g1 - g0) / PITCH, dur = ms || Math.min(2600, 700 + turns * 450);
    return S.hand.pinchMove(ratchetPt(g0), function (k) { return ratchetPt(g0 + (g1 - g0) * k); },
      function (k) { st.gap = g0 + (g1 - g0) * k; place(); if (S.hand.group.visible) S.hand.group.rotation.x = 0.15 + Math.sin(k * turns * Math.PI * 2) * 0.35; }, { mode: 'side', ms: dur, pose: 'grip' })
      .then(function () { st.gap = g1; place(); }); }
  function closeEmpty() {
    if (busy()) return Promise.resolve();
    if (st.wire === 'gauge') { S.say('Take the wire out first: the zero error is read with the faces touching each other.'); return Promise.resolve(); }
    if (sState() === 'closed') { S.say('The faces are already touching.'); return Promise.resolve(); }
    return run(function () { return turnTo(0).then(clicks).then(function () { updViews(); S.focus('lens');
      S.say('Click, click, click: the ratchet slips, so the faces touch with the right pressure. Read the thimble division on the datum line.'); }); });
  }
  function oneTurn() {
    if (busy()) return Promise.resolve();
    if (st.wire === 'gauge' && st.gap < WD + 0.6) { S.say('Open the gauge from the wire first.'); return Promise.resolve(); }
    var g1 = st.gap + PITCH <= 5 ? st.gap + PITCH : st.gap - PITCH;
    return run(function () { updViews(); return turnTo(g1, 1800).then(function () { st.turned = true; updViews(); S.focus('read');
      S.say('One full turn of the thimble: its edge moved by exactly one division of the sleeve scale, ' + PS + '. That is the pitch.'); }); });
  }
  function openGauge() {
    if (busy()) return Promise.resolve();
    if (st.gap >= OPEN - 1e-6) { S.say('The gauge is already open.'); return Promise.resolve(); }
    return run(function () { return turnTo(OPEN).then(function () { S.focus('gap'); }); });
  }
  function wireGrip(pts) { return wpt(pts[2].x, pts[2].y, pts[2].z + 0.6); }
  function placeWire() {
    if (busy()) return Promise.resolve();
    if (st.wire === 'gauge') { S.say('The wire is already between the faces.'); return Promise.resolve(); }
    if (st.gap < WD + 0.4) { S.say('Open the gauge first, so the wire fits between the anvil and the spindle.'); return Promise.resolve(); }
    var zs = ZS[st.zi];
    return run(function () { return S.hand.pinchMove(wireGrip(transit(0, zs)), function (k) { return wireGrip(transit(k, zs)); }, function (k) { setWire(transit(k, zs)); }, { mode: 'front', ms: 2100 })
      .then(function () { st.wire = 'gauge'; setWire(archPts(zs, 0)); S.focus('gap'); S.say('The wire lies across the anvil, square to the spindle.'); }); });
  }
  function removeWire() {
    if (busy()) return Promise.resolve();
    if (st.wire !== 'gauge') return Promise.resolve();
    var zs = ZS[st.zi];
    return run(function () { return (st.gap < OPEN ? turnTo(OPEN) : Promise.resolve()).then(function () {
      return S.hand.pinchMove(wireGrip(transit(1, zs)), function (k) { return wireGrip(transit(1 - k, zs)); }, function (k) { setWire(transit(1 - k, zs)); }, { mode: 'front', ms: 1900 }); })
      .then(function () { st.wire = 'bench'; setWire(lyingPts()); }); });
  }
  function slideWire() {
    if (busy()) return Promise.resolve();
    if (st.wire !== 'gauge') { S.say('Put the wire between the faces first.'); return Promise.resolve(); }
    if (st.gap < WD + 0.4) { S.say('Open the gauge a little first: never drag the wire through closed faces.'); return Promise.resolve(); }
    var z0 = ZS[st.zi], ni = (st.zi + 1) % ZS.length, z1 = ZS[ni];
    return run(function () { return S.hand.pinchMove(wireGrip(archPts(z0, 0)), function (k) { return wireGrip(archPts(z0 + (z1 - z0) * k, 0)); }, function (k) { setWire(archPts(z0 + (z1 - z0) * k, 0)); }, { mode: 'front', ms: 1500 })
      .then(function () { st.zi = ni; st.wk++; st.inp.psr = ''; st.inp.hsr = ''; setWire(archPts(z1, 0)); S.say('The wire now sits at a new place along its length. Close the gauge on it again.'); }); });
  }
  function closeOnWire() {
    if (busy()) return Promise.resolve();
    if (st.wire !== 'gauge') { S.say('Place the wire between the faces first.'); return Promise.resolve(); }
    if (sState() === 'wire') { S.say('The spindle is already on the wire. Read the scales.'); return Promise.resolve(); }
    return run(function () { return turnTo(WD).then(clicks).then(function () { st.placedFor = S.rows.length; updViews(); S.focus('read');
      S.say('The ratchet clicks: the spindle holds the wire gently. Read the sleeve and the thimble.'); }); });
  }

  // ---------------------------------------------------------------- reading checks (typed by the student; hints, never the answer)
  function num(s) { s = String(s === undefined ? '' : s).trim().replace(/−/g, '-').replace(',', '.'); if (!/^[-+]?(\d+\.?\d*|\.\d+)$/.test(s)) return NaN; return parseFloat(s); }
  function same(a, b) { return Math.abs(a - b) < 1e-6; }
  function submitLC() {
    var v = num(st.inp.lc);
    if (!isFinite(v)) { S.say('Type the least count as a number, in mm.'); return false; }
    if (same(v, LC)) { st.lcOk = true; S.say('Right: least count = pitch ÷ divisions = ' + PS + ' ÷ ' + NDIV + ' = ' + LS + '.'); S.render(); return true; }
    if (same(v, PITCH)) S.say(PS + ' is the pitch: the distance the spindle moves in one full turn. Divide it among the thimble divisions.');
    else if (same(v, NDIV) || same(v, 1 / NDIV)) S.say('Use millimetres: least count = pitch (mm) ÷ number of thimble divisions.');
    else S.say('Not yet. Least count = pitch ÷ number of divisions on the thimble.');
    S.render(); return false;
  }
  function submitZero() {
    var v = num(st.inp.zero); st.tries.zero++;
    if (sState() !== 'closed') { S.say('Close the faces with the ratchet first, with nothing between them.'); return false; }
    if (!isFinite(v)) { S.say('Type the zero error as a number in mm (with a minus sign if it is negative).'); return false; }
    if (same(v, ZR)) { st.zeroOk = true; S.say('Correct. Zero error = ' + (ZR > 0 ? '+' : '') + ZR.toFixed(2) + ' mm. It will be subtracted from every reading.'); S.render(); return true; }
    var d = Math.round(Math.abs(ZR) / LC);
    if (d && (same(Math.abs(v), d) || same(Math.abs(v), NDIV - d))) S.say('That is a division number. Multiply it by the least count to get millimetres.');
    else if (same(v, -ZR)) S.say('Check the sign. If the thimble zero is below the datum line when the faces touch, the zero error is positive; above it, negative.');
    else S.say(st.tries.zero > 1 ? 'Not yet. Use "Look through the lens". Find where the thimble zero is, and which thimble division is on the datum line. Zero error = divisions × ' + LS + '.' :
      'Not yet. With the faces touching, which thimble division is on the datum line, and is the thimble zero above or below it?');
    S.render(); return false;
  }
  function submitReading() {
    st.tries.read++;
    if (!st.zeroOk) { S.say('Find the zero error first (step 2).'); return false; }
    if (sState() !== 'wire') { S.say('Turn the ratchet until it clicks on the wire before you read.'); return false; }
    var m = num(st.inp.psr), v = num(st.inp.hsr);
    if (!isFinite(m) || !isFinite(v)) { S.say('Type both: the pitch scale reading in mm, and the thimble division on the datum line (a whole number).'); return false; }
    if (Math.round(v) !== v || v < 0 || v >= NDIV) { S.say('The thimble division is a whole number from 0 to ' + (NDIV - 1) + '.'); return false; }
    var mOk = same(m, PSR), vOk = v === HSR;
    if (mOk && vOk) {
      var obs = r6(m + v * LC), corr = r6(obs - ZR);
      if (!same(corr, KREAD)) console.warn('screw gauge: corrected reading', corr, 'differs from the kernel', KREAD);
      S.addRow({ psr: m, hsr: v, obs: obs, ze: ZR, corr: corr, at: ZS[st.zi] });
      st.inp.psr = ''; st.inp.hsr = ''; st.tries.read = 0;
      S.say('Recorded: ' + m.toFixed(1) + ' mm + ' + v + ' × ' + LS + ' = ' + obs.toFixed(2) + ' mm; corrected: ' + corr.toFixed(2) + ' mm.' + (S.rows.length < 3 ? ' Open the gauge and slide the wire to a new place.' : ''));
      S.render(); return true;
    }
    var msg = [];
    if (!mOk) { if (m > PSR + 1e-6 && same(m, PSR + PITCH)) msg.push('PSR: that mark is still under the thimble. Read the last mark you can see.');
      else if (m < PSR - 1e-6 && same(m, PSR - PITCH)) msg.push('PSR: look again beside the thimble edge. Marks below the datum line are the half millimetres.');
      else if (same(m * 10, PSR) || same(m / 10, PSR)) msg.push('PSR: type it in millimetres.');
      else msg.push('PSR: read the last sleeve mark the thimble edge has uncovered, counting the half-millimetre marks below the line.'); }
    else msg.push('PSR is right.');
    if (!vOk) { if (Math.abs(v - HSR) === 1) msg.push('HSR: close. Look straight at the datum line: which division is exactly on it?');
      else if (v === NDIV - HSR) msg.push('HSR: read the number printed on the thimble at the datum line, as it is printed.');
      else msg.push('HSR: follow the datum line onto the thimble and read the division that lies on it.' + (st.tries.read > 1 ? ' "Look through the lens" helps.' : '')); }
    else msg.push('HSR is right.');
    S.say(msg.join(' ')); S.render(); return false;
  }

  // ---------------------------------------------------------------- UI helpers
  function field(label, key, unit, onEnter) {
    var wrap = document.createElement('label'); wrap.style.cssText = 'display:flex;align-items:center;gap:8px;font-size:14px';
    var t = document.createElement('span'); t.textContent = label; t.style.flex = '1';
    var inp = document.createElement('input'); inp.type = 'text'; inp.inputMode = 'decimal'; inp.autocomplete = 'off'; inp.spellcheck = false; inp.id = 'sg_' + key;
    inp.value = st.inp[key] || ''; inp.setAttribute('aria-label', label);
    inp.style.cssText = 'width:92px;min-height:38px;padding:4px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:600 15px var(--f-mono);text-align:right';
    inp.addEventListener('input', function () { st.inp[key] = inp.value; });
    inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); onEnter(); } });
    var un = document.createElement('span'); un.textContent = unit || ''; un.style.cssText = 'width:26px;color:var(--mut)';
    wrap.appendChild(t); wrap.appendChild(inp); wrap.appendChild(un); return wrap;
  }
  function viewRow(u) { return u.row(u.button('Look through the lens', function () { updViews(); S.focus('lens'); }), u.button('Sleeve + thimble', function () { updViews(); S.focus('read'); }),
    u.button('Anvil and wire', function () { S.focus('gap'); }), u.button('Whole gauge', function () { S.focus('sg'); })); }
  function sgn(v) { return (v > 0 ? '+' : '') + v.toFixed(2); }

  setWire(lyingPts()); place();

  return {
    camera: { pos: [0.13, 0.2, 0.4], look: [0.035, 0.045, -0.03] },
    views: VIEWS,
    theory: { principle: 'The spindle is a fine screw. One full turn of the thimble moves it forward by one pitch, ' + PS + ', read on the sleeve. The thimble is divided into ' + NDIV + ' parts, so turning it by one division moves the spindle ' + fmt(PITCH) + ' ÷ ' + NDIV + ' = ' + LS + '.',
      formula: 'D = PSR + HSR × LC − zero error', formulaNote: 'LC = pitch ÷ number of thimble divisions = ' + PS + ' ÷ ' + NDIV + ' = ' + LS,
      more: ['PSR (pitch scale reading) is the last mark on the sleeve uncovered by the thimble edge; marks above the datum line are whole millimetres, marks below are the half millimetres. HSR is the thimble division lying on the datum line.',
        'Zero error: turn the ratchet until the faces touch. If the thimble zero is below the datum line, the error is positive (+n × LC); above it, negative. Corrected reading = observed − zero error.'],
      precautions: 'Always turn by the ratchet, never by the thimble, at the end: it slips at the same gentle pressure every time. Look straight at the datum line. Measure the wire at several places along its length (and in two perpendicular directions) and take the mean.' },
    book: { title: 'Expt. — Screw Gauge', lines: ['Aim: diameter of a thin wire' + (SAMPLE ? ' (' + WNAME.toLowerCase() + (SWG ? ', SWG ' + SWG : '') + ').' : '.'), 'Pitch = ' + PS + ',  ' + NDIV + ' thimble divisions', 'LC = pitch / ' + NDIV + ' = ' + LS, 'Zero error = …', 'D = PSR + HSR × LC − z.e.', 'Precautions: use the ratchet; no parallax.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'PSR (mm)', get: function (r) { return r.psr.toFixed(1); } },
        { label: 'HSR', get: function (r) { return String(r.hsr); } }, { label: 'Obs. (mm)', get: function (r) { return r.obs.toFixed(2); } },
        { label: 'z.e. (mm)', get: function (r) { return sgn(r.ze); } }, { label: 'D (mm)', get: function (r) { return r.corr.toFixed(2); } }] },
    result: function (rows) { if (!rows.length) return null; var m = S.fit.mean(rows.map(function (r) { return r.corr; }));
      return { label: 'Mean diameter D', value: m, unit: 'mm', digits: 3, truth: p.L * 1000, note: 'Mean of ' + rows.length + ' corrected readings (least count ' + LS + ').' }; },
    tol: (LC + 1e-9) / (p.L * 1000),
    resultNote: 'Each reading is good only to the least count, ' + LS + '. Your mean can differ from the true diameter by up to that much.',
    chips: ['How do I read the PSR?', 'How do I read the thimble?', 'What is the zero error?', 'Why use the ratchet?', 'Check my readings'],
    viva: [['With the faces touching, the thimble zero is 3 divisions below the datum line. The zero error is…', ['+' + fmt(3 * LC) + ' mm', '−' + fmt(3 * LC) + ' mm', '+' + fmt(30 * LC) + ' mm'], 0, 'Below the line means the gauge reads too much: +3 × ' + LS + '.'],
      ['Why do we turn the ratchet and not the thimble at the end?', ['It slips at a fixed gentle pressure', 'It turns faster', 'It reads the zero error'], 0, 'Equal, gentle pressure every time: the wire is not squeezed.']],
    askState: function () { return { least_count_mm: LC, pitch_mm: PITCH, thimble_divisions: NDIV, spindle: sState(), wire_place: st.wire, place_along_wire: st.zi + 1,
      least_count_found: st.lcOk, zero_error_found: st.zeroOk, typed_zero_error_mm: st.inp.zero || null, typed_psr_mm: st.inp.psr || null, typed_hsr: st.inp.hsr || null,
      readings_recorded: S.rows.length, note: 'The correct readings are not given to Ask Hoola. Guide the student to read them.' }; },

    steps: [
      { id: 'zero', title: 'Zero error', view: 'sg', render: function (u) {
          u.h2('Least count and zero error');
          u.p('First find what one thimble division is worth. Then bring the faces together with the ratchet and see whether the gauge reads zero.');
          var t1 = u.task('1. Least count', st.lcOk, st.lcOk ? 'LC = ' + LC.toFixed(2) + ' mm' : 'Turn the thimble once and watch its edge move along the sleeve (the pitch). Count the thimble divisions.');
          t1.add(u.button('Turn the thimble one full turn', oneTurn, false, st.acting));
          if (!st.lcOk) { t1.add(field('Least count', 'lc', 'mm', submitLC)); t1.add(u.button('Check', submitLC, true)); }
          var ss = sState(), closed = ss === 'closed';
          var t2 = u.task('2. Close the faces with the ratchet', closed, closed ? 'The faces touch; the ratchet clicked.' : (st.wire === 'gauge' ? 'The wire is between the faces: take it out first.' : 'The fingers turn the ratchet until it clicks.'));
          if (st.wire === 'gauge') t2.add(u.button('Take the wire out', removeWire, false, st.acting));
          t2.add(u.button(closed ? 'Closed' : 'Turn the ratchet', closeEmpty, !closed, closed || st.acting || st.wire === 'gauge'));
          var t3 = u.task('3. Read the zero error', st.zeroOk, st.zeroOk ? 'Zero error = ' + sgn(ZR) + ' mm' : 'Which thimble division is on the datum line? Positive if the thimble zero is below the line.');
          if (!st.zeroOk) { t3.add(field('Zero error', 'zero', 'mm', submitZero)); t3.add(u.button('Check', submitZero, true, !closed || st.acting)); }
          viewRow(u);
          u.note('Look straight at the datum line, not from above or below.');
          u.next('Next: measure the wire', st.lcOk && st.zeroOk);
        },
        ok: function () { return st.lcOk && st.zeroOk; },
        auto: function () {
          return oneTurn().then(function () { st.inp.lc = String(LC); submitLC(); return closeEmpty(); })
            .then(function () { st.inp.zero = String(ZR); submitZero(); }); } },
      { id: 'measure', title: 'Measure', view: 'sg', render: function (u) {
          u.h2('Measure the wire');
          var ss = sState(), n = S.rows.length, inG = st.wire === 'gauge';
          u.p('Reading ' + Math.min(n + 1, 3) + ' of 3, each at a different place along the wire.');
          var placed = inG && (n === 0 || st.wk > n);
          var tA = u.task('1. Open the gauge', ss === 'open' || ss === 'wire', ss === 'closed' ? 'Turn the thimble back a few turns.' : 'Open.');
          tA.add(u.button('Open the gauge', openGauge, ss === 'closed', ss !== 'closed' || st.acting));
          var tB = u.task(!inG || n === 0 ? '2. Put the wire between the anvil and the spindle' : '2. Slide the wire to a new place', placed,
            placed ? 'The wire lies across the anvil.' : (inG ? 'Open the gauge, then slide the wire along.' : 'Pick it up from the bench.'));
          if (!inG) tB.add(u.button('Place the wire', placeWire, ss === 'open', ss !== 'open' || st.acting));
          else if (!placed) tB.add(u.button('Slide the wire along', slideWire, ss === 'open', ss !== 'open' || st.acting));
          var tC = u.task('3. Turn the ratchet until it clicks', ss === 'wire', ss === 'wire' ? 'The spindle holds the wire gently.' : 'Always finish with the ratchet.');
          tC.add(u.button('Turn the ratchet', closeOnWire, placed && ss === 'open', !placed || ss !== 'open' || st.acting));
          var ready = ss === 'wire' && placed;
          var tD = u.task('4. Read and type', false, ready ? 'PSR = last sleeve mark the thimble has uncovered. HSR = thimble division on the datum line.' : (inG && !placed ? 'Recorded. Open the gauge and slide the wire for another reading.' : 'Close the spindle on the wire first.'));
          if (n < 3 || ready) { tD.add(field('Pitch scale reading (PSR)', 'psr', 'mm', submitReading)); tD.add(field('Thimble division (HSR)', 'hsr', '', submitReading));
            tD.add(u.button('Check and record', submitReading, true, !ready || st.acting)); }
          viewRow(u);
          u.h3('Observation table · zero error ' + sgn(ZR) + ' mm'); u.table();
          if (n >= 3) u.note('Three readings recorded. You may take more, or go on to the result.');
          u.next('Next: result', n >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          function one(i) { return openGauge().then(function () { return i === 0 ? placeWire() : slideWire(); }).then(closeOnWire)
            .then(function () { st.inp.psr = String(PSR); st.inp.hsr = String(HSR); submitReading(); }); }
          return [0, 1, 2].reduce(function (pr, i) { return pr.then(function () { return one(i); }); }, Promise.resolve()); } },
    ],

    ready: function () {
      if (document.fonts && document.fonts.load) document.fonts.load('600 40px "Public Sans"').then(function () { texes.forEach(function (t) { t.paint(); }); }).catch(function () {});
    },
    tick: function () {
      updViews(); place();
      hudLC.set(st.lcOk ? LC.toFixed(2) + ' mm' : '?');
      var ss = sState(); hudS.set(ss === 'wire' ? 'On the wire' : ss === 'closed' ? 'Faces touching' : 'Open');
      hudN.set(S.rows.length + ' of 3');
      var zl = 'Zero error = ' + (st.zeroOk ? sgn(ZR) + ' mm' : '…'); var bk = S.exp && S.exp.book; if (bk && bk.lines[3] !== zl) { bk.lines[3] = zl; S.book.draw(); }
    },
  };
});
