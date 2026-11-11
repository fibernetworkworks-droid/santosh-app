/* HOOLA PROMPTING - the page (/console/prompting; docs/HOOLA_PROMPTING_PLAN.md P3). Its own full-screen app like Hoola
   Flow: the same sign-in as the console (its token in this browser), the /api/prompting routes, the same strict CSP.

   Home (one box) -> the workbench (her words | what Hoola understood | score + the finished prompt) -> Run in Hoola /
   Copy / Save. Recipes = Hoola's starters with blanks. My prompts = what she saved.
   "Run in Hoola" only HANDS THE TEXT to the engine's own box (Web Studio or the chat) - it is never sent for her, and
   the engine shows its own price before anything is made. */
'use strict';
(function () {
  const $ = s => document.querySelector(s);
  const esc = v => (v == null ? '' : String(v)).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  let TOKEN = ''; try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch (e) { /* private window */ }
  if (!TOKEN) { location.replace('/console/'); return; }
  async function api(method, path, body) {
    const headers = {Authorization: 'Bearer ' + TOKEN}; let payload;
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    let data = null; try { data = await r.json(); } catch (e) { /* no body */ }
    if (!r.ok) { const bad = data && Array.isArray(data.detail) && data.detail[0];
      throw new Error((data && ((typeof data.detail === 'string' ? data.detail : '') || data.error || data.message)) || (bad ? String(bad.msg) : '') || `The server refused the request (${r.status})`); }
    return data;
  }
  function toast(msg, bad) { const t = $('#toast'); t.textContent = String(msg); t.className = 'hp-toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200); }
  const UI = window.HoolaImprove({api, esc, toast});
  const I = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const ICON = {home: I('<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"/>'),
    web: I('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/>'),
    image: I('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M21 16l-5-5-8 8"/>'),
    script: I('<path d="M6 3h9l4 4v14H6z"/><path d="M9 12h7M9 16h5"/>'),
    results: I('<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>'),
    recipes: I('<path d="M5 4h14v16H5z"/><path d="M9 8h6M9 12h6"/>'), saved: I('<path d="M6 3h12v18l-6-4-6 4z"/>'),
    back: I('<path d="M15 6l-6 6 6 6"/>')};
  const st = {secs: [], known: [], section: '', text: '', view: null, pack: null, savedId: '', ready: null, recipe: null, q: '', rsec: ''};

  function shell(active, body) {
    const nav = (key, hash, label, icon) => `<a class="hp-nav" href="${hash}" ${active === key ? 'aria-current="page"' : ''}>${ICON[icon || key]}<span>${esc(label)}</span></a>`;
    $('#hp').innerHTML = `<div class="hp"><nav class="hp-side" aria-label="Hoola Prompting">
        <div class="hp-brand"><img src="/static/hoola-icon-192.png" alt=""><span>Hoola Prompting</span></div>
        ${nav('home', '#/', 'Home')}
        <div class="hp-sep">Make a prompt for</div>
        ${st.secs.map(s => nav(s.key, '#/s/' + s.key, s.label, s.key)).join('')}
        <div class="hp-sep">Library</div>
        ${nav('recipes', '#/recipes', 'Recipes')}${nav('saved', '#/saved', 'My prompts')}${nav('results', '#/results', 'Results')}
        <div class="hp-grow"></div>
        <a class="hp-nav" href="/console/">${ICON.back}<span>Back to the console</span></a>
      </nav><main class="hp-main" id="hpMain"><div class="hp-wrap">${body}</div></main></div>`;
  }
  function seg() {
    return `<span class="hp-seg" role="group" aria-label="What are you making?">${[['', 'Auto'], ...st.secs.map(s => [s.key, s.label])]
      .map(([k, l]) => `<button type="button" data-sec="${esc(k)}" aria-pressed="${st.section === k}">${esc(l)}</button>`).join('')}</span>`;
  }
  const cards = items => items.map(r => `<button type="button" class="hp-card" data-recipe="${esc(r.id)}"><b>${esc(r.title)}</b><span>${esc(r.makes || '')}</span>
      <i><span class="hp-tag">${esc((st.secs.find(s => s.key === r.section) || {label: r.section}).label)}</span> ${r.kept ? `<span class="hp-kept">kept ${r.kept.kept} of ${r.kept.of} times</span> ` : ''}${r.blanks && r.blanks.length ? esc(r.blanks.length + ' blank' + (r.blanks.length > 1 ? 's' : '') + ' to fill') : 'ready to use'}</i></button>`).join('');

  /* ---------- home / a section ---------- */
  async function home(section) {
    st.section = section || '';
    const sec = st.secs.find(s => s.key === section);
    const [rec, saved] = await Promise.all([api('GET', '/api/prompting/recipes?section=' + encodeURIComponent(section || '')).catch(() => ({items: []})),
      api('GET', '/api/prompting/saved' + (section ? '?section=' + encodeURIComponent(section) : '')).catch(() => ({items: []}))]);
    shell(section || 'home', `<section class="hp-hero"><h1>${sec ? esc('A prompt for ' + sec.makes) : 'What do you want to make?'}</h1>
        <p>Write it roughly, in Hinglish or English. Hoola shows what it understood, fills in what it knows about your business, asks only what is missing, and writes the prompt the right way for the tool that will make it.</p>
        <form class="hp-ask" id="hpAsk"><label class="hp-lab" for="hpText" style="position:absolute;left:-9999px">Your rough idea</label>
          <textarea id="hpText" maxlength="2000" placeholder="${esc(sec && sec.key === 'web' ? 'mere sweet shop ki website banao' : sec && sec.key === 'script' ? 'coaching class ke liye 30 second ki reel script' : 'Diwali sale ka poster, thoda premium, gold wala')}">${esc(st.text)}</textarea>
          <div class="hp-askrow">${sec ? '' : seg()}<span class="hp-sp"></span><button class="hp-b pri lg" type="submit">Improve my prompt</button></div></form></section>
      <div class="hp-h2"><h2>Start from a recipe</h2><span>Hoola's starters - fill the blanks</span><span class="hp-sp"></span><a class="hp-b sm" href="#/recipes">All recipes</a></div>
      <div class="hp-grid">${cards(section ? (rec.items || []).slice(0, 6) : st.secs.flatMap(x => (rec.items || []).filter(r => r.section === x.key).slice(0, 2))) || '<p class="hp-empty">No recipes here yet.</p>'}</div>
      ${(saved.items || []).length ? `<div class="hp-h2"><h2>Continue</h2><span>your saved prompts</span></div><div class="hp-rows">${rows(saved.items.slice(0, 4))}</div>` : ''}
      <div class="hp-h2"><h2>What Hoola knows about your business</h2><span>used to fill blanks, always shown to you</span></div>
      ${st.known.length ? `<div class="hp-known">${st.known.map(k => `<div><b>${esc(k.label)}</b><span>${esc(k.value)}</span></div>`).join('')}</div>`
        : '<p class="hp-empty">Nothing yet. Add your business name and colours in Create &gt; Brand kit, and Hoola will fill them in for you.</p>'}`);
    $('#hpText').focus();
  }
  const rows = items => items.map(p => `<div class="hp-rowi"><div><b>${esc(p.title)}</b><span>${esc(p.prompt)}</span></div>
      <span class="hp-tag">${esc((st.secs.find(s => s.key === p.section) || {label: p.section}).label)}</span>
      <button type="button" class="hp-b sm" data-open="${esc(p.id)}">Open</button><button type="button" class="hp-b sm ghost danger" data-del="${esc(p.id)}" aria-label="Delete ${esc(p.title)}">Delete</button></div>`).join('');

  /* ---------- the workbench ---------- */
  function bench() {
    const p = st.pack, sec = UI.secOf(p.brief.section);
    shell(p.brief.section, `<div class="hp-top"><a class="hp-b sm ghost" href="#/s/${esc(p.brief.section)}">${ICON.back} New prompt</a><h1>${esc(sec.label)} prompt</h1><span class="hp-sp"></span>
        <span class="hp-tag">${st.savedId ? 'Saved' : 'Not saved'}</span></div>
      <div class="hp-bench"><div class="hp-pane"><label class="hp-lab" for="hpHers">Your words</label>
          <textarea class="hp-hers" id="hpHers" maxlength="2000">${esc(p.brief.intent)}</textarea>
          <div class="hp-acts" style="margin-bottom:18px"><button type="button" class="hp-b sm" id="hpAgain">Read my words again</button></div>
          <div id="hpBrief"></div></div>
        <div class="hp-pane sticky"><div id="hpResult"></div>
          <div class="hp-acts"><button type="button" class="hp-b pri" id="hpRun">${esc(p.out.run.label)}</button>
            <button type="button" class="hp-b" id="hpCopy">Copy</button><button type="button" class="hp-b" id="hpSave">${st.savedId ? 'Save changes' : 'Save'}</button></div>
          <p class="hpi-note" style="margin-top:10px;font-size:12.5px;color:var(--dim)">${p.out.run.to === 'web' ? 'Opens the Web Studio with this in its box. Nothing is built until you press Build there.' : 'Puts this in the chat box. Nothing is sent until you press Send; a paid job shows its price first.'}</p></div></div>`);
    st.view = UI.mount($('#hpBrief'), p, {resultEl: $('#hpResult'), onChange(pk) { st.pack = pk; $('#hpRun').textContent = pk.out.run.label; }});
  }
  async function understand(text, section) {
    text = String(text || '').trim();
    if (text.length < 3) { toast('Write one line about what you want to make.', true); return; }
    st.text = text;
    const btn = document.querySelector('#hpAsk [type=submit], #hpAgain'); if (btn) { btn.disabled = true; btn.textContent = 'Reading…'; }
    try {
      const pack = await api('POST', '/api/prompting/understand', {text, section: section || ''});
      if (pack.choose_section) { toast('Choose what you are making: ' + st.secs.map(s => s.label).join(', ') + '.'); if (btn) { btn.disabled = false; btn.textContent = 'Improve my prompt'; } return; }
      st.pack = pack; st.savedId = ''; go('#/w');
    } catch (e) { toast(e.message, true); if (btn) { btn.disabled = false; btn.textContent = btn.id === 'hpAgain' ? 'Read my words again' : 'Improve my prompt'; } }
  }
  /* BAHI: tell the ledger a prompt was taken out (shape only). Never blocks her. */
  function hand(how) {
    const rd = location.hash === '#/ready';
    const body = rd ? {text: st.ready.run.text || st.ready.prompt, section: 'web', recipe_id: st.ready.id || '', how}
      : {text: how === 'copy' ? st.pack.out.prompt : (st.pack.out.run.text || st.pack.out.prompt), brief: st.pack.brief, how};
    return api('POST', '/api/prompting/runs', {...body, origin: 'page'}).catch(() => null);
  }
  function run(r) {
    try { localStorage.setItem(r.to === 'web' ? 'hoola.prompt.toWeb' : 'hoola.flow.toChat', String(r.text || '')); }
    catch (e) { toast('This browser could not hand the text over. Use Copy.', true); return; }
    location.assign(r.to === 'web' ? '/console/web' : '/console/');
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast('Copied.'); }
    catch (e) { const t = document.createElement('textarea'); t.value = text; document.body.appendChild(t); t.select(); try { document.execCommand('copy'); toast('Copied.'); } catch (er) { toast('Could not copy. Select the text and copy it.', true); } t.remove(); }
  }

  /* ---------- recipes ---------- */
  async function recipes() {
    const r = await api('GET', `/api/prompting/recipes?section=${encodeURIComponent(st.rsec)}&q=${encodeURIComponent(st.q)}`).catch(e => { toast(e.message, true); return {items: []}; });
    shell('recipes', `<div class="hp-top"><h1>Recipes</h1><span class="hp-tag">Hoola's starters</span></div>
      <form class="hp-find" id="hpFind"><input type="search" id="hpQ" value="${esc(st.q)}" placeholder="Search: poster, reel, salon, Diwali, bakery…" aria-label="Search recipes">
        <span class="hp-seg" role="group" aria-label="Kind">${[['', 'All'], ...st.secs.map(s => [s.key, s.label])].map(([k, l]) => `<button type="button" data-rsec="${esc(k)}" aria-pressed="${st.rsec === k}">${esc(l)}</button>`).join('')}</span>
        <button class="hp-b" type="submit">Search</button></form>
      <div class="hp-grid">${cards(r.items || []) || '<p class="hp-empty">Nothing matches. Try one word, like "poster" or "reel".</p>'}</div>
      <p style="margin-top:16px;color:var(--dim);font-size:13px">These are starting points written by Hoola. Once enough people have used a recipe, the ones whose results were kept come first, with the count.</p>`);
  }
  async function openRecipe(id) {
    const list = await api('GET', '/api/prompting/recipes?section=' + (id.startsWith('web:') ? 'web' : '') + '&q=' + (id.startsWith('web:') ? encodeURIComponent(st.q) : '')).catch(() => ({items: []}));
    const r = (list.items || []).find(x => x.id === id) || {id, title: 'Recipe', blanks: []};
    if (!r.blanks || !r.blanks.length) return useRecipe(id, {});
    st.recipe = r;
    shell('recipes', `<div class="hp-top"><a class="hp-b sm ghost" href="#/recipes">${ICON.back} Recipes</a><h1>${esc(r.title)}</h1></div>
      <form class="hp-form" id="hpFill"><p style="color:var(--mut)">${esc(r.makes || '')}. Fill what you know - anything you leave empty becomes a question, never a made-up value.</p>
        ${r.blanks.map(b => `<div><label for="bl_${esc(b.key)}">${esc(b.label)}</label><input id="bl_${esc(b.key)}" name="${esc(b.key)}" maxlength="120" placeholder="${esc(b.eg || '')}" autocomplete="off"></div>`).join('')}
        <div><button class="hp-b pri" type="submit">Make my prompt</button></div></form>`);
    $('#hpFill input')?.focus();
  }
  async function useRecipe(id, values) {
    try {
      const got = await api('POST', '/api/prompting/recipes/use', {recipe_id: id, values});
      if (got.ready) { st.ready = {...got.ready, id}; go('#/ready'); return; }
      st.pack = got; st.savedId = ''; st.text = got.brief.intent; go('#/w');
    } catch (e) { toast(e.message, true); }
  }
  function ready() {
    const r = st.ready;
    shell('recipes', `<div class="hp-top"><a class="hp-b sm ghost" href="#/recipes">${ICON.back} Recipes</a><h1>${esc(r.title)}</h1><span class="hp-tag">Website template</span></div>
      <pre class="hp-pre" tabindex="0">${esc(r.prompt)}</pre>
      <div class="hp-acts"><button type="button" class="hp-b pri" id="hpRun">${esc(r.run.label)}</button><button type="button" class="hp-b" id="hpCopy">Copy</button></div>
      <p style="margin-top:10px;color:var(--dim);font-size:13px">A complete website prompt from the Web Studio library. The name is a working name you can change there.</p>`);
  }

  /* ---------- my prompts ---------- */
  async function saved() {
    const r = await api('GET', '/api/prompting/saved').catch(e => { toast(e.message, true); return {items: []}; });
    shell('saved', `<div class="hp-top"><h1>My prompts</h1><span class="hp-tag">${(r.items || []).length} saved</span></div>
      ${(r.items || []).length ? `<div class="hp-rows">${rows(r.items)}</div>` : '<p class="hp-empty">Nothing saved yet. Make a prompt and press Save to keep it here.</p>'}`);
  }

  /* ---------- results: the ledger (BAHI) ---------- */
  const GRADE = {kept: 'Kept', kept_after_edit: 'Kept after an edit', redone: 'Redone', dropped: 'Dropped', unused: 'Never used'};
  function runState(r) {
    if (r.grade) return GRADE[r.grade] + (r.grade.startsWith('kept') && !r.by_her ? ' (still there after 3 days)' : '');
    return {handed: r.how === 'copy' ? 'Copied out of Hoola' : 'Not run yet', running: 'Being made', ready: 'Made - waiting to see what you do with it', settled: 'Closed'}[r.status] || r.status;
  }
  function four(n) {
    const v = (x, unit) => x === null || x === undefined ? '<b class="hp-na">-</b>' : `<b>${esc(String(x))}${unit || ''}</b>`;
    return `<div class="hp-four">
      <div><span>Kept rate</span>${v(n.kept_rate, '%')}<small>${n.kept} kept of ${n.graded} judged</small></div>
      <div><span>Redos for each kept result</span>${v(n.redos_per_kept)}<small>${n.redone} redone</small></div>
      <div><span>Rupees for each kept result</span>${v(n.inr_per_kept === null || n.inr_per_kept === undefined ? null : 'Rs ' + n.inr_per_kept)}<small>AI list price, not a bill</small></div>
      <div><span>Minutes to a kept result</span>${v(n.minutes_to_kept)}<small>from taking the prompt to keeping the result</small></div></div>
      ${n.enough ? '' : `<p class="hp-empty">Numbers appear after ${n.min_runs} results have been judged. So far: ${n.graded}. ${n.open ? n.open + ' still open.' : ''}</p>`}`;
  }
  async function results() {
    const r = await api('GET', '/api/prompting/ledger' + (st.everyone ? '?everyone=1' : ''));
    const n = r.numbers, lab = k => (st.secs.find(s => s.key === k) || {label: k}).label;
    shell('results', `<div class="hp-top"><h1>Results</h1><span class="hp-tag">last ${n.days} days</span>
        ${r.owner ? `<span class="hp-seg" role="group" aria-label="Whose numbers"><button type="button" data-who="" aria-pressed="${!st.everyone}">Mine</button><button type="button" data-who="1" aria-pressed="${!!st.everyone}">All users who share</button></span>` : ''}</div>
      <p class="hp-lead">What happened to the results of the prompts you took from here. This is how Hoola Prompting is judged.</p>
      ${four(n.all)}
      <h2 class="hp-sub2">By kind</h2>
      <div class="hp-rows">${Object.keys(n.sections).map(k => { const s = n.sections[k]; return `<div class="hp-rowi hp-wrapr"><div><b>${esc(lab(k))}</b>
          <span>${s.enough ? `${s.kept_rate}% kept (${s.kept} of ${s.graded})` : `${s.graded} judged so far - numbers after ${s.min_runs}`} · ${s.redone} redone · ${s.dropped} dropped · ${s.unused} never used</span>
          <span>Prompt Score check: ${esc(s.score_check.say)}</span></div></div>`; }).join('')}</div>
      ${st.everyone ? '' : `<h2 class="hp-sub2">Your recent prompts</h2>
      ${(r.recent || []).length ? `<div class="hp-rows">${r.recent.map(x => `<div class="hp-rowi hp-wrapr"><div><b>${esc(lab(x.section))}${x.recipe ? ' · from a recipe' : ''} · score ${x.score || '-'}</b>
          <span>${esc(runState(x))}${x.edited_before ? ' · you changed the prompt before running it' : ''}${x.edits ? ` · ${x.edits} change${x.edits > 1 ? 's' : ''} to the result` : ''}${x.inr ? ` · Rs ${x.inr}` : ''} · ${esc(new Date(x.at).toLocaleString())}</span></div>
          <button type="button" class="hp-b sm${x.thumb === 'up' ? ' pri' : ''}" data-thumb="up" data-run="${esc(x.id)}" aria-pressed="${x.thumb === 'up'}">Good result</button>
          <button type="button" class="hp-b sm${x.thumb === 'down' ? ' danger' : ''}" data-thumb="down" data-run="${esc(x.id)}" aria-pressed="${x.thumb === 'down'}">Not right</button></div>`).join('')}</div>`
        : '<p class="hp-empty">Nothing yet. Make a prompt and press its Open or Use button; what you do with the result shows here.</p>'}
      <h2 class="hp-sub2">What is kept about your prompts</h2>
      <p class="hp-lead">Only the shape: the kind, the recipe, which details were filled, the score and what happened to the result. Your words, prices, names and numbers are not stored here. Nothing is written from an incognito chat.</p>
      <div class="hp-acts"><label class="hp-sw"><input type="checkbox" id="hpLedger" ${r.prefs.ledger ? 'checked' : ''}> Keep this record for me</label>
        <label class="hp-sw"><input type="checkbox" id="hpShare" ${r.prefs.share ? 'checked' : ''}> Let my results (shape only) help order recipes for everyone</label>
        <button type="button" class="hp-b sm danger" id="hpForget">Delete my record</button></div>`}
      <p style="margin-top:16px;color:var(--dim);font-size:13px">${esc(n.note)}</p>`);
  }

  /* ---------- routing + events ---------- */
  function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }
  async function route() {
    const h = location.hash || '#/';
    try {
      if (h === '#/w') { if (st.pack) bench(); else go('#/'); }
      else if (h === '#/ready') { if (st.ready) ready(); else go('#/recipes'); }
      else if (h === '#/recipes') await recipes();
      else if (h === '#/saved') await saved();
      else if (h === '#/results') await results();
      else if (h.startsWith('#/s/') && st.secs.some(s => s.key === h.slice(4))) await home(h.slice(4));
      else await home('');
    } catch (e) { toast(e.message, true); }
    const m = $('#hpMain'); if (m) m.scrollTop = 0;
  }
  document.addEventListener('submit', e => {
    if (e.target.id === 'hpAsk') { e.preventDefault(); understand($('#hpText').value, st.section); }
    if (e.target.id === 'hpFind') { e.preventDefault(); st.q = $('#hpQ').value.trim(); recipes(); }
    if (e.target.id === 'hpFill') { e.preventDefault(); const v = {}; e.target.querySelectorAll('input').forEach(i => { v[i.name] = i.value.trim(); }); useRecipe(st.recipe.id, v); }
  });
  document.addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && e.target.id === 'hpText') { e.preventDefault(); $('#hpAsk').requestSubmit(); } });
  document.addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.sec !== undefined) { st.section = b.dataset.sec; document.querySelectorAll('[data-sec]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
    if (b.dataset.rsec !== undefined) { st.rsec = b.dataset.rsec; st.q = $('#hpQ') ? $('#hpQ').value.trim() : st.q; recipes(); return; }
    if (b.dataset.recipe) { openRecipe(b.dataset.recipe); return; }
    if (b.dataset.who !== undefined) { st.everyone = !!b.dataset.who; results().catch(er => toast(er.message, true)); return; }
    if (b.dataset.thumb) { try { await api('POST', `/api/prompting/runs/${encodeURIComponent(b.dataset.run)}/thumb`, {value: b.dataset.thumb}); await results(); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpForget') { if (!confirm('Delete the whole record of your prompts and their results? This cannot be undone.')) return;
      try { const r = await api('DELETE', '/api/prompting/ledger?confirm=DELETE'); toast(`Deleted ${r.deleted} record${r.deleted === 1 ? '' : 's'}.`); await results(); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpAgain') { understand($('#hpHers').value, st.pack.brief.section); return; }
    if (b.id === 'hpRun') { b.disabled = true; await hand('run'); run(location.hash === '#/ready' ? st.ready.run : st.pack.out.run); return; }
    if (b.id === 'hpCopy') { hand('copy'); copy(location.hash === '#/ready' ? st.ready.prompt : st.pack.out.prompt); return; }
    if (b.id === 'hpSave') { b.disabled = true;
      try { const r = await api('POST', '/api/prompting/saved', {brief: st.pack.brief, id: st.savedId}); st.savedId = r.id; toast('Saved in My prompts.'); bench(); }
      catch (er) { toast(er.message, true); b.disabled = false; } return; }
    if (b.dataset.open) { try { const r = await api('GET', '/api/prompting/saved/' + encodeURIComponent(b.dataset.open));
        if (!r.out) { toast('This saved prompt could not be opened.', true); return; }
        st.pack = {brief: r.brief, score: r.score, out: r.out, source_labels: r.source_labels}; st.savedId = r.id; st.text = r.brief.intent; go('#/w'); } catch (er) { toast(er.message, true); } return; }
    if (b.dataset.del) { if (!confirm('Delete this saved prompt?')) return;
      try { await api('DELETE', '/api/prompting/saved/' + encodeURIComponent(b.dataset.del)); toast('Deleted.'); route(); } catch (er) { toast(er.message, true); } }
  });
  document.addEventListener('change', async e => {
    if (e.target.id !== 'hpLedger' && e.target.id !== 'hpShare') return;
    try { await api('PUT', '/api/prompting/ledger/prefs', e.target.id === 'hpLedger' ? {ledger: e.target.checked} : {share: e.target.checked}); toast('Saved.'); }
    catch (er) { e.target.checked = !e.target.checked; toast(er.message, true); }
  });
  window.addEventListener('hashchange', route);
  (async () => {
    try { const s = await UI.sections(); st.secs = s.list; st.known = s.known; }
    catch (e) { $('#hp').innerHTML = `<p class="hp-boot">${esc(e.message)}</p>`; return; }
    route();
  })();
})();
