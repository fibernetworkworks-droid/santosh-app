/* Hoola shop (v0.344 DUKAAN, MIT, Newtika). Cart + checkout + UPI for a Hoola website. Talks only to Hoola's shop API
   (the <meta name="hoola-shop"> address). The cart keeps only WHICH product and HOW MANY; every price, total and stock
   figure comes from the server. Customers pay in their own UPI app; "I have paid" + the UTR tells the shop, which checks
   its own account. Every value goes on the page as text. */
(function () {
  'use strict';
  var d = document, W = window;
  var meta = d.querySelector('meta[name="hoola-shop"]');
  if (!meta) return;
  var API = meta.getAttribute('content'), KEY = 'hoola-cart:' + API;
  var opt = function (k) { return meta.getAttribute('data-' + k) || ''; };
  var P = {}, cart = load(), box = null, btn = null;

  function load() { try { return JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { return {}; } }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(cart)); } catch (e) {} paintCount(); }
  function count() { var n = 0; for (var k in cart) n += cart[k]; return n; }
  function el(tag, cls, text) { var e = d.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function rs(p) { var r = Math.round(p) / 100; return '₹' + r.toLocaleString('en-IN', {maximumFractionDigits: 2}); }
  function req(method, path, body) {
    return fetch(API + path, {method: method, headers: body ? {'Content-Type': 'application/json'} : {}, body: body ? JSON.stringify(body) : undefined})
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok || j.ok === false) throw new Error(j.error || 'Kuch gadbad hui, dobara koshish kijiye.'); return j; }); });
  }

  function paintCount() {
    if (!btn) return;
    var n = count(); btn.querySelector('b').textContent = String(n);
    btn.hidden = n === 0 && !d.querySelector('[data-hoola-buy]');
    btn.setAttribute('aria-label', 'Cart: ' + n + ' items');
  }
  function paintPrices() {
    Array.prototype.forEach.call(d.querySelectorAll('[data-hoola-product]'), function (card) {
      var p = P[card.getAttribute('data-hoola-product')]; if (!p) return;
      var pr = card.querySelector('[data-hoola-price]'); if (pr) pr.textContent = p.price_text;
    });
    Array.prototype.forEach.call(d.querySelectorAll('[data-hoola-buy]'), function (b) {
      var p = P[b.getAttribute('data-hoola-buy')];
      if (p && !p.in_stock) { b.disabled = true; b.textContent = 'Stock khatam'; }
      var box2 = b.closest('.hs-buybox'); if (box2 && p) { var pr = box2.querySelector('[data-hoola-price]'); if (pr) pr.textContent = p.price_text; }
    });
  }

  function add(slug) {
    var p = P[slug];
    if (p && !p.in_stock) return;
    cart[slug] = Math.min(99, (cart[slug] || 0) + 1); save();
    toast((p ? p.title : 'Item') + ' cart mein daala');
  }
  function toast(t) {
    var n = el('div', 'hs-shop-toast', t); n.setAttribute('role', 'status'); d.body.appendChild(n);
    setTimeout(function () { n.remove(); }, 2200);
  }

  function open(view) {
    if (!box) {
      box = el('div', 'hs-shop'); box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-label', 'Cart');
      box.addEventListener('click', function (e) { if (e.target === box) close(); });
      box.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
      d.body.appendChild(box);
    }
    while (box.firstChild) box.removeChild(box.firstChild);
    var panel = el('div', 'hs-shop-in'); box.appendChild(panel);
    var x = el('button', 'hs-shop-x', 'Band karein'); x.type = 'button'; x.addEventListener('click', close); panel.appendChild(x);
    view(panel); box.hidden = false;
    var f = panel.querySelector('input,button:not(.hs-shop-x)'); (f || x).focus();
  }
  function close() { if (box) box.hidden = true; if (btn) btn.focus(); }

  function cartView(panel) {
    panel.appendChild(el('h2', '', 'Aapka cart'));
    var slugs = Object.keys(cart).filter(function (k) { return cart[k] > 0; });
    if (!slugs.length) { panel.appendChild(el('p', 'muted', 'Cart khaali hai.')); return; }
    var list = el('ul', 'hs-cart'), sub = 0;
    slugs.forEach(function (s) {
      var p = P[s], q = cart[s];
      var li = el('li'); li.appendChild(el('span', 'hs-cart-t', p ? p.title + (p.unit ? ' (' + p.unit + ')' : '') : 'Yeh cheez ab nahi milti'));
      var minus = el('button', '', '−'), plus = el('button', '', '+'), qty = el('b', '', String(q));
      minus.type = plus.type = 'button'; minus.setAttribute('aria-label', 'Ek kam'); plus.setAttribute('aria-label', 'Ek zyada');
      minus.addEventListener('click', function () { cart[s] = q - 1; if (cart[s] <= 0) delete cart[s]; save(); open(cartView); });
      plus.addEventListener('click', function () { cart[s] = Math.min(99, q + 1); save(); open(cartView); });
      var qbox = el('span', 'hs-cart-q'); qbox.appendChild(minus); qbox.appendChild(qty); qbox.appendChild(plus); li.appendChild(qbox);
      li.appendChild(el('span', 'hs-cart-a', p ? rs(p.price * q) : ''));
      if (p) sub += p.price * q;
      list.appendChild(li);
    });
    panel.appendChild(list);
    panel.appendChild(el('p', 'hs-cart-sub', 'Saaman: ' + rs(sub)));
    var dl = opt('delivery'), fr = opt('free');
    if (dl && dl !== '₹0') panel.appendChild(el('p', 'muted', 'Delivery: ' + dl + (fr ? ' (' + fr + ' se upar free)' : '') + ' - final total order par.'));
    var go = el('button', 'btn btn-primary', 'Aage badhein'); go.type = 'button';
    go.addEventListener('click', function () { open(checkoutView); }); panel.appendChild(go);
  }

  function field(form, label, name, type, req2, extra) {
    var l = el('label'); l.appendChild(el('span', '', label));
    var i = d.createElement(type === 'textarea' ? 'textarea' : 'input');
    if (type !== 'textarea') i.type = type; i.name = name; if (req2) i.required = true;
    for (var k in (extra || {})) i.setAttribute(k, extra[k]);
    l.appendChild(i); form.appendChild(l); return i;
  }
  function checkoutView(panel) {
    panel.appendChild(el('h2', '', 'Order karein'));
    var f = el('form', 'hs-form hs-checkout'); f.noValidate = false;
    field(f, 'Naam', 'name', 'text', true, {autocomplete: 'name'});
    field(f, 'Mobile (10 ank)', 'phone', 'tel', true, {inputmode: 'numeric', autocomplete: 'tel', pattern: '[6-9][0-9]{9}', maxlength: '10'});
    var pick = null;
    if (opt('pickup') === '1') {
      var pl = el('label', 'hs-check'); pick = d.createElement('input'); pick.type = 'checkbox'; pick.name = 'pickup';
      pl.appendChild(pick); pl.appendChild(el('span', '', 'Dukaan se khud le jaunga')); f.appendChild(pl);
    }
    var addr = field(f, 'Poora pata', 'address', 'textarea', true, {autocomplete: 'street-address', rows: '3'});
    var pin = field(f, 'Pincode', 'pincode', 'text', true, {inputmode: 'numeric', pattern: '[1-9][0-9]{5}', maxlength: '6', autocomplete: 'postal-code'});
    if (pick) pick.addEventListener('change', function () { addr.required = pin.required = !pick.checked; addr.closest('label').hidden = pin.closest('label').hidden = pick.checked; });
    field(f, 'Kuch kehna hai? (optional)', 'note', 'text', false);
    var hp = d.createElement('input'); hp.name = 'website'; hp.className = 'hp'; hp.tabIndex = -1; hp.autocomplete = 'off'; f.appendChild(hp);
    var pays = el('fieldset', 'hs-pay-ways'); pays.appendChild(el('legend', '', 'Payment'));
    var ways = [];
    if (opt('upi') === '1') ways.push(['upi', 'UPI (GPay, PhonePe, Paytm...)']);
    if (opt('cod') === '1') ways.push(['cod', 'Cash on delivery']);
    ways.forEach(function (w, i) {
      var l = el('label', 'hs-check'), r = d.createElement('input'); r.type = 'radio'; r.name = 'method'; r.value = w[0]; if (!i) r.checked = true;
      l.appendChild(r); l.appendChild(el('span', '', w[1])); pays.appendChild(l);
    });
    f.appendChild(pays);
    var msg = el('p', 'hs-form-msg'); msg.setAttribute('role', 'status');
    var sub = el('button', 'btn btn-primary', 'Order bhejiye'); sub.type = 'submit';
    f.appendChild(sub); f.appendChild(msg); panel.appendChild(f);
    if (!ways.length) { sub.disabled = true; msg.textContent = 'Online order abhi band hai; dukaan ko call kijiye.'; }
    f.addEventListener('submit', function (e) {
      e.preventDefault(); if (!f.reportValidity()) return;
      var fd = new FormData(f), body = {items: Object.keys(cart).map(function (s) { return {slug: s, qty: cart[s]}; })};
      ['name', 'phone', 'address', 'pincode', 'note', 'method', 'website'].forEach(function (k) { body[k] = fd.get(k) || ''; });
      body.pickup = !!(pick && pick.checked);
      sub.disabled = true; msg.textContent = 'Bhej rahe hain...';
      req('POST', '/order', body).then(function (o) {
        cart = {}; save(); remember(o); open(function (p2) { doneView(p2, o); });
      }).catch(function (er) { msg.textContent = er.message; sub.disabled = false; refresh(); });
    });
  }

  function remember(o) { try { localStorage.setItem(KEY + ':last', JSON.stringify({n: o.number, t: o.token})); } catch (e) {} }
  function trackLink(o) { return location.origin + location.pathname + '?order=' + encodeURIComponent(o.number) + '&t=' + encodeURIComponent(o.token); }

  function doneView(panel, o) {
    panel.appendChild(el('h2', '', 'Order ' + o.number));
    panel.appendChild(el('p', 'hs-status', o.status_text));
    var ul = el('ul', 'hs-cart');
    (o.items || []).forEach(function (x) { var li = el('li'); li.appendChild(el('span', 'hs-cart-t', x.title + ' x ' + x.qty)); li.appendChild(el('span', 'hs-cart-a', x.amount)); ul.appendChild(li); });
    panel.appendChild(ul);
    panel.appendChild(el('p', 'hs-cart-sub', 'Total: ' + o.total + (o.delivery && o.delivery !== '₹0' ? ' (delivery ' + o.delivery + ')' : '')));
    if (o.pay && o.status === 'new') {
      var pay = el('div', 'hs-shop-pay');
      pay.appendChild(el('p', '', o.pay.amount + ' bhejiye: ' + o.pay.vpa));
      var img = d.createElement('img'); img.alt = 'UPI QR code'; img.width = 180; img.height = 180;
      if (/^data:image\/svg\+xml;base64,/.test(o.pay.qr || '')) img.src = o.pay.qr;
      pay.appendChild(img);
      if (/^upi:\/\/pay\?/.test(o.pay.link || '')) { var a = el('a', 'btn btn-primary', 'UPI app mein pay karein'); a.href = o.pay.link; pay.appendChild(a); }
      var f = el('form', 'hs-form'); var u = field(f, 'Pay karne ke baad UTR / reference number', 'utr', 'text', true, {inputmode: 'text', maxlength: '22'});
      var b = el('button', 'btn btn-ghost', 'Maine pay kar diya'); b.type = 'submit'; f.appendChild(b);
      var m = el('p', 'hs-form-msg'); m.setAttribute('role', 'status'); f.appendChild(m);
      f.addEventListener('submit', function (e) {
        e.preventDefault(); b.disabled = true;
        req('POST', '/order/' + encodeURIComponent(o.number) + '/paid', {token: o.token, utr: u.value}).then(function (o2) {
          o2.token = o.token; open(function (p2) { doneView(p2, o2); });
        }).catch(function (er) { m.textContent = er.message; b.disabled = false; });
      });
      pay.appendChild(f); panel.appendChild(pay);
    } else if (o.status === 'payment_told') {
      panel.appendChild(el('p', 'muted', 'Payment ki khabar dukaan ko mil gayi; woh check karke order pakka karenge.'));
    } else if (o.method === 'cod' && o.status === 'new') {
      panel.appendChild(el('p', 'muted', 'Cash on delivery: saaman milne par payment kijiye.'));
    }
    var t = el('p', 'hs-track'); t.appendChild(el('span', '', 'Order ka haal yahan dekhiye: '));
    var ta = el('a', '', 'yeh link'); ta.href = trackLink(o); t.appendChild(ta); panel.appendChild(t);
  }

  function refresh() {
    return req('GET', '/products').then(function (j) {
      P = {}; (j.products || []).forEach(function (p) { P[p.slug] = p; });
      for (var k in cart) if (!P[k]) delete cart[k];
      save(); paintPrices();
    }).catch(function () {});
  }

  function start() {
    if (!btn) {
      btn = el('button', 'hs-cart-b'); btn.type = 'button';
      btn.appendChild(el('span', '', 'Cart ')); btn.appendChild(el('b', '', '0'));
      btn.addEventListener('click', function () { open(cartView); });
      d.body.appendChild(btn);
      d.addEventListener('click', function (e) {
        var b = e.target.closest && e.target.closest('[data-hoola-buy]');
        if (b && !b.disabled) { e.preventDefault(); add(b.getAttribute('data-hoola-buy')); }
      });
    }
    paintCount();
    refresh();
    var q = new URLSearchParams(location.search), n = q.get('order'), t = q.get('t');
    if (n && t) req('GET', '/order/' + encodeURIComponent(n) + '?t=' + encodeURIComponent(t)).then(function (o) {
      o.token = t; open(function (p) { doneView(p, o); });
    }).catch(function (er) { toast(er.message); });
  }
  W.HoolaShop = {start: start};
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start); else start();
})();
