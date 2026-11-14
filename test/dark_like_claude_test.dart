// v0.911 DARK LIKE CLAUDE (owner: "CHECK THE DARK MODE DIFFERENCE BETWEEN CLAUDE AND HOOLA" -> "GO"): her two screenshots
// measured - Claude's dark page #131313, text #E1E1E1, the typing box one quiet step up, nothing brighter than a muted
// send button. These numbers keep Hoola's dark mode there: deep neutral page, soft text, no white blobs, a working switch.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/hoola_theme.dart';

double _lum(Color c) => c.computeLuminance();

void main() {
  const d = HoolaColors.darkSet;

  test('a deep, neutral page like Claude (not the warm brown it was)', () {
    expect(_lum(d.bg), lessThan(.008), reason: 'Claude #131313 is about .0065');
    final r = d.bg.red, g = d.bg.green, b = d.bg.blue;
    expect((r - b).abs(), lessThanOrEqualTo(2), reason: 'neutral, no brown tint');
    expect((r - g).abs(), lessThanOrEqualTo(2));
  });

  test('soft text, never pure white', () {
    expect(_lum(d.ink), lessThan(.80), reason: 'near-white text glares at night; Claude uses about .75');
    expect(hoolaContrast(d.ink, d.bg), greaterThan(12));
  });

  test('surfaces one quiet step apart, outlines almost gone', () {
    expect(hoolaContrast(d.surface, d.bg), inInclusiveRange(1.05, 1.35));
    expect(hoolaContrast(d.sunk, d.surface), inInclusiveRange(1.03, 1.35));
    expect(hoolaContrast(d.line, d.surface), lessThan(1.3), reason: 'an outline you feel more than see');
  });

  test('no white blobs: the open tab, the black circles and main buttons are a soft grey in dark', () {
    expect(_lum(d.pill), lessThan(.06), reason: 'was #F3F1EC (.88) - the brightest thing on her screen');
    expect(hoolaContrast(d.pill, d.surface), greaterThan(1.4), reason: 'still clearly a button');
    expect(hoolaContrast(d.onPill, d.pill), greaterThanOrEqualTo(4.5));
    expect(d.nav, d.surface, reason: 'the tab bar is the same quiet step as the typing box');
  });

  test('a switch that is ON is still clearly on in dark', () {
    final t = hoolaTheme(Brightness.dark);
    final on = t.switchTheme.trackColor!.resolve({WidgetState.selected})!;
    final off = t.switchTheme.trackColor!.resolve({})!;
    expect(hoolaContrast(on, off), greaterThan(3));
  });

  test('light mode is untouched', () {
    expect(HoolaColors.light.bg, const Color(0xFFFAF9F6));
    expect(HoolaColors.light.pill, const Color(0xFF1B1A17));
  });
}
