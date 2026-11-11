/* Prayogshala studio module: COSMIC-RAY MUON LIFETIME BENCH (PhD nuclear / particle physics).
   A scintillator (a plastic block, or a liquid-scintillator tank) viewed by photomultipliers, a discriminator and
   a time-to-amplitude converter feeding a multichannel analyser: a muon that STOPS in the scintillator starts
   the clock (the first pulse, then no second pulse from a muon passing through) and its decay electron stops
   it. The delays make a histogram that falls as exp(-t/tau) on a flat floor of chance coincidences. A run of
   several days is taken in blocks of hours; the histogram is shown live on a logarithmic scale.
   Physics: the `ph3_muon` kernel of packs/ph3_nuc.js - mu+ with the free lifetime, mu- partly captured by
   carbon, a flat accidental floor. Counts are Poisson numbers from the lab's own seed. */
HoolaStudio.define('ph3-muon', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.ph3_muon, assign = HK.assign;
  var p = HK.paramsFor('ph3_muon', S.lab.params);
  var V_ = S.lab.variant || {}, TANK = p.Rs > 500, NB = Math.round(p.nb);
  var SAMPLE = V_.sample || (TANK ? 'Mineral-oil liquid scintillator tank' : 'Plastic scintillator block, 30 cm × 30 cm × 15 cm');
  var NEED = 6, TRUTH = KN.measure(p).tau_fit;
  var st = { hv: false, tac: false, blocks: 0, hist: null, cur: null, prog: 0, running: false, idx: 0, floor: null, fit: null, hours: 0, booked: false };
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

  // ================================================================ the scintillator
  var det = new T.Group(); S.scene.add(det); det.position.set(-0.30, 0, -0.18);
  var scM = new T.MeshStandardMaterial({ color: 0x9fc4e6, roughness: 0.2, transparent: true, opacity: 0.82, emissive: 0x2a5db8, emissiveIntensity: 0.0 });
  var blackM = new T.MeshStandardMaterial({ color: 0x15171a, roughness: 0.8 });
  var stand = S.rounded(0.42, 0.34, 0.03, 0.01, M.iron); stand.rotation.x = -Math.PI / 2; stand.position.set(0, 0.015, 0); det.add(stand);
  var pmts = [];
  function pmtAt(x, y, z, rz, ry) {
    var g = new T.Group(); g.position.set(x, y, z); g.rotation.z = rz || 0; g.rotation.y = ry || 0; det.add(g);
    var cone = S.mesh(new T.CylinderGeometry(0.042, 0.065, 0.05, 28), blackM); cone.position.y = 0.025; g.add(cone);
    var tube = S.mesh(new T.CylinderGeometry(0.0425, 0.0425, 0.13, 32), new T.MeshStandardMaterial({ color: 0x2c3138, roughness: 0.5, metalness: 0.5 })); tube.position.y = 0.115; g.add(tube);
    var bs = S.mesh(new T.CylinderGeometry(0.045, 0.045, 0.04, 32), M.bakelite); bs.position.y = 0.2; g.add(bs); pmts.push(g); return g;
  }
  if (!TANK) {
    var blk = S.mesh(new T.BoxGeometry(0.30, 0.12, 0.30), blackM); blk.position.set(0, 0.09, 0); det.add(blk);
    var top = S.mesh(new T.BoxGeometry(0.2, 0.002, 0.2), scM); top.position.set(0, 0.1505, 0); det.add(top);
    pmtAt(0, 0.15, 0, 0, 0).scale.set(0.7, 0.7, 0.7);
    var lg = S.mesh(new T.BoxGeometry(0.02, 0.1, 0.1), blackM); lg.position.set(0.16, 0.09, 0); det.add(lg);
    var pm2 = pmtAt(0.18, 0.09, 0, -Math.PI / 2, 0); pm2.scale.set(0.7, 0.7, 0.7);
  } else {
    var tk = S.mesh(new T.CylinderGeometry(0.14, 0.14, 0.26, 48), new T.MeshStandardMaterial({ color: 0xcfd4d8, roughness: 0.35, metalness: 0.7 })); tk.position.set(0, 0.16, 0); det.add(tk);
    var liq = S.mesh(new T.CylinderGeometry(0.128, 0.128, 0.004, 48), scM); liq.position.set(0, 0.292, 0); det.add(liq);
    var rim = S.mesh(new T.TorusGeometry(0.14, 0.006, 8, 48), M.steel); rim.rotation.x = Math.PI / 2; rim.position.y = 0.29; det.add(rim);
    [-0.06, 0.06].forEach(function (zz) { var g = pmtAt(0, 0.29, zz, 0, 0); g.scale.set(0.6, 0.6, 0.6); });
    var tlb = S.label('LIQUID SCINTILLATOR', { w: 0.14, ratio: 0.14, color: '#f1efe8', bg: '#26334a' }); tlb.position.set(0, 0.12, 0.1405); det.add(tlb);
  }
  S.contact(0.5, 0.45, -0.3, -0.18, 0.5);

  // ================================================================ electronics
  var rack = panel(0.5, 0.2, 0.22, function (x, w, h, X, Y, k) {
    x.fillStyle = '#f1efe8'; x.textAlign = 'left'; x.font = '700 ' + Math.round(0.011 * k) + 'px "Public Sans", sans-serif'; x.fillText('MUON TIMING', X(-0.235), Y(0.085));
    x.font = '500 ' + Math.round(0.0075 * k) + 'px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText('DISCRIMINATOR · TIME-TO-AMPLITUDE CONVERTER · ' + NB + '-CHANNEL MCA', X(-0.235), Y(0.07));
    x.fillStyle = '#f1efe8'; x.font = '700 ' + Math.round(0.0085 * k) + 'px "Public Sans", sans-serif'; x.fillText('DECAYS', X(-0.235), Y(0.02)); x.fillText('HOURS', X(-0.235), Y(-0.04));
    x.textAlign = 'center'; ['HV', 'TAC', 'RUN', 'CLEAR'].forEach(function (t, i) { x.fillText(t, X(0.0 + i * 0.062 + 0.02), Y(-0.07)); });
    x.textAlign = 'left'; x.font = '500 ' + Math.round(0.0072 * k) + 'px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText('range ' + (p.T0).toFixed(1) + ' – ' + (p.T0 + p.dt * NB).toFixed(1) + ' µs, ' + p.dt + ' µs bins', X(-0.235), Y(-0.085));
  }, 0.42, -0.12, -0.15);
  var bHv = makeButton(rack, 0.02, -0.05, M.green), bTac = makeButton(rack, 0.082, -0.05, M.green), bRun = makeButton(rack, 0.144, -0.05, M.green), bClr = makeButton(rack, 0.206, -0.05, M.grey);
  var lampM = [0, 1].map(function () { return new T.MeshStandardMaterial({ color: 0x331111, emissive: 0xff2a2a, emissiveIntensity: 0.0 }); });
  [0.02, 0.082].forEach(function (u, i) { var l = S.mesh(new T.SphereGeometry(0.005, 12, 8), lampM[i], false); l.position.copy(rack.up(u, -0.03, 0.002)); rack.g.add(l); });
  var showD = makeLcd(rack, -0.065, 0.025, 0.2, 0.034, 8), showH = makeLcd(rack, -0.065, -0.035, 0.2, 0.034, 8);
  var scr = makeScreen(0.04, -0.52, 0, 0.5, 0.3);
  S.wire([[-0.3 - 0.0, 0.34, -0.18], [-0.1, 0.35, -0.2], [0.22, 0.12, -0.05]], 'black');
  S.wire([[-0.12, 0.2, -0.18], [0.0, 0.01, -0.02], [0.24, 0.1, -0.05]], 'blue');
  var hudH = S.hudCard('Data taken'), hudN = S.hudCard('Decays'), hudT = S.hudCard('Mean life');

  S.addApparatus('det', det, SAMPLE, 'A muon that stops in the scintillator lights it, once when it enters and again when its decay electron leaves. Muons that pass through give only the first flash.');
  S.addApparatus('rack', rack.g, 'Timing electronics', 'The discriminator makes a logic pulse from each flash; the time-to-amplitude converter turns the time between the first and the second into a pulse height; the MCA histograms those heights.');
  S.addApparatus('screen', scr.g, 'Live decay-time histogram', 'Counts against decay time on a logarithmic scale: an exponential is a straight line.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ================================================================ screen
  function shown() { var out = [], i; if (!st.hist && !st.cur) return null; for (i = 0; i < NB; i++) out.push((st.hist ? st.hist[i] : 0) + (st.cur ? Math.round(st.cur[i] * st.prog) : 0)); return out; }
  var lastPaint = 0;
  function paint(force) {
    var now = performance.now(); if (!force && now - lastPaint < 100) return; lastPaint = now;
    scr.tex.draw(function (x, w, h) {
      x.fillStyle = '#0d1a14'; x.fillRect(0, 0, w, h);
      var c = shown(), box = { l: 96, r: w - 24, t: h * 0.1, b: h * 0.84 }, i, ymax = 10, X0 = p.T0, X1 = p.T0 + p.dt * NB;
      if (c) for (i = 0; i < NB; i++) if (c[i] > ymax) ymax = c[i];
      var top = Math.pow(10, Math.ceil(Math.log(ymax * 1.05) / Math.LN10)), ymin = 0.7, ly = function (v) { return Math.log(Math.max(v, ymin)) / Math.LN10; };
      var fr = { X: function (v) { return box.l + (v - X0) / (X1 - X0) * (box.r - box.l); }, Y: function (v) { return box.b - (ly(v) - ly(ymin)) / (ly(top) - ly(ymin)) * (box.b - box.t); } };
      x.strokeStyle = 'rgba(160,230,190,.16)'; x.lineWidth = 1; x.fillStyle = '#9fe0b8'; x.font = Math.round(h * 0.034) + 'px "JetBrains Mono", monospace'; x.textAlign = 'right';
      for (var dcd = 0; Math.pow(10, dcd) <= top; dcd++) { var v = Math.pow(10, dcd); x.beginPath(); x.moveTo(box.l, fr.Y(v)); x.lineTo(box.r, fr.Y(v)); x.stroke(); x.fillText(String(v), box.l - 6, fr.Y(v) + 5); }
      x.textAlign = 'center'; for (i = 0; i <= 6; i++) { var tv = X0 + (X1 - X0) * i / 6; x.beginPath(); x.moveTo(fr.X(tv), box.t); x.lineTo(fr.X(tv), box.b); x.stroke(); x.fillText(tv.toFixed(1), fr.X(tv), box.b + h * 0.05); }
      x.fillStyle = '#c9f5dc'; x.fillText('delay between the two pulses (µs)', (box.l + box.r) / 2, h - 8); x.save(); x.translate(20, (box.t + box.b) / 2); x.rotate(-Math.PI / 2); x.fillText('counts per bin (log scale)', 0, 0); x.restore();
      x.strokeStyle = 'rgba(160,230,190,.5)'; x.strokeRect(box.l, box.t, box.r - box.l, box.b - box.t);
      x.textAlign = 'left'; x.fillStyle = '#c9f5dc'; x.font = '600 ' + Math.round(h * 0.04) + 'px "JetBrains Mono", monospace'; x.fillText(st.hours.toFixed(0) + ' h of data' + (st.running ? ' + block running' : ''), box.l + 8, box.t - 10);
      if (c) {
        x.fillStyle = '#6dffa4'; for (i = 0; i < NB; i++) { var cx = fr.X(p.T0 + (i + 0.5) * p.dt); x.beginPath(); x.arc(cx, fr.Y(c[i]), 5, 0, 7); x.fill(); }
        if (st.floor !== null) { x.strokeStyle = '#ffd24a'; x.setLineDash([6, 5]); x.lineWidth = 2; x.beginPath(); x.moveTo(box.l, fr.Y(st.floor)); x.lineTo(box.r, fr.Y(st.floor)); x.stroke(); x.setLineDash([]); x.fillStyle = '#ffd24a'; x.fillText('floor ' + st.floor.toFixed(1), box.r - 190, fr.Y(st.floor) - 8); }
        if (st.fit) { var f = st.fit, y0 = null; x.strokeStyle = '#ff8a5c'; x.lineWidth = 3; x.beginPath();
          // the fitted exponential through the mean of the first bin
          var a0 = 0, n0 = 0; for (i = 0; i < 4; i++) { a0 += (c[i] - st.floor) * Math.exp((p.T0 + (i + 0.5) * p.dt) / f.tau); n0++; } a0 /= n0;
          for (var q = 0; q <= 40; q++) { var tt = X0 + (X1 - X0) * q / 40, yv = st.floor + a0 * Math.exp(-tt / f.tau); if (q) x.lineTo(fr.X(tt), fr.Y(yv)); else x.moveTo(fr.X(tt), fr.Y(yv)); } x.stroke();
          x.fillStyle = '#ff8a5c'; x.fillText('fit: τ = ' + f.tau.toFixed(3) + ' µs', box.l + 16, box.t + h * 0.07); }
      } else { x.fillStyle = '#6aa88a'; x.textAlign = 'center'; x.fillText('no data yet: switch on, then take a block', (box.l + box.r) / 2, (box.t + box.b) / 2); }
    });
  }
  paint(true);

  // ================================================================ human actions
  function sw(button, key) {
    if (busy()) return Promise.resolve();
    return S.hand.tap(button, 'front').then(function () { st[key] = !st[key]; S.say((key === 'hv' ? 'High voltage ' : 'Time-to-amplitude converter ') + (st[key] ? 'on.' : 'off.')); S.render(); });
  }
  function total(h) { var t = 0; if (h) for (var i = 0; i < h.length; i++) t += h[i]; return t; }
  function block() {
    if (busy() || st.running) return Promise.resolve(false);
    if (!st.hv || !st.tac) { S.say('Switch on the high voltage and the converter first.'); return Promise.resolve(false); }
    if (st.blocks >= 12) { S.say('Twelve blocks are enough: stop and analyse.'); return Promise.resolve(false); }
    var c = KN.chunk(assign(p, { j: st.idx })); st.idx += 1; st.cur = c; st.prog = 0; st.running = true;
    return S.hand.tap(bRun, 'front').then(function () { return S.tween(1400, function (u) { st.prog = u; }); }).then(function () {
      var i; st.hist = st.hist || []; for (i = 0; i < NB; i++) st.hist[i] = (st.hist[i] || 0) + c[i];
      st.cur = null; st.prog = 0; st.running = false; st.blocks += 1; st.hours += p.h; st.floor = null; st.fit = null;
      S.say('Block ' + st.blocks + ' done: ' + st.hours.toFixed(0) + ' hours, ' + total(st.hist) + ' decays so far.'); S.render(); paint(true); return true;
    });
  }
  function clearAll() {
    if (busy()) return Promise.resolve();
    return S.hand.tap(bClr, 'front').then(function () { st.hist = null; st.cur = null; st.blocks = 0; st.hours = 0; st.floor = null; st.fit = null; st.booked = false; S.say('Histogram cleared.'); S.render(); paint(true); });
  }
  function findFloor() {
    if (!st.hist) { S.say('Take some data first.'); return false; }
    var nbg = Math.round(p.nbg), s = 0, i; for (i = NB - nbg; i < NB; i++) s += st.hist[i];
    st.floor = s / nbg; S.say('Floor from the last ' + nbg + ' bins (' + (p.T0 + p.dt * (NB - nbg)).toFixed(1) + ' µs onward): ' + st.floor.toFixed(2) + ' counts per bin.'); S.render(); paint(true); return true;
  }
  function writeBook() {
    if (st.floor === null) { S.say('Find the floor first.'); return false; }
    if (st.booked) { S.say('The histogram is already in your record book.'); return false; }
    var i; for (i = 0; i < NB; i++) { var tc = p.T0 + (i + 0.5) * p.dt; if (tc > p.tfit) break; S.addRow({ tc: tc, N: st.hist[i], net: st.hist[i] - st.floor }); }
    st.booked = true; S.say('The bins up to ' + p.tfit + ' µs are written in your record book.'); return true;
  }
  function doFit() {
    if (st.floor === null || !st.booked) { S.say('Find the floor and write the histogram in the book first.'); return false; }
    st.fit = KN.fit_life(st.hist, p); S.say('Mean life from the fit: ' + st.fit.tau.toFixed(3) + ' µs.'); S.render(); paint(true); return true;
  }
  function result() {
    if (!st.fit || !st.fit.tau) return null;
    var cap = (p.tp - st.fit.tau) / p.tp * 100;
    return { label: 'Apparent mean life of stopped muons', value: st.fit.tau, unit: 'µs', digits: 3, truth: TRUTH,
      note: 'From ' + total(st.hist) + ' decays in ' + st.hours.toFixed(0) + ' hours. The free-muon mean life is 2.197 µs; yours is ' + cap.toFixed(1) + ' % lower. The shortfall is the capture of negative muons by carbon, which both shortens their life in the material and removes them from the decay spectrum (the real answer to “why is it lower” is not noise: with this many decays the scatter is about 1.5 %).' };
  }

  return {
    camera: { pos: [0.0, 0.95, 1.4], look: [0.0, 0.1, -0.2] },
    views: { det: [[-0.3, 0.5, 0.5], [-0.3, 0.12, -0.18]], rack: [[0.4, 0.3, 0.5], [0.42, 0.1, -0.01]], screen: [[0.04, 0.3, 0.1], [0.04, 0.2, -0.52]], bench: [[0.0, 0.95, 1.4], [0.0, 0.1, -0.2]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A cosmic-ray muon that stops in the scintillator flashes it once on entering; when it decays, the electron makes a second flash. The delay between the two flashes follows an exponential with the muon’s mean life. A time-to-amplitude converter measures every delay and a histogram builds up over days.',
      formula: 'N(t) = N₀ e^(−t/τ) + floor',
      formulaNote: 'ln(N − floor) against t is a straight line of slope −1/τ',
      more: ['The flat floor is made of chance coincidences: an unrelated start and stop pulse, equally likely at any delay. It is measured from the late bins, where no decays are left.',
        'A positive muon always decays, with the free lifetime 2.197 µs. A negative muon stopping in carbon can instead be captured by the nucleus, so its life in the material is shorter and part of it never gives a decay electron.',
        'The histogram is the sum of two exponentials. A single-exponential fit gives an apparent life a few per cent below 2.197 µs: the difference is the capture effect.'],
      precautions: 'No radioactive source: cosmic rays only. Switch the photomultiplier high voltage on only with the tube bases closed; stand clear of the exposed base pins.' },
    book: { title: 'Expt. — Mean life of cosmic-ray muons', lines: ['Aim: mean life of stopped muons; capture effect.', 'Detector: ' + SAMPLE, 'Blocks of ' + p.h + ' h; bins ' + p.dt + ' µs from ' + p.T0 + ' µs', 'N − floor = N₀ e^(−t/τ)'],
      columns: [{ label: 't (µs)', get: function (r) { return r.tc.toFixed(1); } }, { label: 'Counts', get: function (r) { return r.N; } }, { label: 'N − floor', get: function (r) { return r.net.toFixed(1); } },
        { label: 'ln(N − floor)', get: function (r) { return r.net > 0 ? Math.log(r.net).toFixed(3) : ''; } }] },
    graph: { x: function (r) { return r.tc; }, y: function (r) { return r.net > 0 ? Math.log(r.net) : NaN; }, xlabel: 'delay t (µs)', ylabel: 'ln (N − floor)',
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.05,
    resultNote: 'The weighted straight-line fit on the logarithm gives each bin the weight of its counts: the late, sparse bins count for less.',
    chips: ['Why does a mu- live shorter?', 'What is the floor?', 'Why take data for days?', 'Check my fit', 'Why plot the logarithm?'],
    viva: [['The delay between the two flashes follows', ['An exponential with the muon mean life', 'A Gaussian', 'A straight line'], 0, 'Decay is random with a constant chance per unit time.'],
      ['The flat floor of the histogram is from', ['Chance coincidences', 'Muons that never decay', 'Detector dead time'], 0, 'Unrelated pulses fall at any delay with equal probability.'],
      ['Capture of mu- by carbon makes the measured life', ['Shorter than the free value', 'Longer', 'Exactly the free value'], 0, 'Capture is an extra way for the muon to disappear.']],
    askState: function () {
      return { experiment: 'mean life of stopped cosmic-ray muons', detector: SAMPLE, high_voltage_on: st.hv, converter_on: st.tac, blocks_taken: st.blocks, hours: st.hours,
        decays: total(st.hist), floor_per_bin: st.floor, fitted_mean_life_us: st.fit ? +st.fit.tau.toFixed(3) : null };
    },
    steps: [
      { id: 'on', title: 'Switch on', view: 'rack', render: function (u) {
          u.h2('Switch on the electronics');
          u.p('Detector: ' + SAMPLE + '. Switch on the photomultiplier high voltage and then the time-to-amplitude converter.');
          u.task('High voltage', st.hv, st.hv ? 'On' : 'Off').add(u.button(st.hv ? 'Switch HV off' : 'Switch HV on', function () { S.focus('rack'); sw(bHv, 'hv'); }, !st.hv, S.hand.busy));
          u.task('Time-to-amplitude converter', st.tac, st.tac ? 'On' : 'Off').add(u.button(st.tac ? 'Switch converter off' : 'Switch converter on', function () { sw(bTac, 'tac'); }, !st.tac && st.hv, S.hand.busy));
          u.next('Next: take data', st.hv && st.tac);
        },
        ok: function () { return st.hv && st.tac; },
        auto: function () { return (st.hv ? Promise.resolve() : sw(bHv, 'hv')).then(function () { return st.tac ? null : sw(bTac, 'tac'); }); } },
      { id: 'data', title: 'Take data', view: 'screen', render: function (u) {
          u.h2('Take data in blocks of ' + p.h + ' hours');
          u.p('Each press of RUN adds ' + p.h + ' hours to the histogram. Take at least ' + NEED + ' blocks (three days): the decay curve is only clear with thousands of events.');
          u.row(u.button('Run a block (' + p.h + ' h)', function () { block(); }, true, S.hand.busy || st.running), u.button('Clear', function () { clearAll(); }, false, S.hand.busy || st.running));
          u.live(function () { return st.blocks + ' blocks  ·  ' + st.hours.toFixed(0) + ' h  ·  ' + total(st.hist) + ' decays'; });
          u.next('Next: analyse', st.blocks >= NEED);
        },
        ok: function () { return st.blocks >= NEED; },
        auto: function () { var ch = Promise.resolve(), i; for (i = 0; i < NEED; i++) ch = ch.then(function () { return block(); }); return ch; } },
      { id: 'fit', title: 'Floor and fit', view: 'screen', render: function (u) {
          u.h2('Subtract the floor and fit the decay');
          u.p('The last ' + Math.round(p.nbg) + ' bins hold no decays: their mean is the floor. Subtract it, write the bins up to ' + p.tfit + ' µs in the book, and fit a straight line to the logarithm.');
          u.task('1. Floor', st.floor !== null, st.floor !== null ? st.floor.toFixed(2) + ' per bin' : 'Not found').add(u.button('Find the floor', function () { findFloor(); }, st.floor === null, false));
          u.task('2. Histogram in the book', st.booked, st.booked ? 'Done' : 'Not yet').add(u.button('Write the bins in the book', function () { writeBook(); }, st.floor !== null && !st.booked, st.booked));
          u.task('3. Fit', !!st.fit, st.fit ? 'τ = ' + st.fit.tau.toFixed(3) + ' µs' : 'Not fitted').add(u.button('Fit the decay', function () { doFit(); }, st.booked && !st.fit, !st.booked));
          u.h3('Observation table'); u.table();
          u.next('Next: the result', !!st.fit);
        },
        ok: function () { return !!st.fit; },
        auto: function () { findFloor(); writeBook(); doFit(); return Promise.resolve(); } }
    ],
    tick: function (dt) {
      showD(String(total(shown()))); showH(String(Math.round(st.hours + (st.running ? p.h * st.prog : 0))));
      lampM[0].emissiveIntensity = st.hv ? 1.5 : 0; lampM[1].emissiveIntensity = st.tac ? 1.5 : 0;
      scM.emissiveIntensity = st.running ? 0.35 + 0.35 * Math.sin(performance.now() / 90) : 0;
      hudH.set(st.hours.toFixed(0) + ' h'); hudN.set(String(total(st.hist))); hudT.set(st.fit ? st.fit.tau.toFixed(3) + ' µs' : '—');
      if (st.running) paint(false);
    }
  };
});
