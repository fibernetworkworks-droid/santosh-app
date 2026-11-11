/* HOOLA DESIGN client core: hd-math.js + hd-core.js + hd-net.js
 * Plain node, no packages:   node server/tests/web/design_core_test.js
 * The three files are loaded into a vm context with a fake window / clock / WebSocket / localStorage. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const DIR = path.resolve(__dirname, '../../app/static/console/design');
const SRC = ['hd-math.js', 'hd-core.js', 'hd-net.js'].map(f => ({f, code: fs.readFileSync(path.join(DIR, f), 'utf8')}));

function makeClock() {
  let t = 1000000, seq = 0;
  const timers = new Map();
  const c = {
    now: () => t,
    setTimeout(fn, ms) { const id = ++seq; timers.set(id, {at: t + (ms || 0), fn, every: 0}); return id; },
    clearTimeout(id) { timers.delete(id); },
    setInterval(fn, ms) { const id = ++seq; timers.set(id, {at: t + ms, fn, every: ms}); return id; },
    advance(ms) {
      const end = t + ms;
      for (;;) {
        let next = null;
        for (const [id, x] of timers) {
          if (x.at <= end && (!next || x.at < next[1].at || (x.at === next[1].at && id < next[0]))) next = [id, x];
        }
        if (!next) break;
        t = next[1].at;
        if (next[1].every) next[1].at += next[1].every; else timers.delete(next[0]);
        next[1].fn();
      }
      t = end;
    }
  };
  return c;
}

function makeEnv(opts) {
  opts = opts || {};
  const clock = makeClock();
  const sockets = [];
  class FakeWS {
    constructor(url, protocols) {
      this.url = url; this.protocols = protocols; this.readyState = 0; this.sent = []; this.bufferedAmount = 0;
      sockets.push(this);
    }
    send(s) { if (this.readyState !== 1) throw new Error('not open'); this.sent.push(JSON.parse(s)); }
    close(code) { this.readyState = 3; this.closedBy = 'client'; this.closeCode = code; }
    /* test side */
    open() { this.readyState = 1; if (this.onopen) this.onopen({}); }
    recv(obj) { if (this.onmessage) this.onmessage({data: JSON.stringify(obj)}); }
    drop(code) { this.readyState = 3; if (this.onclose) this.onclose({code: code || 1006}); }
    frames(t) { return this.sent.filter(m => m.t === t); }
  }
  const errors = [];
  const ctx = {
    console: {log() {}, warn() {}, error(...a) { errors.push(a); }},
    localStorage: {getItem: k => (k === 'hoola.console.token' ? (opts.noToken ? null : 'tok_ABC123') : null)},
    location: {protocol: opts.https ? 'https:' : 'http:', host: 'hoola.test:8077'},
    WebSocket: FakeWS,
    setTimeout: (fn, ms) => clock.setTimeout(fn, ms),
    clearTimeout: id => clock.clearTimeout(id),
    setInterval: (fn, ms) => clock.setInterval(fn, ms),
    clearInterval: id => clock.clearTimeout(id),
    requestAnimationFrame: fn => clock.setTimeout(fn, 16),
    addEventListener() {},
    __now: () => clock.now()
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext('Date.now = function () { return __now(); };', ctx);
  for (const s of SRC) vm.runInContext(s.code, ctx, {filename: s.f});
  return {HD: ctx.HD, ctx, clock, sockets, errors, last: () => sockets[sockets.length - 1]};
}

function baseDoc(extra) {
  const nodes = {
    '0:0': {type: 'DOCUMENT', name: 'Document'},
    '0:1': {type: 'PAGE', parent: '0:0', idx: 'a0', name: 'Page 1'}
  };
  return {nodes: Object.assign(nodes, extra || {})};
}
const snap = HD => JSON.parse(JSON.stringify(HD.store.toDoc()));
/* objects made inside the vm context have another realm's prototypes: compare by value */
const deq = (a, e, m) => assert.deepStrictEqual(JSON.parse(JSON.stringify(a)), JSON.parse(JSON.stringify(e)), m);
const near = (a, b, eps) => Math.abs(a - b) <= (eps || 1e-9);
function nearArr(a, b, eps, msg) {
  assert.equal(a.length, b.length, msg);
  for (let i = 0; i < a.length; i++) assert.ok(near(a[i], b[i], eps || 1e-9), (msg || '') + ' [' + i + '] ' + a[i] + ' vs ' + b[i]);
}
function nearRect(r, x, y, w, h, eps) {
  nearArr([r.x, r.y, r.w, r.h], [x, y, w, h], eps || 1e-9, 'rect ' + JSON.stringify(r));
}
/* a tiny deterministic random */
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }

/* ============================================================== HD.math */
test('math: matrices and rects', () => {
  const {HD} = makeEnv(), M = HD.math;
  nearArr(M.identity(), [1, 0, 0, 1, 0, 0]);
  const T = M.translate(10, 20), R = M.rotate(Math.PI / 2), S = M.scale(2, 3);
  nearArr(M.apply(T, 1, 1), [11, 21]);
  nearArr(M.apply(R, 1, 0), [0, 1]);                       /* +90 degrees = clockwise on a y-down canvas */
  nearArr(R, [0, 1, -1, 0, 0, 0]);                         /* exact at a quarter turn */
  nearArr(M.apply(S, 1, 1), [2, 3]);
  nearArr(M.apply(M.mul(T, R), 1, 0), [10, 21]);           /* mul(m, n): n first, then m */
  nearArr(M.mul(M.mul(T, R), M.inv(M.mul(T, R))), [1, 0, 0, 1, 0, 0]);
  nearArr(M.translate(M.scale(2), 5, 5), [2, 0, 0, 2, 10, 10]);   /* the (m, ...) form post-multiplies */
  nearArr(M.rotate(M.identity(), Math.PI), [-1, 0, 0, -1, 0, 0]);
  nearArr(M.apply(M.rotateDeg(90, 10, 10), 20, 10), [10, 20]);
  nearRect(M.rectUnion({x: 0, y: 0, w: 10, h: 10}, {x: 5, y: -5, w: 10, h: 10}), 0, -5, 15, 15);
  assert.equal(M.rectHit({x: 0, y: 0, w: 10, h: 10}, {x: 10, y: 10, w: 5, h: 5}), true);
  assert.equal(M.rectHit({x: 0, y: 0, w: 10, h: 10}, {x: 11, y: 0, w: 5, h: 5}), false);
  assert.equal(M.rectContains({x: 0, y: 0, w: 10, h: 10}, {x: 2, y: 2, w: 3, h: 3}), true);
  assert.equal(M.rectContains({x: 0, y: 0, w: 10, h: 10}, {x: 8, y: 2, w: 3, h: 3}), false);
  const r = {x: 0, y: 0, w: 10, h: 10};
  assert.ok(M.ptInRect(r, 5, 5) && M.ptInRect(5, 5, r) && M.ptInRect([5, 5], r) && M.ptInRect(r, [5, 5]));
  assert.ok(!M.ptInRect(r, 11, 5));
  nearRect(M.boundsOf(M.nodeMatrix(0, 0, 100, 100, 45, false, false), 100, 100),
    50 - Math.SQRT1_2 * 100, 50 - Math.SQRT1_2 * 100, Math.SQRT2 * 100, Math.SQRT2 * 100, 1e-9);
  const cs = M.rectCorners({x: 0, y: 0, w: 20, h: 10}, 90);
  nearArr(cs[0], [15, -5]); nearArr(cs[2], [5, 15]);
  assert.equal(M.clamp(5, 0, 3), 3); assert.equal(M.lerp(0, 10, 0.25), 2.5);
  assert.ok(near(M.deg(Math.PI), 180) && near(M.rad(180), Math.PI) && near(M.dist(0, 0, 3, 4), 5));
  assert.equal(M.normDeg(270), -90); assert.equal(M.normDeg(-180), 180);
  assert.ok(M.ptInBox(M.nodeMatrix(0, 0, 100, 10, 90, false, false), 100, 10, 50, 40));
  assert.ok(!M.ptInBox(M.nodeMatrix(0, 0, 100, 10, 90, false, false), 100, 10, 90, 5));
});

/* ============================================================== HD.frac */
test('frac: 2,000 random inserts incl. head and tail keep a strict order', () => {
  const {HD} = makeEnv(), F = HD.frac, rnd = rng(42);
  const keys = [];
  let longest = 0;
  for (let i = 0; i < 2000; i++) {
    const roll = rnd();
    const pos = roll < 0.15 ? 0 : roll < 0.3 ? keys.length : Math.floor(rnd() * (keys.length + 1));
    const a = pos > 0 ? keys[pos - 1] : null, b = pos < keys.length ? keys[pos] : null;
    const k = F.between(a, b);
    assert.equal(typeof k, 'string');
    assert.ok(/^[0-9A-Za-z]*[1-9A-Za-z]$/.test(k), 'base 62, never ending in 0: ' + k);
    if (a !== null) assert.ok(a < k, a + ' < ' + k);
    if (b !== null) assert.ok(k < b, k + ' < ' + b);
    keys.splice(pos, 0, k);
    if (k.length > longest) longest = k.length;
  }
  deq(keys.slice().sort(), keys);              /* plain string order IS the order */
  assert.equal(new Set(keys).size, keys.length);
  console.log('  frac: 2,000 random inserts, longest key ' + longest + ' chars');
});

test('frac: 50,000 appends and 5,000 prepends stay short; nBetween; foreign keys', () => {
  const {HD} = makeEnv(), F = HD.frac;
  let k = null, prev = null, max = 0;
  for (let i = 0; i < 50000; i++) { k = F.between(prev, null); if (prev !== null) assert.ok(prev < k); assert.notEqual(k[k.length - 1], '0'); prev = k; if (k.length > max) max = k.length; }
  assert.ok(max <= 5, 'append key length ' + max);
  prev = null; let maxHead = 0;
  for (let i = 0; i < 5000; i++) { k = F.between(null, prev); if (prev !== null) assert.ok(k < prev, k + ' < ' + prev); assert.notEqual(k[k.length - 1], '0'); prev = k; if (k.length > maxHead) maxHead = k.length; }
  assert.ok(maxHead <= 5, 'prepend key length ' + maxHead);
  console.log('  frac: 50,000 appends -> max ' + max + ' chars; 5,000 prepends -> max ' + maxHead + ' chars');

  for (const [a, b, n] of [[null, null, 7], ['a0', null, 5], [null, 'a0', 5], ['a0', 'a1', 9], ['a0', 'a0V', 4]]) {
    const ks = F.nBetween(a, b, n);
    assert.equal(ks.length, n);
    const all = [].concat(a === null ? [] : [a], ks, b === null ? [] : [b]);
    for (let i = 1; i < all.length; i++) assert.ok(all[i - 1] < all[i], all[i - 1] + ' < ' + all[i]);
  }
  deq(F.nBetween('a0', 'a1', 0), []);

  /* keys from another (plain fraction) implementation, like the server's "V": only the ordering matters */
  for (const start of [['1', '5', '5V', 'V', 'Vz', 'h', 'zz'], ['V'], ['a0', 'a0V', 'b00'], ['zzz'], ['01']]) {
    const rnd = rng(7), keys = start.slice();
    for (let i = 0; i < 600; i++) {
      const roll = rnd();
      const pos = roll < 0.2 ? 0 : roll < 0.4 ? keys.length : Math.floor(rnd() * (keys.length + 1));
      const a = pos > 0 ? keys[pos - 1] : null, b = pos < keys.length ? keys[pos] : null;
      const key = F.between(a, b);
      if (a !== null) assert.ok(a < key, a + ' < ' + key);
      if (b !== null) assert.ok(key < b, key + ' < ' + b);
      assert.ok(/^[0-9A-Za-z]*[1-9A-Za-z]$/.test(key), 'never ends in 0: ' + key);
      keys.splice(pos, 0, key);
    }
    deq(keys.slice().sort(), keys);
  }
  assert.equal(F.between(null, null), 'a1');
  assert.equal(F.between('V', null), 'a1');                         /* on top of the server's first key: short keys from here on */
  let top = 'V', longest = 0;
  for (let i = 0; i < 5000; i++) { top = F.between(top, null); if (top.length > longest) longest = top.length; }
  assert.ok(longest <= 4, 'appends after a foreign key: ' + longest);
  assert.doesNotThrow(() => { F.between('a0', 'a0'); F.between('b', 'a'); F.between('', ''); F.between('a', 'a0'); });
});

