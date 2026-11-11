/* Prayogshala studio module: LIGHT-DEPENDENT RESISTOR on an optical bench (NCERT Class XII, Section B activity).
   A small filament lamp on a sliding upright, a cadmium sulphide cell in a matt black hood at the far end of the
   bench, and a digital multimeter set to ohms. The hand slides the lamp along the printed bench scale; the
   illumination on the cell follows the inverse-square law, and the resistance comes from this lab's kernel
   (packs/elec11.js: R = A E^-gamma) - the same code the server checks against the textbook formula. */
HoolaStudio.define('ldr-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.ldr;
  var p = HK.paramsFor('ldr', S.lab.params);
  var DMIN = 0.08, DMAX = 0.6;
  var st = { traced: false, lamp: false, d: 0.2 };

  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }

  // ---------------------------------------------------------------- the optical bench (0 cm at the cell)
  var X0 = -0.52;                                    // x of the cell, which is the zero of the bench scale
  function xOf(d) { return X0 + d; }
  var bench = S.opticalBench({ len: 0.78, x0: X0 - 0.06, z: -0.3 });
  var scaleTex = S.canvasTex(2048, 110, function (c, w, h) {
    c.drawImage(S.woodTex.image, 0, 0, w, h); c.fillStyle = 'rgba(255,248,230,.5)'; c.fillRect(0, 0, w, h);
    var k = (w - 40) / 70; c.fillStyle = '#161616'; c.textAlign = 'center';
    for (var i = 0; i <= 70; i++) { var xx = 20 + i * k, big = i % 10 === 0;
      c.fillRect(xx - (i % 5 ? 0.7 : 1.4), 0, i % 5 ? 1.4 : 2.6, big ? 44 : i % 5 === 0 ? 32 : 18);
      if (big) { c.font = '700 30px "Public Sans", sans-serif'; c.fillText(String(i), xx, 78); } }
    c.font = '600 20px "Public Sans", sans-serif'; c.textAlign = 'left'; c.fillStyle = '#6b4a14';
    c.fillText('DISTANCE FROM THE CELL  ·  cm', 30, 102); });
  var scl = S.mesh(new T.BoxGeometry(0.712, 0.004, 0.026), [M.wood, M.wood, new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.55 }), M.wood, M.wood, M.wood]);
  scl.position.set(X0 + 0.35, 0.044, -0.254); S.scene.add(scl);

  // ---------------------------------------------------------------- the cell in its hood
  var cell = new T.Group(); S.scene.add(cell); cell.position.set(X0, 0, -0.3);
  var up1 = S.upright(-0.3, 0.1); up1.position.set(X0, 0, -0.3);
  var hood = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.05, 28, 1, true), new T.MeshStandardMaterial({ color: 0x121214, roughness: 0.95, side: T.DoubleSide }));
  hood.rotation.z = Math.PI / 2; hood.position.set(0.02, 0.15, 0); cell.add(hood);
  var back = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.004, 28), new T.MeshStandardMaterial({ color: 0x18181a, roughness: 0.9 }));
  back.rotation.z = Math.PI / 2; back.position.set(-0.004, 0.15, 0); cell.add(back);
  var face = S.mesh(new T.CylinderGeometry(0.0075, 0.0075, 0.0025, 28), new T.MeshStandardMaterial({ color: 0xe8d9a8, roughness: 0.5 }));
  face.rotation.z = Math.PI / 2; face.position.set(0.0, 0.15, 0); cell.add(face);
  var zig = S.canvasTex(256, 256, function (c, w, h) { c.fillStyle = '#e8d9a8'; c.fillRect(0, 0, w, h);
    c.strokeStyle = '#2b2b2e'; c.lineWidth = 9; c.beginPath();
    for (var i = 0; i <= 14; i++) { var yy = 24 + i * 15, xx = i % 2 ? w - 40 : 40; if (i) c.lineTo(xx, yy); else c.moveTo(xx, yy); } c.stroke(); });
  var zigM = new T.Mesh(new T.CircleGeometry(0.0075, 28), new T.MeshStandardMaterial({ map: zig, roughness: 0.5 }));
  zigM.rotation.y = Math.PI / 2; zigM.position.set(0.0015, 0.15, 0); cell.add(zigM);
  var cl = S.label('CdS cell', { w: 0.04, ratio: 0.3, color: '#2b2f36' }); cl.rotation.x = -Math.PI / 2;
  cl.position.set(X0, 0.0012, -0.21); S.scene.add(cl);

  // ---------------------------------------------------------------- the lamp on its sliding upright
  var lampG = new T.Group(); S.scene.add(lampG);
  var sad = S.rounded(0.034, 0.03, 0.07, 0.004, M.alu); sad.rotation.x = -Math.PI / 2; sad.position.y = 0.045; lampG.add(sad);
  var postM = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.1, 20), M.chrome); postM.position.y = 0.1; lampG.add(postM);
  var knobM = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.01, 6), M.black); knobM.rotation.x = Math.PI / 2; knobM.position.set(0, 0.045, 0.04); lampG.add(knobM);
  var holder = S.mesh(new T.CylinderGeometry(0.014, 0.016, 0.024, 24), M.bakelite); holder.position.y = 0.142; lampG.add(holder);
  var bulbM = new T.MeshStandardMaterial({ color: 0xf6f1df, roughness: 0.1, transparent: true, opacity: 0.55, emissive: 0x000000 });
  var bulb = S.mesh(new T.SphereGeometry(0.016, 24, 18), bulbM); bulb.position.y = 0.168; lampG.add(bulb);
  var fil = S.mesh(new T.TorusGeometry(0.004, 0.0006, 6, 16), new T.MeshStandardMaterial({ color: 0x6b5a2a, roughness: 0.4, emissive: 0x000000 }));
  fil.position.y = 0.166; fil.rotation.x = Math.PI / 2; lampG.add(fil);
  var glow = new T.PointLight(0xffe9b0, 0, 1.2); glow.position.set(0, 0.168, 0); lampG.add(glow);
  var lampShadow = S.contact(0.1, 0.1, 0, -0.3, 0.45);
  function placeLamp(d) { lampG.position.set(xOf(d), 0, -0.3); lampShadow.position.x = xOf(d); }
  placeLamp(st.d);
  var lampSupply = S.powerBox([0.46, 0, -0.56], 'LAMP SUPPLY 6 V');
  var lampRocker = lampSupply.userData.knob;

  // ---------------------------------------------------------------- the multimeter, reading ohms
  var mm = (function () {
    var g = new T.Group(); S.scene.add(g); g.position.set(0.12, 0, 0.0); g.rotation.y = -0.18;
    var W = 0.11, D = 0.15, H = 0.032;
    var body = S.rounded(W, D, H, 0.008, new T.MeshStandardMaterial({ color: 0xe0a93c, roughness: 0.55 }));
    body.rotation.x = -Math.PI / 2; body.position.y = H / 2; g.add(body);
    var faceP = S.mesh(new T.BoxGeometry(W - 0.01, 0.002, D - 0.01), M.bakelite); faceP.position.y = H + 0.001; g.add(faceP);
    var lcd = S.liveTex(512, 220), last = '';
    var scr = new T.Mesh(new T.PlaneGeometry(W - 0.024, 0.032), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
    scr.rotation.x = -Math.PI / 2; scr.position.set(0, H + 0.0025, -D / 2 + 0.03); g.add(scr);
    var bez = S.mesh(new T.BoxGeometry(W - 0.018, 0.003, 0.038), M.grey); bez.position.set(0, H + 0.0015, -D / 2 + 0.03); g.add(bez);
    var sel = new T.Group(); sel.position.set(0, H + 0.004, 0.014); g.add(sel);
    sel.add(S.mesh(new T.CylinderGeometry(0.016, 0.017, 0.008, 28), M.blackPlastic));
    var sp = S.mesh(new T.BoxGeometry(0.003, 0.002, 0.014), M.white, false); sp.position.set(0, 0.005, -0.008); sel.add(sp);
    [-0.024, 0.024].forEach(function (sx) { var sk = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.004, 16), sx < 0 ? M.blackPlastic : M.red);
      sk.position.set(sx, H + 0.001, D / 2 - 0.018); g.add(sk); });
    S.contact(W + 0.06, D + 0.06, 0.12, 0.0, 0.5);
    return { group: g, top: wpt(g, 0, H + 0.02, 0),
      show: function (txt, sub) { if (txt + sub === last) return; last = txt + sub;
        lcd.draw(function (c) { var gr = c.createLinearGradient(0, 0, 0, 220); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b');
          c.fillStyle = gr; c.fillRect(0, 0, 512, 220);
          c.font = '700 104px "JetBrains Mono", monospace'; c.textAlign = 'right'; c.fillStyle = 'rgba(0,0,0,.07)'; c.fillText('8.8.8.8.', 430, 130);
          c.fillStyle = '#1b2116'; c.fillText(txt, 430, 130);
          c.font = '600 40px "Public Sans", sans-serif'; c.textAlign = 'left'; c.fillText(sub, 20, 198);
          c.textAlign = 'right'; c.font = '600 28px "Public Sans", sans-serif'; c.fillText('OHMS', 492, 198); }); } };
  })();
  function lead(a, b, color, via) {
    var pts = [[a.x, a.y, a.z], [a.x, a.y + 0.02, a.z]];
    (via || []).forEach(function (v) { pts.push([v[0], 0.004, v[1]]); });
    pts.push([b.x, b.y + 0.02, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }
  lead(new T.Vector3(X0 - 0.01, 0.14, -0.3), mm.top, 'red', [[-0.3, -0.16], [0.0, -0.04]]);
  lead(new T.Vector3(X0 - 0.01, 0.13, -0.31), mm.top, 'black', [[-0.34, -0.1], [-0.06, 0.02]]);

  S.addApparatus('bench', bench, 'Optical bench', 'A printed scale in centimetres: the zero is at the cell, so the reading is the lamp\'s distance from it.');
  S.addApparatus('cell', cell, 'Light-dependent resistor (CdS cell)', 'A cadmium sulphide cell in a matt black hood, so only the light from the lamp reaches it. The more light, the lower its resistance.');
  S.addApparatus('lamp', lampG, 'Lamp on a sliding upright', 'A small filament lamp of fixed brightness. Slide it along the bench to change the illumination on the cell.');
  S.addApparatus('mm', mm.group, 'Digital multimeter (ohms)', 'Joined across the cell. It reads the cell\'s resistance directly.');
  S.addApparatus('psu', lampSupply, 'Lamp supply (6 V)', 'Keeps the lamp at one steady brightness throughout.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ---------------------------------------------------------------- physics
  function at(d) { var q = HK.assign(p, { d: d }); return KN.view(KN.init(q, q), q, q); }
  function R() { return st.lamp ? at(st.d).R_ldr : at(DMAX * 4).R_ldr; }
  function lux() { return st.lamp ? at(st.d).E_lux : 0; }
  function readR() { var r = R(); return r >= 10000 ? Math.round(r / 10) * 10 : Math.round(r); }
  function fmtR(r) { return r >= 1000 ? (r / 1000).toFixed(2) : String(Math.round(r)); }
  function unitR(r) { return r >= 1000 ? 'kilo-ohm' : 'ohm'; }
  var hudA = S.hudCard('Lamp distance'), hudB = S.hudCard('Cell resistance'), hudC = S.hudCard('Illumination');

  // ---------------------------------------------------------------- human actions
  function trace() {
    st.traced = true; S.focus('bench');
    S.say('The cell sits at the zero of the bench scale inside its black hood; the lamp slides along the bench. The multimeter, set to ohms, reads the cell\'s resistance directly.');
    S.render();
  }
  function setLamp(on) {
    if (busy()) return Promise.resolve();
    if (on === st.lamp) return Promise.resolve();
    return S.hand.tap(lampRocker, 'front').then(function () {
      st.lamp = on;
      bulbM.emissive = new T.Color(on ? 0xffdc8a : 0x000000); bulbM.emissiveIntensity = on ? 2.4 : 0;
      fil.material.emissive = new T.Color(on ? 0xffc14a : 0x000000); fil.material.emissiveIntensity = on ? 3 : 0;
      glow.intensity = on ? 0.9 : 0;
      S.click(900, 0.05); S.say(on ? 'The lamp is lit and the room is darkened: only this lamp lights the cell.' : 'Lamp off.');
      S.render();
    });
  }
  function moveLamp(d) {
    if (busy()) return Promise.resolve(false);
    if (!(d >= DMIN && d <= DMAX)) { S.say('Keep the lamp between ' + Math.round(DMIN * 100) + ' cm and ' + Math.round(DMAX * 100) + ' cm from the cell.'); return Promise.resolve(false); }
    d = rnd(d, 3);
    var d0 = st.d;
    return S.hand.pinchMove(new T.Vector3(xOf(d0), 0.1, -0.3), function (k) { return new T.Vector3(xOf(d0 + (d - d0) * k), 0.1, -0.3); },
      function (k) { st.d = d0 + (d - d0) * k; placeLamp(st.d); }, { mode: 'side', ms: 700 + 600 * Math.abs(d - d0), reachMs: 650 })
      .then(function () { st.d = d; placeLamp(d); S.say('Lamp at ' + Math.round(d * 100) + ' cm from the cell.'); S.render(); return true; });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.lamp) { S.say('Switch the lamp on first.'); return false; }
    var d = Math.round(st.d * 100);
    if (S.rows.some(function (r) { return Math.abs(r.d - d) < 2; })) { S.say('You already have a reading near ' + d + ' cm. Move the lamp further.'); return false; }
    S.addRow({ d: d, R: readR() });
    S.say('Written in your record book: d = ' + d + ' cm, R = ' + fmtR(readR()) + ' ' + unitR(readR()) + '.');
    return true;
  }

  function result(rows) {
    var pts = rows.map(function (r) { return [Math.log(r.d / 100), Math.log(r.R)]; })
      .filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); });
    if (pts.length < 4) return null;
    var f = S.fit.linear(pts);
    if (!f) return null;
    return { label: 'Exponent γ of the cell', value: f.m / 2, unit: '', digits: 3, truth: p.gamma,
      note: 'Slope of the log R against log d graph is 2γ, because the illumination falls as 1/d². Here the slope is ' + f.m.toFixed(3) + '.' };
  }

  return {
    camera: { pos: [-0.08, 0.98, 0.98], look: [-0.08, 0.05, -0.2] },
    views: { bench: [[-0.08, 0.92, 0.92], [-0.08, 0.05, -0.22]], cell: [[-0.42, 0.26, -0.02], [-0.5, 0.14, -0.3]],
      lamp: [[0.0, 0.3, 0.0], [-0.2, 0.14, -0.3]], mm: [[0.12, 0.26, 0.28], [0.12, 0.03, 0.0]],
      psu: [[0.46, 0.3, -0.24], [0.46, 0.06, -0.56]], book: [[-0.5, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A light-dependent resistor is a photoconductive cell: the light falling on it frees charge carriers, so the brighter the light the lower its resistance. A small lamp lights the cell with an illumination that falls as the square of the distance.',
      formula: 'R = A E^(−γ),  E = I / d²',
      formulaNote: 'so log R = constant + 2γ log d: the log-log plot is a straight line of slope 2γ',
      more: ['Because the lamp\'s brightness is fixed, moving it is the easiest way to change the light on the cell by a known factor: at twice the distance the illumination is a quarter.',
        'The cell must be shielded from every other light, which is why it sits in a black hood and the room is darkened: stray light would add a constant to E and bend the straight line.'],
      precautions: 'Keep the lamp\'s voltage the same all through, move the lamp by its upright and not by the hot bulb, and read the distance from the cell\'s face, not from the edge of its holder.' },
    book: { title: 'Expt. — Light-dependent resistor', at: [-0.5, 0.1, 0.1],
      lines: ['Aim: to study how the resistance of an LDR', 'depends on the light falling on it.',
        'Lamp of fixed brightness on an optical bench;', 'the cell at the zero of the scale, in a black hood.',
        'E = I / d²,  R = A E^(−γ)', 'log R against log d: slope = 2γ'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'd (cm)', get: function (r) { return r.d; } },
        { label: 'R (Ω)', get: function (r) { return r.R; } },
        { label: '1/d² (1/m²)', get: function (r) { return (10000 / (r.d * r.d)).toFixed(1); } }] },
    graph: { x: function (r) { return Math.log10(r.d); }, y: function (r) { return Math.log10(r.R); },
      xlabel: 'log d (d in cm)', ylabel: 'log R (R in Ω)',
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.02,
    resultNote: 'A straight line on log-log paper is the proof that R and E follow a power law; its slope is twice the exponent γ, which is about 0.8 for a cadmium sulphide cell.',
    chips: ['Why does the resistance fall in light?', 'Why plot logarithms?', 'Check my readings', 'Why must the room be dark?'],
    viva: [['As the light on an LDR grows, its resistance', ['Falls', 'Rises', 'Does not change'], 0,
      'Light frees charge carriers, so the cell conducts better.'],
      ['If the lamp is moved twice as far away, the illumination on the cell becomes', ['One quarter', 'One half', 'Twice'], 0,
        'The inverse-square law: E = I/d².'],
      ['Why is the cell kept in a black hood?', ['So that only the lamp\'s light reaches it', 'To keep it cool', 'To hold it upright'], 0,
        'Stray light would add to E and spoil the straight line.']],
    askState: function () {
      return { experiment: 'how the resistance of a light-dependent resistor depends on the light falling on it',
        lamp_on: st.lamp, lamp_distance_cm: Math.round(st.d * 100), cell_resistance_ohm: readR(),
        illumination_lux: +lux().toFixed(1), readings_taken: S.rows.length };
    },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Set up the bench');
          u.p('The cell sits at the zero of the bench scale, inside a black hood. The multimeter is already set to ohms and joined across it.');
          u.task('1. Trace the set-up', st.traced, st.traced ? 'Cell at zero, lamp on the slider, meter on ohms' : 'Follow the leads from the cell')
            .add(u.button(st.traced ? 'Traced' : 'Trace the set-up', trace, !st.traced, st.traced));
          u.task('2. Darken the room and light the lamp', st.lamp, st.lamp ? 'Lamp lit at a steady 6 V' : 'The lamp is off')
            .add(u.row(u.button(st.lamp ? 'Lamp is on' : 'Switch the lamp on', function () { S.focus('psu'); setLamp(true); }, !st.lamp, st.lamp || S.hand.busy),
              u.button('Lamp to 20 cm', function () { moveLamp(0.2); }, false, S.hand.busy)));
          u.live(function () { return st.lamp ? 'Multimeter ' + fmtR(readR()) + ' ' + (readR() >= 1000 ? 'kΩ' : 'Ω') + ' at ' + Math.round(st.d * 100) + ' cm' : 'Lamp off: the cell is dark and its resistance is very high'; });
          u.note('The lamp must stay at the same brightness for every reading, or the comparison means nothing.');
          u.next('Next: take the readings', st.traced && st.lamp);
        },
        ok: function () { return st.traced && st.lamp; },
        auto: function () { trace(); return setLamp(true).then(function () { return moveLamp(0.2); }); } },
      { id: 'read', title: 'Readings', view: 'bench', render: function (u) {
          u.h2('Move the lamp and read the resistance');
          u.p('Take readings at 10, 15, 20, 30, 40 and 50 cm. Each time let the hand slide the lamp, then read the multimeter.');
          var tg = { v: Math.round(st.d * 100) };
          u.slider('Lamp distance', Math.round(DMIN * 100), Math.round(DMAX * 100), 1, function () { return tg.v; }, function (v) { tg.v = v; }, 'cm', 0);
          u.row(u.button('Slide the lamp here', function () { moveLamp(tg.v / 100); }, true, S.hand.busy),
            u.button('Record d and R', function () { record(); }, false, S.hand.busy));
          u.live(function () { return 'Lamp at ' + Math.round(st.d * 100) + ' cm  ·  multimeter ' + fmtR(readR()) + ' ' + (readR() >= 1000 ? 'kΩ' : 'Ω') + '  ·  illumination ' + lux().toFixed(1) + ' lux'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 5) u.p(S.rows.length + ' of at least 5 readings recorded.');
          u.next('Next: the result', S.rows.length >= 5);
        },
        ok: function () { return S.rows.length >= 5; },
        auto: function () {
          return [0.1, 0.15, 0.2, 0.3, 0.4, 0.5].reduce(function (pr, d) {
            return pr.then(function () { return moveLamp(d); }).then(function () { record(); }); }, Promise.resolve());
        } },
    ],
    tick: function () {
      mm.show(st.lamp ? fmtR(readR()) : '----', st.lamp ? (readR() >= 1000 ? 'k ohm' : 'ohm') : '');
      hudA.set(Math.round(st.d * 100) + ' cm');
      hudB.set(st.lamp ? fmtR(readR()) + (readR() >= 1000 ? ' kΩ' : ' Ω') : '—');
      hudC.set(st.lamp ? lux().toFixed(1) + ' lx' : 'dark');
    },
  };
});
