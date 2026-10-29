// v0.222 SAAF CHAT: the phone's markdown renderer (lib/ui/md_text.dart). Run: flutter test test/md_text_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/md_text.dart';

String spansText(List<InlineSpan> spans) => spans.map((s) => s.toPlainText()).join();

bool hasStyle(List<InlineSpan> spans, bool Function(TextStyle s) want) {
  for (final s in spans) {
    if (s is! TextSpan) continue;
    if (s.style != null && want(s.style!)) return true;
    if (hasStyle(s.children ?? const [], want)) return true;
  }
  return false;
}

void main() {
  test('blocks: paragraph, heading, lists, code, quote, table, rule', () {
    const src = '# Aaj ka plan\n\nPehle yeh.\nPhir woh.\n\n- ek\n- do\n  - andar\n1. pehla\n2) doosra\n\n'
        '```dart\nprint(1);\n```\n> yaad rakho\n\n| Naam | Rs |\n|---|---|\n| Atta | 450 |\n\n---\nAakhri';
    final b = mdBlocks(src);
    expect(b.map((x) => x.kind).toList(),
        ['h', 'p', 'li', 'li', 'li', 'ol', 'ol', 'code', 'quote', 'table', 'hr', 'p']);
    expect(b[0].text, 'Aaj ka plan');
    expect(b[1].text, 'Pehle yeh.\nPhir woh.');
    expect(b[4].level, 1);
    expect(b[6].marker, '2');
    expect(b[7].text, 'print(1);');
    expect(b[7].lang, 'dart');
    expect(b[9].rows, [
      ['Naam', 'Rs'],
      ['Atta', '450']
    ]);
  });

  test('inline: bold, italic, code, strike, link, bare url', () {
    final s = mdInline('**Ho gaya** _abhi_ `x=1` ~~purana~~ [site](https://hoola.in) https://example.com/a');
    final t = spansText(s);
    expect(t.contains('**'), false);
    expect(t.contains('`'), false);
    expect(t.contains('Ho gaya'), true);
    expect(t.contains('site'), true);
    expect(t.contains('🔗 example.com'), true);
    expect(hasStyle(s, (st) => st.fontWeight == FontWeight.w600), true);   // v0.248 Claude's bold is 600
    expect(hasStyle(s, (st) => st.fontStyle == FontStyle.italic), true);
  });

  test('snake_case and math stay as written', () {
    expect(spansText(mdInline('file_id aur order_id do')), 'file_id aur order_id do');
    expect(spansText(mdInline('2 * 3 = 6')), '2 * 3 = 6');
  });

  test('streaming never shows a half-written mark', () {
    final s = mdInline('Total **450 rup', streaming: true);
    expect(spansText(s), 'Total 450 rup');
    expect(hasStyle(s, (st) => st.fontWeight == FontWeight.w600), true);   // v0.248 Claude's bold is 600
    expect(spansText(mdInline('dekho `fla', streaming: true)), 'dekho fla');
    expect(spansText(mdInline('yeh *', streaming: true)), 'yeh ');
    expect(spansText(mdInline('yahan [Hoola site', streaming: true)), 'yahan Hoola site');
    expect(spansText(mdInline('yahan [Hoola](https://hoo', streaming: true)), 'yahan Hoola');
    // a finished message keeps an unmatched mark as written
    expect(spansText(mdInline('Total **450 rup')), 'Total **450 rup');
  });

  test('streaming hides a lone marker line and an unfinished table header', () {
    expect(mdBlocks('Achha\n##', streaming: true).map((b) => b.kind), ['p']);
    expect(mdBlocks('Achha\n-', streaming: true).map((b) => b.kind), ['p']);
    expect(mdBlocks('Dekho\n| Naam | Rs |', streaming: true).map((b) => b.kind), ['p']);
    expect(mdBlocks('Dekho\n| Naam | Rs |\n|---|---|', streaming: true).map((b) => b.kind), ['p', 'table']);
    // an open code fence is already a code block while it streams
    expect(mdBlocks('```\nprint(', streaming: true).single.kind, 'code');
  });

  test('plain text for copy / quote', () {
    expect(mdPlain('## Plan\n- **ek** kaam\n1. [site](https://a.in)'), 'Plan\n• ek kaam\n1. site (https://a.in)');
  });

  testWidgets('MdText renders with the caret and no raw marks', (t) async {
    await t.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: MdText('**Ho gaya**\n- ek', style: TextStyle(fontSize: 15), streaming: true,
            trailing: WidgetSpan(child: SizedBox(width: 4, height: 4, key: Key('caret')))),
      ),
    ));
    expect(find.textContaining('**'), findsNothing);
    expect(find.byKey(const Key('caret')), findsOneWidget);
  });
}
