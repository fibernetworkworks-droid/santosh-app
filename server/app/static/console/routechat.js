// v0.999.240 HOOLA ROUTE R5: the public chat page of a route started "from a chat" (no data of hers here; the route's
// Respond step is the reply). Served from the console's static folder so the page's CSP can stay script-src 'self'.
(function () {
  'use strict';
  const tok = location.pathname.split('/').filter(Boolean).pop();
  const log = document.getElementById('rcLog'), form = document.getElementById('rcForm'), inp = document.getElementById('rcIn');
  if (!log || !form || !inp) return;
  let sid = '';
  try { sid = sessionStorage.getItem('rc.' + tok) || ''; } catch (e) { /* private window */ }
  if (!sid) {
    const a = new Uint8Array(12); (window.crypto || {}).getRandomValues ? crypto.getRandomValues(a) : a.forEach((_, i) => { a[i] = Math.random() * 256; });
    sid = Array.from(a, b => b.toString(16).padStart(2, '0')).join('');
    try { sessionStorage.setItem('rc.' + tok, sid); } catch (e) { /* fine */ }
  }
  const add = (cls, text) => { const d = document.createElement('div'); d.className = 'rcm ' + cls; d.textContent = text; log.appendChild(d); d.scrollIntoView({block: 'end'}); return d; };
  let busy = false;
  form.addEventListener('submit', async ev => {
    ev.preventDefault();
    const text = inp.value.trim(); if (!text || busy) return;
    busy = true; add('me', text); inp.value = '';
    const w = add('bot wait', '…');
    try {
      const r = await fetch('/api/route-chat/' + encodeURIComponent(tok), {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({session: sid, text, hp: (document.getElementById('rcHp') || {}).value || ''})});
      const j = await r.json().catch(() => ({}));
      w.classList.remove('wait'); w.textContent = j.reply || j.error || 'Something went wrong - please try again.';
    } catch (e) { w.classList.remove('wait'); w.textContent = 'Could not reach the chat - check your connection.'; }
    busy = false; inp.focus();
  });
  inp.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
})();
