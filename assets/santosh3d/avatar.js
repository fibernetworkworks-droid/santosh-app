/* Hoola avatar builder (three.js r1xx, global THREE).
 *
 * HoolaAvatar.build(look, env) -> parts used by the behaviour loop in index.html:
 *   { root, body, neck, head, eyes, irises, brows, smile, mouthIn, hands, screenLight, M, dispose() }
 *
 * `look` = null / undefined builds the original Santosh exactly. Female looks come from looks.js
 * (window.HOOLA_LOOKS) and share the same clay style: one smooth chubby head, glossy eyes, puffy
 * clothes, phone held in both hands. Only colours, hair, clothes and small accessories change.
 */
(function () {
  const V3 = THREE.Vector3;
  const P = (o) => new THREE.MeshPhysicalMaterial(o);
  const C = (c) => new THREE.Color(c);
  const shade = (c, k) => C(c).multiplyScalar(k);

  function cloth(color, o) {
    return P(Object.assign({ color: C(color), roughness: .6, sheen: .15, sheenColor: shade(color, 1.1), sheenRoughness: .5,
      clearcoat: .1, clearcoatRoughness: .5, envMapIntensity: .4 }, o || {}));
  }

  const SANTOSH = {
    id: 'm000', name: 'Santosh', gender: 'm', skin: '#cc8a5e', eyes: '#3e2414', lips: '#7c3020',
    hair: { style: 'santosh', color: '#17110e' }, glasses: { style: 'round', color: '#141416' },
    top: { style: 'puffer', color: '#f29418', color2: '#ee7b2c' }, straps: '#27358c',
    bottom: { style: 'pants', color: '#2c3566' }, shoes: '#f7f5f2', laces: '#f29418', phone: '#26272c', acc: []
  };

  function build(look) {
    const L = Object.assign({}, SANTOSH, look || {});
    if (look && !('straps' in look)) L.straps = null;   // backpack straps only when a look asks for them
    const fem = L.gender === 'f';
    const acc = new Set(L.acc || []);
    const geos = [], mats = [];
    const track = (o) => { o.traverse(n => { if (n.geometry) geos.push(n.geometry); if (n.material) mats.push(n.material); }); };

    /* ---------- materials ---------- */
    const skinC = C(L.skin);
    const M = {
      skin:   P({ color: skinC, roughness: .5, sheen: .18, sheenColor: C(0xff9e80), sheenRoughness: .6, clearcoat: .06, envMapIntensity: .35 }),
      skinDp: P({ color: skinC.clone().multiplyScalar(.93), roughness: .6, sheen: .3, sheenColor: C(0xff9e80), envMapIntensity: .5 }),
      nose:   P({ color: skinC.clone().lerp(C(0xe07050), .18), roughness: .5, sheen: .4, sheenColor: C(0xffa080), envMapIntensity: .55 }),
      hair:   P({ color: C(L.hair.color), roughness: .36, clearcoat: .55, clearcoatRoughness: .28, sheen: .12, sheenColor: shade(L.hair.color, 2.2).lerp(C(0x5a4038), .5), envMapIntensity: .45 }),
      white:  P({ color: 0xfbfaf6, roughness: .18, clearcoat: 1, clearcoatRoughness: .05, envMapIntensity: .7 }),
      iris:   P({ color: C(L.eyes), roughness: .25, clearcoat: 1, clearcoatRoughness: .05 }),
      pupil:  P({ color: 0x0a0605, roughness: .2, clearcoat: 1 }),
      shine:  new THREE.MeshBasicMaterial({ color: 0xffffff }),
      frame:  P({ color: C((L.glasses && L.glasses.color) || '#141416'), roughness: .22, clearcoat: 1, clearcoatRoughness: .08, envMapIntensity: .6,
                  metalness: (L.glasses && L.glasses.style === 'thin') ? .8 : 0 }),
      lens:   P({ color: 0xffffff, roughness: .04, transparent: true, opacity: .1, clearcoat: 1, envMapIntensity: 1.6, depthWrite: false }),
      lip:    P({ color: C(L.lips), roughness: .4, clearcoat: fem ? .5 : 0 }),
      mouth:  P({ color: 0x4a1512, roughness: .6 }),
      top:    cloth(L.top.color),
      top2:   cloth(L.top.color2 || L.top.color, { roughness: .75 }),
      seam:   cloth(shade(L.top.color, .9)),
      strap:  P({ color: C(L.straps || '#27358c'), roughness: .48, clearcoat: .25, sheen: .1, sheenColor: C(0x8090ff) }),
      zip:    P({ color: 0x3a2b20, roughness: .4, metalness: .2 }),
      cord:   P({ color: shade(L.top.color, .66), roughness: .55 }),
      phone:  P({ color: C(L.phone || '#26272c'), roughness: .28, metalness: .35, clearcoat: 1, clearcoatRoughness: .1, envMapIntensity: 1 }),
      glass:  P({ color: 0x0d0e12, roughness: .08, metalness: .2, clearcoat: 1, envMapIntensity: 1.4 }),
      screen: new THREE.MeshBasicMaterial({ color: 0x9fd0ff }),
      bottom: cloth(L.bottom.color, { roughness: .62, sheen: .25 }),
      shoe:   P({ color: C(L.shoes || '#f7f5f2'), roughness: .4, clearcoat: .4, envMapIntensity: .5 }),
      sole:   P({ color: 0xd9d3e8, roughness: .5 }),
      lace:   P({ color: C(L.laces || L.top.color), roughness: .5 }),
      gold:   P({ color: C(L.metal || '#d9a441'), roughness: .25, metalness: .9, clearcoat: .6, envMapIntensity: 1.2 }),
      accent: P({ color: C(L.accColor || '#c2185b'), roughness: .35, clearcoat: .6 }),
      pearl:  P({ color: 0xfaf6ee, roughness: .15, clearcoat: 1, envMapIntensity: 1 }),
      petal:  P({ color: C(L.flower || '#fbfbf7'), roughness: .5, sheen: .4, sheenColor: C(0xffffff) })
    };

    function mesh(geo, mat, parent, pos, scale, rot) {
      const m = new THREE.Mesh(geo, mat);
      if (pos) m.position.set(pos[0], pos[1], pos[2]);
      if (scale) m.scale.set(scale[0], scale[1], scale[2]);
      if (rot) m.rotation.set(rot[0], rot[1], rot[2]);
      m.castShadow = true; m.receiveShadow = true;
      parent.add(m); return m;
    }
    const SPH = new THREE.SphereGeometry(1, 64, 48);
    const SPH_LO = new THREE.SphereGeometry(1, 32, 24);
    function limb(a, b, r, mat, parent) {
      const dir = new V3().subVectors(b, a); const len = dir.length();
      const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 10, 24), mat);
      m.position.copy(a).add(b).multiplyScalar(.5);
      m.quaternion.setFromUnitVectors(new V3(0, 1, 0), dir.normalize());
      m.castShadow = true; m.receiveShadow = true; parent.add(m); return m;
    }
    function tube(points, r, mat, parent, scale) {
      const m = mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map(p => new V3(p[0], p[1], p[2]))), 64, r, 14), mat, parent);
      if (scale) m.scale.set(scale[0], scale[1], scale[2]);
      return m;
    }
    // chain of overlapping beads (braids, ponytails, gajra)
    function beads(points, r0, r1, mat, parent, squash) {
      const curve = new THREE.CatmullRomCurve3(points.map(p => new V3(p[0], p[1], p[2])));
      const n = Math.max(4, Math.round(curve.getLength() / ((r0 + r1) * .55)));
      for (let i = 0; i <= n; i++) {
        const u = i / n, p = curve.getPoint(u), r = r0 + (r1 - r0) * u;
        const b = mesh(SPH_LO, mat, parent, [p.x, p.y, p.z], [r, r * (squash || .8), r]);
        b.lookAt(p.clone().add(curve.getTangent(u)));
      }
    }

    /* ================= CHARACTER ================= */
    const root = new THREE.Group();
    const body = new THREE.Group(); root.add(body);
    const puffy = L.top.style === 'puffer';
    const armR = puffy ? .3 : .24, armR2 = puffy ? .27 : .22;
    const shX = fem && !puffy ? .9 : 1.0;

    /* ---------- torso by outfit ---------- */
    function smoothTorso(hemY, flare) {
      mesh(SPH, M.top, body, [0, .98, 0], [.9, .62, .68]);                       // chest + shoulders
      mesh(SPH, M.top, body, [0, .5, 0], [.86, .62, .66]);                       // waist
      mesh(SPH, M.top, body, [0, .06, 0], [.92 + flare, .5, .7 + flare * .5]);  // hips
      if (hemY !== null) mesh(new THREE.TorusGeometry(.8 + flare, .07, 14, 64), M.seam, body, [0, hemY + .06, 0], [1, 1, .8], [Math.PI / 2, 0, 0]);
    }
    const T = L.top.style;
    if (T === 'puffer') {
      [[-0.35, 1.16, .5, .86], [0.12, 1.2, .5, .88], [0.58, 1.22, .5, .9], [1.02, 1.26, .46, .88]].forEach(([y, sx, sy, sz]) =>
        mesh(SPH, M.top, body, [0, y, 0], [sx * .82, sy * .82, sz * .82]));
      mesh(new THREE.TorusGeometry(.5, .22, 24, 64), M.top, body, [0, 1.36, -.2], [1.28, 1, 1], [Math.PI / 2 - .38, 0, 0]);
      mesh(new THREE.CylinderGeometry(.37, .4, .36, 48), M.top2, body, [0, 1.42, .02]);
      [1.3, 1.4, 1.5].forEach(y => mesh(new THREE.TorusGeometry(.385, .022, 10, 48), M.top2, body, [0, y, .02], null, [Math.PI / 2, 0, 0]));
      mesh(new THREE.BoxGeometry(.05, 1.38, .03), M.zip, body, [0, .52, .73]);
      mesh(new THREE.BoxGeometry(.07, .14, .03), M.zip, body, [0, 1.12, .76]);
      [-1, 1].forEach(s => {
        limb(new V3(s * .15, 1.24, .62), new V3(s * .16, .78, .74), .017, M.cord, body);
        mesh(new THREE.CylinderGeometry(.028, .028, .08, 12), M.zip, body, [s * .16, .74, .745]);
      });
    } else if (T === 'hoodie' || T === 'track') {
      smoothTorso(-.36, 0);
      mesh(new THREE.TorusGeometry(.48, .19, 24, 64), M.top, body, [0, 1.34, -.2], [1.22, 1, 1], [Math.PI / 2 - .38, 0, 0]);
      mesh(new THREE.CylinderGeometry(.35, .38, .22, 48), M.top2, body, [0, 1.4, .02]);
      if (T === 'hoodie') {
        mesh(new THREE.BoxGeometry(.9, .42, .12), M.seam, body, [0, .1, .62], [1, 1, 1], [-.12, 0, 0]);
        [-1, 1].forEach(s => limb(new V3(s * .14, 1.26, .58), new V3(s * .15, .86, .68), .02, M.top2, body));
      } else {
        mesh(new THREE.BoxGeometry(.05, 1.5, .03), M.zip, body, [0, .5, .69]);
        mesh(new THREE.BoxGeometry(.07, .14, .03), M.zip, body, [0, 1.1, .71]);
      }
    } else if (T === 'kurta') {
      smoothTorso(null, .12);
      mesh(new THREE.CylinderGeometry(.86, 1.08, 1.0, 64, 1, true), M.top, body, [0, -.42, 0], [1, 1, .78]);   // tunic flare
      mesh(new THREE.TorusGeometry(1.07, .045, 10, 72), M.top2, body, [0, -.92, 0], [1, 1, .78], [Math.PI / 2, 0, 0]);
      mesh(new THREE.CylinderGeometry(.33, .36, .12, 40), M.top2, body, [0, 1.4, .02]);
      mesh(new THREE.BoxGeometry(.06, .5, .03), M.top2, body, [0, 1.12, .67], null, [-.2, 0, 0]);               // placket
      // dupatta around the neck, both ends falling in front
      tube([[-.95, -.2, .45], [-.82, .7, .62], [-.55, 1.32, .36], [0, 1.5, -.25], [.55, 1.32, .36], [.82, .7, .62], [.95, -.2, .45]], .13, M.top2, body, [1, 1, 1]);
    } else if (T === 'saree') {
      // blouse (short, colour2) + saree body + pallu across the chest over the left shoulder
      mesh(SPH, M.top2, body, [0, 1.0, 0], [.88, .55, .66]);
      mesh(SPH, M.top, body, [0, .42, 0], [.86, .62, .66]);
      mesh(SPH, M.top, body, [0, .02, 0], [.94, .5, .72]);
      mesh(new THREE.CylinderGeometry(.33, .36, .12, 40), M.top2, body, [0, 1.4, .02]);
      tube([[.85, -.15, .55], [.55, .45, .74], [0, .95, .76], [-.55, 1.32, .5], [-.85, 1.35, -.05], [-.9, .6, -.6], [-.88, -.4, -.62]], .2, M.top, body, [1, 1, 1]);
      tube([[.9, -.3, .5], [.62, .35, .78], [.06, .86, .85], [-.5, 1.24, .62]], .045, M.gold, body);          // zari border
      // pleats
      for (let i = -2; i <= 2; i++) mesh(new THREE.BoxGeometry(.06, .9, .05), M.seam, body, [i * .12, -.95, .74], null, [-.12, 0, 0]);
    } else if (T === 'blazer') {
      smoothTorso(-.38, 0);
      mesh(new THREE.CylinderGeometry(.33, .36, .14, 40), M.top2, body, [0, 1.4, .02]);
      // shirt V + lapels
      mesh(new THREE.CylinderGeometry(.01, .32, .7, 3), M.top2, body, [0, 1.0, .58], [1, 1, .3], [Math.PI, 0, 0]);
      [-1, 1].forEach(s => mesh(new THREE.BoxGeometry(.16, .8, .04), M.seam, body, [s * .22, .96, .66], null, [-.25, 0, s * .32]));
      [.55, .25].forEach(y => mesh(SPH_LO, M.zip, body, [.06, y, .72], [.045, .045, .02]));
    } else if (T === 'sweater') {
      smoothTorso(-.34, 0);
      mesh(new THREE.CylinderGeometry(.36, .4, .3, 48), M.top2, body, [0, 1.4, .02]);
      [.72, .52].forEach(y => mesh(new THREE.TorusGeometry(.84, .05, 10, 72), M.top2, body, [0, y, 0], [1, 1, .8], [Math.PI / 2, 0, 0]));
    } else if (T === 'denim') {
      smoothTorso(-.36, 0);
      [-1, 1].forEach(s => mesh(new THREE.BoxGeometry(.32, .14, .06), M.seam, body, [s * .2, 1.33, .45], null, [-.6, 0, s * .45]));  // collar
      mesh(new THREE.CylinderGeometry(.01, .28, .45, 3), M.top2, body, [0, 1.17, .58], [1, 1, .3], [Math.PI, 0, 0]);
      [.8, .5, .2].forEach(y => mesh(SPH_LO, M.gold, body, [0, y, .7], [.04, .04, .02]));
      [-1, 1].forEach(s => mesh(new THREE.BoxGeometry(.3, .22, .04), M.seam, body, [s * .38, .82, .62], null, [-.15, s * .3, 0]));
    } else if (T === 'wrap') {
      smoothTorso(null, .14);
      mesh(new THREE.CylinderGeometry(.9, 1.12, .9, 64, 1, true), M.top, body, [0, -.4, 0], [1, 1, .78]);
      mesh(new THREE.CylinderGeometry(.33, .36, .1, 40), M.skin, body, [0, 1.42, .02]);
      tube([[.7, .1, .66], [.25, .7, .72], [-.25, 1.25, .55]], .05, M.top2, body);                            // wrap line
      mesh(new THREE.TorusGeometry(.9, .06, 10, 72), M.top2, body, [0, .3, 0], [1, 1, .76], [Math.PI / 2, 0, 0]); // belt
    }

    /* ---------- backpack straps (Santosh signature, optional) ---------- */
    if (L.straps) [-1, 1].forEach(s => {
      const sx = puffy ? 1 : .88;
      tube([[s * .5 * sx, 1.28, -.36], [s * .62 * sx, 1.46, 0], [s * .66 * sx, 1.26, .45], [s * .67 * sx, .78, .6], [s * .67 * sx, .18, .61], [s * .65 * sx, -.3, .56]], puffy ? .075 : .06, M.strap, body);
    });
    if (acc.has('sling')) tube([[-.55, 1.42, .1], [-.2, 1.1, .7], [.35, .45, .74], [.75, -.1, .6]], .045, M.accent, body);

    /* ---------- arms, cuffs, hands ---------- */
    const hands = [];
    [-1, 1].forEach(s => {
      const sh = new V3(s * shX, 1.1, 0), el = new V3(s * (shX + .2), .36, .28), wr = new V3(s * .44, .5, 1.0);
      mesh(SPH, M.top, body, [sh.x, sh.y, sh.z], [armR + .06, armR + .06, armR + .06]);
      limb(sh, el, armR, M.top, body);
      mesh(SPH, M.top, body, [el.x, el.y, el.z], [armR, armR, armR]);
      limb(el, wr, armR2, M.top, body);
      if (T === 'track') limb(sh.clone().add(new V3(0, .1, .2)), el.clone().add(new V3(0, 0, .25)), .035, M.top2, body);
      const cuff = new THREE.Mesh(new THREE.TorusGeometry(puffy ? .2 : .17, .07, 14, 40), M.top2);
      cuff.position.copy(wr); cuff.lookAt(new V3().subVectors(wr, el).add(wr)); cuff.castShadow = true; body.add(cuff);
      const hand = new THREE.Group(); hand.position.set(s * .34, .55, 1.08); body.add(hand);
      mesh(SPH, M.skin, hand, [0, 0, 0], fem ? [.155, .195, .175] : [.17, .21, .19]);
      for (let i = 0; i < 3; i++) mesh(SPH_LO, M.skin, hand, [s * -.05, .12 - i * .1, .15], fem ? [.058, .05, .055] : [.065, .055, .06]);
      if (acc.has('bangles') && s < 0) [0, 1, 2].forEach(i => mesh(new THREE.TorusGeometry(.16, .022, 8, 32), i === 1 ? M.accent : M.gold, body,
        [wr.x - s * .02 * i, wr.y + .02 * i, wr.z - .08 - .05 * i], null, [0, Math.PI / 2 - .3, 0]));
      if (acc.has('watch') && s > 0) mesh(new THREE.TorusGeometry(.17, .035, 8, 32), M.accent, body, [wr.x, wr.y, wr.z - .1], null, [0, Math.PI / 2 - .3, 0]);
      hands.push(hand);
    });

    /* ---------- phone ---------- */
    const phone = new THREE.Group(); phone.position.set(0, .62, 1.13); phone.rotation.x = .5; body.add(phone);
    (function () {
      const w = .62, h = 1.02, r = .1, sh = new THREE.Shape();
      sh.moveTo(-w / 2 + r, -h / 2); sh.lineTo(w / 2 - r, -h / 2); sh.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
      sh.lineTo(w / 2, h / 2 - r); sh.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2); sh.lineTo(-w / 2 + r, h / 2);
      sh.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r); sh.lineTo(-w / 2, -h / 2 + r); sh.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
      const g = new THREE.ExtrudeGeometry(sh, { depth: .05, bevelEnabled: true, bevelThickness: .018, bevelSize: .018, bevelSegments: 6, curveSegments: 16 });
      g.translate(0, 0, -.025);
      mesh(g, M.phone, phone);
      mesh(new THREE.BoxGeometry(.2, .2, .03), M.phone, phone, [-.15, .34, .055]);
      mesh(new THREE.CylinderGeometry(.045, .045, .02, 24), M.glass, phone, [-.19, .38, .075], null, [Math.PI / 2, 0, 0]);
      mesh(new THREE.CylinderGeometry(.04, .04, .02, 24), M.glass, phone, [-.11, .3, .075], null, [Math.PI / 2, 0, 0]);
      const scr = new THREE.Mesh(new THREE.PlaneGeometry(w - .06, h - .06), M.screen);
      scr.position.z = -.05; scr.rotation.y = Math.PI; phone.add(scr);
    })();
    const screenLight = new THREE.PointLight(0x9fd0ff, 0, 3.2, 2);
    screenLight.position.set(0, 1.05, .95); body.add(screenLight);

    /* ---------- legs + shoes ---------- */
    const B = L.bottom.style;
    const legMat = (B === 'skirt') ? (L.bottom.legs ? cloth(L.bottom.legs, { roughness: .5 }) : M.skin) : M.bottom;
    if (B === 'skirt') {
      mesh(new THREE.CylinderGeometry(.78, 1.02, .78, 64, 1, true), M.bottom, body, [0, -.6, 0], [1, 1, .8]);
      mesh(new THREE.TorusGeometry(1.0, .05, 10, 72), M.bottom, body, [0, -.98, 0], [1, 1, .8], [Math.PI / 2, 0, 0]);
      mesh(SPH, M.bottom, body, [0, -.3, 0], [.8, .26, .62]);
    } else if (B === 'long') {
      mesh(new THREE.CylinderGeometry(.8, 1.12, 1.28, 64, 1, true), M.bottom, body, [0, -.92, 0], [1, 1, .8]);
      mesh(new THREE.TorusGeometry(1.1, .05, 10, 72), L.bottom.color2 ? cloth(L.bottom.color2) : M.gold, body, [0, -1.54, 0], [1, 1, .8], [Math.PI / 2, 0, 0]);
      mesh(SPH, M.bottom, body, [0, -.3, 0], [.82, .26, .64]);
    } else {
      mesh(SPH, M.bottom, body, [0, -.62, 0], [.74, .32, .58]);
    }
    [-1, 1].forEach(s => {
      if (B !== 'long') {
        limb(new V3(s * .32, -.62, 0), new V3(s * .34, -1.42, .02), B === 'leggings' || B === 'skirt' ? .2 : .25, legMat, body);
        if (B === 'pants' || B === 'jeans') mesh(new THREE.TorusGeometry(.24, .05, 12, 36), B === 'jeans' ? M.seam : M.bottom, body, [s * .34, -1.42, .02], null, [Math.PI / 2, 0, 0]);
      }
      const shoe = new THREE.Group(); shoe.position.set(s * .36, -1.6, .14); shoe.rotation.y = s * -.12; body.add(shoe);
      mesh(SPH, M.shoe, shoe, [0, .02, 0], [.27, .17, .42]);
      mesh(new THREE.CylinderGeometry(1, 1, 1, 40), M.sole, shoe, [0, -.1, .0], [.28, .06, .43]);
      mesh(SPH_LO, M.lace, shoe, [0, .12, .14], [.1, .04, .14]);
    });

    /* ---------- head ---------- */
    const neck = new THREE.Group(); neck.position.set(0, 1.55, .03); body.add(neck);
    const head = new THREE.Group(); head.position.set(0, 1.04, .02); neck.add(head);
    const HS = [1, .95, .92];
    const bulge = (yu) => (fem ? .095 : .11) * Math.exp(-(((yu + .38) / .36) ** 2));
    const headGeo = new THREE.SphereGeometry(1, 96, 72);
    { const pa = headGeo.attributes.position;
      for (let i = 0; i < pa.count; i++) {
        const b = bulge(pa.getY(i));
        pa.setX(i, pa.getX(i) * (1 + b)); pa.setZ(i, pa.getZ(i) * (1 + b * .85));
      }
      headGeo.computeVertexNormals(); }
    mesh(headGeo, M.skin, head, [0, 0, 0], HS);

    function surf(x, y) {
      const yu = y / HS[1], b = bulge(yu);
      const xu = x / (HS[0] * (1 + b));
      const z = HS[2] * (1 + b * .85) * Math.sqrt(Math.max(0, 1 - xu * xu - yu * yu));
      const p = new V3(x, y, z);
      const n = new V3(xu / HS[0], yu / HS[1], z / (HS[2] * (1 + b * .85)) ** 2 * HS[2]).normalize();
      return { p, n };
    }
    function place(obj, x, y, off) {
      const { p, n } = surf(x, y);
      obj.position.copy(p).addScaledVector(n, off);
      obj.lookAt(obj.position.clone().add(n));
      head.add(obj); return obj;
    }

    // ears
    [-1, 1].forEach(s => {
      mesh(SPH_LO, M.skin, head, [s * .97, -.04, -.02], [.14, .23, .18]);
      mesh(SPH_LO, M.skinDp, head, [s * 1.03, -.04, .01], [.06, .14, .1]);
    });

    // eyes
    const eyes = [], irises = [];
    [-1, 1].forEach(s => {
      const g = new THREE.Group(); place(g, s * .35, .04, .0);
      const ball = new THREE.Group(); g.add(ball);
      mesh(SPH, M.white, ball, [0, 0, 0], fem ? [.2, .225, .11] : [.2, .215, .11]);
      const ir = new THREE.Group(); ir.position.z = .07; ball.add(ir);
      mesh(SPH, M.iris, ir, [0, 0, 0], fem ? [.14, .148, .045] : [.135, .14, .045]);
      mesh(SPH, M.pupil, ir, [0, 0, .022], [.085, .088, .03]);
      mesh(SPH_LO, M.shine, ball, [.055, .065, .125], [.042, .042, .01]).castShadow = false;
      mesh(SPH_LO, M.shine, ball, [-.045, -.05, .12], [.018, .018, .006]).castShadow = false;
      if (fem) {   // three lashes flicking up at the outer corner, they blink with the eye
        [[.155, .15, .75], [.19, .09, 1.1]].forEach(([x, y, a]) => {
          const l = mesh(new THREE.CapsuleGeometry(.013, .055, 4, 8), M.pupil, ball, [s * x, y, .05]);
          l.rotation.z = -s * a;
        });
        const lid = mesh(new THREE.TorusGeometry(.2, .018, 8, 32, Math.PI * .9), M.pupil, ball, [0, .005, .06], [1, 1.08, 1]);
        lid.rotation.z = Math.PI * .05;
      }
      eyes.push(ball); irises.push(ir);
    });

    // glasses
    const G = (L.glasses && L.glasses.style) || 'none';
    if (G !== 'none') {
      const rings = [];
      const thick = G === 'thin' ? .016 : .03;
      [-1, 1].forEach(s => {
        const ring = new THREE.Group(); place(ring, s * .35, .05, .2);
        let fr;
        if (G === 'square') { fr = mesh(new THREE.TorusGeometry(.3, thick + .006, 10, 4), M.frame, ring, null, [1.08, .82, 1], [0, 0, Math.PI / 4]); }
        else if (G === 'cat') {
          fr = mesh(new THREE.TorusGeometry(.275, thick + .004, 18, 72), M.frame, ring, null, [1.1, .82, 1]);
          mesh(new THREE.ConeGeometry(.05, .16, 12), M.frame, ring, [s * .27, .17, 0], null, [0, 0, -s * .9]);
        }
        else fr = mesh(new THREE.TorusGeometry(G === 'big' ? .31 : .275, thick, 18, 72), M.frame, ring);
        const lens = new THREE.Mesh(new THREE.CircleGeometry(.27, 48), M.lens); ring.add(lens);
        if (G === 'square' || G === 'cat') lens.scale.set(1.05, .82, 1);
        rings.push(ring);
      });
      head.updateMatrixWorld(true);
      const ringPt = (ring, x) => ring.localToWorld(new V3(x, 0, 0)).applyMatrix4(head.matrixWorld.clone().invert());
      const w = G === 'square' ? .3 : G === 'big' ? .31 : .27;
      limb(ringPt(rings[0], w), ringPt(rings[1], -w), thick * .75, M.frame, head);
      [[rings[0], -w, -1], [rings[1], w, 1]].forEach(([r, x, s]) => limb(ringPt(r, x), new V3(s * .99, .1, -.08), thick * .8, M.frame, head));
    }

    // eyebrows
    const brows = [];
    [-1, 1].forEach(s => {
      const b = new THREE.Mesh(new THREE.CapsuleGeometry(fem ? .034 : .05, fem ? .22 : .2, 8, 16), M.hair);
      b.castShadow = true; place(b, s * .35, fem ? .42 : .4, .035); b.rotateZ(Math.PI / 2 + s * (fem ? .06 : -.18));
      brows.push({ m: b, base: b.position.clone(), n: surf(s * .35, .4).n });
    });

    // nose, mouth, blush
    place(mesh(SPH_LO, M.nose, new THREE.Group(), null, fem ? [.085, .07, .07] : [.1, .085, .08]), 0, -.17, -.005);
    const smileArc = 2.2;
    const smile = new THREE.Mesh(new THREE.TorusGeometry(.17, fem ? .03 : .024, 12, 48, smileArc), M.lip);
    place(smile, 0, -.43, .005); smile.rotateZ(-Math.PI / 2 - smileArc / 2);
    if (fem) { const ul = mesh(SPH_LO, M.lip, new THREE.Group(), null, [.07, .028, .03]); place(ul, 0, -.4, .0); }
    const mouthIn = new THREE.Mesh(SPH, M.mouth); place(mouthIn, 0, -.47, -.025); mouthIn.scale.set(.14, .001, .05);
    const blushTex = (() => {
      const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d');
      const g = x.createRadialGradient(64, 64, 0, 64, 64, 64); g.addColorStop(0, 'rgba(255,110,110,.9)'); g.addColorStop(1, 'rgba(255,110,110,0)');
      x.fillStyle = g; x.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(c);
    })();
    const blushMat = new THREE.MeshBasicMaterial({ map: blushTex, transparent: true, opacity: fem ? .5 : .42, depthWrite: false });
    [-1, 1].forEach(s => place(new THREE.Mesh(new THREE.PlaneGeometry(.42, .3), blushMat), s * .58, -.25, .012));

    /* ---------- face accessories ---------- */
    if (acc.has('bindi')) place(mesh(SPH_LO, M.accent, new THREE.Group(), null, [.045, .045, .02]), 0, .33, .01);
    if (acc.has('nosering')) place(mesh(new THREE.TorusGeometry(.04, .009, 8, 24), M.gold, new THREE.Group()), .07, -.2, .03);
    if (acc.has('nosestud')) place(mesh(SPH_LO, M.gold, new THREE.Group(), null, [.018, .018, .012]), .075, -.18, .02);
    if (acc.has('freckles')) [[-.55, -.12], [-.48, -.2], [-.62, -.22], [.55, -.12], [.48, -.2], [.62, -.22], [-.4, -.1], [.4, -.1]].forEach(([x, y]) =>
      place(mesh(SPH_LO, P({ color: skinC.clone().multiplyScalar(.62), roughness: .7 }), new THREE.Group(), null, [.016, .016, .006]), x, y, .004));
    if (acc.has('mole')) place(mesh(SPH_LO, M.pupil, new THREE.Group(), null, [.018, .018, .008]), .3, -.42, .004);
    if (acc.has('lipstick')) M.lip.clearcoat = .9;

    // ear jewellery (hangs below the earlobe, in front of hair curtains)
    [-1, 1].forEach(s => {
      const ear = new V3(s * 1.0, -.27, .06);
      if (acc.has('studs')) mesh(SPH_LO, M.pearl, head, [ear.x, ear.y + .04, ear.z], [.045, .045, .045]);
      if (acc.has('hoops')) mesh(new THREE.TorusGeometry(.13, .018, 10, 40), M.gold, head, [ear.x, ear.y - .1, ear.z], null, [0, Math.PI / 2, 0]);
      if (acc.has('jhumka')) {
        mesh(SPH_LO, M.gold, head, [ear.x, ear.y + .02, ear.z], [.035, .035, .035]);
        mesh(new THREE.ConeGeometry(.085, .12, 20, 1, true), M.gold, head, [ear.x, ear.y - .1, ear.z]);
        mesh(SPH_LO, M.accent, head, [ear.x, ear.y - .17, ear.z], [.03, .03, .03]);
      }
      if (acc.has('drops')) { mesh(SPH_LO, M.gold, head, [ear.x, ear.y + .02, ear.z], [.025, .025, .025]); mesh(SPH_LO, M.accent, head, [ear.x, ear.y - .1, ear.z], [.045, .07, .045]); }
    });
    if (acc.has('necklace')) for (let i = 0; i <= 14; i++) {
      const a = -Math.PI * .42 + i / 14 * Math.PI * .84;
      mesh(SPH_LO, acc.has('pearls') ? M.pearl : M.gold, body, [Math.sin(a) * .42, 1.3 - Math.cos(a) * .12, Math.cos(a) * .48 + .1], [.04, .04, .04]);
    }
    if (acc.has('scarf')) {
      mesh(new THREE.TorusGeometry(.44, .14, 16, 48), M.accent, body, [0, 1.42, .05], [1, 1, .9], [Math.PI / 2 - .15, 0, 0]);
      limb(new V3(.25, 1.35, .5), new V3(.32, .8, .7), .1, M.accent, body);
    }

    /* ---------- hair ---------- */
    const H = L.hair.style;
    const hm = M.hair;
    const cap = (back) => mesh(new THREE.SphereGeometry(1.04, 64, 48, 0, Math.PI * 2, 0, 1.9), hm, head, [0, 0, 0], [1, .96, .95], [back === undefined ? -1.0 : back, 0, 0]);
    const tight = () => mesh(new THREE.SphereGeometry(1.03, 64, 48, 0, Math.PI * 2, 0, 1.75), hm, head, [0, .02, 0], [1, .97, .96], [-.95, 0, 0]);
    // soft side-parted fringe that frames the forehead
    const fringe = (side) => {        // L.hair.part: 'c' centre (default) | 'l' | 'r'
      const part = L.hair.part || 'c';
      if (part === 'c') [-1, 1].forEach(s => mesh(SPH, hm, head, [s * .4, .8, .42], [.56, .24, .4], [.6, 0, -s * .5]));
      else {
        // soft side sweep: one smooth lock across the forehead that falls down past the temple
        const k = part === 'r' ? -1 : 1;
        mesh(SPH, hm, head, [-k * .12, .8, .44], [.8, .22, .42], [.66, 0, -k * .22]);
        mesh(SPH, hm, head, [k * .72, .42, .5], [.2, .42, .24], [.25, 0, k * .35]);
      }
    };
    const curtains = (len, width) => {      // hair falling either side of the face down to y = -len
      [-1, 1].forEach(s => {
        mesh(SPH, hm, head, [s * .92, .2 - len / 2, -.1], [width, len / 2 + .5, .45], [0, 0, -s * .06]);
      });
      mesh(SPH, hm, head, [0, .1 - len / 2, -.55], [1.02, len / 2 + .62, .5]);
    };
    const curlM = P({ color: C(L.hair.color), roughness: .55, clearcoat: .12, clearcoatRoughness: .5, sheen: .5, sheenColor: shade(L.hair.color, 2.4), envMapIntensity: .35 });
    const curls = (cx, cy, cz, R, n, r, seed) => {   // ball of curls
      let a = seed || 1.3;
      for (let i = 0; i < n; i++) {
        const u = (i + .5) / n, th = Math.acos(1 - 2 * u), ph = i * 2.39996 + a;
        const x = Math.sin(th) * Math.cos(ph), y = Math.cos(th), z = Math.sin(th) * Math.sin(ph);
        const X = cx + x * R, Y = cy + y * R, Z = cz + z * R;
        if (Z > .2 && Y < .78 && Math.abs(X) < .95) continue;   // keep the face clear
        mesh(SPH_LO, curlM, head, [X, Y, Z], [r, r, r]);
      }
    };
    // hair band hugging the head: an arc over the crown, centred on the head, ends tucked behind the ears
    const band = (tilt, mat) => mesh(new THREE.TorusGeometry(1.06, .055, 10, 64, Math.PI * 1.04), mat || M.accent, head, [0, .04, -.04], [1.02, 1, 1], [tilt, 0, -Math.PI * .02]);
    const tie = (p, mat) => mesh(new THREE.TorusGeometry(.12, .045, 10, 32), mat || M.accent, head, p, null, [Math.PI / 2, 0, 0]);
    const flowers = (pts) => pts.forEach(([x, y, z]) => { for (let i = 0; i < 5; i++) { const a = i / 5 * Math.PI * 2; mesh(SPH_LO, M.petal, head, [x + Math.cos(a) * .06, y + Math.sin(a) * .06, z], [.05, .05, .03]); } mesh(SPH_LO, M.gold, head, [x, y, z + .02], [.03, .03, .02]); });

    if (H === 'santosh') {
      cap();
      [[[.1, .98, .45], [.62, .3, .5], [.5, 0, -.25]], [[-.42, .9, .38], [.48, .26, .42], [.4, 0, .55]], [[.56, .82, .3], [.42, .24, .45], [.3, 0, -.75]],
       [[0, 1.0, -.15], [.78, .33, .72], [0, 0, 0]], [[.32, 1.13, .26], [.4, .17, .3], [.2, .3, -.6]], [[-.12, 1.1, .34], [.34, .15, .3], [.5, -.2, .4]],
       [[-.64, .72, .44], [.26, .18, .3], [.2, 0, .9]], [[.86, .45, -.06], [.27, .42, .55], [0, 0, -.15]], [[-.86, .45, -.06], [.27, .42, .55], [0, 0, .15]],
       [[0, .35, -.82], [.86, .66, .36], [0, 0, 0]]].forEach(([p, s, r]) => mesh(SPH, hm, head, p, s, r));
    } else if (H === 'long' || H === 'bangs' || H === 'halfup' || H === 'wavy') {
      cap(-1.05); curtains(H === 'wavy' ? 1.6 : 1.75, .26);
      if (H === 'bangs') { mesh(SPH, hm, head, [0, .78, .5], [.86, .22, .4], [.35, 0, 0]); [-1, 0, 1].forEach(i => mesh(SPH, hm, head, [i * .3, .66, .66], [.2, .12, .12])); }
      else fringe(L.hair.part === 'r' ? -1 : 1);
      if (H === 'halfup') { mesh(SPH, hm, head, [0, .55, -.98], [.3, .26, .24]); tie([0, .55, -.84]); }
      if (H === 'wavy') [-1, 1].forEach(s => [0, 1, 2, 3].forEach(i => mesh(SPH_LO, hm, head, [s * (1.0 + (i % 2) * .08), -.3 - i * .38, -.05], [.24, .24, .3])));
    } else if (H === 'bob') {
      cap(-1.05); fringe(L.hair.part === 'r' ? -1 : 1);
      [-1, 1].forEach(s => mesh(SPH, hm, head, [s * .9, -.12, -.1], [.3, .62, .5]));
      mesh(SPH, hm, head, [0, -.1, -.5], [1.06, .72, .58]);
      [-1, 1].forEach(s => mesh(SPH_LO, hm, head, [s * .85, -.62, .12], [.24, .14, .26]));
    } else if (H === 'pixie') {
      tight();
      mesh(SPH, hm, head, [.18, .9, .4], [.7, .26, .4], [.6, 0, -.4]);
      mesh(SPH, hm, head, [-.5, .72, .5], [.36, .2, .26], [.6, 0, .9]);
      [-1, 1].forEach(s => mesh(SPH_LO, hm, head, [s * .9, .3, -.05], [.2, .34, .4]));
    } else if (H === 'pony_high' || H === 'pony_low') {
      tight(); fringe(1);
      const hi = H === 'pony_high';
      const base = hi ? [0, .9, -.72] : [0, -.2, -.95];
      if (hi) tie(base.map((v, i) => i === 2 ? v - .02 : v));
      // the tail swings to one side so it reads from the front; the low one comes over the shoulder
      const k = L.hair.part === 'r' ? -1 : 1;
      beads(hi ? [base, [k * .2, 1.2, -1.15], [k * .75, .75, -1.1], [k * 1.05, .0, -.85], [k * 1.15, -.75, -.55]]
               : [[k * .55, -.25, -.85], [k * .95, -.55, -.35], [k * .98, -1.05, .25], [k * .85, -1.55, .5]], .3, .16, hm, head, .85);
      if (!hi) tie([k * .6, -.28, -.82]);
    } else if (H === 'bun' || H === 'bun_low') {
      tight(); fringe(-1);
      const p = H === 'bun' ? [0, 1.12, -.35] : [0, -.1, -1.08];
      mesh(SPH, hm, head, p, [.44, .4, .44]);
      if (acc.has('gajra')) for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; mesh(SPH_LO, M.petal, head, [p[0] + Math.cos(a) * .46, p[1] + Math.sin(a) * .42, p[2] + (H === 'bun' ? 0 : -.05)], [.06, .06, .06]); }
      if (acc.has('pin')) limb(new V3(p[0] - .5, p[1] + .1, p[2] + .05), new V3(p[0] + .5, p[1] + .25, p[2] - .05), .025, M.gold, head);
    } else if (H === 'buns') {
      tight(); fringe(1);
      [-1, 1].forEach(s => mesh(SPH, hm, head, [s * .62, .92, -.2], [.34, .34, .34]));
    } else if (H === 'braid' || H === 'braids') {
      tight(); fringe(1);
      const sides = H === 'braids' ? [-1, 1] : [1];
      sides.forEach(s => {
        beads([[s * .85, .2, -.3], [s * .92, -.4, .05], [s * .82, -1.1, .45], [s * .7, -1.75, .55]], .2, .13, hm, head, .75);
        tie([s * .7, -1.72, .55]);
      });
    } else if (H === 'braid_back') {
      tight(); fringe(-1);
      beads([[0, -.1, -.95], [0, -.8, -1.05], [0, -1.6, -.95], [0, -2.3, -.8]], .24, .15, hm, head, .75);
      [-1, 1].forEach(s => mesh(SPH, hm, head, [s * .9, .05, -.25], [.22, .5, .4]));
      if (acc.has('gajra')) beads([[-.25, .1, -.98], [0, .2, -1.05], [.25, .1, -.98], [.3, -.6, -.95]], .07, .07, M.petal, head, 1);
    } else if (H === 'afro') {
      mesh(SPH, curlM, head, [0, .5, -.42], [1.36, 1.22, 1.0]);
      [-1, 1].forEach(s => mesh(SPH, curlM, head, [s * 1.0, .05, -.2], [.42, .7, .62]));
      curls(0, .5, -.35, 1.25, 70, .3, 1.1);
    } else if (H === 'puffs') {
      tight();
      [-1, 1].forEach(s => { mesh(SPH, curlM, head, [s * .74, .98, -.15], [.46, .46, .46]); curls(s * .74, .98, -.15, .42, 18, .15, s); });
    } else if (H === 'curly' || H === 'curly_short') {
      cap(-1.05);
      const long = H === 'curly';
      mesh(SPH, curlM, head, [0, .45, -.2], [1.12, .9, 1.06]);
      curls(0, .5, -.2, 1.06, 46, .22, 2.2);
      [-1, 1].forEach(s => { for (let i = 0; i < (long ? 5 : 2); i++) { const y = .05 - i * .36; mesh(SPH_LO, curlM, head, [s * (.98 + (i % 2) * .07), y, -.18], [.27, .25, .34]); } });
      if (long) mesh(SPH, curlM, head, [0, -.45, -.7], [1.1, 1.0, .5]);
    } else if (H === 'hijab' || H === 'turban' || H === 'wrap') {
      const W = cloth(L.hair.color, { roughness: .7 });
      if (H === 'hijab') {
        mesh(new THREE.SphereGeometry(1.1, 64, 48, Math.PI / 2 + .9, Math.PI * 2 - 1.8, 0, Math.PI * .86), W, head, [0, .02, -.03], [1, 1, 1]);
        mesh(new THREE.SphereGeometry(1.1, 64, 32, 0, Math.PI * 2, 0, .9), W, head, [0, .02, -.03]);
        mesh(new THREE.TorusGeometry(.98, .1, 16, 72), W, head, [0, -.02, .2], [1, 1.1, 1]);
        mesh(new THREE.CylinderGeometry(.62, 1.15, .7, 64, 1, true), W, body, [0, 1.38, 0], [1, 1, .85]);
        mesh(SPH, W, body, [0, 1.62, .25], [.62, .3, .5]);
        if (acc.has('pin')) mesh(SPH_LO, M.pearl, head, [.75, -.3, .7], [.05, .05, .05]);
      } else {
        // a soft fabric wrap with front knot; hair peeks at the temples
        tight();
        mesh(SPH, W, head, [0, .62, -.18], [1.14, .82, 1.06]);
        [0, 1, 2].forEach(i => mesh(new THREE.TorusGeometry(.95 - i * .1, .14, 14, 64), W, head, [0, .55 + i * .22, -.15 - i * .05], [1.08, 1, 1], [Math.PI / 2 - .3, 0, i * .25]));
        if (H === 'wrap') mesh(SPH, W, head, [0, 1.45, -.45], [.55, .42, .5], [.4, 0, .3]);
        else {   // gele: tall pleated fan rising from the wrap
          for (let i = -3; i <= 3; i++) mesh(SPH, W, head, [i * .2, 1.3 + (3 - Math.abs(i)) * .07, -.2 - Math.abs(i) * .05], [.2, .62, .34], [0, 0, i * .22]);
          mesh(SPH, W, head, [.75, .95, .1], [.3, .22, .3], [0, 0, -.6]);
        }
      }
    } else if (H === 'shoulder' || H === 'sidepart') {
      cap(-1.05); fringe(H === 'sidepart' ? -1 : 1);
      curtains(.95, .3);
      [-1, 1].forEach(s => mesh(SPH_LO, hm, head, [s * .95, -.85, .25], [.26, .18, .28], [.3, 0, 0]));
    }

    if (acc.has('headband')) band(-.42);
    if (acc.has('clip')) mesh(new THREE.BoxGeometry(.24, .06, .06), M.accent, head, [.55, .7, .62], null, [0, 0, .5]);
    if (acc.has('flower')) flowers([[-.72, .72, .45]]);
    if (acc.has('tikka')) { limb(new V3(0, 1.0, .42), new V3(0, .56, .82), .012, M.gold, head); mesh(SPH_LO, M.gold, head, [0, .5, .86], [.06, .07, .03]); }

    const sc = L.scale || 1;
    root.scale.setScalar(sc); root.position.y = (sc - 1) * 1.75;   // keep the feet on the pedestal

    root.traverse(n => { if (n.geometry) geos.push(n.geometry); });
    function dispose() {
      geos.forEach(g => g.dispose && g.dispose());
      Object.values(M).forEach(m => m.dispose && m.dispose());
      blushTex.dispose();
    }
    return { root, body, neck, head, eyes, irises, brows, smile, mouthIn, hands, screenLight, phone, M, dispose, look: L };
  }

  window.HoolaAvatar = { build, SANTOSH };
})();
