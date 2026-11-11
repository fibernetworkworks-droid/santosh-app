/* Prayogshala studio module: THE APPLIED-OPTICS BREADBOARD. One rig for seventeen B.Sc. / B.Tech set-ups - critical
   emergence from a prism, Wollaston's air film, the nodal slide, Fresnel's biprism, fringe counting on a Michelson
   (wavelength, index of air, expansion of quartz), the Fabry-Perot, Fourier-transform spectroscopy, the lycopodium
   corona, the resolving power of a telescope, Malus's law, the Babinet compensator, four fibre measurements (near
   field, bend loss, splice loss, mode field diameter) and the light-current curve of a laser diode.
   Every one of them is "set the control, read the detector, write it down". The apparatus stands on posts on a black
   optical breadboard; the gloved hand switches the source on, turns the micrometer, the analyser or the divided
   table, and swaps what is on the bench. Nothing is typed into this page: the detector readings are the kernel's
   read(), the settings the walk-through records are the kernel's own plan(), and the table is reduced by the kernel's
   own calc - the same three functions the server's check runs. */
HoolaStudio.define('w7-optics-bench', function (S) {
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
  function lamOf() { return p.lam || p.lam0 || 5.893e-7; }
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
  };

  // ------------------------------------------------------------------------------------------ the set-ups
  function cfgTir() {
    var liquid = MODE === 1;
    return {
      title: 'Critical emergence', formula: liquid ? 'n_l = sin A √(n² − sin² e) − cos A sin e' : 'n² = 1 + ((sin e + cos A) / sin A)²',
      note: 'e = edge reading − normal reading, A = 60° (the prism angle)' + (liquid ? ', n = ' + fmt(p.n, 5) + ' (the prism)' : ''),
      items: [['lamp', 'src', -0.62, BZ - 0.1, { ry: 0.32, name: 'Sodium lamp and ground glass', info: 'A broad yellow source, so light meets the face at every angle up to grazing.' }],
        ['plate', 'gg', -0.45, BZ - 0.045, { ry: 0.32, name: 'Ground-glass screen', info: 'Scatters the lamp light so some of it grazes the prism face.' }],
        ['table', 'tab', -0.05, BZ, { on: 'prism', name: liquid ? 'Prism with the liquid film on one face' : 'Prism on the spectrometer table', info: liquid ? SAMPLE || 'A film of the liquid held on the first face.' : 'A 60° prism. Its refractive index is what you have to find.' }],
        ['scope', 'tel', -0.05, BZ, { gauss: true, name: 'Telescope with a Gaussian eyepiece', info: 'Swings round the divided circle, read to 1 minute of arc. The side lamp lights the cross-wire for the normal setting.' }]],
      handles: { x: 'tel' }, src: 'src', readyOn: 'tel', readyText: ['Focus the telescope for parallel light', 'Focus the telescope'],
      upd: function (I) { I.tel.g.rotation.y = -(p.x - 35 * DEG) + 0.55; },
      beams: function (I) { return [[I.src, [-0.05, BZ]]]; },
      eye: { title: 'In the telescope', t: 'half' },
      plan: ['the edge of the bright field', 'the normal to the face (Gaussian eyepiece)'],
      res: [{ label: 'refractive index of the glass', unit: '', f: 1, digits: 4 }, { label: 'refractive index of the liquid', unit: '', f: 1, digits: 4 }],
      graph: null, view: [[0.05, 0.55, 0.5], [-0.05, 0.1, BZ]]
    };
  }
  function cfgWollaston() {
    return {
      title: 'Wollaston\'s air film', formula: 'n = 1 / sin C,   2C = angle between the two cut-offs', note: 'C = critical angle of the liquid against air',
      items: [['lamp', 'src', -0.7, BZ, { name: 'Sodium lamp', info: 'The source of yellow light.' }],
        ['lens', 'col', -0.48, BZ, { name: 'Collimating lens', info: 'Makes the light parallel before it enters the cell.' }],
        ['table', 'tab', -0.05, BZ, { on: 'cell', name: 'Cell of liquid with the air-film plate', info: (SAMPLE || 'The liquid') + '. The plate with the sealed air film turns with the divided table.' }],
        ['scope', 'tel', 0.18, BZ, { R: 0.1, name: 'Telescope', info: 'Shows the field going dark at each cut-off.' }]],
      handles: { x: 'tab' }, src: 'src', readyOn: 'tel', readyText: ['Focus the telescope on the slit of light', 'Focus the telescope'],
      upd: function (I) { I.tab.rot.rotation.y = p.x - p.x0; },
      beams: function (I, rd) { return rd.T > 0 ? [[I.src, [0.28, BZ]]] : [[I.src, [-0.05, BZ]]]; },
      eye: { title: 'In the telescope', t: 'level', key: 'T' },
      plan: ['the cut-off on one side', 'the cut-off on the other side'],
      res: [{ label: 'refractive index', unit: '', f: 1, digits: 4 }], view: [[0.0, 0.5, 0.45], [-0.05, 0.1, BZ]]
    };
  }
  function cfgNodal() {
    return {
      title: 'Nodal slide', formula: 'F = f₁ f₂ / (f₁ + f₂ − d)', note: 'd = ' + fmt(p.d * 100, 1) + ' cm between the lenses; the principal point lies F d / f₁ in front of the rear lens',
      items: [['lamp', 'src', -0.75, BZ, { text: 'LAMP', name: 'Lamp and cross-slit', info: 'The lit cross-slit is the object.' }],
        ['slit', 'obj', -0.62, BZ, { name: 'Cross-slit', info: 'At the focus of the collimating lens.' }],
        ['lens', 'col', -0.42, BZ, { name: 'Collimating lens', info: 'Sends parallel light on, as from a distant object.' }],
        ['nodal', 'nod', -0.05, BZ, { name: 'Two lenses on the nodal slide', info: 'The carriage slides the lens pair over a vertical axis (the red pin); the slide turns about that axis.' }],
        ['screen', 'scr', 0.3, BZ, { name: 'Screen', info: 'The image of the cross-slit is focused here.' }]],
      handles: { x: 'nod', stage: 'nod' }, src: 'src', readyOn: 'scr', readyText: ['Focus the image of the cross-slit on the screen', 'Focus the image'],
      stages: ['as set', 'turned end for end'],
      upd: function (I) { I.nod.pair.position.x = 0.02 - p.x; I.nod.pair.rotation.y = p.stage > 0.5 ? Math.PI : 0; I.scr.cursor.visible = false; },
      beams: function (I) { return [[I.src, I.scr]]; },
      plan: ['the image stays still (as set)', 'the image stays still (turned end for end)'],
      res: [{ label: 'equivalent focal length', unit: 'cm', f: 100, digits: 2 }, { label: 'principal point in front of the rear lens', unit: 'mm', f: 1000, digits: 1 }],
      view: [[0.05, 0.5, 0.5], [0.05, 0.1, BZ]]
    };
  }
  function cfgBiprism() {
    var mica = MODE === 1;
    return {
      title: 'Fresnel\'s biprism', formula: mica ? 't = S λ / (β (μ − 1))' : 'λ = β d / D,   d = √(d₁ d₂)',
      note: mica ? 'S = shift of the central fringe, λ = ' + fmt(p.lam * 1e9, 1) + ' nm, μ = ' + fmt(p.mu, 2) : 'D = ' + fmt(p.D * 100, 0) + ' cm from the slit to the eyepiece',
      items: [['lamp', 'src', -0.82, BZ, { name: 'Sodium lamp', info: 'The source of yellow light.' }],
        ['slit', 'slit', -0.68, BZ, { name: 'Narrow slit', info: 'Parallel to the edge of the biprism.' }],
        ['biprism', 'bp', -0.55, BZ, { name: 'Biprism', info: 'Two thin prisms base to base: it makes two virtual images of the slit.' }],
        ['plate', 'mica', -0.53, BZ - 0.014, { stages: [3], text: 'MICA', name: 'Mica sheet', info: 'Covers one half of the biprism.' }],
        ['lens', 'lens', -0.25, BZ, { stages: [1, 2], name: 'Convex lens', info: 'At its two conjugate positions it images the two virtual slits in the eyepiece.' }],
        ['eyepiece', 'eye', 0.32, BZ, { name: 'Micrometer eyepiece', info: 'A cross-wire moved across the field by a micrometer screw, read to 0.01 mm.' }]],
      handles: { x: 'eye', stage: 'bp' }, src: 'src', readyOn: 'bp', readyText: ['Turn the biprism until the fringes are sharp', 'Sharpen the fringes'],
      stages: ['fringes', 'lens, magnified images', 'lens, diminished images', 'fringes with the mica in'],
      upd: function (I) { I.lens.g.position.x = p.stage > 1.5 ? 0.05 : -0.25; },
      beams: function (I) { return [[I.src, I.eye]]; },
      eye: { title: 'In the eyepiece', t: 'strip', key: 'I', span: function () { return p.stage > 0.5 && p.stage < 2.5 ? 1.6e-3 : 2.2e-3; } },
      plan: mica ? ['the 10th bright fringe on one side', 'the 10th bright fringe on the other side', 'the central fringe with the mica in']
        : ['the 10th bright fringe on one side', 'the 10th bright fringe on the other side', 'one slit image (lens near the biprism)', 'the other slit image',
          'one slit image (lens near the eyepiece)', 'the other slit image'],
      res: [{ label: 'wavelength', unit: 'nm', f: 1e9, digits: 1 }, { label: 'thickness of the mica', unit: 'µm', f: 1e6, digits: 2 }],
      view: [[-0.1, 0.5, 0.75], [-0.15, 0.1, BZ]], tol: 0.03
    };
  }
  function cfgFringes() {
    var per = K.per(p), plan = K.plan(p), top = plan.length ? plan[plan.length - 1].x : 1;
    var X = MODE === 0 ? { label: 'Mirror micrometer', unit: 'µm', f: 1e6, min: 0, max: Math.ceil(top * 1.15e6), step: 0.1, digits: 1 }
      : MODE === 1 ? { label: 'Pressure in the cell', unit: 'kPa', f: 1e-3, min: 0, max: 101, step: 0.5, digits: 1 }
        : { label: 'Temperature of the rod', unit: '°C', f: 1, min: p.T0, max: Math.ceil(top + 8), step: 0.1, digits: 1 };
    var items = [[isSodium() ? 'lamp' : 'laser', 'src', -0.62, BZ, { name: isSodium() ? 'Sodium lamp with a ground glass' : 'He-Ne laser', info: 'The light source. ' + (SAMPLE || '') }],
      ['bs', 'bs', -0.1, BZ, { name: 'Beam splitter', info: 'Sends half the light to each mirror and recombines the returning beams.' }],
      ['mirror', 'm2', -0.1, BZ - 0.3, { ry: Math.PI / 2, name: 'Fixed mirror', info: 'Its two screws tilt it to centre the fringes.' }],
      ['detector', 'det', -0.1, BZ + 0.22, { ry: -Math.PI / 2, name: 'Photodetector', info: 'Sits at the centre of the fringe pattern.' }],
      ['meter', 'met', 0.42, -0.02, { text: 'FRINGE COUNTER', name: 'Fringe counter', info: 'Counts the fringes that cross the detector.' }]];
    if (MODE === 2) items.push(['furnace', 'm1', 0.36, BZ, { name: 'Quartz rod in a tube furnace', info: (SAMPLE || 'A quartz rod') + ', ' + fmt(p.L0 * 100, 0) + ' cm long. The mirror is on its free end.' }],
      ['source', 'ctl', 0.72, BZ, { text: 'HEATER', name: 'Heater control and thermometer', info: 'Raises the temperature of the furnace slowly.' }]);
    else items.push(['mirror', 'm1', 0.32, BZ, { mic: MODE === 0, name: 'Movable mirror', info: MODE === 0 ? 'Moved along the beam by a fine micrometer screw through a 10 : 1 lever.' : 'The end mirror of the arm that holds the cell.' }]);
    if (MODE === 1) items.push(['cellarm', 'cell', 0.1, BZ, { name: 'Air cell', info: 'A cell ' + fmt(p.L * 100, 0) + ' cm long with flat windows, pumped out and then filled slowly.' }],
      ['pump', 'ctl', 0.42, BZ + 0.14, { name: 'Hand pump and gauge', info: 'Lets air into the cell; the gauge reads the pressure.' }]);
    return {
      title: MODE === 2 ? 'Expansion of quartz' : 'Michelson interferometer',
      formula: MODE === 0 ? 'λ = 2 Δx / N' : MODE === 1 ? 'n − 1 = N λ P₀ / (2 L P)' : 'α = N λ / (2 L₀ ΔT)',
      note: MODE === 0 ? 'N fringes pass while the mirror moves Δx' : MODE === 1 ? 'L = ' + fmt(p.L * 100, 0) + ' cm, λ = ' + fmt(p.lam * 1e9, 1) + ' nm, P₀ = 101.3 kPa'
        : 'L₀ = ' + fmt(p.L0 * 100, 0) + ' cm, λ = ' + fmt(p.lam * 1e9, 1) + ' nm',
      items: items, x: X, handles: { x: MODE === 0 ? 'm1' : 'ctl' }, src: 'src', readyOn: 'm2', readyText: ['Tilt the fixed mirror until the fringes are centred', 'Centre the fringes'],
      upd: function (I) { if (I.ctl && I.ctl.gtex) gauge(I.ctl.gtex, p.x / 1000); },
      beams: function (I) { return [[I.src, I.bs, MODE === 2 ? [0.225, BZ] : I.m1], [I.bs, I.m2], [I.bs, I.det]]; },
      eye: { title: 'The fringes', t: 'rings', key: 'N' }, meter: 'N',
      plan: function (i) { return i === 0 ? 'the start (counter at zero)' : 'after ' + Math.round(per * (plan[i].x - plan[0].x)) + ' fringes'; },
      cols: { x: { label: X.label + ' (' + X.unit + ')', f: X.f, digits: X.digits } },
      res: [{ label: 'wavelength', unit: 'nm', f: 1e9, digits: 1 }, { label: 'n − 1 of air at one atmosphere', unit: '× 10⁻⁴', f: 1e4, digits: 3 },
        { label: 'coefficient of linear expansion', unit: '× 10⁻⁶ /K', f: 1e6, digits: 3 }],
      graph: { x: 'x', y: 'N', xf: X.f, yf: 1, xlabel: X.label + ' (' + X.unit + ')', ylabel: 'fringes N', fit: 'linear' },
      view: [[0.1, 0.75, 0.55], [0.1, 0.08, BZ]], tol: 0.02
    };
  }
  function cfgFabry() {
    var fin = MODE === 1;
    return {
      title: 'Fabry-Perot', formula: fin ? 'finesse = (spacing of maxima) / (width at half height) = π√R / (1 − R)' : 'λ = 2 Δx / N',
      note: fin ? 'scan the fine travel across two neighbouring maxima' : 'N rings collapse while the plate moves Δx',
      items: [['laser', 'src', -0.7, BZ, { name: 'Laser', info: 'The light source.' }],
        ['lens', 'l1', -0.45, BZ, { name: 'Beam-expanding lens', info: 'Fills the plates with light.' }],
        ['etalon', 'et', -0.12, BZ, { name: 'Fabry-Perot plates', info: 'Two partly silvered plates. One moves on a coarse screw and a fine piezo.' }],
        ['lens', 'l2', 0.12, BZ, { name: 'Focusing lens', info: 'Brings the rings to a focus on the detector.' }],
        ['detector', 'det', 0.36, BZ, { name: 'Photodetector', info: 'At the centre of the ring pattern.' }],
        ['meter', 'met', 0.45, -0.02, { text: fin ? 'PHOTOMETER' : 'RING COUNTER', name: fin ? 'Photometer' : 'Ring counter', info: 'Shows the detector reading.' }]],
      x: fin ? { label: 'Fine (piezo) travel', unit: 'nm', f: 1e9, min: -30, max: Math.ceil(p.lam * 1e9 / 2 + 30), step: 0.05, digits: 2 }
        : { label: 'Plate screw', unit: 'µm', f: 1e6, min: 0, max: Math.ceil(p.lam * 115e6), step: 0.1, digits: 1 },
      handles: { x: 'et' }, src: 'src', readyOn: 'et', readyText: ['Set the two plates parallel', 'Set the plates parallel'],
      beams: function (I) { return [[I.src, I.det]]; },
      eye: { title: 'The rings', t: 'rings', key: 'N', sharp: true }, meter: fin ? 'I' : 'N',
      plan: fin ? ['half height, rising side of the first maximum', 'half height, falling side', 'half height, rising side of the next maximum', 'half height, falling side']
        : function (i) { return i === 0 ? 'the start (counter at zero)' : 'after ' + 25 * i + ' rings'; },
      cols: fin ? { x: { label: 'Fine travel (nm)', f: 1e9, digits: 2 } } : { x: { label: 'Plate screw (µm)', f: 1e6, digits: 1 } },
      res: [{ label: 'wavelength', unit: 'nm', f: 1e9, digits: 1 }, { label: 'finesse', unit: '', f: 1, digits: 1 }],
      graph: fin ? null : { x: 'x', y: 'N', xf: 1e6, yf: 1, xlabel: 'plate travel (µm)', ylabel: 'rings N', fit: 'linear' },
      view: [[-0.15, 0.5, 0.6], [-0.15, 0.1, BZ]]
    };
  }
  function cfgFts() {
    var comp = MODE === 1;
    return {
      title: 'Fourier transform spectroscopy', formula: 'V(x) = exp(−2π² s² x²),   Δλ = 2.355 s λ₀²',
      note: comp ? 'SIMULATED DATA: the computer samples the interferogram and takes its Fourier cosine transform' : 'x = path difference, s = spread of the band in wavenumber',
      items: [['lamp', 'src', -0.7, BZ, { text: 'WHITE LAMP', name: 'White lamp', info: 'A filament lamp: every colour at once.' }],
        ['plate', 'fil', -0.52, BZ, { color: lamOf() > 6e-7 ? 0xd04030 : 0x40b060, text: 'FILTER', name: 'Interference filter', info: (SAMPLE || 'An interference filter') + '. Its pass band is what you have to find.' }],
        ['bs', 'bs', -0.2, BZ, { name: 'Beam splitter', info: 'Splits and recombines the light.' }],
        ['mirror', 'm2', -0.2, BZ - 0.3, { ry: Math.PI / 2, name: 'Fixed mirror', info: 'The reference arm.' }],
        ['mirror', 'm1', 0.15, BZ, { mic: true, name: 'Movable mirror', info: 'Changes the path difference; read to 0.01 µm of path through a lever.' }],
        ['detector', 'det', -0.2, BZ + 0.2, { ry: -Math.PI / 2, name: 'Photodetector', info: 'Records the interferogram.' }],
        ['pc', 'pc', 0.55, BZ + 0.05, { ry: -0.35, name: 'Computer', info: comp ? 'Samples the interferogram and shows its Fourier transform: the band of the filter.' : 'Logs the detector signal.' }]],
      x: comp ? { label: 'Wavelength cursor', unit: 'nm', f: 1e9, min: Math.round((p.lam0 - 2.5 * p.fwhm) * 1e9), max: Math.round((p.lam0 + 2.5 * p.fwhm) * 1e9), step: 0.01, digits: 2 }
        : { label: 'Path difference', unit: 'µm', f: 1e6, min: 0, max: 40, step: 0.01, digits: 2 },
      handles: { x: comp ? 'pc' : 'm1', stage: 'pc' }, src: 'src', readyOn: 'm2', readyText: ['Find the white-light fringes at zero path difference', 'Find zero path difference'],
      stages: ['the interferometer', 'the computer'],
      upd: function (I) { spectrum(I.pc.stex); },
      beams: function (I) { return [[I.src, I.bs, I.m1], [I.bs, I.m2], [I.bs, I.det]]; },
      eye: comp ? null : { title: 'Detector signal near here', t: 'strip', key: 'I', span: function () { return 1.5e-6; } }, meter: comp ? 'T' : 'V',
      plan: comp ? ['half height on the short-wavelength side', 'half height on the long-wavelength side']
        : function (i) { return i === 0 ? 'zero path difference' : 'after ' + 5 * i + ' fringes'; },
      cols: comp ? { x: { label: 'Wavelength (nm)', f: 1e9, digits: 2 } } : { x: { label: 'Path difference (µm)', f: 1e6, digits: 2 } },
      res: [{ label: 'width of the pass band (FWHM)', unit: 'nm', f: 1e9, digits: 2 }, { label: 'width of the pass band (FWHM)', unit: 'nm', f: 1e9, digits: 2 }],
      graph: comp ? null : { x: function (r) { return r.x * r.x * 1e12; }, y: function (r) { return r.V > 0 ? Math.log(r.V) : 0; }, xlabel: 'x² (µm²)', ylabel: 'ln V', fit: 'linear' },
      view: [[0.1, 0.75, 0.6], [0.1, 0.08, BZ]], tol: 0.03
    };
  }
  function cfgCorona() {
    return {
      title: 'Lycopodium corona', formula: 'sin θ₁ = 1.220 λ / d,   sin θ₂ = 2.233 λ / d', note: 'tan θ = r / D with D = ' + fmt(p.D * 100, 0) + ' cm, λ = ' + fmt(p.lam * 1e9, 1) + ' nm',
      items: [['laser', 'src', -0.78, BZ, { name: 'Laser', info: 'A low-power laser clamped at bench height.' }],
        ['plate', 'pl', -0.55, BZ, { name: 'Glass plate dusted with lycopodium powder', info: 'The spores are nearly equal spheres; their size is what you have to find.' }],
        ['screen', 'scr', -0.55 + p.D, BZ, { name: 'Screen with a scale and cursor', info: 'The corona falls on it; the cursor is read to 0.1 mm on its vernier.' }]],
      handles: { x: 'scr' }, src: 'src', readyOn: 'pl', readyText: ['Centre the beam on the dusted plate', 'Centre the beam'],
      upd: function (I, rd) { I.scr.cursor.position.z = -p.x; pattern(I.scr.ptex, 0.16); },
      beams: function (I) { return [[I.src, I.scr]]; },
      eye: { title: 'On the screen', t: 'strip', key: 'I', span: function () { return 0.012; }, gamma: 0.3 },
      plan: ['the first dark ring', 'the second dark ring'],
      res: [{ label: 'particle diameter', unit: 'µm', f: 1e6, digits: 2 }], view: [[0.2, 0.45, 0.45], [0.35, 0.12, BZ]]
    };
  }
  function cfgResolve() {
    return {
      title: 'Resolving power', formula: 'least angle = λ / a,   resolving power = a / λ', note: 'two slits ' + fmt(p.D, 1) + ' m away; at Rayleigh\'s limit the brightness midway is 81 %',
      items: [['lamp', 'src', -0.82, BZ, { name: 'Sodium lamp', info: 'Lights the pair of object slits.' }],
        ['slit', 'obj', -0.68, BZ, { two: true, name: 'Pair of fine slits', info: 'Two close line sources. In the laboratory they stand ' + fmt(p.D, 1) + ' m from the telescope; the bench here is drawn shorter.' }],
        ['slit', 'ap', 0.2, BZ, { mic: true, name: 'Adjustable slit over the objective', info: 'Sets the aperture of the telescope; its micrometer reads the width to 0.01 mm.' }],
        ['scope', 'tel', 0.14, BZ, { R: 0.16, name: 'Telescope', info: 'Shows the two images merging as the aperture is narrowed.' }]],
      handles: { x: 'ap' }, src: 'src', readyOn: 'tel', readyText: ['Focus the telescope on the two slits', 'Focus the telescope'],
      beams: function (I) { return [[I.src, [0.3, BZ]]]; },
      eye: { title: 'In the telescope', t: 'pair' },
      plan: ['Rayleigh\'s limit (midway brightness 81 %)'],
      res: [{ label: 'resolving power a / λ', unit: '', f: 1, digits: 0 }], view: [[0.0, 0.5, 0.7], [-0.1, 0.1, BZ]]
    };
  }
  function cfgMalus() {
    var lampV = /lamp/i.test(SAMPLE), diode = /diode/i.test(SAMPLE);
    var items = lampV ? [['lamp', 'src', -0.7, BZ, { text: 'LAMP', name: 'Filament lamp', info: 'Unpolarised light.' }],
      ['polar', 'pol', -0.45, BZ, { text: 'POLARISER', name: 'Polariser', info: 'Its axis sets the plane of polarisation; the setting is what you have to find.' }]]
      : [['laser', 'src', -0.6, BZ, { name: diode ? 'Laser diode module' : 'Polarised He-Ne laser', info: 'Its light is already plane-polarised; the direction is what you have to find.' }]];
    items.push(['polar', 'ana', -0.1, BZ, { name: 'Analyser', info: 'A polaroid in a rotary mount divided in degrees.' }],
      ['detector', 'det', 0.2, BZ, { name: 'Photodiode', info: 'Its current is proportional to the light that gets through.' }],
      ['meter', 'met', 0.42, -0.02, { text: 'MICROAMMETER', name: 'Digital microammeter', info: 'Reads the photocurrent to 0.01 µA.' }]);
    return {
      title: 'Malus\'s law', formula: 'I = I₀ cos²(θ − θ₀)', note: 'θ = analyser reading, θ₀ = direction of polarisation',
      items: items, handles: { x: 'ana' }, src: 'src', readyOn: 'det', readyText: ['Centre the beam on the photodiode', 'Centre the beam'],
      upd: function (I) { I.ana.rot.rotation.x = p.x; if (I.pol) I.pol.rot.rotation.x = p.th0; },
      beams: function (I) { return [[I.src, I.det]]; }, meter: 'I',
      plan: MODE === 2 ? ['the greatest photocurrent', 'the least photocurrent (analyser crossed)'] : function (i) { return 'analyser at ' + 20 * i + '°'; },
      res: [{ label: 'direction of polarisation θ₀', unit: '°', f: 180 / Math.PI, digits: 1 }, { label: 'power of the cosine', unit: '', f: 1, digits: 3 },
        { label: 'extinction ratio Imax / Imin', unit: '', f: 1, digits: 0 }],
      graph: { x: function (r) { return r.x / DEG; }, y: function (r) { return r.I * 1e6; }, xlabel: 'analyser (°)', ylabel: 'photocurrent (µA)', fit: null },
      view: [[-0.15, 0.5, 0.6], [-0.15, 0.1, BZ]], tol: 0.02
    };
  }
  function cfgBabinet() {
    return {
      title: 'Babinet compensator', formula: 'δ = 2π (fringe shift) / β,   sin 2χ = sin 2ψ sin δ,   tan 2α = tan 2ψ cos δ',
      note: 'β = micrometer travel between dark fringes; the fringe is black with the analyser at 90° + ψ',
      items: [['lamp', 'src', -0.78, BZ, { name: 'Sodium lamp', info: 'The source of yellow light.' }],
        ['polar', 'pol', -0.55, BZ, { text: 'POLARISER', name: 'Polariser', info: 'Set at 45° to the axes of the compensator.' }],
        ['plate', 'qwp', -0.38, BZ, { stages: [1], text: 'λ/4 PLATE', name: 'Quarter-wave plate', info: 'Turns the plane-polarised light into the elliptical light under test.' }],
        ['comp', 'cmp', -0.15, BZ, { name: 'Babinet compensator', info: 'Two quartz wedges with crossed axes; the micrometer slides one over the other and is read to 0.005 mm.' }],
        ['polar', 'ana', 0.1, BZ, { name: 'Analyser', info: 'Turns in a circle divided to 0.1°.' }],
        ['eyepiece', 'eye', 0.32, BZ, { name: 'Eyepiece with a cross-wire', info: 'The dark fringe is set on the cross-wire.' }]],
      handles: { x: 'cmp', A: 'ana', stage: 'qwp' }, src: 'src', readyOn: 'eye', readyText: ['Focus the eyepiece on the fringes', 'Focus the eyepiece'],
      stages: ['plane-polarised (calibration)', 'the light under test'],
      upd: function (I) { I.ana.rot.rotation.x = p.A; I.pol.rot.rotation.x = Math.PI / 4; I.cmp.wedge.position.z = 0.004 + p.x * 2; },
      beams: function (I) { return [[I.src, I.eye]]; },
      eye: { title: 'In the eyepiece', t: 'strip', key: 'I', span: function () { return p.beta * 1.2; } },
      plan: ['a dark fringe (calibration)', 'the next dark fringe (calibration)', 'the dark fringe of the light under test', 'the analyser turned until that fringe is black'],
      res: [{ label: 'ratio of the axes of the ellipse', unit: '', f: 1, digits: 3 }, { label: 'tilt of the major axis', unit: '°', f: 180 / Math.PI, digits: 2 },
        { label: 'phase difference δ', unit: '°', f: 180 / Math.PI, digits: 1 }],
      view: [[-0.2, 0.5, 0.6], [-0.2, 0.1, BZ]], tol: 0.02
    };
  }
  function fibreItems(extra, srcText) {
    return [['source', 'src', -0.78, BZ, { text: srcText, name: srcText === 'LED SOURCE' ? 'LED source' : 'Laser source', info: 'Launches light into the near end of the fibre.' }]].concat(extra);
  }
  function cfgNear() {
    return {
      title: 'Near field of a fibre', formula: 'I(r) / I(0) = 1 − (r / a)^g', note: 'r = x / ' + fmt(p.M, 0) + ' (the magnification), a = ' + fmt(p.a * 1e6, 1) + ' µm (core radius)',
      items: fibreItems([['chuck', 'ch', -0.2, BZ, { name: 'Fibre end in a chuck', info: 'The cleaved end face of the multimode fibre.' }],
        ['objective', 'obj', -0.12, BZ, { name: 'Microscope objective', info: 'Images the end face ' + fmt(p.M, 0) + ' times larger in the detector plane.' }],
        ['detector', 'det', 0.3, BZ, { stage: true, name: 'Pinhole detector on a translation stage', info: 'Scans across the magnified image; the stage is read to 0.1 mm.' }],
        ['meter', 'met', 0.45, -0.02, { name: 'Optical power meter', info: 'Reads the power on the detector in nanowatts.' }]], 'LED SOURCE'),
      fibre: [['src', 'ch', 1]], handles: { x: 'det' }, src: 'src', readyOn: 'obj', readyText: ['Focus the end face on the detector plane', 'Focus the image'],
      upd: function (I) { I.det.g.position.z = BZ + p.x * 3; },
      beams: function (I) { return [[I.ch, [0.3, BZ]]]; }, meter: 'P',
      plan: function (i) { return i === 0 ? 'the centre of the core' : fmt([0, 0.3, 0.45, 0.6, 0.75, 0.9][i], 2) + ' of the core radius'; },
      res: [{ label: 'profile exponent g', unit: '', f: 1, digits: 2 }],
      graph: { x: function (r) { return r.x * 1000; }, y: function (r) { return r.P * 1e9; }, xlabel: 'detector position (mm)', ylabel: 'power (nW)', fit: null },
      view: [[0.0, 0.5, 0.6], [0.0, 0.1, BZ]]
    };
  }
  function cfgBend() {
    return {
      title: 'Bending loss', formula: 'guided fraction = 1 − [2a / R + (3 / (2 n₂ k R))^⅔] / (2Δ)', note: 'a = ' + fmt(p.a * 1e6, 0) + ' µm, n₂ = ' + fmt(p.n2, 2) + ', λ = ' + fmt(p.lam * 1e9, 0) + ' nm (Gloge)',
      items: fibreItems([['mandrel', 'man', -0.15, BZ - 0.02, { name: 'Mandrel', info: 'One full turn of the fibre is wound on it. A set of mandrels gives the different radii.' }],
        ['detector', 'det', 0.3, BZ, { name: 'Power-meter head', info: 'The far end of the fibre is plugged into it.' }],
        ['meter', 'met', 0.45, -0.02, { name: 'Optical power meter', info: 'Reads the power out of the fibre to 0.01 µW.' }]], 'LASER SOURCE 850 nm'),
      fibre: [['src', 'det', 0]], handles: { x: 'man', stage: 'man' }, src: 'src', readyOn: 'det', readyText: ['Plug the far end into the power-meter head', 'Plug in the fibre'],
      stages: ['laid straight', 'one turn on the mandrel'],
      upd: function (I) { var R = Math.max(p.x, 0.004), m = I.man; m.drum.scale.set(R, 1, R); m.g.visible = p.stage > 0.5;
        if (Math.abs(m.R - R) > 1e-5) { m.R = R; m.loop.geometry.dispose(); m.loop.geometry = new T.TorusGeometry(R + 0.0016, 0.0016, 8, 48); } },
      beams: function () { return []; }, meter: 'P',
      plan: function (i, s) { return s.stage < 0.5 ? 'the fibre laid straight (reference)' : 'one turn on the ' + fmt(s.x * 1000, 0) + ' mm mandrel'; },
      res: [{ label: 'relative index difference Δ', unit: '%', f: 100, digits: 3 }],
      graph: { x: function (r) { return r.x * 1000; }, y: function (r) { var ref = S.rows.filter(function (q) { return q.stage < 0.5; })[0]; return r.stage > 0.5 && ref && r.P > 0 ? 10 * Math.log(ref.P / r.P) / Math.LN10 : 0; },
        xlabel: 'bend radius (mm)', ylabel: 'loss (dB)', fit: null },
      view: [[-0.1, 0.5, 0.6], [-0.1, 0.1, BZ]]
    };
  }
  function cfgSplice() {
    return {
      title: 'Splice loss', formula: 'loss = 10 log₁₀(P_ref / P_splice)   (η = (2/π)[acos u − u√(1 − u²)], u = d / 2a)', note: 'a = ' + fmt(p.a * 1e6, 0) + ' µm; d = sideways offset of the two cores',
      items: fibreItems([['vgroove', 'spl', -0.15, BZ, { stages: [1], name: 'Mechanical splice', info: 'Two cleaved ends butted in a V-groove with index-matching gel. The offset between the cores is unknown.' }],
        ['detector', 'det', 0.3, BZ, { name: 'Power-meter head', info: 'The far end of the fibre is plugged into it.' }],
        ['meter', 'met', 0.45, -0.02, { name: 'Optical power meter', info: 'Reads the power out of the fibre to 0.01 µW.' }]], 'LASER SOURCE 850 nm'),
      fibre: [['src', 'det', 1]], handles: { stage: 'spl' }, src: 'src', readyOn: 'det', readyText: ['Plug the far end into the power-meter head', 'Plug in the fibre'],
      stages: ['unbroken reference fibre', 'fibre with the splice'],
      beams: function () { return []; }, meter: 'P',
      plan: ['the unbroken reference fibre', 'the fibre with the splice in it'],
      res: [{ label: 'splice loss', unit: 'dB', f: 1, digits: 3 }], view: [[-0.1, 0.5, 0.6], [-0.1, 0.1, BZ]]
    };
  }
  function cfgMfd() {
    return {
      title: 'Mode field diameter', formula: 'P(θ) = P₀ exp(−2θ² / θ₀²),   MFD = 2λ / (π θ₀)', note: 'λ = ' + fmt(p.lam * 1e9, 0) + ' nm; θ in radians',
      items: fibreItems([['chuck', 'ch', -0.1, BZ, { name: 'Fibre end at the pivot', info: 'The cleaved end of the single-mode fibre, at the centre of the goniometer.' }],
        ['detector', 'det', -0.1, BZ, { name: 'Detector on the goniometer arm', info: 'Swings round the fibre end; the arm is read to 0.1°.' }],
        ['meter', 'met', 0.45, -0.02, { name: 'Optical power meter', info: 'Reads the power on the detector to 0.1 nW.' }]], 'LASER SOURCE 1310 nm'),
      fibre: [['src', 'ch', 1]], handles: { x: 'det' }, src: 'src', readyOn: 'ch', readyText: ['Strip the cladding modes and clamp the end at the pivot', 'Clamp the fibre end'],
      upd: function (I) { var a = p.x * 3, R = 0.28; I.det.g.position.set(-0.1 + R * Math.cos(a), 0, BZ + R * Math.sin(a)); I.det.g.rotation.y = -a; },
      beams: function (I) { return [[I.ch, I.det]]; }, meter: 'P',
      plan: function (i) { return 'arm at ' + fmt(1.5 * i, 1) + '°'; },
      res: [{ label: 'mode field diameter', unit: 'µm', f: 1e6, digits: 2 }],
      graph: { x: function (r) { return r.x * r.x / DEG / DEG; }, y: function (r) { return r.P > 0 ? Math.log(r.P * 1e9) : 0; }, xlabel: 'θ² (deg²)', ylabel: 'ln P (nW)', fit: 'linear' },
      view: [[0.0, 0.55, 0.55], [0.0, 0.1, BZ]]
    };
  }
  function cfgLd() {
    return {
      title: 'Laser diode L-I curve', formula: 'P = η (I − I_th)   above threshold', note: 'I_th: where the two straight parts of the curve meet; η: slope of the upper part',
      items: [['source', 'src', -0.5, BZ, { text: 'LASER DIODE DRIVER', name: 'Laser-diode current driver', info: 'A constant-current source with a fine control, read to 0.1 mA.' }],
        ['ldmount', 'ld', -0.2, BZ, { name: 'Laser diode on its mount', info: (SAMPLE || 'The laser diode under test') + '.' }],
        ['detector', 'det', 0.05, BZ, { name: 'Power-meter head', info: 'Catches the whole diverging beam.' }],
        ['meter', 'met', 0.42, -0.02, { name: 'Optical power meter', info: 'Reads the optical power to 0.001 mW.' }]],
      handles: { x: 'src' }, src: 'src', readyOn: 'det', readyText: ['Set the current limit and put the power-meter head in front of the diode', 'Set the current limit'],
      wire: [['src', 'ld']],
      beams: function (I) { return p.x > 0 ? [[I.ld, I.det]] : []; }, meter: 'P',
      plan: function (i, s) { return fmt(s.x * 1000, 1) + ' mA'; },
      res: [{ label: 'threshold current', unit: 'mA', f: 1000, digits: 2 }, { label: 'slope efficiency', unit: 'W/A', f: 1, digits: 3 }],
      graph: { x: function (r) { return r.x * 1000; }, y: function (r) { return r.P * 1000; }, xlabel: 'current (mA)', ylabel: 'power (mW)', fit: null },
      view: [[-0.15, 0.5, 0.6], [-0.15, 0.1, BZ]], lam: 6.5e-7
    };
  }
  var CFGS = { w7_tir: cfgTir, w7_wollaston: cfgWollaston, w7_nodal: cfgNodal, w7_biprism: cfgBiprism, w7_fringes: cfgFringes, w7_fabry: cfgFabry,
    w7_fts: cfgFts, w7_corona: cfgCorona, w7_resolve: cfgResolve, w7_malus: cfgMalus, w7_babinet: cfgBabinet, w7_nearfield: cfgNear,
    w7_bend: cfgBend, w7_splice: cfgSplice, w7_mfd: cfgMfd, w7_ld: cfgLd };
  if (!CFGS[KN]) throw new Error('w7-optics-bench has no set-up for kernel ' + KN);
  var C = CFGS[KN]();
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
  }).filter(function (c) { return c.id !== 'stage' || STAGES.length > 1; });
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
    if (lit && e.t === 'strip') { var span = e.span();
      for (i = 0; i < w; i++) { a = K.read(Object.assign({}, p, { x: p.x + (i / w - 0.5) * 2 * span }))[e.key]; ectx.fillStyle = col(Math.pow(Math.max(0, a), e.gamma || 0.6)); ectx.fillRect(i, 8, 1, h - 16); } }
    else if (lit && e.t === 'rings') { var N = rd.N, cx = w / 2, cy = h / 2, r;
      for (r = 70; r >= 0; r -= 1) { var ph = N + 3.2 * (r / 64) * (r / 64), s = Math.sin(Math.PI * ph), cc = Math.cos(Math.PI * ph);
        a = e.sharp ? 1 / (1 + 30 * s * s) : cc * cc; ectx.fillStyle = col(a); ectx.beginPath(); ectx.arc(cx, cy, r, 0, 7); ectx.fill(); ectx.fillStyle = '#0a0b0d'; if (r > 0) { ectx.beginPath(); ectx.arc(cx, cy, r - 1, 0, 7); ectx.fill(); } } }
    else if (lit && e.t === 'half') { var edge = w * (1 - rd.bright); ectx.fillStyle = col(0.9); ectx.fillRect(edge, 8, w - edge, h - 16);
      if (Math.abs(rd.refl) < 0.012) { ectx.strokeStyle = 'rgba(255,255,255,.6)'; ectx.lineWidth = 2; var rx = w / 2 + rd.refl / 0.012 * w / 2; ectx.beginPath(); ectx.moveTo(rx - 12, h / 2 - 12); ectx.lineTo(rx + 12, h / 2 + 12); ectx.moveTo(rx + 12, h / 2 - 12); ectx.lineTo(rx - 12, h / 2 + 12); ectx.stroke(); } }
    else if (lit && e.t === 'level') { ectx.fillStyle = col(Math.pow(rd[e.key], 0.6)); ectx.fillRect(0, 8, w, h - 16); }
    else if (lit && e.t === 'pair') { var ang = p.s / p.D;
      for (i = 0; i < w; i++) { var th = (i / w - 0.5) * 6 * ang, u1 = Math.PI * p.x * (th - ang / 2) / p.lam, u2 = Math.PI * p.x * (th + ang / 2) / p.lam;
        a = (Math.abs(u1) < 1e-9 ? 1 : Math.pow(Math.sin(u1) / u1, 2)) + (Math.abs(u2) < 1e-9 ? 1 : Math.pow(Math.sin(u2) / u2, 2)); ectx.fillStyle = col(Math.pow(Math.min(1, a), 0.7)); ectx.fillRect(i, 8, 1, h - 16); } }
    if (e.t !== 'rings' && e.t !== 'level') { ectx.strokeStyle = 'rgba(240,244,248,.9)'; ectx.lineWidth = 1; ectx.beginPath(); ectx.moveTo(w / 2, 2); ectx.lineTo(w / 2, h - 2); ectx.moveTo(w / 2 - 14, h / 2); ectx.lineTo(w / 2 + 14, h / 2); ectx.stroke(); }
  }
  var HC = CTL.map(function (c) { return S.hudCard(c.label.length > 34 ? c.label.slice(0, 32) + '…' : c.label); });
  var HR = READS.map(function (r) { return S.hudCard(r.label.length > 34 ? r.label.slice(0, 32) + '…' : r.label); });
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
    if (I[C.src] && I[C.src].glow) I[C.src].glow.material.color.setHex(st.on ? (C.items[0][4].text ? 0xfff2cc : 0xffc83c) : 0x35311f);
    CTL.forEach(function (c, i) { HC[i].set(c.key === 'stage' ? stageName(p.stage) : fmt(p[c.key] * c.f, c.digits) + ' ' + c.unit); });
    READS.forEach(function (r, i) { HR[i].set(shown(r, rd)); });
    if (I.met && I.met.tex) { var mr = readOf(C.meter || (READS[0] && READS[0].key)), txt = mr ? shown(mr, rd) : '—';
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
