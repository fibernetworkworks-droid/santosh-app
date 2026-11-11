/* Prayogshala studio module: Searle's apparatus - thermal conductivity of a metal bar (B.Sc. Thermal Physics).
   Physics: the hw_searle kernel (packs/heat_wave_ug) - the same numbers the server checks. Steam heats one end of a
   lagged bar, cooling water takes the heat from the other; K is worked out from the four temperatures and the mass of
   water collected. The hidden knob K (the metal) is what the student measures. */
HoolaStudio.define('searle-thermal-conductivity', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.hw_searle;
  var up = new T.Vector3(0, 1, 0);
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('hw_searle');
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var MET = /alumin/i.test(SAMPLE) ? { name: 'Aluminium', mat: M.alu, tag: 'ALUMINIUM BAR' } : /brass/i.test(SAMPLE) ? { name: 'Brass', mat: M.brass, tag: 'BRASS BAR' }
    : /iron/i.test(SAMPLE) ? { name: 'Iron', mat: M.iron, tag: 'IRON BAR' } : { name: 'Copper', mat: M.copper, tag: 'COPPER BAR' };
  function r1(v) { return Math.round(v * 10) / 10; }
  var A = Math.PI * p.r * p.r, DIA = 2 * p.r;
  var Z0 = -0.26, Y0 = 0.11, XH = -0.5;                      // the bar axis: z, height, and the hot end of the bar
  var sim = K.init(p);
  var st = { dims: false, boiler: false, tap: false, speed: 30, read: null, collecting: false, tc0: 0, mass: null, tcol: 0, cold: 0 };

  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'grip', 320); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }
  function clampStand(jx, jz, armY, armLen, h) {
    var g = S.stand({ x: 0, z: 0, armY: armY, armLen: armLen, h: h });
    var blob = S.scene.children[S.scene.children.length - 1], rotY = -Math.PI / 2;
    g.rotation.y = rotY; var j = new T.Vector3(-0.19 + armLen, 0, 0).applyAxisAngle(up, rotY);
    g.position.set(jx - j.x, 0, jz - j.z);
    var bc = new T.Vector3(-0.12, 0, 0).applyAxisAngle(up, rotY); blob.position.set(g.position.x + bc.x, blob.position.y, g.position.z + bc.z); blob.rotation.z = rotY;
    return g;
  }
  function tube(pts, r, mat) {                               // a rubber / metal pipe along a smooth curve
    var curve = new T.CatmullRomCurve3(pts.map(function (a) { return new T.Vector3(a[0], a[1], a[2]); }));
    var m = S.mesh(new T.TubeGeometry(curve, 40, r, 10, false), mat, true, false); S.scene.add(m); return m;
  }
  var rubber = new T.MeshStandardMaterial({ color: 0x2b2d30, roughness: 0.6 }), felt = new T.MeshStandardMaterial({ color: 0xd9d1bb, roughness: 1 });
  var waterM = new T.MeshStandardMaterial({ color: 0x9cc6d6, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.9 });

  // ---------- the bar, lagging, steam chamber, supports
  var barG = new T.Group(); S.scene.add(barG);
  var LB = p.Lb;
  var bar = S.mesh(new T.CylinderGeometry(p.r, p.r, LB + 0.06, 40), MET.mat); bar.rotation.z = Math.PI / 2; bar.position.set(XH + LB / 2 - 0.0, Y0, Z0); barG.add(bar);
  var lag = S.mesh(new T.CylinderGeometry(0.03, 0.03, LB - 0.1, 40), felt); lag.rotation.z = Math.PI / 2; lag.position.set(XH + 0.04 + (LB - 0.1) / 2, Y0, Z0); barG.add(lag);
  var chest = new T.Group(); S.scene.add(chest);
  var cb = S.mesh(new T.CylinderGeometry(0.05, 0.05, 0.1, 40), M.brass); cb.rotation.z = Math.PI / 2; cb.position.set(XH - 0.03, Y0, Z0); chest.add(cb);
  [-0.083, 0.023].forEach(function (dx) { var cap = S.mesh(new T.CylinderGeometry(0.052, 0.052, 0.006, 40), M.brass); cap.rotation.z = Math.PI / 2; cap.position.set(XH + dx, Y0, Z0); chest.add(cap); });
  var drain = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.06, 12), M.brass); drain.position.set(XH - 0.03, Y0 - 0.075, Z0); chest.add(drain);
  var cl = S.label('STEAM CHAMBER', { w: 0.07, ratio: 0.16, color: '#4a3510' }); cl.position.set(XH - 0.03, Y0 + 0.0, Z0 + 0.0515); chest.add(cl);
  [XH - 0.03, XH + 0.26].forEach(function (x) {              // wooden V-block supports
    var blk = S.rounded(0.05, 0.075, 0.06, 0.006, M.wood); blk.position.set(x, 0.0375, Z0); S.scene.add(blk); S.contact(0.1, 0.1, x, Z0, 0.5); });
  var tagL = S.label(MET.tag, { w: 0.06, ratio: 0.16, color: '#5a4a20' }); tagL.position.set(XH + 0.2, Y0, Z0 + 0.0305); S.scene.add(tagL);
  // two bar thermometers dip into holes bored in the bar at x1 and x2 (mercury in oil, through the lagging)
  var X1 = XH + p.x1, X2 = XH + p.x2;
  var th1 = S.thermometer({ len: 0.3, min: 20, max: 110, value: p.Tin, pos: [X1, Y0 + 0.012, Z0] });
  var th2 = S.thermometer({ len: 0.3, min: 20, max: 110, value: p.Tin, pos: [X2, Y0 + 0.012, Z0] });
  // cooling coil on the cold end
  var coilG = new T.Group(); S.scene.add(coilG);
  for (var i = 0; i < 5; i++) { var rg = S.mesh(new T.TorusGeometry(0.02, 0.0035, 10, 36), M.copper); rg.rotation.y = Math.PI / 2; rg.position.set(XH + LB - 0.065 + i * 0.011, Y0, Z0); coilG.add(rg); }
  var coilEnd = XH + LB;
  // ---------- boiler on an electric plate, steam pipe to the chamber
  var BX = -0.8, BZ = -0.24;
  var plate = S.rounded(0.16, 0.16, 0.04, 0.01, new T.MeshStandardMaterial({ color: 0xe7e4dc, roughness: 0.5 })); plate.rotation.x = -Math.PI / 2; plate.position.set(BX, 0.02, BZ); S.scene.add(plate);
  var bsw = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.012, 24), M.red); bsw.rotation.x = Math.PI / 2; bsw.position.set(BX + 0.05, 0.02, BZ + 0.083); S.scene.add(bsw);
  var boiler = S.mesh(new T.SphereGeometry(0.065, 32, 24), M.copper); boiler.position.set(BX, 0.04 + 0.06, BZ); boiler.scale.y = 0.9; S.scene.add(boiler);
  var bneck = S.mesh(new T.CylinderGeometry(0.018, 0.026, 0.05, 20), M.copper); bneck.position.set(BX, 0.04 + 0.12, BZ); S.scene.add(bneck);
  S.contact(0.22, 0.22, BX, BZ, 0.5);
  var pipe = tube([[BX, 0.2, BZ], [BX, 0.24, BZ], [BX + 0.15, 0.22, BZ], [XH - 0.17, 0.2, Z0], [XH - 0.1, Y0 + 0.06, Z0 + 0.0], [XH - 0.06, Y0 + 0.03, Z0]], 0.006, rubber);
  var stand0 = clampStand(BX + 0.0, BZ + 0.1, 0.2, 0.3, 0.3);
  // ---------- constant-head water tank with a tap, rubber pipes through the coil
  var TX = 0.55, TZ = -0.32;
  var tank = S.beaker(0.07, 0.15, [TX, 0.14, TZ]); var tpl = S.rounded(0.2, 0.2, 0.14, 0.01, M.wood); tpl.rotation.x = -Math.PI / 2; tpl.position.set(TX, 0.07, TZ); S.scene.add(tpl); S.contact(0.26, 0.26, TX, TZ, 0.5);
  var twater = S.mesh(new T.CylinderGeometry(0.066, 0.066, 0.11, 40), new T.MeshStandardMaterial({ color: 0x6aaccc, roughness: 0.05, metalness: 0.08 }), false); twater.position.set(0, 0.058, 0); tank.add(twater);
  var tapB = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.03, 14), M.brass); tapB.rotation.z = Math.PI / 2; tapB.position.set(TX - 0.08, 0.17, TZ); S.scene.add(tapB);
  var tapH = S.mesh(new T.BoxGeometry(0.03, 0.006, 0.008), M.red); tapH.position.set(TX - 0.088, 0.19, TZ); S.scene.add(tapH);
  var tl = S.label('CONSTANT HEAD TANK', { w: 0.1, ratio: 0.12, color: '#2b3b4a' }); tl.position.set(TX, 0.17, TZ + 0.0715); S.scene.add(tl);
  var inletThermo = S.thermometer({ len: 0.22, min: 10, max: 50, value: p.Tin, pos: [coilEnd + 0.06, 0.19, Z0 + 0.07] });
  var outThermo = S.thermometer({ len: 0.22, min: 10, max: 50, value: p.Tin, pos: [coilEnd + 0.15, 0.13, Z0] });
  tube([[TX - 0.095, 0.17, TZ], [TX - 0.2, 0.2, TZ + 0.1], [coilEnd + 0.06, 0.2, Z0 + 0.07], [coilEnd + 0.0, Y0 + 0.05, Z0 + 0.03], [coilEnd - 0.065, Y0 + 0.021, Z0 + 0.0]], 0.004, rubber);
  var spout = tube([[coilEnd - 0.011, Y0 + 0.021, Z0], [coilEnd + 0.04, 0.14, Z0], [coilEnd + 0.22, 0.14, Z0], [coilEnd + 0.22, 0.122, Z0]], 0.004, rubber);
  // ---------- beaker, digital balance, stopwatch
  var BKX = 0.72, BKZ = -0.02, BK = { r: 0.04, h: 0.1 };
  var spoutPos = new T.Vector3(coilEnd + 0.22, 0.0, Z0);
  var balance = new T.Group(); S.scene.add(balance);
  var bb = S.rounded(0.16, 0.12, 0.035, 0.008, new T.MeshStandardMaterial({ color: 0xeceae3, roughness: 0.5 })); bb.rotation.x = -Math.PI / 2; bb.position.set(0, 0.0175, 0); balance.add(bb);
  var pan = S.mesh(new T.CylinderGeometry(0.05, 0.05, 0.004, 40), M.chrome); pan.position.set(0, 0.037, -0.005); balance.add(pan);
  var lcd = S.liveTex(256, 96), lcdM = new T.Mesh(new T.PlaneGeometry(0.06, 0.0225), new T.MeshBasicMaterial({ map: lcd })); lcdM.position.set(0.03, 0.0182, 0.0605); lcdM.rotation.x = 0; balance.add(lcdM);
  balance.position.set(BKX, 0, BKZ + 0.0); S.contact(0.2, 0.18, BKX, BKZ, 0.5);
  var lastLcd = '';
  function drawLcd(g) { var txt = (g === null ? 0 : g).toFixed(0) + ' g'; if (txt === lastLcd) return; lastLcd = txt;
    lcd.draw(function (x, w, h) { x.fillStyle = '#b9c4a7'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b2116'; x.font = '700 62px "JetBrains Mono", monospace'; x.textAlign = 'right'; x.fillText(txt, w - 12, h - 22); }); }
  drawLcd(0);
  var beaker = S.beaker(BK.r, BK.h, [BKX, 0.039, BKZ - 0.005]);
  var bwater = S.mesh(new T.CylinderGeometry(BK.r * 0.95, BK.r * 0.95, 1, 36), new T.MeshStandardMaterial({ color: 0x6aaccc, roughness: 0.05, metalness: 0.08 }), false); beaker.add(bwater); bwater.visible = false;
  function setBeakerWater(g) { var hh = Math.max(0.0005, Math.min(0.09, g / 1000 / (Math.PI * BK.r * BK.r * 0.9))); bwater.scale.y = hh; bwater.position.y = 0.002 + hh / 2; bwater.visible = g > 0.5; }
  var bkShadow = S.contact(0.12, 0.12, BKX, BKZ - 0.005, 0.0);
  var watch = S.stopwatch([0.3, 0.035, 0.17], [-1.15, 0, -0.2]);
  var jet = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 1, 10), waterM, false); jet.visible = false; S.scene.add(jet);
  var steamTex = S.canvasTex(128, 128, function (x) { var g = x.createRadialGradient(64, 64, 2, 64, 64, 62); g.addColorStop(0, 'rgba(255,255,255,.75)'); g.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = g; x.fillRect(0, 0, 128, 128); });
  var wisps = []; for (var wi = 0; wi < 6; wi++) { var w = new T.Mesh(new T.PlaneGeometry(0.05, 0.05), new T.MeshBasicMaterial({ map: steamTex, transparent: true, opacity: 0, depthWrite: false }));
    w.userData.ph = wi / 6; S.scene.add(w); wisps.push(w); }

  S.addApparatus('bar', barG, MET.name + ' bar', 'Radius ' + (p.r * 1000).toFixed(2) + ' mm, wrapped in felt so heat leaves only along its length. Heated by steam at the left end.');
  S.addApparatus('chest', chest, 'Steam chamber', 'Steam from the boiler keeps the hot end at 100 °C.');
  S.addApparatus('th1', th1, 'Thermometer θ1', 'Dips into a hole in the bar ' + (p.x1 * 100).toFixed(0) + ' cm from the hot end. Calorimetric thermometer, least count 0.1 °C.');
  S.addApparatus('th2', th2, 'Thermometer θ2', 'Dips into a second hole ' + ((p.x2 - p.x1) * 100).toFixed(0) + ' cm further along. Calorimetric thermometer, least count 0.1 °C.');
  S.addApparatus('coil', coilG, 'Cooling coil', 'Water from the tank runs through a copper coil round the cold end and carries the heat away.');
  S.addApparatus('boiler', boiler, 'Boiler', 'Electric boiler that makes steam for the chamber. Switch it on at the plate.');
  S.addApparatus('tank', tank, 'Constant-head tank', 'Keeps the water flow steady. The tap sets how fast it runs.');
  S.addApparatus('tin', inletThermo, 'Inlet thermometer', 'Reads the temperature of the water entering the coil.');
  S.addApparatus('tout', outThermo, 'Outlet thermometer', 'Reads the temperature of the water leaving the coil.');
  S.addApparatus('beaker', beaker, 'Beaker', 'Collects the water that leaves the coil, to be weighed.');
  S.addApparatus('bal', balance, 'Digital balance', 'Reads to 1 g. Weigh the beaker with the water in it.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Times the collection of water.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');

  var bookLines = ['Aim: to find K of the ' + MET.name.toLowerCase() + ' bar by Searle\'s method.', 'Radius r = ' + (p.r * 1000).toFixed(2) + ' mm,  x2 − x1 = ' + ((p.x2 - p.x1) * 100).toFixed(1) + ' cm',
    'K = m c (Tout − Tin)(x2 − x1) / (t A (θ1 − θ2))', 'c of water = ' + p.cw + ' J/(kg K)'];
  var hudA = S.hudCard('Bar θ1'), hudB = S.hudCard('Bar θ2'), hudC = S.hudCard('Water out'), hudD = S.hudCard('Lab time');

  function nowV() { return K.view(sim, p); }
  // ---------- actions
  function measureBar() { if (st.dims) return; st.dims = true; S.focus('bar'); S.say('Diameter 2r = ' + (DIA * 1000).toFixed(2) + ' mm (screw gauge). Thermometer holes ' + ((p.x2 - p.x1) * 100).toFixed(1) + ' cm apart. Written in your record book.'); S.book.draw(); S.render(); }
  function boilerOn() { if (S.hand.busy || st.boiler) return Promise.resolve(); return S.hand.tap(bsw).then(function () { S.click(2000); st.boiler = true; S.say('Boiler on. Steam will soon fill the chamber.'); S.render(); }); }
  function tapOpen() { if (S.hand.busy || st.tap) return Promise.resolve(); return S.hand.tap(tapH).then(function () { S.click(1500); st.tap = true; tapH.rotation.y = Math.PI / 2;
    S.say('Water is flowing through the coil at ' + (p.mdot * 1000).toFixed(2) + ' g every second.'); S.render(); }); }
  function running() { return st.boiler && st.tap; }
  function jump(sec) { if (!running()) { S.say('Switch the boiler on and open the tap first.'); return; } K.step(sim, p, sec); updateDevices(); S.render(); }
  function view5(back) { var s = { t: Math.max(0, sim.t - back) }; return K.view(s, p); }
  function drift() { var a = nowV(), b = view5(300); return { d1: a.th1 - b.th1, d2: a.th2 - b.th2, dw: a.Tout - b.Tout, ok: sim.t >= 300 && Math.abs(a.th1 - b.th1) < 0.15 && Math.abs(a.th2 - b.th2) < 0.15 && Math.abs(a.Tout - b.Tout) < 0.15 }; }
  function readAll() {
    if (!running()) { S.say('Switch the boiler on and open the tap first.'); return; }
    var v = nowV(); st.read = { th1: r1(v.th1), th2: r1(v.th2), Tin: r1(v.Tin), Tout: r1(v.Tout) };
    S.say('Read θ1 = ' + st.read.th1.toFixed(1) + ', θ2 = ' + st.read.th2.toFixed(1) + ', water in ' + st.read.Tin.toFixed(1) + ', out ' + st.read.Tout.toFixed(1) + ' °C.'); S.focus('th1'); S.render();
  }
  function placeBeaker(pos) { beaker.position.set(pos.x, pos.y, pos.z); bkShadow.position.set(pos.x, 0.0008, pos.z); bkShadow.material.opacity = pos.y > 0.01 ? 0.45 : 0.4; }
  var home = new T.Vector3(BKX, 0.039, BKZ - 0.005), under = new T.Vector3(spoutPos.x, 0.0, spoutPos.z);
  function moveBeaker(a, b) {
    var lift = 0.06;
    return carry(new T.Vector3(a.x + BK.r + 0.004, a.y + 0.05, a.z), [{ ms: 1500, fn: function (k) { var q = a.clone().lerp(b, k); q.y += Math.sin(k * Math.PI) * lift; return new T.Vector3(q.x + BK.r + 0.004, q.y + 0.05, q.z); },
      onK: function (k) { var q = a.clone().lerp(b, k); q.y += Math.sin(k * Math.PI) * lift; placeBeaker(q); } }], 'grip').then(function () { placeBeaker(b); });
  }
  function startCollect() {
    if (S.hand.busy) return Promise.resolve();
    if (!running()) { S.say('Switch the boiler on and open the tap first.'); return Promise.resolve(); }
    if (st.collecting) { S.say('Already collecting.'); return Promise.resolve(); }
    return moveBeaker(home, under).then(function () { return S.hand.tap(watch.start); }).then(function () { S.click(2400);
      st.collecting = true; st.tc0 = sim.t; watch.t = 0; watch.on = true; st.mass = null; S.say('Collecting. Stopwatch started.'); S.render(); });
  }
  function stopCollect() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.collecting) { S.say('Start collecting first.'); return Promise.resolve(); }
    return S.hand.tap(watch.start).then(function () { S.click(2400); watch.on = false; st.collecting = false; st.tcol = Math.round(sim.t - st.tc0);
      return moveBeaker(under, home); }).then(function () {
      st.mass = Math.round(p.mdot * (sim.t - st.tc0) * 1000); setBeakerWater(st.mass); drawLcd(st.mass);
      S.say('Collected ' + st.mass + ' g in ' + st.tcol + ' s (balance).'); S.focus('bal'); S.render(); });
  }
  function record() {
    if (!st.read || st.mass === null || st.tcol < 120) { S.say('Read the thermometers and collect water for at least two minutes first.'); return; }
    var dTw = r1(st.read.Tout - st.read.Tin), dth = r1(st.read.th1 - st.read.th2);
    S.addRow({ m: st.mass / 1000, t: st.tcol, Tin: st.read.Tin, Tout: st.read.Tout, th1: st.read.th1, th2: st.read.th2, dTw: dTw, dth: dth });
    S.say('Row written: ΔTw = ' + dTw.toFixed(1) + ' K, Δθ = ' + dth.toFixed(1) + ' K.');
    st.mass = null; st.read = null; setBeakerWater(0); drawLcd(0); S.render();
  }
  function Kone(r) { return r.m * p.cw * r.dTw * (p.x2 - p.x1) / (r.t * A * r.dth); }
  function updateDevices() {
    var v = nowV(); th1.set(v.th1); th2.set(v.th2); inletThermo.set(v.Tin); outThermo.set(v.Tout);
  }
  function setSpeed(v) { st.speed = v; S.render(); }

  return {
    camera: { pos: [-0.05, 0.65, 2.1], look: [-0.05, 0.1, -0.2] },
    views: { bar: [[-0.15, 0.3, 0.45], [-0.15, 0.1, Z0]], chest: [[-0.5, 0.3, 0.4], [XH - 0.03, 0.11, Z0]], th1: [[-0.25, 0.35, 0.4], [XH + 0.17, 0.2, Z0]], th2: [[-0.2, 0.35, 0.4], [XH + 0.2, 0.2, Z0]],
      coil: [[0.1, 0.25, 0.4], [coilEnd - 0.03, 0.1, Z0]], boiler: [[-0.7, 0.3, 0.4], [BX, 0.12, BZ]], tank: [[0.4, 0.3, 0.35], [TX, 0.12, TZ]], tin: [[0.2, 0.3, 0.35], [coilEnd + 0.12, 0.1, Z0 + 0.07]],
      tout: [[0.3, 0.3, 0.35], [coilEnd + 0.19, 0.1, Z0]], beaker: [[0.65, 0.25, 0.3], [0.55, 0.05, -0.03]], bal: [[0.9, 0.25, 0.3], [BKX, 0.03, BKZ]], sw: [[-0.5, 0.4, 0.5], [-1.1, 0.05, -0.2]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'Heat flows along a lagged bar from the steam end to the water-cooled end. Once the temperatures stop changing, the heat the water takes up each second equals the heat that flows through the bar.',
      formula: 'K A (θ1 − θ2) / (x2 − x1) = m c (Tout − Tin) / t', formulaNote: 'so K = m c (Tout − Tin)(x2 − x1) / (t A (θ1 − θ2))',
      more: ['A = π r² is the area of cross-section of the bar. The lagging stops heat leaving the sides, so the same heat passes every section.'],
      precautions: 'Wait for the steady state: the bar thermometers must stay constant for five minutes. Keep the water flow constant. Handle steam and hot thermometers with care. Read the thermometers with your eye level with the mercury.' },
    book: { title: 'Expt. — Searle\'s apparatus', lines: bookLines,
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'm (g)', get: function (r) { return (r.m * 1000).toFixed(0); } }, { label: 't (s)', get: function (r) { return String(r.t); } },
        { label: 'Tin / Tout', get: function (r) { return r.Tin.toFixed(1) + ' / ' + r.Tout.toFixed(1); } }, { label: 'θ1 / θ2', get: function (r) { return r.th1.toFixed(1) + ' / ' + r.th2.toFixed(1); } },
        { label: 'K', get: function (r) { return Kone(r).toFixed(1); } }] },
    result: function (rows) { if (!rows.length) return null; var s = 0; rows.forEach(function (r) { s += Kone(r); });
      return { label: 'K (' + MET.name.toLowerCase() + ')', value: s / rows.length, unit: 'W/(m·K)', digits: 1, truth: p.K, note: 'Mean of ' + rows.length + ' readings. Water collected over ' + rows[0].t + ' s.' }; },
    tol: 0.03,
    chips: ['Why is the bar lagged?', 'How do I know it is steady?', 'Why use a coil of water?', 'Check my readings', 'Why is my K different?'],
    viva: [['Why do we wait for the steady state?', ['The same heat then flows through every part of the bar', 'The bar must melt', 'The water must boil'], 0, 'Only when temperatures stop changing is all the heat that enters carried on to the water.'],
      ['Which quantity must be measured very carefully because it is squared in A?', ['The radius of the bar', 'The time', 'The mass of water'], 0, 'A = π r², so a 1 % error in r gives a 2 % error in A.']],
    askState: function () { var v = nowV(); return { boiler_on: st.boiler, tap_open: st.tap, lab_time_s: Math.round(sim.t), steady: running() ? drift().ok : false, theta1_C: r1(v.th1), theta2_C: r1(v.th2), water_out_C: r1(v.Tout),
      readings_taken: S.rows.length, material: MET.name }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bar', render: function (u) {
          u.h2('Measure the bar, then start the steam and the water');
          u.task('1. Measure the bar', st.dims, st.dims ? 'Radius ' + (p.r * 1000).toFixed(2) + ' mm; holes ' + ((p.x2 - p.x1) * 100).toFixed(1) + ' cm apart' : 'Screw gauge and metre scale')
            .add(u.button(st.dims ? 'Measured' : 'Measure the bar', measureBar, !st.dims, st.dims));
          u.task('2. Switch the boiler on', st.boiler, st.boiler ? 'Steam is on' : 'The hand presses the switch on the plate')
            .add(u.button(st.boiler ? 'On' : 'Switch the boiler on', function () { boilerOn(); }, st.dims && !st.boiler, st.boiler || S.hand.busy));
          u.task('3. Open the water tap', st.tap, st.tap ? 'Water is flowing' : 'The hand turns the tap on the tank')
            .add(u.button(st.tap ? 'Open' : 'Open the tap', function () { tapOpen(); }, st.boiler && !st.tap, st.tap || S.hand.busy));
          u.note('The flow is set by the tank so that the water leaves about ' + ((p.mdot * p.cw > 0 ? K.steady(p).H / (p.mdot * p.cw) : 0)).toFixed(0) + ' °C warmer than it enters.');
          u.next('Next: wait for the steady state', st.dims && st.boiler && st.tap);
        },
        ok: function () { return st.dims && st.boiler && st.tap; },
        auto: function () { measureBar(); return boilerOn().then(function () { return tapOpen(); }); } },
      { id: 'steady', title: 'Steady state', view: 'th1', render: function (u) {
          u.h2('Wait until the temperatures stop changing');
          u.p('The bar takes a long time to settle. Let the clock run faster, then check that the readings changed by less than 0.15 °C in the last five minutes.');
          var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
          [1, 30, 120].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
          u.row(u.button('Jump 10 minutes', function () { jump(600); }, false, false));
          u.live(function () { var v = nowV(), d = drift(); return 'Lab time ' + Math.floor(sim.t / 60) + ' min · θ1 ' + r1(v.th1).toFixed(1) + ' · θ2 ' + r1(v.th2).toFixed(1) + ' · out ' + r1(v.Tout).toFixed(1) + ' °C · ' + (sim.t < 300 ? 'too early to judge' : d.ok ? 'STEADY' : 'still changing'); });
          u.note('Change in the last 5 minutes appears on the live line only once five minutes have passed.');
          u.next('Next: readings and water', drift().ok);
        },
        ok: function () { return drift().ok; },
        auto: function () { for (var i = 0; i < 80 && !drift().ok; i++) K.step(sim, p, 300); updateDevices(); return Promise.resolve(); } },
      { id: 'readings', title: 'Readings', view: 'bal', render: function (u) {
          u.h2('Take a set of readings');
          u.task('1. Read the four thermometers', !!st.read, st.read ? 'θ1 ' + st.read.th1.toFixed(1) + ', θ2 ' + st.read.th2.toFixed(1) + ', in ' + st.read.Tin.toFixed(1) + ', out ' + st.read.Tout.toFixed(1) : 'Read to 0.1 °C')
            .add(u.button(st.read ? 'Read again' : 'Read the thermometers', readAll, !st.read, S.hand.busy));
          u.task('2. Collect water for the stopwatch time', st.mass !== null, st.collecting ? 'Collecting…' : st.mass !== null ? st.mass + ' g in ' + st.tcol + ' s' : 'Put the beaker under the spout and start the stopwatch')
            .add(u.row(u.button(st.collecting ? 'Collecting' : 'Start collecting', function () { startCollect(); }, !st.collecting && st.mass === null, st.collecting || S.hand.busy),
              u.button('Stop and weigh', function () { stopCollect(); }, st.collecting, !st.collecting || S.hand.busy)));
          var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
          [1, 30, 120].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
          u.live(function () { return st.collecting ? 'Collecting for ' + Math.round(sim.t - st.tc0) + ' s' : 'Stopwatch ' + watch.t.toFixed(0) + ' s'; });
          u.row(u.button('Write in the table', record, true, !st.read || st.mass === null));
          u.h3('Observation table'); u.table();
          u.next('Next: work out K', S.rows.length >= 2);
          if (S.rows.length < 2) u.p(S.rows.length + ' row(s) so far. Take at least 2 sets; collect for 5 minutes each time (300 s).');
        },
        ok: function () { return S.rows.length >= 2; },
        auto: function () {
          function one() { readAll(); return startCollect().then(function () { K.step(sim, p, 300); updateDevices(); watch.t = 300; return stopCollect(); }).then(function () { record(); }); }
          return one().then(one); } },
    ],

    tick: function (dt) {
      if (running()) { var d = dt * st.speed; K.step(sim, p, d); if (watch.on) watch.t += d; }
      else if (watch.on) watch.t += dt;
      if (watch.on && st.collecting) watch.t = sim.t - st.tc0;
      updateDevices();
      var steam = st.boiler ? Math.min(1, sim.t / 120 + 0.2) : 0, now = (S._steamT = (S._steamT || 0) + dt);
      wisps.forEach(function (w) { var ph = (now * 0.3 + w.userData.ph) % 1; w.position.set(BX + Math.sin(ph * 6 + w.userData.ph * 9) * 0.01, 0.27 + ph * 0.12, BZ);
        w.quaternion.copy(S.camera.quaternion); w.scale.setScalar(0.6 + ph * 1.4); w.material.opacity = steam * 0.3 * Math.sin(ph * Math.PI); });
      jet.visible = st.collecting; jet.scale.y = 0.06; jet.position.set(spoutPos.x, 0.092, spoutPos.z);
      var v = nowV(); hudA.set(r1(v.th1).toFixed(1) + ' °C'); hudB.set(r1(v.th2).toFixed(1) + ' °C'); hudC.set(r1(v.Tout).toFixed(1) + ' °C'); hudD.set(Math.floor(sim.t / 60) + ' min');
    },
  };
});
