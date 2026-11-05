/* Prayogshala studio module: THE ALTERNATING-CURRENT BENCH (B.Sc. electricity laboratory).
   A sine function generator with a frequency dial and a calibrated output, a two-trace oscilloscope whose screen
   is drawn live, an alternating-current milliammeter, and three decade boxes - resistance, inductance and
   capacitance - patched into whichever circuit the experiment needs. Series and parallel LCR resonance, the
   series RC circuit and the response of an RC filter all run on this one bench. Every number comes from this
   lab's kernel (packs/em_ug.js: phasor algebra, with the resonant frequency SEARCHED on the simulated response),
   which is the same code the server checks against the textbook formulas. Nothing here is at mains voltage. */
HoolaStudio.define('ac-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels;
  var KIND = S.lab.kernel, KN = HK.K[KIND];
  var p = HK.paramsFor(KIND, S.lab.params);
  var ISLCR = KIND === 'lcr', PAR = ISLCR && p.mode >= 0.5, HIGH = !ISLCR && p.mode >= 0.5;
  var f0 = ISLCR ? 1 / (2 * Math.PI * Math.sqrt(p.L * p.C)) : 1 / (2 * Math.PI * p.R * p.C);
  var st = { traced: false, f: Math.round(f0 / 4 / 10) * 10, set: false, phase: 0 };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function at(f) { var q = HK.assign(p, { f: f }); return KN.view(KN.init(q, q), q, q); }
  function fHz(f) { return f >= 1000 ? (f / 1000).toFixed(3) + ' kHz' : Math.round(f) + ' Hz'; }

  /* ---------------------------------------------------------------- the function generator */
  var gen = (function () {
    var g = new T.Group(); S.scene.add(g); g.position.set(-0.46, 0, -0.44);
    var GW = 0.26, GD = 0.17, GH = 0.095;
    var body = S.rounded(GW, GD, GH, 0.006, new T.MeshStandardMaterial({ color: 0x8e949c, roughness: 0.5 }));
    body.rotation.x = -Math.PI / 2; body.position.y = GH / 2; g.add(body);
    var fascia = new T.Mesh(new T.PlaneGeometry(GW - 0.012, 0.085), new T.MeshStandardMaterial({ color: 0x23262b, roughness: 0.5 }));
    fascia.position.set(0, GH * 0.62, GD / 2 + 0.0012); g.add(fascia);
    var lcd = S.liveTex(520, 180), last = '';
    var scr = new T.Mesh(new T.PlaneGeometry(0.1, 0.034), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
    scr.position.set(-0.062, GH * 0.68, GD / 2 + 0.0022); g.add(scr);
    var bez = S.mesh(new T.BoxGeometry(0.108, 0.042, 0.004), M.black); bez.position.set(-0.062, GH * 0.68, GD / 2 + 0.0008); g.add(bez);
    var knurl = S.canvasTex(256, 32, function (c, w, h) { c.fillStyle = '#17181c'; c.fillRect(0, 0, w, h); c.fillStyle = '#41454c'; for (var i = 0; i < w; i += 8) c.fillRect(i, 0, 3, h); });
    var dial = new T.Group(); dial.position.set(0.062, GH * 0.6, GD / 2 + 0.012); g.add(dial);
    var dk = S.mesh(new T.CylinderGeometry(0.023, 0.025, 0.022, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.42 }));
    dk.rotation.x = Math.PI / 2; dial.add(dk);
    var dcap = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.002, 36), M.chrome); dcap.rotation.x = Math.PI / 2; dcap.position.z = 0.012; dial.add(dcap);
    var dmark = S.mesh(new T.BoxGeometry(0.0022, 0.016, 0.0014), M.red, false); dmark.position.set(0, 0.011, 0.0135); dial.add(dmark);
    var amp = S.mesh(new T.CylinderGeometry(0.011, 0.012, 0.012, 24), M.blackPlastic); amp.rotation.x = Math.PI / 2;
    amp.position.set(0.004, GH * 0.26, GD / 2 + 0.008); g.add(amp);
    [[-0.075, 'red'], [-0.042, 'black']].forEach(function (q) {
      var bnc = S.mesh(new T.CylinderGeometry(0.006, 0.007, 0.012, 18), q[1] === 'red' ? M.red : M.blackPlastic);
      bnc.rotation.x = Math.PI / 2; bnc.position.set(q[0], GH * 0.26, GD / 2 + 0.008); g.add(bnc); });
    var lb = S.label('FUNCTION GENERATOR  ·  SINE', { w: 0.13, ratio: 0.14, color: '#d7dbe0' });
    lb.position.set(0, GH * 0.93, GD / 2 + 0.0022); g.add(lb);
    var lb2 = S.label('OUTPUT', { w: 0.035, ratio: 0.3, color: '#b9bec6' }); lb2.position.set(-0.058, GH * 0.42, GD / 2 + 0.0022); g.add(lb2);
    var lb3 = S.label('FREQUENCY', { w: 0.05, ratio: 0.22, color: '#b9bec6' }); lb3.position.set(0.062, GH * 0.3, GD / 2 + 0.0022); g.add(lb3);
    S.contact(GW + 0.08, GD + 0.08, -0.46, -0.44, 0.55);
    return { group: g, dial: dial, dialAt: wpt(g, 0.062, GH * 0.6, GD / 2 + 0.03), out: wpt(g, -0.075, GH * 0.26, GD / 2 + 0.014),
      outN: wpt(g, -0.042, GH * 0.26, GD / 2 + 0.014),
      turn: function (f) { dial.rotation.z = -Math.log(Math.max(f, 1) / 20) * 1.1; },
      show: function (f) { var t = f >= 1000 ? (f / 1000).toFixed(3) : f.toFixed(1), u = f >= 1000 ? 'kHz' : 'Hz';
        if (t + u === last) return; last = t + u;
        lcd.draw(function (c, w, h) { c.fillStyle = '#0a1016'; c.fillRect(0, 0, w, h);
          c.fillStyle = '#ff9a3c'; c.font = '700 104px "JetBrains Mono", monospace'; c.textAlign = 'right';
          c.fillText(t, w - 120, 124); c.font = '600 46px "Public Sans", sans-serif'; c.fillText(u, w - 14, 124); }); } };
  })();
  gen.turn(st.f);

  /* ---------------------------------------------------------------- the oscilloscope */
  var cro = (function () {
    var g = new T.Group(); S.scene.add(g); g.position.set(0.22, 0, -0.46);
    var CW = 0.34, CD = 0.24, CH = 0.21;
    var body = S.rounded(CW, CD, CH, 0.008, new T.MeshStandardMaterial({ color: 0x474c55, roughness: 0.52 }));
    body.rotation.x = -Math.PI / 2; body.position.y = CH / 2; g.add(body);
    var tilt = new T.Group(); tilt.position.set(-0.055, CH * 0.56, CD / 2 - 0.004); tilt.rotation.x = -0.32; g.add(tilt);
    var tex = S.liveTex(640, 500);
    var scr = new T.Mesh(new T.PlaneGeometry(0.17, 0.133), new T.MeshBasicMaterial({ map: tex, toneMapped: false }));
    scr.position.z = 0.006; tilt.add(scr);
    var bez = S.rounded(0.188, 0.151, 0.012, 0.006, M.blackPlastic); tilt.add(bez);
    var panel = new T.Mesh(new T.PlaneGeometry(0.1, 0.16), new T.MeshStandardMaterial({ color: 0x23262b, roughness: 0.5 }));
    panel.position.set(0.112, CH * 0.56, CD / 2 + 0.0015); panel.rotation.x = -0.1; g.add(panel);
    [[0.086, 0.035], [0.14, 0.035], [0.086, -0.03], [0.14, -0.03]].forEach(function (q) {
      var k = S.mesh(new T.CylinderGeometry(0.009, 0.0095, 0.012, 24), M.blackPlastic);
      k.rotation.x = Math.PI / 2; k.position.set(q[0], CH * 0.56 + q[1], CD / 2 + 0.008); g.add(k);
      var m2 = S.mesh(new T.BoxGeometry(0.0016, 0.008, 0.0012), M.white, false);
      m2.position.set(q[0], CH * 0.56 + q[1] + 0.006, CD / 2 + 0.015); g.add(m2); });
    [[-0.1, 'red'], [-0.06, 'black'], [-0.02, 'blue']].forEach(function (q) {
      var bnc = S.mesh(new T.CylinderGeometry(0.0062, 0.0072, 0.012, 18),
        q[1] === 'red' ? M.red : q[1] === 'blue' ? new T.MeshStandardMaterial({ color: 0x2c5fb4, roughness: 0.4 }) : M.blackPlastic);
      bnc.rotation.x = Math.PI / 2; bnc.position.set(q[0], CH * 0.12, CD / 2 + 0.008); g.add(bnc); });
    var lb = S.label('OSCILLOSCOPE  ·  DUAL TRACE', { w: 0.1, ratio: 0.14, color: '#d7dbe0' });
    lb.position.set(0.112, CH * 0.56 + 0.072, CD / 2 + 0.003); g.add(lb);
    S.contact(CW + 0.1, CD + 0.1, 0.22, -0.46, 0.55);
    var lastKey = '';
    return { group: g, chA: wpt(g, -0.1, CH * 0.12, CD / 2 + 0.014), chB: wpt(g, -0.02, CH * 0.12, CD / 2 + 0.014),
      earth: wpt(g, -0.06, CH * 0.12, CD / 2 + 0.014),
      draw: function (amp, gain, phase, f) {
        var key = amp.toFixed(3) + gain.toFixed(5) + phase.toFixed(5) + Math.round(f);
        if (key === lastKey) return; lastKey = key;
        tex.draw(function (c, w, h) {
          c.fillStyle = '#071a0e'; c.fillRect(0, 0, w, h);
          c.strokeStyle = 'rgba(120,220,150,.20)'; c.lineWidth = 1.5;
          var i;
          for (i = 0; i <= 10; i++) { c.beginPath(); c.moveTo(i * w / 10, 0); c.lineTo(i * w / 10, h); c.stroke(); }
          for (i = 0; i <= 8; i++) { c.beginPath(); c.moveTo(0, i * h / 8); c.lineTo(w, i * h / 8); c.stroke(); }
          c.strokeStyle = 'rgba(140,240,170,.45)'; c.lineWidth = 2.5;
          c.beginPath(); c.moveTo(0, h / 2); c.lineTo(w, h / 2); c.stroke();
          c.beginPath(); c.moveTo(w / 2, 0); c.lineTo(w / 2, h); c.stroke();
          function trace(a, ph, col, lift) {
            c.strokeStyle = col; c.lineWidth = 4; c.shadowColor = col; c.shadowBlur = 10; c.beginPath();
            for (var x = 0; x <= w; x += 2) {
              var th = (x / w) * 3 * 2 * Math.PI + ph;
              var y = h / 2 + lift - a * Math.sin(th) * h * 0.30;
              if (x) c.lineTo(x, y); else c.moveTo(x, y);
            }
            c.stroke(); c.shadowBlur = 0;
          }
          trace(1, 0, '#6ef29a', -h * 0.17);
          trace(Math.min(gain, 2.5), -phase, '#ffd166', h * 0.17);
          c.fillStyle = 'rgba(190,240,205,.75)'; c.font = '600 22px "Public Sans", sans-serif';
          c.fillText('CH1 ' + amp.toFixed(2) + ' V', 12, 26);
          c.fillText('CH2 ' + (amp * gain).toFixed(3) + ' V', 12, h - 14);
          c.textAlign = 'right'; c.fillText(f >= 1000 ? (f / 1000).toFixed(2) + ' kHz' : Math.round(f) + ' Hz', w - 12, 26);
          c.fillText((phase * 180 / Math.PI).toFixed(0) + '°', w - 12, h - 14);
        });
      } };
  })();

  /* ---------------------------------------------------------------- the alternating-current milliammeter */
  var meterMax = ISLCR ? (PAR ? Math.ceil(p.V / p.R * 1000) : Math.ceil(p.V / p.R * 1000)) : 1;
  var amm = S.meter({ min: 0, max: meterMax, ticks: 5, unit: 'mA', symbol: 'mA',
    caption: 'AC MILLIAMMETER', pos: [-0.2, 0, -0.06] });

  /* ---------------------------------------------------------------- three decade boxes */
  function decade(x, z, muls, title, unit, fmt) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z);
    var n = muls.length, BW = 0.045 + n * 0.05, BD = 0.105, BH = 0.044;
    var body = S.rounded(BW, BD, BH, 0.005, M.darkWood); body.rotation.x = -Math.PI / 2; body.position.y = BH / 2; g.add(body);
    var dx = muls.map(function (m, i) { return -(n - 1) * 0.05 / 2 + i * 0.05; });
    var PWn = BW - 0.007, PDn = BD - 0.007;
    var tex = S.canvasTex(1100, Math.round(1100 * PDn / PWn), function (c, w, h) {
      var X = function (u) { return (u / PWn + 0.5) * w; }, Y = function (v) { return (v / PDn + 0.5) * h; }, k = w / PWn;
      c.fillStyle = '#191c21'; c.fillRect(0, 0, w, h);
      c.strokeStyle = 'rgba(255,255,255,.14)'; c.lineWidth = 3; c.strokeRect(9, 9, w - 18, h - 18);
      c.fillStyle = '#eceadf'; c.font = '700 ' + Math.round(k * 0.0082) + 'px "Public Sans", sans-serif'; c.textAlign = 'left';
      c.fillText(title, 20, Math.round(k * 0.0125));
      muls.forEach(function (m, i) {
        var cx = X(dx[i]), cy = Y(0.004), R = 0.023 * k;
        c.strokeStyle = '#8b9099'; c.lineWidth = 2; c.beginPath(); c.arc(cx, cy, R * 0.72, 0, Math.PI * 2); c.stroke();
        c.textAlign = 'center'; c.fillStyle = '#eceadf'; c.font = '600 ' + Math.round(k * 0.0064) + 'px "Public Sans", sans-serif';
        for (var d = 0; d < 10; d++) { var a = d * Math.PI / 5; c.fillText(String(d), cx + Math.sin(a) * R, cy + Math.cos(a) * R + k * 0.0023); }
        c.fillStyle = '#f0c36b'; c.font = '700 ' + Math.round(k * 0.0062) + 'px "Public Sans", sans-serif';
        c.fillText('x ' + fmt(m), cx, Y(-0.040));
      });
    });
    var pan = new T.Mesh(new T.PlaneGeometry(PWn, PDn), new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }));
    pan.rotation.x = -Math.PI / 2; pan.position.y = BH + 0.0006; g.add(pan);
    var knurl = S.canvasTex(256, 32, function (c, w, h) { c.fillStyle = '#15161a'; c.fillRect(0, 0, w, h); c.fillStyle = '#3b3e45'; for (var i = 0; i < w; i += 9) c.fillRect(i, 0, 3, h); });
    var dials = muls.map(function (m, i) {
      var d = new T.Group(); d.position.set(dx[i], BH + 0.001, 0.004); g.add(d);
      var kb = S.mesh(new T.CylinderGeometry(0.015, 0.0165, 0.012, 32), new T.MeshStandardMaterial({ map: knurl, roughness: 0.42 })); kb.position.y = 0.006; d.add(kb);
      var cap = S.mesh(new T.CylinderGeometry(0.0115, 0.0115, 0.0015, 32), M.chrome); cap.position.y = 0.0128; d.add(cap);
      var ptr = S.mesh(new T.BoxGeometry(0.0022, 0.0012, 0.013), M.white, false); ptr.position.set(0, 0.0136, 0.0075); d.add(ptr);
      return { g: d, mul: m, digit: 0, top: new T.Vector3(x + dx[i], BH + 0.015, z + 0.004) };
    });
    S.contact(BW + 0.06, BD + 0.06, x, z, 0.5);
    var api = { group: g, dials: dials, muls: muls, unit: unit,
      value: function () { var v = 0; dials.forEach(function (d) { v += d.digit * d.mul; }); return v; },
      max: function () { var v = 0; dials.forEach(function (d) { v += 9 * d.mul; }); return v; },
      look: function () { dials.forEach(function (d) { d.g.rotation.y = d.digit * Math.PI / 5; }); },
      put: function (value) { var left = value, want = [];
        muls.forEach(function (m) { var d = Math.max(0, Math.min(9, Math.floor(left / m + 1e-9))); want.push(d); left -= d * m; });
        dials.forEach(function (d, i) { d.digit = want[i]; }); api.look(); } };
    return api;
  }
  var rBox = decade(-0.44, 0.08, [1000, 100, 10, 1], 'RESISTANCE BOX', 'Ω', function (m) { return String(m); });
  var lBox = decade(-0.13, 0.12, [100, 10, 1], 'INDUCTANCE BOX  mH', 'mH', function (m) { return String(m); });
  var cBox = decade(0.2, 0.12, [1, 0.1, 0.01, 0.001], 'CAPACITANCE BOX  µF', 'µF',
    function (m) { return m >= 1 ? String(m) : m.toFixed(3).replace(/0+$/, ''); });
  rBox.put(Math.round(p.R));
  if (ISLCR) lBox.put(Math.round(p.L * 1000 * 10) / 10);
  cBox.put(Math.round(p.C * 1e6 * 1000) / 1000);

  /* ---------------------------------------------------------------- leads */
  function lead(a, b, color, via, lift) {
    var up = lift === undefined ? 0.02 : lift, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.005, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color);
    if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; }
    return w;
  }
  var ammPlus = amm.userData.plus.getWorldPosition(new T.Vector3());
  var ammMinus = amm.userData.minus.getWorldPosition(new T.Vector3());
  lead(gen.out, ammPlus, 'red', [[-0.4, -0.2], [-0.3, -0.12]]);
  lead(ammMinus, new T.Vector3(-0.44, 0.045, 0.03), 'black', [[-0.3, 0.0]]);
  lead(new T.Vector3(-0.4, 0.045, 0.03), new T.Vector3(-0.18, 0.045, 0.07), '#d9a520', [[-0.3, 0.1]]);
  lead(new T.Vector3(-0.08, 0.045, 0.07), new T.Vector3(0.15, 0.045, 0.07), 'blue', [[0.04, 0.1]]);
  lead(new T.Vector3(0.25, 0.045, 0.07), gen.outN, 'black', [[0.34, -0.06], [0.0, -0.22], [-0.3, -0.3]]);
  lead(cro.chA, new T.Vector3(-0.42, 0.045, 0.03), new T.Color ? 'red' : 'red', [[0.1, -0.26], [-0.2, -0.16]]);
  lead(cro.chB, new T.Vector3(0.18, 0.045, 0.07), 'blue', [[0.3, -0.2]]);
  lead(cro.earth, new T.Vector3(0.26, 0.045, 0.07), 'black', [[0.34, -0.2]]);

  S.addApparatus('gen', gen.group, 'Function generator',
    'A sine generator. The dial sets the frequency and the display reads it; the amplitude knob is set once and then left alone, because the whole experiment compares readings at one applied voltage.');
  S.addApparatus('cro', cro.group, 'Dual-trace oscilloscope',
    'Channel 1 shows the generator\'s own voltage and channel 2 the voltage across the part being measured, so their sizes and the phase between them are read straight off the screen.');
  S.addApparatus('amm', amm, 'Alternating-current milliammeter', 'In the supply lead, so it reads the current the generator drives.');
  S.addApparatus('rbx', rBox.group, 'Decade resistance box', 'Four dials: thousands, hundreds, tens and units of ohms.');
  if (ISLCR) S.addApparatus('lbx', lBox.group, 'Decade inductance box', 'The coil whose inductance the experiment is to find. Its dials are not read: that would be cheating the measurement.');
  S.addApparatus('cbx', cBox.group, 'Decade capacitance box', 'Dials in microfarads, down to a thousandth of a microfarad.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  /* ---------------------------------------------------------------- readings */
  function cur(f) { return ISLCR ? at(f).I : 0; }
  function gain(f) { return at(f).gain; }
  var hudA = S.hudCard('Generator'), hudB = S.hudCard(ISLCR ? 'Milliammeter' : 'Output / input'),
    hudC = S.hudCard(ISLCR ? 'Impedance' : 'Gain');

  function trace() {
    st.traced = true; S.focus('gen');
    S.say(ISLCR
      ? (PAR ? 'The coil and the capacitor are in parallel across the generator, and the milliammeter is in the lead that feeds them both.'
        : 'The generator, the milliammeter, the resistance box, the coil and the capacitor are all in one series loop.')
      : 'The resistance box and the capacitor are in series across the generator. Channel 1 of the oscilloscope is on the generator and channel 2 on the output.');
    S.render();
  }
  function setFreq(f) {
    if (busy()) return Promise.resolve(false);
    if (!(f >= 20 && f <= 50000)) { S.say('The generator covers 20 Hz to 50 kHz.'); return Promise.resolve(false); }
    f = Math.round(f * 10) / 10;
    var from = st.f;
    return S.hand.pinchMove(gen.dialAt, function () { return gen.dialAt; },
      function (k) { st.f = from + (f - from) * k; gen.turn(st.f); }, { mode: 'front', ms: 480, reachMs: 520 })
      .then(function () { st.f = f; gen.turn(f); S.render(); return true; });
  }
  function setBox(box, value, what) {
    if (busy()) return Promise.resolve(false);
    if (!(value > 0 && value <= box.max())) { S.say('That box goes up to ' + box.max() + ' ' + box.unit + ' only.'); return Promise.resolve(false); }
    var left = value, want = [];
    box.muls.forEach(function (m) { var d = Math.max(0, Math.min(9, Math.floor(left / m + 1e-9))); want.push(d); left -= d * m; });
    var jobs = [];
    want.forEach(function (d, i) { if (Math.abs(box.dials[i].digit - d) > 1e-9) jobs.push([i, d]); });
    return jobs.reduce(function (pr, j) {
      return pr.then(function () {
        var dl = box.dials[j[0]], a = dl.digit, b = j[1];
        return S.hand.pinchMove(dl.top, function () { return dl.top; }, function (k) { dl.digit = a + (b - a) * k; box.look(); },
          { mode: 'top', ms: 340 + 45 * Math.abs(b - a), reachMs: 440 })
          .then(function () { dl.digit = b; box.look(); S.click(1200, 0.02, 0.05); });
      });
    }, Promise.resolve()).then(function () { st.set = true;
      S.say(what + ' set to ' + value + ' ' + box.unit + '.'); S.render(); return true; });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.f - st.f) < Math.max(1, st.f * 0.0008); })) {
      S.say('There is already a reading at ' + fHz(st.f) + '.'); return false;
    }
    var v = at(st.f);
    if (ISLCR) {
      S.addRow({ f: st.f, I: v.I, Z: v.Z });
      S.say('Written in your record book: at ' + fHz(st.f) + ' the current is ' + (v.I * 1000).toFixed(3) + ' mA.');
    } else {
      S.addRow({ f: st.f, g: v.gain, dB: v.dB, ph: v.phase, Z: v.Z });
      S.say('Written in your record book: at ' + fHz(st.f) + ' the output is ' + (v.gain * p.V).toFixed(3) +
        ' V of the ' + p.V.toFixed(2) + ' V applied.');
    }
    return true;
  }

  /* ---------------------------------------------------------------- results */
  function vertex(a, b, c) {                      // the turning point of the parabola through three points
    var d = (a[0] - b[0]) * (a[0] - c[0]) * (b[0] - c[0]);
    if (!d) return b[0];
    var A = (c[0] * (b[1] - a[1]) + b[0] * (a[1] - c[1]) + a[0] * (c[1] - b[1])) / d;
    var Bq = (c[0] * c[0] * (a[1] - b[1]) + b[0] * b[0] * (c[1] - a[1]) + a[0] * a[0] * (b[1] - c[1])) / d;
    return A === 0 ? b[0] : -Bq / (2 * A);
  }
  function coarseBest() {                        // the frequency of the biggest (or smallest) reading so far
    var best = null, i;
    for (i = 0; i < S.rows.length; i++) {
      if (!best || (PAR ? S.rows[i].I < best.I : S.rows[i].I > best.I)) best = S.rows[i];
    }
    return best ? best.f : f0;
  }
  function turningPoint(wantMax) {
    var pts = S.rows.map(function (r) { return [r.f, r.I]; }).filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); });
    pts.sort(function (a, b) { return a[0] - b[0]; });
    if (pts.length < 3) return null;
    var bi = 0;
    for (var i = 1; i < pts.length; i++) if (wantMax ? pts[i][1] > pts[bi][1] : pts[i][1] < pts[bi][1]) bi = i;
    if (bi === 0 || bi === pts.length - 1) return { f: pts[bi][0], peak: pts[bi][1], pts: pts, edge: true };
    return { f: vertex(pts[bi - 1], pts[bi], pts[bi + 1]), peak: pts[bi][1], pts: pts, edge: false };
  }
  function crossing(pts, lo, hi, want) {          // linear interpolation between the two rows that straddle `want`
    for (var i = lo; i !== hi; i += (hi > lo ? 1 : -1)) {
      var a = pts[i], b = pts[i + (hi > lo ? 1 : -1)];
      if (!b) return NaN;
      if ((a[1] - want) * (b[1] - want) <= 0 && a[1] !== b[1]) return a[0] + (b[0] - a[0]) * (want - a[1]) / (b[1] - a[1]);
    }
    return NaN;
  }
  function seriesResult() {
    var tp = turningPoint(true);
    if (!tp || tp.edge) return null;
    var fr = tp.f, L = 1 / (4 * Math.PI * Math.PI * fr * fr * p.C);
    var bi = 0, i;
    for (i = 1; i < tp.pts.length; i++) if (tp.pts[i][1] > tp.pts[bi][1]) bi = i;
    var want = tp.peak / Math.SQRT2;
    var f1 = crossing(tp.pts, bi, 0, want), f2 = crossing(tp.pts, bi, tp.pts.length - 1, want);
    var note = 'Resonance read off the curve at ' + fHz(fr) + ', with a peak current of ' + (tp.peak * 1000).toFixed(3) + ' mA. ';
    if (isFinite(f1) && isFinite(f2)) note += 'The half-power points are at ' + fHz(f1) + ' and ' + fHz(f2) +
      ', a bandwidth of ' + Math.round(f2 - f1) + ' Hz, so Q = ' + (fr / (f2 - f1)).toFixed(1) +
      ' against (1/R)√(L/C) = ' + (Math.sqrt(L / p.C) / p.R).toFixed(1) + '.';
    return { label: 'Inductance of the coil', value: L * 1000, unit: 'mH', digits: 2, truth: p.L * 1000, note: note };
  }
  function parallelResult() {
    var tp = turningPoint(false);
    if (!tp || tp.edge) return null;
    var fr = tp.f, zdyn = p.V / tp.peak;
    return { label: 'Anti-resonant frequency', value: fr, unit: 'Hz', digits: 1,
      truth: HK.TEXTBOOK.lcr_far(p),
      note: 'The supply current fell to ' + (tp.peak * 1000).toFixed(3) + ' mA there, so the impedance of the ' +
        'combination is ' + Math.round(zdyn) + ' Ω against the dynamic impedance L/(CR) = ' +
        Math.round(p.L / (p.C * p.R)) + ' Ω, and Q = 2πf L/R = ' +
        (2 * Math.PI * fr * p.L / p.R).toFixed(1) + '.' };
  }
  function fcFromRow(r) {                          // every single reading gives the cut-off on its own
    var g = r.g;
    if (!(g > 0 && g < 1)) return NaN;
    return HIGH ? r.f * Math.sqrt(1 - g * g) / g : r.f * g / Math.sqrt(1 - g * g);
  }
  function fcMean() {
    var v = S.rows.map(fcFromRow).filter(function (x) { return isFinite(x) && x > 0; });
    return v.length ? v.reduce(function (a, b) { return a + b; }, 0) / v.length : NaN;
  }
  function rcResult() {
    var fc = fcMean();
    if (!isFinite(fc) || S.rows.length < 5) return null;
    var C = 1 / (2 * Math.PI * p.R * fc);
    return { label: 'Capacitance', value: C * 1e6, unit: 'µF', digits: 4, truth: p.C * 1e6,
      note: 'The reactance equals the resistance at ' + fHz(fc) + ', where the output is 0.707 of the input and ' +
        'the phase is 45°. Every reading gives that frequency on its own from the measured ratio, and they ' +
        'agree with each other.' };
  }
  function responseResult() {
    var fc = fcMean();
    if (!isFinite(fc) || S.rows.length < 6) return null;
    var hi = S.rows.filter(function (r) { return r.f > fc * 3; }).sort(function (a, b) { return a.f - b.f; });
    var slope = hi.length >= 2 ? (hi[hi.length - 1].dB - hi[0].dB) / (Math.log10(hi[hi.length - 1].f) - Math.log10(hi[0].f)) : NaN;
    return { label: 'Cut-off frequency', value: fc, unit: 'Hz', digits: 1, truth: HK.TEXTBOOK.rc_fc(p),
      note: 'The gain is 3 dB down there. ' + (isFinite(slope)
        ? 'Well past the corner the response falls at ' + slope.toFixed(1) + ' dB per decade, which is the ' +
          'expected 20 dB per decade for one RC section.'
        : 'Take readings a decade past the corner to measure the roll-off.') };
  }

  /* ---------------------------------------------------------------- the frequency plans */
  function geom(a, b, n) {
    var lo = Math.max(20, a), hi = Math.min(50000, b), out = [], i;
    for (i = 0; i < n; i++) out.push(Math.round(lo * Math.pow(hi / lo, i / (n - 1)) * 10) / 10);
    return out;
  }
  var COARSE = ISLCR ? geom(f0 / 3, f0 * 3, 13) : geom(f0 / 60, f0 * 60, 13);
  /* The close readings are spread over the whole gap between the coarse points either side of the biggest
     reading, so the turning point is certainly inside them, two per cent apart. */
  function fineList(around) { return geom(around / 1.21, around * 1.21, 21); }

  var SETUP = { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
      u.h2('Set the bench up');
      u.p(ISLCR ? (PAR ? 'The coil and the capacitor go in parallel across the generator, with the milliammeter in the supply lead.'
        : 'The resistance box, the coil and the capacitor go in series with the generator and the milliammeter.')
        : 'The resistance box and the capacitor go in series across the generator, with the oscilloscope on both ends of the output.');
      u.task('1. Trace the circuit', st.traced, st.traced ? 'Traced' : 'Follow the leads from the generator')
        .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
      var okR = Math.abs(rBox.value() - Math.round(p.R)) < 0.5;
      u.task('2. Set the resistance box', okR, 'R = ' + rBox.value() + ' Ω')
        .add(u.button('Resistance box to ' + Math.round(p.R) + ' Ω', function () { S.focus('rbx'); setBox(rBox, Math.round(p.R), 'The resistance box'); }, !okR, S.hand.busy));
      var cWant = Math.round(p.C * 1e6 * 1000) / 1000, okC = Math.abs(cBox.value() - cWant) < 0.0005;
      u.task('3. Set the capacitance box', okC, 'C = ' + cBox.value().toFixed(3) + ' µF')
        .add(u.button('Capacitance box to ' + cWant + ' µF', function () { S.focus('cbx'); setBox(cBox, cWant, 'The capacitance box'); }, !okC, S.hand.busy));
      u.live(function () { return 'Generator at ' + fHz(st.f) + ', amplitude ' + p.V.toFixed(2) + ' V' +
        (ISLCR ? '  ·  milliammeter ' + (cur(st.f) * 1000).toFixed(3) + ' mA' : '  ·  output ' + (gain(st.f) * p.V).toFixed(3) + ' V'); });
      u.note('Leave the amplitude knob alone from here on: every reading has to be taken at the same applied voltage.');
      u.next('Next: take the readings', st.traced && okR && okC);
    },
    ok: function () { return st.traced && Math.abs(rBox.value() - Math.round(p.R)) < 0.5; },
    auto: function () {
      trace();
      return setBox(rBox, Math.round(p.R), 'The resistance box')
        .then(function () { return setBox(cBox, Math.round(p.C * 1e6 * 1000) / 1000, 'The capacitance box'); });
    } };

  function sweepStep(title, list, fn, minRows, nextLabel) {
    return { id: title.id, title: title.t, view: 'gen', render: function (u) {
        u.h2(title.h); u.p(title.p);
        var row = u.row();
        fn().forEach(function (f) {
          var done = S.rows.some(function (r) { return Math.abs(r.f - f) < Math.max(1, f * 0.0008); });
          row.appendChild(u.button(fHz(f) + (done ? ' ✓' : ''), function () {
            setFreq(f).then(function (ok) { if (ok) record(); }); }, Math.abs(st.f - f) < 0.5, S.hand.busy));
        });
        var sl = { v: st.f };
        u.slider('Generator frequency', 20, ISLCR ? Math.round(f0 * 4) : 50000, 10, function () { return sl.v; }, function (v) { sl.v = v; }, 'Hz', 0);
        u.row(u.button('Set the generator here', function () { setFreq(sl.v); }, false, S.hand.busy),
          u.button('Record this reading', function () { record(); }, true, S.hand.busy));
        u.live(function () { var v = at(st.f);
          return ISLCR ? fHz(st.f) + '  ·  ' + (v.I * 1000).toFixed(3) + ' mA  ·  impedance ' + Math.round(v.Z) + ' Ω'
            : fHz(st.f) + '  ·  output ' + (v.gain * p.V).toFixed(3) + ' V  ·  ' + v.dB.toFixed(2) + ' dB  ·  phase ' + (v.phase * 180 / Math.PI).toFixed(0) + '°'; });
        u.h3('Observation table'); u.table();
        if (S.rows.length < minRows) u.p(S.rows.length + ' of at least ' + minRows + ' readings recorded.');
        u.next(nextLabel, S.rows.length >= minRows);
      },
      ok: function () { return S.rows.length >= minRows; },
      auto: function () {
        return fn().reduce(function (pr, f) {
          return pr.then(function () { return setFreq(f); }).then(function (ok) { if (ok) record(); });
        }, Promise.resolve());
      } };
  }

  var STEPS;
  if (ISLCR) {
    STEPS = [SETUP,
      sweepStep({ id: 'coarse', t: 'Sweep', h: 'Sweep the frequency', p: 'Take a reading at each frequency on the row. The meter ' + (PAR ? 'dips to a minimum' : 'rises to a maximum') + ' somewhere in the middle of the range.' },
        null, function () { return COARSE; }, 10, 'Next: close readings round the turning point'),
      sweepStep({ id: 'fine', t: 'Close readings', h: 'Close readings round the turning point',
        p: 'Now take readings in small steps either side of it, so that the ' + (PAR ? 'minimum' : 'peak') + ' can be fixed to better than a per cent.' },
        null, function () { return fineList(coarseBest()); }, 26, 'Next: the result')];
  } else {
    STEPS = [SETUP,
      sweepStep({ id: 'sweep', t: 'Readings', h: 'The output over three decades',
        p: 'Hold the amplitude the same and read the output at each frequency on the row, from well below the corner to well above it.' },
        null, function () { return COARSE; }, 10, 'Next: the result')];
  }

  var RES = ISLCR ? (PAR ? parallelResult : seriesResult)
    : (S.lab.id.indexOf('response') >= 0 || (S.lab.variant && S.lab.variant.base === 'rc-frequency-response') ? responseResult : rcResult);

  return {
    camera: { pos: [0.0, 1.0, 1.0], look: [0, 0.06, -0.18] },
    views: { bench: [[0.0, 1.0, 1.0], [0, 0.06, -0.18]], gen: [[-0.3, 0.55, 0.1], [-0.42, 0.08, -0.4]],
      cro: [[0.24, 0.55, 0.06], [0.22, 0.12, -0.44]], amm: [[-0.2, 0.3, 0.26], [-0.2, 0.05, -0.06]],
      rbx: [[-0.44, 0.3, 0.36], [-0.44, 0.03, 0.08]], lbx: [[-0.13, 0.3, 0.4], [-0.13, 0.03, 0.12]],
      cbx: [[0.2, 0.3, 0.4], [0.2, 0.03, 0.12]], book: [[0.56, 0.46, 0.44], [0.56, 0.0, 0.0]] },
    theory: {
      principle: S.lab.theory,
      formula: ISLCR ? (PAR ? 'fₐ ≈ 1/(2π√(LC)),   Zₘₐₓ ≈ L/(CR)'
        : 'f₀ = 1/(2π√(LC)),   Δf = R/(2πL),   Q = f₀/Δf')
        : 'gain = 1/√(1 + (f/f_c)²),   f_c = 1/(2πRC)',
      formulaNote: 'the turning point is read off the measured curve, never taken from the formula',
      more: [
        'The generator\'s amplitude is set once and left alone. Every comparison in this experiment is between readings at the same applied voltage, so a knob nudged half way through spoils the whole set.',
        ISLCR ? 'Take the coarse sweep first to find roughly where the turning point is, then crowd the readings into a few per cent either side of it. A resonance curve read at ten widely spaced frequencies fixes the peak badly; the same ten readings crowded round it fix it well.'
          : 'Spread the readings evenly on a logarithmic scale - two or three a decade - because the response is a straight line against log f, not against f.',
        'The oscilloscope is the honest instrument here: it shows the shape of both voltages at once, so a distorted waveform or a loose lead is seen at once instead of being averaged into the table.'],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, at: [0.56, 0.0, -0.1],
      lines: ISLCR
        ? ['Aim: to study ' + (PAR ? 'anti-resonance in a parallel' : 'resonance in a series') + ' LCR circuit',
          'and to find the ' + (PAR ? 'anti-resonant frequency and Q.' : 'inductance, bandwidth and Q.'),
          'Applied voltage held at ' + p.V.toFixed(2) + ' V throughout',
          PAR ? 'Z is greatest, so I is least, at anti-resonance' : 'f0 = 1/(2 pi sqrt(LC)),  Q = f0 / (f2 - f1)']
        : ['Aim: to measure the response of a series RC circuit', 'and to find its cut-off frequency.',
          'R = ' + Math.round(p.R) + ' ohm, applied voltage ' + p.V.toFixed(2) + ' V',
          'gain = 1 / sqrt(1 + (f/fc)^2),  fc = 1/(2 pi R C)'],
      columns: ISLCR
        ? [{ label: 'S.No', get: function (r, i) { return i + 1; } },
          { label: 'f (Hz)', get: function (r) { return r.f >= 1000 ? r.f.toFixed(0) : r.f.toFixed(1); } },
          { label: 'I (mA)', get: function (r) { return (r.I * 1000).toFixed(3); } },
          { label: 'Z (Ω)', get: function (r) { return Math.round(r.Z); } }]
        : [{ label: 'S.No', get: function (r, i) { return i + 1; } },
          { label: 'f (Hz)', get: function (r) { return r.f >= 1000 ? r.f.toFixed(0) : r.f.toFixed(1); } },
          { label: 'V out (V)', get: function (r) { return (r.g * p.V).toFixed(4); } },
          { label: 'Vout/Vin', get: function (r) { return r.g.toFixed(4); } },
          { label: 'dB', get: function (r) { return r.dB.toFixed(2); } }] },
    graph: ISLCR
      ? { x: function (r) { return r.f; }, y: function (r) { return r.I * 1000; }, xlabel: 'f (Hz)', ylabel: 'I (mA)', y0: 0 }
      : { x: function (r) { return Math.log10(r.f); }, y: function (r) { return r.dB; }, xlabel: 'log f (f in Hz)', ylabel: 'gain (dB)' },
    result: RES,
    tol: 0.02,
    resultNote: ISLCR
      ? 'The sharpness of the curve is the measurement: a tall narrow peak is a high Q, and Q is what makes a tuned circuit select one station out of many.'
      : 'A straight line on the decibel against log-frequency plot is the signature of a single RC section, and its corner is the cut-off frequency.',
    chips: ISLCR
      ? ['Why does the current peak?', 'Check my readings', 'What does Q mean here?', 'Why crowd readings near the peak?']
      : ['Why is the gain 0.707 at the corner?', 'Check my readings', 'Why plot decibels against log f?', 'What sets the roll-off?'],
    viva: ISLCR
      ? (PAR
        ? [['At anti-resonance the current from the generator is', ['The least', 'The greatest', 'Unchanged'], 0, 'The impedance of the combination is greatest.'],
          ['A parallel LCR circuit is called', ['A rejector', 'An acceptor', 'A divider'], 0, 'It rejects the anti-resonant frequency from the supply lead.'],
          ['The impedance at anti-resonance is about', ['L/(CR)', 'R', '2πfL'], 0, 'The two branch currents cancel all but a small resistive part.']]
        : [['At series resonance the impedance is', ['Equal to R', 'Zero', 'The largest'], 0, 'The two reactances cancel.'],
          ['The bandwidth of a series circuit is', ['R/(2πL)', 'L/(2πR)', '1/(2πRC)'], 0, 'It follows from the half-power condition.'],
          ['A series resonant circuit is called', ['An acceptor', 'A rejector', 'A filter'], 0, 'At resonance it offers the least opposition.']])
      : [['At the cut-off frequency the output is', ['0.707 of the input', 'Half the input', 'Zero'], 0, 'The reactance equals the resistance, so the sum in quadrature gives √2.'],
        ['One RC section rolls off at', ['20 dB per decade', '10 dB per decade', '40 dB per decade'], 0, 'The gain falls as 1/f past the corner.'],
        ['The phase shift at the corner is', ['45°', '90°', '0°'], 0, 'The resistance and the reactance are equal there.']],
    askState: function () {
      var v = at(st.f);
      return { experiment: S.lab.title, generator_frequency_hz: st.f, applied_volts: p.V,
        resistance_box_ohm: rBox.value(), capacitance_box_uF: cBox.value(),
        meter_reading: ISLCR ? (v.I * 1000).toFixed(3) + ' mA' : (v.gain * p.V).toFixed(4) + ' V out',
        impedance_ohm: Math.round(v.Z), phase_degrees: +(v.phase * 180 / Math.PI).toFixed(1),
        readings_taken: S.rows.length };
    },
    steps: STEPS,
    tick: function (dt) {
      var v = at(st.f);
      gen.show(st.f);
      cro.draw(p.V, v.gain, v.phase, st.f);
      if (ISLCR) amm.set(v.I * 1000);
      hudA.set(fHz(st.f));
      hudB.set(ISLCR ? (v.I * 1000).toFixed(3) + ' mA' : v.gain.toFixed(4));
      hudC.set(ISLCR ? Math.round(v.Z) + ' Ω' : v.dB.toFixed(2) + ' dB');
    }
  };
});
