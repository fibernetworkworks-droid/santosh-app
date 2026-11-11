/* HOOLA DESIGN - hd-branches.js (phase D9c "branches + merge": docs/HOOLA_DESIGN_PLAN.md section 8).
 *
 * A branch is a normal file linked to its main file (server: design/branches.py). This file adds, all through
 * HD.ui's extension points:
 *
 *   TOP BAR    on a main file a "Branches" button (with the open count); on a branch a "Branch of <main>" badge
 *              ("Merged into <main>" once merged) whose menu has Review & merge, Update from main, Open main.
 *   BRANCHES   a dialog: make a branch (a full copy of main as it is now - it opens at once), the list of every
 *              branch of this main with its state and last edit, open one.
 *   REVIEW     "Review & merge" (and "Update from main"): the server's three-way diff - every layer changed on
 *              this branch grouped by page, with BEFORE / AFTER pictures, and a card per CONFLICT with both values
 *              in plain words ("Fill: #FF8800 here, #2266FF on main") and a picture of each; she picks one per
 *              conflict and the Merge button wakes up only when every conflict is decided. A merge that finds
 *              main moved since the review re-reads it. After the merge: a toast and a bar with a link to main.
 *   FILES      a "Branch of <main>" tag on a branch's card in the file browser.
 *
 * The pictures of OTHER versions of the document (the base, main, this branch) are drawn the way the version
 * history previews a version: HD.net.hold() (nothing is sent, other people's ops wait, the store is locked), each
 * document is loaded into the store in turn and every needed layer is drawn with HD.render.toCanvas; then
 * HD.net.release() fetches the live document again. So the review can never change a file by itself.
 *
 * Every text from a document or a person is set with textContent; nothing here builds HTML from it.
 * HD.branches is the small surface the browser test drives. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const ui = HD.ui;
  if (!ui || !ui.h) return;
  const h = ui.h, icon = ui.icon, clear = ui.clear, enc = encodeURIComponent;
  const S = () => HD.store, R = () => HD.render, N = () => HD.net;
  const file = () => (HD.app && HD.app.file) || null;
  const canWrite = () => { const f = file(); return !!f && !f.share && f.role !== 'view' && N().role !== 'view'; };
  const api = (m, p, b) => ui.api(m, p, b);
  const NS = 'http://www.w3.org/2000/svg';
  const THUMB_W = 168, THUMB_H = 112, THUMB_MAX = 80;

  const B = {info: null, loadedFor: null, index: null, indexAt: 0, review: null, bar: null, busy: false, seq: 0};

  /* our own little drawing: two lines that part and meet (a branch) */
  function branchIcon(size) {
    const s = document.createElementNS(NS, 'svg'); s.setAttribute('viewBox', '0 0 16 16'); s.setAttribute('width', size || 16); s.setAttribute('height', size || 16);
    s.setAttribute('fill', 'none'); s.setAttribute('stroke', 'currentColor'); s.setAttribute('stroke-width', '1.4'); s.setAttribute('stroke-linecap', 'round'); s.setAttribute('aria-hidden', 'true'); s.setAttribute('class', 'hd-ic');
    for (const d of ['M4.5 3.2v9.6', 'M4.5 9.6c0-2.6 7-1.6 7-4.6']) { const p = document.createElementNS(NS, 'path'); p.setAttribute('d', d); s.appendChild(p); }
    for (const c of [[4.5, 3.2], [4.5, 12.8], [11.5, 4.4]]) { const e = document.createElementNS(NS, 'circle'); e.setAttribute('cx', c[0]); e.setAttribute('cy', c[1]); e.setAttribute('r', '1.5'); e.setAttribute('fill', 'var(--surface)'); s.appendChild(e); }
    return s;
  }
  function ago(iso) {
    const t = Date.parse(iso || ''); if (!t) return ''; const s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60) return 'just now'; if (s < 3600) { const m = Math.floor(s / 60); return m + (m === 1 ? ' minute ago' : ' minutes ago'); }
    if (s < 86400) { const x = Math.floor(s / 3600); return x + (x === 1 ? ' hour ago' : ' hours ago'); }
    try { return new Date(t).toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch (e) { return ''; }
  }
  function settle(msLimit) {
    return new Promise(resolve => { const t0 = Date.now(); (function wait() { if (!N().pending || N().pending() === 0) return resolve(true); if (Date.now() - t0 > msLimit) return resolve(false); setTimeout(wait, 60); })(); });
  }
  const isBranch = () => !!(B.info && B.info.is_branch && B.info.branch);
  const merged = () => isBranch() && B.info.branch.state === 'merged';
  const mainName = () => (B.info && B.info.main && B.info.main.name) || 'main';

  /* ---------------------------------------------------------------- what this file is */
  async function loadInfo() {
    const f = file(); if (!f || f.share) { B.info = null; return null; }
    const my = ++B.seq;
    try { const r = await api('GET', '/files/' + enc(f.id) + '/branches'); if (my !== B.seq || !file() || file().id !== f.id) return null; B.info = r; B.loadedFor = f.id; }
    catch (e) { if (my === B.seq) B.info = null; }
    drawTop(); return B.info;
  }

  /* ---------------------------------------------------------------- the top bar */
  function drawTop() {
    const st = ui.state, root = st && st.root; if (!root) return; const left = root.querySelector('.hd-top-l'); if (!left) return;
    let el = left.querySelector('.hd-br-top'); if (el) el.parentNode.removeChild(el);
    const f = file(); if (!f || f.share || !B.info) return;
    if (isBranch()) {
      const done = merged(), text = (done ? 'Merged into ' : 'Branch of ') + mainName();
      el = h('button', {class: 'hd-br-top hd-br-badge' + (done ? ' merged' : ''), type: 'button', title: text + ' – review, merge and more', 'aria-haspopup': 'menu'}, branchIcon(14), h('span', {class: 'hd-br-badge-t', text: text}), icon('down', 10));
      el.addEventListener('click', () => branchMenu(el));
    } else {
      const open = (B.info.branches || []).filter(b => b.state !== 'merged').length;
      el = h('button', {class: 'hd-br-top hd-br-btn', type: 'button', title: 'Branches of this file', 'aria-label': 'Branches' + (open ? ', ' + open + ' open' : '')}, branchIcon(14), h('span', {class: 'hd-btn-t', text: 'Branches'}), open ? h('span', {class: 'hd-br-count', text: String(open)}) : null);
      el.addEventListener('click', openBranches);
    }
    const role = left.querySelector('.hd-chip'), name = left.querySelector('.hd-fname');
    const after = role && role.parentNode === left ? role : name; if (after && after.nextSibling) left.insertBefore(el, after.nextSibling); else left.appendChild(el);
  }
  function branchMenu(anchor) {
    const live = !merged() && canWrite();
    ui.menu(anchor, [
      {label: 'Review & merge…', icon: 'check', disabled: !live, run: () => openReview('merge')},
      {label: 'Update from main…', icon: 'undo', disabled: !live, run: () => openReview('update')},
      '-', {label: 'Open ' + mainName(), icon: 'right', disabled: !(B.info && B.info.main), run: openMain},
      {label: 'All branches…', icon: 'history', run: openBranches}], {label: 'Branch'});
  }
  function openMain() { if (B.info && B.info.main) location.hash = '#/f/' + enc(B.info.main.id); }

  /* ---------------------------------------------------------------- the branches dialog */
  async function openBranches() {
    const f = file(); if (!f || f.share) return;
    if (!B.info || B.loadedFor !== f.id) await loadInfo();
    const info = B.info; if (!info) { ui.toast('The branches could not be loaded.', true); return; }
    const list = h('div', {class: 'hd-br-list', role: 'list', 'aria-label': 'Branches'}), main = info.main || {id: f.id, name: f.name};
    const draw = () => {
      clear(list); const rows = info.branches || [];
      if (!rows.length) list.appendChild(h('p', {class: 'hd-note pad', text: 'No branches yet. A branch is a copy of this file where you can try an idea, then merge it back into the main file.'}));
      for (const b of rows) {
        const here = b.id === f.id, done = b.state === 'merged';
        list.appendChild(h('div', {class: 'hd-br-row' + (here ? ' here' : ''), role: 'listitem', 'data-id': b.id},
          h('span', {class: 'hd-br-ric'}, branchIcon(15)),
          h('div', {class: 'hd-br-rmeta'}, h('span', {class: 'hd-br-rname', text: b.name || 'Branch'}), h('span', {class: 'hd-br-rwhen', text: (done ? 'Merged' : 'Edited') + ' ' + ago(b.updated_at)})),
          h('span', {class: 'hd-br-state' + (done ? ' merged' : ''), text: done ? 'Merged' : 'Open'}),
          here ? h('span', {class: 'hd-br-hereT', text: 'You are here'}) : h('a', {class: 'hd-btn', href: '#/f/' + enc(b.id), text: 'Open', on: {click: () => ui.closeModal()}})));
      }
    };
    const openCount = () => (info.branches || []).filter(b => b.state !== 'merged').length;
    let create = null;
    if (!info.is_branch && canWrite()) {
      const name = h('input', {class: 'hd-in', type: 'text', placeholder: 'Branch name, for example “Try a blue hero”', 'aria-label': 'Branch name', maxlength: '120'});
      const go = h('button', {class: 'hd-btn pri', type: 'button', text: 'Make a branch'});
      const make = async () => { go.disabled = true; try { await settle(3000); const b = await api('POST', '/files/' + enc(f.id) + '/branches', {name: name.value.trim()}); ui.closeModal(); B.index = null; ui.toast('Branch “' + b.name + '” made. It opens now.'); location.hash = '#/f/' + enc(b.id); }
        catch (e) { go.disabled = false; ui.toast(e.message || 'The branch could not be made.', true); } };
      go.addEventListener('click', make); name.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Enter') make(); });
      create = h('div', {class: 'hd-br-make'}, name, go);
      if (openCount() >= (info.max_open || 20)) { go.disabled = true; name.disabled = true; }
    }
    const note = info.is_branch ? 'Branches are made from the main file, “' + main.name + '”.' : !canWrite() ? 'This file is view only: you can see its branches, not make one.' : openCount() + ' of ' + (info.max_open || 20) + ' open branches. A new branch starts as this file is now.';
    ui.modal('hd-co-dialog hd-br-dialog', 'Branches', [
      h('div', {class: 'hd-co-dhead'}, h('h2', {text: 'Branches of “' + main.name + '”'}), h('button', {class: 'hd-ib', type: 'button', title: 'Close', 'aria-label': 'Close', on: {click: () => ui.closeModal()}}, icon('close'))),
      h('div', {class: 'hd-co-dbody'}, create, h('p', {class: 'hd-note', text: note}), list)]);
    draw(); const inp = create && create.querySelector('input'); if (inp && !inp.disabled) inp.focus();
  }

  /* ---------------------------------------------------------------- pictures of other documents */
  function snap(id) {
    try {
      const b = (R().exportBounds && R().exportBounds(id)) || S().worldBounds(id); if (!b || !(b.w > 0) || !(b.h > 0)) return null;
      const dpr = Math.min(2, window.devicePixelRatio || 1), scale = Math.min(THUMB_W / b.w, THUMB_H / b.h, 2) * dpr;
      const cv = R().toCanvas(id, scale, {}); if (!cv || cv.width < 2) return null; return cv.toDataURL('image/png');
    } catch (e) { return null; }
  }
  /* want: {base:[ids], ours:[ids], theirs:[ids]} -> {base:{id: url}, ...}. The live document comes back after. */
  async function drawDocs(docs, want) {
    const out = {base: {}, ours: {}, theirs: {}};
    if (N().held || !N().hold()) return out;                      /* a preview is on / edits on their way: no pictures, still a review */
    const root = ui.state && ui.state.root; if (root) root.classList.add('hd-br-busy');
    try {
      if (HD.sel && HD.sel.clear) HD.sel.clear();
      for (const side of ['base', 'theirs', 'ours']) {
        const ids = (want[side] || []).slice(0, THUMB_MAX); if (!ids.length || !docs[side]) continue;
        S().load(docs[side], N().cid || 0);
        for (const id of ids) { if (!S().has(id)) continue; try { await R().ready(id, 1200); } catch (e) { /* draw what is there */ } const url = snap(id); if (url) out[side][id] = url; }
      }
    } finally { N().release(); if (root) root.classList.remove('hd-br-busy'); if (R().invalidate) R().invalidate(true); }
    return out;
  }

  /* ---------------------------------------------------------------- review + merge */
  async function openReview(mode) {
    const f = file(); if (!f || f.share || !isBranch()) return; if (merged()) { ui.toast('This branch was merged already.'); return; }
    if (!canWrite()) { ui.toast('This file is view only.'); return; }
    mode = mode === 'update' ? 'update' : 'merge';
    const body = h('div', {class: 'hd-br-rbody', 'aria-live': 'polite'}, h('div', {class: 'hd-br-wait', role: 'status'}, h('i'), h('span', {text: 'Preparing the review…'})));
    const foot = h('div', {class: 'hd-br-rfoot'});
    const title = mode === 'merge' ? 'Review & merge into “' + mainName() + '”' : 'Update from “' + mainName() + '”';
    ui.modal('hd-br-review', title, [h('div', {class: 'hd-br-rhead'}, h('span', {class: 'hd-br-ric'}, branchIcon(16)), h('div', {class: 'hd-br-rtitle'}, h('h2', {text: title}), h('span', {class: 'hd-br-rsub', text: mode === 'merge' ? 'What “' + f.name + '” changed goes into the main file, for everyone who has it open.' : 'What changed on main comes into this branch. Main is not touched.'})),
      h('button', {class: 'hd-ib', type: 'button', title: 'Close', 'aria-label': 'Close', on: {click: closeReview}}, icon('close'))), body, foot]);
    const rv = B.review = {mode: mode, body: body, foot: foot, res: {}, data: null, pics: null, file: f.id};
    await loadReview(rv);
  }
  function closeReview() { B.review = null; ui.closeModal(); }
  async function loadReview(rv) {
    try {
      await settle(4000);
      const d = await api('GET', '/files/' + enc(rv.file) + '/merge'); if (B.review !== rv) return;
      rv.data = d; drawReview(rv);
      const want = {base: [], ours: [], theirs: []}, add = (side, id) => { if (id && want[side].indexOf(id) < 0) want[side].push(id); };
      const rows = rv.mode === 'merge' ? d.changes.ours : d.changes.theirs, after = rv.mode === 'merge' ? 'ours' : 'theirs';
      for (const c of d.conflicts) { if (c.kind === 'deleted_main') { add('ours', c.node); add('base', c.node); } else if (c.kind === 'deleted_here') { add('theirs', c.node); add('base', c.node); } else { add('ours', c.node); add('theirs', c.node); } }
      for (const c of rows.slice(0, THUMB_MAX)) { if (c.kind !== 'added') add('base', c.node); if (c.kind !== 'removed') add(after, c.node); }
      const [base, main, mine] = await Promise.all([api('GET', '/files/' + enc(rv.file) + '/merge/base'), api('GET', '/files/' + enc(d.branch.main) + '/doc'), api('GET', '/files/' + enc(rv.file) + '/doc')]);
      if (B.review !== rv) return;
      rv.pics = await drawDocs({base: base.doc, theirs: main.doc, ours: mine.doc}, want);
      if (B.review === rv) drawReview(rv);
    } catch (e) { if (B.review !== rv) return; clear(rv.body).appendChild(h('div', {class: 'hd-herr', role: 'alert'}, h('p', {text: e.message || 'The review could not be made.'}), h('button', {class: 'hd-btn', type: 'button', text: 'Try again', on: {click: () => loadReview(rv)}}))); }
  }
  function pic(rv, side, id, alt) {
    const url = rv.pics && rv.pics[side] && rv.pics[side][id];
    if (url) return h('img', {class: 'hd-br-pic', src: url, alt: alt, draggable: 'false'});
    return h('span', {class: 'hd-br-pic none', 'aria-label': alt, role: 'img', text: rv.pics ? 'Not there' : ''});
  }
  function pair(rv, before, after) {
    return h('div', {class: 'hd-br-pair'}, h('figure', null, before[0], h('figcaption', {text: before[1]})), h('span', {class: 'hd-br-arrow', 'aria-hidden': 'true'}, icon('right', 12)), h('figure', null, after[0], h('figcaption', {text: after[1]})));
  }
  function drawReview(rv) {
    const d = rv.data, body = clear(rv.body), mode = rv.mode, merge = mode === 'merge';
    const rows = merge ? d.changes.ours : d.changes.theirs, other = merge ? d.changes.theirs : d.changes.ours, cnt = d.counts;
    const mine = merge ? cnt.ours : cnt.theirs, theirs = merge ? cnt.theirs : cnt.ours;
    const said = n => n + (n === 1 ? ' change' : ' changes');
    body.appendChild(h('p', {class: 'hd-br-sum'}, h('b', {text: said(mine.total)}), merge ? ' on this branch' : ' on main', ' · ', h('span', {text: said(theirs.total) + (merge ? ' on main since you branched' : ' on this branch')}), ' · ',
      h('span', {class: d.conflicts.length ? 'hd-br-bad' : '', text: d.conflicts.length + (d.conflicts.length === 1 ? ' conflict' : ' conflicts')})));
    if (!rows.length && !d.conflicts.length) body.appendChild(h('div', {class: 'hd-br-empty'}, h('h3', {text: merge ? 'Nothing to merge' : 'Already up to date'}), h('p', {text: merge ? 'This branch has no changes that main does not have.' : 'Main has no changes this branch does not have.'})));
    if (d.conflicts.length) {
      const sec = h('section', {class: 'hd-br-sec', 'aria-label': 'Conflicts'}, h('h3', null, 'Conflicts ', h('span', {class: 'hd-br-hint', text: 'Changed on both sides. Pick the one to keep.'})));
      for (const c of d.conflicts) sec.appendChild(conflictCard(rv, c));
      body.appendChild(sec);
    }
    if (rows.length) {
      const sec = h('section', {class: 'hd-br-sec', 'aria-label': 'Changed layers'}, h('h3', {text: merge ? 'Changed on this branch' : 'Changed on main'}));
      const pages = new Map(); for (const c of rows) { const k = c.page || ''; if (!pages.has(k)) pages.set(k, {name: c.page_name || 'Page', rows: []}); pages.get(k).rows.push(c); }
      const sideAfter = merge ? 'ours' : 'theirs';
      pages.forEach(pg => {
        sec.appendChild(h('h4', {class: 'hd-br-page', text: pg.name}));
        for (const c of pg.rows) {
          const what = c.kind === 'added' ? 'Added' + (c.inside > 1 ? ' (' + c.inside + ' layers)' : '') : c.kind === 'removed' ? 'Deleted' + (c.inside > 1 ? ' (' + c.inside + ' layers)' : '') : c.props.join(', ');
          sec.appendChild(h('div', {class: 'hd-br-chg' + (c.conflict ? ' hasc' : ''), 'data-node': c.node, 'data-kind': c.kind},
            h('div', {class: 'hd-br-cmeta'}, h('span', {class: 'hd-br-cname', text: c.name}), h('span', {class: 'hd-br-cpath', text: c.path}), h('span', {class: 'hd-br-ckind k-' + c.kind, text: what})),
            pair(rv, [c.kind === 'added' ? h('span', {class: 'hd-br-pic none', text: 'New'}) : pic(rv, 'base', c.node, 'Before'), 'Before'], [c.kind === 'removed' ? h('span', {class: 'hd-br-pic none', text: 'Deleted'}) : pic(rv, sideAfter, c.node, 'After'), 'After'])));
        }
      });
      if ((merge ? cnt.ours.total : cnt.theirs.total) > rows.length) sec.appendChild(h('p', {class: 'hd-note', text: 'And ' + ((merge ? cnt.ours.total : cnt.theirs.total) - rows.length) + ' more.'}));
      body.appendChild(sec);
    }
    if (other.length) {
      const det = h('details', {class: 'hd-br-other'}, h('summary', {text: merge ? 'On main since you branched (' + other.length + ') – these stay as they are' : 'On this branch (' + other.length + ') – these stay as they are'}));
      const ul = h('ul'); for (const c of other.slice(0, 200)) ul.appendChild(h('li', null, h('b', {text: c.name}), ' ', h('span', {text: c.kind === 'changed' ? c.props.join(', ') : c.kind === 'added' ? 'added' : 'deleted'})));
      det.appendChild(ul); body.appendChild(det);
    }
    drawFoot(rv);
  }
  function conflictCard(rv, c) {
    const choose = side => { rv.res[c.id] = side; card.querySelectorAll('.hd-br-opt').forEach(b => { const on = b.dataset.side === side; b.classList.toggle('on', on); b.setAttribute('aria-checked', String(on)); }); drawFoot(rv); };
    const shot = side => c.kind === 'deleted_main' && side === 'theirs' ? h('span', {class: 'hd-br-pic none', text: 'Deleted'}) : c.kind === 'deleted_here' && side === 'ours' ? h('span', {class: 'hd-br-pic none', text: 'Deleted'}) : pic(rv, side, c.node, side === 'ours' ? 'On this branch' : 'On main');
    const opt = (side, head, value) => h('button', {class: 'hd-br-opt' + (rv.res[c.id] === side ? ' on' : ''), type: 'button', role: 'radio', 'aria-checked': String(rv.res[c.id] === side), 'data-side': side, on: {click: () => choose(side)}},
      shot(side), h('span', {class: 'hd-br-ohead', text: head}), h('span', {class: 'hd-br-oval', text: value}));
    const kindText = {prop: c.label || 'Property', move: 'Place', order: 'Order', deleted_main: 'Deleted on main', deleted_here: 'Deleted here'}[c.kind] || 'Conflict';
    const card = h('div', {class: 'hd-br-conf', 'data-id': c.id, role: 'radiogroup', 'aria-label': c.text},
      h('div', {class: 'hd-br-cmeta'}, h('span', {class: 'hd-br-cname', text: c.name}), h('span', {class: 'hd-br-cpath', text: c.path}), h('span', {class: 'hd-br-ckind k-conflict', text: kindText})),
      h('p', {class: 'hd-br-ctext', text: c.text}),
      h('div', {class: 'hd-br-opts'}, opt('ours', 'Keep this branch’s', c.ours), opt('theirs', 'Keep main’s', c.theirs)));
    return card;
  }
  function drawFoot(rv) {
    const d = rv.data, foot = clear(rv.foot); if (!d) return; const merge = rv.mode === 'merge';
    const open = d.conflicts.filter(c => !rv.res[c.id]).length, rows = merge ? d.changes.ours : d.changes.theirs;
    const nothing = !rows.length && !d.conflicts.length;
    const go = h('button', {class: 'hd-btn pri big', type: 'button', disabled: open > 0 || nothing || rv.busy, text: rv.busy ? (merge ? 'Merging…' : 'Updating…') : merge ? 'Merge into “' + mainName() + '”' : 'Bring main’s changes in'});
    go.addEventListener('click', () => runMerge(rv));
    foot.appendChild(h('span', {class: 'hd-br-fnote', text: open ? open + (open === 1 ? ' conflict still needs a choice.' : ' conflicts still need a choice.') : merge ? 'A version of main is saved first (“Before merging ' + ((file() && file().name) || 'this branch') + '”), so this can be undone. The branch becomes read only.' : 'A version of this branch is saved first, so this can be undone.'}));
    foot.appendChild(h('button', {class: 'hd-btn big', type: 'button', text: 'Cancel', on: {click: closeReview}})); foot.appendChild(go);
  }
  async function runMerge(rv) {
    const d = rv.data; if (!d || rv.busy) return; rv.busy = true; drawFoot(rv);
    try {
      await settle(4000);
      const out = await api('POST', '/files/' + enc(rv.file) + '/' + (rv.mode === 'merge' ? 'merge' : 'update'), {resolutions: rv.res, main_seq: d.main_seq, branch_seq: d.branch_seq});
      if (B.review !== rv) return;
      closeReview(); B.index = null;
      if (rv.mode === 'merge') {
        ui.toast('Merged into “' + mainName() + '”. This branch is read only now.'); showDone();
      } else ui.toast('Main’s changes are in this branch now.');
      (out.notes || []).forEach(n => setTimeout(() => ui.toast(n.text), 4400));
      await loadInfo();
    } catch (e) {
      rv.busy = false; if (B.review !== rv) return;
      if (/changed since your review|kept changing/i.test(e.message || '')) { ui.toast('The file changed since the review, so it was read again. Check it once more.'); const keep = rv.res; rv.pics = null; await loadReview(rv); rv.res = keep; if (rv.data) drawReview(rv); return; }
      drawFoot(rv); ui.toast(e.message || 'The merge did not work.', true);
    }
  }
  function showDone() {
    hideDone(); const st = ui.state; if (!st || !st.stage || !B.info || !B.info.main) return; const main = B.info.main;
    B.bar = h('div', {class: 'hd-br-done', role: 'status'}, branchIcon(15), h('span', null, 'Merged into ', h('b', {text: main.name}), '. This branch is read only now.'),
      h('a', {class: 'hd-btn pri', href: '#/f/' + enc(main.id), text: 'Open “' + main.name + '”'}), h('button', {class: 'hd-ib', type: 'button', title: 'Close', 'aria-label': 'Close', on: {click: hideDone}}, icon('close')));
    st.stage.appendChild(B.bar);
  }
  function hideDone() { if (B.bar && B.bar.parentNode) B.bar.parentNode.removeChild(B.bar); B.bar = null; }

  /* ---------------------------------------------------------------- the file browser */
  let tagT = 0;
  async function tagCards() {
    tagT = 0; const cards = document.querySelectorAll('.hd-card[data-file]'); if (!cards.length || file() || !ui.token) return;
    if (!B.index || Date.now() - B.indexAt > 15000) { B.indexAt = Date.now(); try { const r = await api('GET', '/branches'); B.index = new Map((r.branches || []).map(b => [b.id, b])); } catch (e) { B.index = new Map(); } }
    document.querySelectorAll('.hd-card[data-file]').forEach(card => {
      const b = B.index.get(card.dataset.file), meta = card.querySelector('.hd-cmeta'), had = card.querySelector('.hd-br-tag'); if (had) had.parentNode.removeChild(had);
      if (!b || !meta) return; const done = b.state === 'merged';
      meta.insertBefore(h('span', {class: 'hd-br-tag' + (done ? ' merged' : '')}, branchIcon(12), h('span', {text: (done ? 'Merged into ' : 'Branch of ') + (b.main_name || 'a file')})), meta.lastChild);
    });
  }
  function watchHome() {
    const root = document.getElementById('hd-app') || document.body; if (!window.MutationObserver) return;
    new MutationObserver(muts => { if (file() || tagT) return; for (const m of muts) for (const n of m.addedNodes) if (n.nodeType === 1 && (n.matches('.hd-card') || n.querySelector('.hd-card'))) { tagT = setTimeout(tagCards, 30); return; } }).observe(root, {childList: true, subtree: true});
  }

  /* ---------------------------------------------------------------- wiring */
  function onOpen() { B.info = null; B.loadedFor = null; hideDone(); loadInfo(); }
  function onClose() { if (B.review) closeReview(); hideDone(); B.info = null; B.loadedFor = null; B.index = null; }
  (function init() { if (!HD.app || !HD.app.on) { setTimeout(init, 0); return; } HD.app.on('open', onOpen); HD.app.on('close', onClose); })();   /* hd-app.js loads after this file */
  if (N() && N().on) N().on('init', () => { if (file() && !file().share && B.loadedFor === file().id) loadInfo(); });   /* a merge turns this branch view only */
  ui.registerMenu('main', {label: 'Branches…', icon: 'history', run: () => openBranches()});
  ui.command({id: 'branches', label: 'Branches…', group: 'Other', when: () => !!file() && !file().share, run: () => openBranches()});
  ui.command({id: 'branches.review', label: 'Review & merge this branch…', group: 'Other', when: () => isBranch() && !merged() && canWrite(), run: () => openReview('merge')});
  ui.command({id: 'branches.update', label: 'Update this branch from main…', group: 'Other', when: () => isBranch() && !merged() && canWrite(), run: () => openReview('update')});
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchHome); else watchHome();

  HD.branches = {get info() { return B.info; }, get review() { return B.review; }, load: loadInfo, open: openBranches, openReview: openReview, close: closeReview,
    choose(id, side) { const rv = B.review; if (!rv) return false; const card = rv.body.querySelector('.hd-br-conf[data-id="' + (window.CSS && CSS.escape ? CSS.escape(id) : id) + '"]'); const b = card && card.querySelector('.hd-br-opt[data-side="' + side + '"]'); if (!b) return false; b.click(); return true; },
    tagCards: tagCards};
})();
