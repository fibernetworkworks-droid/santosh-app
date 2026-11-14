// v0.898 FOUR TABS (owner: "BOTTOM WILL HAVE 4 SECTION --- HOOLA, AI EMPLOYEE, TOOLS, COMPUTER"): the tab bar holds
// exactly those four; Tools shows every studio of the console and opens its console page; AI Employees lists the team
// with who works for her first; Work and Made are one tap away in the drawer.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/shell/hoola_console_page.dart';
import 'package:santosh/ui/shell/hoola_employees.dart';
import 'package:santosh/ui/shell/hoola_shell.dart';
import 'package:santosh/ui/shell/hoola_tools.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

Widget _host(Santosh app, Widget w) => MaterialApp(home: HoolaTheme(appearance: 'light', child: Scaffold(body: w)));

void main() {
  testWidgets('the tab bar: Hoola, AI Employees, Tools, Computer - no Work, Connect or Made', (t) async {
    final app = await _app();
    final taps = <int>[];
    await t.pumpWidget(_host(app, Align(alignment: Alignment.bottomCenter, child: HoolaNav(tab: 0, onTap: taps.add))));
    for (final w in ['Hoola', 'AI Employees', 'Tools', 'Computer']) {
      expect(find.text(w), findsOneWidget, reason: w);
    }
    for (final w in ['Work', 'Connect', 'Made']) {
      expect(find.text(w), findsNothing, reason: w);
    }
    await t.tap(find.text('Tools'));
    await t.tap(find.text('Computer'));
    expect(taps, [2, 3]);
  });

  testWidgets('Tools: every console studio as a tile, a tap opens its console page', (t) async {
    final app = await _app();
    final opened = <String>[];
    final was = hoolaConsoleOpener;
    hoolaConsoleOpener = (ctx, a, path, title) async => opened.add('$title $path');
    addTearDown(() => hoolaConsoleOpener = was);
    t.view.physicalSize = const Size(1080, 3200);
    t.view.devicePixelRatio = 3;
    addTearDown(t.view.reset);
    await t.pumpWidget(_host(app, HoolaTools(app: app)));
    for (final w in ['Create', 'Hoola Interactive', 'Hoola Vocal', 'Hoola Flow', 'Web Development', 'App Development',
                     'Hoola Design', 'Prompting', 'Hoola Code', 'Game Dev', 'Connectors']) {
      expect(find.text(w), findsOneWidget, reason: w);
    }
    await t.tap(find.text('Hoola Interactive'));
    await t.tap(find.text('Web Development'));
    await t.tap(find.text('Prompting'));
    expect(opened, ['Hoola Interactive /console/?v=interactive', 'Web Development /console/web', 'Prompting /console/prompting']);
  });

  testWidgets('AI Employees: who works for her first, departments, the card with Hire', (t) async {
    final app = await _app();
    HoolaEmployees.debugList = [
      {'key': 'seo', 'name': 'SEO Specialist', 'group': 'Business', 'status': 'hired', 'live': true, 'pitch': 'Found on Google'},
      {'key': 'accounts', 'name': 'GST & Accounts', 'group': 'Finance & Banking', 'live': true, 'pitch': 'Your GST',
       'does': ['Prepares GSTR-1'], 'never': ['Files without your OK']},
    ];
    addTearDown(() => HoolaEmployees.debugList = null);
    t.view.physicalSize = const Size(390 * 3, 2400 * 3);
    t.view.devicePixelRatio = 3;
    addTearDown(t.view.reset);
    await t.pumpWidget(_host(app, HoolaEmployees(app: app)));
    await t.pump();
    await t.pump(const Duration(seconds: 2));
    expect(find.text('AI Employees'), findsOneWidget);
    expect(find.text('Your team'), findsOneWidget);
    expect(find.text('Working'), findsOneWidget, reason: 'who works for her, first');
    expect(find.text('Finance & Banking'), findsOneWidget, reason: 'a card per department');
    await t.tap(find.text('Finance & Banking'));
    await t.pump();
    await t.pump(const Duration(seconds: 2));
    await t.tap(find.text('GST & Accounts'));
    await t.pump();
    await t.pump(const Duration(seconds: 2));
    expect(find.text('Hire GST & Accounts'), findsOneWidget);
    expect(find.text('Files without your OK'), findsOneWidget);
  });

  test('an employee without a phone desk opens its console desk', () {
    expect(employeeConsolePath('accounts'), '/console/?v=accountsdesk&a=accounts');
    expect(employeeConsolePath('const_qs'), '/console/?v=deptdesk&a=const_qs');
    expect(employeeConsolePath('kaan'), '/console/flow');
    expect(employeeConsolePath('something_new'), '/console/?v=hire');
  });
}
