/* Hoola website editor (v0.295, MIT, Newtika). Loaded ONLY in the edit preview (/api/site-preview/<token>/__edit/...).
   Hover = outline, click = edit: words are typed in place (Enter / click outside saves, Esc cancels); pictures, links
   and "remove" go to the console / phone through postMessage (or the phone's HoolaEdit channel). This page holds no
   login: it only says WHAT she changed; the console / app sends it to Hoola with her login. */
(function () {
  'use strict';
  var css = document.createElement('style');
  css.textContent = '[data-e]{cursor:pointer}[data-e]:hover{outline:2px dashed rgba(124,92,255,.9);outline-offset:3px}' +
    '[data-e][contenteditable]{outline:2px solid #7c5cff;outline-offset:3px;cursor:text;background:rgba(124,92,255,.06)}' +
    '#hoola-ebar{position:fixed;z-index:2147483647;display:none;gap:4px;padding:4px;background:#1c1830;border-radius:10px;' +
    'box-shadow:0 8px 24px rgba(0,0,0,.25);font:500 13px system-ui,sans-serif}#hoola-ebar button{all:unset;cursor:pointer;color:#fff;' +
    'padding:6px 10px;border-radius:7px}#hoola-ebar button:hover,#hoola-ebar button:focus-visible{background:#3a3260}' +
    '.hoola-ehint{position:fixed;left:50%;bottom:14px;transform:translateX(-50%);z-index:2147483647;background:#1c1830;color:#fff;' +
    'font:500 13px system-ui,sans-serif;padding:8px 14px;border-radius:999px;box-shadow:0 8px 24px rgba(0,0,0,.25)}' +
    '[data-m]{opacity:1!important;transform:none!important;filter:none!important}';
  document.head.appendChild(css);
  var bar = document.createElement('div'); bar.id = 'hoola-ebar'; bar.setAttribute('role', 'toolbar');
  document.body.appendChild(bar);
  var hint = document.createElement('div'); hint.className = 'hoola-ehint';
  hint.textContent = 'Edit mode: kisi bhi cheez par click karke badliye';
  document.body.appendChild(hint);
  var cur = null, before = '';

  function send(msg) {
    msg.hoola = 'edit'; msg.y = Math.round(window.scrollY);
    msg.page = location.pathname.replace(/^.*\/__edit\//, '');
    try { if (window.HoolaEdit && window.HoolaEdit.postMessage) { window.HoolaEdit.postMessage(JSON.stringify(msg)); return; } } catch (e) {}
    try { window.parent.postMessage(msg, '*'); } catch (e) {}
  }
  function where(el) { var s = el.closest('section[data-k]'); return s ? s.getAttribute('data-k') : ''; }
  function text(el) { return (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim(); }
  function place(el) {
    var r = el.getBoundingClientRect();
    bar.style.display = 'flex';
    bar.style.top = Math.max(6, r.top - 44) + 'px';
    bar.style.left = Math.max(6, Math.min(r.left, window.innerWidth - 260)) + 'px';
  }
  function tools(el) {
    bar.innerHTML = '';
    var add = function (label, fn) { var b = document.createElement('button'); b.type = 'button'; b.textContent = label;
      b.addEventListener('mousedown', function (e) { e.preventDefault(); }); b.addEventListener('click', fn); bar.appendChild(b); };
    var k = where(el), e = el.getAttribute('data-e');
    if (el.tagName === 'A') add('Link', function () { send({t: 'link', k: k, e: e, href: el.getAttribute('href') || '', text: text(el)}); });
    if (el.tagName !== 'IMG') add('AI se badlo', function () { send({t: 'ai', k: k, e: e, text: text(el)}); });
    add('Hatao', function () { done(false); send({t: 'remove', k: k, e: e, text: text(el)}); });
    place(el);
  }
  function done(save) {
    if (!cur) return;
    var el = cur; cur = null;
    el.removeAttribute('contenteditable');
    bar.style.display = 'none';
    var now = text(el);
    if (save && now && now !== before) send({t: 'text', k: where(el), e: el.getAttribute('data-e'), value: now, old: before});
    else if (!save) el.innerText = before;
  }
  document.addEventListener('click', function (ev) {
    if (bar.contains(ev.target)) return;
    var el = ev.target.closest && ev.target.closest('[data-e]');
    if (cur && el === cur) return;
    ev.preventDefault(); ev.stopPropagation();
    if (cur) done(true);
    if (!el || !where(el)) return;
    if (el.tagName === 'IMG' || el.closest('picture')) {
      send({t: 'image', k: where(el), e: el.getAttribute('data-e'), img: el.getAttribute('data-hoola-img') || ''});
      return;
    }
    cur = el; before = text(el);
    el.setAttribute('contenteditable', 'plaintext-only');
    if (el.contentEditable !== 'plaintext-only') el.setAttribute('contenteditable', 'true');
    el.focus();
    tools(el);
  }, true);
  document.addEventListener('submit', function (ev) { ev.preventDefault(); }, true);
  document.addEventListener('keydown', function (ev) {
    if (!cur) return;
    if (ev.key === 'Escape') { ev.preventDefault(); done(false); }
    else if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); done(true); }
  });
  window.addEventListener('scroll', function () { if (cur) place(cur); }, {passive: true});
  var m = /[#&]y=(\d+)/.exec(location.hash);
  if (m) window.addEventListener('load', function () { window.scrollTo(0, +m[1]); });
  send({t: 'ready'});
})();
