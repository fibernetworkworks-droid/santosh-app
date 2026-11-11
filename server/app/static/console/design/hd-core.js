/* HOOLA DESIGN - hd-core.js
 *
 * HD.frac   fractional index strings (base 62, plain string order)
 * HD.store  the document: a tree of nodes, each node a flat bag of properties
 * HD.sel    the selection + the current page
 * HD.Emitter  the tiny event emitter the three use (on / off / emit)
 *
 * READ-ONLY RESULTS. get(id) returns the LIVE node object and children(id) returns a FROZEN shared array:
 * never change them (copy first: children(id).slice()). Property values (fills, layout, ...) are immutable
 * by convention: build a NEW array / object and pass it to set(). localMatrix / worldMatrix / worldBounds /
 * subtreeBounds return fresh copies. A missing property means "the default": read with prop(id, name).
 *
 * EDITS. Every edit goes through tx(label, fn). Inside the outermost tx all changes are collected; when fn
 * returns the store calls HD.layout.run(changedIds, changedProps) (if HD.layout exists; its set() calls join
 * the same tx), then closes the tx: ONE op batch (sets merged per node, later value wins), ONE undo entry
 * (the inverse ops), ONE 'change' event. create / set / remove / move called outside a tx open their own.
 * If fn throws, everything it did is put back and nothing is sent. Defaults are never written into ops.
 *
 * THE SYNC HANDSHAKE (HD.store <-> HD.net)
 * While tracking, the store keeps a second copy of the document: the SHADOW = the document as the server has
 * it (the init document + every remote op + every op of ours the server accepted, in the server's order). What
 * is on screen is ALWAYS  shadow + our still-waiting ops, replayed with the server's own rules.
 *   store.tracking(true)            net switches this on while a file is connected (off = no shadow, no
 *                                   book-keeping: a local-only document).
 *   store.onOps(fn(ops, b))         fires once per closed local tx. `ops` is the batch, `b` the store's batch
 *                                   number (1, 2, 3, ...). The op OBJECTS are the handles: keep them, do not
 *                                   clone or change them.
 *   store.acked(ops)                the server ACCEPTED these ops (same objects, in sending order; call it once
 *                                   per ack frame so the shadow follows the server's order). acked(b) = every
 *                                   op of batch b not answered yet. Nothing on screen changes.
 *   store.rollback(ops)             the server REJECTED these ops: they leave the waiting list and the screen is
 *                                   worked out again (shadow + what still waits). So a rejected set shows the
 *                                   server's value, a rejected create is gone, a rejected delete is back.
 *   store.applyRemote(ops)          ops of other people. They go into the shadow. On screen a prop that one of
 *                                   our waiting ops writes keeps OUR value (the ack will carry the truth);
 *                                   when both sides change the tree (create / delete / reparent) the screen is
 *                                   worked out again from the shadow - exact, no guessing, no network.
 *   store.load(doc, cid, {keep:true})   after a reconnect: the fresh document becomes the shadow, undo is
 *                                   kept, the waiting ops are replayed on top (net sends them again).
 *   store.on('desync', fn)          the shadow could not follow the server (an op arrived that the server's own
 *                                   rules refuse). Should never happen; net then reconnects and reloads.
 *   store.readOnly = true           net sets it for a view-only file / a full offline queue: tx() and the
 *                                   editing calls then do nothing and return undefined.
 *   store.syncCheck() / pendingInfo() / serverDoc()   for tests and a debug panel.
 * server/tests/web/design_core_test.js runs three editors against a contract server with crossing messages,
 * rejects, undo and dropped connections, and checks after EVERY step that screen = shadow + waiting ops.
 */
