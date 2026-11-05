/* Prayogshala studio rig: the school cell-and-bulb board (NCERT Science VI / VII).
   One apparatus serves four set-ups - a simple circuit, cells joined into a battery, a home-made safety-pin switch
   and a circuit tester for conductors and insulators. Which one is open is read from the lab, never hard-coded:
   the number of cells comes from params.ncell, the switch from the lab id, the sample from the family variant.
   Every reading comes from the circuit kernel (MNA) run on the lab's own netlist - the numbers the server checks. */
HoolaStudio.define('school-bulb-circuit', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.circuit, CFG = S.lab.cfg;
  var p = window.HoolaKernels.paramsFor('circuit', S.lab.params);
  var V_ = S.lab.variant || {}, BASE = V_.base || S.lab.id, SAMPLE = V_.sample || '';
  var TESTER = BASE === 'conductors-insulators-tester', PINSW = BASE === 'make-a-switch';
  var NCELL = Math.max(1, Math.round(p.ncell || 1)), EB1 = p.Eb / NCELL, RI1 = p.rint / NCELL;
  var RSAM = p.Rsam === undefined ? 0 : p.Rsam, RINS = p.Rins === undefined ? 1e8 : p.Rins;
  function pick(list, need) { for (var i = 0; i < list.length; i++) if (list[i] >= need - 1e-9) return list[i]; return list[list.length - 1]; }
  var IMAX = EB1 * NCELL / (p.Rb + RI1), AMAX = pick([0.5, 1, 1.5, 2, 3], IMAX * 1.3), VMAX = pick([1, 3, 5], EB1 * NCELL);
  var ARES = AMAX / 100, VRES = VMAX / 300, IDIG = ARES < 0.01 - 1e-12 ? 3 : 3;
  function fmtN(v) { return String(+v.toFixed(2)); }
  var st = { key: false, cells: NCELL, traced: false, zero: false, placed: !TESTER, insulator: false };
  var view = {};

  function solve() {
    p.key = st.key ? 1 : 0;
    p.Eb = EB1 * st.cells; p.rint = RI1 * st.cells;
    if (TESTER) p.Rsam = st.insulator ? RINS : RSAM;
    view = K.view(K.init(p, CFG), p, CFG);
  }
  function I() { return st.key && st.placed ? view.I_AM : 0; }
  function Vb() { return st.key && st.placed && view.V_LAMP !== undefined ? view.V_LAMP : 0; }
  function rI(v) { return Math.round(v / ARES) * ARES; }
  function fI(v) { return rI(v).toFixed(IDIG); }
  function fV(v) { return (Math.round(v / VRES) * VRES).toFixed(2); }
  function glow() { var w = Vb() * I(); return Math.max(0, Math.min(1, w / (EB1 * NCELL * IMAX * 0.8))); }

  // ---------- small helpers kept inside this module
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }

  // ---------- the wooden base board every piece is screwed to
  var plank = S.rounded(1.5, 0.78, 0.014, 0.01, M.wood); plank.rotation.x = -Math.PI / 2; plank.position.set(-0.05, 0.007, -0.27); S.scene.add(plank);
  S.contact(1.56, 0.84, -0.05, -0.27, 0.45);
  var BY = 0.014;                                   // everything stands on the plank

  // ---------- cell holder with NCELL dry cells (1.5 V each)
  var CH = [-0.6, -0.14], CW = 0.062 * NCELL + 0.03;
  var holder = new T.Group(); S.scene.add(holder); holder.position.set(CH[0], BY, CH[1]);
  holder.add((function () { var b = S.rounded(CW, 0.09, 0.016, 0.004, M.darkWood); b.rotation.x = -Math.PI / 2; b.position.y = 0.008; return b; })());
  var cells = [];
  for (var ci = 0; ci < NCELL; ci++) {
    var cx = -CW / 2 + 0.031 + ci * 0.062;
    var cg = new T.Group(); holder.add(cg); cg.position.set(cx, 0.033, 0);
    var body = S.mesh(new T.CylinderGeometry(0.0165, 0.0165, 0.05, 28), new T.MeshStandardMaterial({ color: 0x1f3b82, roughness: 0.4, metalness: 0.15 }));
    body.rotation.x = Math.PI / 2; cg.add(body);
    var zinc = S.mesh(new T.CylinderGeometry(0.0168, 0.0168, 0.004, 28), M.steel); zinc.rotation.x = Math.PI / 2; zinc.position.z = -0.026; cg.add(zinc);
    var cap = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.004, 18), M.brass); cap.rotation.x = Math.PI / 2; cap.position.z = 0.0275; cg.add(cap);
    var lbl = S.label('1.5 V', { w: 0.03, ratio: 0.34, color: '#f4f4f4' }); lbl.position.set(0, 0.0168, 0); lbl.rotation.x = -Math.PI / 2; cg.add(lbl);
    var plus = S.label('+', { w: 0.008, ratio: 1, color: '#f4f4f4', weight: 800 }); plus.position.set(0.0, 0.0168, 0.019); plus.rotation.x = -Math.PI / 2; cg.add(plus);
    cells.push(cg);
  }
  [-1, 1].forEach(function (s) { var sp = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.02, 10), M.steel); sp.position.set(s * (CW / 2 - 0.004), 0.033, 0); sp.rotation.z = Math.PI / 2; holder.add(sp); });
  var chPlate = S.label(NCELL > 1 ? 'CELL HOLDER  ·  ' + NCELL + ' × 1.5 V' : 'CELL HOLDER  ·  1.5 V', { w: 0.1, ratio: 0.14, color: '#f3ead2', bg: '#2b2b2b', px: 768 });
  chPlate.rotation.x = -Math.PI / 2; chPlate.position.set(CH[0], BY + 0.0165, CH[1] + 0.058); S.scene.add(chPlate);
  var cellP = post(CH[0] + CW / 2 + 0.014, BY, CH[1], 'red'), cellM = post(CH[0] - CW / 2 - 0.014, BY, CH[1], 'black');
  S.contact(CW + 0.1, 0.16, CH[0], CH[1], 0.4);

  // ---------- the switch: a plug key, or two drawing pins and a safety pin
  var KP = [-0.3, -0.06];
  var key = null, plug = null, pinBase = null, pinArm = null;
  if (PINSW) {
    pinBase = new T.Group(); S.scene.add(pinBase); pinBase.position.set(KP[0], BY, KP[1]);
    var pb = S.rounded(0.12, 0.07, 0.012, 0.004, M.darkWood); pb.rotation.x = -Math.PI / 2; pb.position.y = 0.006; pinBase.add(pb);
    [[-0.035], [0.035]].forEach(function (q) {
      var head = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 0.0022, 20), M.brass); head.position.set(q[0], 0.0132, 0); pinBase.add(head);
      var shaft = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.01, 8), M.steel); shaft.position.set(q[0], 0.007, 0); pinBase.add(shaft);
    });
    pinArm = new T.Group(); pinArm.position.set(-0.035, 0.0145, 0); pinBase.add(pinArm);
    var sp1 = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 0.07, 8), M.chrome); sp1.rotation.z = Math.PI / 2; sp1.position.x = 0.035; pinArm.add(sp1);
    var sp2 = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 0.058, 8), M.chrome); sp2.rotation.z = Math.PI / 2; sp2.position.set(0.033, 0.0022, 0.0016); pinArm.add(sp2);
    var coil = S.mesh(new T.TorusGeometry(0.0035, 0.0007, 8, 16), M.chrome); coil.rotation.y = Math.PI / 2; pinArm.add(coil);
    var clasp = S.rounded(0.012, 0.005, 0.005, 0.001, M.chrome); clasp.position.set(0.069, 0.001, 0.0008); pinArm.add(clasp);
    var swLbl = S.label('HOME-MADE SWITCH', { w: 0.08, ratio: 0.12, color: '#f3ead2', bg: '#2b2b2b', px: 768 });
    swLbl.rotation.x = -Math.PI / 2; swLbl.position.set(KP[0], BY + 0.0128, KP[1] + 0.043); S.scene.add(swLbl);
    S.contact(0.16, 0.11, KP[0], KP[1], 0.4);
  } else {
    key = S.plugKey([KP[0], BY, KP[1]]); plug = key.userData.plug;
    var keyLbl = S.label('K', { w: 0.013, ratio: 1, color: '#f0e6c8' }); keyLbl.rotation.x = -Math.PI / 2; keyLbl.position.set(KP[0], BY + 0.0175, KP[1] + 0.016); S.scene.add(keyLbl);
  }
  var kL = post(KP[0] - 0.045, BY, KP[1] - 0.042, 'red'), kR = post(KP[0] + 0.045, BY, KP[1] - 0.042, 'black');
  var ZAX = new T.Vector3(0, 0, 1);
  function plugPose(k) { return { x: 0.062 * (1 - k), y: 0.008 + 0.016 * k + 0.04 * Math.sin(Math.PI * k), z: 0.012 * (1 - k), rz: Math.PI / 2 * (1 - k) }; }
  function applySwitch(k) {
    if (PINSW) { pinArm.rotation.y = -1.15 * (1 - k); return; }
    var q = plugPose(k); plug.position.set(q.x, q.y, q.z); plug.rotation.set(0, 0, q.rz);
  }
  function switchGrip(k) {
    if (PINSW) { pinArm.updateMatrixWorld(true); return pinArm.localToWorld(new T.Vector3(0.062, 0.004, 0.001)); }
    var q = plugPose(k); return key.localToWorld(new T.Vector3(0, 0.013, 0).applyAxisAngle(ZAX, q.rz).add(new T.Vector3(q.x, q.y, q.z)));
  }
  applySwitch(0);
  function setKey(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!!on === st.key) return Promise.resolve();
    var a = st.key ? 1 : 0, b = on ? 1 : 0;
    if (!on) { st.key = false; solve(); }
    return S.hand.pinchMove(switchGrip(a), function (k) { return switchGrip(a + (b - a) * k); }, function (k) { applySwitch(a + (b - a) * k); },
      { ms: 850, mode: 'top' }).then(function () {
        applySwitch(b); st.key = !!on; solve(); S.click(1500, 0.04, 0.09);
        S.say(on ? (PINSW ? 'The safety pin bridges the two drawing pins: the circuit is complete and the bulb lights.'
          : 'Key closed: current flows and the bulb lights.')
          : (PINSW ? 'The safety pin is swung away: the gap is air, so no current flows.' : 'Key open: no current, and the bulb goes out.'));
        S.render();
      });
  }

  // ---------- ammeter in series, voltmeter across the bulb (not in the tester: a metal sample drops almost nothing)
  var am = S.meter({ min: 0, max: AMAX, ticks: AMAX === 0.5 ? 5 : AMAX === 1 ? 10 : AMAX === 1.5 ? 6 : AMAX === 2 ? 4 : 6,
    unit: 'A', symbol: 'A', caption: 'DC AMMETER 0–' + fmtN(AMAX) + ' A', pos: [-0.02, BY, -0.33] });
  var vm = TESTER ? null : S.meter({ min: 0, max: VMAX, ticks: VMAX === 1 ? 10 : VMAX === 3 ? 6 : 5, unit: 'V', symbol: 'V',
    caption: 'DC VOLTMETER 0–' + fmtN(VMAX) + ' V', pos: [0.4, BY, -0.62] });
  var amP = { at: wpt(am, 0.035, 0.07, -0.03) }, amM = { at: wpt(am, -0.035, 0.07, -0.03) };
  var vmP = vm ? { at: wpt(vm, 0.035, 0.07, -0.03) } : null, vmM = vm ? { at: wpt(vm, -0.035, 0.07, -0.03) } : null;

  // ---------- the torch bulb in a bakelite screw holder
  var BP = [0.42, -0.12];
  var lampG = new T.Group(); S.scene.add(lampG); lampG.position.set(BP[0], BY, BP[1]);
  var hbase = S.rounded(0.075, 0.075, 0.018, 0.005, M.darkWood); hbase.rotation.x = -Math.PI / 2; hbase.position.y = 0.009; lampG.add(hbase);
  var hcup = S.mesh(new T.CylinderGeometry(0.019, 0.022, 0.026, 28), M.bakelite); hcup.position.y = 0.031; lampG.add(hcup);
  var screw = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, 0.013, 20), M.brass); screw.position.y = 0.05; lampG.add(screw);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xf6f3e8, roughness: 0.08, transmission: 0.82, thickness: 0.004, transparent: true, opacity: 0.6 });
  var env = S.mesh(new T.SphereGeometry(0.0155, 24, 18), glassM, false); env.position.y = 0.072; lampG.add(env);
  var neck = S.mesh(new T.CylinderGeometry(0.009, 0.0135, 0.012, 20), glassM, false); neck.position.y = 0.0585; lampG.add(neck);
  var filM = new T.MeshStandardMaterial({ color: 0x5a4a2a, emissive: new T.Color(0, 0, 0), roughness: 0.4, metalness: 0.8 });
  var fil = S.mesh(new T.TorusGeometry(0.0035, 0.0006, 6, 14, Math.PI), filM, false); fil.position.y = 0.071; fil.rotation.x = Math.PI / 2; lampG.add(fil);
  [-1, 1].forEach(function (s) { var w = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.011, 6), M.steel, false); w.position.set(s * 0.0035, 0.0655, 0); lampG.add(w); });
  var halo = new T.PointLight(0xffe4a8, 0, 0.5); halo.position.set(0, 0.072, 0); lampG.add(halo);
  var bLbl = S.label('1.5 V  TORCH BULB', { w: 0.07, ratio: 0.13, color: '#f3ead2', bg: '#2b2b2b', px: 768 });
  bLbl.rotation.x = -Math.PI / 2; bLbl.position.set(0, 0.0185, 0.05); lampG.add(bLbl);
  S.contact(0.13, 0.13, BP[0], BP[1], 0.45);
  var bP = post(BP[0] - 0.03, BY, BP[1] - 0.03, 'red'), bM = post(BP[0] + 0.03, BY, BP[1] - 0.03, 'black');

  // ---------- the tester: two probes on a stand and the sample between them
  var probeL = null, probeR = null, sampleG = null, SAMPOS = [0.62, -0.3];
  if (TESTER) {
    var pr = new T.Group(); S.scene.add(pr); pr.position.set(SAMPOS[0], BY, SAMPOS[1]);
    var prb = S.rounded(0.14, 0.1, 0.012, 0.004, M.darkWood); prb.rotation.x = -Math.PI / 2; prb.position.y = 0.006; pr.add(prb);
    [[-1, 'red'], [1, 'black']].forEach(function (q) {
      var g = new T.Group(); pr.add(g); g.position.set(q[0] * 0.05, 0.012, 0);
      var grip = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.035, 18), q[1] === 'red' ? M.red : M.blackPlastic); grip.position.y = 0.0175; g.add(grip);
      var tip = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, 0.03, 10), M.chrome); tip.rotation.z = -q[0] * Math.PI / 2; tip.position.set(-q[0] * 0.015, 0.03, 0); g.add(tip);
      if (q[0] < 0) probeL = g; else probeR = g;
    });
    sampleG = new T.Group(); S.scene.add(sampleG);
    var sMat = /alumin/i.test(SAMPLE) ? new T.MeshStandardMaterial({ color: 0xd6d8da, roughness: 0.3, metalness: 0.9 })
      : /copper|coin/i.test(SAMPLE) ? M.copper
        : /nichrome|wire/i.test(SAMPLE) ? new T.MeshStandardMaterial({ color: 0xb4b2ae, roughness: 0.3, metalness: 0.85 })
          : /wood/i.test(SAMPLE) ? M.wood
            : /graphite|pencil/i.test(SAMPLE) ? new T.MeshStandardMaterial({ color: 0x2a2a2d, roughness: 0.6 })
              : new T.MeshStandardMaterial({ color: 0x6e7276, roughness: 0.35, metalness: 0.8 });
    var sBody = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.085, 14), sMat); sBody.rotation.z = Math.PI / 2; sampleG.add(sBody);
    var sTag = S.label(SAMPLE || 'Iron nail', { w: 0.1, ratio: Math.min(0.1, 1.9 / ((SAMPLE || 'Iron nail').length + 6)), px: 768, color: '#2b2b2b', bg: '#f3ead2' });
    sTag.rotation.x = -Math.PI / 2; sTag.position.set(0, -0.0035, 0.022); sampleG.add(sTag);
    sampleG.position.set(SAMPOS[0] + 0.02, BY + 0.043, SAMPOS[1] + 0.12);
    var tLbl = S.label('CIRCUIT TESTER  ·  SAMPLE HERE', { w: 0.1, ratio: 0.1, color: '#f3ead2', bg: '#2b2b2b', px: 768 });
    tLbl.rotation.x = -Math.PI / 2; tLbl.position.set(SAMPOS[0], BY + 0.0128, SAMPOS[1] + 0.058); S.scene.add(tLbl);
    S.contact(0.18, 0.14, SAMPOS[0], SAMPOS[1], 0.4);
  }
  var tP = TESTER ? post(SAMPOS[0] - 0.05, BY, SAMPOS[1] - 0.038, 'red') : null;
  var tM = TESTER ? post(SAMPOS[0] + 0.05, BY, SAMPOS[1] - 0.038, 'black') : null;

  // ---------- the leads: one single loop, exactly as the book draws it
  lead(cellP.at, kL.at, 'red', [[-0.5, -0.24], [-0.38, -0.16]]);
  lead(kR.at, amP.at, 'red', [[-0.22, -0.2], [-0.06, -0.28]]);
  if (TESTER) {
    lead(amM.at, bP.at, 'yellow', [[-0.1, -0.42], [0.3, -0.36]]);
    lead(bM.at, tP.at, 'yellow', [[0.5, -0.2], [0.56, -0.26]]);
    lead(tM.at, cellM.at, 'black', [[0.68, -0.52], [0.1, -0.66], [-0.66, -0.5], [-0.68, -0.3]]);
  } else {
    lead(amM.at, bP.at, 'yellow', [[0.08, -0.3], [0.3, -0.26]]);
    lead(bM.at, cellM.at, 'black', [[0.5, -0.46], [0.0, -0.6], [-0.66, -0.46], [-0.68, -0.26]]);
    lead(vmP.at, bP.at, 'red', [[0.44, -0.56], [0.42, -0.3]]);
    lead(vmM.at, bM.at, 'black', [[0.36, -0.56], [0.46, -0.28]]);
  }

  S.addApparatus('cells', holder, NCELL > 1 ? NCELL + ' dry cells (1.5 V each)' : 'Dry cell (1.5 V)',
    'A zinc-carbon cell of nominal emf 1.5 V. ' + (NCELL > 1 ? 'Joined + to −, the cells add their emfs.' : 'It drives the current round the loop.'));
  S.addApparatus('key', PINSW ? pinBase : key, PINSW ? 'Home-made switch' : 'Plug key K',
    PINSW ? 'Two drawing pins and a safety pin on a wooden block. Swung across, the steel pin completes the circuit.'
      : 'Closes the circuit when the brass plug is pushed in. Take it out between readings.');
  S.addApparatus('am', am, 'Ammeter (0–' + fmtN(AMAX) + ' A)', 'In series, + towards the cell. Its resistance is tiny. Read to ' + fmtN(ARES) + ' A.');
  S.addApparatus('bulb', lampG, 'Torch bulb in its holder', 'A 1.5 V torch bulb. Its filament resists the current and glows white hot.');
  if (vm) S.addApparatus('vm', vm, 'Voltmeter (0–' + fmtN(VMAX) + ' V)', 'Across the bulb. Its resistance is very high, so it takes almost no current.');
  if (TESTER) S.addApparatus('tester', sampleG, SAMPLE ? 'Sample: ' + SAMPLE : 'Sample under test', 'Held between the two probes. If it conducts, the circuit is complete and the bulb lights.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudI = S.hudCard('Ammeter'), hudV = S.hudCard(TESTER ? 'Bulb' : 'Voltmeter'), hudK = S.hudCard(PINSW ? 'Switch' : 'Key');
  solve();

  // ---------- the actions the buttons call (the walk-through uses these same functions)
  function trace() {
    st.traced = true; S.focus('circuit');
    S.say((NCELL > 1 ? NCELL + ' cells' : 'Cell') + ' + → ' + (PINSW ? 'switch' : 'key') + ' → ammeter → bulb → back to the cell − terminal: one single loop'
      + (TESTER ? ', with the sample between the probes.' : (vm ? '. The voltmeter is across the bulb.' : '.')));
    S.render();
  }
  function zeroCheck() {
    if (st.key) { S.say('Open the ' + (PINSW ? 'switch' : 'key') + ' first: the zero is checked with no current.'); return; }
    st.zero = true; S.focus('am'); S.say('With no current both needles rest exactly on zero: there is no zero error.'); S.render();
  }
  function setCells(n) {
    n = Math.max(1, Math.min(NCELL, Math.round(n)));
    if (n === st.cells) return Promise.resolve();
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    var was = st.key;
    return (was ? setKey(false) : Promise.resolve()).then(function () {
      return S.hand.tap(cells[NCELL - 1]);
    }).then(function () {
      st.cells = n; solve();
      S.say(n === 1 ? 'One cell in the holder: 1.5 V drives the circuit.' : n + ' cells in series: ' + fmtN(EB1 * n) + ' V drives the circuit.');
      return was ? setKey(true) : Promise.resolve();
    }).then(function () { S.render(); });
  }
  function place(on) {
    if (!TESTER) return Promise.resolve();
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!!on === st.placed && !st.insulator) return Promise.resolve();
    var from = sampleG.position.clone();
    var to = on ? new T.Vector3(SAMPOS[0], BY + 0.043, SAMPOS[1]) : new T.Vector3(SAMPOS[0] + 0.02, BY + 0.043, SAMPOS[1] + 0.12);
    return S.hand.pinchMove(from.clone().add(new T.Vector3(0, 0.004, 0)),
      function (k) { return from.clone().lerp(to, k).add(new T.Vector3(0, 0.004, 0)); },
      function (k) { sampleG.position.copy(from.clone().lerp(to, k)); }, { ms: 900, mode: 'top' })
      .then(function () {
        sampleG.position.copy(to); st.placed = !!on; st.insulator = false; solve();
        S.say(on ? 'The sample is held between the two probes.' : 'The sample is lifted out of the probes.');
        S.render();
      });
  }
  function tryInsulator() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    st.insulator = true; st.placed = true; solve();
    S.say('A plastic scale between the probes: the bulb stays completely dark. The ammeter reads ' + fI(I()) + ' A - the current is far too small to light it.');
    S.render(); return Promise.resolve();
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.key) { S.say('The ' + (PINSW ? 'switch is off' : 'key is open') + ', so no current flows. Close it first.'); return false; }
    if (TESTER && !st.placed) { S.say('Put the sample between the probes first.'); return false; }
    if (st.insulator) { S.say('That is the insulator we tried for comparison: it is not a reading for the table. Put the sample back.'); return false; }
    if (I() <= 0) { S.say('The ammeter reads zero. Check the circuit.'); return false; }
    if (S.rows.length >= 12) { S.say('Twelve readings are plenty. Go on to the result.'); return false; }
    var row = { n: st.cells, I: +fI(I()) };
    if (!TESTER) row.V = +fV(Vb());
    S.addRow(row);
    S.say('Written in your record book: I = ' + row.I.toFixed(IDIG) + ' A' + (TESTER ? '.' : ', V = ' + row.V.toFixed(2) + ' V.'));
    return true;
  }
  function nCells() { var s = {}; S.rows.forEach(function (r) { s[r.n] = 1; }); return Object.keys(s).length; }
  var NEED = TESTER ? 3 : (NCELL > 1 ? 4 : 3);

  var steps = [
    { id: 'check', title: 'Check the circuit', view: 'circuit', render: function (u) {
        u.h2('Check the circuit');
        u.p('Everything is wired on the board. Before switching on, check it the way your teacher would.');
        u.task('1. Trace the loop', st.traced, st.traced ? 'One single loop: cell, ' + (PINSW ? 'switch' : 'key') + ', ammeter, bulb' : 'Follow the leads from the cell’s + terminal')
          .add(u.button(st.traced ? 'Traced' : 'Trace the loop', trace, !st.traced, st.traced));
        u.task('2. Check the meter zeros', st.zero, st.zero ? 'Needles rest on zero: no zero error' : 'With the circuit open the needles must rest on zero')
          .add(u.button(st.zero ? 'Checked' : 'Check the zeros', zeroCheck, !st.zero, st.zero));
        u.note('The ammeter goes in series' + (vm ? ' and the voltmeter in parallel across the bulb' : '') + ', both + terminals facing the cell’s + side.');
        u.next('Next: ' + (TESTER ? 'put the sample in' : 'close the ' + (PINSW ? 'switch' : 'key')), st.traced && st.zero);
      },
      ok: function () { return st.traced && st.zero; },
      auto: function () { trace(); zeroCheck(); return Promise.resolve(); } }];

  if (TESTER) {
    steps.push({ id: 'place', title: 'Put the sample in', view: 'tester', render: function (u) {
        u.h2('Hold the sample between the probes');
        u.p('The two probes are the ends of the circuit. Whatever you hold between them becomes part of the loop.');
        u.task('Sample in the probes', st.placed && !st.insulator, st.placed && !st.insulator ? (SAMPLE || 'The sample') + ' is in place' : 'The sample is lying beside the probes')
          .add(u.row(u.button(st.placed && !st.insulator ? 'In place' : 'Place the sample', function () { place(true); }, true, S.hand.busy || (st.placed && !st.insulator)),
            u.button('Lift it out', function () { place(false); }, false, S.hand.busy || !st.placed)));
        u.live(function () { return 'Ammeter ' + fI(I()) + ' A  ·  bulb ' + (glow() > 0.25 ? 'bright' : glow() > 0.02 ? 'dim' : 'dark'); });
        u.next('Next: close the key and read', st.placed && !st.insulator);
      },
      ok: function () { return st.placed && !st.insulator; },
      auto: function () { return place(true); } });
  }

  steps.push({ id: 'on', title: TESTER ? 'Switch on' : 'Close the ' + (PINSW ? 'switch' : 'key'), view: PINSW ? 'key' : 'bulb',
    render: function (u) {
      u.h2(PINSW ? 'Swing the safety pin across' : 'Close the key');
      u.p(PINSW ? 'The hand swings the safety pin until it rests on the second drawing pin. The metal bridges the gap, so the loop is complete.'
        : 'The hand pushes the brass plug into the key. That completes the loop and the bulb lights.');
      u.task(PINSW ? 'Switch on' : 'Insert the plug', st.key, st.key ? 'Closed: current is flowing' : 'Open')
        .add(u.row(u.button(st.key ? (PINSW ? 'Switch is on' : 'Key is in') : (PINSW ? 'Swing the pin across' : 'Insert the plug'), function () { setKey(true); }, true, st.key || S.hand.busy),
          u.button(PINSW ? 'Switch off' : 'Take the plug out', function () { setKey(false); }, false, !st.key || S.hand.busy)));
      u.live(function () { return 'Ammeter ' + fI(I()) + ' A' + (vm ? '  ·  voltmeter ' + fV(Vb()) + ' V' : '') + '  ·  bulb ' + (glow() > 0.25 ? 'bright' : glow() > 0.02 ? 'dim' : 'dark'); });
      u.note('With the circuit open the gap is air, and air does not conduct: the bulb is dark however new the cell is.');
      u.next('Next: take the readings', st.key);
    },
    ok: function () { return st.key; },
    auto: function () { return setKey(true); } });

  steps.push({ id: 'read', title: 'Take the readings', view: 'work', render: function (u) {
      u.h2(TESTER ? 'Read the current through the sample' : 'Read the ammeter and the voltmeter');
      u.p(TESTER ? 'Take three readings of the current with the sample in the probes, then try an insulator for comparison.'
        : (NCELL > 1 ? 'Read both meters with one cell and then with all ' + NCELL + ' cells in series. Take at least ' + NEED + ' readings in all.'
          : 'Take three readings and average them, as you would in a real practical.'));
      if (!TESTER && NCELL > 1) {
        u.slider('Cells in the holder', 1, NCELL, 1, function () { return st.cells; }, function (v) { st.cells = Math.round(v); }, 'cell(s)', 0);
        u.row(u.button('Set the cells', function () { setCells(st.cells); }, false, S.hand.busy));
      }
      u.row(u.button('Record this reading', function () { record(); }, true, !st.key || S.hand.busy),
        u.button(PINSW ? (st.key ? 'Switch off' : 'Switch on') : (st.key ? 'Take the plug out' : 'Insert the plug'), function () { setKey(!st.key); }, false, S.hand.busy));
      if (TESTER) u.row(u.button('Try a plastic scale instead', function () { tryInsulator(); }, false, S.hand.busy),
        u.button('Put the sample back', function () { st.insulator = false; st.placed = true; solve(); S.render(); }, false, S.hand.busy || !st.insulator));
      u.live(function () { return 'Ammeter ' + fI(I()) + ' A' + (vm ? '  ·  voltmeter ' + fV(Vb()) + ' V' : '') + '  ·  ' + st.cells + ' cell(s)'; });
      u.h3('Observation table'); u.table();
      if (S.rows.length < NEED) u.p(S.rows.length + ' of at least ' + NEED + ' readings recorded.');
      u.next('Next: the result', S.rows.length >= NEED && (TESTER || NCELL === 1 || nCells() >= 2));
    },
    ok: function () { return S.rows.length >= NEED && (TESTER || NCELL === 1 || nCells() >= 2); },
    auto: function () {
      var jobs = [];
      if (TESTER) { jobs = [function () { S.advance(0.2); record(); }, function () { S.advance(0.2); record(); }, function () { S.advance(0.2); record(); },
        function () { return tryInsulator().then(function () { st.insulator = false; solve(); }); }]; }
      else if (NCELL > 1) {
        jobs = [];
        for (var n = 1; n <= NCELL; n++) (function (nn) {
          jobs.push(function () { return setCells(nn).then(function () { S.advance(0.2); record(); record(); }); });
        })(n);
      } else { jobs = [function () { S.advance(0.2); record(); }, function () { S.advance(0.2); record(); }, function () { S.advance(0.2); record(); }]; }
      return jobs.reduce(function (pr, f) { return pr.then(f); }, st.key ? Promise.resolve() : setKey(true));
    } });

  return {
    camera: { pos: [0.0, 1.15, 1.05], look: [-0.02, 0.0, -0.3] },
    views: { cells: [[-0.5, 0.3, 0.1], [-0.6, 0.03, -0.14]], key: [[-0.26, 0.26, 0.14], [-0.3, 0.03, -0.06]],
      am: [[-0.02, 0.3, -0.04], [-0.02, 0.04, -0.34]], bulb: [[0.42, 0.26, 0.14], [0.42, 0.06, -0.12]],
      vm: [[0.42, 0.32, -0.3], [0.4, 0.04, -0.63]], tester: [[0.62, 0.26, 0.0], [0.62, 0.04, -0.3]],
      circuit: [[0.0, 1.15, 1.05], [-0.02, 0.0, -0.3]], work: [[0.1, 0.8, 0.6], [0.04, 0.0, -0.32]],
      book: [[-0.5, 0.45, 0.6], [-0.5, 0.0, 0.08]] },
    theory: TESTER ? {
      principle: 'A circuit tester is a cell and a bulb with a gap in the loop. Whatever you put in the gap becomes part of the circuit. '
        + 'A conductor lets the current through and the bulb lights; an insulator has such a large resistance that the current is far too small to be seen.',
      formula: 'I = E / (R_bulb + r + R_sample)',
      formulaNote: 'the brighter the bulb, the smaller the sample’s resistance',
      more: ['Metals conduct because some of their electrons are free to drift through the whole piece. In glass, rubber, dry wood and plastics every '
        + 'electron is held in place, so the resistance is millions of times larger and nothing visible happens.'],
      precautions: 'Touch the probes together first to prove the tester works. Hold the sample by its middle, not across the probe tips with your fingers, '
        + 'or your own hand becomes part of the circuit.' } : {
      principle: 'Current flows only round a complete loop. The cell drives it, the bulb’s thin filament resists it and glows white hot. '
        + 'The current is the same in every part of a single loop, and the potential difference across the bulb is V = I R.',
      formula: 'I = E / (R + r)',
      formulaNote: 'so the bulb’s resistance is R = V / I',
      more: [NCELL > 1 ? 'Cells joined in series, + of one to − of the next, add their emfs: ' + NCELL + ' cells give ' + fmtN(EB1 * NCELL)
        + ' V. Their internal resistances add too, so the current grows but not quite in proportion.'
        : 'Open the switch and the loop is broken by a gap of air. Air is an insulator, so the current stops at once and the bulb goes dark.'],
      precautions: 'Connections must be tight and clean, and both meter + terminals must face the cell’s + side. Never join the two ends of a cell '
        + 'straight to each other: that short circuit heats the wire and ruins the cell.' },
    book: { title: TESTER ? 'Expt. — Conductors and insulators' : PINSW ? 'Expt. — A home-made switch' : NCELL > 1 ? 'Expt. — Cells in series' : 'Expt. — A simple circuit',
      lines: ['Aim: ' + S.lab.aim].concat(TESTER ? ['Sample: ' + (SAMPLE || 'iron nail')] : [])
        .concat(['Cell: ' + fmtN(EB1) + ' V' + (NCELL > 1 ? ' × ' + NCELL : ''), 'Ammeter: 0–' + fmtN(AMAX) + ' A, read to ' + fmtN(ARES) + ' A'])
        .concat(vm ? ['Voltmeter: 0–' + fmtN(VMAX) + ' V', 'Bulb resistance R = V / I'] : ['Conductor → bulb lights', 'Insulator → bulb dark']),
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'Cells', get: function (r) { return r.n; } },
        { label: 'I (A)', get: function (r) { return r.I.toFixed(IDIG); } }].concat(TESTER ? [] : [
          { label: 'V (V)', get: function (r) { return r.V.toFixed(2); } },
          { label: 'V/I (Ω)', get: function (r) { return r.I ? (r.V / r.I).toFixed(2) : '—'; } }]) },
    graph: TESTER || NCELL === 1 ? null : { x: function (r) { return r.I; }, y: function (r) { return r.V; }, xlabel: 'I (A)', ylabel: 'V (V)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) {
      if (rows.length < NEED) return null;
      if (TESTER) {
        var mi = S.fit.mean(rows.map(function (r) { return r.I; }));
        return { label: 'Current through the sample', value: mi, unit: 'A', digits: 3, truth: p.Eb / (p.Rb + p.rint + RSAM),
          note: 'Mean of the readings with ' + (SAMPLE || 'the sample') + ' in the probes. A conductor lets nearly the short-circuit current through.' };
      }
      var R = S.fit.mean(rows.map(function (r) { return r.V / r.I; }));
      return { label: 'Resistance of the bulb', value: R, unit: 'Ω', digits: 2, truth: p.Rb,
        note: 'Mean of V / I over the readings' + (NCELL > 1 ? ': the same resistance at every number of cells.' : '.') };
    },
    tol: 0.03,
    resultNote: TESTER ? 'The insulator we tried for comparison gave no reading the ammeter could show: that is the whole difference between a conductor and an insulator.'
      : (NCELL > 1 ? 'More cells gave more current, but V / I came out the same each time: that is the bulb’s own resistance.' : ''),
    chips: ['Why does the bulb not light with the key open?', 'Why is the ammeter in series?',
      TESTER ? 'Why does an insulator keep the bulb dark?' : 'What does the voltmeter read?', 'Check my readings',
      NCELL > 1 ? 'Why is the current not exactly doubled?' : 'What is a short circuit?'],
    viva: TESTER ? [['The bulb glows dimly with a sample in place. The sample is',
      ['A conductor with a fairly large resistance', 'A perfect insulator', 'A second cell'], 0,
      'Some current passes, so it conducts; its resistance is large enough to dim the bulb.'],
    ['Why must the probes be touched together before testing?',
      ['To prove the tester itself works', 'To charge the cell', 'To clean the bulb'], 0,
      'Otherwise a dark bulb might only mean a loose lead or a dead cell.']]
      : [['Air in the gap of an open switch is',
        ['An insulator', 'A conductor', 'A cell'], 0, 'That is why breaking the loop stops the current at once.'],
      ['Two cells are joined + to +. The emf driving the bulb is',
        ['Zero', 'Double', 'Half'], 0, 'Joined that way the two emfs oppose and cancel each other.']],
    askState: function () {
      return { set_up: TESTER ? 'circuit tester' : PINSW ? 'home-made switch circuit' : 'cell and bulb circuit',
        switch_closed: st.key, cells_in_holder: st.cells, supply_V: +fmtN(EB1 * st.cells), ammeter_A: +fI(I()),
        voltmeter_V: vm ? +fV(Vb()) : null, bulb: glow() > 0.25 ? 'bright' : glow() > 0.02 ? 'dim' : 'dark',
        sample: TESTER ? (st.insulator ? 'plastic scale (insulator)' : (SAMPLE || 'iron nail')) : null,
        sample_in_probes: TESTER ? st.placed : null, ammeter_range: '0-' + fmtN(AMAX) + ' A', readings_taken: S.rows.length };
    },
    steps: steps,
    tick: function () {
      solve();
      am.set(I()); if (vm) vm.set(Vb());
      var g = glow();
      filM.emissive.setRGB(1.0 * g, 0.72 * g, 0.34 * g);
      filM.color.setRGB(0.35 + 0.5 * g, 0.29 + 0.4 * g, 0.16 + 0.2 * g);
      halo.intensity = g * 0.5;
      hudI.set(fI(I()) + ' A');
      hudV.set(vm ? fV(Vb()) + ' V' : (g > 0.25 ? 'Bright' : g > 0.02 ? 'Dim' : 'Dark'));
      hudK.set(st.key ? 'Closed' : 'Open');
    },
  };
});
