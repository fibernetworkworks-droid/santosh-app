/* Prayogshala studio rig: atmospheric pressure with a rubber sucker (NCERT Class VIII, Force and Pressure).
   A thick plate glass sheet on the laboratory table, a tray of four rubber suction cups (8, 10, 12 and 14 mm), a
   vernier calliper to measure each one, and a spring balance (0-20 N, least count 0.1 N) hooked to the sucker's ring.
   The gloved hand presses a sucker on the glass to drive the air out, measures it with the calliper, then pulls the
   balance straight up until the sucker comes off and reads the force. Force plotted against area is a straight line
   through the origin whose slope is the pressure of the air.
   Physics: the `sucker` kernel of the mech_school pack. Every number comes from S.lab.params. */
HoolaStudio.define('sucker-pressure', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.sucker;
  var p = window.HoolaKernels.paramsFor('sucker', S.lab.params);
  p.P = 0;
  var vs = (S.lab.variant || {}).sample || '';
  var D = [0.008, 0.010, 0.012, 0.014];                   // the four suckers, metres
  var FULL = 20, LC = 0.1, LCD = 0.00002, RATE = 6;       // balance full scale / least count, calliper l.c., pull rate

  var st = { cur: -1, pressed: false, d: 0, pulling: false, off: false, done: false, reading: 0, lift: 0, onDone: null, busy: false };
  var sim = K.init(p);

  // ---------- geometry
  var GX = -0.06, GZ = -0.06, GT = 0.012, SY = GT;
  var glass = S.rounded(0.3, 0.22, GT, 0.004, new T.MeshPhysicalMaterial({ color: 0xe8f2f6, roughness: 0.02, transmission: 0.92, thickness: 0.012, ior: 1.52, transparent: true, opacity: 0.45 }));
  glass.rotation.x = -Math.PI / 2; glass.position.set(GX, GT / 2, GZ); S.scene.add(glass);
  S.contact(0.36, 0.28, GX, GZ, 0.4);
  var gl = S.label('PLATE GLASS — clean and smooth', { w: 0.12, ratio: 0.14, color: '#3a4652' });
  gl.rotation.x = -Math.PI / 2; gl.position.set(GX, GT + 0.0008, GZ + 0.09); S.scene.add(gl);

  // the four suckers; each sits on the tray until it is pressed on the glass
  var TRAY = new T.Vector3(0.34, 0, 0.04);
  var tray = S.rounded(0.17, 0.1, 0.014, 0.005, M.darkWood);
  tray.rotation.x = -Math.PI / 2; tray.position.set(TRAY.x, 0.007, TRAY.z); S.scene.add(tray);
  S.contact(0.24, 0.17, TRAY.x, TRAY.z, 0.5);
  var tl = S.label('SUCKERS  8 · 10 · 12 · 14 mm', { w: 0.13, ratio: 0.13, color: '#f1e3c0' });
  tl.rotation.x = -Math.PI / 2; tl.position.set(TRAY.x, 0.0145, TRAY.z + 0.038); S.scene.add(tl);

  var SUCK = D.map(function (d, i) {
    var g = new T.Group();
    var rub = new T.MeshStandardMaterial({ color: 0x2a2a2c, roughness: 0.8 });
    var cup = S.mesh(new T.CylinderGeometry(d / 2, d / 2 * 0.72, 0.008, 28), rub); cup.position.y = 0.004; g.add(cup);
    var neck = S.mesh(new T.CylinderGeometry(0.0022, 0.0028, 0.016, 14), rub); neck.position.y = 0.016; g.add(neck);
    var ring = S.mesh(new T.TorusGeometry(0.0062, 0.0016, 8, 22), M.chrome); ring.position.y = 0.029; ring.rotation.y = Math.PI / 2; g.add(ring);
    var lb = S.label(Math.round(d * 1000) + ' mm', { w: 0.022, ratio: 0.42, color: '#e8eef6' });
    lb.rotation.x = -Math.PI / 2; lb.position.y = 0.0085; g.add(lb);
    var home = new T.Vector3(TRAY.x - 0.06 + i * 0.04, 0.014, TRAY.z - 0.012);
    g.position.copy(home); S.scene.add(g);
    return { d: d, grp: g, home: home, ringY: 0.029 };
  });

  // the spring balance, hanging above the sucker
  var CASE_H = 0.18, ROD0 = 0.02;
  var bal = new T.Group(); S.scene.add(bal);
  var shell = S.rounded(0.04, CASE_H, 0.028, 0.008, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.45, metalness: 0.3 }));
  shell.position.set(0, CASE_H / 2, 0); bal.add(shell);
  var balTex = S.canvasTex(300, 2048, function (x, w, h) {
    x.fillStyle = '#f4efe0'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#17181a'; x.textAlign = 'left';
    var n = Math.round(FULL / LC);
    for (var i = 0; i <= n; i++) {
      var py = 40 + i / n * (h - 80), big = i % 10 === 0, mid = i % 5 === 0;
      x.fillRect(0, py - (big ? 2 : 1), big ? 108 : mid ? 74 : 42, big ? 4 : 2);
      if (big) { x.font = '700 54px "Public Sans", sans-serif'; x.fillText(String(Math.round(i * LC)), 122, py + 19); }
    }
    x.save(); x.translate(252, h / 2); x.rotate(Math.PI / 2);
    x.font = '600 44px "Public Sans", sans-serif'; x.fillStyle = '#6b4a14'; x.textAlign = 'center';
    x.fillText('NEWTON  0 – ' + FULL + ' N   l.c. 0.1 N', 0, 0); x.restore();
  });
  var bface = new T.Mesh(new T.PlaneGeometry(0.028, CASE_H - 0.012), new T.MeshStandardMaterial({ map: balTex, roughness: 0.5 }));
  bface.position.set(0, CASE_H / 2, 0.0142); bal.add(bface);
  var bptr = S.mesh(new T.BoxGeometry(0.032, 0.0022, 0.002), M.red); bptr.position.set(0, CASE_H - 0.01, 0.0156); bal.add(bptr);
  var brod = S.mesh(new T.CylinderGeometry(0.0032, 0.0032, 1, 12), M.chrome, true, false); bal.add(brod);
  var bhook = S.mesh(new T.TorusGeometry(0.0062, 0.0016, 8, 22), M.chrome); bhook.rotation.y = Math.PI / 2; bal.add(bhook);
  var topRing = S.mesh(new T.TorusGeometry(0.013, 0.0028, 10, 26), M.chrome); topRing.rotation.y = Math.PI / 2; bal.add(topRing);
  bal.visible = false;

  // vernier callipers lying on the bench
  var cal = new T.Group(); cal.position.set(0.28, 0, -0.2); S.scene.add(cal);
  var beam = S.rounded(0.2, 0.008, 0.024, 0.002, M.chrome); beam.position.set(0, 0.004, 0); cal.add(beam);
  var jawF = S.rounded(0.008, 0.008, 0.05, 0.002, M.chrome); jawF.position.set(-0.096, 0.004, -0.03); cal.add(jawF);
  var slide = S.rounded(0.045, 0.012, 0.028, 0.003, M.chrome); slide.position.set(-0.05, 0.006, 0.002); cal.add(slide);
  var jawS = S.rounded(0.007, 0.008, 0.046, 0.002, M.chrome); jawS.position.set(-0.07, 0.004, -0.028); cal.add(jawS);
  var cl = S.label('VERNIER  0.02 mm', { w: 0.08, ratio: 0.16, color: '#20262c' });
  cl.rotation.x = -Math.PI / 2; cl.position.set(0.03, 0.0085, 0.006); cal.add(cl);
  S.contact(0.26, 0.12, 0.28, -0.2, 0.5);

  S.addApparatus('glass', glass, 'Plate glass sheet', 'Thick, clean and perfectly smooth, so no air can leak in under the sucker.');
  S.addApparatus('suckers', SUCK[0].grp, 'Rubber suckers (8–14 mm)', 'Four suction cups of different diameter. Pressed down, they drive the air out from under themselves.');
  S.addApparatus('balance', bal, 'Spring balance (0–' + FULL + ' N)', 'Least count 0.1 N. Pulled straight up, it reads the force at which the sucker comes off.');
  S.addApparatus('cal', cal, 'Vernier callipers', 'Least count 0.02 mm. Used to measure the diameter of each sucker\'s face.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudS = S.hudCard('Sucker'), hudP = S.hudCard('Balance reads'), hudO = S.hudCard('State');

  // ---------- helpers
  function area(d) { return Math.PI * d * d / 4; }
  function cur() { return st.cur >= 0 ? SUCK[st.cur] : null; }
  function ext() { return (p.P / FULL) * 0.03; }
  function suckerY() { return SY + st.lift; }
  function ringWorld() {
    var c = cur();
    if (!c) return new T.Vector3(GX, SY + 0.3, GZ);
    return new T.Vector3(GX, suckerY() + c.ringY + ext() + ROD0 + CASE_H + 0.013, GZ);
  }
  function along(pts) {
    var L = [0], i;
    for (i = 1; i < pts.length; i++) L.push(L[i - 1] + pts[i].distanceTo(pts[i - 1]));
    return function (k) {
      var d = Math.max(0, Math.min(1, k)) * L[L.length - 1], j, f;
      for (j = 1; j < pts.length; j++) if (d <= L[j] || j === pts.length - 1) {
        f = (d - L[j - 1]) / Math.max(1e-9, L[j] - L[j - 1]);
        return pts[j - 1].clone().lerp(pts[j], Math.min(1, f));
      }
      return pts[pts.length - 1].clone();
    };
  }
  function pose() {
    var c = cur();
    if (c) {
      c.grp.position.set(GX, suckerY(), GZ);
      bal.visible = true;
      var hookY = suckerY() + c.ringY + 0.006 + ext();
      bal.position.set(GX, hookY, GZ);
      brod.scale.set(1, Math.max(1e-4, ROD0), 1); brod.position.y = ROD0 / 2;
      bhook.position.y = -0.001;
      shell.position.y = ROD0 + CASE_H / 2; bface.position.y = ROD0 + CASE_H / 2;
      topRing.position.y = ROD0 + CASE_H + 0.013;
      bptr.position.y = ROD0 + 0.006 + (p.P / FULL) * (CASE_H - 0.012);
    } else bal.visible = false;
    hudS.set(c ? Math.round(c.d * 1000) + ' mm' : 'none on the glass');
    hudP.set(p.P.toFixed(1) + ' N');
    hudO.set(st.off ? 'came off at ' + st.reading.toFixed(1) + ' N' : st.pulling ? 'pulling' : st.pressed ? 'pressed down' : 'ready');
  }

  // ---------- actions
  function putBack() {
    var c = cur();
    if (!c) return Promise.resolve();
    var from = c.grp.position.clone(), to = c.home.clone();
    var path = along([from, from.clone().setY(0.2), to.clone().setY(0.2), to]);
    var G = new T.Vector3(0, 0.03, 0);
    return S.hand.pinchMove(from.clone().add(G), function (k) { return path(k).add(G); },
      function (k) { c.grp.position.copy(path(k)); }, { ms: 1200 })
      .then(function () {
        c.grp.position.copy(to); st.cur = -1; st.pressed = false; st.off = false; st.lift = 0; p.P = 0;
        bal.visible = false; pose(); S.render();
      });
  }
  function press(i) {
    if (S.hand.busy || st.busy) return Promise.resolve();
    if (st.cur === i && st.pressed && !st.off) return Promise.resolve();
    st.busy = true;
    return putBack().then(function () {
      var c = SUCK[i], from = c.home.clone(), to = new T.Vector3(GX, SY, GZ);
      var path = along([from, from.clone().setY(0.2), to.clone().setY(0.1), to]);
      var G = new T.Vector3(0, 0.03, 0);
      return S.hand.pinchMove(from.clone().add(G), function (k) { return path(k).add(G); },
        function (k) { c.grp.position.copy(path(k)); }, { ms: 1500 })
        .then(function () {
          st.cur = i; st.pressed = true; st.off = false; st.lift = 0; p.P = 0; p.d = c.d;
          sim = K.init(p);
          st.d = Math.round(c.d / LCD) * LCD;
          pose(); S.render(); st.busy = false;
          S.say('The ' + Math.round(c.d * 1000) + ' mm sucker is pressed on the glass. The callipers read ' + (st.d * 1000).toFixed(2) + ' mm, so its area is ' + (area(st.d) * 1e6).toFixed(1) + ' mm².');
        });
    }).then(null, function (e) { st.busy = false; throw e; });
  }
  function waitDone() {
    if (S.fast) { S.advance(30, function () { return st.done; }); return Promise.resolve(); }
    return new Promise(function (res) { st.onDone = res; });
  }
  function pull() {
    if (S.hand.busy || st.busy || st.pulling) return Promise.resolve();
    if (!st.pressed) { S.say('Press a sucker on the glass first.'); return Promise.resolve(); }
    if (st.off) { S.say('That sucker is already off. Record the reading, then press the next one.'); return Promise.resolve(); }
    st.busy = true; p.P = 0; st.done = false; st.lift = 0; sim = K.init(p);
    return S.hand.reach(ringWorld(), 'top', 800).then(function () { return S.hand.shape('grip', 300); })
      .then(function () {
        st.pulling = true;
        S.hand.follow(function () { return ringWorld(); }, 'top', 6000);
        return waitDone();
      })
      .then(function () { return S.hand.away(500); })
      .then(function () {
        st.busy = false; st.pulling = false; pose(); S.render();
        S.say('The sucker came off at ' + st.reading.toFixed(1) + ' N.');
      });
  }
  function record() {
    if (S.hand.busy || st.busy) return;
    if (!st.off) { S.say('Pull until the sucker comes off, then record the reading.'); return; }
    if (S.rows.some(function (r) { return Math.abs(r.d - st.d) < 1e-9; })) { S.say('That sucker is already in the table.'); return; }
    S.addRow({ d: st.d, A: area(st.d), F: st.reading });
    S.say('Written in your record book: ' + (st.d * 1000).toFixed(2) + ' mm, ' + st.reading.toFixed(1) + ' N.');
  }

  pose();

  var EXP = {
    camera: { pos: [0.44, 0.54, 0.76], look: [0.02, 0.1, -0.04] },
    views: {
      glass: [[0.06, 0.3, 0.34], [-0.05, 0.03, -0.06]],
      suckers: [[0.34, 0.24, 0.26], [0.34, 0.02, 0.03]],
      balance: [[0.14, 0.3, 0.34], [-0.05, 0.16, -0.06]],
      cal: [[0.3, 0.24, 0.0], [0.28, 0.01, -0.2]],
      press: [[0.36, 0.48, 0.64], [0.04, 0.07, -0.04]],
      pull: [[0.34, 0.5, 0.68], [-0.02, 0.13, -0.05]],
      book: [[-0.52, 0.46, 0.5], [-0.6, 0.0, 0.08]]
    },
    theory: {
      principle: 'When a rubber sucker is pressed on a smooth plate the air under it is driven out, so the pressure '
        + 'inside falls almost to nothing while the atmosphere still presses on the outside. The plate then holds the '
        + 'sucker down with a force equal to the pressure of the air times the area of the sucker\'s face.',
      formula: 'F = (P outside − P inside) × A,   A = π d² / 4',
      formulaNote: 'so the slope of the force against area graph is the pressure of the air',
      more: ['One sucker on its own cannot give the pressure reliably, because its diameter is small and hard to '
        + 'measure. Four suckers of different size give four points, and the straight line through them is far '
        + 'steadier than any single reading.',
        'The line passes through the origin: a sucker of no area would need no force at all.',
        'The air pressure is not the same everywhere. It falls as you go higher, so the same sucker needs a smaller '
        + 'pull on a hill station than at the sea.'],
      precautions: 'Clean the glass and the face of the sucker, and press it down hard so no air is left under it. '
        + 'Pull straight up and slowly: a sideways or jerky pull peels the sucker off too early and gives a reading '
        + 'that is too small.'
    },
    book: {
      at: [-0.56, 0.1, 0.1],
      title: 'Expt. — Atmospheric pressure with a rubber sucker',
      lines: ['Aim: ' + S.lab.aim, 'Suckers 8, 10, 12 and 14 mm; vernier callipers, least count 0.02 mm',
        'Spring balance 0–' + FULL + ' N, least count 0.1 N',
        'A = π d² / 4,   P = F / A   (slope of F against A)',
        'Precautions: clean glass, press hard, pull straight up and slowly.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'd (mm)', get: function (r) { return (r.d * 1000).toFixed(2); } },
        { label: 'A (mm²)', get: function (r) { return (r.A * 1e6).toFixed(1); } },
        { label: 'F (N)', get: function (r) { return r.F.toFixed(1); } },
        { label: 'F/A (kPa)', get: function (r) { return (r.F / r.A / 1000).toFixed(1); } }]
    },
    graph: {
      x: function (r) { return r.A * 1e6; }, y: function (r) { return r.F; },
      xlabel: 'area of the sucker A (mm²)', ylabel: 'force to pull it off F (N)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var k = S.fit.origin(rows.map(function (r) { return [r.A, r.F]; }));
      return { label: 'P (air)', value: k, unit: 'Pa', digits: 0, truth: p.Patm,
        note: 'Slope of the force against area graph. 101325 Pa is the standard pressure at sea level.' };
    },
    tol: 0.05,
    chips: ['Why does a sucker stick to glass?', 'Why four suckers and not one?', 'Check my readings',
      'Why does a sucker not stick to a rough wall?', 'Does the pressure change on a hill?'],
    viva: [['The sucker is held down by', ['the air outside pressing on it', 'glue', 'the weight of the glass'], 0,
      'The air under it was driven out, so only the outside air presses.'],
    ['A sucker of twice the diameter needs a pull that is', ['about four times as large', 'twice as large', 'the same'], 0,
      'The area grows as the square of the diameter.'],
    ['The graph of F against A passes through the origin because', ['no area means no force', 'the balance is faulty', 'the glass is thick'], 0,
      'F = P × A, so F is zero when A is zero.']],
    askState: function () {
      return { place: vs, sucker_on_glass_mm: st.cur >= 0 ? Math.round(SUCK[st.cur].d * 1000) : null,
        calliper_reading_mm: st.cur >= 0 ? +(st.d * 1000).toFixed(2) : null,
        area_mm2: st.cur >= 0 ? +(area(st.d) * 1e6).toFixed(1) : null,
        balance_reads_N: +p.P.toFixed(1), sucker_came_off: st.off, force_when_it_came_off_N: st.reading,
        balance_full_scale_N: FULL, balance_least_count_N: LC, suckers_done: S.rows.length };
    },

    steps: [
      { id: 'press', title: 'Press a sucker down', view: 'press',
        render: function (u) {
          u.h2('Press a sucker on the glass');
          u.p('The hand takes a sucker from the tray, presses it hard on the clean glass so the air under it is '
            + 'driven out, and measures its face with the vernier callipers.');
          var r = u.row();
          SUCK.forEach(function (c, i) {
            var done = S.rows.some(function (q) { return Math.abs(q.d - Math.round(c.d / LCD) * LCD) < 1e-9; });
            r.appendChild(u.button((done ? '✓ ' : '') + Math.round(c.d * 1000) + ' mm', function () { press(i); },
              false, S.hand.busy || st.busy || st.pulling));
          });
          u.task('Sucker on the glass', st.pressed && !st.off,
            st.pressed ? (st.d * 1000).toFixed(2) + ' mm, area ' + (area(st.d) * 1e6).toFixed(1) + ' mm²' : 'none pressed yet');
          u.live(function () { return 'Balance reads ' + p.P.toFixed(1) + ' N · ' + (st.off ? 'sucker is off' : st.pressed ? 'holding' : 'waiting'); });
          u.note('Start with the 8 mm sucker and work up to the 14 mm one.');
          u.next('Next: pull it off', st.pressed && !S.hand.busy);
        },
        ok: function () { return st.pressed; },
        auto: function () { return press(0); } },

      { id: 'pull', title: 'Pull it off and read', view: 'pull',
        render: function (u) {
          u.h2('Pull straight up until it comes off');
          u.p('The hand grips the ring at the top of the balance and pulls slowly, straight up. Read the force at the '
            + 'instant the sucker lets go, then record it with the area. Press the next sucker and repeat.');
          var r = u.row();
          SUCK.forEach(function (c, i) {
            var done = S.rows.some(function (q) { return Math.abs(q.d - Math.round(c.d / LCD) * LCD) < 1e-9; });
            r.appendChild(u.button((done ? '✓ ' : '') + Math.round(c.d * 1000) + ' mm', function () { press(i); },
              false, S.hand.busy || st.busy || st.pulling || done));
          });
          u.row(u.button('Pull the balance up', function () { pull(); }, true, S.hand.busy || st.busy || !st.pressed || st.off),
            u.button('Record the reading', function () { record(); }, true, S.hand.busy || st.busy || !st.off));
          u.live(function () {
            return 'Sucker ' + (st.cur >= 0 ? Math.round(SUCK[st.cur].d * 1000) + ' mm' : '—') + ' · balance '
              + p.P.toFixed(1) + ' N · ' + (st.off ? 'came off at ' + st.reading.toFixed(1) + ' N' : st.pulling ? 'pulling' : 'holding');
          });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 4) u.p(S.rows.length + ' of 4 suckers done.');
          u.next('Next: graph and result', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          return SUCK.reduce(function (pr, c, i) {
            return pr.then(function () { return press(i); }).then(function () { return pull(); }).then(function () { record(); });
          }, Promise.resolve());
        } }
    ],

    tick: function (dt) {
      if (st.pulling) {
        if (!st.off) {
          p.P = Math.min(FULL, p.P + RATE * dt);
          K.step(sim, p, dt);
          if (sim.off > 0.5) { st.off = true; st.reading = Math.round(p.P / LC) * LC; p.P = 0; }
          else if (p.P >= FULL - 1e-9) {
            st.pulling = false; st.done = true; p.P = 0;
            S.say('The balance reached full scale and the sucker is still holding.');
            if (st.onDone) { var f0 = st.onDone; st.onDone = null; f0(); }
          }
        } else {
          st.lift = Math.min(0.05, st.lift + 0.25 * dt);
          if (st.lift >= 0.05) {
            st.pulling = false; st.done = true;
            if (st.onDone) { var f1 = st.onDone; st.onDone = null; f1(); }
          }
        }
      }
      pose();
    }
  };
  return EXP;
});
