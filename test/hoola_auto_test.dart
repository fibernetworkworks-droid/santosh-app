// v0.947 HOOLA AUTO phone (design claude.ai/artifact/1JwAQ3KaPuxzusDHf1UzPz, boards P0-P6): the dot colours, the words the
// screens must show, the design tokens only, and the drawer row. No network: pure functions + the source files.
import 'dart:io';

import 'package:flutter/material.dart';
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
    for (final w in ['Add source', 'Talk to the Intake agent', 'Spoken answers come in as Found', 'Monitor', 'Fix it',
        'You merge it yourself', 'Check now', 'From an app', 'Files up to 12 MB']) {
      expect(s.contains(w), isTrue, reason: w);
    }
    for (final route in ['/api/auto/projects', '/mission', '/agents/', '/message', '/decide', '/golive/', '/intake/', '/client-link', '/review', '/env',
        '/sources', '/talk', '/watch', '/watch/check', '/alerts/', '/api/auto/apps']) {
      expect(s.contains(route), isTrue, reason: route);
    }
    final drawer = File('lib/ui/devsahayak_drawer.dart').readAsStringSync();
    expect(drawer.contains("'Hoola Auto'"), isTrue);
    expect(drawer.indexOf("'Hoola Auto'") < drawer.indexOf("'Scheduled tasks'"), isTrue, reason: 'right after New session');
  });

  test('v0.949 sources: states in words, polling only while one is read, the 12 MB limit, five kinds', () {
    expect(autoSourceState({'status': 'reading'}), 'Reading');
    expect(autoSourceState({'status': 'failed'}), 'Could not read');
    expect(autoSourceState({'status': 'done', 'answers': 1}), '1 answer');
    expect(autoSourceState({'status': 'done', 'answers': 4}), '4 answers');
    expect(autoAnyReading([{'status': 'done'}, {'status': 'reading'}]), isTrue);
    expect(autoAnyReading([{'status': 'done'}]), isFalse);
    expect(autoSizeProblem(1024), '');
    expect(autoSizeProblem(13 * 1024 * 1024), contains('Files up to 12 MB'));
    expect([for (final k in autoSourceKinds) k.$1], ['text', 'doc', 'recording', 'repo', 'app']);
    expect(autoEveryLabel(60), '1 hour');
    expect(autoEveryLabel(1440), '1 day');
  });

  testWidgets('v0.949 the add-source list names every kind and says which one she tapped', (t) async {
    String? picked;
    await t.pumpWidget(MaterialApp(home: Scaffold(body: AutoSourceKindList(onPick: (k) => picked = k))));
    for (final w in ['Paste email or chat', 'Document', 'Recording', 'Repo scan', 'From an app']) {
      expect(find.text(w), findsOneWidget, reason: w);
    }
    await t.tap(find.text('From an app'));
    expect(picked, 'app');
  });

  testWidgets('v0.949 a Monitor alert: open = Fix it + Dismiss, fixing = the fix line, dismissed = Reopen', (t) async {
    final acts = <String>[];
    Widget card(Map<String, dynamic> a) => MaterialApp(home: Scaffold(body: AutoAlertCard(alert: a, onAct: acts.add, onOpen: (_) {})));
    await t.pumpWidget(card({'id': 'aa1', 'state': 'open', 'title': 'CI is red on main of me/clinic', 'detail': '1 check failed', 'times': 3}));
    expect(find.text('CI is red on main of me/clinic'), findsOneWidget);
    expect(find.text('seen 3 times'), findsOneWidget);
    await t.tap(find.text('Fix it'));
    await t.tap(find.text('Dismiss'));
    expect(acts, ['fix', 'dismiss']);
    await t.pumpWidget(card({'id': 'aa1', 'state': 'fixing', 'title': 'x', 'times': 1,
        'fix': {'say': 'Pull request #12 waits for your merge in Hoola Code.', 'url': 'https://github.com/me/clinic/pull/12'}}));
    expect(find.text('Pull request #12 waits for your merge in Hoola Code.'), findsOneWidget);
    expect(find.text('Open pull request'), findsOneWidget);
    expect(find.text('Fix it'), findsNothing);
    await t.pumpWidget(card({'id': 'aa1', 'state': 'dismissed', 'title': 'x', 'times': 1}));
    await t.tap(find.text('Reopen'));
    expect(acts.last, 'reopen');
  });
}
