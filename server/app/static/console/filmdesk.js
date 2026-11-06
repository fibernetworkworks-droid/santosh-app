/* v0.565 FILM DESK (console) - the producer's page over /api/filmdesk/*: script coverage, previs, schedule, money (budget, waterfall,
   royalties), sales (festivals, windows) and delivery (deliverables, localisation) for one film at a time.

   Rules this page keeps (they are the server's rules, drawn):
   - every number here was either COUNTED from her script / shot list or TYPED by her; a rate, fee, deadline, holdback or guild term is
     never filled in for her, and the royalty form insists on the contract clause it came from;
   - 'heuristic' flags are drawn as hints, not as findings, and coverage never shows a reader's verdict;
   - nothing here sends, submits, signs or pays: messages and release are cards for her tap on the phone or in chat;
   - every value that came from the server goes through esc() - a script line, a festival name or a note is data, never markup. */
'use strict';
window.HoolaFilmDesk = function ({api, esc, toast}) {
  let EL = null, FILMS = [], REF = '', TAB = 'coverage';
  const TABS = [['coverage', 'Script'], ['previs', 'Shots'], ['schedule', 'Schedule'], ['money', 'Money'], ['sales', 'Sales'], ['delivery', 'Delivery']];
  const inr = n => n == null || n === '' ? '–' : '₹' + Number(n).toLocaleString('en-IN', {maximumFractionDigits: 2});
  const IN = 'border:1px solid var(--hair);border-radius:10px;padding:7px 10px;background:var(--bg);color:var(--ink);min-width:0';
  const H = t => `<h3 style="margin:22px 0 8px;font-size:15px">${esc(t)}</h3>`;
  const note = t => t ? `<p class="muted" style="margin:6px 0">${esc(t)}</p>` : '';
  const flags = (fl, fallback) => {
    if (!fl || !fl.length) return fallback ? `<p class="muted">${esc(fallback)}</p>` : '';
    return `<ul style="margin:6px 0 0 18px;padding:0">${fl.map(f => {
      const o = typeof f === 'string' ? {kind: '', text: f} : f;
      return `<li style="margin:4px 0">${o.kind === 'heuristic' ? '<span class="tag">hint</span> ' : ''}${esc(o.text)}</li>`;
    }).join('')}</ul>`;
  };
  const table = (head, rows) => rows.length
    ? `<div style="overflow-x:auto"><table class="em-tbl"><thead><tr>${head.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`
    : '';
  const stat = (k, v) => `<div style="border:1px solid var(--hair);border-radius:12px;padding:10px 14px;min-width:110px"><div class="muted" style="font-size:12px">${esc(k)}</div><div style="font-size:18px;font-weight:600">${esc(v)}</div></div>`;
  const stats = list => `<div style="display:flex;flex-wrap:wrap;gap:10px;margin:10px 0">${list.map(([k, v]) => stat(k, v)).join('')}</div>`;

  // a small add-row form built from field specs: [key, label, type?, placeholder?]
  function form(id, title, fields, path, ctx = {}) {
    const inputs = fields.map(([k, l, t, ph]) => `<label style="display:flex;flex-direction:column;font-size:12px;gap:3px">${esc(l)}
      ${t === 'select' ? `<select data-k="${k}" style="${IN}">${(ph || []).map(o => `<option value="${esc(o)}">${esc(o || '–')}</option>`).join('')}</select>`
        : `<input data-k="${k}" type="${t === 'date' ? 'date' : t === 'number' ? 'number' : 'text'}" ${t === 'number' ? 'step="any"' : ''} placeholder="${esc(ph || '')}" style="${IN}">`}</label>`).join('');
    return `<details style="margin:10px 0"><summary class="btn soft" style="display:inline-block;cursor:pointer">${esc(title)}</summary>
      <div data-form="${id}" data-path="${esc(path)}" data-ctx='${esc(JSON.stringify(ctx))}' style="display:flex;flex-wrap:wrap;gap:10px;margin-top:10px;align-items:flex-end">${inputs}
      <button class="btn go" data-submit="${id}">Save</button></div></details>`;
  }

  async function load() {
    try { FILMS = (await api('GET', '/api/filmdesk/projects')).projects || []; }
    catch (e) { FILMS = []; EL.innerHTML = `<p class="badc">${esc(e.message)}</p>`; return false; }
    if (!FILMS.find(f => f.number === REF)) REF = FILMS[0] ? FILMS[0].number : '';
    return true;
  }

  async function open(el) {
    EL = el;
    EL.innerHTML = `<div class="vh"><h2>Film Desk</h2></div><div class="empty">Loading…</div>`;
    if (await load()) await draw();
  }

  async function draw() {
    const head = `<div class="vh"><h2>Film Desk</h2><span class="muted">Counts from your script, sums from your own rates. Nothing is sent or paid from here.</span></div>`;
    if (!FILMS.length) { EL.innerHTML = head + `<div class="card"><p>No film yet. Tell Hoola in chat: <i>"Ek short film shuru karo: …"</i> and it shows up here.</p></div>`; return; }
    const sel = `<select id="fdFilm" style="${IN}">${FILMS.map(f => `<option value="${esc(f.number)}" ${f.number === REF ? 'selected' : ''}>${esc(f.number)} · ${esc(f.title)}</option>`).join('')}</select>`;
    const tabs = TABS.map(([k, n]) => `<button class="btn ${k === TAB ? 'go' : 'soft'}" data-fdtab="${k}">${esc(n)}</button>`).join(' ');
    EL.innerHTML = head + `<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:8px 0">${sel}</div><div style="display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 14px">${tabs}</div><div id="fdBody"><div class="empty">Loading…</div></div>`;
    EL.querySelector('#fdFilm').onchange = e => { REF = e.target.value; draw(); };
    EL.querySelectorAll('[data-fdtab]').forEach(b => b.onclick = () => { TAB = b.dataset.fdtab; draw(); });
    const body = EL.querySelector('#fdBody');
    try { body.innerHTML = await PANES[TAB](); } catch (e) { body.innerHTML = `<p class="badc">${esc(e.message)}</p>`; }
    wire(body);
  }

  const U = p => `/api/filmdesk/projects/${encodeURIComponent(REF)}/${p}`;
  const get = async p => api('GET', U(p));

  function wire(body) {
    body.querySelectorAll('[data-submit]').forEach(btn => btn.onclick = async () => {
      const box = btn.closest('[data-form]'), data = JSON.parse(box.dataset.ctx || '{}');
      box.querySelectorAll('[data-k]').forEach(i => { if (String(i.value).trim() !== '') data[i.dataset.k] = i.value.trim(); });
      for (const k of ['rate', 'fee_inr', 'amount_inr', 'net_inr', 'units', 'threshold_inr', 'cap_inr', 'floor_inr', 'gross_inr', 'qa_rounds']) if (k in data) data[k] = Number(data[k]);
      if (data.applies_to) data.applies_to = String(data.applies_to).split(',').map(x => x.trim()).filter(Boolean);
      try { const r = await api('POST', box.dataset.path, data); toast(r.say || 'Saved.'); draw(); }
      catch (e) { toast(e.message, true); }
    });
    body.querySelectorAll('[data-act]').forEach(b => b.onclick = async () => {
      try { const r = await api('POST', b.dataset.path, JSON.parse(b.dataset.body || '{}')); toast(r.say || 'Done.'); draw(); }
      catch (e) { toast(e.message, true); }
    });
  }
  const act = (label, path, body) => `<button class="btn soft" data-act="1" data-path="${esc(path)}" data-body='${esc(JSON.stringify(body || {}))}'>${esc(label)}</button>`;
  const del = (path, op, entry) => act('Remove', path, {op, entry});

  const PANES = {
    async coverage() {
      const c = await get('coverage');
      if (!c.scenes) return `<p class="muted">${esc(c.note || 'No script yet.')}</p>`;
      return stats([['Scenes', c.scenes], ['Est. minutes', c.estimated_minutes], ['Characters', c.characters_n], ['Places', c.places_n],
        ['Company moves', c.company_moves], ['Night scenes', `${c.night_scenes} (${c.night_pct}%)`], ['Dialogue', c.dialogue_pct + '%']])
        + (c.most_dialogue ? note(`Most dialogue: ${c.most_dialogue}. ${c.most_dialogue_note}`) : '')
        + note(Object.entries(c.quarter_marks || {}).map(([k, v]) => `${k} → ${v}`).join(' · ') + ' — ' + (c.script_marks_note || ''))
        + H('Flags') + flags(c.flags, 'Nothing flagged.') + note(c.kind_note)
        + H('Cast') + table(['Name', 'Scenes', 'Lines', 'Words', '% of dialogue', 'Longest speech'],
          c.cast_table.map(x => [esc(x.name), x.scenes_n, x.lines, x.dialogue_words, x.dialogue_pct, x.longest_speech_words]))
        + H('Scenes') + table(['#', 'Heading', 'Place', 'Time', 'Sec', 'Lines'],
          c.scene_table.map(r => [r.n, esc(r.heading), esc(r.place), esc(`${r.int_ext} ${r.time}`), r.seconds, r.dialogue_lines]))
        + H('Word counts (not a rating)') + note(Object.entries(c.theme_hits || {}).map(([k, v]) => `${k}: ${v}`).join(' · ') + ' — ' + (c.theme_note || ''));
    },
    async previs() {
      const v = await get('previs');
      if (!v.shots) return `<p class="muted">${esc(v.note || 'No shots yet.')}</p>`;
      return stats([['Shots', v.shots], ['Total seconds', v.total_seconds], ['Target', v.runtime_target_s ? v.runtime_target_s + ' s' : '–']])
        + H('Flags') + flags(v.flags, 'No problems found in the shot list.')
        + H('Scenes') + table(['#', 'Heading', 'Shots', 'Shot sec', 'Script sec', 'Cameras'],
          v.per_scene.map(r => [r.n, esc(r.heading), r.shots, r.shot_seconds, r.script_seconds, esc(r.cameras.join(', '))]))
        + H('Timeline') + table(['Shot', 'From', 'To', 'Camera', 'Gear'], v.timeline.map(r => [esc(r.id), r.start_s, r.end_s, esc(r.camera), esc(r.gear)]))
        + (v.gear.length ? note('Gear asked by the shots: ' + v.gear.join('; ')) : '') + note(v.note);
    },
    async schedule() {
      let s = null;
      try { s = await api('GET', U('schedule?what=schedule')); } catch (e) { /* no schedule yet */ }
      const mk = form('sch', s ? 'Re-plan the shoot' : 'Plan the shoot', [['start_date', 'Start date', 'date'], ['day_hours', 'Hours a day', 'number', '10'],
        ['setup_hours', 'Set-up hours', 'number', '1'], ['hours_per_screen_minute', 'Hours / screen minute', 'number', '2']], U('schedule'));
      if (!s) return mk + note('Hours are assumptions until you type your own numbers.');
      const d = await api('GET', U('schedule?what=dood')).catch(() => null);
      return mk + stats([['Shoot days', s.days.length], ['Night days', s.days.filter(x => x.part === 'night').length]])
        + flags(s.flags) + table(['Day', 'Date', 'Part', 'Places', 'Scenes', 'Hours'],
          s.days.map(x => [x.order || '', esc(x.date || '[date]'), esc(x.part), esc((x.places || []).join(', ')), (x.scenes || []).length, x.hours]))
        + (d && d.summary ? H('Day-out-of-days') + table(['Who', 'Work days', 'Hold days', 'First', 'Last'], d.summary.map(x => [esc(x.who), x.work_days, x.hold_days, x.first_day, x.last_day])) : '')
        + note('Call sheets are made per day from chat or the phone ("call sheet day 2"); unknown details stay [blank].');
    },
    async money() {
      const [b, w, r] = await Promise.all([api('GET', U('schedule?what=plan_budget')).catch(() => null), api('GET', U('waterfall')).catch(() => null), get('royalties')]);
      const bud = b && b.lines
        ? stats([['Subtotal', inr(b.subtotal_inr)], ['Contingency', b.contingency_inr == null ? '–' : inr(b.contingency_inr)], ['At least', inr(b.total_inr)]])
          + table(['Head', 'Qty', 'Rate', 'Amount'], b.lines.map(l => [esc(l.head || l.key), l.qty, l.rate_inr == null ? 'rate nahi di' : inr(l.rate_inr), l.amount_inr == null ? '–' : inr(l.amount_inr)])) + note(b.note)
        : note('Make a schedule first, then give your rates in chat ("budget plan: crew 8000/day …"). Only your numbers are used.');
      const wf = w && w.tiers ? stats([['Gross', inr(w.gross_inr)], ['Ties to gross', w.ties_to_gross ? 'yes' : 'NO']])
        + table(['Tier', 'Name', 'Amount', 'Left'], w.tiers.map(t => [esc(t.tier), esc(t.name), inr(t.amount_inr), inr(t.left_inr)])) : note('No waterfall calculated yet (chat: "waterfall: gross 5 lakh …").');
      const roy = form('rt', 'Add a contract term', [['party', 'Party'], ['role', 'Role', 'select', ['writer', 'director', 'actor', 'composer', 'lyricist', 'singer', 'musician', 'editor', 'cinematographer', 'other']],
        ['basis', 'Basis', 'select', ['percent_of_gross', 'percent_of_net', 'flat_inr', 'per_unit']], ['rate', 'Rate', 'number'], ['threshold_inr', 'Above ₹', 'number'], ['cap_inr', 'Cap ₹', 'number'],
        ['applies_to', 'Media (comma)', 'text', 'svod, tv or all'], ['source', 'Contract clause (required)']], U('royalties'), {op: 'add'})
        + form('rc', 'Add income received', [['medium', 'Medium', 'select', ['svod', 'avod', 'tvod', 'tv', 'theatrical', 'festival', 'home_video', 'airline', 'educational', 'music', 'other']],
          ['amount_inr', 'Amount ₹', 'number'], ['net_inr', 'Net ₹', 'number'], ['units', 'Units', 'number'], ['period', 'Date', 'date'], ['payer', 'Payer']], U('royalties'), {op: 'receipt'});
      return H('Budget from your rate card') + bud + H('Recoupment waterfall') + wf
        + H('Royalties under your own contract terms') + roy
        + table(['Term', 'Party', 'Basis', 'Rate', 'Source', ''], r.terms.map(t => [esc(t.id), esc(t.party), esc(t.basis), t.rate, esc(t.source), del(U('royalties'), 'remove', t.id)]))
        + table(['Receipt', 'Medium', 'Amount', ''], r.receipts.map(x => [esc(x.id), esc(x.medium), inr(x.amount_inr), del(U('royalties'), 'unreceipt', x.id)]))
        + (r.lines.length ? table(['Party', 'Basis', 'Base', 'Due', 'Note'], r.lines.map(l => [esc(l.party), esc(l.basis), inr(l.gross_base_inr), inr(l.amount_inr), esc(l.problem || (l.capped ? 'capped' : ''))]))
          + stats([['Total due', inr(r.total_inr)], ['Gross receipts', inr(r.gross_receipts_inr)]]) : '') + note(r.note);
    },
    async sales() {
      const [f, w] = await Promise.all([get('festivals'), get('windows')]);
      const ff = form('fs', 'Add a festival', [['name', 'Festival'], ['country', 'Country'], ['deadline', 'Deadline', 'date'], ['event_date', 'Event date', 'date'], ['fee_inr', 'Fee ₹', 'number'],
        ['requires', 'Premiere rule', 'select', ['', 'regional', 'national', 'international', 'world', 'none']]], U('festivals'), {op: 'add'});
      const wf = form('wn', 'Add a release window', [['medium', 'Medium', 'select', ['theatrical', 'festival', 'svod', 'avod', 'tvod', 'tv', 'home_video', 'airline', 'educational', 'other']],
        ['territory', 'Territory', 'text', 'india, uae or world'], ['start', 'Start', 'date'], ['end', 'End', 'date'], ['licensee', 'Licensee']], U('windows'), {op: 'add'});
      return H('Festivals') + ff + flags(f.flags)
        + table(['Festival', 'Deadline', 'Left', 'Status', 'Fee', 'Packet', ''], f.festivals.map(x => [esc(x.name), esc(x.deadline || '–'), x.days_left == null ? '–' : x.days_left, esc(x.status),
          x.fee_inr == null ? '–' : inr(x.fee_inr), x.packet ? `${x.packet.done}/${x.packet.total}` : '', del(U('festivals'), 'remove', x.id)])) + note(f.note)
        + H('Release windows') + wf + (w.check.conflicts.length || w.check.holdback_violations.length ? flags([...w.check.conflicts.map(c => c.why || JSON.stringify(c)), ...w.check.holdback_violations.map(v => v.why)]) : '')
        + table(['Medium', 'Territory', 'Start', 'End', 'Exclusive', ''], w.windows.map(x => [esc(x.medium), esc(x.territory), esc(x.start), esc(x.end || '–'), x.exclusive ? 'yes' : '', del(U('windows'), 'remove', x.id)]))
        + note(w.check.note);
    },
    async delivery() {
      const [d, l] = await Promise.all([get('deliverables'), get('localisation')]);
      const df = form('dl', 'Add a deliverable', [['label', 'Item'], ['buyer', 'Buyer'], ['due', 'Due', 'date']], U('deliverables'), {op: 'add'})
        + act('Add festival starter list', U('deliverables'), {op: 'starter', kind: 'festival'}) + ' ' + act('OTT starter list', U('deliverables'), {op: 'starter', kind: 'ott'});
      const lf = form('lc', 'Add a language', [['language', 'Language'], ['kind', 'Kind', 'select', ['subtitles', 'dub', 'both']], ['dub_mode', 'Dub voice', 'select', ['', 'human', 'ai_voice']],
        ['voice_person', 'Voice person (P-001)'], ['vendor', 'Vendor'], ['due', 'Due', 'date']], U('localisation'), {op: 'add'});
      return H(`Deliverables (${d.done}/${d.total} done)`) + df + flags(d.flags)
        + table(['Item', 'Buyer', 'Due', 'Status', ''], d.deliverables.map(x => [esc(x.label), esc(x.buyer), esc(x.due || '–'), esc(x.status), del(U('deliverables'), 'remove', x.id)])) + note(d.note)
        + H(`Subtitles and dubs (${l.done}/${l.total} done)`) + lf + flags(l.flags)
        + table(['Language', 'Kind', 'Voice', 'Due', 'Status', 'Check', ''], l.localisation.map(x => [esc(x.language), esc(x.kind), esc(x.dub_mode), esc(x.due || '–'), esc(x.status), esc(x.voice_check), del(U('localisation'), 'remove', x.id)])) + note(l.note);
    },
  };
  return {open};
};
