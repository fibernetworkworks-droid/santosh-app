/* Prayogshala studio module: SEMICONDUCTOR CHARACTERISATION BENCH for four labs.
   ph2-vdp-sheet (+ variants): a probe station with four needles at the edge of a flat sample; van der Pauw equation solved
   numerically for the sheet resistance. ph2-fpp-film (+ variants): a collinear four-point head on a film, V against I.
   ph2-haynes-shockley: a germanium bar with an emitter and a collector, a pulse generator and a scope; the drift mobility from
   the transit time at several fields. ph2-solar-cell (+ variants): a cell under a lamp, I-V sweeps at several intensities.
   Kernels ph2_sheet, ph2_hs, ph2_solar (packs/ph2_films.js). */
HoolaStudio.define('ph2-semi-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var id = String(S.lab.id);
  var MODE = id.indexOf('ph2-vdp') === 0 ? 'vdp' : id.indexOf('ph2-fpp') === 0 ? 'fpp' : id.indexOf('ph2-haynes') === 0 ? 'hs' : 'solar';
  var KNAME = { vdp: 'ph2_sheet', fpp: 'ph2_sheet', hs: 'ph2_hs', solar: 'ph2_solar' }[MODE];
  var KN = HK.K[KNAME], CALCS = HK.CALCS;
  var p = HK.paramsFor(KNAME, S.lab.params);
  var V_ = S.lab.variant || {};
  var SAMPLE = V_.sample || { vdp: 'Silicon wafer, 525 µm (illustrative resistivity)', fpp: 'Nickel film on glass, 50 nm (illustrative)', hs: 'n-type germanium bar', solar: 'Silicon solar cell, 4 cm² (illustrative parameters)' }[MODE];
  var st = { placed: false, down: false, on: false, I: 1.0e-3, E: 2000, G: 1000, conf: 0, solved: null, plotKey: '', tr: null, sweepG: 0, sw: null, fitted: false, lamp: false };
  var GS = [200, 500, 1000], ES = [1000, 1500, 2000, 2500, 3000], IS = [1e-3, 2e-3, 3e-3, 4e-3, 5e-3];
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 24); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }
  function sig(v, n) { return v === 0 ? 0 : +v.toPrecision(n); }

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
        xx.font = '700 ' + (txt.length > 8 ? 56 : txt.length > 6 ? 70 : 88) + 'px "JetBrains Mono", monospace'; xx.textAlign = 'right'; xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 118); xx.font = '600 32px "Public Sans", sans-serif'; xx.fillText(u2, 496, 150); }); } };
  }
  var smu = instBox(0.0, 0.1, -0.1, MODE === 'hs' ? 'DRIVE SUPPLY' : 'SOURCE-MEASURE UNIT', MODE === 'hs' ? 'field along the bar' : 'source current / voltage, measure the other', 0.22);
  var aux = MODE === 'hs' ? instBox(0.0, -0.1, 0.05, 'PULSE GENERATOR', 'injects holes at the emitter', 0.22) : null;
  smu.show('OFF', '');
  // ---- the scope / plot screen
  var monG = new T.Group(); S.scene.add(monG); monG.position.set(0.34, 0, -0.1); monG.rotation.y = -0.3;
  var mb = S.rounded(0.3, 0.2, 0.03, 0.008, new T.MeshStandardMaterial({ color: 0x20262e, roughness: 0.4 })); mb.position.set(0, 0.115, 0); monG.add(mb);
  mk(monG, cyl(0.012, 0.016, 0.07, 14), M.alu, 0, 0.035, -0.01); mk(monG, box(0.12, 0.008, 0.08), M.alu, 0, 0.004, 0);
  var plotTex = S.liveTex(768, 480), plot = new T.Mesh(new T.PlaneGeometry(0.28, 0.175), new T.MeshBasicMaterial({ map: plotTex, toneMapped: false })); plot.position.set(0, 0.115, 0.017); monG.add(plot);
  S.contact(0.34, 0.2, 0.34, -0.1, 0.5);
  var CX = -0.3, CZ = -0.12;
  var fixture = new T.Group(); S.scene.add(fixture); fixture.position.set(CX, 0, CZ);
  var sampleG = new T.Group(); var needles = new T.Group(); var lamp = null, lampGlow = null, pulse = null;
  mk(fixture, cyl(0.12, 0.125, 0.02, 48), new T.MeshStandardMaterial({ color: 0xaeb4ba, roughness: 0.35, metalness: 0.85 }), 0, 0.01, 0);
  var tray = new T.Group(); S.scene.add(tray); tray.position.set(-0.06, 0.012, 0.17); mk(tray, cyl(0.035, 0.035, 0.004, 28), M.alu, 0, -0.01, 0);
  var trayHold = null;
  if (MODE === 'vdp' || MODE === 'fpp') {
    var sw = MODE === 'vdp' ? 0.05 : 0.07, sd = MODE === 'vdp' ? 0.05 : 0.04;
    var matS = new T.MeshStandardMaterial({ color: MODE === 'vdp' ? 0x3b4048 : 0xb98a52, roughness: 0.12, metalness: 0.9 });
    trayHold = mk(tray, box(sw, 0.002, sd), matS, 0, 0.0, 0);
    mk(sampleG, box(sw, 0.002, sd), matS, 0, 0, 0); sampleG.position.set(0, 0.025, 0); fixture.add(sampleG); sampleG.visible = false;
    needles.position.set(0, 0.06, 0); fixture.add(needles);
    var pts = MODE === 'vdp' ? [[-sw / 2 + 0.002, -sd / 2 + 0.002], [sw / 2 - 0.002, -sd / 2 + 0.002], [sw / 2 - 0.002, sd / 2 - 0.002], [-sw / 2 + 0.002, sd / 2 - 0.002]] : [[-0.0225, 0], [-0.0075, 0], [0.0075, 0], [0.0225, 0]];
    if (MODE === 'fpp') mk(needles, box(0.07, 0.02, 0.02), M.iron, 0, 0.018, 0);
    pts.forEach(function (q, i) {
      mk(needles, cyl(0.0008, 0.0002, 0.03, 8), M.steel, q[0], 0, q[1]);
      if (MODE === 'vdp') { var px = q[0] * 1.6, pz = q[1] * 1.6, dx = px - q[0], dz = pz - q[1], len = Math.sqrt(dx * dx + dz * dz + 0.02 * 0.02);
        var arm = mk(needles, cyl(0.0008, 0.0008, len, 6), M.steel, (px + q[0]) / 2, 0.01, (pz + q[1]) / 2); arm.lookAt(new T.Vector3(0, 0, 0)); arm.rotation.set(0, 0, 0); arm.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), new T.Vector3(dx, 0.02, dz).normalize());
        mk(needles, cyl(0.004, 0.004, 0.01, 12), M.brass, q[0] * 1.6, 0.02, q[1] * 1.6); var lb = S.label('ABCD'.charAt(i), { w: 0.01, ratio: 1, color: '#fff', bg: '#a8201a' }); lb.position.set(q[0] * 1.6, 0.032, q[1] * 1.6 + 0.005); lb.rotation.x = -1.2; needles.add(lb); }
    });
    var lever = new T.Group(); lever.position.set(0.1, 0.03, 0.04); fixture.add(lever); mk(lever, cyl(0.004, 0.004, 0.03, 10), M.steel, 0, 0.015, 0); var lvh = mk(lever, box(0.03, 0.008, 0.01), M.red, 0, 0.032, 0);
    S.addApparatus('lever', lever, 'Needle lever', 'Lowers the needles onto the sample with a micrometer screw. Never lower them by hand.');
    fixture.userData.lvh = lvh;
  } else if (MODE === 'hs') {
    mk(fixture, box(0.24, 0.006, 0.1), M.darkWood, 0, 0.023, 0);
    var barM = new T.MeshStandardMaterial({ color: 0x70767d, roughness: 0.25, metalness: 0.9 });
    mk(fixture, box(0.14, 0.006, 0.01), barM, 0, 0.03, 0);
    mk(fixture, box(0.008, 0.012, 0.014), M.brass, -0.07, 0.034, 0); mk(fixture, box(0.008, 0.012, 0.014), M.brass, 0.07, 0.034, 0);
    mk(fixture, cyl(0.0006, 0.0003, 0.015, 6), M.steel, -0.02, 0.04, 0); mk(fixture, cyl(0.0006, 0.0003, 0.015, 6), M.steel, 0.02, 0.04, 0);
    var el = S.label('EMITTER', { w: 0.03, ratio: 0.3, color: '#fff', bg: '#a8201a' }); el.position.set(-0.02, 0.045, 0.035); el.rotation.x = -1.0; fixture.add(el);
    var cl = S.label('COLLECTOR', { w: 0.036, ratio: 0.3, color: '#fff', bg: '#1d6fa8' }); cl.position.set(0.02, 0.045, 0.035); cl.rotation.x = -1.0; fixture.add(cl);
    var gl = S.label('Ge BAR · L = 1 cm', { w: 0.08, ratio: 0.14, color: '#e8eaec', bg: '#2b323d' }); gl.position.set(0, 0.027, 0.04); gl.rotation.x = -1.2; fixture.add(gl);
    pulse = mk(fixture, new T.SphereGeometry(0.004, 12, 10), new T.MeshBasicMaterial({ color: 0x29d0ff, transparent: true, opacity: 0 }), -0.02, 0.034, 0);
  } else {
    mk(fixture, box(0.1, 0.012, 0.1), M.alu, 0, 0.026, 0);
    var cellM = new T.MeshStandardMaterial({ color: 0x14224a, roughness: 0.3, metalness: 0.5 });
    var cell = mk(fixture, box(0.05, 0.003, 0.05), cellM, 0, 0.034, 0);
    for (var gi = -2; gi <= 2; gi++) mk(fixture, box(0.0006, 0.0005, 0.05), M.chrome, gi * 0.009, 0.0357, 0);
    mk(fixture, box(0.05, 0.0005, 0.003), M.chrome, 0, 0.0357, 0.021);
    mk(fixture, cyl(0.006, 0.008, 0.2, 14), M.steel, 0.1, 0.12, -0.02);
    lamp = new T.Group(); lamp.position.set(0, 0.18, 0); fixture.add(lamp);
    mk(lamp, box(0.1, 0.012, 0.012), M.steel, 0.05, 0.0, -0.02);
    mk(lamp, cyl(0.04, 0.05, 0.04, 28), new T.MeshStandardMaterial({ color: 0x2f3338, roughness: 0.4, metalness: 0.6 }), 0, 0.0, 0);
    lampGlow = mk(lamp, cyl(0.036, 0.036, 0.004, 28), new T.MeshBasicMaterial({ color: 0xfff0b0, transparent: true, opacity: 0 }), 0, -0.022, 0);
    var ll = S.label('SOLAR SIMULATOR', { w: 0.07, ratio: 0.14, color: '#20252b', bg: '#d8b42a' }); ll.position.set(0, 0.0, 0.0505); lamp.add(ll);
  }
  if (MODE === 'hs') {
    S.wire([[CX - 0.02, 0.05, CZ], [-0.18, 0.06, -0.02], [-0.02, 0.05, -0.1]], 'red');
    S.wire([[CX + 0.02, 0.05, CZ], [0.12, 0.06, -0.1], [0.3, 0.1, -0.1]], 'blue');
    S.wire([[CX + 0.07, 0.04, CZ + 0.02], [-0.1, 0.05, 0.05], [0.0, 0.05, 0.1]], 'black');
  } else S.wire([[CX + 0.1, 0.04, CZ + 0.02], [-0.1, 0.05, 0.02], [-0.02, 0.05, 0.1]], 'blue');
  S.contact(0.26, 0.26, CX, CZ, 0.5);
  S.addApparatus('fixture', fixture, { vdp: 'Probe station', fpp: 'Four-point probe stage', hs: 'Germanium bar on its board', solar: 'Solar cell under the simulator' }[MODE], { vdp: 'A flat sample on the stage with four needles at its edge.', fpp: 'A film on glass with a collinear four-point head above it.', hs: 'An n-type germanium bar with a point-contact emitter and collector 1 cm apart.', solar: 'A silicon cell under a lamp on a post; the reference cell sets the intensity.' }[MODE]);
  S.addApparatus('smu', smu.group, MODE === 'hs' ? 'Drive supply' : 'Source-measure unit', MODE === 'hs' ? 'Sets the electric field along the bar.' : 'Sources a current or voltage and measures the other quantity.');
  if (aux) S.addApparatus('aux', aux.group, 'Pulse generator', 'Injects a short pulse of holes at the emitter.');
  S.addApparatus('mon', monG, MODE === 'hs' ? 'Oscilloscope' : 'Display', 'Shows the signal.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard(MODE === 'hs' ? 'Field' : MODE === 'solar' ? 'Intensity' : 'Current'), hudB = S.hudCard(MODE === 'hs' ? 'Transit time' : MODE === 'solar' ? 'Voc' : 'Voltage');

  // ================================================================ plot helper
  function axes(x, w, h, xl, yl, x0, x1, y0, y1, xt, yt) {
    var L = 78, R = 18, Tp = 30, B = 54;
    var X = function (v) { return L + (v - x0) / (x1 - x0) * (w - L - R); }, Y = function (v) { return h - B - (v - y0) / (y1 - y0) * (h - B - Tp); };
    x.strokeStyle = 'rgba(255,255,255,.14)'; x.fillStyle = '#9aa7b6'; x.font = '600 17px "JetBrains Mono", monospace'; x.lineWidth = 1;
    for (var i = 0; i <= 5; i++) { var xv = x0 + (x1 - x0) * i / 5; x.beginPath(); x.moveTo(X(xv), Tp); x.lineTo(X(xv), h - B); x.stroke(); x.fillText(xt(xv), X(xv) - 18, h - B + 22); }
    for (var j = 0; j <= 4; j++) { var yv = y0 + (y1 - y0) * j / 4; x.beginPath(); x.moveTo(L, Y(yv)); x.lineTo(w - R, Y(yv)); x.stroke(); x.fillText(yt(yv), 4, Y(yv) + 5); }
    x.fillStyle = '#e8eaec'; x.font = '600 20px "Public Sans", sans-serif'; x.fillText(xl, w / 2 - 50, h - 12); x.fillText(yl, 8, 22);
    return { X: X, Y: Y };
  }
  function drawPlot() {
    var key = MODE + '|' + st.conf + '|' + st.E + '|' + st.G + '|' + (st.tr ? 1 : 0) + '|' + (st.sw ? st.sw.G : 0) + '|' + S.rows.length + '|' + st.down + '|' + st.I;
    if (key === st.plotKey) return; st.plotKey = key;
    plotTex.draw(function (x, w, h) {
      x.fillStyle = '#10161d'; x.fillRect(0, 0, w, h);
      if (MODE === 'vdp') {
        var cx = w / 2, cy = h / 2 + 8, a = 150, pts = [[cx - a, cy + a * 0.8], [cx + a, cy + a * 0.8], [cx + a, cy - a * 0.8], [cx - a, cy - a * 0.8]];
        x.strokeStyle = '#6a7684'; x.lineWidth = 3; x.fillStyle = '#2a3340'; x.beginPath(); x.rect(cx - a, cy - a * 0.8, 2 * a, 1.6 * a); x.fill(); x.stroke();
        x.font = '700 26px "Public Sans", sans-serif'; ['A', 'B', 'C', 'D'].forEach(function (l, i) { x.fillStyle = '#e8eaec'; x.fillText(l, pts[i][0] + (i === 0 || i === 3 ? -34 : 14), pts[i][1] + (i < 2 ? 28 : -10)); x.beginPath(); x.arc(pts[i][0], pts[i][1], 7, 0, 7); x.fill(); });
        var cur = st.conf === 0 ? [0, 1] : [1, 2], vol = st.conf === 0 ? [3, 2] : [0, 3];
        x.lineWidth = 4; x.strokeStyle = '#ffb14a'; x.beginPath(); x.moveTo(pts[cur[0]][0], pts[cur[0]][1]); x.lineTo(pts[cur[1]][0], pts[cur[1]][1]); x.stroke();
        x.strokeStyle = '#5ee0a0'; x.setLineDash([10, 8]); x.beginPath(); x.moveTo(pts[vol[0]][0], pts[vol[0]][1]); x.lineTo(pts[vol[1]][0], pts[vol[1]][1]); x.stroke(); x.setLineDash([]);
        x.fillStyle = '#e8eaec'; x.font = '600 22px "Public Sans", sans-serif'; x.fillText(st.conf === 0 ? 'Current in A, out B · voltage across D, C  →  R_AB,CD' : 'Current in B, out C · voltage across A, D  →  R_BC,DA', 40, 34);
        x.fillStyle = '#ffb14a'; x.fillText('current', 40, h - 40); x.fillStyle = '#5ee0a0'; x.fillText('voltage', 140, h - 40);
        return;
      }
      if (MODE === 'fpp') {
        var rs = S.rows.filter(function (r) { return r.I !== undefined; }), imax = 5.5, vmax = 1;
        rs.forEach(function (r) { if (r.Vm * 1e3 > vmax) vmax = r.Vm * 1e3; }); vmax = Math.max(vmax * 1.2, p.Rs * Math.log(2) / Math.PI * 5.5 * 1.1);
        var ax = axes(x, w, h, 'I (mA)', 'V (mV)', 0, imax, 0, vmax, function (v) { return v.toFixed(1); }, function (v) { return v.toFixed(2); });
        x.fillStyle = '#5ee0a0'; rs.forEach(function (r) { x.beginPath(); x.arc(ax.X(r.I * 1e3), ax.Y(r.Vm * 1e3), 6, 0, 7); x.fill(); });
        if (rs.length >= 3) { var f = S.fit.linear(rs.map(function (r) { return [r.I * 1e3, r.Vm * 1e3]; })); if (f) { x.strokeStyle = '#ffd24a'; x.lineWidth = 2; x.beginPath(); x.moveTo(ax.X(0), ax.Y(f.c)); x.lineTo(ax.X(imax), ax.Y(f.m * imax + f.c)); x.stroke(); } }
        return;
      }
      if (MODE === 'hs') {
        var td = p.L / (p.mu * st.E), t1 = 2.2 * td, tr = st.tr, ymax = tr ? tr.peak * 1.2 : 1;
        var ax2 = axes(x, w, h, 't (µs)', 'collector signal (mV)', 0, t1 * 1e6, 0, tr ? ymax : 1, function (v) { return v.toFixed(0); }, function (v) { return v.toFixed(1); });
        x.strokeStyle = '#5ee0a0'; x.lineWidth = 2; x.beginPath();
        if (tr) { for (var k = 0; k <= 300; k++) { var tt = t1 * k / 300, yy = KN.sig(assign(p, { E: st.E }), tt); if (k === 0) x.moveTo(ax2.X(tt * 1e6), ax2.Y(yy)); else x.lineTo(ax2.X(tt * 1e6), ax2.Y(yy)); } x.stroke();
          x.strokeStyle = '#ffd24a'; x.setLineDash([6, 6]); x.beginPath(); x.moveTo(ax2.X(tr.tpk * 1e6), ax2.Y(0)); x.lineTo(ax2.X(tr.tpk * 1e6), ax2.Y(tr.peak)); x.stroke(); x.setLineDash([]);
          x.fillStyle = '#ffd24a'; x.font = '600 20px "JetBrains Mono", monospace'; x.fillText('t_d = ' + (tr.tpk * 1e6).toFixed(2) + ' µs', ax2.X(tr.tpk * 1e6) + 10, 60); }
        else { x.fillStyle = '#9aa7b6'; x.font = '600 22px "Public Sans", sans-serif'; x.fillText('Inject a pulse to see the collector signal.', 150, h / 2); }
        return;
      }
      var sw = st.sw, vmax2 = 0.9, imax2 = 0.18;
      var ax3 = axes(x, w, h, 'V (V)', 'I (A)', 0, vmax2, 0, imax2, function (v) { return v.toFixed(2); }, function (v) { return v.toFixed(3); });
      if (sw) {
        x.strokeStyle = '#5ee0a0'; x.lineWidth = 2; x.beginPath(); var first = true;
        for (var v = 0; v <= sw.m.Voc * 1.02; v += 0.01) { var q = KN.view({}, assign(p, { V: v, G: sw.G })); if (q.I < -0.01) break; if (first) { x.moveTo(ax3.X(v), ax3.Y(q.I)); first = false; } else x.lineTo(ax3.X(v), ax3.Y(q.I)); } x.stroke();
        x.fillStyle = '#ffd24a'; x.font = '600 18px "JetBrains Mono", monospace';
        x.fillText('G = ' + sw.G + ' W/m²   Voc ' + sw.m.Voc.toFixed(3) + ' V   Isc ' + (sw.m.Isc * 1e3).toFixed(1) + ' mA   Pmax ' + (sw.m.Pmax * 1e3).toFixed(1) + ' mW', 90, 52);
      } else { x.fillStyle = '#9aa7b6'; x.font = '600 22px "Public Sans", sans-serif'; x.fillText('Run a sweep to see the I–V curve.', 150, h / 2); }
    });
  }

  // ================================================================ human actions
  function placeSample() {
    if (busy() || st.placed) return Promise.resolve();
    if (MODE === 'hs' || MODE === 'solar') { st.placed = true; S.say(MODE === 'hs' ? 'The germanium bar is wired: emitter, collector and drive supply.' : 'The cell is on the stage under the lamp.'); S.render(); return Promise.resolve(); }
    var a = tray.position.clone(), b = new T.Vector3(CX, 0.04, CZ);
    return S.hand.pinchMove(a.clone().add(new T.Vector3(0, 0.01, 0)), function (k) { return new T.Vector3(a.x + (b.x - a.x) * k, a.y + 0.08 * Math.sin(Math.PI * k) + (b.y - a.y) * k + 0.01, a.z + (b.z - a.z) * k); },
      function (k) { tray.position.set(a.x + (b.x - a.x) * k, a.y + 0.08 * Math.sin(Math.PI * k) + (b.y - a.y) * k, a.z + (b.z - a.z) * k); }, { mode: 'top', ms: 1200, reachMs: 600 })
      .then(function () { tray.visible = false; sampleG.visible = true; st.placed = true; S.say('The sample is on the stage.'); S.render(); });
  }
  function lowerNeedles() {
    if (busy() || st.down) return Promise.resolve();
    if (!st.placed) { S.say('Place the sample first.'); return Promise.resolve(); }
    if (MODE === 'hs' || MODE === 'solar') {
      var tgt = MODE === 'hs' ? smu.knob : smu.knob;
      return S.hand.tap(tgt, 'front').then(function () { st.down = true; st.on = true; if (MODE === 'solar') st.lamp = true; S.say(MODE === 'hs' ? 'Supply and pulse generator on.' : 'Lamp on. Set the intensity with the reference cell: 1000 W/m² is one sun.'); S.click(880, 0.05); S.render(); });
    }
    return S.hand.tap(fixture.userData.lvh, 'top').then(function () { return S.tween(500, function (k) { needles.position.y = 0.06 - 0.032 * k; }); }).then(function () { st.down = true; st.on = true; S.say('The needles touch the sample. The source-meter is on.'); S.click(880, 0.05); S.render(); });
  }
  function setI(v) { st.I = v; }
  // ---- vdp
  function measVdp(conf) {
    if (!st.down) { S.say('Lower the needles first.'); return null; }
    st.conf = conf;
    var q = assign(p, { sel: conf, I: st.I }), v = KN.view({}, q);
    var key = conf === 0 ? 'R1' : 'R2';
    for (var i = 0; i < S.rows.length; i++) if (S.rows[i].conf === conf) { S.say((conf === 0 ? 'R_AB,CD' : 'R_BC,DA') + ' is already measured: ' + S.rows[i].R.toFixed(4) + ' Ω.'); return S.rows[i]; }
    var row = { conf: conf, I: st.I, V: v.V, Vrev: v.Vrev, R: v.R };
    row[key] = v.R; S.addRow(row);
    S.say((conf === 0 ? 'R_AB,CD' : 'R_BC,DA') + ' = (' + (v.V * 1e3).toFixed(4) + ' − (' + (v.Vrev * 1e3).toFixed(4) + ')) mV / (2 × ' + (st.I * 1e3).toFixed(2) + ' mA) = ' + v.R.toFixed(4) + ' Ω.');
    return row;
  }
  function solveVdp() {
    var a = S.rows.filter(function (r) { return r.conf === 0; })[0], b = S.rows.filter(function (r) { return r.conf === 1; })[0];
    if (!a || !b) { S.say('Measure both configurations first.'); return false; }
    var rs = CALCS.ph2_vdp.fn([{ R1: a.R, R2: b.R }], p);
    st.solved = { Rs: rs, rho: rs * p.t, r1: a.R, r2: b.R };
    S.say('Solving exp(−πR1/Rs) + exp(−πR2/Rs) = 1 numerically: Rs = ' + rs.toFixed(3) + ' Ω/□, so ρ = Rs × t = ' + (rs * p.t).toExponential(3) + ' Ω m.'); S.render(); return true;
  }
  // ---- fpp
  function measFpp() {
    if (!st.down) { S.say('Lower the four-point head first.'); return null; }
    for (var i = 0; i < S.rows.length; i++) if (Math.abs(S.rows[i].I - st.I) < 1e-9) { S.say('You already have a reading at ' + (st.I * 1e3).toFixed(1) + ' mA.'); return null; }
    var v = KN.view({}, assign(p, { I: st.I })), row = { I: st.I, V: v.V, Vrev: v.Vrev, Vm: (v.V - v.Vrev) / 2 };
    S.addRow(row); S.say('At ' + (st.I * 1e3).toFixed(1) + ' mA the inner pins read ' + (v.V * 1e3).toFixed(4) + ' mV forward and ' + (v.Vrev * 1e3).toFixed(4) + ' mV reversed: V = ' + (row.Vm * 1e3).toFixed(4) + ' mV.'); return row;
  }
  function fitFpp() {
    if (S.rows.length < 4) { S.say('Take at least four readings at different currents.'); return false; }
    var rs = CALCS.ph2_fpp.fn(S.rows.map(function (r) { return { I: r.I, V: r.Vm }; }), p);
    st.solved = { Rs: rs, rho: rs * p.t }; st.fitted = true;
    S.say('Slope × π / ln 2 = ' + rs.toFixed(4) + ' Ω/□, so ρ = Rs × t = ' + (rs * p.t).toExponential(3) + ' Ω m.'); S.render(); return true;
  }
  // ---- hs
  function injectHs() {
    if (!st.down) { S.say('Switch the supply and pulse generator on first.'); return null; }
    var q = assign(p, { E: st.E }); st.tr = KN.pulse(q);
    for (var i = 0; i < S.rows.length; i++) if (S.rows[i].E === st.E) { S.say('You already have a reading at ' + st.E + ' V/m.'); return null; }
    var tr = st.tr, row = { E: st.E, td: tr.tpk, v: p.L / tr.tpk, fwhm: tr.fwhm, area: tr.area, lnAv: Math.log(tr.area * p.L / tr.tpk) };
    S.addRow(row); S.say('At ' + st.E + ' V/m the pulse peaks at ' + (tr.tpk * 1e6).toFixed(2) + ' µs: v = L / t_d = ' + row.v.toFixed(1) + ' m/s.'); return row;
  }
  function fitHs() {
    if (S.rows.length < 4) { S.say('Take readings at four or more fields.'); return false; }
    var mu = CALCS.ph2_drift.fn(S.rows.map(function (r) { return { E: r.E, v: r.v }; }), p);
    var r2 = S.rows.filter(function (r) { return r.E === 2000; })[0], D = 0, tau = 0, kT = 1.380649e-23 * p.T / 1.602176634e-19;
    if (r2) { var sg = r2.fwhm / 2.3548200450309493; D = sg * sg * r2.v * r2.v / (2 * r2.td); }
    var f = S.fit.linear(S.rows.map(function (r) { return [r.td, r.lnAv]; })); if (f && f.m < 0) tau = -1 / f.m;
    st.solved = { mu: mu, D: D, tau: tau, kT: kT }; st.fitted = true;
    S.say('Slope of v against E: μ = ' + mu.toFixed(4) + ' m²/V s.' + (D ? ' From the pulse width at 2000 V/m D = ' + (D * 1e4).toFixed(1) + ' cm²/s; the Einstein value μkT/q is ' + (mu * kT * 1e4).toFixed(1) + ' cm²/s.' : '') + (tau ? ' The area decay gives τ = ' + (tau * 1e6).toFixed(0) + ' µs.' : '')); S.render(); return true;
  }
  // ---- solar
  function sweepSolar() {
    if (!st.down) { S.say('Switch the lamp on first.'); return null; }
    for (var i = 0; i < S.rows.length; i++) if (S.rows[i].G === st.G) { S.say('You already swept at ' + st.G + ' W/m².'); return null; }
    var q = assign(p, { G: st.G }), m = KN.measure(q);
    st.sw = { G: st.G, m: m };
    var row = { G: st.G, Voc: m.Voc, Isc: m.Isc, Pmax: m.Pmax, FF: m.FF, eta: m.eta };
    S.addRow(row); S.say('At ' + st.G + ' W/m²: Voc = ' + m.Voc.toFixed(3) + ' V, Isc = ' + (m.Isc * 1e3).toFixed(1) + ' mA, Pmax = ' + (m.Pmax * 1e3).toFixed(1) + ' mW, FF = ' + m.FF.toFixed(3) + ', efficiency ' + (100 * m.eta).toFixed(1) + ' %.'); return row;
  }

  function result(rows) {
    if (MODE === 'vdp') { if (!st.solved) return null; return { label: 'Sheet resistance', value: st.solved.Rs, unit: 'Ω/□', digits: 3, truth: p.Rs, note: 'R_AB,CD = ' + st.solved.r1.toFixed(4) + ' Ω and R_BC,DA = ' + st.solved.r2.toFixed(4) + ' Ω solved in exp(−πR/Rs) + exp(−πR/Rs) = 1: Rs = ' + st.solved.Rs.toFixed(3) + ' Ω/□. With t = ' + (p.t * 1e6).toFixed(1) + ' µm the resistivity is ' + (st.solved.rho * 100).toFixed(3) + ' Ω cm (' + st.solved.rho.toExponential(3) + ' Ω m).' }; }
    if (MODE === 'fpp') { if (!st.solved) return null; return { label: 'Sheet resistance', value: st.solved.Rs, unit: 'Ω/□', digits: 4, truth: p.Rs, note: 'The slope of V against I, times π / ln 2, over ' + rows.length + ' currents. With t = ' + (p.t * 1e9).toFixed(0) + ' nm the resistivity is ' + st.solved.rho.toExponential(3) + ' Ω m.' }; }
    if (MODE === 'hs') { if (!st.solved) return null; return { label: 'Hole drift mobility', value: st.solved.mu, unit: 'm²/V s', digits: 4, truth: p.mu, note: 'Slope of the drift velocity v = L / t_d against the field over ' + rows.length + ' fields (peak times are slightly early: diffusion and recombination skew the pulse).' + (st.solved.D ? ' D from the pulse width ' + (st.solved.D * 1e4).toFixed(1) + ' cm²/s.' : '') }; }
    var hi = rows.filter(function (r) { return r.G === 1000; })[0], lo = rows.filter(function (r) { return r.G === 200; })[0];
    if (rows.length < 3 || !hi || !lo) return null;
    var ex = KN.exact(assign(p, { G: 1000 }));
    return { label: 'Efficiency at one sun', value: hi.eta * 100, unit: '%', digits: 2, truth: ex.eta * 100, note: 'Pmax / (G A) at 1000 W/m² with Pmax = ' + (hi.Pmax * 1e3).toFixed(1) + ' mW; fill factor ' + hi.FF.toFixed(3) + '. Voc rose from ' + lo.Voc.toFixed(3) + ' V at 200 W/m² (logarithmic in intensity) and Isc grew in proportion.' };
  }

  var cols = {
    vdp: [{ label: 'config', get: function (r) { return r.conf === 0 ? 'AB→CD' : 'BC→DA'; } }, { label: 'I (mA)', get: function (r) { return (r.I * 1e3).toFixed(2); } }, { label: 'V fwd (mV)', get: function (r) { return (r.V * 1e3).toFixed(4); } }, { label: 'V rev (mV)', get: function (r) { return (r.Vrev * 1e3).toFixed(4); } }, { label: 'R (Ω)', get: function (r) { return r.R.toFixed(4); } }],
    fpp: [{ label: 'I (mA)', get: function (r) { return (r.I * 1e3).toFixed(1); } }, { label: 'V fwd (mV)', get: function (r) { return (r.V * 1e3).toFixed(4); } }, { label: 'V rev (mV)', get: function (r) { return (r.Vrev * 1e3).toFixed(4); } }, { label: 'V (mV)', get: function (r) { return (r.Vm * 1e3).toFixed(4); } }],
    hs: [{ label: 'E (V/m)', get: function (r) { return r.E; } }, { label: 't_d (µs)', get: function (r) { return (r.td * 1e6).toFixed(2); } }, { label: 'v (m/s)', get: function (r) { return r.v.toFixed(1); } }, { label: 'FWHM (µs)', get: function (r) { return (r.fwhm * 1e6).toFixed(2); } }],
    solar: [{ label: 'G (W/m²)', get: function (r) { return r.G; } }, { label: 'Voc (V)', get: function (r) { return r.Voc.toFixed(3); } }, { label: 'Isc (mA)', get: function (r) { return (r.Isc * 1e3).toFixed(1); } }, { label: 'Pmax (mW)', get: function (r) { return (r.Pmax * 1e3).toFixed(1); } }, { label: 'FF', get: function (r) { return r.FF.toFixed(3); } }, { label: 'η (%)', get: function (r) { return (r.eta * 100).toFixed(2); } }]
  }[MODE];
  var graph = {
    vdp: null,
    fpp: { x: function (r) { return r.I * 1e3; }, y: function (r) { return r.Vm * 1e3; }, xlabel: 'I (mA)', ylabel: 'V (mV)', line: function (pts) { var f = S.fit.linear(pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); })); return f ? function (x) { return f.m * x + f.c; } : null; } },
    hs: { x: function (r) { return r.E; }, y: function (r) { return r.v; }, xlabel: 'E (V/m)', ylabel: 'v (m/s)', line: function (pts) { var k = S.fit.origin(pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); })); return isFinite(k) ? function (x) { return k * x; } : null; } },
    solar: { x: function (r) { return Math.log(r.G); }, y: function (r) { return r.Voc; }, xlabel: 'ln G', ylabel: 'Voc (V)', line: function (pts) { var f = S.fit.linear(pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); })); return f ? function (x) { return f.m * x + f.c; } : null; } }
  }[MODE];
  if (!graph) graph = { x: function (r) { return r.conf; }, y: function (r) { return r.R; }, xlabel: 'configuration', ylabel: 'R (Ω)', line: function () { return null; } };

  var THEORY = {
    vdp: { formula: 'exp(−π R_AB,CD / Rs) + exp(−π R_BC,DA / Rs) = 1', formulaNote: 'Rs = ρ / t; if the two resistances are equal Rs = π R / ln 2', more: ['Four small contacts on the edge of a flat, uniform sample of any shape.', 'Reversing the current and halving the difference removes the thermoelectric offset.', 'The equation has no closed form for unequal resistances: it is solved numerically.'] },
    fpp: { formula: 'Rs = (π / ln 2) (V / I) = 4.532 V / I', formulaNote: 'a thin film much larger than the pin spacing', more: ['Current through the outer pins, voltage across the inner pins.', 'Several currents give a slope; reversing the current removes thermoelectric voltage.', 'Resistivity = Rs × thickness, with the thickness from a stylus profilometer.'] },
    hs: { formula: 'v = L / t_d = μ E,   D = σ_t² v² / (2 t_d),   D = μ k T / q', formulaNote: 'the area under the pulse falls as exp(−t_d / τ)', more: ['The pulse spreads as it drifts: its width grows as √t.', 'The peak is slightly early because of diffusion and the decay with the lifetime.', 'The hole mobility of germanium at 300 K is about 0.19 m²/V s.'] },
    solar: { formula: 'Voc = n Vt ln(Iph / I0 + 1),   FF = Pmax / (Voc Isc),   η = Pmax / (G A)', formulaNote: 'Vt = kT/q = 25.9 mV at 300 K', more: ['Isc is proportional to the light intensity; Voc grows with its logarithm.', 'Series resistance lowers the fill factor; shunt resistance pulls the curve down near open circuit.', 'The cell parameters are typical lab values, not a commercial cell.'] }
  }[MODE];

  var steps = [];
  var useLabel = { vdp: 'Lower the needles', fpp: 'Lower the head', hs: 'Switch the supply on', solar: 'Switch the lamp on' }[MODE];
  steps.push({ id: 'setup', title: 'Set up', view: 'fixture', render: function (u) {
      u.h2(MODE === 'hs' ? 'Wire the bar, switch on' : MODE === 'solar' ? 'Place the cell, switch the lamp on' : 'Place the sample, lower the probes');
      u.p(MODE === 'hs' ? 'The bar is on its board. Connect the emitter to the pulse generator, the bar to the drive supply and the collector to the scope, then switch on.' : MODE === 'solar' ? 'The cell sits on the stage under the simulator. Switch the lamp on and let it settle.' : 'The sample waits on the tray. Put it on the stage and lower the probes onto it.');
      u.task('1. ' + (MODE === 'hs' ? 'Connect the bar' : 'Place the sample'), st.placed, st.placed ? 'Done' : 'Waiting').add(u.button(st.placed ? 'Done' : (MODE === 'hs' ? 'Connect' : 'Place the sample'), function () { S.focus('fixture'); placeSample(); }, !st.placed, st.placed || S.hand.busy));
      u.task('2. ' + useLabel, st.down, st.down ? 'On' : 'Off').add(u.button(st.down ? 'Done' : useLabel, function () { S.focus(MODE === 'vdp' || MODE === 'fpp' ? 'lever' : 'smu'); lowerNeedles(); }, !st.down && st.placed, st.down || !st.placed || S.hand.busy));
      u.next('Next: measure', st.placed && st.down);
    }, ok: function () { return st.placed && st.down; }, auto: function () { return placeSample().then(lowerNeedles); } });
  if (MODE === 'vdp') steps.push({ id: 'meas', title: 'Measure R_AB,CD and R_BC,DA', view: 'smu', render: function (u) {
      u.h2('Measure the two resistances');
      u.p('Set the current. For each configuration the source-meter reads the voltage forward and with the current reversed; the resistance is half their difference over the current.');
      u.slider('Source current', 0.1, 5, 0.1, function () { return st.I * 1e3; }, function (v) { setI(v * 1e-3); }, 'mA', 1);
      u.row(u.button('Measure R_AB,CD', function () { S.focus('smu'); measVdp(0); S.render(); }, false, S.hand.busy), u.button('Measure R_BC,DA', function () { S.focus('smu'); measVdp(1); S.render(); }, false, S.hand.busy));
      u.h3('Observation table'); u.table();
      u.task('Solve van der Pauw\'s equation', !!st.solved, st.solved ? 'Rs = ' + st.solved.Rs.toFixed(3) + ' Ω/□' : 'Not solved').add(u.button(st.solved ? 'Solved' : 'Solve numerically', function () { solveVdp(); }, !st.solved && S.rows.length >= 2, !!st.solved || S.rows.length < 2));
      u.next('Next: the result', !!st.solved);
    }, ok: function () { return !!st.solved; }, auto: function () { st.I = 2e-3; measVdp(0); measVdp(1); solveVdp(); return Promise.resolve(); } });
  if (MODE === 'fpp') steps.push({ id: 'meas', title: 'V against I', view: 'smu', render: function (u) {
      u.h2('Read the inner-pin voltage at several currents');
      u.p('Choose a current, read the voltage forward and reversed, and repeat for at least four currents.');
      u.slider('Source current', 0.5, 5, 0.5, function () { return st.I * 1e3; }, function (v) { setI(v * 1e-3); }, 'mA', 1);
      u.row(u.button('Measure', function () { S.focus('smu'); measFpp(); S.render(); }, false, S.hand.busy));
      u.h3('Observation table'); u.table();
      u.task('Fit the line', st.fitted, st.fitted ? 'Rs = ' + st.solved.Rs.toFixed(3) + ' Ω/□' : 'Not fitted').add(u.button(st.fitted ? 'Fitted' : 'Fit V against I', function () { fitFpp(); }, !st.fitted && S.rows.length >= 4, st.fitted || S.rows.length < 4));
      u.next('Next: the result', st.fitted);
    }, ok: function () { return st.fitted; }, auto: function () { return IS.reduce(function (pr, i) { return pr.then(function () { st.I = i; measFpp(); }); }, Promise.resolve()).then(function () { fitFpp(); }); } });
  if (MODE === 'hs') steps.push({ id: 'meas', title: 'Transit time at several fields', view: 'mon', render: function (u) {
      u.h2('Inject a pulse at each field');
      u.p('Set a field along the bar and inject a pulse. The collector signal peaks when the pulse arrives; read the peak time and the width. Repeat for at least four fields.');
      u.slider('Field E', 500, 3500, 100, function () { return st.E; }, function (v) { st.E = v; st.tr = null; }, 'V/m', 0);
      u.row(u.button('Inject a pulse and read it', function () { S.focus('mon'); injectHs(); S.render(); }, false, S.hand.busy));
      u.h3('Observation table'); u.table();
      u.task('Mobility from v against E', st.fitted, st.fitted ? 'μ = ' + st.solved.mu.toFixed(4) + ' m²/V s' : 'Not fitted').add(u.button(st.fitted ? 'Fitted' : 'Fit v against E', function () { fitHs(); }, !st.fitted && S.rows.length >= 4, st.fitted || S.rows.length < 4));
      u.next('Next: the result', st.fitted);
    }, ok: function () { return st.fitted; }, auto: function () { return ES.reduce(function (pr, e) { return pr.then(function () { st.E = e; injectHs(); }); }, Promise.resolve()).then(function () { fitHs(); }); } });
  if (MODE === 'solar') steps.push({ id: 'meas', title: 'I–V sweeps', view: 'mon', render: function (u) {
      u.h2('Sweep the voltage at three intensities');
      u.p('Choose an intensity, run the sweep from 0 V to open circuit and read Voc, Isc and the maximum power point. Do 200, 500 and 1000 W/m².');
      u.row(u.button('200 W/m²', function () { st.G = 200; S.render(); }, st.G === 200, S.hand.busy), u.button('500 W/m²', function () { st.G = 500; S.render(); }, st.G === 500, S.hand.busy), u.button('1000 W/m²', function () { st.G = 1000; S.render(); }, st.G === 1000, S.hand.busy));
      u.row(u.button('Run the sweep', function () { S.focus('mon'); sweepSolar(); S.render(); }, true, S.hand.busy));
      u.h3('Observation table'); u.table();
      u.next('Next: the result', S.rows.length >= 3);
    }, ok: function () { return S.rows.length >= 3; }, auto: function () { GS.forEach(function (g) { st.G = g; sweepSolar(); }); return Promise.resolve(); } });

  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { fixture: [[-0.3, 0.3, 0.25], [-0.3, 0.04, -0.12]], lever: [[-0.15, 0.2, 0.15], [-0.2, 0.05, -0.08]], smu: [[0.0, 0.26, 0.32], [0.0, 0.05, 0.1]], aux: [[0.0, 0.22, 0.08], [0.0, 0.05, -0.1]], mon: [[0.38, 0.24, 0.18], [0.34, 0.11, -0.1]],
      bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: S.lab.theory, formula: THEORY.formula, formulaNote: THEORY.formulaNote, more: THEORY.more, precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 110) + (S.lab.aim.length > 110 ? '…' : ''), 'Sample: ' + SAMPLE + '.', MODE === 'hs' ? 'Probe spacing L = 1 cm.' : MODE === 'solar' ? 'Cell area ' + (p.A * 1e4).toFixed(1) + ' cm².' : 'Thickness ' + (p.t >= 1e-6 ? (p.t * 1e6).toFixed(0) + ' µm' : (p.t * 1e9).toFixed(0) + ' nm') + '.'], columns: cols },
    graph: graph,
    result: result,
    tol: MODE === 'solar' ? 0.03 : 0.02,
    resultNote: 'The value came from your own readings; the lab\'s true value is shown alongside.',
    chips: { vdp: ['Why reverse the current?', 'Why is the equation solved numerically?', 'Check my readings', 'What if the contacts are not at the edge?'], fpp: ['Why four pins?', 'What is π / ln 2?', 'Check my readings', 'When do I need a correction factor?'],
      hs: ['Why does the pulse widen?', 'What is the Einstein relation?', 'Check my readings', 'Why is the peak slightly early?'], solar: ['Why does Voc rise with light?', 'What is the fill factor?', 'Check my readings', 'What lowers the efficiency?'] }[MODE],
    viva: [],
    askState: function () { return { experiment: S.lab.title, sample: SAMPLE, ready: st.down, current_mA: sig(st.I * 1e3, 3), field_V_per_m: st.E, intensity_W_per_m2: st.G, readings_taken: S.rows.length }; },
    steps: steps,
    tick: function () {
      if (MODE === 'hs') { smu.show(st.down ? sig(st.E, 4) + '' : 'OFF', st.down ? 'V/m' : ''); aux.show(st.down ? 'READY' : 'OFF', ''); if (pulse) pulse.material.opacity = st.tr ? 0.6 : 0; hudA.set(st.E + ' V/m'); hudB.set(st.tr ? (st.tr.tpk * 1e6).toFixed(1) + ' µs' : '—'); }
      else if (MODE === 'solar') { smu.show(st.down ? 'ON' : 'OFF', st.down ? 'lamp' : ''); if (lampGlow) lampGlow.material.opacity = st.lamp ? 0.9 : 0; if (lamp) lamp.position.y = 0.18 - 0.05 * (st.G / 1000); hudA.set(st.G + ' W/m²'); hudB.set(st.sw ? st.sw.m.Voc.toFixed(3) + ' V' : '—'); }
      else { smu.show(st.down ? (st.I * 1e3).toFixed(2) : 'OFF', st.down ? 'mA' : ''); hudA.set((st.I * 1e3).toFixed(1) + ' mA'); var vv = st.down ? KN.view({}, assign(p, { sel: st.conf, I: st.I })).V : 0; hudB.set(st.down ? (vv * 1e3).toFixed(3) + ' mV' : '—'); }
      drawPlot();
    },
  };
});
