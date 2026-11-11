/* v0.777 HOOLA FLOW as its OWN page (/console/flow; owner: "NOW SAME FOR HOOLA FLOW --- CHECK DESIGN AND MAKE IT SAME AS
   WISPERFLOW"). Like Hoola Code: a full-screen app with only its own sidebar, the same sign-in as the console (its token in
   this browser), the same /api/flow + /api/kaan routes, the same strict CSP. The page itself is flow.js (HoolaFlow); this
   file only signs her in and hands it api / esc / toast / say. "Put in the Hoola chat" leaves the text for the console's
   chat box (never sent) and opens the console. */
'use strict';
(function () {
  const $ = s => document.querySelector(s);
  const esc = v => (v == null ? '' : String(v)).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  let TOKEN = ''; try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch (e) { /* private window */ }
  if (!TOKEN) { location.replace('/console/'); return; }
  async function api(method, path, body, opts) {
    const {raw = false, form = null} = opts || {};
    const headers = {Authorization: 'Bearer ' + TOKEN}; let payload;
    if (form) payload = form; else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    if (raw) { if (!r.ok) throw new Error(`The server refused the request (${r.status})`); return r; }
    let data = null; try { data = await r.json(); } catch (e) { /* no body */ }
    if (!r.ok) { const bad = data && Array.isArray(data.detail) && data.detail[0];
      throw new Error((data && ((typeof data.detail === 'string' ? data.detail : '') || data.error || data.message)) || (bad ? String(bad.msg) : '') || `The server refused the request (${r.status})`); }
    return data;
  }
  function toast(msg, bad) { const t = $('#toast'); t.textContent = String(msg); t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200); }
  function say(text) {
    try { localStorage.setItem('hoola.flow.toChat', String(text || '')); } catch (e) { toast('This browser could not hand the text over.', true); return; }
    location.assign('/console/');
  }
  window.HoolaFlow({api, esc, toast, say}).open($('#flow'));
})();
