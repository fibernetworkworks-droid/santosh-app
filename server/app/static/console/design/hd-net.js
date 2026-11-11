/* HOOLA DESIGN - hd-net.js
 *
 * HD.net: the live link between HD.store and the multiplayer room of ONE file.
 *
 *   connect(fileId)   close()   resync()
 *   status            'connecting' | 'live' | 'offline'            (the contract)
 *                     'offline-full'  offline and 5,000 edits are waiting: editing is stopped until it is back
 *                     'auth' (4401, not signed in) | 'forbidden' (4403) | 'notfound' (4404): no retry
 *   on('status', fn(status, info))      on('init', fn({cid, seq, file, users, reconnect}))
 *   on('presence', fn({type:'join'|'leave'|'pres'|'reset', cid, user}))
 *   on('file', fn(file))   on('comment', fn(frame))   on('reject', fn({ops}))   on('pending', fn(count))
 *   users  Map cid -> {cid, name, color, x, y, page, sel, vp}   (other people only)
 *   sendPresence({x, y, page, sel, vp})   at most 30 a second, the newest wins
 *   role 'edit' | 'view'      cid      file {id, name, role}      seq      pending() -> ops not confirmed yet
 *
 * The token (localStorage 'hoola.console.token') travels ONLY as a WebSocket subprotocol
 * ['hoola', 'hoola-key.<token>'], never in the address.
 *
 * Sending: every local tx of the store arrives through store.onOps(ops, b). Ops wait in a queue and go out
 * in order, at most ONE frame per animation frame, never while the socket is still busy with the last one.
 * A frame {t:'ops', n, ops} is remembered until its ack: rejected ops -> store.rollback(those op objects),
 * and when every op of a store batch b has been answered -> store.acked(b).
 * Lost connection: retry after 0.5, 1, 2, 4, 8, 8... seconds. The new init is loaded with
 * store.load(doc, cid, {keep:true}) (pending local edits are put back on top) and every un-acked op is
 * sent again, in the same order, under new frame numbers.
 */
