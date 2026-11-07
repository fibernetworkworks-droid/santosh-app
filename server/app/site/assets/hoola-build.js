/* v0.664 ASLI SAMAY - the live canvas inside the Web Studio's sandboxed preview.
   The Studio sends each section's half-written HTML / CSS as Opus writes it; this grows it in its place on the real page.
   Half-written code never runs: scripts, frames, event handlers and javascript: links are removed before it is shown,
   and the page itself is sandboxed without the Studio's origin. Only messages from the parent window are read. */
(function () {
  'use strict';
  var P = window.parent;
  if (!P || P === window) return;
  var css = document.createElement('style');
  css.textContent = [
    '.hb-slot{position:relative;display:block}',
    '.hb-wait{min-height:180px;margin:12px 16px;border-radius:14px;background:linear-gradient(90deg,rgba(124,92,255,.06),rgba(124,92,255,.14),rgba(124,92,255,.06));background-size:200% 100%;animation:hbsh 1.6s linear infinite;display:flex;align-items:center;justify-content:center}',
    '.hb-ph span{font:600 13px/1.2 system-ui,sans-serif;color:rgba(60,50,110,.55);letter-spacing:.01em}',
    '.hb-live{outline:2px solid #7C5CFF;outline-offset:-2px;border-radius:4px}',
    '.hb-fix{outline-color:#E59E2B}',
    '.hb-tag{position:absolute;top:10px;left:10px;z-index:2147483000;background:#1B1030;color:#fff;font:600 12px/1 system-ui,sans-serif;padding:6px 9px;border-radius:7px;box-shadow:0 4px 14px rgba(0,0,0,.25);pointer-events:none;white-space:nowrap;max-width:80%;overflow:hidden;text-overflow:ellipsis}',
    '.hb-tag i{display:inline-block;width:7px;height:7px;border-radius:50%;background:#7CF0B5;margin-right:7px;vertical-align:1px;animation:hbp 1s ease-in-out infinite}',
    '.hb-think{min-height:140px}',
    '.hb-cursor{display:inline-block;width:.55em;height:1.05em;background:#7C5CFF;vertical-align:-.15em;margin-left:2px;animation:hbb 1s steps(2) infinite}',
    '.hb-new{animation:hbn 1.4s ease-out}',
    '.hb-slot .hm-pre{opacity:1!important}',
    '@keyframes hbsh{to{background-position:-200% 0}}@keyframes hbb{50%{opacity:0}}@keyframes hbp{50%{opacity:.35}}',
    '@keyframes hbn{from{box-shadow:inset 0 0 0 3px rgba(124,240,181,.9)}to{box-shadow:inset 0 0 0 3px rgba(124,240,181,0)}}',
    '@media (prefers-reduced-motion:reduce){.hb-wait,.hb-cursor,.hb-tag i,.hb-new{animation:none}}'
  ].join('\n');
  document.head.appendChild(css);

  var BAD = 'script,iframe,object,embed,frame,frameset,base,meta,link,noscript,template';
  function clean(html) {
    var t = document.createElement('template');
    t.innerHTML = html || '';
    var all = t.content.querySelectorAll(BAD);
    for (var i = 0; i < all.length; i++) all[i].remove();
    var els = t.content.querySelectorAll('*');
    for (var j = 0; j < els.length; j++) {
      var el = els[j];
      for (var k = el.attributes.length - 1; k >= 0; k--) {
        var a = el.attributes[k], n = a.name.toLowerCase(), v = String(a.value || '').replace(/\s+/g, '').toLowerCase();
        if (n.indexOf('on') === 0 || n === 'srcdoc' || n === 'formaction' ||
            ((n === 'href' || n === 'src' || n === 'action' || n === 'xlink:href') && (v.indexOf('javascript:') === 0 || v.indexOf('data:text') === 0))) {
          el.removeAttribute(a.name);
        }
      }
    }
    return t.content;
  }

  function slotEl(key, type) {
    var all = document.querySelectorAll('[data-slot]');
    for (var i = 0; i < all.length; i++) if (all[i].getAttribute('data-slot') === key) return all[i];
    var el = document.createElement('div');           // a section the canvas page did not know yet: it goes at the end
    el.className = 'hb-slot';
    el.setAttribute('data-slot', key);
    var main = document.querySelector('main') || document.body;
    var foot = main.querySelector('.hs-foot');
    main.insertBefore(el, foot || null);
    return el;
  }

  function styleFor(key, text) {
    var id = 'hb-css-' + key.replace(/[^\w-]/g, '_'), s = document.getElementById(id);
    if (!s) { s = document.createElement('style'); s.id = id; document.head.appendChild(s); }
    if (s.textContent !== text) s.textContent = text || '';
  }

  var lastScroll = 0;
  function show(d) {
    var el = slotEl(String(d.key || ''), d.type);
    var live = d.state === 'think' || d.state === 'write';
    el.classList.remove('hb-wait');
    var tag = el.querySelector(':scope > .hb-tag');
    if (live) {
      if (d.state === 'think' && !d.html) {
        if (!el.classList.contains('hb-think')) { el.innerHTML = ''; el.classList.add('hb-wait', 'hb-think'); el.appendChild(document.createElement('div')).className = 'hb-ph'; }
        el.querySelector('.hb-ph').innerHTML = '<span></span>';
        el.querySelector('.hb-ph span').textContent = 'Designing this section…';
      } else {
        el.classList.remove('hb-think');
        var frag = clean(d.html);
        var cur = document.createElement('span'); cur.className = 'hb-cursor'; cur.setAttribute('aria-hidden', 'true');
        var last = frag.lastElementChild;
        while (last && last.lastElementChild && !/^(IMG|SVG|BR|HR|INPUT)$/.test(last.lastElementChild.tagName)) last = last.lastElementChild;
        (last || frag).appendChild(cur);
        el.replaceChildren(frag);
      }
      if (d.css) styleFor(d.key, d.css);
      el.classList.add('hb-live');
      el.classList.toggle('hb-fix', d.kind === 'fix');
      tag = document.createElement('div'); tag.className = 'hb-tag';
      tag.appendChild(document.createElement('i'));
      tag.appendChild(document.createTextNode(String(d.label || 'Writing')));
      el.insertBefore(tag, el.firstChild);
      var now = Date.now();
      if (d.follow && now - lastScroll > 700) {
        lastScroll = now;
        var r = el.getBoundingClientRect();
        if (r.bottom > innerHeight - 40 || r.top < 0) {
          var y = window.scrollY + r.bottom - innerHeight + 80;
          window.scrollTo({top: Math.max(window.scrollY + r.top - 60, Math.min(y, window.scrollY + r.top - 60 + Math.max(0, r.height - innerHeight + 140))), behavior: 'smooth'});
        }
      }
    } else if (d.state === 'done' || d.state === 'error') {
      if (d.html != null) {
        el.replaceChildren(clean(d.html));
        if (d.css != null) styleFor(d.key, d.css);
      }
      el.classList.remove('hb-live', 'hb-fix', 'hb-think');
      if (d.state === 'done') { el.classList.remove('hb-new'); void el.offsetWidth; el.classList.add('hb-new'); }
    }
  }

  window.addEventListener('message', function (ev) {
    if (ev.source !== P) return;
    var d = ev.data;
    if (!d || d.hoola !== 'build') return;
    if (d.t === 'slot') show(d);
    else if (d.t === 'slots') { for (var i = 0; i < (d.slots || []).length; i++) show(d.slots[i]); }
  });
  P.postMessage({hoola: 'build', t: 'ready', path: location.pathname}, '*');
})();
