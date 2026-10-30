// v0.222 SAAF CHAT (phase 3 of the Claude-style reply plan): Hoola's replies on the phone read like Claude's -
// paragraphs, real bullet / numbered lists, headings, bold / italic, `code`, code blocks, quotes, small tables and
// tappable links - instead of raw `**` and `###`.
//
// Our own small renderer (no pub package): every input is plain text from the server, nothing is ever run, links
// open through openInApp (http/https inside Hoola's browser, others in their app). While a reply STREAMS in
// (streaming: true) a half-written marker never shows: an open `**` / `` ` `` / `~~` already styles what follows,
// a dangling `*`, `#`, `-`, `[` or a table header without its separator row stays hidden until the next words
// arrive. A finished message with an unmatched marker shows the character as written.
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import '../nav.dart';
import 'glass.dart';

final _url = RegExp(r'https?://[^\s<>()\[\]"]+[^\s<>()\[\]".,;:!?]', caseSensitive: false);
final _heading = RegExp(r'^(#{1,6})\s+(.*)$');
final _bullet = RegExp(r'^(\s*)([-*+•])\s+(.*)$');
final _number = RegExp(r'^(\s*)(\d{1,3})[.)]\s+(.*)$');
final _rule = RegExp(r'^\s*([-*_])(\s*\1){2,}\s*$');
final _tableSep = RegExp(r'^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$');
final _fence = RegExp(r'^\s*(```|~~~)\s*([\w+#.-]*)\s*$');

/// One block of a message (paragraph, heading, list item, code, quote, table, rule).
class MdBlock {
  MdBlock(this.kind, this.text, {this.level = 0, this.marker = '', this.lang = '', this.rows = const []});
  final String kind;        // p | h | li | ol | code | quote | table | hr
  final String text;
  final int level;          // heading level / list nesting
  final String marker;      // the number of an ordered item
  final String lang;        // code fence language
  final List<List<String>> rows;
}

List<String> _cells(String line) {
  var t = line.trim();
  if (t.startsWith('|')) t = t.substring(1);
  if (t.endsWith('|')) t = t.substring(0, t.length - 1);
  return t.split('|').map((c) => c.trim()).toList();
}

/// Cuts a message into blocks. Pure function: the same text always gives the same blocks.
List<MdBlock> mdBlocks(String src, {bool streaming = false}) {
  final lines = src.replaceAll('\r\n', '\n').split('\n');
  final out = <MdBlock>[];
  final para = <String>[];
  void flushPara() {
    if (para.isNotEmpty) {
      out.add(MdBlock('p', para.join('\n')));
      para.clear();
    }
  }

  var i = 0;
  while (i < lines.length) {
    final line = lines[i];
    final last = i == lines.length - 1;
    final fence = _fence.firstMatch(line);
    if (fence != null) {
      flushPara();
      final code = <String>[];
      var j = i + 1;
      while (j < lines.length && !_fence.hasMatch(lines[j])) {
        code.add(lines[j]);
        j++;
      }
      out.add(MdBlock('code', code.join('\n'), lang: fence.group(2) ?? ''));
      i = j + 1;          // past the closing fence (or the end while it streams)
      continue;
    }
    if (line.trim().isEmpty) {
      flushPara();
      i++;
      continue;
    }
    // a table: a pipe row followed by its separator row
    if (line.contains('|') && i + 1 < lines.length && _tableSep.hasMatch(lines[i + 1])) {
      flushPara();
      final rows = <List<String>>[_cells(line)];
      var j = i + 2;
      while (j < lines.length && lines[j].contains('|') && lines[j].trim().isNotEmpty) {
        rows.add(_cells(lines[j]));
        j++;
      }
      out.add(MdBlock('table', '', rows: rows));
      i = j;
      continue;
    }
    // streaming: a trailing pipe row may be a table header whose separator is still coming
    if (streaming && last && line.trimLeft().startsWith('|')) {
      flushPara();
      i++;
      continue;
    }
    final h = _heading.firstMatch(line);
    if (h != null) {
      flushPara();
      out.add(MdBlock('h', h.group(2)!.replaceAll(RegExp(r'\s#+\s*$'), ''), level: h.group(1)!.length));
      i++;
      continue;
    }
    if (_rule.hasMatch(line)) {
      flushPara();
      if (!(streaming && last)) out.add(MdBlock('hr', ''));
      i++;
      continue;
    }
    final b = _bullet.firstMatch(line);
    if (b != null) {
      flushPara();
      out.add(MdBlock('li', b.group(3)!, level: (b.group(1)!.replaceAll('\t', '  ').length ~/ 2).clamp(0, 3)));
      i++;
      continue;
    }
    final n = _number.firstMatch(line);
    if (n != null) {
      flushPara();
      out.add(MdBlock('ol', n.group(3)!,
          level: (n.group(1)!.replaceAll('\t', '  ').length ~/ 2).clamp(0, 3), marker: n.group(2)!));
      i++;
      continue;
    }
    if (line.trimLeft().startsWith('>')) {
      flushPara();
      final q = <String>[];
      var j = i;
      while (j < lines.length && lines[j].trimLeft().startsWith('>')) {
        q.add(lines[j].trimLeft().replaceFirst(RegExp(r'^>\s?'), ''));
        j++;
      }
      out.add(MdBlock('quote', q.join('\n')));
      i = j;
      continue;
    }
    if (streaming && last) {
      // a line that is only the start of a marker ("#", "##", "-", "*", "1.") waits for its words
      final t = line.trim();
      if (RegExp(r'^(#{1,6}|[-*+•]|\d{1,3}[.)]?)$').hasMatch(t)) {
        i++;
        continue;
      }
    }
    // a continuation line of a list item (indented, no marker of its own) joins the item
    if (para.isEmpty && out.isNotEmpty && (out.last.kind == 'li' || out.last.kind == 'ol') &&
        line.startsWith('  ')) {
      final prev = out.removeLast();
      out.add(MdBlock(prev.kind, '${prev.text} ${line.trim()}', level: prev.level, marker: prev.marker));
      i++;
      continue;
    }
    para.add(line);
    i++;
  }
  flushPara();
  return out;
}

