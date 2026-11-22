/* v0.999.116 ULTIMATE PC PLAN P6 - PC Jobs: every PC job (Hoola PC + her PC) read back step by step from the step
   record (/api/pc/trace*): what it did, what it was thinking, the screen it acted on with the click marked; a running
   job shows its live screen and a Stop button; a job that went well can be saved as a routine; routines run again with
   new values; her PC rules (never-open sites, ask-first sites, her own sentences). Routes: #/ , #/job/<id>,
   #/routines, #/rules. Same sign-in as the console. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  let TOKEN = '';
  try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch {}
  const APP = $('#pj');
  if (!TOKEN) { location.replace('/console/'); return; }
  let timer = null;

  async function api(method, path, body) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) throw new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`);
    return data;
  }
  async function blobUrl(path) {
    const r = await fetch(path, {headers: {Authorization: 'Bearer ' + TOKEN}, credentials: 'omit', cache: 'no-store'});
    if (!r.ok) return '';
    return URL.createObjectURL(await r.blob());
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'hc-toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, 3200);
  }
  const ago = s => { const d = Math.max(0, Date.now() / 1000 - (Number(s) || 0));
    return d < 90 ? 'just now' : d < 3600 ? `${Math.round(d / 60)} min ago` : d < 86400 ? `${Math.round(d / 3600)} h ago` : `${Math.round(d / 86400)} d ago`; };
  const STATUS = {done: 'Done', running: 'Working', partial: 'Stopped part-way', needs_confirm: 'Waiting for your yes',
    cancelled: 'Stopped', failed: 'Did not finish'};
  const PCNAME = k => k === 'hoola_pc' ? 'Hoola PC' : 'Your PC';

  function shell(active, inner) {
    const nav = (h, label, key) => `<a class="hc-nav" href="${h}"${active === key ? ' aria-current="page"' : ''}>${esc(label)}</a>`;
    APP.innerHTML = `<nav class="hc-side" aria-label="PC jobs">
        <a class="hc-brand" href="/console/computer"><i>H</i>Hoola Computer</a>
        ${nav('#/', 'Jobs', 'jobs')}${nav('#/routines', 'Routines', 'routines')}${nav('#/rules', 'Your rules', 'rules')}
        <div class="hc-lab">Every job Hoola did on a PC, step by step. Kept 14 days.</div>
      </nav><main class="pj-main">${inner}</main>`;
  }

  async function jobs() {
    const d = await api('GET', '/api/pc/trace?limit=100');
    const rows = (d.jobs || []).map(j => `<a class="pj-row" href="#/job/${enc(j.job)}">
        <span class="pj-dot ${esc(j.status)}" aria-hidden="true"></span>
        <span><b>${esc(j.task || '(no task)')}</b><small>${esc(PCNAME(j.kind))} · ${esc(STATUS[j.status] || j.status || '')} · ${esc(j.steps || 0)} steps</small></span>
        <span class="pj-tag">${esc(ago(j.started))}</span></a>`).join('');
    shell('jobs', `<h1>PC jobs</h1><p class="pj-sub">Open a job to see exactly what Hoola did, with the screen it saw at each step.</p>
      <div class="pj-list">${rows || '<div class="hc-empty">No PC jobs yet.</div>'}</div>`);
    if ((d.jobs || []).some(j => j.status === 'running')) timer = setTimeout(route, 5000);
  }

  function argsLine(tool, a) {
    const bits = [];
    for (const [k, v] of Object.entries(a || {})) {
      if (k === 'lane') continue;
      bits.push(`${k}: ${typeof v === 'object' ? JSON.stringify(v).slice(0, 120) : S(v).slice(0, 120)}`);
    }
    return bits.join(' · ');
  }

  async function job(id) {
    const j = await api('GET', `/api/pc/trace/${enc(id)}`);
    const steps = j.steps_list || [];
    let prev = Number(j.started) || 0;
    const items = steps.map(s => {
      const took = prev ? Math.max(0, (Number(s.t) || prev) - prev).toFixed(1) : '';
      prev = Number(s.t) || prev;
      const a = s.args || {};
      const mark = (a.x !== undefined && a.y !== undefined) ? ` data-x="${esc(a.x)}" data-y="${esc(a.y)}"` : '';
      return `<li class="pj-step"><span class="n">${esc(s.n)}</span>
        <div class="what"><b>${esc(s.action || s.tool)}</b>${s.replay ? ' <span class="pj-tag">routine</span>' : ''}
          <div><code>${esc(s.tool)}${argsLine(s.tool, a) ? ' — ' + esc(argsLine(s.tool, a)) : ''}</code></div>
          ${s.thought ? `<div class="think">Thinking: ${esc(s.thought)}</div>` : ''}
          <div class="t">+${esc(took)} s${s.window ? ' · ' + esc(s.window) : ''}</div></div>
        ${s.shot ? `<div class="pj-shot" data-shot="${esc(s.shot)}"${mark}></div>` : '<div></div>'}</li>`;
    }).join('');
    const running = j.status === 'running';
    shell('jobs', `<p><a href="#/">← All jobs</a></p><h1>${esc(j.task || 'PC job')}</h1>
      <p class="pj-sub">${esc(PCNAME(j.kind))} · ${esc(STATUS[j.status] || j.status)} · ${esc(j.steps || steps.length)} steps · started ${esc(ago(j.started))}</p>
      <div class="pj-bar">${running ? '<button class="pj-btn bad" id="stop">Stop this job</button>' : ''}
        ${j.status === 'done' ? '<button class="pj-btn pri" id="save">Save as a routine</button>' : ''}</div>
      ${running ? '<div class="pj-card"><h2>Live screen</h2><img class="pj-live" id="live" alt="The PC screen right now"></div>' : ''}
      ${j.summary ? `<div class="pj-card"><h2>How it ended</h2><div>${esc(j.summary)}</div></div>` : ''}
      <div class="pj-card"><h2>Step by step</h2><ol class="pj-steps" style="list-style:none;padding:0;margin:0">${items || '<li class="hc-empty">No steps recorded.</li>'}</ol></div>
      ${j.final_shot ? `<div class="pj-card"><h2>The screen at the end</h2><div class="pj-shot" style="width:100%;max-width:880px" data-shot="${esc(j.final_shot)}"></div></div>` : ''}`);
    for (const el of document.querySelectorAll('.pj-shot[data-shot]')) {
      const url = await blobUrl(`/api/pc/trace/${enc(id)}/${enc(el.dataset.shot)}`);
      if (!url) continue;
      const img = new Image();
      img.alt = 'The screen Hoola saw at this step';
      img.onload = () => {
        if (el.dataset.x !== undefined) {
          const m = document.createElement('span'); m.className = 'pj-mark';
          m.style.left = (100 * Number(el.dataset.x) / img.naturalWidth) + '%';
          m.style.top = (100 * Number(el.dataset.y) / img.naturalHeight) + '%';
          el.appendChild(m);
        }
      };
      img.src = url; el.appendChild(img);
      el.addEventListener('click', () => {
        const z = document.createElement('div'); z.className = 'pj-zoom'; z.innerHTML = `<img src="${url}" alt="">`;
        z.addEventListener('click', () => z.remove()); document.body.appendChild(z);
      });
    }
    const stop = $('#stop');
    if (stop) stop.addEventListener('click', async () => {
      try { await api('POST', `/api/browser/${enc(id)}/stop`); toast('Stopped.'); route(); } catch (e) { toast(e.message, true); }
    });
    const save = $('#save');
    if (save) save.addEventListener('click', async () => {
      const name = prompt('Name for this routine', (j.task || '').slice(0, 60));
      if (!name) return;
      try { const r = await api('POST', `/api/pc/routines/from-job/${enc(id)}`, {name}); toast(`Saved '${r.name}' (${r.steps.length} steps).`); }
      catch (e) { toast(e.message, true); }
    });
    if (running) {
      const live = $('#live');
      const tick = async () => {
        if (!document.body.contains(live)) return;
        const u = await blobUrl(`/api/browser/${enc(id)}/frame`);
        if (u) { const old = live.src; live.src = u; if (old && old.startsWith('blob:')) URL.revokeObjectURL(old); }
        timer = setTimeout(tick, 1500);
      };
      tick();
      setTimeout(() => { if (location.hash === `#/job/${id}`) route(); }, 15000);
    }
  }

  async function routinesView() {
    const d = await api('GET', '/api/pc/routines');
    const rows = (d.routines || []).map(r => `<div class="pj-card" data-id="${esc(r.id)}"><h2>${esc(r.name)}</h2>
        <p class="pj-sub">${esc(r.steps)} steps · ran ${esc(r.runs || 0)} times${r.healed ? ` · the AI helped ${esc(r.healed)} times` : ''} · ${esc(PCNAME(r.kind))}</p>
        <form class="pj-form">${(r.blanks || []).map(b => `<label>${esc(b.name)}</label><input name="${esc(b.name)}" value="${esc(b.default)}">`).join('')}
          <div class="pj-bar" style="margin-top:12px"><button class="pj-btn pri" type="submit">Run it</button>
          <button class="pj-btn bad" type="button" data-del>Delete</button></div></form></div>`).join('');
    shell('routines', `<h1>Routines</h1><p class="pj-sub">A job that went well, saved. It replays in seconds with no AI; if the website changed, Hoola's AI takes over from that step.</p>
      ${rows || '<div class="hc-empty">No routines yet. Open a finished job and press "Save as a routine", or tell Hoola "save that as a routine".</div>'}`);
    for (const card of document.querySelectorAll('.pj-card[data-id]')) {
      const id = card.dataset.id;
      card.querySelector('form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const values = {};
        for (const inp of card.querySelectorAll('input')) values[inp.name] = inp.value;
        try { const r = await api('POST', `/api/pc/routines/${enc(id)}/run`, {values}); toast('Running.'); if (r && r.session_id) location.hash = `#/job/${r.session_id}`; }
        catch (err) { toast(err.message, true); }
      });
      card.querySelector('[data-del]').addEventListener('click', async () => {
        if (!confirm('Delete this routine?')) return;
        try { await api('DELETE', `/api/pc/routines/${enc(id)}`); route(); } catch (err) { toast(err.message, true); }
      });
    }
  }

  async function rulesView() {
    const r = await api('GET', '/api/pc/rules');
    shell('rules', `<h1>Your rules</h1><p class="pj-sub">Hoola follows these on Hoola PC and on your PC. The site rules are enforced by the system itself, not only by the AI.</p>
      <form class="pj-form pj-card" id="rules">
        <label for="never">Sites Hoola must never open (one per line)</label><textarea id="never" placeholder="bet365.com">${esc((r.never || []).join('\n'))}</textarea>
        <label for="ask">Sites where every change asks you first (one per line)</label><textarea id="ask" placeholder="gst.gov.in">${esc((r.ask || []).join('\n'))}</textarea>
        <label for="notes">Your own rules, in your words (one per line)</label><textarea id="notes" placeholder="Never order anything on a Sunday">${esc((r.notes || []).join('\n'))}</textarea>
        <div class="pj-bar" style="margin-top:12px"><button class="pj-btn pri" type="submit">Save my rules</button></div></form>`);
    $('#rules').addEventListener('submit', async (e) => {
      e.preventDefault();
      const lines = id => $('#' + id).value.split('\n').map(x => x.trim()).filter(Boolean);
      try { const s = await api('PUT', '/api/pc/rules', {never: lines('never'), ask: lines('ask'), notes: lines('notes')});
        toast(`Saved: ${s.never.length} never, ${s.ask.length} ask-first, ${s.notes.length} of your rules.`); rulesView(); }
      catch (err) { toast(err.message, true); }
    });
  }

  async function route() {
    clearTimeout(timer);
    const h = location.hash || '#/';
    try {
      if (h.startsWith('#/job/')) return await job(decodeURIComponent(h.slice(6)));
      if (h === '#/routines') return await routinesView();
      if (h === '#/rules') return await rulesView();
      return await jobs();
    } catch (e) { shell('', `<div class="hc-empty">${esc(e.message)}</div>`); }
  }
  window.addEventListener('hashchange', route);
  route();
})();
