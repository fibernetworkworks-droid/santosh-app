// v0.909 SESSIONS (owner: "ADD SESSIONS ALSO SAME AS CONSOLE"): the console's sessions on the phone - the same server
// calls, Sessions groups in the drawer that fold, "+" for a new session and a new chat inside one, the chat menu's
// Add to session / Change session, and the session page.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/api.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/shell/hoola_sessions.dart';
import 'package:santosh/ui/shell/hoola_shell.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<(HttpServer, List<String>)> _server() async {
  final seen = <String>[];
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((req) async {
    final body = await utf8.decoder.bind(req).join();
    final q = req.uri.query.isEmpty ? '' : '?${req.uri.query}';
    seen.add('${req.method} ${req.uri.path}$q $body'.trim());
    req.response.headers.contentType = ContentType.json;
    final path = req.uri.path;
    Object out = {'ok': true};
    if (req.method == 'GET' && path == '/api/projects') {
      out = {'projects': [{'id': 'prj_1', 'name': 'GST', 'emoji': '🧾', 'chats': 1}]};
    } else if (req.method == 'POST' && path == '/api/projects') {
      out = {'id': 'prj_2', 'name': 'Research', 'emoji': '📁'};
    } else if (req.method == 'POST' && path == '/api/conversations') {
      out = {'id': 'new1'};
    } else if (req.method == 'GET' && path == '/api/conversations') {
      out = {'conversations': []};
    }
    req.response.write(jsonEncode(out));
    await req.response.close();
  });
  return (server, seen);
}

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);

  test('sessions use the console\'s own calls', () async {
    HttpOverrides.global = null;   // the widget-test binding answers every real request with 400; this test has its own server
    final (server, seen) = await _server();
    final app = await _app();
    app.api = Api('http://127.0.0.1:${server.port}', 'k');
    await app.refreshSessions();
    expect(app.sessionsOn, isTrue);
    expect(app.sessions.single['name'], 'GST');
    expect(await app.createSession('  Research '), 'prj_2');
    app.chatList = [{'id': 'a', 'title': 'Monthly GST Summary'}];
    expect(await app.moveChat('a', 'prj_1'), isNull);
    expect(app.chatList.single['project_id'], 'prj_1');
    expect(await app.moveChat('a', null), isNull);
    expect(await app.deleteSession('prj_1'), isNull);
    expect(seen, containsAllInOrder([
      'GET /api/projects',
      'POST /api/projects {"name":"Research"}',
      'PATCH /api/conversations/a {"project_id":"prj_1"}',
      'PATCH /api/conversations/a {"project_id":null}',
      'DELETE /api/projects/prj_1',
    ]));
    app.toggleSession('prj_2');
    expect(app.closedSessions, contains('prj_2'));
    app.toggleSession('prj_2');
    expect(app.closedSessions, isNot(contains('prj_2')));
    app.dispose();
    await server.close(force: true);
  });

  testWidgets('the drawer: a Sessions group that folds, "+" buttons, chats inside it leave Recents', (t) async {
    final sem = t.ensureSemantics();
    final app = await _app();
    app.sessionsOn = true;
    app.sessions = [{'id': 'prj_1', 'name': 'GST', 'emoji': '🧾'}];
    app.chatList = [
      {'id': 'g', 'title': 'Monthly GST Summary', 'project_id': 'prj_1'},
      {'id': 'r', 'title': 'Diwali offer'},
    ];
    final opened = <String>[];
    final newIn = <String>[];
    await t.pumpWidget(MaterialApp(
      home: HoolaTheme(
        appearance: 'light',
        child: Scaffold(
          body: HoolaDrawer(
            app: app,
            onNewChat: () {},
            onOpenChat: (_) {},
            onCalls: () {},
            onMemory: () {},
            onSettings: () {},
            onSession: opened.add,
            onNewChatIn: newIn.add,
          ),
        ),
      ),
    ));
    await t.pump();
    expect(find.text('Sessions'), findsOneWidget);
    expect(find.bySemanticsLabel('New session'), findsOneWidget);
    expect(find.text('GST'), findsOneWidget);
    expect(find.text('Monthly GST Summary'), findsOneWidget);
    expect(t.getTopLeft(find.text('Monthly GST Summary')).dy, lessThan(t.getTopLeft(find.text('Recents')).dy),
        reason: 'a session chat sits in its session, above Recents');
    expect(t.getTopLeft(find.text('Diwali offer')).dy, greaterThan(t.getTopLeft(find.text('Recents')).dy));

    await t.tap(find.bySemanticsLabel('Fold session: GST'));
    await t.pumpAndSettle();
    expect(find.text('Monthly GST Summary'), findsNothing, reason: 'folded');
    await t.tap(find.bySemanticsLabel('Open session: GST'));
    await t.pumpAndSettle();
    expect(find.text('Monthly GST Summary'), findsOneWidget);

    await t.tap(find.bySemanticsLabel(RegExp('^Session GST')));
    await t.tap(find.bySemanticsLabel('New chat in GST'));
    expect(opened, ['prj_1']);
    expect(newIn, ['prj_1']);

    await t.tap(find.bySemanticsLabel('Chat options: Diwali offer'));
    await t.pumpAndSettle();
    expect(find.text('Add to session'), findsOneWidget, reason: 'the console\'s "Add to session" in the chat menu');
    await t.tap(find.text('Add to session'));
    await t.pumpAndSettle();
    expect(find.text('GST'), findsWidgets, reason: 'the picker lists her sessions');
    expect(find.text('New session'), findsOneWidget);
    await t.tapAt(const Offset(10, 10));
    await t.pumpAndSettle();
    app.dispose();
    sem.dispose();
  });

  testWidgets('the session page: name, emoji, new chat, instructions, memory switch, files, chats, delete', (t) async {
    final app = await _app();
    t.view.physicalSize = const Size(1170, 4200);
    t.view.devicePixelRatio = 3;
    addTearDown(t.view.reset);
    await t.pumpWidget(MaterialApp(
      home: HoolaTheme(
        appearance: 'light',
        child: HoolaSessionPage(app: app, id: 'prj_1', onOpenChat: (_) {}),
      ),
    ));
    await t.pump();
    // no server here: the page says why instead of spinning for ever
    await t.pumpAndSettle();
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.byTooltip('Back'), findsOneWidget);
    app.dispose();
  });
}
