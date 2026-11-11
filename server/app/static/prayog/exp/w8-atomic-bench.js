/* Prayogshala studio module: W8 ATOMIC BENCH (B.Sc. modern physics, pack ug_modern_w8).
     w8-millikan           Millikan chamber with lamp, atomiser and a camera; plate supply; stopwatch.
                           The family variant (meth = 1) uses the rise-and-fall method instead of balancing.
     w8-zeeman             electromagnet with a cadmium lamp between the poles, lens, Fabry-Perot etalon, polaroid
                           and a telescope with a micrometer eyepiece; gaussmeter
     w8-planck-blackbody   tungsten lamp in a vented housing, 650 nm filter and photodetector, optical pyrometer
   Every number comes from the lab's kernel (HoolaKernels.K[S.lab.kernel]) on the lab's own params. */
HoolaStudio.define('w8-atomic-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K[S.lab.kernel], assign = HK.assign;
  var p = HK.paramsFor(S.lab.kernel, S.lab.params);
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var MODE = { 'w8-millikan': 'oil', 'w8-zeeman': 'zee', 'w8-planck-blackbody': 'bb' }[BASE] || 'oil';
  var RISE = MODE === 'oil' && p.meth > 0.5;
  var PI = Math.PI, C = 2.99792458e8, KB = 1.380649e-23;
  var KM = 0.2;                        // electromagnet: tesla per ampere (illustrative calibration)
  var LAMP0 = 1000, LAMPK = 400;      // lamp: pyrometer temperature T = 1000 K + 400 K/A x current (illustrative)

  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function wp(o) { var v = new T.Vector3(); o.updateMatrixWorld(true); o.getWorldPosition(v); return v; }
  var st = { on: false, traced: false, V: 0, field: false, drop: 0, y: -0.0002, sprayed: false, Im: 0, Il: 2.0, cross: 0 };

  // ================================================================ shared: a supply unit with a knob and displays
  function supply(x, z, title, ry) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = ry || 0;
    var UW = 0.3, UD = 0.22, UH = 0.13, FZ = UD / 2 + 0.006;
    var c = S.rounded(UW, UD, UH, 0.012, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5, metalness: 0.12 }));
    c.rotation.x = -Math.PI / 2; c.position.y = UH / 2 + 0.004; g.add(c);
    var tex = S.canvasTex(1024, 440, function (cx, w, h) { cx.fillStyle = '#2b323d'; cx.fillRect(0, 0, w, h); cx.strokeStyle = 'rgba(255,255,255,.14)'; cx.lineWidth = 3; cx.strokeRect(8, 8, w - 16, h - 16);
      cx.fillStyle = '#f1efe8'; cx.font = '700 46px "Public Sans", sans-serif'; cx.fillText(title, 30, 66); });
    var pn = S.mesh(new T.BoxGeometry(UW - 0.014, UH - 0.014, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]);
    pn.position.set(0, 0.004 + UH / 2, FZ - 0.002); g.add(pn);
    function up(u, v, dz) { return new T.Vector3(u, 0.004 + UH / 2 + v, FZ + (dz || 0)); }
    var o = { g: g, up: up };
    o.lcd = function (u, v, w, h) {
      var lt = S.liveTex(512, 190), last = '';
      var bez = S.mesh(new T.BoxGeometry(w + 0.006, h + 0.006, 0.003), M.grey); bez.position.copy(up(u, v, 0.001)); g.add(bez);
      var scr = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ map: lt, toneMapped: false })); scr.position.copy(up(u, v, 0.004)); g.add(scr);
      return function (txt, un) { if (txt + un === last) return; last = txt + un; lt.draw(function (x) {
        var gr = x.createLinearGradient(0, 0, 0, 190); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); x.fillStyle = gr; x.fillRect(0, 0, 512, 190);
        x.font = '700 84px "JetBrains Mono", monospace'; x.textAlign = 'right'; x.fillStyle = '#1b2116'; x.fillText(txt, 400, 116);
        x.font = '600 34px "Public Sans", sans-serif'; x.fillText(un, 496, 170); }); };
    };
    o.knob = function (u, v, label) {
      var kg = new T.Group(); kg.position.copy(up(u, v)); g.add(kg);
      var sk = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.004, 40), M.bakelite); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; kg.add(sk);
      var kb = S.mesh(new T.CylinderGeometry(0.014, 0.016, 0.018, 40), M.black); kb.rotation.x = Math.PI / 2; kb.position.z = 0.013; kg.add(kb);
      var ptr = S.mesh(new T.BoxGeometry(0.002, 0.014, 0.0012), M.white, false); ptr.position.set(0, 0.008, 0.0228); kg.add(ptr);
      var l = S.label(label, { w: 0.08, ratio: 0.16, color: '#f1efe8' }); l.position.copy(up(u, v - 0.03, 0.0025)); g.add(l);
      return kg;
    };
    o.sw = function (u, v, label) {
      var s = S.rounded(0.018, 0.026, 0.009, 0.003, M.bakelite); s.position.copy(up(u, v, 0.004)); g.add(s);
      var l = S.label(label, { w: 0.06, ratio: 0.2, color: '#f1efe8' }); l.position.copy(up(u, v - 0.025, 0.0025)); g.add(l); return s;
    };
    S.contact(UW + 0.1, UD + 0.1, x, z, 0.5);
    return o;
  }
  function turnKnob(kg, getv, setv, v, vmin, vmax) {
    if (busy()) return Promise.resolve();
    var v0 = getv(), pt = wp(kg).add(new T.Vector3(0, 0, 0.02));
    function ang(x) { return 3 * PI / 4 - 1.5 * PI * (x - vmin) / (vmax - vmin); }
    return S.hand.pinchMove(pt, function () { return pt; }, function (t) { setv(v0 + (v - v0) * t); kg.rotation.z = ang(getv()); }, { mode: 'front', ms: 450, reachMs: 500 })
      .then(function () { setv(v); kg.rotation.z = ang(v); S.render(); });
  }

  // ================================================================ MILLIKAN
  var oil = {};
  function buildOil() {
    var g = new T.Group(); g.position.set(-0.32, 0, -0.12); S.scene.add(g); oil.g = g;
    var base = S.rounded(0.22, 0.2, 0.03, 0.01, M.iron); base.rotation.x = -Math.PI / 2; base.position.y = 0.015; g.add(base);
    [-1, 1].forEach(function (sg) { var leg = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.08, 12), M.chrome); leg.position.set(sg * 0.07, 0.07, 0); g.add(leg); });
    var housing = S.mesh(new T.CylinderGeometry(0.07, 0.07, 0.06, 40, 1, true), M.glass); housing.position.y = 0.14; g.add(housing);
    var top = S.mesh(new T.CylinderGeometry(0.055, 0.055, 0.008, 40), M.brass); top.position.y = 0.15; g.add(top);
    var bot = S.mesh(new T.CylinderGeometry(0.055, 0.055, 0.008, 40), M.brass); bot.position.y = 0.128; g.add(bot);
    var hole = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.009, 12), M.black); hole.position.y = 0.151; g.add(hole);
    var ring = S.mesh(new T.CylinderGeometry(0.056, 0.056, 0.014, 40, 1, true), new T.MeshStandardMaterial({ color: 0xe8e2cf, roughness: 0.3, transparent: true, opacity: 0.5 })); ring.position.y = 0.139; g.add(ring);
    var lid = S.mesh(new T.CylinderGeometry(0.072, 0.072, 0.006, 40), M.bakelite); lid.position.y = 0.173; g.add(lid);
    var bulb = S.mesh(new T.SphereGeometry(0.018, 20, 14), M.rubber); bulb.position.set(0.04, 0.2, 0.0); g.add(bulb); oil.bulb = bulb;
    var nozzle = S.mesh(new T.CylinderGeometry(0.003, 0.004, 0.04, 10), M.glass); nozzle.rotation.z = Math.PI / 2; nozzle.position.set(0.012, 0.19, 0); g.add(nozzle);
    var lamp = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.07, 24), new T.MeshStandardMaterial({ color: 0x30343a, metalness: 0.5, roughness: 0.4 }));
    lamp.rotation.z = Math.PI / 2; lamp.position.set(-0.11, 0.139, 0); g.add(lamp);
    var cam = S.mesh(new T.BoxGeometry(0.04, 0.04, 0.06), new T.MeshStandardMaterial({ color: 0x222831, roughness: 0.5 })); cam.position.set(0, 0.139, 0.11); g.add(cam);
    var lens = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.03, 20), M.black); lens.rotation.x = Math.PI / 2; lens.position.set(0, 0.139, 0.075); g.add(lens);
    var post = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.12, 12), M.chrome); post.position.set(0, 0.06, 0.11); g.add(post);
    S.contact(0.3, 0.3, -0.32, -0.12, 0.5);
    // the camera monitor: the drop against the 0.25 mm graticule
    var mon = new T.Group(); mon.position.set(-0.05, 0, -0.22); S.scene.add(mon);
    var mb = S.rounded(0.2, 0.15, 0.02, 0.008, M.black); mb.position.set(0, 0.16, 0); mon.add(mb);
    var stand = S.mesh(new T.BoxGeometry(0.03, 0.08, 0.02), M.black); stand.position.set(0, 0.045, -0.005); mon.add(stand);
    var foot = S.rounded(0.1, 0.06, 0.008, 0.004, M.black); foot.rotation.x = -Math.PI / 2; foot.position.y = 0.004; mon.add(foot);
    oil.tex = S.liveTex(512, 384);
    var scr = new T.Mesh(new T.PlaneGeometry(0.18, 0.135), new T.MeshBasicMaterial({ map: oil.tex, toneMapped: false })); scr.position.set(0, 0.16, 0.011); mon.add(scr);
    var ml = S.label('CAMERA VIEW  (graticule 0.25 mm)', { w: 0.16, ratio: 0.08, color: '#ddd' }); ml.position.set(0, 0.075, 0.011); mon.add(ml);
    S.contact(0.12, 0.08, -0.05, -0.22, 0.4);
    oil.sup = supply(0.3, -0.04, 'MILLIKAN PLATE SUPPLY 0 - 600 V', -0.3);
    oil.knob = oil.sup.knob(-0.07, -0.02, 'VOLTS');
    oil.showV = oil.sup.lcd(-0.07, 0.025, 0.1, 0.034); oil.showV('0.0', 'V');
    oil.swF = oil.sup.sw(0.08, -0.02, 'FIELD');
    oil.watch = S.stopwatch([0.12, 0.05, 0.16], [-0.35, -0.2, 0]);
    S.wire([[-0.25, 0.03, -0.08], [0.0, 0.014, 0.0], [0.2, 0.014, 0.02]], 'red');
    S.wire([[-0.25, 0.03, -0.12], [0.02, 0.012, 0.05], [0.22, 0.012, 0.05]], 'black');
    S.addApparatus('rig', g, 'Millikan chamber', 'Two brass plates ' + (p.d * 1000).toFixed(1) + ' mm apart in a perspex ring, lit from the side; the atomiser bulb sprays oil through the small hole in the top plate.');
    S.addApparatus('mon', mon, 'Camera monitor', 'Shows the drops between the plates against a graticule; the lines are 0.25 mm apart, four of them make 1.0 mm.');
    S.addApparatus('unit', oil.sup.g, 'Plate supply', 'The knob sets the plate voltage; the field switch connects it across the plates or shorts them.');
  }
  function oilQ() { return assign(p, { V: st.field ? st.V : 0, drop: st.drop }); }
  function oilVel() { return KN.view(KN.init(oilQ(), {}), oilQ(), {}).vel; }   // upward, m/s
  function drawOil() {
    oil.tex.draw(function (x) { x.fillStyle = '#05070a'; x.fillRect(0, 0, 512, 384);
      var top = 70, mm = 240;           // 1.0 mm = 240 px
      x.strokeStyle = 'rgba(160,200,255,.45)'; x.lineWidth = 2;
      for (var i = 0; i <= 4; i++) { var yy = top + i * mm / 4; x.beginPath(); x.moveTo(60, yy); x.lineTo(452, yy); x.stroke(); }
      x.fillStyle = 'rgba(200,220,255,.6)'; x.font = '600 20px sans-serif'; x.fillText('0', 30, top + 6); x.fillText('1.0 mm', 456, top + mm + 6);
      if (st.sprayed) { var py = top + st.y / 1e-3 * mm; if (py > -10 && py < 394) { var gr = x.createRadialGradient(256, py, 0, 256, py, 10); gr.addColorStop(0, '#fffbe0'); gr.addColorStop(1, 'rgba(255,240,180,0)'); x.fillStyle = gr; x.beginPath(); x.arc(256, py, 10, 0, PI * 2); x.fill(); } }
      x.fillStyle = '#9fb'; x.font = '600 22px sans-serif'; x.fillText('DROP ' + (st.drop + 1) + (st.field ? '   FIELD ON ' + st.V.toFixed(1) + ' V' : '   PLATES SHORTED'), 20, 30); });
  }
  function spray() {
    if (busy()) return Promise.resolve();
    return S.hand.pinchMove(wp(oil.bulb), function () { return wp(oil.bulb); }, function (t) { oil.bulb.scale.setScalar(1 - 0.3 * Math.sin(PI * t)); }, { mode: 'top', ms: 500 })
      .then(function () { st.sprayed = true; st.y = 0.0006; S.say('A mist of oil drops falls through the hole. Five slow drops are in view; pick one and follow it.'); S.render(); });
  }
  function pickDrop(k) { st.drop = k; st.y = 0.0005; S.say('Following drop ' + (k + 1) + '.'); S.render(); }
  function setField(on) {
    if (busy()) return Promise.resolve();
    if (st.field === on) return Promise.resolve();
    return S.hand.tap(oil.swF, 'front').then(function () { st.field = on; S.click(700, 0.04); S.render(); });
  }
  function setV(v) {
    if (!isFinite(v) || v < 0 || v > 600) { S.say('The supply gives 0 to 600 V.'); return Promise.resolve(); }
    v = rnd(Math.round(v * 2) / 2, 1);
    return turnKnob(oil.knob, function () { return st.V; }, function (x) { st.V = x; }, v, 0, 600);
  }
  function bringTop() { st.y = -0.0002; S.say('The field lifts the drop above the top line; now it can be timed.'); S.render(); }
  function timeOver(up) {               // start the watch as the drop crosses one line, stop it at the other
    var w = oil.watch, ok;
    w.t = 0; w.on = false;
    if (up) st.y = p.s + 0.0001; else st.y = -0.0001;
    ok = S.advance(120, function () { return up ? st.y <= p.s : st.y >= 0; });
    if (!ok) { S.say('The drop does not move that way at this setting.'); return null; }
    w.t = 0; w.on = true;
    ok = S.advance(120, function () { return up ? st.y <= 0 : st.y >= p.s; });
    w.on = false;
    if (!ok) { S.say('The drop took longer than two minutes; pick another drop.'); return null; }
    return rnd(w.t, 2);
  }
  function timeFall() {
    if (busy()) return Promise.resolve(null);
    if (!st.sprayed) { S.say('Spray some oil first.'); return Promise.resolve(null); }
    return setField(false).then(function () { return S.hand.tap(oil.watch.start, 'front'); }).then(function () {
      var t = timeOver(false); if (t) { st.tf = t; S.say('Fall time over 1.0 mm: ' + t.toFixed(2) + ' s.'); } S.render(); return t; });
  }
  function timeRise() {
    if (busy()) return Promise.resolve(null);
    if (!st.sprayed) { S.say('Spray some oil first.'); return Promise.resolve(null); }
    return setField(true).then(function () { return S.hand.tap(oil.watch.start, 'front'); }).then(function () {
      var t = timeOver(true); if (t) { st.tr = t; S.say('Rise time over 1.0 mm at ' + st.V.toFixed(1) + ' V: ' + t.toFixed(2) + ' s.'); } S.render(); return t; });
  }
  function qFrom(tf, V, tr) {
    var vg = p.s / tf, a = Math.sqrt(9 * p.eta * vg / (2 * p.rho * p.g));
    if (RISE) return 6 * PI * p.eta * a * (vg + p.s / tr) * p.d / V;
    return 4 / 3 * PI * a * a * a * p.rho * p.g * p.d / V;
  }
  function recordDrop() {
    if (!st.tf) { S.say('Time the fall of this drop first.'); return false; }
    if (S.rows.some(function (r) { return r.drop === st.drop + 1; })) { S.say('Drop ' + (st.drop + 1) + ' is already recorded.'); return false; }
    if (RISE) { if (!st.tr) { S.say('Time the rise of this drop too.'); return false; } }
    else if (!st.field || Math.abs(oilVel()) > 2e-7) { S.say('The drop is not standing still yet: adjust the voltage with the field on.'); return false; }
    var q = qFrom(st.tf, st.V, st.tr);
    S.addRow({ drop: st.drop + 1, tf: st.tf, V: st.V, tr: RISE ? st.tr : null, q: q });
    st.tf = null; st.tr = null; return true;
  }
  function balanceV() {                 // the voltage on the 0.5 V knob at which the drop drifts least
    var best = 0, bv = 1e9, v, s0 = st.V, f0 = st.field; st.field = true;
    for (v = 0; v <= 600; v += 0.5) { st.V = v; var u = Math.abs(oilVel()); if (u < bv) { bv = u; best = v; } }
    st.V = s0; st.field = f0; return best;
  }

  // ================================================================ ZEEMAN
  var zee = {};
  function buildZee() {
    var g = new T.Group(); g.position.set(-0.4, 0, -0.14); S.scene.add(g); zee.g = g;
    var yoke = S.mesh(new T.BoxGeometry(0.26, 0.03, 0.08), M.iron); yoke.position.y = 0.015; g.add(yoke);
    [-1, 1].forEach(function (sg) {
      var core = S.mesh(new T.BoxGeometry(0.03, 0.12, 0.08), M.iron); core.position.set(sg * 0.115, 0.09, 0); g.add(core);
      var arm = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.07, 32), M.iron); arm.rotation.z = Math.PI / 2; arm.position.set(sg * 0.065, 0.13, 0); g.add(arm);
      var coil = S.mesh(new T.CylinderGeometry(0.045, 0.045, 0.05, 32), new T.MeshStandardMaterial({ color: 0xb8733a, metalness: 0.8, roughness: 0.35 })); coil.rotation.z = Math.PI / 2; coil.position.set(sg * 0.07, 0.13, 0); g.add(coil);
      var pole = S.mesh(new T.CylinderGeometry(0.018, 0.03, 0.025, 32), M.steel); pole.rotation.z = sg * Math.PI / 2; pole.position.set(sg * 0.022, 0.13, 0); g.add(pole);
    });
    zee.lampM = new T.MeshStandardMaterial({ color: 0x552222, emissive: 0x000000, roughness: 0.2 });
    var lamp = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.05, 12), zee.lampM); lamp.position.set(0, 0.13, 0); g.add(lamp);
    var holder = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.1, 12), M.bakelite); holder.position.set(0, 0.2, 0); g.add(holder);
    // optics along +z from the gap: lens, etalon, polaroid, telescope
    var rail = S.mesh(new T.BoxGeometry(0.03, 0.012, 0.36), M.alu); rail.position.set(0, 0.006, 0.2); g.add(rail);
    function onRail(z, obj, h) { var post = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.13 - (h || 0), 10), M.chrome); post.position.set(0, (0.13 - (h || 0)) / 2 + 0.012, z); g.add(post); obj.position.set(0, 0.13, z); g.add(obj); }
    var lens = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.006, 32), M.glass); lens.rotation.x = Math.PI / 2; onRail(0.08, lens);
    var et = S.mesh(new T.CylinderGeometry(0.024, 0.024, 0.03, 32), M.brass); et.rotation.x = Math.PI / 2; onRail(0.14, et);
    var el = S.label('ETALON t = ' + (p.t * 1000).toFixed(1) + ' mm', { w: 0.07, ratio: 0.16, color: '#222', bg: '#e9dcb8' }); el.position.set(0, 0.165, 0.14); el.rotation.x = -0.6; g.add(el);
    var pol = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.004, 32), new T.MeshStandardMaterial({ color: 0x404850, transparent: true, opacity: 0.6 })); pol.rotation.x = Math.PI / 2; onRail(0.19, pol);
    var tel = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.13, 24), new T.MeshStandardMaterial({ color: 0x2b3440, metalness: 0.5, roughness: 0.4 })); tel.rotation.x = Math.PI / 2; onRail(0.3, tel);
    zee.drum = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.02, 24), M.chrome); zee.drum.rotation.z = Math.PI / 2; zee.drum.position.set(0.03, 0.13, 0.36); g.add(zee.drum);
    S.contact(0.32, 0.5, -0.4, 0.02, 0.5);
    var vw = new T.Group(); vw.position.set(-0.08, 0, -0.24); S.scene.add(vw);
    var vb = S.rounded(0.17, 0.17, 0.016, 0.008, M.black); vb.position.set(0, 0.16, 0); vw.add(vb);
    var vs = S.mesh(new T.BoxGeometry(0.03, 0.08, 0.02), M.black); vs.position.set(0, 0.045, -0.005); vw.add(vs);
    zee.tex = S.liveTex(512, 512);
    var sc = new T.Mesh(new T.PlaneGeometry(0.15, 0.15), new T.MeshBasicMaterial({ map: zee.tex, toneMapped: false })); sc.position.set(0, 0.16, 0.009); vw.add(sc);
    var vl = S.label('VIEW IN THE EYEPIECE (enlarged)', { w: 0.15, ratio: 0.08, color: '#ddd' }); vl.position.set(0, 0.068, 0.009); vw.add(vl);
    zee.sup = supply(0.32, -0.04, 'ELECTROMAGNET SUPPLY + GAUSSMETER', -0.3);
    zee.knob = zee.sup.knob(-0.07, -0.02, 'MAGNET A');
    zee.showI = zee.sup.lcd(-0.07, 0.025, 0.1, 0.034);
    zee.showB = zee.sup.lcd(0.07, 0.025, 0.1, 0.034);
    zee.sw = zee.sup.sw(0.07, -0.02, 'LAMP');
    S.addApparatus('rig', g, 'Electromagnet, cadmium lamp and etalon', 'A cadmium lamp between the pole pieces; the lens, the Fabry-Perot etalon, the polaroid and the telescope with a micrometer eyepiece stand on the rail.');
    S.addApparatus('mon', vw, 'Eyepiece view', 'What the telescope shows, enlarged: the etalon rings, and the cross-wire of the micrometer eyepiece.');
    S.addApparatus('unit', zee.sup.g, 'Magnet supply and gaussmeter', 'The knob sets the magnet current; the right display is the gaussmeter in the gap.');
  }
  function zeeB() { return rnd(KM * st.Im * 1000, 0) / 1000; }          // gaussmeter, 1 mT
  function zeeRings() { return KN.view(KN.init(assign(p, { B: KM * st.Im }), {}), assign(p, { B: KM * st.Im }), {}); }
  function drawZee() {
    var r = zeeRings(), sc = 512 / 0.018;                  // 18 mm across the field of view
    zee.tex.draw(function (x) { x.fillStyle = '#060304'; x.fillRect(0, 0, 512, 512);
      if (st.on) { var list = [r.D2p, r.D2m, r.D3p, r.D3m]; if (KM * st.Im < 1e-4) list = [r.D2p, r.D3p];
        list.forEach(function (d) { x.strokeStyle = 'rgba(255,60,40,.9)'; x.lineWidth = 3; x.beginPath(); x.arc(256, 256, d / 2 * sc, 0, PI * 2); x.stroke(); }); }
      x.strokeStyle = 'rgba(230,230,230,.8)'; x.lineWidth = 1.5; var cx = 256 + st.cross * sc; x.beginPath(); x.moveTo(cx, 0); x.lineTo(cx, 512); x.stroke(); x.beginPath(); x.moveTo(0, 256); x.lineTo(512, 256); x.stroke(); });
  }
  function zeeLamp() {
    if (busy()) return Promise.resolve();
    return S.hand.tap(zee.sw, 'front').then(function () { st.on = true; zee.lampM.emissive.setHex(0xff3020); zee.lampM.emissiveIntensity = 2.5;
      S.say('The cadmium lamp glows red; the etalon rings appear in the telescope. With the polaroid in, only the two shifted components will show once the field is on.'); S.render(); });
  }
  function setIm(v) {
    if (!isFinite(v) || v < 0 || v > 4.5) { S.say('The magnet supply gives 0 to 4.5 A.'); return Promise.resolve(); }
    v = rnd(v, 2);
    return turnKnob(zee.knob, function () { return st.Im; }, function (x) { st.Im = x; }, v, 0, 4.5);
  }
  function measureRings() {
    if (busy()) return Promise.resolve(false);
    if (!st.on) { S.say('Switch the lamp on first.'); return Promise.resolve(false); }
    if (KM * st.Im < 0.2) { S.say('Raise the field to at least 0.2 T: below that the two components of a ring cannot be told apart.'); return Promise.resolve(false); }
    var r = zeeRings(), d = function (x) { return rnd(x * 1000, 2); };
    return S.hand.pinchMove(wp(zee.drum), function () { return wp(zee.drum); }, function (t) { st.cross = -r.D3p / 2 + r.D3p * t; zee.drum.rotation.x = t * 12; }, { mode: 'side', ms: 1200 })
      .then(function () { st.cross = 0;
        S.addRow({ B: zeeB(), D2p: d(r.D2p), D2m: d(r.D2m), D3p: d(r.D3p), D3m: d(r.D3m) });
        S.say('Cross-wire set on each side of every ring; diameters read on the micrometer to 0.01 mm.'); S.render(); return true; });
  }

  // ================================================================ BLACK BODY
  var bb = {};
  function buildBB() {
    var g = new T.Group(); g.position.set(-0.4, 0, -0.12); S.scene.add(g); bb.g = g;
    var base = S.rounded(0.12, 0.12, 0.02, 0.008, M.iron); base.rotation.x = -Math.PI / 2; base.position.y = 0.01; g.add(base);
    var hs = S.mesh(new T.CylinderGeometry(0.045, 0.045, 0.14, 32), new T.MeshStandardMaterial({ color: 0x3a3f47, metalness: 0.6, roughness: 0.4 })); hs.position.y = 0.09; g.add(hs);
    for (var i = 0; i < 5; i++) { var vent = S.mesh(new T.BoxGeometry(0.03, 0.004, 0.002), M.black); vent.position.set(0, 0.13 + i * 0.006, -0.045); g.add(vent); }
    var win = S.mesh(new T.CircleGeometry(0.015, 24), M.glass); win.position.set(0.0451, 0.09, 0); win.rotation.y = Math.PI / 2; g.add(win);
    bb.filM = new T.MeshStandardMaterial({ color: 0x6b5a2a, emissive: 0x000000 });
    var fil = S.mesh(new T.CylinderGeometry(0.0015, 0.0015, 0.03, 8), bb.filM); fil.position.set(0.03, 0.09, 0); g.add(fil);
    var tube = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.2, 28), new T.MeshStandardMaterial({ color: 0x1d2228, roughness: 0.6 })); tube.rotation.z = Math.PI / 2; tube.position.set(0.17, 0.09, 0); g.add(tube);
    var filt = S.mesh(new T.CylinderGeometry(0.022, 0.022, 0.008, 28), new T.MeshStandardMaterial({ color: 0xc0201a, transparent: true, opacity: 0.8 })); filt.rotation.z = Math.PI / 2; filt.position.set(0.075, 0.09, 0); g.add(filt);
    var fl = S.label('650 nm FILTER + PHOTODETECTOR', { w: 0.15, ratio: 0.1, color: '#ddd' }); fl.position.set(0.17, 0.112, 0); fl.rotation.x = -Math.PI / 2; g.add(fl);
    [0.1, 0.24].forEach(function (cx) { var pst = S.mesh(new T.BoxGeometry(0.012, 0.07, 0.03), M.darkWood); pst.position.set(cx, 0.045, 0); g.add(pst); });
    var py = new T.Group(); py.position.set(-0.05, 0, 0.18); g.add(py);
    var pr = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.08, 12), M.chrome); pr.position.y = 0.05; py.add(pr);
    var sc = S.mesh(new T.CylinderGeometry(0.015, 0.017, 0.12, 24), new T.MeshStandardMaterial({ color: 0x2f3a46, metalness: 0.5, roughness: 0.4 })); sc.rotation.x = Math.PI / 2; sc.position.set(0, 0.09, 0); py.add(sc);
    py.rotation.y = -0.35;
    var pb = S.rounded(0.07, 0.07, 0.01, 0.005, M.iron); pb.rotation.x = -Math.PI / 2; pb.position.y = 0.005; py.add(pb);
    S.contact(0.4, 0.4, -0.25, -0.05, 0.5);
    bb.sup = supply(0.33, -0.04, 'LAMP SUPPLY, PYROMETER, NANOAMMETER', -0.3);
    bb.knob = bb.sup.knob(-0.09, -0.02, 'LAMP A');
    bb.showA = bb.sup.lcd(-0.09, 0.025, 0.075, 0.03);
    bb.showT = bb.sup.lcd(0.0, 0.025, 0.075, 0.03);
    bb.showI = bb.sup.lcd(0.09, 0.025, 0.075, 0.03);
    bb.sw = bb.sup.sw(0.08, -0.02, 'POWER');
    S.addApparatus('rig', g, 'Tungsten lamp, filter and photodetector', 'The lamp in its vented housing, a 650 nm interference filter, a photodetector in a blackened tube, and the optical pyrometer aimed at the filament.');
    S.addApparatus('unit', bb.sup.g, 'Lamp supply and meters', 'Left: lamp current. Middle: pyrometer temperature. Right: photodetector current in nanoamperes.');
  }
  function bbT() { return LAMP0 + LAMPK * st.Il; }
  function bbRead() { var q = assign(p, { T: bbT() }); return { T: Math.round(bbT()), I: st.on ? rnd(KN.view(KN.init(q, {}), q, {}).I_nA, 2) : 0 }; }
  function bbOn() {
    if (busy()) return Promise.resolve();
    return S.hand.tap(bb.sw, 'front').then(function () { st.on = true; S.say('The lamp lights; let it settle for a minute at each setting before reading.'); S.render(); });
  }
  function setIl(v) {
    if (!isFinite(v) || v < 1.75 || v > 4.25) { S.say('Keep the lamp current between 1.75 and 4.25 A.'); return Promise.resolve(); }
    v = rnd(v, 3);
    return turnKnob(bb.knob, function () { return st.Il; }, function (x) { st.Il = x; }, v, 1.75, 4.25);
  }
  function bbRecord() {
    if (!st.on) { S.say('Switch the lamp on first.'); return false; }
    var r = bbRead();
    if (S.rows.some(function (x) { return x.T === r.T; })) { S.say('You already have a reading at ' + r.T + ' K.'); return false; }
    S.addRow({ Il: st.Il, T: r.T, I: r.I }); return true;
  }

  // ================================================================ build the bench for this lab
  if (MODE === 'oil') buildOil(); else if (MODE === 'zee') buildZee(); else buildBB();
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var hud1 = S.hudCard(MODE === 'oil' ? 'Plate voltage' : MODE === 'zee' ? 'Field' : 'Temperature'), hud2 = S.hudCard(MODE === 'oil' ? 'Drop velocity' : MODE === 'zee' ? 'Rows' : 'Detector');
  function trace() { st.traced = true; S.focus('rig'); S.say({ oil: 'The drops fall between the two brass plates. The camera looks across the gap; the monitor shows a drop as a bright point against the graticule.',
    zee: 'The light of the cadmium lamp crosses the field, goes through the etalon and the polaroid, and the telescope shows the rings.',
    bb: 'The filament light passes the 650 nm filter into the photodetector; the pyrometer reads the filament temperature.' }[MODE]); S.render(); }

  // ================================================================ steps
  var steps = [];
  if (MODE === 'oil') {
    steps.push({ id: 'prep', title: 'Spray the oil', view: 'rig', render: function (u) {
        u.h2('Look at the chamber, then spray some oil');
        u.task('1. Trace the apparatus', st.traced, st.traced ? 'Seen' : '').add(u.button('Look at the chamber', trace, !st.traced, st.traced));
        u.task('2. Spray', st.sprayed, st.sprayed ? 'Drops in view' : 'Squeeze the atomiser bulb').add(u.button('Squeeze the bulb', spray, !st.sprayed, st.sprayed || S.hand.busy));
        u.next('Next', st.traced && st.sprayed);
      }, ok: function () { return st.traced && st.sprayed; }, auto: function () { trace(); return spray(); } });
    steps.push({ id: 'drops', title: RISE ? 'Fall and rise of five drops' : 'Fall and balance of five drops', view: 'mon', render: function (u) {
        u.h2(RISE ? 'Time the fall, then the rise, of each drop' : 'Time the fall, then hold each drop still');
        u.p(RISE ? 'With the plates shorted time the fall over 1.0 mm. Then switch the field on at a fixed voltage (500 V) and time the rise over the same 1.0 mm.'
          : 'With the plates shorted time the fall over 1.0 mm. Then switch the field on and turn the voltage until the drop stands still; record it.');
        u.row(u.button('Previous drop', function () { pickDrop((st.drop + 4) % 5); }, false, S.hand.busy), u.button('Next drop', function () { pickDrop((st.drop + 1) % 5); }, false, S.hand.busy));
        var tg = { v: st.V || (RISE ? 500 : 200) };
        u.slider('Set the plate voltage to', 0, 600, 0.5, function () { return tg.v; }, function (v) { tg.v = v; }, 'V', 1);
        u.row(u.button('Turn the knob', function () { setV(tg.v); }, false, S.hand.busy), u.button(st.field ? 'Short the plates' : 'Field on', function () { setField(!st.field); }, false, S.hand.busy));
        u.row(u.button('Bring the drop to the top', bringTop, false, S.hand.busy), u.button('Time the fall', timeFall, true, S.hand.busy),
          RISE ? u.button('Time the rise', timeRise, true, S.hand.busy) : u.button('Record this drop', recordDrop, true, S.hand.busy));
        if (RISE) u.row(u.button('Record this drop', recordDrop, true, S.hand.busy));
        u.live(function () { return 'Drop ' + (st.drop + 1) + '  ·  ' + (st.field ? st.V.toFixed(1) + ' V' : 'plates shorted') + '  ·  moving ' + (oilVel() * 1e6).toFixed(1) + ' µm/s up'; });
        u.table(); u.next('Next: result', S.rows.length >= 5);
      }, ok: function () { return S.rows.length >= 5; },
      auto: function () {
        var chain = Promise.resolve();
        [0, 1, 2, 3, 4].forEach(function (k) {
          chain = chain.then(function () { pickDrop(k); return timeFall(); })
            .then(function () { if (RISE) return setV(500).then(timeRise); return setV(balanceV()).then(function () { return setField(true); }); })
            .then(function () { recordDrop(); });
        });
        return chain;
      } });
  } else if (MODE === 'zee') {
    steps.push({ id: 'lamp', title: 'Lamp and rings', view: 'rig', render: function (u) {
        u.h2('Look along the optics, then switch the lamp on');
        u.task('1. Trace the light path', st.traced, '').add(u.button('Trace the light path', trace, !st.traced, st.traced));
        u.task('2. Lamp on', st.on, '').add(u.button('Switch the lamp on', zeeLamp, !st.on, st.on || S.hand.busy));
        u.next('Next', st.traced && st.on);
      }, ok: function () { return st.traced && st.on; }, auto: function () { trace(); return zeeLamp(); } });
    steps.push({ id: 'split', title: 'Measure the splitting', view: 'mon', render: function (u) {
        u.h2('Split the rings and measure them');
        u.p('Set the magnet current, read the field on the gaussmeter, then measure both components of the second and third rings with the micrometer. Do this at three fields between 0.5 and 0.8 T.');
        var tg = { v: st.Im || 2.5 };
        u.slider('Set the magnet current to', 0, 4.5, 0.05, function () { return tg.v; }, function (v) { tg.v = v; }, 'A', 2);
        u.row(u.button('Turn the knob', function () { setIm(tg.v); }, false, S.hand.busy), u.button('Measure the ring diameters', measureRings, true, S.hand.busy));
        u.live(function () { return st.Im.toFixed(2) + ' A  ·  B = ' + (zeeB() * 1000).toFixed(0) + ' mT'; });
        u.table(); u.next('Next: result', S.rows.length >= 3);
      }, ok: function () { return S.rows.length >= 3; },
      auto: function () { var c = Promise.resolve(); [2.5, 3.25, 4.0].forEach(function (i) { c = c.then(function () { return setIm(i); }).then(measureRings); }); return c; } });
  } else {
    steps.push({ id: 'lamp', title: 'Line up and switch on', view: 'rig', render: function (u) {
        u.h2('Line up the filter and detector, then switch the lamp on');
        u.task('1. Trace the light path', st.traced, '').add(u.button('Trace the light path', trace, !st.traced, st.traced));
        u.task('2. Lamp on', st.on, '').add(u.button('Switch on', bbOn, !st.on, st.on || S.hand.busy));
        u.next('Next', st.traced && st.on);
      }, ok: function () { return st.traced && st.on; }, auto: function () { trace(); return bbOn(); } });
    steps.push({ id: 'temps', title: 'Signal at each temperature', view: 'unit', render: function (u) {
        u.h2('Read the detector at nine temperatures'); u.p('Set the lamp current so the pyrometer reads 1800, 1900 ... 2600 K and read the detector current each time.');
        var tg = { v: st.Il };
        u.slider('Set the lamp current to', 1.75, 4.25, 0.005, function () { return tg.v; }, function (v) { tg.v = v; }, 'A', 3);
        u.row(u.button('Turn the knob', function () { setIl(tg.v); }, false, S.hand.busy), u.button('Record', bbRecord, true, S.hand.busy));
        u.live(function () { var r = bbRead(); return st.Il.toFixed(3) + ' A  ·  ' + r.T + ' K  ·  ' + r.I.toFixed(2) + ' nA'; });
        u.table(); u.next('Next: result', S.rows.length >= 5);
      }, ok: function () { return S.rows.length >= 5; },
      auto: function () { var c = Promise.resolve(); [1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600].forEach(function (t) { c = c.then(function () { return setIl((t - LAMP0) / LAMPK); }).then(bbRecord); }); return c; } });
  }

  // ================================================================ results, book, graph
  function oilE(rows) {
    var qs = rows.map(function (r) { return r.q; }).filter(function (q) { return q > 0; }); if (qs.length < 3) return null;
    var q1 = Math.min.apply(null, qs), t = 0; qs.forEach(function (q) { var k = Math.floor(q / q1 + 0.5); t += q / (k > 0 ? k : 1); });
    return t / qs.length;
  }
  function zeeEm(r) {
    var d2 = ((r.D3p * r.D3p - r.D2p * r.D2p) + (r.D3m * r.D3m - r.D2m * r.D2m)) / 2,
      ds = ((r.D2p * r.D2p - r.D2m * r.D2m) + (r.D3p * r.D3p - r.D3m * r.D3m)) / 2 / (4 * p.t * d2 * 1e-6) * 1e-6;
    return 4 * PI * C * ds / r.B;
  }
  function result(rows) {
    if (MODE === 'oil') { var e = oilE(rows); if (!e) return null;
      return { label: 'Elementary charge e', value: e * 1e19, unit: 'x 1e-19 C', digits: 3, truth: p.e * 1e19,
        note: 'Each charge divided by the smallest, rounded to a whole number n; e = mean of q/n over ' + rows.length + ' drops.' }; }
    if (MODE === 'zee') { if (rows.length < 3) return null;
      return { label: 'e/m of the electron', value: S.fit.mean(rows.map(zeeEm)) / 1e11, unit: 'x 1e11 C/kg', digits: 3, truth: p.em / 1e11,
        note: 'd_sigma = (Da^2 - Db^2)/(4 t (D3^2 - D2^2)) for each order, averaged; e/m = 4 pi c d_sigma / B, mean of ' + rows.length + ' fields.' }; }
    if (rows.length < 5) return null;
    var f = S.fit.linear(rows.map(function (r) { return [1 / r.T, Math.log(r.I)]; })); if (!f) return null;
    return { label: "Planck's constant h", value: -f.m * p.lam * KB / C * 1e34, unit: 'x 1e-34 J s', digits: 3, truth: p.h * 1e34,
      note: 'Slope of ln I against 1/T = ' + f.m.toFixed(0) + ' K; h = -slope x lam k / c with lam = ' + (p.lam * 1e9).toFixed(0) + ' nm.' };
  }
  var COLS = { oil: RISE ? [['Drop', 'drop', 0], ['t fall (s)', 'tf', 2], ['V (V)', 'V', 1], ['t rise (s)', 'tr', 2]] : [['Drop', 'drop', 0], ['t fall (s)', 'tf', 2], ['V bal (V)', 'V', 1]],
    zee: [['B (T)', 'B', 3], ['D2 out (mm)', 'D2p', 2], ['D2 in (mm)', 'D2m', 2], ['D3 out (mm)', 'D3p', 2], ['D3 in (mm)', 'D3m', 2]],
    bb: [['I lamp (A)', 'Il', 3], ['T (K)', 'T', 0], ['I det (nA)', 'I', 2]] }[MODE];
  var columns = [{ label: 'S.No', get: function (r, i) { return i + 1; } }].concat(COLS.map(function (c) { return { label: c[0], get: function (r) { return typeof r[c[1]] === 'number' ? r[c[1]].toFixed(c[2]) : '-'; } }; }));
  if (MODE === 'oil') columns.push({ label: 'q (1e-19 C)', get: function (r) { return (r.q * 1e19).toFixed(3); } });
  var GRAPH = { oil: { x: function (r) { return r.drop; }, y: function (r) { return r.q * 1e19; }, xlabel: 'drop', ylabel: 'q (1e-19 C)', x0: 0, y0: 0 },
    zee: { x: function (r) { return r.B; }, y: function (r) { return (r.D2p * r.D2p - r.D2m * r.D2m); }, xlabel: 'B (T)', ylabel: 'D2out^2 - D2in^2 (mm^2)', x0: 0, y0: 0 },
    bb: { x: function (r) { return 1e4 / r.T; }, y: function (r) { return Math.log(r.I); }, xlabel: '10^4 / T (1/K)', ylabel: 'ln I' } }[MODE];
  var TH = { oil: ['Stokes fall gives the radius; the balancing (or rise) voltage gives the charge.', RISE ? 'q = 6 pi eta a (vg + vr) d / V' : 'q = (4/3) pi a^3 rho g d / V'],
    zee: ['Each sigma component shifts by e B / (4 pi m c); the etalon converts the shift into a change of ring diameter.', 'e/m = 4 pi c d_sigma / B'],
    bb: ['Through a narrow filter the signal is K / (exp(h c / lam k T) - 1); in the Wien limit ln I falls linearly with 1/T.', 'h = - slope x lam k / c'] }[MODE];

  return {
    camera: { pos: [0.0, 1.0, 1.4], look: [-0.06, 0.08, -0.1] },
    views: { rig: [[-0.32, 0.45, 0.45], [-0.32, 0.12, -0.08]], mon: [[-0.05, 0.3, 0.2], [-0.07, 0.15, -0.22]], unit: [[0.36, 0.34, 0.34], [0.32, 0.08, -0.04]],
      bench: [[-0.02, 0.85, 1.15], [-0.06, 0.1, -0.08]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: TH[0], formula: TH[1], formulaNote: 'Constants: CODATA 2018; the lab\'s own values are printed on the apparatus.',
      more: MODE === 'oil' ? ['Air viscosity eta = ' + p.eta + ' Pa s, oil density ' + p.rho + ' kg/m3, plate gap ' + (p.d * 1000).toFixed(1) + ' mm, timing distance ' + (p.s * 1000).toFixed(1) + ' mm.', 'The Cunningham slip correction is not applied in this lab.']
        : MODE === 'zee' ? ['Etalon spacing t = ' + (p.t * 1000).toFixed(1) + ' mm; air in the etalon taken as n = 1.', 'Magnet calibration ' + KM + ' T/A (illustrative); the field is read on the gaussmeter.']
          : ['Filter at ' + (p.lam * 1e9).toFixed(0) + ' nm. Lamp calibration T = ' + LAMP0 + ' K + ' + LAMPK + ' K/A x current (illustrative).', 'Tungsten is not a perfect black body; its slow change of emissivity is not modelled.'],
      precautions: MODE === 'oil' ? 'Follow one drop at a time and reject a drop that changes its speed (it picked up a charge).' : MODE === 'zee' ? 'Set the cross-wire on the brightest part of each ring and always turn the micrometer in one direction.' : 'Let the lamp settle at each setting; shield the detector from room light.' },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 120)], columns: columns },
    graph: GRAPH,
    result: result,
    tol: 0.02,
    chips: ['What am I measuring?', 'Check my readings', 'Why is this the right formula?'],
    viva: [MODE === 'oil' ? ['The charge of every drop is', ['A whole multiple of e', 'Exactly e', 'Any value'], 0, 'Charge comes in units of e.']
      : MODE === 'zee' ? ['A Fabry-Perot etalon is used because', ['The splitting is far too small for a prism', 'It filters the light', 'It is cheap'], 0, 'Its resolving power is very high.']
        : ['At 650 nm and 2000 K Planck\'s law can be replaced by', ['Wien\'s approximation', 'The Rayleigh-Jeans law', 'Stefan\'s law'], 0, 'h c / lam k T is about 11, so the 1 is negligible.']],
    askState: function () { return { experiment: S.lab.title, readings_taken: S.rows.length, plate_voltage_V: st.V, field_on: st.field, drop: st.drop + 1,
      magnet_current_A: st.Im, field_T: MODE === 'zee' ? zeeB() : null, lamp_current_A: st.Il, pyrometer_K: MODE === 'bb' ? bbRead().T : null }; },
    steps: steps,
    tick: function (dt) {
      var now = (window.performance && performance.now()) || 0, draw = now - (st.lastDraw || -1e9) > 40; if (draw) st.lastDraw = now;
      if (MODE === 'oil') {
        if (st.sprayed) { st.y -= oilVel() * (dt || 0); if (st.y > 0.0016) st.y = 0.0016; if (st.y < -0.0003) st.y = -0.0003; }
        oil.showV(st.V.toFixed(1), 'V'); if (draw) drawOil(); hud1.set(st.V.toFixed(1) + ' V'); hud2.set((oilVel() * 1e6).toFixed(1) + ' µm/s');
      } else if (MODE === 'zee') {
        zee.showI(st.Im.toFixed(2), 'A'); zee.showB((zeeB() * 1000).toFixed(0), 'mT'); if (draw) drawZee(); hud1.set((zeeB() * 1000).toFixed(0) + ' mT'); hud2.set(String(S.rows.length));
      } else {
        var r = bbRead(); bb.showA(st.Il.toFixed(3), 'A'); bb.showT(st.on ? String(r.T) : '----', 'K'); bb.showI(r.I.toFixed(2), 'nA');
        bb.filM.emissive = new T.Color(st.on ? 0xffb050 : 0); bb.filM.emissiveIntensity = st.on ? 1 + (bbT() - 1800) / 400 : 0;
        hud1.set(st.on ? r.T + ' K' : '-'); hud2.set(r.I.toFixed(2) + ' nA');
      }
    }
  };
});
