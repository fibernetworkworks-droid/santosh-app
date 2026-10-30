/* v0.275 ATTACHMENTS LIKE CLAUDE: how her pictures, PDFs, videos and files look in the chat.
   Composer tray: square tiles above the typing box - a picture shows itself the moment she picks it (local blob:),
   a PDF its first page once uploaded, a video its frame + length, text its first lines; a real upload % on each
   tile, a failed one stays red with Retry, ✕ removes.
   Sent message: the same tiles sit ABOVE her bubble, right-aligned (one picture large, several as a grid).
   Click a picture / video = a full-screen viewer (← → between the message's files, Esc, Download, Open in workspace);
   a PDF / Office / text file opens in the workspace's own reader. Her files come with her login into blob: URLs
   (CSP img-src / media-src allow blob: and data:); nothing goes into a URL.
   window.HoolaAttach(ctx) -> {kind, tray, sent, view, upload, thumbOf, forget}
   ctx = {api, esc, toast, token(), open(item) | null, itemOf(kind, p) | null} */
'use strict';
window.HoolaAttach = ctx => {
const {api, esc} = ctx;
const IMG = /\.(png|jpe?g|gif|webp|heic|heif|bmp|avif)$/i, VID = /\.(mp4|webm|mov|m4v|mkv|3gp)$/i,
  AUD = /\.(mp3|m4a|ogg|oga|wav|aac|opus|flac)$/i;
function kind(f) {
  const m = String(f.media || ''), n = String(f.name || '').toLowerCase(), t = String(f.type || f.mime || '');
  if (m && m !== 'other') return m;
  if (IMG.test(n) || t.startsWith('image/')) return 'image';
  if (VID.test(n) || t.startsWith('video/')) return 'video';
  if (AUD.test(n) || t.startsWith('audio/')) return 'audio';
  if (n.endsWith('.pdf') || t === 'application/pdf') return 'pdf';
  if (/\.(docx?|odt|rtf)$/.test(n)) return 'doc';
  if (/\.(xlsx?|csv|ods)$/.test(n)) return 'sheet';
  if (/\.(pptx?|odp|key)$/.test(n)) return 'slides';
  if (/\.(txt|md|json|html?|css|js|ts|py|xml|ya?ml|kt|dart|sql|log|ini|sh)$/.test(n) || t.startsWith('text/')) return 'text';
  return 'file';
}
const ext = f => (String(f.name || '').match(/\.([a-z0-9]{1,5})$/i)?.[1] || '').toUpperCase();
const pasted = f => /^pasted-text-/.test(f.name || '');
const size = n => !n ? '' : n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB';
const dur = s => { s = Math.round(+s || 0); if (!s) return ''; const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = String(s % 60).padStart(2, '0'); return h ? `${h}:${String(m).padStart(2, '0')}:${x}` : `${m}:${x}`; };
const LABEL = {pdf: 'PDF', doc: 'Document', sheet: 'Spreadsheet', slides: 'Slides', text: 'Text', audio: 'Audio', video: 'Video', image: 'Image', file: 'File'};
const ICON = {
  pdf: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  doc: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 12h6M9 15h6M9 18h3"/>',
  sheet: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 10h16M4 15h16M10 4v16"/>',
  slides: '<rect x="3" y="5" width="18" height="12" rx="2"/><path d="M12 17v3M8 20h8"/>',
  text: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  audio: '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
  video: '<rect x="3" y="5" width="14" height="14" rx="2"/><path d="M17 10l4-2v8l-4-2"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="M21 15l-5-5L5 21"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>'};
const svg = (k, cls = 'ai') => `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ICON.file}</svg>`;
const PLAY = '<span class="aplay" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z" fill="currentColor"/></svg></span>';

/* ---------- picture sources: her local pick (blob:), the server's small preview (data:), or her file (blob:) ---------- */
const LOCAL = new Map();                     // file_id -> blob: of the File she picked (kept for this page's life)
const FULL = new Map();                      // file_id -> blob: of the whole file fetched with her login
function remember(fid, url) { if (fid && url) LOCAL.set(fid, url); }
function thumbOf(f) {
  if (f.url && String(f.url).startsWith('blob:')) return f.url;
  if (f.file_id && LOCAL.has(f.file_id)) return LOCAL.get(f.file_id);
  if (f.preview) return 'data:image/jpeg;base64,' + f.preview;
  return '';
}
async function full(fid) {
  if (FULL.has(fid)) return FULL.get(fid);
  const r = await api('GET', `/api/panel/files/${encodeURIComponent(fid)}`, undefined, {raw: true});
  const u = URL.createObjectURL(await r.blob());
  FULL.set(fid, u);
  if (FULL.size > 24) { const [k, v] = FULL.entries().next().value; FULL.delete(k); URL.revokeObjectURL(v); }
  return u;
}
function forget(f) { if (f?.url && String(f.url).startsWith('blob:') && !(f.file_id && LOCAL.get(f.file_id) === f.url)) URL.revokeObjectURL(f.url); }

/* ---------- one tile ---------- */
function tile(f, i, mode) {
  const k = kind(f), t = thumbOf(f), name = esc(f.name || 'file');
  const up = mode === 'tray' && !f.file_id && !f.err, bad = mode === 'tray' && f.err;
  const meta = k === 'pdf' && f.pages ? `${f.pages} page${f.pages > 1 ? 's' : ''}` : (k === 'video' || k === 'audio') && f.duration ? dur(f.duration) : size(f.size);
  const tag = pasted(f) ? 'Pasted' : ext(f) || LABEL[k];
  let body;
  if (k === 'image' && t) body = `<img src="${esc(t)}" alt="" loading="lazy" decoding="async">`;
  else if (k === 'image') body = `<span class="aph" data-lazy="${esc(f.file_id || '')}">${svg('image')}</span>`;
  else if (k === 'video') body = (t ? `<img src="${esc(t)}" alt="" loading="lazy" decoding="async">` : `<span class="aph dark">${svg('video')}</span>`)
    + PLAY + (f.duration ? `<span class="adur">${dur(f.duration)}</span>` : '');
  else if ((k === 'pdf' || k === 'doc' || k === 'slides' || k === 'sheet') && t) body = `<span class="apage"><img src="${esc(t)}" alt="" loading="lazy" decoding="async"></span><span class="aname"><b>${name}</b><i>${esc(tag)}${meta ? ' · ' + esc(meta) : ''}</i></span>`;
  else if (k === 'text' && f.snippet) body = `<span class="asnip">${esc(f.snippet)}</span><span class="aname"><b>${name}</b><i>${esc(tag)}${meta ? ' · ' + esc(meta) : ''}</i></span>`;
  else body = `<span class="aico k-${k}">${svg(k)}</span><span class="aname"><b>${name}</b><i>${esc(tag)}${meta ? ' · ' + esc(meta) : ''}</i></span>`;
  const media = k === 'image' || k === 'video';
  const cls = `at k-${k}${media ? ' media' : ''}${up ? ' up' : ''}${bad ? ' bad' : ''}`;
  const pct = Math.max(4, Math.min(100, Math.round(f.pct || 0)));
  const over = up ? `<span class="aup" role="progressbar" aria-label="Uploading ${name}" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><i style="width:${pct}%"></i></span>`
    : bad ? `<span class="abad"><b>Upload failed</b><button type="button" data-retry="${i}">Retry</button></span>` : '';
  const x = mode === 'tray' ? `<button type="button" class="ax" data-rm="${i}" aria-label="Remove ${name}" title="Remove">✕</button>` : '';
  const label = `${f.name || 'file'}${meta ? ', ' + meta : ''}`;
  const open = mode === 'sent' || (mode === 'tray' && f.file_id) ? ` data-view="${i}" role="button" tabindex="0" aria-label="Open ${esc(label)}"` : ` aria-label="${esc(label)}"`;
  return `<div class="${cls}" title="${esc(label)}"><div class="ab"${open}>${body}</div>${over}${x}</div>`;
}
function tray(list) { return list.length ? `<div class="atray" role="list" aria-label="Attached files">${list.map((f, i) => tile(f, i, 'tray')).join('')}</div>` : ''; }

/* ---------- the tiles above her sent bubble ---------- */
function sent(files) {
  const list = (files || []).map(f => typeof f === 'string' ? {name: f} : {...f});
  const el = document.createElement('div');
  const pics = list.filter(f => kind(f) === 'image' || kind(f) === 'video').length;
  el.className = 'mua' + (list.length === 1 && pics === 1 ? ' solo' : '');
  el.innerHTML = list.map((f, i) => tile(f, i, 'sent')).join('');
  if (list.length === 1 && pics === 1 && list[0].width && list[0].height) {   // the frame keeps her picture's shape before it loads
    const ab = el.querySelector('.ab'); ab.style.aspectRatio = `${list[0].width} / ${list[0].height}`;
  }
  el._files = list;
  el.addEventListener('click', e => { const b = e.target.closest('[data-view]'); if (b) view(list, +b.dataset.view); });
  el.addEventListener('keydown', e => { const b = e.target.closest('[data-view]'); if (b && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); view(list, +b.dataset.view); } });
  lazy(el, list);
  return el;
}
function lazy(el, list) {        // a picture with no preview (old message, server restarted) loads its file when seen
  const holes = [...el.querySelectorAll('[data-lazy]')].filter(h => h.dataset.lazy);
  if (!holes.length) return;
  const load = h => full(h.dataset.lazy).then(u => { h.outerHTML = `<img src="${esc(u)}" alt="" decoding="async">`; }).catch(() => h.classList.add('gone'));
  if (!window.IntersectionObserver) { holes.forEach(load); return; }
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { io.unobserve(e.target); load(e.target); } }), {rootMargin: '400px'});
  holes.forEach(h => io.observe(h));
}

