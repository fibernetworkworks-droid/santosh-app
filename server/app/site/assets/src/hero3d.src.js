/* Hoola 3D hero (v0.566, MIT, Newtika). A few house scenes drawn with three.js - the section only NAMES one:
   <div data-hoola-3d="orb|knot|particles|waves|blocks" aria-hidden="true"></div>
   Colours come from the site's own CSS variables (--c-primary, --c-accent, --c-bg). Renders only while on screen, one still
   frame under prefers-reduced-motion, paused in a hidden tab, pixel ratio capped at 2, and if WebGL is missing the element
   keeps the section's own background (the content never depends on it). No network, no eval, no visitor data. */
import {
  WebGLRenderer, Scene, PerspectiveCamera, Color, Mesh, Points, Group, BufferGeometry, Float32BufferAttribute,
  IcosahedronGeometry, TorusKnotGeometry, PlaneGeometry, BoxGeometry, MeshStandardMaterial, MeshPhysicalMaterial,
  PointsMaterial, AmbientLight, DirectionalLight, PointLight, Clock, MathUtils
} from 'three';

const still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function cssColour(el, name, fallback) {
  const v = getComputedStyle(el).getPropertyValue(name).trim();
  try { return new Color(v || fallback); } catch (e) { return new Color(fallback); }
}

function glOk() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch (e) { return false; }
}

const SCENES = {
  orb(s, c) {
    const m = new Mesh(new IcosahedronGeometry(1.35, 24), new MeshPhysicalMaterial({ color: c.primary, roughness: 0.25, metalness: 0.15, clearcoat: 1, clearcoatRoughness: 0.2 }));
    const base = m.geometry.attributes.position.array.slice();
    s.add(m);
    return t => {
      const p = m.geometry.attributes.position.array;
      for (let i = 0; i < p.length; i += 3) {
        const x = base[i], y = base[i + 1], z = base[i + 2];
        const k = 1 + 0.06 * Math.sin(x * 2.1 + t * 0.9) * Math.cos(y * 1.7 + t * 0.7) + 0.03 * Math.sin(z * 3 + t);
        p[i] = x * k; p[i + 1] = y * k; p[i + 2] = z * k;
      }
      m.geometry.attributes.position.needsUpdate = true;
      m.geometry.computeVertexNormals();
      m.rotation.y = t * 0.15;
    };
  },
  knot(s, c) {
    const m = new Mesh(new TorusKnotGeometry(0.95, 0.3, 220, 28), new MeshStandardMaterial({ color: c.primary, roughness: 0.3, metalness: 0.4 }));
    s.add(m);
    return t => { m.rotation.x = t * 0.2; m.rotation.y = t * 0.3; };
  },
  particles(s, c) {
    const n = 1800, pos = [], g = new BufferGeometry();
    for (let i = 0; i < n; i++) pos.push(MathUtils.randFloatSpread(9), MathUtils.randFloatSpread(5), MathUtils.randFloatSpread(5));
    g.setAttribute('position', new Float32BufferAttribute(pos, 3));
    const a = new Points(g, new PointsMaterial({ color: c.primary, size: 0.035, transparent: true, opacity: 0.85 }));
    const b = new Points(g, new PointsMaterial({ color: c.accent, size: 0.02, transparent: true, opacity: 0.6 }));
    b.rotation.z = 0.6;
    s.add(a); s.add(b);
    return t => { a.rotation.y = t * 0.04; b.rotation.y = -t * 0.03; a.position.y = Math.sin(t * 0.4) * 0.1; };
  },
  waves(s, c) {
    const geo = new PlaneGeometry(10, 6, 90, 54);
    const m = new Mesh(geo, new MeshStandardMaterial({ color: c.primary, roughness: 0.55, metalness: 0.1, wireframe: true }));
    m.rotation.x = -1.05; m.position.y = -0.6;
    s.add(m);
    const base = geo.attributes.position.array.slice();
    return t => {
      const p = geo.attributes.position.array;
      for (let i = 0; i < p.length; i += 3) p[i + 2] = Math.sin(base[i] * 0.9 + t * 0.8) * 0.18 + Math.cos(base[i + 1] * 1.3 + t * 0.6) * 0.14;
      geo.attributes.position.needsUpdate = true;
    };
  },
  blocks(s, c) {
    const g = new Group(), geo = new BoxGeometry(0.6, 0.6, 0.6);
    const mats = [c.primary, c.accent].map(col => new MeshStandardMaterial({ color: col, roughness: 0.35, metalness: 0.2 }));
    for (let i = 0; i < 14; i++) {
      const m = new Mesh(geo, mats[i % 2]);
      m.position.set(MathUtils.randFloatSpread(6), MathUtils.randFloatSpread(3.2), MathUtils.randFloatSpread(2.5));
      m.rotation.set(Math.random() * 3, Math.random() * 3, 0);
      m.userData.s = 0.2 + Math.random() * 0.4;
      g.add(m);
    }
    s.add(g);
    return t => { g.children.forEach((m, i) => { m.rotation.x += 0.003 * m.userData.s * 10; m.position.y += Math.sin(t + i) * 0.0015; }); g.rotation.y = Math.sin(t * 0.2) * 0.25; };
  }
};

function mount(el) {
  const kind = el.getAttribute('data-hoola-3d');
  const make = SCENES[kind];
  if (!make || !glOk()) { el.setAttribute('data-hoola-3d-off', ''); return; }
  const colours = { primary: cssColour(el, '--c-primary', '#5b45e0'), accent: cssColour(el, '--c-accent', '#ff9a3c') };
  let renderer;
  try { renderer = new WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' }); }
  catch (e) { el.setAttribute('data-hoola-3d-off', ''); return; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const canvas = renderer.domElement;
  canvas.setAttribute('aria-hidden', 'true');
  canvas.style.cssText = 'display:block;width:100%;height:100%';
  el.appendChild(canvas);
  const scene = new Scene(), cam = new PerspectiveCamera(45, 1, 0.1, 100);
  cam.position.set(0, 0, 5.2);
  scene.add(new AmbientLight(0xffffff, 0.55));
  const key = new DirectionalLight(0xffffff, 1.4); key.position.set(3, 4, 5); scene.add(key);
  const rim = new PointLight(colours.accent, 18, 20); rim.position.set(-4, -2, 3); scene.add(rim);
  const step = make(scene, colours);
  const clock = new Clock();
  let on = false, raf = 0;
  function size() {
    const w = el.clientWidth || 1, h = el.clientHeight || 1;
    renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix();
  }
  function frame() {
    raf = 0;
    if (!on) return;
    step(clock.getElapsedTime());
    renderer.render(scene, cam);
    raf = requestAnimationFrame(frame);
  }
  size();
  step(0.6); renderer.render(scene, cam);                 // one frame always (reduced motion stops here)
  el.setAttribute('data-hoola-3d-on', '');
  if (still) return;
  const io = new IntersectionObserver(es => {
    on = es[0].isIntersecting && !document.hidden;
    if (on && !raf) { clock.getDelta(); raf = requestAnimationFrame(frame); }
  });
  io.observe(el);
  document.addEventListener('visibilitychange', () => {
    on = !document.hidden && on;
    if (!document.hidden && !raf) raf = requestAnimationFrame(frame);
  });
  window.addEventListener('resize', size, { passive: true });
}

function start() { document.querySelectorAll('[data-hoola-3d]').forEach(el => { try { mount(el); } catch (e) { el.setAttribute('data-hoola-3d-off', ''); } }); }
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
window.HoolaHero3D = { scenes: Object.keys(SCENES), start };
