/* v0.164 Hoola Console · projects, "Project folders" (CHAT_PROJECTS). v0.193: they ARE the sidebar sessions.
   Sidebar: the sessions box is slim now — label + "+" only; the sections themselves live in the chat list
   (chatlist.js draws them). A session page: name + emoji, her instructions for it, its notes (yaad), its files
   (drop or pick; kept until she removes them; big ones are searched through Gyaan), its chats + "Is session mein
   naya chat". A chat's ⋯ menu moves it in / out of a session (chatlist.js asks `pick`).
   window.HoolaProjects(ctx) -> {load, draw, open(pid), pick(chat), nameOf(pid), list()};
   ctx = {api, esc, toast, go(view), openChat(id), current() -> chat id, reloadChats()} */
'use strict';
window.HoolaProjects = ctx => {
const {api, esc, toast} = ctx;
const $ = s => document.querySelector(s);
let LIST = [], CUR = null;

async function load() {
  try { LIST = (await api('GET', '/api/projects')).projects || []; } catch { LIST = []; }
  draw(); return LIST;
}
function draw() {
  const box = $('#projects'); if (!box) return;
  /* v0.193 the folder rows moved into the chat list as session sections — this box stays the "+ New" entry */
  box.innerHTML = `<div class="slabel pjl"><span>Sessions</span><button type="button" class="pjadd" id="pjNew" aria-label="New project">+</button></div>`
    + (LIST.length ? '' : '<div class="empty pjempty">Kaam ke hisaab se session banaiye — App design, Research…</div>');
  box.querySelector('#pjNew').addEventListener('click', create);
}

async function create() {
  const name = (prompt('New session name (e.g. "App design", "Research", "GST")') || '').trim();
  if (!name) return;
  try { const p = await api('POST', '/api/projects', {name}); await load(); ctx.reloadChats?.(); open(p.id); toast('Session created. Its instructions, files and chats live here.'); }
  catch (e) { toast(e.message, true); }
}
const nameOf = pid => LIST.find(p => p.id === pid);

/* ---------- the folder page ---------- */
async function open(pid) {
  CUR = pid; ctx.go('project');
  const box = $('#project');
  box.innerHTML = `<div class="skel-page"><i class="skel" style="width:40%;height:34px"></i><i class="skel" style="height:110px"></i><i class="skel" style="height:110px"></i></div>`;
  let p, chats = [];
  try {
    p = await api('GET', `/api/projects/${encodeURIComponent(pid)}`);
    chats = (await api('GET', `/api/console/conversations?project=${encodeURIComponent(pid)}`)).conversations || [];
  } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  draw();
  box.innerHTML = `<div class="vh pjhd"><h2><button type="button" class="pjemo" aria-label="Change emoji">${esc(p.emoji || '📁')}</button><span class="pjname" contenteditable="plaintext-only" spellcheck="false" aria-label="Project name">${esc(p.name)}</span></h2>
      <div class="acts"><button type="button" class="btn go" data-a="chat">+ New chat in this session</button><button type="button" class="btn soft" data-a="del">Delete session</button></div></div>
    <div class="grid2 pjgrid">
      <div class="tile gl"><h3>Instructions <span class="tag v">every chat</span></h3>
        <p class="muted" style="font-size:13px">${esc(ctx.avatar())} follows these in every chat of this session (for example "Budget 5 lakh", "Always reply in Hindi").</p>
        <textarea class="pjta" data-f="instructions" rows="6" aria-label="Session instructions" placeholder="What should ${esc(ctx.avatar())} know about this work?">${esc(p.instructions)}</textarea></div>
      <div class="tile gl"><h3>Memory <span class="tag v">notes</span></h3>
        <p class="muted" style="font-size:13px">Key facts for this work: names, dates, decisions.</p>
        <textarea class="pjta" data-f="memory" rows="6" aria-label="Session memory" placeholder="Venue: Pune, 12 Dec · Caterer: Sharma ji">${esc(p.memory)}</textarea></div>
      <div class="tile gl pjfiles"><h3>Files <span class="tag v">${p.files}</span></h3>
        <label class="pjdrop" tabindex="0"><input type="file" multiple hidden><b>Drop files here</b><span>or choose · up to 25 MB · big files are searched through Gyaan</span></label>
        <div class="pjfl">${(p.file_list || []).map(f => `<div class="pjf"><span>📎 ${esc(f.name)}</span><small>${Math.max(1, Math.round(f.size / 1024))} KB</small><button type="button" class="ib" data-rm="${esc(f.id)}" aria-label="Remove ${esc(f.name)}">✕</button></div>`).join('') || '<div class="empty">No files yet.</div>'}</div></div>
      <div class="tile gl"><h3>Chats <span class="tag v">${chats.length}</span></h3>
        <div class="pjchats">${chats.map(c => `<button type="button" class="rc" data-chat="${esc(c.id)}"><span class="rct">${esc(c.title)}</span></button>`).join('') || '<div class="empty">No conversations yet. Press "+ New chat in this session".</div>'}</div></div>
    </div>`;
  // name + emoji
  const nm = box.querySelector('.pjname');
  nm.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); nm.blur(); } });
  nm.addEventListener('blur', () => { const n = nm.textContent.trim(); if (n && n !== p.name) save({name: n}).then(() => { p.name = n; }); else nm.textContent = p.name; });
  box.querySelector('.pjemo').addEventListener('click', () => { const e = (prompt('One emoji (e.g. 💍 🧾 🏪)', p.emoji) || '').trim(); if (e) save({emoji: e}).then(() => open(pid)); });
  // instructions + notes save on their own
  box.querySelectorAll('.pjta').forEach(ta => { let t = 0; ta.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => save({[ta.dataset.f]: ta.value}, true), 700); }); });
  // files
  const drop = box.querySelector('.pjdrop'), inp = drop.querySelector('input');
  drop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inp.click(); } });
  inp.addEventListener('change', () => { upload([...inp.files]); inp.value = ''; });
  ['dragover', 'dragenter'].forEach(k => drop.addEventListener(k, e => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach(k => drop.addEventListener(k, () => drop.classList.remove('over')));
  drop.addEventListener('drop', e => { e.preventDefault(); upload([...(e.dataTransfer?.files || [])]); });
  box.querySelector('.pjfl').addEventListener('click', async e => { const b = e.target.closest('[data-rm]'); if (!b) return;
    if (!confirm('Remove this file from the session?')) return;
    try { await api('DELETE', `/api/projects/${encodeURIComponent(pid)}/files/${encodeURIComponent(b.dataset.rm)}`); open(pid); } catch (er) { toast(er.message, true); } });
  box.querySelector('.pjchats').addEventListener('click', e => { const b = e.target.closest('[data-chat]'); if (b) ctx.openChat(b.dataset.chat); });
  box.querySelector('[data-a="chat"]').addEventListener('click', async () => {
    try { const c = await api('POST', `/api/conversations?project_id=${encodeURIComponent(pid)}`); ctx.openChat(c.id, true); ctx.reloadChats(); load(); }
    catch (e) { toast(e.message, true); } });
  box.querySelector('[data-a="del"]').addEventListener('click', async () => {
    if (!confirm(`Delete the "${p.name}" session? Its chats stay; they just leave the session.`)) return;
    try { await api('DELETE', `/api/projects/${encodeURIComponent(pid)}`); CUR = null; await load(); ctx.reloadChats(); ctx.go('chat'); toast('Session deleted.'); }
    catch (e) { toast(e.message, true); } });

  async function save(patch, quiet) {
    try { await api('PATCH', `/api/projects/${encodeURIComponent(pid)}`, patch); if (!quiet) load(); else { const s = box.querySelector(`[data-f="${Object.keys(patch)[0]}"]`); s?.classList.add('saved'); setTimeout(() => s?.classList.remove('saved'), 900); } }
    catch (e) { toast(e.message, true); }
  }
  async function upload(files) {
    for (const f of files.slice(0, 10)) {
      if (f.size > 25 * 1024 * 1024) { toast(`${f.name}: files over 25 MB are not supported.`, true); continue; }
      const fd = new FormData(); fd.append('file', f, f.name);
      try { await api('POST', `/api/projects/${encodeURIComponent(pid)}/files`, undefined, {form: fd}); toast(`${f.name} added to the session.`); }
      catch (e) { toast(`${f.name}: ${e.message}`, true); }
    }
    open(pid);
  }
}

/* ---------- move a chat in / out (from the chat menu) ---------- */
async function pick(chat) {
  if (!LIST.length) await load();
  const choices = LIST.map((p, i) => `${i + 1}. ${p.emoji || '📁'} ${p.name}`).join('\n');
  const inFolder = chat.project_id ? `\n0. Session se bahar nikalo` : '';
  const ans = prompt(`Move to which session? Type its number:\n${choices}${inFolder}`, '');
  if (ans === null || ans.trim() === '') return;
  const n = parseInt(ans, 10);
  const pid = n === 0 ? null : LIST[n - 1]?.id;
  if (pid === undefined) return toast('No such session.', true);
  try { await api('PATCH', `/api/conversations/${encodeURIComponent(chat.id)}`, {project_id: pid}); toast(pid ? 'Chat moved into the session.' : 'Chat moved out of the session.'); ctx.reloadChats(); load(); }
  catch (e) { toast(e.message, true); }
}

return {load, draw, open, pick, nameOf, list: () => LIST};
};
