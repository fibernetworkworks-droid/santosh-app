/* v0.555 HOOLA CARD - the premium default card (design: claude.ai/artifact/NgbT6WLDj63Jhh7MbysuGD).
   One anatomy for every card kind that has no screen of its own: eyebrow (desk + time), a tile, the title, a status
   signal (dot + plain words), one sentence, the amount as the hero, receipt facts, step segments, a secure band for
   money, and a docked action bar. Pure: html(kind, p, at) returns markup; the console wires the buttons.
   The same rules live in lib/ui/any_card.dart (phone) so both surfaces say the same thing. */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const TITLE_KEYS = ['title', 'name', 'label', 'what', 'subject', 'brief', 'task', 'number'];
  const LINE_KEYS = ['say', 'summary', 'text', 'reason', 'message', 'detail', 'now', 'stage_label'];
  const SKIP = /(^id$|_id$|^key$|^tenant|token|secret|^sig|hash|nonce|^at$|_at$|preview|thumb|^b64|^data$|^raw|^conv|^call$|^url$|^link$|^open_url$|^status$|^state$|^pct$|^progress$|^amount|^inr$|^push$|^kind$|^step$|^total$|^done$|^steps_total$|^error$|^_)/i;
  const WORKING = ['queued', 'running', 'working', 'writing', 'building', 'fixing', 'designing', 'checking', 'watching', 'planning',
    'rendering', 'generating', 'uploading', 'compiling', 'started', 'in_progress', 'processing', 'assembling'];
  const ASKING = ['pending', 'waiting', 'needs_tap', 'waiting_payment', 'waiting_sign', 'asking', 'approval', 'needs_confirm', 'looks', 'planned'];
  const DONE = ['done', 'completed', 'complete', 'approved', 'live', 'placed', 'finished', 'delivered', 'success', 'ok', 'ready', 'zip',
    'published', 'signed', 'final', 'sent'];
  const FAILED = ['failed', 'error'];
  const STOPPED = ['stopped', 'cancelled', 'canceled', 'rejected'];

  function pick(p, keys) { for (const k of keys) { const v = p[k]; if (typeof v === 'string' && v.trim()) return [k, v.trim()]; if (typeof v === 'number') return [k, String(v)]; } return ['', '']; }
  function deskOf(kind) {
    return String(kind || 'card').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
  function stateOf(p) {
    const st = String(p.status || p.state || '').toLowerCase().trim();
    if (FAILED.includes(st)) return 'failed';
    if (STOPPED.includes(st)) return 'stopped';
    if (ASKING.includes(st)) return 'ask';
    if (WORKING.includes(st)) return 'work';
    if (DONE.includes(st)) return 'done';
    return st ? 'other' : 'done';
  }
  function amountOf(p) {
    let v = p.amount_inr ?? p.inr ?? p.amount;
    if (v == null && p.amount_paise != null) v = Number(p.amount_paise) / 100;
    if (v == null || v === '') return '';
    if (typeof v === 'number' || /^\s*[\d,.]+\s*$/.test(String(v))) {
      const n = Number(String(v).replace(/,/g, ''));
      if (isFinite(n)) return n.toLocaleString('en-IN', n % 1 ? {minimumFractionDigits: 2, maximumFractionDigits: 2} : {maximumFractionDigits: 0});
    }
    return String(v).replace(/^\s*(₹|rs\.?|inr)\s*/i, '');
  }
  function isMoney(kind, p) {
    if (/_pay|upi|bill|spend|khata|mandate/.test(kind)) return true;
    if (p.amount || p.amount_inr || p.amount_paise || p.inr) return true;
    return /upi|card|wallet|pay|bank|cash/i.test(String(p.pay_method || ''));
  }
  function ago(at) {
    const t = at ? Date.parse(at) : NaN;
    if (!isFinite(t)) return '';
    const s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return `${Math.round(s / 60)} min ago`;
    if (s < 86400) return `${Math.round(s / 3600)} h ago`;
    return new Date(t).toLocaleDateString('en-IN', {day: 'numeric', month: 'short'});
  }
  const WORDS = {ask: 'Needs your approval', work: 'Working', done: 'Ready', failed: 'Stopped with a problem', stopped: 'Stopped'};
  const TONE = {ask: 'ask', work: 'work', done: 'ok', failed: 'bad', stopped: 'mut', other: 'ask'};
  const ICON = {
    money: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>',
    ask: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18"/><path d="M12 8v5M12 16.5h.01"/></svg>',
    work: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/></svg>',
    ok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 5 5 9-10"/></svg>',
    bad: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/></svg>',
    mut: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
    lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>',
  };
  function facts(p, used, max) {
    const rows = [];
    for (const [k, v] of Object.entries(p || {})) {
      if (rows.length >= max || SKIP.test(k) || used.includes(k)) continue;
      if (v === null || v === '' || typeof v === 'object' || typeof v === 'boolean') continue;
      const s = String(v); if (s.length > 48) continue;
      const label = k.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
      rows.push(`<dt>${esc(label)}</dt><dd>${esc(s)}</dd>`);
    }
    return rows.length ? `<dl class="hcard-rc">${rows.join('')}</dl>` : '';
  }
  function steps(p) {
    let pct = Number(p.pct ?? p.progress ?? (p.board && p.board.pct));
    let done = Number(p.step ?? p.done), total = Number(p.total ?? p.steps_total);
    if (isFinite(done) && isFinite(total) && total > 0) pct = (done / total) * 100;
    if (!isFinite(pct) || pct < 0) return '';
    pct = Math.min(100, pct);
    const n = 6, on = Math.floor((pct / 100) * n + 1e-9);
    let segs = '';
    for (let i = 1; i <= n; i++) segs += `<i class="${i <= on ? 'on' : i === on + 1 && pct < 100 ? 'now' : ''}"></i>`;
    const left = isFinite(done) && isFinite(total) && total > 0 ? `${done} / ${total}` : `${Math.round(pct)}%`;
    return `<div class="hcard-steps" role="progressbar" aria-valuenow="${Math.round(pct)}" aria-valuemin="0" aria-valuemax="100">${segs}</div>`
      + `<div class="hcard-stepl"><b>${esc(left)}</b></div>`;
  }

  /** The card's markup. opts: {label, link, panel, told} - label = a known kind name, link = a safe https link,
   *  panel = true when the side panel can open it, told = true when Hoola already said it on her call. */
  function html(kind, p, at, opts) {
    p = p || {}; opts = opts || {};
    const st = stateOf(p), money = isMoney(kind, p), amt = money ? amountOf(p) : '';
    const tone = money && st === 'ask' ? 'money' : TONE[st];
    const [tk, title0] = pick(p, TITLE_KEYS);
    const title = title0 || opts.label || deskOf(kind);
    const [lk, line0] = pick(p, (st === 'failed' ? ['reason', 'error'] : []).concat(LINE_KEYS, ['error']).filter(k => k !== tk));   // a problem is the sentence, never a fact
    const line = line0.length > 600 ? line0.slice(0, 600) + '…' : line0;
    const raw = String(p.status || p.state || '').trim();
    const words = st === 'other' ? raw.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase()) : WORDS[st];
    const when = ago(at);
    const eyebrow = `<div class="hcard-eb"><span>${esc(opts.label && opts.label !== title ? opts.label : deskOf(kind))}</span>`
      + `<span class="hcard-er">${opts.told ? `<span class="hcard-told">${ICON.ok}Told on your call</span>` : ''}${when ? `<time>${esc(when)}</time>` : ''}</span></div>`;
    const head = `<div class="hcard-hd"><div class="hcard-tile">${ICON[tone] || ICON.ask}</div><div class="hcard-ht">`
      + `<h4 class="hcard-title">${esc(title)}</h4><span class="hcard-st"><i></i>${esc(words)}</span></div></div>`;
    const ln = line ? `<p class="hcard-line">${esc(line)}</p>` : '';
    const via = String(p.pay_method || p.via || '');
    const m = amt ? `<div class="hcard-money"><div class="hcard-amt"><sup>₹</sup>${esc(amt)}</div>${via ? `<div class="hcard-via">${esc(via)}</div>` : ''}</div>` : '';
    const rc = facts(p, [tk, lk, 'pay_method', 'via'], 3);
    const body = m && rc ? `<div class="hcard-two">${m}${rc}</div>` : m + rc;
    const sec = money && st === 'ask' ? `<div class="hcard-sec">${ICON.lock}<span>Approve with your fingerprint in the Hoola app. Never by voice.</span></div>` : '';
    const acts = opts.panel ? '<button class="hcard-go" type="button" data-pn>Open</button>'
      : opts.link ? `<a class="hcard-go" href="${esc(opts.link)}" target="_blank" rel="noopener noreferrer">Open</a>` : '';
    const dock = acts ? `<div class="hcard-dock"><span class="hcard-sp"></span>${acts}</div>` : '';
    return `<div class="hcard t-${tone}"><div class="hcard-in">${eyebrow}${head}${ln}${steps(p)}${body}${sec}</div>${dock}</div>`;
  }
  const api = {html, stateOf, amountOf, isMoney, deskOf};
  root.HoolaCard = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