(function () {
  'use strict';
  var W = window;
  var HD = W.HD = W.HD || {};
  var M = HD.math;
  var hasOwn = Object.prototype.hasOwnProperty;
  var isArr = Array.isArray;

  function report(err) { if (W.console && W.console.error) W.console.error('[HD]', err); }

  /* ================================================================ emitter */
  function Emitter() { this._m = Object.create(null); }
  Emitter.prototype.on = function (evt, fn) {
    var self = this;
    if (typeof fn !== 'function') return function () {};
    (this._m[evt] || (this._m[evt] = [])).push(fn);
    return function () { self.off(evt, fn); };
  };
  Emitter.prototype.off = function (evt, fn) {
    var l = this._m[evt];
    if (!l) return;
    var i = l.indexOf(fn);
    if (i >= 0) this._m[evt] = l.slice(0, i).concat(l.slice(i + 1));
  };
  Emitter.prototype.emit = function (evt, a, b) {
    var l = this._m[evt];
    if (!l) return;
    for (var i = 0; i < l.length; i++) {
      try { l[i](a, b); } catch (err) { report(err); }
    }
  };
  Emitter.prototype.count = function (evt) { var l = this._m[evt]; return l ? l.length : 0; };
  HD.Emitter = Emitter;

  /* ================================================================ HD.frac
   * Keys are base-62 strings ("0-9A-Za-z", which is also ASCII order) compared as PLAIN STRINGS, and a key
   * NEVER ends in "0" (the rule of the plain base-62 fraction the server uses: its own between() refuses such
   * a key). Keys made here have a short counting head ("a1", "a2", ... "az", "b01", ...; below "a1": "Zz",
   * "Zy", ...) so adding at the end or the start 50,000 times still gives 4-character keys, plus a fraction
   * tail for inserts in between ("a1V"). Keys from any other correct implementation are accepted: next to a
   * key that is not in that shape the plain string midpoint / one-digit step is used. Only the ordering matters.
   */
  var DIG = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
  var DI = Object.create(null);
  (function () { for (var i = 0; i < DIG.length; i++) DI[DIG.charAt(i)] = i; })();
  var SMALLEST = 'A00000000000000000000000000';
  var FIRST = 'a1';

  function di(ch) {
    var v = DI[ch];
    if (v !== undefined) return v;
    for (var i = DIG.length - 1; i >= 0; i--) if (DIG.charAt(i) <= ch) return i;   /* a foreign character */
    return 0;
  }

  /* a string strictly between a ('' = lowest) and b (null = highest) in plain string order; never ends in '0' */
  function mid(a, b) {
    var out = '', i = 0, ca, cb;
    for (;;) {
      ca = i < a.length ? di(a.charAt(i)) : 0;
      if (b === null) cb = 62;
      else if (i < b.length) cb = di(b.charAt(i));
      else return out + 'V';                       /* b is a + zeros: there is no room, stay next to it */
      if (ca === cb) { out += DIG.charAt(ca); i++; continue; }
      if (cb < ca) return out + DIG.charAt(ca) + 'V';              /* not a < b: keep going, never throw */
      if (cb - ca > 1) return out + DIG.charAt((ca + cb + 1) >> 1);
      if (b !== null && b.length > i + 1) return out + DIG.charAt(cb);
      out += DIG.charAt(ca); i++; b = null;
    }
  }
  /* one digit step above a / below b, for a neighbour that is not in the counting shape (cheap repeated adds) */
  function stepAfter(a) {
    var h = 0;
    while (h < a.length && di(a.charAt(h)) === 61) h++;
    return h === a.length ? a + '1' : a.slice(0, h) + DIG.charAt(di(a.charAt(h)) + 1);
  }
  function stepBefore(b) {
    var h = 0;
    while (h < b.length && di(b.charAt(h)) === 0) h++;
    if (h === b.length) return mid('', b);
    var d = di(b.charAt(h));
    return d > 1 ? b.slice(0, h) + DIG.charAt(d - 1) : b.slice(0, h) + '0z';
  }

  function headLen(key) {
    var c = key.charCodeAt(0);
    if (c >= 97 && c <= 122) return c - 97 + 2;
    if (c >= 65 && c <= 90) return 90 - c + 2;
    return 0;
  }
  function validKey(key) {
    if (typeof key !== 'string' || !key || key === SMALLEST) return false;
    var L = headLen(key);
    if (!L || key.length < L) return false;
    for (var i = 1; i < key.length; i++) if (DI[key.charAt(i)] === undefined) return false;
    return !(key.length > L && key.charAt(key.length - 1) === '0');
  }
  function inc1(x) {
    var head = x.charAt(0), d = x.slice(1).split(''), carry = true;
    for (var i = d.length - 1; carry && i >= 0; i--) {
      var v = DI[d[i]] + 1;
      if (v === 62) d[i] = '0'; else { d[i] = DIG.charAt(v); carry = false; }
    }
    if (!carry) return head + d.join('');
    if (head === 'Z') return 'a0';
    if (head === 'z') return null;
    var h = String.fromCharCode(head.charCodeAt(0) + 1);
    if (h > 'a') d.push('0'); else d.pop();
    return h + d.join('');
  }
  function dec1(x) {
    var head = x.charAt(0), d = x.slice(1).split(''), borrow = true;
    for (var i = d.length - 1; borrow && i >= 0; i--) {
      var v = DI[d[i]] - 1;
      if (v === -1) d[i] = 'z'; else { d[i] = DIG.charAt(v); borrow = false; }
    }
    if (!borrow) return head + d.join('');
    if (head === 'a') return 'Zz';
    if (head === 'A') return null;
    var h = String.fromCharCode(head.charCodeAt(0) - 1);
    if (h < 'Z') d.push('z'); else d.pop();
    return h + d.join('');
  }
  /* the next / previous counting head that does not end in "0" */
  function incInt(x) { var n = inc1(x); return n !== null && n.charAt(n.length - 1) === '0' ? inc1(n) : n; }
  function decInt(x) { var n = dec1(x); return n !== null && n.charAt(n.length - 1) === '0' ? dec1(n) : n; }

  function keyBetween(a, b) {
    var ia, ib, fa, fb, n;
    if (a === null) {
      if (b === null) return FIRST;
      ib = b.slice(0, headLen(b)); fb = b.slice(ib.length);
      if (ib === SMALLEST) return ib + mid('', fb);
      if (ib < b) return ib;
      n = decInt(ib);
      return n === null ? mid('', b) : n;
    }
    ia = a.slice(0, headLen(a)); fa = a.slice(ia.length);
    if (b === null) {
      n = incInt(ia);
      return n === null ? ia + mid(fa, null) : n;
    }
    ib = b.slice(0, headLen(b)); fb = b.slice(ib.length);
    if (ia === ib) return ia + mid(fa, fb);
    n = incInt(ia);
    if (n !== null && n < b) return n;
    return ia + mid(fa, null);
  }
  function fnorm(k) { return (k === undefined || k === null || k === '') ? null : String(k); }

  /* between(a|null, b|null) -> a key k with a < k < b.  null = no bound on that side. */
  function between(a, b) {
    a = fnorm(a); b = fnorm(b);
    if (a !== null && b !== null) {
      if (a === b) return a + 'V';                 /* two equal keys: nothing fits, go right after them */
      if (a > b) { var t = a; a = b; b = t; }
    }
    var k;
    if ((a === null || validKey(a)) && (b === null || validKey(b))) {
      k = keyBetween(a, b);
      if (k.charAt(k.length - 1) !== '0') return k;
    } else if (b === null) return a < FIRST ? FIRST : stepAfter(a);          /* on top of a foreign key */
    else if (a === null) return b > FIRST ? FIRST : stepBefore(b);          /* under a foreign key */
    return mid(a === null ? '' : a, b);
  }
  /* nBetween(a, b, n) -> n keys in rising order, all between a and b */
  function nBetween(a, b, n) {
    var out = [], c, i;
    n = n | 0;
    if (n <= 0) return out;
    if (n === 1) return [between(a, b)];
    a = fnorm(a); b = fnorm(b);
    if (b === null) {
      c = between(a, null); out.push(c);
      for (i = 1; i < n; i++) { c = between(c, null); out.push(c); }
      return out;
    }
    if (a === null) {
      c = between(null, b); out.push(c);
      for (i = 1; i < n; i++) { c = between(null, c); out.push(c); }
      return out.reverse();
    }
    var h = n >> 1;
    c = between(a, b);
    return nBetween(a, c, h).concat([c], nBetween(c, b, n - h - 1));
  }
  HD.frac = {between: between, nBetween: nBetween, valid: validKey, DIGITS: DIG};

  /* ================================================================ HD.store */
  var ROOT = '0:0';
  var LABEL = {
    DOCUMENT: 'Document', PAGE: 'Page', FRAME: 'Frame', GROUP: 'Group', SECTION: 'Section', RECT: 'Rectangle',
    ELLIPSE: 'Ellipse', LINE: 'Line', POLYGON: 'Polygon', STAR: 'Star', VECTOR: 'Vector', TEXT: 'Text',
    COMPONENT: 'Component', COMPONENT_SET: 'Component set', INSTANCE: 'Instance'
  };
  var TYPES = Object.keys(LABEL);

  var COMMON = {
    x: 0, y: 0, w: 100, h: 100, rot: 0, flipH: false, flipV: false,
    visible: true, locked: false, opacity: 1, blend: 'normal', mask: false,
    fills: [], strokes: [], strokeWeight: 1, strokeAlign: 'center', strokeCap: 'butt', strokeJoin: 'miter', dash: [],
    radius: 0, effects: [], clip: false,
    layout: {mode: 'none', gap: 0, pad: [0, 0, 0, 0], alignMain: 'start', alignCross: 'start', wrap: false},
    grids: [], sizeH: 'fixed', sizeV: 'fixed', layoutPos: 'auto', cons: {h: 'left', v: 'top'},
    reactions: [], protoStart: false, scroll: 'none', fixed: false, exports: []
  };
  var BY_TYPE = {
    FRAME: {clip: true},
    COMPONENT: {clip: true, desc: ''},
    INSTANCE: {clip: true, ov: {}},
    LINE: {h: 0},
    POLYGON: {sides: 3},
    STAR: {sides: 5, ratio: 0.5},
    VECTOR: {path: '', fillRule: 'nonzero'},
    TEXT: {
      chars: '', font: 'Inter', fontSize: 16, fontWeight: 400, italic: false, lineHeight: 'auto', letterSpacing: 0,
      align: 'left', alignV: 'top', autoResize: 'wh', decoration: 'none', textCase: 'none'
    },
    PAGE: {bg: '#F5F5F5'},
    DOCUMENT: {styles: {}, vars: {}, modes: []}
  };
  function clone(v) {
    if (v === null || typeof v !== 'object') return v;
    if (isArr(v)) { var a = new Array(v.length); for (var i = 0; i < v.length; i++) a[i] = clone(v[i]); return a; }
    var o = {};
    for (var k in v) if (hasOwn.call(v, k)) o[k] = clone(v[k]);
    return o;
  }
  function deepFreeze(v) {
    if (v !== null && typeof v === 'object' && !Object.isFrozen(v)) {
      Object.freeze(v);
      for (var k in v) if (hasOwn.call(v, k)) deepFreeze(v[k]);
    }
    return v;
  }
  var DEF = Object.create(null);
  (function () {
    for (var i = 0; i < TYPES.length; i++) {
      var t = TYPES[i], d = clone(COMMON), x = BY_TYPE[t];
      if (x) for (var k in x) d[k] = clone(x[k]);
      DEF[t] = deepFreeze(d);
    }
  })();
  var NO_DEF = Object.freeze({});
  var EMPTY = Object.freeze([]);
  var IDENT = [1, 0, 0, 1, 0, 0];

  /* ---------- state ---------- */
  var nodes = new Map();      /* id -> node (the props bag) */
  var kidSet = new Map();     /* parent id -> Set of child ids */
  var sorted = new Map();     /* parent id -> frozen array, children sorted by (idx, id); dropped when stale */
  var tail = new Map();       /* parent id -> last child id | null; a missing entry = not known */
  var lm = new Map();         /* id -> local matrix */
  var wm = new Map();         /* id -> world matrix      (a cached child always has a cached parent) */
  var wb = new Map();         /* id -> world bounds of the node's own box */
  var sb = new Map();         /* id -> world bounds of the node and all it shows (see subtreeBounds) */
  var cid = 0, counter = 0;
  var nameN = new Map();      /* type -> highest "Rectangle N" seen */
  var em = new Emitter();

  /* ---------- undo ---------- */
  var undoS = [], redoS = [], UNDO_MAX = 500;
  var depth = 0, cur = null;  /* the open tx */
  var gKey = null, gSeq = 0;

  /* ---------- sync: the server's copy + our un-acked ops ---------- */
  var tracking = false;
  var batchNo = 0;
  var shadow = null;          /* id -> node: the document as the SERVER has it (init + remote ops + our acked ops, in its order) */
  var skid = null;            /* shadow parent id -> Set of child ids */
  var pendQ = [];             /* our batches the server has not answered yet, oldest first: {b, recs, left} */
  var pendB = new Map();      /* b -> batch */
  var opRec = new WeakMap();  /* op object -> its record {op, batch, done, rej} */
  var pcnt = new Map();       /* "id\nprop" -> how many waiting ops write that prop */
  var pids = new Map();       /* id -> how many waiting ops are about that node */
  var pmade = new Map();      /* id -> how many waiting ops (re)make that node (carry `type`) */
  var pstruct = 0;            /* how many waiting ops change the tree (delete, parent, type) */

  var store = HD.store = {ROOT: ROOT, TYPES: TYPES, readOnly: false};
  var sel;                    /* HD.sel, defined below */

  function same(a, b) {
    if (a === b) return true;
    if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null) return false;
    var aa = isArr(a), i;
    if (aa !== isArr(b)) return false;
    if (aa) {
      if (a.length !== b.length) return false;
      for (i = 0; i < a.length; i++) if (!same(a[i], b[i])) return false;
      return true;
    }
    var ka = Object.keys(a);
    if (ka.length !== Object.keys(b).length) return false;
    for (i = 0; i < ka.length; i++) if (!hasOwn.call(b, ka[i]) || !same(a[ka[i]], b[ka[i]])) return false;
    return true;
  }
  function toArr(ids) { return isArr(ids) ? ids : (ids === undefined || ids === null) ? [] : (ids instanceof Set ? Array.from(ids) : [ids]); }

  /* ================================================================ tree primitives (no recording) */
  function cmpChild(a, b) {
    var na = nodes.get(a), nb = nodes.get(b);
    var ia = na && na.idx !== undefined ? na.idx : '', ib = nb && nb.idx !== undefined ? nb.idx : '';
    return ia < ib ? -1 : ia > ib ? 1 : a < b ? -1 : a > b ? 1 : 0;
  }
  function attach(pid, id) {
    if (pid === undefined || pid === null) return;
    var ks = kidSet.get(pid);
    if (!ks) { ks = new Set(); kidSet.set(pid, ks); if (!tail.has(pid)) tail.set(pid, null); }
    ks.add(id);
    sorted.delete(pid);
    if (tail.has(pid)) {
      var t = tail.get(pid);
      if (t === null || cmpChild(id, t) > 0) tail.set(pid, id);
    }
  }
  function detach(pid, id) {
    var ks = kidSet.get(pid);
    if (ks) ks.delete(id);
    sorted.delete(pid);
    if (tail.get(pid) === id) tail.delete(pid);
  }
  function childrenOf(id) {
    var s = sorted.get(id);
    if (s) return s;
    var ks = kidSet.get(id);
    if (!ks || !ks.size) return EMPTY;
    s = Array.from(ks);
    if (s.length > 1) s.sort(cmpChild);
    Object.freeze(s);
    sorted.set(id, s);
    return s;
  }
  function lastChild(pid) {
    if (tail.has(pid)) return tail.get(pid);
    var s = sorted.get(pid), t = null;
    if (s) t = s.length ? s[s.length - 1] : null;
    else {
      var ks = kidSet.get(pid);
      if (ks) ks.forEach(function (k) { if (t === null || cmpChild(k, t) > 0) t = k; });
    }
    tail.set(pid, t);
    return t;
  }

  /* cache invalidation: the subtree bounds of `id`'s ancestors */
  function dirtyUpFrom(pid) {
    var c = pid, n;
    while (c !== undefined && sb.has(c)) { sb.delete(c); n = nodes.get(c); c = n ? n.parent : undefined; }
  }
  function dirtyUp(id) {
    sb.delete(id);
    var n = nodes.get(id);
    if (n) dirtyUpFrom(n.parent);
  }
  /* the world matrix of `id` and of everything under it (only the part that was ever computed) */
  function dirtyWorld(id) {
    if (!wm.has(id)) return;
    var stack = [id], c, ks;
    while (stack.length) {
      c = stack.pop();
      wm.delete(c); wb.delete(c); sb.delete(c);
      ks = kidSet.get(c);
      if (ks && ks.size) ks.forEach(function (k) { if (wm.has(k)) stack.push(k); });
    }
  }

  var KIND = {x: 1, y: 1, w: 2, h: 2, rot: 3, flipH: 3, flipV: 3, parent: 4, idx: 5, visible: 6, clip: 6, type: 7};

  /* write props into an existing node. Returns null (nothing changed) or [changed, previous]:
     changed = {prop: new value | null}, previous = {prop: old value | null (it did not exist)}. */
  function rawSet(id, n, p) {
    var prev = null, chg = null, flags = 0, k, v, old, f;
    for (k in p) {
      v = p[k];
      if (v === undefined) continue;
      old = n[k];
      if (v === null) {
        if (old === undefined) continue;
        delete n[k];
      } else {
        if (typeof v === 'number' && v !== v) continue;                       /* NaN never enters the document */
        if (old === v ? typeof v !== 'object' : same(old, v)) continue;
        n[k] = v;
      }
      if (prev === null) { prev = {}; chg = {}; }
      prev[k] = old === undefined ? null : old;
      chg[k] = v;
      f = KIND[k];
      if (f !== undefined) flags |= 1 << f;
    }
    if (prev === null) return null;
    if (flags) afterSet(id, n, prev, flags);
    return [chg, prev];
  }
  function afterSet(id, n, prev, flags) {
    var pid;
    if (flags & 16) {                                   /* parent */
      if (prev.parent !== null) { detach(prev.parent, id); dirtyUpFrom(prev.parent); }
      attach(n.parent, id);
      dirtyWorld(id); dirtyUp(id);
    } else if (flags & 32) {                            /* idx alone */
      pid = n.parent;
      if (pid !== undefined) { sorted.delete(pid); tail.delete(pid); }
    }
    if (flags & (2 | 8 | 128)) {                        /* x y / rot flips / type */
      lm.delete(id); dirtyWorld(id); dirtyUp(id);
    } else if (flags & 4) {                             /* w h */
      if (n.rot || n.flipH || n.flipV) { lm.delete(id); dirtyWorld(id); } else wb.delete(id);
      dirtyUp(id);
    }
    if (flags & 64) dirtyUp(id);                        /* visible / clip */
  }
  function rawCreate(id, node) {
    nodes.set(id, node);
    attach(node.parent, id);
    dirtyUpFrom(node.parent);
  }
  /* remove a node and its subtree; returns [[id, node], ...] parents before children */
  function rawDelete(id) {
    var n0 = nodes.get(id), out = [];
    if (!n0) return out;
    if (n0.parent !== undefined) { detach(n0.parent, id); dirtyUpFrom(n0.parent); }
    var stack = [id], c, n, ks;
    while (stack.length) {
      c = stack.pop();
      n = nodes.get(c);
      if (!n) continue;
      out.push([c, n]);
      nodes.delete(c);
      lm.delete(c); wm.delete(c); wb.delete(c); sb.delete(c);
      ks = kidSet.get(c);
      if (ks) { ks.forEach(function (k) { stack.push(k); }); kidSet.delete(c); }
      sorted.delete(c); tail.delete(c);
    }
    return out;
  }
  function isAncestor(a, b) {             /* is a an ancestor of b */
    var n = nodes.get(b), c = n ? n.parent : undefined, guard = 0;
    while (c !== undefined && ++guard < 200000) {       /* the guard: a loop in stored data never hangs the page */
      if (c === a) return true;
      n = nodes.get(c);
      c = n ? n.parent : undefined;
    }
    return guard >= 200000;
  }
  function okParent(id, pid) {
    return id !== ROOT && typeof pid === 'string' && pid !== id && nodes.has(pid) && !isAncestor(id, pid);
  }
  function cleanCopy(p) {
    var o = {}, k, v;
    for (k in p) { v = p[k]; if (v !== null && v !== undefined) o[k] = v; }
    return o;
  }

  /* ================================================================ matrices + bounds */
  function localRaw(id) {
    var m = lm.get(id);
    if (m) return m;
    var n = nodes.get(id);
    if (!n) return IDENT;
    if (n.type === 'PAGE' || n.type === 'DOCUMENT') m = IDENT;
    else {
      var d = DEF[n.type] || NO_DEF;
      m = M.nodeMatrix(+n.x || 0, +n.y || 0,
        n.w === undefined ? (d.w || 0) : +n.w || 0, n.h === undefined ? (d.h || 0) : +n.h || 0,
        +n.rot || 0, !!n.flipH, !!n.flipV);
    }
    lm.set(id, m);
    return m;
  }
  function worldRaw(id) {
    var m = wm.get(id);
    if (m) return m;
    var chain = [], c = id, base = IDENT, n, guard = 0;
    while (c !== undefined) {
      m = wm.get(c);
      if (m) { base = m; break; }
      n = nodes.get(c);
      if (!n || ++guard > 100000) break;
      chain.push(c);
      c = n.parent;
    }
    for (var i = chain.length - 1; i >= 0; i--) {
      m = localRaw(chain[i]);
      base = m === IDENT ? base : base === IDENT ? m : M.mul(base, m);
      wm.set(chain[i], base);
    }
    return base;
  }
  function boundsRaw(id) {
    var n = nodes.get(id);
    if (!n) return null;
    if (n.type === 'PAGE' || n.type === 'DOCUMENT') return subtreeRaw(id);
    var r = wb.get(id);
    if (r) return r;
    var d = DEF[n.type] || NO_DEF;
    r = M.boundsOf(worldRaw(id), n.w === undefined ? (d.w || 0) : +n.w || 0, n.h === undefined ? (d.h || 0) : +n.h || 0);
    wb.set(id, r);
    return r;
  }
  var ZERO = {x: 0, y: 0, w: 0, h: 0};
  function subtreeRaw(id) {
    var r = sb.get(id);
    if (r) return r;
    var n = nodes.get(id);
    if (!n) return null;
    var page = n.type === 'PAGE' || n.type === 'DOCUMENT';
    r = page ? null : boundsRaw(id);
    var clip = n.clip === undefined ? !!(DEF[n.type] || NO_DEF).clip : !!n.clip;
    if (page || !clip) {
      var ks = kidSet.get(id);
      if (ks && ks.size) {
        var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, any = false;
        if (r) { x0 = r.x; y0 = r.y; x1 = r.x + r.w; y1 = r.y + r.h; any = true; }
        ks.forEach(function (k) {
          var kn = nodes.get(k);
          if (!kn || kn.visible === false) return;
          var b = subtreeRaw(k);
          if (!b) return;
          any = true;
          if (b.x < x0) x0 = b.x;
          if (b.y < y0) y0 = b.y;
          if (b.x + b.w > x1) x1 = b.x + b.w;
          if (b.y + b.h > y1) y1 = b.y + b.h;
        });
        if (any) r = {x: x0, y: y0, w: x1 - x0, h: y1 - y0};
      }
    }
    if (!r) r = ZERO;
    sb.set(id, r);
    return r;
  }
  function copyRect(r) { return r ? {x: r.x, y: r.y, w: r.w, h: r.h} : {x: 0, y: 0, w: 0, h: 0}; }

  /* ================================================================ the open tx: recording */
  function newTx(label, kind, key) {
    return {
      label: label || '', kind: kind, key: key || null,
      steps: [],                 /* [forward op, inverse op | inverse ops[] | null] in the order things happened */
      made: new Set(),           /* ids created in this tx */
      changed: new Set(), removed: new Set(), extra: new Set(), props: new Map(),
      structural: false,
      sel0: sel.ids
    };
  }
  function noteProps(t, id, chg) {
    var s = t.props.get(id);
    if (!s) { s = new Set(); t.props.set(id, s); }
    for (var k in chg) s.add(k);
  }
  /* set on an existing node, recorded. The caller has checked a parent change. */
  function recSet(id, n, p) {
    var oldParent = n.parent;
    var r = rawSet(id, n, p);
    if (!r) return false;
    var t = cur, chg = r[0], prev = r[1];
    t.steps.push([{id: id, p: chg}, {id: id, p: prev}]);
    t.changed.add(id);
    noteProps(t, id, chg);
    if (hasOwn.call(chg, 'parent')) {
      t.structural = true;
      if (oldParent !== undefined) t.extra.add(oldParent);
      t.extra.add(n.parent);
    } else if (hasOwn.call(chg, 'idx') || hasOwn.call(chg, 'type')) {
      t.structural = true;
      if (n.parent !== undefined) t.extra.add(n.parent);
    }
    return true;
  }
  function recCreate(id, node) {
    rawCreate(id, node);
    var t = cur, op = {id: id, p: Object.assign({}, node)};
    /* created under a node that this tx created too: undoing the outer one removes it, no delete of its own */
    t.steps.push([op, t.made.has(node.parent) ? null : {id: id, del: 1}]);
    t.made.add(id);
    t.changed.add(id);
    t.extra.add(node.parent);
    t.structural = true;
  }
  function recDelete(id) {
    var n0 = nodes.get(id);
    if (!n0 || id === ROOT) return false;
    var pid = n0.parent, list = rawDelete(id), t = cur, inv = new Array(list.length);
    for (var i = 0; i < list.length; i++) {
      inv[i] = {id: list[i][0], p: list[i][1]};
      t.changed.add(list[i][0]);
      t.removed.add(list[i][0]);
    }
    var op = {id: id, del: 1};
    t.steps.push([op, inv]);
    if (pid !== undefined) t.extra.add(pid);
    t.structural = true;
    return true;
  }
  /* apply one op the way the server would, recorded (undo / redo use this) */
  function recOp(op) {
    if (!op || typeof op.id !== 'string') return false;
    if (op.del) return recDelete(op.id);
    var p = op.p, n = nodes.get(op.id);
    if (!p) return false;
    if (n) {
      if (p.parent !== undefined && p.parent !== n.parent && !okParent(op.id, p.parent)) return false;
      if (p.type !== undefined && p.type !== null && !hasOwn.call(DEF, p.type)) return false;
      return recSet(op.id, n, p);
    }
    if (typeof p.type !== 'string' || p.type === 'DOCUMENT' || !hasOwn.call(DEF, p.type) || op.id === ROOT || !nodes.has(p.parent)) return false;
    recCreate(op.id, cleanCopy(p));
    return true;
  }
  /* the same without recording (abort, re-apply after a reload) */
  function rawOp(op) {
    if (!op || typeof op.id !== 'string') return null;
    if (op.del) {
      if (op.id === ROOT || !nodes.has(op.id)) return null;
      return {del: rawDelete(op.id)};
    }
    var p = op.p, n = nodes.get(op.id);
    if (!p) return null;
    if (n) {
      if (p.parent !== undefined && p.parent !== n.parent && !okParent(op.id, p.parent)) return null;
      var r = rawSet(op.id, n, p);
      return r ? {set: r} : {set: null};
    }
    if (p.type === undefined || !hasOwn.call(DEF, p.type) || op.id === ROOT || !nodes.has(p.parent)) return null;
    rawCreate(op.id, cleanCopy(p));
    return {create: true};
  }

  /* merge a list of ops: sets on one node fold into its earlier op (later value wins). A set that changes
     `parent` only folds into the op right before it (reordering a reparent could build a cycle on the server),
     and nothing folds across a delete. */
  function mergeOps(list) {
    if (list.length < 2) return list;
    var out = [], last = new Map(), holes = 0, i, op, j, t, k;
    for (i = 0; i < list.length; i++) {
      op = list[i];
      if (op.del) {
        j = last.get(op.id);                 /* a plain set right before its own delete says nothing */
        if (j !== undefined && out[j].p.type === undefined) { out[j] = null; holes++; }
        out.push(op); last.clear();
        continue;
      }
      j = last.get(op.id);
      if (j !== undefined && (j === out.length - 1 || !hasOwn.call(op.p, 'parent'))) {
        t = out[j].p;
        for (k in op.p) t[k] = op.p[k];
        continue;
      }
      last.set(op.id, out.length);
      out.push(op);
    }
    if (holes) out = out.filter(function (o) { return o !== null; });
    return out;
  }

  function bump(map, key, d) {
    var c = (map.get(key) || 0) + d;
    if (c > 0) map.set(key, c); else map.delete(key);
  }
  function countOp(op, d) {
    bump(pids, op.id, d);
    if (op.del) { pstruct += d; return; }
    var p = op.p, made = hasOwn.call(p, 'type');
    if (made) bump(pmade, op.id, d);
    if (made || hasOwn.call(p, 'parent')) pstruct += d;
  }
  /* the props a waiting op writes shield those props from remote values - but only while the op really applies
     (rec.live): a waiting move whose target was deleted meanwhile shields nothing */
  function countKeys(op, d) {
    if (op.del) return;
    for (var k in op.p) bump(pcnt, op.id + '\n' + k, d);
  }
  function register(b, ops) {
    var recs = new Array(ops.length), batch = {b: b, recs: recs, left: ops.length};
    for (var i = 0; i < ops.length; i++) {
      recs[i] = {op: ops[i], batch: batch, done: false, rej: false, live: true};
      opRec.set(ops[i], recs[i]);
      countOp(ops[i], 1);
      countKeys(ops[i], 1);
    }
    pendQ.push(batch);
    pendB.set(b, batch);
  }

  function layoutIds(t) {
    var s = new Set();
    t.changed.forEach(function (id) { if (nodes.has(id)) s.add(id); });
    t.extra.forEach(function (id) { if (nodes.has(id)) s.add(id); });
    return s;
  }

  function abortTx() {
    var steps = cur.steps, i, inv, j;
    cur = null; depth = 0;
    for (i = steps.length - 1; i >= 0; i--) {
      inv = steps[i][1];
      if (inv === null) continue;
      if (isArr(inv)) for (j = 0; j < inv.length; j++) rawOp({id: inv[j].id, p: inv[j].p});
      else rawOp(inv);
    }
  }

  function commitTx() {
    var t = cur, steps = t.steps, i, j, inv, fwd, back;
    cur = null; depth = 0;
    if (!steps.length) return false;
    if (steps.length === 1) {
      fwd = [steps[0][0]];
      back = isArr(steps[0][1]) ? steps[0][1] : steps[0][1] === null ? [] : [steps[0][1]];
    } else {
      fwd = new Array(steps.length);
      for (i = 0; i < steps.length; i++) fwd[i] = steps[i][0];
      fwd = mergeOps(fwd);
      back = [];
      for (i = steps.length - 1; i >= 0; i--) {
        inv = steps[i][1];
        if (inv === null) continue;
        if (isArr(inv)) for (j = 0; j < inv.length; j++) back.push(inv[j]); else back.push(inv);
      }
      back = mergeOps(back);
    }
    var b = ++batchNo;
    if (tracking) register(b, fwd);

    var entry = {label: t.label, ops: back, sel0: t.sel0, key: t.key};
    if (t.kind === 'do') {
      redoS.length = 0;
      var top = undoS[undoS.length - 1];
      if (t.key !== null && top && top.key === t.key) top.ops = mergeOps(back.concat(top.ops));
      else { undoS.push(entry); if (undoS.length > UNDO_MAX) undoS.shift(); }
    } else if (t.kind === 'undo') redoS.push(entry);
    else { undoS.push(entry); if (undoS.length > UNDO_MAX) undoS.shift(); }

    if (t.removed.size) sel._drop(t.removed);
    em.emit('ops', fwd, b);
    em.emit('change', {
      ids: t.changed, structural: t.structural, remote: false, removed: t.removed, props: t.props,
      label: t.label, undo: t.kind !== 'do'
    });
    return true;
  }

  function runTx(label, kind, fn, key) {
    cur = newTx(label, kind, key);
    depth = 1;
    var out;
    try { out = fn(); } catch (err) { abortTx(); throw err; }
    if (cur.steps.length && HD.layout && typeof HD.layout.run === 'function') {
      try { HD.layout.run(layoutIds(cur), cur.props); } catch (err2) { report(err2); }
    }
    commitTx();
    return out;
  }
  var warned = false;
  function blocked() {
    if (!store.readOnly) return false;
    if (!warned && W.console && W.console.warn) { warned = true; W.console.warn('[HD] the document is read-only: edit ignored'); }
    return true;
  }
  function inTx(label, fn) {
    if (depth > 0) return fn();
    if (blocked()) return undefined;
    return runTx(label, 'do', fn, gKey);
  }

  /* ================================================================ public: reading */
  store.get = function (id) { return nodes.get(id); };
  store.has = function (id) { return nodes.has(id); };
  /* the value of a property, or its default for the node's type when the node does not carry it */
  store.prop = function (id, name) {
    var n = nodes.get(id);
    if (!n) return undefined;
    var v = n[name];
    return v !== undefined ? v : (DEF[n.type] || NO_DEF)[name];
  };
  store.defaults = function (type) { return clone(DEF[type] || NO_DEF); };
  store.children = function (id) { return childrenOf(id); };
  store.parent = function (id) { var n = nodes.get(id); return n ? n.parent : undefined; };
  store.pageOf = function (id) {
    var c = id, n;
    while (c !== undefined) {
      n = nodes.get(c);
      if (!n) return undefined;
      if (n.type === 'PAGE') return c;
      c = n.parent;
    }
    return undefined;
  };
  store.pages = function () {
    var ks = childrenOf(ROOT), out = [];
    for (var i = 0; i < ks.length; i++) if (nodes.get(ks[i]).type === 'PAGE') out.push(ks[i]);
    return out;
  };
  /* [parent, grandparent, ..., root] */
  store.ancestors = function (id) {
    var out = [], n = nodes.get(id), c = n ? n.parent : undefined;
    while (c !== undefined && nodes.has(c)) { out.push(c); c = nodes.get(c).parent; }
    return out;
  };
  store.isAncestor = function (a, b) { return isAncestor(a, b); };
  /* depth-first, parents first, children in z order. fn(id, node, depth); return false to skip that subtree. */
  store.walk = function (id, fn) {
    if (!nodes.has(id)) return;
    var stack = [id], ds = [0], c, d, ks, i;
    while (stack.length) {
      c = stack.pop(); d = ds.pop();
      if (fn(c, nodes.get(c), d) === false) continue;
      ks = childrenOf(c);
      for (i = ks.length - 1; i >= 0; i--) { stack.push(ks[i]); ds.push(d + 1); }
    }
  };
  /* the ids sorted in document order (parents before children, lower layers first) */
  store.order = function (ids) {
    ids = toArr(ids).filter(function (id) { return nodes.has(id); });
    if (ids.length < 2) return ids.slice();
    var paths = new Map();
    ids.forEach(function (id) {
      var p = [], c = id;
      while (c !== undefined && nodes.has(c)) { p.push(c); c = nodes.get(c).parent; }
      paths.set(id, p.reverse());
    });
    return ids.slice().sort(function (a, b) {
      var pa = paths.get(a), pb = paths.get(b), n = Math.min(pa.length, pb.length);
      for (var i = 0; i < n; i++) if (pa[i] !== pb[i]) return cmpChild(pa[i], pb[i]);
      return pa.length - pb.length;
    });
  };
  store.count = function () { return nodes.size; };
  store.toDoc = function () {
    var out = {};
    nodes.forEach(function (n, id) { out[id] = n; });
    return {nodes: out};
  };
  store.localMatrix = function (id) { return localRaw(id).slice(); };
  store.worldMatrix = function (id) { return worldRaw(id).slice(); };
  /* world box of the node's own (0,0)..(w,h); for a PAGE: of everything on it */
  store.worldBounds = function (id) { return copyRect(boundsRaw(id)); };
  /* world box of the node AND what it shows outside itself: visible descendants, stopped at a clipping frame */
  store.subtreeBounds = function (id) { return copyRect(subtreeRaw(id)); };

  /* ================================================================ public: editing */
  store.newId = function () {
    var id;
    do { id = cid + ':' + (++counter); } while (nodes.has(id));
    return id;
  };
  function nextName(type) {
    var label = LABEL[type] || type, n = nameN.get(type);
    if (n === undefined) {
      n = 0;
      var pre = label + ' ', L = pre.length;
      nodes.forEach(function (nd) {
        if (nd.type !== type || typeof nd.name !== 'string' || nd.name.length <= L || nd.name.slice(0, L) !== pre) return;
        var tail2 = nd.name.slice(L);
        if (/^\d{1,9}$/.test(tail2)) { var v = +tail2; if (v > n) n = v; }
      });
    }
    n++;
    nameN.set(type, n);
    return label + ' ' + n;
  }
  function idxOf(id) { var n = nodes.get(id); return n && n.idx !== undefined ? n.idx : null; }
  /* [a, b]: the idx bounds for a new child of pid placed before beforeId (or last). skip = ids to look past */
  function slot(pid, beforeId, skip) {
    var ks, i;
    if (beforeId !== undefined && beforeId !== null) {
      var bn = nodes.get(beforeId);
      if (bn && bn.parent === pid) {
        ks = childrenOf(pid);
        i = ks.indexOf(beforeId) - 1;
        while (i >= 0 && skip && skip.has(ks[i])) i--;
        return [i >= 0 ? idxOf(ks[i]) : null, idxOf(beforeId)];
      }
    }
    if (!skip) return [idxOf(lastChild(pid)), null];
    ks = childrenOf(pid);
    i = ks.length - 1;
    while (i >= 0 && skip.has(ks[i])) i--;
    return [i >= 0 ? idxOf(ks[i]) : null, null];
  }

  store.create = function (type, parentId, props, beforeId) {
    if (!hasOwn.call(DEF, type) || type === 'DOCUMENT') throw new Error('HD.store.create: unknown type ' + type);
    return inTx('Create', function () {
      if (!nodes.has(parentId)) throw new Error('HD.store.create: no such parent ' + parentId);
      var id = store.newId(), s = slot(parentId, beforeId, null);
      var node = {type: type, parent: parentId, idx: between(s[0], s[1]), name: ''}, k, v;
      if (props) {
        for (k in props) {
          v = props[k];
          if (v === undefined || v === null || k === 'type' || k === 'parent' || k === 'idx') continue;
          if (typeof v === 'number' && v !== v) continue;
          node[k] = v;
        }
      }
      if (typeof node.name !== 'string' || !node.name) node.name = nextName(type);
      recCreate(id, node);
      return id;
    });
  };

  store.set = function (id, props) {
    if (!props) return false;
    return inTx('Change', function () {
      var n = nodes.get(id);
      if (!n) return false;
      if (props.parent !== undefined && props.parent !== n.parent && !okParent(id, props.parent)) {
        props = Object.assign({}, props);            /* a reparent that can not be: keep the rest of the edit */
        delete props.parent; delete props.idx;
      }
      if (props.type !== undefined && (!hasOwn.call(DEF, props.type) || (props.type === 'DOCUMENT') !== (id === ROOT))) {
        props = Object.assign({}, props); delete props.type;
      }
      if (props.idx !== undefined && !idxOk(props.idx)) { props = Object.assign({}, props); delete props.idx; }
      return recSet(id, n, props);
    }) || false;
  };

  store.remove = function (ids) {
    ids = toArr(ids);
    return inTx('Delete', function () {
      var any = false;
      for (var i = 0; i < ids.length; i++) if (recDelete(ids[i])) any = true;     /* a child of an already removed node is simply gone */
      return any;
    }) || false;
  };

  /* reparent / reorder. The nodes keep their place on the canvas: x, y, rot (and flipH) are rewritten for the
     new parent. They keep their order among themselves and land before beforeId (null = on top). */
  store.move = function (ids, parentId, beforeId) {
    ids = toArr(ids);
    return inTx('Move', function () {
      if (!nodes.has(parentId)) return false;
      var seen = new Set(), list = [], i, id;
      for (i = 0; i < ids.length; i++) {
        id = ids[i];
        if (seen.has(id) || !nodes.has(id) || !okParent(id, parentId)) continue;
        seen.add(id); list.push(id);
      }
      list = list.filter(function (x) {                 /* a node whose ancestor moves too goes along with it */
        var p = nodes.get(x).parent;
        while (p !== undefined) { if (seen.has(p)) return false; p = nodes.get(p) ? nodes.get(p).parent : undefined; }
        return true;
      });
      if (!list.length) return false;
      list = store.order(list);
      var moving = new Set(list), ks, j;
      if (beforeId !== undefined && beforeId !== null) {
        var bn = nodes.get(beforeId);
        if (!bn || bn.parent !== parentId) beforeId = null;
        else if (moving.has(beforeId)) {
          ks = childrenOf(parentId);
          j = ks.indexOf(beforeId) + 1;
          while (j < ks.length && moving.has(ks[j])) j++;
          beforeId = j < ks.length ? ks[j] : null;
        }
      }
      var s = slot(parentId, beforeId, moving), keys = nBetween(s[0], s[1], list.length);
      var ip = null, any = false;
      for (i = 0; i < list.length; i++) {
        id = list[i];
        var n = nodes.get(id), p = {parent: parentId, idx: keys[i]};
        if (n.parent !== parentId && n.type !== 'PAGE' && n.type !== 'DOCUMENT') {
          if (ip === null) ip = M.inv(worldRaw(parentId));
          var d = DEF[n.type] || NO_DEF;
          var w = n.w === undefined ? (d.w || 0) : +n.w || 0, h = n.h === undefined ? (d.h || 0) : +n.h || 0;
          var m = M.mul(ip, worldRaw(id));
          var fy = n.flipV ? -1 : 1, fx = (m[0] * m[3] - m[1] * m[2] < 0 ? -1 : 1) * fy;
          var rot = M.round(M.normDeg(Math.atan2(m[1] * fx, m[0] * fx) * 180 / Math.PI), 6);
          var c = M.apply(m, w / 2, h / 2), x = M.round(c[0] - w / 2, 6), y = M.round(c[1] - h / 2, 6);
          if (x !== (+n.x || 0)) p.x = x;
          if (y !== (+n.y || 0)) p.y = y;
          if (rot !== M.normDeg(+n.rot || 0)) p.rot = rot;
          if ((fx < 0) !== !!n.flipH) p.flipH = fx < 0;
        }
        if (recSet(id, n, p)) any = true;
      }
      return any;
    }) || false;
  };

  /* tx(label, fn [, {merge: key}])  everything inside = ONE undo step and ONE op batch; a tx inside a tx joins it.
     {merge: key}: this tx joins the previous undo step when that one was made with the same key (a drag that
     sends an update on every pointer move and still undoes in one step). Use a key that is unique per gesture,
     or gesture() / gestureEnd(). */
  store.tx = function (label, fn, opts) {
    if (typeof label === 'function') { opts = fn; fn = label; label = ''; }
    if (typeof fn !== 'function') return undefined;
    if (depth > 0) { depth++; try { return fn(); } finally { depth--; } }
    if (blocked()) return undefined;
    return runTx(label, 'do', fn, opts && opts.merge !== undefined && opts.merge !== null ? 'm:' + opts.merge : gKey);
  };
  store.inTx = function () { return depth > 0; };
  /* from now until gestureEnd() every tx lands in ONE undo step (ops still go out per tx) */
  store.gesture = function () { gKey = 'g:' + (++gSeq); };
  store.gestureEnd = function () {
    gKey = null;
    var top = undoS[undoS.length - 1];
    if (top) top.key = null;                           /* sealed: nothing merges into it any more */
  };

  function replay(from, kind) {
    if (depth > 0 || !from.length || blocked()) return false;
    var e = from.pop();               /* a step whose nodes other people removed is simply used up */
    runTx(e.label, kind, function () {
      for (var i = 0; i < e.ops.length; i++) recOp(e.ops[i]);
    }, null);
    var ids = e.sel0 ? e.sel0.filter(function (id) { return nodes.has(id); }) : [];
    if (ids.length) {
      var pg = store.pageOf(ids[0]);
      if (pg && pg !== sel.page) sel.setPage(pg);
    }
    sel.set(ids);
    return true;
  }
  store.undo = function () { return replay(undoS, 'undo'); };
  store.redo = function () { return replay(redoS, 'redo'); };
  store.canUndo = function () { return undoS.length > 0; };
  store.canRedo = function () { return redoS.length > 0; };
  store.undoLabel = function () { var e = undoS[undoS.length - 1]; return e ? e.label : null; };
  store.redoLabel = function () { var e = redoS[redoS.length - 1]; return e ? e.label : null; };

  /* ================================================================ public: events */
  store.on = function (evt, fn) { return em.on(evt, fn); };
  store.off = function (evt, fn) { em.off(evt, fn); };
  store.onOps = function (fn) { return em.on('ops', fn); };

  /* ================================================================ sync
   * THE RULE THAT IS ALWAYS TRUE while tracking:   what is on screen  =  shadow + our waiting ops, applied in order
   * with the server's own rules (rule() below is app/design/doc.py Doc.apply, line for line).
   *   - a local edit changes the screen and joins the waiting ops;
   *   - a remote op changes the shadow. Nearly always it can be put on screen directly (skipping the props a
   *     waiting op of ours writes). When it changes the tree while one of OUR waiting ops changes the tree too,
   *     the screen is worked out again from the shadow (rebase): exact, no guessing, no network;
   *   - an ack moves our accepted ops into the shadow (nothing on screen changes), a rejected op is dropped
   *     from the waiting ops and the screen is worked out again.
   */
  function kadd(K, pid, id) {
    var ks = K.get(pid);
    if (!ks) { ks = new Set(); K.set(pid, ks); }
    ks.add(id);
  }
  function inside(N, start, anc) {            /* is `anc` the node `start` or above it */
    var c = start, n, guard = 0;
    while (c !== undefined && ++guard < 200000) {
      if (c === anc) return true;
      n = N.get(c);
      c = n ? n.parent : undefined;
    }
    return guard >= 200000;
  }
  function idxOk(v) { return typeof v === 'string' && v.length > 0 && v.length <= 4096; }
  /* one op on a document (N nodes, K children) under the server's rules: 1 applied, 0 dropped, -1 rejected */
  function rule(N, K, op) {
    var id = op.id, n, p, k, v, ks, stack, c, oldP;
    if (op.del) {
      if (id === ROOT) return -1;
      n = N.get(id);
      if (!n) return 0;
      ks = K.get(n.parent);
      if (ks) ks.delete(id);
      stack = [id];
      while (stack.length) {
        c = stack.pop();
        N.delete(c);
        ks = K.get(c);
        if (ks) { ks.forEach(function (x) { stack.push(x); }); K.delete(c); }
      }
      return 1;
    }
    p = op.p;
    if (!p || typeof p !== 'object') return -1;
    n = N.get(id);
    if (!n) {
      if (p.type === undefined || p.type === null) return 0;          /* a late edit of a node that is gone */
      if (typeof p.type !== 'string' || !hasOwn.call(DEF, p.type) || p.type === 'DOCUMENT') return -1;
      if (typeof p.parent !== 'string' || !N.has(p.parent) || !idxOk(p.idx)) return -1;
      N.set(id, cleanCopy(p));
      kadd(K, p.parent, id);
      return 1;
    }
    if (hasOwn.call(p, 'type') && (typeof p.type !== 'string' || !hasOwn.call(DEF, p.type) || (p.type === 'DOCUMENT') !== (id === ROOT))) return -1;
    oldP = n.parent;
    if (hasOwn.call(p, 'parent')) {
      if (id === ROOT || typeof p.parent !== 'string' || !N.has(p.parent)) return -1;
      if (p.parent !== oldP && inside(N, p.parent, id)) return -1;
    }
    if (hasOwn.call(p, 'idx') && id !== ROOT && !idxOk(p.idx)) return -1;
    for (k in p) {
      v = p[k];
      if (v === null) delete n[k]; else if (v !== undefined) n[k] = v;
    }
    if (n.parent !== oldP) {
      ks = K.get(oldP);
      if (ks) ks.delete(id);
      kadd(K, n.parent, id);
    }
    return 1;
  }

  store.tracking = function (on) {
    if (on === undefined) return tracking;
    on = !!on;
    if (on === tracking) return tracking;
    tracking = on;
    clearPending();
    if (on) takeShadow(); else { shadow = null; skid = null; }
    return tracking;
  };
  function clearPending() {
    pendQ = []; pendB.clear(); pcnt.clear(); pids.clear(); pmade.clear(); pstruct = 0;
    opRec = new WeakMap();
  }
  function takeShadow() {                       /* the screen IS the server's document right now */
    shadow = new Map(); skid = new Map();
    nodes.forEach(function (n, id) {
      shadow.set(id, Object.assign({}, n));
      if (n.parent !== undefined) kadd(skid, n.parent, id);
    });
  }
  /* batches of ours still waiting for the server */
  store.pendingCount = function () { return pendQ.length; };
  /* for tests and a debug panel */
  store.pendingInfo = function () {
    return {batches: pendQ.length, keys: Array.from(pcnt.keys()), ids: Array.from(pids.keys()), structural: pstruct};
  };

  /* shadow + waiting ops, as a fresh document. mark: remember per waiting op whether it applied */
  function project(mark) {
    var N = new Map(), K = new Map(), i, j, recs, rec, live;
    shadow.forEach(function (sn, id) {
      N.set(id, Object.assign({}, sn));
      if (sn.parent !== undefined) kadd(K, sn.parent, id);
    });
    for (i = 0; i < pendQ.length; i++) {
      recs = pendQ[i].recs;
      for (j = 0; j < recs.length; j++) {
        rec = recs[j];
        if (rec.done) continue;
        live = rule(N, K, rec.op) === 1;
        if (mark && live !== rec.live) { rec.live = live; countKeys(rec.op, live ? 1 : -1); }
      }
    }
    return [N, K];
  }
  function nodeDiff(a, b) {
    var d = null, k;
    for (k in a) if (!(k in b) || (a[k] !== b[k] && !same(a[k], b[k]))) (d || (d = new Set())).add(k);
    for (k in b) if (!(k in a)) (d || (d = new Set())).add(k);
    return d;
  }
  /* work the screen out again. ch (optional) collects what changed for the 'change' event. A node that comes out
     the same keeps its very object. */
  function rebase(ch) {
    var old = nodes, pr = project(true), N = pr[0];
    old.forEach(function (on, id) {
      var nn = N.get(id);
      if (!nn) {
        if (ch) { ch.ids.add(id); ch.removed.add(id); ch.structural = true; }
        return;
      }
      var d = nodeDiff(on, nn);
      if (!d) { N.set(id, on); return; }
      if (ch) {
        ch.ids.add(id); ch.props.set(id, d);
        if (d.has('parent') || d.has('idx') || d.has('type')) ch.structural = true;
      }
    });
    if (ch) N.forEach(function (nn, id) { if (!old.has(id)) { ch.ids.add(id); ch.structural = true; } });
    nodes = N; kidSet = pr[1];
    sorted = new Map(); tail = new Map(); lm = new Map(); wm = new Map(); wb = new Map(); sb = new Map();
  }
  /* debug / tests: ids where the screen is NOT shadow + waiting ops (always [] unless there is a bug) */
  store.syncCheck = function (detail) {
    if (!tracking) return [];
    var N = project(false)[0], out = [];
    nodes.forEach(function (n, id) { var m = N.get(id); if (!m || nodeDiff(n, m)) out.push(detail ? {id: id, screen: n, want: m || null} : id); });
    N.forEach(function (m, id) { if (!nodes.has(id)) out.push(detail ? {id: id, screen: null, want: m} : id); });
    return out;
  };
  /* the server's document as this client knows it (debug / tests) */
  store.serverDoc = function () {
    var out = {};
    (shadow || nodes).forEach(function (n, id) { out[id] = n; });
    return {nodes: out};
  };

  function newChange() { return {ids: new Set(), structural: false, remote: true, removed: new Set(), props: new Map()}; }
  function chSet(ch, id, chg) {
    ch.ids.add(id);
    var s = ch.props.get(id);
    if (!s) { s = new Set(); ch.props.set(id, s); }
    for (var k in chg) s.add(k);
    if (hasOwn.call(chg, 'parent') || hasOwn.call(chg, 'idx') || hasOwn.call(chg, 'type')) ch.structural = true;
  }
  function chDel(ch, list) {
    for (var i = 0; i < list.length; i++) { ch.ids.add(list[i][0]); ch.removed.add(list[i][0]); }
    if (list.length) ch.structural = true;
  }
  function finish(ch, desync) {
    if (ch.removed.size) sel._drop(ch.removed);
    if (ch.ids.size) em.emit('change', ch);
    if (desync) em.emit('desync', {});
  }
  function findRec(op) {                    /* an op that is not the object we handed out: match by content */
    if (!op) return null;
    for (var i = 0; i < pendQ.length; i++) {
      var recs = pendQ[i].recs;
      for (var j = 0; j < recs.length; j++) {
        var r = recs[j];
        if (!r.done && r.op.id === op.id && !!r.op.del === !!op.del && (op.del || same(r.op.p, op.p))) return r;
      }
    }
    return null;
  }
  function settle(rec) {                    /* this op has its answer */
    rec.done = true;
    countOp(rec.op, -1);
    if (rec.live) { rec.live = false; countKeys(rec.op, -1); }
    var batch = rec.batch;
    if (--batch.left > 0) return;
    pendB.delete(batch.b);
    if (pendQ[0] === batch) pendQ.shift();
    else { var i = pendQ.indexOf(batch); if (i >= 0) pendQ.splice(i, 1); }
  }

  /* acked(ops)  the server ACCEPTED these ops of ours (the op objects from onOps, in the order they were sent).
     acked(b)    the same for every op of batch b that has no answer yet.
     They move into the shadow; the screen already shows them. */
  store.acked = function (x) {
    if (!tracking) return false;
    var list = [], i, rec, bad = false;
    if (typeof x === 'number') {
      var batch = pendB.get(x);
      if (!batch) return false;
      list = batch.recs.slice();
    } else {
      x = toArr(x);
      for (i = 0; i < x.length; i++) { rec = opRec.get(x[i]) || findRec(x[i]); if (rec) list.push(rec); }
    }
    for (i = 0; i < list.length; i++) {
      rec = list[i];
      if (rec.done) continue;
      settle(rec);
      if (rule(shadow, skid, rec.op) === -1) bad = true;      /* the server took what its own rules refuse: we lost track */
    }
    if (bad) em.emit('desync', {});
    return true;
  };

  /* rollback(ops)  the server REJECTED these ops of ours: they leave the waiting list and the screen is worked
     out again from the server's document + what is still waiting. */
  store.rollback = function (ops) {
    ops = toArr(ops);
    var any = false, i, rec;
    for (i = 0; i < ops.length; i++) {
      rec = opRec.get(ops[i]) || findRec(ops[i]);
      if (!rec || rec.done) continue;
      rec.rej = true;
      settle(rec);
      any = true;
    }
    if (!any || !tracking) return false;
    var ch = newChange();
    rebase(ch);
    finish(ch, false);
    return true;
  };

  /* can the remote ops go on screen one by one, or must the screen be worked out again */
  function needsRebase(ops) {
    for (var i = 0; i < ops.length; i++) {
      var op = ops[i];
      if (!op || typeof op.id !== 'string') continue;
      if (op.del) { if (pstruct > 0) return true; continue; }
      var p = op.p;
      if (!p || typeof p !== 'object') continue;
      var made = hasOwn.call(p, 'type');
      if ((made || hasOwn.call(p, 'parent')) && pstruct > 0) return true;     /* both sides change the tree */
      if (made && pids.has(op.id)) return true;                              /* a node (back) for which an edit of ours waits */
      if (pmade.has(op.id)) return true;                                      /* we are (re)making this very node */
    }
    return false;
  }
  /* one remote op straight onto the screen; false = it does not fit (the caller rebases) */
  function remoteLocal(op, ch) {
    var id = op.id, p, n, use, k, r;
    if (op.del) {
      if (id !== ROOT && nodes.has(id)) chDel(ch, rawDelete(id));
      return true;
    }
    p = op.p;
    if (!p || typeof p !== 'object') return true;
    n = nodes.get(id);
    if (n) {
      use = p;
      if (pcnt.size) {
        use = null;
        for (k in p) if (!pcnt.has(id + '\n' + k)) (use || (use = {}))[k] = p[k];     /* a waiting write of ours wins */
        if (!use) return true;
      }
      if (use.parent !== undefined && use.parent !== n.parent && !okParent(id, use.parent)) return false;
      r = rawSet(id, n, use);
      if (r) chSet(ch, id, r[0]);
      return true;
    }
    if (p.type === undefined || p.type === null) return true;        /* not on screen: one of our waiting ops deletes it */
    if (typeof p.type !== 'string' || !hasOwn.call(DEF, p.type) || id === ROOT) return true;
    if (!nodes.has(p.parent)) return false;
    rawCreate(id, cleanCopy(p));
    ch.ids.add(id); ch.structural = true;
    return true;
  }

  /* ops of other people (already accepted by the server, in its order). Never undoable, never sent back,
     never run through HD.layout. */
  store.applyRemote = function (ops) {
    if (!isArr(ops) || !ops.length) return;
    var ch = newChange(), bad = false, need = false, i, op;
    if (!tracking) {
      for (i = 0; i < ops.length; i++) if (ops[i] && typeof ops[i].id === 'string') remoteLocal(ops[i], ch);
      finish(ch, false);
      return;
    }
    if (pendQ.length) need = needsRebase(ops);
    for (i = 0; i < ops.length; i++) {
      op = ops[i];
      if (!op || typeof op.id !== 'string') continue;
      if (rule(shadow, skid, op) === -1) bad = true;           /* the server sent what its rules refuse: we lost track */
      if (!need && !remoteLocal(op, ch)) need = true;
    }
    if (need) rebase(ch);
    finish(ch, bad);
  };

  /* ================================================================ load */
  /* load(doc, cid)               a new document: undo and waiting ops are forgotten
     load(doc, cid, {keep:true})  the same file again after a reconnect: undo is kept, and the ops the server has
                                  not answered are put back on top of the fresh document (net sends them again) */
  store.load = function (doc, newCid, opts) {
    var keep = !!(opts && opts.keep), src = doc && doc.nodes ? doc.nodes : {}, id, n, k;
    if (depth > 0) { cur = null; depth = 0; }
    nodes = new Map(); kidSet = new Map(); sorted = new Map(); tail = new Map();
    lm = new Map(); wm = new Map(); wb = new Map(); sb = new Map();
    nameN = new Map();
    newCid = (newCid === undefined || newCid === null) ? 0 : newCid;
    if (!(keep && newCid === cid)) counter = 0;      /* same client number again: ids of waiting edits stay taken */
    cid = newCid;
    var pre = cid + ':', pl = pre.length, ks;
    for (id in src) {
      n = src[id];
      if (!n || typeof n !== 'object' || typeof n.type !== 'string') continue;
      nodes.set(id, n);
      k = n.parent;
      if (k !== undefined && k !== null && id !== ROOT) {
        ks = kidSet.get(k);
        if (!ks) { ks = new Set(); kidSet.set(k, ks); }
        ks.add(id);
      } else if (k !== undefined) delete n.parent;
      if (id.length > pl && id.charCodeAt(0) === pre.charCodeAt(0) && id.slice(0, pl) === pre) {
        var num = +id.slice(pl);
        if (num > counter) counter = num;
      }
    }
    if (!nodes.has(ROOT)) nodes.set(ROOT, {type: 'DOCUMENT', name: 'Document'});
    if (!keep) { undoS = []; redoS = []; gKey = null; }
    if (!keep || !tracking) clearPending();
    if (tracking) {
      takeShadow();
      if (pendQ.length) rebase(null);
    }
    sel._load();
    em.emit('load', {keep: keep});
  };

  /* ================================================================ HD.sel */
  var sem = new Emitter(), selSet = new Set();
  sel = HD.sel = {ids: EMPTY, page: null};
  function selEmit() { sem.emit('change', {ids: sel.ids, page: sel.page}); }
  function selWrite(arr) {
    sel.ids = arr.length ? Object.freeze(arr) : EMPTY;
    selSet = new Set(arr);
  }
  sel.set = function (ids) {
    var arr = [], seen = new Set(), src = toArr(ids), i;
    for (i = 0; i < src.length; i++) {
      if (typeof src[i] !== 'string' || seen.has(src[i]) || !nodes.has(src[i])) continue;
      seen.add(src[i]); arr.push(src[i]);
    }
    if (arr.length === sel.ids.length) {
      for (i = 0; i < arr.length; i++) if (arr[i] !== sel.ids[i]) break;
      if (i === arr.length) return false;
    }
    selWrite(arr);
    selEmit();
    return true;
  };
  sel.add = function (id) { return selSet.has(id) ? false : sel.set(sel.ids.concat(toArr(id))); };
  sel.remove = function (id) { return selSet.has(id) ? sel.set(sel.ids.filter(function (x) { return x !== id; })) : false; };
  sel.toggle = function (id) { return selSet.has(id) ? sel.remove(id) : sel.add(id); };
  sel.clear = function () { return sel.set([]); };
  sel.has = function (id) { return selSet.has(id); };
  sel.on = function (evt, fn) { return sem.on(evt, fn); };
  sel.off = function (evt, fn) { sem.off(evt, fn); };
  sel.setPage = function (id) {
    var n = nodes.get(id);
    if (!n || n.type !== 'PAGE') return false;
    if (id === sel.page) return false;
    sel.page = id;
    selWrite([]);
    selEmit();
    return true;
  };
  function firstPage() { var ps = store.pages(); return ps.length ? ps[0] : null; }
  sel._drop = function (removed) {
    var changed = false, arr = sel.ids;
    for (var i = 0; i < arr.length; i++) if (removed.has(arr[i])) { changed = true; break; }
    if (changed) selWrite(arr.filter(function (id) { return !removed.has(id); }));
    if (sel.page !== null && removed.has(sel.page)) { sel.page = firstPage(); if (!changed) selWrite([]); changed = true; }
    if (changed) selEmit();
  };
  sel._load = function () {
    var n = sel.page !== null ? nodes.get(sel.page) : null;
    if (!n || n.type !== 'PAGE') sel.page = firstPage();
    selWrite(sel.ids.filter(function (id) { return nodes.has(id); }));
    selEmit();
  };

  /* start with an empty document, so every call works before the first load */
  nodes.set(ROOT, {type: 'DOCUMENT', name: 'Document'});
})();
