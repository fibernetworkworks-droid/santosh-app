/* Hoola 3D scene runtime (v0.140). Draws a SCENE made by the art direction (DATA only: shapes, materials, lights,
   animations; see appmaker/artdirect.py) with three.js r149. No network, no model-written code.
   window.HoolaScene.build(el, scene, {still: bool, t: seconds, transparent: bool}) -> {render, recolor, dispose}
   Colours come from the app's tokens (--c-primary ...), so light / dark mode and brand colours follow. */
(function () {
  'use strict';
  var T = window.THREE;
  if (!T) return;
  if (T.ColorManagement && 'legacyMode' in T.ColorManagement) T.ColorManagement.legacyMode = false;   // brand hex stays true
  var VARS = { primary: '--c-primary', accent: '--c-accent', ink: '--c-ink', surface: '--c-surface', bg: '--c-bg',
    muted: '--c-muted', tint: '--c-tint' };

  function cssv(v, el) { return (getComputedStyle(el || document.body).getPropertyValue(v) || '').trim(); }
  function colour(c, el) {
    c = c || 'primary';
    if (c.charAt(0) === '#') return c;
    if (c === 'white') return '#ffffff';
    if (c === 'gold') return '#d4a63a';
    var v = cssv(VARS[c] || '--c-primary', el);
    return /^#|^rgb/.test(v) ? v : '#8a8f98';
  }
  function rng(seed) {             // deterministic, so screenshots are the same every time
    var s = seed >>> 0;
    return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  }
  function rad(d) { return (d || 0) * Math.PI / 180; }

  function shape2d(kind, sp) {
    var s = new T.Shape(), i;
    if (kind === 'star') {
      var n = sp || 5, R = 1, r = 0.45;
      for (i = 0; i < n * 2; i++) {
        var a = i * Math.PI / n - Math.PI / 2, rr = i % 2 ? r : R;
        if (i === 0) s.moveTo(Math.cos(a) * rr, Math.sin(a) * rr); else s.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
      }
      s.closePath();
    } else if (kind === 'heart') {
      s.moveTo(0, -0.9);
      s.bezierCurveTo(-0.2, -0.7, -1.1, -0.2, -1.0, 0.35);
      s.bezierCurveTo(-0.95, 0.85, -0.35, 1.0, 0, 0.55);
      s.bezierCurveTo(0.35, 1.0, 0.95, 0.85, 1.0, 0.35);
      s.bezierCurveTo(1.1, -0.2, 0.2, -0.7, 0, -0.9);
    } else {                          // rounded rectangle, -1..1
      var w = 1, h = 1, c = 0.28;
      s.moveTo(-w + c, -h); s.lineTo(w - c, -h); s.quadraticCurveTo(w, -h, w, -h + c); s.lineTo(w, h - c);
      s.quadraticCurveTo(w, h, w - c, h); s.lineTo(-w + c, h); s.quadraticCurveTo(-w, h, -w, h - c); s.lineTo(-w, -h + c);
      s.quadraticCurveTo(-w, -h, -w + c, -h);
    }
    return s;
  }
  function extrude(kind, size, sp) {
    var g = new T.ExtrudeGeometry(shape2d(kind, sp), { depth: 0.5, bevelEnabled: true, bevelThickness: 0.12, bevelSize: 0.08,
      bevelSegments: 4, curveSegments: 24 });
    g.center();
    g.scale(size[0] / 2, size[1] / 2, (size[2] || 0.4) / 0.74);
    return g;
  }

  function geometry(o) {
    var s = o.size || [1, 1, 1], a = o.args || {}, seg = Math.max(3, Math.min(128, a.segments || 48));
    switch (o.shape) {
      case 'box': return new T.BoxGeometry(s[0], s[1], s[2]);
      case 'rounded_box': return extrude('rect', s);
      case 'sphere': return new T.SphereGeometry(s[0], seg, Math.max(8, seg >> 1));
      case 'torus': return new T.TorusGeometry(s[0], (a.tube || 0.3) * s[0], 24, seg * 2);
      case 'torus_knot': return new T.TorusKnotGeometry(s[0], (a.tube || 0.3) * s[0], seg * 3, 16);
      case 'cylinder': return new T.CylinderGeometry(s[0], s[2] || s[0], s[1], seg);
      case 'cone': return new T.ConeGeometry(s[0], s[1], seg);
      case 'capsule': return new T.CapsuleGeometry(s[0], s[1], 8, Math.max(8, seg >> 1));
      case 'pill': { var p = new T.CapsuleGeometry(s[0] * 0.5, s[1], 8, 24); p.rotateZ(Math.PI / 2); return p; }
      case 'icosahedron': return new T.IcosahedronGeometry(s[0], 0);
      case 'octahedron': return new T.OctahedronGeometry(s[0], 0);
      case 'dodecahedron': return new T.DodecahedronGeometry(s[0], 0);
      case 'tetrahedron': return new T.TetrahedronGeometry(s[0], 0);
      case 'plane': return new T.PlaneGeometry(s[0], s[1]);
      case 'ring': return new T.TorusGeometry(s[0], Math.max(0.01, a.tube || 0.04) * s[0], 12, seg * 2);
      case 'disc': return new T.CylinderGeometry(s[0], s[0], Math.max(0.02, s[1]), seg);
      case 'lathe': {
        var pts = (a.points || [[0, -1], [0.8, -0.9], [0.9, 0.6], [0.6, 1]]).map(function (q) { return new T.Vector2(q[0] * s[0], q[1] * s[1]); });
        return new T.LatheGeometry(pts, seg);
      }
      case 'gem': { var g = new T.OctahedronGeometry(s[0], 0); g.scale(1, (s[1] || s[0]) / s[0] * 1.2, 1); return g; }
      case 'star': return extrude('star', s, a.spikes);
      case 'heart': return extrude('heart', s);
    }
    return new T.BoxGeometry(1, 1, 1);
  }

  function material(o, el) {
    var col = new T.Color(colour(o.colour, el)), m, op = o.opacity == null ? 1 : o.opacity;
    switch (o.material) {
      case 'matte': m = new T.MeshStandardMaterial({ color: col, roughness: 0.92, metalness: 0 }); break;
      case 'glossy': m = new T.MeshPhysicalMaterial({ color: col, roughness: 0.18, metalness: 0.05, clearcoat: 1, clearcoatRoughness: 0.08 }); break;
      case 'metal': m = new T.MeshStandardMaterial({ color: col, roughness: 0.22, metalness: 0.95 }); break;
      case 'glass': m = new T.MeshPhysicalMaterial({ color: col, roughness: 0.04, metalness: 0, transmission: 0.92, thickness: 0.6,
        ior: 1.45, transparent: true, opacity: Math.min(op, 0.95) }); break;
      case 'clay': m = new T.MeshStandardMaterial({ color: col, roughness: 1, metalness: 0 }); break;
      case 'glow': m = new T.MeshStandardMaterial({ color: col, emissive: col, emissiveIntensity: 0.9, roughness: 0.4 }); break;
      case 'toon': m = new T.MeshToonMaterial({ color: col }); break;
      case 'wire': m = new T.MeshBasicMaterial({ color: col, wireframe: true, transparent: op < 1, opacity: op }); break;
      default: m = new T.MeshStandardMaterial({ color: col, roughness: 0.5, metalness: 0.1 });
    }
    if (op < 1 && o.material !== 'glass') { m.transparent = true; m.opacity = op; }
    m.userData.colour = o.colour;
    return m;
  }

  function lights(scene, kind, el) {
    var acc = new T.Color(colour('accent', el)), pri = new T.Color(colour('primary', el)), L = [];
    function add(x) { scene.add(x); L.push(x); return x; }
    if (kind === 'neon') {
      add(new T.AmbientLight(0xffffff, 0.18));
      var a = add(new T.PointLight(pri, 2.2, 30)); a.position.set(-3, 2, 3);
      var b = add(new T.PointLight(acc, 2.2, 30)); b.position.set(3, -1, 3);
    } else if (kind === 'sunset') {
      add(new T.HemisphereLight(0xffd2a6, 0x4a3060, 1.0));
      var d = add(new T.DirectionalLight(0xff9a5a, 1.3)); d.position.set(-4, 2, 3);
    } else if (kind === 'morning') {
      add(new T.HemisphereLight(0xfff7e6, 0xcfe3ff, 1.1));
      var m = add(new T.DirectionalLight(0xffffff, 1.0)); m.position.set(3, 5, 2);
    } else if (kind === 'night') {
      add(new T.HemisphereLight(0x334466, 0x0b0b14, 0.7));
      var n = add(new T.PointLight(acc, 1.6, 25)); n.position.set(2, 3, 3);
    } else if (kind === 'soft') {
      add(new T.HemisphereLight(0xffffff, 0x8888aa, 1.25));
      var s2 = add(new T.DirectionalLight(0xffffff, 0.5)); s2.position.set(2, 4, 3);
    } else {                          // studio: key + fill + accent rim
      add(new T.HemisphereLight(0xffffff, 0x555566, 0.9));
      var k = add(new T.DirectionalLight(0xffffff, 1.4)); k.position.set(3, 5, 4);
      var r = add(new T.DirectionalLight(acc, 0.7)); r.position.set(-4, 1, -3);
    }
    return L;
  }

  function envMap(renderer) {        // a soft studio for reflections (metal / glass / glossy look real)
    try {
      var pm = new T.PMREMGenerator(renderer), es = new T.Scene();
      var room = new T.Mesh(new T.SphereGeometry(10, 32, 16), new T.MeshBasicMaterial({ color: 0x9aa0aa, side: T.BackSide }));
      es.add(room);
      [[0, 6, 0, 8, 0.3, 8, 0xffffff], [6, 2, 2, 0.3, 4, 6, 0xffffff], [-6, 1, -2, 0.3, 3, 5, 0xdde6ff]].forEach(function (p) {
        var m = new T.Mesh(new T.BoxGeometry(p[3], p[4], p[5]), new T.MeshBasicMaterial({ color: p[6] }));
        m.position.set(p[0], p[1], p[2]); es.add(m);
      });
      var tex = pm.fromScene(es, 0.04).texture;
      pm.dispose();
      return tex;
    } catch (e) { return null; }
  }

  function build(el, spec, opts) {
    opts = opts || {};
    var w = el.clientWidth || 320, h = el.clientHeight || 320, r;
    try { r = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true }); } catch (e) { return null; }
    r.setPixelRatio(Math.min(2, window.devicePixelRatio || 1)); r.setSize(w, h);
    if ('outputEncoding' in r) r.outputEncoding = T.sRGBEncoding;
    r.toneMapping = T.ACESFilmicToneMapping; r.toneMappingExposure = 1.05;
    el.appendChild(r.domElement);
    var scene = new T.Scene(), cam = spec.camera || {};
    scene.environment = envMap(r);
    var camera = new T.PerspectiveCamera(cam.fov || 38, w / h, 0.1, 100);
    camera.position.set(0, cam.height == null ? 0.6 : cam.height, cam.distance || 6); camera.lookAt(0, 0, 0);
    lights(scene, spec.light, el);
    var root = new T.Group(), live = [], mats = [];
    function make(o, parent) {
      var mat = material(o, el), mesh = new T.Mesh(geometry(o), mat), pv = new T.Group();
      mats.push(mat);
      pv.position.set(o.pos[0], o.pos[1], o.pos[2]);
      mesh.rotation.set(rad(o.rot[0]), rad(o.rot[1]), rad(o.rot[2]));
      pv.add(mesh); parent.add(pv);
      if ((o.anim || []).length) live.push({ o: o, m: mesh, pv: pv, base: pv.position.clone(), rot: mesh.rotation.clone() });
      (o.children || []).forEach(function (c) { make(c, mesh); });
    }
    (spec.objects || []).forEach(function (o) { make(o, root); });
    scene.add(root);
    var pts = null, pc = spec.particles || {};
    if (pc.count) {
      var rnd = rng(7), n = Math.min(300, pc.count), arr = new Float32Array(n * 3), sp = pc.spread || 4;
      for (var i = 0; i < n * 3; i++) arr[i] = (rnd() - 0.5) * sp;
      var gg = new T.BufferGeometry(); gg.setAttribute('position', new T.BufferAttribute(arr, 3));
      var pmat = new T.PointsMaterial({ color: new T.Color(colour(pc.colour, el)), size: pc.size || 0.04, transparent: true, opacity: 0.85 });
      pmat.userData.colour = pc.colour; mats.push(pmat);
      pts = new T.Points(gg, pmat); scene.add(pts);
    }
    function step(t) {
      live.forEach(function (L) {
        (L.o.anim || []).forEach(function (a) {
          var k = t * (a.speed || 1), amt = a.amount == null ? 0.5 : a.amount;
          if (a.type === 'spin') L.m.rotation.y = L.rot.y + k;
          else if (a.type === 'float') L.pv.position.y = L.base.y + Math.sin(k * 1.6) * 0.35 * amt;
          else if (a.type === 'bob') L.pv.position.y = L.base.y + Math.abs(Math.sin(k * 2)) * 0.4 * amt;
          else if (a.type === 'orbit') {
            var R = Math.max(0.6, Math.hypot(L.base.x, L.base.z));
            L.pv.position.x = Math.cos(k) * R; L.pv.position.z = Math.sin(k) * R;
          } else if (a.type === 'pulse') L.m.scale.setScalar(1 + Math.sin(k * 3) * 0.12 * amt);
          else if (a.type === 'breathe') L.m.scale.setScalar(1 + Math.sin(k) * 0.06 * amt);
          else if (a.type === 'wobble') { L.m.rotation.x = L.rot.x + Math.sin(k * 2) * 0.3 * amt; L.m.rotation.z = L.rot.z + Math.cos(k * 2) * 0.3 * amt; }
          else if (a.type === 'sway') L.m.rotation.z = L.rot.z + Math.sin(k * 1.4) * 0.35 * amt;
        });
      });
      root.rotation.y = drag.ry + (spec.autorotate || 0) * t * 0.6;
      root.rotation.x = drag.rx;
      if (pts) pts.rotation.y = t * 0.05;
    }
    var drag = { ry: 0, rx: 0 }, start = null, raf = 0, visible = true, still = !!opts.still;
    function render() { r.render(scene, camera); }
    function loop(now) {
      if (!el.isConnected) return api.dispose();
      if (start == null) start = now;
      if (visible) { step((now - start) / 1000); render(); }
      raf = requestAnimationFrame(loop);
    }
    if (still) { step(opts.t == null ? 1.2 : opts.t); render(); } else raf = requestAnimationFrame(loop);
    if (!still && spec.interact === 'drag') {
      var d0 = null;
      el.addEventListener('pointerdown', function (e) { d0 = { x: e.clientX, y: e.clientY, ry: drag.ry, rx: drag.rx }; });
      window.addEventListener('pointerup', function () { d0 = null; });
      el.addEventListener('pointermove', function (e) {
        if (!d0) return;
        drag.ry = d0.ry + (e.clientX - d0.x) / 90; drag.rx = Math.max(-0.8, Math.min(0.8, d0.rx + (e.clientY - d0.y) / 140));
      });
    } else if (!still && spec.interact === 'tilt') {
      el.addEventListener('pointermove', function (e) {
        var b = el.getBoundingClientRect();
        drag.ry = ((e.clientX - b.left) / b.width - 0.5) * 0.9; drag.rx = ((e.clientY - b.top) / b.height - 0.5) * 0.6;
      });
    } else if (!still && spec.interact === 'scroll') {
      var sc = el.closest('.body') || window;
      sc.addEventListener('scroll', function () { drag.ry = ((sc.scrollTop || window.scrollY || 0) / 300); }, { passive: true });
    }
    if (!still && window.IntersectionObserver) {
      new IntersectionObserver(function (es) { visible = es[0].isIntersecting; }).observe(el);
    }
    var api = {
      render: render,
      recolor: function () {
        mats.forEach(function (m) {
          if (!m.userData.colour || m.userData.colour.charAt(0) === '#') return;
          var c = new T.Color(colour(m.userData.colour, el));
          if (m.color) m.color.copy(c);
          if (m.emissive && m.emissiveIntensity) m.emissive.copy(c);
        });
        render();
      },
      dispose: function () { cancelAnimationFrame(raf); try { r.dispose(); } catch (e) { /* gone */ } }
    };
    return api;
  }

  window.HoolaScene = { build: build };
})();
