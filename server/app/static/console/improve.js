/* HOOLA PROMPTING - the brief view and the Improve sheet (docs/HOOLA_PROMPTING_PLAN.md P2). One piece used everywhere she
   types an ask: the console chat box, the Web Studio, Create and the Prompting page.

   What it never does: rewrite silently. She always sees what Hoola understood - each part marked by where it came from
   (her words / her business / Hoola's suggestion / missing) - and can change, remove or answer it. Her own text is only
   replaced when SHE presses "Use this prompt", and the caller keeps the original for Undo.

   window.HoolaImprove({api, esc, toast}) -> {mount(el, pack, opts), open(text, opts), sections()} ; the last made
   instance is kept at HoolaImprove.ui for pages that load later (the Create studio). */
'use strict';
(function () {
  const LOCK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>';
  window.HoolaImprove = function ({api, esc, toast}) {
    let SECS = null;
    async function sections() {
      if (!SECS) { const r = await api('GET', '/api/prompting/sections'); SECS = {list: r.sections || [], known: r.known || []}; }
      return SECS;
    }
    const secOf = key => (SECS ? SECS.list.find(s => s.key === key) : null) || {slots: [], label: key, engine: ''};

    /* ---- the brief: chips, locked facts, questions ---- */
    function briefHtml(pack, editing) {
      const b = pack.brief, sec = secOf(b.section), lab = pack.source_labels || {};
      const chips = [], adds = [];
      for (const s of sec.slots) {
        const cur = b.slots[s.key];
        if (cur) chips.push(`<button type="button" class="hpi-chip s-${esc(cur.source)}" data-k="${esc(s.key)}" aria-expanded="${editing === s.key}"><b>${esc(s.label)}</b><span>${esc(optLabel(s, cur.value))}</span><i>${esc(lab[cur.source] || cur.source)}</i></button>`);
        else if (s.required) chips.push(`<button type="button" class="hpi-chip miss" data-k="${esc(s.key)}" aria-expanded="${editing === s.key}"><b>${esc(s.label)}</b><span>Not said yet</span><i>tap to add</i></button>`);
        else adds.push(`<button type="button" class="hpi-add" data-k="${esc(s.key)}">+ ${esc(s.label)}</button>`);
      }
      const facts = (b.facts || []).map(f => `<span class="hpi-fact" title="Copied exactly as you wrote it">${LOCK}${esc(f.text)}</span>`).join('');
      const qs = editing ? '' : (b.questions || []).map(q => `<div class="hpi-q" data-q="${esc(q.key)}"><p>${esc(q.q)}</p>
          ${optsHtml(q.key, q.options, q.option_labels, q.suggested)}
          <input class="hpi-in" data-qin="${esc(q.key)}" placeholder="${esc(q.eg ? 'For example: ' + q.eg : 'Type your answer and press Enter')}" aria-label="${esc(q.q)}"></div>`).join('');
      return `<div class="hpi-block"><h4>What Hoola understood <small>for ${esc(sec.engine || sec.label)}</small></h4>
          <div class="hpi-chips">${chips.join('')}</div>${adds.length ? `<div class="hpi-adds">${adds.join('')}</div>` : ''}
          ${editing ? editHtml(b, sec, editing) : ''}
          <div class="hpi-legend"><span class="l1">your words</span><span class="l2">your business</span><span class="l3">Hoola's suggestion</span><span class="l4">missing</span></div></div>
        ${facts ? `<div class="hpi-block"><h4>Your facts <small>locked - copied exactly, never changed</small></h4><div class="hpi-facts">${facts}</div></div>` : ''}
        ${qs ? `<div class="hpi-block"><h4>${(b.questions || []).length === 1 ? 'One question' : 'A few questions'} <small>skip any - a skipped one stays a marked blank</small></h4>${qs}</div>` : ''}`;
    }
    function optLabel(s, value) { const i = (s.options || []).indexOf(value); return i >= 0 && s.option_labels && s.option_labels[i] ? `${s.option_labels[i]} (${value})` : value; }
    function optsHtml(key, options, labels, suggested) {
      const low = String(suggested || '').trim().toLowerCase(), same = o => low && String(o).trim().toLowerCase() === low;
      const out = (options || []).map((o, i) => `<button type="button" class="hpi-opt${same(o) ? ' sug' : ''}" data-set="${esc(key)}" data-v="${esc(o)}"${same(o) ? ' title="Hoola\'s suggestion"' : ''}>${esc(labels && labels[i] ? labels[i] : o)}</button>`);
      if (low && !(options || []).some(same)) out.unshift(`<button type="button" class="hpi-opt sug" data-set="${esc(key)}" data-v="${esc(suggested)}" title="Hoola's suggestion">${esc(suggested)}</button>`);
      return out.length ? `<div class="hpi-opts">${out.join('')}</div>` : '';
    }
    function editHtml(b, sec, key) {
      const s = sec.slots.find(x => x.key === key) || {label: key, q: ''}, cur = b.slots[key];
      return `<div class="hpi-edit" data-edit="${esc(key)}"><label for="hpiEd">${esc(s.label)}${s.q ? ` - ${esc(s.q)}` : ''}</label>
        <textarea class="hpi-in" id="hpiEd" rows="2" placeholder="${esc(s.eg ? 'For example: ' + s.eg : '')}">${esc(cur ? cur.value : '')}</textarea>
        ${optsHtml(key, s.options, s.option_labels, '')}
        <div class="hpi-row"><button type="button" class="hpi-btn pri sm" data-save="${esc(key)}">Save</button>
          ${cur ? `<button type="button" class="hpi-btn sm" data-drop="${esc(key)}">Remove</button>` : ''}
          <button type="button" class="hpi-btn ghost sm" data-cancel>Cancel</button></div></div>`;
    }

    /* ---- the result: score with reasons, the finished prompt ---- */
    function resultHtml(pack) {
      const sc = pack.score, why = (sc.reasons || []).map(r => `<li class="${r.ok ? 'ok' : ''}">${r.key ? `<button type="button" data-k="${esc(r.key)}">${esc(r.text)}</button>` : esc(r.text)}</li>`).join('');
      return `<div class="hpi-block"><h4>Prompt Score</h4><div class="hpi-score"><div class="hpi-num" style="--p:${Number(sc.score) || 0}" role="img" aria-label="Score ${Number(sc.score) || 0} out of 100"><span>${Number(sc.score) || 0}</span></div>
          <ul class="hpi-why">${why || '<li class="ok">Everything this kind of prompt needs is here.</li>'}</ul></div><p class="hpi-note">${esc(sc.note || '')}</p></div>
        <div class="hpi-block"><h4>The finished prompt <small>${esc(String(pack.out.chars))} characters</small></h4><pre class="hpi-out" tabindex="0">${esc(pack.out.prompt)}</pre></div>`;
    }

    /* mount: draws the brief into `el` (and the result into opts.resultEl, else under it); every edit goes to the
       server (/compile, no model) and redraws. opts.onChange(pack) after each change. Returns {pack(), set(pack)}. */
    function mount(el, pack, opts) {
      opts = opts || {};
      let editing = '', busy = false;
      el.classList.add('hpi'); if (opts.resultEl) opts.resultEl.classList.add('hpi');
      function draw() {
        if (opts.resultEl) { el.innerHTML = briefHtml(pack, editing); opts.resultEl.innerHTML = resultHtml(pack); }
        else el.innerHTML = briefHtml(pack, editing) + resultHtml(pack);
        if (editing) { const t = el.querySelector('#hpiEd'); if (t) { t.focus(); t.setSelectionRange(t.value.length, t.value.length); } }
      }
      async function change(body) {
        if (busy) return; busy = true;
        try { pack = await api('POST', '/api/prompting/compile', {brief: pack.brief, ...body}); editing = ''; draw(); if (opts.onChange) opts.onChange(pack); }
        catch (e) { toast(e.message, true); }
        busy = false;
      }
      function click(e) {
        const b = e.target.closest('button'); if (!b) return;
        if (b.dataset.set) { change({set: {[b.dataset.set]: b.dataset.v}}); return; }
        if (b.dataset.save) { const v = el.querySelector('#hpiEd').value.trim(); change(v ? {set: {[b.dataset.save]: v}} : {drop: [b.dataset.save]}); return; }
        if (b.dataset.drop) { change({drop: [b.dataset.drop]}); return; }
        if (b.hasAttribute('data-cancel')) { editing = ''; draw(); return; }
        if (b.dataset.k) { editing = editing === b.dataset.k ? '' : b.dataset.k; draw(); if (!el.contains(b)) el.scrollIntoView({block: 'nearest'}); }
      }
      function key(e) {
        if (e.key === 'Enter' && e.target.dataset && e.target.dataset.qin) { e.preventDefault(); const v = e.target.value.trim(); if (v) change({set: {[e.target.dataset.qin]: v}}); }
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && e.target.id === 'hpiEd') { e.preventDefault(); el.querySelector('[data-save]')?.click(); }
      }
      el.addEventListener('click', click); el.addEventListener('keydown', key);
      if (opts.resultEl) opts.resultEl.addEventListener('click', click);
      draw();
      return {pack: () => pack, set(p) { pack = p; editing = ''; draw(); }};
    }

    /* open: the Improve sheet over her text. opts: {section, onUse(text, pack), useText(pack) -> string, useLabel}.
       Resolves when the sheet closes. Her text is untouched unless she presses the Use button. */
    async function open(text, opts) {
      opts = opts || {};
      text = String(text || '').trim();
      if (!text) { toast('Write a few words first.'); return; }
      const wrap = document.createElement('div');
      wrap.className = 'hpi-sheet'; wrap.setAttribute('role', 'dialog'); wrap.setAttribute('aria-modal', 'true'); wrap.setAttribute('aria-label', 'Improve this prompt');
      wrap.innerHTML = `<div class="hpi-box"><div class="hpi-head"><h3>Improve this prompt</h3><button type="button" class="hpi-x" data-close aria-label="Close">×</button></div>
        <div class="hpi-body"><div class="hpi-hers" aria-label="Your words"></div><div class="hpi-main"><p class="hpi-wait" role="status">Reading what you wrote…</p></div></div>
        <div class="hpi-foot"><button type="button" class="hpi-btn" data-close>Keep mine</button><button type="button" class="hpi-btn pri" data-use disabled>${esc(opts.useLabel || 'Use this prompt')}</button></div></div>`;
      wrap.querySelector('.hpi-hers').textContent = text;
      const before = document.activeElement;
      document.body.appendChild(wrap);
      const main = wrap.querySelector('.hpi-main'), useBtn = wrap.querySelector('[data-use]');
      let view = null, done;
      const closed = new Promise(r => { done = r; });
      function close() { document.removeEventListener('keydown', onKey, true); wrap.remove(); try { before && before.focus(); } catch (e) { /* gone */ } done(); }
      function onKey(e) { if (e.key === 'Escape') { e.stopPropagation(); close(); } }
      document.addEventListener('keydown', onKey, true);
      wrap.addEventListener('click', e => {
        if (e.target === wrap || e.target.closest('[data-close]')) { close(); return; }
        if (e.target.closest('[data-use]') && view) { const p = view.pack(); close(); const out = opts.useText ? opts.useText(p) : p.out.prompt;
          /* NATIJA KHATA: the ledger learns a prompt was taken (shape only; nothing from an incognito chat). Never blocks her. */
          api('POST', '/api/prompting/runs', {text: out, brief: p.brief, origin: 'improve', how: 'use', conversation_id: opts.conversationId ? String(opts.conversationId() || '') : ''}).catch(() => {});
          if (opts.onUse) opts.onUse(out, p); return; }
        const pk = e.target.closest('[data-pick]'); if (pk) read(pk.dataset.pick);
      });
      async function read(section) {
        main.innerHTML = '<p class="hpi-wait" role="status">Reading what you wrote…</p>'; useBtn.disabled = true;
        try {
          await sections();
          const pack = await api('POST', '/api/prompting/understand', {text, section: section || opts.section || ''});
          if (pack.choose_section) {
            main.innerHTML = `<div class="hpi"><h4>What are you making?</h4><div class="hpi-pick">${SECS.list.map(s => `<button type="button" data-pick="${esc(s.key)}"><b>${esc(s.label)}</b><span>${esc(s.makes)}</span></button>`).join('')}</div>
              <p class="hpi-note">For anything else, your own words are already the right prompt - press Keep mine.</p></div>`;
            return;
          }
          main.innerHTML = ''; view = mount(main, pack, {}); useBtn.disabled = false;
          (wrap.querySelector('.hpi-q .hpi-in') || useBtn).focus();
        } catch (e) { main.innerHTML = `<p class="hpi-wait">${esc(e.message)}</p>`; }
      }
      read('');
      return closed;
    }
    const ui = {mount, open, sections, secOf};
    window.HoolaImprove.ui = ui;
    return ui;
  };
})();
