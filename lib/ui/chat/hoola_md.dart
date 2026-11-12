// v0.862 R3 THE CHAT (docs/HOOLA_APP_REDESIGN_PLAN.md 3a): Hoola's reply drawn the Claude way in the new design.
//
// Same parser as the old chat (md_text.dart mdBlocks / mdInline - one truth for what a reply MEANS), new drawing:
//   reply 17 Literata · headings 22 / 18 / 16 · bold 600 · links accent + underline
//   inline code = JetBrains Mono on the code colour role · code block = header (language, Copy, Expand) + body
//   tables in a full-width box that scrolls sideways · quotes with a hairline rule · list indent 16 per level
// While a reply streams, the newest few words are drawn lighter (the soft tail) and an open mark never shows.
// Every colour / size comes from hoola_theme.dart.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../hoola_theme.dart';
import '../md_text.dart';

class HoolaMd extends StatelessWidget {
  const HoolaMd(this.text, {super.key, this.streaming = false, this.selectable = false, this.compact = false});
  final String text;
  final bool streaming;
  final bool selectable;

  /// Smaller body (15 sans) for places that are not a reply: step details, notes.
  final bool compact;

  /// The last few plain words of a streaming block, drawn lighter. Only when they hold no mark of their own.
  static final _tail = RegExp(r'(\S+\s+){0,2}\S*\s*$');
  static const _marks = ['*', '_', '`', '[', ']', '~', '|', '(', ')'];

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final body = compact ? HoolaType.body(c) : HoolaType.reply(c);
    final code = HoolaType.code(c, size: compact ? 13 : 14).copyWith(backgroundColor: c.code, color: c.codeInk);
    List<InlineSpan> inline(String s, {bool live = false}) {
      if (!live) return mdInline(s, link: c.accent, codeStyle: code);
      final m = _tail.firstMatch(s);
      final tail = m?.group(0) ?? '';
      if (tail.trim().isEmpty || tail.length >= s.length || _marks.any(tail.contains)) {
        return mdInline(s, streaming: true, link: c.accent, codeStyle: code);
      }
      // a mark left open in the head (e.g. "**bold wor") must keep styling the tail: then no fade
      final head = s.substring(0, s.length - tail.length);
      final opens =
          '**'.allMatches(head).length.isOdd || '`'.allMatches(head).length.isOdd || '~~'.allMatches(head).length.isOdd;
      if (opens) return mdInline(s, streaming: true, link: c.accent, codeStyle: code);
      return [
        ...mdInline(head, streaming: true, link: c.accent, codeStyle: code),
        TextSpan(text: tail, style: TextStyle(color: c.ink.withOpacity(.42))),
      ];
    }

    final blocks = mdBlocks(text, streaming: streaming);
    final kids = <Widget>[];
    for (var k = 0; k < blocks.length; k++) {
      final b = blocks[k];
      final live = streaming && k == blocks.length - 1;
      final list = b.kind == 'li' || b.kind == 'ol';
      final prevList = k > 0 && (blocks[k - 1].kind == 'li' || blocks[k - 1].kind == 'ol');
      if (kids.isNotEmpty) kids.add(SizedBox(height: list && prevList ? 6 : (b.kind == 'h' ? 20 : 14)));
      switch (b.kind) {
        case 'h':
          final st = b.level <= 1
              ? HoolaType.replyH1(c)
              : b.level == 2
                  ? HoolaType.replyH2(c)
                  : HoolaType.replyH3(c);
          kids.add(_rich(inline(b.text, live: live), compact ? st.copyWith(fontSize: (st.fontSize ?? 16) - 2) : st));
          break;
        case 'li':
        case 'ol':
          kids.add(Padding(
            padding: EdgeInsets.only(left: 2.0 + 16.0 * b.level),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              SizedBox(
                width: b.kind == 'ol' ? 26 : 18,
                child: Text(b.kind == 'ol' ? '${b.marker}.' : (b.level == 0 ? '•' : '◦'),
                    style: body.copyWith(color: c.ink2)),
              ),
              Expanded(child: _rich(inline(b.text, live: live), body)),
            ]),
          ));
          break;
        case 'quote':
          kids.add(Container(
            padding: const EdgeInsets.only(left: 12),
            decoration: BoxDecoration(border: Border(left: BorderSide(color: c.lineStrong, width: 3))),
            child: _rich(inline(b.text, live: live), body.copyWith(color: c.ink2)),
          ));
          break;
        case 'code':
          kids.add(HoolaCodeBlock(code: b.text, lang: b.lang));
          break;
        case 'table':
          kids.add(_table(b, c, body));
          break;
        case 'hr':
          kids.add(Divider(height: 8, thickness: 1, color: c.line));
          break;
        default:
          kids.add(_rich(inline(b.text, live: live), body));
      }
    }
    if (kids.isEmpty) kids.add(const SizedBox(height: 1));
    final col = Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: kids);
    return selectable ? SelectionArea(child: col) : col;
  }

  Widget _rich(List<InlineSpan> spans, TextStyle s) => Text.rich(TextSpan(style: s, children: spans));

  Widget _table(MdBlock b, HoolaColors c, TextStyle body) {
    final cell = HoolaType.body(c);
    final cols = b.rows.isEmpty ? 0 : b.rows.map((r) => r.length).reduce((a, x) => a > x ? a : x);
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(border: Border.all(color: c.line), borderRadius: HoolaRadius.r(HoolaRadius.tile)),
      clipBehavior: Clip.antiAlias,
      child: LayoutBuilder(
          builder: (context, box) => SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: ConstrainedBox(
                  constraints: BoxConstraints(minWidth: box.maxWidth),
                  child: Table(
                    defaultColumnWidth: const IntrinsicColumnWidth(flex: 1),
                    border: TableBorder(
                        horizontalInside: BorderSide(color: c.line), verticalInside: BorderSide(color: c.line)),
                    children: [
                      for (var r = 0; r < b.rows.length; r++)
                        TableRow(
                          decoration: r == 0 ? BoxDecoration(color: c.sunk) : null,
                          children: [
                            for (var k = 0; k < cols; k++)
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                child: ConstrainedBox(
                                  constraints: const BoxConstraints(maxWidth: 240),
                                  child: _rich(
                                      mdInline(k < b.rows[r].length ? b.rows[r][k] : '',
                                          link: c.accent,
                                          codeStyle: HoolaType.code(c, size: 13)
                                              .copyWith(backgroundColor: c.code, color: c.codeInk)),
                                      r == 0 ? cell.copyWith(fontWeight: FontWeight.w600) : cell),
                                ),
                              ),
                          ],
                        ),
                    ],
                  ),
                ),
              )),
    );
  }
}

