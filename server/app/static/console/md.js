/* v0.161 Hoola Console markdown: safe while a reply is still being written.
   - Every character of model text is escaped here first; HTML never passes through.
   - Headings, bold / italic, inline code, fenced code (language label, Copy, light highlighting), ordered / unordered
     lists with nesting (numbers kept), tables, quotes, links (http / https only, rel noopener) and rules.
   - streaming: open syntax at the end is closed (or held back) so a raw **, |, ` or [ never shows.
   - HoolaMD.Live: finished blocks are rendered once; only the last block re-renders on each tick. */
'use strict';
(() => {
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const FENCE = /^\s{0,3}(```+|~~~+)\s*([\w#+.-]*)\s*$/;
const HR = /^\s{0,3}([-*_])(\s*\1){2,}\s*$/;
const HEAD = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/;
const QUOTE = /^\s{0,3}>\s?(.*)$/;
const LI = /^(\s*)([-*+•]|\d{1,9}[.)])\s+(.*)$/;
const TROW = /^\s*\|.*\|?\s*$/;
const TSEP = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

/* ---------- light code highlighting (tokens from the raw code, each escaped) ---------- */
const KW = new Set(('if else elif for while do return function def class const let var import from export default async await ' +
  'try except catch finally raise throw new this self None null true false True False and or not in is with as yield ' +
  'public private static void int str float bool string fn pub use match case break continue lambda select where').split(' '));
function highlight(code, lang) {
  const hashComment = /^(py|python|sh|bash|shell|yaml|yml|toml|rb|ruby|r|dockerfile|ini|conf)$/i.test(lang || '');
  const re = hashComment ? /(#[^\n]*)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`[^`]*`)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)/g
                         : /(\/\/[^\n]*|\/\*[\s\S]*?\*\/|<!--[\s\S]*?-->)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`[^`]*`)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)/g;
  let out = '', last = 0, m;
  while ((m = re.exec(code))) {
    out += esc(code.slice(last, m.index)); last = re.lastIndex;
    if (m[1]) out += `<span class="hc">${esc(m[1])}</span>`;
    else if (m[2]) out += `<span class="hs">${esc(m[2])}</span>`;
    else if (m[3]) out += `<span class="hn">${esc(m[3])}</span>`;
    else out += KW.has(m[4]) ? `<span class="hk">${esc(m[4])}</span>` : esc(m[4]);
  }
  return out + esc(code.slice(last));
}

/* ---------- inline ---------- */
function safeHref(u) { try { const x = new URL(u); return (x.protocol === 'https:' || x.protocol === 'http:') ? x.href : ''; } catch { return ''; } }
function closeInline(s) {
  // streaming: a marker that is still open at the end of the text is closed so it never shows raw
  s = s.replace(/(^|[^*_`~])(\*{1,2}|_{1,2}|`+|~~)\s*$/, '$1');                // an opening marker with no words yet: wait
  const ticks = (s.match(/`/g) || []).length; if (ticks % 2) s += '`';
  const noCode = s.replace(/`[^`]*`/g, '');
  const lb = noCode.lastIndexOf('['), rb = noCode.lastIndexOf(']');
  if (lb > rb) s = s.slice(0, s.lastIndexOf('['));                               // "[link te" -> held back
  else if (/\]\([^)]*$/.test(noCode)) s = s.replace(/\[([^\]]*)\]\([^)]*$/, '$1');  // "[text](http..." -> text for now
  if ((noCode.match(/\*\*/g) || []).length % 2) s += '**';
  const singles = noCode.replace(/\*\*/g, '').replace(/(^|\s)\*(\s|$)/g, '$1$2').split('*').length - 1;  // no lookbehind: old Safari
  if (singles % 2) s += '*';
  return s.replace(/(\s)[*_]{1,2}$/, '$1');                                      // a lone trailing marker
}
function inline(raw) {
  const codes = [];
  let s = raw.replace(/`([^`\n]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
  const links = [];
  s = s.replace(/\[([^\]\n]+)\]\(((?:[^()\s]|\([^()\s]*\))+)(?:\s+"[^"]*")?\)/g, (all, t, u) => {
    const h = safeHref(u); if (!h) return t; links.push([t, h]); return `\u0001${links.length - 1}\u0001`; });
  s = esc(s);
  s = s.replace(/\*\*(?=\S)([\s\S]*?\S)\*\*/g, '<b>$1</b>').replace(/(^|[^\w])__(?=\S)([\s\S]*?\S)__(?!\w)/g, '$1<b>$2</b>');
  s = s.replace(/(^|[^\w*])\*(?=\S)([^*\n]*?\S)\*(?![\w*])/g, '$1<i>$2</i>').replace(/(^|[^\w])_(?=\S)([^_\n]*?\S)_(?!\w)/g, '$1<i>$2</i>');
  s = s.replace(/~~(?=\S)([^~\n]*?\S)~~/g, '<s>$1</s>');
  s = s.replace(/(^|[\s(])(https?:\/\/[^\s<]+[^\s<.,;:!?)'"])/g, (all, pre, u) => {
    const h = safeHref(u.replace(/&amp;/g, '&')); return h ? `${pre}<a href="${esc(h)}" target="_blank" rel="noopener noreferrer">${u}</a>` : all; });
  s = s.replace(/\[(\d{1,2})\]/g, '<span class="tag v">[$1]</span>');
  s = s.replace(/\u0001(\d+)\u0001/g, (_, i) => { const [t, h] = links[+i]; return `<a href="${esc(h)}" target="_blank" rel="noopener noreferrer">${inline(t)}</a>`; });
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${esc(codes[+i])}</code>`);
}

