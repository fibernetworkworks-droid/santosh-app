/* v0.999.169 HOOLA INTERACTIVE - her live agent on her own website: one line,
   <script src="https://<hoola>/static/interactive/agent.js" data-agent="ia_pub_..." defer></script>
   A small round button opens a panel; the visitor types (or speaks, where the browser can hear), the agent answers in
   words and in its Hoola voice, only from the facts she wrote. It says it is an AI before the first question. Nothing
   is stored in the visitor's browser. The page's own styles never reach it (a shadow root). */
(function () {
  'use strict';
  var me = document.currentScript || document.querySelector('script[data-agent]');
  if (!me) return;
  var token = me.getAttribute('data-agent') || '';
  var base = new URL(me.src, location.href).origin;
  var api = base + '/api/interactive/pub/' + encodeURIComponent(token);
  var host = document.createElement('div');
  host.style.cssText = 'position:fixed;right:18px;bottom:18px;z-index:2147483000';
  var root = host.attachShadow ? host.attachShadow({mode: 'open'}) : host;
  root.innerHTML = '<style>' +
    ':host{all:initial}*{box-sizing:border-box;font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}' +
    '.fab{width:56px;height:56px;border-radius:50%;border:0;background:#1A1918;color:#fff;cursor:pointer;display:grid;place-items:center;box-shadow:0 6px 20px rgba(0,0,0,.25)}' +
    '.box{position:absolute;right:0;bottom:68px;width:min(340px,calc(100vw - 36px));max-height:min(520px,75vh);background:#fff;color:#1A1918;border:1px solid #E3E1DD;border-radius:18px;box-shadow:0 18px 50px rgba(0,0,0,.18);display:flex;flex-direction:column;overflow:hidden}' +
    '.box[hidden]{display:none}.hd{padding:12px 14px;border-bottom:1px solid #ECEAE7;display:flex;align-items:center;gap:8px}.hd b{flex:1;font-weight:600}' +
    '.x{border:0;background:none;width:32px;height:32px;border-radius:8px;cursor:pointer;color:#6B6964}.log{flex:1;overflow-y:auto;padding:12px 14px;display:flex;flex-direction:column;gap:8px}' +
    '.ai{font-size:12px;color:#6B6964}.me{align-self:flex-end;background:#F2F1EE;border-radius:14px;padding:7px 11px;max-width:85%;white-space:pre-wrap;overflow-wrap:anywhere}' +
    '.it{background:#F7F5FE;border-radius:14px;padding:7px 11px;max-width:90%;overflow-wrap:anywhere}.f{display:flex;gap:8px;padding:10px;border-top:1px solid #ECEAE7}' +
    'input{flex:1;min-width:0;height:40px;border:1px solid #DAD7D1;border-radius:20px;padding:0 14px;outline:0}input:focus{border-color:#5B45E0}' +
    '.go{height:40px;padding:0 14px;border:0;border-radius:20px;background:#1A1918;color:#fff;cursor:pointer}.go:disabled{opacity:.5}' +
    '@media (prefers-color-scheme:dark){.box{background:#1F1E1C;color:#ECEAE6;border-color:#3A3936}.me{background:#2C2B28}.it{background:#2A2640}.hd,.f{border-color:#3A3936}input{background:#141413;color:#ECEAE6;border-color:#3A3936}}' +
    '</style><div class="box" hidden role="dialog" aria-label="Ask the assistant"><div class="hd"><b class="nm">Assistant</b>' +
    '<button class="x" type="button" aria-label="Close">✕</button></div><div class="log" aria-live="polite"></div>' +
    '<form class="f"><input aria-label="Your question" placeholder="Ask a question" maxlength="400"><button class="go" type="submit">Ask</button></form></div>' +
    '<button class="fab" type="button" aria-label="Ask the assistant"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 5h16v11H9l-5 4z"/></svg></button>';
  var $ = function (s) { return root.querySelector(s); };
  var box = $('.box'), log = $('.log'), input = $('input'), go = $('.go'), audio = new Audio(), info = null;
  function line(cls, text) { var d = document.createElement('div'); d.className = cls; d.textContent = text; log.appendChild(d); log.scrollTop = log.scrollHeight; return d; }
  function req(path, body) {
    return fetch(api + path, {method: body ? 'POST' : 'GET', headers: body ? {'Content-Type': 'application/json'} : {},
      body: body ? JSON.stringify(body) : undefined, credentials: 'omit'})
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.detail || 'Not available'); return j; }); });
  }
  function opened() {
    if (info) return;
    req('').then(function (j) {
      info = j; $('.nm').textContent = j.name || 'Assistant';
      line('ai', j.ai || 'You are talking to an AI assistant.');
      if (j.opening) line('it', j.opening);
    }).catch(function (e) { line('ai', e.message); });
  }
  $('.fab').addEventListener('click', function () { box.hidden = !box.hidden; if (!box.hidden) { opened(); input.focus(); } });
  $('.x').addEventListener('click', function () { box.hidden = true; audio.pause(); });
  $('form').addEventListener('submit', function (e) {
    e.preventDefault();
    var t = input.value.trim(); if (!t) return;
    input.value = ''; line('me', t); go.disabled = true;
    var wait = line('ai', '…');
    req('/ask', {text: t}).then(function (j) {
      wait.remove(); line('it', j.answer || '');
      if (j.audio) { audio.src = 'data:' + (j.mime || 'audio/wav') + ';base64,' + j.audio; audio.play().catch(function () {}); }
    }).catch(function (err) { wait.textContent = err.message; }).then(function () { go.disabled = false; input.focus(); });
  });
  (document.body || document.documentElement).appendChild(host);
})();