final _wordRe = RegExp(r'[A-Za-z0-9\u0900-\u097F]', unicode: true);
bool _word(String c) => _wordRe.hasMatch(c);

/// Inline marks of one block -> spans. [streaming]: an open mark styles the rest instead of showing.
List<InlineSpan> mdInline(String s, {bool streaming = false, Color link = const Color(0xFFA78BFA)}) {
  final spans = <InlineSpan>[];
  final buf = StringBuffer();
  void flush() {
    if (buf.isNotEmpty) {
      spans.add(TextSpan(text: buf.toString()));
      buf.clear();
    }
  }

  const code = TextStyle(fontFamily: 'monospace', fontSize: 14, backgroundColor: Color(0x26FFFFFF));
  var i = 0;
  final n = s.length;
  while (i < n) {
    final ch = s[i];
    // `code`
    if (ch == '`') {
      final j = s.indexOf('`', i + 1);
      if (j > i + 1) {
        flush();
        spans.add(TextSpan(text: s.substring(i + 1, j), style: code));
        i = j + 1;
        continue;
      }
      if (j < 0 && streaming) {
        flush();
        if (i + 1 < n) spans.add(TextSpan(text: s.substring(i + 1), style: code));
        break;
      }
    }
    // **bold** / __bold__ / ~~strike~~
    var next = -1;                       // where the scan goes on when a mark matched
    for (final mk in const ['**', '__', '~~']) {
      if (!s.startsWith(mk, i) || (mk == '__' && i > 0 && _word(s[i - 1]))) continue;
      final j = s.indexOf(mk, i + 2);
      final style = mk == '~~'
          ? const TextStyle(decoration: TextDecoration.lineThrough)
          : const TextStyle(fontWeight: FontWeight.w600);   // v0.249 Claude's bold is 600, not 800
      if (j > i + 2) {
        flush();
        spans.add(TextSpan(style: style, children: mdInline(s.substring(i + 2, j), link: link)));
        next = j + 2;
      } else if (j < 0 && streaming) {
        flush();
        if (i + 2 < n) {
          spans.add(TextSpan(style: style, children: mdInline(s.substring(i + 2), streaming: true, link: link)));
        }
        next = n;
      }
      break;
    }
    if (next >= 0) {
      i = next;
      continue;
    }
    // streaming: a lone trailing "*", "_" or "~" is the start of a mark still being written
    if (streaming && i == n - 1 && (ch == '*' || ch == '_' || ch == '~')) break;
    // *italic* / _italic_
    if ((ch == '*' || ch == '_') && i + 1 < n && s[i + 1] != ' ' && s[i + 1] != ch &&
        (i == 0 || !_word(s[i - 1]))) {
      var j = i + 1;
      var found = -1;
      while (true) {
        j = s.indexOf(ch, j);
        if (j < 0) break;
        if (s[j - 1] != ' ' && (j + 1 >= n || !_word(s[j + 1]))) {
          found = j;
          break;
        }
        j++;
      }
      if (found > i + 1) {
        flush();
        spans.add(TextSpan(style: const TextStyle(fontStyle: FontStyle.italic),
            children: mdInline(s.substring(i + 1, found), streaming: false, link: link)));
        i = found + 1;
        continue;
      }
    }
    // [label](url)
    if (ch == '[') {
      final mid = s.indexOf('](', i + 1);
      final nl = s.indexOf('\n', i + 1);
      if (mid > i && (nl < 0 || mid < nl)) {
        final end = s.indexOf(')', mid + 2);
        if (end > mid) {
          final label = s.substring(i + 1, mid);
          final href = s.substring(mid + 2, end).trim();
          final uri = Uri.tryParse(href);
          if (uri != null && (uri.scheme == 'http' || uri.scheme == 'https' || uri.scheme == 'mailto' || uri.scheme == 'tel')) {
            flush();
            spans.add(TextSpan(
              text: label.isEmpty ? href : label,
              style: TextStyle(color: link, fontWeight: FontWeight.w700, decoration: TextDecoration.underline, decorationColor: link),
              recognizer: TapGestureRecognizer()..onTap = () => openInApp(href, title: label),
            ));
            i = end + 1;
            continue;
          }
        } else if (streaming) {
          flush();
          spans.add(TextSpan(text: s.substring(i + 1, mid)));   // the label, while its address is still coming
          break;
        }
      } else if (streaming && mid < 0 && nl < 0 && !s.substring(i).contains(']')) {
        // "[label" still being written: show the label without its bracket
        buf.write(s.substring(i + 1));
        break;
      }
    }
    // bare link
    if ((ch == 'h' || ch == 'H') && (i == 0 || !_word(s[i - 1]))) {
      final m = _url.matchAsPrefix(s, i);
      if (m != null) {
        flush();
        final href = m.group(0)!;
        final host = Uri.tryParse(href)?.host.replaceFirst('www.', '') ?? href;
        spans.add(TextSpan(
          text: host.isEmpty ? href : '🔗 $host',
          style: TextStyle(color: link, fontWeight: FontWeight.w700, decoration: TextDecoration.underline, decorationColor: link),
          recognizer: TapGestureRecognizer()..onTap = () => openInApp(href),
        ));
        i = m.end;
        continue;
      }
    }
    buf.write(ch);
    i++;
  }
  flush();
  return spans;
}

