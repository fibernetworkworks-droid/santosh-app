/* Prayogshala studio module: Sonometer - frequency of a stretched wire (NCERT Class XI).
   Physics: the sonometer kernel from kernels.js (the wire's fundamental f = (1/2l)√(T/μ) and its response to the fork)
   - the same numbers the server checks. The hidden knob μ (mass per unit length of the wire) is what the student finds. */
HoolaStudio.define('sonometer', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.sonometer;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('sonometer');
  var G = 9.8, DISC = 0.5, HANGER = 0.5, NDISC = 11, LMIN = 0.1, LMAX = 0.85, FORKS = [256, 320, 384, 512];
  var st = { l: Math.round(p.l * 1000) / 1000, target: 30, n: 5, fork: 256, amp: 0, touching: false, rider: 'on', riderT: 0, lastLoud: null, heardAt: null, sound: true, clock: 0 };
  function mass() { return HANGER + DISC * st.n; }
  function sync() { p.l = st.l; p.f = st.fork; p.Tn = mass() * G; return p; }
  function loudNow() { sync(); return K.view({ t: 0 }, p).loud; }

  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'grip', 300); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }
  var up = new T.Vector3(0, 1, 0);
  function seg(mesh, a, b) { var d = b.clone().sub(a), L = d.length(); mesh.position.copy(a).add(b).multiplyScalar(0.5); mesh.scale.set(1, Math.max(1e-4, L), 1); mesh.quaternion.setFromUnitVectors(up, d.normalize()); }

  // ---------- the sonometer: hollow box on two wooden risers, bridges, wire, pulley, hanger
  var BX0 = -0.6, BX1 = 0.4, BZ = -0.28, RISER = 0.2, BOXH = 0.07, YTOP = RISER + BOXH, BRH = 0.022, WY = YTOP + BRH, AX = -0.5;
  var sono = new T.Group(); S.scene.add(sono);
  [-0.45, 0.25].forEach(function (x) { var r = S.rounded(0.12, RISER, 0.15, 0.006, M.darkWood); r.position.set(x, RISER / 2, BZ); sono.add(r); S.contact(0.2, 0.22, x, BZ, 0.55); });
  var box = S.rounded(BX1 - BX0, BOXH, 0.13, 0.006, M.wood); box.position.set((BX0 + BX1) / 2, RISER + BOXH / 2, BZ); sono.add(box);
  [-0.3, 0.1].forEach(function (x) { var hole = new T.Mesh(new T.CircleGeometry(0.017, 32), new T.MeshStandardMaterial({ color: 0x120c06, roughness: 1 })); hole.position.set(x, RISER + BOXH / 2, BZ + 0.0652); sono.add(hole); });
  var nm = S.label('SONOMETER', { w: 0.12, ratio: 0.16, color: '#5a3b16', weight: 700 }); nm.position.set(-0.1, RISER + BOXH / 2, BZ + 0.0653); sono.add(nm);
  var pin = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.014, 16), M.brass); pin.position.set(BX0 + 0.02, YTOP + 0.007, BZ); sono.add(pin);
  function bridge(x, mat) { var g = new T.Group(); var pr = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.1, 3), mat); pr.rotation.x = -Math.PI / 2;
      pr.position.y = BRH - 0.003 - 0.012; g.add(pr); var edge = S.mesh(new T.BoxGeometry(0.0016, 0.004, 0.1), M.steel); edge.position.y = BRH - 0.002; g.add(edge);
      var sole = S.mesh(new T.BoxGeometry(0.022, 0.004, 0.1), mat); sole.position.y = 0.002; g.add(sole);
      g.position.set(x, YTOP, BZ); sono.add(g); return g; }
  var brA = bridge(AX, M.darkWood), brB = bridge(AX + st.l, M.darkWood);
  var idx = S.mesh(new T.BoxGeometry(0.0015, 0.0012, 0.03), M.red); idx.position.set(0, 0.0006, 0.05); brB.add(idx);
  var outer = new T.Group(); sono.add(outer); var rul = S.ruler(0.86, { title: 'METRE SCALE · cm', labelEvery: 10, width: 0.026, thick: 0.003 }); outer.add(rul);
  rul.rotation.z = Math.PI / 2; outer.rotation.x = -Math.PI / 2; outer.position.set(AX + 0.865, YTOP + 0.0016, BZ + 0.048);
  var PX = BX1 + 0.025, PR = 0.02;
  var bracket = S.mesh(new T.BoxGeometry(0.03, 0.05, 0.012), M.iron); bracket.position.set(BX1 + 0.012, WY - PR, BZ - 0.014); sono.add(bracket);
  var pulley = S.mesh(new T.CylinderGeometry(PR, PR, 0.008, 40), M.brass); pulley.rotation.x = Math.PI / 2; pulley.position.set(PX, WY - PR, BZ); sono.add(pulley);
  var axle = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.03, 12), M.steel); axle.rotation.x = Math.PI / 2; axle.position.set(PX, WY - PR, BZ - 0.008); sono.add(axle);
  var wireM = new T.MeshStandardMaterial({ color: 0xd9dde0, roughness: 0.25, metalness: 1 });
  function wire() { var m = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 1, 8), wireM, true, false); S.scene.add(m); return m; }
  var w0 = wire(), w1 = wire(), w2 = wire(), w3 = wire();
  var blurTex = S.canvasTex(256, 64, function (x, w, h) { x.clearRect(0, 0, w, h); var g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, 'rgba(220,224,228,0)'); g.addColorStop(0.5, 'rgba(220,224,228,.9)'); g.addColorStop(1, 'rgba(220,224,228,0)');
    x.fillStyle = g; x.beginPath(); x.moveTo(0, h / 2); for (var i = 0; i <= 64; i++) { var u = i / 64; x.lineTo(u * w, h / 2 - Math.sin(Math.PI * u) * h / 2); } for (i = 64; i >= 0; i--) { u = i / 64; x.lineTo(u * w, h / 2 + Math.sin(Math.PI * u) * h / 2); } x.fill(); });
  var blur = new T.Mesh(new T.PlaneGeometry(1, 1), new T.MeshBasicMaterial({ map: blurTex, transparent: true, opacity: 0, depthWrite: false, side: T.DoubleSide })); S.scene.add(blur);
  // hanger with slotted masses
  var HX = PX + PR, HOOKY = 0.245, HB = 0.066;
  var hanger = new T.Group(); hanger.position.set(HX, 0, BZ); S.scene.add(hanger);
  var hook = S.mesh(new T.TorusGeometry(0.006, 0.0012, 8, 20, Math.PI * 1.6), M.steel); hook.position.y = HOOKY; hanger.add(hook);
  var hrod = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, HOOKY - HB, 14), M.steel); hrod.position.y = HB + (HOOKY - HB) / 2 - 0.006; hanger.add(hrod);
  var hbase = S.mesh(new T.CylinderGeometry(0.035, 0.035, 0.008, 36), M.iron); hbase.position.y = HB; hanger.add(hbase);
  var hl = S.label('0.5 kg', { w: 0.03, ratio: 0.3, color: '#d9dde0' }); hl.position.set(0, HB, 0.0352); hanger.add(hl);
  S.contact(0.1, 0.1, HX, BZ, 0.4);
  var DISC_H = 0.0126, DR = 0.04;
  var discM = new T.MeshStandardMaterial({ color: 0x4a5560, roughness: 0.45, metalness: 0.6 });
  function makeDisc() { var g = new T.Group(); var d = S.mesh(new T.CylinderGeometry(DR, DR, DISC_H - 0.0006, 40), discM); g.add(d);
    var slot = S.mesh(new T.BoxGeometry(0.009, DISC_H, DR + 0.002), new T.MeshStandardMaterial({ color: 0x15181b, roughness: 0.9 })); slot.position.z = DR / 2; g.add(slot);
    var lb = S.label('0.5 kg', { w: 0.022, ratio: 0.3, color: '#e9ecef' }); lb.rotation.x = -Math.PI / 2; lb.position.set(-0.018, DISC_H / 2 + 0.0002, 0); g.add(lb); S.scene.add(g); return g; }
  var discs = []; for (var i = 0; i < NDISC; i++) discs.push(makeDisc());
  var SPX = 0.62, SPZ = -0.3;
  S.contact(0.12, 0.12, SPX, SPZ, 0.45);
  function onHangerPos(i) { return new T.Vector3(HX, HB + 0.004 + i * DISC_H + DISC_H / 2, BZ); }
  function sparePos(j) { return new T.Vector3(SPX, j * DISC_H + DISC_H / 2, SPZ); }
  function layDiscs() { for (var k = 0; k < NDISC; k++) discs[k].position.copy(k < st.n ? onHangerPos(k) : sparePos(NDISC - 1 - k)); }
  layDiscs();
  // paper rider
  var paperM = new T.MeshStandardMaterial({ color: 0xf2efe6, roughness: 0.9, side: T.DoubleSide });
  var rider = new T.Group(); S.scene.add(rider);
  [-1, 1].forEach(function (s) { var f = new T.Mesh(new T.PlaneGeometry(0.014, 0.01), paperM); f.position.set(0, -0.0045, s * 0.0022); f.rotation.x = s * 0.45; f.castShadow = true; rider.add(f); });
  var stripe = new T.Mesh(new T.PlaneGeometry(0.014, 0.002), new T.MeshStandardMaterial({ color: 0xc23b30, side: T.DoubleSide })); stripe.position.set(0, -0.001, 0.0012); stripe.rotation.x = 0.45; rider.add(stripe);
  // fork box with four forks, rubber pad
  var FBX = 0.66, FBZ = 0.07;
  var fbox = S.rounded(0.26, 0.17, 0.022, 0.006, M.darkWood); fbox.rotation.x = -Math.PI / 2; fbox.position.set(FBX, 0.011, FBZ); S.scene.add(fbox);
  var felt = S.mesh(new T.BoxGeometry(0.24, 0.002, 0.15), new T.MeshStandardMaterial({ color: 0x4a1220, roughness: 1 })); felt.position.set(FBX, 0.0225, FBZ); S.scene.add(felt);
  S.contact(0.32, 0.22, FBX, FBZ, 0.45);
  var LIE = { x: Math.PI / 2, z: -Math.PI / 2 }, GRIPL = new T.Vector3(0, 0.035, 0);
  var forks = {}, homes = {};
  FORKS.forEach(function (f, i) { var fk = S.tuningFork([0, 0, 0], f); forks[f] = fk; homes[f] = new T.Vector3(FBX - 0.1 + 0.035, 0.0275, FBZ - 0.054 + i * 0.036); placeFork(fk, homes[f], LIE.z, LIE.x); });
  function placeFork(fk, grip, rz, rx) { fk.rotation.set(rx || 0, 0, rz); var off = GRIPL.clone().applyEuler(fk.rotation); fk.position.copy(grip).sub(off); }
  var PADX = 0.9, PADZ = 0.16, PADH = 0.025;
  var pad = S.rounded(0.07, 0.05, PADH, 0.006, M.rubber); pad.rotation.x = -Math.PI / 2; pad.position.set(PADX, PADH / 2, PADZ); S.scene.add(pad);
  S.contact(0.1, 0.08, PADX, PADZ, 0.45);

  S.addApparatus('box', box, 'Hollow sonometer box', 'A hollow wooden box: it makes the wire\'s vibration loud enough to hear and feel.');
  S.addApparatus('brA', brA, 'Fixed knife-edge bridge', 'One end of the vibrating length l. The scale reads zero here.');
  S.addApparatus('brB', brB, 'Movable bridge', 'Slide it to change the vibrating length l between the bridges.');
  S.addApparatus('wire', w1, 'Steel wire', 'Its mass per unit length μ is what you find. It runs over the pulley to the hanger.');
  S.addApparatus('hanger', hanger, 'Hanger with slotted masses', 'Hanger 0.5 kg + 0.5 kg slotted masses. Tension T = Mg.');
  S.addApparatus('rider', rider, 'Paper rider', 'A small folded paper V on the middle of the wire. At resonance it flutters and falls off.');
  S.addApparatus('forks', forks[256], 'Set of tuning forks', '256, 320, 384 and 512 Hz. Strike on the rubber pad only.');
  S.addApparatus('pad', pad, 'Rubber pad', 'Strike the fork on this, never on the bench.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudL = S.hudCard('Length l'), hudT = S.hudCard('Tension T'), hudF = S.hudCard('Fork');

  // ---------- sound
  var au = { ctx: null, osc: null, gain: null };
  function audioWake() { if (S.fast || !st.sound) return; try { var AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
      if (!au.ctx) { au.ctx = new AC(); au.gain = au.ctx.createGain(); au.gain.gain.value = 0; au.gain.connect(au.ctx.destination); }
      if (au.ctx.state === 'suspended') au.ctx.resume();
      if (!au.osc) { au.osc = au.ctx.createOscillator(); au.osc.type = 'triangle'; au.osc.connect(au.gain); au.osc.start(); }
      au.osc.frequency.setValueAtTime(st.fork, au.ctx.currentTime); } catch (e) { /* sound is optional */ } }
  function audioLevel(v) { if (!au.gain) return; try { au.gain.gain.setTargetAtTime(st.sound ? v : 0, au.ctx.currentTime, 0.05); } catch (e) { /* ignore */ } }

  // ---------- geometry updates
  function riderHome() { return new T.Vector3(AX + st.l / 2, WY + 0.0008, BZ); }
  function layWire() {
    var a = new T.Vector3(BX0 + 0.02, YTOP + 0.012, BZ), A = new T.Vector3(AX, WY, BZ), B = new T.Vector3(AX + st.l, WY, BZ), P = new T.Vector3(PX, WY + 0.0006, BZ),
      Pd = new T.Vector3(HX, WY - PR, BZ), H = new T.Vector3(HX, HOOKY + 0.006, BZ);
    seg(w0, a, A); seg(w1, A, B); seg(w2, B, P); seg(w3, Pd, H);
    brB.position.x = AX + st.l; blur.position.set(AX + st.l / 2, WY, BZ); blur.scale.x = st.l;
    if (st.rider === 'on') rider.position.copy(riderHome());
  }
  layWire();
  function moveBridge(target) {
    if (S.hand.busy) return Promise.resolve();
    target = Math.round(target * 1000) / 1000;
    if (!(target >= LMIN && target <= LMAX)) { S.say('Keep the length between ' + LMIN * 100 + ' and ' + LMAX * 100 + ' cm.'); return Promise.resolve(); }
    if (st.rider !== 'on') { S.say('Put the paper rider back on the wire first.'); return Promise.resolve(); }
    var l0 = st.l; if (Math.abs(target - l0) < 0.0005) { S.say('The bridge is already at ' + (target * 100).toFixed(1) + ' cm.'); return Promise.resolve(); }
    var at = function (l) { return new T.Vector3(AX + l + 0.004, YTOP + 0.016, BZ + 0.04); }, lk = function (k) { return l0 + (target - l0) * k; };
    return S.hand.pinchMove(at(l0), function (k) { return at(lk(k)); }, function (k) { st.l = lk(k); layWire(); }, { ms: 600 + Math.abs(target - l0) * 2500 })
      .then(function () { st.l = target; layWire(); st.heardAt = null; S.say('Bridge at l = ' + (target * 100).toFixed(1) + ' cm. Now sound the fork on the box.'); S.render(); });
  }
  function addMass(dir) {
    if (S.hand.busy) return Promise.resolve();
    if (dir > 0 && st.n >= NDISC) { S.say('All the slotted masses are on: 6 kg is the most this wire should carry.'); return Promise.resolve(); }
    if (dir < 0 && st.n <= 3) { S.say('Keep at least 2 kg on the hanger, or the wire is too slack to give a clear note.'); return Promise.resolve(); }
    if (st.rider !== 'on') { S.say('Put the paper rider back on the wire first.'); return Promise.resolve(); }
    var k0 = dir > 0 ? st.n : st.n - 1, disc = discs[k0], from = dir > 0 ? sparePos(NDISC - 1 - st.n) : onHangerPos(k0), to = dir > 0 ? onHangerPos(st.n) : sparePos(NDISC - st.n);
    var side = new T.Vector3(0, 0, DR + 0.03), lift = 0.05, grip = new T.Vector3(DR + 0.004, 0.004, 0);
    var path = dir > 0 ? [from, from.clone().add(new T.Vector3(0, lift, 0)), to.clone().add(side).add(new T.Vector3(0, 0.012, 0)), to.clone().add(new T.Vector3(0, 0.012, 0)), to]
      : [from, from.clone().add(new T.Vector3(0, 0.012, 0)), from.clone().add(side).add(new T.Vector3(0, 0.012, 0)), to.clone().add(new T.Vector3(0, lift, 0)), to];
    var legs = [];
    for (var i = 0; i < path.length - 1; i++) (function (a, b) { legs.push({ ms: 600, fn: function (k) { return a.clone().lerp(b, k).add(grip); }, onK: function (k) { disc.position.copy(a.clone().lerp(b, k)); } }); })(path[i], path[i + 1]);
    return carry(from.clone().add(grip), legs, 'pinch').then(function () { st.n += dir; layDiscs(); st.heardAt = null;
      S.say((dir > 0 ? 'Added' : 'Removed') + ' 0.5 kg. Load now ' + mass().toFixed(1) + ' kg, T = ' + (mass() * G).toFixed(1) + ' N.'); S.render(); });
  }
  function riderBack() {
    if (S.hand.busy || st.rider === 'on') return Promise.resolve();
    var a = rider.position.clone(), b = riderHome();
    return S.hand.pinchMove(a.clone().add(new T.Vector3(0, 0.004, 0)), function (k) { return a.clone().lerp(b, k).add(new T.Vector3(0, 0.004 + Math.sin(Math.PI * k) * 0.03, 0)); },
      function (k) { rider.position.copy(a.clone().lerp(b, k).add(new T.Vector3(0, Math.sin(Math.PI * k) * 0.03, 0))); rider.rotation.set(0, 0, (1 - k) * rider.rotation.z); }, { ms: 900 })
      .then(function () { st.rider = 'on'; rider.rotation.set(0, 0, 0); layWire(); S.render(); });
  }
  function strike() {
    if (S.hand.busy) return Promise.resolve();
    if (st.rider !== 'on') { S.say('Put the paper rider back on the wire first.'); return Promise.resolve(); }
    audioWake();
    var fk = forks[st.fork], g0 = homes[st.fork].clone(), g1 = new T.Vector3(PADX - 0.135, 0.12, PADZ), gs = new T.Vector3(PADX - 0.1346, PADH + 0.0149 + 0.004, PADZ),
      gp = new T.Vector3(AX - 0.05, YTOP + GRIPL.y, BZ + 0.035);
    var L = function (a, b, k) { return a.clone().lerp(b, k); }, arc = function (a, b, k, hh) { return L(a, b, k).add(new T.Vector3(0, Math.sin(Math.PI * k) * hh, 0)); };
    var legs = [
      { ms: 900, fn: function (k) { return arc(g0, g1, k, 0.05); }, onK: function (k) { placeFork(fk, arc(g0, g1, k, 0.05), LIE.z * (1 - k), LIE.x * (1 - k)); } },
      { ms: 260, fn: function (k) { return L(g1, gs, k); }, onK: function (k) { placeFork(fk, L(g1, gs, k), -1.6 * k, 0); if (k >= 1 && st.amp < 0.5) { st.amp = 1; S.click(300, 0.04, 0.08); } } },
      { ms: 1500, fn: function (k) { return arc(gs, gp, k, 0.12); }, onK: function (k) { placeFork(fk, arc(gs, gp, k, 0.12), -1.6 * (1 - k), 0); st.touching = k > 0.97; } },
      { ms: 2600, fn: function () { return gp; }, onK: function () { st.touching = true; } },
      { ms: 1300, fn: function (k) { return arc(gp, g0, k, 0.1); }, onK: function (k) { st.touching = false; placeFork(fk, arc(gp, g0, k, 0.1), LIE.z * k, LIE.x * k); } },
    ];
    st.amp = 0;
    return carry(g0, legs, 'grip').then(function () {
      st.lastLoud = loudNow(); st.heardAt = st.l; st.amp = 0; st.touching = false; placeFork(fk, homes[st.fork], LIE.z, LIE.x);
      if (S.fast && st.lastLoud > 0.8) knockRider();
      S.say(st.rider !== 'on' ? 'Resonance: the rider flew off the wire at l = ' + (st.l * 100).toFixed(1) + ' cm.' : st.lastLoud > 0.3 ? 'The rider trembled hard: you are very close. Move the bridge by a millimetre or two.' : st.lastLoud > 0.08 ? 'The rider quivered a little.' : 'The rider stayed still.');
      S.render(); });
  }
  function knockRider() { if (st.rider !== 'on') return; st.rider = 'flying'; st.riderT = 0; st.riderFrom = rider.position.clone(); }
  function record() {
    if (S.hand.busy) return;
    if (st.rider === 'on' || st.heardAt === null || Math.abs(st.heardAt - st.l) > 1e-6) { S.say('Record only when the rider has fallen off at this bridge position.'); return; }
    if (S.rows.some(function (r) { return r.f === st.fork && Math.abs(r.M - mass()) < 1e-9; })) { S.say('You already have this fork at this tension. Change the fork or the load.'); return; }
    var row = { f: st.fork, l: Math.round(st.l * 1000) / 1000, M: mass(), Tn: mass() * G };
    S.addRow(row); S.say('Written: f = ' + row.f + ' Hz, l = ' + (row.l * 100).toFixed(1) + ' cm, T = ' + row.Tn.toFixed(1) + ' N.');
  }
  function muOf(r) { return r.Tn / (4 * r.l * r.l * r.f * r.f); }
  function scan(lo, hi, step) {
    var best = { l: lo, v: -1 }, ls = []; for (var x = lo; x <= hi + 1e-9; x += step) ls.push(Math.round(x * 1000) / 1000);
    return ls.reduce(function (pr, l) { return pr.then(function () { return riderBack().then(function () { return moveBridge(l); }).then(strike).then(function () { if (st.lastLoud > best.v) best = { l: l, v: st.lastLoud }; }); }); }, Promise.resolve())
      .then(function () { return best.l; });
  }
  function findRes(guess) { return scan(Math.max(LMIN, guess - 0.04), Math.min(LMAX, guess + 0.04), 0.01)
    .then(function (c) { return scan(Math.max(LMIN, c - 0.009), Math.min(LMAX, c + 0.009), 0.001); })
    .then(function (b) { return riderBack().then(function () { return moveBridge(b); }).then(strike); }); }

  return {
    camera: { pos: [0.4, 0.85, 1.45], look: [0.12, 0.13, -0.12] },
    views: { box: [[-0.05, 0.5, 0.55], [-0.1, 0.2, BZ]], brA: [[-0.38, 0.36, 0.05], [AX, YTOP, BZ]], brB: [[AX + 0.38, 0.37, 0.06], [AX + 0.3, YTOP, BZ]],
      wire: [[-0.1, 0.48, 0.35], [-0.2, WY, BZ]], hanger: [[0.72, 0.3, 0.25], [HX, 0.12, BZ]], rider: [[-0.2, 0.33, -0.06], [-0.33, WY, BZ]],
      forks: [[0.8, 0.3, 0.42], [FBX, 0.02, FBZ]], pad: [[1.0, 0.22, 0.42], [PADX, 0.02, PADZ]], work: [[0.05, 0.62, 0.78], [-0.12, 0.2, -0.2]],
      load: [[0.95, 0.5, 0.5], [0.52, 0.13, -0.26]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A wire stretched between two bridges vibrates most strongly in its fundamental mode. When that natural frequency equals the frequency of a tuning fork pressed on the box, the wire resonates: its amplitude grows large and a paper rider on its middle falls off.',
      formula: 'f = (1 / 2l) √(T / μ)', formulaNote: 'so μ = T / (4 l² f²) · T = Mg, the weight on the hanger',
      more: ['At a fixed tension, f × l is constant: a fork of twice the frequency resonates at half the length. A graph of l against √T / f is a straight line through the origin with slope 1 / (2√μ).'],
      precautions: 'Strike the fork only on the rubber pad. Press its stem gently on the box, not on the wire. Put the rider at the middle of the vibrating length. Move the bridge in small steps near resonance. Do not overload the wire.' },
    book: { title: 'Expt. — Sonometer', lines: ['Aim: to find μ of the wire and verify f·l = constant.', 'Hanger 0.5 kg + 0.5 kg slotted masses, g = 9.8', 'f = (1/2l)√(T/μ)  →  μ = T / (4 l² f²)', 'Rider falls at resonance'],
      columns: [{ label: 'f (Hz)', get: function (r) { return String(r.f); } }, { label: 'M (kg)', get: function (r) { return r.M.toFixed(1); } },
        { label: 'l (cm)', get: function (r) { return (r.l * 100).toFixed(1); } }, { label: 'f·l (m/s)', get: function (r) { return (r.f * r.l).toFixed(1); } },
        { label: 'μ (g/m)', get: function (r) { return (muOf(r) * 1000).toFixed(3); } }] },
    graph: { x: function (r) { return Math.sqrt(r.Tn) / r.f; }, y: function (r) { return r.l * 100; }, xlabel: '√T / f (√N·s)', ylabel: 'l (cm)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) { if (rows.length < 2) return null; var m = S.fit.mean(rows.map(muOf));
      return { label: 'μ (wire)', value: m, unit: 'kg/m', digits: 5, truth: p.mu, note: 'Mean of T / (4 l² f²) over ' + rows.length + ' readings.' }; },
    tol: 0.02,
    chips: ['Why does the rider fall off?', 'Why is f × l constant?', 'Why press the fork on the box?', 'Check my readings', 'Why is my μ different?'],
    viva: [['If the length between the bridges is halved, the frequency of the wire', ['doubles', 'halves', 'stays the same'], 0, 'f = (1/2l)√(T/μ): f ∝ 1/l.'],
      ['Why does the paper rider fall at resonance?', ['The wire\'s amplitude becomes very large at its middle', 'The fork pushes it', 'The box tilts'], 0, 'At resonance the fork drives the wire at its natural frequency, so the amplitude builds up.']],
    askState: function () { return { length_cm: +(st.l * 100).toFixed(1), load_kg: mass(), tension_N: +(mass() * G).toFixed(1), fork_Hz: st.fork, fork_on_box: st.touching,
      rider: st.rider === 'on' ? 'on the wire' : 'fallen off', last_response: st.lastLoud === null ? null : +st.lastLoud.toFixed(2), readings_taken: S.rows.length }; },

    steps: [
      { id: 'load', title: 'Tension', view: 'load', render: function (u) {
          u.h2('Load the hanger');
          u.p('The tension in the wire is the weight on the hanger: T = Mg. Load 3 to 5 kg. Each slotted mass is 0.5 kg; the hanger is 0.5 kg.');
          u.row(u.button('Add 0.5 kg', function () { addMass(1); S.render(); }, true, S.hand.busy || st.n >= NDISC), u.button('Remove 0.5 kg', function () { addMass(-1); S.render(); }, false, S.hand.busy || st.n <= 3));
          u.live(function () { return 'Load M = ' + mass().toFixed(1) + ' kg · T = ' + (mass() * G).toFixed(1) + ' N'; });
          var ok = mass() >= 3 && mass() <= 5;
          if (!ok) u.note('Use a load between 3 and 5 kg for clear resonances on this wire.');
          u.next('Next: find resonance', ok);
        },
        ok: function () { return mass() >= 3 && mass() <= 5; },
        auto: function () { return mass() < 4 ? addMass(1).then(function () { return mass() < 4 ? addMass(1) : null; }) : Promise.resolve(); } },
      { id: 'resonate', title: 'Resonance', view: 'work', render: function (u) {
          u.h2('Slide the bridge until the rider falls');
          u.p('Pick a fork. Set a length, let the hand slide the bridge, then strike the fork on the pad and press its stem on the box. When the rider trembles, move the bridge a millimetre at a time until it flies off. Record, then repeat with the other forks.');
          var fr = u.row(); FORKS.forEach(function (f) { fr.appendChild(u.button((st.fork === f ? '✓ ' : '') + f + ' Hz', function () { st.fork = f; st.heardAt = null; S.render(); }, false, S.hand.busy)); });
          u.slider('Length to set', LMIN * 100, LMAX * 100, 0.1, function () { return st.target; }, function (v) { st.target = v; }, 'cm', 1);
          u.row(u.button('Slide the bridge', function () { moveBridge(st.target / 100); S.render(); }, true, S.hand.busy || st.rider !== 'on'),
            u.button('Sound the fork on the box', function () { strike(); S.render(); }, false, S.hand.busy || st.rider !== 'on'));
          u.row(u.button('−1 mm', function () { st.target = Math.round(st.l * 1000 - 1) / 10; moveBridge(st.target / 100); S.render(); }, false, S.hand.busy || st.rider !== 'on'),
            u.button('+1 mm', function () { st.target = Math.round(st.l * 1000 + 1) / 10; moveBridge(st.target / 100); S.render(); }, false, S.hand.busy || st.rider !== 'on'),
            u.button('Put the rider back', function () { riderBack(); }, false, S.hand.busy || st.rider === 'on'),
            u.button(st.sound ? 'Sound: on' : 'Sound: off', function () { st.sound = !st.sound; if (st.sound) audioWake(); else audioLevel(0); S.render(); }, false, false));
          u.live(function () { return 'l = ' + (st.l * 100).toFixed(1) + ' cm · fork ' + st.fork + ' Hz · rider ' + (st.rider === 'on' ? 'on the wire' : 'fallen off'); });
          u.row(u.button('Record f and l', record, true, S.hand.busy || st.rider === 'on'));
          u.h3('Observation table'); u.table();
          var forksDone = {}; S.rows.forEach(function (r) { forksDone[r.f] = 1; });
          u.next('Next: work out μ', Object.keys(forksDone).length >= 3);
          if (Object.keys(forksDone).length < 3) u.p('Readings with ' + Object.keys(forksDone).length + ' fork(s). Use at least 3 different forks.');
        },
        ok: function () { var d = {}; S.rows.forEach(function (r) { d[r.f] = 1; }); return Object.keys(d).length >= 3; },
        auto: function () {
          var guess = 0.38;
          return [256, 320, 384].reduce(function (pr, f) { return pr.then(function () {
            st.fork = f; var g = S.rows.length ? S.rows[0].l * S.rows[0].f / f : guess;
            return findRes(g).then(function () { S.advance(1); record(); }); }); }, Promise.resolve()); } },
    ],

    tick: function (dt) {
      st.clock += dt;
      if (st.amp > 0) st.amp = Math.max(0, st.amp - st.amp * dt / 4);
      Object.keys(forks).forEach(function (f) { forks[f].vibrate(+f === st.fork ? st.amp : 0); });
      var resp = st.touching ? st.amp * loudNow() : 0;
      if (st.touching && st.amp > 0.3 && loudNow() > 0.8 && st.rider === 'on') knockRider();
      blur.material.opacity = Math.min(0.85, resp * 1.6); blur.scale.y = 0.0015 + 0.012 * resp; blur.position.set(AX + st.l / 2, WY, BZ);
      if (st.rider === 'on') { rider.position.copy(riderHome()); rider.position.y += Math.abs(Math.sin(st.clock * 60)) * 0.004 * resp; rider.rotation.z = Math.sin(st.clock * 47) * 0.25 * resp; }
      else if (st.rider === 'flying') { st.riderT += dt; var t = st.riderT, f0 = st.riderFrom; rider.position.set(f0.x + 0.05 * t, f0.y + 0.35 * t - 4.9 * t * t, f0.z + 0.12 * t); rider.rotation.z += dt * 9;
        var floor = YTOP + 0.005; if (rider.position.z > BZ + 0.065) floor = RISER - 0.0;
        if (rider.position.y <= floor && t > 0.05) { rider.position.y = floor; st.rider = 'off'; rider.rotation.set(Math.PI / 2 - 0.3, 0, 0.8); } }
      if (S.fast && st.rider === 'flying') { st.rider = 'off'; rider.position.set(riderHome().x + 0.04, YTOP + 0.005, BZ + 0.03); rider.rotation.set(Math.PI / 2 - 0.3, 0, 0.8); }
      audioLevel(st.amp > 0.01 ? 0.03 * st.amp + 0.25 * resp : 0);
      hudL.set((st.l * 100).toFixed(1) + ' cm'); hudT.set((mass() * G).toFixed(1) + ' N (' + mass().toFixed(1) + ' kg)'); hudF.set(st.fork + ' Hz');
    },
  };
});
