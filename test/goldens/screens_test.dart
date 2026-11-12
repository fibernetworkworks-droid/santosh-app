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

/// v0.862 R3: a chat with what the new chat draws - steps, a reply with a heading, list, code and a table, and her
/// next ask being worked on (the working mark) or answered word by word (the soft tail).
void _richChat(Santosh app, {bool working = false, bool writing = false}) {
  final at = DateTime(2026, 11, 12, 15, 10).toIso8601String();
  app.feed.add(FeedItem('message', {'role': 'user', 'text': 'Which supplier bills are missing from GSTR-2B this month?', 'at': at}));
  final steps = FeedItem('steps', {});
  steps.steps.addAll([
    {'label': 'Finding the right tools', 'state': 'done', 'kind': 'other', 'housekeeping': true},
    {'label': 'Searching your Gmail for bills', 'state': 'done', 'kind': 'search'},
    {'label': 'Reading 38 bills', 'state': 'done', 'kind': 'read'},
    {'label': 'Checking each bill against GSTR-2B', 'state': 'done', 'kind': 'run'},
  ]);
  app.feed.add(steps);
  app.feed.add(FeedItem('think', {'text': 'Two bills are in her mail but not in 2B.', 'done': true, 'secs': 6}));
  app.feed.add(FeedItem('message', {
    'role': 'assistant',
    'turn': 't1',
    'text': '## Two bills are missing\n\n'
        'Both suppliers have **not filed** their GSTR-1 yet, so the credit is not in your `GSTR-2B`.\n\n'
        '| Supplier | Bill | GST |\n|---|---|---|\n| Shree Traders | 4512 | Rs 8,640 |\n| Patil Steel | 0981 | Rs 12,150 |\n\n'
        '1. Ask them to file before the 11th\n2. Keep the credit on hold till then\n\n'
        '```text\nGSTIN 27AAGCB1286Q1ZL  Shree Traders\n```',
    'at': at,
  }));
  if (working || writing) {
    app.feed.add(FeedItem('message', {'role': 'user', 'text': 'Draft a polite reminder to both of them', 'at': at}));
    app.typing = true;
    app.currentStep = 'Writing the reminder';
  }
  if (writing) {
    app.feed.add(FeedItem('stream', {'turn': 't2', 'text': 'Dear Shree Traders, our October books show your bill 4512 is not yet in', 'seg': 0}));
  }
}

/// v0.864 R4: the redrawn cards in a chat - an approval waiting for her yes, a payment, a made file, a page, a
/// default card.
void _cardsChat(Santosh app) {
  final at = DateTime(2026, 11, 12, 15, 10).toIso8601String();
  app.feed.add(FeedItem('message', {'role': 'user', 'text': 'Send the Diwali offer to my 40 regular customers', 'at': at}));
  app.feed.add(FeedItem('bazar', {
    'id': 'ap1', 'status': 'pending', 'money': false, 'title': 'Send the Diwali offer on WhatsApp',
    'payee': '40 regular customers', 'voice_ok': true,
  }));
  app.feed.add(FeedItem('bazar', {
    'id': 'ap2', 'status': 'pending', 'money': true, 'title': 'Pay Shree Traders for October', 'payee': 'Shree Traders',
    'amount': '₹ 8,640', 'pay_method': 'UPI · HDFC', 'needs_pin': true,
    'items': [{'name': 'Bill 4512', 'price': '₹ 8,640'}],
  }));
}

void _madeChat(Santosh app) {
  final at = DateTime(2026, 11, 12, 15, 10).toIso8601String();
  app.feed.add(FeedItem('message', {'role': 'user', 'text': 'Make the October GST summary and an offer page', 'at': at}));
  app.feed.add(FeedItem('pc_file', {'source': 'bazar', 'name': 'October_GST_summary.pdf', 'size': 248000, 'doc_id': 'd1'}));
  app.feed.add(FeedItem('artifact', {'id': 'a1', 'status': 'ready', 'title': 'Diwali offer page', 'version': 2,
    'summary': 'One page with the offer, the prices and a WhatsApp button'}));
  final any = FeedItem('any_card', {'_kind': 'courier_parcel', 'title': 'Parcel to Pune', 'status': 'running', 'say': 'Picked up, on the way',
    'awb': 'DL778812', 'step': 2, 'total': 4});
  app.feed.add(any);
}

Future<void> _shot(WidgetTester t, String name, Widget Function(Santosh app) screen,
    {void Function(Santosh app)? prep, Finder? tab, Map<String, Object> prefs = const {}, Duration settle = const Duration(milliseconds: 900)}) async {
  final app = await _app(prefs: prefs);
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

  // v0.861 R2: the new frame (Main > Try the new design), light and dark
  void chats(Santosh a) => a.chatList = [
        for (final t in ['October GST summary', 'Reply to WhatsApp leads', 'Diwali offer poster', 'Clinic website changes',
          'Supplier bills not in GSTR-2B', 'Pune delivery route'])
          {'id': t, 'title': t, 'result': {
            'status': t.startsWith('Reply') ? 'working' : t.startsWith('Diwali') ? 'needs_you' : t.startsWith('Pune') ? 'failed' : 'done',
            'needs_you': t.startsWith('Diwali'),
          }},
        {'id': 'call1', 'title': 'Call with Santosh · 6:40 pm', 'kind': 'call'},
      ];
  for (final mode in ['light', 'dark']) {
    final prefs = <String, Object>{'new_look': true, 'appearance': mode};
    testWidgets('30 new home ($mode)', (t) => _shot(t, '30_new_home_$mode', home, prefs: prefs));
    testWidgets('31 new drawer ($mode)', (t) => _shot(t, '31_new_drawer_$mode', home, prefs: prefs, prep: chats, tab: find.byTooltip('Open chats')));
    testWidgets('32 new work tab ($mode)', (t) => _shot(t, '32_new_work_$mode', home, prefs: prefs, tab: find.text('Work')));
    // v0.862 R3 the new chat
    testWidgets('33 new chat ($mode)', (t) => _shot(t, '33_new_chat_$mode', home, prefs: prefs, prep: _richChat));
    testWidgets('34 new chat working ($mode)', (t) => _shot(t, '34_new_chat_working_$mode', home, prefs: prefs,
        prep: (a) => _richChat(a, working: true)));
    testWidgets('36 new cards ($mode)', (t) => _shot(t, '36_new_cards_$mode', home, prefs: prefs, prep: _cardsChat));
    testWidgets('37 new made cards ($mode)', (t) => _shot(t, '37_new_made_$mode', home, prefs: prefs, prep: _madeChat));
    testWidgets('35 new chat writing ($mode)', (t) => _shot(t, '35_new_chat_writing_$mode', home, prefs: prefs,
        prep: (a) => _richChat(a, writing: true)));
  }
}
