/* v0.163 Hoola Console · side panel for finished work (SIDE_PANEL): pages, files, pictures, reels, videos, websites and
   apps open beside the chat in tabs; "Creations" lists everything Hoola made.
   Safety: pages and site / app previews run in sandboxed frames WITHOUT allow-same-origin (they can't see the login).
   A page's bridge (storage / ask / errors) arrives here by postMessage from that frame only and is answered for that
   page only. Her files are fetched with the token into blob: URLs, and only for the types the server marks viewable
   (images, video, audio, PDF); everything else is a download. Share = a Haan card in the chat first.
   window.HoolaPanel(ctx) -> {itemOf, open, update, library, isOpen, close};
   ctx = {api, esc, toast, token(), conv(), say(text), studio(kind, payload) | null} */
'use strict';
window.HoolaPanel = ctx => {
const {api, esc, toast} = ctx;
const $ = s => document.querySelector(s);
const appEl = $('#app'), box = $('#panel');
const TABS = [];          // {key, item, el, blobs: [], frame, aid, ver, view}
let CUR = null;
const ICON = {page: '📄', website: '🌐', app: '📱', image: '🖼', video: '🎬', audio: '🎵', pdf: '📕', doc: '📝', sheet: '📊',
              slides: '📽', text: '📃', file: '📎'};

/* ---------- what can open ---------- */
function preview(u) { const m = String(u || '').match(/(\/api\/(?:site|app)-preview\/[\w-]+\/)$/); return m ? m[1] : ''; }
function media(name) {
  const n = String(name || '').toLowerCase();
  if (/\.(png|jpe?g|gif|webp|heic|bmp)$/.test(n)) return 'image';
  if (/\.(mp4|webm|mov|m4v|mkv|3gp)$/.test(n)) return 'video';
  if (/\.(mp3|m4a|ogg|wav|aac|opus)$/.test(n)) return 'audio';
  if (n.endsWith('.pdf')) return 'pdf';
  if (/\.(docx?|odt|rtf)$/.test(n)) return 'doc';
  if (/\.(xlsx?|csv|ods)$/.test(n)) return 'sheet';
  if (/\.(pptx?|odp|key)$/.test(n)) return 'slides';
  if (/\.(txt|md|json|html?|css|js|py|xml|ya?ml|kt|dart|sql|log)$/.test(n)) return 'text';
  return 'file';
}
const ownPath = u => { try { const x = new URL(String(u || ''), location.origin); return x.origin === location.origin && /^\/api\/(motion|video)\/files\//.test(x.pathname) ? x.pathname + x.search : ''; } catch { return ''; } };
function itemOf(kind, p) {
  p = p || {};
  if (kind === 'artifact' && p.id) return p.version ? {type: 'page', ref: p.id, title: p.title || 'Page', version: p.version} : null;
  if ((kind === 'pc_file' || kind === 'photo_made') && p.file_id) return {type: media(p.name), ref: p.file_id, title: p.title || p.name || 'File', name: p.name};
  if (kind === 'motion' && p.id && ownPath(p.url)) return {type: 'video', ref: 'mv:' + p.id, title: p.title || 'Reel', url: ownPath(p.url)};
  if (kind === 'video_job' && ownPath(p.latest?.url)) return {type: 'video', ref: 'vj:' + p.id, title: p.title || 'Video', url: ownPath(p.latest.url), file_id: p.latest.file_id};
  if ((kind === 'site_board' || kind === 'app_board') && preview(p.preview)) return {type: kind === 'site_board' ? 'website' : 'app', ref: p.id || p.project || p.preview, title: p.title || p.name || (kind === 'site_board' ? 'Website' : 'App'), preview: preview(p.preview), payload: p, kind};
  return null;
}

/* ---------- shell ---------- */
function show() { appEl.classList.add('pn'); appEl.classList.remove('open'); ctx.closeStudio?.(); }
function close() { appEl.classList.remove('pn'); }
const isOpen = () => appEl.classList.contains('pn');
new MutationObserver(() => { if (appEl.classList.contains('st') && isOpen()) appEl.classList.remove('pn'); }).observe(appEl, {attributes: true, attributeFilter: ['class']});

/* v0.248 one item open = ONE header row: its actions bar (name, Share, Download, view switches) moves up beside the
   close button and the tab pill hides; two or more items = the tab row again. q / qa find a tab's controls wherever
   its bar sits right now. */
const slotOf = () => box.querySelector('.pnslot');
const q = (t, s) => t.el.querySelector(s) || (slotOf()?.firstElementChild?._owner === t.el ? slotOf().querySelector(s) : null);
const qa = (t, s) => [...t.el.querySelectorAll(s), ...(slotOf()?.firstElementChild?._owner === t.el ? slotOf().querySelectorAll(s) : [])];
let syncing = false;
function syncHead() {
  const slot = slotOf(); if (!slot || syncing) return; syncing = true;
  try {
    const one = TABS.length === 1 && CUR, held = slot.firstElementChild;
    const fresh = one ? CUR.el.querySelector(':scope>.pnbar') : null;
    if (held && (!one || held._owner !== CUR.el || fresh)) {          // send it home, or drop it when a newer render replaced it
      if (!fresh && held._owner?.isConnected && !held._owner.querySelector(':scope>.pnbar')) held._owner.prepend(held); else held.remove();
    }
    if (fresh) { fresh._owner = CUR.el; slot.replaceChildren(fresh); }
    box.classList.toggle('one', !!one);
  } finally { syncing = false; }
}
function drawTabs() {
  box.querySelector('.pntabs').innerHTML = TABS.map(t => `<div class="pntab${t === CUR ? ' on' : ''}" role="tab" aria-selected="${t === CUR}">
    <button type="button" data-tab="${esc(t.key)}" title="${esc(t.item.title)}"><span aria-hidden="true">${ICON[t.item.type] || '📎'}</span><span class="pnt">${esc(t.item.title)}</span></button>
    <button type="button" class="pnx" data-close="${esc(t.key)}" aria-label="Close: ${esc(t.item.title)}">✕</button></div>`).join('');
  syncHead();
}
function shell() {
  if (box.dataset.ready) return;
  box.dataset.ready = '1';
  box.innerHTML = `<div class="pnhd"><div class="pntabs" role="tablist" aria-label="Open items"></div><div class="pnslot"></div>
      <button type="button" class="ib" id="pnLib" aria-label="Creations" title="Creations"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 4h16v5H4zM4 11h7v9H4zM13 11h7v9h-7z"/></svg></button><button type="button" class="ib" id="pnClose" aria-label="Close panel">✕</button></div>
    <div class="pnbody"></div>`;
  new MutationObserver(syncHead).observe(box.querySelector('.pnbody'), {childList: true, subtree: true});
  box.addEventListener('click', e => {
    const t = e.target.closest('[data-tab]'); if (t) { select(TABS.find(x => x.key === t.dataset.tab)); return; }
    const x = e.target.closest('[data-close]'); if (x) { drop(x.dataset.close); return; }
  });
  $('#pnClose').addEventListener('click', close);
  $('#pnLib').addEventListener('click', () => ctx.goLibrary?.());
}
function open(item) {
  if (!item) return;
  shell(); show();
  const key = item.type + ':' + item.ref;
  let t = TABS.find(x => x.key === key);
  if (!t) {
    t = {key, item, el: document.createElement('div'), blobs: [], controller: new AbortController()};
    t.el.className = 'pnitem'; box.querySelector('.pnbody').appendChild(t.el);
    TABS.push(t);
    if (TABS.length > 6) drop(TABS[0].key);
    render(t);
  }
  select(t);
}
function select(t) {
  if (!t) return; CUR = t;
  TABS.forEach(x => x.el.hidden = x !== t); drawTabs();
}
function drop(key) {
  const i = TABS.findIndex(x => x.key === key); if (i < 0) return;
  const [t] = TABS.splice(i, 1); t.closed = true; t.controller?.abort(); t.pdf?.destroy(); t.el.querySelectorAll('audio,video').forEach(m => m.pause()); t.blobs.forEach(u => URL.revokeObjectURL(u)); t.el.remove();
  if (CUR === t) CUR = TABS[Math.max(0, i - 1)] || null;
  if (!TABS.length) { close(); drawTabs(); return; }
  select(CUR);
}

/* ---------- helpers ---------- */
async function blobOf(t, path, type) {
  const r = await fetch(path, {headers: {Authorization: 'Bearer ' + ctx.token()}, cache: 'no-store', credentials: 'omit', signal: t.controller.signal});
  if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not open (${r.status})`); }
  const bytes = await r.arrayBuffer(); if (t.closed) throw new Error('Workspace closed');
  const u = URL.createObjectURL(new Blob([bytes], {type}));
  t.blobs.push(u); return u;
}
async function download(path, name) {
  try {
    const r = await fetch(path, {headers: {Authorization: 'Bearer ' + ctx.token()}, credentials: 'omit'});
    if (!r.ok) throw new Error(`Download failed (${r.status})`);
    saveBlob(await r.blob(), name);
  } catch (e) { toast(e.message, true); }
}
function saveBlob(blob, name) {
  const u = URL.createObjectURL(blob), a = document.createElement('a');
  a.href = u; a.download = name || 'hoola-file'; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(u), 4000);
}
const bar = (t, html) => `<div class="pnbar">${html}</div>`;
const err = msg => `<div class="pnempty">⚠️ ${esc(msg)}</div>`;
function code(text, lang) {
  const lines = String(text).split('\n');
  return `<pre class="pcode" tabindex="0" aria-label="Code"><code data-lang="${esc(lang || '')}">${lines.map((l, i) => `<span class="ln" data-n="${i + 1}">${esc(l)}</span>`).join('\n')}</code></pre>`;
}
async function share(kind, id) {
  try { await api('POST', '/api/panel/share', {kind, id, conversation_id: ctx.conv() || ''}); toast('An approval card is in your conversation. The link is created after approval.'); }
  catch (e) { toast(e.message, true); }
}
function selectionIn(el) {
  const s = getSelection(); if (!s || s.isCollapsed || !el.contains(s.anchorNode)) return '';
  return String(s).slice(0, 3000);
}

/* ---------- render by type ---------- */
function render(t) {
  const it = t.item;
  if (it.type === 'page') return renderPage(t);
  if (it.type === 'website' || it.type === 'app') return renderPreview(t);
  if (it.url) return renderUrlVideo(t);
  return renderFile(t);
}

/* page (artifact): preview in a sandboxed frame / code, versions, Edit, Share, Download, errors -> Fix */
async function renderPage(t) {
  const it = t.item; t.aid = it.ref; t.view = 'preview';
  t.el.innerHTML = bar(t, `<select class="pnsel" aria-label="Version"></select>
      <div class="bseg" role="group" aria-label="View"><button type="button" data-v="preview" aria-pressed="true">Preview</button><button type="button" data-v="code" aria-pressed="false">Code</button></div>
      ${devSeg(false)}<span class="sp"></span><button type="button" class="btn soft" data-a="share">Share</button><button type="button" class="btn soft" data-a="dl">Download</button>`)
    + `<div class="pnerr" hidden></div><div class="pnview"></div>
    <form class="pnchg"><input placeholder="What should change? (you can select part of the code too)" aria-label="Change request"><button class="btn go" type="submit">Edit</button></form>`;
  const sel = q(t, '.pnsel'), view = q(t, '.pnview');
  try {
    const d = await api('GET', `/api/artifacts/${encodeURIComponent(t.aid)}`);
    t.ver = d.version; it.title = d.title || it.title; drawTabs();
    sel.innerHTML = (d.versions || []).map(v => `<option value="${v.version}">v${v.version}${v.note ? ' · ' + esc(String(v.note).slice(0, 40)) : ''}</option>`).join('');
    sel.value = String(t.ver);
  } catch (e) { view.innerHTML = err(e.message); return; }
  sel.addEventListener('change', () => { t.ver = +sel.value; pageView(t); });
  q(t, '.bseg').addEventListener('click', e => { const b = e.target.closest('[data-v]'); if (!b) return; t.view = b.dataset.v;
    qa(t, '.bseg button').forEach(x => x.setAttribute('aria-pressed', x === b)); pageView(t); });
  wireDev(t);
  q(t, '[data-a="share"]').addEventListener('click', () => share('page', t.aid));
  q(t, '[data-a="dl"]').addEventListener('click', async () => {
    try { const s = await api('GET', `/api/panel/pages/${encodeURIComponent(t.aid)}/source?version=${t.ver}`); saveBlob(new Blob([s.html], {type: 'text/html'}), `${(s.title || 'page').replace(/[^\w-]+/g, '-')}-v${s.version}.html`); }
    catch (e) { toast(e.message, true); } });
  q(t, '.pnchg').addEventListener('submit', async e => {
    e.preventDefault(); const inp = e.target.querySelector('input'), want = inp.value.trim(); if (!want) return;
    const part = selectionIn(view);
    const request = part ? `Is hisse ko badlo:\n"""\n${part}\n"""\nBadlav: ${want}` : want;
    try { await api('POST', `/api/artifacts/${encodeURIComponent(t.aid)}/revise`, {request}); inp.value = ''; toast('Creating a new version. It will appear here when ready.'); }
    catch (er) { toast(er.message, true); } });
  pageView(t);
}
async function pageView(t) {
  const view = q(t, '.pnview'); q(t, '.pnerr').hidden = true;
  view.innerHTML = '<div class="pnempty skel-page" style="width:100%"><i class="skel" style="height:46px"></i><i class="skel" style="height:240px"></i></div>';
  try {
    if (t.view === 'code') {
      const s = await api('GET', `/api/panel/pages/${encodeURIComponent(t.aid)}/source?version=${t.ver}`);
      view.innerHTML = `<div class="pncodebar"><button type="button" class="btn soft" data-copy-code>Copy</button></div>` + code(s.html, 'html');
      view.querySelector('[data-copy-code]').addEventListener('click', async e => { try { await navigator.clipboard.writeText(s.html); e.target.textContent = 'Copied ✓'; } catch { toast('Could not copy', true); } });
      return;
    }
    const v = await api('GET', `/api/panel/pages/${encodeURIComponent(t.aid)}/view?version=${t.ver}`);
    view.innerHTML = '';
    const f = document.createElement('iframe');
    f.className = 'pnframe'; f.title = t.item.title; f.setAttribute('sandbox', 'allow-scripts allow-forms allow-popups');
    f.setAttribute('referrerpolicy', 'no-referrer'); f.src = v.url + '&panel=1';
    view.appendChild(browserFrame(f, `${t.item.title} · v${t.ver}`)); t.frame = f;
  } catch (e) { view.innerHTML = err(e.message); }
}
/* the page bridge: only messages from this tab's own frame, answered for this page only */
addEventListener('message', async e => {
  const t = TABS.find(x => x.frame && e.source === x.frame.contentWindow); if (!t) return;
  const d = e.data || {};
  if (d.hoola === 'error') { showError(t, d); return; }
  if (d.hoola !== 'bridge') return;
  let m; try { m = JSON.parse(d.msg); } catch { return; }
  const reply = (ok, v) => { try { e.source.postMessage({hoola: 'reply', id: m.id, ok, v}, '*'); } catch {} };
  const A = `/api/artifacts/${encodeURIComponent(t.aid)}`;
  try {
    if (m.op === 'storage.get') { const s = (await api('GET', A + '/state')).state || {}; return reply(true, Object.prototype.hasOwnProperty.call(s, m.args?.key) ? s[m.args.key] : null); }
    if (m.op === 'storage.all') return reply(true, (await api('GET', A + '/state')).state || {});
    if (m.op === 'storage.set') { await api('PUT', A + '/state', {key: String(m.args?.key || '').slice(0, 120), value: m.args?.value ?? null}); return reply(true, true); }
    if (m.op === 'ask') return reply(true, (await api('POST', A + '/ask', {question: String(m.args?.question || '').slice(0, 2000)})).answer);
    reply(false, 'unknown');
  } catch (er) { reply(false, er.message); }
});
function showError(t, d) {
  const box = q(t, '.pnerr'); if (!box) return;
  box.hidden = false;
  box.innerHTML = `<span>⚠️ Page error: <code>${esc(String(d.message || '').slice(0, 160))}</code></span><button type="button" class="btn go">Fix</button>`;
  box.querySelector('button').onclick = () => {
    ctx.say(`Page "${t.item.title}" (v${t.ver}) mein error aa raha hai: ${String(d.message || '').slice(0, 300)}${d.line ? ` (line ${d.line})` : ''}. Isse theek karke naya version banao.`);
    box.hidden = true;
  };
}

/* desktop / phone width for a live preview, and a browser frame around it */
function devSeg(phone) {
  return `<div class="bseg dev" role="group" aria-label="Device"><button type="button" data-d="desk" aria-pressed="${!phone}">Desktop</button><button type="button" data-d="phone" aria-pressed="${phone}">Phone</button></div>`;
}
function wireDev(t) {
  const seg = q(t, '.bseg.dev'); if (!seg) return;
  seg.addEventListener('click', e => { const b = e.target.closest('[data-d]'); if (!b) return;
    seg.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
    q(t, '.pnview')?.classList.toggle('phone', b.dataset.d === 'phone'); });
}
function browserFrame(f, label) {
  const w = document.createElement('div'); w.className = 'pnbrowser';
  w.innerHTML = `<div class="pnchrome" aria-hidden="true"><i></i><i></i><i></i><span class="pnurl"></span></div>`;
  w.querySelector('.pnurl').textContent = String(label || '').slice(0, 120);
  w.appendChild(f); return w;
}

/* website / app prototype: live preview in a sandboxed frame */
function renderPreview(t) {
  const it = t.item;
  t.el.innerHTML = bar(t, `<span class="pnnote">${it.type === 'app' ? 'App prototype' : 'Website preview'} · live</span><span class="sp"></span>
      ${devSeg(it.type === 'app')}${ctx.studio && it.payload ? '<button type="button" class="btn soft" data-a="studio">Open build studio</button>' : ''}
      <a class="btn soft" href="${esc(it.preview)}" target="_blank" rel="noopener noreferrer">Open in new tab</a>`)
    + `<div class="pnview ${it.type === 'app' ? 'phone' : ''}"></div>`;
  const f = document.createElement('iframe');
  f.className = 'pnframe'; f.title = it.title; f.setAttribute('sandbox', 'allow-scripts allow-forms allow-popups'); f.setAttribute('referrerpolicy', 'no-referrer');
  f.src = it.preview; q(t, '.pnview').appendChild(browserFrame(f, it.preview));
  wireDev(t);
  q(t, '[data-a="studio"]')?.addEventListener('click', () => { close(); ctx.studio(it.kind, it.payload); });
}

/* a reel / edited video: its own signed link */
function renderUrlVideo(t) {
  const it = t.item;
  t.el.innerHTML = bar(t, `<span class="pnnote">Video</span><span class="sp"></span><a class="btn soft" href="${esc(it.url)}" download>Download</a>`)
    + `<div class="pnview center"><video class="pnmedia" controls playsinline preload="metadata" src="${esc(it.url)}"></video></div>`;
}

/* v0.248 a document fills the whole workspace on our own background: drawn by pdfview.js (no browser toolbar, no grey
   canvas, no thumbnail strip). If the reader cannot start, the browser's viewer is the fallback (toolbar / strip hidden). */
const PDF_VIEW = '#toolbar=0&navpanes=0&pagemode=none&view=FitH&zoom=page-width';
async function docView(t, view, name, path) {
  view.classList.remove('center'); view.classList.add('doc');
  const r = await fetch(path, {headers: {Authorization: 'Bearer ' + ctx.token()}, cache: 'no-store', credentials: 'omit', signal: t.controller.signal});
  if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not open (${r.status})`); }
  const bytes = await r.arrayBuffer(); if (t.closed) return;
  try {
    if (!window.HoolaPdf) throw new Error('no reader');
    t.pdf?.destroy(); t.pdf = await window.HoolaPdf.mount(view, bytes.slice(0), name);
  } catch (e) {
    const u = URL.createObjectURL(new Blob([bytes], {type: 'application/pdf'})); t.blobs.push(u);
    view.innerHTML = `<iframe class="pnframe" title="${esc(name)}" src="${u}${PDF_VIEW}"></iframe>`;
  }
}
/* her file: viewable types as blob:, Office as PDF, text as code, the rest download */
async function renderFile(t) {
  const it = t.item, fid = it.ref, P = `/api/panel/files/${encodeURIComponent(fid)}`;
  t.el.innerHTML = `<div class="pnview center"><div class="skel-page" style="width:100%;padding:16px" aria-label="Loading"><i class="skel" style="height:46px"></i><i class="skel" style="height:260px"></i></div></div>`;
  let info;
  try { info = await api('GET', P + '/info'); if(t.closed)return; } catch (e) { if(t.closed)return; q(t, '.pnview').innerHTML = err(e.message); return; }
  if (!it.title || it.title === it.name) it.title = info.name || it.title; drawTabs();
  t.el.innerHTML = bar(t, `<span class="pnnote">${esc(info.name)} · ${Math.max(1, Math.round((info.size || 0) / 1024))} KB</span><span class="sp"></span>
      <button type="button" class="btn soft" data-a="share">Share</button><button type="button" class="btn soft" data-a="dl">Download</button>`)
    + '<div class="pnview center"><div class="skel-page" style="width:100%;padding:16px" aria-label="Loading"><i class="skel" style="height:46px"></i><i class="skel" style="height:260px"></i></div></div>';
  q(t, '[data-a="dl"]').addEventListener('click', () => download(P + '?download=1', info.name));
  q(t, '[data-a="share"]').addEventListener('click', () => share('file', fid));
  const view = q(t, '.pnview');
  try {
    if (info.inline && info.media === 'pdf') { await docView(t, view, info.name, P); return; }
    if (info.inline && info.mime) {
      const u = await blobOf(t, P, info.mime);
      if (info.media === 'image') view.innerHTML = `<img class="pnmedia" alt="${esc(info.name)}" src="${u}">`;
      else if (info.media === 'video') view.innerHTML = `<video class="pnmedia" controls playsinline src="${u}"></video>`;
      else if (info.media === 'audio') view.innerHTML = `<audio controls src="${u}"></audio>`;
      return;
    }
    if (info.office) { await docView(t, view, info.name, P + '/pdf'); return; }
    if (info.text) { const s = await api('GET', P + '/text'); view.classList.remove('center'); view.innerHTML = code(s.text, s.lang); return; }
    view.innerHTML = `<div class="pnempty">This file cannot be previewed here. <b>Download</b> it to open.</div>`;
  } catch (e) { view.innerHTML = err(e.message); }
}

/* a card changed (a new page version is ready): open tabs follow */
function update(kind, p) {
  if (kind !== 'artifact' || !p?.id) return;
  const t = TABS.find(x => x.item.type === 'page' && x.aid === p.id);
  if (t && p.status === 'ready' && p.version && p.version !== t.ver) { toast(`${p.title || 'Page'}: new version v${p.version} is ready.`); renderPage(t); }
}

/* ---------- Creations ---------- */
const FILTERS = [['', 'All'], ['pages', 'Pages'], ['sites', 'Websites'], ['apps', 'Apps'], ['photos', 'Photos'], ['videos', 'Videos'], ['files', 'Files']];
async function library(el, kind = '', q = '') {
  el.innerHTML = `<div class="vh"><h2>Creations</h2><span class="faint" style="font-weight:700">Your creations — select an item to open it in the workspace.</span></div>
    <label class="ksearch gl"><span aria-hidden="true">⌕</span><input id="libq" placeholder="Search: EMI, poster, bill…" value="${esc(q)}" aria-label="Search"></label>
    <div class="kchips" role="group" aria-label="Filter">${FILTERS.map(([k, n]) => `<button type="button" class="chip${k === kind ? ' on' : ''}" data-f="${k}" aria-pressed="${k === kind}">${n}</button>`).join('')}</div>
    <div class="libgrid" id="libgrid"><div class="skel-grid" aria-hidden="true">${'<i class="skel"></i>'.repeat(6)}</div></div>`;
  el.querySelector('.kchips').addEventListener('click', e => { const b = e.target.closest('[data-f]'); if (b) library(el, b.dataset.f, el.querySelector('#libq').value); });
  let tm = 0; el.querySelector('#libq').addEventListener('input', e => { clearTimeout(tm); tm = setTimeout(() => fill(el, kind, e.target.value), 250); });
  fill(el, kind, q);
}
async function fill(el, kind, q) {
  const g = el.querySelector('#libgrid');
  let items = [];
  try { items = (await api('GET', `/api/panel/library?kind=${encodeURIComponent(kind)}&q=${encodeURIComponent(q.trim())}`)).items || []; }
  catch (e) { g.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  const when = s => { try { return new Date(s).toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}); } catch { return ''; } };
  g.innerHTML = items.length ? items.map((it, i) => `<button type="button" class="libit gl" data-i="${i}"><i aria-hidden="true">${ICON[it.type] || '📎'}</i>
      <b>${esc(it.title)}</b><span>${esc(it.sub || it.type)}</span><time>${esc(when(it.at))}${it.version ? ' · v' + it.version : ''}</time></button>`).join('')
    : '<div class="empty">Nothing here yet. Ask in chat, for example: "EMI calculator banao" or "Diwali poster banao".</div>';
  g.onclick = e => { const b = e.target.closest('[data-i]'); if (!b) return; const it = items[+b.dataset.i];
    open(it.type === 'video' && it.url ? {...it, url: ownPath(it.url)} : it.type === 'page' ? {type: 'page', ref: it.ref, title: it.title} : it); };
}

function reset() {
  for (const t of [...TABS]) drop(t.key);
  CUR=null; close();
}
return {itemOf, open, update, library, isOpen, close, reset};
};
