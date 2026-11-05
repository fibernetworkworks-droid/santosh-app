/* Prayogshala studio rig `flip-flops-nand`: ONE clocked digital trainer for the sequential-logic set-ups of
   app/prayog/labs/engine_ug.py - the flip-flops built from NAND gates (RS, clocked RS, D, JK, master-slave JK), the
   four-stage ripple counter and the four-bit shift register. A 5 V rail, slide switches for the data, a clock push
   button, direct set / clear buttons, lamps on the outputs, a breadboard carrying the 7400 / 7410 / 7476 / 7474
   packages, a logic probe, and (for the counter and the register) a logic analyser that draws the timing diagram.
   Physics: the lab's own kernel (eng_ff / eng_count / eng_shift in packs/engine_ug.js) stepping the real NAND
   network in gate delays, never a stored truth table. */
HoolaStudio.define('flip-flops-nand', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KN = S.lab.kernel, KK = HK.K[KN];
  function labParams() {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(KN, o);
  }
  var p = labParams();
  var FF = KN === 'eng_ff', CNT = KN === 'eng_count', SHF = KN === 'eng_shift';
  var KIND = FF ? Math.round(p.kind) : -1;
  function fmt(v, d) { return (isFinite(v) ? v : 0).toFixed(d); }

  // =============================================================================================== the lab's plan
  var CIRC = FF ? [
    { name: 'RS flip-flop of two NAND gates', ins: [['a', 'S̅'], ['b', 'R̅']], clock: false, chips: ['SN7400'],
      build: 'Two cross-coupled NAND gates. Each output feeds the other gate, so the pair remembers. The inputs are active LOW: a LOW on S̅ sets Q, a LOW on R̅ clears it.',
      eq: 'Q+ = S + R′Q   (S = NOT S̅, R = NOT R̅, not both)' },
    { name: 'clocked RS flip-flop from four NAND gates', ins: [['a', 'S'], ['b', 'R']], clock: true, chips: ['SN7400'],
      build: 'The latch of two NAND gates, with two more NAND gates that let S and R through only while the clock is HIGH.',
      eq: 'Q+ = S + R′Q   for S R = 0' },
    { name: 'gated D latch from five NAND gates', ins: [['a', 'D']], clock: true, chips: ['SN7400', 'SN7400'],
      build: 'A clocked RS latch with R = NOT D, made by a NAND gate used as an inverter, so the forbidden state cannot occur.',
      eq: 'Q+ = D' },
    { name: 'level-triggered JK flip-flop from NAND gates', ins: [['a', 'J'], ['b', 'K']], clock: true, chips: ['SN7400', 'SN7410'],
      build: 'A clocked RS latch whose gating NAND gates also take Q-bar and Q from the output, so J = K = 1 is allowed. The clock is level triggered.',
      eq: 'Q+ = J Q′ + K′Q   (J = K = 1 races around)' },
    { name: 'master-slave JK flip-flop (the circuit inside a 7476)', ins: [['a', 'J'], ['b', 'K']], clock: true, chips: ['SN7476'],
      build: 'A master latch that follows J and K while the clock is HIGH, and a slave latch, opened by the inverted clock, that copies the master when the clock falls.',
      eq: 'Q+ = J Q′ + K′Q' }
  ][KIND] : CNT ? { name: (p.down >= 0.5 ? 'four-stage ripple down counter' : 'four-stage ripple up counter') + ' of JK flip-flops',
      ins: [], clock: true, chips: ['SN7476', 'SN7476'],
      build: 'Four master-slave JK flip-flops with J = K = 1. The clock of each stage is the ' + (p.down >= 0.5 ? 'Q-bar' : 'Q') + ' of the stage before, so each stage divides the frequency by two.',
      eq: 'count = number of falling clock edges (mod 16)' }
    : { name: 'four-bit serial-in shift register of D flip-flops', ins: [['si', 'DATA']], clock: true, chips: ['SN7474', 'SN7474'],
      build: 'Four positive-edge-triggered D flip-flops on one clock, the Q of each joined to the D of the next. The data enters the first.',
      eq: 'on each rising edge: Q0 ← DATA, Q1 ← Q0, Q2 ← Q1, Q3 ← Q2' };
  var NAME = CIRC.name;
  var INS = CIRC.ins;                                           // [[key, label]]
  var NOUT = FF ? 2 : 4;
  function outKeys() { return FF ? ['Q', 'Qb'] : CNT ? ['Q3', 'Q2', 'Q1', 'Q0'] : ['Q0', 'Q1', 'Q2', 'Q3']; }
  function outLabel(k) { return k === 'Qb' ? 'Q̅' : k; }

  // the rows of the table
  var COMBOS = [];                                              // FF only
  if (FF) {
    var a, b, q0;
    for (a = 0; a < 2; a++) for (b = 0; b < 2; b++) for (q0 = 0; q0 < 2; q0++) {
      if (KIND === 2 && b === 1) continue;
      COMBOS.push({ a: a, b: b, q0: q0, idx: (a * 4 + b * 2 + q0), valid: KK.valid(KIND, a, b) });
    }
  }
  var VALID = COMBOS.filter(function (c) { return c.valid; });
  var SIG_TRUTH = FF ? KK.measure(p).sig : CNT ? KK.measure(p).sum : KK.measure(p).word;

  // =============================================================================================== the state
  var ks = KK.init(p);                                          // the kernel's wires
  var st = { power: false, checked: false, a: KIND === 0 ? 1 : 0, b: KIND === 0 ? 1 : 0, si: 0, q0: 0, pulses: 0, last: null, hist: [], lastClock: null };
  function kp() { var q = assign(p, {}); if (FF) { q.a = st.a; q.b = st.b; } return q; }
  function view() { return KK.view(ks, kp()); }
  function qNow() { return ks.sig.Q; }

  // ---------- trainer case with a printed panel
  var TW = 0.62, TD = 0.26, TH = 0.055;
  var tr = new T.Group(); S.scene.add(tr); tr.position.set(0, 0, -0.1);
  var caseM = new T.MeshStandardMaterial({ color: 0x2f343c, roughness: 0.5, metalness: 0.1 });
  var tcase = S.rounded(TW, TD, TH, 0.012, caseM); tcase.rotation.x = -Math.PI / 2; tcase.position.y = TH / 2 + 0.003; tr.add(tcase);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.01, 0.011, 0.004, 14), M.rubber); ft.position.set(f[0] * (TW / 2 - 0.03), 0.002, f[1] * (TD / 2 - 0.03)); tr.add(ft); });
  var SWX = INS.length === 1 ? [-0.2] : [-0.22, -0.17];
  var CLKX = -0.08, CLRX = -0.02, PREX = 0.03;
  var LEDX = NOUT === 2 ? [0.2, 0.25] : [0.12, 0.17, 0.22, 0.27];
  var panelTex = S.canvasTex(1800, Math.round(1800 * (TD - 0.02) / (TW - 0.02)), function (x, w, h) {
    var X = function (u) { return (u / (TW - 0.02) + 0.5) * w; }, Y = function (zz) { return (zz / (TD - 0.02) + 0.5) * h; };
    x.fillStyle = '#242830'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 4; x.strokeRect(14, 14, w - 28, h - 28);
    x.fillStyle = '#f1efe8'; x.font = '700 44px "Public Sans", sans-serif'; x.fillText('DIGITAL LOGIC TRAINER', 44, 74);
    x.font = '500 28px "Public Sans", sans-serif'; x.fillStyle = '#b9c0cb';
    x.fillText('+5 V regulated  ·  TTL levels: LOW below 0.8 V, HIGH above 2 V', 44, 116);
    x.fillStyle = '#b8322a'; x.fillRect(X(-0.26), Y(-0.055) - 8, X(0.26) - X(-0.26), 16);
    x.fillStyle = '#f1efe8'; x.font = '700 30px "Public Sans", sans-serif'; x.fillText('+5 V', X(-0.295), Y(-0.045));
    x.fillStyle = '#2c5fb4'; x.fillRect(X(-0.26), Y(-0.02) - 8, X(0.26) - X(-0.26), 16);
    x.fillStyle = '#f1efe8'; x.fillText('GND', X(-0.3), Y(-0.01));
    x.textAlign = 'center';
    if (INS.length) { x.font = '700 34px "Public Sans", sans-serif'; x.fillText('DATA SWITCHES', X(SWX.length === 2 ? -0.195 : -0.2), Y(0.105)); }
    INS.forEach(function (k, i) { x.font = '700 38px "Public Sans", sans-serif'; x.fillText(k[1], X(SWX[i]), Y(0.025)); });
    if (CIRC.clock) { x.font = '700 34px "Public Sans", sans-serif'; x.fillText('CLOCK', X(CLKX), Y(0.105)); x.fillText('CLEAR', X(CLRX), Y(0.105));
      if (FF) x.fillText('PRESET', X(PREX), Y(0.105)); }
    else { x.font = '700 34px "Public Sans", sans-serif'; x.fillText('CLEAR', X(CLRX), Y(0.105)); x.fillText('PRESET', X(PREX), Y(0.105)); }
    x.font = '700 34px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8'; x.fillText('OUTPUT LAMPS', X((LEDX[0] + LEDX[LEDX.length - 1]) / 2), Y(0.105));
    outKeys().forEach(function (k, i) { x.font = '700 36px "Public Sans", sans-serif'; x.fillText(outLabel(k), X(LEDX[i]), Y(0.025)); });
    x.font = '600 26px "Public Sans", sans-serif'; x.fillStyle = '#b9c0cb'; x.fillText('POWER', X(0.095), Y(0.105));
    x.textAlign = 'left';
  });
  var pf = new T.Mesh(new T.PlaneGeometry(TW - 0.02, TD - 0.02), new T.MeshStandardMaterial({ map: panelTex, roughness: 0.55 }));
  pf.rotation.x = -Math.PI / 2; pf.position.set(0, TH + 0.0038, -0.1); S.scene.add(pf);
  S.contact(TW + 0.1, TD + 0.1, 0, -0.1, 0.55);
  function tp(u, zz) { return new T.Vector3(u, TH + 0.004, -0.1 + zz); }

  // ---------- slide switches
  var switches = INS.map(function (k, i) {
    var g = new T.Group(); S.scene.add(g); g.position.copy(tp(SWX[i], 0.065));
    var frame = S.rounded(0.014, 0.024, 0.006, 0.002, new T.MeshStandardMaterial({ color: 0x15171b, roughness: 0.5 })); frame.rotation.x = -Math.PI / 2; frame.position.y = 0.003; g.add(frame);
    var lever = S.mesh(new T.BoxGeometry(0.008, 0.006, 0.009), new T.MeshStandardMaterial({ color: 0xe8e4d8, roughness: 0.5 })); lever.position.set(0, 0.008, 0.006); g.add(lever);
    g.userData = { lever: lever, key: k[0] };
    return g;
  });
  function setSwitchLook() { switches.forEach(function (g) { g.userData.lever.position.z = st[g.userData.key] ? -0.006 : 0.006; }); }
  setSwitchLook();
  // ---------- push buttons: clock, clear, preset
  function pushButton(x, color) {
    var g = new T.Group(); S.scene.add(g); g.position.copy(tp(x, 0.065));
    var ring = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.004, 24), M.chrome); ring.position.y = 0.002; g.add(ring);
    var cap = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, 0.008, 24), new T.MeshStandardMaterial({ color: color, roughness: 0.4 })); cap.position.y = 0.007; g.add(cap);
    g.userData.cap = cap; return g;
  }
  var btnClk = CIRC.clock ? pushButton(CLKX, 0xc23b30) : null;
  var btnClr = pushButton(CLRX, 0x2c5fb4);
  var btnPre = FF ? pushButton(PREX, 0x3a8a4a) : null;
  function press(b) { if (!b) return Promise.resolve(); b.userData.cap.position.y = 0.0045; return new Promise(function (r) { setTimeout(function () { b.userData.cap.position.y = 0.007; r(); }, S.fast ? 0 : 160); }); }

  // ---------- output lamps
  var leds = outKeys().map(function (k, i) {
    var g = new T.Group(); S.scene.add(g); g.position.copy(tp(LEDX[i], 0.065));
    var mat = new T.MeshStandardMaterial({ color: 0x4a1210, roughness: 0.25, emissive: 0x000000, transparent: true, opacity: 0.9 });
    var dome = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.006, 22), mat); dome.position.y = 0.003; g.add(dome);
    var tip = S.mesh(new T.SphereGeometry(0.0045, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), mat); tip.position.y = 0.006; g.add(tip);
    var ring = S.mesh(new T.TorusGeometry(0.0055, 0.0011, 8, 22), M.chrome); ring.rotation.x = Math.PI / 2; ring.position.y = 0.0012; g.add(ring);
    g.userData = { mat: mat, key: k }; return g;
  });
  // ---------- power rocker and pilot
  var rocker = S.rounded(0.018, 0.012, 0.008, 0.003, M.bakelite); rocker.position.copy(tp(0.095, 0.065)); rocker.position.y += 0.004; S.scene.add(rocker);
  var pilotM = new T.MeshStandardMaterial({ color: 0x14401c, roughness: 0.3 });
  var pilot = S.mesh(new T.SphereGeometry(0.005, 18, 12, 0, Math.PI * 2, 0, Math.PI / 2), pilotM); pilot.position.copy(tp(0.13, 0.065)); S.scene.add(pilot);
  function setPowerLook() { rocker.rotation.x = st.power ? -0.3 : 0.3; pilotM.color.setHex(st.power ? 0x3ae05a : 0x14401c); pilotM.emissive.setHex(st.power ? 0x2ad04a : 0x000000); pilotM.emissiveIntensity = st.power ? 2.0 : 0; }
  setPowerLook();

  // ---------- breadboard with the packages
  var BW = 0.34, BD = 0.1, BT = 0.01, BZ = 0.13;
  var bbTex = S.canvasTex(1400, 420, function (x, w, h) {
    x.fillStyle = '#efece2'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(0,0,0,.12)'; x.lineWidth = 2; x.strokeRect(6, 6, w - 12, h - 12); x.fillStyle = '#7d7668';
    var i, j, y; for (i = 0; i < 56; i++) for (j = 0; j < 10; j++) { y = 60 + j * 26 + (j >= 5 ? 50 : 0); x.fillRect(66 + i * 21, y, 7, 7); }
    x.fillStyle = '#d7d2c4'; x.fillRect(50, 60 + 5 * 26 + 2, w - 100, 44); });
  var bb = S.rounded(BW, BD, BT, 0.004, new T.MeshStandardMaterial({ color: 0xefece2, roughness: 0.6 })); bb.rotation.x = -Math.PI / 2; bb.position.set(0, BT / 2, BZ); S.scene.add(bb);
  var bbTop = new T.Mesh(new T.PlaneGeometry(BW - 0.004, BD - 0.004), new T.MeshStandardMaterial({ map: bbTex, roughness: 0.65 })); bbTop.rotation.x = -Math.PI / 2; bbTop.position.set(0, BT + 0.0004, BZ); S.scene.add(bbTop);
  S.contact(BW + 0.08, BD + 0.06, 0, BZ, 0.5);
  var chips = new T.Group(); S.scene.add(chips);
  CIRC.chips.forEach(function (nm, ci) {
    var tex = S.canvasTex(600, 240, function (x, w, h) { x.fillStyle = '#15161a'; x.fillRect(0, 0, w, h); x.fillStyle = '#9ba1a9'; x.font = '700 58px "Public Sans", sans-serif'; x.fillText(nm + 'N', 40, 100);
      x.font = '600 38px "Public Sans", sans-serif'; x.fillText({ SN7400: 'QUAD 2-NAND', SN7410: 'TRIPLE 3-NAND', SN7476: 'DUAL J-K M/S', SN7474: 'DUAL D EDGE' }[nm], 40, 168); });
    var g = new T.Group(); chips.add(g); g.position.set(-0.1 + ci * 0.1, BT + 0.0018, BZ);
    var dipM = [0, 1, 2, 3, 4, 5].map(function (i) { return i === 2 ? new T.MeshStandardMaterial({ map: tex, roughness: 0.42 }) : new T.MeshStandardMaterial({ color: 0x15161a, roughness: 0.42 }); });
    var dip = S.mesh(new T.BoxGeometry(0.019, 0.0036, 0.0068), dipM); dip.position.y = 0.0018; g.add(dip);
    var pi, sg; for (pi = 0; pi < 7; pi++) for (sg = -1; sg <= 1; sg += 2) { var pin = S.mesh(new T.BoxGeometry(0.0006, 0.004, 0.0003), M.chrome, false); pin.position.set(-0.0076 + pi * 0.00254, -0.0012, sg * 0.0038); g.add(pin); }
  });
  INS.forEach(function (k, i) { S.wire([[SWX[i], TH + 0.006, -0.1 + 0.075], [SWX[i] - 0.01, 0.03, 0.03], [-0.12 + i * 0.02, BT + 0.004, BZ - BD / 2 + 0.006]], 'yellow'); });
  if (CIRC.clock) S.wire([[CLKX, TH + 0.006, -0.1 + 0.075], [CLKX - 0.01, 0.03, 0.03], [-0.06, BT + 0.004, BZ - BD / 2 + 0.006]], 'red');
  outKeys().forEach(function (k, i) { S.wire([[0.04 + i * 0.02, BT + 0.004, BZ - BD / 2 + 0.006], [LEDX[i] - 0.02, 0.03, 0.03], [LEDX[i], TH + 0.006, -0.1 + 0.075]], 'blue'); });
  S.wire([[-0.24, TH + 0.005, -0.155], [-0.2, 0.03, 0.02], [-0.14, BT + 0.004, BZ + BD / 2 - 0.006]], 'red');
  S.wire([[-0.24, TH + 0.005, -0.12], [-0.18, 0.025, 0.04], [0.14, BT + 0.004, BZ + BD / 2 - 0.006]], 'black');
  // ---------- logic probe
  var probe = new T.Group(); S.scene.add(probe); probe.position.set(0.3, 0, 0.1); probe.rotation.y = -0.4;
  var pbody = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.12, 20), new T.MeshStandardMaterial({ color: 0xd9682a, roughness: 0.5 })); pbody.rotation.z = Math.PI / 2; pbody.position.y = 0.009; probe.add(pbody);
  var ptip = S.mesh(new T.ConeGeometry(0.0035, 0.025, 16), M.chrome); ptip.rotation.z = -Math.PI / 2; ptip.position.set(0.072, 0.009, 0); probe.add(ptip);
  var plampM = new T.MeshStandardMaterial({ color: 0x4a1210, roughness: 0.3 }); var plamp = S.mesh(new T.SphereGeometry(0.004, 16, 10), plampM); plamp.position.set(-0.03, 0.016, 0); probe.add(plamp);
  S.contact(0.17, 0.08, 0.3, 0.1, 0.45);

  // ---------- logic analyser (timing diagram) for the counter and the register
  var an = null, anTex = null;
  if (CNT || SHF) {
    an = new T.Group(); S.scene.add(an); an.position.set(0.0, 0, -0.34);
    var abody = S.rounded(0.46, 0.2, 0.03, 0.01, new T.MeshStandardMaterial({ color: 0x23272e, roughness: 0.5 })); abody.position.y = 0.1; an.add(abody);
    anTex = S.liveTex(920, 380);
    var ascr = new T.Mesh(new T.PlaneGeometry(0.42, 0.17), new T.MeshBasicMaterial({ map: anTex, toneMapped: false })); ascr.position.set(0, 0.1, 0.0158); an.add(ascr);
    an.rotation.x = -0.12; S.contact(0.56, 0.1, 0, -0.34, 0.5);
  }
  var anKey = '';
  function drawAnalyser() {
    if (!anTex) return;
    var key = st.hist.length + '|' + st.power; if (key === anKey) return; anKey = key;
    var names = CNT ? ['CLK', 'Q0', 'Q1', 'Q2', 'Q3'] : ['CLK', 'DATA', 'Q0', 'Q1', 'Q2', 'Q3'];
    anTex.draw(function (x, w, h) {
      x.fillStyle = '#0b1a12'; x.fillRect(0, 0, w, h);
      if (!st.power) { x.fillStyle = '#2f5a3e'; x.font = '600 28px "Public Sans", sans-serif'; x.fillText('LOGIC ANALYSER  ·  OFF', 30, 60); return; }
      var L = 90, R = w - 20, rowH = (h - 40) / names.length, nP = Math.max(8, Math.min(16, st.hist.length)), W = (R - L) / Math.max(nP, 1), i, j;
      x.strokeStyle = 'rgba(80,200,120,.18)'; x.lineWidth = 1;
      for (j = 0; j <= nP; j++) { x.beginPath(); x.moveTo(L + j * W, 20); x.lineTo(L + j * W, h - 20); x.stroke(); }
      names.forEach(function (nm, r) {
        var y0 = 28 + r * rowH, yh = y0 + 8, yl = y0 + rowH - 14;
        x.fillStyle = '#9fe2b4'; x.font = '600 24px "JetBrains Mono", monospace'; x.fillText(nm, 12, y0 + rowH / 2 + 6);
        x.strokeStyle = r === 0 ? '#ffd24a' : '#5bf08c'; x.lineWidth = 2.5; x.beginPath();
        var started = false;
        st.hist.slice(-16).forEach(function (hh, k) {
          var xs = L + k * W;
          function lvl(sig) { return sig ? yh : yl; }
          var tpts = hh.tracks[nm]; if (!tpts) return;
          tpts.forEach(function (pt) { var xx = xs + pt[0] * W; if (!started) { x.moveTo(xx, lvl(pt[1])); started = true; } else { x.lineTo(xx, lvl(pt[2])); x.lineTo(xx, lvl(pt[1])); } });
        });
        x.stroke();
      });
    });
  }
  // a pulse's wave-form: [[x in 0..1, level, previous level]] for each trace
  function tracksFor(startWord, startSi, events, tw, tl, endWord) {
    var tr2 = {}, tot = tw + tl;
    function bitOf(wd, k) { return (wd >> k) & 1; }
    tr2.CLK = [[0, 1, 0], [tw / tot, 0, 1]];
    if (CNT) { for (var k = 0; k < 4; k++) { var lv = bitOf(startWord, k), arr = [[0, lv, lv]];
        events.forEach(function (e) { var nb = bitOf(e[1], k); if (nb !== lv) { arr.push([e[0] / tot, nb, lv]); lv = nb; } }); tr2['Q' + k] = arr; } }
    else { tr2.DATA = [[0, startSi, startSi]]; for (var k2 = 0; k2 < 4; k2++) { var a0 = bitOf(startWord, k2), b0 = bitOf(endWord, k2); tr2['Q' + k2] = b0 === a0 ? [[0, a0, a0]] : [[0.05, b0, a0]]; } }
    return tr2;
  }

  S.addApparatus('tr', tr, 'Digital logic trainer', 'A 5 volt regulated rail, slide switches that put a clean HIGH or LOW on each input, a clock push button, and lamps on the outputs. TTL reads below 0.8 V as LOW and above 2 V as HIGH.');
  S.addApparatus('bb', bb, 'Solderless breadboard', 'The packages straddle the central channel and the jumper wires make the circuit.');
  S.addApparatus('chips', chips, CIRC.chips.join(' + '), CIRC.build);
  if (switches[0]) S.addApparatus('sw', switches[0], 'Data switch ' + INS[0][1], 'Up is HIGH (+5 V), down is LOW (ground). The hand flips it.');
  if (btnClk) S.addApparatus('clk', btnClk, 'Clock push button', 'One press gives one clean clock pulse: HIGH, then LOW again. A debounced button is needed, because a bouncing switch would give several pulses.');
  S.addApparatus('led', leds[0], 'Output lamp', 'Lit means the output is HIGH.');
  if (an) S.addApparatus('an', an, 'Logic analyser', 'It draws the clock and every output against time, one clock pulse per column: the timing diagram.');
  S.addApparatus('probe', probe, 'Logic probe', 'Touch it on any pin to see whether that node is HIGH or LOW.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every row you take is written here, as in a real practical file.');
  var hudIn = S.hudCard('Inputs'), hudOut = S.hudCard('Outputs'), hudRow = S.hudCard('Rows');

  // =============================================================================================== human actions
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function needPower() { if (!st.power) { S.say('Switch the trainer on first.'); return true; } return false; }
  function toggleTrainer(on) {
    if (busy()) return Promise.resolve();
    if (on === st.power) return Promise.resolve();
    return S.hand.tap(rocker, 'front').then(function () { st.power = on; setPowerLook(); S.click(900, 0.05); S.say(on ? 'Trainer on: the green pilot is lit and the rail is at 5 volts.' : 'Trainer off.'); S.render(); });
  }
  function applyIn() { if (FF && KIND !== 0) KK.drive(ks, kp(), st.a, st.b); if (SHF) KK.drive(ks, kp(), st.si); }
  function flip(key, v) {
    if (busy() || needPower()) return Promise.resolve();
    if (st[key] === v) return Promise.resolve();
    var g = switches.filter(function (s) { return s.userData.key === key; })[0];
    return S.hand.tap(g ? g.userData.lever : rocker, 'front').then(function () { st[key] = v; setSwitchLook(); applyIn(); S.click(1400, 0.03); S.render(); });
  }
  function setStored(q) {                                       // the direct set / clear line (not a clock pulse)
    if (busy() || needPower()) return Promise.resolve();
    var b = q ? btnPre : btnClr;
    return S.hand.tap(b || btnClr, 'front').then(function () { return press(b); }).then(function () {
      if (FF) { KK.force(ks, kp(), q); }
      else { if (CNT) KK.reset(ks, kp()); else { ks = KK.init(kp()); KK.drive(ks, kp(), st.si); } st.hist = []; st.pulses = 0; while (S.rows.length) S.rows.pop(); S.book.draw(); }
      st.q0 = q; st.last = null; pending = null; S.say(FF ? (q ? 'Stored bit set: Q = 1.' : 'Stored bit cleared: Q = 0.') : 'Cleared: every output is 0.'); S.render();
    });
  }
  var pending = null;                                           // the stored bit and inputs just before a pulse
  function pulse() {
    if (busy() || needPower()) return Promise.resolve(false);
    var before = { q: qNow(), a: st.a, b: st.b, si: st.si, word: CNT ? KK.view(ks, kp()).word : SHF ? KK.view(ks, kp()).word_out : 0 };
    return S.hand.tap(btnClk, 'front').then(function () { return press(btnClk); }).then(function () {
      var r = KK.clock(ks, kp()); S.click(1700, 0.04);
      pending = before; st.pulses += 1; st.last = r;
      if (CNT) { var v = KK.view(ks, kp()); st.hist.push({ n: st.pulses, tracks: tracksFor(before.word, 0, ks.events, Math.round(p.tw), Math.round(p.tl), v.word) }); }
      if (SHF) { var v2 = KK.view(ks, kp()); st.hist.push({ n: st.pulses, tracks: tracksFor(before.word, before.si, [], Math.round(p.tw), Math.round(p.tw), v2.word_out) }); }
      S.render(); return true;
    });
  }
  function applyRS(a, b, q0) {                                  // kind 0: hold, then the inputs
    var q = kp(); q.q0 = q0; ks = KK.init(q);                    // the latch holding q0 with both inputs HIGH
    var before = qNow();
    st.a = a; st.b = b; KK.drive(ks, kp(), a, b); setSwitchLook(); pending = { q: before, a: a, b: b }; S.render();
  }
  function record() {
    if (busy() || needPower()) return false;
    if (FF) {
      if (!pending) { S.say(KIND === 0 ? 'Set the inputs first.' : 'Press the clock first, then record the new Q.'); return false; }
      var c = pending, valid = KK.valid(KIND, c.a, c.b);
      if (!valid) { S.say(KIND === 0 ? 'S̅ = R̅ = 0 is not allowed: both outputs go HIGH.' : KIND === 1 ? 'S = R = 1 is not allowed: the result depends on gate timing.' : 'J = K = 1 races around in a level-triggered circuit: the result is not defined.'); return false; }
      var already = S.rows.some(function (r) { return r.a === c.a && r.b === c.b && r.q0 === c.q; });
      if (already) { S.say('That row is already in your record book.'); return false; }
      S.addRow({ a: c.a, b: c.b, q0: c.q, q: qNow(), idx: c.a * 4 + c.b * 2 + c.q }); pending = null;
      S.say('Row written: ' + INS.map(function (k) { return k[1] + ' = ' + (k[0] === 'a' ? c.a : c.b); }).join(', ') + ', Q before = ' + c.q + ', Q after = ' + qNow() + '.'); return true;
    }
    if (CNT) {
      if (!st.last) { S.say('Press the clock first.'); return false; }
      if (S.rows.some(function (r) { return r.n === st.pulses; })) { S.say('Pulse ' + st.pulses + ' is already written.'); return false; }
      var vv = KK.view(ks, kp()); S.addRow({ n: st.pulses, word: vv.word, Q0: vv.Q0, Q1: vv.Q1, Q2: vv.Q2, Q3: vv.Q3, glitch: vv.glitch }); return true;
    }
    if (!st.last) { S.say('Press the clock first.'); return false; }
    if (S.rows.some(function (r) { return r.n === st.pulses; })) { S.say('Pulse ' + st.pulses + ' is already written.'); return false; }
    var vs = KK.view(ks, kp()); S.addRow({ n: st.pulses, si: pending ? pending.si : st.si, word: vs.word_out, Q0: vs.Q0, Q1: vs.Q1, Q2: vs.Q2, Q3: vs.Q3 }); return true;
  }
  function doRow(c) {                                           // FF: bring the circuit to one row of the table, pulse, record
    return setStored(c.q0).then(function () { return flip('a', c.a); }).then(function () { return flip('b', c.b); }).then(function () {
      if (KIND === 0) { applyRS(c.a, c.b, c.q0); return press(btnClr); }
      return pulse(); }).then(function () { return c.valid ? record() : false; });
  }
  function nextRow() { for (var i = 0; i < COMBOS.length; i++) { var c = COMBOS[i]; if (!S.rows.some(function (r) { return r.a === c.a && r.b === c.b && r.q0 === c.q0; })) return c; } return null; }
  function enough() { return FF ? VALID.every(function (c) { return S.rows.some(function (r) { return r.a === c.a && r.b === c.b && r.q0 === c.q0; }); }) : CNT ? S.rows.length >= 16 : S.rows.length >= 4; }

  function wordNow() { return CNT ? KK.view(ks, kp()).word : SHF ? KK.view(ks, kp()).word_out : 0; }
  function bits4(w) { return [(w >> 3) & 1, (w >> 2) & 1, (w >> 1) & 1, w & 1].join(''); }

  // =============================================================================================== the rig
  drawAnalyser();
  var steps = [];
  steps.push({ id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
      u.h2('Wire the circuit and switch the trainer on');
      u.p(CIRC.chips.join(' and ') + ' on the breadboard. ' + CIRC.build);
      u.p('Pin 14 (or 16) of every package goes to the +5 V rail and the ground pin to ground. The data comes from the trainer’s slide switches' + (CIRC.clock ? ', the clock from its push button,' : '') + ' and the outputs go to its lamps.');
      u.task('1. Check the supply pins and the wiring', st.checked, st.checked ? 'Supply pins on the red and blue rails' : 'Look over the board')
        .add(u.button(st.checked ? 'Checked' : 'Check the wiring', function () { st.checked = true; S.focus('chips'); S.say('The supply pins of each package are on the red and blue rails. ' + CIRC.build); S.render(); }, !st.checked, st.checked));
      u.task('2. Switch the trainer on', st.power, st.power ? 'The green pilot is lit' : 'The hand presses the rocker')
        .add(u.button(st.power ? 'Switch off' : 'Switch on the trainer', function () { S.focus('tr'); toggleTrainer(!st.power); }, !st.power, S.hand.busy));
      u.note('Wire a logic circuit with the power off. Never join two outputs together, and never wire an output straight to the supply rail.');
      u.next('Next: take the table', st.checked && st.power);
    },
    ok: function () { return st.checked && st.power; },
    auto: function () { st.checked = true; return toggleTrainer(true); } });

  if (FF) {
    steps.push({ id: 'table', title: 'Characteristic table', view: 'tr', render: function (u) {
        u.h2('Take every row of the table');
        u.p(KIND === 0 ? 'Set the stored bit with PRESET or CLEAR, set the two inputs, and read the lamps. S̅ and R̅ are active LOW.' :
          'Set the stored bit with PRESET or CLEAR, set the data inputs with the switches, press the clock once, and read Q. Record every row that is allowed.');
        u.row(u.button('Stored bit = 0', function () { setStored(0); }, false, S.hand.busy), u.button('Stored bit = 1', function () { setStored(1); }, false, S.hand.busy));
        INS.forEach(function (k) {
          var key = k[0];
          u.row(u.button(k[1] + ' = ' + st[key] + '   (flip)', function () { flip(key, 1 - st[key]); }, false, S.hand.busy));
        });
        u.row(u.button(KIND === 0 ? 'Apply the inputs' : 'Press the clock', function () { if (KIND === 0) { if (!needPower() && !busy()) { applyRS(st.a, st.b, st.q0); } } else pulse(); }, true, S.hand.busy),
          u.button('Record this row', function () { record(); S.render(); }, false, S.hand.busy));
        u.live(function () { var v = view(); return INS.map(function (k) { return k[1] + '=' + st[k[0]]; }).join(' ') + '   Q=' + (st.power ? v.Q : '—') + '  Q̅=' + (st.power ? v.Qb : '—') + (v.osc ? '   (the outputs are not settling)' : '') + (KIND === 3 && st.last ? '   Q flipped ' + st.last.toggles + ' times while the clock was high' : ''); });
        if (KIND === 3) u.note('With J = K = 1 the level-triggered circuit flips over and over while the clock is HIGH (race-around). That row is not written down: use the master-slave circuit instead.');
        u.h3('Characteristic table'); u.table();
        u.p(VALID.filter(function (c) { return S.rows.some(function (r) { return r.a === c.a && r.b === c.b && r.q0 === c.q0; }); }).length + ' of ' + VALID.length + ' allowed rows recorded.');
        u.next('Next: check the table', enough());
      },
      ok: enough,
      auto: function () {
        return COMBOS.reduce(function (pr, c) { return pr.then(function () { return doRow(c); }); }, Promise.resolve()).then(function () {
          if (KIND === 3) { return setStored(0).then(function () { return flip('a', 1); }).then(function () { return flip('b', 1); }).then(function () { return pulse(); }); }
        });
      } });
  } else if (CNT) {
    steps.push({ id: 'count', title: 'Count the pulses', view: 'tr', render: function (u) {
        u.h2('Count sixteen clock pulses');
        u.p('Clear the counter, then press the clock one pulse at a time and write down the four lamps after each pulse. Watch the lamps closely at 7 → 8 and look at the timing diagram.');
        u.row(u.button('Clear the counter', function () { setStored(0); }, false, S.hand.busy), u.button('Press the clock', function () { pulse(); }, true, S.hand.busy), u.button('Record the lamps', function () { record(); S.render(); }, false, S.hand.busy));
        u.live(function () { var v = view(); return 'Lamps Q3 Q2 Q1 Q0 = ' + (st.power ? bits4(v.word) + '  (count ' + v.word + ')' : '—') + (st.last ? '   output changes after the last pulse: ' + v.ripple + (v.glitch ? ', wrong counts shown on the way: ' + v.glitch : '') : ''); });
        u.row(u.button('Look at the timing diagram', function () { S.focus('an'); }));
        u.h3('Count table'); u.table();
        u.p(S.rows.length + ' of 16 pulses written.');
        u.next('Next: result', enough());
      },
      ok: enough,
      auto: function () {
        var seq = Promise.resolve();
        for (var i = 0; i < 16; i++) seq = seq.then(function () { return pulse(); }).then(function () { return record(); });
        return seq;
      } });
  } else {
    steps.push({ id: 'shift', title: 'Load the word', view: 'tr', render: function (u) {
        var w = Math.round(p.word) & 15;
        u.h2('Load the word ' + bits4(w) + ' serially');
        u.p('Put the most significant bit on the DATA switch, press the clock, then the next bit, and so on: four pulses. After the fourth the first bit has moved to Q3. Write down the lamps after each pulse.');
        u.row(u.button('Clear the register', function () { setStored(0); }, false, S.hand.busy), u.button('DATA = ' + st.si + '  (flip)', function () { flip('si', 1 - st.si); }, false, S.hand.busy));
        u.row(u.button('Press the clock', function () { pulse(); }, true, S.hand.busy), u.button('Record the lamps', function () { record(); S.render(); }, false, S.hand.busy));
        u.live(function () { var v = view(); return 'DATA=' + st.si + '   Q0 Q1 Q2 Q3 = ' + (st.power ? [v.Q0, v.Q1, v.Q2, v.Q3].join(' ') : '—') + '   pulses ' + st.pulses; });
        u.h3('Register table'); u.table();
        u.next('Next: result', enough());
      },
      ok: enough,
      auto: function () {
        var w = Math.round(p.word) & 15, seq = setStored(0);
        for (var i = 0; i < 4; i++) (function (bit) { seq = seq.then(function () { return flip('si', bit); }).then(function () { return pulse(); }).then(function () { return record(); }); })((w >> (3 - i)) & 1);
        return seq;
      } });
  }

  function resultOf(rows) {
    if (FF) {
      var tot = 0, i, c, r;
      for (i = 0; i < COMBOS.length; i++) { c = COMBOS[i]; if (!c.valid) continue; r = rows.filter(function (x) { return x.a === c.a && x.b === c.b && x.q0 === c.q0; })[0]; if (!r) return null; tot += (r.q ? 1 : 0) * Math.pow(2, c.idx); }
      return { label: 'Characteristic table read as a binary number', value: tot, unit: '', digits: 0, truth: SIG_TRUTH, note: 'Each allowed row (S or J, R or K, stored bit) counts its new Q as one binary digit. The characteristic equation ' + CIRC.eq + ' gives the same number.' };
    }
    if (CNT) {
      if (rows.length < 16) return null;
      var s = 0, k; for (k = 0; k < 16; k++) { var rr = rows.filter(function (x) { return x.n === k + 1; })[0]; if (!rr) return null; s += (k + 1) * rr.word; }
      return { label: 'Sum of pulse number × count', value: s, unit: '', digits: 0, truth: SIG_TRUTH, note: 'It checks every one of the sixteen counts at once. The right sequence gives the same number every time.' };
    }
    if (rows.length < 4) return null;
    return { label: 'Word held after four pulses', value: rows[rows.length - 1].word, unit: '', digits: 0, truth: SIG_TRUTH, note: 'Q0 + 2 Q1 + 4 Q2 + 8 Q3 read from the lamps after the fourth pulse; it must equal the word that was fed in.' };
  }

  var bookCols = FF ? [{ label: 'S.No', get: function (r, i) { return i + 1; } }]
      .concat(INS.map(function (k) { return { label: k[1], get: function (r) { return String(r[k[0]]); } }; }))
      .concat([{ label: 'Q before', get: function (r) { return String(r.q0); } }, { label: 'Q after', get: function (r) { return String(r.q); } }])
    : CNT ? [{ label: 'Pulse', get: function (r) { return r.n; } }, { label: 'Q3 Q2 Q1 Q0', get: function (r) { return bits4(r.word); } }, { label: 'Count', get: function (r) { return r.word; } },
        { label: 'Wrong counts on the way', get: function (r) { return r.glitch; } }]
    : [{ label: 'Pulse', get: function (r) { return r.n; } }, { label: 'DATA in', get: function (r) { return r.si; } }, { label: 'Q0 Q1 Q2 Q3', get: function (r) { return [r.Q0, r.Q1, r.Q2, r.Q3].join(' '); } },
        { label: 'Word', get: function (r) { return r.word; } }];

  var VIVA = FF ? (KIND === 4 ? [['In a master-slave JK flip-flop the output changes', ['when the clock falls', 'while the clock is high', 'when J changes'], 0, 'The slave latch opens only when the clock goes low.'],
      ['J = K = 1 and one clock pulse give', ['Q toggled once', 'Q set to 1', 'Q reset to 0'], 0, 'Q+ = Q-bar for J = K = 1.']]
    : KIND === 3 ? [['With J = K = 1 and the clock held HIGH for long, a level-triggered JK flip-flop', ['flips over and over', 'holds Q', 'sets Q'], 0, 'The outputs feed back to the inputs while the gates are open: race-around.'],
      ['The master-slave circuit cures the race-around because', ['the slave is shut while the master is open', 'it uses faster gates', 'it has no feedback'], 0, 'The outputs cannot change until the master has closed.']]
    : KIND === 2 ? [['A gated D latch can never be in a forbidden state because', ['R is always the complement of S', 'it has no clock', 'it uses a NOR gate'], 0, 'R = NOT D.'],
      ['While the clock is HIGH, the output of a D latch', ['follows D', 'holds its value', 'toggles'], 0, 'The latch is transparent while the clock is HIGH.']]
    : KIND === 1 ? [['In the clocked RS flip-flop, S = 0 and R = 0 with a clock pulse', ['leaves Q unchanged', 'sets Q', 'resets Q'], 0, 'Both gating gates output 1, which the latch holds.'],
      ['Why is S = R = 1 forbidden?', ['The outcome depends on gate timing', 'It draws too much current', 'It sets Q twice'], 0, 'Both outputs go HIGH and the final state is undefined.']]
    : [['A NAND-gate RS latch has inputs that are', ['active LOW', 'active HIGH', 'edge triggered'], 0, 'A LOW on an input forces the NAND output HIGH.'],
      ['Which input combination must be avoided in the NAND latch?', ['both LOW', 'both HIGH', 'S̅ LOW and R̅ HIGH'], 0, 'Both outputs go HIGH and release in an unpredictable way.']])
    : CNT ? [['Q0 of a 4-bit ripple counter has a frequency of', ['half the clock', 'a quarter of the clock', 'the clock'], 0, 'Each flip-flop toggles once per clock pulse, dividing by two.'],
      ['A ripple counter may show wrong values for an instant because', ['the stages change one after another', 'the clock is noisy', 'J and K are low'], 0, 'Each stage is clocked by the one before and waits for its gate delays.']]
    : [['A 4-bit serial-in register needs how many pulses to load a word?', ['4', '1', '8'], 0, 'One bit enters per pulse.'],
      ['Why does the register not simply copy the first bit to all four stages?', ['Each stage sees its neighbour’s old value at the edge', 'The clock is slow', 'The bits are inverted'], 0, 'All stages sample at the same edge, before the neighbour has changed.']];

  return {
    camera: { pos: [0.04, 0.66, 0.92], look: [0.0, 0.03, -0.02] },
    views: { tr: [[0.0, 0.58, 0.55], [0.0, 0.04, -0.1]], bb: [[0.0, 0.4, 0.5], [0.0, 0.01, 0.12]], chips: [[-0.05, 0.22, 0.36], [-0.04, 0.015, 0.13]],
      sw: [[-0.2, 0.16, 0.08], [-0.19, 0.055, -0.04]], clk: [[-0.08, 0.16, 0.08], [-0.08, 0.055, -0.04]], led: [[0.2, 0.16, 0.08], [0.2, 0.055, -0.04]],
      an: [[0.0, 0.2, 0.1], [0.0, 0.1, -0.34]], probe: [[0.3, 0.16, 0.28], [0.3, 0.02, 0.1]], bench: [[0.05, 0.62, 0.9], [0.0, 0.03, -0.02]], book: [[-0.42, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: S.lab.theory, formula: CIRC.eq, formulaNote: CIRC.build,
      more: ['On a 7400 in transistor-transistor logic a LOW is anything below 0.8 V and a HIGH anything above 2 V. Each gate takes about the same short time to answer, called its propagation delay; the circuit here is stepped in whole gate delays.'],
      precautions: S.lab.safety + ' Check the supply pins of every package before switching on.' },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim, 'Circuit: ' + NAME + '.', 'ICs: ' + CIRC.chips.join(', ') + ' (supply pins to +5 V and GND)', 'Data from the trainer’s switches' + (CIRC.clock ? '; clock from its push button' : '') + '; outputs on its lamps.', 'Precaution: wire with the power off; check the supply pins first.'],
      columns: bookCols },
    graph: null,
    result: resultOf,
    tol: 0.001,
    resultNote: FF ? 'Every allowed row of the table agrees with the characteristic equation ' + CIRC.eq + '. The state was stored on the wires of a real NAND network, and the clock decided when it could change.'
      : CNT ? 'All sixteen counts are right. The lamps showed wrong values for an instant at some pulses because the stages change one after another.' : 'The word fed in serially is now held in parallel on the four lamps.',
    chips: FF ? ['Why does the latch remember?', 'What is the forbidden state?', 'What does the clock do?', 'Check my table'] : CNT ? ['Why do I see wrong counts for an instant?', 'Why is Q0 half the clock frequency?', 'Check my table'] : ['Why does the first bit end in Q3?', 'Why do all bits move at once?', 'Check my table'],
    viva: VIVA,
    askState: function () {
      var v = view(), o = { trainer_on: st.power, circuit: NAME, built_from: CIRC.build, rows_recorded: S.rows.length, clock_pulses_given: st.pulses };
      INS.forEach(function (k) { o['input_' + k[1]] = st[k[0]]; });
      outKeys().forEach(function (k) { o['output_' + k] = st.power ? v[k] : 0; });
      if (FF) o.outputs_not_settling = !!v.osc;
      return o; },
    steps: steps,
    tick: function () {
      var v = view();
      leds.forEach(function (g) {
        var on = st.power && (g.userData.key.charAt(0) === 'Q' ? v[g.userData.key] === 1 : false);
        if (st.power && FF && v.osc) on = (Math.floor(performance.now() / 120) % 2) === 0;
        g.userData.mat.color.setHex(on ? 0xff4a34 : 0x4a1210); g.userData.mat.emissive.setHex(on ? 0xff3a20 : 0x000000); g.userData.mat.emissiveIntensity = on ? 2.2 : 0; });
      var po = st.power && (FF ? v.Q === 1 : CNT ? v.Q0 === 1 : v.Q3 === 1);
      plampM.emissive.setHex(po ? 0xff3a20 : 0x000000); plampM.emissiveIntensity = po ? 1.4 : 0;
      hudIn.set(INS.length ? INS.map(function (k) { return k[1] + '=' + st[k[0]]; }).join(' ') : 'clock only');
      hudOut.set(st.power ? (FF ? 'Q=' + v.Q + '  Q̅=' + v.Qb : (CNT ? bits4(v.word) : [v.Q0, v.Q1, v.Q2, v.Q3].join(' '))) : 'off');
      hudRow.set(S.rows.length + (FF ? ' / ' + VALID.length : CNT ? ' / 16' : ' / 4'));
      drawAnalyser();
    },
  };
});
