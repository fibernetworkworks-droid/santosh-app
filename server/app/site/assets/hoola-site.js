/* Hoola site runtime v1 (MIT, Newtika). Motion graphics + small helpers for every site Hoola builds.
   Nothing here loads from the network. Motion: transform / opacity only; content is visible without JS;
   elements already on screen at load are never hidden (no LCP delay); prefers-reduced-motion = calm static site.
   Attributes: data-m="reveal|stagger|split|count|draw|parallax|marquee|magnetic|tilt|zoom|float|progress"
   options: data-m-dir (up|down|left|right|scale|blur), data-m-delay (ms), data-m-dur (ms), data-m-dist (px),
   data-m-split (words|chars), data-to / data-from / data-suffix / data-prefix (count), data-speed (parallax, -1..1). */
(function () {
  'use strict';
  var d = document, root = d.documentElement, W = window;
  var still = W.matchMedia && W.matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.classList.add(still ? 'hm-still' : 'hm-live');
  var EASE = 'cubic-bezier(.2,.7,.2,1)';
  function $$(s, el) { return Array.prototype.slice.call((el || d).querySelectorAll(s)); }
  function num(v, f) { var n = parseFloat(v); return isNaN(n) ? f : n; }
  function inView(el) { var r = el.getBoundingClientRect(); return r.top < W.innerHeight && r.bottom > 0; }
  function onEnter(el, fn, once) {
    if (!('IntersectionObserver' in W)) { fn(); return; }
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { fn(); if (once !== false) io.disconnect(); } });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    io.observe(el);
  }
  function from(el) {
    var dir = el.getAttribute('data-m-dir') || 'up', dist = num(el.getAttribute('data-m-dist'), 28);
    return { up: 'translate3d(0,' + dist + 'px,0)', down: 'translate3d(0,-' + dist + 'px,0)',
      left: 'translate3d(' + dist + 'px,0,0)', right: 'translate3d(-' + dist + 'px,0,0)',
      scale: 'scale(.94)', blur: 'translate3d(0,' + (dist / 2) + 'px,0)' }[dir] || 'translate3d(0,' + dist + 'px,0)';
  }
  function play(el, delay) {
    if (!el.animate) { el.style.opacity = 1; el.style.transform = 'none'; return; }
    var blur = (el.getAttribute('data-m-dir') || '') === 'blur';
    var a = el.animate([{ opacity: 0, transform: from(el), filter: blur ? 'blur(8px)' : 'none' },
      { opacity: 1, transform: 'none', filter: 'none' }],
      { duration: num(el.getAttribute('data-m-dur'), 750), delay: delay || num(el.getAttribute('data-m-delay'), 0),
        easing: EASE, fill: 'both' });
    a.onfinish = function () { el.style.opacity = ''; el.classList.remove('hm-pre'); };
  }
  var M = {
    reveal: function (el) {
      if (inView(el)) return;
      el.classList.add('hm-pre');
      onEnter(el, function () { play(el); });
    },
    stagger: function (el) {
      var kids = Array.prototype.slice.call(el.children), gap = num(el.getAttribute('data-m-gap'), 90);
      if (inView(el)) return;
      kids.forEach(function (k) { k.classList.add('hm-pre'); if (!k.getAttribute('data-m-dir')) k.setAttribute('data-m-dir', el.getAttribute('data-m-dir') || 'up'); });
      onEnter(el, function () { kids.forEach(function (k, i) { play(k, i * gap); }); });
    },
    split: function (el) {
      var mode = el.getAttribute('data-m-split') || 'words', text = el.textContent;
      if (!text || el.children.length) return;
      el.setAttribute('aria-label', text.trim());
      var parts = mode === 'chars' ? Array.from(text) : text.split(/(\s+)/);
      el.textContent = '';
      var spans = [];
      parts.forEach(function (p) {
        if (/^\s+$/.test(p)) { el.appendChild(d.createTextNode(p)); return; }
        var w = d.createElement('span'); w.className = 'hm-w'; w.setAttribute('aria-hidden', 'true');
        var i = d.createElement('span'); i.className = 'hm-wi'; i.textContent = p; w.appendChild(i); el.appendChild(w); spans.push(i);
      });
      var go = function () {
        spans.forEach(function (s, n) {
          if (s.animate) s.animate([{ transform: 'translate3d(0,105%,0)' }, { transform: 'none' }],
            { duration: num(el.getAttribute('data-m-dur'), 800), delay: n * (mode === 'chars' ? 22 : 70), easing: EASE, fill: 'both' });
        });
      };
      if (inView(el)) go(); else onEnter(el, go);
    },
    count: function (el) {
      var to = num(el.getAttribute('data-to'), num(el.textContent.replace(/[^\d.]/g, ''), 0));
      var fr = num(el.getAttribute('data-from'), 0), pre = el.getAttribute('data-prefix') || '', suf = el.getAttribute('data-suffix') || '';
      var dec = (String(to).split('.')[1] || '').length;
      var fmt = function (v) { return pre + Number(v.toFixed(dec)).toLocaleString('en-IN') + suf; };
      el.textContent = fmt(to);
      onEnter(el, function () {
        var t0 = null, dur = num(el.getAttribute('data-m-dur'), 1400);
        var step = function (t) {
          if (!t0) t0 = t;
          var k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
          el.textContent = fmt(fr + (to - fr) * e);
          if (k < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      });
    },
    draw: function (el) {
      $$('path,line,polyline,circle,rect,ellipse', el).forEach(function (p) {
        var L = p.getTotalLength ? p.getTotalLength() : 0;
        if (!L) return;
        p.style.strokeDasharray = L; p.style.strokeDashoffset = L;
        onEnter(el, function () {
          if (p.animate) p.animate([{ strokeDashoffset: L }, { strokeDashoffset: 0 }],
            { duration: num(el.getAttribute('data-m-dur'), 1600), easing: EASE, fill: 'forwards' });
          else p.style.strokeDashoffset = 0;
        });
      });
    },
    parallax: function (el) { par.push({ el: el, k: num(el.getAttribute('data-speed'), 0.2) }); },
    marquee: function (el) {
      var track = el.firstElementChild;
      if (!track || track.getAttribute('data-hm-dup')) return;
      track.setAttribute('data-hm-dup', '1');
      var copy = track.cloneNode(true); copy.setAttribute('aria-hidden', 'true'); el.appendChild(copy);
      el.classList.add('hm-marquee');
    },
    magnetic: function (el) {
      if (W.matchMedia && !W.matchMedia('(hover:hover)').matches) return;
      el.addEventListener('pointermove', function (e) {
        var r = el.getBoundingClientRect(), x = e.clientX - r.left - r.width / 2, y = e.clientY - r.top - r.height / 2;
        el.style.transform = 'translate3d(' + x * 0.18 + 'px,' + y * 0.25 + 'px,0)';
      });
      el.addEventListener('pointerleave', function () { el.style.transform = ''; });
    },
    tilt: function (el) {
      if (W.matchMedia && !W.matchMedia('(hover:hover)').matches) return;
      el.addEventListener('pointermove', function (e) {
        var r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        el.style.transform = 'perspective(800px) rotateX(' + (-y * 6) + 'deg) rotateY(' + (x * 6) + 'deg)';
      });
      el.addEventListener('pointerleave', function () { el.style.transform = ''; });
    },
    zoom: function (el) { el.classList.add('hm-zoom'); onEnter(el, function () { el.classList.add('hm-zoom-in'); }); },
    float: function (el) { el.classList.add('hm-float'); },
    progress: function (el) { prog.push(el); }
  };
  var par = [], prog = [], ticking = false;
  function frame() {
    ticking = false;
    var vh = W.innerHeight;
    par.forEach(function (p) {
      var r = p.el.getBoundingClientRect();
      if (r.bottom < -200 || r.top > vh + 200) return;
      var c = (r.top + r.height / 2 - vh / 2) * -p.k;
      p.el.style.transform = 'translate3d(0,' + c.toFixed(1) + 'px,0)';
    });
    prog.forEach(function (el) {
      var host = el.closest('section') || d.body, r = host.getBoundingClientRect();
      var k = Math.max(0, Math.min(1, (vh - r.top) / (r.height + vh)));
      el.style.transform = 'scaleX(' + k.toFixed(3) + ')';
    });
  }
  function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }

  function motion() {
    if (still) return;
    $$('[data-m]').forEach(function (el) {
      (el.getAttribute('data-m') || '').split(/\s+/).forEach(function (k) {
        if (M[k]) { try { M[k](el); } catch (e) { /* one effect never breaks the page */ } }
      });
    });
    if (par.length || prog.length) { W.addEventListener('scroll', onScroll, { passive: true }); frame(); }
  }

  // ------------------------------------------------------------ helpers every site uses
  function nav() {
    var btn = d.querySelector('.hs-menu'), menu = d.querySelector('.hs-links');
    if (btn && menu) btn.addEventListener('click', function () {
      var open = root.classList.toggle('hs-open'); btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    $$('.hs-links a').forEach(function (a) { a.addEventListener('click', function () { root.classList.remove('hs-open'); }); });
    var head = d.querySelector('.hs-head');
    if (head) W.addEventListener('scroll', function () { head.classList.toggle('hs-scrolled', W.scrollY > 12); }, { passive: true });
    $$('[data-year]').forEach(function (el) { el.textContent = new Date().getFullYear(); });
  }
  function forms() {
    $$('form[data-hoola-form]').forEach(function (f) {
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        var out = f.querySelector('.hs-form-msg'), btn = f.querySelector('[type=submit]'), data = {};
        new FormData(f).forEach(function (v, k) { data[k] = String(v).slice(0, 2000); });
        data.page = location.pathname;
        if (btn) btn.disabled = true;
        fetch(f.getAttribute('data-endpoint'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
          .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
          .then(function () { f.reset(); if (out) { out.textContent = f.getAttribute('data-ok') || 'Thank you! We will call you soon.'; out.className = 'hs-form-msg ok'; } })
          .catch(function () { if (out) { out.textContent = f.getAttribute('data-fail') || 'Could not send. Please call or WhatsApp us.'; out.className = 'hs-form-msg bad'; } })
          .then(function () { if (btn) btn.disabled = false; });
      });
    });
  }
  function lightbox() {
    var imgs = $$('[data-lightbox] img');
    if (!imgs.length) return;
    var box = d.createElement('div'); box.className = 'hs-lightbox'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true');
    box.innerHTML = '<button class="hs-lb-x" aria-label="Close">×</button><img alt="">';
    d.body.appendChild(box);
    var big = box.querySelector('img');
    var close = function () { box.classList.remove('on'); };
    box.addEventListener('click', function (e) { if (e.target !== big) close(); });
    d.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
    imgs.forEach(function (im) {
      im.style.cursor = 'zoom-in';
      im.addEventListener('click', function () { big.src = im.currentSrc || im.src; big.alt = im.alt; box.classList.add('on'); });
    });
  }
  function compare() {
    $$('[data-compare]').forEach(function (c) {
      var r = c.querySelector('input[type=range]');
      if (r) r.addEventListener('input', function () { c.style.setProperty('--hs-pos', r.value + '%'); });
    });
  }
  // v0.301 the map / the video load only when the visitor taps (no third party before she asks)
  function embeds() {
    $$('.hs-map, .hs-video').forEach(function (fig) {
      var b = fig.querySelector('.hs-load');
      if (!b) return;
      b.addEventListener('click', function () {
        var f = d.createElement('iframe'), yt = fig.getAttribute('data-hs-yt');
        f.src = yt ? 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(yt) + '?autoplay=1&rel=0' : fig.getAttribute('data-hs-map');
        f.title = yt ? (fig.getAttribute('data-title') || 'Video') : 'Map';
        f.loading = 'lazy'; f.referrerPolicy = 'strict-origin-when-cross-origin';
        if (yt) { f.allow = 'autoplay; encrypted-media; picture-in-picture'; f.allowFullscreen = true; }
        fig.classList.add('on'); fig.innerHTML = ''; fig.appendChild(f);
      });
    });
  }
  // v0.301 booking: her REAL free times from Hoola; the visitor asks for one, the owner confirms it
  function booking() {
    $$('form[data-hoola-book]').forEach(function (f) {
      var ep = f.getAttribute('data-endpoint'), box = f.querySelector('.hs-slots'), btn = f.querySelector('[type=submit]'),
        out = f.querySelector('.hs-form-msg');
      var none = function () { box.innerHTML = ''; var p = d.createElement('p'); p.className = 'muted'; p.textContent = f.getAttribute('data-none'); box.appendChild(p); if (btn) btn.disabled = true; };
      if (!ep) { none(); return; }
      fetch(ep + '/slots').then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); }).then(function (j) {
        var list = (j && j.slots) || [];
        if (!list.length) return none();
        box.innerHTML = '';
        list.forEach(function (s, i) {
          var l = d.createElement('label'), r = d.createElement('input'), sp = d.createElement('span');
          l.className = 'hs-slot'; r.type = 'radio'; r.name = 'slot'; r.value = s.slot; r.required = true;
          sp.textContent = s.label; l.appendChild(r); l.appendChild(sp); box.appendChild(l);
        });
      }).catch(none);
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        var data = {};
        new FormData(f).forEach(function (v, k) { data[k] = String(v).slice(0, 2000); });
        data.page = location.pathname;
        if (btn) btn.disabled = true;
        fetch(ep + '/book', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
          .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
          .then(function () { f.reset(); if (out) { out.textContent = f.getAttribute('data-ok'); out.className = 'hs-form-msg ok'; } })
          .catch(function () { if (out) { out.textContent = f.getAttribute('data-fail'); out.className = 'hs-form-msg bad'; } if (btn) btn.disabled = false; });
      });
    });
  }
  // ------------------------------------------------------------ v0.313 big sites: grouped menu + site search
  function groups() {
    $$('.hs-dd').forEach(function (li) {
      var b = li.querySelector('.hs-ddb');
      if (!b) return;
      b.addEventListener('click', function (e) {
        e.stopPropagation();
        var open = b.getAttribute('aria-expanded') !== 'true';
        $$('.hs-ddb').forEach(function (o) { if (o !== b) o.setAttribute('aria-expanded', 'false'); });
        b.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    });
    d.addEventListener('click', function (e) {
      if (!e.target.closest || !e.target.closest('.hs-dd')) $$('.hs-ddb').forEach(function (o) { o.setAttribute('aria-expanded', 'false'); });
    });
    d.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') $$('.hs-ddb[aria-expanded="true"]').forEach(function (o) { o.setAttribute('aria-expanded', 'false'); o.focus(); });
    });
  }
  function search() {
    var btn = d.querySelector('.hs-search-b');
    if (!btn) return;
    var root = btn.getAttribute('data-root') || './', box = null, list = null, input = null, data = null;
    function close() { if (box) { box.hidden = true; btn.focus(); } }
    function draw(q) {
      while (list.firstChild) list.removeChild(list.firstChild);
      q = (q || '').trim().toLowerCase();
      var hits = (data || []).filter(function (x) { return !q || (x.t + ' ' + x.d).toLowerCase().indexOf(q) >= 0; }).slice(0, 30);
      if (!hits.length) { var none = d.createElement('li'); none.className = 'hs-s-none'; none.textContent = q ? 'Nothing found.' : ''; list.appendChild(none); return; }
      hits.forEach(function (x) {
        var li = d.createElement('li'), a = d.createElement('a'), t = d.createElement('b'), s = d.createElement('span');
        a.href = root + x.u; t.textContent = x.t; s.textContent = x.d || '';
        a.appendChild(t); if (x.d) a.appendChild(s); li.appendChild(a); list.appendChild(li);
      });
    }
    function open() {
      if (!box) {
        box = d.createElement('div'); box.className = 'hs-search'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true');
        box.setAttribute('aria-label', 'Search this site');
        var inner = d.createElement('div'); inner.className = 'hs-search-in wrap';
        input = d.createElement('input'); input.type = 'search'; input.placeholder = 'Search this site'; input.setAttribute('aria-label', 'Search this site');
        var x = d.createElement('button'); x.type = 'button'; x.className = 'hs-search-x'; x.textContent = 'Close';
        list = d.createElement('ul'); list.className = 'hs-search-r';
        inner.appendChild(input); inner.appendChild(x); inner.appendChild(list); box.appendChild(inner); d.body.appendChild(box);
        x.addEventListener('click', close);
        box.addEventListener('click', function (e) { if (e.target === box) close(); });
        box.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
        input.addEventListener('input', function () { draw(input.value); });
      }
      box.hidden = false; input.focus();
      if (data) { draw(input.value); return; }
      fetch(root + 'assets/search.json').then(function (r) { return r.json(); })
        .then(function (j) { data = j; draw(input.value); }).catch(function () { data = []; draw(''); });
    }
    btn.addEventListener('click', open);
  }
  function start() { nav(); groups(); search(); forms(); lightbox(); compare(); embeds(); booking(); motion(); }
  W.HoolaSite = { start: start };      // v0.305 the React export starts it again after a route change
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start); else start();
})();
