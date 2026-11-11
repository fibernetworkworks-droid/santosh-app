/* Prayogshala studio rig: the B.Sc. oscillation bench (pack ug_mech_w7). One rig, one procedure, eleven set-ups:
     w7_pend     a simple pendulum with a card vane, a bar pendulum with a damper vane (decay of the amplitude),
                 a bar pendulum timed at larger and larger amplitudes, a bar pendulum read by an Arduino photo-gate
     w7_kater    Kater's reversible pendulum (timed about both knife edges)
     w7_coupled  two pendulums joined by a spring, or two gliders and three springs on an air track
     w7_spring   a loaded helical spring, alone, in series or in parallel (extension, then period)
     w7_torsion  Maxwell's needle, or Searle's two bars joined by a wire
   The student sets the apparatus, the gloved hand displaces and releases it, and a run either times N oscillations
   (the stopwatch starts and stops as the body passes its rest position), reads the falling amplitude every few
   oscillations, or times the beats. Every number comes from the lab's own kernel and params; the hidden knob (a damper,
   a spring, a wire, the local g) is what the student measures. */
HoolaStudio.define('w7-oscillation-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = S.lab.kernel, K = HK.K[KN], PI = Math.PI, DEG = PI / 180;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams(KN);
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var st = { dims: false, running: false, speed: 1, sel: 0, run: null, armed: false, n: 0, t0: 0, stat: null, pk: [], mins: [], k: 0, released: false, lcd: '' };
  var sim = K.init(p); sim.y = sim.y.map(function () { return 0; });
  var UP = new T.Vector3(0, 1, 0), DOWN = new T.Vector3(0, -1, 0);
  var X0 = 0.15, Z0 = -0.36;

  // ------------------------------------------------------------------ small builders
  function cyl(r, h, mat, seg) { return S.mesh(new T.CylinderGeometry(r, r, h, seg || 24), mat); }
  function box(w, h, d, mat) { return S.mesh(new T.BoxGeometry(w, h, d), mat); }
  function put(o, x, y, z, parent) { o.position.set(x, y, z); (parent || S.scene).add(o); return o; }
  function rodBetween(mesh, a, b) { var d = b.clone().sub(a), len = d.length(); mesh.position.copy(a).add(b).multiplyScalar(0.5); mesh.scale.set(1, len, 1); mesh.quaternion.setFromUnitVectors(UP, d.normalize()); }
  function helix(R, turns, wire) { var pts = [], n = turns * 14, i, a; for (i = 0; i <= n; i++) { a = 2 * PI * turns * i / n; pts.push(new T.Vector3(R * Math.cos(a), -i / n, R * Math.sin(a))); }
    var m = S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts), n * 2, wire, 6, false), M.steel, true, false); S.scene.add(m); return m; }
  function stretch(h, a, b) { var d = b.clone().sub(a), len = d.length(); h.position.copy(a); h.scale.set(1, len, 1); h.quaternion.setFromUnitVectors(DOWN, d.normalize()); }
  function mmStrip(widthM, title) {   // a white scale, zero at the centre, 1 mm divisions, numbered in cm
    var mm = Math.round(widthM * 1000), W = Math.min(4096, mm * 5), H = 150;
    var tex = S.canvasTex(W, H, function (x) { x.fillStyle = '#f4f1e6'; x.fillRect(0, 0, W, H); x.fillStyle = '#16181b'; x.font = '600 30px "Public Sans", sans-serif'; x.textAlign = 'center';
      for (var i = 0; i <= mm; i++) { var px = i * W / mm, d = Math.abs(i - mm / 2), len = d % 10 === 0 ? 60 : d % 5 === 0 ? 42 : 26; x.fillRect(px - 1, 0, 2, len); if (d % 10 === 0) x.fillText(String(d / 10), px, 96); }
      x.font = '600 22px "Public Sans", sans-serif'; x.fillText(title || 'cm', W / 2, 136); });
    var g = new T.Group(); var b = box(widthM + 0.02, 0.034, 0.004, M.white); g.add(b);
    var f = new T.Mesh(new T.PlaneGeometry(widthM, 0.03), new T.MeshStandardMaterial({ map: tex, roughness: 0.6 })); f.position.z = 0.0022; g.add(f); S.scene.add(g); return g; }
  function post(x, z, h) { var g = new T.Group(); S.scene.add(g); var b = S.rounded(0.09, 0.07, 0.016, 0.006, M.iron); b.rotation.x = -PI / 2; b.position.set(x, 0.008, z); g.add(b);
    var r = cyl(0.005, h, M.chrome); r.position.set(x, h / 2 + 0.012, z); g.add(r); S.contact(0.14, 0.11, x, z, 0.45); return g; }
  function frame(x1, x2, z, h) { var g = new T.Group(); S.scene.add(g);
    [x1, x2].forEach(function (x) { var b = S.rounded(0.12, 0.14, 0.02, 0.006, M.iron); b.rotation.x = -PI / 2; b.position.set(x, 0.01, z); g.add(b); var r = cyl(0.008, h, M.chrome); r.position.set(x, h / 2 + 0.015, z); g.add(r); S.contact(0.18, 0.2, x, z, 0.5); });
    var beam = box(x2 - x1 + 0.06, 0.022, 0.022, M.alu); beam.position.set((x1 + x2) / 2, h + 0.01, z); g.add(beam); return g; }
  function carryTap(obj) { return S.hand.busy ? Promise.resolve() : S.hand.tap(obj); }

  var watch = S.stopwatch([0.6, 0.035, 0.14], [-1.15, 0, -0.25]);
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Least count 0.01 s. It is started and stopped as the body passes its rest position.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var hudA, hudB, hudC;

  function mean(xs) { return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : NaN; }
  function timeRows(rows, sel) { return rows.filter(function (r) { return r.type === 'time' && (sel === undefined || r.sel === sel); }); }
  function meanT(rows, sel) { return mean(timeRows(rows, sel).map(function (r) { return r.T; })); }
  function decayGamma(rows) { var d = rows.filter(function (r) { return r.type === 'decay'; }); if (d.length < 3) return null; var a0 = d[0].A;
    var f = S.fit.linear(d.map(function (r) { return [r.t, Math.log(a0 / r.A)]; })); return f ? f.m : null; }
  function colN(lbl, fn) { return { label: lbl, get: fn }; }
  var COL_NO = colN('S.No', function (r, i) { return i + 1; });
  function timeCols(first) { return [COL_NO, first, colN('n', function (r) { return r.type === 'time' ? String(r.n) : '—'; }), colN('t (s)', function (r) { return r.type === 'time' ? r.t.toFixed(L.tDigits || 2) : '—'; }),
    colN('T (s)', function (r) { return r.type === 'time' ? r.T.toFixed(L.TDigits || 3) : (r.type === 'beat' ? r.Tb.toFixed(1) : '—'); })]; }
  var decayCols = [COL_NO, colN('n', function (r) { return String(r.n); }), colN('t (s)', function (r) { return r.t.toFixed(1); }), colN('A (mm)', function (r) { return r.A.toFixed(1); }),
    colN('ln(A0/A)', function (r) { var a0 = S.rows.length ? S.rows[0].A : r.A; return Math.log(a0 / r.A).toFixed(3); })];

  // ================================================================== the set-ups
  var L;                                               // the lab-specific description, filled by one of the builders

  // ------------------------------------------------------------------ pendulums on a stand (w7_pend, w7_kater)
  function buildPendulum() {
    var kater = KN === 'w7_kater', bar = !kater && p.kind > 0.5, damp = !kater && p.mode > 0.5 && p.mode < 1.5, limit = !kater && p.mode > 1.5, gate = bar && p.mode < 0.5;
    var stand = S.stand({ x: X0, z: Z0, armY: 1.16, h: 1.25, armLen: 0.22 }), jaw = stand.userData.jaw;
    var PIV = new T.Vector3(jaw.x, 1.13, Z0 + 0.05);
    var br = box(0.03, 0.02, 0.07, M.brass); put(br, jaw.x, 1.142, Z0 + 0.03);
    var swing = new T.Group(); swing.position.copy(PIV); S.scene.add(swing);
    var tip = new T.Object3D(); swing.add(tip);
    var Rs, body, vane, gateG, lcdTex, bobName;
    if (kater) {
      body = new T.Group(); swing.add(body);
      var rod = cyl(0.007, 1.2, M.brass); rod.position.y = 0.1; body.add(rod);
      [[p.h1, 1], [-p.h2, -1]].forEach(function (k) { var ke = S.mesh(new T.CylinderGeometry(0.0005, 0.012, 0.018, 3), M.steel); ke.rotation.x = PI / 2; ke.rotation.z = k[1] > 0 ? PI : 0; ke.scale.z = 2.4; ke.position.set(0, k[0] + k[1] * -0.009, 0); body.add(ke); });
      var w1 = cyl(0.035, 0.06, M.brass, 40); w1.position.y = -0.46; body.add(w1);
      var w2 = cyl(0.035, 0.06, M.wood, 40); w2.position.y = 0.66; body.add(w2);
      var w3 = cyl(0.018, 0.03, M.steel, 30); w3.position.y = 0.12; body.add(w3);
      [['K1', p.h1 - 0.04], ['K2', -p.h2 + 0.04]].forEach(function (k) { var l = S.label(k[0], { w: 0.03, ratio: 0.5, color: '#3a2a08', bg: '#f1e6c0' }); l.position.set(0.03, k[1], 0.008); body.add(l); });
      Rs = 0; bobName = 'Kater\'s pendulum';
    } else if (bar) {
      var holeTex = S.canvasTex(64, 1280, function (x, w, h) { x.fillStyle = '#c9ced2'; x.fillRect(0, 0, w, h); x.fillStyle = '#23272b'; for (var i = 1; i < 20; i++) { x.beginPath(); x.arc(w / 2, h * i / 20, 9, 0, 2 * PI); x.fill(); } });
      body = S.mesh(new T.BoxGeometry(0.032, p.Lb, 0.005), new T.MeshStandardMaterial({ map: holeTex, roughness: 0.3, metalness: 0.8 })); swing.add(body);
      var ke2 = S.mesh(new T.CylinderGeometry(0.0005, 0.01, 0.016, 3), M.steel); ke2.rotation.x = PI / 2; ke2.rotation.z = PI; ke2.scale.z = 3; ke2.position.set(0, 0.006, 0); swing.add(ke2);
      if (damp) { var side = Math.max(0.045, Math.min(0.1, 0.05 + (p.gam - 0.010) / 0.018 * 0.04)); vane = S.mesh(new T.BoxGeometry(0.0015, side, side), M.alu); swing.add(vane); vane.userData.side = side; }
      bobName = 'Bar pendulum';
    } else {
      var thr = cyl(0.0007, p.L - 0.02, M.thread, 8); thr.position.y = -(p.L - 0.02) / 2; swing.add(thr);
      var bob = S.mesh(new T.SphereGeometry(0.02, 48, 32), M.brass); bob.position.y = -p.L; swing.add(bob);
      vane = S.mesh(new T.BoxGeometry(0.001, 0.08, 0.06), M.paper); vane.position.y = -p.L + 0.075; swing.add(vane);
      var ptr = cyl(0.0008, 0.03, M.black, 8); ptr.position.y = -p.L - 0.033; swing.add(ptr);
      S.cork(new T.Vector3(PIV.x, PIV.y + 0.014, PIV.z)); bobName = 'Brass bob with a card vane';
    }
    // the scale behind the pointer (decay runs), the protractor (amplitude runs), the photo-gate
    var strip = null, prot = null, stripPost = null;
    if (damp) { strip = mmStrip(0.44, 'cm from the rest position'); stripPost = post(PIV.x, PIV.z - 0.03, 0.3); }
    if (limit) {
      var protTex = S.canvasTex(1024, 560, function (x, w) { var cx = w / 2, cy = 30, R = 480; x.fillStyle = 'rgba(225,240,255,0.2)'; x.beginPath(); x.moveTo(cx - R, cy); x.arc(cx, cy, R, 0, PI); x.closePath(); x.fill();
        x.strokeStyle = 'rgba(15,35,65,.92)'; x.fillStyle = 'rgba(15,35,65,.95)'; x.font = '600 22px "Public Sans", sans-serif'; x.textAlign = 'center';
        for (var d = 0; d <= 180; d++) { var a = PI * d / 180, len = d % 10 === 0 ? 40 : d % 5 === 0 ? 26 : 14; x.lineWidth = d % 10 === 0 ? 2.4 : 1.2; x.beginPath(); x.moveTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); x.lineTo(cx + Math.cos(a) * (R - len), cy + Math.sin(a) * (R - len)); x.stroke();
          if (d % 10 === 0 && d && d !== 180) x.fillText(String(Math.abs(90 - d)), cx + Math.cos(a) * (R - 64), cy + Math.sin(a) * (R - 64) + 8); } });
      prot = new T.Mesh(new T.PlaneGeometry(0.4, 0.219), new T.MeshStandardMaterial({ map: protTex, transparent: true, roughness: 0.1, side: T.DoubleSide, depthWrite: false }));
      prot.position.set(PIV.x, PIV.y - 0.104, PIV.z + 0.012); prot.scale.y = -1; prot.renderOrder = 3; S.scene.add(prot);
    }
    if (gate) {
      gateG = new T.Group(); S.scene.add(gateG);
      var gb = box(0.05, 0.02, 0.09, M.black); gateG.add(gb);
      [-0.035, 0.035].forEach(function (z) { var pr = box(0.02, 0.07, 0.016, M.black); pr.position.set(0, 0.045, z); gateG.add(pr); });
      var led = cyl(0.003, 0.004, M.red, 12); led.rotation.x = PI / 2; led.position.set(0, 0.06, -0.026); gateG.add(led);
      var gp = cyl(0.005, 1, M.chrome); gateG.userData.rod = gp; S.scene.add(gp);
      var gbase = S.rounded(0.1, 0.08, 0.016, 0.006, M.iron); gbase.rotation.x = -PI / 2; gbase.position.set(PIV.x, 0.008, PIV.z); S.scene.add(gbase); S.contact(0.15, 0.12, PIV.x, PIV.z, 0.45);
      var AX = PIV.x + 0.42, AZ = -0.05;
      var pcb = S.rounded(0.11, 0.075, 0.012, 0.004, new T.MeshStandardMaterial({ color: 0x0b6e73, roughness: 0.5 })); pcb.rotation.x = -PI / 2; pcb.position.set(AX, 0.006, AZ); S.scene.add(pcb);
      var chip = box(0.035, 0.006, 0.012, M.black); put(chip, AX + 0.01, 0.015, AZ + 0.012);
      var usb = box(0.014, 0.011, 0.016, M.steel); put(usb, AX - 0.05, 0.0175, AZ - 0.02);
      var an = S.label('ARDUINO UNO', { w: 0.05, ratio: 0.2, color: '#e8f6f6' }); an.rotation.x = -PI / 2; an.position.set(AX + 0.01, 0.0125, AZ + 0.028); S.scene.add(an);
      lcdTex = S.liveTex(512, 160);
      var lcdB = S.rounded(0.09, 0.04, 0.012, 0.003, new T.MeshStandardMaterial({ color: 0x1b3c8a, roughness: 0.5 })); lcdB.position.set(AX, 0.045, AZ - 0.05); lcdB.rotation.x = -0.5; S.scene.add(lcdB);
      var lcd = new T.Mesh(new T.PlaneGeometry(0.078, 0.026), new T.MeshBasicMaterial({ map: lcdTex, toneMapped: false })); lcd.position.set(AX, 0.0452 + 0.0035, AZ - 0.05 + 0.0058); lcd.rotation.x = -0.5; S.scene.add(lcd);
      var lcdLeg = box(0.08, 0.03, 0.006, M.black); put(lcdLeg, AX, 0.02, AZ - 0.062);
      S.contact(0.18, 0.16, AX, AZ - 0.02, 0.45);
      gateG.userData.wire = S.wire([[PIV.x + 0.03, 0.2, PIV.z], [AX - 0.02, 0.014, AZ + 0.03]], 'black');
      S.addApparatus('gate', gateG, 'Photo-gate', 'An infrared LED faces a photo-transistor across the gap. The lower end of the bar cuts the beam twice in every oscillation.');
      S.addApparatus('ard', pcb, 'Arduino with LCD', 'Times every second cut of the beam with its microsecond clock and shows the mean of ten periods.');
    }
    function drawLcd(txt) { if (!lcdTex || st.lcd === txt) return; st.lcd = txt; lcdTex.draw(function (x) { x.fillStyle = '#7fd04a'; x.fillRect(0, 0, 512, 160); x.fillStyle = '#14300a'; x.font = '700 54px "JetBrains Mono", monospace'; x.textAlign = 'left'; x.fillText('PERIOD (10 avg)', 16, 62); x.fillText(txt, 16, 132); }); }
    function layout() {
      if (kater) { var flip = p.side > 0.5; body.rotation.z = flip ? PI : 0; body.position.y = flip ? -p.h2 : -p.h1; tip.position.y = flip ? -(p.h2 + p.h1 + 0.2) : -(p.h1 + p.h2 + 0.14); return; }
      if (bar) { body.position.y = -p.h; var end = p.h + p.Lb / 2; tip.position.y = -end + 0.02; Rs = end + 0.02;
        if (vane) vane.position.y = -end + vane.userData.side / 2 + 0.03;
        if (strip) { strip.position.set(PIV.x, PIV.y - end - 0.02, PIV.z - 0.012); }
        if (gateG) { var gy = PIV.y - end - 0.045; gateG.position.set(PIV.x, gy, PIV.z); var rd = gateG.userData.rod; rd.scale.y = Math.max(0.02, gy - 0.02); rd.position.set(PIV.x, (gy - 0.01 + 0.012) / 2, PIV.z);
          gateG.userData.wire.set([[PIV.x + 0.03, gy, PIV.z], [PIV.x + 0.2, 0.01, PIV.z + 0.12], [PIV.x + 0.37, 0.014, -0.02]]); }
        return; }
      tip.position.y = -p.L; Rs = p.L + 0.045; if (strip) strip.position.set(PIV.x, PIV.y - Rs - 0.012, PIV.z - 0.012);
    }
    layout();
    S.addApparatus('stand', stand, 'Retort stand and bracket', 'A heavy stand keeps the point of support from moving while the pendulum swings.');
    S.addApparatus('pend', swing, bobName, kater ? 'A brass rod with two knife edges facing each other and sliding weights. It can be hung from either knife edge.' : bar ? 'A uniform steel bar ' + (p.Lb * 100).toFixed(0) + ' cm long with holes every 5 cm; a knife edge through one hole is the axis.' : 'A brass bob on a thin thread. The light card vane adds air damping without changing the period much.');
    if (strip) S.addApparatus('strip', strip, 'Millimetre scale', 'Behind the pointer, zero at the rest position. The amplitude is read here at the end of a swing.');
    if (prot) S.addApparatus('prot', prot, 'Protractor', 'Reads the angle the bar is drawn aside through.');

    var common = {
      pose: function (y) { swing.rotation.z = y[0]; }, grab: tip,
      views: { main: [[PIV.x + 0.75, 0.85, 1.75], [PIV.x - 0.05, 0.6, Z0]], pend: [[PIV.x + 0.35, 0.5, 0.75], [PIV.x, 0.4, Z0]], stand: [[PIV.x + 0.5, 1.0, 0.9], [PIV.x - 0.1, 0.9, Z0]],
        strip: [[PIV.x + 0.05, 0.35, 0.45], [PIV.x, 0.25, PIV.z]], prot: [[PIV.x + 0.05, 1.1, 0.35], [PIV.x, 1.03, PIV.z]], gate: [[PIV.x + 0.4, 0.45, 0.5], [PIV.x + 0.15, 0.2, PIV.z]], ard: [[PIV.x + 0.45, 0.3, 0.4], [PIV.x + 0.42, 0.03, -0.07]] },
      camera: { pos: [PIV.x + 0.85, 0.95, 2.0], look: [PIV.x - 0.1, 0.6, Z0] }, hud: function (y) { return (y[0] / DEG).toFixed(1) + '°'; }, hudLabel: 'Angle θ',
    };
    function add(o) { Object.keys(common).forEach(function (k) { if (o[k] === undefined) o[k] = common[k]; }); return o; }

    if (kater) {
      var hs = [p.h1, p.h2];
      return add({ name: 'Kater\'s pendulum', N: 20, dims: 'Centre of gravity found on the wedge: K1 is ' + (p.h1 * 100).toFixed(1) + ' cm from it and K2 is ' + (p.h2 * 100).toFixed(1) + ' cm, so K1K2 = ' + ((p.h1 + p.h2) * 100).toFixed(1) + ' cm.',
        settings: [{ label: 'Hang from K1', apply: function () { p.side = 0; layout(); } }, { label: 'Hang from K2 (turned over)', apply: function () { p.side = 1; layout(); } }], tapObj: body,
        selCol: colN('Knife edge', function (r) { return r.sel ? 'K2' : 'K1'; }), types: function () { return ['time']; },
        formula: '8π² / g = (T1² + T2²)/(h1 + h2) + (T1² − T2²)/(h1 − h2)', formulaNote: 'Bessel\'s formula: T1, T2 are the periods about K1 and K2; h1, h2 their distances from the centre of gravity.',
        book: ['Aim: g with Kater\'s reversible pendulum.', 'h1 = ' + (p.h1 * 100).toFixed(1) + ' cm,  h2 = ' + (p.h2 * 100).toFixed(1) + ' cm (from the C.G.)', '8π²/g = (T1²+T2²)/(h1+h2) + (T1²−T2²)/(h1−h2)'],
        plan: [{ sel: 0, type: 'time' }, { sel: 0, type: 'time' }, { sel: 1, type: 'time' }, { sel: 1, type: 'time' }],
        enough: function (rows) { return timeRows(rows, 0).length && timeRows(rows, 1).length ? '' : 'Time the pendulum about both knife edges.'; },
        result: function (rows) { var T1 = meanT(rows, 0), T2 = meanT(rows, 1); if (!isFinite(T1) || !isFinite(T2)) return null;
          var g = 8 * PI * PI / ((T1 * T1 + T2 * T2) / (hs[0] + hs[1]) + (T1 * T1 - T2 * T2) / (hs[0] - hs[1]));
          return { label: 'g', value: g, unit: 'm/s²', digits: 3, truth: p.g, note: 'T1 = ' + T1.toFixed(4) + ' s, T2 = ' + T2.toFixed(4) + ' s. They differ by ' + (Math.abs(T1 - T2) / T1 * 100).toFixed(2) + ' %; Bessel\'s formula allows for it.' }; },
        tol: 0.02, amp: function () { return [p.th0, 0]; },
        viva: [['If T1 = T2 exactly, the distance K1K2 equals', ['the length of the equivalent simple pendulum', 'the radius of gyration', 'half the length of the rod'], 0, 'Then g = 4π² (h1 + h2) / T².']],
        chips: ['Why two knife edges?', 'What is Bessel\'s formula?', 'How is the centre of gravity found?', 'Check my readings'] });
    }
    if (damp) {
      return add({ name: bar ? 'Bar pendulum with a damper vane' : 'Simple pendulum with a card vane', decay: { step: 10, max: 50, read: function (a) { return Math.round(Rs * Math.sin(a) * 2000) / 2; } },
        dims: bar ? 'Bar ' + (p.Lb * 100).toFixed(0) + ' cm long, knife edge ' + (p.h * 100).toFixed(0) + ' cm from the centre. The scale is ' + (Rs * 100).toFixed(1) + ' cm below the knife edge.' + (SAMPLE ? ' Damper: ' + SAMPLE + '.' : '')
          : 'Length to the centre of the bob L = ' + (p.L * 100).toFixed(1) + ' cm. The scale is ' + (Rs * 100).toFixed(1) + ' cm below the point of suspension.',
        settings: [{ label: 'Amplitude run', apply: function () {} }], types: function () { return ['decay']; },
        formula: 'A = A0 exp(−γ t)', formulaNote: 'so ln(A0 / A) = γ t.  Relaxation time τ = 1 / (2γ);  quality factor Q = π / (γ T).',
        book: ['Aim: damping coefficient, relaxation time and Q.', 'A = A0 exp(−γ t)  →  ln(A0/A) = γ t', 'τ = 1/(2γ),   Q = π/(γ T)'], columns: decayCols,
        graph: { x: function (r) { return r.t; }, y: function (r) { return Math.log(S.rows[0].A / r.A); }, xlabel: 't (s)', ylabel: 'ln(A0 / A)', x0: 0, y0: 0, line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
        plan: [{ sel: 0, type: 'decay' }], enough: function (rows) { return rows.length >= 4 ? '' : 'Read the amplitude at least four times.'; },
        result: function (rows) { var g = decayGamma(rows); if (g === null) return null; var d = rows[rows.length - 1], Tp = d.t / d.n;
          return { label: 'γ (damping coefficient)', value: g, unit: '1/s', digits: 4, truth: p.gam, note: 'Period T = ' + Tp.toFixed(3) + ' s. Relaxation time τ = 1/(2γ) = ' + (1 / (2 * g)).toFixed(1) + ' s. Quality factor Q = π/(γT) = ' + (PI / (g * Tp)).toFixed(0) + '.' }; },
        tol: 0.05, amp: function () { return [p.th0, 0]; },
        viva: [['The relaxation time is the time in which', ['the energy falls to 1/e of its value', 'the pendulum stops', 'one oscillation is completed'], 0, 'The energy goes as exp(−2γt), so τ = 1/(2γ).']],
        chips: ['What is the damping coefficient?', 'How do I get Q?', 'Why read every 10 oscillations?', 'Check my readings'] });
    }
    if (limit) {
      return add({ name: 'Bar pendulum', N: 10, dims: 'Bar ' + (p.Lb * 100).toFixed(0) + ' cm long, hung ' + (p.h * 100).toFixed(0) + ' cm from its centre. The protractor at the knife edge reads the amplitude.',
        slider: { label: 'Amplitude θ0', min: 5, max: 35, step: 5, unit: '°', get: function () { return Math.round(p.th0 / DEG); }, set: function (v) { p.th0 = v * DEG; } },
        selCol: colN('θ0 (°)', function (r) { return (r.th0 / DEG).toFixed(0); }), rowBase: function () { return { th0: p.th0 }; }, types: function () { return ['time']; },
        formula: 'T = T0 (1 + θ0²/16 + …)', formulaNote: 'T0 = 2π √((k² + h²) / (g h)) is the small-swing period. The motion is taken as simple harmonic while T is within 1 % of T0.',
        book: ['Aim: the largest amplitude for SHM of a bar pendulum.', 'T = T0 (1 + θ0²/16 + …),  θ0 in radian', 'Limit: T = 1.01 T0'],
        graph: { x: function (r) { return r.th0 * r.th0; }, y: function (r) { return r.T; }, xlabel: 'θ0² (rad²)', ylabel: 'T (s)', line: function (pts) { var f = S.fit.linear(pts); return function (x) { return f.m * x + f.c; }; } },
        plan: [5, 10, 15, 20, 25, 30, 35].map(function (d) { return { slider: d, type: 'time' }; }), enough: function (rows) { return rows.length >= 5 ? '' : 'Time the bar at five or more amplitudes.'; },
        result: function (rows) { if (rows.length < 3) return null; var f = S.fit.linear(rows.map(function (r) { return [r.th0 * r.th0, r.T]; })); if (!f || f.m <= 0) return null; var lim = Math.sqrt(p.eps * f.c / f.m);
          return { label: 'Amplitude limit for SHM', value: lim / DEG, unit: '°', digits: 1, truth: K.measure(p).th_lim / DEG, note: 'T0 = ' + f.c.toFixed(4) + ' s (intercept); slope ÷ T0 = ' + (f.m / f.c).toFixed(4) + ' per rad² (theory 1/16 = 0.0625). T is 1 % above T0 at ' + lim.toFixed(3) + ' rad.' }; },
        tol: 0.04, amp: function () { return [p.th0, 0]; },
        viva: [['Up to about what amplitude is the bar\'s motion simple harmonic to 1 %?', ['About 23°', 'About 2°', 'About 60°'], 0, 'θ0²/16 = 0.01 gives θ0 = 0.4 rad.']],
        chips: ['Why does T grow with amplitude?', 'What does the slope tell me?', 'Check my readings'] });
    }
    // the photo-gate
    return add({ name: 'Bar pendulum', N: 10, tRes: 1e-4, tDigits: 4, TDigits: 4, noWatch: true, dims: 'Bar ' + (p.Lb * 100).toFixed(1) + ' cm long, so k² = L²/12 = ' + (p.Lb * p.Lb / 12 * 1e4).toFixed(1) + ' cm². The gate sits where the lower end hangs at rest.',
      slider: { label: 'Knife edge to centre h', min: 20, max: 40, step: 5, unit: 'cm', get: function () { return Math.round(p.h * 100); }, set: function (v) { p.h = v / 100; layout(); } },
      selCol: colN('h (cm)', function (r) { return (r.h * 100).toFixed(0); }), rowBase: function () { return { h: p.h }; }, types: function () { return ['time']; },
      formula: 'T = 2π √((k² + h²) / (g h))', formulaNote: 'so g = 4π² (k² + h²) / (h T²), with k² = L²/12 for a uniform bar.',
      book: ['Aim: period of a bar pendulum with a photo-gate, and g.', 'L = ' + (p.Lb * 100).toFixed(1) + ' cm,  k² = L²/12', 'g = 4π² (k² + h²) / (h T²)'],
      plan: [20, 25, 30, 35, 40].map(function (d) { return { slider: d, type: 'time' }; }), enough: function (rows) { return rows.length >= 3 ? '' : 'Read the period for three or more holes.'; },
      extraCols: [colN('g (m/s²)', function (r) { return gOf(r).toFixed(3); })],
      result: function (rows) { if (!rows.length) return null; return { label: 'g', value: mean(rows.map(gOf)), unit: 'm/s²', digits: 3, truth: p.g, note: 'Mean over ' + rows.length + ' holes. The period is least near h = k = ' + (p.Lb / Math.sqrt(12) * 100).toFixed(1) + ' cm.' }; },
      tol: 0.02, amp: function () { return [p.th0, 0]; }, lcd: drawLcd,
      viva: [['How many times is the beam cut in one oscillation?', ['Twice', 'Once', 'Four times'], 0, 'The bar passes its rest position twice in each period.']],
      chips: ['How does the photo-gate time the swing?', 'Why is T least near h = k?', 'Check my readings'] });
    function gOf(r) { return 4 * PI * PI * (p.Lb * p.Lb / 12 + r.h * r.h) / (r.h * r.T * r.T); }
  }

  // ------------------------------------------------------------------ two coupled pendulums, or two gliders on an air track
  function buildCoupled() {
    var track = p.kind > 0.5, damped = p.gam > 0, A, B, sprs = [], grab, pose, views, cam;
    if (!track) {
      var XL = X0 - 0.35, XR = X0 + 0.35, H = 0.92; var fr = frame(XL, XR, Z0, H);
      var PA = new T.Vector3(X0 - 0.15, H - 0.002, Z0), PB = new T.Vector3(X0 + 0.15, H - 0.002, Z0);
      function pend(P, tag) { var g = new T.Group(); g.position.copy(P); S.scene.add(g); var r = cyl(0.003, p.L, M.steel, 12); r.position.y = -p.L / 2; g.add(r);
        var b = S.mesh(new T.SphereGeometry(0.028, 40, 28), M.brass); b.position.y = -p.L; g.add(b); var l = S.label(tag, { w: 0.03, ratio: 0.6, color: '#3a2a08' }); l.position.set(0, -p.L, 0.0285); g.add(l);
        var hk = new T.Object3D(); hk.position.y = -p.a; g.add(hk); g.userData.hook = hk; g.userData.bob = b; return g; }
      A = pend(PA, 'A'); B = pend(PB, 'B'); var h1 = helix(0.008, 22, 0.0007); sprs.push(h1);
      pose = function (y) { A.rotation.z = y[0]; B.rotation.z = y[2]; var a = new T.Vector3(), b = new T.Vector3(); A.userData.hook.getWorldPosition(a); B.userData.hook.getWorldPosition(b); stretch(h1, a, b); };
      grab = A.userData.bob;
      S.addApparatus('frame', fr, 'Rigid frame', 'Both pendulums hang from the same heavy beam, which must not rock.');
      S.addApparatus('pa', A, 'Pendulum A', 'A brass bob of ' + (p.m * 1000).toFixed(0) + ' g on a light rod, ' + (p.L * 100).toFixed(0) + ' cm long.');
      S.addApparatus('pb', B, 'Pendulum B', 'Identical to A: alone, the two have the same period.');
      S.addApparatus('spring', h1, 'Coupling spring', 'A light spring hooked ' + (p.a * 100).toFixed(0) + ' cm below the pivots. It is what lets energy pass between the pendulums.');
      views = { main: [[X0 + 0.5, 0.75, 1.5], [X0, 0.5, Z0]], frame: [[X0 + 0.5, 0.9, 1.2], [X0, 0.7, Z0]], pa: [[X0, 0.45, 0.5], [X0 - 0.15, 0.35, Z0]], pb: [[X0 + 0.3, 0.45, 0.5], [X0 + 0.15, 0.35, Z0]], spring: [[X0, 0.7, 0.4], [X0, 0.6, Z0]] };
      cam = { pos: [X0 + 0.55, 0.8, 1.65], look: [X0, 0.5, Z0] };
    } else {
      var TY = 0.12, tg = new T.Group(); S.scene.add(tg);
      var beam = box(1.5, 0.035, 0.06, M.alu); beam.position.set(X0, TY, Z0); tg.add(beam);
      var ridge = box(1.5, 0.012, 0.03, M.alu); ridge.position.set(X0, TY + 0.022, Z0); tg.add(ridge);
      [-0.6, 0.6].forEach(function (dx) { var f = box(0.05, TY - 0.017, 0.12, M.black); f.position.set(X0 + dx, (TY - 0.017) / 2, Z0); tg.add(f); S.contact(0.1, 0.18, X0 + dx, Z0, 0.5); });
      var sc = mmStrip(1.4, 'cm'); sc.position.set(X0, TY - 0.002, Z0 + 0.032); sc.scale.y = 0.8;
      var posts = [-0.72, 0.72].map(function (dx) { var q = box(0.012, 0.09, 0.05, M.black); q.position.set(X0 + dx, TY + 0.06, Z0); tg.add(q); return new T.Vector3(X0 + dx, TY + 0.075, Z0); });
      var blower = S.rounded(0.14, 0.1, 0.12, 0.01, new T.MeshStandardMaterial({ color: 0x8a2f2f, roughness: 0.5 })); blower.rotation.x = -PI / 2; blower.position.set(X0 - 0.86, 0.06, Z0 - 0.1); S.scene.add(blower); S.contact(0.2, 0.18, X0 - 0.86, Z0 - 0.1, 0.5);
      var bl = S.label('AIR BLOWER', { w: 0.1, ratio: 0.2, color: '#f4eaea' }); bl.position.set(X0 - 0.86, 0.07, Z0 - 0.049); S.scene.add(bl);
      S.wire([[X0 - 0.8, 0.09, Z0 - 0.08], [X0 - 0.76, TY, Z0]], 'black');
      function glider(x, tag) { var g = new T.Group(); g.position.set(x, TY + 0.043, Z0); S.scene.add(g); var b = box(0.13, 0.03, 0.075, M.alu); g.add(b);
        var fl = box(0.05, 0.05, 0.002, M.black); fl.position.y = 0.04; g.add(fl); var l = S.label(tag, { w: 0.03, ratio: 0.6, color: '#f3f3f3' }); l.position.set(0, 0.04, 0.0015); g.add(l);
        if (damped) [-0.04, 0.04].forEach(function (dx) { var mg = box(0.02, 0.012, 0.079, M.red); mg.position.set(dx, -0.012, 0); g.add(mg); });
        g.userData.x0 = x; return g; }
      A = glider(X0 - 0.24, 'A'); B = glider(X0 + 0.24, 'B');
      sprs = [helix(0.009, 20, 0.0007), helix(0.009, 20, 0.0007), helix(0.009, 20, 0.0007)];
      pose = function (y) { A.position.x = A.userData.x0 + y[0]; B.position.x = B.userData.x0 + y[2]; var ya = TY + 0.075;
        stretch(sprs[0], posts[0], new T.Vector3(A.position.x - 0.065, ya - 0.03, Z0)); stretch(sprs[1], new T.Vector3(A.position.x + 0.065, ya - 0.03, Z0), new T.Vector3(B.position.x - 0.065, ya - 0.03, Z0));
        stretch(sprs[2], new T.Vector3(B.position.x + 0.065, ya - 0.03, Z0), new T.Vector3(posts[1].x, ya - 0.03, Z0)); };
      posts[0].y -= 0.03; grab = A;
      S.addApparatus('track', tg, 'Air track', 'Air blown through fine holes floats the gliders, so friction is almost nothing. A centimetre scale runs along it.');
      S.addApparatus('pa', A, 'Glider A', 'Mass ' + (p.m * 1000).toFixed(0) + ' g.' + (damped ? ' The red magnets under it induce eddy currents in the track and damp the motion.' : ''));
      S.addApparatus('pb', B, 'Glider B', 'Identical to glider A.');
      S.addApparatus('spring', sprs[1], 'Middle (coupling) spring', 'Joins the two gliders. The two outer springs, ' + p.k.toFixed(1) + ' N/m each, tie them to the end posts.');
      S.addApparatus('blower', blower, 'Air blower', 'Feeds the track. Switch it on before releasing a glider.');
      views = { main: [[X0 + 0.2, 0.55, 1.1], [X0, 0.12, Z0]], track: [[X0 + 0.2, 0.5, 1.0], [X0, 0.12, Z0]], pa: [[X0 - 0.2, 0.3, 0.2], [X0 - 0.24, 0.15, Z0]], pb: [[X0 + 0.3, 0.3, 0.2], [X0 + 0.24, 0.15, Z0]],
        spring: [[X0, 0.3, 0.15], [X0, 0.16, Z0]], blower: [[X0 - 0.6, 0.35, 0.4], [X0 - 0.86, 0.06, Z0 - 0.1]] };
      cam = { pos: [X0 + 0.25, 0.62, 1.25], look: [X0, 0.1, Z0] };
    }
    var unit = track ? 1000 : 1 / DEG, settings = [{ label: 'In phase (both the same way)', apply: function () { p.mode = 0; } }, { label: 'Out of phase (opposite ways)', apply: function () { p.mode = 1; } },
      { label: 'Only A displaced (beats)', apply: function () { p.mode = 2; } }];
    function kap(rows) { var T1 = meanT(rows, 0), T2 = meanT(rows, 1); return isFinite(T1) && isFinite(T2) ? { T1: T1, T2: T2, k: (T1 * T1 - T2 * T2) / (T1 * T1 + T2 * T2) } : null; }
    var plan = [{ sel: 0, type: 'time' }, { sel: 1, type: 'time' }];
    if (damped) plan.push({ sel: 0, type: 'decay' }); else plan.push({ sel: 2, type: 'beat' });
    return { name: track ? 'Coupled gliders' : 'Coupled pendulums', N: 20, pose: pose, grab: grab, views: views, camera: cam, settings: settings, tapObj: grab,
      decay: { step: 5, max: 25, read: function (a) { return Math.round(a * unit * 2) / 2; } },
      types: function (sel) { return sel === 2 ? ['beat'] : (damped && sel === 0 ? ['time', 'decay'] : ['time']); },
      hud: function (y) { return track ? (y[0] * 1000).toFixed(1) + ' mm' : (y[0] / DEG).toFixed(1) + '°'; }, hudLabel: track ? 'Glider A' : 'Pendulum A',
      dims: track ? 'Each glider is ' + (p.m * 1000).toFixed(0) + ' g. The two outer springs are alike (' + p.k.toFixed(1) + ' N/m); the middle spring is the unknown coupling.' + (damped ? ' Damping magnets are fitted.' : '')
        : 'Both pendulums are ' + (p.L * 100).toFixed(0) + ' cm long with ' + (p.m * 1000).toFixed(0) + ' g bobs; alone they have the same period. The spring is hooked ' + (p.a * 100).toFixed(0) + ' cm below the pivots.',
      selCol: colN('Mode', function (r) { return r.type === 'decay' ? 'decay n=' + r.n : ['in phase', 'out of phase', 'beats'][r.sel]; }),
      extraCols: damped ? [colN('A (mm)', function (r) { return r.type === 'decay' ? r.A.toFixed(1) : '—'; }), colN('t (s)', function (r) { return r.type === 'decay' ? r.t.toFixed(1) : '—'; })] : [],
      formula: 'κ = (ω2² − ω1²) / (ω2² + ω1²) = (T1² − T2²) / (T1² + T2²)', formulaNote: 'T1: in phase, T2: out of phase. Beat period Tb = T1 T2 / (T1 − T2).' + (damped ? ' With damping, A = A0 exp(−γ t).' : ''),
      book: ['Aim: normal modes and coupling of two ' + (track ? 'gliders on an air track.' : 'coupled pendulums.'), 'κ = (T1² − T2²) / (T1² + T2²)', damped ? 'A = A0 exp(−γ t)' : 'Tb = T1 T2 / (T1 − T2)'],
      plan: plan, enough: function (rows) { if (!timeRows(rows, 0).length || !timeRows(rows, 1).length) return 'Time both normal modes.'; if (damped && rows.filter(function (r) { return r.type === 'decay'; }).length < 4) return 'Read the decaying amplitude of the in-phase mode.'; return ''; },
      result: function (rows) { var q = kap(rows); if (!q) return null; var beat = rows.filter(function (r) { return r.type === 'beat'; })[0], pred = q.T1 * q.T2 / (q.T1 - q.T2);
        var note = 'T1 = ' + q.T1.toFixed(4) + ' s, T2 = ' + q.T2.toFixed(4) + ' s, so f1 = ' + (1 / q.T1).toFixed(4) + ' Hz and f2 = ' + (1 / q.T2).toFixed(4) + ' Hz. Beat period expected T1T2/(T1 − T2) = ' + pred.toFixed(1) + ' s' + (beat ? '; timed ' + beat.Tb.toFixed(1) + ' s.' : '.');
        if (damped) { var g = decayGamma(rows); if (g === null) return null; return { label: 'γ (damping coefficient)', value: g, unit: '1/s', digits: 4, truth: p.gam, note: 'Coupling coefficient κ = ' + q.k.toFixed(4) + '. ' + note }; }
        var w = K.w(p); return { label: 'κ (coupling coefficient)', value: q.k, unit: '', digits: 4, truth: (w[1] - w[0]) / (w[1] + w[0]), note: note }; },
      tol: damped ? 0.05 : 0.03, amp: function () { return K.y0(p, p.mode); },
      viva: [['In which mode is the coupling spring never stretched?', ['The in-phase mode', 'The out-of-phase mode', 'Both'], 0, 'Both bodies move together, so the distance between them does not change.']],
      chips: ['What is a normal mode?', 'Why do beats appear?', 'What is the coupling coefficient?', 'Check my readings'] };
  }

  // ------------------------------------------------------------------ a loaded helical spring (alone, in series, in parallel)
  function buildSpring() {
    var series = p.mode > 0.5 && p.mode < 1.5, par = p.mode > 1.5, geo = p.geo > 0.5, combo = series || par;
    var stand = S.stand({ x: X0, z: Z0, armY: 1.0, h: 1.1, armLen: 0.22 }), jaw = stand.userData.jaw;
    var TOP = new T.Vector3(jaw.x, 0.975, Z0 + 0.04); var hookB = box(0.02, 0.014, 0.06, M.brass); put(hookB, jaw.x, 0.985, Z0 + 0.025);
    var L0 = combo && series ? 0.26 : 0.16, HANG = 0.07;
    var hs = [helix(0.011, combo ? 14 : 18, 0.0009)]; if (combo) hs.push(helix(0.011, 14, 0.0009));
    var bars = []; if (par) { [0, 1].forEach(function () { var b = box(0.075, 0.005, 0.008, M.brass); S.scene.add(b); bars.push(b); }); }
    var hanger = new T.Group(); S.scene.add(hanger);
    var hr = cyl(0.002, HANG, M.steel, 10); hr.position.y = -HANG / 2; hanger.add(hr); var hp = cyl(0.02, 0.004, M.brass, 32); hp.position.y = -HANG; hanger.add(hp);
    var ptr = S.mesh(new T.ConeGeometry(0.003, 0.05, 8), M.red); ptr.rotation.z = -PI / 2; ptr.position.set(0.045, -0.012, 0); hanger.add(ptr);
    var discs = []; for (var i = 0; i < 6; i++) { var d = cyl(0.02, 0.009, i % 2 ? M.brass : M.iron, 32); d.position.y = -HANG + 0.007 + i * 0.0095; hanger.add(d); discs.push(d); }
    var extMax = 0.3 * p.g / HK.K.w7_spring.keff(p) + 0.03;
    var Y0 = TOP.y - L0 - 0.012;                                         // pointer height with the empty hanger
    var ruler = S.ruler(0.3, { title: 'cm · LC 1 mm', labelEvery: 10 }); ruler.position.set(jaw.x + 0.088, Y0 - 0.3, Z0 + 0.04);
    var rp = post(jaw.x + 0.1, Z0 + 0.0, Y0 + 0.02); var clampR = box(0.03, 0.02, 0.05, M.alu); put(clampR, jaw.x + 0.097, Y0 - 0.15, Z0 + 0.02);
    var spare = cyl(0.02, 0.009, M.brass, 32); put(spare, jaw.x + 0.3, 0.0045, Z0 + 0.12); var spare2 = cyl(0.02, 0.009, M.iron, 32); put(spare2, jaw.x + 0.3, 0.0135, Z0 + 0.12); S.contact(0.08, 0.08, jaw.x + 0.3, Z0 + 0.12, 0.4);
    function loadDiscs() { var n = Math.round(p.m / 0.05); discs.forEach(function (d, i) { d.visible = i < n; }); }
    function pose(y) { var k = HK.K.w7_spring.keff(p), ext = st.loaded ? p.m * p.g / k : 0, len = L0 + ext + y[0], bot = new T.Vector3(TOP.x, TOP.y - len, TOP.z);
      if (series) { var k1 = geo ? k : p.k1, f1 = (1 / k1) / (1 / k1 + 1 / p.k2), mid = new T.Vector3(TOP.x, TOP.y - L0 / 2 - (ext + y[0]) * f1, TOP.z); stretch(hs[0], TOP, mid); stretch(hs[1], mid, bot); }
      else if (par) { stretch(hs[0], new T.Vector3(TOP.x - 0.028, TOP.y - 0.006, TOP.z), new T.Vector3(TOP.x - 0.028, bot.y + 0.006, TOP.z)); stretch(hs[1], new T.Vector3(TOP.x + 0.028, TOP.y - 0.006, TOP.z), new T.Vector3(TOP.x + 0.028, bot.y + 0.006, TOP.z));
        bars[0].position.set(TOP.x, TOP.y - 0.004, TOP.z); bars[1].position.set(TOP.x, bot.y + 0.004, TOP.z); }
      else stretch(hs[0], TOP, bot);
      hanger.position.copy(bot); }
    st.loaded = false; loadDiscs(); discs.forEach(function (d) { d.visible = false; });
    S.addApparatus('stand', stand, 'Retort stand', 'Clamped firmly so the support does not move with the load.');
    S.addApparatus('spring', hs[0], combo ? (series ? 'Two springs in series' : 'Two springs in parallel') : 'Helical spring', combo ? 'Light steel springs: k1 = ' + p.k1.toFixed(0) + ' N/m and k2 = ' + p.k2.toFixed(0) + ' N/m on their tags.'
      : geo ? 'Steel spring: ' + p.Nt.toFixed(0) + ' turns, mean coil radius ' + (p.Rc * 1000).toFixed(1) + ' mm, wire radius ' + (p.rw * 1000).toFixed(2) + ' mm, mass ' + (p.ms * 1000).toFixed(0) + ' g.' : 'A close-wound steel spring. Its stiffness and its own mass are to be found.');
    S.addApparatus('hanger', hanger, 'Hanger with slotted masses', 'The hanger and each slotted mass are 50 g. The red pointer reads the scale.');
    S.addApparatus('ruler', ruler, 'Vertical scale', 'Zero is level with the pointer when the hanger is empty, so the pointer reads the extension. Least count 1 mm.');
    function fitT2(rows) { return S.fit.linear(rows.map(function (r) { return [r.m, r.T * r.T]; })); }
    function fitX(rows) { return S.fit.linear(rows.map(function (r) { return [r.m, r.x]; })); }
    return { name: 'Loaded spring', N: 20, pose: pose, grab: hp, stat: { label: 'Read the pointer', unit: 'mm', read: function () { return Math.round(p.m * p.g / HK.K.w7_spring.keff(p) * 1000); } },
      slider: { label: 'Load on the spring', min: 100, max: 300, step: 50, unit: 'g', get: function () { return Math.round(p.m * 1000); }, set: function (v) { p.m = v / 1000; st.loaded = true; loadDiscs(); } },
      onStart: function () { st.loaded = true; loadDiscs(); },
      selCol: colN('m (g)', function (r) { return (r.m * 1000).toFixed(0); }), rowBase: function () { return { m: p.m, x: st.stat / 1000 }; }, types: function () { return ['time']; },
      extraCols: [colN('x (mm)', function (r) { return (r.x * 1000).toFixed(0); }), colN('T² (s²)', function (r) { return (r.T * r.T).toFixed(4); })],
      views: { main: [[jaw.x + 0.55, 0.75, 1.3], [jaw.x, 0.6, Z0]], stand: [[jaw.x + 0.5, 0.9, 1.0], [jaw.x - 0.1, 0.7, Z0]], spring: [[jaw.x + 0.2, 0.9, 0.4], [jaw.x, 0.85, Z0]], hanger: [[jaw.x + 0.25, 0.7, 0.35], [jaw.x + 0.03, 0.66, Z0]], ruler: [[jaw.x + 0.25, 0.7, 0.3], [jaw.x + 0.08, 0.68, Z0]] },
      camera: { pos: [jaw.x + 0.6, 0.85, 1.45], look: [jaw.x - 0.05, 0.6, Z0] }, hud: function (y) { return (y[0] * 1000).toFixed(1) + ' mm'; }, hudLabel: 'Displacement',
      dims: geo ? 'Spring: N = ' + p.Nt.toFixed(0) + ' turns; outer diameter (vernier) ' + ((p.Rc + p.rw) * 2000).toFixed(2) + ' mm, wire diameter (screw gauge) ' + (p.rw * 2000).toFixed(2) + ' mm, so R = ' + (p.Rc * 1000).toFixed(2) + ' mm and r = ' + (p.rw * 1000).toFixed(2) + ' mm.'
        : combo ? 'Spring tags: k1 = ' + p.k1.toFixed(0) + ' N/m, k2 = ' + p.k2.toFixed(0) + ' N/m, joined ' + (series ? 'end to end (series).' : 'side by side (parallel).') : 'The pointer reads zero with the empty hanger. Each slotted mass is 50 g.',
      formula: geo ? 'η = 4 N R³ k / r⁴' : combo ? (series ? '1/k = 1/k1 + 1/k2' : 'k = k1 + k2') : 'T² = 4π² (m + ms/3) / k', formulaNote: 'k = 4π² ÷ (slope of T² against m). Static check: x = m g / k.',
      book: [geo ? 'Aim: rigidity modulus of the wire of a helical spring.' : combo ? 'Aim: spring constant of two springs in ' + (series ? 'series.' : 'parallel.') : 'Aim: k, g and the mass of a spring (static and dynamic).', 'T² = 4π² (m + ms/3) / k,   x = m g / k', geo ? 'η = 4 N R³ k / r⁴' : combo ? (series ? '1/k = 1/k1 + 1/k2' : 'k = k1 + k2') : 'slope(T², m) = 4π²/k;  intercept → ms/3'],
      graph: { x: function (r) { return r.m; }, y: function (r) { return r.T * r.T; }, xlabel: 'm (kg)', ylabel: 'T² (s²)', line: function (pts) { var f = S.fit.linear(pts); return function (x) { return f.m * x + f.c; }; } },
      plan: [100, 150, 200, 250, 300].map(function (d) { return { slider: d, type: 'time' }; }), enough: function (rows) { return rows.length >= 4 ? '' : 'Take readings for four or more loads.'; },
      result: function (rows) { if (rows.length < 3) return null; var f = fitT2(rows), fx = fitX(rows); if (!f || f.m <= 0) return null; var k = 4 * PI * PI / f.m, g = fx ? k * fx.m : NaN, ms = 3 * f.c / f.m;
        var base = 'k = 4π²/slope = ' + k.toFixed(2) + ' N/m. Static slope x/m gives g = ' + g.toFixed(2) + ' m/s².';
        if (geo) return { label: 'η (spring wire)', value: 4 * p.Nt * Math.pow(p.Rc, 3) * k / Math.pow(p.rw, 4) / 1e9, unit: 'GPa', digits: 1, truth: p.eta / 1e9, note: base };
        if (combo) return { label: 'k (' + (series ? 'series' : 'parallel') + ')', value: k, unit: 'N/m', digits: 2, truth: HK.K.w7_spring.keff(p), note: base + ' From the tags: ' + (series ? 'k1k2/(k1 + k2)' : 'k1 + k2') + ' = ' + HK.K.w7_spring.keff(p).toFixed(2) + ' N/m.' };
        return { label: 'k (spring constant)', value: k, unit: 'N/m', digits: 2, truth: p.k1, note: base + ' Mass of the spring ms = 3 × intercept ÷ slope = ' + (ms * 1000).toFixed(0) + ' g (true ' + (p.ms * 1000).toFixed(0) + ' g).' }; },
      tol: 0.03, amp: function () { return [p.x0, 0]; },
      viva: [['T² plotted against the load m gives', ['a straight line of slope 4π²/k', 'a parabola', 'a horizontal line'], 0, 'T² = 4π² (m + ms/3) / k is linear in m.']],
      chips: ['Why add one third of the spring\'s mass?', 'Static or dynamic: which is better?', 'Check my readings', 'Why is my k different?'] };
  }

  // ------------------------------------------------------------------ Maxwell's needle / Searle's two bars
  function buildTorsion() {
    var searle = p.kind > 0.5, MAT = /brass/i.test(SAMPLE) ? { name: 'brass', m: M.brass } : { name: 'steel', m: M.steel };
    var r4 = Math.pow(p.rw, 4);
    if (!searle) {
      var stand = S.stand({ x: X0, z: Z0, armY: 0.82, h: 0.92, armLen: 0.28 }), jaw = stand.userData.jaw;
      var chuck = cyl(0.007, 0.025, M.brass); put(chuck, jaw.x, 0.795, Z0 + 0.035); var cb = box(0.02, 0.012, 0.05, M.brass); put(cb, jaw.x, 0.812, Z0 + 0.02);
      var NY = 0.782 - p.lw; var wire = cyl(0.0009, p.lw, MAT.m, 8); put(wire, jaw.x, 0.782 - p.lw / 2, Z0 + 0.035);
      var needle = new T.Group(); needle.position.set(jaw.x, NY - 0.014, Z0 + 0.035); S.scene.add(needle);
      var tube = cyl(0.011, p.Ln, M.brass, 32); tube.rotation.z = PI / 2; needle.add(tube);
      var stem = cyl(0.003, 0.016, M.brass, 10); stem.position.y = 0.018; needle.add(stem);
      var mirror = box(0.014, 0.014, 0.001, M.chrome); mirror.position.set(0, 0.034, 0); needle.add(mirror);
      var solidM = new T.MeshStandardMaterial({ color: 0x7a5a1c, roughness: 0.3, metalness: 0.9 }), hollowM = new T.MeshStandardMaterial({ color: 0xe9d9a2, roughness: 0.35, metalness: 0.6 });
      var secs = [-3, -1, 1, 3].map(function (q) { var c = cyl(0.0118, p.Ln / 4 - 0.006, solidM, 32); c.rotation.z = PI / 2; c.position.x = q * p.Ln / 8; needle.add(c);
        var l = S.liveTex(64, 64); var lm = new T.Mesh(new T.PlaneGeometry(0.014, 0.014), new T.MeshBasicMaterial({ map: l, transparent: true })); lm.position.set(q * p.Ln / 8, 0, 0.0122); needle.add(lm); c.userData.tex = l; c.userData.outer = Math.abs(q) === 3; return c; });
      function paint() { secs.forEach(function (c) { var solid = (p.pos < 0.5) === c.userData.outer; c.material = solid ? solidM : hollowM; c.userData.tex.draw(function (x) { x.clearRect(0, 0, 64, 64); x.fillStyle = solid ? '#fff4d0' : '#3a2a08'; x.font = '700 44px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText(solid ? 'S' : 'H', 32, 48); }); }); }
      paint();
      S.addApparatus('stand', stand, 'Stand with chuck', 'The top of the wire is gripped in a chuck so that it cannot turn.');
      S.addApparatus('wire', wire, MAT.name.charAt(0).toUpperCase() + MAT.name.slice(1) + ' suspension wire', 'Length l = ' + (p.lw * 100).toFixed(1) + ' cm, radius r = ' + (p.rw * 1000).toFixed(3) + ' mm (screw gauge, mean of several places).');
      S.addApparatus('needle', needle, 'Maxwell\'s needle', 'A hollow brass tube ' + (p.Ln * 100).toFixed(1) + ' cm long. Four cylinders fill it: two solid (S, ' + (p.ms * 1000).toFixed(0) + ' g each) and two hollow (H, ' + (p.mh * 1000).toFixed(0) + ' g each).');
      var Tm = function (rows) { var a = meanT(rows, 0), b = meanT(rows, 1); return isFinite(a) && isFinite(b) ? [a, b] : null; };
      return { name: 'Maxwell\'s needle', N: 10, pose: function (y) { needle.rotation.y = y[0]; }, grab: secs[3], tapObj: secs[3],
        settings: [{ label: 'Solid cylinders outside', apply: function () { p.pos = 0; paint(); } }, { label: 'Hollow cylinders outside', apply: function () { p.pos = 1; paint(); } }],
        selCol: colN('Outside', function (r) { return r.sel ? 'hollow' : 'solid'; }), types: function () { return ['time']; },
        views: { main: [[jaw.x + 0.45, 0.6, 1.0], [jaw.x, 0.45, Z0]], stand: [[jaw.x + 0.45, 0.8, 0.9], [jaw.x - 0.1, 0.6, Z0]], wire: [[jaw.x + 0.2, 0.65, 0.4], [jaw.x, 0.58, Z0]], needle: [[jaw.x + 0.1, 0.5, 0.3], [jaw.x, NY, Z0]] },
        camera: { pos: [jaw.x + 0.5, 0.7, 1.2], look: [jaw.x - 0.05, 0.45, Z0] }, hud: function (y) { return (y[0] / DEG).toFixed(1) + '°'; }, hudLabel: 'Twist',
        dims: 'Wire: l = ' + (p.lw * 100).toFixed(1) + ' cm, r = ' + (p.rw * 1000).toFixed(3) + ' mm. Needle: L = ' + (p.Ln * 100).toFixed(1) + ' cm. Cylinders: solid ms = ' + (p.ms * 1000).toFixed(1) + ' g, hollow mh = ' + (p.mh * 1000).toFixed(1) + ' g.',
        formula: 'η = 2π l (ms − mh) L² / (r⁴ (T1² − T2²))', formulaNote: 'T1: solid cylinders outside; T2: hollow cylinders outside.',
        book: ['Aim: rigidity modulus of ' + MAT.name + ' with Maxwell\'s needle.', 'l = ' + (p.lw * 100).toFixed(1) + ' cm, r = ' + (p.rw * 1000).toFixed(3) + ' mm, L = ' + (p.Ln * 100).toFixed(1) + ' cm', 'ms = ' + (p.ms * 1000).toFixed(1) + ' g, mh = ' + (p.mh * 1000).toFixed(1) + ' g', 'η = 2π l (ms − mh) L² / (r⁴ (T1² − T2²))'],
        plan: [{ sel: 0, type: 'time' }, { sel: 0, type: 'time' }, { sel: 1, type: 'time' }, { sel: 1, type: 'time' }],
        enough: function (rows) { return Tm(rows) ? '' : 'Time the needle with the solid cylinders outside and with the hollow ones outside.'; },
        result: function (rows) { var q = Tm(rows); if (!q) return null; var eta = 2 * PI * p.lw * (p.ms - p.mh) * p.Ln * p.Ln / (r4 * (q[0] * q[0] - q[1] * q[1]));
          return { label: 'η (' + MAT.name + ')', value: eta / 1e9, unit: 'GPa', digits: 1, truth: p.eta / 1e9, note: 'T1 = ' + q[0].toFixed(3) + ' s (solid outside), T2 = ' + q[1].toFixed(3) + ' s (hollow outside).' }; },
        tol: 0.03, amp: function () { return [p.th0, 0]; },
        viva: [['Changing the cylinders over changes', ['the moment of inertia but not the mass', 'the mass but not the moment of inertia', 'the wire'], 0, 'The same four cylinders hang from the wire; only their distances from the axis change.']],
        chips: ['Why change the cylinders over?', 'Why does r matter so much?', 'Check my readings', 'Why is my η different?'] };
    }
    // Searle's two bars
    var XL = X0 - 0.38, XR = X0 + 0.38, H = 0.62, fr = frame(XL, XR, Z0, H), I = HK.K.w7_torsion.inertia(p, 0);
    var barM = M.brass, BY = 0.3;
    var g0 = new T.Group(), g1 = new T.Group(); S.scene.add(g0); S.scene.add(g1);
    var bars0 = [-1, 1].map(function (sg) { var b = new T.Group(); b.position.set(X0 + sg * p.lw / 2, BY, Z0); g0.add(b); var m = box(p.wb, p.wb, p.Lbar, barM); b.add(m);
      var th = cyl(0.0006, H - BY, M.thread, 6); th.position.set(X0 + sg * p.lw / 2, (H + BY) / 2, Z0); g0.add(th); return b; });
    var w0 = cyl(0.0009, p.lw, MAT.m, 8); w0.rotation.z = PI / 2; w0.position.set(X0, BY, Z0); g0.add(w0);
    var topBar = box(p.Lbar, p.wb, p.wb, barM); topBar.position.set(X0, H - 0.012, Z0 + 0.02); g1.add(topBar);
    var cl = box(0.04, 0.03, 0.03, M.iron); cl.position.set(X0, H - 0.004, Z0 + 0.012); g1.add(cl);
    var w1 = cyl(0.0009, p.lw, MAT.m, 8); w1.position.set(X0, H - 0.018 - p.lw / 2, Z0 + 0.02); g1.add(w1);
    var lowBar = new T.Group(); lowBar.position.set(X0, H - 0.018 - p.lw - p.wb / 2, Z0 + 0.02); g1.add(lowBar); var lb = box(p.Lbar, p.wb, p.wb, barM); lowBar.add(lb);
    function arrange() { g0.visible = p.pos < 0.5; g1.visible = p.pos > 0.5; }
    arrange();
    S.addApparatus('frame', fr, 'Support frame', 'The two bars hang from it by long threads that have almost no torsion.');
    S.addApparatus('bars', g0, 'Two equal bars joined by the wire', 'Brass bars, each ' + (p.Mb * 1000).toFixed(0) + ' g, ' + (p.Lbar * 100).toFixed(1) + ' cm long and ' + (p.wb * 1000).toFixed(0) + ' mm square. The ' + MAT.name + ' wire, ' + (p.lw * 100).toFixed(1) + ' cm long, joins their middles.');
    S.addApparatus('tors', g1, 'One bar clamped, one hanging', 'For the torsional oscillations one bar is clamped to the frame and the other hangs from the wire and twists it.');
    function TT(rows) { var a = meanT(rows, 0), b = meanT(rows, 1); return isFinite(a) && isFinite(b) ? [a, b] : null; }
    return { name: 'Searle\'s bars', N: 20, pose: function (y) { if (p.pos < 0.5) { bars0[0].rotation.y = y[0]; bars0[1].rotation.y = -y[0]; } else lowBar.rotation.y = y[0]; }, grab: lb, tapObj: topBar,
      grabFor: function () { return p.pos < 0.5 ? bars0[1] : lb; },
      settings: [{ label: 'Bars hung side by side (wire bends)', apply: function () { p.pos = 0; arrange(); } }, { label: 'One bar clamped (wire twists)', apply: function () { p.pos = 1; arrange(); } }],
      selCol: colN('Wire', function (r) { return r.sel ? 'twists' : 'bends'; }), types: function () { return ['time']; },
      views: { main: [[X0 + 0.4, 0.6, 1.05], [X0, 0.35, Z0]], frame: [[X0 + 0.5, 0.7, 1.0], [X0, 0.4, Z0]], bars: [[X0 + 0.1, 0.55, 0.3], [X0, 0.3, Z0]], tors: [[X0 + 0.2, 0.55, 0.3], [X0, 0.45, Z0]] },
      camera: { pos: [X0 + 0.45, 0.7, 1.2], look: [X0, 0.32, Z0] }, hud: function (y) { return (y[0] / DEG).toFixed(1) + '°'; }, hudLabel: 'Angle',
      dims: 'Each bar: M = ' + (p.Mb * 1000).toFixed(1) + ' g, L = ' + (p.Lbar * 100).toFixed(1) + ' cm, breadth b = ' + (p.wb * 1000).toFixed(1) + ' mm, so I = M (L² + b²)/12 = ' + (I * 1e4).toFixed(3) + ' × 10⁻⁴ kg m². Wire: l = ' + (p.lw * 100).toFixed(1) + ' cm, r = ' + (p.rw * 1000).toFixed(3) + ' mm.',
      formula: 'Y = 8π I l / (T1² r⁴),   η = 8π I l / (T2² r⁴)', formulaNote: 'T1: bars swing and bend the wire; T2: one bar twists the wire. Poisson\'s ratio σ = T2² / (2 T1²) − 1.',
      book: ['Aim: Y, η and σ of ' + MAT.name + ' by Searle\'s method.', 'I = ' + (I * 1e4).toFixed(3) + '×10⁻⁴ kg m²,  l = ' + (p.lw * 100).toFixed(1) + ' cm,  r = ' + (p.rw * 1000).toFixed(3) + ' mm', 'Y = 8π I l/(T1² r⁴),  η = 8π I l/(T2² r⁴)', 'σ = T2²/(2 T1²) − 1'],
      plan: [{ sel: 0, type: 'time' }, { sel: 0, type: 'time' }, { sel: 1, type: 'time' }, { sel: 1, type: 'time' }],
      enough: function (rows) { return TT(rows) ? '' : 'Time both kinds of oscillation.'; },
      result: function (rows) { var q = TT(rows); if (!q) return null; var Y = 8 * PI * I * p.lw / (q[0] * q[0] * r4), eta = 8 * PI * I * p.lw / (q[1] * q[1] * r4), sg = q[1] * q[1] / (2 * q[0] * q[0]) - 1;
        return { label: 'Y (' + MAT.name + ')', value: Y / 1e9, unit: 'GPa', digits: 1, truth: p.Y / 1e9, note: 'T1 = ' + q[0].toFixed(4) + ' s, T2 = ' + q[1].toFixed(4) + ' s. Modulus of rigidity η = ' + (eta / 1e9).toFixed(1) + ' GPa (true ' + (p.eta / 1e9).toFixed(1) + '). Poisson\'s ratio σ = T2²/(2T1²) − 1 = ' + sg.toFixed(3) + ' (true ' + (p.Y / (2 * p.eta) - 1).toFixed(3) + ').' }; },
      tol: 0.03, amp: function () { return [p.th0, 0]; },
      viva: [['Which quantity needs no measurement of length or mass at all?', ['Poisson\'s ratio', 'Young\'s modulus', 'The modulus of rigidity'], 0, 'σ = T2²/(2T1²) − 1 contains only the two periods.']],
      chips: ['Why does the wire bend in the first case?', 'How do I get Poisson\'s ratio?', 'Check my readings', 'Why is my Y different?'] };
  }

  L = KN === 'w7_coupled' ? buildCoupled() : KN === 'w7_spring' ? buildSpring() : KN === 'w7_torsion' ? buildTorsion() : buildPendulum();
  if (!L.settings) L.settings = [{ label: 'Ready', apply: function () {} }];
  hudA = S.hudCard(L.hudLabel); hudB = S.hudCard('Stopwatch'); hudC = S.hudCard('Oscillations');
  L.pose(sim.y);

  // ================================================================== the common procedure
  function zero() { sim = K.init(p); sim.y = sim.y.map(function () { return 0; }); st.running = false; st.run = null; st.armed = false; st.released = false; watch.on = false; }
  function grabObj() { return L.grabFor ? L.grabFor() : L.grab; }
  function grabPoint() { var w = new T.Vector3(); grabObj().getWorldPosition(w); return w; }
  function measureAll() { if (st.dims) return; st.dims = true; if (L.onStart) L.onStart(); S.say(L.dims + ' Written in your record book.'); S.book.draw(); S.render(); }
  function choose(i) {
    if (S.hand.busy) return Promise.resolve();
    if (st.run) { S.say('Finish the run first.'); return Promise.resolve(); }
    return (L.tapObj && i !== st.sel ? carryTap(L.tapObj) : Promise.resolve()).then(function () { st.sel = i; L.settings[i].apply(); zero(); st.stat = null; S.render(); });
  }
  function setSlider(v) { if (st.run) { S.say('Finish the run first.'); return; } var s = L.slider; v = Math.max(s.min, Math.min(s.max, v)); s.set(v); zero(); st.stat = null; }
  function readStatic() { if (st.running) { S.say('Stop the oscillation and read the pointer at rest.'); return; } st.stat = L.stat.read(); S.say('Pointer reads ' + st.stat + ' ' + L.stat.unit + '.'); if (S.views.ruler) S.focus('ruler'); S.render(); }
  function release() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.dims) { S.say('Measure the apparatus first.'); return Promise.resolve(); }
    if (st.run) { S.say('A run is in progress.'); return Promise.resolve(); }
    if (L.stat && st.stat === null) { S.say('Read the pointer at rest first.'); return Promise.resolve(); }
    st.running = false; var y1 = L.amp(), start = grabPoint();
    return S.hand.pinchMove(start, function (k) { sim.y = y1.map(function (v, i) { return i % 2 ? 0 : v * k; }); L.pose(sim.y); return grabPoint(); },
      function (k) { sim.y = y1.map(function (v, i) { return i % 2 ? 0 : v * k; }); }, { ms: 1000 })
      .then(function () { sim = K.init(p); sim.y = y1.slice(); st.running = true; st.released = true; S.render(); });
  }
  function stopBody() { if (st.run) { S.say('Finish the run first.'); return; } zero(); S.render(); }
  function startRun(type) {
    if (S.hand.busy) return Promise.resolve();
    if (!st.running) { S.say('Displace and release the body first.'); return Promise.resolve(); }
    if (st.run) return Promise.resolve();
    if (L.types(st.sel).indexOf(type) < 0) { S.say('That reading does not belong to this arrangement.'); return Promise.resolve(); }
    return (L.noWatch ? Promise.resolve() : S.hand.tap(watch.start)).then(function () { S.click(2400); st.run = type; st.armed = true; st.n = 0; st.k = 0; st.pk = []; st.mins = []; watch.t = 0; S.render(); });
  }
  function finish(msg) { st.run = null; st.armed = false; watch.on = false; S.say(msg); S.click(2000); S.render(); }
  function baseRow(type) { var r = { type: type, sel: st.sel }, b = L.rowBase ? L.rowBase() : {}; Object.keys(b).forEach(function (k) { r[k] = b[k]; }); return r; }
  function stepOnce(dt) {
    var y0 = sim.y.slice(), t0 = sim.t; K.step(sim, p, dt); var y1 = sim.y, tc, fr, a, r;
    if (!st.run) return;
    if (st.run === 'time') {
      if (y0[0] > 0 && y1[0] <= 0) { tc = t0 + dt * y0[0] / (y0[0] - y1[0]);
        if (st.armed) { st.armed = false; st.t0 = tc; st.n = 0; watch.on = true; }
        else { st.n++; if (st.n >= L.N) { var res = L.tRes || 0.01, tt = Math.round((tc - st.t0) / res) * res; r = baseRow('time'); r.n = L.N; r.t = tt; r.T = tt / L.N; watch.t = tt; S.addRow(r);
          if (L.lcd) L.lcd((tt / L.N).toFixed(4) + ' s'); finish(L.N + ' oscillations in ' + tt.toFixed(L.tDigits || 2) + ' s: T = ' + (tt / L.N).toFixed(L.TDigits || 3) + ' s. Written in the table.'); return; } } }
      if (!st.armed) watch.t = sim.t - st.t0;
    } else if (st.run === 'decay') {
      if (y0[1] > 0 && y1[1] <= 0 && y0[0] > 0) { fr = y0[1] / (y0[1] - y1[1]); tc = t0 + dt * fr; a = y0[0] + fr * (y1[0] - y0[0]);
        if (st.armed) { st.armed = false; st.t0 = tc; st.k = 0; watch.on = true; }
        else st.k++;
        if (st.k % L.decay.step === 0) { r = baseRow('decay'); r.n = st.k; r.t = Math.round((tc - st.t0) * 10) / 10; r.A = L.decay.read(a); S.addRow(r); }
        if (st.k >= L.decay.max) { watch.t = tc - st.t0; finish('Amplitude read every ' + L.decay.step + ' oscillations up to ' + L.decay.max + '. Plot ln(A0/A) against t.'); return; } }
      if (!st.armed) watch.t = sim.t - st.t0;
    } else if (st.run === 'beat') {
      if (st.armed) { st.armed = false; st.t0 = sim.t - dt; watch.on = true; }
      if (y0[1] !== 0 && y0[1] * y1[1] <= 0) { fr = y0[1] / (y0[1] - y1[1]); st.pk.push([t0 + dt * fr, Math.abs(y0[0] + fr * (y1[0] - y0[0]))]); var n = st.pk.length;
        if (n >= 3) { var a0 = st.pk[n - 3], a1 = st.pk[n - 2], a2 = st.pk[n - 1];
          if (a1[1] < a0[1] && a1[1] <= a2[1]) { st.mins.push(a1[0] + (a2[0] - a0[0]) / 2 * (a0[1] - a2[1]) / (a0[1] + a2[1]));
            if (st.mins.length >= 2) { r = baseRow('beat'); r.Tb = Math.round((st.mins[1] - st.mins[0]) * 10) / 10; watch.t = r.Tb; S.addRow(r); finish('Body A stood still twice, ' + r.Tb.toFixed(1) + ' s apart: that is the beat period.'); return; } } } }
      watch.t = sim.t - st.t0;
    }
  }
  var typeLabel = { time: function () { return L.noWatch ? 'Read ' + L.N + ' periods from the display' : 'Time ' + L.N + ' oscillations'; }, decay: function () { return 'Read the amplitude every ' + L.decay.step + ' oscillations'; }, beat: function () { return 'Time the beats'; } };
  function setSpeed(v) { st.speed = v; S.render(); }

  var cols = L.columns || timeCols(L.selCol || colN('Run', function (r) { return r.type; })).concat(L.extraCols || []);
  var views = L.views; views.sw = [[0.75, 0.4, 0.75], [0.6, 0.03, 0.14]]; views.book = [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]];

  return {
    camera: L.camera, views: views,
    theory: { principle: S.lab.theory, formula: L.formula, formulaNote: L.formulaNote, more: [S.lab.aim], precautions: S.lab.safety + ' Start and stop the count as the body passes its rest position, where it moves fastest. Keep the amplitude small unless the experiment asks otherwise.' },
    book: { title: 'Expt. — ' + L.name, lines: L.book, columns: cols },
    graph: L.graph, result: L.result, tol: L.tol, chips: L.chips, viva: L.viva,
    askState: function () { return { set_up: L.name, sample: SAMPLE || 'as described', arrangement: L.slider ? L.slider.label + ' = ' + L.slider.get() + ' ' + L.slider.unit : L.settings[st.sel].label, oscillating: st.running, run_in_progress: st.run || 'none',
      oscillations_counted: st.run === 'decay' ? st.k : st.n, stopwatch_s: +watch.t.toFixed(2), reading_now: L.hud(sim.y), rows_recorded: S.rows.length, still_needed: L.enough(S.rows) || 'nothing' }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'main', render: function (u) {
          u.h2('Measure the apparatus');
          u.p(S.lab.steps && S.lab.steps[0] ? S.lab.steps[0] : 'Note the dimensions you will need.');
          u.task('Measure and note the constants', st.dims, st.dims ? L.dims : 'Metre scale, vernier callipers, screw gauge and balance as needed')
            .add(u.button(st.dims ? 'Measured' : 'Measure', measureAll, !st.dims, st.dims));
          if (SAMPLE) u.note('Sample: ' + SAMPLE + '.');
          u.next('Next: take the readings', st.dims);
        },
        ok: function () { return st.dims; }, auto: function () { measureAll(); return Promise.resolve(); } },
      { id: 'runs', title: 'Readings', view: 'main', render: function (u) {
          u.h2('Release, then take the reading');
          if (L.slider) u.slider(L.slider.label, L.slider.min, L.slider.max, L.slider.step, L.slider.get, function (v) { setSlider(v); }, L.slider.unit);
          if (L.settings.length > 1) { var r0 = u.row(); L.settings.forEach(function (s, i) { r0.appendChild(u.button((st.sel === i ? '✓ ' : '') + s.label, function () { choose(i); }, false, !!st.run || S.hand.busy)); }); }
          if (L.stat) u.task('1. ' + L.stat.label + ' (at rest)', st.stat !== null, st.stat !== null ? st.stat + ' ' + L.stat.unit : 'The extension for this load')
            .add(u.button('Read the pointer', readStatic, st.stat === null, st.running));
          u.task((L.stat ? '2. ' : '1. ') + 'Displace and release', st.running, st.running ? 'Oscillating' : 'The hand draws the body aside and lets go')
            .add(u.button(st.running ? 'Oscillating…' : 'Displace and release', function () { release(); }, !st.running, st.running || S.hand.busy))
            .add(u.button('Stop', stopBody, false, !st.running || !!st.run));
          var tk = u.task((L.stat ? '3. ' : '2. ') + 'Take the reading', false, st.run ? 'Running…' : 'Starts as the body passes its rest position');
          L.types(st.sel).forEach(function (ty) { tk.add(u.button(typeLabel[ty](), function () { startRun(ty); }, st.running && !st.run, !st.running || !!st.run || S.hand.busy)); });
          var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
          [1, 4, 10].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
          u.live(function () { return L.hudLabel + ' ' + L.hud(sim.y) + ' · stopwatch ' + watch.t.toFixed(2) + ' s · count ' + (st.run === 'decay' ? st.k : st.n); });
          u.h3('Observation table'); u.table();
          var need = L.enough(S.rows); if (need) u.p(need);
          u.next('Next: work out the result', !need && !st.run);
        },
        ok: function () { return !L.enough(S.rows) && !st.run; },
        auto: function () {
          return L.plan.reduce(function (pr, q) { return pr.then(function () {
            var pre = q.sel !== undefined ? choose(q.sel) : Promise.resolve();
            return pre.then(function () { if (q.slider !== undefined) setSlider(q.slider); if (L.stat) readStatic(); return release(); })
              .then(function () { S.advance(0.3); return startRun(q.type); })
              .then(function () { S.advance(900, function () { return !st.run; }); stopBody(); }); }); }, Promise.resolve()); } },
    ],
    tick: function (dt) {
      if (st.running) { for (var i = 0; i < st.speed; i++) { stepOnce(dt); if (!st.running) break; } }
      L.pose(sim.y);
      hudA.set(L.hud(sim.y)); hudB.set(watch.t.toFixed(2) + ' s'); hudC.set(String(st.run === 'decay' ? st.k : st.n));
    },
  };
});
