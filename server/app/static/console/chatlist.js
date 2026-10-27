/* v0.162 Hoola Console: the chat list and search (CHAT_SESSIONS). v0.193: sessions in the sidebar.
   - Sessions (v0.193): every kaam folder (project) becomes a collapsible section in the list itself — a header
     with emoji, name and chat count; click the chevron to collapse (state lives in localStorage, a collapsed
     session still shows a dot when a chat inside is busy or has a new reply), click the name to open the session
     page, hover "+" starts a new chat right inside that session. Drag a chat row onto a session header to move
     it there, onto "Other chats" to take it out. No sessions -> the exact old list.
   - Groups (chats without a session): Pinned, Today, Yesterday, Previous 7 days, Older; a busy badge on every chat that
     is working, a dot on chats with a new reply; a menu per chat: Rename, Pin, Session, Archive, Delete (asks
     first). Archive list at the bottom.
   - Search (Ctrl+K or the search button): titles + message text of all chats; a result opens the chat at that
     message and carries a chip naming the session it lives in.
   window.HoolaChats(ctx) -> {load, busy, unread, current, openSearch}; ctx = {api, esc, toast, open(id),
   jump(id, eventId), current() -> id, newChat(), newChatIn(sessionId), openSection(sessionId), avatar()} */
'use strict';
window.HoolaChats = ctx => {
const {api, esc, toast} = ctx;
const $ = s => document.querySelector(s);
const BUSY = new Set(), UNREAD = new Set();
let LIST = [], ARCH = false, MENU = null, MENU_TRIGGER = null;
let HISTORY = null, HISTORY_ARCH = false, HISTORY_ROWS = [], HISTORY_OFFSET = 0, HISTORY_MORE = true, HISTORY_LOADING = false, HISTORY_GEN = 0;
let SECS = [];                        // v0.193 sessions (projects), server order — last-touched first

const DAY = 86400000;
function group(c) {
  if (c.pinned) return 'Pinned';
  const t = new Date(c.updated_at || 0), now = new Date(), start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  if (t >= start) return 'Today';
  if (t >= start - DAY) return 'Yesterday';
  if (t >= start - 6 * DAY) return 'Previous 7 days';
  return 'Older';
}
const ORDER = ['Pinned', 'Today', 'Yesterday', 'Previous 7 days', 'Older'];

/* v0.193 which sessions are collapsed: {"<pid>": 1} — survives reloads, per browser */
const OPEN_KEY = 'hoola.sessions.v1';
const openState = () => { try { return JSON.parse(localStorage.getItem(OPEN_KEY) || '{}') || {}; } catch { return {}; } };
const setOpen = (pid, closed) => { const st = openState(); if (closed) st[pid] = 1; else delete st[pid];
  try { localStorage.setItem(OPEN_KEY, JSON.stringify(st)); } catch {} };
const secOf = c => c.project_id ? SECS.find(p => p.id === c.project_id) : null;

async function load() {
  const [list, pj] = await Promise.all([          // sessions ride along (skipped in archive view)
    api('GET', `/api/console/conversations${ARCH ? '?archived=true' : ''}`).then(r => r.conversations || []).catch(() => null),
    ARCH ? Promise.resolve(null)
         : api('GET', '/api/projects').then(r => r.projects || []).catch(() => SECS),
  ]);
  if (list === null) return LIST;                 // the list fetch failed: keep what we had
  LIST = list;
  if (pj) SECS = pj;
  for (const c of LIST) if (c.busy) BUSY.add(c.id);
  draw();
  return LIST;
}
function item(c, drag) {
  const cur = c.id === ctx.current();
  return `<div class="rcw${cur ? ' cur' : ''}" data-row="${esc(c.id)}"${drag ? ' draggable="true"' : ''}>
    <a class="rc" href="/console/c/${encodeURIComponent(c.id)}" data-conv="${esc(c.id)}"${cur ? ' aria-current="true"' : ''} title="${esc(c.title)}">
      ${BUSY.has(c.id) ? '<span class="spin" aria-label="Working"></span>' : UNREAD.has(c.id) ? '<i class="udot" aria-label="New reply"></i>' : ''}<span class="rct">${esc(c.title)}</span></a>
    <button type="button" class="rcm" data-menu="${esc(c.id)}" aria-label="Chat options: ${esc(c.title)}" aria-haspopup="menu" aria-expanded="false">⋯</button></div>`;
}
/* v0.193 one session header: chevron collapses, the name opens the session page, "+" starts a chat inside,
   the count lives at the right; a collapsed session that still has a busy/unread chat shows the dot. */
function secHead(p, rows, closed) {
  const live = closed && rows.some(r => BUSY.has(r.id) || UNREAD.has(r.id));
  return `<div class="sgh${closed ? ' closed' : ''}" data-sec="${esc(p.id)}">
    <button type="button" class="sgc" data-a="tog" aria-expanded="${!closed}" aria-label="${closed ? 'Open project' : 'Collapse project'}: ${esc(p.name)}"><i class="chev" aria-hidden="true"></i></button>
    <button type="button" class="sgn" data-a="open" title="${esc(p.name)} — Open project"><span aria-hidden="true">${esc(p.emoji || '📁')}</span><span class="sgnt">${esc(p.name)}</span></button>
    ${live ? '<i class="udot" aria-label="Active conversation"></i>' : ''}<small class="sgn-n">${rows.length || ''}</small>
    <span class="sgacts"><button type="button" class="ib" data-a="new" aria-label="New chat: ${esc(p.name)}">+</button></span>
  </div>`;
}
function draw() {
  const box = $('#recents'); if (!box) return;
  if (ARCH) {                                     // archive stays one flat list, nothing to drag into
    box.innerHTML = `<div class="rg">Archive</div>` + LIST.map(c => item(c)).join('')
      || `<div class="empty" style="padding:8px 12px">Archive is empty.</div>`;
    box.insertAdjacentHTML('beforeend', `<button type="button" class="rcarch" id="archTog">← All chats</button>`);
    $('#archTog').addEventListener('click', () => { ARCH = !ARCH; load(); });
    return;
  }
  const drag = SECS.length > 0;                   // no sessions yet -> the old plain list, nothing draggable
  let html = '';
  for (const p of SECS) {
    const rows = LIST.filter(c => c.project_id === p.id);
    const closed = !!openState()[p.id];
    html += secHead(p, rows, closed) + (closed ? '' : rows.map(c => item(c, drag)).join(''));
  }
  const by = {};
  for (const c of LIST) if (!secOf(c)) (by[group(c)] ||= []).push(c);   // a deleted session's chats come back here on their own
  const rest = ORDER.filter(k => by[k]?.length).map(k => `<div class="rg">${esc(k)}</div>${by[k].map(c => item(c, drag)).join('')}`).join('');
  /* "Other chats" is the un-filed home once sessions exist — always visible, so dragging the LAST chat out of
     a session always has a target (it also labels the day groups when they are non-empty) */
  html += (drag ? `<div class="rg sgb" data-rest title="Drop here to move out of the project">Other chats</div>` : '') + rest;
  box.innerHTML = html || `<div class="empty" style="padding:8px 12px">No conversations yet.</div>`;
  box.insertAdjacentHTML('beforeend', `<button type="button" class="rcarch" id="archTog">🗄 Archived conversations</button>`);
  $('#archTog').addEventListener('click', () => { ARCH = !ARCH; load(); });
}

/* ---------- session header actions + drag & drop (v0.193, listeners live on document so draw() can repaint freely) ---------- */
document.addEventListener('click', e => {
  const b = e.target.closest('#recents .sgh [data-a]'); if (!b) return;
  const pid = b.closest('.sgh').dataset.sec;
  if (b.dataset.a === 'tog') { setOpen(pid, !openState()[pid]); draw(); }
  else if (b.dataset.a === 'open') ctx.openSection ? ctx.openSection(pid) : toast('Could not open the project.');
  else if (b.dataset.a === 'new') ctx.newChatIn ? ctx.newChatIn(pid) : toast('Could not create a conversation.');
});
let DRAG_ID = '';
const clearDrops = () => document.querySelectorAll('#recents .dropok').forEach(t => t.classList.remove('dropok'));
document.addEventListener('dragstart', e => {
  const row = e.target.closest && e.target.closest('#recents .rcw[draggable="true"]'); if (!row) return;
  DRAG_ID = row.dataset.row;
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', LIST.find(c => c.id === DRAG_ID)?.title || 'chat');   // Firefox needs data to drag
  row.classList.add('dragging');
});
document.addEventListener('dragend', () => { DRAG_ID = ''; clearDrops(); document.querySelector('#recents .dragging')?.classList.remove('dragging'); });
document.addEventListener('dragover', e => {
  const t = e.target.closest && e.target.closest('#recents .sgh, #recents .sgb');
  if (!t || !DRAG_ID) return;
  e.preventDefault(); e.dataTransfer.dropEffect = 'move'; t.classList.add('dropok');
});
document.addEventListener('dragleave', e => {
  const t = e.target.closest && e.target.closest('#recents .sgh, #recents .sgb');
  if (t && !t.contains(e.relatedTarget)) t.classList.remove('dropok');
});
document.addEventListener('drop', e => {
  const t = e.target.closest && e.target.closest('#recents .sgh, #recents .sgb');
  if (!t || !DRAG_ID) return;
  e.preventDefault();
  const pid = t.classList.contains('sgb') ? '' : t.dataset.sec;
  const c = LIST.find(x => x.id === DRAG_ID);
  DRAG_ID = ''; clearDrops();
  if (!c || (c.project_id || '') === (pid || '')) return;
  api('PATCH', `/api/conversations/${encodeURIComponent(c.id)}`, {project_id: pid})
    .then(() => { toast(pid ? `Moved "${c.title}" to the project.` : `Moved "${c.title}" out of the project.`); load(); })
    .catch(er => toast(er.message, true));
});

/* ---------- menu ---------- */
function closeMenu(restore=false) { const trigger=MENU_TRIGGER; MENU?.remove(); MENU = null; MENU_TRIGGER=null; trigger?.setAttribute("aria-expanded","false"); if(restore&&trigger?.isConnected)trigger.focus(); }
function openMenu(id, btn) {
  closeMenu();
  const c = LIST.find(x => x.id === id)||HISTORY_ROWS.find(x=>x.id===id); if (!c) return;
  const m = document.createElement('div'); m.className = 'rmenu gl'; m.setAttribute('role', 'menu');
  m.innerHTML = `<button role="menuitem" data-a="rename">✎ Rename</button>
    ${c.archived ? '' : `<button role="menuitem" data-a="pin">${c.pinned ? '📌 Unpin' : '📌 Pin'}</button>`}
    ${ctx.pickProject ? `<button role="menuitem" data-a="folder">🗂 ${c.project_id ? 'Change project' : 'Move to project'}</button>` : ''}
    <button role="menuitem" data-a="archive">${c.archived ? '↩ Restore' : '🗄 Archive'}</button>
    <button role="menuitem" data-a="delete" class="bad">🗑 Delete</button>`;
  document.body.appendChild(m);
  const r = btn.getBoundingClientRect();
  m.style.top = Math.min(innerHeight - m.offsetHeight - 8, r.bottom + 4) + 'px';
  m.style.left = Math.max(8, Math.min(innerWidth - m.offsetWidth - 8, r.right - m.offsetWidth)) + 'px';
  m.querySelector('button').focus();
  m.addEventListener('click', e => { const b = e.target.closest('[data-a]'); if (b) act(c, b.dataset.a); });
  m.addEventListener('keydown', e => {
    const items = [...m.querySelectorAll('button')], i = items.indexOf(document.activeElement);
    if (e.key === 'Escape') { e.preventDefault();e.stopPropagation();closeMenu(true); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); items[(i + 1) % items.length].focus(); }
    else if(e.key==='Home'){e.preventDefault();items[0]?.focus();}
    else if(e.key==='End'){e.preventDefault();items.at(-1)?.focus();}
    else if(e.key==='Tab')closeMenu();
    else if (e.key === 'ArrowUp') { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
  });
  MENU = m; MENU_TRIGGER=btn;btn.setAttribute('aria-expanded','true');
}
async function act(c, a) {
  closeMenu();
  try {
    if (a === 'rename') { rename(c); return; }
    if (a === 'folder') { ctx.pickProject(c); return; }
    if (a === 'pin') await api('PATCH', `/api/conversations/${encodeURIComponent(c.id)}`, {pinned: !c.pinned});
    if (a === 'archive') { await api('PATCH', `/api/conversations/${encodeURIComponent(c.id)}`, {archived: !c.archived}); toast(c.archived ? 'Conversation restored.' : 'Conversation archived.'); }
    if (a === 'delete') {
      if (!confirm(`"${c.title}" Delete this conversation? It will be removed from history and search.`)) return;
      await api('DELETE', `/api/conversations/${encodeURIComponent(c.id)}`); toast('Conversation deleted.');
      if (c.id === ctx.current()) ctx.newChat();
    }
    refreshLists();
  } catch (e) { toast(e.message, true); }
}
function rename(c) {
  const row = HISTORY?.querySelector(`[data-row="${CSS.escape(c.id)}"]`) || document.querySelector(`[data-row="${CSS.escape(c.id)}"]`); if (!row) return;
  row.innerHTML = `<form class="rcren"><input aria-label="Rename conversation" maxlength="120" value="${esc(c.title)}"><button class="ib" aria-label="Save">✓</button></form>`;
  const f = row.querySelector('form'), inp = f.querySelector('input'); inp.focus(); inp.select();
  let saving=false,finished=false;
  const cancel=()=>{if(saving||finished)return;finished=true;refreshLists();};
  const save=async()=>{
    if(saving||finished)return;
    const title=inp.value.trim();if(!title){inp.setCustomValidity('Enter a conversation name.');inp.reportValidity();return;}
    if(title===c.title){cancel();return;}
    saving=true;inp.disabled=true;f.querySelector('button').disabled=true;
    try{await api('PATCH',`/api/conversations/${encodeURIComponent(c.id)}`,{title});c.title=title;finished=true;toast('Conversation renamed.');refreshLists();}
    catch(e){toast(e.message,true);saving=false;inp.disabled=false;f.querySelector('button').disabled=false;inp.focus();}
  };
  inp.addEventListener('input',()=>inp.setCustomValidity(''));
  f.addEventListener('submit',e=>{e.preventDefault();save();});
  inp.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();cancel();}});
  inp.addEventListener('blur',()=>setTimeout(()=>{if(!row.contains(document.activeElement)&&!saving)cancel();},120));
}
document.addEventListener('click', e => {
  const m = e.target.closest('[data-menu]'); if (m) { e.preventDefault(); openMenu(m.dataset.menu, m); return; }
  if (MENU && !e.target.closest('.rmenu')) closeMenu();
  const a = e.target.closest('#recents a[data-conv]');
  if (a && !e.ctrlKey && !e.metaKey && !e.shiftKey && e.button === 0) { e.preventDefault(); UNREAD.delete(a.dataset.conv); ctx.open(a.dataset.conv); }
});