/* ---------- the full-screen viewer (pictures + video); documents go to the workspace reader ---------- */
let LB = null;
function workspaceItem(f) { return f.file_id ? ctx.itemOf?.('pc_file', {file_id: f.file_id, name: f.name, title: f.name}) : null; }
function view(list, i) {
  const f = list[i]; if (!f) return;
  const k = kind(f);
  if (!f.file_id) { ctx.toast('This file is not on the server any more.', true); return; }
  if (k !== 'image' && k !== 'video' && k !== 'audio') {
    const it = workspaceItem(f);
    if (it && ctx.open?.(it)) return;
    download(f); return;
  }
  const media = list.map((x, j) => ({x, j})).filter(o => ['image', 'video', 'audio'].includes(kind(o.x)));
  lightbox(media.map(o => o.x), media.findIndex(o => o.j === i));
}
function lightbox(items, at) {
  close();
  const back = document.activeElement;
  LB = document.createElement('div'); LB.className = 'albx'; LB.setAttribute('role', 'dialog'); LB.setAttribute('aria-modal', 'true');
  LB.innerHTML = `<div class="albhd"><span class="albn"></span><span class="albc"></span>
      <button type="button" class="albb" data-act="ws">Open in workspace</button><button type="button" class="albb" data-act="dl">Download</button>
      <button type="button" class="albi" data-act="x" aria-label="Close viewer" title="Close (Esc)">✕</button></div>
    <div class="albst"><button type="button" class="albnav prev" data-act="prev" aria-label="Previous">‹</button><div class="albm"></div><button type="button" class="albnav next" data-act="next" aria-label="Next">›</button></div>`;
  document.body.appendChild(LB); document.body.classList.add('albon');
  let cur = at, tok = 0;
  const stage = LB.querySelector('.albm');
  async function show(n) {
    cur = (n + items.length) % items.length; const f = items[cur], k = kind(f), my = ++tok;
    LB.querySelector('.albn').textContent = f.name || 'file';
    LB.querySelector('.albc').textContent = [items.length > 1 ? `${cur + 1} of ${items.length}` : '', k === 'image' && f.width ? `${f.width} × ${f.height}` : '', size(f.size)].filter(Boolean).join(' · ');
    LB.querySelectorAll('.albnav').forEach(b => b.hidden = items.length < 2);
    LB.querySelector('[data-act="ws"]').hidden = !workspaceItem(f);
    stage.querySelectorAll('video,audio').forEach(m => m.pause());
    const t = thumbOf(f);
    stage.innerHTML = k === 'image' ? (t ? `<img class="albimg low" src="${esc(t)}" alt="${esc(f.name || '')}">` : '<span class="albwait">Loading…</span>')
      : k === 'video' ? (t ? `<img class="albimg low" src="${esc(t)}" alt="">` : '') + '<span class="albwait">Loading video…</span>' : '<span class="albwait">Loading…</span>';
    try {
      const u = await full(f.file_id); if (my !== tok || !LB) return;
      if (k === 'image') {
        const img = new Image(); img.className = 'albimg'; img.alt = f.name || ''; img.decoding = 'async'; img.src = u;
        await img.decode().catch(() => {}); if (my !== tok || !LB) return;
        img.addEventListener('click', () => img.classList.toggle('zoom'));
        stage.replaceChildren(img);
      } else {
        const m = document.createElement(k === 'video' ? 'video' : 'audio'); m.controls = true; m.autoplay = true; m.playsInline = true;
        m.className = k === 'video' ? 'albvid' : 'albaud'; m.src = u; stage.replaceChildren(m);
      }
    } catch (e) {
      if (my === tok && LB) stage.innerHTML = `<span class="albwait">${esc(e.message || 'Could not open')}</span>`;
    }
  }
  LB.addEventListener('click', e => {
    const a = e.target.closest('[data-act]')?.dataset.act;
    if (a === 'x') close(); else if (a === 'prev') show(cur - 1); else if (a === 'next') show(cur + 1);
    else if (a === 'dl') download(items[cur]);
    else if (a === 'ws') { const it = workspaceItem(items[cur]); close(); if (it) ctx.open(it); }
    else if (e.target === LB || e.target.classList.contains('albst') || e.target === stage) close();
  });
  LB._key = e => {
    if (!LB) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); close(); }
    else if (e.key === 'ArrowLeft' && items.length > 1 && !/^(INPUT|TEXTAREA)$/.test(e.target.tagName)) { e.preventDefault(); e.stopImmediatePropagation(); show(cur - 1); }
    else if (e.key === 'ArrowRight' && items.length > 1 && !/^(INPUT|TEXTAREA)$/.test(e.target.tagName)) { e.preventDefault(); e.stopImmediatePropagation(); show(cur + 1); }
  };
  LB._back = back;
  document.addEventListener('keydown', LB._key, true);
  LB.querySelector('[data-act="x"]').focus();
  show(at < 0 ? 0 : at);
}
function close() {
  if (!LB) return;
  LB.querySelectorAll('video,audio').forEach(m => m.pause());
  document.removeEventListener('keydown', LB._key, true);
  const back = LB._back; LB.remove(); LB = null; document.body.classList.remove('albon');
  back?.focus?.();
}
async function download(f) {
  try {
    const r = await api('GET', `/api/panel/files/${encodeURIComponent(f.file_id)}?download=1`, undefined, {raw: true});
    const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = f.name || 'file'; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  } catch (e) { ctx.toast(e.message || 'Download failed', true); }
}

/* ---------- upload with a real progress number ---------- */
function upload(conv, file, onp) {
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open('POST', `/api/conversations/${encodeURIComponent(conv)}/files`);
    const t = ctx.token(); if (t) x.setRequestHeader('Authorization', 'Bearer ' + t);
    x.upload.onprogress = e => { if (e.lengthComputable) onp?.(e.loaded / e.total * 96); };
    x.onload = () => {
      let d = null; try { d = JSON.parse(x.responseText); } catch {}
      if (x.status >= 200 && x.status < 300 && d) { onp?.(100); resolve(d); return; }
      const m = d && (d.detail?.message || (typeof d.detail === 'string' ? d.detail : '') || d.message);
      const er = new Error(m || `Upload refused (${x.status})`); er.status = x.status; reject(er);
    };
    x.onerror = () => reject(new Error('Network problem: upload stopped'));
    x.onabort = () => { const er = new Error('Upload cancelled'); er.name = 'AbortError'; reject(er); };
    const fd = new FormData(); fd.append('file', file, file.name); x.send(fd);
    file._xhr = x;
  });
}

return {kind, tray, sent, view, upload, thumbOf, forget, remember, close, isOpen: () => !!LB};
};
