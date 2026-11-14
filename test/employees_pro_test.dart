// v0.910 AI EMPLOYEES PRO (design canvas claude.ai/artifact/VkbWNUPLT1s7UYycxjhnjJ, "GO BUILD"): the console's three
// levels on the phone - home with the numbers, Your team and a card per department; a department page with
// All / Ready / My team / Soon; one employee with its trust ladder and Hire / Open desk - on the console's own calls.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/api.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/shell/hoola_employees.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

final _list = <Map<String, dynamic>>[
  {'key': 'seo', 'name': 'SEO Specialist', 'group': 'Business', 'live': true, 'pitch': 'Gets your business found on Google',
   'does': ['Full audit of your website every week'], 'needs': ['Your website address'], 'never': ['Buy links or fake reviews']},
  {'key': 'social', 'name': 'Social Media Manager', 'group': 'Business', 'status': 'hired', 'trust': 'seekh', 'live': true,
   'pitch': 'Runs your Instagram and Facebook Page'},
  {'key': 'telecaller', 'name': 'Telecaller', 'group': 'Business', 'live': false, 'pitch': 'Calls your leads with a script'},
  {'key': 'const_store', 'name': 'Material Store Manager (Saaman)', 'group': 'Construction & Real Estate', 'live': true, 'pitch': 'GRN, issue, stock'},
  {'key': 'new_one', 'name': 'Space Planner', 'group': 'Space & Orbit', 'live': false, 'pitch': 'Something new'},
];

Widget _host(Widget w, {bool still = false, String mode = 'light'}) => MaterialApp(
      builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(disableAnimations: still), child: child!),
      home: HoolaTheme(appearance: mode, child: Scaffold(body: w)),
    );

void _phone(WidgetTester t) {
  t.view.physicalSize = const Size(390 * 3, 2400 * 3);
  t.view.devicePixelRatio = 3;
  addTearDown(t.view.reset);
}

