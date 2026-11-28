// v0.999.203 EVERY CHAT LIKE CLAUDE: the tool chats on the shared thread kit (Hoola Computer, Hoola Auto ...) land her
// sent message at the top like the main chat - 16 under it, room kept below, held while the reply grows past the screen,
// hers again once she drags. History never lands.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/ui/chat/hoola_thread.dart';
import 'package:santosh/ui/hoola_theme.dart';

const _para = 'A line of the reply that grows down the page while she reads her own question above it.';

Widget _host(List<HoolaMsg> msgs) => MaterialApp(
    home: HoolaTheme(appearance: 'light', child: Scaffold(body: HoolaThreadView(messages: msgs, threadKey: 'k'))));

void main() {
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);

  testWidgets('a sent message lands at the top of a tool chat and stays while the reply grows', (t) async {
    t.view.physicalSize = const Size(400, 800);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final msgs = <HoolaMsg>[
      for (var i = 0; i < 6; i++) ...[
        HoolaMsg(id: 'q$i', text: 'Earlier question $i', mine: true),
        HoolaMsg(id: 'a$i', text: List.filled(4, _para).join(' ')),
      ],
    ];
    await t.pumpWidget(_host(List.of(msgs)));
    await t.pump(const Duration(milliseconds: 300));
    expect(find.byKey(const ValueKey('landroom')), findsNothing, reason: 'history does not land');

    double topOf(Finder f) => t.getTopLeft(f).dy - t.getTopLeft(find.byType(Scrollable).first).dy;
    final mine = find.text('Which invoices are still unpaid?');
    msgs.add(const HoolaMsg(id: 'q9', text: 'Which invoices are still unpaid?', mine: true));
    await t.pumpWidget(_host(List.of(msgs)));
    for (var i = 0; i < 20; i++) { await t.pump(const Duration(milliseconds: 50)); }
    final y0 = topOf(mine);
    expect((y0 - 27).abs() < 4, isTrue, reason: 'landed at $y0');   // 16 + the bubble's 11 inner padding

    for (var n = 2; n <= 30; n += 4) {   // the reply arrives and grows, past the screen
      final now = [...msgs, HoolaMsg(id: 'a9', text: List.filled(n, _para).join(' '))];
      await t.pumpWidget(_host(now));
      for (var i = 0; i < 4; i++) {
        await t.pump(const Duration(milliseconds: 16));
        expect((topOf(mine) - y0).abs() < 1, isTrue, reason: 'moved to ${topOf(mine)} at $n');
      }
    }
    await t.pumpAndSettle(const Duration(milliseconds: 100));

    await t.drag(find.byType(Scrollable).first, const Offset(0, 300));   // she scrolls: the view is hers
    await t.pump(const Duration(milliseconds: 400));
    expect(topOf(mine) > y0 + 100, isTrue);
  });

  test('her message reads 16 / 1.4 like the main chat, in the kit and in Hoola Code', () {
    expect(File('lib/ui/chat/hoola_thread.dart').readAsStringSync(), contains('bodyLarge(c).copyWith(height: 1.4)'));
    expect(File('lib/ui/code/code_session.dart').readAsStringSync(), contains('_lander.land()'));
    expect(File('lib/ui/chat/hoola_md.dart').readAsStringSync(), contains('fontSize: reply ? 28 : null, height: reply ? 1.3'));
  });
}
