// v0.879 HOOLA CODE PHONE (owner-approved design docs/design/hoola_code/Phone*.png): the words and colours the new
// Hoola Code phone screens show, and the switch from the design. No network: pure functions + one small widget.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/devsahayak_kit.dart';
import 'package:santosh/ui/devsahayak_new.dart';
import 'package:santosh/ui/devsahayak_session.dart';
import 'package:santosh/ui/hoola_theme.dart';

void main() {
  test('the dark set is the design: page, sheet, cream button, the one violet, diff rows', () {
    const c = CodeColors.darkSet;
    expect(c.bg, const Color(0xFF1C1B1A));
    expect(c.sheet, const Color(0xFF232220));
    expect(c.cream, const Color(0xFFF3F1EC));
    expect(c.onCream, const Color(0xFF1B1A17));
    expect(c.accent, const Color(0xFF9C88FF));
    expect(c.onAccent, const Color(0xFF14102B));
    expect(c.accentTint, const Color(0xFF2B2947));
    expect(c.addBg, const Color(0xFF1A3226));
    expect(c.delBg, const Color(0xFF36211E));
    // text on its own surfaces stays readable in both sets
    for (final s in [CodeColors.darkSet, CodeColors.lightSet]) {
      expect(hoolaContrast(s.ink, s.bg), greaterThanOrEqualTo(4.5));
      expect(hoolaContrast(s.ink3, s.bg), greaterThanOrEqualTo(4.5));
      expect(hoolaContrast(s.onCream, s.cream), greaterThanOrEqualTo(4.5));
      expect(hoolaContrast(s.onAccent, s.accent), greaterThanOrEqualTo(4.5));
      expect(hoolaContrast(s.addInk, s.addBg), greaterThanOrEqualTo(4.5));
      expect(hoolaContrast(s.delInk, s.delBg), greaterThanOrEqualTo(4.5));
    }
  });

  test('session words: status under a row, the +N −M count, the working clock, an environment line', () {
    expect(devStatusWords({'running': true, 'status': 'new'}), 'working');
    expect(devStatusWords({'status': 'explained', 'question': 'Which file?'}), 'needs you');
    expect(devStatusWords({'status': 'pr_open', 'pr_number': 213}), 'PR #213 open');
    expect(devStatusWords({'status': 'checks_failed', 'pr_number': 9}), 'PR #9 CI failed');
    expect(devStatusWords({'status': 'merged', 'pr_number': 9}), 'merged');
    expect(devStat({
      'files': [
        {'added': 40, 'removed': 9},
        {'added': '2', 'removed': 0},
      ]
    }), [42, 9]);
    expect(hcClock(14), '14s');
    expect(hcClock(102), '1m 42s');
    expect(hcClock(3720), '1h 02m');
    expect(hcShortRepo('fibernetworkworks-droid/santosh-app'), 'santosh-app');
    expect(devEnvSub({'net': {'level': 'limited'}, 'setup': ''}), 'Hoola cloud · limited network');
    expect(devEnvSub({'net': {'level': 'full'}, 'setup': 'npm ci'}), 'Hoola cloud · full network · setup script');
  });

  testWidgets('the design switch toggles and says so', (t) async {
    var on = false;
    await t.pumpWidget(MaterialApp(
      home: Scaffold(
        body: StatefulBuilder(
          builder: (context, set) => Center(child: HcSwitch(value: on, label: 'Auto-fix', onChanged: (v) => set(() => on = v))),
        ),
      ),
    ));
    await t.tap(find.byType(HcSwitch));
    await t.pumpAndSettle();
    expect(on, isTrue);
    expect(t.getSize(find.byType(HcSwitch)).height, greaterThanOrEqualTo(48));
  });

  test('the Hoola Code phone files draw from the design tokens only (no raw colour, no glass, English)', () {
    for (final name in ['devsahayak_kit', 'devsahayak_new', 'devsahayak_session', 'devsahayak_drawer']) {
      final s = File('lib/ui/$name.dart').readAsStringSync();
      expect(RegExp(r'Color\(0x').hasMatch(s), isFalse, reason: '$name: a raw colour');
      expect(s.contains("glass.dart'"), isFalse, reason: '$name builds on glass.dart');
      for (final w in ['Kaam', 'kijiye', 'Haan,']) {
        expect(s.contains(w), isFalse, reason: '$name says $w');
      }
    }
    final home = File('lib/ui/devsahayak_new.dart').readAsStringSync();
    for (final w in ['Ready when you are', 'Type or hold to talk', 'Select environment', 'Connect more on GitHub', 'Limited (Recommended)']) {
      expect(home.contains(w), isTrue, reason: w);
    }
    final session = File('lib/ui/devsahayak_session.dart').readAsStringSync();
    for (final w in ['Steer or queue a message', 'Long-press a line to comment · merging is always your tap', 'Goes with your next message']) {
      expect(session.contains(w), isTrue, reason: w);
    }
    final drawer = File('lib/ui/devsahayak_drawer.dart').readAsStringSync();
    for (final w in ['Scheduled tasks', 'Search sessions', 'At most once a day · times in India time · each run is its own session']) {
      expect(drawer.contains(w), isTrue, reason: w);
    }
  });
}