/* ============================================================== HD.store basics */
test('store: load, create, set, remove, children order, names, defaults', () => {
  const {HD} = makeEnv(), S = HD.store;
  const batches = [];
  S.onOps((ops, b) => batches.push({ops: JSON.parse(JSON.stringify(ops)), b}));
  const changes = [];
  S.on('change', c => changes.push(c));
  let loads = 0;
  S.on('load', () => loads++);
  S.load(baseDoc(), 7);
  assert.equal(loads, 1);
  assert.equal(S.ROOT, '0:0');
  deq(S.pages(), ['0:1']);
  assert.equal(HD.sel.page, '0:1');

  const a = S.create('RECT', '0:1', {x: 10, y: 20, w: 50});
  assert.equal(a, '7:1');
  deq(S.get(a), {type: 'RECT', parent: '0:1', idx: S.get(a).idx, name: 'Rectangle 1', x: 10, y: 20, w: 50});
  assert.equal(batches.length, 1);
  deq(batches[0].ops, [{id: a, p: S.get(a)}]);                /* no defaults written into the op */
  assert.equal(S.prop(a, 'h'), 100);                                        /* ...they come from prop() */
  assert.equal(S.prop(a, 'visible'), true);
  assert.equal(S.prop(a, 'opacity'), 1);
  assert.equal(S.get(a).h, undefined);
  assert.equal(changes.length, 1);
  assert.ok(changes[0].ids.has(a) && changes[0].structural === true && changes[0].remote === false);

  const b = S.create('RECT', '0:1', {});
  const c = S.create('ELLIPSE', '0:1', {name: 'Dot'}, a);                   /* before a = below it */
  assert.equal(S.get(b).name, 'Rectangle 2');
  assert.equal(S.get(c).name, 'Dot');
  deq(S.children('0:1'), [c, a, b]);
  assert.ok(Object.isFrozen(S.children('0:1')));
  assert.equal(S.parent(a), '0:1'); assert.equal(S.pageOf(a), '0:1');
  deq(S.ancestors(a), ['0:1', '0:0']);

  /* set: only real changes become ops; null removes */
  const n0 = batches.length;
  assert.equal(S.set(a, {x: 10}), false);
  assert.equal(batches.length, n0);
  assert.equal(S.set(a, {x: 11, fills: [{type: 'solid', color: '#FF0000'}]}), true);
  deq(batches[batches.length - 1].ops, [{id: a, p: {x: 11, fills: [{type: 'solid', color: '#FF0000'}]}}]);
  assert.equal(S.set(a, {fills: [{type: 'solid', color: '#FF0000'}]}), false);   /* an equal value is no change */
  S.set(a, {fills: null});
  assert.equal(S.get(a).fills, undefined);
  deq(batches[batches.length - 1].ops, [{id: a, p: {fills: null}}]);
  assert.equal(S.set('9:9', {x: 1}), false);                                 /* a node that is gone: nothing */
  S.set(a, {x: NaN});
  assert.equal(S.get(a).x, 11);

  /* defaults per type */
  assert.equal(S.defaults('FRAME').clip, true);
  assert.equal(S.defaults('RECT').clip, false);
  assert.equal(S.defaults('STAR').sides, 5);
  assert.equal(S.defaults('POLYGON').sides, 3);
  assert.equal(S.defaults('TEXT').fontSize, 16);
  assert.equal(S.defaults('PAGE').bg, '#F5F5F5');
  deq(S.defaults('RECT').cons, {h: 'left', v: 'top'});
  const d = S.defaults('RECT'); d.fills.push(1);                             /* a private copy every time */
  deq(S.defaults('RECT').fills, []);
  assert.throws(() => S.create('NOPE', '0:1', {}));
  assert.throws(() => S.create('RECT', '9:9', {}));

  /* remove deletes the subtree and drops it from the selection */
  const f = S.create('FRAME', '0:1', {x: 0, y: 0, w: 300, h: 300});
  const k1 = S.create('RECT', f, {}), k2 = S.create('TEXT', f, {chars: 'hi'});
  const g = S.create('GROUP', f, {}), k3 = S.create('RECT', g, {});
  HD.sel.set([k1, k3, a]);
  let selEvents = 0;
  HD.sel.on('change', () => selEvents++);
  S.remove([f]);
  for (const id of [f, k1, k2, g, k3]) assert.equal(S.has(id), false);
  deq(HD.sel.ids.slice(), [a]);
  assert.equal(selEvents, 1);
  const last = batches[batches.length - 1].ops;
  deq(last, [{id: f, del: 1}]);                                 /* one op deletes the subtree */
  const ch = changes[changes.length - 1];
  assert.ok(ch.removed.has(k3) && ch.ids.has(f) && ch.structural);
  assert.equal(S.remove(['0:0']), false);                                    /* the root can not be deleted */
  assert.ok(S.has('0:0'));

  /* walk + order */
  const seen = [];
  S.walk('0:1', (id, node, depth) => { seen.push(id + '@' + depth); });
  deq(seen, ['0:1@0', c + '@1', a + '@1', b + '@1']);
  deq(S.order([b, c, a]), [c, a, b]);
  assert.equal(S.count(), 5);
});

test('store: tx = one op batch (merged per node, later value wins) and one undo step', () => {
  const {HD} = makeEnv(), S = HD.store;
  S.load(baseDoc(), 1);
  const batches = [], changes = [];
  S.onOps(ops => batches.push(JSON.parse(JSON.stringify(ops))));
  S.on('change', c => changes.push(c));
  const a = S.create('RECT', '0:1', {x: 0}), b = S.create('RECT', '0:1', {x: 0});
  batches.length = 0; changes.length = 0;
  const before = snap(HD);

  const out = S.tx('Drag', () => {
    S.set(a, {x: 1}); S.set(b, {x: 5}); S.set(a, {x: 2, y: 9});
    S.tx('inner', () => { S.set(a, {x: 3}); });               /* nesting joins the outer tx */
    S.set(b, {name: 'B'});
    assert.equal(batches.length, 0);                          /* nothing leaves before the tx closes */
    return 'done';
  });
  assert.equal(out, 'done');
  assert.equal(batches.length, 1);
  deq(batches[0], [{id: a, p: {x: 3, y: 9}}, {id: b, p: {x: 5, name: 'B'}}]);
  assert.equal(changes.length, 1);
  deq(Array.from(changes[0].ids).sort(), [a, b].sort());
  assert.equal(changes[0].structural, false);
  deq(Array.from(changes[0].props.get(a)).sort(), ['x', 'y']);

  /* create + set in one tx fold into the create op; a set that changes nothing gives no batch */
  let c;
  S.tx('Make', () => { c = S.create('RECT', '0:1', {}); S.set(c, {w: 40}); S.set(c, {w: 44}); });
  assert.equal(batches.length, 2);
  assert.equal(batches[1].length, 1);
  assert.equal(batches[1][0].p.w, 44);
  assert.equal(batches[1][0].p.type, 'RECT');
  S.tx('Nothing', () => { S.set(a, {x: 3}); });
  assert.equal(batches.length, 2);

  /* undo: ONE step each, sent as normal op batches */
  assert.ok(S.canUndo() && !S.canRedo());
  S.undo();                                                    /* the create */
  assert.equal(S.has(c), false);
  deq(batches[2], [{id: c, del: 1}]);
  S.undo();                                                    /* the drag */
  deq(snap(HD), before);
  deq(batches[3], [{id: b, p: {name: 'Rectangle 2', x: 0}}, {id: a, p: {x: 0, y: null}}]);   /* y did not exist -> null */
  assert.ok(changes[changes.length - 1].undo === true);
  S.redo();
  deq([S.get(a).x, S.get(a).y, S.get(b).x, S.get(b).name], [3, 9, 5, 'B']);
  S.redo();
  assert.ok(S.has(c) && S.get(c).w === 44);
  assert.equal(S.canRedo(), false);
  S.undo(); S.undo();
  deq(snap(HD), before);
  S.set(a, {x: 77});                                           /* a new edit clears redo */
  assert.equal(S.canRedo(), false);

  /* a tx that throws puts everything back and sends nothing */
  const n = batches.length, mid = snap(HD);
  assert.throws(() => S.tx('Boom', () => { S.set(a, {x: 500}); S.create('RECT', '0:1', {}); S.remove([b]); throw new Error('boom'); }), /boom/);
  deq(snap(HD), mid);
  assert.equal(batches.length, n);
  assert.equal(S.inTx(), false);
});

