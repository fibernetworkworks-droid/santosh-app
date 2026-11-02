/* Prayogshala studio module: Resonance tube - speed of sound (NCERT Class XI).
   Physics: the resonance kernel from kernels.js (loudness of the air column closed by water, with the 0.3 d end
   correction) - the same numbers the server checks. v = 2f(l2 - l1); the true v in this lab is 331.3 √(1 + Tc/273.15). */
HoolaStudio.define('resonance-tube', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.resonance;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('resonance');
  var HMIN = 0.02, HMAX = 0.95;
  var st = { h: Math.round(p.h * 1000) / 1000, target: 12, roomRead: false, forkRead: false, amp: 0, over: false, lastLoud: null, heardAt: null, sound: true, shownDb: 30 };
  function has(n) { for (var i = 0; i < S.rows.length; i++) if (S.rows[i].n === n) return S.rows[i]; return null; }
  function loudAt(h) { p.h = h; return K.view({}, p).loud; }
  function vTrue() { return 331.3 * Math.sqrt(1 + p.Tc / 273.15); }

  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'grip', 300); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }

  // ---------- apparatus: base, back board, glass tube, metre scale, reservoir on a rod
  var TX = 0, TZ = -0.15, RIN = p.d / 2, ROUT = RIN + 0.0022, Y_TOP = 1.05, Y_BOT = 0.06;
  var frame = new T.Group(); S.scene.add(frame);
  var base = S.rounded(0.44, 0.22, 0.03, 0.008, M.darkWood); base.rotation.x = -Math.PI / 2; base.position.set(0.15, 0.015, -0.15); frame.add(base);
  [[-0.05, -0.23], [-0.05, -0.07], [0.35, -0.23], [0.35, -0.07]].forEach(function (f) { var s = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.006, 6), M.brass); s.position.set(f[0], 0.033, f[1]); frame.add(s); });
  var board = S.rounded(0.15, 1.06, 0.02, 0.006, M.wood); board.position.set(0.0, 0.56, -0.2); frame.add(board);
  S.contact(0.56, 0.32, 0.15, -0.15, 0.6);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xf2f8fa, roughness: 0.04, metalness: 0, transparent: true, opacity: 0.2, clearcoat: 1, clearcoatRoughness: 0.04, envMapIntensity: 1.6, depthWrite: false, side: T.DoubleSide });   // light glass: no transmission pass for a 1 m tube
  var tube = S.mesh(new T.CylinderGeometry(ROUT, ROUT, Y_TOP - Y_BOT, 48, 1, true), glassM, false, false); tube.position.set(TX, (Y_TOP + Y_BOT) / 2, TZ); S.scene.add(tube);
  var lip = S.mesh(new T.TorusGeometry(ROUT - 0.001, 0.0014, 8, 40), glassM, false); lip.rotation.x = Math.PI / 2; lip.position.set(TX, Y_TOP, TZ); S.scene.add(lip);
  var foot = S.mesh(new T.CylinderGeometry(ROUT + 0.003, 0.006, 0.03, 32), M.brass); foot.position.set(TX, Y_BOT - 0.012, TZ); S.scene.add(foot);
  [0.28, 0.82].forEach(function (y) { var band = S.mesh(new T.TorusGeometry(ROUT + 0.002, 0.0022, 8, 32), M.alu); band.rotation.x = Math.PI / 2; band.position.set(TX, y, TZ); S.scene.add(band);
    var arm = S.mesh(new T.BoxGeometry(0.008, 0.008, 0.03), M.alu); arm.position.set(TX, y, TZ - ROUT - 0.013); S.scene.add(arm); });
  var waterM = new T.MeshStandardMaterial({ color: 0x4f9fcf, roughness: 0.06, metalness: 0, transparent: true, opacity: 0.5 });
  var col = S.mesh(new T.CylinderGeometry(RIN - 0.0004, RIN - 0.0004, 1, 32), waterM, false); S.scene.add(col);
  var meniscus = S.mesh(new T.TorusGeometry(RIN - 0.0012, 0.0012, 6, 32), waterM, false); meniscus.rotation.x = Math.PI / 2; S.scene.add(meniscus);
  var ruler = S.ruler(1.0, { title: 'METRE SCALE · cm from the open end', labelEvery: 10 });
  ruler.position.set(TX + 0.042, Y_TOP - 1.0, TZ);   // zero at the open end S.scene.add(ruler);
  var thermo = S.thermometer({ len: 0.24, min: -10, max: 50, value: p.Tc, pos: [-0.052, 0.52, -0.186] });
  var tl = S.label('ROOM', { w: 0.026, ratio: 0.3, color: '#4a3412' }); tl.position.set(-0.05, 0.5, -0.1895); S.scene.add(tl);
  // reservoir: a glass can on a sliding clamp
  var RX = 0.3, RODX = 0.22, CANR = 0.032, CANH = 0.1;
  var rod = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 1.06, 32), M.chrome); rod.position.set(RODX, 0.56, TZ); S.scene.add(rod);
  var rodNut = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.01, 6), M.chrome); rodNut.position.set(RODX, 0.035, TZ); S.scene.add(rodNut);
  var res = new T.Group(); S.scene.add(res);
  var boss = S.rounded(0.032, 0.04, 0.032, 0.006, M.alu); boss.position.set(RODX - RX, 0.06, 0); res.add(boss);
  var screw = new T.Group(); var sk = S.mesh(new T.CylinderGeometry(0.0095, 0.0095, 0.009, 6), M.black); sk.rotation.x = Math.PI / 2; sk.position.z = 0.03; screw.add(sk);
  var ss = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.02, 10), M.chrome); ss.rotation.x = Math.PI / 2; ss.position.z = 0.02; screw.add(ss); screw.position.set(RODX - RX, 0.06, 0); res.add(screw);
  var rarm = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, RX - RODX - CANR, 16), M.chrome); rarm.rotation.z = Math.PI / 2; rarm.position.set(-(RX - RODX + CANR) / 2 + 0.0, 0.06, 0); res.add(rarm);
  var ring = S.mesh(new T.TorusGeometry(CANR + 0.002, 0.0028, 8, 36), M.chrome); ring.rotation.x = Math.PI / 2; ring.position.y = 0.06; res.add(ring);
  var canPts = [[0, 0.0005], [CANR - 0.004, 0.0005], [CANR, 0.004], [CANR, CANH], [CANR - 0.0015, CANH], [CANR - 0.0015, 0.0035], [0, 0.002]].map(function (a) { return new T.Vector2(a[0], a[1]); });
  res.add(new T.Mesh(new T.LatheGeometry(canPts, 40), glassM));
  var cw = S.mesh(new T.CylinderGeometry(CANR - 0.002, CANR - 0.002, 0.05, 32), waterM, false); cw.position.y = 0.002 + 0.025; res.add(cw);
  var outlet = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.018, 12), glassM, false); outlet.rotation.z = Math.PI / 2; outlet.position.set(-CANR - 0.007, 0.008, 0); res.add(outlet);
  var rubberM = new T.MeshStandardMaterial({ color: 0x8e3a26, roughness: 0.62 });
  var hose = S.mesh(new T.BufferGeometry(), rubberM); S.scene.add(hose); var hoseAt = -1;
  var resShadow = S.contact(0.1, 0.1, RX, TZ, 0.3, 0.03);
  // tuning fork resting on its felt-lined box, rubber pad, sound-level meter
  var fork = S.tuningFork([0, 0, 0], Math.round(p.f));
  var fbox = S.rounded(0.24, 0.07, 0.022, 0.006, M.darkWood); fbox.rotation.x = -Math.PI / 2; fbox.position.set(0.37, 0.011, 0.08); S.scene.add(fbox);
  var felt = S.mesh(new T.BoxGeometry(0.22, 0.002, 0.05), new T.MeshStandardMaterial({ color: 0x7a1f2b, roughness: 1 })); felt.position.set(0.37, 0.0225, 0.08); S.scene.add(felt);
  S.contact(0.3, 0.11, 0.37, 0.08, 0.45);
  var FORK_HOME = { grip: new T.Vector3(0.3, 0.0275, 0.08), rot: -Math.PI / 2, rx: Math.PI / 2 };
  var GRIPL = new T.Vector3(0, 0.02, 0);
  function placeFork(grip, rot, rx) { fork.rotation.set(rx || 0, 0, rot); var off = GRIPL.clone().applyEuler(fork.rotation); fork.position.copy(grip).sub(off); }
  placeFork(FORK_HOME.grip, FORK_HOME.rot, FORK_HOME.rx);
  var PADX = 0.56, PADZ = 0.14, PADH = 0.025;
  var pad = S.rounded(0.07, 0.05, PADH, 0.006, M.rubber); pad.rotation.x = -Math.PI / 2; pad.position.set(PADX, PADH / 2, PADZ); S.scene.add(pad);
  var pl = S.label('RUBBER PAD', { w: 0.04, ratio: 0.16, color: '#9a9a9a' }); pl.rotation.x = -Math.PI / 2; pl.position.set(PADX, PADH + 0.0005, PADZ + 0.012); S.scene.add(pl);
  S.contact(0.1, 0.08, PADX, PADZ, 0.45);
  var meter = S.meter({ min: 30, max: 100, unit: 'dB', symbol: 'dB', caption: 'SOUND LEVEL', ticks: 7, pos: [-0.2, 0, -0.08], rotY: 0.35 });

  S.addApparatus('tube', tube, 'Resonance tube', 'Glass tube about 1 m long, inner diameter ' + (p.d * 100).toFixed(1) + ' cm. Open at the top, closed below by the water.');
  S.addApparatus('ruler', ruler, 'Metre scale', 'Zero at the open end: it reads the length of the air column directly. Least count 1 mm.');
  S.addApparatus('res', res, 'Water reservoir', 'Joined to the tube by rubber tubing. Raise it and the water in the tube rises; lower it and the air column gets longer.');
  S.addApparatus('fork', fork, 'Tuning fork, ' + Math.round(p.f) + ' Hz', 'Strike it on the rubber pad, never on the bench. Hold it just over the mouth with the prongs one above the other.');
  S.addApparatus('pad', pad, 'Rubber pad', 'Strike the fork on this so it sounds a pure note without damage.');
  S.addApparatus('meter', meter, 'Sound-level meter', 'Shows how loud the tube is. At resonance the sound swells sharply.');
  S.addApparatus('thermo', thermo, 'Room thermometer', 'The speed of sound depends on the air temperature.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudH = S.hudCard('Air column l'), hudL = S.hudCard('Sound level'), hudN = S.hudCard('Readings');

  // ---------- sound (WebAudio, only after the student taps a button)
  var au = { ctx: null, osc: null, gain: null };
  function audioWake() { if (S.fast || !st.sound) return; try { var AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
      if (!au.ctx) { au.ctx = new AC(); au.gain = au.ctx.createGain(); au.gain.gain.value = 0; au.gain.connect(au.ctx.destination); }
      if (au.ctx.state === 'suspended') au.ctx.resume();
      if (!au.osc) { au.osc = au.ctx.createOscillator(); au.osc.type = 'sine'; au.osc.frequency.value = p.f; au.osc.connect(au.gain); au.osc.start(); } } catch (e) { /* sound is optional */ } }
  function audioLevel(v) { if (!au.gain) return; try { au.gain.gain.setTargetAtTime(st.sound ? v : 0, au.ctx.currentTime, 0.04); } catch (e) { /* ignore */ } }

  // ---------- actions
  function surfY(h) { return Y_TOP - h; }
  function setH(h) { st.h = h; var y = surfY(h), hh = y - Y_BOT; col.scale.y = hh; col.position.set(TX, Y_BOT + hh / 2, TZ); meniscus.position.set(TX, y, TZ);
    var canB = y - 0.05; res.position.set(RX, canB, TZ); resShadow.material.opacity = Math.max(0.08, 0.35 - canB * 0.4);
    if (Math.abs(canB - hoseAt) > 0.002) { hoseAt = canB; var ox = RX - CANR - 0.016, oy = canB + 0.008;
      var pts = [[TX, Y_BOT - 0.026], [TX + 0.004, 0.045], [TX + 0.05, 0.04], [ox - 0.06, Math.min(0.045 + (oy - 0.04) * 0.35, oy)], [ox - 0.015, oy], [ox, oy]].map(function (a) { return new T.Vector3(a[0], a[1], TZ); });
      hose.geometry.dispose(); hose.geometry = new T.TubeGeometry(new T.CatmullRomCurve3(pts), 70, 0.005, 12, false); } }
  setH(st.h);
  function moveRes(target) {
    if (S.hand.busy) return Promise.resolve();
    target = Math.round(target * 1000) / 1000;
    if (!(target >= HMIN && target <= HMAX)) { S.say('Keep the air column between ' + HMIN * 100 + ' and ' + HMAX * 100 + ' cm: the water must stay inside the tube.'); return Promise.resolve(); }
    var h0 = st.h; if (Math.abs(target - h0) < 0.0005) { S.say('The water is already at ' + (target * 100).toFixed(1) + ' cm.'); return Promise.resolve(); }
    var knobAt = function (h) { return new T.Vector3(RX + RODX - RX, surfY(h) - 0.05 + 0.06, TZ + 0.035); };
    var hk = function (k) { return h0 + (target - h0) * k; };
    return S.hand.pinchMove(knobAt(h0), function (k) { return knobAt(hk(k)); }, function (k) { setH(hk(k)); }, { ms: 700 + Math.abs(target - h0) * 2500 })
      .then(function () { setH(target); st.heardAt = null; S.say('Reservoir moved: air column ' + (target * 100).toFixed(1) + ' cm on the scale. Strike the fork and listen.'); S.render(); });
  }
  function strike() {
    if (S.hand.busy) return Promise.resolve();
    audioWake();
    var g0 = FORK_HOME.grip.clone(), g1 = new T.Vector3(PADX - 0.15, 0.11, PADZ), gs = new T.Vector3(PADX - 0.15, PADH + 0.0154 + 0.004, PADZ),
      gm = new T.Vector3(TX + 0.09, Y_TOP + 0.03, TZ + 0.0);
    var L = function (a, b, k) { return a.clone().lerp(b, k); }, arc = function (a, b, k, hh) { return L(a, b, k).add(new T.Vector3(0, Math.sin(Math.PI * k) * hh, 0)); };
    var legs = [
      { ms: 900, fn: function (k) { return arc(g0, g1, k, 0.05); }, onK: function (k) { placeFork(arc(g0, g1, k, 0.05), FORK_HOME.rot * (1 - k), FORK_HOME.rx * (1 - k)); } },
      { ms: 260, fn: function (k) { return L(g1, gs, k); }, onK: function (k) { placeFork(L(g1, gs, k), -1.6 * k); if (k >= 1 && st.amp < 0.5) { st.amp = 1; S.click(300, 0.04, 0.08); } } },
      { ms: 1300, fn: function (k) { return arc(gs, gm, k, 0.1); }, onK: function (k) { placeFork(arc(gs, gm, k, 0.1), -1.6 + (1.6 + Math.PI / 2) * k); st.over = k > 0.97; } },
      { ms: 2600, fn: function () { return gm; }, onK: function () { st.over = true; } },
      { ms: 1300, fn: function (k) { return arc(gm, g0, k, 0.08); }, onK: function (k) { st.over = false; placeFork(arc(gm, g0, k, 0.08), Math.PI / 2 - Math.PI * k, FORK_HOME.rx * k); } },
    ];
    st.amp = 0;
    return carry(g0, legs, 'grip').then(function () {
      st.lastLoud = loudAt(st.h); st.heardAt = st.h; st.amp = 0; st.over = false; placeFork(FORK_HOME.grip, FORK_HOME.rot, FORK_HOME.rx);
      S.say('At ' + (st.h * 100).toFixed(1) + ' cm the tube sounded ' + (st.lastLoud > 0.6 ? 'very loud: resonance.' : st.lastLoud > 0.15 ? 'louder than the fork alone.' : 'faint.')); S.render(); });
  }
  function mark(n) {
    if (S.hand.busy) return;
    if (st.heardAt === null || Math.abs(st.heardAt - st.h) > 1e-6) { S.say('Strike the fork and listen at this level first.'); return; }
    if (n === 2 && (!has(1) || st.h < has(1).h + 0.15)) { S.say(has(1) ? 'The second resonance is much further down (about three times l₁). Lower the water more.' : 'Find l₁ first.'); return; }
    if (n === 1 && st.h > 0.4) { S.say('That is too long for the first resonance. Look between 10 and 30 cm.'); return; }
    var row = { n: n, h: Math.round(st.h * 1000) / 1000, loud: st.lastLoud };
    for (var i = S.rows.length - 1; i >= 0; i--) if (S.rows[i].n === n) S.rows.splice(i, 1);
    S.rows.push(row); S.rows.sort(function (a, b) { return a.n - b.n; }); S.book.draw();
    S.say('Written: l' + (n === 1 ? '₁' : '₂') + ' = ' + (row.h * 100).toFixed(1) + ' cm.'); S.render();
  }
  function scan(lo, hi, step) {     // listen at each level, return the loudest - the same moves a student makes
    var best = { h: lo, l: -1 }, hs = []; for (var h = lo; h <= hi + 1e-9; h += step) hs.push(Math.round(h * 1000) / 1000);
    return hs.reduce(function (pr, h) { return pr.then(function () { return moveRes(h).then(strike).then(function () { if (st.lastLoud > best.l) best = { h: h, l: st.lastLoud }; }); }); }, Promise.resolve())
      .then(function () { return best.h; });
  }
  function find(lo, hi) { return scan(lo, hi, 0.01).then(function (c) { return scan(Math.max(HMIN, c - 0.009), Math.min(HMAX, c + 0.009), 0.001); }).then(function (b) { return moveRes(b).then(strike); }); }
  function stepUi(u, n) {
    var lo = n === 1 ? 2 : 30, hi = n === 1 ? 40 : 95;
    if (st.target < lo || st.target > hi) st.target = n === 1 ? 12 : Math.max(40, Math.round(st.h * 100));
    u.slider('Air column to set', lo, hi, 0.1, function () { return st.target; }, function (v) { st.target = v; }, 'cm', 1);
    u.row(u.button('Move the reservoir', function () { moveRes(st.target / 100); S.render(); }, true, S.hand.busy),
      u.button('Strike the fork and listen', function () { strike(); S.render(); }, false, S.hand.busy));
    u.row(u.button('−1 mm', function () { st.target = Math.max(lo, Math.round(st.h * 1000 - 1) / 10); moveRes(st.target / 100); S.render(); }, false, S.hand.busy),
      u.button('+1 mm', function () { st.target = Math.min(hi, Math.round(st.h * 1000 + 1) / 10); moveRes(st.target / 100); S.render(); }, false, S.hand.busy),
      u.button(st.sound ? 'Sound: on' : 'Sound: off', function () { st.sound = !st.sound; if (st.sound) audioWake(); else audioLevel(0); S.render(); }, false, false));
    u.live(function () { return 'Air column ' + (st.h * 100).toFixed(1) + ' cm · ' + (st.heardAt !== null && Math.abs(st.heardAt - st.h) < 1e-6 ? 'heard: ' + Math.round(st.shownDb > 30 ? st.shownDb : dbOf(st.lastLoud, 1)) + ' dB' : 'not yet listened here'); });
  }
  function dbOf(loud, amp) { return Math.max(30, Math.min(100, 92 + 20 * Math.log10(Math.max(1e-6, loud * amp)))); }

  return {
    camera: { pos: [0.95, 0.9, 1.85], look: [0.1, 0.5, -0.12] },
    views: { tube: [[0.5, 0.75, 1.2], [0.05, 0.6, TZ]], ruler: [[0.2, 0.85, 0.38], [0.04, 0.8, TZ]], res: [[0.6, 0.45, 0.6], [0.26, 0.3, TZ]],
      fork: [[0.52, 0.25, 0.42], [0.37, 0.03, 0.08]], pad: [[0.7, 0.22, 0.45], [0.56, 0.02, 0.14]], meter: [[-0.05, 0.25, 0.32], [-0.2, 0.05, -0.08]],
      thermo: [[0.05, 0.6, 0.25], [-0.05, 0.6, -0.19]], mouth: [[0.38, 1.15, 0.55], [0.06, 1.0, TZ]], work: [[0.62, 1.16, 0.8], [0.14, 0.94, -0.15]], work2: [[0.8, 1.02, 1.2], [0.14, 0.74, -0.15]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A tuning fork held over a tube closed at one end sets the air column vibrating. When the column\'s natural frequency matches the fork, it resonates and the sound swells. This happens when the column (plus a small end correction e at the open end) is a quarter wavelength, then three quarters.',
      formula: 'l₁ + e = λ/4,  l₂ + e = 3λ/4', formulaNote: 'so l₂ − l₁ = λ/2 and v = fλ = 2f(l₂ − l₁) · e ≈ 0.3 d cancels out',
      more: ['The speed of sound rises with temperature: v ≈ 331.3 √(1 + t/273.15) m/s, about 0.6 m/s more for each °C.'],
      precautions: 'Strike the fork only on the rubber pad. Hold it just above the mouth, prongs one above the other, without touching the tube. Find each resonance by moving the water in small steps, from both sides. Read the bottom of the meniscus with your eye level with it.' },
    book: { title: 'Expt. — Resonance Tube', lines: ['Aim: to find the speed of sound in air.', 'Fork f = ' + Math.round(p.f) + ' Hz,  room ' + p.Tc + ' °C', 'Inner diameter d = ' + (p.d * 100).toFixed(1) + ' cm', 'l₂ − l₁ = λ/2  →  v = 2f(l₂ − l₁)', 'End correction e = (l₂ − 3l₁)/2'],
      columns: [{ label: 'Resonance', get: function (r) { return r.n === 1 ? 'First (l₁)' : 'Second (l₂)'; } }, { label: 'l (cm)', get: function (r) { return (r.h * 100).toFixed(1); } },
        { label: 'Sound', get: function (r) { return r.loud > 0.6 ? 'very loud' : 'loud'; } }] },
    result: function (rows) { var a = rows.filter(function (r) { return r.n === 1; })[0], b = rows.filter(function (r) { return r.n === 2; })[0]; if (!a || !b) return null;
      return { label: 'v (sound)', value: 2 * p.f * (b.h - a.h), unit: 'm/s', digits: 1, truth: vTrue(), note: 'v = 2f(l₂ − l₁); end correction e = ' + ((b.h - 3 * a.h) / 2 * 100).toFixed(2) + ' cm.' }; },
    tol: 0.02,
    chips: ['Why does the tube get loud at certain lengths?', 'What is the end correction?', 'Why use two resonances?', 'Check my readings', 'Why is my v different from 343 m/s?'],
    viva: [['Why is v found from l₂ − l₁ and not from l₁ alone?', ['The end correction cancels in the difference', 'l₁ is too short to measure', 'The fork changes frequency'], 0, 'l₁ + e = λ/4 and l₂ + e = 3λ/4, so l₂ − l₁ = λ/2 has no e in it.'],
      ['At the first resonance, the air column is about', ['a quarter wavelength', 'half a wavelength', 'one wavelength'], 0, 'A tube closed at one end resonates at λ/4, 3λ/4, ...']],
    askState: function () { return { air_column_cm: +(st.h * 100).toFixed(1), fork_Hz: Math.round(p.f), room_C: p.Tc, fork_sounding: st.amp > 0.05, held_over_mouth: st.over,
      last_heard_level_cm: st.heardAt === null ? null : +(st.heardAt * 100).toFixed(1), last_heard_dB: st.lastLoud === null ? null : Math.round(dbOf(st.lastLoud, 1)),
      l1_cm: has(1) ? +(has(1).h * 100).toFixed(1) : null, l2_cm: has(2) ? +(has(2).h * 100).toFixed(1) : null }; },

    steps: [
      { id: 'ready', title: 'Get ready', view: 'tube', render: function (u) {
          u.h2('Check the apparatus');
          u.task('1. Note the fork frequency', st.forkRead, st.forkRead ? 'f = ' + Math.round(p.f) + ' Hz (stamped on the fork)' : 'It is stamped on the fork')
            .add(u.button('Read the fork', function () { st.forkRead = true; S.focus('fork'); S.render(); }, !st.forkRead, st.forkRead));
          u.task('2. Note the room temperature', st.roomRead, st.roomRead ? 'Room ' + p.Tc.toFixed(0) + ' °C' : 'The thermometer is on the back board')
            .add(u.button('Read the thermometer', function () { st.roomRead = true; S.focus('thermo'); S.render(); }, !st.roomRead, st.roomRead));
          u.note('The air column is ' + (st.h * 100).toFixed(1) + ' cm now. You will lengthen the air column by lowering the reservoir. Sound plays after your first tap on Strike.');
          u.next('Next: find the first resonance', st.forkRead && st.roomRead);
        },
        ok: function () { return st.forkRead && st.roomRead; },
        auto: function () { st.forkRead = true; st.roomRead = true; return Promise.resolve(); } },
      { id: 'first', title: 'First resonance', view: 'work', render: function (u) {
          u.h2('Find l₁, the first resonance');
          u.p('Lower the water a little at a time, strike the fork and listen. Where the tube booms loudest, go back and forth by a millimetre to find the loudest point. Then mark it.');
          stepUi(u, 1);
          u.row(u.button(has(1) ? 'Mark again as l₁' : 'Mark this as l₁', function () { mark(1); }, true, S.hand.busy));
          u.h3('Observation table'); u.table();
          u.next('Next: find the second resonance', !!has(1));
        },
        ok: function () { return !!has(1); },
        auto: function () { return find(0.1, 0.25).then(function () { mark(1); }); } },
      { id: 'second', title: 'Second resonance', view: 'work2', render: function (u) {
          u.h2('Find l₂, the second resonance');
          u.p('Keep lowering the reservoir. The next loud point is roughly three times as deep as l₁. Find its loudest point and mark it.');
          stepUi(u, 2);
          u.row(u.button(has(2) ? 'Mark again as l₂' : 'Mark this as l₂', function () { mark(2); }, true, S.hand.busy));
          u.h3('Observation table'); u.table();
          u.next('Next: work out v', !!has(1) && !!has(2));
        },
        ok: function () { return !!has(1) && !!has(2); },
        auto: function () { var l1 = has(1).h; return find(Math.round((3 * l1 - 0.03) * 100) / 100, Math.round((3 * l1 + 0.06) * 100) / 100).then(function () { mark(2); }); } },
    ],

    tick: function (dt) {
      if (st.amp > 0) st.amp = Math.max(0, st.amp - st.amp * dt / 5);
      var l = loudAt(st.h), heard = st.amp * (st.over ? l : 0.04);
      var db = heard > 1e-4 ? dbOf(st.over ? l : 0.04, st.amp) : 30; st.shownDb += (db - st.shownDb) * Math.min(1, dt * 6);
      meter.set(st.shownDb); fork.vibrate(st.amp);
      audioLevel(st.amp > 0.01 ? 0.03 * st.amp + 0.3 * st.amp * (st.over ? l : 0) : 0);
      hudH.set((st.h * 100).toFixed(1) + ' cm'); hudL.set(Math.round(st.shownDb) + ' dB'); hudN.set(String(S.rows.length));
    },
  };
});
