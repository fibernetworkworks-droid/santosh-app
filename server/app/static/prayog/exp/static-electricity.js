/* Prayogshala studio rig: static electricity (NCERT Science VIII, Some Natural Phenomena).
   A dry bench with a polythene rod and a woollen duster serves two set-ups: two pith balls hanging side by side on
   threads, and a jar electroscope with two aluminium foil strips. Both are the same physics - two equal charges
   hanging apart until gravity, the thread and the Coulomb repulsion balance - and both are solved by the `estatic`
   kernel of packs/em_school.js, which finds the angle by bisection on the exact balance. */
HoolaStudio.define('static-electricity', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KE = HK.K.estatic;
  var p = HK.paramsFor('estatic', S.lab.params);
  var V_ = S.lab.variant || {}, BASE = V_.base || S.lab.id, SAMPLE = V_.sample || '';
  var LEAF = BASE === 'jar-electroscope';
  var KCOUL = 1.0 / (4 * Math.PI * 8.8541878128e-12);
  var L0 = p.Lth, LMIN = LEAF ? 0.03 : 0.1, LMAX = LEAF ? 0.09 : 0.3;
  var SCALE = LEAF ? 2.4 : 1.0;                       // the electroscope is drawn larger than life so the gap can be seen
  var st = { L: L0, targetL: L0, charged: false, rubs: 0, dry: false, traced: false };
  function solve() { p.Lth = st.L; p.charged = st.charged ? 1 : 0; }
  function theta() { solve(); return KE.theta(p); }
  function sep() { return 2 * p.Lth * Math.sin(theta()); }
  function sepRead() { return Math.round(sep() / 0.0002) * 0.0002; }    // a mm scale read with a hand lens
  function fmtN(v, d) { return String(+v.toFixed(d === undefined ? 2 : d)); }

  // ---------- the bench
  var tbl = S.rounded(1.0, 0.5, 0.014, 0.006, M.darkWood); tbl.rotation.x = -Math.PI / 2; tbl.position.set(0.0, 0.007, -0.22); S.scene.add(tbl);
  S.contact(1.06, 0.56, 0.0, -0.22, 0.45);

  // ---------- the charged pair: pith balls on threads, or the foil strips of an electroscope
  var HX = LEAF ? 0.02 : -0.06, HZ = -0.26, TOPY = LEAF ? 0.2 : 0.46;
  var threadM = new T.MeshStandardMaterial({ color: 0xe8e2d2, roughness: 0.9 });
  var foilM = new T.MeshStandardMaterial({ color: 0xd7d9dc, roughness: 0.35, metalness: 0.75, side: T.DoubleSide });
  var pithM = new T.MeshStandardMaterial({ color: 0xf4f1e6, roughness: 0.9 });
  var armG = null, jarG = null, arms = [];
  if (!LEAF) {
    S.stand({ x: HX - 0.26, z: HZ - 0.04, h: 0.56, armY: 0.5, armLen: 0.22 });
    var arm = S.mesh(new T.BoxGeometry(0.26, 0.01, 0.01), M.chrome); arm.position.set(HX - 0.14, TOPY + 0.03, HZ - 0.04); S.scene.add(arm);
    var hookBar = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.05, 10), M.chrome);
    hookBar.rotation.x = Math.PI / 2; hookBar.position.set(HX, TOPY + 0.025, HZ); S.scene.add(hookBar);
  } else {
    jarG = new T.Group(); S.scene.add(jarG); jarG.position.set(HX, 0.014, HZ);
    var glass = S.mesh(new T.CylinderGeometry(0.075, 0.075, 0.2, 40, 1, true), M.glass, false); glass.position.y = 0.1; jarG.add(glass);
    var jbot = S.mesh(new T.CylinderGeometry(0.075, 0.075, 0.004, 40), M.glass, false); jbot.position.y = 0.002; jarG.add(jbot);
    var lidM = S.rounded(0.18, 0.18, 0.008, 0.004, new T.MeshStandardMaterial({ color: 0xa9804c, roughness: 0.8 }));
    lidM.rotation.x = -Math.PI / 2; lidM.position.y = 0.204; jarG.add(lidM);
    var rodW = S.mesh(new T.CylinderGeometry(0.0016, 0.0016, 0.1, 12), M.copper); rodW.position.y = 0.212; jarG.add(rodW);
    var disc = S.mesh(new T.CylinderGeometry(0.026, 0.026, 0.0025, 32), M.brass); disc.position.y = 0.262; jarG.add(disc);
    jarG.userData.disc = disc;
    var hookI = S.mesh(new T.TorusGeometry(0.004, 0.0009, 8, 16), M.copper); hookI.rotation.x = Math.PI / 2; hookI.position.y = 0.2; jarG.add(hookI);
    S.contact(0.2, 0.2, HX, HZ, 0.4);
  }
  [-1, 1].forEach(function (s) {
    var g = new T.Group(); S.scene.add(g);
    g.position.set(HX, TOPY, HZ);
    var line = LEAF
      ? S.mesh(new T.PlaneGeometry(0.01 * SCALE, 1, 1, 1), foilM, false)
      : S.mesh(new T.CylinderGeometry(0.0003, 0.0003, 1, 6), threadM, false);
    g.add(line); g.userData.line = line; g.userData.sign = s;
    if (!LEAF) {
      var ball = S.mesh(new T.SphereGeometry(0.006, 20, 14), pithM); g.add(ball); g.userData.ball = ball;
    }
    arms.push(g);
  });
  function place() {
    var th = theta(), L = p.Lth * SCALE;
    arms.forEach(function (g) {
      var s = g.userData.sign, ln = g.userData.line;
      g.rotation.z = -s * th;
      ln.scale.y = L; ln.position.y = -L / 2;
      if (LEAF) ln.position.z = 0.0002 * s;
      if (g.userData.ball) g.userData.ball.position.y = -L;
    });
  }
  place();

  // ---------- the millimetre scale behind the charged pair
  var ruler = S.ruler(LEAF ? 0.1 : 0.2, { pxPerMm: 6, labelEvery: 10, width: 0.022, title: 'cm' });
  ruler.position.set(HX - (LEAF ? 0.05 : 0.1), TOPY - p.Lth * SCALE - 0.012, HZ - 0.03);
  ruler.rotation.z = -Math.PI / 2;

  // ---------- the polythene rod and the woollen duster
  var RODX = 0.42, RODZ = -0.08;
  var rod = new T.Group(); S.scene.add(rod);
  rod.add((function () { var r = S.mesh(new T.CylinderGeometry(0.0075, 0.0075, 0.26, 20), new T.MeshStandardMaterial({ color: 0x24262b, roughness: 0.35 })); r.rotation.z = Math.PI / 2; return r; })());
  rod.add((function () { var l = S.label('POLYTHENE', { w: 0.06, ratio: 0.14, color: '#d8d8da' }); l.rotation.x = -Math.PI / 2; l.position.set(0, 0.0078, 0); return l; })());
  rod.position.set(RODX, 0.0215, RODZ);
  S.contact(0.3, 0.05, RODX, RODZ, 0.4);
  var duster = S.rounded(0.1, 0.07, 0.022, 0.008, new T.MeshStandardMaterial({ color: 0x8a5f3b, roughness: 0.95 }));
  duster.rotation.x = -Math.PI / 2; duster.position.set(RODX - 0.02, 0.025, RODZ - 0.16); S.scene.add(duster);
  S.contact(0.13, 0.1, RODX - 0.02, RODZ - 0.16, 0.4);
  var dtag = S.label('WOOLLEN DUSTER', { w: 0.08, ratio: 0.12, color: '#f3ead2', bg: '#2b2b2b', px: 640 });
  dtag.rotation.x = -Math.PI / 2; dtag.position.set(RODX - 0.02, 0.037, RODZ - 0.16); S.scene.add(dtag);

  S.addApparatus(LEAF ? 'jar' : 'balls', LEAF ? jarG : arms[0], LEAF ? 'Jar electroscope' : 'Two pith balls on threads',
    LEAF ? 'A metal disc on a copper wire through the lid, with two aluminium foil strips hanging from its hook inside a dry glass jar.'
      : 'Two light pith balls hanging side by side on silk threads of equal length, just touching when they are uncharged.');
  S.addApparatus('rod', rod, 'Polythene rod', 'Rubbed with wool it takes electrons from the wool and becomes negatively charged.');
  S.addApparatus('duster', duster, 'Woollen duster', 'The wool gives up electrons and is left positively charged. Charge is never made, only moved.');
  S.addApparatus('ruler', ruler, 'Millimetre scale', 'Held behind the pair; the gap is read against it with a hand lens, to about a fifth of a millimetre.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hud1 = S.hudCard('Gap'), hud2 = S.hudCard('Angle'), hud3 = S.hudCard('Charge');

  // ---------- actions
  function dryCheck() {
    st.dry = true;
    S.say('The jar, the threads and the rod have been wiped dry. On a damp day the charge leaks away in seconds and nothing works.');
    S.render();
  }
  function rub() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    var a = new T.Vector3(RODX - 0.06, 0.04, RODZ - 0.16), b = new T.Vector3(RODX + 0.06, 0.04, RODZ - 0.16);
    var home = rod.position.clone();
    return S.hand.pinchMove(home.clone().add(new T.Vector3(0, 0.012, 0)),
      function (k) {
        var s = Math.sin(k * Math.PI * 3) * 0.05;
        return new T.Vector3((a.x + b.x) / 2 + s, 0.05, a.z);
      },
      function (k) {
        var s = Math.sin(k * Math.PI * 3) * 0.05;
        rod.position.set((a.x + b.x) / 2 + s, 0.038, a.z);
      }, { ms: 1100, mode: 'top' })
      .then(function () {
        rod.position.copy(home); st.rubs++;
        S.say('The rod has been rubbed along the wool. Electrons have moved from the wool to the polythene, so the rod is now negatively charged.');
        S.render();
      });
  }
  function touch() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (st.rubs < 1) { S.say('Rub the rod on the duster first: an unrubbed rod carries no charge.'); return Promise.resolve(); }
    var home = rod.position.clone();
    var to = LEAF ? new T.Vector3(HX + 0.08, 0.28, HZ) : new T.Vector3(HX + 0.09, TOPY - p.Lth * SCALE, HZ);
    return S.hand.pinchMove(home.clone().add(new T.Vector3(0, 0.012, 0)),
      function (k) { return home.clone().lerp(to, k).add(new T.Vector3(0, 0.012, 0)); },
      function (k) { rod.position.copy(home.clone().lerp(to, k)); }, { ms: 900, mode: 'top' })
      .then(function () {
        st.charged = true; solve();
        S.say(LEAF ? 'The rod is touched to the disc. The charge spreads down the wire to both strips, they now carry the same kind of charge, and they fly apart.'
          : 'The rod is touched to both balls. They take the same kind of charge, so they push each other apart.');
        return S.hand.pinchMove(to.clone().add(new T.Vector3(0, 0.012, 0)),
          function (k) { return to.clone().lerp(home, k).add(new T.Vector3(0, 0.012, 0)); },
          function (k) { rod.position.copy(to.clone().lerp(home, k)); }, { ms: 700, mode: 'top' });
      }).then(function () { rod.position.copy(home); S.render(); });
  }
  function earth() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    var tgt = LEAF ? jarG.userData.disc : arms[0].userData.ball;
    return S.hand.tap(tgt).then(function () {
      st.charged = false; solve();
      S.say('Touched with a finger: you are a conductor joined to the earth, so the charge runs away and the ' + (LEAF ? 'strips' : 'balls') + ' fall together again.');
      S.render();
    });
  }
  function setLen(L) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    L = Math.max(LMIN, Math.min(LMAX, Math.round(L * 1000) / 1000)); st.targetL = L;
    var a = st.L; if (Math.abs(L - a) < 1e-9) return Promise.resolve();
    var from = new T.Vector3(HX, TOPY - a * SCALE, HZ);
    return S.hand.pinchMove(from.clone().add(new T.Vector3(0, 0.01, 0.01)),
      function (k) { return new T.Vector3(HX, TOPY - (a + (L - a) * k) * SCALE, HZ).add(new T.Vector3(0, 0.01, 0.01)); },
      function (k) { st.L = a + (L - a) * k; solve(); place(); }, { ms: 800, mode: 'top' })
      .then(function () {
        st.L = L; solve(); place();
        ruler.position.y = TOPY - p.Lth * SCALE - 0.012;
        S.say(LEAF ? 'Another centimetre of each strip is folded over the hook: the hanging length is now ' + (L * 100).toFixed(1) + ' cm.'
          : 'The threads are shortened to ' + (L * 100).toFixed(1) + ' cm.');
        S.render();
      });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.charged) { S.say('Charge them first: there is nothing to measure.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.L - st.L) < 0.004; })) { S.say('There is already a reading at this length.'); return false; }
    if (S.rows.length >= 10) { S.say('That is plenty of readings. Go on to the result.'); return false; }
    var r = sepRead();
    if (r < 0.002) { S.say('The gap is too small to read on the scale.'); return false; }
    S.addRow({ L: st.L, r: r });
    S.say('Written in your record book: hanging length ' + (st.L * 100).toFixed(1) + ' cm, gap ' + (r * 1000).toFixed(1) + ' mm.');
    return true;
  }
  var NEED = 3;
  function lens() { var out = [], step = (LMAX - LMIN) / 3; for (var k = 0; k < 4; k++) out.push(Math.round((LMIN + k * step) * 1000) / 1000); return out; }

  return {
    camera: { pos: [0.08, LEAF ? 0.42 : 0.6, 0.55], look: [HX, LEAF ? 0.18 : 0.3, HZ] },
    views: { balls: [[HX + 0.12, TOPY - 0.08, HZ + 0.3], [HX, TOPY - p.Lth * SCALE, HZ]],
      jar: [[HX + 0.12, 0.3, HZ + 0.34], [HX, 0.16, HZ]],
      rod: [[RODX - 0.02, 0.2, RODZ + 0.2], [RODX, 0.02, RODZ]],
      duster: [[RODX, 0.2, RODZ + 0.02], [RODX - 0.02, 0.02, RODZ - 0.16]],
      ruler: [[HX + 0.1, TOPY - 0.1, HZ + 0.22], [HX, TOPY - p.Lth * SCALE, HZ]],
      work: [[HX + 0.14, LEAF ? 0.34 : 0.5, HZ + 0.42], [HX, LEAF ? 0.16 : TOPY - 0.12, HZ]],
      book: [[-0.5, 0.45, 0.6], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'Rubbing does not make charge: it moves electrons from one surface to the other. Polythene rubbed with wool takes electrons and is left '
        + 'negative, the wool positive. ' + (LEAF ? 'A conductor shares charge over the whole of itself, so charge put on the disc runs down the wire to both strips.'
          : 'Touching the rod to both balls gives them the same kind of charge.') + ' Like charges repel, so the two hang apart.',
      formula: 'tan θ = k q² / (r² m g),   r = 2L sin θ',
      formulaNote: 'and for a small angle r = (2 k q² L / m g)^{1/3}, so the gap gives the charge',
      more: ['Each ' + (LEAF ? 'strip' : 'ball') + ' hangs where three forces balance: its weight, the pull along the ' + (LEAF ? 'strip' : 'thread')
        + ' and the Coulomb push of the other charge. Make the hanging length longer and the same charge pushes them further apart, so measuring the gap at '
        + 'several lengths gives the same charge each time - which is the check that the picture is right.',
        'The charges here are a few nanocoulombs, a few thousand-millionths of a coulomb. That is all a rubbed rod carries, and it is why the whole thing fails on a damp day.'],
      precautions: 'Keep everything dry and do not touch the charged parts: a finger earths them at once. Hold the rod by the end you did not rub.' },
    book: { title: LEAF ? 'Expt. — A jar electroscope' : 'Expt. — Charging by rubbing',
      lines: ['Aim: ' + S.lab.aim].concat(SAMPLE ? ['Method: ' + SAMPLE] : [])
        .concat(['Mass of each ' + (LEAF ? 'strip' : 'ball') + ' = ' + (p.mass * 1e6).toFixed(0) + ' mg',
          'Gap read to 0.2 mm with a hand lens', 'q = √(r³ m g / 2 k L)']),
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'L (cm)', get: function (r) { return (r.L * 100).toFixed(1); } },
        { label: 'Gap r (mm)', get: function (r) { return (r.r * 1000).toFixed(1); } },
        { label: 'q (nC)', get: function (r) { return (Math.sqrt(r.r * r.r * r.r * p.mass * p.g / (2 * KCOUL * r.L)) * 1e9).toFixed(2); } }] },
    graph: { x: function (r) { return r.L * 100; }, y: function (r) { return r.r * 1000; }, xlabel: 'L (cm)', ylabel: 'gap (mm)', x0: 0, y0: 0 },
    result: function (rows) {
      if (rows.length < NEED) return null;
      var q = S.fit.mean(rows.map(function (r) { return Math.sqrt(r.r * r.r * r.r * p.mass * p.g / (2 * KCOUL * r.L)); }));
      return { label: 'Charge on each ' + (LEAF ? 'strip' : 'ball'), value: q * 1e9, unit: 'nC', digits: 2, truth: p.q * 1e9,
        note: 'From the mean of √(r³ m g / 2 k L) over the readings.' };
    },
    tol: 0.06,
    resultNote: 'The gap changed with the hanging length but the charge worked out the same each time, which is the test of the picture.',
    chips: ['Where does the charge come from?', 'Why do they fly apart?', 'Why does it fail on a damp day?',
      'Check my readings', LEAF ? 'What does an electroscope tell you?' : 'What happens with an uncharged ball?'],
    viva: [['A charged ' + (LEAF ? 'rod is brought near the disc without touching it' : 'ball is brought near an uncharged one') + '. What happens?',
      ['They attract', 'They repel', 'Nothing at all'], 0,
      'The charge pulls the opposite charge to the near side of the neutral body, so it is attracted.'],
    ['Rubbing a rod with wool',
      ['Moves electrons from one to the other', 'Makes new charge', 'Destroys charge'], 0,
      'Charge is conserved: the rod gains exactly what the wool loses.']],
    askState: function () {
      return { set_up: LEAF ? 'jar electroscope with two foil strips' : 'two pith balls on threads',
        dry_checked: st.dry, rod_rubbed_times: st.rubs, charged: st.charged,
        hanging_length_cm: +(st.L * 100).toFixed(1), gap_mm: st.charged ? +(sepRead() * 1000).toFixed(1) : 0,
        angle_deg: +(theta() * 180 / Math.PI).toFixed(1), readings_taken: S.rows.length };
    },
    steps: [
      { id: 'set', title: 'Set it up', view: LEAF ? 'jar' : 'balls', render: function (u) {
          u.h2(LEAF ? 'Build the electroscope' : 'Hang the two pith balls');
          u.p(LEAF ? 'A copper wire through the cardboard lid, a metal disc on top and two aluminium foil strips hanging from the hook inside. '
            + 'Uncharged, the strips hang straight down against each other.'
            : 'Two pith balls hang side by side on threads of the same length, just touching while they are uncharged.');
          u.task('1. Look at the apparatus', st.traced, st.traced ? 'The two hang together: no charge yet' : 'Not yet')
            .add(u.button(st.traced ? 'Looked' : 'Look at it', function () { st.traced = true; S.focus(LEAF ? 'jar' : 'balls'); S.render(); }, !st.traced, st.traced));
          u.task('2. Check that everything is dry', st.dry, st.dry ? 'Dry: the charge will stay put' : 'A damp day leaks the charge away')
            .add(u.button(st.dry ? 'Checked' : 'Wipe everything dry', dryCheck, !st.dry, st.dry));
          u.next('Next: charge the rod', st.traced && st.dry);
        },
        ok: function () { return st.traced && st.dry; },
        auto: function () { st.traced = true; dryCheck(); return Promise.resolve(); } },
      { id: 'charge', title: 'Charge them', view: 'rod', render: function (u) {
          u.h2('Rub the rod and touch it to the ' + (LEAF ? 'disc' : 'balls'));
          u.p('The hand rubs the polythene rod along the woollen duster, then touches it to the ' + (LEAF ? 'metal disc on top' : 'two balls') + '.');
          u.task('1. Rub the rod', st.rubs > 0, st.rubs > 0 ? 'Rubbed ' + st.rubs + ' time(s)' : 'Not yet')
            .add(u.button('Rub it on the duster', function () { rub(); }, true, S.hand.busy));
          u.task('2. Touch it to the ' + (LEAF ? 'disc' : 'balls'), st.charged, st.charged ? 'They have flown apart' : 'Not yet')
            .add(u.row(u.button('Touch the ' + (LEAF ? 'disc' : 'balls'), function () { touch(); }, true, S.hand.busy || st.charged),
              u.button('Earth it with a finger', function () { earth(); }, false, S.hand.busy || !st.charged)));
          u.live(function () { return st.charged ? 'gap ' + (sepRead() * 1000).toFixed(1) + ' mm  ·  each ' + (LEAF ? 'strip' : 'thread') + ' at ' + (theta() * 180 / Math.PI).toFixed(1) + '°' : 'hanging together'; });
          u.note('Hold the rod by the end you did not rub, and do not touch the ' + (LEAF ? 'disc' : 'balls') + ' with your fingers.');
          u.next('Next: measure the gap', st.charged);
        },
        ok: function () { return st.charged; },
        auto: function () { return rub().then(touch); } },
      { id: 'read', title: 'Measure the gap', view: 'work', render: function (u) {
          u.h2('The gap at several hanging lengths');
          u.p(LEAF ? 'Fold a little more of each strip over the hook to shorten it, and read the gap between the tips against the scale each time.'
            : 'Shorten the threads a little at a time and read the gap between the balls against the scale each time. The charge stays where it is.');
          u.slider('Hanging length', LMIN, LMAX, 0.005, function () { return st.targetL; }, function (v) { st.targetL = v; }, 'm', 3);
          u.row(u.button('Set the length', function () { setLen(st.targetL); }, true, S.hand.busy),
            u.button('Record this reading', function () { record(); }, true, S.hand.busy || !st.charged));
          u.live(function () { return 'L ' + (st.L * 100).toFixed(1) + ' cm  ·  gap ' + (st.charged ? (sepRead() * 1000).toFixed(1) : '0.0') + ' mm'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < NEED) u.p(S.rows.length + ' of at least ' + NEED + ' readings recorded.');
          u.next('Next: the result', S.rows.length >= NEED);
        },
        ok: function () { return S.rows.length >= NEED; },
        auto: function () {
          return lens().reduce(function (pr, L) {
            return pr.then(function () { return setLen(L).then(function () { S.advance(0.1); record(); }); });
          }, Promise.resolve());
        } },
    ],
    tick: function () {
      place();
      hud1.set(st.charged ? (sepRead() * 1000).toFixed(1) + ' mm' : '0.0 mm');
      hud2.set((theta() * 180 / Math.PI).toFixed(1) + '°');
      hud3.set(st.charged ? 'on' : 'none');
    },
  };
});
