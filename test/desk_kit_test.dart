// v0.868 R8: the shared desk frame, the flat Night Glass bridge, and wave 1 (30 desks on DeskScaffold, English tabs).
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/desk/desk_kit.dart';
import 'package:santosh/ui/glass.dart';

void main() {
  tearDown(() => NightGlass.flat.value = false);

  test('wave 1: 30 desks stand in DeskScaffold, no old chip row left, English tab labels', () {
    final desks = [
      for (final f in Directory('lib/ui').listSync().whereType<File>())
        if (f.path.endsWith('.dart') && f.readAsStringSync().contains('return DeskScaffold(')) f
    ];
    expect(desks.length, greaterThanOrEqualTo(30));
    for (final f in desks) {
      final s = f.readAsStringSync();
      expect(s.contains("import 'desk/desk_kit.dart';"), isTrue, reason: f.path);
      final i = s.indexOf('return DeskScaffold(');
      final frame = s.substring(i, s.indexOf('\n    );', i));
      final tabs = RegExp(r"tabs: const \[(.*?)\]", dotAll: true).firstMatch(frame)?.group(1) ?? '';
      expect(tabs, isNotEmpty, reason: f.path);
      for (final w in ["'Aaj'", "'Niyam'", "'Jaanch'"]) {
        expect(tabs.contains(w), isFalse, reason: '${f.path} still shows $w');
      }
    }
    // no desk's main page still draws the old chip row; inner detail pages with their own tabs are wave 2
    const innerPagesWave2 = {'archassist_screen.dart', 'contracts_screen.dart', 'cosec_screen.dart', 'shaadi_screen.dart'};
    final left = [
      for (final f in Directory('lib/ui').listSync().whereType<File>())
        if (f.path.endsWith('.dart') &&
            f.readAsStringSync().contains('ChoiceChip(label: Text(tabs[i])') &&
            !innerPagesWave2.contains(f.uri.pathSegments.last))
          f.path
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
