/* v0.999.123 D10 PROOF CARD page (owner only): the old website engine and the new one on the same briefs, side by side;
   the critic's pick, HER pick per pair (which outranks every number), blind Arena duels of the new engine's websites,
   the recommendation code makes, and HER decision: the new engine as the default for NEW websites (or back).
   Reads /api/proofcard* and /api/engine-default; never starts a run. */
(function () {
  'use strict';
  let TOKEN = ''; try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch (e) { /* private window */ }
  const root = document.getElementById('dc');
  const toastEl = document.getElementById('dcToast');
  const S = {data: null, run: '', busy: false};
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const num = v => (v == null ? '–' : String(v));
  const SAY = {old: 'the old one', new: 'the new one', same: 'the same', none: 'neither built'};

  async function api(method, path, body) {
    const r = await fetch(path, {method, headers: Object.assign({Authorization: 'Bearer ' + TOKEN}, body ? {'Content-Type': 'application/json'} : {}),
      body: body ? JSON.stringify(body) : undefined});
    if (!r.ok) { let m = 'Request failed (' + r.status + ')'; try { m = (await r.json()).detail || m; } catch (e) { /* not json */ } throw new Error(m); }
    return r;
  }
  function toast(t) { toastEl.textContent = t; toastEl.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { toastEl.hidden = true; }, 2600); }

  async function load() {
    try {
      const r = await api('GET', '/api/proofcard' + (S.run ? '?run=' + encodeURIComponent(S.run) : ''));
      S.data = await r.json();
      draw();
    } catch (e) {
      root.innerHTML = '<h1>Old or new engine</h1><p class="dc-mut">' + esc(e.message) + (TOKEN ? '' : ' Sign in to the console first.') + '</p>';
    }
  }

  function engRow(name, g) {
    if (!g) return '';
    return '<tr><th>' + esc(name) + '</th><td>' + num(g.built) + '/' + num(g.n) + '</td><td>' + num(g.ok) + '</td><td><b>' + num(g.design) + '</b> (' + num(g.design_n) + ')</td><td>'
      + num(g.ai_made) + '</td><td>' + num(g.median_minutes) + '</td><td>' + num(g.median_inr) + '</td><td>' + num(g.gate_fails) + '</td><td>'
      + num(g.look_tells) + '</td><td>' + num(g.lcp_ms) + '</td></tr>';
  }

  function side(row, eng) {
    const shots = (row.shots || []).map(s => '<figure class="dc-shot"><img alt="' + esc(s.what) + '" data-shot="' + esc(s.file) + '"><figcaption>' + esc(s.what) + '</figcaption></figure>').join('');
    const why = (row.reasons || []).concat(row.warnings || []).concat((row.problems || []).map(p => 'critic: ' + p));
    return '<div data-engine="' + eng + '"><h3>' + (eng === 'old' ? 'Old engine' : 'New engine') + ' <b>' + num(row.design) + '</b>'
      + '<span class="dc-tag ' + (row.ok ? 'ok' : 'no') + '">' + (row.skipped ? 'not run' : row.ok ? 'built right' : 'problem') + '</span></h3>'
      + (why.length ? '<ul class="dc-why">' + why.map(w => '<li>' + esc(w) + '</li>').join('') + '</ul>' : '')
      + (shots ? '<div class="dc-shots">' + shots + '</div>' : '<p class="dc-mut">No pictures.</p>') + '</div>';
  }

  function pairHtml(p, card) {
    const v = (card.picks || {})[p.id] || {};
    const ask = (S.data.briefs || {})[p.id] || '';
    const btn = (k, t) => '<button type="button" data-pick="' + k + '" data-id="' + esc(p.id) + '" aria-pressed="' + (v.pick === k) + '">' + t + '</button>';
    const duel = (p.new || {}).built ? '<div class="pc-duel"><span class="dc-mut">Blind duel of the new one against a public website another builder made for this brief:</span>'
      + '<input type="text" maxlength="40" placeholder="Which builder (e.g. lovable)" data-rival="' + esc(p.id) + '">'
      + '<input type="url" maxlength="500" placeholder="https://… their public website" data-rurl="' + esc(p.id) + '">'
      + '<button type="button" data-duel="' + esc(p.id) + '">Run the duel</button></div>' : '';
    return '<section class="dc-site" data-pair="' + esc(p.id) + '"><div class="dc-head"><span class="dc-id">' + esc(p.id) + '</span>'
      + '<span class="dc-tag">critic: ' + esc(SAY[p.critic_pick] || p.critic_pick) + '</span>'
      + (p.design_gain != null ? '<span class="dc-tag">' + (p.design_gain >= 0 ? '+' : '') + esc(p.design_gain) + '</span>' : '') + '</div>'
      + '<p class="dc-ask">' + esc(ask) + '</p><div class="pc-pair">' + side(p.old || {}, 'old') + side(p.new || {}, 'new') + '</div>'
      + (p.skipped ? '' : '<div class="dc-vote"><span class="dc-mut">Which would you rather have?</span>' + btn('old', 'The old one') + btn('new', 'The new one') + btn('same', 'The same')
        + '<input type="text" maxlength="300" placeholder="A note (optional)" data-note="' + esc(p.id) + '" value="' + esc(v.note || '') + '"></div>')
      + duel + '</section>';
  }

  // ONE ENGINE: the new engine's builder box - checked before every build and repaired by itself
  function boxHtml(b) {
    if (!b) return '';
    const disk = b.disk_free_gb != null ? ' · ' + num(b.disk_free_gb) + ' GB free' : '';
    const fixed = b.repairs ? ' · repaired by itself ' + num(b.repairs) + (b.repairs === 1 ? ' time' : ' times') : '';
    const txt = b.repairing ? 'Website builder: being rebuilt now (about a minute)'
      : b.ok ? 'Website builder: ready' + (b.rev ? ' (rev ' + esc(b.rev) + ')' : '') + disk + fixed
      : 'Website builder: not ready - ' + esc(b.why || '') + (b.fixable ? ' (Hoola rebuilds it by itself before the next build)' : '');
    return '<div class="pc-box" data-box="' + (b.ok && !b.disk_low ? 'ok' : 'bad') + '">' + txt
      + (b.ok && b.disk_low ? ' - ' + esc(b.why || '') : '') + (b.repair_failed ? '<br>Last automatic repair failed: ' + esc(b.repair_failed) : '') + '</div>';
  }

  function decideHtml(card, eng) {
    const rec = card.recommendation || {}, h = card.her || {}, c = card.critic || {};
    const duels = card.duels || {};
    const dl = Object.keys(duels).map(k => esc(k) + ': ' + duels[k].hoola + ' won, ' + duels[k].rival + ' lost, ' + duels[k].tie + ' tied').join(' · ');
    const isNew = eng.engine === 'new';
    return '<section class="pc-decide" data-decide="' + (isNew ? 'new' : 'old') + '"><b>' + (eng.new_sites_on === 'new' ? 'New websites are built on the new engine' : 'New websites are built on the old engine') + '</b>'
      + (eng.server_switch ? '<span class="dc-mut">The server switch studio_react_sites is on, so new websites use the new engine whatever is decided here.</span>' : '')
      + boxHtml(eng.box)
      + '<div class="pc-rec">Critic preferred the new one ' + num(c.new) + ' times, the old one ' + num(c.old) + ', the same ' + num(c.same)
      + '. You picked the new one ' + num(h.new) + ', the old one ' + num(h.old) + ', the same ' + num(h.same) + ' (' + num(h.picked) + ' compared).'
      + (dl ? '<br>Arena duels: ' + dl : '<br>No Arena duels yet.')
      + '<br>What the numbers say: <b>' + esc(rec.say || 'not measured') + '</b>' + ((rec.why || []).length ? '<ul>' + rec.why.map(w => '<li>' + esc(w) + '</li>').join('') + '</ul>' : '') + '</div>'
      + '<div class="row">' + (isNew ? '<button type="button" data-default="old">Back to the old engine</button>'
        : '<button type="button" class="pri" data-default="new"' + (card.running ? ' disabled' : '') + '>Make the new engine the default for new websites</button>')
      + '<span class="dc-mut">Only new websites change. Websites already built stay as they are; an older one moves only when its owner taps Upgrade this site.</span></div></section>';
  }

  function draw() {
    const d = S.data, card = d.card;
    let h = '<h1>Old or new engine</h1><p class="dc-sub">The same briefs built on both website engines, photographed and scored the same way. '
      + 'Critic: ' + esc(d.critic.critic) + ' · writer: ' + esc(d.critic.writer) + '. Your picks outrank every number, and only your tap changes the default.</p>';
    if (!card) {
      root.innerHTML = h + '<div class="dc-empty">No proof card yet. ' + esc(d.how) + '</div>';
      return;
    }
    S.run = card.run || S.run;
    h += '<div class="dc-bar"><label class="dc-mut" for="dcRun">Run</label><select id="dcRun">' + (d.runs || []).map(r => '<option' + (card.file && card.file.indexOf(r) >= 0 ? ' selected' : '') + '>' + esc(r) + '</option>').join('')
      + '</select><span class="dc-mut">' + (card.running ? 'still running · ' : '') + 'version ' + esc(card.version || '') + ' · spent Rs ' + num(card.spent_inr) + ' of Rs ' + num(card.budget_inr)
      + ' · ' + num((card.pairs || []).length) + ' of ' + num(card.planned) + ' briefs' + (card.photos_off ? ' · generated photos off' : '') + '</span></div>';
    h += decideHtml(card, d.engine || {});
    h += '<div class="dc-wrap"><table class="dc-sum"><tr><th></th><th>Built</th><th>Built right</th><th>Design (judged)</th><th>Looks AI-made</th><th>Minutes</th><th>Rs</th><th>Blockers</th><th>AI tells</th><th>LCP ms</th></tr>'
      + engRow('Old engine', card.old) + engRow('New engine', card.new) + '</table></div>';
    h += '<h2>Every brief, both engines</h2>' + (card.pairs || []).map(p => pairHtml(p, card)).join('');
    root.innerHTML = h;
    root.querySelectorAll('img[data-shot]').forEach(img => shot(img));
  }

  async function shot(img) {
    try {
      const r = await api('GET', '/api/proofcard/shot/' + encodeURIComponent(S.run) + '/' + encodeURIComponent(img.dataset.shot));
      img.src = URL.createObjectURL(await r.blob());
    } catch (e) { img.alt = 'Picture not found'; }
  }

  root.addEventListener('click', async e => {
    if (S.busy) return;
    const b = e.target.closest('[data-pick]');
    if (b) {
      const id = b.dataset.id;
      const note = (root.querySelector('[data-note="' + id + '"]') || {}).value || '';
      try {
        await api('POST', '/api/proofcard/pick', {run: S.run, id, pick: b.dataset.pick, note});
        toast('Saved: ' + id + ' - ' + b.textContent.toLowerCase());
        await load();
      } catch (err) { toast(err.message); }
      return;
    }
    const du = e.target.closest('[data-duel]');
    if (du) {
      const id = du.dataset.duel;
      const rival = (root.querySelector('[data-rival="' + id + '"]') || {}).value || '';
      const url = (root.querySelector('[data-rurl="' + id + '"]') || {}).value || '';
      S.busy = true; du.disabled = true; du.textContent = 'Judging…';
      try {
        const r = await (await api('POST', '/api/proofcard/duel', {run: S.run, id, rival: rival || 'other', url})).json();
        toast(r.winner === 'hoola' ? 'The new engine won this duel.' : r.winner === 'rival' ? 'The other builder won this duel.' : 'A tie.');
        S.busy = false; await load();
      } catch (err) { toast(err.message); du.disabled = false; du.textContent = 'Run the duel'; }
      finally { S.busy = false; }
      return;
    }
    const dd = e.target.closest('[data-default]');
    if (dd) {
      const go = dd.dataset.default === 'new';
      if (go && !confirm('Build every NEW website on the new engine from now on?\n\nWebsites already built stay as they are. You can go back at any time.')) return;
      S.busy = true;
      try {
        const r = await (await api('POST', '/api/engine-default', go ? {go: true, hash: S.data.card.hash, run: S.run} : {go: false})).json();
        toast(r.say || 'Saved.');
      } catch (err) { toast(err.message); }
      finally { S.busy = false; }
      await load();
      return;
    }
    const img = e.target.closest('img[data-shot]');
    if (img && img.src) {
      const big = document.createElement('div');
      big.className = 'dc-big';
      big.innerHTML = '<img alt="">';
      big.firstChild.src = img.src;
      big.addEventListener('click', () => big.remove());
      document.body.appendChild(big);
    }
  });
  root.addEventListener('change', e => {
    if (e.target.id === 'dcRun') { S.run = e.target.value; load(); }
  });
  load();
})();
