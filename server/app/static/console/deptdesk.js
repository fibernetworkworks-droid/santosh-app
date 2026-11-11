/* v0.799 DESK ROOM (built as 0.796) (console) - one desk per department for the AI employees that had none: Finance & Banking,
   Retail & E-commerce, Health Insurance and Construction & Real Estate (31 live employees whose "Open desk" was a dead
   tap). The server (/api/deskroom, employee/deskroom.py) reads each employee's OWN tool schema into forms, so every
   action the employee knows is here, with the fields that action uses; running one goes through the same tool the chat
   uses, as her, so every guard and card inside the tool stays as it is.

   Rules this page keeps:
   - every value from the server goes through esc(); a result is data, never markup;
   - nothing here sends, pays or files: a tool that needs her tap makes its card in her "Hoola updates" chat, and the
     result says so;
   - CRISP TEXT: only drawings and the running dot move; entrances fill BACKWARDS once; Reduce motion / calm switch all
     motion off for #app. Class prefix `ddk-` (never .live / .top / .tag - the console styles those). */
'use strict';
window.HoolaDeptDesk = function ({api, esc, toast, open, ask, title}) {
  let EL = null, OV = null, D = null, KEY = '', TAB = 'work', ACT = {}, FORM = {}, RES = {}, BUSY = '', Q = '', SEQ = 0, ENTER = '', FRESH = '';
  const ICON = {
    fin: '<path d="M4 19h16M6 16V10M10 16V7M14 16v-5M18 16V5"/>',
    retail: '<path d="M4 9l1.5-5h13L20 9M4 9h16v2a2.5 2.5 0 0 1-5 0 2.5 2.5 0 0 1-5 0 2.5 2.5 0 0 1-5 0zM5 12.5V20h14v-7.5M10 20v-4h4v4"/>',
    health: '<path d="M12 3l7 3v5.5c0 4.3-3 8-7 9.5-4-1.5-7-5.2-7-9.5V6zM12 9v6M9 12h6"/>',
    const: '<path d="M3 21h18M6 21V9h5v12M14 21v-7h4v7M6 9l9-5v3M15 7h5M18 7v3"/>'};
  const ART = {   // hero drawings; every path traces itself once (pathLength 1 + .ddk-draw)
    fin: '<path d="M40 170h320" stroke-width="1.5" opacity=".35"/><path d="M60 150l60-38 50 22 62-58 54 24 74-50" stroke-width="2.6"/><circle cx="360" cy="50" r="6" stroke-width="2.2" style="animation-delay:.6s"/><path d="M80 170v-20M130 170v-46M180 170v-30M230 170v-86M280 170v-60M330 170v-104" stroke-width="10" stroke-linecap="butt" opacity=".16" style="animation-delay:.25s"/><rect x="250" y="120" width="96" height="40" rx="9" stroke-width="2" style="animation-delay:.45s"/><path d="M266 140h30M310 134v12M304 140h12" stroke-width="2" style="animation-delay:.7s"/>',
    retail: '<path d="M40 176h320" stroke-width="1.5" opacity=".35"/><path d="M90 84l16-40h188l16 40" stroke-width="2.6"/><path d="M90 84h220v14c0 12-10 20-22 20s-22-8-22-20c0 12-10 20-22 20s-22-8-22-20c0 12-10 20-22 20s-22-8-22-20c0 12-10 20-22 20s-22-8-22-20z" stroke-width="2.3" style="animation-delay:.2s"/><path d="M104 120v56h192v-56M180 176v-34h40v34" stroke-width="2.2" style="animation-delay:.45s"/><path d="M318 132h28l-4 30h-20z" stroke-width="2" style="animation-delay:.7s"/><path d="M324 132c0-8 4-12 8-12s8 4 8 12" stroke-width="2" style="animation-delay:.8s"/>',
    health: '<path d="M40 176h320" stroke-width="1.5" opacity=".35"/><path d="M200 34l70 26v48c0 40-30 64-70 76-40-12-70-36-70-76V60z" stroke-width="2.6"/><path d="M200 80v52M174 106h52" stroke-width="3" style="animation-delay:.4s"/><rect x="282" y="104" width="64" height="74" rx="8" stroke-width="2" style="animation-delay:.55s"/><path d="M296 124h36M296 140h36M296 156h22" stroke-width="1.8" style="animation-delay:.75s"/><path d="M60 140h40l10-18 14 36 12-24h30" stroke-width="2" opacity=".7" style="animation-delay:.3s"/>',
    const: '<path d="M30 178h340" stroke-width="1.5" opacity=".35"/><path d="M90 178V40M90 40h190M90 64l40-24M130 40v18M270 40v40" stroke-width="2.6"/><path d="M262 80h16v14h-16z" stroke-width="2" style="animation-delay:.6s"/><path d="M180 178v-84h70v84M196 110h12M222 110h12M196 130h12M222 130h12M196 150h12M222 150h12" stroke-width="2.2" style="animation-delay:.35s"/><path d="M280 178v-54h60v54M294 140h10M316 140h10M294 158h10M316 158h10" stroke-width="2" style="animation-delay:.5s"/><path d="M70 178l20-30 20 30" stroke-width="2" opacity=".7" style="animation-delay:.2s"/>'};
  const svg = (p, c = '') => `<svg class="${c}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
  const art = id => `<svg class="ddk-art" viewBox="0 0 400 210" aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">${(ART[id] || ART.fin).replace(/<(path|rect|circle)/g, '<$1 class="ddk-draw" pathLength="1"')}</svg>`;
  const play = '<path d="M8 5.5v13l10.5-6.5z"/>', back = '<path d="M15 6l-6 6 6 6"/>', chat = '<path d="M5 18l-1 3 4-1.5A8.5 8.5 0 1 0 4.5 14"/>';
  const UP = new Set('kfs dcf ecl dpd aml tds gst rwh bim itp itps ncr ncrs bbs boq ids bcf cde evm pmc si uw fhir ppm wo dlp afs mep gis ld arb jv pv ve mv tc cx rto rera ifc hvac sip emi apr utr ehs dwg grn kyc upi url abc pdf id tat ncb opd hsn mrp sku bocw dsr gstin pan dpdp'.split(' '));
  const human = w => String(w || '').split(/[_\s]+/).filter(Boolean).map((p, i) => {
    const lo = p.toLowerCase();
    if (lo === 'pct') return '%';
    if (UP.has(lo)) return lo.length > 3 && lo.endsWith('s') && UP.has(lo.slice(0, -1)) ? lo.slice(0, -1).toUpperCase() + 's' : lo.toUpperCase();
    return i ? lo : lo.charAt(0).toUpperCase() + lo.slice(1);
  }).join(' ');
  const num = n => typeof n === 'number' ? (Number.isInteger(n) ? n.toLocaleString('en-IN') : n.toLocaleString('en-IN', {maximumFractionDigits: 2})) : n;
  const pill = st => st === 'hired' ? '<span class="ddk-pill ok">Working</span>' : st === 'paused' ? '<span class="ddk-pill warn">Paused</span>' : '<span class="ddk-pill mute">Not hired</span>';
  const emp = k => D && D.lanes.flatMap(l => l.employees).find(e => e.key === k);
  const toolOf = (e, read) => (e.tools || []).find(t => !!t.read === !!read);
  const actsCount = e => (e.tools || []).reduce((n, t) => n + t.actions.length, 0);

  // ------------------------------------------------------------ open / load
  async function openDesk(el, arg) {
    EL = el; const id = String(arg || '');
    try { OV = OV || await api('GET', '/api/deskroom'); } catch (e) { el.innerHTML = `<div class="ddk"><p class="ddk-quiet">${esc(e.message)}</p></div>`; return; }
    const asDept = OV.depts.some(d => d.id === id);
    const dept = asDept ? id : (OV.where || {})[id] || (D && D.id) || OV.depts[0].id;
    await load(dept, asDept ? '' : id);
  }
  async function load(dept, key) {
    const my = ++SEQ;
    if (!D || D.id !== dept) {
      EL.innerHTML = `<div class="ddk"><p class="ddk-quiet">Opening the desk…</p></div>`;
      try { D = await api('GET', `/api/deskroom/${encodeURIComponent(dept)}`); } catch (e) { EL.innerHTML = `<div class="ddk"><p class="ddk-quiet">${esc(e.message)}</p></div>`; return; }
      if (my !== SEQ) return;
    }
    const all = D.lanes.flatMap(l => l.employees);
    KEY = key && all.some(e => e.key === key) ? key : (all.find(e => e.status === 'hired') || all[0]).key;
    TAB = 'work'; Q = '';
    title?.('· ' + D.name);
    draw(true);
    autoRecords();
  }
  function autoRecords() {   // a hired employee with a "day" record opens with today's picture in Records
    const e = emp(KEY); const r = e && toolOf(e, true);
    if (!e || e.status !== 'hired' || !r) return;
    const first = r.actions.find(a => a.id === 'day') || (TAB === 'records' ? r.actions.find(a => !a.fields.length) : null);
    if (first && !RES[rk(e.key, r.tool, first.id)]) { ACT[r.tool] = first.id; run(e, r, first, true); }
  }
  const rk = (k, t, a) => `${k}|${t}|${a}`;

  // ------------------------------------------------------------ the page
  function draw(first) {
    if (!EL || !D) return;
    const e = emp(KEY);
    const hiredN = D.lanes.flatMap(l => l.employees).filter(x => x.status === 'hired' || x.status === 'paused').length;
    const working = D.lanes.flatMap(l => l.employees).filter(x => x.status === 'hired').length;
    const acts = D.lanes.flatMap(l => l.employees).reduce((n, x) => n + actsCount(x), 0);
    EL.innerHTML = `<div class="ddk${first ? ' in' : ''}" data-dept="${esc(D.id)}">
      <nav class="ddk-crumb" aria-label="Where you are"><button type="button" data-dd="hub">AI Employees</button><span aria-hidden="true">›</span><span aria-current="page">${esc(D.name)}</span></nav>
      <div class="ddk-depts" role="tablist" aria-label="Departments">${OV.depts.map(d => `<button type="button" role="tab" class="ddk-dept" data-dd="dept" data-id="${esc(d.id)}" aria-selected="${d.id === D.id}">${svg(ICON[d.icon] || ICON.fin)}<span>${esc(d.name)}</span><em>${d.count}</em></button>`).join('')}</div>
      <section class="ddk-hero">
        <div class="ddk-herotx">
          <span class="ddk-eyebrow">${svg(ICON[D.icon] || ICON.fin)}Department desk</span>
          <h1 class="ddk-h1">${esc(D.name)}</h1>
          <p class="ddk-lede">${esc(D.line)}</p>
          <div class="ddk-nums">
            <div><b>${D.lanes.flatMap(l => l.employees).length}</b><span>employees</span></div>
            <div><b>${working}</b><span>working for you</span></div>
            <div><b>${acts}</b><span>things they can do</span></div>
          </div>
        </div>
        <div class="ddk-heroart">${art(D.icon)}</div>
      </section>
      <div class="ddk-body">
        <aside class="ddk-rail" aria-label="Employees">${D.lanes.map(l => `<div class="ddk-lane"><h2 class="ddk-lanehd">${esc(l.name)}</h2>${l.employees.map(x => `
          <button type="button" class="ddk-emp" data-dd="emp" data-key="${esc(x.key)}" aria-current="${x.key === KEY}">
            <span class="ddk-ini" aria-hidden="true">${esc(ini(x.name))}</span>
            <span class="ddk-empname">${esc(x.name)}<small>${actsCount(x)} actions</small></span>
            <i class="ddk-dot ${x.status === 'hired' ? 'ok' : x.status === 'paused' ? 'warn' : ''}" title="${x.status === 'hired' ? 'Working' : x.status === 'paused' ? 'Paused' : 'Not hired'}"></i>
          </button>`).join('')}</div>`).join('')}
          ${hiredN ? '' : '<p class="ddk-fine">Hire one to open its desk. Hiring adds the desk; it never moves money.</p>'}
        </aside>
        <main class="ddk-main" aria-live="polite">${e ? panel(e) : ''}</main>
      </div></div>`;
  }
  const ini = n => String(n || '').replace(/\(.*?\)/g, '').split(/[\s/&-]+/).filter(w => /^[A-Za-z]/.test(w)).slice(0, 2).map(w => w[0].toUpperCase()).join('') || '•';

  function panel(e) {
    const work = toolOf(e, false), rec = toolOf(e, true);
    const hired = e.status === 'hired';
    const head = `<header class="ddk-ehead">
        <div class="ddk-ehtx"><div class="ddk-erow"><h2 class="ddk-h2">${esc(e.name)}</h2>${pill(e.status)}</div>
          <p class="ddk-pitch">${esc(e.pitch)}</p></div>
        <div class="ddk-ehact">${hired ? `<button type="button" class="btn soft ddk-mid" data-dd="ask">${svg(chat)}Ask in chat</button>`
          : e.status === 'paused' ? `<button type="button" class="btn go ddk-mid" data-dd="resume">Resume</button>`
          : `<button type="button" class="btn go ddk-mid" data-dd="hire">Hire ${esc(e.name.split('(')[0].trim())}</button>`}</div>
      </header>`;
    if (!hired) return head + `<div class="ddk-intro">
        <div class="ddk-card"><h3 class="ddk-h3">What it does</h3><ul class="ddk-list">${(e.does || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>
        <div class="ddk-card"><h3 class="ddk-h3">It will never</h3><ul class="ddk-list never">${(e.never || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>
          ${(e.needs || []).length ? `<h3 class="ddk-h3 sp">It needs from you</h3><ul class="ddk-list">${e.needs.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}</div>
        <p class="ddk-fine">${e.status === 'paused' ? 'Paused: nothing runs until you resume it.' : `Hire it to open its desk - ${actsCount(e)} actions, each one a form you fill. Hiring adds the desk and starts on the careful trust level.`}</p></div>`;
    const tabs = rec ? `<div class="ddk-tabs" role="tablist"><button type="button" role="tab" data-dd="tab" data-t="work" aria-selected="${TAB === 'work'}">Work<em>${work ? work.actions.length : 0}</em></button><button type="button" role="tab" data-dd="tab" data-t="records" aria-selected="${TAB === 'records'}">Records<em>${rec.actions.length}</em></button></div>` : '';
    const t = TAB === 'records' && rec ? rec : (work || rec);
    return head + tabs + (t ? toolView(e, t) : '<p class="ddk-quiet">This employee has nothing to run here yet.</p>');
  }

  function toolView(e, t) {
    const cur = ACT[t.tool] && t.actions.find(a => a.id === ACT[t.tool]) ? ACT[t.tool] : (t.read && t.actions.some(a => a.id === 'day') ? 'day' : t.actions[0]?.id);
    ACT[t.tool] = cur;
    const list = Q && !t.read ? t.actions.filter(a => (a.label + ' ' + a.gives + ' ' + a.id).toLowerCase().includes(Q.toLowerCase())) : t.actions;
    const a = t.actions.find(x => x.id === cur);
    return `<p class="ddk-about">${esc(t.about)}</p>
      ${t.actions.length > 9 && !t.read ? `<div class="ddk-find">${svg('<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4-4"/>')}<input id="ddkQ" type="search" placeholder="Find an action" value="${esc(Q)}" aria-label="Find an action"></div>` : ''}
      <div class="ddk-acts${t.read ? ' rd' : ''}" role="list">${list.map((x, i) => `<button type="button" role="listitem" class="ddk-act" data-dd="act" data-tool="${esc(t.tool)}" data-a="${esc(x.id)}" aria-pressed="${x.id === cur}" style="animation-delay:${Math.min(i, 14) * 28}ms"><b>${esc(t.read && x.id === 'day' ? "Today's desk" : x.label)}</b>${t.read ? '' : `<small>${esc(x.gives || (x.fields.length ? x.fields.slice(0, 3).map(f => f.label).join(', ') : 'No inputs'))}</small>`}</button>`).join('') || '<p class="ddk-quiet">No action matches.</p>'}</div>
      ${a ? formView(e, t, a) : ''}`;
  }

  // ------------------------------------------------------------ the form
  function formView(e, t, a) {
    const key = rk(e.key, t.tool, a.id), vals = FORM[key] || (FORM[key] = {});
    const fields = a.fields.map(f => field(f, vals)).join('');
    const running = BUSY === key;
    const enter = ENTER === key; ENTER = '';
    return `<section class="ddk-form${enter ? ' enter' : ''}" data-k="${esc(key)}">
      <div class="ddk-formhd"><div><h3 class="ddk-h3">${esc(t.read && a.id === 'day' ? "Today's desk" : a.label)}</h3>
        ${a.gives ? `<p class="ddk-gives">You get: ${esc(a.gives)}</p>` : a.about ? `<p class="ddk-gives">${esc(a.about.replace(/^\(|\)$/g, ''))}</p>` : ''}</div></div>
      ${a.guessed ? `<p class="ddk-note">This action does not list its inputs one by one. Fill only what applies; leave the rest empty.</p>` : ''}
      ${fields ? (a.guessed ? `<details class="ddk-more"><summary>All fields (${a.fields.length})</summary><div class="ddk-fields">${fields}</div></details>` : `<div class="ddk-fields">${fields}</div>`) : ''}
      <div class="ddk-run"><button type="button" class="btn go ddk-big" data-dd="run" ${running ? 'disabled' : ''}>${running ? '<i class="ddk-pulse"></i>Working…' : svg(play) + (t.read ? 'Show' : 'Run')}</button>
        ${Object.keys(vals).length ? '<button type="button" class="btn soft ddk-mid" data-dd="clear">Clear</button>' : ''}
        <span class="ddk-fine first">${t.read ? 'Reads only. Nothing changes.' : 'Runs as you, with the same checks as chat. Anything that sends, pays or files waits for your tap.'}</span></div>
      <div class="ddk-out">${result(RES[key], FRESH === key && !(FRESH = ''))}</div>
    </section>`;
  }
  const fid = f => 'ddkf-' + f.name;
  function field(f, vals) {
    const v = vals[f.name], id = fid(f), lab = `<label class="ddk-lab" for="${id}">${esc(f.label)}</label>`;
    const hint = f.hint ? `<small class="ddk-hint">${esc(f.hint)}</small>` : '';
    const wide = ['long', 'rows', 'json', 'list', 'map'].includes(f.shape) ? ' wide' : '';
    let ctl;
    if (f.options && f.options.length) ctl = `<select id="${id}" data-f="${esc(f.name)}"><option value="">—</option>${f.options.map(o => `<option${v === o ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
    else if (f.type === 'boolean') ctl = `<div class="ddk-seg" role="radiogroup" aria-label="${esc(f.label)}">${[['', 'Default'], ['true', 'Yes'], ['false', 'No']].map(([k, n]) => `<button type="button" role="radio" data-bool="${esc(f.name)}" data-v="${k}" aria-checked="${String(v === undefined ? '' : v) === k}">${n}</button>`).join('')}</div>`;
    else if (f.shape === 'rows') ctl = rowsEd(f, v);
    else if (f.shape === 'file') ctl = `<div class="ddk-file"><input id="${id}" type="file" data-file="${esc(f.name)}" class="ddk-sr"><label for="${id}" class="btn soft ddk-mid">${v ? 'Change file' : 'Choose file'}</label><span class="ddk-fine first">${v ? 'Attached' : 'CSV, Excel or PDF'}</span></div>`;
    else if (['long', 'json', 'list', 'map'].includes(f.shape)) {
      const ph = f.shape === 'list' ? 'One per line' : f.shape === 'map' ? 'key: value - one per line' : f.shape === 'json' ? '[{"name": "...", "amount": 0}]' : '';
      const shown = v === undefined ? '' : f.shape === 'list' ? (Array.isArray(v) ? v.join('\n') : v) : f.shape === 'map' ? (typeof v === 'object' ? Object.entries(v).map(([a, b]) => `${a}: ${b}`).join('\n') : v) : f.shape === 'json' ? (typeof v === 'string' ? v : JSON.stringify(v, null, 1)) : v;
      ctl = `<textarea id="${id}" data-f="${esc(f.name)}" rows="${f.shape === 'long' ? 5 : 4}" placeholder="${esc(ph)}">${esc(shown)}</textarea>`;
    } else ctl = `<input id="${id}" data-f="${esc(f.name)}" type="${f.type === 'number' || f.type === 'integer' ? 'number' : 'text'}"${f.type === 'integer' ? ' step="1"' : f.type === 'number' ? ' step="any"' : ''} value="${esc(v ?? '')}" autocomplete="off">`;
    return `<div class="ddk-fld${wide}">${lab}${ctl}${hint}</div>`;
  }
  function rowsEd(f, v) {
    const rows = Array.isArray(v) && v.length ? v : [{}];
    return `<div class="ddk-rows" data-rows="${esc(f.name)}"><div class="ddk-rowsscroll"><table><thead><tr>${f.cols.map(c => `<th>${esc(human(c))}</th>`).join('')}<th><span class="ddk-sr">Remove</span></th></tr></thead><tbody>${rows.map((r, i) => `<tr>${f.cols.map(c => `<td><input data-r="${i}" data-c="${esc(c)}" value="${esc(r[c] ?? '')}" aria-label="${esc(human(c))} row ${i + 1}"></td>`).join('')}<td><button type="button" class="ddk-x" data-dd="rowdel" data-i="${i}" aria-label="Remove row ${i + 1}">×</button></td></tr>`).join('')}</tbody></table></div>
      <div class="ddk-rowsact"><button type="button" class="btn soft ddk-sm" data-dd="rowadd">+ Add row</button><button type="button" class="btn soft ddk-sm" data-dd="rowpaste">Paste from Excel</button><span class="ddk-fine first">${rows.length} row${rows.length === 1 ? '' : 's'}</span></div></div>`;
  }
  const asNum = s => { const t = String(s).replace(/[,₹\s]/g, ''); return t !== '' && !isNaN(t) ? Number(t) : s; };
  function readForm(sec, a) {   // the form as the tool's arguments (empty fields left out)
    const key = sec.dataset.k, vals = FORM[key] || (FORM[key] = {}), args = {};
    for (const f of a.fields) {
      if (f.shape === 'rows') { const rows = collectRows(sec, f); vals[f.name] = rows; const keep = rows.filter(r => Object.values(r).some(x => x !== '' && x != null)); if (keep.length) args[f.name] = keep.map(r => Object.fromEntries(Object.entries(r).filter(([, x]) => x !== '').map(([c, x]) => [c, asNum(x)]))); continue; }
      if (f.type === 'boolean') { if (vals[f.name] === true || vals[f.name] === false) args[f.name] = vals[f.name]; continue; }
      if (f.shape === 'file') { if (vals[f.name]) args[f.name] = vals[f.name]; continue; }
      const el = sec.querySelector(`[data-f="${CSS.escape(f.name)}"]`); if (!el) continue;
      const raw = el.value.trim(); vals[f.name] = raw; if (raw === '') { delete vals[f.name]; continue; }
      if (f.type === 'number' || f.type === 'integer') { const n = Number(raw); if (!isNaN(n)) args[f.name] = n; continue; }
      if (f.shape === 'list') { const items = raw.split(/\n|,(?![^\[]*\])/).map(x => x.trim()).filter(Boolean); args[f.name] = items.map(x => (/^-?[\d.,]+$/.test(x) ? asNum(x) : x)); continue; }
      if (f.shape === 'map') { const o = {}; raw.split('\n').forEach(l => { const m = l.match(/^\s*([^:=]+)\s*[:=]\s*(.+)$/); if (m) o[m[1].trim()] = asNum(m[2].trim()); }); args[f.name] = o; continue; }
      if (f.shape === 'json' || f.type === 'array' || f.type === 'object') { try { args[f.name] = JSON.parse(raw); } catch (_) { throw new Error(`${f.label}: that is not valid JSON - check the brackets and quotes.`); } continue; }
      args[f.name] = raw;
    }
    return args;
  }
  function collectRows(sec, f) {
    const box = sec.querySelector(`[data-rows="${CSS.escape(f.name)}"]`); if (!box) return [];
    const rows = [];
    box.querySelectorAll('input[data-r]').forEach(i => { const r = +i.dataset.r; (rows[r] = rows[r] || {})[i.dataset.c] = i.value.trim(); });
    return rows.filter(Boolean);
  }

  // ------------------------------------------------------------ the result
  const NOTE_KEYS = /^(note|notes|warning|warnings|caveat|caveats|verify|disclaimer|why|not_advice|honest|limits?)$/i;
  function result(r, fresh) {
    if (!r) return '';
    if (r.error) return `<div class="ddk-res err" role="alert"><b>Could not run this</b><p>${esc(r.error)}</p></div>`;
    const v = r.result;
    return `<div class="ddk-res${fresh ? ' enter' : ''}"><div class="ddk-reshd"><b>Result</b><span class="ddk-fine first">${esc(r.at)}</span>
        <button type="button" class="btn soft ddk-sm" data-dd="copy">Copy</button></div>${show(v, 0)}
      ${r.card ? '<p class="ddk-note">A card is waiting for your tap in your Hoola updates chat.</p>' : ''}</div>`;
  }
  function show(v, depth) {
    if (v == null || v === '') return '<p class="ddk-quiet">Nothing came back.</p>';
    if (typeof v !== 'object') return longText(String(v));
    if (Array.isArray(v)) return arr(v, depth);
    if (depth > 3) return `<pre class="ddk-pre">${esc(JSON.stringify(v, null, 2))}</pre>`;
    const say = depth === 0 && typeof v.say === 'string' ? `<p class="ddk-say">${esc(v.say)}</p>` : '';
    const ent = Object.entries(v).filter(([k, x]) => x !== null && x !== '' && !(Array.isArray(x) && !x.length) && k !== 'ok' && !(say && k === 'say'));
    const notes = ent.filter(([k, x]) => NOTE_KEYS.test(k) && (typeof x === 'string' || Array.isArray(x)));
    const tiles = ent.filter(([k, x]) => !NOTE_KEYS.test(k) && (typeof x === 'number' || typeof x === 'boolean' || (typeof x === 'string' && x.length <= 48 && !/\n/.test(x))));
    const rest = ent.filter(e => !notes.includes(e) && !tiles.includes(e));
    let h = say;
    if (tiles.length) h += `<div class="ddk-tiles">${tiles.slice(0, depth ? 12 : 16).map(([k, x]) => `<div class="ddk-tile"><span>${esc(human(k))}</span><b>${esc(typeof x === 'boolean' ? (x ? 'Yes' : 'No') : num(x))}</b></div>`).join('')}</div>`;
    for (const [k, x] of rest) h += `<div class="ddk-sec d${depth}"><h4>${esc(human(k))}</h4>${show(x, depth + 1)}</div>`;
    if (notes.length) h += `<div class="ddk-callout">${notes.map(([k, x]) => `<p><b>${esc(human(k))}:</b> ${Array.isArray(x) ? x.map(y => esc(typeof y === 'string' ? y : JSON.stringify(y))).join(' · ') : esc(x)}</p>`).join('')}</div>`;
    return h || '<p class="ddk-quiet">Nothing came back.</p>';
  }
  function arr(a, depth) {
    if (a.every(x => x == null || typeof x !== 'object')) return `<ul class="ddk-ul">${a.slice(0, 200).map(x => `<li>${esc(num(x))}</li>`).join('')}</ul>`;
    if (a.every(x => x && typeof x === 'object' && !Array.isArray(x) && typeof x.text === 'string' && Object.keys(x).length <= 3))   // flags / findings: a list that reads
      return `<ul class="ddk-flags">${a.slice(0, 200).map(x => `<li>${x.kind || x.level || x.severity ? `<span class="ddk-kind">${esc(human(x.kind || x.level || x.severity))}</span>` : ''}${esc(x.text)}</li>`).join('')}</ul>`;
    if (a.every(x => x && typeof x === 'object' && !Array.isArray(x))) {
      const cols = [];
      a.slice(0, 30).forEach(r => Object.keys(r).forEach(k => { if (!cols.includes(k)) cols.push(k); }));
      const use = cols.slice(0, 9);
      const cell = x => x == null ? '' : typeof x === 'object' ? esc(Array.isArray(x) && x.every(y => typeof y !== 'object') ? x.join(', ') : JSON.stringify(x)).slice(0, 220) : esc(num(x));
      return `<div class="ddk-tbl"><table><thead><tr>${use.map(c => `<th>${esc(human(c))}</th>`).join('')}</tr></thead><tbody>${a.slice(0, 300).map(r => `<tr>${use.map(c => `<td>${cell(r[c])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${a.length > 300 ? `<p class="ddk-fine">Showing 300 of ${a.length}.</p>` : ''}${cols.length > 9 ? `<p class="ddk-fine">${cols.length - 9} more columns are in Copy.</p>` : ''}`;
    }
    return `<pre class="ddk-pre">${esc(JSON.stringify(a, null, 2))}</pre>`;
  }
  const longText = s => s.length > 160 || /\n/.test(s) ? `<div class="ddk-doc">${esc(s)}</div>` : `<p class="ddk-p">${esc(s)}</p>`;

  // ------------------------------------------------------------ actions
  async function run(e, t, a, quiet) {
    const key = rk(e.key, t.tool, a.id);
    const sec = EL.querySelector(`.ddk-form[data-k="${CSS.escape(key)}"]`);
    let args = {};
    try { if (sec) args = readForm(sec, a); } catch (err) { RES[key] = {error: err.message}; paintForm(e, t, a); return; }
    BUSY = key; paintForm(e, t, a);
    try {
      const r = await api('POST', `/api/deskroom/${encodeURIComponent(e.key)}/run`, {tool: t.tool, action: a.id, args});
      const txt = JSON.stringify(r.result || {});
      RES[key] = {result: r.result, at: new Date().toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit'}), card: /"(card|approval|ask_id|pending_card)"/.test(txt)};
    } catch (err) { RES[key] = {error: err.message || 'Something went wrong'}; if (!quiet) toast(err.message, true); }
    BUSY = ''; FRESH = key;
    if (emp(KEY) === e) paintForm(e, t, a);
  }
  function paintForm(e, t, a) {   // repaint only the form, so the rail, tabs and her scroll stay
    const key = rk(e.key, t.tool, a.id), sec = EL.querySelector(`.ddk-form[data-k="${CSS.escape(key)}"]`);
    if (!sec) return;
    const tmp = document.createElement('div'); tmp.innerHTML = formView(e, t, a); sec.replaceWith(tmp.firstElementChild);
  }
  const cur = () => { const e = emp(KEY); if (!e) return {}; const t = (TAB === 'records' && toolOf(e, true)) || toolOf(e, false) || toolOf(e, true); return {e, t, a: t && t.actions.find(x => x.id === ACT[t.tool])}; };
  function keep() { const {t, a} = cur(); const sec = EL.querySelector('.ddk-form'); if (t && a && sec) { try { readForm(sec, a); } catch (_) {} } }

  function bind(el) {
    if (el._ddk) return; el._ddk = true;
    el.addEventListener('click', async ev => {
      const b = ev.target.closest('[data-dd],[data-bool]'); if (!b || !el.contains(b)) return;
      if (b.dataset.bool !== undefined) { const {e, t, a} = cur(); keep(); const vals = FORM[rk(e.key, t.tool, a.id)]; const v = b.dataset.v; if (v === '') delete vals[b.dataset.bool]; else vals[b.dataset.bool] = v === 'true'; paintForm(e, t, a); return; }
      const w = b.dataset.dd;
      if (w === 'hub') { open?.('hire'); return; }
      if (w === 'dept') { keep(); await load(b.dataset.id, ''); return; }
      if (w === 'emp') { keep(); KEY = b.dataset.key; TAB = 'work'; Q = ''; draw(false); autoRecords(); EL.querySelector('.ddk-main')?.scrollIntoView?.({block: 'nearest', behavior: 'smooth'}); return; }
      if (w === 'tab') { keep(); TAB = b.dataset.t; draw(false); if (TAB === 'records') autoRecords(); return; }
      if (w === 'act') { keep(); ACT[b.dataset.tool] = b.dataset.a; ENTER = rk(KEY, b.dataset.tool, b.dataset.a); draw(false); const f = EL.querySelector('.ddk-form'); f?.scrollIntoView?.({block: 'nearest', behavior: 'smooth'}); const {e, t, a} = cur(); if (t?.read && a && !a.fields.length && !RES[rk(e.key, t.tool, a.id)]) run(e, t, a, true); return; }
      const {e, t, a} = cur();
      if (w === 'run' && e && t && a) { run(e, t, a); return; }
      if (w === 'clear' && e) { delete FORM[rk(e.key, t.tool, a.id)]; delete RES[rk(e.key, t.tool, a.id)]; paintForm(e, t, a); return; }
      if (w === 'copy' && e) { const r = RES[rk(e.key, t.tool, a.id)]; try { await navigator.clipboard.writeText(JSON.stringify(r?.result ?? {}, null, 2)); toast('Copied'); } catch (_) { toast('Copy did not work in this browser', true); } return; }
      if (w === 'ask' && e) { ask?.(`Use ${e.name.split('(')[0].trim()}: ${a ? a.label.toLowerCase() + ' - ' : ''}`); return; }
      if ((w === 'hire' || w === 'resume') && e) {
        try { await api('POST', `/api/employees/${encodeURIComponent(e.key)}/${w}`, w === 'hire' ? {trust: 'seekh'} : undefined);
          toast(w === 'hire' ? 'Hired. Its desk is open.' : 'Back at work.'); OV = null; D = null;
          OV = await api('GET', '/api/deskroom'); await load(dept(), e.key);
        } catch (err) { toast(err.message, true); }
        return;
      }
      if (w === 'rowadd' || w === 'rowdel' || w === 'rowpaste') {
        const box = b.closest('[data-rows]'), name = box.dataset.rows, f = a.fields.find(x => x.name === name);
        keep(); const vals = FORM[rk(e.key, t.tool, a.id)]; let rows = (vals[name] || []).slice(); if (!rows.length) rows = [{}];
        if (w === 'rowadd') rows.push({});
        if (w === 'rowdel') { rows.splice(+b.dataset.i, 1); if (!rows.length) rows = [{}]; }
        if (w === 'rowpaste') {
          const txt = prompt(`Paste rows (one per line; columns in this order: ${f.cols.map(human).join(', ')}). Tabs or commas between columns.`);
          if (!txt) return;
          const got = txt.split(/\r?\n/).map(l => l.trim()).filter(Boolean).map(l => l.split(l.includes('\t') ? '\t' : ',').map(x => x.trim()));
          const head = got[0] && got[0].every(x => f.cols.includes(x.toLowerCase().replace(/\s+/g, '_')));
          const order = head ? got[0].map(x => x.toLowerCase().replace(/\s+/g, '_')) : f.cols;
          const data = (head ? got.slice(1) : got).map(cells => Object.fromEntries(order.map((c, i) => [c, cells[i] ?? ''])));
          rows = rows.filter(r => Object.values(r).some(x => x !== '' && x != null)).concat(data);
        }
        vals[name] = rows; paintForm(e, t, a); return;
      }
    });
    el.addEventListener('input', ev => {
      if (ev.target.id === 'ddkQ') { Q = ev.target.value; const pos = ev.target.selectionStart; draw(false); const q = el.querySelector('#ddkQ'); if (q) { q.focus(); try { q.setSelectionRange(pos, pos); } catch (_) {} } }
    });
    el.addEventListener('change', async ev => {
      const inp = ev.target.closest('input[data-file]'); if (!inp || !inp.files?.[0]) return;
      const {e, t, a} = cur(); keep();
      if (!D.conversation_id) { toast('No chat to keep the file in yet - open a chat once, then try again.', true); return; }
      try {
        const fd = new FormData(); fd.append('file', inp.files[0], inp.files[0].name);
        const r = await api('POST', `/api/conversations/${encodeURIComponent(D.conversation_id)}/files`, undefined, {form: fd});
        FORM[rk(e.key, t.tool, a.id)][inp.dataset.file] = r.file_id || r.id; toast('File attached'); paintForm(e, t, a);
      } catch (err) { toast(err.message, true); }
    });
    el.addEventListener('keydown', ev => {
      if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey) && ev.target.closest('.ddk-form')) { ev.preventDefault(); el.querySelector('[data-dd="run"]')?.click(); }
    });
  }
  const dept = () => D?.id || '';

  return {
    open: (el, arg) => { bind(el); return openDesk(el, arg); },
    keys: () => (OV ? OV.depts.map(d => d.id) : []),
    _human: human, _show: show, _readForm: readForm,
  };
};
