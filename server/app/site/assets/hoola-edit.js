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
    '[data-m]{opacity:1!important;transform:none!important;filter:none!important}' +
    /* v0.795 YEH WALA: select / comment / draw modes, selection outline, pins */
    'html.hoola-m-select [data-e]:hover,html.hoola-m-comment [data-e]:hover{outline:1px solid #6d4aff;outline-offset:2px;background-color:rgba(109,74,255,.04)}' +
    'html.hoola-m-select,html.hoola-m-select *{cursor:crosshair!important}html.hoola-m-view [data-e]:hover{outline:none}html.hoola-m-view [data-e]{cursor:default}' +
    '.hoola-sel{outline:1px solid #6d4aff!important;outline-offset:2px;background-color:rgba(109,74,255,.04)!important}' +
    '#hoola-tip{position:fixed;z-index:2147483647;pointer-events:none;display:none;background:#6d4aff;color:#fff;font:500 12px system-ui,sans-serif;padding:3px 8px;border-radius:999px;white-space:nowrap}' +
    '.hoola-pin{position:absolute;z-index:2147483646;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50% 50% 50% 4px;background:#6d4aff;color:#fff;font:600 11px/22px system-ui,sans-serif;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.25);pointer-events:none}' +
    '.hoola-pin.done{background:#8a8796}';
  document.head.appendChild(css);
  var bar = document.createElement('div'); bar.id = 'hoola-ebar'; bar.setAttribute('role', 'toolbar');
  document.body.appendChild(bar);
  var hint = document.createElement('div'); hint.className = 'hoola-ehint';
  hint.textContent = 'Edit mode: kisi bhi cheez par click karke badliye';
  document.body.appendChild(hint);
  var cur = null, before = '';
  var MODE = 'text', SEL = [];              // v0.795: text (the v0.295 behaviour) | select | comment | view (draw on top)
  var tip = document.createElement('div'); tip.id = 'hoola-tip'; document.body.appendChild(tip);
  var HINTS = {text: 'Edit mode: kisi bhi cheez par click karke badliye', select: 'Select: click a part of the page (Ctrl / Shift to add more)',
    comment: 'Comment: click the part your note is about', view: 'Draw: mark the page, then send it to Hoola'};
  function setMode(m) {
    if (!HINTS[m]) return;
    if (cur) done(true);
    hide();
    MODE = m;
    var cl = document.documentElement.classList;
    ['text', 'select', 'comment', 'view'].forEach(function (x) { cl.remove('hoola-m-' + x); });
    cl.add('hoola-m-' + m);
    hint.textContent = HINTS[m];
    tip.style.display = 'none';
  }
  function nameOf(el) {
    var t = el.tagName.toLowerCase(), w = text(el).slice(0, 28);
    var kind = t === 'a' ? 'link' : t === 'button' ? 'button' : t === 'img' ? 'picture' : /^h[1-6]$/.test(t) ? 'heading' : 'text';
    return kind + (w ? " '" + w + "'" : '');
  }
  function paintSel() {
    document.querySelectorAll('.hoola-sel').forEach(function (x) { x.classList.remove('hoola-sel'); });
    SEL.forEach(function (s) {
      var sec = document.querySelector('section[data-k="' + s.k + '"]');
      var el = sec && sec.querySelector('[data-e="' + s.e + '"]');
      if (el) el.classList.add('hoola-sel');
    });
  }
  function pins(list) {
    document.querySelectorAll('.hoola-pin').forEach(function (x) { x.remove(); });
    (list || []).forEach(function (p) {
      var sec = document.querySelector('section[data-k="' + p.k + '"]');
      var el = sec && sec.querySelector('[data-e="' + p.e + '"]');
      if (!el) return;
      var r = el.getBoundingClientRect(), d = document.createElement('div');
      d.className = 'hoola-pin' + (p.done ? ' done' : ''); d.textContent = String(p.n);
      d.style.left = (r.left + window.scrollX) + 'px'; d.style.top = (r.top + window.scrollY) + 'px';
      document.body.appendChild(d);
    });
  }
  window.addEventListener('message', function (ev) {      // commands from the Studio (only the page that holds this frame)
    if (ev.source !== window.parent) return;
    var d = ev.data || {};
    if (d.hoola !== 'edit-cmd') return;
    if (d.mode) setMode(d.mode);
    if (d.t === 'selected') { SEL = (d.items || []).map(function (x) { return {k: String(x.k), e: String(x.e)}; }); paintSel(); }
    if (d.t === 'pins') pins(d.pins);
    if (d.t === 'where') send({t: 'where', w: window.innerWidth, h: window.innerHeight});
  });
  document.addEventListener('mouseover', function (ev) {
    if (MODE !== 'select' && MODE !== 'comment') return;
    var el = ev.target.closest && ev.target.closest('[data-e]');
    if (!el || !where(el)) { tip.style.display = 'none'; return; }
    var r = el.getBoundingClientRect();
    tip.textContent = nameOf(el); tip.style.display = 'block';
    tip.style.left = Math.max(4, Math.min(r.left, window.innerWidth - 220)) + 'px';
    tip.style.top = Math.max(4, r.top - 24) + 'px';
  }, true);

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
    var media = isMedia(el);
    if (el.tagName === 'IMG') add('Photo badlo', function () { hide(); send({t: 'image', k: k, e: e, img: el.getAttribute('data-hoola-img') || ''}); });
    if (el.tagName === 'A') add('Link', function () { send({t: 'link', k: k, e: e, href: el.getAttribute('href') || '', text: text(el)}); });
    if (el.tagName !== 'IMG' && !media) add('AI se badlo', function () { send({t: 'ai', k: k, e: e, text: text(el)}); });
    add('+ Jodo', function () { done(true); hide(); send({t: 'add', k: k, e: e, text: text(el)}); });   // v0.338 photo / video / audio / file
    add('Hatao', function () { done(false); hide(); send({t: 'remove', k: k, e: e, text: text(el) || (media ? 'video / audio' : 'photo')}); });
    place(el);
  }
  function hide() { bar.style.display = 'none'; }
  function isMedia(el) { return el.hasAttribute('data-hoola-media') || el.hasAttribute('data-hs-yt') || el.hasAttribute('data-hoola-video'); }
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
    if (MODE !== 'text') {                                  // v0.795 select / comment / view never type or follow links
      ev.preventDefault(); ev.stopPropagation();
      var pick = ev.target.closest && ev.target.closest('[data-e]');
      if (!pick || !where(pick) || MODE === 'view') return;
      var it = {k: where(pick), e: pick.getAttribute('data-e'), text: text(pick).slice(0, 200), tag: pick.tagName.toLowerCase(), name: nameOf(pick)};
      if (MODE === 'comment') { send({t: 'comment', k: it.k, e: it.e, text: it.text, name: it.name}); return; }
      var i = SEL.findIndex(function (s) { return s.k === it.k && s.e === it.e; });
      if (ev.ctrlKey || ev.metaKey || ev.shiftKey) { if (i >= 0) SEL.splice(i, 1); else if (SEL.length < 8) SEL.push(it); }
      else SEL = i >= 0 && SEL.length === 1 ? [] : [it];
      paintSel();
      send({t: 'select', items: SEL});
      return;
    }
    var el = ev.target.closest && ev.target.closest('[data-e]');
    if (cur && el === cur) return;
    ev.preventDefault(); ev.stopPropagation();
    if (cur) done(true);
    if (!el || !where(el)) return;
    if (el.tagName === 'IMG' || isMedia(el)) { tools(el); return; }   // v0.338 photos / videos get the toolbar too
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
  setMode('text');
  send({t: 'ready'});
})();
