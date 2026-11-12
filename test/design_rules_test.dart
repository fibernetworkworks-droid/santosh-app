// v0.860 R1 THE DESIGN SYSTEM rules (docs/HOOLA_APP_REDESIGN_PLAN.md section 1).
//  1. Every text colour pair of the new palette reads at 4.5:1 or better, light AND dark.
//  2. The new theme builds for both brightnesses and carries its colour roles.
//  3. A RATCHET over lib/: raw Color(0x..), text under 12 and weights 800/900 may only go DOWN per file
//     (test/design_baseline.json). A new file starts at zero - it takes everything from hoola_theme.dart.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/hoola_theme.dart';

void main() {
  test('every text pair of the palette reads at 4.5:1 or better', () {
    for (final set in [HoolaColors.light, HoolaColors.darkSet]) {
      for (final (fg, bg, name) in set.readablePairs) {
        final r = hoolaContrast(fg, bg);
        expect(r, greaterThanOrEqualTo(4.5), reason: '${set.dark ? 'dark' : 'light'} $name is ${r.toStringAsFixed(2)}:1');
      }
    }
  });

  test('the theme builds light and dark with its colour roles and fonts', () {
    for (final b in Brightness.values) {
      final t = hoolaTheme(b);
      final c = t.extension<HoolaColors>()!;
      expect(c.dark, b == Brightness.dark);
      expect(t.scaffoldBackgroundColor, c.bg);
      expect(t.textTheme.bodyMedium!.fontFamily, HoolaFont.sans);
      expect(t.textTheme.displayLarge!.fontFamily, HoolaFont.serif);
      // the type scale: nothing under 12, nothing heavier than 700
      for (final s in [
        t.textTheme.displayLarge, t.textTheme.headlineSmall, t.textTheme.titleLarge, t.textTheme.titleMedium,
        t.textTheme.bodyLarge, t.textTheme.bodyMedium, t.textTheme.bodySmall, t.textTheme.labelMedium,
        t.textTheme.labelSmall, HoolaType.reply(c), HoolaType.code(c),
      ]) {
        expect(s!.fontSize!, greaterThanOrEqualTo(12));
        expect(s.fontWeight!.index, lessThanOrEqualTo(FontWeight.w700.index));
      }
    }
    expect(hoolaMode('dark'), ThemeMode.dark);
    expect(hoolaMode('light'), ThemeMode.light);
    expect(hoolaMode('anything'), ThemeMode.system);
  });

  test('ratchet: raw colours, tiny text and 800/900 weights never grow in lib/', () {
    final base = (jsonDecode(File('test/design_baseline.json').readAsStringSync()) as Map)['files'] as Map;
    final grew = <String>[];
    final raw = RegExp(r'Color\(0x');
    final size = RegExp(r'fontSize:\s*(\d+(?:\.\d+)?)');
    final heavy = RegExp(r'FontWeight\.w(?:800|900)');
    for (final f in Directory('lib').listSync(recursive: true).whereType<File>()) {
      final path = f.path.replaceAll('\\', '/');
      if (!path.endsWith('.dart') || path.endsWith('hoola_theme.dart')) continue;
      final s = f.readAsStringSync();
      final now = [
        raw.allMatches(s).length,
        size.allMatches(s).where((m) => double.parse(m.group(1)!) < 12).length,
        heavy.allMatches(s).length,
      ];
      final was = (base[path] as List?)?.cast<int>() ?? [0, 0, 0];
      const what = ['raw Color(0x..)', 'fontSize under 12', 'FontWeight w800/w900'];
      for (var i = 0; i < 3; i++) {
        if (now[i] > was[i]) grew.add('$path: ${what[i]} ${was[i]} -> ${now[i]} (use lib/ui/hoola_theme.dart)');
      }
    }
    expect(grew, isEmpty, reason: grew.join('\n'));
  });

  // R9: glass.dart (Night Glass) cannot be deleted yet - ~220 old screens still build on its widgets, which the new
  // design draws flat (NightGlass.flat). This ratchet makes sure it only shrinks: a new file never builds on it, and
  // the baseline below is lowered as screens move to lib/ui/hoola_theme.dart. Nothing anywhere blurs any more.
  test('ratchet: fewer files build on glass.dart, and nothing blurs', () {
    const baseline = 222;   // v0.872.0
    final users = [
      for (final f in Directory('lib').listSync(recursive: true).whereType<File>())
        if (f.path.endsWith('.dart') && f.readAsStringSync().contains("glass.dart'")) f.path
    ];
    expect(users.length, lessThanOrEqualTo(baseline), reason: 'a new file builds on glass.dart: use hoola_theme.dart');
    final blur = [
      for (final f in Directory('lib').listSync(recursive: true).whereType<File>())
        if (f.path.endsWith('.dart') && !f.path.endsWith('glass.dart') && RegExp(r'BackdropFilter|ImageFilter\.blur').hasMatch(f.readAsStringSync())) f.path
    ];
    expect(blur, isEmpty, reason: 'blur costs frames on a budget phone');
  });
}
