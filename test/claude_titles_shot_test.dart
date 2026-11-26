// v0.999.206 a picture of the greeting and a page title, light and dark, to check them by eye (HOOLA_SHOTS=dir).
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/hoola_theme.dart';

import 'goldens/golden_fonts.dart';

void main() {
  setUpAll(loadHoolaFamilies);
  for (final dark in [false, true]) {
    testWidgets('greeting + title ${dark ? 'dark' : 'light'}: the light cut is thinner than the regular serif', (t) async {
      final c = dark ? HoolaColors.darkSet : HoolaColors.light;
      final key = GlobalKey();
      await t.pumpWidget(MaterialApp(
        home: Material(child: RepaintBoundary(
          key: key,
          child: Container(
            color: c.bg,
            padding: const EdgeInsets.all(20),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text('Good evening, Asha', style: HoolaType.hero(c)),
              const SizedBox(height: 16),
              Text('AI Employees', style: HoolaType.pageTitle(c)),
              const SizedBox(height: 16),
              Text('Good evening, Asha', style: HoolaType.serifFigure(c).copyWith(fontSize: 38, letterSpacing: 0)),
            ]),
          ),
        )),
      ));
      await t.pumpAndSettle();
      // the light cut sets the same words a little narrower than the regular Literata at the same size
      final w = t.getSize(find.text('Good evening, Asha').first).width;
      final r = t.getSize(find.text('Good evening, Asha').last).width;
      expect(w, lessThan(r));
      final dir = Platform.environment['HOOLA_SHOTS'];
      if (dir != null) {
        final ro = key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
        final img = await t.runAsync(() => ro.toImage(pixelRatio: 2));
        final png = await t.runAsync(() => img!.toByteData(format: ui.ImageByteFormat.png));
        File('$dir/titles_${dark ? 'dark' : 'light'}.png').writeAsBytesSync(png!.buffer.asUint8List());
      }
    });
  }
}
