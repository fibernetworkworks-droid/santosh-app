/* HOOLA DESIGN - D5 AI: "Ask Hoola" - one line -> a designed frame, or a change to what is selected.
   The server makes the design (POST /api/design/files/<id>/ai: the model only ever writes a validated spec, code
   turns it into ops and applies them THROUGH the room), so the new layers arrive like anybody else's edit. This
   file is the composer, the progress and what she can do with the result:
     - Remove            the new frames go in ONE ordinary transaction (a server-made change is not on her undo stack)
     - Revert            for a change of the selection: the layers go back to how they were when she asked
     - Try again / Make variations (3 more side by side)
   The server sizes words from a table of letter widths, not the real font. Every frame it makes carries the mark
   `aiSettle`; an editor that sees the mark runs the real layout once over that frame (fonts loaded first) and takes
   the mark off. That is the only edit this file makes without being asked, and it is one merged undo step.
   Text from the server (names, notes, errors) is always set with textContent. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const ui = HD.ui;
  if (!ui || !ui.h) return;
  const h = ui.h;
  const PROMPT_MAX = 2000, VARIATIONS = 3;
  const PRESETS = [['', 'Auto'], ['phone', 'Phone app'], ['web', 'Web page'], ['instagram', 'Insta post'], ['story', 'Story'],
    ['poster', 'Poster'], ['card', 'Business card'], ['slide', 'Slide'], ['logo', 'Logo'], ['android', 'Android'], ['whatsapp', 'WhatsApp status']];
  const IDEAS = ['A home screen for a food delivery app', 'Diwali sale poster for my sweet shop', 'Landing page for a yoga studio',
    'Instagram post: grand opening this Sunday', 'A business card for a boutique'];
  const st = {open: false, busy: false, prompt: '', preset: '', brand: true, at: null, last: null, error: '', t0: 0, tick: 0, panel: null, fab: null, note: ''};
  try { st.brand = localStorage.getItem('hoola.design.ai.brand') !== '0'; } catch (e) { /* private window */ }

  const canEdit = () => !!(HD.app && HD.app.file) && !!(HD.tools && HD.tools.u && HD.tools.u.canEdit());
  const fileId = () => (HD.app && HD.app.file && HD.app.file.id) || '';
  const selIds = () => (HD.sel && HD.sel.ids ? Array.from(HD.sel.ids).filter(id => HD.store.has(id)) : []);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  function viewCentre() {
    try { const c = HD.tools.view.centre(), w = HD.render.screenToWorld(c[0], c[1]); return {x: Math.round(w[0]), y: Math.round(w[1])}; } catch (e) { return null; }
  }

  /* ---------------------------------------------------------------- settle: the real layout, once */
  const settled = new Set();
  let settleT = 0;
  function subtree(root) { const ids = []; HD.store.walk(root, id => { ids.push(id); return ids.length < 5000; }); return ids; }
  async function fontsOf(ids) {
    /* the families through the editor's own loader (it adds the stylesheet), then every WEIGHT really used: a bold
       headline measured before its bold face arrived would be sized with a stand-in */
    const fams = new Set(), faces = new Map();
    for (const id of ids) { const n = HD.store.get(id); if (!n || n.type !== 'TEXT') continue; const f = String(n.font || 'Inter').replace(/["\\]/g, ''), w = Math.round(+n.fontWeight || 400);
      fams.add(f); faces.set(w + ' 16px "' + f + '"', String(n.chars || 'Aa').slice(0, 24)); }
    const first = Array.from(fams).map(f => { try { return Promise.resolve(ui.loadFont(f)).catch(() => false); } catch (e) { return Promise.resolve(false); } });
    await Promise.race([Promise.all(first), sleep(4000)]);
    if (document.fonts && document.fonts.load) {
      const rest = Array.from(faces).map(e => document.fonts.load(e[0], e[1]).catch(() => null));
      await Promise.race([Promise.all(rest), sleep(3000)]);
    }
    try { if (HD.layout.fontsChanged) HD.layout.fontsChanged(); } catch (e) { /* the layout keeps its own measure */ }
  }
  async function settle(roots) {
    roots = roots.filter(id => HD.store.has(id));
    if (!roots.length || !canEdit()) return;
    let ids = [];
    for (const r of roots) ids = ids.concat(subtree(r));
    await fontsOf(ids);
    if (!canEdit()) return;
    try {
      HD.store.tx('Hoola layout', () => {
        HD.layout.run(new Set(ids.filter(id => HD.store.has(id))));
        for (const r of roots) { const n = HD.store.get(r); if (n && n.aiSettle !== undefined) HD.store.set(r, {aiSettle: null}); }
      }, {merge: 'hd-ai-settle'});
    } catch (e) { /* a view-only file, or the layers are gone */ }
    HD.render.invalidate(true);
  }
  /* frames another editor (or the agent tool) asked for: settle them too, a moment later, if nobody else has */
  function scanMarks(delay) {
    clearTimeout(settleT);
    settleT = setTimeout(() => {
      if (!canEdit() || !HD.store.pages) return;
      const todo = [];
      for (const p of HD.store.pages()) for (const id of HD.store.children(p)) {
        const n = HD.store.get(id), mark = n && n.aiSettle;
        if (typeof mark === 'string' && !settled.has(id + '|' + mark)) { settled.add(id + '|' + mark); todo.push(id); }
      }
      if (todo.length) settle(todo);
    }, delay);
  }
  function wireStore() {
    if (wireStore.done || !HD.store || !HD.store.on) return;
    wireStore.done = true;
    HD.store.on('load', () => scanMarks(1200));
    HD.store.on('change', ch => { if (ch && ch.remote && ch.structural !== false) scanMarks(1800); });
  }

  /* ---------------------------------------------------------------- asking */
  async function waitFor(ids, ms) {
    const until = Date.now() + ms;
    while (Date.now() < until) { if (ids.every(id => HD.store.has(id))) return true; await sleep(80); }
    return ids.some(id => HD.store.has(id));
  }
  function snapshot(ids) {
    const snap = new Map();
    for (const root of ids) for (const id of subtree(root)) { const n = HD.store.get(id); if (n) snap.set(id, JSON.parse(JSON.stringify(n))); }
    return snap;
  }
  async function request(body) {
    return ui.api('POST', '/files/' + encodeURIComponent(fileId()) + '/ai', body);
  }
  async function ask(opts) {
    opts = opts || {};
    const prompt = (opts.prompt !== undefined ? opts.prompt : st.prompt).trim();
    if (!prompt) { st.error = 'Say in a line what Hoola should design.'; paint(); return; }
    if (st.busy || !canEdit()) return;
    const sel = opts.mode === 'new' ? [] : selIds();
    const mode = opts.mode || (sel.length ? 'edit' : 'new');
    const body = {prompt: prompt, page: HD.sel.page, mode: mode, preset: st.preset, brand: st.brand};
    if (mode === 'edit') body.selection = sel;
    else { const at = opts.at || st.at || viewCentre(); if (at && !opts.beside) { body.x = at.x; body.y = at.y; } }
    const snap = mode === 'edit' ? snapshot(sel) : null;
    const count = Math.max(1, Math.min(VARIATIONS, opts.variations || 1));
    st.busy = true; st.error = ''; st.note = ''; st.t0 = performance.now(); st.step = count > 1 ? [0, count] : null;
    paint(); startClock();
    const made = [], notes = [];
    let engine = '', res = null, failed = '';
    for (let i = 0; i < count; i++) {
      if (count > 1) { st.step = [i + 1, count]; body.variant = i + 1; delete body.x; delete body.y; paint(); }
      try { res = await request(body); } catch (e) { failed = (e && e.message) || 'Hoola could not design this.'; break; }
      engine = res.engine || engine;
      if (res.notes) notes.push(res.notes);
      if (mode === 'edit') break;
      const roots = Array.isArray(res.roots) ? res.roots : [];
      await waitFor(roots, 6000);
      for (const r of roots) { const n = HD.store.get(r); if (n && typeof n.aiSettle === 'string') settled.add(r + '|' + n.aiSettle); }
      await settle(roots);
      for (const r of roots) if (HD.store.has(r)) made.push(r);
    }
    stopClock(); st.busy = false;
    const secs = Math.max(1, Math.round((performance.now() - st.t0) / 1000));
    if (mode === 'edit' && res && !failed) {
      const touched = (res.touched || []).filter(id => typeof id === 'string');
      await sleep(120); await waitFor(res.added || [], 4000);
      await settle(sel.filter(id => HD.store.has(id)));
      st.last = {mode: 'edit', prompt: prompt, touched: touched, added: res.added || [], snap: snap, sel: sel, engine: engine, secs: secs,
        notes: res.notes || '', refused: res.refused || [], left: res.left};
      st.note = touched.length ? '' : 'Nothing needed to change.'; st.prompt = '';
    } else if (made.length) {
      st.last = {mode: 'new', prompt: prompt, roots: made, engine: engine, secs: secs, notes: notes[0] || '', left: res && res.left,
        fixed: res && res.contrast_fixed, blanked: res && res.blanked};
      try { HD.sel.set(made); HD.render.zoomToFit(made, true); } catch (e) { /* the frames are there even if the view did not move */ }
      st.at = null; st.prompt = '';
    }
    if (failed) st.error = failed;
    paint();
    if (st.panel) { const f = st.panel.querySelector(failed ? '.hdai-in' : '.hdai-acts button'); if (f) f.focus({preventScroll: true}); }
  }
  function removeLast() {
    const L = st.last; if (!L || L.mode !== 'new') return;
    const ids = L.roots.filter(id => HD.store.has(id));
    if (ids.length) HD.store.tx('Remove Hoola design', () => { HD.store.remove(ids); });
    try { HD.sel.set([]); } catch (e) { /* nothing selected */ }
    st.last = null; st.note = 'Removed.'; paint();
  }
  function revertLast() {
    const L = st.last; if (!L || L.mode !== 'edit' || !L.snap) return;
    HD.store.tx('Revert Hoola change', () => {
      const gone = (L.added || []).filter(id => HD.store.has(id));
      if (gone.length) HD.store.remove(gone);
      L.snap.forEach((was, id) => {
        const now = HD.store.get(id); if (!now) return;
        const back = {};
        for (const k of new Set(Object.keys(now).concat(Object.keys(was)))) {
          if (k === 'type' || k === 'parent' || k === 'idx') continue;
          if (JSON.stringify(now[k]) !== JSON.stringify(was[k])) back[k] = was[k] === undefined ? null : was[k];
        }
        if (Object.keys(back).length) HD.store.set(id, back);
      });
    });
    st.last = null; st.note = 'Put back the way it was.'; paint();
  }
  async function again() {
    const L = st.last; if (!L) return ask();
    const prompt = L.prompt;
    if (L.mode === 'new') { const ids = L.roots.filter(id => HD.store.has(id)); if (ids.length) HD.store.tx('Remove Hoola design', () => { HD.store.remove(ids); }); st.last = null; return ask({prompt: prompt, mode: 'new'}); }
    revertLast(); try { HD.sel.set(L.sel.filter(id => HD.store.has(id))); } catch (e) { /* gone */ }
    return ask({prompt: prompt, mode: 'edit'});
  }
  function variations() { const L = st.last; if (!L || L.mode !== 'new') return; return ask({prompt: L.prompt, mode: 'new', variations: VARIATIONS, beside: true}); }

  /* ---------------------------------------------------------------- the composer */
  function startClock() { stopClock(); st.tick = setInterval(() => { const el = st.panel && st.panel.querySelector('.hdai-secs'); if (el) el.textContent = secsText(); }, 250); }
  function stopClock() { clearInterval(st.tick); st.tick = 0; }
  function secsText() { const s = Math.floor((performance.now() - st.t0) / 1000); return s + ' s'; }
  function chip(value, label) {
    return h('button', {class: 'hdai-chip' + (st.preset === value ? ' on' : ''), type: 'button', 'aria-pressed': st.preset === value ? 'true' : 'false', text: label,
      on: {click: () => { st.preset = value; paint(); const f = st.panel && st.panel.querySelector('.hdai-in'); if (f) f.focus({preventScroll: true}); }}});
  }
  function resultView() {
    const L = st.last, box = h('div', {class: 'hdai-result', role: 'status', 'aria-live': 'polite'});
    if (L.mode === 'new') {
      const names = L.roots.map(id => { const n = HD.store.get(id); return n ? (n.name || 'Frame') + ' (' + Math.round(n.w) + ' × ' + Math.round(n.h) + ')' : null; }).filter(Boolean);
      box.appendChild(h('p', {class: 'hdai-done'}, ui.icon('check', 14), h('span', {text: (names.length > 1 ? names.length + ' frames added' : 'Added ' + (names[0] || 'a frame')) + ' in ' + L.secs + ' s'})));
      if (L.engine === 'template') box.appendChild(h('p', {class: 'hdai-sub', text: 'No AI model is set up on this server, so this is one of Hoola’s built-in layouts filled from your words. Every [blank] is a fact only you know.'}));
      else if (L.notes) box.appendChild(h('p', {class: 'hdai-sub', text: L.notes}));
      const extra = [];
      if (L.fixed) extra.push(L.fixed + (L.fixed === 1 ? ' text colour was' : ' text colours were') + ' changed so the words read clearly');
      if (L.blanked) extra.push(L.blanked + (L.blanked === 1 ? ' fact' : ' facts') + ' nobody gave became a [blank]');
      if (extra.length) box.appendChild(h('p', {class: 'hdai-sub', text: extra.join('; ') + '.'}));
      box.appendChild(h('div', {class: 'hdai-acts'},
        h('button', {class: 'hd-btn', type: 'button', text: 'Remove', on: {click: removeLast}}),
        h('button', {class: 'hd-btn', type: 'button', text: 'Try again', on: {click: again}}),
        h('button', {class: 'hd-btn', type: 'button', text: 'Make variations (' + VARIATIONS + ')', title: VARIATIONS + ' more designs for the same words, side by side', on: {click: variations}})));
    } else {
      const n = L.touched.length;
      box.appendChild(h('p', {class: 'hdai-done'}, ui.icon('check', 14), h('span', {text: (n ? n + (n === 1 ? ' layer' : ' layers') + ' changed' : 'Nothing needed to change') + ' in ' + L.secs + ' s'})));
      if (L.notes) box.appendChild(h('p', {class: 'hdai-sub', text: L.notes}));
      if (L.refused && L.refused.length) box.appendChild(h('p', {class: 'hdai-sub', text: 'Not done (an edit never deletes or moves layers): ' + L.refused.slice(0, 4).join(', ')}));
      box.appendChild(h('div', {class: 'hdai-acts'},
        n ? h('button', {class: 'hd-btn', type: 'button', text: 'Revert', on: {click: revertLast}}) : null,
        h('button', {class: 'hd-btn', type: 'button', text: 'Try again', on: {click: again}})));
    }
    return box;
  }
  function paint() {
    syncFab();
    if (!st.open) { if (st.panel) { st.panel.remove(); st.panel = null; } return; }
    const stage = document.querySelector('.hd-stage');
    if (!stage) { st.open = false; return; }
    if (!st.panel || !stage.contains(st.panel)) { st.panel = h('section', {class: 'hdai-panel', role: 'dialog', 'aria-label': 'Ask Hoola'}); stage.appendChild(st.panel);
      st.panel.addEventListener('keydown', ev => { if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); close(); } });
      st.panel.addEventListener('pointerdown', ev => ev.stopPropagation()); st.panel.addEventListener('wheel', ev => ev.stopPropagation()); }
    const keep = st.panel.querySelector('.hdai-in'), hadFocus = keep && document.activeElement === keep, caret = keep ? keep.selectionStart : null;
    ui.clear(st.panel);
    const sel = selIds(), editing = sel.length > 0;
    const head = h('header', {class: 'hdai-head'}, h('span', {class: 'hdai-mark'}, ui.icon('spark', 16)), h('strong', {text: 'Ask Hoola'}),
      h('span', {class: 'hdai-mode', text: editing ? 'Change the ' + sel.length + (sel.length === 1 ? ' selected layer' : ' selected layers') : 'A new design'}),
      h('button', {class: 'hd-ib hdai-x', type: 'button', title: 'Close  (Esc)', 'aria-label': 'Close', on: {click: close}}, ui.icon('close')));
    st.panel.appendChild(head);
    if (st.busy) {
      st.panel.appendChild(h('div', {class: 'hdai-busy', role: 'status', 'aria-live': 'polite'}, h('span', {class: 'hdai-spin', 'aria-hidden': 'true'}),
        h('span', {text: st.step ? 'Designing option ' + st.step[0] + ' of ' + st.step[1] + '…' : (editing ? 'Hoola is changing it…' : 'Hoola is designing…')}),
        h('span', {class: 'hdai-secs', text: secsText()})));
      st.panel.appendChild(h('p', {class: 'hdai-quote', text: st.prompt}));
      return;
    }
    const input = h('textarea', {class: 'hdai-in', rows: 3, maxlength: PROMPT_MAX, 'aria-label': editing ? 'What should change?' : 'What should Hoola design?',
      placeholder: editing ? 'What should change?  e.g. make it more premium · dark theme · translate to Hindi · add a pricing section' : 'What should Hoola design?  e.g. ' + IDEAS[Math.floor(Date.now() / 60000) % IDEAS.length]});
    input.value = st.prompt;
    input.addEventListener('input', () => { st.prompt = input.value; const b = st.panel.querySelector('.hdai-go'); if (b) b.disabled = !st.prompt.trim(); if (st.error) { st.error = ''; const er = st.panel.querySelector('.hdai-err'); if (er) er.remove(); } });
    input.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey || !ev.shiftKey)) { ev.preventDefault(); ask(); } else if (ev.key === 'Escape') { ev.preventDefault(); close(); } });
    st.panel.appendChild(input);
    if (st.error) st.panel.appendChild(h('p', {class: 'hdai-err', role: 'alert', text: st.error}));
    if (!editing) st.panel.appendChild(h('div', {class: 'hdai-chips', role: 'group', 'aria-label': 'Size'}, PRESETS.map(p => chip(p[0], p[1]))));
    const brand = h('input', {type: 'checkbox', checked: st.brand, id: 'hdai-brand'});
    brand.addEventListener('change', () => { st.brand = brand.checked; try { localStorage.setItem('hoola.design.ai.brand', st.brand ? '1' : '0'); } catch (e) { /* private window */ } });
    const go = h('button', {class: 'hd-btn pri hdai-go', type: 'button', disabled: !st.prompt.trim(), on: {click: () => ask()}}, ui.icon('spark', 14), h('span', {text: editing ? 'Change it' : 'Design'}));
    st.panel.appendChild(h('div', {class: 'hdai-foot'}, h('label', {class: 'hdai-brand', for: 'hdai-brand', title: 'Use the name, colours and logo of your brand kit'}, brand, h('span', {text: 'Use my brand'})),
      h('span', {class: 'hdai-hint', text: 'Enter to send · Shift+Enter for a new line'}), go));
    if (st.note) st.panel.appendChild(h('p', {class: 'hdai-sub', role: 'status', text: st.note}));
    if (st.last) st.panel.appendChild(resultView());
    if (hadFocus || !keep) { input.focus({preventScroll: true}); if (caret !== null) { try { input.setSelectionRange(caret, caret); } catch (e) { /* not focusable yet */ } } }
  }
  function open(at) {
    if (!HD.app || !HD.app.file) return;
    if (!canEdit()) { ui.toast('This file is view only.'); return; }
    wireStore();
    st.open = true; st.at = at && typeof at.x === 'number' ? {x: at.x, y: at.y} : null; st.error = ''; st.note = '';
    if (ui.closePops) ui.closePops(0);
    paint();
    const f = st.panel && st.panel.querySelector('.hdai-in'); if (f) f.focus({preventScroll: true});
  }
  function close() { if (st.busy) return; st.open = false; paint(); try { if (HD.tools.canvas) HD.tools.canvas.focus({preventScroll: true}); } catch (e) { /* no canvas */ } }
  function toggle() { if (st.open) close(); else open(null); }

  /* ---------------------------------------------------------------- the button on the canvas */
  function syncFab() {
    const stage = document.querySelector('.hd-stage');
    if (!stage) { st.fab = null; return; }
    if (!st.fab || !stage.contains(st.fab)) {
      st.fab = h('button', {class: 'hdai-fab', type: 'button', title: 'Ask Hoola to design  (' + ui.keysLabel('mod+i') + ')', on: {click: toggle}}, ui.icon('spark', 16), h('span', {text: 'Ask Hoola'}));
      st.fab.addEventListener('pointerdown', ev => ev.stopPropagation());
      stage.appendChild(st.fab);
    }
    st.fab.hidden = st.open || !canEdit();
  }
  function watchMount() {
    const root = document.getElementById('hd-app');
    if (!root || watchMount.done) return;
    watchMount.done = true;
    let t = 0;
    const later = () => { clearTimeout(t); t = setTimeout(() => { wireStore(); if (st.panel && !document.contains(st.panel)) { st.panel = null; st.open = false; st.last = null; st.busy = false; stopClock(); } syncFab(); scanMarks(1500); }, 60); };
    new MutationObserver(later).observe(root, {childList: true});
    later();
  }

  ui.hook('ai', at => open(at));
  ui.registerShortcut('mod+i', toggle, 'Ask Hoola to design');
  ui.registerMenu('context', (ids, e) => (canEdit() ? {label: ids && ids.length ? 'Ask Hoola to change this…' : 'Ask Hoola to design here…', keys: 'mod+i', icon: 'spark',
    run: () => open(ids && ids.length ? null : (e && typeof e.x === 'number' ? {x: Math.round(e.x), y: Math.round(e.y)} : null))} : null));
  if (HD.sel && HD.sel.on) HD.sel.on('change', () => { if (st.open && !st.busy) paint(); });
  if (HD.net && HD.net.on) HD.net.on('init', () => { wireStore(); scanMarks(1500); syncFab(); });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchMount); else watchMount();

  HD.ai = {open: open, close: close, ask: ask, settle: settle, state: st, presets: PRESETS};
})();