(function () {
  'use strict';
  var W = window;
  var HD = W.HD = W.HD || {};
  var store = HD.store;

  var TOKEN_KEY = 'hoola.console.token';
  var MAX_FRAME_OPS = 1000, MAX_FRAME_CHARS = 512 * 1024, MAX_BUFFERED = 1024 * 1024;
  var MAX_OP_CHARS = 2 * 1024 * 1024;     /* the server refuses an op over 256 KB; one this big is not even sent */
  var OFFLINE_CAP = 5000;
  var PING_MS = 15000, SILENCE_MS = 30000, TICK_MS = 5000;
  var BACKOFF_MIN = 500, BACKOFF_MAX = 8000;
  var PRES_MS = 34;                       /* 30 a second */

  var em = new HD.Emitter();
  var net = HD.net = {status: 'offline', users: new Map(), role: null, cid: null, file: null, seq: 0};

  var ws = null, gen = 0;                 /* gen: events of an old socket are ignored */
  var fileId = null, want = false;        /* want: keep this file connected */
  var loaded = false;                     /* this file has had its first init */
  var fresh = false;                      /* the next init replaces everything (a version was restored) */
  var queue = [];                         /* [{op, b}] not sent yet */
  var flying = [];                        /* [{n, items}] sent, no ack yet */
  var left = new Map();                   /* b -> ops of that store batch still unanswered */
  var nextN = 1;
  var backoff = BACKOFF_MIN, retryT = null, tickT = null, flushT = null, flushOn = false;
  var lastHeard = 0, lastPing = 0, lastResync = 0;
  var presT = null, presLast = 0, presNext = null, resyncT = null;
  var full = false, offOps = null, offDesync = null, lastPendingZero = true;

  function now() { return Date.now(); }
  function setStatus(s, info) {
    if (net.status === s && !info) return;
    net.status = s;
    em.emit('status', s, info || {});
  }
  function token() {
    try { return W.localStorage ? W.localStorage.getItem(TOKEN_KEY) : null; } catch (e) { return null; }
  }
  function send(obj) {
    if (!ws || ws.readyState !== 1) return false;
    try { ws.send(typeof obj === 'string' ? obj : JSON.stringify(obj)); return true; } catch (e) { return false; }
  }
  function pendingCount() {
    var n = queue.length;
    for (var i = 0; i < flying.length; i++) n += flying[i].items.length;
    return n;
  }
  function notePending() {
    var n = pendingCount(), zero = n === 0;
    if (zero !== lastPendingZero) { lastPendingZero = zero; em.emit('pending', n); }
  }
  function canEdit() { return net.role === 'edit'; }
  function lockStore() { if (store) store.readOnly = full || (net.role !== null && !canEdit()); }

  /* ---------------------------------------------------------------- local ops -> the wire */
  function onLocal(ops, b) {
    if (!want || !ops || !ops.length) return;
    if (!loaded || !canEdit()) { store.acked(b); return; }    /* before the first init, or a viewer: nothing is sent */
    for (var i = 0; i < ops.length; i++) queue.push({op: ops[i], b: b});
    left.set(b, ops.length);
    notePending();
    if (net.status !== 'live' && !full && pendingCount() >= OFFLINE_CAP) {
      full = true;
      lockStore();
      setStatus('offline-full', {queued: pendingCount()});
    }
    scheduleFlush();
  }
  function scheduleFlush() {
    if (flushOn) return;
    flushOn = true;
    var done = false;
    function go() {
      if (done) return;
      done = true;
      if (flushT !== null) { W.clearTimeout(flushT); flushT = null; }
      flushOn = false;
      flush();
    }
    if (typeof W.requestAnimationFrame === 'function') W.requestAnimationFrame(go);
    flushT = W.setTimeout(go, 60);         /* a hidden tab gets no animation frames */
  }
  function flush() {
    if (!ws || ws.readyState !== 1 || net.status !== 'live' || !queue.length) return;
    if (!canEdit()) return;
    if (ws.bufferedAmount > MAX_BUFFERED) { scheduleFlush(); return; }          /* still busy: wait, keep coalescing */
    var items = [], parts = [], chars = 0, s, big = null, q;
    while (queue.length && items.length < MAX_FRAME_OPS) {
      s = JSON.stringify(queue[0].op);
      if (s.length > MAX_OP_CHARS) { (big || (big = [])).push(queue.shift()); continue; }
      if (items.length && chars + s.length > MAX_FRAME_CHARS) break;
      chars += s.length;
      parts.push(s);
      items.push(queue.shift());
    }
    if (big) {                              /* answered here, the way the server would: rejected */
      var ops = [];
      for (q = 0; q < big.length; q++) ops.push(big[q].op);
      store.rollback(ops);
      for (q = 0; q < big.length; q++) answered(big[q].b);
      em.emit('reject', {ops: ops, tooBig: true});
      notePending();
    }
    if (!items.length) { if (queue.length) scheduleFlush(); return; }
    var n = nextN++;
    flying.push({n: n, items: items});
    if (!send('{"t":"ops","n":' + n + ',"ops":[' + parts.join(',') + ']}')) {
      flying.pop();                         /* the socket died under us: the ops go back to the head of the queue */
      queue = items.concat(queue);
      return;
    }
    if (queue.length) scheduleFlush();
  }
  function answered(b) {                    /* one more op of store batch b has its answer */
    var c = left.get(b);
    if (c === undefined) return;
    if (c <= 1) { left.delete(b); store.acked(b); } else left.set(b, c - 1);
  }
  function onAck(msg) {
    var i, f = null;
    for (i = 0; i < flying.length; i++) if (flying[i].n === msg.n) { f = flying[i]; flying.splice(i, 1); break; }
    if (typeof msg.seq === 'number' && msg.seq > net.seq) net.seq = msg.seq;
    if (!f) return;
    var rej = msg.rejected, bad = [];
    if (rej && rej.length) {
      for (i = 0; i < rej.length; i++) if (f.items[rej[i]]) bad.push(f.items[rej[i]].op);
      if (bad.length) store.rollback(bad);
    }
    for (i = 0; i < f.items.length; i++) answered(f.items[i].b);
    if (bad.length) em.emit('reject', {ops: bad});
    notePending();
  }

  /* ---------------------------------------------------------------- the socket */
  function open() {
    retryT = null;
    if (!want || ws) return;
    var tk = token();
    if (!tk) { want = false; store.readOnly = true; setStatus('auth', {code: 4401}); return; }
    if (!full) setStatus('connecting');
    var url = (W.location.protocol === 'https:' ? 'wss' : 'ws') + '://' + W.location.host +
      '/api/design/ws?file=' + encodeURIComponent(fileId);
    var g = ++gen, sock;
    try { sock = new W.WebSocket(url, ['hoola', 'hoola-key.' + tk]); }
    catch (e) { lost(); return; }
    ws = sock;
    lastHeard = now(); lastPing = now();
    sock.onopen = function () { if (g === gen) lastHeard = now(); };
    sock.onmessage = function (ev) {
      if (g !== gen) return;
      lastHeard = now();
      var msg;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }
      if (msg && typeof msg === 'object') onFrame(msg);
    };
    sock.onerror = function () {};
    sock.onclose = function (ev) {
      if (g !== gen) return;
      ws = null;
      var code = ev && ev.code;
      if (code === 4401 || code === 4403 || code === 4404) {
        want = false;
        stopTimers();
        clearUsers();
        store.readOnly = true;                /* nothing typed now could ever be saved */
        setStatus(code === 4401 ? 'auth' : code === 4403 ? 'forbidden' : 'notfound', {code: code});
        return;
      }
      lost();
    };
    if (tickT === null) tickT = W.setInterval(tick, TICK_MS);
  }
  function lost() {                         /* the connection is gone: say so, try again later */
    if (ws) { gen++; try { ws.close(); } catch (e) {} ws = null; }
    clearUsers();
    if (!want) return;
    setStatus(full ? 'offline-full' : 'offline');
    if (retryT === null) {
      retryT = W.setTimeout(open, backoff);
      backoff = Math.min(backoff * 2, BACKOFF_MAX);
    }
  }
  function tick() {
    if (!ws || !want) return;
    var t = now();
    if (t - lastHeard >= SILENCE_MS) { lost(); return; }
    if (ws.readyState === 1 && t - lastPing >= PING_MS) { lastPing = t; send({t: 'ping'}); }
  }
  function stopTimers() {
    if (retryT !== null) { W.clearTimeout(retryT); retryT = null; }
    if (tickT !== null) { W.clearInterval(tickT); tickT = null; }
    if (presT !== null) { W.clearTimeout(presT); presT = null; }
    if (resyncT !== null) { W.clearTimeout(resyncT); resyncT = null; }
    presNext = null;
  }
  function clearUsers() {
    if (!net.users.size) return;
    net.users.clear();
    em.emit('presence', {type: 'reset'});
  }
  function putUser(u) {
    if (!u || u.cid === undefined || u.cid === net.cid) return null;
    var cur = net.users.get(u.cid) || {cid: u.cid, name: '', color: '#888888', x: null, y: null, page: null, sel: [], vp: null};
    if (typeof u.name === 'string') cur.name = u.name;
    if (typeof u.color === 'string') cur.color = u.color;
    net.users.set(u.cid, cur);
    return cur;
  }

  function onFrame(msg) {
    var u;
    switch (msg.t) {
      case 'init': onInit(msg); break;
      case 'ack': onAck(msg); break;
      case 'ops':
        if (typeof msg.seq === 'number' && msg.seq > net.seq) net.seq = msg.seq;
        if (loaded) store.applyRemote(msg.ops);
        break;
      case 'pres':
        if (msg.cid === undefined || msg.cid === net.cid) break;
        u = putUser({cid: msg.cid});
        if (typeof msg.x === 'number') u.x = msg.x;
        if (typeof msg.y === 'number') u.y = msg.y;
        if (msg.page !== undefined) u.page = msg.page;
        if (Array.isArray(msg.sel)) u.sel = msg.sel;
        if (Array.isArray(msg.vp)) u.vp = msg.vp;
        em.emit('presence', {type: 'pres', cid: msg.cid, user: u});
        break;
      case 'join':
        u = putUser(msg.user);
        if (u) em.emit('presence', {type: 'join', cid: u.cid, user: u});
        break;
      case 'leave':
        if (net.users.has(msg.cid)) {
          u = net.users.get(msg.cid);
          net.users.delete(msg.cid);
          em.emit('presence', {type: 'leave', cid: msg.cid, user: u});
        }
        break;
      case 'ping': send({t: 'pong'}); break;
      case 'pong': break;
      case 'file':
        if (!net.file) net.file = {id: fileId};
        if (typeof msg.name === 'string') net.file.name = msg.name;
        em.emit('file', net.file);
        break;
      case 'comment': em.emit('comment', msg); break;
      case 'reload': net.resync(true); break;
      default: break;
    }
  }
  function onInit(msg) {
    var keep = loaded && !fresh, i;
    net.cid = msg.cid;
    net.seq = typeof msg.seq === 'number' ? msg.seq : 0;
    net.file = msg.file || {id: fileId, name: '', role: 'edit'};
    net.role = net.file.role === 'view' ? 'view' : 'edit';
    net.users.clear();
    if (Array.isArray(msg.users)) for (i = 0; i < msg.users.length; i++) putUser(msg.users[i]);
    if (!canEdit()) keep = false;
    if (keep) {
      var back = [];                        /* everything un-acked goes out again, oldest first */
      for (i = 0; i < flying.length; i++) back = back.concat(flying[i].items);
      queue = back.concat(queue);
      flying = [];
      store.load(msg.doc, msg.cid, {keep: true});
    } else {
      queue = []; flying = []; left.clear();
      store.load(msg.doc, msg.cid);
    }
    loaded = true; fresh = false; full = false;
    backoff = BACKOFF_MIN;
    lockStore();
    setStatus('live');
    em.emit('init', {cid: net.cid, seq: net.seq, file: net.file, users: net.users, reconnect: keep});
    em.emit('presence', {type: 'reset'});
    notePending();
    scheduleFlush();
  }

  /* ---------------------------------------------------------------- public */
  net.on = function (evt, fn) { return em.on(evt, fn); };
  net.off = function (evt, fn) { em.off(evt, fn); };
  net.pending = function () { return pendingCount(); };

  net.connect = function (id) {
    if (id === undefined || id === null || id === '') return;
    id = String(id);
    if (want && fileId === id) return;
    net.close();
    fileId = id; want = true; loaded = false; fresh = false; full = false;
    backoff = BACKOFF_MIN;
    store.tracking(true);
    offOps = store.onOps(onLocal);
    offDesync = store.on('desync', function () { net.resync(false); });
    open();
  };

  net.close = function () {
    var was = fileId !== null;
    want = false;
    stopTimers();
    if (flushT !== null) { W.clearTimeout(flushT); flushT = null; }
    flushOn = false;
    if (ws) {
      if (queue.length && ws.readyState === 1 && net.status === 'live') { try { flush(); } catch (e) {} }   /* last edits out */
      gen++;
      try { ws.close(1000); } catch (e2) {}
      ws = null;
    }
    if (offOps) { offOps(); offOps = null; }
    if (offDesync) { offDesync(); offDesync = null; }
    fileId = null; loaded = false; fresh = false; full = false;
    queue = []; flying = []; left.clear();
    net.users.clear();
    net.role = null; net.cid = null; net.file = null; net.seq = 0;
    if (was) {
      store.tracking(false);
      store.readOnly = false;
      lastPendingZero = true;
      setStatus('offline', {closed: true});
    }
  };

  /* drop the socket and load the room again. replace = true: the document itself was replaced (a version was
     restored), so local undo and waiting edits are dropped; otherwise they are kept and sent again. */
  net.resync = function (replace) {
    if (!want) return;
    var t = now();
    if (!replace && t - lastResync < 2000) {                /* never a reconnect storm: this one waits its turn */
      if (resyncT === null) resyncT = W.setTimeout(function () { resyncT = null; net.resync(false); }, 2000 - (t - lastResync));
      return;
    }
    lastResync = t;
    if (replace) fresh = true;
    if (ws) { gen++; try { ws.close(); } catch (e) {} ws = null; }
    if (retryT !== null) { W.clearTimeout(retryT); retryT = null; }
    clearUsers();
    setStatus(full ? 'offline-full' : 'connecting');
    retryT = W.setTimeout(open, 0);
  };

  net.sendPresence = function (p) {
    if (!p || net.status !== 'live') return;
    presNext = p;
    var wait = PRES_MS - (now() - presLast);
    if (wait <= 0) firePresence();
    else if (presT === null) presT = W.setTimeout(firePresence, wait);
  };
  function firePresence() {
    if (presT !== null) { W.clearTimeout(presT); presT = null; }
    var p = presNext;
    presNext = null;
    if (!p || net.status !== 'live') return;
    presLast = now();
    var sel = p.sel !== undefined ? p.sel : (HD.sel ? HD.sel.ids : []);
    send({
      t: 'pres', x: p.x, y: p.y,
      page: p.page !== undefined ? p.page : (HD.sel ? HD.sel.page : null),
      sel: sel && sel.length > 200 ? sel.slice(0, 200) : sel,
      vp: p.vp
    });
  }

  if (typeof W.addEventListener === 'function') {
    W.addEventListener('online', function () {              /* the network is back: do not wait for the timer */
      if (want && !ws) { if (retryT !== null) { W.clearTimeout(retryT); retryT = null; } backoff = BACKOFF_MIN; open(); }
    });
    W.addEventListener('pagehide', function () {            /* leaving: push out what is still waiting */
      if (ws && ws.readyState === 1 && net.status === 'live') { try { while (queue.length) { var q = queue.length; flush(); if (queue.length === q) break; } } catch (e) {} }
    });
  }
})();
