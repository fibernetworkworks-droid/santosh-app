/* HOOLA DOCUMENTS - the page (/console/documents; docs/DOCUMENT_KIT_PLAN.md D7). Its own full-screen app like Hoola
   Prompting: the same sign-in as the console (its token in this browser), the /api/dockit routes, the same strict CSP.

   Home = every pdf_kit tool as a card (the iLovePDF grid). A tool = her files (uploaded once, the chat's own file store)
   + its few options + Run -> the SAME pdf_kit the chat uses, the result with its download link. Workflows = ready-made
   and her saved chains, run on one file or a batch. A password is never typed here: a lock gives a one-time link. */
'use strict';
(function () {
  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));
  const esc = v => (v == null ? '' : String(v)).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  let TOKEN = ''; try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch (e) { /* private window */ }
  if (!TOKEN) { location.replace('/console/'); return; }
  async function api(method, path, body, form) {
    const headers = {Authorization: 'Bearer ' + TOKEN}; let payload;
    if (form) payload = form;
    else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    let data = null; try { data = await r.json(); } catch (e) { /* no body */ }
    if (!r.ok) { const bad = data && Array.isArray(data.detail) && data.detail[0];
      throw new Error((data && ((typeof data.detail === 'string' ? data.detail : '') || data.error)) || (bad ? String(bad.msg) : '') || `The server refused the request (${r.status})`); }
    return data;
  }
  function toast(msg, bad) { const t = $('#toast'); t.textContent = String(msg); t.className = 'hd-toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200); }
  const I = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const ICON = {home: I('<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>'),
    flows: I('<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.5 6H14a4 4 0 0 1 4 4v5.5"/>'),
    back: I('<path d="M15 6l-6 6 6 6"/>')};
  const ACCEPT = {pdf: '.pdf,application/pdf', pdfs: '.pdf,application/pdf,image/*', two: '.pdf,application/pdf',
    files: 'image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp,.rtf,.txt,.csv', any: '*/*'};
  const NEEDS = {pdf: 'one PDF', pdfs: 'two or more files, in order', two: 'two PDFs: the OLD version first, then the NEW', files: 'pictures or Word / Excel / PowerPoint files', url: 'a link'};
  const st = {cat: null, tool: null, files: [], carry: false, q: '', busy: false, flows: null, steps: []};

  function shell(active, body) {
    const nav = (key, hash, label) => `<a class="hd-nav" href="${hash}" ${active === key ? 'aria-current="page"' : ''}>${ICON[key]}<span>${esc(label)}</span></a>`;
    $('#hd').innerHTML = `<div class="hd"><nav class="hd-side" aria-label="Hoola Documents">
        <div class="hd-brand"><img src="/static/hoola-icon-192.png" alt=""><span>Hoola Documents</span></div>
        ${nav('home', '#/', 'All tools')}${nav('flows', '#/flows', 'Workflows')}
        <div class="hd-grow"></div>
        <a class="hd-nav" href="/console/">${ICON.back}<span>Back to the console</span></a>
      </nav><main class="hd-main" id="hdMain"><div class="hd-wrap">${body}</div></main></div>`;
  }
  const allTools = () => st.cat.groups.flatMap(g => g.items.map(t => ({...t, group: g.group})));

  /* ---------- home: the grid ---------- */
  function home() {
    const q = st.q.trim().toLowerCase();
    const groups = st.cat.groups.map(g => ({...g, items: g.items.filter(t => !q || (t.title + ' ' + t.line).toLowerCase().includes(q))})).filter(g => g.items.length);
    shell('home', `<div class="hd-top"><div><h1 class="hd-h1">Every PDF tool, on Hoola's own server</h1>
        <p class="hd-sub">Free, no key, your original is never changed, and every result is checked before you get it. Files are kept 24 hours.</p></div>
        <input class="hd-search" id="q" type="search" placeholder="Find a tool (compress, merge, Word…)" value="${esc(st.q)}" aria-label="Find a tool"></div>
      ${groups.map(g => `<h2 class="hd-g">${esc(g.group)}</h2><div class="hd-grid">${g.items.map(t =>
        `<button type="button" class="hd-card" data-tool="${esc(t.id)}"><b>${esc(t.title)}</b><span>${esc(t.line)}</span><i>${esc(NEEDS[t.input] || '')}</i></button>`).join('')}</div>`).join('')
        || '<p class="hd-note">No tool matches. Try "compress" or "merge".</p>'}`);
    const qi = $('#q'); qi.addEventListener('input', () => { st.q = qi.value; const pos = qi.selectionStart; home(); const n = $('#q'); n.focus(); n.setSelectionRange(pos, pos); });
    $$('[data-tool]').forEach(b => b.addEventListener('click', () => { location.hash = '#/t/' + b.dataset.tool; }));
  }

  /* ---------- one tool ---------- */
  function optField(o, vals) {
    const [key, label, kind, def, choices] = o; const v = vals && key in vals ? vals[key] : def;
    if (kind === 'bool') return `<label class="chk"><input type="checkbox" data-opt="${esc(key)}" data-kind="bool" ${v ? 'checked' : ''}>${esc(label)}</label>`;
    if (kind === 'select') return `<label>${esc(label)}<select class="hd-in" data-opt="${esc(key)}">${choices.map(c => `<option ${String(c) === String(v) ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select></label>`;
    return `<label>${esc(label)}<input class="hd-in" data-opt="${esc(key)}" ${kind === 'number' ? 'type="number" step="any"' : 'type="text"'} value="${esc(v == null ? '' : v)}"></label>`;
  }
  function readOpts(root) {
    const out = {};
    (root || document).querySelectorAll('[data-opt]').forEach(el => {
      const k = el.dataset.opt;
      if (el.dataset.kind === 'bool') out[k] = el.checked;
      else if (el.value !== '') out[k] = el.type === 'number' ? Number(el.value) : el.value;
    });
    return out;
  }
  function fileList() {
    return st.files.length ? `<ul class="hd-files">${st.files.map((f, i) => `<li><span class="k">${i + 1}</span><span class="n">${esc(f.name)}</span>
        <span class="k">${f.size ? Math.max(1, Math.round(f.size / 1024)) + ' KB' : ''}</span>
        <button type="button" class="hd-b sm" data-up="${i}" ${i ? '' : 'disabled'} aria-label="Move up">↑</button>
        <button type="button" class="hd-b sm" data-down="${i}" ${i < st.files.length - 1 ? '' : 'disabled'} aria-label="Move down">↓</button>
        <button type="button" class="hd-b sm" data-del="${i}" aria-label="Remove ${esc(f.name)}">✕</button></li>`).join('')}</ul>` : '';
  }
  function tool(id) {
    const t = allTools().find(x => x.id === id);
    if (!t) { location.hash = '#/'; return; }
    if (st.tool !== id) { st.tool = id; st.files = st.carry ? st.files.slice(0, t.input === 'pdf' ? 1 : 50) : []; st.carry = false; }   // only "Use next" carries a file over
    const isUrl = t.input === 'url';
    shell('home', `<p><a class="hd-b sm" href="#/">${ICON.back} All tools</a></p>
      <div class="hd-top" style="margin-top:16px"><div><h1 class="hd-h1">${esc(t.title)}</h1><p class="hd-sub">${esc(t.line)}</p></div></div>
      <div class="hd-panel">
        ${isUrl ? '' : `<div class="hd-drop" id="drop"><b>Drop ${esc(NEEDS[t.input] || 'files')} here</b><span class="hd-note">or</span>
          <label class="hd-b"><input type="file" id="pick" class="hd-sr" accept="${esc(ACCEPT[t.input] || '*/*')}" ${t.input === 'pdf' ? '' : 'multiple'}>Choose files</label>
          <span class="hd-note">Up to 25 MB each. Bigger files: ask Hoola in chat with a Google Drive link.</span></div>
          <div id="files">${fileList()}</div>`}
        ${t.opts.length ? `<div class="hd-opts">${t.opts.map(o => optField(o)).join('')}</div>` : ''}
        <div class="hd-row"><button type="button" class="hd-b pri" id="go">${esc(t.title)}</button>
          ${t.input === 'pdf' || t.input === 'files' ? '<label class="chk hd-note"><input type="checkbox" id="each"> Run on each file (batch)</label>' : ''}
          <span class="hd-note" id="state"></span></div>
        <div id="res"></div></div>`);
    if (!isUrl) wireDrop(t);
    $('#go').addEventListener('click', () => runTool(t));
  }
  function wireDrop(t) {
    const drop = $('#drop'), pick = $('#pick');
    const add = list => upload(Array.from(list), t);
    pick.addEventListener('change', () => { add(pick.files); pick.value = ''; });
    drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('on'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('on'));
    drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('on'); add(e.dataTransfer.files); });
    $('#files').addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      const i = Number(b.dataset.up ?? b.dataset.down ?? b.dataset.del);
      if (b.dataset.up != null && i > 0) [st.files[i - 1], st.files[i]] = [st.files[i], st.files[i - 1]];
      else if (b.dataset.down != null && i < st.files.length - 1) [st.files[i + 1], st.files[i]] = [st.files[i], st.files[i + 1]];
      else if (b.dataset.del != null) st.files.splice(i, 1);
      $('#files').innerHTML = fileList();
    });
  }
  async function upload(list, t) {
    for (const f of list) {
      if (f.size > 25 * 1024 * 1024) { toast(`${f.name} is over 25 MB. Send it to Hoola in chat as a Drive link.`, true); continue; }
      $('#state').innerHTML = `<span class="hd-spin"></span> Uploading ${esc(f.name)}…`;
      const fd = new FormData(); fd.append('file', f, f.name);
      try {
        const r = await api('POST', '/api/dockit/upload', undefined, fd);
        if (t && t.input === 'pdf') st.files = [];
        st.files.push({file_id: r.file_id, name: r.name || f.name, size: r.size || f.size});
      } catch (e) { toast(e.message, true); }
    }
    $('#state').textContent = '';
    const box = $('#files'); if (box) box.innerHTML = fileList();
  }
  function argsFor(t, opts) {
    const ids = st.files.map(f => f.file_id), a = {...opts};
    if (t.input === 'url') return a;
    if (!ids.length) throw new Error('Add ' + (NEEDS[t.input] || 'a file') + ' first.');
    if (t.input === 'pdfs' && ids.length < 2) throw new Error('Add two or more files.');
    if (t.input === 'two' && ids.length !== 2) throw new Error('Add exactly two PDFs: the old version, then the new.');
    if (t.input === 'pdf') a.file_id = ids[0]; else a.file_ids = ids;
    return a;
  }
  async function runTool(t) {
    if (st.busy) return;
    let action = t.id, args;
    try { args = argsFor(t, readOpts($('.hd-opts'))); } catch (e) { toast(e.message, true); return; }
    const each = $('#each') && $('#each').checked;
    if (each && st.files.length > 1) { args = {steps: [{action: t.id, ...readOpts($('.hd-opts'))}], file_ids: st.files.map(f => f.file_id), batch: true, workflow: t.title}; action = 'flow'; }
    else if (t.input === 'pdf' && st.files.length > 1) { toast('This tool takes one PDF. Tick "Run on each file" for all of them.', true); return; }
    await go(action, args, $('#res'));
  }
  async function go(action, args, out) {
    st.busy = true; const btn = $('#go'); if (btn) btn.disabled = true;
    $('#state') && ($('#state').innerHTML = '<span class="hd-spin"></span> Working on it…');
    out.innerHTML = '';
    try {
      const r = await api('POST', '/api/dockit/run', {action, args});
      out.innerHTML = result(r.result || {});
      wireResult(out);
    } catch (e) {
      out.innerHTML = `<div class="hd-res"><h3 class="bad">Not done</h3><p>${esc(e.message)}</p></div>`;
    } finally {
      st.busy = false; if (btn) btn.disabled = false; $('#state') && ($('#state').textContent = '');
    }
  }

  /* ---------- the result ---------- */
  function outRow(f) {
    if (!f || !f.file_id) return '';
    return `<div class="hd-out"><span class="n">${esc(f.name || 'file')}</span>${f.kb != null ? `<span class="hd-note">${esc(f.kb)} KB</span>` : ''}
      ${f.url ? `<a class="hd-b sm acc" href="${esc(f.url)}" download="${esc(f.name || '')}">Download</a>` : ''}
      <button type="button" class="hd-b sm" data-next="${esc(f.file_id)}" data-name="${esc(f.name || '')}">Use next</button></div>`;
  }
  function result(r) {
    const outs = [];
    if (r.zip) outs.push(r.zip);
    else if (Array.isArray(r.files) && r.files.length && typeof r.files[0] === 'object' && r.files[0].file_id) outs.push(...r.files);
    else if (r.file_id) outs.push(r);
    if (r.report) outs.push(r.report);
    if (r.preview_file_id) outs.push({file_id: r.preview_file_id, name: 'Redaction preview', url: r.preview_url});
    const bits = [];
    if (outs.length) bits.push(outs.map(outRow).join(''));
    if (r.checked) bits.push(`<p class="ok">${esc(r.checked)}</p>`);
    if (r.password_link) bits.push(`<p><a class="hd-b sm acc" href="${esc(r.password_link)}" target="_blank" rel="noopener noreferrer">See the password once</a> <span class="hd-note">${esc(r.expires || '')}</span></p>`);
    (r.password_links || []).forEach(l => bits.push(`<p>${esc(l.file)}: <a class="hd-b sm acc" href="${esc(l.link)}" target="_blank" rel="noopener noreferrer">See the password once</a></p>`));
    if (r.link) bits.push(`<p><a class="hd-b sm acc" href="${esc(r.link)}" target="_blank" rel="noopener noreferrer">Open the private page</a> <span class="hd-note">${esc(r.expires || '')}</span></p>`);
    if (r.redact_id) bits.push(`<p class="warn">Nothing is removed yet. Check the preview, then:</p><p><button type="button" class="hd-b pri" data-apply="${esc(r.redact_id)}">Remove for good</button></p>`);
    if (r.answer || r.summary) bits.push(`<p class="hd-pre">${esc(r.answer || r.summary)}</p>`);
    if (r.say) bits.push(`<p>${esc(r.say)}</p>`);
    if (r.same) bits.push('<p>The words of the two PDFs are the same.</p>');
    if (Array.isArray(r.parts)) bits.push(`<p>${r.parts.length} documents found:</p><ul>${r.parts.map(x => `<li>${esc(x.title)} - pages ${esc(x.pages)}</li>`).join('')}</ul>
      <p><button type="button" class="hd-b pri" data-ranges="${esc(JSON.stringify(r.ranges || []))}">Split this way</button></p>`);
    const lists = [['money_changed', 'warn'], ['dates_changed', 'warn'], ['changes', 'hd-note'], ['warnings', 'warn'], ['notes', 'hd-note'], ['check_these', 'warn'], ['did_not_fit', 'warn']];
    lists.forEach(([k, cls]) => { const v = r[k]; if (Array.isArray(v) && v.length) bits.push(`<ul class="${cls}">${v.slice(0, 20).map(x => `<li>${esc(typeof x === 'string' ? x : JSON.stringify(x))}</li>`).join('')}</ul>`); });
    if (Array.isArray(r.failed) && r.failed.length) bits.push(`<p class="bad">${r.failed.length} file(s) failed:</p><ul class="bad">${r.failed.map(f => `<li>${esc(f.why)}</li>`).join('')}</ul>`);
    if (r.fields) bits.push(`<p>${esc(r.count)} fillable boxes: ${esc(r.fields.slice(0, 30).map(f => f.name).join(', '))}</p>`);
    if (r.files && !outs.length && Array.isArray(r.files) && r.files[0] && r.files[0].pages != null) bits.push(`<ul>${r.files.map(f => `<li>${esc(f.name)} - ${esc(f.pages)} pages, ${esc(f.kb || '')} KB${f.scanned ? ', scanned' : ''}</li>`).join('')}</ul>`);
    if (r.kept_for) bits.push(`<p class="hd-note">Kept for ${esc(r.kept_for)}.</p>`);
    if (!bits.length) bits.push('<p>Done.</p>');
    return `<div class="hd-res"><h3 class="ok">Done</h3>${bits.join('')}</div>`;
  }
  function wireResult(out) {
    out.querySelectorAll('[data-next]').forEach(b => b.addEventListener('click', () => {
      st.files = [{file_id: b.dataset.next, name: b.dataset.name}]; st.carry = true; st.tool = null; location.hash = '#/'; toast('Pick the next tool - this file is ready in it.');
    }));
    out.querySelectorAll('[data-apply]').forEach(b => b.addEventListener('click', () => go('redact_apply', {redact_id: b.dataset.apply}, out)));
    out.querySelectorAll('[data-ranges]').forEach(b => b.addEventListener('click', () => {
      if (!st.files[0]) return toast('The file is gone from this page; open the tool again.', true);
      go('split', {file_id: st.files[0].file_id, mode: 'ranges', ranges: JSON.parse(b.dataset.ranges)}, out);
    }));
  }

  /* ---------- workflows ---------- */
  async function flowsView() {
    shell('flows', '<p class="hd-note"><span class="hd-spin"></span> Loading…</p>');
    try { st.flows = await api('GET', '/api/dockit/flows'); } catch (e) { toast(e.message, true); st.flows = {mine: [], ready_made: []}; }
    const titles = Object.fromEntries(allTools().map(t => [t.id, t.title]));
    const row = (f, mine) => `<div class="hd-flow"><div><b>${esc(f.name)}</b><span>${esc(f.line ? f.line + ' · ' : '')}${esc(f.steps)}${mine && f.runs ? ` · run ${esc(f.runs)} times` : ''}</span></div>
      <div class="hd-row" style="margin:0"><button type="button" class="hd-b sm pri" data-run="${esc(f.key)}" data-title="${esc(f.name)}">Run</button>
      ${mine ? `<button type="button" class="hd-b sm" data-delflow="${esc(f.key)}">Delete</button>` : ''}</div></div>`;
    shell('flows', `<div class="hd-top"><div><h1 class="hd-h1">Workflows</h1><p class="hd-sub">A chain of steps run as one job - on one file, or on a whole batch.</p></div></div>
      <div class="hd-panel"><h2 class="hd-g" style="margin-top:0">Your workflows</h2>${st.flows.mine.map(f => row(f, true)).join('') || '<p class="hd-note">None saved yet. Build one below.</p>'}</div>
      <div class="hd-panel"><h2 class="hd-g" style="margin-top:0">Ready-made</h2>${st.flows.ready_made.map(f => row(f, false)).join('')}</div>
      <div class="hd-panel"><h2 class="hd-g" style="margin-top:0">Build a workflow</h2>
        <p class="hd-note">Merge / photos-to-PDF only as the first step; lock, split and conversions only as the last. Options as key=value, e.g. target_kb=2000.</p>
        <ol class="hd-steps" id="steps"></ol>
        <div class="hd-row"><select class="hd-in" id="addStep" aria-label="Add a step">${st.cat.steps.map(s => `<option value="${esc(s)}">${esc(titles[s] || s)}</option>`).join('')}</select>
          <button type="button" class="hd-b" id="addBtn">Add step</button></div>
        <div class="hd-row"><input class="hd-in" id="fname" placeholder="Name, e.g. CA ke liye" aria-label="Workflow name">
          <button type="button" class="hd-b pri" id="saveFlow">Save workflow</button></div></div>
      <div class="hd-panel" id="runBox" hidden></div>`);
    const draw = () => { $('#steps').innerHTML = st.steps.map((s, i) => `<li><span class="num">${i + 1}</span><b>${esc(titles[s.action] || s.action)}</b>
        <input class="hd-in" data-sopt="${i}" placeholder="options (key=value, …)" value="${esc(s.opts || '')}">
        <button type="button" class="hd-b sm" data-sdel="${i}" aria-label="Remove step ${i + 1}">✕</button></li>`).join(''); };
    draw();
    $('#addBtn').addEventListener('click', () => { if (st.steps.length >= st.cat.max_steps) return toast('That is the most steps a workflow can have.', true); st.steps.push({action: $('#addStep').value, opts: ''}); draw(); });
    $('#steps').addEventListener('input', e => { const i = e.target.dataset.sopt; if (i != null) st.steps[i].opts = e.target.value; });
    $('#steps').addEventListener('click', e => { const i = e.target.closest('[data-sdel]'); if (i) { st.steps.splice(Number(i.dataset.sdel), 1); draw(); } });
    $('#saveFlow').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/dockit/flows', {name: $('#fname').value, steps: stepsOut()}); toast(`Saved: ${r.saved}`); st.steps = []; flowsView(); }
      catch (e) { toast(e.message, true); }
    });
    $$('[data-delflow]').forEach(b => b.addEventListener('click', async () => {
      if (!confirm('Delete this workflow?')) return;
      try { await api('DELETE', '/api/dockit/flows/' + encodeURIComponent(b.dataset.delflow)); flowsView(); } catch (e) { toast(e.message, true); }
    }));
    $$('[data-run]').forEach(b => b.addEventListener('click', () => runFlowBox(b.dataset.run, b.dataset.title)));
  }
  function stepsOut() {
    return st.steps.map(s => {
      const o = {action: s.action};
      String(s.opts || '').split(',').map(x => x.trim()).filter(Boolean).forEach(kv => {
        const m = kv.match(/^([a-z_]+)\s*=\s*(.+)$/i); if (!m) return;
        const v = m[2].trim(); o[m[1]] = /^-?\d+(\.\d+)?$/.test(v) ? Number(v) : v === 'true' ? true : v === 'false' ? false : v;
      });
      return o;
    });
  }
  function runFlowBox(key, title) {
    const box = $('#runBox'); box.hidden = false; st.tool = null; if (!st.carry) st.files = []; st.carry = false;
    box.innerHTML = `<h2 class="hd-g" style="margin-top:0">Run "${esc(title)}"</h2>
      <div class="hd-drop" id="drop"><b>Drop the files here</b>
        <label class="hd-b"><input type="file" id="pick" class="hd-sr" multiple>Choose files</label></div>
      <div id="files">${fileList()}</div>
      <div class="hd-row"><button type="button" class="hd-b pri" id="go">Run</button>
        <label class="chk hd-note"><input type="checkbox" id="each"> Each file on its own (batch)</label><span class="hd-note" id="state"></span></div><div id="res"></div>`;
    wireDrop({input: 'files'});
    box.scrollIntoView({behavior: 'smooth', block: 'start'});
    $('#go').addEventListener('click', () => {
      if (!st.files.length) return toast('Add the files first.', true);
      go('flow', {workflow: key, file_ids: st.files.map(f => f.file_id), batch: $('#each').checked}, $('#res'));
    });
  }

  /* ---------- the router ---------- */
  function route() {
    const h = location.hash || '#/';
    const m = h.match(/^#\/t\/([a-z_]+)/);
    if (m) return tool(m[1]);
    if (h.startsWith('#/flows')) return flowsView();
    st.tool = null; return home();
  }
  (async () => {
    try { st.cat = await api('GET', '/api/dockit/tools'); }
    catch (e) { $('#hd').innerHTML = `<p class="hd-boot">${esc(e.message)}</p>`; return; }
    window.addEventListener('hashchange', route);
    route();
  })();
})();
