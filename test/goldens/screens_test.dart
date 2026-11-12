// R0 EYES FIRST (docs/HOOLA_APP_REDESIGN_PLAN.md): a picture of every main screen, made on CI, so each later
// redesign step is SEEN, not guessed (Flutter does not run where the code is written).
//
// Run:  flutter test --update-goldens test/goldens/
// Out:  test/goldens/shots/<screen>.png  (390 x 844 logical, x2) - uploaded by .github/workflows/app-screens.yml
//
// These are screenshots, not yet a pass / fail comparison: the screens are about to change on purpose. Each screen
// is its own test, so one screen that cannot render on a test machine never hides the others' pictures.
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:santosh/state.dart';
import 'package:santosh/main.dart';
import 'package:santosh/ui/employees_screen.dart';
import 'package:santosh/ui/glass.dart';
import 'package:santosh/ui/setup_screen.dart';

import 'golden_fonts.dart';

/// The phone the pictures are taken on: 390 x 844 logical pixels (a common Android size), at 2x.
const _logical = Size(390, 844);
const _ratio = 2.0;

/// Plugins the screens may call while they open. On a test machine none of them exist; they answer "nothing".
void _quietPlugins() {
  const names = [
    'santosh/native',
    'santosh/links',
    'plugins.flutter.io/url_launcher_android',
    'plugins.flutter.io/path_provider',
    'dexterous.com/flutter/local_notifications',
    'flutter_tts',
    'plugin.csdcorp.com/speech_to_text',
    'flutter_timezone',
  ];
  final m = TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
  for (final n in names) {
    m.setMockMethodCallHandler(MethodChannel(n), (call) async => null);
  }
}

Future<Santosh> _app({Map<String, Object> prefs = const {}}) async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', ...prefs});
  return Santosh.load();
}

/// A small, fixed conversation so the chat picture shows real bubbles, a reply with Markdown, and a card.
void _sampleChat(Santosh app) {
  final at = DateTime(2026, 11, 12, 15, 10).toIso8601String();
  app.feed.add(FeedItem('message', {
    'role': 'user',
    'text': 'Make the October GST summary from my bills and get it ready for my CA',
    'at': at,
  }));
  app.feed.add(FeedItem('message', {
    'role': 'assistant',
    'source': 'agent',
    'text': 'Your October GST summary is ready.\n\n'
        '## What I checked\n\n'
        '- Every purchase and sales bill in your Gmail\n'
        '- Each bill against the GST portal (`GSTR-2B`)\n\n'
        'Two supplier bills are **not filed yet**. Both are listed at the end of the PDF.\n\n'
        '| Part | Status |\n|---|---|\n| Sales bills | Matched |\n| Purchase bills | 2 missing |',
    'at': at,
  }));
}

Future<void> _shot(WidgetTester t, String name, Widget Function(Santosh app) screen,
    {void Function(Santosh app)? prep, Finder? tab, Duration settle = const Duration(milliseconds: 900)}) async {
  final app = await _app();
  prep?.call(app);
  t.view.physicalSize = _logical * _ratio;
  t.view.devicePixelRatio = _ratio;
  addTearDown(t.view.reset);

  await t.pumpWidget(MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: santoshTheme(),
    home: screen(app),
  ));
  // fonts and pictures load for real (outside the fake clock), then a few frames settle the layout
  await t.runAsync(() async {
    await GoogleFonts.pendingFonts();
    await Future<void>.delayed(const Duration(milliseconds: 400));
  });
  await t.pump(settle);
  if (tab != null) {
    // the real app shell: the tab is opened the way she opens it, by tapping the tab bar
    await t.tap(tab.last);
    await t.pump(settle);
    await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
    await t.pump(settle);
  }
  await t.pump(const Duration(milliseconds: 100));
  await expectLater(find.byType(MaterialApp), matchesGoldenFile('shots/$name.png'));

  // leave nothing running: the screen goes, and its timers run out with it
  await t.pumpWidget(const SizedBox.shrink());
  await t.pump(const Duration(seconds: 15));
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    GoogleFonts.config.allowRuntimeFetching = false;   // every font comes from assets/fonts (R0)
    _quietPlugins();
    await loadIconFont();
    await loadHoolaFamilies();
  });

  // the app shell exactly as the phone shows it after setup: Aurora, tab bar, the tab's own screen
  Widget home(Santosh a) => Home(app: a, onReset: () {});
  testWidgets('01 setup (first open)', (t) => _shot(t, '01_setup', (a) => SetupScreen(app: a)));
  testWidgets('02 today tab', (t) => _shot(t, '02_today', home));
  testWidgets('03 chat tab, empty', (t) => _shot(t, '03_chat_empty', home, tab: find.text('Chat')));
  testWidgets('04 chat tab, a reply', (t) => _shot(t, '04_chat_reply', home, prep: _sampleChat, tab: find.text('Chat')));
  testWidgets('05 talk (voice)', (t) => _shot(t, '05_talk', home, tab: find.bySemanticsLabel('Talk — live voice')));
  testWidgets('06 connect tab', (t) => _shot(t, '06_connect', home, tab: find.text('Connect')));
  testWidgets('07 main tab (profile)', (t) => _shot(t, '07_main', home, tab: find.text('Main')));
  testWidgets('08 AI employees', (t) => _shot(t, '08_employees', (a) => EmployeesScreen(app: a)));
}
