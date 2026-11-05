/* Prayogshala studio rig `digital-trainer`: ONE digital electronics trainer - a 5 V regulated rail, slide switches
   for the inputs, light-emitting diodes on the outputs, a logic probe and a breadboard carrying 7400 quad 2-input
   NAND packages - serving every undergraduate digital set-up in app/prayog/labs/elec_ug.py. The wiring on the
   breadboard changes with the lab; the trainer and the procedure do not.
   Physics: the lab's own kernel (logic_gate / logic_arith from packs/elec_ug.js) evaluates the real NAND network
   node by node, never a stored truth table. */
HoolaStudio.define('digital-trainer', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KK = HK.K[S.lab.kernel], p = HK.paramsFor(S.lab.kernel, S.lab.params);
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var GATES = S.lab.kernel === 'logic_gate';
  var FN = Math.round(p.fn);

  function fmt(v, d) { return (isFinite(v) ? v : 0).toFixed(d); }
  function bit(v) { return v >= 0.5 ? 1 : 0; }
  function readAt(over) { var q = assign(p, over || {}); return KK.view(KK.init(q, null), q, null); }

  // =============================================================================================== the lab's plan
  var GATE_NAMES = { 1: 'NOT', 2: 'AND', 3: 'OR', 4: 'XOR', 5: 'NAND', 6: 'NOR', 7: 'XNOR' };
  var GATE_EXPR = { 1: "Y = A'", 2: 'Y = A·B', 3: 'Y = A + B', 4: "Y = A·B' + A'·B", 5: "Y = (A·B)'",
    6: "Y = (A + B)'", 7: "Y = A·B + A'·B'" };
  var GATE_BUILD = {
    1: 'One NAND with both inputs joined: A NAND A = A\'.',
    2: 'A NAND gate followed by an inverting NAND: Y = (A NAND B) NAND (A NAND B).',
    3: 'Invert each input with its own NAND, then NAND the two: Y = A\' NAND B\'.',
    4: 'Four NAND gates: n1 = A NAND B, n2 = A NAND n1, n3 = B NAND n1, Y = n2 NAND n3.',
    5: 'One NAND gate, straight from the package.',
    6: 'The OR network of three NAND gates, with a fourth NAND as an inverter on the output.',
    7: 'The XOR network of four NAND gates, with a fifth NAND inverting the output.',
  };
  var ARITH = {
    1: { name: 'half adder', ins: ['A', 'B'], outs: [['S', 'S'], ['Cout', 'C']], chips: 2,
      build: 'An exclusive-OR of four NAND gates gives the sum; two more NAND gates give the carry as A·B.' },
    2: { name: 'full adder', ins: ['A', 'B', 'Cin'], outs: [['S', 'S'], ['Cout', 'C']], chips: 3,
      build: 'Two half adders in cascade, their carries combined by an OR built from NAND gates.' },
    3: { name: 'half subtractor', ins: ['A', 'B'], outs: [['D', 'D'], ['Bout', 'B_out']], chips: 2,
      build: 'The same exclusive-OR gives the difference; the borrow is A\' · B, two NAND gates.' },
    4: { name: 'full subtractor', ins: ['A', 'B', 'Cin'], outs: [['D', 'D'], ['Bout', 'B_out']], chips: 3,
      build: 'D = A xor B xor B_in, and the borrow out combines A\'·B with B_in·(A xor B)\'.' },
    5: { name: '4-bit ripple-carry adder', ins: ['An', 'Bn', 'Cin'], outs: [['SUM', 'Σ'], ['Cout', 'C₄']], chips: 3,
      build: 'Four full adders in a chain, each carry out feeding the next carry in.' },
  };

  var COMBOS, INS, OUTS, NCHIPS, BUILD, NAME;
  if (GATES) {
    COMBOS = [{ A: 0, B: 0 }, { A: 0, B: 1 }, { A: 1, B: 0 }, { A: 1, B: 1 }];
    INS = ['A', 'B'];
    OUTS = [['Y', 'Y'], ['n1', 'n1']];
    NCHIPS = FN >= 6 ? 2 : 1;
    BUILD = GATE_BUILD[FN] || GATE_BUILD[4];
    NAME = (GATE_NAMES[FN] || 'XOR') + ' gate from NAND gates';
  } else {
    var A = ARITH[FN] || ARITH[1];
    NAME = A.name + ' from NAND gates';
    INS = A.ins; OUTS = A.outs; NCHIPS = A.chips; BUILD = A.build;
    if (FN === 5) {
      COMBOS = [{ An: 0, Bn: 0, Cin: 0 }, { An: 1, Bn: 1, Cin: 0 }, { An: 3, Bn: 5, Cin: 0 },
        { An: 7, Bn: 8, Cin: 0 }, { An: 6, Bn: 9, Cin: 0 }, { An: 9, Bn: 5, Cin: 1 },
        { An: 13, Bn: 11, Cin: 1 }, { An: 15, Bn: 15, Cin: 1 }];
    } else if (A.ins.length === 3) {
      COMBOS = [];
      for (var a3 = 0; a3 < 2; a3++) for (var b3 = 0; b3 < 2; b3++) for (var c3 = 0; c3 < 2; c3++) COMBOS.push({ A: a3, B: b3, Cin: c3 });
    } else {
      COMBOS = [{ A: 0, B: 0 }, { A: 0, B: 1 }, { A: 1, B: 0 }, { A: 1, B: 1 }];
    }
  }
  // the arithmetic each row of the table should come to (plain binary, no gates involved)
  function wanted(c) {
    if (GATES) return null;
    if (FN === 5) return (c.An || 0) + (c.Bn || 0) + (c.Cin || 0);
    if (FN === 1) return (c.A || 0) + (c.B || 0);
    if (FN === 2) return (c.A || 0) + (c.B || 0) + (c.Cin || 0);
    if (FN === 3) return (c.A || 0) - (c.B || 0);
    return (c.A || 0) - (c.B || 0) - (c.Cin || 0);
  }
  function valueOf(v) {
    if (GATES) return v.Y;
    return v.value;
  }

  // =============================================================================================== the trainer
  var st = { power: false, checked: false, row: 0, inp: {} };
  INS.forEach(function (k) { st.inp[k] = 0; });
  function over() { var o = {}, k; for (k in st.inp) o[k] = st.inp[k]; return o; }
  function live() { return readAt(st.power ? over() : {}); }

  // ---------- trainer case with a printed, tilted panel
  var TW = 0.62, TD = 0.26, TH = 0.055;
  var tr = new T.Group(); S.scene.add(tr); tr.position.set(0, 0, -0.1);
  var caseM = new T.MeshStandardMaterial({ color: 0x2f343c, roughness: 0.5, metalness: 0.1 });
  var tcase = S.rounded(TW, TD, TH, 0.012, caseM); tcase.rotation.x = -Math.PI / 2; tcase.position.y = TH / 2 + 0.003; tr.add(tcase);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.01, 0.011, 0.004, 14), M.rubber);
    ft.position.set(f[0] * (TW / 2 - 0.03), 0.002, f[1] * (TD / 2 - 0.03)); tr.add(ft);
  });
  var SWX = INS.length <= 3 ? [-0.22, -0.17, -0.12] : [-0.26, -0.225, -0.19, -0.155, -0.1, -0.065, -0.03, 0.005];
  var LEDX = [0.17, 0.225];
  var panelTex = S.canvasTex(1800, Math.round(1800 * (TD - 0.02) / (TW - 0.02)), function (x, w, h) {
    var X = function (u) { return (u / (TW - 0.02) + 0.5) * w; }, Y = function (zz) { return (zz / (TD - 0.02) + 0.5) * h; };
    x.fillStyle = '#242830'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 4; x.strokeRect(14, 14, w - 28, h - 28);
    x.fillStyle = '#f1efe8'; x.font = '700 44px "Public Sans", sans-serif'; x.fillText('DIGITAL LOGIC TRAINER', 44, 74);
    x.font = '500 28px "Public Sans", sans-serif'; x.fillStyle = '#b9c0cb';
    x.fillText('+5 V regulated  ·  TTL levels: LOW below 0.8 V, HIGH above 2 V', 44, 116);
    // supply rail strip
    x.fillStyle = '#b8322a'; x.fillRect(X(-0.26), Y(-0.055) - 8, X(0.26) - X(-0.26), 16);
    x.fillStyle = '#f1efe8'; x.font = '700 30px "Public Sans", sans-serif';
    x.fillText('+5 V', X(-0.295), Y(-0.045));
    x.fillStyle = '#2c5fb4'; x.fillRect(X(-0.26), Y(-0.02) - 8, X(0.26) - X(-0.26), 16);
    x.fillStyle = '#f1efe8'; x.fillText('GND', X(-0.3), Y(-0.01));
    x.textAlign = 'center';
    x.font = '700 34px "Public Sans", sans-serif';
    x.fillText('INPUT SWITCHES', X(-0.17), Y(0.105));
    INS.forEach(function (k, i) { x.fillStyle = '#f1efe8'; x.font = '700 36px "Public Sans", sans-serif';
      x.fillText(k === 'Cin' ? (FN === 3 || FN === 4 ? 'B_in' : 'C_in') : k === 'An' ? 'A (4 bit)' : k === 'Bn' ? 'B (4 bit)' : k, X(SWX[i]), Y(0.025)); });
    x.font = '700 34px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8';
    x.fillText('OUTPUT LAMPS', X(0.2), Y(0.105));
    OUTS.forEach(function (o, i) { x.font = '700 36px "Public Sans", sans-serif'; x.fillText(o[1], X(LEDX[i]), Y(0.025)); });
    x.font = '600 26px "Public Sans", sans-serif'; x.fillStyle = '#b9c0cb';
    x.fillText('POWER', X(-0.005), Y(0.105));
    x.textAlign = 'left';
  });
  var pf = new T.Mesh(new T.PlaneGeometry(TW - 0.02, TD - 0.02), new T.MeshStandardMaterial({ map: panelTex, roughness: 0.55 }));
  pf.rotation.x = -Math.PI / 2; pf.position.set(0, TH + 0.0038, -0.1); S.scene.add(pf);
  S.contact(TW + 0.1, TD + 0.1, 0, -0.1, 0.55);
  function tp(u, zz) { return new T.Vector3(u, TH + 0.004, -0.1 + zz); }

  // ---------- slide switches
  var switches = INS.map(function (k, i) {
    var g = new T.Group(); S.scene.add(g); g.position.copy(tp(SWX[i], 0.065));
    var frame = S.rounded(0.014, 0.024, 0.006, 0.002, new T.MeshStandardMaterial({ color: 0x15171b, roughness: 0.5 }));
    frame.rotation.x = -Math.PI / 2; frame.position.y = 0.003; g.add(frame);
    var lever = S.mesh(new T.BoxGeometry(0.008, 0.006, 0.009), new T.MeshStandardMaterial({ color: 0xe8e4d8, roughness: 0.5 }));
    lever.position.set(0, 0.008, 0.006); g.add(lever);
    g.userData = { lever: lever, key: k };
    return g;
  });
  function setSwitchLook() {
    switches.forEach(function (g) { g.userData.lever.position.z = st.inp[g.userData.key] ? -0.006 : 0.006; });
  }
  setSwitchLook();

  // ---------- output lamps
  var leds = OUTS.map(function (o, i) {
    var g = new T.Group(); S.scene.add(g); g.position.copy(tp(LEDX[i], 0.065));
    var mat = new T.MeshStandardMaterial({ color: 0x4a1210, roughness: 0.25, emissive: 0x000000, transparent: true, opacity: 0.9 });
    var dome = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.006, 22), mat); dome.position.y = 0.003; g.add(dome);
    var tip = S.mesh(new T.SphereGeometry(0.0045, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), mat); tip.position.y = 0.006; g.add(tip);
    var ring = S.mesh(new T.TorusGeometry(0.0055, 0.0011, 8, 22), M.chrome); ring.rotation.x = Math.PI / 2; ring.position.y = 0.0012; g.add(ring);
    g.userData = { mat: mat, key: o[0] };
    return g;
  });

  // ---------- power rocker and pilot
  var rocker = S.rounded(0.018, 0.012, 0.008, 0.003, M.bakelite); rocker.position.copy(tp(-0.005, 0.065)); rocker.position.y += 0.004; S.scene.add(rocker);
  var rmark = S.mesh(new T.BoxGeometry(0.009, 0.001, 0.0018), M.white, false); rmark.position.set(0, 0.0045, 0.003); rocker.add(rmark);
  var pilotM = new T.MeshStandardMaterial({ color: 0x14401c, roughness: 0.3 });
  var pilot = S.mesh(new T.SphereGeometry(0.005, 18, 12, 0, Math.PI * 2, 0, Math.PI / 2), pilotM);
  pilot.position.copy(tp(0.04, 0.065)); S.scene.add(pilot);
  function setPowerLook() {
    rocker.rotation.x = st.power ? -0.3 : 0.3;
    pilotM.color.setHex(st.power ? 0x3ae05a : 0x14401c);
    pilotM.emissive.setHex(st.power ? 0x2ad04a : 0x000000);
    pilotM.emissiveIntensity = st.power ? 2.0 : 0;
  }
  setPowerLook();

  // ---------- breadboard with the 7400 packages and jumper wires
  var BW = 0.34, BD = 0.1, BT = 0.01, BZ = 0.13;
  var bbTex = S.canvasTex(1400, 420, function (x, w, h) {
    x.fillStyle = '#efece2'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(0,0,0,.12)'; x.lineWidth = 2; x.strokeRect(6, 6, w - 12, h - 12);
    x.fillStyle = '#7d7668';
    var i, j, y;
    for (i = 0; i < 56; i++) for (j = 0; j < 10; j++) { y = 60 + j * 26 + (j >= 5 ? 50 : 0); x.fillRect(66 + i * 21, y, 7, 7); }
    x.fillStyle = '#d7d2c4'; x.fillRect(50, 60 + 5 * 26 + 2, w - 100, 44);
  });
  var bb = S.rounded(BW, BD, BT, 0.004, new T.MeshStandardMaterial({ color: 0xefece2, roughness: 0.6 }));
  bb.rotation.x = -Math.PI / 2; bb.position.set(0, BT / 2, BZ); S.scene.add(bb);
  var bbTop = new T.Mesh(new T.PlaneGeometry(BW - 0.004, BD - 0.004), new T.MeshStandardMaterial({ map: bbTex, roughness: 0.65 }));
  bbTop.rotation.x = -Math.PI / 2; bbTop.position.set(0, BT + 0.0004, BZ); S.scene.add(bbTop);
  S.contact(BW + 0.08, BD + 0.06, 0, BZ, 0.5);

  var chips = new T.Group(); S.scene.add(chips);
  var icTex = S.canvasTex(600, 240, function (x, w, h) {
    x.fillStyle = '#15161a'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#9ba1a9'; x.font = '700 58px "Public Sans", sans-serif'; x.fillText('SN7400N', 40, 100);
    x.font = '600 42px "Public Sans", sans-serif'; x.fillText('QUAD 2-NAND', 40, 168);
  });
  var icIdx;
  for (icIdx = 0; icIdx < NCHIPS; icIdx++) {
    var g = new T.Group(); chips.add(g);
    g.position.set(-0.1 + icIdx * 0.1, BT + 0.0018, BZ);
    var dipM = [new T.MeshStandardMaterial({ color: 0x15161a, roughness: 0.42 }), new T.MeshStandardMaterial({ color: 0x15161a, roughness: 0.42 }),
      new T.MeshStandardMaterial({ map: icTex, roughness: 0.42 }), new T.MeshStandardMaterial({ color: 0x15161a, roughness: 0.42 }),
      new T.MeshStandardMaterial({ color: 0x15161a, roughness: 0.42 }), new T.MeshStandardMaterial({ color: 0x15161a, roughness: 0.42 })];
    var dip = S.mesh(new T.BoxGeometry(0.019, 0.0036, 0.0068), dipM); dip.position.y = 0.0018; g.add(dip);
    var notch = S.mesh(new T.CylinderGeometry(0.0011, 0.0011, 0.0014, 12, 1, false, 0, Math.PI), new T.MeshStandardMaterial({ color: 0x2a2c32, roughness: 0.5 }), false);
    notch.position.set(-0.0095, 0.0036, 0); g.add(notch);
    var pi, sg;
    for (pi = 0; pi < 7; pi++) for (sg = -1; sg <= 1; sg += 2) {
      var pin = S.mesh(new T.BoxGeometry(0.0006, 0.004, 0.0003), M.chrome, false);
      pin.position.set(-0.0076 + pi * 0.00254, -0.0012, sg * 0.0038); g.add(pin);
    }
  }
  // jumper wires from the trainer's switches / rail to the chips, and from the chips to the lamps
  INS.forEach(function (k, i) {
    S.wire([[SWX[i], TH + 0.006, -0.1 + 0.075], [SWX[i] - 0.01, 0.03, 0.03], [-0.12 + i * 0.02, BT + 0.004, BZ - BD / 2 + 0.006]], 'gold');
  });
  OUTS.forEach(function (o, i) {
    S.wire([[0.06 + i * 0.02, BT + 0.004, BZ - BD / 2 + 0.006], [LEDX[i] - 0.02, 0.03, 0.03], [LEDX[i], TH + 0.006, -0.1 + 0.075]], 'blue');
  });
  S.wire([[-0.24, TH + 0.005, -0.155], [-0.2, 0.03, 0.02], [-0.14, BT + 0.004, BZ + BD / 2 - 0.006]], 'red');
  S.wire([[-0.24, TH + 0.005, -0.12], [-0.18, 0.025, 0.04], [0.14, BT + 0.004, BZ + BD / 2 - 0.006]], 'black');

  // ---------- logic probe
  var probe = new T.Group(); S.scene.add(probe); probe.position.set(0.3, 0, 0.1); probe.rotation.y = -0.4;
  var pbody = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.12, 20), new T.MeshStandardMaterial({ color: 0xd9682a, roughness: 0.5 }));
  pbody.rotation.z = Math.PI / 2; pbody.position.y = 0.009; probe.add(pbody);
  var ptip = S.mesh(new T.ConeGeometry(0.0035, 0.025, 16), M.chrome); ptip.rotation.z = -Math.PI / 2; ptip.position.set(0.072, 0.009, 0); probe.add(ptip);
  var plampM = new T.MeshStandardMaterial({ color: 0x4a1210, roughness: 0.3 });
  var plamp = S.mesh(new T.SphereGeometry(0.004, 16, 10), plampM); plamp.position.set(-0.03, 0.016, 0); probe.add(plamp);
  S.contact(0.17, 0.08, 0.3, 0.1, 0.45);

  S.addApparatus('tr', tr, 'Digital logic trainer', 'A 5 volt regulated rail, slide switches that put a clean HIGH or LOW on each input, and lamps on the outputs. Transistor-transistor logic reads anything below 0.8 V as LOW and anything above 2 V as HIGH.');
  S.addApparatus('bb', bb, 'Solderless breadboard', 'The NAND packages straddle the central channel, and the jumper wires make the circuit.');
  S.addApparatus('chips', chips, NCHIPS + ' × SN7400 quad 2-input NAND', 'Fourteen pins: four NAND gates, pin 14 to +5 V and pin 7 to ground. ' + BUILD);
  S.addApparatus('sw', switches[0], 'Input switch ' + INS[0], 'Up is HIGH (+5 V), down is LOW (ground). The hand flips it.');
  S.addApparatus('led', leds[0], 'Output lamp ' + OUTS[0][1], 'Lit means the output is HIGH.');
  S.addApparatus('probe', probe, 'Logic probe', 'Touch it on any pin to see whether that node is HIGH or LOW: that is how a wrong gate is found.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every row of the truth table you take is written here, as in a real practical file.');

  var hudIn = S.hudCard('Inputs'), hudOut = S.hudCard('Outputs'), hudRow = S.hudCard('Row');

  // =============================================================================================== human actions
  function flip(key, value) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!st.power) { S.say('Switch the trainer on first.'); return Promise.resolve(); }
    if (st.inp[key] === value) return Promise.resolve();
    var g = switches[INS.indexOf(key)];
    if (!g) { st.inp[key] = value; return Promise.resolve(); }
    return S.hand.tap(g.userData.lever, 'front').then(function () {
      st.inp[key] = value; setSwitchLook(); S.click(1400, 0.03); S.render();
    });
  }
  function setWord(key, value) {
    // a four-bit word on the trainer: its four switches are flipped one after the other
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    st.inp[key] = value; setSwitchLook();
    return S.hand.tap(switches[INS.indexOf(key)] ? switches[INS.indexOf(key)].userData.lever : rocker, 'front')
      .then(function () { S.click(1400, 0.03); S.render(); });
  }
  function toggleTrainer(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (on === st.power) return Promise.resolve();
    return S.hand.tap(rocker, 'front').then(function () {
      st.power = on; setPowerLook(); S.click(900, 0.05);
      S.say(on ? 'Trainer on: the green pilot is lit and the rail is at 5 volts.' : 'Trainer off.');
      S.render();
    });
  }
  function applyCombo(i) {
    var c = COMBOS[i];
    return INS.reduce(function (pr, k) {
      return pr.then(function () { return FN === 5 && (k === 'An' || k === 'Bn') ? setWord(k, c[k]) : flip(k, c[k] || 0); });
    }, Promise.resolve()).then(function () { st.row = i; S.render(); });
  }
  function matchesRow(i) {
    var c = COMBOS[i], k;
    for (k = 0; k < INS.length; k++) if ((c[INS[k]] || 0) !== st.inp[INS[k]]) return false;
    return true;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return; }
    if (!st.power) { S.say('Switch the trainer on first.'); return; }
    var i, found = -1;
    for (i = 0; i < COMBOS.length; i++) if (matchesRow(i)) found = i;
    if (found < 0) { S.say('These switch settings are not one of the rows of the table. Use "Set the next row".'); return; }
    for (i = 0; i < S.rows.length; i++) if (S.rows[i].ri === found) { S.say('Row ' + (found + 1) + ' is already in your record book.'); return; }
    var v = live(), row = { ri: found };
    INS.forEach(function (k) { row[k] = st.inp[k]; });
    OUTS.forEach(function (o) { row[o[0]] = v[o[0]]; });
    row.val = valueOf(v);
    row.want = wanted(COMBOS[found]);
    S.addRow(row);
    S.say('Row ' + (found + 1) + ' written: ' + OUTS.map(function (o) { return o[1] + ' = ' + v[o[0]]; }).join(', ') + '.');
  }
  function enough() { return S.rows.length >= COMBOS.length; }

  var SIG_TRUTH = (function () {
    var tot = 0, i;
    for (i = 0; i < COMBOS.length; i++) tot += bit(readAt(COMBOS[i])[OUTS[0][0]]) * Math.pow(2, i);
    return tot;
  })();

  return {
    camera: { pos: [0.0, 0.52, 0.62], look: [0.0, 0.03, -0.06] },
    views: {
      tr: [[0.0, 0.3, 0.18], [0.0, 0.04, -0.12]], bb: [[0.0, 0.22, 0.3], [0.0, 0.01, 0.12]],
      chips: [[-0.06, 0.1, 0.22], [-0.06, 0.015, 0.13]], sw: [[-0.2, 0.14, 0.06], [-0.19, 0.06, -0.04]],
      led: [[0.2, 0.14, 0.06], [0.2, 0.06, -0.04]], probe: [[0.3, 0.14, 0.24], [0.3, 0.02, 0.1]],
      bench: [[0.05, 0.44, 0.66], [0.0, 0.03, -0.04]], book: [[-0.42, 0.44, 0.52], [-0.5, 0.0, 0.08]],
    },
    theory: {
      principle: 'NAND is a universal gate: every Boolean function can be built out of NAND gates alone, because ' +
        'a NAND with its inputs joined inverts, and De Morgan\'s theorem turns any sum into a product of ' +
        'complements. This circuit is a ' + NAME + '.',
      formula: GATES ? (GATE_EXPR[FN] || GATE_EXPR[4]) :
        (FN === 3 || FN === 4 ? "D = A ⊕ B ⊕ B_in,   B_out = A'·B + B_in·(A ⊕ B)'"
          : 'S = A ⊕ B ⊕ C_in,   C_out = A·B + C_in·(A ⊕ B)'),
      formulaNote: BUILD,
      more: [S.lab.theory,
        'On a 7400 in transistor-transistor logic a LOW is anything below 0.8 V and a HIGH anything above 2 V, ' +
        'while the outputs are guaranteed below 0.4 V and above 2.4 V. The gap between what an output promises ' +
        'and what an input demands is the noise margin, and it is why a digital circuit does not drift.'],
      precautions: S.lab.safety + ' Wire the circuit with the trainer switched off, and check pin 14 and pin 7 on ' +
        'every package before switching on.',
    },
    book: {
      title: 'Expt. — ' + S.lab.title,
      lines: ['Aim: ' + S.lab.aim, 'Circuit: ' + NAME + '. ' + BUILD,
        'ICs: ' + NCHIPS + ' × SN7400 (pin 14 → +5 V, pin 7 → GND)',
        'Inputs from the trainer\'s slide switches; outputs read on its lamps.',
        'Precautions: wire with the power off; check the supply pins first.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }]
        .concat(INS.map(function (k) {
          return { label: k === 'Cin' ? (FN === 3 || FN === 4 ? 'B_in' : 'C_in') : k === 'An' ? 'A' : k === 'Bn' ? 'B' : k,
            get: function (r) { return String(r[k]); } };
        }))
        .concat(OUTS.map(function (o) { return { label: o[1], get: function (r) { return String(r[o[0]]); } }; }))
        .concat(GATES ? [] : [{ label: 'value', get: function (r) { return String(r.val); } },
          { label: 'A ± B', get: function (r) { return String(r.want); } }]),
    },
    graph: null,
    result: function (rows) {
      if (rows.length < COMBOS.length) return null;
      if (GATES) {
        var tot = 0, i;
        for (i = 0; i < COMBOS.length; i++) {
          var r = null, j;
          for (j = 0; j < rows.length; j++) if (rows[j].ri === i) r = rows[j];
          if (!r) return null;
          tot += bit(r.Y) * Math.pow(2, i);
        }
        return { label: 'Output column of the truth table, read as a binary number', value: tot, unit: '',
          digits: 0, truth: SIG_TRUTH,
          note: 'Top row is the least significant bit. For this gate the Boolean expression ' +
            (GATE_EXPR[FN] || GATE_EXPR[4]) + ' gives the same number.' };
      }
      var agree = 0, k;
      for (k = 0; k < rows.length; k++) if (rows[k].val === rows[k].want) agree += 1;
      return { label: 'Rows that agree with binary arithmetic', value: agree, unit: 'of ' + COMBOS.length,
        digits: 0, truth: COMBOS.length,
        note: 'Each row\'s lamps are read as a number and compared with plain arithmetic on the input bits.' };
    },
    tol: 0.001,
    resultNote: GATES
      ? 'Every row of the table agrees with the Boolean expression, and the circuit was built from nothing but ' +
        '2-input NAND gates. That is what universality means in practice: one package in the drawer is enough.'
      : 'Every row of the table agrees with plain binary arithmetic on the input bits, and the whole circuit is ' +
        'NAND gates. The difference output of a subtractor is the same function as the sum output of an adder, ' +
        'which is why one circuit with a control line can be made to do both.',
    chips: GATES
      ? ['Why is NAND universal?', 'How is this gate built from NAND gates?', 'What is the noise margin?', 'Check my truth table']
      : ['How does the carry get out?', 'Why is the sum an exclusive-OR?', 'What is a ripple-carry delay?', 'Check my truth table'],
    viva: GATES
      ? [['A NAND gate with both inputs tied together behaves as', ['a NOT gate', 'an AND gate', 'a short circuit'], 0,
        "A NAND A = (A·A)' = A'."],
        ['Building an OR gate out of NAND gates uses', ["De Morgan's theorem", 'the distributive law', 'the consensus theorem'], 0,
          "A + B = (A'·B')', which is one NAND of the two complements."]]
      : [['The carry output of a full adder is', ['A·B + C_in(A ⊕ B)', 'A ⊕ B ⊕ C_in', 'A·B·C_in'], 0,
        'A carry appears if both inputs are 1, or if one of them is and a carry came in.'],
        ['The borrow of a half subtractor is', ["A'·B", 'A·B', 'A ⊕ B'], 0,
          'A borrow is needed only when A is 0 and B is 1.']],
    askState: function () {
      var v = live(), out = { trainer_on: st.power, circuit: NAME, built_from: BUILD,
        rows_recorded: S.rows.length, rows_needed: COMBOS.length };
      INS.forEach(function (k) { out['input_' + k] = st.inp[k]; });
      OUTS.forEach(function (o) { out['output_' + o[1]] = st.power ? v[o[0]] : 0; });
      if (!GATES) out.arithmetic_expected = wanted(COMBOS[st.row]);
      return out;
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'chips', render: function (u) {
          u.h2('Wire the circuit and switch the trainer on');
          u.p(NCHIPS + ' × SN7400 on the breadboard. ' + BUILD);
          u.p('Pin 14 of every package goes to the +5 V rail and pin 7 to ground. The inputs come from the ' +
            'trainer\'s slide switches and the outputs go to its lamps.');
          u.task('1. Check the supply pins and the wiring', st.checked,
            st.checked ? 'Pin 14 to +5 V, pin 7 to ground on every package' : 'Look over the board')
            .add(u.button(st.checked ? 'Checked' : 'Check the wiring', function () {
              st.checked = true; S.focus('chips');
              S.say('Pin 14 of each 7400 is on the red rail and pin 7 on the blue one. ' + BUILD);
              S.render();
            }, !st.checked, st.checked));
          u.task('2. Switch the trainer on', st.power, st.power ? 'The green pilot is lit' : 'The hand presses the rocker')
            .add(u.button(st.power ? 'Switch off' : 'Switch on the trainer', function () {
              S.focus('tr'); toggleTrainer(!st.power);
            }, !st.power, S.hand.busy));
          u.note('Wire a logic circuit with the power off. Never join two outputs together, and never wire an ' +
            'output straight to the supply rail.');
          u.next('Next: take the truth table', st.checked && st.power);
        },
        ok: function () { return st.checked && st.power; },
        auto: function () { st.checked = true; return toggleTrainer(true); } },
      { id: 'table', title: 'Truth table', view: 'tr', render: function (u) {
          u.h2('Set every input combination and read the lamps');
          u.p('There ' + (COMBOS.length === 1 ? 'is 1 row' : 'are ' + COMBOS.length + ' rows') +
            ' to take. The hand flips the switches; you read the lamps and write the row down.');
          u.row.apply(u, COMBOS.map(function (c, i) {
            var labelBits = INS.map(function (k) { return k + '=' + (c[k] || 0); }).join(' ');
            return u.button('Row ' + (i + 1) + ': ' + labelBits, function () { applyCombo(i); }, i === st.row, S.hand.busy);
          }).slice(0, 8));
          u.live(function () {
            var v = live();
            return 'Inputs ' + INS.map(function (k) { return k + '=' + st.inp[k]; }).join(' ') + '   →   ' +
              OUTS.map(function (o) { return o[1] + '=' + (st.power ? v[o[0]] : '—'); }).join('  ');
          });
          u.row(u.button('Record this row', function () { record(); }, true, S.hand.busy));
          u.h3('Truth table'); u.table();
          if (!enough()) u.p(S.rows.length + ' of ' + COMBOS.length + ' rows recorded.');
          u.next('Next: check the table', enough());
        },
        ok: function () { return enough(); },
        auto: function () {
          return COMBOS.reduce(function (pr, c, i) {
            return pr.then(function () { return applyCombo(i); }).then(record);
          }, Promise.resolve());
        } },
    ],

    tick: function () {
      var v = live();
      leds.forEach(function (g) {
        var on = st.power && bit(v[g.userData.key]) === 1;
        g.userData.mat.color.setHex(on ? 0xff4a34 : 0x4a1210);
        g.userData.mat.emissive.setHex(on ? 0xff3a20 : 0x000000);
        g.userData.mat.emissiveIntensity = on ? 2.2 : 0;
      });
      var probeOn = st.power && bit(v[OUTS[0][0]]) === 1;
      plampM.emissive.setHex(probeOn ? 0xff3a20 : 0x000000);
      plampM.emissiveIntensity = probeOn ? 1.4 : 0;
      hudIn.set(INS.map(function (k) { return k + '=' + st.inp[k]; }).join(' '));
      hudOut.set(st.power ? OUTS.map(function (o) { return o[1] + '=' + v[o[0]]; }).join('  ') : 'off');
      hudRow.set(S.rows.length + ' / ' + COMBOS.length + ' rows');
    },
  };
});