test('store: undo / redo round trips incl. delete-subtree restore with the same ids, props, parent and idx', () => {
  const {HD} = makeEnv(), S = HD.store;
  S.load(baseDoc(), 2);
  const f = S.create('FRAME', '0:1', {x: 100, y: 100, w: 400, h: 300, rot: 30, layout: {mode: 'h', gap: 8}});
  const a = S.create('RECT', f, {x: 10, y: 10, fills: [{type: 'solid', color: '#112233'}]});
  const g = S.create('GROUP', f, {x: 50, y: 50});
  const t = S.create('TEXT', g, {chars: 'Namaste', fontSize: 24});
  const e = S.create('ELLIPSE', g, {x: 5}, t);
  const z = S.create('RECT', '0:1', {});
  const full = snap(HD);
  const order = S.children(g).slice();
  HD.sel.set([f]);

  const batches = [];
  S.onOps(ops => batches.push(JSON.parse(JSON.stringify(ops))));
  S.remove([f]);
  assert.equal(S.count(), 3);
  deq(HD.sel.ids.slice(), []);
  S.undo();
  deq(snap(HD), full);                                 /* everything back, byte for byte */
  deq(S.children(g), order);
  deq(HD.sel.ids.slice(), [f]);                        /* and the selection */
  const re = batches[1];
  assert.equal(re.length, 5);                                       /* 5 creates, parents first */
  deq(re.map(o => o.id), [f, ...re.slice(1).map(o => o.id)]);
  const pos = new Map(re.map((o, i) => [o.id, i]));
  for (const o of re) if (pos.has(o.p.parent)) assert.ok(pos.get(o.p.parent) < pos.get(o.id), 'parent first');
  for (const o of re) assert.ok(o.p.type && o.p.parent && o.p.idx);
  S.redo();
  assert.equal(S.has(t), false);
  deq(batches[2], [{id: f, del: 1}]);
  S.undo();
  deq(snap(HD), full);

  /* a mixed tx: reparent + set + delete + create, undone and redone 3 times */
  let made;
  S.tx('Mixed', () => {
    S.move([t], '0:1', null);
    S.set(a, {x: 99, fills: null, radius: 4});
    S.remove([g]);
    made = S.create('STAR', f, {sides: 7});
    S.set(z, {name: 'Zed', rot: 45});
  });
  const after = snap(HD);
  for (let i = 0; i < 3; i++) {
    S.undo();
    deq(snap(HD), full, 'undo round ' + i);
    S.redo();
    deq(snap(HD), after, 'redo round ' + i);
  }
  assert.ok(S.has(made) && !S.has(e) && S.parent(t) === '0:1');

  /* undo of something another person already removed is harmless */
  S.set(z, {x: 5});
  S.applyRemote([{id: z, del: 1}]);
  assert.doesNotThrow(() => S.undo());
  assert.equal(S.has(z), false);

  /* gesture: many tx, one undo step; ops still leave per tx */
  const s0 = snap(HD), n0 = batches.length;
  S.gesture();
  for (let i = 1; i <= 5; i++) S.tx('Move', () => S.set(a, {x: 100 + i}));
  S.gestureEnd();
  assert.equal(batches.length, n0 + 5);
  S.tx('Other', () => S.set(a, {y: 1}));
  S.undo(); S.undo();
  deq(snap(HD), s0);
  /* {merge: key} does the same */
  S.tx('Nudge', () => S.set(a, {x: 1}), {merge: 'n1'});
  S.tx('Nudge', () => S.set(a, {x: 2}), {merge: 'n1'});
  S.tx('Nudge', () => S.set(a, {x: 3}), {merge: 'n2'});
  S.undo();
  assert.equal(S.get(a).x, 2);
  S.undo();
  deq(snap(HD), s0);
});

test('store: local and world matrices for nested rotated nodes match hand-computed numbers', () => {
  const {HD} = makeEnv(), S = HD.store;
  S.load(baseDoc(), 1);
  /* frame 200x100 at (100,50) turned 90 degrees clockwise: its centre (200,100) stays put */
  const f = S.create('FRAME', '0:1', {x: 100, y: 50, w: 200, h: 100, rot: 90});
  const c = S.create('RECT', f, {x: 10, y: 20, w: 40, h: 20});
  const g = S.create('RECT', f, {x: 10, y: 20, w: 40, h: 20, rot: 90});
  nearArr(S.localMatrix(f), [0, 1, -1, 0, 250, 0]);          /* (0,0) -> (200,100) + R90(-100,-50) = (250,0) */
  nearArr(S.worldMatrix(f), [0, 1, -1, 0, 250, 0]);
  nearRect(S.worldBounds(f), 150, 0, 100, 200);
  /* child: local (10,20) -> centre + R90((10,20) - (100,50)) = (200,100) + (30,-90) = (230,10) */
  nearArr(S.localMatrix(c), [1, 0, 0, 1, 10, 20]);
  nearArr(S.worldMatrix(c), [0, 1, -1, 0, 230, 10]);
  nearRect(S.worldBounds(c), 210, 10, 20, 40);
  /* child itself turned 90: 180 in total about its centre, local (30,30) -> world (220,30) */
  nearArr(S.worldMatrix(g), [-1, 0, 0, -1, 240, 40]);
  nearRect(S.worldBounds(g), 200, 20, 40, 20);

  /* 45 degrees: corner (0,0) of a 100x100 goes to (50, 50 - 70.7107) */
  const d = S.create('RECT', '0:1', {x: 0, y: 0, w: 100, h: 100, rot: 45});
  const m = S.worldMatrix(d), r2 = Math.SQRT1_2;
  nearArr(m, [r2, r2, -r2, r2, 50, 50 - 100 * r2], 1e-9);
  nearRect(S.worldBounds(d), 50 - 100 * r2, 50 - 100 * r2, 100 * Math.SQRT2, 100 * Math.SQRT2, 1e-9);
  /* 3 levels with a 30 degree turn at each: 90 in total; checked against the long-hand product */
  const l1 = S.create('FRAME', '0:1', {x: 300, y: 300, w: 200, h: 200, rot: 30});
  const l2 = S.create('FRAME', l1, {x: 20, y: 40, w: 100, h: 80, rot: 30});
  const l3 = S.create('RECT', l2, {x: 5, y: 6, w: 10, h: 20, rot: 30});
  const M = HD.math;
  const byHand = (x, y, w, h, deg) => {
    const t = deg * Math.PI / 180, cs = Math.cos(t), sn = Math.sin(t), cx = w / 2, cy = h / 2;
    return [cs, sn, -sn, cs, x + cx - (cs * cx - sn * cy), y + cy - (sn * cx + cs * cy)];
  };
  const want = M.mul(M.mul(byHand(300, 300, 200, 200, 30), byHand(20, 40, 100, 80, 30)), byHand(5, 6, 10, 20, 30));
  nearArr(S.worldMatrix(l3), want, 1e-9);
  nearArr([want[0], want[1], want[2], want[3]], [0, 1, -1, 0], 1e-9);       /* 30 + 30 + 30 = a quarter turn */
  /* flips: flipH mirrors about the centre */
  const fl = S.create('RECT', '0:1', {x: 10, y: 10, w: 100, h: 50, flipH: true});
  nearArr(M.apply(S.worldMatrix(fl), 0, 0), [110, 10]);
  nearArr(M.apply(S.worldMatrix(fl), 100, 50), [10, 60]);
  const fv = S.create('RECT', '0:1', {x: 10, y: 10, w: 100, h: 50, flipV: true, rot: 90});
  /* flip first, then turn: (0,0) -> flipV -> (0,50) -> about (50,25): (-50,25) -> R90 -> (-25,-50) -> (60+(-25), 35-50) */
  nearArr(M.apply(S.worldMatrix(fv), 0, 0), [35, -15]);

  /* caches: moving the frame moves its children, and only them; results are private copies */
  const other = S.worldBounds(d);
  S.worldMatrix(c)[4] = 99999; S.worldBounds(c).x = 99999;
  S.set(f, {x: 110});
  nearArr(S.worldMatrix(c), [0, 1, -1, 0, 240, 10]);
  nearRect(S.worldBounds(c), 220, 10, 20, 40);
  nearRect(S.worldBounds(d), other.x, other.y, other.w, other.h);
  S.set(f, {rot: 0});
  nearArr(S.worldMatrix(c), [1, 0, 0, 1, 120, 70]);
  S.set(c, {w: 60});
  nearRect(S.worldBounds(c), 120, 70, 60, 20);
  /* a resized turned node keeps its top-left box origin but its centre moves */
  S.set(g, {w: 80});
  nearRect(S.worldBounds(g), 110 + 10 + 40 - 10, 50 + 20 + 10 - 40, 20, 80);

  /* subtreeBounds: a clipping frame hides what sticks out, a group does not; hidden nodes do not count */
  const grp = S.create('GROUP', '0:1', {x: 1000, y: 1000, w: 10, h: 10});
  const far = S.create('RECT', grp, {x: 500, y: 0, w: 10, h: 10});
  nearRect(S.subtreeBounds(grp), 1000, 1000, 510, 10);
  nearRect(S.worldBounds(grp), 1000, 1000, 10, 10);
  S.set(far, {visible: false});
  nearRect(S.subtreeBounds(grp), 1000, 1000, 10, 10);
  S.set(far, {visible: null, x: 600});
  nearRect(S.subtreeBounds(grp), 1000, 1000, 610, 10);
  const clipF = S.create('FRAME', '0:1', {x: 2000, y: 0, w: 50, h: 50});
  S.create('RECT', clipF, {x: 400, y: 0});
  nearRect(S.subtreeBounds(clipF), 2000, 0, 50, 50);
  S.set(clipF, {clip: false});
  nearRect(S.subtreeBounds(clipF), 2000, 0, 500, 100);
  const pb = S.worldBounds('0:1');                                  /* a page = everything on it */
  assert.ok(pb.w > 2000 && pb.x <= 50 - 100 * r2 + 1e-9);
});

test('store: move() reparents keeping the world position and gives fresh idx', () => {
  const {HD} = makeEnv(), S = HD.store, M = HD.math;
  S.load(baseDoc(), 1);
  const f = S.create('FRAME', '0:1', {x: 100, y: 50, w: 200, h: 100, rot: 90});
  const h = S.create('FRAME', '0:1', {x: 700, y: 300, w: 300, h: 300, rot: -30, flipH: true});
  const c = S.create('RECT', f, {x: 10, y: 20, w: 40, h: 20, rot: 15});
  const c2 = S.create('RECT', f, {x: 60, y: 20, w: 40, h: 20});
  const x1 = S.create('RECT', h, {}), x2 = S.create('RECT', h, {});
  const wc = S.worldMatrix(c), wc2 = S.worldMatrix(c2);
  const batches = [];
  S.onOps(ops => batches.push(JSON.parse(JSON.stringify(ops))));

  S.move([c2, c], h, x2);                                         /* into a turned, mirrored frame, between x1 and x2 */
  assert.equal(batches.length, 1);                                /* one batch; parent + idx travel together */
  for (const op of batches[0]) assert.ok(op.p.parent === h && typeof op.p.idx === 'string');
  deq(S.children(h), [x1, c, c2, x2]);               /* their own order is kept */
  deq(S.children(f), []);
  nearArr(S.worldMatrix(c), wc, 1e-4);                             /* x / y / rot are stored to 6 decimals */
  nearArr(S.worldMatrix(c2), wc2, 1e-4);
  assert.equal(S.get(c).flipH, true);                             /* the mirror of the new parent is cancelled out */

  S.move([c], '0:1', null);                                       /* out to the page, on top */
  nearArr(S.worldMatrix(c), wc, 1e-4);
  assert.equal(!!S.get(c).flipH, false);
  assert.ok(near(S.get(c).rot, 105, 1e-6));
  const top = S.children('0:1');
  assert.equal(top[top.length - 1], c);
  S.undo(); S.undo();
  nearArr(S.worldMatrix(c), wc, 1e-9);
  deq(S.children(f), [c, c2]);

  /* reorder inside one parent: only idx changes */
  batches.length = 0;
  S.move([c2], f, c);
  deq(S.children(f), [c2, c]);
  deq(Object.keys(batches[0][0].p), ['idx']);
  /* never into itself or its own child; a child of a moving node just goes along */
  assert.equal(S.move([f], f, null), false);
  assert.equal(S.move([f], c, null), false);
  assert.equal(S.move(['0:0'], '0:1', null), false);
  S.move([f, c], h, null);
  assert.equal(S.parent(f), h); assert.equal(S.parent(c), f);
  /* a reparent through set() that would make a cycle is dropped, the rest of the edit is kept */
  S.set(h, {parent: c, name: 'H'});
  assert.equal(S.parent(h), '0:1'); assert.equal(S.get(h).name, 'H');
});

