// v0.889 every chat its own session on the phone, as on the web console: the drawer shows which chats work and
// which got a reply while she was elsewhere, and her unfinished words stay with the chat she typed them in.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/shell/hoola_shell.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

void main() {
  testWidgets('drawer: a working chat spins, a chat with a new reply gets the dot, the open chat never does', (t) async {
    final sem = t.ensureSemantics();
    final app = await _app();
    app.conversationId = 'open';
    app.chatList = [
      {'id': 'open', 'title': 'Open chat'},
      {'id': 'busy', 'title': 'GST summary'},
      {'id': 'news', 'title': 'Website'},
      {'id': 'quiet', 'title': 'Hello'},
    ];
    app.busyChats.add('busy');
    app.unreadChats.addAll({'news', 'open'});
    await t.pumpWidget(MaterialApp(
      home: HoolaTheme(
        appearance: 'light',
        child: Scaffold(
          body: HoolaDrawer(app: app, onNewChat: () {}, onOpenChat: (_) {}, onCalls: () {}, onMemory: () {}, onSettings: () {}),
        ),
      ),
    ));
    await t.pump();
    expect(find.bySemanticsLabel(RegExp(r'^GST summary, working')), findsOneWidget);
    expect(find.bySemanticsLabel(RegExp(r'^Website, new reply')), findsOneWidget);
    expect(find.bySemanticsLabel(RegExp(r'^Open chat, new reply')), findsNothing);
    expect(find.bySemanticsLabel(RegExp('^Hello, ')), findsNothing);
    app.dispose();
    sem.dispose();
  });

  testWidgets('her unfinished words stay with their chat', (t) async {
    final app = await _app();
    app.saveDraft('a', 'Send the Diwali offer to');
    app.saveDraft('b', '');
    expect(app.draftFor('a'), 'Send the Diwali offer to');
    expect(app.draftFor('b'), '');
    expect(app.draftFor(null), '');
    await t.pump(const Duration(milliseconds: 500));   // the phone copy is written a moment later
    await t.pump();
    await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 20)));
    final p = await SharedPreferences.getInstance();
    expect(p.getString('draft.a'), 'Send the Diwali offer to');
    expect(p.getString('draft.b'), isNull);
    app.dispose();
  });
}
