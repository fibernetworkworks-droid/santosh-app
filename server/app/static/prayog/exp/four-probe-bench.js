/* Prayogshala studio module: FOUR-PROBE BENCH (B.Sc. solid state physics).
   A small oven with the four-probe head inside it, a germanium slice on the probe stage, a constant-current
   source, a four-and-a-half digit millivoltmeter and a thermocouple readout.
   Physics: the `fourprobe` kernel of packs/modern_ug.js on the lab's own params - the same code the server checks
   against rho = rho300 exp((Eg e / 2k)(1/T - 1/300)). The student gets the resistivity from the probe voltage
   through the thin-slice formula and the band gap from the slope of ln rho against 1/T. */
HoolaStudio.define('four-probe-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.fourprobe, assign = HK.assign;
  var p = HK.paramsFor('fourprobe', S.lab.params);
  var QEL = 1.602176634e-19, KBL = 1.380649e-23, LN2 = Math.log(2);
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || 'Germanium slice, 0.5 mm thick';
  var TMIN = 300, TMAX = 450, VLC = 0.01;                 // oven range (K) and millivoltmeter least count (mV)
  var st = { probed: false, current: false, T: 300, setT: 300, heating: false, done: {} };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function qAt(t) { return assign(p, { T: t }); }
  function probeV() { return st.current ? KN.probeV(qAt(st.T)) : 0; }
  function readMv() { return rnd(probeV() * 1000, 2); }                 // millivolts, least count 0.01 mV
  function rhoFrom(mv) { return Math.PI * p.w * (mv / 1000) / (LN2 * p.I); }

  // ================================================================ the oven
  var ovenG = new T.Group(); S.scene.add(ovenG); ovenG.position.set(-0.32, 0, -0.12);
  var shellM = new T.MeshStandardMaterial({ color: 0x5a6069, roughness: 0.55, metalness: 0.45 });
  var OW = 0.22, OD = 0.2, OH = 0.17;
  /* Panels with a real opening in the front, so the slice and the probes can be seen through the window. */
  var WW = 0.1, WH = 0.07, WY = 0.09, TH = 0.007;
  var shell = new T.Group(); ovenG.add(shell);
  function panel(w, h, d, x, y, z) { var m = S.mesh(new T.BoxGeometry(w, h, d), shellM);
    m.position.set(x, y, z); shell.add(m); return m; }
  panel(OW, TH, OD, 0, TH / 2 + 0.006, 0);
  panel(OW, OH, TH, 0, OH / 2 + 0.006, -OD / 2 + TH / 2);
  panel(TH, OH, OD, -OW / 2 + TH / 2, OH / 2 + 0.006, 0);
  panel(TH, OH, OD, OW / 2 - TH / 2, OH / 2 + 0.006, 0);
  panel(OW, TH, OD, 0, OH + 0.006 - TH / 2, 0);
  var FZP = OD / 2 - TH / 2;
  panel((OW - WW) / 2, OH, TH, -(WW + (OW - WW) / 2) / 2, OH / 2 + 0.006, FZP);
  panel((OW - WW) / 2, OH, TH, (WW + (OW - WW) / 2) / 2, OH / 2 + 0.006, FZP);
  panel(WW, OH - (WY + WH / 2), TH, 0, (WY + WH / 2 + OH) / 2 + 0.006, FZP);
  panel(WW, WY - WH / 2, TH, 0, (WY - WH / 2) / 2 + 0.006, FZP);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.006, 16), M.rubber);
    ft.position.set(f[0] * (OW / 2 - 0.02), 0.003, f[1] * (OD / 2 - 0.02)); ovenG.add(ft);
  });
  var winM = new T.MeshStandardMaterial({ color: 0xdfe6ea, roughness: 0.08, transparent: true, opacity: 0.16 });
  var window2 = S.mesh(new T.BoxGeometry(WW, WH, 0.0025), winM, false, false);
  window2.position.set(0, WY + 0.006, OD / 2 - TH / 2); ovenG.add(window2);
  var wFrame = S.mesh(new T.TorusGeometry(0.063, 0.0032, 8, 4), M.iron);
  wFrame.position.set(0, WY + 0.006, OD / 2 + 0.001); wFrame.rotation.z = Math.PI / 4; ovenG.add(wFrame);
  var glowM = new T.MeshBasicMaterial({ color: 0xff5a1e, transparent: true, opacity: 0, depthWrite: false,
    blending: T.AdditiveBlending });
  var coil = S.mesh(new T.TorusGeometry(0.06, 0.004, 8, 32), glowM, false, false);
  coil.rotation.x = Math.PI / 2; coil.position.set(0, 0.06, 0); ovenG.add(coil);
  // the stage, the slice and the four probes
  var stage = S.mesh(new T.CylinderGeometry(0.04, 0.045, 0.012, 28), M.iron); stage.position.set(0, 0.075, 0);
  ovenG.add(stage);
  var sliceM = new T.MeshStandardMaterial({ color: 0x6e747c, roughness: 0.25, metalness: 0.85 });
  var slice = S.mesh(new T.BoxGeometry(0.035, 0.0015, 0.035), sliceM); slice.position.set(0, 0.082, 0);
  ovenG.add(slice);
  var probeHead = new T.Group(); ovenG.add(probeHead); probeHead.position.set(0, 0.13, 0);
  var headBlock = S.rounded(0.05, 0.03, 0.016, 0.004, M.bakelite); headBlock.rotation.x = -Math.PI / 2;
  headBlock.position.y = 0.03; probeHead.add(headBlock);
  var probes = [];
  for (var pi = 0; pi < 4; pi++) {
    var gx = (pi - 1.5) * (p.s * 1000 / 1000);
    var spr = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, 0.04, 10), M.chrome);
    spr.position.set(gx, 0.008, 0); probeHead.add(spr);
    var tipP = S.mesh(new T.ConeGeometry(0.0012, 0.004, 10), M.chrome); tipP.rotation.x = Math.PI;
    tipP.position.set(gx, -0.014, 0); probeHead.add(tipP);
    probes.push(spr);
  }
  var post = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.12, 16), M.chrome); post.position.set(0.07, 0.11, 0);
  ovenG.add(post);
  var tcM = S.mesh(new T.CylinderGeometry(0.0015, 0.0015, 0.08, 10), M.copper); tcM.position.set(0.03, 0.1, 0.02);
  ovenG.add(tcM);
  var insideL = new T.PointLight(0xfff0d8, 0.5, 0.5); insideL.position.set(0, 0.1, 0.06); ovenG.add(insideL);
  var ovenLbl = S.label('FOUR-PROBE OVEN  ·  ' + TMIN + '–' + TMAX + ' K', { w: 0.14, ratio: 0.14, color: '#e8eaec' });
  ovenLbl.position.set(0, 0.03, OD / 2 + 0.007); ovenGLbl();
  function ovenGLbl() { ovenG.add(ovenLbl); }
  S.contact(0.3, 0.28, -0.32, -0.12, 0.55);

  // ================================================================ the three instruments
  function instBox(x, z, rotY, title, sub, wdt) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = rotY;
    var W = wdt || 0.2, D = 0.15, Hh = 0.08;
    var cse = S.rounded(W, D, Hh, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 }));
    cse.rotation.x = -Math.PI / 2; cse.position.y = Hh / 2 + 0.003; g.add(cse);
    var FZ = D / 2 + 0.005, PW = W - 0.012, PH = Hh - 0.012;
    var tex = S.canvasTex(900, Math.round(900 * PH / PW), function (xx, w, h) {
      xx.fillStyle = '#2b323d'; xx.fillRect(0, 0, w, h);
      xx.strokeStyle = 'rgba(255,255,255,.12)'; xx.lineWidth = 3; xx.strokeRect(8, 8, w - 16, h - 16);
      xx.fillStyle = '#f1efe8'; xx.font = '700 34px "Public Sans", sans-serif'; xx.fillText(title, 26, 52);
      xx.font = '500 24px "Public Sans", sans-serif'; xx.fillStyle = '#c7ccd6'; xx.fillText(sub, 26, 88);
    });
    var fac = S.mesh(new T.BoxGeometry(PW, PH, 0.004),
      [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]);
    fac.position.set(0, 0.003 + Hh / 2, FZ - 0.002); g.add(fac);
    var lcdT = S.liveTex(512, 180), last = '';
    var bez = S.mesh(new T.BoxGeometry(PW * 0.52, PH * 0.42, 0.003), M.grey);
    bez.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.001); g.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(PW * 0.48, PH * 0.38), new T.MeshBasicMaterial({ map: lcdT, toneMapped: false }));
    scr.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(scr);
    var knobG = new T.Group(); knobG.position.set(-PW * 0.28, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(knobG);
    knobG.add(S.mesh(new T.CylinderGeometry(0.012, 0.013, 0.012, 28), M.bakelite));
    knobG.children[0].rotation.x = Math.PI / 2;
    var kp = S.mesh(new T.BoxGeometry(0.0018, 0.012, 0.001), M.white, false); kp.position.set(0, 0.007, 0.007);
    knobG.add(kp);
    S.contact(W + 0.06, D + 0.06, x, z, 0.5);
    return { group: g, knob: knobG,
      show: function (txt, u2) {
        if (txt + u2 === last) return; last = txt + u2;
        lcdT.draw(function (xx) {
          var gr = xx.createLinearGradient(0, 0, 0, 180); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
          xx.fillStyle = gr; xx.fillRect(0, 0, 512, 180);
          xx.font = '700 92px "JetBrains Mono", monospace'; xx.textAlign = 'right';
          xx.fillStyle = 'rgba(0,0,0,.07)'; xx.fillText('88888', 400, 118);
          xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 118);
          xx.font = '600 34px "Public Sans", sans-serif'; xx.fillText(u2, 496, 150);
        });
      } };
  }
  var csrc = instBox(0.0, 0.1, -0.1, 'CONSTANT CURRENT SOURCE', '0 – 10 mA  ·  holds the probe current steady', 0.22);
  var dvm = instBox(0.28, -0.06, -0.35, 'DIGITAL MILLIVOLTMETER', '4½ digit  ·  across the inner probes', 0.22);
  var ovc = instBox(-0.08, -0.26, 0.12, 'OVEN CONTROLLER', 'sets and holds the stage temperature', 0.2);
  csrc.show('0.00', 'mA'); dvm.show('0.00', 'mV'); ovc.show('300', 'K');   // the displays read before the first tick

  S.wire([[-0.3, 0.14, -0.04], [-0.14, 0.03, 0.04], [-0.04, 0.03, 0.06]], 'red');
  S.wire([[-0.26, 0.14, -0.04], [-0.1, 0.028, 0.08], [0.04, 0.03, 0.06]], 'black');
  S.wire([[-0.3, 0.14, -0.02], [-0.06, 0.026, -0.02], [0.22, 0.03, -0.1]], 'gold');
  S.wire([[-0.28, 0.14, -0.02], [-0.04, 0.024, -0.05], [0.32, 0.03, -0.1]], 'blue');
  S.wire([[-0.3, 0.05, -0.06], [-0.2, 0.012, -0.2], [-0.12, 0.03, -0.26]], 'black');

  S.addApparatus('oven', ovenG, 'Four-probe oven', 'A small furnace holding the probe stage. The slice is heated slowly and held at each temperature until the thermocouple settles.');
  S.addApparatus('probes', probeHead, 'Four-probe head', 'Four spring-loaded probes ' + (p.s * 1000).toFixed(1) + ' mm apart in a line. The current goes through the outer pair; the voltage is read between the inner two, which carry almost no current.');
  S.addApparatus('slice', slice, SAMPLE, 'A thin slice on the stage. Because it is much thinner than the probe spacing, the geometry correction is (2s/w)ln2.');
  S.addApparatus('csrc', csrc.group, 'Constant-current source', 'Holds the probe current at ' + (p.I * 1000).toFixed(1) + ' mA however the sample\'s resistance changes.');
  S.addApparatus('dvm', dvm.group, 'Digital millivoltmeter', 'Reads the voltage between the inner probes, to 0.01 mV.');
  S.addApparatus('ovc', ovc.group, 'Oven controller', 'Sets the temperature and holds it there; the thermocouple reads the stage itself.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudT = S.hudCard('Temperature'), hudV = S.hudCard('Probe voltage'), hudR = S.hudCard('Resistivity');

  // ================================================================ human actions
  function setProbes() {
    if (busy()) return Promise.resolve();
    if (st.probed) return Promise.resolve();
    var pt = wpt(probeHead, 0, 0.04, 0.02);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) {
      probeHead.position.y = 0.13 - 0.018 * k;
    }, { mode: 'top', ms: 800, reachMs: 650 }).then(function () {
      probeHead.position.y = 0.112; st.probed = true;
      S.say('The four probes are down on the slice, just touching. They are spring-loaded: pressing harder would crack the germanium and change nothing in the reading.');
      S.render();
    });
  }
  function setCurrent(on) {
    if (busy()) return Promise.resolve();
    if (on === st.current) return Promise.resolve();
    if (on && !st.probed) { S.say('Put the probes down on the slice first.'); return Promise.resolve(); }
    return S.hand.tap(csrc.knob, 'front').then(function () {
      st.current = on;
      S.say(on ? 'Probe current set to ' + (p.I * 1000).toFixed(1) + ' mA and held there.' : 'Current off.');
      S.click(880, 0.05); S.render();
    });
  }
  function heatTo(tK) {
    if (busy()) return Promise.resolve();
    if (!(tK >= TMIN && tK <= TMAX)) { S.say('The oven works between ' + TMIN + ' K and ' + TMAX + ' K.'); return Promise.resolve(); }
    var t0 = st.T;
    st.heating = true;
    return S.hand.tap(ovc.knob, 'front').then(function () {
      st.setT = tK;
      return S.tween(900 + 6 * Math.abs(tK - t0), function (k) { st.T = t0 + (tK - t0) * k; });
    }).then(function () {
      st.T = tK; st.heating = false;
      S.say('The stage has settled at ' + tK + ' K. The thermocouple is steady, so the reading can be taken.');
      S.render();
    });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.current) { S.say('Switch the constant-current source on first.'); return false; }
    if (st.heating) { S.say('Wait for the temperature to settle before reading.'); return false; }
    var tk = Math.round(st.T);
    if (st.done[tk]) { S.say('You already have a reading at ' + tk + ' K. Raise the oven further.'); return false; }
    var mv = readMv();
    if (mv < VLC) { S.say('The probe voltage has fallen below the meter\'s least count. The sample is too hot for this current; the run ends here.'); return false; }
    st.done[tk] = true;
    S.addRow({ T: tk, mv: mv, rho: rhoFrom(mv) });
    S.say('Written in your record book: ' + tk + ' K, ' + mv.toFixed(2) + ' mV, resistivity ' + (rhoFrom(mv) * 100).toFixed(3) + ' Ω·cm.');
    return true;
  }

  function result(rows) {
    var pts = rows.filter(function (r) { return r.rho > 0; })
      .map(function (r) { return [1 / r.T, Math.log(r.rho)]; });
    if (pts.length < 5) return null;
    var f = S.fit.linear(pts);
    if (!f || f.m <= 0) return null;
    return { label: 'Band gap of the sample', value: 2 * KBL * f.m / QEL, unit: 'eV', digits: 3, truth: p.Eg,
      note: 'Slope of ln ρ against 1/T is ' + f.m.toFixed(0) + ' K = Eg e / 2k, so the band gap is twice k times the slope, divided by e. Taken from ' + pts.length + ' temperatures.' };
  }

  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { oven: [[-0.3, 0.26, 0.3], [-0.32, 0.1, -0.12]], probes: [[-0.3, 0.2, 0.14], [-0.32, 0.1, -0.12]],
      slice: [[-0.3, 0.16, 0.1], [-0.32, 0.085, -0.12]], csrc: [[0.0, 0.26, 0.32], [0.0, 0.05, 0.1]],
      dvm: [[0.3, 0.24, 0.16], [0.28, 0.05, -0.06]], ovc: [[-0.08, 0.24, -0.04], [-0.08, 0.05, -0.26]],
      bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'In an intrinsic semiconductor the number of free carriers goes as exp(−Eg/2kT), so heating the sample frees many more of them and the resistivity falls steeply. The four-probe method measures that resistivity without the contact resistance getting in the way: the current goes through the outer probes while the voltage is read between the inner two, which carry almost no current.',
      formula: 'ρ = π w V / (ln2 · I),   ln ρ = const + (Eg e / 2k)(1/T)',
      formulaNote: 'the thin-slice form of the four-probe correction G₇(w/s) = (2s/w) ln2',
      more: ['The probe current is kept small so that the sample does not heat itself, and the same current is used at every temperature.',
        'Readings are taken on the way up AND held until the thermocouple is steady: the slice must be at the temperature the thermometer claims.',
        'The slope of ln ρ against 1/T is Eg e/2k. The factor of two is there because both electrons and holes are made in pairs, so the carrier number carries half the gap in its exponent.'],
      precautions: 'Do not press the probes down hard: germanium is brittle. Keep the current the same throughout. The oven and the head stay hot long after the heater is off.' },
    book: { title: 'Expt. — Four-probe resistivity and band gap',
      lines: ['Aim: resistivity against temperature; band gap.', 'Sample: ' + SAMPLE,
        'Probe spacing ' + (p.s * 1000).toFixed(1) + ' mm, thickness ' + (p.w * 1000).toFixed(2) + ' mm.',
        'Probe current ' + (p.I * 1000).toFixed(1) + ' mA, held constant.',
        'ρ = π w V / (ln2 I);  slope of ln ρ vs 1/T = Eg e/2k.'],
      columns: [{ label: 'T (K)', get: function (r) { return r.T; } },
        { label: '1/T (10⁻³/K)', get: function (r) { return (1000 / r.T).toFixed(3); } },
        { label: 'V (mV)', get: function (r) { return r.mv.toFixed(2); } },
        { label: 'ρ (Ω·cm)', get: function (r) { return (r.rho * 100).toFixed(3); } }] },
    graph: { x: function (r) { return 1000 / r.T; }, y: function (r) { return Math.log(r.rho); },
      xlabel: '1/T (10⁻³ /K)', ylabel: 'ln ρ (ρ in Ω·m)',
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.03,
    resultNote: 'A straight line of ln ρ against 1/T is the signature of intrinsic conduction, and its slope measures the energy an electron needs to cross the forbidden gap - a number you have taken from a voltmeter and a thermometer alone.',
    chips: ['Why four probes and not two?', 'Why does the factor 2 appear in Eg/2kT?',
      'Why keep the current small?', 'Check my readings', 'What would a doped sample look like?'],
    viva: [['The four-probe method avoids', ['Contact resistance', 'The need for a current', 'Heating altogether'], 0,
      'The voltage probes carry almost no current, so their contact resistance drops no voltage.'],
      ['As an intrinsic semiconductor is heated its resistivity', ['Falls steeply', 'Rises steeply', 'Stays put'], 0,
        'The carrier number goes as exp(−Eg/2kT).'],
      ['The slope of ln ρ against 1/T equals', ['Eg e / 2k', 'Eg e / k', 'k / Eg'], 0,
        'Hence Eg = 2k × slope ÷ e.']],
    askState: function () {
      return { experiment: 'four-probe resistivity against temperature, and the band gap',
        sample: SAMPLE, probes_down: st.probed, current_on: st.current, probe_current_mA: p.I * 1000,
        temperature_K: Math.round(st.T), probe_voltage_mV: readMv(),
        resistivity_ohm_cm: +(rhoFrom(readMv()) * 100).toFixed(4), readings_taken: S.rows.length };
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'oven', render: function (u) {
          u.h2('Probes down, current on');
          u.p('The slice sits on the stage inside the oven. Lower the four-probe head until the probes just touch it, then switch the constant-current source on and leave it at ' + (p.I * 1000).toFixed(1) + ' mA for the whole run.');
          u.task('1. Lower the probes', st.probed, st.probed ? 'All four probes touching' : 'Spring-loaded: just touching is enough')
            .add(u.button(st.probed ? 'Probes are down' : 'Lower the probe head', function () { S.focus('probes'); setProbes(); }, !st.probed, st.probed || S.hand.busy));
          u.task('2. Switch the current on', st.current, st.current ? (p.I * 1000).toFixed(1) + ' mA through the outer probes' : 'Current source off')
            .add(u.button(st.current ? 'Current is on' : 'Switch the current on', function () { S.focus('csrc'); setCurrent(true); }, !st.current, st.current || S.hand.busy));
          u.live(function () { return st.current ? 'Probe voltage ' + readMv().toFixed(2) + ' mV at ' + Math.round(st.T) + ' K' : 'No current yet'; });
          u.note('Germanium is brittle. The probes are sprung for a reason: never press the head down.');
          u.next('Next: heat and read', st.probed && st.current);
        },
        ok: function () { return st.probed && st.current; },
        auto: function () { return setProbes().then(function () { return setCurrent(true); }); } },

      { id: 'heat', title: 'Heat and read', view: 'dvm', render: function (u) {
          u.h2('Read the probe voltage at each temperature');
          u.p('Raise the oven in steps of about 15 K. At each step wait for the thermocouple to settle, then read the millivoltmeter and record it. The resistivity follows from ρ = π w V / (ln2 · I).');
          var tg = { v: Math.min(TMAX, Math.round(st.T / 5) * 5 + 15) };
          u.slider('Set the oven to', TMIN, TMAX, 5, function () { return tg.v; }, function (v) { tg.v = v; }, 'K', 0);
          u.row(u.button('Heat and settle', function () { S.focus('ovc'); heatTo(tg.v); }, true, S.hand.busy),
            u.button('Record T and V', function () { record(); }, false, S.hand.busy));
          u.live(function () { return Math.round(st.T) + ' K  ·  ' + readMv().toFixed(2) + ' mV  ·  ρ = '
            + (rhoFrom(readMv()) * 100).toFixed(3) + ' Ω·cm'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 5) u.p(S.rows.length + ' of at least 5 temperatures recorded (eight is better).');
          u.next('Next: the band gap', S.rows.length >= 5);
        },
        ok: function () { return S.rows.length >= 5; },
        auto: function () {
          var ts = [300, 315, 330, 345, 360, 375, 390, 405];
          return ts.reduce(function (pr, tk) {
            return pr.then(function () { return heatTo(tk); }).then(function () { record(); });
          }, Promise.resolve());
        } },
    ],

    tick: function () {
      csrc.show(st.current ? (p.I * 1000).toFixed(2) : '0.00', 'mA');
      dvm.show(st.current ? readMv().toFixed(2) : '0.00', 'mV');
      ovc.show(Math.round(st.T) + '', 'K');
      glowM.opacity = Math.max(0, Math.min(0.5, (st.T - 300) / 150 * 0.5));
      sliceM.emissive = new T.Color(0xff3a10);
      sliceM.emissiveIntensity = Math.max(0, Math.min(0.5, (st.T - 330) / 120));
      hudT.set(Math.round(st.T) + ' K');
      hudV.set(st.current ? readMv().toFixed(2) + ' mV' : '—');
      hudR.set(st.current ? (rhoFrom(readMv()) * 100).toFixed(3) + ' Ω·cm' : '—');
    },
  };
});
