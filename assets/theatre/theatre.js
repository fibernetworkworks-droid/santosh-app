/* Hoola Work Theatre \u2014 real-time 3D scenes of the work Hoola is doing, built around the existing Hoola avatar
 * (the same clay character as assets/santosh3d: orange puffer hoodie, round glasses, phone).
 * HoolaTheatre.mount(canvas, sceneName) -> { set(data), dispose() }
 * Scenes: email, browser, payment, bluetooth, network, pc, work. Driven by the server's `work` events. Everything is three.js geometry; screens are live canvas
 * textures redrawn from the data the app sends (step, counts, fields), so the picture always matches the real work.
 */
(function () {
  const T = window.THREE;
  if (!T) return;
  if (T.ColorManagement) T.ColorManagement.legacyMode = false;
  const V3 = T.Vector3;
  const P = (o) => new T.MeshPhysicalMaterial(o);
  const SPH = new T.SphereGeometry(1, 48, 36);
  const SPH_LO = new T.SphereGeometry(1, 24, 18);
  const FONT = '"Manrope", system-ui, sans-serif';
  const DISPLAY = '"Sora", "Manrope", system-ui, sans-serif';

  function mesh(geo, mat, parent, pos, scale, rot) {
    const m = new T.Mesh(geo, mat);
    if (pos) m.position.set(pos[0], pos[1], pos[2]);
    if (scale) m.scale.set(scale[0], scale[1], scale[2]);
    if (rot) m.rotation.set(rot[0], rot[1], rot[2]);
    m.castShadow = true; m.receiveShadow = true;
    if (parent) parent.add(m);
    return m;
  }
  function limb(a, b, r, mat, parent) {
    const dir = new V3().subVectors(b, a); const len = dir.length();
    const m = new T.Mesh(new T.CapsuleGeometry(r, len, 8, 18), mat);
    m.position.copy(a).add(b).multiplyScalar(.5);
    m.quaternion.setFromUnitVectors(new V3(0, 1, 0), dir.normalize());
    m.castShadow = true; m.receiveShadow = true; parent.add(m); return m;
  }
  function rshape(w, h, r) {
    const s = new T.Shape();
    s.moveTo(-w / 2 + r, -h / 2); s.lineTo(w / 2 - r, -h / 2); s.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
    s.lineTo(w / 2, h / 2 - r); s.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2); s.lineTo(-w / 2 + r, h / 2);
    s.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r); s.lineTo(-w / 2, -h / 2 + r); s.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
    return s;
  }
  /** Rounded slab centred on the origin, front face at +z. */
  function rbox(w, h, d, r) {
    const bev = Math.min(r * .5, d * .45);
    const g = new T.ExtrudeGeometry(rshape(w - bev * 2, h - bev * 2, Math.max(.001, r - bev)), {
      depth: Math.max(.001, d - bev * 2), bevelEnabled: true, bevelThickness: bev, bevelSize: bev, bevelSegments: 4, curveSegments: 10 });
    g.translate(0, 0, -(d - bev * 2) / 2);
    return g;
  }
  function rr(x, X, Y, W, H, R) {
    x.beginPath(); x.moveTo(X + R, Y); x.arcTo(X + W, Y, X + W, Y + H, R); x.arcTo(X + W, Y + H, X, Y + H, R);
    x.arcTo(X, Y + H, X, Y, R); x.arcTo(X, Y, X + W, Y, R); x.closePath();
  }
  function canvasTex(w, h) {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    const x = c.getContext('2d');
    const tex = new T.CanvasTexture(c); tex.encoding = T.sRGBEncoding; tex.anisotropy = 4;
    return { c, x, tex };
  }
  function glowTex(rgba) {
    const { x, tex } = canvasTex(128, 128);
    const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, rgba); g.addColorStop(1, 'rgba(0,0,0,0)');
    x.fillStyle = g; x.fillRect(0, 0, 128, 128); return tex;
  }
  /** A text pill that always faces the camera. */
  function label(text, bg, fg, h) {
    const t = canvasTex(1024, 160);
    const mat = new T.SpriteMaterial({ map: t.tex, transparent: true, depthWrite: false, depthTest: false, toneMapped: false });
    const sp = new T.Sprite(mat);
    const H = h || .32;
    sp.userData.draw = (txt, b, f) => {
      const x = t.x; x.clearRect(0, 0, 1024, 160);
      x.font = `800 84px ${FONT}`;
      const w = Math.min(1000, x.measureText(txt).width + 90);
      rr(x, (1024 - w) / 2, 18, w, 124, 62); x.fillStyle = b; x.fill();
      x.lineWidth = 6; x.strokeStyle = 'rgba(255,255,255,.22)'; x.stroke();
      x.fillStyle = f; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(txt, 512, 84);
      t.tex.needsUpdate = true;
    };
    sp.userData.text = [text, bg, fg];
    sp.userData.draw(text, bg, fg);
    sp.scale.set(H * 6.4, H, 1);
    sp.renderOrder = 10;
    return sp;
  }

  /* ============================================================ the Hoola avatar (same build as santosh3d) */
  function makeAvatar(opt) {
    const o = Object.assign({ hoodie: 0xf29418, seam: 0xdc7f10, rib: 0xee7b2c, strap: 0x27358c, skin: 0xcc8a5e,
      pants: 0x2c3566, lace: 0xf29418, scale: .42 }, opt || {});
    const M = {
      skin: P({ color: o.skin, roughness: .5, sheen: .18, sheenColor: new T.Color(0xff9e80), sheenRoughness: .6, clearcoat: .06, envMapIntensity: .35 }),
      skinDp: P({ color: 0xc47c55, roughness: .6, sheen: .3, sheenColor: new T.Color(0xff9e80), envMapIntensity: .5 }),
      nose: P({ color: 0xd88460, roughness: .5, sheen: .4, sheenColor: new T.Color(0xffa080), envMapIntensity: .55 }),
      hair: P({ color: 0x17110e, roughness: .36, clearcoat: .55, clearcoatRoughness: .28, envMapIntensity: .45 }),
      white: P({ color: 0xfbfaf6, roughness: .18, clearcoat: 1, clearcoatRoughness: .05, envMapIntensity: .7 }),
      iris: P({ color: 0x3e2414, roughness: .25, clearcoat: 1 }),
      pupil: P({ color: 0x0a0605, roughness: .2, clearcoat: 1 }),
      shine: new T.MeshBasicMaterial({ color: 0xffffff }),
      frame: P({ color: 0x141416, roughness: .22, clearcoat: 1, envMapIntensity: .6 }),
      lens: P({ color: 0xffffff, roughness: .04, transparent: true, opacity: .1, clearcoat: 1, envMapIntensity: 1.6, depthWrite: false }),
      lip: P({ color: 0x7c3020, roughness: .45 }),
      mouth: P({ color: 0x4a1512, roughness: .6 }),
      hoodie: P({ color: o.hoodie, roughness: .58, sheen: .3, sheenColor: new T.Color(0xffc46b), sheenRoughness: .5, clearcoat: .12, envMapIntensity: .4 }),
      rib: P({ color: o.rib, roughness: .8, sheen: .2 }),
      strap: P({ color: o.strap, roughness: .48, clearcoat: .25 }),
      zip: P({ color: 0x3a2b20, roughness: .4, metalness: .2 }),
      cord: P({ color: 0xa24f16, roughness: .55 }),
      phone: P({ color: 0x26272c, roughness: .28, metalness: .35, clearcoat: 1, envMapIntensity: 1 }),
      glass: P({ color: 0x0d0e12, roughness: .08, metalness: .2, clearcoat: 1, envMapIntensity: 1.4 }),
      screen: new T.MeshBasicMaterial({ color: 0x9fd0ff }),
      pants: P({ color: o.pants, roughness: .62, sheen: .25, envMapIntensity: .4 }),
      shoe: P({ color: 0xf7f5f2, roughness: .4, clearcoat: .4, envMapIntensity: .5 }),
      sole: P({ color: 0xd9d3e8, roughness: .5 }),
      lace: P({ color: o.lace, roughness: .5 })
    };
    const holder = new T.Group();
    const root = new T.Group(); holder.add(root);
    const body = new T.Group(); root.add(body);
    [[-0.35, 1.16, .5, .86], [0.12, 1.2, .5, .88], [0.58, 1.22, .5, .9], [1.02, 1.26, .46, .88]].forEach(([y, sx, sy, sz]) =>
      mesh(SPH, M.hoodie, body, [0, y, 0], [sx * .82, sy * .82, sz * .82]));
    mesh(new T.TorusGeometry(.5, .22, 18, 48), M.hoodie, body, [0, 1.36, -.2], [1.28, 1, 1], [Math.PI / 2 - .38, 0, 0]);
    mesh(new T.CylinderGeometry(.37, .4, .36, 36), M.rib, body, [0, 1.42, .02]);
    [1.3, 1.4, 1.5].forEach(y => mesh(new T.TorusGeometry(.385, .022, 8, 36), M.rib, body, [0, y, .02], null, [Math.PI / 2, 0, 0]));
    mesh(new T.BoxGeometry(.05, 1.38, .03), M.zip, body, [0, .52, .73]);
    [-1, 1].forEach(s => {
      limb(new V3(s * .15, 1.24, .62), new V3(s * .16, .78, .74), .017, M.cord, body);
      const curve = new T.CatmullRomCurve3([new V3(s * .5, 1.28, -.36), new V3(s * .62, 1.46, 0), new V3(s * .66, 1.26, .45),
        new V3(s * .67, .78, .6), new V3(s * .67, .18, .61), new V3(s * .65, -.3, .56)]);
      mesh(new T.TubeGeometry(curve, 48, .075, 10), M.strap, body);
    });
    const hands = [];
    [-1, 1].forEach(s => {
      const sh = new V3(s * 1.0, 1.1, 0), el = new V3(s * 1.2, .36, .28), wr = new V3(s * .44, .5, 1.0);
      mesh(SPH, M.hoodie, body, [sh.x, sh.y, sh.z], [.36, .36, .36]);
      limb(sh, el, .3, M.hoodie, body);
      mesh(SPH, M.hoodie, body, [el.x, el.y, el.z], [.3, .3, .3]);
      limb(el, wr, .27, M.hoodie, body);
      const hand = new T.Group(); hand.position.set(s * .34, .55, 1.08); body.add(hand);
      mesh(SPH, M.skin, hand, [0, 0, 0], [.17, .21, .19]);
      for (let i = 0; i < 3; i++) mesh(SPH_LO, M.skin, hand, [s * -.05, .12 - i * .1, .15], [.065, .055, .06]);
      hands.push(hand);
    });
    const phone = new T.Group(); phone.position.set(0, .62, 1.13); phone.rotation.x = .5; body.add(phone);
    mesh(rbox(.62, 1.02, .08, .1), M.phone, phone);
    mesh(new T.CylinderGeometry(.045, .045, .02, 20), M.glass, phone, [-.19, .38, .05], null, [Math.PI / 2, 0, 0]);
    const scr = new T.Mesh(new T.PlaneGeometry(.56, .96), M.screen); scr.position.z = -.045; scr.rotation.y = Math.PI; phone.add(scr);
    const screenLight = new T.PointLight(0x9fd0ff, 0, 3.2, 2); screenLight.position.set(0, 1.05, .95); body.add(screenLight);
    mesh(SPH, M.pants, body, [0, -.62, 0], [.74, .32, .58]);
    [-1, 1].forEach(s => {
      limb(new V3(s * .32, -.62, 0), new V3(s * .34, -1.42, .02), .25, M.pants, body);
      const shoe = new T.Group(); shoe.position.set(s * .36, -1.6, .14); shoe.rotation.y = s * -.12; body.add(shoe);
      mesh(SPH, M.shoe, shoe, [0, .02, 0], [.27, .17, .42]);
      mesh(new T.CylinderGeometry(1, 1, 1, 30), M.sole, shoe, [0, -.1, 0], [.28, .06, .43]);
      mesh(SPH_LO, M.lace, shoe, [0, .12, .14], [.1, .04, .14]);
    });
    const neck = new T.Group(); neck.position.set(0, 1.55, .03); body.add(neck);
    const head = new T.Group(); head.position.set(0, 1.04, .02); neck.add(head);
    const HS = [1, .95, .92];
    const bulge = (yu) => .11 * Math.exp(-(((yu + .38) / .36) ** 2));
    const headGeo = new T.SphereGeometry(1, 64, 48);
    { const pa = headGeo.attributes.position;
      for (let i = 0; i < pa.count; i++) { const b = bulge(pa.getY(i)); pa.setX(i, pa.getX(i) * (1 + b)); pa.setZ(i, pa.getZ(i) * (1 + b * .85)); }
      headGeo.computeVertexNormals(); }
    mesh(headGeo, M.skin, head, [0, 0, 0], HS);
    function surf(x, y) {
      const yu = y / HS[1], b = bulge(yu); const xu = x / (HS[0] * (1 + b));
      const z = HS[2] * (1 + b * .85) * Math.sqrt(Math.max(0, 1 - xu * xu - yu * yu));
      return { p: new V3(x, y, z), n: new V3(xu / HS[0], yu / HS[1], z / (HS[2] * (1 + b * .85)) ** 2 * HS[2]).normalize() };
    }
    function place(obj, x, y, off) { const { p, n } = surf(x, y); obj.position.copy(p).addScaledVector(n, off); obj.lookAt(obj.position.clone().add(n)); head.add(obj); return obj; }
    [-1, 1].forEach(s => { mesh(SPH_LO, M.skin, head, [s * .97, -.04, -.02], [.14, .23, .18]); mesh(SPH_LO, M.skinDp, head, [s * 1.03, -.04, .01], [.06, .14, .1]); });
    const eyes = [], irises = [];
    [-1, 1].forEach(s => {
      const g = new T.Group(); place(g, s * .35, .04, 0);
      const ball = new T.Group(); g.add(ball);
      mesh(SPH, M.white, ball, [0, 0, 0], [.2, .215, .11]);
      const ir = new T.Group(); ir.position.z = .07; ball.add(ir);
      mesh(SPH, M.iris, ir, [0, 0, 0], [.135, .14, .045]);
      mesh(SPH, M.pupil, ir, [0, 0, .022], [.085, .088, .03]);
      mesh(SPH_LO, M.shine, ball, [.055, .065, .125], [.042, .042, .01]).castShadow = false;
      eyes.push(ball); irises.push(ir);
    });
    const rings = [];
    [-1, 1].forEach(s => {
      const ring = new T.Group(); place(ring, s * .35, .05, .2);
      mesh(new T.TorusGeometry(.275, .03, 14, 48), M.frame, ring);
      ring.add(new T.Mesh(new T.CircleGeometry(.27, 36), M.lens)); rings.push(ring);
    });
    head.updateMatrixWorld(true);
    const inv = head.matrixWorld.clone().invert();
    const ringPt = (ring, x) => ring.localToWorld(new V3(x, 0, 0)).applyMatrix4(inv);
    limb(ringPt(rings[0], .27), ringPt(rings[1], -.27), .022, M.frame, head);
    [[rings[0], -.27, -1], [rings[1], .27, 1]].forEach(([r, x, s]) => limb(ringPt(r, x), new V3(s * .99, .1, -.08), .024, M.frame, head));
    const brows = [];
    [-1, 1].forEach(s => {
      const b = new T.Mesh(new T.CapsuleGeometry(.05, .2, 6, 12), M.hair);
      place(b, s * .35, .4, .035); b.rotateZ(Math.PI / 2 + s * -.18); brows.push({ m: b, base: b.position.clone() });
    });
    place(mesh(SPH_LO, M.nose, new T.Group(), null, [.1, .085, .08]), 0, -.17, -.005);
    const smile = new T.Mesh(new T.TorusGeometry(.17, .024, 10, 36, 2.2), M.lip);
    place(smile, 0, -.43, .005); smile.rotateZ(-Math.PI / 2 - 1.1);
    const mouthIn = new T.Mesh(SPH, M.mouth); place(mouthIn, 0, -.47, -.025); mouthIn.scale.set(.14, .001, .05);
    const blushMat = new T.MeshBasicMaterial({ map: glowTex('rgba(255,110,110,.9)'), transparent: true, opacity: .42, depthWrite: false });
    [-1, 1].forEach(s => place(new T.Mesh(new T.PlaneGeometry(.42, .3), blushMat), s * .58, -.25, .012));
    mesh(new T.SphereGeometry(1.04, 48, 36, 0, Math.PI * 2, 0, 1.9), M.hair, head, [0, 0, 0], [1, .96, .95], [-1.0, 0, 0]);
    [[[.1, .98, .45], [.62, .3, .5], [.5, 0, -.25]], [[-.42, .9, .38], [.48, .26, .42], [.4, 0, .55]], [[.56, .82, .3], [.42, .24, .45], [.3, 0, -.75]],
     [[0, 1.0, -.15], [.78, .33, .72], [0, 0, 0]], [[.32, 1.13, .26], [.4, .17, .3], [.2, .3, -.6]], [[-.12, 1.1, .34], [.34, .15, .3], [.5, -.2, .4]],
     [[-.64, .72, .44], [.26, .18, .3], [.2, 0, .9]], [[.86, .45, -.06], [.27, .42, .55], [0, 0, -.15]], [[-.86, .45, -.06], [.27, .42, .55], [0, 0, .15]],
     [[0, .35, -.82], [.86, .66, .36], [0, 0, 0]]].forEach(([p, s, r]) => mesh(SPH, M.hair, head, p, s, r));

    holder.scale.setScalar(o.scale);
    holder.position.y = 1.7 * o.scale;
    const S = { hx: 0, hy: 0, hz: 0, ex: 0, ey: 0, smile: 1, squint: 1, brow: 0, open: 0, screen: .15, bob: 0 };
    let blinkAt = 2 + Math.random() * 2, blinkT = -1, moodT = 0, lastMood = 'idle';
    const bubble = label(' ', 'rgba(18,14,42,.94)', '#FFE3C2', .3);
    bubble.position.set(0, 4.15, 0); bubble.scale.multiplyScalar(1 / o.scale); root.add(bubble);
    const api = {
      holder, root, body, phone, hands, M,
      mood: 'idle', talking: false, yaw: 0,
      say(text) { if (bubble.userData.text[0] !== text) { bubble.userData.text[0] = text; bubble.userData.draw(text, 'rgba(18,14,42,.94)', '#FFE3C2'); } bubble.visible = !!text; },
      redraw() { const u = bubble.userData.text; bubble.userData.draw(u[0], u[1], u[2]); },
      update(t, dt) {
        if (api.mood !== lastMood) { lastMood = api.mood; moodT = 0; }
        moodT += dt;
        const k = 1 - Math.exp(-dt * 6);
        const G = { hx: .05, hy: Math.sin(t * .4) * .18, hz: 0, ex: Math.sin(t * .7) * .03, ey: 0, smile: 1, squint: 1, brow: 0, open: 0, screen: .2, bob: 0 };
        if (api.mood === 'working') { G.hx = .38 + Math.sin(t * .7) * .03; G.hy = Math.sin(t * .5) * .08; G.ey = -.06; G.smile = .85; G.screen = 1.25 + Math.sin(t * 9) * .12; }
        if (api.mood === 'thinking') { G.hx = -.16; G.hy = .22; G.hz = .14; G.ex = .045; G.ey = .06; G.smile = .6; G.brow = .07; G.open = .08; }
        if (api.mood === 'look') { G.hx = -.05; G.hy = .45; G.ex = .04; G.smile = 1.05; }
        if (api.mood === 'happy') { G.smile = 1.38; G.squint = .6; G.brow = .05; G.open = .3; G.bob = Math.abs(Math.sin(moodT * 6)) * .07 * Math.max(.25, 1 - moodT / 1.6); }
        if (api.talking) { const v = Math.max(0, Math.sin(t * 13) * .55 + Math.sin(t * 7.7) * .35); G.open = Math.max(G.open, .12 + v * .6); }
        for (const key in G) S[key] += (G[key] - S[key]) * k;
        if (blinkT < 0 && t > blinkAt) blinkT = 0;
        let lid = 1;
        if (blinkT >= 0) { blinkT += dt; lid = blinkT < .07 ? 1 - blinkT / .07 : Math.min(1, (blinkT - .07) / .09); lid = .06 + .94 * lid;
          if (blinkT > .16) { blinkT = -1; blinkAt = t + 2.2 + Math.random() * 3; } }
        const breath = Math.sin(t * 1.6);
        body.position.y = S.bob + breath * .012;
        root.rotation.y = api.yaw + Math.sin(t * .35) * .08;
        neck.rotation.set(S.hx, S.hy, S.hz);
        eyes.forEach(e => { e.scale.y = S.squint * lid; });
        irises.forEach(ir => { ir.position.x = S.ex; ir.position.y = S.ey; });
        brows.forEach(b => { b.m.position.copy(b.base).y += S.brow; });
        smile.scale.set(.85 + S.smile * .25, .7 + S.smile * .35, 1);
        const op = Math.max(0, Math.min(1, S.open)); mouthIn.visible = op > .02; mouthIn.scale.set(.13 + op * .02, .012 + op * .12, .05);
        screenLight.intensity = S.screen; M.screen.color.setRGB(.55 + S.screen * .2, .75 + S.screen * .12, 1);
        const tap = api.mood === 'working' ? 1 : 0;
        hands[0].position.z = 1.08 + tap * Math.max(0, Math.sin(t * 11)) * .025;
        hands[1].position.z = 1.08 + tap * Math.max(0, Math.sin(t * 11 + 1.7)) * .025;
      }
    };
    api.say('');
    return api;
  }

  /* ============================================================ shared stage */
  function makeStage(canvas, accent, opts) {
    const renderer = new T.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.outputEncoding = T.sRGBEncoding;
    renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(30, 1, .1, 100);
    const env = new T.Scene();
    env.add(new T.Mesh(new T.SphereGeometry(20, 24, 12), new T.ShaderMaterial({ side: T.BackSide,
      vertexShader: 'varying vec3 vP; void main(){ vP = position; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }',
      fragmentShader: 'varying vec3 vP; void main(){ float h = normalize(vP).y; vec3 c = mix(vec3(.22,.2,.32), vec3(.6,.58,.68), smoothstep(-.4,.7,h)); gl_FragColor = vec4(c,1.); }' })));
    [[8, 6, 6, 8, 10, 1.1], [10, 4, -10, 3, 4, .45], [6, 10, -6, 4, -10, .8]].forEach(([w, h, x, y, z, k]) => {
      const m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ color: new T.Color(k, k, k), side: T.DoubleSide }));
      m.position.set(x, y, z); m.lookAt(0, 0, 0); env.add(m);
    });
    const pm = new T.PMREMGenerator(renderer); scene.environment = pm.fromScene(env, .04).texture;
    scene.add(new T.HemisphereLight(0xffffff, 0x2a2050, .6));
    const key = new T.DirectionalLight(0xfff1e2, 2.0); key.position.set(4, 8, 6); key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024); Object.assign(key.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: 1, far: 30 });
    key.shadow.bias = -.0004; key.shadow.normalBias = .02; scene.add(key);
    const rim = new T.DirectionalLight(new T.Color(accent).lerp(new T.Color(0xffffff), .3), 1.4); rim.position.set(-5, 4, -5); scene.add(rim);
    const fill = new T.DirectionalLight(0xffe8d8, .45); fill.position.set(-4, 1.5, 5); scene.add(fill);
    const stage = { renderer, scene, camera, pads: [] };
    stage.pad = (x, z, r, col) => {
      const g = new T.Group(); g.position.set(x, 0, z); scene.add(g);
      mesh(new T.CylinderGeometry(r, r * 1.02, .22, 72), P({ color: 0x2a2352, roughness: .35, clearcoat: .8, envMapIntensity: .8 }), g, [0, -.11, 0]);
      mesh(new T.CylinderGeometry(r * 1.08, r * 1.12, .18, 72), P({ color: 0x1c1738, roughness: .5, clearcoat: .5 }), g, [0, -.3, 0]);
      const ring = new T.Mesh(new T.TorusGeometry(r * 1.0, .03, 10, 120), new T.MeshBasicMaterial({ color: col, toneMapped: false }));
      ring.rotation.x = Math.PI / 2; ring.position.y = .005; g.add(ring);
      const grid = canvasTex(512, 512);
      grid.x.strokeStyle = 'rgba(255,255,255,.07)'; grid.x.lineWidth = 2;
      for (let i = 0; i <= 512; i += 32) { grid.x.beginPath(); grid.x.moveTo(i, 0); grid.x.lineTo(i, 512); grid.x.stroke(); grid.x.beginPath(); grid.x.moveTo(0, i); grid.x.lineTo(512, i); grid.x.stroke(); }
      const gm = new T.Mesh(new T.CircleGeometry(r * .97, 72), new T.MeshBasicMaterial({ map: grid.tex, transparent: true, depthWrite: false }));
      gm.rotation.x = -Math.PI / 2; gm.position.y = .003; g.add(gm);
      const halo = new T.Mesh(new T.CircleGeometry(r * 1.9, 48), new T.MeshBasicMaterial({ map: glowTex(new T.Color(col).getStyle().replace('rgb', 'rgba').replace(')', ',.45)')), transparent: true, depthWrite: false }));
      halo.rotation.x = -Math.PI / 2; halo.position.y = -.38; g.add(halo);
      g.userData.ring = ring; stage.pads.push(g);
      return g;
    };
    if (!opts || opts.pad !== false) stage.pad(0, 0, 3.3, accent);
    // light motes
    const moteTex = glowTex('rgba(255,255,255,1)');
    stage.motes = [];
    for (let i = 0; i < 10; i++) {
      const sp = new T.Sprite(new T.SpriteMaterial({ map: moteTex, color: i % 3 ? accent : 0xffb85c, transparent: true, opacity: .5, depthWrite: false }));
      sp.userData = { a: Math.random() * 6.28, r: 3 + Math.random() * 1.8, y: .4 + Math.random() * 4, sp: .05 + Math.random() * .08, ph: Math.random() * 6 };
      sp.scale.setScalar(.1 + Math.random() * .16); scene.add(sp); stage.motes.push(sp);
    }
    stage.frame = (pos, look) => { stage.camPos = new V3(...pos); stage.look = new V3(...look); };
    stage.layout = () => {
      const w = canvas.clientWidth || canvas.width, h = canvas.clientHeight || canvas.height;
      if (!w || !h) return;
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    };
    stage.tick = (t) => {
      stage.motes.forEach(m => { const u = m.userData; const a = u.a + t * u.sp;
        m.position.set(Math.cos(a) * u.r, u.y + Math.sin(t * .6 + u.ph) * .25, Math.sin(a) * u.r);
        m.material.opacity = .15 + .25 * (.5 + .5 * Math.sin(t * .9 + u.ph)); });
      const sway = Math.sin(t * .25) * .35;
      camera.position.set(stage.camPos.x + sway, stage.camPos.y, stage.camPos.z);
      camera.lookAt(stage.look);
      renderer.render(scene, camera);
    };
    return stage;
  }

  /* screen helper: a glowing panel with a live canvas texture */
  function screenMesh(w, h, px, glow) {
    const t = canvasTex(px, Math.round(px * h / w));
    const m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ map: t.tex, toneMapped: false, transparent: !!glow }));
    m.userData.ctx = t; return m;
  }
  function envelope(hot) {
    const t = canvasTex(256, 172);
    const x = t.x;
    const bg = x.createLinearGradient(0, 0, 0, 172); bg.addColorStop(0, hot ? '#FFF1DE' : '#FFFFFF'); bg.addColorStop(1, hot ? '#FFD2A0' : '#E8E3FF');
    x.fillStyle = bg; x.fillRect(0, 0, 256, 172);
    x.strokeStyle = hot ? '#E58A2E' : '#A99BF0'; x.lineWidth = 10; x.lineJoin = 'round';
    x.beginPath(); x.moveTo(14, 18); x.lineTo(128, 104); x.lineTo(242, 18); x.stroke();
    if (hot) { x.fillStyle = '#E5484D'; x.beginPath(); x.arc(220, 140, 22, 0, 6.3); x.fill(); x.fillStyle = '#fff'; x.font = `800 30px ${FONT}`; x.textAlign = 'center'; x.fillText('!', 220, 151); }
    const face = new T.MeshPhysicalMaterial({ map: t.tex, roughness: .5, clearcoat: .3 });
    const side = new T.MeshPhysicalMaterial({ color: hot ? 0xffd8a8 : 0xeee9ff, roughness: .6 });
    return mesh(new T.BoxGeometry(.56, .38, .03), [side, side, side, side, face, face]);
  }
  function tray(col, w, d) {
    const g = new T.Group();
    const mat = P({ color: col, roughness: .35, clearcoat: .7, envMapIntensity: .8 });
    mesh(new T.BoxGeometry(w, .06, d), mat, g, [0, .03, 0]);
    mesh(new T.BoxGeometry(w, .22, .05), mat, g, [0, .14, d / 2]);
    mesh(new T.BoxGeometry(w, .22, .05), mat, g, [0, .14, -d / 2]);
    mesh(new T.BoxGeometry(.05, .22, d), mat, g, [w / 2, .14, 0]);
    mesh(new T.BoxGeometry(.05, .22, d), mat, g, [-w / 2, .14, 0]);
    g.userData.stack = [];
    return g;
  }
  const ease = (u) => u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
  const bez = (a, b, c, u) => new V3().copy(a).multiplyScalar((1 - u) * (1 - u)).addScaledVector(b, 2 * (1 - u) * u).addScaledVector(c, u * u);

  /* ============================================================ scenes (driven by real `work` events) */
  // D = { phase: start|done|waiting|error|stopped|idle, label, error, data: {...facts from the real call} }
  const SCENES = {};
  const MOOD = { start: 'working', done: 'happy', waiting: 'thinking', error: 'thinking', stopped: 'idle', idle: 'idle' };
  function sayOf(D) {
    if (D.phase === 'error') return D.error || 'Yeh nahi ho paya';
    if (D.phase === 'stopped') return 'Theek hai, rok diya';
    if (D.phase === 'waiting') return 'Aapke tap ka intezaar';
    if (D.phase === 'done') return (D.data && D.data.note) || 'Ho gaya!';
    return D.label || 'Kaam kar raha hoon';
  }
  function clip(x, s, max) { s = String(s || ''); if (x.measureText(s).width <= max) return s; while (s.length > 1 && x.measureText(s + '\u2026').width > max) s = s.slice(0, -1); return s + '\u2026'; }
  const fresh = () => ({ phase: 'idle', label: '', error: '', data: {} });

  SCENES.email = function (st) {
    st.frame([3.2, 4.2, 9.6], [0, 1.25, 0]);
    const av = makeAvatar(); av.holder.position.x = -.7; av.holder.position.z = .9; av.yaw = .3; st.scene.add(av.holder);
    const inbox = tray(0x5b46c9, 1.1, .8); inbox.position.set(-2.4, 0, -.7); st.scene.add(inbox);
    for (let i = 0; i < 5; i++) { const e = envelope(false); e.rotation.x = -Math.PI / 2; e.position.set(0, .1 + i * .035, 0); e.scale.set(1.5, 1.5, 1); inbox.add(e); }
    const inLbl = label('Inbox', 'rgba(18,14,42,.92)', '#D7D2F2', .26); inLbl.position.set(-2.4, .85, -.7); st.scene.add(inLbl);
    const trays = [[0xff9a3c, 'Zaroori', '#1B1030', 2.1, 1.25], [0x7c5cff, 'Baad mein', '#FFFFFF', 2.55, -.05], [0x4b4668, 'Baaki', '#E6E3F5', 2.1, -1.35]].map(([c, n, fg, x, z]) => {
      const tr = tray(c, .9, .7); tr.position.set(x, 0, z); st.scene.add(tr);
      const l = label(n, new T.Color(c).getStyle(), fg, .24); l.position.set(x, .78, z); st.scene.add(l);
      tr.userData.lbl = l; tr.userData.name = n; tr.userData.fg = fg; tr.userData.col = c; return tr;
    });
    const panel = new T.Group(); panel.position.set(.4, 2.45, -1.3); panel.rotation.y = -.15; st.scene.add(panel);
    mesh(rbox(2.6, 1.7, .08, .12), P({ color: 0x1a1640, roughness: .2, clearcoat: 1, transparent: true, opacity: .55 }), panel);
    const scr = screenMesh(2.46, 1.56, 640, true); scr.position.z = .05; panel.add(scr);
    const glow = new T.PointLight(0x9b7dff, 1.2, 5, 2); glow.position.set(0, 0, .8); panel.add(glow);
    const envs = [0, 1, 2].map(i => { const e = envelope(i === 0); st.scene.add(e); e.userData.i = i; return e; });
    const A = new V3(-2.4, .55, -.7), B = new V3(.1, 2.2, -.5);
    let D = fresh(), last = -1, flown = 0;
    function drawScreen(t) {
      const { x, c, tex } = scr.userData.ctx; const W = c.width, H = c.height; const d = D.data || {};
      x.clearRect(0, 0, W, H);
      const g = x.createLinearGradient(0, 0, 0, H); g.addColorStop(0, 'rgba(124,92,255,.55)'); g.addColorStop(1, 'rgba(45,212,191,.25)');
      rr(x, 0, 0, W, H, 28); x.fillStyle = g; x.fill();
      x.fillStyle = '#F4F2FF'; x.font = `700 28px ${DISPLAY}`; x.fillText(clip(x, d.account || 'Inbox', W - 220), 28, 52);
      x.font = `700 22px ${FONT}`; x.fillStyle = '#E6E1FF'; x.textAlign = 'right';
      x.fillText(d.total != null ? `${d.total} mail` : (D.phase === 'start' ? 'padh raha\u2026' : ''), W - 28, 50); x.textAlign = 'left';
      const rows = d.rows || [];
      const cur = Math.floor(t * 1.4) % Math.max(1, rows.length || 5);
      for (let i = 0; i < 5; i++) {
        const y = 80 + i * 66; const m = rows[i];
        rr(x, 20, y, W - 40, 56, 14);
        x.fillStyle = i === cur && D.phase === 'start' ? 'rgba(255,177,92,.35)' : 'rgba(255,255,255,.1)'; x.fill();
        if (m) {
          x.fillStyle = m.hot ? '#FFC27A' : '#C9C4E8'; x.beginPath(); x.arc(46, y + 28, 9, 0, 6.3); x.fill();
          x.fillStyle = '#FFFFFF'; x.font = `800 21px ${FONT}`; x.fillText(clip(x, m.from, W - 120), 68, y + 24);
          x.fillStyle = '#E2DEFA'; x.font = `600 18px ${FONT}`; x.fillText(clip(x, m.subject, W - 120), 68, y + 46);
        } else {
          x.fillStyle = 'rgba(255,255,255,.18)'; rr(x, 68, y + 14, 180 + (i * 37) % 120, 12, 6); x.fill();
          rr(x, 68, y + 34, 260 + (i * 53) % 140, 10, 5); x.fill();
        }
      }
      if (D.phase === 'start') {
        const sy = 70 + ((t * 120) % (H - 70));
        const sg = x.createLinearGradient(0, sy - 20, 0, sy + 20); sg.addColorStop(0, 'rgba(255,213,160,0)'); sg.addColorStop(.5, 'rgba(255,213,160,.55)'); sg.addColorStop(1, 'rgba(255,213,160,0)');
        x.fillStyle = sg; x.fillRect(10, sy - 20, W - 20, 40);
      }
      tex.needsUpdate = true;
    }
    function drop(tr) {
      if (tr.children.length > 12) return;
      const e = envelope(tr.userData.name === 'Zaroori'); e.rotation.x = -Math.PI / 2; e.scale.set(1.3, 1.3, 1);
      const n = tr.children.length - 5;
      e.position.set((Math.random() - .5) * .1, .1 + n * .035, (Math.random() - .5) * .1); e.rotation.z = (Math.random() - .5) * .4; tr.add(e);
    }
    return {
      set(d) { D = d; const g = (d.data && d.data.groups) || null;
        if (g) { const ks = Object.keys(g); trays.forEach((tr, i) => { if (ks[i]) tr.userData.lbl.userData.draw(`${ks[i]} \u00b7 ${g[ks[i]]}`, new T.Color(tr.userData.col).getStyle(), tr.userData.fg); }); }
        inLbl.userData.draw(d.data && d.data.total != null ? `Inbox \u00b7 ${d.data.total}` : 'Inbox', 'rgba(18,14,42,.92)', '#D7D2F2');
        av.mood = MOOD[d.phase] || 'idle'; av.say(sayOf(d)); },
      update(t, dt) {
        av.update(t, dt);
        if (Math.floor(t * 15) !== last) { last = Math.floor(t * 15); drawScreen(t); }
        const active = D.phase === 'start';
        envs.forEach((e) => {
          const per = 3.6, tt = t + e.userData.i * 1.2, ph = (tt % per) / per, cyc = Math.floor(tt / per);
          const dest = trays[(cyc + e.userData.i) % 3];
          const C = new V3(dest.position.x, .45, dest.position.z);
          e.visible = active;
          if (!active) return;
          if (ph > .97 && e.userData.cyc !== cyc) { e.userData.cyc = cyc; drop(dest); flown++; }
          let p;
          if (ph < .42) p = bez(A, new V3(-1.6, 2.6, -.9), B, ease(ph / .42));
          else if (ph < .58) p = B.clone().add(new V3(0, Math.sin(t * 6) * .03, 0));
          else p = bez(B, new V3(1.6, 2.4, (B.z + C.z) / 2), C, ease((ph - .58) / .42));
          e.position.copy(p);
          e.rotation.set(ph < .42 || ph > .58 ? Math.sin(ph * 12) * .3 : 0, ph * 6.28, 0);
          const sc = ph > .42 && ph < .58 ? 1.25 : 1; e.scale.set(sc, sc, sc);
        });
      },
      redraw() { av.redraw(); }
    };
  };

  SCENES.browser = function (st) {
    st.frame([2.6, 4.0, 10.2], [0, 1.5, 0]);
    const av = makeAvatar(); av.holder.position.set(-1.75, av.holder.position.y, 1.0); av.yaw = .55; st.scene.add(av.holder);
    const panel = new T.Group(); panel.position.set(.75, 2.15, -.9); panel.rotation.y = -.28; st.scene.add(panel);
    mesh(rbox(3.6, 2.45, .14, .14), P({ color: 0x1c1840, roughness: .25, clearcoat: 1, metalness: .2 }), panel);
    const scr = screenMesh(3.42, 2.27, 760, false); scr.position.z = .075; panel.add(scr);
    const glow = new T.PointLight(0x2dd4bf, 1.4, 6, 2); glow.position.set(0, 0, 1.2); panel.add(glow);
    mesh(new T.CylinderGeometry(.06, .06, 1.0, 16), P({ color: 0x3a3470, roughness: .3, metalness: .5 }), panel, [0, -1.65, -.05]);
    const lens = new T.Group(); panel.add(lens);
    const gold = P({ color: 0xffb15c, roughness: .25, metalness: .8, clearcoat: 1 });
    mesh(new T.TorusGeometry(.3, .05, 16, 48), gold, lens);
    lens.add(new T.Mesh(new T.CircleGeometry(.29, 40), P({ color: 0xffffff, transmission: .9, roughness: .05, thickness: .2, transparent: true, opacity: .35 })));
    const handle = mesh(new T.CylinderGeometry(.05, .06, .55, 16), gold, lens, [.32, -.32, 0]); handle.rotation.z = Math.PI / 4;
    const cards = [0, 1, 2].map(i => { const c = new T.Group(); st.scene.add(c);
      mesh(rbox(.8, .55, .04, .06), P({ color: [0x2dd4bf, 0x7c5cff, 0xffb15c][i], roughness: .3, clearcoat: 1, transparent: true, opacity: .75 }), c);
      c.userData.i = i; return c; });
    let D = fresh(), last = -1, t0 = 0;
    function draw(t) {
      const { x, c, tex } = scr.userData.ctx; const W = c.width, H = c.height; const d = D.data || {};
      x.fillStyle = '#F7F5FF'; x.fillRect(0, 0, W, H);
      x.fillStyle = '#E6E1FA'; x.fillRect(0, 0, W, 54);
      ['#F87171', '#FBBF24', '#34D399'].forEach((col, i) => { x.fillStyle = col; x.beginPath(); x.arc(28 + i * 26, 27, 8, 0, 6.3); x.fill(); });
      rr(x, 110, 12, W - 140, 30, 15); x.fillStyle = '#FFFFFF'; x.fill();
      x.fillStyle = '#0F766E'; x.font = `700 17px ${FONT}`; x.fillText(clip(x, 'https://' + (d.url || '\u2026'), W - 170), 126, 33);
      x.fillStyle = '#1B1030'; x.font = `700 30px ${DISPLAY}`; x.fillText(clip(x, d.url ? d.url.replace(/^www\./, '') : 'Website', W - 70), 34, 104);
      x.fillStyle = '#5B5580'; x.font = `600 17px ${FONT}`; x.fillText('Hoola Browser \u00b7 login/OTP kabhi nahi', 34, 130);
      rr(x, 34, 152, W - 68, 50, 10); x.fillStyle = '#FFFFFF'; x.fill(); x.strokeStyle = D.phase === 'start' ? '#2DD4BF' : '#CFC9EA'; x.lineWidth = 3; x.stroke();
      const goal = d.goal || D.label || '';
      const n = D.phase === 'start' ? Math.min(goal.length, Math.floor((t - t0) * 14)) : goal.length;
      x.fillStyle = '#1B1030'; x.font = `800 21px ${FONT}`; x.fillText(clip(x, goal.slice(0, n) + (D.phase === 'start' && Math.floor(t * 3) % 2 ? '|' : ''), W - 110), 50, 185);
      rr(x, 34, 226, W - 68, 120, 14);
      if (D.phase === 'done' && (d.result || d.note)) {
        x.fillStyle = 'rgba(52,211,153,.16)'; x.fill(); x.strokeStyle = '#10B981'; x.lineWidth = 3; x.stroke();
        x.fillStyle = '#065F46'; x.font = `800 24px ${DISPLAY}`;
        const words = String(d.result || d.note).split(' '); let line = '', y = 268;
        for (const w of words) { if (x.measureText(line + w).width > W - 130 && line) { x.fillText(line, 56, y); line = ''; y += 34; if (y > 330) break; } line += w + ' '; }
        if (y <= 330) x.fillText(line, 56, y);
      } else if (D.phase === 'error') {
        x.fillStyle = 'rgba(248,113,113,.14)'; x.fill(); x.strokeStyle = '#EF4444'; x.lineWidth = 3; x.stroke();
        x.fillStyle = '#991B1B'; x.font = `800 22px ${FONT}`; x.fillText(clip(x, D.error || 'Site nahi khuli', W - 130), 56, 292);
      } else { x.setLineDash([10, 8]); x.strokeStyle = '#CFC9EA'; x.lineWidth = 3; x.stroke(); x.setLineDash([]);
        x.fillStyle = '#9C96C2'; x.font = `700 20px ${FONT}`; x.fillText(D.phase === 'waiting' ? 'Submit se pehle aapse pooch raha hoon' : 'Jawab yahan aayega', 56, 292); }
      for (let i = 0; i < 4; i++) { rr(x, 34 + i * 176, 368, 160, 92, 10); x.fillStyle = '#EEEAFB'; x.fill(); }
      tex.needsUpdate = true;
    }
    let clk = 0;
    return {
      set(d) { if (d.phase === 'start' && D.phase !== 'start') t0 = clk; D = d; av.mood = d.phase === 'start' ? 'look' : (MOOD[d.phase] || 'idle'); av.say(sayOf(d)); },
      update(t, dt) {
        clk = t; av.update(t, dt);
        if (Math.floor(t * 12) !== last) { last = Math.floor(t * 12); draw(t); }
        const target = D.phase === 'done' ? [-.2, -.25] : [Math.sin(t * .9) * 1.1, .3 + Math.cos(t * 1.3) * .4];
        lens.position.lerp(new V3(target[0] + Math.sin(t * 2) * .06, target[1] + Math.cos(t * 2.4) * .05, .32), .06);
        cards.forEach(c => { const a = t * .4 + c.userData.i * 2.1; c.position.set(-1.4 + Math.cos(a) * .5, 2.8 + c.userData.i * .45 + Math.sin(t + c.userData.i) * .12, -1.9 + Math.sin(a) * .3); c.rotation.y = .4 + Math.sin(a) * .2; });
      },
      redraw() { av.redraw(); }
    };
  };

  SCENES.payment = function (st) {
    st.frame([2.6, 4.0, 9.4], [0, 1.4, 0]);
    const av = makeAvatar(); av.holder.position.set(-.9, av.holder.position.y, 1.0); av.yaw = .35; st.scene.add(av.holder);
    const bill = new T.Group(); bill.position.set(-2.2, 1.7, -.6); st.scene.add(bill);
    const bs = screenMesh(1.15, 1.5, 360, false); bill.add(bs);
    mesh(new T.BoxGeometry(1.17, 1.52, .015), P({ color: 0xffffff, roughness: .7 }), bill, [0, 0, -.012]);
    const ped = new T.Group(); ped.position.set(1.5, 0, .1); st.scene.add(ped);
    mesh(new T.CylinderGeometry(.75, .85, .9, 48), P({ color: 0x3a2f6e, roughness: .3, clearcoat: 1 }), ped, [0, .45, 0]);
    mesh(new T.CylinderGeometry(.82, .82, .06, 48), P({ color: 0xffb15c, roughness: .25, metalness: .7 }), ped, [0, .93, 0]);
    const rings = [0, 1, 2].map(() => { const r = new T.Mesh(new T.TorusGeometry(.9, .025, 8, 80), new T.MeshBasicMaterial({ color: 0xffb15c, transparent: true, toneMapped: false })); r.rotation.x = Math.PI / 2; ped.add(r); return r; });
    const card = new T.Group(); card.position.set(0, 1.8, 0); ped.add(card);
    const cs = canvasTex(512, 320);
    const cardMat = new T.MeshPhysicalMaterial({ map: cs.tex, roughness: .25, clearcoat: 1, emissive: 0x000000 });
    const cardEdge = P({ color: 0xff9a3c, roughness: .3, metalness: .4 });
    mesh(new T.BoxGeometry(1.5, .94, .05), [cardEdge, cardEdge, cardEdge, cardEdge, cardMat, cardEdge], card);
    const lock = new T.Group(); lock.position.set(.62, .5, .12); card.add(lock);
    mesh(rbox(.42, .34, .16, .06), P({ color: 0xffc27a, roughness: .2, metalness: .9, clearcoat: 1 }), lock);
    const shackle = new T.Group(); shackle.position.set(0, .17, 0); lock.add(shackle);
    mesh(new T.TorusGeometry(.13, .04, 12, 32, Math.PI), P({ color: 0xd8d4e8, roughness: .2, metalness: 1 }), shackle, [0, .02, 0]);
    const cardLight = new T.PointLight(0xffa04c, 1.6, 4, 2); cardLight.position.set(0, 2.2, .8); ped.add(cardLight);
    let D = fresh();
    function paint() {
      const d = D.data || {};
      { const { x, c, tex } = bs.userData.ctx; const W = c.width, H = c.height;
        x.fillStyle = '#FFFFFF'; x.fillRect(0, 0, W, H); x.fillStyle = '#4A31BE'; x.fillRect(0, 0, W, 64);
        x.fillStyle = '#FFFFFF'; x.font = `800 28px ${DISPLAY}`; x.fillText(clip(x, d.biller || 'Bill', W - 40), 22, 44);
        x.fillStyle = '#5B5580'; x.font = `700 18px ${FONT}`; if (d.ref) x.fillText(clip(x, 'Consumer ' + d.ref, W - 40), 22, 104);
        [140, 166, 192, 218].forEach((y, i) => { x.fillStyle = '#E6E1FA'; x.fillRect(22, y, [280, 220, 250, 190][i], 12); });
        x.fillStyle = '#1B1030'; x.font = `800 48px ${DISPLAY}`; x.fillText(clip(x, d.amount || '\u20b9 \u2026', W - 40), 22, 312);
        if (d.due) { x.fillStyle = '#B45309'; x.font = `800 20px ${FONT}`; x.fillText(clip(x, 'Due ' + d.due, W - 40), 22, 348); }
        tex.needsUpdate = true; }
      { const x = cs.x; const g = x.createLinearGradient(0, 0, 512, 320); g.addColorStop(0, '#FFD9A8'); g.addColorStop(.55, '#FF9A3C'); g.addColorStop(1, '#C055F5');
        x.fillStyle = g; x.fillRect(0, 0, 512, 320); x.fillStyle = 'rgba(27,16,48,.85)'; x.font = `800 34px ${FONT}`; x.fillText('UPI', 34, 66);
        x.font = `700 22px ${FONT}`; x.fillText(clip(x, d.biller || '', 440), 34, 104); x.font = `800 70px ${DISPLAY}`; x.fillText(clip(x, d.amount || '', 440), 34, 270); cs.tex.needsUpdate = true; }
    }
    paint();
    return {
      set(d) { D = d; paint(); av.mood = MOOD[d.phase] || 'idle'; av.say(sayOf(d)); },
      update(t, dt) {
        av.update(t, dt);
        bill.position.y = 1.7 + Math.sin(t * 1.2) * .08; bill.rotation.y = .5 + Math.sin(t * .7) * .12;
        card.rotation.y = Math.sin(t * .8) * .35; card.position.y = 1.8 + Math.sin(t * 1.4) * .07;
        const ok = D.phase === 'done' && /pay|send_money|order|checkout/.test((D.data && D.data.action) || ''), bad = D.phase === 'error' || D.phase === 'stopped';
        shackle.position.y += ((ok ? .32 : .17) - shackle.position.y) * .08;
        shackle.rotation.y += ((ok ? 1.2 : 0) - shackle.rotation.y) * .08;
        cardMat.emissive.lerp(new T.Color(ok ? 0x0b5d3b : 0x000000), .05);
        cardLight.color.lerp(new T.Color(ok ? 0x34d399 : bad ? 0x6b6890 : 0xffa04c), .05);
        rings.forEach((r, i) => { const u = ((t * .55) + i / 3) % 1; r.scale.setScalar(.7 + u * 1.1); r.position.y = .95 + u * .02;
          r.material.opacity = (bad ? .12 : .9) * (1 - u); r.material.color.set(ok ? 0x34d399 : 0xffb15c); });
      },
      redraw() { av.redraw(); paint(); }
    };
  };

  SCENES.bluetooth = function (st) {
    st.frame([2.4, 4.2, 10.2], [0, 1.45, 0]);
    const av = makeAvatar(); av.holder.position.set(-1.5, av.holder.position.y, 1.1); av.yaw = .55; st.scene.add(av.holder);
    const cab = new T.Group(); cab.position.set(1.1, 0, -1.2); cab.rotation.y = -.35; st.scene.add(cab);
    mesh(rbox(2.8, .55, .7, .06), P({ color: 0x3b3170, roughness: .45, clearcoat: .6 }), cab, [0, .28, 0], null, [Math.PI / 2, 0, 0]);
    mesh(new T.BoxGeometry(.9, .06, .35), P({ color: 0x1c1738, metalness: .6, roughness: .3 }), cab, [0, .6, 0]);
    mesh(new T.CylinderGeometry(.06, .08, .35, 16), P({ color: 0x1c1738, metalness: .6, roughness: .3 }), cab, [0, .78, 0]);
    const tv = new T.Group(); tv.position.set(0, 1.9, 0); cab.add(tv);
    mesh(rbox(3.1, 1.8, .1, .05), P({ color: 0x0b0a12, roughness: .2, metalness: .5, clearcoat: 1 }), tv);
    const scr = screenMesh(2.98, 1.68, 720, false); scr.position.z = .055; tv.add(scr);
    const tvGlow = new T.PointLight(0x93c5fd, 1.2, 6, 2); tvGlow.position.set(0, 0, 1); tv.add(tvGlow);
    const waves = [0, 1, 2, 3].map(i => { const w = new T.Mesh(new T.TorusGeometry(.22, .025, 8, 48), new T.MeshBasicMaterial({ color: 0x93c5fd, transparent: true, toneMapped: false })); st.scene.add(w); w.userData.i = i; return w; });
    let D = fresh(), last = -1;
    function draw(t) {
      const { x, c, tex } = scr.userData.ctx; const W = c.width, H = c.height; const d = D.data || {};
      const g = x.createLinearGradient(0, 0, W, H); g.addColorStop(0, '#1E1B4B'); g.addColorStop(.5, '#312E81'); g.addColorStop(1, '#0F766E');
      x.fillStyle = g; x.fillRect(0, 0, W, H);
      for (let i = 0; i < 5; i++) { x.fillStyle = `rgba(255,255,255,${.05 + i * .02})`; x.beginPath(); x.arc(W * (.2 + i * .15) + Math.sin(t + i) * 20, H * .55 + Math.cos(t * .8 + i) * 18, 50 + i * 12, 0, 6.3); x.fill(); }
      x.fillStyle = 'rgba(255,255,255,.88)'; x.font = `800 24px ${FONT}`;
      x.fillText(clip(x, d.device || ({ tv: 'TV', speaker: 'Speaker', ac: 'AC' }[d.kind] || 'Bluetooth'), W - 60), 28, 46);
      const act = String(d.action || '');
      const vol = /VOL_UP|VOL_DOWN|volume/i.test(act);
      if (vol && D.phase !== 'idle') {
        const n = d.repeat || 1, up = !/DOWN|down/.test(act);
        const prog = D.phase === 'start' ? (t * 2.5) % (n + 1) : n;
        rr(x, W - 110, 40, 60, H - 80, 30); x.fillStyle = 'rgba(0,0,0,.45)'; x.fill();
        const lvl = Math.max(.08, Math.min(1, .45 + (up ? 1 : -1) * prog * .05));
        const hh = (H - 100) * lvl;
        rr(x, W - 100, H - 50 - hh, 40, hh, 20); x.fillStyle = '#93C5FD'; x.fill();
        x.fillStyle = '#FFFFFF'; x.font = `800 26px ${FONT}`; x.fillText(`${up ? 'VOL +' : 'VOL \u2212'} ${Math.floor(prog)}/${n}`, W - 330, H / 2);
      } else if (act) {
        x.fillStyle = '#FFFFFF'; x.font = `800 34px ${DISPLAY}`; x.fillText(clip(x, act.replace(/_/g, ' '), W - 60), 28, H / 2 + 10);
      }
      if (d.found && d.found.length) { x.font = `700 20px ${FONT}`; x.fillStyle = '#BFDBFE'; d.found.slice(0, 4).forEach((f, i) => x.fillText('\u2022 ' + clip(x, f, W - 80), 28, 90 + i * 30)); }
      x.font = `800 24px ${FONT}`;
      if (D.phase === 'start') { x.fillStyle = 'rgba(255,255,255,.9)'; x.fillText('Hoola Remote se bhej raha hoon\u2026', 28, H - 34); }
      if (D.phase === 'done') { x.fillStyle = '#A7F3D0'; x.fillText('\u2713 Device ne kar diya', 28, H - 34); }
      if (D.phase === 'error') { x.fillStyle = '#FCA5A5'; x.fillText(clip(x, D.error || 'Device se nahi juda', W - 60), 28, H - 34); }
      tex.needsUpdate = true;
    }
    const tmp = new V3(), tvPos = new V3();
    return {
      set(d) { D = d; av.mood = MOOD[d.phase] || 'idle'; av.say(sayOf(d)); },
      update(t, dt) {
        av.update(t, dt);
        if (Math.floor(t * 12) !== last) { last = Math.floor(t * 12); draw(t); }
        av.phone.getWorldPosition(tmp); tv.getWorldPosition(tvPos);
        waves.forEach(w => { const u = ((t * .8) + w.userData.i / 4) % 1;
          w.visible = D.phase === 'start'; w.position.lerpVectors(tmp, tvPos, u); w.lookAt(tvPos);
          w.scale.setScalar(.6 + u * 2.2); w.material.opacity = .9 * (1 - u); });
      },
      redraw() { av.redraw(); }
    };
  };

  SCENES.network = function (st) {
    st.frame([0, 4.8, 12.8], [0, 1.3, 0]);
    st.pad(-2.3, .9, 1.6, 0x7c5cff); st.pad(2.3, -.9, 1.6, 0x2dd4bf);
    const me = makeAvatar(); me.holder.position.set(-2.3, me.holder.position.y, .9); me.yaw = .75; st.scene.add(me.holder);
    const peer = makeAvatar({ hoodie: 0x14b8a6, rib: 0x0f9488, strap: 0x7c2d12, skin: 0xb97a4e, pants: 0x3f3f46, lace: 0x14b8a6 });
    peer.holder.position.set(2.3, peer.holder.position.y, -.9); peer.yaw = -.75; st.scene.add(peer.holder);
    const n1 = label('Aapka Hoola', '#7C5CFF', '#FFFFFF', .24); n1.position.set(-2.3, .3, 2.6); st.scene.add(n1);
    const n2 = label('Doosra Hoola', '#14B8A6', '#04201D', .24); n2.position.set(2.3, .3, .8); st.scene.add(n2);
    const curve = new T.QuadraticBezierCurve3(new V3(-2.0, 1.7, .8), new V3(0, 3.2, 0), new V3(2.0, 1.7, -.8));
    const dots = []; const dotMat = new T.SpriteMaterial({ map: glowTex('rgba(196,181,253,1)'), transparent: true, depthWrite: false, toneMapped: false });
    for (let i = 0; i < 22; i++) { const s = new T.Sprite(dotMat.clone()); s.position.copy(curve.getPoint(i / 21)); s.scale.setScalar(.16); st.scene.add(s); dots.push(s); }
    const shield = new T.Group(); shield.position.copy(curve.getPoint(.5)).add(new V3(0, .2, .3)); st.scene.add(shield);
    const sh = new T.Shape(); sh.moveTo(0, .5); sh.quadraticCurveTo(.38, .42, .4, .32); sh.lineTo(.36, -.05); sh.quadraticCurveTo(.3, -.38, 0, -.52); sh.quadraticCurveTo(-.3, -.38, -.36, -.05); sh.lineTo(-.4, .32); sh.quadraticCurveTo(-.38, .42, 0, .5);
    const sg = new T.ExtrudeGeometry(sh, { depth: .08, bevelEnabled: true, bevelThickness: .03, bevelSize: .03, bevelSegments: 3 }); sg.center();
    mesh(sg, P({ color: 0x34d399, roughness: .15, clearcoat: 1, transmission: .4, transparent: true, opacity: .85, emissive: 0x0b5d3b, emissiveIntensity: .6 }), shield);
    shield.add(new T.Mesh(new T.TubeGeometry(new T.CatmullRomCurve3([new V3(-.16, 0, .09), new V3(-.04, -.12, .09), new V3(.18, .14, .09)]), 20, .035, 8), new T.MeshBasicMaterial({ color: 0xffffff })));
    const sl = label('PIN / OTP kabhi nahi jaata', 'rgba(18,14,42,.92)', '#A7F3D0', .2); sl.position.set(0, -.75, 0); shield.add(sl);
    const letter = envelope(false); st.scene.add(letter);
    let D = fresh();
    return {
      set(d) { D = d; const p = (d.data && d.data.peer) || '';
        if (p) { n2.userData.text = [p.slice(0, 28), '#14B8A6', '#04201D']; n2.userData.draw(...n2.userData.text); }
        me.say(sayOf(d)); peer.say(d.phase === 'done' ? 'Mil gaya \u2713' : '');
        me.mood = MOOD[d.phase] || 'idle'; peer.mood = d.phase === 'done' ? 'happy' : 'idle'; me.talking = d.phase === 'start'; },
      update(t, dt) {
        me.update(t, dt); peer.update(t, dt);
        const per = 3.4, ph = (t % per) / per;
        const moving = D.phase === 'start';
        const u = moving ? (ph < .5 ? ease(ph * 2) : ease(1 - (ph - .5) * 2)) : (D.phase === 'done' ? 1 : 0);
        letter.visible = D.phase !== 'idle';
        letter.position.copy(curve.getPoint(u)).add(new V3(0, .15, 0)); letter.rotation.set(Math.sin(t * 3) * .2, t * 2, 0);
        dots.forEach((s, i) => { const k = Math.abs(i / 21 - u); s.material.opacity = .25 + Math.max(0, .75 - k * 4); s.scale.setScalar(.12 + Math.max(0, .14 - k * .6)); });
        shield.rotation.y = Math.sin(t * .9) * .5; shield.position.y = curve.getPoint(.5).y + .2 + Math.sin(t * 1.5) * .06;
      },
      redraw() { me.redraw(); peer.redraw(); n1.userData.draw(...n1.userData.text); n2.userData.draw(...n2.userData.text); sl.userData.draw(...sl.userData.text); }
    };
  };

  SCENES.pc = function (st) {
    st.frame([2.8, 4.2, 10.4], [.1, 1.45, 0]);
    const av = makeAvatar(); av.holder.position.set(-1.7, av.holder.position.y, 1.0); av.yaw = .75; st.scene.add(av.holder);
    const desk = new T.Group(); desk.position.set(.9, 0, -.6); desk.rotation.y = -.3; st.scene.add(desk);
    mesh(rbox(3.6, 1.6, .1, .06), P({ color: 0x4a3f86, roughness: .45, clearcoat: .5 }), desk, [0, 1.1, 0], null, [Math.PI / 2, 0, 0]);
    [[-1.65, -.65], [1.65, -.65], [-1.65, .65], [1.65, .65]].forEach(([x, z]) => mesh(new T.CylinderGeometry(.05, .05, 1.1, 12), P({ color: 0x1c1738, metalness: .7, roughness: .3 }), desk, [x, .55, z]));
    const kb = new T.Group(); kb.position.set(0, 1.18, .45); desk.add(kb);
    mesh(rbox(1.5, .5, .06, .04), P({ color: 0x2b2558, roughness: .4 }), kb, [0, 0, 0], null, [Math.PI / 2, 0, 0]);
    const keyMat = P({ color: 0xd7d2f2, roughness: .5 }); const keys = [];
    for (let r = 0; r < 4; r++) for (let c = 0; c < 12; c++) keys.push(mesh(new T.BoxGeometry(.09, .03, .08), keyMat, kb, [-.6 + c * .109, .045, -.17 + r * .11]));
    const mon = new T.Group(); mon.position.set(0, 2.25, -.4); desk.add(mon);
    mesh(rbox(2.7, 1.65, .09, .05), P({ color: 0x15122c, roughness: .2, metalness: .5, clearcoat: 1 }), mon);
    mesh(new T.CylinderGeometry(.06, .06, .5, 16), P({ color: 0x15122c, metalness: .6 }), mon, [0, -1.05, -.05]);
    mesh(new T.CylinderGeometry(.35, .38, .04, 32), P({ color: 0x15122c, metalness: .6 }), mon, [0, -1.12, -.05]);
    const scr = screenMesh(2.58, 1.53, 720, false); scr.position.z = .05; mon.add(scr);
    const mg = new T.PointLight(0xe879f9, 1.0, 5, 2); mg.position.set(0, 0, 1); mon.add(mg);
    let D = fresh(), last = -1;
    function draw(t) {
      const { x, c, tex } = scr.userData.ctx; const W = c.width, H = c.height; const d = D.data || {};
      x.fillStyle = '#FFFDF5'; x.fillRect(0, 0, W, H);
      x.fillStyle = '#B91C1C'; x.fillRect(0, 0, W, 40); x.fillStyle = '#FFFFFF'; x.font = `800 19px ${FONT}`; x.fillText('Hoola PC chala raha hai \u00b7 rokne ke liye STOP dabaiye', 18, 27);
      x.fillStyle = '#1E3A8A'; x.fillRect(0, 40, W, 44); x.fillStyle = '#FFFFFF'; x.font = `800 21px ${FONT}`; x.fillText(clip(x, d.app || (d.tally ? 'Tally' : 'Mera PC'), W - 40), 18, 70);
      const fields = d.fields && d.fields.length ? d.fields : null;
      if (fields) {
        fields.slice(0, 5).forEach((f, i) => { const y = 104 + i * 56;
          x.fillStyle = '#334155'; x.font = `700 19px ${FONT}`; x.fillText(clip(x, f[0], 200), 30, y + 26);
          rr(x, 240, y, W - 280, 40, 6); x.fillStyle = '#F1F5F9'; x.fill(); x.strokeStyle = '#CBD5E1'; x.lineWidth = 2; x.stroke();
          x.fillStyle = '#0F172A'; x.font = `800 20px ${FONT}`; x.fillText(clip(x, f[1], W - 300), 254, y + 27); });
      } else {
        const goal = d.goal || D.label || '';
        x.fillStyle = '#0F172A'; x.font = `800 22px ${FONT}`;
        const words = goal.split(' '); let line = '', y = 130;
        for (const w of words) { if (x.measureText(line + w).width > W - 80 && line) { x.fillText(line, 30, y); line = ''; y += 34; if (y > 260) break; } line += w + ' '; }
        if (y <= 260) x.fillText(line, 30, y);
        for (let i = 0; i < 3; i++) { rr(x, 30, 290 + i * 40, W - 60 - i * 80, 26, 6); x.fillStyle = '#E2E8F0'; x.fill(); }
      }
      if (D.phase === 'waiting') { rr(x, W - 290, H - 62, 260, 44, 22); x.fillStyle = '#F59E0B'; x.fill(); x.fillStyle = '#1B1030'; x.font = `800 19px ${FONT}`; x.fillText('Aapse pooch raha hoon\u2026', W - 272, H - 33); }
      if (D.phase === 'done') { x.fillStyle = '#047857'; x.font = `800 22px ${FONT}`; x.fillText('\u2713 Ho gaya', 30, H - 26); }
      if (D.phase === 'error') { x.fillStyle = '#B91C1C'; x.font = `800 20px ${FONT}`; x.fillText(clip(x, D.error || 'Nahi ho paya', W - 60), 30, H - 26); }
      const cx = 250 + ((t * 120) % 300), cy = 120 + ((t * 37) % 220);
      if (D.phase === 'start') { x.fillStyle = '#FFFFFF'; x.strokeStyle = '#111827'; x.lineWidth = 2; x.beginPath(); x.moveTo(cx, cy); x.lineTo(cx, cy + 26); x.lineTo(cx + 7, cy + 19); x.lineTo(cx + 14, cy + 30); x.lineTo(cx + 18, cy + 28); x.lineTo(cx + 11, cy + 17); x.lineTo(cx + 20, cy + 17); x.closePath(); x.fill(); x.stroke(); }
      tex.needsUpdate = true;
    }
    return {
      set(d) { D = d; av.mood = MOOD[d.phase] || 'idle'; av.say(sayOf(d)); },
      update(t, dt) {
        av.update(t, dt);
        if (Math.floor(t * 12) !== last) { last = Math.floor(t * 12); draw(t); }
        const typing = D.phase === 'start';
        keys.forEach((k, i) => { k.position.y = .045 - (typing && Math.sin(t * 17 + i * 2.3) > .85 ? .018 : 0); });
      },
      redraw() { av.redraw(); }
    };
  };

  /* anything else (reminders, calendar, sheets, maps, artifacts...): Hoola at a holographic desk with the task */
  SCENES.work = function (st) {
    st.frame([2.4, 4.0, 9.6], [0, 1.4, 0]);
    const av = makeAvatar(); av.holder.position.set(-.9, av.holder.position.y, .9); av.yaw = .35; st.scene.add(av.holder);
    const panel = new T.Group(); panel.position.set(1.0, 2.3, -1.0); panel.rotation.y = -.3; st.scene.add(panel);
    mesh(rbox(2.7, 1.6, .08, .12), P({ color: 0x1a1640, roughness: .2, clearcoat: 1, transparent: true, opacity: .55 }), panel);
    const scr = screenMesh(2.56, 1.46, 640, true); scr.position.z = .05; panel.add(scr);
    { const wl = new T.PointLight(0xffb15c, 1.1, 5, 2); wl.position.set(0, 0, .8); panel.add(wl); }
    const orbit = new T.Group(); orbit.position.set(-.9, 1.6, .9); st.scene.add(orbit);
    const cubes = [0, 1, 2, 3, 4].map(i => mesh(rbox(.26, .26, .26, .06), P({ color: [0xffb15c, 0x7c5cff, 0x2dd4bf, 0xc055f5, 0x60a5fa][i], roughness: .3, clearcoat: 1 }), orbit));
    const gear = mesh(new T.TorusGeometry(.55, .06, 12, 64), P({ color: 0xffb15c, roughness: .25, metalness: .8 }), st.scene, [1.0, .5, .6], null, [Math.PI / 2, 0, 0]);
    let D = fresh(), last = -1;
    function draw(t) {
      const { x, c, tex } = scr.userData.ctx; const W = c.width, H = c.height;
      x.clearRect(0, 0, W, H);
      const g = x.createLinearGradient(0, 0, 0, H); g.addColorStop(0, 'rgba(255,177,92,.45)'); g.addColorStop(1, 'rgba(124,92,255,.35)');
      rr(x, 0, 0, W, H, 28); x.fillStyle = g; x.fill();
      x.fillStyle = '#FFFFFF'; x.font = `800 30px ${DISPLAY}`; x.fillText(clip(x, D.label || 'Hoola', W - 56), 28, 60);
      x.font = `700 22px ${FONT}`; x.fillStyle = '#FFF1DE';
      const note = D.phase === 'error' ? (D.error || '') : ((D.data && D.data.note) || '');
      const words = note.split(' '); let line = '', y = 110;
      for (const w of words) { if (x.measureText(line + w).width > W - 70 && line) { x.fillText(line, 28, y); line = ''; y += 32; if (y > 230) break; } line += w + ' '; }
      if (y <= 230) x.fillText(line, 28, y);
      const p = D.phase === 'start' ? (t * .35) % 1 : (D.phase === 'done' ? 1 : .0);
      rr(x, 28, H - 54, W - 56, 16, 8); x.fillStyle = 'rgba(255,255,255,.2)'; x.fill();
      rr(x, 28, H - 54, Math.max(16, (W - 56) * p), 16, 8); x.fillStyle = D.phase === 'error' ? '#F87171' : '#FFD9A8'; x.fill();
      tex.needsUpdate = true;
    }
    return {
      set(d) { D = d; av.mood = MOOD[d.phase] || 'idle'; av.say(sayOf(d)); },
      update(t, dt) {
        av.update(t, dt);
        if (Math.floor(t * 12) !== last) { last = Math.floor(t * 12); draw(t); }
        const sp = D.phase === 'start' ? 1.4 : .3;
        cubes.forEach((cb, i) => { const a = t * sp + i * 1.256; cb.position.set(Math.cos(a) * 1.3, 1.2 + Math.sin(a * 2) * .25, Math.sin(a) * 1.3); cb.rotation.set(t * sp, t * sp * .7, 0); });
        gear.rotation.z = t * sp;
      },
      redraw() { av.redraw(); }
    };
  };

  const ACCENT = { email: 0x8b6dff, browser: 0x2dd4bf, payment: 0xffb15c, bluetooth: 0x60a5fa, network: 0xa78bfa, pc: 0xe879f9, work: 0xffb15c };

  window.HoolaTheatre = {
    scenes: Object.keys(SCENES),
    mount(canvas, name) {
      if (!SCENES[name]) name = 'work';
      let st;
      try { st = makeStage(canvas, ACCENT[name], { pad: name !== 'network' }); } catch (e) { return { set() {}, dispose() {}, failed: true }; }
      const sc = SCENES[name](st);
      const clock = new T.Clock(); let t = 0, raf = 0, alive = true, paused = false;
      st.layout();
      const ro = window.ResizeObserver ? new ResizeObserver(() => st.layout()) : null; if (ro) ro.observe(canvas);
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { if (alive && sc.redraw) sc.redraw(); });
      function frame() {
        if (!alive) return;
        raf = requestAnimationFrame(frame);
        if (paused || document.hidden) { clock.getDelta(); return; }
        const dt = Math.min(clock.getDelta(), .05); t += dt;
        sc.update(t, dt); st.tick(t);
      }
      frame();
      return {
        name,
        set(d) { try { sc.set(Object.assign(fresh(), d || {}, { data: (d && d.data) || {} })); } catch (e) {} },
        pause(on) { paused = !!on; },
        dispose() { alive = false; cancelAnimationFrame(raf); if (ro) ro.disconnect(); try { st.renderer.dispose(); st.renderer.forceContextLoss(); } catch (e) {} }
      };
    }
  };
})();
