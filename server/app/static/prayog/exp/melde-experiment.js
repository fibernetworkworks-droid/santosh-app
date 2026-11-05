/* Prayogshala studio module: Melde's experiment - frequency of an electrically maintained tuning fork (B.Sc. Waves).
   Physics: the hw_melde kernel (packs/heat_wave_ug) - the same numbers the server checks. The thread's tension is T = M g;
   p loops stand when 2 l f_s / v is a whole number (f_s = f/2 across the thread, f along it). The hidden knob f (the fork)
   is what the student finds, from f = k (p / l) sqrt(T / mu), k = 1 (transverse) or 1/2 (longitudinal). */
HoolaStudio.define('melde-experiment', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.hw_melde;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('hw_melde');
  var LONG = p.mode > 0.5, PAN = 0.005;                      // the pan weighs 5 g
  var muMeas = Math.round(p.mu * 2 * 1e5) / 2e5;               // 2.00 m of thread weighed to 0.01 g, per metre
  var KF = LONG ? 0.5 : 1.0, P0 = Math.round(p.p0);
  var st = { mu: false, len: false, fork: false, load: 0.1, phase: 0, shown: 0, clock: 0 };                                              // total hung mass in kg, starting well above any resonance
  function r1(v) { return Math.round(v * 10) / 10; }
  function mass() { return Math.round(st.load * 1e4) / 1e4; }
  function view() { p.M = mass(); return K.view({ t: 0 }, p); }
  function g1(v) { return (v * 1000).toFixed(1); }

  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'pinch', 320); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }
  // ---------- geometry: thread along x at height YT, from the fork tip (x = XF) to the pulley (x = XF + L)
  var L = p.L, ZT = -0.2, YT = 0.22, XF = -0.62, XP = XF + L;
  var OFFY = LONG ? 0 : YT - 0.07, BHT = LONG ? 0.05 : OFFY + 0.05;     // a transverse fork stands on a block so the thread runs level
  var base = S.rounded(0.3, BHT, 0.14, 0.008, M.darkWood); base.position.set(XF - 0.17, BHT / 2, ZT); S.scene.add(base); S.contact(0.36, 0.2, XF - 0.17, ZT, 0.5);
  var forkG = new T.Group(); S.scene.add(forkG); forkG.position.y = OFFY;
  var fbody = S.mesh(new T.BoxGeometry(0.04, 0.02, 0.03), M.steel); fbody.position.set(XF - 0.15, 0.06, ZT); forkG.add(fbody);
  var pr1, pr2;
  if (!LONG) {                                                // transverse: prongs one above the other, vibrating up and down
    pr1 = S.mesh(new T.BoxGeometry(0.15, 0.008, 0.02), M.steel); pr1.position.set(XF - 0.07, 0.07, ZT); forkG.add(pr1);
    pr2 = S.mesh(new T.BoxGeometry(0.15, 0.008, 0.02), M.steel); pr2.position.set(XF - 0.07, 0.05, ZT); forkG.add(pr2);
  } else {                                                    // longitudinal: prongs side by side along the thread, vibrating along it
    pr1 = S.mesh(new T.BoxGeometry(0.008, 0.2, 0.02), M.steel); pr1.position.set(XF - 0.012, 0.16, ZT); forkG.add(pr1);
    pr2 = S.mesh(new T.BoxGeometry(0.008, 0.2, 0.02), M.steel); pr2.position.set(XF - 0.036, 0.16, ZT); forkG.add(pr2);
    var fb2 = S.mesh(new T.BoxGeometry(0.04, 0.02, 0.03), M.steel); fb2.position.set(XF - 0.024, 0.055, ZT); forkG.add(fb2);
  }
  var coil = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.03, 20), M.copper); coil.rotation.z = Math.PI / 2; coil.position.set(XF - 0.2, 0.06, ZT); forkG.add(coil);
  var core = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.045, 14), M.iron); core.rotation.z = Math.PI / 2; core.position.set(XF - 0.185, 0.06, ZT); forkG.add(core);
  var fl = S.label('ELECTRICALLY MAINTAINED FORK', { w: 0.12, ratio: 0.1, color: '#e8e8e8', bg: '#2b2f36' }); fl.position.set(XF - 0.17, 0.0505, ZT + 0.0705); fl.rotation.x = 0; forkG.add(fl);
  var fsw = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.012, 20), M.red); fsw.rotation.x = Math.PI / 2; fsw.position.set(XF - 0.1, 0.03, ZT + 0.072); forkG.add(fsw);
  var cell = S.cell([XF - 0.3, 0, ZT + 0.0]);
  // thread's fixed end is the tip of the upper prong (transverse) / the right prong (longitudinal)
  var tipX = LONG ? XF - 0.012 : XF + 0.005, tipY = YT;
  // pulley on a clamp stand
  var stand = new T.Group(); S.scene.add(stand);
  var sb = S.rounded(0.14, 0.1, 0.025, 0.006, M.iron); sb.rotation.x = -Math.PI / 2; sb.position.set(XP + 0.02, 0.0125, ZT); stand.add(sb);
  var rod = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.34, 14), M.chrome); rod.position.set(XP + 0.04, 0.17, ZT); stand.add(rod);
  var arm = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.07, 12), M.chrome); arm.rotation.z = Math.PI / 2; arm.position.set(XP + 0.0, YT - 0.02 + 0.02, ZT - 0.01); stand.add(arm);
  var pulley = S.mesh(new T.CylinderGeometry(0.022, 0.022, 0.01, 40), M.brass); pulley.rotation.x = Math.PI / 2; pulley.position.set(XP, YT - 0.022, ZT); stand.add(pulley);
  S.contact(0.18, 0.14, XP + 0.02, ZT, 0.5);
  // hanger, pan and weights
  var hang = new T.Group(); S.scene.add(hang);
  var cordV = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 1, 6), M.thread, false, false); hang.add(cordV);
  var panG = new T.Group(); hang.add(panG);
  var pdisc = S.mesh(new T.CylinderGeometry(0.04, 0.036, 0.008, 36), M.steel); panG.add(pdisc);
  [-1, 1].forEach(function (sx) { var hk = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 0.05, 6), M.steel, false, false); hk.position.set(sx * 0.02, 0.025, 0); hk.rotation.z = -sx * 0.4; panG.add(hk); });
  var wstack = new T.Group(); panG.add(wstack);
  function setHang() {
    var m = mass(), drop = 0.06 + Math.max(0, 0.16 - m * 0.6), yPan = YT - 0.022 - 0.17 - drop * 0.0 - 0.0;
    var yp = Math.max(0.03, YT - 0.022 - 0.1 - m * 0.2); panG.position.set(XP + 0.022, yp, ZT);
    var top = YT - 0.022, len = Math.max(0.01, top - (yp + 0.05)); cordV.scale.y = len; cordV.position.set(XP + 0.022, yp + 0.05 + len / 2, ZT);
    while (wstack.children.length) wstack.remove(wstack.children[0]);
    var nW = Math.min(10, Math.round((m - PAN) * 1000 / 10)); for (var i = 0; i < nW; i++) { var w = S.mesh(new T.CylinderGeometry(0.024, 0.024, 0.005, 24), M.brass); w.position.set(0, 0.0065 + i * 0.0052, 0); wstack.add(w); }
  }
  setHang();
  // metre scale behind the thread (to read l), and a tuning-fork-style nameplate
  var scTex = S.canvasTex(2048, 64, function (x, w, h) { x.fillStyle = '#e7d4a4'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a2a10'; x.font = '600 22px sans-serif';
    for (var c = 0; c <= 100; c++) { var xx = c / 100 * (w - 4) + 2, big = c % 10 === 0; x.fillRect(xx, 0, big ? 3 : 1.5, big ? 28 : (c % 5 === 0 ? 20 : 12)); if (big) x.fillText(String(c), xx - 10, 54); } });
  var scale = new T.Mesh(new T.PlaneGeometry(L, 0.03), new T.MeshStandardMaterial({ map: scTex, roughness: 0.6 })); scale.position.set(XF + L / 2, YT - 0.075, ZT - 0.05); S.scene.add(scale);
  var sup = [XF + 0.01, XP - 0.01].map(function (x) { var s2 = S.mesh(new T.CylinderGeometry(0.003, 0.003, YT - 0.075, 8), M.steel); s2.position.set(x, (YT - 0.075) / 2, ZT - 0.05); S.scene.add(s2); return s2; });
  // the thread: a line + a translucent envelope that shows the blur of the loops
  var N = 160, tpos = new Float32Array((N + 1) * 3), tgeo = new T.BufferGeometry(); tgeo.setAttribute('position', new T.BufferAttribute(tpos, 3));
  var thread = new T.Line(tgeo, new T.LineBasicMaterial({ color: 0xf4f0e6 })); thread.frustumCulled = false; S.scene.add(thread);
  var epos = new Float32Array((N + 1) * 2 * 3), egeo = new T.BufferGeometry(); egeo.setAttribute('position', new T.BufferAttribute(epos, 3));
  var idx = []; for (var ei = 0; ei < N; ei++) { var a = ei * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } egeo.setIndex(idx);
  var env = new T.Mesh(egeo, new T.MeshBasicMaterial({ color: 0xfff2c8, transparent: true, opacity: 0.35, side: T.DoubleSide, depthWrite: false })); env.frustumCulled = false; S.scene.add(env);
  var thickT = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, L, 6), M.thread, false, false); thickT.rotation.z = Math.PI / 2; thickT.position.set(XF + L / 2, tipY, ZT); S.scene.add(thickT);
  var watch = S.stopwatch([0.3, 0.035, 0.17], [-1.15, 0, -0.2]);
  var hudM = S.hudCard('Load M'), hudP = S.hudCard('Loops'), hudA = S.hudCard('Sharpness');

  S.addApparatus('fork', forkG, 'Electrically maintained fork', 'A steel fork kept vibrating by an electromagnet and a contact breaker. Its frequency is unknown: you will find it. ' + (LONG ? 'The prongs vibrate along the thread (longitudinal arrangement).' : 'The prongs vibrate across the thread (transverse arrangement).'));
  S.addApparatus('thread', thread, 'Thread', 'A light cotton thread, ' + (L * 100).toFixed(0) + ' cm long between the fork and the pulley. Its mass per unit length is found by weighing.');
  S.addApparatus('pulley', pulley, 'Pulley', 'Smooth brass pulley. The thread passes over it to the pan.');
  S.addApparatus('pan', hang, 'Pan and weights', 'The pan weighs 5 g. Slotted weights go on it; the total load M sets the tension T = M g.');
  S.addApparatus('scale', scale, 'Metre scale', 'Lies along the thread: it gives the length l between the fork and the pulley.');
  S.addApparatus('cell', cell, 'Cell', 'Drives the electromagnet of the fork.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Not needed here, but it sits on every bench.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var bookLines = ['Aim: to find the frequency of the fork by Melde\'s method (' + (LONG ? 'longitudinal' : 'transverse') + ').', 'l = ' + (L * 100).toFixed(1) + ' cm,   μ = ' + (muMeas * 1000).toFixed(3) + ' g/m  (weighed)', 'f = ' + (LONG ? '(p / 2l) √(T/μ)' : '(p / l) √(T/μ)') + ',   T = M g'];

  // ---------- actions
  function weighThread() { if (st.mu) return; st.mu = true; S.say('2.00 m of thread weighs ' + (muMeas * 2000).toFixed(2) + ' g, so μ = ' + (muMeas * 1000).toFixed(3) + ' g/m. Written in your record book.'); S.book.draw(); S.render(); }
  function measureLen() { if (st.len) return; st.len = true; S.focus('scale'); S.say('l = ' + (L * 100).toFixed(1) + ' cm from the fork to the pulley.'); S.book.draw(); S.render(); }
  function forkOn() { if (S.hand.busy || st.fork) return Promise.resolve(); return S.hand.tap(fsw).then(function () { S.click(2000); st.fork = true; S.say('The fork is humming. Change the load and watch the thread.'); S.render(); }); }
  function setLoad(m) { st.load = Math.max(PAN + 0.001, Math.min(0.2, Math.round(m * 1e4) / 1e4)); setHang(); S.render(); }
  function addLoad(dm, hand) {
    if (S.hand.busy) return Promise.resolve();
    var go = function () { setLoad(mass() + dm); };
    if (hand && !S.fast) return S.hand.tap(pdisc).then(go);
    go(); return Promise.resolve();
  }
  function mark() {
    if (!st.fork) { S.say('Switch the fork on first.'); return; }
    var v = view();
    if (v.amp < 0.5 || v.p < 1) { S.say('The loops are not sharp yet (sharpness ' + v.amp.toFixed(2) + '). Adjust the load by 0.1 g until they are widest and steadiest.'); return; }
    if (S.rows.some(function (r) { return r.p === v.p; })) { S.say('You already have a reading with ' + v.p + ' loops. Find a different number of loops.'); return; }
    S.addRow({ M: mass(), p: v.p }); S.say('Written: ' + v.p + ' loops with M = ' + g1(mass()) + ' g.');
  }
  function fOne(r) { return KF * (r.p / L) * Math.sqrt(r.M * p.g / muMeas); }
  function seek(pwant) {                                      // the same moves as the student: bring the load near, then trim by 0.1 g to the sharpest loops
    var T0 = p.mu * Math.pow(2 * L * K.fs(p) / pwant, 2), m0 = T0 / p.g, best = m0, bs = -1, i;
    setLoad(Math.round(m0 * 1000) / 1000); var cur = mass();
    for (i = -6; i <= 6; i++) { var m = Math.round((cur + i * 0.0001) * 1e4) / 1e4; setLoad(m); var v = view(); if (v.p === pwant && v.amp > bs) { bs = v.amp; best = m; } }
    setLoad(best);
  }
  function setPan() { setHang(); }
  var steps = [
      { id: 'setup', title: 'Set up', view: 'thread', render: function (u) {
          u.h2('Weigh the thread, measure l, start the fork');
          u.task('1. Weigh the thread', st.mu, st.mu ? 'μ = ' + (muMeas * 1000).toFixed(3) + ' g/m' : 'Weigh 2.00 m of the thread on a balance')
            .add(u.button(st.mu ? 'Weighed' : 'Weigh the thread', weighThread, !st.mu, st.mu));
          u.task('2. Measure the length l', st.len, st.len ? 'l = ' + (L * 100).toFixed(1) + ' cm' : 'Fork to pulley, along the metre scale')
            .add(u.button(st.len ? 'Measured' : 'Measure l', measureLen, !st.len, st.len));
          u.task('3. Switch the fork on', st.fork, st.fork ? 'Humming' : 'The hand presses the switch')
            .add(u.button(st.fork ? 'On' : 'Switch the fork on', function () { forkOn(); }, st.mu && st.len && !st.fork, st.fork || S.hand.busy));
          u.note('The fork is stamped with no number: that is what you are finding.');
          u.next('Next: find the loops', st.mu && st.len && st.fork);
        },
        ok: function () { return st.mu && st.len && st.fork; },
        auto: function () { weighThread(); measureLen(); return forkOn(); } },
      { id: 'loops', title: 'Loops', view: 'pan', render: function (u) {
          u.h2('Find loads that give sharp loops');
          u.p('Start heavy (100 g) and lighten the pan. At certain loads the thread shakes in a whole number of wide, steady loops. Trim by 0.1 g to make them widest, then mark. Find three different numbers of loops.');
          u.live(function () { var v = view(); return 'Load M = ' + g1(mass()) + ' g · ' + (v.amp >= 0.5 ? v.p + ' loops, sharpness ' + v.amp.toFixed(2) : 'no steady loops (sharpness ' + v.amp.toFixed(2) + ')'); });
          u.slider('Load M', PAN * 1000 + 1, 200, 0.1, function () { return mass() * 1000; }, function (v) { setLoad(v / 1000); }, 'g', 1);
          u.row(u.button('−5 g', function () { addLoad(-0.005, true); }, false, S.hand.busy), u.button('−1 g', function () { addLoad(-0.001, true); }, false, S.hand.busy),
            u.button('+1 g', function () { addLoad(0.001, true); }, false, S.hand.busy), u.button('+5 g', function () { addLoad(0.005, true); }, false, S.hand.busy));
          u.row(u.button('−0.1 g', function () { addLoad(-0.0001, false); }, false, false), u.button('+0.1 g', function () { addLoad(0.0001, false); }, false, false),
            u.button('Mark these loops', mark, true, false));
          u.h3('Observation table'); u.table();
          u.next('Next: work out f', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' reading(s) so far. Find 3 different numbers of loops.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () { for (var i = -1; i <= 1; i++) { seek(P0 + i); mark(); } return Promise.resolve(); } },
  ];

  return {
    camera: { pos: [-0.15, 0.5, 2.1], look: [-0.15, 0.12, -0.2] },
    views: { thread: [[-0.2, 0.35, 0.6], [-0.15, 0.2, ZT]], fork: [[-0.75, 0.3, 0.3], [XF - 0.1, 0.1, ZT]], pulley: [[0.25, 0.3, 0.3], [XP, 0.18, ZT]], pan: [[0.35, 0.3, 0.35], [XP + 0.02, 0.1, ZT]], scale: [[-0.1, 0.3, 0.45], [-0.1, 0.14, ZT - 0.05]],
      cell: [[-0.8, 0.25, 0.3], [XF - 0.3, 0.03, ZT]], sw: [[-0.5, 0.4, 0.5], [-1.1, 0.05, -0.2]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A thread stretched between a vibrating fork and a pulley carries waves at v = √(T/μ). When the fork\'s waves and their reflections fit the thread in a whole number of loops, a standing wave forms and the loops are large and steady.',
      formula: LONG ? 'f = (p / 2l) √(T / μ)' : 'f = (p / l) √(T / μ)',
      formulaNote: LONG ? 'Fork along the thread: the thread vibrates at the fork frequency f. The loop length l/p = λ/2, so λ = 2l/p and f = v/λ.' : 'Fork across the thread: the thread vibrates at f/2 because the thread goes through one cycle for two of the prong. The loop length l/p = λ/2 with λ = v / (f/2), giving f = (p / l) √(T/μ).',
      more: ['T = M g, M the whole load including the 5 g pan. Doubling the load makes the wave 1.41 times faster, so λ is longer and fewer loops fit: p² T is constant.'],
      precautions: 'Keep the thread horizontal and the pulley smooth. Keep the weights still while you count loops. Find the sharpest loops by changing the load a little at a time, from both sides. Measure l from the fork tip to the pulley.' },
    book: { title: 'Expt. — Melde\'s experiment', lines: bookLines,
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'M (g)', get: function (r) { return g1(r.M); } }, { label: 'p', get: function (r) { return String(r.p); } },
        { label: 'T (N)', get: function (r) { return (r.M * p.g).toFixed(3); } }, { label: 'f (Hz)', get: function (r) { return fOne(r).toFixed(1); } }] },
    graph: { x: function (r) { return 1 / (r.p * r.p); }, y: function (r) { return r.M * p.g; }, xlabel: '1 / p²', ylabel: 'T (N)', x0: 0, y0: 0,
      line: function () { return function (x) { return 4 * muMeas * Math.pow(L * K.fs(p), 2) * x; }; } },
    result: function (rows) { if (!rows.length) return null; var s = 0; rows.forEach(function (r) { s += fOne(r); });
      return { label: 'f (fork)', value: s / rows.length, unit: 'Hz', digits: 1, truth: p.f, note: 'Mean of ' + rows.length + ' readings; ' + (LONG ? 'longitudinal' : 'transverse') + ' arrangement. T against 1/p² is a straight line through the origin.' }; },
    tol: 0.02,
    chips: ['Why do the loops appear only at certain loads?', 'Why is the thread at half the fork frequency?', 'Why does a bigger load give fewer loops?', 'Check my readings', 'Why is my f different?'],
    viva: [[LONG ? 'In the longitudinal arrangement the thread vibrates at' : 'In the transverse arrangement the thread vibrates at', LONG ? ['the frequency of the fork', 'half the frequency of the fork', 'twice the frequency of the fork'] : ['half the frequency of the fork', 'the frequency of the fork', 'twice the frequency of the fork'], 0, LONG ? 'The fork pulls the thread along its length once for each cycle of the fork.' : 'The prong goes through one cycle while the thread goes through half of one: a loop forms for every two vibrations of the fork.'],
      ['If the load is made four times larger, the number of loops', ['halves', 'doubles', 'stays the same'], 0, 'v = √(T/μ) doubles, so the wavelength doubles and half as many loops fit.']],
    askState: function () { var v = view(); return { fork_on: st.fork, load_g: +g1(mass()), loops_standing: v.amp >= 0.5 ? v.p : 0, sharpness: +v.amp.toFixed(2), arrangement: LONG ? 'longitudinal' : 'transverse', length_cm: st.len ? +(L * 100).toFixed(1) : null, mu_g_per_m: st.mu ? +(muMeas * 1000).toFixed(3) : null, readings: S.rows.length }; },
    steps: steps,

    tick: function (dt) {
      st.clock += dt; var v = view(), target = st.fork ? v.amp : 0; st.shown += (target - st.shown) * Math.min(1, dt * 6);
      var A = st.fork ? 0.0015 + 0.021 * st.shown : 0, ph = st.clock * 7.5, pp = Math.max(1, v.p);
      var amp = pp > 0 ? A : 0, i, x, sh;
      for (i = 0; i <= N; i++) { x = i / N; sh = Math.sin(pp * Math.PI * x); var y = YT;                                       // the thread runs level from the fork tip to the top of the pulley
        var dy = amp * sh * Math.cos(ph); tpos[i * 3] = XF + x * L; tpos[i * 3 + 1] = y + dy; tpos[i * 3 + 2] = ZT;
        epos[i * 6] = XF + x * L; epos[i * 6 + 1] = y + amp * Math.abs(sh); epos[i * 6 + 2] = ZT; epos[i * 6 + 3] = XF + x * L; epos[i * 6 + 4] = y - amp * Math.abs(sh); epos[i * 6 + 5] = ZT; }
      tgeo.attributes.position.needsUpdate = true; egeo.attributes.position.needsUpdate = true; env.visible = st.shown > 0.05;
      thickT.visible = st.shown < 0.05;
      var vib = st.fork ? Math.sin(st.clock * 40) * 0.0015 : 0; pr1.position.y = (LONG ? 0.16 : 0.07 + vib * 1); if (!LONG) pr2.position.y = 0.05 - vib; else { pr1.position.x = XF - 0.012 + vib; pr2.position.x = XF - 0.036 - vib; }
      hudM.set(g1(mass()) + ' g'); hudP.set(v.amp >= 0.5 ? String(v.p) : '—'); hudA.set(v.amp.toFixed(2));
    },
  };
});
