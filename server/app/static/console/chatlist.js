/* v0.162 Hoola Console: the chat list and search (CHAT_SESSIONS).
   - Groups: Pinned, Aaj, Kal, Pichhle 7 din, Purane; a busy badge on every chat that is working, a dot on chats with
     a new reply; a menu per chat: Rename, Pin, Archive, Delete (asks first). Archive list at the bottom.
   - Search (Ctrl+K or the search button): titles + message text of all chats; a result opens the chat at that message.
   window.HoolaChats(ctx) -> {load, busy, unread, current, openSearch}; ctx = {api, esc, toast, open(id), jump(id, eventId),
   current() -> id, newChat()} */
'use strict';
window.HoolaChats = ctx => {
const {api, esc, toast} = ctx;
const $ = s => document.querySelector(s);
const BUSY = new Set(), UNREAD = new Set();
let LIST = [], ARCH = false, MENU = null;

const DAY = 86400000;
function group(c) {
  if (c.pinned) return 'Pin kiye hue';
  const t = new Date(c.updated_at || 0), now = new Date(), start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  if (t >= start) return 'Aaj';
  if (t >= start - DAY) return 'Kal';
  if (t >= start - 6 * DAY) return 'Pichhle 7 din';
  return 'Purane';
}
const ORDER = ['Pin kiye hue', 'Aaj', 'Kal', 'Pichhle 7 din', 'Purane'];

async function load() {
  try { LIST = (await api('GET', `/api/console/conversations${ARCH ? '?archived=true' : ''}`)).conversations || []; }
  catch { return LIST; }
  for (const c of LIST) if (c.busy) BUSY.add(c.id);
  draw();
  return LIST;
}
function item(c) {
  const cur = c.id === ctx.current();
  return `<div class="rcw${cur ? ' cur' : ''}" data-row="${esc(c.id)}">
    <a class="rc" href="/console/c/${encodeURIComponent(c.id)}" data-conv="${esc(c.id)}"${cur ? ' aria-current="true"' : ''} title="${esc(c.title)}">
      ${BUSY.has(c.id) ? '<span class="spin" aria-label="kaam chal raha"></span>' : UNREAD.has(c.id) ? '<i class="udot" aria-label="naya jawab"></i>' : ''}<span class="rct">${esc(c.title)}</span></a>
    <button type="button" class="rcm" data-menu="${esc(c.id)}" aria-label="Chat options: ${esc(c.title)}" aria-haspopup="menu">⋯</button></div>`;
}
function draw() {
  const box = $('#recents'); if (!box) return;
  const by = {};
  for (const c of LIST) (by[ARCH ? 'Archive' : group(c)] ||= []).push(c);
  const keys = ARCH ? ['Archive'] : ORDER;
  box.innerHTML = keys.filter(k => by[k]?.length).map(k => `<div class="rg">${esc(k)}</div>${by[k].map(item).join('')}`).join('')
    || `<div class="empty" style="padding:8px 12px">${ARCH ? 'Archive khaali hai.' : 'Abhi koi chat nahi.'}</div>`;
  box.insertAdjacentHTML('beforeend', `<button type="button" class="rcarch" id="archTog">${ARCH ? '← Saare chats' : '🗄 Archive dekhiye'}</button>`);
  $('#archTog').addEventListener('click', () => { ARCH = !ARCH; load(); });
}

/* ---------- menu ---------- */
function closeMenu() { MENU?.remove(); MENU = null; }
function openMenu(id, btn) {
  closeMenu();
  const c = LIST.find(x => x.id === id); if (!c) return;
  const m = document.createElement('div'); m.className = 'rmenu gl'; m.setAttribute('role', 'menu');
  m.innerHTML = `<button role="menuitem" data-a="rename">✎ Naam badlo</button>
    ${c.archived ? '' : `<button role="menuitem" data-a="pin">${c.pinned ? '📌 Pin hatao' : '📌 Pin karo'}</button>`}
    ${ctx.pickProject ? `<button role="menuitem" data-a="folder">📁 ${c.project_id ? 'Folder badlo / nikalo' : 'Folder mein daalo'}</button>` : ''}
    <button role="menuitem" data-a="archive">${c.archived ? '↩ Archive se wapas' : '🗄 Archive karo'}</button>
    <button role="menuitem" data-a="delete" class="bad">🗑 Delete karo</button>`;
  document.body.appendChild(m);
  const r = btn.getBoundingClientRect();
  m.style.top = Math.min(innerHeight - m.offsetHeight - 8, r.bottom + 4) + 'px';
  m.style.left = Math.max(8, Math.min(innerWidth - m.offsetWidth - 8, r.right - m.offsetWidth)) + 'px';
  m.querySelector('button').focus();
  m.addEventListener('click', e => { const b = e.target.closest('[data-a]'); if (b) act(c, b.dataset.a); });
  m.addEventListener('keydown', e => {
    const items = [...m.querySelectorAll('button')], i = items.indexOf(document.activeElement);
    if (e.key === 'Escape') { closeMenu(); btn.focus(); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); items[(i + 1) % items.length].focus(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
  });
  MENU = m;
}
async function act(c, a) {
  closeMenu();
  try {
    if (a === 'rename') { rename(c); return; }
    if (a === 'folder') { ctx.pickProject(c); return; }
    if (a === 'pin') await api('PATCH', `/api/conversations/${encodeURIComponent(c.id)}`, {pinned: !c.pinned});
    if (a === 'archive') { await api('PATCH', `/api/conversations/${encodeURIComponent(c.id)}`, {archived: !c.archived}); toast(c.archived ? 'Chat wapas aa gayi.' : 'Chat archive mein chali gayi.'); }
    if (a === 'delete') {
      if (!confirm(`"${c.title}" delete karein? Yeh chat list, search aur link se hat jayegi.`)) return;
      await api('DELETE', `/api/conversations/${encodeURIComponent(c.id)}`); toast('Chat delete ho gayi.');
      if (c.id === ctx.current()) ctx.newChat();
    }
    load();
  } catch (e) { toast(e.message, true); }
}
function rename(c) {
  const row = document.querySelector(`[data-row="${CSS.escape(c.id)}"]`); if (!row) return;
  row.innerHTML = `<form class="rcren"><input aria-label="Chat ka naya naam" maxlength="120" value="${esc(c.title)}"><button class="ib" aria-label="Save">✓</button></form>`;
  const f = row.querySelector('form'), inp = f.querySelector('input'); inp.focus(); inp.select();
  const save = async () => { const t = inp.value.trim(); if (t && t !== c.title) { try { await api('PATCH', `/api/conversations/${encodeURIComponent(c.id)}`, {title: t}); } catch (e) { toast(e.message, true); } } load(); };
  f.addEventListener('submit', e => { e.preventDefault(); save(); });
  inp.addEventListener('keydown', e => { if (e.key === 'Escape') load(); });
  inp.addEventListener('blur', () => setTimeout(() => { if (row.contains(f)) save(); }, 120));
}
document.addEventListener('click', e => {
  const m = e.target.closest('[data-menu]'); if (m) { e.preventDefault(); openMenu(m.dataset.menu, m); return; }
  if (MENU && !e.target.closest('.rmenu')) closeMenu();
  const a = e.target.closest('#recents a[data-conv]');
  if (a && !e.ctrlKey && !e.metaKey && !e.shiftKey && e.button === 0) { e.preventDefault(); UNREAD.delete(a.dataset.conv); ctx.open(a.dataset.conv); }
});

/* ---------- search ---------- */
let SBOX = null, ST = 0;
function openSearch() {
  if (SBOX) { SBOX.querySelector('input').focus(); return; }
  const w = document.createElement('div'); w.className = 'sbg'; w.setAttribute('role', 'dialog'); w.setAttribute('aria-modal', 'true'); w.setAttribute('aria-label', 'Chats mein dhoondhiye');
  w.innerHTML = `<div class="sbox gl"><label class="sin"><span aria-hidden="true">⌕</span><input placeholder="Saari chats mein dhoondhiye…" aria-label="Search" autocomplete="off"><kbd>Esc</kbd></label><div class="sres" role="listbox"><div class="empty">Kam se kam 2 akshar likhiye.</div></div></div>`;
  document.body.appendChild(w); SBOX = w;
  const inp = w.querySelector('input'), res = w.querySelector('.sres'); inp.focus();
  const close = () => { w.remove(); SBOX = null; };
  w.addEventListener('click', e => { if (e.target === w) close(); });
  inp.addEventListener('input', () => { clearTimeout(ST); ST = setTimeout(() => find(inp.value, res), 220); });
  w.addEventListener('keydown', e => {
    const items = [...res.querySelectorAll('.sr')], i = items.indexOf(document.activeElement);
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowDown') { e.preventDefault(); (items[i + 1] || items[0])?.focus(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); i <= 0 ? inp.focus() : items[i - 1].focus(); }
  });
  res.addEventListener('click', e => { const b = e.target.closest('.sr'); if (!b) return; close(); UNREAD.delete(b.dataset.c); ctx.jump(b.dataset.c, +b.dataset.e || 0); });
}
async function find(q, res) {
  q = q.trim(); if (q.length < 2) { res.innerHTML = '<div class="empty">Kam se kam 2 akshar likhiye.</div>'; return; }
  res.innerHTML = '<div class="empty"><span class="spin"></span> Dhoondh raha hoon…</div>';
  const me = ++FIND_SEQ;                              // v0.178 only the newest query may paint
  let r = []; try { r = (await api('GET', `/api/conversations/search?q=${encodeURIComponent(q)}`)).results || []; } catch (e) { if (me === FIND_SEQ) res.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  if (me !== FIND_SEQ) return;                        // she typed again while this fetch was out
  /* v0.178 the server sends <<match>> marks from FTS5 (snippet()); paint them after esc, never before */
  const mark = s => esc(s || '').replace(/&lt;&lt;/g, '<mark>').replace(/&gt;&gt;/g, '</mark>');
  const who = h => h.role === 'user' ? 'Aap' : h.role === 'title' ? 'Naam' : (ctx.avatar ? ctx.avatar() : 'Hoola');
  res.innerHTML = r.length
    ? `<div class="scount">${r.length} jagah mila · Enter se khologiye</div>` + r.map(h => `<button type="button" class="sr" role="option" data-c="${esc(h.conversation_id)}" data-e="${h.event_id || 0}">
      <b><i class="rwho">${esc(who(h))}</i>${esc(h.title || 'Chat')}</b><span>${mark(h.snippet || '')}</span>
      <time>${esc(new Date(h.at).toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}))}</time></button>`).join('')
    : '<div class="empty">Kuch nahi mila.</div>';
}
let FIND_SEQ = 0;
document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openSearch(); } });

return {
  load, openSearch, draw,
  ids: () => LIST.map(c => c.id),                     // v0.178 Alt+↑/↓ walks this order
  busy(id, on) { const had = BUSY.has(id); on ? BUSY.add(id) : BUSY.delete(id); if (had !== !!on) draw(); },
  unread(id) { if (id !== ctx.current() && !UNREAD.has(id)) { UNREAD.add(id); draw(); } },
  isBusy: id => BUSY.has(id),
  find: id => LIST.find(x => x.id === id),
};
};
