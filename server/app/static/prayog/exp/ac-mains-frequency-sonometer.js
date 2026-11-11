/* Prayogshala studio rig `ac-mains-frequency-sonometer`: the frequency of the AC mains with a sonometer (NCERT Class XII
   laboratory manual, permanent-magnet method). A non-magnetic wire on a sonometer carries the small alternating current of
   the 6 V secondary of a step-down transformer, through a rheostat, between the poles of a horse-shoe magnet at its middle.
   The magnetic force alternates at the mains frequency, so the wire is driven like a string: its amplitude peaks when the
   vibrating length l brings its natural frequency to the mains frequency, and f = (1 / 2l) sqrt(T / mu).
   Physics: the lab's own kernel (eng_acsono in packs/engine_ug.js: the driving current from the AC phasor solution, the
   driven damped string). The hidden knob fm (the mains frequency) is what the student finds. Nothing is at mains voltage. */
HoolaStudio.define('ac-mains-frequency-sonometer', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign, K = HK.K.eng_acsono;
  function labParams() {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor('eng_acsono', o);
  }
  var p = labParams();
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var WIRE_R = Math.max(0.0004, Math.min(0.0012, Math.sqrt(p.mu / (8960 * Math.PI)) ));
  var LMIN = 0.2, LMAX = 0.85, HANGER = 0.2, DISC = 0.1, NDISC = 9;
  var st = { l: 0.5, lSet: 50, n: Math.max(0, Math.round((p.M - HANGER) / DISC)), on: false, key: false, checked: false, amp: 0, clock: 0 };
  function mass() { return HANGER + DISC * st.n; }
  function sync() { p.l = st.l; p.M = mass(); p.Rh = st.Rh; return p; }
  st.Rh = Math.max(3, p.Rh);
  function ampNow() { sync(); return st.on && st.key ? K.view(null, p).amp : 0; }
  function currentRms() { sync(); return st.on && st.key ? K.view(null, p).I / Math.SQRT2 : 0; }
  function ampAt(l, M) { var q = assign(p, { l: l, M: M === undefined ? mass() : M, Rh: st.Rh }); return K.view(null, q).amp; }
  function fmt(v, d) { return (isFinite(v) ? v : 0).toFixed(d); }

  // ---------- the sonometer: hollow box on two wooden risers, bridges, wire, pulley, hanger
  var BX0 = -0.6, BX1 = 0.4, BZ = -0.28, RISER = 0.2, BOXH = 0.07, YTOP = RISER + BOXH, BRH = 0.022, WY = YTOP + BRH, AX = -0.5;
  var sono = new T.Group(); S.scene.add(sono);
  [-0.45, 0.25].forEach(function (x) { var r = S.rounded(0.12, RISER, 0.15, 0.006, M.darkWood); r.position.set(x, RISER / 2, BZ); sono.add(r); S.contact(0.2, 0.22, x, BZ, 0.55); });
  var box = S.rounded(BX1 - BX0, BOXH, 0.13, 0.006, M.wood); box.position.set((BX0 + BX1) / 2, RISER + BOXH / 2, BZ); sono.add(box);
  [-0.3, 0.1].forEach(function (x) { var hole = new T.Mesh(new T.CircleGeometry(0.017, 32), new T.MeshStandardMaterial({ color: 0x120c06, roughness: 1 })); hole.position.set(x, RISER + BOXH / 2, BZ + 0.0652); sono.add(hole); });
  var nm = S.label('SONOMETER', { w: 0.12, ratio: 0.16, color: '#5a3b16', weight: 700 }); nm.position.set(-0.1, RISER + BOXH / 2, BZ + 0.0653); sono.add(nm);
  var pin = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.014, 16), M.brass); pin.position.set(BX0 + 0.02, YTOP + 0.007, BZ); sono.add(pin);
  function bridge(x, mat) { var g = new T.Group(); var pr = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.1, 3), mat); pr.rotation.x = -Math.PI / 2; pr.position.y = BRH - 0.003 - 0.012; g.add(pr);
    var edge = S.mesh(new T.BoxGeometry(0.0016, 0.004, 0.1), M.steel); edge.position.y = BRH - 0.002; g.add(edge); var sole = S.mesh(new T.BoxGeometry(0.022, 0.004, 0.1), mat); sole.position.y = 0.002; g.add(sole);
    g.position.set(x, YTOP, BZ); sono.add(g); return g; }
  var brA = bridge(AX, M.darkWood), brB = bridge(AX + st.l, M.darkWood);
  var idx = S.mesh(new T.BoxGeometry(0.0015, 0.0012, 0.03), M.red); idx.position.set(0, 0.0006, 0.05); brB.add(idx);
  var outer = new T.Group(); sono.add(outer); var rul = S.ruler(0.86, { title: 'METRE SCALE · cm', labelEvery: 10, width: 0.026, thick: 0.003 }); outer.add(rul);
  rul.rotation.z = Math.PI / 2; outer.rotation.x = -Math.PI / 2; outer.position.set(AX + 0.86, YTOP + 0.0016, BZ + 0.048);
  var PX = BX1 + 0.025, PR = 0.02;
  var bracket = S.mesh(new T.BoxGeometry(0.03, 0.05, 0.012), M.iron); bracket.position.set(BX1 + 0.012, WY - PR, BZ - 0.014); sono.add(bracket);
  var pulley = S.mesh(new T.CylinderGeometry(PR, PR, 0.008, 40), M.brass); pulley.rotation.x = Math.PI / 2; pulley.position.set(PX, WY - PR, BZ); sono.add(pulley);
  var wireM = new T.MeshStandardMaterial({ color: 0xd98a5e, roughness: 0.25, metalness: 0.9, emissive: 0x2a1408 });
  var up = new T.Vector3(0, 1, 0);
  function seg(mesh, a, b) { var d = b.clone().sub(a), L = d.length(); mesh.position.copy(a).add(b).multiplyScalar(0.5); mesh.scale.set(1, Math.max(1e-4, L), 1); mesh.quaternion.setFromUnitVectors(up, d.normalize()); }
  function wire() { var m = S.mesh(new T.CylinderGeometry(WIRE_R, WIRE_R, 1, 8), wireM, true, false); S.scene.add(m); return m; }
  var w0 = wire(), w2 = wire(), w3 = wire();
  var NSEG = 40, vib = new T.Mesh(new T.BufferGeometry(), wireM); vib.castShadow = false; S.scene.add(vib);
  var blurTex = S.canvasTex(256, 64, function (x, w, h) { x.clearRect(0, 0, w, h); var g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, 'rgba(220,160,110,0)'); g.addColorStop(0.5, 'rgba(235,170,120,.9)'); g.addColorStop(1, 'rgba(220,160,110,0)');
    x.fillStyle = g; x.beginPath(); x.moveTo(0, h / 2); for (var i = 0; i <= 64; i++) { var u = i / 64; x.lineTo(u * w, h / 2 - Math.sin(Math.PI * u) * h / 2); } for (i = 64; i >= 0; i--) { u = i / 64; x.lineTo(u * w, h / 2 + Math.sin(Math.PI * u) * h / 2); } x.fill(); });
  var blur = new T.Mesh(new T.PlaneGeometry(1, 1), new T.MeshBasicMaterial({ map: blurTex, transparent: true, opacity: 0, depthWrite: false, side: T.DoubleSide })); S.scene.add(blur);
  // the horse-shoe magnet at the middle of the wire: its poles are on either side of the wire
  var mag = new T.Group(); S.scene.add(mag);
  var magM = new T.MeshStandardMaterial({ color: 0xb02a22, roughness: 0.4, metalness: 0.4 });
  var arcM = S.mesh(new T.TorusGeometry(0.02, 0.0075, 14, 32, Math.PI), magM); arcM.position.y = 0.045; mag.add(arcM);
  [-1, 1].forEach(function (sg) { var limb = S.mesh(new T.CylinderGeometry(0.0075, 0.0075, 0.035, 16), magM); limb.position.set(sg * 0.02, 0.0275, 0); mag.add(limb);
    var tip = S.mesh(new T.CylinderGeometry(0.0075, 0.0075, 0.016, 16), new T.MeshStandardMaterial({ color: 0xd9dde2, roughness: 0.3, metalness: 0.9 })); tip.position.set(sg * 0.02, 0.008, 0); mag.add(tip); });
  mag.rotation.y = Math.PI / 2;                                   // the poles on either side of the wire (in z)
  // hanger with slotted masses
  var HX = PX + PR, HOOKY = 0.245, HB = 0.066;
  var hanger = new T.Group(); hanger.position.set(HX, 0, BZ); S.scene.add(hanger);
  var hook = S.mesh(new T.TorusGeometry(0.006, 0.0012, 8, 20, Math.PI * 1.6), M.steel); hook.position.y = HOOKY; hanger.add(hook);
  var hrod = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, HOOKY - HB, 14), M.steel); hrod.position.y = HB + (HOOKY - HB) / 2 - 0.006; hanger.add(hrod);
  var hbase = S.mesh(new T.CylinderGeometry(0.035, 0.035, 0.008, 36), M.iron); hbase.position.y = HB; hanger.add(hbase);
  var hl = S.label('0.2 kg', { w: 0.03, ratio: 0.3, color: '#d9dde0' }); hl.position.set(0, HB, 0.0352); hanger.add(hl);
  S.contact(0.1, 0.1, HX, BZ, 0.4);
  var DISC_H = 0.0066, DR = 0.035, discM = new T.MeshStandardMaterial({ color: 0x4a5560, roughness: 0.45, metalness: 0.6 });
  function makeDisc() { var g = new T.Group(); var d = S.mesh(new T.CylinderGeometry(DR, DR, DISC_H - 0.0004, 40), discM); g.add(d);
    var slot = S.mesh(new T.BoxGeometry(0.009, DISC_H, DR + 0.002), new T.MeshStandardMaterial({ color: 0x15181b, roughness: 0.9 })); slot.position.z = DR / 2; g.add(slot);
    var lb = S.label('0.1 kg', { w: 0.02, ratio: 0.3, color: '#e9ecef' }); lb.rotation.x = -Math.PI / 2; lb.position.set(-0.016, DISC_H / 2 + 0.0002, 0); g.add(lb); S.scene.add(g); return g; }
  var discs = []; for (var i = 0; i < NDISC; i++) discs.push(makeDisc());
  var SPX = 0.62, SPZ = -0.3; S.contact(0.12, 0.12, SPX, SPZ, 0.45);
  function layDiscs() { for (var k = 0; k < NDISC; k++) discs[k].position.set(k < st.n ? HX : SPX, k < st.n ? HB + 0.004 + k * DISC_H + DISC_H / 2 : (NDISC - 1 - k) * DISC_H + DISC_H / 2, k < st.n ? BZ : SPZ) }
  layDiscs();
  // ---------- electrical: transformer, plug key, rheostat, AC ammeter
  var tx = new T.Group(); S.scene.add(tx); tx.position.set(-0.55, 0, 0.1);
  var txb = S.rounded(0.15, 0.11, 0.1, 0.008, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 })); txb.rotation.x = -Math.PI / 2; txb.position.y = 0.05; tx.add(txb);
  var lam = S.mesh(new T.BoxGeometry(0.15, 0.012, 0.11), M.iron); lam.position.y = 0.106; tx.add(lam);
  var txl = S.label('STEP-DOWN TRANSFORMER', { w: 0.12, ratio: 0.11, color: '#e8e2cf', weight: 700 }); txl.position.set(0, 0.075, 0.0555); tx.add(txl);
  var txl2 = S.label('230 V in  ·  6 V out', { w: 0.12, ratio: 0.1, color: '#b9bec6' }); txl2.position.set(0, 0.058, 0.0555); tx.add(txl2);
  var rocker = S.rounded(0.02, 0.014, 0.01, 0.003, M.bakelite); rocker.position.set(-0.04, 0.035, 0.058); tx.add(rocker);
  var pilotM = new T.MeshStandardMaterial({ color: 0x14401c, roughness: 0.3 });
  var pilot = S.mesh(new T.SphereGeometry(0.0045, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), pilotM); pilot.position.set(-0.01, 0.044, 0.056); pilot.rotation.x = Math.PI / 2; tx.add(pilot);
  var t1 = S.terminal([0, 0, 0], 'red'), t2 = S.terminal([0, 0, 0], 'black'); [t1, t2].forEach(function (t, i) { t.position.set(-0.55 + 0.03 + i * 0.022, 0.033, 0.1 + 0.058); t.rotation.x = Math.PI / 2; });
  S.contact(0.22, 0.17, -0.55, 0.1, 0.5);
  function setPilot() { pilotM.color.setHex(st.on ? 0x3ae05a : 0x14401c); pilotM.emissive.setHex(st.on ? 0x2ad04a : 0x000000); pilotM.emissiveIntensity = st.on ? 2 : 0; rocker.rotation.x = st.on ? -0.25 : 0.25; }
  setPilot();
  var plug = S.plugKey([-0.34, 0, 0.16]);
  var rheo = S.rheostat([-0.1, 0, 0.18], 0.24); rheo.setFraction((st.Rh - 3) / 17);
  var amm = S.meter({ min: 0, max: 2, unit: 'A', symbol: 'A~', caption: 'AC AMMETER (rms)', pos: [0.2, 0, 0.14], ticks: 10 });
  S.wire([[-0.55 + 0.03, 0.04, 0.16], [-0.45, 0.03, 0.18], [-0.36, 0.03, 0.16]], 'red');
  S.wire([[-0.32, 0.03, 0.16], [-0.2, 0.06, 0.2], [-0.2, 0.065, 0.18]], 'red');
  S.wire([[0.0, 0.065, 0.18], [0.1, 0.06, 0.2], [0.2 + 0.035, 0.07, 0.11]], 'yellow');
  S.wire([[0.2 - 0.035, 0.07, 0.11], [0.0, 0.2, -0.1], [BX0 + 0.02, YTOP + 0.012, BZ + 0.0]], 'yellow');
  S.wire([[PX, WY + 0.004, BZ + 0.0], [PX + 0.05, 0.22, -0.05], [-0.55 + 0.052, 0.04, 0.16]], 'black');

  S.addApparatus('sono', box, 'Sonometer', 'A hollow wooden box with a fixed bridge and a movable bridge. The scale reads the vibrating length l from the fixed bridge.');
  S.addApparatus('brB', brB, 'Movable bridge', 'Slide it to change the vibrating length l of the wire.');
  S.addApparatus('wire', vib, 'Copper wire', (SAMPLE ? SAMPLE + '. ' : '') + 'It carries the small alternating current. Its mass per unit length μ = ' + (+(p.mu * 1000).toFixed(3)) + ' g/m is printed on the reel. It runs over the pulley to the hanger. Its vibration is drawn three times larger than it really is.');
  S.addApparatus('mag', mag, 'Horse-shoe magnet', 'Its poles are on either side of the wire at the middle. A current in the wire feels a force at right angles to the wire and to the field, and this force alternates with the current.');
  S.addApparatus('hanger', hanger, 'Hanger with slotted masses', 'Hanger 0.2 kg plus 0.1 kg slotted masses. Tension T = Mg.');
  S.addApparatus('tx', tx, 'Step-down transformer', 'Mains in, 6 V out. Only this low-voltage secondary is joined to the wire, never the mains.');
  S.addApparatus('rheo', rheo, 'Rheostat', 'It limits the current in the wire, which would otherwise get hot.');
  S.addApparatus('amm', amm, 'AC ammeter', 'It reads the current through the wire (rms).');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudL = S.hudCard('Length l'), hudM = S.hudCard('Load M'), hudA = S.hudCard('Amplitude at the middle');

  // ---------- geometry updates
  var vt = 0;
  function layWire() {
    var a = new T.Vector3(BX0 + 0.02, YTOP + 0.012, BZ), A = new T.Vector3(AX, WY, BZ), B = new T.Vector3(AX + st.l, WY, BZ), P = new T.Vector3(PX, WY + 0.0006, BZ), Pd = new T.Vector3(HX, WY - PR, BZ), H = new T.Vector3(HX, HOOKY + 0.006, BZ);
    seg(w0, a, A); seg(w2, B, P); seg(w3, Pd, H);
    brB.position.x = AX + st.l; blur.position.set(AX + st.l / 2, WY, BZ); blur.scale.x = st.l;
    mag.position.set(AX + st.l / 2, WY - 0.008, BZ);
  }
  function vibrate(amp, ph) {
    var pts = [], i, x, y;
    for (i = 0; i <= NSEG; i++) { x = i / NSEG; y = amp * Math.sin(Math.PI * x) * ph; pts.push(new T.Vector3(AX + x * st.l, WY + y, BZ)); }
    vib.geometry.dispose(); vib.geometry = new T.TubeGeometry(new T.CatmullRomCurve3(pts), 40, WIRE_R, 8, false);
  }
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function moveBridge(toCm) {
    if (S.hand.busy) return wait();
    var target = Math.round(toCm * 10) / 1000;                    // least count 1 mm
    if (!(target >= LMIN - 1e-9 && target <= LMAX + 1e-9)) { S.say('Keep the length between ' + LMIN * 100 + ' and ' + LMAX * 100 + ' cm.'); return Promise.resolve(false); }
    var l0 = st.l; if (Math.abs(target - l0) < 0.0004) return Promise.resolve(true);
    var at = function (l) { return new T.Vector3(AX + l + 0.004, YTOP + 0.016, BZ + 0.04); }, lk = function (k) { return l0 + (target - l0) * k; };
    return S.hand.pinchMove(at(l0), function (k) { return at(lk(k)); }, function (k) { st.l = lk(k); layWire(); }, { ms: 500 + Math.abs(target - l0) * 2000 }).then(function () { st.l = target; st.lSet = target * 100; layWire(); S.render(); return true; });
  }
  function addMass(dir) {
    if (S.hand.busy) return wait();
    if (dir > 0 && st.n >= NDISC) { S.say('All the slotted masses are on: ' + (HANGER + DISC * NDISC).toFixed(1) + ' kg is the most this wire should carry.'); return Promise.resolve(false); }
    if (dir < 0 && st.n <= 1) { S.say('Keep at least 0.3 kg on the hanger, or the wire is too slack.'); return Promise.resolve(false); }
    return S.hand.tap(hbase, 'top').then(function () { st.n += dir; layDiscs(); S.say('Load now ' + mass().toFixed(1) + ' kg, T = ' + (mass() * p.g).toFixed(1) + ' N.'); S.render(); return true; });
  }
  function loadTo(M) { var n = Math.round((M - HANGER) / DISC), seq = Promise.resolve(), k; var steps = n - st.n; for (k = 0; k < Math.abs(steps); k++) seq = seq.then(function () { return addMass(steps > 0 ? 1 : -1); }); return seq; }
  function powerOn() {
    if (S.hand.busy) return wait();
    if (st.on && st.key) return Promise.resolve(true);
    return S.hand.tap(rocker, 'front').then(function () { st.on = true; setPilot(); S.click(900, 0.05); return S.hand.tap(plug.userData.plug, 'top'); }).then(function () {
      st.key = true; plug.set(true); S.say('The transformer is on and the key is in: a current of ' + fmt(currentRms(), 2) + ' A flows in the wire.'); S.render(); return true; });
  }
  function setRh(v) { if (S.hand.busy) return wait(); st.Rh = Math.max(3, Math.min(20, v)); rheo.setFraction((st.Rh - 3) / 17); S.render(); return Promise.resolve(true); }
  function isPeak() {                                              // the amplitude is largest here, within the bridge's 1 mm least count
    var l = st.l, a = ampAt(l), a1 = ampAt(l - 0.002), a2 = ampAt(l + 0.002);
    return a >= a1 && a >= a2 && a > 0.0004;
  }
  function note() {
    if (S.hand.busy) { wait(); return false; }
    if (!(st.on && st.key)) { S.say('Switch the transformer on and put the key in first.'); return false; }
    if (!isPeak()) { S.say('The wire is not at its largest amplitude here. Move the bridge a millimetre or two each way and watch the middle of the wire.'); return false; }
    var M = Math.round(mass() * 100) / 100;
    if (S.rows.some(function (r) { return Math.abs(r.M - M) < 1e-6; })) { S.say('You already have a reading with this load. Change the load.'); return false; }
    S.addRow({ l: Math.round(st.l * 1000) / 1000, M: M }); S.say('Written: l = ' + fmt(st.l * 100, 1) + ' cm with a load of ' + fmt(M, 1) + ' kg.'); return true;
  }
  function findRes() {                                             // what a careful student converges to: coarse then fine steps
    var best = LMIN, bv = -1, l, v;
    for (l = LMIN; l <= LMAX + 1e-9; l += 0.005) { v = ampAt(l); if (v > bv) { bv = v; best = l; } }
    var c = best; bv = -1; for (l = c - 0.006; l <= c + 0.006 + 1e-9; l += 0.001) { v = ampAt(Math.round(l * 1000) / 1000); if (v > bv) { bv = v; best = Math.round(l * 1000) / 1000; } }
    return best * 100;
  }
  function fOf(r) { return Math.sqrt(r.M * p.g / p.mu) / (2 * r.l); }

  layWire(); vibrate(0, 0);
  var VIEWS = { sono: [[-0.05, 0.5, 0.55], [-0.1, 0.2, BZ]], brB: [[AX + 0.38, 0.37, 0.06], [AX + 0.3, YTOP, BZ]], wire: [[-0.1, 0.48, 0.35], [-0.2, WY, BZ]], mag: [[-0.2, 0.42, 0.1], [AX + 0.25, WY, BZ]],
    hanger: [[0.72, 0.3, 0.25], [HX, 0.12, BZ]], tx: [[-0.4, 0.26, 0.4], [-0.55, 0.05, 0.1]], rheo: [[-0.1, 0.22, 0.45], [-0.1, 0.04, 0.18]], amm: [[0.2, 0.22, 0.4], [0.2, 0.05, 0.14]], work: [[0.02, 0.78, 0.82], [-0.1, 0.24, -0.28]],
    book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] };
  VIEWS.bench = [[0.4, 0.85, 1.45], [0.0, 0.13, -0.05]];

  return {
    camera: { pos: [0.4, 0.85, 1.45], look: [0.0, 0.13, -0.05] },
    views: VIEWS,
    theory: { principle: 'The current in the wire alternates at the mains frequency, so the force B I w from the horse-shoe magnet alternates too, and pushes the wire up and down f times a second. The wire is a stretched string with natural frequency f1 = (1 / 2l) √(T / μ). It responds most when f1 equals the mains frequency.',
      formula: 'f = (1 / 2l) √(T / μ)', formulaNote: 'T = M g, the weight on the hanger · l = resonant length · μ = mass per unit length of the wire',
      more: ['The wire must be non-magnetic (copper, brass): an iron wire would be pulled by the magnet once in every half cycle whichever way the current flows, and the pull would come twice per cycle. A larger load needs a longer length to resonate.'],
      precautions: 'Use only the low-voltage secondary of the step-down transformer and keep the rheostat in the circuit: a short length of copper wire gets hot. Never connect the wire to the mains. Place the magnet at the middle of the vibrating length. Move the bridge in small steps near resonance.' },
    book: { title: 'Expt. — Frequency of the AC mains', lines: ['Aim: to find the frequency of the AC mains with a sonometer.'].concat(SAMPLE ? [SAMPLE] : []).concat(['μ = ' + fmt(p.mu * 1000, 3) + ' g/m (printed on the reel), g = ' + p.g, 'f = (1 / 2l) √(M g / μ)', 'Current limited by the rheostat']),
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'M (kg)', get: function (r) { return r.M.toFixed(1); } }, { label: 'l (cm)', get: function (r) { return (r.l * 100).toFixed(1); } },
        { label: 'T (N)', get: function (r) { return (r.M * p.g).toFixed(2); } }, { label: 'f (Hz)', get: function (r) { return fOf(r).toFixed(2); } }] },
    graph: null,
    result: function (rows) { if ((rows || []).length < 3) return null; var m = S.fit.mean(rows.map(fOf));
      return { label: 'f of the mains', value: m, unit: 'Hz', digits: 2, truth: p.fm, note: 'Mean of (1 / 2l) √(M g / μ) over ' + rows.length + ' loads.' }; },
    tol: 0.02,
    chips: ['Why does the wire vibrate at the mains frequency?', 'Why must the wire be non-magnetic?', 'Why does a larger load need a longer length?', 'Check my readings'],
    viva: [['At resonance the wire vibrates', ['with the largest amplitude', 'not at all', 'with the smallest amplitude'], 0, 'The natural frequency of the wire equals the driving frequency.'],
      ['If the load M is increased the resonant length', ['increases', 'decreases', 'stays the same'], 0, 'l is proportional to √T: a tighter wire needs a longer length to keep the same frequency.']],
    askState: function () { sync(); var v = K.view(null, p); return { transformer_on: st.on, key_in: st.key, load_kg: +mass().toFixed(2), tension_N: +(mass() * p.g).toFixed(2), length_cm: +fmt(st.l * 100, 1), rheostat_ohm: +fmt(st.Rh, 1), current_A_rms: +fmt(currentRms(), 2),
      amplitude_mm: +fmt(ampNow() * 1000, 2), wire_natural_frequency_Hz: +fmt(v.fn, 2), readings_recorded: S.rows.length }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'work', render: function (u) {
          u.h2('Check the circuit and switch on');
          u.p('The wire is joined, through the key, the rheostat and the AC ammeter, to the 6 V secondary of the step-down transformer. The horse-shoe magnet straddles the wire at its middle.');
          u.task('1. Check the connections', st.checked, st.checked ? 'Wire, rheostat, ammeter and key in series' : 'Look over the circuit').add(u.button(st.checked ? 'Checked' : 'Check the circuit', function () { st.checked = true; S.focus('tx'); S.say('The key, rheostat and ammeter are in series with the wire, and the magnet is at its middle.'); S.render(); }, !st.checked, st.checked));
          u.task('2. Switch on and insert the key', st.on && st.key, st.on && st.key ? 'Current ' + fmt(currentRms(), 2) + ' A' : 'The hand presses the rocker, then inserts the plug').add(u.button(st.on ? 'Switched on' : 'Switch on', function () { S.focus('tx'); powerOn(); }, !(st.on && st.key), S.hand.busy || (st.on && st.key)));
          u.note('Use only the low-voltage secondary. Never connect the wire or the coil of the transformer to the mains. Keep the rheostat at 3 ohm or more so the wire stays cool.');
          u.next('Next: find resonance', st.checked && st.on && st.key);
        },
        ok: function () { return st.checked && st.on && st.key; }, auto: function () { st.checked = true; return powerOn(); } },
      { id: 'res', title: 'Resonant lengths', view: 'work', render: function (u) {
          u.h2('Find the length of largest amplitude for three loads');
          u.p('Slide the bridge a little at a time while you watch the middle of the wire: its amplitude is largest at resonance. Note l. Then change the load and find the new resonant length. Take at least 3 loads.');
          u.row(u.button('Load − 0.1 kg', function () { addMass(-1); }, false, S.hand.busy), u.button('Load + 0.1 kg', function () { addMass(1); }, false, S.hand.busy), u.button('Look at the hanger', function () { S.focus('hanger'); }));
          u.slider('Length l', LMIN * 100, LMAX * 100, 0.1, function () { return st.lSet; }, function (x) { st.lSet = x; }, 'cm', 1);
          u.row(u.button('Slide the bridge there', function () { moveBridge(st.lSet).then(function () { S.render(); }); }, true, S.hand.busy));
          function nudge(d) { return function () { var to = Math.round((st.l * 100 + d) * 10) / 10; st.lSet = to; moveBridge(to).then(function () { S.render(); }); }; }
          u.row(u.button('− 1 cm', nudge(-1), false, S.hand.busy), u.button('− 1 mm', nudge(-0.1), false, S.hand.busy), u.button('+ 1 mm', nudge(0.1), false, S.hand.busy), u.button('+ 1 cm', nudge(1), false, S.hand.busy));
          u.task('Rheostat', true, 'Set at ' + fmt(st.Rh, 1) + ' ohm → current ' + fmt(currentRms(), 2) + ' A').add(u.slider('Rheostat', 3, 20, 0.5, function () { return st.Rh; }, function (x) { setRh(x); }, 'ohm', 1));
          u.live(function () { return 'l = ' + fmt(st.l * 100, 1) + ' cm   M = ' + fmt(mass(), 1) + ' kg   amplitude at the middle ' + fmt(ampNow() * 1000, 2) + ' mm'; });
          u.row(u.button('Note l (largest amplitude)', function () { note(); S.render(); }, true, S.hand.busy), u.button('Look at the wire', function () { S.focus('wire'); }));
          u.h3('Observation table'); u.table();
          u.next('Next: result', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 loads recorded.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          var loads = [0.3, 0.5, 0.7], seq = Promise.resolve();
          loads.forEach(function (Ld) { seq = seq.then(function () { return loadTo(Ld); }).then(function () { return moveBridge(findRes()); }).then(function () { note(); }); });
          return seq;
        } },
    ],
    tick: function (dt) {
      sync(); vt += dt || 0.016; var a = ampNow();
      vibrate(a * 3, Math.sin(vt * 40));
      blur.material.opacity = Math.min(0.85, a * 120); blur.scale.y = Math.max(0.002, a * 6 + 0.002);
      amm.set(currentRms());
      hudL.set(fmt(st.l * 100, 1) + ' cm'); hudM.set(fmt(mass(), 1) + ' kg'); hudA.set(st.on && st.key ? fmt(a * 1000, 2) + ' mm' : 'no current');
    },
  };
});
