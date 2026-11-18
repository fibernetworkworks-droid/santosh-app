/* v0.827 Hoola App Engine - the app's SHELL (Hoola's own code, the same for every app).
   Every App Engine app runs inside a sealed frame (sandbox, its own blank origin): it cannot read storage, cookies or
   any other app on this address. This shell is the only part with the app's address: it keeps the visitor's Hoola
   Cloud sign-in (localStorage, one key per app; in the Studio preview only in memory) and makes the Cloud calls the
   app asks for through src/lib/hoola.ts (postMessage). It also passes the Studio's preview messages both ways and
   keeps the address bar in step with the app's page. */
(() => {
  'use strict';
  const meta = document.querySelector('meta[name="hoola-app"]');
  let cfg = {};
  try { cfg = JSON.parse(meta.getAttribute('content')); } catch (e) { cfg = {}; }
  const base = String(cfg.base || '/');
  const cloud = String(cfg.cloud || '');
  const KEY = 'hoola.cloud.' + String(cfg.key || '');
  let mem = '';
  const tok = {
    get() { try { return localStorage.getItem(KEY) || mem; } catch (e) { return mem; } },
    set(v) { mem = v || ''; try { if (v) localStorage.setItem(KEY, v); else localStorage.removeItem(KEY); } catch (e) { /* in-memory */ } },
  };
  const rest = location.pathname.startsWith(base) ? location.pathname.slice(base.length) : '';
  const f = document.createElement('iframe');
  f.title = String(cfg.title || 'App');
  f.setAttribute('sandbox', 'allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-modals allow-downloads');
  f.setAttribute('referrerpolicy', 'no-referrer');
  f.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;border:0;display:block;background:#fff';
  f.src = base + '__app/' + rest.replace(/^__app\//, '') + location.search;
  document.body.appendChild(f);

  // v0.999.7 B4 the one backend: phone OTP, authenticator 2FA, sign-in sessions, approvals and functions too
  const OPS = {schema: 1, me: 1, list: 1, signup: 1, signin: 1, signout: 1, create: 1, update: 1, remove: 1,
    otp_start: 1, otp_verify: 1, '2fa_login': 1, sessions: 1, session_end: 1, signout_all: 1, '2fa_start': 1,
    '2fa_confirm': 1, '2fa_off': 1, export: 1, delete_me: 1, approvals: 1, decide: 1, fn: 1};
  async function cloudCall(op, args) {
    if (!cloud || !OPS[op]) throw new Error('Hoola Cloud is not reachable here.');
    const t = tok.get();
    const r = await fetch(cloud + '/' + op, {method: 'POST', credentials: 'omit', cache: 'no-store',
      headers: Object.assign({'Content-Type': 'application/json'}, t ? {Authorization: 'Bearer ' + t} : {}),
      body: JSON.stringify(args || {})});
    let data = null;
    try { data = await r.json(); } catch (e) { data = null; }
    if (!r.ok) {
      if (r.status === 401 && t && (op === 'me' || op === 'list')) tok.set('');
      throw new Error((data && (data.detail || data.error)) || ('Hoola Cloud answered ' + r.status));
    }
    if (data && data.token) { tok.set(data.token); delete data.token; }
    if (op === 'signout' || op === 'signout_all' || op === 'delete_me') tok.set('');
    return data;
  }

  addEventListener('message', async e => {
    const d = e.data || {};
    if (e.source === f.contentWindow) {
      if (d.hoola === 'cloud') {
        let reply;
        try { reply = {hoola: 'cloud-r', id: d.id, ok: true, data: await cloudCall(String(d.op), d.args)}; }
        catch (er) { reply = {hoola: 'cloud-r', id: d.id, ok: false, error: String(er && er.message || er)}; }
        f.contentWindow.postMessage(reply, '*');
        return;
      }
      if (d.hoola === 'nav') {
        try { history.replaceState(null, '', base + String(d.path || '').replace(/^\//, '')); } catch (er) { /* sealed preview */ }
        return;
      }
      if (d.hoola === 'ae' && window.parent !== window) window.parent.postMessage(d, '*');   // up to the Studio
      return;
    }
    if (window.parent !== window && e.source === window.parent && d.hoola === 'ae-cmd') f.contentWindow.postMessage(d, '*');
  });
})();
