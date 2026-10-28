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
let LIB_SEQ=0,TAB_UID=0;const AUTO_OPENED=new Set();
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

function drawTabs() {
  box.querySelector('.pntabs').innerHTML = TABS.map(t => `<div class="pntab${t === CUR ? ' on' : ''}" role="presentation">
    <button type="button" role="tab" aria-selected="${t===CUR}" tabindex="${t===CUR?0:-1}" aria-controls="${t.el.id}" data-tab="${esc(t.key)}" title="${esc(t.item.title)}"><span aria-hidden="true">${ICON[t.item.type] || '📎'}</span><span class="pnt">${esc(t.item.title)}</span></button>
    <button type="button" class="pnx" data-close="${esc(t.key)}" aria-label="Close: ${esc(t.item.title)}">✕</button></div>`).join('');
}
function shell() {
  if (box.dataset.ready) return;
  box.dataset.ready = '1';
  box.innerHTML = `<div class="pnhd"><div class="pntabs" role="tablist" aria-label="Open artifacts"></div>
      <button type="button" class="ib" id="pnLib" aria-label="Artifact library" title="Artifact library"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 4h16v5H4zM4 11h7v9H4zM13 11h7v9h-7z"/></svg></button><button type="button" class="ib" id="pnClose" aria-label="Close workspace">✕</button></div>
    <div class="pnbody"></div>`;
  box.addEventListener('click', e => {
    const t = e.target.closest('[data-tab]'); if (t) { select(TABS.find(x => x.key === t.dataset.tab)); return; }
    const x = e.target.closest('[data-close]'); if (x) { drop(x.dataset.close); return; }
  });
  box.querySelector('.pntabs').addEventListener('keydown',e=>{const button=e.target.closest('[data-tab]');if(!button||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const index=TABS.findIndex(t=>t.key===button.dataset.tab),next=e.key==='Home'?0:e.key==='End'?TABS.length-1:(index+(e.key==='ArrowRight'?1:-1)+TABS.length)%TABS.length;select(TABS[next]);box.querySelector('[role=tab][aria-selected=true]')?.focus();});
  $('#pnClose').addEventListener('click', close);
  $('#pnLib').addEventListener('click', () => ctx.goLibrary?.());
}
function open(item) {
  if (!item) return;
  shell(); show();
  const key = item.type + ':' + item.ref;
  let t = TABS.find(x => x.key === key);
  if (!t) {
    t = {key, item, conv:ctx.conv(), el: document.createElement('div'), blobs: [], controller: new AbortController()};
    t.el.id='artifact-panel-'+(++TAB_UID);t.el.setAttribute('role','tabpanel');t.el.setAttribute('aria-label',item.title);
    t.el.className = 'pnitem'; box.querySelector('.pnbody').appendChild(t.el);
    TABS.push(t);
    if (TABS.length > 6) drop(TABS[0].key);
    render(t);
  }
  select(t);
}
function select(t) {
  if (!t) return; CUR = t;
  const hadFocus=box.querySelector('.pntabs')?.contains(document.activeElement);TABS.forEach(x=>x.el.hidden=x!==t);drawTabs();if(hadFocus)box.querySelector('[role=tab][aria-selected=true]')?.focus();
}
function drop(key) {
  const i = TABS.findIndex(x => x.key === key); if (i < 0) return;
  const [t] = TABS.splice(i, 1); t.closed = true; t.controller?.abort(); t.el.querySelectorAll('audio,video').forEach(m => m.pause()); t.blobs.forEach(u => URL.revokeObjectURL(u)); t.el.remove();
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
async function share(kind, id, conv) {
  try { await api('POST', '/api/panel/share', {kind, id, conversation_id: conv || ctx.conv() || ''}); toast('An approval card is in your conversation. The link is created after approval.'); }
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
  const it=t.item,generation=(t.renderGeneration||0)+1,draft=t.el.querySelector('.pnchg input')?.value||'';t.renderGeneration=generation;t.aid=it.ref;t.view='preview';
  t.el.innerHTML = bar(t, `<select class="pnsel" aria-label="Version"></select>
      <div class="bseg" role="group" aria-label="Artifact view"><button type="button" data-v="preview" aria-pressed="true">Preview</button><button type="button" data-v="code" aria-pressed="false">Code</button></div>
      <span class="sp"></span><button type="button" class="btn soft" data-a="share">Share</button><button type="button" class="btn soft" data-a="dl">Download</button>`)
    + `<div class="pnerr" hidden></div><div class="pnview"></div>
    <form class="pnchg"><input placeholder="Describe a change, or select code to refine a section…" aria-label="Refine artifact"><button class="btn go" type="submit">Refine</button></form>`;
  t.el.querySelector('.pnchg input').value=draft;
  const sel = t.el.querySelector('.pnsel'), view = t.el.querySelector('.pnview');
  try {
    const d = await api('GET', `/api/artifacts/${encodeURIComponent(t.aid)}`);
    if(t.closed||generation!==t.renderGeneration)return;
    t.ver = d.version; it.title = d.title || it.title; drawTabs();
    sel.innerHTML = (d.versions || []).map(v => `<option value="${v.version}">v${v.version}${v.note ? ' · ' + esc(String(v.note).slice(0, 40)) : ''}</option>`).join('');
    sel.value = String(t.ver);
  } catch (e) { view.innerHTML = err(e.message); return; }
  sel.addEventListener('change', () => { t.ver = +sel.value; pageView(t); });
  t.el.querySelector('.bseg').addEventListener('click', e => { const b = e.target.closest('[data-v]'); if (!b) return; t.view = b.dataset.v;
    t.el.querySelectorAll('.bseg button').forEach(x => x.setAttribute('aria-pressed', x === b)); pageView(t); });
  t.el.querySelector('[data-a="share"]').addEventListener('click', () => share('page', t.aid, t.conv));
  t.el.querySelector('[data-a="dl"]').addEventListener('click', async () => {
    try { const s = await api('GET', `/api/panel/pages/${encodeURIComponent(t.aid)}/source?version=${t.ver}`); saveBlob(new Blob([s.html], {type: 'text/html'}), `${(s.title || 'page').replace(/[^\w-]+/g, '-')}-v${s.version}.html`); }
    catch (e) { toast(e.message, true); } });
  t.el.querySelector('.pnchg').addEventListener('submit', async e => {
    e.preventDefault(); const inp = e.target.querySelector('input'), want = inp.value.trim(); if (!want) return;
    const part = selectionIn(view);
    const request = part ? `Change this selected section:\n"""\n${part}\n"""\nRequested change: ${want}` : want;
    const button=e.target.querySelector('button');if(button.disabled)return;button.disabled=true;
    try { await api('POST', `/api/artifacts/${encodeURIComponent(t.aid)}/revise`, {request}); inp.value = ''; toast('Creating a new version. It will appear here when ready.'); }
    catch (er) { toast(er.message, true); }finally{if(!t.closed)button.disabled=false;} });
  pageView(t);
}
async function pageView(t) {
  const generation=(t.viewGeneration||0)+1;t.viewGeneration=generation;
  const view = t.el.querySelector('.pnview'); t.el.querySelector('.pnerr').hidden = true;
  view.innerHTML = '<div class="pnempty skel-page" style="width:100%"><i class="skel" style="height:46px"></i><i class="skel" style="height:240px"></i></div>';
  try {
    if (t.view === 'code') {
      const s = await api('GET', `/api/panel/pages/${encodeURIComponent(t.aid)}/source?version=${t.ver}`);
      if(t.closed||generation!==t.viewGeneration)return;
      view.innerHTML = `<div class="pncodebar"><button type="button" class="btn soft" data-copy-code>Copy</button></div>` + code(s.html, 'html');
      view.querySelector('[data-copy-code]').addEventListener('click', async e => { try { await navigator.clipboard.writeText(s.html); e.target.textContent = 'Copied ✓'; } catch { toast('Could not copy', true); } });
      return;
    }
    const v = await api('GET', `/api/panel/pages/${encodeURIComponent(t.aid)}/view?version=${t.ver}`);
    if(t.closed||generation!==t.viewGeneration)return;
    view.innerHTML = '';
    const f = document.createElement('iframe');
    f.className = 'pnframe'; f.title = t.item.title; f.setAttribute('sandbox', 'allow-scripts allow-forms allow-popups');
    f.setAttribute('referrerpolicy','no-referrer');const link=new URL(v.url,location.origin);if(link.origin!==location.origin||!/^\/a\/[\w-]+\/\d+$/.test(link.pathname))throw Error('Invalid artifact preview URL');link.searchParams.set('panel','1');f.src=link.pathname+link.search;
    view.appendChild(f); t.frame = f;
  } catch (e) { if(!t.closed&&generation===t.viewGeneration)view.innerHTML = err(e.message); }
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
  const box = t.el.querySelector('.pnerr'); if (!box) return;
  box.hidden = false;
  box.innerHTML = `<span>⚠️ Artifact error: <code>${esc(String(d.message || '').slice(0, 160))}</code></span><button type="button" class="btn go">Fix</button>`;
  box.querySelector('button').onclick = () => {
    ctx.say(`The artifact "${t.item.title}" (v${t.ver}) reports this error: ${String(d.message || '').slice(0,300)}${d.line ? ` (line ${d.line})` : ''}. Diagnose it and create a corrected version.`);
    box.hidden = true;
  };
}

/* website / app prototype: live preview in a sandboxed frame */
function renderPreview(t) {
  const it = t.item;
  t.el.innerHTML = bar(t, `<span class="pnnote">${it.type === 'app' ? 'App prototype' : 'Website preview'} · live</span><span class="sp"></span>
      ${ctx.studio && it.payload ? '<button type="button" class="btn soft" data-a="studio">Open build studio</button>' : ''}
      <a class="btn soft" href="${esc(it.preview)}" target="_blank" rel="noopener noreferrer">Open in new tab</a>`)
    + `<div class="pnview ${it.type === 'app' ? 'phone' : ''}"></div>`;
  const f = document.createElement('iframe');
  f.className = 'pnframe'; f.title = it.title; f.setAttribute('sandbox', 'allow-scripts allow-forms allow-popups'); f.setAttribute('referrerpolicy', 'no-referrer');
  f.src = it.preview; t.el.querySelector('.pnview').appendChild(f);
  t.el.querySelector('[data-a="studio"]')?.addEventListener('click', () => { close(); ctx.studio(it.kind, it.payload); });
}

/* a reel / edited video: its own signed link */
function renderUrlVideo(t) {
  const it = t.item;
  t.el.innerHTML = bar(t, `<span class="pnnote">Video</span><span class="sp"></span><a class="btn soft" href="${esc(it.url)}" download>Download</a>`)
    + `<div class="pnview center"><video class="pnmedia" controls playsinline preload="metadata" src="${esc(it.url)}"></video></div>`;
}

/* her file: viewable types as blob:, Office as PDF, text as code, the rest download */
async function renderFile(t) {
  const it = t.item, fid = it.ref, P = `/api/panel/files/${encodeURIComponent(fid)}`;
  t.el.innerHTML = `<div class="pnview center"><div class="skel-page" style="width:100%;padding:16px" aria-label="Loading"><i class="skel" style="height:46px"></i><i class="skel" style="height:260px"></i></div></div>`;
  let info;
  try { info = await api('GET', P + '/info'); if(t.closed)return; } catch (e) { if(t.closed)return; t.el.querySelector('.pnview').innerHTML = err(e.message); return; }
  if (!it.title || it.title === it.name) it.title = info.name || it.title; drawTabs();
  t.el.innerHTML = bar(t, `<span class="pnnote">${esc(info.name)} · ${Math.max(1, Math.round((info.size || 0) / 1024))} KB</span><span class="sp"></span>
      <button type="button" class="btn soft" data-a="refine">Refine in chat</button><button type="button" class="btn soft" data-a="share">Share</button><button type="button" class="btn soft" data-a="dl">Download</button>`)
    + '<div class="pnview center"><div class="skel-page" style="width:100%;padding:16px" aria-label="Loading"><i class="skel" style="height:46px"></i><i class="skel" style="height:260px"></i></div></div>';
  t.el.querySelector('[data-a="dl"]').addEventListener('click', () => download(P + '?download=1', info.name));
  t.el.querySelector('[data-a="share"]').addEventListener('click', () => share('file', fid, t.conv));
  t.el.querySelector('[data-a="refine"]')?.addEventListener('click',()=>ctx.say(`Help me refine the file ${info.name} [file_id: ${fid}]. Ask what changes I want, then use the available file tools to create an updated file. Do not claim an edit is saved until the tool confirms it.`));
  const view = t.el.querySelector('.pnview');
  try {
    if (info.inline && info.mime) {
      const u = await blobOf(t, P, info.mime);
      if (info.media === 'image') view.innerHTML = `<img class="pnmedia" alt="${esc(info.name)}" src="${u}">`;
      else if (info.media === 'video') view.innerHTML = `<video class="pnmedia" controls playsinline src="${u}"></video>`;
      else if (info.media === 'audio') view.innerHTML = `<audio controls src="${u}"></audio>`;
      else if (info.media === 'pdf') view.innerHTML = `<iframe class="pnframe" title="${esc(info.name)}" src="${u}"></iframe>`;
      return;
    }
    if (info.office) { const u = await blobOf(t, P + '/pdf', 'application/pdf'); view.innerHTML = `<iframe class="pnframe" title="${esc(info.name)}" src="${u}"></iframe>`; return; }
    if (info.text) { const s = await api('GET', P + '/text'); view.classList.remove('center'); view.innerHTML = code(s.text, s.lang); return; }
    view.innerHTML = `<div class="pnempty">This file cannot be previewed here. <b>Download</b> to open it.</div>`;
  } catch (e) { view.innerHTML = err(e.message); }
}

/* a card changed (a new page version is ready): open tabs follow */
function update(kind,p){
  if(kind!=='artifact'||!p?.id||p.status!=='ready'||!p.version)return;
  const t=TABS.find(x=>x.item.type==='page'&&x.aid===p.id);
  if(t&&p.version!==t.ver){toast(`${p.title||'Artifact'}: version ${p.version} is ready.`);renderPage(t);return;}
  if(!t&&!AUTO_OPENED.has(p.id)&&ctx.canOpen?.()!==false&&!isOpen()&&!appEl.classList.contains('st')){AUTO_OPENED.add(p.id);open(itemOf(kind,p));}
}

/* ---------- Creations ---------- */
const FILTERS = [['', 'All artifacts'], ['pages', 'Pages'], ['sites', 'Websites'], ['apps', 'Apps'], ['photos', 'Photos'], ['videos', 'Videos'], ['files', 'Files']];
const TEMPLATES=[
 {id:'dashboard',icon:'▥',title:'Interactive dashboard',description:'Explore metrics, filters and charts.',request:'Use artifact_make to create an interactive dashboard artifact in Hoola branding. First ask what data and metrics I want to use. Do not invent business figures. Build an editable versioned artifact after the brief is clear.'},
 {id:'calculator',icon:'⌘',title:'Calculator',description:'An interactive tool with clear inputs.',request:'Use artifact_make to create an interactive calculator artifact. First ask what it should calculate and confirm the formula and units. Include input validation, clear results and Hoola branding.'},
 {id:'guide',icon:'▤',title:'Interactive guide',description:'Turn a topic into a useful walkthrough.',request:'Use artifact_make to build an interactive guide artifact. Ask for the topic, audience and source material first. Use clear sections and Hoola branding, and do not invent facts.'},
 {id:'report',icon:'↗',title:'Business report',description:'A structured document from your sources.',request:'Create a downloadable Word business report. Ask for the topic, audience and source files first. Include an executive summary, findings, evidence and recommendations. Use only verified source material and mark gaps.'}
];
async function library(el, kind = '', q = '') {
  el.innerHTML = `<div class="vh"><h2>Artifacts</h2><span class="faint" style="font-weight:700">Your finished work, ready to revisit and refine.</span></div>
    <label class="ksearch gl"><span aria-hidden="true">⌕</span><input id="libq" placeholder="Search your artifacts…" value="${esc(q)}" aria-label="Search artifacts"></label>
    <section class="artifact-templates"><h3>Start from a template</h3><div class="artifact-template-grid">${TEMPLATES.map(t=>`<button type="button" data-template="${t.id}"><span aria-hidden="true">${t.icon}</span><b>${t.title}</b><small>${t.description}</small></button>`).join('')}</div><p>Templates start a guided brief. Your sources and instructions shape the result.</p></section>
    <h3 class="artifact-library-label">Your artifacts</h3><div class="kchips" role="group" aria-label="Filter">${FILTERS.map(([k, n]) => `<button type="button" class="chip${k === kind ? ' on' : ''}" data-f="${k}" aria-pressed="${k === kind}">${n}</button>`).join('')}</div>
    <div class="libgrid" id="libgrid"><div class="skel-grid" aria-hidden="true">${'<i class="skel"></i>'.repeat(6)}</div></div>`;
  el.querySelector('.artifact-templates').addEventListener('click',e=>{const b=e.target.closest('[data-template]');const template=TEMPLATES.find(t=>t.id===b?.dataset.template);if(template)ctx.say(template.request);});
  el.querySelector('.kchips').addEventListener('click', e => { const b = e.target.closest('[data-f]'); if (b) library(el, b.dataset.f, el.querySelector('#libq').value); });
  let tm = 0; el.querySelector('#libq').addEventListener('input', e => { LIB_SEQ++;clearTimeout(tm); tm = setTimeout(() => fill(el, kind, e.target.value), 250); });
  fill(el, kind, q);
}
async function fill(el, kind, q) {
  const g = el.querySelector('#libgrid'),seq=++LIB_SEQ;
  let items = [];
  try { items = (await api('GET', `/api/panel/library?kind=${encodeURIComponent(kind)}&q=${encodeURIComponent(q.trim())}`)).items || []; }
  catch (e) { if(seq===LIB_SEQ&&g.isConnected)g.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  if(seq!==LIB_SEQ||!g.isConnected)return;
  const when = s => { try { return new Date(s).toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}); } catch { return ''; } };
  g.innerHTML = items.length ? items.map((it, i) => `<button type="button" class="libit gl" data-i="${i}"><i aria-hidden="true">${ICON[it.type] || '📎'}</i>
      <b>${esc(it.title)}</b><span>${esc(it.sub || it.type)}</span><time>${esc(when(it.at))}${it.version ? ' · v' + it.version : ''}</time></button>`).join('')
    : '<div class="empty">No artifacts found. Try another filter, or start with a template above.</div>';
  g.onclick = e => { const b = e.target.closest('[data-i]'); if (!b) return; const it = items[+b.dataset.i];
    open(it.type === 'video' && it.url ? {...it, url: ownPath(it.url)} : it.type === 'page' ? {type: 'page', ref: it.ref, title: it.title} : it); };
}

function reset() {
  for (const t of [...TABS]) drop(t.key);
  CUR=null;LIB_SEQ++;AUTO_OPENED.clear();close();
}
return {itemOf, open, update, library, isOpen, close, reset};
};
