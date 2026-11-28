// The "Your apps" top of the Connect page (the Connections board): counts, paused, needs you, the Google card.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/shell/hoola_connect.dart';
import 'package:shared_preferences/shared_preferences.dart';

Map<String, dynamic> _a(String k, String n, String st) =>
    {'toolkit': k, 'name': n, 'line': '$n work', 'group': 'mail', 'group_name': 'Mail & chat', 'status': st, 'tools': 12};

Map<String, dynamic> _home() => {
      'configured': true,
      'total': 1600,
      'mine': [_a('slack', 'Slack', 'ready'), _a('notion', 'Notion', 'pending')],
      'featured': const [],
      'groups': [
        {'id': 'mail', 'name': 'Mail & chat', 'count': 140, 'connected': 1, 'top': [_a('slack', 'Slack', 'ready')]},
      ],
    };

Map<String, dynamic> _google() => {
      'accounts': [
        {'email': 'me@example.com', 'state': 'expired', 'first': true, 'apps': ['calendar']},
        {'email': 'work@example.com', 'state': 'ok', 'first': false, 'apps': ['gmail']},
      ],
      'apps': [
        {'key': 'gmail', 'name': 'Gmail', 'state': 'ok', 'group': 'core'},
        {'key': 'calendar', 'name': 'Calendar', 'state': 'expired', 'group': 'core'},
        {'key': 'drive', 'name': 'Drive', 'state': 'none', 'group': 'core'},
      ],
    };

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true, 'appearance': 'light'});
  return Santosh.load();
}

void main() {
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);

  test('the line under the Google logos', () {
    expect(connectGoogleLine(null), 'Checking Google…');
    expect(connectGoogleLine(null, failed: true), 'Google could not be checked right now');
    expect(connectGoogleLine(const {}), 'Not connected yet - tap to connect');
    expect(connectGoogleLine(_google()), '1 working · Calendar needs you');
    expect(
        connectGoogleLine({
          'apps': [
            {'key': 'gmail', 'state': 'expired'},
            {'key': 'drive', 'state': 'expired'},
          ]
        }),
        '2 apps need you');
  });

  testWidgets('counts, paused, needs you, the Google card and her other apps', (t) async {
    t.view.physicalSize = const Size(1170, 6000);
    t.view.devicePixelRatio = 3;
    addTearDown(t.view.reset);
    final app = await _app();
    HoolaConnectDebug.home = _home();
    HoolaConnectDebug.google = _google();
    HoolaConnectDebug.summary = {
      'month': {'total': 12, 'done': 10, 'asked': 2, 'failed': 0, 'paused': 0},
      'week': const {},
      'last': const {},
      'paused': true,
    };
    await t.pumpWidget(MaterialApp(
        home: HoolaTheme(appearance: 'light', child: Scaffold(body: HoolaConnect(app: app, onMore: () {})))));
    await t.pumpAndSettle();
    expect(find.text('Your apps'), findsOneWidget);
    expect(find.text('2 connected · 12 actions this month'), findsOneWidget);   // Gmail + Slack
    expect(find.text('Every app is paused'), findsOneWidget);
    expect(find.text('me@example.com needs you'), findsOneWidget);
    expect(find.text('Notion needs you'), findsOneWidget);
    expect(find.text('Fix'), findsNWidgets(2));
    expect(find.text('2 accounts'), findsOneWidget);
    expect(find.text('1 working · Calendar needs you'), findsOneWidget);
    expect(find.text('Other apps'), findsOneWidget);
    expect(find.text('Find an app'), findsWidgets);
    await t.tap(find.bySemanticsLabel('Notion, not connected yet'));
    await t.pumpAndSettle();
    expect(find.text('What Hoola will do'), findsOneWidget);
    HoolaConnectDebug.home = null;
    HoolaConnectDebug.google = null;
    HoolaConnectDebug.summary = null;
    app.dispose();
  });
}
