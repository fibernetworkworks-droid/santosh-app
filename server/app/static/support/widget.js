/* Hoola Customer Support - the website chat (G5 of docs/SUPPORT_GLOBAL_PLAN.md).
   <script src="https://HOOLA/static/support/widget.js" data-hoola-support="KEY" async></script>
   Optional for a signed-in user: data-user-id="42" data-user-hash="<HMAC-SHA256 of the id with your identity secret, made on
   your server>" data-name="Ana". data-mode="page" = the full-page chat (used by /support/chat/KEY for app web views).
   No outside libraries, no eval; everything inside its own shadow root so her site's styles never collide. */
(function () {
  'use strict';
  var me = document.currentScript || document.querySelector('script[data-hoola-support]');
  if (!me || window.__hoolaSupport) return;
  window.__hoolaSupport = true;
  var KEY = me.getAttribute('data-hoola-support') || '';
  var BASE = new URL(me.src, location.href).origin;
  var PAGE = me.getAttribute('data-mode') === 'page';
  var q = new URLSearchParams(location.search);
  var USER = me.getAttribute('data-user-id') || (PAGE ? q.get('user_id') || '' : '');
  var HASH = me.getAttribute('data-user-hash') || (PAGE ? q.get('user_hash') || '' : '');
  var NAME = me.getAttribute('data-name') || (PAGE ? q.get('name') || '' : '');
  var store = 'hoola.support.' + KEY + (USER ? '.u.' + USER : '');
  var st = {token: '', cfg: null, msgs: [], open: PAGE, timer: 0, busy: false};

  function api(method, path, body, form) {
    var o = {method: method, headers: {}};
    if (form) o.body = form; else if (body) { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(body); }
    return fetch(BASE + '/api/support/web/' + encodeURIComponent(KEY) + path, o).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok) throw new Error(j.detail || 'Something went wrong.'); return j; });
    });
  }
  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    for (var k in (attrs || {})) e.setAttribute(k, attrs[k]);
    if (text) e.textContent = text;
    return e;
  }

  var host = el('div', {id: 'hoola-support'});
  var root = host.attachShadow({mode: 'open'});
  var css = el('style');
  css.textContent = ':host{all:initial}*{box-sizing:border-box;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}' +
    '.fab{position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;border:0;cursor:pointer;color:#fff;box-shadow:0 6px 20px rgba(0,0,0,.2);font-size:24px;z-index:2147483000}' +
    '.box{position:fixed;right:20px;bottom:88px;width:360px;max-width:calc(100vw - 32px);height:520px;max-height:calc(100vh - 120px);background:#fff;color:#1b1b1f;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.22);display:flex;flex-direction:column;overflow:hidden;z-index:2147483000}' +
    '.box.page{position:static;width:100%;max-width:none;height:100vh;max-height:none;border-radius:0;box-shadow:none}' +
    '.hd{padding:14px 16px;color:#fff;font-weight:600;font-size:15px;display:flex;align-items:center;justify-content:space-between}' +
    '.x{background:none;border:0;color:#fff;font-size:20px;cursor:pointer;line-height:1}' +
    '.msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;background:#f7f7f8}' +
    '.m{max-width:82%;padding:9px 12px;border-radius:12px;font-size:14px;line-height:1.45;white-space:pre-wrap;word-wrap:break-word}' +
    '.m.you{align-self:flex-end;color:#fff}.m.hoola,.m.team{align-self:flex-start;background:#fff;border:1px solid #e6e6ea}' +
    '.who{display:block;font-size:11px;opacity:.65;margin-bottom:2px}' +
    '.bar{display:flex;gap:6px;padding:10px;border-top:1px solid #ececf0;align-items:center}' +
    '.in{flex:1;min-width:0;border:1px solid #d9d9e0;border-radius:10px;padding:10px;font-size:14px;outline:none}' +
    '.in:focus{border-color:#888}.b{border:0;border-radius:10px;padding:10px 12px;font-size:14px;cursor:pointer;color:#fff}' +
    '.ic{background:#f0f0f3;color:#333}.row{display:flex;gap:6px;padding:0 10px 10px;flex-wrap:wrap}' +
    '.cm{padding:10px;border-top:1px solid #ececf0;display:flex;flex-direction:column;gap:6px}.err{color:#b42318;font-size:12.5px;padding:0 12px 8px}' +
    '.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}';
  root.appendChild(css);

  var fab = el('button', {class: 'fab', type: 'button', 'aria-label': 'Open the chat'}, '\u{1F4AC}');
  var box = el('div', {class: 'box' + (PAGE ? ' page' : ''), role: 'dialog', 'aria-label': 'Chat'});
  var hd = el('div', {class: 'hd'});
  var title = el('span', {}, 'Chat with us');
  var x = el('button', {class: 'x', type: 'button', 'aria-label': 'Close the chat'}, '×');
  hd.appendChild(title); if (!PAGE) hd.appendChild(x);
  var list = el('div', {class: 'msgs', 'aria-live': 'polite'});
  var err = el('div', {class: 'err', role: 'alert'});
  var bar = el('form', {class: 'bar'});
  var lab = el('label', {class: 'sr', for: 'hsIn'}, 'Your message');
  var input = el('input', {class: 'in', id: 'hsIn', placeholder: 'Write a message…', autocomplete: 'off', maxlength: '2000'});
  var send = el('button', {class: 'b', type: 'submit'}, 'Send');
  bar.appendChild(lab); bar.appendChild(input); bar.appendChild(send);
  var extra = el('div', {class: 'row'});
  var fileBtn = el('button', {class: 'b ic', type: 'button'}, 'Add a file');
  var callBtn = el('button', {class: 'b ic', type: 'button'}, 'Call me');
  var pick = el('input', {type: 'file', accept: 'image/png,image/jpeg,image/gif,application/pdf', hidden: ''});
  var cm = el('form', {class: 'cm', hidden: ''});
  var ph = el('input', {class: 'in', placeholder: 'Your phone number with country code', inputmode: 'tel', 'aria-label': 'Your phone number'});
  var note = el('input', {class: 'in', placeholder: 'What should we call about? (optional)', 'aria-label': 'What should we call about'});
  var cmGo = el('button', {class: 'b', type: 'submit'}, 'Ask for a call');
  cm.appendChild(ph); cm.appendChild(note); cm.appendChild(cmGo);
  box.appendChild(hd); box.appendChild(list); box.appendChild(err); box.appendChild(cm); box.appendChild(extra); box.appendChild(bar); box.appendChild(pick);
  if (!PAGE) root.appendChild(fab);
  box.hidden = !PAGE;
  root.appendChild(box);
  (document.body || document.documentElement).appendChild(host);

  function colour(c) { [fab, hd, send, cmGo].forEach(function (e) { e.style.background = c; }); st.colour = c; }
  function draw() {
    list.textContent = '';
    if (st.cfg && st.cfg.greeting) { var g = el('div', {class: 'm hoola'}, st.cfg.greeting); list.appendChild(g); }
    st.msgs.forEach(function (m) {
      var d = el('div', {class: 'm ' + m.from});
      if (m.from === 'you') d.style.background = st.colour || '#5B45E0';
      if (m.from !== 'you') d.appendChild(el('span', {class: 'who'}, m.from === 'team' ? 'Our team' : 'Assistant'));
      d.appendChild(document.createTextNode(m.text));
      list.appendChild(d);
    });
    list.scrollTop = list.scrollHeight;
  }
  function say(e) { err.textContent = e ? (e.message || String(e)) : ''; }
  function ready() { if (!st.ready) st.ready = start().catch(function (e) { st.ready = null; throw e; }); return st.ready; }
  function start() {
    var saved = ''; try { saved = localStorage.getItem(store) || ''; } catch (e) { saved = ''; }
    return api('POST', '/session', {user_id: USER, user_hash: HASH, name: NAME}).then(function (r) {
      st.cfg = r; title.textContent = r.title || 'Chat with us'; colour(r.colour || '#5B45E0');
      st.token = USER ? r.token : (saved || r.token);
      try { localStorage.setItem(store, st.token); } catch (e) { /* private mode */ }
      extra.textContent = '';
      if (r.files) extra.appendChild(fileBtn);
      if (r.call_me) extra.appendChild(callBtn);
      if (USER || !saved) { st.msgs = r.messages || []; draw(); return; }
      return poll();
    });
  }
  function poll() {
    return api('GET', '/messages?token=' + encodeURIComponent(st.token)).then(function (r) { st.msgs = r.messages || []; draw(); });
  }
  function loop() {
    clearInterval(st.timer);
    if (st.open) st.timer = setInterval(function () { if (!st.busy) poll().catch(function () {}); }, 4000);
  }
  fab.addEventListener('click', function () {
    st.open = !st.open; box.hidden = !st.open;
    if (st.open) { (st.cfg ? poll() : ready()).then(function () { input.focus(); }).catch(say); }
    loop();
  });
  x.addEventListener('click', function () { st.open = false; box.hidden = true; loop(); fab.focus(); });
  bar.addEventListener('submit', function (e) {
    e.preventDefault();
    var t = input.value.trim(); if (!t || st.busy) return;
    st.busy = true; send.disabled = true; say('');
    st.msgs.push({from: 'you', text: t}); draw(); input.value = '';
    ready().then(function () { return api('POST', '/messages', {token: st.token, text: t, name: NAME}); }).then(function (r) { st.msgs = r.messages || st.msgs; draw(); })
      .catch(say).then(function () { st.busy = false; send.disabled = false; input.focus(); });
  });
  fileBtn.addEventListener('click', function () { pick.click(); });
  pick.addEventListener('change', function () {
    var f = pick.files[0]; pick.value = ''; if (!f) return;
    if (f.size > 5 * 1024 * 1024) { say('The file is bigger than 5 MB.'); return; }
    var fd = new FormData(); fd.append('token', st.token); fd.append('file', f, f.name);
    api('POST', '/file', null, fd).then(function (r) { st.msgs = r.messages || st.msgs; draw(); say(''); }).catch(say);
  });
  callBtn.addEventListener('click', function () { cm.hidden = !cm.hidden; if (!cm.hidden) ph.focus(); });
  cm.addEventListener('submit', function (e) {
    e.preventDefault();
    api('POST', '/callme', {token: st.token, phone: ph.value, note: note.value, name: NAME})
      .then(function (r) { st.msgs = r.messages || st.msgs; draw(); cm.hidden = true; say(''); }).catch(say);
  });
  if (PAGE) { ready().then(loop).catch(say); }
})();
