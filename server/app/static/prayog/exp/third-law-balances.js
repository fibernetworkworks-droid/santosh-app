/* Prayogshala studio rig: Newton's third law with two spring balances (NCERT Class IX Laboratory Manual).
   A clamp stand carries a fixed hook. Spring balance A (0-5 N, least count 0.05 N) hangs from it; balance B
   (0-10 N, least count 0.1 N) is hooked through A's ring, so the two lie in one straight line. The gloved hand pulls
   B's ring horizontally and holds it, and both balances are read at the same moment. However hard the pull, the two
   readings are the same: what B pulls A with, A pulls B back with.
   Physics: the `twospring` kernel of the mech_school pack. Every number is read from S.lab.params. */
HoolaStudio.define('third-law-balances', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.twospring;
  var p = window.HoolaKernels.paramsFor('twospring', S.lab.params);
  p.X = 0;
  var FULL_A = 5, LC_A = 0.05, FULL_B = 10, LC_B = 0.1;
  var PULLS = [[0.008, 'a gentle pull'], [0.014, 'a little harder'], [0.020, 'firmly'], [0.026, 'as hard as the scale allows']];

  var st = { hooked: false, held: false, X: 0, busy: false };

  // ---------- geometry (everything lies along x at y = HY, z = HZ)
  var HY = 0.11, HZ = -0.06, CL = 0.19, ROD = 0.022, HOOKX = -0.47;

  var base = S.rounded(0.2, 0.16, 0.022, 0.014, M.iron);
  base.rotation.x = -Math.PI / 2; base.position.set(-0.5, 0.011, HZ); S.scene.add(base);
  S.contact(0.3, 0.24, -0.5, HZ, 0.55);
  var post = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.26, 24), M.chrome); post.position.set(-0.52, 0.13, HZ); S.scene.add(post);
  var armj = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.06, 18), M.chrome); armj.rotation.z = Math.PI / 2;
  armj.position.set(-0.49, HY, HZ); S.scene.add(armj);
  var fixHook = S.mesh(new T.TorusGeometry(0.008, 0.0022, 8, 24), M.chrome); fixHook.rotation.y = Math.PI / 2;
  fixHook.position.set(HOOKX, HY, HZ); S.scene.add(fixHook);
  var fhl = S.label('FIXED SUPPORT', { w: 0.07, ratio: 0.17, color: '#20262c' });
  fhl.rotation.x = -Math.PI / 2; fhl.position.set(-0.5, 0.0235, HZ + 0.06); S.scene.add(fhl);

  function balanceTex(full, lc, name) {
    return S.canvasTex(2048, 220, function (x, w, h) {
      x.fillStyle = '#f4efe0'; x.fillRect(0, 0, w, h);
      x.fillStyle = '#17181a'; x.textAlign = 'center';
      var n = Math.round(full / lc);
      for (var i = 0; i <= n; i++) {
        var px = 40 + i / n * (w - 80), big = i % Math.round(1 / lc) === 0, mid = i % Math.round(0.5 / lc) === 0;
        x.fillRect(px - (big ? 2 : 1), 0, big ? 4 : 2, big ? 64 : mid ? 44 : 26);
        if (big) { x.font = '700 54px "Public Sans", sans-serif'; x.fillText(String(Math.round(i * lc)), px, 128); }
      }
      x.font = '600 44px "Public Sans", sans-serif'; x.fillStyle = '#6b4a14';
      x.fillText(name + '   0 – ' + full + ' N   l.c. ' + lc.toFixed(2) + ' N', w / 2, 196);
    });
  }
  // one spring balance: case + printed scale + pointer + hook rod at the left + ring at the right
  function balance(full, lc, name, colour) {
    var g = new T.Group(); S.scene.add(g);
    var shell = S.rounded(CL, 0.034, 0.03, 0.006, new T.MeshStandardMaterial({ color: colour, roughness: 0.45, metalness: 0.3 }));
    shell.position.set(CL / 2, 0, 0); g.add(shell);
    var face = new T.Mesh(new T.PlaneGeometry(CL - 0.012, 0.024), new T.MeshStandardMaterial({ map: balanceTex(full, lc, name), roughness: 0.5 }));
    face.position.set(CL / 2, 0.0006, 0.0152); g.add(face);
    var ptr = S.mesh(new T.BoxGeometry(0.0022, 0.032, 0.002), M.red); ptr.position.set(0.006, 0.001, 0.0166); g.add(ptr);
    var rod = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 1, 12), M.chrome, true, false); rod.rotation.z = Math.PI / 2; g.add(rod);
    var hook = S.mesh(new T.TorusGeometry(0.0065, 0.0018, 8, 22), M.chrome); hook.rotation.y = Math.PI / 2; g.add(hook);
    var ring = S.mesh(new T.TorusGeometry(0.012, 0.0028, 10, 26), M.chrome); ring.rotation.y = Math.PI / 2;
    ring.position.set(CL + 0.012, 0, 0); g.add(ring);
    var tag = S.label(name, { w: 0.03, ratio: 0.4, color: '#e8eef6' });
    tag.rotation.x = -Math.PI / 2; tag.position.set(CL / 2, 0.018, 0); g.add(tag);
    g.userData.set = function (reading, ext) {
      rod.scale.set(1, Math.max(1e-4, ROD + ext), 1);
      rod.position.set(-(ROD + ext) / 2, 0, 0);
      hook.position.set(-(ROD + ext) - 0.005, 0, 0);
      ptr.position.x = 0.006 + (reading / full) * (CL - 0.012);
    };
    g.userData.ringX = CL + 0.024;
    return g;
  }
  var balA = balance(FULL_A, LC_A, 'A', 0x2b2f36);
  var balB = balance(FULL_B, LC_B, 'B', 0x3a3038);
  var B_HOME = new T.Vector3(0.16, 0.012, 0.11);
  balB.position.copy(B_HOME); balB.rotation.z = 0;
  var bShadow = S.contact(0.24, 0.1, B_HOME.x + 0.1, B_HOME.z, 0.45);

  S.addApparatus('stand', post, 'Clamp stand with a fixed hook', 'A rigid support. Balance A is hooked to it so that it cannot move.');
  S.addApparatus('balA', balA, 'Spring balance A (0–' + FULL_A + ' N)', 'Least count ' + LC_A.toFixed(2) + ' N. Hooked to the fixed support.');
  S.addApparatus('balB', balB, 'Spring balance B (0–' + FULL_B + ' N)', 'Least count ' + LC_B.toFixed(1) + ' N. Its hook goes through A\'s ring; the hand pulls its ring.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard('Balance A'), hudB = S.hudCard('Balance B'), hudX = S.hudCard('Pull');

  // ---------- helpers
  function tension() { return p.X <= 0 ? 0 : p.X / (1 / p.k1 + 1 / p.k2); }
  function readA() { return Math.round(tension() / LC_A) * LC_A; }
  function readB() { return Math.round(tension() / LC_B) * LC_B; }
  function extA() { return tension() / p.k1; }
  function extB() { return tension() / p.k2; }
  function ringWorld() {
    if (!st.hooked) return B_HOME.clone().add(new T.Vector3(balB.userData.ringX, 0, 0));
    return new T.Vector3(HOOKX + ROD + extA() + CL + ROD + extB() + CL + 0.024, HY, HZ);
  }
  function pose() {
    var T1 = tension();
    balA.position.set(HOOKX + ROD + extA(), HY, HZ);
    balA.userData.set(Math.min(T1, FULL_A), extA());
    if (st.hooked) {
      balB.position.set(HOOKX + ROD + extA() + CL + 0.024 + ROD + extB(), HY, HZ);
      bShadow.material.opacity = 0;
    } else {
      balB.userData.set(0, 0);
      bShadow.material.opacity = 0.45;
    }
    if (st.hooked) balB.userData.set(Math.min(T1, FULL_B), extB());
    hudA.set(st.hooked ? readA().toFixed(2) + ' N' : '0.00 N');
    hudB.set(st.hooked ? readB().toFixed(1) + ' N' : 'not hooked on');
    hudX.set(st.held ? (p.X * 1000).toFixed(0) + ' mm' : 'none');
  }

  // ---------- actions
  function hookOn() {
    if (S.hand.busy || st.busy || st.hooked) return Promise.resolve();
    var from = B_HOME.clone(), to = new T.Vector3(HOOKX + ROD + CL + 0.024 + ROD, HY, HZ);
    var mid = from.clone().lerp(to, 0.5).setY(0.24);
    var G = new T.Vector3(CL / 2, 0.022, 0);
    function at(k) { return k < 0.5 ? from.clone().lerp(mid, k * 2) : mid.clone().lerp(to, (k - 0.5) * 2); }
    return S.hand.pinchMove(from.clone().add(G), function (k) { return at(k).add(G); },
      function (k) { balB.position.copy(at(k)); }, { ms: 1600 })
      .then(function () { st.hooked = true; p.X = 0; pose(); S.render();
        S.say('Balance B\'s hook is through balance A\'s ring. Both read zero.'); });
  }
  function pullTo(X) {
    if (S.hand.busy || st.busy || !st.hooked) {
      if (!st.hooked) S.say('Hook the two balances together first.');
      return Promise.resolve();
    }
    if (S.rows.some(function (r) { return Math.abs(r.X - X) < 1e-9; })) {
      S.say('You already have a reading for that pull. Choose another one.'); return Promise.resolve();
    }
    var X0 = p.X;
    return S.hand.pinchMove(ringWorld(), function () { return ringWorld(); },
      function (k) { p.X = X0 + (X - X0) * k; pose(); }, { ms: 1400, pose: 'grip', release: false })
      .then(function () {
        p.X = X; st.held = true; pose(); S.render();
        S.say('Holding steady: balance A reads ' + readA().toFixed(2) + ' N and balance B reads ' + readB().toFixed(1) + ' N.');
      });
  }
  function letGo() {
    if (S.hand.busy || st.busy || !st.held) return Promise.resolve();
    var X0 = p.X;
    return S.hand.pinchMove(ringWorld(), function () { return ringWorld(); },
      function (k) { p.X = X0 * (1 - k); pose(); }, { ms: 900, pose: 'grip' })
      .then(function () { p.X = 0; st.held = false; pose(); S.render(); });
  }
  function record() {
    if (S.hand.busy || st.busy) return;
    if (!st.held || p.X <= 0) { S.say('Pull and hold first, then read both balances.'); return; }
    if (S.rows.some(function (r) { return Math.abs(r.X - p.X) < 1e-9; })) { S.say('That pull is already in the table.'); return; }
    S.addRow({ X: p.X, A: readA(), B: readB(), T: tension() });
    S.say('Written in your record book: A = ' + readA().toFixed(2) + ' N, B = ' + readB().toFixed(1) + ' N.');
  }

  pose();

  return {
    camera: { pos: [0.42, 0.66, 0.95], look: [-0.12, 0.08, 0.0] },
    views: {
      stand: [[-0.26, 0.26, 0.16], [-0.48, 0.1, -0.06]],
      balA: [[-0.3, 0.26, 0.16], [-0.36, 0.1, -0.06]],
      balB: [[-0.06, 0.26, 0.18], [-0.12, 0.1, -0.06]],
      hook: [[0.18, 0.4, 0.58], [-0.16, 0.08, 0.0]],
      pull: [[0.06, 0.4, 0.56], [-0.2, 0.09, -0.03]],
      book: [[-0.56, 0.46, 0.54], [-0.64, 0.0, 0.1]]
    },
    theory: {
      principle: 'When the hand pulls balance B, balance B pulls balance A, and balance A pulls balance B back just '
        + 'as hard the other way. There is no way for one of them to pull harder than the other, so both springs '
        + 'carry the same tension and both balances show the same reading, however hard the pull.',
      formula: 'reading of B = reading of A',
      formulaNote: 'action and reaction are equal in size and opposite in direction',
      more: ['The two balances are not identical: A reads to ' + LC_A.toFixed(2) + ' N and B only to '
        + LC_B.toFixed(1) + ' N. The small differences between the two columns come from those least counts, not from '
        + 'the forces being different.',
        'Action and reaction act on DIFFERENT bodies - one on balance A, the other on balance B - which is why they '
        + 'do not cancel each other out.'],
      precautions: 'Keep both balances in one straight line and horizontal, pull steadily and read both at the same '
        + 'moment while the pull is held. Never pull past the full scale of either balance.'
    },
    book: {
      at: [-0.6, 0.14, 0.12],
      title: 'Expt. — Newton\'s third law with two spring balances',
      lines: ['Aim: ' + S.lab.aim,
        'Balance A: 0–' + FULL_A + ' N, least count ' + LC_A.toFixed(2) + ' N',
        'Balance B: 0–' + FULL_B + ' N, least count ' + LC_B.toFixed(1) + ' N',
        'Expected: reading of B = reading of A for every pull.',
        'Precautions: both balances in a line, read both at the same moment.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'A (N)', get: function (r) { return r.A.toFixed(2); } },
        { label: 'B (N)', get: function (r) { return r.B.toFixed(1); } },
        { label: 'B − A (N)', get: function (r) { return (r.B - r.A).toFixed(2); } },
        { label: 'B / A', get: function (r) { return r.A > 0 ? (r.B / r.A).toFixed(3) : '—'; } }]
    },
    graph: {
      x: function (r) { return r.A; }, y: function (r) { return r.B; },
      xlabel: 'reading of balance A (N)', ylabel: 'reading of balance B (N)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var k = S.fit.origin(rows.map(function (r) { return [r.A, r.B]; }));
      return { label: 'B / A', value: k, unit: '', digits: 3, truth: 1.0,
        note: 'Slope of the graph of B\'s reading against A\'s reading. A slope of 1 means the two forces are equal.' };
    },
    tol: 0.05,
    chips: ['Why do the two balances read the same?', 'Why do action and reaction not cancel out?',
      'Check my readings', 'Why are my two columns not exactly equal?'],
    viva: [['The two balances read', ['the same', 'B more than A', 'A more than B'], 0,
      'Action and reaction are equal in size.'],
    ['Action and reaction do not cancel out because', ['they act on different bodies', 'they are not equal', 'one is friction'], 0,
      'Forces cancel only when they act on the SAME body.'],
    ['Pulling twice as hard makes the readings', ['both twice as large, and still equal', 'different', 'unchanged'], 0,
      'The tension is the same all along the line, whatever its size.']],
    askState: function () {
      return { balances_hooked_together: st.hooked, pull_mm: +(p.X * 1000).toFixed(1),
        balance_A_reads_N: st.hooked ? +readA().toFixed(2) : 0, balance_B_reads_N: st.hooked ? +readB().toFixed(1) : 0,
        A_least_count_N: LC_A, B_least_count_N: LC_B, readings_taken: S.rows.length };
    },

    steps: [
      { id: 'hook', title: 'Hook them together', view: 'hook',
        render: function (u) {
          u.h2('Hook the two balances together');
          u.p('Balance A hangs from the fixed hook on the clamp stand. The hand brings balance B and puts its hook '
            + 'through balance A\'s ring, so the two lie in one straight line.');
          u.row(u.button('Hook balance B on to balance A', function () { hookOn(); }, true, S.hand.busy || st.busy || st.hooked));
          u.task('Balances joined', st.hooked, st.hooked ? 'in a line, both reading zero' : 'balance B is still on the table');
          u.live(function () { return 'A ' + (st.hooked ? readA().toFixed(2) : '0.00') + ' N · B ' + (st.hooked ? readB().toFixed(1) + ' N' : 'not hooked on'); });
          u.note('Both balances must read zero before you start pulling.');
          u.next('Next: pull and read both', st.hooked && !S.hand.busy);
        },
        ok: function () { return st.hooked; },
        auto: function () { return hookOn(); } },

      { id: 'pull', title: 'Pull and read both', view: 'pull',
        render: function (u) {
          u.h2('Pull balance B and read both balances');
          u.p('The hand pulls balance B\'s ring horizontally and holds it still. Read A and B at the same moment and '
            + 'record both. Then try a harder pull.');
          var r = u.row();
          PULLS.forEach(function (q) {
            var done = S.rows.some(function (z) { return Math.abs(z.X - q[0]) < 1e-9; });
            r.appendChild(u.button((done ? '✓ ' : '') + q[1], function () { pullTo(q[0]); },
              false, S.hand.busy || st.busy || !st.hooked || done));
          });
          u.row(u.button('Record both readings', function () { record(); }, true, S.hand.busy || st.busy || !st.held),
            u.button('Let go', function () { letGo(); }, false, S.hand.busy || st.busy || !st.held));
          u.live(function () {
            return 'A reads ' + readA().toFixed(2) + ' N · B reads ' + readB().toFixed(1) + ' N · '
              + (st.held ? 'held steady' : 'no pull');
          });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 4) u.p(S.rows.length + ' of 4 pulls recorded.');
          u.next('Next: graph and result', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          return PULLS.reduce(function (pr, q) {
            return pr.then(function () { return pullTo(q[0]); }).then(function () { record(); });
          }, Promise.resolve());
        } }
    ],

    tick: function () { pose(); }
  };
});
