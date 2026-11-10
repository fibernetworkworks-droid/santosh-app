/* Prayogshala studio module: Vernier callipers (NCERT Class XI, Units and Measurement).
   A stainless 0-150 mm vernier calliper at TRUE size (main scale 1 mm, vernier 10 divisions = 9 mm, least count 0.1 mm),
   held level in a bench holder so its outside jaws close on a brass sphere resting on the bench.
   Numbers: K.gauge from kernels.js (kind 0) with the lab's params - the same MSR / vernier division / reading the server
   checks. The jaw is drawn exactly where the kernel's reading puts it (rounded to the least count), so the coinciding
   division really coincides. The student reads the scales and TYPES the zero error, MSR and VSD; nothing is shown for them. */
HoolaStudio.define('vernier-callipers', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.gauge;
  var lp = S.lab.params || {};
  var p = window.HoolaKernels.paramsFor('gauge', lp); p.kind = 0;
  if (lp.ze === undefined) p.ze = 0.0002;          // this calliper's own zero error (+0.2 mm, a slightly worn instrument)
  function r6(v) { return Math.round(v * 1e6) / 1e6; }
  var KV = K.view({}, p), KZ = K.view({}, Object.assign({}, p, { L: 0 }));
  var LC = r6(KV.lc * 1000);                                    // least count, mm
  var ZR = r6((KZ.main + KZ.div * KZ.lc) * 1000);              // zero reading with the jaws closed, mm
  var MSR = r6(KV.main * 1000), VSD = KV.div;                   // what the scales show on the sphere
  var OBS = r6(MSR + VSD * LC), DIA = r6(OBS - ZR);             // observed reading, jaw opening on the sphere (mm)
  var KREAD = r6(K.measure(p).reading * 1000);                  // the kernel's corrected reading, mm
  var FONT = '"Public Sans", Arial, Helvetica, sans-serif';
  var X0 = -0.06, Z0 = -0.03;                                   // world position of the main-scale zero (fixed jaw face)
  var OPEN = Math.max(32, Math.ceil(DIA + 8));                 // jaw opening when "open", mm
  // the object measured: from the variant's sample line (the brass sphere by default)
  var SAMPLE = ((S.lab.variant || {}).sample || '');
  var OB = (function () {
    var sm = SAMPLE.toLowerCase(), o = { kind: 'sphere', noun: 'sphere', name: 'Brass sphere', mat: M.brass, dot: 0x5b3d12 };
    if (/coin/.test(sm)) { var den = (SAMPLE.match(/₹\s*(\d+)/) || [])[1] || '1';
      o = { kind: 'coin', noun: 'coin', name: '₹' + den + ' coin', den: den, thick: { '1': 1.45, '2': 1.5, '5': 1.7, '10': 1.9 }[den] || 1.6,
        ring: /^(5|10)$/.test(den) ? 0xcfae55 : 0xc9ced2, core: den === '10' ? 0xc9ced2 : (den === '5' ? 0xcfae55 : 0xc9ced2) }; }
    else if (/cylinder|rod/.test(sm)) o = { kind: 'cylinder', noun: 'cylinder', name: (/alumin/.test(sm) ? 'Aluminium' : /steel/.test(sm) ? 'Steel' : 'Brass') + ' cylinder',
      mat: /alumin/.test(sm) ? M.alu : /steel/.test(sm) ? M.chrome : M.brass, H: 30, dot: 0x3a2a10 };
    else if (/marble/.test(sm)) o = { kind: 'sphere', noun: 'marble', name: 'Glass marble', glass: true, dot: 0x1d6e8c };
    else if (/ball bearing|steel ball/.test(sm)) o = { kind: 'sphere', noun: 'ball', name: 'Steel ball bearing', mat: M.chrome, dot: 0x40464c };
    else if (/bob/.test(sm)) o = { kind: 'sphere', noun: 'bob', name: 'Brass pendulum bob', mat: M.brass, dot: 0x5b3d12, hook: true };
    return o; })();
  var NOUN = OB.noun;

  var st = { gap: 12.0, locked: false, sphere: 'tray', turned: 0, lcOk: false, zeroOk: false, tries: { lc: 0, zero: 0, read: 0 },
    inp: { lc: '', zero: '', msr: '', vsd: '' }, acting: false };

  // ---------------------------------------------------------------- helpers (mm units inside the calliper group)
  var G = new T.Group(); G.scale.setScalar(0.001); G.position.set(X0, 0, Z0); S.scene.add(G);
  var SL = new T.Group(); G.add(SL);                            // the slider: origin on the moving jaw's measuring face
  var satin = new T.MeshStandardMaterial({ color: 0xd4d8db, roughness: 0.3, metalness: 0.85 });
  var satinEdge = new T.MeshStandardMaterial({ color: 0xc2c7cb, roughness: 0.24, metalness: 0.95 });
  function prism(pts, depth, mat, bv) {   // a flat steel part from an outline (x, y in mm), depth along z, centred
    bv = bv === undefined ? 0.2 : bv; var s = new T.Shape(); s.moveTo(pts[0][0], pts[0][1]);
    for (var i = 1; i < pts.length; i++) s.lineTo(pts[i][0], pts[i][1]); s.closePath();
    var g = new T.ExtrudeGeometry(s, { depth: Math.max(0.05, depth - 2 * bv), bevelEnabled: bv > 0, bevelThickness: bv, bevelSize: bv, bevelSegments: 2, curveSegments: 6 });
    g.translate(0, 0, -Math.max(0.05, depth - 2 * bv) / 2); return S.mesh(g, mat); }
  function box(w, h, d, mat, x, y, z, parent) { var m = S.mesh(new T.BoxGeometry(w, h, d), mat); m.position.set(x, y, z); (parent || G).add(m); return m; }
  function brushed(x, w, h, base) {   // satin-chrome background with fine brushing along the length
    x.fillStyle = base; x.fillRect(0, 0, w, h); var sd = 7;
    for (var i = 0; i < h; i += 2) { sd = (sd * 16807) % 2147483647; var a = (sd / 2147483647) * 0.06; x.fillStyle = 'rgba(' + (i % 4 ? '255,255,255' : '40,45,50') + ',' + a + ')'; x.fillRect(0, i, w, 1); } }
  function knurlTex() { return S.canvasTex(512, 64, function (x, w, h) { x.fillStyle = '#b9bec2'; x.fillRect(0, 0, w, h); x.fillStyle = '#5d646b';
    for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); }); }
  function printMat(tex) { return new T.MeshStandardMaterial({ map: tex, roughness: 0.42, metalness: 0.35 }); }
  var texes = [];
  function liveCanvas(w, h, draw) { var t = S.liveTex(w, h); t.anisotropy = 16; t.paint = function () { t.draw(draw); }; t.paint(); texes.push(t); return t; }

  // ---------------------------------------------------------------- beam with the main scale (mm), fixed jaws
  var beam = S.rounded(208, 16, 3.5, 0.9, satin); beam.position.set(88, 48, 0); G.add(beam);
  // fixed outside jaw (measuring face at x = 0) and fixed inside jaw, fused with the beam head
  var b = 0.2;
  var fjaw = prism([[-b, 2.4], [-b, 40.6], [-16, 40.6], [-16, 33], [-9, 21], [-3.4, 4.2], [-1.6, 2.2]], 3.2, satin); G.add(fjaw);
  var fin = prism([[-b, 55.4], [-b, 71.2], [-1.4, 72.2], [-3.2, 71.6], [-9.5, 55.4]], 2.8, satin); G.add(fin);
  // main scale in three printed tiles (64 px per mm), ticks pointing down to the vernier edge at y = 46.95
  var MS_Y0 = 46.95, MS_Y1 = 55.4, PX = 64;
  [[-3, 61], [61, 125], [125, 189]].forEach(function (span) {
    var w = Math.round((span[1] - span[0]) * PX), h = Math.round((MS_Y1 - MS_Y0) * PX);
    var tex = liveCanvas(w, h, function (x) {
      brushed(x, w, h, '#dadde0');
      var X = function (mm) { return (mm - span[0]) * PX; }, Y = function (mm) { return h - (mm - MS_Y0) * PX; };
      x.fillStyle = '#121416';
      for (var i = 0; i <= 150; i++) { if (i < span[0] - 1 || i > span[1] + 1) continue;
        var len = i % 10 === 0 ? 5.6 : i % 5 === 0 ? 4.2 : 3.0, lw = 0.13 * PX;
        x.fillRect(X(i) - lw / 2, Y(MS_Y0 + len), lw, len * PX);
        if (i % 10 === 0) { x.font = '600 ' + Math.round(2.5 * PX) + 'px ' + FONT; x.textAlign = 'center'; x.textBaseline = 'alphabetic'; x.fillText(String(i / 10), X(i), Y(MS_Y0 + 6.3)); } }
      x.font = '500 ' + Math.round(1.3 * PX) + 'px ' + FONT; x.textAlign = 'left';
      if (span[0] < 0) x.fillText('mm', X(1.2), Y(MS_Y0 + 6.6));
      if (span[0] > 100) { x.font = '600 ' + Math.round(1.6 * PX) + 'px ' + FONT; x.fillText('HOOLA LAB', X(153), Y(MS_Y0 + 5.2));
        x.font = '500 ' + Math.round(1.3 * PX) + 'px ' + FONT; x.fillText('0.1 mm', X(153), Y(MS_Y0 + 2.6)); }
    });
    var pl = new T.Mesh(new T.PlaneGeometry(span[1] - span[0], MS_Y1 - MS_Y0), printMat(tex)); pl.receiveShadow = true;
    pl.position.set((span[0] + span[1]) / 2, (MS_Y0 + MS_Y1) / 2, 1.762); G.add(pl);
  });

  // ---------------------------------------------------------------- the slider: moving jaws, vernier plate, thumb wheel, lock screw
  var mjaw = prism([[b, 2.4], [b, 40.6], [16, 40.6], [16, 33], [9, 21], [3.4, 4.2], [1.6, 2.2]], 3.2, satin); SL.add(mjaw);
  var mIn = prism([[b, 55.4], [b, 71.2], [1.4, 72.2], [3.2, 71.6], [9.5, 55.4]], 2.8, satin); SL.add(mIn);
  box(16, 3.0, 6.0, satinEdge, 8, 38.6, 0, SL);            // bottom bar (wraps under the beam)
  box(30, 2.6, 6.0, satinEdge, 15, 57.3, 0, SL);           // top bar
  box(30, 16.4, 1.1, satinEdge, 15, 48.2, -2.4, SL);       // back plate
  // front piece with the bevelled vernier edge: profile in (z, y), extruded along x
  (function () { var s = new T.Shape(); s.moveTo(1.85, 40.3); s.lineTo(2.4, 40.3); s.lineTo(2.4, 44.0); s.lineTo(1.86, 46.85); s.closePath();
    var g = new T.ExtrudeGeometry(s, { depth: 33, bevelEnabled: false }); var m = S.mesh(g, satin); m.rotation.y = -Math.PI / 2; m.position.x = 30; SL.add(m); })();
  // vernier graduations on the bevel (80 px per mm): zero at x = ZR from the jaw face, 10 divisions in 9 mm
  var VX0 = -3, VX1 = 30, VPX = 80, BEV = Math.hypot(2.85, 0.54), bevA = Math.atan2(0.54, 2.85);
  var vTex = liveCanvas((VX1 - VX0) * VPX, Math.round(BEV * VPX), function (x, w, h) {
    brushed(x, w, h, '#dfe2e4'); x.fillStyle = '#121416';
    for (var k = 0; k <= 10; k++) { var xx = (ZR + k * 0.9 - VX0) * VPX, len = (k % 5 === 0 ? 2.4 : 1.6) * VPX, lw = 0.13 * VPX; x.fillRect(xx - lw / 2, 0, lw, len); } });
  var vPlane = new T.Mesh(new T.PlaneGeometry(VX1 - VX0, BEV), printMat(vTex));
  vPlane.rotation.x = -bevA; vPlane.position.set((VX0 + VX1) / 2, (46.85 + 44.0) / 2, (1.86 + 2.4) / 2 + 0.012); SL.add(vPlane);
  var nTex = liveCanvas((VX1 - VX0) * VPX, Math.round(3.7 * VPX), function (x, w, h) {
    brushed(x, w, h, '#dfe2e4'); x.fillStyle = '#121416'; x.textAlign = 'center'; x.textBaseline = 'top';
    x.font = '600 ' + Math.round(1.3 * VPX) + 'px ' + FONT; [0, 5, 10].forEach(function (k) { x.fillText(String(k), (ZR + k * 0.9 - VX0) * VPX, 0.15 * VPX); });
    x.font = '500 ' + Math.round(0.95 * VPX) + 'px ' + FONT; x.textAlign = 'left'; x.fillText('0.1 mm', (13.5 - VX0) * VPX, 1.9 * VPX); });
  var nPlane = new T.Mesh(new T.PlaneGeometry(VX1 - VX0, 3.7), printMat(nTex)); nPlane.position.set((VX0 + VX1) / 2, 40.3 + 3.7 / 2, 2.412); SL.add(nPlane);
  // fine-adjust thumb wheel on a bracket, rolling on the underside of the beam
  var kn = knurlTex(); kn.wrapS = T.RepeatWrapping; kn.repeat.set(3, 1);
  var wheel = S.mesh(new T.CylinderGeometry(4.2, 4.2, 2.6, 48), [new T.MeshStandardMaterial({ map: kn, roughness: 0.4, metalness: 0.8 }), satinEdge, satinEdge]);
  wheel.rotation.x = Math.PI / 2; wheel.position.set(23, 35.7, 0); SL.add(wheel);
  box(10, 7, 0.7, satinEdge, 23, 36.4, -1.75, SL);   // bracket behind the wheel; the knurled rim stays in view for the thumb
  // locking screw on the top bar
  var lockG = new T.Group(); lockG.position.set(17, 58.6, 0); SL.add(lockG);
  var neck = S.mesh(new T.CylinderGeometry(1.3, 1.3, 1.4, 20), satinEdge); neck.position.y = 0.7; lockG.add(neck);
  var lockHead = S.mesh(new T.CylinderGeometry(3.0, 3.0, 2.6, 36), [new T.MeshStandardMaterial({ map: kn, roughness: 0.4, metalness: 0.8 }), satinEdge, satinEdge]); lockHead.position.y = 2.7; lockG.add(lockHead);
  // depth rod: runs inside the beam, comes out of its right end as the jaws open
  var rod = box(160, 1.4, 0.9, satinEdge, 32 + 80, 48.2, -0.6, SL);

  // ---------------------------------------------------------------- bench holder (cast-iron base, clamp on the beam end)
  var HX = 177;
  var hb = S.rounded(44, 30, 9, 3, M.iron); hb.rotation.x = -Math.PI / 2; hb.position.set(HX, 4.5, 0); G.add(hb);
  var post = S.mesh(new T.CylinderGeometry(4, 4.6, 28, 28), M.chrome); post.position.set(HX, 23, 0); G.add(post);
  box(16, 4, 11, M.iron, HX, 37.9, 0);
  [-1, 1].forEach(function (sg) { box(16, 22, 3, M.iron, HX, 48.5, sg * 3.6); box(15, 15, 0.3, M.rubber, HX, 48, sg * 1.95); });
  var cs = S.mesh(new T.CylinderGeometry(1.4, 1.4, 5, 16), M.chrome); cs.rotation.x = Math.PI / 2; cs.position.set(HX, 52, 7.3); G.add(cs);
  var ck = S.mesh(new T.CylinderGeometry(4.2, 4.2, 3, 6), M.black); ck.rotation.x = Math.PI / 2; ck.position.set(HX, 52, 10.3); G.add(ck);
  S.contact(0.075, 0.055, X0 + HX / 1000, Z0, 0.55);
  S.contact(0.19, 0.03, X0 + 0.075, Z0, 0.22);

  // ---------------------------------------------------------------- brass sphere, tray
  var TX = 0.165, TZ = 0.07, TRAY_TOP = 0.009;
  var tray = S.rounded(0.07, 0.06, 0.009, 0.006, M.wood); tray.rotation.x = -Math.PI / 2; tray.position.set(TX, 0.0045, TZ); S.scene.add(tray);
  var felt = S.mesh(new T.PlaneGeometry(0.06, 0.05), new T.MeshStandardMaterial({ color: 0x24543d, roughness: 1 })); felt.rotation.x = -Math.PI / 2; felt.position.set(TX, TRAY_TOP + 0.0002, TZ); S.scene.add(felt);
  S.contact(0.1, 0.09, TX, TZ, 0.5);
  var RS = DIA / 2000;                                         // object radius (half the measured width) in m
  var ball = new T.Group(); S.scene.add(ball);
  var spin = new T.Group(); ball.add(spin);                     // turned by the hand between readings
  var HB = RS, HT = RS, ROT_TRAY = 0, ROT_JAW = 0;              // centre height on the bench (in the jaws) and on the tray; tilt about x
  if (OB.kind === 'coin') {
    var TH = OB.thick / 1000, FONTV = '"Public Sans", Arial, sans-serif';
    var faceTex = S.canvasTex(256, 256, function (x, w, h) { var c = w / 2;
      var gr = x.createRadialGradient(c * 0.8, c * 0.7, 10, c, c, c); var col = '#' + OB.core.toString(16).padStart(6, '0');
      x.fillStyle = '#' + OB.ring.toString(16).padStart(6, '0'); x.beginPath(); x.arc(c, c, c, 0, 7); x.fill();
      x.fillStyle = col; x.beginPath(); x.arc(c, c, OB.den === '10' ? c * 0.7 : c, 0, 7); x.fill();
      gr.addColorStop(0, 'rgba(255,255,255,0.25)'); gr.addColorStop(1, 'rgba(0,0,0,0.12)'); x.fillStyle = gr; x.beginPath(); x.arc(c, c, c, 0, 7); x.fill();
      x.strokeStyle = 'rgba(60,60,60,0.45)'; x.lineWidth = 4; x.beginPath(); x.arc(c, c, c - 10, 0, 7); x.stroke();
      x.fillStyle = 'rgba(55,55,60,0.75)'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.font = '700 92px ' + FONTV; x.fillText('₹' + OB.den, c, c + 4); });
    var edgeM = new T.MeshStandardMaterial({ color: OB.ring, roughness: 0.35, metalness: 0.9 }), faceM = new T.MeshStandardMaterial({ map: faceTex, roughness: 0.35, metalness: 0.75 });
    var bm = S.mesh(new T.CylinderGeometry(RS, RS, TH, 64), [edgeM, faceM, faceM]); spin.add(bm);
    HB = RS; HT = TH / 2; ROT_JAW = Math.PI / 2; ROT_TRAY = 0;   // lies flat on the felt, stands on its rim between the jaws
  } else if (OB.kind === 'cylinder') {
    var CH = OB.H / 1000;
    var bm = S.mesh(new T.CylinderGeometry(RS, RS, CH, 64), OB.mat); spin.add(bm);
    var dot = S.mesh(new T.CircleGeometry(RS * 0.12, 16), new T.MeshStandardMaterial({ color: OB.dot, roughness: 0.7 }));
    dot.position.set(0, CH * 0.25, RS * 1.001); spin.add(dot);
    HB = HT = CH / 2;
  } else {
    var bmat = OB.glass ? new T.MeshPhysicalMaterial({ color: 0xbfe6ef, roughness: 0.04, metalness: 0, transparent: true, opacity: 0.55, clearcoat: 1, envMapIntensity: 1.5 }) : OB.mat;
    var bm = S.mesh(new T.SphereGeometry(RS, 64, 48), bmat); spin.add(bm);
    if (OB.glass) { var swirl = S.mesh(new T.TorusGeometry(RS * 0.45, RS * 0.12, 10, 32, Math.PI * 1.4), new T.MeshStandardMaterial({ color: OB.dot, roughness: 0.4 })); swirl.rotation.set(0.6, 0.3, 0); spin.add(swirl); }
    else { var dot = S.mesh(new T.CircleGeometry(RS * 0.07, 16), new T.MeshStandardMaterial({ color: OB.dot, roughness: 0.7 }));   // a tiny punch mark, so a turn shows
      dot.position.set(0, RS * 0.62, RS * 0.785); dot.lookAt(0, RS * 1.24, RS * 1.57); spin.add(dot); }
    if (OB.hook) { var hk = S.mesh(new T.TorusGeometry(RS * 0.16, RS * 0.035, 8, 20), M.brass); hk.position.y = RS * 1.1; spin.add(hk); }
  }
  var ballShadow = S.contact(0.04, 0.04, TX, TZ, 0.5);
  var TRAY_POS = new T.Vector3(TX - 0.01, TRAY_TOP + HT, TZ);
  var JAW_POS = new T.Vector3(X0 + DIA / 2000, HB, Z0);
  function tilt(k) { ball.rotation.x = ROT_TRAY + (ROT_JAW - ROT_TRAY) * k; }   // 0 = as on the tray, 1 = as between the jaws
  ball.position.copy(TRAY_POS); tilt(0);

  S.addApparatus('vc', G, 'Vernier callipers', 'Stainless steel, 0–150 mm. Main scale in mm; vernier of 10 divisions = 9 mm, so the least count is 0.1 mm.');
  S.addApparatus('ball', ball, OB.name, 'The object to measure. Its true diameter is hidden: you find it.');
  S.addApparatus('tray', tray, 'Felt tray', 'Keeps the ' + NOUN + ' from rolling off the bench.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudLC = S.hudCard('Least count'), hudJ = S.hudCard('Jaws'), hudN = S.hudCard('Readings');

  // ---------------------------------------------------------------- state -> 3D
  function place() {
    SL.position.x = st.gap;
    wheel.rotation.y = -st.gap / 4.2;                          // the wheel rolls along the beam
    lockHead.rotation.y = st.locked ? 1.3 : 0;
    var low = ball.position.y - (Math.abs(ball.rotation.x - ROT_JAW) < 1e-6 ? HB : HT);
    ballShadow.position.set(ball.position.x, 0.0009 + (low > 0.004 ? TRAY_TOP : 0), ball.position.z);
    var hgt = Math.max(0, low); ballShadow.material.opacity = Math.max(0.12, 0.5 - hgt * 6);
  }
  function wpt(x, y, z) { G.updateMatrixWorld(true); return G.localToWorld(new T.Vector3(x, y, z)); }
  function wheelPt(gap) { return wpt(gap + 23, 35.7, 1.6); }
  var VIEWS = { act: [[X0 - 0.1, 0.13, Z0 + 0.21], [X0 + 0.035, 0.028, Z0]], vc: [[X0 + 0.07, 0.085, Z0 + 0.26], [X0 + 0.07, 0.035, Z0]], jaws: [[X0 + 0.02, 0.04, Z0 + 0.13], [X0 + 0.018, 0.024, Z0]],
    scale: [[0, 0.049, Z0 + 0.05], [0, 0.0475, Z0]], lens: [[0, 0.0478, Z0 + 0.03], [0, 0.0468, Z0]],
    tray: [[TX + 0.02, 0.09, TZ + 0.17], [TX, 0.01, TZ]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] };
  function updViews() { var vx = X0 + (st.gap + ZR + 4.5) / 1000;
    VIEWS.scale[0][0] = vx - 0.004; VIEWS.scale[1][0] = vx - 0.004; VIEWS.lens[0][0] = vx; VIEWS.lens[1][0] = vx; }
  function jawState() { if (st.sphere === 'jaws' && Math.abs(st.gap - DIA) < 1e-6) return 'sphere'; if (st.gap < 1e-6) return 'closed'; return 'open'; }

  // ---------------------------------------------------------------- human actions (every one done by the gloved hand)
  function busy() { if (st.acting || S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function run(fn) { st.acting = true; S.render(); S.focus('act'); return Promise.resolve().then(fn).catch(function (e) { console.warn(e); })
    .then(function () { st.acting = false; place(); S.render(); }); }
  function slideTo(g1, ms) {   // the thumb pushes the fine-adjust wheel; the slider follows
    var g0 = st.gap; if (Math.abs(g1 - g0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(wheelPt(g0), function (k) { return wheelPt(g0 + (g1 - g0) * k); }, function (k) { st.gap = g0 + (g1 - g0) * k; place(); }, { mode: 'front', ms: ms || 1300 })
      .then(function () { st.gap = g1; place(); }); }
  function unlock() { if (!st.locked) return Promise.resolve(); return S.hand.tap(lockHead).then(function () { st.locked = false; place(); }); }
  function lock() { return S.hand.tap(lockHead).then(function () { st.locked = true; place(); S.click(1800, 0.02); }); }

  function closeEmpty() {
    if (busy()) return Promise.resolve();
    if (st.sphere === 'jaws') { S.say('Take the ' + NOUN + ' out of the jaws first: the zero error is read with the jaws closed on nothing.'); return Promise.resolve(); }
    return run(function () { return unlock().then(function () { return slideTo(0, 1100); }).then(lock).then(function () {
      updViews(); S.focus('lens'); S.say('The jaws are closed and locked. Read the vernier: where is its zero, and which vernier line meets a main-scale line exactly?'); }); });
  }
  function openJaws() {
    if (busy()) return Promise.resolve();
    if (st.gap >= OPEN - 0.01) { S.say('The jaws are already open.'); return Promise.resolve(); }
    return run(function () { return unlock().then(function () { return slideTo(OPEN, 1200); }).then(function () { S.focus('jaws'); }); });
  }
  function placeSphere() {
    if (busy()) return Promise.resolve();
    if (st.sphere === 'jaws') { S.say('The ' + NOUN + ' is already between the jaws.'); return Promise.resolve(); }
    if (st.gap < DIA + 2) { S.say('Open the jaws first: the ' + NOUN + ' will not fit between them.'); return Promise.resolve(); }
    var a = TRAY_POS.clone(), p1 = TRAY_POS.clone().setY(0.05), p2 = JAW_POS.clone().setZ(Z0 + 0.05), p3 = JAW_POS.clone();
    function path(k) { var q = new T.Vector3(); if (k < 0.25) return q.lerpVectors(a, p1, k / 0.25); if (k < 0.72) return q.lerpVectors(p1, p2, (k - 0.25) / 0.47); return q.lerpVectors(p2, p3, (k - 0.72) / 0.28); }
    var front = new T.Vector3(0, 0, RS);
    return run(function () {
      return S.hand.pinchMove(a.clone().add(front), function (k) { return path(k).add(front); }, function (k) { ball.position.copy(path(k)); tilt(Math.min(1, Math.max(0, (k - 0.25) / 0.47))); place(); }, { mode: 'front', ms: 1900 })
        .then(function () { ball.position.copy(JAW_POS); tilt(1); st.sphere = 'jaws'; place();
          S.say(OB.kind === 'coin' ? 'The coin stands on its rim between the open jaws, touching the fixed jaw.' : 'The ' + NOUN + ' rests on the bench between the open jaws, touching the fixed jaw.'); }); });
  }
  function takeOut() {
    if (busy()) return Promise.resolve();
    if (st.sphere !== 'jaws') return Promise.resolve();
    var go = function () { var a = ball.position.clone(), p1 = a.clone().setZ(Z0 + 0.05), p2 = TRAY_POS.clone().setY(0.05), p3 = TRAY_POS.clone();
      function path(k) { var q = new T.Vector3(); if (k < 0.28) return q.lerpVectors(a, p1, k / 0.28); if (k < 0.75) return q.lerpVectors(p1, p2, (k - 0.28) / 0.47); return q.lerpVectors(p2, p3, (k - 0.75) / 0.25); }
      var front = new T.Vector3(0, 0, RS);
      return S.hand.pinchMove(a.clone().add(front), function (k) { return path(k).add(front); }, function (k) { ball.position.copy(path(k)); tilt(1 - Math.min(1, Math.max(0, (k - 0.28) / 0.47))); place(); }, { mode: 'front', ms: 1700 })
        .then(function () { ball.position.copy(TRAY_POS); tilt(0); st.sphere = 'tray'; place(); }); };
    return run(function () { return (st.gap < DIA + 2 ? unlock().then(function () { return slideTo(OPEN, 900); }) : Promise.resolve()).then(go); });
  }
  function turnSphere() {
    if (busy()) return Promise.resolve();
    if (st.sphere !== 'jaws') { S.say('Put the ' + NOUN + ' between the jaws first.'); return Promise.resolve(); }
    if (st.gap < DIA + 2) { S.say('Open the jaws a little first, so the ' + NOUN + ' can turn freely.'); return Promise.resolve(); }
    var r0 = spin.rotation.clone(), fp = ball.position.clone().add(new T.Vector3(0, 0, OB.kind === 'coin' ? OB.thick / 2000 : RS));
    function turnAt(k) { if (OB.kind === 'sphere') spin.rotation.set(r0.x + 1.1 * k, r0.y + 0.8 * k, r0.z); else spin.rotation.set(r0.x, r0.y + 1.1 * k, r0.z); }
    return run(function () { return S.hand.pinchMove(fp, function () { return fp; }, turnAt, { mode: 'front', ms: 1100 })
      .then(function () { st.turned++; st.inp.msr = ''; st.inp.vsd = ''; S.say((OB.kind === 'coin' ? 'Coin turned on its rim' : OB.kind === 'cylinder' ? 'Cylinder turned about its axis' : NOUN.charAt(0).toUpperCase() + NOUN.slice(1) + ' turned') + ' to a new position. Now close the jaws on it again.'); }); });
  }
  function closeOnSphere() {
    if (busy()) return Promise.resolve();
    if (st.sphere !== 'jaws') { S.say('Place the ' + NOUN + ' between the jaws first.'); return Promise.resolve(); }
    if (jawState() === 'sphere') { S.say('The jaws are already closed on the ' + NOUN + '. Read the scales.'); return Promise.resolve(); }
    return run(function () { return unlock().then(function () { return slideTo(DIA, 1400); }).then(lock).then(function () {
      updViews(); S.focus('scale'); S.say('The jaws touch the ' + NOUN + ' gently and the screw is locked. Read the main scale and the vernier.'); }); });
  }

  // ---------------------------------------------------------------- reading checks (the student types; hints, never the answer)
  function num(s) { s = String(s === undefined ? '' : s).trim().replace(/−/g, '-').replace(',', '.'); if (!/^[-+]?(\d+\.?\d*|\.\d+)$/.test(s)) return NaN; return parseFloat(s); }
  function same(a, b) { return Math.abs(a - b) < 1e-6; }
  function submitLC() {
    var v = num(st.inp.lc); st.tries.lc++;
    if (!isFinite(v)) { S.say('Type the least count as a number, in mm.'); return false; }
    if (same(v, LC)) { st.lcOk = true; S.say('Right: least count = 1 MSD − 1 VSD = 1 mm − 0.9 mm = 0.1 mm.'); S.render(); return true; }
    if (same(v, 1)) S.say('1 mm is one main-scale division. The least count is the difference between one main-scale and one vernier division.');
    else if (same(v, 0.9)) S.say('0.9 mm is one vernier division (10 VSD = 9 mm). Least count = 1 MSD − 1 VSD.');
    else S.say('Not yet. 10 vernier divisions cover 9 main-scale divisions. Work out 1 MSD − 1 VSD.');
    S.render(); return false;
  }
  function submitZero() {
    var v = num(st.inp.zero); st.tries.zero++;
    if (jawState() !== 'closed') { S.say('Close the jaws on nothing first: the zero error is read with the jaws touching each other.'); return false; }
    if (!isFinite(v)) { S.say('Type the zero error as a number in mm (with a minus sign if it is negative).'); return false; }
    if (same(v, ZR)) { st.zeroOk = true; S.say('Correct. Zero error = ' + (ZR > 0 ? '+' : '') + ZR.toFixed(1) + ' mm. It will be subtracted from every reading.'); S.render(); return true; }
    var d = Math.round(Math.abs(ZR) / LC);
    if (same(Math.abs(v), d) && d) S.say('That is a division number. Multiply the coinciding division by the least count to get millimetres.');
    else if (same(v, -ZR)) S.say('Check the sign. If the vernier zero sits to the right of the main-scale zero, the zero error is positive; to the left, it is negative.');
    else S.say(st.tries.zero > 1 ? 'Not yet. Use "Look through the lens". With the jaws closed, find the one vernier line that lines up exactly with a main-scale line. Zero error = that division × 0.1 mm.' :
      'Not yet. Look at the vernier zero against the main-scale zero, and at which vernier line meets a main-scale line exactly.');
    S.render(); return false;
  }
  function submitReading() {
    st.tries.read++;
    if (!st.zeroOk) { S.say('Find the zero error first (step 2).'); return false; }
    if (jawState() !== 'sphere' || !st.locked) { S.say('Close the jaws on the ' + NOUN + ' and lock them before you read.'); return false; }
    var m = num(st.inp.msr), v = num(st.inp.vsd);
    if (!isFinite(m) || !isFinite(v)) { S.say('Type both: the main scale reading in mm, and the coinciding vernier division (a whole number).'); return false; }
    if (Math.round(v) !== v || v < 0 || v > 10) { S.say('The vernier division is a whole number from 0 to 9.'); return false; }
    var mOk = same(m, MSR), vOk = v === VSD;
    if (mOk && vOk) {
      var obs = r6(m + v * LC), corr = r6(obs - ZR);
      if (!same(corr, KREAD)) console.warn('vernier: corrected reading', corr, 'differs from the kernel', KREAD);
      S.addRow({ msr: m, vsd: v, obs: obs, ze: ZR, corr: corr, pos: st.turned });
      st.inp.msr = ''; st.inp.vsd = ''; st.tries.read = 0;
      S.say('Recorded: ' + m.toFixed(0) + ' mm + ' + v + ' × 0.1 mm = ' + obs.toFixed(1) + ' mm; corrected for zero error: ' + corr.toFixed(1) + ' mm.' + (S.rows.length < 3 ? ' Turn the ' + NOUN + ' for the next reading.' : ''));
      S.render(); return true;
    }
    var msg = [];
    if (!mOk) { if (same(m, MSR + 1)) msg.push('MSR: the vernier zero has not reached that main-scale line yet. MSR is the last mm mark before the vernier zero.');
      else if (same(m * 10, MSR)) msg.push('MSR: type it in millimetres, not centimetres.');
      else if (Math.abs(m - MSR) < 1) msg.push('MSR is a whole number of millimetres: the last mark before the vernier zero.');
      else msg.push('MSR: find the vernier zero (the line marked 0 on the sliding jaw) and read the last main-scale mark to its left.'); }
    else msg.push('MSR is right.');
    if (!vOk) { if (Math.abs(v - VSD) === 1) msg.push('VSD: close, but look again at the lines on both sides. Only one lines up exactly.');
      else msg.push('VSD: run your eye along the vernier and find the one line that is exactly in line with a main-scale line.' + (st.tries.read > 1 ? ' "Look through the lens" helps.' : '')); }
    else msg.push('VSD is right.');
    S.say(msg.join(' ')); S.render(); return false;
  }

  // ---------------------------------------------------------------- UI helpers (text boxes for the readings)
  function field(label, key, unit, onEnter) {
    var wrap = document.createElement('label'); wrap.style.cssText = 'display:flex;align-items:center;gap:8px;font-size:14px';
    var t = document.createElement('span'); t.textContent = label; t.style.flex = '1';
    var inp = document.createElement('input'); inp.type = 'text'; inp.inputMode = 'decimal'; inp.autocomplete = 'off'; inp.spellcheck = false; inp.id = 'vc_' + key;
    inp.value = st.inp[key] || ''; inp.setAttribute('aria-label', label);
    inp.style.cssText = 'width:92px;min-height:38px;padding:4px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:600 15px var(--f-mono);text-align:right';
    inp.addEventListener('input', function () { st.inp[key] = inp.value; });
    inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); onEnter(); } });
    var un = document.createElement('span'); un.textContent = unit || ''; un.style.cssText = 'width:26px;color:var(--mut)';
    wrap.appendChild(t); wrap.appendChild(inp); wrap.appendChild(un); return wrap;
  }
  function viewRow(u) { return u.row(u.button('Look through the lens', function () { updViews(); S.focus('lens'); }), u.button('Main scale + vernier', function () { updViews(); S.focus('scale'); }),
    u.button('Whole callipers', function () { S.focus('vc'); })); }
  function f1(v) { return S.fmt(v, 1); }
  function sgn(v) { return (v > 0 ? '+' : '') + v.toFixed(1); }

  return {
    camera: { pos: [0.11, 0.2, 0.46], look: [0.03, 0.03, -0.01] },
    views: VIEWS,
    theory: { principle: 'The vernier scale slides along the main scale. 10 vernier divisions are exactly as long as 9 main-scale divisions, so each vernier division is 0.1 mm shorter than a millimetre. Where a vernier line lines up with a main-scale line, its number tells you how many tenths of a millimetre to add.',
      formula: 'D = MSR + VSD × LC − zero error', formulaNote: 'LC = 1 MSD − 1 VSD = 1 mm − 0.9 mm = 0.1 mm',
      more: ['MSR is the last main-scale mark (in mm) before the vernier zero. VSD is the number of the vernier line that coincides with a main-scale line.',
        'Zero error: close the jaws on nothing. If the vernier zero is to the right of the main zero, the error is positive (+n × LC); to the left, negative. The corrected reading = observed reading − zero error.'],
      precautions: 'Close the jaws gently with the thumb wheel; do not squeeze the ' + NOUN + '. Lock the screw before reading. Look straight at the scales to avoid parallax. Take readings in different positions of the ' + NOUN + ' and use the mean.' },
    book: { title: 'Expt. — Vernier Callipers', lines: ['Aim: diameter of a ' + OB.name.replace(/^[A-Z]/, function (c) { return c.toLowerCase(); }) + '.', '1 MSD = 1 mm,  10 VSD = 9 MSD', 'LC = 1 MSD − 1 VSD = 0.1 mm', 'Zero error = ' + (st.zeroOk ? sgn(ZR) + ' mm' : '…'), 'D = MSR + VSD × LC − z.e.', 'Precautions: no parallax, gentle grip.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'MSR (mm)', get: function (r) { return r.msr.toFixed(0); } },
        { label: 'VSD', get: function (r) { return String(r.vsd); } }, { label: 'Obs. (mm)', get: function (r) { return r.obs.toFixed(1); } },
        { label: 'z.e. (mm)', get: function (r) { return sgn(r.ze); } }, { label: 'D (mm)', get: function (r) { return r.corr.toFixed(1); } }] },
    result: function (rows) { if (!rows.length) return null; var m = S.fit.mean(rows.map(function (r) { return r.corr; }));
      return { label: 'Mean diameter D', value: m, unit: 'mm', digits: 2, truth: p.L * 1000, note: 'Mean of ' + rows.length + ' corrected readings (least count 0.1 mm).' }; },
    tol: (LC + 1e-9) / (p.L * 1000),
    resultNote: 'A single reading is good only to the least count, 0.1 mm. Your mean can differ from the true value by up to that much.',
    chips: ['How do I read the MSR?', 'How do I find the coinciding division?', 'What is zero error?', 'Why is the least count 0.1 mm?', 'Check my readings'],
    viva: [['The vernier zero lies to the right of the main zero when the jaws are closed. The zero error is…', ['Positive', 'Negative', 'Zero'], 0, 'The instrument reads too much, so the error is positive and is subtracted.'],
      ['10 VSD = 9 MSD and 1 MSD = 1 mm. One VSD is…', ['0.9 mm', '1.1 mm', '0.1 mm'], 0, '9 mm ÷ 10 = 0.9 mm.']],
    askState: function () { return { least_count_mm: LC, jaws: jawState(), screw_locked: st.locked, sphere_place: st.sphere, sphere_positions_used: st.turned + 1,
      least_count_found: st.lcOk, zero_error_found: st.zeroOk, typed_zero_error_mm: st.inp.zero || null, typed_msr_mm: st.inp.msr || null, typed_vsd: st.inp.vsd || null,
      readings_recorded: S.rows.length, note: 'The correct readings are not given to Ask Hoola. Guide the student to read them.' }; },

    steps: [
      { id: 'zero', title: 'Zero error', view: 'vc', render: function (u) {
          u.h2('Least count and zero error');
          u.p('Before measuring, find what one vernier step is worth, then check whether the callipers read zero when the jaws are closed.');
          var t1 = u.task('1. Least count', st.lcOk, st.lcOk ? 'LC = ' + LC.toFixed(1) + ' mm' : 'Look at the vernier: 10 of its divisions cover 9 mm of the main scale.');
          if (!st.lcOk) { t1.add(field('Least count', 'lc', 'mm', submitLC)); t1.add(u.button('Check', submitLC, true)); }
          var js = jawState(), closed = js === 'closed';
          var t2 = u.task('2. Close the jaws on nothing', closed, closed ? 'Closed and locked. Now read the vernier.' : (st.sphere === 'jaws' ? 'The ' + NOUN + ' is between the jaws: take it out first.' : 'The thumb pushes the wheel until the jaws touch.'));
          if (st.sphere === 'jaws') t2.add(u.button('Take the ' + NOUN + ' out', takeOut, false, st.acting));
          t2.add(u.button(closed ? 'Closed' : 'Close the jaws', closeEmpty, !closed, closed || st.acting || st.sphere === 'jaws'));
          var t3 = u.task('3. Read the zero error', st.zeroOk, st.zeroOk ? 'Zero error = ' + sgn(ZR) + ' mm' : 'Which vernier line meets a main-scale line? Zero error = that division × LC, positive if the vernier zero is to the right.');
          if (!st.zeroOk) { t3.add(field('Zero error', 'zero', 'mm', submitZero)); t3.add(u.button('Check', submitZero, true, !closed || st.acting)); }
          viewRow(u);
          u.note('Look straight at the scales, not from the side: the lines must be judged without parallax.');
          u.next('Next: measure the ' + NOUN, st.lcOk && st.zeroOk);
        },
        ok: function () { return st.lcOk && st.zeroOk; },
        auto: function () {
          return closeEmpty().then(function () {
            st.inp.lc = String(LC); submitLC();
            st.inp.zero = String(ZR); submitZero();
          }); } },
      { id: 'measure', title: 'Measure', view: 'jaws', render: function (u) {
          u.h2('Measure the ' + NOUN);
          var js = jawState(), n = S.rows.length, inJaws = st.sphere === 'jaws';
          u.p('Reading ' + Math.min(n + 1, 3) + ' of 3. Take each reading with the ' + NOUN + ' in a new position.');
          var placed = inJaws && (n === 0 || st.turned >= n);
          var tA = u.task('1. Open the jaws', js === 'open' || js === 'sphere', js === 'closed' ? 'Unlock the screw and slide the jaw back.' : 'Open.');
          tA.add(u.button('Open the jaws', openJaws, js === 'closed', js !== 'closed' || st.acting));
          var tB = u.task(n === 0 || !inJaws ? '2. Place the ' + NOUN + ' between the jaws' : '2. Turn the ' + NOUN + ' to a new position', placed,
            placed ? 'The ' + NOUN + (OB.kind === 'coin' ? ' stands' : ' rests') + ' against the fixed jaw.' : (n > 0 && inJaws ? 'Open the jaws, then turn the ' + NOUN + '.' : 'Pick it up from the felt tray.'));
          if (!inJaws) tB.add(u.button('Place the ' + NOUN, placeSphere, js !== 'closed' && !placed, js === 'closed' || st.acting));
          else if (!placed) tB.add(u.button('Turn the ' + NOUN, turnSphere, js === 'open', js !== 'open' || st.acting));
          var tC = u.task('3. Close the jaws on the ' + NOUN + ' and lock', js === 'sphere' && st.locked, js === 'sphere' ? 'Touching gently, screw locked.' : 'The thumb wheel brings the jaw up to the ' + NOUN + '.');
          tC.add(u.button('Close on the ' + NOUN, closeOnSphere, placed && js === 'open', !placed || js !== 'open' || st.acting));
          var ready = js === 'sphere' && st.locked && placed;
          var tD = u.task('4. Read and type', false, ready ? 'MSR = last mm mark before the vernier zero. VSD = the vernier line that coincides.' : (inJaws && !placed ? 'Recorded. Open the jaws and turn the ' + NOUN + ' for another reading.' : 'Close the jaws on the ' + NOUN + ' first.'));
          if (n < 3 || ready) { tD.add(field('Main scale reading (MSR)', 'msr', 'mm', submitReading)); tD.add(field('Coinciding vernier division (VSD)', 'vsd', '', submitReading));
            tD.add(u.button('Check and record', submitReading, true, !ready || st.acting)); }
          viewRow(u);
          u.h3('Observation table · zero error ' + sgn(ZR) + ' mm'); u.table();
          if (n >= 3) u.note('Three readings recorded. You may take more, or go on to the result.');
          u.next('Next: result', n >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          function one(i) { return openJaws().then(function () { return i === 0 ? placeSphere() : turnSphere(); }).then(closeOnSphere)
            .then(function () { st.inp.msr = String(MSR); st.inp.vsd = String(VSD); submitReading(); }); }
          return [0, 1, 2].reduce(function (pr, i) { return pr.then(function () { return one(i); }); }, Promise.resolve()); } },
    ],

    ready: function () {
      if (document.fonts && document.fonts.load) document.fonts.load('600 40px "Public Sans"').then(function () { texes.forEach(function (t) { t.paint(); }); }).catch(function () {});
    },
    tick: function () {
      updViews(); place();
      hudLC.set(st.lcOk ? LC.toFixed(1) + ' mm' : '?');
      var js = jawState(); hudJ.set(js === 'sphere' ? (st.locked ? 'On ' + NOUN + ' · locked' : 'On ' + NOUN) : js === 'closed' ? (st.locked ? 'Closed · locked' : 'Closed') : 'Open');
      hudN.set(S.rows.length + ' of 3');
      // keep the record book's zero-error line current
      var zl = 'Zero error = ' + (st.zeroOk ? sgn(ZR) + ' mm' : '…'); var bk = S.exp && S.exp.book; if (bk && bk.lines[3] !== zl) { bk.lines[3] = zl; S.book.draw(); }
    },
  };
});
