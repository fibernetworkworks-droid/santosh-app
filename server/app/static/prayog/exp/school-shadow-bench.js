/* Prayogshala studio module: Shadows on a bench (NCERT Class VI-VII, Light, Shadows and Reflections).
   A lamp house at the zero of a metre scale, an opaque card standing on a sliding block, and a white screen with a
   centimetre scale. A straight pipe and a bent pipe lie beside the bench for the first check: light travels in
   straight lines. Every number comes from the `shadowbox` kernel - the ray from the lamp grazing the top of the
   card gives the edge of the shadow (shadow, umbra, pen, see). */
HoolaStudio.define('school-shadow-bench', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.shadowbox;
  var p = window.HoolaKernels.paramsFor('shadowbox', S.lab.params);
  var XL = -0.52, BZ = -0.12, YB = 0.006;                            // the lamp's x, the bench's z, the height of the bench top
  var SCR_H = 0.30, SCR_W = 0.3, OBJ_W = 0.05;
  var st = { on: false, aCm: 30, aSet: 30, dCm: 90, dSet: 90, straight: false, bent: false, pipe: 'none' };
  function xAt(cm) { return XL + cm / 100; }
  function round1(v) { return Math.round(v * 10) / 10; }
  function sync() { p.a = Math.max(0.05, st.aCm / 100); p.D = Math.max(p.a + 0.05, st.dCm / 100);
    p.bend = st.pipe === 'bent' ? 0.5 : 0; p.tilt = 0; return K.view(null, p); }

  // ---------- the bench and its metre scale
  var bench = new T.Group(); S.scene.add(bench);
  var plank = S.mesh(new T.BoxGeometry(1.35, 0.012, 0.22), M.wood); plank.position.set(XL + 0.6, YB - 0.006, BZ); bench.add(plank);
  var scaleTex = S.canvasTex(4096, 128, function (x, w, h) {
    x.fillStyle = '#f0ead8'; x.fillRect(0, 0, w, h); x.fillStyle = '#1a1a1a';
    var cm = 130, k = w / cm, i;
    for (i = 0; i <= cm; i++) { var xx = i * k, big = i % 10 === 0;
      x.fillRect(xx, 0, big ? 3 : 1.5, big ? 48 : (i % 5 === 0 ? 32 : 18));
      if (big) { x.font = '600 38px sans-serif'; x.fillText(String(i), xx + 5, 92); } }
  });
  var strip = new T.Mesh(new T.PlaneGeometry(1.3, 0.03), new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.6 }));
  strip.rotation.x = -Math.PI / 2; strip.position.set(XL + 0.65, YB + 0.0012, BZ + 0.07); bench.add(strip);
  S.contact(1.45, 0.3, XL + 0.6, BZ, 0.45);

  // ---------- the lamp house
  var lampG = new T.Group(); S.scene.add(lampG); lampG.position.set(XL, 0, BZ);
  var house = S.rounded(0.09, 0.1, 0.09, 0.008, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 }));
  house.rotation.x = -Math.PI / 2; house.position.y = YB + 0.05; lampG.add(house);
  var hole = new T.Mesh(new T.CircleGeometry(0.016, 24), new T.MeshBasicMaterial({ color: 0x1a1a1a })); hole.rotation.y = Math.PI / 2;
  hole.position.set(0.0455, YB + 0.05, 0); lampG.add(hole);
  var bulbM = new T.MeshStandardMaterial({ color: 0xfff6e0, emissive: 0x000000, roughness: 0.2 });
  var bulb = S.mesh(new T.SphereGeometry(0.012, 18, 12), bulbM); bulb.position.set(0.04, YB + 0.05, 0); lampG.add(bulb);
  var sw = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.008, 16), M.red); sw.rotation.x = Math.PI / 2; sw.position.set(0, YB + 0.02, 0.046); lampG.add(sw);
  var lampLab = S.label('LAMP', { w: 0.04, ratio: 0.26, color: '#e6e8ec', weight: 700 });
  lampLab.rotation.x = -Math.PI / 2; lampLab.position.set(0, YB + 0.101, 0); lampG.add(lampLab);
  var pl = new T.PointLight(0xfff0d0, 0, 2.2, 2); pl.position.set(0.05, YB + 0.05, 0); lampG.add(pl);
  var glow = new T.Sprite(new T.SpriteMaterial({ map: S.canvasTex(128, 128, function (x) {
    var g = x.createRadialGradient(64, 64, 2, 64, 64, 62); g.addColorStop(0, 'rgba(255,245,210,0.9)'); g.addColorStop(1, 'rgba(255,220,150,0)');
    x.fillStyle = g; x.fillRect(0, 0, 128, 128); }), transparent: true, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending }));
  glow.scale.set(0.09, 0.09, 1); glow.position.set(0.05, YB + 0.05, 0); glow.visible = false; lampG.add(glow);

  // ---------- the opaque card on its sliding block
  var objG = new T.Group(); S.scene.add(objG); objG.position.set(xAt(st.aCm), 0, BZ);
  var block = S.rounded(0.05, 0.04, 0.03, 0.004, M.darkWood); block.rotation.x = -Math.PI / 2; block.position.y = YB + 0.015; objG.add(block);
  var cardM = new T.MeshStandardMaterial({ color: 0x1d1f24, roughness: 0.9 });
  var objCard = S.mesh(new T.BoxGeometry(0.004, 1, OBJ_W), cardM); objG.add(objCard);
  var objMark = S.label('OBJECT', { w: 0.03, ratio: 0.3, color: '#cfd3d9', weight: 700 });
  objMark.rotation.y = Math.PI / 2; objMark.position.set(-0.003, YB + 0.012, 0); objG.add(objMark);
  var objSh = S.contact(0.08, 0.08, xAt(st.aCm), BZ, 0.4, YB);

  // ---------- the screen with its centimetre scale
  var scrG = new T.Group(); S.scene.add(scrG); scrG.position.set(xAt(st.dCm), 0, BZ);
  var foot = S.rounded(0.06, 0.07, 0.016, 0.004, M.iron); foot.rotation.x = -Math.PI / 2; foot.position.y = YB + 0.008; scrG.add(foot);
  var shadTex = S.liveTex(256, Math.round(256 * SCR_H / SCR_W));
  var scrCard = S.mesh(new T.BoxGeometry(0.004, SCR_H, SCR_W), new T.MeshStandardMaterial({ color: 0xeeece4, roughness: 0.95 }));
  scrCard.position.y = YB + SCR_H / 2; scrG.add(scrCard);
  var shadPlane = new T.Mesh(new T.PlaneGeometry(SCR_W, SCR_H), new T.MeshBasicMaterial({ map: shadTex, transparent: true, depthWrite: false, toneMapped: false }));
  shadPlane.rotation.y = -Math.PI / 2; shadPlane.position.set(-0.0022, YB + SCR_H / 2, 0); shadPlane.renderOrder = 4; scrG.add(shadPlane);
  var scrScaleTex = S.canvasTex(128, 1024, function (x, w, h) {
    x.fillStyle = '#fbf8ef'; x.fillRect(0, 0, w, h); x.fillStyle = '#1a1a1a';
    var cm = 30, k = h / cm, i;
    for (i = 0; i <= cm; i++) { var yy = h - i * k, big = i % 5 === 0;
      x.fillRect(0, yy - 1, big ? 46 : 26, big ? 3 : 1.6);
      if (big) { x.font = '600 26px sans-serif'; x.fillText(String(i), 52, yy + 9); } }
  });
  var scrScale = new T.Mesh(new T.PlaneGeometry(0.03, SCR_H), new T.MeshStandardMaterial({ map: scrScaleTex, roughness: 0.7 }));
  scrScale.rotation.y = -Math.PI / 2; scrScale.position.set(-0.0024, YB + SCR_H / 2, -SCR_W / 2 + 0.018); scrScale.renderOrder = 5; scrG.add(scrScale);

  // ---------- the two pipes, in a rack in front of the bench
  function pipe(bent) {
    var g = new T.Group(); S.scene.add(g);
    var mat = new T.MeshStandardMaterial({ color: bent ? 0x8a5a32 : 0x5f646b, roughness: 0.6 });
    if (!bent) { var tube = S.mesh(new T.CylinderGeometry(0.011, 0.011, p.plen, 20, 1, true), mat); tube.rotation.z = Math.PI / 2; g.add(tube); }
    else {
      var h1 = S.mesh(new T.CylinderGeometry(0.011, 0.011, p.plen / 2, 20, 1, true), mat); h1.rotation.z = Math.PI / 2; h1.position.x = -p.plen / 4; g.add(h1);
      var h2 = S.mesh(new T.CylinderGeometry(0.011, 0.011, p.plen / 2, 20, 1, true), mat); h2.rotation.set(0, 0, Math.PI / 2 - 0.5); h2.position.set(p.plen / 4 * Math.cos(0.5), p.plen / 4 * Math.sin(0.5), 0); g.add(h2);
    }
    return g;
  }
  var pipeS = pipe(false), pipeB = pipe(true);
  pipeS.position.set(XL + 0.54, YB + 0.014, BZ + 0.19); pipeB.position.set(XL + 0.54, YB + 0.014, BZ + 0.25);
  S.contact(0.36, 0.16, XL + 0.54, BZ + 0.22, 0.35, YB);

  // ---------- the light cone (two faint edges from the lamp over the top of the card)
  var coneMat = new T.LineBasicMaterial({ color: 0xffd98a, transparent: true, opacity: 0.55, depthWrite: false, toneMapped: false });
  var edges = [];
  for (var ei = 0; ei < 3; ei++) { var l = new T.Line(new T.BufferGeometry(), coneMat); l.visible = false; l.renderOrder = 7; S.scene.add(l); edges.push(l); }

  S.addApparatus('lamp', lampG, 'Lamp house', 'A clear lamp in a metal house with a small window: it acts as the source of light at the zero of the scale.');
  S.addApparatus('object', objG, 'Opaque card', 'A black card standing on a sliding block. Its height is what you have to find from its shadow.');
  S.addApparatus('screen', scrG, 'White screen', 'A white board with a centimetre scale along one edge: the shadow is measured on it.');
  S.addApparatus('pipes', pipeS, 'Straight and bent pipes', 'Look at the lamp through each of them: the lamp is seen only through the straight one, because light travels in straight lines.');
  S.addApparatus('bench', bench, 'Bench with a metre scale', 'The lamp stands at zero; the card and the screen are read on this scale.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hudA = S.hudCard('Lamp → object (a)'), hudD = S.hudCard('Lamp → screen (D)'), hudS = S.hudCard('Shadow on the screen');

  var view = null;
  function update() {
    var v = sync(); view = v;
    objG.position.x = xAt(st.aCm); objSh.position.x = xAt(st.aCm);
    scrG.position.x = xAt(st.dCm);
    objCard.scale.y = p.h; objCard.position.y = YB + p.h / 2;
    bulbM.emissive.setRGB(st.on ? 1 : 0, st.on ? 0.94 : 0, st.on ? 0.78 : 0);
    pl.intensity = st.on ? 0.1 : 0; glow.visible = st.on;
    shadTex.draw(function (x, w, h) {
      x.clearRect(0, 0, w, h);
      if (!st.on) return;
      var pxm = h / SCR_H, wid = OBJ_W * p.D / p.a * pxm, top = h - v.shadow * pxm, soft = Math.max(0.6, v.pen * pxm * 0.5);
      x.save(); x.filter = 'blur(' + soft.toFixed(1) + 'px)';
      x.fillStyle = 'rgba(20,20,24,0.88)';
      x.fillRect(w / 2 - wid / 2, top, wid, h - top);
      x.restore();
    });
    edges.forEach(function (l) { l.visible = false; });
    if (st.on) {
      var pts = [[[0, 0], [p.a, p.h], [p.D, v.shadow]], [[0, 0], [p.D, 0]], [[0, 0], [p.a, p.h * 0.0], [p.D, 0]]];
      [0, 1].forEach(function (k) {
        var l = edges[k];
        l.geometry.setFromPoints(pts[k].map(function (q) { return new T.Vector3(XL + q[0], YB + q[1], BZ); }));
        l.visible = true;
      });
    }
    hudA.set(st.aCm.toFixed(1) + ' cm'); hudD.set(st.dCm.toFixed(1) + ' cm');
    hudS.set(st.on ? (v.shadow * 100).toFixed(1) + ' cm tall' : 'lamp is off');
  }

  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function lampSwitch() {
    if (S.hand.busy) return wait();
    return S.hand.tap(sw).then(function () {
      st.on = !st.on; update(); S.render();
      S.say(st.on ? 'The lamp is on. A sharp shadow of the card falls on the screen.' : 'The lamp is off.');
      return true;
    });
  }
  function slide(which, toCm) {
    if (S.hand.busy) return wait();
    var from = which === 'o' ? st.aCm : st.dCm, g = which === 'o' ? objG : scrG;
    var lo = which === 'o' ? 10 : 40, hi = which === 'o' ? 60 : 110;
    toCm = round1(toCm);
    if (!(toCm >= lo && toCm <= hi)) { S.say((which === 'o' ? 'The card' : 'The screen') + ' slides from ' + lo + ' cm to ' + hi + ' cm on this bench.'); return Promise.resolve(false); }
    if (which === 'o' && toCm > st.dCm - 20) { S.say('Keep the card at least 20 cm in front of the screen.'); return Promise.resolve(false); }
    if (which === 'd' && toCm < st.aCm + 20) { S.say('Keep the screen at least 20 cm behind the card.'); return Promise.resolve(false); }
    if (Math.abs(toCm - from) < 0.05) { if (which === 'o') st.aCm = toCm; else st.dCm = toCm; update(); return Promise.resolve(true); }
    function at(k) { return from + (toCm - from) * k; }
    var gy = which === 'o' ? YB + p.h + 0.01 : YB + SCR_H - 0.03;
    return S.hand.pinchMove(new T.Vector3(xAt(from), gy, BZ), function (k) { return new T.Vector3(xAt(at(k)), gy, BZ); },
      function (k) { if (which === 'o') st.aCm = at(k); else st.dCm = at(k); update(); },
      { ms: Math.min(1600, 420 + Math.abs(toCm - from) * 25), reachMs: 550, hold: 120 })
      .then(function () { if (which === 'o') st.aCm = toCm; else st.dCm = toCm; update(); S.render(); void g; return true; });
  }
  function lookThrough(kind) {
    if (S.hand.busy) return wait();
    var g = kind === 'bent' ? pipeB : pipeS;
    st.pipe = kind;
    var eye = new T.Vector3(XL + 0.78, YB + 0.12, BZ + 0.16);
    return S.hand.pinchMove(new T.Vector3(g.position.x, g.position.y + 0.02, g.position.z), function (k) {
      return new T.Vector3(g.position.x + (eye.x - g.position.x) * k, g.position.y + (eye.y - g.position.y) * k, g.position.z + (eye.z - g.position.z) * k);
    }, function (k) { g.position.lerpVectors(new T.Vector3(g.position.x, g.position.y, g.position.z), eye, 0); void k; }, { ms: 700, reachMs: 500, hold: 300 })
      .then(function () {
        var v = sync();
        if (kind === 'bent') st.bent = true; else st.straight = true;
        st.pipe = 'none'; update(); S.render();
        S.say(v.see ? 'Through the straight pipe the lamp is seen clearly: the light comes straight down the bore.'
          : 'Through the bent pipe nothing is seen, however the pipe is turned: light does not bend round the corner.');
        return true;
      });
  }
  function record() {
    if (S.hand.busy) { wait(); return false; }
    if (!st.on) { S.say('Switch the lamp on first.'); return false; }
    var v = sync(), a = round1(st.aCm), D = round1(st.dCm), sh = round1(v.shadow * 100);   // the screen scale reads to 1 mm
    if (S.rows.some(function (r) { return Math.abs(r.a - a) < 2 && Math.abs(r.D - D) < 2; })) { S.say('You already have a reading at a = ' + a.toFixed(1) + ' cm. Move the card or the screen.'); return false; }
    S.addRow({ a: a, D: D, sh: sh });
    S.say('Written in your record book: a = ' + a.toFixed(1) + ' cm, D = ' + D.toFixed(1) + ' cm, shadow = ' + sh.toFixed(1) + ' cm.');
    return true;
  }

  var VIEWS = { bench: [[XL + 0.6, 0.72, BZ + 1.4], [XL + 0.55, 0.06, BZ]], lamp: [[XL + 0.22, 0.16, BZ + 0.22], [XL + 0.02, YB + 0.05, BZ]],
    object: [[xAt(30) + 0.16, 0.14, BZ + 0.2], [xAt(30), YB + 0.03, BZ]], screen: [[xAt(90) - 0.46, YB + 0.26, BZ + 0.42], [xAt(90), YB + 0.1, BZ]],
    pipes: [[XL + 0.78, 0.46, BZ + 0.9], [XL + 0.54, 0.02, BZ + 0.16]],
    book: [[-0.4, 0.44, 0.5], [-0.5, 0.0, 0.08]] };
  update();

  function hMean(rows) {
    var hs = (rows || []).filter(function (r) { return r.D > 0; }).map(function (r) { return r.sh * r.a / r.D; });
    return hs.length ? S.fit.mean(hs) : NaN;
  }

  return {
    camera: { pos: [XL + 0.62, 0.78, BZ + 1.5], look: [XL + 0.55, 0.06, BZ] },
    views: VIEWS,
    theory: { principle: 'Light travels in straight lines. An opaque object in its way cuts out a part of the light, and on a screen behind it there is a dark patch with a sharp edge: a shadow. The ray that just grazes the top of the object marks the edge of the shadow, and the two triangles it makes are similar, so the shadow grows in the same ratio as the distances.',
      formula: 'shadow / object = D / a',
      formulaNote: 'a = lamp to object, D = lamp to screen · so the object’s height = shadow × a / D',
      more: ['Move the object towards the lamp and the shadow grows; move it towards the screen and the shadow shrinks until it is the size of the object itself.',
        'A real lamp has a filament of some size, so the border of the shadow is not perfectly sharp: there is a full shadow (the umbra) with a faint band round it (the penumbra). The sharp geometrical edge lies in the middle of that band.',
        'The straight and bent pipes are the simplest proof that light travels in straight lines, and so is a pinhole camera.'],
      precautions: 'Keep the lamp, the card and the screen in one straight line along the bench, and the card upright. Read the screen scale with your eye level with the top of the shadow. The lamp gets hot: switch it off before you move it.' },
    book: { title: 'Expt. — Shadows on a bench', lines: ['Aim: to show that light travels in straight lines and to find the height of a card from its shadow.',
      'Lamp at the zero of the bench scale.', 'a = lamp → card,  D = lamp → screen', 'shadow / object = D / a', 'So object = shadow × a / D.'],
      columns: [{ label: 'No.', get: function (r, i) { return i + 1; } }, { label: 'a (cm)', get: function (r) { return r.a.toFixed(1); } },
        { label: 'D (cm)', get: function (r) { return r.D.toFixed(1); } }, { label: 'shadow (cm)', get: function (r) { return r.sh.toFixed(1); } },
        { label: 'D / a', get: function (r) { return (r.D / r.a).toFixed(2); } }, { label: 'height (cm)', get: function (r) { return (r.sh * r.a / r.D).toFixed(2); } }] },
    graph: { x: function (r) { return r.D / r.a; }, y: function (r) { return r.sh; }, xlabel: 'D / a', ylabel: 'shadow (cm)', x0: 0, y0: 0,
      line: function (pts) { var m = S.fit.origin(pts); return isFinite(m) ? function (x) { return m * x; } : null; } },
    result: function (rows) {
      var h = hMean(rows); if (!isFinite(h) || (rows || []).length < 3) return null;
      return { label: 'height of the card', value: h, unit: 'cm', digits: 2, truth: p.h * 100,
        note: 'Mean of shadow × a / D. The graph of the shadow against D / a is a straight line through the origin whose slope is the height of the card.' };
    },
    tol: 0.02,
    chips: ['Why does the shadow grow when the card comes nearer the lamp?', 'What is the penumbra?', 'Why is nothing seen through the bent pipe?', 'Check my readings', 'Why is a shadow always black?'],
    viva: [['The card is moved closer to the lamp. The shadow?', ['Gets bigger', 'Gets smaller', 'Does not change'], 0, 'a gets smaller, so D / a gets larger.'],
      ['Why is the edge of a shadow from a big lamp not sharp?', ['The lamp is not a point, so there is a penumbra', 'Light bends at the edge', 'The screen is rough'], 0, 'Different points of the filament cast slightly different shadows.'],
      ['Nothing is seen through the bent pipe because?', ['Light travels in straight lines', 'The pipe is too narrow', 'The lamp is too dim'], 0, 'Light cannot turn the corner inside the pipe.']],
    askState: function () {
      var v = view || sync();
      return { lamp_on: st.on, lamp_to_object_cm: +st.aCm.toFixed(1), lamp_to_screen_cm: +st.dCm.toFixed(1),
        shadow_height_cm: st.on ? +(v.shadow * 100).toFixed(1) : null, penumbra_band_cm: +(v.pen * 100).toFixed(2),
        magnification_D_over_a: +v.mag.toFixed(2), straight_pipe_tried: st.straight, bent_pipe_tried: st.bent,
        readings_taken: S.rows.length };
    },

    steps: [
      { id: 'straight', title: 'Light travels in straight lines', view: 'pipes', render: function (u) {
          u.h2('Look at the lamp through the two pipes');
          u.p('Two pipes of the same bore lie beside the bench: one straight, one bent in the middle. Switch the lamp on and look at it through each of them.');
          u.task('1. Switch the lamp on', st.on, st.on ? 'The lamp is on' : 'The switch is on the side of the house')
            .add(u.button(st.on ? 'Switch the lamp off' : 'Switch the lamp on', function () { lampSwitch(); }, !st.on, S.hand.busy));
          u.task('2. The straight pipe', st.straight, st.straight ? 'The lamp is seen clearly' : 'Not tried yet')
            .add(u.button('Look through the straight pipe', function () { lookThrough('straight'); }, !st.straight, S.hand.busy || !st.on));
          u.task('3. The bent pipe', st.bent, st.bent ? 'Nothing is seen through it' : 'Not tried yet')
            .add(u.button('Look through the bent pipe', function () { lookThrough('bent'); }, !st.bent, S.hand.busy || !st.on));
          u.note('The same thing is shown by three cards with a hole each: the lamp is seen only when the three holes are in one straight line.');
          u.next('Next: measure the shadow', st.straight && st.bent);
        },
        ok: function () { return st.straight && st.bent; },
        auto: function () {
          return (st.on ? Promise.resolve(true) : lampSwitch()).then(function () { return lookThrough('straight'); }).then(function () { return lookThrough('bent'); });
        } },
      { id: 'shadow', title: 'Measure the shadow', view: 'screen', render: function (u) {
          u.h2('How big is the shadow?');
          u.p('Put the card at a distance from the lamp, read the height of its shadow on the screen scale, and write down a, D and the shadow. Then move the card and do it again. At least three positions.');
          u.task('Card', true, 'At ' + st.aCm.toFixed(1) + ' cm from the lamp');
          u.slider('Lamp to card (a)', 10, 60, 1, function () { return st.aSet; }, function (x) { st.aSet = x; }, 'cm', 0);
          u.row(u.button('Move the card there', function () { slide('o', st.aSet); S.render(); }, true, S.hand.busy),
            u.button('Look at the screen', function () { update(); S.focus('screen'); }));
          u.task('Screen', true, 'At ' + st.dCm.toFixed(1) + ' cm from the lamp');
          u.slider('Lamp to screen (D)', 40, 110, 1, function () { return st.dSet; }, function (x) { st.dSet = x; }, 'cm', 0);
          u.row(u.button('Move the screen there', function () { slide('d', st.dSet); S.render(); }, true, S.hand.busy));
          u.live(function () { var v = view || sync(); return st.on ? 'Shadow: ' + (v.shadow * 100).toFixed(1) + ' cm tall, with a ' + (v.pen * 100).toFixed(2) + ' cm faint band round it' : 'The lamp is off'; });
          u.row(u.button('Record a, D and the shadow', function () { record(); }, true, S.hand.busy));
          u.h3('Observation table'); u.table();
          u.next('Next: graph and result', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 positions recorded.');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          return [[20, 90], [30, 90], [40, 90], [30, 105]].reduce(function (pr, q) {
            return pr.then(function () { st.dSet = q[1]; return slide('d', q[1]); })
              .then(function () { st.aSet = q[0]; return slide('o', q[0]); })
              .then(function () { record(); });
          }, st.on ? Promise.resolve(true) : lampSwitch());
        } },
    ],

    tick: function () { update(); },
  };
});
