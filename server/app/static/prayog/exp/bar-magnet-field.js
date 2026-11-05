/* Prayogshala studio rig: the bar magnet bench (NCERT Science VI "Fun with Magnets" and Class X magnetism).
   One bench with a plotting board, bar magnets, a plotting compass, an electronic balance and a stirrup hanging on
   a torsionless thread serves four set-ups: plotting the field and its neutral points, the force between like poles,
   a suspended magnet settling north-south, and a strip magnetised by stroking. Every number comes from the
   `barmagnet` kernel of packs/em_school.js - two poles, added as vectors, and the real equation of motion. */
HoolaStudio.define('bar-magnet-field', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KB = HK.K.barmagnet;
  var p = HK.paramsFor('barmagnet', S.lab.params);
  var V_ = S.lab.variant || {}, BASE = V_.base || S.lab.id, SAMPLE = V_.sample || '';
  var MODE = BASE === 'like-unlike-poles' ? 'force' : (BASE === 'suspended-magnet-direction' || BASE === 'make-a-magnet-stroking') ? 'swing' : 'plot';
  var STROKE = BASE === 'make-a-magnet-stroking';
  var MU0 = 4e-7 * Math.PI, BH = p.BH, LB = p.Lbar, HALF = LB / 2;
  var D0 = p.dnp, DF0 = p.d;
  var NOSC = 20;                                            // oscillations timed in one trial (long swings: fewer)
  var sim = KB.init(p), theta = p.theta0, prevTh = p.theta0;
  var st = { d: D0, df: DF0, target: D0, targetF: DF0, aligned: false, zero: false, running: false,
    osc: 0, started: false, strokes: 0, released: false, lastT: 0, trials: 0, tanB: false };
  function solve() { p.dnp = st.d; p.d = st.df; }
  function Beq(d) { var q = p.m / LB, r = Math.sqrt(HALF * HALF + d * d); return MU0 * q * LB / (4 * Math.PI * r * r * r); }
  function force(d) { return KB.force(p, d); }
  function degRead(d) { return Math.round(Math.atan(Beq(d) / BH) * 180 / Math.PI / 0.5) * 0.5; }
  function gramRead(d) { return Math.round(force(d) / 9.8 * 1000 / 0.1) * 0.1; }
  function fmtN(v, d) { return String(+v.toFixed(d === undefined ? 2 : d)); }
  var PERIOD = 2 * Math.PI * Math.sqrt(KB.inertia(p) / (p.m * BH));
  if (PERIOD > 4) NOSC = 10;

  // ---------- the bench: a plotting board with a drawing sheet
  var WX = 0.0, WZ = -0.22;
  var stage = S.rounded(0.96, 0.52, 0.016, 0.006, M.darkWood); stage.rotation.x = -Math.PI / 2; stage.position.set(WX, 0.008, WZ); S.scene.add(stage);
  S.contact(1.02, 0.58, WX, WZ, 0.45);
  var sheetTex = S.canvasTex(1400, 760, function (x, w, h) {
    x.fillStyle = '#f9f6ec'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(60,70,90,.22)'; x.lineWidth = 1.5;
    for (var i = 1; i < 28; i++) { x.beginPath(); x.moveTo(i * w / 28, 0); x.lineTo(i * w / 28, h); x.stroke(); }
    for (var j = 1; j < 15; j++) { x.beginPath(); x.moveTo(0, j * h / 15); x.lineTo(w, j * h / 15); x.stroke(); }
    x.strokeStyle = 'rgba(40,60,110,.5)'; x.lineWidth = 3;
    x.beginPath(); x.moveTo(0, h / 2); x.lineTo(w, h / 2); x.stroke();
    x.beginPath(); x.moveTo(w / 2, 0); x.lineTo(w / 2, h); x.stroke();
    x.fillStyle = '#2b3a55'; x.font = '700 42px "Public Sans", sans-serif'; x.textAlign = 'center';
    x.fillText('N', w / 2, 50); x.fillText('S', w / 2, h - 16);
    x.textAlign = 'left'; x.fillText('W', 14, h / 2 - 16); x.textAlign = 'right'; x.fillText('E', w - 14, h / 2 - 16);
  });
  var sheet = new T.Mesh(new T.PlaneGeometry(0.9, 0.46), new T.MeshStandardMaterial({ map: sheetTex, roughness: 0.85 }));
  sheet.rotation.x = -Math.PI / 2; sheet.position.set(WX, 0.0165, WZ); S.scene.add(sheet);

  // ---------- a bar magnet, built once and used wherever it is needed
  function barMagnet(len, wid, red, blue) {
    var g = new T.Group();
    var rm = new T.MeshStandardMaterial({ color: red || 0xc8312a, roughness: 0.35, metalness: 0.25 });
    var bm = new T.MeshStandardMaterial({ color: blue || 0x2457b5, roughness: 0.35, metalness: 0.25 });
    var hN = S.rounded(len / 2, wid, wid, 0.0012, rm); hN.position.x = len / 4; g.add(hN);
    var hS = S.rounded(len / 2, wid, wid, 0.0012, bm); hS.position.x = -len / 4; g.add(hS);
    [['N', len / 2 - 0.008, '#ffffff'], ['S', -len / 2 + 0.008, '#ffffff']].forEach(function (q) {
      var l = S.label(q[0], { w: 0.009, ratio: 1, color: q[2], weight: 800 });
      l.rotation.x = -Math.PI / 2; l.position.set(q[1], wid / 2 + 0.0004, 0); g.add(l);
    });
    return g;
  }
  var mag = barMagnet(LB, p.wbar);
  var magShown = MODE !== 'swing';
  S.scene.add(mag);
  mag.position.set(WX, 0.0165 + p.wbar / 2, WZ);
  if (MODE === 'plot') mag.rotation.y = Math.PI / 2;      // first position: the magnet's axis lies along north-south
  mag.visible = magShown;
  if (magShown) S.contact(LB + 0.02, p.wbar + 0.02, WX, WZ, 0.3, 0.0168);

  // ---------- plotting compass
  var comp = new T.Group(); S.scene.add(comp);
  comp.add((function () { var b = S.mesh(new T.CylinderGeometry(0.024, 0.026, 0.011, 36), M.brass); b.position.y = 0.0055; return b; })());
  var dialTex = S.canvasTex(512, 512, function (x, w, h) {
    x.fillStyle = '#f8f5ec'; x.fillRect(0, 0, w, h);
    var cx = w / 2, cy = h / 2, R = w * 0.44;
    x.strokeStyle = '#1b1b1b'; x.fillStyle = '#1b1b1b';
    for (var i = 0; i < 360; i += 2) {
      var a = i * Math.PI / 180, big = i % 10 === 0;
      x.lineWidth = big ? 2.6 : 1.2; x.beginPath();
      x.moveTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R);
      x.lineTo(cx + Math.cos(a) * (R - (big ? 26 : 12)), cy + Math.sin(a) * (R - (big ? 26 : 12))); x.stroke();
    }
    x.font = '700 30px "Public Sans", sans-serif'; x.textAlign = 'center';
    [[270, 'N'], [0, 'E'], [90, 'S'], [180, 'W']].forEach(function (q) {
      var a = q[0] * Math.PI / 180; x.fillText(q[1], cx + Math.cos(a) * (R - 52), cy + Math.sin(a) * (R - 52) + 10);
    });
  });
  var dial = new T.Mesh(new T.CircleGeometry(0.0225, 48), new T.MeshStandardMaterial({ map: dialTex, roughness: 0.7 }));
  dial.rotation.x = -Math.PI / 2; dial.position.y = 0.0115; comp.add(dial);
  var ndl = new T.Group(); ndl.position.y = 0.0125; comp.add(ndl);
  ndl.add((function () { var m = S.mesh(new T.BoxGeometry(0.0015, 0.0008, 0.018), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.4 }), false); m.position.z = -0.009; return m; })());
  ndl.add((function () { var m = S.mesh(new T.BoxGeometry(0.0015, 0.0008, 0.018), new T.MeshStandardMaterial({ color: 0xe8e8ea, roughness: 0.4 }), false); m.position.z = 0.009; return m; })());
  ndl.add(S.mesh(new T.CylinderGeometry(0.0014, 0.0014, 0.002, 12), M.chrome, false));
  comp.add((function () { var g = new T.Mesh(new T.CircleGeometry(0.0245, 36), M.glass); g.rotation.x = -Math.PI / 2; g.position.y = 0.0135; return g; })());
  // the compass always sits on the magnet's EQUATORIAL line: east of it while the magnet points north (neutral
  // points), north of it once the magnet has been turned east-west (the deflection, or tan B, position)
  function compAt(d) { return st.tanB ? new T.Vector3(WX, 0.0165, WZ - d) : new T.Vector3(WX + d, 0.0165, WZ); }
  comp.position.copy(compAt(MODE === 'plot' ? D0 : 0.33));

  // ---------- force mode: the second magnet on an electronic balance
  var bal = null, mag2 = null;
  if (MODE === 'force') {
    bal = new T.Group(); S.scene.add(bal); bal.position.set(WX + 0.3, 0.0165, WZ);
    var bbody = S.rounded(0.15, 0.13, 0.03, 0.006, new T.MeshStandardMaterial({ color: 0x2f3338, roughness: 0.55 }));
    bbody.rotation.x = -Math.PI / 2; bbody.position.y = 0.015; bal.add(bbody);
    var pan = S.mesh(new T.CylinderGeometry(0.05, 0.05, 0.003, 36), M.chrome); pan.position.y = 0.032; bal.add(pan);
    var blcd = S.liveTex(512, 180), lastB = '';
    var bm2 = new T.Mesh(new T.PlaneGeometry(0.075, 0.026), new T.MeshBasicMaterial({ map: blcd, toneMapped: false }));
    bm2.rotation.x = -Math.PI / 2 + 0.6; bm2.position.set(0, 0.031, 0.056); bal.add(bm2);
    bal.userData.draw = function (grams) {
      var txt = grams.toFixed(1); if (txt === lastB) return; lastB = txt;
      blcd.draw(function (x, w, h) {
        var g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#b9c4a7'); g.addColorStop(1, '#9eab8b');
        x.fillStyle = g; x.fillRect(0, 0, w, h);
        x.fillStyle = '#1b2116'; x.textAlign = 'right'; x.font = '700 92px "JetBrains Mono", monospace';
        x.fillText(txt, w - 86, 128); x.font = '600 40px "Public Sans", sans-serif'; x.fillText('g', w - 20, 128);
        x.textAlign = 'left'; x.font = '600 26px "Public Sans", sans-serif'; x.fillText('BALANCE  0.1 g', 16, 40);
      });
    };
    bal.userData.draw(0);
    S.contact(0.19, 0.17, WX + 0.3, WZ, 0.45);
    mag2 = barMagnet(LB, p.wbar); S.scene.add(mag2);
    mag2.position.set(WX + st.df, 0.0165 + 0.034 + p.wbar / 2, WZ);
    mag2.rotation.y = Math.PI;                                   // N pole of the second magnet faces the first
  }

  // ---------- swing mode: a stirrup on a torsionless thread, and a stopwatch
  var swing = null, stirrup = null, watch = null, strip = null;
  if (MODE === 'swing') {
    S.stand({ x: WX - 0.3, z: WZ - 0.12, h: 0.78, armY: 0.72, armLen: 0.26 });
    var arm = S.mesh(new T.BoxGeometry(0.3, 0.012, 0.012), M.chrome); arm.position.set(WX - 0.36, 0.72, WZ - 0.12); S.scene.add(arm);
    var hook = S.mesh(new T.TorusGeometry(0.006, 0.0012, 8, 16), M.chrome); hook.position.set(WX - 0.22, 0.714, WZ - 0.12); hook.rotation.x = Math.PI / 2; S.scene.add(hook);
    var THY = 0.3;                                               // the magnet hangs this high above the bench
    var thread = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.714 - THY, 6), new T.MeshStandardMaterial({ color: 0xe8e2d2, roughness: 0.9 }));
    thread.position.set(WX - 0.22, (0.714 + THY) / 2, WZ - 0.12); S.scene.add(thread);
    swing = new T.Group(); S.scene.add(swing); swing.position.set(WX - 0.22, THY, WZ - 0.12);
    stirrup = new T.Group(); swing.add(stirrup);
    [[-1], [1]].forEach(function (q) {
      var side = S.mesh(new T.BoxGeometry(0.0015, 0.03, 0.0015), M.chrome); side.position.set(0, 0.015, q[0] * (p.wbar / 2 + 0.003)); stirrup.add(side);
    });
    var cradle = S.mesh(new T.BoxGeometry(LB * 0.6, 0.0015, p.wbar + 0.008), M.chrome); stirrup.add(cradle);
    var hung = barMagnet(LB, p.wbar, STROKE ? 0x8d9095 : 0xc8312a, STROKE ? 0x76797e : 0x2457b5);
    hung.position.y = p.wbar / 2 + 0.001; stirrup.add(hung);
    var top = S.mesh(new T.CylinderGeometry(0.0016, 0.0016, 0.004, 10), M.chrome); top.position.y = 0.031; stirrup.add(top);
    watch = S.stopwatch([WX + 0.3, 0.0165, WZ + 0.08], [0, -0.25, 0]);
    if (STROKE) {
      strip = barMagnet(LB, p.wbar, 0x8d9095, 0x76797e);
      S.scene.add(strip); strip.position.set(WX + 0.1, 0.0165 + p.wbar / 2, WZ - 0.12);
      S.contact(LB + 0.02, p.wbar + 0.02, WX + 0.1, WZ - 0.12, 0.3, 0.0168);
      mag.visible = true; mag.position.set(WX + 0.1, 0.0165 + p.wbar / 2 + p.wbar + 0.004, WZ + 0.02);
      mag.rotation.y = 0; magShown = true;
    }
  }

  S.addApparatus('mag', MODE === 'swing' ? swing : mag, STROKE ? 'Bar magnet (for stroking)' : 'Bar magnet',
    'Red end N, blue end S. Its magnetic moment is the quantity this experiment finds.');
  if (MODE !== 'swing') S.addApparatus('comp', comp, 'Plotting compass',
    'Its needle sets itself along the resultant of the earth’s horizontal field and the magnet’s field, so tan(deflection) = B / B_H.');
  if (MODE === 'force') S.addApparatus('bal', bal, 'Electronic balance (0.1 g)', 'The second magnet stands on the pan. The reading is the push of one magnet on the other, in grams.');
  if (MODE === 'swing') {
    S.addApparatus('swing', swing, 'Magnet in a stirrup', 'Hung on a fresh untwisted thread so the only couple on it is the earth’s field.');
    S.addApparatus('watch', watch.group, 'Stopwatch', 'Times ' + NOSC + ' complete oscillations; dividing gives the period.');
    if (STROKE) S.addApparatus('strip', strip, 'Iron strip', 'An ordinary iron strip. Stroked the same way again and again, it becomes a magnet itself.');
  }
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hud1 = S.hudCard(MODE === 'force' ? 'Separation' : MODE === 'swing' ? 'Oscillations' : 'Compass at');
  var hud2 = S.hudCard(MODE === 'force' ? 'Balance' : MODE === 'swing' ? 'Stopwatch' : 'Deflection');
  var hud3 = S.hudCard(MODE === 'force' ? 'Force' : MODE === 'swing' ? 'Angle' : 'Magnet’s field');
  solve();

  // ---------- actions
  function align() {
    st.aligned = true;
    S.focus(MODE === 'swing' ? 'swing' : 'mag');
    S.say(MODE === 'plot' ? 'The sheet is turned until the compass needle lies along the printed north-south line, and the magnet is laid east-west across the centre.'
      : MODE === 'force' ? 'Both magnets lie along the same line with their N poles facing each other, and the balance is set to zero with the second magnet on the pan.'
        : 'The thread is fresh and untwisted, and the magnet in the stirrup has settled along north-south: that line is the magnetic meridian.');
    S.render();
  }
  function zeroCheck() {
    st.zero = true;
    S.say(MODE === 'force' ? 'With the first magnet far away the balance reads 0.0 g: the tare is taken.'
      : MODE === 'swing' ? 'The stopwatch is reset to zero.' : 'With the magnet taken away the needle rests on north-south: there is no other magnet near the bench.');
    if (MODE === 'swing' && watch) { watch.t = 0; watch.on = false; }
    S.render();
  }
  function turnMagnet(toTanB) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!!toTanB === st.tanB) return Promise.resolve();
    var a0 = mag.rotation.y, a1 = toTanB ? 0 : Math.PI / 2, dOld = st.d;
    return S.hand.pinchMove(new T.Vector3(WX + LB / 2, 0.0165 + p.wbar, WZ),
      function (k) { var a = a0 + (a1 - a0) * k; return new T.Vector3(WX + Math.cos(a) * LB / 2, 0.0165 + p.wbar, WZ - Math.sin(a) * LB / 2); },
      function (k) { mag.rotation.y = a0 + (a1 - a0) * k; }, { ms: 800, mode: 'top' })
      .then(function () {
        mag.rotation.y = a1; st.tanB = !!toTanB; st.d = dOld; comp.position.copy(compAt(st.d));
        ndl.rotation.y = 0;
        S.say(toTanB ? 'The magnet has been turned east-west, and the compass moved round to the north of it. It is still on the magnet\u2019s equatorial line, but now the magnet\u2019s field there is across the earth\u2019s, so the needle turns through a measurable angle.'
          : 'The magnet points north again.');
        S.render();
      });
  }
  function moveCompass(d) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    d = Math.max(0.06, Math.min(0.34, d)); st.target = d;
    var d0 = st.d; if (Math.abs(d - d0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(compAt(d0).add(new T.Vector3(0, 0.014, 0)),
      function (k) { return compAt(d0 + (d - d0) * k).add(new T.Vector3(0, 0.014, 0)); },
      function (k) { st.d = d0 + (d - d0) * k; comp.position.copy(compAt(st.d)); solve(); },
      { ms: 700, mode: 'top' }).then(function () { st.d = d; comp.position.copy(compAt(d)); solve(); S.render(); });
  }
  function moveMagnet2(d) {
    if (!mag2) return Promise.resolve();
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    d = Math.max(LB + 0.008, Math.min(0.18, d)); st.targetF = d;
    var d0 = st.df; if (Math.abs(d - d0) < 1e-9) return Promise.resolve();
    function at(x) { return new T.Vector3(WX + x, 0.0165 + 0.034 + p.wbar / 2, WZ); }
    return S.hand.pinchMove(at(d0).add(new T.Vector3(0, p.wbar, 0)),
      function (k) { return at(d0 + (d - d0) * k).add(new T.Vector3(0, p.wbar, 0)); },
      function (k) { st.df = d0 + (d - d0) * k; mag2.position.copy(at(st.df)); solve(); },
      { ms: 800, mode: 'top' }).then(function () { st.df = d; mag2.position.copy(at(d)); solve(); S.render(); });
  }
  function stroke() {
    if (!STROKE) return Promise.resolve();
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    var y0 = 0.0165 + p.wbar / 2 + p.wbar + 0.004, z0 = WZ - 0.12;
    function at(k) { return new T.Vector3(WX + 0.1 - LB / 2 + LB * k, y0 + 0.004 * (k > 0.98 ? 1 : 0), z0); }
    return S.hand.pinchMove(at(0).add(new T.Vector3(0, p.wbar, 0)),
      function (k) { return at(k).add(new T.Vector3(0, p.wbar, 0)); },
      function (k) { mag.position.copy(at(k)); }, { ms: 900, mode: 'top' })
      .then(function () {
        st.strokes += 10; mag.position.set(WX + 0.1 - LB / 2, y0, z0);
        S.say('Ten more strokes, always from one end to the other and lifted clear on the way back. ' + st.strokes + ' strokes so far.');
        S.render();
      });
  }
  function hangStrip() {
    if (!STROKE) return Promise.resolve();
    if (st.strokes < 30) { S.say('Stroke the strip at least thirty times first: fewer strokes leave it barely magnetised.'); return Promise.resolve(); }
    st.released = true; S.focus('swing');
    S.say('The stroked strip is hung in the stirrup, and it settles along north-south: it has become a magnet.');
    S.render(); return Promise.resolve();
  }
  function startSwing() {
    if (st.running) { S.say('A set of oscillations is already being timed.'); return Promise.resolve(); }
    if (STROKE && !st.released) { S.say('Hang the stroked strip in the stirrup first.'); return Promise.resolve(); }
    sim = KB.init(p); theta = p.theta0; prevTh = p.theta0; st.osc = 0; st.started = false; watch.t = 0;
    return S.hand.tap(watch.start).then(function () {
      st.running = true; watch.on = true;
      S.say('The magnet is turned a little way and let go. The stopwatch is started as it swings through the middle, and ' + NOSC + ' oscillations are counted from there.');
      S.render();
    });
  }
  function stopSwing() {
    if (!st.running) return Promise.resolve();
    st.running = false; watch.on = false; st.lastT = watch.t;
    return S.hand.tap(watch.start).then(function () {
      S.say(NOSC + ' oscillations took ' + watch.t.toFixed(2) + ' s, so the period is ' + (watch.t / NOSC).toFixed(3) + ' s.');
      S.render();
    });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (S.rows.length >= 12) { S.say('Twelve readings are plenty. Go on to the result.'); return false; }
    if (MODE === 'plot') {
      if (!st.tanB) { S.say('Turn the magnet east-west first: on this line a magnet pointing north gives no deflection at all, only a neutral point.'); return false; }
      var th = degRead(st.d);
      if (th < 6) { S.say('The deflection is too small to read here. Bring the compass nearer the magnet.'); return false; }
      if (th > 75) { S.say('The needle is nearly across the dial: at more than 75° tan θ cannot be read accurately. Move the compass further away.'); return false; }
      if (S.rows.some(function (r) { return Math.abs(r.d - st.d) < 0.004; })) { S.say('There is already a reading at this distance. Move the compass.'); return false; }
      S.addRow({ d: st.d, th: th });
      S.say('Written in your record book: d = ' + (st.d * 100).toFixed(1) + ' cm, deflection = ' + th.toFixed(1) + '°.');
      return true;
    }
    if (MODE === 'force') {
      var gr = gramRead(st.df);
      if (gr < 0.5) { S.say('The balance barely moves at this separation. Bring the magnets nearer.'); return false; }
      if (S.rows.some(function (r) { return Math.abs(r.d - st.df) < 0.004; })) { S.say('There is already a reading at this separation. Move the magnet.'); return false; }
      S.addRow({ d: st.df, g: gr });
      S.say('Written in your record book: separation ' + (st.df * 100).toFixed(1) + ' cm, balance ' + gr.toFixed(1) + ' g.');
      return true;
    }
    if (st.running) { S.say('Stop the stopwatch first.'); return false; }
    if (st.lastT <= 0) { S.say('Time a set of oscillations first.'); return false; }
    S.addRow({ n: ++st.trials, t: +st.lastT.toFixed(2) });
    st.lastT = 0;
    S.say('Written in your record book: trial ' + st.trials + ', ' + NOSC + ' oscillations.');
    return true;
  }
  var NEED = MODE === 'swing' ? 3 : 4;

  // ---------- the result, worked out exactly as the student would
  function momentFromRows(rows) {
    if (MODE === 'plot') {
      return S.fit.mean(rows.map(function (r) {
        var B = BH * Math.tan(r.th * Math.PI / 180), rr = Math.sqrt(HALF * HALF + r.d * r.d);
        return B * 4 * Math.PI * rr * rr * rr / MU0;
      }));
    }
    if (MODE === 'force') {
      return S.fit.mean(rows.map(function (r) {
        var F = r.g * 9.8 / 1000, d = r.d;
        var br = 1 / Math.pow(d - LB, 2) - 2 / (d * d) + 1 / Math.pow(d + LB, 2);
        return Math.sqrt(F * 4 * Math.PI / (MU0 * br)) * LB;                       // q_m = sqrt(...), m = q_m × 2l
      }));
    }
    return S.fit.mean(rows.map(function (r) {
      var Tp = r.t / NOSC;
      return 4 * Math.PI * Math.PI * KB.inertia(p) / (Tp * Tp * BH);
    }));
  }

  // four distances spread over the part of the range where the instrument reads well (every magnet is different)
  function goodD(lo, hi, ok) {
    var step = 0.005, all = [], d;
    for (d = lo; d <= hi + 1e-9; d += step) { var dd = Math.round(d / step) * step; if (ok(dd)) all.push(dd); }
    if (all.length < 4) { return [lo, lo + (hi - lo) / 3, lo + 2 * (hi - lo) / 3, hi].map(function (x) { return Math.round(x / step) * step; }); }
    var out = [], n = all.length;
    for (var k = 0; k < 4; k++) out.push(all[Math.round(k * (n - 1) / 3)]);
    return out;
  }

  var steps = [
    { id: 'set', title: 'Set the apparatus up', view: 'work', render: function (u) {
        u.h2(MODE === 'plot' ? 'Line the sheet up with north' : MODE === 'force' ? 'Line the two magnets up' : 'Hang the magnet');
        u.p(MODE === 'plot' ? 'The compass needle must lie along the printed north-south line before anything else is done; then the magnet is laid across the centre, east-west.'
          : MODE === 'force' ? 'One magnet is fixed on the sheet; the second stands on the balance pan with its N pole facing the first magnet’s N pole.'
            : 'The magnet hangs in a light stirrup on a fresh untwisted thread, so nothing but the earth’s field can turn it.');
        u.task('1. ' + (MODE === 'plot' ? 'Line up the sheet' : MODE === 'force' ? 'Line up the magnets' : 'Let it settle'), st.aligned,
          st.aligned ? 'Done' : 'Not yet').add(u.button(st.aligned ? 'Done' : 'Set it up', align, !st.aligned, st.aligned));
        u.task('2. ' + (MODE === 'force' ? 'Tare the balance' : MODE === 'swing' ? 'Reset the stopwatch' : 'Check for stray magnets'), st.zero,
          st.zero ? 'Zero checked' : 'Not yet').add(u.button(st.zero ? 'Checked' : 'Check the zero', zeroCheck, !st.zero, st.zero));
        u.note(MODE === 'swing' ? 'The magnet points north-south on its own. That is all a compass is: a magnet free to turn.'
          : 'Keep iron, other magnets and phones well away from the bench.');
        u.next('Next: ' + (MODE === 'plot' ? 'find the neutral points' : MODE === 'force' ? 'measure the push' : STROKE ? 'stroke the strip' : 'time the oscillations'),
          st.aligned && st.zero);
      },
      ok: function () { return st.aligned && st.zero; },
      auto: function () { align(); zeroCheck(); return Promise.resolve(); } }];

  if (MODE === 'plot') {
    steps.push({ id: 'neutral', title: 'Find a neutral point', view: 'comp', render: function (u) {
        u.h2('Where the two fields cancel');
        u.p('Slide the compass east along the line through the magnet’s centre. Near the magnet its field beats the earth’s and the needle points one way; '
          + 'far away the earth wins and it points north. Where they are equal the needle has no settled direction at all: that is a neutral point.');
        u.slider('Compass east of the centre', 0.06, 0.34, 0.005, function () { return st.target; }, function (v) { st.target = v; }, 'm', 3);
        u.row(u.button('Move the compass', function () { moveCompass(st.target); }, true, S.hand.busy));
        u.live(function () {
          var b = Beq(st.d);
          return 'd = ' + (st.d * 100).toFixed(1) + ' cm  ·  magnet’s field ' + (b * 1e6).toFixed(1) + ' µT  ·  earth’s ' + (BH * 1e6).toFixed(1) + ' µT  ·  deflection ' + degRead(st.d).toFixed(1) + '°';
        });
        u.note('The neutral points of this magnet lie about ' + (KB.measure(p).np_d * 100).toFixed(0) + ' cm from its centre, east and west.');
        u.next('Next: measure the deflections', true);
      },
      ok: function () { return true; },
      auto: function () { return moveCompass(0.2).then(function () { return moveCompass(D0); }); } });
  }

  steps.push({ id: 'read', title: MODE === 'swing' ? 'Time the oscillations' : 'Take the readings',
    view: MODE === 'force' ? 'bal' : MODE === 'swing' ? 'swing' : 'comp', render: function (u) {
      if (MODE === 'plot') {
        u.h2('Deflection at four distances');
        u.p('At each distance read how far the needle has turned from north. The compass is on the magnet’s equatorial line, so the magnet’s field is across the earth’s and tan θ = B / B_H.');
        u.task('Magnet turned east-west', st.tanB, st.tanB ? 'In the deflection position' : 'Still pointing north')
          .add(u.button(st.tanB ? 'Turned' : 'Turn the magnet east-west', function () { turnMagnet(true); }, !st.tanB, st.tanB || S.hand.busy));
        u.slider('Compass north of the centre', 0.06, 0.34, 0.005, function () { return st.target; }, function (v) { st.target = v; }, 'm', 3);
        u.row(u.button('Move the compass', function () { moveCompass(st.target); }, true, S.hand.busy),
          u.button('Record this reading', function () { record(); }, true, S.hand.busy || !st.tanB));
        u.live(function () { return 'd = ' + (st.d * 100).toFixed(1) + ' cm  ·  deflection ' + degRead(st.d).toFixed(1) + '°  ·  B = B_H tan θ = ' + (BH * Math.tan(degRead(st.d) * Math.PI / 180) * 1e6).toFixed(2) + ' µT'; });
      } else if (MODE === 'force') {
        u.h2('The push between like poles');
        u.p('Bring the fixed magnet nearer, N pole to N pole, and read the balance. The reading in grams times g is the force.');
        u.slider('Centre-to-centre separation', LB + 0.008, 0.18, 0.005, function () { return st.targetF; }, function (v) { st.targetF = v; }, 'm', 3);
        u.row(u.button('Move the magnet', function () { moveMagnet2(st.targetF); }, true, S.hand.busy),
          u.button('Record this reading', function () { record(); }, true, S.hand.busy));
        u.live(function () { return 'separation ' + (st.df * 100).toFixed(1) + ' cm  ·  balance ' + gramRead(st.df).toFixed(1) + ' g  ·  force ' + (force(st.df) * 1000).toFixed(1) + ' mN'; });
        u.note('Turn one magnet round and the balance reading changes sign: unlike poles pull instead of push.');
      } else {
        u.h2('Time ' + NOSC + ' oscillations');
        if (STROKE) {
          u.p('Stroke the iron strip from end to end with one pole of the bar magnet, always the same way, lifting the magnet clear on the way back. Thirty strokes are enough.');
          u.row(u.button('Stroke it ten times', function () { stroke(); }, true, S.hand.busy),
            u.button('Hang it in the stirrup', function () { hangStrip(); }, false, S.hand.busy || st.released || st.strokes < 30));
          u.live(function () { return st.strokes + ' strokes  ·  ' + (st.released ? 'hung in the stirrup' : 'on the bench'); });
        } else {
          u.p('Turn the magnet a little way from north and let it go. Start the stopwatch as it swings through the middle, count ' + NOSC + ' complete oscillations and stop it.');
        }
        u.row(u.button('Start: let it swing', function () { startSwing(); }, true, S.hand.busy || st.running),
          u.button('Stop the watch', function () { stopSwing(); }, false, S.hand.busy || !st.running),
          u.button('Record this trial', function () { record(); }, true, S.hand.busy || st.running || st.lastT <= 0));
        u.live(function () { return 'oscillations counted ' + st.osc + ' of ' + NOSC + '  ·  stopwatch ' + watch.t.toFixed(2) + ' s  ·  angle ' + (theta * 180 / Math.PI).toFixed(1) + '°'; });
      }
      u.h3('Observation table'); u.table();
      if (S.rows.length < NEED) u.p(S.rows.length + ' of at least ' + NEED + ' readings recorded.');
      u.next('Next: the result', S.rows.length >= NEED);
    },
    ok: function () { return S.rows.length >= NEED; },
    auto: function () {
      if (MODE === 'plot') {
        return goodD(0.06, 0.34, function (d) { var t = degRead(d); return t >= 12 && t <= 70; }).reduce(function (pr, d) {
          return pr.then(function () { return moveCompass(d).then(function () { S.advance(0.2); record(); }); });
        }, turnMagnet(true));
      }
      if (MODE === 'force') {
        return goodD(LB + 0.008, 0.18, function (d) { var g = gramRead(d); return g >= 2 && g <= 190; }).reduce(function (pr, d) {
          return pr.then(function () { return moveMagnet2(d).then(function () { S.advance(0.2); record(); }); });
        }, Promise.resolve());
      }
      var pre = Promise.resolve();
      if (STROKE) { pre = [1, 2, 3].reduce(function (pr) { return pr.then(stroke); }, Promise.resolve()).then(hangStrip); }
      return [1, 2, 3].reduce(function (pr) {
        return pr.then(function () {
          return startSwing().then(function () {
            S.advance(NOSC * PERIOD * 1.3, function () { return st.osc >= NOSC; });
            return stopSwing();
          }).then(function () { record(); });
        });
      }, pre);
    } });

  return {
    camera: { pos: [0.0, 1.14, 0.54], look: [0.0, 0.0, -0.2] },
    views: { mag: [[0.0, 0.46, 0.2], [0.0, 0.02, -0.2]], comp: [[WX + 0.1, 0.34, WZ + 0.16], [WX + 0.04, 0.02, WZ - 0.06]],
      bal: [[WX + 0.22, 0.3, WZ + 0.26], [WX + 0.18, 0.03, WZ]],
      swing: [[WX - 0.1, 0.44, WZ + 0.36], [WX - 0.22, 0.28, WZ - 0.12]],
      watch: [[WX + 0.3, 0.26, WZ + 0.3], [WX + 0.3, 0.02, WZ + 0.08]],
      strip: [[WX + 0.12, 0.26, WZ + 0.1], [WX + 0.1, 0.02, WZ - 0.12]],
      circuit: [[0.0, 1.14, 0.54], [0.0, 0.0, -0.2]], work: [[0.02, 0.72, 0.3], [0.0, 0.02, -0.22]],
      book: [[-0.5, 0.45, 0.6], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: MODE === 'plot'
        ? 'A bar magnet behaves as two poles of equal strength q_m at its ends. On its equatorial line - the line through its centre at right angles to its axis - '
          + 'its field is parallel to the axis, so with the magnet laid east-west the field at the compass is across the earth’s horizontal field and the needle turns through tan θ = B / B_H.'
        : MODE === 'force'
          ? 'Pole acts on pole with a force μ₀q₁q₂/4πr², repelling if the poles are alike. Two bar magnets face to face have four such pairs, and what the balance reads is their sum.'
          : 'The earth’s horizontal field exerts a couple m B_H sin θ on a magnet turned away from north, so it swings to and fro like a pendulum. '
            + (STROKE ? 'Stroking an iron strip always in one direction turns its domains the same way, and the strip becomes a magnet whose moment the swing measures.' : ''),
      formula: MODE === 'plot' ? 'B = μ₀m / 4π(d² + l²)^{3/2},   tan θ = B / B_H'
        : MODE === 'force' ? 'F = μ₀q_m²/4π [1/(d−2l)² − 2/d² + 1/(d+2l)²]'
          : 'T = 2π √(I / m B_H),   I = M(L² + b²)/12',
      formulaNote: MODE === 'swing' ? 'so the period gives the magnetic moment m' : 'so each reading gives the magnet’s moment m',
      more: [MODE === 'plot'
        ? 'Where the magnet’s field exactly cancels the earth’s the needle has no direction at all: that point is a neutral point, and it is the quickest way to see how strong the magnet is.'
        : MODE === 'force' ? 'The force falls away very fast indeed - much faster than 1/d² - because the far poles of the two magnets pull while the near poles push. That is why magnets seem to grab each other only at the last moment.'
          : 'Nothing but the earth’s field is turning the magnet, so the same experiment anywhere measures the product m B_H. Knowing B_H from a map gives m; knowing m gives B_H.'],
      precautions: 'Keep iron, other magnets, phones and steel rules away from the bench. Do not drop or heat a magnet: both shake its domains out of line and weaken it.' },
    book: { title: 'Expt. — ' + (MODE === 'plot' ? 'Field of a bar magnet' : MODE === 'force' ? 'Force between like poles' : STROKE ? 'Making a magnet by stroking' : 'A suspended magnet'),
      lines: ['Aim: ' + S.lab.aim].concat(SAMPLE ? ['Magnet: ' + SAMPLE] : [])
        .concat(['Magnet: ' + (LB * 100).toFixed(1) + ' cm long, ' + (p.mass * 1000).toFixed(0) + ' g',
          'B_H = ' + (BH * 1e6).toFixed(1) + ' µT (given)'])
        .concat(MODE === 'plot' ? ['Compass on the equatorial line', 'B = B_H tan θ', 'm = 4π B (d² + l²)^{3/2} / μ₀']
          : MODE === 'force' ? ['Balance reads in grams; F = (g reading) × 9.8 / 1000', 'Four pole pairs added']
            : [NOSC + ' oscillations timed', 'T = t / ' + NOSC, 'm = 4π² I / (T² B_H)']),
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }].concat(
        MODE === 'plot' ? [{ label: 'd (cm)', get: function (r) { return (r.d * 100).toFixed(1); } },
          { label: 'θ (°)', get: function (r) { return r.th.toFixed(1); } },
          { label: 'B (µT)', get: function (r) { return (BH * Math.tan(r.th * Math.PI / 180) * 1e6).toFixed(2); } }]
          : MODE === 'force' ? [{ label: 'd (cm)', get: function (r) { return (r.d * 100).toFixed(1); } },
            { label: 'Balance (g)', get: function (r) { return r.g.toFixed(1); } },
            { label: 'F (mN)', get: function (r) { return (r.g * 9.8).toFixed(1); } }]
            : [{ label: 'Trial', get: function (r) { return r.n; } },
              { label: 't for ' + NOSC + ' (s)', get: function (r) { return r.t.toFixed(2); } },
              { label: 'T (s)', get: function (r) { return (r.t / NOSC).toFixed(3); } }]) },
    graph: MODE === 'swing' ? null : { x: function (r) { return r.d * 100; },
      y: function (r) { return MODE === 'plot' ? BH * Math.tan(r.th * Math.PI / 180) * 1e6 : r.g * 9.8; },
      xlabel: 'd (cm)', ylabel: MODE === 'plot' ? 'B (µT)' : 'F (mN)', x0: 0, y0: 0 },
    result: function (rows) {
      if (rows.length < NEED) return null;
      var m = momentFromRows(rows);
      return { label: STROKE ? 'Moment given to the strip' : 'Magnetic moment of the magnet', value: m, unit: 'A·m²', digits: 3,
        truth: p.m, note: MODE === 'plot' ? 'From the mean of 4π B (d² + l²)^{3/2} / μ₀ over the readings.'
          : MODE === 'force' ? 'From the pole strength that fits the measured forces, times the magnet’s length.'
            : 'From the mean period: m = 4π² I / (T² B_H).' };
    },
    tol: 0.06,
    resultNote: MODE === 'plot' ? 'Every distance gave nearly the same moment, which is the test that the two-pole picture is right.'
      : MODE === 'force' ? 'The force fell off far faster than the distance grew: that is the signature of pole against pole.'
        : STROKE ? 'The stroked strip is a real magnet, but a far weaker one than the magnet that made it.' : '',
    chips: ['Why does the needle point north at all?', MODE === 'plot' ? 'What is a neutral point?' : MODE === 'force' ? 'Why do like poles repel?' : 'Why does the magnet swing to and fro?',
      'What is the magnetic meridian?', 'Check my readings', 'How can a magnet be weakened?'],
    viva: [[MODE === 'swing' ? 'The same magnet is taken where B_H is smaller. Its period' : 'The compass is moved twice as far from the magnet. Its deflection',
      MODE === 'swing' ? ['Grows', 'Falls', 'Does not change'] : ['Falls to much less than half', 'Doubles', 'Is unchanged'], 0,
      MODE === 'swing' ? 'T = 2π√(I/mB_H): a weaker field gives a slower swing.' : 'The field of a magnet falls as 1/d³ on the equatorial line.'],
    ['A bar magnet is cut in half across its middle. Each half is',
      ['A complete magnet with both poles', 'A single N pole', 'Not a magnet at all'], 0,
      'Poles always come in pairs: there is no such thing as a single magnetic pole.']],
    askState: function () {
      return { set_up: MODE === 'plot' ? 'bar magnet on a plotting sheet with a compass' : MODE === 'force' ? 'two magnets, like poles facing, on a balance'
        : STROKE ? 'an iron strip magnetised by stroking, hung in a stirrup' : 'a bar magnet hung in a stirrup',
        earth_field_uT: +(BH * 1e6).toFixed(1), magnet_length_cm: +(LB * 100).toFixed(1),
        compass_distance_cm: MODE === 'plot' ? +(st.d * 100).toFixed(1) : null,
        deflection_deg: MODE === 'plot' ? degRead(st.d) : null,
        separation_cm: MODE === 'force' ? +(st.df * 100).toFixed(1) : null,
        balance_g: MODE === 'force' ? gramRead(st.df) : null,
        oscillations_counted: MODE === 'swing' ? st.osc : null, stopwatch_s: MODE === 'swing' ? +watch.t.toFixed(2) : null,
        strokes_given: STROKE ? st.strokes : null, readings_taken: S.rows.length };
    },
    steps: steps,
    tick: function (dt) {
      solve();
      if (MODE === 'swing') {
        if (st.running) {
          KB.step(sim, p, dt);
          theta = sim.y[0];
          if (prevTh > 0 && theta <= 0) {                 // it is passing the middle one way
            if (!st.started) { st.started = true; watch.t = 0; }     // the watch is started here, not at the release
            else if (++st.osc >= NOSC) { st.running = false; watch.on = false; st.lastT = watch.t; }
          }
          prevTh = theta;
        }
        if (stirrup) stirrup.rotation.y = theta;
      } else if (MODE === 'force') {
        var g = gramRead(st.df); if (bal) bal.userData.draw(g);
        hud1.set((st.df * 100).toFixed(1) + ' cm'); hud2.set(g.toFixed(1) + ' g'); hud3.set((force(st.df) * 1000).toFixed(1) + ' mN');
      }
      if (MODE === 'plot') {
        var want = st.tanB ? Math.atan(Beq(st.d) / BH) : (Beq(st.d) > BH ? Math.PI : 0);
        ndl.rotation.y += (want - ndl.rotation.y) * 0.18;
        hud1.set((st.d * 100).toFixed(1) + ' cm'); hud2.set(st.tanB ? degRead(st.d).toFixed(1) + '°' : (Beq(st.d) > BH ? 'points south' : 'points north'));
        hud3.set((Beq(st.d) * 1e6).toFixed(1) + ' µT');
      } else if (MODE === 'swing') {
        hud1.set(st.osc + ' / ' + NOSC); hud2.set(watch.t.toFixed(2) + ' s'); hud3.set((theta * 180 / Math.PI).toFixed(1) + '°');
      }
    },
  };
});
