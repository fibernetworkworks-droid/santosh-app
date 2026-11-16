// v0.947 HOOLA AUTO phone (design claude.ai/artifact/1JwAQ3KaPuxzusDHf1UzPz, boards P0-P6): the dot colours, the words the
// screens must show, the design tokens only, and the drawer row. No network: pure functions + the source files.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/hoola_auto.dart';
import 'package:santosh/ui/hoola_theme.dart';

void main() {
  test('state dots: violet = working, amber = needs you, green = done, grey = waiting', () {
    const c = CodeColors.darkSet;
    expect(autoStateColor(c, 'run'), c.accent);
    expect(autoStateColor(c, 'working'), c.accent);
    expect(autoStateColor(c, 'queued'), c.accent);
    expect(autoStateColor(c, 'need'), c.amber);
    expect(autoStateColor(c, 'needs'), c.amber);
    expect(autoStateColor(c, 'paused'), c.amber);
    expect(autoStateColor(c, 'done'), c.green);
    expect(autoStateColor(c, 'wait'), c.ink5);
  });

  test('the Hoola Auto phone file draws from the design tokens only and says the design words', () {
    final s = File('lib/ui/hoola_auto.dart').readAsStringSync();
    expect(RegExp(r'Color\(0x').hasMatch(s), isFalse, reason: 'a raw colour');
    expect(RegExp(r'fontSize:').hasMatch(s), isFalse, reason: 'text sizes come from HcType');
    expect(s.contains("glass.dart'"), isFalse);
    for (final w in [
      'New Auto project',
      'Needs your OK',
      'Hoola asks',
      'Live feed',
      'Open full session',
      'Change request',
      'Ask for changes',
      'Continue to client intake',
      'Send for review',
      'Copy link',
      'Merge into',
      'Waiting for a slot',
      'Hoola Code sessions run at a time on this server',
    ]) {
      expect(s.contains(w), isTrue, reason: w);
    }
    for (final route in ['/api/auto/projects', '/mission', '/agents/', '/message', '/decide', '/golive/', '/intake/', '/client-link', '/review', '/env']) {
      expect(s.contains(route), isTrue, reason: route);
    }
    final drawer = File('lib/ui/devsahayak_drawer.dart').readAsStringSync();
    expect(drawer.contains("'Hoola Auto'"), isTrue);
    expect(drawer.indexOf("'Hoola Auto'") < drawer.indexOf("'Scheduled tasks'"), isTrue, reason: 'right after New session');
  });
}
