/* HOOLA DESIGN - hd-collab.js (phase D5 "together": docs/HOOLA_DESIGN_PLAN.md).
 *
 * Four things people do in one file together, all plugged in through HD.ui's extension points:
 *
 *   COMMENTS   the comment tool drops a pin (HD.ui.hook('comment')). A pin dropped on a layer remembers the layer
 *              and its place inside it (ox / oy in the layer's own box), so it follows the layer; a pin on the
 *              bare page keeps its page point. Threads with replies, edit / delete, resolve / reopen, a Comments
 *              tab on the left (open / resolved / mine, click to jump, unread dots), pins drawn by ONE canvas
 *              overlay in screen space (always the same size; pins that touch become one counted pin), live
 *              through the socket's `comment` frames. Shift+C hides the pins. A share-link guest reads only.
 *   VERSIONS   HD.ui.hook('versions'), Ctrl/Cmd+Alt+H (with three or more layers selected that key still
 *              distributes them, as before; Ctrl/Cmd+Alt+Shift+H is always the history). The History tab lists
 *              automatic + named versions by day. Selecting one shows it READ ONLY: HD.net.hold() first (nothing
 *              is sent, the ops of other people are not applied, the store is locked), then the version's
 *              document is loaded into the store; leaving is HD.net.release(), which fetches the live document
 *              again. So a preview can never change the file, and the live file can never leak into a preview.
 *   SHARE      HD.ui.hook('share'): make / copy / switch off the view-only link (#/s/<token>), copy a link to one
 *              layer (?node=<id>). The signed-out editor itself is booted by hd-app.js; this file adds its
 *              "View only" badge and the way in to sign in.
 *   PRESENCE   click a person to follow their view (their vp + canvas size from presence; any pan or zoom of
 *              your own stops it), "Spotlight me" asks the others to follow you, people quiet for a minute are
 *              dimmed, "/" opens cursor chat (80 characters, shown by your cursor to the others for 5 seconds).
 *
 * Every text that comes from a person (comment, name, version label, chat) is set with textContent or drawn on
 * the canvas; nothing here ever builds HTML from it. HD.collab is the small surface the browser test drives.
 */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const ui = HD.ui;
  if (!ui || !ui.h) return;
  const h = ui.h, icon = ui.icon, clear = ui.clear, enc = encodeURIComponent;
  const S = () => HD.store, R = () => HD.render, N = () => HD.net, T = () => HD.tools;
  const file = () => (HD.app && HD.app.file) || null;
  const isGuest = () => { const f = file(); return !!(f && f.share); };
  const canWrite = () => { const f = file(); return !!f && !f.share && f.role !== 'view' && N().role !== 'view'; };
  const myName = () => (N().me && N().me.name) || '';
  const MOD = /Mac|iPhone|iPad/.test(navigator.platform || '') ? '⌘' : 'Ctrl';
  const PALETTE = ['#5B45E0', '#0FA958', '#E0457B', '#F2994A', '#2D9CDB', '#B347E6', '#00B5AD', '#C94343'];

  /* ---------------------------------------------------------------- small helpers */
  function api(method, path, body) { return ui.api(method, path, body); }
  async function sharedGet(path) {
    const f = file(); if (!f || !f.share) throw new Error('This is not a shared file.');
    const r = await HD.app.rawFetch('/api/design/shared/' + enc(f.share) + path, {credentials: 'omit', cache: 'no-store'});
    if (!r.ok) throw new Error(r.status === 429 ? 'Too many requests. Please wait a minute.' : 'The shared file did not answer.');
    return r.json();
  }
  function hashOf(s) { let v = 7; s = String(s || ''); for (let i = 0; i < s.length; i++) v = (v * 31 + s.charCodeAt(i)) >>> 0; return v; }
  function colorOf(name) {
    let found = null; const users = N().users;
    if (users && users.forEach) users.forEach(u => { if (!found && u && u.name === name && u.color) found = u.color; });
    if (!found && N().me && N().me.name === name && N().me.color) found = N().me.color;
    return found || PALETTE[hashOf(name) % PALETTE.length];
  }
  function initial(name) { const t = String(name || '').trim(); return t ? t.charAt(0).toUpperCase() : '?'; }
  function ms(iso) { const t = Date.parse(iso || ''); return isFinite(t) ? t : 0; }
  function ago(iso) {
    const t = ms(iso); if (!t) return ''; const s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60) return 'just now'; if (s < 3600) return Math.floor(s / 60) + ' min ago'; if (s < 86400) { const hr = Math.floor(s / 3600); return hr + (hr === 1 ? ' hour ago' : ' hours ago'); }
    if (s < 172800) return 'yesterday'; if (s < 86400 * 7) return Math.floor(s / 86400) + ' days ago';
    try { return new Date(t).toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch (e) { return ''; }
  }
  function dayLabel(iso) {
    const t = ms(iso); if (!t) return 'Earlier'; const d = new Date(t), n = new Date(), same = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
    if (same(d, n)) return 'Today'; const y = new Date(n.getTime() - 86400000); if (same(d, y)) return 'Yesterday';
    try { return d.toLocaleDateString(undefined, {weekday: 'short', day: 'numeric', month: 'short', year: d.getFullYear() === n.getFullYear() ? undefined : 'numeric'}); } catch (e) { return 'Earlier'; }
  }
  function clock(iso) { const t = ms(iso); if (!t) return ''; try { return new Date(t).toLocaleTimeString(undefined, {hour: 'numeric', minute: '2-digit'}); } catch (e) { return ''; } }
  function whenText(iso) { const day = dayLabel(iso); return (day === 'Today' ? '' : day + ', ') + clock(iso); }
  let cssCache = null;
  function css(name) {
    if (!cssCache) { cssCache = {}; }
    if (cssCache[name] === undefined) { let v = ''; try { v = getComputedStyle(document.documentElement).getPropertyValue(name).trim(); } catch (e) { v = ''; } cssCache[name] = v; }
    return cssCache[name];
  }
  function copyText(text, okMsg) {
    const done = () => ui.toast(okMsg || 'Copied.');
    const old = () => { const ta = h('textarea', {class: 'hd-co-offscreen', 'aria-hidden': 'true', tabIndex: -1}); ta.value = text; document.body.appendChild(ta); ta.select(); let ok = false; try { ok = document.execCommand('copy'); } catch (e) { ok = false; } document.body.removeChild(ta); if (ok) done(); else ui.toast('Copy it by hand: ' + text, true); };
    try { if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(text).then(done, old); return; } } catch (e) { /* the old way below */ }
    old();
  }
  function avatar(name, cls) { return h('span', {class: 'hd-co-av' + (cls ? ' ' + cls : ''), 'aria-hidden': 'true', style: {backgroundColor: colorOf(name)}, text: initial(name)}); }
  function canvasBox() { const c = T().canvas; return c ? c.getBoundingClientRect() : {left: 0, top: 0, width: 0, height: 0}; }
  function redraw() { if (R() && R().invalidate) R().invalidate(); }
  function leftTab(id) { const st = ui.state; if (!st) return; st.leftTab = id; st.sig = ''; st.customSig = ''; if (st.leftTabs) st.leftTabs.dataset.sig = ''; ui.refresh(); }

  /* ================================================================ comments */
  const C = {byId: new Map(), threads: [], rev: 0, loadedFor: null, hidden: false, filter: 'open', openId: null, draft: null, pop: null, hits: [], seen: {}, mine: new Set(), panelSig: '', hover: false, reply: ''};
  const SEEN_KEY = id => 'hoola.design.seen.' + id;
  function seenLoad(id) { C.seen = {}; C.firstVisit = true; try { const raw = localStorage.getItem(SEEN_KEY(id)); if (raw !== null) { C.firstVisit = false; const v = JSON.parse(raw); if (v && typeof v === 'object') C.seen = v; } } catch (e) { /* private window: unread lasts for this visit */ } }
  function seenSave() { const f = file(); if (!f) return; try { const keep = {}; for (const t of C.threads) if (C.seen[t.id]) keep[t.id] = C.seen[t.id]; localStorage.setItem(SEEN_KEY(f.id), JSON.stringify(keep)); } catch (e) { /* not kept */ } }
  function markSeen(t) { if (!t) return; if ((C.seen[t.id] || '') >= t.last) return; C.seen[t.id] = t.last; seenSave(); C.rev++; panelDirty(); redraw(); }
  function unread(t) { return t.last > (C.seen[t.id] || ''); }
  function rebuild() {
    const heads = [], kids = new Map();
    C.byId.forEach(c => { if (c.parent) { if (!kids.has(c.parent)) kids.set(c.parent, []); kids.get(c.parent).push(c); } else heads.push(c); });
    const byTime = (a, b) => (a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : a.id < b.id ? -1 : 1);
    heads.sort(byTime);
    C.threads = heads.map(head => { const replies = (kids.get(head.id) || []).sort(byTime); let last = head.created_at || '';
      for (const r of replies) if ((r.created_at || '') > last) last = r.created_at; return {id: head.id, head: head, replies: replies, last: last}; });
    C.rev++; panelDirty(); redraw();
  }
  function thread(id) { return C.threads.find(t => t.id === id) || null; }
  async function loadComments() {
    const f = file(); if (!f) return; const fid = f.id;
    try { const r = f.share ? await sharedGet('/comments') : await api('GET', '/files/' + enc(fid) + '/comments');
      if (!file() || file().id !== fid) return; C.byId = new Map(); for (const c of (r && r.comments) || []) if (c && c.id) C.byId.set(c.id, c);
      rebuild(); if (C.firstVisit) { C.firstVisit = false; for (const t of C.threads) C.seen[t.id] = t.last; seenSave(); C.rev++; panelDirty(); redraw(); }
      C.loadedFor = fid; refreshPop(); }
    catch (e) { /* comments are an extra: the file still opens */ }
  }
  function onCommentFrame(msg) {
    const c = msg && msg.comment; if (!c || !c.id || !file() || (c.file && c.file !== file().id)) return;
    if (msg.action === 'delete') { C.byId.delete(c.id); C.byId.forEach((x, id) => { if (x.parent === c.id) C.byId.delete(id); }); }
    else C.byId.set(c.id, Object.assign({}, C.byId.get(c.id), c));
    rebuild();
    const root = c.parent || c.id, t = thread(root);
    if (t && (C.mine.has(c.id) || C.openId === root)) { C.mine.delete(c.id); if ((C.seen[t.id] || '') < t.last) { C.seen[t.id] = t.last; seenSave(); C.rev++; panelDirty(); } }
    if (C.openId && !thread(C.openId)) closePop(); else refreshPop();
  }

  /* where a pin is: [world x, world y, page id] */
  function pinPlace(c) {
    const st = S();
    if (c.node && st.has(c.node) && typeof c.ox === 'number' && typeof c.oy === 'number') {
      const n = st.get(c.node);
      if (n && n.type !== 'PAGE' && n.type !== 'DOCUMENT') { const p = HD.math.apply(st.worldMatrix(c.node), c.ox, c.oy); return [p[0], p[1], st.pageOf(c.node) || c.page]; }
    }
    return [c.x, c.y, c.page];
  }
  function anchorFor(p) {     /* a click of the comment tool -> what the server keeps */
    const st = S(), out = {x: p.x, y: p.y, page: p.page || HD.sel.page, node: null};
    const n = p.node && st.has(p.node) ? st.get(p.node) : null;
    if (n && n.type !== 'PAGE' && n.type !== 'DOCUMENT') { try { const q = HD.math.apply(HD.math.inv(st.worldMatrix(p.node)), p.x, p.y); if (isFinite(q[0]) && isFinite(q[1])) { out.node = p.node; out.ox = Math.round(q[0] * 100) / 100; out.oy = Math.round(q[1] * 100) / 100; } } catch (e) { /* a flat layer: a page pin */ } }
    return out;
  }
  function shownOnCanvas(t) { return !t.head.resolved || C.filter === 'resolved' || C.openId === t.id; }

  /* ---- the pins: one overlay, screen space ---- */
  const PIN_R = 13, JOIN = 27;
  function pinPath(ctx, x, y, r) {         /* a round badge whose bottom-left corner is the exact point */
    const cx = x + r, cy = y - r; ctx.beginPath(); ctx.moveTo(x, y - 3); ctx.lineTo(x, cy); ctx.arc(cx, cy, r, Math.PI, 0.5 * Math.PI); ctx.lineTo(x + 3, y); ctx.quadraticCurveTo(x, y, x, y - 3); ctx.closePath();
  }
  function drawPins(ctx) {
    C.hits = [];
    if (!file() || !R() || !T().canvas) return;
    drawChats(ctx);
    if (C.hidden) return;
    const page = HD.sel.page, cv = T().canvas, W = cv.clientWidth, H = cv.clientHeight, pins = [];
    for (const t of C.threads) { if (!shownOnCanvas(t)) continue; const pl = pinPlace(t.head); if (pl[2] !== page) continue; const s = R().worldToScreen(pl[0], pl[1]);
      if (s[0] < -40 || s[1] < -10 || s[0] > W + 10 || s[1] > H + 40) continue; pins.push({t: t, x: s[0], y: s[1]}); }
    const groups = [];
    for (const p of pins) { let g = null; for (const q of groups) if (Math.abs(q.x - p.x) < JOIN && Math.abs(q.y - p.y) < JOIN) { g = q; break; }
      if (g) { g.items.push(p); g.x = (g.x * (g.items.length - 1) + p.x) / g.items.length; g.y = (g.y * (g.items.length - 1) + p.y) / g.items.length; } else groups.push({x: p.x, y: p.y, items: [p]}); }
    const surf = css('--surface') || '#FFFFFF', pri = css('--pri') || '#5B45E0', dim = css('--dim') || '#8B8B92', hair = css('--hair2') || '#DCDCD8';
    ctx.save(); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.lineJoin = 'round';
    for (const g of groups) {
      const x = Math.round(g.x), y = Math.round(g.y), cx = x + PIN_R, cy = y - PIN_R, many = g.items.length > 1, first = g.items[0].t, open = !many && C.openId === first.id, fresh = g.items.some(p => unread(p.t));
      ctx.shadowColor = 'rgba(0,0,0,0.28)'; ctx.shadowBlur = 8; ctx.shadowOffsetY = 2;
      pinPath(ctx, x, y, PIN_R); ctx.fillStyle = open ? pri : surf; ctx.fill();
      ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0; ctx.lineWidth = 1; ctx.strokeStyle = open ? pri : hair; ctx.stroke();
      ctx.beginPath(); ctx.arc(cx, cy, PIN_R - 3, 0, Math.PI * 2);
      if (many) { ctx.fillStyle = pri; ctx.fill(); ctx.fillStyle = '#FFFFFF'; ctx.font = '600 12px "Schibsted Grotesk", system-ui, sans-serif'; ctx.fillText(g.items.length > 99 ? '99+' : String(g.items.length), cx, cy + 0.5); }
      else if (first.head.resolved) { ctx.fillStyle = dim; ctx.fill(); ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 1.8; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(cx - 4, cy + 0.5); ctx.lineTo(cx - 1, cy + 3.5); ctx.lineTo(cx + 4.5, cy - 3); ctx.stroke(); }
      else { ctx.fillStyle = colorOf(first.head.author); ctx.fill(); ctx.fillStyle = '#FFFFFF'; ctx.font = '600 12px "Schibsted Grotesk", system-ui, sans-serif'; ctx.fillText(initial(first.head.author), cx, cy + 0.5); }
      if (fresh) { ctx.beginPath(); ctx.arc(cx + PIN_R - 3, cy - PIN_R + 3, 4.5, 0, Math.PI * 2); ctx.fillStyle = css('--saf') || '#EE8F35'; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = surf; ctx.stroke(); }
      C.hits.push({x: cx, y: cy, r: PIN_R + 3, ids: g.items.map(p => p.t.id), tip: [x, y]});
    }
    if (C.draft && C.draft.page === page) { const s = R().worldToScreen(C.draft.x, C.draft.y), x = Math.round(s[0]), y = Math.round(s[1]);
      pinPath(ctx, x, y, PIN_R); ctx.fillStyle = pri; ctx.fill(); ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 1.8; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(x + PIN_R - 4.5, y - PIN_R); ctx.lineTo(x + PIN_R + 4.5, y - PIN_R); ctx.moveTo(x + PIN_R, y - PIN_R - 4.5); ctx.lineTo(x + PIN_R, y - PIN_R + 4.5); ctx.stroke(); }
    ctx.restore();
  }
  function hitAt(sx, sy) { for (let i = C.hits.length - 1; i >= 0; i--) { const q = C.hits[i]; if (Math.hypot(q.x - sx, q.y - sy) <= q.r) return q; } return null; }
  function pinClient(t) { const pl = pinPlace(t.head), s = R().worldToScreen(pl[0], pl[1]), b = canvasBox(); return [b.left + s[0], b.top + s[1]]; }

  /* ---- text with @mentions: plain text nodes and spans, never HTML ---- */
  function knownNames() { const set = new Set(); const users = N().users; if (users && users.forEach) users.forEach(u => { if (u && u.name) set.add(u.name); }); if (myName()) set.add(myName()); C.byId.forEach(c => { if (c.author) set.add(c.author); }); return Array.from(set).sort((a, b) => b.length - a.length); }
  function textNodes(text) {
    const out = [], names = knownNames(), low = String(text).toLowerCase(); let i = 0, from = 0; text = String(text);
    while (i < text.length) {
      if (text.charAt(i) === '@' && (i === 0 || /[\s(\[{,;:]/.test(text.charAt(i - 1)))) {
        let hit = ''; for (const n of names) { if (low.substr(i + 1, n.length) === n.toLowerCase() && !/[A-Za-z0-9_]/.test(text.charAt(i + 1 + n.length) || ' ')) { hit = text.substr(i, n.length + 1); break; } }
        if (hit) { if (i > from) out.push(document.createTextNode(text.slice(from, i))); out.push(h('span', {class: 'hd-co-at', text: hit})); i += hit.length; from = i; continue; }
      }
      i++;
    }
    if (from < text.length) out.push(document.createTextNode(text.slice(from)));
    return out;
  }
  function peopleNow() { const set = new Set(); const users = N().users; if (users && users.forEach) users.forEach(u => { if (u && u.name && u.name !== 'Guest') set.add(u.name); }); if (myName()) set.add(myName()); return Array.from(set); }

  /* ---- the writing box (a new comment, a reply, an edit) ---- */
  function writer(o) {
    const ta = h('textarea', {class: 'hd-co-ta', rows: o.rows || 2, placeholder: o.placeholder || 'Write a comment', 'aria-label': o.label || 'Comment', maxlength: '4000', autofocus: o.focus ? true : null});
    ta.value = o.value || '';
    const send = h('button', {class: 'hd-btn pri hd-co-send', type: 'button', title: o.sendTitle || ('Send  (' + MOD + '+Enter)'), text: o.sendText || 'Send'});
    const cancel = o.cancel ? h('button', {class: 'hd-btn', type: 'button', text: 'Cancel', on: {click: o.cancel}}) : null;
    const ats = h('div', {class: 'hd-co-ats', role: 'listbox', 'aria-label': 'People in this file', hidden: true});
    const hint = h('span', {class: 'hd-co-hint', text: '@ to mention · ' + MOD + '+Enter to send'});
    let at = null, cur = 0, busy = false;
    function sync() { send.disabled = busy || !ta.value.trim(); ta.style.height = 'auto'; ta.style.height = Math.min(160, Math.max(o.rows === 1 ? 34 : 56, ta.scrollHeight + 2)) + 'px'; if (o.onText) o.onText(ta.value); }
    function mention() {
      const upto = ta.value.slice(0, ta.selectionStart || 0), m = /(^|[\s(\[{,;:])@([^\s@]{0,30})$/.exec(upto);
      if (!m) { at = null; ats.hidden = true; return; }
      const q = m[2].toLowerCase(), list = peopleNow().filter(n => n.toLowerCase().indexOf(q) === 0 || n.toLowerCase().indexOf(' ' + q) >= 0).slice(0, 6);
      if (!list.length) { at = null; ats.hidden = true; return; }
      at = {start: upto.length - m[2].length - 1, list: list}; cur = Math.min(cur, list.length - 1); clear(ats);
      list.forEach((n, i) => ats.appendChild(h('button', {class: 'hd-co-atb' + (i === cur ? ' cur' : ''), type: 'button', role: 'option', 'aria-selected': String(i === cur), tabIndex: -1, on: {pointerdown: ev => { ev.preventDefault(); pick(n); }}}, avatar(n, 'sm'), h('span', {text: n}))));
      ats.hidden = false;
    }
    function pick(name) { if (!at) return; const end = ta.selectionStart || 0, v = ta.value; ta.value = v.slice(0, at.start) + '@' + name + ' ' + v.slice(end); const pos = at.start + name.length + 2; ta.setSelectionRange(pos, pos); at = null; ats.hidden = true; ta.focus(); sync(); }
    async function go() {
      const text = ta.value.trim(); if (!text || busy) return; busy = true; sync();
      try { await o.send(text); ta.value = ''; } catch (e) { ui.toast(e.message || 'The comment could not be saved.', true); }
      busy = false; if (document.contains(ta)) sync();
    }
    ta.addEventListener('input', () => { cur = 0; sync(); mention(); });
    ta.addEventListener('click', mention);
    ta.addEventListener('keydown', ev => {
      if (at && !ats.hidden) {
        if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') { ev.preventDefault(); ev.stopPropagation(); cur = (cur + (ev.key === 'ArrowDown' ? 1 : at.list.length - 1)) % at.list.length; mention(); return; }
        if (ev.key === 'Enter' || ev.key === 'Tab') { if (!(ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); ev.stopPropagation(); pick(at.list[cur]); return; } }
        if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); at = null; ats.hidden = true; return; }
      }
      if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); ev.stopPropagation(); go(); return; }
      if (ev.key !== 'Escape') ev.stopPropagation();          /* typing never reaches the editor's shortcuts */
    });
    send.addEventListener('click', go);
    const el = h('div', {class: 'hd-co-writer'}, ta, ats, h('div', {class: 'hd-co-wfoot'}, hint, cancel, send));
    setTimeout(sync, 0);
    return {el: el, ta: ta, focus() { ta.focus(); }};
  }

  /* ---- a thread, in a popover by its pin ---- */
  function closePop() { const p = C.pop; if (p && p.handle) p.handle.close(); }
  function refreshPop() { const p = C.pop; if (!p || !p.id || !document.contains(p.box)) return; const t = thread(p.id); if (!t) { closePop(); return; } const had = p.ta && document.activeElement === p.ta; paintThread(p, t); if (had && p.ta) p.ta.focus(); }
  function paintThread(p, t) {
    const head = t.head, write = canWrite() && !N().held; clear(p.box);
    const resolve = write ? h('button', {class: 'hd-ib' + (head.resolved ? ' on' : ''), type: 'button', title: head.resolved ? 'Reopen this thread' : 'Mark as resolved', 'aria-label': head.resolved ? 'Reopen this thread' : 'Mark as resolved', 'aria-pressed': String(!!head.resolved), on: {click: () => setResolved(t, !head.resolved)}}, icon('check')) : null;
    const closeB = h('button', {class: 'hd-ib', type: 'button', title: 'Close', 'aria-label': 'Close', on: {click: closePop}}, icon('close'));
    p.box.appendChild(h('div', {class: 'hd-co-thead'}, h('span', {class: 'hd-co-ttitle', text: 'Comment'}), head.resolved ? h('span', {class: 'hd-co-chip ok', text: 'Resolved'}) : null, h('span', {class: 'hd-grow1'}), resolve, closeB));
    const list = h('div', {class: 'hd-co-msgs'});
    for (const c of [head].concat(t.replies)) list.appendChild(message(p, t, c, write));
    p.box.appendChild(list);
    if (write) { const w = writer({rows: 1, placeholder: 'Reply', label: 'Reply', value: C.reply, onText: v => { C.reply = v; }, send: async text => { const made = await api('POST', '/files/' + enc(file().id) + '/comments', {text: text, parent: t.id, page: head.page, x: head.x, y: head.y}); C.reply = ''; if (made && made.id) { C.mine.add(made.id); onCommentFrame({action: 'add', comment: made}); } }});
      p.ta = w.ta; p.box.appendChild(w.el); }
    else { p.ta = null; p.box.appendChild(h('p', {class: 'hd-co-ro'}, isGuest() ? 'You are viewing a shared link. ' : N().held ? 'Go back to the current version to reply.' : 'This file is view only.', isGuest() ? h('a', {href: '/console/', text: 'Sign in to reply'}) : null)); }
    list.scrollTop = list.scrollHeight;
    if (p.handle) p.handle.place();
  }
  function message(p, t, c, write) {
    const body = h('div', {class: 'hd-co-text'}, textNodes(c.text || ''));
    const more = write ? h('button', {class: 'hd-ib sm hd-co-more', type: 'button', title: 'Edit or delete', 'aria-label': 'Edit or delete this comment', 'aria-haspopup': 'menu'}, icon('dots')) : null;
    const el = h('div', {class: 'hd-co-msg', 'data-id': c.id}, avatar(c.author), h('div', {class: 'hd-co-mbody'}, h('div', {class: 'hd-co-mhead'}, h('span', {class: 'hd-co-who', text: c.author || 'Someone'}), h('span', {class: 'hd-co-when', text: ago(c.created_at), title: whenText(c.created_at)}), h('span', {class: 'hd-grow1'}), more), body));
    if (more) more.addEventListener('click', () => ui.menu(more, [
      {label: 'Edit', icon: 'text', run: () => { const w = writer({rows: 2, value: c.text, focus: true, label: 'Edit the comment', sendText: 'Save', sendTitle: 'Save  (' + MOD + '+Enter)', cancel: () => refreshPop(),
        send: async text => { const up = await api('PATCH', '/comments/' + enc(c.id), {text: text}); if (up && up.id) onCommentFrame({action: 'update', comment: up}); else refreshPop(); }});
        body.parentNode.replaceChild(w.el, body); w.focus(); if (p.handle) p.handle.place(); }},
      {label: c.parent ? 'Delete' : 'Delete the thread', icon: 'trash', danger: true, run: async () => { if (!c.parent && t.replies.length && !window.confirm('Delete this comment and its ' + t.replies.length + (t.replies.length === 1 ? ' reply?' : ' replies?'))) return;
        try { await api('DELETE', '/comments/' + enc(c.id)); onCommentFrame({action: 'delete', comment: {id: c.id, file: c.file}}); } catch (e) { ui.toast(e.message || 'It could not be deleted.', true); } }}
    ], {level: 1, label: 'Comment'}));
    return el;
  }
  async function setResolved(t, on) { try { const up = await api('PATCH', '/comments/' + enc(t.id), {resolved: on}); if (up && up.id) onCommentFrame({action: 'update', comment: up}); if (on) ui.toast('Resolved. Find it again under Resolved in the Comments tab.'); } catch (e) { ui.toast(e.message || 'That did not work.', true); } }
  function openThread(id) {
    const t = thread(id); if (!t || !ui.mounted) return false; const at = pinClient(t), anchor = {x: at[0] + 2 * PIN_R + 8, y: at[1] - 2 * PIN_R - 4};
    const box = h('div', {class: 'hd-co-thread'}), p = {id: id, box: box, anchor: anchor, ta: null, handle: null}; C.reply = '';
    p.handle = ui.pop(anchor, box, {cls: 'hd-co-pop', label: 'Comment thread', noFocus: true, onClose: () => { if (C.pop === p) { C.pop = null; C.openId = null; redraw(); panelDirty(); } }});
    C.pop = p; C.openId = id; paintThread(p, t); markSeen(t); redraw(); panelDirty();
    const focus = () => { if (C.pop !== p) return; if (p.ta) p.ta.focus({preventScroll: true}); else p.handle.el.focus({preventScroll: true}); };
    focus(); setTimeout(focus, 0);
    return true;
  }
  function followPop() {                 /* the canvas moved under an open thread / draft: the popover goes with its pin */
    const p = C.pop; if (!p || !p.handle || !document.contains(p.box)) return; let at = null;
    if (p.id) { const t = thread(p.id); if (t) at = pinClient(t); } else if (C.draft) { const s = R().worldToScreen(C.draft.x, C.draft.y), b = canvasBox(); at = [b.left + s[0], b.top + s[1]]; }
    if (!at) return; p.anchor.x = at[0] + 2 * PIN_R + 8; p.anchor.y = at[1] - 2 * PIN_R - 4; p.handle.place();
  }
  function startDraft(p) {
    if (isGuest()) { ui.toast('Comments are read only on a shared link. Sign in to add one.'); return; }
    if (N().held) { ui.toast('Go back to the current version to comment.'); return; }
    if (!canWrite()) { ui.toast('This file is view only.'); return; }
    const a = anchorFor(p), b = canvasBox(), anchor = {x: b.left + p.sx + 2 * PIN_R + 8, y: b.top + p.sy - 2 * PIN_R - 4};
    const box = h('div', {class: 'hd-co-thread new'}), st = {id: null, box: box, anchor: anchor, ta: null, handle: null};
    const w = writer({rows: 2, focus: true, placeholder: 'Add a comment', label: 'New comment', cancel: () => { if (C.pop === st) closePop(); },
      send: async text => { const made = await api('POST', '/files/' + enc(file().id) + '/comments', Object.assign({text: text}, a)); if (made && made.id) { C.mine.add(made.id); onCommentFrame({action: 'add', comment: made}); } if (C.pop === st) closePop(); }});
    box.appendChild(w.el); st.ta = w.ta;
    st.handle = ui.pop(anchor, box, {cls: 'hd-co-pop', label: 'New comment', onClose: () => { if (C.pop === st) { C.pop = null; C.draft = null; redraw(); } }});
    C.pop = st; C.draft = a; C.openId = null; redraw(); w.focus();
    setTimeout(() => { if (C.pop === st && document.contains(w.ta)) w.focus(); }, 0);     /* the click that dropped the pin gives the focus to the canvas after us */
  }
  function jump(id) {
    const t = thread(id); if (!t) return; const pl = pinPlace(t.head);
    if (pl[2] && pl[2] !== HD.sel.page && S().has(pl[2])) ui.setPage(pl[2]);
    C.openId = id;                      /* a resolved pin is drawn while its thread is open */
    const cv = T().canvas, s = R().worldToScreen(pl[0], pl[1]);
    if (cv && (s[0] < 60 || s[1] < 80 || s[0] > cv.clientWidth - 360 || s[1] > cv.clientHeight - 120)) { const z = (R().view && R().view.zoom) || 1; R().setView(T().view.at(z, pl[0], pl[1], cv.clientWidth * 0.4, cv.clientHeight * 0.4), false); }
    if (R().flush) { try { R().flush(); } catch (e) { /* next frame */ } }
    openThread(id);
  }

  /* ---- the Comments tab ---- */
  function panelDirty() { C.panelSig = ''; if (ui.mounted && ui.state && ui.state.leftTab === 'comments') ui.refresh(); }
  function filtered() { const me = myName(); return C.threads.filter(t => C.filter === 'resolved' ? t.head.resolved : C.filter === 'mine' ? (!t.head.resolved && [t.head].concat(t.replies).some(c => c.author === me)) : !t.head.resolved).sort((a, b) => (a.last < b.last ? 1 : -1)); }
  function renderPanel(el) {
    const sig = [C.rev, C.filter, C.hidden, C.openId, HD.sel.page, isGuest(), file() && file().id].join('|');
    if (el.dataset.co === 'c' && C.panelSig === sig) return; C.panelSig = sig; el.dataset.co = 'c'; clear(el);
    const tabs = h('div', {class: 'hd-seg hd-co-filter', role: 'tablist', 'aria-label': 'Which comments'});
    const kinds = [['open', 'Open'], ['resolved', 'Resolved']]; if (!isGuest()) kinds.push(['mine', 'Mine']);
    for (const k of kinds) { const n = k[0] === 'open' ? C.threads.filter(t => !t.head.resolved).length : 0;
      tabs.appendChild(h('button', {class: 'hd-segb' + (C.filter === k[0] ? ' on' : ''), type: 'button', role: 'tab', 'aria-selected': String(C.filter === k[0]), text: k[1] + (n ? ' ' + n : ''), on: {click: () => { C.filter = k[0]; panelDirty(); redraw(); ui.refresh(); }}})); }
    const eye = h('button', {class: 'hd-ib' + (C.hidden ? '' : ' on'), type: 'button', title: (C.hidden ? 'Show' : 'Hide') + ' the pins on the canvas  (Shift+C)', 'aria-label': 'Show the pins on the canvas', 'aria-pressed': String(!C.hidden), on: {click: togglePins}}, icon(C.hidden ? 'eyeoff' : 'eye'));
    el.appendChild(h('div', {class: 'hd-co-phead'}, tabs, eye));
    const list = filtered(), box = h('div', {class: 'hd-co-list', role: 'list'});
    if (!list.length) {
      box.appendChild(h('div', {class: 'hd-co-empty'}, icon('comment', 22), h('p', {text: C.filter === 'resolved' ? 'Nothing is resolved yet.' : C.filter === 'mine' ? 'You have no open comments.' : 'No open comments.'}),
        isGuest() || C.filter !== 'open' ? null : h('p', {class: 'hd-note', text: 'Pick the comment tool (C) and click anywhere on the canvas.'})));
    }
    for (const t of list) {
      const c = t.head, pl = pinPlace(c), other = pl[2] && pl[2] !== HD.sel.page && S().has(pl[2]) ? S().get(pl[2]).name : '', layer = c.node && S().has(c.node) ? S().get(c.node).name : '';
      const meta = [t.replies.length ? t.replies.length + (t.replies.length === 1 ? ' reply' : ' replies') : '', layer ? 'on ' + layer : '', other].filter(Boolean).join(' · ');
      box.appendChild(h('button', {class: 'hd-co-row' + (C.openId === t.id ? ' on' : '') + (unread(t) ? ' unread' : ''), type: 'button', role: 'listitem', 'data-id': t.id, on: {click: () => jump(t.id)}},
        avatar(c.author), h('span', {class: 'hd-co-rbody'}, h('span', {class: 'hd-co-rhead'}, h('span', {class: 'hd-co-who', text: c.author || 'Someone'}), h('span', {class: 'hd-co-when', text: ago(t.last)}), unread(t) ? h('i', {class: 'hd-co-dot', title: 'New'}) : null),
          h('span', {class: 'hd-co-rtext'}, textNodes(c.text || '')), meta ? h('span', {class: 'hd-co-rmeta', text: meta}) : null)));
    }
    el.appendChild(box);
  }
  function togglePins() { C.hidden = !C.hidden; if (C.hidden) closePop(); ui.toast(C.hidden ? 'Comment pins are hidden. Shift+C shows them again.' : 'Comment pins are shown.'); panelDirty(); redraw(); ui.refresh(); }

  /* ================================================================ version history */
  const V = {open: false, list: [], cur: null, busy: false, saving: false, sig: '', rev: 0, bar: null, loadedFor: null, err: ''};
  function vName(v) { return v.label || (v.auto ? 'Automatic save' : 'Saved version'); }
  function vDirty() { V.rev++; if (ui.mounted && ui.state && ui.state.leftTab === 'versions') ui.refresh(); }
  async function loadVersions() {
    const f = file(); if (!f || f.share) return; const fid = f.id;
    try { const r = await api('GET', '/files/' + enc(fid) + '/versions'); if (!file() || file().id !== fid) return; V.list = (r && r.versions) || []; V.err = ''; V.loadedFor = fid; }
    catch (e) { V.err = e.message || 'The versions could not be loaded.'; }
    vDirty();
  }
  function openVersions() {
    const f = file(); if (!f) return;
    if (f.share) { ui.toast('Sign in to see the version history of a file.'); return; }
    V.open = true; leftTab('versions'); loadVersions();
  }
  function closeVersions() { if (V.cur) exitPreview(); V.open = false; V.saving = false; leftTab('layers'); }
  function settle(msLimit) {              /* every edit of ours is with the server (or the time is up) */
    return new Promise(resolve => { const t0 = Date.now(); (function wait() { if (!N().pending || N().pending() === 0) return resolve(true); if (Date.now() - t0 > msLimit) return resolve(false); setTimeout(wait, 60); })(); });
  }
  async function preview(v) {
    if (V.busy || !file() || isGuest()) return; if (V.cur && V.cur.id === v.id) return;
    V.busy = true; vDirty();
    try {
      const d = await api('GET', '/versions/' + enc(v.id) + '/doc');
      if (!d || !d.doc || !d.doc.nodes) throw new Error('That version could not be read.');
      if (!N().held) {
        if (T().text && T().text.el) { try { T().text.commit(); } catch (e) { /* no text is open */ } }
        if (!(await settle(4000)) || !N().hold()) throw new Error(N().status === 'live' ? 'Your last changes are still being saved. Try again in a moment.' : 'You are offline. Version history needs the connection.');
      }
      ui.closePops(0); HD.sel.clear();
      S().load(d.doc, N().cid || 0);
      V.cur = v; showBar(); if (R().invalidate) R().invalidate(true); ui.refresh();
    } catch (e) { ui.toast(e.message || 'That version could not be shown.', true); }
    V.busy = false; vDirty();
  }
  function exitPreview() {
    if (!V.cur && !N().held) return; V.cur = null; hideBar();
    N().release(); if (R().invalidate) R().invalidate(true); vDirty(); ui.refresh();
  }
  function showBar() {
    hideBar(); const st = ui.state, v = V.cur; if (!st || !st.stage || !v) return;
    if (st.root) st.root.classList.add('hd-co-previewing');
    V.bar = h('div', {class: 'hd-co-vbar', role: 'status'}, icon('history'),
      h('span', {class: 'hd-co-vtext'}, 'Viewing ', h('b', {text: vName(v)}), h('span', {class: 'hd-co-vwhen', text: ' · ' + whenText(v.created_at)})),
      h('button', {class: 'hd-btn pri', type: 'button', text: 'Restore', on: {click: () => restore(v)}}),
      h('button', {class: 'hd-btn', type: 'button', text: 'Duplicate as new file', on: {click: () => duplicate(v)}}),
      h('button', {class: 'hd-btn', type: 'button', text: 'Back to current', on: {click: exitPreview}}));
    st.stage.appendChild(V.bar);
  }
  function hideBar() { if (V.bar && V.bar.parentNode) V.bar.parentNode.removeChild(V.bar); V.bar = null; const st = ui.state; if (st && st.root) st.root.classList.remove('hd-co-previewing'); }
  function restore(v) {
    const box = ui.modal('hd-co-dialog', 'Restore this version', [
      h('div', {class: 'hd-co-dhead'}, h('h2', {text: 'Restore “' + vName(v) + '”?'})),
      h('div', {class: 'hd-co-dbody'}, h('p', {text: 'The file goes back to how it was on ' + whenText(v.created_at) + ' for everyone who has it open.'}), h('p', {class: 'hd-note', text: 'What the file is now is saved as a version first (“Before restore”), so this can be undone from the same list.'})),
      h('div', {class: 'hd-co-dfoot'}, h('button', {class: 'hd-btn', type: 'button', text: 'Cancel', on: {click: () => ui.closeModal()}}), h('button', {class: 'hd-btn pri', type: 'button', autofocus: true, text: 'Restore', on: {click: async ev => {
        ev.currentTarget.disabled = true;
        try { await api('POST', '/versions/' + enc(v.id) + '/restore'); ui.closeModal(); if (N().held || V.cur) exitPreview(); ui.toast('Restored. The file as it was before is in the list as “Before restore”.'); loadVersions(); }
        catch (e) { ui.closeModal(); ui.toast(e.message || 'The version could not be restored.', true); } }}}))]);
    const b = box.querySelector('.hd-btn.pri'); if (b) b.focus();
  }
  async function duplicate(v) {
    try { const f = await api('POST', '/versions/' + enc(v.id) + '/duplicate', {}); if (!f || !f.id) throw new Error('The copy could not be made.');
      const url = location.pathname + '#/f/' + enc(f.id); V.lastCopy = f;
      const box = ui.modal('hd-co-dialog', 'A new file was made', [h('div', {class: 'hd-co-dhead'}, h('h2', {text: 'A new file was made'})),
        h('div', {class: 'hd-co-dbody'}, h('p', null, h('b', {text: f.name || 'Untitled'}), ' starts as this version. The file you are in was not changed.')),
        h('div', {class: 'hd-co-dfoot'}, h('button', {class: 'hd-btn', type: 'button', text: 'Stay here', on: {click: () => ui.closeModal()}}), h('a', {class: 'hd-btn pri', href: url, target: '_blank', rel: 'noopener', text: 'Open it in a new tab', on: {click: () => ui.closeModal()}}))]);
      const a = box.querySelector('a.hd-btn'); if (a) a.focus(); }
    catch (e) { ui.toast(e.message || 'The copy could not be made.', true); }
  }
  function renderVersions(el) {
    const sig = [V.rev, V.cur && V.cur.id, V.busy, V.saving, canWrite(), file() && file().id].join('|');
    if (el.dataset.co === 'v' && V.sig === sig) return; V.sig = sig; el.dataset.co = 'v'; clear(el);
    el.appendChild(h('div', {class: 'hd-co-phead'}, h('span', {class: 'hd-co-ptitle', text: 'Version history'}), h('span', {class: 'hd-grow1'}), h('button', {class: 'hd-ib', type: 'button', title: 'Close the history', 'aria-label': 'Close the history', on: {click: closeVersions}}, icon('close'))));
    if (canWrite() || N().held) {
      if (V.saving) {
        const name = h('input', {class: 'hd-in', type: 'text', placeholder: 'Name, for example “Before the client call”', 'aria-label': 'Version name', maxlength: '120', autofocus: true});
        const note = h('textarea', {class: 'hd-co-ta', rows: 2, placeholder: 'What changed (optional)', 'aria-label': 'What changed', maxlength: '1000'});
        const save = h('button', {class: 'hd-btn pri', type: 'button', text: 'Save'});
        const go = async () => { save.disabled = true; try { await settle(3000); await api('POST', '/files/' + enc(file().id) + '/versions', {label: name.value.trim(), note: note.value.trim()}); V.saving = false; ui.toast('Version saved.'); await loadVersions(); } catch (e) { save.disabled = false; ui.toast(e.message || 'The version could not be saved.', true); } };
        save.addEventListener('click', go);
        for (const f of [name, note]) f.addEventListener('keydown', ev => { if (ev.key === 'Enter' && (f === name || ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); go(); } if (ev.key !== 'Escape') ev.stopPropagation(); else { ev.stopPropagation(); V.saving = false; vDirty(); } });
        el.appendChild(h('div', {class: 'hd-co-vform'}, name, note, h('div', {class: 'hd-co-wfoot'}, h('span', {class: 'hd-grow1'}), h('button', {class: 'hd-btn', type: 'button', text: 'Cancel', on: {click: () => { V.saving = false; vDirty(); }}}), save)));
        setTimeout(() => { if (document.contains(name)) name.focus(); }, 0);
      } else el.appendChild(h('div', {class: 'hd-co-vact'}, h('button', {class: 'hd-btn hd-co-wide', type: 'button', disabled: !!N().held, title: N().held ? 'Go back to the current version first' : 'Keep the file as it is now, under a name', on: {click: () => { V.saving = true; vDirty(); }}}, icon('plus'), h('span', {text: 'Save a version'}))));
    }
    const list = h('div', {class: 'hd-co-vlist', role: 'list'});
    list.appendChild(h('button', {class: 'hd-co-vrow' + (!V.cur ? ' on' : ''), type: 'button', role: 'listitem', 'data-id': 'current', on: {click: () => { if (V.cur) exitPreview(); }}}, h('span', {class: 'hd-co-vdot live'}), h('span', {class: 'hd-co-vbody'}, h('span', {class: 'hd-co-vname', text: 'Current version'}), h('span', {class: 'hd-co-vmeta', text: 'What everyone is editing now'}))));
    let day = '';
    for (const v of V.list) {
      const d = dayLabel(v.created_at); if (d !== day) { day = d; list.appendChild(h('div', {class: 'hd-co-vday', text: d})); }
      const more = h('span', {class: 'hd-ib sm hd-co-vmore', role: 'button', tabIndex: 0, title: 'Restore or duplicate', 'aria-label': 'More for ' + vName(v), 'aria-haspopup': 'menu'}, icon('dots'));
      const row = h('button', {class: 'hd-co-vrow' + (V.cur && V.cur.id === v.id ? ' on' : '') + (v.auto ? ' auto' : ''), type: 'button', role: 'listitem', 'data-id': v.id, disabled: V.busy, on: {click: ev => { if (more.contains(ev.target)) return; preview(v); }}},
        h('span', {class: 'hd-co-vdot'}), h('span', {class: 'hd-co-vbody'}, h('span', {class: 'hd-co-vname', text: vName(v)}), h('span', {class: 'hd-co-vmeta', text: clock(v.created_at) + (v.by ? ' · ' + v.by : '')}), v.note ? h('span', {class: 'hd-co-vnote', text: v.note}) : null), more);
      const menu = ev => { ev.preventDefault(); ev.stopPropagation(); ui.menu(more, [{label: 'Show this version', icon: 'eye', run: () => preview(v)}, {label: 'Restore…', icon: 'undo', disabled: !canWrite() && !N().held, run: () => restore(v)}, {label: 'Duplicate as new file', icon: 'copy', run: () => duplicate(v)}], {label: 'Version'}); };
      more.addEventListener('click', menu); more.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') menu(ev); });
      list.appendChild(row);
    }
    if (!V.list.length) list.appendChild(h('p', {class: 'hd-note pad', text: V.err || (V.loadedFor === (file() && file().id) ? 'No saved versions yet. Hoola saves one by itself every 30 minutes of editing; you can also save one by name.' : 'Loading…')}));
    el.appendChild(list);
  }

  /* ================================================================ share */
  function selectedNode() { const ids = HD.sel.ids || []; return ids.length === 1 && S().has(ids[0]) ? ids[0] : null; }
  function copyNodeLink(id, token) { const n = S().get(id); copyText(HD.app.link(id, token), 'Link to “' + ((n && n.name) || 'this layer') + '” copied.'); }
  function shareDialog() {
    const f = file(); if (!f) return;
    const body = h('div', {class: 'hd-co-dbody'}), box = ui.modal('hd-co-dialog hd-co-share', 'Share this file', [
      h('div', {class: 'hd-co-dhead'}, h('h2', {text: 'Share “' + (f.name || 'Untitled') + '”'}), h('button', {class: 'hd-ib', type: 'button', title: 'Close', 'aria-label': 'Close', on: {click: () => ui.closeModal()}}, icon('close'))), body]);
    const node = selectedNode(), nodeName = node ? (S().get(node).name || 'this layer') : '';
    function linkRow(label, url, copyMsg, id) { const inp = h('input', {class: 'hd-in hd-co-url', type: 'text', readonly: true, value: url, 'aria-label': label, id: id || null}); inp.addEventListener('focus', () => inp.select());
      return h('div', {class: 'hd-co-linkrow'}, inp, h('button', {class: 'hd-btn', type: 'button', on: {click: () => copyText(url, copyMsg)}}, icon('copy'), h('span', {text: 'Copy'}))); }
    function paint(state) {
      clear(body);
      if (f.share) {                       /* a guest: the link they came in by */
        body.appendChild(h('p', {class: 'hd-co-lead', text: 'You are looking at this file through a view-only link.'}));
        body.appendChild(linkRow('View-only link', HD.app.link(null), 'Link copied.'));
        if (node) { body.appendChild(h('p', {class: 'hd-co-sub', text: 'Link to “' + nodeName + '”'})); body.appendChild(linkRow('Link to the selected layer', HD.app.link(node), 'Link copied.')); }
        body.appendChild(h('div', {class: 'hd-co-dfoot flat'}, h('a', {class: 'hd-btn pri', href: '/console/', text: 'Sign in to edit'})));
        return;
      }
      if (state.loading) { body.appendChild(h('p', {class: 'hd-note', text: 'Loading…'})); return; }
      const on = !!state.token;
      body.appendChild(h('div', {class: 'hd-co-sharehead'}, h('span', {class: 'hd-co-shareic' + (on ? ' on' : '')}, icon('link', 18)),
        h('div', {class: 'hd-co-sharetext'}, h('b', {text: on ? 'Anyone with the link can view' : 'Only you can open this file'}), h('span', {text: on ? 'No sign-in needed. They see changes and cursors live, and can inspect and export, but can not change anything.' : 'Make a view-only link to show it to someone who has no Hoola account.'}))));
      if (on) {
        body.appendChild(linkRow('View-only link', HD.app.link(null, state.token), 'View-only link copied.', 'hd-co-sharelink'));
        if (node) { body.appendChild(h('p', {class: 'hd-co-sub', text: 'View-only link straight to “' + nodeName + '”'})); body.appendChild(linkRow('View-only link to the selected layer', HD.app.link(node, state.token), 'Link copied.')); }
      }
      body.appendChild(h('div', {class: 'hd-co-dfoot flat'},
        on ? h('button', {class: 'hd-btn danger', type: 'button', text: 'Turn off the link', title: 'People using the link lose access right away', on: {click: () => set('none')}}) : h('button', {class: 'hd-btn pri', type: 'button', autofocus: true, on: {click: () => set('view')}}, icon('link'), h('span', {text: 'Create a view-only link'})),
        state.err ? h('span', {class: 'hd-co-err', role: 'alert', text: state.err}) : null));
      body.appendChild(h('div', {class: 'hd-co-sep'}));
      body.appendChild(h('p', {class: 'hd-co-sub', text: node ? 'Your own link to “' + nodeName + '” (needs your sign-in)' : 'Your own link to this file (needs your sign-in)'}));
      body.appendChild(linkRow('Your link', HD.app.link(node, null), 'Link copied.'));
      if (!node) body.appendChild(h('p', {class: 'hd-note', text: 'Select one frame or layer first to copy a link that opens on it.'}));
      const first = body.querySelector('[autofocus]') || body.querySelector('.hd-btn'); if (first) first.focus();
    }
    async function set(role) {
      try { const r = await api('POST', '/files/' + enc(f.id) + '/share', {role: role}); paint({token: r && r.token}); ui.toast(role === 'none' ? 'The link is off. Nobody can open it any more.' : 'The view-only link is ready.'); }
      catch (e) { paint({token: role === 'none' ? cur : null, err: e.message || 'That did not work.'}); }
    }
    let cur = null;
    if (f.share) { paint({}); return box; }
    paint({loading: true});
    api('GET', '/files/' + enc(f.id)).then(meta => { cur = meta && meta.share && meta.share.role === 'view' ? meta.share.token : null; if (document.contains(body)) paint({token: cur}); }, e => { if (document.contains(body)) paint({token: null, err: e.message || 'The sharing state could not be read.'}); });
    return box;
  }

  /* ================================================================ presence: follow, spotlight, idle, cursor chat */
  const IDLE_MS = 60000, CHAT_MS = 5000;
  const P = {ptr: null, vs: '', follow: null, frame: null, wait: null, applying: false, spots: new Map(), spotEl: null, chat: null, chatT: 0, presT: 0, idleT: 0, box: null, mo: null};
  function others() { const out = [], me = N().cid; const users = N().users; if (users && users.forEach) users.forEach((u, cid) => { if (u && cid !== me && u.cid !== me) out.push(u); }); return out; }
  function idle(cid) { const x = N().extra && N().extra.get(cid); return !!x && Date.now() - x.at > IDLE_MS; }
  function decorate() {
    const box = P.box; if (!box || !document.contains(box)) return; const list = others();
    box.querySelectorAll('button.hd-person').forEach((b, i) => { const u = list[i]; if (!u) return; const on = P.follow === u.cid, away = idle(u.cid), name = String(u.name || 'Guest');
      b.dataset.cid = String(u.cid); b.classList.toggle('hd-co-idle', away); b.classList.toggle('hd-co-on', on); b.setAttribute('aria-pressed', String(on));
      b.title = name + (away ? ' (away)' : '') + (on ? ' – you are following; click to stop' : ' – click to follow'); b.style.setProperty('--co', u.color || '#888888'); });
    const more = box.querySelector('.hd-person.more'); if (more) { more.setAttribute('role', 'button'); more.tabIndex = 0; more.title = 'Everyone in this file'; more.setAttribute('aria-label', 'Everyone in this file'); }
  }
  function peopleMenu(anchor) { ui.menu(anchor, others().map(u => ({label: String(u.name || 'Guest') + (idle(u.cid) ? ' (away)' : ''), checked: P.follow === u.cid ? true : undefined, icon: 'eye', run: () => toggleFollow(u.cid)})).concat(P.follow !== null ? ['-', {label: 'Stop following', run: () => stopFollow()}] : []), {label: 'People'}); }
  function toggleFollow(cid) { if (P.follow === cid) stopFollow(); else follow(cid); }
  function follow(cid) {
    const u = N().users.get(cid); if (!u) return false;
    P.follow = cid; P.wait = null; P.fname = String(u.name || 'Guest'); P.fcolor = u.color || '#5B45E0';
    if (!P.frame) { const st = ui.state; if (st && st.stage) { P.frame = h('div', {class: 'hd-co-follow'}, h('button', {class: 'hd-co-fchip', type: 'button', title: 'Stop following', on: {click: () => stopFollow()}}, h('span', {class: 'hd-co-fname'}), h('span', {class: 'hd-co-fstop', text: 'Stop'}))); st.stage.appendChild(P.frame); } }
    if (P.frame) { P.frame.style.setProperty('--co', P.fcolor); P.frame.querySelector('.hd-co-fname').textContent = 'Following ' + P.fname; }
    applyFollow(u, true); decorate(); return true;
  }
  function stopFollow(silent) { if (P.follow === null && !P.wait && !P.frame) return; P.follow = null; P.wait = null; if (P.frame && P.frame.parentNode) P.frame.parentNode.removeChild(P.frame); P.frame = null; decorate(); if (!silent && ui.mounted) ui.toast('You stopped following ' + (P.fname || 'them') + '.'); }
  function applyFollow(u, first) {
    const cv = T().canvas; if (!cv || !u) return; P.applying = true;
    try {
      if (u.page && u.page !== HD.sel.page && S().has(u.page)) ui.setPage(u.page);
      const x = N().extra && N().extra.get(u.cid), vp = u.vp, W = cv.clientWidth, H = cv.clientHeight;
      if (Array.isArray(vp) && vp.length >= 3 && isFinite(vp[0]) && isFinite(vp[1]) && vp[2] > 0) {
        const vs = x && Array.isArray(x.vs) && x.vs[0] > 0 && x.vs[1] > 0 ? x.vs : [W, H];
        const wx = (vs[0] / 2 - vp[0]) / vp[2], wy = (vs[1] / 2 - vp[1]) / vp[2], z = vp[2] * Math.min(W / vs[0], H / vs[1]);
        R().setView(T().view.at(z, wx, wy, W / 2, H / 2), first ? true : false);
      } else if (typeof u.x === 'number' && typeof u.y === 'number') R().setView(T().view.at((R().view && R().view.zoom) || 1, u.x, u.y, W / 2, H / 2), first ? true : false);
    } catch (e) { /* their view could not be read: stay where we are */ }
    P.applying = false;
  }
  function onPresence(ev) {
    if (!ev || !file()) return;
    if (ev.type === 'pres') {
      const x = N().extra && N().extra.get(ev.cid);
      if (P.follow === ev.cid) applyFollow(ev.user, false);
      if (x && x.spot && P.spots.get(ev.cid) !== x.spot) { P.spots.set(ev.cid, x.spot); askFollow(ev.user); }
      if (x && x.chat) { clearTimeout(P.chatT); P.chatT = setTimeout(redraw, CHAT_MS + 80); }
      if (x && x.chat !== undefined) redraw();
      const b = P.box && P.box.querySelector('button.hd-person[data-cid="' + ev.cid + '"]'); if (b && b.classList.contains('hd-co-idle')) decorate();
      return;
    }
    /* the person we follow went away. After a restored version everyone reconnects under a new number: wait 5 s
       for the same name to come back before giving up. */
    if ((ev.type === 'leave' && P.follow === ev.cid) || (ev.type === 'reset' && P.follow !== null && !N().users.has(P.follow))) {
      P.follow = null; P.wait = {name: P.fname, until: Date.now() + 5000};
      setTimeout(() => { if (P.wait && Date.now() >= P.wait.until) { const n = P.wait.name; P.wait = null; stopFollow(true); if (ui.mounted) ui.toast(n + ' left, so you are no longer following.'); } }, 5200); }
    if (P.wait && Date.now() < P.wait.until && (ev.type === 'join' || ev.type === 'reset')) { let back = null; N().users.forEach(u => { if (!back && u && u.name === P.wait.name) back = u; }); if (back) { follow(back.cid); return; } }
    if (ev.type === 'leave') { P.spots.delete(ev.cid); if (P.spotEl && P.spotEl.dataset.cid === String(ev.cid)) hideSpot(); }
    setTimeout(decorate, 0);
  }
  function hideSpot() { clearTimeout(P.spotT); if (P.spotEl && P.spotEl.parentNode) P.spotEl.parentNode.removeChild(P.spotEl); P.spotEl = null; }
  function askFollow(u) {
    if (!u || P.follow === u.cid || !ui.state || !ui.state.stage) return; hideSpot(); const name = String(u.name || 'Guest');
    P.spotEl = h('div', {class: 'hd-co-spot', role: 'status', 'data-cid': String(u.cid)}, avatar(name), h('span', {class: 'hd-co-spottext'}, h('b', {text: name}), ' would like you to follow them'),
      h('button', {class: 'hd-btn pri', type: 'button', text: 'Follow', on: {click: () => { hideSpot(); follow(u.cid); }}}), h('button', {class: 'hd-ib', type: 'button', title: 'Not now', 'aria-label': 'Not now', on: {click: hideSpot}}, icon('close')));
    ui.state.stage.appendChild(P.spotEl); P.spotT = setTimeout(hideSpot, 12000);
  }
  function spotlight() {
    if (!file() || N().status !== 'live') { ui.toast('You are offline: nobody can follow you right now.', true); return; }
    if (!others().length) { ui.toast('Nobody else is in this file right now.'); return; }
    sendView(); N().setPresence({spot: Date.now()}); clearTimeout(P.spotMine); P.spotMine = setTimeout(() => { if (N().setPresence) N().setPresence({spot: null}); }, 15000);
    ui.toast('Everyone here was asked to follow you.');
  }

  /* my own cursor + view go out when the VIEW changes too (the tools only send on a pointer move) */
  function ptrWorld() { const p = P.ptr, b = canvasBox(); if (!p || !b.width) return null; return R().screenToWorld(p[0] - b.left, p[1] - b.top); }
  function sendView() {
    const f = file(), cv = T().canvas; if (!f || !cv || N().status !== 'live') return; const v = R().view || {}, w = ptrWorld(), vs = cv.clientWidth + 'x' + cv.clientHeight;
    if (vs !== P.vs) { P.vs = vs; N().setPresence({vs: [cv.clientWidth, cv.clientHeight]}); }
    N().sendPresence({x: w ? Math.round(w[0] * 100) / 100 : undefined, y: w ? Math.round(w[1] * 100) / 100 : undefined, page: HD.sel.page, sel: (HD.sel.ids || []).slice(0, 200), vp: [v.x, v.y, v.zoom]});
  }
  function onView() { followPop(); placeChat(); if (P.presT) return; P.presT = setTimeout(() => { P.presT = 0; sendView(); }, 50); }

  /* cursor chat */
  function placeChat() { const c = P.chat; if (!c || !P.ptr) return; const w = c.el.offsetWidth || 180, x = Math.min(window.innerWidth - w - 8, P.ptr[0] + 16), y = Math.min(window.innerHeight - 44, P.ptr[1] + 20); c.el.style.left = Math.max(8, x) + 'px'; c.el.style.top = Math.max(8, y) + 'px'; }
  function endChat(now) { const c = P.chat; if (!c) return; clearTimeout(c.t); const done = () => { if (P.chat === c) P.chat = null; if (c.el.parentNode) c.el.parentNode.removeChild(c.el); if (N().setPresence) N().setPresence({chat: null}); if (T().canvas && ui.mounted) { try { T().canvas.focus({preventScroll: true}); } catch (e) { /* gone */ } } };
    if (now) done(); else { c.inp.readOnly = true; c.el.classList.add('sent'); c.inp.blur(); c.t = setTimeout(done, CHAT_MS); if (T().canvas) { try { T().canvas.focus({preventScroll: true}); } catch (e) { /* gone */ } } } }
  function startChat() {
    if (!file() || !ui.mounted) return; if (P.chat) { P.chat.inp.readOnly = false; P.chat.el.classList.remove('sent'); clearTimeout(P.chat.t); P.chat.inp.focus(); P.chat.inp.select(); return; }
    if (!P.ptr) { const b = canvasBox(); P.ptr = [b.left + b.width / 2, b.top + b.height / 2]; }
    const inp = h('input', {class: 'hd-co-chatin', type: 'text', maxlength: '80', placeholder: 'Say something…', 'aria-label': 'Cursor chat: shown by your cursor for 5 seconds', autocomplete: 'off', spellcheck: 'false'});
    const el = h('div', {class: 'hd-co-chat'}, inp), c = {el: el, inp: inp, t: 0}; P.chat = c;
    el.style.setProperty('--co', (N().me && N().me.color) || css('--pri') || '#5B45E0');
    document.body.appendChild(el); placeChat();
    inp.addEventListener('input', () => { const v = inp.value.slice(0, 80); inp.style.width = Math.max(120, Math.min(360, v.length * 8 + 30)) + 'px'; sendView(); N().setPresence({chat: v || null}); clearTimeout(c.t); c.t = setTimeout(() => endChat(true), CHAT_MS); placeChat(); });
    inp.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Enter') { ev.preventDefault(); if (inp.value.trim()) endChat(false); else endChat(true); } else if (ev.key === 'Escape') { ev.preventDefault(); endChat(true); } });
    inp.addEventListener('blur', () => { if (P.chat === c && !c.inp.readOnly) { if (inp.value.trim()) endChat(false); else endChat(true); } });
    inp.focus();
  }
  function drawChats(ctx) {
    const users = N().users, extra = N().extra; if (!users || !extra || !users.size) return; const now = Date.now(), page = HD.sel.page;
    users.forEach((u, cid) => { const x = extra.get(cid); if (!u || !x || !x.chat || now - x.chatAt > CHAT_MS || u.page !== page || typeof u.x !== 'number') return;
      /* shown for 5 s after its last change, whatever the sender's clock says */
      const s = R().worldToScreen(u.x, u.y), text = x.chat.slice(0, 80); ctx.save(); ctx.font = '500 13px "Schibsted Grotesk", system-ui, sans-serif'; const w = Math.min(360, Math.ceil(ctx.measureText(text).width) + 20), bx = s[0] + 12, by = s[1] + 44;
      ctx.beginPath(); const r = 9, hh = 28; ctx.moveTo(bx + 3, by); ctx.lineTo(bx + w - r, by); ctx.arc(bx + w - r, by + r, r, -0.5 * Math.PI, 0); ctx.lineTo(bx + w, by + hh - r); ctx.arc(bx + w - r, by + hh - r, r, 0, 0.5 * Math.PI); ctx.lineTo(bx + r, by + hh); ctx.arc(bx + r, by + hh - r, r, 0.5 * Math.PI, Math.PI); ctx.lineTo(bx, by + 3); ctx.quadraticCurveTo(bx, by, bx + 3, by); ctx.closePath();
      ctx.fillStyle = u.color || '#5B45E0'; ctx.shadowColor = 'rgba(0,0,0,0.22)'; ctx.shadowBlur = 8; ctx.shadowOffsetY = 2; ctx.fill(); ctx.shadowColor = 'transparent';
      ctx.fillStyle = '#FFFFFF'; ctx.textBaseline = 'middle'; ctx.textAlign = 'left'; ctx.save(); ctx.beginPath(); ctx.rect(bx + 8, by, w - 16, hh); ctx.clip(); ctx.fillText(text, bx + 10, by + hh / 2 + 0.5); ctx.restore(); ctx.restore(); });
  }

  /* ================================================================ the signed-out viewer's badge */
  function guestBadge() {
    const f = file(), top = ui.state && ui.state.root && ui.state.root.querySelector('.hd-top-r'); if (!f || !f.share || !top || top.querySelector('.hd-co-view')) return;
    const link = h('a', {class: 'hd-btn pri hd-co-signin', href: '/console/', text: ui.token ? 'Open Hoola' : 'Sign in to edit'});
    top.insertBefore(h('span', {class: 'hd-co-view', title: 'You opened a view-only link: you can look around, inspect and export, but not change the file.'}, icon('eye'), h('span', {text: 'View only'})), top.firstChild);
    top.appendChild(link); ui.state.root.classList.add('hd-co-guest');
    if (ui.token) HD.app.rawFetch('/api/design/files/' + enc(f.id), {headers: {Authorization: 'Bearer ' + ui.token}, credentials: 'omit', cache: 'no-store'}).then(r => { if (r.ok && document.contains(link) && file() === f) { link.textContent = 'Open to edit'; link.href = location.pathname + '#/f/' + enc(f.id); link.title = 'This is your own file'; } }, () => {});
  }

  /* ================================================================ wiring */
  let wiredOnce = false;
  function onStageDown(ev) {
    if (ev.button !== 0 || !file() || ev.target !== T().canvas) return; const b = canvasBox(), q = hitAt(ev.clientX - b.left, ev.clientY - b.top); if (!q) return;
    ev.preventDefault(); ev.stopPropagation();
    if (q.ids.length === 1) { if (C.openId === q.ids[0] && C.pop) closePop(); else openThread(q.ids[0]); return; }
    const pts = q.ids.map(id => pinPlace(thread(id).head)); let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity; for (const p of pts) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); }
    const z = (R().view && R().view.zoom) || 1, cv = T().canvas;
    if ((x1 - x0) * z < 2 && (y1 - y0) * z < 2 || z >= 64) { ui.menu({x: ev.clientX + 8, y: ev.clientY + 8}, q.ids.map(id => { const t = thread(id); return {label: (t.head.author || 'Someone') + ': ' + String(t.head.text || '').replace(/\s+/g, ' ').slice(0, 36), run: () => openThread(id)}; }), {label: 'Comments here'}); return; }
    const nz = Math.min(64, Math.max(z * 2, Math.min(cv.clientWidth / Math.max(1, x1 - x0), cv.clientHeight / Math.max(1, y1 - y0)) * 0.45));
    R().setView(T().view.at(nz, (x0 + x1) / 2, (y0 + y1) / 2, cv.clientWidth / 2, cv.clientHeight / 2), true);
  }
  function onStageMove(ev) {
    P.ptr = [ev.clientX, ev.clientY]; if (P.chat) placeChat();
    if (ev.buttons !== 0 || ev.target !== T().canvas || !C.hits.length) { if (C.hover) { C.hover = false; } return; }
    const b = canvasBox(), q = hitAt(ev.clientX - b.left, ev.clientY - b.top);
    if (q) { C.hover = true; ev.stopPropagation(); T().canvas.style.cursor = 'pointer'; if (T().state && T().state.hover) { T().state.hover = null; redraw(); } }
    else if (C.hover) { C.hover = false; T().canvas.style.cursor = (T().def && T().def.cursor) || 'default'; }
  }
  function onOpen(f) {
    cssCache = null; C.byId = new Map(); C.threads = []; C.openId = null; C.draft = null; C.pop = null; C.hits = []; C.mine = new Set(); C.filter = 'open'; C.rev++; C.panelSig = ''; C.loadedFor = null;
    V.open = false; V.list = []; V.cur = null; V.busy = false; V.saving = false; V.bar = null; V.loadedFor = null; V.rev++;
    P.follow = null; P.frame = null; P.wait = null; P.spots = new Map(); P.spotEl = null; P.vs = ''; P.chat = null;
    seenLoad(f.id);
    const st = ui.state;
    if (st && st.stage) { st.stage.addEventListener('pointerdown', onStageDown, true); st.stage.addEventListener('pointermove', onStageMove, true); }
    P.box = st && st.root ? st.root.querySelector('.hd-people') : null;
    if (P.mo) { P.mo.disconnect(); P.mo = null; }
    if (P.box) { P.box.addEventListener('click', ev => { const b = ev.target.closest ? ev.target.closest('.hd-person') : null; if (!b || !P.box.contains(b)) return; ev.preventDefault(); ev.stopPropagation(); if (b.classList.contains('more')) peopleMenu(b); else toggleFollow(+b.dataset.cid); }, true);
      P.box.addEventListener('keydown', ev => { if ((ev.key === 'Enter' || ev.key === ' ') && ev.target.classList && ev.target.classList.contains('more')) { ev.preventDefault(); peopleMenu(ev.target); } });
      if (typeof MutationObserver === 'function') { P.mo = new MutationObserver(decorate); P.mo.observe(P.box, {childList: true}); } decorate(); }
    guestBadge();
    if (!wiredOnce) { wiredOnce = true; wire(); }
    loadComments(); setTimeout(sendView, 300);
  }
  function onClose() {
    if (P.chat) endChat(true); hideSpot(); stopFollow(true); if (P.mo) { P.mo.disconnect(); P.mo = null; } P.box = null; clearTimeout(P.spotMine);
    hideBar(); V.cur = null; V.open = false; C.pop = null; C.openId = null; C.draft = null; C.byId = new Map(); C.threads = []; C.hits = [];
    if (ui.state && ui.state.leftTab !== 'layers') ui.state.leftTab = 'layers';
  }
  function wire() {                      /* once, after the first editor is up (the default commands exist by now) */
    R().addOverlay(drawPins);
    R().on('view', onView);
    T().onView(() => { if (P.follow !== null && !P.applying) stopFollow(); });
    N().on('comment', onCommentFrame);
    N().on('presence', onPresence);
    N().on('init', () => { if (!file()) return; setTimeout(decorate, 0); loadComments(); P.vs = ''; setTimeout(sendView, 120); if (V.open && !isGuest()) loadVersions(); });
    N().on('reload', () => { if (file() && ui.mounted) ui.toast('This file was restored to an earlier version.'); });
    N().on('status', s => { if (!file()) return; if (s !== 'live' && V.cur && !N().held) { V.cur = null; hideBar(); vDirty(); } });
    HD.sel.on('change', () => { C.panelSig = ''; });
    S().on('change', ch => { if (C.threads.length && (!ch || ch.structural !== false)) C.panelSig = ''; });
    if (window.HoolaTheme && window.HoolaTheme.onChange) window.HoolaTheme.onChange(() => { cssCache = null; redraw(); });
    P.idleT = setInterval(() => { if (file() && P.box) decorate(); }, 10000);
    window.addEventListener('resize', () => { P.vs = ''; if (file()) setTimeout(sendView, 150); });
    const act = () => (T().act || {});
    ui.registerShortcut('shift+c', () => togglePins(), 'Show or hide the comment pins');
    ui.registerShortcut('/', () => startChat(), 'Cursor chat');
    ui.registerShortcut('mod+alt+shift+h', () => openVersions(), 'Version history');
    /* Ctrl/Cmd+Alt+H was "distribute horizontally" before D5; with three or more layers selected it still is */
    ui.registerShortcut('mod+alt+h', () => { if ((HD.sel.ids || []).length >= 3 && canWrite() && !N().held && act().distribute) act().distribute('h'); else if (V.open) closeVersions(); else openVersions(); }, 'Version history');
    ui.command({id: 'versions', label: 'Version history', group: 'Other', run: openVersions});
    ui.command({id: 'versions.save', label: 'Save a version…', group: 'Other', when: () => canWrite() && !N().held, run: () => { openVersions(); V.saving = true; vDirty(); }});
    ui.command({id: 'comments.show', label: 'Show the comments', group: 'Other', run: () => leftTab('comments')});
    ui.command({id: 'comments.pins', label: 'Show or hide the comment pins', group: 'View', run: togglePins});
    ui.command({id: 'collab.spotlight', label: 'Spotlight me (ask everyone to follow)', group: 'Other', run: spotlight});
    ui.command({id: 'collab.chat', label: 'Cursor chat', group: 'Other', run: startChat});
    ui.command({id: 'collab.stopFollow', label: 'Stop following', group: 'Other', when: () => P.follow !== null, run: () => stopFollow()});
    ui.command({id: 'share.copyLayer', label: 'Copy a link to the selected layer', group: 'Other', when: () => !!selectedNode(), run: () => copyNodeLink(selectedNode())});
  }
  function init() {
    if (!HD.app || !HD.app.on) { setTimeout(init, 0); return; }
    HD.app.on('open', onOpen); HD.app.on('close', onClose);
  }

  ui.hook('comment', startDraft);
  ui.hook('versions', openVersions);
  ui.hook('share', shareDialog);
  ui.registerPanel('left', 'comments', {title: 'Comments', render: renderPanel});
  ui.registerPanel('left', 'versions', {title: 'History', render: renderVersions, when: () => V.open});
  ui.registerMenu('main', {label: 'Spotlight me', icon: 'eye', run: () => spotlight()});
  ui.registerMenu('main', {label: 'Cursor chat', icon: 'comment', keys: '/', run: () => startChat()});
  ui.registerMenu('main', {label: 'Show or hide the comment pins', icon: 'eyeoff', keys: 'shift+c', run: () => togglePins()});
  ui.registerMenu('context', ids => (ids && ids.length === 1 && file() ? {label: 'Copy link to this layer', icon: 'link', run: () => copyNodeLink(ids[0])} : null));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();

  /* what the browser test (server/tests/web/design_collab_test.js) and other feature files may call */
  HD.collab = {
    comments: {list: () => C.threads, open: openThread, close: closePop, jump: jump, reload: loadComments, unread: id => { const t = thread(id); return !!t && unread(t); },
      pin: id => { const t = thread(id); if (!t) return null; const p = pinClient(t); return {x: p[0] + PIN_R, y: p[1] - PIN_R, page: pinPlace(t.head)[2]}; }, hits: () => C.hits.slice(), get hidden() { return C.hidden; }, toggle: togglePins},
    versions: {open: openVersions, close: closeVersions, list: () => V.list, preview: preview, exit: exitPreview, get current() { return V.cur; }, reload: loadVersions},
    share: shareDialog,
    follow: follow, stopFollow: stopFollow, get following() { return P.follow; }, spotlight: spotlight, chat: startChat
  };
})();
