/* Prayogshala studio module: COINCIDENCE BENCH (M.Sc. / PhD nuclear physics).
   Two scintillation detectors, their discriminators, a coincidence unit with a gate of 1 to 4 unit widths and a
   four-channel scaler-timer, with a live monitor. Two UNRELATED sources give only chance (accidental)
   coincidences, at 2 k tau R1 R2; a source that emits both quanta of one decay (the back-to-back 511 keV pair of
   Na-22, the 1173 / 1332 keV cascade of Co-60) adds a true rate that does not depend on the gate. The straight line of
   the coincidence rate against the gate setting gives the resolving time from its slope and the true coincidence
   rate from its intercept.
   Physics: the `ph3_coinc` kernel of packs/ph3_nuc.js. Every count is a Poisson number from the lab's own seed. */
HoolaStudio.define('ph3-coincidence', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.ph3_coinc, assign = HK.assign;
  var p = HK.paramsFor('ph3_coinc', S.lab.params);
  var V_ = S.lab.variant || {};
  var PAIR = p.Rt > 0, SLOW = p.tau > 2e-7;
  var SAMPLE = V_.sample || (PAIR ? 'Na-22 sealed source (back-to-back 511 keV pair)' : 'Cs-137 and Co-60 as two unrelated sources');
  var UNIT = p.tau >= 1e-6 ? 1e6 : 1e9, UNAME = p.tau >= 1e-6 ? 'µs' : 'ns';
  var st = { placed: false, k: 1, counting: false, n1: 0, n2: 0, nc: 0, elapsed: 0, idx: 0, last: null, recorded: true };
  // ---------------------------------------------------------------- shared bench helpers (this rig carries its own copy)
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function pad(n, w) { var s = String(n); while (s.length < w) s = '0' + s; return s; }
  var leadM = new T.MeshStandardMaterial({ color: 0x53565c, roughness: 0.72, metalness: 0.55 });
  function brick(g, x, y, z, w, h, d) { var b = S.rounded(w, d, h, 0.004, leadM); b.rotation.x = -Math.PI / 2; b.position.set(x, y + h / 2, z); g.add(b); return b; }
  function makeSource(color) {
    var g = new T.Group();
    var disc = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, 0.004, 24), new T.MeshStandardMaterial({ color: color || 0xb8322a, roughness: 0.4, metalness: 0.3 }));
    g.add(disc);
    var rim = S.mesh(new T.TorusGeometry(0.0085, 0.0012, 8, 24), M.chrome); rim.rotation.x = Math.PI / 2; g.add(rim);
    var tref = S.canvasTex(128, 128, function (x, w, h) {
      x.fillStyle = '#f2d02a'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b1b1b'; x.beginPath(); x.arc(w / 2, h / 2, 10, 0, Math.PI * 2); x.fill();
      for (var i = 0; i < 3; i++) { x.beginPath(); x.arc(w / 2, h / 2, 46, i * 2.094 - 0.45, i * 2.094 + 0.45); x.arc(w / 2, h / 2, 18, i * 2.094 + 0.45, i * 2.094 - 0.45, true); x.closePath(); x.fill(); } });
    var tm = new T.Mesh(new T.CircleGeometry(0.0082, 24), new T.MeshStandardMaterial({ map: tref, roughness: 0.6 }));
    tm.rotation.x = -Math.PI / 2; tm.position.y = 0.0021; g.add(tm);
    return g;
  }
  function makePot(x, z, text) {
    var pot = new T.Group(); S.scene.add(pot); pot.position.set(x, 0, z);
    var b = S.mesh(new T.CylinderGeometry(0.03, 0.032, 0.03, 28), leadM); b.position.y = 0.015; pot.add(b);
    var h = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.022, 24), new T.MeshStandardMaterial({ color: 0x17181b })); h.position.y = 0.021; pot.add(h);
    var lid = S.mesh(new T.CylinderGeometry(0.031, 0.031, 0.008, 28), leadM); lid.position.set(0.055, 0.004, 0.02); pot.add(lid);
    var lb = S.label(text || 'SEALED SOURCE STORE', { w: 0.06, ratio: 0.2, color: '#e8e8ea' }); lb.rotation.x = -Math.PI / 2; lb.position.set(0, 0.0012, 0.058); pot.add(lb);
    return pot;
  }
  function makeTongs(x, z) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0.004, z); g.rotation.y = 0.4;
    [-1, 1].forEach(function (sg) { var a = S.mesh(new T.BoxGeometry(0.17, 0.004, 0.005), M.chrome); a.position.set(0, 0, sg * 0.006); a.rotation.y = sg * 0.04; g.add(a); });
    var hg = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.016, 12), M.chrome); hg.rotation.x = Math.PI / 2; hg.position.set(0.06, 0, 0); g.add(hg);
    return g;
  }
  // a rack-mounted instrument: front panel drawn on a canvas, with helper to place parts on it (metres from its centre)
  function panel(W, H, D, drawFn, x, z, ry) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = ry || 0;
    var caseM = S.rounded(W, D, H, 0.012, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5, metalness: 0.12 }));
    caseM.rotation.x = -Math.PI / 2; caseM.position.y = H / 2 + 0.004; g.add(caseM);
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) { var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.004, 16), M.rubber); ft.position.set(f[0] * (W / 2 - 0.02), 0.002, f[1] * (D / 2 - 0.02)); g.add(ft); });
    var FZ = D / 2 + 0.0062, PW = W - 0.014, PH = H - 0.014;
    var tex = S.canvasTex(Math.min(2000, Math.round(W * 2800)), Math.round(Math.min(2000, Math.round(W * 2800)) * PH / PW), function (x, w, h) {
      var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; }, k = w / PW;
      x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(8, 8, w - 16, h - 16);
      drawFn(x, w, h, X, Y, k);
    });
    var fac = S.mesh(new T.BoxGeometry(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]);
    fac.position.set(0, 0.004 + H / 2, FZ - 0.002); g.add(fac);
    S.contact(W * 1.25, D * 1.35, x, z, 0.55);
    return { g: g, FZ: FZ, PW: PW, PH: PH, H: H, up: function (u, v, dz) { return new T.Vector3(u, 0.004 + H / 2 + v, FZ + (dz || 0)); } };
  }
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  function makeKnob(pn, u, v) {
    var k = new T.Group(); k.position.copy(pn.up(u, v)); pn.g.add(k);
    var sk = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.004, 36), M.bakelite); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; k.add(sk);
    var kb = S.mesh(new T.CylinderGeometry(0.0145, 0.016, 0.016, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; k.add(kb);
    var pt = S.mesh(new T.BoxGeometry(0.002, 0.016, 0.0012), M.white, false); pt.position.set(0, 0.009, 0.0215); k.add(pt);
    return k;
  }
  function makeButton(pn, u, v, mat) { var b = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 20), mat || M.green); b.rotation.x = Math.PI / 2; b.position.copy(pn.up(u, v, 0.004)); pn.g.add(b); return b; }
  function makeLcd(pn, cx, cy, wdt, hgt, digits) {
    var tex = S.liveTex(512, 190), last = '';
    var bez = S.mesh(new T.BoxGeometry(wdt + 0.006, hgt + 0.006, 0.003), M.grey); bez.position.copy(pn.up(cx, cy, 0.001)); pn.g.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(wdt, hgt), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); scr.position.copy(pn.up(cx, cy, 0.004)); pn.g.add(scr);
    var ghost = ''; while (ghost.length < digits) ghost += '8';
    var set = function (txt) {
      if (txt === last) return; last = txt;
      tex.draw(function (x) {
        var gr = x.createLinearGradient(0, 0, 0, 190); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); x.fillStyle = gr; x.fillRect(0, 0, 512, 190);
        x.font = '700 ' + Math.round(Math.min(110, 880 / (digits + 1))) + 'px "JetBrains Mono", monospace'; x.textAlign = 'right';
        x.fillStyle = 'rgba(0,0,0,.07)'; x.fillText(ghost, 480, 130); x.fillStyle = '#1b2116'; x.fillText(txt, 480, 130);
      });
    };
    set('0'); return set;
  }
  // a flat monitor on a stand showing a live plot
  function makeScreen(x, z, ry, W, H) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = ry || 0;
    var base = S.rounded(0.14, 0.1, 0.008, 0.004, M.iron); base.rotation.x = -Math.PI / 2; base.position.set(0, 0.004, 0); g.add(base);
    var neck = S.mesh(new T.CylinderGeometry(0.012, 0.016, 0.07, 20), M.iron); neck.position.set(0, 0.04, 0); g.add(neck);
    var head = new T.Group(); head.position.set(0, 0.075 + H / 2, 0.01); head.rotation.x = -0.12; g.add(head);
    var bz = S.rounded(W + 0.03, H + 0.03, 0.02, 0.008, new T.MeshStandardMaterial({ color: 0x1a1c20, roughness: 0.5, metalness: 0.3 })); head.add(bz);
    var tex = S.liveTex(1280, Math.round(1280 * H / W));
    var scr = new T.Mesh(new T.PlaneGeometry(W, H), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); scr.position.z = 0.0125; head.add(scr);
    S.contact(0.2, 0.16, x, z, 0.5);
    return { g: g, tex: tex, W: W, H: H };
  }
  // plot helpers for the monitor
  function plotFrame(x, w, h, box, xmin, xmax, ymin, ymax, xlabel, ylabel, xt, yt, fmtx, fmty) {
    var X = function (v) { return box.l + (v - xmin) / (xmax - xmin) * (box.r - box.l); }, Y = function (v) { return box.b - (v - ymin) / (ymax - ymin) * (box.b - box.t); };
    x.strokeStyle = 'rgba(160,230,190,.16)'; x.lineWidth = 1; x.fillStyle = '#9fe0b8'; x.font = Math.round(h * 0.034) + 'px "JetBrains Mono", monospace';
    var i, v;
    x.textAlign = 'right';
    for (i = 0; i <= yt; i++) { v = ymin + (ymax - ymin) * i / yt; x.beginPath(); x.moveTo(box.l, Y(v)); x.lineTo(box.r, Y(v)); x.stroke(); x.fillText(fmty ? fmty(v) : String(Math.round(v)), box.l - 6, Y(v) + 5); }
    x.textAlign = 'center';
    for (i = 0; i <= xt; i++) { v = xmin + (xmax - xmin) * i / xt; x.beginPath(); x.moveTo(X(v), box.t); x.lineTo(X(v), box.b); x.stroke(); x.fillText(fmtx ? fmtx(v) : String(Math.round(v)), X(v), box.b + h * 0.045); }
    x.fillStyle = '#c9f5dc'; x.fillText(xlabel, (box.l + box.r) / 2, box.ly || h - 8);
    x.save(); x.translate(box.lx || 18, (box.t + box.b) / 2); x.rotate(-Math.PI / 2); x.fillText(ylabel, 0, 0); x.restore();
    x.strokeStyle = 'rgba(160,230,190,.5)'; x.strokeRect(box.l, box.t, box.r - box.l, box.b - box.t);
    return { X: X, Y: Y };
  }

  // ================================================================ detectors, sources, lead
  var detG = [];
  function makeDet(x, dir, name) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0.07, -0.30); g.rotation.y = dir > 0 ? 0 : Math.PI;
    var wrap = S.mesh(new T.BoxGeometry(0.034, 0.1, 0.1), new T.MeshStandardMaterial({ color: 0x15171a, roughness: 0.8 })); g.add(wrap);
    var face = S.mesh(new T.BoxGeometry(0.002, 0.09, 0.09), new T.MeshStandardMaterial({ color: 0x9fc4e6, roughness: 0.2, transparent: true, opacity: 0.85 })); face.position.x = 0.0175; g.add(face);
    var guide = S.mesh(new T.CylinderGeometry(0.03, 0.042, 0.05, 28), new T.MeshStandardMaterial({ color: 0x15171a, roughness: 0.8 })); guide.rotation.z = Math.PI / 2; guide.position.x = -0.042; g.add(guide);
    var pmt = S.mesh(new T.CylinderGeometry(0.0425, 0.0425, 0.14, 36), new T.MeshStandardMaterial({ color: 0x2c3138, roughness: 0.5, metalness: 0.5 })); pmt.rotation.z = Math.PI / 2; pmt.position.x = -0.135; g.add(pmt);
    var base = S.mesh(new T.CylinderGeometry(0.045, 0.045, 0.05, 36), M.bakelite); base.rotation.z = Math.PI / 2; base.position.x = -0.23; g.add(base);
    var lb = S.label(name, { w: 0.06, ratio: 0.2, color: '#e8e8ea', bg: '#2b2f36' }); lb.position.set(-0.135, 0.0435, 0); lb.rotation.set(-Math.PI / 2, 0, 0); lb.rotation.z = 0; g.add(lb);
    var post = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.05, 16), M.chrome); post.position.set(-0.06, -0.037, 0); post.rotation.z = 0; g.add(post);
    var foot = S.rounded(0.2, 0.09, 0.008, 0.004, M.iron); foot.rotation.x = -Math.PI / 2; foot.position.set(-0.08, -0.066, 0); g.add(foot);
    detG.push(g); return g;
  }
  var det1 = makeDet(-0.40, 1, 'DETECTOR 1'), det2 = makeDet(-0.07, -1, 'DETECTOR 2');
  S.contact(0.34, 0.14, -0.48, -0.30, 0.45); S.contact(0.34, 0.14, 0.02, -0.30, 0.45);
  function holder(x, z) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z);
    var po = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.062, 12), M.chrome); po.position.y = 0.031; g.add(po);
    var ba = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.004, 20), M.iron); ba.position.y = 0.002; g.add(ba);
    var cup = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.003, 20), M.alu); cup.position.y = 0.0635; g.add(cup);
    return g;
  }
  var SY = 0.0675, hold = [];
  var srcPos = PAIR ? [new T.Vector3(-0.235, SY + 0.004, -0.30)] : [new T.Vector3(-0.33, SY + 0.004, -0.30), new T.Vector3(-0.14, SY + 0.004, -0.30)];
  srcPos.forEach(function (v) { hold.push(holder(v.x, v.z)); });
  var wall = null;
  if (!PAIR) { wall = new T.Group(); S.scene.add(wall); wall.position.set(-0.235, 0, -0.30); brick(wall, 0, 0, 0, 0.05, 0.13, 0.16); brick(wall, 0, 0.13, 0, 0.05, 0.04, 0.16); }
  var potG = makePot(-0.12, 0.10, 'SOURCE STORE'), tongs = makeTongs(0.0, 0.14);
  var srcs = [], potSpot = [new T.Vector3(-0.135, 0.016, 0.10), new T.Vector3(-0.105, 0.016, 0.10)];
  for (var si = 0; si < srcPos.length; si++) { var sg = makeSource(si === 0 ? 0xb8322a : 0x2a5db8); S.scene.add(sg); sg.position.copy(potSpot[si]); srcs.push(sg); }
  S.contact(0.3, 0.2, -0.06, 0.12, 0.45);
  if (wall) S.contact(0.12, 0.2, -0.235, -0.3, 0.5);
  var srcNames = PAIR ? [SAMPLE] : (V_.sample ? V_.sample.split(' and ') : ['Source A', 'Source B']);
  if (!PAIR && srcNames.length < 2) srcNames = [srcNames[0], 'Source B'];

  // ================================================================ the electronics crate
  var K0 = -0.03, KR = 0.034;
  function ang(k) { return (135 - (k - 1) * 30) * Math.PI / 180; }
  var crate = panel(0.66, 0.22, 0.24, function (x, w, h, X, Y, k) {
    x.fillStyle = '#f1efe8'; x.textAlign = 'left'; x.font = '700 ' + Math.round(0.011 * k) + 'px "Public Sans", sans-serif';
    x.fillText('DISCRIMINATOR', X(-0.31), Y(0.088)); x.fillText('COINCIDENCE UNIT', X(-0.115), Y(0.088)); x.fillText('SCALER – TIMER', X(0.075), Y(0.088));
    x.strokeStyle = 'rgba(255,255,255,.25)'; x.lineWidth = 2;
    [-0.135, 0.062].forEach(function (u) { x.beginPath(); x.moveTo(X(u), Y(0.095)); x.lineTo(X(u), Y(-0.095)); x.stroke(); });
    x.font = '500 ' + Math.round(0.0075 * k) + 'px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6';
    x.fillText(SLOW ? 'SLOW: SHAPING AMP + SINGLE-CHANNEL' : 'FAST: CONSTANT-FRACTION', X(-0.31), Y(0.07));
    x.fillText(SLOW ? 'ANALYSER, 2 CHANNELS' : 'DISCRIMINATOR, 2 CHANNELS', X(-0.31), Y(0.056));
    ['CH 1', 'CH 2'].forEach(function (t, i) {
      var cy = Y(0.015 - i * 0.05);
      x.beginPath(); x.arc(X(-0.285), cy, 0.011 * k, 0, 7); x.fillStyle = '#0d0f12'; x.fill(); x.strokeStyle = '#c9ced6'; x.lineWidth = 3; x.stroke();
      x.fillStyle = '#f1efe8'; x.font = '600 ' + Math.round(0.0085 * k) + 'px "Public Sans", sans-serif'; x.fillText('IN', X(-0.297), cy + 0.0035 * k);
      x.beginPath(); x.arc(X(-0.215), cy, 0.011 * k, 0, 7); x.fillStyle = '#0d0f12'; x.fill(); x.strokeStyle = '#c9ced6'; x.stroke();
      x.fillStyle = '#f1efe8'; x.fillText('OUT', X(-0.2305), cy + 0.0035 * k);
      x.fillStyle = '#c7ccd6'; x.fillText(t, X(-0.255), cy - 0.018 * k);
    });
    x.fillStyle = '#f1efe8'; x.font = '600 ' + Math.round(0.008 * k) + 'px "Public Sans", sans-serif'; x.textAlign = 'center';
    for (var g = 1; g <= 4; g++) { var th = ang(g); x.fillText('×' + g, X(K0 + (KR + 0.028) * Math.cos(th)), Y(-0.01 + (KR + 0.028) * Math.sin(th)) + 5);
      x.beginPath(); x.moveTo(X(K0 + (KR - 0.002) * Math.cos(th)), Y(-0.01 + (KR - 0.002) * Math.sin(th))); x.lineTo(X(K0 + (KR + 0.012) * Math.cos(th)), Y(-0.01 + (KR + 0.012) * Math.sin(th))); x.strokeStyle = '#f1efe8'; x.lineWidth = 4; x.stroke(); }
    x.fillText('GATE WIDTH (unit widths)', X(K0), Y(-0.088)); x.font = '500 ' + Math.round(0.0068 * k) + 'px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6';
    x.fillText('width of one unit is set by a clipped cable', X(K0), Y(-0.0985));
    x.textAlign = 'left'; x.fillStyle = '#f1efe8'; x.font = '700 ' + Math.round(0.0085 * k) + 'px "Public Sans", sans-serif';
    ['N1', 'N2', 'NC', 'T (s)'].forEach(function (t, i) { x.fillText(t, X(0.07), Y(0.067 - i * 0.04) + 5); });
    x.textAlign = 'center'; x.fillText('START', X(0.288), Y(0.0)); x.fillText('RESET', X(0.288), Y(-0.058));
  }, 0.55, -0.20, -0.15);
  var gateKnob = makeKnob(crate, K0, -0.01), gateA = ang(1);
  function gateRot(k) { return ang(k) - Math.PI / 2; }
  gateKnob.rotation.z = gateRot(1);
  var startB = makeButton(crate, 0.288, 0.02, M.green), resetB = makeButton(crate, 0.288, -0.038, M.grey);
  var showN1 = makeLcd(crate, 0.185, 0.068, 0.11, 0.03, 8), showN2 = makeLcd(crate, 0.185, 0.028, 0.11, 0.03, 8),
    showNc = makeLcd(crate, 0.185, -0.012, 0.11, 0.03, 8), showT = makeLcd(crate, 0.185, -0.052, 0.11, 0.03, 8);
  [[-0.285, 0.015, -0.14], [-0.285, -0.035, -0.12]].forEach(function (c, i) {      // cables detector -> crate
    var d = i ? det2 : det1, endx = i ? 0.0 : -0.9;
    S.wire(i ? [[0.18, 0.07, -0.30], [0.24, 0.01, -0.2], [0.30, 0.05, -0.09]] : [[-0.66, 0.07, -0.30], [-0.4, 0.01, -0.12], [0.28, 0.06, -0.08]], 'black');
  });
  S.wire([[0.215, 0.0, -0.1], [0.3, 0.02, -0.12]], 'black');
  var scr = makeScreen(-0.12, -0.52, 0, 0.36, 0.22);
  var hudG = S.hudCard('Gate setting'), hudC = S.hudCard('Coincidences'), hudR = S.hudCard('Coincidence rate');

  S.addApparatus('det1', det1, 'Detector 1', 'A plastic scintillator on a photomultiplier tube. Each quantum that stops in it gives a flash and one electrical pulse.');
  S.addApparatus('det2', det2, 'Detector 2', 'The second scintillation detector. It looks at the other source (or at the other half of the pair).');
  if (wall) S.addApparatus('wall', wall, 'Lead wall', 'Keeps radiation from one source out of the other detector, so a pulse in one detector has nothing to do with a pulse in the other: only chance coincidences can occur.');
  S.addApparatus('src', srcs[0], PAIR ? SAMPLE : srcNames[0], 'A sealed disc source. It is moved only with the tongs, from behind the shield, and lives in the lead store when not in use.');
  S.addApparatus('pot', potG, 'Lead source store', 'Sources are kept here, lid on, whenever they are not being counted.');
  S.addApparatus('tongs', tongs, 'Source tongs', 'Long tongs keep your hands away from the source: distance is the cheapest shielding there is.');
  S.addApparatus('crate', crate.g, 'Electronics crate', 'Discriminators turn each pulse into a logic pulse of fixed width; the coincidence unit gives an output when pulses from both detectors overlap; the scaler counts them for a preset time.');
  S.addApparatus('screen', scr.g, 'Live monitor', 'Shows the counts as they come in and the coincidence rate against the gate setting, with the straight line through them.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ================================================================ the monitor
  var lastPaint = 0;
  function paint(force) {
    var now = performance.now(); if (!force && now - lastPaint < 90) return; lastPaint = now;
    scr.tex.draw(function (x, w, h) {
      x.fillStyle = '#0d1a14'; x.fillRect(0, 0, w, h);
      x.fillStyle = '#c9f5dc'; x.textAlign = 'left'; x.font = '700 ' + Math.round(h * 0.052) + 'px "JetBrains Mono", monospace';
      x.fillText('COINCIDENCE COUNTER', 24, h * 0.085);
      x.font = '500 ' + Math.round(h * 0.034) + 'px "JetBrains Mono", monospace'; x.fillStyle = '#9fe0b8';
      x.fillText((SLOW ? 'slow' : 'fast') + ' coincidence', 24, h * 0.14);
      var tt = st.elapsed > 0 ? st.elapsed : 0, rr = function (n) { return tt > 0 ? (n / tt) : 0; };
      x.font = '600 ' + Math.round(h * 0.044) + 'px "JetBrains Mono", monospace'; x.fillStyle = '#6dffa4';
      var yy = h * 0.27, rowsT = [['CH 1', st.n1, rr(st.n1)], ['CH 2', st.n2, rr(st.n2)], ['COINC', st.nc, rr(st.nc)]];
      rowsT.forEach(function (r, i) { x.textAlign = 'left'; x.fillText(r[0], 24, yy + i * h * 0.09); x.textAlign = 'right'; x.fillText(String(r[1]), 330, yy + i * h * 0.09);
        x.fillStyle = '#9fe0b8'; x.fillText(tt > 0 ? r[2].toFixed(r[2] < 100 ? 1 : 0) + ' /s' : '— /s', 590, yy + i * h * 0.09); x.fillStyle = '#6dffa4'; });
      x.textAlign = 'left'; x.fillStyle = '#ffd24a'; x.fillText('GATE  ×' + st.k, 24, yy + 3 * h * 0.09 + 8);
      // pulses, to show what "overlap" means
      var by = h * 0.66, bw = 580, bx = 24, wdt = 0.045 * st.k, t1 = [0.06, 0.30, 0.52, 0.80], t2 = [0.13, 0.33, 0.62, 0.77], i, ov;
      x.strokeStyle = '#7fd7a8'; x.lineWidth = 2; x.fillStyle = '#9fe0b8'; x.font = Math.round(h * 0.03) + 'px "JetBrains Mono", monospace';
      x.fillText('detector 1', bx, by - 6); x.fillText('detector 2', bx, by + h * 0.12 - 6);
      for (i = 0; i < 4; i++) {
        ov = Math.abs(t1[i] - t2[i]) < wdt;
        x.fillStyle = ov ? 'rgba(255,210,74,.55)' : 'rgba(109,255,164,.35)';
        x.fillRect(bx + bw * t1[i], by + 4, bw * wdt, h * 0.05); x.fillRect(bx + bw * t2[i], by + h * 0.12 + 4, bw * wdt, h * 0.05);
      }
      x.fillStyle = '#9fe0b8'; x.fillText('amber = pulses overlap', bx, by + h * 0.24);
      // the line of Rc against the gate
      var box = { l: 800, r: w - 30, t: h * 0.14, b: h * 0.78 }, pts = S.rows.map(function (r) { return [r.k, r.rc]; });
      var ymax = 10, i2; pts.forEach(function (q) { if (q[1] > ymax) ymax = q[1]; }); if (st.last) ymax = Math.max(ymax, st.last.Nc / st.last.t);
      ymax = ymax * 1.18;
      var fr = plotFrame(x, w, h, box, 0, 5, 0, ymax, 'gate setting k', 'coincidence rate (/s)', 5, 4, null, function (v) { return v >= 100 ? String(Math.round(v)) : v.toFixed(1); });
      var fitr = S.rows.length >= 2 ? KN.fit(S.rows.map(function (r) { return [r.k, r.r1, r.r2, r.rc]; })) : null;
      if (fitr) {
        var rr12 = 0, nn = 0; S.rows.forEach(function (r) { rr12 += r.r1 * r.r2; nn++; }); rr12 /= nn; var slope = 2 * fitr.tau * rr12;
        x.strokeStyle = '#ffd24a'; x.lineWidth = 2; x.setLineDash([6, 5]); x.beginPath(); x.moveTo(fr.X(0), fr.Y(fitr.Rt)); x.lineTo(fr.X(5), fr.Y(fitr.Rt + slope * 5)); x.stroke(); x.setLineDash([]);
        x.fillStyle = '#ffd24a'; x.beginPath(); x.arc(fr.X(0), fr.Y(fitr.Rt), 6, 0, 7); x.fill();
      }
      x.fillStyle = '#6dffa4'; pts.forEach(function (q) { x.beginPath(); x.arc(fr.X(q[0]), fr.Y(q[1]), 7, 0, 7); x.fill(); });
    });
  }
  paint(true);

  // ================================================================ human actions
  function moveSource(i, to) {
    var sg = srcs[i], from = sg.position.clone();
    var arc = function (k) { return new T.Vector3(from.x + (to.x - from.x) * k, from.y + (to.y - from.y) * k + 0.06 * Math.sin(Math.PI * k), from.z + (to.z - from.z) * k); };
    return S.hand.pinchMove(from, arc, function (k) { sg.position.copy(arc(k)); tongs.position.set(sg.position.x + 0.07, sg.position.y, sg.position.z + 0.05); },
      { mode: 'side', ms: 1000, reachMs: 600 }).then(function () { sg.position.copy(to); });
  }
  function placeSources() {
    if (busy() || st.placed) return Promise.resolve();
    var ch = Promise.resolve();
    srcs.forEach(function (sg, i) { ch = ch.then(function () { return moveSource(i, srcPos[i]); }); });
    return ch.then(function () {
      st.placed = true;
      S.say(PAIR ? 'The source is midway between the two detectors, put there with the tongs from behind the shield.'
        : 'Each source is in front of its own detector, with the lead wall between the detectors, put there with the tongs from behind the shield.');
      S.render();
    });
  }
  function storeSources() {
    if (busy() || !st.placed) return Promise.resolve();
    var ch = Promise.resolve();
    srcs.forEach(function (sg, i) { ch = ch.then(function () { return moveSource(i, potSpot[i]); }); });
    return ch.then(function () { st.placed = false; S.say('Sources back in the lead store, lid on, locked away. That is where they belong when the readings are done.'); S.render(); });
  }
  function turnGate(k) {
    if (busy()) return Promise.resolve();
    if (!isFinite(k) || k < 1 || k > 4 || Math.round(k) !== k) { S.say('The gate switch has four positions: ×1, ×2, ×3 and ×4.'); return Promise.resolve(); }
    if (k === st.k) return Promise.resolve();
    var k0 = st.k, a0 = gateRot(k0), a1 = gateRot(k), pt = wpt(crate.g, K0, 0.004 + crate.H / 2 - 0.01, crate.FZ + 0.024);
    return S.hand.pinchMove(pt, function () { return pt; }, function (u) { gateKnob.rotation.z = a0 + (a1 - a0) * u; S.hand.group.rotation.y = -(a1 - a0) * u * 0.3; },
      { mode: 'front', ms: 500, reachMs: 600 }).then(function () { st.k = k; gateKnob.rotation.z = a1; S.say('Gate set to ×' + k + ': the coincidence window is ' + k + ' unit widths.'); S.render(); });
  }
  function count() {
    if (busy()) return Promise.resolve(false);
    if (!st.placed) { S.say('Put the sources in place first, with the tongs.'); return Promise.resolve(false); }
    var c = KN.counts(assign(p, { k: st.k, j: st.idx })); st.idx += 1;
    st.counting = true; st.n1 = st.n2 = st.nc = 0; st.elapsed = 0; st.recorded = false;
    return S.hand.tap(startB, 'front').then(function () {
      return S.tween(1500, function (u) { st.elapsed = p.t * u; st.n1 = Math.round(c[0] * u); st.n2 = Math.round(c[1] * u); st.nc = Math.round(c[2] * u); });
    }).then(function () {
      st.counting = false; st.elapsed = p.t; st.n1 = c[0]; st.n2 = c[1]; st.nc = c[2]; st.last = { k: st.k, N1: c[0], N2: c[1], Nc: c[2], t: p.t };
      S.say('Gate ×' + st.k + ': N1 = ' + c[0] + ', N2 = ' + c[1] + ', coincidences = ' + c[2] + ' in ' + p.t + ' s.'); S.render(); paint(true); return true;
    });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.last || st.recorded || st.elapsed < p.t - 1e-9) { S.say('Press START and let the counter run its full ' + p.t + ' s first.'); return false; }
    var L = st.last; st.recorded = true;
    S.addRow({ k: L.k, t: L.t, N1: L.N1, N2: L.N2, Nc: L.Nc, r1: L.N1 / L.t, r2: L.N2 / L.t, rc: L.Nc / L.t });
    S.say('Written in your record book: gate ×' + L.k + ', coincidence rate ' + (L.Nc / L.t).toFixed(1) + ' per second.'); paint(true); return true;
  }
  function resetCounter() {
    if (busy()) return Promise.resolve();
    return S.hand.tap(resetB, 'front').then(function () { st.n1 = st.n2 = st.nc = 0; st.elapsed = 0; S.say('Counter cleared.'); S.render(); paint(true); });
  }
  function distinctK() { var o = {}; S.rows.forEach(function (r) { o[r.k] = 1; }); return Object.keys(o).length; }
  function fitNow(rows) {
    var ok = rows.map(function (r) { return [r.k, r.r1, r.r2, r.rc]; });
    return ok.length >= 3 ? KN.fit(ok) : null;
  }

  function result(rows) {
    var f = fitNow(rows); if (!f || distinctK() < 4) return null;
    if (PAIR) return { label: 'True coincidence rate', value: f.Rt, unit: '/s', digits: 0, truth: p.Rt,
      note: 'The line of coincidence rate against gate setting does not pass through zero: where it meets k = 0 is the rate of coincidences that do not depend on the gate, the true ones (' + f.Rt.toFixed(0) + ' per second). Its slope gives the resolving time of one unit width, ' + (f.tau * UNIT).toFixed(1) + ' ' + UNAME + '.' };
    return { label: 'Resolving time of one gate unit', value: f.tau * UNIT, unit: UNAME, digits: 1, truth: p.tau * UNIT,
      note: 'The coincidence rate is a straight line in the gate setting with slope 2 τ R1 R2, so τ = slope / (2 R1 R2) = ' + (f.tau * UNIT).toFixed(1) + ' ' + UNAME + ' (R1 and R2 are the mean singles rates). The line goes through zero, as it must for unrelated sources.' };
  }

  return {
    camera: { pos: [0.08, 0.9, 1.55], look: [0.08, 0.06, -0.2] },
    views: { det1: [[-0.45, 0.25, 0.15], [-0.4, 0.07, -0.3]], det2: [[-0.1, 0.25, 0.15], [-0.07, 0.07, -0.3]], wall: [[-0.235, 0.25, 0.1], [-0.235, 0.07, -0.3]],
      src: [[-0.3, 0.2, 0.0], [-0.235, 0.07, -0.3]], pot: [[-0.1, 0.2, 0.4], [-0.12, 0.02, 0.1]], tongs: [[0.05, 0.2, 0.42], [0.0, 0.0, 0.14]],
      crate: [[0.5, 0.32, 0.5], [0.55, 0.1, -0.08]], unit: [[0.5, 0.32, 0.5], [0.55, 0.1, -0.08]], screen: [[-0.12, 0.3, 0.1], [-0.12, 0.17, -0.52]],
      bench: [[0.08, 0.9, 1.55], [0.08, 0.06, -0.2]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A coincidence unit gives an output when pulses from two detectors overlap. Pulses from one decay (two quanta emitted together) always overlap: these are TRUE coincidences. But two pulses from unrelated events also overlap now and then by chance, whenever one falls within the gate width of the other. Those ACCIDENTAL coincidences are a nuisance, and they also measure how good the coincidence unit is.',
      formula: 'R_acc = 2 τ R₁ R₂,   R_c = R_true + 2 k τ R₁ R₂',
      formulaNote: 'τ = width of one unit of the gate; k = 1…4; R₁, R₂ = singles rates',
      more: ['With two unrelated sources there is no true rate, so the coincidence rate is a straight line through the origin whose slope is 2 τ R₁ R₂: that is how the resolving time is measured.',
        'With a source that emits both quanta of one decay, the same line has an intercept: the rate at k = 0 is the true coincidence rate.',
        'The 2 comes from the window: a pulse in detector 2 counts if it comes within τ before or within τ after a pulse in detector 1.'],
      precautions: 'The sources are sealed, moved only with tongs from behind the lead shield and returned to their locked store when the readings are done. Keep the singles rates well below 1/τ, or pulses start to overlap among themselves.' },
    book: { title: 'Expt. — ' + (PAIR ? 'True and accidental coincidences' : 'Resolving time by accidental coincidences'),
      lines: ['Aim: ' + (PAIR ? 'true coincidence rate and resolving time.' : 'resolving time of the coincidence unit.'), 'Sample: ' + SAMPLE,
        'Method: ' + (V_.method || (SLOW ? 'slow coincidence' : 'fast coincidence')), 'R_c = R_true + 2kτR₁R₂;  counting time ' + p.t + ' s'],
      columns: [{ label: 'k', get: function (r) { return r.k; } }, { label: 'N1', get: function (r) { return r.N1; } },
        { label: 'N2', get: function (r) { return r.N2; } }, { label: 'Nc', get: function (r) { return r.Nc; } },
        { label: 'Rc (/s)', get: function (r) { return r.rc.toFixed(1); } }] },
    graph: { x: function (r) { return r.k; }, y: function (r) { return r.rc; }, xlabel: 'gate setting k', ylabel: 'coincidence rate (/s)', x0: 0, y0: 0,
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.04,
    resultNote: 'A straight line in the gate setting is the signature of chance coincidences: doubling the window doubles them.',
    chips: ['Why does the line go through zero?', 'Why the factor 2?', 'What is a true coincidence?', 'Check my readings', 'Why must R1 and R2 stay small?'],
    viva: [['Accidental coincidences between unrelated pulses happen at a rate of', ['2 τ R₁ R₂', 'τ R₁ R₂', 'R₁ R₂ / τ'], 0,
      'A pulse in detector 2 must fall within τ before or after a pulse in detector 1: the window is 2τ.'],
      ['Doubling the gate width makes the accidental rate', ['Twice as big', 'Four times as big', 'Unchanged'], 0, 'R_acc is proportional to τ.'],
      ['The true coincidence rate is the', ['Intercept of the line at k = 0', 'Slope of the line', 'Rate at k = 4'], 0,
        'It does not depend on the gate width, so it is what is left when the gate shrinks to nothing.']],
    askState: function () {
      return { experiment: PAIR ? 'true and accidental coincidences' : 'resolving time by accidental coincidences', sample: SAMPLE,
        sources_placed: st.placed, gate_setting: st.k, counting_time_s: p.t, readings_taken: S.rows.length,
        last_reading: st.last ? { k: st.last.k, N1: st.last.N1, N2: st.last.N2, coincidences: st.last.Nc } : null };
    },
    steps: [
      { id: 'setup', title: 'Sources in place', view: 'bench', render: function (u) {
          u.h2('Put the sources in front of the detectors');
          u.p(PAIR ? 'The source goes midway between the two detectors, so that the two quanta of one decay reach one detector each.'
            : 'Each source goes in front of its own detector. The lead wall between the detectors keeps each source out of the other detector: any coincidence will be pure chance.');
          u.p('Use the tongs, from behind the shield. The sources stay exactly there for every reading.');
          u.task('Sources in place', st.placed, st.placed ? 'In front of the detectors' : 'In the lead store')
            .add(u.button(st.placed ? 'Sources are in place' : 'Lift them with the tongs', function () { S.focus('src'); placeSources(); }, !st.placed, st.placed || S.hand.busy));
          u.next('Next: take the readings', st.placed);
        },
        ok: function () { return st.placed; }, auto: function () { return placeSources(); } },
      { id: 'read', title: 'Readings at four gate settings', view: 'crate', render: function (u) {
          u.h2('Count at each gate setting');
          u.p('Turn the gate switch to ×1, count for ' + p.t + ' s and write the reading down. Repeat for ×2, ×3 and ×4. Nothing else may be touched.');
          u.row(u.button('Gate ×1', function () { turnGate(1); }, st.k === 1, S.hand.busy), u.button('×2', function () { turnGate(2); }, st.k === 2, S.hand.busy),
            u.button('×3', function () { turnGate(3); }, st.k === 3, S.hand.busy), u.button('×4', function () { turnGate(4); }, st.k === 4, S.hand.busy));
          u.row(u.button('START (' + p.t + ' s)', function () { count(); }, true, S.hand.busy), u.button('Record this reading', function () { record(); }, false, S.hand.busy),
            u.button('Reset', function () { resetCounter(); }, false, S.hand.busy));
          u.live(function () { return 'Gate ×' + st.k + '  ·  N1 ' + st.n1 + '  ·  N2 ' + st.n2 + '  ·  coincidences ' + st.nc + '  ·  ' + st.elapsed.toFixed(1) + ' s'; });
          u.h3('Observation table'); u.table();
          u.p(distinctK() + ' of 4 gate settings recorded.');
          u.next('Next: the result', distinctK() >= 4);
        },
        ok: function () { return distinctK() >= 4; },
        auto: function () {
          var ch = Promise.resolve();
          [1, 2, 3, 4].forEach(function (k) { ch = ch.then(function () { return turnGate(k); }).then(function () { return count(); }).then(function () { record(); }); });
          return ch.then(function () { return storeSources(); });
        } }
    ],
    tick: function () {
      showN1(String(st.n1)); showN2(String(st.n2)); showNc(String(st.nc)); showT(st.elapsed.toFixed(0));
      hudG.set('×' + st.k); hudC.set(String(st.nc)); hudR.set(st.elapsed > 0 ? (st.nc / st.elapsed).toFixed(1) + ' /s' : '—');
      if (st.counting) paint(false);
    }
  };
});
