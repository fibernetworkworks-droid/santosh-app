/* Prayogshala studio module: 21 cm DATA BENCH (PhD radio astronomy).
   A data workstation with a monitor that shows, live, a SIMULATED 21 cm spectrum of the Galactic plane, and an
   antenna pointing panel. The spectrometer reports frequency channels; the student converts them to velocity,
   corrects them to the local standard of rest with the observatory's logged Doppler correction, reads the terminal
   velocity of the gas at the tangent point at five Galactic longitudes, and builds the rotation curve. The spectra
   are generated from a stated model of the Galaxy with seeded noise: they are NOT a survey of the real sky, and
   the screen, the log card and the title say so.
   Physics: the `ph3_hi` kernel of packs/ph3_nuc.js. */
HoolaStudio.define('ph3-hi21', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.ph3_hi, assign = HK.assign;
  var p = HK.paramsFor('ph3_hi', S.lab.params);
  var LS = KN.LS, F0 = KN.F0, NCH = Math.round(p.nch), SAMPLE = 'SIMULATED Galactic-plane pointings (b = 0)';
  function vcFor(l) { return p.vc - 0.2 * (l - 40); }
  var st = { l: 40, spec: {}, axis: 0, edge: {}, running: false, rowsDone: {} };
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

  // ================================================================ workstation
  var scr = makeScreen(0.0, -0.46, 0, 0.66, 0.40);
  var kb = new T.Group(); S.scene.add(kb); kb.position.set(0.0, 0.0, -0.02);
  var kbody = S.rounded(0.36, 0.14, 0.014, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 })); kbody.rotation.x = -Math.PI / 2; kbody.position.y = 0.011; kb.add(kbody);
  var ktex = S.canvasTex(720, 280, function (x, w, h) { x.fillStyle = '#d7d3c9'; x.fillRect(0, 0, w, h); x.fillStyle = '#b9b5ab'; for (var r = 0; r < 4; r++) for (var c = 0; c < 14; c++) x.fillRect(16 + c * 49, 108 + r * 42, 42, 34); });
  var kplane = new T.Mesh(new T.PlaneGeometry(0.35, 0.136), new T.MeshStandardMaterial({ map: ktex, roughness: 0.6 })); kplane.rotation.x = -Math.PI / 2; kplane.position.y = 0.0185; kb.add(kplane);
  var FK = ['INTEGRATE', 'AXIS', 'EDGE'], keys = [];
  FK.forEach(function (n, i) {
    var k = S.rounded(0.08, 0.03, 0.008, 0.004, new T.MeshStandardMaterial({ color: 0x2f3a49, roughness: 0.5 })); k.rotation.x = -Math.PI / 2; k.position.set(-0.11 + i * 0.11, 0.0205, -0.04); kb.add(k); keys.push(k);
    var lb = S.label('F' + (i + 1) + '  ' + n, { w: 0.075, ratio: 0.2, color: '#f1efe8' }); lb.rotation.x = -Math.PI / 2; lb.position.set(-0.11 + i * 0.11, 0.0252, -0.04); kb.add(lb);
  });
  S.contact(0.4, 0.18, 0.0, -0.02, 0.5);
  var pointP = panel(0.26, 0.13, 0.18, function (x, w, h, X, Y, k) {
    x.fillStyle = '#f1efe8'; x.textAlign = 'left'; x.font = '700 ' + Math.round(0.0095 * k) + 'px "Public Sans", sans-serif'; x.fillText('ANTENNA POINTING', X(-0.115), Y(0.05));
    x.font = '700 ' + Math.round(0.0078 * k) + 'px "Public Sans", sans-serif'; x.fillText('GALACTIC LONGITUDE (deg)', X(-0.115), Y(0.012)); x.fillText('b = 0° (the plane)', X(-0.115), Y(-0.05));
    x.textAlign = 'center'; var i, th, R = 0.027;
    for (i = 0; i < LS.length; i++) { th = (225 - 270 * (LS[i] - 20) / 60) * Math.PI / 180; x.strokeStyle = '#f1efe8'; x.lineWidth = 4; x.beginPath(); x.moveTo(X(0.072 + Math.cos(th) * (R + 0.002)), Y(-0.005 + Math.sin(th) * (R + 0.002))); x.lineTo(X(0.072 + Math.cos(th) * (R + 0.011)), Y(-0.005 + Math.sin(th) * (R + 0.011))); x.stroke();
      x.font = '600 ' + Math.round(0.0062 * k) + 'px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8'; x.fillText(String(LS[i]), X(0.072 + Math.cos(th) * (R + 0.02)), Y(-0.005 + Math.sin(th) * (R + 0.02)) + 4); }
  }, 0.42, 0.0, -0.2);
  var lLcd = makeLcd(pointP, -0.06, -0.01, 0.1, 0.034, 3), pk = makeKnob(pointP, 0.072, -0.005);
  function pRot(l) { return (225 - 270 * (l - 20) / 60) * Math.PI / 180 - Math.PI / 2; }
  pk.rotation.z = pRot(40);
  var card = new T.Group(); S.scene.add(card); card.position.set(-0.43, 0, -0.2); card.rotation.y = 0.35;
  var ctex = S.canvasTex(600, 800, function (x, w, h) {
    x.fillStyle = '#f6f3ea'; x.fillRect(0, 0, w, h); x.fillStyle = '#b8322a'; x.fillRect(0, 0, w, 90); x.fillStyle = '#fff'; x.font = '700 38px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText('SIMULATED DATA', w / 2, 60);
    x.fillStyle = '#1b1b1b'; x.textAlign = 'left'; x.font = '700 32px "Public Sans", sans-serif'; x.fillText('OBSERVING LOG', 36, 145);
    x.font = '500 25px "Public Sans", sans-serif'; var L = ['Doppler correction to the', 'local standard of rest:'];
    LS.forEach(function (l) { L.push('  l = ' + l + '°     ' + (vcFor(l) >= 0 ? '+' : '') + vcFor(l).toFixed(1) + ' km/s'); });
    L = L.concat(['', 'f0 = 1420.405752 MHz', 'band ' + (p.bw / 1e6).toFixed(1) + ' MHz, ' + NCH + ' channels', 'R0 = ' + p.R0 + ' kpc (IAU 1985)', 'Θ0 = ' + p.Th0 + ' km/s (IAU 1985)', 'line width σ = ' + p.sv + ' km/s', 'edge correction: 0.63 σ', '', 'Generated from a model.', 'Not a survey of the sky.']);
    L.forEach(function (t, i) { x.fillText(t, 36, 190 + i * 33); }); });
  var cardM = S.mesh(new T.BoxGeometry(0.15, 0.2, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: ctex, roughness: 0.6 }), M.grey]); cardM.position.set(0, 0.1, 0); cardM.rotation.x = -0.18; card.add(cardM);
  var cstand = S.mesh(new T.BoxGeometry(0.15, 0.01, 0.05), M.iron); cstand.position.set(0, 0.005, 0.03); card.add(cstand);
  var hudL = S.hudCard('Longitude'), hudV = S.hudCard('Terminal velocity'), hudT = S.hudCard('Circular speed');
  S.addApparatus('screen', scr.g, 'Data monitor', 'Shows the SIMULATED 21 cm spectrum as you work on it: first by channel, then frequency, velocity and velocity relative to the local standard of rest.');
  S.addApparatus('kb', kb, 'Keyboard with function keys', 'F1 integrates a spectrum at the pointing, F2 steps the axis, F3 finds the edge of the emission.');
  S.addApparatus('point', pointP.g, 'Antenna pointing', 'Sets the Galactic longitude of the line of sight; the antenna stays in the plane of the Galaxy.');
  S.addApparatus('card', card, 'Observing log', 'The logged Doppler correction for each pointing (Earth’s orbit and the Sun’s motion), and the standard constants. The data are simulated.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ================================================================ spectrum maths
  function q() { return assign(p, { l: st.l, vc: vcFor(st.l) }); }
  var AX = ['channel', 'frequency (MHz)', 'velocity, as observed (km/s)', 'velocity relative to the LSR (km/s)'];
  function xOf(i, qq) {
    var f = KN.freq(qq, i), v = C0 * (F0 - f) / F0 / 1000;
    return st.axis === 0 ? i + 0.5 : (st.axis === 1 ? f / 1e6 : (st.axis === 2 ? v : v + qq.vc));
  }
  var C0 = 2.99792458e8;
  var lastPaint = 0;
  function paint(force) {
    var now = performance.now(); if (!force && now - lastPaint < 90) return; lastPaint = now;
    scr.tex.draw(function (x, w, h) {
      x.fillStyle = '#0d1a14'; x.fillRect(0, 0, w, h);
      x.fillStyle = '#b8322a'; x.fillRect(0, 0, w, h * 0.075); x.fillStyle = '#fff'; x.font = '700 ' + Math.round(h * 0.045) + 'px "JetBrains Mono", monospace'; x.textAlign = 'center';
      x.fillText('SIMULATED DATA — not a survey of the real sky', w / 2, h * 0.055);
      var qq = q(), sp = st.spec[st.l], i, b1 = { l: 100, r: w - 30, t: h * 0.14, b: h * 0.58, ly: h * 0.66 };
      if (sp) {
        var xs = [], mn = 1e30, mx = -1e30, ymx = 1, ymn = 0; for (i = 0; i < NCH; i++) { var xv = xOf(i, qq); xs.push(xv); if (xv < mn) mn = xv; if (xv > mx) mx = xv; if (sp.tb[i] > ymx) ymx = sp.tb[i]; if (sp.tb[i] < ymn) ymn = sp.tb[i]; }
        var fr = plotFrame(x, w, h, b1, mn, mx, ymn * 1.1 - 0.5, ymx * 1.12, AX[st.axis], 'brightness temperature (K)', 6, 4, function (v) { return st.axis === 1 ? v.toFixed(2) : String(Math.round(v)); }, function (v) { return v.toFixed(0); });
        x.strokeStyle = '#6dffa4'; x.lineWidth = 1.6; x.beginPath(); for (i = 0; i < NCH; i++) { var X = fr.X(xs[i]), Y = fr.Y(sp.tb[i]); if (i) x.lineTo(X, Y); else x.moveTo(X, Y); } x.stroke();
        x.fillStyle = '#c9f5dc'; x.textAlign = 'left'; x.font = '600 ' + Math.round(h * 0.04) + 'px "JetBrains Mono", monospace'; x.fillText('l = ' + st.l + '°   b = 0°   rms ' + p.sig.toFixed(2) + ' K', b1.l + 8, b1.t - 10);
        var e = st.edge[st.l]; if (e && st.axis === 3) { x.strokeStyle = '#ffd24a'; x.setLineDash([6, 5]); x.lineWidth = 2; x.beginPath(); x.moveTo(fr.X(e.vedge), b1.t); x.lineTo(fr.X(e.vedge), b1.b); x.stroke(); x.setLineDash([]);
          x.fillStyle = '#ffd24a'; x.fillText('half-peak edge ' + e.vedge.toFixed(1) + ' km/s;  v_t = ' + e.vt.toFixed(1) + ' km/s', fr.X(e.vedge) - 560, b1.t + h * 0.06); }
      } else { plotFrame(x, w, h, b1, 0, NCH, 0, 10, 'channel', 'brightness temperature (K)', 6, 4); x.fillStyle = '#6aa88a'; x.textAlign = 'center'; x.font = '600 ' + Math.round(h * 0.04) + 'px "JetBrains Mono", monospace'; x.fillText('point the antenna, then press F1 to integrate', (b1.l + b1.r) / 2, (b1.t + b1.b) / 2); }
      // rotation curve being built
      var b2 = { l: 100, r: w - 30, t: h * 0.76, b: h * 0.9, ly: h * 0.985 }, rr = S.rows;
      var fr2 = plotFrame(x, w, h, b2, 3, 9, 150, 250, 'R (kpc)', 'Θ (km/s)', 6, 2, function (v) { return v.toFixed(0); }, function (v) { return v.toFixed(0); });
      x.fillStyle = '#ffd24a'; rr.forEach(function (r) { x.beginPath(); x.arc(fr2.X(r.R), fr2.Y(r.Th), 7, 0, 7); x.fill(); });
    });
  }
  paint(true);

  // ================================================================ actions
  function press(i) { return S.hand.tap(keys[i], 'top'); }
  function setL(l) {
    if (busy()) return Promise.resolve();
    if (LS.indexOf(l) < 0) { S.say('Point at one of 30, 40, 50, 60 or 70 degrees.'); return Promise.resolve(); }
    if (l === st.l) return Promise.resolve();
    var l0 = st.l, pt = wpt(pointP.g, 0.072, 0.004 + pointP.H / 2 - 0.005, pointP.FZ + 0.024);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { pk.rotation.z = pRot(l0 + (l - l0) * k); S.hand.group.rotation.y = -(pRot(l) - pRot(l0)) * k * 0.3; }, { mode: 'front', ms: 450, reachMs: 600 })
      .then(function () { st.l = l; st.axis = st.spec[l] ? 3 : 0; pk.rotation.z = pRot(l); S.say('Antenna at l = ' + l + '°.'); S.render(); paint(true); });
  }
  function integrate() {
    if (busy()) return Promise.resolve(false);
    if (st.spec[st.l]) { S.say('Already integrated at this longitude.'); return Promise.resolve(true); }
    return press(0).then(function () { var qq = q(); st.spec[st.l] = { tb: KN.spectrum(qq, true) }; st.axis = 0; S.say('Integrated at l = ' + st.l + '°. The spectrometer reports channels: convert them to frequency and then to velocity.'); S.render(); paint(true); return true; });
  }
  function axisTo(a) {
    if (busy()) return Promise.resolve(false);
    if (!st.spec[st.l]) { S.say('Integrate a spectrum first (F1).'); return Promise.resolve(false); }
    if (a === st.axis) return Promise.resolve(true);
    if (a > st.axis + 1) { S.say('Go through the steps in order: channel, frequency, velocity, then the LSR correction.'); return Promise.resolve(false); }
    return press(1).then(function () { st.axis = a; S.say(a === 1 ? 'Channel → frequency: f = f₀ + band/2 − channel × width.' : (a === 2 ? 'Frequency → velocity: v = c (f₀ − f) / f₀.' : 'Velocity corrected to the LSR with the logged correction of ' + (vcFor(st.l) >= 0 ? '+' : '') + vcFor(st.l).toFixed(1) + ' km/s.')); S.render(); paint(true); return true; });
  }
  function edge() {
    if (busy()) return Promise.resolve(false);
    if (!st.spec[st.l]) { S.say('Integrate a spectrum first (F1).'); return Promise.resolve(false); }
    if (st.axis < 3) { S.say('Convert to velocity relative to the LSR first (F2).'); return Promise.resolve(false); }
    if (st.edge[st.l]) { S.say('The edge is already found here.'); return Promise.resolve(true); }
    return press(2).then(function () {
      var qq = q(), tb = st.spec[st.l].tb, vt = KN.edge(qq, tb), sl = Math.sin(st.l * Math.PI / 180);
      st.edge[st.l] = { vt: vt, vedge: vt + KN.EDGE_K * p.sv, R: p.R0 * sl, Th: vt + p.Th0 * sl, nh: KN.nh(qq, tb) };
      S.say('Terminal velocity v_t = ' + vt.toFixed(1) + ' km/s at l = ' + st.l + '°.'); S.render(); paint(true); return true; });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    var e = st.edge[st.l]; if (!e) { S.say('Find the edge first (F3).'); return false; }
    if (S.rows.some(function (r) { return r.l === st.l; })) { S.say('That longitude is already written down.'); return false; }
    S.addRow({ l: st.l, vc: vcFor(st.l), vt: e.vt, R: e.R, Th: e.Th }); S.say('Written in your record book: R = ' + e.R.toFixed(2) + ' kpc, Θ = ' + e.Th.toFixed(0) + ' km/s.'); paint(true); return true;
  }
  function result() {
    if (S.rows.length < LS.length) return null;
    var th = S.rows.reduce(function (a, r) { return a + r.Th; }, 0) / S.rows.length, e40 = st.edge[40];
    return { label: 'Mean circular speed at the five tangent radii', value: th, unit: 'km/s', digits: 1, truth: HK.TEXTBOOK.ph3_hi_theta(p),
      note: 'Θ = v_t + Θ0 sin l at R = R0 sin l. The five points rise from ' + S.rows.slice().sort(function (a, b) { return a.l - b.l; })[0].Th.toFixed(0) + ' km/s at R = ' + S.rows.slice().sort(function (a, b) { return a.l - b.l; })[0].R.toFixed(1) + ' kpc and then level off: the curve is nearly flat in the outer disc. ' +
        (e40 ? 'Hydrogen column density along l = 40°: N_H = 1.823e18 Σ T dv = ' + e40.nh.toExponential(2) + ' cm⁻². ' : '') + 'SIMULATED DATA.' };
  }

  return {
    camera: { pos: [0.0, 0.9, 1.2], look: [0.0, 0.1, -0.2] },
    views: { screen: [[0.0, 0.32, 0.45], [0.0, 0.22, -0.46]], kb: [[0.0, 0.3, 0.3], [0.0, 0.02, -0.03]], point: [[0.4, 0.25, 0.55], [0.42, 0.07, 0.09]], card: [[-0.3, 0.25, 0.1], [-0.43, 0.1, -0.2]], bench: [[0.0, 0.9, 1.2], [0.0, 0.1, -0.2]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'Hydrogen atoms emit a line at 1420.405752 MHz when the electron’s spin flips relative to the proton’s. Along the Galactic plane at longitude l in the first quadrant, gas on circular orbits shows a radial velocity that grows with distance up to the tangent point, where the line of sight just touches an orbit of radius R = R0 sin l, and falls beyond it. The highest velocity in the spectrum is that of the gas at the tangent point.',
      formula: 'v_t = Θ(R) − Θ₀ sin l,   R = R₀ sin l',
      formulaNote: 'so Θ(R) = v_t + Θ₀ sin l; radio velocity v = c (f₀ − f) / f₀',
      more: ['The spectrometer measures frequencies in the antenna’s own frame; the observatory logs the Doppler correction (Earth’s orbit, the Sun’s motion) that brings the velocities to the local standard of rest.',
        'The edge of the emission is smoothed by the gas’s own velocity spread (σ ≈ 6 km/s): the half-peak point lies 0.63 σ beyond the true terminal velocity in this model.',
        'The line is thin, so the column density is N_H = 1.823×10¹⁸ ∫T_b dv (cm⁻², T in K, v in km/s). THE SPECTRA ARE SIMULATED from a stated model of the Galaxy; they are not a survey.'],
      precautions: 'No hazard. A radio receiver is passive. Read the red banner and the observing log: the data are a simulation.' },
    book: { title: 'Expt. — 21 cm line and the Galactic rotation curve (SIMULATED)', lines: ['Data: ' + SAMPLE, 'R₀ = ' + p.R0 + ' kpc, Θ₀ = ' + p.Th0 + ' km/s (IAU 1985)', 'v = c(f₀ − f)/f₀;  v_LSR = v + correction', 'R = R₀ sin l;  Θ = v_t + Θ₀ sin l'],
      columns: [{ label: 'l (°)', get: function (r) { return r.l; } }, { label: 'LSR corr', get: function (r) { return r.vc.toFixed(1); } }, { label: 'v_t (km/s)', get: function (r) { return r.vt.toFixed(1); } },
        { label: 'R (kpc)', get: function (r) { return r.R.toFixed(2); } }, { label: 'Θ (km/s)', get: function (r) { return r.Th.toFixed(0); } }] },
    graph: { x: function (r) { return r.R; }, y: function (r) { return r.Th; }, xlabel: 'R (kpc)', ylabel: 'Θ (km/s)', x0: 0, y0: 0 },
    result: result,
    tol: 0.03,
    resultNote: 'A flat rotation curve in the outer disc means the mass inside radius R keeps growing in proportion to R: more mass than the stars and gas we see.',
    chips: ['Why the tangent point?', 'What is the LSR correction?', 'How is the edge found?', 'Why is this simulated?', 'What does a flat curve mean?'],
    viva: [['The terminal velocity is read at the tangent point because there', ['The line of sight runs along an orbit and the radial velocity is largest', 'The gas is densest', 'The Sun is nearest'], 0, 'The radial velocity of circular motion peaks where the line of sight is tangent.'],
      ['The 21 cm line comes from', ['The spin flip of the electron in hydrogen', 'An electronic transition from n = 2', 'Molecular rotation'], 0, 'The hyperfine splitting of the ground state.'],
      ['A flat rotation curve at large R means', ['Mass keeps growing in proportion to R', 'No mass beyond the Sun', 'The gas has stopped'], 0, 'Θ² = G M(<R)/R, so constant Θ needs M ∝ R.']],
    askState: function () {
      return { experiment: '21 cm line and Galactic rotation curve (SIMULATED DATA)', longitude_deg: st.l, spectra_taken: Object.keys(st.spec).length, axis: AX[st.axis], edges_found: Object.keys(st.edge).length, rows: S.rows.length };
    },
    steps: [
      { id: 'point', title: 'Point and integrate', view: 'point', render: function (u) {
          u.h2('Point the antenna and integrate');
          u.p('These are SIMULATED spectra of the Galactic plane. Set a longitude, then press F1 to integrate. Do it at 30, 40, 50, 60 and 70 degrees; the next steps are done at each one.');
          u.row.apply(u, LS.map(function (l) { return u.button(l + '°', function () { S.focus('point'); setL(l); }, st.l === l, S.hand.busy); }));
          u.task('Spectrum at l = ' + st.l + '°', !!st.spec[st.l], st.spec[st.l] ? 'Integrated' : 'Not yet').add(u.button('Press F1 (integrate)', function () { S.focus('kb'); integrate(); }, !st.spec[st.l], !!st.spec[st.l] || S.hand.busy));
          u.live(function () { return 'Log: Doppler correction to the LSR at l = ' + st.l + '° is ' + (vcFor(st.l) >= 0 ? '+' : '') + vcFor(st.l).toFixed(1) + ' km/s'; });
          u.next('Next: velocity axis and edge', !!st.spec[st.l]);
        }, ok: function () { return !!st.spec[st.l]; }, auto: function () { return integrate(); } },
      { id: 'edge', title: 'Velocity and edge', view: 'screen', render: function (u) {
          u.h2('Convert to velocity, then find the edge of the emission');
          u.p('F2 steps the axis: channel → frequency → velocity → velocity relative to the LSR (the logged correction is added). F3 finds the high-velocity edge of the emission and corrects it to the terminal velocity.');
          u.row(u.button('Frequency', function () { axisTo(1); }, st.axis === 0, S.hand.busy || !st.spec[st.l]), u.button('Velocity', function () { axisTo(2); }, st.axis === 1, S.hand.busy || !st.spec[st.l]), u.button('LSR', function () { axisTo(3); }, st.axis === 2, S.hand.busy || !st.spec[st.l]));
          u.task('Edge at l = ' + st.l + '°', !!st.edge[st.l], st.edge[st.l] ? 'v_t = ' + st.edge[st.l].vt.toFixed(1) + ' km/s' : 'Not found').add(u.button('Press F3 (edge)', function () { edge(); }, !st.edge[st.l], st.axis < 3 || !!st.edge[st.l] || S.hand.busy))
            .add(u.button('Write it down', function () { record(); }, false, !st.edge[st.l] || S.rows.some(function (r) { return r.l === st.l; })));
          u.p('Longitude: ' + LS.map(function (l) { return (S.rows.some(function (r) { return r.l === l; }) ? '✓ ' : '') + l + '°'; }).join('  ·  '));
          u.row.apply(u, LS.map(function (l) { return u.button(l + '°', function () { setL(l); }, st.l === l, S.hand.busy); }));
          u.h3('Observation table'); u.table();
          u.next('Next: the result', S.rows.length >= LS.length);
        }, ok: function () { return S.rows.length >= LS.length; },
        auto: function () {
          var ch = Promise.resolve();
          LS.forEach(function (l) { ch = ch.then(function () { return setL(l); }).then(function () { return integrate(); }).then(function () { return axisTo(1); }).then(function () { return axisTo(2); }).then(function () { return axisTo(3); }).then(function () { return edge(); }).then(function () { record(); }); });
          return ch;
        } }
    ],
    tick: function () {
      lLcd(String(st.l)); hudL.set(st.l + '°'); var e = st.edge[st.l]; hudV.set(e ? e.vt.toFixed(1) + ' km/s' : '—'); hudT.set(e ? e.Th.toFixed(0) + ' km/s' : '—');
    }
  };
});
