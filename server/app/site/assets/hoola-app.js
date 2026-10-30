/* Hoola web app (v0.303, MIT, Newtika): login / sign up, forms, lists and the staff panel of a Hoola-built website.
   Talks only to Hoola's API (meta[name=hoola-app]); the login token lives in this browser only. Every value from the
   server is put on the page as TEXT (never as HTML), and the server checks every rule again on every call. */
(function () {
  'use strict';
  var d = document, meta = d.querySelector('meta[name="hoola-app"]');
  if (!meta) return;
  var API = meta.getAttribute('content'), LANG = meta.getAttribute('data-lang') || 'en', KEY = 'hoola-app:' + API;
  var T = {
    en: {login: 'Log in', signup: 'Create account', email: 'Email', pw: 'Password (8+ characters)', name: 'Your name',
      hi: 'Hello', out: 'Log out', send: 'Submit', saved: 'Saved!', fail: 'Could not save', need: 'Please log in first.',
      empty: 'Nothing here yet.', edit: 'Edit', del: 'Delete', sure: 'Delete this entry?', role: 'Role', members: 'Members',
      staffonly: 'Log in with a staff account to see this.', save: 'Save', cancel: 'Cancel', yes: 'Yes', no: 'No'},
    hinglish: {login: 'Login', signup: 'Naya account', email: 'Email', pw: 'Password (8+ akshar)', name: 'Aapka naam',
      hi: 'Namaste', out: 'Logout', send: 'Bhejiye', saved: 'Save ho gaya!', fail: 'Save nahi hua', need: 'Pehle login kijiye.',
      empty: 'Abhi kuch nahi.', edit: 'Badlo', del: 'Hatao', sure: 'Yeh entry hata dein?', role: 'Role', members: 'Members',
      staffonly: 'Yeh dekhne ke liye staff account se login kijiye.', save: 'Save', cancel: 'Rehne do', yes: 'Haan', no: 'Nahi'},
    hi: {login: 'लॉगिन', signup: 'नया अकाउंट', email: 'ईमेल', pw: 'पासवर्ड (8+ अक्षर)', name: 'आपका नाम', hi: 'नमस्ते',
      out: 'लॉगआउट', send: 'भेजिए', saved: 'सेव हो गया!', fail: 'सेव नहीं हुआ', need: 'पहले लॉगिन कीजिए।', empty: 'अभी कुछ नहीं।',
      edit: 'बदलें', del: 'हटाएँ', sure: 'यह एंट्री हटा दें?', role: 'रोल', members: 'मेंबर', staffonly: 'स्टाफ अकाउंट से लॉगिन कीजिए।',
      save: 'सेव', cancel: 'रहने दें', yes: 'हाँ', no: 'नहीं'}
  };
  var t = T[LANG] || (LANG === 'mr' ? T.hi : T.en);
  var tok = '';
  try { tok = localStorage.getItem(KEY) || ''; } catch (e) {}
  var me = null, schema = null;

  function el(tag, attrs, kids) {
    var x = d.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { if (k === 'text') x.textContent = attrs[k]; else if (attrs[k] !== null && attrs[k] !== undefined) x.setAttribute(k, attrs[k]); });
    (kids || []).forEach(function (c) { if (c) x.appendChild(c); });
    return x;
  }
  function call(method, path, body) {
    var h = {'Content-Type': 'application/json'};
    if (tok) h.Authorization = 'Bearer ' + tok;
    return fetch(API + path, {method: method, headers: h, body: body ? JSON.stringify(body) : undefined}).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok) { var e = new Error(j.error || t.fail); e.code = r.status; throw e; } return j; });
    });
  }
  function setTok(v) { tok = v || ''; try { if (tok) localStorage.setItem(KEY, tok); else localStorage.removeItem(KEY); } catch (e) {} }
  function msg(box, text, ok) { var p = box.querySelector('.hs-form-msg') || box.appendChild(el('p', {'class': 'hs-form-msg', role: 'status'})); p.textContent = text; p.className = 'hs-form-msg ' + (ok ? 'ok' : 'bad'); }
  function C(key) { return (schema.collections || []).filter(function (c) { return c.key === key; })[0]; }
  function staff() { return !!(me && (me.role === 'staff' || me.role === 'admin')); }

  function input(f, val) {
    var id = 'hf-' + f.key + '-' + Math.random().toString(36).slice(2, 7), box;
    if (f.type === 'long_text') box = el('textarea', {id: id, name: f.key, rows: '3'});
    else if (f.type === 'choice') { box = el('select', {id: id, name: f.key}); f.options.forEach(function (o) { box.appendChild(el('option', {value: o, text: o})); }); }
    else if (f.type === 'yes_no') box = el('input', {id: id, name: f.key, type: 'checkbox'});
    else box = el('input', {id: id, name: f.key, type: {number: 'number', phone: 'tel', email: 'email', date: 'date'}[f.type] || 'text',
      inputmode: f.type === 'phone' ? 'numeric' : null});
    if (f.required && f.type !== 'yes_no') box.required = true;
    if (val !== undefined && val !== null) { if (f.type === 'yes_no') box.checked = !!val; else box.value = val; }
    else if (f.default) box.value = f.default;
    return el('label', {'for': id}, [d.createTextNode(f.label + ' '), box]);
  }
  function values(form, c) {
    var out = {};
    // by name, never form.elements[key]: a field called 'item' or 'length' would hit the collection's own method
    c.fields.forEach(function (f) { var x = form.querySelector('[name="' + f.key + '"]'); if (!x) return; out[f.key] = f.type === 'yes_no' ? x.checked : x.value; });
    return out;
  }

  // ---------------------------------------------------------------- login / sign up
  function login(box) {
    box.textContent = '';
    if (me) {
      var out = el('button', {type: 'button', 'class': 'btn btn-ghost', text: t.out});
      out.addEventListener('click', function () { call('POST', '/logout').catch(function () {}).then(function () { setTok(''); me = null; all(); }); });
      box.appendChild(el('p', {'class': 'hs-app-me'}, [d.createTextNode(t.hi + ', ' + (me.name || me.email) + ' '), out]));
      return;
    }
    var mode = 'login', f = el('form', {'class': 'hs-form hs-app-login'});
    function draw() {
      f.textContent = '';
      var tabs = el('div', {'class': 'btns', role: 'tablist'});
      ['login', 'signup'].forEach(function (m) {
        if (m === 'signup' && schema.signup === false) return;
        var b = el('button', {type: 'button', role: 'tab', 'aria-selected': String(mode === m), 'class': 'btn ' + (mode === m ? 'btn-primary' : 'btn-ghost'), text: t[m]});
        b.addEventListener('click', function () { mode = m; draw(); }); tabs.appendChild(b);
      });
      f.appendChild(tabs);
      if (mode === 'signup') f.appendChild(input({key: 'name', label: t.name, type: 'text'}));
      f.appendChild(input({key: 'email', label: t.email, type: 'email', required: true}));
      var pw = input({key: 'password', label: t.pw, type: 'text', required: true}); pw.querySelector('input').type = 'password';
      pw.querySelector('input').autocomplete = mode === 'signup' ? 'new-password' : 'current-password';
      f.appendChild(pw);
      f.appendChild(el('button', {type: 'submit', 'class': 'btn btn-primary', text: t[mode]}));
    }
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = function (n) { var x = f.querySelector('[name="' + n + '"]'); return x ? x.value : ''; };
      var b = {email: q('email'), password: q('password'), name: q('name')};
      call('POST', '/' + mode, b).then(function (j) { setTok(j.token); me = j.me; all(); }).catch(function (er) { msg(f, er.message, false); });
    });
    draw(); box.appendChild(f);
  }

  // ---------------------------------------------------------------- a form for one list
  function form(box) {
    var c = C(box.getAttribute('data-c')); box.textContent = ''; if (!c) return;
    if (c.rules.create === 'member' && !me) { box.appendChild(el('p', {'class': 'muted', text: t.need})); return; }
    if (c.rules.create === 'admin' && !staff()) return;
    var f = el('form', {'class': 'hs-form'});
    c.fields.forEach(function (x) { if (!x.admin_only || staff()) f.appendChild(input(x)); });
    f.appendChild(el('button', {type: 'submit', 'class': 'btn btn-primary', text: t.send}));
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      call('POST', '/c/' + c.key, values(f, c)).then(function () { f.reset(); msg(f, t.saved, true); lists(); }).catch(function (er) { msg(f, er.message, false); });
    });
    box.appendChild(f);
  }

  // ---------------------------------------------------------------- a list (cards)
  function list(box, c, rows, editable) {
    box.textContent = '';
    if (!rows.length) { box.appendChild(el('p', {'class': 'muted', text: t.empty})); return; }
    var g = el('div', {'class': 'grid g2 hs-app-list'});
    rows.forEach(function (r) {
      var card = el('article', {'class': 'card'});
      c.fields.forEach(function (f) {
        var v = r[f.key]; if (v === '' || v === null || v === undefined) return;
        if (f.type === 'yes_no') v = v ? t.yes : t.no;
        card.appendChild(el('p', {}, [el('strong', {text: f.label + ': '}), d.createTextNode(String(v))]));
      });
      if (r.created) card.appendChild(el('p', {'class': 'muted', text: new Date(r.created).toLocaleString()}));
      if (editable(r)) {
        var eb = el('button', {type: 'button', 'class': 'btn btn-ghost', text: t.edit}), db = el('button', {type: 'button', 'class': 'btn btn-ghost', text: t.del});
        eb.addEventListener('click', function () { editor(card, c, r); });
        db.addEventListener('click', function () { if (confirm(t.sure)) call('DELETE', '/c/' + c.key + '/' + r.id).then(all).catch(function (er) { alert(er.message); }); });
        card.appendChild(el('div', {'class': 'btns'}, [eb, db]));
      }
      g.appendChild(card);
    });
    box.appendChild(g);
  }
  function editor(card, c, r) {
    var f = el('form', {'class': 'hs-form'});
    c.fields.forEach(function (x) { if (!x.admin_only || staff()) f.appendChild(input(x, r[x.key])); });
    var no = el('button', {type: 'button', 'class': 'btn btn-ghost', text: t.cancel});
    f.appendChild(el('div', {'class': 'btns'}, [el('button', {type: 'submit', 'class': 'btn btn-primary', text: t.save}), no]));
    no.addEventListener('click', all);
    f.addEventListener('submit', function (e) { e.preventDefault(); call('PATCH', '/c/' + c.key + '/' + r.id, values(f, c)).then(all).catch(function (er) { msg(f, er.message, false); }); });
    card.textContent = ''; card.appendChild(f);
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

  // ---------------------------------------------------------------- the staff panel (/admin/)
  function admin(box) {
    box.textContent = '';
    if (!staff()) { if (me) box.appendChild(el('p', {'class': 'muted', text: t.staffonly})); return; }
    (schema.collections || []).forEach(function (c) {
      var sec = el('section', {'class': 'hs-app-admin'}, [el('h2', {text: c.label})]), inner = el('div');
      sec.appendChild(inner); box.appendChild(sec);
      call('GET', '/c/' + c.key).then(function (j) { list(inner, c, j.rows || [], function () { return true; }); });
    });
    call('GET', '/members').then(function (j) {
      var sec = el('section', {'class': 'hs-app-admin'}, [el('h2', {text: t.members})]), ul = el('ul');
      (j.members || []).forEach(function (m) {
        var li = el('li', {}, [d.createTextNode((m.name || m.email) + ' · ' + m.email + ' · ')]);
        if (j.admin && me && m.id !== me.id) {
          var s = el('select', {'aria-label': t.role}); ['member', 'staff', 'admin'].forEach(function (r) { var o = el('option', {value: r, text: r}); if (r === m.role) o.selected = true; s.appendChild(o); });
          s.addEventListener('change', function () { call('POST', '/members/' + m.id + '/role', {role: s.value}).catch(function (er) { alert(er.message); }); });
          li.appendChild(s);
        } else li.appendChild(d.createTextNode(m.role));
        ul.appendChild(li);
      });
      sec.appendChild(ul); box.appendChild(sec);
    }).catch(function () {});
  }

  function all() {
    d.querySelectorAll('[data-hoola-app="login"]').forEach(login);
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
