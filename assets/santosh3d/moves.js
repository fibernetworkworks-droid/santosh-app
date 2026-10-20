/* Hoola moves: real body movement for an avatar built with HoolaAvatar.build(look, { rig: true }).
 *
 *   const mover = HoolaMoves.attach(parts);   // parts = the build() result
 *   mover.play('bhangra');                    // any id in HoolaMoves.MOVES
 *   mover.update(dt, t);                      // every frame, before render
 *
 * A move is a function of time that returns a pose (joint angles + body squash, jump height, spin).
 * The mover eases the skeleton toward that pose every frame, so switching moves always blends smoothly.
 * Angles: shoulder z = raise sideways (outward is +s), shoulder x < 0 = raise forward, elbow x < 0 = bend forward,
 * hip x < 0 = leg forward, knee x > 0 = bend back. s = -1 for the avatar's right side (screen left), +1 for the left.
 */
(function () {
  const TAU = Math.PI * 2;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ease = (x) => x < .5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
  const pulse = (x) => Math.max(0, Math.sin(x));                 // half-wave
  const S = [-1, 1];

  function base() {
    return {
      root: { y: 0, ry: 0 }, body: { rx: 0, ry: 0, rz: 0, dy: 0, sq: 0 }, neck: { x: 0, y: 0, z: 0 },
      sh: { '-1': { x: 0, y: 0, z: -.12 }, '1': { x: 0, y: 0, z: .12 } },
      el: { '-1': { x: -.18, y: 0, z: 0 }, '1': { x: -.18, y: 0, z: 0 } },
      hip: { '-1': { x: 0, z: 0 }, '1': { x: 0, z: 0 } },
      kn: { '-1': { x: 0 }, '1': { x: 0 } },
      face: { smile: 1.1, open: 0, squint: 1 }, phone: 0,
    };
  }
  // bend both legs by angle a and drop the body so the feet stay on the floor
  function crouch(p, a, side) {
    for (const s of side ? [side] : S) { p.hip[s].x -= a; p.kn[s].x += 2 * a; }
    if (!side) p.body.dy -= .98 * (1 - Math.cos(a));
  }
  function arm(p, s, x, z, ex, y, ez) {
    p.sh[s].x = x; p.sh[s].z = s * z; p.sh[s].y = y || 0; p.el[s].x = ex; p.el[s].z = ez || 0;
  }

  const MOVES = [
    { id: 'idle', label: 'Aaram', en: 'Relax' },
    { id: 'phone', label: 'Phone', en: 'On the phone' },
    { id: 'wave', label: 'Hello', en: 'Wave' },
    { id: 'namaste', label: 'Namaste', en: 'Namaste' },
    { id: 'bhangra', label: 'Bhangra', en: 'Dance' },
    { id: 'groove', label: 'Disco', en: 'Groove' },
    { id: 'jump', label: 'Kudo', en: 'Jump' },
    { id: 'spin', label: 'Ghoomo', en: 'Spin' },
    { id: 'clap', label: 'Taali', en: 'Clap' },
    { id: 'walk', label: 'Chalo', en: 'Walk' },
    { id: 'cheer', label: 'Jeet gaye!', en: 'Cheer' },
    { id: 'think', label: 'Socho', en: 'Think' },
    { id: 'yoga', label: 'Yoga', en: 'Tree pose' },
  ];

  const POSE = {
    idle(t) {
      const p = base();
      p.body.rz = Math.sin(t * 1.1) * .025; p.body.dy = Math.sin(t * 2.2) * .01;
      p.neck.y = Math.sin(t * .5) * .25; p.neck.x = .03 + Math.sin(t * .7) * .04;
      for (const s of S) { p.sh[s].z = s * (.12 + Math.sin(t * 1.1 + s) * .03); p.sh[s].x = Math.sin(t * 1.1) * .04 * s; }
      return p;
    },
    phone(t) {
      const p = base(); p.phone = 1; p.neck.x = .32; p.face.smile = 1;
      for (const s of S) arm(p, s, -.55, -.2, -1.35, -s * .55);
      p.body.dy = Math.sin(t * 2.2) * .01;
      return p;
    },
    wave(t) {
      const p = POSE.idle(t); const s = -1;
      arm(p, s, -.15, 2.35, -.35, 0, s * (.35 + .45 * Math.sin(t * 9)));
      p.neck.z = .12; p.neck.y = -.15; p.body.rz = .05; p.face.smile = 1.45; p.face.open = .25; p.face.squint = .7;
      return p;
    },
    namaste(t) {
      const p = base();
      const bow = ease(clamp((t % 3.2) / .8, 0, 1)) * (1 - ease(clamp(((t % 3.2) - 2.2) / .8, 0, 1)));
      for (const s of S) arm(p, s, -.75, -.28, -1.75, -s * .82, 0);
      p.body.rx = .14 * bow; p.neck.x = .05 + .16 * bow; p.face.smile = 1.2; p.face.squint = 1 - .55 * bow;
      return p;
    },
    bhangra(t) {
      const p = base(); const b = .42, ph = t / b * Math.PI;   // one bounce per beat
      crouch(p, .16 + .12 * Math.abs(Math.sin(ph)));
      for (const s of S) {
        const pump = Math.sin(ph + (s > 0 ? 0 : Math.PI));
        arm(p, s, -.25, 2.55 + .25 * pump, -.55 - .2 * pump, 0, s * .2);
      }
      const k = Math.floor(t / (2 * b)) % 2 ? 1 : -1;            // alternate the kicking leg every two beats
      const lift = pulse(ph);
      p.hip[k].x -= .55 * lift; p.kn[k].x += .85 * lift;
      p.body.ry = .22 * Math.sin(ph / 2); p.body.rz = .06 * Math.sin(ph / 2);
      p.neck.z = .14 * Math.sin(ph); p.neck.x = -.05;
      p.face.smile = 1.5; p.face.open = .35 + .2 * Math.abs(Math.sin(ph)); p.face.squint = .65;
      return p;
    },
    groove(t) {
      const p = base(); const b = .5, ph = t / b * Math.PI;
      const up = Math.sin(ph) > 0;
      arm(p, -1, up ? -.2 : -.35, up ? 2.5 : .55, up ? -.1 : -.3, 0);          // disco point: up, then down across
      if (!up) { p.sh['-1'].x = -.6; p.sh['-1'].z = .35; }
      arm(p, 1, 0, .25, -1.6, .2);                                              // hand on hip
      p.body.rz = .12 * Math.sin(ph); p.body.ry = up ? .25 : -.15;
      for (const s of S) { const a = .12 + .14 * pulse(ph + (s > 0 ? Math.PI : 0)); p.hip[s].x -= a; p.kn[s].x += 2 * a; }
      p.body.dy = -.05 - .03 * Math.abs(Math.sin(ph));
      p.neck.z = -.15 * Math.sin(ph); p.neck.y = up ? -.25 : .15;
      p.face.smile = 1.4; p.face.open = .2; p.face.squint = .75;
      return p;
    },
    jump(t) {
      const p = base(); const c = 1.4, x = (t % c) / c;
      if (x < .25) {                                   // wind up
        const a = ease(x / .25); crouch(p, .55 * a);
        for (const s of S) arm(p, s, .55 * a, .15, -.3, 0);
        p.body.sq = .12 * a; p.body.rx = .15 * a;
      } else if (x < .7) {                             // up in the air
        const u = (x - .25) / .45, h = Math.sin(u * Math.PI);
        p.root.y = 1.15 * h;
        for (const s of S) arm(p, s, -.3, 2.6 * Math.min(1, u * 3), -.25, 0);
        for (const s of S) { p.hip[s].x = -.35 * h; p.kn[s].x = .9 * h; }
        p.body.sq = -.1 * (1 - u); p.face.open = .45; p.face.smile = 1.5;
      } else {                                         // land, squash, settle
        const v = (x - .7) / .3, a = .45 * (1 - ease(v));
        crouch(p, a); p.body.sq = .14 * (1 - v);
        for (const s of S) arm(p, s, .2 * (1 - v), .5 * (1 - v) + .12, -.3, 0);
        p.face.smile = 1.4;
      }
      p.face.squint = .8;
      return p;
    },
    spin(t) {
      const p = base(); const c = 2.2, x = (t % c) / c;
      if (x < .5) {
        const u = ease(x / .5); p.root.ry = u * TAU;
        for (const s of S) arm(p, s, -.1, 1.45, -.15, 0);
        p.hip['1'].x = -.25; p.kn['1'].x = .9; p.root.y = .08 * Math.sin(u * Math.PI);
        p.face.open = .3; p.face.smile = 1.4;
      } else {                                         // ta-da
        const v = ease(clamp((x - .5) / .2, 0, 1));
        for (const s of S) arm(p, s, -.3 * v, 1.45 + .9 * v, -.2, 0);
        p.neck.x = -.12 * v; p.face.smile = 1.55; p.face.squint = .6; p.face.open = .3;
      }
      return p;
    },
    clap(t) {
      const p = base(); const ph = t / .32 * Math.PI, o = Math.abs(Math.sin(ph));
      for (const s of S) arm(p, s, -.95, -.2 + .45 * o, -1.25, -s * (.45 - .35 * o), 0);
      p.body.dy = -.03 * (1 - o); p.neck.x = .05; p.face.smile = 1.5; p.face.open = .2; p.face.squint = .7;
      return p;
    },
    walk(t) {
      const p = base(); const ph = t / .55 * Math.PI;
      for (const s of S) {
        const sw = Math.sin(ph + (s > 0 ? 0 : Math.PI));
        p.hip[s].x = -.62 * sw; p.kn[s].x = .6 * pulse(-sw * Math.PI / 2 + Math.PI / 2) * (sw < 0 ? 1 : .2);
        arm(p, s, .5 * sw, .12, -.35, 0);
      }
      p.body.dy = -.035 * Math.abs(Math.cos(ph)); p.body.ry = .08 * Math.sin(ph); p.neck.y = -.08 * Math.sin(ph);
      p.face.smile = 1.2;
      return p;
    },
    cheer(t) {
      const p = base(); const ph = t / .3 * Math.PI;
      for (const s of S) arm(p, s, -.1, 2.45 + .12 * Math.sin(ph), -.35 - .25 * Math.abs(Math.sin(ph)), 0);
      p.root.y = .35 * Math.abs(Math.sin(t / .6 * Math.PI));
      for (const s of S) { p.hip[s].x = -.2 * Math.abs(Math.sin(t / .6 * Math.PI)); p.kn[s].x = .45 * Math.abs(Math.sin(t / .6 * Math.PI)); }
      p.neck.x = -.18; p.face.smile = 1.6; p.face.open = .55; p.face.squint = .55;
      return p;
    },
    think(t) {
      const p = base();
      arm(p, -1, -.2, 1.95, -.15, 0, -1.75 - .12 * Math.sin(t * 7));  // scratching the head
      arm(p, 1, 0, .25, -1.6, .2);                                    // other hand on the hip
      p.neck.x = -.15; p.neck.z = .16; p.neck.y = .12 + .05 * Math.sin(t * .8); p.body.rz = -.04;
      p.face.smile = .6; p.face.open = .06;
      return p;
    },
    yoga(t) {
      const p = base(); const w = Math.sin(t * 1.6) * .03;
      for (const s of S) arm(p, s, -.08, 2.45, 0, 0, s * .95);          // palms together overhead
      p.hip['1'].z = .95; p.hip['1'].x = -.2; p.kn['1'].x = 2.2;        // tree pose: foot on the other knee
      p.body.rz = w; p.body.dy = -.02; p.neck.x = -.05; p.face.smile = 1.1; p.face.squint = .35;
      return p;
    },
  };

  function attach(A) {
    if (!A.rig) throw new Error('build the avatar with { rig: true }');
    const R = A.rig;
    let move = 'idle', t0 = 0, now = 0;
    const cur = base();
    const lerp = (o, n, k) => { for (const key in n) { if (typeof n[key] === 'object') lerp(o[key], n[key], k); else o[key] += (n[key] - o[key]) * k; } };
    const api = {
      move: () => move,
      play(id) { if (POSE[id] && id !== move) { move = id; t0 = now; } },
      update(dt, t) {
        now = t;
        const target = POSE[move](t - t0);
        lerp(cur, target, 1 - Math.exp(-dt * (move === 'jump' || move === 'spin' ? 22 : 13)));
        A.root.position.y = (A.root.userData.baseY ?? (A.root.userData.baseY = A.root.position.y)) + cur.root.y;
        A.root.rotation.y = cur.root.ry;
        const b = A.body; b.rotation.set(cur.body.rx, cur.body.ry, cur.body.rz); b.position.y = cur.body.dy;
        const q = cur.body.sq; b.scale.set(1 + q * .5, 1 - q, 1 + q * .5);
        A.neck.rotation.set(cur.neck.x, cur.neck.y, cur.neck.z);
        for (const s of S) {
          R.shoulder[s].rotation.set(cur.sh[s].x, cur.sh[s].y, cur.sh[s].z);
          R.elbow[s].rotation.set(cur.el[s].x, cur.el[s].y, cur.el[s].z);
          R.hip[s].rotation.set(cur.hip[s].x, 0, cur.hip[s].z);
          R.knee[s].rotation.set(cur.kn[s].x, 0, 0);
          R.foot[s].rotation.x = -(cur.hip[s].x + cur.kn[s].x) * .85;    // keep soles near flat
        }
        A.phone.visible = cur.phone > .5;
        A.phone.position.set(0, .62, 1.13);
        A.smile.scale.set(.85 + cur.face.smile * .25, .7 + cur.face.smile * .35, 1);
        const o = clamp(cur.face.open, 0, 1); A.mouthIn.visible = o > .02; A.mouthIn.scale.set(.13 + o * .02, .012 + o * .12, .05);
        return cur;
      },
    };
    return api;
  }

  window.HoolaMoves = { MOVES, POSE, attach };
})();