test('store: HD.layout.run is called inside the tx with the changed ids; its writes join the batch and the undo step', () => {
  const {HD} = makeEnv(), S = HD.store;
  S.load(baseDoc(), 1);
  const g = S.create('GROUP', '0:1', {x: 0, y: 0, w: 10, h: 10});
  const a = S.create('RECT', g, {x: 0, y: 0, w: 10, h: 10});
  const calls = [];
  HD.layout = {
    run(ids, props) {
      calls.push({ids: Array.from(ids).sort(), inTx: S.inTx(), props});
      if (ids.has(a)) S.set(g, {w: S.get(a).x + S.prop(a, 'w')});     /* "group bounds" */
    }
  };
  const batches = [];
  S.onOps(ops => batches.push(JSON.parse(JSON.stringify(ops))));
  S.set(a, {x: 30});
  assert.equal(calls.length, 1);
  assert.equal(calls[0].inTx, true);
  deq(calls[0].ids, [a]);
  assert.ok(calls[0].props.get(a).has('x'));
  deq(batches, [[{id: a, p: {x: 30}}, {id: g, p: {w: 40}}]]);
  S.undo();
  assert.equal(S.get(a).x, 0); assert.equal(S.get(g).w, 10);
  S.redo();
  assert.equal(S.get(a).x, 30); assert.equal(S.get(g).w, 40);
  S.undo();
  /* a delete tells layout about the parent that lost a child; remote ops never call layout */
  calls.length = 0;
  S.remove([a]);
  deq(calls[0].ids, [g]);
  calls.length = 0;
  S.applyRemote([{id: g, p: {x: 5}}]);
  assert.equal(calls.length, 0);
  /* a layout that throws does not lose the edit */
  HD.layout = {run() { throw new Error('layout bug'); }};
  S.set(g, {x: 9});
  assert.equal(S.get(g).x, 9);
});

