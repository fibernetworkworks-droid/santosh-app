/* HOOLA DESIGN D8b: the starter plugins run against a FAKE `hoola` in node (no browser, no sandbox).
   node design_plugins_ai_harness.js <starters.json>   (the JSON = GET /api/design/plugins/starters' "starters")
   Each starter's code runs exactly as shipped and exactly as D8a's worker runs it: the BODY of an async function with
   `hoola` and `command`, no DOM. A panel (hoola.ui.show) is read for its named fields and answered like the runner
   does (hoola.ui.on -> {action, values}). Every scenario checks what the plugin wrote with hoola.set, what it said with
   hoola.notify, that a ui:false plugin never shows a panel and that every run ends with hoola.close(). Prints PASS <name> per check,
   exits 1 on the first failure. */
'use strict';
const fs = require('fs');
const assert = require('assert');

const starters = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const byId = {};
for (const s of starters) byId[s.manifest.id] = s;

function unescape(s) { return String(s).replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&'); }

/* the panel as the runner would send it back: every named field's value (checkbox = true / false) */
function fieldsOf(html) {
  const out = {}, rx = /<(input|select|textarea)\b([^>]*)>/g; let m;
  while ((m = rx.exec(html))) {
    const attrs = m[2], nm = /\bname="([^"]+)"/.exec(attrs);
    if (!nm) continue;
    if (/\btype="checkbox"/.test(attrs)) { out[nm[1]] = /\bchecked\b/.test(attrs); continue; }
    if (m[1] === 'select') { const end = html.indexOf('</select>', m.index), om = /<option value="([^"]*)"/.exec(html.slice(m.index, end)); out[nm[1]] = om ? unescape(om[1]) : ''; continue; }
    if (m[1] === 'textarea') { const end = html.indexOf('</textarea>', m.index); out[nm[1]] = unescape(html.slice(m.index + m[0].length, end)); continue; }
    const vm = /\bvalue="([^"]*)"/.exec(attrs); out[nm[1]] = vm ? unescape(vm[1]) : '';
  }
  return out;
}
const textOf = (html, id) => { const m = new RegExp('id="' + id + '">([^<]*)<').exec(html); return m ? unescape(m[1]) : ''; };

/* D8a's worker API, faked: answers are node objects (with id), like the real runtime */
function makeHoola(nodes, selection, command) {
  const st = {sets: [], notes: [], closed: false, html: '', opts: null, handlers: [], shown: 0};
  const clone = v => JSON.parse(JSON.stringify(v));
  const nodeOf = id => nodes[id] ? Object.assign(clone(nodes[id]), {id: id}) : null;
  const hoola = {
    command: command || 'run', manifest: {},
    async selection() { return selection.map(nodeOf).filter(Boolean); },
    async select() { return []; },
    async get(id) { return nodeOf(id); },
    async children(id) { return Object.keys(nodes).filter(k => nodes[k].parent === id).sort((a, b) => String(nodes[a].idx || '') < String(nodes[b].idx || '') ? -1 : 1).map(nodeOf); },
    async page() { return nodeOf('0:1'); },
    async pages() { return [nodeOf('0:1')]; },
    async find() { return []; },
    async create() { throw new Error('not used'); },
    async set(id, props) {
      assert.ok(nodes[id], 'set on an unknown node ' + id);
      st.sets.push({id: id, p: clone(props)});
      for (const k of Object.keys(props)) { if (props[k] === null) delete nodes[id][k]; else nodes[id][k] = clone(props[k]); }
      return true;
    },
    async remove() { throw new Error('not used'); },
    async move() { throw new Error('not used'); },
    async notify(t) { st.notes.push(String(t)); return true; },
    ui: {async show(html, opts) { st.shown++; st.html = String(html); st.opts = opts; return true; }, on(fn) { st.handlers.push(fn); }, async close() { st.closed = true; return true; }},
    async close() { st.closed = true; return true; },
    storage: {async get() { return null; }, async set() { return true; }, async keys() { return []; }}
  };
  return {hoola: hoola, st: st};
}

function solid(c) { return [{type: 'solid', color: c, opacity: 1, visible: true}]; }
function base() {
  return {'0:0': {type: 'DOCUMENT', name: 'Document'}, '0:1': {type: 'PAGE', parent: '0:0', idx: 'a', name: 'Page 1', bg: '#F5F5F5'}};
}
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