/// A code block: a header with the language, Copy and Expand, then the code (scrolls sideways, never wraps).
class HoolaCodeBlock extends StatelessWidget {
  const HoolaCodeBlock({super.key, required this.code, this.lang = ''});
  final String code;
  final String lang;

  Future<void> _copy(BuildContext context) async {
    await Clipboard.setData(ClipboardData(text: code));
    HapticFeedback.lightImpact();
    if (context.mounted) {
      ScaffoldMessenger.maybeOf(context)
          ?.showSnackBar(const SnackBar(content: Text('Code copied'), duration: Duration(seconds: 2)));
    }
  }

  void _expand(BuildContext context) => showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        useSafeArea: true,
        builder: (ctx) {
          final c = HoolaColors.of(ctx);
          return FractionallySizedBox(
            heightFactor: .92,
            child: Column(children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 4, 8, 8),
                child: Row(children: [
                  Expanded(child: Text(lang.isEmpty ? 'Code' : lang, style: HoolaType.title(c))),
                  IconButton(
                      tooltip: 'Copy', onPressed: () => _copy(ctx), icon: Icon(Icons.copy_rounded, color: c.ink2)),
                  IconButton(
                      tooltip: 'Close',
                      onPressed: () => Navigator.pop(ctx),
                      icon: Icon(Icons.close_rounded, color: c.ink2)),
                ]),
              ),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: SelectableText(code,
                        style: HoolaType.code(c, size: 14).copyWith(color: c.codeInk, height: 1.55)),
                  ),
                ),
              ),
            ]),
          );
        },
      );

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
          color: c.code, borderRadius: HoolaRadius.r(HoolaRadius.tile), border: Border.all(color: c.line)),
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Container(
          height: 36,
          padding: const EdgeInsets.only(left: 12),
          decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
          child: Row(children: [
            Expanded(child: Text(lang.isEmpty ? 'code' : lang, style: HoolaType.label(c).copyWith(color: c.ink3))),
            _HeadButton(icon: Icons.copy_rounded, label: 'Copy code', onTap: () => _copy(context)),
            _HeadButton(
                icon: Icons.open_in_full_rounded, label: 'Open the code full screen', onTap: () => _expand(context)),
          ]),
        ),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.all(12),
          child: Text(code, style: HoolaType.code(c, size: 13).copyWith(color: c.codeInk, height: 1.55)),
        ),
      ]),
    );
  }
}

class _HeadButton extends StatelessWidget {
  const _HeadButton({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: label,
        excludeSemantics: true,
        child: InkWell(
          onTap: onTap,
          child: SizedBox(width: 40, height: 36, child: Icon(icon, size: 16, color: HoolaColors.of(context).ink3)),
        ),
      );
}
