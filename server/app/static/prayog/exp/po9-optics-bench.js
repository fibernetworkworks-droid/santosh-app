/* Prayogshala studio module: THE M.Sc. OPTICS, LASERS AND SPECTROSCOPY BENCH (wave 9). One rig for the M.Sc. set-ups of
   the pg_optics_w9 pack - a Fabry-Perot etalon on a hyperfine satellite, the Zeeman effect (etalon or Lummer-Gehrcke
   plate), elliptical light and birefringence (quarter-wave plate, Babinet compensator, rotating analyser),
   photoelasticity, Kerr and Pockels cells and electro-optic modulation, the Faraday effect and magneto-optic
   modulation, laser diffraction, the constant deviation spectrometer, a Rowland-mounted concave grating, band heads,
   scanned absorption / fluorescence / solar spectra, film thickness at a step, Stoney's stress, photometry and
   acousto-optics. Built on the wave-7 applied-optics breadboard (same engine: set the control, read the instrument,
   record). Nothing is typed into this page: the readings are the kernel's read(), the settings the walk-through
   records are the kernel's own plan(), and the table is reduced by the kernel's own calc - the same three functions
   the server's check runs. */
HoolaStudio.define('po9-optics-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels;
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var KN = S.lab.kernel, K = HK.K[KN];
  var p = HK.paramsFor(KN, S.lab.params);
  (S.lab.knobs || []).forEach(function (k) {
    if (k.hidden && isFinite(k.value) && p[k.param] !== undefined) p[k.param] = +k.value * (+k.k || 1);
  });
  var MODE = Math.round(p.mode || 0), DEG = Math.PI / 180;
  var AXY = 0.15, BZ = -0.3, TOP = 0.012;
  var SAMPLE = (S.lab.variant && S.lab.variant.sample) || '';
  var st = { on: false, ready: false, set: {} };

  function fmt(v, d) { if (!isFinite(v)) return '—'; var o = (+v).toFixed(d === undefined ? 2 : d); return /^-0(\.0*)?$/.test(o) ? o.slice(1) : o; }
  var LAMF = null;
  function lamOf() { if (LAMF) { var v = LAMF(); if (v > 0) return v; } return p.lam || p.lam0 || 5.893e-7; }
  function rgb() { var nm = lamOf() * 1e9;
    return nm > 700 ? [150, 30, 30] : nm > 610 ? [255, 60, 50] : nm > 575 ? [255, 200, 60] : nm > 500 ? [80, 220, 110] : [80, 110, 240]; }
  function hex() { var c = rgb(); return (c[0] << 16) | (c[1] << 8) | c[2]; }
  function isSodium() { return Math.abs(lamOf() - 5.893e-7) < 3e-9; }

  // ------------------------------------------------------------------------------------------ small parts
  function cyl(r, h, mat, seg) { return S.mesh(new T.CylinderGeometry(r, r, h, seg || 24), mat); }
  function box(w, h, d, mat) { return S.mesh(new T.BoxGeometry(w, h, d), mat); }
  function along(m) { m.rotation.z = Math.PI / 2; return m; }                 // a cylinder laid along the beam (local x)
  function put(m, x, y, z) { m.position.set(x, y, z); return m; }
  var glassDark = new T.MeshPhysicalMaterial({ color: 0x4a5560, roughness: 0.08, transmission: 0.55, thickness: 0.002, transparent: true });
  var liquidM = new T.MeshPhysicalMaterial({ color: 0xbfe3f2, roughness: 0.05, transmission: 0.85, thickness: 0.03, transparent: true });
  var cardM = new T.MeshStandardMaterial({ color: 0xeceadf, roughness: 0.95 });
  var anod = new T.MeshStandardMaterial({ color: 0x16181b, roughness: 0.45, metalness: 0.35 });
  var fibreM = new T.MeshStandardMaterial({ color: 0xf2c230, roughness: 0.5 });
  function post(g, h, x) {
    var b = S.rounded(0.05, 0.05, 0.012, 0.006, M.alu); b.rotation.x = -Math.PI / 2; put(b, x || 0, TOP + 0.006, 0); g.add(b);
    var r = cyl(0.006, Math.max(h - TOP - 0.012, 0.01), M.chrome, 18); put(r, x || 0, TOP + 0.012 + Math.max(h - TOP - 0.012, 0.01) / 2, 0); g.add(r);
  }
  function thimble(g, x, y, z, axis) {                                        // a micrometer head: barrel + knurled thimble
    var b = cyl(0.005, 0.03, M.chrome, 18), t = cyl(0.009, 0.022, M.steel, 20);
    if (axis === 'x') { along(b); along(t); put(b, x + 0.015, y, z); put(t, x + 0.04, y, z); }
    else if (axis === 'z') { b.rotation.x = Math.PI / 2; t.rotation.x = Math.PI / 2; put(b, x, y, z + 0.015); put(t, x, y, z + 0.04); }
    else { put(b, x, y + 0.015, z); put(t, x, y + 0.04, z); }
    g.add(b); g.add(t); return t;
  }
  function tag(g, text, w, y, z) { var l = S.label(text, { w: w || 0.07, ratio: 0.2, color: '#e8ecf0', weight: 700 }); put(l, 0, y, z); g.add(l); return l; }

  var BUILD = {
    laser: function (g) {
      post(g, AXY - 0.02);
      var body = along(cyl(0.02, 0.17, M.blackPlastic, 28)); put(body, 0, AXY, 0); g.add(body);
      var nose = along(cyl(0.011, 0.02, M.alu, 20)); put(nose, 0.093, AXY, 0); g.add(nose);
      var sw = cyl(0.006, 0.006, M.red, 14); put(sw, -0.04, AXY + 0.022, 0); g.add(sw);
      var w = S.label('LASER · DO NOT LOOK INTO THE BEAM', { w: 0.1, ratio: 0.13, color: '#f2d04a', weight: 700 });
      put(w, 0.01, AXY + 0.0205, 0); w.rotation.x = -Math.PI / 2; g.add(w);
      return { sw: sw, out: 0.1 };
    },
    lamp: function (g, o) {
      var h = S.rounded(0.1, 0.19, 0.1, 0.012, M.iron); put(h, 0, TOP + 0.095, 0); g.add(h);
      var win = new T.Mesh(new T.CircleGeometry(0.02, 28), new T.MeshBasicMaterial({ color: 0x35311f })); win.rotation.y = Math.PI / 2; put(win, 0.051, AXY, 0); g.add(win);
      var hood = along(cyl(0.026, 0.03, M.black, 24)); put(hood, 0.062, AXY, 0); g.add(hood);
      var ch = cyl(0.02, 0.03, M.iron, 16); put(ch, 0, TOP + 0.2, 0); g.add(ch);
      var sw = cyl(0.007, 0.006, M.red, 14); put(sw, -0.02, TOP + 0.193, 0.03); g.add(sw);
      var t = tag(g, (o && o.text) || 'SODIUM LAMP', 0.085, TOP + 0.05, 0.051);
      t.material.color = new T.Color(0xffffff);
      return { sw: sw, out: 0.078, glow: win };
    },
    source: function (g, o) {                                                 // a fibre-optic light source / laser driver box
      var b = S.rounded(0.14, 0.08, 0.11, 0.008, M.blackPlastic); put(b, 0, TOP + 0.04, 0); g.add(b);
      tag(g, (o && o.text) || 'LIGHT SOURCE', 0.11, TOP + 0.055, 0.056);
      var port = along(cyl(0.006, 0.014, M.brass, 14)); put(port, 0.075, TOP + 0.04, 0); g.add(port);
      var sw = cyl(0.007, 0.006, M.red, 14); put(sw, -0.04, TOP + 0.083, 0.02); g.add(sw);
      var kn = cyl(0.013, 0.014, M.bakelite, 22); put(kn, 0.03, TOP + 0.087, 0.02); g.add(kn);
      return { sw: sw, handle: kn, out: 0.082, y: TOP + 0.04 };
    },
    lens: function (g) {
      post(g, AXY - 0.034);
      var ring = S.mesh(new T.TorusGeometry(0.03, 0.004, 10, 40), anod); ring.rotation.y = Math.PI / 2; put(ring, 0, AXY, 0); g.add(ring);
      var l = along(cyl(0.029, 0.005, M.glass, 36)); put(l, 0, AXY, 0); g.add(l);
      return {};
    },
    polar: function (g, o) {                                                  // a polaroid in a divided rotary mount
      post(g, AXY - 0.045);
      var outer = along(cyl(0.044, 0.012, anod, 40)); put(outer, 0, AXY, 0); g.add(outer);
      var rot = new T.Group(); put(rot, 0, AXY, 0); g.add(rot);
      var disc = along(cyl(0.03, 0.014, glassDark, 36)); rot.add(disc);
      var rim = S.mesh(new T.TorusGeometry(0.033, 0.005, 10, 44), M.alu); rim.rotation.y = Math.PI / 2; rot.add(rim);
      var peg = cyl(0.004, 0.022, M.chrome, 12); put(peg, 0, 0.045, 0); rot.add(peg);
      var mark = box(0.002, 0.012, 0.003, M.red); put(mark, 0.0085, 0.031, 0); rot.add(mark);
      tag(g, (o && o.text) || 'ANALYSER', 0.06, AXY - 0.058, 0.012);
      return { rot: rot, handle: peg };
    },
    slit: function (g, o) {
      post(g, AXY - 0.04);
      var pl = box(0.004, 0.08, 0.05, anod); put(pl, 0, AXY, 0); g.add(pl);
      var n = (o && o.two) ? [-0.004, 0.004] : [0];
      n.forEach(function (z) { var s = new T.Mesh(new T.PlaneGeometry(0.0012, 0.03), new T.MeshBasicMaterial({ color: 0xf5e7a8 })); s.rotation.y = Math.PI / 2; put(s, 0.0022, AXY, z); g.add(s); });
      var th = (o && o.mic) ? thimble(g, 0, AXY, 0.026, 'z') : null;
      return { handle: th };
    },
    plate: function (g, o) {                                                  // a thin plate in a holder: mica, filter, wave plate, dusted glass
      post(g, AXY - 0.035);
      var fr = box(0.006, 0.012, 0.056, anod); put(fr, 0, AXY - 0.03, 0); g.add(fr);
      var mat = (o && o.color) ? new T.MeshPhysicalMaterial({ color: o.color, roughness: 0.1, transmission: 0.6, thickness: 0.002, transparent: true }) : M.glass;
      var pl = box(0.003, 0.05, 0.05, mat); put(pl, 0, AXY, 0); g.add(pl);
      if (o && o.text) tag(g, o.text, 0.055, AXY - 0.044, 0.008);
      return { handle: pl };
    },
    biprism: function (g) {
      post(g, AXY - 0.04);
      var fr = box(0.01, 0.07, 0.006, anod); put(fr, 0, AXY, 0.024); g.add(fr);
      var fr2 = fr.clone(); put(fr2, 0, AXY, -0.024); g.add(fr2);
      var bp = S.mesh(new T.CylinderGeometry(0.024, 0.024, 0.055, 3), M.glassBlock); bp.scale.set(0.18, 1, 1); bp.rotation.y = Math.PI; put(bp, 0, AXY, 0); g.add(bp);
      return { handle: fr };
    },
    table: function (g, o) {                                                  // a divided circle with a turning table on it
      var base = cyl(0.1, 0.014, M.iron, 48); put(base, 0, TOP + 0.007, 0); g.add(base);
      var sc = S.canvasTex(1024, 1024, function (x, w) {
        x.fillStyle = '#d9c48a'; x.beginPath(); x.arc(w / 2, w / 2, w / 2, 0, 7); x.fill();
        x.strokeStyle = '#2a2415'; x.fillStyle = '#2a2415'; x.font = '600 26px sans-serif'; x.textAlign = 'center';
        for (var d = 0; d < 360; d += 2) { var a = d * Math.PI / 180, r1 = w / 2 - 6, r2 = w / 2 - (d % 10 === 0 ? 46 : 24);
          x.lineWidth = d % 10 === 0 ? 3 : 1.5; x.beginPath(); x.moveTo(w / 2 + r1 * Math.cos(a), w / 2 + r1 * Math.sin(a)); x.lineTo(w / 2 + r2 * Math.cos(a), w / 2 + r2 * Math.sin(a)); x.stroke();
          if (d % 30 === 0) x.fillText(String(d), w / 2 + (w / 2 - 70) * Math.cos(a), w / 2 + (w / 2 - 70) * Math.sin(a) + 9); }
      });
      var circ = new T.Mesh(new T.CircleGeometry(0.098, 64), new T.MeshStandardMaterial({ map: sc, roughness: 0.4, metalness: 0.5 }));
      circ.rotation.x = -Math.PI / 2; put(circ, 0, TOP + 0.0145, 0); g.add(circ);
      var pil = cyl(0.012, AXY - 0.05 - TOP, M.chrome, 20); put(pil, 0, TOP + (AXY - 0.05 - TOP) / 2, 0); g.add(pil);
      var rot = new T.Group(); put(rot, 0, AXY - 0.05, 0); g.add(rot);
      var top = cyl(0.05, 0.008, M.brass, 40); put(top, 0, 0.004, 0); rot.add(top);
      var arm = box(0.012, 0.006, 0.05, M.brass); put(arm, 0, 0.002, 0.07); rot.add(arm);
      var peg = cyl(0.005, 0.016, M.bakelite, 12); put(peg, 0, 0.012, 0.092); rot.add(peg);
      if (o && o.on === 'prism') {
        var pr = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.045, 3), M.glassBlock); put(pr, 0, 0.031, 0); rot.add(pr);
      } else if (o && o.on === 'cell') {
        var cell = box(0.06, 0.07, 0.05, liquidM); put(cell, 0, 0.043, 0); rot.add(cell);
        var wall = box(0.064, 0.074, 0.054, M.glass); put(wall, 0, 0.043, 0); rot.add(wall);
        var film = box(0.004, 0.06, 0.04, M.glass); put(film, 0, 0.043, 0); rot.add(film);
        var edge = box(0.0045, 0.062, 0.002, M.white); put(edge, 0, 0.043, 0.021); rot.add(edge);
      }
      return { rot: rot, handle: peg };
    },
    scope: function (g, o) {                                                  // a telescope on an arm that swings about the group's origin
      var R = (o && o.R) || 0.2;
      var arm = box(R, 0.008, 0.02, M.iron); put(arm, R / 2, TOP + 0.02, 0); g.add(arm);
      var up = cyl(0.007, AXY - TOP - 0.03, M.chrome, 16); put(up, R, TOP + 0.02 + (AXY - TOP - 0.03) / 2, 0); g.add(up);
      var tube = along(cyl(0.014, 0.16, M.brass, 28)); put(tube, R + 0.02, AXY, 0); g.add(tube);
      var obj = along(cyl(0.017, 0.02, M.brass, 28)); put(obj, R - 0.06, AXY, 0); g.add(obj);
      var eye = along(cyl(0.011, 0.04, M.black, 22)); put(eye, R + 0.115, AXY, 0); g.add(eye);
      var screw = cyl(0.006, 0.02, M.bakelite, 14); put(screw, R, TOP + 0.045, 0.02); g.add(screw);
      if (o && o.gauss) { var side = cyl(0.006, 0.03, M.brass, 14); put(side, R + 0.095, AXY + 0.02, 0); g.add(side);
        var bulb = S.mesh(new T.SphereGeometry(0.008, 14, 10), new T.MeshBasicMaterial({ color: 0xffe9a8 })); put(bulb, R + 0.095, AXY + 0.038, 0); g.add(bulb); }
      return { handle: screw, eyeAt: R + 0.14 };
    },
    eyepiece: function (g) {                                                  // a micrometer eyepiece
      post(g, AXY - 0.02);
      var body = box(0.03, 0.04, 0.07, anod); put(body, 0, AXY, 0); g.add(body);
      var tube = along(cyl(0.013, 0.06, M.black, 22)); put(tube, 0.04, AXY, 0); g.add(tube);
      var th = thimble(g, 0, AXY, 0.035, 'z');
      return { handle: th };
    },
    mirror: function (g, o) {
      post(g, AXY - 0.035);
      var mt = box(0.012, 0.06, 0.06, anod); put(mt, 0.008, AXY, 0); g.add(mt);
      var mi = along(cyl(0.022, 0.004, M.chrome, 36)); put(mi, 0, AXY, 0); g.add(mi);
      [[0.022, 0.022], [-0.022, -0.022]].forEach(function (a) { var s = along(cyl(0.004, 0.014, M.brass, 12)); put(s, 0.02, AXY + a[0], a[1]); g.add(s); });
      var th = (o && o.mic) ? thimble(g, 0.014, AXY - 0.045 + 0.045, 0, 'x') : null;
      return { handle: th };
    },
    bs: function (g) {
      post(g, AXY - 0.03);
      var pl = box(0.045, 0.006, 0.045, anod); put(pl, 0, AXY - 0.024, 0); g.add(pl);
      var c = box(0.036, 0.036, 0.036, M.glassBlock); put(c, 0, AXY, 0); g.add(c);
      var d = new T.Mesh(new T.PlaneGeometry(0.05, 0.036), new T.MeshPhysicalMaterial({ color: 0xbfd0e0, roughness: 0.05, metalness: 0.6, transparent: true, opacity: 0.45, side: T.DoubleSide }));
      d.rotation.y = Math.PI / 4; put(d, 0, AXY, 0); g.add(d);
      return {};
    },
    etalon: function (g) {
      post(g, AXY - 0.04, -0.02); post(g, AXY - 0.04, 0.03);
      var bar = box(0.1, 0.008, 0.05, anod); put(bar, 0.005, AXY - 0.036, 0); g.add(bar);
      [-0.02, 0.012].forEach(function (x) { var r = S.mesh(new T.TorusGeometry(0.03, 0.005, 10, 40), anod); r.rotation.y = Math.PI / 2; put(r, x, AXY, 0); g.add(r);
        var pl = along(cyl(0.028, 0.006, M.glass, 36)); put(pl, x, AXY, 0); g.add(pl); });
      var th = thimble(g, 0.02, AXY - 0.036, 0, 'x');
      return { handle: th };
    },
    comp: function (g) {                                                      // Babinet compensator: two quartz wedges, one on a micrometer slide
      post(g, AXY - 0.04);
      var fr = box(0.014, 0.012, 0.09, anod); put(fr, 0, AXY - 0.034, 0); g.add(fr);
      var w1 = box(0.004, 0.045, 0.06, M.glassBlock); put(w1, -0.003, AXY, 0); g.add(w1);
      var w2 = box(0.004, 0.045, 0.06, M.glassBlock); put(w2, 0.003, AXY, 0.004); g.add(w2);
      var th = thimble(g, 0, AXY - 0.034, 0.045, 'z');
      tag(g, 'BABINET', 0.05, AXY - 0.034, 0.0462).position.x = 0.0072;
      return { handle: th, wedge: w2 };
    },
    detector: function (g, o) {
      post(g, AXY - 0.02);
      var h = along(cyl(0.016, 0.035, M.blackPlastic, 24)); put(h, 0.008, AXY, 0); g.add(h);
      var a = new T.Mesh(new T.CircleGeometry(0.008, 20), new T.MeshStandardMaterial({ color: 0x2a3550, roughness: 0.15, metalness: 0.6 })); a.rotation.y = -Math.PI / 2; put(a, -0.0098, AXY, 0); g.add(a);
      if (o && o.stage) { var s = box(0.06, 0.016, 0.06, M.alu); put(s, 0, TOP + 0.03, 0); g.add(s); return { handle: thimble(g, 0, TOP + 0.03, 0.03, 'z') }; }
      return { handle: h };
    },
    meter: function (g, o) {                                                  // a bench meter with a live display
      var b = S.rounded(0.17, 0.075, 0.11, 0.008, M.blackPlastic); put(b, 0, TOP + 0.0375, 0); g.add(b);
      var tex = S.liveTex(512, 160);
      var scr = new T.Mesh(new T.PlaneGeometry(0.11, 0.034), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); put(scr, -0.018, TOP + 0.046, 0.0556); g.add(scr);
      tag(g, (o && o.text) || 'POWER METER', 0.1, TOP + 0.016, 0.0556);
      var kn = cyl(0.012, 0.012, M.bakelite, 22); kn.rotation.x = Math.PI / 2; put(kn, 0.062, TOP + 0.046, 0.058); g.add(kn);
      return { tex: tex, handle: kn };
    },
    screen: function (g) {                                                    // a white card with a millimetre scale and a sliding cursor
      post(g, 0.05);
      var card = box(0.004, 0.2, 0.34, cardM); put(card, 0, AXY + 0.02, 0); g.add(card);
      var sc = S.canvasTex(2048, 96, function (x, w, h) { var mm = 320, k = w / mm, i, big; x.fillStyle = '#f3eedd'; x.fillRect(0, 0, w, h); x.fillStyle = '#17181a';
        for (i = 0; i <= mm; i++) { big = i % 10 === 0; x.fillRect(i * k, 0, big ? 3 : 1.5, big ? 40 : (i % 5 === 0 ? 28 : 16));
          if (big) { x.font = '600 30px sans-serif'; x.textAlign = 'center'; x.fillText(String(Math.abs(i - 160) / 10), i * k, 76); } } });
      var sm = new T.Mesh(new T.PlaneGeometry(0.32, 0.015), new T.MeshStandardMaterial({ map: sc, roughness: 0.6 })); sm.rotation.y = -Math.PI / 2; put(sm, -0.0025, AXY - 0.06, 0); g.add(sm);
      var tex = S.liveTex(512, 128);
      var pm = new T.Mesh(new T.PlaneGeometry(0.32, 0.08), new T.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, toneMapped: false })); pm.rotation.y = -Math.PI / 2; put(pm, -0.0026, AXY, 0); pm.renderOrder = 5; g.add(pm);
      var cur = new T.Group(); g.add(cur);
      var cb = box(0.006, 0.04, 0.014, M.bakelite); put(cb, -0.006, AXY - 0.055, 0); cur.add(cb);
      var hair = box(0.001, 0.09, 0.0007, M.red); put(hair, -0.004, AXY - 0.01, 0); cur.add(hair);
      return { handle: cb, cursor: cur, ptex: tex };
    },
    objective: function (g) {
      post(g, AXY - 0.03);
      var hold = box(0.012, 0.05, 0.05, anod); put(hold, 0, AXY, 0); g.add(hold);
      var ob = along(S.mesh(new T.CylinderGeometry(0.008, 0.014, 0.04, 24), M.chrome)); put(ob, -0.024, AXY, 0); g.add(ob);
      return {};
    },
    chuck: function (g) {                                                     // a fibre chuck on a post
      post(g, AXY - 0.012);
      var b = box(0.03, 0.02, 0.026, M.alu); put(b, 0, AXY - 0.004, 0); g.add(b);
      var c = box(0.03, 0.005, 0.012, anod); put(c, 0, AXY + 0.008, 0); g.add(c);
      return { handle: c };
    },
    vgroove: function (g) {                                                   // a mechanical V-groove splice
      post(g, AXY - 0.02);
      var b = box(0.07, 0.014, 0.03, M.alu); put(b, 0, AXY - 0.009, 0); g.add(b);
      var lid = box(0.04, 0.006, 0.02, new T.MeshStandardMaterial({ color: 0x2c63c4, roughness: 0.4 })); put(lid, 0, AXY + 0.004, 0); g.add(lid);
      tag(g, 'SPLICE', 0.04, AXY - 0.009, 0.0152);
      return { handle: lid };
    },
    mandrel: function (g) {
      var base = box(0.09, 0.012, 0.09, anod); put(base, 0, TOP + 0.006, 0); g.add(base);
      var rot = new T.Group(); put(rot, 0, TOP + 0.012, 0); g.add(rot);
      var m = cyl(1, 0.17, M.alu, 40); put(m, 0, 0.085, 0); rot.add(m);
      var loop = S.mesh(new T.TorusGeometry(0.03, 0.0016, 8, 48), fibreM); loop.rotation.x = Math.PI / 2; put(loop, 0, AXY - TOP - 0.012, 0); rot.add(loop);
      return { rot: rot, drum: m, handle: m, loop: loop, R: 0 };
    },
    cellarm: function (g) {                                                   // a gas cell with windows and a hose nipple
      post(g, AXY - 0.03);
      var c = along(cyl(0.02, 0.1, M.glass, 28)); put(c, 0, AXY, 0); g.add(c);
      [-0.05, 0.05].forEach(function (x) { var e = along(cyl(0.023, 0.006, M.alu, 28)); put(e, x, AXY, 0); g.add(e); });
      var nip = cyl(0.004, 0.02, M.brass, 12); put(nip, 0, AXY + 0.028, 0); g.add(nip);
      return {};
    },
    pump: function (g) {                                                      // a hand pump with a pressure gauge
      var b = S.rounded(0.12, 0.05, 0.09, 0.008, M.grey); put(b, 0, TOP + 0.025, 0); g.add(b);
      var gauge = cyl(0.035, 0.02, M.chrome, 36); gauge.rotation.x = Math.PI / 2; put(gauge, -0.02, TOP + 0.08, 0); g.add(gauge);
      var tex = S.liveTex(256, 256);
      var face = new T.Mesh(new T.CircleGeometry(0.032, 36), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); put(face, -0.02, TOP + 0.08, 0.0105); g.add(face);
      var bulb = S.mesh(new T.SphereGeometry(0.022, 20, 14), M.rubber); bulb.scale.set(1.5, 1, 1); put(bulb, 0.05, TOP + 0.07, 0); g.add(bulb);
      tag(g, 'PRESSURE', 0.07, TOP + 0.02, 0.0456);
      return { handle: bulb, gtex: tex };
    },
    furnace: function (g) {                                                   // a tube furnace with the rod inside and a mirror on its free end
      post(g, AXY - 0.035, -0.05); post(g, AXY - 0.035, 0.07);
      var tube = along(cyl(0.03, 0.2, new T.MeshStandardMaterial({ color: 0xd8d2c4, roughness: 0.9 }), 30)); put(tube, 0.02, AXY, 0); g.add(tube);
      for (var i = 0; i < 9; i++) { var c = S.mesh(new T.TorusGeometry(0.031, 0.0018, 8, 30), M.copper); c.rotation.y = Math.PI / 2; put(c, -0.06 + i * 0.02, AXY, 0); g.add(c); }
      var rod = along(cyl(0.006, 0.26, M.glass, 16)); put(rod, 0.0, AXY, 0); g.add(rod);
      var mi = along(cyl(0.012, 0.003, M.chrome, 24)); put(mi, -0.131, AXY, 0); g.add(mi);
      var th = cyl(0.003, 0.09, M.glass, 10); put(th, 0.04, AXY + 0.07, 0); g.add(th);
      return {};
    },
    pc: function (g) {                                                        // the computer that transforms the interferogram
      var base = box(0.12, 0.01, 0.09, M.grey); put(base, 0, TOP + 0.005, 0); g.add(base);
      var neck = box(0.02, 0.07, 0.012, M.grey); put(neck, 0, TOP + 0.04, -0.02); g.add(neck);
      var mon = S.rounded(0.24, 0.16, 0.014, 0.006, M.blackPlastic); put(mon, 0, TOP + 0.15, -0.02); g.add(mon);
      var tex = S.liveTex(640, 400);
      var scr = new T.Mesh(new T.PlaneGeometry(0.22, 0.14), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); put(scr, 0, TOP + 0.15, -0.0125); g.add(scr);
      var mouse = S.rounded(0.03, 0.045, 0.012, 0.005, M.white); mouse.rotation.x = -Math.PI / 2; put(mouse, 0.1, TOP + 0.006, 0.06); g.add(mouse);
      return { handle: mouse, stex: tex };
    },
    nodal: function (g) {                                                     // two lenses on a carriage that slides over a vertical axis
      var base = cyl(0.06, 0.014, M.iron, 40); put(base, 0, TOP + 0.007, 0); g.add(base);
      var pil = cyl(0.01, AXY - 0.06 - TOP, M.chrome, 18); put(pil, 0, TOP + (AXY - 0.06 - TOP) / 2, 0); g.add(pil);
      var rot = new T.Group(); put(rot, 0, AXY - 0.06, 0); g.add(rot);
      var rail = box(0.26, 0.01, 0.03, M.iron); put(rail, 0, 0.005, 0); rot.add(rail);
      var pair = new T.Group(); rot.add(pair);
      var car = box(0.11, 0.008, 0.04, M.alu); put(car, 0, 0.014, 0); pair.add(car);
      [-0.025, 0.025].forEach(function (x) { var up = cyl(0.004, 0.02, M.chrome, 12); put(up, x, 0.028, 0); pair.add(up);
        var ring = S.mesh(new T.TorusGeometry(0.024, 0.0035, 10, 36), anod); ring.rotation.y = Math.PI / 2; put(ring, x, 0.06, 0); pair.add(ring);
        var l = along(cyl(0.023, 0.005, M.glass, 30)); put(l, x, 0.06, 0); pair.add(l); });
      var kn = cyl(0.007, 0.014, M.bakelite, 14); put(kn, 0.045, 0.025, 0.022); pair.add(kn);
      var pin = cyl(0.003, 0.03, M.red, 10); put(pin, 0, 0.025, -0.02); rot.add(pin);
      return { rot: rot, pair: pair, handle: kn };
    },
    ldmount: function (g) {
      post(g, AXY - 0.025);
      var b = box(0.03, 0.045, 0.045, M.alu); put(b, 0, AXY, 0); g.add(b);
      for (var i = 0; i < 5; i++) { var f = box(0.028, 0.04, 0.002, M.alu); put(f, -0.004, AXY, -0.03 + i * 0.004 - 0.008); g.add(f); }
      var can = along(cyl(0.0045, 0.008, M.brass, 16)); put(can, 0.019, AXY, 0); g.add(can);
      return {};
    },
    magnet: function (g, o) {                                                 // an electromagnet: two coils on soft-iron cores, pole gap at the centre
      var base = box(0.26, 0.016, 0.1, M.iron); put(base, 0, TOP + 0.008, 0); g.add(base);
      [-1, 1].forEach(function (sd) {
        var up = box(0.03, AXY - 0.02, 0.06, M.iron); put(up, sd * 0.115, TOP + 0.016 + (AXY - 0.02) / 2, 0); g.add(up);
        var core = along(cyl(0.022, 0.07, M.iron, 28)); put(core, sd * 0.065, AXY, 0); g.add(core);
        var coil = along(cyl(0.04, 0.05, M.copper, 32)); put(coil, sd * 0.07, AXY, 0); g.add(coil);
        for (var i = 0; i < 6; i++) { var r = S.mesh(new T.TorusGeometry(0.0405, 0.0018, 6, 36), M.copper); r.rotation.y = Math.PI / 2; put(r, sd * (0.05 + i * 0.008), AXY, 0); g.add(r); }
        var pole = along(S.mesh(new T.CylinderGeometry(0.012, 0.022, 0.02, 24), M.steel)); put(pole, sd * 0.022, AXY, 0); pole.rotation.z = sd > 0 ? Math.PI / 2 : -Math.PI / 2; g.add(pole);
        [0.018, -0.018].forEach(function (z) { var tm = cyl(0.004, 0.012, z > 0 ? M.red : M.black, 12); put(tm, sd * 0.07, AXY + 0.046, z); g.add(tm); });
      });
      var inner = null;
      if (o && o.lamp) { inner = cyl(0.007, 0.06, new T.MeshBasicMaterial({ color: 0x35311f }), 16); put(inner, 0, AXY, 0); g.add(inner);
        var cap = cyl(0.009, 0.01, M.blackPlastic, 16); put(cap, 0, AXY + 0.035, 0); g.add(cap); }
      if (o && o.rod) { var rod = along(cyl(0.008, 0.2, M.glass, 20)); put(rod, 0, AXY, 0); g.add(rod); }
      var probe = box(0.004, 0.03, 0.002, M.blackPlastic); put(probe, 0, AXY + 0.028, 0.012); g.add(probe);
      tag(g, o && o.text || 'ELECTROMAGNET', 0.09, TOP + 0.009, 0.051);
      return { handle: base, glow: inner, sw: probe };
    },
    solenoid: function (g) {                                                  // a long coil round a glass rod
      post(g, AXY - 0.03, -0.06); post(g, AXY - 0.03, 0.06);
      var coil = along(cyl(0.026, 0.16, M.copper, 32)); put(coil, 0, AXY, 0); g.add(coil);
      for (var i = 0; i < 16; i++) { var r = S.mesh(new T.TorusGeometry(0.0265, 0.0015, 6, 32), M.copper); r.rotation.y = Math.PI / 2; put(r, -0.075 + i * 0.01, AXY, 0); g.add(r); }
      [-1, 1].forEach(function (s) { var e = along(cyl(0.03, 0.006, M.bakelite, 30)); put(e, s * 0.083, AXY, 0); g.add(e); });
      var rod = along(cyl(0.007, 0.2, M.glass, 20)); put(rod, 0, AXY, 0); g.add(rod);
      tag(g, 'SOLENOID', 0.06, AXY - 0.036, 0.028);
      return { handle: coil };
    },
    eocell: function (g, o) {                                                 // a Kerr cell (glass box, two plates) or an electro-optic crystal between electrodes
      post(g, AXY - 0.04);
      if (o && o.crystal) {
        var hold = box(0.06, 0.012, 0.05, anod); put(hold, 0, AXY - 0.034, 0); g.add(hold);
        var cr = box(0.04, 0.02, 0.02, new T.MeshPhysicalMaterial({ color: 0xe9f2f0, roughness: 0.05, transmission: 0.8, thickness: 0.02, transparent: true })); put(cr, 0, AXY, 0); g.add(cr);
        [0.0115, -0.0115].forEach(function (y) { var el = box(0.04, 0.002, 0.02, M.gold || M.brass); put(el, 0, AXY + y, 0); g.add(el); });
      } else {
        var cell = box(0.08, 0.05, 0.04, new T.MeshPhysicalMaterial({ color: 0xf2e7a0, roughness: 0.05, transmission: 0.8, thickness: 0.04, transparent: true })); put(cell, 0, AXY, 0); g.add(cell);
        var wall = box(0.084, 0.054, 0.044, M.glass); put(wall, 0, AXY, 0); g.add(wall);
        [0.012, -0.012].forEach(function (y) { var pl = box(0.07, 0.002, 0.032, M.steel); put(pl, 0, AXY + y, 0); g.add(pl); });
        var lid = box(0.09, 0.006, 0.05, M.bakelite); put(lid, 0, AXY + 0.03, 0); g.add(lid);
      }
      var tr = cyl(0.005, 0.014, M.red, 12); put(tr, -0.02, AXY + 0.04, 0); g.add(tr);
      var tb = cyl(0.005, 0.014, M.black, 12); put(tb, 0.02, AXY + 0.04, 0); g.add(tb);
      tag(g, (o && o.text) || 'KERR CELL', 0.07, AXY - 0.046, 0.028);
      return { handle: tr };
    },
    frame: function (g, o) {                                                  // a loading frame with a load cell and the photoelastic model
      var base = box(0.14, 0.014, 0.06, M.iron); put(base, 0, TOP + 0.007, 0); g.add(base);
      [-0.055, 0.055].forEach(function (z) { var c = cyl(0.005, 0.25, M.chrome, 14); put(c, 0, TOP + 0.13, z); g.add(c); });
      var head = box(0.04, 0.02, 0.13, M.iron); put(head, 0, TOP + 0.255, 0); g.add(head);
      var screw = cyl(0.005, 0.05, M.steel, 14); put(screw, 0, TOP + 0.235, 0); g.add(screw);
      var wheel = cyl(0.025, 0.008, M.bakelite, 28); put(wheel, 0, TOP + 0.272, 0); g.add(wheel);
      var mat = new T.MeshPhysicalMaterial({ color: 0xe8e2c8, roughness: 0.15, transmission: 0.7, thickness: 0.01, transparent: true });
      var model;
      if (o && o.beam) { model = box(0.01, 0.012, 0.1, mat); put(model, 0, AXY, 0); g.add(model);
        [-0.04, 0.04].forEach(function (z) { var s = cyl(0.003, 0.012, M.steel, 10); s.rotation.x = 0; put(s, 0, AXY - 0.009, z); g.add(s); }); }
      else { model = cyl(0.025, 0.006, mat, 40); model.rotation.z = Math.PI / 2; put(model, 0, AXY, 0); g.add(model); }
      var pl = box(0.02, 0.008, 0.03, M.steel); put(pl, 0, AXY + (o && o.beam ? 0.01 : 0.029), 0); g.add(pl);
      var pl2 = box(0.02, 0.008, 0.03, M.steel); put(pl2, 0, AXY - (o && o.beam ? 0.016 : 0.029), 0); g.add(pl2);
      var cell = box(0.02, 0.02, 0.03, M.alu); put(cell, 0, AXY - 0.045, 0); g.add(cell);
      tag(g, 'LOADING FRAME', 0.08, TOP + 0.007, 0.031);
      return { handle: wheel, model: model };
    },
    tank: function (g, o) {                                                   // an ultrasonic water cell with its quartz transducer, or an AO crystal
      post(g, AXY - 0.045);
      if (o && o.crystal) {
        var cr = box(0.03, 0.02, 0.02, new T.MeshPhysicalMaterial({ color: 0xf6f0d8, roughness: 0.05, transmission: 0.8, thickness: 0.02, transparent: true })); put(cr, 0, AXY, 0); g.add(cr);
        var tr0 = box(0.03, 0.004, 0.02, M.gold || M.brass); put(tr0, 0, AXY + 0.012, 0); g.add(tr0);
        var sm = cyl(0.004, 0.02, M.brass, 12); put(sm, 0, AXY + 0.024, 0); g.add(sm);
        tag(g, 'Bragg CELL', 0.05, AXY - 0.035, 0.012);
        return { handle: sm };
      }
      var w = box(0.06, 0.07, 0.05, liquidM); put(w, 0, AXY - 0.004, 0); g.add(w);
      var wall = box(0.064, 0.074, 0.054, M.glass); put(wall, 0, AXY - 0.004, 0); g.add(wall);
      var tr = box(0.04, 0.008, 0.04, M.brass); put(tr, 0, AXY + 0.037, 0); g.add(tr);
      var lead = cyl(0.003, 0.03, M.black, 10); put(lead, 0.015, AXY + 0.055, 0); g.add(lead);
      tag(g, 'ULTRASONIC CELL', 0.06, AXY - 0.045, 0.028);
      return { handle: tr };
    },
    slide: function (g, o) {                                                  // a plate / slide / film sample on a comparator stage under a microscope
      var base = box(0.2, 0.02, 0.12, M.iron); put(base, 0, TOP + 0.01, 0); g.add(base);
      var stage = new T.Group(); put(stage, 0, TOP + 0.022, 0); g.add(stage);
      var top = box(0.16, 0.006, 0.1, M.alu); put(top, 0, 0.003, 0); stage.add(top);
      var c = o && o.color || 0x2b2a28;
      var tex = S.canvasTex(512, 128, function (x, w, h) { x.fillStyle = '#e9e5d6'; x.fillRect(0, 0, w, h); x.fillStyle = '#' + ('000000' + c.toString(16)).slice(-6);
        for (var i = 0; i < 40; i++) { var px = 20 + i * 12 + (i % 3) * 3; x.globalAlpha = 0.3 + 0.7 * ((i * 37) % 10) / 10; x.fillRect(px, 20, 2 + (i % 4), h - 40); } x.globalAlpha = 1; });
      var plate = new T.Mesh(new T.BoxGeometry(0.13, 0.002, 0.06), new T.MeshStandardMaterial({ map: tex, roughness: 0.3 })); put(plate, 0, 0.007, 0); stage.add(plate);
      var post2 = cyl(0.008, 0.2, M.chrome, 16); put(post2, -0.085, TOP + 0.1, -0.05); g.add(post2);
      var arm = box(0.1, 0.014, 0.02, M.iron); put(arm, -0.04, TOP + 0.19, -0.05); g.add(arm);
      var tube = cyl(0.012, 0.09, M.blackPlastic, 20); put(tube, 0.0, TOP + 0.14, -0.05); tube.rotation.x = 0.0; g.add(tube);
      var obj = cyl(0.007, 0.02, M.chrome, 16); put(obj, 0.0, TOP + 0.085, -0.05); g.add(obj);
      var th = thimble(g, 0.09, TOP + 0.02, 0, 'x');
      if (o && o.text) tag(g, o.text, 0.12, TOP + 0.01, 0.061);
      return { handle: th, stage: stage, sw: obj };
    },
    rail: function (g) {                                                      // a photometer bench rail with a scale
      var r = box(1.3, 0.012, 0.05, M.alu); put(r, 0.65, TOP + 0.006, 0); g.add(r);
      var sc = S.canvasTex(2048, 64, function (x, w, h) { x.fillStyle = '#ece6cf'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b1b1b';
        for (var i = 0; i <= 130; i++) { var big = i % 10 === 0; x.fillRect(i * w / 130, 0, 2, big ? 34 : 16); if (big) { x.font = '600 24px sans-serif'; x.fillText(String(i / 100), i * w / 130 + 4, 58); } } });
      var sm = new T.Mesh(new T.PlaneGeometry(1.3, 0.02), new T.MeshStandardMaterial({ map: sc, roughness: 0.6 })); sm.rotation.x = -Math.PI / 2; put(sm, 0.65, TOP + 0.0125, 0.012); g.add(sm);
      return {};
    },
  };

  // ------------------------------------------------------------------------------------------ the set-ups
  function planMax(key) { var m = 0; K.plan(p).forEach(function (s) { if (s[key] !== undefined && Math.abs(s[key]) > m) m = Math.abs(s[key]); }); return m; }
  function hasS(re) { return re.test(SAMPLE); }
  function cfgFp() {
    var na = Math.abs(p.lam - 5.895924e-7) < 1e-10, top = planMax('x');
    var F = ['Δσ = σ (cos θ₁ / cos θ₂ − 1),   cos θ = f / √(f² + x²)', 't = 1 / (2σ · step of cos θ between orders)', 'finesse = (step of cos θ between orders) / (width of a ring at half height)'];
    return {
      title: 'Fabry-Perot etalon', formula: F[MODE] || F[0],
      note: 'σ = 1/λ, λ = ' + fmt(p.lam * 1e9, 4) + ' nm, f = ' + fmt(p.f * 1000, 0) + ' mm' + (MODE === 0 ? '; both rings of the same order m' : ''),
      items: [['lamp', 'src', -0.82, BZ, { text: na ? 'SODIUM LAMP' : 'MERCURY LAMP', name: na ? 'Sodium lamp' : 'Mercury lamp', info: (SAMPLE || 'The mercury green line') + '.' }],
        ['plate', 'fil', -0.66, BZ, { color: na ? 0xf0c040 : 0x50c060, text: 'FILTER', name: 'Filter and ground glass', info: 'Passes the line and spreads the light over all angles.' }],
        ['etalon', 'et', -0.3, BZ, { name: 'Fabry-Perot etalon', info: 'Two flat plates coated on their inner faces, held a fixed distance apart.' }],
        ['lens', 'l2', 0.0, BZ, { name: 'Lens (f = ' + fmt(p.f * 1000, 0) + ' mm)', info: 'Turns each angle into a ring in its focal plane.' }],
        ['eyepiece', 'eye', 0.32, BZ, { name: 'Micrometer eyepiece', info: 'Its cross-wire is moved across the rings by a micrometer, read to 0.001 mm.' }]],
      x: { max: Math.max(5, Math.ceil(top * 1300)) }, handles: { x: 'eye' }, src: 'src', readyOn: 'et', readyText: ['Set the etalon plates parallel and centre the rings', 'Set the plates parallel'],
      beams: function (I) { return [[I.src, I.eye]]; },
      eye: { title: 'In the eyepiece', t: 'radial', key: 'I', span: function () { return top * 1.15; } },
      plan: MODE === 2 ? ['ring 2: on its brightest line', 'ring 2: its inner half-bright edge', 'ring 2: its outer half-bright edge', 'ring 3: on its brightest line']
        : ['main line, ring 1', 'main line, ring 2', 'main line, ring 3', 'second component, ring 1', 'second component, ring 2'],
      res: [{ label: 'wavenumber spacing of the second component', unit: 'cm⁻¹', f: 0.01, digits: 4 }, { label: 'etalon spacing', unit: 'mm', f: 1000, digits: 4 },
        { label: 'finesse', unit: '', f: 1, digits: 1 }],
      view: [[-0.15, 0.5, 0.65], [-0.2, 0.1, BZ]], tol: 0.02
    };
  }
  function cfgZeeman() {
    var cd = p.gu === 1 && p.gl === 1, lg = p.meth > 0.5, lon = p.view > 0.5, top = planMax('x');
    var R = [{ label: 'specific charge e/m', unit: '× 10¹¹ C/kg', f: 1e-11, digits: 4 }, { label: 'Bohr magneton', unit: '× 10⁻²⁴ J/T', f: 1e24, digits: 4 },
      { label: 'Landé g of the upper level', unit: '', f: 1, digits: 3 }];
    return {
      title: 'Zeeman effect', formula: (lg ? 'q = √(n² − cos² α)' : 'q = cos θ') + ';   Δσ = σ (q₁ / q₂ − 1) between the outer σ components;   Lorentz unit = eB / (4π m c)',
      note: 'B = ' + fmt(p.B, 3) + ' T, λ = ' + fmt(p.lam * 1e9, 4) + ' nm, ' + (lon ? 'longitudinal view' : 'transverse view') +
        (MODE === 2 ? '; e/m = 1.75882 × 10¹¹ C/kg (CODATA)' : '; outer σ components at ±' + (cd ? '1' : '2') + ' Lorentz units'),
      items: [['magnet', 'mag', -0.62, BZ, { lamp: true, text: cd ? 'Cd LAMP · MAGNET' : 'Hg LAMP · MAGNET', name: (cd ? 'Cadmium' : 'Mercury') + ' lamp in an electromagnet', info: 'The lamp sits in the pole gap; the gaussmeter probe reads the field. ' + (lon ? 'Viewed along the field through a hollow pole.' : 'Viewed across the field.') }],
        ['plate', 'fil', -0.42, BZ, { color: cd ? 0xd04030 : 0x50c060, text: 'FILTER', name: 'Line filter', info: 'Passes only the line under study.' }],
        lg ? ['plate', 'et', -0.22, BZ, { text: 'LUMMER-GEHRCKE', name: 'Lummer-Gehrcke plate', info: 'A thick plane-parallel glass plate; light leaves near grazing emergence after many internal reflections.' }]
          : ['etalon', 'et', -0.22, BZ, { name: 'Fabry-Perot etalon', info: 'Two coated plates ' + fmt(p.t * 1000, 0) + ' mm apart.' }],
        ['lens', 'l2', 0.02, BZ, { name: 'Telescope objective', info: 'Brings the pattern to a focus at the cross-wire.' }],
        ['eyepiece', 'eye', 0.3, BZ, { name: 'Micrometer eyepiece', info: 'Read to 0.001 mm.' }],
        ['meter', 'met', 0.48, -0.02, { text: 'GAUSSMETER', name: 'Gaussmeter', info: 'Reads the field in the pole gap.' }]],
      x: { max: Math.max(5, Math.ceil(top * 1300)) }, handles: { x: 'eye' }, src: 'mag', readyOn: 'mag', readyText: ['Raise the magnet current until the gaussmeter reads ' + fmt(p.B * 1000, 0) + ' mT', 'Set the field'],
      meterFn: function () { return fmt(p.B * 1000, 1) + ' mT'; },
      beams: function (I) { return [[I.mag, I.eye]]; },
      eye: lg ? { title: 'In the eyepiece', t: 'strip', key: 'I', scale: 4, span: function () { return 0.0012; } } : { title: 'In the eyepiece', t: 'radial', key: 'I', scale: 4, span: function () { return top * 1.15; } },
      plan: ['order 1: the outermost long-wavelength σ component', 'order 1: the outermost short-wavelength σ component', 'order 2: the outermost long-wavelength σ component', 'order 2: the outermost short-wavelength σ component'],
      res: R, view: [[-0.15, 0.5, 0.65], [-0.2, 0.1, BZ]], tol: 0.02
    };
  }
  function cfgEllipse() {
    var bab = MODE >= 2, qwpS = hasS(/quarter/i);
    var items = [['lamp', 'src', -0.82, BZ, { name: 'Sodium lamp', info: 'Yellow light, 589 nm.' }],
      ['polar', 'pol', -0.62, BZ, { text: 'POLARISER', name: 'Polariser', info: 'Set at 0 degrees.' }],
      ['plate', 'pl', -0.45, BZ, { stages: bab ? [1] : [0, 1], color: qwpS ? 0x9fc8d8 : 0xd9cfa8, text: qwpS ? 'λ/4 PLATE' : 'MICA', name: qwpS ? 'Quarter-wave plate under test' : 'Mica plate', info: (SAMPLE || 'The plate') + ', axis at ' + fmt(p.phi / DEG, 0) + ' degrees to the polariser.' }]];
    if (bab) items.push(['comp', 'cmp', -0.2, BZ, { name: 'Babinet compensator', info: 'Two quartz wedges, axes along the plate\'s; the micrometer is read to 0.001 mm.' }]);
    else items.push(['plate', 'qwp', -0.25, BZ, { stages: [1], color: 0x9fc8d8, text: 'λ/4 ANALYSING', name: 'Quarter-wave plate', info: 'Set with its axis along the major axis of the ellipse.' }]);
    items.push(['polar', 'ana', 0.0, BZ, { name: 'Analyser', info: 'A polaroid in a divided circle read to 0.01 degree.' }],
      ['detector', 'det', 0.22, BZ, { name: 'Photocell', info: 'Its current is proportional to the light through the analyser.' }],
      ['meter', 'met', 0.45, -0.02, { text: 'PHOTOMETER', name: 'Photometer', info: 'Reads the photocell.' }]);
    return {
      title: 'Elliptically polarised light',
      formula: bab ? 'δ = 2π (fringe shift) / (fringe width),   sin 2χ = sin 2ψ sin δ,   b/a = tan χ' : 'tan 2α = (I₄₅ − I₁₃₅) / (I₀ − I₉₀),   χ = (null) − 90° − α,   b/a = tan χ',
      note: bab ? 'ψ = (analyser at the black fringe) − 90° − (plate axis ' + fmt(p.phi / DEG, 0) + '°)' : 'α = azimuth of the major axis; the quarter-wave plate is set on α',
      items: items, handles: { A: 'ana', x: 'cmp', stage: bab ? 'pl' : 'qwp' }, src: 'src', readyOn: 'det', readyText: ['Cross the polariser and analyser with nothing between them', 'Cross the polarisers'],
      stages: bab ? ['without the plate (calibration)', 'with the plate'] : ['the plate only', 'with the quarter-wave plate on the major axis'],
      upd: function (I) { I.ana.rot.rotation.x = p.A; I.pol.rot.rotation.x = 0; if (I.cmp) I.cmp.wedge.position.z = 0.004 + (p.x - 0.005) * 2; },
      beams: function (I) { return [[I.src, I.det]]; }, meter: 'I',
      eye: bab ? { title: 'In the eyepiece', t: 'strip', key: 'I', span: function () { return p.beta * 1.2; } } : { title: 'Photocell', t: 'level', key: 'I' },
      plan: bab ? ['a dark fringe (no plate)', 'the next dark fringe (no plate)', 'the dark fringe with the plate in, analyser turned to black it'] : ['analyser at 0°', 'analyser at 45°', 'analyser at 90°', 'analyser at 135°', 'the null with the quarter-wave plate in'],
      res: [{ label: 'ellipticity b/a', unit: '', f: 1, digits: 4 }, { label: 'azimuth of the major axis', unit: '°', f: 180 / Math.PI, digits: 2 },
        { label: 'retardation of the plate', unit: '°', f: 180 / Math.PI, digits: 2 }, { label: 'ellipticity b/a', unit: '', f: 1, digits: 4 }],
      hideCols: bab ? [] : ['x'],
      view: [[-0.2, 0.5, 0.65], [-0.25, 0.1, BZ]], tol: 0.02
    };
  }
  function cfgBiref() {
    var bab = MODE === 0 || MODE === 2, mica = hasS(/mica/i);
    var items = [['lamp', 'src', -0.82, BZ, { name: 'Sodium lamp', info: 'Yellow light, 589 nm.' }],
      ['polar', 'pol', -0.62, BZ, { text: 'POLARISER', name: 'Polariser', info: bab ? 'At 45 degrees to the compensator axes.' : 'At 0 degrees; the plate axis is at 45 degrees.' }],
      ['plate', 'pl', -0.42, BZ, { stages: [1], color: mica ? 0xd9cfa8 : 0xe8eef0, text: mica ? 'MICA' : 'QUARTZ', name: mica ? 'Mica sheet' : 'Quartz plate', info: (SAMPLE || 'The crystal plate') + ', ' + fmt(p.t * 1e6, 0) + ' µm thick (screw gauge).' }]];
    if (bab) items.push(['comp', 'cmp', -0.2, BZ, { name: 'Babinet compensator', info: 'Two quartz wedges with crossed axes; micrometer read to 0.001 mm.' }]);
    items.push(['polar', 'ana', 0.02, BZ, { name: 'Analyser', info: bab ? 'Crossed with the polariser.' : 'Turns in a circle read to 0.01 degree.' }],
      ['detector', 'det', 0.24, BZ, { name: bab ? 'Eyepiece photocell' : 'Photocell', info: 'Reads the light through the analyser.' }],
      ['meter', 'met', 0.46, -0.02, { text: 'PHOTOMETER', name: 'Photometer', info: 'Reads the photocell.' }]);
    return {
      title: 'Birefringence', formula: bab ? 'δ = 2π S / β,   Δn = δ λ / (2π t)' : 'sin²(δ/2) = I₉₀ / (I₀ + I₉₀),   Δn = δ λ / (2π t)',
      note: 'λ = ' + fmt(p.lam * 1e9, 1) + ' nm, t = ' + fmt(p.t * 1e6, 1) + ' µm' + (bab ? '; S = fringe shift, β = fringe width' : '; analyser at 0° (parallel) and 90° (crossed)'),
      items: items, handles: { x: 'cmp', A: 'ana', stage: 'pl' }, src: 'src', readyOn: 'det', readyText: ['Cross the polariser and analyser', 'Cross the polarisers'],
      stages: ['without the plate', 'with the plate'],
      upd: function (I) { I.ana.rot.rotation.x = bab ? Math.PI / 2 + Math.PI / 4 : p.A; I.pol.rot.rotation.x = bab ? Math.PI / 4 : 0; if (I.cmp) I.cmp.wedge.position.z = 0.004 + (p.x - 0.005) * 2; },
      beams: function (I) { return [[I.src, I.det]]; }, meter: 'I',
      eye: bab ? { title: 'In the eyepiece', t: 'strip', key: 'I', span: function () { return p.beta * 1.2; } } : { title: 'Photocell', t: 'level', key: 'I' },
      plan: bab ? ['a dark fringe (no plate)', 'the next dark fringe (no plate)', 'the dark fringe with the plate in'] : ['analyser at 0° (parallel)', 'analyser at 45°', 'analyser at 90° (crossed)'],
      res: [{ label: 'birefringence n_e − n_o', unit: '', f: 1, digits: 5 }, { label: 'birefringence n_e − n_o', unit: '', f: 1, digits: 5 },
        { label: 'retardation (path difference)', unit: 'nm', f: 1e9, digits: 1 }, { label: 'retardation (path difference)', unit: 'nm', f: 1e9, digits: 1 }],
      hideCols: bab ? ['A'] : ['x'],
      view: [[-0.2, 0.5, 0.65], [-0.25, 0.1, BZ]], tol: 0.02
    };
  }
  function cfgPhotoel() {
    var beam = p.shape > 0.5, circ = p.pol > 0.5, top = planMax('x');
    var items = [['lamp', 'src', -0.82, BZ, { text: 'MERCURY LAMP', name: 'Mercury lamp with a green filter', info: 'Monochromatic light, 546.1 nm.' }],
      ['polar', 'pol', -0.62, BZ, { text: 'POLARISER', name: 'Polariser', info: 'At 45 degrees to the load.' }]];
    if (circ) items.push(['plate', 'q1', -0.48, BZ, { color: 0x9fc8d8, text: 'λ/4', name: 'Quarter-wave plate', info: 'Makes the light circular: a circular polariscope.' }]);
    items.push(['frame', 'frm', -0.22, BZ, { beam: beam, name: 'Loading frame with the model', info: (SAMPLE || 'The model') + '. Turn the wheel to load it; the load cell reads the load.' }]);
    if (circ) items.push(['plate', 'q2', 0.0, BZ, { color: 0x9fc8d8, text: 'λ/4', name: 'Second quarter-wave plate', info: 'Crossed with the first.' }]);
    items.push(['polar', 'ana', 0.14, BZ, { name: 'Analyser', info: 'Crossed with the polariser: a dark field.' }],
      ['scope', 'tel', 0.24, BZ, { R: 0.06, name: 'Viewing telescope', info: 'Looks at the watched point of the model.' }],
      ['meter', 'met', 0.48, -0.02, { text: 'LOAD CELL', name: 'Load-cell readout', info: 'Reads the load to 0.01 N.' }]);
    return {
      title: 'Photoelasticity', formula: beam ? 'N = 3 C F a / (h² λ)' : 'N = 8 C F / (π D λ)',
      note: (beam ? 'a = ' + fmt(p.a * 1000, 0) + ' mm, h = ' + fmt(p.hb * 1000, 0) + ' mm' : 'D = ' + fmt(p.D * 1000, 0) + ' mm') + ', λ = ' + fmt(p.lam * 1e9, 1) + ' nm; ' + (circ ? 'circular' : 'plane') + ' polariscope',
      items: items, x: { max: Math.max(10, Math.ceil(top * 1.3)) }, handles: { x: 'frm' }, src: 'src', readyOn: 'ana', readyText: ['Cross the analyser: the unloaded model is dark', 'Cross the analyser'],
      upd: function (I) { I.ana.rot.rotation.x = Math.PI * 0.75; I.pol.rot.rotation.x = Math.PI / 4; var rd = K.read(p), c = 0.35 + 0.65 * rd.I; I.frm.model.material.color.setRGB(0.55 + 0.4 * c, 0.5 + 0.45 * c, 0.4 + 0.3 * c); },
      beams: function (I) { return [[I.src, I.tel]]; }, meterFn: function () { return fmt(p.x, 2) + ' N'; },
      eye: { title: 'The watched point', t: 'level', key: 'I' },
      plan: function (i) { return i === 0 ? 'no load' : 'dark fringe ' + i + ' at the point'; },
      res: [{ label: 'stress-optic coefficient C', unit: 'brewster', f: 1e12, digits: 2 }, { label: 'fringe order per newton', unit: 'per kN', f: 1000, digits: 3 }],
      graph: { x: function (r) { return r.n; }, y: function (r) { return r.x; }, xlabel: 'fringe order N', ylabel: 'load (N)', fit: 'linear' },
      view: [[-0.2, 0.5, 0.65], [-0.2, 0.12, BZ]], tol: 0.02
    };
  }
  function cfgEo() {
    var kind = Math.round(p.kind), mod = MODE >= 2, vp = K.vpi(p);
    var cellText = kind === 0 ? 'KERR CELL' : (kind === 1 ? 'KDP CELL' : 'LiNbO₃');
    var items = [['laser', 'src', -0.8, BZ, { name: 'He-Ne laser', info: '632.8 nm.' }],
      ['polar', 'pol', -0.6, BZ, { text: 'POLARISER', name: 'Polariser', info: 'At 45 degrees to the induced axes.' }]];
    if (mod) items.push(['plate', 'qwp', -0.46, BZ, { color: 0x9fc8d8, text: 'λ/4 BIAS', name: 'Quarter-wave plate', info: 'Biases the modulator at half transmission.' }]);
    items.push(['eocell', 'cell', -0.25, BZ, { crystal: kind > 0, text: cellText, name: kind === 0 ? 'Kerr cell (nitrobenzene)' : (kind === 1 ? 'Longitudinal KDP Pockels cell' : 'Transverse lithium niobate modulator'), info: SAMPLE || 'The electro-optic cell.' }],
      ['polar', 'ana', 0.0, BZ, { name: 'Analyser', info: 'Crossed with the polariser.' }],
      ['detector', 'det', 0.2, BZ, { name: 'Photodetector', info: 'Reads the light through the analyser.' }],
      ['meter', 'met', 0.46, -0.02, { text: mod ? 'OSCILLOSCOPE' : 'POWER METER', name: mod ? 'Oscilloscope readout' : 'Optical power meter', info: mod ? 'Shows the received signal; the depth is read from it.' : 'Reads the light to 0.001 µW.' }],
      ['source', 'hv', -0.25, BZ + 0.2, { text: mod ? 'SIGNAL GENERATOR' : (kind === 2 ? 'DC SUPPLY 0-60 V' : 'HV SUPPLY 0-15 kV'), name: mod ? 'Signal generator and driver' : 'Voltage supply', info: mod ? 'Sets the signal amplitude and frequency.' : 'Sets the voltage on the cell, read to 0.1 V.' }]);
    var R0 = kind === 0 ? { label: 'Kerr constant', unit: '× 10⁻¹² m/V²', f: 1e12, digits: 3 } : { label: kind === 1 ? 'electro-optic coefficient r₆₃' : 'electro-optic coefficient r₃₃', unit: 'pm/V', f: 1e12, digits: 2 };
    return {
      title: kind === 0 ? 'Kerr effect' : (mod ? 'Electro-optic modulation' : 'Pockels effect'),
      formula: mod ? 'depth = sin(π V_m H / V_π),   H = 1 / √(1 + (f / f_c)²)' : (kind === 0 ? 'P = P₀ sin²(Γ/2),   Γ = π (V / V_π)²,   K = d² / (2 l V_π²)'
        : (kind === 1 ? 'P = P₀ sin²(Γ/2),   Γ = π V / V_π,   r = λ / (2 n³ V_π)' : 'P = P₀ sin²(Γ/2),   Γ = π V / V_π,   r = λ d / (2 n³ L V_π)')),
      note: kind === 0 ? 'l = ' + fmt(p.l * 1000, 0) + ' mm, d = ' + fmt(p.d * 1000, 1) + ' mm, λ = 632.8 nm' : 'n = ' + fmt(p.n, 2) + (kind === 2 ? ', L = ' + fmt(p.L * 1000, 0) + ' mm, d = ' + fmt(p.d * 1000, 1) + ' mm' : '') + ', λ = 632.8 nm',
      items: items, wire: [['hv', 'cell']],
      x: MODE === 2 ? { max: Math.max(1, Math.ceil(vp * 0.08)), step: 0.001 } : (mod ? undefined : { max: Math.ceil(vp * 1.35), step: kind === 2 ? 0.01 : 0.1 }),
      A: MODE === 3 ? { max: Math.ceil(p.fc * 3 / 1000) } : undefined,
      handles: { x: 'hv', A: 'hv' }, src: 'src', readyOn: 'det', readyText: [mod ? 'Bias at a quarter wave and centre the beam on the detector' : 'Cross the analyser: the field is dark at zero volts', mod ? 'Set the bias' : 'Cross the analyser'],
      upd: function (I) { I.ana.rot.rotation.x = Math.PI * 0.75; I.pol.rot.rotation.x = Math.PI / 4; },
      beams: function (I) { return [[I.src, I.det]]; }, meter: mod ? 'm' : 'P',
      eye: { title: mod ? 'Received light' : 'Light through the analyser', t: 'level', key: mod ? 'm' : 'P', scale: mod ? 3 : 1 / p.P0 },
      plan: function (i, s) { return MODE === 3 ? fmt(s.A / 1000, 2) + ' kHz' : (MODE === 2 ? 'amplitude ' + fmt(s.x, 3) + ' V' : fmt(s.x, 1) + ' V'); },
      res: [R0, { label: 'half-wave voltage', unit: 'V', f: 1, digits: kind === 2 ? 2 : 0 }, { label: 'half-wave voltage', unit: 'V', f: 1, digits: 2 }, { label: 'bandwidth of the link', unit: 'kHz', f: 1e-3, digits: 2 }],
      hideCols: MODE === 2 ? ['A'] : (MODE === 3 ? ['x'] : []),
      graph: mod ? null : { x: function (r) { return r.x; }, y: function (r) { return r.P * 1e6; }, xlabel: 'voltage (V)', ylabel: 'light (µW)', fit: null },
      view: [[-0.2, 0.5, 0.65], [-0.25, 0.1, BZ + 0.05]], tol: 0.02
    };
  }
  function cfgFaraday() {
    var mo = MODE === 2, filt = MODE === 1, dense = hasS(/dense/i);
    var items = [[mo ? 'laser' : 'lamp', 'src', -0.84, BZ, { text: filt ? 'TUNGSTEN LAMP' : 'SODIUM LAMP', name: mo ? 'He-Ne laser' : (filt ? 'Tungsten lamp' : 'Sodium lamp'), info: mo ? '632.8 nm.' : (filt ? 'White light; the filters pick the colour.' : 'Yellow light, 589.3 nm.') }]];
    if (filt) items.push(['plate', 'fil', -0.7, BZ, { color: 0x4060d0, text: 'FILTER', name: 'Interference filters', info: '450, 550 and 650 nm, changed by hand.' }]);
    items.push(['polar', 'pol', -0.56, BZ, { text: 'POLARISER', name: 'Polariser', info: 'Fixed at 0 degrees.' }]);
    items.push(mo ? ['solenoid', 'mag', -0.3, BZ, { name: 'Flint glass rod in a solenoid', info: (SAMPLE || 'The rod') + ', ' + fmt(p.l * 100, 0) + ' cm long; the coil gives ' + fmt(p.kB * 1000, 1) + ' mT per ampere.' }]
      : ['magnet', 'mag', -0.3, BZ, { rod: true, text: 'ELECTROMAGNET', name: 'Glass rod in an electromagnet', info: (SAMPLE || 'Flint glass') + ', ' + fmt(p.l * 100, 0) + ' cm in the field (hollow pole pieces).' }]);
    items.push(['polar', 'ana', -0.02, BZ, { name: 'Analyser', info: mo ? 'Fixed at 45 degrees.' : 'Divided circle read to 0.001 degree with a half-shade.' }],
      ['detector', 'det', 0.2, BZ, { name: 'Photocell', info: 'Reads the light through the analyser.' }],
      ['meter', 'met', 0.46, -0.02, { text: 'GAUSSMETER', name: 'Gaussmeter', info: 'Reads the field on the rod.' }],
      ['source', 'ps', -0.3, BZ + 0.2, { text: mo ? 'AC SUPPLY' : 'MAGNET SUPPLY', name: mo ? 'Alternating current supply' : 'Magnet power supply', info: 'Sets the coil current, read to 0.001 A.' }]);
    return {
      title: mo ? 'Magneto-optic modulation' : 'Faraday effect', formula: mo ? 'depth = sin(2 V B l)' : (filt ? 'ρ = V(λ) B l,   V ∝ λ⁻ᵖ' : 'ρ = V B l'),
      note: 'l = ' + fmt(p.l * 100, 1) + ' cm' + (mo ? ', analyser at 45°' : ', null = 90° + ρ'),
      items: items, wire: [['ps', 'mag']], handles: { x: 'ana', A: 'ps', stage: 'fil' }, src: 'src', readyOn: 'ana', readyText: [mo ? 'Set the analyser at 45 degrees' : 'Cross the analyser with no current (the null)', mo ? 'Set the analyser' : 'Find the null'],
      stages: ['blue filter (450 nm)', 'green filter (550 nm)', 'red filter (650 nm)'],
      upd: function (I) { I.ana.rot.rotation.x = mo ? Math.PI / 4 : p.x; if (I.fil) { var c = [0x4060d0, 0x40b060, 0xd04030][Math.round(p.stage) || 0]; I.fil.g.children.forEach(function (m) { if (m.material && m.material.transmission) m.material.color.setHex(c); }); } },
      beams: function (I) { return [[I.src, I.det]]; }, meter: 'B',
      eye: { title: mo ? 'Received light' : 'Light through the analyser', t: 'level', key: mo ? 'm' : 'P', scale: mo ? 4 : 1 },
      plan: function (i, s) { return MODE === 2 ? 'current amplitude ' + fmt(s.A, 2) + ' A' : (MODE === 1 ? ['blue', 'green', 'red'][Math.round(s.stage)] + ' filter, ' + (s.A > 0 ? 'magnet at ' + fmt(s.A, 0) + ' A' : 'magnet off') : fmt(s.A, 0) + ' A: the null'); },
      res: [{ label: 'Verdet constant', unit: 'rad/(T m)', f: 1, digits: 3 }, { label: 'power p in V ∝ λ⁻ᵖ', unit: '', f: 1, digits: 3 }, { label: 'Verdet constant', unit: 'rad/(T m)', f: 1, digits: 3 }],
      hideCols: mo ? [] : ['m'],
      graph: MODE === 0 ? { x: function (r) { return r.B * 1000; }, y: function (r) { return r.x / DEG; }, xlabel: 'field (mT)', ylabel: 'analyser at null (°)', fit: 'linear' } : null,
      view: [[-0.2, 0.5, 0.65], [-0.3, 0.1, BZ + 0.05]], tol: 0.02
    };
  }
  function cfgFraun() {
    var O = ['WIRE MESH', 'CIRCULAR APERTURE', 'SQUARE APERTURE', 'SINGLE SLIT', 'DOUBLE SLIT', 'GRATING'];
    if (MODE === 0 && hasS(/cross/i)) O[0] = 'CROSS GRATING';
    var top = planMax('x');
    var NM = ['spot', 'dark ring', 'dark band', 'minimum', 'bright fringe', 'order'];
    return {
      title: 'Laser diffraction', formula: ['d sin θ = m λ', 'a sin θ = (zero of J₁) λ / π:  3.8317, 7.0156', 'a sin θ = m λ (minima)', 'a sin θ = m λ (minima)', 'd sin θ = m λ (maxima)', 'λ = d sin θ / m'][MODE] + ',   sin θ = sin(atan(x / L))',
      note: 'L = ' + fmt(p.L * 100, 1) + ' cm' + (MODE === 5 ? ', d = ' + fmt(p.d * 1e6, 3) + ' µm' : ', λ = ' + fmt(p.lam * 1e9, 1) + ' nm'),
      items: [['laser', 'src', -0.8, BZ, { name: 'He-Ne laser', info: '632.8 nm.' }],
        ['plate', 'obj', -0.55, BZ, { color: 0x30343a, text: O[MODE], name: O[MODE].toLowerCase().replace(/^./, function (c) { return c.toUpperCase(); }), info: (SAMPLE || 'The object') + '.' }],
        ['screen', 'scr', 0.35, BZ, { name: 'Screen with a scale and cursor', info: 'A millimetre scale; the cursor is read to 0.001 mm with its vernier.' }]],
      x: { max: Math.max(5, Math.ceil(top * 1500)) }, handles: { x: 'scr' }, src: 'src', readyOn: 'obj', readyText: ['Set the object square to the beam', 'Square the object'],
      upd: function (I) { I.scr.cursor.position.z = -Math.min(0.16, p.x); pattern(I.scr.ptex, 0.16); },
      beams: function (I) { return [[I.src, I.scr]]; }, meter: 'I',
      eye: { title: 'Around the cursor', t: 'strip', key: 'I', span: function () { return Math.max(top * 0.35, 5e-4); }, gamma: 0.4 },
      plan: function (i) { var k = MODE === 1 ? i + 1 : i + 1; return NM[MODE] + ' ' + k; },
      res: [{ label: 'lattice spacing d', unit: 'µm', f: 1e6, digits: 2 }, { label: 'aperture diameter', unit: 'µm', f: 1e6, digits: 2 }, { label: 'aperture side', unit: 'µm', f: 1e6, digits: 2 },
        { label: 'slit width', unit: 'µm', f: 1e6, digits: 2 }, { label: 'slit separation', unit: 'µm', f: 1e6, digits: 2 }, { label: 'laser wavelength', unit: 'nm', f: 1e9, digits: 1 }],
      view: [[-0.1, 0.5, 0.7], [-0.15, 0.1, BZ]], tol: 0.02
    };
  }
  function lampsCdev() {
    var na = hasS(/sodium/i), ne = hasS(/neon/i), hgS = !na && !ne;
    return [['lamp', 'cal', -0.82, BZ, { stages: [0], text: 'MERCURY LAMP', name: 'Mercury calibration lamp', info: 'Its violet, blue and green lines calibrate the drum.' }],
      ['lamp', 'smp', -0.82, BZ, { stages: [1], text: na ? 'SODIUM LAMP' : (ne ? 'NEON LAMP' : 'MERCURY LAMP'), name: 'Lamp under test', info: (SAMPLE || 'The lamp under test') + '.' + (hgS ? ' (The same mercury lamp: its yellow doublet is under test.)' : '') }]];
  }
  function cfgCdev() {
    return {
      title: 'Constant deviation spectrometer', formula: 'λ = Lagrange quadratic through the three calibration points (drum → true λ)',
      note: 'mercury: 404.6565, 435.8335, 546.0750 nm (NIST, in air)',
      items: lampsCdev().concat([['slit', 'slit', -0.6, BZ, { name: 'Collimator slit', info: 'Narrow, vertical.' }],
        ['table', 'tab', -0.22, BZ, { on: 'prism', name: 'Pellin-Broca prism on its table', info: 'Turned by the wavelength drum; the line at minimum deviation leaves at 90 degrees.' }],
        ['scope', 'tel', -0.22, BZ, { ry: -Math.PI / 2, R: 0.16, name: 'Fixed telescope at 90 degrees', info: 'The line on its cross-wire is the one the drum names.' }],
        ['source', 'drum', 0.32, BZ + 0.05, { text: 'WAVELENGTH DRUM', name: 'Wavelength drum', info: 'Engraved in nanometres, read to 0.0001 nm with its vernier.' }]]),
      handles: { x: 'drum', stage: 'smp' }, src: 'cal', readyOn: 'tel', readyText: ['Focus the telescope on the slit image', 'Focus the telescope'],
      stages: ['mercury calibration lamp', 'lamp under test'], lamNow: function () { return p.x; },
      upd: function (I) { I.tab.rot.rotation.y = (p.x - 5.5e-7) * 2e6; },
      beams: function (I) { return [[Math.round(p.stage) ? I.smp : I.cal, I.tab]]; }, meter: 'I',
      eye: { title: 'In the telescope', t: 'strip', key: 'I', span: function () { return 1.2e-9; } },
      plan: ['mercury violet 404.66 nm', 'mercury blue 435.83 nm', 'mercury green 546.07 nm', 'the first line of the lamp under test', 'the second line of the lamp under test'],
      res: [{ label: 'separation of the two lines', unit: 'nm', f: 1e9, digits: 3 }, { label: 'wavelength of the first line', unit: 'nm', f: 1e9, digits: 3 }],
      view: [[-0.2, 0.55, 0.6], [-0.25, 0.1, BZ]], tol: 0.02
    };
  }
  function cfgPlate(title, text, color, span, plan, res, formula, note, extra) {
    var c = {
      title: title, formula: formula, note: note,
      items: [['source', 'src', -0.62, BZ + 0.05, { text: 'COMPARATOR LAMP', name: 'Comparator lamp', info: 'Lights the plate from below.' }],
        ['slide', 'pl', -0.15, BZ + 0.02, { text: text, color: color, name: 'Plate on the comparator', info: (SAMPLE || text) + '. The micrometer moves it under the microscope.' }]],
      handles: { x: 'pl' }, src: 'src', readyOn: 'pl', readyText: ['Lay the plate on the comparator and focus the microscope', 'Focus the microscope'],
      upd: function (I) { var v = (p.x * (extra && extra.scale || 1e3)) % 10; I.pl.stage.position.x = -0.02 + 0.004 * v; },
      beams: function () { return []; }, meter: 'I',
      eye: { title: 'In the microscope', t: 'strip', key: 'I', span: function () { return span; }, gamma: 0.5 },
      plan: plan, res: res, view: [[-0.15, 0.55, 0.55], [-0.15, 0.08, BZ]], tol: 0.02
    };
    Object.keys(extra || {}).forEach(function (k) { c[k] = extra[k]; });
    return c;
  }
  function cfgRowland() {
    var fe = hasS(/iron/i);
    return cfgPlate('Concave grating (Rowland mounting)', fe ? 'IRON ARC PLATE' : 'MERCURY PLATE', 0x1e1e1e, MODE === 2 ? 2e-4 : 5e-4,
      MODE === 2 ? ['the inner half-blackening edge of the line', 'the centre of the line', 'the outer half-blackening edge'] : ['the first standard line', 'the second standard line', 'the line under study'],
      [{ label: 'plate factor', unit: 'nm/mm', f: 1e6, digits: 4 }, { label: 'wavelength of the line', unit: 'nm', f: 1e9, digits: 3 }, { label: 'resolving power', unit: '', f: 1, digits: 0 }],
      MODE === 2 ? 'R = λ / (FWHM / 0.886),   λ(s) = d (sin α + sin(s / R)) / m' : 'plate factor = Δλ / Δs;   λ = λ₁ + (s − s₁) × plate factor',
      'standards ' + fmt(p.la * 1e9, 4) + ' and ' + fmt(p.lb * 1e9, 4) + ' nm; R = ' + fmt(p.R, 2) + ' m, ' + fmt(1e-3 / p.d, 0) + ' lines/mm, order ' + fmt(p.m, 0), { scale: 1e3, lamNow: function () { return K.lam(p, p.x); } });
  }
  function cfgBand() {
    return cfgPlate('AlO band spectrum (simulated)', 'AlO BANDS (SIMULATED)', 0x13304a, 1.2e-9,
      ['head of the (2,0) band', 'head of the (1,0) band', 'head of the (0,0) band', 'head of the (0,1) band', 'head of the (0,2) band'],
      [{ label: 'ω_e x_e of the ground state', unit: 'cm⁻¹', f: 0.01, digits: 3 }, { label: 'ω_e of the ground state', unit: 'cm⁻¹', f: 0.01, digits: 2 },
        { label: 'ω_e of the upper state', unit: 'cm⁻¹', f: 0.01, digits: 2 }, { label: 'ω_e x_e of the upper state', unit: 'cm⁻¹', f: 0.01, digits: 3 }],
      'ΔG(v+½) from neighbouring heads;   ω_e x_e = (ΔG(½) − ΔG(3/2)) / 2,   ω_e = ΔG(½) + 2 ω_e x_e', 'ν = 1 / λ; heads taken as band origins; SIMULATED spectrogram',
      { scale: 1e9, lamNow: function () { return p.x; } });
  }
  function cfgSpec() {
    var kind = Math.round(p.kind), did = hasS(/didymium/i);
    var items = kind === 2 ? [['mirror', 'src', -0.82, BZ, { name: 'Heliostat mirror', info: 'Follows the Sun and sends its light to the slit. Never look into it.' }],
      ['slit', 'slit', -0.62, BZ, { name: 'Entrance slit', info: 'Narrow, to resolve the lines.' }]]
      : [['lamp', 'src', -0.82, BZ, { text: kind === 1 ? 'MERCURY LAMP' : 'WHITE LAMP', name: kind === 1 ? 'Mercury lamp with a violet filter' : 'White lamp', info: kind === 1 ? 'Excites the crystals.' : 'Every colour at once.' }],
        kind === 1 ? ['plate', 'smp', -0.62, BZ, { color: 0xc8e040, text: 'UNH CRYSTALS', name: 'Uranyl nitrate crystals', info: (SAMPLE || 'The sample') + '. Glows green under violet light.' }]
          : ['plate', 'smp', -0.62, BZ, { color: did ? 0xc8a0d0 : 0x8a2a8a, text: did ? 'DIDYMIUM CELL' : 'KMnO₄ CELL', name: 'Cell of solution', info: (SAMPLE || 'The solution') + '.' }]];
    items.push(['table', 'tab', -0.25, BZ, { on: 'prism', name: kind === 2 ? 'Grating spectrometer' : 'Monochromator', info: 'Turned by the wavelength drum.' }],
      ['scope', 'tel', -0.25, BZ, { R: 0.2, name: 'Exit slit and detector arm', info: 'Passes a narrow band of wavelengths to the detector.' }],
      ['meter', 'met', 0.46, -0.02, { text: kind === 1 ? 'PHOTOMULTIPLIER' : 'PHOTOMETER', name: 'Detector readout', info: 'Reads the light at the exit slit.' }],
      ['source', 'drum', 0.3, BZ + 0.08, { text: 'WAVELENGTH DRUM', name: 'Wavelength drum', info: 'Read to 0.0001 nm.' }]);
    return {
      title: kind === 2 ? 'Fraunhofer lines' : (kind === 1 ? 'Uranyl fluorescence' : 'Band spectrum of a liquid'),
      formula: kind === 1 ? 'peak = vertex of the parabola through ln I;   spacing = (σ₁ − σ_N) / (N − 1)' : (kind === 2 ? 'line = vertex of the parabola through the three readings' : 'band centre = vertex of the parabola through ln(−ln T)'),
      note: kind === 2 ? 'SIMULATED DATA: a 5772 K continuum with laboratory line wavelengths' : 'three readings about each band, half a band width apart',
      items: items, handles: { x: 'drum' }, src: 'src', readyOn: 'tel', readyText: ['Focus the spectrometer and open the exit slit', 'Focus the spectrometer'],
      lamNow: function () { return p.x; },
      upd: function (I) { I.tab.rot.rotation.y = (p.x - 5.5e-7) * 2e6; },
      beams: function (I) { return [[I.src, I.tab]]; }, meter: 'S',
      eye: { title: 'Spectrum near the drum setting', t: 'strip', key: 'S', span: function () { return p.w * 3; }, gamma: 0.8 },
      plan: function (i) { return (MODE === 1 ? 'peak ' + (Math.floor(i / 3) + 1) + ': ' : '') + ['half a width below', 'the setting nearest the ' + (kind === 1 ? 'peak' : 'minimum'), 'half a width above'][i % 3]; },
      res: [{ label: 'centre of the band', unit: 'nm', f: 1e9, digits: 2 }, { label: 'mean vibronic spacing', unit: 'cm⁻¹', f: 0.01, digits: 1 }, { label: 'wavelength of the line', unit: 'nm', f: 1e9, digits: 3 }],
      view: [[-0.2, 0.55, 0.6], [-0.25, 0.1, BZ]], tol: 0.02
    };
  }
  function cfgFilm() {
    var feco = MODE === 1;
    return {
      title: feco ? 'Fringes of equal chromatic order' : 'Multiple-beam fringes at a step', formula: feco ? 'm = λ_(m+1) / (λ_m − λ_(m+1)),   t = m (λ_m − λ′_m) / 2' : 't = (λ / 2)(shift / s)',
      note: feco ? 'white light into a spectrometer; bright bands at 2G = m λ' : 'λ = ' + fmt(p.lam * 1e9, 1) + ' nm; s = fringe spacing on the bare glass',
      items: [['lamp', 'src', -0.82, BZ, { text: feco ? 'WHITE LAMP' : 'MERCURY LAMP', name: feco ? 'White lamp' : 'Mercury lamp with a green filter', info: feco ? 'Every colour at once.' : '546.1 nm.' }],
        ['slide', 'smp', -0.3, BZ + 0.02, { text: 'FILM STEP · SILVERED', color: 0x40403a, name: 'Film step under a silvered flat', info: (SAMPLE || 'The film') + ', over-coated with silver.' }],
        feco ? ['source', 'mono', 0.3, BZ + 0.05, { text: 'SPECTROMETER', name: 'Spectrometer', info: 'Spreads the light from the step region; read to 0.0001 nm.' }]
          : ['source', 'mono', 0.3, BZ + 0.05, { text: 'MICROSCOPE DRIVE', name: 'Travelling-microscope drive', info: 'Read to 0.0001 mm.' }]],
      handles: { x: 'smp', A: 'mono', stage: 'smp' }, src: 'src', readyOn: 'smp', readyText: ['Lay the flat on and focus the microscope on the fringes', 'Focus on the fringes'],
      stages: ['on the bare glass', 'on the film'], lamNow: feco ? function () { return p.A; } : undefined,
      beams: function () { return []; }, meter: 'I',
      eye: feco ? { title: 'Spectrometer field', t: 'strip', key: 'I', ctl: 'A', span: function () { return 6e-9; } } : { title: 'In the microscope', t: 'strip', key: 'I', span: function () { return p.s * 1.2; } },
      plan: feco ? ['bright band m on the bare glass', 'bright band m + 1 on the bare glass', 'bright band m on the film'] : ['a fringe on the bare glass', 'the next fringe on the bare glass', 'the same fringe on the film'],
      res: [{ label: 'film thickness', unit: 'nm', f: 1e9, digits: 1 }, { label: 'film thickness', unit: 'nm', f: 1e9, digits: 1 }],
      hideCols: feco ? ['x'] : ['A'],
      view: [[-0.15, 0.55, 0.55], [-0.2, 0.08, BZ]], tol: 0.02
    };
  }
  function cfgStoney() {
    var si = hasS(/silicon|wafer/i), top = planMax('x');
    return {
      title: 'Residual stress by Stoney\'s equation', formula: 'r² = m R λ;   σ_f = M_s h_s² (1/R₁ − 1/R₀) / (6 h_f)',
      note: 'λ = ' + fmt(p.lam * 1e9, 1) + ' nm, h_s = ' + fmt(p.hs * 1000, 3) + ' mm, h_f = ' + fmt(p.hf * 1e9, 0) + ' nm, M_s = ' + fmt(p.Ms / 1e9, 1) + ' GPa',
      items: [['lamp', 'src', -0.82, BZ, { text: 'SODIUM LAMP', name: 'Sodium lamp', info: '589.3 nm.' }],
        ['bs', 'bs', -0.55, BZ, { name: 'Glass plate at 45 degrees', info: 'Sends the light down onto the sample and lets the reflected light up to the microscope.' }],
        ['slide', 'smp', -0.2, BZ + 0.02, { text: si ? 'Si WAFER + FLAT' : 'GLASS SLIDE + FLAT', color: 0x2a2a2a, name: si ? 'Coated silicon wafer under an optical flat' : 'Coated glass slide under an optical flat', info: (SAMPLE || 'The sample') + '.' }]],
      x: { max: Math.max(10, Math.ceil(top * 1300)) }, handles: { x: 'smp', stage: 'smp' }, src: 'src', readyOn: 'smp', readyText: ['Focus the microscope on the rings and centre them', 'Focus on the rings'],
      stages: ['before coating', 'after coating'],
      beams: function (I) { return [[I.src, I.bs]]; }, meter: 'I',
      eye: { title: 'In the microscope', t: 'radial', key: 'I', span: function () { return top * 1.15; } },
      plan: function (i, s) { return (s.stage < 0.5 ? 'before coating' : 'after coating') + ': dark ring ' + [2, 4, 6][i % 3]; },
      res: [{ label: 'change in curvature', unit: '× 10⁻³ m⁻¹', f: 1e3, digits: 3 }, { label: 'film stress', unit: 'MPa', f: 1e-6, digits: 1 }],
      graph: { x: function (r) { return r.m; }, y: function (r) { return r.x * r.x * 1e6; }, xlabel: 'ring m', ylabel: 'r² (mm²)', fit: null },
      view: [[-0.2, 0.55, 0.55], [-0.25, 0.08, BZ]], tol: 0.02
    };
  }
  function cfgPhotom() {
    var led = hasS(/LED/), cfl = hasS(/fluorescent/i);
    return {
      title: 'Photometry', formula: MODE === 1 ? 'E = I d⁻ⁿ,   n = −slope of ln E against ln d' : (MODE === 2 ? 'E_e = (E_e at 1 m) / d²' : 'E = I / d²'),
      note: 'd from the lamp to the meter; a point source far from its own size',
      items: [['rail', 'rail', -0.78, BZ + 0.05, { name: 'Photometer bench', info: 'A rail with a scale in metres.' }],
        ['lamp', 'src', -0.78, BZ, { text: led ? 'LED LAMP' : (cfl ? 'CFL' : 'FILAMENT LAMP'), name: led ? 'LED lamp' : (cfl ? 'Compact fluorescent lamp' : 'Incandescent lamp'), info: (SAMPLE || 'The lamp under test') + '.' }],
        ['detector', 'det', -0.28, BZ, { stage: true, name: 'Lux meter and radiometer heads', info: 'On a carriage that slides along the bench.' }],
        ['meter', 'met', 0.46, -0.02, { text: 'LUX METER', name: 'Lux meter', info: 'Reads the illuminance to 0.1 lx.' }]],
      handles: { x: 'det' }, src: 'src', readyOn: 'det', readyText: ['Darken the room and face the meter heads square to the lamp', 'Square the meter'],
      upd: function (I) { I.det.g.position.x = -0.78 + p.x; },
      beams: function (I) { return [[I.src, I.det]]; }, meter: 'E',
      plan: function (i, s) { return 'meter at ' + fmt(s.x, 2) + ' m'; },
      res: [{ label: 'luminous intensity', unit: 'cd', f: 1, digits: 2 }, { label: 'power n of the distance', unit: '', f: 1, digits: 3 }, { label: 'irradiance at 1 m', unit: 'mW/m²', f: 1000, digits: 1 }],
      graph: { x: function (r) { return 1 / (r.x * r.x); }, y: function (r) { return MODE === 2 ? r.Ee * 1000 : r.E; }, xlabel: '1 / d² (m⁻²)', ylabel: MODE === 2 ? 'irradiance (mW/m²)' : 'illuminance (lx)', fit: 'linear' },
      view: [[-0.3, 0.55, 0.65], [-0.35, 0.08, BZ]], tol: 0.02
    };
  }
  function cfgAo() {
    var bragg = MODE >= 1, top = Math.max(planMax('x'), 0.004);
    var items = [['laser', 'src', -0.8, BZ, { name: 'He-Ne laser', info: '632.8 nm.' }],
      ['tank', 'cell', -0.5, BZ, { crystal: bragg, name: bragg ? 'Acousto-optic crystal (Bragg cell)' : 'Ultrasonic water cell', info: (SAMPLE || 'The medium') + '; driven at ' + fmt(p.f / 1e6, 1) + ' MHz.' }],
      ['source', 'rf', -0.5, BZ + 0.2, { text: 'RF DRIVER ' + fmt(p.f / 1e6, 0) + ' MHz', name: 'RF driver', info: 'Drives the transducer; its power is read to 0.0001 W.' }]];
    if (MODE === 2) items.push(['detector', 'det', 0.2, BZ, { name: 'Power-meter head', info: 'Measures the zero and first orders in turn.' }], ['meter', 'met', 0.46, -0.02, { text: 'POWER METER', name: 'Power meter', info: 'Reads the orders\' powers.' }]);
    else items.push(['screen', 'scr', 0.35, BZ, { name: 'Screen with a scale and cursor', info: 'A millimetre scale, read to 0.001 mm.' }]);
    return {
      title: 'Acousto-optics', formula: MODE === 0 ? 'v = m λ f / sin θ_m' : (MODE === 1 ? 'v = λ f / (2 sin θ_B),   deflection = 2 θ_B' : 'η = sin²((π/2) √(P / P₁₀₀))'),
      note: 'f = ' + fmt(p.f / 1e6, 1) + ' MHz, λ = 632.8 nm' + (MODE < 2 ? ', L = ' + fmt(p.L * 100, 0) + ' cm' : ''),
      items: items, wire: [['rf', 'cell']], x: { max: Math.max(5, Math.ceil(top * 1500)) }, handles: { x: 'scr', A: 'rf' }, src: 'src', readyOn: 'cell', readyText: [bragg ? 'Turn the cell to the Bragg angle (one strong first order)' : 'Switch on the RF driver and set the cell square to the beam', bragg ? 'Find the Bragg angle' : 'Start the ultrasound'],
      upd: function (I) { if (I.scr) { I.scr.cursor.position.z = -Math.min(0.16, p.x); pattern(I.scr.ptex, 0.16); } },
      beams: function (I) { return [[I.src, I.scr || I.det]]; }, meter: MODE === 2 ? 'eta' : 'I',
      eye: MODE === 2 ? { title: 'First order', t: 'level', key: 'eta' } : { title: 'Around the cursor', t: 'strip', key: 'I', span: function () { return top * 0.4; }, gamma: 0.5 },
      plan: function (i, s) { return MODE === 2 ? 'drive ' + fmt(s.A, 3) + ' W' : (MODE === 1 ? (i === 0 ? 'the zero order' : 'the first (Bragg) order') : 'order ' + (i + 1)); },
      res: [{ label: 'speed of sound', unit: 'm/s', f: 1, digits: 1 }, { label: 'speed of sound', unit: 'm/s', f: 1, digits: 1 }, { label: 'drive for full efficiency P₁₀₀', unit: 'W', f: 1, digits: 3 }],
      hideCols: MODE === 2 ? ['x', 'm'] : ['A', 'eta'],
      view: [[-0.15, 0.5, 0.7], [-0.2, 0.1, BZ]], tol: 0.02
    };
  }
  function cfgEllips() {
    var ra = p.meth > 0.5, metal = p.sample > 0.5, ANG = [p.phi0, p.phi1, p.phi2];
    var items = [['laser', 'src', -0.5, BZ, { name: 'He-Ne laser', info: '632.8 nm.' }],
      ['polar', 'pol', -0.4, BZ, { text: 'POLARISER', name: 'Polariser', info: ra ? 'Fixed at 45 degrees.' : 'Divided circle read to 0.001 degree.' }]];
    if (!ra) items.push(['plate', 'cmp', -0.3, BZ, { color: 0x9fc8d8, text: 'λ/4 at 45°', name: 'Quarter-wave compensator', info: 'Fixed at +45 degrees.' }]);
    items.push(['table', 'tab', 0.0, BZ, { name: 'Goniometer table with the sample', info: (SAMPLE || (metal ? 'A metal film' : 'Oxidised silicon wafer')) + '. The arms turn to set the angle of incidence.' }],
      ['polar', 'ana', 0.3, BZ, { name: 'Analyser', info: 'Divided circle read to 0.001 degree.' }],
      ['detector', 'det', 0.4, BZ, { name: 'Photodetector', info: 'Reads the reflected light through the analyser.' }],
      ['meter', 'met', 0.62, 0.05, { text: 'PHOTOMETER', name: 'Photometer', info: 'Reads the detector to 0.0001 %.' }]);
    var ARM = { src: [-1, 0.52], pol: [-1, 0.4], cmp: [-1, 0.3], ana: [1, 0.3], det: [1, 0.42] };
    function at(r, side) { var ph = ANG[Math.round(p.stage) || 0]; return [side * r * Math.sin(ph), BZ + r * Math.cos(ph)]; }
    return {
      title: 'Ellipsometry', formula: ra ? 'tan Ψ = √(I₀ / I₉₀),   cos Δ = (I₄₅ − I₁₃₅) / (2 √(I₀ I₉₀))' : 'Ψ = analyser,   Δ = 270° − 2 × polariser',
      note: metal ? 'ε = sin²φ [1 + tan²φ ((1 − ρ)/(1 + ρ))²],   N = √ε' : 'ρ = tan Ψ e^(iΔ) matched by the film model: n₁ = ' + fmt(p.n1, 3) + ' on Si (3.882 + 0.019i), λ = 632.8 nm',
      items: items, handles: { x: 'pol', A: 'ana', stage: 'tab' }, src: 'src', readyOn: 'det', readyText: ['Centre the reflected beam on the detector', 'Centre the beam'],
      stages: [fmt(p.phi0 / DEG, 0) + '° incidence', fmt(p.phi1 / DEG, 0) + '° incidence', fmt(p.phi2 / DEG, 0) + '° incidence'],
      upd: function (I) { Object.keys(ARM).forEach(function (k) { if (!I[k]) return; var q = at(ARM[k][1], ARM[k][0]), ph = ANG[Math.round(p.stage) || 0];
          I[k].g.position.x = q[0]; I[k].g.position.z = q[1]; I[k].g.rotation.y = ARM[k][0] < 0 ? Math.PI / 2 - ph : -(Math.PI / 2 - ph); });
        I.pol.rot.rotation.x = ra ? Math.PI / 4 : p.x; I.ana.rot.rotation.x = p.A; },
      beams: function () { return [[at(0.45, -1), [0.0, BZ], at(0.42, 1)]]; }, meter: 'I',
      eye: { title: 'Detector', t: 'level', key: 'I', scale: ra ? 0.6 : 50 },
      plan: function (i, s) { var a = fmt(ANG[Math.round(s.stage)] / DEG, 0) + '°: '; return ra ? a + 'analyser at ' + fmt(s.A / DEG, 0) + '°' : a + 'polariser and analyser at the null'; },
      res: [{ label: 'film thickness', unit: 'nm', f: 1e9, digits: 2 }, { label: 'refractive index n', unit: '', f: 1, digits: 4 }, { label: 'extinction coefficient k', unit: '', f: 1, digits: 4 }],
      hideCols: ra ? ['x'] : [],
      view: [[0.0, 0.6, 0.55], [0.0, 0.1, BZ + 0.1]], tol: 0.02
    };
  }
  function cfgAerosol() {
    var E = [0.3, 0.5, 0.7, 1, 2, 3, 5, 10];
    return {
      title: 'Aerosol spectrometer (SIMULATED DATA)', formula: MODE === 1 ? 'median: where the cumulative count reaches half (log interpolation)' : 'n = Σ counts / (Q t)',
      note: 'Q = 2.83 L/min, t = 60 s; only particles above 0.3 µm are counted; SIMULATED air',
      items: [['source', 'src', -0.3, BZ + 0.05, { text: 'OPTICAL PARTICLE COUNTER', name: 'Optical particle counter', info: 'Draws the air through a laser beam and sorts the particles into eight size channels.' }],
        ['chuck', 'inlet', -0.52, BZ + 0.05, { name: 'Inlet with its zero filter', info: 'The air enters here.' }],
        ['meter', 'met', 0.2, BZ + 0.1, { text: 'COUNTS', name: 'Count display', info: 'Shows the counts in the chosen channel.' }]],
      handles: { x: 'src' }, src: 'src', readyOn: 'inlet', readyText: ['Check zero counts on the filter, then take it off and sample', 'Zero and sample'],
      beams: function () { return []; }, meter: 'C',
      plan: function (i) { return 'channel ' + (i + 1) + ': ' + E[i] + (i < 7 ? '-' + E[i + 1] : '+') + ' µm'; },
      res: [{ label: 'number concentration above 0.3 µm', unit: 'cm⁻³', f: 1e-6, digits: 2 }, { label: 'median diameter of the counted particles', unit: 'µm', f: 1e6, digits: 3 }],
      graph: { x: function (r) { return r.x; }, y: function (r) { return r.C; }, xlabel: 'channel', ylabel: 'counts in one minute', fit: null },
      view: [[-0.1, 0.5, 0.55], [-0.1, 0.08, BZ + 0.05]], tol: 0.02
    };
  }
  var CFGS = { po9_fp: cfgFp, po9_zeeman: cfgZeeman, po9_ellipse: cfgEllipse, po9_biref: cfgBiref, po9_photoel: cfgPhotoel, po9_eo: cfgEo,
    po9_faraday: cfgFaraday, po9_fraun: cfgFraun, po9_cdev: cfgCdev, po9_rowland: cfgRowland, po9_band: cfgBand, po9_spec: cfgSpec,
    po9_film: cfgFilm, po9_stoney: cfgStoney, po9_photom: cfgPhotom, po9_ao: cfgAo, po9_ellipso: cfgEllips, po9_aerosol: cfgAerosol };
  if (!CFGS[KN]) throw new Error('po9-optics-bench has no set-up for kernel ' + KN);
  var C = CFGS[KN]();
  LAMF = C.lamNow || null;
  var RES = C.res[MODE] || C.res[0];

  // ------------------------------------------------------------------------------------------ controls, readings, columns (from the lab data)
  var CTL = [];
  (S.lab.knobs || []).forEach(function (k) {
    if (k.hidden || ['x', 'A', 'stage'].indexOf(k.param) < 0) return;
    var c = { key: k.param, label: k.label, unit: k.unit || '', f: 1 / (+k.k || 1), min: +k.min, max: +k.max, step: +k.step, digits: k.digits === undefined ? 2 : +k.digits };
    if (C[k.param]) Object.keys(C[k.param]).forEach(function (q) { c[q] = C[k.param][q]; });
    CTL.push(c);
  });
  var PLAN = K.plan(p);
  var STAGES = [];
  PLAN.forEach(function (s) { if (s.stage !== undefined && STAGES.indexOf(Math.round(s.stage)) < 0) STAGES.push(Math.round(s.stage)); });
  CTL = CTL.filter(function (c) { return c.key !== 'stage' || STAGES.length > 1; });
  var USED = {};
  PLAN.forEach(function (s) { Object.keys(s).forEach(function (k) { USED[k] = true; }); });
  CTL = CTL.filter(function (c) { return USED[c.key]; });
  function ctl(key) { for (var i = 0; i < CTL.length; i++) if (CTL[i].key === key) return CTL[i]; return null; }
  function snap(c, v) { var d = Math.round(v * c.f / c.step) * c.step; d = Math.max(c.min, Math.min(c.max, d)); return d / c.f; }
  if (PLAN.length && PLAN[0].stage !== undefined) p.stage = PLAN[0].stage;
  CTL.forEach(function (c) { if (c.key !== 'stage') { p[c.key] = snap(c, p[c.key]); st.set[c.key] = p[c.key] * c.f; } });
  var READS = (S.lab.instruments || []).filter(function (m) { return m.var; }).map(function (m) {
    return { id: m.id, key: m.var, label: m.label, unit: m.unit || '', f: +m.k || 1, lc: +m.lc || 0, digits: m.digits === undefined ? 2 : +m.digits }; });
  function readOf(key) { for (var i = 0; i < READS.length; i++) if (READS[i].key === key) return READS[i]; return null; }
  function rounded(r, v) { if (!r.lc) return v; var lc = r.lc / r.f; return Math.round(v / lc) * lc; }
  var COLS = ((S.lab.table && S.lab.table.columns) || []).map(function (c) {
    var from = String(c.from || ''), o = { id: c.id, label: c.label + (c.unit ? ' (' + c.unit + ')' : ''), f: 1 / (+c.k || 1), digits: c.digits === undefined ? 2 : +c.digits, knob: null, inst: null };
    if (from.indexOf('knob:') === 0) o.knob = from.slice(5);
    if (from.indexOf('inst:') === 0) o.inst = from.slice(5);
    if (C.cols && C.cols[c.id]) Object.keys(C.cols[c.id]).forEach(function (q) { o[q] = C.cols[c.id][q]; });
    return o;
  }).filter(function (c) { return c.id !== 'stage' || STAGES.length > 1; })
    .filter(function (c) { return !(C.hideCols && C.hideCols.indexOf(c.id) >= 0) && !(c.knob && (c.knob === 'x' || c.knob === 'A') && !ctl(c.knob)); });
  function stageName(v) { return (C.stages && C.stages[Math.round(v)]) || String(Math.round(v)); }
  function planName(i) { var s = PLAN[i]; if (!s) return 'reading ' + (i + 1); return typeof C.plan === 'function' ? C.plan(i, s) : (C.plan && C.plan[i]) || 'reading ' + (i + 1); }

  // ------------------------------------------------------------------------------------------ build the bench
  var board = S.rounded(1.9, 0.66, TOP, 0.01, anod); board.rotation.x = -Math.PI / 2; put(board, 0, TOP / 2, BZ + 0.03); S.scene.add(board);
  var holes = S.canvasTex(1024, 512, function (x, w, h) { x.fillStyle = '#17191c'; x.fillRect(0, 0, w, h); x.fillStyle = '#07080a';
    for (var i = 0; i < 38; i++) for (var j = 0; j < 13; j++) { x.beginPath(); x.arc(14 + i * 27, 20 + j * 39, 3.2, 0, 7); x.fill(); } });
  var top = new T.Mesh(new T.PlaneGeometry(1.88, 0.64), new T.MeshStandardMaterial({ map: holes, roughness: 0.5, metalness: 0.3 }));
  top.rotation.x = -Math.PI / 2; put(top, 0, TOP + 0.0006, BZ + 0.03); top.receiveShadow = true; S.scene.add(top);
  S.contact(2.0, 0.76, 0, BZ + 0.03, 0.45);
  var I = {};
  C.items.forEach(function (it) {
    var kind = it[0], id = it[1], o = it[4] || {}, g = new T.Group();
    var parts = BUILD[kind](g, o) || {};
    g.position.set(it[2], 0, it[3]); g.rotation.y = o.ry || 0; S.scene.add(g);
    parts.g = g; parts.kind = kind; parts.o = o; parts.home = [it[2], it[3]];
    if (kind !== 'scope') parts.sh = S.contact(0.12, 0.12, it[2], it[3], 0.35, TOP);
    I[id] = parts;
    if (o.name) S.addApparatus(id, g, o.name, o.info || '');
  });
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  if (SAMPLE) { var sl = S.label(SAMPLE.length > 46 ? SAMPLE.slice(0, 44) + '…' : SAMPLE, { w: 0.36, ratio: 0.09, color: '#1b1b1b', bg: '#f1ead2', weight: 600, px: 1024 });
    sl.rotation.x = -Math.PI / 2; put(sl, 0.0, TOP + 0.002, BZ + 0.33); S.scene.add(sl); }

  function pos(spec, y) { if (Array.isArray(spec)) return new T.Vector3(spec[0], y, spec[1]); return new T.Vector3(spec.g.position.x, y, spec.g.position.z); }
  // fibres: a yellow patch cord from one item to another, with a storage loop
  (C.fibre || []).forEach(function (f) {
    var a = pos(I[f[0]], I[f[0]].y || AXY), b = pos(I[f[1]], AXY), pts = [], n = 60, i, t, loop = f[2];
    a.x += I[f[0]].out || 0; a.y = I[f[0]].y || AXY;
    for (i = 0; i <= n; i++) { t = i / n; var q = a.clone().lerp(b, t);
      q.y = a.y + (b.y - a.y) * t - 0.05 * Math.sin(Math.PI * t) * (loop ? 0.3 : 1);
      if (loop) { var w = Math.sin(Math.PI * t), ang = t * Math.PI * 2 * 2; q.x += 0.05 * w * Math.sin(ang) * 0.6; q.z += 0.07 * w * (1 - Math.cos(ang)) * 0.5; }
      pts.push(q); }
    var tube = S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts), 120, 0.0016, 8, false), fibreM); S.scene.add(tube); I['fibre_' + f[0]] = { g: tube };
  });
  (C.wire || []).forEach(function (wv) { var a = pos(I[wv[0]], TOP + 0.04), b = pos(I[wv[1]], AXY - 0.03); S.wire([[a.x + 0.075, a.y, a.z], [(a.x + b.x) / 2 + 0.03, TOP + 0.012, a.z + 0.05], [b.x, b.y, b.z + 0.024]], 'black'); });

  var beamM = new T.LineBasicMaterial({ color: C.lam ? 0xff3c32 : hex(), transparent: true, opacity: lamOf() > 7e-7 && !C.lam ? 0.35 : 0.85, depthWrite: false, toneMapped: false });
  var beamLines = [];
  for (var bi = 0; bi < 4; bi++) { var bl = new T.Line(new T.BufferGeometry(), beamM); bl.visible = false; bl.renderOrder = 7; S.scene.add(bl); beamLines.push(bl); }

  // ------------------------------------------------------------------------------------------ live drawings
  function gauge(tex, kpa) {
    tex.draw(function (x, w, h) { x.fillStyle = '#f4f1e6'; x.fillRect(0, 0, w, h); x.strokeStyle = '#222'; x.fillStyle = '#222'; x.lineWidth = 3; x.font = '600 22px sans-serif'; x.textAlign = 'center';
      for (var v = 0; v <= 100; v += 10) { var a = Math.PI * (0.75 + 1.5 * v / 100); x.beginPath(); x.moveTo(w / 2 + 100 * Math.cos(a), h / 2 + 100 * Math.sin(a)); x.lineTo(w / 2 + 116 * Math.cos(a), h / 2 + 116 * Math.sin(a)); x.stroke();
        if (v % 20 === 0) x.fillText(String(v), w / 2 + 80 * Math.cos(a), h / 2 + 80 * Math.sin(a) + 8); }
      x.fillText('kPa', w / 2, h / 2 + 60); var an = Math.PI * (0.75 + 1.5 * Math.max(0, Math.min(100, kpa)) / 100);
      x.strokeStyle = '#c0281c'; x.lineWidth = 5; x.beginPath(); x.moveTo(w / 2, h / 2); x.lineTo(w / 2 + 95 * Math.cos(an), h / 2 + 95 * Math.sin(an)); x.stroke(); });
  }
  var specKey = '', specPts = null;
  function spectrum(tex) {                                                   // the computer screen: the transformed spectrum and the cursor
    var show = p.stage > 0.5 && st.on, key = show + '|' + fmt(p.x * 1e9, 2);
    if (key === specKey) return; specKey = key;
    var lo = p.lam0 - 2.5 * p.fwhm, hi = p.lam0 + 2.5 * p.fwhm, i, n = 90;
    if (show && !specPts) { specPts = []; var pk = K.spec(p, p.lam0); for (i = 0; i <= n; i++) specPts.push(K.spec(p, lo + (hi - lo) * i / n) / pk); }
    tex.draw(function (x, w, h) { x.fillStyle = '#0b1220'; x.fillRect(0, 0, w, h); x.fillStyle = '#9fb3c8'; x.font = '500 22px sans-serif';
      if (!show) { x.fillText('Interferogram logger', 24, 44); x.fillText(MODE === 1 ? 'Press Transform to see the spectrum' : 'Recording the detector signal', 24, 80); return; }
      x.fillText('Fourier transform of the interferogram', 24, 36);
      x.strokeStyle = '#2b3b52'; x.lineWidth = 1; x.beginPath(); x.moveTo(40, h - 50); x.lineTo(w - 20, h - 50); x.moveTo(40, h - 50 - 0.5 * (h - 120)); x.lineTo(w - 20, h - 50 - 0.5 * (h - 120)); x.stroke();
      x.strokeStyle = '#5fe08a'; x.lineWidth = 3; x.beginPath();
      for (i = 0; i <= n; i++) { var px = 40 + (w - 60) * i / n, py = h - 50 - Math.max(0, specPts[i]) * (h - 120); if (i) x.lineTo(px, py); else x.moveTo(px, py); } x.stroke();
      var cx = 40 + (w - 60) * (p.x - lo) / (hi - lo); x.strokeStyle = '#ffd166'; x.lineWidth = 2; x.beginPath(); x.moveTo(cx, 50); x.lineTo(cx, h - 50); x.stroke();
      x.fillStyle = '#ffd166'; x.fillText(fmt(p.x * 1e9, 2) + ' nm', Math.min(w - 150, Math.max(40, cx + 8)), 70);
      x.fillStyle = '#9fb3c8'; x.fillText(fmt(lo * 1e9, 0) + ' nm', 40, h - 20); x.fillText(fmt(hi * 1e9, 0) + ' nm', w - 110, h - 20); });
  }
  var patKey = '';
  function pattern(tex, half) {                                              // the corona on the screen card
    var key = String(st.on && st.ready); if (key === patKey) return; patKey = key;
    tex.draw(function (x, w, h) { x.clearRect(0, 0, w, h); if (!(st.on && st.ready)) return; var c = rgb(), i;
      for (i = 0; i < w; i++) { var xx = (i / w - 0.5) * 2 * half, a = Math.pow(K.read(Object.assign({}, p, { x: xx })).I, 0.3);
        if (a < 0.02) continue; var g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, 'rgba(' + c + ',0)'); g.addColorStop(0.5, 'rgba(' + c + ',' + a.toFixed(3) + ')'); g.addColorStop(1, 'rgba(' + c + ',0)');
        x.fillStyle = g; x.fillRect(w - 1 - i, 0, 1, h); } });
  }
  var eyeCan = null, ectx = null, eyeKey = '';
  if (C.eye) { var card = document.createElement('div'); card.className = 'card'; card.appendChild(document.createTextNode(C.eye.title));
    eyeCan = document.createElement('canvas'); eyeCan.width = 300; eyeCan.height = 130; eyeCan.style.cssText = 'width:200px;height:87px;display:block;margin-top:4px;border-radius:8px';
    card.appendChild(eyeCan); S.hud.appendChild(card); ectx = eyeCan.getContext('2d'); }
  function drawEye(rd) {
    if (!C.eye) return;
    var key = [st.on, st.ready, p.stage, fmt(p.x * 1e9, 3), fmt((p.A || 0) * 1e4, 1)].join('|'); if (key === eyeKey) return; eyeKey = key;
    var w = eyeCan.width, h = eyeCan.height, c = rgb(), i, a, lit = st.on && st.ready, e = C.eye;
    ectx.fillStyle = '#0a0b0d'; ectx.fillRect(0, 0, w, h);
    function col(al) { return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + Math.max(0, Math.min(1, al)).toFixed(3) + ')'; }
    if (lit && e.t === 'strip') { var span = e.span(), ck = e.ctl || 'x';
      for (i = 0; i < w; i++) { var q = Object.assign({}, p); q[ck] = p[ck] + (i / w - 0.5) * 2 * span; a = K.read(q)[e.key] * (e.scale || 1); ectx.fillStyle = col(Math.pow(Math.max(0, a), e.gamma || 0.6)); ectx.fillRect(i, 8, 1, h - 16); } }
    else if (lit && e.t === 'rings') { var N = rd.N, cx = w / 2, cy = h / 2, r;
      for (r = 70; r >= 0; r -= 1) { var ph = N + 3.2 * (r / 64) * (r / 64), s = Math.sin(Math.PI * ph), cc = Math.cos(Math.PI * ph);
        a = e.sharp ? 1 / (1 + 30 * s * s) : cc * cc; ectx.fillStyle = col(a); ectx.beginPath(); ectx.arc(cx, cy, r, 0, 7); ectx.fill(); ectx.fillStyle = '#0a0b0d'; if (r > 0) { ectx.beginPath(); ectx.arc(cx, cy, r - 1, 0, 7); ectx.fill(); } } }
    else if (lit && e.t === 'half') { var edge = w * (1 - rd.bright); ectx.fillStyle = col(0.9); ectx.fillRect(edge, 8, w - edge, h - 16);
      if (Math.abs(rd.refl) < 0.012) { ectx.strokeStyle = 'rgba(255,255,255,.6)'; ectx.lineWidth = 2; var rx = w / 2 + rd.refl / 0.012 * w / 2; ectx.beginPath(); ectx.moveTo(rx - 12, h / 2 - 12); ectx.lineTo(rx + 12, h / 2 + 12); ectx.moveTo(rx + 12, h / 2 - 12); ectx.lineTo(rx - 12, h / 2 + 12); ectx.stroke(); } }
    else if (lit && e.t === 'level') { ectx.fillStyle = col(Math.pow(Math.max(0, Math.min(1, rd[e.key] * (e.scale || 1))), 0.6)); ectx.fillRect(0, 8, w, h - 16); }
    else if (lit && e.t === 'radial') { var sp = e.span(), cx2 = w / 2, cy2 = h / 2, rr, R2 = h / 2 - 4;
      for (rr = R2; rr >= 0; rr -= 1) { var q2 = Object.assign({}, p); q2.x = sp * rr / R2; a = Math.pow(Math.max(0, Math.min(1, K.read(q2)[e.key] * (e.scale || 1))), 0.7); ectx.fillStyle = 'rgb(' + Math.round(c[0] * a) + ',' + Math.round(c[1] * a) + ',' + Math.round(c[2] * a) + ')'; ectx.beginPath(); ectx.arc(cx2, cy2, rr + 1, 0, 7); ectx.fill(); }
      var hx = cx2 + Math.min(1, Math.abs(p.x) / sp) * R2; ectx.strokeStyle = 'rgba(240,244,248,.9)'; ectx.lineWidth = 1; ectx.beginPath(); ectx.moveTo(hx, 4); ectx.lineTo(hx, h - 4); ectx.stroke(); }
    else if (lit && e.t === 'pair') { var ang = p.s / p.D;
      for (i = 0; i < w; i++) { var th = (i / w - 0.5) * 6 * ang, u1 = Math.PI * p.x * (th - ang / 2) / p.lam, u2 = Math.PI * p.x * (th + ang / 2) / p.lam;
        a = (Math.abs(u1) < 1e-9 ? 1 : Math.pow(Math.sin(u1) / u1, 2)) + (Math.abs(u2) < 1e-9 ? 1 : Math.pow(Math.sin(u2) / u2, 2)); ectx.fillStyle = col(Math.pow(Math.min(1, a), 0.7)); ectx.fillRect(i, 8, 1, h - 16); } }
    if (e.t !== 'rings' && e.t !== 'level' && e.t !== 'radial') { ectx.strokeStyle = 'rgba(240,244,248,.9)'; ectx.lineWidth = 1; ectx.beginPath(); ectx.moveTo(w / 2, 2); ectx.lineTo(w / 2, h - 2); ectx.moveTo(w / 2 - 14, h / 2); ectx.lineTo(w / 2 + 14, h / 2); ectx.stroke(); }
  }
  var HC = CTL.map(function (c) { return S.hudCard(c.label.length > 34 ? c.label.slice(0, 32) + '…' : c.label); });
  var HR = READS.map(function (r) { if (C.hideCols && C.hideCols.indexOf(r.key) >= 0) return null; return S.hudCard(r.label.length > 34 ? r.label.slice(0, 32) + '…' : r.label); });
  var meterKey = '';

  function live() { return st.on && st.ready; }
  function shown(r, rd) { return live() ? fmt(rounded(r, rd[r.key]) * r.f, r.digits) + (r.unit ? ' ' + r.unit : '') : '—'; }
  function update() {
    var rd = K.read(p), sg = Math.round(p.stage || 0);
    Object.keys(I).forEach(function (id) { var it = I[id]; if (it.o && it.o.stages) { it.g.visible = it.o.stages.indexOf(sg) >= 0; if (it.sh) it.sh.visible = it.g.visible; } });
    if (C.upd) C.upd(I, rd);
    Object.keys(I).forEach(function (id) { var it = I[id]; if (it.sh && it.g.position) { it.sh.position.x = it.g.position.x; it.sh.position.z = it.g.position.z; if (it.g.visible === false) it.sh.visible = false; } });
    var bs = st.on ? C.beams(I, rd) : [];
    beamLines.forEach(function (l, i) { var b = bs[i]; l.visible = !!b; if (b) l.geometry.setFromPoints(b.map(function (q, j) { var v = pos(q, AXY); if (j === 0 && !Array.isArray(q) && q.out) v.x += q.out; return v; })); });
    Object.keys(I).forEach(function (id) { var it = I[id]; if (it && it.glow) it.glow.material.color.setHex(st.on ? hex() : 0x35311f); });
    CTL.forEach(function (c, i) { HC[i].set(c.key === 'stage' ? stageName(p.stage) : fmt(p[c.key] * c.f, c.digits) + ' ' + c.unit); });
    READS.forEach(function (r, i) { if (HR[i]) HR[i].set(shown(r, rd)); });
    if (I.met && I.met.tex) { var mr = readOf(C.meter || (READS[0] && READS[0].key)), txt = C.meterFn ? (live() ? C.meterFn() : '—') : (mr ? shown(mr, rd) : '—');
      if (txt !== meterKey) { meterKey = txt; I.met.tex.draw(function (x, w, h) { x.fillStyle = '#0d1a12'; x.fillRect(0, 0, w, h); x.fillStyle = '#6dff9a'; x.font = '600 92px "DM Mono", monospace'; x.textAlign = 'right'; x.textBaseline = 'middle'; x.fillText(txt, w - 24, h / 2 + 6); }); } }
    drawEye(rd);
  }

  // ------------------------------------------------------------------------------------------ the human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function meshOf(id) { var it = I[id]; return (it && (it.handle || it.g)) || S.book.group; }
  function switchOn() {
    if (st.on) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    return S.hand.tap(I[C.src].sw || I[C.src].g, 'top').then(function () { st.on = true; update();
      S.say(I[C.src].kind === 'laser' ? 'The laser is on. The beam stays at bench height: never bring your eye down to it.' : 'The source is on.'); S.render(); return true; });
  }
  function makeReady() {
    if (st.ready) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    if (!st.on) { S.say('Switch the source on first.'); return Promise.resolve(false); }
    return S.hand.tap(meshOf(C.readyOn), 'top').then(function () { st.ready = true; update(); S.say('Done. The readings are live now.'); S.render(); return true; });
  }
  function setStage(v) {
    v = Math.round(v);
    if (Math.round(p.stage) === v) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    if (STAGES.indexOf(v) < 0) { S.say('That is not part of this experiment.'); return Promise.resolve(false); }
    return S.hand.tap(meshOf(C.handles.stage), 'top').then(function () { p.stage = v; update(); S.say('Now: ' + stageName(v) + '.'); S.render(); return true; });
  }
  function moveCtl(c, toSI) {
    if (S.hand.busy) return wait();
    if (!isFinite(toSI)) { S.say('That setting is not a number.'); return Promise.resolve(false); }
    var lim = snap(c, toSI), from = p[c.key];
    if (Math.abs(lim * c.f - toSI * c.f) > c.step * 0.6) S.say(c.label + ' goes from ' + fmt(c.min, c.digits) + ' to ' + fmt(c.max, c.digits) + ' ' + c.unit + '. It is set as near as it can go.');
    st.set[c.key] = lim * c.f;
    if (Math.abs(lim - from) * c.f < c.step * 1e-6) return Promise.resolve(true);
    var m = meshOf(C.handles[c.key]);
    function at() { var w = new T.Vector3(); m.getWorldPosition(w); w.y += 0.014; return w; }
    return S.hand.pinchMove(at(), function () { return at(); }, function (k) { p[c.key] = from + (lim - from) * k; update(); },
      { ms: 900, reachMs: 650, hold: 150, mode: 'top' }).then(function () { p[c.key] = lim; update(); S.render(); return true; });
  }
  function applySetting(s) {
    var seq = Promise.resolve(true);
    ['stage', 'A', 'x'].forEach(function (key) {
      if (s[key] === undefined) return;
      seq = seq.then(function (ok) { if (ok === false) return false; if (key === 'stage') return STAGES.length > 1 ? setStage(s.stage) : true; var c = ctl(key); return c ? moveCtl(c, s[key]) : true; });
    });
    return seq;
  }
  function same(row) { return CTL.every(function (c) { return Math.abs((row[c.key] - p[c.key]) * (c.key === 'stage' ? 1 : c.f)) < (c.key === 'stage' ? 0.5 : c.step * 0.5); }); }
  function record() {
    if (!live()) { S.say('Switch the source on and finish setting up first.'); return false; }
    if (S.rows.length >= 15) { S.say('The table is full.'); return false; }
    if (S.rows.some(same)) { S.say('That setting is already in the table. Change a control first.'); return false; }
    var rd = K.read(p), row = {};
    CTL.forEach(function (c) { row[c.key] = p[c.key]; });
    READS.forEach(function (r) { row[r.key] = rounded(r, rd[r.key]); });
    COLS.forEach(function (c) { if (row[c.id] === undefined) row[c.id] = c.knob ? p[c.knob] : rd[c.id]; });
    if (p.stage !== undefined && row.stage === undefined) row.stage = p.stage;
    S.addRow(row);
    S.say('Recorded: ' + COLS.map(function (c) { return c.id === 'stage' ? stageName(row.stage) : fmt(row[c.id] * c.f, c.digits); }).join(', ') + '.');
    return true;
  }
  function nextPlan() {
    for (var i = 0; i < PLAN.length; i++) {
      var s = PLAN[i], q = Object.assign({}, p);
      Object.keys(s).forEach(function (k) { var c = ctl(k); q[k] = c && k !== 'stage' ? snap(c, s[k]) : s[k]; });
      var done = S.rows.some(function (r) { return CTL.every(function (c) { return Math.abs((r[c.key] - q[c.key]) * (c.key === 'stage' ? 1 : c.f)) < (c.key === 'stage' ? 0.5 : c.step * 0.5); }); });
      if (!done) return i;
    }
    return -1;
  }
  function p0() { var q = Object.assign({}, p); return q; }
  var truth = (function () { try { return HK.TEXTBOOK[(S.lab.check && S.lab.check.textbook) || KN](p0()) * RES.f; } catch (e) { return NaN; } })();
  function resultFor(rows) {
    if (rows.length < need()) return null;
    var v = HK.CALCS[(S.lab.table && S.lab.table.calc) || KN].fn(rows, p);
    if (!isFinite(v) || v === 0) return null;
    return { label: RES.label, value: v * RES.f, unit: RES.unit, digits: RES.digits, truth: truth, note: C.formula + '. ' + C.note + '.' };
  }
  function need() { return Math.max(1, PLAN.length); }

  var VIEWS = { wide: [[0.0, 1.0, 1.7], [0.0, 0.1, BZ + 0.05]], work: C.view || [[0.0, 0.55, 0.6], [0.0, 0.1, BZ]], book: [[-0.5, 0.46, 0.56], [-0.5, 0.0, 0.1]] };
  update();

  var graph = null;
  if (C.graph) { var G = C.graph;
    graph = { x: typeof G.x === 'function' ? G.x : function (r) { return r[G.x] * (G.xf || 1); }, y: typeof G.y === 'function' ? G.y : function (r) { return r[G.y] * (G.yf || 1); },
      xlabel: G.xlabel, ylabel: G.ylabel,
      line: function (pts) { if (G.fit !== 'linear' || pts.length < 2) return null; var l = S.fit.linear(pts); if (!l) return null; var m = l.m !== undefined ? l.m : l[0], c = l.c !== undefined ? l.c : (l.b !== undefined ? l.b : l[1]);
        return isFinite(m) && isFinite(c) ? function (x) { return m * x + c; } : null; } }; }

  return {
    camera: { pos: VIEWS.wide[0], look: VIEWS.wide[1] },
    views: VIEWS,
    theory: { principle: S.lab.theory || S.lab.aim, formula: C.formula, formulaNote: C.note, more: (S.lab.steps || []).slice(0, 3), precautions: S.lab.safety || '' },
    book: { title: 'Expt. — ' + C.title, lines: [SAMPLE ? 'Sample: ' + SAMPLE.slice(0, 60) : (S.lab.title || '').slice(0, 60), C.formula, C.note].concat(
      READS.slice(0, 2).map(function (r) { return r.label + (r.lc ? ': read to ' + r.lc + ' ' + r.unit : ''); })),
      columns: COLS.map(function (c) { return { label: c.label, get: function (r) { return c.id === 'stage' ? stageName(r.stage) : fmt(r[c.id] * c.f, c.digits); } }; }),
      at: [-0.62, 0.12, 0.1] },
    graph: graph || undefined,
    result: resultFor,
    tol: C.tol || 0.02,
    chips: ['What am I measuring here?', 'Check my readings', 'Why is this formula right?', 'What is the main source of error?', 'What is the safe way to work here?'],
    viva: [],
    askState: function () {
      var rd = K.read(p), o = { set_up: C.title, source_on: st.on, ready: st.ready, readings_taken: S.rows.length, readings_needed: need() };
      CTL.forEach(function (c) { o[c.label] = c.key === 'stage' ? stageName(p.stage) : fmt(p[c.key] * c.f, c.digits) + ' ' + c.unit; });
      READS.forEach(function (r) { o[r.label] = shown(r, rd); });
      return o;
    },
    steps: [
      { id: 'setup', title: 'Set up the bench', view: 'wide', render: function (u) {
        u.h2('Switch on and line up');
        u.p(S.lab.aim || '');
        u.task('1. Switch the source on', st.on, st.on ? 'The source is on' : 'Press the switch on the source')
          .add(u.button(st.on ? 'Source on' : 'Switch the source on', function () { switchOn(); }, !st.on, st.on || S.hand.busy));
        u.task('2. ' + C.readyText[0], st.ready, st.ready ? 'Done' : 'Needed before any reading means anything')
          .add(u.button(st.ready ? 'Done' : C.readyText[1], function () { makeReady(); }, !st.ready, st.ready || !st.on || S.hand.busy));
        if (S.lab.safety) u.note(S.lab.safety);
        u.next('Next: take the readings', st.on && st.ready);
      },
      ok: function () { return st.on && st.ready; },
      auto: function () { return switchOn().then(makeReady); } },

      { id: 'measure', title: 'Take the readings', view: 'work', render: function (u) {
        u.h2('Set the control, read the detector, record');
        (S.lab.steps || []).slice(2).forEach(function (t) { u.p(t); });
        if (STAGES.length > 1) { u.h3('On the bench');
          u.row.apply(u, STAGES.map(function (v) { return u.button(stageName(v), function () { setStage(v).then(function () { S.render(); }); }, Math.round(p.stage) === v, S.hand.busy); })); }
        CTL.forEach(function (c) { if (c.key === 'stage') return;
          u.slider(c.label, c.min, c.max, c.step, function () { return st.set[c.key]; }, function (x) { st.set[c.key] = x; }, c.unit, c.digits);
          u.row(u.button('Set it', function () { moveCtl(c, st.set[c.key] / c.f).then(function () { S.render(); }); }, false, S.hand.busy)); });
        var ni = nextPlan();
        u.live(function () { var rd = K.read(p); return READS.map(function (r) { return r.label + ': ' + shown(r, rd); }).join(' · '); });
        u.row(u.button(ni < 0 ? 'All the readings are taken' : 'Go to: ' + planName(ni), function () { var i = nextPlan(); if (i < 0) { S.say('Every reading of the procedure is in the table.'); return; }
          applySetting(PLAN[i]).then(function () { S.render(); }); }, false, S.hand.busy || ni < 0),
          u.button('Record this reading', function () { record(); S.render(); }, true, S.hand.busy));
        u.h3('Observation table'); u.table();
        u.next('Next: result', S.rows.length >= need());
        if (S.rows.length < need()) u.p(S.rows.length + ' of ' + need() + ' readings recorded.');
      },
      ok: function () { return S.rows.length >= need(); },
      auto: function () {
        var seq = Promise.resolve();
        PLAN.forEach(function (s) { seq = seq.then(function () { return applySetting(s); }).then(function () { record(); }); });
        return seq;
      } }
    ],
    tick: function () { update(); }
  };
});
