/* HOOLA CHAT KIT (v1.0) - the main chat's thread as ONE part every chat panel mounts, so words land, work shows and
   text is spaced the same way everywhere. Needs md.js (HoolaMD), stream.js (HoolaStream.Pacer) and mark.js (HoolaMark):
   the same three files the main chat runs. Styles: chatkit.css.

   const t = HoolaChat.mount(el, {acts, onAct, scroller, jump})
     acts      which buttons sit under the newest reply: any of 'copy','aloud','up','down','again' (default copy + aloud).
               copy and aloud work by themselves; up / down / again call onAct(kind, text, value) - give them only
               where the panel can really honour them.
     scroller  the element that scrolls (default: el's parent). jump:true adds the "Latest" button.

   A PANEL WITH LIVE EVENTS drives the turn itself:
     t.her(text, {files})        her message (rises in)
     t.begin(label)              a turn starts: the working row ("Thinking…" + the clock)
     t.label(text)               what Hoola is doing now (the row's words)
     t.step({id,label,state})    a step row: running -> 'done' / 'error' (also names the working row)
     t.delta(text)               streamed words                    } both land at the same pace: a panel
     t.final(text) -> Promise    the whole answer (resolves landed) } with no stream hands the whole text here
     t.text(full)                the whole text SO FAR (a snapshot that grows) - lands only the new part
     t.nextBlock()               words -> steps -> words: the next words are a new block
     t.end({stopped})            the turn is over: steps fold to "Worked for Ns", the action row appears
     t.stop()                    her Stop (the panel also tells its server)

   A PANEL THAT POLLS hands the whole list each time and the kit works out what is new:
     t.sync({key, messages, working, label, steps})
       key       which chat this is (a change redraws everything, unpaced)
       messages  [{id, role:'her'|'hoola'|'raw', text, files, node|html, worked, steps}] oldest first
       working   Hoola is working now; label = the working row's words; steps = [{id,label,state}]
     The first sync draws history whole. After that a NEW reply lands word by word, a reply that grows keeps landing,
     and her message shown at send time (t.her(text, {pending:true})) is matched, never drawn twice.

     t.set(messages)             history, drawn whole (what sync does the first time)
     t.holding                   true while her sent message is held at the top (a panel that scrolls by itself leaves it)
     t.clear()                                                                                              */
