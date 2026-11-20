/* v0.999.46 CA PRACTICE - the CA document desk inside the GST & Accounts section (/console/accounts#/ca/<page>).
   Four pages: Clients (with each client's folder), Document inbox, Requests, Channels & storage. Everything comes from
   /api/practice/*; nothing is invented. A file from an unknown sender waits for her tap; a request to a client is a draft
   she reads and sends herself (never sent by itself); bot tokens are typed once and never shown back. CSP-clean: no
   inline handlers, every listener added here. Mounted by accountsdesk.js: window.HoolaCAPractice({api, esc, toast, onCount}). */
(() => {
  'use strict';
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const enc = encodeURIComponent;
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const CHAN = {whatsapp: 'WhatsApp', email: 'Email', telegram: 'Telegram', slack: 'Slack', pc: 'Your PC', upload: 'Upload', phone: 'Phone'};
  const STATE = {done: 'saved', waiting: 'waiting', failed: 'failed', inbox: 'in PC inbox', off: 'off', '': 'off'};
  const PAGES = [['clients', 'Clients'], ['inbox', 'Document inbox'], ['requests', 'Requests'], ['channels', 'Channels & storage']];
  const nowMonth = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`; };
  const prevMonth = m => { let [y, n] = m.split('-').map(Number); n -= 1; if (!n) { n = 12; y -= 1; } return `${y}-${String(n).padStart(2, '0')}`; };
  const mLabel = m => { const [y, n] = S(m).split('-').map(Number); return y && n ? `${MONTHS[n - 1]} ${y}` : S(m); };
  const mShort = m => { const n = Number(S(m).split('-')[1]); return n ? MONTHS[n - 1] : S(m); };
  const day = iso => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}); };
  const money = v => (v === null || v === undefined || v === '' || isNaN(Number(v))) ? '' : '₹' + Number(v).toLocaleString('en-IN', {maximumFractionDigits: 2});
  const list = v => S(v).split(',').map(x => x.trim()).filter(Boolean);

  window.HoolaCAPractice = function (opts) {
    const {api, esc, toast} = opts;
    const onCount = opts.onCount || (() => {});
    const C = {el: null, page: 'clients', arg: '', home: null, kinds: {}, clients: [], month: nowMonth(), q: '', adding: false,
      inbox: null, itab: 'need', open: {}, folder: null, fsel: null, req: null, rmonth: '', draft: null, seq: 0};
    const K = k => C.kinds[k] || k;

    async function loadHome() {
      try { const h = await api('GET', '/api/practice'); C.home = h; C.kinds = h.kinds || {}; onCount(Number((h.summary || {}).waiting || 0)); }
      catch (e) { toast(e.message, true); }
    }
    function count() { return Number(((C.home || {}).summary || {}).waiting || 0); }

    function mount(el) {
      C.el = el;
      el.addEventListener('click', onClick);
      el.addEventListener('change', onChange);
      el.addEventListener('input', onInput);
      el.addEventListener('submit', onSubmit);
      el.addEventListener('dragover', e => { const z = e.target.closest('.ca-drop'); if (z) { e.preventDefault(); z.classList.add('over'); } });
      el.addEventListener('dragleave', e => { const z = e.target.closest('.ca-drop'); if (z && !z.contains(e.relatedTarget)) z.classList.remove('over'); });
      el.addEventListener('drop', e => {
        const z = e.target.closest('.ca-drop'); if (!z) return;
        e.preventDefault(); z.classList.remove('over');
        upload([...(e.dataTransfer?.files || [])], z.dataset.client || selectedUploadClient());
      });
      loadHome();
    }

    async function show(page, arg) {
      C.page = PAGES.some(p => p[0] === page) || page === 'folder' ? page : 'clients';
      C.arg = S(arg);
      const seq = ++C.seq;
      if (!C.home) await loadHome();
      if (seq !== C.seq) return;
      C.el.innerHTML = '<div class="empty">Loading…</div>';
      try {
        if (C.page === 'clients') await drawClients(seq);
        else if (C.page === 'folder') await drawFolder(seq);
        else if (C.page === 'inbox') await drawInbox(seq);
        else if (C.page === 'requests') await drawRequests(seq);
        else drawChannels();
      } catch (e) { if (seq === C.seq) C.el.innerHTML = `<div class="card"><p class="lead">${esc(e.message)}</p></div>`; }
    }
    const go = h => { location.hash = '#/ca/' + h; };

    /* ------------------------------------------------------------ Clients */
    async function drawClients(seq) {
      const r = await api('GET', `/api/practice/clients?month=${enc(C.month)}&q=${enc(C.q)}`);
      if (seq !== C.seq) return;
      C.clients = r.clients || [];
      const done = C.clients.filter(c => c.complete).length, filesM = C.clients.reduce((a, c) => a + Number(c.files_month || 0), 0);
      const state = c => c.complete ? '<span class="pill ok"><span class="dt"></span>Complete</span>'
        : !Number(c.files_month) ? '<span class="pill bad"><span class="dt"></span>Nothing yet</span>'
        : `<span class="pill warn"><span class="dt"></span>${esc(K(c.missing[0]))} missing${c.missing.length > 1 ? ` +${c.missing.length - 1}` : ''}</span>`;
      C.el.innerHTML = `
        <div class="ca-head"><div><h1 class="sd-h">Clients</h1><p class="lead">Each client's documents, filed by financial year, month and kind.</p></div>
          <button class="btn" type="button" data-ca="add">Add client</button></div>
        <div class="ca-tiles">
          <div class="card kpi"><span class="n">${esc(mShort(C.month))} complete</span><span class="v">${C.clients.length ? `${done}/${C.clients.length}` : '0'}</span></div>
          <div class="card kpi"><span class="n">Files this month</span><span class="v">${filesM}</span></div>
          <div class="card kpi"><span class="n">Waiting in inbox</span><span class="v">${count()}</span>${count() ? '<a class="c" href="#/ca/inbox">Open the inbox</a>' : ''}</div></div>
        ${C.adding ? clientForm() : ''}
        <div class="ca-tools"><input class="in" type="search" id="caQ" placeholder="Search by name, GSTIN, phone or email" aria-label="Search clients" value="${esc(C.q)}">
          <label class="ca-month">Month <input class="in" type="month" id="caMonth" value="${esc(C.month)}" aria-label="Month"></label></div>
        <div class="card">${C.clients.length ? `<div class="scroll"><table class="tb ca-tb"><thead><tr><th>Client</th><th>Sends on</th><th>${esc(mShort(C.month))}</th><th>Last file</th><th></th></tr></thead><tbody>
          ${C.clients.map(c => `<tr><td><b>${esc(c.name)}</b><div class="ca-sub num">${esc(c.gstin || 'No GSTIN')}</div></td>
            <td>${esc((c.sends_on || []).join(', ') || '—')}</td><td>${state(c)}</td>
            <td>${c.last ? `${esc(c.last.name)}<div class="ca-sub">${esc(day(c.last.at))} · ${esc(CHAN[c.last.channel] || c.last.channel)}</div>` : '<span class="mut">—</span>'}</td>
            <td><button class="btn soft sm" type="button" data-folder="${esc(c.id)}">Open folder</button></td></tr>`).join('')}</tbody></table></div>`
        : `<p class="empty">${C.q ? 'No client matches that search.' : 'No clients yet — add your first client.'}</p>`}</div>`;
    }
    function clientForm(c) {
      c = c || {};
      return `<form class="card form ca-form" data-form="${c.id ? 'edit' : 'add'}">
        <h3 class="wide">${c.id ? 'Senders for this client' : 'Add a client'}</h3>
        ${c.id ? '' : `<label>Name<input class="in" name="name" required></label>
        <label>GSTIN<input class="in" name="gstin" autocomplete="off" spellcheck="false"></label>
        <label>PAN<input class="in" name="pan" autocomplete="off" spellcheck="false"></label>`}
        <label>WhatsApp numbers (comma separated)<input class="in" name="phones" value="${esc((c.phones || []).join(', '))}"></label>
        <label>Emails (comma separated)<input class="in" name="emails" value="${esc((c.emails || []).join(', '))}"></label>
        <div class="wide ca-row"><button class="btn" type="submit">${c.id ? 'Save senders' : 'Add client'}</button>
          ${c.id ? '' : '<button class="btn soft" type="button" data-ca="cancel">Cancel</button>'}</div></form>`;
    }

    /* ------------------------------------------------------------ Client folder */
    async function drawFolder(seq) {
      const r = await api('GET', `/api/practice/clients/${enc(C.arg)}/folder`);
      if (seq !== C.seq) return;
      C.folder = r;
      const c = r.client, files = r.files || [];
      const months = [...new Set(files.map(f => f.month).filter(m => /^\d{4}-\d{2}$/.test(m)))].sort().reverse();
      const tree = r.tree || {};
      const sel = C.fsel;
      const shown = files.filter(f => !sel || (sel.kind ? (f.kind_label === sel.kind && (sel.perm || f.month === sel.month)) : f.month === sel.month));
      const fyOf = m => { const [y, n] = S(m).split('-').map(Number); if (!y || !n) return 'FY unknown'; const st = n >= 4 ? y : y - 1; return `FY ${st}-${String(st + 1).slice(2)}`; };
      const mdOf = m => { const n = Number(S(m).split('-')[1]); return n ? `${String(n).padStart(2, '0')} ${MONTHS[n - 1]}` : 'Undated'; };
      const kindMonth = (fy, md) => {           // the month key (YYYY-MM) behind a tree node, as the server names its folders
        const f = files.find(x => x.kind !== 'permanent' && fyOf(x.month) === fy && mdOf(x.month) === md); return f ? f.month : '';
      };
      const senders = [...(c.phones || []).map(p => 'WhatsApp ' + p), ...(c.emails || []), ...(c.telegram || []).map(t => 'Telegram ' + t), ...(c.slack || []).map(t => 'Slack ' + t)];
      C.el.innerHTML = `
        <div class="ca-head"><div><button class="btn soft sm" type="button" data-go="clients">← Clients</button>
          <h1 class="sd-h" style="margin-top:10px">${esc(c.name)}</h1>
          <p class="lead num">${esc([c.gstin, c.pan].filter(Boolean).join(' · ') || 'No GSTIN or PAN saved')}</p></div>
          <div class="ca-row"><label class="btn soft" for="caUp">Upload</label>
            <input type="file" id="caUp" multiple hidden data-client="${esc(c.id)}">
            ${months.length ? `<select class="in ca-zipm" id="caZipM" aria-label="Month for the ZIP">${months.map(m => `<option value="${esc(m)}"${sel && sel.month === m ? ' selected' : ''}>${esc(mLabel(m))}</option>`).join('')}</select>
            <button class="btn" type="button" data-ca="zip">Download month as ZIP</button>` : ''}</div></div>
        <div class="card ca-senders"><div><b>Sends from</b> <span class="mut">${esc(senders.join(' · ') || 'No senders saved yet. Files from unknown senders wait in the inbox.')}</span></div>
          ${r.telegram_link ? `<div>Telegram link for this client: <a href="${esc(r.telegram_link)}" target="_blank" rel="noopener">${esc(r.telegram_link)}</a></div>` : ''}
          <button class="btn soft sm" type="button" data-ca="senders">Edit senders</button></div>
        <div id="caSendersForm"></div>
        <div class="ca-folder">
          <nav class="card ca-tree" aria-label="Folder">
            <button type="button" class="ca-node${!sel ? ' on' : ''}" data-node="">All files <span>${files.length}</span></button>
            ${Object.keys(tree).length ? Object.entries(tree).map(([fy, ms]) => {
              const perm = fy === K('permanent');
              return `<div class="ca-fy">${esc(fy)}</div>${Object.entries(ms).map(([md, ks]) => {
                const m = perm ? '' : kindMonth(fy, md);
                return `${md ? `<button type="button" class="ca-node ca-m${sel && !sel.kind && sel.month === m ? ' on' : ''}" data-node="${esc(m)}">${esc(md)}</button>` : ''}
                  ${Object.entries(ks).map(([k, n]) => `<button type="button" class="ca-node ca-k${sel && sel.kind === k && (perm || sel.month === m) ? ' on' : ''}" data-node="${esc(m)}" data-kind="${esc(k)}"${perm ? ' data-perm="1"' : ''}>${esc(k)} <span>${n}</span></button>`).join('')}`;
              }).join('')}`;
            }).join('') : '<p class="mut ca-sub">Nothing filed yet.</p>'}
          </nav>
          <div class="card ca-files">${shown.length ? `<div class="scroll"><table class="tb ca-tb"><thead><tr><th>File</th><th>Came by</th><th>Read as</th><th>Amount</th><th>Kept in</th><th></th></tr></thead><tbody>
            ${shown.map(f => `<tr><td><b>${esc(f.name)}</b><div class="ca-sub">${esc(mLabel(f.month))}${f.orig_name && f.orig_name !== f.name ? ' · sent as ' + esc(f.orig_name) : ''}</div></td>
              <td>${esc(CHAN[f.channel] || f.channel)}${f.sender ? `<div class="ca-sub">${esc(f.sender)}</div>` : ''}</td>
              <td>${esc(f.kind_label)}</td><td class="num">${esc(money((f.facts || {}).total))}</td>
              <td class="ca-sub">Hoola cloud · Drive ${esc(STATE[f.drive] || f.drive)} · PC ${esc(STATE[f.pc] || f.pc)}</td>
              <td><button class="ib" type="button" data-dl="${esc(f.id)}" data-name="${esc(f.name)}" aria-label="Download ${esc(f.name)}" title="Download">
                <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg></button></td></tr>`).join('')}</tbody></table></div>`
            : `<div class="ca-drop" data-client="${esc(c.id)}"><p>No files here yet. Drop files here or use Upload — they go straight into ${esc(c.name)}'s folder.</p></div>`}</div>
        </div>`;
    }
    async function download(path, name) {
      try {
        const r = await api('GET', path, undefined, {raw: true});
        const b = await r.blob(), u = URL.createObjectURL(b), a = document.createElement('a');
        a.href = u; a.download = name || 'file'; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(u), 4000);
      } catch (e) { toast(e.message, true); }
    }

    /* ------------------------------------------------------------ Document inbox */
    async function drawInbox(seq) {
      const [r, cl] = await Promise.all([api('GET', '/api/practice/inbox'), api('GET', '/api/practice/clients')]);
      if (seq !== C.seq) return;
      C.inbox = r; C.clients = cl.clients || [];
      if (C.home && C.home.summary) C.home.summary.waiting = r.waiting_count;
      onCount(Number(r.waiting_count || 0));
      const need = C.itab === 'need';
      const rows = need ? (r.waiting || []) : (r.filed || []);
      C.el.innerHTML = `
        <div class="ca-head"><div><h1 class="sd-h">Document inbox</h1><p class="lead">Files that came in from your clients. A file from someone Hoola does not know waits here for your tap.</p></div></div>
        <div class="seg" role="tablist" aria-label="Inbox">
          <button type="button" role="tab" data-itab="need" aria-pressed="${need}">Needs you · ${Number(r.waiting_count || 0)}</button>
          <button type="button" role="tab" data-itab="filed" aria-pressed="${!need}">Filed today · ${Number(r.filed_count || 0)}</button></div>
        <div class="card ca-drop" data-client="">
          <p><b>Upload files</b> — drop them here, or <label class="ca-link" for="caInUp">choose files</label>.</p>
          <input type="file" id="caInUp" multiple hidden>
          <label class="ca-month">For <select class="in" id="caUpFor" aria-label="Upload for which client"><option value="">Not sure — keep in the inbox</option>
            ${C.clients.map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></label></div>
        <div class="ca-cards">${rows.length ? rows.map(f => need ? waitCard(f) : filedCard(f)).join('')
          : `<p class="empty">${need ? 'Nothing is waiting for you. New files from your clients land in their folders by themselves.' : 'Nothing was filed in the last 24 hours.'}</p>`}</div>`;
    }
    function waitCard(f) {
      const g = f.guess || {}, o = C.open[f.id] || '';
      const months = Array.isArray(g.months) ? g.months : [];
      return `<article class="card ca-wait" data-fid="${esc(f.id)}">
        <div class="ca-wt"><b>${esc(f.name)}</b><span class="pill warn"><span class="dt"></span>Needs you</span></div>
        <p class="ca-why">${esc(f.why || 'Hoola needs you to say where this goes.')}</p>
        <div class="ca-sub">Came by ${esc(CHAN[f.channel] || f.channel)}${f.sender ? ' from ' + esc(f.sender) : ''} · ${esc(day(f.at))}</div>
        ${f.message ? `<blockquote class="ca-msg">${esc(f.message)}</blockquote>` : ''}
        <div class="ca-sub">Hoola thinks: ${esc(K(g.kind || f.kind))}${g.client ? ' for ' + esc(g.client) : ''}${g.month ? ', ' + esc(mLabel(g.month)) : ''}${(f.facts || {}).total ? ' · ' + esc(money(f.facts.total)) : ''}</div>
        <div class="ca-row">
          ${g.client_id && months.length ? `<span class="mut">Which month?</span>${months.map(m => `<button class="btn sm" type="button" data-act="month" data-month="${esc(m)}">${esc(mLabel(m))}</button>`).join('')}`
            : g.client_id ? `<button class="btn sm" type="button" data-act="yes">Yes, add to ${esc(g.client)}</button>` : ''}
          <button class="btn soft sm" type="button" data-act="other" aria-expanded="${o === 'other'}">Another client</button>
          <button class="btn soft sm" type="button" data-act="new" aria-expanded="${o === 'new'}">New client</button>
          <button class="btn soft sm bad" type="button" data-act="drop">Not for me</button></div>
        ${o === 'other' ? `<div class="ca-row ca-pick"><select class="in" data-pick aria-label="Which client">${C.clients.length ? C.clients.map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('') : '<option value="">No clients yet</option>'}</select>
          <label class="ca-chk"><input type="checkbox" data-remember checked> Remember this sender</label>
          <button class="btn sm" type="button" data-act="file-other"${C.clients.length ? '' : ' disabled'}>File it here</button></div>` : ''}
        ${o === 'new' ? `<div class="ca-row ca-pick"><input class="in" data-newname placeholder="New client's name" aria-label="New client's name">
          <button class="btn sm" type="button" data-act="file-new">Create and file</button></div>` : ''}
      </article>`;
    }
    function filedCard(f) {
      return `<article class="card ca-wait"><div class="ca-wt"><b>${esc(f.name)}</b><span class="pill ok"><span class="dt"></span>Filed</span></div>
        <div class="ca-sub">${esc(f.client || '—')} · ${esc(f.kind_label)} · ${esc(mLabel(f.month))} · came by ${esc(CHAN[f.channel] || f.channel)}</div>
        ${f.client_id ? `<div class="ca-row"><button class="btn soft sm" type="button" data-folder="${esc(f.client_id)}">Open folder</button></div>` : ''}</article>`;
    }
    async function fileIt(fid, body, okMsg) {
      try { const r = await api('POST', `/api/practice/files/${enc(fid)}/file`, body); delete C.open[fid]; toast(okMsg || `Filed in ${r.client || 'the folder'}.`); await loadHome(); show('inbox'); }
      catch (e) { toast(e.message, true); }
    }
    function selectedUploadClient() { const s = C.el.querySelector('#caUpFor'); return s ? s.value : ''; }
    async function upload(files, clientId) {
      if (!files.length) return;
      let n = 0, wait = 0;
      for (const f of files) {
        try {
          const fd = new FormData(); fd.append('file', f, f.name || 'file'); if (clientId) fd.append('client_id', clientId);
          const r = await api('POST', '/api/practice/upload', undefined, {form: fd});
          for (const x of r.files || []) { n++; if (x.status === 'waiting') wait++; }
        } catch (e) { toast(`${f.name}: ${e.message}`, true); }
      }
      if (n) toast(wait ? `${n} file${n > 1 ? 's' : ''} uploaded · ${wait} waiting for you in the inbox.` : `${n} file${n > 1 ? 's' : ''} filed.`);
      await loadHome();
      show(C.page, C.arg);
    }

    /* ------------------------------------------------------------ Requests */
    async function drawRequests(seq) {
      const r = await api('GET', `/api/practice/requests?month=${enc(C.rmonth)}`);
      if (seq !== C.seq) return;
      C.req = r; C.rmonth = r.month; C.kinds = r.kinds || C.kinds;
      const on = new Set(r.checklist || []);
      C.el.innerHTML = `
        <div class="ca-head"><div><h1 class="sd-h">Requests</h1><p class="lead">Clients still missing something. Hoola drafts the message; you read it and send it.</p></div>
          <label class="ca-month">Month <input class="in" type="month" id="caRMonth" value="${esc(r.month)}" aria-label="Month"></label></div>
        <div class="card"><h3>What every client sends each month</h3>
          <div class="ca-row" style="margin-top:10px">${Object.entries(C.kinds).filter(([k]) => k !== 'permanent').map(([k, n]) =>
            `<button class="chip" type="button" data-check="${esc(k)}" aria-pressed="${on.has(k)}">${esc(n)}</button>`).join('')}</div></div>
        <div class="card">${(r.missing || []).length ? `<div class="scroll"><table class="tb ca-tb"><thead><tr><th>Client</th><th>Missing for ${esc(mLabel(r.month))}</th><th>Asked</th><th></th></tr></thead><tbody>
          ${r.missing.map(c => `<tr><td><b>${esc(c.name)}</b><div class="ca-sub">${esc((c.sends_on || []).join(', ') || 'No sender saved')}</div></td>
            <td>${c.missing.map(k => `<span class="pill warn">${esc(K(k))}</span>`).join(' ')}</td>
            <td>${c.asked ? esc(day(c.asked)) : '<span class="mut">Not yet</span>'}</td>
            <td><button class="btn soft sm" type="button" data-review="${esc(c.id)}">Review &amp; send</button></td></tr>`).join('')}</tbody></table></div>`
          : `<p class="empty">${'Every client has sent everything on the list for ' + esc(mLabel(r.month)) + '.'}</p>`}</div>
        <aside class="ca-panel" id="caPanel" hidden aria-label="Request draft"></aside>`;
    }
    async function openDraft(cid) {
      const p = C.el.querySelector('#caPanel'); if (!p) return;
      p.hidden = false; p.innerHTML = '<div class="empty">Writing the draft…</div>';
      try {
        const d = await api('GET', `/api/practice/requests/${enc(cid)}/draft?month=${enc(C.rmonth)}`);
        C.draft = {d, ch: (d.channels || [])[0] || ''};
        paintDraft();
      } catch (e) { p.innerHTML = `<p class="lead">${esc(e.message)}</p>`; }
    }
    function paintDraft() {
      const p = C.el.querySelector('#caPanel'); if (!p || !C.draft) return;
      const {d, ch} = C.draft;
      p.innerHTML = `<div class="ca-wt"><h3>To ${esc(d.client.name)}</h3><button class="ib" type="button" data-ca="close" aria-label="Close the draft" title="Close">×</button></div>
        <p class="ca-sub">For ${esc(mLabel(d.month))}. Nothing is sent until you tap Send.</p>
        ${(d.channels || []).length ? `<div class="ca-row">${d.channels.map(c => `<button class="chip" type="button" data-ch="${esc(c)}" aria-pressed="${c === ch}">${esc(CHAN[c] || c)}</button>`).join('')}</div>`
          : '<p class="lead">This client has no email or WhatsApp number saved. Add one in their folder first.</p>'}
        ${ch === 'email' ? `<label class="ca-lbl">Subject<input class="in" id="caSubj" value="${esc(d.subject)}"></label>` : ''}
        <label class="ca-lbl">Message<textarea class="in" id="caText" rows="10">${esc(d.text)}</textarea></label>
        <div class="ca-row"><button class="btn" type="button" data-ca="send"${ch ? '' : ' disabled'}>Send</button></div>
        <div id="caSaid"></div>`;
    }
    async function sendDraft(btn) {
      const {d, ch} = C.draft || {};
      if (!d || !ch) return;
      const text = S(C.el.querySelector('#caText')?.value).trim(), subject = S(C.el.querySelector('#caSubj')?.value || d.subject);
      if (!text) { toast('The message is empty.', true); return; }
      btn.disabled = true;
      try {
        const r = await api('POST', `/api/practice/requests/${enc(d.client.id)}/send`, {channel: ch, text, month: d.month, subject});
        const said = C.el.querySelector('#caSaid');
        if (r.sent) { toast(`Sent by ${CHAN[r.channel] || r.channel}.`); C.draft = null; show('requests'); return; }
        if (r.link && said) said.innerHTML = `<p class="lead">${esc(r.say || '')}</p><a class="btn" href="${esc(r.link)}" target="_blank" rel="noopener">Open in WhatsApp</a>`;
      } catch (e) { toast(e.message, true); }
      btn.disabled = false;
    }

    /* ------------------------------------------------------------ Channels & storage */
    function drawChannels() {
      const s = (C.home || {}).settings || {};
      const sw = (k, label, on) => `<button type="button" class="ca-sw" role="switch" aria-checked="${!!on}" data-set="${esc(k)}" aria-label="${esc(label)}"><span></span></button>`;
      const card = (title, body, right, cls) => `<section class="card ca-ch${cls ? ' ' + cls : ''}"><div class="ca-wt"><h3>${esc(title)}</h3>${right || ''}</div>${body}</section>`;
      C.el.innerHTML = `
        <div class="ca-head"><div><h1 class="sd-h">Channels &amp; storage</h1><p class="lead">Where your clients send documents, and where Hoola keeps them.</p></div></div>
        <section class="card form" data-form="name"><label class="wide">Practice name (signs your requests)<input class="in" name="practice_name" value="${esc(s.practice_name)}" placeholder="e.g. Sharma & Co."></label>
          <div class="wide ca-row"><button class="btn sm" type="submit" data-ca="savename">Save name</button>
          <span class="ca-chk">${sw('on', 'Collect documents for my clients', s.on)} Collect documents for my clients</span></div></section>
        <h2 class="sd-h ca-h2">Where clients send</h2>
        <div class="ca-grid">
          ${card('WhatsApp', '<p class="ca-sub">Files clients send to your WhatsApp Business number.</p>', sw('whatsapp_on', 'WhatsApp', s.whatsapp_on))}
          ${card('Email', '<p class="ca-sub">Attachments in mail from your clients\' saved addresses, read from your connected mailbox.</p>', sw('email_on', 'Email', s.email_on))}
          ${card('Telegram', (s.telegram || {}).on ? `<p class="ca-sub">Connected as @${esc((s.telegram || {}).bot)}. Each client gets their own link in their folder.</p>`
            : `<form class="ca-tok" data-form="telegram"><label class="ca-lbl">Bot token (from @BotFather)<input class="in" type="password" name="token" autocomplete="off" required></label><button class="btn sm" type="submit">Connect Telegram</button></form>`,
            (s.telegram || {}).on ? '<span class="pill ok"><span class="dt"></span>On</span>' : '')}
          ${card('Slack', `${(s.slack || {}).on ? '<p class="ca-sub">Connected. Files clients share with your bot land in the inbox.</p>' : ''}
            <form class="ca-tok" data-form="slack"><label class="ca-lbl">Bot token<input class="in" type="password" name="bot_token" autocomplete="off" required></label>
              <label class="ca-lbl">Signing secret<input class="in" type="password" name="signing_secret" autocomplete="off" required></label>
              <button class="btn sm" type="submit">${(s.slack || {}).on ? 'Replace Slack keys' : 'Connect Slack'}</button></form><div id="caSlackUrl"></div>`,
            (s.slack || {}).on ? '<span class="pill ok"><span class="dt"></span>On</span>' : '')}
          ${card('Your PC', `<p class="ca-sub">A folder on your PC (through Hoola Desktop): files are copied there, and files you drop in a client's "_Drop here" folder come in.</p>
            <form class="ca-tok" data-form="pc"><label class="ca-lbl">Folder path<input class="in" name="pc_root" value="${esc(s.pc_root)}" placeholder="D:\\Clients"></label><button class="btn soft sm" type="submit">Save folder</button></form>`, sw('pc_on', 'Your PC', s.pc_on))}
          ${card('LinkedIn', `<p class="ca-sub">${esc((s.linkedin || {}).why || 'LinkedIn cannot be connected.')}</p>`, '<span class="pill">Not possible</span>', 'off')}
        </div>
        <h2 class="sd-h ca-h2">Where files are kept</h2>
        <div class="ca-grid">
          ${card('Hoola cloud', '<p class="ca-sub">Every filed document is kept here, always.</p>', '<span class="pill ok"><span class="dt"></span>Always</span>')}
          ${card('Google Drive', '<p class="ca-sub">A copy in your Drive, in the same folders (Client / FY / month / kind).</p>', sw('drive_on', 'Google Drive', s.drive_on))}
          ${card('Your PC', '<p class="ca-sub">A copy in the PC folder above, when Hoola Desktop is running.</p>', sw('pc_on', 'Your PC copy', s.pc_on))}
        </div>`;
    }
    async function saveSettings(body, msg) {
      try { const s = await api('PUT', '/api/practice/settings', body); if (C.home) C.home.settings = s; toast(msg || 'Saved.'); if (C.page === 'channels') drawChannels(); return s; }
      catch (e) { toast(e.message, true); }
    }

    /* ------------------------------------------------------------ events */
    async function onClick(e) {
      const t = e.target;
      const fo = t.closest('[data-folder]'); if (fo) { go('folder/' + fo.dataset.folder); return; }
      const g = t.closest('[data-go]'); if (g && C.el.contains(g)) { e.stopPropagation(); go(g.dataset.go); return; }
      const it = t.closest('[data-itab]'); if (it) { C.itab = it.dataset.itab; show('inbox'); return; }
      const nd = t.closest('[data-node]');
      if (nd) { C.fsel = nd.dataset.node || nd.dataset.kind ? {month: nd.dataset.node, kind: nd.dataset.kind || '', perm: !!nd.dataset.perm} : null; show('folder', C.arg); return; }
      const dl = t.closest('[data-dl]'); if (dl) { download(`/api/practice/files/${enc(dl.dataset.dl)}`, dl.dataset.name); return; }
      const rv = t.closest('[data-review]'); if (rv) { openDraft(rv.dataset.review); return; }
      const ch = t.closest('[data-ch]'); if (ch && C.draft) { const txt = C.el.querySelector('#caText'); if (txt) C.draft.d.text = txt.value; C.draft.ch = ch.dataset.ch; paintDraft(); return; }
      const ck = t.closest('[data-check]');
      if (ck) {
        const cur = new Set((C.req || {}).checklist || []);
        cur.has(ck.dataset.check) ? cur.delete(ck.dataset.check) : cur.add(ck.dataset.check);
        if (!cur.size) { toast('Keep at least one kind on the list.', true); return; }
        await saveSettings({checklist: [...cur]}, 'Checklist saved.'); show('requests'); return;
      }
      const sw = t.closest('[data-set]');
      if (sw) { await saveSettings({[sw.dataset.set]: sw.getAttribute('aria-checked') !== 'true'}); return; }
      const act = t.closest('[data-act]');
      if (act) {
        const card = act.closest('[data-fid]'), fid = card && card.dataset.fid; if (!fid) return;
        const f = ((C.inbox || {}).waiting || []).find(x => x.id === fid) || {}, gs = f.guess || {};
        const a = act.dataset.act;
        if (a === 'yes') fileIt(fid, {client_id: gs.client_id, month: gs.month || '', remember_sender: true});
        else if (a === 'month') fileIt(fid, {client_id: gs.client_id, month: act.dataset.month, remember_sender: true});
        else if (a === 'other' || a === 'new') { C.open[fid] = C.open[fid] === a ? '' : a; show('inbox'); }
        else if (a === 'file-other') {
          const cid = card.querySelector('[data-pick]')?.value; if (!cid) return;
          fileIt(fid, {client_id: cid, month: gs.month || '', remember_sender: !!card.querySelector('[data-remember]')?.checked});
        } else if (a === 'file-new') {
          const name = S(card.querySelector('[data-newname]')?.value).trim(); if (!name) { toast("Give the new client's name.", true); return; }
          fileIt(fid, {client_id: '', new_client: {name}, month: gs.month || '', remember_sender: true}, `Added ${name} and filed it.`);
        } else if (a === 'drop') {
          try { await api('POST', `/api/practice/files/${enc(fid)}/drop`); toast('Taken out of the inbox. The file is not kept.'); await loadHome(); show('inbox'); }
          catch (err) { toast(err.message, true); }
        }
        return;
      }
      const b = t.closest('[data-ca]'); if (!b) return;
      const k = b.dataset.ca;
      if (k === 'add') { C.adding = !C.adding; show('clients'); }
      else if (k === 'cancel') { C.adding = false; show('clients'); }
      else if (k === 'zip') { const m = C.el.querySelector('#caZipM')?.value; if (m) download(`/api/practice/clients/${enc(C.arg)}/zip?month=${enc(m)}`, `${C.folder.client.folder || C.folder.client.name} ${m}.zip`); }
      else if (k === 'senders') { const box = C.el.querySelector('#caSendersForm'); if (box) box.innerHTML = box.innerHTML ? '' : clientForm(C.folder.client); }
      else if (k === 'close') { const p = C.el.querySelector('#caPanel'); if (p) p.hidden = true; C.draft = null; }
      else if (k === 'send') sendDraft(b);
      else if (k === 'savename') { e.preventDefault(); const f = b.closest('[data-form]'); saveSettings({practice_name: S(f.querySelector('[name=practice_name]').value).trim()}, 'Practice name saved.'); }
    }
    function onChange(e) {
      const t = e.target;
      if (t.id === 'caMonth') { C.month = t.value || nowMonth(); show('clients'); }
      else if (t.id === 'caRMonth') { C.rmonth = t.value || prevMonth(nowMonth()); show('requests'); }
      else if (t.id === 'caUp') { upload([...t.files], t.dataset.client); t.value = ''; }
      else if (t.id === 'caInUp') { upload([...t.files], selectedUploadClient()); t.value = ''; }
    }
    function onInput(e) {
      if (e.target.id !== 'caQ') return;
      C.q = e.target.value;
      clearTimeout(onInput._t);
      onInput._t = setTimeout(async () => {
        const at = e.target.selectionStart; await show('clients');
        const q = C.el.querySelector('#caQ'); if (q) { q.focus(); try { q.setSelectionRange(at, at); } catch {} }
      }, 300);
    }
    async function onSubmit(e) {
      const f = e.target.closest('[data-form]'); if (!f) return;
      e.preventDefault();
      const v = n => S(f.querySelector(`[name=${n}]`)?.value).trim();
      const btn = f.querySelector('[type=submit]'); if (btn) btn.disabled = true;
      try {
        const kind = f.dataset.form;
        if (kind === 'add') {
          await api('POST', '/api/practice/clients', {name: v('name'), gstin: v('gstin'), pan: v('pan'), phones: list(v('phones')), emails: list(v('emails'))});
          toast('Client added.'); C.adding = false; await loadHome(); show('clients');
        } else if (kind === 'edit') {
          await api('PATCH', `/api/practice/clients/${enc(C.arg)}`, {phones: list(v('phones')), emails: list(v('emails'))});
          toast('Senders saved.'); show('folder', C.arg);
        } else if (kind === 'name') {
          await saveSettings({practice_name: v('practice_name')}, 'Practice name saved.');
        } else if (kind === 'pc') {
          await saveSettings({pc_root: v('pc_root')}, 'PC folder saved.');
        } else if (kind === 'telegram') {
          const s = await api('POST', '/api/practice/telegram', {token: v('token')});
          f.reset(); if (C.home) C.home.settings = s; toast('Telegram connected.'); drawChannels();
        } else if (kind === 'slack') {
          const s = await api('POST', '/api/practice/slack', {bot_token: v('bot_token'), signing_secret: v('signing_secret')});
          f.reset(); const url = s.events_url; delete s.events_url;
          if (C.home) C.home.settings = Object.assign({}, C.home.settings, s.slack ? s : {slack: {on: true}});
          drawChannels();
          const box = C.el.querySelector('#caSlackUrl');
          if (box && url) box.innerHTML = `<p class="ca-sub">Paste this as the Request URL under Event Subscriptions in your Slack app:</p><input class="in num" readonly value="${esc(url)}" aria-label="Slack events URL">`;
          toast('Slack keys saved.');
        }
      } catch (err) { toast(err.message, true); }
      if (btn && btn.isConnected) btn.disabled = false;
    }

    return {mount, show, count, PAGES};
  };
})();
