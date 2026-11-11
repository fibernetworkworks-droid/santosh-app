/* Prayogshala studio rig: Young's modulus of a wire by the optical lever method (B.Sc. Mechanics lab).
   Physics: the shipped `searle` kernel (mech11 pack): a wire of length L and diameter d stretched by the load m, the
   same numbers the server checks. The extension tilts an optical lever (front leg on the wire's chuck, hind legs on a
   fixed platform z behind); a telescope and scale D away read the shift s = D tan(2 atan(e / z)). z and D are fixed
   dimensions of this rig. The hidden knob Y (the wire) is what the student measures. */
HoolaStudio.define('w7-optical-lever', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.searle, PI = Math.PI;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('searle'); p.m = 0;
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var MAT = /brass/i.test(SAMPLE) ? { name: 'brass', m: M.brass } : /copper/i.test(SAMPLE) ? { name: 'copper', m: M.copper } : { name: 'steel', m: M.steel };
  var ZL = 0.040, D = 1.000, S0 = 0.200;                 // lever leg (m), mirror-to-scale distance (m), scale reading with no load (m)
  var st = { dims: false, mSet: 0, speed: 1 };
  var sim = K.init(p);
  var WX = 0.72, ZB = -0.4, H = 1.28;
  function box(w, h, d, mat) { return S.mesh(new T.BoxGeometry(w, h, d), mat); }
  function cyl(r, h, mat, seg) { return S.mesh(new T.CylinderGeometry(r, r, h, seg || 24), mat); }
  function put(o, x, y, z, parent) { o.position.set(x, y, z); (parent || S.scene).add(o); return o; }
  function rnd(v, lc) { return Math.round(v / lc) * lc; }

  // ---------- frame, wire, chuck, hanger
  var frame = new T.Group(); S.scene.add(frame);
  [WX - 0.2, WX + 0.2].forEach(function (x) { var b = S.rounded(0.12, 0.16, 0.02, 0.006, M.iron); b.rotation.x = -PI / 2; b.position.set(x, 0.01, ZB); frame.add(b); var r = cyl(0.009, H, M.chrome); r.position.set(x, H / 2 + 0.015, ZB); frame.add(r); S.contact(0.18, 0.22, x, ZB, 0.5); });
  var beam = box(0.46, 0.025, 0.03, M.alu); beam.position.set(WX, H + 0.012, ZB); frame.add(beam);
  var topChuck = cyl(0.008, 0.025, M.brass); put(topChuck, WX, H - 0.012, ZB);
  var WL = 0.96, CY = H - 0.025 - WL;                     // drawn wire length and the height of the lower chuck's top
  var wire = cyl(0.0012, WL, MAT.m, 10); put(wire, WX, H - 0.025 - WL / 2, ZB);
  var low = new T.Group(); low.position.set(WX, CY, ZB); S.scene.add(low);
  var chuck = cyl(0.011, 0.03, M.brass); chuck.position.y = -0.015; low.add(chuck);
  var shelf = cyl(0.022, 0.003, M.brass, 32); shelf.position.set(0.012, -0.004, 0); low.add(shelf);
  var hrod = cyl(0.0025, 0.09, M.steel, 10); hrod.position.y = -0.075; low.add(hrod);
  var pan = cyl(0.045, 0.006, M.iron, 40); pan.position.y = -0.12; low.add(pan);
  var discs = []; for (var i = 0; i < 6; i++) { var dsc = cyl(0.045, 0.011, i % 2 ? M.iron : M.brass, 40); dsc.position.y = -0.117 + 0.0085 + i * 0.0115; dsc.visible = false; low.add(dsc); discs.push(dsc); }
  var spare = cyl(0.045, 0.011, M.iron, 40); put(spare, WX + 0.02, 0.0055, ZB + 0.22); var spare2 = cyl(0.045, 0.011, M.brass, 40); put(spare2, WX + 0.02, 0.017, ZB + 0.22); S.contact(0.14, 0.14, WX + 0.02, ZB + 0.22, 0.45);
  // ---------- fixed platform and the optical lever
  var pf = new T.Group(); S.scene.add(pf); var pb = S.rounded(0.1, 0.08, 0.016, 0.006, M.iron); pb.rotation.x = -PI / 2; pb.position.set(WX + 0.09, 0.008, ZB + 0.07); pf.add(pb);
  var pr = cyl(0.006, CY - 0.02, M.chrome); pr.position.set(WX + 0.09, (CY - 0.02) / 2 + 0.012, ZB + 0.07); pf.add(pr);
  var table = box(0.06, 0.006, 0.09, M.alu); table.position.set(WX + 0.075, CY - 0.0075, ZB + 0.03); pf.add(table); S.contact(0.14, 0.12, WX + 0.09, ZB + 0.07, 0.45);
  var lever = new T.Group(); lever.position.set(WX + 0.012 + ZL, CY - 0.001, ZB); S.scene.add(lever);     // pivots on its hind legs
  var plate = box(ZL + 0.014, 0.003, 0.03, M.brass); plate.position.set(-ZL / 2, 0.006, 0); lever.add(plate);
  [[-ZL, 0], [0, -0.011], [0, 0.011]].forEach(function (q) { var leg = S.mesh(new T.ConeGeometry(0.0025, 0.008, 10), M.steel); leg.rotation.x = PI; leg.position.set(q[0], 0.003, q[1]); lever.add(leg); });
  var mirror = box(0.0015, 0.034, 0.026, M.chrome); mirror.position.set(-ZL / 2, 0.025, 0); lever.add(mirror);
  // ---------- telescope and scale, D away
  var TX = WX - 0.012 - D + ZL / 2, tel = new T.Group(); S.scene.add(tel);
  var tb = S.rounded(0.16, 0.12, 0.02, 0.008, M.iron); tb.rotation.x = -PI / 2; tb.position.set(TX, 0.01, ZB); tel.add(tb); S.contact(0.22, 0.18, TX, ZB, 0.5);
  var tr = cyl(0.007, 0.6, M.chrome); tr.position.set(TX, 0.31, ZB); tel.add(tr);
  var tube = cyl(0.014, 0.2, M.brass, 32); tube.rotation.z = PI / 2; tube.position.set(TX + 0.03, CY + 0.02, ZB); tel.add(tube);
  var eye = cyl(0.01, 0.05, M.black, 24); eye.rotation.z = PI / 2; eye.position.set(TX - 0.09, CY + 0.02, ZB); tel.add(eye);
  var obj = cyl(0.017, 0.02, M.black, 32); obj.rotation.z = PI / 2; obj.position.set(TX + 0.135, CY + 0.02, ZB); tel.add(obj);
  var ruler = S.ruler(0.5, { title: 'cm · LC 1 mm', labelEvery: 10 }); ruler.rotation.y = PI / 2; ruler.position.set(TX + 0.01, CY + 0.07, ZB + 0.03);
  var rcl = box(0.03, 0.02, 0.04, M.alu); rcl.position.set(TX, CY + 0.09, ZB + 0.015); tel.add(rcl);
  var lamp = S.rounded(0.05, 0.05, 0.05, 0.008, M.black); lamp.position.set(TX + 0.07, CY + 0.34, ZB + 0.1); tel.add(lamp); var lpost = cyl(0.004, CY + 0.32, M.chrome); lpost.position.set(TX + 0.07, (CY + 0.32) / 2, ZB + 0.1); tel.add(lpost);
  var screw = new T.Group(); S.scene.add(screw); var sg1 = box(0.09, 0.012, 0.014, M.steel); screw.add(sg1); var sg2 = cyl(0.008, 0.05, M.chrome); sg2.rotation.z = PI / 2; sg2.position.x = 0.07; screw.add(sg2); screw.position.set(0.1, 0.008, 0.12); screw.rotation.y = 0.4; S.contact(0.18, 0.06, 0.11, 0.12, 0.4);

  S.addApparatus('frame', frame, 'Rigid frame', 'The wire hangs from a heavy frame that must not sag when the load is added.');
  S.addApparatus('wire', wire, MAT.name.charAt(0).toUpperCase() + MAT.name.slice(1) + ' wire', 'The experimental wire: length L = ' + (p.L * 100).toFixed(1) + ' cm from chuck to chuck, diameter ' + (p.d * 1000).toFixed(3) + ' mm.');
  S.addApparatus('hanger', low, 'Lower chuck and hanger', 'The chuck grips the lower end of the wire and carries the hanger. Each slotted mass is 0.5 kg.');
  S.addApparatus('lever', lever, 'Optical lever', 'A small plate on three legs with an upright mirror. The front leg rests on the chuck, the two hind legs on the fixed platform ' + (ZL * 100).toFixed(2) + ' cm behind.');
  S.addApparatus('pf', pf, 'Fixed platform', 'Carries the hind legs of the lever. It does not move when the wire stretches.');
  S.addApparatus('tel', tel, 'Telescope, scale and lamp', 'The telescope looks at the image of the lit vertical scale in the lever\'s mirror. The scale is ' + (D * 100).toFixed(1) + ' cm from the mirror.');
  S.addApparatus('screw', screw, 'Screw gauge', 'Measures the diameter of the wire. Least count 0.01 mm.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var hud1 = S.hudCard('Scale in the telescope'), hud2 = S.hudCard('Load');

  function target() { return p.m * p.g * p.L / (PI * p.d * p.d / 4 * p.Y); }
  function settled() { return Math.abs(sim.e - target()) < 2e-7; }
  function scaleNow() { return S0 + D * Math.tan(2 * Math.atan(sim.e / ZL)); }
  var DIMS = 'Wire: L = ' + (p.L * 100).toFixed(1) + ' cm (metre scale), diameter ' + (p.d * 1000).toFixed(3) + ' mm (screw gauge, mean of several places), r = ' + (p.d * 500).toFixed(4) + ' mm. Lever leg z = ' + (ZL * 100).toFixed(2) + ' cm. Mirror to scale D = ' + (D * 100).toFixed(1) + ' cm.';
  function measure() { if (st.dims) return; st.dims = true; S.say(DIMS + ' Written in your record book.'); S.focus('screw'); S.book.draw(); S.render(); }
  function load() { if (S.hand.busy) return Promise.resolve(); if (!st.dims) { S.say('Measure the wire and the lever first.'); return Promise.resolve(); }
    return S.hand.tap(pan).then(function () { p.m = st.mSet; var n = Math.round(p.m / 0.5); discs.forEach(function (d, i) { d.visible = i < n; }); S.click(1600); S.say('Load ' + p.m.toFixed(1) + ' kg. Wait for the wire to settle, then read the telescope.'); S.render(); }); }
  function read() { if (!st.dims) { S.say('Measure the wire and the lever first.'); return; } if (!settled()) { S.say('The image is still creeping. Wait for the wire to settle.'); return; }
    var r = { m: p.m, s: rnd(scaleNow() * 100, 0.1) }; S.addRow(r); S.say('Load ' + r.m.toFixed(1) + ' kg: the cross-wire is on ' + r.s.toFixed(1) + ' cm.'); }
  function slope(rows) { var f = S.fit.linear(rows.map(function (r) { return [r.m, r.s / 100]; })); return f ? f.m : null; }
  function loads(rows) { var o = {}; rows.forEach(function (r) { o[r.m] = 1; }); return Object.keys(o).length; }

  return {
    camera: { pos: [0.25, 0.85, 1.75], look: [0.22, 0.5, ZB] },
    views: { main: [[0.25, 0.8, 1.65], [0.22, 0.5, ZB]], frame: [[WX + 0.3, 0.9, 1.0], [WX, 0.7, ZB]], wire: [[WX + 0.2, 0.8, 0.4], [WX, 0.7, ZB]], hanger: [[WX + 0.15, 0.35, 0.1], [WX, 0.2, ZB]],
      lever: [[WX - 0.02, 0.36, -0.2], [WX + 0.03, CY, ZB]], pf: [[WX + 0.2, 0.4, 0.0], [WX + 0.08, CY - 0.05, ZB]], tel: [[TX + 0.2, 0.55, 0.3], [TX, 0.35, ZB]], screw: [[0.15, 0.25, 0.4], [0.1, 0.0, 0.12]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: S.lab.theory, formula: 'Y = M g L / (π r² e),   e = s z / (2 D)', formulaNote: 's: shift of the scale reading; z: leg of the lever; D: mirror to scale. With the slope of s against M:  Y = 2 D g L / (π r² z × slope).',
      more: [S.lab.aim], precautions: S.lab.safety + ' Add the masses gently and wait before each reading. Read while loading and again while unloading. Measure the diameter at several places: it enters as r².' },
    book: { title: 'Expt. — Young\'s modulus (optical lever)', lines: ['Aim: Y of ' + MAT.name + ' by the optical lever method.', 'L = ' + (p.L * 100).toFixed(1) + ' cm,  r = ' + (p.d * 500).toFixed(4) + ' mm', 'z = ' + (ZL * 100).toFixed(2) + ' cm,  D = ' + (D * 100).toFixed(1) + ' cm', 'e = s z / (2D),   Y = M g L / (π r² e)'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'Load M (kg)', get: function (r) { return r.m.toFixed(1); } }, { label: 'Scale (cm)', get: function (r) { return r.s.toFixed(1); } },
        { label: 'Shift s (cm)', get: function (r) { return (r.s - S.rows[0].s).toFixed(1); } }, { label: 'e (mm)', get: function (r) { return ((r.s - S.rows[0].s) / 100 * ZL / (2 * D) * 1000).toFixed(3); } }] },
    graph: { x: function (r) { return r.m; }, y: function (r) { return r.s; }, xlabel: 'Load M (kg)', ylabel: 'Scale reading (cm)', line: function (pts) { var f = S.fit.linear(pts); return function (x) { return f.m * x + f.c; }; } },
    result: function (rows) { if (loads(rows) < 3) return null; var sl = slope(rows); if (!sl || sl <= 0) return null; var ePerKg = sl * ZL / (2 * D), Y = p.g * p.L / (PI * p.d * p.d / 4 * ePerKg);
      return { label: 'Y (' + MAT.name + ')', value: Y / 1e9, unit: 'GPa', digits: 0, truth: p.Y / 1e9, note: 'Slope of the scale reading against load: ' + (sl * 100).toFixed(3) + ' cm/kg, so the wire stretches ' + (ePerKg * 1000).toFixed(4) + ' mm per kg. The lever magnifies ' + (2 * D / ZL).toFixed(0) + ' times.' }; },
    tol: 0.04,
    chips: ['How does the optical lever magnify?', 'Why read while unloading too?', 'Check my readings', 'Why is my Y different?'],
    viva: [['If the mirror turns through a small angle θ, the reflected ray turns through', ['2θ', 'θ', 'θ/2'], 0, 'The angle of incidence and the angle of reflection both change by θ.']],
    askState: function () { return { wire: MAT.name, load_kg: p.m, scale_reading_cm: +(scaleNow() * 100).toFixed(1), settled: settled(), readings: S.rows.length, lever_leg_cm: ZL * 100, scale_distance_cm: D * 100 }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'main', render: function (u) { u.h2('Measure the wire and the lever');
          u.p('The extension will be found from the scale shift, so the lever\'s leg and the scale distance are needed as well as the wire\'s length and diameter.');
          u.task('Measure L, the diameter, z and D', st.dims, st.dims ? DIMS : 'Metre scale, screw gauge, and the lever\'s legs pressed on paper')
            .add(u.button(st.dims ? 'Measured' : 'Measure', measure, !st.dims, st.dims));
          if (SAMPLE) u.note('Sample: ' + SAMPLE + '.');
          u.next('Next: load the wire', st.dims); },
        ok: function () { return st.dims; }, auto: function () { measure(); return Promise.resolve(); } },
      { id: 'load', title: 'Readings', view: 'hanger', render: function (u) { u.h2('Load the wire, read the telescope');
          u.slider('Load on the hanger', 0, 3, 0.5, function () { return st.mSet; }, function (v) { st.mSet = v; }, 'kg');
          u.row(u.button('Put this load on the hanger', function () { load(); }, true, S.hand.busy), u.button('Read the scale in the telescope', read, false, false), u.button('Look through the telescope', function () { S.focus('tel'); }, false, false));
          u.live(function () { return 'Load ' + p.m.toFixed(1) + ' kg · cross-wire on ' + (scaleNow() * 100).toFixed(1) + ' cm · ' + (settled() ? 'settled' : 'creeping'); });
          u.h3('Observation table'); u.table(); if (loads(S.rows) < 5) u.p(loads(S.rows) + ' of at least 5 different loads read (include no load).');
          u.next('Next: work out Y', loads(S.rows) >= 5); },
        ok: function () { return loads(S.rows) >= 5; },
        auto: function () { return [0, 0.5, 1, 1.5, 2, 2.5, 3].reduce(function (pr, m) { return pr.then(function () { st.mSet = m; return load(); }).then(function () { S.advance(20, settled); read(); }); }, Promise.resolve()); } },
    ],
    tick: function (dt) { K.step(sim, p, dt); low.position.y = CY - sim.e * 10; lever.rotation.z = Math.atan(sim.e * 10 / ZL);      // the stretch and the tilt are drawn ten times larger than life so they can be seen
      hud1.set((scaleNow() * 100).toFixed(1) + ' cm'); hud2.set(p.m.toFixed(1) + ' kg'); },
  };
});