/* the shipped code, as is, as the BODY of an async function with `hoola` and `command` (exactly like D8a's worker) */
async function run(id, nodes, selection, command, drive) {
  const s = byId[id];
  assert.ok(s, 'no starter ' + id);
  const h = makeHoola(nodes, selection, command || (s.manifest.menu[0] || {}).command);
  const fn = new AsyncFunction('hoola', 'command', s.code);       // the harness is trusted; the plugin code is what runs
  await fn(h.hoola, h.hoola.command);
  if (h.st.shown && !h.st.closed) {
    assert.ok(s.manifest.ui, id + ' shows a panel, so its manifest must say ui: true');
    assert.ok(drive, id + ' showed a panel the test does not drive');
    await drive(h);
  }
  assert.ok(h.st.closed || !h.st.shown, id + ' left its panel open without hoola.close()');
  if (!s.manifest.ui) assert.strictEqual(h.st.shown, 0, id + ' has ui: false and must not show a panel');
  return h;
}
/* a click on data-action=<action>, with the panel's fields (+ what she typed) - like the runner sends it */
async function act(h, action, typed) {
  const values = Object.assign(fieldsOf(h.st.html), typed || {});
  for (const fn of h.st.handlers) await fn({action: action, value: '', values: values});
}
const pass = name => console.log('PASS ' + name);

