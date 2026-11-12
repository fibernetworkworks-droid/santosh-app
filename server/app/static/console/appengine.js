/* v0.814 APP ENGINE 1 (L8 of docs/LOVABLE_STUDIO_PLAN.md): the React app lane of the Web Studio.
   #/apps       her apps + "New app" (one line of what it should do, a palette); Hoola builds it in the chat
   #/app/<id>   the app's own Hoola chat on the left; Preview / Code / Design / Versions / Publish on the right.
   The preview is the newest version built in the box. Code is read-only here (changes go through Hoola); going live
   is HER tap with a confirm, the exact version she sees. Uses the Studio's own helpers (window.HoolaWSKit). */
(() => {
  'use strict';
  const S = v => (v == null ? '' : String(v));
  const L = v => (Array.isArray(v) ? v : []);
  const PALS = {calm: ['#f7f7f8', '#4f46e5', '#0ea5a4'], warm: ['#fbf7f2', '#c2410c', '#a16207'], fresh: ['#f3faf6', '#15803d', '#0369a1'],
    bold: ['#ffffff', '#e11d48', '#7c3aed'], night: ['#0d0f14', '#8b7cff', '#2dd4bf']};
  const ST = {id: '', app: null, tab: 'preview', device: 'pc', conv: '', rows: [], waiting: false, started: 0, poll: null,
    file: '', fileCode: null, err: '', sig: '', building: false, gen: 0,
    select: false, pick: null, pend: {}, ptext: null, sel: [], errs: [], line: 0, theme: null, shown: 0};
  // v0.825 L9 the live preview of a style choice: the same values the token classes give
  const CSSOF = {
    color: v => ({color: `var(--color-${v})`}), bg: v => ({'background-color': `var(--color-${v})`}),
    size: v => ({'font-size': {xs: '.75rem', sm: '.875rem', base: '1rem', lg: '1.125rem', xl: '1.25rem', '2xl': '1.5rem', '3xl': '1.875rem', '4xl': '2.25rem'}[v] || ''}),
    weight: v => ({'font-weight': {normal: '400', medium: '500', semibold: '600', bold: '700'}[v] || ''}),
    pad: v => ({padding: v === '' ? '' : `${Number(v) * 0.25}rem`}),
    radius: v => ({'border-radius': {none: '0', control: 'var(--radius-control)', card: 'var(--radius-card)', full: '9999px'}[v] || ''}),
    align: v => ({'text-align': v})};
  const FAM = [['color', 'Text colour'], ['bg', 'Background'], ['size', 'Text size'], ['weight', 'Weight'], ['pad', 'Padding'], ['radius', 'Corners'], ['align', 'Align']];
  let K = null;

  const k = () => (K = K || window.HoolaWSKit);
  const enc = encodeURIComponent;
  const secs = s => { s = Math.max(0, Math.round(s)); return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`; };

  function stop() { clearTimeout(ST.poll); ST.poll = null; }
  addEventListener('hashchange', () => { if (!/^#\/app\//.test(location.hash)) stop(); });

  /* ================= the list ================= */
  async function listPage() {
    const {api, esc, ico, sidebar, APP} = k();
    let r = {apps: [], status: {}};
    try { r = await api('GET', '/api/appengine'); } catch (e) { r.error = e.message; }
    const eng = (r.status || {}).engine || {};
    const card = a => `<div class="cw"><a class="card ae-card" href="#/app/${enc(S(a.id))}">
        <span class="ae-thumb" aria-hidden="true">${ico('app', 26)}</span>
        <span class="ct"><b class="ell">${esc(a.name)}</b><span class="mut sm">App ${esc(a.number)} · ${a.version ? 'version ' + esc(a.version) : 'not built yet'}${a.live_version ? ' · live' : ''}</span></span>
        ${a.live_version ? '<span class="pill ok">Live</span>' : S(a.status) === 'failed' ? '<span class="pill bad">Needs attention</span>' : ''}</a></div>`;
    const pals = Object.entries(PALS).map(([n, c], i) => `<label class="ae-pal"><input type="radio" name="palette" value="${n}" ${i === 0 ? 'checked' : ''}>
        <span class="sw">${c.map(x => `<i style="background:${x}"></i>`).join('')}</span><span>${n[0].toUpperCase() + n.slice(1)}</span></label>`).join('');
    APP.innerHTML = `<div class="home">${sidebar('apps')}<main class="hmain"><section class="wrap ae">
      <div class="sec"><h2 style="font-size:24px">Apps</h2><span class="pill v">Beta</span></div>
      <p class="mut">Real React apps: screens, forms, lists, dashboards. Hoola writes the code and builds it in its locked box; you see every version and nothing goes live until you tap. A brochure website stays a website.</p>
      ${eng.ok === false ? `<div class="panel ae-warn" role="status"><b>Apps cannot be built on this server yet.</b> ${esc(eng.why || '')}</div>` : ''}
      ${r.error ? `<div class="panel ae-warn" role="alert">${esc(r.error)}</div>` : ''}
      <form class="panel ae-new" data-ae-form="new">
        <label class="ae-l" for="aeName">App name</label>
        <input id="aeName" name="name" maxlength="80" placeholder="Shop staff tasks" required>
        <label class="ae-l" for="aeBrief">What should it do?</label>
        <textarea id="aeBrief" name="brief" rows="3" maxlength="2000" placeholder="A task list for my shop staff: add a task, mark it done, see what is left today"></textarea>
        <fieldset class="ae-pals"><legend class="ae-l">Colours</legend>${pals}</fieldset>
        <div class="ae-row"><span class="mut sm">Data stays on the page for now (marked sample); sign-in and saved data come with Hoola Cloud.</span><span class="sp"></span>
          <button class="b pri" type="submit">${ico('plus', 16)}Create app</button></div>
      </form>
      <section class="panel ae-imp"><h3>Bring in a project</h3>
        <p class="mut sm">From a ZIP (this app's own export, GitHub's "Download ZIP", another builder's export) or from a GitHub repository. Files that break Hoola's rules (design tokens, safety, vetted packages) are not brought in; they are listed with the reason, and Hoola can fix them.</p>
        <form class="ae-row" data-ae-form="imp-zip"><input type="file" name="zip" accept=".zip,application/zip" aria-label="ZIP file" required><button class="b" type="submit">Import ZIP</button></form>
        <form class="ae-row" data-ae-form="imp-gh"><input name="repo" maxlength="140" placeholder="owner/repository, e.g. asha/shop-app" aria-label="GitHub repository" required><button class="b" type="submit">Import from GitHub</button></form>
        <div id="aeImpOut" role="status" aria-live="polite"></div></section>
      <div class="sec"><h2>Your apps</h2></div>
      ${L(r.apps).length ? `<div class="grid">${L(r.apps).map(card).join('')}</div>` : '<div class="panel mut">No app yet.</div>'}
    </section></main></div>`;
  }

  async function createApp(form) {
    const {api, toast, go} = k();
    const fd = new FormData(form);
    const name = S(fd.get('name')).trim(), brief = S(fd.get('brief')).trim();
    if (!name) { toast('Give the app a name.', true); return; }
    const btn = form.querySelector('button[type=submit]'); btn.disabled = true; btn.textContent = 'Creating…';
    try {
      const a = await api('POST', '/api/appengine', {name, brief, palette: S(fd.get('palette')) || 'calm'});
      const c = await newConv(a);
      if (brief) await send(a, c, `Build this app: ${brief}`);
      go('#/app/' + enc(S(a.id)));
    } catch (e) { toast(e.message, true); btn.disabled = false; btn.textContent = 'Create app'; }
  }

  async function newConv(a) {
    const {api} = k();
    const c = S((await api('POST', '/api/conversations')).id);
    api('PATCH', `/api/conversations/${enc(c)}`, {title: `App · ${S(a.name)}`}).catch(() => {});
    await api('PATCH', `/api/appengine/${enc(S(a.id))}`, {conversation_id: c});
    return c;
  }

  async function send(a, c, text) {
    const {api} = k();
    const hints = [`Web Studio App Engine: this chat is only about app ${S(a.number)} "${S(a.name)}" (app id ${S(a.id)}). Work on THIS app with the app_engine tool; never start a new app or website unless I ask for one.`];
    for (const x of L(ST.sel)) {                              // v0.825 the parts she selected in the preview (no square brackets)
      const [f, ln] = S(x.hs).split(':');
      hints.push(`selected part: <${S(x.tag)}> in ${f} line ${ln}${x.hc ? ' (component ' + S(x.hc) + ')' : ''}, its words: "${S(x.text).replace(/[\[\]"]/g, '').slice(0, 80)}"`);
    }
    ST.sel = [];
    await api('POST', `/api/conversations/${enc(c)}/messages`, {text, hints, client_id: 'ae-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8)});
  }

  /* ================= the workspace ================= */
  async function workspace(id, tab) {
    const {api, APP} = k();
    if (ST.id !== id) Object.assign(ST, {id, conv: '', rows: [], waiting: false, file: '', fileCode: null, err: '', sig: '', device: 'pc'});
    ST.tab = ['preview', 'code', 'design', 'cloud', 'versions', 'publish'].includes(tab) ? tab : 'preview';
    ST.app = await api('GET', `/api/appengine/${enc(id)}`);
    ST.conv = S(ST.app.conversation_id);
    if (!ST.conv) ST.conv = await newConv(ST.app);
    APP.innerHTML = `<div class="ae-shell" data-ae-root>
      <header class="ae-top" id="aeTop"></header>
      <div class="ae-body"><section class="ae-chat" aria-label="Hoola chat"><div class="ae-msgs" id="aeMsgs" aria-live="polite"></div>
        <div class="ae-pills" id="aePills" hidden></div>
        <form class="ae-comp" data-ae-form="say"><label for="aeSay" class="sr">Message Hoola</label>
          <textarea id="aeSay" rows="2" maxlength="6000" placeholder="Tell Hoola what to change…"></textarea>
          <button class="go" type="submit" aria-label="Send">${k().ico('up', 18)}</button></form></section>
        <section class="ae-pane"><nav class="ae-tabs" id="aeTabs" role="tablist"></nav><div class="ae-view" id="aeView"></div></section></div></div>`;
    drawTop(); drawTabs(); await drawView(); await readChat(); readErrs(); tick();
  }

  function stateLine(a) {
    const lb = a.last_build || {};
    if (a.held) return ['Hoola is changing the app - the preview updates when the change is complete', 'v'];
    if (S(a.status) === 'building') return ['Building in the box…', 'v'];
    if (a.dirty && a.version) return ['Changes are being built…', 'v'];
    if (lb.ok === false && lb.why && !a.version) return [S(lb.why), 'bad'];
    if (lb.ok === false) return [`The last build failed - the preview still shows version ${a.version}`, 'bad'];
    if (!a.version) return ['Not built yet', ''];
    return [`Version ${a.version}${lb.seconds ? ` · built in ${lb.seconds}s` : ''}${lb.types_ok === false ? ' · TypeScript problems' : ''}`, lb.types_ok === false ? 'warn' : 'ok'];
  }

  function drawTop() {
    const {esc, ico} = k(), a = ST.app, [t, c] = stateLine(a);
    const el = document.getElementById('aeTop'); if (!el) return;
    el.innerHTML = `<a class="b ghost sm" href="#/apps">${ico('back', 16)}Apps</a><b class="ell ae-name">${esc(a.name)}</b>
      <span class="pill ${c}" id="aeState">${esc(t)}</span><span class="sp"></span>
      ${a.live_version ? `<a class="b ghost sm" href="${esc(a.live_url)}" target="_blank" rel="noopener">${ico('ext', 15)}Live: version ${esc(a.live_version)}</a>` : ''}
      <button class="b sm" type="button" data-ae="build">${ico('hist', 15)}Rebuild</button>
      <button class="b pri sm" type="button" data-ae="tab" data-ae-tab="publish">Publish</button>`;
  }

  function drawTabs() {
    const T = [['preview', 'Preview'], ['code', 'Code'], ['design', 'Design'], ['cloud', 'Cloud'], ['versions', 'Versions'], ['publish', 'Publish']];
    const el = document.getElementById('aeTabs'); if (!el) return;
    el.innerHTML = T.map(([key, label]) => `<button type="button" role="tab" aria-selected="${ST.tab === key}" data-ae="tab" data-ae-tab="${key}">${label}</button>`).join('');
  }

  async function drawView() {
    const {esc, ico, api} = k(), a = ST.app, el = document.getElementById('aeView'); if (!el) return;
    const lb = a.last_build || {};
    // a redraw that waited on the server must not paint over a newer one (she may have changed tab meanwhile)
    const gen = ++ST.gen, tab = ST.tab, fresh = () => gen === ST.gen && tab === ST.tab && document.getElementById('aeView') === el;
    if (ST.tab === 'preview') {
      const probs = [...L(lb.build_problems), ...L(lb.types)].slice(0, 6);
      const prob = (lb.ok === false || lb.types_ok === false) && probs.length
        ? `<div class="ae-probs" role="status"><b>${lb.ok === false ? 'The build failed' : 'TypeScript found problems'}</b> - Hoola reads these too.<ul>${probs.map(x => `<li><code>${esc(S(x.file) || '?')}${x.line ? ':' + esc(x.line) : ''}</code> ${esc(S(x.message))}</li>`).join('')}</ul></div>` : '';
      const dev = `<div class="seg ae-dev" role="group" aria-label="Device"><button type="button" data-ae="dev" data-ae-dev="pc" aria-pressed="${ST.device === 'pc'}">Computer</button><button type="button" data-ae="dev" data-ae-dev="phone" aria-pressed="${ST.device === 'phone'}">Phone</button></div>`;
      const sel = `<button class="b sm${ST.select ? ' on' : ''}" type="button" data-ae="select" aria-pressed="${ST.select}" title="Point at a part of the app (S)">${ico('edit', 15)}Select</button>`;
      const ebar = `<div id="aeEbar">${ebarHtml()}</div>`;
      el.innerHTML = `<div class="ae-bar">${dev}${a.preview ? sel : ''}<span class="sp"></span>${a.preview ? `<a class="b ghost sm" href="${esc(a.preview)}" target="_blank" rel="noopener">${ico('ext', 15)}Open in a new tab</a>` : ''}</div>${ebar}${prob}
        ${a.preview ? `<div class="ae-stage"><div class="ae-frame ${ST.device}"><iframe title="App preview" id="aeFrame" sandbox="allow-scripts allow-forms allow-popups" referrerpolicy="no-referrer" src="${esc(a.preview)}?v=${esc(a.version)}"></iframe></div><div class="ae-sel" id="aeSel" ${ST.pick ? '' : 'hidden'}></div></div>`
          : `<div class="panel mut ae-empty">${S(a.status) === 'building' || a.dirty ? 'The first version is being built…' : 'No version yet.'}</div>`}`;
      ST.shown = a.version;
      if (ST.pick) drawPick();
      return;
    }
    if (ST.tab === 'code') {
      const full = await api('GET', `/api/appengine/${enc(a.id)}`);
      if (!fresh()) return;
      const files = L(full.files).filter(f => S(f.path) !== 'package-lock.json');
      if (!ST.file) ST.file = (files.find(f => S(f.path) === 'src/App.tsx') || files[0] || {}).path || '';
      let code = '';
      if (ST.file) { try { code = S((await api('GET', `/api/appengine/${enc(a.id)}/file?path=${enc(ST.file)}&from_line=${Math.max(1, ST.line - 150)}`)).code); } catch (e) { code = e.message; } }
      if (!fresh()) return;
      el.innerHTML = `<div class="ae-code"><nav class="ae-files" aria-label="Files">${files.map(f => `<button type="button" data-ae="file" data-ae-file="${esc(f.path)}" aria-current="${f.path === ST.file}">${esc(f.path)}${f.locked ? ' <span class="mut sm">locked</span>' : ''}</button>`).join('')}</nav>
        <div class="ae-src"><div class="ae-bar"><code>${esc(ST.file)}</code><span class="sp"></span><span class="mut sm">Read only here - ask Hoola for changes</span></div><pre tabindex="0">${code.split('\n').map(l => { const n = Number((/^\s*(\d+)\|/.exec(l) || [])[1]) || 0; return `<span class="ln${n && n === ST.line ? ' hot' : ''}" data-ln="${n}">${esc(l)}</span>`; }).join('\n')}</pre></div></div>`;
      el.querySelector('.ln.hot')?.scrollIntoView({block: 'center'});
      return;
    }
    if (ST.tab === 'design') {
      const full = await api('GET', `/api/appengine/${enc(a.id)}`);
      if (!fresh()) return;
      const th = full.theme || {}, cols = th.colors || {};
      el.innerHTML = `<div class="ae-pad"><h3>Colours</h3><p class="mut sm">Every screen uses these names only, so one change here changes the whole app.</p>
        <div class="ae-pals">${Object.entries(PALS).map(([n, c]) => `<button type="button" class="ae-pal${S(full.palette) === n ? ' on' : ''}" data-ae="pal" data-ae-pal="${n}" aria-pressed="${S(full.palette) === n}"><span class="sw">${c.map(x => `<i style="background:${x}"></i>`).join('')}</span><span>${n[0].toUpperCase() + n.slice(1)}</span></button>`).join('')}</div>
        <div class="ae-toks">${Object.entries(cols).map(([n, v]) => `<div class="ae-tok"><i style="background:${esc(v)}"></i><b>${esc(n)}</b><code>${esc(v)}</code></div>`).join('')}</div>
        <p class="mut sm">Text on background: contrast ${esc(th.contrast_ink_on_bg)} · text on buttons: ${esc(th.contrast_primary_ink)} (4.5 or more reads well).</p></div>`;
      return;
    }
    if (ST.tab === 'cloud') {                                   // v0.827 HOOLA CLOUD: her data, rules, members
      let o;
      try { o = await api('GET', `/api/appengine/${enc(a.id)}/cloud`); } catch (e) { if (fresh()) el.innerHTML = `<div class="ae-probs">${esc(e.message)}</div>`; return; }
      if (!fresh()) return;
      const ds = ST.ds === 'live' ? 'live' : 'preview';
      const lists = L((o.schema || {}).lists).filter(x => !x.hidden);
      const rowsBy = {};
      await Promise.all(lists.map(async x => { try { rowsBy[x.key] = L((await api('GET', `/api/appengine/${enc(a.id)}/cloud/${ds}/rows/${enc(x.key)}`)).rows); } catch (e) { rowsBy[x.key] = []; } }));
      let mem = [];
      try { mem = L((await api('GET', `/api/appengine/${enc(a.id)}/cloud/${ds}/members`)).members); } catch {}
      if (!fresh()) return;
      const lvl = {high: 'bad', medium: 'warn', info: ''};
      const auditOf = k2 => L(o.audit).find(x => x.list === k2) || {};
      const pend = L(o.pending);
      const card = pend.length ? `<div class="ae-loss" role="alertdialog" aria-label="Data loss"><b>Hoola asked for a change that loses data</b>
          <ul>${pend.map(c => `<li><code>${esc(c.op)}</code> ${esc([c.list, c.field].filter(Boolean).join('.'))}${c.to ? ' → ' + esc(c.to) : ''}${c.type ? ' → ' + esc(c.type) : ''}</li>`).join('')}</ul>
          <p class="sm">This deletes or changes saved data in BOTH preview and live. It cannot be undone.</p>
          <label class="ae-row sm"><input type="checkbox" id="aeLossOk"> I accept data loss</label>
          <div class="ae-row"><button class="b sm" type="button" data-ae="loss-yes" style="border-color:var(--bad);color:var(--bad)">Apply</button><button class="b ghost sm" type="button" data-ae="loss-no">Not now</button></div></div>` : '';
      const listHtml = x => { const au = auditOf(x.key), rows = rowsBy[x.key] || [], flds = L(x.fields).filter(f => !f.hidden);
        return `<section class="ae-cl"><div class="ae-row"><h3>${esc(x.label)}</h3><code class="mut sm">${esc(x.key)}</code><span class="sp"></span><span class="mut sm">${rows.length} ${ds} ${rows.length === 1 ? 'entry' : 'entries'}</span></div>
          <p class="sm ae-who">Read: <b>${esc(au.read || '')}</b> · Add: <b>${esc(au.add || '')}</b> · Change: <b>${esc(au.change || '')}</b></p>
          ${L(au.flags).map(f => `<p class="sm ae-flag ${lvl[f.level] || ''}">${esc(f.say)}</p>`).join('')}
          <div class="ae-tbl"><table><thead><tr>${flds.map(f => `<th>${esc(f.label)}${f.required ? ' *' : ''}</th>`).join('')}<th></th></tr></thead>
          <tbody>${rows.slice(0, 50).map(rw => `<tr>${flds.map(f => `<td>${esc(S(rw[f.key]))}</td>`).join('')}<td>${rw.sample ? '<span class="pill">Sample</span>' : ''}</td></tr>`).join('') || `<tr><td colspan="${flds.length + 1}" class="mut">No entries in ${ds} yet.</td></tr>`}</tbody></table></div></section>`; };
      el.innerHTML = `<div class="ae-pad ae-cloud"><div class="ae-row"><h3>Hoola Cloud</h3><span class="pill">schema v${esc((o.schema || {}).version || 0)}</span><span class="sp"></span>
          <div class="seg" role="group" aria-label="Which data"><button type="button" data-ae="ds" data-ae-ds="preview" aria-pressed="${ds === 'preview'}">Preview data</button><button type="button" data-ae="ds" data-ae-ds="live" aria-pressed="${ds === 'live'}">Live data</button></div></div>
        <p class="mut sm">Saved data and sign-in for this app. Every rule is checked on Hoola's server. Preview data (with sample rows) and live data (your visitors) are kept apart: publishing never copies one into the other.</p>
        ${card}
        ${lists.length ? lists.map(listHtml).join('') : '<div class="panel mut">No saved data yet. Ask Hoola, for example: "save the orders and let customers sign in".</div>'}
        <section class="ae-cl"><div class="ae-row"><h3>Members (${ds})</h3><span class="sp"></span>${ds === 'preview' ? '<button class="b ghost sm" type="button" data-ae="samples">Fresh sample rows</button><button class="b ghost sm" type="button" data-ae="clearprev">Clear preview data</button>' : ''}</div>
          ${mem.length ? `<div class="ae-tbl"><table><thead><tr><th>Email</th><th>Name</th><th>Role</th></tr></thead><tbody>${mem.map(m => `<tr><td>${esc(m.email)}</td><td>${esc(m.name)}</td><td><select data-ae-role="${esc(m.id)}" aria-label="Role of ${esc(m.email)}">${['member', 'staff', 'admin'].map(rl => `<option${rl === m.role ? ' selected' : ''}>${rl}</option>`).join('')}</select></td></tr>`).join('')}</tbody></table></div>`
            : `<p class="mut sm">No one has signed up in ${ds} yet.</p>`}
          <p class="mut sm">Roles live in Hoola Cloud, never in the app's data: staff and admin see and change every entry.</p></section>
        <p class="mut sm">Not connected yet: ${esc(L(o.not_built).join(', '))}.</p>
        ${L(o.migrations).length ? `<details><summary class="sm">Changes to the lists (${L(o.migrations).length})</summary><ol class="ae-vers">${L(o.migrations).map(m => `<li><b>v${esc(m.n)}</b><span class="mut sm">${esc(m.by)} · ${esc(L(m.changes).map(c => c.op).join(', '))} · ${esc(k().ago(m.at) || '')}</span></li>`).join('')}</ol></details>` : ''}
      </div>`;
      return;
    }
    if (ST.tab === 'versions') {
      const full = await api('GET', `/api/appengine/${enc(a.id)}`);
      if (!fresh()) return;
      el.innerHTML = `<div class="ae-pad"><h3>Versions</h3><p class="mut sm">Every good build is a version. A failed build never replaces the one on screen.</p>
        ${L(full.versions).length ? `<ol class="ae-vers">${L(full.versions).map(v => `<li><b>Version ${esc(v.version)}</b>${v.live ? ' <span class="pill ok">Live</span>' : ''}
          <span class="mut sm">${esc(k().ago(v.at) || '')}${v.seconds ? ' · ' + esc(v.seconds) + 's' : ''}${v.types_ok === false ? ' · TypeScript problems' : ''}</span>
          <a class="b ghost sm" href="${esc(a.preview)}__v/${esc(v.version)}/" target="_blank" rel="noopener">Open</a></li>`).join('')}</ol>` : '<p class="mut">No version yet.</p>'}</div>`;
      return;
    }
    if (ST.tab === 'publish') {
      el.innerHTML = `<div class="ae-pad"><h3>Publish</h3>
        ${a.live_version ? `<p>Version <b>${esc(a.live_version)}</b> is live at <a href="${esc(a.live_url)}" target="_blank" rel="noopener">${esc(location.origin + a.live_url)}</a>.</p>` : '<p class="mut">This app is not live.</p>'}
        ${a.version ? `<p>The preview shows version <b>${esc(a.version)}</b>. Publishing puts exactly that version live; visitors see it at once.</p>
          <div class="ae-row"><button class="b pri" type="button" data-ae="publish" ${a.version === a.live_version ? 'disabled' : ''}>Publish version ${esc(a.version)}</button>
          ${a.live_version ? '<button class="b ghost" type="button" data-ae="unpublish">Take down</button>' : ''}</div>` : '<p class="mut">Nothing to publish yet.</p>'}
        <div id="aePubMsg" role="status" aria-live="polite">${ST.err ? `<div class="ae-probs">${esc(ST.err)}</div>` : ''}</div>
        <p class="mut sm">Before it goes live Hoola checks the code again: TypeScript, the design rules and the safety rules. A problem stops it and says where.</p>
        <section class="ae-checks"><div class="ae-row"><h3>Checks</h3><span class="sp"></span>
          <button class="b ghost sm" type="button" data-ae="chk" data-ae-chk="tests">Test the rules</button>
          <button class="b ghost sm" type="button" data-ae="chk" data-ae-chk="browser">Browser check</button>
          <button class="b ghost sm" type="button" data-ae="chk" data-ae-chk="quick">Quick scan</button>
          <button class="b ghost sm" type="button" data-ae="chk" data-ae-chk="deep">Deep scan</button></div>
          <div id="aeChecks" class="mut sm">Loading the last results...</div></section>
        <section class="ae-gitsec"><div class="ae-row"><h3>GitHub</h3><span class="sp"></span></div><div id="aeGit" class="mut sm">Loading...</div></section></div>`;
      drawChecks(el); drawGit();
    }
  }


  /* ----- v0.839 L14 GITHUB DO TARAF: one branch, both directions, her tap for every move ----- */
  async function drawGit(cmp) {
    const box = document.getElementById('aeGit'); if (!box) return;
    const {esc} = k();
    let g; try { g = await k().api('GET', `/api/appengine/${enc(ST.id)}/github`); } catch (e) { box.textContent = e.message; return; }
    if (!document.getElementById('aeGit')) return;
    box.className = '';
    if (!g.linked) {
      box.innerHTML = `<p class="mut sm">Link this app to a GitHub repository: your code goes there and changes made on GitHub can come back. It needs your GitHub token (Profile, typed only in the app). A new repository is private.</p>
        <form class="ae-row" data-ae-form="git-link"><input name="repo" maxlength="140" placeholder="repository name, e.g. shop-app" aria-label="Repository" required><button class="b pri" type="submit">Link</button></form>`;
      return;
    }
    const ch = L(g.changes);
    box.innerHTML = `<p><a href="${esc(g.url)}" target="_blank" rel="noopener">${esc(g.repo)}</a> · branch <b>${esc(g.branch)}</b>${g.private ? '' : ' · <span class="pill bad">PUBLIC</span>'}</p>
      <p class="mut sm">${esc(g.say)}${ch.length ? ' ' + ch.slice(0, 6).map(x => esc(x.path)).join(', ') + (ch.length > 6 ? '…' : '') : ''}</p>
      ${cmp ? cmpHtml(cmp) : ''}
      <div class="ae-row"><button class="b" type="button" data-ae="git" data-ae-git="compare">Compare with GitHub</button>
        <button class="b pri" type="button" data-ae="git" data-ae-git="pull">Pull</button>
        <button class="b pri" type="button" data-ae="git" data-ae-git="push">Push</button>
        <span class="sp"></span><button class="b ghost sm" type="button" data-ae="git" data-ae-git="unlink">Unlink</button></div>`;
  }
  function cmpHtml(c) {
    const {esc} = k(), ch = L(c.changed), cf = L(c.conflicts), ka = Object.entries(c.kept_apart || {});
    return `<div class="panel" id="aeGitCmp"><b>${c.remote_moved ? 'GitHub has new commits' : 'GitHub has nothing new'}</b>
      ${ch.length ? `<ul class="dflist">${ch.slice(0, 12).map(x => `<li>${esc(x.say)} <span class="mut sm">${esc(x.what)}</span></li>`).join('')}</ul>` : ''}
      ${cf.length ? `<div class="dfconf"><b>Both changed - you choose:</b>${cf.map(x => `<fieldset class="dfc" data-item="${esc(x.item)}"><legend>${esc(x.say)}</legend>
        <label><input type="radio" name="g-${esc(x.item)}" value="site" checked> Keep the app's</label><label><input type="radio" name="g-${esc(x.item)}" value="github"> Use GitHub's</label></fieldset>`).join('')}</div>` : ''}
      ${ka.length ? `<p class="mut sm">Left alone (locked by Hoola or not text): ${ka.slice(0, 5).map(([p]) => esc(p)).join(', ')}${ka.length > 5 ? '…' : ''}</p>` : ''}</div>`;
  }
  async function gitAct(w) {
    const {api, toast} = k(), base = `/api/appengine/${enc(ST.id)}/github`;
    try {
      if (w === 'compare') { drawGit(await api('GET', base + '/compare')); return; }
      if (w === 'unlink') { if (!confirm('Unlink from GitHub? Nothing on GitHub or in the app changes.')) return; await api('DELETE', base); drawGit(); return; }
      if (w === 'push') {
        if (!confirm('Push this app to GitHub as one commit?')) return;
        const r = await api('POST', base + '/push', {confirm: true}); toast(S(r.say)); drawGit(); return;
      }
      if (w === 'pull') {
        const res = {}; document.querySelectorAll('#aeGitCmp .dfc').forEach(f => { res[f.dataset.item] = f.querySelector('input:checked')?.value || 'site'; });
        if (!confirm('Pull from GitHub into this app? Incoming files must follow the app\'s rules.')) return;
        const r = await api('POST', base + '/pull', {confirm: true, resolutions: res}); toast(S(r.say).slice(0, 200)); drawGit(); return;
      }
    } catch (e) { toast(e.message, true); drawGit(); }
  }
  async function gitLink(f) {
    const {api, toast} = k(); const repo = S(f.repo.value).trim(); if (!repo) return;
    if (!confirm(`Link to GitHub repository "${repo}"? It is created (private) if it does not exist.`)) return;
    try { const r = await api('POST', `/api/appengine/${enc(ST.id)}/github/link`, {repo, confirm: true, private: true}); toast(S(r.say).slice(0, 200)); drawGit(); }
    catch (e) { toast(e.message, true); }
  }
  async function importApp(f) {
    const {api, toast, go} = k(), out = document.getElementById('aeImpOut'), btn = f.querySelector('button[type=submit]');
    btn.disabled = true; if (out) out.innerHTML = '<span class="mut sm">Importing...</span>';
    try {
      let r;
      if (f.dataset.aeForm === 'imp-zip') {
        const file = f.querySelector('input[type=file]').files[0]; if (!file) return;
        r = await api('POST', '/api/appengine-import/zip?name=' + enc(file.name.replace(/\.zip$/i, '')), undefined, {form: file});
      } else {
        if (!confirm('Import this repository as a new app? Nothing is changed on GitHub.')) { btn.disabled = false; if (out) out.innerHTML = ''; return; }
        r = await api('POST', '/api/appengine-import/github', {repo: S(f.repo.value).trim(), confirm: true});
      }
      const {esc} = k();
      if (out) out.innerHTML = `<p>${esc(r.say)}</p>${L(r.refused).length ? `<ul class="dflist">${L(r.refused).slice(0, 10).map(x => `<li><code>${esc(x.file)}</code> ${esc(x.why)}</li>`).join('')}</ul>` : ''}
        <a class="b pri" href="#/app/${enc(S(r.id))}">Open the app</a>`;
    } catch (e) { toast(e.message, true); if (out) out.innerHTML = ''; }
    btn.disabled = false;
  }

  /* ----- v0.832 L11 SABOOT: what Hoola proved before it says done ----- */
  function checksHtml(o) {
    const {esc} = k();
    const row = (name, ok, say, stale) => `<li><b>${esc(name)}</b> <span class="pill ${ok === true ? 'ok' : ''}">${ok === true ? 'Passed' : ok === false ? 'FAILED' : 'Not run'}</span>${stale ? ' <span class="pill">out of date</span>' : ''}
      <span class="mut sm">${esc(say)}</span></li>`;
    const rt = o.rule_tests, br = o.browser, q = o.quick, d = o.deep;
    const items = (x) => L(x && x.items).filter(i => i.level !== 'info').slice(0, 8).map(i => `<li class="sm"><b>${esc(i.level === 'fail' ? 'Stops going live' : 'Warning')}</b> ${esc(i.where)}: ${esc(i.say)}</li>`).join('');
    return `<ul class="ae-vers">
      ${row('Rule tests', rt ? rt.ok : null, rt ? (rt.ok ? `${rt.count} checks over ${rt.lists} list(s) behaved as the rules say.` : `${L(rt.failed).length} of ${rt.count} failed: ${L(rt.failed).slice(0, 2).map(f => `${f.list}: ${f.check}`).join('; ')}`) : 'Run when a rule changes.', rt && rt.stale)}
      ${row('Browser check', br && br.ran ? br.ok : null, br ? (br.ran ? (br.ok ? 'Opened at phone and desktop size; the saved-data walk worked.' : L(br.problems).slice(0, 2).join('; ')) : S(br.why)) : 'Runs after a build of an app that saves data.')}
      ${row('Quick scan', q ? q.ok : null, q ? `${q.fail} stop(s), ${q.warn} warning(s). Runs on every publish.` : 'Runs on every publish.')}
      ${row('Deep scan', d ? d.ok : null, d ? `${d.fail} stop(s), ${d.warn} warning(s). Code checks only; no model reviews the code.` : 'Run it before a big launch.')}</ul>
      ${q || d ? `<ul class="ae-vers">${items(d) || items(q)}</ul>` : ''}`;
  }
  async function drawChecks(el) {
    const {esc, api} = k();
    const box = document.getElementById('aeChecks');
    if (!box) return;
    try {
      const o = await api('GET', `/api/appengine/${enc(ST.id)}/checks`);
      if (document.getElementById('aeChecks') !== box) return;
      box.className = ''; box.innerHTML = checksHtml(o);
    } catch (e) { box.innerHTML = `<span class="mut">${esc(e.message)}</span>`; }
  }

  /* ----- v0.825 L9: the error bar, Select, the free style panel ----- */
  function ebarHtml() {
    const {esc} = k(), a = ST.app;
    const open = L(ST.errs).filter(x => x.state === 'open' && Number(x.version) === Number(a.version));
    if (!open.length) return '';
    const x = open[0];
    return `<div class="ae-ebar" role="alert"><b>This app hit a problem</b><span class="ell">${esc(x.message)}${x.file ? ` <code>${esc(x.file)}:${esc(x.line)}</code>` : ''}${open.length > 1 ? ` (+${open.length - 1} more)` : ''}</span>
      <span class="sp"></span><button class="b sm pri" type="button" data-ae="fixerr" data-ae-fp="${esc(x.fp)}">Try to fix</button><button class="b ghost sm" type="button" data-ae="dismiss" data-ae-fp="${esc(x.fp)}">Dismiss</button></div>`;
  }
  function drawEbar() { const el = document.getElementById('aeEbar'); if (el) el.innerHTML = ebarHtml(); }
  async function readErrs() {
    try { ST.errs = L((await k().api('GET', `/api/appengine/${enc(ST.id)}/errors`)).errors); } catch { return; }
    drawEbar();
  }
  const toFrame = m => { const f = document.getElementById('aeFrame'); if (f && f.contentWindow) f.contentWindow.postMessage(Object.assign({hoola: 'ae-cmd'}, m), '*'); };
  let ERRQ = [], ERRT = null;
  function queueErr(d) {
    ERRQ.push({kind: d.kind, m: d.m, s: d.s, p: d.p, v: ST.shown});
    clearTimeout(ERRT);
    ERRT = setTimeout(async () => {
      const items = ERRQ.splice(0, 20);
      try { await k().api('POST', `/api/appengine/${enc(ST.id)}/preview-errors`, {items, version: ST.shown}); } catch { /* the bar just stays */ }
      readErrs();
    }, 400);
  }
  async function onPick(d) {
    const {api, toast} = k();
    ST.pick = {hs: S(d.hs), tag: S(d.tag), hc: S(d.hc), text: S(d.text), info: null};
    ST.pend = {}; ST.ptext = null;
    drawPick();
    try { ST.pick.info = await api('GET', `/api/appengine/${enc(ST.id)}/pick?hs=${enc(ST.pick.hs)}`); }
    catch (e) { ST.pick.info = {editable_style: false, why: e.message, text: null}; toast(e.message, true); }
    drawPick();
  }
  function drawPick() {
    const {esc, ico} = k(), el = document.getElementById('aeSel'); if (!el) return;
    const p = ST.pick;
    if (!p) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    const [file, line] = p.hs.split(':');
    const info = p.info, cols = ((ST.app.theme || {}).colors) || {};
    const chip = (f, v, label) => { const on = (f in ST.pend ? ST.pend[f] : (info.values || {})[f]) === v;
      const sw = f === 'color' || f === 'bg' ? `<i style="background:${esc(cols[v] || 'transparent')}"></i>` : '';
      return `<button type="button" class="ae-chip${on ? ' on' : ''}" aria-pressed="${on}" data-ae="pk-chip" data-ae-f="${f}" data-ae-v="${esc(v)}" title="${esc(label || v)}">${sw}${esc(label || v)}</button>`; };
    const VALS = {color: ['ink', 'muted', 'primary', 'accent', 'ok', 'warn', 'bad', 'primary-ink'], bg: ['bg', 'surface', 'primary', 'accent', 'line'],
      size: ['xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl'], weight: ['normal', 'medium', 'semibold', 'bold'], pad: ['0', '2', '4', '6', '8'],
      radius: ['none', 'control', 'card', 'full'], align: ['left', 'center', 'right']};
    const body = !info ? '<p class="mut sm">Reading that line…</p>' : `
      ${info.editable_style ? FAM.map(([f, label]) => `<div class="ae-fam"><span class="ae-l">${label}</span><div class="ae-chips">${VALS[f].map(v => chip(f, v)).join('')}${chip(f, '', 'Default')}</div></div>`).join('')
        : `<p class="mut sm">${esc(info.why || 'This part cannot be styled here.')}</p>`}
      ${info.text !== null && info.text !== undefined ? `<label class="ae-l" for="aePkText">Words</label><input id="aePkText" class="ae-in" value="${esc(ST.ptext !== null ? ST.ptext : info.text)}" maxlength="400">` : ''}
      <div class="ae-row"><button class="b pri sm" type="button" data-ae="pk-apply" ${Object.keys(ST.pend).length || ST.ptext !== null ? '' : 'disabled'}>Apply · free</button>
        <button class="b ghost sm" type="button" data-ae="pk-cancel">Cancel</button><span class="sp"></span>
        ${ST.undo ? `<button class="b ghost sm" type="button" data-ae="undo">Undo last change</button>` : ''}</div>`;
    el.innerHTML = `<div class="ae-selh"><b>&lt;${esc(p.tag)}&gt;</b><span class="mut sm ell">${esc(p.hc ? p.hc + ' · ' : '')}${esc(file)}:${esc(line)}</span><span class="sp"></span>
        <button class="b ghost sm ae-x" type="button" data-ae="pk-close" aria-label="Close">×</button></div>
      <div class="ae-row"><button class="b sm" type="button" data-ae="pk-code">Open in code</button><button class="b sm" type="button" data-ae="pk-ask">Ask Hoola about this</button></div>
      ${body}<p class="mut sm">Style and words here change the code at that line without AI (Rs 0). Anything bigger: ask Hoola.</p>`;
  }
  function livePreview() {
    if (!ST.pick) return;
    const css = {};
    for (const [f, v] of Object.entries(ST.pend)) Object.assign(css, v === '' ? Object.fromEntries(Object.keys(CSSOF[f]('x')).map(kk => [kk, ''])) : CSSOF[f](v));
    toFrame({t: 'style', hs: ST.pick.hs, css, ...(ST.ptext !== null ? {text: ST.ptext} : {})});
  }
  function drawPills() {
    const {esc} = k(), el = document.getElementById('aePills'); if (!el) return;
    el.innerHTML = L(ST.sel).map((x, i) => `<span class="ae-pill">&lt;${esc(x.tag)}&gt; ${esc(S(x.hs).split(':').slice(0, 2).join(':'))}<button type="button" data-ae="unpill" data-ae-i="${i}" aria-label="Remove">×</button></span>`).join('');
    el.hidden = !L(ST.sel).length;
  }
  addEventListener('message', e => {
    const f = document.getElementById('aeFrame');
    if (!f || e.source !== f.contentWindow) return;
    const d = e.data || {};
    if (d.hoola !== 'ae') return;
    if (d.t === 'ready') {
      if (ST.select) toFrame({t: 'mode', mode: 'select'});
      k().api('POST', `/api/appengine/${enc(ST.id)}/preview-errors`, {items: [], loaded: ST.shown}).then(readErrs).catch(() => {});
    }
    if (d.t === 'err') queueErr(d);
    if (d.t === 'pick') onPick(d);
    if (d.t === 'mode') { ST.select = d.mode === 'select'; const b = document.querySelector('[data-ae="select"]'); if (b) { b.setAttribute('aria-pressed', String(ST.select)); b.classList.toggle('on', ST.select); } }
  });
  document.addEventListener('change', async e => {               // v0.827 her tap on a member's role
    const sel = e.target && e.target.closest && e.target.closest('[data-ae-role]');
    if (!sel) return;
    const ds = ST.ds === 'live' ? 'live' : 'preview';
    try { await k().api('POST', `/api/appengine/${enc(ST.id)}/cloud/${ds}/members/${enc(sel.dataset.aeRole)}/role`, {role: sel.value}); k().toast('Role changed; they sign in again.'); }
    catch (er) { k().toast(er.message, true); }
  });
  document.addEventListener('input', e => {
    if (e.target && e.target.id === 'aePkText') { ST.ptext = S(e.target.value); livePreview(); const b = document.querySelector('[data-ae="pk-apply"]'); if (b) b.disabled = false; }
  });

  /* ----- the chat ----- */
  async function readChat() {
    const {api} = k();
    if (!ST.conv) return;
    try {
      const r = await api('GET', `/api/conversations/${enc(ST.conv)}/messages?limit=60`);
      ST.rows = L(r.messages).filter(m => (m.role === 'user' || m.role === 'assistant') && S(m.text).trim());
    } catch { return; }
    const talk = ST.rows; let lu = -1; talk.forEach((m, i) => { if (m.role === 'user') lu = i; });
    ST.waiting = lu >= 0 && !talk.slice(lu + 1).some(m => m.role === 'assistant');
    drawChat();
  }

  function drawChat() {
    const {esc, md, clean} = k(), el = document.getElementById('aeMsgs'); if (!el) return;
    const sig = ST.rows.map(m => m.id).join(',') + ST.waiting;
    if (sig === ST.sig && !ST.waiting) return;
    ST.sig = sig;
    const body = ST.rows.map(m => m.role === 'user'
      ? `<div class="ae-me">${esc(clean(S(m.text)))}</div>`
      : `<div class="ae-hoola"><b class="sm">Hoola</b><div class="mdb">${md ? md.render(S(m.text)) : esc(S(m.text))}</div></div>`).join('');
    const last = ST.rows.filter(m => m.role === 'user').pop();
    const since = last ? Math.max(0, Date.now() / 1000 - (Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(S(last.at)) ? S(last.at) : S(last.at) + 'Z') / 1000)) : 0;
    el.innerHTML = (body || '<p class="mut ae-hint">Tell Hoola what this app should do, or what to change. Hoola edits the code, builds it, and shows you the new version on the right.</p>')
      + (ST.waiting ? `<div class="ae-work" role="status"><span class="dot v"></span>Hoola is working on the app… ${secs(since)}</div>` : '');
    el.scrollTop = el.scrollHeight;
  }

  async function say(form) {
    const {toast} = k(), ta = form.querySelector('textarea'), text = S(ta.value).trim();
    if (!text) return;
    ta.value = '';
    ST.rows.push({id: 'local-' + Date.now(), role: 'user', text}); ST.waiting = true; ST.sig = ''; drawChat();
    try { await send(ST.app, ST.conv, text); drawPills(); } catch (e) { ta.value = text; ST.waiting = false; toast(e.message, true); }
  }

  /* ----- the loop: the app row (status / version) + the chat ----- */
  async function tick() {
    stop();
    const {api} = k();
    if (!document.querySelector('[data-ae-root]')) return;
    try {
      const a = await api('GET', `/api/appengine/${enc(ST.id)}?full=0`);
      const moved = a.version !== ST.app.version || a.status !== ST.app.status || a.dirty !== ST.app.dirty || a.live_version !== ST.app.live_version
        || JSON.stringify(a.last_build) !== JSON.stringify(ST.app.last_build);
      ST.app = {...ST.app, ...a};
      if (moved) { drawTop(); if (ST.tab === 'preview' || ST.tab === 'publish') await drawView(); if (a.version !== ST.errsV) { ST.errsV = a.version; readErrs(); } }
    } catch { /* keep polling */ }
    await readChat();
    ST.poll = setTimeout(tick, ST.waiting || ST.app.dirty || S(ST.app.status) === 'building' ? 2000 : 6000);
  }

  async function act(b) {
    const {api, toast} = k(), what = b.dataset.ae;
    if (what === 'tab') { ST.tab = b.dataset.aeTab; history.replaceState(null, '', `#/app/${enc(ST.id)}/${ST.tab}`); drawTabs(); await drawView(); return; }
    if (what === 'dev') { ST.device = b.dataset.aeDev; await drawView(); return; }
    if (what === 'file') { ST.file = b.dataset.aeFile; ST.line = 0; await drawView(); return; }
    if (what === 'select') { ST.select = !ST.select; toFrame({t: 'mode', mode: ST.select ? 'select' : 'off'}); b.setAttribute('aria-pressed', String(ST.select)); b.classList.toggle('on', ST.select); return; }
    if (what === 'pk-chip') { const f = b.dataset.aeF, v = S(b.dataset.aeV); ST.pend[f] = v; livePreview(); drawPick(); return; }
    if (what === 'pk-close' || what === 'pk-cancel') { toFrame({t: 'clear'}); ST.pick = null; ST.pend = {}; ST.ptext = null; drawPick(); return; }
    if (what === 'pk-code') { const [f, ln] = ST.pick.hs.split(':'); ST.file = f; ST.line = Number(ln) || 0; ST.tab = 'code'; history.replaceState(null, '', `#/app/${enc(ST.id)}/code`); drawTabs(); await drawView(); return; }
    if (what === 'pk-ask') { if (!L(ST.sel).some(x => x.hs === ST.pick.hs)) ST.sel.push({...ST.pick}); drawPills(); document.getElementById('aeSay')?.focus(); return; }
    if (what === 'unpill') { ST.sel.splice(Number(b.dataset.aeI), 1); drawPills(); return; }
    if (what === 'pk-apply') {
      const body = {hs: ST.pick.hs, ...(Object.keys(ST.pend).length ? {style: ST.pend} : {}), ...(ST.ptext !== null ? {text: ST.ptext} : {})};
      b.disabled = true;
      try { const r = await api('POST', `/api/appengine/${enc(ST.id)}/edit`, body); toast(S(r.say)); ST.undo = true; ST.pend = {}; ST.ptext = null; ST.pick.info = null; drawPick();
        ST.pick.info = await api('GET', `/api/appengine/${enc(ST.id)}/pick?hs=${enc(ST.pick.hs)}`); }
      catch (e) { toast(e.message, true); }
      drawPick(); return;
    }
    if (what === 'undo') {
      try { const r = await api('POST', `/api/appengine/${enc(ST.id)}/undo`); toast(S(r.say)); ST.undo = Number(r.left) > 0; if (ST.pick) ST.pick.info = await api('GET', `/api/appengine/${enc(ST.id)}/pick?hs=${enc(ST.pick.hs)}`); }
      catch (e) { toast(e.message, true); }
      drawPick(); return;
    }
    if (what === 'ds') { ST.ds = b.dataset.aeDs; await drawView(); return; }
    if (what === 'samples' || what === 'clearprev') {
      if (what === 'clearprev' && !(await confirmBox('Clear all PREVIEW data and preview members of this app? Live data is not touched.', 'Clear preview data'))) return;
      try { const r = await api('POST', `/api/appengine/${enc(ST.id)}/cloud/preview/${what === 'samples' ? 'samples' : 'clear'}`); toast(what === 'samples' ? `${r.made} sample rows added.` : `${r.removed} preview rows removed.`); }
      catch (e) { toast(e.message, true); }
      await drawView(); return;
    }
    if (what === 'loss-no') { try { await api('POST', `/api/appengine/${enc(ST.id)}/cloud/pending/clear`); } catch (e) { toast(e.message, true); } await drawView(); return; }
    if (what === 'loss-yes') {
      if (!document.getElementById('aeLossOk')?.checked) { toast('Tick "I accept data loss" first.', true); return; }
      try { const r = await api('POST', `/api/appengine/${enc(ST.id)}/cloud/changes`, {accept_data_loss: true, confirm: true}); toast(S(r.say)); }
      catch (e) { toast(e.message, true); }
      await drawView(); return;
    }
    if (what === 'git') { gitAct(b.dataset.aeGit); return; }
    if (what === 'chk') {
      const box = document.getElementById('aeChecks'); const w = b.dataset.aeChk;
      if (box) box.innerHTML = '<span class="mut">Checking... a browser check can take up to a minute.</span>';
      b.disabled = true;
      try { await k().api('POST', `/api/appengine/${enc(ST.id)}/checks/${enc(w)}`); } catch (e) { toast(e.message, true); }
      b.disabled = false; drawChecks(); return;
    }
    if (what === 'dismiss') { try { await api('POST', `/api/appengine/${enc(ST.id)}/errors/${enc(b.dataset.aeFp)}/dismissed`); } catch (e) { toast(e.message, true); } readErrs(); return; }
    if (what === 'fixerr') {
      const x = L(ST.errs).find(y => y.fp === b.dataset.aeFp); if (!x) return;
      const text = `Fix this error the preview reported: "${S(x.message).slice(0, 300)}"${x.file ? ` (at ${x.file} line ${x.line})` : ''}.`;
      ST.rows.push({id: 'local-' + Date.now(), role: 'user', text}); ST.waiting = true; ST.sig = ''; drawChat();
      try { await send(ST.app, ST.conv, text); toast('Sent to Hoola.'); } catch (e) { ST.waiting = false; toast(e.message, true); }
      return;
    }
    if (what === 'build') {
      b.disabled = true; ST.app.status = 'building'; drawTop();
      try { const r = await api('POST', `/api/appengine/${enc(ST.id)}/build`); toast(S(r.say), !r.built); ST.app = {...ST.app, ...r}; }
      catch (e) { toast(e.message, true); }
      drawTop(); await drawView(); return;
    }
    if (what === 'pal') {
      try { const r = await api('POST', `/api/appengine/${enc(ST.id)}/tokens`, {palette: b.dataset.aePal}); toast(S(r.say)); } catch (e) { toast(e.message, true); }
      await drawView(); return;
    }
    if (what === 'publish' || what === 'unpublish') {
      const v = ST.app.version;
      const q = what === 'publish' ? `Put version ${v} of "${S(ST.app.name)}" live? Visitors see it at once.` : `Take "${S(ST.app.name)}" down? Visitors will not see it any more.`;
      if (!(await confirmBox(q, what === 'publish' ? `Publish version ${v}` : 'Take down'))) return;
      ST.err = '';
      try {
        const r = await api('POST', `/api/appengine/${enc(ST.id)}/${what}`, what === 'publish' ? {version: v, confirm: true} : {confirm: true});
        ST.app = {...ST.app, ...r}; toast(S(r.say));
      } catch (e) { ST.err = e.message; }
      drawTop(); await drawView();
    }
  }

  function confirmBox(q, yes) {
    const {esc} = k();
    return new Promise(res => {
      const d = document.createElement('div');
      d.className = 'ae-modal'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true'); d.setAttribute('aria-label', 'Confirm');
      d.innerHTML = `<div class="ae-box"><p>${esc(q)}</p><div class="ae-row"><span class="sp"></span><button class="b ghost" type="button" data-x="no">Cancel</button><button class="b pri" type="button" data-x="yes">${esc(yes)}</button></div></div>`;
      const done = v => { d.remove(); res(v); };
      d.addEventListener('click', e => { const x = e.target.closest('[data-x]'); if (x) done(x.dataset.x === 'yes'); else if (e.target === d) done(false); });
      d.addEventListener('keydown', e => { if (e.key === 'Escape') done(false); });
      document.body.appendChild(d); d.querySelector('[data-x="yes"]').focus();
    });
  }

  document.addEventListener('click', e => {
    const b = e.target.closest && e.target.closest('[data-ae]');
    if (!b || !document.getElementById('ws')?.contains(b)) return;
    e.preventDefault(); e.stopPropagation();
    act(b);
  }, true);
  document.addEventListener('submit', e => {
    const f = e.target.closest && e.target.closest('[data-ae-form]');
    if (!f) return;
    e.preventDefault(); e.stopPropagation();
    if (f.dataset.aeForm === 'new') createApp(f); else if (f.dataset.aeForm === 'say') say(f); else if (f.dataset.aeForm === 'git-link') gitLink(f); else if (f.dataset.aeForm === 'imp-zip' || f.dataset.aeForm === 'imp-gh') importApp(f);
  }, true);
  document.addEventListener('keydown', e => {
    if ((e.key === 's' || e.key === 'S') && !e.metaKey && !e.ctrlKey && !e.altKey && ST.tab === 'preview' && document.querySelector('[data-ae-root]')
        && !/^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || '') && !(e.target && e.target.isContentEditable)) {
      const b = document.querySelector('[data-ae="select"]'); if (b) { e.preventDefault(); act(b); } return;
    }
    if (e.key === 'Enter' && !e.shiftKey && e.target && e.target.id === 'aeSay') { e.preventDefault(); e.target.form.requestSubmit(); }
  });

  window.HoolaAppEngine = {
    async open(p) {
      stop();
      if (p[0] === 'app' && p[1]) return workspace(decodeURIComponent(p[1]), p[2] || 'preview');
      return listPage();
    },
  };
})();
