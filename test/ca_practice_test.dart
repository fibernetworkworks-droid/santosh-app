// v0.999.46 CA PRACTICE on the phone: the clients list, the document inbox and the /api/practice calls.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/api.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/ca_practice.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

Widget _host(Widget w, {String mode = 'light'}) => MaterialApp(home: HoolaTheme(appearance: mode, child: w));

void _phone(WidgetTester t) {
  t.view.physicalSize = const Size(390 * 3, 1800 * 3);
  t.view.devicePixelRatio = 3;
  addTearDown(t.view.reset);
}

final _home = <String, dynamic>{
  'settings': <String, dynamic>{},
  'summary': {'clients': 3, 'complete': 1, 'month': '2026-10', 'waiting': 2},
  'kinds': {'sales': 'Sales bills', 'purchase': 'Purchase bills', 'bank': 'Bank statements', 'other': 'Other'},
};
final _clients = <String, dynamic>{
  'month': '2026-10',
  'clients': [
    {'id': 'c1', 'name': 'Shree Traders', 'gstin': '27AAAAA0000A1Z5', 'missing': <String>[], 'complete': true, 'files_month': 6,
     'last': {'name': 'bank_oct.pdf', 'at': '2026-10-30T10:00:00Z', 'channel': 'email'}},
    {'id': 'c2', 'name': 'Patil Hardware', 'gstin': '', 'missing': ['bank', 'purchase'], 'complete': false, 'files_month': 2,
     'last': {'name': 'sale_12.jpg', 'at': '2026-10-28T10:00:00Z', 'channel': 'whatsapp'}},
    {'id': 'c3', 'name': 'New Client', 'missing': ['sales', 'purchase', 'bank'], 'complete': false, 'files_month': 0, 'last': null},
  ],
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);
  tearDown(CaPracticeDebug.clear);

  test('months, rupees and the client state read plainly', () {
    expect(caMonthLabel('2026-10'), 'October 2026');
    expect(caMonthLabel(''), 'No month');
    expect(caRupees(1234567.4), '₹12,34,567');
    expect(caRupees(999), '₹999');
    expect(caRupees('abc'), '');
    final list = (_clients['clients'] as List).cast<Map<String, dynamic>>();
    expect(list.map(caClientState).toList(), ['Complete', '2 missing', 'Nothing yet']);
  });

  test('the practice calls go to /api/practice with the right bodies', () async {
    HttpOverrides.global = null;   // the binding answers real requests with 400; this test has its own server
    final seen = <String>[];
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((req) async {
      final body = await utf8.decoder.bind(req).join();
      final path = req.uri.path;
      seen.add('${req.method} $path${req.uri.query.isEmpty ? '' : '?${req.uri.query}'}');
      if (path == '/api/practice/upload') {
        expect(req.headers.contentType?.mimeType, 'multipart/form-data');
        expect(body, contains('name="channel"'));
        expect(body, contains('phone'));
        expect(body, contains('name="client_id"'));
        expect(body, contains('filename="bill.jpg"'));
        expect(req.headers.value('authorization'), 'Bearer k');
      }
      if (path.endsWith('/file')) expect(jsonDecode(body), {'client_id': 'c2', 'month': '2026-10', 'remember_sender': true});
      if (path == '/api/practice/files/f9') {
        req.response.headers.set('content-disposition', 'attachment; filename="bank oct.pdf"');
        req.response.add([1, 2, 3]);
        await req.response.close();
        return;
      }
      req.response.headers.contentType = ContentType.json;
      req.response.write(jsonEncode(switch (path) {
        '/api/practice' => _home,
        '/api/practice/clients' => _clients,
        '/api/practice/upload' => {'files': [{'id': 'f1', 'status': 'filed', 'name': 'bill.jpg'}]},
        _ => {'ok': true},
      }));
      await req.response.close();
    });
    final api = Api('http://127.0.0.1:${server.port}', 'k');
    expect((await api.practiceHome())['summary']['waiting'], 2);
    expect(((await api.practiceClients(q: 'patil'))['clients'] as List).length, 3);
    expect((await api.practiceUpload([1, 2, 3], 'bill.jpg', clientId: 'c2'))['files'][0]['status'], 'filed');
    await api.practiceFile('f2', 'c2', month: '2026-10');
    await api.practiceDrop('f3');
    final got = await api.practiceDownload('f9');
    expect(got.name, 'bank oct.pdf');
    expect(got.bytes, [1, 2, 3]);
    expect(seen, [
      'GET /api/practice',
      'GET /api/practice/clients?q=patil',
      'POST /api/practice/upload',
      'POST /api/practice/files/f2/file',
      'POST /api/practice/files/f3/drop',
      'GET /api/practice/files/f9',
    ]);
    await server.close(force: true);
  });

  for (final mode in ['light', 'dark']) {
    testWidgets('$mode clients: count, inbox row, states and the two bottom buttons', (t) async {
      _phone(t);
      CaPracticeDebug.home = _home;
      CaPracticeDebug.clients = _clients;
      final app = await _app();
      await t.pumpWidget(_host(CaClientsPage(app: app), mode: mode));
      await t.pump();
      await t.pump(const Duration(milliseconds: 500));
      expect(find.text('Clients'), findsOneWidget);
      expect(find.text('3'), findsOneWidget);
      expect(find.text('Document inbox · 2 need you'), findsOneWidget);
      expect(find.text('Shree Traders'), findsOneWidget);
      expect(find.text('Complete'), findsOneWidget);
      expect(find.text('2 missing'), findsOneWidget);
      expect(find.text('Nothing yet'), findsOneWidget);
      expect(find.text('Scan a bill'), findsOneWidget);
      expect(find.text('Call GST & Accounts'), findsOneWidget);
      expect(t.takeException(), isNull);
      app.dispose();
    });
  }

  testWidgets('clients: empty state says where to add them', (t) async {
    _phone(t);
    CaPracticeDebug.home = {'summary': {'clients': 0, 'waiting': 0}};
    CaPracticeDebug.clients = {'clients': <Object>[]};
    final app = await _app();
    await t.pumpWidget(_host(CaClientsPage(app: app)));
    await t.pump();
    await t.pump(const Duration(milliseconds: 500));
    expect(find.text('No clients yet. Add them on the console: Accounts > CA practice > Add client.'), findsOneWidget);
    expect(find.text('Document inbox · nothing waiting'), findsOneWidget);
    app.dispose();
  });

  testWidgets('inbox: why, guess, month chips and the three answers', (t) async {
    _phone(t);
    CaPracticeDebug.home = _home;
    CaPracticeDebug.clients = _clients;
    CaPracticeDebug.inbox = {
      'waiting_count': 1,
      'filed_count': 4,
      'waiting': [
        {'id': 'f1', 'name': 'IMG_2201.jpg', 'why': 'This number has sent files for two clients.', 'channel': 'whatsapp',
         'sender': '+91 98220 00000', 'message': 'October bills',
         'guess': {'client_id': 'c2', 'client': 'Patil Hardware', 'kind': 'purchase', 'months': ['2026-09', '2026-10']}},
      ],
    };
    final app = await _app();
    await t.pumpWidget(_host(CaInboxPage(app: app)));
    await t.pump();
    await t.pump(const Duration(milliseconds: 500));
    expect(find.text('Document inbox'), findsOneWidget);
    expect(find.text('This number has sent files for two clients.'), findsOneWidget);
    expect(find.text('WhatsApp · +91 98220 00000'), findsOneWidget);
    expect(find.text('Looks like: Purchase bills for Patil Hardware'), findsOneWidget);
    expect(find.text('September 2026'), findsOneWidget);
    expect(find.text('October 2026'), findsOneWidget);
    expect(find.text('Yes, add to Patil Hardware'), findsOneWidget);
    expect(find.text('Pick another client'), findsOneWidget);
    expect(find.text('Not for me'), findsOneWidget);
    await t.tap(find.text('October 2026'));
    await t.pump();
    expect(t.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'October 2026')).selected, isTrue);
    expect(t.takeException(), isNull);
    app.dispose();
  });

  testWidgets('folder: months newest first, kinds with their files and amounts', (t) async {
    _phone(t);
    CaPracticeDebug.folder = {
      'client': {'id': 'c2', 'name': 'Patil Hardware', 'phones': ['+91 98220 00000'], 'emails': <String>[]},
      'tree': <String, dynamic>{},
      'files': [
        {'id': 'a', 'month': '2026-09', 'kind': 'sales', 'kind_label': 'Sales bills', 'name': 'sale_1.jpg', 'channel': 'phone', 'facts': {'total': 11800}},
        {'id': 'b', 'month': '2026-10', 'kind': 'bank', 'kind_label': 'Bank statements', 'name': 'bank.pdf', 'channel': 'email', 'facts': <String, dynamic>{}},
      ],
    };
    final app = await _app();
    await t.pumpWidget(_host(CaFolderPage(app: app, clientId: 'c2', name: 'Patil Hardware')));
    await t.pump();
    await t.pump(const Duration(milliseconds: 500));
    expect(find.text('Patil Hardware'), findsOneWidget);
    expect(find.text('Files from +91 98220 00000'), findsOneWidget);
    final oct = t.getTopLeft(find.text('October 2026')).dy, sep = t.getTopLeft(find.text('September 2026')).dy;
    expect(oct, lessThan(sep), reason: 'newest month first');
    expect(find.text('Bank statements · 1'), findsOneWidget);
    expect(find.text('₹11,800'), findsOneWidget);
    expect(t.takeException(), isNull);
    app.dispose();
  });
}
