/* v0.768 HOOLA CODE as its OWN page (/console/code; owner: "CREATE A SEPERATE PAGE WITH ITS OWN SIDE BAR FOR HOOLA CODE").
   Like the Web Studio and the App Studio: a full-screen app with only its own sidebar, the same sign-in as the console
   (its token in this browser), the same /api/devsahayak routes, the same strict CSP. The page itself is code.js; this
   file only signs her in and hands it api / esc / toast. */
'use strict';
(function () {
  const $ = s => document.querySelector(s);
  const esc = v => (v == null ? '' : String(v)).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  let TOKEN = ''; try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch (e) { /* private window */ }
  if (!TOKEN) { location.replace('/console/'); return; }
  async function api(method, path, body, {raw = false} = {}) {
    const headers = {Authorization: 'Bearer ' + TOKEN}; let payload;
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
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
  window.HoolaCode({api, esc, toast, standalone: true}).open($('#code'));
})();