/// The words of a markdown message without its marks: for Copy, Quote and anything that must read as plain text.
String mdPlain(String src) {
  final out = <String>[];
  for (final b in mdBlocks(src)) {
    String strip(String t) => t
        .replaceAllMapped(RegExp(r'\[([^\]\n]*)\]\(([^)\s]+)\)'), (m) => '${m[1]} (${m[2]})')
        .replaceAllMapped(RegExp(r'(\*\*|__|~~)(.+?)\1'), (m) => m[2]!)
        .replaceAllMapped(RegExp(r'(^|[^\w*])\*([^*\s][^*]*?)\*(?!\w)'), (m) => '${m[1]}${m[2]}')
        .replaceAllMapped(RegExp(r'`([^`]+)`'), (m) => m[1]!);
    switch (b.kind) {
      case 'h':
      case 'p':
      case 'quote':
        out.add(strip(b.text));
        break;
      case 'li':
        out.add('${'  ' * b.level}• ${strip(b.text)}');
        break;
      case 'ol':
        out.add('${'  ' * b.level}${b.marker}. ${strip(b.text)}');
        break;
      case 'code':
        out.add(b.text);
        break;
      case 'table':
        for (final r in b.rows) {
          out.add(r.map(strip).join(' | '));
        }
        break;
    }
  }
  return out.join('\n');
}

/// A Hoola reply, rendered. [trailing] (the typing caret) rides at the end of the last text block.
class MdText extends StatelessWidget {
  const MdText(this.text, {super.key, required this.style, this.streaming = false, this.selectable = false, this.trailing});
  final String text;
  final TextStyle style;
  final bool streaming;
  final bool selectable;
  final InlineSpan? trailing;