/* Full conversation history, including running conversation tasks. */
function refreshLists(){load();if(HISTORY){HISTORY_ROWS=[];HISTORY_OFFSET=0;HISTORY_MORE=true;HISTORY_GEN++;HISTORY_LOADING=false;fetchHistory();}}
function closeHistory(){closeMenu();HISTORY_GEN++;HISTORY?.remove();HISTORY=null;document.getElementById('historyBtn')?.focus();}
function historyRows(){
  if(!HISTORY)return;
  const q=HISTORY.querySelector('input').value.trim().toLowerCase(),busy=HISTORY.querySelector('[data-running]').getAttribute('aria-pressed')==='true';
  const rows=HISTORY_ROWS.filter(c=>(!q||c.title.toLowerCase().includes(q))&&(!busy||c.busy||BUSY.has(c.id)));
  HISTORY.querySelector('.history-list').innerHTML=rows.map(c=>item(c,false)).join('')||'<p class="empty">No matching conversations.</p>';
  const more=HISTORY.querySelector('[data-more]');more.hidden=!HISTORY_MORE;more.disabled=HISTORY_LOADING;more.textContent=HISTORY_LOADING?'Loading…':'Load older conversations';
  HISTORY.querySelector('.history-count').textContent=`${HISTORY_ROWS.length} conversations loaded`;
}
async function fetchHistory(){
  if(!HISTORY||HISTORY_LOADING||!HISTORY_MORE)return;
  HISTORY_LOADING=true;const gen=HISTORY_GEN;historyRows();
  try{
    const r=await api('GET',`/api/console/conversations?limit=200&offset=${HISTORY_OFFSET}&archived=${HISTORY_ARCH}`);
    if(!HISTORY||gen!==HISTORY_GEN)return;
    const page=r.conversations||[],known=new Set(HISTORY_ROWS.map(c=>c.id));
    HISTORY_ROWS.push(...page.filter(c=>!known.has(c.id)));HISTORY_OFFSET+=page.length;HISTORY_MORE=page.length===200;
  }catch(e){if(gen===HISTORY_GEN)toast(e.message,true);}
  finally{if(gen===HISTORY_GEN){HISTORY_LOADING=false;historyRows();}}
}
function openHistory(){
  if(HISTORY){HISTORY.querySelector('input').focus();return;}
  closeMenu();HISTORY_ROWS=[];HISTORY_OFFSET=0;HISTORY_MORE=true;HISTORY_LOADING=false;HISTORY_ARCH=false;HISTORY_GEN++;
  const w=document.createElement('div');w.className='history-overlay';w.setAttribute('role','dialog');w.setAttribute('aria-modal','true');w.setAttribute('aria-labelledby','history-title');
  w.innerHTML='<section class="history-surface"><header><div><span class="history-brand">HOOLA WORKSPACE</span><h2 id="history-title">Chats and tasks</h2></div><button class="ib" data-close aria-label="Close history">×</button></header><label class="history-search"><span aria-hidden="true">⌕</span><input type="search" aria-label="Filter loaded conversations" placeholder="Filter conversations by title…"></label><div class="history-filters"><button data-archive aria-pressed="false">Archived</button><button data-running aria-pressed="false">Working</button><span class="history-count"></span></div><div class="history-list"></div><footer><span>Tasks stay with their conversation.</span><button class="btn soft" data-more>Load older conversations</button></footer></section>';
  HISTORY=w;document.body.appendChild(w);w.querySelector('input').focus();fetchHistory();
  w.querySelector('input').addEventListener('input',historyRows);
  w.addEventListener('click',e=>{
    if(e.target===w||e.target.closest('[data-close]')){closeHistory();return;}
    if(e.target.closest('[data-more]')){fetchHistory();return;}
    const filter=e.target.closest('[data-archive],[data-running]');if(filter){filter.setAttribute('aria-pressed',String(filter.getAttribute('aria-pressed')!=='true'));if(filter.hasAttribute('data-archive')){HISTORY_ARCH=filter.getAttribute('aria-pressed')==='true';refreshLists();}else historyRows();return;}
    const link=e.target.closest('a[data-conv]');if(link&&!e.ctrlKey&&!e.metaKey&&!e.shiftKey){e.preventDefault();const id=link.dataset.conv;closeHistory();UNREAD.delete(id);ctx.open(id);}
  });
  w.addEventListener('keydown',e=>{
    if(e.key==='Escape'){e.preventDefault();closeHistory();return;}
    if(e.key==='Tab'&&!MENU){const nodes=[...w.querySelectorAll('button:not([disabled]):not([hidden]),input,a')].filter(n=>n.getClientRects().length),first=nodes[0],last=nodes.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
  });
}
/* ---------- search ---------- */
let SBOX = null, ST = 0;
function openSearch() {
  if (SBOX) { SBOX.querySelector('input').focus(); return; }
  const w = document.createElement('div'); w.className = 'sbg'; w.setAttribute('role', 'dialog'); w.setAttribute('aria-modal', 'true'); w.setAttribute('aria-label', 'Search conversations');
  w.innerHTML = `<div class="sbox gl"><label class="sin"><span aria-hidden="true">⌕</span><input placeholder="Search your conversations…" aria-label="Search" autocomplete="off"><kbd>Esc</kbd></label><div class="sres" role="listbox"><div class="empty">Type at least 2 characters.</div></div></div>`;
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
  q = q.trim(); if (q.length < 2) { res.innerHTML = '<div class="empty">Type at least 2 characters.</div>'; return; }
  res.innerHTML = '<div class="empty"><span class="spin"></span> Searching…</div>';
  const me = ++FIND_SEQ;                              // v0.178 only the newest query may paint
  let r = []; try { r = (await api('GET', `/api/conversations/search?q=${encodeURIComponent(q)}`)).results || []; } catch (e) { if (me === FIND_SEQ) res.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  if (me !== FIND_SEQ) return;                        // she typed again while this fetch was out
  /* v0.178 the server sends <<match>> marks from FTS5 (snippet()); paint them after esc, never before */
  const mark = s => esc(s || '').replace(/&lt;&lt;/g, '<mark>').replace(/&gt;&gt;/g, '</mark>');
  const who = h => h.role === 'user' ? 'You' : h.role === 'title' ? 'Title' : (ctx.avatar ? ctx.avatar() : 'Hoola');
  const chip = cid => { const p = secOf(LIST.find(x => x.id === cid) || {}); return p ? `<i class="srsec" aria-hidden="true">📁 ${esc(p.name)}</i>` : ''; };   // v0.193
  res.innerHTML = r.length
    ? `<div class="scount">${r.length} results</div>` + r.map(h => `<button type="button" class="sr" role="option" data-c="${esc(h.conversation_id)}" data-e="${h.event_id || 0}">
      <b><i class="rwho">${esc(who(h))}</i>${esc(h.title || 'Chat')}${chip(h.conversation_id)}</b><span>${mark(h.snippet || '')}</span>
      <time>${esc(new Date(h.at).toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}))}</time></button>`).join('')
    : '<div class="empty">No results found.</div>';
}
let FIND_SEQ = 0;
document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openSearch(); } });

return {
  load, openSearch, openHistory, draw,
  ids: () => LIST.map(c => c.id),                     // v0.178 Alt+↑/↓ walks this order
  busy(id, on) { const had = BUSY.has(id); on ? BUSY.add(id) : BUSY.delete(id); if (had !== !!on) draw(); },
  unread(id) { if (id !== ctx.current() && !UNREAD.has(id)) { UNREAD.add(id); draw(); } },
  isBusy: id => BUSY.has(id),
  find: id => LIST.find(x => x.id === id),
};
};
