/* v0.999.29 QUALITY EVERYWHERE (owner: "NOW CHECK EVERY CHAT PANEL ... HAS THIS LLM RANGE OR NOT" -> the audit ->
   "GO BUILD 1 AND 2"): the one piece every studio's typing box carries at the right of the row under it - her credits
   (a small pie + "4,820 credits" / "42 free today", a link to the Credits page) and her quality tier (the chat's own
   five: Normal, Ultra asks first, High, Medium, Low; locked = Buy credits). The same choice as the chat (one setting on
   the server: GET / PUT /api/model/tier); no model names, no rupees. Works on any console page: it carries its own small
   menu and reads the page's own colour tokens (--ink --mut --dim --hair2 --pri --sunk --surface), so a studio that does
   not load menu.js / v2.css still shows the chat's look.
     HoolaQuality.mount(host, {api})   fills host (a span / div) and keeps it current; several mounts share one state
     HoolaQuality.refresh()            reads the tier + credits again (after a purchase)
     HoolaQuality.use(api)             once per page: every [data-hoola-quality] spot the page draws (now or later) fills itself */
'use strict';
window.HoolaQuality = (() => {
  const NAME = {'': 'Normal', ultra: 'Ultra', high: 'High', medium: 'Medium', low: 'Low'};
  const ROWS = ['', 'ultra', 'high', 'medium', 'low'];
  const NOTE = 'Better models give better answers and use your credit faster.';
  const LOCKED = 'Free works on Normal. Buy any plan or extra credits to open the other tiers.';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const num = v => Math.round(+v || 0).toLocaleString('en-US');
  let API = null, TIERS = null, WALLET = null, PLAN = 0, RATE = 0.088, LOADING = null, MENU = null, LAST = 0, LATER = false;
  const HOSTS = new Set();

  const CSS = `
.hq-under{display:flex;justify-content:flex-end;align-items:center;width:100%;align-self:stretch;padding:6px 2px 0;min-height:30px;box-sizing:border-box}
.hq-row{display:inline-flex;align-items:center;gap:2px;flex:none;font-family:inherit}
.hq-cr{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 8px;border-radius:8px;color:var(--mut,#57554F);
  font-size:12.5px;font-weight:500;line-height:1;text-decoration:none;white-space:nowrap;font-variant-numeric:tabular-nums}
.hq-cr:hover{background:var(--sunk,#F1F0EC);color:var(--ink,#1B1A17)}
.hq-cr svg{width:16px;height:16px;flex:none}
.hq-btn{display:inline-flex;align-items:center;gap:4px;height:30px;padding:0 6px 0 10px;border:0;border-radius:8px;background:transparent;
  color:var(--ink,#1B1A17);font:inherit;font-size:13.5px;font-weight:500;line-height:1;cursor:pointer;white-space:nowrap}
.hq-btn:hover,.hq-btn[aria-expanded="true"]{background:var(--sunk,#F1F0EC)}
.hq-btn svg{width:12px;height:12px;color:var(--dim,#6F6C65)}
.hq-cr:focus-visible,.hq-btn:focus-visible,.hq-mi:focus-visible{outline:2px solid var(--pri,#5B45E0);outline-offset:1px}
.hq-menu{position:fixed;z-index:2000;box-sizing:border-box;padding:6px;display:flex;flex-direction:column;gap:1px;
  background:var(--surface,var(--bg,#fff));color:var(--ink,#1B1A17);border:1px solid var(--hair2,#D3D1CA);border-radius:12px;
  box-shadow:0 1px 2px rgb(0 0 0 / .05),0 6px 24px rgb(0 0 0 / .12);font-family:inherit;font-size:14px;opacity:0;transform:scale(.97);
  transition:opacity .12s ease,transform .12s ease}
.hq-menu.on{opacity:1;transform:none}
.hq-note{margin:4px 8px 8px;font-size:13px;line-height:1.45;color:var(--mut,#57554F)}
.hq-mi{display:flex;align-items:center;gap:10px;width:100%;min-height:40px;padding:6px 8px;border:0;border-radius:8px;background:none;
  color:inherit;font:inherit;text-align:left;cursor:pointer}
.hq-mi:hover,.hq-mi:focus{background:rgb(27 26 23 / .06);outline:none}
.hq-mi[aria-checked="true"]{background:rgb(27 26 23 / .045)}
.hq-mi .t{flex:1}
.hq-tag{display:inline-block;margin-left:8px;padding:1px 7px;border-radius:6px;font-size:12px;line-height:18px;font-weight:500;
  background:rgb(27 26 23 / .06);color:var(--mut,#57554F);white-space:nowrap}
.hq-tag.warn{background:var(--warn-soft,#FBF0DF);color:var(--warn,#8F5409)}
.hq-tick{width:16px;height:16px;color:var(--pri,#5B45E0);flex:none}
.hq-title{display:flex;align-items:center;gap:6px;padding:6px 8px 2px}
.hq-title h2{margin:0;font-size:15px;line-height:20px;font-weight:600}
.hq-back{width:28px;height:28px;margin-left:-4px;padding:0;border:0;border-radius:8px;background:none;color:var(--mut,#57554F);cursor:pointer;display:flex;align-items:center;justify-content:center}
.hq-back:hover{background:var(--sunk,#F1F0EC)}
.hq-acts{display:flex;justify-content:flex-end;gap:8px;padding:12px 4px 4px}
.hq-b{min-height:36px;padding:0 14px;border:1px solid var(--hair2,#D3D1CA);border-radius:10px;background:transparent;color:inherit;font:inherit;font-weight:500;cursor:pointer}
.hq-b.pri{border-color:transparent;background:var(--ink,#1B1A17);color:var(--surface,var(--bg,#fff))}
@media (max-width:640px){.hq-cr span{display:none}}
@media (prefers-reduced-motion:reduce){.hq-menu{transition:none;transform:none}}`;
  function style() {
    if (document.getElementById('hqStyle')) return;
    const s = document.createElement('style'); s.id = 'hqStyle'; s.textContent = CSS; document.head.appendChild(s);
  }
  const DOWN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
  const TICK = '<svg class="hq-tick" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';
  const pie = f => { const p = Math.max(0, Math.min(1, +f || 0)), a = 2 * Math.PI * Math.max(p, 0.1);
    const x = (9 + 5 * Math.sin(a)).toFixed(2), y = (9 - 5 * Math.cos(a)).toFixed(2);
    return `<svg viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" r="7.2" fill="none" stroke="currentColor" stroke-width="1.5"/>${p >= 1
      ? '<circle cx="9" cy="9" r="5" fill="currentColor"/>' : `<path fill="currentColor" d="M9 9V4A5 5 0 ${p > 0.5 ? 1 : 0} 1 ${x} ${y}Z"/>`}</svg>`; };

  function html() {
    const out = [], w = WALLET;
    if (w && w.on && !w.exempt) {
      const paid = !!w.unlocked, left = paid ? w.paid_left : w.free_left;
      const frac = paid ? (w.plan && PLAN ? w.plan_left / PLAN : 1) : (w.free_daily ? w.free_left / w.free_daily : 0);
      const say = paid ? `${num(left)} credits` : `${num(left)} free today`;
      const tip = paid ? `${num(left)} credits left${w.plan_name ? ' · ' + w.plan_name + ' plan' : ''}. Open plans and extra credits.`
        : `${num(w.free_left)} of ${num(w.free_daily)} free credits left today (Normal only). Open plans.`;
      out.push(`<a class="hq-cr" href="/console/?v=credits" target="_blank" rel="noopener" title="${esc(tip)}" aria-label="${esc(tip)}">${pie(frac)}<span>${esc(say)}</span></a>`);
    }
    if (TIERS && TIERS.available) {
      const n = NAME[TIERS.selected || ''] || 'Normal';
      out.push(`<button type="button" class="hq-btn" aria-haspopup="menu" aria-expanded="false" aria-label="Quality: ${esc(n)}" title="Quality: ${esc(n)}"><span>${esc(n)}</span>${DOWN}</button>`);
    }
    return out.join('');
  }
  function draw() {
    if (MENU) { LATER = true; return; }      // v0.999.30 never redraw the button an open menu hangs from
    LATER = false;
    for (const h of [...HOSTS]) {
      if (!h.isConnected) { HOSTS.delete(h); continue; }
      h.innerHTML = html();
    }
  }
  async function refresh() {
    if (!API) return;
    if (LOADING) return LOADING;
    const cc = ((navigator.language || '').split('-')[1] || '').toUpperCase();
    LOADING = Promise.all([API('GET', '/api/model/tier').catch(() => null), API('GET', '/api/credits?country=' + encodeURIComponent(cc)).catch(() => null)])
      .then(([t, c]) => { LAST = Date.now(); if (+c?.inr_per_credit > 0) RATE = +c.inr_per_credit; TIERS = t; WALLET = c?.wallet || null; PLAN = ((c?.prices?.plans || []).find(p => p.id === WALLET?.plan) || {}).credits || 0; draw(); })
      .finally(() => { LOADING = null; });
    return LOADING;
  }

  // ---- the menu (the chat's sheet: a note, five rows, a violet tick; Ultra asks first)
  function close(back) {
    if (!MENU) return;
    const {el, btn} = MENU; MENU = null; el.remove(); btn.setAttribute('aria-expanded', 'false');
    if (LATER) draw();
    removeEventListener('pointerdown', outside, true); removeEventListener('resize', onMove); removeEventListener('scroll', onMove, true);
    if (back && btn.isConnected) btn.focus({preventScroll: true});
  }
  function outside(e) { if (MENU && !MENU.el.contains(e.target) && !MENU.btn.contains(e.target)) close(false); }
  function onMove(e) {             // only a resize, or a scroll that really moved the button, closes it (pages scroll on their own)
    if (!MENU || (e && e.target && MENU.el.contains(e.target))) return;
    if (e && e.type === 'scroll') { const r = MENU.btn.getBoundingClientRect(); if (Math.abs(r.top - MENU.at.top) <= 2 && Math.abs(r.left - MENU.at.left) <= 2) return; }
    close(false);
  }
  function place(el, btn) {
    const r = btn.getBoundingClientRect(), w = el.offsetWidth, h = el.offsetHeight, gap = 6, pad = 8;
    const up = r.top - gap - pad >= Math.min(h, 200) || r.top > innerHeight - r.bottom;
    el.style.left = Math.round(Math.max(pad, Math.min(innerWidth - w - pad, r.right - w))) + 'px';
    if (up) { el.style.bottom = Math.round(innerHeight - r.top + gap) + 'px'; el.style.maxHeight = (r.top - gap - pad) + 'px'; }
    else { el.style.top = Math.round(r.bottom + gap) + 'px'; el.style.maxHeight = (innerHeight - r.bottom - gap - pad) + 'px'; }
    el.style.overflowY = 'auto'; el.style.transformOrigin = `right ${up ? 'bottom' : 'top'}`;
  }
  function open(btn, view) {
    close(false); style();
    const el = document.createElement('div');
    el.className = 'hq-menu'; el.setAttribute('role', 'menu'); el.tabIndex = -1;
    const sel = TIERS?.selected || '', lock = !!TIERS?.locked;
    if (view === 'ultra') {
      el.style.width = '340px'; el.setAttribute('aria-label', 'Use Ultra?'); el.style.padding = '10px';
      el.innerHTML = `<div class="hq-title"><button type="button" class="hq-back" data-q="back" aria-label="Back to the tiers"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14.5 5.5L8 12l6.5 6.5"/></svg></button><h2>Use Ultra?</h2><span class="hq-tag warn">⚠ Up to 70× credit</span></div>
        <p class="hq-note" style="margin:6px 8px 0;font-size:13.5px">Ultra runs the best and most expensive models in every field: chat, coding, AI employees, apps and videos.</p>
        <p class="hq-note" style="margin:6px 8px 0;font-size:13.5px">Your credit runs out up to 70 times faster than on Medium.</p>
        <div class="hq-acts"><button type="button" class="hq-b" data-q="no">Not now</button><button type="button" class="hq-b pri" data-q="ultra-yes">Use Ultra</button></div>`;
    } else {
      el.style.width = '300px'; el.setAttribute('aria-label', 'Quality');
      el.innerHTML = `<p class="hq-note">${esc(lock ? LOCKED : NOTE)}</p>` + ROWS.map(id => {
        const tag = id === '' ? '<span class="hq-tag">Recommended</span>' : lock ? '<span class="hq-tag">🔒 Buy credits</span>' : id === 'ultra' ? '<span class="hq-tag warn">⚠ Up to 70× credit</span>' : '';
        return `<button type="button" class="hq-mi" role="menuitemradio" aria-checked="${sel === id}" data-tier="${id}"><span class="t">${NAME[id]}${tag}</span>${sel === id ? TICK : ''}</button>`;
      }).join('');
    }
    document.body.appendChild(el); place(el, btn);
    btn.setAttribute('aria-expanded', 'true');
    MENU = {el, btn, at: btn.getBoundingClientRect()};
    requestAnimationFrame(() => el.classList.add('on'));
    (el.querySelector('[aria-checked="true"]') || el.querySelector('button'))?.focus({preventScroll: true});
    el.addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      const q = b.dataset.q, t = b.dataset.tier;
      if (q === 'back') return open(btn);
      if (q === 'no') return close(true);
      if (q === 'ultra-yes') { close(true); return set('ultra'); }
      if (t === undefined) return;
      if (t && lock) { close(true); window.open('/console/?v=credits', '_blank', 'noopener'); return; }
      if (t === 'ultra' && sel !== 'ultra') return open(btn, 'ultra');
      close(true); if (t !== sel) set(t);
    });
    el.addEventListener('keydown', e => {
      const bs = [...el.querySelectorAll('button')], i = bs.indexOf(document.activeElement);
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(true); }
      else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); const n = bs.length; bs[((i < 0 ? 0 : i) + (e.key === 'ArrowDown' ? 1 : n - 1)) % n]?.focus(); }
      else if (e.key === 'Tab') { e.preventDefault(); close(true); }
    });
    addEventListener('pointerdown', outside, true); addEventListener('resize', onMove); addEventListener('scroll', onMove, true);
  }
  function say(text, bad) {
    const t = document.getElementById('toast');
    if (typeof window.toast === 'function') return window.toast(text, bad);
    if (!t) return;
    t.textContent = text; t.hidden = false; t.classList.toggle('bad', !!bad);
    clearTimeout(say.t); say.t = setTimeout(() => { t.hidden = true; }, 3200);
  }
  async function set(id) {
    try {
      TIERS = await API('PUT', '/api/model/tier', {tier: id, confirm_ultra: id === 'ultra'});
      draw();
      say(id ? 'Your next message runs on ' + NAME[id] + '.' : "Back to Hoola's normal setup.");
    } catch (e) { say(e.message || String(e), true); }
  }

  function mount(host, o = {}) {
    if (!host) return null;
    style();
    if (o.api) API = o.api;
    host.classList.add('hq-row');
    if (!host.dataset.hq) {
      host.dataset.hq = '1';
      host.addEventListener('click', e => { const b = e.target.closest('.hq-btn'); if (!b) return; e.preventDefault(); e.stopPropagation();
        if (MENU && MENU.btn === b) close(true); else open(b); });
    }
    HOSTS.add(host);
    if (TIERS || WALLET) host.innerHTML = html();
    if (!TIERS && !LOADING) refresh(); else if (LOADING) LOADING.then(draw);
    return {refresh};
  }
  let OBS = null;
  function scan(root) { (root.querySelectorAll ? root : document).querySelectorAll('[data-hoola-quality]:not([data-hq])').forEach(h => mount(h)); }
  // v0.999.30 WIRED: her credits go down as Hoola works - read them again when she comes back to the page and every minute
  function fresh() {
    if (!API || LOADING || document.visibilityState !== 'visible' || Date.now() - LAST < 20000) return;
    if ([...HOSTS].some(h => h.isConnected)) refresh();
  }
  function use(api) {
    if (api) API = api;
    if (!use.on) { use.on = true; addEventListener('focus', fresh); document.addEventListener('visibilitychange', fresh); setInterval(fresh, 60000); }
    if (!document.body) return addEventListener('DOMContentLoaded', () => use(api), {once: true});
    scan(document);
    if (!OBS && window.MutationObserver) {
      OBS = new MutationObserver(ms => { for (const m of ms) for (const n of m.addedNodes) if (n.nodeType === 1) {
        if (n.matches?.('[data-hoola-quality]:not([data-hq])')) mount(n); else if (n.querySelector?.('[data-hoola-quality]')) scan(n); } });
      OBS.observe(document.body, {childList: true, subtree: true});
    }
  }
  // v0.999.30 AI spend in credits (the server's own rupee rate for a credit), never rupees
  function credits(inr) { const c = Math.round((+inr || 0) / RATE); return (+inr || 0) > 0 && c < 1 ? 'under 1 credit' : c.toLocaleString('en-US') + (c === 1 ? ' credit' : ' credits'); }
  return {mount, refresh, use, credits, close: () => close(false), names: NAME};
})();
