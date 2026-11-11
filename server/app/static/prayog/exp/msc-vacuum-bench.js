/* Prayogshala studio module: VACUUM BENCH (pump-down, Gaede's equation, Pirani and ionisation gauges).
   A glass bell jar on a baseplate, a rotary pump (and, for the gauge experiment, a diffusion pump behind it), a Pirani
   gauge and an ionisation gauge. The `msc_vac` kernel (packs/msc_solid.js) gives the pressure P(t) = Pu + (P0 - Pu) exp(-S t / V)
   with Pu = Q / S, and the two gauges' real limits: the Pirani saturates above about a kilopascal and floors at 0.1 Pa,
   the ionisation gauge reads only below 0.1 Pa and is interlocked off above it. The student runs the clock and reads the
   gauges, then finds the pumping speed from the slope of ln(P - Pu) (Gaede's equation) or the ultimate pressure from the
   ionisation gauge. The simulated clock runs on demand: the student chooses how long to wait. */
HoolaStudio.define('msc-vacuum-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.msc_vac, assign = HK.assign;
  var p = HK.paramsFor('msc_vac', S.lab.params);
  var GAEDE = String(S.lab.id).indexOf('gaede') === 0;
  var TEND = GAEDE ? 1500 : 200;
  var PU = p.Q / p.S;
  var st = { vent: false, run: false, t: 0, ion: false, running: false, hv: false };
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function sig(v, n) { return v === 0 ? 0 : +v.toPrecision(n); }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 24); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }
  function fmtP(v) { var e = Math.floor(Math.log10(v)), m = v / Math.pow(10, e); return m.toFixed(2) + 'E' + e; }
  function pvals() { return KN.view({}, assign(p, { t: st.t })); }
  function pirani() { return sig(pvals().Ppir, 3); }
  function ion() { var v = pvals().Pion; return v < 0 ? null : sig(v, 3); }

  var CX = -0.3, CZ = -0.15;
  var plate = new T.Group(); S.scene.add(plate); plate.position.set(CX, 0, CZ);
  mk(plate, cyl(0.1, 0.105, 0.025, 48), new T.MeshStandardMaterial({ color: 0xaeb4ba, roughness: 0.3, metalness: 0.9 }), 0, 0.0125, 0);
  mk(plate, cyl(0.082, 0.082, 0.004, 48), M.rubber, 0, 0.027, 0);
  var jarM = new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.04, transmission: 0.92, thickness: 0.004, transparent: true, opacity: 0.32 });
  mk(plate, cyl(0.075, 0.075, 0.16, 48), jarM, 0, 0.109, 0);
  var dome = mk(plate, new T.SphereGeometry(0.075, 36, 18, 0, Math.PI * 2, 0, Math.PI / 2), jarM, 0, 0.189, 0);
  mk(plate, cyl(0.075, 0.075, 0.006, 48), M.rubber, 0, 0.03, 0);
  var filament = mk(plate, new T.SphereGeometry(0.004, 10, 10), new T.MeshBasicMaterial({ color: 0xffa040, transparent: true, opacity: 0 }), 0.0, 0.07, 0);
  mk(plate, cyl(0.004, 0.004, 0.05, 8), M.copper, 0, 0.055, 0);
  var jl = S.label('50 litre vessel', { w: 0.08, ratio: 0.14, color: '#e8eaec', bg: '#2b323d' }); jl.position.set(0, 0.0125, 0.1065); plate.add(jl);
  S.contact(0.28, 0.28, CX, CZ, 0.55);
  // pipe, Pirani head, vent valve
  var pipe = mk(S.scene, cyl(0.011, 0.011, 0.22, 16), M.steel, CX + 0.12, 0.038, CZ); pipe.rotation.z = Math.PI / 2;
  mk(S.scene, cyl(0.014, 0.014, 0.03, 18), M.chrome, CX + 0.1, 0.06, CZ);
  var head = mk(S.scene, cyl(0.009, 0.009, 0.04, 14), M.brass, CX + 0.1, 0.09, CZ);
  var ventG = new T.Group(); ventG.position.set(CX + 0.05, 0.05, CZ + 0.02); S.scene.add(ventG);
  mk(ventG, cyl(0.006, 0.006, 0.03, 12), M.steel, 0, 0, 0); var vh = mk(ventG, box(0.03, 0.006, 0.008), M.red, 0, 0.02, 0);
  var vl = S.label('VENT', { w: 0.02, ratio: 0.3, color: '#e8eaec' }); vl.position.set(0, 0.032, 0.013); vl.rotation.x = -0.3; ventG.add(vl);
  // rotary pump
  var rot = new T.Group(); rot.position.set(CX + 0.28, 0, CZ + 0.02); S.scene.add(rot);
  mk(rot, box(0.14, 0.07, 0.07), new T.MeshStandardMaterial({ color: 0x2c63c4, roughness: 0.4, metalness: 0.4 }), 0, 0.045, 0);
  mk(rot, cyl(0.04, 0.04, 0.09, 28), new T.MeshStandardMaterial({ color: 0x2c63c4, roughness: 0.4, metalness: 0.4 }), 0.1, 0.05, 0).rotation.z = Math.PI / 2;
  mk(rot, cyl(0.012, 0.012, 0.006, 20), new T.MeshStandardMaterial({ color: 0xe6d9a0, roughness: 0.2, transparent: true, opacity: 0.8 }), 0, 0.075, 0.0355).rotation.x = Math.PI / 2;
  mk(rot, box(0.012, 0.012, 0.01), M.chrome, -0.04, 0.095, 0);
  var rl = S.label('ROTARY PUMP', { w: 0.08, ratio: 0.14, color: '#fff' }); rl.position.set(0, 0.025, 0.0355); rot.add(rl);
  S.contact(0.28, 0.14, CX + 0.28, CZ + 0.02, 0.55);
  var hose = mk(S.scene, cyl(0.006, 0.006, 0.2, 10), M.rubber, CX + 0.22, 0.042, CZ + 0.0); hose.rotation.z = Math.PI / 2;
  var dif = null;
  if (!GAEDE) {
    dif = new T.Group(); dif.position.set(CX + 0.14, 0, CZ - 0.12); S.scene.add(dif);
    mk(dif, cyl(0.035, 0.035, 0.012, 28), M.alu, 0, 0.006, 0);
    mk(dif, cyl(0.026, 0.026, 0.16, 28), new T.MeshStandardMaterial({ color: 0xb8bcc0, roughness: 0.25, metalness: 0.9 }), 0, 0.092, 0);
    for (var f = 0; f < 6; f++) mk(dif, new T.TorusGeometry(0.03, 0.0025, 6, 28), M.copper, 0, 0.035 + f * 0.025, 0).rotation.x = Math.PI / 2;
    mk(dif, cyl(0.032, 0.032, 0.01, 28), M.alu, 0, 0.18, 0);
    var dl = S.label('DIFFUSION PUMP', { w: 0.07, ratio: 0.14, color: '#20252b', bg: '#d8dde2' }); dl.position.set(0, 0.03, 0.0305); dif.add(dl);
    S.contact(0.12, 0.12, CX + 0.14, CZ - 0.12, 0.5);
  }

  function instBox(x, z, rotY, title, sub, wdt) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = rotY;
    var W = wdt || 0.2, Dd = 0.15, Hh = 0.08;
    var cse = S.rounded(W, Dd, Hh, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 })); cse.rotation.x = -Math.PI / 2; cse.position.y = Hh / 2 + 0.003; g.add(cse);
    var FZ = Dd / 2 + 0.005, PW = W - 0.012, PH = Hh - 0.012;
    var tex = S.canvasTex(900, Math.round(900 * PH / PW), function (xx, w, h) { xx.fillStyle = '#2b323d'; xx.fillRect(0, 0, w, h); xx.strokeStyle = 'rgba(255,255,255,.12)'; xx.lineWidth = 3; xx.strokeRect(8, 8, w - 16, h - 16);
      xx.fillStyle = '#f1efe8'; xx.font = '700 34px "Public Sans", sans-serif'; xx.fillText(title, 26, 52); xx.font = '500 22px "Public Sans", sans-serif'; xx.fillStyle = '#c7ccd6'; xx.fillText(sub, 26, 88); });
    var fac = S.mesh(box(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]); fac.position.set(0, 0.003 + Hh / 2, FZ - 0.002); g.add(fac);
    var lcdT = S.liveTex(512, 180), last = '';
    var bez = S.mesh(box(PW * 0.52, PH * 0.42, 0.003), M.grey); bez.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.001); g.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(PW * 0.48, PH * 0.38), new T.MeshBasicMaterial({ map: lcdT, toneMapped: false })); scr.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(scr);
    var knobG = new T.Group(); knobG.position.set(-PW * 0.28, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(knobG);
    var kk = S.mesh(cyl(0.012, 0.013, 0.012, 28), M.bakelite); kk.rotation.x = Math.PI / 2; knobG.add(kk);
    var kp = S.mesh(box(0.0018, 0.012, 0.001), M.white, false); kp.position.set(0, 0.007, 0.007); knobG.add(kp);
    S.contact(W + 0.06, Dd + 0.06, x, z, 0.5);
    return { group: g, knob: knobG, show: function (txt, u2) { if (txt + u2 === last) return; last = txt + u2;
      lcdT.draw(function (xx) { var gr = xx.createLinearGradient(0, 0, 0, 180); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); xx.fillStyle = gr; xx.fillRect(0, 0, 512, 180);
        xx.font = '700 ' + (txt.length > 6 ? 70 : 92) + 'px "JetBrains Mono", monospace'; xx.textAlign = 'right'; xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 118); xx.font = '600 34px "Public Sans", sans-serif'; xx.fillText(u2, 496, 150); }); } };
  }
  var clock = instBox(0.0, 0.1, -0.1, GAEDE ? 'PUMP SWITCH + TIMER' : 'HIGH-VACUUM VALVE + TIMER', GAEDE ? 'starts the rotary pump and the clock' : 'opens the diffusion pump to the vessel', 0.22);
  var pir = instBox(0.28, -0.06, -0.35, 'PIRANI GAUGE', 'thermal conductivity, 0.1 Pa to 1 kPa', 0.2);
  var ionB = GAEDE ? null : instBox(0.02, -0.24, 0.1, 'IONISATION GAUGE', 'below 0.1 Pa only · interlocked', 0.2);
  clock.show('0', 's'); pir.show(fmtP(pirani()), 'Pa'); if (ionB) ionB.show('OFF', '');
  S.wire([[CX + 0.1, 0.11, CZ], [0.0, 0.03, -0.02], [0.2, 0.03, -0.1]], 'blue');
  S.addApparatus('jar', plate, 'Bell jar and baseplate', 'A glass bell jar of 50 litres on a greased baseplate. Everything that matters is the gas inside it and how fast the pump takes it away.');
  S.addApparatus('pump', rot, 'Rotary pump', 'A two-stage oil-sealed pump. By itself it takes the pressure to about a pascal.');
  if (dif) S.addApparatus('diff', dif, 'Diffusion pump', 'Hot oil vapour carries gas molecules downward to the rotary pump. It needs the rotary pump behind it and takes the pressure far lower.');
  S.addApparatus('pir', pir.group, 'Pirani gauge', 'A hot wire cooled by the gas. Accurate from about 0.1 Pa to 1 kPa; above that it saturates, below it only reads its floor.');
  if (ionB) S.addApparatus('ionb', ionB.group, 'Ionisation gauge', 'A hot cathode ionises the gas and the ion current is read. It works from 10⁻⁶ to 0.1 Pa. Above 0.1 Pa the filament burns out, so it is interlocked off.');
  S.addApparatus('clock', clock.group, 'Pump switch and timer', 'Starts the pump and runs the timer in seconds. You choose how long to wait before reading the gauge.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudT = S.hudCard('Time'), hudP = S.hudCard('Gauge reading');

  function ventClose() {
    if (busy() || st.vent) return Promise.resolve();
    return S.hand.tap(vh, 'top').then(function () { st.vent = true; vh.rotation.y = Math.PI / 2; S.say('Vent valve closed.'); S.click(660, 0.05); S.render(); });
  }
  function start() {
    if (busy() || st.run) return Promise.resolve();
    if (!st.vent) { S.say('Close the vent valve first.'); return Promise.resolve(); }
    return S.hand.tap(clock.knob, 'front').then(function () { st.run = true; S.say(GAEDE ? 'The rotary pump is running and the timer has started at zero.' : 'The high-vacuum valve is open and the timer has started at zero.'); S.click(880, 0.05); S.render(); });
  }
  function runTo(t1) {
    if (busy()) return Promise.resolve();
    if (!st.run) { S.say('Start the pump first.'); return Promise.resolve(); }
    if (t1 < st.t) { S.say('The clock only runs forward: choose a time later than ' + Math.round(st.t) + ' s.'); return Promise.resolve(); }
    if (t1 > TEND) { S.say('This run lasts ' + TEND + ' s.'); return Promise.resolve(); }
    var t0 = st.t; st.running = true;
    return S.tween(300 + Math.min(1800, (t1 - t0) * 3), function (k) { st.t = t0 + (t1 - t0) * k; }).then(function () { st.t = t1; st.running = false; S.say('The clock reads ' + Math.round(t1) + ' s.'); S.render(); });
  }
  function ionOn() {
    if (GAEDE || busy() || st.ion) return Promise.resolve();
    if (!st.run) { S.say('Start the pumping first.'); return Promise.resolve(); }
    if (pirani() > 0.15) { S.say('The Pirani gauge reads ' + pirani() + ' Pa. The ionisation gauge stays interlocked off above 0.1 Pa: its filament would burn out.'); return Promise.resolve(); }
    return S.hand.tap(ionB.knob, 'front').then(function () { st.ion = true; S.say('Ionisation gauge on. It reads below 0.1 Pa.'); S.click(880, 0.05); S.render(); });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return null; }
    if (!st.run) { S.say('Start the pump first.'); return null; }
    if (st.running) { S.say('Wait for the clock to stop.'); return null; }
    var tt = Math.round(st.t);
    for (var i = 0; i < S.rows.length; i++) if (S.rows[i].t === tt) { S.say('You already have a reading at ' + tt + ' s. Let the clock run on.'); return null; }
    var useIon = st.ion && ion() !== null, v = useIon ? ion() : pirani();
    var row = { t: tt, P: v, g: useIon ? 'ion' : 'Pirani', lnP: Math.log(v) };
    S.addRow(row);
    S.say('Written in your record book: t = ' + tt + ' s, ' + (useIon ? 'ionisation gauge ' : 'Pirani gauge ') + fmtP(v) + ' Pa.');
    return row;
  }

  function result(rows) {
    var r = rows.slice().sort(function (a, b) { return a.t - b.t; }), n = r.length;
    if (n < 6) return null;
    var last = r[n - 1], prev = r[n - 2];
    if (Math.abs(last.P - prev.P) > 0.03 * last.P) return null;                  // the pressure must have stopped falling
    var pu = last.P;
    if (!GAEDE) return { label: 'Ultimate pressure', value: pu, unit: 'Pa', digits: 5, truth: PU, note: 'The last two ionisation-gauge readings (' + prev.t + ' s and ' + last.t + ' s) agree: the pressure has stopped falling, so the ultimate pressure is ' + fmtP(pu) + ' Pa. The Pirani gauge had floored at 0.1 Pa long before.' };
    var pts = r.filter(function (q) { return q.P <= 100 && q.P > 2.5 * pu; }).map(function (q) { return [q.t, Math.log(q.P - pu)]; });
    if (pts.length < 5) return null;
    var f = S.fit.linear(pts); if (!f || f.m >= 0) return null;
    return { label: 'Pumping speed of the rotary pump', value: -p.V * f.m, unit: 'm³/s', digits: 5, truth: p.S,
      note: 'The pressure levels off at Pu = ' + pu + ' Pa. For the readings between ' + Math.round(2.5 * pu * 10) / 10 + ' and 100 Pa (where the Pirani gauge is accurate) ln(P − Pu) falls linearly: slope ' + f.m.toFixed(5) + ' /s. S = V × |slope| = ' + p.V.toFixed(3) + ' m³ × ' + (-f.m).toFixed(5) + ' /s (' + (-p.V * f.m * 1000).toFixed(2) + ' L/s), the same as Gaede\'s equation between two points.' };
  }

  var AUTO = GAEDE ? [0, 120, 180, 240, 280, 300, 320, 340, 360, 380, 400, 450, 600, 1500] : [0, 5, 10, 15, 20, 25, 40, 60, 80, 100, 120, 150, 200];
  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { jar: [[-0.3, 0.3, 0.3], [-0.3, 0.1, -0.15]], pump: [[-0.02, 0.2, 0.2], [-0.02, 0.05, -0.13]], diff: [[-0.1, 0.3, 0.1], [-0.16, 0.1, -0.27]], pir: [[0.3, 0.24, 0.16], [0.28, 0.05, -0.06]], ionb: [[0.0, 0.25, 0.3], [0.02, 0.04, -0.24]],
      clock: [[0.0, 0.26, 0.32], [0.0, 0.05, 0.1]], bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: S.lab.theory,
      formula: GAEDE ? 'S = (V / t) ln[(P₁ − Pu) / (P₂ − Pu)]' : 'Pu = Q / S',
      formulaNote: GAEDE ? 'V = ' + p.V.toFixed(3) + ' m³ for this vessel; Pu is the ultimate pressure' : 'Q is the gas load (leaks and outgassing), S the pumping speed',
      more: ['A gauge is only to be believed inside its range: the Pirani gauge above about a kilopascal reads far too low, and below 0.1 Pa it only shows its floor.', 'The ionisation gauge must never be switched on above 0.1 Pa.', 'The clock runs only when you ask it to, so choose when to read.'],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 110) + (S.lab.aim.length > 110 ? '…' : ''), 'Vessel volume V = ' + (p.V * 1000).toFixed(0) + ' litres.', GAEDE ? 'Pirani gauge, 0.1 Pa to 1 kPa.' : 'Pirani gauge to 0.1 Pa, ionisation gauge below.'],
      columns: [{ label: 't (s)', get: function (r) { return r.t; } }, { label: 'gauge', get: function (r) { return r.g; } }, { label: 'P (Pa)', get: function (r) { return fmtP(r.P); } }, { label: 'ln P', get: function (r) { return r.lnP.toFixed(2); } }] },
    graph: { x: function (r) { return r.t; }, y: function (r) { return r.lnP; }, xlabel: 't (s)', ylabel: 'ln P (P in Pa)', line: function () { return null; } },
    result: result,
    tol: 0.03,
    resultNote: GAEDE ? 'The speed came from the slope of your own readings, the way Gaede\'s equation uses two of them.' : 'The ultimate pressure is the ionisation gauge\'s steady reading; the lab\'s true value is shown for comparison.',
    chips: ['Why can\'t the Pirani gauge read at atmospheric pressure?', 'What is the ultimate pressure?', 'Check my readings', 'Why is the ion gauge interlocked?'],
    viva: [],
    askState: function () { return { experiment: S.lab.title, vent_closed: st.vent, pumping: st.run, time_s: Math.round(st.t), pirani_Pa: st.run ? pirani() : 'atmosphere', ionisation_gauge: st.ion ? ion() : 'off', readings_taken: S.rows.length }; },
    steps: [
      { id: 'start', title: 'Start pumping', view: 'jar', render: function (u) {
          u.h2('Close the vent, start pumping');
          u.p(GAEDE ? 'The vessel is at atmospheric pressure. Close the vent valve, then start the rotary pump: the timer starts with it.' : 'The vessel has been roughed down to about 10 Pa and the diffusion pump is hot. Close the vent valve, then open the high-vacuum valve: the timer starts with it.');
          u.task('1. Close the vent valve', st.vent, st.vent ? 'Closed' : 'Open').add(u.button(st.vent ? 'Closed' : 'Close the vent valve', function () { S.focus('jar'); ventClose(); }, !st.vent, st.vent || S.hand.busy));
          u.task('2. ' + (GAEDE ? 'Start the pump' : 'Open the high-vacuum valve'), st.run, st.run ? 'Pumping' : 'Not started').add(u.button(st.run ? 'Pumping' : (GAEDE ? 'Start the pump' : 'Open the valve'), function () { S.focus('clock'); start(); }, !st.run && st.vent, st.run || !st.vent || S.hand.busy));
          u.next('Next: read the gauges', st.vent && st.run);
        },
        ok: function () { return st.vent && st.run; }, auto: function () { return ventClose().then(start); } },
      { id: 'read', title: 'Read the gauges', view: 'pir', render: function (u) {
          u.h2('Let the clock run, read the gauges');
          u.p(GAEDE ? 'Choose a time, run the clock to it, and record the Pirani reading. Take a first reading at zero and notice what the gauge says at atmospheric pressure. Carry on until the pressure stops falling.'
            : 'Run the clock and record the Pirani gauge until it reaches its 0.1 Pa floor. Then switch the ionisation gauge on, and carry on reading it until the pressure stops falling.');
          var tg = { v: st.t };
          u.slider('Run the clock to', 0, TEND, 1, function () { return tg.v; }, function (v) { tg.v = v; }, 's', 0);
          u.row(u.button('Run the clock', function () { S.focus('clock'); runTo(tg.v); }, true, S.hand.busy), u.button('Record the reading', function () { S.focus('pir'); record(); }, false, S.hand.busy));
          if (!GAEDE) u.task('Ionisation gauge', st.ion, st.ion ? 'On' : 'Off: switch on only below 0.1 Pa').add(u.button(st.ion ? 'On' : 'Switch the ionisation gauge on', function () { S.focus('ionb'); ionOn(); }, !st.ion, st.ion || S.hand.busy));
          u.live(function () { return 't = ' + Math.round(st.t) + ' s  ·  Pirani ' + fmtP(pirani()) + ' Pa' + (st.ion ? '  ·  ion ' + (ion() === null ? 'interlocked' : fmtP(ion()) + ' Pa') : ''); });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 6) u.p(S.rows.length + ' of at least 6 readings taken.');
          u.next('Next: the result', S.rows.length >= 6);
        },
        ok: function () { return S.rows.length >= 6; },
        auto: function () {
          var ionAt = 25;
          return AUTO.reduce(function (pr, t1) { return pr.then(function () { return runTo(t1); }).then(function () { return (!GAEDE && t1 > ionAt && !st.ion) ? ionOn() : null; }).then(function () { record(); }); }, Promise.resolve());
        } }
    ],
    tick: function () {
      clock.show(Math.round(st.t) + '', 's'); pir.show(st.run ? fmtP(pirani()) : fmtP(pirani()), 'Pa'); if (ionB) ionB.show(st.ion ? (ion() === null ? 'LOCK' : fmtP(ion())) : 'OFF', st.ion ? 'Pa' : '');
      filament.material.opacity = st.ion ? 0.9 : 0;
      hudT.set(Math.round(st.t) + ' s'); hudP.set(fmtP(pirani()) + ' Pa');
    },
  };
});
