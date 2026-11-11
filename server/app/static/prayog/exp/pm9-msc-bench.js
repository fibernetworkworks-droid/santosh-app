/* Prayogshala studio RIG: the M.Sc. bench of wave 9 (pack pg_matter_w9, kernels pm9_*).
   One rig draws the apparatus of 23 set-ups (each a "kit") and walks them the same honest way: every kernel is a
   SWEEP - the student sets one control x in one or more stages, takes a reading, records it. Every reading comes from
   KN.read(p, stage, x, k) on the lab's own params (k numbers the reading, so a count is the same Poisson number the
   server's check draws); the result is KN.fit(rows, p), the same fit the server checks against the textbook relation.
   Kits: GM castle, spark counter, proportional counter / scintillation spectrometer + MCA, magnetic beta spectrometer,
   coincidence table, Hall magnet, furnace, oil bath, monochromator rail, cryostat + lock-in, Stefan enclosure / lamp,
   X-ray cabinet, LC ladder, pulse-echo block, sound tube, Lecher line, waveform analyser, transducer stations and the
   microwave goniometer. */
HoolaStudio.define('pm9-msc-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KNAME = S.lab.kernel, KN = HK.K[KNAME];
  var p = HK.paramsFor(KNAME, S.lab.params);
  var V_ = S.lab.variant || {};
  var DEG = Math.PI / 180;
  var st = { on: false, s: 0, x: 0, idx: 0, last: null, lastIdx: -1, rec: -1, counting: false, shown: 0, prep: {}, fill: 0 };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function f(v, d) { return (v === null || v === undefined || !isFinite(v)) ? '-' : Number(v).toFixed(d); }
  function wp(o) { var v = new T.Vector3(); o.updateMatrixWorld(true); o.getWorldPosition(v); return v; }
  function mat(c, r, m) { return new T.MeshStandardMaterial({ color: c, roughness: r === undefined ? 0.5 : r, metalness: m || 0 }); }
  function cyl(r1, r2, h, m, seg) { return S.mesh(new T.CylinderGeometry(r1, r2, h, seg || 28), m); }
  function bx(w, h, d, m) { return S.mesh(new T.BoxGeometry(w, h, d), m); }
  function lbl(text, w, color, bg) { return S.label(text, { w: w, ratio: 0.18, color: color || '#f2f2f2', bg: bg }); }
  function add(parent, o, x, y, z) { o.position.set(x, y, z); parent.add(o); return o; }
  var G = function (x, z, ry) { var g = new T.Group(); g.position.set(x || 0, 0, z || 0); g.rotation.y = ry || 0; S.scene.add(g); return g; };

  // ======================================================================== instrument box (case, printed panel, screen, knob, button)
  function instr(o) {
    var g = G(o.x, o.z, o.ry), W = o.w || 0.3, D = o.d || 0.22, H = o.h || 0.12;
    var cs = S.rounded(W, D, H, 0.01, mat(o.color || 0xd7d3c9, 0.5, 0.12)); cs.rotation.x = -Math.PI / 2; cs.position.y = H / 2 + 0.004; g.add(cs);
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (q) { add(g, cyl(0.008, 0.009, 0.004, M.rubber, 12), q[0] * (W / 2 - 0.02), 0.002, q[1] * (D / 2 - 0.02)); });
    var FZ = D / 2 + 0.006, PW = W - 0.014, PH = H - 0.014;
    var tex = S.canvasTex(1024, Math.round(1024 * PH / PW), function (x, w, h) {
      x.fillStyle = o.panel || '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 3; x.strokeRect(8, 8, w - 16, h - 16);
      x.fillStyle = '#f1efe8'; x.font = '700 ' + Math.round(h * 0.11) + 'px "Public Sans", sans-serif'; x.fillText(o.title || '', 22, h * 0.15);
      x.font = '500 ' + Math.round(h * 0.07) + 'px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText(o.sub || '', 22, h * 0.26);
      x.textAlign = 'center'; x.fillStyle = '#f1efe8'; x.font = '600 ' + Math.round(h * 0.07) + 'px "Public Sans", sans-serif';
      x.fillText(o.knobLabel || 'ADJUST', w * 0.84, h * 0.9); x.fillText('POWER', w * 0.65, h * 0.9);
    });
    var face = bx(PW, PH, 0.004, [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]);
    face.position.set(0, 0.004 + H / 2, FZ - 0.002); g.add(face);
    var scrW = PW * 0.56, scrH = PH * 0.56, live = S.liveTex(640, Math.round(640 * scrH / scrW));
    var bez = bx(scrW + 0.008, scrH + 0.008, 0.003, M.black); bez.position.set(-PW / 2 + scrW / 2 + 0.012, 0.004 + H / 2 - PH * 0.08, FZ + 0.001); g.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(scrW, scrH), new T.MeshBasicMaterial({ map: live, toneMapped: false }));
    scr.position.set(bez.position.x, bez.position.y, FZ + 0.0035); g.add(scr);
    var knob = new T.Group(); knob.position.set(PW * 0.34, 0.004 + H / 2 - PH * 0.08, FZ); g.add(knob);
    var sk = cyl(0.016, 0.017, 0.004, M.bakelite, 32); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; knob.add(sk);
    var kb = cyl(0.012, 0.014, 0.014, M.black, 32); kb.rotation.x = Math.PI / 2; kb.position.z = 0.01; knob.add(kb);
    var kp = bx(0.002, 0.012, 0.001, M.white); kp.position.set(0, 0.007, 0.0175); knob.add(kp);
    var btn = cyl(0.007, 0.007, 0.008, M.green, 20); btn.rotation.x = Math.PI / 2; btn.position.set(PW * 0.15, 0.004 + H / 2 - PH * 0.08, FZ + 0.004); g.add(btn);
    var led = cyl(0.003, 0.003, 0.003, mat(0x401010, 0.4), 12); led.rotation.x = Math.PI / 2; led.position.set(PW * 0.15, 0.004 + H / 2 + PH * 0.12, FZ + 0.002); g.add(led);
    S.contact(W + 0.08, D + 0.08, o.x, o.z, 0.5);
    var lastSig = '';
    return { g: g, knob: knob, btn: btn, led: led, H: H, FZ: FZ,
      draw: function (sig, fn) { if (sig === lastSig) return; lastSig = sig; live.draw(fn); },
      power: function (on) { led.material = on ? mat(0x30ff50, 0.3) : mat(0x401010, 0.4); } };
  }
  function screenText(x, w, h, lines, pts, opts) {
    opts = opts || {};
    x.fillStyle = opts.bg || '#0d1a14'; x.fillRect(0, 0, w, h);
    var ink = opts.ink || '#7dffb0';
    x.fillStyle = ink; x.font = '600 ' + Math.round(h * 0.11) + 'px "JetBrains Mono", monospace';
    (lines || []).forEach(function (t, i) { x.fillText(t, 14, h * (0.16 + 0.13 * i)); });
    if (pts && pts.length) {
      var X0 = w * 0.08, X1 = w * 0.96, Y0 = h * 0.94, Y1 = h * (0.2 + 0.13 * (lines || []).length);
      var xs = pts.map(function (q) { return q[0]; }), ys = pts.map(function (q) { return q[1]; });
      var xa = Math.min.apply(null, xs), xb = Math.max.apply(null, xs), ya = Math.min(0, Math.min.apply(null, ys)), yb = Math.max.apply(null, ys);
      if (xb === xa) xb = xa + 1; if (yb === ya) yb = ya + 1;
      x.strokeStyle = 'rgba(125,255,176,.3)'; x.lineWidth = 2; x.strokeRect(X0, Y1, X1 - X0, Y0 - Y1);
      x.fillStyle = ink;
      pts.forEach(function (q) { var px = X0 + (q[0] - xa) / (xb - xa) * (X1 - X0), py = Y0 - (q[1] - ya) / (yb - ya) * (Y0 - Y1);
        x.fillRect(px - 3, py - 3, 6, 6); });
    }
  }
  function stand(x, z, h) {
    var g = G(x, z);
    var base = S.rounded(0.14, 0.1, 0.012, 0.004, M.iron); base.rotation.x = -Math.PI / 2; base.position.y = 0.006; g.add(base);
    add(g, cyl(0.005, 0.005, h, M.chrome, 16), 0.0, h / 2, -0.03);
    S.contact(0.18, 0.14, x, z, 0.5);
    return g;
  }
  function trefoil() {
    return S.canvasTex(128, 128, function (x, w, h) {
      x.fillStyle = '#f2d02a'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b1b1b';
      x.beginPath(); x.arc(w / 2, h / 2, 10, 0, Math.PI * 2); x.fill();
      for (var i = 0; i < 3; i++) { x.beginPath(); x.arc(w / 2, h / 2, 46, i * 2.094 - 0.45, i * 2.094 + 0.45);
        x.arc(w / 2, h / 2, 18, i * 2.094 + 0.45, i * 2.094 - 0.45, true); x.closePath(); x.fill(); } });
  }
  var TREF = trefoil();
  function source(color) {
    var g = new T.Group();
    g.add(cyl(0.0085, 0.0085, 0.004, mat(color || 0xb8322a, 0.4, 0.3), 24));
    var t = new T.Mesh(new T.CircleGeometry(0.008, 24), new T.MeshStandardMaterial({ map: TREF, roughness: 0.6 }));
    t.rotation.x = -Math.PI / 2; t.position.y = 0.0021; g.add(t);
    var rim = S.mesh(new T.TorusGeometry(0.0085, 0.0012, 8, 24), M.chrome); rim.rotation.x = Math.PI / 2; g.add(rim);
    return g;
  }
  function protractorTex() {
    return S.canvasTex(1024, 1024, function (x, w) { x.fillStyle = '#f2ede0'; x.fillRect(0, 0, w, w); x.strokeStyle = '#222'; x.fillStyle = '#222';
      for (var a = 0; a < 360; a++) { var r1 = a % 10 ? 470 : (a % 30 ? 450 : 430), t = a * DEG; x.lineWidth = a % 10 ? 1.5 : 3;
        x.beginPath(); x.moveTo(512 + Math.cos(t) * 500, 512 - Math.sin(t) * 500); x.lineTo(512 + Math.cos(t) * r1, 512 - Math.sin(t) * r1); x.stroke(); }
      x.font = '600 30px "Public Sans", sans-serif'; x.textAlign = 'center';
      for (a = 0; a < 360; a += 30) { var tt = a * DEG, v = a <= 180 ? a : 360 - a; x.fillText(String(v), 512 + Math.cos(tt) * 395, 522 - Math.sin(tt) * 395); } });
  }
  function scopeBox(x, z, title, sub, knobLabel) { return instr({ x: x, z: z, ry: -0.25, w: 0.3, d: 0.22, h: 0.15, color: 0x4b5260, panel: '#1f2630', title: title, sub: sub, knobLabel: knobLabel }); }

  // ======================================================================== kits
  var K = { parts: {}, views: {}, ctl: null, main: null, aux: [] };      // ctl: {kind, apply(v, s), pt() | box}
  var srcs = [];

  function kitGM() {
    var castle = G(-0.3, -0.3);
    var leadM = mat(0x53565c, 0.72, 0.55);
    function brick(x, y, z, w, h, d) { var b = S.rounded(w, d, h, 0.004, leadM); b.rotation.x = -Math.PI / 2; b.position.set(x, y + h / 2, z); castle.add(b); }
    for (var r = 0; r < 4; r++) { brick(-0.105, r * 0.045, 0, 0.05, 0.044, 0.22); brick(0.105, r * 0.045, 0, 0.05, 0.044, 0.22); brick(0, r * 0.045, -0.085, 0.16, 0.044, 0.05); }
    brick(0, 0.18, -0.072, 0.26, 0.03, 0.095);
    add(castle, cyl(0.005, 0.005, 0.17, M.chrome, 16), -0.052, 0.085, 0.05); add(castle, cyl(0.005, 0.005, 0.17, M.chrome, 16), 0.052, 0.085, 0.05);
    var shelf = add(castle, bx(0.12, 0.0025, 0.07, M.alu), 0, 0.082, 0.05);
    var tube = new T.Group(); add(castle, tube, 0, 0.168, 0.05);
    add(tube, cyl(0.016, 0.016, 0.03, M.bakelite), 0, 0.018, 0);
    add(tube, cyl(0.0135, 0.0135, 0.05, mat(0x9aa2ab, 0.32, 0.75)), 0, -0.016, 0);
    add(tube, cyl(0.0115, 0.0115, 0.0015, mat(0xd8d2bd, 0.5)), 0, -0.0415, 0);
    var tl = lbl('GM END WINDOW', 0.028, '#2b2f36'); add(tube, tl, 0, -0.016, 0.0138);
    K.parts.castle = castle; K.parts.tube = tube; K.parts.shelf = shelf;
    S.contact(0.3, 0.26, -0.3, -0.3, 0.5);
    S.addApparatus('castle', castle, 'Lead castle with an end-window GM tube', 'Lead bricks keep the background down; the sample sits on the shelf a fixed distance below the mica window.');
    K.views.app = [[-0.18, 0.48, 0.28], [-0.3, 0.1, -0.26]];
    var pot = G(-0.05, -0.14); add(pot, cyl(0.03, 0.032, 0.03, leadM), 0, 0.015, 0); add(pot, cyl(0.014, 0.014, 0.022, mat(0x17181b)), 0, 0.021, 0);
    S.addApparatus('pot', pot, 'Lead source store', 'The sources live here, lid on, whenever a reading is not being taken.');
    var unit = instr({ x: 0.36, z: -0.26, ry: -0.3, w: 0.36, h: 0.13, title: 'SCALER - TIMER', sub: 'GM E.H.T. 250 - 800 V  ·  PRESET TIME', knobLabel: 'E.H.T.' });
    K.main = unit; S.addApparatus('unit', unit.g, 'Scaler-timer', 'The knob sets the tube voltage; START counts for the preset time.');
    K.views.unit = [[0.42, 0.42, 0.34], [0.36, 0.07, -0.26]];
    S.wire([[-0.3, 0.2, -0.25], [-0.3, 0.27, -0.38], [-0.05, 0.03, -0.45], [0.22, 0.03, -0.32]], 'black');
    return castle;
  }
  function shelfPt(dx) { var c = K.parts.castle; return wp(c).add(new T.Vector3(dx || 0, 0.085, 0.05)); }

  function kitSpark() {
    var g = G(-0.32, -0.28);
    var base = S.rounded(0.5, 0.14, 0.014, 0.004, M.darkWood); base.rotation.x = -Math.PI / 2; base.position.y = 0.007; g.add(base);
    var rail = add(g, bx(0.42, 0.01, 0.025, M.alu), 0.02, 0.019, 0);
    var sc = S.canvasTex(1024, 64, function (x, w, h) { x.fillStyle = '#f0ead8'; x.fillRect(0, 0, w, h); x.fillStyle = '#111';
      for (var i = 0; i <= 80; i++) { var xx = i * w / 80; x.fillRect(xx, 0, i % 10 ? 1.5 : 3, i % 10 ? 18 : 34); if (i % 10 === 0) { x.font = '600 26px sans-serif'; x.fillText(String(i / 10), xx + 3, 58); } } });
    var strip = new T.Mesh(new T.PlaneGeometry(0.4, 0.016), new T.MeshStandardMaterial({ map: sc })); strip.rotation.x = -Math.PI / 2; add(g, strip, 0.02, 0.0245, 0.02);
    var head = new T.Group(); add(g, head, -0.2, 0, 0);
    add(head, bx(0.012, 0.09, 0.08, M.bakelite), 0, 0.06, 0);
    add(head, bx(0.003, 0.05, 0.05, M.brass), 0.008, 0.06, 0);
    var wire = cyl(0.0005, 0.0005, 0.05, M.chrome, 6); wire.rotation.x = Math.PI / 2; add(head, wire, 0.012, 0.06, 0);
    var sl = lbl('SPARK COUNTER', 0.06, '#f2f2f2'); sl.rotation.y = Math.PI / 2; add(head, sl, 0.007, 0.1, 0);
    var car = new T.Group(); add(g, car, 0, 0, 0);
    add(car, bx(0.03, 0.02, 0.04, M.alu), 0, 0.034, 0);
    var s = source(0x3d6fb2); s.rotation.z = Math.PI / 2; add(car, s, -0.016, 0.06, 0); add(car, cyl(0.002, 0.002, 0.02, M.chrome, 8), -0.005, 0.05, 0);
    K.parts.car = car; K.parts.sparkG = g;
    S.contact(0.56, 0.2, -0.32, -0.28, 0.5);
    S.addApparatus('spark', g, 'Spark counter and source carriage', 'A fine wire a millimetre above a brass plate at a few kilovolts; the Am-241 source on the carriage faces it across a measured air gap.');
    K.views.app = [[-0.3, 0.32, 0.22], [-0.32, 0.05, -0.28]];
    var eht = instr({ x: 0.22, z: -0.38, ry: -0.15, w: 0.24, h: 0.11, title: 'E.H.T. UNIT', sub: '0 - 6 kV', knobLabel: 'kV' });
    var unit = instr({ x: 0.55, z: -0.22, ry: -0.35, w: 0.3, h: 0.12, title: 'SCALER - TIMER', sub: 'PRESET TIME', knobLabel: 'SET' });
    K.main = unit; K.aux.push(eht);
    S.addApparatus('eht', eht.g, 'E.H.T. unit', 'Sets the voltage across the spark gap.');
    S.addApparatus('unit', unit.g, 'Scaler-timer', 'Counts the sparks for the preset time.');
    K.views.unit = [[0.4, 0.42, 0.34], [0.38, 0.07, -0.3]];
    S.wire([[-0.52, 0.06, -0.28], [-0.1, 0.02, -0.45], [0.15, 0.04, -0.38]], 'red');
    S.wire([[-0.52, 0.06, -0.26], [0.1, 0.02, -0.12], [0.45, 0.04, -0.2]], 'black');
    function carX(d) { return -0.2 + 0.016 + 0.012 + d / 100; }
    car.position.x = carX(1.0);
    return { carX: carX };
  }

  function kitMCA(kind) {
    var g = G(-0.33, -0.3);
    var st0 = stand(-0.33, -0.3, 0.26); void st0;
    var det = new T.Group(); add(g, det, 0, 0, 0.02);
    if (kind === 'prop') {
      var body = cyl(0.025, 0.025, 0.2, mat(0xb9bec6, 0.3, 0.8)); body.rotation.z = Math.PI / 2; add(det, body, 0, 0.12, 0);
      var win = cyl(0.009, 0.009, 0.002, mat(0x6f6a5a, 0.6)); add(det, win, 0, 0.146, 0);
      add(det, cyl(0.004, 0.004, 0.03, M.brass, 8), 0.1, 0.12, 0).rotation.z = Math.PI / 2;
      var pa = add(det, bx(0.06, 0.05, 0.05, mat(0x2f6fb0, 0.45, 0.3)), 0.13, 0.12, 0);
      var pl = lbl('PREAMP', 0.04); add(pa, pl, 0, 0, 0.026);
      add(det, bx(0.004, 0.004, 0.06, M.black), -0.08, 0.1, 0);
      var gl = lbl('Ar-CH4 PROPORTIONAL COUNTER', 0.12, '#2b2f36'); add(det, gl, 0, 0.12, 0.026);
      var sr = source(0x3d6fb2); add(det, sr, 0, 0.152, 0); K.parts.src = sr;
      K.parts.det = det;
      S.addApparatus('det', g, 'Argon-methane proportional counter', 'A thin anode wire on the axis of a metal cylinder of flowing argon-methane, a beryllium window on top; the preamplifier on its end.');
    } else {
      add(det, cyl(0.026, 0.026, 0.05, mat(0xe8e1c8, 0.3, 0.1)), 0, 0.05, 0);
      add(det, cyl(0.028, 0.028, 0.12, mat(0x1f2329, 0.4, 0.4)), 0, 0.135, 0);
      add(det, cyl(0.03, 0.03, 0.02, M.alu), 0, 0.2, 0);
      var dl = lbl('ANTHRACENE + PMT', 0.07, '#f2f2f2'); add(det, dl, 0, 0.13, 0.029);
      var sh = add(det, cyl(0.03, 0.03, 0.006, M.alu), 0, 0.012, 0); void sh;
      var sr2 = source(0xb8322a); add(det, sr2, 0, 0.02, 0); K.parts.src = sr2;
      S.addApparatus('det', g, 'Anthracene scintillation spectrometer', 'An anthracene crystal on a photomultiplier tube, looking down at the beta source through a thin window.');
    }
    S.contact(0.3, 0.2, -0.33, -0.28, 0.5);
    K.views.app = [[-0.25, 0.36, 0.22], [-0.33, 0.12, -0.28]];
    var nim = instr({ x: 0.08, z: -0.42, ry: -0.05, w: 0.28, h: 0.16, color: 0x8b8f96, panel: '#3a3f47', title: 'NIM BIN', sub: 'H.V.  ·  AMPLIFIER  ·  ADC', knobLabel: 'H.V.' });
    var mca = instr({ x: 0.5, z: -0.24, ry: -0.35, w: 0.36, h: 0.16, color: 0x30343b, panel: '#1c2027', title: 'MULTICHANNEL ANALYSER', sub: '1024 CHANNELS  ·  CURSOR', knobLabel: 'CURSOR' });
    K.main = mca; K.aux.push(nim);
    S.addApparatus('nim', nim.g, 'NIM bin', 'The detector high voltage and the shaping amplifier.');
    S.addApparatus('unit', mca.g, 'Multichannel analyser', 'Sorts the pulses by height into channels; the cursor reads the counts in any channel.');
    K.views.unit = [[0.46, 0.44, 0.36], [0.4, 0.08, -0.28]];
    S.wire([[-0.2, 0.12, -0.28], [-0.05, 0.03, -0.35], [0.02, 0.05, -0.42]], 'black');
    S.wire([[0.2, 0.06, -0.4], [0.32, 0.03, -0.3], [0.38, 0.05, -0.24]], 'black');
  }

  function kitMagspec() {
    var g = G(-0.33, -0.3);
    var yoke = mat(0x2f4f86, 0.45, 0.4);
    [-1, 1].forEach(function (sg) { add(g, cyl(0.11, 0.11, 0.03, yoke, 40), 0, 0.09 + sg * 0.045, 0); add(g, cyl(0.12, 0.12, 0.02, mat(0xb87333, 0.35, 0.6), 40), 0, 0.09 + sg * 0.075, 0); });
    add(g, bx(0.04, 0.22, 0.04, yoke), -0.15, 0.11, 0);
    var ch = new T.Mesh(new T.TorusGeometry(0.07, 0.008, 10, 40, Math.PI), mat(0xcfd3d8, 0.25, 0.85)); ch.rotation.x = Math.PI / 2; add(g, ch, 0, 0.09, 0);
    var s = source(0xb8322a); s.rotation.x = Math.PI / 2; add(g, s, 0.07, 0.09, 0.01);
    var gm = cyl(0.012, 0.012, 0.05, mat(0x9aa2ab, 0.32, 0.75)); gm.rotation.z = Math.PI / 2; add(g, gm, -0.07, 0.09, 0.03);
    var l = lbl('180° MAGNETIC BETA SPECTROMETER', 0.14, '#f2f2f2'); l.rotation.x = -Math.PI / 2; add(g, l, 0, 0.181, 0.06);
    S.contact(0.34, 0.3, -0.33, -0.3, 0.5);
    S.addApparatus('det', g, 'Magnetic beta spectrometer', 'Electrons from the source bend in a semicircle in the field between the poles; only those of the selected momentum reach the GM counter at the other end. The coil current sets the momentum.');
    K.views.app = [[-0.2, 0.42, 0.22], [-0.33, 0.1, -0.3]];
    var sup = instr({ x: 0.1, z: -0.42, ry: -0.05, w: 0.28, h: 0.12, color: 0x3a4f6e, panel: '#22324a', title: 'MAGNET SUPPLY', sub: 'COIL CURRENT 0 - 15 A', knobLabel: 'CURRENT' });
    var unit = instr({ x: 0.52, z: -0.22, ry: -0.35, w: 0.3, h: 0.12, title: 'SCALER - TIMER', sub: 'GM COUNTER', knobLabel: 'SET' });
    K.main = unit; K.aux.push(sup);
    S.addApparatus('sup', sup.g, 'Magnet supply', 'The coil current sets the field and so the momentum that reaches the counter.');
    S.addApparatus('unit', unit.g, 'Scaler-timer', 'Counts the electrons that reach the GM tube.');
    K.views.unit = [[0.36, 0.42, 0.34], [0.3, 0.07, -0.3]];
    S.wire([[-0.42, 0.09, -0.27], [-0.1, 0.02, -0.12], [0.42, 0.04, -0.2]], 'black');
    S.wire([[-0.48, 0.12, -0.3], [-0.2, 0.02, -0.46], [0.0, 0.04, -0.42]], 'red');
  }

  function kitCoinc() {
    var g = G(-0.33, -0.3);
    var tb = S.mesh(new T.CylinderGeometry(0.17, 0.17, 0.012, 64), [mat(0xcfc7b4), new T.MeshStandardMaterial({ map: protractorTex(), roughness: 0.6 }), M.grey]);
    add(g, tb, 0, 0.02, 0); add(g, cyl(0.03, 0.05, 0.014, M.iron), 0, 0.007, 0);
    var s = source(0xb8322a); add(g, s, 0, 0.03, 0);
    add(g, cyl(0.004, 0.004, 0.03, M.chrome, 8), 0, 0.04, 0);
    function det() { var d = new T.Group(); var c = cyl(0.022, 0.022, 0.06, mat(0xb9bec6, 0.3, 0.8)); c.rotation.z = Math.PI / 2; add(d, c, 0, 0.055, 0);
      var pm = cyl(0.02, 0.02, 0.09, mat(0x1f2329, 0.4, 0.4)); pm.rotation.z = Math.PI / 2; add(d, pm, 0.075, 0.055, 0);
      add(d, bx(0.15, 0.008, 0.03, M.alu), 0.06, 0.03, 0); var l = lbl('NaI(Tl)', 0.03, '#2b2f36'); add(d, l, 0, 0.055, 0.0225); return d; }
    var fixed = det(); var fg = new T.Group(); add(g, fg, 0, 0, 0); fixed.position.x = 0.1; fg.add(fixed); fg.rotation.y = Math.PI;
    var arm = new T.Group(); add(g, arm, 0, 0, 0); var mv = det(); mv.position.x = 0.1; arm.add(mv);
    var ptr = S.mesh(new T.ConeGeometry(0.006, 0.02, 3), M.red); ptr.rotation.z = Math.PI / 2; add(arm, ptr, 0.15, 0.03, 0);
    K.parts.arm = arm; K.parts.mvdet = mv;
    S.contact(0.5, 0.4, -0.33, -0.3, 0.5);
    S.addApparatus('det', g, 'Coincidence table', 'One NaI(Tl) detector fixed, the other on an arm that swings round the Co-60 source over a protractor; both 10 cm from it.');
    K.views.app = [[-0.3, 0.5, 0.2], [-0.33, 0.05, -0.3]];
    var unit = instr({ x: 0.45, z: -0.25, ry: -0.3, w: 0.36, h: 0.14, color: 0x8b8f96, panel: '#3a3f47', title: 'FAST-SLOW COINCIDENCE', sub: 'RESOLVING TIME 20 ns  ·  DELAY', knobLabel: 'SET' });
    K.main = unit; S.addApparatus('unit', unit.g, 'Coincidence unit and scaler', 'Counts only pairs of pulses that arrive together; a delay in one arm shows the chance rate.');
    K.views.unit = [[0.46, 0.42, 0.36], [0.42, 0.07, -0.26]];
    S.wire([[-0.12, 0.06, -0.3], [0.1, 0.03, -0.22], [0.3, 0.05, -0.24]], 'black');
    function setAng(th) { arm.rotation.y = Math.PI - th * DEG; }
    setAng(90);
    return { setAng: setAng };
  }

  function kitHall() {
    var g = G(-0.33, -0.32);
    var yoke = mat(0x3a4f6e, 0.45, 0.4);
    add(g, bx(0.42, 0.04, 0.12, yoke), 0, 0.02, 0);
    [-1, 1].forEach(function (sg) {
      add(g, bx(0.04, 0.16, 0.12, yoke), sg * 0.19, 0.11, 0);
      var coil = cyl(0.055, 0.055, 0.07, mat(0xb87333, 0.35, 0.6), 36); coil.rotation.z = Math.PI / 2; add(g, coil, sg * 0.13, 0.13, 0);
      var pole = cyl(0.035, 0.03, 0.05, M.iron, 32); pole.rotation.z = Math.PI / 2; add(g, pole, sg * 0.065, 0.13, 0);
    });
    var dw = cyl(0.022, 0.022, 0.16, mat(0xd9dde2, 0.2, 0.9)); add(g, dw, 0, 0.24, 0);
    add(g, cyl(0.004, 0.004, 0.08, M.chrome, 8), 0, 0.15, 0);
    var l = lbl('Ge HALL PROBE', 0.05, '#2b2f36'); add(g, l, 0, 0.26, 0.023);
    S.contact(0.5, 0.2, -0.33, -0.32, 0.5);
    S.addApparatus('det', g, 'Electromagnet with the Hall probe', 'The germanium slab on the probe sits in a small cryostat-oven between the pole pieces; B = 0.3 T.');
    K.views.app = [[-0.25, 0.42, 0.26], [-0.33, 0.14, -0.32]];
    var cc = instr({ x: 0.12, z: -0.44, ry: 0, w: 0.26, h: 0.11, color: 0x3a4f6e, panel: '#22324a', title: 'TEMPERATURE CONTROLLER', sub: '77 - 450 K  ·  PT100', knobLabel: 'SET K' });
    var dvm = instr({ x: 0.52, z: -0.24, ry: -0.35, w: 0.34, h: 0.12, title: 'CONSTANT CURRENT  +  DVM', sub: '1.000 mA  ·  Hall / sample voltage', knobLabel: 'RANGE' });
    K.main = dvm; K.aux.push(cc);
    S.addApparatus('ctrl', cc.g, 'Temperature controller', 'Sets and holds the sample temperature.');
    S.addApparatus('unit', dvm.g, 'Current source and voltmeter', 'Drives 1 mA through the slab and reads the Hall voltage and the voltage along it.');
    K.views.unit = [[0.4, 0.44, 0.36], [0.34, 0.07, -0.32]];
    S.wire([[-0.33, 0.32, -0.32], [0.0, 0.03, -0.3], [0.38, 0.05, -0.24]], 'black');
  }

  function kitFurnace() {
    var g = G(-0.33, -0.3);
    add(g, bx(0.34, 0.03, 0.12, M.iron), 0, 0.015, 0);
    var fur = cyl(0.06, 0.06, 0.26, mat(0xc9c2b5, 0.6, 0.1), 36); fur.rotation.z = Math.PI / 2; add(g, fur, 0, 0.1, 0);
    [-1, 1].forEach(function (sg) { var e = cyl(0.062, 0.062, 0.012, M.alu, 36); e.rotation.z = Math.PI / 2; add(g, e, sg * 0.13, 0.1, 0); add(g, bx(0.02, 0.04, 0.06, M.iron), sg * 0.1, 0.04, 0); });
    var rod = cyl(0.004, 0.004, 0.4, M.chrome, 8); rod.rotation.z = Math.PI / 2; add(g, rod, 0, 0.1, 0);
    var l = lbl('TUBULAR FURNACE 450 °C', 0.1, '#2b2f36'); add(g, l, 0, 0.12, 0.061);
    S.contact(0.46, 0.2, -0.33, -0.3, 0.5);
    S.addApparatus('det', g, 'Tubular furnace with a two-probe holder', 'The bar is clamped between two spring-loaded probes on a ceramic holder inside the furnace, with a thermocouple beside it.');
    K.views.app = [[-0.25, 0.36, 0.24], [-0.33, 0.1, -0.3]];
    var cc = instr({ x: 0.12, z: -0.44, ry: 0, w: 0.26, h: 0.11, color: 0x3a4f6e, panel: '#22324a', title: 'FURNACE CONTROLLER', sub: 'K-TYPE  ·  PID', knobLabel: 'SET K' });
    var dvm = instr({ x: 0.52, z: -0.24, ry: -0.35, w: 0.34, h: 0.12, title: 'CONSTANT CURRENT  +  DVM', sub: 'two-probe', knobLabel: 'RANGE' });
    K.main = dvm; K.aux.push(cc);
    S.addApparatus('ctrl', cc.g, 'Furnace controller', 'Sets and holds the furnace temperature.');
    S.addApparatus('unit', dvm.g, 'Current source and voltmeter', 'A constant current through the bar, the voltage read across the same two probes.');
    K.views.unit = [[0.4, 0.44, 0.36], [0.34, 0.07, -0.32]];
    S.wire([[-0.53, 0.1, -0.3], [0.0, 0.02, -0.15], [0.38, 0.05, -0.24]], 'black');
  }

  function kitBath(label) {
    var g = G(-0.3, -0.28);
    var hp = S.rounded(0.18, 0.18, 0.04, 0.008, mat(0xe6e3dc, 0.4, 0.1)); hp.rotation.x = -Math.PI / 2; hp.position.y = 0.02; g.add(hp);
    add(g, cyl(0.07, 0.07, 0.004, mat(0x555a60, 0.4, 0.6), 36), 0, 0.042, 0);
    var hk = cyl(0.012, 0.012, 0.01, M.black, 20); hk.rotation.x = Math.PI / 2; add(g, hk, 0.05, 0.02, 0.092); K.parts.hpk = hk;
    var bk = S.beaker(0.055, 0.12, [-0.3, 0.044, -0.28], 0xd9b866, 0.65); void bk;
    add(g, cyl(0.002, 0.002, 0.2, M.chrome, 8), 0.02, 0.15, 0);
    var th = S.thermometer({ len: 0.24, min: 0, max: 150 }); th.position.set(-0.32, 0.06, -0.3); K.parts.th = th;
    var l = lbl(label || 'OIL BATH', 0.07, '#2b2f36'); add(g, l, 0, 0.03, 0.091);
    S.addApparatus('det', g, label === 'WATER BATH' ? 'Water bath on a hot plate' : 'Stirred oil bath on a hot plate', 'The sample on long leads sits in the bath next to the thermometer; the hot plate knob sets the temperature.');
    K.views.app = [[-0.2, 0.36, 0.22], [-0.3, 0.1, -0.28]];
    var dvm = instr({ x: 0.45, z: -0.26, ry: -0.3, w: 0.34, h: 0.12, title: label === 'WATER BATH' ? 'DIGITAL OHMMETER' : 'CURRENT SOURCE  +  DVM', sub: label === 'WATER BATH' ? '4-wire' : '0.1 mA / 1 mA  ·  mV', knobLabel: 'RANGE' });
    K.main = dvm; S.addApparatus('unit', dvm.g, 'Meter', 'Reads the output of the sample.');
    K.views.unit = [[0.42, 0.42, 0.34], [0.4, 0.07, -0.26]];
    S.wire([[-0.3, 0.2, -0.28], [0.05, 0.03, -0.2], [0.3, 0.05, -0.24]], 'black');
  }

  function kitOptical() {
    S.opticalBench({ len: 0.7, x0: -0.75, z: -0.3 });
    var lamp = G(-0.6, -0.3);
    add(lamp, bx(0.06, 0.08, 0.06, mat(0x2a2d33, 0.5, 0.3)), 0, 0.09, 0);
    var lens = cyl(0.018, 0.018, 0.01, M.glass); lens.rotation.z = Math.PI / 2; add(lamp, lens, 0.035, 0.09, 0);
    add(lamp, bx(0.03, 0.02, 0.05, M.iron), 0, 0.045, 0);
    var mono = G(-0.24, -0.3);
    add(mono, bx(0.14, 0.08, 0.1, mat(0x30343b, 0.5, 0.2)), 0, 0.09, 0);
    var drum = cyl(0.02, 0.02, 0.02, M.chrome, 24); drum.rotation.x = Math.PI / 2; add(mono, drum, 0.03, 0.09, 0.06); K.parts.drum = drum;
    var ml = lbl('GRATING MONOCHROMATOR', 0.1, '#f2f2f2'); add(mono, ml, 0, 0.11, 0.051);
    var shutter = add(mono, bx(0.004, 0.04, 0.04, M.black), -0.075, 0.09, 0); K.parts.shutter = shutter;
    mono.visible = false;
    var cell = G(-0.1, -0.3);
    if (KNAME === 'pm9_gasphoto') {
      add(cell, cyl(0.016, 0.018, 0.02, M.bakelite), 0, 0.045, 0);
      add(cell, S.mesh(new T.SphereGeometry(0.024, 24, 18), M.glass), 0, 0.085, 0);
      var cath = new T.Mesh(new T.CylinderGeometry(0.016, 0.016, 0.03, 20, 1, true, Math.PI / 2, Math.PI), new T.MeshStandardMaterial({ color: 0xc9a227, metalness: 0.6, roughness: 0.3, side: T.DoubleSide })); add(cell, cath, 0.004, 0.085, 0);
      add(cell, cyl(0.0008, 0.0008, 0.03, M.chrome, 6), -0.004, 0.085, 0);
      var gl = lbl('GAS PHOTOCELL (Ar)', 0.05, '#2b2f36'); add(cell, gl, 0, 0.045, 0.019);
    } else {
      add(cell, bx(0.03, 0.06, 0.05, M.bakelite), 0, 0.08, 0);
      var w = new T.Mesh(new T.CircleGeometry(0.012, 24), mat(0xc45d1a, 0.5)); w.rotation.y = -Math.PI / 2; add(cell, w, -0.016, 0.08, 0);
      var cl = lbl(/CdSe/.test(V_.sample || '') ? 'CdSe' : 'CdS', 0.02, '#f2f2f2'); add(cell, cl, 0, 0.1, 0.026);
    }
    K.parts.lens = lens;
    K.parts.lamp = lamp; K.parts.mono = mono; K.parts.cell = cell;
    S.addApparatus('det', lamp, 'Lamp on the optical rail', 'A tungsten lamp house on a carriage; its distance from the cell is read on the rail.');
    S.addApparatus('mono', mono, 'Grating monochromator', 'Selects one wavelength; its shutter cuts the light.');
    S.addApparatus('cell', cell, 'Photoconductive cell', 'The photoconductor in its holder at the end of the rail.');
    K.views.app = [[-0.35, 0.34, 0.24], [-0.38, 0.06, -0.3]];
    var unit = instr({ x: 0.42, z: -0.26, ry: -0.3, w: 0.34, h: 0.12, title: KNAME === 'pm9_gasphoto' ? 'SUPPLY 0 - 100 V  +  µA' : 'PICOAMMETER  +  BIAS', sub: KNAME === 'pm9_gasphoto' ? 'anode voltage  ·  photocurrent' : 'µA  ·  STORAGE', knobLabel: KNAME === 'pm9_gasphoto' ? 'VOLTS' : 'RANGE' });
    K.main = unit; S.addApparatus('unit', unit.g, 'Microammeter with bias supply', 'Biases the cell and reads its current.');
    K.views.unit = [[0.42, 0.42, 0.34], [0.4, 0.07, -0.26]];
    S.wire([[-0.1, 0.1, -0.3], [0.1, 0.03, -0.2], [0.28, 0.05, -0.24]], 'red');
    return { lampX: function (d) { return -0.1 - 0.015 - d / 100 * 1.0; } };
  }

  function kitCryo(title) {
    var g = G(-0.3, -0.3);
    var dw = cyl(0.07, 0.065, 0.26, mat(0xd9dde2, 0.2, 0.9), 40); add(g, dw, 0, 0.13, 0);
    add(g, cyl(0.075, 0.075, 0.02, M.alu, 40), 0, 0.27, 0);
    add(g, cyl(0.008, 0.008, 0.1, M.chrome, 12), 0, 0.33, 0);
    add(g, bx(0.05, 0.03, 0.05, M.bakelite), 0, 0.39, 0);
    var l = lbl(title || 'LN2 CRYOSTAT', 0.08, '#2b2f36'); add(g, l, 0, 0.15, 0.071);
    S.contact(0.2, 0.2, -0.3, -0.3, 0.5);
    S.addApparatus('det', g, 'Liquid-nitrogen cryostat with the sample insert', 'The insert carries the sample, a heater and a temperature sensor down into the dewar.');
    K.views.app = [[-0.2, 0.46, 0.26], [-0.3, 0.2, -0.3]];
    var cc = instr({ x: 0.1, z: -0.44, ry: 0, w: 0.26, h: 0.11, color: 0x3a4f6e, panel: '#22324a', title: 'TEMPERATURE CONTROLLER', sub: 'Si DIODE  ·  PID', knobLabel: 'SET K' });
    var li = instr({ x: 0.5, z: -0.24, ry: -0.35, w: 0.36, h: 0.13, color: 0x30343b, panel: '#1c2027', title: 'LOCK-IN AMPLIFIER', sub: "X (in-phase)  ·  Y (out-of-phase)", knobLabel: 'SENS' });
    K.main = li; K.aux.push(cc);
    S.addApparatus('ctrl', cc.g, 'Temperature controller', 'Sets and holds the sample temperature.');
    S.addApparatus('unit', li.g, 'Lock-in amplifier', 'Drives the primary coil and reads the secondary in phase and out of phase.');
    K.views.unit = [[0.4, 0.44, 0.36], [0.32, 0.07, -0.32]];
    S.wire([[-0.3, 0.4, -0.3], [0.0, 0.03, -0.25], [0.36, 0.05, -0.24]], 'black');
  }

  function kitStefan(lamp) {
    if (!lamp) {
      var g = G(-0.3, -0.3);
      add(g, cyl(0.13, 0.13, 0.02, M.iron, 40), 0, 0.01, 0);
      var jar = S.mesh(new T.SphereGeometry(0.11, 32, 20, 0, Math.PI * 2, 0, Math.PI / 2), M.glass); jar.scale.y = 1.6; add(g, jar, 0, 0.02, 0);
      add(g, cyl(0.002, 0.002, 0.1, M.chrome, 8), 0, 0.12, 0);
      var ball = S.mesh(new T.SphereGeometry(0.02, 24, 16), mat(0x111111, 0.95)); add(g, ball, 0, 0.07, 0);
      var hose = cyl(0.008, 0.008, 0.2, M.rubber, 12); hose.rotation.z = Math.PI / 2; add(g, hose, -0.2, 0.012, 0);
      S.addApparatus('det', g, 'Blackened body in an evacuated enclosure', 'A hollow copper body coated with lamp black hangs on thin supports inside the bell jar, pumped down to stop convection; a thermocouple reads its temperature.');
      K.views.app = [[-0.22, 0.36, 0.22], [-0.3, 0.1, -0.3]];
      var sw = S.stopwatch([0.05, 0, -0.1], 0); K.parts.sw = sw;
      var unit = instr({ x: 0.45, z: -0.26, ry: -0.3, w: 0.34, h: 0.12, title: 'THERMOCOUPLE METER', sub: '°C  ·  0.1', knobLabel: 'ZERO' });
      K.main = unit; S.addApparatus('unit', unit.g, 'Thermocouple meter', 'Reads the body temperature.');
    } else {
      var lg = G(-0.3, -0.3);
      add(lg, cyl(0.03, 0.035, 0.03, M.bakelite), 0, 0.015, 0);
      var bulb = S.mesh(new T.SphereGeometry(0.035, 28, 20), M.glass); add(lg, bulb, 0, 0.065, 0);
      var fil = new T.Mesh(new T.TorusGeometry(0.008, 0.0012, 6, 20), mat(0x664422, 0.5)); add(lg, fil, 0, 0.065, 0); K.parts.fil = fil;
      S.addApparatus('det', lg, 'Tungsten filament lamp', 'A 12 V vacuum lamp; its filament temperature is found from its resistance.');
      K.views.app = [[-0.22, 0.28, 0.2], [-0.3, 0.06, -0.3]];
      var vm = S.meter({ min: 0, max: 15, unit: 'V', symbol: 'V', caption: 'VOLTMETER', pos: [-0.05, 0, -0.32], rotY: -0.2 }); void vm;
      var unit2 = instr({ x: 0.45, z: -0.26, ry: -0.3, w: 0.34, h: 0.12, color: 0x3a4f6e, panel: '#22324a', title: 'DC SUPPLY  +  AMMETER', sub: '0 - 15 V  ·  mA', knobLabel: 'VOLTS' });
      K.main = unit2; S.addApparatus('unit', unit2.g, 'Supply and ammeter', 'Sets the lamp voltage and reads its current.');
    }
    K.views.unit = [[0.42, 0.42, 0.34], [0.4, 0.07, -0.26]];
    S.wire([[-0.3, 0.05, -0.3], [0.05, 0.02, -0.25], [0.3, 0.05, -0.24]], 'black');
  }

  function kitXray() {
    var g = G(-0.3, -0.3);
    add(g, bx(0.5, 0.02, 0.3, M.iron), 0, 0.01, 0);
    var glass = new T.Mesh(new T.BoxGeometry(0.5, 0.26, 0.3), new T.MeshPhysicalMaterial({ color: 0xf5e7c0, transparent: true, opacity: 0.18, roughness: 0.1 })); add(g, glass, 0, 0.15, 0);
    add(g, bx(0.5, 0.02, 0.3, mat(0xe8e4dc, 0.5)), 0, 0.29, 0);
    var tube = cyl(0.025, 0.025, 0.12, mat(0x2b2f36, 0.4, 0.5)); tube.rotation.z = Math.PI / 2; add(g, tube, -0.17, 0.12, 0);
    var tl = lbl('Cu ANODE', 0.04); add(g, tl, -0.17, 0.12, 0.026);
    var disc = S.mesh(new T.CylinderGeometry(0.08, 0.08, 0.01, 48), [mat(0xcfc7b4), new T.MeshStandardMaterial({ map: protractorTex(), roughness: 0.6 }), M.grey]); add(g, disc, 0.05, 0.08, 0);
    var cry = add(g, bx(0.004, 0.03, 0.025, mat(0xdfe8ef, 0.1)), 0.05, 0.1, 0);
    var arm = new T.Group(); add(g, arm, 0.05, 0.09, 0);
    add(arm, bx(0.14, 0.006, 0.02, M.alu), 0.07, 0, 0);
    var ctr = cyl(0.012, 0.012, 0.05, mat(0x9aa2ab, 0.32, 0.75)); ctr.rotation.z = Math.PI / 2; add(arm, ctr, 0.12, 0.025, 0);
    var filt = add(g, bx(0.002, 0.03, 0.03, mat(0xc9ccd0, 0.3, 0.9)), -0.08, 0.12, 0); filt.visible = false;
    K.parts.xarm = arm; K.parts.cry = cry; K.parts.filt = filt;
    S.contact(0.56, 0.36, -0.3, -0.3, 0.5);
    S.addApparatus('det', g, 'X-ray cabinet with the goniometer', 'The copper-anode tube, the LiF crystal on the goniometer table and the counter on its arm, behind lead glass with an interlock.');
    K.views.app = [[-0.2, 0.46, 0.28], [-0.26, 0.12, -0.3]];
    var unit = instr({ x: 0.5, z: -0.24, ry: -0.35, w: 0.34, h: 0.13, color: 0x30343b, panel: '#1c2027', title: 'X-RAY CONTROL  +  RATEMETER', sub: '30 kV  ·  1 mA  ·  2-THETA', knobLabel: '2 THETA' });
    K.main = unit; S.addApparatus('unit', unit.g, 'Control and ratemeter', 'Sets the goniometer angle and counts the X-rays.');
    K.views.unit = [[0.46, 0.42, 0.34], [0.44, 0.07, -0.26]];
    function setTT(tt) { arm.rotation.y = -tt * DEG; cry.rotation.y = -tt / 2 * DEG; }
    setTT(40);
    return { setTT: setTT };
  }

  function kitLadder() {
    var g = G(-0.33, -0.3);
    var pcb = S.rounded(0.46, 0.16, 0.008, 0.004, mat(0x1f6b3a, 0.6)); pcb.rotation.x = -Math.PI / 2; pcb.position.y = 0.012; g.add(pcb);
    [-1, 1].forEach(function (a) { [-1, 1].forEach(function (b) { add(g, cyl(0.004, 0.004, 0.012, M.brass, 8), a * 0.21, 0.006, b * 0.06); }); });
    for (var i = 0; i < 10; i++) {
      var xx = -0.2 + i * 0.044;
      var coil = cyl(0.009, 0.009, 0.024, mat(0x9c5a2c, 0.5, 0.4), 16); coil.rotation.z = Math.PI / 2; add(g, coil, xx, 0.026, -0.03);
      var cap = cyl(0.006, 0.006, 0.014, mat(i % 2 && p.d > 0.5 ? 0x3355aa : 0xd8b04a, 0.5), 14); add(g, cap, xx + 0.022, 0.024, 0.02);
      add(g, cyl(0.002, 0.002, 0.004, M.chrome, 6), xx + 0.022, 0.018, 0.05);
    }
    var l = lbl(p.d > 0.5 ? 'LC LATTICE  ·  DIATOMIC' : 'LC LATTICE  ·  MONATOMIC', 0.14, '#f2f2f2'); l.rotation.x = -Math.PI / 2; add(g, l, 0, 0.0165, 0.065);
    S.contact(0.5, 0.2, -0.33, -0.3, 0.5);
    S.addApparatus('det', g, 'LC lattice board', 'Twenty L-C sections in a row with test points between them; the CRO compares two neighbouring points.');
    K.views.app = [[-0.3, 0.32, 0.2], [-0.33, 0.02, -0.3]];
    var gen = instr({ x: 0.1, z: -0.44, ry: 0, w: 0.26, h: 0.11, color: 0x3a4f6e, panel: '#22324a', title: 'SIGNAL GENERATOR', sub: 'SINE  ·  10 Hz - 100 kHz', knobLabel: 'FREQ' });
    var cro = scopeBox(0.52, -0.24, 'DUAL-TRACE CRO', 'X-Y  ·  Lissajous', 'POSITION');
    K.main = cro; K.aux.push(gen);
    S.addApparatus('gen', gen.g, 'Signal generator', 'Drives the first section of the lattice.');
    S.addApparatus('unit', cro.g, 'Dual-trace CRO', 'In X-Y mode the Lissajous figure gives the phase shift per section.');
    K.views.unit = [[0.4, 0.44, 0.36], [0.32, 0.07, -0.32]];
    S.wire([[-0.55, 0.02, -0.25], [-0.2, 0.02, -0.45], [0.0, 0.04, -0.44]], 'red');
    S.wire([[-0.2, 0.02, -0.25], [0.1, 0.02, -0.15], [0.4, 0.05, -0.22]], 'black');
  }

  function kitEcho() {
    var g = G(-0.3, -0.28);
    var smp = (V_.sample || '').toLowerCase();
    var bm = /steel/.test(smp) ? mat(0x8d949b, 0.35, 0.8) : /perspex|acryl/.test(smp) ? new T.MeshPhysicalMaterial({ color: 0xdde8f0, roughness: 0.05, transmission: 0.6, thickness: 0.05, transparent: true }) : mat(0xc8ccd2, 0.3, 0.85);
    add(g, bx(0.12, 0.05, 0.08, bm), 0, 0.025, 0);
    add(g, cyl(0.012, 0.012, 0.025, mat(0x2f6fb0, 0.4, 0.4)), 0, 0.0625, 0);
    add(g, cyl(0.003, 0.003, 0.02, M.chrome, 8), 0, 0.085, 0);
    var l = lbl((V_.sample || 'Aluminium block, 50.0 mm').split(',')[0].toUpperCase(), 0.1, '#2b2f36'); add(g, l, 0, 0.025, 0.041);
    S.contact(0.18, 0.14, -0.3, -0.28, 0.5);
    S.addApparatus('det', g, V_.sample || 'Aluminium block, 50.0 mm', 'A block of measured thickness; the probe is pressed on its top face over a drop of couplant.');
    K.views.app = [[-0.22, 0.26, 0.18], [-0.3, 0.04, -0.28]];
    var pr = instr({ x: 0.1, z: -0.44, ry: 0, w: 0.26, h: 0.11, color: 0x3a4f6e, panel: '#22324a', title: 'PULSER - RECEIVER', sub: '5 MHz  ·  GAIN', knobLabel: 'GAIN' });
    var cro = scopeBox(0.52, -0.24, 'DIGITAL CRO', 'TIME CURSOR  ·  µs', 'CURSOR');
    K.main = cro; K.aux.push(pr);
    S.addApparatus('gen', pr.g, 'Pulser-receiver', 'Fires the probe and amplifies the echoes.');
    S.addApparatus('unit', cro.g, 'CRO', 'Shows the echo train; the time cursor reads each echo.');
    K.views.unit = [[0.4, 0.44, 0.36], [0.32, 0.07, -0.32]];
    S.wire([[-0.3, 0.09, -0.28], [-0.1, 0.02, -0.42], [0.0, 0.04, -0.44]], 'black');
    S.wire([[0.2, 0.05, -0.42], [0.32, 0.02, -0.3], [0.4, 0.05, -0.24]], 'black');
  }

  function kitTube() {
    var g = G(-0.4, -0.3);
    var tube = cyl(0.03, 0.03, 0.66, new T.MeshPhysicalMaterial({ color: 0xe8eef2, roughness: 0.1, transmission: 0.5, transparent: true, opacity: 0.6 }), 32); tube.rotation.z = Math.PI / 2; add(g, tube, 0, 0.06, 0);
    var spk = cyl(0.035, 0.035, 0.03, mat(0x222222, 0.6), 28); spk.rotation.z = Math.PI / 2; add(g, spk, -0.345, 0.06, 0);
    [-0.25, 0.25].forEach(function (xx) { add(g, bx(0.02, 0.03, 0.06, M.darkWood), xx, 0.015, 0); });
    var sc = S.canvasTex(2048, 64, function (x, w, h) { x.fillStyle = '#f0ead8'; x.fillRect(0, 0, w, h); x.fillStyle = '#111';
      for (var i = 0; i <= 600; i++) { var xx = i * w / 600; if (i % 5 === 0) x.fillRect(xx, 0, i % 50 ? 1.5 : 3, i % 50 ? (i % 10 ? 12 : 20) : 34); if (i % 50 === 0) { x.font = '600 24px sans-serif'; x.fillText(String(i), xx + 3, 58); } } });
    var strip = new T.Mesh(new T.PlaneGeometry(0.6, 0.016), new T.MeshStandardMaterial({ map: sc })); strip.rotation.x = -Math.PI / 2; add(g, strip, 0.0, 0.002, 0.045);
    var mic = new T.Group(); add(g, mic, 0, 0, 0);
    var rod = cyl(0.002, 0.002, 0.3, M.chrome, 8); rod.rotation.z = Math.PI / 2; add(mic, rod, 0.15, 0.06, 0);
    add(mic, cyl(0.008, 0.008, 0.02, M.black, 16), 0, 0.06, 0).rotation.z = Math.PI / 2;
    var ptr = add(mic, bx(0.003, 0.004, 0.02, M.red), 0, 0.03, 0.04); void ptr;
    K.parts.mic = mic;
    S.contact(0.72, 0.14, -0.4, -0.3, 0.5);
    S.addApparatus('det', g, 'Sound tube with speaker and microphone', 'The loudspeaker closes the left end; the microphone rides on a rod and its position is read on the scale.');
    K.views.app = [[-0.32, 0.3, 0.2], [-0.36, 0.05, -0.3]];
    var gen = instr({ x: 0.15, z: -0.46, ry: 0, w: 0.24, h: 0.11, color: 0x3a4f6e, panel: '#22324a', title: 'AUDIO GENERATOR', sub: '3000 Hz', knobLabel: 'FREQ' });
    var cro = scopeBox(0.55, -0.24, 'CRO', 'X: speaker  ·  Y: microphone', 'POSITION');
    K.main = cro; K.aux.push(gen);
    S.addApparatus('gen', gen.g, 'Audio generator', 'Drives the loudspeaker at a fixed frequency.');
    S.addApparatus('unit', cro.g, 'CRO in X-Y mode', 'Shows the Lissajous figure of the speaker signal against the microphone signal.');
    K.views.unit = [[0.44, 0.44, 0.36], [0.36, 0.07, -0.32]];
    S.wire([[-0.75, 0.06, -0.3], [-0.3, 0.02, -0.45], [0.05, 0.04, -0.46]], 'red');
    function micX(mm) { return -0.33 + mm / 1000; }
    return { micX: micX };
  }

  function kitLecher() {
    var g = G(-0.35, -0.32);
    var trough = add(g, bx(0.72, 0.025, 0.08, mat(0xe9e5d8, 0.4)), 0.02, 0.0125, 0);
    var oil = add(g, bx(0.7, 0.012, 0.07, new T.MeshPhysicalMaterial({ color: 0xd9b866, transmission: 0.5, transparent: true, opacity: 0.7, roughness: 0.1 })), 0.02, 0.03, 0); oil.visible = false;
    [-0.015, 0.015].forEach(function (zz) { var w = cyl(0.0015, 0.0015, 0.7, M.copper, 8); w.rotation.z = Math.PI / 2; add(g, w, 0.02, 0.032, zz); });
    [-0.32, 0.36].forEach(function (xx) { add(g, bx(0.012, 0.03, 0.06, M.bakelite), xx, 0.035, 0); });
    var osc = add(g, bx(0.08, 0.07, 0.08, mat(0x2b2f36, 0.5, 0.3)), -0.37, 0.035, 0);
    var ol = lbl('UHF 600 MHz', 0.06); add(osc, ol, 0, 0.01, 0.041);
    var br = new T.Group(); add(g, br, 0, 0, 0);
    add(br, bx(0.01, 0.006, 0.05, M.brass), 0, 0.036, 0); add(br, cyl(0.006, 0.006, 0.015, M.glass), 0, 0.048, 0);
    var sc = S.canvasTex(2048, 64, function (x, w, h) { x.fillStyle = '#f0ead8'; x.fillRect(0, 0, w, h); x.fillStyle = '#111';
      for (var i = 0; i <= 700; i++) { var xx = i * w / 700; if (i % 5 === 0) x.fillRect(xx, 0, i % 50 ? 1.5 : 3, i % 50 ? 14 : 34); if (i % 100 === 0) { x.font = '600 24px sans-serif'; x.fillText(String(i / 10), xx + 3, 58); } } });
    var strip = new T.Mesh(new T.PlaneGeometry(0.7, 0.014), new T.MeshStandardMaterial({ map: sc })); strip.rotation.x = -Math.PI / 2; add(g, strip, 0.02, 0.026, 0.035);
    K.parts.bridge = br; K.parts.oil = oil;
    S.contact(0.82, 0.14, -0.35, -0.32, 0.5);
    S.addApparatus('det', g, 'Lecher line', 'Two parallel copper wires on insulating posts over a trough; the oscillator couples in at the left, the shorting bridge slides along the scale (cm from the coupling loop).');
    K.views.app = [[-0.28, 0.3, 0.2], [-0.3, 0.03, -0.32]];
    var unit = instr({ x: 0.5, z: -0.24, ry: -0.35, w: 0.32, h: 0.12, title: 'DETECTOR METER', sub: 'crystal detector  ·  bridge position', knobLabel: 'SENS' });
    K.main = unit; S.addApparatus('unit', unit.g, 'Detector meter', 'The detector current dips at each node.');
    K.views.unit = [[0.46, 0.42, 0.34], [0.44, 0.07, -0.26]];
    S.wire([[-0.33, 0.04, -0.3], [0.1, 0.02, -0.12], [0.36, 0.05, -0.22]], 'black');
    function brX(cm) { return -0.33 + cm / 100; }
    return { brX: brX };
  }

  function kitScope() {
    var gen = instr({ x: -0.48, z: -0.32, ry: 0.1, w: 0.28, h: 0.12, color: 0x3a4f6e, panel: '#22324a', title: 'FUNCTION GENERATOR', sub: 'SQUARE  ·  TRIANGLE  ·  HALF-WAVE  ·  1 kHz', knobLabel: 'AMPL' });
    var an = instr({ x: -0.12, z: -0.42, ry: 0.0, w: 0.28, h: 0.12, color: 0x8b8f96, panel: '#3a3f47', title: 'TUNABLE HARMONIC ANALYSER', sub: 'n = 1 ... 9', knobLabel: 'HARMONIC' });
    var cro = scopeBox(0.42, -0.26, 'CRO', 'selected harmonic  ·  V', 'POSITION');
    K.main = cro; K.aux.push(an); K.parts.gen = gen;
    S.addApparatus('det', gen.g, 'Function generator', 'Gives the waveform under study.');
    S.addApparatus('an', an.g, 'Tunable harmonic analyser', 'A narrow band-pass filter tuned to one harmonic at a time.');
    S.addApparatus('unit', cro.g, 'CRO', 'Reads the amplitude of the selected harmonic.');
    K.views.app = [[-0.25, 0.42, 0.3], [-0.28, 0.06, -0.36]];
    K.views.unit = [[0.36, 0.44, 0.36], [0.34, 0.07, -0.28]];
    S.wire([[-0.34, 0.05, -0.28], [-0.22, 0.02, -0.3], [-0.2, 0.05, -0.4]], 'black');
    S.wire([[-0.02, 0.05, -0.4], [0.15, 0.02, -0.3], [0.3, 0.05, -0.24]], 'black');
  }

  function kitTrans() {
    var t = Math.floor(p.typ + 0.5);
    if (t === 0) { kitBath('WATER BATH'); return; }
    var g = G(-0.3, -0.3);
    if (t === 1) {
      add(g, bx(0.06, 0.12, 0.08, M.iron), -0.15, 0.06, 0);
      var beam = add(g, bx(0.3, 0.006, 0.03, mat(0xc8ccd2, 0.3, 0.85)), 0.02, 0.1, 0);
      add(g, bx(0.02, 0.0012, 0.012, mat(0xc49a3a, 0.4, 0.4)), -0.07, 0.1035, 0);
      var hg = new T.Group(); add(g, hg, 0.16, 0, 0); add(hg, cyl(0.001, 0.001, 0.04, M.chrome, 6), 0, 0.078, 0); add(hg, cyl(0.012, 0.012, 0.02, M.brass, 16), 0, 0.05, 0);
      K.parts.beam = beam; K.parts.hanger = hg;
      S.addApparatus('det', g, 'Cantilever with a strain gauge', 'A steel cantilever clamped at one end, the foil gauge near the clamp; slotted masses on the hanger set the strain.');
    } else if (t === 2) {
      add(g, bx(0.32, 0.02, 0.08, M.iron), 0, 0.01, 0);
      var lv = cyl(0.014, 0.014, 0.1, mat(0x9aa2ab, 0.3, 0.8), 24); lv.rotation.z = Math.PI / 2; add(g, lv, -0.06, 0.05, 0);
      var core = cyl(0.003, 0.003, 0.16, M.chrome, 8); core.rotation.z = Math.PI / 2; add(g, core, -0.02, 0.05, 0);
      var mic = cyl(0.012, 0.012, 0.05, M.chrome, 24); mic.rotation.z = Math.PI / 2; add(g, mic, 0.12, 0.05, 0);
      var th = cyl(0.016, 0.016, 0.03, M.black, 24); th.rotation.z = Math.PI / 2; add(g, th, 0.155, 0.05, 0);
      K.parts.core = core; K.parts.thimble = th;
      S.addApparatus('det', g, 'LVDT on a micrometer stage', 'The core of the LVDT is pushed by a micrometer screw; 0 is the centre position.');
    } else {
      var hot = S.beaker(0.045, 0.1, [-0.36, 0.04, -0.3], 0x9fd0e6, 0.6); void hot;
      add(g, cyl(0.06, 0.06, 0.04, mat(0xe6e3dc, 0.4, 0.1), 32), -0.06, 0.02, 0);
      var ice = S.beaker(0.04, 0.09, [-0.16, 0, -0.3], 0xe8f4ff, 0.7); void ice;
      S.wire([[-0.36, 0.14, -0.3], [-0.26, 0.18, -0.3], [-0.16, 0.13, -0.3]], 'red');
      S.addApparatus('det', g, 'Type K thermocouple', 'The hot junction in the heated water bath, the cold junction in melting ice.');
    }
    K.views.app = [[-0.22, 0.34, 0.22], [-0.3, 0.06, -0.3]];
    var dvm = instr({ x: 0.45, z: -0.26, ry: -0.3, w: 0.34, h: 0.12, title: t === 1 ? 'BRIDGE AMPLIFIER  +  DVM' : 'DIGITAL VOLTMETER', sub: t === 1 ? 'quarter bridge  ·  5 V' : t === 2 ? 'LVDT demodulator  ·  mV' : 'mV  ·  0.001', knobLabel: 'RANGE' });
    K.main = dvm; S.addApparatus('unit', dvm.g, 'Meter', 'Reads the transducer output.');
    K.views.unit = [[0.42, 0.42, 0.34], [0.4, 0.07, -0.26]];
    S.wire([[-0.2, 0.06, -0.3], [0.05, 0.02, -0.2], [0.3, 0.05, -0.24]], 'black');
  }

  function kitGonio(horn) {
    var g = G(-0.3, -0.3), ARM = 0.3, HY = 0.11;
    var table = S.mesh(new T.CylinderGeometry(0.18, 0.18, 0.012, 64), [mat(0xcfc7b4), new T.MeshStandardMaterial({ map: protractorTex(), roughness: 0.6 }), M.grey]);
    add(g, table, 0, 0.04, 0); add(g, cyl(0.03, 0.05, 0.034, M.iron), 0, 0.017, 0);
    function hornM(color) { var h = new T.Group();
      add(h, bx(0.07, 0.04, 0.05, mat(color, 0.35, 0.6)), -0.04, 0, 0);
      var hh = S.mesh(new T.CylinderGeometry(0.05, 0.015, 0.09, 4, 1, true), new T.MeshStandardMaterial({ color: 0xa8adb3, metalness: 0.9, roughness: 0.3, side: T.DoubleSide }));
      hh.rotation.z = -Math.PI / 2; hh.rotation.x = Math.PI / 4; add(h, hh, 0.04, 0, 0); return h; }
    var top = new T.Group(); add(g, top, 0, 0.046, 0);
    var tArm = add(g, bx(ARM, 0.012, 0.04, M.alu), -ARM / 2, 0.052, 0); void tArm;
    var tx = hornM(0x2c5fb4); add(g, tx, -ARM + 0.08, HY, 0);
    add(g, cyl(0.006, 0.006, HY - 0.06, M.chrome, 12), -ARM + 0.04, (HY + 0.06) / 2, 0);
    var rArm = new T.Group(); add(g, rArm, 0, 0.06, 0);
    add(rArm, bx(ARM, 0.012, 0.04, M.alu), ARM / 2, 0, 0);
    var rx = hornM(0x2b2f36); rx.rotation.y = Math.PI; add(rArm, rx, ARM - 0.08, HY - 0.06, 0);
    add(rArm, cyl(0.006, 0.006, HY - 0.06, M.chrome, 12), ARM - 0.04, (HY - 0.06) / 2, 0);
    if (!horn) {
      for (var i = -2; i <= 2; i++) for (var j = -2; j <= 2; j++) for (var k = 0; k < 4; k++) add(top, S.mesh(new T.SphereGeometry(0.005, 10, 8), M.chrome), i * 0.025, 0.02 + k * 0.025, j * 0.025);
      for (i = -2; i <= 2; i++) for (j = -2; j <= 2; j++) add(top, cyl(0.0008, 0.0008, 0.08, mat(0xeeeeee, 0.5), 4), i * 0.025, 0.055, j * 0.025);
      var bl = lbl('BALL LATTICE 4.0 cm', 0.08, '#2b2f36'); bl.rotation.x = -Math.PI / 2; add(g, bl, 0, 0.047, 0.15);
    } else {
      var th = hornM(0x2c5fb4); add(top, th, 0, 0.06, 0);
      tx.visible = false;
      add(g, bx(0.02, 0.03, 0.02, M.iron), 0, 0.06, 0);
    }
    K.parts.top = top; K.parts.rArm = rArm; K.parts.rx = rx;
    S.contact(0.7, 0.42, -0.3, -0.3, 0.45);
    S.addApparatus('det', g, horn ? 'Horn on a turntable' : 'Microwave goniometer with the ball lattice', horn ? 'The transmitting horn turns on the graduated turntable; the receiving horn stands 1 m away on the fixed arm.' : 'The Gunn transmitter on the fixed arm, the ball lattice on the turntable, the receiving horn with its crystal detector on the swinging arm.');
    K.views.app = [[-0.3, 0.6, 0.26], [-0.3, 0.08, -0.3]];
    var unit = instr({ x: 0.5, z: -0.24, ry: -0.35, w: 0.32, h: 0.12, title: 'GUNN SUPPLY  +  DETECTOR', sub: '10.5 GHz  ·  square-law  ·  %', knobLabel: 'SENS' });
    K.main = unit; S.addApparatus('unit', unit.g, 'Gunn supply and detector meter', 'Powers the oscillator and reads the crystal detector as a percentage of the straight-through signal.');
    K.views.unit = [[0.46, 0.42, 0.34], [0.44, 0.07, -0.26]];
    S.wire([[-0.56, 0.1, -0.3], [0.0, 0.02, -0.08], [0.38, 0.05, -0.22]], 'black');
    function setTh(th) { if (horn) { top.rotation.y = -th * DEG; rArm.rotation.y = 0; } else { top.rotation.y = -th * DEG; rArm.rotation.y = -2 * th * DEG; } }
    if (horn) rArm.rotation.y = 0; else setTh(10);
    return { setTh: setTh };
  }

  function kitCoupled() {
    var m = p.m > 0.5;
    if (!m) {
      var g = G(-0.33, -0.3), H = 0.5;
      [-0.2, 0.2].forEach(function (xx) { var b0 = S.rounded(0.1, 0.08, 0.012, 0.004, M.iron); b0.rotation.x = -Math.PI / 2; add(g, b0, xx, 0.006, 0); add(g, cyl(0.006, 0.006, H, M.chrome, 16), xx, H / 2, 0); });
      var bar = cyl(0.008, 0.008, 0.44, M.iron, 16); bar.rotation.z = Math.PI / 2; add(g, bar, 0, H, 0);
      var pends = [-0.07, 0.07].map(function (xx) { var pg = new T.Group(); add(g, pg, xx, H, 0);
        add(pg, cyl(0.0006, 0.0006, 0.4, mat(0xeeeeee, 0.6), 4), 0, -0.2, 0); add(pg, S.mesh(new T.SphereGeometry(0.018, 24, 16), M.brass), 0, -0.4, 0); return pg; });
      var spring = new T.Mesh(new T.CylinderGeometry(0.004, 0.004, 0.14, 8, 1, true), new T.MeshStandardMaterial({ color: 0x9aa0a6, wireframe: true })); spring.rotation.z = Math.PI / 2; add(g, spring, 0, H - 0.3, 0);
      K.parts.pends = pends; K.parts.spring = spring;
      S.contact(0.5, 0.14, -0.33, -0.3, 0.45);
      S.addApparatus('det', g, 'Two coupled pendulums', 'Two equal pendulums, 60 cm long, hang from one rigid bar; a light spring joins their strings below the bar.');
      K.views.app = [[-0.25, 0.5, 0.35], [-0.33, 0.25, -0.3]];
      var sw = S.stopwatch([0.08, 0, -0.1], 0); K.parts.sw = sw;
      var unit = instr({ x: 0.45, z: -0.26, ry: -0.3, w: 0.3, h: 0.11, title: 'TIMER', sub: 'oscillations  ·  s', knobLabel: 'RESET' });
      K.main = unit; S.addApparatus('unit', unit.g, 'Timer', 'Shows the timed interval.');
    } else {
      var b = G(-0.33, -0.3);
      var pcb = S.rounded(0.4, 0.16, 0.008, 0.004, mat(0x1f6b3a, 0.6)); pcb.rotation.x = -Math.PI / 2; pcb.position.y = 0.012; b.add(pcb);
      [-0.09, 0.09].forEach(function (xx) { var c = cyl(0.025, 0.025, 0.03, mat(0x9c5a2c, 0.5, 0.4), 24); add(b, c, xx, 0.031, -0.02); add(b, cyl(0.008, 0.008, 0.025, mat(0x3355aa, 0.5), 16), xx, 0.028, 0.045); });
      var lb = lbl('COUPLED LC CIRCUITS  ·  M', 0.12, '#f2f2f2'); lb.rotation.x = -Math.PI / 2; add(b, lb, 0, 0.0165, 0.065);
      S.addApparatus('det', b, 'Two coupled LC circuits', 'Two equal coils and capacitors; the coils face each other so that their mutual inductance couples the circuits.');
      K.views.app = [[-0.28, 0.3, 0.2], [-0.33, 0.02, -0.3]];
      var cro = scopeBox(0.45, -0.25, 'STORAGE CRO', 'time cursors  ·  ms', 'MODE');
      K.main = cro; S.addApparatus('unit', cro.g, 'Storage CRO', 'Records the voltage on one capacitor; the cursors time the oscillations.');
    }
    K.views.unit = [[0.42, 0.42, 0.34], [0.4, 0.07, -0.26]];
  }

  // ======================================================================== the plan of each kernel
  var Y_NAME = 'Count rate', Y_UNIT = 'counts/s';
  function cntCols(xl, xf) { return [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: xl, get: xf },
    { label: 'Counts', get: function (r) { return r.N; } }, { label: 't (s)', get: function (r) { return r.T; } },
    { label: 'Rate (/s)', get: function (r) { return f(r.y, 3); } }]; }
  function xcol(xl, d) { return { label: xl, get: function (r) { return f(r.x, d); } }; }
  function ycol(yl, d, key) { return { label: yl, get: function (r) { return f(r[key || 'y'], d); } }; }
  var PLAN = null, kitApi = {};
  var TBMAP = { pm9_gmdt: 'pm9_tau', pm9_gmeff: 'pm9_eint', pm9_betaf: 'pm9_range', pm9_k40: 'pm9_tbeta', pm9_spark: 'pm9_geiger', pm9_prop: 'pm9_presol', pm9_kurie: 'pm9_endpoint', pm9_angcorr: 'pm9_a2', pm9_hallt: 'pm9_eg0', pm9_twop: 'pm9_twop', pm9_diode: 'pm9_eg0', pm9_photoc: 'pm9_egphoto', pm9_acsusc: 'pm9_tc', pm9_lclat: 'pm9_lccut', pm9_echo: 'pm9_v', pm9_sound: 'pm9_vsound', pm9_lecher: 'pm9_eps', pm9_fourier: 'pm9_fratio', pm9_trans: 'pm9_sens', pm9_stefan: 'pm9_sigma', pm9_cuxray: 'pm9_kalpha', pm9_mwbragg: 'pm9_d', pm9_horn: 'pm9_hpbw', pm9_coupled: 'pm9_kappa', pm9_gasphoto: 'pm9_isq' };
  var TBNAME = (S.lab.check && S.lab.check.textbook) || TBMAP[KNAME] || '';
  function truthVal() { var tb = HK.TEXTBOOK[TBNAME]; return tb ? tb(p) : null; }

  if (KNAME === 'pm9_gmdt') {
    kitGM();
    var sA = source(0xb8322a), sB = source(0x3d6fb2); S.scene.add(sA); S.scene.add(sB);
    var POT = new T.Vector3(-0.06, 0.032, -0.14), POTB = new T.Vector3(-0.04, 0.032, -0.14);
    sA.position.copy(POT); sB.position.copy(POTB);
    S.addApparatus('src', sA, 'Sealed Cs-137 and Sr-90 sources', 'Two sealed disc sources; for the two-source method each has its own fixed place on the shelf.');
    var arr = ['no source (background)', 'Cs-137 (source 1)', 'Cs-137 and Sr-90', 'Sr-90 (source 2)'];
    PLAN = { stages: [
      { title: 'Plateau', h2: 'Find the counting plateau', text: 'With the Cs-137 source in place 1 on the shelf, raise the E.H.T. in 20 V steps and count 30 s at each.', label: 'E.H.T.', unit: 'V', min: 250, max: 800, step: 10, digits: 0, count: true, minRows: 10,
        prep: { label: 'Put Cs-137 in place 1', fn: function () { return place(sA, shelfPt(-0.025)); } } },
      { title: 'Two sources', h2: 'Two-source method at the operating voltage', text: 'Set the E.H.T. to ' + p.V + ' V. Count ' + p.t + ' s with: no source, Cs-137 alone, both sources, Sr-90 alone. Each source always in its own place.', label: 'Sources on the shelf (0 none, 1 Cs-137, 2 both, 3 Sr-90)', unit: '', min: 0, max: 3, step: 1, digits: 0, count: true, minRows: 4,
        show: function (v) { return arr[Math.round(v)]; }, prep: { label: 'Set ' + p.V + ' V', fn: function () { return turn(K.main, 250, 800, p.V); } } }],
      ctl: function (v, s) {
        if (s === 0) return turn(K.main, 250, 800, v);
        var i = Math.round(v);
        var a = (i === 1 || i === 2), b = (i === 2 || i === 3);
        return place(sA, a ? shelfPt(-0.025) : POT).then(function () { return place(sB, b ? shelfPt(0.025) : POTB); });
      },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Setting', get: function (r) { return r.s === 0 ? f(r.x, 0) + ' V' : arr[Math.round(r.x)]; } },
        { label: 'Counts', get: function (r) { return r.N; } }, { label: 't (s)', get: function (r) { return r.T; } }, { label: 'Rate (/s)', get: function (r) { return f(r.y, 2); } }],
      res: { label: 'Dead time of the GM tube', unit: 'µs', k: 1e6, digits: 0 },
      note: function (rows) { var pl = rows.filter(function (r) { return r.s === 0; }); var top = 0; pl.forEach(function (r) { top = Math.max(top, r.y); });
        var v0 = null; pl.forEach(function (r) { if (v0 === null && r.y > 0.9 * top) v0 = r.x; });
        var pp = pl.filter(function (r) { return v0 !== null && r.x >= v0 + 20 && r.x <= 680; }).map(function (r) { return [r.x, r.y]; }), fs = pp.length > 2 ? S.fit.linear(pp) : null;
        var mean = pp.length ? pp.reduce(function (a, q) { return a + q[1]; }, 0) / pp.length : 1;
        return (v0 !== null ? 'The plateau starts near ' + v0 + ' V; the operating voltage ' + p.V + ' V lies about a third of the way along it. ' : '') + (fs ? 'Plateau slope ' + f(fs.m * 100 / mean * 100, 1) + ' % per 100 V. ' : '') + 'Dead time from n1 + n2 = n12 + nb with n = m/(1 - m tau). SIMULATED DATA.'; },
      graph: { x: function (r) { return r.s === 0 ? r.x : NaN; }, y: function (r) { return r.s === 0 ? r.y : NaN; }, xlabel: 'E.H.T. (V)', ylabel: 'count rate (/s)' },
      tol: 0.03, screen: 'count' };
    var place = function (obj, to) {
      if (obj.position.distanceTo(to) < 1e-4) return Promise.resolve();
      var from = obj.position.clone();
      return S.hand.pinchMove(from, function (k) { return new T.Vector3(from.x + (to.x - from.x) * k, Math.max(from.y, to.y) + 0.05 * Math.sin(Math.PI * k), from.z + (to.z - from.z) * k); },
        function (k) { obj.position.set(from.x + (to.x - from.x) * k, Math.max(from.y, to.y) + 0.05 * Math.sin(Math.PI * k), from.z + (to.z - from.z) * k); }, { mode: 'side', ms: 800, reachMs: 500 })
        .then(function () { obj.position.copy(to); });
    };
  } else if (KNAME === 'pm9_gmeff') {
    kitGM(); K.parts.shelf.visible = false;
    var gsrc = source(/gamma|Cs/i.test(V_.sample || '') ? 0x2e8b57 : 0xb8322a); S.scene.add(gsrc);
    var GPOT = new T.Vector3(-0.05, 0.032, -0.14); gsrc.position.copy(GPOT);
    var rod = cyl(0.002, 0.002, 0.1, M.chrome, 8); rod.position.set(-0.3, 0.11, -0.22); S.scene.add(rod);
    S.addApparatus('src', gsrc, V_.sample || 'Sr-90/Y-90 beta source, 3.7 kBq certificate', 'A calibrated sealed source; its carriage slides on a graduated rod below the window.');
    var winY = 0.168 - 0.0415;
    var spot = function (d) { return new T.Vector3(-0.3, winY - d, -0.25); };
    PLAN = { stages: [
      { title: 'Background', h2: 'Background', text: 'With the source locked in its store, count for ' + p.t + ' s.', label: 'Background count', unit: '', min: 0, max: 0, step: 1, digits: 0, count: true, minRows: 1, fixed: true },
      { title: 'Distances', h2: 'Count at known distances', text: 'Put the source on its carriage at 2, 3, 4, 5 and 6 cm below the window and count ' + p.t + ' s at each.', label: 'Distance below the window', unit: 'cm', min: 1, max: 8, step: 0.5, digits: 1, xk: 0.01, count: true, minRows: 4 }],
      ctl: function (v, s) {
        var to = s === 0 ? GPOT : spot(v), from = gsrc.position.clone();
        if (from.distanceTo(to) < 1e-4) return Promise.resolve();
        return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k).add(new T.Vector3(0, 0.03 * Math.sin(Math.PI * k), 0)); }, function (k) { gsrc.position.copy(from.clone().lerp(to, k)); }, { mode: 'side', ms: 700, reachMs: 500 })
          .then(function () { gsrc.position.copy(to); }); },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'd (cm)', get: function (r) { return r.s === 0 ? 'store' : f(r.x * 100, 1); } },
        { label: 'Counts', get: function (r) { return r.N; } }, { label: 'Rate (/s)', get: function (r) { return f(r.y, 3); } },
        { label: 'G', get: function (r) { return r.s === 0 ? '-' : f(KN.geo(p, r.x), 4); } }],
      res: { label: 'Intrinsic efficiency of the tube', unit: '%', k: 100, digits: 2 },
      note: function () { return 'Window radius ' + (p.a * 100).toFixed(1) + ' cm; source ' + (p.A / 1000).toFixed(1) + ' kBq, ' + p.yld + ' particles per decay. The geometry factor G = (1 - d/sqrt(d^2 + a^2))/2 was taken off each reading. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.s === 1 ? KN.geo(p, r.x) : NaN; }, y: function (r) { return r.s === 1 ? r.y : NaN; }, xlabel: 'geometry factor G', ylabel: 'count rate (/s)' },
      tol: 0.04, screen: 'count' };
  } else if (KNAME === 'pm9_betaf') {
    kitGM();
    var bsrc = source(0xb8322a); S.scene.add(bsrc); var BPOT = new T.Vector3(-0.05, 0.032, -0.14); bsrc.position.copy(BPOT);
    var foil = new T.Mesh(new T.BoxGeometry(0.09, 1, 0.055), mat(0xc3c8cf, 0.35, 0.7)); foil.position.set(-0.3, 0.11, -0.25); foil.visible = false; S.scene.add(foil);
    S.addApparatus('src', bsrc, V_.sample || 'Sealed Sr-90/Y-90 beta source', 'Moved only with tongs; it sits on the shelf below the foils.');
    var R_ = function () { return KN.rkp(p.E1); };
    PLAN = { stages: [
      { title: 'Background', h2: 'Background', text: 'With the source in its store, count for ' + p.tl + ' s.', label: 'Background count', min: 0, max: 0, step: 1, digits: 0, count: true, minRows: 1, fixed: true },
      { title: 'Foils', h2: 'Count through the foils', text: 'Put the source on its shelf. Count through each foil of the box (0 to 2000 mg/cm²; the thickest shows only the tail). Near the end, stack 5 mg/cm² foils to halve the gap between the last foil with betas and the first without.', label: 'Aluminium on the shelf', unit: 'mg/cm²', min: 0, max: 2000, step: 5, digits: 0, xk: 0.001, count: true, minRows: 16,
        prep: { label: 'Put the source on the shelf', fn: function () { var from = bsrc.position.clone(), to = new T.Vector3(-0.3, 0.084, -0.25);
          return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); }, function (k) { bsrc.position.copy(from.clone().lerp(to, k)); }, { mode: 'side', ms: 800 }).then(function () { bsrc.position.copy(to); }); } } }],
      ctl: function (v, s) { if (s === 0) return Promise.resolve();
        var pt = new T.Vector3(-0.3, 0.12, -0.2);
        return S.hand.pinchMove(pt, function () { return pt; }, function () {}, { mode: 'side', ms: 400, reachMs: 500 }).then(function () {
          foil.visible = v > 0; foil.scale.y = Math.max(0.0008, v / 270); foil.position.y = 0.088 + foil.scale.y / 2; }); },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'x (mg/cm²)', get: function (r) { return r.s === 0 ? 'bg' : f(r.x * 1000, 0); } },
        { label: 'Counts', get: function (r) { return r.N; } }, { label: 't (s)', get: function (r) { return r.T; } }, { label: 'Rate (/s)', get: function (r) { return f(r.y, 3); } }],
      res: { label: 'Range of the betas in aluminium', unit: 'mg/cm²', k: 1000, digits: 0 },
      note: function (rows) { var v = KN.fit(rows, p), tl = rows.filter(function (r) { return r.s === 1 && Math.abs(r.x - 2.0) < 1e-9; })[0];
        var ep = tl ? rows.filter(function (r) { return r.s === 1 && r.x > 0 && r.x <= 0.15 * v + 1e-9 && r.y - tl.y > 0; }).map(function (r) { return [r.x, Math.log(r.y - tl.y)]; }) : [], fm = ep.length > 1 ? S.fit.linear(ep) : null;
        return 'Feather\'s rule: E = (R + 0.160)/0.543 = ' + f(KN.feather(v), 3) + ' MeV. ' + (fm ? 'Early slope: mu_m = ' + f(-fm.m, 1) + ' cm²/g. ' : '') + 'SIMULATED DATA.'; },
      graph: { x: function (r) { return r.s === 1 ? r.x * 1000 : NaN; }, y: function (r) { return r.s === 1 && r.y > 0 ? Math.log(r.y) : NaN; }, xlabel: 'x (mg/cm²)', ylabel: 'ln(rate)' },
      tol: 0.03, screen: 'count' };
    void R_;
  } else if (KNAME === 'pm9_k40') {
    kitGM();
    var tray = new T.Group(); S.scene.add(tray); tray.position.set(-0.3, 0.084, -0.25);
    tray.add(cyl(0.03, 0.03, 0.008, M.alu, 32)); var fill = cyl(0.029, 0.029, 0.005, mat(0xf4f2ec, 0.95), 32); fill.position.y = 0.002; tray.add(fill); fill.visible = false;
    S.addApparatus('tray', tray, 'Counting tray', 'The same tray is counted empty, with the UX2 standard and with the potassium salt, in the same place.');
    var fills = [null, 0xe8d24a, 0xf4f2ec];
    PLAN = { stages: [
      { title: 'Empty tray', h2: 'Background: the empty tray', text: 'Count the empty tray twice for ' + p.t + ' s.', label: 'Count number', min: 1, max: 5, step: 1, digits: 0, count: true, minRows: 2 },
      { title: 'UX2 standard', h2: 'The UX2 standard', text: 'Fill the tray with the UX2 standard (certified ' + p.Bstd + ' betas per second) and count three times.', label: 'Count number', min: 1, max: 5, step: 1, digits: 0, count: true, minRows: 3,
        prep: { label: 'Load the standard', fn: function () { return loadTray(1); } } },
      { title: 'Potassium salt', h2: 'Potassium chloride', text: 'Fill the tray with ' + (p.m * 1000).toFixed(0) + ' g of KCl, levelled to the same depth, and count three times.', label: 'Count number', min: 1, max: 5, step: 1, digits: 0, count: true, minRows: 3,
        prep: { label: 'Load the KCl', fn: function () { return loadTray(2); } } }],
      ctl: function () { return Promise.resolve(); },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Tray', get: function (r) { return ['empty', 'UX2 standard', 'KCl'][r.s]; } },
        { label: 'Counts', get: function (r) { return r.N; } }, { label: 'Rate (/s)', get: function (r) { return f(r.y, 3); } }],
      res: { label: 'Partial beta half-life of K-40', unit: '× 10⁹ y', k: 1e-9, digits: 3 },
      note: function (rows) { var m = function (s) { var v = rows.filter(function (r) { return r.s === s; }); return v.length ? v.reduce(function (a, r) { return a + r.y; }, 0) / v.length : NaN; };
        var eps = (m(1) - m(0)) / p.Bstd; var A = (m(2) - m(0)) / eps; var mk = p.m * 1000 * p.fK;
        return 'Efficiency from the standard ' + f(eps * 100, 3) + ' %; the salt emits ' + f(A, 0) + ' betas/s from ' + f(mk, 1) + ' g of potassium (' + f(A / mk, 1) + ' per g). SIMULATED DATA.'; },
      graph: { x: function (r, i) { return i + 1; }, y: function (r) { return r.y; }, xlabel: 'count', ylabel: 'rate (/s)' },
      tol: 0.06, screen: 'count' };
    var loadTray = function (s) {
      var pt = new T.Vector3(-0.3, 0.12, -0.2);
      return S.hand.pinchMove(pt, function () { return pt; }, function () {}, { mode: 'top', ms: 600 }).then(function () { fill.visible = true; fill.material = mat(fills[s], 0.9); });
    };
  } else if (KNAME === 'pm9_spark') {
    kitApi = kitSpark();
    PLAN = { stages: [
      { title: 'Plateau', h2: 'Counting plateau', text: 'With the source 1.0 cm from the wire, raise the E.H.T. from 3.0 to 5.1 kV in 100 V steps and count ' + p.t + ' s at each.', label: 'E.H.T.', unit: 'kV', min: 2.5, max: 6, step: 0.1, digits: 1, xk: 1000, count: true, minRows: 10,
        knob: function () { return K.aux[0]; } },
      { title: 'Range', h2: 'Counts against distance', text: 'At ' + (p.V / 1000).toFixed(1) + ' kV, move the source away from the wire: 1 to 3.5 cm in 0.5 cm steps, then 0.1 cm steps to 4.6 cm.', label: 'Source to wire distance', unit: 'cm', min: 0.5, max: 6, step: 0.1, digits: 1, count: true, minRows: 12,
        prep: { label: 'Set ' + (p.V / 1000).toFixed(1) + ' kV', fn: function () { return turn(K.aux[0], 0, 6000, p.V); } } }],
      ctl: function (v, s) {
        if (s === 0) return turn(K.aux[0], 0, 6000, v);
        var car = K.parts.car, to = kitApi.carX(v), from = car.position.x, pt = function () { return wp(car).add(new T.Vector3(0, 0.035, 0)); };
        return S.hand.pinchMove(pt(), function () { return pt(); }, function (k) { car.position.x = from + (to - from) * k; }, { mode: 'top', ms: 500 + 300 * Math.abs(to - from) / 0.05 }).then(function () { car.position.x = to; }); },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Setting', get: function (r) { return r.s === 0 ? f(r.x / 1000, 1) + ' kV' : f(r.x, 1) + ' cm'; } },
        { label: 'Counts', get: function (r) { return r.N; } }, { label: 'Rate (/s)', get: function (r) { return f(r.y, 3); } },
        { label: '(rate-bg) d²', get: function (r) { return r.s === 1 ? f((r.y - p.bg) * r.x * r.x, 2) : '-'; } }],
      res: { label: 'Mean range of the alphas in air', unit: 'cm', k: 1, digits: 2 },
      note: function (rows) { var R = KN.fit(rows, p); return 'Geiger\'s rule R = 0.318 E^1.5 turns this into E = ' + f(Math.pow(R / 0.318, 2 / 3), 2) + ' MeV. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.s === 1 ? r.x : NaN; }, y: function (r) { return r.s === 1 ? (r.y - p.bg) * r.x * r.x : NaN; }, xlabel: 'd (cm)', ylabel: '(rate - bg) d²' },
      tol: 0.02, screen: 'count' };
  } else if (KNAME === 'pm9_prop') {
    kitMCA('prop');
    var c0 = KN.chan(p, p.E, p.Vop);
    PLAN = { stages: [
      { title: 'Gas gain', h2: 'Peak channel against voltage', text: 'Raise the counter voltage from ' + (p.Vop - 150) + ' to ' + (p.Vop + 150) + ' V in 25 V steps and read the peak channel of the line.', label: 'Counter voltage', unit: 'V', min: 1200, max: 2100, step: 5, digits: 0, minRows: 8,
        knob: function () { return K.aux[0]; } },
      { title: 'Line shape', h2: 'The line, channel by channel', text: 'Set ' + p.Vop + ' V, collect the spectrum, and read the counts with the cursor every 2 channels across the line.', label: 'Cursor channel', unit: '', min: 2, max: 1022, step: 2, digits: 0, minRows: 10,
        prep: { label: 'Set ' + p.Vop + ' V and collect', fn: function () { return turn(K.aux[0], 1200, 2100, p.Vop); } } }],
      ctl: function (v, s) { return s === 0 ? turn(K.aux[0], 1200, 2100, v) : turn(K.main, 0, 1024, v); },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Setting', get: function (r) { return r.s === 0 ? f(r.x, 0) + ' V' : 'ch ' + f(r.x, 0); } },
        { label: 'Reading', get: function (r) { return r.s === 0 ? 'peak ' + f(r.y, 1) : f(r.y, 0) + ' counts'; } }],
      res: { label: 'Energy resolution (FWHM / E)', unit: '%', k: 1, digits: 1 },
      note: function (rows) { var g = rows.filter(function (r) { return r.s === 0 && r.y > 0; }).map(function (r) { return [r.x, Math.log(r.y)]; }); var fl = g.length > 1 ? S.fit.linear(g) : null;
        return (fl ? 'Gas gain: ln(peak) rises ' + f(fl.m * 1000, 2) + ' per kV, the gain doubles every ' + f(Math.LN2 / fl.m, 0) + ' V. ' : '') + 'Line centred near channel ' + f(c0, 0) + '. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.s === 1 ? r.x : NaN; }, y: function (r) { return r.s === 1 ? r.y : NaN; }, xlabel: 'channel', ylabel: 'counts' },
      tol: 0.04, screen: 'mca' };
  } else if (KNAME === 'pm9_kurie') {
    var MAG = p.m > 0.5;
    if (MAG) kitMagspec(); else kitMCA('scint');
    var xsK = KN.xs(p, 0);
    PLAN = { stages: [
      { title: 'Spectrum', h2: MAG ? 'Count against the magnet current' : 'Counts channel by channel', text: MAG ? 'Step the coil current from ' + f(xsK[0], 2) + ' A to ' + f(xsK[xsK.length - 1], 2) + ' A in 0.05 A steps and count at each (p = ' + p.kI + ' m c per ampere, from the conversion-line calibration).' : 'Read the counts in channels of ' + p.dT + ' keV from ' + p.dT + ' keV to past the end of the spectrum.', label: MAG ? 'Coil current' : 'Channel energy', unit: MAG ? 'A' : 'keV', min: MAG ? 0.05 : p.dT, max: xsK[xsK.length - 1], step: MAG ? 0.05 : p.dT, digits: MAG ? 2 : 0, count: true, minRows: 20 }],
      ctl: function (v) { return MAG ? turn(K.aux[0], 0, xsK[xsK.length - 1], v) : turn(K.main, 0, xsK[xsK.length - 1], v); },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: MAG ? 'I (A)' : 'T (keV)', get: function (r) { return f(r.x, MAG ? 2 : 0); } },
        { label: 'T (keV)', get: function (r) { return f(KN.kin(p, r.x), 0); } }, { label: 'Counts', get: function (r) { return f(r.y, 0); } }],
      res: { label: 'End-point energy', unit: 'keV', k: 1, digits: 0 },
      note: function (rows) { var e0 = KN.fit(rows, p), lp = null, lm = 0; rows.forEach(function (r) { var T = KN.kin(p, r.x); if (T > 1.05 * e0 && r.y > lm) { lm = r.y; lp = T; } });
        return (lp !== null && lm > 50 ? 'The sharp peak beyond the continuum, at about ' + f(lp, 0) + ' keV, is the K conversion line. ' : '') + 'Kurie fit over 35 to 85 % of the end of the continuum; allowed shape assumed. SIMULATED DATA.'; },
      graph: { x: function (r) { return 1 + KN.kin(p, r.x) / 510.99895; }, y: function (r) { var q = KN.kuriePts([r], p); return q.length ? q[0][1] : NaN; }, xlabel: 'W (m c² units)', ylabel: 'Kurie function K' },
      tol: 0.02, screen: 'mca' };
  } else if (KNAME === 'pm9_angcorr') {
    kitApi = kitCoinc();
    PLAN = { stages: [
      { title: 'Chance rate', h2: 'Chance coincidences', text: 'Put the long delay cable in one arm and count at 90 degrees for ' + p.t + ' s: only chance coincidences are left.', label: 'Angle', unit: 'deg', min: 90, max: 90, step: 1, digits: 0, count: true, minRows: 1, fixed: true },
      { title: 'Angles', h2: 'Prompt coincidences against angle', text: 'Take the delay out. Swing the movable detector from 90 to 180 degrees in 15 degree steps and count ' + p.t + ' s at each.', label: 'Angle between the detectors', unit: 'deg', min: 90, max: 180, step: 5, digits: 0, count: true, minRows: 5 }],
      ctl: function (v) { var arm = K.parts.arm, a0 = (Math.PI - arm.rotation.y) / DEG, pt = function () { return wp(K.parts.mvdet).add(new T.Vector3(0, 0.07, 0)); };
        if (Math.abs(a0 - v) < 1e-6) return Promise.resolve();
        return S.hand.pinchMove(pt(), function () { return pt(); }, function (k) { kitApi.setAng(a0 + (v - a0) * k); }, { mode: 'top', ms: 400 + 8 * Math.abs(v - a0) }).then(function () { kitApi.setAng(v); }); },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'theta (deg)', get: function (r) { return r.s === 0 ? 'delay' : f(r.x, 0); } },
        { label: 'Counts', get: function (r) { return r.N; } }, { label: 'Rate (/s)', get: function (r) { return f(r.y, 3); } }],
      res: { label: 'Correlation coefficient a2', unit: '', k: 1, digits: 3 },
      note: function (rows) { var c0 = rows.filter(function (r) { return r.s === 0; })[0], pr = rows.filter(function (r) { return r.s === 1; }), w9 = pr.filter(function (r) { return r.x === 90; })[0];
        var a4 = NaN; if (c0 && w9) { var s11 = 0, s12 = 0, s22 = 0, s1y = 0, s2y = 0; pr.forEach(function (r) { var c = Math.cos(r.x * DEG), u = c * c, v = u * u, y = (r.y - c0.y) / (w9.y - c0.y) - 1; s11 += u * u; s12 += u * v; s22 += v * v; s1y += u * y; s2y += v * y; });
          a4 = (s11 * s2y - s12 * s1y) / (s11 * s22 - s12 * s12); }
        var a2 = KN.fit(rows, p), A2 = (2 * a2 / 3 + 4 * a4 / 7) / (1 + a2 / 3 + a4 / 5), A4 = (8 * a4 / 35) / (1 + a2 / 3 + a4 / 5);
        return 'Fitted a4 = ' + f(a4, 3) + '. In Legendre form A2 = ' + f(A2, 3) + ', A4 = ' + f(A4, 4) + '. Theory for the 4(2)2(2)0 cascade: a2 = 1/8, a4 = 1/24. The a4 term needs far longer counts to pin down. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.s === 1 ? Math.pow(Math.cos(r.x * DEG), 2) : NaN; }, y: function (r) { return r.s === 1 ? r.y : NaN; }, xlabel: 'cos² theta', ylabel: 'coincidence rate (/s)' },
      tol: 0.05, screen: 'count' };
  } else if (KNAME === 'pm9_hallt') {
    kitHall();
    PLAN = { stages: [
      { title: 'Temperature scan', h2: 'Hall and sample voltages from 77 K to 420 K', text: 'Fill the cryostat (77 K) and warm in steps. At each temperature read the Hall voltage and the voltage along the slab (I = ' + p.I * 1000 + ' mA, B = ' + p.B + ' T).', label: 'Set temperature', unit: 'K', min: 77, max: 420, step: 1, digits: 0, minRows: 10, knob: function () { return K.aux[0]; } }],
      ctl: function (v) { return turn(K.aux[0], 77, 450, v); },
      cols: [{ label: 'T (K)', get: function (r) { return f(r.x, 0); } }, ycol('V_H (mV)', 3), ycol('V_s (mV)', 2, 'y2'),
        { label: 'mu_H (m²/Vs)', get: function (r) { var rh = Math.abs(r.y) / 1000 * p.d / (p.I * p.B), sg = p.I * p.L / (r.y2 / 1000 * p.w * p.d); return f(rh * sg, 3); } }],
      res: { label: 'Band gap of germanium (intrinsic region)', unit: 'eV', k: 1, digits: 3 },
      note: function (rows) { var s = rows.filter(function (r) { return r.y < 0; }).length && rows.filter(function (r) { return r.y > 0; }).length;
        return (s ? 'The Hall voltage changed sign: the electrons took over. ' : '') + 'Slope of ln(|R_H| T^1.5) against 1/T above 375 K = Eg0/2k. The mobility column shows mu_H falling as T^-1.5. SIMULATED DATA.'; },
      graph: { x: function (r) { return 1000 / r.x; }, y: function (r) { var rh = Math.abs(r.y) / 1000 * p.d / (p.I * p.B); return rh > 0 ? Math.log(rh * Math.pow(r.x, 1.5)) : NaN; }, xlabel: '1000/T (1/K)', ylabel: 'ln(|R_H| T^1.5)' },
      tol: 0.02, screen: 'dvm2' };
  } else if (KNAME === 'pm9_twop') {
    kitFurnace();
    var GRA = p.mat > 0.5;
    PLAN = { stages: [
      { title: 'Temperature scan', h2: 'Voltage across the probes against temperature', text: 'Pass ' + (p.I * 1000) + ' mA through the ' + (GRA ? 'graphite rod' : 'germanium bar') + ' and read the voltage from 300 to 420 K in 10 K steps.', label: 'Furnace set point', unit: 'K', min: 290, max: 430, step: 1, digits: 0, minRows: 8, knob: function () { return K.aux[0]; } }],
      ctl: function (v) { return turn(K.aux[0], 290, 450, v); },
      cols: [{ label: 'T (K)', get: function (r) { return f(r.x, 0); } }, ycol('V (mV)', 3),
        { label: 'sigma (S/m)', get: function (r) { return f(p.L / (r.y / 1000 / p.I * p.A), GRA ? 0 : 3); } }],
      res: GRA ? { label: 'Conductivity of graphite at 300 K', unit: 'S/m', k: 1, digits: 0 } : { label: 'Band gap of germanium', unit: 'eV', k: 1, digits: 3 },
      note: function () { return GRA ? 'Graphite is a semimetal: its conductivity barely changes with temperature. Contacts of ' + (p.Rc * 1000) + ' milliohm each are included in this two-probe reading. SIMULATED DATA.' : 'Slope of ln(sigma) against 1/T = -Eg0/2k. The contact resistances add a small error at high temperature. SIMULATED DATA.'; },
      graph: { x: function (r) { return 1000 / r.x; }, y: function (r) { return Math.log(p.L / (r.y / 1000 / p.I * p.A)); }, xlabel: '1000/T (1/K)', ylabel: 'ln(sigma)' },
      tol: 0.02, screen: 'dvm' };
  } else if (KNAME === 'pm9_diode') {
    kitBath('OIL BATH');
    PLAN = { stages: [
      { title: 'Temperatures', h2: 'Diode voltage at two currents', text: 'At each bath temperature from 300 to 380 K, set ' + (p.I1 * 1000) + ' mA and then ' + (p.I2 * 1000) + ' mA and read the diode voltage.', label: 'Bath temperature', unit: 'K', min: 290, max: 400, step: 1, digits: 0, minRows: 6,
        knob: function () { return null; } }],
      ctl: function (v) { var hk = K.parts.hpk, pt = wp(hk), a0 = hk.rotation.y;
        return S.hand.pinchMove(pt, function () { return pt; }, function (k) { hk.rotation.y = a0 + k * 0.6; K.parts.th.set(Math.max(0, v - 273.15)); }, { mode: 'front', ms: 500 }).then(function () { K.parts.th.set(v - 273.15); }); },
      cols: [{ label: 'T (K)', get: function (r) { return f(r.x, 0); } }, ycol('V1 (mV)', 1), ycol('V2 (mV)', 1, 'y2'), { label: 'n', get: function (r) { return f(KN.ideal(p, r), 3); } }],
      res: { label: 'Band gap Eg0 of the junction', unit: 'eV', k: 1, digits: 3 },
      note: function (rows) { var n = rows.map(function (r) { return KN.ideal(p, r); }); var mn = n.length ? n.reduce(function (a, b) { return a + b; }, 0) / n.length : NaN;
        var r3 = rows.filter(function (r) { return r.x === 300; })[0], i3 = r3 ? p.I1 / (Math.exp(r3.y / 1000 / (KN.ideal(p, r3) * 8.617333262e-5 * 300)) - 1) : NaN;
        return 'Mean ideality factor ' + f(mn, 2) + '; saturation current at 300 K ' + (isFinite(i3) ? i3.toExponential(2) : '-') + ' A. ln(I0/T³) against 1/T has slope -Eg0/k. SIMULATED DATA.'; },
      graph: { x: function (r) { return 1000 / r.x; }, y: function (r) { var n = KN.ideal(p, r), T = r.x; var i0 = p.I1 / (Math.exp(r.y / 1000 / (n * 8.617333262e-5 * T)) - 1); return Math.log(i0 / (T * T * T)); }, xlabel: '1000/T (1/K)', ylabel: 'ln(I0 / T³)' },
      tol: 0.02, screen: 'dvm2' };
  } else if (KNAME === 'pm9_photoc') {
    kitApi = kitOptical();
    K.parts.lamp.position.x = kitApi.lampX(20);
    PLAN = { stages: [
      { title: 'Intensity', h2: 'Photocurrent against the lamp distance', text: 'Move the lamp from 10 to 50 cm from the cell and read the photocurrent.', label: 'Lamp to cell', unit: 'cm', min: 8, max: 55, step: 1, digits: 0, minRows: 5 },
      { title: 'Spectral response', h2: 'Response against wavelength', text: 'Put the monochromator in front of the cell. Turn the drum from ' + p.l1 + ' to ' + p.l2 + ' nm in 5 nm steps and read the current.', label: 'Wavelength', unit: 'nm', min: 350, max: 900, step: 5, digits: 0, minRows: 20,
        prep: { label: 'Put the monochromator in', fn: function () { var pt = new T.Vector3(-0.24, 0.16, -0.3); return S.hand.pinchMove(pt, function () { return pt; }, function () {}, { mode: 'top', ms: 600 }).then(function () { K.parts.mono.visible = true; }); } } },
      { title: 'Rise', h2: 'Rise when the light comes on', text: 'With the shutter closed and the current back at its dark value, open the shutter and read the stored current at 25 ms intervals.', label: 'Time after the shutter opened', unit: 'ms', min: 0, max: 300, step: 5, digits: 0, xk: 0.001, minRows: 5,
        prep: { label: 'Open the shutter', fn: function () { return S.hand.tap(K.parts.shutter, 'tap').then(function () { K.parts.shutter.position.y = 0.13; }); } } },
      { title: 'Decay', h2: 'Decay after the light is cut off', text: 'Close the shutter and read the stored current at 25 ms intervals.', label: 'Time after the shutter closed', unit: 'ms', min: 0, max: 300, step: 5, digits: 0, xk: 0.001, minRows: 5,
        prep: { label: 'Close the shutter', fn: function () { return S.hand.tap(K.parts.shutter, 'tap').then(function () { K.parts.shutter.position.y = 0.09; }); } } }],
      ctl: function (v, s) {
        if (s === 0) { var L = K.parts.lamp, to = kitApi.lampX(v), from = L.position.x, pt = function () { return wp(L).add(new T.Vector3(0, 0.14, 0)); };
          return S.hand.pinchMove(pt(), function () { return pt(); }, function (k) { L.position.x = from + (to - from) * k; }, { mode: 'top', ms: 600 }).then(function () { L.position.x = to; }); }
        if (s === 1) return turn(null, 0, 1, 0, K.parts.drum, v / 100);
        return turn(K.main, 0, 300, v * 1000); },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Setting', get: function (r) { return r.s === 0 ? f(r.x, 0) + ' cm' : r.s === 1 ? f(r.x, 0) + ' nm' : (r.s === 2 ? 'rise ' : 'decay ') + f(r.x * 1000, 0) + ' ms'; } }, ycol('I (µA)', 2)],
      res: { label: 'Band gap from the cut-off', unit: 'eV', k: 1, digits: 3 },
      note: function (rows) { var a = rows.filter(function (r) { return r.s === 0; }).map(function (r) { return [Math.log(1 / (r.x * r.x)), Math.log(r.y - p.Id)]; });
        var d = rows.filter(function (r) { return r.s === 3 && r.y - p.Id > 0.05; }).map(function (r) { return [r.x, Math.log(r.y - p.Id)]; });
        var ri = rows.filter(function (r) { return r.s === 2; }), top = 0; ri.forEach(function (r) { top = Math.max(top, r.y); });
        var rr = ri.filter(function (r) { return top - r.y > 0.05 && r.x < 0.2; }).map(function (r) { return [r.x, Math.log(top + 0.02 - r.y)]; }), fr = rr.length > 1 ? S.fit.linear(rr) : null;
        var fa = a.length > 1 ? S.fit.linear(a) : null, fd = d.length > 1 ? S.fit.linear(d) : null;
        return (fa ? 'I ~ (illumination)^' + f(fa.m, 2) + '. ' : '') + (fr ? 'Rise time about ' + f(-1000 / fr.m, 0) + ' ms. ' : '') + (fd ? 'Decay time ' + f(-1000 / fd.m, 0) + ' ms. ' : '') + 'Cut-off where the response falls to half its plateau. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.s === 1 ? r.x : NaN; }, y: function (r) { return r.s === 1 ? r.y : NaN; }, xlabel: 'wavelength (nm)', ylabel: 'photocurrent (µA)' },
      tol: 0.02, screen: 'dvm' };
  } else if (KNAME === 'pm9_acsusc') {
    kitCryo('LN2 CRYOSTAT  ·  YBCO');
    PLAN = { stages: [
      { title: 'Warm through Tc', h2: 'In-phase and loss signals against temperature', text: 'Starting at 80 K, warm in steps (0.5 K near the transition) and read the lock-in X (in-phase) and Y (out-of-phase) outputs.', label: 'Set temperature', unit: 'K', min: 77, max: 110, step: 0.5, digits: 1, minRows: 12, knob: function () { return K.aux[0]; } }],
      ctl: function (v) { return turn(K.aux[0], 77, 110, v); },
      cols: [{ label: 'T (K)', get: function (r) { return f(r.x, 1); } }, ycol("V' (µV)", 2), ycol("V'' (µV)", 2, 'y2')],
      res: { label: 'Critical temperature Tc', unit: 'K', k: 1, digits: 1 },
      note: function (rows) { var pts = rows.map(function (r) { return [r.x, r.y]; }).sort(function (a, b) { return a[0] - b[0]; }); var on = null;
        if (pts.length) { var lo = pts[0][1], hi = pts[pts.length - 1][1]; for (var i = 1; i < pts.length; i++) if (on === null && pts[i][1] > hi - 0.1 * (hi - lo)) on = pts[i][0]; }
        return (on !== null ? 'Diamagnetic onset (90 % back to normal) near ' + f(on, 1) + ' K. ' : '') + "The loss peak V'' sits at Tc. SIMULATED DATA."; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.y; }, xlabel: 'T (K)', ylabel: "in-phase V' (µV)" },
      tol: 0.01, screen: 'dvm2' };
  } else if (KNAME === 'pm9_stefan') {
    var LAMP = p.m > 0.5;
    kitStefan(LAMP);
    PLAN = LAMP ? { stages: [
      { title: 'Lamp', h2: 'Lamp voltage and current', text: 'Raise the lamp voltage from 2 to 12 V in 1 V steps and read the current at each, after it settles.', label: 'Lamp voltage', unit: 'V', min: 1, max: 14, step: 0.5, digits: 1, minRows: 6 }],
      ctl: function (v) { return turn(K.main, 0, 15, v); },
      cols: [{ label: 'V (V)', get: function (r) { return f(r.x, 1); } }, ycol('I (mA)', 1), { label: 'T (K)', get: function (r) { return f(p.T0 * Math.pow((r.x / (r.y / 1000)) / p.R0, 1 / 1.2), 0); } }],
      res: { label: "Stefan's constant", unit: '× 10⁻⁸ W m⁻² K⁻⁴', k: 1e8, digits: 3 },
      note: function () { return 'Filament area ' + (p.Af * 1e6).toFixed(0) + ' mm², tungsten emissivity taken as ' + p.ew + '. Slope of V I against e_W A_f T^4 through the origin. SIMULATED DATA.'; },
      graph: { x: function (r) { var T = p.T0 * Math.pow((r.x / (r.y / 1000)) / p.R0, 1 / 1.2); return p.ew * p.Af * Math.pow(T, 4) / 1e-8 * 1e-8 * 1e8; }, y: function (r) { return r.x * r.y / 1000; }, xlabel: 'e A T^4 (x 1e-8)', ylabel: 'P = V I (W)' },
      tol: 0.02, screen: 'dvm' } : { stages: [
      { title: 'Cooling curve', h2: 'Temperature as the body cools', text: 'Heat the body to about ' + (p.Ti - 273.15).toFixed(0) + ' °C, pump the enclosure, switch the heater off and read the temperature every ' + p.dt + ' s.', label: 'Time on the stopwatch', unit: 's', min: 0, max: 1000, step: p.dt, digits: 0, minRows: 10 }],
      ctl: function (v) { var sw = K.parts.sw; sw.t = v; return Promise.resolve(); },
      cols: [{ label: 't (s)', get: function (r) { return f(r.x, 0); } }, ycol('T (°C)', 1)],
      res: { label: "Stefan's constant", unit: '× 10⁻⁸ W m⁻² K⁻⁴', k: 1e8, digits: 3 },
      note: function () { return 'Body ' + (p.mb * 1000) + ' g of copper (c = ' + p.cb + ' J/kg K), area ' + (p.Ab * 1e4).toFixed(1) + ' cm², emissivity ' + p.eb + ', enclosure at ' + p.T0 + ' K. Rates from central differences. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.y; }, xlabel: 't (s)', ylabel: 'T (°C)' },
      tol: 0.02, screen: 'dvm' };
  } else if (KNAME === 'pm9_cuxray') {
    kitApi = kitXray();
    PLAN = { stages: [
      { title: 'Spectrum', h2: 'Scan without a filter', text: 'At 30 kV, scan the counter from 2 theta = 36 to 50 degrees in 0.1 degree steps, ' + p.t + ' s per step.', label: 'Counter angle 2 theta', unit: 'deg', min: 30, max: 60, step: 0.1, digits: 1, count: true, minRows: 60 },
      { title: 'Nickel filter', h2: 'Scan with the nickel foil', text: 'Slide the nickel foil into the beam and scan again.', label: 'Counter angle 2 theta', unit: 'deg', min: 30, max: 60, step: 0.1, digits: 1, count: true, minRows: 60,
        prep: { label: 'Slide the nickel foil in', fn: function () { var pt = wp(K.parts.filt).add(new T.Vector3(0, 0.12, 0)); return S.hand.pinchMove(pt, function () { return pt; }, function () {}, { mode: 'top', ms: 600 }).then(function () { K.parts.filt.visible = true; }); } } }],
      ctl: function (v) { var a0 = -K.parts.xarm.rotation.y / DEG; return turn(K.main, 30, 60, v, null, null, function (k) { kitApi.setTT(a0 + (v - a0) * k); }); },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Filter', get: function (r) { return r.s ? 'Ni' : 'none'; } }, xcol('2 theta (deg)', 1), ycol('Rate (/s)', 1)],
      res: { label: 'K-alpha wavelength of copper', unit: 'Å', k: 1, digits: 4 },
      note: function (rows) { function pk(s, lo, hi) { var m = 0; rows.forEach(function (r) { if (r.s === s && r.x >= lo && r.x <= hi) m = Math.max(m, r.y); }); return m; }
        var ta = KN.ang(p, (2 * p.la1 + p.la2) / 3), tb = KN.ang(p, p.lb);
        var r0 = pk(0, tb - 0.4, tb + 0.4) / Math.max(pk(0, ta - 0.4, ta + 0.4), 1e-9), r1 = pk(1, tb - 0.4, tb + 0.4) / Math.max(pk(1, ta - 0.4, ta + 0.4), 1e-9);
        var s0 = rows.filter(function (r) { return r.s === 0; }), ka = null, km = 0, kb = null, kbm = 0;
        s0.forEach(function (r) { if (r.y > km) { km = r.y; ka = r.x; } }); s0.forEach(function (r) { if (ka !== null && r.x < ka - 1.5 && r.y > kbm) { kbm = r.y; kb = r.x; } });
        return (kb !== null ? 'K-beta peak at 2 theta = ' + f(kb, 1) + ' deg, lambda = ' + f(KN.lam(p, kb), 3) + ' Å. ' : '') + 'K-beta / K-alpha: ' + f(r0, 3) + ' without the filter, ' + f(r1, 4) + ' with nickel. LiF (200) 2d = ' + f(2 * p.dc, 3) + ' Å. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.y; }, xlabel: '2 theta (deg)', ylabel: 'rate (/s)' },
      tol: 0.005, screen: 'mca' };
  } else if (KNAME === 'pm9_lclat') {
    kitLadder();
    var xsL = KN.xs(p, 0);
    PLAN = { stages: [
      { title: 'Phase against frequency', h2: 'Phase shift per section', text: 'Step the generator from ' + xsL[0] + ' Hz upwards and read the phase shift per section from the Lissajous figure, until it reaches 180 degrees' + (p.d > 0.5 ? '; then go on through the gap (no transmission, 180 degrees) into the optical branch.' : '.'), label: 'Generator frequency', unit: 'Hz', min: 50, max: 30000, step: 50, digits: 0, minRows: 8, knob: function () { return K.aux[0]; } }],
      ctl: function (v) { return turn(K.aux[0], 0, 30000, v); },
      cols: [{ label: 'f (Hz)', get: function (r) { return f(r.x, 0); } }, ycol('phi (deg)', 1), { label: 'sin(phi/2)', get: function (r) { return f(Math.sin(r.y / 2 * DEG), 4); } }],
      res: p.d > 0.5 ? { label: 'Top of the acoustic branch', unit: 'Hz', k: 1, digits: 0 } : { label: 'Cut-off frequency', unit: 'Hz', k: 1, digits: 0 },
      note: function (rows) { var ps = rows.slice().sort(function (a, b) { return a.x - b.x; }), g0 = null, g1 = null, i;
        for (i = 0; i < ps.length; i++) { if (g0 === null && ps[i].y >= 179.9) g0 = ps[i].x; else if (g0 !== null && g1 === null && ps[i].y < 179.9) g1 = ps[i].x; }
        return p.d > 0.5 ? (g1 !== null ? 'No wave travels from about ' + f(g0, 0) + ' Hz until the optical branch appears near ' + f(g1, 0) + ' Hz: that is the band gap (theory: optical branch from ' + f(Math.sqrt(2 / (p.L * p.C2)) / (2 * Math.PI), 0) + ' Hz). ' : '') + 'Fit of sin²(phi/2)/w² against w² over the acoustic branch. SIMULATED DATA.' : 'f = fc sin(phi/2): the slope through the origin. SIMULATED DATA.'; },
      graph: { x: function (r) { return Math.sin(r.y / 2 * DEG); }, y: function (r) { return r.x; }, xlabel: 'sin(phi/2)', ylabel: 'f (Hz)' },
      tol: 0.02, screen: 'cro' };
  } else if (KNAME === 'pm9_echo') {
    kitEcho();
    PLAN = { stages: [
      { title: 'Echoes', h2: 'Read the echo times', text: 'Move the CRO time cursor onto the leading edge of each back-wall echo, 1 to 6.', label: 'Echo number', unit: '', min: 1, max: 8, step: 1, digits: 0, minRows: 5 }],
      ctl: function (v) { return turn(K.main, 0, 8, v); },
      cols: [{ label: 'n', get: function (r) { return f(r.x, 0); } }, ycol('t (µs)', 2), ycol('height (%)', 1, 'y2')],
      res: { label: 'Longitudinal velocity of sound', unit: 'm/s', k: 1, digits: 0 },
      note: function (rows) { var v = KN.fit(rows, p); return 'Block ' + (p.d * 1000).toFixed(1) + ' mm thick, density ' + p.rho + ' kg/m³: longitudinal modulus M = rho v² = ' + f(p.rho * v * v / 1e9, 1) + ' GPa. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.y; }, xlabel: 'echo number n', ylabel: 't (µs)' },
      tol: 0.01, screen: 'cro' };
  } else if (KNAME === 'pm9_sound') {
    kitApi = kitTube();
    PLAN = { stages: [
      { title: 'Straight lines', h2: 'Find each straight-line figure', text: 'Slide the microphone away from the speaker; stop at each position where the ellipse closes to a straight line and read the scale.', label: 'Straight-line figure number', unit: '', min: 0, max: 9, step: 1, digits: 0, minRows: 6 }],
      ctl: function (v) { var mic = K.parts.mic, r = KN.read(p, 0, v, 0), to = kitApi.micX(r.y), from = mic.position.x, pt = function () { return wp(mic).add(new T.Vector3(0, 0.08, 0)); };
        return S.hand.pinchMove(pt(), function () { return pt(); }, function (k) { mic.position.x = from + (to - from) * k; }, { mode: 'top', ms: 600 }).then(function () { mic.position.x = to; }); },
      cols: [{ label: 'Line', get: function (r) { return f(r.x, 0); } }, ycol('Position (mm)', 1)],
      res: { label: 'Velocity of sound in air', unit: 'm/s', k: 1, digits: 1 },
      note: function () { return 'v = 2 f x slope, f = ' + p.f + ' Hz. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.y; }, xlabel: 'line number', ylabel: 'position (mm)' },
      tol: 0.01, screen: 'cro' };
  } else if (KNAME === 'pm9_lecher') {
    kitApi = kitLecher();
    PLAN = { stages: [
      { title: 'In air', h2: 'Nodes in air', text: 'Slide the bridge from the coupling end and note the position of every node (the detector dips).', label: 'Node number', unit: '', min: 0, max: 12, step: 1, digits: 0, minRows: 4 },
      { title: 'In the liquid', h2: 'Nodes with the wires in transformer oil', text: 'Fill the trough with transformer oil and find the nodes again.', label: 'Node number', unit: '', min: 0, max: 12, step: 1, digits: 0, minRows: 4,
        prep: { label: 'Fill the trough', fn: function () { var pt = new T.Vector3(-0.3, 0.14, -0.3); return S.hand.pinchMove(pt, function () { return pt; }, function () {}, { mode: 'top', ms: 700 }).then(function () { K.parts.oil.visible = true; }); } } }],
      ctl: function (v, s) { var b = K.parts.bridge, r = KN.read(p, s, v, 0), to = kitApi.brX(r.y), from = b.position.x, pt = function () { return wp(b).add(new T.Vector3(0, 0.05, 0)); };
        return S.hand.pinchMove(pt(), function () { return pt(); }, function (k) { b.position.x = from + (to - from) * k; }, { mode: 'top', ms: 600 }).then(function () { b.position.x = to; }); },
      cols: [{ label: 'Medium', get: function (r) { return r.s ? 'oil' : 'air'; } }, { label: 'Node', get: function (r) { return f(r.x, 0); } }, ycol('Position (cm)', 1)],
      res: { label: 'Dielectric constant of the oil', unit: '', k: 1, digits: 3 },
      note: function (rows) { var l0 = KN.lamOf(rows, 0); return 'In air lambda0 = ' + f(l0, 1) + ' cm, so f = c / lambda0 = ' + f(299792458 / (l0 / 100) / 1e6, 1) + ' MHz. eps = (lambda0 / lambda)². SIMULATED DATA.'; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.y; }, xlabel: 'node number', ylabel: 'position (cm)' },
      tol: 0.02, screen: 'dvm' };
  } else if (KNAME === 'pm9_fourier') {
    kitScope();
    var shp = ['square', 'triangular', 'half-wave rectified'][Math.floor(p.shape + 0.5)];
    PLAN = { stages: [
      { title: 'Harmonics', h2: 'Amplitude of each harmonic', text: 'With the ' + shp + ' wave on, tune the analyser to harmonics 1 to 7 and read each amplitude on the CRO.', label: 'Harmonic number', unit: '', min: 1, max: 9, step: 1, digits: 0, minRows: 5, knob: function () { return K.aux[0]; } }],
      ctl: function (v) { return turn(K.aux[0], 0, 9, v); },
      cols: [{ label: 'n', get: function (r) { return f(r.x, 0); } }, ycol('amplitude (V)', 3), { label: 'ratio to n = 1', get: function (r) { var r1 = S.rows.filter(function (q) { return Math.round(q.x) === 1; })[0]; return r1 ? f(r.y / r1.y, 4) : '-'; } }],
      res: { label: (FS2 = (Math.floor(p.shape + 0.5) === 2 ? 'Second' : 'Third')) + ' harmonic / fundamental', unit: '', k: 1, digits: 4 },
      note: function () { return 'The ' + shp + ' wave: ' + ['odd harmonics 4A/(n pi), the third one third of the fundamental', 'odd harmonics 8A/(n pi)², the third one ninth', 'A/pi, A/2 and even harmonics 2A/(pi(n² - 1)): the second is 4/(3 pi) of the fundamental'][Math.floor(p.shape + 0.5)] + '. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.y; }, xlabel: 'harmonic n', ylabel: 'amplitude (V)' },
      tol: 0.01, screen: 'cro' };
  } else if (KNAME === 'pm9_trans') {
    kitTrans();
    var TY = Math.floor(p.typ + 0.5);
    var TD = [{ label: 'Bath temperature', unit: '°C', min: 20, max: 90, step: 1, d: 0, y: 'R (ohm)', yd: 0, res: { label: 'B constant of the thermistor', unit: 'K', k: 1, digits: 0 } },
      { label: 'Strain', unit: 'µstrain', min: 0, max: 1000, step: 50, d: 0, y: 'V (mV)', yd: 3, res: { label: 'Gauge factor', unit: '', k: 1, digits: 3 } },
      { label: 'Core displacement', unit: 'mm', min: -5, max: 5, step: 0.5, d: 1, y: 'V (mV)', yd: 1, res: { label: 'LVDT sensitivity (central ±2 mm)', unit: 'mV/mm', k: 1, digits: 2 } },
      { label: 'Hot junction temperature', unit: '°C', min: 0, max: 100, step: 5, d: 0, y: 'E (mV)', yd: 3, res: { label: 'Mean sensitivity, 0 - 100 °C', unit: 'µV/K', k: 1, digits: 2 } }][TY];
    PLAN = { stages: [
      { title: 'Characteristic', h2: 'Output against the stimulus', text: 'Step the stimulus over its range and read the output at each step.', label: TD.label, unit: TD.unit, min: TD.min, max: TD.max, step: TD.step, digits: TD.d, minRows: 6 }],
      ctl: function (v) {
        if (TY === 1) { var hg = K.parts.hanger, pt = wp(hg).add(new T.Vector3(0, 0.03, 0)); return S.hand.pinchMove(pt, function () { return pt; }, function () {}, { mode: 'top', ms: 500 }).then(function () { hg.scale.y = 1 + v / 500; K.parts.beam.rotation.z = -v * 1e-5; }); }
        if (TY === 2) { var th2 = K.parts.thimble, core = K.parts.core, a0 = th2.rotation.x, pt2 = wp(th2); return S.hand.pinchMove(pt2, function () { return pt2; }, function (k) { th2.rotation.x = a0 + k * 2; core.position.x = -0.02 + v / 1000 * k; }, { mode: 'front', ms: 500 }).then(function () { core.position.x = -0.02 + v / 1000; }); }
        if (TY === 0) { var hk = K.parts.hpk, ptq = wp(hk), b0 = hk.rotation.y; return S.hand.pinchMove(ptq, function () { return ptq; }, function (k) { hk.rotation.y = b0 + 0.6 * k; }, { mode: 'front', ms: 500 }).then(function () { K.parts.th.set(v); }); }
        return turn(K.main, 0, 100, v); },
      cols: [xcol(TD.label + ' (' + TD.unit + ')', TD.d), ycol(TD.y, TD.yd)],
      res: TD.res,
      note: function (rows) { var pts = rows.map(function (r) { return [r.x, TY === 0 ? Math.log(r.y) : r.y]; }); var fl = pts.length > 1 ? S.fit.linear(TY === 0 ? rows.map(function (r) { return [1 / (r.x + 273.15), Math.log(r.y)]; }) : pts) : null, dev = 0, span = 1;
        if (fl && TY !== 0) { var ys = rows.map(function (r) { return r.y; }); span = Math.max.apply(null, ys) - Math.min.apply(null, ys) || 1; rows.forEach(function (r) { dev = Math.max(dev, Math.abs(r.y - (fl.m * r.x + fl.c))); }); }
        return (TY !== 0 && fl ? 'Largest departure from the straight line ' + f(100 * dev / span, 2) + ' % of full scale. ' : 'Far from linear: ln R against 1/T is the straight line. ') + 'SIMULATED DATA.'; },
      graph: TY === 0 ? { x: function (r) { return 1000 / (r.x + 273.15); }, y: function (r) { return Math.log(r.y); }, xlabel: '1000/T (1/K)', ylabel: 'ln R' } : { x: function (r) { return r.x; }, y: function (r) { return r.y; }, xlabel: TD.label, ylabel: TD.y },
      tol: 0.01, screen: 'dvm' };
  } else if (KNAME === 'pm9_mwbragg' || KNAME === 'pm9_horn') {
    var HORN = KNAME === 'pm9_horn';
    kitApi = kitGonio(HORN);
    PLAN = { stages: [
      { title: HORN ? 'Pattern' : 'Bragg scan', h2: HORN ? 'Received power against the horn angle' : 'Turn the crystal, receiver at 2 theta', text: HORN ? 'Turn the transmitting horn from -40 to +40 degrees in 1 degree steps (' + (p.pl > 0.5 ? 'H-plane' : 'E-plane') + ') and read the detector.' : 'Turn the crystal from 10 to 60 degrees in 0.5 degree steps, the receiver arm always at twice the angle, and read the detector.',
        label: HORN ? 'Horn angle' : 'Crystal angle theta', unit: 'deg', min: HORN ? -60 : 5, max: HORN ? 60 : 70, step: 0.5, digits: 1, minRows: HORN ? 30 : 40 }].concat(HORN ? [
      { title: 'Gain', h2: 'Gain by the two-horn method', text: 'Face the horns at each other and move the receiving horn to 0.6, 0.8, 1.0 and 1.2 m; read the received power as a fraction (x 1000) of the transmitted power.', label: 'Separation of the horns', unit: 'm', min: 0.5, max: 1.5, step: 0.05, digits: 2, minRows: 3,
        prep: { label: 'Turn the horn back to 0 degrees', fn: function () { kitApi.setTh(0); return Promise.resolve(); } } }] : []),
      ctl: function (v, s) {
        if (HORN && s === 1) { var rx = K.parts.rx, from = rx.position.x, to = 0.22 + (v - 1.0) * 0.1, ptr = function () { return wp(rx).add(new T.Vector3(0, 0.05, 0)); };
          return S.hand.pinchMove(ptr(), function () { return ptr(); }, function (k) { rx.position.x = from + (to - from) * k; }, { mode: 'top', ms: 600 }).then(function () { rx.position.x = to; }); }
        var top = K.parts.top, a0 = -top.rotation.y / DEG, pt = function () { return wp(top).add(new T.Vector3(0, 0.12, 0)); };
        if (Math.abs(v - a0) < 1e-9) return Promise.resolve();
        return S.hand.pinchMove(pt(), function () { return pt(); }, function (k) { kitApi.setTh(a0 + (v - a0) * k); }, { mode: 'top', ms: 300 + 6 * Math.abs(v - a0) }).then(function () { kitApi.setTh(v); }); },
      cols: [{ label: HORN ? 'Setting' : 'theta (deg)', get: function (r) { return r.s === 1 ? f(r.x, 2) + ' m' : f(r.x, 1) + (HORN ? ' deg' : ''); } }, { label: 'Reading', get: function (r) { return r.s === 1 ? f(r.y, 3) + ' per mille' : f(r.y, 1) + ' %'; } }],
      res: HORN ? { label: 'Half-power beam width (' + (p.pl > 0.5 ? 'H' : 'E') + '-plane)', unit: 'deg', k: 1, digits: 1 } : { label: 'Plane spacing of the ball lattice', unit: 'cm', k: 100, digits: 2 },
      note: function (rows) { var gs = rows.filter(function (r) { return r.s === 1 && r.y > 0; }).map(function (r) { return 4 * Math.PI * r.x / p.lam * Math.sqrt(r.y / 1000); });
        var gm = gs.length ? gs.reduce(function (a, b) { return a + b; }, 0) / gs.length : NaN;
        return HORN ? (gs.length ? 'Gain from the two-horn (Friis) readings G = (4 pi R / lambda) sqrt(Pr/Pt) = ' + f(gm, 1) + ' (' + f(10 * Math.log(gm) / Math.LN10, 1) + ' dB); the aperture formula (8/pi²) 4 pi a b / lambda² gives ' + f(KN.gain(p), 1) + '. ' : '') + 'Aperture ' + (p.a * 100).toFixed(1) + ' x ' + (p.b * 100).toFixed(1) + ' cm, lambda ' + (p.lam * 100).toFixed(3) + ' cm. SIMULATED DATA.' : 'd = n lambda / (2 sin theta) from the first two orders, lambda = ' + (p.lam * 100).toFixed(3) + ' cm. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.s === 0 ? r.x : NaN; }, y: function (r) { return r.s === 0 ? r.y : NaN; }, xlabel: HORN ? 'angle (deg)' : 'theta (deg)', ylabel: 'detector (%)' },
      tol: 0.02, screen: 'dvm' };
  } else if (KNAME === 'pm9_coupled') {
    kitCoupled();
    var MODES = ['both in phase', 'in opposite phase', 'one alone (beats)'], CU = p.m > 0.5 ? 'ms' : 's';
    st.mode = -1; st.tt = 0;
    PLAN = { stages: [
      { title: 'Normal modes', h2: 'Time the two modes and the beats', text: p.m > 0.5 ? 'Drive the circuits in each way in turn and read on the storage CRO the time of ' + p.nper + ' oscillations (both in phase, in opposite phase) and of one beat (one circuit alone).' : 'Start the pendulums each way in turn: time ' + p.nper + ' oscillations in phase and in opposite phase, and one beat when only one is started.', label: 'Way of starting', unit: '', min: 0, max: 2, step: 1, digits: 0, minRows: 3,
        show: function (v) { return MODES[Math.round(v)] || ''; } }],
      ctl: function (v) {
        if (p.m > 0.5) return turn(K.main, 0, 2, v).then(function () { st.mode = Math.round(v); st.tt = 0; });
        var pg = K.parts.pends[Math.round(v) === 1 ? 1 : 0], pt = wp(pg).add(new T.Vector3(0, -0.4, 0.03));
        return S.hand.pinchMove(pt, function (k) { return pt.clone().add(new T.Vector3(0.03 * k, 0, 0)); }, function () {}, { mode: 'side', ms: 500 }).then(function () { st.mode = Math.round(v); st.tt = 0; }); },
      cols: [{ label: 'Start', get: function (r) { return MODES[Math.round(r.x)]; } }, ycol('Time (' + CU + ')', p.m > 0.5 ? 3 : 2),
        { label: 'Period (' + CU + ')', get: function (r) { return Math.round(r.x) < 2 ? f(r.y / p.nper, 4) : '-'; } }],
      res: { label: 'Coupling constant kappa', unit: '', k: 1, digits: 4 },
      note: function (rows) { var t = [null, null, null]; rows.forEach(function (r) { t[Math.round(r.x)] = r.y; });
        if (t[0] === null || t[1] === null) return '';
        var T1 = t[0] / p.nper, T2 = t[1] / p.nper, pb = 1 / (1 / T2 - 1 / T1);
        return 'Normal-mode frequencies ' + f(1 / T1 * (CU === 'ms' ? 1000 : 1), 3) + ' and ' + f(1 / T2 * (CU === 'ms' ? 1000 : 1), 3) + ' Hz. The two modes predict a beat period of ' + f(pb, 3) + ' ' + CU + (t[2] !== null ? '; measured ' + f(t[2], 3) + ' ' + CU : '') + '. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return Math.round(r.x) < 2 ? r.y / p.nper : NaN; }, xlabel: 'mode (0 in phase, 1 opposite)', ylabel: 'period (' + CU + ')' },
      tol: 0.01, screen: 'dvm' };
  } else if (KNAME === 'pm9_gasphoto') {
    kitApi = kitOptical();
    K.parts.lamp.position.x = kitApi.lampX(20);
    PLAN = { stages: [
      { title: 'Voltage', h2: 'Current against the anode voltage', text: 'With the lamp at 20 cm, raise the anode voltage from 0 to 90 V in 5 V steps and read the current.', label: 'Anode voltage', unit: 'V', min: 0, max: 100, step: 1, digits: 0, minRows: 10 },
      { title: 'Lamp distance', h2: 'Current against the lamp distance', text: 'Set ' + p.Vop + ' V. Read the dark current with the lamp off (distance 0 in the table), then move the lamp from 15 to 50 cm.', label: 'Lamp to cell (0 = lamp off)', unit: 'cm', min: 0, max: 55, step: 1, digits: 0, minRows: 5,
        prep: { label: 'Set ' + p.Vop + ' V', fn: function () { return turn(K.main, 0, 100, p.Vop); } } }],
      ctl: function (v, s) {
        if (s === 0) return turn(K.main, 0, 100, v);
        if (v <= 0) return S.hand.tap(K.parts.lamp.children[0], 'tap').then(function () { K.parts.lens.material = M.black; });
        K.parts.lens.material = M.glass;
        var L = K.parts.lamp, to = kitApi.lampX(v), from = L.position.x, pt = function () { return wp(L).add(new T.Vector3(0, 0.14, 0)); };
        return S.hand.pinchMove(pt(), function () { return pt(); }, function (k) { L.position.x = from + (to - from) * k; }, { mode: 'top', ms: 600 }).then(function () { L.position.x = to; }); },
      cols: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'Setting', get: function (r) { return r.s === 0 ? f(r.x, 0) + ' V' : r.x <= 0 ? 'lamp off' : f(r.x, 0) + ' cm'; } }, ycol('I (µA)', 3)],
      res: { label: 'Exponent n of I ~ d^n', unit: '', k: 1, digits: 3 },
      note: function (rows) { var v = rows.filter(function (r) { return r.s === 0; }), sat = null, top = null;
        v.forEach(function (r) { if (Math.abs(r.x - 25) < 1e-9) sat = r.y; if (Math.abs(r.x - 90) < 1e-9) top = r.y; });
        return (sat && top ? 'Saturation near ' + f(sat, 3) + ' µA by 25 V; at 90 V the gas multiplies it ' + f(top / sat, 1) + ' times. ' : '') + 'The slope near -2 shows the current follows the light flux. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.s === 0 ? r.x : NaN; }, y: function (r) { return r.s === 0 ? r.y : NaN; }, xlabel: 'anode voltage (V)', ylabel: 'current (µA)' },
      tol: 0.01, screen: 'dvm' };
  }
  var FS2;

  // ======================================================================== the human actions
  function knobAngle(min, max, v) { return 3 * Math.PI / 4 - 1.5 * Math.PI * Math.max(0, Math.min(1, (v - min) / ((max - min) || 1))); }
  function turn(box, min, max, v, mesh, frac, onK) {
    var kn = mesh || (box ? box.knob : null);
    if (!kn) return Promise.resolve();
    var a0 = kn.rotation.z, a1 = frac !== undefined && frac !== null ? a0 - frac : knobAngle(min, max, v), pt = wp(kn).add(new T.Vector3(0, 0, 0.01));
    if (Math.abs(a1 - a0) < 1e-6 && !onK) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { kn.rotation.z = a0 + (a1 - a0) * k; if (onK) onK(k); }, { mode: 'front', ms: 450, reachMs: 500 })
      .then(function () { kn.rotation.z = a1; if (onK) onK(1); });
  }
  var STG = PLAN.stages;
  function curStage() { return STG[st.s]; }
  function powerOn() {
    if (busy()) return Promise.resolve();
    if (st.on) return Promise.resolve();
    return S.hand.tap(K.main.btn, 'front').then(function () {
      st.on = true; K.main.power(true); K.aux.forEach(function (b) { b.power(true); });
      S.say('Switched on. Let the electronics warm up for a minute before the first reading.'); S.click(820, 0.05); S.render(); });
  }
  function setX(v) {
    if (busy()) return Promise.resolve(false);
    var sg = curStage();
    if (!isFinite(v) || v < sg.min - 1e-9 || v > sg.max + 1e-9) { S.say(sg.label + ': from ' + sg.min + ' to ' + sg.max + (sg.unit ? ' ' + sg.unit : '') + ' only.'); return Promise.resolve(false); }
    var x = sg.xk ? v * sg.xk : v;
    return PLAN.ctl(x, st.s).then(function () { st.x = x; st.last = null; S.render(); return true; });
  }
  function shownX(x, sg) { return sg.xk ? x / sg.xk : x; }
  function take() {
    if (busy()) return Promise.resolve(false);
    if (!st.on) { S.say('Switch the instruments on first.'); return Promise.resolve(false); }
    var sg = curStage();
    if (sg.prep && !st.prep[st.s]) { S.say('First: ' + sg.prep.label.toLowerCase() + '.'); return Promise.resolve(false); }
    var r = KN.read(p, st.s, st.x, st.idx); st.lastIdx = st.idx; st.idx += 1;
    if (!sg.count) { st.last = r; S.render(); return Promise.resolve(true); }
    st.counting = true; st.last = null;
    return S.hand.tap(K.main.btn, 'front').then(function () { return S.tween(900, function (k) { st.shown = Math.round((r.N !== undefined ? r.N : r.y) * k); }); })
      .then(function () { st.counting = false; st.last = r; st.shown = r.N !== undefined ? r.N : r.y; S.say('Counted ' + (r.N !== undefined ? r.N + ' in ' + r.T + ' s: ' + f(r.y, 3) + ' per second.' : f(r.y, 0) + ' counts.')); S.render(); return true; });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.last) { S.say('Take a reading first.'); return false; }
    if (st.rec === st.lastIdx) { S.say('That reading is already written down. Take a new one.'); return false; }
    st.rec = st.lastIdx;
    var row = { s: st.s, x: st.x }; Object.keys(st.last).forEach(function (k) { row[k] = st.last[k]; });
    S.addRow(row); return true;
  }
  function rowsOf(s) { return S.rows.filter(function (r) { return r.s === s; }); }
  function prep(i) {
    var sg = STG[i];
    if (!sg.prep || st.prep[i]) return Promise.resolve();
    if (busy()) return Promise.resolve();
    return sg.prep.fn().then(function () { st.prep[i] = true; S.say(sg.prep.label + ': done.'); S.render(); });
  }

  // ======================================================================== screens
  function screen() {
    var sg = curStage() || STG[0];
    var pts = rowsOf(st.s).map(function (r) { return [r.x, r.y]; });
    var sx = sg.show ? sg.show(st.x) : f(shownX(st.x, sg), sg.digits) + (sg.unit ? ' ' + sg.unit : '');
    var rd = !st.on ? 'OFF' : st.counting ? String(st.shown) : st.last ? (st.last.N !== undefined ? st.last.N + ' counts / ' + st.last.T + ' s' : f(st.last.y, 3) + (st.last.y2 !== undefined ? '   ' + f(st.last.y2, 2) : '')) : '---';
    var sig = sx + '|' + rd + '|' + pts.length + '|' + st.on;
    K.main.draw(sig, function (x, w, h) {
      if (!st.on) { x.fillStyle = '#0b0f0d'; x.fillRect(0, 0, w, h); return; }
      screenText(x, w, h, [sg.label.slice(0, 26), sx, rd], PLAN.screen === 'dvm' && pts.length < 3 ? null : pts);
    });
  }

  // ======================================================================== steps
  var steps = [{ id: 'on', title: 'Set up and switch on', view: 'app', render: function (u) {
      u.h2('Look at the apparatus, then switch on');
      u.p(S.lab.aim);
      u.task('Instruments on', st.on, st.on ? 'On' : 'Off').add(u.button('Switch on', function () { S.focus('unit'); powerOn(); }, !st.on, st.on || S.hand.busy));
      u.next('Next: ' + STG[0].title, st.on);
    }, ok: function () { return st.on; }, auto: function () { return powerOn(); } }];
  STG.forEach(function (sg, i) {
    steps.push({ id: 'st' + i, title: sg.title, view: i === 0 && !sg.prep ? 'unit' : 'app',
      enter: function () { st.s = i; st.last = null; },
      render: function (u) {
        st.s = i;
        u.h2(sg.h2); u.p(sg.text);
        if (sg.prep) u.task(sg.prep.label, !!st.prep[i], st.prep[i] ? 'Done' : 'Not yet').add(u.button(sg.prep.label, function () { prep(i); }, !st.prep[i], !!st.prep[i] || S.hand.busy));
        if (!sg.fixed) {
          var tg = { v: shownX(st.x, sg) };
          if (tg.v < sg.min || tg.v > sg.max || !isFinite(tg.v)) tg.v = sg.min;
          u.slider(sg.label, sg.min, sg.max, sg.step, function () { return tg.v; }, function (v) { tg.v = v; }, sg.show ? '' : sg.unit, sg.digits);
          u.row(u.button('Set', function () { setX(tg.v); }, false, S.hand.busy),
            u.button(sg.count ? 'START count' : 'Read', function () { take(); }, true, S.hand.busy),
            u.button('Record', function () { record(); }, false, S.hand.busy));
        } else {
          u.row(u.button(sg.count ? 'START count' : 'Read', function () { take(); }, true, S.hand.busy), u.button('Record', function () { record(); }, false, S.hand.busy));
        }
        u.live(function () { var sx = sg.show ? sg.show(st.x) : f(shownX(st.x, sg), sg.digits) + ' ' + (sg.unit || '');
          return sx + '  ·  ' + (st.counting ? 'counting ' + st.shown : st.last ? (st.last.N !== undefined ? st.last.N + ' counts, ' + f(st.last.y, 3) + ' /s' : f(st.last.y, 3) + (st.last.y2 !== undefined ? ' / ' + f(st.last.y2, 2) : '')) : 'no reading yet'); });
        u.h3('Observation table'); u.table();
        var last = i === STG.length - 1;
        u.next(last ? 'Next: the result' : 'Next: ' + STG[i + 1].title, rowsOf(i).length >= sg.minRows && (!last || S.result() !== null));
      },
      ok: function () { return rowsOf(i).length >= sg.minRows && (i < STG.length - 1 || S.result() !== null); },
      auto: function () {
        st.s = i;
        var list = KN.plan(p).filter(function (q) { return q[0] === i; }), c = prep(i);
        list.forEach(function (q) {
          c = c.then(function () { var v = shownX(q[1], sg); if (sg.fixed) { st.x = q[1]; return true; } return setX(v); })
            .then(function () { return take(); }).then(function () { record(); });
        });
        return c;
      } });
  });

  // ======================================================================== result
  function result(rows) {
    if (!rows.length) return null;
    var v = KN.fit(rows, p);
    if (!isFinite(v) || v === 0) return null;
    var tr = truthVal();
    return { label: PLAN.res.label, value: v * PLAN.res.k, unit: PLAN.res.unit, digits: PLAN.res.digits, truth: tr === null ? null : tr * PLAN.res.k,
      note: PLAN.note ? PLAN.note(rows) : '' };
  }

  var hudA = S.hudCard('Setting'), hudR = S.hudCard('Reading');
  var th0 = { principle: S.lab.theory, formula: '', formulaNote: '', more: (S.lab.steps || []).slice(0, 3), precautions: S.lab.safety || '' };
  return {
    camera: { pos: [0.1, 0.9, 1.15], look: [0.1, 0.1, -0.25] },
    views: Object.assign({ bench: [[0.1, 0.9, 1.15], [0.1, 0.1, -0.25]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] }, K.views),
    theory: th0,
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + (S.lab.aim || '').slice(0, 110), V_.sample ? 'Sample: ' + V_.sample : 'Apparatus as drawn on the bench.'], columns: PLAN.cols },
    graph: { x: PLAN.graph.x, y: PLAN.graph.y, xlabel: PLAN.graph.xlabel, ylabel: PLAN.graph.ylabel },
    result: result,
    tol: PLAN.tol,
    chips: ['What am I measuring?', 'Check my readings', 'What is the main source of error?'],
    viva: [],
    askState: function () { var sg = curStage() || STG[0]; return { experiment: S.lab.title, sample: V_.sample || '', switched_on: st.on, stage: sg.title, setting: sg.label + ' = ' + f(shownX(st.x, sg), sg.digits) + ' ' + (sg.unit || ''), last_reading: st.last, readings_taken: S.rows.length }; },
    steps: steps,
    tick: function (TDT) {
      screen();
      var sg = curStage() || STG[0];
      hudA.set(sg.show ? sg.show(st.x) : f(shownX(st.x, sg), sg.digits) + ' ' + (sg.unit || ''));
      hudR.set(st.last ? f(st.last.y, 3) : '-');
      if (KNAME === 'pm9_coupled' && K.parts.pends && st.mode >= 0) {
        st.tt += (TDT || 0.016); var w = KN.omegas(p), A = 0.06, t = st.tt * 0.6, a1, a2;
        if (st.mode === 0) { a1 = A * Math.cos(w[0] * t); a2 = a1; } else if (st.mode === 1) { a1 = A * Math.cos(w[1] * t); a2 = -a1; }
        else { a1 = A / 2 * (Math.cos(w[0] * t) + Math.cos(w[1] * t)); a2 = A / 2 * (Math.cos(w[0] * t) - Math.cos(w[1] * t)); }
        K.parts.pends[0].rotation.z = a1; K.parts.pends[1].rotation.z = a2;
        K.parts.spring.position.x = (Math.sin(a1) + Math.sin(a2)) * 0.15; K.parts.spring.scale.y = 1 + (Math.sin(a2) - Math.sin(a1)) * 0.3 / 0.14;
      }
      if (KNAME === 'pm9_stefan' && K.parts.fil) K.parts.fil.material = st.on && st.x > 0 ? mat(0xffc060, 0.3) : mat(0x664422, 0.5);
    },
  };
});
