/* Prayogshala studio RIG: the JUNCTION IN A HEATED BATH of wave 8 (B.Sc. solid state physics, engineering physics).
   A germanium diode and a mercury thermometer side by side in a stirred oil bath on a thermostatted hot plate; a DC
   supply holds the diode at a small reverse bias through a plug key and a digital microammeter.
   Physics: the um8_revsat kernel (packs/ug_matter_w8.js) - the same code the server checks. The reverse current is the
   saturation current I_s = C T^3 exp(-Eg / kT); the bath approaches its set point with a time constant. The student
   plots ln(I_s / T^3) against 1/T and reads Eg from the slope. SIMULATED DATA. */
HoolaStudio.define('um8-junction-oven', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.um8_revsat, assign = HK.assign;
  var p = HK.paramsFor('um8_revsat', S.lab.params);
  var V_ = S.lab.variant || {};
  var DIODE = V_.sample || 'Germanium junction diode (OA79 type)';
  var KB = 8.617333262e-5;
  var st = { Tset: p.T0, Vr: 0, key: false, last: null };
  var ks = KN.init(p);

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function pp() { return assign(p, { Tset: st.Tset, Vr: st.key ? st.Vr : 0 }); }
  function readT() { return Math.round(ks.T * 10) / 10; }
  function readI() { var v = KN.view(ks, pp()).I_uA; return Math.round(v * 100) / 100; }
  function fmt(v, d) { return isFinite(v) ? v.toFixed(d) : '—'; }

  // ================================================================ hot plate, bath, diode, thermometer
  var plate = new T.Group(); S.scene.add(plate); plate.position.set(-0.25, 0, -0.1);
  var pb = S.rounded(0.2, 0.2, 0.05, 0.012, new T.MeshStandardMaterial({ color: 0xe6e3dc, roughness: 0.5 })); pb.rotation.x = -Math.PI / 2; pb.position.y = 0.025; plate.add(pb);
  var top = S.mesh(new T.CylinderGeometry(0.075, 0.075, 0.006, 40), new T.MeshStandardMaterial({ color: 0x3a3d42, roughness: 0.6, metalness: 0.4 })); top.position.y = 0.053; plate.add(top);
  var thKnob = new T.Group(); thKnob.position.set(-0.04, 0.025, 0.101); plate.add(thKnob);
  var tk = S.mesh(new T.CylinderGeometry(0.014, 0.015, 0.014, 28), M.bakelite); tk.rotation.x = Math.PI / 2; tk.position.z = 0.007; thKnob.add(tk);
  var tptr = S.mesh(new T.BoxGeometry(0.002, 0.012, 0.0012), M.white, false); tptr.position.set(0, 0.006, 0.0145); thKnob.add(tptr);
  var pl = S.label('THERMOSTAT 25–90 °C', { w: 0.08, ratio: 0.16, color: '#2b2f36' }); pl.position.set(0.035, 0.03, 0.1006); plate.add(pl);
  var lamp = S.mesh(new T.SphereGeometry(0.004, 12, 10), new T.MeshBasicMaterial({ color: 0x552222 })); lamp.position.set(0.06, 0.012, 0.1); plate.add(lamp);
  function knobAng(t) { return 2.2 - 4.4 * (t - 25) / 65; }
  thKnob.rotation.z = knobAng(st.Tset);
  var bath = S.beaker(0.06, 0.11, [-0.25, 0.056, -0.1], 0xe8c56a, 0.7);
  var tube = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.13, 20, 1, true), M.glass, false); tube.position.set(-0.235, 0.12, -0.1); S.scene.add(tube);
  var diode = new T.Group(); diode.position.set(-0.235, 0.085, -0.1); S.scene.add(diode);
  var dbody = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.012, 16), M.glass); diode.add(dbody);
  var band = S.mesh(new T.CylinderGeometry(0.0037, 0.0037, 0.002, 16), M.black); band.position.y = 0.005; diode.add(band);
  var lead1 = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 0.1, 6), M.copper); lead1.position.set(-0.002, 0.056, 0); diode.add(lead1);
  var lead2 = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 0.1, 6), M.copper); lead2.position.set(0.002, 0.056, 0); diode.add(lead2);
  var therm = S.thermometer({ len: 0.26, min: 0, max: 110, pos: [-0.27, 0.07, -0.1], value: ks.T });
  var stirrer = S.mesh(new T.CylinderGeometry(0.002, 0.002, 0.15, 8), M.chrome); stirrer.position.set(-0.27, 0.13, -0.075); stirrer.rotation.z = 0.15; S.scene.add(stirrer);
  S.contact(0.24, 0.24, -0.25, -0.1, 0.5);
  // the circuit: DC supply (reverse bias), plug key, digital microammeter
  var sup = S.powerBox([0.05, 0, 0.12], 'DC 0–3 V');
  var key = S.plugKey([0.2, 0, 0.14]);
  var mtr = new T.Group(); S.scene.add(mtr); mtr.position.set(0.2, 0, -0.12);
  var mb = S.rounded(0.16, 0.09, 0.1, 0.01, new T.MeshStandardMaterial({ color: 0xf0c419, roughness: 0.5 })); mb.position.y = 0.045; mtr.add(mb);
  var lcdTex = S.liveTex(512, 190);
  var lcd = new T.Mesh(new T.PlaneGeometry(0.11, 0.04), new T.MeshBasicMaterial({ map: lcdTex, toneMapped: false }));
  lcd.position.set(0, 0.058, 0.0505); mtr.add(lcd);
  var ml = S.label('DIGITAL MICROAMMETER  µA', { w: 0.12, ratio: 0.12, color: '#2b2f36' }); ml.position.set(0, 0.024, 0.0505); mtr.add(ml);
  S.contact(0.2, 0.14, 0.2, -0.12, 0.5);
  var lastLcd = '';
  function showLcd(txt) { if (txt === lastLcd) return; lastLcd = txt; lcdTex.draw(function (x) {
    x.fillStyle = '#a9b79a'; x.fillRect(0, 0, 512, 190); x.font = '700 92px "JetBrains Mono", monospace'; x.textAlign = 'right'; x.fillStyle = '#1b2116'; x.fillText(txt, 490, 132); }); }
  showLcd('0.00');
  S.wire([[-0.233, 0.19, -0.1], [-0.1, 0.12, -0.05], [0.13, 0.02, -0.12]], 'red');
  S.wire([[-0.237, 0.19, -0.1], [-0.12, 0.1, 0.05], [0.0, 0.1, 0.12]], 'black');
  S.wire([[0.1, 0.1, 0.12], [0.18, 0.03, 0.14]], 'red');
  S.wire([[0.22, 0.03, 0.14], [0.27, 0.02, -0.1]], 'black');

  S.addApparatus('bath', plate, 'Hot plate with thermostat and oil bath', 'The bath of transformer oil is stirred so the diode and the thermometer bulb share one temperature; the thermostat holds it at the set point.');
  S.addApparatus('diode', diode, DIODE, 'Held in a glass tube in the oil, connected the wrong way round on purpose: reverse biased, it passes only its saturation current.');
  S.addApparatus('therm', therm, 'Thermometer', 'Its bulb sits beside the diode. Read it to 0.1 °C.');
  S.addApparatus('sup', sup, 'DC supply', 'Sets the reverse bias across the diode.');
  S.addApparatus('key', key, 'Plug key', 'Closes the circuit.');
  S.addApparatus('mtr', mtr, 'Digital microammeter', 'Reads the reverse current to 0.01 µA.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var hudT = S.hudCard('Bath'), hudI = S.hudCard('Reverse current');

  // ================================================================ actions
  function closeKey() {
    if (busy() || st.key) return Promise.resolve();
    return S.hand.tap(key.userData.plug, 'top').then(function () { key.set(true); st.key = true; S.say('Plug key in: the diode is in the circuit.'); S.render(); });
  }
  function setBias(v) {
    if (busy()) return Promise.resolve();
    if (!isFinite(v) || v < 0.2 || v > 3) { S.say('Keep the reverse bias between 0.2 and 3 V: a germanium diode breaks down not far above that.'); return Promise.resolve(); }
    var kn = sup.userData.knob, pt = kn.getWorldPosition(new T.Vector3()), v0 = st.Vr;
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { st.Vr = v0 + (v - v0) * k; kn.rotation.y = st.Vr; }, { mode: 'front', ms: 600, reachMs: 500 })
      .then(function () { st.Vr = Math.round(v * 10) / 10; S.say('Reverse bias ' + st.Vr.toFixed(1) + ' V.'); S.render(); });
  }
  function setTemp(t) {
    if (busy()) return Promise.resolve(false);
    if (!isFinite(t) || t < 25 || t > 85) { S.say('Set the bath between 25 and 85 °C: never above 90 °C with this oil.'); return Promise.resolve(false); }
    var pt = thKnob.getWorldPosition(new T.Vector3()), t0 = st.Tset;
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { st.Tset = t0 + (t - t0) * k; thKnob.rotation.z = knobAng(st.Tset); }, { mode: 'front', ms: 700, reachMs: 500 })
      .then(function () { st.Tset = Math.round(t); thKnob.rotation.z = knobAng(st.Tset); S.say('Thermostat set to ' + st.Tset + ' °C. Stir and wait for the bath to settle.'); S.render(); return true; });
  }
  function settle() {
    if (busy()) return Promise.resolve(false);
    var total = 8 * p.tau, done = 0;
    return S.tween(1500, function (k) { var want = total * k; if (want > done) { KN.step(ks, pp(), want - done); done = want; } })
      .then(function () { if (total > done) KN.step(ks, pp(), total - done); S.say('The bath has settled at ' + readT().toFixed(1) + ' °C.'); S.render(); return true; });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.key || st.Vr < 0.2) { S.say('Close the circuit with the reverse bias set first.'); return false; }
    if (Math.abs(ks.T - st.Tset) > 0.15) { S.say('The bath is still changing: wait for it to settle before you read.'); return false; }
    var t = readT();
    if (S.rows.some(function (r) { return Math.abs(r.T - t) < 2; })) { S.say('You already have a reading near ' + t.toFixed(1) + ' °C. Change the set point.'); return false; }
    var i = readI(), TK = t + 273.15;
    var row = { T: t, I: i, invT: 1000 / TK, y: Math.log(i * 1e-6 / (TK * TK * TK)) };
    S.addRow(row); st.last = row;
    S.say('Written: ' + t.toFixed(1) + ' °C, ' + i.toFixed(2) + ' µA.');
    return true;
  }
  function result(rows) {
    if (rows.length < 5) return null;
    var f = S.fit.linear(rows.map(function (r) { return [1 / (r.T + 273.15), r.y]; }));
    if (!f || f.m >= 0) return null;
    var eg = -f.m * KB;
    var g = S.fit.linear(rows.map(function (r) { return [1 / (r.T + 273.15), Math.log(r.I)]; }));
    return { label: 'Band gap of germanium', value: eg, unit: 'eV', digits: 3, truth: p.Eg,
      note: 'From the slope of ln(I_s/T³) against 1/T. Without the T³ term (ln I_s alone) the slope would give ' + (g ? fmt(-g.m * KB, 3) : '—') + ' eV, a little too high. SIMULATED DATA.' };
  }

  return {
    camera: { pos: [0.0, 0.6, 0.85], look: [0.0, 0.08, -0.08] },
    views: { bath: [[-0.12, 0.34, 0.32], [-0.25, 0.1, -0.1]], diode: [[-0.15, 0.25, 0.12], [-0.235, 0.13, -0.1]], therm: [[-0.2, 0.3, 0.2], [-0.27, 0.18, -0.1]],
      sup: [[0.1, 0.3, 0.4], [0.05, 0.05, 0.12]], key: [[0.22, 0.22, 0.36], [0.2, 0.02, 0.14]], mtr: [[0.22, 0.3, 0.15], [0.2, 0.05, -0.12]],
      bench: [[0.0, 0.6, 0.85], [0.0, 0.08, -0.08]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'In reverse bias a p-n junction passes only the saturation current carried by minority carriers, which are made by thermal excitation across the band gap. Their number grows as T³ exp(−Eg/kT), so the reverse current climbs steeply with temperature.',
      formula: 'I_s = C T³ exp(−Eg / kT)   ⇒   ln(I_s / T³) = ln C − (Eg / k)(1/T)',
      formulaNote: 'the slope of ln(I_s/T³) against 1/T is −Eg/k;  k = 8.617 × 10⁻⁵ eV/K',
      more: ['A few tenths of a volt of reverse bias already saturates the current; more only adds leakage in a real diode.',
        'Eg is taken as constant here; in germanium it falls by about 0.4 meV per kelvin, a small effect over 30–80 °C.',
        'A silicon diode is not used: its reverse current at these temperatures comes from generation in the depletion layer and grows as exp(−Eg/2kT).'],
      precautions: 'Let the bath settle before each reading, keep the diode and the thermometer bulb side by side, and never heat the oil above 90 °C.' },
    book: { title: 'Expt. — Band gap from the reverse saturation current',
      lines: ['Diode: ' + DIODE, 'Reverse bias about 1 V.', 'I_s = C T³ exp(−Eg/kT)', 'Plot ln(I_s/T³) against 1/T.'],
      columns: [{ label: 'T (°C)', get: function (r) { return r.T.toFixed(1); } }, { label: 'I_s (µA)', get: function (r) { return r.I.toFixed(2); } },
        { label: '1000/T (1/K)', get: function (r) { return r.invT.toFixed(4); } }, { label: 'ln(I_s/T³)', get: function (r) { return r.y.toFixed(3); } }] },
    graph: { x: function (r) { return r.invT; }, y: function (r) { return r.y; }, xlabel: '1000/T (1/K)', ylabel: 'ln (I_s / T³)',
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.02,
    resultNote: 'A steep straight line: the reverse current is a thermometer of the band gap. Germanium\'s 0.66 eV is why its diodes leak far more than silicon\'s.',
    chips: ['Why reverse bias?', 'Why divide by T³?', 'Why not a silicon diode?', 'Check my readings'],
    viva: [['The slope of ln(I_s/T³) against 1/T is', ['−Eg/k', '−kT', '+Eg/k'], 0, 'I_s = C T³ e^(−Eg/kT).'],
      ['The reverse current rises with temperature because', ['More electron-hole pairs are made across the gap', 'The bias rises', 'The diode shrinks'], 0, 'Thermal generation across Eg.']],
    askState: function () {
      return { experiment: 'band gap of germanium from the reverse saturation current', diode: DIODE, circuit_closed: st.key, reverse_bias_V: st.Vr,
        set_point_C: st.Tset, bath_C: readT(), reverse_current_uA: readI(), readings: S.rows.length };
    },
    steps: [
      { id: 'circuit', title: 'Circuit', view: 'sup', render: function (u) {
          u.h2('Reverse-bias the diode');
          u.p('The diode is connected with its cathode band to the + of the supply. Set about 1 V and put the plug key in.');
          u.task('Reverse bias', st.Vr >= 0.2, fmt(st.Vr, 1) + ' V').add(u.button('Set 1.0 V', function () { S.focus('sup'); setBias(1.0); }, false, S.hand.busy));
          u.task('Plug key', st.key, st.key ? 'In' : 'Out').add(u.button('Put the key in', function () { S.focus('key'); closeKey(); }, true, st.key || S.hand.busy));
          u.live(function () { return 'Microammeter: ' + readI().toFixed(2) + ' µA at ' + readT().toFixed(1) + ' °C'; });
          u.next('Next: heat and read', st.key && st.Vr >= 0.2);
        },
        ok: function () { return st.key && st.Vr >= 0.2; },
        auto: function () { return setBias(1.0).then(function () { return closeKey(); }); } },
      { id: 'heat', title: 'Heat and read', view: 'bath', render: function (u) {
          u.h2('Raise the bath in steps and read I_s');
          u.p('Set the thermostat, stir, wait for the bath to settle, then read the temperature and the reverse current. Take at least five readings from about 30 °C to 80 °C.');
          var sel = { t: Math.max(30, st.Tset + 10 > 85 ? 30 : st.Tset + 10) };
          u.slider('Set point', 25, 85, 1, function () { return sel.t; }, function (v) { sel.t = Math.round(v); }, '°C', 0);
          u.row(u.button('Turn the thermostat', function () { S.focus('bath'); setTemp(sel.t); }, true, S.hand.busy),
            u.button('Stir and wait', function () { settle(); }, false, S.hand.busy),
            u.button('Record T and I', function () { record(); }, false, S.hand.busy));
          u.live(function () { return 'Bath ' + readT().toFixed(1) + ' °C (set ' + st.Tset + ')  ·  ' + readI().toFixed(2) + ' µA'; });
          u.table();
          u.next('Next: the result', S.rows.length >= 5);
        },
        ok: function () { return S.rows.length >= 5; },
        auto: function () {
          return [30, 40, 50, 60, 70, 80].reduce(function (pr, t) {
            return pr.then(function () { return setTemp(t); }).then(function () { return settle(); }).then(function () { record(); });
          }, Promise.resolve());
        } },
    ],
    tick: function (dt) {
      KN.step(ks, pp(), dt);
      therm.set(ks.T);
      lamp.material.color.setHex(st.Tset > ks.T + 0.2 ? 0xff3b30 : 0x552222);
      bath.setLevel(0.7);
      showLcd(st.key ? readI().toFixed(2) : '0.00');
      hudT.set(readT().toFixed(1) + ' °C');
      hudI.set((st.key ? readI().toFixed(2) : '0.00') + ' µA');
    },
  };
});
