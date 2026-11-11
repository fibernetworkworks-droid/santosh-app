/* Prayogshala studio module: LASER BENCH - scanning Fabry-Perot cavity (Ph.D. laser spectroscopy).
   A He-Ne laser (two longitudinal modes) or a single-mode diode laser, a Fabry-Perot cavity whose second mirror is on a
   piezo, a photodiode and an oscilloscope that shows the transmitted light against the piezo ramp voltage.
   Physics: the `phd_fp` kernel of packs/phd_optics.js. The scope trace is sampled from the Airy response of the cavity;
   the peak positions and widths are found on that trace by the same half-maximum search the student's cursors do, and
   nothing is read back from the finesse formula.
   Safety: the beam is clamped horizontal, 10 cm above the bench, and never leaves the table. */
/* ---- shared bench kit (the same few helpers are built into every Ph.D. instrument rig) ---- */
function phdKit(S) {
  var T = S.T, M = S.M, K = {};
  K.r = function (v, d) { var k = Math.pow(10, d === undefined ? 2 : d); return Math.round(v * k) / k; };
  K.si = function (v, unit, d) {
    if (!isFinite(v)) return '—'; if (v === 0) return '0 ' + unit;
    var a = Math.abs(v), pre = [['G', 1e9], ['M', 1e6], ['k', 1e3], ['', 1], ['m', 1e-3], ['µ', 1e-6], ['n', 1e-9], ['p', 1e-12], ['f', 1e-15]], i;
    for (i = 0; i < pre.length; i++) if (a >= pre[i][1] * 0.9995) break;
    if (i === pre.length) i = pre.length - 1;
    return String(parseFloat((v / pre[i][1]).toPrecision(d || 3))) + ' ' + pre[i][0] + unit;
  };
  K.busy = function () { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; };
  K.wpt = function (o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); };
  K.knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  K.knob = function (parent, u, v, z0, rad) {
    var kg = new T.Group(); kg.position.set(u, v, z0); parent.add(kg);
    var sk = S.mesh(new T.CylinderGeometry(rad * 1.3, rad * 1.38, 0.004, 36), M.bakelite); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; kg.add(sk);
    var kb = S.mesh(new T.CylinderGeometry(rad, rad * 1.1, 0.016, 36), new T.MeshStandardMaterial({ map: K.knurl, roughness: 0.45 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; kg.add(kb);
    var kp = S.mesh(new T.BoxGeometry(0.002, rad * 1.1, 0.0012), M.white, false); kp.position.set(0, rad * 0.65, 0.0215); kg.add(kp);
    return kg;
  };
  K.button = function (parent, u, v, z0, color) {
    var b = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, 0.008, 20), color || M.green); b.rotation.x = Math.PI / 2; b.position.set(u, v, z0 + 0.004); parent.add(b); return b;
  };
  // an instrument case on the bench: front panel with printed title, a screen, knobs and buttons.
  // o = { x, z, ry, w, h, d, title, sub, screen: { u, v, w, h }, knobs: [[u, v, r, label]], buttons: [[u, v, label, color]], tint }
  K.instrument = function (o) {
    var g = new T.Group(); g.position.set(o.x, 0, o.z); g.rotation.y = o.ry || 0; S.scene.add(g);
    var W = o.w, Hh = o.h, D = o.d, FZ = D / 2 + 0.0062, PW = W - 0.014, PH = Hh - 0.014;
    var cs = S.rounded(W, D, Hh, 0.01, new T.MeshStandardMaterial({ color: o.tint || 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); cs.rotation.x = -Math.PI / 2; cs.position.y = Hh / 2 + 0.004; g.add(cs);
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) { var ft = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.004, 14), M.rubber); ft.position.set(f[0] * (W / 2 - 0.02), 0.002, f[1] * (D / 2 - 0.02)); g.add(ft); });
    var tex = S.canvasTex(1400, Math.round(1400 * PH / PW), function (x, w, h) {
      var k = w / PW, X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; };
      x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
      x.fillStyle = '#f1efe8'; x.font = '700 ' + Math.round(0.0125 * k) + 'px "Public Sans", sans-serif'; x.textAlign = 'left'; x.fillText(o.title, 28, 52);
      x.fillStyle = '#c7ccd6'; x.font = '500 ' + Math.round(0.0075 * k) + 'px "Public Sans", sans-serif'; x.fillText(o.sub || '', 28, 88);
      x.textAlign = 'center'; x.fillStyle = '#f1efe8'; x.font = '700 ' + Math.round(0.0068 * k) + 'px "Public Sans", sans-serif';
      (o.knobs || []).forEach(function (q) { x.fillText(q[3] || '', X(q[0]), Y(q[1] - q[2] * 1.9 - 0.004)); });
      (o.buttons || []).forEach(function (q) { x.fillText(q[2] || '', X(q[0]), Y(q[1] - 0.019)); });
      x.textAlign = 'left';
    });
    var fac = S.mesh(new T.BoxGeometry(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]); fac.position.set(0, 0.004 + Hh / 2, FZ - 0.002); g.add(fac);
    var cy = 0.004 + Hh / 2, I = { g: g, FZ: FZ, cy: cy, knobs: [], buttons: [], PH: PH, PW: PW };
    I.at = function (u, v, dz) { return new T.Vector3(u, cy + v, FZ + (dz || 0)); };
    (o.knobs || []).forEach(function (q) { var kn = K.knob(g, q[0], cy + q[1], FZ, q[2]); I.knobs.push(kn); });
    (o.buttons || []).forEach(function (q) { I.buttons.push(K.button(g, q[0], cy + q[1], FZ, q[3])); });
    if (o.screen) {
      var sc = o.screen, pxw = 1024, pxh = Math.round(1024 * sc.h / sc.w), stex = S.liveTex(pxw, pxh);
      var bez = S.mesh(new T.BoxGeometry(sc.w + 0.008, sc.h + 0.008, 0.003), M.grey); bez.position.copy(I.at(sc.u, sc.v, 0.001)); g.add(bez);
      var scr = new T.Mesh(new T.PlaneGeometry(sc.w, sc.h), new T.MeshBasicMaterial({ map: stex, toneMapped: false })); scr.position.copy(I.at(sc.u, sc.v, 0.0035)); g.add(scr);
      I.screen = { tex: stex, w: pxw, h: pxh, paint: function (fn) { stex.draw(function (x, w, h) { fn(x, w, h); }); } };
    }
    return I;
  };
  // a panel canvas in the step pane that shares the 3D screen's drawing
  K.panel = function (u, ratio) {
    var cv = document.createElement('canvas'); cv.width = 760; cv.height = Math.round(760 * ratio);
    cv.style.cssText = 'width:100%;border-radius:10px;border:1px solid var(--line);background:#06130c'; u.el(cv); return cv;
  };
  // plot helpers for the green instrument screens
  K.bg = function (x, w, h) { x.fillStyle = '#06130c'; x.fillRect(0, 0, w, h); };
  K.chart = function (x, R, o) {
    var lx = o.xlog ? Math.log(o.xr[0]) : o.xr[0], hx = o.xlog ? Math.log(o.xr[1]) : o.xr[1], ly = o.ylog ? Math.log(o.yr[0]) : o.yr[0], hy = o.ylog ? Math.log(o.yr[1]) : o.yr[1], i, fs = Math.round(R.h * 0.075);
    var X = function (v) { return R.x + R.w * ((o.xlog ? Math.log(v) : v) - lx) / (hx - lx); }, Y = function (v) { return R.y + R.h - R.h * ((o.ylog ? Math.log(v) : v) - ly) / (hy - ly); };
    x.strokeStyle = 'rgba(120,220,150,.2)'; x.lineWidth = 1;
    for (i = 0; i <= 8; i++) { x.beginPath(); x.moveTo(R.x + R.w * i / 8, R.y); x.lineTo(R.x + R.w * i / 8, R.y + R.h); x.stroke(); }
    for (i = 0; i <= 6; i++) { x.beginPath(); x.moveTo(R.x, R.y + R.h * i / 6); x.lineTo(R.x + R.w, R.y + R.h * i / 6); x.stroke(); }
    x.strokeStyle = 'rgba(120,220,150,.55)'; x.strokeRect(R.x, R.y, R.w, R.h);
    x.fillStyle = '#9fe0b8'; x.font = fs + 'px "JetBrains Mono", monospace'; x.textAlign = 'left';
    if (o.xlabel) x.fillText(o.xlabel, R.x + 4, R.y + R.h + fs * 1.3);
    if (o.ylabel) x.fillText(o.ylabel, R.x + 4, R.y - fs * 0.35);
    return { X: X, Y: Y };
  };
  K.poly = function (x, ch, pts, col, lw) {
    x.strokeStyle = col; x.lineWidth = lw || 2.2; x.beginPath();
    for (var i = 0; i < pts.length; i++) { var px = ch.X(pts[i][0]), py = ch.Y(pts[i][1]); if (i) x.lineTo(px, py); else x.moveTo(px, py); } x.stroke();
  };
  K.dots = function (x, ch, pts, col, rad) { x.fillStyle = col; pts.forEach(function (q) { x.beginPath(); x.arc(ch.X(q[0]), ch.Y(q[1]), rad || 3, 0, Math.PI * 2); x.fill(); }); };
  K.text = function (x, t, px, py, col, size, al) { x.fillStyle = col || '#9fe0b8'; x.font = size + 'px "JetBrains Mono", monospace'; x.textAlign = al || 'left'; x.fillText(t, px, py); };
  // a BNC socket on the side of a case / box
  K.bnc = function (parent, x, y, z, rotY) {
    var g = new T.Group(); g.position.set(x, y, z); g.rotation.y = rotY || 0; parent.add(g);
    var b = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 0.012, 20), M.chrome); b.rotation.x = Math.PI / 2; g.add(b);
    var pin = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, 0.014, 8), M.brass); pin.rotation.x = Math.PI / 2; pin.position.z = 0.002; g.add(pin);
    return g;
  };
  K.box = function (w, h, d, color, x, y, z, parent) { var b = S.rounded(w, d, h, Math.min(0.004, w / 6), new T.MeshStandardMaterial({ color: color, roughness: 0.55, metalness: 0.1 })); b.rotation.x = -Math.PI / 2; b.position.set(x, y + h / 2, z); (parent || S.scene).add(b); return b; };
  // a tiny Lehmer + Box-Muller generator for decorative noise on the screens (same stream as the pack's)
  K.rnd = function (seed) {
    var s = (Math.floor(Math.abs(seed)) % 2147483646) + 1, has = false, z1 = 0, o = {};
    o.next = function () { s = (s * 16807) % 2147483647; return s / 2147483647; };
    o.gauss = function () { if (has) { has = false; return z1; } var a = o.next(), b = o.next(), q = Math.sqrt(-2 * Math.log(a)); z1 = q * Math.sin(2 * Math.PI * b); has = true; return q * Math.cos(2 * Math.PI * b); };
    return o;
  };
  return K;
}

