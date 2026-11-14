// v0.901 CONNECT: only Composio apps, in ten groups; the home, a group page and the app sheet.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/shell/hoola_connect.dart';
import 'package:shared_preferences/shared_preferences.dart';

Map<String, dynamic> _a(String k, String n, String g, String st) =>
    {'toolkit': k, 'name': n, 'line': '$n work', 'group': g, 'group_name': g, 'status': st, 'tools': 12};

Map<String, dynamic> _home() => {
      'configured': true,
      'total': 1600,
      'mine': [_a('slack', 'Slack', 'mail', 'ready')],
      'featured': [_a('razorpay', 'Razorpay', 'money', 'needs_link'), _a('notion', 'Notion', 'projects', 'needs_link')],
      'groups': [
        {'id': 'mail', 'name': 'Mail & chat', 'count': 140, 'connected': 1,
         'top': [_a('slack', 'Slack', 'mail', 'ready'), _a('telegram', 'Telegram', 'mail', 'needs_key')]},
        {'id': 'more', 'name': 'More apps', 'count': 30, 'top': [_a('x', 'X app', 'more', 'needs_link')]},
        {'id': 'crm', 'name': 'Sales & CRM', 'count': 90, 'top': [_a('pipedrive', 'Pipedrive', 'crm', 'needs_link')]},
        {'id': 'money', 'name': 'Money & payments', 'count': 70, 'top': [_a('razorpay', 'Razorpay', 'money', 'needs_link')]},
        {'id': 'projects', 'name': 'Projects & tasks', 'count': 110, 'top': [_a('notion', 'Notion', 'projects', 'needs_link')]},
        {'id': 'docs', 'name': 'Docs & files', 'count': 80, 'top': [_a('dropbox', 'Dropbox', 'docs', 'needs_link')]},
        {'id': 'dev', 'name': 'Developer', 'count': 0, 'top': []},
      ],
    };

void _tall(WidgetTester t) {
  t.view.physicalSize = const Size(1170, 6000);   // a phone 390 wide and tall enough to hold the whole page
  t.view.devicePixelRatio = 3;
  addTearDown(t.view.reset);
}

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true, 'appearance': 'light'});
  return Santosh.load();
}

void main() {
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);

  test('home: four group cards, the rest as tiles, More apps last, empty groups gone', () {
    final p = connectHome(_home());
    expect(p.total, 1600);
    expect(p.mine.single.connected, isTrue);
    expect(p.featured.map((a) => a.name), ['Razorpay', 'Notion']);
    expect(p.cards.map((g) => g.id), ['mail', 'crm', 'money', 'projects']);
    expect(p.tiles.map((g) => g.id), ['docs', 'more']);
  });

  test('button words for every state', () {
    expect(connectActionLabel('ready'), 'Connected');
    expect(connectActionLabel('needs_link'), 'Connect');
    expect(connectActionLabel('needs_key'), 'Add key');
    expect(connectActionLabel('needs_setup'), 'Coming soon');
    expect(connectActionLabel('pending'), 'Finish sign-in');
    expect(connectActionLabel('needs_link', waiting: true), 'Waiting');
    expect(connectActionLabel('ready', waiting: true), 'Connected');
  });

  testWidgets('the home shows only apps, by category, and the way to built-in tools', (t) async {
    _tall(t);
    final app = await _app();
    HoolaConnectDebug.home = _home();
    var more = 0;
    await t.pumpWidget(MaterialApp(
        home: HoolaTheme(appearance: 'light', child: Scaffold(body: HoolaConnect(app: app, onMore: () => more++)))));
    await t.pumpAndSettle();
    expect(find.text('Connect'), findsWidgets);
    expect(find.textContaining('1 connected · 1,600 ready to add'), findsOneWidget);
    expect(find.text('Your apps'), findsOneWidget);
    expect(find.text('Most used by Indian businesses'), findsOneWidget);
    expect(find.text('Browse by category'), findsOneWidget);
    expect(find.text('Add key'), findsOneWidget);   // Telegram is a key app
        await t.tap(find.text('Built-in tools'));
    expect(more, 1);
    HoolaConnectDebug.home = null;
    app.dispose();
  });

  testWidgets('tapping an app opens its sheet with one big Connect button', (t) async {
    _tall(t);
    final app = await _app();
    HoolaConnectDebug.home = _home();
    await t.pumpWidget(MaterialApp(
        home: HoolaTheme(appearance: 'light', child: Scaffold(body: HoolaConnect(app: app, onMore: () {})))));
    await t.pumpAndSettle();
    await t.tap(find.text('Notion').first);
    await t.pumpAndSettle();
    expect(find.text('Connect Notion'), findsOneWidget);
    expect(find.text('What Hoola will do'), findsOneWidget);
    expect(find.textContaining('Never see your Notion password'), findsOneWidget);
    HoolaConnectDebug.home = null;
    app.dispose();
  });

  testWidgets('a connected app says so and can be removed; an app not switched on cannot be tapped', (t) async {
    final app = await _app();
    HoolaConnectDebug.home = {
      ..._home(),
      'mine': [_a('slack', 'Slack', 'mail', 'ready'), _a('xero', 'Xero', 'money', 'needs_setup')],
    };
    await t.pumpWidget(MaterialApp(
        home: HoolaTheme(appearance: 'light', child: Scaffold(body: HoolaConnect(app: app, onMore: () {})))));
    await t.pumpAndSettle();
    await t.tap(find.bySemanticsLabel('Slack, connected').first);
    await t.pumpAndSettle();
    expect(find.text('Remove'), findsOneWidget);
    Navigator.of(t.element(find.text('Remove'))).pop();
    await t.pumpAndSettle();
    await t.tap(find.bySemanticsLabel('Xero, not connected yet'));
    await t.pumpAndSettle();
    expect(find.text('Coming soon'), findsOneWidget);
    final b = t.widget<ButtonStyleButton>(find.ancestor(of: find.text('Coming soon'), matching: find.byWidgetPredicate((w) => w is ButtonStyleButton)));
    expect(b.onPressed, isNull);
    HoolaConnectDebug.home = null;
    app.dispose();
  });

  testWidgets('a group page lists its apps with Popular / A-Z / Connected', (t) async {
    final app = await _app();
    HoolaConnectDebug.apps = {
      'total': 3,
      'apps': [_a('hubspot', 'HubSpot', 'crm', 'ready'), _a('salesforce', 'Salesforce', 'crm', 'needs_link'),
        _a('pipedrive', 'Pipedrive', 'crm', 'needs_link')],
    };
    await t.pumpWidget(MaterialApp(
        home: HoolaTheme(appearance: 'light', child: ConnectGroupPage(app: app, group: 'crm', name: 'Sales & CRM'))));
    await t.pumpAndSettle();
    expect(find.text('Sales & CRM'), findsOneWidget);
    expect(find.text('Popular'), findsOneWidget);
    expect(find.text('A–Z'), findsOneWidget);
    expect(find.text('Popular in Sales & CRM'), findsOneWidget);
    expect(find.text('Salesforce'), findsOneWidget);
    expect(find.textContaining('1 connected'), findsOneWidget);
    HoolaConnectDebug.apps = null;
    app.dispose();
  });
}
