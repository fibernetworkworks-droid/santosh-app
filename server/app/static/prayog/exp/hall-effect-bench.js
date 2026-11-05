/* Prayogshala studio module: HALL EFFECT BENCH (B.Sc. solid state physics).
   An electromagnet with flat pole pieces, a germanium crystal on a thin Hall probe board in the gap, a digital
   gaussmeter with its own probe, a constant-current source for the crystal and a millivoltmeter across its width.
   Physics: the `hallbar` kernel of packs/modern_ug.js on the lab's own params - the same code the server checks
   against VH = I B / (n e t). The sign of the Hall voltage is the carrier's own sign. */
HoolaStudio.define('hall-effect-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.hallbar, assign = HK.assign;
  var p = HK.paramsFor('hallbar', S.lab.params);
  var QEL = 1.602176634e-19;
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || 'Germanium crystal on a Hall probe board';
  var BMAX = 0.6, BSTEP = 0.05, VLC = 0.01;             // field range (T), knob step, millivoltmeter least count
  var st = { inGap: false, current: false, B: 0, zero: null, done: {} };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function qAt(b) { return assign(p, { B: st.inGap ? b : 0 }); }
  function hallMv() { return st.current ? KN.hallV(qAt(st.B)) * 1000 : 0; }
  function readMv() { return rnd(hallMv(), 2); }
  function readB() { return rnd(st.inGap ? st.B : 0, 3); }

  // ================================================================ the electromagnet
  var mag = new T.Group(); S.scene.add(mag); mag.position.set(-0.26, 0, -0.14);
  var ironM = new T.MeshStandardMaterial({ color: 0x3f444b, roughness: 0.62, metalness: 0.65 });
  var yokeB = S.rounded(0.26, 0.1, 0.024, 0.006, ironM); yokeB.rotation.x = -Math.PI / 2; yokeB.position.y = 0.012;
  mag.add(yokeB);
  [-1, 1].forEach(function (sg) {
    var up2 = S.rounded(0.034, 0.08, 0.14, 0.006, ironM); up2.rotation.x = -Math.PI / 2;
    up2.position.set(sg * 0.1, 0.082, 0); mag.add(up2);
    var arm2 = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.062, 24), ironM); arm2.rotation.z = Math.PI / 2;
    arm2.position.set(sg * 0.063, 0.14, 0); mag.add(arm2);
    var pole = S.mesh(new T.CylinderGeometry(0.026, 0.026, 0.012, 28), new T.MeshStandardMaterial({ color: 0x9aa2ab, roughness: 0.35, metalness: 0.85 }));
    pole.rotation.z = Math.PI / 2; pole.position.set(sg * 0.026, 0.14, 0); mag.add(pole);
    // the coil: a stack of copper rings
    var coilT = S.canvasTex(256, 64, function (x, w, h) { x.fillStyle = '#b06a3a'; x.fillRect(0, 0, w, h);
      x.strokeStyle = '#7d4320'; x.lineWidth = 3; for (var i = 0; i < h; i += 6) { x.beginPath(); x.moveTo(0, i); x.lineTo(w, i); x.stroke(); } });
    var coil = S.mesh(new T.CylinderGeometry(0.042, 0.042, 0.05, 28),
      new T.MeshStandardMaterial({ map: coilT, roughness: 0.5, metalness: 0.5 }));
    coil.rotation.z = Math.PI / 2; coil.position.set(sg * 0.072, 0.14, 0); mag.add(coil);
    var cheek = S.mesh(new T.CylinderGeometry(0.046, 0.046, 0.004, 28), M.bakelite); cheek.rotation.z = Math.PI / 2;
    cheek.position.set(sg * 0.047, 0.14, 0); mag.add(cheek);
  });
  var gapGlow = new T.MeshBasicMaterial({ color: 0x6fa8ff, transparent: true, opacity: 0, depthWrite: false,
    blending: T.AdditiveBlending });
  var gapM = S.mesh(new T.CylinderGeometry(0.024, 0.024, 0.04, 24, 1, true), gapGlow, false, false);
  gapM.rotation.z = Math.PI / 2; gapM.position.set(0, 0.14, 0); mag.add(gapM);
  var magLbl = S.label('ELECTROMAGNET  ·  POLE GAP 40 mm', { w: 0.15, ratio: 0.13, color: '#e8eaec' });
  magLbl.rotation.x = -Math.PI / 2; magLbl.position.set(0, 0.0252, 0.044); mag.add(magLbl);
  S.contact(0.34, 0.2, -0.26, -0.14, 0.55);

  // ================================================================ the Hall probe board
  var probe = new T.Group(); S.scene.add(probe);
  var PARK = new T.Vector3(-0.02, 0.02, 0.14), INGAP = new T.Vector3(-0.26, 0.14, -0.14);   // the gap is at the magnet's own z
  var pcb = S.mesh(new T.BoxGeometry(0.018, 0.0025, 0.1), new T.MeshStandardMaterial({ color: 0x17572f, roughness: 0.6 }));
  probe.add(pcb);
  var xtal = S.mesh(new T.BoxGeometry(0.01, 0.0008, 0.016),
    new T.MeshStandardMaterial({ color: 0x6e747c, roughness: 0.22, metalness: 0.85 }));
  xtal.position.set(0, 0.0017, 0.0); probe.add(xtal);
  [[-0.005, 0.03], [0.005, 0.03], [-0.005, -0.03], [0.005, -0.03]].forEach(function (q) {
    var pad = S.mesh(new T.BoxGeometry(0.005, 0.0006, 0.006), M.brass); pad.position.set(q[0], 0.0016, q[1]);
    probe.add(pad);
  });
  var handleP = S.mesh(new T.BoxGeometry(0.014, 0.004, 0.03), M.bakelite); handleP.position.set(0, 0.0015, 0.062);
  probe.add(handleP);
  probe.position.copy(PARK);
  var gauss = new T.Group(); S.scene.add(gauss); gauss.position.set(-0.26, 0.14, -0.17);
  var gprobe = S.mesh(new T.BoxGeometry(0.01, 0.002, 0.07), new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.6 }));
  gauss.add(gprobe);
  var gtip = S.mesh(new T.BoxGeometry(0.008, 0.0015, 0.008), M.brass); gtip.position.set(0, 0.0012, 0.03);
  gauss.add(gtip);

  // ================================================================ the three boxes
  function box(x, z, rotY, title, sub, wdt) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = rotY;
    var W = wdt || 0.2, D = 0.15, Hh = 0.085;
    var cse = S.rounded(W, D, Hh, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 }));
    cse.rotation.x = -Math.PI / 2; cse.position.y = Hh / 2 + 0.003; g.add(cse);
    var FZ = D / 2 + 0.005, PW = W - 0.012, PH = Hh - 0.012;
    var tex = S.canvasTex(900, Math.round(900 * PH / PW), function (xx, w, h) {
      xx.fillStyle = '#2b323d'; xx.fillRect(0, 0, w, h);
      xx.strokeStyle = 'rgba(255,255,255,.12)'; xx.lineWidth = 3; xx.strokeRect(8, 8, w - 16, h - 16);
      xx.fillStyle = '#f1efe8'; xx.font = '700 32px "Public Sans", sans-serif'; xx.fillText(title, 24, 50);
      xx.font = '500 23px "Public Sans", sans-serif'; xx.fillStyle = '#c7ccd6'; xx.fillText(sub, 24, 86);
    });
    var fac = S.mesh(new T.BoxGeometry(PW, PH, 0.004),
      [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]);
    fac.position.set(0, 0.003 + Hh / 2, FZ - 0.002); g.add(fac);
    var lcdT = S.liveTex(512, 180), last = '';
    var bez = S.mesh(new T.BoxGeometry(PW * 0.52, PH * 0.4, 0.003), M.grey);
    bez.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.17, FZ + 0.001); g.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(PW * 0.48, PH * 0.36), new T.MeshBasicMaterial({ map: lcdT, toneMapped: false }));
    scr.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.17, FZ + 0.004); g.add(scr);
    var knobG = new T.Group(); knobG.position.set(-PW * 0.28, 0.003 + Hh / 2 - PH * 0.17, FZ + 0.004); g.add(knobG);
    var kk = S.mesh(new T.CylinderGeometry(0.013, 0.014, 0.012, 28), M.bakelite); kk.rotation.x = Math.PI / 2;
    knobG.add(kk);
    var kp = S.mesh(new T.BoxGeometry(0.0018, 0.013, 0.001), M.white, false); kp.position.set(0, 0.0075, 0.007);
    knobG.add(kp);
    S.contact(W + 0.06, D + 0.06, x, z, 0.5);
    return { group: g, knob: knobG,
      show: function (txt, u2) {
        if (txt + u2 === last) return; last = txt + u2;
        lcdT.draw(function (xx) {
          var gr = xx.createLinearGradient(0, 0, 0, 180); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
          xx.fillStyle = gr; xx.fillRect(0, 0, 512, 180);
          xx.font = '700 88px "JetBrains Mono", monospace'; xx.textAlign = 'right';
          xx.fillStyle = 'rgba(0,0,0,.07)'; xx.fillText('88.888', 400, 116);
          xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 116);
          xx.font = '600 32px "Public Sans", sans-serif'; xx.fillText(u2, 498, 150);
        });
      } };
  }
  var magSup = box(0.1, 0.14, -0.1, 'MAGNET POWER SUPPLY', '0 – 4 A  ·  sets the field in the gap', 0.22);
  var gaussm = box(0.32, -0.04, -0.4, 'DIGITAL GAUSSMETER', 'reads the field in the gap, in tesla', 0.2);
  var hallm = box(0.06, -0.26, 0.1, 'HALL VOLTMETER + CURRENT SOURCE', 'crystal current and Hall voltage', 0.24);
  magSup.show('0.00', 'T set'); gaussm.show('0.000', 'T'); hallm.show('0.00', 'mV');   // read before the first tick

  S.wire([[-0.3, 0.03, -0.06], [-0.1, 0.012, 0.06], [0.06, 0.03, 0.1]], 'red');
  S.wire([[-0.22, 0.03, -0.06], [-0.06, 0.012, 0.1], [0.14, 0.03, 0.1]], 'black');
  S.wire([[-0.26, 0.145, -0.19], [0.0, 0.016, -0.12], [0.28, 0.03, -0.08]], 'gold');
  S.wire([[-0.25, 0.145, -0.1], [-0.02, 0.014, -0.14], [0.02, 0.03, -0.22]], 'blue');
  S.wire([[-0.27, 0.145, -0.1], [-0.06, 0.012, -0.18], [0.1, 0.03, -0.22]], 'green');

  S.addApparatus('mag', mag, 'Electromagnet', 'An iron yoke with two coils and flat pole pieces 40 mm apart. The field in the gap follows the coil current and is read by the gaussmeter, never assumed.');
  S.addApparatus('probe', probe, SAMPLE, 'A thin crystal with four soldered leads: two carry the current along it, two sit opposite each other across its width for the Hall voltage.');
  S.addApparatus('gauss', gauss, 'Gaussmeter probe', 'Its own small Hall element in the same gap, so the field is measured where the crystal is.');
  S.addApparatus('magSup', magSup.group, 'Magnet power supply', 'Sets the coil current and so the field. The coils get warm: do not leave it at full current.');
  S.addApparatus('gaussm', gaussm.group, 'Digital gaussmeter', 'Reads the field in the gap in tesla.');
  S.addApparatus('hallm', hallm.group, 'Hall voltmeter and current source', 'Holds the crystal current steady in milliamperes and reads the millivolts across the crystal\'s width.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudB = S.hudCard('Field in the gap'), hudV = S.hudCard('Hall voltage'), hudR = S.hudCard('Carriers');

  // ================================================================ human actions
  function putInGap() {
    if (busy()) return Promise.resolve();
    if (st.inGap) return Promise.resolve();
    var from = probe.position.clone(), to = INGAP.clone();
    return S.hand.pinchMove(from, function (k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.05 * Math.sin(Math.PI * k) + (to.y - from.y) * k,
        from.z + (to.z - from.z) * k);
    }, function (k) {
      probe.position.set(from.x + (to.x - from.x) * k,
        from.y + 0.05 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
    }, { mode: 'side', ms: 1100, reachMs: 700 }).then(function () {
      probe.position.copy(INGAP); st.inGap = true;
      S.say('The crystal is in the pole gap, flat and square to the field. The current runs along it and the field goes through it, so the Hall voltage appears across its width.');
      S.render();
    });
  }
  function setCurrent(on) {
    if (busy()) return Promise.resolve();
    if (on === st.current) return Promise.resolve();
    return S.hand.tap(hallm.knob, 'front').then(function () {
      st.current = on; S.click(880, 0.05);
      S.say(on ? 'Crystal current set to ' + (p.I * 1000).toFixed(1) + ' mA and held there.' : 'Current off.');
      S.render();
    });
  }
  function zeroIt() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.current) { S.say('Switch the crystal current on first.'); return false; }
    if (st.B > 1e-9) { S.say('Turn the magnet down to zero before taking the zero-field reading.'); return false; }
    st.zero = readMv();
    S.say('Zero-field reading noted: ' + st.zero.toFixed(2) + ' mV. On a real crystal the Hall contacts are never exactly opposite, so this small offset is subtracted from every reading.');
    S.render(); return true;
  }
  function setField(b) {
    if (busy()) return Promise.resolve();
    if (!isFinite(b) || b < 0 || b > BMAX + 1e-9) { S.say('The magnet goes from 0 to ' + BMAX + ' T in this gap.'); return Promise.resolve(); }
    b = rnd(Math.round(b / BSTEP) * BSTEP, 3);
    var b0 = st.B;
    if (Math.abs(b - b0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(wpt(magSup.knob, 0, 0, 0.01), function () { return wpt(magSup.knob, 0, 0, 0.01); },
      function (k) { st.B = b0 + (b - b0) * k; magSup.knob.rotation.z = -st.B / BMAX * 4; },
      { mode: 'front', ms: 500 + 600 * Math.abs(b - b0), reachMs: 620 })
      .then(function () { st.B = b; S.render(); });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.inGap) { S.say('Put the crystal in the pole gap first.'); return false; }
    if (!st.current) { S.say('Switch the crystal current on first.'); return false; }
    if (st.zero === null) { S.say('Take the zero-field reading first.'); return false; }
    var b = readB();
    if (st.done[b]) { S.say('You already have a reading at ' + b.toFixed(2) + ' T. Turn the magnet up.'); return false; }
    st.done[b] = true;
    S.addRow({ B: b, raw: readMv(), Vh: rnd(readMv() - st.zero, 2) });
    S.say('Written in your record book: ' + b.toFixed(2) + ' T, Hall voltage ' + (readMv() - st.zero).toFixed(2) + ' mV.');
    return true;
  }

  function result(rows) {
    var pts = rows.map(function (r) { return [r.B, r.Vh / 1000]; })
      .filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); });
    if (pts.length < 4) return null;
    var m = S.fit.origin(pts);
    if (!isFinite(m) || m === 0) return null;
    var RH = m * p.th / p.I, n = 1 / (Math.abs(RH) * QEL);
    return { label: 'Hall coefficient R_H', value: RH, unit: 'm³/C', digits: 5, truth: p.sg / (p.n21 * 1e21 * QEL),
      note: 'Slope of V_H against B is ' + m.toFixed(4) + ' V/T, and R_H = slope × t / I. The sign says the carriers are '
        + (RH < 0 ? 'electrons (n-type)' : 'holes (p-type)') + ', and their number works out at '
        + (n / 1e21).toFixed(2) + ' × 10²¹ per cubic metre.' };
  }

  return {
    camera: { pos: [-0.02, 0.92, 1.12], look: [-0.04, 0.09, -0.06] },
    views: { mag: [[-0.12, 0.44, 0.3], [-0.26, 0.12, -0.14]], probe: [[-0.16, 0.3, 0.1], [-0.26, 0.13, -0.14]],
      gauss: [[-0.14, 0.28, 0.06], [-0.26, 0.14, -0.16]], magSup: [[0.1, 0.26, 0.36], [0.1, 0.05, 0.14]],
      gaussm: [[0.34, 0.24, 0.18], [0.32, 0.05, -0.04]], hallm: [[0.06, 0.24, -0.04], [0.06, 0.05, -0.26]],
      bench: [[-0.02, 0.92, 1.12], [-0.04, 0.09, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A current in a magnetic field has its carriers pushed sideways. They pile up on one face until the electric field they build up balances the magnetic force, and the voltage across the sample is the Hall voltage. Its SIZE gives the number of carriers; its SIGN says whether they are electrons or holes.',
      formula: 'V_H = I B / (n e t),   R_H = V_H t / (I B) = ± 1 / (n e)',
      formulaNote: 't is the thickness along the field, here ' + (p.th * 1000).toFixed(2) + ' mm',
      more: ['The field is measured with a gaussmeter in the same gap, never worked out from the coil current: iron saturates and remembers.',
        'With the magnet off the Hall leads still show a small voltage, because they are never exactly opposite one another on a real crystal. That offset is taken off every reading.',
        'With the resistivity of the same crystal, the mobility follows as µ = |R_H| / ρ: the Hall effect is the only simple experiment that gives the carrier type, the number and the mobility together.'],
      precautions: 'Keep the crystal flat and square in the gap, use the same current throughout, and do not leave the magnet at full current: the coils get hot and the field drifts.' },
    book: { title: 'Expt. — Hall coefficient of a semiconductor',
      lines: ['Aim: Hall coefficient, carrier type and number.', 'Sample: ' + SAMPLE,
        'Thickness ' + (p.th * 1000).toFixed(2) + ' mm, current ' + (p.I * 1000).toFixed(1) + ' mA.',
        'V_H = I B / (n e t);  R_H = V_H t / (I B)',
        'Zero-field offset subtracted from every reading.'],
      columns: [{ label: 'B (T)', get: function (r) { return r.B.toFixed(2); } },
        { label: 'Reading (mV)', get: function (r) { return r.raw.toFixed(2); } },
        { label: 'V_H (mV)', get: function (r) { return r.Vh.toFixed(2); } },
        { label: 'V_H/B (mV/T)', get: function (r) { return r.B > 0 ? (r.Vh / r.B).toFixed(1) : ''; } }] },
    graph: { x: function (r) { return r.B; }, y: function (r) { return r.Vh; }, xlabel: 'B (T)',
      ylabel: 'V_H (mV)', x0: 0,
      line: function (pts) { var m = S.fit.origin(pts); return isFinite(m) ? function (x) { return m * x; } : null; } },
    result: result,
    tol: 0.03,
    resultNote: 'A straight line through the origin: the Hall voltage is proportional to the field and to the current, and the constant of proportionality counts the carriers inside the crystal. Its sign is the only easy way to tell an n-type sample from a p-type one.',
    chips: ['What does the sign of V_H tell us?', 'Why subtract the zero-field reading?',
      'Why measure B instead of calculating it?', 'Check my readings', 'How is the mobility found?'],
    viva: [['The Hall voltage is proportional to', ['Both the current and the field', 'The field only', 'The thickness'], 0,
      'V_H = IB/(net).'],
      ['A positive Hall coefficient means the carriers are', ['Holes', 'Electrons', 'Both equally'], 0,
        'R_H = +1/(ne) for holes, −1/(ne) for electrons.'],
      ['A thinner crystal gives', ['A larger Hall voltage', 'A smaller Hall voltage', 'No change'], 0,
        'V_H goes as 1/t, which is why Hall samples are made thin.']],
    askState: function () {
      return { experiment: 'Hall effect: coefficient, carrier type and carrier number',
        sample: SAMPLE, crystal_in_gap: st.inGap, current_on: st.current, crystal_current_mA: p.I * 1000,
        field_T: readB(), hall_reading_mV: readMv(), zero_field_offset_mV: st.zero,
        readings_taken: S.rows.length };
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'mag', render: function (u) {
          u.h2('Crystal in the gap, current on, zero noted');
          u.p('Slide the probe board into the pole gap so that the crystal lies flat and square to the field. Set the crystal current to ' + (p.I * 1000).toFixed(1) + ' mA, and with the magnet still off read the small offset across the Hall leads.');
          u.task('1. Crystal in the pole gap', st.inGap, st.inGap ? 'Flat and square in the gap' : 'On the bench')
            .add(u.button(st.inGap ? 'In the gap' : 'Slide it into the gap', function () { S.focus('probe'); putInGap(); }, !st.inGap, st.inGap || S.hand.busy));
          u.task('2. Crystal current', st.current, st.current ? (p.I * 1000).toFixed(1) + ' mA along the crystal' : 'Current source off')
            .add(u.button(st.current ? 'Current is on' : 'Switch the current on', function () { S.focus('hallm'); setCurrent(true); }, !st.current, st.current || S.hand.busy));
          u.task('3. Zero-field reading', st.zero !== null, st.zero === null ? 'Magnet off, read the offset' : 'Offset ' + st.zero.toFixed(2) + ' mV')
            .add(u.button('Note the zero', function () { zeroIt(); }, false, S.hand.busy));
          u.live(function () { return st.current ? 'Field ' + readB().toFixed(2) + ' T  ·  reading ' + readMv().toFixed(2) + ' mV' : 'No current yet'; });
          u.note('The gaussmeter probe is already in the gap beside the crystal: the field is measured, never calculated from the coil current.');
          u.next('Next: raise the field', st.inGap && st.current && st.zero !== null);
        },
        ok: function () { return st.inGap && st.current && st.zero !== null; },
        auto: function () { return putInGap().then(function () { return setCurrent(true); })
          .then(function () { zeroIt(); }); } },

      { id: 'field', title: 'Hall voltage against field', view: 'magSup', render: function (u) {
          u.h2('Raise the field in steps and read the Hall voltage');
          u.p('Turn the magnet supply up in steps of ' + BSTEP.toFixed(2) + ' T. At each step read the gaussmeter and the Hall voltmeter, take the offset off, and record both.');
          var tg = { v: Math.min(BMAX, rnd(st.B + BSTEP, 2)) };
          u.slider('Set the field to', 0, BMAX, BSTEP, function () { return tg.v; }, function (v) { tg.v = v; }, 'T', 2);
          u.row(u.button('Turn the magnet up', function () { setField(tg.v); }, true, S.hand.busy),
            u.button('Record B and V_H', function () { record(); }, false, S.hand.busy));
          u.row(u.button('Magnet back to zero', function () { setField(0); }, false, S.hand.busy || st.B === 0));
          u.live(function () { return readB().toFixed(2) + ' T  ·  reading ' + readMv().toFixed(2) + ' mV  ·  V_H '
            + (st.zero === null ? '—' : (readMv() - st.zero).toFixed(2)) + ' mV'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 5) u.p(S.rows.length + ' of at least 5 fields recorded.');
          u.next('Next: the Hall coefficient', S.rows.length >= 5);
        },
        ok: function () { return S.rows.length >= 5; },
        auto: function () {
          var bs = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6];
          return bs.reduce(function (pr, b) {
            return pr.then(function () { return setField(b); }).then(function () { record(); });
          }, Promise.resolve()).then(function () { return setField(0); });
        } },
    ],

    tick: function () {
      magSup.show(st.B.toFixed(2), 'T set');
      gaussm.show(readB().toFixed(3), 'T');
      hallm.show(st.current ? readMv().toFixed(2) : '0.00', 'mV');
      gapGlow.opacity = Math.min(0.4, st.B / BMAX * 0.4);
      hudB.set(readB().toFixed(3) + ' T');
      hudV.set(st.current ? readMv().toFixed(2) + ' mV' : '—');
      hudR.set(st.current && st.B > 0 ? (hallMv() < 0 ? 'negative: electrons' : 'positive: holes') : '—');
    },
  };
});
