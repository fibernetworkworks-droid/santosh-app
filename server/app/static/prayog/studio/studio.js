/* Hoola Prayogshala STUDIO (v0.419): the realistic lab every experiment runs in.
   One engine, 22 experiments: the room (walls, window daylight, poster, clock, shelf with glassware), a black epoxy
   bench, real-looking materials, shared lab DEVICES (retort stand, stopwatch, analog meters, thermometer, scales,
   wires, cells, keys, rheostat, resistance box, optical bench, tuning fork, beaker...), a gloved HAND that does the
   human actions, the guided WORKFLOW (theory -> experiment steps -> graph / result -> viva), the handwritten RECORD
   BOOK, and ASK HOOLA (answers only about this experiment, from the live state, via the Hoola server).
   An experiment is a module: HoolaStudio.define(id, (S) => ({...})) in exp/<id>.js. Physics numbers come from the
   kernels (kernels.js twins), never from the page's guesses. */
(function () {
  'use strict';
  var T = window.THREE;
  var DEFS = {};
  window.HoolaStudio = { define: function (id, fn) { DEFS[id] = fn; }, defs: DEFS, start: start };

  function $(s, root) { return (root || document).querySelector(s); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
  var RM = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var TEST = /[?&]test=1/.test(location.search);

  function start(root, lab) {
    var make = DEFS[lab.rig || lab.id];             // a variant runs on its family's rig with its own numbers
    if (!make) throw new Error('No studio module for ' + (lab.rig || lab.id));
    root.innerHTML = '';
    var S = toolkit(root, lab);
    try {
      var exp = make(S);
      S.exp = exp;
      workflow(S, lab, exp);
    } catch (err) {                                  // a rig that throws must not leave a render loop running on an empty scene
      S.dead = true;
      window.__studioError = String((err && err.message) || err);
      console.error(err);
      root.innerHTML = '';
      var m = el('p', 'err', 'This experiment could not start: ' + window.__studioError);
      m.style.cssText = 'padding:16px;color:#b42318';
      root.appendChild(m);
      throw err;
    }
    window.__studio = S;
    return S;
  }

  /* ================================================================================================== toolkit */
  function toolkit(root, lab) {
    var S = { T: T, lab: lab, fast: TEST, state: {}, groups: {}, apparatus: [], tickers: [], rows: [] };

    // ---------- page shell
    var app = el('div', 'app'); root.appendChild(app);
    var top = el('header', 'top'); app.appendChild(top);
    var back = el('a', 'back', '‹'); back.href = './'; back.setAttribute('aria-label', 'All labs'); top.appendChild(back);
    top.appendChild(el('span', 'mark', 'Prayogshala'));
    top.appendChild(el('span', 'crumb', [lab.group, lab.level].filter(Boolean).join(' · ')));
    top.appendChild(el('span', 'grow'));
    S.stepPill = el('span', 'pill', ''); top.appendChild(S.stepPill);
    var side = el('aside', 'side'); app.appendChild(side);
    S.stepsNav = el('nav', 'steps'); S.stepsNav.setAttribute('aria-label', 'Experiment steps'); side.appendChild(S.stepsNav);
    S.pane = el('div', 'pane'); side.appendChild(S.pane);
    var stage = el('main', 'stage'); app.appendChild(stage); S.stage = stage;
    S.hud = el('div', 'hud'); stage.appendChild(S.hud);
    var hint = el('div', 'hint3d', 'Drag to look around · scroll or pinch to zoom · tap any apparatus'); stage.appendChild(hint);

    // ---------- renderer + scene
    var renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, TEST ? 1 : 2));
    renderer.outputEncoding = T.sRGBEncoding; renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap; renderer.physicallyCorrectLights = true;
    stage.prepend(renderer.domElement);
    var scene = new T.Scene(); scene.background = new T.Color(0xcfcac2); scene.fog = new T.Fog(0xcfcac2, 3.2, 7.5);
    var camera = new T.PerspectiveCamera(38, 1, 0.005, 30);
    S.renderer = renderer; S.scene = scene; S.camera = camera;

    // ---------- small helpers
    var seed = 11; var rnd = S.rnd = function () { return (seed = (seed * 16807) % 2147483647) / 2147483647; };
    S.canvasTex = function (w, h, draw, srgb) {
      var c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
      var t = new T.CanvasTexture(c); if (srgb !== false) t.encoding = T.sRGBEncoding; t.anisotropy = 8; return t;
    };
    S.liveTex = function (w, h) {   // a canvas texture you redraw: tex.draw(fn(ctx,w,h))
      var c = document.createElement('canvas'); c.width = w; c.height = h; var t = new T.CanvasTexture(c); t.encoding = T.sRGBEncoding; t.anisotropy = 8;
      t.draw = function (fn) { fn(c.getContext('2d'), w, h); t.needsUpdate = true; }; return t;
    };
    function noiseTex(w, h, base, spots, alpha, size) {
      return S.canvasTex(w, h, function (x) { x.fillStyle = base; x.fillRect(0, 0, w, h);
        for (var i = 0; i < spots; i++) { var s = 0.6 + rnd() * size; x.fillStyle = 'rgba(' + (rnd() < .5 ? '255,255,255' : '0,0,0') + ',' + (rnd() * alpha) + ')'; x.fillRect(rnd() * w, rnd() * h, s, s); } });
    }
    S.noiseTex = noiseTex;
    S.rounded = function (w, h, d, r, mat, seg) {
      var s = new T.Shape(), x = -w / 2, y = -h / 2;
      s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + h - r);
      s.quadraticCurveTo(x + w, y + h, x + w - r, y + h); s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r); s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
      var bv = Math.min(r, d) * 0.3;
      var g = new T.ExtrudeGeometry(s, { depth: Math.max(d - 2 * bv, 0.0002), bevelEnabled: true, bevelThickness: bv, bevelSize: bv, bevelSegments: seg || 4, curveSegments: 12 });
      g.translate(0, 0, -Math.max(d - 2 * bv, 0.0002) / 2);
      var m = new T.Mesh(g, mat); m.castShadow = m.receiveShadow = true; return m;
    };
    S.mesh = function (g, m, cast, recv) { var o = new T.Mesh(g, m); o.castShadow = cast !== false; o.receiveShadow = recv !== false; return o; };
    var blob = S.canvasTex(128, 128, function (x) { var g = x.createRadialGradient(64, 64, 4, 64, 64, 64); g.addColorStop(0, 'rgba(0,0,0,.55)'); g.addColorStop(1, 'rgba(0,0,0,0)'); x.fillStyle = g; x.fillRect(0, 0, 128, 128); });
    S.contact = function (w, d, x, z, o, y) {
      var m = new T.Mesh(new T.PlaneGeometry(w, d), new T.MeshBasicMaterial({ map: blob, transparent: true, opacity: o === undefined ? 0.5 : o, depthWrite: false }));
      m.rotation.x = -Math.PI / 2; m.position.set(x, (y || 0) + 0.0008, z); m.renderOrder = 1; scene.add(m); return m;
    };
    S.label = function (text, opts) {   // printed text on a plane (engraving, labels on devices)
      opts = opts || {}; var w = opts.px || 512, h = Math.round(w * (opts.ratio || 0.25));
      var tex = S.canvasTex(w, h, function (x) { if (opts.bg) { x.fillStyle = opts.bg; x.fillRect(0, 0, w, h); }
        x.fillStyle = opts.color || '#1b1b1b'; x.font = (opts.weight || 600) + ' ' + Math.round(h * 0.55) + 'px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(text, w / 2, h / 2); });
      var m = new T.Mesh(new T.PlaneGeometry(opts.w || 0.05, (opts.w || 0.05) * (opts.ratio || 0.25)), new T.MeshStandardMaterial({ map: tex, transparent: !opts.bg, roughness: 0.6 }));
      return m;
    };

    // ---------- reflections + lights
    (function env() {
      var pm = new T.PMREMGenerator(renderer), room = new T.Scene();
      room.add(new T.Mesh(new T.BoxGeometry(10, 6, 10), new T.MeshStandardMaterial({ color: 0x7d7770, side: T.BackSide })));
      room.add(new T.AmbientLight(0xffffff, 0.5));
      function panel(w, h, pos, k, tint) { var m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ color: new T.Color(tint).multiplyScalar(k) })); m.position.set(pos[0], pos[1], pos[2]); m.lookAt(0, 0, 0); room.add(m); }
      panel(3.5, 0.5, [0, 2.9, 0], 7, 0xffffff); panel(3.5, 0.5, [0, 2.9, -2], 6, 0xffffff);
      panel(2.2, 2.6, [-4.9, 1.4, 0], 4, 0xfff1dc); panel(3, 1.4, [0, 1.2, 4.9], 1.4, 0xffffff);
      scene.environment = pm.fromScene(room, 0.035).texture;
    })();
    var sun = new T.DirectionalLight(0xffe7c4, 3.0); sun.position.set(-2.4, 2.6, 1.4); sun.castShadow = true;
    sun.shadow.mapSize.set(TEST ? 1024 : 2048, TEST ? 1024 : 2048);
    Object.assign(sun.shadow.camera, { left: -1.1, right: 1.1, top: 1.6, bottom: -0.5, near: 0.5, far: 7 });
    sun.shadow.radius = 5; sun.shadow.bias = -0.0003; sun.shadow.normalBias = 0.01; scene.add(sun);
    var tube = new T.DirectionalLight(0xf3f6ff, 1.1); tube.position.set(0.6, 3, 0.8); scene.add(tube);
    scene.add(new T.HemisphereLight(0xf4f1ea, 0x6b5f52, 0.5));

    // ---------- materials
    var epoxy = noiseTex(512, 512, '#1d2124', 9000, 0.06, 2.2); epoxy.wrapS = epoxy.wrapT = T.RepeatWrapping; epoxy.repeat.set(3, 1.5);
    var woodTex = S.canvasTex(512, 256, function (x, w, h) { x.fillStyle = '#d8c08a'; x.fillRect(0, 0, w, h);
      for (var i = 0; i < 90; i++) { var y0 = rnd() * h; x.strokeStyle = 'rgba(140,100,50,' + (.08 + rnd() * .14) + ')'; x.lineWidth = .6 + rnd() * 1.5; x.beginPath();
        for (var px = 0; px <= w; px += 8) { var yy = y0 + Math.sin(px * .012 + i) * 3; if (px) x.lineTo(px, yy); else x.moveTo(px, yy); } x.stroke(); } });
    var darkWood = S.canvasTex(512, 256, function (x, w, h) { x.fillStyle = '#7a4e2c'; x.fillRect(0, 0, w, h);
      for (var i = 0; i < 120; i++) { var y0 = rnd() * h; x.strokeStyle = 'rgba(50,25,10,' + (.1 + rnd() * .2) + ')'; x.lineWidth = .6 + rnd() * 1.8; x.beginPath();
        for (var px = 0; px <= w; px += 8) { var yy = y0 + Math.sin(px * .01 + i) * 3; if (px) x.lineTo(px, yy); else x.moveTo(px, yy); } x.stroke(); } });
    darkWood.wrapS = darkWood.wrapT = T.RepeatWrapping;
    S.woodTex = woodTex;
    var M = S.M = {
      epoxy: new T.MeshStandardMaterial({ map: epoxy, roughness: 0.32, metalness: 0.05 }),
      cabinet: new T.MeshStandardMaterial({ color: 0x6f8193, roughness: 0.6 }),
      iron: new T.MeshStandardMaterial({ map: noiseTex(256, 256, '#25313b', 5000, 0.05, 1.6), roughness: 0.42, metalness: 0.4 }),
      chrome: new T.MeshStandardMaterial({ color: 0xe9ebed, roughness: 0.1, metalness: 1 }),
      alu: new T.MeshStandardMaterial({ color: 0xc4c9ce, roughness: 0.3, metalness: 0.9 }),
      brass: new T.MeshStandardMaterial({ color: 0xd6aa4c, roughness: 0.18, metalness: 1 }),
      copper: new T.MeshStandardMaterial({ color: 0xc8764a, roughness: 0.25, metalness: 1 }),
      steel: new T.MeshStandardMaterial({ color: 0xd2d6d9, roughness: 0.22, metalness: 1 }),
      black: new T.MeshStandardMaterial({ color: 0x0c0d0f, roughness: 0.55, metalness: 0.05 }),
      bakelite: new T.MeshStandardMaterial({ color: 0x17181b, roughness: 0.35, metalness: 0.05 }),
      rubber: new T.MeshStandardMaterial({ color: 0x141414, roughness: 0.9 }),
      white: new T.MeshStandardMaterial({ color: 0xf2f2ef, roughness: 0.8 }),
      red: new T.MeshStandardMaterial({ color: 0xc23b30, roughness: 0.4 }), blackPlastic: new T.MeshStandardMaterial({ color: 0x1b1b1d, roughness: 0.4 }),
      green: new T.MeshStandardMaterial({ color: 0x2e9b5a, roughness: 0.35 }), grey: new T.MeshStandardMaterial({ color: 0x5f646b, roughness: 0.35 }),
      wood: new T.MeshStandardMaterial({ map: woodTex, roughness: 0.6 }), darkWood: new T.MeshStandardMaterial({ map: darkWood, roughness: 0.55 }),
      cork: new T.MeshStandardMaterial({ map: S.canvasTex(256, 256, function (x, w, h) { x.fillStyle = '#c29660'; x.fillRect(0, 0, w, h);
        for (var i = 0; i < 3200; i++) { var s = 1 + rnd() * 3; x.fillStyle = rnd() < .5 ? 'rgba(110,70,35,.4)' : 'rgba(240,210,160,.35)'; x.fillRect(rnd() * w, rnd() * h, s, s); } }), roughness: 0.95 }),
      thread: new T.MeshStandardMaterial({ color: 0xf4f0e6, roughness: 0.95 }),
      glass: new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, metalness: 0, transmission: 0.92, thickness: 0.004, ior: 1.5, transparent: true }),
      glassBlock: new T.MeshPhysicalMaterial({ color: 0xe8f4f2, roughness: 0.03, metalness: 0, transmission: 0.95, thickness: 0.05, ior: 1.5, transparent: true }),
      glove: new T.MeshStandardMaterial({ color: 0x2c63c4, roughness: 0.42 }), cuff: new T.MeshStandardMaterial({ color: 0xf2f2ef, roughness: 0.85 }),
      paper: new T.MeshStandardMaterial({ color: 0xf6f3ea, roughness: 0.9 }),
    };

    // ---------- room
    var floorTex = S.canvasTex(1024, 1024, function (x, w, h) { var n = 8, s = w / n;
      for (var i = 0; i < n; i++) for (var j = 0; j < n; j++) { var v = 196 + rnd() * 16; x.fillStyle = 'rgb(' + v + ',' + (v - 6) + ',' + (v - 14) + ')'; x.fillRect(i * s, j * s, s, s); }
      x.strokeStyle = 'rgba(80,70,60,.35)'; x.lineWidth = 2; for (var k = 0; k <= n; k++) { x.beginPath(); x.moveTo(k * s, 0); x.lineTo(k * s, h); x.stroke(); x.beginPath(); x.moveTo(0, k * s); x.lineTo(w, k * s); x.stroke(); } });
    floorTex.wrapS = floorTex.wrapT = T.RepeatWrapping; floorTex.repeat.set(3, 3);
    var tileTex = S.canvasTex(1024, 512, function (x, w, h) { var cols = 10, rows = 5, s = w / cols; x.fillStyle = '#d9dcd6'; x.fillRect(0, 0, w, h);
      for (var i = 0; i < cols; i++) for (var j = 0; j < rows; j++) { var v = 230 + rnd() * 14; x.fillStyle = 'rgb(' + (v - 6) + ',' + v + ',' + (v - 4) + ')'; x.fillRect(i * s + 3, j * (h / rows) + 3, s - 6, h / rows - 6); } });
    tileTex.wrapS = T.RepeatWrapping; tileTex.repeat.set(3, 1);
    var paint = noiseTex(256, 256, '#e8e4dc', 3000, 0.03, 2); paint.wrapS = paint.wrapT = T.RepeatWrapping; paint.repeat.set(4, 2);
    var wallM = new T.MeshStandardMaterial({ map: paint, roughness: 0.9 });
    var floor = S.mesh(new T.PlaneGeometry(8, 8), new T.MeshStandardMaterial({ map: floorTex, roughness: 0.75 }), false); floor.rotation.x = -Math.PI / 2; floor.position.y = -0.9; scene.add(floor);
    var backW = S.mesh(new T.PlaneGeometry(8, 3.4), wallM, false); backW.position.set(0, 0.8, -0.95); scene.add(backW);
    var tiles = S.mesh(new T.PlaneGeometry(8, 0.6), new T.MeshStandardMaterial({ map: tileTex, roughness: 0.35 }), false); tiles.position.set(0, 0.29, -0.948); scene.add(tiles);
    var leftW = S.mesh(new T.PlaneGeometry(4, 3.4), wallM, false); leftW.rotation.y = Math.PI / 2; leftW.position.set(-1.6, 0.8, 1); scene.add(leftW);
    var sky = S.canvasTex(512, 512, function (x, w, h) { var g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#bcd8f2'); g.addColorStop(.7, '#eef4f6'); g.addColorStop(1, '#d7e2c8'); x.fillStyle = g; x.fillRect(0, 0, w, h);
      x.fillStyle = 'rgba(120,150,110,.55)'; for (var i = 0; i < 40; i++) { x.beginPath(); x.arc(rnd() * w, h * .82 + rnd() * h * .2, 20 + rnd() * 40, 0, Math.PI * 2); x.fill(); } });
    var win = new T.Mesh(new T.PlaneGeometry(1.2, 1.0), new T.MeshBasicMaterial({ map: sky, toneMapped: false })); win.rotation.y = Math.PI / 2; win.position.set(-1.595, 1.05, 0.15); scene.add(win);
    [[0, 0.5, 1.24, 0.05], [0, -0.5, 1.24, 0.05], [0.6, 0, 0.05, 1.04], [-0.6, 0, 0.05, 1.04], [0, 0, 0.035, 1.0], [0, 0, 1.2, 0.035]].forEach(function (a) {
      var f = S.mesh(new T.BoxGeometry(0.04, a[3], a[2]), M.white); f.position.set(-1.58, 1.05 + a[1], 0.15 + a[0]); scene.add(f); });
    var poster = S.canvasTex(1024, 640, function (x, w, h) { x.fillStyle = '#f7f5ef'; x.fillRect(0, 0, w, h); x.fillStyle = '#23324a'; x.font = '700 44px "Public Sans", sans-serif'; x.fillText('PERIODIC TABLE OF ELEMENTS', 40, 64);
      var cols = ['#e7a96b', '#f2d46b', '#9fd09b', '#8fc4e6', '#c6a3e0', '#f19a9a'], cw = 52, ch = 58;
      for (var r = 0; r < 7; r++) for (var c = 1; c <= 18; c++) { if (r === 0 && c > 1 && c < 18) continue; if ((r === 1 || r === 2) && c > 2 && c < 13) continue;
        x.fillStyle = cols[(c + r) % cols.length]; x.fillRect(40 + (c - 1) * cw, 100 + r * ch, cw - 4, ch - 4); }
      for (var k = 0; k < 15; k++) { x.fillStyle = '#e8c7a0'; x.fillRect(196 + k * cw, 530, cw - 4, 44); x.fillStyle = '#b9d6c4'; x.fillRect(196 + k * cw, 578, cw - 4, 44); } });
    var pst = new T.Mesh(new T.PlaneGeometry(0.72, 0.45), new T.MeshStandardMaterial({ map: poster, roughness: 0.8 })); pst.position.set(-0.55, 1.3, -0.945); scene.add(pst);
    var signT = S.canvasTex(1024, 192, function (x) { x.fillStyle = '#2f4a3a'; x.fillRect(0, 0, 1024, 192); x.fillStyle = '#f2efe4'; x.font = '700 78px "Newsreader", Georgia, serif'; x.fillText('Physics Laboratory', 60, 120);
      x.font = '500 30px "Public Sans", sans-serif'; x.fillStyle = '#cfe0d4'; x.fillText(lab.level || '', 64, 166); });
    var sign = new T.Mesh(new T.PlaneGeometry(0.62, 0.116), new T.MeshStandardMaterial({ map: signT, roughness: 0.6 })); sign.position.set(0.5, 1.62, -0.945); scene.add(sign);
    var clockTex = S.liveTex(256, 256);
    function drawClock() { clockTex.draw(function (x) { var c = 128, d = new Date(); x.clearRect(0, 0, 256, 256); x.fillStyle = '#fbfaf6'; x.beginPath(); x.arc(c, c, 120, 0, Math.PI * 2); x.fill();
      x.strokeStyle = '#1b1b1b'; for (var i = 0; i < 60; i++) { var a = i / 60 * Math.PI * 2, r0 = i % 5 ? 108 : 100; x.lineWidth = i % 5 ? 2 : 6; x.beginPath(); x.moveTo(c + Math.sin(a) * r0, c - Math.cos(a) * r0); x.lineTo(c + Math.sin(a) * 116, c - Math.cos(a) * 116); x.stroke(); }
      function hand(a, len, wd, col) { x.strokeStyle = col; x.lineWidth = wd; x.lineCap = 'round'; x.beginPath(); x.moveTo(c, c); x.lineTo(c + Math.sin(a) * len, c - Math.cos(a) * len); x.stroke(); }
      var s = d.getSeconds(), m = d.getMinutes() + s / 60, hr = (d.getHours() % 12) + m / 60;
      hand(hr / 12 * Math.PI * 2, 62, 9, '#1b1b1b'); hand(m / 60 * Math.PI * 2, 92, 6, '#1b1b1b'); hand(s / 60 * Math.PI * 2, 100, 2.5, '#c0392b'); }); }
    drawClock(); setInterval(drawClock, 1000);
    var clock = new T.Group(); scene.add(clock); clock.add(S.mesh(new T.TorusGeometry(0.105, 0.012, 16, 48), M.black));
    var face = new T.Mesh(new T.CircleGeometry(0.1, 48), new T.MeshStandardMaterial({ map: clockTex, transparent: true, roughness: 0.4 })); face.position.z = 0.002; clock.add(face); clock.position.set(0.18, 1.33, -0.94);
    var shelf = S.mesh(new T.BoxGeometry(0.9, 0.025, 0.2), M.wood); shelf.position.set(0.72, 1.12, -0.85); scene.add(shelf);
    S.beaker = function (r, h, pos, liquid, level) {
      var g = new T.Group(); var pts = []; for (var i = 0; i <= 12; i++) pts.push(new T.Vector2(r * (i < 2 ? i / 2 : 1), h * Math.max(0, i - 1) / 11));
      g.add(new T.Mesh(new T.LatheGeometry(pts, 36), M.glass));
      var lip = S.mesh(new T.TorusGeometry(r, 0.0012, 6, 36), M.glass, false); lip.rotation.x = Math.PI / 2; lip.position.y = h; g.add(lip);
      var liq = null;
      if (liquid) { liq = S.mesh(new T.CylinderGeometry(r * 0.94, r * 0.94, 1, 32), new T.MeshPhysicalMaterial({ color: liquid, transmission: 0.55, roughness: 0.08, thickness: 0.02, transparent: true, opacity: 0.85 }), false);
        g.add(liq); }
      g.setLevel = function (f) { if (!liq) return; var hh = Math.max(0.001, h * f); liq.scale.y = hh; liq.position.y = hh / 2 + 0.001; };
      g.setLevel(level === undefined ? 0.45 : level);
      g.position.set(pos[0], pos[1], pos[2]); scene.add(g); return g;
    };
    S.beaker(0.035, 0.09, [0.45, 1.133, -0.85], 0x9fd0e6); S.beaker(0.028, 0.07, [0.56, 1.133, -0.83]); S.beaker(0.04, 0.11, [0.98, 1.133, -0.86], 0xe6c58f);
    var bottle = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.12, 24), new T.MeshPhysicalMaterial({ color: 0x5a2b0c, roughness: .15, transmission: .35, thickness: .02 })); bottle.position.set(0.72, 1.193, -0.86); scene.add(bottle);

    // ---------- bench
    var top2 = S.rounded(2.6, 1.0, 0.04, 0.012, M.epoxy); top2.rotation.x = -Math.PI / 2; top2.position.set(0, -0.02, -0.2); top2.castShadow = false; scene.add(top2);
    var cab = S.mesh(new T.BoxGeometry(2.5, 0.84, 0.9), M.cabinet, false); cab.position.set(0, -0.46, -0.2); scene.add(cab);
    for (var i = 0; i < 4; i++) { var hd = S.mesh(new T.BoxGeometry(0.14, 0.012, 0.012), M.chrome); hd.position.set(-0.9 + i * 0.6, -0.12, 0.262); scene.add(hd);
      var ln = S.mesh(new T.BoxGeometry(0.004, 0.8, 0.004), M.black, false); ln.position.set(-1.2 + i * 0.6, -0.46, 0.252); scene.add(ln); }
    S.BENCH_FRONT = 0.29;   // z of the bench's front edge; keep every object behind it

    devices(S);
    hand(S);
    camera_controls(S);
    record_book(S);
    return S;
  }

  /* ================================================================================================== devices */
  function devices(S) {
    var M = S.M, scene = S.scene;

    // retort stand with boss head, clamp arm and (optionally) a split cork at the clamp jaw
    S.stand = function (opts) {
      opts = opts || {}; var x = opts.x || 0, z = opts.z || 0, h = opts.h || 1.22, armY = opts.armY || 1.13, armLen = opts.armLen || 0.2;
      var g = new T.Group(); scene.add(g);
      var base = S.rounded(0.27, 0.17, 0.022, 0.02, M.iron); base.rotation.x = -Math.PI / 2; base.position.set(x - 0.12, 0.011, z); g.add(base);
      [[-0.24, -0.07], [-0.24, 0.07], [0, -0.07], [0, 0.07]].forEach(function (f) { var ft = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.003, 16), M.rubber); ft.position.set(x + f[0], 0.0015, z + f[1]); g.add(ft); });
      var rx = x - 0.19;
      var nut = S.mesh(new T.CylinderGeometry(0.017, 0.017, 0.012, 6), M.chrome); nut.position.set(rx, 0.028, z); g.add(nut);
      var rod = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, h, 40), M.chrome); rod.position.set(rx, h / 2 + 0.02, z); g.add(rod);
      var boss = S.rounded(0.05, 0.046, 0.042, 0.007, M.alu); boss.position.set(rx, armY, z); g.add(boss);
      function thumb(px, py, pz, rxx, rzz) { var t = new T.Group(); var s = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.035, 16), M.chrome); s.position.y = 0.017; t.add(s);
        var k = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.009, 6), M.black); k.position.y = 0.036; t.add(k); t.position.set(px, py, pz); t.rotation.set(rxx, 0, rzz); g.add(t); }
      thumb(rx, armY, z + 0.02, Math.PI / 2, 0); thumb(rx + 0.025, armY, z, 0, -Math.PI / 2);
      var arm = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, armLen, 24), M.chrome); arm.rotation.z = Math.PI / 2; arm.position.set(rx + armLen / 2, armY, z); g.add(arm);
      var jaw = S.rounded(0.034, 0.028, 0.032, 0.006, M.alu); jaw.position.set(rx + armLen - 0.01 + 0.01, armY - 0.002, z); g.add(jaw);
      thumb(rx + armLen, armY - 0.002, z + 0.016, Math.PI / 2, 0);
      S.contact(0.42, 0.28, x - 0.12, z, 0.55);
      g.userData.jaw = new T.Vector3(rx + armLen, armY, z);
      return g;
    };
    S.cork = function (pos) { var g = new T.Group(); scene.add(g);
      [-1, 1].forEach(function (sg) { var c = S.mesh(new T.CylinderGeometry(0.012, 0.0095, 0.032, 28, 1, false, 0, Math.PI), M.cork); c.rotation.y = sg > 0 ? -Math.PI / 2 : Math.PI / 2; c.position.set(pos.x + sg * 0.0006, pos.y, pos.z); g.add(c); });
      return g; };

    // printed scales (metre scale, half-metre, bench scales): length in m, zero at `zeroAt` (m from the start)
    S.scaleTex = function (lengthM, opts) {
      opts = opts || {}; var pxPerMm = opts.pxPerMm || 4, mm = Math.round(lengthM * 1000), H = mm * pxPerMm + 40, W = opts.w || 160;
      return S.canvasTex(W, Math.min(H, 8192), function (x, w, h) {
        x.drawImage(S.woodTex.image, 0, 0, w, h); if (opts.bg) { x.fillStyle = opts.bg; x.fillRect(0, 0, w, h); }
        var k = h / (mm + 20); x.fillStyle = opts.ink || '#151515'; x.font = '600 ' + Math.round(w * 0.2) + 'px "Public Sans", sans-serif';
        var step = opts.labelEvery || 10, start = opts.start || 0, unitDiv = opts.unitDiv || 10;
        for (var i = 0; i <= mm; i++) { var y = (10 + i) * k, len = i % 10 === 0 ? w * 0.38 : i % 5 === 0 ? w * 0.26 : w * 0.16; x.fillRect(0, y - 0.8, len, 1.6);
          if (i % step === 0) x.fillText(String(start + i / unitDiv), w * 0.46, y + w * 0.07); }
        if (opts.title) { x.save(); x.fillStyle = '#6b4a14'; x.font = '600 ' + Math.round(w * 0.15) + 'px "Public Sans", sans-serif'; x.translate(w * 0.86, h - 30); x.rotate(-Math.PI / 2); x.fillText(opts.title, 0, 0); x.restore(); }
      });
    };
    // S.ruler: a wooden scale along +y of its group; its ZERO mark sits at local y = lengthM and the mark for v metres at
    // local y = lengthM - v (true scale: 1 printed mm = 1 mm), so placing the group at (zeroY - lengthM) puts zero at zeroY
    S.ruler = function (lengthM, opts) {
      opts = opts || {}; var tex = S.scaleTex(lengthM, opts), wdt = opts.width || 0.03;
      var edge = M.wood, face = new T.MeshStandardMaterial({ map: tex, roughness: 0.55 });
      var m = S.mesh(new T.BoxGeometry(wdt, lengthM + 0.02, opts.thick || 0.006), [edge, edge, edge, edge, face, edge]);
      var g = new T.Group(); g.add(m); m.position.y = (lengthM + 0.02) / 2 - 0.01; scene.add(g); return g;
    };

    // digital stopwatch (LCD you can read; START/STOP + RESET buttons the hand presses)
    S.stopwatch = function (pos, rot) {
      var lcd = S.liveTex(512, 200), last = '';
      var w = { t: 0, on: false, group: new T.Group() };
      w.draw = function () { var t = w.t, s = Math.floor(t), cs = Math.floor((t - s) * 100), mm = Math.floor(s / 60), ss = s % 60;
        var txt = String(mm).padStart(2, '0') + ':' + String(ss).padStart(2, '0') + '.' + String(cs).padStart(2, '0'); if (txt + w.on === last) return; last = txt + w.on;
        lcd.draw(function (x) { var gr = x.createLinearGradient(0, 0, 0, 200); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); x.fillStyle = gr; x.fillRect(0, 0, 512, 200);
          x.font = '700 104px "JetBrains Mono", monospace'; x.textAlign = 'center'; x.fillStyle = 'rgba(0,0,0,.07)'; x.fillText('88:88.88', 256, 126); x.fillStyle = '#1b2116'; x.fillText(txt, 256, 126);
          x.font = '600 26px "Public Sans", sans-serif'; x.textAlign = 'left'; x.fillText(w.on ? '▶ RUN' : '■ STOP', 22, 182); x.textAlign = 'right'; x.fillText('1/100 SEC', 490, 182); }); };
      var g = w.group; scene.add(g);
      g.add(S.rounded(0.07, 0.095, 0.02, 0.018, M.black));
      var bz = S.rounded(0.06, 0.03, 0.002, 0.005, M.grey); bz.position.set(0, 0.016, 0.0105); g.add(bz);
      var scr = new T.Mesh(new T.PlaneGeometry(0.054, 0.022), new T.MeshBasicMaterial({ map: lcd, toneMapped: false })); scr.position.set(0, 0.016, 0.0122); g.add(scr);
      w.start = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 0.008, 24), M.green); w.start.position.set(0.014, 0.05, 0); g.add(w.start);
      w.reset = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 0.008, 24), M.grey); w.reset.position.set(-0.014, 0.05, 0); g.add(w.reset);
      var lb = S.label('START/STOP      RESET', { w: 0.056, ratio: 0.18, color: '#c9ccd1' }); lb.position.set(0, -0.014, 0.0112); g.add(lb);
      var br = S.label('LAB TIMER', { w: 0.03, ratio: 0.25, color: '#e6e7ea', weight: 700 }); br.position.set(0, -0.032, 0.0112); g.add(br);
      g.position.set(pos[0], pos[1], pos[2]); g.rotation.set(rot[0], rot[1], rot[2]);
      S.contact(0.11, 0.13, pos[0], pos[2], 0.5);
      S.tickers.push(function (dt) { if (w.on) w.t += dt; w.draw(); });
      w.draw();
      return w;
    };

    // analog meter (ammeter / voltmeter / galvanometer / milliammeter): black bakelite case, printed dial, needle, glass
    S.meter = function (opts) {
      opts = opts || {}; var min = opts.min || 0, max = opts.max === undefined ? 1 : opts.max, zc = !!opts.zeroCentre, unit = opts.unit || 'A';
      var g = new T.Group(); scene.add(g); var sweep = 1.6;
      var body = S.rounded(0.12, 0.1, 0.05, 0.012, M.bakelite); body.rotation.x = -Math.PI / 2 + 0.55; body.position.y = 0.04; g.add(body);
      var face = new T.Group(); face.rotation.x = -Math.PI / 2 + 0.55; face.position.set(0, 0.04, 0); g.add(face);
      var dial = S.canvasTex(512, 384, function (x, w, h) { x.fillStyle = '#f7f4ea'; x.fillRect(0, 0, w, h);
        var cx = w / 2, cy = h * 0.92, R = h * 0.72; x.strokeStyle = '#1b1b1b'; x.fillStyle = '#1b1b1b'; x.lineWidth = 3;
        x.beginPath(); x.arc(cx, cy, R, -Math.PI / 2 - sweep / 2, -Math.PI / 2 + sweep / 2); x.stroke();
        var n = opts.ticks || 10;
        for (var i = 0; i <= n * 5; i++) { var a = -Math.PI / 2 - sweep / 2 + sweep * i / (n * 5), big = i % 5 === 0, len = big ? 26 : 13;
          x.lineWidth = big ? 3 : 1.5; x.beginPath(); x.moveTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); x.lineTo(cx + Math.cos(a) * (R - len), cy + Math.sin(a) * (R - len)); x.stroke();
          if (big) { var v = min + (max - min) * i / (n * 5); x.font = '600 26px "Public Sans", sans-serif'; x.textAlign = 'center';
            x.fillText(String(Math.round(v * 1000) / 1000), cx + Math.cos(a) * (R - 48), cy + Math.sin(a) * (R - 48) + 8); } }
        x.font = '700 64px "Newsreader", Georgia, serif'; x.textAlign = 'center'; x.fillText(opts.symbol || unit, cx, cy - R * 0.35);
        x.font = '500 20px "Public Sans", sans-serif'; x.fillText(opts.caption || '', cx, cy - R * 0.12); });
      var dm = new T.Mesh(new T.PlaneGeometry(0.1, 0.075), new T.MeshStandardMaterial({ map: dial, roughness: 0.6 })); dm.position.set(0, 0.006, 0.0255); face.add(dm);
      var pivot = new T.Group(); pivot.position.set(0, -0.0315, 0.027); face.add(pivot);
      var nd = S.mesh(new T.BoxGeometry(0.0012, 0.054, 0.0006), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.4 }), false); nd.position.y = 0.027; pivot.add(nd);
      var hub = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.002, 16), M.black, false); hub.rotation.x = Math.PI / 2; pivot.add(hub);
      var gl = new T.Mesh(new T.PlaneGeometry(0.104, 0.08), M.glass); gl.position.set(0, 0.006, 0.0285); face.add(gl);
      // terminals: red (+) and black (-)
      var tp = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.012, 20), M.red); tp.position.set(0.035, 0.07, -0.03); g.add(tp);
      var tn = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.012, 20), M.blackPlastic); tn.position.set(-0.035, 0.07, -0.03); g.add(tn);
      g.userData.plus = tp; g.userData.minus = tn;
      var shown = zc ? 0 : min;
      g.set = function (v) { shown = v; };
      S.tickers.push(function (dt) { var target = Math.max(min, Math.min(max, shown)), f = (target - min) / (max - min);
        var ang = -(f - 0.5) * sweep; pivot.rotation.z += (ang - pivot.rotation.z) * Math.min(1, dt * 9); });
      if (opts.pos) g.position.set(opts.pos[0], opts.pos[1], opts.pos[2]); if (opts.rotY) g.rotation.y = opts.rotY;
      S.contact(0.17, 0.14, g.position.x, g.position.z, 0.5);
      return g;
    };

    // mercury thermometer: set(°C)
    S.thermometer = function (opts) {
      opts = opts || {}; var len = opts.len || 0.3, min = opts.min === undefined ? 0 : opts.min, max = opts.max === undefined ? 110 : opts.max;
      var g = new T.Group(); scene.add(g);
      var tubeM = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, len, 20, 1, true), M.glass, false); tubeM.position.y = len / 2; g.add(tubeM);
      var bulb = S.mesh(new T.SphereGeometry(0.0075, 20, 14), new T.MeshStandardMaterial({ color: 0xbcc3c9, roughness: 0.1, metalness: 1 })); g.add(bulb);
      var col = S.mesh(new T.CylinderGeometry(0.0019, 0.0019, 1, 10), new T.MeshStandardMaterial({ color: 0xc4cbd1, roughness: 0.08, metalness: 1 }), false); g.add(col);
      var sc = S.canvasTex(64, 1024, function (x, w, h) { x.fillStyle = '#fbfaf3'; x.fillRect(0, 0, w, h); x.fillStyle = '#222'; x.font = '600 18px sans-serif';
        for (var v = min; v <= max; v++) { var y = h - 30 - (v - min) / (max - min) * (h - 60); var big = v % 10 === 0; x.fillRect(0, y, big ? 22 : (v % 5 === 0 ? 15 : 9), big ? 2.4 : 1.2); if (big) x.fillText(String(v), 26, y + 6); } });
      var plate = new T.Mesh(new T.PlaneGeometry(0.012, len * 0.92), new T.MeshStandardMaterial({ map: sc, roughness: 0.6 })); plate.position.set(0.0075, len * 0.5, -0.001); g.add(plate);
      var cap = S.mesh(new T.SphereGeometry(0.0056, 14, 10, 0, Math.PI * 2, 0, Math.PI / 2), M.glass, false); cap.position.y = len; g.add(cap);
      var base0 = len * 0.04 + 0.006, span = len * 0.92 * ((1024 - 60) / 1024);
      g.set = function (tc) { var f = Math.max(0.002, Math.min(1, (tc - min) / (max - min))), hh = Math.max(0.002, (len * 0.04 + 0.0) + f * span - 0.0);
        col.scale.y = hh; col.position.y = hh / 2 + 0.004; };
      g.set(opts.value === undefined ? 25 : opts.value);
      if (opts.pos) g.position.set(opts.pos[0], opts.pos[1], opts.pos[2]);
      return g;
    };

    // insulated wire with a natural sag between points: wire([p...], 'red') -> {set(points)}
    S.wire = function (points, color) {
      var mat = new T.MeshStandardMaterial({ color: color === 'black' ? 0x1d1d1f : color === 'blue' ? 0x2c5fb4 : color === 'yellow' ? 0xd9a520 : 0xb8322a, roughness: 0.45 });
      var m = S.mesh(new T.BufferGeometry(), mat, true, false); scene.add(m);
      m.set = function (pts) { var v = [];
        for (var i = 0; i < pts.length; i++) { v.push(new T.Vector3(pts[i][0], pts[i][1], pts[i][2]));
          if (i < pts.length - 1) { var a = pts[i], b = pts[i + 1], d = Math.hypot(b[0] - a[0], b[2] - a[2]); v.push(new T.Vector3((a[0] + b[0]) / 2, Math.max(0.004, (a[1] + b[1]) / 2 - d * 0.12), (a[2] + b[2]) / 2)); } }
        m.geometry.dispose(); m.geometry = new T.TubeGeometry(new T.CatmullRomCurve3(v), Math.max(24, v.length * 10), 0.0022, 8, false); };
      m.set(points); return m;
    };
    S.terminal = function (pos, color) { var g = new T.Group(); var b = S.mesh(new T.CylinderGeometry(0.006, 0.007, 0.01, 6), M.brass); b.position.y = 0.005; g.add(b);
      var k = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.006, 16), color === 'red' ? M.red : color === 'black' ? M.blackPlastic : M.brass); k.position.y = 0.013; g.add(k);
      g.position.set(pos[0], pos[1], pos[2]); scene.add(g); return g; };

    // dry cell / battery eliminator box
    S.cell = function (pos, opts) { opts = opts || {}; var g = new T.Group(); scene.add(g);
      var b = S.mesh(new T.CylinderGeometry(0.017, 0.017, 0.06, 32), new T.MeshStandardMaterial({ color: opts.color || 0x1f3b82, roughness: 0.35, metalness: 0.2 })); g.add(b);
      var tp = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.005, 16), M.steel); tp.position.y = 0.0325; g.add(tp);
      var lab2 = S.label(opts.text || '1.5 V', { w: 0.03, ratio: 0.35, color: '#f4f4f4' }); lab2.position.set(0, 0, 0.0172); g.add(lab2);
      g.rotation.z = Math.PI / 2; g.position.set(pos[0], pos[1] + 0.017, pos[2]); S.contact(0.09, 0.05, pos[0], pos[2], 0.45); return g; };
    S.powerBox = function (pos, text) { var g = new T.Group(); scene.add(g);
      var b = S.rounded(0.16, 0.08, 0.1, 0.01, new T.MeshStandardMaterial({ color: 0x3a4f6e, roughness: 0.5 })); b.rotation.x = -Math.PI / 2; b.position.y = 0.05; g.add(b);
      var l = S.label(text || 'DC SUPPLY', { w: 0.1, ratio: 0.2, color: '#f2f2f2' }); l.position.set(0, 0.06, 0.0405); g.add(l);
      g.userData.plus = S.terminal([pos[0] + 0.04, 0.1, pos[2]], 'red'); g.userData.minus = S.terminal([pos[0] - 0.04, 0.1, pos[2]], 'black');
      var knob = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.01, 24), M.black); knob.rotation.x = Math.PI / 2; knob.position.set(0, 0.035, 0.05); g.add(knob); g.userData.knob = knob;
      g.position.set(pos[0], 0, pos[2]); S.contact(0.24, 0.16, pos[0], pos[2], 0.5); return g; };

    // plug key: set(closed)
    S.plugKey = function (pos) { var g = new T.Group(); scene.add(g);
      var b = S.rounded(0.06, 0.04, 0.016, 0.004, M.bakelite); b.rotation.x = -Math.PI / 2; b.position.y = 0.008; g.add(b);
      [-0.016, 0.016].forEach(function (x) { var p = S.mesh(new T.BoxGeometry(0.018, 0.006, 0.026), M.brass); p.position.set(x, 0.019, 0); g.add(p); });
      var plug = new T.Group(); var pb = S.mesh(new T.CylinderGeometry(0.0045, 0.003, 0.016, 16), M.brass); plug.add(pb);
      var ph = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.012, 20), M.blackPlastic); ph.position.y = 0.013; plug.add(ph); g.add(plug);
      g.set = function (on) { plug.position.set(on ? 0 : 0.045, on ? 0.024 : 0.012, on ? 0 : 0.01); plug.rotation.z = on ? 0 : Math.PI / 2; };
      g.set(false); g.userData.plug = plug; g.position.set(pos[0], pos[1], pos[2]); S.contact(0.09, 0.06, pos[0], pos[2], 0.45); return g; };

    // rheostat: setFraction(0..1) moves the sliding contact
    S.rheostat = function (pos, len) { len = len || 0.24; var g = new T.Group(); scene.add(g);
      [-1, 1].forEach(function (s) { var e = S.rounded(0.03, 0.05, 0.02, 0.004, M.iron); e.position.set(s * len / 2, 0.025, 0); g.add(e); });
      var coilTex = S.canvasTex(512, 64, function (x, w, h) { x.fillStyle = '#c9b07a'; x.fillRect(0, 0, w, h); x.strokeStyle = '#7b5a23'; x.lineWidth = 2; for (var i = 0; i < w; i += 5) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i + 3, h); x.stroke(); } });
      var tubeG = S.mesh(new T.CylinderGeometry(0.018, 0.018, len, 32), new T.MeshStandardMaterial({ map: coilTex, roughness: 0.4, metalness: 0.5 })); tubeG.rotation.z = Math.PI / 2; tubeG.position.y = 0.032; g.add(tubeG);
      var bar = S.mesh(new T.BoxGeometry(len, 0.006, 0.006), M.chrome); bar.position.set(0, 0.062, 0); g.add(bar);
      var slider = new T.Group(); var sb = S.rounded(0.02, 0.026, 0.02, 0.004, M.blackPlastic); slider.add(sb); g.add(slider);
      g.setFraction = function (f) { slider.position.set(-len / 2 + 0.02 + f * (len - 0.04), 0.058, 0); };
      g.setFraction(0.5); g.userData.slider = slider;
      g.position.set(pos[0], pos[1], pos[2]); S.contact(len + 0.08, 0.08, pos[0], pos[2], 0.45); return g; };

    // resistance box: show(value) pulls the plugs that make up `value`
    S.resistanceBox = function (pos) { var g = new T.Group(); scene.add(g);
      var b = S.rounded(0.16, 0.08, 0.05, 0.006, M.darkWood); b.rotation.x = -Math.PI / 2; b.position.y = 0.025; g.add(b);
      var topP = S.mesh(new T.BoxGeometry(0.15, 0.004, 0.07), M.bakelite); topP.position.y = 0.051; g.add(topP);
      var vals = [1, 2, 2, 5, 10, 20, 20, 50], plugs = [];
      vals.forEach(function (v, i) { var p = new T.Group(); var pb = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.012, 12), M.brass); p.add(pb);
        var ph = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 0.01, 16), M.blackPlastic); ph.position.y = 0.01; p.add(ph);
        p.position.set(-0.063 + i * 0.018, 0.058, 0); g.add(p); plugs.push(p);
        var lb = S.label(String(v), { w: 0.012, ratio: 0.6, color: '#f0e6c8' }); lb.rotation.x = -Math.PI / 2; lb.position.set(-0.063 + i * 0.018, 0.0535, 0.022); g.add(lb); });
      g.show = function (value) { var left = Math.round(value), out = vals.map(function () { return false; });
        for (var i = vals.length - 1; i >= 0; i--) if (vals[i] <= left) { out[i] = true; left -= vals[i]; }
        plugs.forEach(function (p, i) { p.position.y = out[i] ? 0.075 : 0.058; p.rotation.z = out[i] ? 0.5 : 0; }); };
      g.show(0); g.position.set(pos[0], pos[1], pos[2]); S.contact(0.22, 0.12, pos[0], pos[2], 0.5); return g; };

    // optical bench: a long iron bed with a printed scale; S.upright(bench, x) gives a holder you can slide
    S.opticalBench = function (opts) { opts = opts || {}; var len = opts.len || 1.2, x0 = opts.x0 || -0.6, z = opts.z || 0; var g = new T.Group(); scene.add(g);
      var bed = S.mesh(new T.BoxGeometry(len, 0.02, 0.06), M.iron); bed.position.set(x0 + len / 2, 0.03, z); g.add(bed);
      [x0 + 0.04, x0 + len - 0.04].forEach(function (lx) { var leg = S.rounded(0.04, 0.03, 0.08, 0.006, M.iron); leg.rotation.x = -Math.PI / 2; leg.position.set(lx, 0.01, z); g.add(leg); });
      var sTex = S.canvasTex(4096, 96, function (x, w, h) { x.fillStyle = '#f0ead8'; x.fillRect(0, 0, w, h); x.fillStyle = '#1a1a1a'; var cm = Math.round(len * 100), k = w / cm;
        for (var i = 0; i <= cm; i++) { var xx = i * k, big = i % 10 === 0; x.fillRect(xx, 0, big ? 3 : 1.5, big ? 40 : (i % 5 === 0 ? 28 : 16)); if (big) { x.font = '600 34px sans-serif'; x.fillText(String((opts.start || 0) + i), xx + 4, 80); } } });
      var strip = new T.Mesh(new T.PlaneGeometry(len, 0.022), new T.MeshStandardMaterial({ map: sTex, roughness: 0.6 })); strip.rotation.x = -Math.PI / 2; strip.position.set(x0 + len / 2, 0.0405, z + 0.018); g.add(strip);
      S.contact(len + 0.1, 0.12, x0 + len / 2, z, 0.5); return g; };
    S.upright = function (z, height) { var g = new T.Group(); scene.add(g);
      var sad = S.rounded(0.03, 0.03, 0.07, 0.004, M.alu); sad.rotation.x = -Math.PI / 2; sad.position.y = 0.045; g.add(sad);
      var post = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, height || 0.12, 20), M.chrome); post.position.y = 0.05 + (height || 0.12) / 2; g.add(post);
      var knob = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.01, 6), M.black); knob.rotation.x = Math.PI / 2; knob.position.set(0, 0.045, 0.04); g.add(knob);
      g.position.z = z || 0; g.userData.top = 0.05 + (height || 0.12); return g; };

    S.tuningFork = function (pos, freq) { var g = new T.Group(); scene.add(g);
      [-1, 1].forEach(function (s) { var p = S.mesh(new T.BoxGeometry(0.006, 0.12, 0.006), M.steel); p.position.set(s * 0.011, 0.11, 0); g.add(p); g.userData['prong' + s] = p; });
      var u = S.mesh(new T.TorusGeometry(0.011, 0.003, 10, 20, Math.PI), M.steel); u.rotation.z = Math.PI; u.position.y = 0.05; g.add(u);
      var st = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.05, 12), M.steel); st.position.y = 0.025; g.add(st);
      var l = S.label(String(freq || 512) + ' Hz', { w: 0.03, ratio: 0.25, color: '#333' }); l.position.set(0.016, 0.1, 0.0035); l.rotation.z = Math.PI / 2; g.add(l);
      g.vibrate = function (a) { g.userData.amp = a; };
      S.tickers.push(function () { var a = g.userData.amp || 0, s = Math.sin(performance.now() / 6) * a * 0.002; g.userData['prong-1'].position.x = -0.011 - s; g.userData['prong1'].position.x = 0.011 + s; });
      g.position.set(pos[0], pos[1], pos[2]); return g; };
  }

  /* ================================================================================================== the gloved hand */
  function hand(S) {
    var M = S.M, T3 = T;
    var h = new T3.Group(), palm = new T3.Group(); h.add(palm);
    var p = S.mesh(new T3.CapsuleGeometry(0.03, 0.035, 8, 20), M.glove); p.scale.set(1.15, 1, 0.42); palm.add(p);
    var cuff = S.mesh(new T3.CylinderGeometry(0.034, 0.038, 0.06, 28), M.cuff); cuff.position.y = -0.065; palm.add(cuff);
    var sleeve = S.mesh(new T3.CylinderGeometry(0.04, 0.046, 0.3, 28), M.cuff); sleeve.position.y = -0.24; palm.add(sleeve);
    var fingers = [];
    [[0.021, 0.054, 0.028], [0.0072, 0.057, 0.03], [-0.0072, 0.054, 0.028], [-0.021, 0.047, 0.023]].forEach(function (sp) {
      var segs = [], parent = palm;
      for (var s = 0; s < 3; s++) { var j = new T3.Group(); j.position.set(s ? 0 : sp[0], s ? sp[2] * (s === 1 ? 1 : 0.8) : sp[1], 0); parent.add(j);
        var L = sp[2] * (s === 0 ? 1 : s === 1 ? 0.8 : 0.65), seg = S.mesh(new T3.CapsuleGeometry(0.0078 - s * 0.0008, L, 6, 14), M.glove); seg.position.y = L / 2; j.add(seg); segs.push(j); parent = j; }
      fingers.push(segs); });
    var th = [], tp = palm;
    [[0.032, 0.0, 0.006], [0, 0.026, 0], [0, 0.02, 0]].forEach(function (v, s) { var j = new T3.Group(); j.position.set(v[0], v[1], v[2]); tp.add(j);
      var L = s ? 0.015 : 0.02, seg = S.mesh(new T3.CapsuleGeometry(0.0086 - s * .0008, L, 6, 14), M.glove); seg.position.y = L / 2; j.add(seg); th.push(j); tp = j; });
    h.visible = false; S.scene.add(h);
    var POSES = { open: [[0.1, 0.1, 0.12, 0.15], 0.05, 0.3], relaxed: [[0.25, 0.3, 0.35, 0.4], 0.15, 0.3], pinch: [[0.8, 0.9, 1.0, 1.05], 0.65, 0],
      point: [[0.0, 1.2, 1.2, 1.2], 0.9, 0], grip: [[1.1, 1.2, 1.2, 1.2], 0.9, 0] };
    var cur = { curl: POSES.relaxed[0].slice(), th: POSES.relaxed[1], spread: POSES.relaxed[2] };
    function apply() { fingers.forEach(function (f, i) { f[0].rotation.set(cur.curl[i] * 1.2, 0, (i - 1.5) * cur.spread * 0.12); f[1].rotation.x = cur.curl[i] * 1.4; f[2].rotation.x = cur.curl[i] * 1.1; });
      th[0].rotation.set(cur.th * 0.5, 0, -0.9 + cur.th * 0.45); th[1].rotation.x = cur.th * 0.9; th[2].rotation.x = cur.th * 0.8; }
    apply();
    // orientations: where the fingertips point (side = from the right, pointing left; top = from above, pointing down; tap = finger down onto a button)
    var ORIENT = { side: [0.15, -0.25, 1.32], top: [Math.PI - 0.25, 0, 0.1], tap: [-1.0, -0.4, 0.35], front: [-1.35, 0, 0] };
    // offset from the hand's origin to the working point (fingertip pinch / index tip), in world space for each orientation
    var TIP = { side: new T3.Vector3(-0.084, -0.016, -0.016), top: new T3.Vector3(0.01, -0.09, 0.0), tap: new T3.Vector3(-0.012, -0.075, -0.03), front: new T3.Vector3(0, 0.0, -0.09) };
    var HOME = new T3.Vector3(0.6, 0.6, 0.6);
    var api = S.hand = { group: h, busy: false };
    function at(point, mode) { return point.clone().sub(TIP[mode]); }
    api.shape = function (name, ms) { var from = { curl: cur.curl.slice(), th: cur.th, spread: cur.spread }, to = POSES[name];
      return S.tween(ms || 300, function (k) { for (var i = 0; i < 4; i++) cur.curl[i] = from.curl[i] + (to[0][i] - from.curl[i]) * k; cur.th = from.th + (to[1] - from.th) * k; cur.spread = from.spread + (to[2] - from.spread) * k; apply(); }); };
    // reach: bring the working point to `point` (Vector3) with an orientation; from home if hidden
    api.reach = function (point, mode, ms) { mode = mode || 'side'; var o = ORIENT[mode];
      if (!h.visible) { h.visible = true; h.position.copy(at(point, mode).add(new T3.Vector3(0.18, 0.12, 0.18))); }
      var r0 = h.rotation.clone(), p0 = h.position.clone(), p1 = at(point, mode);
      return S.tween(ms || 700, function (k) { h.position.lerpVectors(p0, p1, k); h.rotation.set(r0.x + (o[0] - r0.x) * k, r0.y + (o[1] - r0.y) * k, r0.z + (o[2] - r0.z) * k); }); };
    // follow: keep the working point on a moving target for `ms` (k -> Vector3)
    api.follow = function (fn, mode, ms, onK) { mode = mode || 'side'; return S.tween(ms || 800, function (k) { h.position.copy(at(fn(k), mode)); if (onK) onK(k); }); };
    api.away = function (ms) { var p0 = h.position.clone(), p1 = p0.clone().add(new T3.Vector3(0.22, 0.16, 0.26));
      return S.tween(ms || 600, function (k) { h.position.lerpVectors(p0, p1, k); }).then(function () { h.visible = false; }); };
    // common human actions
    api.tap = function (obj, mode) { if (S.fast || RM) return Promise.resolve(); var w = new T3.Vector3(); obj.getWorldPosition(w); w.y += 0.006;
      api.busy = true; return api.shape('point', 1).then(function () { return api.reach(w.clone().add(new T3.Vector3(0, 0.03, 0)), mode || 'tap', 380); })
        .then(function () { return api.reach(w, mode || 'tap', 120); }).then(function () { S.click(); return api.reach(w.clone().add(new T3.Vector3(0, 0.03, 0)), mode || 'tap', 120); })
        .then(function () { return api.away(420); }).then(function () { api.busy = false; }); };
    // pinch an object at a point, move it along fn(k) while onK(k) updates the physics, then let go
    api.pinchMove = function (startPt, fn, onK, opts) { opts = opts || {}; var mode = opts.mode || 'side';
      if (S.fast || RM) { onK(1); return Promise.resolve(); }
      api.busy = true;
      return api.shape('relaxed', 1).then(function () { return api.reach(startPt, mode, opts.reachMs || 800); }).then(function () { return api.shape(opts.pose || 'pinch', 320); })
        .then(function () { return api.follow(fn, mode, opts.ms || 1000, onK); }).then(function () { return S.tween(opts.hold || 300, function () {}); })
        .then(function () { if (opts.release !== false) return api.shape('relaxed', 260); })
        .then(function () { return api.away(); }).then(function () { api.busy = false; }); };
    api.HOME = HOME;
  }

  /* ================================================================================================== camera, tweens, picking, render loop */
  function camera_controls(S) {
    var camera = S.camera, renderer = S.renderer, stage = S.stage, scene = S.scene;
    var tweens = [];
    S.tween = function (ms, fn) { if (S.fast || RM) { fn(1); return Promise.resolve(); }
      return new Promise(function (res) { tweens.push({ t0: performance.now(), ms: ms, fn: fn, res: res }); }); };
    function ease(k) { return k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2; }
    S.wait = function (ms) { return new Promise(function (r) { setTimeout(r, S.fast ? 0 : ms); }); };
    // run the experiment's own physics forward by `sec` seconds (tests + 'fast' mode); until(fn) stops early
    S.advance = function (sec, until) { var n = Math.ceil(sec / 0.005); for (var i = 0; i < n; i++) { if (S.exp && S.exp.tick) S.exp.tick(0.005); S.tickers.forEach(function (f) { f(0.005); }); if (until && until()) return true; } return false; };
    var target = S.target = new T.Vector3();
    S.home = { pos: new T.Vector3(0.78, 1.0, 1.75), look: new T.Vector3(-0.05, 0.55, -0.15) };
    camera.position.copy(S.home.pos); camera.lookAt(S.home.look); target.copy(S.home.look);
    S.fly = function (pos, look, ms) { if (S._fly) S._fly.dead = true; var me = S._fly = { dead: false }; var p0 = camera.position.clone(), l0 = target.clone(), p1 = Array.isArray(pos) ? new T.Vector3().fromArray(pos) : pos, l1 = Array.isArray(look) ? new T.Vector3().fromArray(look) : look;
      return S.tween(ms || 1000, function (k) { if (me.dead) return; camera.position.lerpVectors(p0, p1, k); target.lerpVectors(l0, l1, k); camera.lookAt(target); }); };   // a newer fly wins
    S.views = {};
    S.focus = function (k) { var v = S.views[k]; if (v) S.fly(v[0], v[1]); S.flash(k); };
    var flashUntil = 0, flashKey = '';
    S.flash = function (k) { flashKey = k; flashUntil = performance.now() + 1600; };
    S.addApparatus = function (k, group, name, info) { S.groups[k] = group; S.apparatus.push({ k: k, name: name, info: info }); };

    var ray = new T.Raycaster(), ndc = new T.Vector2(), cvs = renderer.domElement, ptrs = new Map(), drag = null, last = null, moved = 0, pinch = 0;
    S.ray = ray;
    function setNdc(e) { var r = cvs.getBoundingClientRect(); ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1); ray.setFromCamera(ndc, camera); }
    S.draggables = [];   // {objects:[mesh], start(e,ray)->bool, move(ray), end()}
    cvs.addEventListener('pointerdown', function (e) { ptrs.set(e.pointerId, [e.clientX, e.clientY]); last = [e.clientX, e.clientY]; moved = 0; cvs.setPointerCapture(e.pointerId); drag = null;
      setNdc(e); for (var i = 0; i < S.draggables.length; i++) { var d = S.draggables[i]; if ((!d.enabled || d.enabled()) && ray.intersectObjects(d.objects, true).length && !S.hand.busy) { drag = d; break; } } });
    cvs.addEventListener('pointermove', function (e) {
      if (!ptrs.has(e.pointerId)) return;
      if (ptrs.size === 2) { ptrs.set(e.pointerId, [e.clientX, e.clientY]); var vs = Array.from(ptrs.values()), dd = Math.hypot(vs[0][0] - vs[1][0], vs[0][1] - vs[1][1]); if (pinch) zoom(pinch / dd); pinch = dd; moved = 99; return; }
      var dx = e.clientX - last[0], dy = e.clientY - last[1]; moved += Math.abs(dx) + Math.abs(dy); last = [e.clientX, e.clientY]; ptrs.set(e.pointerId, last);
      if (drag) { setNdc(e); drag.move(ray); return; }
      var off = camera.position.clone().sub(target), sp = new T.Spherical().setFromVector3(off);
      sp.theta -= dx * 0.006; sp.phi = Math.min(1.45, Math.max(0.25, sp.phi - dy * 0.006)); off.setFromSpherical(sp); camera.position.copy(target).add(off); camera.lookAt(target); });
    function zoom(f) { var off = camera.position.clone().sub(target); off.setLength(Math.min(2.6, Math.max(0.015, off.length() * f))); camera.position.copy(target).add(off); }   // 0.015: small instruments need close views
    function up(e) { if (!ptrs.has(e.pointerId)) return; ptrs.delete(e.pointerId); pinch = 0; if (drag) { if (drag.end) drag.end(); drag = null; return; } if (moved < 6) pick(e); }
    cvs.addEventListener('pointerup', up); cvs.addEventListener('pointercancel', function (e) { ptrs.delete(e.pointerId); pinch = 0; drag = null; });
    cvs.addEventListener('wheel', function (e) { e.preventDefault(); zoom(e.deltaY > 0 ? 1.08 : 0.92); }, { passive: false });
    var tag = el('div', 'tag'); tag.hidden = true; stage.appendChild(tag); var tagFor = null;
    S.clickables = [];   // {object, fn}
    function pick(e) { setNdc(e);
      for (var i = 0; i < S.clickables.length; i++) { var c = S.clickables[i]; if (ray.intersectObject(c.object, true).length) { c.fn(); return; } }
      for (var j = 0; j < S.apparatus.length; j++) { var a = S.apparatus[j], g = S.groups[a.k]; if (!g) continue;
        if (ray.intersectObject(g, true).length) { S.showTag(a); return; } }
      tag.hidden = true; tagFor = null; }
    S.showTag = function (a) { tag.textContent = a.name + ' — ' + a.info; tag.hidden = false; tagFor = S.groups[a.k]; S.flash(a.k); };
    S.hideTag = function () { tag.hidden = true; tagFor = null; };
    function resize() { var w = stage.clientWidth, h = stage.clientHeight; if (!w || !h) return; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }
    window.addEventListener('resize', resize); S.resize = resize; setTimeout(resize, 0);
    var prev = performance.now();
    function frame(now) {
      if (S.dead) return;                            // stopped: do not render or reschedule
      var dt = Math.min(0.05, (now - prev) / 1000); prev = now;
      for (var i = tweens.length - 1; i >= 0; i--) { var tw = tweens[i], k = Math.min(1, (now - tw.t0) / tw.ms); tw.fn(ease(k)); if (k >= 1) { tweens.splice(i, 1); tw.res(); } }
      if (!S.fast) try { if (S.exp && S.exp.tick) S.exp.tick(dt); } catch (err) { if (!S._tickErr) { S._tickErr = 1; console.error(err); S.say('Something went wrong in the simulation: ' + err.message); } }
      if (!S.fast) S.tickers.forEach(function (f) { f(dt); });
      if (S.liveUpdate) S.liveUpdate();
      var pulse = now < flashUntil ? 0.35 + 0.35 * Math.sin(now / 90) : 0;
      S.apparatus.forEach(function (a) { var g = S.groups[a.k]; if (!g) return; var on = a.k === flashKey ? pulse : 0; if (!on && !g.userData.lit) return; g.userData.lit = !!on;
        g.traverse(function (o) { if (o.isMesh && o.material && o.material.emissive) { if (!o.userData.own) { o.material = o.material.clone(); o.userData.own = true; } o.material.emissive.setRGB(on * .55, on * .42, on * .08); } }); });
      if (tagFor && !tag.hidden) { var pp = new T.Vector3(); new T.Box3().setFromObject(tagFor).getCenter(pp); pp.project(camera);
        tag.style.left = ((pp.x + 1) / 2 * stage.clientWidth) + 'px'; tag.style.top = ((1 - pp.y) / 2 * stage.clientHeight) + 'px'; }
      renderer.render(scene, camera);
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    var actx = null;
    S.click = function (freq, dur, vol) { try { actx = actx || new (window.AudioContext || window.webkitAudioContext)(); var o = actx.createOscillator(), g = actx.createGain();
      o.type = 'square'; o.frequency.value = freq || 2200; g.gain.setValueAtTime(vol === undefined ? 0.12 : vol, actx.currentTime); g.gain.exponentialRampToValueAtTime(0.0001, actx.currentTime + (dur || 0.03));
      o.connect(g).connect(actx.destination); o.start(); o.stop(actx.currentTime + (dur || 0.03)); } catch (e) { /* sound is optional */ } };
    var toastTimer = 0;
    S.say = function (text) { var t = $('#toast', stage); if (!t) { t = el('div', 'toast'); t.id = 'toast'; t.setAttribute('role', 'status'); stage.appendChild(t); }
      t.textContent = text; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.hidden = true; }, 4500); if (S.askNote) S.askNote(text); };
    // HUD cards: S.hudCard(label) -> {set(text)}
    S.hudCard = function (label) { var c = el('div', 'card', label); var n = el('div', 'num', '—'); c.appendChild(n); S.hud.appendChild(c); return { set: function (t) { if (n.textContent !== t) n.textContent = t; } }; };
    // drag helper: a point on the plane through `origin` with normal `normal`
    S.rayPlane = function (rayc, origin, normal) { var p = new T.Vector3(); return rayc.ray.intersectPlane(new T.Plane().setFromNormalAndCoplanarPoint(normal, origin), p) ? p : null; };
  }

  /* ================================================================================================== the lab record book */
  function record_book(S) {
    var c = document.createElement('canvas'); c.width = 1400; c.height = 1000;
    var tex = new T.CanvasTexture(c); tex.encoding = T.sRGBEncoding; tex.anisotropy = 8;
    var g = new T.Group(); S.scene.add(g);
    var cover = S.mesh(new T.BoxGeometry(0.43, 0.004, 0.3), new T.MeshStandardMaterial({ color: 0x2c3e6b, roughness: 0.7 })); cover.position.y = 0.002; g.add(cover);
    var pm = new T.MeshStandardMaterial({ map: tex, roughness: 0.92 });
    var pages = S.mesh(new T.BoxGeometry(0.42, 0.008, 0.29), [S.M.white, S.M.white, pm, S.M.white, S.M.white, S.M.white]); pages.position.y = 0.008; g.add(pages);
    var pencil = new T.Group(); var pb = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.15, 6), new T.MeshStandardMaterial({ color: 0xe8b024, roughness: 0.5 })); pb.rotation.z = Math.PI / 2; pencil.add(pb);
    var pt = S.mesh(new T.ConeGeometry(0.0035, 0.014, 12), S.M.wood); pt.rotation.z = -Math.PI / 2; pt.position.x = 0.082; pencil.add(pt); S.scene.add(pencil);
    S.book = { group: g, pencil: pencil, place: function (x, z, ry) { g.position.set(x, 0, z); g.rotation.y = ry || 0.12; pencil.position.set(x + 0.27, 0.0036, z + 0.12); pencil.rotation.y = -0.4; S.contact(0.5, 0.36, x, z, 0.45); } };
    S.book.place(-0.5, 0.08, 0.12);
    S.book.draw = function () {
      var x = c.getContext('2d'), W = 1400, H = 1000, HAND = '"Caveat", "Comic Sans MS", cursive', exp = S.exp || {}, bk = exp.book || {}, rows = S.rows;
      x.fillStyle = '#f6f1e3'; x.fillRect(0, 0, W, H);
      var gg = x.createLinearGradient(W / 2 - 60, 0, W / 2 + 60, 0); gg.addColorStop(0, 'rgba(0,0,0,0)'); gg.addColorStop(.5, 'rgba(0,0,0,.18)'); gg.addColorStop(1, 'rgba(0,0,0,0)'); x.fillStyle = gg; x.fillRect(W / 2 - 60, 0, 120, H);
      x.strokeStyle = 'rgba(70,110,170,.28)'; x.lineWidth = 2; for (var y = 120; y < H; y += 46) { x.beginPath(); x.moveTo(30, y); x.lineTo(W / 2 - 30, y); x.moveTo(W / 2 + 30, y); x.lineTo(W - 30, y); x.stroke(); }
      x.strokeStyle = 'rgba(200,70,70,.45)'; x.beginPath(); x.moveTo(110, 40); x.lineTo(110, H - 20); x.moveTo(W / 2 + 110, 40); x.lineTo(W / 2 + 110, H - 20); x.stroke();
      x.fillStyle = '#1f3a8a'; x.font = '700 54px ' + HAND; x.fillText(bk.title || S.lab.title, 130, 100, W / 2 - 160);
      x.font = '500 38px ' + HAND; (bk.lines || []).slice(0, 15).forEach(function (t, i) { x.fillText(t, 130, 162 + i * 46, W / 2 - 160); });
      x.font = '700 44px ' + HAND; x.fillText('Observation table', W / 2 + 130, 100);
      var cols = bk.columns || [], n = Math.max(1, cols.length), span = (W / 2 - 160) / n;
      x.font = '600 32px ' + HAND; cols.forEach(function (cc, i) { x.fillText(cc.label, W / 2 + 130 + i * span, 158, span - 10); });
      x.strokeStyle = 'rgba(31,58,138,.6)'; x.beginPath(); x.moveTo(W / 2 + 120, 170); x.lineTo(W - 40, 170); x.stroke();
      x.font = '500 38px ' + HAND; var sd = 5;
      rows.slice(0, 15).forEach(function (r, ri) { var yy = 214 + ri * 46; cols.forEach(function (cc, i) { var v; try { v = cc.get(r, ri); } catch (e) { v = ''; }
        x.save(); x.translate(W / 2 + 130 + i * span, yy); sd = (sd * 16807) % 2147483647; x.rotate(((sd / 2147483647) - .5) * .03); x.fillText(String(v), 0, 0, span - 10); x.restore(); }); });
      var res = S.result && S.result();
      if (res && isFinite(res.value)) { var ry = 214 + Math.min(rows.length, 12) * 46 + 40; x.font = '700 44px ' + HAND; x.fillStyle = '#7a1f1f';
        var txt = res.label + ' = ' + fmt(res.value, res.digits) + ' ' + (res.unit || ''); x.fillText(txt, W / 2 + 140, ry);
        x.strokeStyle = '#7a1f1f'; x.lineWidth = 3; x.strokeRect(W / 2 + 126, ry - 44, Math.min(W / 2 - 160, x.measureText(txt).width + 30), 62); }
      tex.needsUpdate = true; };
    if (document.fonts && document.fonts.load) document.fonts.load('40px "Caveat"').then(function () { S.book.draw(); }).catch(function () {});
  }

  function fmt(v, d) { if (!isFinite(v)) return '—'; var a = Math.abs(v); if (d === undefined) d = a >= 100 ? 1 : a >= 10 ? 2 : a >= 1 ? 3 : 4; var o = v.toFixed(d); return /^-0(\.0*)?$/.test(o) ? o.slice(1) : o; }

  /* ================================================================================================== workflow: theory -> steps -> result -> viva */
  function workflow(S, lab, exp) {
    S.fmt = fmt;
    S.views = Object.assign(S.views, exp.views || {});
    if (exp.camera) { S.home = { pos: new T.Vector3().fromArray(exp.camera.pos), look: new T.Vector3().fromArray(exp.camera.look) }; S.camera.position.copy(S.home.pos); S.target.copy(S.home.look); S.camera.lookAt(S.target); }
    if (exp.book && exp.book.at) S.book.place(exp.book.at[0], exp.book.at[1], exp.book.at[2]);
    S.result = function () { try { return exp.result ? exp.result(S.rows) : null; } catch (e) { return null; } };
    S.book.draw();
    var steps = [{ id: 'theory', title: 'Theory', theory: true }].concat(exp.steps || []).concat([{ id: 'result', title: 'Result', result: true }, { id: 'viva', title: 'Viva', viva: true }]);
    S.steps = steps; S.step = 0; S.maxStep = 0;
    S.go = function (i) { if (i > S.maxStep) return; S.step = i; var st = steps[i]; drawSteps(); S.render();
      if (st.view) S.focus(st.view); else if (st.result) S.focus('book'); else if (i === 0) S.fly(S.home.pos, S.home.look);
      if (st.enter) st.enter(S); };
    S.unlock = function (i) { S.maxStep = Math.max(S.maxStep, Math.min(i, steps.length - 1)); drawSteps(); };
    S.next = function () { var i = S.step + 1; S.unlock(i); S.go(i); };
    S.addRow = function (row) { S.rows.push(row); S.book.draw(); S.render(); };
    S.removeRow = function (i) { S.rows.splice(i, 1); S.book.draw(); S.render(); };
    function drawSteps() { S.stepsNav.innerHTML = '';
      steps.forEach(function (st, i) { var b = el('button', i < S.maxStep ? 'done' : '', (i + 1) + '. ' + st.title); b.type = 'button'; b.disabled = i > S.maxStep;
        if (i === S.step) b.setAttribute('aria-current', 'step'); b.addEventListener('click', function () { S.go(i); }); S.stepsNav.appendChild(b); });
      S.stepPill.textContent = 'Step ' + (S.step + 1) + ' of ' + steps.length + ' · ' + steps[S.step].title; }

    // ---------- UI kit handed to each step's render(ui, S)
    var lives = [];
    S.liveUpdate = function () { lives.forEach(function (l) { var t = l.fn(); if (l.el.textContent !== t) l.el.textContent = t; }); };
    function ui(pane) { return {
      h2: function (t) { pane.appendChild(el('h2', '', t)); }, h3: function (t) { pane.appendChild(el('h3', '', t)); }, p: function (t) { pane.appendChild(el('p', '', t)); },
      note: function (t) { var n = el('div', 'note', t); pane.appendChild(n); return n; },
      formula: function (f, small) { var d = el('div', 'formula', f); if (small) d.appendChild(el('small', '', small)); pane.appendChild(d); },
      button: function (t, fn, pri, disabled) { var b = el('button', 'btn' + (pri ? ' pri' : ''), t); b.type = 'button'; b.disabled = !!disabled; b.addEventListener('click', function () { if (!b.disabled) fn(); }); return b; },
      row: function () { var r = el('div', 'row'); for (var i = 0; i < arguments.length; i++) if (arguments[i]) r.appendChild(arguments[i]); pane.appendChild(r); return r; },
      slider: function (label, min, max, step, get, set, unit, digits) { var l = el('label', 'slider'), h = el('div', 'h'), v = el('span', 'v'); h.appendChild(el('span', '', label)); h.appendChild(v); l.appendChild(h);
        var inp = el('input'); inp.type = 'range'; inp.min = min; inp.max = max; inp.step = step; inp.value = get(); inp.id = 'sl_' + label.replace(/\W+/g, '_');
        var dg = digits === undefined ? ((String(step).split('.')[1] || '').length) : digits;
        function show() { v.textContent = fmt(Number(inp.value), dg) + (unit ? ' ' + unit : ''); }
        inp.addEventListener('input', function () { set(Number(inp.value)); show(); }); show(); l.appendChild(inp); pane.appendChild(l);
        l.setValue = function (x) { inp.value = x; set(Number(x)); show(); }; return l; },
      task: function (title, done, status) { var b = el('div', 'task' + (done ? ' ok' : '')); b.appendChild(el('div', 't', title)); var st = el('div', 'st', (done ? '✓ ' : '') + status); pane.appendChild(b);
        b.add = function (x) { b.insertBefore(x, st); return b; }; b.appendChild(st); return b; },
      live: function (fn, cls) { var d = el('div', cls || 'live', ''); pane.appendChild(d); lives.push({ el: d, fn: fn }); d.textContent = fn(); return d; },
      table: function () { pane.appendChild(table()); },
      input: function (label, get, set, unit) {   // a typed reading (vernier, screw gauge...)
        var l = el('label', 'slider'), h = el('div', 'h'); h.appendChild(el('span', '', label)); if (unit) h.appendChild(el('span', 'v', unit)); l.appendChild(h);
        var inp = el('input'); inp.type = 'number'; inp.step = 'any'; inp.inputMode = 'decimal'; inp.id = 'in_' + label.replace(/\W+/g, '_');
        inp.style.cssText = 'border:1px solid var(--line);border-radius:10px;padding:8px 10px;min-height:40px;background:var(--bg);color:var(--ink);font:inherit';
        var v0 = get(); if (v0 !== undefined && v0 !== null && v0 !== '') inp.value = v0;
        inp.addEventListener('input', function () { set(inp.value === '' ? null : Number(inp.value)); }); l.appendChild(inp); pane.appendChild(l); return l; },
      next: function (label, ok) { var b = el('button', 'btn pri', label || 'Next'); b.type = 'button'; b.disabled = ok === false; b.addEventListener('click', function () { if (!b.disabled) S.next(); }); pane.appendChild(el('div', 'row')).appendChild(b); return b; },
      el: function (x) { pane.appendChild(x); return x; },
    }; }
    S.ui = ui;
    function table() { var w = el('div', 'tw'), t = el('table'), hd = el('tr'), cols = (exp.book && exp.book.columns) || [];
      cols.forEach(function (c) { hd.appendChild(el('th', '', c.label)); }); hd.appendChild(el('th', '', '')); t.appendChild(hd);
      if (!S.rows.length) { var tr0 = el('tr'), td0 = el('td', '', 'No readings yet'); td0.colSpan = cols.length + 1; td0.style.textAlign = 'left'; tr0.appendChild(td0); t.appendChild(tr0); }
      S.rows.forEach(function (r, i) { var tr = el('tr'); cols.forEach(function (c) { var v; try { v = c.get(r, i); } catch (e) { v = ''; } tr.appendChild(el('td', '', String(v))); });
        var x = el('button', 'btn', '×'); x.type = 'button'; x.style.minHeight = '28px'; x.style.padding = '0 8px'; x.setAttribute('aria-label', 'Delete reading ' + (i + 1));
        x.addEventListener('click', function () { S.removeRow(i); }); var td = el('td'); td.appendChild(x); tr.appendChild(td); t.appendChild(tr); });
      w.appendChild(t); return w; }

    S.render = function () {
      lives.length = 0; S.pane.innerHTML = ''; var u = ui(S.pane), st = steps[S.step];
      if (st.theory) return theory(u);
      if (st.result) return result(u);
      if (st.viva) return viva(u);
      if (st.render) st.render(u, S);
    };

    function theory(u) {
      var th = exp.theory || {};
      u.h2(lab.title); u.h3('Aim'); u.p(lab.aim);
      var v = lab.variant || {};
      if (v.sample || v.method || v.unknown || v.note) {
        u.h3('This experiment');
        [['Sample', v.sample], ['Method', v.method], ['You will find', v.unknown]].forEach(function (x) { if (x[1]) u.p(x[0] + ': ' + x[1]); });
        if (v.note) u.note(v.note);
      }
      u.h3('Principle'); u.p(th.principle || lab.theory || '');
      if (th.formula) u.formula(th.formula, th.formulaNote);
      (th.more || []).forEach(function (t) { u.p(t); });
      u.h3('Apparatus · tap one to see it on the bench');
      var list = el('div', 'app-list');
      S.apparatus.forEach(function (a) { var b = el('button'); b.type = 'button'; b.appendChild(el('b', '', a.name)); b.appendChild(el('span', '', a.info.split('. ')[0].replace(/\.$/, '') + '.'));
        b.addEventListener('click', function () { S.focus(a.k); S.showTag(a); }); list.appendChild(b); });
      u.el(list);
      if (lab.safety || th.precautions) { u.h3('Precautions'); u.note([th.precautions, lab.safety].filter(Boolean).join(' ')); }
      u.next('Start the experiment');
    }
    function result(u) {
      u.h2('Graph and result');
      u.table();
      var gr = exp.graph;
      if (gr) { var c = el('canvas', 'graph'); c.width = 720; c.height = 420; u.el(c); plot(c, gr); }
      var r = S.result();
      var box = el('div', 'result', r && isFinite(r.value) ? r.label + ' = ' + fmt(r.value, r.digits) + ' ' + (r.unit || '') : 'Record the readings first');
      if (r && isFinite(r.value)) { var sub = r.note || ''; if (r.truth !== undefined && isFinite(r.truth) && r.truth !== 0) sub += (sub ? ' · ' : '') + 'True value in this lab ' + fmt(r.truth, r.digits) + ' ' + (r.unit || '') + ' · your error ' + (Math.abs(r.value - r.truth) / Math.abs(r.truth) * 100).toFixed(1) + '%';
        if (sub) box.appendChild(el('small', '', sub)); }
      u.el(box);
      if (exp.resultNote) u.note(exp.resultNote);
      u.next('Next: viva questions');
    }
    function viva(u) {
      u.h2('Viva voce');
      var qs = (exp.viva || []).concat((lab.questions || []).map(function (q) { return [q.q, q.options, q.answer, q.why]; }));
      S.quiz = S.quiz || {};
      qs.forEach(function (q, qi) { var box = el('div', 'task quiz'); box.appendChild(el('div', 't', q[0]));
        q[1].forEach(function (o, oi) { var b = u.button(o, function () { S.quiz[qi] = oi; S.render(); }); if (S.quiz[qi] !== undefined) { b.disabled = true; if (oi === q[2]) b.classList.add('right'); else if (oi === S.quiz[qi]) b.classList.add('wrong'); } box.appendChild(b); });
        if (S.quiz[qi] !== undefined) box.appendChild(el('div', 'st', (S.quiz[qi] === q[2] ? 'Correct. ' : 'Not quite. ') + (q[3] || '') + (S.quiz[qi] === q[2] ? '' : ' Ask Hoola why.')));
        u.el(box); });
      u.h3('Sources'); (lab.sources || []).forEach(function (s) { u.el(el('div', 'src', s.title + (s.note ? ' — ' + s.note : ''))); });
    }
    function plot(c, gr) {
      var x = c.getContext('2d'), W = c.width, H = c.height, css = getComputedStyle(document.documentElement);
      var ink = css.getPropertyValue('--ink').trim(), mut = css.getPropertyValue('--mut').trim(), line = css.getPropertyValue('--line').trim(), acc = css.getPropertyValue('--accent').trim();
      var pts = S.rows.map(function (r) { return [gr.x(r), gr.y(r)]; }).filter(function (p) { return isFinite(p[0]) && isFinite(p[1]); });
      var P = { l: 78, r: 20, t: 20, b: 60 };
      var xs = pts.map(function (p) { return p[0]; }), ys = pts.map(function (p) { return p[1]; });
      var xmin = gr.x0 !== undefined ? gr.x0 : Math.min.apply(null, xs.concat([0])), xmax = Math.max.apply(null, xs.concat([gr.x1 || 1e-9]));
      var ymin = gr.y0 !== undefined ? gr.y0 : Math.min.apply(null, ys.concat([0])), ymax = Math.max.apply(null, ys.concat([gr.y1 || 1e-9]));
      if (xmax - xmin < 1e-12) xmax = xmin + 1; if (ymax - ymin < 1e-12) ymax = ymin + 1;
      xmax += (xmax - xmin) * 0.08; ymax += (ymax - ymin) * 0.08;
      var X = function (v) { return P.l + (v - xmin) / (xmax - xmin) * (W - P.l - P.r); }, Y = function (v) { return H - P.b - (v - ymin) / (ymax - ymin) * (H - P.t - P.b); };
      x.clearRect(0, 0, W, H); x.strokeStyle = line; x.lineWidth = 1; x.fillStyle = mut; x.font = '19px "Public Sans", sans-serif';
      for (var i = 0; i <= 5; i++) { var xv = xmin + (xmax - xmin) * i / 5, yv = ymin + (ymax - ymin) * i / 5;
        x.beginPath(); x.moveTo(X(xv), Y(ymin)); x.lineTo(X(xv), Y(ymax)); x.stroke(); x.fillText(fmt(xv, 2), X(xv) - 14, H - P.b + 24);
        x.beginPath(); x.moveTo(X(xmin), Y(yv)); x.lineTo(X(xmax), Y(yv)); x.stroke(); x.fillText(fmt(yv, 2), 6, Y(yv) + 6); }
      x.fillStyle = ink; x.fillText(gr.xlabel || '', W - 10 - x.measureText(gr.xlabel || '').width, H - 10);
      x.save(); x.translate(20, P.t + 10 + x.measureText(gr.ylabel || '').width); x.rotate(-Math.PI / 2); x.fillText(gr.ylabel || '', 0, 0); x.restore();
      if (gr.line && pts.length >= 2) { var L = gr.line(pts); if (L) { x.strokeStyle = acc; x.lineWidth = 3; x.beginPath(); for (var k = 0; k <= 40; k++) { var xv2 = xmin + (xmax - xmin) * k / 40, yv2 = L(xv2); if (k) x.lineTo(X(xv2), Y(yv2)); else x.moveTo(X(xv2), Y(yv2)); } x.stroke(); } }
      x.fillStyle = ink; pts.forEach(function (p) { x.beginPath(); x.arc(X(p[0]), Y(p[1]), 7, 0, Math.PI * 2); x.fill(); });
    }
    // standard fits handed to experiments
    S.fit = {
      origin: function (pts) { var sxy = 0, sxx = 0; pts.forEach(function (p) { sxy += p[0] * p[1]; sxx += p[0] * p[0]; }); return sxx ? sxy / sxx : NaN; },
      linear: function (pts) { var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0; pts.forEach(function (p) { sx += p[0]; sy += p[1]; sxy += p[0] * p[1]; sxx += p[0] * p[0]; });
        var d = n * sxx - sx * sx; if (!d) return null; var m = (n * sxy - sx * sy) / d; return { m: m, c: (sy - m * sx) / n }; },
      mean: function (xs) { return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : NaN; },
    };

    // ---------- Ask Hoola dock
    askHoola(S, lab, exp);

    // ---------- go
    (exp.apparatus || []).forEach(function () {});
    drawSteps(); S.render();
    if (exp.ready) exp.ready(S);
  }

  /* ================================================================================================== Ask Hoola */
  function askHoola(S, lab, exp) {
    var stage = S.stage;
    var btn = el('button', 'askbtn', 'Ask Hoola about this experiment'); btn.type = 'button'; stage.appendChild(btn);
    var dock = el('section', 'dock'); dock.hidden = true; dock.setAttribute('aria-label', 'Ask Hoola'); stage.appendChild(dock);
    var hd = el('header'); hd.appendChild(el('b', '', 'Ask Hoola')); hd.appendChild(el('span', 'pill', 'This experiment only'));
    var x = el('button', 'x', '×'); x.type = 'button'; x.setAttribute('aria-label', 'Close'); hd.appendChild(x); dock.appendChild(hd);
    var msgs = el('div', 'msgs'); dock.appendChild(msgs);
    var chips = el('div', 'chips'); dock.appendChild(chips);
    var form = el('form', 'compose'); var q = el('textarea'); q.rows = 1; q.placeholder = 'Ask about the theory, your readings, errors…'; q.setAttribute('aria-label', 'Your question'); q.id = 'askq';
    var send = el('button', 'btn pri', 'Ask'); send.type = 'submit'; form.appendChild(q); form.appendChild(send); dock.appendChild(form);
    function bubble(cls, t) { var m = el('div', 'msg ' + cls, t); msgs.appendChild(m); msgs.scrollTop = msgs.scrollHeight; return m; }
    S.askNote = function (t) { bubble('sys', t); };
    btn.addEventListener('click', function () { dock.hidden = false; btn.hidden = true; q.focus(); });
    x.addEventListener('click', function () { dock.hidden = true; btn.hidden = false; });
    bubble('ai', 'Hi, I am Hoola, your lab partner for "' + lab.title + '". Ask me about the theory, the apparatus, your readings, or why your result differs from the true value.');
    (exp.chips || ['Explain the principle simply', 'Check my readings', 'Why is my result different?', 'What are the main sources of error?']).forEach(function (c) {
      var b = el('button', '', c); b.type = 'button'; b.addEventListener('click', function () { ask(c); }); chips.appendChild(b); });
    var turns = [], busy = false;
    function token() { try { return window.HOOLA_TOKEN || localStorage.getItem('hoola.console.token') || ''; } catch (e) { return window.HOOLA_TOKEN || ''; } }
    function state() { var st = {}; try { st = exp.askState ? exp.askState(S) : {}; } catch (e) { st = {}; }
      st.current_step = S.steps[S.step].title; st.readings = S.rows.slice(-12).map(function (r, i) { var o = {}; ((exp.book && exp.book.columns) || []).forEach(function (c) { try { o[c.label] = c.get(r, i); } catch (e) { /* skip */ } }); return o; });
      var res = S.result(); if (res && isFinite(res.value)) st.result = { label: res.label, value: +fmt(res.value, res.digits), unit: res.unit, true_value_in_lab: res.truth };
      return st; }
    function ask(text) {
      text = (text || '').trim(); if (!text || busy) return;
      dock.hidden = false; btn.hidden = true; bubble('me', text); q.value = '';
      var tok = token();
      if (!tok) { bubble('sys', 'Open this lab from the Hoola app or console (signed in) to ask Hoola. The experiment itself works without signing in.'); return; }
      busy = true; send.disabled = true; var out = bubble('ai', 'Thinking…');
      turns.push({ role: 'user', content: text }); while (turns.length > 8) turns.shift();
      fetch('/api/prayog/ask', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + tok },
        body: JSON.stringify({ lab_id: lab.id, question: text, turns: turns.slice(0, -1), state: state() }) })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) { if (!res.ok) throw new Error((res.d && res.d.detail) || 'Hoola could not answer just now.'); out.textContent = res.d.answer; turns.push({ role: 'assistant', content: res.d.answer }); })
        .catch(function (e) { out.remove(); turns.pop(); bubble('sys', String(e.message || e)); })
        .then(function () { busy = false; send.disabled = false; });
    }
    form.addEventListener('submit', function (e) { e.preventDefault(); ask(q.value); });
    q.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(q.value); } });
    S.ask = ask;
  }
})();
