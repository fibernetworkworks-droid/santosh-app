/* HOOLA DESIGN - hd-net.js
 *
 * HD.net: the live link between HD.store and the multiplayer room of ONE file.
 *
 *   connect(fileId)   close()   resync()
 *   connect(fileId, {share: token})    a VIEW-ONLY guest of a share link: no sign-in, the socket is
 *                     /api/design/ws?share=<token>; net.share is the token (null for a signed-in editor)
 *   status            'connecting' | 'live' | 'offline'            (the contract)
 *                     'offline-full'  offline and 5,000 edits are waiting: editing is stopped until it is back
 *                     'auth' (4401, not signed in) | 'forbidden' (4403) | 'notfound' (4404): no retry
 *   on('status', fn(status, info))      on('init', fn({cid, seq, file, users, reconnect}))
 *   on('presence', fn({type:'join'|'leave'|'pres'|'reset', cid, user}))
 *   on('file', fn(file))   on('comment', fn(frame))   on('reject', fn({ops}))   on('pending', fn(count))
 *   on('reload', fn())                  a version was restored: the document is being fetched again (the view stays)
 *   users  Map cid -> {cid, name, color, x, y, page, sel, vp}   (other people only)
 *   extra  Map cid -> {vs, chat, chatAt, spot, at}   the same people: vs = their canvas size [w, h], chat =
 *                     cursor chat text (chatAt = when it last changed), spot = "follow me" stamp, at = when
 *                     they were last heard from
 *   sendPresence({x, y, page, sel, vp})   at most 30 a second, the newest wins
 *   setPresence({vs, chat, spot})        extra fields that ride on EVERY presence frame from now on (null removes
 *                     one); sent at once. Only the keys in PRES_EXTRA travel.
 *   hold() -> bool    look at another document for a while (a version preview): from now on nothing is sent, the
 *                     ops of other people are NOT applied to the store, and the store is read only. Refused
 *                     (false) while edits are still waiting for the server. The socket stays open: presence and
 *                     comments keep flowing. held is true meanwhile.
 *   release()         end of hold(): the live document is fetched again (like a reload), whatever the store holds.
 *   role 'edit' | 'view'      cid      file {id, name, role}      seq      pending() -> ops not confirmed yet
 *   me {cid, name, color}     this person, as the others see them (the server's init.you)
 *
 * The token (localStorage 'hoola.console.token') travels ONLY as a WebSocket subprotocol
 * ['hoola', 'hoola-key.<token>'], never in the address.
 *
 * Sending: every local tx of the store arrives through store.onOps(ops, b). Ops wait in a queue and go out
 * in order, at most ONE frame per animation frame, never while the socket is still busy with the last one.
 * A frame {t:'ops', n, ops} is remembered until its ack: accepted ops -> store.acked(those op objects),
 * rejected ops -> store.rollback(those op objects).
 * Lost connection: retry after 0.5, 1, 2, 4, 8, 8... seconds. The new init is loaded with
 * store.load(doc, cid, {keep:true}) (pending local edits are put back on top) and every un-acked op is
 * sent again, in the same order, under new frame numbers.
 *
 * D9b SPEED (both are asked for in the address, so an old server simply ignores them):
 *   ?lazy=1[&pages=<ids>]  a big file may come PAGE BY PAGE: init then carries `lazy` (the page ids whose layers
 *                     are not in it) and `pages` [{id, name, count}]; net asks for the missing pages one at a time -
 *                     the one she opens at once, the rest when the page is idle - with {t:'page', id} and puts each
 *                     answer in with store.loadPage. store 'need' (a layer of a missing page moved onto a page we
 *                     hold) asks for that page again. On a reconnect it asks for the pages it already holds.
 *   ?enc=c1           the compact op frames (keys as numbers, ops as arrays; see KEYS below and server
 *                     app/design/wire.py). Used only when init.use === 'c1'; JSON frames are always understood.
 *   on('page', fn({id, left}))   one page arrived (left = pages still missing)      pages  init.pages
 *   loading() -> ids of the pages not here yet        options {lazy: true, c1: true}  (set before connect)
 *   wire  {bytesIn, bytesOut, framesIn, framesOut}   what went over this socket (the perf harness reads it)
 */
