/* v0.947 HOOLA AUTO - the client's intake page. No sign-in: the random token in the address is the whole key. This page
   can only read its own project's intake and answer / confirm / sign off. Every server string goes in as text. */
'use strict';
(function () {
  const TOKEN = (location.pathname.split('/').filter(Boolean).pop() || '').trim();
  const BASE = '/api/auto/c/' + encodeURIComponent(TOKEN);
  const app = document.getElementById('app');
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
  let D = null, editing = '', picked = '', typed = '', err = '', warn = '', busy = false, rec = null, listening = false;

  function h(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') e.className = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else if (k === 'value') e.value = v;
      else e.setAttribute(k, v === true ? '' : String(v));
    }
    for (const c of kids.flat()) { if (c == null || c === false) continue; e.append(c instanceof Node ? c : document.createTextNode(String(c))); }
    return e;
  }

  async function call(method, path, body) {
    const opt = {method, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', headers: {}};
    if (body !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
    const r = await fetch(BASE + path, opt);
    let data = null; try { data = await r.json(); } catch (e) { /* no body */ }
    if (r.status === 404) { const x = new Error('dead'); x.dead = true; throw x; }
    if (r.status === 429) throw new Error('Too many answers today - try again tomorrow.');
    if (!r.ok) throw new Error((data && typeof data.detail === 'string' && data.detail) || 'Something went wrong. Please try again.');
    return data;
  }

  function dead() {
    app.replaceChildren(h('div', {class: 'ci-dead'}, h('h1', {}, 'This link is not active'),
      h('p', {}, 'Ask the team for a new one.')));
  }

  async function load() {
    try { D = await call('GET', ''); err = ''; render(); }
    catch (e) { if (e.dead) return dead(); err = e.message; render(); }
  }

  async function act(method, path, body, after) {
    if (busy) return; busy = true; err = ''; render();
    try { const out = await call(method, path, body); D = out; warn = out.warn || ''; if (after) after(); }
    catch (e) { if (e.dead) { busy = false; return dead(); } err = e.message; }
    busy = false; render();
  }

  const answer = (key, value, after) => act('POST', '/answer', {key, value}, after);
  const confirm = (key, pick) => act('POST', '/confirm', {key, pick: pick || ''});

  function talk(target) {
    if (!SR) return;
    if (listening && rec) { rec.stop(); return; }
    rec = new SR(); rec.lang = 'en-IN'; rec.interimResults = true; rec.continuous = false;
    const start = target.value ? target.value + ' ' : '';
    rec.onresult = ev => { let t = ''; for (const r of ev.results) t += r[0].transcript; target.value = start + t; typed = target.value; nextOk(); };
    rec.onend = () => { listening = false; render(); };
    rec.onerror = () => { listening = false; render(); };
    listening = true; rec.start(); render();
  }

  // ---- v0.949 talk with the Intake agent: a spoken (or typed) conversation, turn by turn. The browser hears the words
  // with its own speech engine and reads the agent's reply aloud; the server gets text only.
  const TK = {open: false, msgs: [], said: '', interim: '', busy: false, err: '', answered: 0, of: 0, complete: false,
              warn: '', rec: null, listening: false, started: false};

  function stopVoice() { try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) { /* none */ } }

  function say(text) {
    if (!text || !window.speechSynthesis || !window.SpeechSynthesisUtterance) return;
    stopVoice();
    const u = new SpeechSynthesisUtterance(text);
    const vs = window.speechSynthesis.getVoices() || [];
    const v = vs.find(x => /en[-_]IN/i.test(x.lang)) || vs.find(x => /^en/i.test(x.lang));
    if (v) u.voice = v;
    u.lang = (v && v.lang) || 'en-IN';
    window.speechSynthesis.speak(u);
  }

  async function turn(said, spoken) {
    if (TK.busy) return;
    TK.busy = true; TK.err = ''; TK.interim = '';
    if (said) TK.msgs.push({who: 'you', text: said});
    render();
    let got = [];
    try {
      const out = await call('POST', '/talk', {said: said || '', spoken: !!spoken});
      TK.msgs.push({who: 'agent', text: out.reply || '', got: out.got || []});
      TK.answered = out.answered || 0; TK.of = out.of || 0; TK.complete = !!out.complete; TK.warn = out.warn || '';
      got = out.got || [];
      say(out.speak || out.reply || '');
    } catch (e) {
      if (e.dead) { TK.busy = false; return dead(); }
      TK.err = e.message;
    }
    TK.busy = false;
    if (got.length) await load(); else render();
  }

  function openTalk() {
    TK.open = true; render();
    if (!TK.started) { TK.started = true; turn('', false); }
    setTimeout(() => document.getElementById('ci-talk')?.scrollIntoView({behavior: 'smooth', block: 'start'}), 0);
  }

  function closeTalk() {
    stopVoice();
    if (TK.rec && TK.listening) { try { TK.rec.abort(); } catch (e) { /* none */ } }
    TK.open = false; TK.listening = false; render();
  }

  function talkMic() {
    if (!SR || TK.busy) return;
    if (TK.listening && TK.rec) { TK.rec.stop(); return; }
    stopVoice();
    const r = new SR(); r.lang = 'en-IN'; r.interimResults = true; r.continuous = false;
    let fin = '';
    r.onresult = ev => {
      let inter = ''; fin = '';
      for (const x of ev.results) { if (x.isFinal) fin += x[0].transcript; else inter += x[0].transcript; }
      TK.interim = (fin + ' ' + inter).trim();
      const el = document.getElementById('ci-talk-heard'); if (el) el.textContent = TK.interim;
    };
    r.onerror = ev => { TK.listening = false; if (ev && ev.error && ev.error !== 'no-speech' && ev.error !== 'aborted') TK.err = 'The microphone did not work here. Type instead.'; render(); };
    r.onend = () => { TK.listening = false; const t = fin.trim(); TK.interim = ''; if (t) turn(t, true); else render(); };
    TK.rec = r; TK.listening = true; TK.interim = '';
    try { r.start(); } catch (e) { TK.listening = false; }
    render();
  }

  function talkSend() {
    const t = TK.said.trim(); if (!t || TK.busy) return;
    TK.said = ''; turn(t, false);
  }

  function talkPanel() {
    const ta = h('textarea', {id: 'ci-talk-in', class: 'ci-in', rows: '1', placeholder: 'Type here', 'aria-label': 'Your reply to the Intake agent',
      oninput: e => { TK.said = e.target.value; const b = document.getElementById('ci-talk-send'); if (b) b.disabled = TK.busy || !TK.said.trim(); },
      onkeydown: e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); talkSend(); } }});
    ta.value = TK.said;
    const log = h('div', {class: 'ci-talk-log', id: 'ci-talk-log', 'aria-live': 'polite'},
      TK.msgs.map(m => h('div', {class: 'ci-tb ' + (m.who === 'agent' ? 'agent' : 'you')},
        h('span', {}, m.text),
        (m.got || []).map(g => h('span', {class: 'ci-tgot'}, '✓ ' + g.q + ' ', h('b', {}, g.value))))),
      TK.listening ? h('div', {class: 'ci-tb you heard', id: 'ci-talk-heard'}, TK.interim || 'Listening…') : null,
      TK.busy ? h('div', {class: 'ci-tb agent wait'}, 'Thinking…') : null);
    return h('section', {class: 'ci-card ci-talk', id: 'ci-talk', 'aria-label': 'Talk with the Intake agent'},
      h('div', {class: 'ci-talk-hd'},
        h('span', {class: 'ci-talk-tt'}, h('b', {}, 'Talk with the Intake agent'),
          h('span', {}, TK.of ? `${TK.answered} of ${TK.of} answered` : 'Answer by speaking or typing')),
        h('button', {type: 'button', class: 'ci-btn ci-sm', onclick: closeTalk}, 'Close')),
      log,
      TK.err ? h('div', {class: 'ci-err', role: 'alert'}, TK.err) : null,
      TK.warn ? h('div', {class: 'ci-warn', role: 'status'}, TK.warn) : null,
      SR ? null : h('span', {class: 'ci-note'}, 'This browser cannot hear speech - type instead.'),
      h('div', {class: 'ci-talk-bar'},
        SR ? h('button', {type: 'button', class: 'ci-btn ci-mic' + (TK.listening ? ' on' : ''), 'aria-pressed': TK.listening ? 'true' : 'false',
          disabled: TK.busy, onclick: talkMic}, TK.listening ? 'Stop' : 'Speak') : null,
        ta,
        h('button', {type: 'button', id: 'ci-talk-send', class: 'ci-btn pri', disabled: TK.busy || !TK.said.trim(), onclick: talkSend}, 'Send')),
      h('span', {class: 'ci-note'}, 'Your browser turns your voice into words; only the words are sent. Answers you give here show below as "Please check".'));
  }

  // ---- pieces
  function top() {
    return h('header', {class: 'ci-top'}, h('span', {class: 'ci-logo', 'aria-hidden': 'true'}, (D.project || 'P').charAt(0).toUpperCase()),
      h('span', {class: 'ci-tt'}, h('b', {}, D.project || 'Your project'), h('span', {}, 'Project intake')),
      h('span', {class: 'ci-pct', 'aria-label': `${D.pct} percent answered`}, `${D.pct}%`));
  }

  function nav() {
    return h('nav', {class: 'ci-nav', 'aria-label': 'Intake sections'}, D.sections.map((s, i) => {
      const done = s.fields.filter(f => f.state === 'confirmed' || f.state === 'found').length;
      return h('button', {type: 'button', class: done === s.fields.length ? 'done' : '',
        onclick: () => document.getElementById('sec-' + i)?.scrollIntoView({behavior: 'smooth', block: 'start'})},
        s.name, h('span', {}, `${done}/${s.fields.length}`));
    }));
  }

  function foundCard(f) {
    if (f.state === 'conflict' && f.alt) {
      return h('div', {class: 'ci-card ci-found'}, h('span', {class: 'ci-q'}, f.q),
        h('span', {class: 'ci-v'}, 'Two answers disagree. Which one is right?'),
        h('div', {class: 'ci-pick'},
          h('button', {type: 'button', disabled: !D.can_answer || busy, onclick: () => confirm(f.key, 'a')}, f.value, h('small', {}, 'From ' + (f.source_ref || 'an earlier answer'))),
          h('button', {type: 'button', disabled: !D.can_answer || busy, onclick: () => confirm(f.key, 'b')}, f.alt.value, h('small', {}, 'From ' + (f.alt.source_ref || 'another source')))));
    }
    if (editing === 'found:' + f.key) return editCard(f, 'ci-card ci-found');
    return h('div', {class: 'ci-card ci-found'},
      h('span', {}, h('span', {class: 'ci-q'}, f.q), h('br'), h('span', {class: 'ci-v'}, f.value), h('br'),
        h('span', {class: 'ci-from'}, 'From ' + (f.source_ref || f.source_label || 'what the team read'))),
      D.can_answer ? h('div', {class: 'ci-row'},
        h('button', {type: 'button', class: 'ci-btn pri', disabled: busy, onclick: () => confirm(f.key)}, 'Yes, correct'),
        h('button', {type: 'button', class: 'ci-btn', disabled: busy, onclick: () => { editing = 'found:' + f.key; render(); }}, 'Change')) : null);
  }

  function editCard(f, cls) {
    const ta = h('textarea', {class: 'ci-in', rows: '2', 'aria-label': f.q}); ta.value = f.value || '';
    setTimeout(() => ta.focus(), 0);
    return h('div', {class: cls}, h('span', {class: 'ci-q'}, f.q), ta,
      h('div', {class: 'ci-row'},
        h('button', {type: 'button', class: 'ci-btn pri', disabled: busy, onclick: () => ta.value.trim() && answer(f.key, ta.value.trim(), () => { editing = ''; })}, 'Save'),
        h('button', {type: 'button', class: 'ci-btn', onclick: () => { editing = ''; render(); }}, 'Cancel')));
  }

  function question() {
    const q = D.next;
    if (!q) return h('div', {class: 'ci-card'}, h('span', {class: 'ci-question'}, 'Every question has an answer. Thank you.'),
      h('span', {class: 'ci-note'}, 'Look over the answers below, then review and sign off.'));
    if (q.state === 'conflict') return null;             // shown in "Please check what we found"
    const order = D.sections.flatMap(s => s.fields.map(f => f.key));
    const sec = q.section || '';
    const ta = h('textarea', {id: 'ci-answer', class: 'ci-in', rows: '2', placeholder: q.choices.length ? 'Or write your own answer' : 'Your answer',
      'aria-label': q.q, oninput: e => { typed = e.target.value; nextOk(); }});
    ta.value = typed;
    return h('div', {class: 'ci-card', id: 'ci-q'},
      h('span', {class: 'ci-qnum'}, `QUESTION ${order.indexOf(q.key) + 1} · ${sec.toUpperCase()}`),
      h('span', {class: 'ci-question'}, q.q),
      q.choices.length ? h('div', {class: 'ci-choices', role: 'radiogroup', 'aria-label': q.q}, q.choices.map(c =>
        h('label', {class: 'ci-choice' + (picked === c ? ' on' : '')},
          h('input', {type: 'radio', name: 'ci-choice', value: c, checked: picked === c, onchange: () => { picked = c; typed = ''; render(); }}),
          h('i', {'aria-hidden': 'true'}), c))) : null,
      ta,
      h('div', {class: 'ci-row'},
        h('button', {type: 'button', class: 'ci-btn pri ci-next', disabled: busy || !(picked || typed.trim()), onclick: sendQ}, 'Next question'),
        SR ? h('button', {type: 'button', class: 'ci-btn ci-mic' + (listening ? ' on' : ''), 'aria-pressed': listening ? 'true' : 'false',
          onclick: () => talk(document.getElementById('ci-answer'))}, listening ? 'Listening… tap to stop' : 'Speak your answer') : null));
  }

  function nextOk() {
    document.querySelectorAll('.ci-next').forEach(b => { b.disabled = busy || !(picked || typed.trim()); });
  }

  function sendQ() {
    const q = D.next; const v = (typed.trim() || picked);
    if (!q || !v) return;
    answer(q.key, v, () => { picked = ''; typed = ''; });
  }

  function tag(f) {
    if (f.state === 'confirmed') return h('span', {class: 'ci-tag ok'}, 'Answered');
    if (f.state === 'found') return h('span', {class: 'ci-tag f'}, 'Please check');
    if (f.state === 'conflict') return h('span', {class: 'ci-tag c'}, 'Two answers');
    return null;
  }

  function sections() {
    return D.sections.map((s, i) => h('section', {class: 'ci-card ci-sec', id: 'sec-' + i, 'aria-label': s.name}, h('h3', {}, s.name),
      s.fields.map(f => editing === 'f:' + f.key ? h('div', {class: 'ci-f'}, h('div', {class: 'ci-form'}, editCard(f, ''))) :
        h('div', {class: 'ci-f'},
          h('span', {class: 'ci-q'}, f.q, ' ', tag(f)),
          h('span', {class: 'ci-a' + (f.value ? '' : ' none')}, f.value || 'Not answered yet'),
          D.can_answer ? h('button', {type: 'button', class: 'ci-btn ci-edit', disabled: busy,
            onclick: () => { editing = 'f:' + f.key; render(); }}, f.value ? 'Edit' : 'Answer') : null))));
  }

  function side() {
    const msgs = (D.msgs || []).slice(-12);
    return h('aside', {class: 'ci-side'},
      h('div', {class: 'ci-card'}, h('span', {class: 'ci-h2'}, 'Your answers so far'),
        msgs.length ? h('div', {class: 'ci-msgs'}, msgs.map(m => h('div', {class: 'ci-msg' + (m.who === 'client' ? '' : ' agent')}, m.text)))
          : h('span', {class: 'ci-note'}, 'Answer one question at a time. Everything is saved as you go.')),
      h('div', {class: 'ci-card'},
        D.signed ? h('span', {class: 'ci-signed'}, '✓ Signed off on ' + new Date(D.signed).toLocaleDateString())
          : h('span', {class: 'ci-note'}, 'When you are happy with the answers, sign off. The team reviews them and starts.'),
        D.can_answer && !D.signed ? h('button', {type: 'button', class: 'ci-btn pri', disabled: busy,
          onclick: () => { if (window.confirm('Sign off these answers? You can still change them until the team starts.')) act('POST', '/signoff'); }}, 'Review and sign off') : null,
        h('span', {class: 'ci-note'}, 'Never type passwords or secret keys here.')));
  }

  function render() {
    if (!D) { if (err) app.replaceChildren(h('p', {class: 'ci-err'}, err)); return; }
    document.title = (D.project || 'Project') + ' · intake';
    const check = (D.check || []);
    const main = h('main', {class: 'ci-main'},
      h('div', {}, h('h1', {}, `Hi${D.client ? ' ' + D.client : ''}, let's plan your ${D.project || 'project'}`),
        h('p', {class: 'ci-sub'}, D.can_answer ? `${D.of - D.answered} questions left · saved as you go`
          : 'The scope is signed off, so this page is read-only now. Ask the team for any change.'),
        D.can_answer && !TK.open ? h('button', {type: 'button', class: 'ci-btn ci-talkbtn', onclick: openTalk},
          h('span', {class: 'ci-dot', 'aria-hidden': 'true'}), 'Talk instead of typing') : null),
      D.can_answer && TK.open ? talkPanel() : null,
      h('div', {class: 'ci-prog'}, h('div', {class: 'ci-bar', role: 'progressbar', 'aria-valuemin': '0', 'aria-valuemax': '100', 'aria-valuenow': String(D.pct)},
        h('i', {style: `width:${D.pct}%`})), h('small', {}, `${D.answered} of ${D.of} answered · ${D.pct}%`)),
      err ? h('div', {class: 'ci-err', role: 'alert'}, err) : null,
      warn ? h('div', {class: 'ci-warn', role: 'status'}, warn) : null,
      check.length ? h('div', {class: 'ci-list'}, h('span', {class: 'ci-h2'}, 'Please check what we found'),
        h('span', {class: 'ci-note'}, 'The team read your documents and calls. Confirm each answer or change it.'),
        check.map(foundCard)) : null,
      D.can_answer ? question() : null,
      h('span', {class: 'ci-h2'}, 'All your answers'),
      sections());
    const dock = D.can_answer && D.next && D.next.state !== 'conflict' ? h('div', {class: 'ci-dock'},
      SR ? h('button', {type: 'button', class: 'ci-btn', onclick: () => { const t = document.getElementById('ci-answer'); if (t) { t.scrollIntoView({block: 'center'}); talk(t); } }},
        listening ? 'Stop' : 'Speak') : null,
      h('button', {type: 'button', class: 'ci-btn pri ci-next', disabled: busy || !(picked || typed.trim()), onclick: sendQ}, 'Next question')) : null;
    const focusId = document.activeElement && document.activeElement.id;
    app.replaceChildren(top(), h('div', {class: 'ci-wrap'}, nav(), main, side()), (TK.open ? '' : dock) || '');
    if (focusId === 'ci-answer' || focusId === 'ci-talk-in') { const t = document.getElementById(focusId); if (t) { t.focus(); t.setSelectionRange(t.value.length, t.value.length); } }
    const lg = document.getElementById('ci-talk-log'); if (lg) lg.scrollTop = lg.scrollHeight;
  }

  if (!TOKEN || TOKEN.length < 20) dead(); else load();
})();
