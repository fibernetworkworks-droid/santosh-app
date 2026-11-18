// v0.891 CLAUDE JAISA LIKHAI: a reply table that is wider than the phone says so (a fade on the side with more), number
// columns sit right in even-width digits, links are underlined at the text's own weight, and a capitals title on
// the "learned this task" card reads as a sentence.
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/chat/hoola_md.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/md_text.dart';
import 'package:santosh/ui/procedures_screen.dart';

Widget _host(Widget w, {double width = 360}) => MaterialApp(
      home: HoolaTheme(
        appearance: 'light',
        child: Scaffold(body: Center(child: SizedBox(width: width, child: SingleChildScrollView(child: w)))),
      ),
    );

const _wide = '''| Source | Revenue | Share of total revenue |
|---|---|---|
| **Google Services** | \$102.35B | 80.2% |
| — Search & other ads | \$63.35B | 49.7% |
| Google Cloud + Other Bets | \$25.23B | 19.8% |''';

void main() {
  test('number columns: figures only, the header does not count', () {
    final rows = [
      ['Source', 'Revenue', 'Share', 'Note'],
      ['iPhone', '\$196.5B', '54%', 'hardware'],
      ['Services', '**\$91.73B**', '~25%', ''],
      ['Mac', 'Rs 1,200', '(3.4)', 'flat'],
    ];
    expect(HoolaMdTable.numberColumns(rows), {1, 2});
    for (final n in ['\$102.35B', '54%', '~50%', 'Rs 1,200', '₹4.5 cr', '1,250', '-3.2%', '12x']) {
      expect(HoolaMdTable.isNumber(n), true, reason: n);
    }
    for (final w in ['Q3 2026 total', 'iPhone 17', 'n/a', '']) {
      expect(HoolaMdTable.isNumber(w), false, reason: w);
    }
  });

  testWidgets('a table wider than the phone shows a fade on the right, then on the left once scrolled', (t) async {
    await t.pumpWidget(_host(const HoolaMd(_wide)));
    await t.pumpAndSettle();
    final fades = find.descendant(of: find.byType(HoolaMdTable), matching: find.byType(AnimatedOpacity));
    expect(fades, findsNWidgets(2));
    expect(t.widget<AnimatedOpacity>(fades.at(0)).opacity, 0);   // left: nothing hidden yet
    expect(t.widget<AnimatedOpacity>(fades.at(1)).opacity, 1);   // right: more columns
    await t.drag(find.byType(HoolaMdTable), const Offset(-800, 0));
    await t.pumpAndSettle();
    expect(t.widget<AnimatedOpacity>(fades.at(0)).opacity, 1);
    expect(t.widget<AnimatedOpacity>(fades.at(1)).opacity, 0);
  });

  testWidgets('a table that fits shows no fade, and figures sit right in even-width digits', (t) async {
    await t.pumpWidget(_host(const HoolaMd('| Item | Price |\n|---|---|\n| Tea | Rs 20 |\n| Coffee | Rs 120 |'),
        width: 600));
    await t.pumpAndSettle();
    final fades = find.descendant(of: find.byType(HoolaMdTable), matching: find.byType(AnimatedOpacity));
    expect(fades.evaluate().every((e) => (e.widget as AnimatedOpacity).opacity == 0), true);
    final price = t.widgetList<Text>(find.byType(Text)).firstWhere((x) => x.textSpan?.toPlainText() == 'Rs 120');
    expect(price.textAlign, TextAlign.right);
    expect(price.textSpan!.style!.fontFeatures, contains(const FontFeature.tabularFigures()));
    final item = t.widgetList<Text>(find.byType(Text)).firstWhere((x) => x.textSpan?.toPlainText() == 'Coffee');
    expect(item.textAlign, TextAlign.left);
  });

  test('links are underlined at the text weight, not bold', () {
    final spans = mdInline('see [apple.com](https://apple.com) now');
    final link = spans.whereType<TextSpan>().firstWhere((s) => s.recognizer is TapGestureRecognizer);
    expect(link.style!.decoration, TextDecoration.underline);
    expect(link.style!.fontWeight, isNull);
  });

  testWidgets('blocks breathe like the console: 16 between paragraphs, 24 above a heading, 8 under it', (t) async {
    await t.pumpWidget(_host(const HoolaMd('First paragraph.\n\nSecond paragraph.\n\n## Part two\n\nUnder the heading.')));
    final gaps = t
        .widgetList<SizedBox>(find.descendant(of: find.byType(HoolaMd), matching: find.byType(SizedBox)))
        .where((b) => b.width == null && b.child == null)
        .map((b) => b.height)
        .toList();
    expect(gaps, [16, 24, 8]);
  });

  // v0.892 CLAUDE KE AKSHAR: claude.ai thins its reply in dark mode (360 / 530); the phone uses Literata cut at those
  // weights, and her chat font choice changes only the reply (headings follow, code stays mono).
  test('the reply font follows the mode and her chat font', () {
    ChatFont.current = 'serif';
    expect(HoolaType.reply(HoolaColors.light).fontFamily, 'Literata');
    expect(HoolaType.reply(HoolaColors.darkSet).fontFamily, 'Literata Dark');
    expect(HoolaType.replyH1(HoolaColors.darkSet).fontFamily, 'Literata Dark');
    ChatFont.current = 'sans';
    expect(HoolaType.reply(HoolaColors.darkSet).fontFamily, HoolaFont.sans);
    ChatFont.current = 'dyslexic';
    expect(HoolaType.reply(HoolaColors.light).fontFamily, 'OpenDyslexic');
    expect(HoolaType.replyH2(HoolaColors.light).fontWeight, FontWeight.w700);
    ChatFont.current = 'system';
    expect(HoolaType.reply(HoolaColors.light).fontFamily, 'Roboto');
    expect(HoolaType.code(HoolaColors.light).fontFamily, HoolaFont.mono);
    ChatFont.current = 'serif';
  });

  testWidgets('a `term` reads like Claude: muted red on a faint tint with room each side, not a blue link', (t) async {
    await t.pumpWidget(_host(const HoolaMd('Check `drive.google.com` now')));
    final rich = t.widgetList<RichText>(find.byType(RichText)).firstWhere((r) => r.text.toPlainText().contains('drive'));
    TextSpan? term;
    rich.text.visitChildren((s) {
      if (s is TextSpan && s.text == 'drive.google.com') term = s;
      return true;
    });
    expect(term, isNotNull);
    expect(term!.style!.color, HoolaColors.light.codeTerm);
    expect(term!.style!.color, isNot(HoolaColors.light.accent));
    expect(term!.style!.fontSize, 13.5);
    expect(rich.text.toPlainText(), contains('\u00A0drive.google.com\u00A0'));
    // a plain paragraph gets no padding characters
    expect(mdInline('no code here').length, 1);
  });

  test('a capitals title reads as a sentence; business words and normal titles stay', () {
    expect(sentenceCase('FROM WHERE THEY EARN MONEY'), 'From where they earn money');
    expect(sentenceCase('MAKE GST REPORT PDF'), 'Make GST report PDF');
    expect(sentenceCase('Apple vs Alphabet revenue'), 'Apple vs Alphabet revenue');
    expect(sentenceCase('GST'), 'GST');
  });
}