(function () {
  'use strict';
  var W = window;
  var HD = W.HD = W.HD || {};
  var store = HD.store;

  var hasOwn = Object.prototype.hasOwnProperty;
  var TOKEN_KEY = 'hoola.console.token';
  var MAX_FRAME_OPS = 1000, MAX_FRAME_CHARS = 512 * 1024, MAX_BUFFERED = 1024 * 1024;
  var MAX_OP_CHARS = 2 * 1024 * 1024;     /* the server refuses an op over 256 KB; one this big is not even sent */
  var OFFLINE_CAP = 5000;
  var PING_MS = 15000, SILENCE_MS = 30000, TICK_MS = 5000;
  var BACKOFF_MIN = 500, BACKOFF_MAX = 8000;
  var PRES_MS = 34;                       /* 30 a second */
  var PRES_EXTRA = ['vs', 'chat', 'spot'];

  var em = new HD.Emitter();
  var net = HD.net = {status: 'offline', users: new Map(), extra: new Map(), role: null, cid: null, file: null, seq: 0, share: null, held: false,
    options: {lazy: true, c1: true}, pages: null, wire: {bytesIn: 0, bytesOut: 0, framesIn: 0, framesOut: 0}};

  /* ---------------------------------------------------------------- D9b: the compact op frames (c1)
   * KEYS must be exactly app/design/wire.py KEYS (a test holds them equal). */
  var KEYS = ['type', 'parent', 'idx', 'name', 'x', 'y', 'w', 'h', 'rot', 'flipH', 'flipV', 'visible', 'locked', 'opacity',
    'blend', 'mask', 'fills', 'strokes', 'strokeWeight', 'strokeAlign', 'strokeCap', 'strokeJoin', 'dash', 'radius',
    'effects', 'clip', 'layout', 'grids', 'bool', 'sizeH', 'sizeV', 'layoutPos', 'minW', 'maxW', 'minH', 'maxH',
    'cons', 'sides', 'ratio', 'path', 'fillRule', 'chars', 'font', 'fontSize', 'fontWeight', 'italic', 'lineHeight',
    'letterSpacing', 'align', 'alignV', 'autoResize', 'decoration', 'textCase', 'runs', 'comp', 'ov', 'desc', 'styles',
    'vars', 'modes', 'fillStyle', 'textStyle', 'effectStyle', 'bind', 'reactions', 'protoStart', 'scroll', 'fixed',
    'exports', 'bg', 'guides'];
  var KEY_NO = Object.create(null);
  (function () { for (var i = 0; i < KEYS.length; i++) KEY_NO[KEYS[i]] = i; })();
  function encOp(op) {
    if (op.del) return [op.id];
    var out = [op.id], p = op.p, k, n;
    for (k in p) { if (!hasOwn.call(p, k)) continue; n = KEY_NO[k]; out.push(n === undefined ? k : n, p[k]); }
    if (out.length === 1) out.push(-1);
    return out;
  }
  function decOp(a) {
    if (!Array.isArray(a) || !a.length || typeof a[0] !== 'string') return null;
    if (a.length === 1) return {id: a[0], del: 1};
    var p = {}, op = {id: a[0], p: p}, k;
    for (var i = 1; i + 1 < a.length; i += 2) {
      k = a[i];
      if (typeof k === 'number') { if (k === -2) { op.ex = 1; continue; } k = KEYS[k]; if (k === undefined) return null; }
      else if (typeof k !== 'string') return null;
      p[k] = a[i + 1];
    }
    return op;
  }
  function decFrame(a) {                    /* a c1 frame -> the JSON frame it stands for; null = not one we know */
    var ops, i;
    if (a[0] === 2 && Array.isArray(a[3])) {
      ops = new Array(a[3].length);
      for (i = 0; i < ops.length; i++) ops[i] = decOp(a[3][i]);
      return {t: 'ops', seq: a[1], by: a[2], ops: ops.filter(function (o) { return o !== null; })};
    }
    if (a[0] === 3) return {t: 'ack', n: a[1], seq: a[2], rejected: Array.isArray(a[3]) ? a[3] : [], ex: Array.isArray(a[4]) ? a[4] : null};
    return null;
  }
  net.codec = {KEYS: KEYS, encOp: encOp, decOp: decOp, decFrame: decFrame};

  var ws = null, gen = 0;                 /* gen: events of an old socket are ignored */
  var fileId = null, want = false;        /* want: keep this file connected */
  var loaded = false;                     /* this file has had its first init */
  var fresh = false;                      /* the next init replaces everything (a version was restored) */
  var queue = [];                         /* [{op, b}] not sent yet */
  var flying = [];                        /* [{n, items}] sent, no ack yet */
  var nextN = 1;
  var backoff = BACKOFF_MIN, retryT = null, tickT = null, flushT = null, flushOn = false;
  var lastHeard = 0, lastPing = 0, lastResync = 0;
  var presT = null, presLast = 0, presNext = null, resyncT = null;
  var full = false, offOps = null, offDesync = null, lastPendingZero = true;
  var quiet = false;                      /* a reload is fetching the document again: not shown as a lost connection */
  var shareToken = null;                  /* a share link's token: this visit is a view-only guest */
  var held = false;                       /* hold(): the store shows something else, nothing goes in or out */
  var presExtra = {}, presKept = null;    /* setPresence fields; the last cursor frame (sent again with new extras) */
  var useC1 = false;                      /* D9b: this socket speaks the compact op frames */
  var pageAsk = null, pageAskAt = 0, pageQ = [], pageT = null, offNeed = null, offSelPg = null;

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
    try {
      var text = typeof obj === 'string' ? obj : JSON.stringify(obj);
      ws.send(text);
      net.wire.bytesOut += text.length; net.wire.framesOut++;
      return true;
    } catch (e) { return false; }
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
  function lockStore() { if (store) store.readOnly = full || held || (net.role !== null && !canEdit()); }

  /* ---------------------------------------------------------------- local ops -> the wire */
  function onLocal(ops, b) {
    if (!want || !ops || !ops.length) return;
    if (held) return;                                               /* a preview: nothing of it ever reaches the server */
    if (!loaded || !canEdit()) { store.rollback(ops); return; }    /* before the first init, or a viewer: nothing is sent */
    for (var i = 0; i < ops.length; i++) queue.push({op: ops[i], b: b});
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
    if (!canEdit() || held) return;
    if (ws.bufferedAmount > MAX_BUFFERED) { scheduleFlush(); return; }          /* still busy: wait, keep coalescing */
    var items = [], parts = [], chars = 0, s, big = null, q;
    while (queue.length && items.length < MAX_FRAME_OPS) {
      s = JSON.stringify(useC1 ? encOp(queue[0].op) : queue[0].op);
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
      em.emit('reject', {ops: ops, tooBig: true});
      notePending();
    }
    if (!items.length) { if (queue.length) scheduleFlush(); return; }
    var n = nextN++;
    flying.push({n: n, items: items});
    if (!send(useC1 ? '[1,' + n + ',[' + parts.join(',') + ']]' : '{"t":"ops","n":' + n + ',"ops":[' + parts.join(',') + ']}')) {
      flying.pop();                         /* the socket died under us: the ops go back to the head of the queue */
      queue = items.concat(queue);
      return;
    }
    if (queue.length) scheduleFlush();
  }
  function onAck(msg) {
    var i, f = null;
    for (i = 0; i < flying.length; i++) if (flying[i].n === msg.n) { f = flying[i]; flying.splice(i, 1); break; }
    if (typeof msg.seq === 'number' && msg.seq > net.seq) net.seq = msg.seq;
    if (!f) return;
    var rej = msg.rejected, no = null, good = [], bad = [];
    if (rej && rej.length) { no = new Set(); for (i = 0; i < rej.length; i++) no.add(rej[i]); }
    if (msg.ex && msg.ex.length) for (i = 0; i < msg.ex.length; i++) { var it = f.items[msg.ex[i]]; if (it) it.op.ex = 1; }   /* D9b: merged into a node the server had */
    for (i = 0; i < f.items.length; i++) (no && no.has(i) ? bad : good).push(f.items[i].op);
    if (good.length) store.acked(good);         /* into the store's copy of the server, in the server's order */
    if (bad.length) { store.rollback(bad); em.emit('reject', {ops: bad}); }
    notePending();
  }

  /* ---------------------------------------------------------------- the socket */
  function open() {
    retryT = null;
    if (!want || ws) return;
    var tk = shareToken ? '' : token();
    if (!tk && !shareToken) { want = false; store.readOnly = true; setStatus('auth', {code: 4401}); return; }
    if (!full && !(quiet && net.status === 'live')) setStatus('connecting');
    var url = (W.location.protocol === 'https:' ? 'wss' : 'ws') + '://' + W.location.host +
      (shareToken ? '/api/design/ws?share=' + encodeURIComponent(shareToken) : '/api/design/ws?file=' + encodeURIComponent(fileId)) + caps();
    var g = ++gen, sock;
    try { sock = new W.WebSocket(url, shareToken ? ['hoola'] : ['hoola', 'hoola-key.' + tk]); }
    catch (e) { lost(); return; }
    ws = sock;
    lastHeard = now(); lastPing = now();
    sock.onopen = function () { if (g === gen) lastHeard = now(); };
    sock.onmessage = function (ev) {
      if (g !== gen) return;
      lastHeard = now();
      var msg;
      net.wire.framesIn++;
      if (typeof ev.data === 'string') net.wire.bytesIn += ev.data.length;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }
      if (Array.isArray(msg)) msg = decFrame(msg);              /* D9b: a compact frame */
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
    quiet = false;
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
    net.extra.clear();
    if (!net.users.size) return;
    net.users.clear();
    em.emit('presence', {type: 'reset'});
  }
  function putUser(u) {
    if (!u || u.cid === undefined || u.cid === net.cid) return null;
    var cur = net.users.get(u.cid) || {cid: u.cid, name: '', color: '#888888', x: null, y: null, page: null, sel: [], vp: null};
    if (!net.extra.has(u.cid)) net.extra.set(u.cid, {vs: null, chat: '', chatAt: 0, spot: 0, at: now()});
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
        if (loaded && !held) store.applyRemote(msg.ops);   /* held: the live document is fetched again at release() */
        break;
      case 'pres':
        if (msg.cid === undefined || msg.cid === net.cid) break;
        u = putUser({cid: msg.cid});
        if (typeof msg.x === 'number') u.x = msg.x;
        if (typeof msg.y === 'number') u.y = msg.y;
        if (msg.page !== undefined) u.page = msg.page;
        if (Array.isArray(msg.sel)) u.sel = msg.sel;
        if (Array.isArray(msg.vp)) u.vp = msg.vp;
        var x = net.extra.get(msg.cid), chat = typeof msg.chat === 'string' ? msg.chat.slice(0, 80) : '';
        x.vs = Array.isArray(msg.vs) ? msg.vs : null;
        if (chat !== x.chat) { x.chat = chat; x.chatAt = now(); }
        x.spot = typeof msg.spot === 'number' ? msg.spot : 0;
        x.at = now();
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
          net.extra.delete(msg.cid);
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
      case 'page': onPage(msg); break;
      case 'reload':
        if (held) break;                    /* release() fetches the live document anyway */
        em.emit('reload');
        net.resync(true);
        break;
      default: break;
    }
  }
  function onInit(msg) {
    var keep = loaded && !fresh, i;
    net.cid = msg.cid;
    net.seq = typeof msg.seq === 'number' ? msg.seq : 0;
    net.file = msg.file || {id: fileId, name: '', role: 'edit'};
    net.role = net.file.role === 'view' ? 'view' : 'edit';
    net.me = msg.you && typeof msg.you === 'object' ? msg.you : {cid: msg.cid, name: '', color: '#888888'};
    net.users.clear(); net.extra.clear();
    if (Array.isArray(msg.users)) for (i = 0; i < msg.users.length; i++) putUser(msg.users[i]);
    if (!canEdit()) keep = false;
    quiet = false;
    useC1 = msg.use === 'c1';
    net.pages = Array.isArray(msg.pages) ? msg.pages : null;
    pageAsk = null; pageQ = [];
    var lazyOpts = Array.isArray(msg.lazy) && msg.lazy.length ? {unloaded: msg.lazy} : null;
    if (held) {                             /* a new socket while a preview is on screen: the store is left alone */
      queue = []; flying = [];
      loaded = true; full = false; backoff = BACKOFF_MIN;
      lockStore();
      setStatus('live');
      em.emit('presence', {type: 'reset'});
      resendPresence();
      return;
    }
    if (keep) {
      var back = [];                        /* everything un-acked goes out again, oldest first */
      for (i = 0; i < flying.length; i++) back = back.concat(flying[i].items);
      queue = back.concat(queue);
      flying = [];
      store.load(msg.doc, msg.cid, lazyOpts ? {keep: true, unloaded: lazyOpts.unloaded} : {keep: true});
    } else {
      queue = []; flying = [];
      store.load(msg.doc, msg.cid, lazyOpts);
    }
    loaded = true; fresh = false; full = false;
    backoff = BACKOFF_MIN;
    lockStore();
    setStatus('live');
    em.emit('init', {cid: net.cid, seq: net.seq, file: net.file, users: net.users, reconnect: keep});
    em.emit('presence', {type: 'reset'});
    notePending();
    scheduleFlush();
    resendPresence();
    if (lazyOpts) pagesLater(0);
  }

  /* ---------------------------------------------------------------- D9b: page by page */
  function caps() {
    var o = net.options || {}, out = '';
    if (o.lazy !== false) {
      if (!loaded || !store.partial || !store.partial()) out += loaded ? '' : '&lazy=1';
      else {                                 /* a reconnect: the pages it holds, the one on screen first */
        var have = [], cur = HD.sel && HD.sel.page, tops = store.children(store.ROOT), i;
        if (cur && store.pageLoaded(cur)) have.push(cur);
        for (i = 0; i < tops.length; i++) if (tops[i] !== cur && store.pageLoaded(tops[i])) have.push(tops[i]);
        var list = have.map(encodeURIComponent).join(',');
        if (list.length < 1500) out += '&lazy=1' + (list ? '&pages=' + list : '');
      }
    }
    if (o.c1 !== false) out += '&enc=c1';
    return out;
  }
  function pagesLater(ms) {
    if (pageT !== null || pageAsk !== null) return;
    var go = function () { pageT = null; askNext(); };
    if (!ms && typeof W.requestIdleCallback === 'function') { pageT = -1; W.requestIdleCallback(go, {timeout: 400}); }
    else pageT = W.setTimeout(go, ms || 30);
  }
  function askNext() {
    if (pageAsk !== null && now() - pageAskAt > 20000) pageAsk = null;      /* never stuck behind one lost answer */
    if (pageAsk !== null || held || !loaded || !ws || ws.readyState !== 1) return;
    var cur = HD.sel && HD.sel.page, id = null;
    while (pageQ.length && id === null) { var q = pageQ.shift(); if (!store.pageLoaded(q) && store.has(q)) id = q; }
    if (id === null && cur && store.has(cur) && !store.pageLoaded(cur)) id = cur;
    if (id === null) { var miss = store.unloadedPages ? store.unloadedPages() : []; if (miss.length) id = miss[0]; }
    if (id === null) return;
    pageAsk = id; pageAskAt = now();
    send({t: 'page', id: id});
  }
  function ask(id, first) {                 /* first: she is looking at it (or it went stale): ahead of the idle ones */
    if (!id) return;
    var i = pageQ.indexOf(id);
    if (i >= 0) pageQ.splice(i, 1);
    if (first) pageQ.unshift(id); else pageQ.push(id);
    if (pageAsk === null) { if (pageT !== null && pageT !== -1) { W.clearTimeout(pageT); pageT = null; } askNext(); }
  }
  function onPage(msg) {
    if (held || !loaded || typeof msg.id !== 'string') return;      /* held: release() fetches everything again */
    store.loadPage(msg.id, msg.nodes);
    if (pageAsk === msg.id) pageAsk = null;
    var left = store.unloadedPages ? store.unloadedPages() : [];
    em.emit('page', {id: msg.id, left: left});
    if (left.length || pageQ.length) { if (pageQ.length) askNext(); else pagesLater(0); }
  }
  net.loading = function () { return store.unloadedPages ? store.unloadedPages() : []; };
  net.askPage = function (id) { ask(id, true); };

  function resendPresence() {              /* a new socket knows nothing of us yet: the extras (and the cursor) again */
    if (presKept) net.sendPresence(presKept);
    else if (hasExtra()) net.sendPresence({});
  }
  function hasExtra() { for (var k in presExtra) return true; return false; }

  /* ---------------------------------------------------------------- public */
  net.on = function (evt, fn) { return em.on(evt, fn); };
  net.off = function (evt, fn) { em.off(evt, fn); };
  net.pending = function () { return pendingCount(); };

  net.connect = function (id, opts) {
    if (id === undefined || id === null || id === '') return;
    id = String(id);
    var share = opts && opts.share ? String(opts.share) : null;
    if (want && fileId === id && shareToken === share) return;
    net.close();
    shareToken = share; net.share = share;
    fileId = id; want = true; loaded = false; fresh = false; full = false;
    backoff = BACKOFF_MIN;
    store.tracking(true);
    offOps = store.onOps(onLocal);
    offDesync = store.on('desync', function () { net.resync(false); });
    offNeed = store.on('need', function (pg) { ask(pg, true); });               /* D9b */
    if (HD.sel && HD.sel.on) offSelPg = HD.sel.on('change', function () {       /* she opened a page that is not here yet */
      var pg = HD.sel.page;
      if (pg && store.pageLoaded && !store.pageLoaded(pg)) ask(pg, true);
    });
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
    if (offNeed) { offNeed(); offNeed = null; }
    if (offSelPg) { offSelPg(); offSelPg = null; }
    if (pageT !== null && pageT !== -1) W.clearTimeout(pageT);
    pageT = null; pageAsk = null; pageQ = []; useC1 = false; net.pages = null;
    fileId = null; loaded = false; fresh = false; full = false;
    shareToken = null; net.share = null; held = false; net.held = false; quiet = false;
    presExtra = {}; presKept = null;
    queue = []; flying = [];
    net.users.clear(); net.extra.clear();
    net.role = null; net.cid = null; net.file = null; net.seq = 0; net.me = null;
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
    /* a reload on a live line is not a lost connection: the status stays 'live' while the document comes again
       (if the new socket fails, lost() says 'offline' as always) */
    quiet = !!replace && net.status === 'live' && !full;
    if (ws) { gen++; try { ws.close(); } catch (e) {} ws = null; }
    if (retryT !== null) { W.clearTimeout(retryT); retryT = null; }
    clearUsers();
    if (!quiet) setStatus(full ? 'offline-full' : 'connecting');
    retryT = W.setTimeout(open, 0);
  };

  /* ---------------------------------------------------------------- hold: a version preview */
  net.hold = function () {
    if (!want || held) return held;
    if (pendingCount() > 0 || (store.pendingCount && store.pendingCount() > 0)) return false;
    held = true; net.held = true;
    lockStore();
    return true;
  };
  net.release = function () {
    if (!held) return;
    held = false; net.held = false;
    queue = []; flying = [];
    lockStore();
    if (want) store.readOnly = true;        /* until the live document is back: an edit of the preview would be lost */
    if (want) net.resync(true);             /* the live document, fresh: whatever the store shows now is dropped */
    notePending();
  };

  net.setPresence = function (extra) {
    var k, i, changed = false;
    for (i = 0; i < PRES_EXTRA.length; i++) {
      k = PRES_EXTRA[i];
      if (!extra || !hasOwn.call(extra, k)) continue;
      if (extra[k] === null || extra[k] === undefined || extra[k] === '') { if (hasOwn.call(presExtra, k)) { delete presExtra[k]; changed = true; } }
      else if (JSON.stringify(presExtra[k]) !== JSON.stringify(extra[k])) { presExtra[k] = extra[k]; changed = true; }
    }
    if (changed) net.sendPresence(presNext || presKept || {});
  };

  net.sendPresence = function (p) {
    if (!p) return;
    if (p.x !== undefined || p.vp !== undefined) presKept = p;
    else if (presKept) p = presKept;        /* only the extras changed: the cursor and the view as last sent */
    if (net.status !== 'live') return;
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
    var out = {
      t: 'pres', x: p.x, y: p.y,
      page: p.page !== undefined ? p.page : (HD.sel ? HD.sel.page : null),
      sel: sel && sel.length > 200 ? sel.slice(0, 200) : sel,
      vp: p.vp
    };
    for (var k in presExtra) if (hasOwn.call(presExtra, k)) out[k] = presExtra[k];
    send(out);
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