  @override
  Widget build(BuildContext context) {
    final blocks = mdBlocks(text, streaming: streaming);
    final kids = <Widget>[];
    var caretUsed = false;
    for (var k = 0; k < blocks.length; k++) {
      final b = blocks[k];
      final lastBlock = k == blocks.length - 1;
      final tail = (lastBlock && trailing != null && b.kind != 'code' && b.kind != 'table' && b.kind != 'hr')
          ? trailing
          : null;
      if (tail != null) caretUsed = true;
      final live = streaming && lastBlock;
      // v0.274 SAAF JAGAH: the same air the console got. Claude's gap between paragraphs measures 22-32px
      // against 6-8px between the lines inside one; ours was 9px here (and 4px between list items), so the
      // blocks never separated. 16 / 8 puts the ratio back where the eye can use it.
      if (kids.isNotEmpty) kids.add(SizedBox(height: (b.kind == 'li' || b.kind == 'ol') ? 8 : 16));
      switch (b.kind) {
        case 'h':
          // v0.249 CLAUDE JAISA AKSHAR: sized against the 16px serif body, at Claude's heading weight 600
          final size = b.level <= 1 ? 22.0 : b.level == 2 ? 20.0 : 17.0;
          kids.add(_rich(mdInline(b.text, streaming: live), style.copyWith(fontSize: size, fontWeight: FontWeight.w600, height: 1.3), tail));
          break;
        case 'li':
        case 'ol':
          kids.add(Padding(
            padding: EdgeInsets.only(left: 4.0 + 16.0 * b.level),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              SizedBox(
                width: b.kind == 'ol' ? 24 : 16,
                child: Text(b.kind == 'ol' ? '${b.marker}.' : (b.level == 0 ? '•' : '◦'),
                    style: style.copyWith(color: C.accentSoft, fontWeight: FontWeight.w700)),
              ),
              Expanded(child: _rich(mdInline(b.text, streaming: live), style, tail)),
            ]),
          ));
          break;
        case 'quote':
          kids.add(Container(
            padding: const EdgeInsets.only(left: 10),
            decoration: const BoxDecoration(border: Border(left: BorderSide(color: Color(0x66A78BFA), width: 3))),
            child: _rich(mdInline(b.text, streaming: live), style.copyWith(color: C.muted, fontStyle: FontStyle.italic), tail),
          ));
          break;
        case 'code':
          kids.add(Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
            decoration: BoxDecoration(color: const Color(0x33000000), borderRadius: BorderRadius.circular(12),
                border: Border.all(color: C.line)),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Text(b.text, style: style.copyWith(fontFamily: 'monospace', fontSize: 14, height: 1.45)),
            ),
          ));
          break;
        case 'table':
          kids.add(SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Table(
              defaultColumnWidth: const IntrinsicColumnWidth(),
              border: TableBorder.all(color: const Color(0x26FFFFFF), width: .8, borderRadius: BorderRadius.circular(8)),
              children: [
                for (var r = 0; r < b.rows.length; r++)
                  TableRow(
                    decoration: r == 0 ? const BoxDecoration(color: Color(0x14FFFFFF)) : null,
                    children: [
                      for (var c = 0; c < b.rows[0].length; c++)
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                          child: ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 220),
                            child: _rich(mdInline(c < b.rows[r].length ? b.rows[r][c] : ''),
                                r == 0 ? style.copyWith(fontWeight: FontWeight.w600, fontSize: 14) : style.copyWith(fontSize: 14), null),
                          ),
                        ),
                    ],
                  ),
              ],
            ),
          ));
          break;
        case 'hr':
          kids.add(const Divider(height: 8, thickness: 1, color: Color(0x26FFFFFF)));
          break;
        default:
          kids.add(_rich(mdInline(b.text, streaming: live), style, tail));
      }
    }
    if (trailing != null && !caretUsed) kids.add(Text.rich(TextSpan(children: [trailing!])));
    if (kids.isEmpty) kids.add(Text.rich(TextSpan(style: style, children: trailing == null ? const [] : [trailing!])));
    final col = Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: kids);
    return selectable ? SelectionArea(child: col) : col;
  }

  Widget _rich(List<InlineSpan> spans, TextStyle s, InlineSpan? tail) =>
      Text.rich(TextSpan(style: s, children: [...spans, if (tail != null) tail]));
}
