/* HOOLA DESIGN - D8b: plugins by Hoola, the starter plugins, and the template gallery (docs/HOOLA_DESIGN_PLAN.md
   section 8, D8b). Styles: design-plugins-ai.css. Server: design/plugin_ai.py, plugin_starters.py, gallery.py.
   Loaded after hd-plugins.js (D8a: HD.plugins.install opens ITS review dialog - the code and every permission in plain
   words - and only her Install there installs) and before hd-app.js.

   ASK HOOLA TO MAKE A PLUGIN  (main menu, the command palette, and a card in the Plugins dialog)
     one sentence -> POST /api/design/plugins/draft -> the draft (manifest + code, checked on the server: the static scan,
     the smallest permissions) -> HD.plugins.install(manifest, code) = D8a's review. Nothing is installed by this file.
     Without D8a's runtime on the page the draft is shown READ ONLY (code + permissions + Copy).
   STARTER PLUGINS  GET /api/design/plugins/starters -> a "Starter plugins by Hoola" list inside D8a's Plugins dialog
     (put there by watching for that dialog: hd-plugins.js has no hook for it), each with Add = the same review dialog.
   TEMPLATES  a "Templates" tab in the file browser (put there by watching for the browser's tab row): categories,
     search, pictures (GET /templates/<id>/thumb), Use = POST /templates/<id>/use -> a NEW file in her files, opened.
     "My templates" = her own files she kept as templates (only she sees them): "Save as a template…" in the editor's
     main menu -> POST /files/<id>/publish-template.
   Every text from the server or a plugin is set with textContent. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const ui = HD.ui;
  if (!ui || !ui.h) return;
  const h = ui.h, icon = ui.icon, clear = ui.clear, enc = encodeURIComponent;
  const IDEAS = ['Number the selected layers as Step 1, Step 2, Step 3', 'Make every text in the selection one size bigger',
    'Turn the selected texts into Title Case', 'Spread the selected layers evenly from left to right'];
  const signedIn = () => !!ui.token && !(HD.net && HD.net.share) && !(HD.app && HD.app.file && HD.app.file.share);
  const st = {starters: null, draft: null, prompt: '', busy: false};

  /* ================================================================ ask Hoola to make a plugin */
  function sheet(title, body, foot) {
    return ui.modal('hdpa-dialog', title, [h('div', {class: 'hd-sheethead'}, h('h2', {text: title}),
      h('button', {type: 'button', class: 'hd-ib', title: 'Close', 'aria-label': 'Close', on: {click: () => ui.closeModal()}}, icon('close'))), body, foot || null]);
  }
  function ask(prefill) {
    if (!signedIn()) { ui.toast('Sign in to make plugins.'); return; }
    if (typeof prefill === 'string') st.prompt = prefill;
    const ta = h('textarea', {class: 'hd-in hdpa-ta', rows: '3', maxlength: '1200', 'aria-label': 'What should the plugin do?',
      placeholder: 'What should the plugin do? For example: number the selected layers as Step 1, Step 2, Step 3'});
    ta.value = st.prompt;
    const status = h('p', {class: 'hdpa-status', role: 'status', 'aria-live': 'polite'});
    const go = h('button', {type: 'button', class: 'hd-btn pri', text: 'Write the plugin'});
    const ideas = h('div', {class: 'hdpa-ideas'}, IDEAS.map(t => h('button', {type: 'button', class: 'hdpa-idea', text: t, on: {click: () => { ta.value = t; st.prompt = t; ta.focus(); }}})));
    const body = h('div', {class: 'hdpa-body'},
      h('p', {class: 'hdpa-lead', text: 'Say in a sentence what it should do. Hoola writes the plugin with the fewest permissions it needs, and you see its code and every permission before anything is installed.'}),
      ta, ideas, status);
    if (st.draft) body.appendChild(draftCard(st.draft, true));
    sheet('Ask Hoola to make a plugin', body, h('div', {class: 'hdpa-foot'}, h('span', {class: 'hdpa-hint', text: 'Plugins run in a sealed box and only do what you allow.'}), go));
    ta.addEventListener('input', () => { st.prompt = ta.value; });
    ta.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) { ev.preventDefault(); go.click(); } });
    go.addEventListener('click', async () => {
      const prompt = ta.value.trim();
      if (!prompt) { status.className = 'hdpa-status bad'; status.textContent = 'Say in a sentence what the plugin should do.'; ta.focus(); return; }
      if (st.busy) return;
      st.busy = true; go.disabled = true; ta.disabled = true; status.className = 'hdpa-status busy'; status.textContent = 'Hoola is writing the plugin and checking its code…';
      let d;
      try { d = await ui.api('POST', '/plugins/draft', {prompt: prompt}); }
      catch (e) { st.busy = false; go.disabled = false; ta.disabled = false; status.className = 'hdpa-status bad'; status.textContent = (e && e.message) || 'Hoola could not write that plugin.'; return; }
      st.busy = false; st.draft = d;
      review(d);
    });
    setTimeout(() => ta.focus({preventScroll: true}), 0);
  }
  /* D8a's review dialog is the approval; when she closes it without installing, her draft is still here */
  async function review(d) {
    if (!HD.plugins || typeof HD.plugins.install !== 'function') { readOnly(d); return; }
    let out = null;
    try { out = await HD.plugins.install(d.manifest, d.code); } catch (e) { ui.toast((e && e.message) || 'The plugin could not be shown.', true); }
    if (out && out.installed) { st.draft = null; st.prompt = ''; return; }
    if (!document.querySelector('.hd-modal')) ask();               /* back to the idea and the draft, nothing installed */
  }
  function draftCard(d, again) {
    const m = d.manifest || {};
    return h('section', {class: 'hdpa-draft', 'aria-label': 'The last draft'},
      h('div', {class: 'hdpa-drow'}, h('div', {class: 'hdpa-dwho'}, h('strong', {text: String(m.name || 'Plugin')}), h('span', {text: String(m.description || '')})),
        again ? h('button', {type: 'button', class: 'hd-btn', text: 'Review and install', on: {click: () => review(d)}}) : null),
      chips(m.permissions || []),
      (d.notes || []).length ? h('ul', {class: 'hdpa-notes'}, d.notes.map(n => h('li', {text: String(n)}))) : null);
  }
  function chips(perms) {
    return h('div', {class: 'hdpa-chips'}, perms.length ? perms.map(p => h('span', {class: 'hdpa-chip' + (/^net:|^edit$/.test(p) ? ' strong' : ''), text: words(p)}))
      : h('span', {class: 'hdpa-chip', text: 'Asks for nothing'}));
  }
  function words(p) { return HD.plugins && HD.plugins.words ? HD.plugins.words(p) : p; }
  function readOnly(d) {
    const m = d.manifest || {};
    const copy = h('button', {type: 'button', class: 'hd-btn', text: 'Copy the code'});
    copy.addEventListener('click', async () => { try { await navigator.clipboard.writeText(d.code); copy.textContent = 'Copied'; } catch (e) { ui.toast('Select the code and copy it by hand.'); } });
    sheet('A plugin draft', h('div', {class: 'hdpa-body'},
      h('p', {class: 'hdpa-warn', text: 'Plugins can not be installed in this editor yet, so here is the draft to read. Nothing was installed.'}),
      draftCard(d, false), h('pre', {class: 'hdpa-code', tabIndex: 0, 'aria-label': 'The plugin code', text: String(d.code || '')}),
      h('details', {class: 'hdpa-man'}, h('summary', {text: 'Manifest'}), h('pre', {class: 'hdpa-code', text: JSON.stringify(m, null, 2)}))),
      h('div', {class: 'hdpa-foot'}, h('span', {class: 'hdpa-hint', text: String(m.id || '')}), copy));
  }

  /* ================================================================ the starters, inside D8a's Plugins dialog */
  async function starters() {
    if (!st.starters) st.starters = ui.api('GET', '/plugins/starters').then(r => (r && r.starters) || []).catch(e => { st.starters = null; throw e; });
    return st.starters;
  }
  async function addStarter(s, btn) {
    if (!HD.plugins || !HD.plugins.install) { readOnly({manifest: s.manifest, code: s.code, notes: []}); return; }
    btn.disabled = true;
    try { const out = await HD.plugins.install(s.manifest, s.code); if (out && out.installed && HD.plugins.open) HD.plugins.open(); }
    catch (e) { ui.toast((e && e.message) || 'That did not work.', true); }
    finally { btn.disabled = false; }
  }
  async function fillManager(list) {
    if (list.querySelector('.hdpa-from')) return;
    const box = h('section', {class: 'hdpa-from', 'aria-label': 'From Hoola'});
    list.appendChild(box);
    const askCard = h('button', {type: 'button', class: 'hdpa-askcard', on: {click: () => ask()}},
      h('span', {class: 'hdpa-mark', 'aria-hidden': 'true'}, icon('spark', 18)),
      h('span', {class: 'hdpa-asktext'}, h('strong', {text: 'Ask Hoola to make a plugin'}), h('span', {text: 'Say what you need in a sentence. You see the code before it is installed.'})),
      icon('right'));
    box.appendChild(askCard);
    box.appendChild(h('h3', {class: 'hdpa-h3', text: 'Starter plugins by Hoola'}));
    const rows = h('div', {class: 'hdpa-starters'}, h('p', {class: 'hdpa-hint', text: 'Loading…'}));
    box.appendChild(rows);
    let all, mine = [];
    try { all = await starters(); } catch (e) { clear(rows).appendChild(h('p', {class: 'hdpa-hint', text: (e && e.message) || 'The starter plugins could not be loaded.'})); return; }
    try { mine = HD.plugins && HD.plugins.list ? await HD.plugins.list() : []; } catch (e) { mine = []; }
    clear(rows);
    for (const s of all) {
      const m = s.manifest, have = mine.some(p => p.id === m.id);
      const btn = h('button', {type: 'button', class: 'hd-btn' + (have ? '' : ' pri'), text: have ? 'Added' : 'Add', disabled: have, 'aria-label': (have ? 'Added: ' : 'Add ') + m.name});
      btn.addEventListener('click', () => addStarter(s, btn));
      rows.appendChild(h('article', {class: 'hdpa-starter', 'data-starter': m.id},
        h('span', {class: 'hdpa-sicon', 'aria-hidden': 'true'}, icon(s.icon || 'spark')),
        h('div', {class: 'hdpa-swho'}, h('strong', {text: m.name}), h('span', {text: m.description}), chips(m.permissions || [])), btn));
    }
  }
  function watchManager() {
    const list = document.querySelector('.hdp-manager .hdp-list');
    if (list && !list.querySelector('.hdpa-from') && !list.querySelector('.hdp-note')) fillManager(list);
  }

  /* ================================================================ templates: a tab in the file browser */
  const gal = {on: false, q: '', cat: '', data: null, box: null, urls: new Map(), seq: 0};
  function grid() { const main = document.querySelector('.hd-home .hd-hmain'); return main ? main.children[1] || null : null; }
  function addTab() {
    const seg = document.querySelector('.hd-home .hd-hbar .hd-seg');
    if (!seg || seg.querySelector('[data-v="templates"]')) return;
    const b = h('button', {class: 'hd-segb', type: 'button', role: 'tab', 'data-v': 'templates', text: 'Templates', 'aria-selected': 'false'});
    b.addEventListener('click', openGallery);
    seg.appendChild(b);
    seg.addEventListener('click', ev => { const t = ev.target.closest && ev.target.closest('.hd-segb'); if (t && t.dataset.v !== 'templates') closeGallery(); }, true);
    if (gal.on || /^#\/templates/.test(location.hash || '')) openGallery();
  }
  function setTabs() {
    const seg = document.querySelector('.hd-home .hd-hbar .hd-seg'); if (!seg) return;
    for (const b of seg.children) { const on = gal.on ? b.dataset.v === 'templates' : b.classList.contains('on') && b.dataset.v !== 'templates'; b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); }
  }
  function closeGallery() {
    if (!gal.on) return; gal.on = false;
    if (gal.box && gal.box.parentNode) gal.box.parentNode.removeChild(gal.box);
    gal.box = null; const g = grid(); if (g) g.style.display = '';
    const t = document.querySelector('[data-v="templates"]'); if (t) { t.classList.remove('on'); t.setAttribute('aria-selected', 'false'); }
  }
  async function openGallery() {
    const main = document.querySelector('.hd-home .hd-hmain'); if (!main) return;
    gal.on = true; setTabs();
    const title = main.querySelector('.hd-hbar h1'); if (title) title.textContent = 'Templates';
    const g = grid(); if (g && !g.classList.contains('hdg-gallery')) g.style.display = 'none';
    const search = document.querySelector('.hd-hsearch input'); if (search) { gal.q = search.value.trim(); search.placeholder = 'Search templates'; }
    if (!gal.box || !document.contains(gal.box)) { gal.box = h('div', {class: 'hdg-gallery', 'aria-live': 'polite'}); main.appendChild(gal.box); }
    await load();
  }
  async function load() {
    const my = ++gal.seq, box = gal.box; if (!box) return;
    if (!gal.data) { clear(box).appendChild(h('div', {class: 'hdg-grid'}, Array.from({length: 8}, () => h('div', {class: 'hd-skel', 'aria-hidden': 'true'})))); }
    try { gal.data = await ui.api('GET', '/templates?q=' + enc(gal.q) + '&category=' + enc(gal.cat)); }
    catch (e) { if (my !== gal.seq) return; clear(box).appendChild(h('div', {class: 'hd-herr', role: 'alert'}, h('p', {text: (e && e.message) || 'The templates could not be loaded.'}), h('button', {class: 'hd-btn', type: 'button', text: 'Try again', on: {click: load}}))); return; }
    if (my === gal.seq && gal.on) paint();
  }
  function paint() {
    const box = gal.box, d = gal.data || {templates: [], mine: [], categories: []}; clear(box);
    const cats = h('div', {class: 'hdg-cats', role: 'tablist', 'aria-label': 'Categories'});
    for (const c of [''].concat(d.categories || [])) {
      const on = gal.cat === c;
      cats.appendChild(h('button', {type: 'button', class: 'hdg-cat' + (on ? ' on' : ''), role: 'tab', 'aria-selected': String(on), text: c || 'All', on: {click: () => { gal.cat = c; load(); }}}));
    }
    box.appendChild(cats);
    if ((d.mine || []).length) {
      box.appendChild(h('h2', {class: 'hdg-h2', text: 'My templates'}));
      box.appendChild(h('p', {class: 'hdg-sub', text: 'Your own files kept as templates. Only you can see them.'}));
      box.appendChild(h('div', {class: 'hdg-grid'}, d.mine.map(t => card(t))));
    }
    if ((d.mine || []).length) box.appendChild(h('h2', {class: 'hdg-h2', text: 'Made by Hoola'}));
    if (!(d.templates || []).length) {
      box.appendChild(h('div', {class: 'hd-empty'}, h('h2', {text: gal.q ? 'No template called “' + gal.q + '”' : 'No templates here'}), h('p', {text: 'Try another word or another category.'})));
      return;
    }
    box.appendChild(h('div', {class: 'hdg-grid'}, d.templates.map(t => card(t))));
  }
  function card(t) {
    const pic = h('div', {class: 'hdg-thumb'}, icon('frame', 30));
    const use = h('button', {type: 'button', class: 'hd-btn pri hdg-use', text: 'Use template', 'aria-label': 'Use the template ' + t.name});
    const el = h('article', {class: 'hdg-card', 'data-template': t.id},
      h('button', {type: 'button', class: 'hdg-open', 'aria-label': 'Use the template ' + t.name}, pic,
        h('div', {class: 'hdg-meta'}, h('span', {class: 'hdg-name', text: t.name}),
          h('span', {class: 'hdg-info', text: t.category + (t.w && t.h ? ' · ' + Math.round(t.w) + ' × ' + Math.round(t.h) : '')}))),
      h('div', {class: 'hdg-acts'}, use, t.mine ? h('button', {type: 'button', class: 'hd-ib', title: 'Delete this template', 'aria-label': 'Delete the template ' + t.name,
        on: {click: () => drop(t)}}, icon('trash')) : null));
    const go = () => useTemplate(t, use);
    el.querySelector('.hdg-open').addEventListener('click', go); use.addEventListener('click', go);
    thumb(t, pic);
    return el;
  }
  function thumb(t, box) {
    const key = t.id + '|' + (t.created_at || '');
    const put = url => { if (!document.contains(box)) return; clear(box).appendChild(h('img', {src: url, alt: '', loading: 'lazy', draggable: 'false'})); };
    if (gal.urls.has(key)) { put(gal.urls.get(key)); return; }
    ui.api('GET', '/templates/' + enc(t.id) + '/thumb').then(blob => { if (!blob || !blob.size) return; const url = URL.createObjectURL(blob); gal.urls.set(key, url); put(url); }).catch(() => {});
  }
  async function useTemplate(t, btn) {
    if (btn.disabled) return; btn.disabled = true; btn.textContent = 'Making your copy…';
    try { const f = await ui.api('POST', '/templates/' + enc(t.id) + '/use', {}); closeGallery(); location.hash = '#/f/' + enc(f.id); }
    catch (e) { ui.toast((e && e.message) || 'The template could not be used.', true); btn.disabled = false; btn.textContent = 'Use template'; }
  }
  async function drop(t) {
    if (!window.confirm('Delete your template “' + t.name + '”? Files you made from it stay.')) return;
    try { await ui.api('DELETE', '/templates/' + enc(t.id)); ui.toast('Template deleted.'); load(); } catch (e) { ui.toast(e.message || 'That did not work.', true); }
  }
  /* the browser's search box searches templates while the Templates tab is open (and only then) */
  document.addEventListener('input', ev => {
    if (!gal.on || !ev.target || !ev.target.closest || !ev.target.closest('.hd-hsearch')) return;
    ev.stopPropagation(); gal.q = ev.target.value.trim(); clearTimeout(gal.t); gal.t = setTimeout(load, 220);
  }, true);

  /* ================================================================ her file as one of her templates */
  function saveAsTemplate() {
    const f = HD.app && HD.app.file;
    if (!f || f.share || f.role === 'view' || !signedIn()) { ui.toast('Open one of your own files to keep it as a template.'); return; }
    const name = h('input', {class: 'hd-in', type: 'text', maxlength: '80', value: f.name || 'My template', 'aria-label': 'Template name'});
    const cat = h('select', {class: 'hd-in', 'aria-label': 'Category'}, ['My designs', 'Posters', 'Festivals', 'Social media', 'Business', 'Invitations', 'Food', 'App screens', 'Presentations', 'YouTube', 'Certificates', 'Websites'].map(c => h('option', {value: c, text: c})));
    const status = h('p', {class: 'hdpa-status', role: 'status', 'aria-live': 'polite'});
    const go = h('button', {type: 'button', class: 'hd-btn pri', text: 'Save as a template'});
    sheet('Save as a template', h('div', {class: 'hdpa-body'},
      h('p', {class: 'hdpa-lead', text: 'A copy of this file as it is now goes to My templates in your file browser. Only you can see it; it is never shared or made public.'}),
      h('label', {class: 'hdpa-lab'}, h('span', {text: 'Name'}), name), h('label', {class: 'hdpa-lab'}, h('span', {text: 'Category'}), cat), status),
      h('div', {class: 'hdpa-foot'}, h('span', {class: 'hdpa-hint', text: 'Your file itself does not change.'}), go));
    name.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Enter') go.click(); });
    go.addEventListener('click', async () => {
      go.disabled = true; status.className = 'hdpa-status busy'; status.textContent = 'Saving…';
      try { await ui.api('POST', '/files/' + enc(f.id) + '/publish-template', {name: name.value.trim(), category: cat.value}); gal.data = null; ui.closeModal(); ui.toast('Saved to My templates. Only you can see it.'); }
      catch (e) { go.disabled = false; status.className = 'hdpa-status bad'; status.textContent = (e && e.message) || 'It could not be saved.'; }
    });
    setTimeout(() => name.select(), 0);
  }

  /* ================================================================ wiring */
  ui.command({id: 'plugin-ask', label: 'Ask Hoola to make a plugin…', group: 'Plugins', when: signedIn, run: () => ask()});
  ui.command({id: 'template-save', label: 'Save as a template…', group: 'File', when: signedIn, run: saveAsTemplate});
  ui.registerMenu('main', {label: 'Ask Hoola to make a plugin…', icon: 'spark', run: () => ask()});
  ui.registerMenu('main', {label: 'Save as a template…', icon: 'copy', run: saveAsTemplate});
  if (typeof MutationObserver === 'function') new MutationObserver(() => { addTab(); watchManager(); }).observe(document.documentElement, {childList: true, subtree: true});
  window.addEventListener('hashchange', () => { if (!/^#\/?$/.test(location.hash || '#/') && !/^#\/templates/.test(location.hash)) gal.on = false; });
  HD.pluginsAI = {ask: ask, starters: starters, templates: openGallery, saveAsTemplate: saveAsTemplate, get draft() { return st.draft; }};
})();
