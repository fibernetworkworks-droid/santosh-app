/* Hoola Prayogshala lab runtime (v0.415). Draws ONE lab described in the Lab Scene Language (LSL: data only - bodies,
   knobs, instruments, table, tour) with three.js r149, and drives it with a kernel from kernels.js (the true behaviour).
   No network after the page loads, no model-written code: the lab JSON is checked on the server (app/prayog/lsl.py)
   and every string here is set with textContent. */
(function () {
  'use strict';
  var T = window.THREE, HK = window.HoolaKernels;
  if (!T || !HK) return;
  if (T.ColorManagement && 'legacyMode' in T.ColorManagement) T.ColorManagement.legacyMode = false;

  function $(s, el) { return (el || document).querySelector(s); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
  function num(v, d) { return typeof v === 'number' && isFinite(v) ? v : d; }
  function v3(a, d) { return a && a.length === 3 ? new T.Vector3(+a[0], +a[1], +a[2]) : (d || new T.Vector3()); }
  function fmt(v, digits) {
    if (!isFinite(v)) return '—';
    var a = Math.abs(v);
    if (digits === undefined) digits = a >= 100 ? 1 : a >= 10 ? 2 : 3;
    var out = v.toFixed(digits);
    return /^-0(\.0*)?$/.test(out) ? out.slice(1) : out;
  }
  var COLORS = { glass: '#9fd3ff', water: '#4aa3df', steel: '#9aa3ad', brass: '#c9a24a', copper: '#c46b3c', wood: '#a86f3f',
    red: '#e5484d', blue: '#3e63dd', green: '#30a46c', black: '#202020', white: '#f4f4f4', gold: '#d4a63a', ink: '#444b55',
    ray: '#ff7a1a', glycerine: '#e8d9a0', mercury: '#c0c6cc' };
  var STATIC = ['boyle', 'resonance', 'sonometer', 'mirror', 'lens', 'prism', 'slab', 'gauge', 'circuit'];   // a knob never restarts these
  function col(c) { return c && c.charAt(0) === '#' ? c : COLORS[c] || '#8a8f98'; }

  // ------------------------------------------------------------------------------------------- the lab
  function Lab(root, lab) {
    this.root = root; this.lab = lab;
    var K = HK.K[lab.kernel];
    this.K = K; this.cfg = lab.cfg || {};
    this.p = HK.paramsFor(lab.kernel, lab.params);
    this.knobVals = {};
    var self = this;
    (lab.knobs || []).forEach(function (k) { self.knobVals[k.id] = k.value; self.p[k.param] = k.value * num(k.k, 1); });
    this.s = K.init(this.p, this.cfg);
    this.view = K.view(this.s, this.p, this.cfg);
    this.running = !!lab.autorun; this.speed = num(lab.speed, 1);
    this.explode = 0; this.cut = null; this.peaks = {}; this.graphs = {}; this.watches = {};
    this.rows = []; this.objs = {}; this.dyn = [];
    this.ui(); this.scene(); this.bodies(); this.update(0); this.frame();
  }
  Lab.prototype.val = function (spec) {
    var name = typeof spec === 'string' ? spec : spec['var'], v;
    if (name.slice(0, 2) === 'p.') v = this.p[name.slice(2)];
    else if (name.slice(0, 5) === 'knob:') v = this.knobVals[name.slice(5)];
    else v = this.view[name];
    if (typeof spec !== 'string') {
      v = num(spec.c, 0) + num(spec.k, 1) * v;
      if (spec.min !== undefined) v = Math.max(spec.min, v);
      if (spec.max !== undefined) v = Math.min(spec.max, v);
    }
    return v;
  };

  // ------------------------------------------------------------------------------------------- 3D
  Lab.prototype.scene = function () {
    var box = this.stage, w = box.clientWidth || 360, h = box.clientHeight || 300, cam = this.lab.camera || {};
    var r = this.renderer = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)); r.setSize(w, h); r.localClippingEnabled = true;
    box.appendChild(r.domElement);
    this.sc = new T.Scene();
    this.camera = new T.PerspectiveCamera(42, w / h, 0.01, 200);
    this.target = v3(cam.look, new T.Vector3(0, 0, 0));
    this.home = { pos: v3(cam.pos, new T.Vector3(0, 0.3, 3)), look: this.target.clone() };
    this.camera.position.copy(this.home.pos); this.camera.lookAt(this.target);
    this.sc.add(new T.HemisphereLight(0xffffff, 0x8a8f98, 0.9));
    var d = new T.DirectionalLight(0xffffff, 0.8); d.position.set(2, 4, 3); this.sc.add(d);
    var grid = new T.GridHelper(6, 30, 0x9aa3ad, 0xd0d4da); grid.position.y = num(this.lab.floor, -1.2);
    grid.material.transparent = true; grid.material.opacity = 0.35; this.sc.add(grid);
    this.clip = new T.Plane(new T.Vector3(0, 0, -1), 10);
    this.controls();
    var self = this;
    window.addEventListener('resize', function () { self.resize(); });
  };
  Lab.prototype.resize = function () {
    var w = this.stage.clientWidth, h = this.stage.clientHeight; if (!w || !h) return;
    this.renderer.setSize(w, h); this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
  };
  Lab.prototype.controls = function () {
    var self = this, c = this.renderer.domElement, pts = {}, last = null, moved = 0, pinch = 0;
    function orbit(dx, dy) {
      var off = self.camera.position.clone().sub(self.target), sp = new T.Spherical().setFromVector3(off);
      sp.theta -= dx * 0.008; sp.phi = Math.min(Math.PI - 0.05, Math.max(0.05, sp.phi - dy * 0.008));
      off.setFromSpherical(sp); self.camera.position.copy(self.target).add(off); self.camera.lookAt(self.target);
    }
    function zoom(f) {
      var off = self.camera.position.clone().sub(self.target), L = Math.min(40, Math.max(0.15, off.length() * f));
      off.setLength(L); self.camera.position.copy(self.target).add(off);
    }
    c.style.touchAction = 'none';
    c.addEventListener('pointerdown', function (e) { pts[e.pointerId] = [e.clientX, e.clientY]; last = [e.clientX, e.clientY]; moved = 0; c.setPointerCapture(e.pointerId); });
    c.addEventListener('pointermove', function (e) {
      if (!pts[e.pointerId]) return;
      var ids = Object.keys(pts);
      if (ids.length === 2) {
        pts[e.pointerId] = [e.clientX, e.clientY];
        var a = pts[ids[0]], b = pts[ids[1]], dist = Math.hypot(a[0] - b[0], a[1] - b[1]);
        if (pinch) zoom(pinch / dist); pinch = dist; moved = 99; return;
      }
      var dx = e.clientX - last[0], dy = e.clientY - last[1]; moved += Math.abs(dx) + Math.abs(dy);
      last = [e.clientX, e.clientY]; pts[e.pointerId] = last; orbit(dx, dy);
    });
    function up(e) {
      if (!pts[e.pointerId]) return;
      delete pts[e.pointerId]; pinch = 0;
      if (moved < 6) self.pick(e);
    }
    c.addEventListener('pointerup', up); c.addEventListener('pointercancel', function (e) { delete pts[e.pointerId]; pinch = 0; });
    c.addEventListener('wheel', function (e) { e.preventDefault(); zoom(e.deltaY > 0 ? 1.1 : 0.9); }, { passive: false });
    c.addEventListener('dblclick', function () { self.fly(self.home.pos, self.home.look); });
  };
  Lab.prototype.pick = function (e) {
    var rect = this.renderer.domElement.getBoundingClientRect(), m = new T.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
    var ray = new T.Raycaster(); ray.setFromCamera(m, this.camera);
    var meshes = [], self = this;
    Object.keys(this.objs).forEach(function (k) { var o = self.objs[k]; if (o.body.name) o.obj.traverse(function (x) { if (x.isMesh) { x.userData.bid = k; meshes.push(x); } }); });
    var hit = ray.intersectObjects(meshes, false)[0];
    if (this.hl) { this.hl.forEach(function (x) { if (x.material.emissive) x.material.emissive.setHex(0); }); this.hl = null; }
    if (!hit) { this.chip.hidden = true; return; }
    var o = this.objs[hit.object.userData.bid], b = o.body;
    this.hl = []; o.obj.traverse(function (x) { if (x.isMesh && x.material.emissive) { x.material.emissive.setHex(0x333300); self.hl.push(x); } });
    this.chip.hidden = false; this.chip.innerHTML = '';
    this.chip.appendChild(el('b', '', b.name));
    if (b.info) this.chip.appendChild(el('span', '', ' — ' + b.info));
    if (b.illustrative) this.chip.appendChild(el('em', 'ill', ' sirf samjhane ke liye (illustrative)'));
  };
  Lab.prototype.fly = function (pos, look) {
    var self = this, p0 = this.camera.position.clone(), l0 = this.target.clone(), t0 = performance.now();
    function go(now) {
      var k = Math.min(1, (now - t0) / 900), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      self.camera.position.lerpVectors(p0, pos, e); self.target.lerpVectors(l0, look, e); self.camera.lookAt(self.target);
      if (k < 1) requestAnimationFrame(go);
    }
    requestAnimationFrame(go);
  };
  function mat(b) {
    var m = new T.MeshStandardMaterial({ color: col(b.color), roughness: b.color === 'steel' || b.color === 'brass' ? 0.35 : 0.6,
      metalness: b.color === 'steel' || b.color === 'brass' || b.color === 'copper' ? 0.6 : 0.05, side: T.DoubleSide });
    if (b.opacity !== undefined && b.opacity < 1) { m.transparent = true; m.opacity = b.opacity; m.depthWrite = false; }
    return m;
  }
  function label(text, size, color) {
    var c = document.createElement('canvas'), x = c.getContext('2d'), fs = 48;
    x.font = '600 ' + fs + 'px system-ui, sans-serif';
    var w = Math.ceil(x.measureText(text).width) + 16; c.width = w; c.height = fs + 16;
    x.font = '600 ' + fs + 'px system-ui, sans-serif'; x.fillStyle = color || '#1d2330'; x.textBaseline = 'middle'; x.fillText(text, 8, c.height / 2);
    var tex = new T.CanvasTexture(c), sp = new T.Sprite(new T.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
    var hgt = size || 0.06; sp.scale.set(hgt * w / c.height, hgt, 1); sp.renderOrder = 10; return sp;
  }
  function lineMat(color, dashed) {
    return dashed ? new T.LineDashedMaterial({ color: col(color), dashSize: 0.02, gapSize: 0.015 }) : new T.LineBasicMaterial({ color: col(color) });
  }
  function rod(a, b, r, m) {
    var d = b.clone().sub(a), L = d.length() || 1e-6, g = new T.CylinderGeometry(r, r, 1, 10), mesh = new T.Mesh(g, m);
    mesh.position.copy(a).add(b).multiplyScalar(0.5); mesh.scale.y = L;
    mesh.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize()); return mesh;
  }
  function placeRod(mesh, a, b) {
    var d = b.clone().sub(a), L = d.length() || 1e-6;
    mesh.position.copy(a).add(b).multiplyScalar(0.5); mesh.scale.set(1, L, 1); mesh.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize());
  }
  Lab.prototype.make = function (b) {
    var g, o, m = mat(b), s = b.size || [];
    switch (b.kind) {
      case 'box': o = new T.Mesh(new T.BoxGeometry(num(s[0], 0.1), num(s[1], 0.1), num(s[2], 0.1)), m); break;
      case 'sphere': o = new T.Mesh(new T.SphereGeometry(num(b.r, 0.05), 32, 16), m); break;
      case 'cylinder': o = new T.Mesh(new T.CylinderGeometry(num(b.r2, num(b.r, 0.05)), num(b.r, 0.05), num(b.h, 0.1), 32, 1, !!b.open), m); break;
      case 'cone': o = new T.Mesh(new T.ConeGeometry(num(b.r, 0.05), num(b.h, 0.1), 32), m); break;
      case 'torus': o = new T.Mesh(new T.TorusGeometry(num(b.r, 0.1), num(b.tube, 0.01), 12, 48, num(b.arc, Math.PI * 2)), m); break;
      case 'plane': o = new T.Mesh(new T.PlaneGeometry(num(s[0], 1), num(s[1], 1)), m); break;
      case 'dish': {
        var R = num(b.R, 0.3), ap = num(b.r, 0.06), th = Math.asin(Math.min(0.99, ap / R));
        g = new T.SphereGeometry(R, 32, 8, 0, Math.PI * 2, 0, th); o = new T.Group();
        var dish = new T.Mesh(g, m); dish.rotation.z = b.convex ? -Math.PI / 2 : Math.PI / 2; dish.position.x = b.convex ? -R : R; o.add(dish); break;
      }
      case 'lens': {
        var ra = num(b.r, 0.05), t = num(b.thick, 0.012), pts = [], i, n = 16, Rr = (ra * ra + (t / 2) * (t / 2)) / t;
        for (i = 0; i <= n; i++) { var y = ra * i / n, x = t / 2 - (Rr - Math.sqrt(Rr * Rr - y * y)); pts.push(new T.Vector2(y, Math.max(0.0005, x))); }
        for (i = n; i >= 0; i--) pts.push(new T.Vector2(pts[i].x, -pts[i].y));
        g = new T.LatheGeometry(pts, 40); var ln = new T.Mesh(g, m); ln.rotation.z = Math.PI / 2; o = new T.Group(); o.add(ln); break;
      }
      case 'prism': {
        var A = typeof b.angle === 'string' ? this.p[b.angle] : num(b.angle, Math.PI / 3), S = num(b.side, 0.12), sh = new T.Shape();
        sh.moveTo(-S * Math.sin(A / 2), 0); sh.lineTo(S * Math.sin(A / 2), 0); sh.lineTo(0, S * Math.cos(A / 2)); sh.closePath();
        g = new T.ExtrudeGeometry(sh, { depth: num(b.depth, 0.05), bevelEnabled: false }); g.translate(0, 0, -num(b.depth, 0.05) / 2);
        o = new T.Mesh(g, m); break;
      }
      case 'spring': {
        var turns = num(b.turns, 12), rad = num(b.r, 0.02), curve = [], k;
        for (k = 0; k <= turns * 24; k++) { var a = k / 24 * Math.PI * 2; curve.push(new T.Vector3(rad * Math.cos(a), k / (turns * 24) - 0.5, rad * Math.sin(a))); }
        g = new T.TubeGeometry(new T.CatmullRomCurve3(curve), turns * 24, num(b.wire, 0.002), 6, false);
        o = new T.Group(); o.add(new T.Mesh(g, m)); o.userData.spring = true; break;
      }
      case 'rope': {
        o = new T.Group();
        if (b.bow) { var lg = new T.BufferGeometry(); lg.setAttribute('position', new T.BufferAttribute(new Float32Array(3 * 25), 3)); o.add(new T.Line(lg, lineMat(b.color || 'ink'))); }
        else o.add(rod(new T.Vector3(), new T.Vector3(0, 1, 0), num(b.r, 0.0025), m));
        break;
      }
      case 'wire': {
        o = new T.Group(); var P = (b.pts || []).map(function (q) { return v3(q); }), j;
        for (j = 0; j + 1 < P.length; j++) o.add(rod(P[j], P[j + 1], num(b.r, 0.003), m));
        break;
      }
      case 'rays': {
        o = new T.Group(); o.userData.rays = true; break;
      }
      case 'arrow': {
        var dir = v3(b.dir, new T.Vector3(0, 1, 0)).normalize();
        o = new T.ArrowHelper(dir, new T.Vector3(), num(b.len, 0.1), col(b.color || 'red'), num(b.head, 0.03), num(b.head, 0.03) * 0.6);
        o.userData.dir = dir; break;
      }
      case 'scale': {
        o = new T.Group();
        var L = num(b.length, 1), sp = num(b.spacing, 0.01), maj = num(b.major, 10), cnt = Math.round(L / sp), segs = [], q, h;
        for (q = 0; q <= cnt; q++) { h = q % maj === 0 ? num(b.tick, 0.02) * 1.8 : q % (maj / 2) === 0 ? num(b.tick, 0.02) * 1.3 : num(b.tick, 0.02); segs.push(q * sp, 0, 0.001, q * sp, b.down ? -h : h, 0.001); }
        var sg = new T.BufferGeometry(); sg.setAttribute('position', new T.BufferAttribute(new Float32Array(segs), 3));
        o.add(new T.LineSegments(sg, lineMat(b.color || 'ink')));
        if (b.labels) for (q = 0; q <= cnt; q += maj) { var lb = label(String(num(b.start, 0) + q / maj * num(b.label_step, 1)), num(b.font, 0.025)); lb.position.set(q * sp, (b.down ? -1 : 1) * num(b.tick, 0.02) * 2.6, 0.002); o.add(lb); }
        var mk = new T.Mesh(new T.BoxGeometry(sp * 0.35, num(b.tick, 0.02) * 2, 0.002), new T.MeshBasicMaterial({ color: col('red') }));
        mk.visible = false; o.add(mk); o.userData.mark = mk; o.userData.sp = sp; break;
      }
      case 'text': o = label(b.text || '', num(b.size, 0.05), col(b.color || '#1d2330')); break;
      case 'needle': {
        g = new T.BoxGeometry(num(b.w, 0.004), num(b.length, 0.08), 0.002); g.translate(0, num(b.length, 0.08) / 2, 0);
        o = new T.Mesh(g, mat({ color: b.color || 'red' })); break;
      }
      case 'gas': {
        o = new T.Group(); var cntg = Math.min(200, num(b.count, 60)), seed = 7, rnd = function () { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
        var pg = new T.SphereGeometry(num(b.r, 0.006), 8, 6), pm = new T.MeshStandardMaterial({ color: col(b.color || 'blue') }), parts = [];
        for (var z = 0; z < cntg; z++) { var pt = new T.Mesh(pg, pm); pt.userData.v = new T.Vector3(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).normalize().multiplyScalar(0.25 + rnd() * 0.25); pt.userData.u = new T.Vector3(rnd(), rnd(), rnd()); parts.push(pt); o.add(pt); }
        o.userData.gas = { parts: parts, size: v3(b.size, new T.Vector3(0.1, 0.1, 0.1)) }; break;
      }
      default: o = new T.Group();
    }
    return o;
  };
  Lab.prototype.bodies = function () {
    var self = this, lab = this.lab;
    (lab.bodies || []).forEach(function (b) {
      var o = self.make(b), rec = { body: b, obj: o, base: v3(b.pos), rot: v3(b.rot) };
      o.position.copy(rec.base); o.rotation.set(rec.rot.x, rec.rot.y, rec.rot.z);
      o.traverse(function (x) { if (x.isMesh && x.material && !x.isSprite) x.material.clippingPlanes = b.cut === false ? [] : [self.clip]; });
      self.objs[b.id] = rec;
      var parent = b.parent && self.objs[b.parent] ? self.objs[b.parent].obj : self.sc;
      parent.add(o);
      if (b.bind || b.kind === 'spring' || b.kind === 'rope' || b.kind === 'rays' || b.kind === 'gas' || b.explode) self.dyn.push(rec);
    });
  };
  Lab.prototype.point = function (spec) {
    if (typeof spec === 'string' && this.objs[spec]) { var w = new T.Vector3(); this.objs[spec].obj.getWorldPosition(w); return w; }
    if (spec && spec.body && this.objs[spec.body]) { var w2 = new T.Vector3(); this.objs[spec.body].obj.updateWorldMatrix(true, false); this.objs[spec.body].obj.localToWorld(w2.copy(v3(spec.off))); return w2; }
    return v3(spec);
  };
  Lab.prototype.update = function (dt) {
    var self = this;
    this.dyn.forEach(function (rec) {
      var b = rec.body, o = rec.obj, bd = b.bind || {}, k;
      var pos = rec.base.clone();
      if (b.explode) pos.add(v3(b.explode).multiplyScalar(self.explode));
      if (bd.x) pos.x += self.val(bd.x); if (bd.y) pos.y += self.val(bd.y); if (bd.z) pos.z += self.val(bd.z);
      if (b.kind !== 'spring' && !(b.kind === 'rope')) o.position.copy(pos);
      if (bd.rx || bd.ry || bd.rz) o.rotation.set(rec.rot.x + (bd.rx ? self.val(bd.rx) : 0), rec.rot.y + (bd.ry ? self.val(bd.ry) : 0), rec.rot.z + (bd.rz ? self.val(bd.rz) : 0));
      if (bd.sx || bd.sy || bd.sz) o.scale.set(bd.sx ? Math.max(1e-4, self.val(bd.sx)) : 1, bd.sy ? Math.max(1e-4, self.val(bd.sy)) : 1, bd.sz ? Math.max(1e-4, self.val(bd.sz)) : 1);
      if (bd.visible) o.visible = self.val(bd.visible) > 0.5;
      if (bd.opacity) o.traverse(function (x) { if (x.material) { x.material.transparent = true; x.material.opacity = Math.max(0, Math.min(1, self.val(bd.opacity))); } });
      if (bd.len && o.setLength) {
        var L = self.val(bd.len), dir = o.userData.dir.clone();
        if (L < 0) dir.negate(); o.setDirection(dir); var aL = Math.max(Math.abs(L), 0.002), hd = Math.min(num(b.head, 0.03), aL * 0.5);
        o.setLength(aL, hd, hd * 0.6);
      }
      if (bd.mark && o.userData.mark) { var mi = self.val(bd.mark); o.userData.mark.visible = mi >= 0; o.userData.mark.position.x = mi * o.userData.sp; }
      if (b.kind === 'spring' || b.kind === 'rope') {
        var A = self.point(b.a), B = self.point(b.b);
        if (b.kind === 'spring') { placeRod(o, A, B); o.scale.x = 1; o.scale.z = 1; }
        else if (b.bow) {
          var bow = self.val(b.bow), arr = o.children[0].geometry.attributes.position, i, tq;
          for (i = 0; i < 25; i++) { tq = i / 24; arr.setXYZ(i, A.x + (B.x - A.x) * tq, A.y + (B.y - A.y) * tq + bow * Math.sin(Math.PI * tq), A.z + (B.z - A.z) * tq); }
          arr.needsUpdate = true;
        } else placeRod(o.children[0], A, B);
      }
      if (b.kind === 'rays') self.drawRays(rec);
      if (b.kind === 'gas') {
        var gq = o.userData.gas, sz = gq.size.clone(), hy = bd.h ? self.val(bd.h) : sz.y;
        gq.parts.forEach(function (pt) {
          pt.userData.u.addScaledVector(pt.userData.v, dt * (self.running ? 1 : 0.25));
          ['x', 'y', 'z'].forEach(function (ax) { var u = pt.userData.u[ax]; if (u < 0 || u > 1) { pt.userData.v[ax] *= -1; pt.userData.u[ax] = Math.min(1, Math.max(0, u)); } });
          pt.position.set((pt.userData.u.x - 0.5) * sz.x, pt.userData.u.y * hy, (pt.userData.u.z - 0.5) * sz.z);
        });
      }
    });
  };
  Lab.prototype.drawRays = function (rec) {
    var o = rec.obj, b = rec.body, data = this.view[b['var']] || [], sc = num(b.scale, 1);
    while (o.children.length) { var c = o.children.pop(); c.geometry.dispose(); }
    for (var i = 0; i < data.length; i++) {
      var pts = data[i].p.map(function (q) { return new T.Vector3(q[0] * sc, q[1] * sc, 0); });
      var g = new T.BufferGeometry().setFromPoints(pts), line = new T.Line(g, lineMat(data[i].v ? (b.virtual || 'ink') : (b.color || 'ray'), !!data[i].v));
      if (data[i].v) line.computeLineDistances();
      o.add(line);
    }
  };
  Lab.prototype.frame = function () {
    var self = this, prev = performance.now();
    function tick(now) {
      var dt = Math.min(0.05, (now - prev) / 1000); prev = now;
      if (self.running && self.K.step) {
        try { self.K.step(self.s, self.p, dt * self.speed, self.cfg); } catch (e) { self.running = false; self.say('Simulation ruk gayi: ' + e.message); }
      }
      self.view = self.K.view(self.s, self.p, self.cfg);
      self.update(dt); self.instruments(dt * (self.running ? self.speed : 0));
      self.renderer.render(self.sc, self.camera);
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  };

  // ------------------------------------------------------------------------------------------- panels
  Lab.prototype.ui = function () {
    var lab = this.lab, root = this.root, self = this;
    root.innerHTML = '';
    var top = el('header', 'top'); top.appendChild(el('a', 'back', '‹')).href = './';
    var tt = el('div', 'tt'); tt.appendChild(el('h1', '', lab.title)); tt.appendChild(el('p', '', (lab.level ? lab.level + ' · ' : '') + (lab.aim || '')));
    top.appendChild(tt); root.appendChild(top);
    var main = el('div', 'main'); root.appendChild(main);
    this.stage = el('div', 'stage'); main.appendChild(this.stage);
    this.chip = el('div', 'chip'); this.chip.hidden = true; this.stage.appendChild(this.chip);
    this.caption = el('div', 'cap'); this.caption.hidden = true; this.stage.appendChild(this.caption);
    var bar = el('div', 'bar'); this.stage.appendChild(bar);
    function btn(t, fn, cls) { var b = el('button', cls || '', t); b.type = 'button'; b.addEventListener('click', fn); bar.appendChild(b); return b; }
    this.playBtn = btn(this.running ? 'Pause' : 'Chalao ▶', function () { self.running = !self.running; self.playBtn.textContent = self.running ? 'Pause' : 'Chalao ▶'; }, 'pri');
    btn('Reset', function () { self.reset(); });
    btn('Tour', function () { self.tour(0); });
    if (lab.speeds && lab.speeds.length) {
      var sel = el('select'); lab.speeds.forEach(function (s) { var o = el('option', '', '×' + s); o.value = s; if (+s === self.speed) o.selected = true; sel.appendChild(o); });
      sel.addEventListener('change', function () { self.speed = +sel.value; }); sel.setAttribute('aria-label', 'Speed'); bar.appendChild(sel);
    }
    var side = el('div', 'side'); main.appendChild(side);
    var tabs = el('div', 'tabs'), body = el('div', 'tbody'); side.appendChild(tabs); side.appendChild(body);
    var panes = {};
    [['knobs', 'Knobs'], ['meters', 'Meters'], ['table', 'Table'], ['steps', 'Steps'], ['quiz', 'Andaaza'], ['about', 'About']].forEach(function (t, i) {
      var b = el('button', i === 0 ? 'on' : '', t[1]); b.type = 'button'; tabs.appendChild(b);
      var pane = el('div', 'pane'); pane.hidden = i !== 0; body.appendChild(pane); panes[t[0]] = pane;
      b.addEventListener('click', function () { Array.prototype.forEach.call(tabs.children, function (x) { x.className = ''; }); b.className = 'on'; Object.keys(panes).forEach(function (k) { panes[k].hidden = k !== t[0]; }); });
    });
    this.panes = panes;
    this.drawKnobs(); this.drawMeters(); this.drawTable(); this.drawSteps(); this.drawQuiz(); this.drawAbout();
  };
  Lab.prototype.reset = function () {
    this.s = this.K.init(this.p, this.cfg); this.peaks = {}; this.graphs = {};
    var self = this; Object.keys(this.watches).forEach(function (k) { self.watches[k] = { t: 0, on: false }; });
  };
  Lab.prototype.drawKnobs = function () {
    var self = this, pane = this.panes.knobs, dyn = STATIC.indexOf(this.lab.kernel) < 0;
    (this.lab.knobs || []).forEach(function (k) {
      var row = el('label', 'knob'), head = el('div', 'kh'), val = el('span', 'kv');
      head.appendChild(el('span', '', k.label)); head.appendChild(val); row.appendChild(head);
      var inp = el('input'); inp.type = 'range'; inp.min = k.min; inp.max = k.max; inp.step = k.step; inp.value = k.value;
      var dg = k.digits !== undefined ? k.digits : ((String(k.step).split('.')[1] || '').length);
      function show() { val.textContent = k.hidden ? '?' : fmt(+inp.value, dg) + (k.unit ? ' ' + k.unit : ''); }
      inp.addEventListener('input', function () {
        self.knobVals[k.id] = +inp.value; self.p[k.param] = +inp.value * num(k.k, 1); show();
        if (k.reset !== undefined ? k.reset : dyn) self.reset();
      });
      row.appendChild(inp); show();
      if (k.hint) row.appendChild(el('small', '', k.hint));
      pane.appendChild(row);
    });
    if (!(this.lab.knobs || []).length) pane.appendChild(el('p', 'mut', 'Is lab mein koi knob nahi.'));
    var x = el('div', 'tools');
    var cut = el('label', 'knob'); cut.appendChild(el('div', 'kh', 'Kaat ke dekho (section)'));
    var ci = el('input'); ci.type = 'range'; ci.min = -1; ci.max = 1; ci.step = 0.01; ci.value = 1;
    ci.addEventListener('input', function () { self.clip.constant = +ci.value >= 0.99 ? 10 : +ci.value; }); cut.appendChild(ci); x.appendChild(cut);
    if ((this.lab.bodies || []).some(function (b) { return b.explode; })) {
      var ex = el('label', 'knob'); ex.appendChild(el('div', 'kh', 'Khol ke dekho (explode)'));
      var ei = el('input'); ei.type = 'range'; ei.min = 0; ei.max = 1; ei.step = 0.01; ei.value = 0;
      ei.addEventListener('input', function () { self.explode = +ei.value; }); ex.appendChild(ei); x.appendChild(ex);
    }
    pane.appendChild(x);
  };
  Lab.prototype.drawMeters = function () {
    var self = this, pane = this.panes.meters; this.meterEls = {};
    (this.lab.instruments || []).forEach(function (m) {
      var box = el('div', 'meter ' + m.kind), head = el('div', 'mh'); head.appendChild(el('span', '', m.label)); box.appendChild(head);
      var out = el('div', 'mv'); box.appendChild(out); self.meterEls[m.id] = { m: m, out: out };
      if (m.kind === 'stopwatch') {
        self.watches[m.id] = { t: 0, on: false };
        var b1 = el('button', '', 'Start / Stop'), b2 = el('button', '', 'Shoonya');
        b1.type = b2.type = 'button';
        b1.addEventListener('click', function () { var w = self.watches[m.id]; w.on = !w.on; if (w.on && !self.running) { self.running = true; self.playBtn.textContent = 'Pause'; } });
        b2.addEventListener('click', function () { self.watches[m.id] = { t: 0, on: false }; });
        var r = el('div', 'row'); r.appendChild(b1); r.appendChild(b2); box.appendChild(r);
      }
      if (m.kind === 'graph') { var c = el('canvas'); c.width = 600; c.height = 260; box.appendChild(c); self.meterEls[m.id].c = c; self.graphs[m.id] = []; }
      if (m.kind === 'meter') { var bar = el('div', 'gauge'), fill = el('i'); bar.appendChild(fill); box.appendChild(bar); self.meterEls[m.id].fill = fill; }
      if (m.hint) {
        out.textContent = 'Dekhne ke liye tap'; out.classList.add('hint'); self.meterEls[m.id].hidden = true;
        out.addEventListener('click', function () { self.meterEls[m.id].hidden = false; out.classList.remove('hint'); });
      }
      pane.appendChild(box);
    });
    pane.appendChild(el('p', 'mut', 'Har reading Hoola ke "' + this.lab.kernel + '" simulation se aati hai (code), andaaze se nahi.'));
  };
  Lab.prototype.reading = function (m) {
    if (m.kind === 'stopwatch') return this.watches[m.id] ? this.watches[m.id].t : 0;
    var v = this.val(m['var']) * num(m.k, 1);
    if (m.peak) { this.peaks[m.id] = Math.max(this.peaks[m.id] || 0, Math.abs(v)); v = this.peaks[m.id]; }
    if (m.lc) v = Math.round(v / m.lc) * m.lc;
    return v;
  };
  Lab.prototype.instruments = function (dt) {
    var self = this;
    Object.keys(this.watches).forEach(function (k) { if (self.watches[k].on) self.watches[k].t += dt; });
    Object.keys(this.meterEls || {}).forEach(function (id) {
      var e = self.meterEls[id], m = e.m, v = self.reading(m);
      if (m.kind === 'graph') {
        var xs = m.x ? self.val(m.x) * num(m.xk, 1) : self.view.t, g = self.graphs[id];
        if (!g.length || Math.abs(g[g.length - 1][0] - xs) > 1e-9 || Math.abs(g[g.length - 1][1] - v) > 1e-9) { g.push([xs, v]); if (g.length > 600) g.shift(); }
        self.plot(e.c, g, m);
      }
      if (e.hidden) return;
      e.out.textContent = m.kind === 'stopwatch' ? v.toFixed(2) + ' s' : fmt(v, m.digits) + (m.unit ? ' ' + m.unit : '');
      if (e.fill) { var r = m.range || [0, 1], f = Math.max(0, Math.min(1, (v - r[0]) / (r[1] - r[0]))); e.fill.style.width = (f * 100).toFixed(1) + '%'; }
    });
  };
  Lab.prototype.plot = function (c, g, m) {
    var x = c.getContext('2d'), W = c.width, H = c.height, i, lo = Infinity, hi = -Infinity, xl = Infinity, xh = -Infinity;
    x.clearRect(0, 0, W, H);
    if (!g.length) return;
    for (i = 0; i < g.length; i++) { lo = Math.min(lo, g[i][1]); hi = Math.max(hi, g[i][1]); xl = Math.min(xl, g[i][0]); xh = Math.max(xh, g[i][0]); }
    if (m.range) { lo = m.range[0]; hi = m.range[1]; }
    if (hi - lo < 1e-12) { hi += 1; lo -= 1; } if (xh - xl < 1e-12) xh = xl + 1;
    var css = getComputedStyle(document.body);
    x.strokeStyle = css.getPropertyValue('--line') || '#ccc'; x.lineWidth = 1; x.strokeRect(40, 10, W - 50, H - 40);
    x.fillStyle = css.getPropertyValue('--mut') || '#666'; x.font = '20px system-ui';
    x.fillText(fmt(hi), 2, 24); x.fillText(fmt(lo), 2, H - 30); x.fillText((m.xlabel || 't') + ' →', W - 120, H - 6);
    x.strokeStyle = '#3e63dd'; x.lineWidth = 3; x.beginPath();
    for (i = 0; i < g.length; i++) {
      var px = 40 + (g[i][0] - xl) / (xh - xl) * (W - 50), py = 10 + (1 - (g[i][1] - lo) / (hi - lo)) * (H - 40);
      if (m.x && m.dots) { x.fillStyle = '#3e63dd'; x.fillRect(px - 3, py - 3, 6, 6); } else if (i) x.lineTo(px, py); else x.moveTo(px, py);
    }
    x.stroke();
  };
  Lab.prototype.drawTable = function () {
    var self = this, pane = this.panes.table, t = this.lab.table;
    if (!t) { pane.appendChild(el('p', 'mut', 'Is lab mein observation table nahi.')); return; }
    var wrap = el('div', 'tw'), tbl = el('table'), thead = el('tr'); wrap.appendChild(tbl); tbl.appendChild(thead);
    thead.appendChild(el('th', '', '#'));
    t.columns.forEach(function (c) { thead.appendChild(el('th', '', c.label + (c.unit ? ' (' + c.unit + ')' : ''))); });
    thead.appendChild(el('th', '', ''));
    var tb = el('tbody'); tbl.appendChild(tb);
    var res = el('div', 'res');
    function value(c) {
      var src = c.from || 'manual', v = '';
      if (src.slice(0, 5) === 'knob:') v = self.knobVals[src.slice(5)];
      else if (src.slice(0, 5) === 'inst:') { var m = (self.lab.instruments || []).filter(function (x) { return x.id === src.slice(5); })[0]; v = m ? self.reading(m) : ''; }
      if (v !== '' && c.div) v = v / c.div;
      return v;
    }
    function compute() {
      var rowsSI = self.rows.map(function (r) { var o = {}; t.columns.forEach(function (c) { var v = r[c.id]; o[c.id] = v === '' || v === undefined ? '' : +v * num(c.k, 1); }); return o; });
      var C = HK.CALCS[t.calc]; res.innerHTML = '';
      if (!C) return;
      var need = t.rows_min || 2;
      if (self.rows.length < need) { res.appendChild(el('p', 'mut', 'Kam se kam ' + need + ' readings record kijiye, phir result yahan.')); return; }
      var v = C.fn(rowsSI, self.p) * num(t.result_k, 1);
      res.appendChild(el('p', 'big', C.label + ' = ' + fmt(v, t.result_digits) + ' ' + (t.result_unit || C.unit)));
      if (t.truth) {
        var tv = (t.truth.slice(0, 2) === 'p.' ? self.p[t.truth.slice(2)] : +t.truth) * num(t.result_k, 1);
        var err = tv ? Math.abs(v - tv) / Math.abs(tv) * 100 : 0;
        res.appendChild(el('p', 'mut', 'Is lab mein asli value ' + fmt(tv, t.result_digits) + ' ' + (t.result_unit || C.unit) + ' hai · aapki galti ' + err.toFixed(1) + '%'));
      }
    }
    function draw() {
      tb.innerHTML = '';
      self.rows.forEach(function (r, i) {
        var tr = el('tr'); tr.appendChild(el('td', '', String(i + 1)));
        t.columns.forEach(function (c) {
          var td = el('td');
          if ((c.from || 'manual') === 'manual') {
            var inp = el('input'); inp.type = 'number'; inp.step = 'any'; inp.value = r[c.id]; inp.setAttribute('aria-label', c.label);
            inp.addEventListener('change', function () { r[c.id] = inp.value; compute(); }); td.appendChild(inp);
          } else td.textContent = r[c.id] === '' ? '—' : fmt(+r[c.id], c.digits);
          tr.appendChild(td);
        });
        var del = el('button', 'x', '×'); del.type = 'button'; del.setAttribute('aria-label', 'Delete row');
        del.addEventListener('click', function () { self.rows.splice(i, 1); draw(); compute(); });
        var td2 = el('td'); td2.appendChild(del); tr.appendChild(td2); tb.appendChild(tr);
      });
    }
    var actions = el('div', 'row');
    var rec = el('button', 'pri', '+ Reading record karo'); rec.type = 'button';
    rec.addEventListener('click', function () { var r = {}; t.columns.forEach(function (c) { r[c.id] = value(c); }); self.rows.push(r); draw(); compute(); });
    var csv = el('button', '', 'CSV'); csv.type = 'button';
    csv.addEventListener('click', function () {
      var lines = [t.columns.map(function (c) { return '"' + c.label + (c.unit ? ' (' + c.unit + ')' : '') + '"'; }).join(',')];
      self.rows.forEach(function (r) { lines.push(t.columns.map(function (c) { return r[c.id]; }).join(',')); });
      var a = el('a'); a.href = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' })); a.download = self.lab.id + '.csv'; a.click();
    });
    actions.appendChild(rec); actions.appendChild(csv);
    if (t.hint) pane.appendChild(el('p', 'mut', t.hint));
    pane.appendChild(actions); pane.appendChild(wrap); pane.appendChild(res);
    this.recordRow = function () { rec.click(); };
  };
  Lab.prototype.drawSteps = function () {
    var pane = this.panes.steps, ol = el('ol');
    (this.lab.steps || []).forEach(function (s) { ol.appendChild(el('li', '', s)); });
    pane.appendChild(ol);
    if (this.lab.theory) { pane.appendChild(el('h3', '', 'Siddhant')); pane.appendChild(el('p', '', this.lab.theory)); }
    if (this.lab.safety) { pane.appendChild(el('h3', '', 'Asli lab mein savdhani')); pane.appendChild(el('p', '', this.lab.safety)); }
  };
  Lab.prototype.drawQuiz = function () {
    var pane = this.panes.quiz;
    (this.lab.questions || []).forEach(function (q) {
      var box = el('div', 'q'); box.appendChild(el('p', 'qq', q.q));
      var why = el('p', 'why'); why.hidden = true;
      q.options.forEach(function (o, i) {
        var b = el('button', '', o); b.type = 'button';
        b.addEventListener('click', function () {
          Array.prototype.forEach.call(box.querySelectorAll('button'), function (x, j) { x.disabled = true; if (j === q.answer) x.classList.add('ok'); });
          if (i !== q.answer) b.classList.add('no');
          why.hidden = false; why.textContent = (i === q.answer ? 'Sahi! ' : 'Nahi - ') + (q.why || '') + ' Ab lab chala ke khud dekhiye.';
        });
        box.appendChild(b);
      });
      box.appendChild(why); pane.appendChild(box);
    });
    if (!(this.lab.questions || []).length) pane.appendChild(el('p', 'mut', 'Is lab mein sawaal nahi.'));
  };
  Lab.prototype.drawAbout = function () {
    var pane = this.panes.about, lab = this.lab;
    pane.appendChild(el('p', '', 'Yeh lab Hoola ke "' + lab.kernel + '" simulation se chalta hai: har number code se nikalta hai. ' +
      'Server ke tests isko NCERT ke formula se milate hain (1% ke andar).'));
    if (lab.check && lab.check.textbook) pane.appendChild(el('p', 'mut', 'Jaanch: ' + lab.check.textbook));
    var ill = (lab.bodies || []).filter(function (b) { return b.illustrative; }).map(function (b) { return b.name || b.id; });
    if (ill.length) pane.appendChild(el('p', 'mut', 'Sirf samjhane ke liye (illustrative): ' + ill.join(', ')));
    pane.appendChild(el('h3', '', 'Sources'));
    var ul = el('ul'); (lab.sources || []).forEach(function (s) { ul.appendChild(el('li', '', s.title + (s.note ? ' — ' + s.note : ''))); }); pane.appendChild(ul);
  };

  // ------------------------------------------------------------------------------------------- tour + narration
  Lab.prototype.say = function (text) {
    this.caption.hidden = !text; this.caption.textContent = text || '';
    try {
      if (!window.speechSynthesis || !text || this.mute) return;
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(text); u.lang = this.lab.lang || 'hi-IN'; u.rate = 0.95;
      window.speechSynthesis.speak(u);
    } catch (e) { /* narration is optional; the caption always shows */ }
  };
  Lab.prototype.tour = function (i) {
    var steps = this.lab.tour || [], self = this;
    if (i >= steps.length) { this.say(''); if (this.tourBar) this.tourBar.remove(); this.tourBar = null; return; }
    var st = steps[i];
    if (st.cam) this.fly(v3(st.cam), v3(st.look, this.target.clone()));
    if (st.set) Object.keys(st.set).forEach(function (kid) {
      var k = (self.lab.knobs || []).filter(function (x) { return x.id === kid; })[0]; if (!k) return;
      self.knobVals[k.id] = st.set[kid]; self.p[k.param] = st.set[kid] * num(k.k, 1);
      var inputs = self.panes.knobs.querySelectorAll('input[type=range]'), idx = self.lab.knobs.indexOf(k);
      if (inputs[idx]) { inputs[idx].value = st.set[kid]; inputs[idx].dispatchEvent(new Event('input')); }
    });
    if (st.run !== undefined) { this.running = !!st.run; this.playBtn.textContent = this.running ? 'Pause' : 'Chalao ▶'; }
    this.say(st.say);
    if (!this.tourBar) {
      this.tourBar = el('div', 'tour'); this.stage.appendChild(this.tourBar);
    }
    this.tourBar.innerHTML = '';
    var prev = el('button', '', '‹'), next = el('button', 'pri', i + 1 < steps.length ? 'Aage ›' : 'Khatam'), stop = el('button', '', '×');
    [prev, next, stop].forEach(function (b) { b.type = 'button'; });
    prev.disabled = i === 0;
    prev.addEventListener('click', function () { self.tour(i - 1); });
    next.addEventListener('click', function () { self.tour(i + 1); });
    stop.addEventListener('click', function () { self.tour(steps.length); });
    this.tourBar.appendChild(prev); this.tourBar.appendChild(el('span', '', (i + 1) + ' / ' + steps.length)); this.tourBar.appendChild(next); this.tourBar.appendChild(stop);
  };

  window.HoolaLab = { open: function (root, lab) { return new Lab(root, lab); } };
})();
