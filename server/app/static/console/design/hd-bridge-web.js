/* HOOLA DESIGN - D7 bridge B: a frame -> Web Studio (docs/HOOLA_DESIGN_PLAN.md section 7 B).
   One selected frame: "Send to Web Studio…" (right-click menu, the Design panel, the command palette) opens a dialog -
     - a NEW website whose first page is this frame (name prefilled, an optional line on what it is for), or
     - add it as a section to a page of one of her built websites (her sites from /api/sites, the pages of the one she picks);
     - "Preview HTML" shows the code Web Studio would get, read only, before anything is sent;
     - Send -> the server turns the frame into HTML + CSS and hands it to Web Studio THROUGH Web Studio's own checks
       (design/toweb.py); the result shows "Open in Web Studio" and every warning (what did not translate).
   Nothing is published from here: going live stays her tap in Web Studio. Every text from the server is set with
   textContent (h(..., {text})), never as HTML. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const ui = HD.ui;
  if (!ui || !ui.h) return;
  const h = ui.h;
  const KINDS = {FRAME: 1, COMPONENT: 1, INSTANCE: 1, SECTION: 1};
  const enc = encodeURIComponent;

  const fileId = () => (HD.app && HD.app.file && HD.app.file.id) || '';
  const fileName = () => (HD.app && HD.app.file && HD.app.file.name) || '';
  const canEdit = () => !!fileId() && !!(HD.tools && HD.tools.u && HD.tools.u.canEdit());
  const selIds = () => (HD.sel && HD.sel.ids ? Array.from(HD.sel.ids).filter(id => HD.store.has(id)) : []);
  const frameOf = ids => { ids = ids || selIds(); if (ids.length !== 1) return null; const n = HD.store.get(ids[0]); return n && KINDS[n.type] ? ids[0] : null; };
  const GENERIC = /^\s*(frame|desktop|page|screen|artboard|section|web|phone|tablet|component|instance)(\s*[-\d.x ]*)?\s*$/i;
  function defaultName(id) { const n = HD.store.get(id) || {}; const nm = String(n.name || '').trim(); return (!nm || GENERIC.test(nm) ? fileName() || nm : nm).slice(0, 120); }
  const BUILT = s => !/^(planned|looks|draft)$/.test(String(s.status || ''));

  function open(id) {
    id = id || frameOf();
    if (!id) { ui.toast('Select one frame first.'); return; }
    if (!canEdit()) { ui.toast('This file is view only.'); return; }
    const st = {id: id, mode: 'new', sites: null, site: '', pages: [], page: 'home', busy: false, preview: null, showCode: false, result: null, error: ''};
    const body = h('div', {class: 'hdw-body'});
    const box = ui.modal('hdw-dialog', 'Send to Web Studio', [
      h('div', {class: 'hdw-head'}, h('h2', {text: 'Send to Web Studio'}), h('button', {class: 'hd-ib', type: 'button', title: 'Close', 'aria-label': 'Close', on: {click: () => ui.closeModal()}}, ui.icon('close'))),
      body]);
    const name = h('input', {class: 'hd-in', type: 'text', maxlength: '120', value: defaultName(id), 'aria-label': 'Website name'});
    const brief = h('input', {class: 'hd-in', type: 'text', maxlength: '600', placeholder: 'For example: a sweet shop in Pune', 'aria-label': 'What the website is for'});
    for (const f of [name, brief]) f.addEventListener('keydown', ev => ev.stopPropagation());

    async function loadSites() {
      try { const r = await ui.api('GET', '/api/sites'); st.sites = (r && r.sites) || []; }
      catch (e) { st.sites = []; st.error = (e && e.message) || 'Your websites could not be loaded.'; }
      const built = st.sites.filter(BUILT);
      if (!st.site && built.length) { st.site = String(built[0].id); await loadPages(); }
      paint();
    }
    async function loadPages() {
      st.pages = [];
      if (!st.site) return;
      try {
        const v = await ui.api('GET', '/api/sites/' + enc(st.site));
        st.pages = ((v && v.plan && v.plan.pages) || []).filter(p => !/^(privacy|refund|disclaimer|terms)$/.test(p.slug));
        if (!st.pages.some(p => p.slug === st.page)) st.page = (st.pages[0] && st.pages[0].slug) || 'home';
      } catch (e) { st.error = (e && e.message) || 'The pages could not be loaded.'; }
    }
    async function loadPreview() {
      st.preview = {loading: true}; paint();
      try { st.preview = await ui.api('POST', '/files/' + enc(fileId()) + '/to-site/preview', {node: st.id, mode: st.mode}); }
      catch (e) { st.preview = {error: (e && e.message) || 'The code could not be made.'}; }
      paint();
    }
    async function send() {
      if (st.busy) return;
      st.busy = true; st.error = ''; paint();
      const req = st.mode === 'new' ? {node: st.id, mode: 'new', name: name.value.trim(), brief: brief.value.trim()} : {node: st.id, mode: 'section', site: st.site, page: st.page};
      try { st.result = await ui.api('POST', '/files/' + enc(fileId()) + '/to-site', req); }
      catch (e) { st.error = (e && e.message) || 'Web Studio refused it.'; }
      st.busy = false; paint();
    }

    function warnList(list) {
      if (!list || !list.length) return null;
      return h('div', {class: 'hdw-warn'}, h('p', {class: 'hdw-wtitle', text: 'Not carried over exactly'}), h('ul', null, list.map(w => h('li', {text: String(w)}))));
    }
    function paint() {
      ui.clear(body);
      if (st.result) {
        const r = st.result;
        body.appendChild(h('p', {class: 'hdw-lead', text: String(r.say || 'Sent to Web Studio.')}));
        body.appendChild(h('p', {class: 'hd-note', text: 'Website ' + (r.number || '') + ' · ' + (r.name || '') + ' · page ' + (r.page || 'home') + (r.images ? ' · ' + r.images + ' picture' + (r.images === 1 ? '' : 's') + ' copied' : '')}));
        const w = warnList(r.warnings); if (w) body.appendChild(w);
        if (r.removed && r.removed.length) body.appendChild(h('p', {class: 'hd-note', text: 'Web Studio’s safety check removed: ' + r.removed.join('; ') + '.'}));
        body.appendChild(h('div', {class: 'hdw-foot'}, h('button', {class: 'hd-btn', type: 'button', text: 'Close', on: {click: () => ui.closeModal()}}),
          h('a', {class: 'hd-btn pri', href: String(r.url || '/console/web'), target: '_blank', rel: 'noopener', text: 'Open in Web Studio', on: {click: () => ui.closeModal()}})));
        return;
      }
      const n = HD.store.get(st.id) || {};
      body.appendChild(h('p', {class: 'hdw-lead'}, 'Frame ', h('b', {text: String(n.name || 'Frame')}), ' · ' + Math.round(+n.w || 0) + ' × ' + Math.round(+n.h || 0)));
      const seg = h('div', {class: 'hd-seg hdw-seg', role: 'radiogroup', 'aria-label': 'Where it goes'});
      for (const m of [['new', 'A new website'], ['section', 'Add to a website']]) {
        seg.appendChild(h('button', {class: 'hd-segb' + (st.mode === m[0] ? ' on' : ''), type: 'button', role: 'radio', 'aria-checked': String(st.mode === m[0]), text: m[1],
          on: {click: async () => { if (st.mode === m[0]) return; st.mode = m[0]; st.preview = null; st.error = ''; if (m[0] === 'section' && st.sites === null) { paint(); await loadSites(); } else paint(); }}}));
      }
      body.appendChild(seg);
      if (st.mode === 'new') {
        body.appendChild(h('label', {class: 'hdw-field'}, h('span', {text: 'Website name'}), name));
        body.appendChild(h('label', {class: 'hdw-field'}, h('span', {text: 'What is it for? (optional)'}), brief));
        body.appendChild(h('p', {class: 'hd-note', text: 'The frame becomes the home page of a new website in Web Studio. Its legal pages are added by Web Studio.'}));
      } else if (st.sites === null) body.appendChild(h('p', {class: 'hd-note', text: 'Loading your websites…'}));
      else {
        const built = st.sites.filter(BUILT);
        if (!built.length) body.appendChild(h('p', {class: 'hd-note', text: 'None of your websites is built yet. Send it as a new website, or finish one in Web Studio first.'}));
        else {
          const sel = h('select', {class: 'hd-in', 'aria-label': 'Website'}, built.map(s => h('option', {value: String(s.id), text: (s.number ? s.number + ' · ' : '') + (s.name || 'Untitled'), selected: String(s.id) === st.site})));
          sel.addEventListener('change', async () => { st.site = sel.value; st.pages = []; paint(); await loadPages(); paint(); });
          body.appendChild(h('label', {class: 'hdw-field'}, h('span', {text: 'Website'}), sel));
          const pg = h('select', {class: 'hd-in', 'aria-label': 'Page'}, st.pages.map(p => h('option', {value: p.slug, text: (p.title || p.slug) + ' (' + p.slug + ')', selected: p.slug === st.page})));
          pg.addEventListener('change', () => { st.page = pg.value; });
          body.appendChild(h('label', {class: 'hdw-field'}, h('span', {text: 'Page'}), pg));
          body.appendChild(h('p', {class: 'hd-note', text: 'It is added at the end of the page as a new section. Web Studio checks it and saves a new version.'}));
        }
      }
      const tog = h('button', {class: 'hd-btn hdw-tog', type: 'button', 'aria-expanded': String(st.showCode), text: st.showCode ? 'Hide HTML' : 'Preview HTML',
        on: {click: () => { st.showCode = !st.showCode; if (st.showCode && !st.preview) loadPreview(); else paint(); }}});
      body.appendChild(tog);
      if (st.showCode && st.preview) {
        const p = st.preview;
        if (p.loading) body.appendChild(h('p', {class: 'hd-note', text: 'Making the code…'}));
        else if (p.error) body.appendChild(h('p', {class: 'hdw-err', text: String(p.error)}));
        else {
          body.appendChild(h('div', {class: 'hdw-code'}, h('p', {class: 'hdw-ctitle', text: 'HTML'}), h('pre', {class: 'hdw-pre', tabIndex: 0, text: String(p.html || '')}),
            h('p', {class: 'hdw-ctitle', text: 'CSS'}), h('pre', {class: 'hdw-pre', tabIndex: 0, text: String(p.css || '')})));
          if (p.fonts && p.fonts.length) body.appendChild(h('p', {class: 'hd-note', text: 'Fonts: ' + p.fonts.map(f => f.family + (f.shipped ? '' : ' (not shipped by the website)')).join(', ')}));
          const w = warnList(p.warnings); if (w) body.appendChild(w);
        }
      }
      if (st.error) body.appendChild(h('p', {class: 'hdw-err', role: 'alert', text: st.error}));
      const canSend = !st.busy && (st.mode === 'new' ? !!name.value.trim() : !!(st.site && st.page && st.sites && st.sites.some(s => String(s.id) === st.site && BUILT(s))));
      body.appendChild(h('div', {class: 'hdw-foot'}, h('span', {class: 'hd-note hdw-safe', text: 'Nothing is published. Going live stays your tap in Web Studio.'}),
        h('button', {class: 'hd-btn', type: 'button', text: 'Cancel', on: {click: () => ui.closeModal()}}),
        h('button', {class: 'hd-btn pri hdw-send', type: 'button', disabled: !canSend, text: st.busy ? 'Sending…' : 'Send', on: {click: send}})));
    }
    paint();
    setTimeout(() => { if (document.contains(name)) name.focus(); }, 0);
    return box;
  }

  ui.registerMenu('context', ids => (frameOf(ids) && canEdit() ? {label: 'Send to Web Studio…', icon: 'share', run: () => open(frameOf(ids))} : null));
  ui.command({id: 'sendToWeb', label: 'Send to Web Studio…', group: 'File', when: () => !!frameOf() && canEdit(), run: () => open()});
  if (ui.designSection) ui.designSection((el, ids) => {
    const id = frameOf(ids); if (!id || !canEdit()) return;
    const s = ui.section(el, 'Website', [], {cls: 'hdw-sec'});
    s.body.appendChild(h('button', {class: 'hd-btn hdw-wide', type: 'button', text: 'Send to Web Studio…', on: {click: () => open(id)}}));
  });

  HD.bridgeWeb = {open: open};
})();
