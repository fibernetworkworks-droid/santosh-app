/* Prayogshala studio rig: upthrust, Archimedes' principle and the density of a solid
   (NCERT Class IX, chapter Gravitation; NCERT Class IX Laboratory Manual).
   A retort stand whose boss the gloved hand slides down the rod, a spring balance (0-5 N, least count 0.02 N) hanging
   from its arm, and the solid hanging from the balance on a thread. Under it stands either a graduated glass jar of
   liquid, with a millimetre scale down its side (Archimedes), or a 250 mL measuring cylinder with a beaker to pour
   water from (density of a solid). Physics: the `buoy` kernel of the mech_school pack.
   Two labs share this rig: `archimedes-balance` and `solid-density`. Every number comes from S.lab.params. */
HoolaStudio.define('archimedes-balance', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.buoy;
  var p = window.HoolaKernels.paramsFor('buoy', S.lab.params);
  p.frac = 0;
  var MODE = ((S.lab.variant || {}).base) || S.lab.id;            // 'archimedes-balance' or 'solid-density'
  var DENS = MODE === 'solid-density';
  var vs = (S.lab.variant || {}).sample || '';

  var FULLB = 5, LCB = 0.02;                                      // spring balance: full scale N, least count N
  var LCMM = 0.001, LCML = 1;                                     // scale least count 1 mm, cylinder least count 1 mL
  var SOLID_D = DENS ? 0.030 : 0.040;                             // the solid is a cylinder: diameter and height
  var HS = p.V / (Math.PI * SOLID_D * SOLID_D / 4);
  var ASOL = Math.PI * SOLID_D * SOLID_D / 4;

  // ---------- vessel
  var JX = 0.01, JZ = -0.1;
  var JR = DENS ? 0.0201 : 0.05, JH = DENS ? 0.26 : 0.17;         // jar / measuring cylinder
  var AJAR = DENS ? p.Acyl : Math.PI * JR * JR;
  var V0_BASE = DENS ? 80.4e-6 : AJAR * 0.1;                      // starting volume of liquid
  var POURS = [80.4e-6, 96.7e-6, 113.3e-6];
  var THREAD = DENS ? 0.18 : 0.05;                                // the solid hangs this far below the balance hook
  var CASE_H = 0.2, ROD0 = 0.022;
  var DROP = CASE_H + ROD0 + THREAD;                              // boss to the top of the solid, with no load

  var st = { hung: false, bossY: 0, V0: V0_BASE, pour: 0, Wair: 0, V1: 0, V2: 0, lowered: false, busy: false, lastFrac: 0 };

  function liquidLevel(vol) { return vol / AJAR; }
  // the geometry settles in a few passes: the spring stretches with the load, and the liquid rises as the solid goes in
  function settle() {
    var ext = 0, frac = 0, top, bot, lvl, i, W = p.rho_s * p.V * p.g;
    for (i = 0; i < 4; i++) {
      top = st.bossY - DROP - ext;
      bot = top - HS;
      lvl = liquidLevel(st.V0 + p.V * frac);
      frac = Math.min(1, Math.max(0, (lvl - bot) / HS));
      ext = Math.max(0, W - p.rho_l * p.g * p.V * frac) / FULLB * 0.025;
    }
    return { ext: ext, frac: frac, top: top, bot: bot, lvl: lvl, W: W };
  }
  var g0 = { ext: 0, frac: 0, top: 0, bot: 0, lvl: liquidLevel(V0_BASE), W: p.rho_s * p.V * p.g };

  // ---------- stand (own, because the boss slides)
  var base = S.rounded(0.24, 0.17, 0.022, 0.014, M.iron);
  base.rotation.x = -Math.PI / 2; base.position.set(-0.24, 0.011, JZ); S.scene.add(base);
  S.contact(0.34, 0.26, -0.24, JZ, 0.55);
  var rod = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 0.86, 32), M.chrome); rod.position.set(-0.3, 0.45, JZ); S.scene.add(rod);
  var boss = new T.Group(); S.scene.add(boss);
  var bb = S.rounded(0.05, 0.046, 0.042, 0.007, M.alu); bb.position.set(-0.3, 0, JZ); boss.add(bb);
  var bthumb = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.03, 12), M.chrome); bthumb.rotation.x = Math.PI / 2;
  bthumb.position.set(-0.3, 0, JZ + 0.036); boss.add(bthumb);
  var bknob = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.009, 6), M.black); bknob.rotation.x = Math.PI / 2;
  bknob.position.set(-0.3, 0, JZ + 0.055); boss.add(bknob);
  var arm = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.33, 20), M.chrome); arm.rotation.z = Math.PI / 2;
  arm.position.set(-0.135, 0, JZ); boss.add(arm);
  var armEnd = S.mesh(new T.TorusGeometry(0.007, 0.002, 8, 20), M.chrome); armEnd.position.set(JX, -0.007, JZ); boss.add(armEnd);

  // ---------- the spring balance
  var bal = new T.Group(); S.scene.add(bal);
  var shell = S.rounded(0.042, CASE_H, 0.03, 0.008, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.45, metalness: 0.3 }));
  shell.position.set(0, -CASE_H / 2, 0); bal.add(shell);
  var balTex = S.canvasTex(300, 2048, function (x, w, h) {
    x.fillStyle = '#f4efe0'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#17181a'; x.textAlign = 'left';
    var n = Math.round(FULLB / LCB);
    for (var i = 0; i <= n; i++) {
      var py = 40 + i / n * (h - 80), big = i % 25 === 0, mid = i % 5 === 0;
      x.fillRect(0, py - (big ? 2 : 1), big ? 110 : mid ? 76 : 44, big ? 4 : 2);
      if (big) { x.font = '700 58px "Public Sans", sans-serif'; x.fillText((i * LCB).toFixed(0), 125, py + 20); }
    }
    x.save(); x.translate(250, h / 2); x.rotate(Math.PI / 2);
    x.font = '600 46px "Public Sans", sans-serif'; x.fillStyle = '#6b4a14'; x.textAlign = 'center';
    x.fillText('NEWTON  0 – ' + FULLB + ' N   l.c. ' + LCB.toFixed(2) + ' N', 0, 0); x.restore();
  });
  var bface = new T.Mesh(new T.PlaneGeometry(0.03, CASE_H - 0.014), new T.MeshStandardMaterial({ map: balTex, roughness: 0.5 }));
  bface.position.set(0, -CASE_H / 2, 0.0152); bal.add(bface);
  var bptr = S.mesh(new T.BoxGeometry(0.034, 0.0022, 0.002), M.red); bptr.position.set(0, 0, 0.0166); bal.add(bptr);
  var bloop = S.mesh(new T.TorusGeometry(0.007, 0.0018, 8, 20), M.chrome); bloop.position.set(0, 0.004, 0); bal.add(bloop);
  var brod = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 1, 12), M.chrome, true, false); bal.add(brod);
  var bhook = S.mesh(new T.TorusGeometry(0.006, 0.0016, 8, 22), M.chrome); bal.add(bhook);

  // ---------- the solid and its thread
  var SOLID_HOME = new T.Vector3(0.42, 0, 0.1);
  var solidName = vs || (DENS ? 'Metal cylinder' : 'Aluminium cylinder');
  function solidColour() {
    var t = (vs || '').toLowerCase();
    if (/copper/.test(t)) return 0xc27a4a;
    if (/brass/.test(t)) return 0xd6aa4c;
    if (/iron|steel/.test(t)) return 0x9aa0a6;
    if (/glass/.test(t)) return 0xbfd8e4;
    if (/cork/.test(t)) return 0xc29660;
    if (/wood|pine/.test(t)) return 0xb98a58;
    return 0xc8cdd2;
  }
  var solid = new T.Group(); S.scene.add(solid);
  var sm = S.mesh(new T.CylinderGeometry(SOLID_D / 2, SOLID_D / 2, HS, 40),
    new T.MeshStandardMaterial({ color: solidColour(), roughness: 0.3, metalness: /cork|wood|glass/.test((vs || '').toLowerCase()) ? 0 : 0.85 }));
  sm.position.y = HS / 2; solid.add(sm);
  var sEye = S.mesh(new T.TorusGeometry(0.004, 0.0012, 8, 18), M.brass); sEye.position.y = HS + 0.004; solid.add(sEye);
  var thM = new T.MeshStandardMaterial({ color: 0xf0ece0, roughness: 0.9 });
  var thread = S.mesh(new T.CylinderGeometry(0.0008, 0.0008, 1, 6), thM, true, false); S.scene.add(thread);

  // ---------- the vessel
  var vessel = new T.Group(); vessel.position.set(JX, 0, JZ); S.scene.add(vessel);
  var glassPts = [];
  for (var gi = 0; gi <= 12; gi++) glassPts.push(new T.Vector2(JR * (gi < 2 ? gi / 2 : 1), JH * Math.max(0, gi - 1) / 11));
  vessel.add(new T.Mesh(new T.LatheGeometry(glassPts, 44), M.glass));
  var lip = S.mesh(new T.TorusGeometry(JR, 0.0015, 6, 40), M.glass, false); lip.rotation.x = Math.PI / 2; lip.position.y = JH; vessel.add(lip);
  if (DENS) {
    var foot = S.mesh(new T.CylinderGeometry(JR * 2.1, JR * 2.3, 0.012, 32), M.glass); foot.position.y = 0.006; vessel.add(foot);
  }
  var LIQ_NAME = DENS ? 'Water' : ((S.lab.variant || {}).sample && /water|kerosene|glycer|brine|salt/i.test(vs) ? vs : 'Water');
  function liqColour() {
    var t = (LIQ_NAME || '').toLowerCase();
    if (/kerosene/.test(t)) return 0xe8dca8;
    if (/glycer/.test(t)) return 0xf2efe2;
    if (/salt|brine/.test(t)) return 0xcfe6ef;
    return 0x9fd0e6;
  }
  var liq = S.mesh(new T.CylinderGeometry(JR * 0.97, JR * 0.97, 1, 36),
    new T.MeshPhysicalMaterial({ color: liqColour(), transmission: 0.55, roughness: 0.08, thickness: 0.02, transparent: true, opacity: 0.85 }), false);
  vessel.add(liq);
  var vtex = S.canvasTex(220, 2048, function (x, w, h) {
    x.fillStyle = 'rgba(255,255,255,0.0)'; x.clearRect(0, 0, w, h);
    x.fillStyle = '#16314a'; x.textAlign = 'left';
    if (DENS) {
      for (var i = 0; i <= 125; i++) {                            // 250 mL in 2 mL steps
        var ml = i * 2, py = h - 30 - (ml * 1e-6 / AJAR) / (JH * 0.96) * (h - 60);
        if (py < 10) break;
        var big = ml % 50 === 0, mid = ml % 10 === 0;
        x.fillRect(0, py - (big ? 2 : 1), big ? 96 : mid ? 64 : 36, big ? 4 : 2);
        if (big && ml > 0) { x.font = '700 46px "Public Sans", sans-serif'; x.fillText(String(ml), 104, py + 16); }
      }
      x.font = '600 40px "Public Sans", sans-serif'; x.fillText('mL', 104, 60);
    } else {
      for (var j = 0; j <= 160; j++) {                            // a millimetre scale down the side of the jar
        var py2 = h - 30 - (j * 0.001) / (JH * 0.96) * (h - 60);
        if (py2 < 10) break;
        var big2 = j % 10 === 0, mid2 = j % 5 === 0;
        x.fillRect(0, py2 - (big2 ? 2 : 1), big2 ? 88 : mid2 ? 58 : 32, big2 ? 4 : 2);
        if (big2 && j > 0) { x.font = '700 42px "Public Sans", sans-serif'; x.fillText(String(j / 10), 96, py2 + 15); }
      }
      x.font = '600 38px "Public Sans", sans-serif'; x.fillText('cm', 96, 58);
    }
  });
  var vstrip = new T.Mesh(new T.PlaneGeometry(JR * 1.1, JH * 0.96),
    new T.MeshStandardMaterial({ map: vtex, transparent: true, roughness: 0.4, depthWrite: false }));
  vstrip.position.set(JR * 0.3, JH * 0.48, JR + 0.0012); vstrip.renderOrder = 4; vessel.add(vstrip);
  S.contact(JR * 2.6, JR * 2.6, JX, JZ, 0.5);

  // the beaker of water (density run only)
  var beaker = null, BEAK_HOME = new T.Vector3(0.3, 0, 0.1);
  if (DENS) {
    beaker = S.beaker(0.036, 0.075, [BEAK_HOME.x, 0, BEAK_HOME.z], 0x9fd0e6, 0.6);
    S.contact(0.11, 0.11, BEAK_HOME.x, BEAK_HOME.z, 0.5);
  }

  S.addApparatus('stand', boss, 'Retort stand and boss', 'The boss slides down the rod, lowering the balance and the solid into the liquid.');
  S.addApparatus('balance', bal, 'Spring balance (0–' + FULLB + ' N)', 'Least count ' + LCB.toFixed(2) + ' N. It reads the true weight in air and the apparent weight in the liquid.');
  S.addApparatus('solid', solid, solidName, 'A cylinder ' + Math.round(SOLID_D * 1000) + ' mm across and ' + (HS * 1000).toFixed(1) + ' mm long, so its volume is ' + (p.V * 1e6).toFixed(1) + ' cm³.');
  S.addApparatus('vessel', vessel, DENS ? 'Measuring cylinder (250 mL)' : 'Graduated glass jar',
    DENS ? 'Bore 40.2 mm, graduated in 2 mL and read to 1 mL. The rise of the water gives the volume of the solid.'
      : 'Holds the liquid. A millimetre scale down its side gives the depth of the solid under the surface.');
  if (beaker) S.addApparatus('beaker', beaker, 'Beaker of water', 'Water poured in to set a fresh starting level in the measuring cylinder.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudW = S.hudCard('Balance reads'), hudF = S.hudCard(DENS ? 'Water level' : 'Depth under surface'), hudU = S.hudCard('Upthrust');

  // ---------- helpers
  function readN(x) { return Math.round(x / LCB) * LCB; }
  function reading() { var q = settle(); return Math.max(0, q.W - p.rho_l * p.g * p.V * q.frac); }
  function depthMm() { var q = settle(); return Math.max(0, Math.min(HS, q.lvl - q.bot)); }
  function volMl(v) { return v * 1e6; }
  // the boss height that puts exactly `f` of the solid under the surface (the spring's stretch is solved for)
  function bossForFrac(f) {
    var W = p.rho_s * p.V * p.g, ext = 0, lvl, bot, i;
    for (i = 0; i < 4; i++) {
      lvl = liquidLevel(st.V0 + p.V * f);
      bot = lvl - f * HS - (f >= 1 ? 0.004 : 0);
      ext = Math.max(0, W - p.rho_l * p.g * p.V * f) / FULLB * 0.025;
    }
    return bot + HS + DROP + ext;
  }
  function bossTop() { return bossForFrac(0) + 0.025; }            // clear of the liquid
  function bossIn() { return bossForFrac(1); }
  function pose() {
    var q = settle();
    p.frac = q.frac;
    boss.position.y = st.bossY;
    bal.position.set(JX, st.bossY - 0.012, JZ);
    brod.scale.set(1, Math.max(1e-4, ROD0 + q.ext), 1);
    brod.position.y = -CASE_H - (ROD0 + q.ext) / 2;
    bhook.position.y = -CASE_H - (ROD0 + q.ext) - 0.005;
    bptr.position.y = -0.008 - (reading() / FULLB) * (CASE_H - 0.02);
    solid.position.set(JX, q.bot, JZ);
    var a = st.bossY - 0.012 - CASE_H - (ROD0 + q.ext) - 0.009, b = q.top + 0.008;
    thread.position.set(JX, (a + b) / 2, JZ); thread.scale.set(1, Math.max(1e-4, a - b), 1);
    var lh = Math.max(0.004, q.lvl);
    liq.scale.y = lh; liq.position.y = lh / 2 + 0.002;
    hudW.set(readN(reading()).toFixed(2) + ' N');
    hudF.set(DENS ? volMl(st.V0 + p.V * q.frac).toFixed(1) + ' mL' : (depthMm() * 1000).toFixed(1) + ' mm');
    hudU.set(st.Wair > 0 ? (st.Wair - readN(reading())).toFixed(2) + ' N' : '—');
  }

  // ---------- actions
  function hangSolid() {
    if (S.hand.busy || st.busy || st.hung) return Promise.resolve();
    var from = SOLID_HOME.clone(), to = new T.Vector3(JX, settle().bot, JZ);
    var path = [from, from.clone().setY(0.3), to.clone().setY(to.y + 0.08), to];
    var G = new T.Vector3(0, HS * 0.6, 0);
    var L = [0], i;
    for (i = 1; i < path.length; i++) L.push(L[i - 1] + path[i].distanceTo(path[i - 1]));
    function at(k) {
      var d = Math.max(0, Math.min(1, k)) * L[L.length - 1], j, f;
      for (j = 1; j < path.length; j++) if (d <= L[j] || j === path.length - 1) {
        f = (d - L[j - 1]) / Math.max(1e-9, L[j] - L[j - 1]);
        return path[j - 1].clone().lerp(path[j], Math.min(1, f));
      }
      return path[path.length - 1].clone();
    }
    return S.hand.pinchMove(from.clone().add(G), function (k) { return at(k).add(G); },
      function (k) { solid.position.copy(at(k)); }, { ms: 1600 })
      .then(function () {
        st.hung = true; st.Wair = readN(p.rho_s * p.V * p.g); pose(); S.render();
        S.say('The solid hangs from the balance. In air it reads ' + st.Wair.toFixed(2) + ' N.');
      });
  }
  function slideTo(y, ms) {
    if (S.hand.busy || st.busy) return Promise.resolve();
    var y0 = st.bossY;
    function grip(yy) { return new T.Vector3(-0.3, yy, JZ + 0.06); }
    return S.hand.pinchMove(grip(y0), function (k) { return grip(y0 + (y - y0) * k); },
      function (k) { st.bossY = y0 + (y - y0) * k; pose(); }, { ms: ms || 1300, mode: 'front', pose: 'grip' })
      .then(function () { st.bossY = y; pose(); S.render(); });
  }
  function lowerTo(fracWanted) {
    if (!st.hung) { S.say('Hang the solid on the balance first.'); return Promise.resolve(); }
    if (S.rows.some(function (r) { return r.want === fracWanted; })) {
      S.say('You already have a reading at that depth.'); return Promise.resolve();
    }
    st.lastFrac = fracWanted;
    return slideTo(bossForFrac(fracWanted), 1300).then(function () {
      S.say('Balance reads ' + readN(reading()).toFixed(2) + ' N with ' + (depthMm() * 1000).toFixed(0) + ' mm of the solid under the surface.');
      S.render();
    });
  }
  function recordImmersion(fracWanted) {
    if (S.hand.busy || st.busy) return;
    if (!st.hung) { S.say('Hang the solid on the balance first.'); return; }
    var d = Math.round(depthMm() / LCMM) * LCMM;
    if (d <= 0) { S.say('The solid is still out of the liquid. Lower it first.'); return; }
    if (S.rows.some(function (r) { return r.want === fracWanted; })) { S.say('That depth is already in the table.'); return; }
    var Wp = readN(reading()), Vs = ASOL * d;
    S.addRow({ want: fracWanted, d: d, Vs: Vs, W: st.Wair, Wp: Wp, U: st.Wair - Wp });
    S.say('Written in your record book: depth ' + (d * 1000).toFixed(0) + ' mm, balance ' + Wp.toFixed(2) + ' N.');
  }
  function pourWater(i) {
    if (S.hand.busy || st.busy || !beaker) return Promise.resolve();
    if (st.bossY < bossTop() - 1e-6) { S.say('Raise the solid out of the cylinder first.'); return Promise.resolve(); }
    var from = beaker.position.clone(), over = new T.Vector3(JX + 0.05, 0.3, JZ);
    return S.hand.pinchMove(from.clone().add(new T.Vector3(0, 0.05, 0)),
      function (k) { return from.clone().lerp(over, k).add(new T.Vector3(0, 0.05, 0)); },
      function (k) { beaker.position.copy(from.clone().lerp(over, k)); beaker.rotation.z = -0.9 * k; }, { ms: 1200 })
      .then(function () {
        st.V0 = POURS[i]; st.pour = i; pose();
        return S.hand.pinchMove(over.clone().add(new T.Vector3(0, 0.05, 0)),
          function (k) { return over.clone().lerp(from, k).add(new T.Vector3(0, 0.05, 0)); },
          function (k) { beaker.position.copy(over.clone().lerp(from, k)); beaker.rotation.z = -0.9 * (1 - k); }, { ms: 1000 });
      })
      .then(function () {
        beaker.position.copy(BEAK_HOME); beaker.rotation.z = 0;
        st.V1 = Math.round(volMl(st.V0) / LCML) * LCML; st.lowered = false; pose(); S.render();
        S.say('The water in the cylinder now reads ' + st.V1.toFixed(0) + ' mL.');
      });
  }
  function dipSolid() {
    if (!st.hung) { S.say('Hang the solid on the balance first.'); return Promise.resolve(); }
    return slideTo(bossIn(), 1400).then(function () {
      st.V2 = Math.round(volMl(st.V0 + p.V) / LCML) * LCML; st.lowered = true; pose(); S.render();
      S.say('Fully under water the cylinder reads ' + st.V2.toFixed(0) + ' mL.');
    });
  }
  function raiseSolid() { return slideTo(bossTop(), 1200).then(function () { st.lowered = false; S.render(); }); }
  function recordVolume() {
    if (S.hand.busy || st.busy) return;
    if (!st.lowered) { S.say('Lower the solid fully under the water, then record.'); return; }
    if (S.rows.some(function (r) { return r.V1 === st.V1; })) { S.say('That starting level is already in the table.'); return; }
    S.addRow({ V1: st.V1, V2: st.V2, V: (st.V2 - st.V1) * 1e-6, W: st.Wair });
    S.say('Written in your record book: ' + st.V1.toFixed(0) + ' mL to ' + st.V2.toFixed(0) + ' mL.');
  }

  st.bossY = bossTop(); pose();

  // ---------- workflow
  var IMM = [0.25, 0.5, 0.75, 1.0];
  var EXP = {
    camera: { pos: [0.34, 0.62, 0.78], look: [-0.02, 0.26, -0.08] },
    views: {
      stand: [[0.1, 0.6, 0.5], [-0.2, 0.34, -0.1]],
      balance: [[0.16, 0.55, 0.36], [0.01, 0.42, -0.1]],
      solid: [[0.16, 0.26, 0.3], [0.01, 0.12, -0.1]],
      vessel: [[0.2, 0.3, 0.38], [0.01, 0.1, -0.1]],
      beaker: [[0.34, 0.26, 0.32], [0.3, 0.04, 0.08]],
      air: [[0.24, 0.5, 0.52], [0.0, 0.3, -0.09]],
      dip: [[0.24, 0.36, 0.46], [0.01, 0.16, -0.09]],
      book: [[-0.56, 0.46, 0.54], [-0.64, 0.0, 0.1]]
    },
    theory: {
      principle: DENS
        ? 'The mass of a solid follows from its weight, m = W / g. A solid that sinks pushes aside exactly its own '
          + 'volume of water, so the rise of the water level in a measuring cylinder gives its volume. Its density '
          + 'is then the mass divided by that volume.'
        : 'A body in a liquid is pushed up by an upthrust equal to the weight of the liquid it displaces '
          + '(Archimedes\' principle). The spring balance therefore reads less than the true weight, and the loss in '
          + 'weight is exactly that upthrust. Lowering the solid a little at a time shows the upthrust growing in '
          + 'step with the volume under the surface.',
      formula: DENS ? 'ρ = m / V,   m = W / g,   V = V₂ − V₁' : 'U = W − W′ = ρ g V (under the surface)',
      formulaNote: DENS ? 'read the water level with your eye at the bottom of the meniscus'
        : 'so the slope of the upthrust against submerged volume graph is ρ g',
      more: [DENS
        ? 'The cylinder is graduated in 2 mL and read to 1 mL, so the volume carries the larger error. Three starting '
          + 'levels are used and the three volumes averaged.'
        : 'The liquid level in the jar itself rises as the solid goes in, so the depth is always read against the '
          + 'surface as it stands at that moment.',
        'The balance reads to ' + LCB.toFixed(2) + ' N, so the smallest readings carry the largest percentage error. '
        + 'That is why a straight line is drawn through all the points rather than one reading being trusted.'],
      precautions: 'The solid must hang freely and must not touch the bottom or the sides of the vessel. Let the '
        + 'balance come to rest before you read it, and read the liquid level with your eye level with the bottom of '
        + 'the meniscus.'
    },
    book: {
      at: [-0.6, 0.14, 0.12],
      title: DENS ? 'Expt. — Density of a solid' : 'Expt. — Archimedes\' principle',
      lines: ['Aim: ' + S.lab.aim,
        'Solid: ' + solidName + ', ' + Math.round(SOLID_D * 1000) + ' mm × ' + (HS * 1000).toFixed(1) + ' mm, V = ' + (p.V * 1e6).toFixed(1) + ' cm³',
        'Spring balance 0–' + FULLB + ' N, least count ' + LCB.toFixed(2) + ' N; g = 9.8 m/s²',
        DENS ? 'ρ = m / V,  m = W / g,  V = V₂ − V₁' : 'U = W − W′ = ρ g V_sub',
        'Precautions: the solid must not touch the vessel; read the meniscus at eye level.'],
      columns: DENS
        ? [{ label: 'S.No', get: function (r, i) { return i + 1; } },
          { label: 'W (N)', get: function (r) { return r.W.toFixed(2); } },
          { label: 'V₁ (mL)', get: function (r) { return r.V1.toFixed(0); } },
          { label: 'V₂ (mL)', get: function (r) { return r.V2.toFixed(0); } },
          { label: 'V (mL)', get: function (r) { return (r.V * 1e6).toFixed(0); } }]
        : [{ label: 'S.No', get: function (r, i) { return i + 1; } },
          { label: 'depth (mm)', get: function (r) { return (r.d * 1000).toFixed(0); } },
          { label: 'V_sub (cm³)', get: function (r) { return (r.Vs * 1e6).toFixed(1); } },
          { label: 'W′ (N)', get: function (r) { return r.Wp.toFixed(2); } },
          { label: 'U = W − W′ (N)', get: function (r) { return r.U.toFixed(2); } }]
    },
    graph: DENS ? null : {
      x: function (r) { return r.Vs * 1e6; }, y: function (r) { return r.U; },
      xlabel: 'volume under the surface (cm³)', ylabel: 'upthrust U (N)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; }
    },
    result: function (rows) {
      if (DENS) {
        if (!rows.length) return null;
        var V = S.fit.mean(rows.map(function (r) { return r.V; })), m = rows[0].W / p.g;
        return { label: 'ρ (solid)', value: m / V, unit: 'kg/m³', digits: 0, truth: p.rho_s,
          note: 'Mass from the balance, volume from the mean rise of the water level.' };
      }
      if (rows.length < 2) return null;
      var k = S.fit.origin(rows.map(function (r) { return [r.Vs, r.U]; }));
      return { label: 'ρ (liquid)', value: k / p.g, unit: 'kg/m³', digits: 0, truth: p.rho_l,
        note: 'From the slope of the upthrust against submerged volume graph: slope = ρ g. The loss in weight when '
          + 'fully immersed is the weight of the liquid displaced.' };
    },
    tol: 0.06,
    chips: DENS
      ? ['Why does the water level rise?', 'Check my readings', 'Why three starting levels?', 'Which reading carries the larger error?']
      : ['What is upthrust?', 'Why does the balance read less in the liquid?', 'Check my readings', 'Why does the graph pass through the origin?'],
    viva: DENS
      ? [['The volume of the solid is', ['the rise of the water level', 'the weight divided by g', 'the height of the solid'], 0,
        'A fully immersed solid displaces its own volume of water.'],
      ['A solid of density 2700 kg/m³ in water will', ['sink', 'float', 'stay anywhere'], 0,
        'It is denser than water (1000 kg/m³).']]
      : [['The loss in weight of an immersed solid equals', ['the weight of the liquid displaced', 'its own weight', 'the weight of the jar'], 0,
        'That is Archimedes\' principle.'],
      ['Immersing the solid deeper makes the upthrust', ['larger, until it is fully under', 'smaller', 'unchanged'], 0,
        'U = ρ g V_submerged, and the submerged volume grows until the solid is completely under.']],
    askState: function () {
      return { experiment: DENS ? 'density of a solid' : 'Archimedes\' principle', solid: solidName, liquid: LIQ_NAME,
        sample: vs, solid_volume_cm3: +(p.V * 1e6).toFixed(1), weight_in_air_N: st.Wair,
        balance_reads_N: +readN(reading()).toFixed(2), depth_under_surface_mm: +(depthMm() * 1000).toFixed(1),
        cylinder_V1_mL: st.V1, cylinder_V2_mL: st.V2, balance_least_count_N: LCB,
        readings_taken: S.rows.length };
    },

    steps: DENS
      ? [{ id: 'air', title: 'Weigh it in air', view: 'air',
        render: function (u) {
          u.h2('Hang the solid and weigh it in air');
          u.p('The hand hangs the solid from the balance\'s hook on a thread. The reading is its true weight W; its mass is m = W / g.');
          u.row(u.button('Hang the solid on the balance', function () { hangSolid(); }, true, S.hand.busy || st.busy || st.hung));
          u.task('Weight in air', st.hung, st.hung ? st.Wair.toFixed(2) + ' N  (m = ' + (st.Wair / p.g * 1000).toFixed(0) + ' g)' : 'not taken yet');
          u.live(function () { return 'Balance reads ' + readN(reading()).toFixed(2) + ' N'; });
          u.next('Next: find its volume', st.hung && !S.hand.busy);
        },
        ok: function () { return st.hung; },
        auto: function () { return hangSolid(); } },
      { id: 'vol', title: 'Find its volume', view: 'dip',
        render: function (u) {
          u.h2('Volume by displacement');
          u.p('Pour water into the measuring cylinder and read the level V₁. Then lower the solid until it is '
            + 'completely under the water and read the level again as V₂. The volume of the solid is V₂ − V₁. Do it '
            + 'three times, starting from a different level each time.');
          var r = u.row();
          POURS.forEach(function (v, i) {
            r.appendChild(u.button('Pour to level ' + (i + 1), function () { pourWater(i); }, false, S.hand.busy || st.busy || st.lowered));
          });
          u.row(u.button('Lower the solid in', function () { dipSolid(); }, true, S.hand.busy || st.busy || !st.hung || st.lowered),
            u.button('Raise it out', function () { raiseSolid(); }, false, S.hand.busy || st.busy || !st.lowered));
          u.row(u.button('Record V₁ and V₂', function () { recordVolume(); }, true, S.hand.busy || st.busy || !st.lowered));
          u.live(function () {
            return 'V₁ = ' + st.V1.toFixed(0) + ' mL · level now ' + volMl(st.V0 + p.V * settle().frac).toFixed(1)
              + ' mL · solid ' + (st.lowered ? 'fully under water' : 'out of the water');
          });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 3) u.p(S.rows.length + ' of 3 trials done.');
          u.next('Next: result', S.rows.length >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          return POURS.reduce(function (pr, v, i) {
            return pr.then(function () { return raiseSolid(); }).then(function () { return pourWater(i); })
              .then(function () { return dipSolid(); }).then(function () { recordVolume(); });
          }, Promise.resolve());
        } }]
      : [{ id: 'air', title: 'Weigh it in air', view: 'air',
        render: function (u) {
          u.h2('Hang the solid and weigh it in air');
          u.p('The hand hangs the solid from the balance\'s hook on a thread, well above the liquid. The reading is its true weight W.');
          u.row(u.button('Hang the solid on the balance', function () { hangSolid(); }, true, S.hand.busy || st.busy || st.hung));
          u.task('Weight in air', st.hung, st.hung ? st.Wair.toFixed(2) + ' N' : 'not taken yet');
          u.live(function () { return 'Balance reads ' + readN(reading()).toFixed(2) + ' N'; });
          u.next('Next: lower it into the liquid', st.hung && !S.hand.busy);
        },
        ok: function () { return st.hung; },
        auto: function () { return hangSolid(); } },
      { id: 'dip', title: 'Lower it in, step by step', view: 'dip',
        render: function (u) {
          u.h2('Lower the solid into the liquid');
          u.p('The hand slides the boss down the rod. At each depth read the balance and the millimetre scale on the '
            + 'jar, then record. The upthrust is the loss in weight, U = W − W′.');
          var r = u.row();
          IMM.forEach(function (f) {
            var done = S.rows.some(function (q) { return q.want === f; });
            r.appendChild(u.button((done ? '✓ ' : '') + (f === 1 ? 'fully in' : Math.round(f * 100) + '% in'),
              function () { lowerTo(f); }, false, S.hand.busy || st.busy || done));
          });
          u.row(u.button('Record this reading', function () { recordImmersion(st.lastFrac); },
            true, S.hand.busy || st.busy || depthMm() <= 0 || !st.lastFrac));
          u.live(function () {
            return 'Balance ' + readN(reading()).toFixed(2) + ' N · depth under the surface ' + (depthMm() * 1000).toFixed(1)
              + ' mm · upthrust ' + (st.Wair - readN(reading())).toFixed(2) + ' N';
          });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 4) u.p(S.rows.length + ' of 4 depths done.');
          u.next('Next: graph and result', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          return IMM.reduce(function (pr, f) {
            return pr.then(function () { return lowerTo(f); }).then(function () { recordImmersion(f); });
          }, Promise.resolve());
        } }],

    tick: function () { pose(); }
  };
  return EXP;
});
