/* HOOLA DESIGN - D7 bridge A: Import from Figma (docs/HOOLA_DESIGN_PLAN.md section 7 A; server: design/figma.py).
   Where it shows: an "Import from Figma" button in the file browser's header (put there by watching the page for that
   header: hd-app.js has no hook for it), "Import from Figma\u2026" in the editor's main menu and in the command palette,
   and the address  #/import/<job>  (the link the chat's hoola_design tool gives) opens the same dialog on that job.
   The dialog: her Figma personal access token if none is saved yet (a password field; it is sealed on the server,
   shared with Web Studio, and never shown again - the server answers only "...abcd"), then the file link, Import,
   the job's real steps and counts while it runs, and "Open file" + every warning when it is done.
   Plain text only: everything from the server is set with textContent. Loaded after hd-ai.js, before hd-app.js. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const ui = HD.ui;
  if (!ui || !ui.h) return;
  const h = ui.h, icon = ui.icon, clear = ui.clear;
  const TOKEN_PAGE = 'https://www.figma.com/settings';
  const HELP = 'https://help.figma.com/hc/en-us/articles/8085703771159-Manage-personal-access-tokens';
  const STATES = {queued: 'Waiting to start', reading: 'Reading the file', images: 'Getting the pictures', writing: 'Writing the layers', done: 'Imported', failed: 'Stopped'};
  const enc = encodeURIComponent;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const st = {box: null, body: null, job: null, polling: 0};

  function alive() { return !!(st.box && document.contains(st.box)); }
  function close() { st.polling++; if (alive()) ui.closeModal(); st.box = null; }

  /* ---------------------------------------------------------------- the dialog */
  function open(jobId) {
    if (alive()) { if (jobId) watch(jobId); return; }
    st.body = h('div', {class: 'hd-fig-body', 'aria-live': 'polite'});
    st.box = ui.modal('hd-fig', 'Import from Figma', [
      h('div', {class: 'hd-fig-head'}, h('span', {class: 'hd-fig-mark', 'aria-hidden': 'true'}, icon('export')), h('h2', {text: 'Import from Figma'}),
        h('button', {class: 'hd-ib', type: 'button', title: 'Close', 'aria-label': 'Close', on: {click: close}}, icon('close'))),
      st.body]);
    st.box.addEventListener('keydown', ev => { if (ev.key === 'Escape') { ev.stopPropagation(); close(); } else ev.stopPropagation(); });
    if (jobId) watch(jobId); else start();
  }
  function say(text, bad) { return h('p', {class: bad ? 'hd-fig-err' : 'hd-fig-sub', role: bad ? 'alert' : null, text: text}); }
  async function start() {
    clear(st.body).appendChild(say('Checking your Figma connection\u2026'));
    let s;
    try { s = await ui.api('GET', '/figma'); } catch (e) { clear(st.body).appendChild(say(e.message || 'Hoola could not check your Figma connection.', true)); return; }
    if (!alive()) return;
    if (s && s.linked) linkStep(s.hint || ''); else tokenStep('');
  }

  function tokenStep(err) {
    const inp = h('input', {class: 'hd-in hd-fig-in', type: 'password', autocomplete: 'off', spellcheck: 'false', 'aria-label': 'Figma personal access token', placeholder: 'figd_\u2026', name: 'hoola-figma-token'});
    const save = h('button', {class: 'hd-btn pri', type: 'submit', text: 'Save token'});
    const form = h('form', {class: 'hd-fig-form', autocomplete: 'off'},
      h('p', {class: 'hd-fig-lead', text: 'Hoola reads your Figma files with your own personal access token, through Figma\u2019s official API. Figma is only read, never changed.'}),
      h('ol', {class: 'hd-fig-steps'},
        h('li', null, 'Open ', h('a', {href: TOKEN_PAGE, target: '_blank', rel: 'noopener noreferrer', text: 'Figma\u2019s settings'}), ' > Security > Personal access tokens.'),
        h('li', {text: 'Make a new token that can read file content, and copy it.'}),
        h('li', {text: 'Paste it here and save.'})),
      h('label', {class: 'hd-fig-lab'}, h('span', {text: 'Personal access token'}), inp),
      h('p', {class: 'hd-fig-note'}, icon('lock'), h('span', {text: 'Stored sealed on the server and never shown again. It is the same token Web Studio uses, so you only add it once. Never paste it into a chat.'})),
      err ? say(err, true) : null,
      h('div', {class: 'hd-fig-acts'}, h('a', {class: 'hd-fig-help', href: HELP, target: '_blank', rel: 'noopener noreferrer', text: 'Help with tokens'}), save));
    form.addEventListener('submit', async ev => {
      ev.preventDefault(); const v = inp.value.trim(); if (!v) { inp.focus(); return; }
      save.disabled = true; save.textContent = 'Saving\u2026';
      try { const r = await ui.api('PUT', '/figma', {token: v}); inp.value = ''; if (alive()) linkStep((r && r.hint) || ''); }
      catch (e) { inp.value = ''; if (alive()) tokenStep(e.message || 'The token could not be saved.'); }
    });
    clear(st.body).appendChild(form); inp.focus();
  }

  function linkStep(hint, err, url) {
    const link = h('input', {class: 'hd-in hd-fig-in', type: 'url', autocomplete: 'off', spellcheck: 'false', 'aria-label': 'Figma file link', placeholder: 'https://www.figma.com/design/\u2026', value: url || ''});
    const name = h('input', {class: 'hd-in hd-fig-in', type: 'text', autocomplete: 'off', 'aria-label': 'Name of the new file (optional)', placeholder: 'Same as in Figma', maxlength: '180'});
    const go = h('button', {class: 'hd-btn pri', type: 'submit'}, icon('export'), h('span', {text: 'Import'}));
    const forget = h('button', {class: 'hd-fig-link', type: 'button', text: 'Use another token'});
    forget.addEventListener('click', async () => { if (!window.confirm('Forget the saved Figma token? Web Studio uses the same one, so it is forgotten there too.')) return;
      try { await ui.api('DELETE', '/figma'); if (alive()) tokenStep(''); } catch (e) { ui.toast(e.message || 'That did not work.', true); } });
    const form = h('form', {class: 'hd-fig-form', autocomplete: 'off'},
      h('p', {class: 'hd-fig-ok'}, icon('check'), h('span', {text: 'Your Figma token is saved' + (hint ? ' (' + hint + ')' : '') + '.'}), forget),
      h('label', {class: 'hd-fig-lab'}, h('span', {text: 'Link to the Figma design file'}), link),
      h('label', {class: 'hd-fig-lab'}, h('span', {text: 'Name in Hoola Design (optional)'}), name),
      h('p', {class: 'hd-fig-note'}, icon('page'), h('span', {text: 'A NEW file is made; your Figma file is not changed. Layers, pages, components, auto layout, text and pictures come across; anything without a Hoola equivalent is listed when the import is done.'})),
      err ? say(err, true) : null,
      h('div', {class: 'hd-fig-acts'}, h('span'), go));
    form.addEventListener('submit', async ev => {
      ev.preventDefault(); const v = link.value.trim(); if (!v) { link.focus(); return; }
      go.disabled = true;
      try { const r = await ui.api('POST', '/import/figma', {url: v, name: name.value.trim() || null}); if (alive()) watch(r.job.id, r.job); }
      catch (e) { if (!alive()) return; if (/token/i.test(e.message || '') && /add your figma/i.test(e.message || '')) tokenStep(e.message); else linkStep(hint, e.message || 'The import could not start.', v); }
    });
    clear(st.body).appendChild(form); link.focus();
  }

  /* ---------------------------------------------------------------- progress */
  function progress(j) {
    const total = +j.total || 0, done = Math.min(total, +j.done || 0), pct = total ? Math.round(done / total * 100) : 0;
    const bar = h('div', {class: 'hd-fig-bar' + (total ? '' : ' wait'), role: 'progressbar', 'aria-valuemin': '0', 'aria-valuemax': String(total || 100), 'aria-valuenow': total ? String(done) : null, 'aria-label': 'Import progress'}, h('i', {style: {width: (total ? pct : 30) + '%'}}));
    const order = ['reading', 'images', 'writing'], at = order.indexOf(j.state);
    return h('div', {class: 'hd-fig-run'},
      h('ul', {class: 'hd-fig-stages'}, order.map((s, i) => h('li', {class: i < at ? 'past' : i === at ? 'now' : ''}, h('span', {class: 'hd-fig-dot', 'aria-hidden': 'true'}), h('span', {text: STATES[s]})))),
      h('p', {class: 'hd-fig-step', text: (j.step || STATES[j.state] || 'Working') + (total ? ' \u00B7 ' + done.toLocaleString() + ' of ' + total.toLocaleString() : '')}),
      bar, j.name ? h('p', {class: 'hd-fig-sub', text: 'From \u201C' + j.name + '\u201D'}) : null,
      h('p', {class: 'hd-fig-sub', text: 'You can close this window: the import goes on, and the new file appears in your files.'}));
  }
  function result(j) {
    const warns = Array.isArray(j.warnings) ? j.warnings : [];
    const open = h('button', {class: 'hd-btn pri', type: 'button', on: {click: () => { const id = j.file; close(); if (id) location.hash = '#/f/' + enc(id); }}}, icon('right'), h('span', {text: 'Open file'}));
    const facts = [(+j.layers || 0).toLocaleString() + ' layers', (+j.pages || 0) + ((+j.pages || 0) === 1 ? ' page' : ' pages'), (+j.images || 0) + ((+j.images || 0) === 1 ? ' picture' : ' pictures')].join(' \u00B7 ');
    return h('div', {class: 'hd-fig-res'},
      h('p', {class: 'hd-fig-ok big'}, icon('check'), h('span', {text: '\u201C' + (j.name || 'Figma file') + '\u201D is in Hoola Design'})),
      h('p', {class: 'hd-fig-sub', text: facts}),
      warns.length ? h('div', {class: 'hd-fig-warns'}, h('h3', {text: 'Not brought across exactly (' + warns.length + ')'}),
        h('ul', null, warns.slice(0, 80).map(w => h('li', null, h('span', {text: String((w && w.text) || w)}), w && w.count > 1 ? h('b', {text: '\u00D7 ' + Number(w.count).toLocaleString()}) : null))))
        : h('p', {class: 'hd-fig-sub', text: 'Everything in the file had a Hoola equivalent.'}),
      h('div', {class: 'hd-fig-acts'}, h('button', {class: 'hd-btn', type: 'button', text: 'Import another', on: {click: start}}), open));
  }
  function failed(j) {
    return h('div', {class: 'hd-fig-res'}, say(j.error || 'The import stopped.', true),
      h('div', {class: 'hd-fig-acts'}, h('button', {class: 'hd-btn', type: 'button', text: 'Close', on: {click: close}}), h('button', {class: 'hd-btn pri', type: 'button', text: 'Try again', on: {click: start}})));
  }
  async function watch(jobId, first) {
    const my = ++st.polling; st.job = jobId; let j = first || null, misses = 0;
    if (j) clear(st.body).appendChild(progress(j)); else clear(st.body).appendChild(say('Looking for the import\u2026'));
    while (alive() && my === st.polling) {
      if (j && (j.state === 'done' || j.state === 'failed')) { clear(st.body).appendChild(j.state === 'done' ? result(j) : failed(j)); if (j.state === 'done') refreshHome(); return; }
      await sleep(j ? 700 : 0);
      if (!alive() || my !== st.polling) return;
      try { j = await ui.api('GET', '/import/' + enc(jobId)); misses = 0; clear(st.body).appendChild(j.state === 'done' || j.state === 'failed' ? h('span') : progress(j)); }
      catch (e) { if (++misses >= 3 || /no such import/i.test(e.message || '')) { clear(st.body).appendChild(say(e.message || 'The import could not be found.', true)); return; } await sleep(1500); }
    }
  }
  function refreshHome() { if (!(HD.app && HD.app.file) && HD.app && HD.app.home && document.querySelector('.hd-hhead')) { try { HD.app.home(); } catch (e) { /* the browser redraws on its own later */ } } }

  /* ---------------------------------------------------------------- where it shows */
  function addHomeButton() {
    const right = document.querySelector('.hd-hhead .hd-hright');
    if (!right || right.querySelector('.hd-fig-open')) return;
    const b = h('button', {class: 'hd-btn big hd-fig-open', type: 'button', title: 'Import a Figma file with your own Figma token'}, icon('export'), h('span', {text: 'Import from Figma'}));
    b.addEventListener('click', () => open());
    const pri = right.querySelector('.hd-btn.pri'); right.insertBefore(b, pri || null);
  }
  if (typeof MutationObserver === 'function') new MutationObserver(addHomeButton).observe(document.documentElement, {childList: true, subtree: true});
  ui.registerMenu('main', {label: 'Import from Figma\u2026', icon: 'export', run: () => open()});
  if (ui.command) ui.command({id: 'figmaImport', label: 'Import from Figma\u2026', group: 'File', run: () => open()});
  function fromHash() { const m = /^#\/import\/([^/?#]+)/.exec(location.hash || ''); if (!m) return; let id = m[1]; try { id = decodeURIComponent(id); } catch (e) { /* as typed */ }
    if (ui.token) { open(id); try { history.replaceState(null, '', location.pathname + location.search + '#/'); } catch (e) { /* the address stays */ } } }
  window.addEventListener('hashchange', () => setTimeout(fromHash, 0));      /* after hd-app.js has left the editor (that closes any dialog) */
  const later = () => setTimeout(fromHash, 0);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', later); else later();
  HD.bridgeFigma = {open: open, watch: id => open(id)};
})();
