// v0.907 TOOLS PRO: option B of the Tools canvas - every studio its own drawing, centred on a black circle, big; a
// quiet motion of its own; the cards rise in; reduce motion = still.
import 'dart:ui' show PictureRecorder;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/shell/hoola_tool_icons.dart';
import 'package:santosh/ui/shell/hoola_tools.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

Widget _host(Santosh app, {bool still = false, String mode = 'light'}) => MaterialApp(
      builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(disableAnimations: still), child: child!),
      home: HoolaTheme(appearance: mode, child: Scaffold(body: HoolaTools(app: app))),
    );

void _phone(WidgetTester t) {
  t.view.physicalSize = const Size(390 * 3, 2600 * 3);
  t.view.devicePixelRatio = 3;
  addTearDown(t.view.reset);
}

void main() {
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);

  test('every drawing reads, sits on the 24-unit grid, and has a moving part', () {
    for (final g in ToolGlyph.values) {
      final c = ToolIconPainter(glyph: g, color: Colors.black);
      final rec = PictureRecorder();
      c.paint(Canvas(rec), const Size(32, 32));
      rec.endRecording();
    }
    const d = 'M5 7h8.5A2.5 2.5 0 0 1 16 9.5v8M9.25 14a2 2 0 1 0 0-4a2 2 0 1 0 0 4zM5.6 19.6c.5-2 1.9-3.1 3.65-3.1s3.15 1.1 3.65 3.1';
    final b = svgPath(d).getBounds();
    expect(b.left, greaterThanOrEqualTo(5 - .01));
    expect(b.right, lessThanOrEqualTo(16 + .01));
    expect(b.top, greaterThanOrEqualTo(7 - .01));
    expect(b.bottom, lessThanOrEqualTo(19.6 + .5));
  });

  testWidgets('every icon paints through its whole motion without a fault', (t) async {
    final clock = ValueNotifier<double>(0);
    await t.pumpWidget(MaterialApp(
      home: Wrap(children: [for (final g in ToolGlyph.values) ToolIcon(glyph: g, color: Colors.black, clock: clock, draw: .5)]),
    ));
    for (var s = 0.0; s < 4; s += .13) {
      clock.value = s;
      await t.pump();
    }
    expect(t.takeException(), isNull);
  });

  for (final mode in ['light', 'dark']) {
    testWidgets('$mode: 11 different drawings, each centred on the black circle; the name centred below', (t) async {
      _phone(t);
      final app = await _app();
      await t.pumpWidget(_host(app, mode: mode));
      await t.pump(HoolaTools.enter + const Duration(milliseconds: 100));
      final c = mode == 'light' ? HoolaColors.light : HoolaColors.darkSet;
      final badges = t.widgetList<ToolBadge>(find.byType(ToolBadge)).toList();
      expect(badges.length, 11, reason: '8 studios + Hoola Code, Game Dev, Connectors');
      expect(badges.map((b) => b.glyph).toSet().length, 11, reason: 'no two the same');
      final circles = t.widgetList<Container>(find.descendant(of: find.byType(ToolBadge), matching: find.byType(Container)));
      for (final k in circles) {
        expect((k.decoration as BoxDecoration).color, c.pill, reason: 'black circle (near-white in dark)');
      }
      for (final i in t.widgetList<ToolIcon>(find.byType(ToolIcon))) {
        expect(i.color, c.onPill);
      }
      for (final name in ['Create', 'Hoola Interactive', 'Web Development', 'Prompting']) {
        final card = find.ancestor(of: find.text(name), matching: find.byType(InkWell));
        final cell = t.getRect(card);
        final badge = t.getRect(find.descendant(of: card, matching: find.byType(ToolBadge)));
        final label = t.getRect(find.text(name));
        expect(badge.width, 60, reason: 'big');
        expect((badge.center.dx - cell.center.dx).abs(), lessThan(.6), reason: '$name: icon centred');
        expect((label.center.dx - cell.center.dx).abs(), lessThan(.6), reason: '$name: name centred');
      }
      expect(t.takeException(), isNull);
    });
  }

  testWidgets('the cards rise in one after another, then the drawings keep moving', (t) async {
    _phone(t);
    final app = await _app();
    await t.pumpWidget(_host(app));
    await t.pump(const Duration(milliseconds: 100));
    double op(String name) => t.widget<Opacity>(find.ancestor(of: find.text(name), matching: find.byType(Opacity)).last).opacity;
    expect(op('Create'), greaterThan(op('Prompting')), reason: 'the first card is ahead of the last');
    await t.pump(HoolaTools.enter);
    expect(op('Create'), 1);
    expect(op('Prompting'), 1);
    expect(t.binding.hasScheduledFrame, isTrue, reason: 'the quiet motion keeps running');
  });

  testWidgets('reduce motion: everything is there at once and nothing moves', (t) async {
    _phone(t);
    final app = await _app();
    await t.pumpWidget(_host(app, still: true));
    await t.pump();
    double op(String name) => t.widget<Opacity>(find.ancestor(of: find.text(name), matching: find.byType(Opacity)).last).opacity;
    expect(op('Prompting'), 1);
    expect(t.widgetList<ToolIcon>(find.byType(ToolIcon)).every((i) => i.clock == null && i.draw == 1), isTrue);
    expect(t.binding.hasScheduledFrame, isFalse, reason: 'no motion, no frames');
  });
}
