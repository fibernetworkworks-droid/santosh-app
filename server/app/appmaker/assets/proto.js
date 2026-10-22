/* Hoola app prototype runtime (v0.128.1). No network, no storage. Screens are <section class="scr" data-screen="id">.
   Navigation: data-go="screen" (push or tab switch), data-back, data-drawer (side bar), data-sheet="id" / data-close,
   data-fab-toggle (speed dial / FAB menu), data-toast="text", data-toggle, .chips[data-single] .chip, .seg > button,
   .stepper (- n +), .add-btn. Motion: data-m = stagger pop float pulse count number_roll tilt flip carousel3d parallax
   reveal typewriter wiggle bounce jelly shake confetti draw ... ; screen transitions from body tr-<name>.
   3D: .obj3d[data-shape] with three.js when present. Light / dark: data-mode button or ?m=dark|light.
   URL: ?s=<screen>&p=android|ios&m=dark|light&shot=1 (screenshot mode: no motion, no timers). */
(function () {
  'use strict';
  var q = new URLSearchParams(location.search);
  var body = document.body, frame = document.querySelector('.frame');
  var shot = q.get('shot') === '1';
  if (shot) body.classList.add('shot');
  var reduce = shot || (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  var each = function (sel, fn, root) { Array.prototype.forEach.call((root || document).querySelectorAll(sel), fn); };
  var screens = {};
  each('.scr[data-screen]', function (s) { screens[s.getAttribute('data-screen')] = s; });
  var tabs = Array.prototype.map.call(document.querySelectorAll('[data-tabbtn]'), function (b) { return b.getAttribute('data-tabbtn'); });
  var stack = [], current = null, lastTab = tabs[0] || null, timer = null, lastTap = null;
  var toast = document.querySelector('.toast');
  var trans = ((body.className.match(/\btr-([\w]+)/) || [])[1]) || 'fade_through';

  function platform(p) {
    if (p !== 'android' && p !== 'ios') return;
    body.classList.remove('p-android', 'p-ios');
    body.classList.add('p-' + p);
    each('[data-plat]', function (b) { b.classList.toggle('on', b.getAttribute('data-plat') === p); });
  }

  function mode(m) {           // m = 'dark' | 'light' | 'toggle'
    var base = body.getAttribute('data-base') || 'light';
    var alt = m === 'toggle' ? !body.classList.contains('mode-alt') : (m === 'alt' || (m && m !== base && m !== 'base'));
    body.classList.toggle('mode-alt', !!alt);
    var now = alt ? (base === 'light' ? 'dark' : 'light') : base;
    each('[data-mode]', function (b) { b.textContent = now === 'dark' ? 'Light' : 'Dark'; });
    each('.obj3d', function (o) { if (o._hk3d) o._hk3d.recolor(); });
  }

  function closeAll() {
    each('.sheet.open,.scrim.open,.drawer.open,.scrim-d.open,.fabx.open', function (e) { e.classList.remove('open'); });
  }

  // ---------------------------------------------------------------- micro motion when a screen shows
  function counts(scr) {
    each('[data-m="count"][data-to],[data-m="number_roll"][data-to]', function (el) {
      var to = parseFloat(el.getAttribute('data-to')) || 0, suf = el.getAttribute('data-suffix') || '', pre = el.getAttribute('data-prefix') || '';
      if (reduce) { el.textContent = pre + to.toLocaleString('en-IN') + suf; return; }
      var t0 = null;
      function step(t) {
        if (!t0) t0 = t;
        var k = Math.min(1, (t - t0) / 900), v = Math.round(to * (1 - Math.pow(1 - k, 3)));
        el.textContent = pre + v.toLocaleString('en-IN') + suf;
        if (k < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }, scr);
  }

  function typewriter(scr) {
    each('[data-m="typewriter"]', function (el) {
      var full = el.getAttribute('data-text') || el.textContent;
      el.setAttribute('data-text', full);
      if (reduce) { el.textContent = full; return; }
      var i = 0; el.textContent = '';
      (function tick() { el.textContent = full.slice(0, ++i); if (i < full.length) setTimeout(tick, 32); })();
    }, scr);
  }

  function draw(scr) {
    each('[data-m="draw"] path,[data-m="draw"] line,[data-m="draw"] polyline,[data-m="route_draw"] path', function (p) {
      if (reduce || !p.getTotalLength) return;
      var L = p.getTotalLength();
      p.style.transition = 'none'; p.style.strokeDasharray = L; p.style.strokeDashoffset = L;
      void p.getBoundingClientRect();
      p.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(.2,.8,.2,1)'; p.style.strokeDashoffset = '0';
    }, scr);
  }

  function confetti(scr) {
    if (reduce || !scr.querySelector('[data-m="confetti"]')) return;
    var cols = [getComputedStyle(body).getPropertyValue('--c-primary'), getComputedStyle(body).getPropertyValue('--c-accent'), '#FFD166', '#06D6A0'];
    for (var i = 0; i < 34; i++) {
      var b = document.createElement('i');
      b.className = 'confetti-bit';
      b.style.left = (Math.random() * 100) + '%';
      b.style.background = cols[i % cols.length];
      b.style.animationDelay = (Math.random() * 0.4) + 's';
      scr.appendChild(b);
      setTimeout(function (x) { return function () { x.remove(); }; }(b), 2300);
    }
  }

  function reveal(scr) {
    var root = scr.querySelector('.body');
    var els = scr.querySelectorAll('[data-m="reveal"]');
    if (!els.length) return;
    if (reduce || !('IntersectionObserver' in window)) { each('[data-m="reveal"]', function (e) { e.classList.remove('reveal-wait'); }, scr); return; }
    var io = new IntersectionObserver(function (en) {
      en.forEach(function (x) { if (x.isIntersecting) { x.target.classList.add('reveal-in'); io.unobserve(x.target); } });
    }, { root: root, threshold: 0.12 });
    Array.prototype.forEach.call(els, function (e) { e.classList.add('reveal-wait'); e.classList.remove('reveal-in'); io.observe(e); });
  }

  function carousel(c, step) {
    var kids = Array.prototype.slice.call(c.children), n = kids.length;
    c._i = ((c._i || 0) + (step || 0) + n) % n;
    kids.forEach(function (k, i) {
      var d = ((i - c._i) % n + n) % n; if (d > n / 2) d -= n;
      k.style.transform = 'translateX(' + (d * 58) + '%) translateZ(' + (-Math.abs(d) * 160) + 'px) rotateY(' + (-d * 28) + 'deg)';
      k.style.opacity = Math.abs(d) > 2 ? 0 : 1 - Math.abs(d) * 0.25;
      k.style.zIndex = 10 - Math.abs(d);
    });
  }

  function once(scr) {
    each('[data-m="wiggle"],[data-m="bounce"],[data-m="jelly"]', function (el) {
      if (reduce) return;
      var k = 'm-' + el.getAttribute('data-m'); el.classList.remove(k); void el.offsetWidth; el.classList.add(k);
    }, scr);
    each('.carousel3d', function (c) { carousel(c, 0); }, scr);
  }

  function enter(scr, mode) {
    var cls = ['t-enter-push', 't-enter-pop', 't-enter-fade', 't-in-axis_x', 't-in-axis_y', 't-in-axis_z', 't-in-zoom', 't-in-sheet',
      't-in-container', 't-in-reveal', 't-in-cube', 't-in-flip', 't-in-curl'];
    cls.forEach(function (c) { scr.classList.remove(c); });
    if (reduce || !mode || mode === 'instant') return;
    void scr.offsetWidth;
    if (mode === 'pop') { scr.classList.add('t-enter-pop'); return; }
    if (mode === 'tab') { scr.classList.add('t-enter-fade'); return; }
    var ios = body.classList.contains('p-ios');
    var t = trans;
    if (t === 'push') { scr.classList.add(ios ? 't-enter-push' : 't-in-axis_x'); return; }
    if (t === 'fade_through') { scr.classList.add(ios ? 't-enter-push' : 't-enter-fade'); return; }
    if ((t === 'container' || t === 'reveal') && lastTap) {
      var fr = frame.getBoundingClientRect(), r = lastTap;
      scr.style.setProperty('--ct', Math.max(0, r.top - fr.top) + 'px');
      scr.style.setProperty('--cb', Math.max(0, fr.bottom - r.bottom) + 'px');
      scr.style.setProperty('--cl', Math.max(0, r.left - fr.left) + 'px');
      scr.style.setProperty('--cr', Math.max(0, fr.right - r.right) + 'px');
      scr.style.setProperty('--rx', ((r.left + r.width / 2 - fr.left) / fr.width * 100) + '%');
      scr.style.setProperty('--ry', ((r.top + r.height / 2 - fr.top) / fr.height * 100) + '%');
    }
    scr.classList.add('t-in-' + t);
  }

  function show(id, mode) {
    var scr = screens[id];
    if (!scr) return false;
    closeAll();
    if (current && screens[current] && current !== id) screens[current].classList.remove('on');
    scr.classList.add('on');
    enter(scr, mode);
    var tabbed = scr.hasAttribute('data-tabbed');
    frame.classList.toggle('has-tabs', tabbed);
    frame.classList.toggle('has-bar', !!scr.querySelector(':scope > .bar'));   // its own action bar: no FAB over it
    if (tabbed) lastTab = id;
    each('[data-tabbtn]', function (b) { b.classList.toggle('on', b.getAttribute('data-tabbtn') === lastTab); });
    each('[data-tabbtn-d]', function (b) { b.classList.toggle('on', b.getAttribute('data-tabbtn-d') === id); });
    var b = scr.querySelector('.body');
    if (b && mode !== 'pop') b.scrollTop = 0;
    scr.classList.remove('scrolled');
    current = id;
    counts(scr); typewriter(scr); draw(scr); reveal(scr); once(scr); confetti(scr); init3d(scr);
    if (scr.hasAttribute('data-auto') && !shot) {
      clearTimeout(timer);
      timer = setTimeout(function () { if (current === id) go(scr.getAttribute('data-auto'), true); }, 1400);
    }
    if (!shot) try { history.replaceState(null, '', '?s=' + encodeURIComponent(id) + (q.get('p') ? '&p=' + q.get('p') : '')); } catch (e) { /* preview frame */ }
    return true;
  }

  function go(id, replace) {
    if (!screens[id]) { say('Yeh screen abhi plan mein nahi hai'); return; }
    if (tabs.indexOf(id) >= 0) { stack = [id]; show(id, 'tab'); return; }
    if (replace) stack[stack.length - 1] = id; else stack.push(id);
    show(id, 'push');
  }

  function back() {
    if (stack.length > 1) { stack.pop(); show(stack[stack.length - 1], 'pop'); }
    else if (lastTab && current !== lastTab) { stack = [lastTab]; show(lastTab, 'pop'); }
  }

  function say(text) {
    if (!toast || !text) return;
    toast.textContent = text;
    toast.classList.add('show');
    clearTimeout(say.t);
    say.t = setTimeout(function () { toast.classList.remove('show'); }, 1800);
  }

  function bumpCart() {
    each('[data-cart] .badge-dot, .badge-dot[data-cart]', function (d) {
      d.textContent = String((parseInt(d.textContent, 10) || 0) + 1);
      d.classList.remove('badge-bump'); void d.offsetWidth; d.classList.add('badge-bump');
    });
  }

  function ripple(e, el) {
    if (reduce || !body.classList.contains('p-android')) return;
    var r = el.getBoundingClientRect(), s = document.createElement('span'), d = Math.max(r.width, r.height);
    s.className = 'ripple';
    s.style.width = s.style.height = d + 'px';
    s.style.left = (e.clientX - r.left - d / 2) + 'px'; s.style.top = (e.clientY - r.top - d / 2) + 'px';
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    el.style.overflow = 'hidden';
    el.appendChild(s);
    setTimeout(function () { s.remove(); }, 520);
  }

  // ---------------------------------------------------------------- 3D objects (three.js, only when the page has .obj3d)
  function css(v) { return (getComputedStyle(body).getPropertyValue(v) || '#888').trim(); }
  function init3d(scr) {
    if (!window.THREE) return;
    each('.obj3d', function (o) {
      if (o._hk3d) { o._hk3d.render(); return; }
      var T = window.THREE, w = o.clientWidth || 300, h = o.clientHeight || 300;
      var r;
      try { r = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true }); } catch (e) { return; }
      r.setPixelRatio(Math.min(2, window.devicePixelRatio || 1)); r.setSize(w, h); o.appendChild(r.domElement);
      var scene = new T.Scene(), cam = new T.PerspectiveCamera(36, w / h, 0.1, 50);
      cam.position.set(0, 0.6, 5.2); cam.lookAt(0, 0, 0);
      scene.add(new T.HemisphereLight(0xffffff, 0x444466, 1.1));
      var dl = new T.DirectionalLight(0xffffff, 1.2); dl.position.set(3, 5, 4); scene.add(dl);
      var mat = new T.MeshStandardMaterial({ color: css('--c-primary'), roughness: 0.35, metalness: 0.15 });
      var mat2 = new T.MeshStandardMaterial({ color: css('--c-accent'), roughness: 0.4, metalness: 0.1 });
      var g = new T.Group(), shape = o.getAttribute('data-shape') || 'box', m;
      if (shape === 'sphere') m = new T.Mesh(new T.SphereGeometry(1.25, 48, 32), mat);
      else if (shape === 'cylinder') m = new T.Mesh(new T.CylinderGeometry(1, 1, 1.9, 48), mat);
      else if (shape === 'torus') m = new T.Mesh(new T.TorusGeometry(1.05, 0.38, 32, 80), mat);
      else if (shape === 'gem') m = new T.Mesh(new T.OctahedronGeometry(1.4, 0), mat);
      else if (shape === 'phone') { m = new T.Mesh(new T.BoxGeometry(1.3, 2.5, 0.16), mat); var sc = new T.Mesh(new T.BoxGeometry(1.16, 2.3, 0.02), mat2); sc.position.z = 0.09; g.add(sc); }
      else if (shape === 'bottle') { m = new T.Mesh(new T.CylinderGeometry(0.62, 0.7, 1.9, 40), mat); var nk = new T.Mesh(new T.CylinderGeometry(0.26, 0.4, 0.6, 32), mat2); nk.position.y = 1.2; g.add(nk); }
      else if (shape === 'cake') { m = new T.Mesh(new T.CylinderGeometry(1.3, 1.3, 0.8, 48), mat); var top = new T.Mesh(new T.CylinderGeometry(0.85, 0.85, 0.6, 48), mat2); top.position.y = 0.7; g.add(top); }
      else m = new T.Mesh(new T.BoxGeometry(1.7, 1.7, 1.7), mat);
      g.add(m); g.rotation.set(0.35, 0.6, 0); scene.add(g);
      var spin = o.hasAttribute('data-spin') && !reduce;
      var api = {
        render: function () { r.render(scene, cam); },
        recolor: function () { mat.color.set(css('--c-primary')); mat2.color.set(css('--c-accent')); api.render(); }
      };
      o._hk3d = api;
      (function loop() { if (spin && o.isConnected) { g.rotation.y += 0.012; requestAnimationFrame(loop); } api.render(); })();
      var drag = null;
      o.addEventListener('pointerdown', function (e) { drag = { x: e.clientX, y: e.clientY, ry: g.rotation.y, rx: g.rotation.x }; });
      window.addEventListener('pointerup', function () { drag = null; });
      o.addEventListener('pointermove', function (e) { if (!drag) return; g.rotation.y = drag.ry + (e.clientX - drag.x) / 80; g.rotation.x = drag.rx + (e.clientY - drag.y) / 120; api.render(); });
    }, scr);
  }

  // ---------------------------------------------------------------- input
  document.addEventListener('pointerdown', function (e) {
    var el = e.target.closest('.btn,.li,.card,.tab,.dr-item,.fab-main,.chip');
    if (el) ripple(e, el);
    var g = e.target.closest('[data-go]');
    if (g) lastTap = g.getBoundingClientRect();
  });
  document.addEventListener('pointermove', function (e) {
    var t = e.target.closest('[data-m="tilt"]');
    if (!t || reduce) return;
    var r = t.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
    t.style.transform = 'perspective(700px) rotateY(' + (x * 14) + 'deg) rotateX(' + (-y * 14) + 'deg)';
  });
  document.addEventListener('pointerleave', function (e) {
    if (e.target && e.target.matches && e.target.matches('[data-m="tilt"]')) e.target.style.transform = '';
  }, true);
  document.addEventListener('scroll', function (e) {
    var b = e.target;
    if (!b.classList || !b.classList.contains('body')) return;
    var scr = b.closest('.scr');
    scr.classList.toggle('scrolled', b.scrollTop > 24);
    if (!reduce) each('[data-m="parallax"]', function (p) { p.style.transform = 'translateY(' + (b.scrollTop * 0.3) + 'px)'; }, scr);
  }, true);

  document.addEventListener('click', function (e) {
    var t = e.target;
    var a = t.closest('a[href="#"]');
    if (a) e.preventDefault();
    var plat = t.closest('[data-plat]');
    if (plat) { platform(plat.getAttribute('data-plat')); return; }
    if (t.closest('[data-mode]')) { mode('toggle'); return; }
    if (t.closest('[data-drawer]')) {
      var d = document.getElementById('hk-drawer');
      if (d) { d.classList.add('open'); document.querySelector('.scrim-d').classList.add('open'); }
      return;
    }
    var ft = t.closest('[data-fab-toggle]');
    if (ft) { ft.closest('.fabx').classList.toggle('open'); return; }
    var st = t.closest('.stepper button');
    if (st) {
      var box = st.parentNode, out = box.querySelector('output,span'), n = parseInt(out && out.textContent, 10) || 0;
      n = st === box.firstElementChild ? Math.max(0, n - 1) : n + 1;
      if (out) out.textContent = String(n);
      if (st !== box.firstElementChild) bumpCart();
      return;
    }
    var add = t.closest('.add-btn');
    if (add) { add.textContent = '✓'; add.classList.add('on'); bumpCart(); say('Cart mein daal diya'); return; }
    var fl = t.closest('.flip');
    if (fl && !t.closest('[data-go],button,a')) { fl.classList.toggle('on'); return; }
    var c3 = t.closest('.carousel3d');
    if (c3) { carousel(c3, (e.clientX - c3.getBoundingClientRect().left) > c3.clientWidth / 2 ? 1 : -1); return; }
    var mm = t.closest('[data-m="wiggle"],[data-m="bounce"],[data-m="jelly"],[data-m="shake"]');
    if (mm && !reduce) { var k = 'm-' + mm.getAttribute('data-m'); mm.classList.remove(k); void mm.offsetWidth; mm.classList.add(k); }
    var chip = t.closest('.chip');
    if (chip && !chip.hasAttribute('data-go')) {
      var grp = chip.closest('.chips');
      if (grp && grp.hasAttribute('data-single')) each('.chip', function (c) { c.classList.remove('on'); }, grp);
      chip.classList.toggle('on');
    }
    var seg = t.closest('.seg > *');
    if (seg) { Array.prototype.forEach.call(seg.parentNode.children, function (c) { c.classList.remove('on'); }); seg.classList.add('on'); }
    var tg = t.closest('[data-toggle]');
    if (tg) tg.classList.toggle('on');
    var sh = t.closest('[data-sheet]');
    if (sh) {
      var s = document.getElementById(sh.getAttribute('data-sheet'));
      if (s) {
        var scrim = s.parentNode.querySelector(':scope > .scrim');
        if (!scrim) { scrim = document.createElement('div'); scrim.className = 'scrim'; s.parentNode.insertBefore(scrim, s); scrim.setAttribute('data-close', ''); }
        scrim.classList.add('open'); s.classList.add('open');
      }
      return;
    }
    if (t.closest('[data-fab-close]')) each('.fabx.open', function (f) { f.classList.remove('open'); });
    var cl = t.closest('[data-close]');
    if (cl) closeAll();
    var ts = t.closest('[data-toast]');
    if (ts) say(ts.getAttribute('data-toast'));
    if (t.closest('[data-back]')) { back(); return; }
    var g = t.closest('[data-go]');
    if (g && !g.hasAttribute('disabled')) { go(g.getAttribute('data-go')); }
  });

  document.addEventListener('change', function (e) {
    if (e.target.matches('[data-consent]')) {
      var scr = e.target.closest('.scr');
      each('[data-needs-consent]', function (b) {
        if (e.target.checked) b.removeAttribute('disabled'); else b.setAttribute('disabled', '');
      }, scr);
    }
  });

  platform(q.get('p') || (body.classList.contains('p-ios') ? 'ios' : 'android'));
  mode(q.get('m') || '');
  var start = q.get('s') || body.getAttribute('data-start') || Object.keys(screens)[0];
  if (!screens[start]) start = body.getAttribute('data-home') || Object.keys(screens)[0];
  if (tabs.indexOf(start) < 0 && lastTab && start !== 'splash') stack = [lastTab, start]; else stack = [start];
  show(start, 'instant');
  window.HoolaProto = {
    show: function (id) { stack = [id]; return show(id, 'instant'); }, platform: platform, mode: mode, go: go,
    drawer: function (open) { var d = document.getElementById('hk-drawer'); if (!d) return false; d.classList.toggle('open', !!open); document.querySelector('.scrim-d').classList.toggle('open', !!open); return true; },
    fab: function (open) { var f = document.querySelector('.fabx'); if (!f) return false; f.classList.toggle('open', !!open); return true; },
    current: function () { return current; }
  };
})();
