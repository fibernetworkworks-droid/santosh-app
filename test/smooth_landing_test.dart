// v0.999.199 SMOOTH LANDING like Claude: her new message slides to the top of the chat (16 under it), the reply
// grows into the room below without moving it - even past the screen - and the hold ends when she scrolls.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/chat/hoola_chat.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

const _para = 'A line of the reply that grows down the page while she reads her own question above it.';

void main() {
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);

  testWidgets('a sent message lands at the top and stays while the reply grows', (t) async {
    t.view.physicalSize = const Size(400, 800);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final app = await _app();
    for (var i = 0; i < 6; i++) {   // history: an earlier question and a long answer
      app.feed.add(FeedItem('message', {'role': 'user', 'text': 'Earlier question $i'}));
      app.feed.add(FeedItem('message', {'role': 'assistant', 'text': List.filled(4, _para).join(' ')}));
    }
    await t.pumpWidget(MaterialApp(home: HoolaTheme(appearance: 'light',
        child: Scaffold(body: HoolaChat(app: app, onTalk: () {}, onMenu: () {})))));
    await t.pump(const Duration(milliseconds: 300));

    app.endReplayForTest();   // the chat has loaded: what comes now is live
    double topOf(Finder f) => t.getTopLeft(f).dy - t.getTopLeft(find.byType(Scrollable).first).dy;
    final mine = find.text('What is my GST due this month?');

    app.feed.add(FeedItem('message', {'role': 'user', 'text': 'What is my GST due this month?'}));
    app.notifyChange();
    for (var i = 0; i < 12; i++) { await t.pump(const Duration(milliseconds: 50)); }
    await t.pump(const Duration(milliseconds: 400));
    final y0 = topOf(mine);
    expect((y0 - 27).abs() < 4, isTrue, reason: 'landed at $y0');   // 16 + the bubble's 11 inner padding

    final reply = FeedItem('stream', {'turn': 't9', 'text': _para});
    app.feed.add(reply);
    app.notifyChange();
    for (var n = 2; n <= 30; n += 4) {   // the reply streams in, past the screen
      reply.data['text'] = List.filled(n, _para).join(' ');
      app.notifyChange();
      for (var i = 0; i < 4; i++) {   // every frame, so a frame that jumps and comes back fails too
        await t.pump(const Duration(milliseconds: 16));
        expect((topOf(mine) - y0).abs() < 1, isTrue, reason: 'moved to ${topOf(mine)} at $n');
      }
    }

    await t.drag(find.byType(Scrollable).first, const Offset(0, 300));   // she scrolls: the hold ends, the view is hers
    await t.pump(const Duration(milliseconds: 400));
    expect(topOf(mine) > y0 + 100, isTrue);

    await t.pumpWidget(const SizedBox());
    app.dispose();
  });

  testWidgets('a chat that opens with history does not land anything', (t) async {
    final app = await _app();
    app.feed.add(FeedItem('message', {'role': 'user', 'text': 'Old question'}));
    app.feed.add(FeedItem('message', {'role': 'assistant', 'text': 'Old answer'}));
    await t.pumpWidget(MaterialApp(home: HoolaTheme(appearance: 'light',
        child: Scaffold(body: HoolaChat(app: app, onTalk: () {}, onMenu: () {})))));
    await t.pump(const Duration(milliseconds: 300));
    expect(find.byKey(const ValueKey('landpad')), findsNothing);
    await t.pumpWidget(const SizedBox());
    app.dispose();
  });
}
