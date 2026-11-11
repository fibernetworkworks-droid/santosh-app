/* Prayogshala studio module: LIGHT-CURVE DATA BENCH (PhD astrophysical data analysis).
   A data workstation with a monitor that shows, live, a SIMULATED light curve, the box-least-squares periodogram
   and the folded transit. The light curve is generated from a stated model (a planet on a circular orbit, a
   limb-darkened star, seeded Gaussian noise): it is NOT an observation of any real star, and the screen, the
   target card and the title say so. The student searches for the period, folds, measures the depth and the
   duration, and deduces the radius ratio, the impact parameter and the inclination.
   Physics: the `ph3_transit` kernel of packs/ph3_nuc.js. */
HoolaStudio.define('ph3-transit', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.ph3_transit, assign = HK.assign;
  var p = HK.paramsFor('ph3_transit', S.lab.params);
  var V_ = S.lab.variant || {}, CADMIN = p.cad * 1440, NPT = Math.floor(p.span / p.cad);
  var SAMPLE = V_.sample || 'SIMULATED TESS-like target: bright star, 10-minute cadence, 27 days';
  var ARS = KN.ars(p);
  var st = { t: null, f: null, pg: null, pgShow: 0, P: null, an: null, fold: null, running: false, rowsDone: {} };
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
  var desk = new T.Group(); S.scene.add(desk);
  var scr = makeScreen(0.0, -0.46, 0, 0.66, 0.40);
  var kb = new T.Group(); S.scene.add(kb); kb.position.set(0.0, 0.0, -0.02);
  var kbody = S.rounded(0.36, 0.14, 0.014, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 })); kbody.rotation.x = -Math.PI / 2; kbody.position.y = 0.011; kb.add(kbody);
  var ktex = S.canvasTex(720, 280, function (x, w, h) { x.fillStyle = '#d7d3c9'; x.fillRect(0, 0, w, h); x.fillStyle = '#b9b5ab';
    for (var r = 0; r < 4; r++) for (var c = 0; c < 14; c++) x.fillRect(16 + c * 49, 108 + r * 42, 42, 34); });
  var kplane = new T.Mesh(new T.PlaneGeometry(0.35, 0.136), new T.MeshStandardMaterial({ map: ktex, roughness: 0.6 })); kplane.rotation.x = -Math.PI / 2; kplane.position.y = 0.0185; kb.add(kplane);
  var FK = ['LOAD', 'PERIOD', 'FOLD', 'MEASURE'], keys = [];
  FK.forEach(function (n, i) {
    var k = S.rounded(0.062, 0.03, 0.008, 0.004, new T.MeshStandardMaterial({ color: 0x2f3a49, roughness: 0.5 })); k.rotation.x = -Math.PI / 2; k.position.set(-0.133 + i * 0.0885, 0.0205, -0.04); kb.add(k); keys.push(k);
    var lb = S.label('F' + (i + 1) + '  ' + n, { w: 0.058, ratio: 0.22, color: '#f1efe8' }); lb.rotation.x = -Math.PI / 2; lb.position.set(-0.133 + i * 0.0885, 0.0252, -0.04); kb.add(lb);
  });
  S.contact(0.4, 0.18, 0.0, -0.02, 0.5);
  var card = new T.Group(); S.scene.add(card); card.position.set(-0.42, 0, -0.2); card.rotation.y = 0.35;
  var ctex = S.canvasTex(600, 800, function (x, w, h) {
    x.fillStyle = '#f6f3ea'; x.fillRect(0, 0, w, h); x.fillStyle = '#b8322a'; x.fillRect(0, 0, w, 90); x.fillStyle = '#fff'; x.font = '700 38px "Public Sans", sans-serif'; x.textAlign = 'center'; x.fillText('SIMULATED DATA', w / 2, 60);
    x.fillStyle = '#1b1b1b'; x.textAlign = 'left'; x.font = '700 34px "Public Sans", sans-serif'; x.fillText('TARGET CARD', 36, 150);
    x.font = '500 27px "Public Sans", sans-serif'; var L = [SAMPLE.replace('SIMULATED ', ''), '', 'cadence: ' + CADMIN.toFixed(1) + ' min', 'points: ' + NPT, 'span: ' + p.span + ' days', 'noise: ' + (p.sig * 1e6).toFixed(0) + ' ppm per point', '',
      'star mean density', '   ' + Math.round(p.rho) + ' kg/m³', 'limb darkening (linear)', '   u = ' + p.u.toFixed(2), '', 'a/Rs = (G ρ P² / 3π)^(1/3)', 'circular orbit', '',
      'Generated here from a model.', 'Not an observation of any star.'];
    L.forEach(function (t, i) { x.fillText(t, 36, 200 + i * 36); }); });
  var cardM = S.mesh(new T.BoxGeometry(0.15, 0.2, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: ctex, roughness: 0.6 }), M.grey]); cardM.position.set(0, 0.1, 0); cardM.rotation.x = -0.18; card.add(cardM);
  var cstand = S.mesh(new T.BoxGeometry(0.15, 0.01, 0.05), M.iron); cstand.position.set(0, 0.005, 0.03); card.add(cstand);
  var hudP = S.hudCard('Period'), hudD = S.hudCard('Depth'), hudK = S.hudCard('Rp / Rs');
  S.addApparatus('screen', scr.g, 'Data monitor', 'Shows the SIMULATED light curve, the periodogram and the folded transit as you work. Nothing on it is a real observation.');
  S.addApparatus('kb', kb, 'Keyboard with function keys', 'F1 loads the light curve, F2 searches for the period, F3 folds it, F4 measures the transit.');
  S.addApparatus('card', card, 'Target card', 'The properties the simulation gives you: the star’s density and limb darkening, the cadence and noise. They are the “catalogue values” of the simulated target.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ================================================================ monitor
  var lastPaint = 0;
  function paint(force) {
    var now = performance.now(); if (!force && now - lastPaint < 90) return; lastPaint = now;
    scr.tex.draw(function (x, w, h) {
      x.fillStyle = '#0d1a14'; x.fillRect(0, 0, w, h);
      x.fillStyle = '#b8322a'; x.fillRect(0, 0, w, h * 0.075); x.fillStyle = '#fff'; x.font = '700 ' + Math.round(h * 0.045) + 'px "JetBrains Mono", monospace'; x.textAlign = 'center';
      x.fillText('SIMULATED DATA — not an observation of any real star', w / 2, h * 0.055);
      var i, fr;
      // raw light curve
      var b1 = { l: 100, r: w - 30, t: h * 0.13, b: h * 0.43, ly: h * 0.5 };
      if (st.f) {
        var lo = 2, hi = 0; for (i = 0; i < st.f.length; i++) { if (st.f[i] < lo) lo = st.f[i]; if (st.f[i] > hi) hi = st.f[i]; } var pad = (hi - lo) * 0.08;
        fr = plotFrame(x, w, h, b1, 0, p.span, lo - pad, hi + pad, 'time (days)', 'flux', 6, 3, function (v) { return v.toFixed(0); }, function (v) { return v.toFixed(3); });
        x.fillStyle = '#6dffa4'; for (i = 0; i < st.f.length; i += 1) x.fillRect(fr.X(st.t[i]) - 1, fr.Y(st.f[i]) - 1, 2.4, 2.4);
        if (st.P) { x.strokeStyle = 'rgba(255,210,74,.5)'; x.lineWidth = 1; var tr = st.an ? st.an.t0 : null; if (tr !== null) for (var n = 0; tr + n * st.P < p.span; n++) { x.beginPath(); x.moveTo(fr.X(tr + n * st.P), b1.t); x.lineTo(fr.X(tr + n * st.P), b1.b); x.stroke(); } }
      } else { plotFrame(x, w, h, b1, 0, p.span, 0, 1, 'time (days)', 'flux', 6, 3); x.fillStyle = '#6aa88a'; x.textAlign = 'center'; x.font = '600 ' + Math.round(h * 0.04) + 'px "JetBrains Mono", monospace'; x.fillText('press F1 to load the light curve', (b1.l + b1.r) / 2, (b1.t + b1.b) / 2); }
      // periodogram
      var b2 = { l: 100, r: w * 0.5 - 20, t: h * 0.58, b: h * 0.86, ly: h * 0.93, lx: 20 };
      if (st.pg) {
        var n2 = Math.round(st.pgShow * st.pg.length), mx = 1e-12; for (i = 0; i < st.pg.length; i++) if (st.pg[i][1] > mx) mx = st.pg[i][1];
        fr = plotFrame(x, w, h, b2, 0.8, 14, 0, 1.1, 'trial period (days)', 'BLS power (relative)', 4, 3, function (v) { return v.toFixed(0); }, function (v) { return v.toFixed(1); });
        x.strokeStyle = '#6dffa4'; x.lineWidth = 1.6; x.beginPath(); for (i = 0; i < n2; i++) { var X = fr.X(st.pg[i][0]), Y = fr.Y(st.pg[i][1] / mx); if (i) x.lineTo(X, Y); else x.moveTo(X, Y); } x.stroke();
        if (st.P && st.pgShow >= 1) { x.strokeStyle = '#ffd24a'; x.setLineDash([5, 4]); x.beginPath(); x.moveTo(fr.X(st.P), b2.t); x.lineTo(fr.X(st.P), b2.b); x.stroke(); x.setLineDash([]); x.fillStyle = '#ffd24a'; x.textAlign = 'left'; x.fillText('P = ' + st.P.toFixed(4) + ' d', fr.X(st.P) + 10, b2.t + h * 0.05); }
      } else { plotFrame(x, w, h, b2, 0.8, 14, 0, 1, 'trial period (days)', 'BLS power', 4, 3); x.fillStyle = '#6aa88a'; x.textAlign = 'center'; x.font = '600 ' + Math.round(h * 0.034) + 'px "JetBrains Mono", monospace'; x.fillText('F2: period search', (b2.l + b2.r) / 2, (b2.t + b2.b) / 2); }
      // folded transit
      var b3 = { l: w * 0.5 + 90, r: w - 30, t: h * 0.58, b: h * 0.86, ly: h * 0.93, lx: w * 0.5 + 10 };
      if (st.fold && st.an) {
        var fd = st.fold, half = fd[fd.length - 1][0], ymin = 2, ymax = 0; for (i = 0; i < fd.length; i++) { if (fd[i][1] < ymin) ymin = fd[i][1]; if (fd[i][1] > ymax) ymax = fd[i][1]; }
        fr = plotFrame(x, w, h, b3, -half, half, ymin - 0.001, ymax + 0.001, 'days from mid-transit', 'flux', 4, 3, function (v) { return v.toFixed(2); }, function (v) { return v.toFixed(3); });
        x.fillStyle = '#6dffa4'; for (i = 0; i < fd.length; i++) if (fd[i][2] > 0) { x.beginPath(); x.arc(fr.X(fd[i][0]), fr.Y(fd[i][1]), 4, 0, 7); x.fill(); }
        if (st.an.done) { x.strokeStyle = '#ff8a5c'; x.lineWidth = 2; x.setLineDash([6, 4]); x.beginPath(); x.moveTo(fr.X(-half), fr.Y(1 - st.an.depth)); x.lineTo(fr.X(half), fr.Y(1 - st.an.depth)); x.stroke(); x.setLineDash([]);
          x.strokeStyle = '#ffd24a'; x.beginPath(); x.moveTo(fr.X(-st.an.dur / 2), b3.t); x.lineTo(fr.X(-st.an.dur / 2), b3.b); x.moveTo(fr.X(st.an.dur / 2), b3.t); x.lineTo(fr.X(st.an.dur / 2), b3.b); x.stroke();
          x.fillStyle = '#ffd24a'; x.textAlign = 'left'; x.fillText('depth ' + (st.an.depth * 100).toFixed(3) + ' %   T14 ' + (st.an.dur * 24).toFixed(2) + ' h', b3.l, b3.t - 8); }
      } else { plotFrame(x, w, h, b3, -0.3, 0.3, 0.98, 1.002, 'days from mid-transit', 'flux', 4, 3); x.fillStyle = '#6aa88a'; x.textAlign = 'center'; x.font = '600 ' + Math.round(h * 0.034) + 'px "JetBrains Mono", monospace'; x.fillText('F3: fold on the period', (b3.l + b3.r) / 2, (b3.t + b3.b) / 2); }
    });
  }
  paint(true);

  // ================================================================ actions
  function press(i) { return S.hand.tap(keys[i], 'top'); }
  function load() {
    if (busy()) return Promise.resolve(false);
    if (st.f) { S.say('The light curve is already loaded.'); return Promise.resolve(true); }
    return press(0).then(function () { st.t = KN.times(p); st.f = KN.curve(p, true); S.say('Light curve loaded: ' + st.f.length + ' points over ' + p.span + ' days. The dips are too small to see by eye.'); S.render(); paint(true); return true; });
  }
  function search() {
    if (busy()) return Promise.resolve(false);
    if (!st.f) { S.say('Load the light curve first (F1).'); return Promise.resolve(false); }
    if (st.P) { S.say('The period is already found.'); return Promise.resolve(true); }
    st.running = true;
    return press(1).then(function () {
      var c = KN.bls(st.t, st.f, 0.8, 14.0, 0.02), pk = c[0], i; for (i = 1; i < c.length; i++) if (c[i][1] > pk[1]) pk = c[i];
      st.pg = c; st.pgShow = 0;
      var P = KN.best_period(st.t, st.f);
      return S.tween(1100, function (u) { st.pgShow = u; }).then(function () { st.pgShow = 1; st.P = P; st.running = false;
        S.say('The tallest peak of the box least-squares search is at ' + P.toFixed(4) + ' days (refined on a finer grid).'); S.render(); paint(true); return true; });
    });
  }
  function fold() {
    if (busy()) return Promise.resolve(false);
    if (!st.P) { S.say('Find the period first (F2).'); return Promise.resolve(false); }
    return press(2).then(function () {
      var tref = KN.epoch(st.t, st.f, st.P); st.an = { t0: tref, done: false }; st.fold = KN.fold(st.t, st.f, st.P, tref, Math.min(0.5, 0.1 * st.P), 100);
      S.say('Folded on ' + st.P.toFixed(4) + ' days, mid-transit at day ' + tref.toFixed(3) + '. The transit stands out.'); S.render(); paint(true); return true; });
  }
  function measure() {
    if (busy()) return Promise.resolve(false);
    if (!st.fold) { S.say('Fold the light curve first (F3).'); return Promise.resolve(false); }
    if (st.an.done) { S.say('Already measured.'); return Promise.resolve(true); }
    return press(3).then(function () {
      var a = KN.analyse(p, st.t, st.f, st.P); a.done = true; st.an = a;
      S.say('Depth ' + (a.depth * 100).toFixed(3) + ' %, duration ' + (a.dur * 24).toFixed(2) + ' h, so Rp/Rs = ' + a.k.toFixed(4) + '.'); S.render(); paint(true); return true; });
  }
  function rec(q, v, unit, label) {
    if (st.rowsDone[q]) { S.say('That is already written down.'); return false; }
    st.rowsDone[q] = true; S.addRow({ q: q, label: label, v: v, unit: unit }); paint(true); return true;
  }
  function recordPeriod() { if (!st.P) { S.say('Find the period first.'); return false; } return rec('P', st.P, 'd', 'Orbital period'); }
  function recordMeasure() {
    if (!st.an || !st.an.done) { S.say('Press F4 to measure the transit first.'); return false; }
    var a = st.an; rec('dep', a.depth, '', 'Mid-transit depth'); rec('T14', a.dur * 24, 'h', 'Duration (first to last contact)'); rec('aRs', a.aRs, '', 'a/Rs from the star’s density');
    rec('b', a.b, '', 'Impact parameter'); rec('inc', a.inc, '°', 'Inclination'); return rec('k', a.k, '', 'Rp/Rs (limb-darkening corrected)');
  }
  function kRow() { return S.rows.filter(function (r) { return r.q === 'k'; })[0]; }
  function result() {
    var r = kRow(); if (!r || !isFinite(r.v)) return null;
    var a = st.an, itrue = Math.acos(p.b / ARS) * 180 / Math.PI;
    return { label: 'Planet-to-star radius ratio', value: r.v, unit: '', digits: 4, truth: p.k,
      note: 'Period ' + st.P.toFixed(4) + ' d (the simulation’s is ' + p.P + '), inclination ' + a.inc.toFixed(1) + '° (the simulation’s is ' + itrue.toFixed(1) + '°). The depth ' + (a.depth * 100).toFixed(3) + ' % is corrected for limb darkening with u = ' + p.u.toFixed(2) + ': Rp/Rs = √[depth (1 − u/3) / (1 − u(1 − μ))]. SIMULATED DATA.' };
  }

  return {
    camera: { pos: [0.0, 0.9, 1.2], look: [-0.02, 0.1, -0.2] },
    views: { screen: [[0.0, 0.32, 0.45], [0.0, 0.22, -0.46]], kb: [[0.0, 0.3, 0.3], [0.0, 0.02, -0.03]], card: [[-0.3, 0.25, 0.1], [-0.42, 0.1, -0.2]], bench: [[0.0, 0.9, 1.2], [-0.02, 0.1, -0.2]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'When a planet crosses the face of its star the light dips by the fraction of the disc that is hidden. A transit repeats with the orbital period, so a periodic search finds it even when each dip is buried in the noise. Folding on the period stacks the dips and shows the shape: depth, duration, ingress.',
      formula: 'δ ≈ (Rp/Rs)² · (1 − u(1 − μ)) / (1 − u/3),   μ = √(1 − b²)',
      formulaNote: 'u = linear limb darkening; b = impact parameter; cos i = b / (a/Rs); a/Rs = (G ρ P² / 3π)^(1/3)',
      more: ['A box least-squares search folds the light curve on every trial period and measures how well a box-shaped dip fits; the right period gives the deepest box.',
        'The duration from first to last contact is T₁₄ = (P/π) asin[√((1 + k)² − b²) / (a/Rs)]: a longer transit means a smaller impact parameter.',
        'THE DATA ARE SIMULATED: generated from a stated model with seeded noise. They are not an observation of any real star.'],
      precautions: 'Nothing to handle: it is a data analysis. Read the target card and the red banner: this is a simulation, and its planet is invented.' },
    book: { title: 'Expt. — Transit light curve (SIMULATED DATA)', lines: ['Target: ' + SAMPLE, 'Cadence ' + CADMIN.toFixed(1) + ' min, ' + NPT + ' points, noise ' + (p.sig * 1e6).toFixed(0) + ' ppm', 'ρ★ = ' + Math.round(p.rho) + ' kg/m³, u = ' + p.u.toFixed(2)],
      columns: [{ label: 'Quantity', get: function (r) { return r.label; } }, { label: 'Value', get: function (r) { return (r.q === 'P' ? r.v.toFixed(4) : (r.q === 'dep' ? (r.v * 100).toFixed(3) + ' %' : r.v.toFixed(r.q === 'k' ? 4 : 2))); } }, { label: 'Unit', get: function (r) { return r.unit; } }] },
    result: result,
    tol: 0.05,
    resultNote: 'The folded curve is the average of every transit: noise that hides each single dip averages away, so the depth is good to about one per cent.',
    chips: ['How does the period search work?', 'Why correct for limb darkening?', 'How is the inclination found?', 'Why is this simulated?', 'Check my depth'],
    viva: [['A planet one tenth of the star’s radius (centre of the disc, no limb darkening) dims the star by', ['1 %', '10 %', '0.1 %'], 0, '(Rp/Rs)² = 0.01.'],
      ['Folding on the wrong period', ['Smears the transit into a shallow dip', 'Makes the transit deeper', 'Does nothing'], 0, 'The transits no longer line up.'],
      ['A longer transit duration at the same period means', ['A smaller impact parameter', 'A smaller planet', 'A larger inclination angle error'], 0, 'The planet crosses nearer a diameter of the star.']],
    askState: function () {
      return { experiment: 'transit light curve (SIMULATED DATA)', target: SAMPLE, loaded: !!st.f, period_found_d: st.P ? +st.P.toFixed(4) : null, folded: !!st.fold,
        measured: st.an && st.an.done ? { depth: +st.an.depth.toFixed(5), duration_h: +(st.an.dur * 24).toFixed(2), k: +st.an.k.toFixed(4), inclination_deg: +st.an.inc.toFixed(2) } : null };
    },
    steps: [
      { id: 'load', title: 'Load the light curve', view: 'screen', render: function (u) {
          u.h2('Load the SIMULATED light curve');
          u.p('Read the target card: this is a simulated star with an invented planet. Press F1 to load its ' + NPT + ' points.');
          u.task('Light curve', !!st.f, st.f ? NPT + ' points loaded' : 'Not loaded').add(u.button('Press F1 (load)', function () { S.focus('kb'); load(); }, !st.f, st.f || S.hand.busy));
          u.next('Next: the period', !!st.f);
        }, ok: function () { return !!st.f; }, auto: function () { return load(); } },
      { id: 'period', title: 'Find the period', view: 'screen', render: function (u) {
          u.h2('Search for the period');
          u.p('F2 runs a box least-squares search over trial periods from 0.8 to 14 days. The highest peak of the periodogram is the orbital period.');
          u.task('Period', !!st.P, st.P ? st.P.toFixed(4) + ' days' : 'Not found').add(u.button('Press F2 (search)', function () { search(); }, !st.P, !st.f || !!st.P || S.hand.busy))
            .add(u.button('Write the period down', function () { recordPeriod(); }, false, !st.P || !!st.rowsDone.P));
          u.next('Next: fold and measure', !!st.P && !!st.rowsDone.P);
        }, ok: function () { return !!st.P && !!st.rowsDone.P; }, auto: function () { return search().then(function () { recordPeriod(); }); } },
      { id: 'fold', title: 'Fold and measure', view: 'screen', render: function (u) {
          u.h2('Fold the light curve and measure the transit');
          u.p('F3 folds on the period; F4 measures the depth in the middle of the transit and the duration from first to last contact, then corrects the depth for limb darkening and finds the impact parameter and the inclination.');
          u.task('1. Fold', !!st.fold, st.fold ? 'Mid-transit at day ' + st.an.t0.toFixed(3) : 'Not folded').add(u.button('Press F3 (fold)', function () { fold(); }, !st.fold, !st.P || !!st.fold || S.hand.busy));
          u.task('2. Measure', !!(st.an && st.an.done), st.an && st.an.done ? 'Rp/Rs = ' + st.an.k.toFixed(4) : 'Not measured').add(u.button('Press F4 (measure)', function () { measure(); }, !(st.an && st.an.done), !st.fold || (st.an && st.an.done) || S.hand.busy))
            .add(u.button('Write the results down', function () { recordMeasure(); }, false, !(st.an && st.an.done) || !!st.rowsDone.k));
          u.h3('Observation table'); u.table();
          u.next('Next: the result', !!kRow());
        }, ok: function () { return !!kRow(); }, auto: function () { return fold().then(function () { return measure(); }).then(function () { recordMeasure(); }); } }
    ],
    tick: function () {
      hudP.set(st.P ? st.P.toFixed(3) + ' d' : '—'); hudD.set(st.an && st.an.done ? (st.an.depth * 100).toFixed(2) + ' %' : '—'); hudK.set(st.an && st.an.done ? st.an.k.toFixed(4) : '—');
      if (st.running) paint(false);
    }
  };
});