HoolaStudio.define('phd-laser-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign, KERN = S.lab.kernel, KN = HK.K[KERN];
  var p0 = HK.paramsFor(KERN, S.lab.params), V_ = S.lab.variant || {}, Kt = phdKit(S), r = Kt.r, si = Kt.si, C = 2.99792458e8;
  var DIODE = { lam: 7.8e-7 };                                               // a 780 nm diode laser, single mode (the lab's nominal choice)
  var st = { on: false, src: 'hene', pk: null, weak: null, trace: null, prog: 0, cur: null };
  var dirty = true;
  function mark() { dirty = true; }
  function pNow() { return st.src === 'hene' ? p0 : assign(p0, { lam: DIODE.lam, amp2: 0, dnu: 0 }); }
  function trace() { if (!st.trace) st.trace = KN.trace(pNow()); return st.trace; }
  var HY = 0.1;

  // ================================================================ the bench
  function beam(a, b, op) { var d = new T.Vector3().subVectors(b, a), len = d.length(), m = new T.Mesh(new T.CylinderGeometry(0.0011, 0.0011, len, 8), new T.MeshBasicMaterial({ color: 0xff3322, transparent: true, opacity: op || 0.5 })); m.position.copy(a).addScaledVector(d, 0.5); m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize()); S.scene.add(m); return m; }
  var hene = new T.Group(); hene.position.set(-0.62, 0, -0.2); S.scene.add(hene);
  var hb = S.mesh(new T.CylinderGeometry(0.024, 0.024, 0.3, 28), new T.MeshStandardMaterial({ color: 0x2f3a46, roughness: 0.4, metalness: 0.5 })); hb.rotation.z = Math.PI / 2; hb.position.set(0, HY, 0); hene.add(hb);
  var hc = S.mesh(new T.CylinderGeometry(0.026, 0.026, 0.014, 28), M.alu); hc.rotation.z = Math.PI / 2; hc.position.set(0.157, HY, 0); hene.add(hc);
  [-0.08, 0.08].forEach(function (x) { var po = S.mesh(new T.BoxGeometry(0.03, HY - 0.024, 0.05), M.alu); po.position.set(x, (HY - 0.024) / 2, 0); hene.add(po); });
  var hl = S.label('He-Ne LASER 632.8 nm · tube 30 cm', { w: 0.2, ratio: 0.09, color: '#e8e8ea' }); hl.position.set(-0.02, HY, 0.0245); hene.add(hl);
  var hled = S.mesh(new T.SphereGeometry(0.004, 12, 12), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 })); hled.position.set(-0.13, HY + 0.01, 0.0245); hene.add(hled);
  var dio = new T.Group(); dio.position.set(-0.62, HY - 0.03, -0.06); S.scene.add(dio);
  Kt.box(0.09, 0.05, 0.06, 0x3a3f47, 0, 0, 0, dio);
  var dl = S.label('DIODE LASER 780 nm', { w: 0.08, ratio: 0.14, color: '#e8e8ea' }); dl.position.set(0, 0.03, 0.0305); dio.add(dl);
  var dled = S.mesh(new T.SphereGeometry(0.004, 12, 12), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 })); dled.position.set(-0.03, 0.043, 0.0305); dio.add(dled);
  var dsn = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.03, 16), M.alu); dsn.rotation.z = Math.PI / 2; dsn.position.set(0.058, 0.03, 0); dio.add(dsn);
  S.contact(0.34, 0.1, -0.62, -0.2, 0.4); S.contact(0.12, 0.1, -0.62, -0.06, 0.4);
  var sel = new T.Group(); sel.position.set(-0.42, 0, -0.06); S.scene.add(sel);
  Kt.box(0.07, 0.04, 0.05, 0x6f8193, 0, 0, 0, sel);
  var selK = Kt.knob(sel, 0, 0.022, 0.0252, 0.011);
  var sll = S.label('SOURCE  HeNe ◂  ▸ DIODE', { w: 0.065, ratio: 0.14, color: '#f1efe8', bg: '#2b323d', px: 512 }); sll.position.set(0, 0.008, 0.0254); sel.add(sll);
  S.contact(0.1, 0.08, -0.42, -0.06, 0.4);

  var fpc = new T.Group(); fpc.position.set(-0.22, 0, -0.2); S.scene.add(fpc);
  var fsteel = new T.MeshStandardMaterial({ color: 0x8c949b, roughness: 0.3, metalness: 0.9 });
  var tubeL = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.09, 32, 1, true), fsteel); tubeL.rotation.z = Math.PI / 2; tubeL.position.set(0, HY, 0); fpc.add(tubeL);
  [-1, 1].forEach(function (sg) { var mr = S.mesh(new T.CylinderGeometry(0.027, 0.027, 0.014, 32), M.alu); mr.rotation.z = Math.PI / 2; mr.position.set(sg * 0.052, HY, 0); fpc.add(mr);
    var mg = S.mesh(new T.CylinderGeometry(0.015, 0.015, 0.002, 28), new T.MeshPhysicalMaterial({ color: 0xbfd8e6, roughness: 0.03, metalness: 0.2, transmission: 0.6, transparent: true, opacity: 0.8 })); mg.rotation.z = Math.PI / 2; mg.position.set(sg * 0.043, HY, 0); fpc.add(mg); });
  var pz = S.mesh(new T.CylinderGeometry(0.022, 0.022, 0.008, 28), new T.MeshStandardMaterial({ color: 0xd8c9a8, roughness: 0.5 })); pz.rotation.z = Math.PI / 2; pz.position.set(0.064, HY, 0); fpc.add(pz);
  var pstand = S.mesh(new T.BoxGeometry(0.2, HY - 0.027, 0.05), M.alu); pstand.position.set(0, (HY - 0.027) / 2, 0); pstand.scale.set(0.8, 1, 1); fpc.add(pstand);
  var fl = S.label('SCANNING FABRY-PEROT · L = ' + r(p0.L * 100, 1) + ' cm', { w: 0.16, ratio: 0.08, color: '#e8e8ea' }); fl.position.set(0, HY - 0.032, 0.0285); fpc.add(fl);
  S.contact(0.24, 0.1, -0.22, -0.2, 0.4);
  var pd = new T.Group(); pd.position.set(-0.02, 0, -0.2); S.scene.add(pd);
  var pdb = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.03, 18), M.chrome); pdb.rotation.z = Math.PI / 2; pdb.position.set(0, HY, 0); pd.add(pdb);
  var pds = S.mesh(new T.CylinderGeometry(0.003, 0.003, HY - 0.014, 10), M.chrome); pds.position.set(0, (HY - 0.014) / 2, 0); pd.add(pds);
  S.contact(0.04, 0.04, -0.02, -0.2, 0.4);
  var bmHene = beam(new T.Vector3(-0.455, HY, -0.2), new T.Vector3(-0.015, HY, -0.2));
  var bmDio = [beam(new T.Vector3(-0.54, HY, -0.06), new T.Vector3(-0.4, HY, -0.06)), beam(new T.Vector3(-0.4, HY, -0.06), new T.Vector3(-0.4, HY, -0.2)), beam(new T.Vector3(-0.4, HY, -0.2), new T.Vector3(-0.015, HY, -0.2))];
  var flip = S.mesh(new T.BoxGeometry(0.018, 0.018, 0.003), M.chrome); flip.position.set(-0.4, HY, -0.2); flip.rotation.y = Math.PI / 4; S.scene.add(flip);
  var fpost = S.mesh(new T.CylinderGeometry(0.003, 0.003, HY - 0.009, 10), M.chrome); fpost.position.set(-0.4, (HY - 0.009) / 2, -0.2); S.scene.add(fpost);
  var dpost = S.mesh(new T.CylinderGeometry(0.004, 0.004, HY - 0.055, 10), M.chrome); dpost.position.set(-0.62, (HY - 0.055) / 2, -0.06); S.scene.add(dpost);
  var warn = S.label('beam clamped horizontal · 10 cm above the bench', { w: 0.2, ratio: 0.06, color: '#7a1f1f' }); warn.rotation.x = -Math.PI / 2; warn.position.set(-0.3, 0.0012, -0.03); S.scene.add(warn);

  // the piezo driver and the scope
  var drv = new T.Group(); drv.position.set(-0.17, 0, -0.04); S.scene.add(drv);
  Kt.box(0.12, 0.05, 0.08, 0x6f8193, 0, 0, 0, drv);
  var drl = S.label('PIEZO RAMP 0 – ' + p0.Vmax + ' V', { w: 0.11, ratio: 0.1, color: '#f1efe8', bg: '#2b323d', px: 512 }); drl.position.set(0, 0.032, 0.0405); drv.add(drl);
  S.contact(0.15, 0.11, -0.17, -0.04, 0.4);
  var ins = Kt.instrument({ x: 0.2, z: -0.22, ry: -0.12, w: 0.42, h: 0.2, d: 0.26, title: 'OSCILLOSCOPE', sub: 'X: piezo ramp (V) · Y: photodiode', screen: { u: -0.045, v: 0.0, w: 0.28, h: 0.155 }, buttons: [[0.1, -0.06, 'POWER', M.green], [0.17, -0.06, 'AUTOSET', M.grey]] });
  var pwr = ins.buttons[0], auto = ins.buttons[1], led1 = S.mesh(new T.SphereGeometry(0.004, 12, 12), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 }));
  led1.position.copy(ins.at(0.1, -0.038, 0.002)); ins.g.add(led1);
  S.contact(0.5, 0.34, 0.2, -0.22, 0.5);
  S.wire([[-0.02 + 0.015, 0.1, -0.2], [0.05, 0.04, -0.18], [-0.015, 0.06, -0.24]], 'black'); S.wire([[-0.17 + 0.06, 0.03, -0.04], [0.0, 0.02, -0.08], [-0.015, 0.07, -0.2]], 'red');

  S.addApparatus('lasers', hene, 'He-Ne laser and diode laser', 'The He-Ne laser has a 30 cm tube, so its longitudinal modes are 500 MHz apart and two of them oscillate. The diode laser is a single mode. The knob on the selector box picks which one feeds the cavity.');
  S.addApparatus('fp', fpc, 'Scanning Fabry-Perot cavity', 'Two mirrors a fixed distance apart; the second is on a piezo disc that moves it by a few hundred nanometres as the ramp voltage rises. Light passes only when the spacing is a whole number of half wavelengths.');
  S.addApparatus('pd', pd, 'Photodiode', 'It measures the light that gets through the cavity and sends it to the scope.');
  S.addApparatus('ins', ins.g, 'Oscilloscope', 'Shows the transmitted light against the piezo ramp voltage. Each peak is one order of the cavity.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard('Power'), hudB = S.hudCard('Laser'), hudC = S.hudCard('Readings');

  // ================================================================ the screen
  function drawScreen(x, w, h) {
    Kt.bg(x, w, h); var fs = Math.round(h * 0.05), i, tr, ch, p = pNow();
    if (!st.on) { Kt.text(x, 'power off', w / 2, h / 2, '#5aa77a', fs * 1.4, 'center'); return; }
    tr = trace(); var ymax = 1.3;
    ch = Kt.chart(x, { x: w * 0.08, y: h * 0.1, w: w * 0.88, h: h * 0.6 }, { xr: [0, p.Vmax], yr: [0, ymax], xlabel: 'piezo ramp (V)', ylabel: 'transmitted light' });
    var step = Math.max(1, Math.floor(tr.length / 1200)), pts = [];
    for (i = 0; i < tr.length; i += step) pts.push([p.Vmax * i / (tr.length - 1), tr[i]]);
    Kt.poly(x, ch, pts, '#ffe45e', 1.8);
    if (st.pk) st.pk.pos.forEach(function (v, k) { x.strokeStyle = 'rgba(100,227,255,.9)'; x.lineWidth = 2; var hw = st.pk.wid[k] / 2; x.beginPath(); x.moveTo(ch.X(v - hw), ch.Y(0.5)); x.lineTo(ch.X(v + hw), ch.Y(0.5)); x.stroke(); x.beginPath(); x.moveTo(ch.X(v), ch.Y(1.02)); x.lineTo(ch.X(v), ch.Y(1.12)); x.stroke(); Kt.text(x, r(v, 2), ch.X(v), ch.Y(1.17), '#64e3ff', fs * 0.9, 'center'); });
    if (st.weak) st.weak.forEach(function (v) { x.strokeStyle = 'rgba(255,159,94,.9)'; x.lineWidth = 2; x.beginPath(); x.moveTo(ch.X(v), ch.Y(0.5)); x.lineTo(ch.X(v), ch.Y(0.62)); x.stroke(); Kt.text(x, r(v, 2), ch.X(v), ch.Y(0.67), '#ff9f5e', fs * 0.9, 'center'); });
    Kt.text(x, (st.src === 'hene' ? 'He-Ne ' : 'Diode ') + si(p.lam, 'm', 4) + '   cavity L = ' + r(p.L * 100, 1) + ' cm', w * 0.04, h * 0.84, '#9fe0b8', fs);
    Kt.text(x, st.pk ? st.pk.pos.length + ' full peaks found' + (st.pk.pos.length > 1 ? '   spacing ' + r((st.pk.pos[st.pk.pos.length - 1] - st.pk.pos[0]) / (st.pk.pos.length - 1), 3) + ' V' : '') : 'press AUTOSET', w * 0.04, h * 0.93, '#ffe45e', fs * 1.1);
    if (st.prog > 0 && st.prog < 1) { x.fillStyle = 'rgba(100,227,255,.8)'; x.fillRect(0, h - 6, w * st.prog, 6); }
  }
  function paint() { ins.screen.paint(drawScreen); }
  var panelCv = null;
  function paintPanel() { if (panelCv && panelCv.isConnected) drawScreen(panelCv.getContext('2d'), panelCv.width, panelCv.height); }
  function panel(u) { panelCv = Kt.panel(u, 0.62); paintPanel(); }

  // ================================================================ actions
  function integrate(ms, fn) { return S.tween(ms, function (k) { st.prog = k; if (k >= 1) st.prog = 0; mark(); }).then(function () { st.prog = 0; return fn(); }); }
  function needOn() { if (!st.on) { S.say('Switch the laser and the scope on first.'); return true; } return false; }
  function powerOn(on) {
    if (Kt.busy()) return Promise.resolve(); if (st.on === on) return Promise.resolve();
    return S.hand.tap(pwr, 'front').then(function () {
      st.on = on; led1.material.emissive.setHex(on ? 0x22cc44 : 0); led1.material.color.setHex(on ? 0x33dd55 : 0x331111);
      lamps(); S.say(on ? 'Laser warming up, ramp running. The beam is horizontal, 10 cm above the bench.' : 'Everything switched off.'); mark(); S.render();
    });
  }
  function lamps() {
    var h = st.on && st.src === 'hene', d = st.on && st.src === 'diode';
    hled.material.emissive.setHex(h ? 0xcc2222 : 0); hled.material.color.setHex(h ? 0xff3333 : 0x331111); dled.material.emissive.setHex(d ? 0xcc2222 : 0); dled.material.color.setHex(d ? 0xff3333 : 0x331111);
    bmHene.visible = h; bmDio.forEach(function (b) { b.visible = d; }); flip.visible = st.src === 'diode'; fpost.visible = st.src === 'diode';
  }
  function chooseLaser(src) {
    if (Kt.busy() || st.src === src) return Promise.resolve();
    var a0 = selK.rotation.z, a1 = src === 'hene' ? 0.9 : -0.9, pt = Kt.wpt(sel, 0, 0.022, 0.044);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { selK.rotation.z = a0 + (a1 - a0) * k; }, { mode: 'front', ms: 500, reachMs: 500 }).then(function () {
      st.src = src; selK.rotation.z = a1; st.trace = null; st.pk = null; st.weak = null; lamps();
      S.say(src === 'hene' ? 'He-Ne laser into the cavity: two longitudinal modes oscillate.' : 'Flip mirror in: the diode laser feeds the cavity, a single mode.'); mark(); S.render();
    });
  }
  function readPeaks() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    return S.hand.tap(auto, 'front').then(function () { return integrate(700, function () {
      var q = pNow(), pk = KN.peaks(q, trace()); st.pk = pk; st.cur = pk;
      S.say(pk.pos.length + ' complete peaks on the scope. Put the cursors on each: position and full width at half height.'); mark(); S.render(); return pk;
    }); });
  }
  function findWeak() {                                                      // the smaller peaks, between the main ones
    if (!st.pk) { S.say('Read the main peaks first.'); return null; }
    var tr = trace(), q = pNow(), n = tr.length, mx = Math.max.apply(null, tr), out = [], i, near;
    for (i = 2; i < n - 2; i++) if (tr[i] > 0.08 * mx && tr[i] < 0.5 * mx && tr[i] >= tr[i - 1] && tr[i] > tr[i + 1] && tr[i] >= tr[i - 2] && tr[i] > tr[i + 2]) out.push(q.Vmax * i / (n - 1));
    st.weak = out; mark(); S.say(out.length ? out.length + ' smaller peaks found between the main ones.' : 'No smaller peaks: a single mode.'); S.render(); return out;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.pk || !st.pk.pos.length) { S.say('Read the peaks first.'); return false; }
    var tag = st.src === 'hene' ? 'hene' : 'diode';
    if (S.rows.some(function (z) { return z.k === 'pk' && z.src === tag; })) { S.say('These peaks are already in the book.'); return false; }
    st.pk.pos.forEach(function (v, i) { S.addRow({ k: 'pk', src: tag, n: i + 1, v: v, w: st.pk.wid[i] }); }); return true;
  }
  function recordMode() {
    if (S.hand.busy) return false; if (!st.weak || !st.pk) { S.say('Find the smaller peaks first.'); return false; }
    if (S.rows.some(function (z) { return z.k === 'mode'; })) { S.say('The mode offset is already in the book.'); return false; }
    var strong = st.pk.pos, fsr = (strong[strong.length - 1] - strong[0]) / (strong.length - 1), best = null, i, j, d;
    for (i = 0; i < st.weak.length; i++) for (j = 0; j < strong.length; j++) { d = st.weak[i] - strong[j]; if (d > 0 && d < fsr && (best === null || d < best)) best = d; }
    if (best === null) { S.say('Could not pair a smaller peak with a main one.'); return false; }
    S.addRow({ k: 'mode', d: best, fsr: fsr, dnu: best / fsr * (C / (2 * p0.L)) }); return true;
  }
  function fitRows(rows, tag) {
    var rs = rows.filter(function (z) { return z.k === 'pk' && z.src === tag; }); if (rs.length < 3) return null;
    var fsr = (rs[rs.length - 1].v - rs[0].v) / (rs.length - 1), w = S.fit.mean(rs.map(function (z) { return z.w; })); return { fsr: fsr, w: w, f: fsr / w };
  }
  function result(rows) {
    var a = fitRows(rows, 'hene'); if (!a) return null; var md = rows.filter(function (z) { return z.k === 'mode'; })[0], dd = fitRows(rows, 'diode');
    return { label: 'Finesse of the cavity', value: a.f, unit: '', digits: 2, truth: HK.TEXTBOOK.phd_fp_finesse(p0),
      note: 'Peak spacing ' + r(a.fsr, 2) + ' V = λ/2 of mirror travel (so ' + r(p0.lam / 2 * 1e9, 1) + ' nm per ' + r(a.fsr, 1) + ' V), width ' + r(a.w, 3) + ' V. Free spectral range c/2L = ' + r(C / (2 * p0.L) / 1e9, 3) + ' GHz.'
        + (md ? ' Laser mode spacing from the smaller peaks: ' + r(md.dnu / 1e6, 0) + ' MHz.' : '') + (dd ? ' The diode laser gives finesse ' + r(dd.f, 1) + ' (same cavity, one set of peaks).' : '') };
  }
  var VIVA = [['The free spectral range of a cavity of length L is', ['c / 2L', 'c / L', '2L / c'], 0, 'The round trip is 2L.'], ['Higher mirror reflectivity makes the peaks', ['Narrower', 'Wider', 'Higher'], 0, 'Finesse = π√R / (1 − R) grows with R.'], ['A mirror moved by λ/2 shifts the pattern by', ['One free spectral range', 'Nothing', 'Two peaks'], 0, 'That is how the ramp volts are calibrated.']];

  // ================================================================ steps
  var STEPS = [{ id: 'on', title: 'Switch on', view: 'ins', render: function (u) {
      u.h2('Switch the laser and the scope on');
      u.p('The He-Ne laser feeds the cavity along a line 10 cm above the bench. The piezo driver ramps the second mirror from 0 to ' + p0.Vmax + ' V and the photodiode behind the cavity is shown on the scope against that ramp.');
      u.task('Power', st.on, st.on ? 'On' : 'Off').add(u.button(st.on ? 'Switch off' : 'Switch on', function () { S.focus('ins'); powerOn(!st.on); }, !st.on, S.hand.busy));
      u.note('The beam is clamped horizontal at bench height and stays on the table. Never look into it or at a reflection from a mirror; block it when you change anything.');
      u.next('Next', st.on); }, ok: function () { return st.on; }, auto: function () { return powerOn(true); } },
    { id: 'peaks', title: 'Peaks and finesse', view: 'ins', render: function (u) {
        u.h2('Spacing and width of the peaks (He-Ne laser)');
        u.p('Press AUTOSET to put the cursors on every complete peak. Write down each peak\'s position and its full width at half maximum. The spacing of the peaks is one free spectral range; the finesse is that spacing divided by the width.');
        u.row(u.button('Select the He-Ne laser', function () { S.focus('lasers'); chooseLaser('hene'); }, st.src !== 'hene', S.hand.busy || st.src === 'hene'), u.button('AUTOSET', function () { S.focus('ins'); readPeaks(); }, true, S.hand.busy), u.button('Write the peaks down', function () { record(); }, false, !st.pk || S.hand.busy || st.src !== 'hene'));
        u.live(function () { var a = fitRows(S.rows, 'hene'); return st.pk ? st.pk.pos.length + ' peaks · spacing ' + (st.pk.pos.length > 1 ? r((st.pk.pos[st.pk.pos.length - 1] - st.pk.pos[0]) / (st.pk.pos.length - 1), 3) : '—') + ' V' + (a ? ' · finesse ' + r(a.f, 1) : '') : 'no peaks read'; });
        panel(u); u.h3('Observation table'); u.table(); u.next('Next: the laser modes', !!fitRows(S.rows, 'hene')); },
      ok: function () { return !!fitRows(S.rows, 'hene'); }, auto: function () { return chooseLaser('hene').then(function () { return readPeaks(); }).then(function () { record(); }); } },
    { id: 'modes', title: 'Mode structure', view: 'ins', render: function (u) {
        u.h2('The smaller peaks: the laser has two modes');
        u.p('Between the main peaks there are smaller ones: the second longitudinal mode of the He-Ne laser, at a slightly different frequency. Find them and write down how far each lies after a main peak. That offset, over the peak spacing, times the free spectral range c/2L, is the laser\'s mode spacing.');
        u.row(u.button('Find the smaller peaks', function () { S.focus('ins'); findWeak(); }, true, S.hand.busy), u.button('Write the offset down', function () { recordMode(); }, false, !st.weak || !st.weak.length || S.hand.busy));
        u.live(function () { var m = S.rows.filter(function (z) { return z.k === 'mode'; })[0]; return m ? 'offset ' + r(m.d, 2) + ' V of a ' + r(m.fsr, 2) + ' V spacing → ' + r(m.dnu / 1e6, 0) + ' MHz' : st.weak ? st.weak.length + ' smaller peaks' : 'none yet'; });
        panel(u); u.h3('Observation table'); u.table(); u.next('Next: the diode laser', S.rows.some(function (z) { return z.k === 'mode'; })); },
      ok: function () { return S.rows.some(function (z) { return z.k === 'mode'; }); }, auto: function () { findWeak(); recordMode(); return Promise.resolve(); } },
    { id: 'diode', title: 'Diode laser', view: 'lasers', render: function (u) {
        u.h2('The same cavity with a single-mode diode laser');
        u.p('Turn the selector to the diode laser. The extra peaks go: it oscillates in one mode only. The peak widths, and so the finesse, are the same, because they belong to the cavity, not to the laser.');
        u.row(u.button('Select the diode laser', function () { S.focus('lasers'); chooseLaser('diode'); }, st.src !== 'diode', S.hand.busy || st.src === 'diode'), u.button('AUTOSET', function () { S.focus('ins'); readPeaks(); }, true, S.hand.busy || st.src !== 'diode'), u.button('Write the peaks down', function () { record(); }, false, !st.pk || S.hand.busy || st.src !== 'diode'));
        panel(u); u.h3('Observation table'); u.table(); u.next('Next: result', !!fitRows(S.rows, 'diode')); },
      ok: function () { return !!fitRows(S.rows, 'diode'); }, auto: function () { return chooseLaser('diode').then(function () { return readPeaks(); }).then(function () { record(); }); } }];

  function askState() { var p = pNow(); return { experiment: S.lab.title, laser: st.src === 'hene' ? 'He-Ne 632.8 nm, two modes' : 'diode 780 nm, single mode', power_on: st.on, cavity_length_cm: r(p.L * 100, 1), ramp_max_V: p.Vmax, peaks_read: st.pk ? st.pk.pos.length : 0, readings: S.rows.length }; }
  return {
    camera: { pos: [-0.2, 0.62, 1.2], look: [-0.2, 0.06, -0.15] },
    views: { lasers: [[-0.5, 0.3, 0.2], [-0.52, 0.08, -0.14]], fp: [[-0.22, 0.25, 0.1], [-0.22, 0.1, -0.2]], ins: [[0.18, 0.37, 0.48], [0.2, 0.1, -0.22]], bench: [[-0.2, 0.62, 1.2], [-0.2, 0.06, -0.15]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'Two parallel mirrors transmit light only when their spacing is a whole number of half wavelengths. Scanning one mirror therefore shows a series of sharp transmission peaks, one per free spectral range, each as narrow as the mirrors are reflective. The ratio of the peak spacing to the peak width is the finesse.',
      formula: 'T = 1 / (1 + F sin²(δ/2)),  FSR = c / 2L,  finesse = FSR / width', formulaNote: 'F = 4R/(1−R)², δ = 4πL ν / c; for high R the finesse is about π√R / (1 − R)',
      more: ['Moving a mirror by λ/2 shifts the pattern by exactly one order, so the piezo volts between two peaks calibrate the scan.', 'A laser with several longitudinal modes shows one set of peaks per mode; the offset between the sets, as a fraction of the spacing, times c/2L is the mode spacing.', 'A He-Ne laser tube 30 cm long has modes 500 MHz apart.'],
      precautions: 'The beam is clamped horizontal at bench height. Never look into it or at a reflection. Block it when changing optics.' },
    book: { title: 'Expt. - ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 74), 'Cavity L = ' + r(p0.L * 100, 1) + ' cm, ramp 0 - ' + p0.Vmax + ' V', 'Safety: beam horizontal, 10 cm up.'],
      columns: [{ label: 'Laser', get: function (z) { return z.k === 'mode' ? 'modes' : z.src; } }, { label: 'Peak', get: function (z) { return z.k === 'mode' ? '—' : z.n; } }, { label: 'V (V)', get: function (z) { return z.k === 'mode' ? 'offset ' + r(z.d, 2) : r(z.v, 3); } }, { label: 'FWHM (V)', get: function (z) { return z.k === 'mode' ? r(z.dnu / 1e6, 0) + ' MHz' : r(z.w, 3); } }] },
    result: result, tol: 0.03, resultNote: 'The finesse comes from the widths on the simulated trace, found by interpolating the half-height crossings. A real cavity also has mirror flatness and alignment losses, which lower it.',
    chips: ['What is finesse?', 'Why are there smaller peaks?', 'How is the ramp calibrated?', 'Check my readings', 'What sets the peak width?'],
    viva: VIVA, askState: askState, steps: STEPS,
    tick: function () { hudA.set(st.on ? 'On' : 'Off'); hudB.set(st.src === 'hene' ? 'He-Ne' : 'Diode'); hudC.set(S.rows.length + ' written'); if (dirty) { dirty = false; paint(); paintPanel(); } },
    ready: function () { paint(); lamps(); }
  };
});
