/* Hoola web app (v0.305, v0.434 APP PAGES, MIT, Newtika): the app part of a Hoola-built website.
   v0.434: one in-page app per area (data-hoola-app="shell" data-area="member|staff") with its own menu per role -
   home, tables (sort, search, filter, pages, bulk select), detail pages with linked lists, multi-step forms with checks
   and photo / file upload, kanban, calendar, approvals, members, audit log, permissions, and My account (devices,
   sign out everywhere, 2-step login for staff, download my data, delete my account). Login: email + password, mobile
   OTP (when the site has SMS), the authenticator code for staff with 2-step on.
   Talks only to Hoola's API (meta[name=hoola-app]); the login token lives in this browser only. Every value from the
   server is put on the page as TEXT (never as HTML), and the server checks every rule again on every call.
   The older placeholders (login / form / list / admin) keep working for pages built before v0.434. */
(function () {
  'use strict';
  var d = document, meta = d.querySelector('meta[name="hoola-app"]');
  if (!meta) return;
  var API = meta.getAttribute('content'), LANG = meta.getAttribute('data-lang') || 'en', KEY = 'hoola-app:' + API;
  var PRIVACY = meta.getAttribute('data-privacy') || '../privacy/';
  var EN = {login: 'Log in', signup: 'Create account', otp: 'Mobile OTP', email: 'Email', pw: 'Password (8+ characters)',
    name: 'Your name', mobile: 'Mobile number', code: '6-digit code', getcode: 'Send code', verify: 'Verify', hi: 'Hello',
    out: 'Log out', send: 'Submit', saved: 'Saved!', fail: 'Could not save', need: 'Please log in first.', empty: 'Nothing here yet.',
    edit: 'Edit', del: 'Delete', sure: 'Delete this entry?', role: 'Role', members: 'Members', staffonly: 'Log in with a staff account to see this.',
    save: 'Save', cancel: 'Cancel', yes: 'Yes', no: 'No', dash: 'Last 30 days', perday: 'New a day', total: 'Total',
    approvals: 'Waiting for approval', approve: 'Approve', reject: 'Reject', waiting: 'Waiting for', pick: 'Choose...',
    consent: 'I agree to the privacy notice (how my details are kept and used).', privacy: 'Privacy notice', twofa: 'Code from your authenticator app',
    home: 'Home', account: 'My account', audit: 'Changes (audit log)', matrix: 'Who can do what', search: 'Search', all: 'All',
    table: 'Table', board: 'Board', calendar: 'Calendar', add: 'New', next: 'Next', back: 'Back', step: 'Step', of: 'of',
    selected: 'selected', moveto: 'Move to', bulkdel: 'Delete selected', prev: 'Previous', more: 'Next page', related: 'Linked',
    devices: 'Logged-in devices', thisdev: 'this device', end: 'Log out', outall: 'Sign out everywhere', export: 'Download my data',
    delacc: 'Delete my account', delsure: 'Delete your account and everything you added? This cannot be undone.',
    tfa: '2-step login', tfaon: 'On', tfaoff: 'Off', tfastart: 'Turn on 2-step login', tfakey: 'Key for your authenticator app',
    tfaconfirm: 'Confirm', tfaremove: 'Turn off', bad_email: 'Write a correct email.', bad_phone: 'Write a 10-digit mobile number.',
    bad_num: 'Write a number.', required: 'Please fill this.', maps: 'Open in Maps', file: 'File', yours: 'Yours', who: 'Who',
    when: 'When', what: 'What', create: 'Add', read: 'See', update: 'Change', staffset: 'Only staff set', staffsee: 'Only staff see',
    nomatch: 'No match.', open: 'Open', sentto: 'Code sent to', resend: 'Send again', days: 'Days'};
  var T = {
    en: EN,
    hinglish: {login: 'Login', signup: 'Naya account', otp: 'Mobile OTP', email: 'Email', pw: 'Password (8+ akshar)', name: 'Aapka naam',
      mobile: 'Mobile number', code: '6 ank ka code', getcode: 'Code bhejo', verify: 'Pakka karo', hi: 'Namaste', out: 'Logout',
      send: 'Bhejiye', saved: 'Save ho gaya!', fail: 'Save nahi hua', need: 'Pehle login kijiye.', empty: 'Abhi kuch nahi.', edit: 'Badlo',
      del: 'Hatao', sure: 'Yeh entry hata dein?', staffonly: 'Yeh dekhne ke liye staff account se login kijiye.', cancel: 'Rehne do',
      yes: 'Haan', no: 'Nahi', dash: 'Pichhle 30 din', perday: 'Roz naye', total: 'Kul', approvals: 'Manzoori ka intezaar',
      approve: 'Manzoor', reject: 'Na-manzoor', waiting: 'Intezaar', pick: 'Chuniye...',
      consent: 'Main privacy notice se sehmat hoon (meri jaankari kaise rakhi aur use hogi).', twofa: 'Authenticator app ka code',
      home: 'Home', account: 'Mera account', audit: 'Badlav (audit log)', matrix: 'Kaun kya kar sakta hai', search: 'Khojiye', all: 'Sab',
      add: 'Naya', next: 'Aage', back: 'Peeche', step: 'Kadam', selected: 'chune', moveto: 'Yahan bhejo', bulkdel: 'Chune hue hatao',
      prev: 'Pichhla', more: 'Agla page', related: 'Jude hue', devices: 'Login wale device', thisdev: 'yeh device', end: 'Logout',
      outall: 'Har jagah se logout', export: 'Mera data download', delacc: 'Mera account hatao',
      delsure: 'Aapka account aur aapki daali har cheez hata dein? Wapas nahi hoga.', tfa: '2-step login', tfastart: '2-step login chalu karo',
      tfakey: 'Authenticator app ke liye key', tfaconfirm: 'Pakka karo', tfaremove: 'Band karo', bad_email: 'Sahi email likhiye.',
      bad_phone: '10 ank ka mobile number likhiye.', bad_num: 'Number likhiye.', required: 'Yeh bhariye.', maps: 'Maps mein kholo',
      yours: 'Aapke', who: 'Kaun', when: 'Kab', what: 'Kya', create: 'Daale', read: 'Dekhe', update: 'Badle', staffset: 'Sirf staff bhare',
      staffsee: 'Sirf staff dekhe', nomatch: 'Kuch nahi mila.', open: 'Kholo', sentto: 'Code bheja', resend: 'Dobara bhejo', days: 'Din'},
    hi: {login: 'लॉगिन', signup: 'नया अकाउंट', otp: 'मोबाइल OTP', email: 'ईमेल', pw: 'पासवर्ड (8+ अक्षर)', name: 'आपका नाम', mobile: 'मोबाइल नंबर',
      code: '6 अंक का कोड', getcode: 'कोड भेजें', verify: 'पक्का करें', hi: 'नमस्ते', out: 'लॉगआउट', send: 'भेजिए', saved: 'सेव हो गया!',
      fail: 'सेव नहीं हुआ', need: 'पहले लॉगिन कीजिए।', empty: 'अभी कुछ नहीं।', edit: 'बदलें', del: 'हटाएँ', sure: 'यह एंट्री हटा दें?',
      save: 'सेव', cancel: 'रहने दें', yes: 'हाँ', no: 'नहीं', approve: 'मंज़ूर', reject: 'नामंज़ूर', home: 'होम', account: 'मेरा अकाउंट',
      search: 'खोजिए', add: 'नया', next: 'आगे', back: 'पीछे', consent: 'मैं प्राइवेसी नोटिस से सहमत हूँ।'}
  };
  var t = {};
  Object.keys(EN).forEach(function (k) { t[k] = EN[k]; });
  var L1 = T[LANG] || (LANG === 'mr' ? T.hi : null);
  if (LANG === 'hi' || LANG === 'mr') Object.keys(T.hinglish).forEach(function (k) { t[k] = T.hinglish[k]; });
  if (L1) Object.keys(L1).forEach(function (k) { t[k] = L1[k]; });
  var tok = '';
  try { tok = localStorage.getItem(KEY) || ''; } catch (e) {}
  var me = null, schema = null;

  // ---------------------------------------------------------------- small helpers
  function el(tag, attrs, kids) {
    var x = d.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { if (k === 'text') x.textContent = attrs[k]; else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) x.setAttribute(k, attrs[k] === true ? '' : attrs[k]); });
    (kids || []).forEach(function (c) { if (c) x.appendChild(typeof c === 'string' ? d.createTextNode(c) : c); });
    return x;
  }
  function btn(text, cls, fn) { var b = el('button', {type: 'button', 'class': 'btn ' + (cls || 'btn-ghost'), text: text}); if (fn) b.addEventListener('click', fn); return b; }
  function call(method, path, body, raw) {
    var h = raw ? {} : {'Content-Type': 'application/json'};
    if (tok) h.Authorization = 'Bearer ' + tok;
    return fetch(API + path, {method: method, headers: h, body: raw ? body : (body ? JSON.stringify(body) : undefined)}).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok) { var e = new Error(j.error || t.fail); e.code = r.status; throw e; } return j; });
    });
  }
  function blobOf(path) {
    var h = {}; if (tok) h.Authorization = 'Bearer ' + tok;
    return fetch(API + path, {headers: h}).then(function (r) { if (!r.ok) throw new Error(t.fail); return r.blob(); });
  }
  function setTok(v) { tok = v || ''; try { if (tok) localStorage.setItem(KEY, tok); else localStorage.removeItem(KEY); } catch (e) {} }
  function msg(box, text, ok) { var p = box.querySelector('.hs-form-msg') || box.appendChild(el('p', {'class': 'hs-form-msg', role: 'status'})); p.textContent = text; p.className = 'hs-form-msg ' + (ok ? 'ok' : 'bad'); }
  function C(key) { return (schema.collections || []).filter(function (c) { return c.key === key; })[0]; }
  function staff() { return !!(me && (me.role === 'staff' || me.role === 'admin')); }
  function admin_() { return !!(me && me.role === 'admin'); }
  function canCreate(c) { return c.rules.create === 'public' || (c.rules.create === 'member' && me) || (c.rules.create === 'admin' && staff()); }
  function canRead(c) { return c.rules.read === 'public' || staff() || (me && c.rules.read !== 'admin'); }
  function labelOf(c, r) { var lf = c.label_field || ((c.fields || []).filter(function (f) { return f.type === 'text'; })[0] || {}).key; return String((lf && r[lf]) || r.id); }
  function shown(f, r) {
    var v = r[f.key];
    if (v === '' || v === null || v === undefined) return '';
    if (f.type === 'yes_no') return v ? t.yes : t.no;
    if (f.type === 'ref') return (r._labels || {})[f.key] || String(v);
    if (f.type === 'date' && /^\d{4}-\d{2}-\d{2}/.test(String(v))) { try { return new Date(String(v).slice(0, 10) + 'T00:00:00').toLocaleDateString(); } catch (e) { return String(v); } }
    if (f.type === 'location' && typeof v === 'object') return (v.lat || '') + ', ' + (v.lng || '');
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
  }
  function dateField(c) { return (c.fields || []).filter(function (f) { return f.type === 'date'; })[0]; }
  function boardField(c) {
    if (c.workflow) return (c.fields || []).filter(function (f) { return f.key === c.workflow; })[0];
    return (c.fields || []).filter(function (f) { return f.type === 'choice' && (f.options || []).length > 1; })[0];
  }
  var REFS = {};
  function refOptions(to) {                            // the rows of the linked list this person may see, by their name
    if (!REFS[to]) REFS[to] = call('GET', '/c/' + to).then(function (j) {
      var c = C(to) || {fields: []};
      return (j.rows || []).map(function (r) { return [String(r.id), labelOf(c, r)]; });
    }).catch(function () { return []; });
    return REFS[to];
  }
  function inForm(x) { return !x.computed && !x.workflow && (!x.admin_only || staff()); }

  // ---------------------------------------------------------------- one field
  function input(f, val) {
    var id = 'hf-' + f.key + '-' + Math.random().toString(36).slice(2, 7), box;
    if (f.type === 'long_text') box = el('textarea', {id: id, name: f.key, rows: '3'});
    else if (f.type === 'choice') { box = el('select', {id: id, name: f.key}); (f.options || []).forEach(function (o) { box.appendChild(el('option', {value: o, text: o})); }); }
    else if (f.type === 'yes_no') box = el('input', {id: id, name: f.key, type: 'checkbox'});
    else if (f.type === 'ref' && f.to) {
      box = el('select', {id: id, name: f.key}); box.appendChild(el('option', {value: '', text: t.pick}));
      refOptions(f.to).then(function (opts) {
        opts.forEach(function (o) { var op = el('option', {value: o[0], text: o[1]}); if (String(val || '') === o[0]) op.selected = true; box.appendChild(op); });
      });
    }
    else if (f.type === 'photo' || f.type === 'file') {
      box = el('input', {id: id, name: f.key, type: 'file', accept: f.type === 'photo' ? 'image/*' : 'image/*,application/pdf', 'data-kind': f.type});
      if (val) box.setAttribute('data-had', String(val));
    }
    else box = el('input', {id: id, name: f.key, type: {number: 'number', phone: 'tel', email: 'email', date: 'date'}[f.type] || 'text',
      inputmode: f.type === 'phone' ? 'numeric' : null, step: f.type === 'number' ? 'any' : null});
    if (f.required && f.type !== 'yes_no' && !(box.type === 'file' && val)) box.setAttribute('data-req', '1');
    if (val !== undefined && val !== null && box.type !== 'file') { if (f.type === 'yes_no') box.checked = !!val; else if (f.type !== 'ref') box.value = val; }
    else if (f.default && box.type !== 'file') box.value = f.default;
    var lab = el('label', {'for': id, 'class': 'hs-field'}, [f.label + (f.required ? ' *' : '') + ' ', box]);
    lab.appendChild(el('span', {'class': 'hs-field-err', role: 'alert'}));
    return lab;
  }
  function check(scope, c) {                           // the same checks the server makes, before the trip
    var ok = true;
    scope.querySelectorAll('[name]').forEach(function (x) {
      var f = (c.fields || []).filter(function (y) { return y.key === x.name; })[0], err = '', v = (x.value || '').trim();
      if (!f) return;
      if (x.getAttribute('data-req') && (x.type === 'file' ? !x.files.length : !v)) err = t.required;
      else if (v && f.type === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) err = t.bad_email;
      else if (v && f.type === 'phone' && !/^(\+?91)?[6-9]\d{9}$/.test(v.replace(/[\s-]/g, ''))) err = t.bad_phone;
      else if (v && f.type === 'number' && isNaN(Number(v))) err = t.bad_num;
      var e = x.parentNode.querySelector('.hs-field-err'); if (e) e.textContent = err;
      x.setAttribute('aria-invalid', err ? 'true' : 'false');
      if (err) { if (ok) x.focus(); ok = false; }
    });
    return ok;
  }
  function values(form, c) {                           // uploads first (photo / file), then one JSON body
    var out = {}, ups = [];
    c.fields.forEach(function (f) {
      var x = form.querySelector('[name="' + f.key + '"]'); if (!x) return;
      if (x.type === 'file') {
        if (x.files && x.files[0]) ups.push(call('POST', '/upload', x.files[0], true).then(function (j) { out[f.key] = j.id || j.file || j.fid || ''; }));
        return;
      }
      out[f.key] = f.type === 'yes_no' ? x.checked : x.value;
    });
    return Promise.all(ups).then(function () { return out; });
  }

  // ---------------------------------------------------------------- login: email / mobile OTP / 2-step
  function login(box) {
    box.textContent = '';
    if (me) {
      box.appendChild(el('p', {'class': 'hs-app-me'}, [t.hi + ', ' + (me.name || me.email || '') + ' ',
        btn(t.out, 'btn-ghost', function () { call('POST', '/logout').catch(function () {}).then(function () { setTok(''); me = null; all(); }); })]));
      return;
    }
    var sec = schema.security || {}, mode = 'login', f = el('form', {'class': 'hs-form hs-app-login', novalidate: true}), state = {};
    function done(j) {
      if (j.need_2fa) { state.ticket = j.ticket; mode = 'twofa'; draw(); return; }
      setTok(j.token); me = j.me; all();
    }
    function draw() {
      f.textContent = '';
      if (mode !== 'twofa') {
        var tabs = el('div', {'class': 'btns', role: 'tablist'});
        ['login', 'signup', 'otp'].forEach(function (m) {
          if (m === 'signup' && schema.signup === false) return;
          if (m === 'otp' && !sec.otp) return;
          tabs.appendChild(el('button', {type: 'button', role: 'tab', 'aria-selected': String(mode === m), 'class': 'btn ' + (mode === m ? 'btn-primary' : 'btn-ghost'), text: t[m]}));
          tabs.lastChild.addEventListener('click', function () { mode = m; state = {}; draw(); });
        });
        f.appendChild(tabs);
      }
      if (mode === 'twofa') {
        f.appendChild(input({key: 'code', label: t.twofa, type: 'text', required: true}));
        f.querySelector('[name=code]').setAttribute('autocomplete', 'one-time-code');
        f.querySelector('[name=code]').setAttribute('inputmode', 'numeric');
      } else if (mode === 'otp') {
        f.appendChild(input({key: 'phone', label: t.mobile, type: 'phone', required: true}));
        if (state.sent) {
          f.appendChild(el('p', {'class': 'muted', text: t.sentto + ' ' + state.sent}));
          f.appendChild(input({key: 'code', label: t.code, type: 'text', required: true}));
          f.querySelector('[name=code]').setAttribute('autocomplete', 'one-time-code');
          f.querySelector('[name=code]').setAttribute('inputmode', 'numeric');
          f.querySelector('[name=phone]').value = state.phone;
          if (schema.signup !== false) { f.appendChild(input({key: 'name', label: t.name, type: 'text'})); f.appendChild(consentBox()); }
        }
      } else {
        if (mode === 'signup') f.appendChild(input({key: 'name', label: t.name, type: 'text'}));
        f.appendChild(input({key: 'email', label: t.email, type: 'email', required: true}));
        var pw = input({key: 'password', label: t.pw, type: 'text', required: true}), pi = pw.querySelector('input');
        pi.type = 'password'; pi.autocomplete = mode === 'signup' ? 'new-password' : 'current-password';
        f.appendChild(pw);
        if (mode === 'signup') f.appendChild(consentBox());
      }
      var label = mode === 'otp' ? (state.sent ? t.verify : t.getcode) : mode === 'twofa' ? t.verify : t[mode];
      f.appendChild(el('button', {type: 'submit', 'class': 'btn btn-primary', text: label}));
      if (mode === 'otp' && state.sent) f.appendChild(btn(t.resend, 'btn-ghost', function () { state.sent = ''; draw(); }));
    }
    function consentBox() {
      var id = 'hc-' + Math.random().toString(36).slice(2, 7);
      return el('p', {'class': 'hs-consent'}, [el('input', {type: 'checkbox', id: id, name: 'consent'}), ' ',
        el('label', {'for': id, text: t.consent}), ' ', el('a', {href: PRIVACY, target: '_blank', rel: 'noopener', text: t.privacy})]);
    }
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = function (n) { var x = f.querySelector('[name="' + n + '"]'); return x ? (x.type === 'checkbox' ? x.checked : x.value) : ''; };
      var p;
      if (mode === 'twofa') p = call('POST', '/2fa/login', {ticket: state.ticket, code: q('code')});
      else if (mode === 'otp' && !state.sent) {
        state.phone = q('phone');
        p = call('POST', '/otp/start', {phone: state.phone}).then(function (j) { state.sent = j.sent_to; draw(); return null; });
      } else if (mode === 'otp') p = call('POST', '/otp/verify', {phone: state.phone, code: q('code'), name: q('name'), consent: q('consent') === true});
      else p = call('POST', '/' + mode, {email: q('email'), password: q('password'), name: q('name'), consent: mode === 'signup' ? q('consent') === true : undefined});
      p.then(function (j) { if (j) done(j); }).catch(function (er) { msg(f, er.message, false); });
    });
    draw(); box.appendChild(f);
  }

  // ---------------------------------------------------------------- older placeholders (pages built before v0.434)
  function form(box) {
    var c = C(box.getAttribute('data-c')); box.textContent = ''; if (!c) return;
    if (c.rules.create === 'member' && !me) { box.appendChild(el('p', {'class': 'muted', text: t.need})); return; }
    if (c.rules.create === 'admin' && !staff()) return;
    box.appendChild(formView(c, null, function () { lists(); }));
  }
  function list(box, c, rows, editable) {
    box.textContent = '';
    if (!rows.length) { box.appendChild(el('p', {'class': 'muted', text: t.empty})); return; }
    var g = el('div', {'class': 'grid g2 hs-app-list'});
    rows.forEach(function (r) {
      var card = el('article', {'class': 'card'});
      c.fields.forEach(function (f) { var v = shown(f, r); if (v) card.appendChild(el('p', {}, [el('strong', {text: f.label + ': '}), v])); });
      if (r.created) card.appendChild(el('p', {'class': 'muted', text: new Date(r.created).toLocaleString()}));
      rowActions(card, c, r, all);
      if (editable(r)) {
        card.appendChild(el('div', {'class': 'btns'}, [btn(t.edit, 'btn-ghost', function () { card.textContent = ''; card.appendChild(formView(c, r, all)); }),
          btn(t.del, 'btn-ghost', function () { if (confirm(t.sure)) call('DELETE', '/c/' + c.key + '/' + r.id).then(all).catch(function (er) { alert(er.message); }); })]));
      }
      g.appendChild(card);
    });
    box.appendChild(g);
  }
  function lists() {
    d.querySelectorAll('[data-hoola-app="list"]').forEach(function (box) {
      var c = C(box.getAttribute('data-c')); if (!c) return;
      if (c.rules.read !== 'public' && !me) { box.textContent = ''; box.appendChild(el('p', {'class': 'muted', text: t.need})); return; }
      call('GET', '/c/' + c.key).then(function (j) {
        list(box, c, j.rows || [], function (r) { return staff() || (r.mine && (c.rules.update === 'own' || c.rules.delete === 'own')); });
      }).catch(function (er) { box.textContent = ''; box.appendChild(el('p', {'class': 'muted', text: er.message})); });
    });
  }
  function admin(box) {                                // the old /admin/ placeholder now opens the staff app
    box.textContent = '';
    if (!staff()) { if (me) box.appendChild(el('p', {'class': 'muted', text: t.staffonly})); return; }
    shell(box, 'staff');
  }

  // ---------------------------------------------------------------- workflow buttons + approvals on a row
  function rowActions(box, c, r, after) {
    if (r._pending) {
      box.appendChild(el('p', {'class': 'pill hs-app-pending', text: r._pending.label + ' · ' + t.waiting + ': ' + r._pending.waiting_for +
        ' (' + r._pending.step + '/' + r._pending.of + ')'}));
      if (r._pending.can_decide) box.appendChild(decideButtons(r._pending.id, after));
    }
    if ((r._actions || []).length && c.workflow) {
      var ab = el('div', {'class': 'btns hs-app-actions'});
      r._actions.forEach(function (a) {
        ab.appendChild(btn(a.label + (a.approval ? ' *' : ''), 'btn-primary', function (e) {
          var body = {}; body[c.workflow] = a.to; e.target.disabled = true;
          call('PATCH', '/c/' + c.key + '/' + r.id, body).then(after).catch(function (er) { e.target.disabled = false; alert(er.message); });
        }));
      });
      box.appendChild(ab);
    }
  }
  function decideButtons(id, after) {
    var ok = btn(t.approve, 'btn-primary'), no = btn(t.reject, 'btn-ghost');
    [[ok, 'approve'], [no, 'reject']].forEach(function (p) {
      p[0].addEventListener('click', function () {
        ok.disabled = no.disabled = true;
        call('POST', '/approvals/' + id, {decision: p[1]}).then(after || all).catch(function (er) { ok.disabled = no.disabled = false; alert(er.message); });
      });
    });
    return el('div', {'class': 'btns'}, [ok, no]);
  }

  // ---------------------------------------------------------------- the multi-step form (new + edit)
  function formView(c, r, after) {
    var fields = c.fields.filter(inForm), per = fields.length > 6 ? 5 : fields.length || 1, steps = [], i;
    for (i = 0; i < fields.length; i += per) steps.push(fields.slice(i, i + per));
    if (!steps.length) steps.push([]);
    var f = el('form', {'class': 'hs-form hs-app-form', novalidate: true}), at = 0, parts = [];
    var bar = steps.length > 1 ? el('p', {'class': 'hs-steps muted', 'aria-live': 'polite'}) : null;
    if (bar) f.appendChild(bar);
    steps.forEach(function (st) {
      var fs = el('fieldset', {'class': 'hs-step'});
      st.forEach(function (x) { fs.appendChild(input(x, r ? r[x.key] : undefined)); });
      parts.push(fs); f.appendChild(fs);
    });
    var back = btn(t.back, 'btn-ghost'), next = btn(t.next, 'btn-primary'),
      go = el('button', {type: 'submit', 'class': 'btn btn-primary', text: r ? t.save : t.send}),
      no = btn(t.cancel, 'btn-ghost', function () { after(); });
    f.appendChild(el('div', {'class': 'btns'}, [back, next, go, r ? no : null]));
    function show() {
      parts.forEach(function (p, j) { p.hidden = j !== at; });
      back.hidden = at === 0; next.hidden = at === parts.length - 1; go.hidden = at !== parts.length - 1;
      if (bar) bar.textContent = t.step + ' ' + (at + 1) + ' ' + t.of + ' ' + parts.length;
    }
    back.addEventListener('click', function () { at = Math.max(0, at - 1); show(); });
    next.addEventListener('click', function () { if (check(parts[at], c)) { at++; show(); } });
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!check(parts[at], c)) return;
      go.disabled = true;
      values(f, c).then(function (body) {
        return r ? call('PATCH', '/c/' + c.key + '/' + r.id, body) : call('POST', '/c/' + c.key, body);
      }).then(function (j) { go.disabled = false; if (!r) { f.reset(); at = 0; show(); } msg(f, t.saved, true); setTimeout(function () { after(j); }, r ? 0 : 600); })
        .catch(function (er) { go.disabled = false; msg(f, er.message, false); });
    });
    show();
    return f;
  }

  // ---------------------------------------------------------------- the app shell: menu per role + routes
  function shell(box, area) {
    var wrap = el('div', {'class': 'hs-appx'}), nav = el('nav', {'class': 'hs-appx-nav', 'aria-label': area === 'staff' ? 'Staff' : t.account}),
      main = el('div', {'class': 'hs-appx-main', 'aria-live': 'polite'});
    wrap.appendChild(nav); wrap.appendChild(main); box.textContent = ''; box.appendChild(wrap);
    if (!me) { main.appendChild(el('p', {'class': 'muted', text: t.need})); nav.remove(); return; }
    if (area === 'staff' && !staff()) { main.appendChild(el('p', {'class': 'muted', text: t.staffonly})); nav.remove(); return; }
    var items = [['home', t.home]];
    (schema.collections || []).forEach(function (c) {
      if (area === 'staff' ? true : (canRead(c) && c.rules.read !== 'admin') || canCreate(c)) items.push(['c/' + c.key, c.label]);
    });
    if (area === 'staff' && schema.approvals) items.push(['approvals', t.approvals]);
    if (area === 'staff') items.push(['members', t.members], ['matrix', t.matrix]);
    if (area === 'staff' && admin_()) items.push(['audit', t.audit]);
    items.push(['me', t.account]);
    items.forEach(function (it) { nav.appendChild(el('a', {href: '#/' + area + '/' + it[0], 'data-r': it[0], text: it[1]})); });
    function route() {
      var h = (location.hash || '').replace(/^#\//, '').split('?')[0], parts = h.split('/');
      if (parts[0] !== area) parts = [area, 'home'];
      var r = parts.slice(1);
      nav.querySelectorAll('a').forEach(function (a) { var on = (r.join('/') + '/').indexOf(a.getAttribute('data-r') + '/') === 0; if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
      main.textContent = '';
      var go = function (p) { location.hash = '#/' + area + '/' + p; };
      try {
        if (r[0] === 'c' && C(r[1])) {
          var c = C(r[1]);
          if (r[2] === 'new') return main.appendChild(el('section', {}, [el('h2', {text: c.label + ' · ' + t.add}), formView(c, null, function (j) { go('c/' + c.key + (j && j.id ? '/' + j.id : '')); })]));
          if (r[2] && r[3] === 'edit') return detail(main, c, r[2], area, go, true);
          if (r[2] && ['table', 'board', 'calendar'].indexOf(r[2]) < 0) return detail(main, c, r[2], area, go, false);
          return listView(main, c, r[2] || 'table', area, go);
        }
        if (r[0] === 'approvals') return approvalsView(main);
        if (r[0] === 'members') return membersView(main);
        if (r[0] === 'matrix') return matrixView(main);
        if (r[0] === 'audit') return auditView(main);
        if (r[0] === 'me') return accountView(main);
        return homeView(main, area, go);
      } catch (er) { main.appendChild(el('p', {'class': 'muted', text: String(er.message || er)})); }
    }
    if (shell.bound) removeEventListener('hashchange', shell.bound);
    shell.bound = route; addEventListener('hashchange', route);
    route();
  }

  function homeView(main, area, go) {
    main.appendChild(el('h2', {text: t.hi + ', ' + (me.name || me.email || '')}));
    var g = el('div', {'class': 'hs-dash-grid'}); main.appendChild(g);
    (schema.collections || []).forEach(function (c) {
      if (area !== 'staff' && !(canRead(c) && c.rules.read !== 'admin') && !canCreate(c)) return;
      var card = el('div', {'class': 'card hs-dash-card'}, [el('h3', {text: c.label})]), n = el('p', {'class': 'hs-dash-big', text: '…'});
      card.appendChild(n); g.appendChild(card);
      var acts = el('div', {'class': 'btns'});
      if (canRead(c) && c.rules.read !== 'admin' || area === 'staff') acts.appendChild(btn(t.open, 'btn-ghost', function () { go('c/' + c.key); }));
      if (canCreate(c)) acts.appendChild(btn(t.add, 'btn-primary', function () { go('c/' + c.key + '/new'); }));
      card.appendChild(acts);
      if (canRead(c) && (c.rules.read !== 'admin' || staff())) call('GET', '/c/' + c.key).then(function (j) {
        var rows = j.rows || [];
        n.textContent = String(area === 'staff' ? rows.length : rows.filter(function (x) { return x.mine || c.rules.read !== 'own'; }).length);
      }).catch(function () { n.textContent = '–'; }); else n.textContent = '';
    });
    if (area === 'staff') {
      var dash = el('section', {'class': 'hs-app-admin hs-app-dash'}, [el('h2', {text: t.dash})]);
      main.appendChild(dash);
      call('GET', '/stats?days=30').then(function (j) { board(dash, j); }).catch(function () { dash.remove(); });
    }
  }

  // ---------------------------------------------------------------- list: table / board / calendar
  function listView(main, c, mode, area, go) {
    var head = el('div', {'class': 'hs-appx-head'}, [el('h2', {text: c.label})]);
    main.appendChild(head);
    var bf = boardField(c), df = dateField(c);
    var tabs = el('div', {'class': 'btns', role: 'tablist'});
    [['table', t.table, true], ['board', t.board, !!bf], ['calendar', t.calendar, !!df]].forEach(function (m) {
      if (!m[2]) return;
      tabs.appendChild(el('a', {href: '#/' + area + '/c/' + c.key + '/' + m[0], role: 'tab', 'aria-selected': String(mode === m[0]), 'class': 'btn ' + (mode === m[0] ? 'btn-primary' : 'btn-ghost'), text: m[1]}));
    });
    if (tabs.children.length > 1) head.appendChild(tabs);
    if (canCreate(c)) head.appendChild(btn(t.add, 'btn-primary', function () { go('c/' + c.key + '/new'); }));
    var body = el('div'); main.appendChild(body);
    if (!canRead(c)) { body.appendChild(el('p', {'class': 'muted', text: t.empty})); return; }
    body.appendChild(el('p', {'class': 'muted', text: '…'}));
    call('GET', '/c/' + c.key).then(function (j) {
      body.textContent = '';
      var rows = j.rows || [];
      if (mode === 'board' && bf) return kanban(body, c, rows, bf, area, go);
      if (mode === 'calendar' && df) return calendar(body, c, rows, df, area);
      table(body, c, rows, area, go);
    }).catch(function (er) { body.textContent = ''; body.appendChild(el('p', {'class': 'muted', text: er.message})); });
  }

  function table(body, c, rows, area, go) {
    var cols = c.fields.filter(function (f) { return ['long_text', 'photo', 'file', 'location'].indexOf(f.type) < 0; }).slice(0, 6);
    var st = {q: '', filter: '', sort: '', dir: 1, page: 0, sel: {}}, PER = 20, ff = boardField(c);
    var tools = el('div', {'class': 'hs-appx-tools'}), sq = el('input', {type: 'search', placeholder: t.search, 'aria-label': t.search});
    tools.appendChild(sq);
    var fsel = null;
    if (ff) {
      fsel = el('select', {'aria-label': ff.label}); fsel.appendChild(el('option', {value: '', text: t.all + ' · ' + ff.label}));
      (ff.options || []).forEach(function (o) { fsel.appendChild(el('option', {value: o, text: o})); });
      tools.appendChild(fsel);
    }
    var bulk = el('div', {'class': 'hs-appx-bulk', hidden: true});
    body.appendChild(tools); body.appendChild(bulk);
    var tw = el('div', {'class': 'hs-appx-tablewrap'}); body.appendChild(tw);
    var pager = el('div', {'class': 'btns hs-appx-pager'}); body.appendChild(pager);
    function visible() {
      var q = st.q.toLowerCase();
      var out = rows.filter(function (r) {
        if (st.filter && ff && String(r[ff.key]) !== st.filter) return false;
        if (!q) return true;
        return c.fields.some(function (f) { return shown(f, r).toLowerCase().indexOf(q) >= 0; });
      });
      if (st.sort) {
        var f = c.fields.filter(function (x) { return x.key === st.sort; })[0] || {type: 'text', key: 'created'};
        out.sort(function (a, b) {
          var x = a[st.sort], y = b[st.sort];
          if (f.type === 'number') { x = Number(x) || 0; y = Number(y) || 0; return (x - y) * st.dir; }
          return String(shown(f, a) || '').localeCompare(String(shown(f, b) || '')) * st.dir;
        });
      }
      return out;
    }
    function draw() {
      var all_ = visible(), pages = Math.max(1, Math.ceil(all_.length / PER));
      st.page = Math.min(st.page, pages - 1);
      var view = all_.slice(st.page * PER, st.page * PER + PER);
      tw.textContent = '';
      if (!all_.length) { tw.appendChild(el('p', {'class': 'muted', text: rows.length ? t.nomatch : t.empty})); pager.textContent = ''; drawBulk(); return; }
      var tb = el('table', {'class': 'hs-appx-table'}), hr = el('tr');
      if (staff()) {
        var ca = el('input', {type: 'checkbox', 'aria-label': t.selected});
        ca.checked = view.length > 0 && view.every(function (r) { return st.sel[r.id]; });
        ca.addEventListener('change', function () { view.forEach(function (r) { if (ca.checked) st.sel[r.id] = 1; else delete st.sel[r.id]; }); draw(); });
        hr.appendChild(el('th', {scope: 'col'}, [ca]));
      }
      cols.forEach(function (f) {
        var b = el('button', {type: 'button', 'class': 'hs-sort', text: f.label + (st.sort === f.key ? (st.dir > 0 ? ' ▲' : ' ▼') : '')});
        b.addEventListener('click', function () { if (st.sort === f.key) st.dir = -st.dir; else { st.sort = f.key; st.dir = 1; } draw(); });
        hr.appendChild(el('th', {scope: 'col', 'aria-sort': st.sort === f.key ? (st.dir > 0 ? 'ascending' : 'descending') : null}, [b]));
      });
      tb.appendChild(el('thead', {}, [hr]));
      var tbody = el('tbody');
      view.forEach(function (r) {
        var tr = el('tr', {'class': r._pending ? 'is-pending' : null});
        if (staff()) {
          var cb = el('input', {type: 'checkbox', 'aria-label': labelOf(c, r)}); cb.checked = !!st.sel[r.id];
          cb.addEventListener('change', function () { if (cb.checked) st.sel[r.id] = 1; else delete st.sel[r.id]; drawBulk(); });
          tr.appendChild(el('td', {}, [cb]));
        }
        cols.forEach(function (f, i) {
          var v = shown(f, r);
          tr.appendChild(el('td', {}, [i === 0 ? el('a', {href: '#/' + area + '/c/' + c.key + '/' + r.id, text: v || labelOf(c, r)}) : v]));
        });
        tbody.appendChild(tr);
      });
      tb.appendChild(tbody); tw.appendChild(tb);
      pager.textContent = '';
      if (pages > 1) {
        var pv = btn(t.prev, 'btn-ghost', function () { st.page--; draw(); }), nx = btn(t.more, 'btn-ghost', function () { st.page++; draw(); });
        pv.disabled = st.page === 0; nx.disabled = st.page >= pages - 1;
        pager.appendChild(pv); pager.appendChild(el('span', {'class': 'muted', text: (st.page + 1) + ' / ' + pages})); pager.appendChild(nx);
      }
      drawBulk();
    }
    function drawBulk() {
      var ids = Object.keys(st.sel);
      bulk.hidden = !ids.length; bulk.textContent = '';
      if (!ids.length) return;
      bulk.appendChild(el('span', {text: ids.length + ' ' + t.selected}));
      if (c.workflow) {
        var wf = c.fields.filter(function (f) { return f.key === c.workflow; })[0], s = el('select', {'aria-label': t.moveto});
        s.appendChild(el('option', {value: '', text: t.moveto + '…'}));
        (wf.options || []).forEach(function (o) { s.appendChild(el('option', {value: o, text: o})); });
        s.addEventListener('change', function () {
          if (!s.value) return;
          var to = s.value, body_ = {}; body_[c.workflow] = to;
          seq(ids, function (id) { return call('PATCH', '/c/' + c.key + '/' + id, body_); }).then(function (res) { report(res); reload(); });
        });
        bulk.appendChild(s);
      }
      bulk.appendChild(btn(t.bulkdel, 'btn-ghost', function () {
        if (!confirm(t.sure + ' (' + ids.length + ')')) return;
        seq(ids, function (id) { return call('DELETE', '/c/' + c.key + '/' + id); }).then(function (res) { report(res); reload(); });
      }));
    }
    function report(res) { var bad = res.filter(function (x) { return x.error; }); if (bad.length) alert(bad.length + ' x ' + bad[0].error); }
    function reload() { call('GET', '/c/' + c.key).then(function (j) { rows = j.rows || []; st.sel = {}; draw(); }); }
    sq.addEventListener('input', function () { st.q = sq.value; st.page = 0; draw(); });
    if (fsel) fsel.addEventListener('change', function () { st.filter = fsel.value; st.page = 0; draw(); });
    draw();
  }
  function seq(ids, fn) {                              // one at a time: the server checks each against its rules
    var out = [], i = 0;
    return new Promise(function (done) {
      (function next() {
        if (i >= ids.length) return done(out);
        var id = ids[i++];
        fn(id).then(function () { out.push({id: id}); next(); }).catch(function (er) { out.push({id: id, error: er.message}); next(); });
      })();
    });
  }

  function kanban(body, c, rows, bf, area, go) {
    var lanes = el('div', {'class': 'hs-kanban'});
    (bf.options || []).forEach(function (state) {
      var lane = el('section', {'class': 'hs-lane', 'data-state': state, 'aria-label': state}, [el('h3', {text: state})]);
      lane.addEventListener('dragover', function (e) { e.preventDefault(); lane.classList.add('is-over'); });
      lane.addEventListener('dragleave', function () { lane.classList.remove('is-over'); });
      lane.addEventListener('drop', function (e) {
        e.preventDefault(); lane.classList.remove('is-over');
        var id = e.dataTransfer.getData('text/plain'), r = rows.filter(function (x) { return x.id === id; })[0];
        if (!r || String(r[bf.key]) === state) return;
        var body_ = {}; body_[bf.key] = state;
        if (c.workflow && !(r._actions || []).some(function (a) { return a.to === state; })) { alert(state + ': ' + t.fail); return; }
        call('PATCH', '/c/' + c.key + '/' + id, body_).then(function () { go('c/' + c.key + '/board?' + Date.now()); }).catch(function (er) { alert(er.message); });
      });
      rows.filter(function (r) { return String(r[bf.key] || bf.default || '') === state; }).forEach(function (r) {
        var card = el('article', {'class': 'card hs-kcard', draggable: staff() ? 'true' : null},
          [el('a', {href: '#/' + area + '/c/' + c.key + '/' + r.id, text: labelOf(c, r)})]);
        c.fields.filter(function (f) { return f.key !== bf.key && ['long_text', 'photo', 'file'].indexOf(f.type) < 0; }).slice(1, 3).forEach(function (f) {
          var v = shown(f, r); if (v) card.appendChild(el('p', {'class': 'muted', text: f.label + ': ' + v}));
        });
        card.addEventListener('dragstart', function (e) { e.dataTransfer.setData('text/plain', r.id); });
        rowActions(card, c, r, function () { go('c/' + c.key + '/board?' + Date.now()); });
        lane.appendChild(card);
      });
      lanes.appendChild(lane);
    });
    body.appendChild(lanes);
  }

  function calendar(body, c, rows, df, area) {
    var now = new Date(), y = now.getFullYear(), m = now.getMonth();
    var box = el('div', {'class': 'hs-cal'}); body.appendChild(box);
    function draw() {
      box.textContent = '';
      var first = new Date(y, m, 1), days = new Date(y, m + 1, 0).getDate(), lead = (first.getDay() + 6) % 7;
      var head = el('div', {'class': 'btns hs-cal-head'}, [btn('‹', 'btn-ghost', function () { m--; if (m < 0) { m = 11; y--; } draw(); }),
        el('strong', {text: first.toLocaleDateString(undefined, {month: 'long', year: 'numeric'})}),
        btn('›', 'btn-ghost', function () { m++; if (m > 11) { m = 0; y++; } draw(); })]);
      box.appendChild(head);
      var grid = el('div', {'class': 'hs-cal-grid', role: 'grid'});
      ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].forEach(function (n, i) {
        grid.appendChild(el('div', {'class': 'hs-cal-dow muted', role: 'columnheader', text: new Date(2024, 0, 1 + i).toLocaleDateString(undefined, {weekday: 'short'}) || n}));
      });
      for (var i = 0; i < lead; i++) grid.appendChild(el('div', {'class': 'hs-cal-day is-empty'}));
      for (var day = 1; day <= days; day++) {
        var key = y + '-' + String(m + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
        var cell = el('div', {'class': 'hs-cal-day', role: 'gridcell'}, [el('span', {'class': 'hs-cal-n', text: String(day)})]);
        rows.filter(function (r) { return String(r[df.key] || '').slice(0, 10) === key; }).forEach(function (r) {
          cell.appendChild(el('a', {href: '#/' + area + '/c/' + c.key + '/' + r.id, 'class': 'hs-cal-item', text: labelOf(c, r)}));
        });
        grid.appendChild(cell);
      }
      box.appendChild(grid);
    }
    draw();
  }

  // ---------------------------------------------------------------- a row's own page
  function detail(main, c, id, area, go, editing) {
    call('GET', '/c/' + c.key).then(function (j) {
      var r = (j.rows || []).filter(function (x) { return x.id === id; })[0];
      if (!r) { main.appendChild(el('p', {'class': 'muted', text: t.empty})); return; }
      main.appendChild(el('p', {}, [el('a', {href: '#/' + area + '/c/' + c.key, text: '← ' + c.label})]));
      main.appendChild(el('h2', {text: labelOf(c, r)}));
      var mayEdit = staff() || (r.mine && c.rules.update === 'own'), mayDel = staff() || (r.mine && c.rules.delete === 'own');
      if (editing && mayEdit) { main.appendChild(formView(c, r, function () { go('c/' + c.key + '/' + id); })); return; }
      var dl = el('dl', {'class': 'hs-appx-dl'});
      c.fields.forEach(function (f) {
        var v = r[f.key];
        if (v === '' || v === null || v === undefined) return;
        var dd = el('dd');
        if ((f.type === 'photo' || f.type === 'file') && v) {
          var a = el('a', {href: '#', text: t.file + ' ↗'});
          a.addEventListener('click', function (e) { e.preventDefault(); blobOf('/file/' + encodeURIComponent(v)).then(function (b) { window.open(URL.createObjectURL(b), '_blank', 'noopener'); }).catch(function (er) { alert(er.message); }); });
          if (f.type === 'photo') blobOf('/file/' + encodeURIComponent(v)).then(function (b) { dd.insertBefore(el('img', {src: URL.createObjectURL(b), alt: f.label, 'class': 'hs-appx-img'}), dd.firstChild); }).catch(function () {});
          dd.appendChild(a);
        } else if (f.type === 'location' && v && typeof v === 'object' && v.lat) {
          dd.appendChild(el('a', {href: 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(v.lat + ',' + v.lng), target: '_blank', rel: 'noopener', text: t.maps}));
        } else dd.textContent = shown(f, r);
        dl.appendChild(el('dt', {text: f.label})); dl.appendChild(dd);
      });
      if (r.created) { dl.appendChild(el('dt', {text: t.when})); dl.appendChild(el('dd', {text: new Date(r.created).toLocaleString()})); }
      main.appendChild(dl);
      rowActions(main, c, r, function () { go('c/' + c.key + '/' + id + '?' + Date.now()); });
      var acts = el('div', {'class': 'btns'});
      if (mayEdit) acts.appendChild(btn(t.edit, 'btn-ghost', function () { go('c/' + c.key + '/' + id + '/edit'); }));
      if (mayDel) acts.appendChild(btn(t.del, 'btn-ghost', function () { if (confirm(t.sure)) call('DELETE', '/c/' + c.key + '/' + id).then(function () { go('c/' + c.key); }).catch(function (er) { alert(er.message); }); }));
      main.appendChild(acts);
      (c.relations || []).forEach(function (rel) {
        var kc = C(rel.coll); if (!kc) return;
        var sec = el('section', {'class': 'hs-appx-rel'}, [el('h3', {text: t.related + ': ' + rel.label})]);
        main.appendChild(sec);
        call('GET', '/c/' + c.key + '/' + id + '/related/' + rel.name).then(function (k) {
          var kids = k.rows || [];
          if (!kids.length) { sec.appendChild(el('p', {'class': 'muted', text: t.empty})); return; }
          var ul = el('ul');
          kids.forEach(function (x) { ul.appendChild(el('li', {}, [el('a', {href: '#/' + area + '/c/' + kc.key + '/' + x.id, text: labelOf(kc, x)})])); });
          sec.appendChild(ul);
        }).catch(function () { sec.remove(); });
      });
    }).catch(function (er) { main.appendChild(el('p', {'class': 'muted', text: er.message})); });
  }

  // ---------------------------------------------------------------- staff pages
  function approvalsView(main) {
    main.appendChild(el('h2', {text: t.approvals}));
    call('GET', '/approvals').then(function (j) {
      var list_ = (j.approvals || []).filter(function (a) { return a.status === 'pending'; });
      if (!list_.length) { main.appendChild(el('p', {'class': 'muted', text: t.empty})); return; }
      list_.forEach(function (a) {
        var card = el('article', {'class': 'card'}, [el('h3', {text: (a.title || a.coll) + ': ' + a.label}),
          el('p', {'class': 'muted', text: a.from + ' → ' + a.to + ' · ' + (a.maker || '') + ' · ' + t.waiting + ': ' + a.waiting_for + ' (' + a.step + '/' + a.of + ')'})]);
        if (a.can_decide) card.appendChild(decideButtons(a.id, function () { main.textContent = ''; approvalsView(main); }));
        main.appendChild(card);
      });
    }).catch(function (er) { main.appendChild(el('p', {'class': 'muted', text: er.message})); });
  }
  function approvalsBox(box) { if (schema.approvals) { var s = el('section', {'class': 'hs-app-admin hs-app-appr'}); box.appendChild(s); approvalsView(s); } }
  function membersView(main) {
    main.appendChild(el('h2', {text: t.members}));
    call('GET', '/members').then(function (j) {
      var tb = el('table', {'class': 'hs-appx-table'}), tbody = el('tbody');
      tb.appendChild(el('thead', {}, [el('tr', {}, [el('th', {text: t.name}), el('th', {text: t.email}), el('th', {text: t.role}), el('th', {text: t.tfa})])]));
      (j.members || []).forEach(function (m) {
        var rc = el('td');
        if (j.admin && me && m.id !== me.id) {
          var s = el('select', {'aria-label': t.role});
          ['member', 'staff', 'admin'].forEach(function (r) { var o = el('option', {value: r, text: r}); if (r === m.role) o.selected = true; s.appendChild(o); });
          s.addEventListener('change', function () { call('POST', '/members/' + m.id + '/role', {role: s.value}).catch(function (er) { alert(er.message); }); });
          rc.appendChild(s);
        } else rc.textContent = m.role;
        tbody.appendChild(el('tr', {}, [el('td', {text: m.name || ''}), el('td', {text: m.email && m.email.indexOf('@phone.local') < 0 ? m.email : (m.phone || '')}), rc,
          el('td', {text: m.role === 'member' ? '' : (m.two_fa ? t.tfaon : t.tfaoff)})]));
      });
      tb.appendChild(tbody); main.appendChild(el('div', {'class': 'hs-appx-tablewrap'}, [tb]));
    }).catch(function (er) { main.appendChild(el('p', {'class': 'muted', text: er.message})); });
  }
  function matrixView(main) {
    main.appendChild(el('h2', {text: t.matrix}));
    call('GET', '/matrix').then(function (j) {
      var tb = el('table', {'class': 'hs-appx-table'}), tbody = el('tbody');
      tb.appendChild(el('thead', {}, [el('tr', {}, [t.what, t.create, t.read, t.update, t.del, t.staffset, t.staffsee].map(function (x) { return el('th', {scope: 'col', text: x}); }))]));
      (j.matrix || []).forEach(function (m) {
        tbody.appendChild(el('tr', {}, [m.label, m.create, m.read, m.update, m['delete'], (m.staff_set || []).join(', '), (m.staff_see || []).join(', ')].map(function (x) { return el('td', {text: String(x || '')}); })));
      });
      tb.appendChild(tbody); main.appendChild(el('div', {'class': 'hs-appx-tablewrap'}, [tb]));
    }).catch(function (er) { main.appendChild(el('p', {'class': 'muted', text: er.message})); });
  }
  function auditView(main) {
    main.appendChild(el('h2', {text: t.audit}));
    call('GET', '/audit?limit=200').then(function (j) {
      var tb = el('table', {'class': 'hs-appx-table'}), tbody = el('tbody');
      tb.appendChild(el('thead', {}, [el('tr', {}, [t.when, t.who, t.what, ''].map(function (x) { return el('th', {scope: 'col', text: x}); }))]));
      (j.audit || []).forEach(function (a) {
        var c = C(a.list);
        tbody.appendChild(el('tr', {}, [el('td', {text: new Date(a.at).toLocaleString()}), el('td', {text: a.by}),
          el('td', {text: (c ? c.label : a.list) + ' · ' + a.op}), el('td', {text: (a.fields || []).join(', ')})]));
      });
      if (!(j.audit || []).length) main.appendChild(el('p', {'class': 'muted', text: t.empty}));
      tb.appendChild(tbody); main.appendChild(el('div', {'class': 'hs-appx-tablewrap'}, [tb]));
    }).catch(function (er) { main.appendChild(el('p', {'class': 'muted', text: er.message})); });
  }

  // ---------------------------------------------------------------- My account: devices, 2-step, my data
  function accountView(main) {
    main.appendChild(el('h2', {text: t.account}));
    main.appendChild(el('p', {text: (me.name || '') + ' · ' + (me.email && me.email.indexOf('@phone.local') < 0 ? me.email : (me.phone || '')) + ' · ' + me.role}));
    var dev = el('section', {'class': 'hs-appx-rel'}, [el('h3', {text: t.devices})]); main.appendChild(dev);
    call('GET', '/sessions').then(function (j) {
      var ul = el('ul');
      (j.sessions || []).forEach(function (s) {
        var li = el('li', {}, [s.device + ' · ' + (s.ip || '') + ' · ' + new Date(s.seen).toLocaleString() + (s.this ? ' (' + t.thisdev + ') ' : ' ')]);
        if (!s.this) li.appendChild(btn(t.end, 'btn-ghost', function () { call('POST', '/sessions/' + s.id + '/end').then(function () { li.remove(); }).catch(function (er) { alert(er.message); }); }));
        ul.appendChild(li);
      });
      dev.appendChild(ul);
      dev.appendChild(btn(t.outall, 'btn-ghost', function () { call('POST', '/logout-all').catch(function () {}).then(function () { setTok(''); me = null; all(); }); }));
    }).catch(function () { dev.remove(); });
    if (staff()) {
      var tf = el('section', {'class': 'hs-appx-rel'}, [el('h3', {text: t.tfa + ': ' + (me.two_fa ? t.tfaon : t.tfaoff)})]); main.appendChild(tf);
      if (!me.two_fa) tf.appendChild(btn(t.tfastart, 'btn-primary', function (e) {
        e.target.disabled = true;
        call('POST', '/2fa/start').then(function (j) {
          var f = el('form', {'class': 'hs-form'}, [el('p', {text: t.tfakey + ':'}), el('code', {'class': 'hs-key', text: j.secret}),
            el('p', {}, [el('a', {href: j.uri, text: 'otpauth ↗'})]), input({key: 'code', label: t.twofa, type: 'text', required: true}),
            el('button', {type: 'submit', 'class': 'btn btn-primary', text: t.tfaconfirm})]);
          f.addEventListener('submit', function (ev) {
            ev.preventDefault();
            call('POST', '/2fa/confirm', {code: f.querySelector('[name=code]').value}).then(function () { me.two_fa = true; main.textContent = ''; accountView(main); }).catch(function (er) { msg(f, er.message, false); });
          });
          tf.appendChild(f);
        }).catch(function (er) { e.target.disabled = false; alert(er.message); });
      }));
      else {
        var off = el('form', {'class': 'hs-form'}, [input({key: 'code', label: t.twofa, type: 'text', required: true}), el('button', {type: 'submit', 'class': 'btn btn-ghost', text: t.tfaremove})]);
        off.addEventListener('submit', function (ev) { ev.preventDefault(); call('POST', '/2fa/off', {code: off.querySelector('[name=code]').value}).then(function () { me.two_fa = false; main.textContent = ''; accountView(main); }).catch(function (er) { msg(off, er.message, false); }); });
        tf.appendChild(off);
      }
    }
    var ap = el('section', {'class': 'hs-appx-rel'}, [el('h3', {text: 'AutoPay'})]); main.appendChild(ap);   // v0.451 her plans
    call('GET', '/pay/plans').then(function (j) {
      var plans = j.plans || [];
      if (!plans.length) { ap.remove(); return; }
      plans.forEach(function (pl) {
        ap.appendChild(el('p', {}, [(pl.name || '') + ' · ' + (pl.amount_rs || '') + ' / ' + (pl.period || '') + ' ',
          btn(t.add, 'btn-primary', function (e) {
            e.target.disabled = true;
            call('POST', '/pay/plans/' + encodeURIComponent(pl.key) + '/subscribe').then(function (r) {
              var u = String(r.path || r.url || ''); if (u.charAt(0) === '/') u = new URL(u, API).href;
              if (/^https?:\/\//.test(u)) location.href = u;
            }).catch(function (er) { e.target.disabled = false; alert(er.message); });
          })]));
      });
      call('GET', '/pay/subs').then(function (k) {
        (k.subs || []).forEach(function (sb) {
          ap.appendChild(el('p', {'class': 'muted'}, [(sb.plan || '') + ': ' + (sb.status || '') + ' ',
            sb.status === 'cancelled' ? null : btn(t.cancel, 'btn-ghost', function (e) {
              if (!confirm(t.cancel + '?')) return;
              e.target.disabled = true;
              call('POST', '/pay/subs/' + encodeURIComponent(sb.id) + '/cancel').then(function () { main.textContent = ''; accountView(main); }).catch(function (er) { alert(er.message); });
            })]));
        });
      }).catch(function () {});
    }).catch(function () { ap.remove(); });
    var data = el('section', {'class': 'hs-appx-rel'}, [el('h3', {text: t.export})]); main.appendChild(data);
    data.appendChild(btn(t.export, 'btn-ghost', function () {
      call('GET', '/me/export').then(function (j) {
        var a = el('a', {href: URL.createObjectURL(new Blob([JSON.stringify(j, null, 2)], {type: 'application/json'})), download: 'my-data.json'});
        d.body.appendChild(a); a.click(); a.remove();
      }).catch(function (er) { alert(er.message); });
    }));
    data.appendChild(btn(t.delacc, 'btn-ghost hs-danger', function () {
      if (!confirm(t.delsure) || !confirm(t.delsure)) return;
      call('POST', '/me/delete').then(function () { setTok(''); me = null; all(); }).catch(function (er) { alert(er.message); });
    }));
  }

  // v0.357 DASHBOARD: the staff charts (assets/hoola-chart.js draws them; numbers come from /stats, staff only)
  function board(box, j) {
    var HC = window.HoolaChart, days = (j.days || []).map(function (x) { return x.slice(5); });
    var grid = el('div', {'class': 'hs-dash-grid'});
    box.appendChild(grid);
    (j.lists || []).forEach(function (c) {
      var card = el('div', {'class': 'card hs-dash-card'}, [el('h3', {text: c.label}), el('p', {'class': 'hs-dash-big', text: String(c.count)}),
        el('p', {'class': 'muted', text: t.perday})]);
      grid.appendChild(card);
      var ch = el('div'); card.appendChild(ch);
      if (HC) HC.live(ch, {type: 'bar', labels: days, series: [{name: c.label, values: c.days}], height: 150});
      if (c.mix && c.mix.items.some(function (x) { return x[1] > 0; })) {
        var m = el('div'); card.appendChild(el('p', {'class': 'muted', text: c.mix.field})); card.appendChild(m);
        if (HC) HC.live(m, {type: 'donut', labels: c.mix.items.map(function (x) { return x[0]; }),
          series: [{name: c.mix.field, values: c.mix.items.map(function (x) { return x[1]; })}], height: 180, totalLabel: t.total});
      }
      (c.sums || []).forEach(function (x) { card.appendChild(el('p', {}, [el('span', {'class': 'muted', text: x[0] + ': '}), el('strong', {text: HC ? HC.fmt(x[1]) : String(x[1])})])); });
      (c.yes || []).forEach(function (x) { card.appendChild(el('p', {}, [el('span', {'class': 'muted', text: x[0] + ': '}), el('strong', {text: x[1] + ' / ' + x[2]})])); });
    });
  }

  function all() {
    REFS = {};
    d.querySelectorAll('[data-hoola-app="login"]').forEach(login);
    d.querySelectorAll('[data-hoola-app="shell"]').forEach(function (b) { shell(b, b.getAttribute('data-area') === 'staff' ? 'staff' : 'member'); });
    d.querySelectorAll('[data-hoola-app="form"]').forEach(form);
    d.querySelectorAll('[data-hoola-app="admin"]').forEach(admin);
    lists();
  }
  function start() {
    call('GET', '/schema').then(function (s) {
      schema = s;
      return tok ? call('GET', '/me').then(function (j) { me = j.me; if (!me) setTok(''); }).catch(function () { setTok(''); }) : null;
    }).then(all).catch(function () {});
  }
  window.HoolaApp = {start: start};    // the React export starts it again after a route change
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start); else start();
})();
