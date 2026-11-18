// v0.895 ATTACH LIKE CLAUDE: the typing box shows big thumbnails with a dark x (a too-big file says so and offers no
// Retry), the + button opens Claude's "Add to chat" sheet (Camera / Photos / Files, Research, Memory, places), and her
// sent files land above her bubble - one photo large, several as a row of thumbnails.
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/chat/hoola_attach.dart';
import 'package:santosh/ui/chat_attach.dart' show TrayFile;
import 'package:santosh/ui/hoola_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

// a 1x1 PNG
final _png = base64Decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==');

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

Widget _host(Widget w) => MaterialApp(home: HoolaTheme(appearance: 'light', child: Scaffold(body: Center(child: w))));

void main() {
  testWidgets('typing box: a thumbnail per file, a dark x on each, a too-big file says so with no Retry', (t) async {
    final sem = t.ensureSemantics();
    final photo = TrayFile('shop.jpg', _png)..sent = {'file_id': 'f1', 'media': 'image'};
    final apk = TrayFile('hoola.apk', List<int>.filled(10, 1))..err = 'Not added';
    final big = TrayFile('film.mp4', const <int>[])..err = 'Over 30 MB';
    final removed = <String>[];
    final retried = <String>[];
    await t.pumpWidget(_host(SizedBox(
      width: 400,
      child: HoolaAttachTray(
        files: [photo, apk, big],
        onRemove: (f) => removed.add(f.name),
        onRetry: (f) => retried.add(f.name),
        onOpen: (_) {},
      ),
    )));
    await t.pump();
    expect(find.byType(HoolaFileTile), findsNWidgets(3));
    expect(find.text('Over 30 MB'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);   // the APK can be tried again; the too-big film cannot
    await t.tap(find.text('Retry'));
    expect(retried, ['hoola.apk']);
    expect(find.bySemanticsLabel('Remove film.mp4'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Remove shop.jpg'));
    expect(removed, ['shop.jpg']);
    final tile = t.getSize(find.byType(HoolaFileTile).first);
    expect(tile.width, HoolaAttachTray.tile);
    sem.dispose();
  });

  testWidgets('chat: one photo alone lands large; several files land as a row of thumbnails', (t) async {
    final sem = t.ensureSemantics();
    final app = await _app();
    final photo = {'file_id': 'a', 'name': 'shop.jpg', 'media': 'image', 'preview': base64Encode(_png), 'width': 800, 'height': 600};
    await t.pumpWidget(_host(SizedBox(width: 360, child: HoolaSentFiles(files: [photo], app: app))));
    await t.pump();
    expect(find.byType(HoolaFileTile), findsNothing);
    expect(find.bySemanticsLabel('Open shop.jpg'), findsOneWidget);
    final big = t.getSize(find.byType(AspectRatio));
    expect(big.width, closeTo(260, 1));   // a 4:3 photo at Claude's width

    await t.pumpWidget(_host(SizedBox(
      width: 360,
      child: HoolaSentFiles(files: [
        photo,
        {'file_id': 'b', 'name': 'bill.pdf', 'media': 'pdf', 'pages': 3, 'size': 120000},
        {'file_id': 'c', 'name': 'hoola.apk', 'media': 'other', 'size': 18 * 1024 * 1024},
      ], app: app),
    )));
    await t.pump();
    expect(find.byType(HoolaFileTile), findsNWidgets(3));
    expect(find.text('PDF · 3 pages'), findsOneWidget);
    expect(find.text('APK · 18.0 MB'), findsOneWidget);
    expect(find.byIcon(Icons.android_rounded), findsOneWidget);
    sem.dispose();
  });

  testWidgets('+ opens Claude\'s Add sheet: Camera / Photos / Files, Research switch, places', (t) async {
    final app = await _app();
    HoolaAddPick? picked;
    var research = false;
    await t.pumpWidget(MaterialApp(
      home: HoolaTheme(
        appearance: 'light',
        child: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: TextButton(
                onPressed: () async => picked = await showHoolaAddSheet(context, app: app, research: false, onResearch: (v) => research = v),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    ));
    await t.tap(find.text('open'));
    await t.pumpAndSettle();
    expect(find.text('Add to chat'), findsOneWidget);
    for (final w in ['Camera', 'Photos', 'Files', 'Research', 'Connectors', 'Your computers', 'AI team', 'Memory']) {
      expect(find.text(w), findsOneWidget, reason: w);
    }
    await t.tap(find.byType(Switch).first);
    await t.pump();
    expect(research, isTrue);
    await t.tap(find.text('Files'));
    await t.pumpAndSettle();
    expect(picked, HoolaAddPick.files);
  });

  test('limits are Claude\'s: 20 files, 30 MB each', () {
    expect(hoolaMaxFiles, 20);
    expect(hoolaMaxBytes, 30 * 1024 * 1024);
    expect(Uint8List.fromList(_png).isNotEmpty, isTrue);
  });
}
