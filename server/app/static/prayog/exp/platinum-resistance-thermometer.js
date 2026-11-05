/* Prayogshala studio module: platinum resistance thermometer on a Wheatstone bridge (B.Sc. Thermal Physics).
   Serves platinum-resistance-thermometer (alpha between the ice and steam points) and rtd-calibration (null or off-balance
   bridge; the slope of the calibration curve). Physics: the hw_rtd kernel (packs/heat_wave_ug) - the same numbers the server
   checks: R = R0 (1 + A t + B t²), the bridge output Vg = Vs (R / (R + Rref) - 1/2). */
HoolaStudio.define('platinum-resistance-thermometer', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.hw_rtd;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('hw_rtd');
  var OFF = p.mode > 0.5, ALPHA = /^platinum/.test(S.lab.id || '');
  var ELEMENT = p.R0 > 500 ? 'Pt1000' : 'Pt100';
  function r1(v) { return Math.round(v * 10) / 10; }
  function r2(v) { return Math.round(v * 100) / 100; }
  var sim = K.init(p);
  var st = { conn: false, on: false, speed: 30, target: 40, hold: 0, loc: 'air', Rbox: p.R0, shownV: 0, moving: false };
  var NEEDROWS = ALPHA ? 4 : 6;

  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'pinch', 320); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }
  // ---------- bath, ice flask, thermometers
  var BX = -0.85, BZ = -0.28, BR = 0.07, BH = 0.12, IX = -0.5, IZ = -0.28;
  var hp = S.rounded(0.2, 0.2, 0.04, 0.012, new T.MeshStandardMaterial({ color: 0xe7e4dc, roughness: 0.5 })); hp.rotation.x = -Math.PI / 2; hp.position.set(BX, 0.02, BZ); S.scene.add(hp);
  var hsw = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.012, 24), M.red); hsw.rotation.x = Math.PI / 2; hsw.position.set(BX + 0.06, 0.02, BZ + 0.103); S.scene.add(hsw);
  var hlbl = S.label('THERMOSTAT BATH', { w: 0.09, ratio: 0.13, color: '#3b3b3b' }); hlbl.position.set(BX - 0.02, 0.034, BZ + 0.1035); S.scene.add(hlbl);
  S.contact(0.26, 0.26, BX, BZ, 0.55);
  var bath = S.beaker(BR, BH, [BX, 0.04, BZ]);
  var liq = S.mesh(new T.CylinderGeometry(BR * 0.95, BR * 0.95, BH * 0.7, 40), new T.MeshStandardMaterial({ color: 0x6aaccc, roughness: 0.05, metalness: 0.08 }), false); liq.position.y = 0.002 + BH * 0.35; bath.add(liq);
  var stirrer = S.mesh(new T.CylinderGeometry(0.0015, 0.0015, 0.16, 8), M.steel); stirrer.position.set(BX + 0.035, 0.12, BZ), S.scene.add(stirrer);
  var thermo = S.thermometer({ len: 0.3, min: 0, max: 110, value: p.Ts, pos: [BX - 0.03, 0.054, BZ + 0.015] });
  var ice = S.beaker(0.045, 0.1, [IX, 0, IZ]);
  var icelev = S.mesh(new T.CylinderGeometry(0.042, 0.042, 0.07, 32), new T.MeshStandardMaterial({ color: 0xcfe6ee, roughness: 0.2, transparent: true, opacity: 0.9 }), false); icelev.position.y = 0.04; ice.add(icelev);
  for (var ic = 0; ic < 9; ic++) { var cube = S.mesh(new T.BoxGeometry(0.014, 0.014, 0.014), new T.MeshStandardMaterial({ color: 0xf0f8fb, roughness: 0.1, transparent: true, opacity: 0.9 }), false);
    cube.position.set(Math.cos(ic * 1.9) * 0.025, 0.07 + (ic % 3) * 0.004, Math.sin(ic * 1.9) * 0.025); cube.rotation.set(ic, ic * 0.7, 0); ice.add(cube); }
  S.contact(0.12, 0.12, IX, IZ, 0.45);
  var iThermo = S.thermometer({ len: 0.25, min: -10, max: 40, value: 0, pos: [IX - 0.025, 0.014, IZ + 0.012] });
  var icelbl = S.label('MELTING ICE  0 °C', { w: 0.07, ratio: 0.13, color: '#235' }); icelbl.position.set(IX, 0.03, IZ + 0.046); S.scene.add(icelbl);
  // holder where the probe waits
  var HX = -0.67, HZ = -0.28;
  var hold = S.rounded(0.04, 0.04, 0.08, 0.004, M.wood); hold.rotation.x = -Math.PI / 2; hold.position.set(HX, 0.04, HZ + 0.0); S.scene.add(hold); S.contact(0.08, 0.08, HX, HZ, 0.4);
  // ---------- the probe: a steel sheath with a ceramic Pt element inside, a head and a cable
  var probe = new T.Group(); S.scene.add(probe);
  var sheath = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.16, 16), M.steel); sheath.position.y = 0.08; probe.add(sheath);
  var phead = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.028, 18), M.alu); phead.position.y = 0.174; probe.add(phead);
  var ptag = S.label(ELEMENT, { w: 0.018, ratio: 0.5, color: '#222' }); ptag.position.set(0, 0.174, 0.0092); probe.add(ptag);
  var LOC = { air: new T.Vector3(HX, 0.095, HZ), ice: new T.Vector3(IX + 0.012, 0.03, IZ - 0.005), bath: new T.Vector3(BX + 0.012, 0.055, BZ - 0.015) };
  probe.position.copy(LOC.air);
  // ---------- the bridge: ratio arms, decade box, galvanometer or voltmeter
  var BRX = 0.25, BRZ = -0.3;
  var bridge = new T.Group(); S.scene.add(bridge);
  var bb = S.rounded(0.34, 0.12, 0.08, 0.008, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 })); bb.rotation.x = -Math.PI / 2; bb.position.set(BRX, 0.04, BRZ); bridge.add(bb);
  var bl = S.label('WHEATSTONE BRIDGE  ·  P = Q = ' + Math.round(p.Rref) + ' Ω', { w: 0.3, ratio: 0.08, color: '#e8e8e8', bg: '#2b2f36' }); bl.rotation.x = -Math.PI / 2; bl.position.set(BRX, 0.0805, BRZ - 0.035); bridge.add(bl);
  var readTex = S.liveTex(512, 128), readM = new T.Mesh(new T.PlaneGeometry(0.15, 0.0375), new T.MeshBasicMaterial({ map: readTex })); readM.rotation.x = -Math.PI / 2; readM.position.set(BRX - 0.06, 0.0805, BRZ + 0.02); bridge.add(readM);
  var dials = [];
  [0.0, 0.035, 0.07].forEach(function (dx, i) { var dk = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.012, 24), M.chrome); dk.position.set(BRX + 0.04 + dx, 0.086, BRZ + 0.02); bridge.add(dk); dials.push(dk); });
  [-0.14, 0.14].forEach(function (dx) { bridge.add(S.terminal([BRX + dx, 0.082, BRZ + 0.045], dx < 0 ? 'red' : 'black')); });
  S.contact(0.4, 0.18, BRX, BRZ, 0.5);
  var galv = OFF ? null : S.meter({ min: -1, max: 1, zeroCentre: true, unit: '', symbol: 'G', caption: 'GALVANOMETER', ticks: 10, pos: [0.0, 0, -0.1] });
  var lastRead = '';
  function drawRead(txt, sub) { var key = txt + sub; if (key === lastRead) return; lastRead = key;
    readTex.draw(function (x, w, h) { x.fillStyle = '#b9c4a7'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b2116'; x.font = '700 62px "JetBrains Mono", monospace'; x.textAlign = 'right'; x.fillText(txt, w - 14, h - 40); x.font = '600 20px sans-serif'; x.textAlign = 'left'; x.fillText(sub, 14, 26); }); }
  var cable = S.wire([[LOC.air.x, 0.2, LOC.air.z], [-0.4, 0.14, -0.2], [0.0, 0.1, BRZ + 0.1], [BRX - 0.14, 0.09, BRZ + 0.06]], 'black');
  function cablePts() { var c = probe.position; return [[c.x, c.y + 0.12, c.z], [(c.x + BRX) / 2 - 0.2, 0.15, -0.18], [0.0, 0.1, BRZ + 0.1], [BRX - 0.14, 0.09, BRZ + 0.06]]; }
  var watch = S.stopwatch([0.3, 0.035, 0.17], [-1.15, 0, -0.2]);

  S.addApparatus('bath', bath, 'Water bath', 'A thermostat keeps the bath at the temperature you choose, up to boiling. Stirred.');
  S.addApparatus('thermo', thermo, 'Mercury thermometer', 'Reads the bath temperature to 0.1 °C. Your reference thermometer.');
  S.addApparatus('ice', ice, 'Melting ice', 'Crushed ice and a little water, stirred: exactly 0 °C. The ice point.');
  S.addApparatus('ithermo', iThermo, 'Ice-point thermometer', 'Reads 0.0 °C in melting ice.');
  S.addApparatus('probe', probe, ELEMENT + ' probe', ELEMENT + ' platinum resistance element in a steel sheath: ' + Math.round(p.R0) + ' Ω at 0 °C. Carry it by the head.');
  S.addApparatus('bridge', bridge, 'Wheatstone bridge', OFF ? 'Equal ratio arms and a fixed arm of ' + Math.round(p.Rref) + ' Ω, with a ' + p.Vs.toFixed(1) + ' V supply. The unbalanced output voltage gives the probe resistance.' : 'Equal ratio arms and a decade box. When the galvanometer shows no current, the box equals the probe resistance.');
  if (galv) S.addApparatus('galv', galv, 'Zero-centre galvanometer', 'No deflection means the bridge is balanced.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Handy for timing how long the bath has been steady.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var bookLines = ['Aim: ' + (ALPHA ? 'to find the temperature coefficient α of a ' + ELEMENT + ' element.' : 'to calibrate a ' + ELEMENT + ' resistance device.'), OFF ? 'Off-balance bridge: R = Rref (1/2 + Vg/Vs) / (1/2 − Vg/Vs)' : 'Null method: decade box = probe resistance R',
    ALPHA ? 'α = (R100 − R0) / (100 R0)' : 'R = R0 (1 + A t + B t²); slope dR/dt at 50 °C'];
  var hudT = S.hudCard('Bath'), hudR = S.hudCard('Probe R'), hudN = S.hudCard('Readings');

  // ---------- thermostat bath clock
  function runFor(sec) {
    var n = Math.max(1, Math.round(sec / 0.5)), i, h = sec / n;
    for (i = 0; i < n; i++) { sim.on = (st.on && sim.T < st.target - 0.3) ? 1 : 0; K.step(sim, p, h); if (st.on && Math.abs(sim.T - st.target) <= 0.4) st.hold += h; else st.hold = 0; }
  }
  function Tprobe() { return st.loc === 'ice' ? 0 : st.loc === 'bath' ? sim.T : p.Ts; }
  function Rnow() { return K.res(p, Tprobe()); }
  function ready() { return st.loc === 'ice' ? true : st.loc === 'bath' && st.on && st.hold >= 60 && Math.abs(r1(sim.T) - st.target) <= 0.5; }
  function Vnow() { var R = Rnow(); return p.Vs * (R / (R + p.Rref) - 0.5); }
  function devNow() { var R = Rnow(), Vg = p.Vs * (R / (R + st.Rbox) - 0.5); return Math.max(-1, Math.min(1, Vg * (p.R0 / 100) / 0.02)); }
  function setRbox(v) { st.Rbox = Math.max(p.R0 * 0.8, Math.min(p.R0 * 2, Math.round(v * 100) / 100)); if (galv) galv.set(devNow()); }
  function RfromV(v) { return p.Rref * (0.5 + v / p.Vs) / (0.5 - v / p.Vs); }
  function moveProbe(to) {
    if (S.hand.busy || st.loc === to) return Promise.resolve();
    var a = probe.position.clone(), b = LOC[to].clone();
    return carry(a.clone().add(new T.Vector3(0, 0.13, 0)), [{ ms: 1700, fn: function (k) { var q = a.clone().lerp(b, k); q.y += Math.sin(k * Math.PI) * 0.1; return q.add(new T.Vector3(0, 0.13, 0)); },
      onK: function (k) { var q = a.clone().lerp(b, k); q.y += Math.sin(k * Math.PI) * 0.1; probe.position.copy(q); cable.set(cablePts()); } }], 'pinch').then(function () { probe.position.copy(b); cable.set(cablePts()); st.loc = to;
      S.say('The probe is ' + (to === 'ice' ? 'in melting ice.' : to === 'bath' ? 'in the bath.' : 'on its holder.')); S.render(); });
  }
  function connect() { if (st.conn) return; st.conn = true; S.focus('bridge'); S.say('The probe is connected to the bridge.'); S.render(); }
  function heaterOn() { if (S.hand.busy || st.on) return Promise.resolve(); return S.hand.tap(hsw).then(function () { S.click(2000); st.on = true; S.say('Thermostat on. Choose a target temperature.'); S.render(); }); }
  function setTarget(v) { st.target = Math.max(35, Math.min(100, Math.round(v / 5) * 5)); st.hold = 0; S.render(); }
  function record() {
    if (st.loc === 'air') { S.say('Put the probe in the ice or in the bath first.'); return; }
    if (!ready()) { S.say('Let the bath settle at the target first (steady for a minute).'); return; }
    var Tr = st.loc === 'ice' ? 0 : r1(sim.T), R;
    if (OFF) { R = r2(RfromV(Math.round(Vnow() * 1e5) / 1e5)); }
    else { if (Math.abs(devNow()) > 0.04) { S.say('The galvanometer is not at zero. Adjust the decade box until there is no deflection.'); return; } R = st.Rbox; }
    S.addRow({ T: Tr, R: R }); S.say('Written: T = ' + Tr.toFixed(1) + ' °C, R = ' + R.toFixed(2) + ' Ω.');
  }
  function findNull() {
    var lo = p.R0 * 0.8, hi = p.R0 * 2, i, best, bd = 9, c0;
    for (i = 0; i < 40; i++) { var mid = (lo + hi) / 2; setRbox(mid); if (devNow() > 0) lo = mid; else hi = mid; }       // a positive output means the probe is the larger resistance: raise the box
    c0 = Math.round((lo + hi) / 2 * 100) / 100; best = c0;
    for (i = -5; i <= 5; i++) { var c = Math.round((c0 + i * 0.01) * 100) / 100; setRbox(c); var d = Math.abs(devNow()); if (d < bd) { bd = d; best = c; } }
    setRbox(best);
  }
  function rowsOK() {
    var ts = S.rows.map(function (r) { return r.T; });
    if (S.rows.length < NEEDROWS) return false;
    if (ALPHA) return Math.min.apply(null, ts) < 1 && Math.max.apply(null, ts) > 99.5;
    return Math.max.apply(null, ts) - Math.min.apply(null, ts) >= 60;
  }
  function fit2(pts) {
    var n = pts.length, s1 = 0, s2 = 0, s3 = 0, s4 = 0, t0 = 0, t1 = 0, t2 = 0, i, x, y;
    for (i = 0; i < n; i++) { x = pts[i][0]; y = pts[i][1]; s1 += x; s2 += x * x; s3 += x * x * x; s4 += x * x * x * x; t0 += y; t1 += x * y; t2 += x * x * y; }
    var det = n * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2); if (n < 3 || Math.abs(det) < 1e-300) return null;
    return [(t0 * (s2 * s4 - s3 * s3) - s1 * (t1 * s4 - s3 * t2) + s2 * (t1 * s3 - s2 * t2)) / det, (n * (t1 * s4 - s3 * t2) - t0 * (s1 * s4 - s3 * s2) + s2 * (s1 * t2 - t1 * s2)) / det,
      (n * (s2 * t2 - t1 * s3) - s1 * (s1 * t2 - t1 * s2) + t0 * (s1 * s3 - s2 * s2)) / det];
  }
  function curve(rows) { return fit2(rows.map(function (r) { return [r.T, r.R]; })); }
  function alphaOf(rows) {
    if (rows.length < 2) return null; var lo = rows[0], hi = rows[0];
    rows.forEach(function (r) { if (Math.abs(r.T) < Math.abs(lo.T)) lo = r; if (Math.abs(r.T - 100) < Math.abs(hi.T - 100)) hi = r; });
    return (hi.T === lo.T || lo.R === 0) ? null : (hi.R - lo.R) / ((hi.T - lo.T) * lo.R);
  }
  function setSpeed(v) { st.speed = v; S.render(); }

  return {
    camera: { pos: [-0.2, 0.7, 1.75], look: [-0.15, 0.1, -0.25] },
    views: { bath: [[-0.7, 0.3, 0.3], [BX, 0.1, BZ]], thermo: [[-0.7, 0.3, 0.3], [BX - 0.03, 0.15, BZ]], ice: [[-0.4, 0.25, 0.3], [IX, 0.06, IZ]], ithermo: [[-0.4, 0.25, 0.3], [IX - 0.025, 0.1, IZ]], probe: [[-0.55, 0.3, 0.3], [HX, 0.12, HZ]],
      bridge: [[0.25, 0.3, 0.2], [BRX, 0.05, BRZ]], galv: [[0.05, 0.22, 0.2], [0.0, 0.05, -0.1]], sw: [[-0.5, 0.4, 0.5], [-1.1, 0.05, -0.2]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'The resistance of platinum rises almost in proportion to its temperature, so a platinum wire is a thermometer. ' + ELEMENT + ' means ' + Math.round(p.R0) + ' Ω at 0 °C. A Wheatstone bridge measures the resistance.',
      formula: 'R = R0 (1 + A t + B t²),   α = (R100 − R0) / (100 R0)', formulaNote: 'For the standard element A = 3.9083×10⁻³ /°C and B = −5.775×10⁻⁷ /°C², so α ≈ 3.85×10⁻³ per kelvin. The slope dR/dt = R0 (A + 2 B t) falls slowly as t rises.',
      more: [OFF ? 'Off-balance bridge: the output Vg = Vs (R / (R + Rref) − 1/2) is read on a voltmeter; then R = Rref (1/2 + Vg/Vs) / (1/2 − Vg/Vs).' : 'Null method: change the decade box until the galvanometer shows no current; then R equals the box.'],
      precautions: 'Keep the bridge current small so the probe does not heat itself. Stir the bath and let it settle before each reading. Put the probe in the ice only after dabbing it dry. Boiling water scalds.' },
    book: { title: 'Expt. — Platinum resistance thermometer', lines: bookLines,
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'T (°C)', get: function (r) { return r.T.toFixed(1); } }, { label: 'R (Ω)', get: function (r) { return r.R.toFixed(2); } },
        { label: 'R / R0', get: function (r) { return (r.R / p.R0).toFixed(4); } }] },
    graph: { x: function (r) { return r.T; }, y: function (r) { return r.R; }, xlabel: 'T (°C)', ylabel: 'R (Ω)', x0: 0, y0: Math.floor(p.R0 * 0.9 / 10) * 10,
      line: function () { var f = curve(S.rows); return f ? function (x) { return f[0] + f[1] * x + f[2] * x * x; } : null; } },
    result: function (rows) {
      if (ALPHA) { var a = alphaOf(rows); if (a === null) return null; return { label: 'α (0 to 100 °C)', value: a, unit: '1/K', digits: 6, truth: p.A + 100 * p.B, note: 'α = (R100 − R0) / (100 R0) from the ice point and the steam point.' }; }
      var f = curve(rows); if (!f) return null;
      return { label: 'dR/dt at 50 °C', value: f[1] + 100 * f[2], unit: 'Ω/K', digits: 4, truth: p.R0 * (p.A + 100 * p.B), note: 'The slope of the fitted calibration curve at 50 °C; R = ' + f[0].toFixed(2) + ' + ' + f[1].toFixed(4) + ' t ' + (f[2] < 0 ? '−' : '+') + ' ' + Math.abs(f[2] * 1e5).toFixed(2) + '×10⁻⁵ t².' };
    },
    tol: 0.01,
    chips: ['Why keep the bridge current small?', 'Why use melting ice and boiling water?', OFF ? 'How do I get R from the voltage?' : 'How do I know the bridge is balanced?', 'Check my readings', 'Why is my result different?'],
    viva: [['What does Pt100 mean?', ['A platinum element of 100 Ω at 0 °C', 'A probe that reads 100 °C', '100 turns of platinum wire'], 0, 'The number is its resistance at the ice point.'],
      ['Why is the probe\'s current kept small?', ['To avoid heating it, which would raise its own temperature', 'To save the battery', 'To keep the bridge balanced'], 0, 'Self-heating makes the probe read higher than the bath.']],
    askState: function () { return { probe_at: st.loc, connected: st.conn, thermostat_on: st.on, target_C: st.target, bath_C: r1(sim.T), steady_for_s: Math.round(st.hold), decade_box_ohm: OFF ? null : st.Rbox, galvanometer: OFF ? null : +devNow().toFixed(2), bridge_output_mV: OFF ? +(Vnow() * 1000).toFixed(2) : null, readings: S.rows.length }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bridge', render: function (u) {
          u.h2('Connect the probe and switch the bath on');
          u.task('1. Connect the probe to the bridge', st.conn, st.conn ? 'Connected (two-wire)' : 'The cable goes to the left terminal')
            .add(u.button(st.conn ? 'Connected' : 'Connect', connect, !st.conn, st.conn));
          u.task('2. Switch the thermostat on', st.on, st.on ? 'On' : 'The hand presses the heater switch')
            .add(u.button(st.on ? 'On' : 'Switch on', function () { heaterOn(); }, st.conn && !st.on, st.on || S.hand.busy));
          u.next('Next: take readings', st.conn && st.on);
        },
        ok: function () { return st.conn && st.on; },
        auto: function () { connect(); return heaterOn(); } },
      { id: 'readings', title: 'Readings', view: 'probe', render: function (u) {
          u.h2(ALPHA ? 'Ice point, steam point and a few between' : 'A reading at each temperature');
          u.p(ALPHA ? 'Read R in melting ice and in boiling water (target 100 °C), plus two points between.' : 'Take at least ' + NEEDROWS + ' readings from the ice point to boiling.');
          u.row(u.button('Probe → ice', function () { moveProbe('ice').then(function () { S.render(); }); }, st.loc !== 'ice', st.loc === 'ice' || S.hand.busy),
            u.button('Probe → bath', function () { moveProbe('bath').then(function () { S.render(); }); }, st.loc !== 'bath', st.loc === 'bath' || S.hand.busy));
          u.slider('Bath target', 35, 100, 5, function () { return st.target; }, function (v) { setTarget(v); }, '°C', 0);
          var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
          [1, 30, 120].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
          u.live(function () { return 'Probe in ' + (st.loc === 'air' ? 'air (on its holder)' : st.loc === 'ice' ? 'melting ice: 0.0 °C' : 'the bath, ' + r1(sim.T).toFixed(1) + ' °C (target ' + st.target + ') · ' + (ready() ? 'STEADY' : 'settling')); });
          if (!OFF) {
            u.slider('Decade box R', p.R0 * 0.8, p.R0 * 2, 1, function () { return st.Rbox; }, function (v) { setRbox(v); }, 'Ω', 0);
            u.row(u.button('−0.1', function () { setRbox(st.Rbox - 0.1); S.render(); }, false, false), u.button('−0.01', function () { setRbox(st.Rbox - 0.01); S.render(); }, false, false),
              u.button('+0.01', function () { setRbox(st.Rbox + 0.01); S.render(); }, false, false), u.button('+0.1', function () { setRbox(st.Rbox + 0.1); S.render(); }, false, false));
            u.live(function () { var d = devNow(); return 'Box ' + st.Rbox.toFixed(2) + ' Ω · galvanometer ' + (Math.abs(d) < 0.04 ? 'at zero (balanced)' : d > 0 ? 'deflects right: the probe is larger, raise the box' : 'deflects left: lower the box'); });
          } else u.live(function () { return 'Bridge output: ' + (Vnow() * 1000).toFixed(2) + ' mV'; });
          u.row(u.button('Write in the table', record, true, st.loc === 'air' || !ready()));
          u.h3('Observation table'); u.table();
          u.next('Next: plot R against T', rowsOK());
          if (!rowsOK()) u.p(S.rows.length + ' reading(s) so far. ' + (ALPHA ? 'Need the ice point, the steam point and at least ' + NEEDROWS + ' readings.' : 'Need at least ' + NEEDROWS + ' readings spread over 60 °C or more.'));
        },
        ok: function () { return rowsOK(); },
        auto: function () {
          var targets = ALPHA ? [40, 70, 100] : [40, 55, 70, 85, 100];
          return moveProbe('ice').then(function () { if (!OFF) findNull(); record(); return moveProbe('bath'); }).then(function () {
            for (var i = 0; i < targets.length; i++) { setTarget(targets[i]); var n = 0; while (!ready() && n++ < 20000) runFor(2); if (!OFF) findNull(); record(); }
          }); } },
    ],

    tick: function (dt) {
      if (st.on) runFor(Math.min(dt * st.speed, 8));
      thermo.set(sim.T); iThermo.set(0);
      var R = st.conn ? Rnow() : 0;
      if (galv) galv.set(devNow());
      if (OFF) drawRead(st.conn ? (Vnow() * 1000).toFixed(2) + ' mV' : '0.00 mV', 'OUTPUT Vg');
      else drawRead(st.Rbox.toFixed(2) + ' Ω', 'DECADE BOX');
      hudT.set(r1(sim.T).toFixed(1) + ' °C'); hudR.set(st.conn && st.loc !== 'air' ? R.toFixed(2) + ' Ω' : '—'); hudN.set(String(S.rows.length));
    },
  };
});
