/* Prayogshala studio module: GAMMA-RAY SPECTROMETER BENCH (M.Sc. nuclear physics).
   A lead castle with a detector hanging in its roof (a NaI(Tl) / CsI(Tl) / BGO / plastic scintillator on a
   photomultiplier, or a coaxial HPGe on its liquid-nitrogen dewar), a rail that carries a sealed source at a chosen
   distance below it, a lead store with tongs, a NIM bin (HV, spectroscopy amplifier, multichannel analyser) and the
   analyser's monitor. The spectrum on the monitor is the lab's own kernel `msc_gspec` (packs/msc_elec.js): the
   counts of every channel are Poisson numbers from the lab's seed. Peak finding, the Gaussian fit and the area are
   done here on those counts, the way the analyser's software does it - nothing is read back from the formula.
   One rig serves calibration, resolution, efficiency, the Compton edge, a germanium energy scale and a soil
   spectrum: the lab's `task` number says which. */
HoolaStudio.define('msc-gamma-spectrometer', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.msc_gspec, assign = HK.assign;
  var p = HK.paramsFor('msc_gspec', S.lab.params);
  var V_ = S.lab.variant || {};
  var TASK = Math.round(p.task), HPGE = p.w0 > 0, NCH = Math.round(p.nch), SRCT = KN.SRC;
  var PLASTIC = /plastic/i.test(V_.sample || ''), DET = V_.sample || (HPGE ? 'Coaxial HPGe detector' : 'NaI(Tl) scintillator, 3 in x 3 in');
  var UNK = Math.round(p.src);
  var KNOWN = [4, 3, 2, 0, 1].filter(function (i) { return i !== UNK; });
  var SOURCES = TASK === 0 ? KNOWN.concat([UNK]) : [UNK];
  var NOMG = Math.round(p.gain * 10) / 10 || p.gain;               // the nominal gain printed on the amplifier
  var COLS = ['#c9462f', '#2f6fb3', '#3f9a58', '#d19a2a', '#7a4fa8', '#b8527e', '#6b6b6b'];
  var st = { hv: false, loaded: -1, d: p.d, t: p.t, cursor: Math.round(NCH * 0.25), zoom: 0, cdata: null, key: '', shown: 0,
    acq: false, fit: null, edge: null, done: {}, live: 0 };
  var dirty = true, panelCv = null;

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function r1(v, d) { var k = Math.pow(10, d === undefined ? 1 : d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function name(i) { return SRCT[i][0]; }
  function ecal(ch) { return p.off + p.gain * (ch + 0.5); }          // the analyser's stored calibration
  function Q() { return assign(p, { src: st.loaded, d: st.d, t: st.t, seed: p.seed + 31 * st.loaded + Math.round(st.d * 7) + Math.round(st.t / 10) }); }
  function shownCounts() {
    if (!st.cdata) return null;
    if (st.shown >= 1) return st.cdata;
    var o = [], i; for (i = 0; i < st.cdata.length; i++) o.push(Math.round(st.cdata[i] * st.shown)); return o;
  }

  // ================================================================ the analyser's software
  function smooth3(c) { var o = [], i, n = c.length; for (i = 0; i < n; i++) o.push((c[Math.max(0, i - 1)] + 2 * c[i] + c[Math.min(n - 1, i + 1)]) / 4); return o; }
  function tallest(c) {
    var s = smooth3(c), i, best = Math.max(3, Math.round(c.length * 0.02)), bi = best;
    for (i = best; i < c.length - 3; i++) if (s[i] > s[bi]) bi = i;
    return s[bi] > 12 ? bi : -1;
  }
  function fwhmCh(i) { return Math.max(2, KN.fwhm(Math.max(ecal(i), 1), p) / p.gain); }
  function nextPeak(c, from) {                                        // second-difference peak search, like the real software
    var n = c.length, i, j, k, sig = new Array(n), best;
    for (i = 0; i < n; i++) sig[i] = 0;
    for (i = 4; i < n - 4; i++) {
      k = Math.max(1, Math.round(fwhmCh(i) / 2));
      if (i - k < 0 || i + k >= n) continue;
      var sd = -(c[i - k] - 2 * c[i] + c[i + k]), v = c[i - k] + 4 * c[i] + c[i + k];
      sig[i] = v > 0 ? sd / Math.sqrt(v) : 0;
    }
    for (i = Math.max(4, from + 1); i < n - 4; i++) {
      if (sig[i] < 4.5 || c[i] < 15) continue;
      k = Math.max(1, Math.round(fwhmCh(i) / 2)); best = true;
      for (j = Math.max(0, i - k); j <= Math.min(n - 1, i + k); j++) if (sig[j] > sig[i] || (sig[j] === sig[i] && j < i)) { best = false; break; }
      if (best) return i;
    }
    return -1;
  }
  function fitPeak(c, c0) {                                           // Gaussian least squares on ln(counts - baseline)
    var n = c.length, W = Math.max(10, Math.round(n / 45)), lo = Math.max(3, c0 - W), hi = Math.min(n - 4, c0 + W), s = smooth3(c), im = lo, i;
    for (i = lo; i <= hi; i++) if (s[i] > s[im]) im = i;
    var smax = s[im]; if (smax < 12) return null;
    var l = im, r = im; while (l > 1 && s[l] > smax / 2) l--; while (r < n - 2 && s[r] > smax / 2) r++;
    var rough = Math.max(r - l, 3), a = 0, b = 0, na = 0, nb = 0, j;
    for (j = -2; j <= 2; j++) { var ia = im - Math.floor(3 * rough) + j, ib = im + Math.floor(3 * rough) + j;
      if (ia >= 0) { a += c[ia]; na++; } if (ib < n) { b += c[ib]; nb++; } }
    var bl = Math.min(na ? a / na : 1e18, nb ? b / nb : 1e18); if (bl > 1e17) bl = 0;
    var pk = smax - bl; if (pk < 8) return null;
    var thr = 0.25, sw = Math.ceil(1.2 * rough), S0, S1, S2, S3, S4, T0, T1, T2, pts;
    for (var pass = 0; pass < 2; pass++) {
      S0 = S1 = S2 = S3 = S4 = T0 = T1 = T2 = 0; pts = 0;
      for (j = im - sw; j <= im + sw; j++) {
        if (j < 0 || j >= n) continue;
        var y = c[j] - bl; if (y < thr * pk || y < 3) continue;
        var x = j - im, w = y, ly = Math.log(y);
        S0 += w; S1 += w * x; S2 += w * x * x; S3 += w * x * x * x; S4 += w * x * x * x * x; T0 += w * ly; T1 += w * x * ly; T2 += w * x * x * ly; pts++;
      }
      if (pts >= 4) break; thr = 0.1;
    }
    if (pts < 3) return null;
    // solve [S0 S1 S2; S1 S2 S3; S2 S3 S4] [a b c]' = [T0 T1 T2]'
    var m = [[S0, S1, S2, T0], [S1, S2, S3, T1], [S2, S3, S4, T2]], q, rr, f;
    for (q = 0; q < 3; q++) { var pv = q; for (rr = q + 1; rr < 3; rr++) if (Math.abs(m[rr][q]) > Math.abs(m[pv][q])) pv = rr;
      var tmp = m[q]; m[q] = m[pv]; m[pv] = tmp; if (Math.abs(m[q][q]) < 1e-12) return null;
      for (rr = q + 1; rr < 3; rr++) { f = m[rr][q] / m[q][q]; for (var cc = q; cc < 4; cc++) m[rr][cc] -= f * m[q][cc]; } }
    var cq = m[2][3] / m[2][2], bq = (m[1][3] - m[1][2] * cq) / m[1][1];
    if (!(cq < 0)) return null;
    var varch = -1 / (2 * cq) - 1 / 12, mu = im - bq / (2 * cq); if (!(varch > 0.05)) return null;
    var fw = 2.3548200450309493 * Math.sqrt(varch), wA = Math.ceil(1.5 * fw), area = 0, jc = Math.round(mu);
    for (j = jc - wA; j <= jc + wA; j++) if (j >= 0 && j < n) area += c[j] - bl;
    return { mu: mu, fwhmCh: fw, area: area, bl: bl, peak: pk };
  }
  function findEdge(c) {                                              // the steepest fall of the smoothed continuum
    var n = c.length, k = 5, s = [], i, im = k, best = 0, bi;
    for (i = 0; i < n; i++) { var a = 0, q = 0; for (var j = -k; j <= k; j++) if (i + j >= 0 && i + j < n) { a += c[i + j]; q++; } s.push(a / q); }
    for (i = k; i < n - k; i++) if (s[i] > s[im]) im = i;
    bi = im; for (i = im; i < n - 8; i++) { var d = s[i + 3] - s[i - 3]; if (d < best) { best = d; bi = i; } }
    return bi;
  }
  function lineFor(src, ch) {                                         // match a peak to a line of the nuclear-data table
    var ls = SRCT[src][1].slice().sort(function (a, b) { return b[1] - a[1]; }), cand = [], i, j, ok;
    for (i = 0; i < ls.length; i++) { if (ls[i][1] < 0.05) continue; ok = true;
      for (j = 0; j < cand.length; j++) if (Math.abs(cand[j][0] - ls[i][0]) / ls[i][0] < 0.04) ok = false;
      if (ok) cand.push(ls[i]); }
    var est = NOMG * (ch + 0.5), bj = -1, bd = 1e18;
    for (i = 0; i < cand.length; i++) { var dd = Math.abs(cand[i][0] - est); if (dd < bd) { bd = dd; bj = i; } }
    return bj >= 0 && bd / cand[bj][0] < 0.1 ? { E: cand[bj][0], I: cand[bj][1], w: cand[bj][2] } : null;
  }
  function calFit() {                                                 // E = a + b ch from the known-source rows
    var pts = S.rows.filter(function (r) { return r.kind === 'k'; }).map(function (r) { return [r.ch, r.E]; });
    return pts.length >= 2 ? S.fit.linear(pts) : null;
  }

  // ================================================================ the spectrum screen
  function drawSpec(x, w, h) {
    var c = shownCounts(), PL = 54, PB = 34, PT = 16, PR = 12, n = NCH, calibrated = TASK !== 0 && TASK !== 5;
    x.fillStyle = '#0d1a14'; x.fillRect(0, 0, w, h);
    var span = Math.max(48, Math.round(n / Math.pow(4, st.zoom))), x0 = Math.max(0, Math.min(n - span, Math.round(st.cursor - span / 2))), x1 = x0 + span;
    var ymax = 10, i, X = function (ch) { return PL + (ch - x0) / (x1 - x0) * (w - PL - PR); };
    if (c) for (i = x0; i < x1; i++) if (c[i] > ymax) ymax = c[i];
    ymax = ymax * 1.12;
    var Y = function (v) { return h - PB - v / ymax * (h - PB - PT); };
    x.strokeStyle = 'rgba(160,230,190,.16)'; x.lineWidth = 1; x.fillStyle = '#9fe0b8'; x.font = Math.round(h * 0.052) + 'px "JetBrains Mono", monospace';
    for (i = 0; i <= 4; i++) { var yv = ymax * i / 4; x.beginPath(); x.moveTo(PL, Y(yv)); x.lineTo(w - PR, Y(yv)); x.stroke(); x.textAlign = 'right'; x.fillText(String(Math.round(yv)), PL - 5, Y(yv) + 4); }
    x.textAlign = 'center';
    for (i = 0; i <= 5; i++) { var cv = x0 + (x1 - x0) * i / 5; x.beginPath(); x.moveTo(X(cv), PT); x.lineTo(X(cv), h - PB); x.stroke();
      x.fillText(calibrated ? String(Math.round(ecal(cv))) : String(Math.round(cv)), X(cv), h - PB + 16); }
    x.fillText(calibrated ? 'energy (keV)' : 'channel', PL + (w - PL - PR) / 2, h - 5);
    if (c) {
      x.strokeStyle = '#6dffa4'; x.lineWidth = 1.6; x.beginPath();
      var px = w - PL - PR, col, k, mx, first = true;
      for (col = 0; col <= px; col++) {
        var a = x0 + Math.floor(col / px * (x1 - x0)), b = Math.max(a + 1, x0 + Math.floor((col + 1) / px * (x1 - x0)));
        mx = 0; for (k = a; k < b && k < n; k++) if (c[k] > mx) mx = c[k];
        if (first) { x.moveTo(PL + col, Y(mx)); first = false; } else x.lineTo(PL + col, Y(mx));
      }
      x.stroke();
    }
    if (st.fit) { x.strokeStyle = 'rgba(255,196,80,.55)'; x.lineWidth = 6; x.beginPath(); x.moveTo(X(st.fit.mu - st.fit.fwhmCh / 2), h - PB - 5); x.lineTo(X(st.fit.mu + st.fit.fwhmCh / 2), h - PB - 5); x.stroke(); }
    x.strokeStyle = '#ffd24a'; x.lineWidth = 1.5; x.setLineDash([5, 4]); x.beginPath(); x.moveTo(X(st.cursor), PT); x.lineTo(X(st.cursor), h - PB); x.stroke(); x.setLineDash([]);
    x.fillStyle = '#ffd24a'; x.textAlign = 'left';
    x.fillText('cursor: ch ' + st.cursor + (calibrated ? '  ' + r1(ecal(st.cursor), 1) + ' keV' : ''), PL + 6, PT + 14);
    if (!c) { x.fillStyle = '#6aa88a'; x.textAlign = 'center'; x.fillText('no spectrum yet', PL + (w - PL - PR) / 2, h / 2); }
  }
  function paintPanel() { if (panelCv && panelCv.isConnected) { drawSpec(panelCv.getContext('2d'), panelCv.width, panelCv.height); } }

  // ================================================================ the bench
  var leadM = new T.MeshStandardMaterial({ color: 0x53565c, roughness: 0.72, metalness: 0.55 });
  var castle = new T.Group(); S.scene.add(castle); castle.position.set(-0.46, 0, -0.30);
  function brick(x, y, z, w, hh, d) { var b = S.rounded(w, d, hh, 0.004, leadM); b.rotation.x = -Math.PI / 2; b.position.set(x, y + hh / 2, z); castle.add(b); return b; }
  var CH = 0.62;
  for (var r = 0; r < 7; r++) { brick(-0.135, r * 0.0885, 0.0, 0.05, 0.0865, 0.30); brick(0.135, r * 0.0885, 0.0, 0.05, 0.0865, 0.30); brick(0.0, r * 0.0885, -0.125, 0.22, 0.0865, 0.05); }
  brick(0.0, CH, -0.04, 0.32, 0.03, 0.22);
  var floorP = S.rounded(0.3, 0.3, 0.012, 0.004, M.darkWood); floorP.rotation.x = -Math.PI / 2; floorP.position.set(0, 0.006, 0); castle.add(floorP);
  var FACE = 0.50;
  var det = new T.Group(); castle.add(det); det.position.set(0, FACE, 0);
  var canM = new T.MeshStandardMaterial({ color: PLASTIC ? 0xcfe3ee : 0xb9bec5, roughness: 0.3, metalness: PLASTIC ? 0.1 : 0.85 });
  if (HPGE) {
    var cap = S.mesh(new T.CylinderGeometry(0.043, 0.043, 0.12, 36), canM); cap.position.y = 0.06; det.add(cap);
    var capd = S.mesh(new T.CylinderGeometry(0.043, 0.043, 0.002, 36), new T.MeshStandardMaterial({ color: 0xd5d8dc, roughness: 0.25, metalness: 0.9 })); capd.position.y = 0.001; det.add(capd);
    var cold = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.12, 24), canM); cold.position.set(0, 0.18, 0); det.add(cold);
    var dewar = S.mesh(new T.CylinderGeometry(0.1, 0.1, 0.34, 40), new T.MeshStandardMaterial({ color: 0x8c9199, roughness: 0.4, metalness: 0.7 })); dewar.position.set(0.0, 0.3, 0.0); castle.add(dewar);
    dewar.position.set(0, CH + 0.2, -0.04);
    var dlbl = S.label('LIQUID NITROGEN', { w: 0.1, ratio: 0.16, color: '#ffffff', bg: '#2a6fb0' }); dlbl.position.set(0, CH + 0.2, 0.062); castle.add(dlbl);
    S.addApparatus('det', det, DET, 'A coaxial high-purity germanium crystal in a vacuum cryostat. It is kept near 77 K by liquid nitrogen: the energy of each photon is read to about a thousandth of its value.');
    S.addApparatus('dewar', dewar, 'Liquid-nitrogen dewar', 'The cold finger runs from this dewar to the crystal. Never let the dewar run dry with the high voltage on.');
  } else {
    var can = S.mesh(new T.CylinderGeometry(0.0432, 0.0432, 0.1, 40), canM); can.position.y = 0.05; det.add(can);
    var win = S.mesh(new T.CylinderGeometry(0.0398, 0.0398, 0.003, 40), new T.MeshStandardMaterial({ color: PLASTIC ? 0xa8d4ee : 0xe6e8ea, roughness: 0.15, metalness: 0.4 })); win.position.y = 0.0015; det.add(win);
    var pmt = S.mesh(new T.CylinderGeometry(0.0375, 0.0375, 0.14, 36), new T.MeshStandardMaterial({ color: 0x2c3138, roughness: 0.5, metalness: 0.5 })); pmt.position.y = 0.17; det.add(pmt);
    var base = S.mesh(new T.CylinderGeometry(0.04, 0.04, 0.06, 36), M.bakelite); base.position.y = 0.27; det.add(base);
    S.addApparatus('det', det, DET, 'A scintillation crystal sealed behind an aluminium window, optically coupled to a photomultiplier tube. A gamma ray that stops in the crystal makes a flash of light proportional to the energy it leaves there.');
  }
  var rod = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.44, 16), M.chrome); rod.position.set(0.075, 0.28, 0.09); castle.add(rod);
  var rodB = S.rounded(0.05, 0.05, 0.008, 0.003, M.iron); rodB.rotation.x = -Math.PI / 2; rodB.position.set(0.075, 0.004, 0.09); castle.add(rodB);
  var scaleTex = S.canvasTex(64, 700, function (x, w, h) { x.fillStyle = '#f1efe8'; x.fillRect(0, 0, w, h); x.fillStyle = '#16171a'; x.font = '600 20px "Public Sans", sans-serif'; x.textAlign = 'left';
    for (var cm = 0; cm <= 40; cm += 1) { var yy = (cm / 40) * (h - 20) + 10; x.fillRect(0, yy, cm % 5 === 0 ? 30 : 16, 2); if (cm % 5 === 0) x.fillText(String(cm), 33, yy + 7); } });
  var scaleP = new T.Mesh(new T.PlaneGeometry(0.014, 0.4), new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.6 }));
  scaleP.position.set(0.075, FACE - 0.2, 0.0985); castle.add(scaleP);
  var carrier = new T.Group(); castle.add(carrier);
  var arm = S.mesh(new T.BoxGeometry(0.075, 0.006, 0.012), M.alu); arm.position.set(0.0375, 0, 0.09); carrier.add(arm);
  var collar = S.mesh(new T.CylinderGeometry(0.0095, 0.0095, 0.016, 20), M.iron); collar.position.set(0.075, 0, 0.09); carrier.add(collar);
  var cup = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.004, 24), M.alu); cup.position.set(0.0, 0.004, 0.0); carrier.add(cup);
  var arm2 = S.mesh(new T.BoxGeometry(0.075, 0.004, 0.006), M.alu); arm2.position.set(0.0375, 0.004, 0.0); carrier.add(arm2);
  function carrierY(d) { return FACE - d / 100 - 0.004; }
  carrier.position.y = carrierY(st.d);
  S.addApparatus('castle', castle, 'Lead castle', 'Lead bricks keep the room background out of the detector and keep the radiation in. It is open at the front so the source can be put on its rail with the tongs.');
  S.addApparatus('rail', carrier, 'Source rail and distance scale', 'The source cup slides on a vertical rail. The scale is read from the detector face to the source, in centimetres.');

  // lead store with the sealed sources, and the tongs
  var store = new T.Group(); S.scene.add(store); store.position.set(-0.50, 0, 0.12);
  var sbody = S.rounded(0.36, 0.12, 0.05, 0.006, leadM); sbody.rotation.x = -Math.PI / 2; sbody.position.set(0, 0.025, 0); store.add(sbody);
  var slbl = S.label('SEALED SOURCE STORE - LOCKED', { w: 0.3, ratio: 0.1, color: '#e8e8ea' }); slbl.rotation.x = -Math.PI / 2; slbl.position.set(0, 0.0512, 0.045); store.add(slbl);
  var disc = {}, slot = {}, vialNames = {};
  var order = SOURCES.slice(), k0;
  for (k0 = 0; k0 < order.length; k0++) {
    var si = order[k0], sx = -0.15 + k0 * (0.3 / Math.max(1, order.length - 1)); if (order.length === 1) sx = 0;
    var hole = S.mesh(new T.CylinderGeometry(0.0125, 0.0125, 0.004, 24), new T.MeshStandardMaterial({ color: 0x17181b })); hole.position.set(sx, 0.0505, -0.01); store.add(hole);
    var dg = new T.Group(); dg.position.set(sx, 0.054, -0.01); store.add(dg);
    var dd = S.mesh(new T.CylinderGeometry(0.0105, 0.0105, 0.004, 24), new T.MeshStandardMaterial({ color: new T.Color(COLS[si % COLS.length]), roughness: 0.4, metalness: 0.3 })); dg.add(dd);
    var rim = S.mesh(new T.TorusGeometry(0.0105, 0.0012, 8, 24), M.chrome); rim.rotation.x = Math.PI / 2; dg.add(rim);
    var tf = S.canvasTex(128, 128, function (x, w2, h2) { x.fillStyle = '#f2d02a'; x.fillRect(0, 0, w2, h2); x.fillStyle = '#1b1b1b'; x.beginPath(); x.arc(w2 / 2, h2 / 2, 10, 0, 6.2832); x.fill();
      for (var q = 0; q < 3; q++) { x.beginPath(); x.arc(w2 / 2, h2 / 2, 46, q * 2.094 - 0.45, q * 2.094 + 0.45); x.arc(w2 / 2, h2 / 2, 18, q * 2.094 + 0.45, q * 2.094 - 0.45, true); x.closePath(); x.fill(); } });
    var tfm = new T.Mesh(new T.CircleGeometry(0.0085, 24), new T.MeshStandardMaterial({ map: tf, roughness: 0.6 })); tfm.rotation.x = -Math.PI / 2; tfm.position.y = 0.0022; dg.add(tfm);
    var vl = S.label(TASK === 0 && si === UNK ? 'UNKNOWN' : name(si), { w: 0.06, ratio: 0.26, color: '#e8e8ea', px: 256 }); vl.rotation.x = -Math.PI / 2; vl.position.set(sx, 0.0512, 0.025); store.add(vl);
    disc[si] = dg; slot[si] = new T.Vector3(sx, 0.054, -0.01);
  }
  var tongs = new T.Group(); S.scene.add(tongs); tongs.position.set(-0.22, 0.004, 0.2); tongs.rotation.y = 0.35;
  [-1, 1].forEach(function (sg) { var al = S.mesh(new T.BoxGeometry(0.2, 0.004, 0.005), M.chrome); al.position.set(0, 0, sg * 0.006); al.rotation.y = sg * 0.04; tongs.add(al); });
  var hinge = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.016, 12), M.chrome); hinge.rotation.x = Math.PI / 2; hinge.position.set(0.07, 0, 0); tongs.add(hinge);
  S.addApparatus('store', store, 'Sealed source store', 'Every sealed source lives in this lead store, locked, and goes back the moment the counting is over. They are handled only with the tongs.');
  S.addApparatus('tongs', tongs, 'Source tongs', 'Long tongs keep your fingers away from the source: distance is the cheapest shielding there is.');

  // the NIM bin: high voltage, spectroscopy amplifier, multichannel analyser
  var nim = new T.Group(); S.scene.add(nim); nim.position.set(0.05, 0, -0.28); nim.rotation.y = -0.12;
  var NW = 0.34, NH = 0.2, ND = 0.22;
  var ncase = S.rounded(NW, ND, NH, 0.01, new T.MeshStandardMaterial({ color: 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); ncase.rotation.x = -Math.PI / 2; ncase.position.y = NH / 2 + 0.004; nim.add(ncase);
  var NFZ = ND / 2 + 0.0062, NPW = NW - 0.014, NPH = NH - 0.014;
  var nTex = S.canvasTex(1300, Math.round(1300 * NPH / NPW), function (x, w, h) {
    var Xx = function (u) { return (u / NPW + 0.5) * w; }, Yy = function (v) { return (0.5 - v / NPH) * h; };
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3;
    for (var m = 0; m < 3; m++) { x.strokeRect(10 + m * w / 3, 10, w / 3 - 20, h - 20); }
    x.fillStyle = '#f1efe8'; x.textAlign = 'center'; x.font = '700 34px "Public Sans", sans-serif';
    x.fillText('HIGH VOLTAGE', w / 6, 66); x.fillText('SPECTROSCOPY AMP', w / 2, 66); x.fillText('MCA ' + NCH + ' CH', 5 * w / 6, 66);
    x.font = '500 24px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6';
    x.fillText(HPGE ? '0 - +5000 V  ·  POSITIVE' : '0 - +1500 V  ·  POSITIVE', w / 6, 100);
    x.fillText('GAIN ' + NOMG + ' keV / channel (nominal)', w / 2, 100); x.fillText('LIVE TIME  ·  COUNTS', 5 * w / 6, 100);
    x.font = '700 26px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8'; x.fillText('HV', w / 6, Yy(-0.058)); x.fillText('START', 5 * w / 6, Yy(-0.058)); });
  var nfac = S.mesh(new T.BoxGeometry(NPW, NPH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: nTex, roughness: 0.45 }), M.grey]);
  nfac.position.set(0, 0.004 + NH / 2, NFZ - 0.002); nim.add(nfac);
  function nup(u, v, dz) { return new T.Vector3(u, 0.004 + NH / 2 + v, NFZ + (dz || 0)); }
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  var hvK = new T.Group(); hvK.position.copy(nup(-NW / 3 + 0.0, -0.02)); nim.add(hvK);
  var hvS = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.004, 36), M.bakelite); hvS.rotation.x = Math.PI / 2; hvS.position.z = 0.002; hvK.add(hvS);
  var hvB = S.mesh(new T.CylinderGeometry(0.0145, 0.016, 0.016, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); hvB.rotation.x = Math.PI / 2; hvB.position.z = 0.012; hvK.add(hvB);
  var hvP = S.mesh(new T.BoxGeometry(0.002, 0.016, 0.0012), M.white, false); hvP.position.set(0, 0.009, 0.0215); hvK.add(hvP);
  function hvAngle(on) { return on ? -0.9 : 2.3; } hvK.rotation.z = hvAngle(false);
  var hvLed = S.mesh(new T.SphereGeometry(0.005, 14, 14), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 })); hvLed.position.copy(nup(-NW / 3, 0.045, 0.002)); nim.add(hvLed);
  var startB = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.008, 20), M.green); startB.rotation.x = Math.PI / 2; startB.position.copy(nup(NW / 3, -0.035, 0.004)); nim.add(startB);
  function lcd(cx, cy, wd, hg) {
    var tex = S.liveTex(512, 190), last = '';
    var bez = S.mesh(new T.BoxGeometry(wd + 0.006, hg + 0.006, 0.003), M.grey); bez.position.copy(nup(cx, cy, 0.001)); nim.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(wd, hg), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); scr.position.copy(nup(cx, cy, 0.004)); nim.add(scr);
    return function (txt) { if (txt === last) return; last = txt; tex.draw(function (x) { var gr = x.createLinearGradient(0, 0, 0, 190); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); x.fillStyle = gr; x.fillRect(0, 0, 512, 190);
      x.font = '700 92px "JetBrains Mono", monospace'; x.textAlign = 'right'; x.fillStyle = '#1b2116'; x.fillText(txt, 480, 128); }); };
  }
  var showT = lcd(NW / 3, 0.035, 0.1, 0.034), showN = lcd(NW / 3, -0.003, 0.1, 0.034);
  showT('0'); showN('0');
  S.addApparatus('nim', nim, 'NIM bin: HV supply, amplifier and analyser', 'The high-voltage supply powers the detector, the spectroscopy amplifier shapes its pulses, and the multichannel analyser sorts them by height into channels. START counts for the preset live time.');
  // the analyser's monitor
  var mon = new T.Group(); S.scene.add(mon); mon.position.set(0.44, 0, -0.30); mon.rotation.y = -0.38;
  var mbody = S.rounded(0.36, 0.23, 0.03, 0.008, new T.MeshStandardMaterial({ color: 0x1b1d21, roughness: 0.45, metalness: 0.3 })); mbody.position.set(0, 0.2, 0); mon.add(mbody);
  var mstem = S.mesh(new T.BoxGeometry(0.04, 0.1, 0.03), M.iron); mstem.position.set(0, 0.07, -0.01); mon.add(mstem);
  var mbase = S.rounded(0.2, 0.14, 0.012, 0.006, M.iron); mbase.rotation.x = -Math.PI / 2; mbase.position.set(0, 0.006, 0.0); mon.add(mbase);
  var screenTex = S.liveTex(1024, 640), spaint = function () { screenTex.draw(function (x, w, h) { drawSpec(x, w, h); }); };
  var mscr = new T.Mesh(new T.PlaneGeometry(0.33, 0.33 * 640 / 1024), new T.MeshBasicMaterial({ map: screenTex, toneMapped: false })); mscr.position.set(0, 0.2, 0.017); mon.add(mscr);
  S.addApparatus('monitor', mon, 'Analyser display', 'The spectrum builds up here, counts against channel (or energy). The dashed line is your cursor.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  S.contact(0.4, 0.4, -0.46, -0.30, 0.5); S.contact(0.4, 0.2, -0.50, 0.12, 0.45); S.contact(0.4, 0.26, 0.05, -0.28, 0.5); S.contact(0.4, 0.24, 0.44, -0.30, 0.5);
  S.wire([[-0.46, 0.5, -0.30], [-0.46, 0.7, -0.38], [-0.1, 0.18, -0.34], [0.0, 0.1, -0.28]], 'black');
  var hudD = S.hudCard('Source distance'), hudT = S.hudCard('Live time'), hudR = S.hudCard('Readings');

  // ================================================================ human actions
  function turnHV(on) {
    if (busy()) return Promise.resolve();
    if (st.hv === on) return Promise.resolve();
    var pt = wpt(nim, -NW / 3, 0.004 + NH / 2 - 0.02, NFZ + 0.024), a0 = hvAngle(st.hv), a1 = hvAngle(on);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { hvK.rotation.z = a0 + (a1 - a0) * k; }, { mode: 'front', ms: 700, reachMs: 600 })
      .then(function () { st.hv = on; hvK.rotation.z = a1; hvLed.material.emissive.setHex(on ? 0x22cc44 : 0x000000); hvLed.material.color.setHex(on ? 0x33dd55 : 0x331111);
        S.say(on ? 'High voltage on, raised slowly to the working value. The detector is live.' : 'High voltage off.'); S.render(); });
  }
  function unload() {
    if (st.loaded < 0) return Promise.resolve();
    if (busy()) return Promise.resolve();
    var si = st.loaded, g = disc[si], from = g.position.clone(), to = slot[si].clone(), cl = wpt(carrier, 0, 0.007, 0);
    var local0 = from.clone();
    return S.hand.pinchMove(wpt(castle, 0, carrierY(st.d) + 0.006, 0), function (k) { return new T.Vector3().lerpVectors(cl, wpt(store, to.x, 0.08, to.z), k).add(new T.Vector3(0, 0.05 * Math.sin(Math.PI * k), 0)); },
      function (k) { var w = new T.Vector3().lerpVectors(cl, wpt(store, to.x, 0.054, to.z), k); w.y += 0.05 * Math.sin(Math.PI * k); g.parent.worldToLocal(w); g.position.copy(w); }, { mode: 'side', ms: 1000, reachMs: 600 })
      .then(function () { g.position.copy(to); st.loaded = -1; st.cdata = null; st.shown = 0; st.fit = null; dirty = true; S.say(name(si) + ' is back in its lead store.'); S.render(); });
  }
  function load(si) {
    if (busy()) return Promise.resolve();
    if (st.loaded === si) return Promise.resolve();
    var chain = st.loaded >= 0 ? unload() : Promise.resolve();
    return chain.then(function () {
      var g = disc[si], from = wpt(store, slot[si].x, 0.054, slot[si].z), to = wpt(castle, 0, carrierY(st.d) + 0.0075, 0);
      g.parent.remove(g); S.scene.add(g); g.position.copy(from);
      return S.hand.pinchMove(from, function (k) { return new T.Vector3().lerpVectors(from, to, k).add(new T.Vector3(0, 0.06 * Math.sin(Math.PI * k), 0)); },
        function (k) { g.position.lerpVectors(from, to, k); g.position.y += 0.06 * Math.sin(Math.PI * k); tongs.position.set(g.position.x + 0.08, g.position.y, g.position.z + 0.05); }, { mode: 'side', ms: 1100, reachMs: 700 })
        .then(function () { g.position.copy(to); g.parent.remove(g); carrier.add(g); g.position.set(0, 0.0075, 0); st.loaded = si; st.cdata = null; st.shown = 0; st.fit = null; dirty = true;
          S.say(name(si) + ' on the rail, ' + st.d + ' cm below the detector face, put there with the tongs from behind the lead.'); S.render(); });
    });
  }
  function setDistance(d) {
    if (busy()) return Promise.resolve();
    if (!isFinite(d) || d < 3 || d > 40) { S.say('The rail reads from 3 to 40 cm.'); return Promise.resolve(); }
    var d0 = st.d, wasLoaded = st.loaded;
    return S.tween(500, function (k) { st.d = d0 + (d - d0) * k; carrier.position.y = carrierY(st.d); }).then(function () {
      st.d = d; carrier.position.y = carrierY(d); st.cdata = null; st.shown = 0; st.fit = null; dirty = true; S.render(); });
  }
  function acquire() {
    if (busy()) return Promise.resolve(false);
    if (!st.hv) { S.say('Switch the high voltage on first.'); return Promise.resolve(false); }
    if (st.loaded < 0) { S.say('Put a source on the rail with the tongs first.'); return Promise.resolve(false); }
    if (st.acq) return Promise.resolve(false);
    var q = Q(), key = [q.src, q.d, q.t, q.seed].join('/');
    if (st.key !== key || !st.cdata) { st.cdata = KN.counts(q); st.key = key; st.total = 0; for (var ii = 0; ii < st.cdata.length; ii++) st.total += st.cdata[ii]; }
    st.acq = true; st.shown = 0; st.fit = null; st.edge = null; dirty = true; st.cursor = Math.round(NCH * 0.25);
    return S.hand.tap(startB, 'front').then(function () { return S.tween(1500, function (k) { st.shown = k; st.live = st.t * k; dirty = true; }); }).then(function () {
      st.acq = false; st.shown = 1; st.live = st.t; dirty = true;
      var tot = st.total;
      S.say('Counted ' + name(st.loaded) + (TASK === 0 && st.loaded === UNK ? ' (unknown)' : '') + ' for ' + st.t + ' s of live time: ' + tot + ' counts in the spectrum.'); S.render(); return true; });
  }
  function setCursor(c) { st.cursor = Math.max(3, Math.min(NCH - 4, Math.round(c))); st.fit = null; dirty = true; }
  function findTallest() {
    var c = shownCounts(); if (!c || st.shown < 1) { S.say('Take a spectrum first.'); return false; }
    var i = tallest(c); if (i < 0) { S.say('Nothing stands out of the background yet.'); return false; }
    setCursor(i); S.render(); return true;
  }
  function findNext() {
    var c = shownCounts(); if (!c || st.shown < 1) { S.say('Take a spectrum first.'); return false; }
    var i = nextPeak(c, st.cursor + Math.max(3, Math.round(fwhmCh(st.cursor) / 2)));
    if (i < 0) { S.say('No further peak above the cursor.'); return false; }
    setCursor(i); S.render(); return true;
  }
  function doFit() {
    var c = shownCounts(); if (!c || st.shown < 1) { S.say('Take a spectrum first.'); return null; }
    if (TASK === 3) { var e = findEdge(c); st.edge = e; setCursor(e); st.edge = e; S.say('The continuum falls steepest at channel ' + e + ', ' + r1(ecal(e), 1) + ' keV: that is the Compton edge.'); dirty = true; S.render(); return { edge: e }; }
    var f = fitPeak(c, st.cursor);
    if (!f) { S.say('There is no clear peak near the cursor. Move it onto a peak.'); st.fit = null; dirty = true; return null; }
    st.fit = f; st.cursor = Math.round(f.mu); dirty = true;
    var cal = TASK === 0 || TASK === 5 ? null : null;
    S.say('Gaussian fit: centroid channel ' + r1(f.mu, 2) + (TASK !== 0 && TASK !== 5 ? ' (' + r1(ecal(f.mu), 2) + ' keV)' : '') + ', FWHM ' + r1(f.fwhmCh, 2) + ' channels, net area ' + Math.round(f.area) + ' counts.');
    S.render(); return f;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    var f = st.fit, c = shownCounts();
    if (TASK === 3) {
      if (st.edge === null || !c) { S.say('Press "Find the edge" first.'); return false; }
      S.addRow({ kind: 'e', name: name(st.loaded), ch: st.edge, E: ecal(st.edge) }); return true;
    }
    if (!f) { S.say('Fit a peak first: put the cursor on it and press the fit button.'); return false; }
    var line;
    if (TASK === 0) {
      if (st.loaded === UNK) {
        if (S.rows.some(function (r) { return r.kind === 'u'; })) { S.say('The unknown is already recorded.'); return false; }
        S.addRow({ kind: 'u', name: 'Unknown', ch: f.mu, E: NaN }); return true;
      }
      if (S.rows.some(function (r) { return r.kind === 'k' && r.src === st.loaded; })) { S.say(name(st.loaded) + ' is already recorded.'); return false; }
      line = lineFor(st.loaded, f.mu);
      if (!line) { S.say('That peak does not match a line of ' + name(st.loaded) + '.'); return false; }
      S.addRow({ kind: 'k', src: st.loaded, name: name(st.loaded), ch: f.mu, E: line.E }); return true;
    }
    if (TASK === 5) {
      line = lineFor(st.loaded, f.mu);
      if (!line) { S.say('That peak does not match a calibration line of ' + name(st.loaded) + '.'); return false; }
      if (S.rows.some(function (r) { return Math.abs(r.E - line.E) < 0.01; })) { S.say('The ' + r1(line.E, 1) + ' keV line is already recorded.'); return false; }
      S.addRow({ kind: 'k', src: st.loaded, name: name(st.loaded), ch: f.mu, E: line.E, fw: f.fwhmCh * p.gain }); return true;
    }
    var E = ecal(f.mu), fwE = f.fwhmCh * p.gain;
    if (TASK === 2) {
      line = lineFor(st.loaded, f.mu); if (!line) { S.say('That peak does not match a line of ' + name(st.loaded) + '.'); return false; }
      if (S.rows.some(function (r) { return Math.abs(r.d - st.d) < 1e-9; })) { S.say('A reading at ' + st.d + ' cm is already in the book.'); return false; }
      var emitted = st.t * p.act * 1000 * line.w * line.I, om = KN.omega(assign(p, { d: st.d }));
      S.addRow({ kind: 'd', name: name(st.loaded), d: st.d, E: line.E, area: f.area, eff: f.area / emitted, om: om, ei: f.area / emitted / om }); return true;
    }
    if (TASK === 4) {
      if (S.rows.some(function (r) { return Math.abs(r.E - E) < 0.6; })) { S.say('That peak is already recorded.'); return false; }
      S.addRow({ kind: 'p', name: name(st.loaded), E: E, ch: f.mu, area: f.area, h: f.peak, fw: fwE }); return true;
    }
    S.addRow({ kind: 'r', name: name(st.loaded), E: E, ch: f.mu, fw: fwE, res: fwE / E * 100, t: st.t });
    return true;
  }
  function rowsOf(kind) { return S.rows.filter(function (r) { return r.kind === kind; }); }

  // ================================================================ result
  function truthE() { return KN.mainLine(assign(p, { src: UNK })).E; }
  function result(rows) {
    var k, f, i, v;
    if (TASK === 0) {
      var cal = calFit(), u = rows.filter(function (r) { return r.kind === 'u'; })[0];
      if (!cal || !u) return null;
      return { label: 'Energy of the unknown source\'s peak', value: cal.c + cal.m * u.ch, unit: 'keV', digits: 1, truth: truthE(),
        note: 'Calibration line E = ' + r1(cal.c, 2) + ' + ' + cal.m.toFixed(4) + ' × channel from ' + rows.filter(function (r) { return r.kind === 'k'; }).length + ' known peaks.' };
    }
    if (TASK === 5) {
      f = calFit(); if (!f || rows.filter(function (r) { return r.kind === 'k'; }).length < 4) return null;
      return { label: 'Energy per channel (gain)', value: f.m, unit: 'keV/channel', digits: 5, truth: p.gain, note: 'Intercept ' + r1(f.c, 2) + ' keV; ' + rows.length + ' Eu-152 lines fitted.' };
    }
    k = rows.filter(function (r) { return r.kind === 'r'; });
    if (TASK === 1) {
      if (!k.length) return null; v = S.fit.mean(HPGE ? k.map(function (r) { return r.fw; }) : k.map(function (r) { return r.res; }));
      var mainE = KN.mainLine(p).E;
      return HPGE ? { label: 'FWHM of the ' + r1(k[0].E, 1) + ' keV peak', value: v, unit: 'keV', digits: 3, truth: KN.fwhm(mainE, p), note: 'From ' + k.length + ' fit' + (k.length > 1 ? 's' : '') + '; resolution ' + r1(v / k[0].E * 100, 3) + ' %.' }
        : { label: 'Energy resolution at ' + r1(k[0].E, 1) + ' keV', value: v, unit: '%', digits: 2, truth: KN.fwhm(mainE, p) / mainE * 100, note: 'FWHM ÷ peak energy, from ' + k.length + ' fit' + (k.length > 1 ? 's' : '') + '.' };
    }
    if (TASK === 2) {
      k = rows.filter(function (r) { return r.kind === 'd'; }); if (k.length < 4) return null;
      var mE = k[0].E, truth = KN.et(mE, p) * KN.pf(mE, p) * 100;
      return { label: 'Intrinsic photopeak efficiency at ' + r1(mE, 1) + ' keV', value: 100 * S.fit.mean(k.map(function (r) { return r.ei; })), unit: '%', digits: 2, truth: truth,
        note: 'Area ÷ (photons emitted × solid-angle fraction), averaged over ' + k.length + ' distances.' };
    }
    if (TASK === 3) {
      k = rows.filter(function (r) { return r.kind === 'e'; }); if (!k.length) return null;
      var e0 = KN.mainLine(assign(p, { pf662: 0 })).E, al = SRCT[UNK][1][0][0] / 510.99895;
      return { label: 'Compton edge', value: S.fit.mean(k.map(function (r) { return r.E; })), unit: 'keV', digits: 1, truth: 2 * al / (1 + 2 * al) * SRCT[UNK][1][0][0],
        note: 'The edge is the largest energy a Compton electron can take: 2α/(1+2α) × E.' };
    }
    k = rows.filter(function (r) { return r.kind === 'p'; }); if (k.length < 3) return null;
    var best = k[0]; for (i = 1; i < k.length; i++) if (k[i].h > best.h) best = k[i];
    return { label: 'Energy of the strongest line', value: best.E, unit: 'keV', digits: 1, truth: truthE(), note: k.length + ' peaks recorded; the tallest is the one named.' };
  }

  // ================================================================ per-task text
  var TXT = {
    0: { aim: 'Calibrate the channel scale with known gamma lines, then read the energy of an unknown source.',
      principle: 'A gamma ray that is stopped completely in the crystal gives a pulse whose height is proportional to its energy. The analyser sorts the pulses by height into channels, so a photopeak sits at a channel number that is a straight line in energy: E = a + b × channel. Two or more peaks of known energy fix the line; the unknown peak is then read off it.',
      formula: 'E = a + b · channel', note: 'a and b from a straight-line fit through the known peaks' },
    1: { principle: 'A photopeak is not a line but a Gaussian, because the number of light photons (or charge carriers) made by one gamma ray fluctuates. The full width at half maximum divided by the energy is the energy resolution. For a scintillator it falls as 1/√E; for germanium the width is only a few hundred times smaller.',
      formula: 'R = FWHM / E     (FWHM = 2.355 σ)', note: 'a good NaI(Tl) crystal gives about 7 % at 662 keV' },
    2: { principle: 'Only a fraction of the photons a source emits reach the crystal (the solid-angle fraction), and only a fraction of those leave all their energy in it. The counts in the photopeak divided by the photons emitted is the absolute photopeak efficiency; dividing by the geometric fraction leaves the intrinsic efficiency of the crystal, which does not change with distance.',
      formula: 'ε_abs = N_peak / (A t I)     ε_int = ε_abs / Ω,   Ω = ½ (1 − d / √(d² + a²))', note: 'a is the crystal radius' },
    3: { principle: 'A photon that scatters once in the crystal and escapes leaves only the recoil electron\'s energy, which runs from zero up to a maximum: the Compton edge, 2α/(1+2α) × E with α = E / 511 keV. A plastic scintillator has too low a atomic number to have a photopeak at all, so the edge is its only landmark.',
      formula: 'T_max = E · 2α / (1 + 2α)', note: 'α = E / m_e c²' },
    4: { principle: 'Natural radioactivity in soil shows up as sharp lines on top of a low continuum. Every line is a signature of a nuclide: Bi-214 and Pb-214 (the uranium series), Ac-228 and Tl-208 (thorium series) and K-40. A germanium detector separates them because its resolution is about 1.8 keV at 1.3 MeV.',
      formula: 'Activity ∝ net peak area / (I · ε · t)', note: 'the energy identifies the nuclide' },
    5: { principle: 'Europium-152 has a long list of lines from 122 to 1408 keV, all of them known to a fraction of a keV. Fitting channel against energy for several of them gives the energy per channel of the analyser, and the departure of the points from the line shows its linearity.',
      formula: 'E = a + b · channel', note: 'b is the energy per channel' }
  };
  var TT = TXT[TASK] || TXT[1];

  // ================================================================ steps
  function spectrumPanel(u) {
    var cv = document.createElement('canvas'); cv.width = 760; cv.height = 330; cv.style.cssText = 'width:100%;border-radius:10px;border:1px solid var(--line);background:#0d1a14';
    u.el(cv); panelCv = cv; paintPanel();
  }
  function cursorControls(u) {
    u.slider('Cursor channel', 3, NCH - 4, 1, function () { return st.cursor; }, function (v) { setCursor(v); paintPanel(); dirty = true; });
    u.row(u.button('Zoom in', function () { st.zoom = Math.min(3, st.zoom + 1); dirty = true; S.render(); }, false, st.zoom >= 3),
      u.button('Zoom out', function () { st.zoom = Math.max(0, st.zoom - 1); dirty = true; S.render(); }, false, st.zoom <= 0),
      u.button('Tallest peak', function () { findTallest(); }, false, !st.cdata || st.shown < 1),
      u.button('Next peak →', function () { findNext(); }, false, !st.cdata || st.shown < 1));
  }
  function sourceButtons(u) {
    var btns = SOURCES.map(function (si) { return u.button((TASK === 0 && si === UNK ? 'Unknown source' : name(si)) + (st.loaded === si ? ' · on rail' : ''), function () { S.focus('store'); load(si); }, st.loaded !== si, S.hand.busy || st.loaded === si); });
    var rows = [], i; for (i = 0; i < btns.length; i += 3) rows.push(btns.slice(i, i + 3));
    rows.forEach(function (r) { u.row.apply(u, r); });
  }
  function tableOrNote(u) { u.h3('Observation table'); u.table(); }
  function stepSetup() {
    return { id: 'setup', title: 'Set up', view: 'nim', render: function (u) {
        u.h2('Switch on and put the source in place');
        u.p(TASK === 0 ? 'Switch the high voltage on, then take a known source from the lead store with the tongs and put it on the rail, ' + st.d + ' cm below the detector.'
          : 'Switch the high voltage on, then take the source from the lead store with the tongs and put it on the rail below the detector.');
        u.task('1. High voltage', st.hv, st.hv ? 'On' : 'Off').add(u.button(st.hv ? 'Switch HV off' : 'Switch HV on', function () { S.focus('nim'); turnHV(!st.hv); }, !st.hv, S.hand.busy));
        u.task('2. Source on the rail', st.loaded >= 0, st.loaded >= 0 ? name(st.loaded) + ' on the rail' : 'All sources in their store');
        sourceButtons(u);
        u.note('Sealed sources are handled with the tongs, from behind the lead, and go back into the locked store as soon as the counting is over. Never point a source at anyone.');
        u.next('Next: take a spectrum', st.hv && st.loaded >= 0);
      }, ok: function () { return st.hv && st.loaded >= 0; },
      auto: function () { return turnHV(true).then(function () { return load(TASK === 0 ? KNOWN[0] : SOURCES[0]); }); } };
  }
  function acqBlock(u) {
    u.slider('Live time', 20, 1000, 10, function () { return st.t; }, function (v) { st.t = v; st.cdata = null; st.shown = 0; st.fit = null; dirty = true; }, 's');
    if (TASK === 2) u.slider('Source distance', 3, 40, 1, function () { return st.d; }, function (v) { if (!S.hand.busy) { st.d = v; carrier.position.y = carrierY(v); st.cdata = null; st.shown = 0; st.fit = null; dirty = true; } }, 'cm');
    u.row(u.button('START (' + st.t + ' s live time)', function () { S.focus('nim'); acquire(); }, !st.cdata || st.shown < 1, S.hand.busy || st.acq));
    u.live(function () { return st.acq ? 'Counting… ' + r1(st.live, 0) + ' s' : st.cdata && st.shown >= 1 ? 'Spectrum of ' + name(st.loaded) + ' · ' + st.t + ' s live time' : 'No spectrum yet'; });
    spectrumPanel(u);
  }
  var STEPS = [stepSetup()];
  if (TASK === 0) {
    STEPS.push({ id: 'known', title: 'Known sources', view: 'monitor', render: function (u) {
        u.h2('Find the peak of each known source');
        u.p('For each known source: put it on the rail, take a spectrum, put the cursor on its tallest peak, fit the peak and write the centroid channel in the book. At least three known sources.');
        sourceButtons(u); acqBlock(u); cursorControls(u);
        u.row(u.button('Fit the peak at the cursor', function () { doFit(); }, true, !st.cdata || st.shown < 1), u.button('Write it down', function () { record(); }, false, !st.fit));
        u.live(function () { return st.fit ? 'Centroid ch ' + r1(st.fit.mu, 2) + ' · FWHM ' + r1(st.fit.fwhmCh, 1) + ' ch · area ' + Math.round(st.fit.area) : 'No fit yet'; });
        tableOrNote(u);
        u.next('Next: the unknown source', rowsOf('k').length >= 3);
      }, ok: function () { return rowsOf('k').length >= 3; },
      auto: function () {
        var chain = Promise.resolve();
        KNOWN.forEach(function (si) { chain = chain.then(function () { return load(si); }).then(function () { return acquire(); }).then(function () { findTallest(); doFit(); record(); }); });
        return chain; } });
    STEPS.push({ id: 'unknown', title: 'Unknown source', view: 'monitor', render: function (u) {
        u.h2('The unknown source');
        u.p('Put the unknown source on the rail, take its spectrum, fit its tallest peak and write it down. The book then reads its energy off your calibration line.');
        u.task('Calibration line', !!calFit(), calFit() ? 'E = ' + r1(calFit().c, 2) + ' + ' + calFit().m.toFixed(4) + ' ch' : 'needs two known peaks');
        sourceButtons(u); acqBlock(u); cursorControls(u);
        u.row(u.button('Fit the peak at the cursor', function () { doFit(); }, true, !st.cdata || st.shown < 1), u.button('Write it down', function () { record(); }, false, !st.fit));
        var cal = calFit();
        u.live(function () { return st.fit && cal ? 'Centroid ch ' + r1(st.fit.mu, 2) + ' → ' + r1(cal.c + cal.m * st.fit.mu, 1) + ' keV' : 'No fit yet'; });
        tableOrNote(u);
        u.next('Next: result', rowsOf('u').length >= 1);
      }, ok: function () { return rowsOf('u').length >= 1; },
      auto: function () { return load(UNK).then(function () { return acquire(); }).then(function () { findTallest(); doFit(); record(); }).then(function () { return unload(); }); } });
  } else if (TASK === 5) {
    STEPS.push({ id: 'lines', title: 'Calibration lines', view: 'monitor', render: function (u) {
        u.h2('Fit the Eu-152 lines');
        u.p('Take a spectrum, then step through the peaks with "Next peak". Fit each one and write it down; the book matches it to the line of the nuclear-data table (the amplifier is marked ' + NOMG + ' keV per channel). Record at least four, spread over the range.');
        acqBlock(u); cursorControls(u);
        u.row(u.button('Fit the peak at the cursor', function () { doFit(); }, true, !st.cdata || st.shown < 1), u.button('Write it down', function () { record(); }, false, !st.fit));
        u.live(function () { return st.fit ? 'Centroid ch ' + r1(st.fit.mu, 2) + ' · FWHM ' + r1(st.fit.fwhmCh * p.gain, 2) + ' keV' : 'No fit yet'; });
        tableOrNote(u);
        u.next('Next: result', rowsOf('k').length >= 4);
      }, ok: function () { return rowsOf('k').length >= 4; },
      auto: function () {
        return acquire().then(function () { setCursor(3); var guard = 0;
          while (rowsOf('k').length < 6 && guard++ < 14) { if (!findNext()) break; if (doFit()) record(); }
          return true; }); } });
  } else if (TASK === 4) {
    STEPS.push({ id: 'peaks', title: 'Find the lines', view: 'monitor', render: function (u) {
        u.h2('Search the soil spectrum');
        u.p('A long count, ' + st.t + ' s. Step through the peaks with "Next peak", fit each and write it down (at least three). The energies identify the nuclides.');
        acqBlock(u); cursorControls(u);
        u.row(u.button('Fit the peak at the cursor', function () { doFit(); }, true, !st.cdata || st.shown < 1), u.button('Write it down', function () { record(); }, false, !st.fit));
        u.live(function () { return st.fit ? 'Peak at ' + r1(ecal(st.fit.mu), 2) + ' keV · net area ' + Math.round(st.fit.area) : 'No fit yet'; });
        tableOrNote(u);
        u.next('Next: result', rowsOf('p').length >= 3);
      }, ok: function () { return rowsOf('p').length >= 3; },
      auto: function () {
        return acquire().then(function () { setCursor(3); var guard = 0;
          while (rowsOf('p').length < 7 && guard++ < 14) { if (!findNext()) break; if (doFit()) record(); }
          return true; }); } });
  } else if (TASK === 2) {
    STEPS.push({ id: 'dist', title: 'Counts against distance', view: 'rail', render: function (u) {
        u.h2('The photopeak area at several distances');
        u.p('Move the source along the rail, take a spectrum at each distance, fit the peak and write its net area down. Take at least four distances between 5 and 30 cm. The book works out the efficiencies.');
        acqBlock(u); cursorControls(u);
        u.row(u.button('Tallest peak and fit', function () { if (findTallest()) doFit(); }, true, !st.cdata || st.shown < 1), u.button('Write it down', function () { record(); }, false, !st.fit));
        u.live(function () { return st.fit ? 'Area ' + Math.round(st.fit.area) + ' counts at ' + st.d + ' cm' : 'No fit yet'; });
        tableOrNote(u);
        u.next('Next: result', rowsOf('d').length >= 4);
      }, ok: function () { return rowsOf('d').length >= 4; },
      auto: function () {
        var chain = Promise.resolve(); [5, 8, 12, 18, 25, 30].forEach(function (d) { chain = chain.then(function () { return setDistance(d); }).then(function () { return acquire(); }).then(function () { findTallest(); doFit(); record(); }); });
        return chain.then(function () { return unload(); }); } });
  } else {
    STEPS.push({ id: 'spec', title: TASK === 3 ? 'Compton edge' : 'Resolution', view: 'monitor', render: function (u) {
        u.h2(TASK === 3 ? 'Find the Compton edge' : 'Fit the photopeak');
        u.p(TASK === 3 ? 'Take a spectrum. The continuum ends in a drop: press "Find the edge" and the software locates its steepest point. Repeat at a different live time for a second value.'
          : 'Take a spectrum, put the cursor on the photopeak and fit it. The fit gives the centroid and the FWHM. Repeat with a different live time to see how steady the result is.');
        acqBlock(u); cursorControls(u);
        u.row(u.button(TASK === 3 ? 'Find the edge' : 'Fit the peak at the cursor', function () { if (TASK !== 3 && st.cursor < 5) findTallest(); doFit(); }, true, !st.cdata || st.shown < 1),
          u.button('Write it down', function () { record(); }, false, TASK === 3 ? st.edge === null : !st.fit));
        u.live(function () { return TASK === 3 ? (st.edge !== null ? 'Edge at ' + r1(ecal(st.edge), 1) + ' keV' : 'No edge yet') : (st.fit ? 'Peak at ' + r1(ecal(st.fit.mu), 1) + ' keV · FWHM ' + r1(st.fit.fwhmCh * p.gain, 2) + ' keV · R = ' + r1(st.fit.fwhmCh * p.gain / ecal(st.fit.mu) * 100, 2) + ' %' : 'No fit yet'); });
        tableOrNote(u);
        u.next('Next: result', S.rows.length >= 1);
      }, ok: function () { return S.rows.length >= 1; },
      auto: function () { return acquire().then(function () { if (TASK !== 3) findTallest(); doFit(); record(); }).then(function () { return unload(); }); } });
  }

  var pageCols = {
    0: [{ label: 'Source', get: function (r) { return r.name; } }, { label: 'Channel', get: function (r) { return r1(r.ch, 2); } },
      { label: 'E (keV)', get: function (r) { var c = calFit(); return r.kind === 'k' ? r1(r.E, 1) : (c ? r1(c.c + c.m * r.ch, 1) : '—'); } }],
    5: [{ label: 'Line', get: function (r) { return r1(r.E, 1) + ' keV'; } }, { label: 'Channel', get: function (r) { return r1(r.ch, 2); } },
      { label: 'FWHM (keV)', get: function (r) { return r1(r.fw, 2); } }],
    1: [{ label: 'Peak (keV)', get: function (r) { return r1(r.E, 2); } }, { label: 'FWHM (keV)', get: function (r) { return r1(r.fw, 2); } },
      { label: 'R = FWHM/E (%)', get: function (r) { return r1(r.res, 2); } }, { label: 't (s)', get: function (r) { return r.t; } }],
    2: [{ label: 'd (cm)', get: function (r) { return r.d; } }, { label: 'Net area', get: function (r) { return Math.round(r.area); } },
      { label: 'ε abs (%)', get: function (r) { return r1(r.eff * 100, 3); } }, { label: 'Ω', get: function (r) { return r.om.toFixed(4); } },
      { label: 'ε int (%)', get: function (r) { return r1(r.ei * 100, 2); } }],
    3: [{ label: 'Edge channel', get: function (r) { return r.ch; } }, { label: 'Edge (keV)', get: function (r) { return r1(r.E, 1); } }],
    4: [{ label: 'E (keV)', get: function (r) { return r1(r.E, 2); } }, { label: 'Net area', get: function (r) { return Math.round(r.area); } },
      { label: 'FWHM (keV)', get: function (r) { return r1(r.fw, 2); } }]
  };
  var gcfg = null;
  if (TASK === 0 || TASK === 5) gcfg = { x: function (r) { return r.kind === 'u' ? NaN : r.ch; }, y: function (r) { return r.kind === 'u' ? NaN : r.E; }, xlabel: 'channel', ylabel: 'E (keV)',
    line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.c + f.m * x; } : null; } };
  if (TASK === 2) gcfg = { x: function (r) { return r.d; }, y: function (r) { return r.eff * 100; }, xlabel: 'distance d (cm)', ylabel: 'absolute efficiency (%)', y0: 0, x0: 0 };

  var VIVA = {
    0: [['Why must the channel scale be calibrated with sources of known energy?', ['The analyser only counts pulses by height; the energy of a channel depends on the gain', 'The detector is not accurate', 'The peaks move when the source is removed'], 0, 'The same crystal gives different channel numbers if the amplifier gain changes.'],
      ['A peak at channel 330 and another at 600 belong to 662 and 1173 keV. Where is a 511 keV peak?', ['About channel 253', 'About channel 450', 'About channel 150'], 0, 'The slope is (1173 − 662) / 270 = 1.89 keV per channel, so 511 keV is 80 channels below 330.']],
    1: [['The energy resolution of a scintillator is the FWHM of the photopeak divided by', ['the peak energy', 'the peak height', 'the number of channels'], 0, 'R = FWHM / E.'],
      ['Doubling the energy changes the resolution of a scintillator (percent) to about', ['0.71 of its value', 'twice its value', 'the same'], 0, 'FWHM goes as √E, so FWHM/E goes as 1/√E.']],
    2: [['Does the intrinsic efficiency of the crystal change with the source distance?', ['No, the solid angle does', 'Yes, it falls as 1/d', 'Yes, it rises as d'], 0, 'The crystal is the same; only the fraction of photons that reach it changes.'],
      ['Why is the absolute efficiency lower than the intrinsic one?', ['Most photons miss the crystal', 'The crystal absorbs more', 'The source decays'], 0, 'The solid-angle fraction Ω is small.']],
    3: [['The Compton edge of a gamma ray of energy E is', ['E · 2α/(1+2α), below E', 'exactly E', 'E/2'], 0, 'The recoil electron cannot take the whole energy; backscatter leaves E/(1+2α) with the photon.'],
      ['Why does a plastic scintillator show no photopeak?', ['Its atomic number is too low for photoelectric absorption', 'It is too small', 'It is too noisy'], 0, 'The photoelectric cross section goes roughly as Z⁴⁻⁵.']],
    4: [['Which of these is NOT a natural radionuclide you expect in soil?', ['Cs-137 from a medical source', 'K-40', 'Bi-214'], 0, 'Soil is dominated by K-40 and the uranium and thorium series.'],
      ['Why does germanium identify nuclides that a NaI crystal cannot?', ['Its peaks are much narrower', 'It is bigger', 'It counts faster'], 0, 'Neighbouring lines stay separate when the FWHM is about 2 keV.']],
    5: [['What does the slope of the channel-energy line tell you?', ['The energy per channel of the analyser', 'The efficiency of the crystal', 'The activity of the source'], 0, 'E = a + b × channel; b is keV per channel.'],
      ['Points that lie off the line show', ['non-linearity of the analyser or a misread peak', 'a stronger source', 'a longer count'], 0, 'A linear ADC puts every point on the line.']]
  };

  function askState() {
    var f = st.fit, q = {};
    q.experiment = S.lab.title; q.detector = DET; q.source_on_rail = st.loaded >= 0 ? name(st.loaded) : 'none'; q.distance_cm = st.d; q.live_time_s = st.t;
    q.high_voltage_on = st.hv; q.cursor_channel = st.cursor; q.readings = S.rows.length;
    if (f) { q.last_fit_channel = r1(f.mu, 2); q.last_fit_fwhm_channels = r1(f.fwhmCh, 2); q.last_fit_area = Math.round(f.area); }
    return q;
  }

  return {
    camera: { pos: [-0.02, 0.95, 1.52], look: [-0.03, 0.27, -0.2] },
    views: { det: [[-0.30, 0.66, 0.30], [-0.46, 0.46, -0.30]], dewar: [[-0.1, 0.9, 0.3], [-0.46, 0.8, -0.34]], castle: [[-0.3, 0.52, 0.5], [-0.46, 0.3, -0.3]], rail: [[-0.26, 0.4, 0.34], [-0.4, 0.3, -0.22]],
      store: [[-0.4, 0.28, 0.5], [-0.5, 0.0, 0.12]], tongs: [[-0.22, 0.2, 0.4], [-0.22, 0.0, 0.2]], nim: [[0.14, 0.32, 0.12], [0.05, 0.1, -0.28]],
      monitor: [[0.36, 0.34, 0.26], [0.44, 0.2, -0.3]], bench: [[-0.02, 0.95, 1.52], [-0.03, 0.27, -0.2]], book: [[0.2, 0.46, 0.5], [0.3, 0.0, 0.08]] },
    theory: { principle: TT.principle, formula: TT.formula, formulaNote: TT.note,
      more: ['The counts in every channel are Poisson numbers, so a peak of N counts carries an uncertainty of √N. This is why a longer live time gives a cleaner spectrum.',
        'Radioactive sources are sealed and handled with tongs behind lead. Time, distance and shielding are the three things that keep a dose low.'],
      precautions: 'Handle the sealed sources only with the tongs, from behind the lead, and return them to the locked store when you finish. Bring the high voltage up slowly and switch it off before touching the detector.' },
    book: { title: 'Expt. - ' + S.lab.title, at: [0.30, 0.10, 0.08],
      lines: ['Aim: ' + S.lab.aim.slice(0, 74), 'Detector: ' + DET, 'Amplifier gain ' + NOMG + ' keV/channel (nominal).', 'Safety: tongs, lead, source back in its store.'],
      columns: pageCols[TASK] || pageCols[1] },
    graph: gcfg || undefined,
    result: result, tol: TASK === 4 || TASK === 0 ? 0.01 : (TASK === 5 ? 0.01 : (TASK === 3 ? 0.03 : 0.04)),
    resultNote: 'Every count came from the lab\'s simulated detector with its own random seed. A different live time or a different seed gives slightly different numbers, as a real run does.',
    chips: ['What is a photopeak?', 'Why is the peak a Gaussian?', 'Check my fit', 'Why are the sources handled with tongs?', 'What is the Compton edge?'],
    viva: VIVA[TASK] || VIVA[1],
    askState: askState,
    steps: STEPS,
    tick: function () {
      if (dirty) { dirty = false; spaint(); paintPanel(); }
      showT(String(Math.round(st.live))); showN(st.cdata ? String(Math.round(st.total * Math.min(1, st.shown))) : '0');
      hudD.set(st.d + ' cm'); hudT.set(r1(st.live, 0) + ' s'); hudR.set(S.rows.length + ' written');
    },
    ready: function () { spaint(); }
  };
});
