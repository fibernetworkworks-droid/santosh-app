/* Prayogshala studio module: THIN-FILM / HIGH-VACUUM CHAMBER for two labs.
   ph2-qcm-evap (+ variants): a bell-jar evaporator with a quartz crystal monitor. The crystal frequency falls as the film
   grows (Sauerbrey); the student reads f against t, finds the deposition rate from the slope, then compares the monitor's
   thickness with a stylus step on the substrate to get the tooling factor. Kernel ph2_qcm (packs/ph2_films.js).
   ph2-vac-research (+ variants): a stainless chamber, a gate valve, a pipe to a high-vacuum pump (turbomolecular or
   diffusion) with a rotary backing pump. The student roughs the chamber, opens the gate valve, reads the gauge while the
   pressure falls (effective speed, then the pipe's conductance), and does a rate-of-rise test (leak). Kernel ph2_vac. */
HoolaStudio.define('ph2-film-chamber', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels;
  var QCM = String(S.lab.id).indexOf('ph2-qcm') === 0;
  var KN = QCM ? HK.K.ph2_qcm : HK.K.ph2_vac, assign = HK.assign;
  var p = HK.paramsFor(QCM ? 'ph2_qcm' : 'ph2_vac', S.lab.params);
  var V_ = S.lab.variant || {};
  var SAMPLE = V_.sample || (QCM ? 'Gold wire in a tungsten boat' : 'Stainless-steel chamber, 50 litres');
  var TURBO = !(V_.method || '').match(/diffusion/);
  var st = { vent: false, rough: false, rotary: false, gate: false, iso: false, t: 0, running: false, pumped: false, zeroed: false, hot: false, shutter: false, closed: false, stylus: 0, tc: 0, fp: 0 };
  function sig(v, n) { return v === 0 ? 0 : +v.toPrecision(n); }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 24); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }
  function fmtP(v) { if (!(v > 0)) return '—'; var e = Math.floor(Math.log10(v)), m = v / Math.pow(10, e); return m.toFixed(2) + 'E' + e; }
  function fmtF(f) { return Math.round(f) + ''; }

  // ---------------------------------------------------------------- pressure model for the VAC mode
  function pnow() {
    if (!st.rough) return p.Pat;                       // before roughing
    if (!st.gate && !st.iso) return QCM ? p.Pat : KN.pressure(assign(p, { stage: 0, t: st.t }));
    return KN.pressure(assign(p, { stage: st.iso ? 2 : 1, t: st.t, tc: st.tc }));
  }
  var steelM = new T.MeshStandardMaterial({ color: 0xb8bcc0, roughness: 0.28, metalness: 0.92 });

  // ================================================================ chamber
  var CX = -0.38, CZ = -0.2;
  var ch = new T.Group(); S.scene.add(ch); ch.position.set(CX, 0, CZ);
  mk(ch, cyl(0.1, 0.105, 0.025, 48), new T.MeshStandardMaterial({ color: 0xaeb4ba, roughness: 0.3, metalness: 0.9 }), 0, 0.0125, 0);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.04, transmission: 0.92, thickness: 0.004, transparent: true, opacity: 0.3 });
  if (QCM) {
    mk(ch, cyl(0.075, 0.075, 0.17, 48), glassM, 0, 0.11, 0);
    mk(ch, new T.SphereGeometry(0.075, 36, 18, 0, Math.PI * 2, 0, Math.PI / 2), glassM, 0, 0.195, 0);
    mk(ch, cyl(0.075, 0.075, 0.006, 48), M.rubber, 0, 0.03, 0);
  } else {
    mk(ch, cyl(0.07, 0.07, 0.16, 48), steelM, 0, 0.105, 0);
    mk(ch, cyl(0.075, 0.075, 0.012, 48), steelM, 0, 0.19, 0);
    var vp = mk(ch, cyl(0.022, 0.022, 0.012, 24), new T.MeshPhysicalMaterial({ color: 0xbfd8e8, roughness: 0.05, transmission: 0.8, transparent: true, opacity: 0.55 }), 0, 0.115, 0.07); vp.rotation.x = Math.PI / 2;
    var vl = S.label('50 litre chamber', { w: 0.08, ratio: 0.14, color: '#e8eaec', bg: '#2b323d' }); vl.position.set(0, 0.06, 0.0705); ch.add(vl);
  }
  var boatG = new T.Group(); ch.add(boatG);
  var glowM = new T.MeshBasicMaterial({ color: 0xff7a1a, transparent: true, opacity: 0 });
  var shutter = null, subs = null, head = null, jet = null;
  if (QCM) {
    mk(boatG, box(0.03, 0.006, 0.014), M.iron, 0, 0.034, 0); mk(boatG, box(0.012, 0.012, 0.024), M.copper, -0.026, 0.03, 0); mk(boatG, box(0.012, 0.012, 0.024), M.copper, 0.026, 0.03, 0);
    mk(boatG, new T.SphereGeometry(0.006, 14, 10), new T.MeshStandardMaterial({ color: 0xd9b84a, roughness: 0.25, metalness: 0.95 }), 0, 0.043, 0);
    mk(boatG, new T.SphereGeometry(0.009, 14, 10), glowM, 0, 0.043, 0);
    shutter = new T.Group(); shutter.position.set(0.0, 0.07, 0); boatG.add(shutter);
    mk(shutter, box(0.05, 0.002, 0.03), M.iron, 0, 0, 0);
    mk(boatG, cyl(0.045, 0.045, 0.004, 28), M.alu, 0, 0.17, 0);
    subs = mk(boatG, cyl(0.03, 0.03, 0.0015, 28), new T.MeshStandardMaterial({ color: 0xcfd6dc, roughness: 0.1, metalness: 0.4 }), 0, 0.1675, 0);
    head = mk(boatG, cyl(0.011, 0.011, 0.012, 20), M.chrome, 0.05, 0.15, 0.0);
    mk(boatG, cyl(0.002, 0.002, 0.07, 8), M.copper, 0.05, 0.11, 0);
  } else {
    mk(ch, cyl(0.012, 0.012, 0.18, 12), M.copper, 0, 0.1, 0).visible = false;
  }
  S.contact(0.28, 0.28, CX, CZ, 0.55);
  // pipe, gate valve, pumps
  var pipeLen = QCM ? 0.2 : 0.3;
  var pipe = mk(S.scene, cyl(0.011, 0.011, 0.14, 16), M.steel, CX + 0.15, 0.038, CZ); pipe.rotation.z = Math.PI / 2;
  var gv = new T.Group(); gv.position.set(CX + 0.24, 0.038, CZ); S.scene.add(gv);
  mk(gv, box(0.03, 0.036, 0.03), steelM, 0, 0, 0);
  var gvWheel = new T.Group(); gvWheel.position.set(0, 0.03, 0); gv.add(gvWheel);
  mk(gvWheel, cyl(0.003, 0.003, 0.03, 8), M.steel, 0, 0, 0); var wheel = mk(gvWheel, cyl(0.016, 0.016, 0.004, 24), M.red, 0, 0.018, 0);
  var gl = S.label('GATE', { w: 0.02, ratio: 0.3, color: '#e8eaec' }); gl.position.set(0, 0.0, 0.0155); gv.add(gl);
  var ventG = new T.Group(); ventG.position.set(CX + 0.1, 0.05, CZ + 0.09); S.scene.add(ventG);
  mk(ventG, cyl(0.006, 0.006, 0.03, 12), M.steel, 0, 0, 0); var vh = mk(ventG, box(0.03, 0.006, 0.008), M.red, 0, 0.02, 0);
  var vlb = S.label('VENT', { w: 0.02, ratio: 0.3, color: '#e8eaec' }); vlb.position.set(0, 0.032, 0.013); vlb.rotation.x = -0.3; ventG.add(vlb);
  var hp = new T.Group(); hp.position.set(CX + 0.34, 0, CZ); S.scene.add(hp);
  if (TURBO) {
    mk(hp, cyl(0.04, 0.04, 0.01, 28), M.alu, 0, 0.005, 0);
    mk(hp, cyl(0.03, 0.03, 0.09, 28), new T.MeshStandardMaterial({ color: 0x2e3d52, roughness: 0.4, metalness: 0.6 }), 0, 0.055, 0);
    mk(hp, cyl(0.034, 0.034, 0.012, 28), M.alu, 0, 0.106, 0);
    var tl = S.label('TURBO PUMP', { w: 0.05, ratio: 0.16, color: '#e8eaec', bg: '#2e3d52' }); tl.position.set(0, 0.055, 0.0305); hp.add(tl);
  } else {
    mk(hp, cyl(0.035, 0.035, 0.012, 28), M.alu, 0, 0.006, 0);
    mk(hp, cyl(0.026, 0.026, 0.16, 28), steelM, 0, 0.092, 0);
    for (var f = 0; f < 6; f++) mk(hp, new T.TorusGeometry(0.03, 0.0025, 6, 28), M.copper, 0, 0.035 + f * 0.025, 0).rotation.x = Math.PI / 2;
    mk(hp, cyl(0.032, 0.032, 0.01, 28), M.alu, 0, 0.18, 0);
    var dl = S.label('DIFFUSION PUMP', { w: 0.07, ratio: 0.14, color: '#20252b', bg: '#d8dde2' }); dl.position.set(0, 0.03, 0.0305); hp.add(dl);
  }
  var hv = mk(S.scene, cyl(0.011, 0.011, 0.1, 16), M.steel, CX + 0.29, 0.038, CZ); hv.rotation.z = Math.PI / 2; hv.visible = true;
  S.contact(0.12, 0.12, CX + 0.34, CZ, 0.5);
  var rot = new T.Group(); rot.position.set(CX + 0.34, 0, CZ + 0.14); S.scene.add(rot);
  mk(rot, box(0.14, 0.07, 0.07), new T.MeshStandardMaterial({ color: 0x2c63c4, roughness: 0.4, metalness: 0.4 }), 0, 0.045, 0);
  mk(rot, cyl(0.04, 0.04, 0.09, 28), new T.MeshStandardMaterial({ color: 0x2c63c4, roughness: 0.4, metalness: 0.4 }), 0.1, 0.05, 0).rotation.z = Math.PI / 2;
  var rl = S.label('ROTARY PUMP', { w: 0.08, ratio: 0.14, color: '#fff' }); rl.position.set(0, 0.025, 0.0355); rot.add(rl);
  S.contact(0.28, 0.14, CX + 0.34, CZ + 0.14, 0.55);
  mk(S.scene, cyl(0.006, 0.006, 0.14, 10), M.rubber, CX + 0.34, 0.04, CZ + 0.07).rotation.x = Math.PI / 2;

  function instBox(x, z, rotY, title, sub, wdt) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = rotY;
    var W = wdt || 0.2, Dd = 0.15, Hh = 0.08;
    var cse = S.rounded(W, Dd, Hh, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 })); cse.rotation.x = -Math.PI / 2; cse.position.y = Hh / 2 + 0.003; g.add(cse);
    var FZ = Dd / 2 + 0.005, PW = W - 0.012, PH = Hh - 0.012;
    var tex = S.canvasTex(900, Math.round(900 * PH / PW), function (xx, w, h) { xx.fillStyle = '#2b323d'; xx.fillRect(0, 0, w, h); xx.strokeStyle = 'rgba(255,255,255,.12)'; xx.lineWidth = 3; xx.strokeRect(8, 8, w - 16, h - 16);
      xx.fillStyle = '#f1efe8'; xx.font = '700 34px "Public Sans", sans-serif'; xx.fillText(title, 26, 52); xx.font = '500 22px "Public Sans", sans-serif'; xx.fillStyle = '#c7ccd6'; xx.fillText(sub, 26, 88); });
    var fac = S.mesh(box(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]); fac.position.set(0, 0.003 + Hh / 2, FZ - 0.002); g.add(fac);
    var lcdT = S.liveTex(512, 180), last = '';
    var bez = S.mesh(box(PW * 0.52, PH * 0.42, 0.003), M.grey); bez.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.001); g.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(PW * 0.48, PH * 0.38), new T.MeshBasicMaterial({ map: lcdT, toneMapped: false })); scr.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(scr);
    var knobG = new T.Group(); knobG.position.set(-PW * 0.28, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(knobG);
    var kk = S.mesh(cyl(0.012, 0.013, 0.012, 28), M.bakelite); kk.rotation.x = Math.PI / 2; knobG.add(kk);
    var kp = S.mesh(box(0.0018, 0.012, 0.001), M.white, false); kp.position.set(0, 0.007, 0.007); knobG.add(kp);
    S.contact(W + 0.06, Dd + 0.06, x, z, 0.5);
    return { group: g, knob: knobG, show: function (txt, u2) { if (txt + u2 === last) return; last = txt + u2;
      lcdT.draw(function (xx) { var gr = xx.createLinearGradient(0, 0, 0, 180); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); xx.fillStyle = gr; xx.fillRect(0, 0, 512, 180);
        xx.font = '700 ' + (txt.length > 7 ? 64 : 88) + 'px "JetBrains Mono", monospace'; xx.textAlign = 'right'; xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 118); xx.font = '600 32px "Public Sans", sans-serif'; xx.fillText(u2, 496, 150); }); } };
  }
  var gauge = instBox(0.3, -0.22, -0.2, 'GAUGE CONTROLLER', 'Pirani 0.1 Pa to 1 kPa · ion gauge below 0.1 Pa', 0.22);
  var ctrl = instBox(0.0, 0.1, -0.1, QCM ? 'SOURCE SUPPLY + TIMER' : 'PUMP SWITCH + TIMER', QCM ? 'source heater, shutter clock' : 'rotary pump and the clock', 0.22);
  var qcb = QCM ? instBox(0.3, -0.02, -0.15, 'QUARTZ MONITOR', '6 MHz crystal · frequency in Hz', 0.22) : null;
  gauge.show(fmtP(p.Pat), 'Pa'); ctrl.show('0', 's'); if (qcb) qcb.show(fmtF(p.f0), 'Hz');
  S.wire([[CX + 0.08, 0.11, CZ], [0.1, 0.03, -0.1], [0.24, 0.05, -0.22]], 'blue');
  S.addApparatus('jar', ch, QCM ? 'Bell-jar evaporator' : 'Stainless chamber', QCM ? 'A bell jar with a tungsten boat, a shutter, the substrate holder above and the quartz crystal head beside it.' : 'A 50 litre stainless-steel chamber. The pumps take gas out through the pipe; leaks and outgassing put it back.');
  S.addApparatus('hvpump', hp, TURBO ? 'Turbomolecular pump' : 'Diffusion pump', TURBO ? 'A fast-spinning bladed rotor knocks molecules toward the backing pump. It needs a rotary pump behind it.' : 'Hot oil vapour carries gas molecules downward to the rotary pump. It needs the rotary pump behind it.');
  S.addApparatus('gate', gv, 'Gate valve', 'Opens the chamber to the high-vacuum pump through the pipe.');
  S.addApparatus('gauge', gauge.group, 'Gauge controller', 'A Pirani gauge above 0.1 Pa and an ion gauge below it. Each reads only inside its own range.');
  S.addApparatus('ctrl', ctrl.group, QCM ? 'Source supply and timer' : 'Pump switch and timer', 'Runs the timer in seconds. You choose how long to wait before reading.');
  if (qcb) S.addApparatus('qcm', qcb.group, 'Quartz monitor', 'Reads the crystal frequency. Film on the crystal lowers it.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudT = S.hudCard('Time'), hudP = S.hudCard(QCM ? 'Crystal frequency' : 'Gauge reading');

  // ================================================================ human actions (shared)
  function ventClose() {
    if (busy() || st.vent) return Promise.resolve();
    return S.hand.tap(vh, 'top').then(function () { st.vent = true; vh.rotation.y = Math.PI / 2; S.say('Vent valve closed.'); S.click(660, 0.05); S.render(); });
  }
  function runTo(t1, lim) {
    if (busy()) return Promise.resolve();
    if (t1 < st.t) { S.say('The clock only runs forward: choose a time later than ' + Math.round(st.t) + ' s.'); return Promise.resolve(); }
    if (t1 > lim) { S.say('This run lasts ' + lim + ' s.'); return Promise.resolve(); }
    var t0 = st.t; st.running = true;
    return S.tween(300 + Math.min(1800, (t1 - t0) * 3), function (k) { st.t = t0 + (t1 - t0) * k; }).then(function () { st.t = t1; st.running = false; S.say('The clock reads ' + Math.round(t1) + ' s.'); S.render(); });
  }

  // ---------------------------------------------------------------- VAC mode actions
  function rotaryStart() {
    if (busy() || st.rotary) return Promise.resolve();
    if (!st.vent) { S.say('Close the vent valve first.'); return Promise.resolve(); }
    return S.hand.tap(ctrl.knob, 'front').then(function () { st.rotary = true; st.t = 0; S.say('The rotary pump is running and the timer has started at zero.'); S.click(880, 0.05); S.render(); });
  }
  function roughDown() {
    if (busy() || st.rough) return Promise.resolve();
    if (!st.rotary) { S.say('Start the rotary pump first.'); return Promise.resolve(); }
    var tx = p.V / p.Sr * Math.log((p.Pat - p.Pur) / (p.Px - p.Pur)); st.running = true; st.fp = 1;
    return S.tween(1600, function (k) { st.t = tx * k; st.rough = true; }).then(function () { st.rough = true; st.running = false; st.t = 0; st.fp = 2; S.say('Roughed to ' + p.Px + ' Pa in about ' + Math.round(tx) + ' s. The gate valve can open now.'); S.render(); });
  }
  function openGate() {
    if (busy() || st.gate) return Promise.resolve();
    if (!st.rough) { S.say('Rough the chamber to ' + p.Px + ' Pa before opening the gate valve.'); return Promise.resolve(); }
    return S.hand.tap(wheel, 'top').then(function () { st.gate = true; st.t = 0; S.say('Gate valve open: the chamber is now pumped by the ' + (TURBO ? 'turbomolecular' : 'diffusion') + ' pump through the pipe. The timer restarts at zero.'); S.click(880, 0.05); S.render(); });
  }
  function isolate() {
    if (busy() || st.iso) return Promise.resolve();
    if (!st.gate) { S.say('Open the gate valve first.'); return Promise.resolve(); }
    if (st.t < 1000) { S.say('Let the pump run longer first: the outgassing must have died away (about 1000 s) before a rate-of-rise test shows the leak.'); return Promise.resolve(); }
    return S.hand.tap(wheel, 'top').then(function () { st.tc = st.t; st.iso = true; st.gate = false; st.t = 0; S.say('Gate valve closed at ' + Math.round(st.tc) + ' s: the chamber is isolated and the pressure will rise.'); S.click(660, 0.05); S.render(); });
  }
  function gaugeP() {
    var v = pnow();
    if (v > 1e5 * 1.01) return null;
    return sig(v, 3);
  }
  function recordVac() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return null; }
    if (st.running) { S.say('Wait for the clock to stop.'); return null; }
    if (!st.gate && !st.iso) { S.say('Open the gate valve first (or close it for a rate-of-rise run).'); return null; }
    var kind = st.iso ? 'rise' : 'pump', tt = Math.round(st.t);
    for (var i = 0; i < S.rows.length; i++) if (S.rows[i].kind === kind && S.rows[i].t === tt) { S.say('You already have a reading at ' + tt + ' s. Let the clock run on.'); return null; }
    var v = gaugeP();
    var row = { kind: kind, t: tt, P: v, lnP: Math.log(v) };
    S.addRow(row);
    S.say('Written in your record book: ' + (kind === 'rise' ? 'rise test, ' : '') + 't = ' + tt + ' s, P = ' + fmtP(v) + ' Pa.');
    return row;
  }
  function vacFit() {
    var pts = S.rows.filter(function (r) { return r.kind === 'pump' && r.P >= 0.3 && r.P <= 10; }).map(function (r) { return [r.t, r.lnP]; });
    if (pts.length < 5) return null;
    var f = S.fit.linear(pts); if (!f || f.m >= 0) return null;
    var se = -p.V * f.m, inv = 1 / se - 1 / p.Sp;
    return { S: se, C: inv > 0 ? 1 / inv : 0, n: pts.length };
  }
  function riseFit() {
    var pts = S.rows.filter(function (r) { return r.kind === 'rise'; }).map(function (r) { return [r.t, r.P]; });
    if (pts.length < 4) return null;
    var f = S.fit.linear(pts); return f ? { QL: p.V * f.m } : null;
  }

  // ---------------------------------------------------------------- QCM mode actions
  function pumpDownQ() {
    if (busy() || st.pumped) return Promise.resolve();
    if (!st.vent) { S.say('Close the vent valve first.'); return Promise.resolve(); }
    return S.hand.tap(ctrl.knob, 'front').then(function () { st.fp = 1; return S.tween(1600, function (k) { st.pk = k; }); }).then(function () { st.pumped = true; st.fp = 2; S.say('The chamber is at about 5×10⁻⁴ Pa: good enough for a clean film.'); S.render(); });
  }
  function zeroQ() {
    if (busy() || st.zeroed) return Promise.resolve();
    if (!st.pumped) { S.say('Pump the chamber down first.'); return Promise.resolve(); }
    return S.hand.tap(qcb.knob, 'front').then(function () { st.zeroed = true; S.say('The monitor is zeroed: it reads the crystal at ' + fmtF(p.f0) + ' Hz.'); S.render(); });
  }
  function heatQ() {
    if (busy() || st.hot) return Promise.resolve();
    if (!st.zeroed) { S.say('Zero the monitor first.'); return Promise.resolve(); }
    return S.hand.tap(ctrl.knob, 'front').then(function () { st.hot = true; S.say('The boat glows: the metal is evaporating, but the shutter is still closed.'); S.render(); });
  }
  function shutterQ() {
    if (busy() || st.shutter) return Promise.resolve();
    if (!st.hot) { S.say('Heat the source first.'); return Promise.resolve(); }
    return S.hand.tap(shutter, 'top').then(function () { st.shutter = true; st.t = 0; S.say('Shutter open. The timer starts at zero; the crystal is now collecting the film.'); S.click(880, 0.05); S.render(); });
  }
  function recordQ() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return null; }
    if (!st.shutter || st.closed) { S.say('Record while the shutter is open.'); return null; }
    if (st.running) { S.say('Wait for the clock to stop.'); return null; }
    var tt = Math.round(st.t);
    if (tt < 1) { S.say('Let the clock run first.'); return null; }
    for (var i = 0; i < S.rows.length; i++) if (S.rows[i].t === tt) { S.say('You already have a reading at ' + tt + ' s.'); return null; }
    var f = Math.round(KN.freq(p, tt));
    var row = { t: tt, f: f, df: f - p.f0 };
    S.addRow(row); S.say('Written in your record book: t = ' + tt + ' s, f = ' + f + ' Hz.'); return row;
  }
  function closeShutter() {
    if (busy() || st.closed) return Promise.resolve();
    if (!st.shutter) { S.say('The shutter is not open yet.'); return Promise.resolve(); }
    if (st.t < p.Tdep - 1) { S.say('Run the clock to ' + p.Tdep + ' s before closing the shutter: this lab deposits for ' + p.Tdep + ' s.'); return Promise.resolve(); }
    return S.hand.tap(shutter, 'top').then(function () { st.closed = true; S.say('Shutter closed. The film is finished; cool the source and take the substrate out.'); S.render(); });
  }
  function stylusQ() {
    if (busy() || st.stylus) return Promise.resolve();
    if (!st.closed) { S.say('Finish the deposition first.'); return Promise.resolve(); }
    st.stylus = p.tool * p.rate * p.Tdep; S.say('The stylus profilometer measures a step of ' + (st.stylus * 1e9).toFixed(1) + ' nm on the substrate.');
    S.addRow({ t: 'step', f: 0, df: 0, step: st.stylus * 1e9 }); S.render(); return Promise.resolve();
  }
  function qFit() {
    var pts = S.rows.filter(function (r) { return typeof r.t === 'number' && r.t <= 80; }).map(function (r) { return [r.t, r.f]; });
    if (pts.length < 6) return null;
    var f = S.fit.linear(pts); if (!f || f.m >= 0) return null;
    var rate = -f.m / (KN.sens(p) * p.rho_f);
    return { rate: rate, thick: rate * p.Tdep, n: pts.length };
  }

  function result(rows) {
    if (QCM) {
      var q = qFit(); if (!q) return null;
      var tf = st.stylus ? st.stylus / q.thick : 0;
      return { label: 'Deposition rate', value: q.rate * 1e9, unit: 'nm/s', digits: 4, truth: p.rate * 1e9,
        note: 'Slope of the crystal frequency against time over ' + q.n + ' readings, divided by C ρf with C = 2 f0² / √(ρq μq): rate ' + (q.rate * 1e9).toFixed(4) + ' nm/s, so the monitor reports ' + (q.thick * 1e9).toFixed(1) + ' nm after ' + p.Tdep + ' s.' + (tf ? ' The stylus step on the substrate is ' + (st.stylus * 1e9).toFixed(1) + ' nm, so the tooling factor is ' + tf.toFixed(3) + '.' : '') };
    }
    var v = vacFit(); if (!v) return null;
    var r = riseFit();
    var p200 = null; rows.forEach(function (x) { if (x.kind === 'pump' && x.t === 200) p200 = x.P; });
    var pu = null; rows.forEach(function (x) { if (x.kind === 'pump' && x.t >= 1500) pu = x.P; });
    var note = 'Readings between 0.3 and 10 Pa (' + v.n + ' of them): ln P falls with slope −S/V, so S = ' + (v.S * 1000).toFixed(1) + ' L/s. The pump is rated ' + (p.Sp * 1000).toFixed(0) + ' L/s, so 1/C = 1/S − 1/Sp gives C = ' + (v.C * 1000).toFixed(1) + ' L/s.';
    if (r) note += ' The rate-of-rise slope gives the leak rate ' + r.QL.toExponential(2) + ' Pa m³/s.';
    if (r && p200) note += ' Throughput at 200 s S·P − leak = ' + (v.S * p200 - r.QL).toExponential(2) + ' Pa m³/s is the outgassing then.';
    if (pu) note += ' Ultimate pressure about ' + fmtP(pu) + ' Pa.';
    return { label: 'Conductance of the pipe', value: v.C * 1000, unit: 'L/s', digits: 2, truth: KN.cond(p) * 1000, note: note };
  }

  var cols = QCM
    ? [{ label: 't (s)', get: function (r) { return r.t; } }, { label: 'f (Hz)', get: function (r) { return r.step === undefined ? r.f : '—'; } }, { label: 'Δf (Hz)', get: function (r) { return r.step === undefined ? r.df : '—'; } }, { label: 'step (nm)', get: function (r) { return r.step === undefined ? '—' : r.step.toFixed(1); } }]
    : [{ label: 'run', get: function (r) { return r.kind === 'rise' ? 'rise' : 'pump-down'; } }, { label: 't (s)', get: function (r) { return r.t; } }, { label: 'P (Pa)', get: function (r) { return fmtP(r.P); } }, { label: 'ln P', get: function (r) { return r.lnP.toFixed(2); } }];

  var TLIST = [1, 2, 3, 4, 5, 6, 200, 1800], ULIST = [20, 60, 100, 140], QLIST = [10, 20, 30, 40, 50, 60, 70, 80];
  var theoryQ = { principle: S.lab.theory, formula: 'Δf = − 2 f0² ρf h / √(ρq μq)', formulaNote: 'h the film thickness on the crystal; the substrate sees (tooling factor) × h',
    more: ['The crystal here is 6 MHz AT-cut quartz; the relation holds while the frequency has fallen by under about 2 %.', 'The slope of f against t gives the rate at once: dh/dt = −(df/dt) √(ρq μq) / (2 f0² ρf).', 'The tooling factor is found once by comparing the monitor with a measured step height, then reused.'], precautions: S.lab.safety };
  var theoryV = { principle: S.lab.theory, formula: '1/S = 1/Sp + 1/C,   C = (π/12) v̄ d³ / L',
    formulaNote: 'molecular flow in a long pipe; v̄ = √(8kT/πm); P falls as exp(−S t / V)', more: ['The rate of rise with the pump isolated is (QL + Qout)/V. Outgassing fades with time; the leak stays constant.', 'Gauges: Pirani 0.1 Pa to 1 kPa, ion gauge below 0.1 Pa.', 'The pump speeds are illustrative nameplate values; the pipe bore is hidden and found from the conductance.'], precautions: S.lab.safety };

  var steps;
  if (QCM) steps = [
    { id: 'pump', title: 'Pump down', view: 'jar', render: function (u) {
        u.h2('Close the vent, pump the chamber down');
        u.p('A clean metal film needs a high vacuum. Close the vent valve, then switch the pumps on and wait for the chamber to come to about 5×10⁻⁴ Pa.');
        u.task('1. Close the vent valve', st.vent, st.vent ? 'Closed' : 'Open').add(u.button(st.vent ? 'Closed' : 'Close the vent valve', function () { S.focus('jar'); ventClose(); }, !st.vent, st.vent || S.hand.busy));
        u.task('2. Pump down', st.pumped, st.pumped ? 'At high vacuum' : st.fp === 1 ? 'Pumping…' : 'Not started').add(u.button(st.pumped ? 'Pumped' : 'Start the pumps', function () { S.focus('ctrl'); pumpDownQ(); }, !st.pumped && st.vent, st.pumped || !st.vent || S.hand.busy));
        u.live(function () { return 'Gauge ' + (st.pumped ? '5.00E-4 Pa' : st.fp === 1 ? 'falling…' : '1.01E5 Pa'); });
        u.next('Next: heat the source', st.pumped);
      },
      ok: function () { return st.pumped; }, auto: function () { return ventClose().then(pumpDownQ); } },
    { id: 'depo', title: 'Evaporate and read the crystal', view: 'qcm', render: function (u) {
        u.h2('Zero the monitor, heat the source, open the shutter');
        u.task('1. Zero the monitor', st.zeroed, st.zeroed ? fmtF(p.f0) + ' Hz' : 'Not zeroed').add(u.button(st.zeroed ? 'Zeroed' : 'Zero the monitor', function () { S.focus('qcm'); zeroQ(); }, !st.zeroed, st.zeroed || S.hand.busy));
        u.task('2. Heat the source', st.hot, st.hot ? 'Source glowing' : 'Cold').add(u.button(st.hot ? 'Hot' : 'Raise the current', function () { S.focus('ctrl'); heatQ(); }, !st.hot && st.zeroed, st.hot || !st.zeroed || S.hand.busy));
        u.task('3. Open the shutter', st.shutter, st.shutter ? 'Depositing' : 'Closed').add(u.button(st.shutter ? 'Open' : 'Open the shutter', function () { S.focus('jar'); shutterQ(); }, !st.shutter && st.hot, st.shutter || !st.hot || S.hand.busy));
        var tg = { v: Math.max(10, Math.round(st.t)) };
        u.slider('Run the clock to', 0, p.Tdep, 1, function () { return tg.v; }, function (v) { tg.v = v; }, 's', 0);
        u.row(u.button('Run the clock', function () { S.focus('qcm'); runTo(tg.v, p.Tdep); }, true, S.hand.busy || !st.shutter), u.button('Record the frequency', function () { S.focus('qcm'); recordQ(); }, false, S.hand.busy || !st.shutter));
        u.live(function () { return 't = ' + Math.round(st.t) + ' s  ·  f = ' + fmtF(KN.freq(p, st.shutter ? st.t : 0)) + ' Hz'; });
        u.h3('Observation table'); u.table();
        if (S.rows.length < 6) u.p(S.rows.length + ' of at least 6 readings (between 10 s and 80 s).');
        u.next('Next: close the shutter, measure the step', S.rows.length >= 6);
      },
      ok: function () { return S.rows.length >= 6; },
      auto: function () {
        return zeroQ().then(heatQ).then(shutterQ).then(function () {
          return QLIST.reduce(function (pr, t1) { return pr.then(function () { return runTo(t1, p.Tdep); }).then(function () { recordQ(); }); }, Promise.resolve());
        });
      } },
    { id: 'step', title: 'Close the shutter, measure the step', view: 'jar', render: function (u) {
        u.h2('Finish the film, measure its thickness on the substrate');
        u.p('Run the clock to ' + p.Tdep + ' s, close the shutter, then measure the step height on the substrate with the stylus profilometer. Compare it with the monitor\'s thickness: the ratio is the tooling factor.');
        u.row(u.button('Run to ' + p.Tdep + ' s', function () { runTo(p.Tdep, p.Tdep); }, !st.closed && st.t < p.Tdep, st.closed || S.hand.busy), u.button(st.closed ? 'Shutter closed' : 'Close the shutter', function () { S.focus('jar'); closeShutter(); }, !st.closed && st.t >= p.Tdep - 1, st.closed || st.t < p.Tdep - 1 || S.hand.busy));
        u.task('Stylus step on the substrate', !!st.stylus, st.stylus ? (st.stylus * 1e9).toFixed(1) + ' nm' : 'Not measured').add(u.button(st.stylus ? 'Measured' : 'Measure the step', function () { stylusQ(); }, !st.stylus && st.closed, !!st.stylus || !st.closed || S.hand.busy));
        var q = qFit(); if (q) u.p('From your readings the monitor reports ' + (q.thick * 1e9).toFixed(1) + ' nm after ' + p.Tdep + ' s.' + (st.stylus ? ' Tooling factor = ' + (st.stylus / q.thick).toFixed(3) + '.' : ''));
        u.next('Next: the result', !!st.stylus);
      },
      ok: function () { return !!st.stylus; }, auto: function () { return runTo(p.Tdep, p.Tdep).then(closeShutter).then(stylusQ); } }
  ];
  else steps = [
    { id: 'rough', title: 'Rough the chamber', view: 'jar', render: function (u) {
        u.h2('Close the vent, start the rotary pump, rough to ' + p.Px + ' Pa');
        u.p('The chamber is at atmospheric pressure. The high-vacuum pump cannot start from there: the rotary pump takes the chamber down to ' + p.Px + ' Pa first.');
        u.task('1. Close the vent valve', st.vent, st.vent ? 'Closed' : 'Open').add(u.button(st.vent ? 'Closed' : 'Close the vent valve', function () { S.focus('jar'); ventClose(); }, !st.vent, st.vent || S.hand.busy));
        u.task('2. Start the rotary pump', st.rotary, st.rotary ? 'Running' : 'Off').add(u.button(st.rotary ? 'Running' : 'Start the pump', function () { S.focus('ctrl'); rotaryStart(); }, !st.rotary && st.vent, st.rotary || !st.vent || S.hand.busy));
        u.task('3. Rough to ' + p.Px + ' Pa', st.fp === 2, st.fp === 2 ? 'Done' : st.fp === 1 ? 'Roughing…' : 'Waiting').add(u.button(st.fp === 2 ? 'Roughed' : 'Rough the chamber', function () { S.focus('gauge'); roughDown(); }, st.fp !== 2 && st.rotary, st.fp === 2 || !st.rotary || S.hand.busy));
        u.live(function () { return 'Gauge ' + fmtP(pnow()) + ' Pa'; });
        u.next('Next: open the gate valve', st.fp === 2);
      },
      ok: function () { return st.fp === 2; }, auto: function () { return ventClose().then(rotaryStart).then(roughDown); } },
    { id: 'pump', title: 'High-vacuum pump-down', view: 'gauge', render: function (u) {
        u.h2('Open the gate valve and read the gauge');
        u.p('Open the gate valve. Record the gauge every second for the first 6 s (the pressure is far above the ultimate pressure, so the gas load does not matter), then let the clock run to 200 s and 1800 s and record again.');
        u.task('Gate valve', st.gate || st.iso, st.gate ? 'Open' : 'Closed').add(u.button(st.gate ? 'Open' : 'Open the gate valve', function () { S.focus('gate'); openGate(); }, !st.gate, st.gate || S.hand.busy));
        var tg = { v: Math.max(1, Math.round(st.t)) };
        u.slider('Run the clock to', 0, 2000, 1, function () { return tg.v; }, function (v) { tg.v = v; }, 's', 0);
        u.row(u.button('Run the clock', function () { S.focus('ctrl'); runTo(tg.v, 2000); }, true, S.hand.busy || !st.gate), u.button('Record the reading', function () { S.focus('gauge'); recordVac(); }, false, S.hand.busy || !st.gate));
        u.live(function () { return 't = ' + Math.round(st.t) + ' s  ·  P = ' + fmtP(pnow()) + ' Pa'; });
        u.h3('Observation table'); u.table();
        var okc = S.rows.filter(function (r) { return r.kind === 'pump' && r.P >= 0.3 && r.P <= 10; }).length;
        u.p(okc + ' of at least 5 readings between 0.3 and 10 Pa; a reading at about 1800 s is needed for the rise test.');
        u.next('Next: the rate-of-rise test', okc >= 5 && st.t >= 1000);
      },
      ok: function () { return vacFit() !== null && st.t >= 1000; },
      auto: function () {
        return openGate().then(function () { return TLIST.reduce(function (pr, t1) { return pr.then(function () { return runTo(t1, 2000); }).then(function () { recordVac(); }); }, Promise.resolve()); });
      } },
    { id: 'rise', title: 'Rate of rise', view: 'gate', render: function (u) {
        u.h2('Close the gate valve and watch the pressure rise');
        u.p('The outgassing has died away by now. Close the gate valve, then run the clock and record the pressure: it rises at (leak rate) / V.');
        u.task('Isolate the chamber', st.iso, st.iso ? 'Gate valve closed at ' + Math.round(st.tc) + ' s' : 'Pumping').add(u.button(st.iso ? 'Isolated' : 'Close the gate valve', function () { S.focus('gate'); isolate(); }, !st.iso, st.iso || S.hand.busy));
        var tg = { v: 20 };
        u.slider('Run the clock to', 0, 300, 1, function () { return tg.v; }, function (v) { tg.v = v; }, 's', 0);
        u.row(u.button('Run the clock', function () { S.focus('ctrl'); runTo(tg.v, 300); }, true, S.hand.busy || !st.iso), u.button('Record the reading', function () { S.focus('gauge'); recordVac(); }, false, S.hand.busy || !st.iso));
        u.live(function () { return 't = ' + Math.round(st.t) + ' s after closing  ·  P = ' + fmtP(pnow()) + ' Pa'; });
        u.h3('Observation table'); u.table();
        u.next('Next: the result', S.rows.filter(function (r) { return r.kind === 'rise'; }).length >= 4);
      },
      ok: function () { return S.rows.filter(function (r) { return r.kind === 'rise'; }).length >= 4; },
      auto: function () { return isolate().then(function () { return ULIST.reduce(function (pr, t1) { return pr.then(function () { return runTo(t1, 300); }).then(function () { recordVac(); }); }, Promise.resolve()); }); } }
  ];

  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { jar: [[-0.38, 0.3, 0.25], [-0.38, 0.1, -0.2]], hvpump: [[-0.04, 0.25, 0.1], [-0.04, 0.06, -0.2]], gate: [[-0.14, 0.2, 0.1], [-0.14, 0.04, -0.2]], gauge: [[0.3, 0.24, 0.08], [0.3, 0.05, -0.22]], ctrl: [[0.0, 0.26, 0.32], [0.0, 0.05, 0.1]],
      qcm: [[0.3, 0.24, 0.2], [0.3, 0.04, -0.02]], bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: QCM ? theoryQ : theoryV,
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 110) + (S.lab.aim.length > 110 ? '…' : ''), QCM ? 'Crystal 6 MHz; film: ' + SAMPLE + '.' : 'Chamber V = ' + (p.V * 1000).toFixed(0) + ' L; pump rated ' + (p.Sp * 1000).toFixed(0) + ' L/s; pipe length ' + p.Lt.toFixed(2) + ' m.'], columns: cols },
    graph: QCM ? { x: function (r) { return typeof r.t === 'number' ? r.t : NaN; }, y: function (r) { return r.step === undefined ? r.df : NaN; }, xlabel: 't (s)', ylabel: 'Δf (Hz)',
        line: function (pts) { var f = S.fit.linear(pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); })); return f ? function (x) { return f.m * x + f.c; } : null; } }
      : { x: function (r) { return r.kind === 'pump' ? r.t : NaN; }, y: function (r) { return r.kind === 'pump' ? r.lnP : NaN; }, xlabel: 't (s)', ylabel: 'ln P (P in Pa)', line: function () { return null; } },
    result: result,
    tol: QCM ? 0.02 : 0.03,
    resultNote: QCM ? 'The rate came from the slope of your own readings; the lab\'s true value is shown alongside.' : 'The conductance came from your own pump-down readings; the lab\'s true value (from the pipe\'s bore and length) is shown alongside.',
    chips: QCM ? ['Why does the frequency fall?', 'What is the tooling factor?', 'Check my readings', 'When does Sauerbrey fail?'] : ['Why is the speed less than the pump rating?', 'What is a rate-of-rise test?', 'Check my readings', 'Leak or outgassing?'],
    viva: [],
    askState: function () { return QCM ? { experiment: S.lab.title, film: SAMPLE, vacuum_ok: st.pumped, source_hot: st.hot, shutter_open: st.shutter && !st.closed, time_s: Math.round(st.t), readings_taken: S.rows.length }
      : { experiment: S.lab.title, vent_closed: st.vent, roughed: st.fp === 2, gate_open: st.gate, isolated: st.iso, time_s: Math.round(st.t), gauge_Pa: fmtP(pnow()), readings_taken: S.rows.length }; },
    steps: steps,
    tick: function () {
      ctrl.show(Math.round(st.t) + '', 's');
      if (QCM) {
        var fq = KN.freq(p, st.shutter && !st.closed ? st.t : (st.closed ? p.Tdep : 0));
        if (st.closed) fq = KN.freq(p, p.Tdep);
        qcb.show(fmtF(st.zeroed ? fq : p.f0), 'Hz');
        var pg = st.pumped ? 5e-4 : (st.fp === 1 ? p.Pat * Math.pow(5e-4 / p.Pat, st.pk || 0) : p.Pat); gauge.show(fmtP(pg), 'Pa');
        glowM.opacity = st.hot ? 0.55 : 0; if (shutter) shutter.position.x = (st.shutter && !st.closed) ? 0.04 : 0;
        hudT.set(Math.round(st.t) + ' s'); hudP.set(fmtF(st.zeroed ? fq : p.f0) + ' Hz');
      } else {
        var v = pnow(); gauge.show(st.rotary || st.gate ? fmtP(v) : fmtP(p.Pat), 'Pa');
        wheel.rotation.y = st.gate ? 1.0 : 0;
        hudT.set(Math.round(st.t) + ' s'); hudP.set(fmtP(v) + ' Pa');
      }
    },
  };
});
