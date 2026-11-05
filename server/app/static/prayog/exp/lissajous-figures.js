/* Prayogshala studio module: Lissajous figures on a CRO (B.Sc. Waves and Oscillations).
   Physics: the hw_lissajous kernel (packs/heat_wave_ug) - the same numbers the server checks: x = ax sin(2 pi fx t),
   y = ay sin(2 pi fy t + phi). Frequency mode: tune generator X until the figure is steady, count the touches on the top
   and side edges: fy/fx = top / side. Phase mode (fx = fy): ellipse, sin(phi) = y0 / ymax. The hidden knob fy (or phi)
   is what the student finds. */
HoolaStudio.define('lissajous-figures', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.hw_lissajous;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('hw_lissajous');
  var PH = p.mode > 0.5, DIV = 8, PXD = 64, TW = 0.25;
  var Ax = 3.4, YG = [2, 3, 4];                                // X amplitude in divisions, and the Y gain settings (divisions) in phase mode
  var st = { cro: false, conn: false, mode: false, fx: PH ? Math.round(p.fy) + 7 : 100, gain: 1, nt: 0, ns: 0, clock: 0, last: '', lastT: -1, helper: false, y0: null, ym: null };
  var cur = { fx: st.fx };
  function qfx() { return Math.round(cur.fx * 10) / 10; }
  function pp() { var q = HK.assign(p, { fx: st.fx }); if (PH) q.ay = YG[st.gain] / Ax; return q; }
  function fr() { return K.frac(pp()); }
  function isStatic() { var f = fr(); return f[0] <= 9 && f[1] <= 9; }
  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'pinch', 320); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }
  // ---------- the CRO
  var CZ = -0.18;
  var cro = new T.Group(); S.scene.add(cro);
  var body = S.rounded(0.34, 0.3, 0.32, 0.02, new T.MeshStandardMaterial({ color: 0xb9bec4, roughness: 0.45, metalness: 0.4 })); body.position.set(0, 0.15, CZ); cro.add(body);
  var bezel = S.rounded(0.24, 0.24, 0.01, 0.02, M.black); bezel.position.set(-0.04, 0.17, CZ + 0.162); cro.add(bezel);
  var scr = S.liveTex(512, 512), screen = new T.Mesh(new T.PlaneGeometry(0.2, 0.2), new T.MeshBasicMaterial({ map: scr })); screen.position.set(-0.04, 0.17, CZ + 0.168); cro.add(screen);
  var panelBg = S.mesh(new T.BoxGeometry(0.075, 0.28, 0.004), new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 })); panelBg.position.set(0.12, 0.15, CZ + 0.162); cro.add(panelBg);
  var cl = S.label('CRO  ·  X-Y', { w: 0.065, ratio: 0.16, color: '#e8e8e8', bg: '#2b2f36' }); cl.position.set(0.12, 0.27, CZ + 0.1645); cro.add(cl);
  var pwr = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.012, 20), M.red); pwr.rotation.x = Math.PI / 2; pwr.position.set(0.12, 0.23, CZ + 0.168); cro.add(pwr);
  var tb = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.012, 20), M.chrome); tb.rotation.x = Math.PI / 2; tb.position.set(0.12, 0.18, CZ + 0.168); cro.add(tb);
  var tbl = S.label('TIME BASE', { w: 0.05, ratio: 0.14, color: '#e8e8e8', bg: '#2b2f36' }); tbl.position.set(0.12, 0.158, CZ + 0.1645); cro.add(tbl);
  var xin = S.terminal([0.1, 0.12, CZ + 0.17], 'red'), yin = S.terminal([0.14, 0.12, CZ + 0.17], 'red'); cro.add(xin); cro.add(yin); xin.rotation.x = Math.PI / 2; yin.rotation.x = Math.PI / 2;
  var xl = S.label('X', { w: 0.012, ratio: 1, color: '#e8e8e8', bg: '#2b2f36' }); xl.position.set(0.1, 0.105, CZ + 0.1645); cro.add(xl);
  var yl = S.label('Y', { w: 0.012, ratio: 1, color: '#e8e8e8', bg: '#2b2f36' }); yl.position.set(0.14, 0.105, CZ + 0.1645); cro.add(yl);
  S.contact(0.4, 0.4, 0, CZ, 0.5);
  // ---------- two audio generators with a frequency dial and a display
  function generator(x, name, unknown) {
    var g = new T.Group(); S.scene.add(g);
    var b = S.rounded(0.2, 0.1, 0.16, 0.01, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 })); b.rotation.x = -Math.PI / 2; b.position.set(x, 0.05, -0.12); g.add(b);
    var tex = S.liveTex(256, 80), disp = new T.Mesh(new T.PlaneGeometry(0.085, 0.0266), new T.MeshBasicMaterial({ map: tex })); disp.rotation.x = -0.9; disp.position.set(x - 0.045, 0.098, -0.06); g.add(disp);
    var dial = S.mesh(new T.CylinderGeometry(0.028, 0.028, 0.02, 36), M.chrome); dial.position.set(x + 0.055, 0.108, -0.1); g.add(dial);
    var mark = S.mesh(new T.BoxGeometry(0.003, 0.004, 0.022), M.red); mark.position.set(0, 0.012, -0.012); dial.add(mark);
    var lbl = S.label(name, { w: 0.15, ratio: 0.09, color: '#e8e8e8', bg: '#2b2f36' }); lbl.rotation.x = -0.9; lbl.position.set(x, 0.092, -0.045); g.add(lbl);
    var out = S.terminal([x - 0.08, 0.09, -0.06], 'red'); g.add(out); S.contact(0.26, 0.2, x, -0.12, 0.5);
    g.userData = { tex: tex, dial: dial, last: '', out: out, unknown: unknown };
    return g;
  }
  var gx = generator(-0.42, 'AUDIO GENERATOR X', false), gy = generator(0.42, 'AUDIO GENERATOR Y', true);
  function drawGen(g, txt, sub) { var k = txt + sub; if (g.userData.last === k) return; g.userData.last = k;
    g.userData.tex.draw(function (x, w, h) { x.fillStyle = '#b9c4a7'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b2116'; x.font = '700 40px "JetBrains Mono", monospace'; x.textAlign = 'right'; x.fillText(txt, w - 8, h - 24); x.font = '600 14px sans-serif'; x.textAlign = 'left'; x.fillText(sub, 8, 18); }); }
  var wX = S.wire([[-0.5, 0.09, -0.06], [-0.3, 0.12, -0.02], [-0.1, 0.12, 0.0], [0.1 - 0.04 + 0.04, 0.125, CZ + 0.19]], 'red');
  var wY = S.wire([[0.34, 0.09, -0.06], [0.25, 0.12, 0.0], [0.2, 0.13, 0.0], [0.14, 0.125, CZ + 0.19]], 'black');
  var watch = S.stopwatch([0.3, 0.035, 0.17], [-1.15, 0, -0.2]);

  S.addApparatus('cro', cro, 'Cathode ray oscilloscope', 'In X-Y mode (time base off) the beam moves sideways with the signal on X and up and down with the signal on Y.');
  S.addApparatus('genx', gx, 'Audio generator X', 'You set this one. Its frequency is on the display.');
  S.addApparatus('geny', gy, 'Audio generator Y', PH ? 'Its signal passes through a phase-shifting RC network. Its frequency and phase are the unknowns.' : 'Its frequency is not shown: that is what you are finding.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Handy for timing how long a figure stays steady.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var bookLines = ['Aim: ' + (PH ? 'to find the phase difference from a Lissajous ellipse.' : 'to find an unknown frequency by Lissajous figures.'), PH ? 'sin φ = y0 / ymax' : 'fy / fx = (touches on the top edge) / (touches on the side edge)'];
  var hudX = S.hudCard('fx'), hudS = S.hudCard('Figure'), hudN = S.hudCard('Readings');

  // ---------- drawing the screen
  function drawScreen(t0) {
    var q = pp(), f = fr(), N = 3600, i, tt, X, Y;
    scr.draw(function (c, w, h) {
      c.fillStyle = '#031208'; c.fillRect(0, 0, w, h);
      if (st.cro) {
        c.strokeStyle = 'rgba(80,200,120,.28)'; c.lineWidth = 1; for (i = 0; i <= DIV; i++) { c.beginPath(); c.moveTo(i * PXD, 0); c.lineTo(i * PXD, h); c.stroke(); c.beginPath(); c.moveTo(0, i * PXD); c.lineTo(w, i * PXD); c.stroke(); }
        c.strokeStyle = 'rgba(80,200,120,.5)'; for (i = 0; i <= DIV * 5; i++) { var a = i * PXD / 5; c.beginPath(); c.moveTo(w / 2 - 4, a); c.lineTo(w / 2 + 4, a); c.moveTo(a, h / 2 - 4); c.lineTo(a, h / 2 + 4); c.stroke(); }
        if (st.conn) {
          var ax = Ax, ay = PH ? YG[st.gain] : Ax * q.ay;
          function pt(k) { tt = t0 + TW * k / N; X = ax * Math.sin(2 * Math.PI * q.fx * tt); Y = ay * Math.sin(2 * Math.PI * q.fy * tt + q.phi); return [w / 2 + X * PXD, h / 2 - Y * PXD]; }
          c.lineJoin = 'round'; c.strokeStyle = 'rgba(70,255,130,.22)'; c.lineWidth = 7; c.beginPath(); var s0 = pt(0); c.moveTo(s0[0], s0[1]); for (i = 1; i <= N; i++) { var s1 = pt(i); c.lineTo(s1[0], s1[1]); } c.stroke();
          c.strokeStyle = '#7dff9c'; c.lineWidth = 2; c.beginPath(); s0 = pt(0); c.moveTo(s0[0], s0[1]); for (i = 1; i <= N; i++) { s1 = pt(i); c.lineTo(s1[0], s1[1]); } c.stroke();
          if (st.helper && isStatic()) {                       // the box round the figure and where it touches
            c.strokeStyle = 'rgba(255,220,120,.8)'; c.lineWidth = 1.5; c.setLineDash([6, 5]); c.strokeRect(w / 2 - ax * PXD, h / 2 - ay * PXD, 2 * ax * PXD, 2 * ay * PXD); c.setLineDash([]);
            c.fillStyle = 'rgba(255,220,120,.95)';
            var per = f[1] / q.fx, topX = [], sideY = [], n2 = 12000, prevY = -9, prevX = -9, k2;       // one full period of the figure
            for (k2 = 0; k2 <= n2; k2++) { var tq = per * k2 / n2, xx = ax * Math.sin(2 * Math.PI * q.fx * tq), yy = ay * Math.sin(2 * Math.PI * q.fy * tq + q.phi);
              if (yy > ay * 0.9995 && prevY <= ay * 0.9995) topX.push(xx); if (xx > ax * 0.9995 && prevX <= ax * 0.9995) sideY.push(yy); prevY = yy; prevX = xx; }
            topX.forEach(function (xv) { c.beginPath(); c.arc(w / 2 + xv * PXD, h / 2 - ay * PXD, 5, 0, 7); c.fill(); }); sideY.forEach(function (yv) { c.beginPath(); c.arc(w / 2 + ax * PXD, h / 2 - yv * PXD, 5, 0, 7); c.fill(); });
          }
        }
      } else { c.fillStyle = '#041a0c'; c.fillRect(0, 0, w, h); }
    });
  }
  // ---------- actions
  function croOn() { if (S.hand.busy || st.cro) return Promise.resolve(); return S.hand.tap(pwr).then(function () { S.click(2000); st.cro = true; S.say('The oscilloscope is on. You see the graticule.'); S.render(); }); }
  function connect() { if (st.conn) return; st.conn = true; S.say('Generator X is on the X input and generator Y on the Y input.'); S.render(); }
  function xyMode() { if (st.mode) return Promise.resolve(); if (S.hand.busy) return Promise.resolve(); return S.hand.tap(tb).then(function () { S.click(1500); st.mode = true; S.say('Time base off: the beam is driven by the two generators only.'); S.render(); }); }
  function setFx(v) { st.fx = Math.max(20, Math.min(1000, Math.round(v * 10) / 10)); st.last = ''; S.render(); }
  function setCount(k, v) { st[k] = Math.max(0, Math.min(12, v)); S.render(); }
  function steadyMsg() { return isStatic() ? 'steady figure' : (function () { var q = pp(), r = q.fy / q.fx; return Math.abs(r * 10 - Math.round(r * 10)) < 0.3 ? 'drifting slowly: nearly a ratio' : 'moving: not a ratio'; })(); }
  function record() {
    if (!st.mode || !st.conn) { S.say('Set up the CRO first.'); return; }
    if (PH) {
      if (Math.abs(st.fx - p.fy) > 0.05) { S.say('The figure is not an ellipse yet: make generator X equal to generator Y (a steady ellipse).'); return; }
      if (st.y0 === null || st.ym === null) { S.say('Read y0 and ymax from the screen first.'); return; }
      if (S.rows.some(function (r) { return r.ymax === st.ym; })) { S.say('Change the Y gain and measure again for a different reading.'); return; }
      S.addRow({ y0: st.y0, ymax: st.ym }); S.say('Written: y0 = ' + st.y0.toFixed(2) + ' div, ymax = ' + st.ym.toFixed(2) + ' div. sin φ = ' + (st.y0 / st.ym).toFixed(3) + '.'); st.y0 = null; st.ym = null; return;
    }
    if (!isStatic()) { S.say('The figure is not steady. Tune generator X until it stops moving.'); return; }
    var f = fr();
    if (st.nt !== f[0] || st.ns !== f[1]) { S.say('Count again: where does the curve touch the top edge of the box, and where the side edge? (Use "Show the box and touches" if you like.)'); return; }
    if (S.rows.some(function (r) { return r.nt / r.ns === f[0] / f[1]; })) { S.say('You already have this figure. Find a different one.'); return; }
    S.addRow({ fx: st.fx, nt: st.nt, ns: st.ns }); S.say('Written: fx = ' + st.fx.toFixed(0) + ' Hz, ' + st.nt + ' touches on top, ' + st.ns + ' on the side.'); st.nt = 0; st.ns = 0;
  }
  function readCursors() { var q = pp(); var ay = YG[st.gain]; st.y0 = Math.round(Math.abs(ay * Math.sin(q.phi)) / 0.02) * 0.02; st.ym = ay; S.say('Read from the graticule: y0 = ' + st.y0.toFixed(2) + ' div, ymax = ' + st.ym.toFixed(2) + ' div.'); S.render(); }
  function fyOne(r) { return r.fx * r.nt / r.ns; }
  var targets = PH ? [] : [[1, 2], [2, 3], [3, 4]];
  function steps() {
    return [
      { id: 'setup', title: 'Set up', view: 'cro', render: function (u) {
          u.h2('Switch on and connect');
          u.task('1. Switch the oscilloscope on', st.cro, st.cro ? 'Graticule visible' : 'The hand presses the power switch')
            .add(u.button(st.cro ? 'On' : 'Switch on', function () { croOn(); }, !st.cro, st.cro || S.hand.busy));
          u.task('2. Connect the generators', st.conn, st.conn ? 'X to the X input, Y to the Y input' : 'Two leads')
            .add(u.button(st.conn ? 'Connected' : 'Connect', connect, !st.conn, st.conn));
          u.task('3. Switch the time base off (X-Y mode)', st.mode, st.mode ? 'X-Y mode' : 'Turn the time-base knob to X-Y')
            .add(u.button(st.mode ? 'X-Y' : 'Set X-Y mode', function () { xyMode(); }, st.cro && st.conn && !st.mode, st.mode || S.hand.busy));
          u.next('Next: find the figures', st.cro && st.conn && st.mode);
        },
        ok: function () { return st.cro && st.conn && st.mode; },
        auto: function () { connect(); return croOn().then(function () { return xyMode(); }); } },
      PH ? { id: 'phase', title: 'Ellipse', view: 'cro', render: function (u) {
          u.h2('Make the ellipse and read it');
          u.p('Both generators must have the same frequency. Tune generator X until the ellipse is steady, then read where it cuts the Y axis (y0) and how high it goes (ymax).');
          u.slider('Generator X', 20, 1000, 1, function () { return st.fx; }, function (v) { setFx(v); }, 'Hz', 0);
          u.row(u.button('−10', function () { setFx(st.fx - 10); }, false, false), u.button('−1', function () { setFx(st.fx - 1); }, false, false), u.button('+1', function () { setFx(st.fx + 1); }, false, false), u.button('+10', function () { setFx(st.fx + 10); }, false, false));
          u.row(u.button('Y gain: ' + YG[st.gain] + ' div (change)', function () { st.gain = (st.gain + 1) % 3; st.y0 = null; st.ym = null; st.last = ''; S.render(); }, false, false));
          u.live(function () { return 'Figure: ' + (Math.abs(st.fx - p.fy) < 0.05 ? 'steady ellipse' : 'drifting (X ' + st.fx + ' Hz is not equal to Y)'); });
          u.row(u.button('Read y0 and ymax', readCursors, Math.abs(st.fx - p.fy) < 0.05, Math.abs(st.fx - p.fy) >= 0.05), u.button('Write in the table', record, true, false));
          u.live(function () { return st.y0 === null ? 'y0, ymax: not read yet' : 'y0 = ' + st.y0.toFixed(2) + ' div, ymax = ' + st.ym.toFixed(2) + ' div, sin φ = ' + (st.y0 / st.ym).toFixed(3); });
          u.h3('Observation table'); u.table();
          u.next('Next: work out φ', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' reading(s) so far. Take 3, changing the Y gain each time.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () { setFx(p.fy); for (var i = 0; i < 3; i++) { st.gain = i; readCursors(); record(); } return Promise.resolve(); } }
      : { id: 'figures', title: 'Figures', view: 'genx', render: function (u) {
          u.h2('Find steady figures and count the touches');
          u.p('Turn generator X up and down. When fx is a simple fraction of the unknown frequency a closed figure forms; tune until it stops moving. Then count the touches on the top and side edges of the box round it.');
          u.slider('Generator X', 20, 1000, 1, function () { return st.fx; }, function (v) { setFx(v); }, 'Hz', 0);
          u.row(u.button('−10', function () { setFx(st.fx - 10); }, false, false), u.button('−1', function () { setFx(st.fx - 1); }, false, false), u.button('+1', function () { setFx(st.fx + 1); }, false, false), u.button('+10', function () { setFx(st.fx + 10); }, false, false));
          u.live(function () { return 'fx = ' + st.fx + ' Hz · ' + steadyMsg(); });
          u.row(u.button((st.helper ? '✓ ' : '') + 'Show the box and touches', function () { st.helper = !st.helper; st.last = ''; S.render(); }, false, false));
          var c1 = u.row(); c1.appendChild(document.createTextNode('Touches on the TOP edge: ' + st.nt + '  '));
          c1.appendChild(u.button('−', function () { setCount('nt', st.nt - 1); }, false, false)); c1.appendChild(u.button('+', function () { setCount('nt', st.nt + 1); }, false, false));
          var c2 = u.row(); c2.appendChild(document.createTextNode('Touches on the SIDE edge: ' + st.ns + '  '));
          c2.appendChild(u.button('−', function () { setCount('ns', st.ns - 1); }, false, false)); c2.appendChild(u.button('+', function () { setCount('ns', st.ns + 1); }, false, false));
          u.row(u.button('Write in the table', record, true, false));
          u.h3('Observation table'); u.table();
          u.next('Next: work out fy', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' figure(s) so far. Take 3 different steady figures.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {                                       // the figures a student would hunt for: fx = fy × (side / top) for a few small ratios
          var done = 0, cand = [[2, 3], [1, 1], [3, 2], [1, 2], [2, 1], [3, 4], [4, 3]], i;
          for (i = 0; i < cand.length && done < 3; i++) {
            var fxs = p.fy * cand[i][1] / cand[i][0]; if (fxs < 20 || fxs > 1000 || Math.abs(fxs - Math.round(fxs)) > 1e-9) continue;
            setFx(fxs); if (!isStatic()) continue;
            var f = fr(); st.nt = f[0]; st.ns = f[1]; var before = S.rows.length; record(); if (S.rows.length > before) done++;
          }
          return Promise.resolve(); } },
    ];
  }

  return {
    camera: { pos: [0.1, 0.4, 1.15], look: [0.0, 0.14, -0.12] },
    views: { cro: [[0.0, 0.26, 0.45], [-0.02, 0.16, CZ + 0.1]], genx: [[-0.35, 0.3, 0.3], [-0.42, 0.07, -0.1]], geny: [[0.35, 0.3, 0.3], [0.42, 0.07, -0.1]], sw: [[-0.5, 0.4, 0.5], [-1.1, 0.05, -0.2]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'Two perpendicular simple harmonic motions combine into a Lissajous figure. When the frequencies are in a ratio of small whole numbers the figure is closed and steady.',
      formula: PH ? 'sin φ = y0 / ymax' : 'fy / fx = (touches on the top edge) / (touches on the side edge)',
      formulaNote: PH ? 'With equal frequencies the figure is an ellipse. y0 is where it cuts the Y axis, ymax its greatest height; φ is the phase difference of the two signals.' : 'A horizontal line along the top edge touches the figure fy times where a vertical line along the side edge touches it fx times (after cancelling common factors).',
      more: [PH ? 'φ = 0 gives a sloping straight line, φ = 90° a circle (equal amplitudes), φ = 180° the other diagonal.' : 'If the figure drifts slowly the frequencies are close to a ratio but not exact; the drift rate is the difference.'],
      precautions: 'Keep the beam intensity low and the spot out of focus when it is still, to protect the screen. Wait until the figure is steady before counting. Count the touches on the top and the side edges of a box drawn round the figure.' },
    book: { title: 'Expt. — Lissajous figures', lines: bookLines,
      columns: PH ? [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'y0 (div)', get: function (r) { return r.y0.toFixed(2); } }, { label: 'ymax (div)', get: function (r) { return r.ymax.toFixed(2); } },
        { label: 'sin φ', get: function (r) { return (r.y0 / r.ymax).toFixed(3); } }, { label: 'φ (°)', get: function (r) { return (Math.asin(r.y0 / r.ymax) * 180 / Math.PI).toFixed(1); } }]
        : [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'fx (Hz)', get: function (r) { return r.fx.toFixed(0); } }, { label: 'Top', get: function (r) { return String(r.nt); } }, { label: 'Side', get: function (r) { return String(r.ns); } },
          { label: 'fy (Hz)', get: function (r) { return fyOne(r).toFixed(1); } }] },
    result: function (rows) {
      if (!rows.length) return null;
      if (PH) { var s = 0; rows.forEach(function (r) { s += Math.asin(r.y0 / r.ymax); }); return { label: 'φ (phase difference)', value: s / rows.length * 180 / Math.PI, unit: '°', digits: 1, truth: p.phi * 180 / Math.PI, note: 'sin φ = y0 / ymax, mean of ' + rows.length + ' readings.' }; }
      var t = 0; rows.forEach(function (r) { t += fyOne(r); });
      return { label: 'fy (unknown frequency)', value: t / rows.length, unit: 'Hz', digits: 1, truth: p.fy, note: 'fy = fx × top / side, mean of ' + rows.length + ' figures.' };
    },
    tol: 0.02,
    chips: ['Why does the figure drift?', 'How do I count the touches?', 'Why is a circle a 90° phase?', 'Check my readings', 'Why is my result different?'],
    viva: PH ? [['For a circle (equal amplitudes) the phase difference is', ['90°', '0°', '180°'], 0, 'x = a sin ωt and y = a sin(ωt + 90°) = a cos ωt trace a circle.'],
      ['A sloping straight line means the phase difference is', ['0° or 180°', '90°', '45°'], 0, 'The two signals rise and fall together (or oppositely).']]
      : [['A figure touches the top edge 3 times and the side edge 2 times. fy/fx is', ['3/2', '2/3', '1'], 0, 'fy/fx = touches on the top / touches on the side.'],
        ['A slowly rotating figure means', ['the frequencies are close to, but not exactly, a simple ratio', 'the CRO is broken', 'the phase is 90°'], 0, 'The relative phase changes slowly at the difference frequency.']],
    askState: function () { return { cro_on: st.cro, connected: st.conn, xy_mode: st.mode, generator_x_Hz: st.fx, figure: st.conn ? steadyMsg() : 'no signal', top_count: st.nt, side_count: st.ns, readings: S.rows.length, y_gain_div: PH ? YG[st.gain] : null }; },
    steps: steps(),

    tick: function (dt) {
      st.clock += dt; cur.fx += (st.fx - cur.fx) * Math.min(1, dt * 10);
      var key = [st.cro, st.conn, st.fx, st.gain, st.helper, st.mode].join('|'), moving = st.cro && st.conn && !isStatic();
      if (key !== st.last || (moving && st.clock - st.lastT > 0.08)) { st.last = key; st.lastT = st.clock; drawScreen(moving ? st.clock : 0); }
      drawGen(gx, (st.cro ? st.fx.toFixed(0) : st.fx.toFixed(0)) + ' Hz', 'FREQUENCY'); drawGen(gy, st.conn && st.cro ? (PH ? 'f  ? ' : '---') : '---', PH ? 'UNKNOWN' : 'UNKNOWN');
      gx.userData.dial.rotation.y = st.fx / 60; gy.userData.dial.rotation.y = 2.1;
      hudX.set(st.fx.toFixed(0) + ' Hz'); hudS.set(st.conn && st.cro ? (isStatic() ? 'steady' : 'moving') : '—'); hudN.set(String(S.rows.length));
    },
  };
});
