// v0.903 NAV PRO: the tab bar - four equal cells, the selected pill sits behind the ICON only (never wider than its
// cell, never behind the label), every label fits its cell even at big text sizes, the icons are vectors that paint
// in both forms.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/ui/hoola_mark.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/shell/hoola_nav_icons.dart';
import 'package:santosh/ui/shell/hoola_shell.dart';

Widget _bar(int tab, {double text = 1, ValueChanged<int>? onTap}) => MaterialApp(
      builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(textScaler: TextScaler.linear(text)), child: child!),
      home: HoolaTheme(
        appearance: 'light',
        child: Scaffold(body: Align(alignment: Alignment.bottomCenter, child: HoolaNav(tab: tab, onTap: onTap ?? (_) {}))),
      ),
    );

void _phone(WidgetTester t, double width) {
  t.view.physicalSize = Size(width * 3, 2400);
  t.view.devicePixelRatio = 3;
  addTearDown(t.view.reset);
}

void main() {
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);

  testWidgets('every icon paints in its outline and its filled form', (t) async {
    await t.pumpWidget(MaterialApp(
      home: Row(children: [
        for (final g in NavGlyph.values)
          for (final on in [0.0, .5, 1.0]) NavIcon(glyph: g, on: on, color: Colors.black, cut: Colors.white),
      ]),
    ));
    expect(find.byType(NavIcon), findsNWidgets(NavGlyph.values.length * 3));
    expect(t.takeException(), isNull);
    expect(HoolaNav.items.map((i) => i.$1).toSet().length, 4, reason: 'four different icons');
  });

  for (final width in [320.0, 360.0, 412.0]) {
    for (final text in [1.0, 1.3, 2.0]) {
      testWidgets('at $width dp and ${(text * 100).round()} % text: AI Employees and its pill stay inside the cell',
          (t) async {
        _phone(t, width);
        await t.pumpWidget(_bar(1, text: text));
        await t.pumpAndSettle();
        expect(t.takeException(), isNull, reason: 'no overflow');
        final cell = t.getRect(find.ancestor(of: find.text('AI Employees'), matching: find.byType(Expanded)).first);
        final label = t.getRect(find.text('AI Employees'));
        final pill = t.getRect(find.byWidgetPredicate((w) =>
            w is Container && w.decoration is BoxDecoration && (w.decoration as BoxDecoration).color == HoolaColors.light.pill));
        expect(label.left, greaterThanOrEqualTo(cell.left - .5));
        expect(label.right, lessThanOrEqualTo(cell.right + .5));
        expect(pill.left, greaterThanOrEqualTo(cell.left));
        expect(pill.right, lessThanOrEqualTo(cell.right));
        expect(pill.bottom, lessThanOrEqualTo(label.top), reason: 'the pill sits behind the icon, above the label');
        expect((pill.center.dx - cell.center.dx).abs(), lessThan(.5), reason: 'centred in its cell');
      });
    }
  }

  testWidgets('the four cells are equal and every icon sits on one line', (t) async {
    _phone(t, 390);
    await t.pumpWidget(_bar(0));
    await t.pumpAndSettle();
    final cells = [for (final e in find.descendant(of: find.byType(HoolaNav), matching: find.byType(Expanded)).evaluate()) t.getRect(find.byWidget(e.widget))];
    expect(cells.length, 4);
    for (final r in cells) {
      expect((r.width - cells.first.width).abs(), lessThan(.5));
    }
    final icons = [for (final e in find.byType(NavIcon).evaluate()) t.getRect(find.byWidget(e.widget)).center.dy];
    expect(icons.toSet().length, 1, reason: 'icons share one baseline');
    final labels = [for (final w in ['Hoola', 'AI Employees', 'Tools', 'Computer']) t.getRect(find.text(w)).center.dy];
    for (final y in labels) {
      expect((y - labels.first).abs(), lessThan(.5), reason: 'labels share one line');
    }
    for (final r in [for (final e in find.byType(NavIcon).evaluate()) t.getRect(find.byWidget(e.widget))]) {
      expect(r.width, 24);
    }
  });

  testWidgets('a tap selects; the selected tab says so to a screen reader', (t) async {
    final taps = <int>[];
    await t.pumpWidget(_bar(0, onTap: taps.add));
    await t.pumpAndSettle();
    await t.tap(find.text('Computer'));
    await t.tap(find.text('AI Employees'));
    expect(taps, [3, 1]);
    final h = t.ensureSemantics();
    expect(t.getSemantics(find.bySemanticsLabel('Hoola')), containsSemantics(label: 'Hoola', isButton: true, isSelected: true, hasTapAction: true));
    h.dispose();
  });

  testWidgets('v0.904 black: a solid black pill + white icon, no violet tile, the Hoola tab keeps its violet logo', (t) async {
    _phone(t, 390);
    await t.pumpWidget(_bar(2));
    await t.pumpAndSettle();
    final c = HoolaColors.light;
    bool tile(Widget w, Color k) => w is Container && w.decoration is BoxDecoration && (w.decoration as BoxDecoration).color == k;
    expect(find.byWidgetPredicate((w) => tile(w, c.pill)), findsOneWidget, reason: 'one black pill, on the open tab');
    expect(find.byWidgetPredicate((w) => tile(w, c.accentSoft)), findsNothing, reason: 'no violet tile any more');
    final icons = t.widgetList<NavIcon>(find.byType(NavIcon)).toList();
    expect(icons.length, 3);
    expect(icons.firstWhere((i) => i.glyph == NavGlyph.tools).color, c.onPill);
    expect(icons.where((i) => i.glyph != NavGlyph.tools).every((i) => i.color == c.ink2), isTrue);
    expect(t.widget<HoolaMark>(find.byType(HoolaMark)).color, isNull, reason: 'closed Hoola tab = its own violet');

    await t.pumpWidget(_bar(0));
    await t.pumpAndSettle();
    expect(t.widget<HoolaMark>(find.byType(HoolaMark)).color, HoolaColors.darkSet.accent, reason: 'lighter violet on the black pill');
  });
}
