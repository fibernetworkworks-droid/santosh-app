// v0.868 R8: the shared desk frame, the flat Night Glass bridge, and wave 1 (30 desks on DeskScaffold, English tabs).
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/desk/desk_kit.dart';
import 'package:santosh/ui/glass.dart';

void main() {
  tearDown(() => NightGlass.flat.value = false);

  test('waves 1 + 2: 57 desks + 4 inner pages stand in DeskScaffold, no old chip row left, English labels', () {
    final desks = [
      for (final f in Directory('lib/ui').listSync().whereType<File>())
        if (f.path.endsWith('.dart') && f.readAsStringSync().contains('return DeskScaffold(')) f
    ];
    expect(desks.length, greaterThanOrEqualTo(57));
    final frames = desks.fold<int>(0, (n, f) => n + 'return DeskScaffold('.allMatches(f.readAsStringSync()).length);
    expect(frames, greaterThanOrEqualTo(61));
    for (final f in desks) {
      final s = f.readAsStringSync();
      expect(s.contains("import 'desk/desk_kit.dart';"), isTrue, reason: f.path);
      for (final m in 'return DeskScaffold('.allMatches(s)) {
        final frame = s.substring(m.start, s.indexOf('\n    );', m.start));
        final tabs = RegExp(r"tabs: const \[(.*?)\]", dotAll: true).firstMatch(frame)?.group(1) ?? '';
        expect(tabs, isNotEmpty, reason: f.path);
        for (final w in ["'Aaj'", "'Niyam'", "'Jaanch'"]) {
          expect(tabs.contains(w), isFalse, reason: '${f.path} still shows $w');
        }
        final title = RegExp(r"title: (.*),\n").firstMatch(frame)?.group(1) ?? '';
        expect(title.toLowerCase().contains('sahayak'), isFalse, reason: '${f.path} title $title');
      }
    }
    // no screen still draws either of the two old desk chip rows of its own
    final old = RegExp(r"ChoiceChip\(label: Text\(tabs\[i\]\)|for \(final \(i, t\) in const \[\(0, |for \(final \(i, t\) in tabs\.indexed\)");
    final left = [
      for (final f in Directory('lib/ui').listSync().whereType<File>())
        if (f.path.endsWith('.dart') && old.hasMatch(f.readAsStringSync())) f.path
    ];
    expect(left, isEmpty);
  });

  test('English for the old Hinglish tab words', () {
    expect(deskWord('Aaj'), 'Today');
    expect(deskWord('Niyam'), 'Rules');
    expect(deskWord('Documents'), 'Documents');
  });

  Widget host(Widget w) => MaterialApp(home: w);

  testWidgets('tabs, busy line, pull to refresh, and a slow first load offers Try again', (t) async {
    var tab = 0, refreshed = 0;
    late StateSetter set;
    var loading = true;
    await t.pumpWidget(host(StatefulBuilder(builder: (context, s) {
      set = s;
      return DeskScaffold(
        title: 'Notary desk',
        tabs: const ['Aaj', 'Documents'],
        tab: tab,
        onTab: (i) => s(() => tab = i),
        loading: loading,
        busy: true,
        onRefresh: () async => refreshed++,
        body: () => ListView(children: [Text('tab $tab')]),
      );
    })));
    expect(find.text('Today'), findsOneWidget);           // English tab
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    expect(find.text('Still loading'), findsNothing);
    await t.pump(const Duration(seconds: 13));
    expect(find.text('Still loading'), findsOneWidget);   // never a spinner for ever
    await t.tap(find.text('Try again'));
    await t.pump();
    expect(refreshed, 1);
    set(() => loading = false);
    await t.pump();
    expect(find.text('tab 0'), findsOneWidget);
    await t.tap(find.text('Documents'));
    await t.pump();
    expect(find.text('tab 1'), findsOneWidget);
    await t.tap(find.byTooltip('Refresh'));
    await t.pump();
    expect(refreshed, 2);
  });

  testWidgets('an inner page with nothing to reload shows no Refresh and no pull', (t) async {
    await t.pumpWidget(host(DeskScaffold(
      title: 'Asha (Class 8)',
      tabs: const ['Study', 'Practice'],
      tab: 0,
      onTab: (_) {},
      loading: false,
      body: () => ListView(children: const [Text('study')]),
    )));
    expect(find.byTooltip('Refresh'), findsNothing);
    expect(find.byType(RefreshIndicator), findsNothing);
    expect(find.text('study'), findsOneWidget);
  });

  testWidgets('with the new design on, Night Glass draws flat: no blur, no drifting aurora', (t) async {
    NightGlass.flat.value = true;
    await t.pumpWidget(host(const Aurora(child: Glass(child: Text('card')))));
    expect(find.byType(BackdropFilter), findsNothing);
    expect(find.byType(ImageFiltered), findsNothing);
    NightGlass.flat.value = false;
    await t.pumpWidget(host(const SizedBox()));
    await t.pumpWidget(host(const Aurora(child: Glass(child: Text('card')))));
    expect(find.byType(BackdropFilter), findsOneWidget);   // the old look is unchanged when the switch is off
    await t.pumpWidget(const SizedBox());
  });

  test('wave 3: every swipe-tab desk stands in DeskTabsScaffold, no TabBar of its own, English titles', () {
    final files = [for (final f in Directory('lib/ui').listSync().whereType<File>()) if (f.path.endsWith('.dart')) f];
    final desks = [for (final f in files) if (f.readAsStringSync().contains('DeskTabsScaffold(')) f];
    expect(desks.length, greaterThanOrEqualTo(20));   // + the Notebook on DeskTabBar
    for (final f in desks) {
      final s = f.readAsStringSync();
      expect(s.contains("import 'desk/desk_kit.dart';"), isTrue, reason: f.path);
      final i = s.indexOf('DeskTabsScaffold(');
      final title = RegExp(r"title: (.*),\n").firstMatch(s.substring(i))?.group(1) ?? '';
      expect(title.toLowerCase().contains('sahayak'), isFalse, reason: '${f.path} title $title');
      expect(title.contains('aName} ·'), isFalse, reason: '${f.path} title $title');
    }
    // nothing outside the kit draws a TabBar or a DefaultTabController of its own any more
    final left = [
      for (final f in files)
        if (RegExp(r"\bTabBar\(|DefaultTabController\(").hasMatch(f.readAsStringSync())) f.path
    ];
    expect(left, isEmpty);
    expect(deskWord('Galla'), 'Cash box');
    expect(deskWord('Kharcha'), 'Spending');
  });

  testWidgets('swipe-tab frame: English pill tabs, swipe, error shows Could not load + Try again', (t) async {
    NightGlass.flat.value = true;
    var tries = 0;
    String? err = 'Server did not answer';
    late StateSetter set;
    await t.pumpWidget(host(StatefulBuilder(builder: (context, s) {
      set = s;
      return DeskTabsScaffold(
        title: 'Office manager',
        tabs: const ['Aaj', 'Kharcha', 'Niyam'],
        error: err,
        onRefresh: () async => tries++,
        pages: () => const [Center(child: Text('page today')), Center(child: Text('page money')), Center(child: Text('page rules'))],
      );
    })));
    expect(find.text('Could not load'), findsOneWidget);
    expect(find.text('Server did not answer'), findsOneWidget);
    await t.tap(find.text('Try again'));
    await t.pump();
    expect(tries, 1);
    set(() => err = null);
    await t.pumpAndSettle();
    expect(find.text('Today'), findsOneWidget);
    expect(find.text('Spending'), findsOneWidget);
    expect(find.text('page today'), findsOneWidget);
    await t.tap(find.text('Rules'));
    await t.pumpAndSettle();
    expect(find.text('page rules'), findsOneWidget);
    await t.fling(find.text('page rules'), const Offset(400, 0), 1000);
    await t.pumpAndSettle();
    expect(find.text('page money'), findsOneWidget);
    expect(find.byType(BackdropFilter), findsNothing);
  });

  test('wave 4: one-page desks and detail pages stand in DeskPage, English titles, the frozen PC screens untouched', () {
    final files = [for (final f in Directory('lib/ui').listSync().whereType<File>()) if (f.path.endsWith('.dart')) f];
    var frames = 0, users = 0;
    for (final f in files) {
      final s = f.readAsStringSync();
      final n = RegExp(r'\bDeskPage\(').allMatches(s).length;
      if (n == 0) continue;
      users++;
      frames += n;
      expect(s.contains("import 'desk/desk_kit.dart';"), isTrue, reason: f.path);
      for (final m in RegExp(r'DeskPage\(\s*title: (.*),\n').allMatches(s)) {
        final t = m.group(1)!;
        for (final w in ['sahayak', 'band na ho', 'hisaab', "'Kaam'"]) {
          expect(t.toLowerCase().contains(w.toLowerCase()), isFalse, reason: '${f.path} title $t');
        }
        expect(t.contains('aName} ·'), isFalse, reason: '${f.path} title $t');
      }
    }
    expect(users, greaterThanOrEqualTo(120));
    expect(frames, greaterThanOrEqualTo(175));
    for (final frozen in ['lib/ui/pc_screen.dart', 'lib/ui/hoola_pc_screen.dart']) {
      expect(File(frozen).readAsStringSync().contains('DeskPage('), isFalse, reason: '$frozen is frozen');
    }
  });

  testWidgets('one-page frame: Refresh, error + Try again, then the page', (t) async {
    NightGlass.flat.value = true;
    var tries = 0;
    String? err = 'No internet';
    late StateSetter set;
    await t.pumpWidget(host(StatefulBuilder(builder: (context, s) {
      set = s;
      return DeskPage(title: 'Google Drive', error: err, onRefresh: () async => tries++, body: () => const Center(child: Text('files here')));
    })));
    expect(find.text('Could not load'), findsOneWidget);
    expect(find.byTooltip('Refresh'), findsOneWidget);
    await t.tap(find.text('Try again'));
    await t.pump();
    expect(tries, 1);
    set(() => err = null);
    await t.pump();
    expect(find.text('files here'), findsOneWidget);
    expect(find.byType(BackdropFilter), findsNothing);
  });
}
