/* v0.999.50 D0 DESIGN CARD page (owner only): the newest (or a chosen) run, every test site with its screenshots, the
   critic's scores and HER Good / OK / Bad - which outranks every number. Reads /api/designcard*, never starts a run. */
(function () {
  'use strict';
  let TOKEN = ''; try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch (e) { /* private window */ }
  const root = document.getElementById('dc');
  const toastEl = document.getElementById('dcToast');
  const S = {data: null, run: ''};
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const num = v => (v == null ? '–' : String(v));

  async function api(method, path, body) {
    const r = await fetch(path, {method, headers: Object.assign({Authorization: 'Bearer ' + TOKEN}, body ? {'Content-Type': 'application/json'} : {}),
      body: body ? JSON.stringify(body) : undefined});
    if (!r.ok) { let m = 'Request failed (' + r.status + ')'; try { m = (await r.json()).detail || m; } catch (e) { /* not json */ } throw new Error(m); }
    return r;
  }
  function toast(t) { toastEl.textContent = t; toastEl.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { toastEl.hidden = true; }, 2200); }

  async function load() {
    try {
      const r = await api('GET', '/api/designcard' + (S.run ? '?run=' + encodeURIComponent(S.run) : ''));
      S.data = await r.json();
      draw();
    } catch (e) {
      root.innerHTML = '<h1>Design card</h1><p class="dc-mut">' + esc(e.message) + (TOKEN ? '' : ' Sign in to the console first.') + '</p>';
    }
  }

  function sumRow(name, g) {
    if (!g) return '';
    return '<tr><th>' + esc(name) + '</th><td>' + g.built + '/' + g.n + '</td><td>' + g.purpose_ok + '</td><td><b>' + num(g.design) + '</b> (' + g.design_n + ')</td><td>'
      + g.ai_made + '</td><td>' + num(g.median_minutes) + '</td><td>' + num(g.median_inr) + '</td><td>' + g.gate_fails + '</td><td>' + num(g.look_tells)
      + '</td><td>' + num(g.lcp_ms) + '</td><td>' + g.her_good + ' / ' + g.her_ok + ' / ' + g.her_bad + '</td></tr>';
  }

  function siteHtml(row, card) {
    const v = (card.verdicts || {})[row.id] || {};
    const ask = (S.data.briefs || {})[row.id] || '';
    const shots = (row.shots || []).map(s => '<figure class="dc-shot"><img alt="' + esc(s.what) + '" data-shot="' + esc(s.file) + '"><figcaption>' + esc(s.what) + '</figcaption></figure>').join('');
    const crit = row.scores ? '<div class="dc-crit">' + Object.keys(row.scores).map(k => esc(k.replace('_', ' ')) + ' <b>' + row.scores[k] + '</b>').join('') + '</div>' : '';
    const why = (row.reasons || []).concat(row.warnings || []).concat((row.problems || []).map(p => 'critic: ' + p));
    const btn = (k, t) => '<button type="button" data-vote="' + k + '" data-id="' + esc(row.id) + '" aria-pressed="' + (v.verdict === k) + '">' + t + '</button>';
    return '<section class="dc-site"><div class="dc-head"><span class="dc-id">' + esc(row.id) + '</span><span class="dc-score">' + num(row.design) + '</span>'
      + '<span class="dc-tag ' + (row.ok ? 'ok' : 'no') + '">' + (row.skipped ? 'not run' : row.ok ? 'built right' : 'problem') + '</span>'
      + '<span class="dc-tag">' + esc(row.purpose || 'no purpose') + '</span>' + (row.ai_made ? '<span class="dc-tag no">looks AI-made</span>' : '') + '</div>'
      + '<p class="dc-ask">' + esc(ask) + '</p>' + (why.length ? '<ul class="dc-why">' + why.map(w => '<li>' + esc(w) + '</li>').join('') + '</ul>' : '')
      + (shots ? '<div class="dc-shots">' + shots + '</div>' : '') + crit
      + (row.skipped ? '' : '<div class="dc-vote"><span class="dc-mut">Your verdict:</span>' + btn('good', 'Good') + btn('ok', 'OK') + btn('bad', 'Bad')
        + '<input type="text" maxlength="300" placeholder="A note (optional)" data-note="' + esc(row.id) + '" value="' + esc(v.note || '') + '"></div>')
      + '</section>';
  }

  function draw() {
    const d = S.data, card = d.card;
    let h = '<h1>Design card</h1><p class="dc-sub">How good the Web Studio\'s websites look today: 40 fixed briefs, scored the same way every run. '
      + 'Critic: ' + esc(d.critic.critic) + ' · writer: ' + esc(d.critic.writer) + '. Your verdict outranks every number. <a href="/console/proofcard">Old engine or new: the proof</a></p>';
    if (!card) {
      root.innerHTML = h + '<div class="dc-empty">No run yet. ' + esc(d.how) + '</div>';
      return;
    }
    S.run = card.run || S.run;
    h += '<div class="dc-bar"><label class="dc-mut" for="dcRun">Run</label><select id="dcRun">' + (d.runs || []).map(r => '<option' + (card.file && card.file.indexOf(r) >= 0 ? ' selected' : '') + '>' + esc(r) + '</option>').join('')
      + '</select><span class="dc-mut">' + (card.running ? 'still running · ' : '') + 'version ' + esc(card.version || '') + ' · spent Rs ' + num(card.spent_inr) + ' of Rs ' + num(card.budget_inr)
      + ' · ran ' + num(card.ran) + ' of ' + num(card.planned) + (card.photos_off ? ' · generated photos off' : '') + '</span></div>';
    h += '<div class="dc-wrap"><table class="dc-sum"><tr><th></th><th>Built</th><th>Right purpose</th><th>Design (judged)</th><th>Looks AI-made</th><th>Minutes</th><th>Rs</th><th>Blockers</th><th>AI tells</th><th>LCP ms</th><th>Your good / ok / bad</th></tr>'
      + sumRow('Business', card.business) + sumRow('Not a business', card.other) + sumRow('All', card.all) + '</table></div>';
    h += '<h2>Every site</h2>' + (card.rows || []).map(r => siteHtml(r, card)).join('');
    root.innerHTML = h;
    root.querySelectorAll('img[data-shot]').forEach(img => shot(img));
  }

  async function shot(img) {
    try {
      const r = await api('GET', '/api/designcard/shot/' + encodeURIComponent(S.run) + '/' + encodeURIComponent(img.dataset.shot));
      img.src = URL.createObjectURL(await r.blob());
    } catch (e) { img.alt = 'Picture not found'; }
  }

  root.addEventListener('click', async e => {
    const b = e.target.closest('[data-vote]');
    if (b) {
      const id = b.dataset.id;
      const note = (root.querySelector('[data-note="' + id + '"]') || {}).value || '';
      try {
        await api('POST', '/api/designcard/verdict', {run: S.run, id, verdict: b.dataset.vote, note});
        S.data.card.verdicts = S.data.card.verdicts || {};
        S.data.card.verdicts[id] = {verdict: b.dataset.vote, note};
        b.parentNode.querySelectorAll('[data-vote]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
        toast('Saved: ' + id + ' ' + b.textContent);
      } catch (err) { toast(err.message); }
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
