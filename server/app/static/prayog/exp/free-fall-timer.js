/* Prayogshala studio module: g by digital timing of a freely falling body (B.Sc. mechanics).
   A rigid steel column on a heavy base carries an electromagnet at the top and a receiver pad on a sliding clamp below.
   A steel ball hangs from the magnet; pressing the release switch cuts the current and starts a millisecond timer at the
   same instant, and the ball landing on the pad stops it. A metre scale fixed to the column measures the drop.
   The gloved hand slides the pad's clamp to set the height and presses the release switch.
   Physics: the `freefall` kernel of the mech_ug pack - h = ½ g t². Everything is read from the lab's params. */
HoolaStudio.define('free-fall-timer', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.freefall;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('freefall');
  var kh = (S.lab.knobs || []).filter(function (q) { return q.param === 'h'; })[0] || { min: 20, max: 100, k: 0.01 };
  var HMIN = Math.round(kh.min * (kh.k || 1) * 1000) / 1000, HMAX = Math.round(kh.max * (kh.k || 1) * 1000) / 1000;
  var HEIGHTS = [0, 1, 2, 3, 4].map(function (i) { return Math.round((HMIN + (HMAX - HMIN) * i / 4) * 1000) / 1000; });
  var TLC = 1e-4;                                       // the timer's least count: 0.1 ms
  var st = { hi: 2, read: [null, null], falling: false, landed: false, t: null };
  p.h = HEIGHTS[st.hi];
  var sim = K.init(p), ready = false;

  // ---------- geometry: the magnet's face is at y = MAGY; the pad's top is h below it
  var XC = 0.0, ZC = -0.2, MAGY = 1.22, BALLR = 0.009;
  var col = new T.Group(); S.scene.add(col);
  var cbase = S.rounded(0.34, 0.24, 0.034, 0.01, M.iron); cbase.rotation.x = -Math.PI / 2; cbase.position.set(XC - 0.2, 0.017, ZC); col.add(cbase);
  var cpost = S.mesh(new T.CylinderGeometry(0.017, 0.02, MAGY + 0.1, 26), M.chrome); cpost.position.set(XC - 0.2, (MAGY + 0.1) / 2 + 0.034, ZC); col.add(cpost);
  var carm = S.mesh(new T.BoxGeometry(0.24, 0.022, 0.04), M.iron); carm.position.set(XC - 0.09, MAGY + 0.04, ZC); col.add(carm);
  S.contact(0.4, 0.3, XC - 0.2, ZC, 0.55);
  var mag = new T.Group(); S.scene.add(mag);
  var mbody = S.rounded(0.055, 0.045, 0.055, 0.006, new T.MeshStandardMaterial({ color: 0x3a4149, roughness: 0.5, metalness: 0.5 }));
  mbody.position.y = 0.025; mag.add(mbody);
  var mcoil = S.mesh(new T.CylinderGeometry(0.019, 0.019, 0.016, 20), new T.MeshStandardMaterial({ color: 0xb06a32, roughness: 0.5, metalness: 0.7 }));
  mcoil.position.y = 0.006; mag.add(mcoil);
  mag.position.set(XC, MAGY, ZC);
  var lead = S.wire([[XC, MAGY + 0.02, ZC], [XC - 0.19, MAGY - 0.02, ZC - 0.012], [XC - 0.19, 0.3, ZC - 0.012], [XC + 0.28, 0.07, 0.05]], 'red');

  var ball = S.mesh(new T.SphereGeometry(BALLR, 26, 18), new T.MeshStandardMaterial({ color: 0xd7dbe0, roughness: 0.08, metalness: 1 }));
  S.scene.add(ball);

  var pad = new T.Group(); S.scene.add(pad);
  var ppl = S.rounded(0.12, 0.12, 0.014, 0.004, new T.MeshStandardMaterial({ color: 0x2b3138, roughness: 0.6 }));
  ppl.rotation.x = -Math.PI / 2; pad.add(ppl);
  var pdisc = S.mesh(new T.CylinderGeometry(0.035, 0.035, 0.004, 28), new T.MeshStandardMaterial({ color: 0x8a2a1e, roughness: 0.75 }));
  pdisc.position.y = 0.008; pad.add(pdisc);
  var pclamp = S.rounded(0.05, 0.045, 0.05, 0.005, M.alu); pclamp.position.set(-0.2, -0.005, 0); pad.add(pclamp);
  var parm = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.2, 14), M.chrome); parm.rotation.z = Math.PI / 2; parm.position.set(-0.1, 0, 0); pad.add(parm);

  // the metre scale fixed to the column: its zero is at the magnet's face
  var RLEN = 1.2, RTOP = MAGY, RX = XC - 0.16, RZ = ZC + 0.022;
  var ruler = S.ruler(RLEN, { title: 'SCALE · cm · zero at the magnet', labelEvery: 10, width: 0.03 });
  ruler.position.set(RX, RTOP - RLEN, RZ); S.scene.add(ruler);
  function cmAt(y) { return (RTOP - y) * 100; }

  // the millisecond timer
  var tim = new T.Group(); S.scene.add(tim);
  var tbody = S.rounded(0.22, 0.14, 0.07, 0.008, new T.MeshStandardMaterial({ color: 0x1b1b1d, roughness: 0.5 }));
  tbody.rotation.x = -0.5; tbody.position.y = 0.035; tim.add(tbody);
  var lcd = S.liveTex(512, 180), lcdLast = '';
  function drawLcd(txt) {
    if (txt === lcdLast) return; lcdLast = txt;
    lcd.draw(function (x) {
      var gr = x.createLinearGradient(0, 0, 0, 180); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
      x.fillStyle = gr; x.fillRect(0, 0, 512, 180);
      x.font = '700 92px "JetBrains Mono", monospace'; x.textAlign = 'center';
      x.fillStyle = 'rgba(0,0,0,.07)'; x.fillText('8.8888', 256, 112);
      x.fillStyle = '#1b2116'; x.fillText(txt, 256, 112);
      x.font = '600 24px "Public Sans", sans-serif'; x.textAlign = 'left'; x.fillText('MILLISECOND TIMER', 20, 160);
      x.textAlign = 'right'; x.fillText('SECONDS', 492, 160);
    });
  }
  var scr = new T.Mesh(new T.PlaneGeometry(0.15, 0.052), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
  scr.rotation.x = -0.5 - Math.PI / 2 + Math.PI / 2; scr.rotation.x = -0.5; scr.position.set(0, 0.07, 0.022); tim.add(scr);
  var relBtn = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.01, 22), new T.MeshStandardMaterial({ color: 0xc0392b, roughness: 0.4 }));
  relBtn.position.set(0.075, 0.075, -0.016); tim.add(relBtn);
  var relLbl = S.label('RELEASE', { w: 0.03, ratio: 0.25, color: '#e6e7ea', weight: 600 }); relLbl.rotation.x = -Math.PI / 2;
  relLbl.position.set(0.075, 0.072, 0.008); tim.add(relLbl);
  tim.position.set(XC + 0.32, 0, 0.06); S.contact(0.26, 0.2, XC + 0.32, 0.06, 0.5);

  S.addApparatus('mag', mag, 'Electromagnet', 'Holds the ball until the switch is pressed. The same press starts the timer, so no reaction time comes in.');
  S.addApparatus('ball', ball, 'Steel ball', 'A smooth steel ball, 18 mm across. Over a fall of a metre, air resistance on it is negligible.');
  S.addApparatus('pad', pad, 'Receiver pad', 'A switch pad on a sliding clamp. The ball landing on it stops the timer.');
  S.addApparatus('ruler', ruler, 'Scale on the column', 'Its zero is at the face of the magnet, so the pad’s reading is the drop h.');
  S.addApparatus('tim', tim, 'Millisecond timer', 'Reads to ' + (TLC * 1000).toFixed(1) + ' ms. A hand-held stopwatch cannot time a fall this short.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudH = S.hudCard('Height of fall'), hudY = S.hudCard('Fallen'), hudT = S.hudCard('Timer');

  // ---------- state
  function padY() { return MAGY - p.h; }
  function placePad() { pad.position.set(XC, padY(), ZC); }
  function setHeight(i) {
    if (S.hand.busy || st.falling) return Promise.resolve();
    var y0 = padY();
    st.hi = i;
    var y1 = MAGY - HEIGHTS[i];
    st.read = [null, null]; st.t = null; st.landed = false;
    return S.hand.pinchMove(new T.Vector3(XC - 0.2, y0, ZC + 0.03), function (k) {
      return new T.Vector3(XC - 0.2, y0 + (y1 - y0) * k, ZC + 0.03);
    }, function (k) { p.h = Math.max(0.02, MAGY - (y0 + (y1 - y0) * k)); placePad(); }, { ms: 900, hold: 180, mode: 'side' })
      .then(function () {
        p.h = HEIGHTS[i]; placePad(); sim = K.init(p);
        S.say('Pad clamped about ' + (p.h * 100).toFixed(0) + ' cm below the magnet. Read the scale.');
        S.render();
      });
  }
  function readScale(which) {                            // 0 = the magnet's face, 1 = the top of the pad
    var y = which === 0 ? MAGY : padY();
    st.read[which] = Math.round(cmAt(y) * 10) / 10;
    if (bothRead()) S.say('Magnet at ' + st.read[0].toFixed(1) + ' cm, pad at ' + st.read[1].toFixed(1) + ' cm, so h = ' + hCm().toFixed(1) + ' cm.');
    else S.say((which === 0 ? 'The magnet’s face' : 'The top of the pad') + ' reads ' + st.read[which].toFixed(1) + ' cm.');
    if (ready) S.render();
  }
  function bothRead() { return st.read[0] !== null && st.read[1] !== null; }
  function hCm() { return bothRead() ? Math.round((st.read[1] - st.read[0]) * 10) / 10 : 0; }

  function release() {
    if (S.hand.busy || st.falling) return Promise.resolve();
    if (!bothRead()) { S.say('Measure the height on the scale first.'); return Promise.resolve(); }
    return S.hand.tap(relBtn).then(function () {
      S.click(1800); sim = K.init(p); st.falling = true; st.landed = false; st.t = null;
      S.say('Released. The timer is running.'); S.render();
    });
  }
  function recordRun() {
    if (st.t === null) { S.say('Drop the ball first.'); return; }
    S.addRow({ h: hCm() / 100, hcm: hCm(), t: st.t });
    S.say('Written in your record book: h = ' + hCm().toFixed(1) + ' cm fell in ' + st.t.toFixed(4) + ' s.');
    st.t = null; S.render();
  }
  function dropOnce() {
    return release().then(function () {
      S.advance(5, function () { return st.landed; });
      recordRun();
      return Promise.resolve();
    });
  }
  function heightsDone() { var o = {}; S.rows.forEach(function (r) { o[r.hcm.toFixed(1)] = 1; }); return Object.keys(o).length; }

  placePad(); drawLcd('0.0000');

  var EXP = {
    camera: { pos: [1.15, 1.2, 2.3], look: [-0.04, 0.6, -0.18] },
    views: {
      setup: [[1.1, 1.15, 2.25], [-0.04, 0.6, -0.18]],
      mag: [[0.42, 1.36, 0.72], [XC - 0.02, 1.19, -0.2]],
      pad: [[0.46, 0.5, 0.85], [XC, 0.34, -0.18]],
      ruler: [[0.78, 0.86, 1.5], [XC - 0.08, 0.64, -0.18]],
      tim: [[0.55, 0.38, 0.52], [XC + 0.3, 0.07, 0.04]],
      book: [[-0.34, 0.5, 0.56], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'A body let go from rest and acted on by gravity alone falls with constant acceleration, so the distance '
        + 'it covers is proportional to the square of the time.',
      formula: 'h = ½ g t²,   so g = 2h / t²',
      formulaNote: 'A fall of 50 cm lasts about 0.32 s, which is why the timing is done electrically and not by hand.',
      more: ['A graph of h against t² is a straight line through the origin whose slope is g/2.',
        'If the release lags behind the start of the timer by a constant amount, the line has an intercept: the graph shows up such a fault, a single reading does not.',
        'Air resistance on a smooth steel ball over a metre is far below the timer’s own resolution.'],
      precautions: 'Make sure the ball hangs centrally under the magnet and lands squarely on the pad. Take three drops at '
        + 'each height and use their mean. Do not put your hand under the ball.'
    },
    book: {
      title: 'Expt. — g by free fall',
      lines: ['Aim: to find the acceleration due to gravity by timing a freely falling ball.',
        'Scale zero at the face of the magnet', 'h = (pad reading) − (magnet reading)',
        'Timer least count ' + (TLC * 1000).toFixed(1) + ' ms', 'g = 2h / t²',
        'Slope of h against t² = g/2'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'h (cm)', get: function (r) { return r.hcm.toFixed(1); } },
        { label: 't (s)', get: function (r) { return r.t.toFixed(4); } },
        { label: 't² (s²)', get: function (r) { return (r.t * r.t).toFixed(5); } },
        { label: '2h/t²', get: function (r) { return (2 * r.h / (r.t * r.t)).toFixed(3); } }]
    },
    graph: {
      x: function (r) { return r.t * r.t; }, y: function (r) { return r.hcm; },
      xlabel: 't² (s²)', ylabel: 'h (cm)', x0: 0, y0: 0,
      line: function (pts) { var s = S.fit.origin(pts); return function (x) { return s * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var v = HK.CALCS.ff_g.fn(rows, p);
      if (!isFinite(v) || v <= 0) return null;
      return { label: 'g', value: v, unit: 'm/s²', digits: 3, truth: p.g, note: 'Mean of 2h/t² over the heights used.' };
    },
    tol: 0.02,
    chips: ['Why not use a hand stopwatch?', 'Why plot h against t²?', 'Check my readings',
      'Does air resistance matter here?', 'What would a release delay look like on the graph?'],
    viva: [['The graph of h against t² for a freely falling body is', ['a straight line of slope g/2', 'a parabola', 'a horizontal line'], 0,
      'h = ½gt².'],
      ['A hand stopwatch is useless here because', ['the fall is shorter than a human reaction time', 'it cannot read seconds', 'the ball is too small'], 0,
        'A reaction time of about 0.2 s is comparable with the whole fall.']],
    askState: function () {
      var v = K.view(sim, p);
      return {
        height_set_cm: +(p.h * 100).toFixed(1), measured_height_cm: bothRead() ? hCm() : null,
        magnet_reading_cm: st.read[0], pad_reading_cm: st.read[1],
        ball_falling: st.falling, fallen_cm: +(v.y * 100).toFixed(1), speed_m_s: +v.v.toFixed(3),
        last_time_s: st.t
      };
    },

    steps: [
      { id: 'set', title: 'Set the height', view: 'ruler',
        render: function (u) {
          u.h2('Set the height of fall and measure it');
          u.p('Slide the pad’s clamp down the column. Then read the magnet’s face and the top of the pad on the '
            + 'scale: h is the difference.');
          var r = u.row();
          HEIGHTS.forEach(function (h, i) {
            r.appendChild(u.button((h * 100).toFixed(0) + ' cm' + (st.hi === i ? ' ✓' : ''), function () { setHeight(i).then(function () { S.focus('ruler'); }); }, st.hi === i, S.hand.busy || st.falling));
          });
          u.task('1. Read the magnet’s face', st.read[0] !== null, st.read[0] !== null ? st.read[0].toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read', function () { S.focus('mag'); readScale(0); }, st.read[0] === null, st.read[0] !== null));
          u.task('2. Read the top of the pad', st.read[1] !== null, st.read[1] !== null ? st.read[1].toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read', function () { S.focus('pad'); readScale(1); }, st.read[1] === null, st.read[1] !== null));
          if (bothRead()) u.formula('h = ' + st.read[1].toFixed(1) + ' − ' + st.read[0].toFixed(1) + ' = ' + hCm().toFixed(1) + ' cm');
          u.next('Next: drop the ball', bothRead());
        },
        ok: function () { return bothRead(); },
        auto: function () { readScale(0); readScale(1); return Promise.resolve(); } },

      { id: 'drop', title: 'Drop and time', view: 'setup',
        render: function (u) {
          u.h2('Drop the ball and read the timer');
          u.p('Pressing RELEASE cuts the current to the magnet and starts the timer in the same instant. The ball landing '
            + 'on the pad stops it.');
          var r = u.row();
          HEIGHTS.forEach(function (h, i) {
            r.appendChild(u.button((h * 100).toFixed(0) + ' cm' + (st.hi === i ? ' ✓' : ''), function () { setHeight(i).then(function () { S.focus('setup'); }); }, st.hi === i, S.hand.busy || st.falling));
          });
          u.task('Measure h for this setting', bothRead(), bothRead() ? 'h = ' + hCm().toFixed(1) + ' cm' : 'Not measured yet')
            .add(u.button('Measure it', function () { readScale(0); readScale(1); }, !bothRead(), bothRead()));
          u.row(u.button(st.falling ? 'Falling…' : 'RELEASE', function () { release(); }, true, S.hand.busy || st.falling || !bothRead()),
            u.button('Write this drop down', function () { recordRun(); }, false, S.hand.busy || st.t === null));
          u.live(function () {
            var v = K.view(sim, p);
            return 'h = ' + (p.h * 100).toFixed(0) + ' cm · fallen ' + (v.y * 100).toFixed(1) + ' cm · '
              + (st.t === null ? (st.falling ? 'timing…' : 'ready') : st.t.toFixed(4) + ' s');
          });
          u.h3('Observation table'); u.table();
          var n = heightsDone();
          u.next('Next: work out g', n >= 3);
          if (n < 3) u.p(n + ' of at least 3 heights done. Move the pad, measure h again and drop the ball.');
        },
        ok: function () { return heightsDone() >= 3; },
        auto: function () {
          return [4, 2, 0].reduce(function (pr, i) {
            return pr.then(function () { return setHeight(i); })
              .then(function () { readScale(0); readScale(1); return dropOnce(); });
          }, Promise.resolve());
        } }
    ],

    tick: function (dt) {
      if (st.falling) {
        K.step(sim, p, dt);
        var v = K.view(sim, p);
        if (v.landed) {
          st.falling = false; st.landed = true;
          st.t = Math.floor(K.measure(p).t / TLC + 0.5) * TLC;
          S.render();
        }
      }
      pose();
    },
    ready: function () { ready = true; }
  };
  function pose() {
    var v = K.view(sim, p), y = st.falling || st.landed ? MAGY - 0.012 - Math.min(v.y, p.h - 0.012) : MAGY - 0.012;
    ball.position.set(XC, y - BALLR, ZC);
    hudH.set((p.h * 100).toFixed(0) + ' cm');
    hudY.set((v.y * 100).toFixed(1) + ' cm');
    var shown = st.t !== null ? st.t : (st.falling ? Math.min(v.t, K.measure(p).t) : 0);
    hudT.set(shown.toFixed(4) + ' s');
    drawLcd(shown.toFixed(4));
  }
  pose();
  return EXP;
});
