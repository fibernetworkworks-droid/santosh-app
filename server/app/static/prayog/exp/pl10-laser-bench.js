/* Prayogshala studio RIG: the Ph.D. laser / atomic / quantum-optics table of wave 10 (pack phd_laser_w10, kernels pl10_*).
   One rig draws 15 set-ups (each a "kit") on a black optical breadboard and walks them the same honest way: every kernel
   is a SWEEP - the student sets one control x in one or more stages, takes a reading, records it. Every reading comes
   from KN.read(p, stage, x, k) on the lab's own params (k numbers the reading, so a photon count is the same Poisson
   number the server's check draws); the result is KN.fit(rows, p), the same fit the server checks against the
   textbook relation. Photon counts are SIMULATED DATA; the MOT and the BEC are simulated instruments. */
HoolaStudio.define('pl10-laser-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels;
  var KNAME = S.lab.kernel, KN = HK.K[KNAME];
  var p = HK.paramsFor(KNAME, S.lab.params);
  var V_ = S.lab.variant || {};
  var Q = Math.floor((p.q || 0) + 0.5);
  var DEG = Math.PI / 180;
  var st = { on: false, s: 0, x: 0, idx: 0, last: null, lastIdx: -1, rec: -1, counting: false, shown: 0, prep: {} };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function f(v, d) { return (v === null || v === undefined || !isFinite(v)) ? '-' : Number(v).toFixed(d); }
  function wp(o) { var v = new T.Vector3(); o.updateMatrixWorld(true); o.getWorldPosition(v); return v; }
  function mat(c, r, m) { return new T.MeshStandardMaterial({ color: c, roughness: r === undefined ? 0.5 : r, metalness: m || 0 }); }
  function glow(c) { return new T.MeshBasicMaterial({ color: c, toneMapped: false }); }
  function cyl(r1, r2, h, m, seg) { return S.mesh(new T.CylinderGeometry(r1, r2, h, seg || 28), m); }
  function bx(w, h, d, m) { return S.mesh(new T.BoxGeometry(w, h, d), m); }
  function lbl(text, w, color, bg) { return S.label(text, { w: w, ratio: 0.18, color: color || '#f2f2f2', bg: bg }); }
  function add(parent, o, x, y, z) { o.position.set(x, y, z); parent.add(o); return o; }

  // ======================================================================== the optical table
  var TOP = 0.024, BH = 0.105, ZB = -0.27;           // breadboard top, beam height, beam line
  (function table() {
    var tex = S.canvasTex(2048, 576, function (x, w, h) {
      x.fillStyle = '#1b1d21'; x.fillRect(0, 0, w, h);
      for (var i = 1; i < 60; i++) for (var j = 1; j < 17; j++) {
        var px = i * w / 60, py = j * h / 17;
        x.fillStyle = '#0a0b0d'; x.beginPath(); x.arc(px, py, 5.5, 0, Math.PI * 2); x.fill();
        x.strokeStyle = 'rgba(255,255,255,.08)'; x.lineWidth = 1.5; x.beginPath(); x.arc(px, py, 6.5, 0, Math.PI * 2); x.stroke();
      }
      x.fillStyle = 'rgba(255,255,255,.25)'; x.font = '600 22px "Public Sans", sans-serif'; x.fillText('M6 x 25 mm  ·  OPTICAL BREADBOARD', 24, h - 14);
    });
    var top = bx(1.52, TOP, 0.42, [M.iron, M.iron, new T.MeshStandardMaterial({ map: tex, roughness: 0.6, metalness: 0.3 }), M.iron, M.iron, M.iron]);
    top.position.set(-0.2, TOP / 2, ZB); S.scene.add(top);
    [[-0.92, -0.44], [-0.92, -0.1], [0.52, -0.44], [0.52, -0.1]].forEach(function (q) { var f0 = cyl(0.018, 0.02, 0.006, M.rubber, 16); f0.position.set(q[0], 0.003, q[1]); S.scene.add(f0); });
    S.contact(1.6, 0.5, -0.2, ZB, 0.55);
    S.addApparatus('table', top, 'Optical breadboard', 'A steel breadboard with an M6 hole grid on 25 mm centres; every mount is bolted down.');
  })();
  var G = function (x, z, ry) { var g = new T.Group(); g.position.set(x || 0, TOP, z === undefined ? ZB : z); g.rotation.y = ry || 0; S.scene.add(g); return g; };
  function post(g, h) {
    add(g, cyl(0.013, 0.015, 0.006, M.black, 20), 0, 0.003, 0);
    add(g, cyl(0.0065, 0.0065, h, M.steel, 16), 0, h / 2 + 0.006, 0);
  }
  // ======================================================================== components
  var C = {
    laser: function (x, len, label, col, z, w) {
      var g = G(x, z), W = w || 0.05;
      var body = S.rounded(len, W, W, 0.008, mat(col || 0x2b3440, 0.45, 0.25)); body.rotation.x = -Math.PI / 2; body.position.set(0, BH - W / 2, 0); g.add(body);
      var noz = cyl(0.009, 0.011, 0.02, M.black, 20); noz.rotation.z = Math.PI / 2; add(g, noz, len / 2 + 0.01, BH, 0);
      add(g, bx(len * 0.9, BH - W, 0.03, M.black), 0, (BH - W) / 2, 0);
      var l = lbl(label, Math.min(len * 0.8, 0.2), '#f2f2f2'); add(g, l, 0, BH, W / 2 + 0.001);
      var warn = S.canvasTex(128, 128, function (c, w2, h2) { c.fillStyle = '#f2d02a'; c.beginPath(); c.moveTo(64, 8); c.lineTo(122, 116); c.lineTo(6, 116); c.closePath(); c.fill();
        c.fillStyle = '#111'; c.font = '700 54px sans-serif'; c.textAlign = 'center'; c.fillText('*', 64, 104); });
      var wt = new T.Mesh(new T.PlaneGeometry(0.02, 0.02), new T.MeshStandardMaterial({ map: warn, transparent: true })); add(g, wt, -len / 2 + 0.02, BH + 0.004, W / 2 + 0.001);
      S.contact(len + 0.04, W + 0.04, x, z === undefined ? ZB : z, 0.4);
      return g;
    },
    mirror: function (x, ry, z) {
      var g = G(x, z, ry); post(g, BH - 0.02);
      add(g, bx(0.006, 0.04, 0.04, M.black), 0.004, BH, 0);
      var m = cyl(0.0125, 0.0125, 0.004, M.chrome, 32); m.rotation.z = Math.PI / 2; add(g, m, -0.001, BH, 0);
      [[0.012, 0.012], [-0.012, 0.012], [0.012, -0.012]].forEach(function (q) { var sc = cyl(0.002, 0.002, 0.012, M.brass, 8); sc.rotation.z = Math.PI / 2; add(g, sc, 0.012, BH + q[0], q[1]); });
      return g;
    },
    bs: function (x, z) { var g = G(x, z); post(g, BH - 0.015); add(g, bx(0.022, 0.022, 0.022, M.glassBlock), 0, BH, 0); add(g, bx(0.03, 0.004, 0.03, M.black), 0, BH - 0.013, 0); return g; },
    lens: function (x, z) { var g = G(x, z); post(g, BH - 0.02); var r = S.mesh(new T.TorusGeometry(0.016, 0.003, 10, 28), M.black); r.rotation.y = Math.PI / 2; add(g, r, 0, BH, 0);
      var l = cyl(0.015, 0.015, 0.005, M.glass, 28); l.rotation.z = Math.PI / 2; add(g, l, 0, BH, 0); return g; },
    plate: function (x, label, z) {
      var g = G(x, z); post(g, BH - 0.024);
      var ring = new T.Group(); add(g, ring, 0, BH, 0);
      var rm = S.mesh(new T.TorusGeometry(0.019, 0.005, 10, 32), M.black); rm.rotation.y = Math.PI / 2; ring.add(rm);
      var d = cyl(0.016, 0.016, 0.002, M.glass, 28); d.rotation.z = Math.PI / 2; ring.add(d);
      var mark = bx(0.002, 0.008, 0.002, M.white); mark.position.set(0.003, 0.02, 0); ring.add(mark);
      if (label) { var l = lbl(label, 0.05, '#2b2f36', '#e8e6df'); l.rotation.y = 0; add(g, l, 0, BH - 0.035, 0.012); }
      return { g: g, ring: ring };
    },
    cell: function (x, len, label, tint, z, heater) {
      var g = G(x, z); post(g, BH - 0.026);
      var c = S.mesh(new T.CylinderGeometry(0.0125, 0.0125, len, 28, 1, true), new T.MeshPhysicalMaterial({ color: tint || 0xffe8c8, roughness: 0.05, transmission: 0.85, thickness: 0.003, transparent: true, side: T.DoubleSide }));
      c.rotation.z = Math.PI / 2; add(g, c, 0, BH, 0);
      [-1, 1].forEach(function (s) { var w = cyl(0.0135, 0.0135, 0.002, M.glass, 28); w.rotation.z = Math.PI / 2; add(g, w, s * len / 2, BH, 0); });
      add(g, bx(0.012, 0.01, 0.03, M.black), 0, BH - 0.017, 0);
      if (heater) { for (var i = 0; i < 9; i++) { var t = S.mesh(new T.TorusGeometry(0.0138, 0.0012, 6, 24), M.copper); t.rotation.y = Math.PI / 2; add(g, t, -len / 2 + len * (i + 0.5) / 9, BH, 0); } }
      if (label) { var l = lbl(label, Math.min(0.09, len * 1.3), '#2b2f36', '#e8e6df'); add(g, l, 0, BH - 0.032, 0.016); }
      return g;
    },
    det: function (x, label, ry, z) {
      var g = G(x, z, ry); post(g, BH - 0.018);
      add(g, bx(0.02, 0.034, 0.034, mat(0x30343b, 0.4, 0.4)), 0.006, BH, 0);
      var a = cyl(0.007, 0.007, 0.003, M.black, 20); a.rotation.z = Math.PI / 2; add(g, a, -0.0055, BH, 0);
      var bnc = cyl(0.003, 0.003, 0.012, M.chrome, 10); bnc.rotation.z = Math.PI / 2; add(g, bnc, 0.022, BH, 0);
      if (label) { var l = lbl(label, 0.06, '#2b2f36', '#e8e6df'); add(g, l, 0.006, BH - 0.03, 0.018); }
      return g;
    },
    stage: function (x, len, label, z) {
      var g = G(x, z);
      add(g, bx(len + 0.04, 0.014, 0.05, mat(0x2a2e34, 0.4, 0.5)), 0, 0.007, 0);
      add(g, bx(len, 0.004, 0.01, M.chrome), 0, 0.016, 0);
      var car = new T.Group(); add(g, car, 0, 0.018, 0);
      add(car, bx(0.05, 0.012, 0.05, M.alu), 0, 0.006, 0);
      var mic = cyl(0.007, 0.007, 0.05, M.chrome, 16); mic.rotation.z = Math.PI / 2; add(g, mic, len / 2 + 0.045, 0.012, 0);
      var th = cyl(0.009, 0.009, 0.02, mat(0x9ba3ab, 0.25, 0.8), 24); th.rotation.z = Math.PI / 2; add(g, th, len / 2 + 0.075, 0.012, 0);
      var sc = S.canvasTex(512, 48, function (c, w, h) { c.fillStyle = '#e8e6df'; c.fillRect(0, 0, w, h); c.fillStyle = '#111';
        for (var i = 0; i <= 50; i++) { c.fillRect(i * w / 50, 0, 2, i % 5 ? 14 : 26); } });
      var strip = new T.Mesh(new T.PlaneGeometry(len, 0.008), new T.MeshStandardMaterial({ map: sc })); strip.rotation.x = -Math.PI / 2; add(g, strip, 0, 0.0145, 0.02);
      if (label) { var l = lbl(label, 0.08, '#f2f2f2'); add(g, l, -len / 2 + 0.03, 0.008, 0.0255); }
      S.contact(len + 0.1, 0.07, x, z === undefined ? ZB : z, 0.4);
      return { g: g, car: car, thimble: th, len: len };
    },
    rstage: function (x, label, z) {
      var g = G(x, z); post(g, BH - 0.045);
      add(g, cyl(0.03, 0.03, 0.012, mat(0x2a2e34, 0.4, 0.5), 32), 0, BH - 0.033, 0);
      var top = new T.Group(); add(g, top, 0, BH - 0.026, 0);
      var dial = S.canvasTex(512, 512, function (c, w) { c.fillStyle = '#d9dcdf'; c.fillRect(0, 0, w, w); c.strokeStyle = '#111';
        for (var a = 0; a < 360; a += 2) { var t = a * DEG, r1 = a % 10 ? 236 : 220; c.lineWidth = a % 10 ? 1.5 : 3; c.beginPath(); c.moveTo(256 + Math.cos(t) * 252, 256 + Math.sin(t) * 252); c.lineTo(256 + Math.cos(t) * r1, 256 + Math.sin(t) * r1); c.stroke(); } });
      var dt = new T.Mesh(new T.CircleGeometry(0.029, 40), new T.MeshStandardMaterial({ map: dial, roughness: 0.4 })); dt.rotation.x = -Math.PI / 2; dt.position.y = 0.0005; top.add(dt);
      if (label) { var l = lbl(label, 0.06, '#f2f2f2'); add(g, l, 0, BH - 0.04, 0.031); }
      return { g: g, top: top };
    },
    coils: function (x, R, z) {
      var g = G(x, z);
      [-1, 1].forEach(function (s) { var t = S.mesh(new T.TorusGeometry(R, 0.012, 12, 48), M.copper); t.rotation.y = Math.PI / 2; add(g, t, s * R / 2, BH + 0.0, 0);
        add(g, bx(0.02, BH - R + 0.01, 0.04, M.darkWood), s * R / 2, (BH - R + 0.01) / 2, 0); });
      return g;
    },
    lamp: function (x, label, col, z) {
      var g = G(x, z); post(g, BH - 0.04);
      var h = cyl(0.025, 0.025, 0.08, mat(0x3a3d42, 0.45, 0.4), 24); add(g, h, 0, BH, 0);
      var win = bx(0.004, 0.03, 0.006, glow(col || 0xff6070)); add(g, win, 0.026, BH, 0);
      var l = lbl(label, 0.06, '#f2f2f2'); add(g, l, 0, BH + 0.0, 0.026);
      return { g: g, win: win };
    },
    box: function (x, w, h, d, label, col, z, ry) {
      var g = G(x, z, ry);
      var b = S.rounded(w, d, h, 0.006, mat(col || 0x30343b, 0.45, 0.25)); b.rotation.x = -Math.PI / 2; b.position.y = h / 2; g.add(b);
      var l = lbl(label, Math.min(w * 0.85, 0.2), '#f2f2f2'); add(g, l, 0, h * 0.7, d / 2 + 0.001);
      S.contact(w + 0.04, d + 0.04, x, z === undefined ? ZB : z, 0.4);
      return g;
    },
    vac: function (x, z) {
      var g = G(x, z); post(g, BH - 0.03);
      add(g, bx(0.05, 0.05, 0.05, M.glassBlock), 0, BH, 0);
      [[0.03, 0, 0, 0, 0, Math.PI / 2], [-0.03, 0, 0, 0, 0, Math.PI / 2], [0, 0, 0.03, Math.PI / 2, 0, 0], [0, 0, -0.03, Math.PI / 2, 0, 0]].forEach(function (q) {
        var fl = cyl(0.02, 0.02, 0.008, M.steel, 24); fl.rotation.set(q[3], q[4], q[5]); add(g, fl, q[0], BH + q[1], q[2]); });
      var pipe = cyl(0.008, 0.008, 0.12, M.steel, 16); add(g, pipe, 0, BH + 0.085, -0.0);
      add(g, cyl(0.03, 0.03, 0.05, M.steel, 24), 0, BH + 0.16, 0);
      var cloud = S.mesh(new T.SphereGeometry(0.004, 16, 12), new T.MeshBasicMaterial({ color: 0xff6060, transparent: true, opacity: 0.0, toneMapped: false })); add(g, cloud, 0, BH, 0);
      return { g: g, cloud: cloud };
    },
    camera: function (x, ry, z) {
      var g = G(x, z, ry); post(g, BH - 0.02);
      add(g, bx(0.04, 0.04, 0.04, mat(0x2d3746, 0.4, 0.3)), 0.01, BH, 0);
      var ln = cyl(0.012, 0.012, 0.03, M.black, 20); ln.rotation.z = Math.PI / 2; add(g, ln, -0.024, BH, 0);
      return g;
    },
  };
  var beams = [];
  function beam(pts, col, r) {
    var m = new T.MeshBasicMaterial({ color: col || 0xff2020, transparent: true, opacity: 0.85, toneMapped: false });
    for (var i = 0; i + 1 < pts.length; i++) {
      var a = new T.Vector3(pts[i][0], pts[i][1], pts[i][2]), b = new T.Vector3(pts[i + 1][0], pts[i + 1][1], pts[i + 1][2]);
      var L = a.distanceTo(b); if (L < 1e-6) continue;
      var c = new T.Mesh(new T.CylinderGeometry(r || 0.0012, r || 0.0012, L, 6), m);
      c.position.copy(a).add(b).multiplyScalar(0.5);
      c.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), b.clone().sub(a).normalize());
      c.visible = false; S.scene.add(c); beams.push(c);
    }
  }
  var Y = TOP + BH;
  function line(x0, x1, z, col) { beam([[x0, Y, z], [x1, Y, z]], col); }

  // ======================================================================== instrument box (case, printed panel, screen, knob, button)
  function instr(o) {
    var g = new T.Group(); g.position.set(o.x, 0, o.z); g.rotation.y = o.ry || 0; S.scene.add(g);
    var W = o.w || 0.3, D = o.d || 0.22, H = o.h || 0.12;
    var cs = S.rounded(W, D, H, 0.01, mat(o.color || 0xd7d3c9, 0.5, 0.12)); cs.rotation.x = -Math.PI / 2; cs.position.y = H / 2 + 0.004; g.add(cs);
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (q) { add(g, cyl(0.008, 0.009, 0.004, M.rubber, 12), q[0] * (W / 2 - 0.02), 0.002, q[1] * (D / 2 - 0.02)); });
    var FZ = D / 2 + 0.006, PW = W - 0.014, PH = H - 0.014;
    var tex = S.canvasTex(1024, Math.round(1024 * PH / PW), function (x, w, h) {
      x.fillStyle = o.panel || '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 3; x.strokeRect(8, 8, w - 16, h - 16);
      x.fillStyle = '#f1efe8'; x.font = '700 ' + Math.round(h * 0.11) + 'px "Public Sans", sans-serif'; x.fillText(o.title || '', 22, h * 0.15);
      x.font = '500 ' + Math.round(h * 0.07) + 'px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText(o.sub || '', 22, h * 0.26);
      x.textAlign = 'center'; x.fillStyle = '#f1efe8'; x.font = '600 ' + Math.round(h * 0.07) + 'px "Public Sans", sans-serif';
      x.fillText(o.knobLabel || 'ADJUST', w * 0.84, h * 0.9); x.fillText('RUN', w * 0.65, h * 0.9);
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
    x.fillStyle = '#0d1a14'; x.fillRect(0, 0, w, h);
    var ink = '#7dffb0';
    x.fillStyle = ink; x.font = '600 ' + Math.round(h * 0.1) + 'px "JetBrains Mono", monospace';
    (lines || []).forEach(function (t, i) { x.fillText(t, 14, h * (0.14 + 0.12 * i)); });
    var tr = opts.trace, all = (pts || []).concat(tr || []);
    if (!all.length) return;
    var X0 = w * 0.06, X1 = w * 0.97, Y0 = h * 0.95, Y1 = h * (0.18 + 0.12 * (lines || []).length);
    var xs = all.map(function (q) { return q[0]; }), ys = all.map(function (q) { return q[1]; });
    var xa = Math.min.apply(null, xs), xb = Math.max.apply(null, xs), ya = Math.min.apply(null, ys), yb = Math.max.apply(null, ys);
    if (opts.zero) ya = Math.min(ya, 0);
    if (xb === xa) xb = xa + 1; if (yb === ya) yb = ya + 1;
    function px(v) { return X0 + (v - xa) / (xb - xa) * (X1 - X0); }
    function py(v) { return Y0 - (v - ya) / (yb - ya) * (Y0 - Y1); }
    x.strokeStyle = 'rgba(125,255,176,.3)'; x.lineWidth = 2; x.strokeRect(X0, Y1, X1 - X0, Y0 - Y1);
    if (tr && tr.length) { x.strokeStyle = '#ffd36b'; x.lineWidth = 2.5; x.beginPath(); tr.forEach(function (q, i) { if (i) x.lineTo(px(q[0]), py(q[1])); else x.moveTo(px(q[0]), py(q[1])); }); x.stroke(); }
    if (opts.cursor !== undefined && opts.cursor !== null) { x.strokeStyle = '#ff6b6b'; x.lineWidth = 2; x.beginPath(); x.moveTo(px(opts.cursor), Y1); x.lineTo(px(opts.cursor), Y0); x.stroke(); }
    x.fillStyle = ink;
    (pts || []).forEach(function (q) { x.fillRect(px(q[0]) - 3, py(q[1]) - 3, 6, 6); });
  }

  // ======================================================================== motions
  function knobAngle(min, max, v) { return 3 * Math.PI / 4 - 1.5 * Math.PI * Math.max(0, Math.min(1, (v - min) / ((max - min) || 1))); }
  function turn(box, min, max, v) {
    var kn = box ? box.knob : null;
    if (!kn) return Promise.resolve();
    var a0 = kn.rotation.z, a1 = knobAngle(min, max, v), pt = wp(kn).add(new T.Vector3(0, 0, 0.01));
    if (Math.abs(a1 - a0) < 1e-6) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { kn.rotation.z = a0 + (a1 - a0) * k; }, { mode: 'front', ms: 450, reachMs: 500 })
      .then(function () { kn.rotation.z = a1; });
  }
  function rotTo(obj, axis, ang) {
    var a0 = obj.rotation[axis], pt = wp(obj).add(new T.Vector3(0, 0.02, 0.02));
    if (Math.abs(ang - a0) < 1e-6) return Promise.resolve();
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { obj.rotation[axis] = a0 + (ang - a0) * k; }, { mode: 'side', ms: 500, reachMs: 450 })
      .then(function () { obj.rotation[axis] = ang; });
  }
  function slideTo(stg, pos, spin) {           // pos in metres along the stage axis (carriage centre from the stage centre)
    var car = stg.car, x0 = car.position.x, x1 = Math.max(-stg.len / 2, Math.min(stg.len / 2, pos));
    var a0 = stg.thimble.rotation.x, a1 = a0 + (spin || 0);
    if (Math.abs(x1 - x0) < 1e-7 && !spin) return Promise.resolve();
    var pt = wp(stg.thimble).add(new T.Vector3(0.012, 0, 0));
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { car.position.x = x0 + (x1 - x0) * k; stg.thimble.rotation.x = a0 + (a1 - a0) * k; }, { mode: 'side', ms: 600, reachMs: 450 })
      .then(function () { car.position.x = x1; stg.thimble.rotation.x = a1; });
  }
  function moveObj(obj, to) {
    if (obj.position.distanceTo(to) < 1e-4) return Promise.resolve();
    var from = obj.position.clone();
    var path = function (k) { return new T.Vector3(from.x + (to.x - from.x) * k, Math.max(from.y, to.y) + 0.05 * Math.sin(Math.PI * k), from.z + (to.z - from.z) * k); };
    return S.hand.pinchMove(wp(obj).add(new T.Vector3(0, 0.1, 0)), function (k) { return path(k).add(new T.Vector3(0, 0.1, 0)); }, function (k) { obj.position.copy(path(k)); }, { mode: 'top', ms: 800, reachMs: 500 })
      .then(function () { obj.position.copy(to); });
  }
  function mainBox(title, sub, knobLabel, w) {
    var b = instr({ x: 0.8, z: -0.22, ry: -0.35, w: w || 0.36, h: 0.14, color: 0x30343b, panel: '#1c2027', title: title, sub: sub, knobLabel: knobLabel });
    K.main = b; S.addApparatus('unit', b.g, title, 'Reads the detector and sets the control of this step.');
    K.views.unit = [[0.82, 0.44, 0.36], [0.8, 0.08, -0.22]];
    S.wire([[0.45, 0.06, -0.12], [0.6, 0.03, -0.05], [0.68, 0.05, -0.15]], 'black');
    return b;
  }
  function appView(x) { K.views.app = [[x || -0.2, 0.55, 0.5], [x || -0.2, 0.08, ZB]]; }

  // ======================================================================== kits
  var K = { parts: {}, views: {}, main: null, aux: [] };
  function srcName(def) { return V_.sample || def; }

  function kitSatAbs() {
    C.laser(-0.82, 0.12, 'DIODE 780 nm', 0x2b3440);
    var bsP = C.bs(-0.6); var cell = C.cell(-0.3, 0.075, /heated|60 C/i.test(srcName('')) ? 'Rb CELL 60 C' : 'NATURAL Rb', 0xffe2b8, ZB, true);
    var hwp = C.plate(-0.48, 'PUMP lambda/2');
    C.mirror(0.0, 0); C.det(-0.62, 'PD A', Math.PI, ZB + 0.06); C.det(-0.62, 'PD B', Math.PI, ZB + 0.11);
    var fp = C.box(-0.62, 0.08, 0.06, 0.06, 'FABRY-PEROT', 0x3a3f47, ZB - 0.11);
    line(-0.76, -0.6, ZB, 0xff3030); line(-0.6, 0.0, ZB, 0xff3030); line(-0.6, -0.6, ZB, 0xff3030);
    beam([[-0.6, Y, ZB + 0.004], [0.0, Y, ZB + 0.004]], 0xff6060); beam([[-0.6, Y, ZB], [-0.6, Y, ZB + 0.1]], 0xff6060);
    K.parts.hwp = hwp;
    S.addApparatus('cell', cell, srcName('Natural Rb vapour cell'), 'A glass cell of rubidium vapour in its heater winding; pump and probe beams cross it in opposite directions.');
    S.addApparatus('laser', bsP, 'Thick glass plate', 'Its two surface reflections make the probe and the reference beams; the main beam goes on as the pump.');
    S.addApparatus('fp', fp, 'Fabry-Perot etalon', 'Its marker fringes calibrate the scan in megahertz.');
    appView(-0.35);
    mainBox('DIGITAL OSCILLOSCOPE', 'difference signal  ·  cursor + peak search', 'CURSOR');
  }
  function kitOptPump() {
    var lamp = C.lamp(-0.82, 'Rb LAMP', 0xff4a4a);
    C.lens(-0.7); C.plate(-0.62, 'D1 + lambda/4');
    var coil = C.coils(-0.32, 0.12); C.cell(-0.32, 0.05, 'Rb CELL', 0xffe2b8, ZB, true);
    C.lens(-0.1); C.det(0.02, 'PHOTODIODE', 0);
    line(-0.79, 0.01, ZB, 0xff5a5a);
    K.parts.lamp = lamp;
    S.addApparatus('lamp', K.parts.lamp.g, 'Rubidium discharge lamp', 'An RF-excited lamp glowing on the rubidium lines; the filter passes D1 only.');
    S.addApparatus('coils', coil, 'Helmholtz coils round the Rb cell', 'Their axial field plus the Earth\'s field sets the Zeeman splitting; an RF coil sits beside the cell.');
    appView(-0.4);
    mainBox('RF + COIL SUPPLY', 'RF synthesiser  ·  coil current  ·  scope', 'RF kHz');
  }
  function kitHD() {
    var lamps = [C.lamp(-0.82, 'He', 0xffe070), C.lamp(-0.82, 'H2', 0xff4a8a, ZB + 0.13), C.lamp(-0.7, 'D2', 0xff6ab0, ZB + 0.13)];
    K.parts.lamps = lamps; K.parts.slot = new T.Vector3(-0.82, TOP, ZB);
    K.parts.store = [new T.Vector3(-0.82, TOP, ZB + 0.13), new T.Vector3(-0.82, TOP, ZB + 0.13), new T.Vector3(-0.7, TOP, ZB + 0.13)];
    var mono = C.box(-0.4, 0.5, 0.15, 0.2, '1 m SCANNING MONOCHROMATOR', 0x2f3a46);
    var drum = cyl(0.018, 0.018, 0.02, M.chrome, 24); drum.rotation.x = Math.PI / 2; add(mono, drum, 0.18, 0.08, 0.11); K.parts.drum = drum;
    C.det(-0.08, 'PMT', 0);
    line(-0.79, -0.65, ZB, 0xff8080);
    S.addApparatus('mono', mono, '1 m scanning monochromator', 'A grating monochromator whose wavelength counter is calibrated against the helium lines.');
    S.addApparatus('lamps', lamps[0].g, 'Discharge lamps', 'Helium (calibration), hydrogen and deuterium lamps; one at a time at the entrance slit.');
    appView(-0.45);
    mainBox('WAVELENGTH COUNTER', 'PMT current  ·  line centre', 'SCAN');
  }
  function kitDiode() {
    var mount = C.box(-0.78, 0.09, 0.09, 0.07, 'TEC MOUNT', 0x3a4250);
    C.laser(-0.78, 0.04, '', 0x1c1f24, ZB, 0.025);
    C.lens(-0.66); var bsP = C.bs(-0.5);
    C.det(-0.2, 'POWER METER', 0); C.box(-0.5, 0.1, 0.05, 0.06, 'WAVEMETER', 0x2b3a4a, ZB - 0.12);
    line(-0.73, -0.21, ZB, /650/.test(srcName('')) ? 0xff2a10 : 0xb01030); beam([[-0.5, Y, ZB], [-0.5, Y, ZB - 0.09]], 0xb01030);
    S.addApparatus('mount', mount, srcName('780 nm diode laser') + ' in a Peltier mount', 'The thermistor and Peltier element hold the case temperature; the current driver sets the drive current.');
    S.addApparatus('bs', bsP, 'Beam sampler', 'Sends a small part of the beam to the wavemeter.');
    var tec = instr({ x: 0.36, z: -0.02, ry: -0.2, w: 0.22, h: 0.1, title: 'TEC CONTROLLER', sub: 'case temperature', knobLabel: 'SET C' });
    K.aux.push(tec); K.parts.tec = tec;
    appView(-0.45);
    mainBox('LASER DIODE DRIVER', 'current  ·  power  ·  wavelength', 'mA');
  }
  function kitLock() {
    C.laser(-0.82, 0.12, 'DIODE 780 nm', 0x2b3440); C.bs(-0.6); C.cell(-0.4, 0.06, 'Rb REF', 0xffe2b8); C.det(-0.2, 'PD', 0);
    C.bs(-0.6, ZB + 0.0); C.det(-0.6, 'BEAT PD', -Math.PI / 2, ZB + 0.12);
    C.laser(-0.25, 0.1, 'REFERENCE LASER', 0x3b2f40, ZB + 0.12);
    line(-0.76, -0.21, ZB, 0xff3030); beam([[-0.6, Y, ZB], [-0.6, Y, ZB + 0.11]], 0xff6060); beam([[-0.31, Y, ZB + 0.12], [-0.6, Y, ZB + 0.12]], 0xff6060);
    var li = instr({ x: 0.36, z: -0.02, ry: -0.2, w: 0.22, h: 0.1, title: 'LOCK-IN + PI SERVO', sub: p.m < 0.5 ? 'side of fringe' : 'dither 1 MHz', knobLabel: 'GAIN' });
    K.aux.push(li);
    S.addApparatus('ref', li.g, 'Lock-in amplifier and PI servo', p.m < 0.5 ? 'Side-of-fringe: the error is the dip signal minus half its height.' : 'Dither lock: the current is modulated and the lock-in output is the derivative of the line.');
    appView(-0.45);
    mainBox('SPECTRUM / RMS ANALYSER', 'error signal  ·  beat note', 'f');
  }
  function kitSHG() {
    C.laser(-0.82, 0.14, 'Nd:YAG 1064 nm', 0x2c3a2c);
    var hwp = C.plate(-0.66, 'lambda/2'); C.bs(-0.58); C.lens(-0.48);
    var rs = C.rstage(-0.36, 'ROTATION');
    var cr = bx(0.012, 0.012, 0.012, new T.MeshPhysicalMaterial({ color: p.cry < 0.5 ? 0xeef6ff : 0xfffbe8, roughness: 0.05, transmission: 0.9, thickness: 0.01, transparent: true }));
    add(rs.top, cr, 0, 0.026, 0); add(rs.top, bx(0.02, 0.016, 0.02, M.black), 0, 0.008, 0);
    var cl = lbl(p.cry < 0.5 ? 'KDP' : 'BBO', 0.025, '#2b2f36', '#e8e6df'); add(rs.top, cl, 0, 0.004, 0.0105);
    C.plate(-0.2, 'IR FILTER'); C.det(-0.06, 'POWER METER', 0);
    line(-0.75, -0.36, ZB, 0x8a1a1a); line(-0.36, -0.2, ZB, 0x8a1a1a); line(-0.36, -0.07, ZB + 0.002, 0x30ff40);
    K.parts.hwp = hwp; K.parts.rs = rs;
    S.addApparatus('crystal', rs.g, srcName(p.cry < 0.5 ? 'KDP crystal' : 'BBO crystal') + ' on a rotation stage', 'Type-I crystal cut near the phase-matching angle; the stage reads the external tilt.');
    appView(-0.45);
    mainBox('POWER METER READ-OUT', 'green power (532 nm)', 'TILT');
  }
  function kitZScan() {
    C.laser(-0.82, 0.12, 'ps 532 nm', 0x2c3a2c); C.lens(-0.6);
    var stg = C.stage(-0.4, 0.16, 'MOTORISED RAIL');
    var cuv = bx(0.004, 0.03, 0.012, new T.MeshPhysicalMaterial({ color: /dye/i.test(srcName('')) ? 0xff7ab0 : /colloid/i.test(srcName('')) ? 0xd9a040 : 0xf6f6ff, roughness: 0.05, transmission: 0.8, thickness: 0.002, transparent: true }));
    add(stg.car, add(new T.Group(), cuv, 0, BH - 0.018, 0), 0, 0, 0);
    add(stg.car, cyl(0.004, 0.004, BH - 0.04, M.steel, 10), 0, (BH - 0.04) / 2 + 0.012, 0);
    C.bs(-0.16); C.det(-0.16, 'OPEN', -Math.PI / 2, ZB + 0.1); C.plate(-0.02, 'APERTURE'); C.det(0.08, 'CLOSED', 0);
    line(-0.76, 0.07, ZB, 0x30ff40); beam([[-0.16, Y, ZB], [-0.16, Y, ZB + 0.09]], 0x30ff40);
    K.parts.stg = stg;
    S.addApparatus('sample', stg.g, srcName('CS2 in a 1 mm cell') + ' on the rail', 'The rail moves the sample through the focus of the lens; z = 0 is the focus.');
    appView(-0.35);
    mainBox('TWO-CHANNEL ENERGY METER', 'open + closed aperture', 'z mm');
  }
  function kitTCSPC() {
    C.laser(-0.82, 0.1, 'PICOSECOND DIODE', 0x30304a);
    var cuv = C.box(-0.6, 0.03, 0.05, 0.03, '', 0x1c1f24); add(cuv, bx(0.012, 0.03, 0.012, mat(/ruby/i.test(srcName('')) ? 0xc0203a : /dot/i.test(srcName('')) ? 0xff9a30 : 0xff6a90, 0.2, 0.1)), 0, 0.065, 0);
    C.lens(-0.5); C.box(-0.32, 0.18, 0.1, 0.12, 'MONOCHROMATOR', 0x2f3a46); C.det(-0.14, 'SPAD', 0);
    C.box(-0.14, 0.16, 0.05, 0.1, 'TCSPC MODULE', 0x24303a, ZB + 0.14);
    line(-0.76, -0.6, ZB, 0x4060ff); line(-0.6, -0.15, ZB, 0xff9050);
    S.addApparatus('sample', cuv, srcName('Rhodamine 6G in water'), 'The cuvette in its holder; the emission is collected at right angles to the excitation in the real set-up.');
    appView(-0.45);
    mainBox('HISTOGRAM DISPLAY', p.ms > 0.5 ? 'multichannel scaling  ·  ms' : 'start-stop  ·  ns', 'BIN');
  }
  function kitPumpProbe() {
    C.laser(-0.85, 0.14, 'fs Ti:SAPPHIRE', 0x2b3440); C.bs(-0.66);
    var stg = C.stage(-0.42, 0.14, 'DELAY STAGE', ZB + 0.12);
    var rr = cyl(0.012, 0.012, 0.012, M.chrome, 20); rr.rotation.z = Math.PI / 2; add(stg.car, rr, 0, BH - 0.012, 0);
    add(stg.car, cyl(0.004, 0.004, BH - 0.03, M.steel, 10), 0, (BH - 0.03) / 2 + 0.012, 0);
    C.mirror(-0.2, 0, ZB + 0.12); C.plate(-0.5, 'CHOPPER');
    C.cell(-0.2, 0.006, srcName('FILM'), 0xb0b8c0); C.det(-0.05, 'PROBE PD', 0);
    line(-0.78, -0.2, ZB, 0xb02020); beam([[-0.66, Y, ZB], [-0.66, Y, ZB + 0.12], [-0.42, Y, ZB + 0.12]], 0xff4040);
    K.parts.stg = stg;
    S.addApparatus('stage', stg.g, 'Retro-reflector on a delay stage', 'Moving it by 1 mm delays the probe by 6.67 ps.');
    appView(-0.4);
    mainBox('LOCK-IN dT/T', 'probe transmission change', 'SCAN');
  }
  function kitMOT(bec) {
    var v = C.vac(-0.35);
    [-1, 1].forEach(function (s) { var t = S.mesh(new T.TorusGeometry(0.035, 0.008, 10, 32), M.copper); t.rotation.x = Math.PI / 2; add(v.g, t, 0, BH + s * 0.035, 0); });
    C.laser(-0.82, 0.12, 'COOLING 780 nm', 0x2b3440);
    C.mirror(-0.62, 0); C.mirror(-0.08, Math.PI);
    C.camera(-0.35, Math.PI / 2, ZB + 0.15); C.lens(-0.55, ZB + 0.12); C.det(-0.62, 'FLUOR. PD', Math.PI, ZB + 0.12);
    line(-0.76, -0.08, ZB, 0xff3030); beam([[-0.35, Y, ZB - 0.12], [-0.35, Y, ZB + 0.12]], 0xff3030);
    K.parts.vac = v;
    S.addApparatus('vac', v.g, bec ? 'Magnetic trap in the science chamber' : 'Glass vacuum cell with quadrupole coils', bec ? 'Atoms from the MOT are held in the magnetic trap and cooled by RF evaporation.' : 'Six beams cross at the zero of the quadrupole field; the atoms gather there.');
    appView(-0.35);
    mainBox(bec ? 'IMAGING + RF CONTROL' : 'MOT CONTROL', bec ? 'bimodal fit  ·  RF evaporation' : 'fluorescence  ·  time of flight', bec ? 'RF' : 'SET');
  }
  function kitMich() {
    var srcs = [C.laser(-0.82, 0.1, 'He-Ne 632.8', 0x2b3440), C.lamp(-0.82, 'LED', 0xff5030, ZB + 0.15), C.lamp(-0.7, 'Na LAMP', 0xffc040, ZB + 0.15)];
    K.parts.srcs = srcs; K.parts.slot = new T.Vector3(-0.82, TOP, ZB);
    K.parts.store = [new T.Vector3(-0.82, TOP, ZB - 0.12), new T.Vector3(-0.82, TOP, ZB + 0.15), new T.Vector3(-0.7, TOP, ZB + 0.15)];
    srcs[0].position.copy(K.parts.store[0]);
    C.bs(-0.6); C.mirror(-0.6, -Math.PI / 2, ZB - 0.12);
    var stg = C.stage(-0.3, 0.22, 'LONG-TRAVEL STAGE');
    var mm = cyl(0.0125, 0.0125, 0.004, M.chrome, 32); mm.rotation.z = Math.PI / 2; add(stg.car, mm, 0.01, BH - 0.012, 0);
    add(stg.car, bx(0.006, 0.04, 0.04, M.black), 0.014, BH - 0.012, 0);
    add(stg.car, cyl(0.005, 0.005, BH - 0.035, M.steel, 10), 0.012, (BH - 0.035) / 2 + 0.012, 0);
    C.det(-0.6, 'PD + COUNTER', -Math.PI / 2, ZB + 0.11);
    line(-0.77, -0.6, ZB, 0xff3030); line(-0.6, -0.3, ZB, 0xff3030); beam([[-0.6, Y, ZB], [-0.6, Y, ZB - 0.12]], 0xff3030); beam([[-0.6, Y, ZB], [-0.6, Y, ZB + 0.1]], 0xff3030);
    K.parts.stg = stg;
    S.addApparatus('stage', stg.g, 'Moving mirror on a long-travel stage', 'A micrometer drive for small moves; the long stage for path differences up to 20 cm.');
    S.addApparatus('srcs', srcs[1].g, 'Sources', 'The He-Ne laser, the LED and the sodium lamp; one at a time at the input of the interferometer.');
    appView(-0.45);
    mainBox('FRINGE COUNTER / SCOPE', 'fringe count  ·  visibility', 'SET');
  }
  function kitPhotons(kind) {
    C.laser(-0.85, 0.1, 'PUMP 405 nm', 0x3a2c4a);
    var bbo = C.box(-0.68, 0.03, 0.05, 0.03, '', 0x1c1f24); add(bbo, bx(0.012, 0.012, 0.004, new T.MeshPhysicalMaterial({ color: 0xfff8e0, transmission: 0.9, transparent: true, roughness: 0.05 })), 0, 0.07, 0);
    beam([[-0.8, Y, ZB], [-0.68, Y, ZB]], 0x6040ff);
    if (kind === 'hom') {
      C.mirror(-0.52, Math.PI / 4, ZB - 0.07); C.mirror(-0.52, -Math.PI / 4, ZB + 0.07);
      var stg = C.stage(-0.34, 0.1, 'DELAY', ZB + 0.07); K.parts.stg = stg;
      C.bs(-0.16); C.det(-0.04, 'SPCM A', 0); C.det(-0.16, 'SPCM B', Math.PI / 2, ZB - 0.1);
      beam([[-0.68, Y, ZB], [-0.52, Y, ZB - 0.07], [-0.16, Y, ZB - 0.07], [-0.16, Y, ZB]], 0x9a1a1a); beam([[-0.68, Y, ZB], [-0.52, Y, ZB + 0.07], [-0.16, Y, ZB + 0.07], [-0.16, Y, ZB]], 0x9a1a1a);
      S.addApparatus('stage', stg.g, 'Delay stage in one photon arm', 'Changes one photon\'s path; zero delay is the bottom of the dip.');
    } else if (kind === 'chsh') {
      var A = C.plate(-0.45, 'ANALYSER A', ZB - 0.07), Bp = C.plate(-0.45, 'ANALYSER B', ZB + 0.07);
      C.det(-0.2, 'SPCM A', 0, ZB - 0.07); C.det(-0.2, 'SPCM B', 0, ZB + 0.07);
      beam([[-0.68, Y, ZB], [-0.21, Y, ZB - 0.07]], 0x9a1a1a); beam([[-0.68, Y, ZB], [-0.21, Y, ZB + 0.07]], 0x9a1a1a);
      K.parts.A = A; K.parts.B = Bp;
      S.addApparatus('ana', A.g, 'Polarisation analysers', 'A polariser on a graduated rotation mount in front of each detector.');
    } else {
      C.bs(-0.55); C.mirror(-0.55, Math.PI / 4, ZB + 0.12); C.mirror(-0.25, -Math.PI / 4, ZB); var pz = C.box(-0.22, 0.02, 0.03, 0.03, 'PZT', 0x5a4a20, ZB - 0.03);
      C.bs(-0.25, ZB + 0.12); var hw = C.plate(-0.4, 'lambda/2', ZB + 0.12); var pol = C.plate(-0.12, 'ERASER', ZB + 0.12); C.det(0.0, 'SPCM', 0, ZB + 0.12);
      K.parts.hw = hw; K.parts.pol = pol; hw.g.visible = false; pol.g.visible = false;
      beam([[-0.68, Y, ZB], [-0.25, Y, ZB], [-0.25, Y, ZB + 0.12]], 0xff3030); beam([[-0.55, Y, ZB], [-0.55, Y, ZB + 0.12], [0.0, Y, ZB + 0.12]], 0xff3030);
      S.addApparatus('mz', pz, 'Mach-Zehnder with a piezo mirror', 'The piezo changes one path by a fraction of a wavelength per volt.');
    }
    var cc = C.box(0.2, 0.16, 0.05, 0.1, 'COINCIDENCE COUNTER', 0x24303a, ZB + 0.12); void cc;
    appView(-0.35);
    mainBox('PHOTON COUNTER', 'singles  ·  coincidences  ·  gate', 'SET');
  }

  // ======================================================================== the plans (one per kernel)
  function xcol(xl, d, k) { return { label: xl, get: function (r) { return f(r.x / (k || 1), d); } }; }
  function ycol(yl, d, key) { return { label: yl, get: function (r) { return f(r[key || 'y'], d); } }; }
  var NO = { label: 'No.', get: function (r, i) { return i + 1; } };
  var STG_ = { label: 'Stage', get: function (r) { return r.s + 1; } };
  var PLAN = null;
  var TBMAP = { pl10_satabs: 'pl10_sat', pl10_oppump: 'pl10_pump', pl10_hdshift: 'pl10_ryd', pl10_diodelaser: 'pl10_diode', pl10_freqlock: 'pl10_lock',
    pl10_shg: 'pl10_shgpm', pl10_zscan: 'pl10_nl', pl10_tcspc: 'pl10_life', pl10_pumpprobe: 'pl10_relax', pl10_mot: 'pl10_motq', pl10_bec: 'pl10_tc',
    pl10_michmetro: 'pl10_mich', pl10_hom: 'pl10_homv', pl10_chsh: 'pl10_bell', pl10_eraser: 'pl10_erase' };
  var TBNAME = (S.lab.check && S.lab.check.textbook) || TBMAP[KNAME] || '';
  function truthVal() { var tb = HK.TEXTBOOK[TBNAME]; return tb ? tb(p) : null; }
  function swap(list, i) {      // bring source i to the slot, everything else to its store
    var c = Promise.resolve();
    list.forEach(function (o, j) { if (j !== i) c = c.then(function () { return moveObj(o.g || o, K.parts.store[j]); }); });
    return c.then(function () { return moveObj(list[i].g || list[i], K.parts.slot); });
  }

  if (KNAME === 'pl10_satabs') {
    kitSatAbs();
    var rg = function (s) { var L = KN.lines(p, s), a = 0, b = 0; L.forEach(function (l) { a = Math.min(a, l[0]); b = Math.max(b, l[0]); }); return [a - 40, b + 40]; };
    PLAN = { stages: [
      { title: '87Rb F = 2', h2: 'The 87Rb F = 2 group', text: 'Scan the 87Rb F = 2 -> F\' lines. Put the cursor on each of the six peaks (three transitions, three crossovers) and press PEAK.', label: 'Cursor', unit: 'MHz', min: -520, max: 60, step: 1, digits: 0, minRows: 6 },
      { title: '85Rb F = 3', h2: 'The 85Rb F = 3 group', text: 'Tune the laser to the 85Rb F = 3 -> F\' lines and read their six peaks the same way.', label: 'Cursor', unit: 'MHz', min: -260, max: 60, step: 1, digits: 0, minRows: 6,
        prep: { label: 'Tune to the 85Rb group', fn: function () { return turn(K.main, 0, 1, 0.6); } } },
      { title: 'Dip width', h2: 'Dip width against pump power', text: 'Back on the 87Rb F = 2 -> F\'= 3 dip, set the pump with its half-wave plate and read the dip width at six saturation parameters I/Isat.', label: 'Pump saturation I/Isat', unit: '', min: 0.1, max: 5, step: 0.05, digits: 2, minRows: 6 }],
      ctl: function (v, s) { if (s < 2) return turn(K.main, s === 0 ? -520 : -260, 60, v); return rotTo(K.parts.hwp.ring, 'x', Math.asin(Math.sqrt(Math.min(1, v / 5))) / 2); },
      trace: function (s) { if (s === 2) return null; var r = rg(s), out = [], i; for (i = 0; i <= 260; i++) { var v = r[0] + (r[1] - r[0]) * i / 260; out.push([v, KN.sig(p, s, v, p.s0)]); } return out; },
      cols: [NO, STG_, { label: 'Setting', get: function (r) { return r.s < 2 ? f(r.x, 0) + ' MHz' : f(r.x, 2); } }, { label: 'Centre / width (MHz)', get: function (r) { return f(r.y, 2); } }, ycol('Height (mV)', 3, 'h')],
      res: Q === 2 ? { label: 'Natural line width of the D2 line', unit: 'MHz', k: 1, digits: 2 } : { label: Q === 1 ? '85Rb F\'4 - F\'3 splitting' : '87Rb F\'3 - F\'2 splitting', unit: 'MHz', k: 1, digits: 2 },
      note: function (rows) {
        var c0 = rows.filter(function (r) { return r.s === 0; }).map(function (r) { return r.y; }).sort(function (a, b) { return a - b; });
        var c1 = rows.filter(function (r) { return r.s === 1; }).map(function (r) { return r.y; }).sort(function (a, b) { return a - b; });
        var t = '';
        if (c0.length >= 6) t += '87Rb: F\'3-F\'2 ' + f(c0[5] - c0[2], 2) + ' MHz, F\'2-F\'1 ' + f(c0[2] - c0[0], 2) + ' MHz; crossover (3,2) ' + f(c0[4] - (c0[5] + c0[2]) / 2, 2) + ' MHz from the midpoint. ';
        if (c1.length >= 6) t += '85Rb: F\'4-F\'3 ' + f(c1[5] - c1[2], 2) + ' MHz, F\'3-F\'2 ' + f(c1[2] - c1[0], 2) + ' MHz. ';
        var w = rows.filter(function (r) { return r.s === 2; }).map(function (r) { return [Math.sqrt(1 + r.x), r.y]; });
        if (w.length > 2) { var ft = S.fit.linear(w); t += 'Width = ' + f(ft.m, 2) + ' sqrt(1 + I/Isat) + ' + f(ft.c !== undefined ? ft.c : ft.b, 2) + ' MHz (natural width + laser width). '; }
        return t + 'Steck: 266.650, 156.947, 120.640, 63.401 and 6.0666 MHz.';
      },
      graph: { x: function (r) { return r.s === 2 ? Math.sqrt(1 + r.x) : NaN; }, y: function (r) { return r.s === 2 ? r.y : NaN; }, xlabel: 'sqrt(1 + I/Isat)', ylabel: 'dip width (MHz)' },
      tol: 0.01 };
  } else if (KNAME === 'pl10_oppump') {
    kitOptPump();
    PLAN = { stages: [
      { title: 'Field forward', h2: 'Resonances with the coil field along the Earth\'s field', text: 'At each radio frequency, sweep the coil current and note the current of the 87Rb and the 85Rb dips.', label: 'RF frequency', unit: 'kHz', min: 100, max: 2000, step: 10, digits: 0, minRows: 5 },
      { title: 'Field reversed', h2: 'Resonances with the coil current reversed', text: 'Reverse the coil current with the switch and repeat at the same frequencies.', label: 'RF frequency', unit: 'kHz', min: 100, max: 2000, step: 10, digits: 0, minRows: 5,
        prep: { label: 'Reverse the coil current', fn: function () { return S.hand.tap(K.main.btn, 'front'); } } },
      { title: 'Pumping time', h2: 'Transmission after the light is unblocked', text: 'Unblock the pumping light and read the photodiode at times from 0 to 24 ms, and once long after (80 ms).', label: 'Time after unblocking', unit: 'ms', min: 0, max: 100, step: 1, digits: 0, minRows: 8 }],
      ctl: function (v, s) { return turn(K.main, s < 2 ? 100 : 0, s < 2 ? 2000 : 100, v); },
      cols: [NO, STG_, { label: 'f (kHz) / t (ms)', get: function (r) { return f(r.x, 0); } }, { label: '87Rb I (mA) / signal', get: function (r) { return r.s < 2 ? f(r.y, 2) : f(r.y, 4); } }, { label: '85Rb I (mA)', get: function (r) { return r.s < 2 ? f(r.y2, 2) : '-'; } }],
      res: [{ label: 'gF of 87Rb', unit: '', k: 1, digits: 4 }, { label: 'Nuclear spin of 85Rb', unit: '', k: 1, digits: 3 }, { label: 'Earth\'s horizontal field', unit: 'uT', k: 1, digits: 2 }, { label: 'Pumping time', unit: 'ms', k: 1, digits: 2 }][Q],
      note: function (rows) { var pp = rows.filter(function (r) { return r.s === 0; }).map(function (r) { return [r.x, r.y2]; }); if (pp.length < 2) return '';
        var ft = S.fit.linear(pp), k = KN.k(p), g = 6.62607015e-34 * 1e6 / (9.2740100783e-24 * k * ft.m); return 'Forward field: gF(85Rb) about ' + f(g, 4) + '. Low-field Breit-Rabi limit: gF = gJ/(2I + 1).'; },
      graph: { x: function (r) { return r.s < 2 ? r.x : NaN; }, y: function (r) { return r.s < 2 ? r.y : NaN; }, xlabel: 'RF frequency (kHz)', ylabel: '87Rb resonance current (mA)' },
      tol: 0.01 };
  } else if (KNAME === 'pl10_hdshift') {
    kitHD();
    var HEN = ['He 447.15', 'He 501.57', 'He 587.56', 'He 667.82', 'He 706.52'];
    K.parts.lamps.forEach(function (l, j) { if (j) l.g.position.copy(K.parts.store[j]); });
    PLAN = { stages: [
      { title: 'Helium calibration', h2: 'Calibrate the counter with helium', text: 'With the helium lamp at the slit, scan each of the five lines and read the counter at its centre.', label: 'Helium line', unit: '', min: 0, max: 4, step: 1, digits: 0, minRows: 5, show: function (v) { return HEN[Math.round(v)] + ' nm'; } },
      { title: 'Hydrogen', h2: 'Balmer lines of hydrogen', text: 'Put the hydrogen lamp at the slit and read H-alpha to H-delta.', label: 'Upper level n', unit: '', min: 3, max: 6, step: 1, digits: 0, minRows: 4,
        prep: { label: 'Put the hydrogen lamp at the slit', fn: function () { return swap(K.parts.lamps, 1); } } },
      { title: 'Deuterium', h2: 'Balmer lines of deuterium', text: 'Put the deuterium lamp at the slit and read the same four lines.', label: 'Upper level n', unit: '', min: 3, max: 6, step: 1, digits: 0, minRows: 4,
        prep: { label: 'Put the deuterium lamp at the slit', fn: function () { return swap(K.parts.lamps, 2); } } }],
      ctl: function (v, s) { return rotTo(K.parts.drum, 'z', (s * 7 + v) * 0.8); },
      cols: [NO, { label: 'Lamp', get: function (r) { return ['He', 'H', 'D'][r.s]; } }, { label: 'Line', get: function (r) { return r.s === 0 ? HEN[Math.round(r.x)] : 'n = ' + r.x; } }, ycol('Counter (nm)', 4)],
      res: Q === 1 ? { label: 'Deuteron / proton mass ratio', unit: '', k: 1, digits: 4 } : { label: 'Rydberg constant for hydrogen', unit: 'x 10^7 1/m', k: 1e-7, digits: 5 },
      note: function (rows) { var h = rows.filter(function (r) { return r.s === 1 && r.x === 3; }), d = rows.filter(function (r) { return r.s === 2 && r.x === 3; });
        return (h.length && d.length ? 'H-alpha minus D-alpha on the counter: ' + f(h[0].y - d[0].y, 4) + ' nm. ' : '') + 'Air to vacuum with n_air = 1.000277; CODATA R_inf = 10973731.568 1/m.'; },
      graph: { x: function (r) { return r.s ? 0.25 - 1 / (r.x * r.x) : NaN; }, y: function (r) { return r.s ? 1e3 / r.y : NaN; }, xlabel: '1/4 - 1/n^2', ylabel: '1/reading (1/um)' },
      tol: 0.02 };
  } else if (KNAME === 'pl10_diodelaser') {
    kitDiode();
    PLAN = { stages: [
      { title: 'L-I curve', h2: 'Light out against drive current (25 C)', text: 'Raise the current in steps from zero and read the power meter.', label: 'Drive current', unit: 'mA', min: 0, max: p.Imax, step: 0.5, digits: 1, minRows: 12 },
      { title: 'Current tuning', h2: 'Wavelength against current', text: 'Read the wavemeter at currents 20 mA either side of ' + p.Iop + ' mA.', label: 'Drive current', unit: 'mA', min: 0, max: p.Imax, step: 0.5, digits: 1, minRows: 5 },
      { title: 'Temperature tuning', h2: 'Wavelength against case temperature', text: 'Hold ' + p.Iop + ' mA and step the case temperature from 15 C to 35 C; let it settle before each reading.', label: 'Case temperature', unit: 'C', min: 10, max: 40, step: 0.5, digits: 1, minRows: 5 }],
      ctl: function (v, s) { return s < 2 ? turn(K.main, 0, p.Imax, v) : turn(K.parts.tec, 10, 40, v); },
      cols: [NO, STG_, { label: 'I (mA) / T (C)', get: function (r) { return f(r.x, 1); } }, { label: 'P (mW) / lambda (nm)', get: function (r) { return r.s === 0 ? f(r.y, 2) : f(r.y, 4); } }],
      res: [{ label: 'Threshold current', unit: 'mA', k: 1, digits: 2 }, { label: 'Slope efficiency', unit: 'W/A', k: 1, digits: 3 }, { label: 'Current tuning', unit: 'pm/mA', k: 1000, digits: 2 }, { label: 'Temperature tuning', unit: 'nm/K', k: 1, digits: 3 }][Q],
      note: function () { return 'Linear fit above the knee; the rate-equation knee rounds the curve just above threshold.'; },
      graph: { x: function (r) { return r.s === (Q < 2 ? 0 : Q - 1) ? r.x : NaN; }, y: function (r) { return r.s === (Q < 2 ? 0 : Q - 1) ? r.y : NaN; }, xlabel: Q === 3 ? 'temperature (C)' : 'current (mA)', ylabel: Q < 2 ? 'power (mW)' : 'wavelength (nm)' },
      tol: 0.01 };
  } else if (KNAME === 'pl10_freqlock') {
    kitLock();
    PLAN = { stages: [
      { title: 'Discriminator', h2: 'Error signal round the lock point', text: 'Scan the laser slowly and read the error signal at five detunings from the lock point.', label: 'Detuning from the lock point', unit: 'MHz', min: -1, max: 1, step: 0.05, digits: 2, minRows: 5 },
      { title: 'Lock bandwidth', h2: 'Suppression of an injected disturbance', text: 'Close the loop. Modulate the current at each frequency and read how much of the modulation is left.', label: 'Disturbance frequency', unit: 'Hz', min: 100, max: 1000000, step: 100, digits: 0, minRows: 6,
        prep: { label: 'Close the loop', fn: function () { return turn(K.aux[0], 0, 1, 0.7); } } },
      { title: 'Residual noise', h2: 'Out-of-loop frequency noise', text: 'Beat against the independent reference laser and read the rms frequency noise in 1, 10 and 100 kHz bands.', label: 'Measurement band', unit: 'Hz', min: 100, max: 1000000, step: 100, digits: 0, minRows: 3 }],
      ctl: function (v, s) { return turn(K.main, s === 0 ? -1 : 0, s === 0 ? 1 : 6, s === 0 ? v : Math.log(v) / Math.LN10); },
      cols: [NO, STG_, { label: 'Setting', get: function (r) { return r.s === 0 ? f(r.x, 2) + ' MHz' : f(r.x, 0) + ' Hz'; } }, { label: 'Error V / suppression / rms kHz', get: function (r) { return f(r.y, r.s === 2 ? 2 : 4); } }],
      res: Q === 1 ? { label: 'Residual rms frequency noise in 100 kHz', unit: 'kHz', k: 1, digits: 1 } : { label: 'Lock bandwidth (unity-gain frequency)', unit: 'kHz', k: 0.001, digits: 2 },
      note: function (rows) { var d = rows.filter(function (r) { return r.s === 0; }).map(function (r) { return [r.x, r.y]; }); if (d.length < 2) return '';
        return 'Discriminator slope ' + f(Math.abs(S.fit.linear(d).m), 4) + ' V/MHz (' + (p.m < 0.5 ? 'side of fringe' : 'dither / lock-in') + ').'; },
      graph: { x: function (r) { return r.s === 1 ? 1 / (r.x * r.x) : NaN; }, y: function (r) { return r.s === 1 ? 1 / (r.y * r.y) : NaN; }, xlabel: '1/f^2 (1/Hz^2)', ylabel: '1/S^2' },
      tol: 0.01 };
  } else if (KNAME === 'pl10_shg') {
    kitSHG();
    var c0 = KN.ext_of(p, KN.theta_pm(p));
    PLAN = { stages: [
      { title: 'Power law', h2: 'Green power against infrared power', text: 'With the crystal at the peak, turn the half-wave plate to set the infrared power and read the green power.', label: 'Infrared power', unit: 'W', min: 0.1, max: 5, step: 0.1, digits: 1, minRows: 5 },
      { title: 'Phase matching', h2: 'Tilt the crystal through phase matching', text: 'At ' + p.Pf + ' W, tilt the crystal in ' + f(p.span / 25, 2) + ' degree steps through the green peak.', label: 'External tilt', unit: 'deg', min: -5, max: 5, step: 0.01, digits: 2, minRows: 20 }],
      ctl: function (v, s) { if (s === 0) return rotTo(K.parts.hwp.ring, 'x', Math.asin(Math.sqrt(Math.min(1, v / 5))) / 2); return rotTo(K.parts.rs.top, 'y', (v - c0) * DEG * 6); },
      cols: [NO, STG_, { label: 'P (W) / tilt (deg)', get: function (r) { return f(r.x, 2); } }, ycol('Green (mW)', 4)],
      res: Q === 0 ? { label: 'Exponent of P2 against P', unit: '', k: 1, digits: 3 } : { label: 'Phase-matching angle (internal)', unit: 'deg', k: 1, digits: 3 },
      note: function () { return 'Internal angle = cut angle ' + f(p.thc, 2) + ' deg + asin(sin(tilt)/n_o). Sellmeier theory gives ' + f(KN.theta_pm(p), 3) + ' deg.'; },
      graph: { x: function (r) { return r.s === (Q === 0 ? 0 : 1) ? (Q === 0 ? Math.log(r.x) : r.x) : NaN; }, y: function (r) { return r.s === (Q === 0 ? 0 : 1) ? (Q === 0 ? Math.log(r.y) : r.y) : NaN; }, xlabel: Q === 0 ? 'ln P' : 'tilt (deg)', ylabel: Q === 0 ? 'ln P2' : 'green power (mW)' },
      tol: 0.01 };
  } else if (KNAME === 'pl10_zscan') {
    kitZScan();
    PLAN = { stages: [
      { title: 'Open aperture', h2: 'Open-aperture scan', text: 'Move the sample through the focus and read the open detector at each position.', label: 'Sample position z', unit: 'mm', min: -20, max: 20, step: 0.1, digits: 1, minRows: 20 },
      { title: 'Closed aperture', h2: 'Closed and open together', text: 'Put the aperture in front of the second detector and repeat, reading both detectors.', label: 'Sample position z', unit: 'mm', min: -20, max: 20, step: 0.1, digits: 1, minRows: 20,
        prep: { label: 'Close the far-field aperture', fn: function () { return S.hand.tap(K.main.btn, 'front'); } } }],
      ctl: function (v) { return slideTo(K.parts.stg, v * 0.004, v * 0.05); },
      cols: [NO, STG_, xcol('z (mm)', 1), ycol('T (closed or open)', 4), ycol('T open', 4, 'y2')],
      res: Q === 1 ? { label: 'Two-photon absorption coefficient', unit: 'cm/GW', k: 1e11, digits: 3 } : { label: 'Nonlinear refractive index n2', unit: 'x 1e-18 m^2/W', k: 1e18, digits: 3 },
      note: function (rows) { var c = rows.filter(function (r) { return r.s === 1; }); if (!c.length) return ''; var hi = -1e9, lo = 1e9; c.forEach(function (r) { var v = r.y / r.y2; hi = Math.max(hi, v); lo = Math.min(lo, v); });
        return 'Closed / open peak-valley ' + f(hi - lo, 4) + '; z0 = ' + f(KN.z0(p), 2) + ' mm. Sheik-Bahae 1990 formulas, small-aperture limit.'; },
      graph: { x: function (r) { return r.s === (Q === 1 ? 0 : 1) ? r.x : NaN; }, y: function (r) { return r.s === (Q === 1 ? 0 : 1) ? (r.s === 1 ? r.y / r.y2 : r.y) : NaN; }, xlabel: 'z (mm)', ylabel: Q === 1 ? 'T open' : 'T closed / T open' },
      tol: 0.01 };
  } else if (KNAME === 'pl10_tcspc') {
    kitTCSPC();
    var U = p.ms > 0.5 ? 'ms' : 'ns';
    PLAN = { stages: [
      { title: 'Decay histogram', h2: 'Read the histogram', text: 'The histogram has filled (peak about ' + f(p.Np, 0) + ' counts per bin). Move the bin cursor across it and read the counts, starting before the pulse.', label: 'Bin start', unit: U, min: 0, max: p.span, step: p.span / 600, digits: 2, minRows: 30, count: true }],
      ctl: function (v) { return turn(K.main, 0, p.span, v); },
      trace: function () { var out = [], i; for (i = 0; i <= 200; i++) { var t = p.span * i / 200; out.push([t, Math.log(Math.max(1, p.Np * KN.shape(p, t) + p.bg)) / Math.LN10]); } return out; },
      ylog: true, ptsWithTrace: true,
      cols: [NO, xcol('t (' + U + ')', 2), ycol('Counts', 0)],
      res: { label: Q === 1 ? 'Fast lifetime component' : Q === 2 ? 'Slow lifetime component' : 'Fluorescence lifetime', unit: U, k: 1, digits: 3 },
      note: function () { return (Q === 0 ? 'Weighted tail fit after the instrument response.' : 'Two-exponential Poisson-weighted least squares.') + ' Background from the bins before the pulse. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.y > 0 ? Math.log(r.y) / Math.LN10 : NaN; }, xlabel: 't (' + U + ')', ylabel: 'log10 counts' },
      tol: 0.02 };
  } else if (KNAME === 'pl10_pumpprobe') {
    kitPumpProbe();
    PLAN = { stages: [
      { title: 'Delay scan', h2: 'dT/T against delay', text: 'Probe at ' + f(p.lb, 0) + ' nm. Step the delay stage from just before zero delay and read the lock-in.', label: 'Stage position', unit: 'mm', min: 0, max: 50, step: 0.0001, digits: 4, minRows: 20 },
      { title: 'Transient spectrum', h2: 'The bleach spectrum at ' + p.td + ' ps', text: 'Set the delay to ' + p.td + ' ps and scan the probe wavelength across the band.', label: 'Probe wavelength', unit: 'nm', min: 300, max: 1200, step: 0.1, digits: 1, minRows: 20,
        prep: { label: 'Set the delay to ' + p.td + ' ps', fn: function () { return slideTo(K.parts.stg, (p.xz + p.td * 1e-12 * 299792458 / 2 * 1e3 - 25) * 0.002); } } }],
      ctl: function (v, s) { return s === 0 ? slideTo(K.parts.stg, (v - 25) * 0.002, (v - 25) * 2) : turn(K.main, 300, 1200, v); },
      cols: [NO, STG_, { label: 'x (mm) / lambda (nm)', get: function (r) { return r.s === 0 ? f(r.x, 4) : f(r.x, 1); } }, ycol('dT/T x 1000', 3)],
      res: Q === 1 ? { label: 'Bleach peak wavelength', unit: 'nm', k: 1, digits: 1 } : { label: 'Relaxation time', unit: 'ps', k: 1, digits: 3 },
      note: function () { return 'Delay = 2 x / c: 6.671 ps per mm. Tail fitted after the cross-correlation.'; },
      graph: { x: function (r) { return r.s === Q ? r.x : NaN; }, y: function (r) { return r.s === Q ? r.y : NaN; }, xlabel: Q === 1 ? 'probe wavelength (nm)' : 'stage position (mm)', ylabel: 'dT/T x 1000' },
      tol: 0.01 };
  } else if (KNAME === 'pl10_mot') {
    kitMOT(false);
    PLAN = { stages: [
      { title: 'Atom number', h2: 'Fluorescence of the loaded trap', text: 'Read the fluorescence photodiode three times with the trap full.', label: 'Reading', unit: '', min: 1, max: 3, step: 1, digits: 0, minRows: 3 },
      { title: 'Time of flight', h2: 'Cloud size after release', text: 'Switch the trap off for each flight time and image the cloud; read its rms size.', label: 'Flight time', unit: 'ms', min: 0, max: 20, step: 0.5, digits: 1, minRows: 5 },
      { title: 'Loading', h2: 'The loading curve', text: 'Empty the trap and switch the field on again; read the fluorescence at each time.', label: 'Loading time', unit: 's', min: 0, max: 20, step: 0.1, digits: 1, minRows: 6 }],
      ctl: function (v, s) { return turn(K.main, 0, [3, 20, 20][s], v); },
      cols: [NO, STG_, { label: 'Setting', get: function (r) { return f(r.x, 1); } }, { label: 'V or sigma (mm)', get: function (r) { return f(r.y, r.s === 1 ? 3 : 4); } }],
      res: [{ label: 'Atom number', unit: 'x 10^8', k: 1e-8, digits: 3 }, { label: 'Cloud temperature', unit: 'uK', k: 1, digits: 1 }, { label: 'Capture velocity', unit: 'm/s', k: 1, digits: 2 }][Q],
      note: function () { return 'Scattering rate ' + f(KN.scat(p) / 1e6, 3) + ' x 10^6 /s per atom. SIMULATED INSTRUMENT.'; },
      graph: { x: function (r) { return r.s === 1 ? Math.pow(r.x / 1000, 2) : NaN; }, y: function (r) { return r.s === 1 ? Math.pow(r.y, 2) : NaN; }, xlabel: 't^2 (s^2)', ylabel: 'sigma^2 (mm^2)' },
      tol: 0.01 };
  } else if (KNAME === 'pl10_bec') {
    kitMOT(true);
    PLAN = { stages: [
      { title: 'Evaporation series', h2: 'Evaporate, release, image, fit', text: 'For each final RF frequency, evaporate, release the cloud for the time of flight, image it and fit the bimodal profile.', label: 'Final RF frequency', unit: 'kHz', min: 1, max: 100, step: 0.5, digits: 1, minRows: 8 }],
      ctl: function (v) { return turn(K.main, 0, 100, v); },
      trace: function () { var r = st.last, out = [], i, f0 = r ? r.f : 0, T0 = r ? r.y : 100; for (i = -60; i <= 60; i++) { var u = i / 60, th = (1 - f0) * Math.exp(-u * u * 4), tf = Math.max(0, 1 - u * u * 9) * f0 * 4; out.push([u, th + tf]); } return out; },
      cols: [NO, xcol('RF (kHz)', 1), ycol('T (nK)', 1), ycol('N', 0, 'N'), ycol('N0/N', 3, 'f')],
      res: { label: 'Critical temperature for 10^6 atoms', unit: 'nK', k: 1, digits: 1 },
      note: function () { return 'Theory 0.94 hbar wbar N^(1/3)/kB = ' + f(KN.tc(p, p.Nref), 1) + ' nK (wbar/2pi = ' + f(KN.wbar(p) / 2 / Math.PI, 1) + ' Hz). SIMULATED INSTRUMENT.'; },
      graph: { x: function (r) { return r.y; }, y: function (r) { return r.f; }, xlabel: 'T (nK)', ylabel: 'condensate fraction' },
      tol: 0.01 };
  } else if (KNAME === 'pl10_michmetro') {
    kitMich();
    PLAN = { stages: [
      { title: 'He-Ne fringe count', h2: 'Displacement by fringe counting', text: 'With the He-Ne laser in, zero the counter and turn the micrometer; read the whole fringes counted.', label: 'Micrometer setting', unit: 'um', min: 0, max: 200, step: 1, digits: 0, minRows: 5,
        prep: { label: 'Put the He-Ne laser in', fn: function () { return swap(K.parts.srcs, 0); } } },
      { title: 'LED coherence', h2: 'White-light coherence scan', text: 'Put the LED in, find zero path difference and read the fringe visibility as you step the mirror.', label: 'Path difference', unit: 'um', min: 0, max: 100, step: 0.01, digits: 2, minRows: 10,
        prep: { label: 'Put the LED in', fn: function () { return swap(K.parts.srcs, 1); } } },
      { title: 'Sodium beats', h2: 'Fading of the sodium beats', text: 'Put the sodium lamp in and read the visibility at every 50th beat maximum.', label: 'Path difference', unit: 'um', min: 0, max: 200000, step: 0.1, digits: 1, minRows: 5,
        prep: { label: 'Put the sodium lamp in', fn: function () { return swap(K.parts.srcs, 2); } } }],
      ctl: function (v, s) { return s === 0 ? slideTo(K.parts.stg, K.parts.stg.car.position.x, (v - (st.x || 0)) * 0.05) : slideTo(K.parts.stg, v * 1e-6 / 2 - 0.1, v * 1e-4); },
      cols: [NO, STG_, { label: 'Setting (um)', get: function (r) { return f(r.x, r.s === 1 ? 2 : 1); } }, { label: 'Count or visibility', get: function (r) { return r.s === 0 ? f(r.y, 0) : f(r.y, 3); } }],
      res: [{ label: 'Displacement for 100 um set', unit: 'um', k: 1, digits: 2 }, { label: 'LED coherence length', unit: 'um', k: 1, digits: 2 }, { label: 'Sodium line width', unit: 'GHz', k: 1, digits: 3 }, { label: 'LED line width', unit: 'nm', k: 1, digits: 2 }][Q],
      note: function () { return 'd = N lambda/2 with lambda = ' + p.lh + ' nm; beat period of the D lines ' + f(KN.beat(p), 1) + ' um.'; },
      graph: { x: function (r) { return r.s === (Q === 0 ? 0 : Q === 2 ? 2 : 1) ? r.x : NaN; }, y: function (r) { return r.s === (Q === 0 ? 0 : Q === 2 ? 2 : 1) ? r.y : NaN; }, xlabel: 'setting (um)', ylabel: Q === 0 ? 'fringes' : 'visibility' },
      tol: 0.01 };
  } else if (KNAME === 'pl10_hom') {
    kitPhotons('hom');
    PLAN = { stages: [
      { title: 'Delay scan', h2: 'Coincidences against delay', text: 'Step the delay stage across the dip and count coincidences for ' + p.t + ' s at each step.', label: 'Delay', unit: 'um', min: -500, max: 500, step: 0.5, digits: 1, minRows: 15, count: true }],
      ctl: function (v) { return slideTo(K.parts.stg, v * 1e-4, v * 0.02); },
      cols: [NO, xcol('Delay (um)', 1), ycol('Coincidences', 0), { label: 'Rate (/s)', get: function (r) { return f(r.y / r.T, 1); } }],
      res: Q === 1 ? { label: 'Photon coherence length (dip FWHM)', unit: 'um', k: 1, digits: 1 } : { label: 'HOM dip visibility', unit: '', k: 1, digits: 3 },
      note: function () { return 'Accidentals ' + p.acc + ' /s taken off. Filters ' + p.dl + ' nm FWHM at ' + p.lam + ' nm. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.y / r.T; }, xlabel: 'delay (um)', ylabel: 'coincidences (/s)' },
      tol: 0.03 };
  } else if (KNAME === 'pl10_chsh') {
    kitPhotons('chsh');
    var lab0 = function (s, x) { var ab = KN.ab(s, x); return 'a ' + f(ab[0], 1) + ', b ' + f(ab[1], 1); };
    PLAN = { stages: [
      { title: 'Correlation curves', h2: 'Polarisation correlation', text: 'With A at 0 degrees turn B in 22.5 degree steps (settings 0-8), then with A at 45 degrees (settings 9-17); count ' + p.t + ' s at each.', label: 'Setting', unit: '', min: 0, max: 17, step: 1, digits: 0, minRows: 18, count: true, show: function (v) { return lab0(0, v); } },
      { title: 'CHSH settings', h2: 'The sixteen CHSH settings', text: 'Count at a in {0, 45, 90, 135} and b in {22.5, 67.5, 112.5, 157.5}.', label: 'Setting', unit: '', min: 0, max: 15, step: 1, digits: 0, minRows: 16, count: true, show: function (v) { return lab0(1, v); } }],
      ctl: function (v, s) { var ab = KN.ab(s, v); return rotTo(K.parts.A.ring, 'x', ab[0] * DEG).then(function () { return rotTo(K.parts.B.ring, 'x', ab[1] * DEG); }); },
      cols: [NO, STG_, { label: 'a, b (deg)', get: function (r) { return lab0(r.s, r.x); } }, ycol('Coincidences', 0)],
      res: Q === 1 ? { label: 'Polarisation correlation visibility', unit: '', k: 1, digits: 3 } : { label: 'CHSH S', unit: '', k: 1, digits: 3 },
      note: function () { return 'Local realism: |S| <= 2; quantum limit 2 sqrt2 = 2.828. Accidentals ' + p.acc + ' /s taken off. SIMULATED DATA.'; },
      graph: { x: function (r) { return r.s === 0 ? KN.ab(0, r.x)[1] + (r.x >= 9 ? 200 : 0) : NaN; }, y: function (r) { return r.s === 0 ? r.y / r.T : NaN; }, xlabel: 'b (deg; A = 45 offset by 200)', ylabel: 'coincidences (/s)' },
      tol: 0.02 };
  } else {
    kitPhotons('eraser');
    PLAN = { stages: [
      { title: 'Plain interferometer', h2: 'Single-photon fringes', text: 'Scan the piezo over two fringes, counting ' + p.t + ' s at each step.', label: 'Piezo voltage', unit: 'V', min: 0, max: 10, step: 0.05, digits: 2, minRows: 12, count: true },
      { title: 'Which-path marked', h2: 'Mark the path', text: 'Put the half-wave plate in one arm (polarisation turned by ' + p.psi + ' degrees) and scan again.', label: 'Piezo voltage', unit: 'V', min: 0, max: 10, step: 0.05, digits: 2, minRows: 12, count: true,
        prep: { label: 'Insert the half-wave plate', fn: function () { K.parts.hw.g.visible = true; return S.hand.tap(K.parts.hw.ring.children[0], 'side'); } } },
      { title: 'Eraser', h2: 'Erase the mark', text: 'Put the polariser at ' + f(p.psi / 2, 1) + ' degrees after the output beam splitter and scan again.', label: 'Piezo voltage', unit: 'V', min: 0, max: 10, step: 0.05, digits: 2, minRows: 12, count: true,
        prep: { label: 'Insert the eraser polariser', fn: function () { K.parts.pol.g.visible = true; return rotTo(K.parts.pol.ring, 'x', p.psi / 2 * DEG); } } }],
      ctl: function (v) { return turn(K.main, 0, 10, v); },
      cols: [NO, { label: 'Scan', get: function (r) { return ['plain', 'marked', 'erased'][r.s]; } }, xcol('Piezo (V)', 2), ycol('Counts', 0)],
      res: Q === 1 ? { label: 'Visibility with which-path information', unit: '', k: 1, digits: 3 } : { label: 'Visibility with the eraser', unit: '', k: 1, digits: 3 },
      note: function () { return (/herald/i.test(V_.sample || '') ? 'Counts are coincidences with the herald. ' : 'Mean photon number per coherence time far below one. ') + 'SIMULATED DATA.'; },
      graph: { x: function (r) { return r.x + 10 * r.s; }, y: function (r) { return r.y; }, xlabel: 'piezo voltage (V; scans offset by 10 V)', ylabel: 'counts' },
      tol: 0.02 };
  }

  var STG = PLAN.stages;
  function curStage() { return STG[st.s]; }
  function powerOn() {
    if (busy()) return Promise.resolve();
    if (st.on) return Promise.resolve();
    return S.hand.tap(K.main.btn, 'front').then(function () {
      st.on = true; K.main.power(true); K.aux.forEach(function (b) { b.power(true); });
      beams.forEach(function (b) { b.visible = true; });
      S.say('Switched on. Let the laser and the electronics warm up before the first reading.'); S.click(820, 0.05); S.render(); });
  }
  function setX(v) {
    if (busy()) return Promise.resolve(false);
    var sg = curStage();
    if (!isFinite(v) || v < sg.min - 1e-9 || v > sg.max + 1e-9) { S.say(sg.label + ': from ' + sg.min + ' to ' + sg.max + (sg.unit ? ' ' + sg.unit : '') + ' only.'); return Promise.resolve(false); }
    return PLAN.ctl(v, st.s).then(function () { st.x = v; st.last = null; S.render(); return true; });
  }
  function take() {
    if (busy()) return Promise.resolve(false);
    if (!st.on) { S.say('Switch the instruments on first.'); return Promise.resolve(false); }
    var sg = curStage();
    if (sg.prep && !st.prep[st.s]) { S.say('First: ' + sg.prep.label.toLowerCase() + '.'); return Promise.resolve(false); }
    var r = KN.read(p, st.s, st.x, st.idx); st.lastIdx = st.idx; st.idx += 1;
    if (!sg.count) { st.last = r; S.say(sg.label + ' ' + shown(st.x, sg) + ': reading ' + f(r.y, 4) + '.'); S.render(); return Promise.resolve(true); }
    st.counting = true; st.last = null;
    return S.hand.tap(K.main.btn, 'front').then(function () { return S.tween(900, function (k) { st.shown = Math.round(r.y * k); }); })
      .then(function () { st.counting = false; st.last = r; st.shown = r.y; S.say('Counted ' + f(r.y, 0) + (r.T ? ' in ' + r.T + ' s.' : '.')); S.render(); return true; });
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
  function shown(x, sg) { return sg.show ? sg.show(x) : f(x, sg.digits) + (sg.unit ? ' ' + sg.unit : ''); }

  // ======================================================================== screen
  var trCache = {};
  function screen() {
    var sg = curStage() || STG[0];
    var pts = rowsOf(st.s).map(function (r) { return [r.x, PLAN.ylog ? (r.y > 0 ? Math.log(r.y) / Math.LN10 : 0) : r.y]; });
    var rd = !st.on ? 'OFF' : st.counting ? String(st.shown) : st.last ? f(st.last.y, 4) + (st.last.y2 !== undefined ? '   ' + f(st.last.y2, 4) : '') : '---';
    var key = st.s + '|' + (KNAME === 'pl10_bec' ? (st.last ? st.last.f : -1) : '');
    if (PLAN.trace && st.on && !(key in trCache)) trCache[key] = PLAN.trace(st.s);
    var tr = PLAN.trace && st.on ? trCache[key] : null;
    var sig = shown(st.x, sg) + '|' + rd + '|' + pts.length + '|' + st.on + '|' + key;
    K.main.draw(sig, function (x, w, h) {
      if (!st.on) { x.fillStyle = '#0b0f0d'; x.fillRect(0, 0, w, h); return; }
      screenText(x, w, h, [sg.label.slice(0, 28), shown(st.x, sg), rd], tr && !PLAN.ptsWithTrace ? [] : pts, { trace: tr, cursor: tr && KNAME === 'pl10_satabs' ? st.x : (tr && KNAME === 'pl10_tcspc' ? st.x : null) });
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
        var tg = { v: st.x };
        if (tg.v < sg.min || tg.v > sg.max || !isFinite(tg.v)) tg.v = sg.min;
        u.slider(sg.label, sg.min, sg.max, sg.step, function () { return tg.v; }, function (v) { tg.v = v; }, sg.show ? '' : sg.unit, sg.digits);
        u.row(u.button('Set', function () { setX(tg.v); }, false, S.hand.busy),
          u.button(sg.count ? 'START count' : 'Read', function () { take(); }, true, S.hand.busy),
          u.button('Record', function () { record(); }, false, S.hand.busy));
        u.live(function () { return shown(st.x, sg) + '  ·  ' + (st.counting ? 'counting ' + st.shown : st.last ? f(st.last.y, 4) + (st.last.y2 !== undefined ? ' / ' + f(st.last.y2, 4) : '') : 'no reading yet'); });
        u.h3('Observation table'); u.table();
        var last = i === STG.length - 1;
        u.next(last ? 'Next: the result' : 'Next: ' + STG[i + 1].title, rowsOf(i).length >= sg.minRows && (!last || S.result() !== null));
      },
      ok: function () { return rowsOf(i).length >= sg.minRows && (i < STG.length - 1 || S.result() !== null); },
      auto: function () {
        st.s = i;
        var list = KN.plan(p).filter(function (q) { return q[0] === i; }), c = prep(i);
        list.forEach(function (q) {
          c = c.then(function () { return setX(q[1]); }).then(function () { return take(); }).then(function () { record(); });
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
  var tt = 0;
  return {
    camera: { pos: [0.0, 0.95, 1.2], look: [-0.05, 0.08, -0.25] },
    views: Object.assign({ bench: [[0.0, 0.95, 1.2], [-0.05, 0.08, -0.25]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] }, K.views),
    theory: th0,
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + (S.lab.aim || '').slice(0, 110), V_.sample ? 'Sample: ' + V_.sample : 'Apparatus as drawn on the table.'], columns: PLAN.cols },
    graph: { x: PLAN.graph.x, y: PLAN.graph.y, xlabel: PLAN.graph.xlabel, ylabel: PLAN.graph.ylabel },
    result: result,
    tol: PLAN.tol,
    chips: ['What am I measuring?', 'Check my readings', 'What is the main source of error?'],
    viva: [],
    askState: function () { var sg = curStage() || STG[0]; return { experiment: S.lab.title, sample: V_.sample || '', switched_on: st.on, stage: sg.title, setting: sg.label + ' = ' + shown(st.x, sg), last_reading: st.last, readings_taken: S.rows.length }; },
    steps: steps,
    tick: function (TDT) {
      tt += (TDT || 0.016);
      screen();
      var sg = curStage() || STG[0];
      hudA.set(shown(st.x, sg));
      hudR.set(st.last ? f(st.last.y, 4) : '-');
      if (K.parts.vac && st.on) { K.parts.vac.cloud.material.opacity = 0.75; K.parts.vac.cloud.scale.setScalar(1 + 0.15 * Math.sin(tt * 3)); }
    },
  };
});