/* ============================================================== sync */
test('store: applyRemote skips props with an un-acked local change, accepts them after the ack', () => {
  const {HD} = makeEnv(), S = HD.store;
  S.load(baseDoc({'5:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'R', x: 0, y: 0}}), 1);
  S.tracking(true);
  const sent = [];
  S.onOps((ops, b) => sent.push({ops, b}));
  const changes = [];
  S.on('change', c => changes.push(c));

  S.set('5:1', {x: 10});                                            /* local, un-acked */
  assert.equal(sent.length, 1);
  assert.equal(S.pendingCount(), 1);
  S.applyRemote([{id: '5:1', p: {x: 99, y: 7, name: 'Theirs'}}]);
  assert.equal(S.get('5:1').x, 10);                                 /* the same (node, prop): ignored */
  assert.equal(S.get('5:1').y, 7);                                  /* other props of the same node: applied */
  assert.equal(S.get('5:1').name, 'Theirs');
  const rc = changes[changes.length - 1];
  assert.ok(rc.remote === true && rc.ids.has('5:1') && !rc.props.get('5:1').has('x'));
  S.applyRemote([{id: '5:1', p: {x: 98}}]);
  assert.equal(S.get('5:1').x, 10);

  S.acked(sent[0].b);                                               /* our write is confirmed: ours won */
  assert.equal(S.pendingCount(), 0);
  assert.equal(S.get('5:1').x, 10);
  S.applyRemote([{id: '5:1', p: {x: 55}}]);                         /* a later remote value is now taken */
  assert.equal(S.get('5:1').x, 55);

  /* two local writes on one prop: the prop stays protected until BOTH are acked */
  S.set('5:1', {x: 1}); S.set('5:1', {x: 2});
  S.acked(sent[1].b);
  S.applyRemote([{id: '5:1', p: {x: 500}}]);
  assert.equal(S.get('5:1').x, 2);
  S.acked(sent[2].b);
  S.applyRemote([{id: '5:1', p: {x: 501}}]);
  assert.equal(S.get('5:1').x, 501);

  /* remote create / delete / unknown-id set; remote ops are not undoable and never go back out */
  const n = sent.length, undoable = S.canUndo();
  S.applyRemote([
    {id: '8:1', p: {type: 'FRAME', parent: '0:1', idx: 'a1', name: 'Theirs', x: 5}},
    {id: '8:2', p: {type: 'RECT', parent: '8:1', idx: 'a0', name: 'Kid', fills: null}},
    {id: '9:9', p: {x: 4}},                                         /* unknown id, no type: dropped */
    {id: '0:0', del: 1}                                             /* the root never goes */
  ]);
  assert.ok(S.has('8:1') && S.has('8:2') && !S.has('9:9') && S.has('0:0'));
  assert.equal('fills' in S.get('8:2'), false);
  deq(S.children('0:1'), ['5:1', '8:1']);
  HD.sel.set(['8:2']);
  S.applyRemote([{id: '8:1', del: 1}]);
  assert.ok(!S.has('8:1') && !S.has('8:2'));
  deq(HD.sel.ids.slice(), []);
  assert.equal(sent.length, n);
  assert.equal(S.canUndo(), undoable);

  /* we deleted a node (not confirmed yet): remote ops on it, and moves into it, do not bring anything back */
  S.applyRemote([{id: '8:3', p: {type: 'FRAME', parent: '0:1', idx: 'a2', name: 'F'}},
                 {id: '8:4', p: {type: 'RECT', parent: '0:1', idx: 'a3', name: 'Free'}}]);
  S.remove(['8:3']);
  S.applyRemote([{id: '8:3', p: {x: 1}}, {id: '8:4', p: {parent: '8:3', idx: 'a0'}},
                 {id: '8:5', p: {type: 'RECT', parent: '8:3', idx: 'a1', name: 'New'}}]);
  assert.ok(!S.has('8:3') && !S.has('8:4') && !S.has('8:5'));
});

test('store: rollback of rejected ops (set -> the server value, create -> gone, delete -> back)', () => {
  const {HD} = makeEnv(), S = HD.store;
  S.load(baseDoc({
    '5:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'R', x: 0},
    '5:2': {type: 'FRAME', parent: '0:1', idx: 'a1', name: 'F'},
    '5:3': {type: 'RECT', parent: '5:2', idx: 'a0', name: 'In'}
  }), 1);
  S.tracking(true);
  const sent = [];
  S.onOps((ops, b) => sent.push({ops, b}));
  const changes = [];
  S.on('change', c => changes.push(c));

  /* a rejected set goes back to the value before the edit */
  S.set('5:1', {x: 10, name: 'Mine'});
  S.rollback(sent[0].ops); S.acked(sent[0].b);
  deq([S.get('5:1').x, S.get('5:1').name], [0, 'R']);
  assert.equal(changes[changes.length - 1].remote, true);
  assert.equal(S.pendingCount(), 0);

  /* ...or to the remote value that arrived (and was skipped) while it was pending */
  S.set('5:1', {x: 20});
  S.applyRemote([{id: '5:1', p: {x: 77}}]);
  assert.equal(S.get('5:1').x, 20);
  S.rollback(sent[1].ops); S.acked(sent[1].b);
  assert.equal(S.get('5:1').x, 77);

  /* the first of two writes is rejected: the later one is still on its way and stays */
  S.set('5:1', {x: 1}); S.set('5:1', {x: 2});
  S.rollback(sent[2].ops); S.acked(sent[2].b);
  assert.equal(S.get('5:1').x, 2);
  S.rollback(sent[3].ops); S.acked(sent[3].b);
  assert.equal(S.get('5:1').x, 77);

  /* a rejected reparent goes home */
  S.move(['5:1'], '5:2', null);
  assert.equal(S.parent('5:1'), '5:2');
  S.rollback(sent[4].ops); S.acked(sent[4].b);
  assert.equal(S.parent('5:1'), '0:1');
  deq(S.children('0:1'), ['5:1', '5:2']);
  deq(S.children('5:2'), ['5:3']);

  /* a rejected create disappears; only the rejected op of a batch is rolled back */
  let made;
  S.tx('two', () => { made = S.create('RECT', '5:2', {}); S.set('5:3', {x: 4}); });
  const batch = sent[5];
  assert.equal(batch.ops.length, 2);
  S.rollback([batch.ops[0]]); S.acked(batch.b);
  assert.equal(S.has(made), false);
  assert.equal(S.get('5:3').x, 4);

  /* a rejected delete puts the subtree back */
  S.remove(['5:2']);
  assert.ok(!S.has('5:2') && !S.has('5:3'));
  S.rollback(sent[6].ops); S.acked(sent[6].b);
  assert.ok(S.has('5:2') && S.has('5:3') && S.get('5:3').x === 4);
  deq(S.children('5:2'), ['5:3']);

  /* a set that waits while somebody deletes the node: nothing to repair, both sides simply lose it */
  let desync = 0;
  S.on('desync', () => desync++);
  S.set('5:3', {x: 9});
  S.applyRemote([{id: '5:2', del: 1}]);
  assert.ok(!S.has('5:2') && !S.has('5:3'));
  S.acked(sent[7].b);                                               /* the server dropped it silently */
  deq(S.syncCheck(), []);
  assert.equal(desync, 0);

  /* both sides change the tree at once: we move A into B (waiting), they move B into A. The server took theirs
     first, so ours can not happen: the screen shows the server's tree at once, never a loop */
  S.applyRemote([{id: '6:1', p: {type: 'FRAME', parent: '0:1', idx: 'b0', name: 'A'}},
                 {id: '6:2', p: {type: 'FRAME', parent: '0:1', idx: 'b1', name: 'B'}}]);
  S.move(['6:1'], '6:2', null);
  assert.equal(S.parent('6:1'), '6:2');
  S.applyRemote([{id: '6:2', p: {parent: '6:1', idx: 'a0'}}]);
  assert.equal(S.parent('6:2'), '6:1');
  assert.equal(S.parent('6:1'), '0:1');
  deq(S.syncCheck(), []);
  S.rollback(sent[8].ops);                                          /* and the server indeed says no */
  assert.equal(S.parent('6:1'), '0:1');
  assert.equal(S.pendingCount(), 0);
  assert.equal(desync, 0);
  deq(JSON.parse(JSON.stringify(S.serverDoc())), JSON.parse(JSON.stringify(S.toDoc())));   /* nothing waits: screen = server */

  /* an op the server's own rules refuse can not have come from it: the store says it lost track (net reloads) */
  S.applyRemote([{id: '6:1', p: {parent: '6:2', idx: 'a0'}}]);     /* a loop */
  assert.equal(desync, 1);
  assert.equal(S.parent('6:1'), '0:1');
  S.applyRemote([{id: '7:1', p: {type: 'RECT', parent: 'no:such', idx: 'a0', name: 'orphan'}}]);
  assert.equal(desync, 2);
  assert.equal(S.has('7:1'), false);
});

test('store: load(doc, cid, {keep:true}) puts pending batches back on a fresh document and keeps undo', () => {
  const {HD} = makeEnv(), S = HD.store;
  const doc = () => baseDoc({
    '5:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'R', x: 0},
    '5:2': {type: 'RECT', parent: '0:1', idx: 'a1', name: 'Gone soon'}
  });
  S.load(doc(), 1);
  S.tracking(true);
  const sent = [];
  S.onOps((ops, b) => sent.push({ops, b}));
  S.set('5:1', {x: 10});
  const made = S.create('ELLIPSE', '0:1', {x: 3});
  S.set('5:2', {x: 8});
  assert.equal(made, '1:1');

  const fresh = doc();
  delete fresh.nodes['5:2'];                                        /* somebody deleted it meanwhile */
  fresh.nodes['5:1'].name = 'Renamed';
  fresh.nodes['1:1'] = {type: 'ELLIPSE', parent: '0:1', idx: 'a2', name: 'Ellipse 1', x: 3};   /* ours did arrive */
  S.load(fresh, 4, {keep: true});
  assert.equal(S.get('5:1').x, 10);                                 /* pending edit is back on top */
  assert.equal(S.get('5:1').name, 'Renamed');
  assert.ok(S.has(made));
  assert.equal(S.has('5:2'), false);                                /* the edit on a deleted node is dropped */
  assert.equal(S.pendingCount(), 3);
  S.applyRemote([{id: '5:1', p: {x: 99}}]);
  assert.equal(S.get('5:1').x, 10);                                 /* still protected */
  S.rollback([sent[2].ops[0]]);                                     /* the server rejects / ignores the dead one */
  for (const s of sent) S.acked(s.b);
  assert.equal(S.pendingCount(), 0);
  assert.equal(S.newId(), '4:1');                                   /* ids now use the new client number */
  assert.ok(S.canUndo());
  S.undo();                                                         /* undo history survived (its dead step is harmless) */
  S.undo();
  assert.equal(S.has(made), false);
  S.load(doc(), 9);                                                 /* a plain load forgets undo and pending */
  assert.ok(!S.canUndo() && S.pendingCount() === 0);
  /* new ids never collide with ids already in the document */
  S.load(baseDoc({'9:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'x'}, '9:7': {type: 'RECT', parent: '0:1', idx: 'a1', name: 'y'}}), 9);
  assert.equal(S.create('RECT', '0:1', {}), '9:8');
  assert.equal(S.get('9:8').name, 'Rectangle 1');
});

test('sel: set / add / toggle / clear / has / page', () => {
  const {HD} = makeEnv(), S = HD.store, L = HD.sel;
  S.load(baseDoc({'0:2': {type: 'PAGE', parent: '0:0', idx: 'a1', name: 'Page 2'}}), 1);
  const a = S.create('RECT', '0:1', {}), b = S.create('RECT', '0:1', {});
  const ev = [];
  L.on('change', e => ev.push(e));
  L.set([a, a, 'nope', b]);
  deq(L.ids.slice(), [a, b]);
  assert.ok(L.has(a) && !L.has('nope'));
  assert.equal(ev.length, 1);
  L.set([a, b]);
  assert.equal(ev.length, 1);                                       /* the same selection: no event */
  L.toggle(a); deq(L.ids.slice(), [b]);
  L.toggle(a); deq(L.ids.slice(), [b, a]);
  L.add(a); assert.equal(ev.length, 3);
  L.clear(); deq(L.ids.slice(), []);
  assert.throws(() => { 'use strict'; L.ids.push('x'); });           /* never changed from outside */
  L.set([a]);
  assert.equal(L.setPage('0:2'), true);
  assert.equal(L.page, '0:2'); deq(L.ids.slice(), []);
  assert.equal(L.setPage(a), false);
  S.remove(['0:2']);                                                /* the current page is deleted: fall back */
  assert.equal(L.page, '0:1');
});

/* ============================================================== convergence
 * Three editors and a server that follows the contract (ops applied in arrival order, last writer wins per
 * property, reject: unknown type / missing parent / cycle / root). Random edits, undo, delays, messages
 * crossing each other. When everything has been delivered every editor must hold EXACTLY the server's document. */
function makeServer(doc) {
  const nodes = new Map(Object.entries(JSON.parse(JSON.stringify(doc.nodes))));
  const TYPES = new Set(['DOCUMENT', 'PAGE', 'FRAME', 'GROUP', 'SECTION', 'RECT', 'ELLIPSE', 'LINE', 'POLYGON', 'STAR', 'VECTOR', 'TEXT', 'COMPONENT', 'COMPONENT_SET', 'INSTANCE']);
  const under = (a, b) => { let c = b; while (c !== undefined) { if (c === a) return true; c = nodes.get(c) ? nodes.get(c).parent : undefined; } return false; };
  function del(id) { for (const [k, n] of Array.from(nodes)) if (n.parent === id) del(k); nodes.delete(id); }
  return {
    nodes,
    doc() { return {nodes: JSON.parse(JSON.stringify(Object.fromEntries(nodes)))}; },
    apply(ops) {
      const ok = [], rejected = [];
      ops.forEach((op, i) => {
        if (op.del) { if (op.id === '0:0') return rejected.push(i); if (nodes.has(op.id)) { del(op.id); ok.push(op); } return; }
        const n = nodes.get(op.id), p = op.p;
        if (p.type !== undefined && p.type !== null && !TYPES.has(p.type)) return rejected.push(i);
        if (n) {
          if ('parent' in p && p.parent !== n.parent) {
            if (op.id === '0:0' || !nodes.has(p.parent) || under(op.id, p.parent)) return rejected.push(i);
          }
          for (const k in p) { if (p[k] === null) delete n[k]; else n[k] = p[k]; }
          ok.push(op);
        } else if (p.type !== undefined) {
          if (!nodes.has(p.parent)) return rejected.push(i);
          const o = {}; for (const k in p) if (p[k] !== null) o[k] = p[k];
          nodes.set(op.id, o); ok.push(op);
        }                                                           /* unknown id without a type: dropped */
      });
      return {ok, rejected};
    }
  };
}
function canon(v) {
  if (Array.isArray(v)) return v.map(canon);
  if (v && typeof v === 'object') { const o = {}; for (const k of Object.keys(v).sort()) o[k] = canon(v[k]); return o; }
  return v;
}

const CHECK_EVERY = +process.env.HD_CHECK || 1;                    /* a long soak: HD_SEEDS=3000 HD_CHECK=40 */
const EDIT = +process.env.HD_EDIT || 0.4;                          /* share of steps that are edits: lower = a faster network */
const TRACE = process.env.HD_TRACE || '';                          /* HD_SEED=2 HD_TRACE=11:15 node design_core_test.js */
function converge(seed, steps, drops) {
  const rnd = rng(seed), pick = a => a[Math.floor(rnd() * a.length)];
  const tr = (who, what, ops) => {
    if (!TRACE) return;
    const hit = ops.filter(o => TRACE === '*' || JSON.stringify(o).includes('"' + TRACE + '"'));
    if (hit.length) console.log('    ' + who + ' ' + what + ' ' + JSON.stringify(hit));
  };
  const server = makeServer(baseDoc({'0:9': {type: 'FRAME', parent: '0:1', idx: 'a0', name: 'Shared', x: 0, y: 0, w: 500, h: 500}}));
  const DUMP = process.env.HD_DUMP || '';                           /* every batch the server saw + its verdict, for the Python replay */
  const dump = DUMP ? {start: server.doc(), batches: []} : null;
  const stats = {edits: 0, rejected: 0, reloads: 0, repairs: 0};
  const clients = [11, 12, 13].map(cid => {
    const env = makeEnv(), S = env.HD.store;
    const c = {cid, S, HD: env.HD, up: [], down: [], unacked: [], desync: false};
    S.tracking(true);
    S.onOps((ops, b) => { const m = {ops: JSON.parse(JSON.stringify(ops)), real: ops, b}; c.unacked.push(m); c.up.push(m); tr(cid, 'local b' + b, m.ops); });
    S.on('desync', () => { c.desync = true; if (TRACE) console.log('    ' + cid + ' DESYNC'); });
    S.load(server.doc(), cid);
    return c;
  });
  const containers = S => { const out = []; S.walk('0:1', (id, n) => { if (n.type === 'PAGE' || n.type === 'FRAME' || n.type === 'GROUP') out.push(id); }); return out; };
  const layers = S => { const out = []; S.walk('0:1', (id, n) => { if (n.type !== 'PAGE') out.push(id); }); return out; };

  function edit(c) {
    const S = c.S, r = rnd(), ls = layers(S);
    stats.edits++;
    if (r < 0.22 || !ls.length) S.create(pick(['RECT', 'FRAME', 'GROUP', 'TEXT']), pick(containers(S)), {x: Math.floor(rnd() * 400), y: Math.floor(rnd() * 400)});
    else if (r < 0.55) S.set(pick(ls), pick([{x: Math.floor(rnd() * 900)}, {name: 'n' + Math.floor(rnd() * 50)}, {fills: [{type: 'solid', color: '#' + Math.floor(rnd() * 9) + '00000'}]}, {rot: Math.floor(rnd() * 360), y: 3}, {fills: null}, {opacity: rnd()}]));
    else if (r < 0.75) { const kids = S.children(pick(containers(S))); S.move([pick(ls)], pick(containers(S)), rnd() < 0.5 && kids.length ? pick(kids) : null); }
    else if (r < 0.85) S.remove([pick(ls)]);
    else if (r < 0.93) S.undo();
    else if (r < 0.97) S.redo();
    else S.tx('multi', () => { const a = S.create('FRAME', pick(containers(S)), {}); S.create('RECT', a, {x: 1}); const l = pick(ls); if (S.has(l)) S.set(l, {x: 7, name: 'multi'}); });
  }
  function toServer(c) {
    const m = c.up.shift();
    const res = server.apply(m.ops);
    if (dump) dump.batches.push({ops: m.ops, rejected: res.rejected});
    tr(c.cid, '-> server b' + m.b + ' rejected=' + JSON.stringify(res.rejected), m.ops);
    stats.rejected += res.rejected.length;
    c.down.push({t: 'ack', b: m.b, rejected: res.rejected});
    if (res.ok.length) for (const o of clients) if (o !== c) o.down.push({t: 'ops', ops: JSON.parse(JSON.stringify(res.ok))});
  }
  function toClient(c) {
    const m = c.down.shift();
    if (m.t === 'ops') {
      tr(c.cid, 'remote', m.ops);
      c.S.applyRemote(m.ops);
    }
    else {
      if (TRACE) console.log('    ' + c.cid + ' ack b' + m.b + ' ' + JSON.stringify(m.rejected));
      const i = c.unacked.findIndex(u => u.b === m.b);
      if (i < 0) return;
      const u = c.unacked.splice(i, 1)[0];
      if (m.rejected.length) c.S.rollback(m.rejected.map(k => u.real[k]));
      c.S.acked(u.b);
    }
    if (c.desync) { stats.repairs++; reload(c); }
  }
  function reload(c) {                                              /* what HD.net does: new socket, fresh doc, pending again */
    c.desync = false; stats.reloads++;
    if (TRACE) console.log('    ' + c.cid + ' RELOAD has=' + server.nodes.has(TRACE));
    c.up = []; c.down = [];
    c.S.load(server.doc(), c.cid, {keep: true});
    for (const u of c.unacked) c.up.push(u);
  }
  const WATCH = process.env.HD_WATCH || '', seen = new Map();        /* HD_WATCH=11:13 prints when a node appears / goes */
  let tick = 0;
  const watch = () => {
    if (++tick % CHECK_EVERY === 0) for (const c of clients) {       /* THE invariant, after every single step */
      const off = c.S.syncCheck();
      if (off.length) assert.fail('seed ' + seed + ': client ' + c.cid + ' screen is not server copy + waiting ops at ' + JSON.stringify(c.S.syncCheck(true).slice(0, 3)));
    }
    if (!WATCH) return;
    for (const c of clients.concat([{cid: 'server', S: {has: id => server.nodes.has(id)}}])) {
      const h = c.S.has(WATCH);
      if (seen.get(c.cid) !== h) { seen.set(c.cid, h); console.log('    ' + c.cid + ' WATCH ' + WATCH + ' -> ' + h); }
    }
  };
  for (let i = 0; i < steps; i++) {
    watch();
    const c = pick(clients), r = rnd();
    if (r < EDIT) edit(c);
    else if (r < EDIT + (1 - EDIT) / 2) { if (c.up.length) toServer(c); }
    else if (r < 1 - drops) { if (c.down.length) toClient(c); }
    else reload(c);                                                 /* a dropped connection now and then */
    if (c.desync) { stats.repairs++; reload(c); }
  }
  for (let guard = 0; guard < 100000; guard++) {
    watch();
    const busy = clients.filter(c => c.up.length || c.down.length);
    if (!busy.length) break;
    const c = pick(busy);
    if (c.up.length && (rnd() < 0.5 || !c.down.length)) toServer(c); else toClient(c);
    if (c.desync) { stats.repairs++; reload(c); }
  }
  const want = canon(server.doc());
  for (const c of clients) {
    assert.equal(c.S.pendingCount(), 0, 'seed ' + seed + ': client ' + c.cid + ' still has pending batches');
    assert.deepStrictEqual(canon(JSON.parse(JSON.stringify(c.S.serverDoc()))), want, 'seed ' + seed + ': client ' + c.cid + ' has a wrong copy of the server');
    assert.deepStrictEqual(canon(JSON.parse(JSON.stringify(c.S.toDoc()))), want, 'seed ' + seed + ': client ' + c.cid + ' differs from the server');
    /* and the tree is sound: every child list matches the parent pointers, no cycles */
    let seen = 0;
    c.S.walk('0:0', () => { seen++; });
    assert.equal(seen, c.S.count(), 'seed ' + seed + ': client ' + c.cid + ' has unreachable nodes');
  }
  stats.nodes = server.nodes.size;
  if (dump) { dump.end = server.doc(); fs.writeFileSync(DUMP, JSON.stringify(dump)); }
  return stats;
}

test('sync: three editors with crossing messages, rejects, undo and dropped connections always converge', () => {
  const total = {edits: 0, rejected: 0, reloads: 0, repairs: 0, nodes: 0};
  const only = +process.env.HD_SEED || 0, runs = +process.env.HD_SEEDS || 40;      /* HD_SEEDS=2000 for a long soak */
  for (let seed = only || 1; seed <= (only || runs); seed++) {
    const s = converge(seed, 1500, seed % 2 ? 0.015 : 0);          /* every other run: no dropped connections at all */
    for (const k in total) total[k] += s[k];
  }
  console.log('  sync: ' + (only ? 1 : runs) + ' runs x 1,500 steps, ' + total.edits + ' edits, ' + total.rejected + ' ops rejected by the server, ' +
    total.reloads + ' dropped connections, the store lost track ' + total.repairs + ' times, all editors equal to the server');
  assert.ok(total.rejected > 0, 'the run should include rejected ops');
  assert.equal(total.repairs, 0, 'the store never loses track of the server');
});

/* ============================================================== HD.net */
function initFrame(extra, cid) {
  return {
    t: 'init', cid: cid || 3, seq: 10, doc: baseDoc(extra), file: {id: 'F1', name: 'My file', role: 'edit'},
    users: [{cid: cid || 3, name: 'Me', color: '#111111'}, {cid: 8, name: 'Asha', color: '#FF8800'}]
  };
}
function connected(opts) {
  const env = makeEnv(opts), N = env.HD.net;
  const statuses = [];
  N.on('status', s => statuses.push(s));
  N.connect('F1');
  const ws = env.last();
  ws.open();
  ws.recv(initFrame({'5:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'R', x: 0}}));
  return Object.assign(env, {N, ws, statuses});
}

test('net: connects with the token as a subprotocol (never in the URL), init loads the store', () => {
  const env = makeEnv({https: true}), N = env.HD.net, S = env.HD.store;
  const statuses = [], inits = [];
  N.on('status', s => statuses.push(s));
  N.on('init', i => inits.push(i));
  N.connect('F 1/x');
  const ws = env.last();
  assert.equal(ws.url, 'wss://hoola.test:8077/api/design/ws?file=F%201%2Fx');
  deq(Array.from(ws.protocols), ['hoola', 'hoola-key.tok_ABC123']);
  assert.ok(!ws.url.includes('tok_'));
  assert.equal(N.status, 'connecting');
  ws.open();
  ws.recv(initFrame({'5:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'R'}}));
  assert.equal(N.status, 'live');
  deq(statuses, ['connecting', 'live']);
  assert.ok(S.has('5:1'));
  assert.equal(S.newId(), '3:1');
  assert.equal(N.cid, 3); assert.equal(N.role, 'edit'); assert.equal(N.seq, 10);
  deq(JSON.parse(JSON.stringify(N.file)), {id: 'F1', name: 'My file', role: 'edit'});
  assert.equal(N.users.size, 1);                                    /* other people only */
  assert.equal(N.users.get(8).name, 'Asha');
  assert.equal(inits.length, 1); assert.equal(inits[0].reconnect, false);
  assert.equal(S.tracking(), true);
  N.close();
  assert.equal(N.status, 'offline');
  assert.equal(ws.closedBy, 'client');
  assert.equal(S.tracking(), false);

  /* no token: no socket at all, a clear status */
  const e2 = makeEnv({noToken: true});
  e2.HD.net.connect('F1');
  assert.equal(e2.sockets.length, 0);
  assert.equal(e2.HD.net.status, 'auth');
});

test('net: local batches go out with rising n, at most one frame per animation frame; ack releases them', () => {
  const {HD, N, ws, clock} = connected(), S = HD.store;
  const pend = [];
  N.on('pending', n => pend.push(n));
  S.set('5:1', {x: 1});
  S.set('5:1', {x: 2});
  const made = S.create('RECT', '0:1', {});
  assert.equal(ws.frames('ops').length, 0);                         /* nothing yet: waiting for the frame */
  assert.equal(N.pending(), 3);
  clock.advance(16);
  let frames = ws.frames('ops');
  assert.equal(frames.length, 1);                                   /* three store batches, ONE wire frame */
  assert.equal(frames[0].n, 1);
  deq(frames[0].ops.map(o => o.id), ['5:1', '5:1', made]);
  assert.equal(S.pendingCount(), 3);
  S.set('5:1', {y: 5});
  clock.advance(16);
  frames = ws.frames('ops');
  assert.equal(frames.length, 2);
  assert.equal(frames[1].n, 2);

  ws.recv({t: 'ops', seq: 11, by: 8, ops: [{id: '5:1', p: {x: 50, name: 'Asha was here'}}]});
  assert.equal(S.get('5:1').x, 2);                                  /* ours is un-acked: theirs is skipped */
  assert.equal(S.get('5:1').name, 'Asha was here');
  ws.recv({t: 'ack', n: 1, seq: 12, rejected: []});
  assert.equal(S.pendingCount(), 1);
  assert.equal(N.seq, 12);
  ws.recv({t: 'ack', n: 2, seq: 13, rejected: []});
  assert.equal(S.pendingCount(), 0);
  assert.equal(N.pending(), 0);
  deq(pend, [1, 0]);                                                /* told when it starts and when all is saved */
  ws.recv({t: 'ops', seq: 14, by: 8, ops: [{id: '5:1', p: {x: 60}}]});
  assert.equal(S.get('5:1').x, 60);                                 /* after the ack remote values are taken again */

  /* a busy socket: wait and keep coalescing */
  ws.bufferedAmount = 5 * 1024 * 1024;
  S.set('5:1', {x: 61});
  clock.advance(100);
  S.set('5:1', {x: 62});
  clock.advance(100);
  assert.equal(ws.frames('ops').length, 2);
  ws.bufferedAmount = 0;
  clock.advance(100);
  frames = ws.frames('ops');
  assert.equal(frames.length, 3);
  assert.equal(frames[2].n, 3);
  assert.equal(frames[2].ops.length, 2);

  /* big work is cut into frames of at most 1,000 ops, one per animation frame, in order */
  ws.recv({t: 'ack', n: 3, seq: 15, rejected: []});
  S.tx('many', () => { for (let i = 0; i < 2500; i++) S.create('RECT', '0:1', {x: i}); });
  clock.advance(16);
  assert.equal(ws.frames('ops').length, 4);
  clock.advance(16); clock.advance(16);
  frames = ws.frames('ops');
  deq(frames.slice(3).map(f => f.ops.length), [1000, 1000, 500]);
  deq(frames.slice(3).map(f => f.n), [4, 5, 6]);
  assert.equal(S.pendingCount(), 1);                                /* one store batch over three frames */
  ws.recv({t: 'ack', n: 4, seq: 16, rejected: []});
  ws.recv({t: 'ack', n: 5, seq: 17, rejected: []});
  assert.equal(S.pendingCount(), 1);                                /* ...released only when all of it is answered */
  ws.recv({t: 'ack', n: 6, seq: 18, rejected: []});
  assert.equal(S.pendingCount(), 0);
});

test('net: rejected ops are rolled back in the store', () => {
  const {HD, N, ws, clock} = connected(), S = HD.store;
  const rejects = [];
  N.on('reject', r => rejects.push(r));
  let made;
  S.tx('t', () => { S.set('5:1', {x: 44}); made = S.create('RECT', '0:1', {}); });
  S.set('5:1', {name: 'Kept'});
  clock.advance(16);
  const f = ws.frames('ops')[0];
  assert.equal(f.ops.length, 3);
  ws.recv({t: 'ack', n: f.n, seq: 11, rejected: [0, 1]});
  assert.equal(S.get('5:1').x, 0);                                  /* rolled back */
  assert.equal(S.has(made), false);                                 /* rejected create is gone */
  assert.equal(S.get('5:1').name, 'Kept');                          /* the accepted op stays */
  assert.equal(S.pendingCount(), 0);
  assert.equal(rejects.length, 1); assert.equal(rejects[0].ops.length, 2);
});

test('net: lost connection -> backoff 0.5..8 s -> fresh init, pending edits put back and sent again', () => {
  const env = connected(), {HD, N, clock, statuses} = env, S = HD.store;
  let ws = env.ws;
  const inits = [];
  N.on('init', i => inits.push(i));
  S.set('5:1', {x: 5});
  clock.advance(16);
  assert.equal(ws.frames('ops').length, 1);                         /* sent, no ack yet */
  S.set('5:1', {y: 6});                                             /* not sent yet */
  ws.drop(1006);
  assert.equal(N.status, 'offline');
  assert.equal(N.users.size, 0);
  const made = S.create('RECT', '0:1', {});                         /* an offline edit keeps queuing */
  assert.equal(N.pending(), 3);

  /* retries: 0.5, 1, 2, 4, 8, 8 seconds */
  const gaps = [];
  let lastAt = clock.now(), count = env.sockets.length;
  for (let i = 0; i < 6; i++) {
    for (let ms = 0; ms < 20000 && env.sockets.length === count; ms += 100) clock.advance(100);
    assert.ok(env.sockets.length > count, 'retry ' + i);
    gaps.push((clock.now() - lastAt) / 1000);
    lastAt = clock.now(); count = env.sockets.length;
    if (i < 5) env.last().drop(1006);                               /* fails again */
  }
  deq(gaps, [0.5, 1, 2, 4, 8, 8]);

  ws = env.last();
  ws.open();
  const fresh = initFrame({'5:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'Server name', x: 0}}, 9);
  fresh.seq = 40;
  ws.recv(fresh);
  assert.equal(N.status, 'live');
  assert.equal(inits[inits.length - 1].reconnect, true);
  deq([S.get('5:1').x, S.get('5:1').y, S.get('5:1').name], [5, 6, 'Server name']);   /* fresh doc + our pending edits */
  assert.ok(S.has(made));
  assert.ok(S.canUndo());
  clock.advance(16);
  const frames = ws.frames('ops');
  assert.equal(frames.length, 1);                                   /* everything un-acked again, in order, a new n */
  deq(frames[0].ops.map(o => [o.id, Object.keys(o.p)[0]]), [['5:1', 'x'], ['5:1', 'y'], [made, 'type']]);
  assert.equal(frames[0].n, 2);
  ws.recv({t: 'ack', n: 2, seq: 41, rejected: []});
  assert.equal(S.pendingCount(), 0); assert.equal(N.pending(), 0);
  assert.equal(statuses[statuses.length - 1], 'live');
  /* the backoff starts again from 0.5 s after a good init */
  ws.drop(1006);
  const c2 = env.sockets.length;
  clock.advance(499); assert.equal(env.sockets.length, c2);
  clock.advance(1); assert.equal(env.sockets.length, c2 + 1);
});

test('net: presence is throttled to 30/s, users join / move / leave', () => {
  const {HD, N, ws, clock} = connected();
  const ev = [];
  N.on('presence', e => ev.push(e.type + ':' + e.cid));
  for (let i = 0; i < 100; i++) { N.sendPresence({x: i, y: i * 2, page: '0:1', sel: [], vp: [0, 0, 1]}); clock.advance(10); }
  clock.advance(100);
  const pres = ws.frames('pres');
  assert.ok(pres.length <= 31, 'frames in one second: ' + pres.length);
  assert.ok(pres.length >= 25, 'frames in one second: ' + pres.length);
  deq(pres[pres.length - 1], {t: 'pres', x: 99, y: 198, page: '0:1', sel: [], vp: [0, 0, 1]});   /* the newest is never lost */
  deq(pres[0], {t: 'pres', x: 0, y: 0, page: '0:1', sel: [], vp: [0, 0, 1]});

  ws.recv({t: 'join', user: {cid: 12, name: 'Ravi', color: '#00AA88'}});
  ws.recv({t: 'pres', cid: 12, x: 5, y: 6, page: '0:1', sel: ['5:1'], vp: [1, 2, 3]});
  deq(JSON.parse(JSON.stringify(N.users.get(12))), {cid: 12, name: 'Ravi', color: '#00AA88', x: 5, y: 6, page: '0:1', sel: ['5:1'], vp: [1, 2, 3]});
  ws.recv({t: 'pres', cid: 3, x: 1, y: 1});                         /* an echo of ourselves is ignored */
  assert.equal(N.users.has(3), false);
  ws.recv({t: 'leave', cid: 12});
  assert.equal(N.users.has(12), false);
  deq(ev, ['join:12', 'pres:12', 'leave:12']);
  assert.equal(N.users.size, 1);
});

test('net: ping every 15 s, 30 s of silence = lost; file / comment / reload frames; fatal close codes', () => {
  const env = connected(), {HD, N, clock} = env, S = HD.store;
  let ws = env.ws;
  clock.advance(15000);
  assert.equal(ws.frames('ping').length, 1);
  ws.recv({t: 'pong'});
  clock.advance(15000);
  assert.equal(ws.frames('ping').length, 2);
  assert.equal(N.status, 'live');
  ws.recv({t: 'ping'});
  assert.equal(ws.frames('pong').length, 1);
  clock.advance(30000);                                             /* silence */
  assert.equal(N.status, 'offline');
  assert.equal(ws.closedBy, 'client');
  clock.advance(500);
  ws = env.last();
  assert.notEqual(ws, env.ws);
  ws.open(); ws.recv(initFrame({}));
  assert.equal(N.status, 'live');

  const got = [];
  N.on('file', f => got.push('file:' + f.name));
  N.on('comment', c => got.push('comment:' + c.id));
  ws.recv({t: 'file', name: 'Renamed'});
  ws.recv({t: 'comment', id: 'c1', text: 'hi'});
  deq(got, ['file:Renamed', 'comment:c1']);
  assert.equal(N.file.name, 'Renamed');

  /* reload: the document was replaced -> a fresh socket, undo and waiting edits dropped */
  const a = S.create('RECT', '0:1', {});
  assert.ok(S.canUndo());
  ws.recv({t: 'reload'});
  clock.advance(1);
  const ws2 = env.last();
  assert.notEqual(ws2, ws);
  ws2.open(); ws2.recv(initFrame({'7:7': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'Restored'}}));
  assert.ok(S.has('7:7') && !S.has(a) && !S.canUndo());
  clock.advance(100);
  assert.equal(ws2.frames('ops').length, 0);
  assert.equal(S.pendingCount(), 0);

  /* 4401 / 4403 / 4404: no retry, a clear status */
  for (const [code, status] of [[4401, 'auth'], [4403, 'forbidden'], [4404, 'notfound']]) {
    const e = connected(), count = e.sockets.length;
    e.ws.drop(code);
    assert.equal(e.N.status, status);
    e.clock.advance(60000);
    assert.equal(e.sockets.length, count, 'no retry after ' + code);
    assert.equal(e.HD.store.readOnly, true);
  }
});

test('net: a view-only file never sends; offline edits stop at 5,000 queued ops', () => {
  const env = makeEnv(), N = env.HD.net, S = env.HD.store;
  N.connect('F1');
  let ws = env.last();
  ws.open();
  const fr = initFrame({'5:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'R'}});
  fr.file.role = 'view';
  ws.recv(fr);
  assert.equal(N.role, 'view');
  assert.equal(S.readOnly, true);
  assert.equal(S.set('5:1', {x: 5}), false);                        /* edits are simply ignored */
  assert.equal(S.create('RECT', '0:1', {}), undefined);
  assert.equal(S.get('5:1').x, undefined);
  env.clock.advance(100);
  assert.equal(ws.frames('ops').length, 0);
  ws.recv({t: 'ops', seq: 11, by: 8, ops: [{id: '5:1', p: {x: 9}}]});
  assert.equal(S.get('5:1').x, 9);                                  /* a viewer still sees the others */

  const e = connected(), statuses = e.statuses;
  e.ws.drop(1006);
  for (let i = 0; i < 4999; i++) e.HD.store.set('5:1', {x: i + 1});
  assert.equal(e.N.status, 'offline');
  e.HD.store.set('5:1', {x: -1});
  assert.equal(e.N.status, 'offline-full');
  assert.equal(e.HD.store.readOnly, true);
  assert.equal(e.HD.store.set('5:1', {x: -2}), false);              /* the UI is told; nothing more queues */
  assert.equal(e.N.pending(), 5000);
  e.clock.advance(500);
  ws = e.last();
  ws.open(); ws.recv(initFrame({'5:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'R', x: 0}}));
  assert.equal(e.N.status, 'live');
  assert.equal(e.HD.store.readOnly, false);
  assert.equal(e.HD.store.get('5:1').x, -1);
  for (let i = 0; i < 6; i++) e.clock.advance(16);
  assert.equal(ws.frames('ops').reduce((n, f) => n + f.ops.length, 0), 5000);
  assert.ok(statuses.includes('offline-full'));
});

test('net: both sides move at once; a lost store reloads the room (never a storm); an op too big to send', () => {
  const env = connected(), {HD, N, clock} = env, S = HD.store;
  const ws = env.ws;
  ws.recv({t: 'ops', seq: 11, by: 8, ops: [
    {id: '8:1', p: {type: 'FRAME', parent: '0:1', idx: 'b1', name: 'A'}},
    {id: '8:2', p: {type: 'FRAME', parent: '0:1', idx: 'b2', name: 'B'}}]});
  S.move(['8:1'], '8:2', null);                                     /* ours: A into B (not acked) */
  clock.advance(16);
  ws.recv({t: 'ops', seq: 12, by: 8, ops: [{id: '8:2', p: {parent: '8:1', idx: 'a1'}}]});   /* theirs: B into A, taken first */
  assert.equal(S.parent('8:2'), '8:1');                             /* the server's tree, at once, without a reload */
  assert.equal(S.parent('8:1'), '0:1');
  assert.equal(N.status, 'live');
  assert.equal(env.sockets.length, 1);
  const f = ws.frames('ops')[0];
  ws.recv({t: 'ack', n: f.n, seq: 13, rejected: [0]});              /* and the server says no to ours */
  assert.equal(S.pendingCount(), 0);
  assert.equal(S.parent('8:1'), '0:1');
  deq(S.syncCheck(), []);

  /* the store lost track of the server (an op its rules refuse) -> a fresh socket, waiting edits kept */
  S.set('8:1', {name: 'Mine'});
  ws.recv({t: 'ops', seq: 14, by: 8, ops: [{id: '9:9', p: {type: 'RECT', parent: 'no:such', idx: 'a0', name: 'x'}}]});
  assert.equal(N.status, 'connecting');
  clock.advance(1);
  const ws2 = env.last();
  assert.notEqual(ws2, ws);
  ws2.open();
  ws2.recv({t: 'init', cid: 9, seq: 15, file: {id: 'F1', name: 'My file', role: 'edit'}, users: [], doc: baseDoc({
    '5:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'R', x: 0},
    '8:1': {type: 'FRAME', parent: '0:1', idx: 'b1', name: 'A'},
    '8:2': {type: 'FRAME', parent: '8:1', idx: 'a1', name: 'B'}})});
  assert.equal(N.status, 'live');
  assert.equal(S.get('8:1').name, 'Mine');                          /* the waiting edit is back on top */
  clock.advance(16);
  const f2 = ws2.frames('ops')[0];
  deq(f2.ops, [{id: '8:1', p: {name: 'Mine'}}]);
  ws2.recv({t: 'ack', n: f2.n, seq: 16, rejected: []});
  assert.equal(S.pendingCount(), 0);

  /* a second reload right away waits for its turn (2 s), it is not dropped */
  const count = env.sockets.length;
  N.resync(false);
  clock.advance(500);
  assert.equal(env.sockets.length, count);
  clock.advance(2000);
  assert.equal(env.sockets.length, count + 1);
  const ws3 = env.last();
  ws3.open(); ws3.recv(initFrame({'5:1': {type: 'RECT', parent: '0:1', idx: 'a0', name: 'R'}}));

  /* one op over 2 MB never goes out (it would only be refused): rolled back here, the rest is sent */
  const rejects = [];
  N.on('reject', r => rejects.push(r));
  S.set('5:1', {name: 'ok'});
  S.set('5:1', {path: 'M'.repeat(2200000)});
  S.set('5:1', {x: 3});
  clock.advance(16);
  const fr = ws3.frames('ops');
  assert.equal(fr.length, 1);
  deq(fr[0].ops, [{id: '5:1', p: {name: 'ok'}}, {id: '5:1', p: {x: 3}}]);
  assert.equal(S.get('5:1').path, undefined);
  assert.equal(rejects.length, 1); assert.equal(rejects[0].tooBig, true);
  ws3.recv({t: 'ack', n: fr[0].n, seq: 20, rejected: []});
  assert.equal(S.pendingCount(), 0);
  deq(S.syncCheck(), []);
});

/* ============================================================== speed */
test('perf: 50,000 nodes load < 1 s; 1,000 sets in one tx < 50 ms', () => {
  const {HD} = makeEnv(), S = HD.store, F = HD.frac;
  /* 50,000 nodes: 500 frames x 99 children on one page */
  const nodes = {'0:0': {type: 'DOCUMENT', name: 'Document'}, '0:1': {type: 'PAGE', parent: '0:0', idx: 'a0', name: 'Page 1'}};
  const fk = F.nBetween(null, null, 500), ck = F.nBetween(null, null, 99);
  let count = 2;
  for (let i = 0; i < 500; i++) {
    const fid = '1:' + (i * 100 + 1);
    nodes[fid] = {type: 'FRAME', parent: '0:1', idx: fk[i], name: 'Frame ' + i, x: (i % 25) * 400, y: Math.floor(i / 25) * 400, w: 360, h: 360, rot: i % 7 === 0 ? 15 : 0};
    count++;
    for (let j = 0; j < 99; j++) {
      nodes['1:' + (i * 100 + 2 + j)] = {type: j % 5 === 0 ? 'TEXT' : 'RECT', parent: fid, idx: ck[j], name: 'Layer ' + j, x: (j % 10) * 36, y: Math.floor(j / 10) * 36, w: 30, h: 30, fills: [{type: 'solid', color: '#3366FF'}]};
      count++;
    }
  }
  assert.ok(count >= 50000, 'nodes: ' + count);
  const json = JSON.stringify({nodes});
  const doc = JSON.parse(json);
  let t0 = process.hrtime.bigint();
  S.load(doc, 2);
  const loadMs = Number(process.hrtime.bigint() - t0) / 1e6;
  assert.equal(S.count(), count);

  t0 = process.hrtime.bigint();
  let seen = 0;
  S.walk('0:0', () => { seen++; });
  const walkMs = Number(process.hrtime.bigint() - t0) / 1e6;
  assert.equal(seen, count);

  t0 = process.hrtime.bigint();
  const frames = S.children('0:1');
  for (let i = 0; i < frames.length; i++) { const ks = S.children(frames[i]); for (let j = 0; j < ks.length; j++) S.worldBounds(ks[j]); }
  const boundsMs = Number(process.hrtime.bigint() - t0) / 1e6;

  const ids = [];
  for (let i = 0; i < 10; i++) { const ks = S.children(frames[i * 37]); for (let j = 0; j < 99; j++) ids.push(ks[j]); }
  ids.push(...S.children(frames[499]).slice(0, 10));
  assert.equal(ids.length, 1000);
  let ops = 0;
  S.onOps(o => { ops += o.length; });
  S.on('change', () => {});
  /* warm */
  S.tx('warm', () => { for (let i = 0; i < 1000; i++) S.set(ids[i], {y: 1 + i}); });
  ops = 0;
  t0 = process.hrtime.bigint();
  S.tx('1000 sets', () => { for (let i = 0; i < 1000; i++) S.set(ids[i], {x: 5000 + i, opacity: 0.5}); });
  const setMs = Number(process.hrtime.bigint() - t0) / 1e6;
  assert.equal(ops, 1000);                                          /* 1,000 nodes, 2 props each, one op per node */

  /* one set touches its subtree only: every other cached world box stays as it was */
  const far = S.children(frames[100])[3], farBox = S.worldBounds(far);
  t0 = process.hrtime.bigint();
  for (let i = 0; i < 1000; i++) S.set(frames[5], {x: 9000 + i});
  const dragMs = Number(process.hrtime.bigint() - t0) / 1e6;
  deq(S.worldBounds(far), farBox);
  const kid = S.children(frames[5])[0];
  assert.ok(near(S.worldBounds(kid).x, 9999 + S.get(kid).x, 1e-6) || S.get(frames[5]).rot);

  t0 = process.hrtime.bigint();
  S.undo();
  const undoMs = Number(process.hrtime.bigint() - t0) / 1e6;

  /* 5,000 creates in one parent (append) stay cheap */
  t0 = process.hrtime.bigint();
  S.tx('paste', () => { for (let i = 0; i < 5000; i++) S.create('RECT', frames[1], {x: i}); });
  const createMs = Number(process.hrtime.bigint() - t0) / 1e6;
  assert.equal(S.children(frames[1]).length, 99 + 5000);

  /* the same with the multiplayer book-keeping on: a second copy of the document (what the server has) */
  const S2 = makeEnv().HD.store;
  S2.tracking(true);
  const doc2 = JSON.parse(json);
  t0 = process.hrtime.bigint();
  S2.load(doc2, 2);
  const loadLiveMs = Number(process.hrtime.bigint() - t0) / 1e6;
  const sent = [];
  S2.onOps((o, b) => sent.push(b));
  S2.on('change', () => {});
  const fr2 = S2.children('0:1'), kids2 = S2.children(fr2[3]);
  S2.tx('warm', () => { for (let i = 0; i < 99; i++) S2.set(kids2[i], {y: 7 + i}); });
  t0 = process.hrtime.bigint();
  S2.tx('1000 sets, waiting', () => { for (let i = 0; i < 1000; i++) S2.set(S2.children(fr2[i % 400])[i % 99], {x: 4000 + i}); });
  const setLiveMs = Number(process.hrtime.bigint() - t0) / 1e6;
  const remote = [];
  for (let i = 0; i < 1000; i++) remote.push({id: S2.children(fr2[400 + (i % 90)])[i % 99], p: {x: i, name: 'r' + i}});
  t0 = process.hrtime.bigint();
  S2.applyRemote(remote);                                           /* 1,000 remote sets while 1,099 of ours wait */
  const remoteMs = Number(process.hrtime.bigint() - t0) / 1e6;
  S2.move([kids2[0]], fr2[4], null);                                /* a waiting tree change of ours ... */
  t0 = process.hrtime.bigint();
  S2.applyRemote([{id: '9:1', p: {type: 'RECT', parent: fr2[5], idx: 'zz', name: 'theirs'}}]);   /* ... meets one of theirs: full rebase */
  const rebaseMs = Number(process.hrtime.bigint() - t0) / 1e6;
  assert.ok(S2.has('9:1') && S2.parent(kids2[0]) === fr2[4]);
  deq(S2.syncCheck(), []);
  t0 = process.hrtime.bigint();
  for (const b of sent) S2.acked(b);
  const ackMs = Number(process.hrtime.bigint() - t0) / 1e6;
  assert.equal(S2.pendingCount(), 0);
  console.log('  perf (live file): load ' + loadLiveMs.toFixed(1) + ' ms | 1,000 sets in one tx ' + setLiveMs.toFixed(2) +
    ' ms | 1,000 remote sets ' + remoteMs.toFixed(2) + ' ms | a full rebase of 50,000 nodes ' + rebaseMs.toFixed(1) +
    ' ms | acks ' + ackMs.toFixed(2) + ' ms');
  assert.ok(loadLiveMs < 1000 && setLiveMs < 50 && rebaseMs < 500);

  console.log('  perf: load ' + count + ' nodes ' + loadMs.toFixed(1) + ' ms | walk all ' + walkMs.toFixed(1) +
    ' ms | world bounds of all ' + boundsMs.toFixed(1) + ' ms | 1,000 sets in one tx ' + setMs.toFixed(2) +
    ' ms | 1,000 single-set tx on a 99-child frame ' + dragMs.toFixed(1) + ' ms | undo ' + undoMs.toFixed(2) +
    ' ms | 5,000 creates in one tx ' + createMs.toFixed(1) + ' ms');
  assert.ok(loadMs < 1000, 'load took ' + loadMs + ' ms');
  assert.ok(setMs < 50, '1,000 sets took ' + setMs + ' ms');
});

test('no eval / no new Function / no inline tricks in the three files (strict CSP)', () => {
  for (const s of SRC) {
    assert.ok(!/\beval\s*\(/.test(s.code), s.f + ' uses eval');
    assert.ok(!/new\s+Function\b/.test(s.code), s.f + ' uses new Function');
    assert.ok(!/setTimeout\s*\(\s*['"`]/.test(s.code), s.f + ' passes a string to setTimeout');
    assert.ok(/^\s*\(function \(\) \{\s*'use strict';/m.test(s.code), s.f + ' is one strict IIFE');
    assert.ok(!/token[^\n]*\?[^\n]*=|[?&]key=/.test(s.code.replace(/\/\*[\s\S]*?\*\//g, '')), s.f + ' puts a token in a URL');
  }
});
