// v0.999.206 the phone's greetings and page titles like Claude's: Literata 38 / 1.2 at 330 (dark 290), titles 28 / 530.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/hoola_theme.dart';

void main() {
  test('greeting = Literata 38 / 1.2, the light cut, the darker-mode cut in dark', () {
    final l = HoolaType.hero(HoolaColors.light);
    final d = HoolaType.hero(HoolaColors.darkSet);
    expect(l.fontFamily, HoolaFont.greet);
    expect(d.fontFamily, HoolaFont.greetDark);
    expect(l.fontSize, 38);
    expect(l.height, 1.2);
    expect(l.letterSpacing, isNull);
  });

  test('page title = Literata 28 / 1.25 at 530', () {
    final t = HoolaType.pageTitle(HoolaColors.light);
    expect(t.fontFamily, HoolaFont.title);
    expect(t.fontSize, 28);
    expect(t.height, 1.25);
    expect(t.fontWeight, FontWeight.w600);
  });

  test('a figure on a card keeps the regular serif', () {
    expect(HoolaType.serifFigure(HoolaColors.light).fontFamily, HoolaFont.serif);
  });
}