/* ---------- blocks ---------- */
function splitBlocks(text) {
  // top-level blocks separated by blank lines; a fenced code block is one block even with blank lines inside
  const lines = String(text ?? '').replace(/\r\n?/g, '\n').split('\n'), out = [];
  let cur = [], fence = null;
  for (const l of lines) {
    const f = l.match(FENCE);
    if (fence) { cur.push(l); if (f && f[1][0] === fence[0] && f[1].length >= fence.length && !f[2]) { fence = null; } continue; }
    if (f) { if (cur.length) { out.push(cur.join('\n')); cur = []; } fence = f[1]; cur.push(l); continue; }
    if (!l.trim()) { if (cur.length) { out.push(cur.join('\n')); cur = []; } continue; }
    cur.push(l);
  }
  if (cur.length) out.push(cur.join('\n'));
  return out;
}
function cells(row) { return row.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim()); }
function table(lines, streaming) {
  const head = cells(lines[0]), al = cells(lines[1]).map(c => c.endsWith(':') ? (c.startsWith(':') ? 'center' : 'right') : '');
  let body = lines.slice(2);
  if (streaming && body.length && !/\|\s*$/.test(body[body.length - 1])) body = body.slice(0, -1);   // the row being written
  const td = (c, i, tag) => `<${tag}${al[i] ? ` style="text-align:${al[i]}"` : ''}>${inline(c)}</${tag}>`;
  return `<div class="tbw"><table class="mdt"><thead><tr>${head.map((c, i) => td(c, i, 'th')).join('')}</tr></thead><tbody>`
    + body.map(r => `<tr>${cells(r).slice(0, head.length).map((c, i) => td(c, i, 'td')).join('')}</tr>`).join('') + '</tbody></table></div>';
}
function list(lines, streaming) {
  // nested ordered / unordered lists from indentation; ordered lists keep their first number
  let html = '';
  const stack = [];   // {tag, indent}
  let open = false;
  for (let k = 0; k < lines.length; k++) {
    const l = lines[k], m = l.match(LI);
    if (!m) { if (open) html = html.replace(/<\/li>$/, '') + '<br>' + inline(streaming && k === lines.length - 1 ? closeInline(l.trim()) : l.trim()) + '</li>'; continue; }
    const ind = m[1].replace(/\t/g, '    ').length, ordered = /\d/.test(m[2]), tag = ordered ? 'ol' : 'ul';
    let txt = m[3]; if (streaming && k === lines.length - 1) txt = closeInline(txt);
    while (stack.length && ind < stack[stack.length - 1].indent) { html += `</${stack.pop().tag}></li>`; }
    const top = stack[stack.length - 1];
    if (!top || ind > top.indent) {
      if (top) html = html.replace(/<\/li>$/, '');
      const start = ordered ? parseInt(m[2], 10) : 1;
      html += `<${tag}${ordered && start !== 1 ? ` start="${start}"` : ''}>`; stack.push({tag, indent: ind});
    } else if (top.tag !== tag) { html += `</${stack.pop().tag}>`; html += `<${tag}>`; stack.push({tag, indent: ind}); }
    html += `<li>${inline(txt)}</li>`; open = true;
  }
  while (stack.length) { const s = stack.pop(); html += `</${s.tag}>` + (stack.length ? '</li>' : ''); }
  return html;
}
function block(src, streaming) {
  const lines = src.split('\n'), first = lines[0];
  const f = first.match(FENCE);
  if (f) {
    let body = lines.slice(1); const closed = body.length && FENCE.test(body[body.length - 1]) && !body[body.length - 1].match(FENCE)[2];
    if (closed) body = body.slice(0, -1);
    const lang = f[2] || '', code = body.join('\n');
    return `<div class="cb"><div class="cbh"><span>${esc(lang || 'code')}</span><button type="button" class="cbcopy" data-copy>Copy</button></div>`
      + `<pre><code${lang ? ` data-lang="${esc(lang)}"` : ''}>${highlight(code, lang)}${!closed && streaming ? '<span class="caret"></span>' : ''}</code></pre></div>`;
  }
  if (lines.length === 1 && HR.test(first)) return '<hr>';
  const h = first.match(HEAD);
  if (h && lines.length === 1) { const n = h[1].length; return `<h${Math.min(6, n + 2)} class="mdh">${inline(streaming ? closeInline(h[2]) : h[2])}</h${Math.min(6, n + 2)}>`; }
  if (lines.every(l => QUOTE.test(l))) return `<blockquote>${render(lines.map(l => l.match(QUOTE)[1]).join('\n'), streaming)}</blockquote>`;
  if (lines.length >= 2 && TROW.test(first) && TSEP.test(lines[1]) && lines.slice(2).every(l => TROW.test(l))) return table(lines, streaming);
  if (streaming && TROW.test(lines[lines.length - 1]) && lines.every(l => TROW.test(l) || TSEP.test(l) || /^\s*\|?[\s:|-]*$/.test(l))) return '';   // a table still arriving
  if (LI.test(first)) return list(lines, streaming);
  // paragraph (a heading line inside is still a heading)
  return lines.map((l, k) => {
    const hh = l.match(HEAD); const t = streaming && k === lines.length - 1 ? closeInline(l) : l;
    if (hh) return `<h${Math.min(6, hh[1].length + 2)} class="mdh">${inline(streaming && k === lines.length - 1 ? closeInline(hh[2]) : hh[2])}</h${Math.min(6, hh[1].length + 2)}>`;
    return `<p>${inline(t)}</p>`;
  }).join('').replace(/<\/p><p>/g, '<br>');
}
function render(text, streaming) {
  const bs = splitBlocks(text);
  return bs.map((b, i) => block(b, streaming && i === bs.length - 1)).join('');
}

/* ---------- live: finished blocks stay, the last one re-renders ---------- */
class Live {
  constructor(el) { this.el = el; this.done = []; this.tail = null; this.text = ''; }
  update(text, streaming) {
    this.text = text;
    const bs = splitBlocks(text), fin = streaming ? bs.length - 1 : bs.length;
    let i = 0;
    while (i < this.done.length && i < fin && this.done[i].src === bs[i]) i++;
    for (const d of this.done.splice(i)) d.node.remove();          // changed (a reset or a final text that differs)
    for (; i < fin; i++) {
      const node = document.createElement('div'); node.className = 'mdb'; node.innerHTML = block(bs[i], false);
      this.el.insertBefore(node, this.tail); this.done.push({src: bs[i], node});
    }
    if (!this.tail) { this.tail = document.createElement('div'); this.tail.className = 'mdb tail'; this.el.appendChild(this.tail); }
    this.tail.innerHTML = streaming && bs.length ? block(bs[bs.length - 1], true) : '';
  }
  clear() { this.done = []; this.tail = null; this.text = ''; this.el.innerHTML = ''; }
}

window.HoolaMD = {render, Live, esc, splitBlocks, closeInline, inline};
})();