(async function main() {
  assert.strictEqual(starters.length, 8, 'eight starters');

  /* 1 rename: reading order, numbering with digits, {name} */
  {
    const n = base();
    n['1:1'] = {type: 'FRAME', parent: '0:1', idx: 'a', name: 'Old B', x: 200, y: 0, w: 100, h: 100};
    n['1:2'] = {type: 'FRAME', parent: '0:1', idx: 'b', name: 'Old A', x: 0, y: 5, w: 100, h: 100};
    n['1:3'] = {type: 'RECT', parent: '0:1', idx: 'c', name: 'Old C', x: 0, y: 300, w: 100, h: 100};
    const h = await run('hoola.rename-layers', n, ['1:1', '1:2', '1:3'], 'run', async h => {
      await act(h, 'preview', {pat: 'Card {n}', digits: '2'});
      assert.ok(/Card 01, Card 02, Card 03/.test(textOf(h.st.html, 'preview')), textOf(h.st.html, 'preview'));
      assert.ok(/value="Card \{n\}"/.test(h.st.html), 'what she typed stays in the field');
      await act(h, 'go');
    });
    assert.deepStrictEqual([n['1:2'].name, n['1:1'].name, n['1:3'].name], ['Card 01', 'Card 02', 'Card 03']);
    assert.ok(/Renamed 3 layers/.test(h.st.notes.join(' ')));
    const h2 = await run('hoola.rename-layers', n, ['1:1'], 'run', async h => { await act(h, 'go', {pat: '{type} - {name}'}); });
    assert.strictEqual(n['1:1'].name, 'Frame - Card 02');
    const h3 = await run('hoola.rename-layers', n, [], 'run');
    assert.ok(/Select the layers/.test(h3.st.notes[0]) && h3.st.sets.length === 0 && h2.st.closed);
    pass('rename layers');
  }

  /* 2 tidy: 5 items -> 3 columns, 24 apart, starting at the top-left of the selection; another parent left alone */
  {
    const n = base();
    n['2:9'] = {type: 'FRAME', parent: '0:1', idx: 'z', name: 'Other', x: 900, y: 900, w: 300, h: 300};
    const sizes = [[100, 50], [80, 120], [60, 60], [100, 100], [40, 40]];
    sizes.forEach((s, i) => { n['2:' + (i + 1)] = {type: 'RECT', parent: '0:1', idx: 'a' + i, name: 'R' + i, x: 10 + i * 137, y: 20 + (i % 2) * 3, w: s[0], h: s[1]}; });
    n['2:8'] = {type: 'RECT', parent: '2:9', idx: 'a', name: 'Inside', x: 5, y: 5, w: 10, h: 10};
    const h = await run('hoola.tidy-grid', n, ['2:1', '2:2', '2:3', '2:4', '2:5', '2:8'], 'run');
    const pos = id => [n[id].x, n[id].y];
    assert.deepStrictEqual(pos('2:1'), [10, 20]);
    assert.deepStrictEqual(pos('2:2'), [10 + 100 + 24, 20]);
    assert.deepStrictEqual(pos('2:3'), [10 + 100 + 24 + 80 + 24, 20]);
    assert.deepStrictEqual(pos('2:4'), [10, 20 + 120 + 24]);
    assert.deepStrictEqual(pos('2:5'), [134, 164]);
    assert.deepStrictEqual(pos('2:8'), [5, 5], 'a layer in another frame never moves');
    assert.ok(/5 layers into 3 columns/.test(h.st.notes[0]) && /1 in another frame/.test(h.st.notes[0]), h.st.notes[0]);
    const one = await run('hoola.tidy-grid', n, ['2:1'], 'run');
    assert.ok(/two or more/.test(one.st.notes[0]) && one.st.sets.length === 0);
    pass('tidy grid');
  }

  /* 3 contrast: lists the low ones (frame fill, gradient worst end, page bg), fix makes every one read >= 4.5 */
  {
    const n = base();
    n['3:1'] = {type: 'FRAME', parent: '0:1', idx: 'a', name: 'Card', x: 0, y: 0, w: 400, h: 400, fills: solid('#FFFFFF')};
    n['3:2'] = {type: 'TEXT', parent: '3:1', idx: 'a', name: 'Low', chars: 'Pale words', fills: solid('#CCCCCC')};
    n['3:3'] = {type: 'TEXT', parent: '3:1', idx: 'b', name: 'Good', chars: 'Dark words', fills: solid('#111827')};
    n['3:4'] = {type: 'FRAME', parent: '3:1', idx: 'c', name: 'Band', fills: [{type: 'linear', stops: [{pos: 0, color: '#FFFFFF'}, {pos: 1, color: '#E2E8F0'}], from: [0, 0], to: [1, 0], visible: true}]};
    n['3:5'] = {type: 'TEXT', parent: '3:4', idx: 'a', name: 'On gradient', chars: 'Mid grey', fills: solid('#777777')};
    n['3:6'] = {type: 'TEXT', parent: '0:1', idx: 'b', name: 'On page', chars: 'Light on page', fills: solid('#DDDDDD')};
    const h = await run('hoola.contrast-check', n, [], 'check', async h => {
      assert.ok(/3 of 4 texts in this page are below 4.5/.test(textOf(h.st.html, 'sum')), textOf(h.st.html, 'sum'));
      assert.ok(h.st.html.indexOf('Pale words') > 0 && h.st.html.indexOf('Dark words') < 0);
      await act(h, 'fix');
    });
    assert.ok(/Fixed 3 texts/.test(h.st.notes[0]), h.st.notes.join('|'));
    const lumOf = c => { const v = [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16) / 255).map(x => x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4)); return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
    const ratio = (a, b) => { const x = lumOf(a), y = lumOf(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
    assert.ok(ratio(n['3:2'].fills[0].color, '#FFFFFF') >= 4.5 && ratio(n['3:6'].fills[0].color, '#F5F5F5') >= 4.5);
    assert.strictEqual(n['3:3'].fills[0].color, '#111827', 'a text that reads is never touched');
    const c5 = n['3:5'].fills[0].color;
    assert.ok(Math.min(ratio(c5, '#FFFFFF'), ratio(c5, '#E2E8F0')) >= 4.5, 'a gradient counts its worst end');
    const again = await run('hoola.contrast-check', n, ['3:1'], 'fix');
    assert.ok(/(Fixed [01] texts|already reads)/.test(again.st.notes[0]), again.st.notes[0]);
    pass('contrast checker');
  }

  /* 4 find and replace: case, whole words, a styled text keeps its runs (left alone when the length changes) */
  {
    const n = base();
    n['4:1'] = {type: 'TEXT', parent: '0:1', idx: 'a', name: 'A', chars: 'Sale today. sale ends soon; wholesale too'};
    n['4:2'] = {type: 'TEXT', parent: '0:1', idx: 'b', name: 'B', chars: 'Big Sale', runs: [{s: 0, e: 3, fontWeight: 700}]};
    n['4:3'] = {type: 'TEXT', parent: '0:1', idx: 'c', name: 'C', chars: 'Sale', runs: [{s: 0, e: 4, fontWeight: 700}]};
    const h = await run('hoola.find-replace', n, [], 'run', async h => {
      await act(h, 'preview', {find: 'sale', to: 'Offer', whole: true});
      const said = textOf(h.st.html, 'count');
      assert.ok(/4 matches in 3 texts/.test(said) && /2 with mixed styles/.test(said), said);
      await act(h, 'go');
    });
    assert.strictEqual(n['4:1'].chars, 'Offer today. Offer ends soon; wholesale too');
    assert.strictEqual(n['4:2'].chars, 'Big Sale', 'mixed styles + a length change = left alone');
    assert.ok(/Replaced in 1 text; 2 with mixed styles/.test(h.st.notes[0]), h.st.notes[0]);
    const h2 = await run('hoola.find-replace', n, [], 'run', async h => { await act(h, 'go', {find: 'Sale', to: 'Deal', caseOn: true}); });
    assert.strictEqual(n['4:2'].chars, 'Big Deal', 'same length: a styled text is changed, its runs still line up');
    assert.deepStrictEqual(n['4:2'].runs, [{s: 0, e: 3, fontWeight: 700}]);
    assert.strictEqual(n['4:1'].chars, 'Offer today. Offer ends soon; wholesale too', 'match case: lower case left');
    assert.ok(h2.st.sets.every(s => Object.keys(s.p).join() === 'chars'));
    const h3 = await run('hoola.find-replace', n, [], 'run', async h => { await act(h, 'go', {find: 'a.b', to: 'x'}); });
    assert.ok(/Nothing to replace/.test(h3.st.notes[0]), 'regex characters are found literally');
    pass('find and replace');
  }

  /* 5 palette: near colours merged, the most used first, existing styles kept and not doubled */
  {
    const n = base();
    n['0:0'].styles = {s_old: {kind: 'fill', name: 'Brand', value: solid('#4F46E5')}};
    n['5:1'] = {type: 'FRAME', parent: '0:1', idx: 'a', name: 'Card', fills: solid('#FFFFFF'), strokes: solid('#E5E7EB')};
    n['5:2'] = {type: 'RECT', parent: '5:1', idx: 'a', fills: solid('#4F46E6')};
    n['5:3'] = {type: 'TEXT', parent: '5:1', idx: 'b', fills: solid('#111827'), chars: 'x'};
    n['5:4'] = {type: 'TEXT', parent: '5:1', idx: 'c', fills: solid('#121828'), chars: 'y'};
    n['5:5'] = {type: 'RECT', parent: '5:1', idx: 'd', fills: solid('#FF0000'), visible: false};
    const h = await run('hoola.palette-styles', n, ['5:1'], 'run');
    const st = n['0:0'].styles, mine = Object.keys(st).filter(k => k !== 's_old').map(k => st[k]);
    assert.ok(st.s_old && st.s_old.name === 'Brand', 'her own style is kept');
    assert.deepStrictEqual(mine.map(s => s.value[0].color), ['#111827', '#FFFFFF', '#E5E7EB']);
    assert.ok(mine.every(s => s.kind === 'fill' && /^Palette \/ #/.test(s.name)));
    assert.ok(/Added 3 colour styles/.test(h.st.notes[0]) && h.st.sets.length === 1 && h.st.sets[0].id === '0:0');
    const again = await run('hoola.palette-styles', n, ['5:1'], 'run');
    assert.ok(/already has a fill style/.test(again.st.notes[0]) && again.st.sets.length === 0);
    pass('palette to styles');
  }

  /* 6 Indian numbers and rupees */
  {
    const n = base();
    const texts = {
      '6:1': 'Rs 150000 only, was INR 2500000',
      '6:2': 'Call 9876543210 · PIN 411001 · since 1998 · 12500 happy customers · 1,000,000 views · 3.5 rating',
      '6:3': 'Price 4999 and 120.50',
      '6:4': 'Model X2000 and order #00123'
    };
    for (const k of Object.keys(texts)) n[k] = {type: 'TEXT', parent: '0:1', idx: k, chars: texts[k]};
    await run('hoola.indian-numbers', n, ['6:1', '6:2', '6:4'], 'indian');
    assert.strictEqual(n['6:1'].chars, '₹1,50,000 only, was ₹25,00,000');
    assert.strictEqual(n['6:2'].chars, 'Call 9876543210 · PIN 411001 · since 1998 · 12,500 happy customers · 10,00,000 views · 3.5 rating');
    assert.strictEqual(n['6:4'].chars, 'Model X2000 and order #00123');
    await run('hoola.indian-numbers', n, ['6:3'], 'rupee');
    assert.strictEqual(n['6:3'].chars, 'Price ₹4,999 and ₹120.50');
    const none = await run('hoola.indian-numbers', n, ['6:4'], 'indian');
    assert.ok(/No numbers to format/.test(none.st.notes[0]));
    pass('indian numbers and rupee');
  }

  /* 7 CSS variables: read only, every kind */
  {
    const n = base();
    n['0:0'].styles = {
      a: {kind: 'fill', name: 'Brand / Primary', value: solid('#4f46e5')},
      b: {kind: 'fill', name: 'Hero glow', value: [{type: 'linear', stops: [{pos: 0, color: '#FFD9A8', opacity: 1}, {pos: 1, color: '#C055F5', opacity: 0.5}], from: [0, 0], to: [1, 0], visible: true}]},
      c: {kind: 'text', name: 'Heading 1', value: {font: 'Sora', fontSize: 40, fontWeight: 700, lineHeight: 48, letterSpacing: -0.5}},
      d: {kind: 'effect', name: 'Card shadow', value: [{type: 'drop', x: 0, y: 6, blur: 16, spread: 0, color: '#0F172A', opacity: 0.12, visible: true}]}
    };
    n['0:0'].vars = {v1: {name: 'Space M', type: 'number', modes: {Light: 16}}, v2: {name: 'Ink', type: 'color', modes: {Light: '#111827', Dark: '#F8FAFC'}}};
    n['0:0'].modes = ['Light', 'Dark'];
    const h = await run('hoola.css-variables', n, [], 'run', async h => {
      const css = fieldsOf(h.st.html).out;
      for (const line of ['--color-brand-primary: #4F46E5;', '--color-hero-glow: linear-gradient(90deg, #FFD9A8 0%, rgba(192, 85, 245, 0.5) 100%);',
        "--font-heading-1-family: 'Sora';", '--font-heading-1-size: 40px;', '--font-heading-1-weight: 700;', '--font-heading-1-line-height: 48px;',
        '--font-heading-1-letter-spacing: -0.5px;', '--shadow-card-shadow: 0px 6px 16px 0px rgba(15, 23, 42, 0.12);', '--space-m: 16;', '--ink: #111827;'])
        assert.ok(css.indexOf(line) >= 0, 'missing ' + line + '\n' + css);
      assert.ok(/^:root \{/.test(css));
      await act(h, 'close');
    });
    assert.strictEqual(h.st.sets.length, 0, 'read only');
    const empty = await run('hoola.css-variables', base(), [], 'run');
    assert.ok(/no colour, text or effect styles/.test(empty.st.notes[0]));
    pass('css variables');
  }

  /* 8 swap fonts: the node font and the styled ranges, sizes kept */
  {
    const n = base();
    n['8:1'] = {type: 'FRAME', parent: '0:1', idx: 'a', name: 'Box'};
    n['8:2'] = {type: 'TEXT', parent: '8:1', idx: 'a', chars: 'One', font: 'Inter', fontSize: 20};
    n['8:3'] = {type: 'TEXT', parent: '8:1', idx: 'b', chars: 'Two', fontSize: 14, runs: [{s: 0, e: 1, font: 'Inter', fontWeight: 700}, {s: 1, e: 3, font: 'Lora'}]};
    n['8:4'] = {type: 'TEXT', parent: '8:1', idx: 'c', chars: 'Three', font: 'Lora'};
    const h = await run('hoola.swap-fonts', n, ['8:1'], 'run', async h => {
      assert.strictEqual(fieldsOf(h.st.html).from, 'Inter', 'the most used font is offered first');
      const to = h.st.html.slice(h.st.html.indexOf('name="to"'));
      assert.ok(to.indexOf('value="Noto Sans Devanagari"') >= 0 && to.indexOf('value="Inter"') < 0);
      await act(h, 'go', {to: 'Poppins'});
    });
    assert.deepStrictEqual([n['8:2'].font, n['8:2'].fontSize, n['8:3'].font, n['8:4'].font], ['Poppins', 20, 'Poppins', 'Lora']);
    assert.deepStrictEqual(n['8:3'].runs, [{s: 0, e: 1, font: 'Poppins', fontWeight: 700}, {s: 1, e: 3, font: 'Lora'}]);
    assert.ok(/Inter is now Poppins in 2 texts/.test(h.st.notes[0]), h.st.notes[0]);
    pass('swap fonts');
  }
  console.log('ALL ' + starters.length + ' STARTERS OK');
})().catch(e => { console.error('FAIL', e && e.stack || e); process.exit(1); });