Future<void> _settle(WidgetTester t) async {
  await t.pump();
  await t.pump(const Duration(seconds: 2));
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);

  test('initials, counts and departments read like the console', () {
    expect(employeeMono('SEO Specialist'), 'SS');
    expect(employeeMono('GST & Accounts'), 'GA');
    expect(employeeMono('Material Store Manager (Saaman)'), 'MS');
    expect(employeeMono('Kaan (transcription)'), 'K');
    expect(deptCount([{'live': true}, {'live': true}]), '2 roles, all ready');
    expect(deptCount([{'live': true}]), '1 role, ready');
    expect(deptCount([{'live': true}, {'live': false}, {'live': false}]), '1 of 3 ready');
    expect(hoolaDepts.length, 12);
    expect(hoolaDepts.map((d) => d.icon).toSet().length, 12, reason: 'every department its own drawing');
    expect(hoolaDeptOf('Space & Orbit').name, 'Space & Orbit', reason: 'a group the hub does not know still shows');
  });

  test('hire, pause and the trust level go through the console\'s own calls', () async {
    HttpOverrides.global = null;   // the widget-test binding answers every real request with 400; this test has its own server
    final seen = <String>[];
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((req) async {
      final body = await utf8.decoder.bind(req).join();
      seen.add('${req.method} ${req.uri.path} $body'.trim());
      req.response.headers.contentType = ContentType.json;
      req.response.write(jsonEncode(req.uri.path == '/api/employees' ? {'employees': _list} : {'ok': true}));
      await req.response.close();
    });
    final app = await _app();
    app.api = Api('http://127.0.0.1:${server.port}', 'k');
    final staff = HoolaStaff(app);
    await staff.load();
    expect(staff.all.length, 5);
    expect(staff.team.single['key'], 'social');
    expect(staff.ready, 3);
    expect(staff.departments.first.$1.name, 'Business', reason: 'the hub\'s order');
    expect(staff.departments.last.$1.group, 'Space & Orbit', reason: 'unknown groups after the known ones');
    expect(await staff.act('seo', 'hire'), isNull);
    expect(await staff.act('social', 'pause'), isNull);
    expect(await staff.setTrust('social', 'saathi'), isNull);
    expect(staff.byKey('social')!['trust'], 'saathi');
    expect(seen, containsAllInOrder([
      'GET /api/employees',
      'POST /api/employees/seo/hire {}',
      'POST /api/employees/social/pause {}',
      'PUT /api/employees/social/settings {"trust":"saathi"}',
    ]));
    staff.dispose();
    app.dispose();
    await server.close(force: true);
  });

  for (final mode in ['light', 'dark']) {
    testWidgets('$mode home: the numbers, Your team, a card per department with its drawing on black', (t) async {
      _phone(t);
      HoolaEmployees.debugList = _list;
      addTearDown(() => HoolaEmployees.debugList = null);
      final app = await _app();
      await t.pumpWidget(_host(HoolaEmployees(app: app), mode: mode));
      await _settle(t);
      final c = mode == 'light' ? HoolaColors.light : HoolaColors.darkSet;
      expect(find.text('AI Employees'), findsOneWidget);
      for (final w in ['5', 'roles', '3', 'ready to hire', '4', 'departments']) {
        expect(find.text(w), findsOneWidget, reason: 'the numbers: $w');
      }
      expect(find.text('Your team'), findsOneWidget);
      expect(find.text('Social Media Manager'), findsOneWidget);
      expect(find.text('Open desk'), findsOneWidget);
      final badges = t.widgetList<DeptBadge>(find.byType(DeptBadge)).toList();
      expect(badges.length, 3, reason: 'Business, Construction, and the unknown group');
      for (final b in t.widgetList<Container>(find.descendant(of: find.byType(DeptBadge), matching: find.byType(Container)))) {
        if (b.decoration is BoxDecoration && (b.decoration as BoxDecoration).shape == BoxShape.circle) {
          expect((b.decoration as BoxDecoration).color, c.pill, reason: 'black circle (near-white in dark)');
        }
      }
      expect(find.text('2 of 3 ready'), findsOneWidget, reason: 'Business: SEO + Social ready, Telecaller coming');
      expect(find.text('1 role, ready'), findsOneWidget);
      // the search finds people across departments
      await t.enterText(find.byType(TextField), 'stock');
      await t.pump();
      expect(find.text('Material Store Manager (Saaman)'), findsOneWidget);
      expect(find.byType(DeptBadge), findsNothing);
      expect(t.takeException(), isNull);
      app.dispose();
    });
  }

  testWidgets('a department: All / Ready / My team / Soon filter its people', (t) async {
    _phone(t);
    HoolaEmployees.debugList = _list;
    addTearDown(() => HoolaEmployees.debugList = null);
    final app = await _app();
    final staff = HoolaStaff(app);
    await staff.load();
    await t.pumpWidget(_host(HoolaDepartmentPage(staff: staff, group: 'Business')));
    await _settle(t);
    expect(find.text('Business'), findsOneWidget);
    expect(find.text('3 roles'), findsOneWidget);
    expect(find.text('1 on your team'), findsOneWidget);
    expect(find.text('SEO Specialist'), findsOneWidget);
    expect(find.text('Telecaller'), findsOneWidget);
    expect(find.text('Coming soon'), findsOneWidget);
    expect(find.text('On your team · working'), findsOneWidget);
    await t.tap(find.text('Soon 1'));
    await _settle(t);
    expect(find.text('SEO Specialist'), findsNothing);
    expect(find.text('Telecaller'), findsOneWidget);
    await t.tap(find.text('My team 1'));
    await _settle(t);
    expect(find.text('Social Media Manager'), findsOneWidget);
    expect(find.text('Telecaller'), findsNothing);
    await t.tap(find.text('Ready 2'));
    await _settle(t);
    expect(find.text('SEO Specialist'), findsOneWidget);
    expect(find.text('Telecaller'), findsNothing);
    staff.dispose();
    app.dispose();
  });

  testWidgets('one employee: what it does / needs / never, the trust ladder, Hire', (t) async {
    _phone(t);
    HoolaEmployees.debugList = _list;
    addTearDown(() => HoolaEmployees.debugList = null);
    final app = await _app();
    final staff = HoolaStaff(app);
    await staff.load();
    await t.pumpWidget(_host(HoolaEmployeePage(staff: staff, employeeKey: 'seo')));
    await _settle(t);
    for (final w in ['SEO Specialist', 'Ready to hire', 'How much it does on its own', 'What it does', 'What it needs from you',
        'It will never', 'Buy links or fake reviews', 'Hire SEO Specialist', 'Learning', 'Partner', 'Trusted']) {
      expect(find.text(w), findsWidgets, reason: w);
    }
    await t.tap(find.text('Partner'));
    await _settle(t);
    expect(find.text('Makes small changes that can be undone, and tells you the same day.'), findsOneWidget);
    expect(find.textContaining('Use '), findsNothing, reason: 'not hired yet: it starts on Learning, the ladder only explains');
    staff.dispose();
    app.dispose();
  });

  testWidgets('a hired employee: Open desk, Pause, Let go, and a trust level it can move to', (t) async {
    _phone(t);
    HoolaEmployees.debugList = _list;
    addTearDown(() => HoolaEmployees.debugList = null);
    final app = await _app();
    final staff = HoolaStaff(app);
    await staff.load();
    await t.pumpWidget(_host(HoolaEmployeePage(staff: staff, employeeKey: 'social')));
    await _settle(t);
    expect(find.text('Open desk'), findsOneWidget);
    expect(find.text('Pause'), findsOneWidget);
    expect(find.text('Let go'), findsOneWidget);
    await t.tap(find.text('Partner'));
    await _settle(t);
    expect(find.text('Use Partner'), findsOneWidget);
    await t.tap(find.text('Trusted'));
    await _settle(t);
    expect(find.text('Use Trusted'), findsNothing);
    expect(find.text('Trusted is turned on from its desk, once it has shown good work.'), findsOneWidget);
    await t.tap(find.text('Let go'));
    await _settle(t);
    expect(find.text('Let Social Media Manager go?'), findsOneWidget, reason: 'let go asks first');
    await t.tap(find.text('Cancel'));
    await _settle(t);
    staff.dispose();
    app.dispose();
  });

  testWidgets('reduce motion: everything there at once, nothing moves', (t) async {
    _phone(t);
    HoolaEmployees.debugList = _list;
    addTearDown(() => HoolaEmployees.debugList = null);
    final app = await _app();
    await t.pumpWidget(_host(HoolaEmployees(app: app), still: true));
    await t.pump();
    await t.pump();
    expect(t.widgetList<DeptBadge>(find.byType(DeptBadge)).every((b) => b.clock == null && b.draw == 1), isTrue);
    expect(t.binding.hasScheduledFrame, isFalse, reason: 'no motion, no frames');
    app.dispose();
  });
}
