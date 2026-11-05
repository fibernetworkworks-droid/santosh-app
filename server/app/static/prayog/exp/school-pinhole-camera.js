/* Prayogshala studio module: the pinhole camera (NCERT Class VI-VII, Light, Shadows and Reflections).
   A cardboard camera - an outer box with a pin hole in its front face and an inner box with tracing paper that
   slides in and out - stands on a bench with a metre scale, facing a lit candle. Every number comes from the
   `pinhole` kernel: the ray from the top of the candle through the hole gives an inverted image of height h v / u,
   and a hole of finite size spreads every point into a small circle (blur). */
HoolaStudio.define('school-pinhole-camera', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.pinhole;
  var p = window.HoolaKernels.paramsFor('pinhole', S.lab.params);
  var BZ = -0.12, YB = 0.006, HX = -0.05;                              // bench z, bench top, x of the pin hole
  var BOXW = 0.13, SCR_H = 0.13;                                      // the box's width (z) and the tracing paper's height
  var st = { lit: false, hole: false, looked: false, uCm: 40, uSet: 40, vCm: 20, vSet: 20, dpMm: p.dp * 1000, dpSet: p.dp * 1000 };
  function round1(v) { return Math.round(v * 10) / 10; }
  function sync() { p.u = Math.max(0.05, st.uCm / 100); p.v = Math.max(0.03, st.vCm / 100); p.dp = st.dpMm / 1000; return K.view(null, p); }
  function xAt(cm) { return HX - cm / 100; }                           // the candle's x, cm in front of the hole

  // ---------- the bench and its scale
  var bench = new T.Group(); S.scene.add(bench);
  var plank = S.mesh(new T.BoxGeometry(1.42, 0.012, 0.22), M.wood); plank.position.set(HX - 0.33, YB - 0.006, BZ); bench.add(plank);
  var scaleTex = S.canvasTex(4096, 128, function (x, w, h) {
    x.fillStyle = '#f0ead8'; x.fillRect(0, 0, w, h); x.fillStyle = '#1a1a1a';
    var cm = 100, k = w / cm, i;
    for (i = 0; i <= cm; i++) { var xx = w - i * k, big = i % 10 === 0;
      x.fillRect(xx, 0, big ? 3 : 1.5, big ? 48 : (i % 5 === 0 ? 32 : 18));
      if (big) { x.font = '600 38px sans-serif'; x.fillText(String(i), xx + 5, 92); } }
  });
  var strip = new T.Mesh(new T.PlaneGeometry(1.0, 0.03), new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.6 }));
  strip.rotation.x = -Math.PI / 2; strip.position.set(HX - 0.5, YB + 0.0012, BZ + 0.075); bench.add(strip);
  S.contact(1.5, 0.3, HX - 0.33, BZ, 0.45);

  // ---------- the camera: an outer box with the hole, an inner box with tracing paper
  var cam = new T.Group(); S.scene.add(cam); cam.position.set(HX, 0, BZ);
  var cardM = new T.MeshStandardMaterial({ color: 0xb98a55, roughness: 0.9 });
  var AXY = YB + 0.07;                                                // the axis: the height of the hole
  function shell(len, w, h, mat, open) {
    var g = new T.Group();
    var t = 0.0025;
    [[0, h / 2, w / 2, len, h, t], [0, h / 2, -w / 2, len, h, t], [0, h, 0, len, t, w], [0, 0, 0, len, t, w]].forEach(function (a) {
      var m = S.mesh(new T.BoxGeometry(a[3], a[4], a[5]), mat); m.position.set(a[0], a[1], a[2]); g.add(m); });
    if (!open) { var e = S.mesh(new T.BoxGeometry(t, h, w), mat); e.position.set(-len / 2, h / 2, 0); g.add(e); }
    return g;
  }
  var outer = shell(0.34, BOXW, SCR_H, cardM, true); outer.position.set(0.17, AXY - SCR_H / 2, 0); cam.add(outer);
  var front = S.mesh(new T.BoxGeometry(0.0025, SCR_H, BOXW), new T.MeshStandardMaterial({ color: 0x8c6239, roughness: 0.9 }));
  front.position.set(0, AXY, 0); cam.add(front);
  var holeDot = new T.Mesh(new T.CircleGeometry(0.0016, 16), new T.MeshBasicMaterial({ color: 0x15171a }));
  holeDot.rotation.y = -Math.PI / 2; holeDot.position.set(-0.0016, AXY, 0); cam.add(holeDot); holeDot.visible = false;
  var inner = new T.Group(); cam.add(inner);
  var innerShell = shell(0.1, BOXW - 0.012, SCR_H - 0.012, new T.MeshStandardMaterial({ color: 0xa87a48, roughness: 0.9 }), true);
  innerShell.position.set(-0.05, AXY - (SCR_H - 0.012) / 2, 0); inner.add(innerShell);
  var tpTex = S.liveTex(192, Math.round(192 * (SCR_H - 0.012) / (BOXW - 0.012)));
  var tp = S.mesh(new T.BoxGeometry(0.0022, SCR_H - 0.012, BOXW - 0.012), new T.MeshStandardMaterial({ color: 0xf2eee2, roughness: 0.95, transparent: true, opacity: 0.92 }));
  tp.position.set(0, AXY, 0); inner.add(tp);
  var imgPlane = new T.Mesh(new T.PlaneGeometry(BOXW - 0.012, SCR_H - 0.012), new T.MeshBasicMaterial({ map: tpTex, transparent: true, depthWrite: false, toneMapped: false }));
  imgPlane.rotation.y = Math.PI / 2; imgPlane.position.set(0.0014, AXY, 0); imgPlane.renderOrder = 5; inner.add(imgPlane);
  var camLab = S.label('PIN HOLE CAMERA', { w: 0.07, ratio: 0.14, color: '#3b2a18', weight: 700 });
  camLab.rotation.x = -Math.PI / 2; camLab.position.set(0.12, AXY + SCR_H / 2 + 0.001, 0); cam.add(camLab);

  // ---------- the candle on its stand
  var canG = new T.Group(); S.scene.add(canG); canG.position.set(xAt(st.uCm), 0, BZ);
  var foot = S.rounded(0.07, 0.07, 0.014, 0.004, M.iron); foot.rotation.x = -Math.PI / 2; foot.position.y = YB + 0.007; canG.add(foot);
  var holderH = Math.max(0.01, AXY - YB - 0.014 - p.h / 2);
  var holder = S.mesh(new T.CylinderGeometry(0.006, 0.006, holderH, 14), M.chrome); holder.position.y = YB + 0.014 + holderH / 2; canG.add(holder);
  var cup = S.mesh(new T.CylinderGeometry(0.018, 0.015, 0.006, 24), M.brass); cup.position.y = YB + 0.014 + holderH; canG.add(cup);
  var waxM = new T.MeshStandardMaterial({ color: 0xf4ecd9, roughness: 0.5 });
  var wax = S.mesh(new T.CylinderGeometry(0.009, 0.0095, 1, 24), waxM); canG.add(wax);
  var flameTex = S.canvasTex(128, 128, function (x) { var gr = x.createRadialGradient(64, 64, 2, 64, 64, 62);
    gr.addColorStop(0, 'rgba(255,245,205,0.95)'); gr.addColorStop(0.3, 'rgba(255,170,70,0.5)'); gr.addColorStop(1, 'rgba(255,140,40,0)');
    x.fillStyle = gr; x.fillRect(0, 0, 128, 128); });
  var flame = new T.Group();
  var fcore = new T.Mesh(new T.ConeGeometry(0.004, 0.018, 14), new T.MeshBasicMaterial({ color: 0xfff0c8, transparent: true, opacity: 0.95, toneMapped: false, depthWrite: false }));
  fcore.position.y = 0.009; flame.add(fcore);
  var fglow = new T.Sprite(new T.SpriteMaterial({ map: flameTex, transparent: true, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending, opacity: 0.85 }));
  fglow.scale.set(0.05, 0.05, 1); fglow.position.y = 0.012; flame.add(fglow);
  canG.add(flame); flame.visible = false;
  var lamp = new T.PointLight(0xffa851, 0, 1.2, 2); canG.add(lamp);
  var canSh = S.contact(0.1, 0.1, xAt(st.uCm), BZ, 0.4, YB);

  // ---------- the pin used to make the hole
  var pin = new T.Group(); S.scene.add(pin);
  var pinSh = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 0.045, 10), M.steel); pinSh.rotation.z = Math.PI / 2; pin.add(pinSh);
  var pinHd = S.mesh(new T.SphereGeometry(0.0028, 12, 8), new T.MeshStandardMaterial({ color: 0x2c63c4, roughness: 0.4 })); pinHd.position.x = -0.024; pin.add(pinHd);
  pin.position.set(HX + 0.08, YB + 0.004, BZ + 0.14);
  S.contact(0.08, 0.05, HX + 0.08, BZ + 0.14, 0.3, YB);

  // ---------- the rays through the hole
  var rayMat = new T.LineBasicMaterial({ color: 0xffc15a, transparent: true, opacity: 0.6, depthWrite: false, toneMapped: false });
  var rayLines = [];
  for (var ri = 0; ri < 4; ri++) { var l = new T.Line(new T.BufferGeometry(), rayMat); l.visible = false; l.renderOrder = 7; S.scene.add(l); rayLines.push(l); }

  S.addApparatus('cam', cam, 'Pin hole camera', 'An outer cardboard box with a pin hole in its front face, and an inner box with tracing paper that slides in and out to change the length v.');
  S.addApparatus('candle', canG, 'Candle on a stand', 'The lit candle is the object. Its height is what you have to find from the picture on the tracing paper.');
  S.addApparatus('pin', pin, 'Pin', 'Used once, to prick a small round hole in the front of the box.');
  S.addApparatus('bench', bench, 'Bench with a metre scale', 'The distance u from the candle to the hole is read on it.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudU = S.hudCard('Candle to hole (u)'), hudV = S.hudCard('Length of the box (v)'), hudI = S.hudCard('Picture on the paper');

  var view = null;
  function update() {
    var v = sync(); view = v;
    canG.position.x = xAt(st.uCm); canSh.position.x = xAt(st.uCm);
    wax.scale.y = p.h - 0.018; wax.position.y = AXY - p.h / 2 + (p.h - 0.018) / 2;
    flame.position.y = AXY + p.h / 2 - 0.018; lamp.position.y = AXY + p.h / 2 - 0.01;
    inner.position.x = st.vCm / 100;
    holeDot.visible = st.hole;
    tpTex.draw(function (x, w, h) {
      x.clearRect(0, 0, w, h);
      if (!st.hole || !st.lit) return;
      var pxm = h / (SCR_H - 0.012), cy = h / 2, cx = w / 2;
      var ih = v.img_h * pxm, blur = Math.max(0.5, v.blur * pxm * 0.5);
      x.save(); x.filter = 'blur(' + blur.toFixed(1) + 'px)';
      x.globalAlpha = Math.min(1, 0.35 + 0.5 / Math.max(0.4, v.mag));
      var g1 = x.createLinearGradient(0, cy - ih / 2, 0, cy + ih / 2);
      g1.addColorStop(0, 'rgba(255,210,120,0.95)'); g1.addColorStop(0.22, 'rgba(255,170,70,0.75)'); g1.addColorStop(1, 'rgba(140,95,45,0.35)');
      x.fillStyle = g1;                                                // the flame is at the TOP of the candle, so at the BOTTOM of the picture
      x.beginPath(); x.ellipse(cx, cy + ih * 0.42, ih * 0.09, ih * 0.11, 0, 0, Math.PI * 2); x.fill();
      x.fillRect(cx - ih * 0.055, cy - ih / 2, ih * 0.11, ih * 0.92);
      x.restore();
    });
    rayLines.forEach(function (l) { l.visible = false; });
    if (st.hole && st.lit) {
      var pts = [[[-p.u, p.h / 2], [0, 0], [p.v, -p.h / 2 * v.mag]], [[-p.u, -p.h / 2], [0, 0], [p.v, p.h / 2 * v.mag]]];
      pts.forEach(function (q, k) {
        var l = rayLines[k];
        l.geometry.setFromPoints(q.map(function (a) { return new T.Vector3(HX + a[0], AXY + a[1], BZ); }));
        l.visible = true;
      });
    }
    hudU.set(st.uCm.toFixed(1) + ' cm'); hudV.set(st.vCm.toFixed(1) + ' cm');
    hudI.set(!st.hole ? 'no hole yet' : !st.lit ? 'candle not lit' : (v.img_h * 100).toFixed(2) + ' cm tall, upside down');
  }

  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function makeHole() {
    if (st.hole) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    var at = new T.Vector3(HX + 0.02, AXY, BZ);
    return S.hand.pinchMove(new T.Vector3(pin.position.x, pin.position.y + 0.01, pin.position.z), function (k) {
      return new T.Vector3(pin.position.x + (at.x - pin.position.x) * k, pin.position.y + 0.01 + (at.y - pin.position.y - 0.01) * k, pin.position.z + (at.z - pin.position.z) * k);
    }, function (k) { pin.position.set(pin.position.x, pin.position.y, pin.position.z); void k; }, { ms: 900, reachMs: 600, hold: 250 })
      .then(function () {
        st.hole = true; pin.position.set(HX + 0.08, YB + 0.004, BZ + 0.14); update(); S.render();
        S.say('A small round hole is pricked in the middle of the front face. Keep it small: a big hole gives a bright but blurred picture.');
        return true;
      });
  }
  function lightCandle() {
    if (st.lit) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    return S.hand.tap(wax).then(function () {
      st.lit = true; flame.visible = true; update(); S.render();
      S.say('The candle is lit. Now look at the tracing paper at the back of the box.'); return true;
    });
  }
  function lookAtPaper() {
    if (!st.hole) { S.say('Make the pin hole first.'); return Promise.resolve(false); }
    if (!st.lit) { S.say('Light the candle first.'); return Promise.resolve(false); }
    st.looked = true; update(); S.focus('paper'); S.render();
    var v = sync();
    S.say('The picture on the tracing paper is upside down and ' + (v.img_h * 100).toFixed(2) + ' cm tall, because the rays cross at the hole.');
    return Promise.resolve(true);
  }
  function moveCandle(toCm) {
    if (S.hand.busy) return wait();
    toCm = round1(toCm);
    if (!(toCm >= 25 && toCm <= 80)) { S.say('Keep the candle between 25 cm and 80 cm from the hole.'); return Promise.resolve(false); }
    var from = st.uCm;
    if (Math.abs(toCm - from) < 0.05) { st.uCm = toCm; update(); return Promise.resolve(true); }
    function at(k) { return from + (toCm - from) * k; }
    return S.hand.pinchMove(new T.Vector3(xAt(from), AXY - p.h / 2 - 0.01, BZ), function (k) { return new T.Vector3(xAt(at(k)), AXY - p.h / 2 - 0.01, BZ); },
      function (k) { st.uCm = at(k); update(); }, { ms: Math.min(1500, 420 + Math.abs(toCm - from) * 24), reachMs: 550, hold: 120 })
      .then(function () { st.uCm = toCm; update(); S.render(); return true; });
  }
  function slideInner(toCm) {
    if (S.hand.busy) return wait();
    toCm = round1(toCm);
    if (!(toCm >= 8 && toCm <= 28)) { S.say('The inner box slides between 8 cm and 28 cm.'); return Promise.resolve(false); }
    var from = st.vCm;
    if (Math.abs(toCm - from) < 0.05) { st.vCm = toCm; update(); return Promise.resolve(true); }
    function at(k) { return from + (toCm - from) * k; }
    return S.hand.pinchMove(new T.Vector3(HX + from / 100 + 0.01, AXY, BZ), function (k) { return new T.Vector3(HX + at(k) / 100 + 0.01, AXY, BZ); },
      function (k) { st.vCm = at(k); update(); }, { ms: 900, reachMs: 550, hold: 150 })
      .then(function () { st.vCm = toCm; update(); S.render(); return true; });
  }
  function record() {
    if (S.hand.busy) { wait(); return false; }
    if (!st.hole || !st.lit) { S.say('Make the hole and light the candle first.'); return false; }
    var v = sync(), u = round1(st.uCm), vv = round1(st.vCm), hi = round1(v.img_h * 100);   // the paper has a millimetre scale
    if (S.rows.some(function (r) { return Math.abs(r.u - u) < 2 && Math.abs(r.v - vv) < 2; })) { S.say('You already have this pair of distances. Move the candle or slide the inner box.'); return false; }
    S.addRow({ u: u, v: vv, hi: hi });
    S.say('Written in your record book: u = ' + u.toFixed(1) + ' cm, v = ' + vv.toFixed(1) + ' cm, picture = ' + hi.toFixed(1) + ' cm.');
    return true;
  }

  var ft = 0;
  S.tickers.push(function (dt) { ft += dt; var f = 1 + 0.07 * Math.sin(ft * 19) + 0.03 * Math.sin(ft * 31 + 1.1);
    flame.scale.set(1, f, 1); lamp.intensity = st.lit ? 0.03 * f : 0; });

  var VIEWS = { cam: [[HX + 0.46, AXY + 0.34, BZ + 0.66], [HX + 0.08, AXY - 0.02, BZ]], candle: [[xAt(40) + 0.26, AXY + 0.12, BZ + 0.34], [xAt(40), AXY, BZ]],
    paper: [[HX + 0.56, AXY + 0.12, BZ + 0.34], [HX + 0.2, AXY, BZ]], bench: [[HX + 0.02, 0.62, BZ + 1.16], [HX - 0.12, AXY - 0.01, BZ]],
    pin: [[HX + 0.16, 0.12, BZ + 0.24], [HX + 0.06, YB, BZ + 0.1]],
    book: [[-0.4, 0.44, 0.5], [-0.5, 0.0, 0.08]] };
  update();

  function hMean(rows) {
    var hs = (rows || []).filter(function (r) { return r.v > 0; }).map(function (r) { return r.hi * r.u / r.v; });
    return hs.length ? S.fit.mean(hs) : NaN;
  }

  return {
    camera: { pos: [HX + 0.02, 0.64, BZ + 1.2], look: [HX - 0.12, AXY - 0.01, BZ] },
    views: VIEWS,
    theory: { principle: 'Light travels in straight lines, and only the rays that pass through the pin hole reach the tracing paper. The ray from the top of the candle goes on downwards and lands at the bottom of the paper, so the picture is upside down. The two triangles on either side of the hole are similar, so the picture and the candle are in the same ratio as v and u.',
      formula: 'picture / object = v / u',
      formulaNote: 'u = candle to the hole, v = hole to the tracing paper · so the candle’s height = picture × u / v',
      more: ['Slide the inner box out and the picture grows but gets fainter, because the same light is spread over a larger area.',
        'A wider hole lets in more light, so the picture is brighter, but every point of the candle is spread into a small circle and the picture goes blurred. The blur circle is the hole’s size times (u + v) / u.',
        'The picture has no sharp focus to hunt for: a pin hole camera needs no lens at all. This is how a camera obscura works, and how the image of the sun can be caught safely during an eclipse.'],
      precautions: 'Make the hole small and round, with a pin and not a pencil. Work in a dim corner of the room so that the faint picture can be seen, and keep the candle well away from the cardboard.' },
    book: { title: 'Expt. — Pin hole camera', lines: ['Aim: to make a pin hole camera and find the height of the candle from its picture.',
      'u = candle to the hole, v = hole to the tracing paper.', 'picture / candle = v / u', 'So candle = picture × u / v.',
      'The picture is always upside down.'],
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'u (cm)', get: function (r) { return r.u.toFixed(1); } },
        { label: 'v (cm)', get: function (r) { return r.v.toFixed(1); } }, { label: 'picture (cm)', get: function (r) { return r.hi.toFixed(1); } },
        { label: 'v / u', get: function (r) { return (r.v / r.u).toFixed(3); } }, { label: 'candle (cm)', get: function (r) { return (r.hi * r.u / r.v).toFixed(2); } }] },
    graph: { x: function (r) { return r.v / r.u; }, y: function (r) { return r.hi; }, xlabel: 'v / u', ylabel: 'picture (cm)', x0: 0, y0: 0,
      line: function (pts) { var m = S.fit.origin(pts); return isFinite(m) ? function (x) { return m * x; } : null; } },
    result: function (rows) {
      var h = hMean(rows); if (!isFinite(h) || (rows || []).length < 3) return null;
      return { label: 'height of the candle', value: h, unit: 'cm', digits: 2, truth: p.h * 100,
        note: 'Mean of picture × u / v. The graph of the picture against v / u is a straight line through the origin whose slope is the height of the candle.' };
    },
    tol: 0.03,
    chips: ['Why is the picture upside down?', 'What happens if the hole is bigger?', 'Why does the picture get fainter?', 'Check my readings', 'Why is there no focusing to do?'],
    viva: [['Why is the image of a pin hole camera inverted?', ['The rays cross at the hole', 'The paper is thin', 'Light bends at the hole'], 0, 'A straight ray from the top of the object reaches the bottom of the screen.'],
      ['The inner box is pulled further out (v larger). The picture?', ['Gets bigger and fainter', 'Gets smaller', 'Does not change'], 0, 'Picture = h v / u, and the same light covers a larger area.'],
      ['A bigger hole gives?', ['A brighter but blurred picture', 'A sharper picture', 'No picture'], 0, 'Every point of the object spreads into a circle the size of the hole.']],
    askState: function () {
      var v = view || sync();
      return { hole_made: st.hole, hole_diameter_mm: +st.dpMm.toFixed(2), candle_lit: st.lit,
        candle_to_hole_cm: +st.uCm.toFixed(1), box_length_cm: +st.vCm.toFixed(1),
        picture_height_cm: (st.hole && st.lit) ? +(v.img_h * 100).toFixed(2) : null,
        blur_circle_mm: +(v.blur * 1000).toFixed(2), magnification_v_over_u: +v.mag.toFixed(3), readings_taken: S.rows.length };
    },

    steps: [
      { id: 'make', title: 'Make the camera', view: 'cam', render: function (u) {
          u.h2('Prick the hole and light the candle');
          u.p('The camera is two cardboard boxes, one sliding inside the other, with tracing paper across the back of the inner one. Prick a small round hole in the middle of the front face, light the candle in front of it, and look at the paper from behind.');
          u.task('1. Prick the pin hole', st.hole, st.hole ? 'A small round hole, in the middle of the front face' : 'Use the pin lying on the bench')
            .add(u.button('Make the hole with the pin', function () { makeHole(); }, !st.hole, st.hole || S.hand.busy));
          u.task('2. Light the candle', st.lit, st.lit ? 'Lit, ' + st.uCm.toFixed(1) + ' cm in front of the hole' : 'Not lit yet')
            .add(u.button('Light the candle', function () { lightCandle(); }, !st.lit, st.lit || S.hand.busy));
          u.task('3. Look at the tracing paper', st.looked, st.looked ? 'The picture is upside down' : 'Look from behind the box')
            .add(u.button('Look at the tracing paper', function () { lookAtPaper(); }, !st.looked, S.hand.busy || !st.hole || !st.lit));
          u.note('Work in a dim corner: the picture is faint. Never make the hole with a pencil - it must be small and round.');
          u.next('Next: measure the picture', st.hole && st.lit && st.looked);
        },
        ok: function () { return st.hole && st.lit && st.looked; },
        auto: function () { return makeHole().then(function () { return lightCandle(); }).then(function () { return lookAtPaper(); }); } },
      { id: 'measure', title: 'Measure the picture', view: 'paper', render: function (u) {
          u.h2('Read u, v and the height of the picture');
          u.p('The tracing paper has a millimetre scale down one side. For each pair of distances, read the height of the picture and write down u, v and that height. At least three pairs.');
          u.task('Candle', true, 'At ' + st.uCm.toFixed(1) + ' cm from the hole');
          u.slider('Candle to the hole (u)', 25, 80, 1, function () { return st.uSet; }, function (x) { st.uSet = x; }, 'cm', 0);
          u.row(u.button('Move the candle there', function () { moveCandle(st.uSet); S.render(); }, true, S.hand.busy));
          u.task('Inner box', true, 'Pulled out to v = ' + st.vCm.toFixed(1) + ' cm');
          u.slider('Length of the box (v)', 8, 28, 1, function () { return st.vSet; }, function (x) { st.vSet = x; }, 'cm', 0);
          u.row(u.button('Slide the inner box there', function () { slideInner(st.vSet); S.render(); }, true, S.hand.busy),
            u.button('Look at the paper', function () { update(); S.focus('paper'); }));
          u.live(function () { var v = view || sync(); return 'Picture: ' + (v.img_h * 100).toFixed(2) + ' cm tall, blur circle ' + (v.blur * 1000).toFixed(2) + ' mm'; });
          u.row(u.button('Record u, v and the picture', function () { record(); }, true, S.hand.busy));
          u.h3('Observation table'); u.table();
          u.next('Next: graph and result', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 pairs recorded.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          return [[30, 25], [40, 20], [30, 20], [50, 25]].reduce(function (pr, q) {
            return pr.then(function () { st.uSet = q[0]; return moveCandle(q[0]); })
              .then(function () { st.vSet = q[1]; return slideInner(q[1]); })
              .then(function () { record(); });
          }, Promise.resolve());
        } },
    ],

    tick: function () { update(); },
  };
});
