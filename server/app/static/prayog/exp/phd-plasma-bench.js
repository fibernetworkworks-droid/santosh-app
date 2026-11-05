/* Prayogshala studio module: PLASMA BENCH (Ph.D. plasma diagnostics).
   Two set-ups, one kernel each of packs/phd_optics.js:
     phd_langmuir  an argon DC glow discharge in a glass tube with three probes on top ports: a single Langmuir probe, a
                   symmetric double probe and a heated emissive probe, and a probe source-meter with a live I-V screen;
     phd_paschen   a bell jar with two parallel plates, a pressure gauge and a high-voltage supply that is raised until the
                   gas breaks down.
   The curves are the kernel's: electron and ion currents of an ideal probe (Bohm ion current, Maxwellian electrons, no
   sheath expansion, no magnetic field), and Paschen's law with the gas constants of the lab. The student finds Te, the
   plasma potential, the density and the breakdown minimum by their own fit; the bench never shows them.
   The wire's work function, Richardson constant and heating, and the Paschen gas constants, are illustrative (see the lab).
   Safety: a glow discharge and a breakdown supply are high voltage; the cover stays on and the supply is interlocked. */
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

HoolaStudio.define('phd-plasma-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign, KERN = S.lab.kernel, KN = HK.K[KERN];
  var p = HK.paramsFor(KERN, S.lab.params), V_ = S.lab.variant || {}, Kt = phdKit(S), r = Kt.r, si = Kt.si;
  var MODE = KERN === 'phd_langmuir' ? 'lang' : 'pas';
  var st = { on: false, dis: false, probe: 0, sw: null, fit: null, prog: 0, idx: 0, pd: 1.0, cur: null, flash: 0, vshow: 0, lastV: null };
  var dirty = true;
  function mark() { dirty = true; }
  var PROBES = ['single', 'double', 'emissive'];

  // ================================================================ the bench
  var sup = new T.Group(); sup.position.set(-0.6, 0, -0.18); S.scene.add(sup);
  Kt.box(0.14, 0.09, 0.12, 0x6f8193, 0, 0, 0, sup);
  var supl = S.label(MODE === 'lang' ? 'DISCHARGE SUPPLY · HIGH VOLTAGE' : 'BREAKDOWN SUPPLY · 0 - 5 kV · interlocked', { w: 0.13, ratio: 0.1, color: '#f1efe8', bg: '#7a1f1f', px: 768 }); supl.position.set(0, 0.07, 0.0607); sup.add(supl);
  var sbut = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.008, 20), M.green); sbut.rotation.x = Math.PI / 2; sbut.position.set(-0.03, 0.04, 0.064); sup.add(sbut);
  var sled = S.mesh(new T.SphereGeometry(0.005, 12, 12), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 })); sled.position.set(0.03, 0.04, 0.062); sup.add(sled);
  var sbl = S.label('ON / OFF', { w: 0.04, ratio: 0.15, color: '#f1efe8' }); sbl.position.set(-0.03, 0.022, 0.0607); sup.add(sbl);
  S.contact(0.2, 0.17, -0.6, -0.18, 0.4);
  var glow = null, glowMat = null, tip = [], jar = null, bk = null, plateTop = null, spark = null, gauge = null;
  if (MODE === 'lang') {
    var tube = new T.Group(); tube.position.set(-0.2, 0, -0.2); S.scene.add(tube); jar = tube;
    var gl = S.mesh(new T.CylinderGeometry(0.036, 0.036, 0.44, 40, 1, true), new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, transmission: 0.9, thickness: 0.003, ior: 1.5, transparent: true, opacity: 0.35, side: T.DoubleSide })); gl.rotation.z = Math.PI / 2; gl.position.set(0, 0.06, 0); tube.add(gl);
    glowMat = new T.MeshBasicMaterial({ color: 0xb36bff, transparent: true, opacity: 0.0 }); glow = new T.Mesh(new T.CylinderGeometry(0.03, 0.03, 0.4, 32), glowMat); glow.rotation.z = Math.PI / 2; glow.position.set(0, 0.06, 0); tube.add(glow);
    [-1, 1].forEach(function (sg) { var el = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.006, 28), M.brass); el.rotation.z = Math.PI / 2; el.position.set(sg * 0.205, 0.06, 0); tube.add(el);
      var cp = S.mesh(new T.CylinderGeometry(0.04, 0.04, 0.02, 32), M.alu); cp.rotation.z = Math.PI / 2; cp.position.set(sg * 0.225, 0.06, 0); tube.add(cp); });
    [-0.06, 0.0, 0.06].forEach(function (x, i) {
      var port = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.04, 18), M.alu); port.position.set(x, 0.1, 0); tube.add(port);
      var wire = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 0.052, 6), M.copper); wire.position.set(x, 0.062, 0); tube.add(wire);
      var tp = S.mesh(new T.SphereGeometry(0.0018, 8, 8), new T.MeshStandardMaterial({ color: 0xaaaaaa, emissive: 0x000000 })); tp.position.set(x, 0.036, 0); tube.add(tp); tip.push(tp);
      var lb = S.label(['S', 'D', 'E'][i], { w: 0.014, ratio: 1, color: '#1b1b1b', bg: '#f2d02a', px: 128 }); lb.position.set(x, 0.14, 0.0); lb.rotation.x = 0; tube.add(lb); });
    var tl = S.label('ARGON · ABOUT 10 Pa · probes S (single), D (double), E (emissive)', { w: 0.28, ratio: 0.05, color: '#e8e8ea' }); tl.rotation.x = -Math.PI / 2; tl.position.set(0, 0.0012, 0.07); tube.add(tl);
    var cs = S.mesh(new T.BoxGeometry(0.46, 0.04, 0.07), M.alu); cs.position.set(0, 0.02, 0); tube.add(cs);
    S.contact(0.56, 0.12, -0.2, -0.2, 0.4);
    S.wire([[-0.6 + 0.06, 0.04, -0.18 + 0.05], [-0.5, 0.02, -0.12], [-0.2 - 0.23, 0.06, -0.2]], 'red');
  } else {
    jar = new T.Group(); jar.position.set(-0.25, 0, -0.2); S.scene.add(jar);
    var base = S.mesh(new T.CylinderGeometry(0.1, 0.11, 0.02, 40), M.alu); base.position.y = 0.01; jar.add(base);
    var bell = S.mesh(new T.CylinderGeometry(0.085, 0.085, 0.2, 40, 1, true), new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, transmission: 0.92, thickness: 0.003, ior: 1.5, transparent: true, opacity: 0.4, side: T.DoubleSide })); bell.position.y = 0.12; jar.add(bell);
    var dome = S.mesh(new T.SphereGeometry(0.085, 40, 16, 0, Math.PI * 2, 0, Math.PI / 2), new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, transmission: 0.92, thickness: 0.003, ior: 1.5, transparent: true, opacity: 0.4, side: T.DoubleSide })); dome.position.y = 0.22; jar.add(dome);
    var pb = S.mesh(new T.CylinderGeometry(0.04, 0.04, 0.004, 32), M.brass); pb.position.y = 0.04; jar.add(pb);
    plateTop = S.mesh(new T.CylinderGeometry(0.04, 0.04, 0.004, 32), M.brass); plateTop.position.y = 0.05; jar.add(plateTop);
    var pr1 = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.03, 10), M.chrome); pr1.position.y = 0.025; jar.add(pr1); var pr2 = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.12, 10), M.chrome); pr2.position.y = 0.11; jar.add(pr2);
    spark = new T.Mesh(new T.CylinderGeometry(0.004, 0.004, 0.01, 8), new T.MeshBasicMaterial({ color: 0xc9a0ff, transparent: true, opacity: 0 })); spark.position.y = 0.045; jar.add(spark);
    var gl2 = S.label('PLATES 1.00 cm APART', { w: 0.1, ratio: 0.1, color: '#e8e8ea' }); gl2.position.set(0, 0.02, 0.1); jar.add(gl2);
    gauge = new T.Group(); gauge.position.set(-0.08, 0, -0.34); S.scene.add(gauge);
    var gb = S.mesh(new T.CylinderGeometry(0.04, 0.04, 0.02, 36), M.alu); gb.rotation.x = Math.PI / 2; gb.position.set(0, 0.07, 0); gauge.add(gb);
    var gst = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.06, 14), M.alu); gst.position.set(0, 0.03, 0); gauge.add(gst);
    var gtex = S.liveTex(256, 256); var gfac = new T.Mesh(new T.CircleGeometry(0.036, 36), new T.MeshBasicMaterial({ map: gtex, toneMapped: false })); gfac.position.set(0, 0.07, 0.0106); gauge.add(gfac);
    gauge.userData.tex = gtex; S.contact(0.12, 0.12, -0.08, -0.34, 0.4); S.contact(0.26, 0.26, -0.25, -0.2, 0.4);
    S.wire([[-0.6 + 0.06, 0.04, -0.18 + 0.05], [-0.45, 0.02, -0.12], [-0.25, 0.05, -0.2]], 'red');
  }
  var TIT = { lang: ['PROBE SOURCE-METER', 'bias ±40 V · picoammeter · heater supply'], pas: ['BREAKDOWN MONITOR', 'voltage ramp · spark detector · pd plot'] };
  var ins = Kt.instrument({ x: 0.22, z: -0.22, ry: -0.12, w: 0.42, h: 0.2, d: 0.26, title: TIT[MODE][0], sub: TIT[MODE][1], screen: { u: -0.045, v: 0.0, w: 0.28, h: 0.155 },
    knobs: MODE === 'lang' ? [[0.145, 0.035, 0.012, 'PROBE S / D / E']] : [], buttons: [[0.1, -0.06, 'POWER', M.green], [0.17, -0.06, MODE === 'lang' ? 'SWEEP' : 'RAISE V', M.grey]] });
  var pwr = ins.buttons[0], go = ins.buttons[1], led1 = S.mesh(new T.SphereGeometry(0.004, 12, 12), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 }));
  led1.position.copy(ins.at(0.1, -0.038, 0.002)); ins.g.add(led1);
  S.contact(0.5, 0.34, 0.22, -0.22, 0.5);
  S.wire([[-0.2, 0.1, -0.2], [0.0, 0.05, -0.18], [0.22 - 0.17, 0.05, -0.22 + 0.13]], 'black');

  S.addApparatus('jar', jar, MODE === 'lang' ? 'Glass discharge tube with three probes' : 'Bell jar with two parallel plates', MODE === 'lang' ? 'A glass tube of argon at about 10 pascal with a brass anode and cathode. Three thin tungsten wires dip in from the top ports: S, a single probe; D, one of a pair for the double probe; E, a loop that can be heated.' : 'Two brass plates exactly 1 cm apart under a bell jar. A pump (out of sight) sets the pressure; the gauge reads it.');
  S.addApparatus('sup', sup, MODE === 'lang' ? 'Discharge supply' : 'Breakdown supply', 'A high-voltage supply with an interlock: it works only with the cover on. The glow in the tube starts when it is switched on.');
  S.addApparatus('ins', ins.g, TIT[MODE][0].charAt(0) + TIT[MODE][0].slice(1).toLowerCase(), 'Shows the curve it measures. Read the screen as you would a real one.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard(MODE === 'lang' ? 'Discharge' : 'Supply'), hudB = S.hudCard(MODE === 'lang' ? 'Probe' : 'pd (torr cm)'), hudC = S.hudCard('Readings');

  // ================================================================ the screen
  function drawScreen(x, w, h) {
    Kt.bg(x, w, h); var fs = Math.round(h * 0.05), ch, i;
    if (!st.on) { Kt.text(x, 'power off', w / 2, h / 2, '#5aa77a', fs * 1.4, 'center'); return; }
    if (MODE === 'lang') {
      var sw = st.sw, mn = 0, mx = 1;
      if (st.probe === 0) {
        ch = Kt.chart(x, { x: w * 0.1, y: h * 0.08, w: w * 0.86, h: st.fit ? h * 0.38 : h * 0.62 }, { xr: [-40, 20], yr: [-60, KN.ies(p) * 1.05e6], xlabel: 'probe voltage (V)', ylabel: 'probe current (µA)' });
        if (sw) Kt.poly(x, ch, sw.map(function (q) { return [q[0], q[1] * 1e6]; }), '#ffe45e', 1.8);
        if (st.fit) { var lo = Math.log(KN.ies(p) * 1.0e-3), hi = Math.log(KN.ies(p) * 1.1), ch2 = Kt.chart(x, { x: w * 0.1, y: h * 0.56, w: w * 0.86, h: h * 0.3 }, { xr: [-40, 20], yr: [Math.exp(lo) * 1e6, Math.exp(hi) * 1e6], ylog: true, xlabel: 'V (V)', ylabel: 'electron current (µA, log)' });
          var iis = st.fit.Iis; Kt.dots(x, ch2, sw.filter(function (q) { return q[1] + iis > Math.exp(lo); }).map(function (q) { return [q[0], (q[1] + iis) * 1e6]; }), '#ffe45e', 2);
          if (st.fit.Te > 0) Kt.poly(x, ch2, [-14, -6, 0, 6, st.fit.Vp].map(function (v) { return [v, Math.exp(st.fit.a + v / st.fit.Te) * 1e6]; }), '#64e3ff', 2.2); }
      } else if (st.probe === 1) {
        ch = Kt.chart(x, { x: w * 0.1, y: h * 0.08, w: w * 0.86, h: h * 0.66 }, { xr: [-30, 30], yr: [-KN.iis(p) * 1.4e6, KN.iis(p) * 1.4e6], xlabel: 'voltage across the pair (V)', ylabel: 'current (µA)' });
        if (sw) Kt.poly(x, ch, sw.map(function (q) { return [q[0], q[1] * 1e6]; }), '#ffe45e', 1.8);
      } else {
        ch = Kt.chart(x, { x: w * 0.1, y: h * 0.08, w: w * 0.86, h: h * 0.66 }, { xr: [0, 3.5], yr: [p.Vp - 16, p.Vp + 4], xlabel: 'heater current (A)', ylabel: 'floating potential (V)' });
        if (sw) Kt.poly(x, ch, sw.map(function (q) { return [q[0], q[1]]; }), '#ffe45e', 1.8);
      }
      var msg = st.fit ? (st.probe === 2 ? 'plateau ' + r(st.fit.Vp, 2) + ' V' : 'Te ' + r(st.fit.Te, 3) + ' eV' + (st.probe === 0 ? '   Vp ' + r(st.fit.Vp, 2) + ' V' : '') + '   ne ' + (st.fit.ne / 1e16).toFixed(3) + ' × 10¹⁶ m⁻³') : sw ? 'curve recorded: press FIT' : 'press SWEEP';
      Kt.text(x, 'probe ' + PROBES[st.probe] + (st.dis ? '' : '   (discharge off)'), w * 0.04, h * 0.9, '#9fe0b8', fs); Kt.text(x, msg, w * 0.96, h * 0.97, '#ffe45e', fs * 1.1, 'right');
    } else {
      var rows = S.rows.filter(function (q) { return q.k; });
      ch = Kt.chart(x, { x: w * 0.1, y: h * 0.08, w: w * 0.86, h: h * 0.62 }, { xr: [0.3, 300], yr: [200, 2400], xlog: true, xlabel: 'pd (torr cm, log)', ylabel: 'breakdown voltage (V)' });
      Kt.dots(x, ch, rows.map(function (q) { return [q.pd, q.V]; }), '#ffe45e', 4);
      if (st.lastV !== null) { Kt.text(x, 'last: pd ' + r(st.pd, 3) + '  →  ' + (st.lastV > 0 ? r(st.lastV, 0) + ' V' : 'no breakdown up to 5 kV'), w * 0.04, h * 0.82, '#64e3ff', fs * 1.2); }
      Kt.text(x, 'supply ' + r(st.vshow, 0) + ' V' + (st.flash > 0 ? '   SPARK' : ''), w * 0.04, h * 0.92, st.flash > 0 ? '#ff9f5e' : '#9fe0b8', fs * 1.3);
    }
    if (st.prog > 0 && st.prog < 1) { x.fillStyle = 'rgba(100,227,255,.8)'; x.fillRect(0, h - 6, w * st.prog, 6); }
  }
  function drawGauge(x, w, h) {
    x.fillStyle = '#f2f0e8'; x.fillRect(0, 0, w, h); x.strokeStyle = '#222'; x.lineWidth = 3; x.font = '600 20px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillStyle = '#222';
    for (var i = 0; i <= 10; i++) { var a = 2.4 - i * 0.48, cx = w / 2, cy = h * 0.55; x.beginPath(); x.moveTo(cx + Math.cos(a) * 90, cy - Math.sin(a) * 90); x.lineTo(cx + Math.cos(a) * 108, cy - Math.sin(a) * 108); x.stroke(); }
    var f = Math.log(st.pd / 0.3) / Math.log(1000), a2 = 2.4 - Math.max(0, Math.min(1, f)) * 4.8; x.strokeStyle = '#c23b30'; x.lineWidth = 5; x.beginPath(); x.moveTo(w / 2, h * 0.55); x.lineTo(w / 2 + Math.cos(a2) * 92, h * 0.55 - Math.sin(a2) * 92); x.stroke();
    x.fillStyle = '#222'; x.font = '600 24px "Public Sans", sans-serif'; x.fillText('torr', w / 2, h * 0.86); x.fillText(st.pd < 10 ? r(st.pd, 2) : r(st.pd, 1), w / 2, h * 0.34);
  }
  function paint() { ins.screen.paint(drawScreen); if (gauge) gauge.userData.tex.draw(drawGauge); }
  var panelCv = null;
  function paintPanel() { if (panelCv && panelCv.isConnected) drawScreen(panelCv.getContext('2d'), panelCv.width, panelCv.height); }
  function panel(u) { panelCv = Kt.panel(u, 0.62); paintPanel(); }

  // ================================================================ actions
  function integrate(ms, fn) { return S.tween(ms, function (k) { st.prog = k; if (k >= 1) st.prog = 0; mark(); }).then(function () { st.prog = 0; return fn(); }); }
  function needOn() { if (!st.on) { S.say('Switch the instrument on first.'); return true; } return false; }
  function powerOn(on) {
    if (Kt.busy()) return Promise.resolve(); if (st.on === on) return Promise.resolve();
    return S.hand.tap(pwr, 'front').then(function () { st.on = on; led1.material.emissive.setHex(on ? 0x22cc44 : 0); led1.material.color.setHex(on ? 0x33dd55 : 0x331111); S.say(on ? 'Instrument on.' : 'Switched off.'); mark(); S.render(); });
  }
  function strike(on) {
    if (Kt.busy() || st.dis === on) return Promise.resolve();
    return S.hand.tap(sbut, 'front').then(function () {
      st.dis = on; sled.material.emissive.setHex(on ? 0xcc2222 : 0); sled.material.color.setHex(on ? 0xff3333 : 0x331111);
      if (glowMat) glowMat.opacity = on ? 0.4 : 0;
      S.say(on ? (MODE === 'lang' ? 'The discharge strikes: a violet glow fills the tube. Keep the cover on and do not touch anything.' : 'High voltage armed. The supply is interlocked: it needs the cover on.') : 'Supply off.'); mark(); S.render();
    });
  }
  function setProbe(i) {
    if (Kt.busy() || i < 0 || i > 2) return Promise.resolve();
    var kn = ins.knobs[0], a0 = kn.rotation.z, a1 = 1.0 - 1.0 * i, pt = Kt.wpt(ins.g, kn.position.x, kn.position.y, ins.FZ + 0.024);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { kn.rotation.z = a0 + (a1 - a0) * k; }, { mode: 'front', ms: 450, reachMs: 450 }).then(function () {
      st.probe = i; kn.rotation.z = a1; st.sw = null; st.fit = null; tip.forEach(function (t, j) { t.material.emissive.setHex(j === i ? 0xffcc33 : 0); }); mark(); S.render();
    });
  }
  function sweep() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    if (!st.dis) { S.say('Strike the discharge first: there is no plasma to probe.'); return Promise.resolve(null); }
    return S.hand.tap(go, 'front').then(function () { return integrate(1000, function () {
      var q = assign(p, { seed: p.seed + 5 * st.idx++ });
      st.sw = st.probe === 0 ? KN.sweepSingle(q) : st.probe === 1 ? KN.sweepDouble(q) : KN.sweepEmissive(q); st.fit = null;
      S.say(st.probe === 2 ? 'Heater current raised from 0 to 3.5 A: the floating potential is on the screen.' : 'Sweep done: the curve is on the screen.'); mark(); S.render(); return st.sw;
    }); });
  }
  function fit() {
    if (!st.sw) { S.say('Sweep first.'); return null; }
    if (st.probe === 0) { st.fit = KN.fitSingle(p, st.sw); var sw0 = st.sw, k, v0 = null; for (k = 1; k < sw0.length; k++) if (sw0[k - 1][1] < 0 && sw0[k][1] >= 0) { v0 = sw0[k - 1][0] + (0 - sw0[k - 1][1]) / (sw0[k][1] - sw0[k - 1][1]) * (sw0[k][0] - sw0[k - 1][0]); break; } st.fit.Vf = v0; }
    else if (st.probe === 1) st.fit = KN.fitDouble(p, st.sw); else st.fit = { Vp: KN.fitEmissive(st.sw) };
    S.say(st.probe === 2 ? 'The floating potential flattens at ' + r(st.fit.Vp, 2) + ' V: close to the plasma potential.' : 'Fit: Te = ' + r(st.fit.Te, 3) + ' eV, ne = ' + (st.fit.ne / 1e16).toFixed(3) + ' × 10¹⁶ per cubic metre' + (st.probe === 0 ? ', plasma potential ' + r(st.fit.Vp, 2) + ' V, floating potential ' + (st.fit.Vf === null ? '—' : r(st.fit.Vf, 2)) + ' V.' : '.')); mark(); S.render(); return st.fit;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.fit) { S.say('Fit the curve first.'); return false; }
    if (S.rows.some(function (z) { return z.m === PROBES[st.probe]; })) { S.say('This probe is already in the book.'); return false; }
    S.addRow({ m: PROBES[st.probe], Te: st.fit.Te || 0, Vp: st.fit.Vp || 0, ne: st.fit.ne || 0, Vf: st.fit.Vf === undefined ? null : st.fit.Vf }); return true;
  }
  // ---- Paschen
  function setPd(v) { if (!isFinite(v) || v < 0.3 || v > 300) { S.say('pd from 0.3 to 300 torr cm.'); return; } st.pd = v; st.lastV = null; mark(); }
  function raise() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    if (!st.dis) { S.say('Arm the breakdown supply first (the ON / OFF key).'); return Promise.resolve(null); }
    return S.hand.tap(go, 'front').then(function () {
      var g = Kt.rnd(p.seed + 13 * st.idx++ + 1), vb = KN.vb(p, st.pd), v = vb > 0 && vb < 5000 ? vb * (1 + p.noise * g.gauss()) : 0;
      return S.tween(900, function (k) { st.vshow = (v > 0 ? v : 5000) * k; st.prog = k >= 1 ? 0 : k; mark(); }).then(function () {
        st.prog = 0; st.lastV = v; st.cur = { pd: st.pd, V: v }; st.flash = v > 0 ? 1 : 0; if (spark) spark.material.opacity = v > 0 ? 0.9 : 0;
        S.say(v > 0 ? 'Breakdown at ' + r(v, 0) + ' V: the gas flashes over.' : 'No breakdown up to 5 kV: at this pd the gas holds off.'); mark(); S.render();
        return S.tween(250, function () {}).then(function () { st.flash = 0; st.vshow = 0; if (spark) spark.material.opacity = 0; mark(); return st.cur; });
      });
    });
  }
  function recordPd(kind) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.cur || !(st.cur.V > 0)) { S.say('Raise the voltage until the gas breaks down first.'); return false; }
    if (S.rows.some(function (z) { return z.k && Math.abs(Math.log(z.pd / st.cur.pd)) < 1e-3; })) { S.say('That pd is already in the book.'); return false; }
    S.addRow({ k: kind, pd: st.cur.pd, V: st.cur.V }); st.cur = null; return true;
  }
  function coarsePd(i, n) { var lo = 0.35; return lo * Math.exp(Math.log(300 / lo) * i / (n - 1)); }
  function minOf(rows) {
    var cs = rows.filter(function (z) { return z.k === 'coarse'; }).sort(function (a, b) { return a.pd - b.pd; }), k = 0, i; if (cs.length < 8) return null;
    for (i = 1; i < cs.length; i++) if (cs[i].V < cs[k].V) k = i; return cs[k];
  }
  function pasResult(rows) {
    var fine = rows.filter(function (z) { return z.k === 'fine'; }).sort(function (a, b) { return a.pd - b.pd; }); if (fine.length < 7) return null;
    var mn = KN.minimum(fine.map(function (z) { return [z.pd, z.V]; })), q = HK.TEXTBOOK.phd_paschen_vmin(p), e = Math.exp(1) * Math.log(1 + 1 / p.gam) / p.A;
    return { label: 'Minimum breakdown voltage', value: mn[1], unit: 'V', digits: 1, truth: q, note: 'The minimum is at pd = ' + r(mn[0], 3) + ' torr cm (the lab\'s gas gives ' + r(e, 3) + '), found by a quadratic fit of the fine scan against ln(pd). Gas constants are illustrative.' };
  }
  function langResult(rows) {
    var a = rows.filter(function (z) { return z.m === 'single'; })[0], b = rows.filter(function (z) { return z.m === 'double'; })[0], c = rows.filter(function (z) { return z.m === 'emissive'; })[0]; if (!a || !b) return null;
    return { label: 'Electron temperature', value: (a.Te + b.Te) / 2, unit: 'eV', digits: 3, truth: p.Te,
      note: 'Single probe ' + r(a.Te, 3) + ' eV, double probe ' + r(b.Te, 3) + ' eV. Density ' + (a.ne / 1e16).toFixed(3) + ' × 10¹⁶ m⁻³ (single) and ' + (b.ne / 1e16).toFixed(3) + ' × 10¹⁶ (double). Plasma potential ' + r(a.Vp, 2) + ' V from the knee' + (c ? ', ' + r(c.Vp, 2) + ' V from the emissive probe' : '') + '; floating potential ' + (a.Vf === null ? '—' : r(a.Vf, 2)) + ' V.' };
  }

  // ================================================================ text
  var TXT = MODE === 'lang' ? {
    principle: 'A small metal probe in a plasma collects ions (a steady current set by the Bohm speed) when it is very negative, and electrons when it is positive. In between, the Maxwellian electrons are repelled in proportion to exp(eV/kTe), so ln of the electron current is a straight line of slope 1/Te volts; the knee where it saturates is the plasma potential.',
    formula: 'ln Ie = const + V / Te,   Iis = 0.61 e ne A √(kTe / M)', note: 'Te in electron-volts is the inverse slope in volts; the ion saturation current then gives the density',
    more: ['A double probe floats: it draws equal and opposite currents, so it can never take more than the ion saturation current and needs no reference to the plasma. I = Iis tanh(V / 2Te).', 'A heated emissive probe floats close to the plasma potential, because its emitted electrons balance the electron flux.', 'The bench models an ideal probe: no sheath expansion, no magnetic field, no RF.'],
    precautions: 'The discharge supply is high voltage: keep the cover on, never touch the electrodes or probe leads while it is on. The tube and heated wire are hot.'
  } : {
    principle: 'A spark jumps across a gas when each electron leaving the cathode makes enough ions on its way to free one more. The voltage needed depends on the product pd of pressure and gap, falling to a minimum and rising again on both sides: too few collisions at low pd, too many at high.',
    formula: 'V = B pd / (ln(A pd) − ln ln(1 + 1/γ))', note: 'minimum V = e B ln(1 + 1/γ) / A at pd = e ln(1 + 1/γ) / A',
    more: ['The breakdown voltage depends on pd only, not on p and d separately.', 'The gas constants A and B and the cathode coefficient γ are set by the gas and the plate surface.', 'Each breakdown carries a little scatter, so the minimum is found by a fit, not by one point.'],
    precautions: 'The breakdown supply goes to 5 kV and is interlocked: it works only with the cover on. Never touch the plates or the leads while it is on.' };
  var BOOK = MODE === 'lang' ? [{ label: 'Probe', get: function (z) { return z.m; } }, { label: 'Te (eV)', get: function (z) { return z.Te ? r(z.Te, 3) : '—'; } }, { label: 'Vp (V)', get: function (z) { return z.Vp ? r(z.Vp, 2) : '—'; } }, { label: 'ne (1e16)', get: function (z) { return z.ne ? (z.ne / 1e16).toFixed(3) : '—'; } }]
    : [{ label: 'Scan', get: function (z) { return z.k; } }, { label: 'pd (torr cm)', get: function (z) { return r(z.pd, 3); } }, { label: 'V (V)', get: function (z) { return r(z.V, 0); } }];
  var VIVA = MODE === 'lang' ? [['The slope of ln(electron current) against V is', ['1/Te in volts', 'Te', 'The plasma potential'], 0, 'Ie is proportional to exp(V/Te).'], ['A double probe can never draw more than', ['The ion saturation current', 'The electron saturation current', 'Zero'], 0, 'It floats and draws equal and opposite currents.'], ['A heated emissive probe floats at', ['Close to the plasma potential', 'Far below it', 'Zero volts'], 0, 'Strong emission raises the floating potential to Vp.']]
    : [['At very low pd the breakdown voltage rises because', ['Electrons cross the gap without enough collisions', 'The gas is too hot', 'The plates are too far apart'], 0, 'Too few ionising collisions.'], ['The minimum of the Paschen curve depends on', ['The gas and the cathode surface', 'Only the supply', 'Only the temperature'], 0, 'Through A, B and γ.'], ['Doubling the gap at fixed pd', ['Leaves Vb unchanged', 'Doubles Vb', 'Halves Vb'], 0, 'Vb depends on pd only.']];

  // ================================================================ steps
  var STEPS = [{ id: 'on', title: 'Switch on', view: 'ins', render: function (u) {
      u.h2(MODE === 'lang' ? 'Strike the discharge' : 'Arm the supply');
      u.p(MODE === 'lang' ? 'The tube is filled with argon at about 10 pascal. Switch the probe source-meter on, then the discharge supply: the gas lights up violet.' : 'The jar is pumped to the pressure you choose and the plates are 1.00 cm apart. Switch the monitor on and arm the breakdown supply.');
      u.task('Instrument', st.on, st.on ? 'On' : 'Off').add(u.button(st.on ? 'Switch off' : 'Switch on', function () { S.focus('ins'); powerOn(!st.on); }, !st.on, S.hand.busy));
      u.task(MODE === 'lang' ? 'Discharge' : 'Supply', st.dis, st.dis ? (MODE === 'lang' ? 'Glowing' : 'Armed') : 'Off').add(u.button(st.dis ? 'Switch the supply off' : (MODE === 'lang' ? 'Strike the discharge' : 'Arm the supply'), function () { S.focus('sup'); strike(!st.dis); }, !st.dis, S.hand.busy || !st.on));
      u.note('High voltage. The cover stays on and the supply is interlocked; do not touch the electrodes, plates or leads while it is on.');
      u.next('Next', st.on && st.dis); }, ok: function () { return st.on && st.dis; }, auto: function () { return powerOn(true).then(function () { return strike(true); }); } }];
  if (MODE === 'lang') {
    var probeStep = function (i, title, lead, last) { return { id: PROBES[i], title: title, view: 'jar', render: function (u) {
        u.h2(title); u.p(lead);
        u.row(u.button('Probe ' + ['S (single)', 'D (double)', 'E (emissive)'][i], function () { S.focus('jar'); setProbe(i); }, st.probe !== i, S.hand.busy || st.probe === i), u.button(i === 2 ? 'RAISE THE HEATER' : 'SWEEP', function () { S.focus('ins'); sweep(); }, true, S.hand.busy || st.probe !== i), u.button('Fit', function () { fit(); }, false, !st.sw || S.hand.busy), u.button('Write it down', function () { record(); }, false, !st.fit || S.hand.busy));
        u.live(function () { return st.fit && st.probe === i ? (i === 2 ? 'floating potential plateau ' + r(st.fit.Vp, 2) + ' V' : 'Te ' + r(st.fit.Te, 3) + ' eV · ne ' + (st.fit.ne / 1e16).toFixed(3) + ' × 10¹⁶') : st.sw ? 'curve recorded' : 'no curve'; });
        panel(u); u.h3('Observation table'); u.table(); u.next(last ? 'Next: result' : 'Next', S.rows.some(function (z) { return z.m === PROBES[i]; })); },
      ok: function () { return S.rows.some(function (z) { return z.m === PROBES[i]; }); }, auto: function () { return setProbe(i).then(function () { return sweep(); }).then(function () { fit(); record(); }); } }; };
    STEPS.push(probeStep(0, 'Single probe', 'Select the single probe S and sweep the bias from −40 V to +20 V. The curve has an ion saturation current at the far negative end, a rise, and electron saturation. Fit: the ion current is added back, ln of the electron current in the transition region is fitted by a line, and the knee gives the plasma potential.'));
    STEPS.push(probeStep(1, 'Double probe', 'Select the double probe D: two identical wires floating together. Sweep the bias across the pair from −30 V to +30 V. The current saturates at the ion current; the slope through the origin gives the electron temperature.'));
    STEPS.push(probeStep(2, 'Emissive probe', 'Select the emissive loop E and raise its heater current from 0 to 3.5 A. The floating potential climbs as the wire emits and flattens near the plasma potential.', true));
  } else {
    STEPS.push({ id: 'coarse', title: 'Coarse scan', view: 'jar', render: function (u) {
        u.h2('Coarse scan: breakdown from low to high pd');
        u.p('Choose a pd (the pressure in torr, as the plates are 1 cm apart), press RAISE V and write the breakdown voltage down. Take at least ten values spread from 0.35 to 300 torr cm.');
        u.slider('pd (torr cm), log scale', 0, 100, 1, function () { return Math.round(100 * Math.log(st.pd / 0.35) / Math.log(300 / 0.35)); }, function (v) { setPd(0.35 * Math.exp(Math.log(300 / 0.35) * v / 100)); paintPanel(); }, '%', 0);
        u.row(u.button('RAISE V', function () { S.focus('ins'); raise(); }, true, S.hand.busy), u.button('Write it down', function () { recordPd('coarse'); }, false, !st.cur || S.hand.busy));
        u.live(function () { return 'pd = ' + r(st.pd, 3) + ' torr cm · ' + (st.lastV === null ? 'no reading' : st.lastV > 0 ? r(st.lastV, 0) + ' V' : 'no breakdown up to 5 kV'); });
        panel(u); u.h3('Observation table'); u.table(); var nc = S.rows.filter(function (z) { return z.k === 'coarse'; }).length; u.next('Next: fine scan', nc >= 10); },
      ok: function () { return S.rows.filter(function (z) { return z.k === 'coarse'; }).length >= 10; },
      auto: function () { var c = Promise.resolve(), j; for (j = 0; j < 12; j++) (function (jj) { c = c.then(function () { setPd(coarsePd(jj, 12)); st.lastV = null; return raise(); }).then(function () { if (st.cur && st.cur.V > 0) recordPd('coarse'); }); })(j); return c; } });
    STEPS.push({ id: 'fine', title: 'Fine scan', view: 'ins', render: function (u) {
        u.h2('Fine scan round the minimum');
        var m = minOf(S.rows); u.p(m ? 'The lowest voltage so far is ' + r(m.V, 0) + ' V at pd = ' + r(m.pd, 2) + '. Take at least eight more readings in steps of about 8 % in pd either side of it (pd between ' + r(m.pd * 0.7, 2) + ' and ' + r(m.pd * 1.4, 2) + ').' : 'Finish the coarse scan first.');
        u.slider('pd (torr cm), log scale', 0, 100, 1, function () { return Math.round(100 * Math.log(st.pd / 0.35) / Math.log(300 / 0.35)); }, function (v) { setPd(0.35 * Math.exp(Math.log(300 / 0.35) * v / 100)); paintPanel(); }, '%', 0);
        u.row(u.button('RAISE V', function () { S.focus('ins'); raise(); }, true, S.hand.busy), u.button('Write it down', function () { recordPd('fine'); }, false, !st.cur || S.hand.busy));
        u.live(function () { return 'pd = ' + r(st.pd, 3) + ' torr cm · ' + (st.lastV === null ? 'no reading' : st.lastV > 0 ? r(st.lastV, 0) + ' V' : 'no breakdown'); });
        panel(u); u.h3('Observation table'); u.table(); var nf = S.rows.filter(function (z) { return z.k === 'fine'; }).length; u.next('Next: result', nf >= 8); },
      ok: function () { return S.rows.filter(function (z) { return z.k === 'fine'; }).length >= 8; },
      auto: function () { var m = minOf(S.rows), c = Promise.resolve(), j; if (!m) return c; for (j = 0; j < 9; j++) (function (jj) { c = c.then(function () { setPd(m.pd * Math.exp(0.07 * (jj - 4) * 1.0 * 1.0)); st.lastV = null; return raise(); }).then(function () { if (st.cur && st.cur.V > 0) recordPd('fine'); }); })(j); return c; } });
  }
  function askState() { var q = { experiment: S.lab.title, sample: V_.sample || '', power_on: st.on, supply_on: st.dis, readings: S.rows.length }; if (MODE === 'lang') { q.probe = PROBES[st.probe]; q.gas = 'argon, about 10 Pa'; } else { q.pd_torr_cm = r(st.pd, 3); q.gap_cm = 1; } return q; }
  return {
    camera: { pos: [-0.18, 0.62, 1.2], look: [-0.18, 0.06, -0.2] },
    views: { jar: [[-0.22, 0.3, 0.3], [-0.22, 0.07, -0.2]], sup: [[-0.5, 0.25, 0.2], [-0.6, 0.05, -0.18]], ins: [[0.2, 0.37, 0.48], [0.22, 0.1, -0.22]], bench: [[-0.18, 0.62, 1.2], [-0.18, 0.06, -0.2]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: TXT.principle, formula: TXT.formula, formulaNote: TXT.note, more: TXT.more, precautions: TXT.precautions },
    book: { title: 'Expt. - ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 74), V_.sample ? 'Sample: ' + V_.sample.slice(0, 50) : '', MODE === 'lang' ? 'Argon discharge, about 10 Pa.' : 'Plates 1.00 cm apart.', 'Safety: high voltage, cover on.'], columns: BOOK },
    result: MODE === 'lang' ? langResult : pasResult, tol: 0.02, resultNote: 'The numbers come from fitting the simulated curves. A real probe has sheath expansion, and the method is usually good to 10 to 30 %; this bench is ideal.',
    chips: ['How do I find Te?', 'What is the plasma potential?', 'Why does the double probe saturate?', 'Check my readings', 'What would a magnetic field do?'],
    viva: VIVA, askState: askState, steps: STEPS,
    tick: function () { hudA.set(st.on ? (st.dis ? (MODE === 'lang' ? 'Glowing' : 'Armed') : 'On, supply off') : 'Off'); hudB.set(MODE === 'lang' ? PROBES[st.probe] : r(st.pd, 2)); hudC.set(S.rows.length + ' written'); if (dirty) { dirty = false; paint(); paintPanel(); } },
    ready: function () { paint(); if (MODE === 'lang') tip[0].material.emissive.setHex(0xffcc33); }
  };
});
