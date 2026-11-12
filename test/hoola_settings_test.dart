// v0.867 R7: every row of the old Main page still has exactly one way in - a screen it opened is in Settings or in
// Your AI team, and every inline setting it held is in Settings.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/shell/hoola_settings.dart';
import 'package:santosh/ui/shell/hoola_team_list.dart';

void main() {
  final old = File('lib/ui/profile_screen.dart').readAsStringSync();
  final settings = File('lib/ui/shell/hoola_settings.dart').readAsStringSync();
  final team = File('lib/ui/shell/hoola_team_list.dart').readAsStringSync();

  test('every screen the old Main page opened is in Settings or Your AI team, once', () {
    final opened = {for (final m in RegExp(r'builder: \(_\) => (\w+)\(').allMatches(old)) m.group(1)!};
    expect(opened.length, greaterThan(100));
    final missing = <String>[], twice = <String>[];
    for (final s in opened) {
      final inSettings = RegExp('\\b$s\\(').hasMatch(settings);
      final n = RegExp('\\(a\\) => $s\\(').allMatches(team).length;
      if (!inSettings && n == 0) missing.add(s);
      if ((inSettings ? 1 : 0) + n > 1) twice.add(s);
    }
    expect(missing, isEmpty, reason: 'old Main rows with no way in');
    expect(twice, isEmpty, reason: 'old Main rows in more than one place');
  });

  test('every inline setting of the old Main page is in Settings', () {
    const held = [
      'saveProfile', "'briefing_time'", "'city'", 'saveSettings(lang:', 'saveSettings(speak:', 'saveAvatar(voice:',
      'saveAvatar(look:', 'setBackground(', 'askBattery', 'askExactAlarms', 'askCalendar', 'HoolaKeepAlive.open',
      'wakeStart', 'wakeStop', 'disconnectProvider', 'pinMemory', '.forget(', 'signOut', 'dryRun', 'setNewLook',
      'setAppearance', 'rulesOnly: true',
    ];
    for (final h in held) {
      expect(old.contains(h) || h == "'city'", isTrue, reason: 'old page no longer has $h - update this list');
      expect(settings.contains(h), isTrue, reason: 'Settings lost: $h');
    }
  });

  test('team search keeps the group order and matches every word', () {
    Widget open(_) => const SizedBox();
    final all = [
      HoolaTeamEntry('Software and IT', Icons.code, 'Developer', 'Repos, pull requests', open),
      HoolaTeamEntry('Hire and manage', Icons.groups, 'AI employees', 'Hire staff', open),
      HoolaTeamEntry('Tools and apps', Icons.mail, 'Email', 'Gmail, Outlook', open),
    ];
    final s = teamSections(all, '');
    expect(s.map((x) => x.$1), ['Hire and manage', 'Software and IT', 'Tools and apps']);
    expect(teamSections(all, 'gmail').single.$2.single.title, 'Email');
    expect(teamSections(all, 'pull developer').single.$1, 'Software and IT');
    expect(teamSections(all, 'nothing like this'), isEmpty);
  });
}