'use strict';
(() => {
const TICK = '<svg viewBox="0 0 16 16"><path d="M3 8.5l3.2 3L13 5"/></svg>';
const DN = '<svg class="hck-dn" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3"/></svg>';
const ICON = {
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  aloud: '<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>',
  up: '<path d="M7 10v11H3V10zM7 10l5-8a3 3 0 0 1 3 3v4h5a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 18.6 21H7"/>',
  down: '<path d="M17 14V3h4v11zM17 14l-5 8a3 3 0 0 1-3-3v-4H4a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 5.4 3H17"/>',
  again: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
};
const NAME = {copy: 'Copy', aloud: 'Read aloud', up: 'Good answer', down: 'Not right', again: 'Ask again'};
const fmtSecs = s => s < 60 ? s + 's' : Math.floor(s / 60) + 'm ' + String(s % 60).padStart(2, '0') + 's';
const el = (tag, cls, html) => { const n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; };
/* what a voice should read: the words, not the markdown signs */
const plain = s => String(s || '').replace(/```[\s\S]*?```/g, ' ').replace(/[*_#>`|]/g, '').replace(/\[(.*?)\]\((.*?)\)/g, '$1').replace(/\s+/g, ' ').trim();
let speaking = null;
function aloud(text, btn) {
  const syn = window.speechSynthesis; if (!syn || typeof SpeechSynthesisUtterance === 'undefined') return false;
  const was = speaking; try { syn.cancel(); } catch { /* nothing to stop */ }
  if (was) { was.setAttribute('aria-pressed', 'false'); speaking = null; if (was === btn) return true; }
  const u = new SpeechSynthesisUtterance(plain(text)); u.lang = document.documentElement.lang || 'en-IN';
  u.onend = u.onerror = () => { if (speaking === btn) { btn.setAttribute('aria-pressed', 'false'); speaking = null; } };
  speaking = btn; btn.setAttribute('aria-pressed', 'true'); syn.speak(u); return true;
}

function mount(root, opts = {}) {
  root.classList.add('hck'); root.setAttribute('role', 'log'); root.setAttribute('aria-live', 'polite');
  const acts = opts.acts || ['copy', 'aloud'];
  let T = null;                    // the running turn
  let lastActs = null;
  let SY = null;                   // what sync() has drawn: {key, ids, text}
  const scroller = () => opts.scroller || root.parentElement;
  const L = lander(root, scroller);           // v0.999.203 her sent message lands at the top (see lander below)
  const near = () => { const s = scroller(); return !s || s.scrollHeight - (L.box === s ? L.pad : 0) - s.scrollTop - s.clientHeight < 90; };
  let follow = true, jumpBtn = null;
  const landAt = n => { if (!L.at(n)) return false; follow = false; if (jumpBtn) jumpBtn.hidden = true; return true; };
  const down = () => {
    if (L.anchored) {
      const s = L.box; L.space();
      if (L.held) { if (jumpBtn) jumpBtn.hidden = near(); return; }
      if (follow && s === scroller()) s.scrollTop = Math.max(s.scrollTop, s.scrollHeight - L.pad - s.clientHeight);
      return;
    }
    const s = scroller(); if (s && follow) s.scrollTop = s.scrollHeight;
  };
  const sc = scroller();
  if (sc) { sc.addEventListener('scroll', () => { follow = near(); if (jumpBtn) jumpBtn.hidden = follow; }, {passive: true}); L.watch(sc); }
  if (opts.jump && sc) {
    jumpBtn = el('button', 'hck-jump', 'Latest'); jumpBtn.type = 'button'; jumpBtn.hidden = true; root.after(jumpBtn);
    jumpBtn.addEventListener('click', () => { L.mine(); follow = true; jumpBtn.hidden = true; down(); });
  }
  // the Copy button on a code block
  root.addEventListener('click', async e => {
    const b = e.target.closest('.cbcopy'); if (!b || !root.contains(b)) return;
    const pre = b.closest('.cb')?.querySelector('pre'); if (!pre) return;
    try { await navigator.clipboard.writeText(pre.textContent); b.textContent = 'Copied'; setTimeout(() => { b.textContent = 'Copy'; }, 1500); } catch { /* the browser said no */ }
  });

  function her(text, o = {}) {
    lastActs?.remove(); lastActs = null;
    const m = el('div', 'hck-me');
    if (o.files && o.files.length) { const f = el('div', 'hck-files'); for (const x of o.files) { const name = typeof x === 'string' ? x : (x.name || x.filename || 'file'); const c = el('span', 'hck-file'); c.innerHTML = `<i>${HoolaMD.esc((name.split('.').pop() || '').slice(0, 4).toUpperCase())}</i>`; c.append(name); f.append(c); } m.append(f); }
    if (text) { const b = el('div', 'hck-bub'); b.textContent = text; if (o.still) b.style.animation = 'none'; m.append(b); }
    if (o.pending) { m._pending = String(text || '').trim(); }
    if (o.id != null) m.dataset.id = o.id;
    root.append(m);
    if (o.still || !landAt(m)) { follow = true; if (jumpBtn) jumpBtn.hidden = true; down(); }
    return m;
  }
  function block() { const h = el('div', 'hck-ho'); root.append(h); return h; }
  function raw(m) { const d = el('div', 'hck-raw'); if (m.node) d.append(m.node); else d.innerHTML = m.html || ''; if (m.id != null) d.dataset.id = m.id; root.append(d); down(); return d; }

  function begin(label = 'Thinking…') {
    if (T) end();
    lastActs?.remove(); lastActs = null;
    const ho = block();
    const work = el('div', 'hck-work'); work.setAttribute('role', 'status');
    const mark = el('span', 'hck-mark'); mark.setAttribute('aria-hidden', 'true'); if (window.HoolaMark) mark.innerHTML = HoolaMark.think(24);
    const lab = el('span', 'hck-label'); lab.textContent = label || 'Thinking…';
    const secs = el('span', 'hck-secs'); secs.setAttribute('aria-hidden', 'true');
    const tog = el('button', 'hck-tog', DN); tog.type = 'button'; tog.hidden = true; tog.setAttribute('aria-label', 'Show steps'); tog.setAttribute('aria-expanded', 'false');
    const steps = el('div', 'hck-steps', '<div class="hck-tl"></div>');
    tog.addEventListener('click', () => { const on = !work.classList.contains('open'); work.classList.toggle('open', on); T && (T.open = on); tog.setAttribute('aria-expanded', String(on)); tog.setAttribute('aria-label', on ? 'Hide steps' : 'Show steps'); });
    work.append(mark, lab, secs, tog, steps); ho.append(work);
    T = {ho, work, lab, secs, tog, tl: steps.firstChild, rows: new Map(), n: 0, t0: opts.startedAt ? +opts.startedAt : Date.now(), stepT0: 0, seg: null, segs: [], open: false, base: label || 'Thinking…', lastWord: 0, chain: Promise.resolve(), msg: null};
    T.timer = setInterval(() => tick(), 500); down();
    return T;
  }
  function tick() {
    if (!T) return;
    const s = Math.floor((Date.now() - T.t0) / 1000); const want = s >= 1 ? fmtSecs(s) : '';
    if (T.secs.textContent !== want) T.secs.textContent = want;
    // the watchdog: words stopped for a moment while the turn still runs -> the row is back
    if (T.work.hidden && Date.now() - T.lastWord > 600) place();
  }
  function setLabel(text) { if (!T || !text || T.lab.textContent === text) return; T.lab.textContent = text; T.lab.classList.remove('swap'); void T.lab.offsetWidth; T.lab.classList.add('swap'); }
  function label(text) { if (!T) begin(text); else { T.base = text || T.base; if (![...T.rows.values()].some(r => r.classList.contains('run'))) setLabel(T.base); } }
  function place() { if (!T) return; T.ho.append(T.work); T.work.hidden = false; down(); }

  function step(p) {
    if (!T) begin();
    if (!T.rows.size) T.stepT0 = Date.now();
    T.tog.hidden = false;
    const id = String(p.id ?? p.label ?? T.n);
    let r = T.rows.get(id);
    if (!r) { r = el('div', 'hck-ts run', '<span class="ic"><span class="hck-spin"></span></span><span class="tx"></span><span class="tm"></span>'); r._t0 = Date.now(); T.rows.set(id, r); T.n++; T.tl.append(r); }
    r.querySelector('.tx').textContent = p.label || 'Working';
    if (p.state === 'done' || p.state === 'error') {
      if (r.classList.contains('run')) {
        r.classList.remove('run');
        const ic = r.querySelector('.ic'); ic.className = p.state === 'error' ? 'ic' : 'ic hck-tick'; ic.innerHTML = p.state === 'error' ? '!' : TICK;
        const s = p.secs != null ? +p.secs : Math.max(0, Date.now() - r._t0) / 1000; r.querySelector('.tm').textContent = s < 1 ? '<1s' : s.toFixed(1) + 's';
      }
      const running = [...T.rows.values()].find(x => x.classList.contains('run'));
      setLabel(running ? running.querySelector('.tx').textContent : T.base);
    } else setLabel(p.label || T.base);
    if (T.work.hidden) place();
    down();
  }
  function fold() {
    if (!T || !T.rows.size) return;
    const secs = Math.max(1, Math.round((Date.now() - T.stepT0) / 1000));
    const d = el('details', 'hck-fold'); d.open = !!T.open;
    d.innerHTML = `<summary><span class="sm">Worked for ${fmtSecs(secs)}</span>${DN}</summary>`;
    const tl = el('div', 'hck-tl');
    for (const r of T.rows.values()) { if (r.classList.contains('run')) { r.classList.remove('run'); const ic = r.querySelector('.ic'); ic.className = 'ic hck-tick'; ic.innerHTML = TICK; } tl.append(r); }
    d.append(tl); T.ho.insertBefore(d, T.work);
    T.rows = new Map(); T.tog.hidden = true; T.work.classList.remove('open'); setLabel(T.base);
  }
  function seg() {
    if (T.seg) return T.seg;
    fold();                                   // the steps fold the moment the words start
    const box = el('div', 'hck-txt textmd'); T.ho.insertBefore(box, T.work); T.work.hidden = true;
    const view = new HoolaMD.Live(box, {soft: true});
    const S = {box, view};
    S.pacer = new HoolaStream.Pacer((text, fin) => { view.update(text, !fin); T && (T.lastWord = Date.now()); down(); if (fin) { const d = S.done; S.done = null; d?.(); } });
    T.seg = S; T.segs.push(S); return S;
  }
  function delta(text) { if (!text) return; if (!T) begin(); seg().pacer.push(text); }
  function final(text) {
    if (!T) begin(); const S = seg();
    return new Promise(res => { S.done = res; S.pacer.final(String(text ?? '')); if (S.pacer.done && S.done) { S.done = null; res(); } });
  }
  /* the whole text so far: only what is new is queued; a text that no longer starts the same way is shown at once */
  function text(full) {
    if (!T) begin(); const S = seg(); full = String(full ?? '');
    if (full === S.pacer.target) return;
    if (full.startsWith(S.pacer.target)) S.pacer.push(full.slice(S.pacer.target.length));
    else { S.pacer.reset(); S.pacer.push(full); }
  }
  function nextBlock() { if (T) T.seg = null; }

  function drawActs(t, stopped) {
    const words = () => t.segs.map(S => S.pacer.finalText ?? S.pacer.target).filter(Boolean).join('\n\n');
    if (!t.segs.length || (!acts.length && !stopped)) return;
    const a = el('div', 'hck-acts'); a.setAttribute('role', 'group'); a.setAttribute('aria-label', 'Reply actions');
    a.innerHTML = acts.map(k => `<button type="button" class="hck-ra" data-act="${k}" aria-label="${NAME[k]}"${k === 'up' || k === 'down' || k === 'aloud' ? ' aria-pressed="false"' : ''}><svg viewBox="0 0 24 24">${ICON[k]}</svg><span>${NAME[k]}</span></button>`).join('')
      + (stopped ? '<span class="hck-stopped">Stopped</span>' : '');
    a.addEventListener('click', async e => {
      const b = e.target.closest('[data-act]'); if (!b) return; const k = b.dataset.act; let value;
      if (k === 'copy') { try { await navigator.clipboard.writeText(words()); const s = b.querySelector('span'); s.textContent = 'Copied'; setTimeout(() => { s.textContent = 'Copy'; }, 1500); } catch { /* the browser said no */ } }
      else if (k === 'aloud') { aloud(words(), b); }
      else if (k === 'up' || k === 'down') { const on = b.getAttribute('aria-pressed') !== 'true'; a.querySelectorAll('[data-act="up"],[data-act="down"]').forEach(x => x.setAttribute('aria-pressed', 'false')); b.setAttribute('aria-pressed', String(on)); value = on ? k : 'none'; }
      opts.onAct?.(k, words(), value, t.msg);
    });
    t.ho.append(a); lastActs = a; down();
  }
  function end(o = {}) {
    if (!T) return;
    const t = T; clearInterval(t.timer);
    for (const S of t.segs) if (!S.pacer.done) S.pacer.flush();
    fold(); t.work.remove(); T = null;
    drawActs(t, o.stopped);
    opts.onEnd?.(o);
  }
  function stop() { if (T) end({stopped: true}); }

  function drawOne(m, isLast) {
    if (m.role === 'her') return her(m.text, {files: m.files, still: true, id: m.id});
    if (m.role === 'raw') return raw(m);
    const ho = block(); if (m.id != null) ho.dataset.id = m.id;
    if (m.worked) {
      const d = el('details', 'hck-fold'); d.innerHTML = `<summary><span class="sm">Worked for ${HoolaMD.esc(String(m.worked))}</span>${DN}</summary>`;
      const tl = el('div', 'hck-tl');
      for (const s of m.steps || []) { const r = el('div', 'hck-ts', `<span class="ic hck-tick">${TICK}</span><span class="tx"></span><span class="tm"></span>`); r.querySelector('.tx').textContent = Array.isArray(s) ? s[0] : s.label; r.querySelector('.tm').textContent = (Array.isArray(s) ? s[1] : s.time) || ''; tl.append(r); }
      d.append(tl); ho.append(d);
    }
    if (m.text) ho.append(el('div', 'hck-txt textmd', HoolaMD.render(m.text, false)));
    if (isLast && m.text) drawActs({ho, msg: m, segs: [{pacer: {finalText: m.text}}]}, m.stopped);
    return ho;
  }
  function set(messages) {
    clear();
    const list = messages || [];
    list.forEach((m, i) => drawOne(m, i === list.length - 1));
    follow = true; down();
  }
  function clear() { if (T) { clearInterval(T.timer); for (const S of T.segs) S.pacer.flush?.(); T = null; } lastActs = null; SY = null; L.drop(); root.innerHTML = ''; }

  /* a reply that arrived: lands at reading pace inside the running turn (a turn is opened when none is) */
  function land(m, working) {
    if (!T) begin(); 
    if (T.msg && T.msg.id !== m.id) nextBlock();
    T.msg = m;
    if (working) { text(m.text); return; }
    const t = T; t.landing = (t.landing || 0) + 1;
    t.chain = t.chain.then(() => (T === t ? final(m.text) : null)).then(() => { t.landing--; if (T === t && !t.landing && t.over) end(); });
  }
  function sync(st = {}) {
    const list = (st.messages || []).filter(m => m && (m.role === 'raw' || m.text || (m.files && m.files.length)));
    const ids = list.map(m => String(m.id));
    const samePrefix = SY && SY.key === st.key && SY.ids.length <= ids.length && SY.ids.every((x, i) => x === ids[i]);
    if (!samePrefix) {
      // first time, another chat, or the list was rewritten: history drawn whole, the newest reply only if it is still being written
      const live = st.working && list.length && list[list.length - 1].role === 'hoola' ? list[list.length - 1] : null;
      set(live ? list.slice(0, -1) : list);
      SY = {key: st.key, ids, text: new Map(list.map(m => [String(m.id), m.text || '']))};
      if (st.working) { begin(st.label); if (live) land(live, true); }
    } else {
      for (let i = SY.ids.length; i < list.length; i++) {
        const m = list[i];
        if (m.role === 'her') {
          const mine = [...root.querySelectorAll('.hck-me')].find(n => n._pending != null && n._pending === String(m.text || '').trim());
          if (mine) { mine._pending = null; mine.dataset.id = m.id; }
          else { if (T && T.segs.length) end(); her(m.text, {files: m.files, id: m.id}); }
        } else if (m.role === 'raw') { if (T && T.segs.length && !st.working) end(); raw(m); if (T) place(); }
        else land(m, !!st.working && i === list.length - 1);
        SY.ids.push(String(m.id)); SY.text.set(String(m.id), m.text || '');
      }
      // the newest reply grew (a snapshot) or was finished
      const lastM = list[list.length - 1];
      if (lastM && lastM.role === 'hoola' && SY.text.get(String(lastM.id)) !== (lastM.text || '')) {
        SY.text.set(String(lastM.id), lastM.text || '');
        if (T && T.msg && String(T.msg.id) === String(lastM.id)) { T.msg = lastM; if (st.working) text(lastM.text); else land(lastM, false); }
        else { const n = [...root.querySelectorAll('.hck-ho')].find(x => x.dataset.id === String(lastM.id)); const box = n?.querySelector('.hck-txt'); if (box) box.innerHTML = HoolaMD.render(lastM.text, false); }
      } else if (lastM && lastM.role === 'hoola' && !st.working && T && T.msg && String(T.msg.id) === String(lastM.id) && !T.landing && T.seg && !T.seg.pacer.finalText) land(lastM, false);
      if (st.working && !T) begin(st.label);
    }
    if (T) {
      if (st.working) { T.over = false; if (st.label) label(st.label); for (const s of st.steps || []) step(s); }
      else { T.over = true; if (!T.landing) end(); }
    }
  }
  return {her, begin, label, step, delta, text, final, nextBlock, end, stop, set, sync, clear, raw, get busy() { return !!T; }, get holding() { return L.held; }, get el() { return root; }};
}

/* v0.999.203 THE LANDING (the main chat's v0.999.199, for every thread): her sent message goes to the TOP of the box and
   room is kept under the thread, so the reply grows into space that is already there; the view is held there until she
   scrolls herself, then it is hers. lander(thread, box) -> {at(node), space(), drop(), watch(box), mine(), held, anchored, pad, box}
   box: the element that scrolls, or a function giving it; a box that does not scroll -> the nearest scrolling box around
   the thread. A thread drawn by innerHTML keeps it: call at(her newest bubble) after drawing, space() after each redraw. */
function lander(root, box) {
  const TOP = 16;
  let A = null, PAD = 0, BASE = null, T0 = 0, U = 0, B = null;
  const bound = new WeakSet();
  const scrolls = s => { try { return !!s && s.isConnected && /(auto|scroll|overlay)/.test(getComputedStyle(s).overflowY); } catch { return false; } };
  const yOf = (n, s) => n.getBoundingClientRect().top - s.getBoundingClientRect().top + s.scrollTop;
  const mine = () => { U = Date.now(); };
  const held = () => !!A && U < T0;
  function find() {
    const s = typeof box === 'function' ? box() : box; if (scrolls(s)) return s;
    for (let p = root.parentElement; p && p !== document.body; p = p.parentElement) if (scrolls(p)) return p;
    return null;
  }
  function watch(s) { if (!s || bound.has(s)) return; bound.add(s); for (const k of ['wheel', 'touchstart', 'pointerdown']) s.addEventListener(k, mine, {passive: true}); }
  function space() {
    const s = B; if (!A || !s) return;
    if (!A.isConnected) return;
    if (BASE == null) BASE = parseFloat(getComputedStyle(root).paddingBottom) || 0;
    const natural = root.getBoundingClientRect().bottom - s.getBoundingClientRect().top + s.scrollTop - PAD + (parseFloat(getComputedStyle(s).paddingBottom) || 0);
    const pad = Math.max(0, Math.ceil(yOf(A, s) - TOP + s.clientHeight - natural));
    if (pad !== PAD) { PAD = pad; root.style.paddingBottom = (BASE + pad) + 'px'; }
    if (held() && Date.now() - T0 > 450) { const want = Math.max(0, Math.round(yOf(A, s) - TOP)); if (Math.abs(s.scrollTop - want) > 1) s.scrollTop = want; }
  }
  function drop() { A = null; B = null; if (PAD) { PAD = 0; root.style.paddingBottom = BASE ? BASE + 'px' : ''; } }
  function at(n) {
    const s = find(); if (!s || !n) return false;
    watch(s); A = n; B = s; T0 = Date.now(); space();
    const top = Math.max(0, Math.round(yOf(n, s) - TOP));
    const calm = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    try { s.scrollTo({top, behavior: calm ? 'auto' : 'smooth'}); } catch { s.scrollTop = top; }
    return true;
  }
  /* a node that was redrawn (innerHTML): the same place in the new drawing */
  function again(n) { if (A && !A.isConnected && n) A = n; space(); }
  document.addEventListener('keydown', e => { if (/^(PageUp|PageDown|ArrowUp|ArrowDown|Home|End| )$/.test(e.key) && !e.target.closest?.('textarea,input,[contenteditable]')) mine(); });
  if (window.ResizeObserver) new ResizeObserver(() => { if (A) space(); }).observe(root);
  return {at, space, again, drop, watch, mine, get held() { return held(); }, get anchored() { return !!A && !!B; }, get pad() { return PAD; }, get box() { return B; }};
}

/* the box she types in - the same pill everywhere; Send turns into Stop while Hoola works.
   bar(host, {placeholder, plus, mic, quality, onSend(text, {working}), onStop, onPlus, onMic}) -> {working, value, focus, clear}
   quality: true = the row under the box carries her credits + the quality tier (the page loads quality.js) */
function bar(host, o = {}) {
  host.classList.add('hck-bar');
  const ph = HoolaMD.esc(o.placeholder || 'Message Hoola');
  host.innerHTML = (o.plus ? '<button type="button" class="hck-ib" data-b="plus" aria-label="Add files"><svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg></button>' : '')
    + `<textarea rows="1" aria-label="${ph}" placeholder="${ph}"></textarea>`
    + (o.mic ? '<button type="button" class="hck-ib" data-b="mic" aria-label="Speak"><svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg></button>' : '')
    + '<button type="button" class="hck-ib go" aria-label="Send" disabled><svg viewBox="0 0 24 24"><path d="M12 19V5M6 11l6-6 6 6"/></svg></button>';
  const ta = host.querySelector('textarea'), go = host.querySelector('.go');
  // v0.999.29 the row under the box: her credits + the quality tier (quality.js), only where the panel asks for it
  if (o.quality && !host.nextElementSibling?.classList.contains('hck-under')) {
    const u = document.createElement('div'); u.className = 'hck-under'; u.innerHTML = '<span data-hoola-quality></span>';
    host.insertAdjacentElement('afterend', u);
  }
  let working = false;
  const sync = () => { go.disabled = !working && !ta.value.trim(); ta.style.height = 'auto'; const h = ta.scrollHeight; if (h) ta.style.height = Math.min(140, h) + 'px'; };
  const send = () => { const v = ta.value.trim(); if (!v) return; ta.value = ''; sync(); o.onSend?.(v, {working}); };
  ta.addEventListener('input', sync);
  // typed while Hoola works: the panel decides (queue / steer); the round button is Stop then
  ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
  go.addEventListener('click', () => { if (working) o.onStop?.(); else send(); });
  host.querySelector('[data-b="plus"]')?.addEventListener('click', () => o.onPlus?.());
  host.querySelector('[data-b="mic"]')?.addEventListener('click', e => o.onMic?.(e.currentTarget));
  return {
    set working(v) { working = !!v; go.classList.toggle('stop', working); go.setAttribute('aria-label', working ? 'Stop' : 'Send');
      go.innerHTML = working ? '<svg viewBox="0 0 24 24"><rect x="7" y="7" width="10" height="10" rx="2"/></svg>' : '<svg viewBox="0 0 24 24"><path d="M12 19V5M6 11l6-6 6 6"/></svg>'; sync(); },
    get working() { return working; },
    get value() { return ta.value; }, set value(v) { ta.value = v || ''; sync(); },
    focus: () => ta.focus(), clear: () => { ta.value = ''; sync(); }, input: ta,
  };
}

window.HoolaChat = {mount, bar, fmtSecs, plain};
window.HoolaChat.lander = lander;   // v0.999.203 the landing, for a thread drawn without the kit (Interactive)
})();
