/* Hoola app prototype runtime (v0.128). No network, no storage. Screens are <section class="scr" data-screen="id">.
   Attributes: data-go="screen" (push or switch tab), data-back, data-sheet="id" / data-close, data-toast="text",
   data-toggle, .chips[data-single] .chip, .seg > button, .stepper (- n +), .add-btn, data-m="count" data-to="n".
   URL: ?s=<screen>&p=android|ios&shot=1 (screenshot mode: no motion, no splash timer). */
(function () {
  'use strict';
  var q = new URLSearchParams(location.search);
  var body = document.body, frame = document.querySelector('.frame');
  var shot = q.get('shot') === '1';
  if (shot) body.classList.add('shot');
  var reduce = shot || (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  var screens = {};
  Array.prototype.forEach.call(document.querySelectorAll('.scr[data-screen]'), function (s) { screens[s.getAttribute('data-screen')] = s; });
  var tabs = Array.prototype.map.call(document.querySelectorAll('[data-tabbtn]'), function (b) { return b.getAttribute('data-tabbtn'); });
  var stack = [], current = null, lastTab = tabs[0] || null, timer = null;
  var toast = document.querySelector('.toast');

  function platform(p) {
    if (p !== 'android' && p !== 'ios') return;
    body.classList.remove('p-android', 'p-ios');
    body.classList.add('p-' + p);
    Array.prototype.forEach.call(document.querySelectorAll('[data-plat]'), function (b) { b.classList.toggle('on', b.getAttribute('data-plat') === p); });
  }

  function closeSheets() {
    Array.prototype.forEach.call(document.querySelectorAll('.sheet.open,.scrim.open'), function (e) { e.classList.remove('open'); });
  }

  function counts(scr) {
    Array.prototype.forEach.call(scr.querySelectorAll('[data-m="count"][data-to]'), function (el) {
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
    });
  }

  function show(id, mode) {
    var scr = screens[id];
    if (!scr) return false;
    closeSheets();
    if (current && screens[current]) screens[current].classList.remove('on', 't-enter-push', 't-enter-pop', 't-enter-fade');
    scr.classList.remove('t-enter-push', 't-enter-pop', 't-enter-fade');
    scr.classList.add('on');
    if (!reduce && mode && mode !== 'instant') {
      var ios = body.classList.contains('p-ios');
      void scr.offsetWidth;
      scr.classList.add(mode === 'tab' ? 't-enter-fade' : mode === 'pop' ? 't-enter-pop' : (ios ? 't-enter-push' : 't-enter-fade'));
    }
    var tabbed = scr.hasAttribute('data-tabbed');
    frame.classList.toggle('has-tabs', tabbed);
    if (tabbed) lastTab = id;
    Array.prototype.forEach.call(document.querySelectorAll('[data-tabbtn]'), function (b) { b.classList.toggle('on', b.getAttribute('data-tabbtn') === lastTab); });
    var b = scr.querySelector('.body');
    if (b && mode !== 'pop') b.scrollTop = 0;
    current = id;
    counts(scr);
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
    Array.prototype.forEach.call(document.querySelectorAll('[data-cart] .badge-dot, .badge-dot[data-cart]'), function (d) {
      d.textContent = String((parseInt(d.textContent, 10) || 0) + 1);
      d.classList.remove('badge-bump'); void d.offsetWidth; d.classList.add('badge-bump');
    });
  }

  document.addEventListener('click', function (e) {
    var t = e.target;
    var a = t.closest('a[href="#"]');
    if (a) e.preventDefault();
    var plat = t.closest('[data-plat]');
    if (plat) { platform(plat.getAttribute('data-plat')); return; }
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
    var chip = t.closest('.chip');
    if (chip && !chip.hasAttribute('data-go')) {
      var grp = chip.closest('.chips');
      if (grp && grp.hasAttribute('data-single')) Array.prototype.forEach.call(grp.querySelectorAll('.chip'), function (c) { c.classList.remove('on'); });
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
    var cl = t.closest('[data-close]');
    if (cl) closeSheets();
    var ts = t.closest('[data-toast]');
    if (ts) say(ts.getAttribute('data-toast'));
    if (t.closest('[data-back]')) { back(); return; }
    var g = t.closest('[data-go]');
    if (g && !g.hasAttribute('disabled')) { go(g.getAttribute('data-go')); }
  });

  document.addEventListener('change', function (e) {
    if (e.target.matches('[data-consent]')) {
      var scr = e.target.closest('.scr');
      Array.prototype.forEach.call(scr.querySelectorAll('[data-needs-consent]'), function (b) {
        if (e.target.checked) b.removeAttribute('disabled'); else b.setAttribute('disabled', '');
      });
    }
  });

  platform(q.get('p') || (body.classList.contains('p-ios') ? 'ios' : 'android'));
  var start = q.get('s') || body.getAttribute('data-start') || Object.keys(screens)[0];
  if (!screens[start]) start = body.getAttribute('data-home') || Object.keys(screens)[0];
  if (tabs.indexOf(start) < 0 && lastTab && start !== 'splash') stack = [lastTab, start]; else stack = [start];
  show(start, 'instant');
  window.HoolaProto = { show: function (id) { stack = [id]; return show(id, 'instant'); }, platform: platform, go: go,
    current: function () { return current; } };
})();
