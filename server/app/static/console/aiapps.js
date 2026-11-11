/* v0.772 HOOLA AI APPS - the console page (sidebar row "AI Apps").

   An AI app answers HER customers (a chat page, a website bubble, her business WhatsApp, an API key, an MCP tool) from
   her facts, her Seva knowledge base and her approved answers. This page is her desk for them:

     list       her AI apps + New + Templates
     new        one line -> POST /api/aiapps/plan -> the checked soul (errors / warnings / questions) -> Create
     app        Settings (the soul fields, Save draft), Preview (a private chat on the DRAFT), Channels (link + QR, embed
                snippet, API keys, MCP address, WhatsApp number), Logs (filter + Correct this answer), Numbers (stats +
                gaps), Versions (Restore, her tap). Publish = a confirm showing the draft hash -> POST publish {hash}.
     templates  ready souls by trade: Trial (nothing saved) / Use

   Routes are exactly the ones in docs/AIAPPS_PLAN.md. Every piece of server data goes into the page with textContent
   (the h() helper below); nothing from the server is ever written as HTML. */
window.HoolaAiApps = function ({api, toast}) {
  const B = '/api/aiapps';
  const q = encodeURIComponent;
  const ACTIONS = [['handover', 'Pass the visitor to your team', true], ['ticket', 'Open a support ticket for a real problem', false],
    ['slots', 'Read your free appointment slots', false], ['book', 'Book one free slot for the visitor', false]];
  const LANGS = [['auto', "The customer's language"], ['en', 'English'], ['hi', 'Hindi'], ['mr', 'Marathi'], ['gu', 'Gujarati'],
    ['ta', 'Tamil'], ['te', 'Telugu'], ['kn', 'Kannada'], ['ml', 'Malayalam'], ['bn', 'Bengali'], ['pa', 'Punjabi']];
  const OUTCOMES = ['answered', 'annotated', 'model', 'unknown', 'refused', 'action', 'cap', 'paused', 'error'];
  const OUT_WORD = {answered: 'From your knowledge base', annotated: 'Your approved answer', model: 'Written from your facts',
    unknown: 'Passed to your team', refused: 'Refused (safety)', action: 'Did something', cap: 'Over the cost cap',
    paused: 'Paused', error: 'Error'};
  const TABS = [['settings', 'Settings'], ['preview', 'Preview'], ['channels', 'Channels'], ['logs', 'Logs'],
    ['numbers', 'Numbers'], ['versions', 'Versions']];
  let ROOT = null, VIEWN = 'list', APP = null, TAB = 'settings', PREV_SID = '', SEQ = 0, PLAN = null;

  /* ---------------------------------------------------------------- tiny DOM helpers (textContent only) */
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = String(v);
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else if (k === 'value') el.value = v;
      else if (k === 'checked' || k === 'disabled' || k === 'hidden' || k === 'selected') el[k] = !!v;
      else el.setAttribute(k, v === true ? '' : String(v));
    }
    for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) el.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return el;
  }
  const list = r => Array.isArray(r) ? r : (r && (r.items || r.apps || r.templates || r.keys || r.versions || r.gaps || r.logs)) || [];
  const btn = (text, on, cls = 'btn soft', extra = {}) => h('button', {type: 'button', class: cls, onclick: on, ...extra}, text);
  const chip = (text, cls = '') => h('span', {class: 'tag aia-chip ' + cls}, text);
  const stateChip = a => a.status === 'live' ? chip('Live', 'ok') : a.status === 'paused' ? chip('Paused', 'warn') : chip('Draft');
  const field = (label, input, hint) => h('label', {class: 'aia-field'}, h('span', {class: 'aia-lab'}, label), input,
    hint ? h('span', {class: 'aia-hint faint'}, hint) : null);
  const lines = t => String(t || '').split('\n').map(x => x.trim()).filter(Boolean);
  const say = (e, fallback) => toast((e && e.message) || fallback || 'Something went wrong', true);
  function copy(text) {
    try { navigator.clipboard.writeText(text).then(() => toast('Copied')); } catch { toast('Copy it by hand', true); }
  }
  function mount(...kids) { if (!ROOT) return; ROOT.replaceChildren(h('div', {class: 'aia'}, ...kids)); }
  function busy(el, on) { if (el) { el.disabled = !!on; el.classList.toggle('aia-busy', !!on); } }

  /* a small dialog for HER taps (publish / restore / delete): the exact thing that will happen is written out */
  function ask({title, body, okText = 'Confirm', danger = false, input = null}) {
    return new Promise(res => {
      const box = h('div', {class: 'aia-dlgbg', role: 'dialog', 'aria-modal': 'true', 'aria-label': title});
      const inp = input ? h('input', {class: 'aia-in', placeholder: input, 'aria-label': input}) : null;
      const close = v => { box.remove(); res(v); };
      box.append(h('div', {class: 'aia-dlg'}, h('h3', {text: title}), ...(Array.isArray(body) ? body : [body]).map(b => h('p', {class: 'muted', text: b})),
        inp, h('div', {class: 'aia-row aia-end'}, btn('Cancel', () => close(null)),
          btn(okText, () => close(inp ? inp.value : true), danger ? 'btn go aia-danger' : 'btn go'))));
      box.addEventListener('keydown', e => { if (e.key === 'Escape') close(null); });
      document.body.append(box);
      (inp || box.querySelector('.btn.go')).focus();
    });
  }

  /* ---------------------------------------------------------------- list */
  async function drawList() {
    VIEWN = 'list'; APP = null;
    const n = ++SEQ;
    const grid = h('div', {class: 'aia-grid'}, h('p', {class: 'faint', text: 'Loading your AI apps…'}));
    mount(h('div', {class: 'aia-head'}, h('div', {}, h('h1', {text: 'AI Apps'}),
        h('p', {class: 'muted', text: 'AIs that answer your customers - on a chat page, a website bubble, your business WhatsApp, an API or MCP. They answer only from your facts and your approved answers, and nothing goes live without your tap.'})),
      h('div', {class: 'aia-row'}, btn('Templates', drawTemplates), btn('New AI app', drawNew, 'btn go'))), grid);
    let apps = [];
    try { apps = list(await api('GET', B)); } catch (e) { if (n === SEQ) grid.replaceChildren(h('p', {class: 'aia-err', text: e.message || 'Could not load your AI apps.'})); return; }
    if (n !== SEQ) return;
    if (!apps.length) {
      grid.replaceChildren(h('div', {class: 'aia-empty'}, h('h3', {text: 'No AI app yet'}),
        h('p', {class: 'muted', text: 'Describe your business in one line and Hoola drafts the AI for you to check, try and publish.'}),
        h('div', {class: 'aia-row'}, btn('Start from one line', drawNew, 'btn go'), btn('Browse templates', drawTemplates))));
      return;
    }
    grid.replaceChildren(...apps.map(a => h('button', {type: 'button', class: 'aia-card', onclick: () => openApp(a.id)},
      h('div', {class: 'aia-row aia-between'}, h('b', {class: 'aia-name', text: a.name || 'AI app'}), stateChip(a)),
      h('span', {class: 'faint', text: `${a.kind === 'form' ? 'Form' : 'Chat'} · ${a.live_version ? 'version ' + a.live_version + ' live' : 'never published'}`}),
      a.changed_since_live ? h('span', {class: 'aia-warn', text: 'The draft has changes that are not live yet'}) : null)));
  }

  /* ---------------------------------------------------------------- new: one line -> plan -> create */
  function drawNew() {
    VIEWN = 'new'; SEQ++;
    const words = h('textarea', {class: 'aia-in aia-big', rows: 3, placeholder: 'e.g. My kirana shop in Pune: answer timings, delivery and what we stock; open a ticket for complaints', 'aria-label': 'Your business in one line'});
    const out = h('div', {class: 'aia-plan'});
    const go = btn('Plan it', async () => {
      const w = words.value.trim();
      if (!w) { toast('Write one line about your business first', true); return; }
      busy(go, true); out.replaceChildren(h('p', {class: 'faint', text: 'Hoola is drafting the AI and checking it…'}));
      try { PLAN = await api('POST', `${B}/plan`, {words: w}); drawPlan(out); }
      catch (e) { out.replaceChildren(h('p', {class: 'aia-err', text: e.message || 'Could not plan it.'})); }
      finally { busy(go, false); }
    }, 'btn go');
    mount(h('div', {class: 'aia-head'}, h('div', {}, btn('← AI Apps', drawList, 'btn soft aia-back'), h('h1', {text: 'New AI app'}),
      h('p', {class: 'muted', text: 'One line is enough. Hoola drafts it, the checker says what is missing, and nothing is saved until you press Create.'}))),
      h('div', {class: 'aia-panel'}, field('Your business and what the AI should do', words), h('div', {class: 'aia-row'}, go,
        btn('Start blank instead', async () => {
          try { const a = await api('POST', B, {name: 'My assistant', kind: 'chat'}); openApp(a.id); } catch (e) { say(e); }
        }))), out);
    words.focus();
  }
  function drawPlan(out) {
    const p = PLAN || {}, s = p.soul || {};
    const errs = p.errors || [], warns = p.warnings || [], qs = p.questions || [];
    const name = h('input', {class: 'aia-in', value: s.name || '', 'aria-label': 'Name'});
    const create = btn('Create the draft', async () => {
      busy(create, true);
      try { const a = await api('POST', B, {name: name.value.trim() || s.name || 'My assistant', kind: s.kind || 'chat', soul: {...s, name: name.value.trim() || s.name}});
        toast('Saved as a draft - nothing is live yet'); openApp(a.id); }
      catch (e) { say(e); } finally { busy(create, false); }
    }, 'btn go');
    out.replaceChildren(h('div', {class: 'aia-panel'},
      p.says ? h('p', {class: 'muted', text: p.says}) : null,
      field('Name', name),
      s.about ? h('div', {class: 'aia-kv'}, h('b', {text: 'About'}), h('span', {text: s.about})) : null,
      (s.facts || []).length ? h('div', {class: 'aia-kv'}, h('b', {text: 'Facts it may state'}), h('ul', {}, ...(s.facts || []).map(f => h('li', {text: f})))) : null,
      h('div', {class: 'aia-kv'}, h('b', {text: 'What it may do'}), h('span', {text: (s.actions || []).map(a => (ACTIONS.find(x => x[0] === a) || [a, a])[1]).join(' · ') || 'Pass visitors to your team'})),
      (s.refuse || []).length ? h('div', {class: 'aia-kv'}, h('b', {text: 'Always passed to your team'}), h('span', {text: s.refuse.join(', ')})) : null,
      errs.length ? h('div', {class: 'aia-box bad'}, h('b', {text: 'Must be fixed before it can go live'}), h('ul', {}, ...errs.map(x => h('li', {text: x})))) : null,
      warns.length ? h('div', {class: 'aia-box warn'}, h('b', {text: 'Worth a look'}), h('ul', {}, ...warns.map(x => h('li', {text: x})))) : null,
      qs.length ? h('div', {class: 'aia-box'}, h('b', {text: 'Hoola needs to know'}), h('ul', {}, ...qs.map(x => h('li', {text: typeof x === 'string' ? x : (x.question || x.q || JSON.stringify(x))})))) : null,
      h('div', {class: 'aia-row'}, create)));
  }

  /* ---------------------------------------------------------------- one app */
  async function openApp(id, tab) {
    VIEWN = 'app'; TAB = tab || 'settings'; PREV_SID = '';
    const n = ++SEQ;
    mount(h('p', {class: 'faint', text: 'Opening…'}));
    try { APP = await api('GET', `${B}/${q(id)}`); } catch (e) { if (n === SEQ) { say(e, 'Could not open this AI app'); drawList(); } return; }
    if (n !== SEQ) return;
    drawApp();
  }
  async function reload() { try { APP = await api('GET', `${B}/${q(APP.id)}`); } catch (e) { say(e); } drawApp(); }
  function drawApp() {
    const a = APP;
    const body = h('div', {class: 'aia-body'});
    const pub = btn(a.live_version ? 'Publish changes' : 'Publish', publish, 'btn go', {disabled: a.live_version && !a.changed_since_live});
    const pause = a.live_version ? btn(a.status === 'paused' ? 'Resume' : 'Pause', () => setStatus(a.status === 'paused' ? 'live' : 'paused')) : null;
    mount(h('div', {class: 'aia-head'},
      h('div', {}, btn('← AI Apps', drawList, 'btn soft aia-back'), h('div', {class: 'aia-row'}, h('h1', {text: a.name || 'AI app'}), stateChip(a)),
        h('p', {class: 'faint', text: a.live_version ? `Version ${a.live_version} is live` + (a.changed_since_live ? ' · the draft has unpublished changes' : '') : 'A draft - customers cannot reach it until you publish'})),
      h('div', {class: 'aia-row'}, pause, pub)),
      h('div', {class: 'aia-tabs', role: 'tablist'}, ...TABS.map(([k, t]) => h('button', {type: 'button', role: 'tab', class: 'aia-tab', 'aria-selected': String(k === TAB),
        onclick: () => { TAB = k; drawApp(); }}, t))), body);
    ({settings: tabSettings, preview: tabPreview, channels: tabChannels, logs: tabLogs, numbers: tabNumbers, versions: tabVersions}[TAB] || tabSettings)(body);
  }
  async function publish() {
    const a = APP;
    const ch = a.check || {};
    if ((ch.errors || []).length) { toast('Fix this first: ' + ch.errors[0], true); TAB = 'settings'; drawApp(); return; }
    const note = await ask({title: `Publish "${a.name}"?`, okText: 'Publish',
      body: [`Customers will be answered by this draft as version ${(a.live_version || 0) + 1}.`, `Draft hash: ${a.draft_hash}`,
        'If the draft changes before you confirm, the server refuses and you check it again.'], input: 'A note for this version (optional)'});
    if (note === null) return;
    try { const r = await api('POST', `${B}/${q(a.id)}/publish`, {hash: a.draft_hash, note: note || ''}); toast((r && r.says) || 'Published'); reload(); }
    catch (e) { say(e); if (e.status === 409) reload(); }
  }
  async function setStatus(status) {
    try { await api('POST', `${B}/${q(APP.id)}/status`, {status}); toast(status === 'paused' ? 'Paused on every channel' : 'Live again'); reload(); }
    catch (e) { say(e); }
  }

  /* -------- Settings: the soul fields */
  function tabSettings(body) {
    const s = APP.draft || {};
    const lim = s.limits || {};
    const f = {
      name: h('input', {class: 'aia-in', value: s.name || '', maxlength: 80}),
      kind: h('select', {class: 'aia-in'}, h('option', {value: 'chat', selected: s.kind !== 'form'}, 'Chat'), h('option', {value: 'form', selected: s.kind === 'form'}, 'Form')),
      about: h('textarea', {class: 'aia-in', rows: 4, maxlength: 2000, value: s.about || ''}),
      persona: h('input', {class: 'aia-in', maxlength: 600, value: s.persona || ''}),
      facts: h('textarea', {class: 'aia-in', rows: 7, value: (s.facts || []).join('\n')}),
      opening: h('input', {class: 'aia-in', maxlength: 400, value: s.opening || ''}),
      suggested: h('textarea', {class: 'aia-in', rows: 3, value: (s.suggested || []).join('\n')}),
      refuse: h('textarea', {class: 'aia-in', rows: 3, value: (s.refuse || []).join('\n')}),
      language: h('select', {class: 'aia-in'}, ...LANGS.map(([k, t]) => h('option', {value: k, selected: (s.language || 'auto') === k}, t))),
      cap: h('input', {class: 'aia-in', type: 'number', min: '1', step: '1', value: String(lim.monthly_cap_inr ?? 500)}),
      notice: h('textarea', {class: 'aia-in', rows: 2, maxlength: 400, value: s.notice || ''}),
    };
    const acts = ACTIONS.map(([k, t, always]) => h('label', {class: 'aia-check'},
      h('input', {type: 'checkbox', value: k, checked: always || (s.actions || []).includes(k), disabled: always}), h('span', {}, h('b', {text: k}), ' - ' + t)));
    const ch = APP.check || {};
    const status = h('div', {class: 'aia-status'});
    const showCheck = c => status.replaceChildren(...[
      (c.errors || []).length ? h('div', {class: 'aia-box bad'}, h('b', {text: 'Must be fixed before publishing'}), h('ul', {}, ...c.errors.map(x => h('li', {text: x})))) : h('p', {class: 'aia-ok', text: 'The checker found nothing that blocks publishing.'}),
      (c.warnings || []).length ? h('div', {class: 'aia-box warn'}, h('b', {text: 'Worth a look'}), h('ul', {}, ...c.warnings.map(x => h('li', {text: x})))) : null].filter(Boolean));   // a null child would print the word 'null'
    showCheck(ch);
    const save = btn('Save draft', async () => {
      const soul = {...s, name: f.name.value.trim(), kind: f.kind.value, about: f.about.value, persona: f.persona.value,
        facts: lines(f.facts.value), opening: f.opening.value, suggested: lines(f.suggested.value), refuse: lines(f.refuse.value),
        language: f.language.value, notice: f.notice.value,
        actions: acts.map(l => l.querySelector('input')).filter(i => i.checked).map(i => i.value),
        limits: {...lim, monthly_cap_inr: Number(f.cap.value) || 0}};
      busy(save, true);
      try { const r = await api('PUT', `${B}/${q(APP.id)}/draft`, {soul}); APP = {...APP, ...r, check: {errors: r.errors || [], warnings: r.warnings || []}};
        toast('Draft saved - customers still see the live version'); drawApp(); }
      catch (e) { say(e); } finally { busy(save, false); }
    }, 'btn go');
    const del = btn('Delete this AI app', async () => {
      const ok = await ask({title: `Delete "${APP.name}"?`, body: ['The app, its versions, its keys and its logs are deleted. Its link stops answering.'], okText: 'Delete', danger: true});
      if (!ok) return;
      try { await api('DELETE', `${B}/${q(APP.id)}`); toast('Deleted'); drawList(); } catch (e) { say(e); }
    }, 'btn soft aia-dangerline');
    body.append(h('div', {class: 'aia-panel'}, status,
      h('div', {class: 'aia-two'}, field('Name', f.name), field('Kind', f.kind)),
      field('About the business', f.about, 'In your words. The AI may describe the business only from this.'),
      field('How it talks', f.persona, 'e.g. Warm and short, like the shop owner.'),
      field('Facts it may state (one per line)', f.facts, 'Prices, timings, dates and numbers only from here - a reply with any other number is thrown away.'),
      h('div', {class: 'aia-field'}, h('span', {class: 'aia-lab', text: 'What it may do'}), ...acts,
        h('span', {class: 'aia-hint faint', text: 'An AI app can never take or send money, message anyone else or change your prices.'})),
      h('div', {class: 'aia-two'}, field('First message', f.opening), field('Language', f.language)),
      field('Suggested questions (one per line)', f.suggested),
      field('Always pass to your team (topics, one per line)', f.refuse, 'e.g. discounts, credit, medical advice'),
      h('div', {class: 'aia-two'}, field('Monthly cost cap (Rs)', f.cap, 'Over the cap no model is called; visitors are passed to your team.'), field('Notice shown before the first message', f.notice)),
      h('div', {class: 'aia-row aia-between'}, del, save)));
  }

  /* -------- Preview: a private chat on the DRAFT */
  function tabPreview(body) {
    const log = h('div', {class: 'aia-chat', 'aria-live': 'polite'});
    const s = APP.draft || {};
    if (s.opening) log.append(h('div', {class: 'aia-msg bot'}, h('span', {text: s.opening})));
    const inp = h('input', {class: 'aia-in', placeholder: 'Ask what a customer would ask', 'aria-label': 'Preview question'});
    const send = async text => {
      text = String(text || inp.value).trim(); if (!text) return;
      inp.value = ''; log.append(h('div', {class: 'aia-msg me'}, h('span', {text})));
      const wait = h('div', {class: 'aia-msg bot faint'}, h('span', {text: '…'})); log.append(wait); log.scrollTop = log.scrollHeight;
      try {
        const r = await api('POST', `${B}/${q(APP.id)}/preview`, {text, session_id: PREV_SID || undefined});
        if (r && r.session_id) PREV_SID = r.session_id;
        wait.replaceWith(h('div', {class: 'aia-msg bot'}, h('span', {text: (r && r.reply) || ''}),
          h('span', {class: 'aia-meta'}, chip(OUT_WORD[r && r.outcome] || (r && r.outcome) || '', r && (r.outcome === 'refused' || r.outcome === 'error') ? 'bad' : r && r.outcome === 'unknown' ? 'warn' : 'ok'),
            ...((r && r.sources) || []).filter(x => x && x.title).map(x => h('span', {class: 'faint', text: 'Source: ' + x.title})))));
      } catch (e) { wait.replaceWith(h('div', {class: 'aia-msg bot aia-err'}, h('span', {text: e.message || 'Could not answer'}))); }
      log.scrollTop = log.scrollHeight;
    };
    inp.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); send(); } });
    body.append(h('div', {class: 'aia-panel'},
      h('p', {class: 'muted', text: 'This is the DRAFT answering on a private preview - no customer sees it. Try the questions your customers ask, and the tricky ones.'}),
      (s.suggested || []).length ? h('div', {class: 'aia-row aia-wrap'}, ...s.suggested.map(x => btn(x, () => send(x), 'btn soft aia-sug'))) : null,
      log, h('div', {class: 'aia-row'}, inp, btn('Send', () => send(), 'btn go'), btn('New conversation', () => { PREV_SID = ''; TAB = 'preview'; drawApp(); }))));
    inp.focus();
  }

  /* -------- Channels: link + QR, embed, API keys, MCP, WhatsApp */
  function tabChannels(body) {
    const a = APP, ch = a.channels || {};
    const base = location.origin;
    const link = `${base}/ai/${a.code}`;
    const embed = `<script src="${base}/ai/${a.code}/embed.js"></script>`;
    const mcp = `${base}/mcp/aiapp/${a.code}`;
    const tog = k => h('input', {type: 'checkbox', checked: !!ch[k], 'aria-label': k});
    const t = {page: tog('page'), embed: tog('embed'), api: tog('api'), mcp: tog('mcp')};
    const wa = h('input', {class: 'aia-in', value: ch.whatsapp || '', placeholder: 'Phone number id of your business WhatsApp', 'aria-label': 'WhatsApp phone number id', maxlength: 40});
    const qr = h('img', {class: 'aia-qr', alt: 'QR code for the chat page'});
    try { const c = window.qrcode(0, 'M'); c.addData(link); c.make(); qr.src = c.createDataURL(4, 2); } catch { qr.hidden = true; }
    const saveCh = btn('Save channels', async () => {
      try { const r = await api('POST', `${B}/${q(a.id)}/channels`, {page: t.page.checked, embed: t.embed.checked, api: t.api.checked, mcp: t.mcp.checked, whatsapp: wa.value.trim()});
        APP = {...APP, ...(r || {})}; toast('Channels saved'); } catch (e) { say(e); }
    }, 'btn go');
    const keysBox = h('div', {class: 'aia-keys'}, h('p', {class: 'faint', text: 'Loading keys…'}));
    const notLive = a.status !== 'live' ? h('div', {class: 'aia-box warn'}, h('b', {text: a.live_version ? 'Paused' : 'Not published yet'}),
      h('p', {text: 'Every channel below answers only while the app is live.'})) : null;
    const row = (k, title, what, extra) => h('div', {class: 'aia-chan'}, h('label', {class: 'aia-check'}, t[k], h('span', {}, h('b', {text: title}), ' - ' + what)), extra);
    body.append(h('div', {class: 'aia-panel'}, notLive,
      row('page', 'Chat page', 'a page anyone can open, also from the QR',
        h('div', {class: 'aia-row aia-wrap'}, qr, h('code', {class: 'aia-code', text: link}), btn('Copy link', () => copy(link)), h('a', {class: 'btn soft', href: link, target: '_blank', rel: 'noopener'}, 'Open'))),
      row('embed', 'Website bubble', 'paste this one line before </body> on any website',
        h('div', {class: 'aia-row aia-wrap'}, h('pre', {class: 'aia-code', text: embed}), btn('Copy snippet', () => copy(embed)))),
      row('api', 'API', 'POST /api/aiapp-api/v1/chat with a key from below (Bearer aik_...)', null),
      row('mcp', 'MCP tool', 'other AI tools call this app as an MCP server (a key from below is needed)',
        h('div', {class: 'aia-row aia-wrap'}, h('code', {class: 'aia-code', text: mcp}), btn('Copy', () => copy(mcp)))),
      h('div', {class: 'aia-chan'}, field('Business WhatsApp', wa, 'Your Employee WhatsApp number id. Customers who message it are answered by this app (24 h window, STOP and your takeover unchanged). Empty = off.')),
      h('div', {class: 'aia-row aia-end'}, saveCh)),
      h('div', {class: 'aia-panel'}, h('h3', {text: 'API keys'}), h('p', {class: 'muted', text: 'For the API and MCP channels. A key is shown ONCE when it is made; only its last 4 characters are kept to tell keys apart.'}), keysBox));
    drawKeys(keysBox);
  }
  async function drawKeys(box) {
    const name = h('input', {class: 'aia-in', placeholder: 'Key name, e.g. My website', 'aria-label': 'Key name', maxlength: 80});
    const rpm = h('input', {class: 'aia-in aia-num', type: 'number', min: '1', value: '20', 'aria-label': 'Calls a minute'});
    const rph = h('input', {class: 'aia-in aia-num', type: 'number', min: '1', value: '300', 'aria-label': 'Calls an hour'});
    const conc = h('input', {class: 'aia-in aia-num', type: 'number', min: '1', value: '2', 'aria-label': 'At the same time'});
    const shown = h('div', {});
    const make = btn('Make a key', async () => {
      busy(make, true);
      try {
        const r = await api('POST', `${B}/${q(APP.id)}/keys`, {name: name.value.trim() || 'Key', rpm: +rpm.value || 20, rph: +rph.value || 300, concurrent: +conc.value || 2});
        const key = (r && (r.key || r.secret || r.token)) || '';
        shown.replaceChildren(h('div', {class: 'aia-box ok'}, h('b', {text: 'Copy it now - it is shown only once'}),
          h('div', {class: 'aia-row aia-wrap'}, h('code', {class: 'aia-code', text: key}), btn('Copy key', () => copy(key)))));
        name.value = ''; await fill();
      } catch (e) { say(e); } finally { busy(make, false); }
    }, 'btn go');
    const listEl = h('div', {class: 'aia-list'});
    async function fill() {
      let keys = [];
      try { keys = list(await api('GET', `${B}/${q(APP.id)}/keys`)); } catch (e) { listEl.replaceChildren(h('p', {class: 'aia-err', text: e.message || 'Could not load keys'})); return; }
      listEl.replaceChildren(...(keys.length ? keys.map(k => h('div', {class: 'aia-item'},
        h('div', {}, h('b', {text: k.name || 'Key'}), h('span', {class: 'faint', text: ` …${k.tail || ''} · ${k.rpm ?? '?'}/min · ${k.rph ?? '?'}/hour · ${k.concurrent ?? '?'} at once`})),
        btn('Revoke', async () => {
          const ok = await ask({title: `Revoke "${k.name || 'key'}"?`, body: ['Anything using this key stops working at once.'], okText: 'Revoke', danger: true});
          if (!ok) return;
          try { await api('DELETE', `${B}/${q(APP.id)}/keys/${q(k.id)}`); toast('Revoked'); fill(); } catch (e) { say(e); }
        }))) : [h('p', {class: 'faint', text: 'No keys yet.'})]));
    }
    box.replaceChildren(shown, h('div', {class: 'aia-row aia-wrap'}, name, field('Per minute', rpm), field('Per hour', rph), field('At once', conc), make), listEl);
    fill();
  }

  /* -------- Logs: what customers asked, Correct this answer */
  function tabLogs(body) {
    const sel = h('select', {class: 'aia-in', 'aria-label': 'Outcome'}, h('option', {value: ''}, 'Every answer'), ...OUTCOMES.map(o => h('option', {value: o}, OUT_WORD[o] || o)));
    const qi = h('input', {class: 'aia-in', placeholder: 'Search the questions', 'aria-label': 'Search'});
    const out = h('div', {class: 'aia-list'});
    const load = async () => {
      out.replaceChildren(h('p', {class: 'faint', text: 'Loading…'}));
      let rows = [];
      try { rows = list(await api('GET', `${B}/${q(APP.id)}/logs?outcome=${q(sel.value)}&q=${q(qi.value.trim())}&limit=50`)); }
      catch (e) { out.replaceChildren(h('p', {class: 'aia-err', text: e.message || 'Could not load the logs'})); return; }
      out.replaceChildren(...(rows.length ? rows.map(logRow) : [h('p', {class: 'faint', text: 'Nothing here yet.'})]));
    };
    sel.addEventListener('change', load);
    qi.addEventListener('keydown', e => { if (e.key === 'Enter') load(); });
    body.append(h('div', {class: 'aia-panel'}, h('p', {class: 'muted', text: 'What customers asked and what the app said. Their words are shown as written (secret numbers masked) - they are data, never instructions. Correct an answer and the same question is answered with your words next time.'}),
      h('div', {class: 'aia-row'}, sel, qi, btn('Search', load)), out));
    load();
  }
  function logRow(m) {
    const fixBox = h('div', {class: 'aia-fix', hidden: true});
    const ta = h('textarea', {class: 'aia-in', rows: 3, placeholder: 'Your answer to this question', 'aria-label': 'Corrected answer'});
    const saveFix = btn('Save as my answer', async () => {
      const ans = ta.value.trim(); if (!ans) { toast('Write the answer first', true); return; }
      busy(saveFix, true);
      try { await api('POST', `${B}/${q(APP.id)}/logs/${q(m.id)}/correct`, {answer: ans}); toast('Saved - this question now gets your answer');
        fixBox.replaceChildren(h('p', {class: 'aia-ok', text: 'Corrected. Next time: ' + ans})); }
      catch (e) { say(e); } finally { busy(saveFix, false); }
    }, 'btn go');
    fixBox.append(ta, h('div', {class: 'aia-row'}, saveFix));
    const bad = m.outcome === 'refused' || m.outcome === 'error';
    return h('div', {class: 'aia-item aia-log'},
      h('div', {class: 'aia-row aia-between'}, h('span', {class: 'faint', text: [m.channel, (m.at || m.created || '').replace('T', ' ').slice(0, 16)].filter(Boolean).join(' · ')}),
        chip(OUT_WORD[m.outcome] || m.outcome || '', bad ? 'bad' : m.outcome === 'unknown' || m.outcome === 'cap' ? 'warn' : 'ok')),
      h('p', {class: 'aia-q', text: m.question || m.q || ''}), h('p', {class: 'aia-a', text: m.answer || m.a || ''}),
      m.corrected ? h('span', {class: 'aia-ok', text: 'Corrected by you'}) : btn('Correct this answer', () => { fixBox.hidden = !fixBox.hidden; if (!fixBox.hidden) ta.focus(); }),
      fixBox);
  }

  /* -------- Numbers: stats + gaps */
  function tabNumbers(body) {
    const days = h('select', {class: 'aia-in', 'aria-label': 'Period'}, ...[[7, 'Last 7 days'], [30, 'Last 30 days'], [90, 'Last 90 days']].map(([d, t]) => h('option', {value: String(d), selected: d === 30}, t)));
    const tiles = h('div', {class: 'aia-tiles'});
    const gaps = h('div', {class: 'aia-list'});
    const WORD = {messages: 'Messages', sessions: 'Conversations', answered_share: 'Answered', unknown: 'Passed to your team', refused: 'Refused',
      actions: 'Actions done', avg_ms: 'Average reply time', inr_month: 'Spent this month', cap_inr: 'Monthly cap', satisfaction: 'Satisfaction'};
    const fmt = (k, v) => typeof v !== 'number' ? String(v) : /share|satisfaction/.test(k) && v <= 1 ? Math.round(v * 100) + '%'
      : /inr|cap/.test(k) ? 'Rs ' + v.toLocaleString('en-IN', {maximumFractionDigits: 2}) : /ms$/.test(k) ? (v / 1000).toFixed(1) + ' s' : v.toLocaleString('en-IN');
    const load = async () => {
      tiles.replaceChildren(h('p', {class: 'faint', text: 'Counting…'}));
      try {
        const st = await api('GET', `${B}/${q(APP.id)}/stats?days=${q(days.value)}`) || {};
        const tot = st.totals && typeof st.totals === 'object' ? st.totals : st;   // the stats route answers {totals, per_day, says}
        const flat = Object.entries(tot).filter(([k, v]) => (typeof v === 'number' || (k === 'satisfaction' && v === null)) && k in WORD)
          .map(([k, v]) => [k, v === null ? 'No ratings yet' : v]);
        if (st.says) flat.unshift(['__says', st.says]);
        tiles.replaceChildren(...(flat.length ? flat.map(([k, v]) => k === '__says' ? h('p', {class: 'aia-says', text: v}) : h('div', {class: 'aia-tile'}, h('span', {class: 'faint', text: WORD[k] || k.replace(/_/g, ' ')}), h('b', {text: fmt(k, v)})))
          : [h('p', {class: 'faint', text: 'No numbers yet.'})]));
      } catch (e) { tiles.replaceChildren(h('p', {class: 'aia-err', text: e.message || 'Could not count'})); }
      try {
        const g = list(await api('GET', `${B}/${q(APP.id)}/gaps`));
        gaps.replaceChildren(...(g.length ? g.map(x => h('div', {class: 'aia-item'}, h('span', {text: x.question || x.q || x.text || ''}),
          h('span', {class: 'faint', text: x.count ? `asked ${x.count} time${x.count === 1 ? '' : 's'}` : ''}))) : [h('p', {class: 'faint', text: 'No unanswered questions - nice.'})]));
      } catch (e) { gaps.replaceChildren(h('p', {class: 'aia-err', text: e.message || 'Could not load the gaps'})); }
    };
    days.addEventListener('change', load);
    body.append(h('div', {class: 'aia-panel'}, h('div', {class: 'aia-row aia-between'}, h('h3', {text: 'Numbers'}), days), tiles),
      h('div', {class: 'aia-panel'}, h('h3', {text: 'Questions it could not answer'}), h('p', {class: 'muted', text: 'Add a fact or an approved answer for the ones that keep coming back.'}), gaps));
    load();
  }

  /* -------- Versions: Restore (her tap) */
  async function tabVersions(body) {
    const out = h('div', {class: 'aia-list'}, h('p', {class: 'faint', text: 'Loading…'}));
    body.append(h('div', {class: 'aia-panel'}, h('p', {class: 'muted', text: 'Every publish is kept as it was. Restoring publishes an old version again as the newest one; nothing is rewritten.'}), out));
    let vs = [];
    try { vs = list(await api('GET', `${B}/${q(APP.id)}/versions`)); } catch (e) { out.replaceChildren(h('p', {class: 'aia-err', text: e.message || 'Could not load versions'})); return; }
    out.replaceChildren(...(vs.length ? vs.map(v => h('div', {class: 'aia-item'},
      h('div', {}, h('b', {text: `Version ${v.version}`}), v.live ? chip('Live', 'ok') : null,
        h('span', {class: 'faint', text: ` · ${v.op || 'publish'} · ${(v.at || '').replace('T', ' ').slice(0, 16)}${v.note ? ' · ' + v.note : ''}`})),
      v.live ? null : btn('Restore', async () => {
        const ok = await ask({title: `Restore version ${v.version}?`, okText: 'Restore',
          body: [`Version ${v.version} goes live again as a new version, and becomes your draft. Hash: ${v.hash}`]});
        if (!ok) return;
        try { const r = await api('POST', `${B}/${q(APP.id)}/restore`, {version: v.version}); toast((r && r.says) || 'Restored'); TAB = 'versions'; reload(); }
        catch (e) { say(e); }
      }))) : [h('p', {class: 'faint', text: 'Not published yet.'})]));
  }

  /* ---------------------------------------------------------------- templates */
  async function drawTemplates() {
    VIEWN = 'templates';
    const n = ++SEQ;
    const search = h('input', {class: 'aia-in', placeholder: 'Search by trade, e.g. clinic, salon, kirana', 'aria-label': 'Search templates'});
    const grid = h('div', {class: 'aia-grid'});
    const load = async () => {
      grid.replaceChildren(h('p', {class: 'faint', text: 'Loading…'}));
      let ts = [];
      try { ts = list(await api('GET', `${B}/templates?q=${q(search.value.trim())}`)); }
      catch (e) { if (n === SEQ) grid.replaceChildren(h('p', {class: 'aia-err', text: e.message || 'Could not load templates'})); return; }
      grid.replaceChildren(...(ts.length ? ts.map(tplCard) : [h('p', {class: 'faint', text: 'No template matches.'})]));
    };
    search.addEventListener('keydown', e => { if (e.key === 'Enter') load(); });
    mount(h('div', {class: 'aia-head'}, h('div', {}, btn('← AI Apps', drawList, 'btn soft aia-back'), h('h1', {text: 'Templates'}),
      h('p', {class: 'muted', text: 'Ready AI apps by trade. Try one first (nothing is saved), then Use it and fill in your own facts.'}))),
      h('div', {class: 'aia-row'}, search, btn('Search', load)), grid);
    load();
  }
  function tplCard(t) {
    const out = h('div', {class: 'aia-trial'});
    const inp = h('input', {class: 'aia-in', placeholder: (t.sample_questions || [])[0] || 'Ask what a customer would ask', 'aria-label': 'Trial question'});
    const trial = async text => {
      text = String(text || inp.value || (t.sample_questions || [])[0] || '').trim(); if (!text) return;
      out.replaceChildren(h('p', {class: 'faint', text: '…'}));
      try { const r = await api('POST', `${B}/templates/${q(t.key)}/trial`, {text});
        out.replaceChildren(h('p', {class: 'aia-q', text}), h('p', {class: 'aia-a', text: (r && r.reply) || ''}), r && r.outcome ? chip(OUT_WORD[r.outcome] || r.outcome) : null); }
      catch (e) { out.replaceChildren(h('p', {class: 'aia-err', text: e.message || 'Could not try it'})); }
    };
    inp.addEventListener('keydown', e => { if (e.key === 'Enter') trial(); });
    return h('div', {class: 'aia-card aia-tpl'},
      h('div', {class: 'aia-row aia-between'}, h('b', {class: 'aia-name', text: t.name || t.key}), t.trade ? chip(t.trade) : null),
      t.about ? h('p', {class: 'muted', text: t.about}) : null,
      (t.actions || []).length ? h('span', {class: 'faint', text: 'Can: ' + t.actions.join(', ')}) : null,
      (t.sample_questions || []).length ? h('div', {class: 'aia-row aia-wrap'}, ...t.sample_questions.slice(0, 3).map(x => btn(x, () => trial(x), 'btn soft aia-sug'))) : null,
      h('div', {class: 'aia-row'}, inp, btn('Try', () => trial())), out,
      h('div', {class: 'aia-row aia-end'}, btn('Use this template', async () => {
        const name = await ask({title: `Use "${t.name || t.key}"`, body: ['A draft copy is made for you; nothing is live until you publish.'], okText: 'Create draft', input: 'Name for your AI app'});
        if (name === null) return;
        try { const a = await api('POST', `${B}/templates/${q(t.key)}/use`, {name: name || t.name || ''}); toast('Draft created'); openApp(a.id); }
        catch (e) { say(e); }
      }, 'btn go')));
  }

  /* ---------------------------------------------------------------- the page contract (v2.js go()) */
  /* its own stylesheet, loaded once on first open (v2.html keeps its one stylesheet), stamped like this script */
  function sheet() {
    if (document.getElementById('aia-css')) return;
    const me = [...document.scripts].find(x => /console\/aiapps\.js/.test(x.src));
    const v = me ? (me.src.split('?v=')[1] || '') : '';
    document.head.append(h('link', {id: 'aia-css', rel: 'stylesheet', href: '/static/console/aiapps.css' + (v ? '?v=' + v : '')}));
  }
  return {
    open(el, arg) {
      sheet();
      ROOT = el;
      if (arg) openApp(arg); else if (VIEWN === 'app' && APP) drawApp(); else if (VIEWN === 'templates') drawTemplates(); else drawList();
    },
    leave() { SEQ++; document.querySelectorAll('.aia-dlgbg').forEach(x => x.remove()); },
  };
};
