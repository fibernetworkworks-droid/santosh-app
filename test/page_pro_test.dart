// v0.902 PAGE PRO: a page Hoola makes is shown like Claude's artifact - the card (thumbnail, the real step + a clock,
// Stop / Share / Open), the "N pages" pill and the list of this chat's pages.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/chat/hoola_artifact.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

Widget _host(Widget child) =>
    MaterialApp(home: HoolaTheme(appearance: 'light', child: Scaffold(body: SingleChildScrollView(child: child))));

void main() {
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);

  test('the status line says what the page is doing, in plain words', () {
    final now = DateTime.utc(2026, 11, 14, 10, 0, 42);
    expect(artifactState({'status': 'building', 'stage': 'writing', 'started_at': '2026-11-14T10:00:00Z'}, now: now).line,
        'Writing the page · 0:42');
    expect(artifactState({'status': 'building', 'stage': 'checking'}, now: now).line, 'Checking it opens');
    expect(artifactState({'status': 'building'}).line, 'Writing the page');
    expect(artifactState({'status': 'ready', 'version': 3, 'build_s': 48}).line, 'Version 3 · made in 0:48');
    expect(artifactState({'status': 'ready'}).line, 'Version 1');
    expect(artifactState({'status': 'ready', 'version': 2, 'stage': 'stopped'}).line, 'Version 2 · the newer one was not made');
    expect(artifactState({'status': 'failed', 'stage': 'stopped'}).line, 'Stopped');
    expect(artifactState({'status': 'failed'}).line, 'Not made');
    expect(artifactClock(125), '2:05');
    expect(artifactStepIndex('read'), 1, reason: 'the first step shown as running is writing');
  });

  testWidgets('a page being made: the step, a live clock, the step marks, Stop', (t) async {
    final app = await _app();
    final v = {'id': 'a2', 'title': 'October GST checklist', 'status': 'building', 'stage': 'writing',
      'started_at': DateTime.now().toUtc().subtract(const Duration(seconds: 23)).toIso8601String()};
    await t.pumpWidget(_host(HCArtifact(v: v, app: app)));
    await t.pump(const Duration(milliseconds: 50));
    expect(find.text('October GST checklist'), findsOneWidget);
    expect(find.textContaining(RegExp(r'^Writing the page · 0:2\d$')), findsOneWidget);
    expect(find.text('Stop'), findsOneWidget);
    expect(find.text('Open'), findsNothing, reason: 'nothing to open before the first version');
    expect(find.textContaining('20 to 90 seconds'), findsOneWidget);
    await t.pumpWidget(const SizedBox());
    app.dispose();
  });

  testWidgets('a ready page: version, build time, summary, Share + Open; a failed one: Try again', (t) async {
    final app = await _app();
    await t.pumpWidget(_host(HCArtifact(v: const {'id': 'a1', 'title': 'Bank revenue dashboard', 'status': 'ready', 'version': 3,
      'build_s': 48, 'summary': 'Revenue of every listed bank.'}, app: app)));
    expect(find.text('Version 3 · made in 0:48'), findsOneWidget);
    expect(find.text('Revenue of every listed bank.'), findsOneWidget);
    expect(find.text('Share'), findsOneWidget);
    expect(find.text('Open'), findsOneWidget);
    expect(find.text('Stop'), findsNothing);

    await t.pumpWidget(_host(HCArtifact(v: const {'id': 'a3', 'title': 'Quiz', 'status': 'failed', 'error': 'The page maker took too long.'},
        app: app)));
    expect(find.text('Not made'), findsOneWidget);
    expect(find.text('The page maker took too long.'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
    expect(find.text('Open'), findsNothing);
    app.dispose();
  });

  testWidgets('the pages pill counts this chat\'s pages and lists them, newest first', (t) async {
    final app = await _app();
    app.feed.add(FeedItem('artifact', {'id': 'a1', 'title': 'Dashboard', 'status': 'ready', 'version': 2}));
    app.feed.add(FeedItem('artifact', {'id': 'gone', 'title': 'Old', 'status': 'deleted'}));
    app.feed.add(FeedItem('artifact', {'id': 'a2', 'title': 'Checklist', 'status': 'ready'}));
    expect(chatPages(app).map((p) => p['id']), ['a2', 'a1']);
    await t.pumpWidget(MaterialApp(home: HoolaTheme(appearance: 'light', child: Scaffold(body: Center(child: PagesPill(app: app))))));
    expect(find.text('2 pages'), findsOneWidget);
    await t.tap(find.text('2 pages'));
    await t.pumpAndSettle();
    expect(find.text('Pages in this chat'), findsOneWidget);
    expect(find.text('Checklist'), findsOneWidget);
    expect(find.text('Dashboard'), findsOneWidget);
    expect(find.text('Old'), findsNothing);
    app.dispose();
  });

  testWidgets('no pages = no pill', (t) async {
    final app = await _app();
    await t.pumpWidget(MaterialApp(home: HoolaTheme(appearance: 'light', child: Scaffold(body: PagesPill(app: app)))));
    expect(find.byType(InkWell), findsNothing);
    app.dispose();
  });
}
