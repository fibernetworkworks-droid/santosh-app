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
}
