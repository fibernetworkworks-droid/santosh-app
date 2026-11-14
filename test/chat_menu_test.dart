// v0.908 CHAT MENU (owner: "EVERY CHAT NAME SHOULD BE EDITED, DELETED SAME AS CONSOLE HAS"): the console's chat menu on
// the phone - the same server calls (PATCH title / pinned / archived, DELETE), the list changing at once, a ⋯ beside
// every chat, hold to open, Delete asks first, pinned chats in their own group, the Archive list.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/api.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/shell/hoola_shell.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// A server that records every call and answers like the real one.
Future<(HttpServer, List<String>)> _server() async {
  final seen = <String>[];
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((req) async {
    final body = await utf8.decoder.bind(req).join();
    seen.add('${req.method} ${req.uri.path}${req.uri.query.isEmpty ? '' : '?${req.uri.query}'} $body'.trim());
    req.response.headers.contentType = ContentType.json;
    if (req.method == 'GET' && req.uri.path == '/api/conversations') {
      final archived = req.uri.queryParameters['archived'] == 'true';
      req.response.write(jsonEncode({
        'conversations': archived
            ? [{'id': 'old', 'title': 'Old plan', 'archived': true}]
            : [{'id': 'a', 'title': 'Renamed GST', 'pinned': true}, {'id': 'b', 'title': 'Diwali offer'}],
      }));
    } else {
      req.response.write(jsonEncode({'ok': true}));
    }
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

  test('rename, pin, archive, delete send the console\'s own calls and change the list at once', () async {
    final (server, seen) = await _server();
    final app = await _app();
    app.api = Api('http://127.0.0.1:${server.port}', 'k');
    app.chatList = [
      {'id': 'a', 'title': 'Monthly GST Summary'},
      {'id': 'b', 'title': 'Diwali offer'},
      {'id': 'c', 'title': 'Haan toh?'},
    ];
    expect(await app.renameChat('a', '  Renamed GST  '), isNull);
    expect(app.chatList.first['title'], 'Renamed GST');
    expect(await app.pinChat('a', true), isNull);
    expect(await app.archiveChat('c', true), isNull);
    expect(await app.deleteChat('b'), isNull);
    expect(seen, containsAllInOrder([
      'PATCH /api/conversations/a {"title":"Renamed GST"}',
      'PATCH /api/conversations/a {"pinned":true}',
      'PATCH /api/conversations/c {"archived":true}',
      'DELETE /api/conversations/b',
    ]));
    expect(await app.renameChat('a', '   '), isNotNull, reason: 'an empty name is refused before any call');
    final arch = await app.archivedChats();
    expect(arch.single['title'], 'Old plan');
    expect(seen.any((s) => s.startsWith('GET /api/conversations?archived=true')), isTrue);
    app.dispose();
    await server.close(force: true);
  });

  testWidgets('the drawer: pinned group, a ⋯ beside every chat, hold to open, Delete asks first', (t) async {
    final app = await _app();
    app.chatList = [
      {'id': 'p', 'title': 'Monthly GST Summary', 'pinned': true},
      {'id': 'a', 'title': 'Image Generation Capabilities'},
      {'id': 'b', 'title': 'Top 100 AI Repos PDF Report'},
    ];
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
            onArchive: () {},
          ),
        ),
      ),
    ));
    await t.pump();
    expect(find.text('Pinned'), findsOneWidget);
    expect(find.text('Recents'), findsOneWidget);
    expect(find.text('Archive'), findsOneWidget, reason: 'the Archive list is in More');
    expect(find.bySemanticsLabel(RegExp('^Chat options: ')), findsNWidgets(3), reason: 'a ⋯ beside every chat');
    expect(t.getTopLeft(find.text('Monthly GST Summary')).dy, lessThan(t.getTopLeft(find.text('Recents')).dy),
        reason: 'pinned above Recents');

    await t.tap(find.bySemanticsLabel('Chat options: Image Generation Capabilities'));
    await t.pumpAndSettle();
    for (final w in ['Pin', 'Rename', 'Compact chat', 'Archive', 'Delete']) {
      expect(find.text(w), findsWidgets, reason: w);
    }
    await t.tap(find.text('Delete').last);
    await t.pumpAndSettle();
    expect(find.text('Delete "Image Generation Capabilities"?'), findsOneWidget, reason: 'Delete asks first');
    expect(find.text('It leaves the chat list, search and its link.'), findsOneWidget);
    await t.tap(find.text('Cancel'));
    await t.pumpAndSettle();
    expect(app.chatList.length, 3, reason: 'Cancel deletes nothing');

    await t.longPress(find.text('Monthly GST Summary'));
    await t.pumpAndSettle();
    expect(find.text('Unpin'), findsOneWidget, reason: 'hold the chat = the same menu; a pinned chat offers Unpin');
    await t.tap(find.text('Rename'));
    await t.pumpAndSettle();
    expect(find.text('Rename chat'), findsOneWidget);
    expect(find.widgetWithText(TextField, 'Monthly GST Summary'), findsOneWidget, reason: 'the old name is in the box');
    await t.tap(find.text('Cancel'));
    await t.pumpAndSettle();
    app.dispose();
  });
}
