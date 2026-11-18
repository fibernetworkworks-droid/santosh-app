// HOOLA THREAD KIT (lib/ui/chat/hoola_thread.dart): the one conversation every chat panel of the app draws.
// History is whole; a reply that arrives while she watches lands word by word at the Hoola chat's pace; the
// working row shows the real step; the actions wait for the last word.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/chat/hoola_thread.dart';
import 'package:santosh/ui/hoola_theme.dart';

Widget _host(Widget w) => MaterialApp(home: HoolaTheme(appearance: 'light', child: Scaffold(body: w)));

void main() {
  test('the kit runs at the Hoola chat pace', () {
    expect(kThreadMsPerWord, 34);
    expect(kThreadSoftMs, 460);
  });

  testWidgets('history is drawn whole; a reply that arrives later lands word by word', (t) async {
    final reply = List.generate(60, (i) => 'word$i').join(' ');
    var msgs = <HoolaMsg>[
      const HoolaMsg(id: '1', text: 'old question', mine: true),
      const HoolaMsg(id: '2', text: 'old answer stays whole'),
    ];
    var working = false;
    late StateSetter setS;
    await t.pumpWidget(_host(StatefulBuilder(builder: (c, s) {
      setS = s;
      return HoolaThreadView(messages: msgs, working: working, label: 'Reading the sheet');
    })));
    await t.pump(const Duration(milliseconds: 50));
    expect(find.text('old question'), findsOneWidget);
    expect(find.textContaining('old answer stays whole', findRichText: true), findsOneWidget);
    expect(find.byType(HoolaReplyActions), findsOneWidget);

    setS(() {
      msgs = [...msgs, const HoolaMsg(id: '3', text: 'new question', mine: true)];
      working = true;
    });
    await t.pump(const Duration(milliseconds: 50));
    expect(find.byType(HoolaWorkingRow), findsOneWidget);
    expect(find.text('Reading the sheet'), findsOneWidget);
    expect(find.byType(HoolaReplyActions), findsNothing);

    setS(() {
      msgs = [...msgs, HoolaMsg(id: '4', text: reply)];
      working = false;
    });
    await t.pump();
    await t.pump(const Duration(milliseconds: 120));
    expect(find.byType(HoolaWorkingRow), findsNothing);
    expect(find.textContaining('word0', findRichText: true), findsOneWidget);
    expect(find.textContaining('word59', findRichText: true), findsNothing, reason: 'the last word has not landed yet');
    expect(find.byType(HoolaReplyActions), findsNothing, reason: 'the actions wait for the last word');
    for (var i = 0; i < 45; i++) {
      await t.pump(const Duration(milliseconds: 100));
    }
    expect(find.textContaining('word59', findRichText: true), findsOneWidget);
    expect(find.byType(HoolaReplyActions), findsOneWidget);
    await t.pumpWidget(const SizedBox());   // the screen is gone: its clock and tickers stop with it
  });

  testWidgets('inside an old dark screen the kit reads the dark colours', (t) async {
    late HoolaColors seen;
    await t.pumpWidget(MaterialApp(
        home: Scaffold(
            body: HoolaOnDark(child: Builder(builder: (c) {
      seen = HoolaColors.of(c);
      return const HoolaHerBubble('hello');
    })))));
    expect(seen.dark, true);
    expect(find.text('hello'), findsOneWidget);
  });
}
