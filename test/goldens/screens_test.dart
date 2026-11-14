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

import 'package:santosh/call_session.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/desk/desk_kit.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/shell/hoola_settings.dart';
import 'package:santosh/ui/shell/hoola_employees.dart';
import 'package:santosh/ui/shell/hoola_tabs.dart';
import 'package:santosh/ui/shell/hoola_tools.dart';
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

/// v0.900 every card in the new design: a long task running, a question from a job, a memory line, a finished task.
void _goalChat(Santosh app) {
  final at = DateTime(2026, 11, 14, 10, 1).toIso8601String();
  app.feed.add(FeedItem('message', {'role': 'user', 'text': 'Deep research on Indian banking with revenues, make a PDF', 'at': at}));
  app.feed.add(FeedItem('goal', {
    'id': 'g1', 'title': 'Deep research on Indian banking: banks and revenues', 'status': 'working',
    'started_at': DateTime.now().toUtc().subtract(const Duration(minutes: 4, seconds: 12)).toIso8601String(),
    'done': 1, 'total': 6, 'pct': 17,
    'steps': [
      {'n': 1, 'text': 'Bank list and sector overview', 'state': 'done'},
      {'n': 2, 'text': 'Public sector bank revenues', 'state': 'current'},
      {'n': 3, 'text': 'Private sector bank revenues', 'state': 'pending'},
      {'n': 4, 'text': 'Small finance banks and RRBs', 'state': 'pending'},
      {'n': 5, 'text': 'Check every figure against two sources', 'state': 'pending'},
      {'n': 6, 'text': 'Build the PDF', 'state': 'pending'},
    ],
  }));
  app.feed.add(FeedItem('operator_ask', {
    'id': 'q1', 'kind': 'choice', 'status': 'pending', 'site': 'swiggy.com', 'reason': 'Which pizza should I add?',
    'options': ['Margherita · ₹249', 'Farmhouse · ₹399', 'Peppy Paneer · ₹379'],
  }));
  app.feed.add(FeedItem('memory_used', {'items': [{'label': 'Your GSTIN', 'text': '27AAGCB1286Q1ZL'}]}));
  app.feed.add(FeedItem('goal', {
    'id': 'g2', 'title': 'October GST summary for the CA', 'status': 'done', 'done': 3, 'total': 3, 'pct': 100,
    'steps': [
      {'n': 1, 'text': 'Read 38 bills', 'state': 'done'},
      {'n': 2, 'text': 'Match against GSTR-2B', 'state': 'done'},
      {'n': 3, 'text': 'Build the PDF', 'state': 'done'},
    ],
    'report': {'summary': 'Two bills are missing from 2B; the PDF is ready.', 'bana': ['October_GST_summary.pdf']},
  }));
}

/// v0.900 a calendar entry, places nearby and a desk card that keeps its full card behind Details.
void _moreCards(Santosh app) {
  final at = DateTime(2026, 11, 14, 10, 1).toIso8601String();
  app.feed.add(FeedItem('message', {'role': 'user', 'text': 'Book a call with the CA and find a chemist nearby', 'at': at}));
  app.feed.add(FeedItem('calendar_event', {'title': 'Call with CA Kulkarni', 'status': 'added', 'start': 'Tue 18 Nov, 4:00 pm',
    'end': 'Tue 18 Nov, 4:30 pm', 'meet_link': 'https://meet.google.com/abc', 'link': 'https://calendar.google.com'}));
  app.feed.add(FeedItem('maps_places', {'title': 'Chemists', 'near': 'Ramdaspeth', 'places': [
    {'name': 'Sai Medical & General', 'rating': 4.6, 'distance_km': 0.6, 'open_now': true, 'maps_link': 'https://maps.google.com/?q=1'},
    {'name': 'Apollo Pharmacy', 'rating': 4.3, 'distance_km': 1.2, 'open_now': true, 'maps_link': 'https://maps.google.com/?q=2'},
  ]}));
  app.feed.add(FeedItem('thok_order', {'order_id': 'o1', 'title': 'Order from Sharma Traders', 'status': 'pending',
    'text': '40 boxes of soan papdi for Diwali', 'buyer': 'Sharma Traders'}));
}

/// v0.865 R5: a call in progress (the fields the screen reads; no real call is started in a test).
void _inCall(Santosh app) {
  final c = app.voiceCall;
  c.inCall = true;
  c.act = CallAct.speaking;
  c.startedAt = DateTime.now().subtract(const Duration(minutes: 2, seconds: 14));
  c.heard = 'Did Shree Traders file their GSTR-1 yet?';
  c.reply = 'Not yet. Their October bill is still missing from your 2B, so I have drafted a reminder for them.';
}

/// v0.866 R6: what the Work, Connect and Made tabs read (the tests have no server).
void _tabsData(Santosh app) {
  final now = DateTime.now().toUtc();
  String ago(int m) => now.subtract(Duration(minutes: m)).toIso8601String();
  HoolaTabsDebug.kaam = {
    'waiting': [
      {'title': 'Pick one of three website looks', 'state': 'waiting', 'conversation_id': 'w1', 'at': ago(20)},
    ],
    'running': [
      {'title': 'October GST summary for your CA', 'state': 'working', 'conversation_id': 'w2', 'at': ago(4),
       'detail': 'Matching 48 purchase bills with GSTR-2B'},
    ],
    'done': [
      {'title': 'Diwali offer poster', 'state': 'done', 'conversation_id': 'w3', 'at': ago(90)},
      {'title': 'Reminder mails to 12 customers', 'state': 'done', 'conversation_id': 'w4', 'at': ago(60 * 26)},
      {'title': 'Book a cab to Nagpur airport', 'state': 'stuck', 'conversation_id': 'w5', 'at': ago(60 * 30), 'from_call': true},
    ],
  };
  app.chatList = [
    {'id': 'w6', 'title': 'Send the price list to Shree Traders', 'updated_at': ago(8),
     'result': {'status': 'needs_you', 'line': 'Approve the email to Shree Traders'}},
  ];
  final t = now.millisecondsSinceEpoch ~/ 1000;
  HoolaTabsDebug.pages = [
    {'id': 'a1', 'title': 'Monthly sales dashboard', 'summary': 'Sales by week', 'updated_at': ago(50), 'status': 'ready'},
    {'id': 'a2', 'title': 'Shop opening checklist', 'updated_at': ago(60 * 30), 'status': 'ready'},
  ];
  HoolaTabsDebug.creations = [
    {'id': 'c1', 'kind': 'song', 'title': 'Diwali jingle', 'mime': 'audio/mpeg', 'created': t - 600},
    {'id': 'c2', 'kind': 'script', 'title': 'Reel script: new sweets', 'mime': 'text/markdown', 'created': t - 7200},
    {'id': 'c3', 'kind': 'voice', 'title': 'Shop welcome voice-over', 'mime': 'audio/mpeg', 'created': t - 90000},
  ];
  HoolaTabsDebug.catalog = {
    'packs': [
      {'id': 'gmail', 'name': 'Gmail', 'status': 'ready', 'does': 'Read, draft and send your mail'},
      {'id': 'gcal', 'name': 'Google Calendar', 'status': 'ready', 'does': 'Your meetings and reminders'},
      {'id': 'upi', 'name': 'UPI payments', 'status': 'core', 'does': 'Payment cards you approve'},
      {'id': 'maps', 'name': 'Maps', 'status': 'core', 'does': 'Places, routes and travel time'},
      {'id': 'notion', 'name': 'Notion', 'status': 'needs_link', 'does': 'Your pages and databases'},
    ],
  };
  // v0.898 the AI Employees tab
  HoolaEmployees.debugList = [
    {'key': 'seo', 'name': 'SEO Specialist', 'group': 'Business', 'status': 'hired', 'live': true,
     'pitch': 'Gets your website found on Google and AI search'},
    {'key': 'social', 'name': 'Social Media Manager', 'group': 'Business', 'status': 'paused', 'live': true,
     'pitch': 'Plans, posts and answers on Instagram and Facebook'},
    {'key': 'accounts', 'name': 'GST & Accounts', 'group': 'Finance & Banking', 'live': true,
     'pitch': 'Your GST returns, credit, bills and the CA pack'},
    {'key': 'tutor', 'name': 'Guru Sahayak', 'group': 'Education, Research & Lab', 'live': true,
     'pitch': 'A patient tutor for every student'},
    {'key': 'const_qs', 'name': 'Quantity Surveyor', 'group': 'Construction', 'live': false,
     'pitch': 'Measures, rate analysis and bills of quantities'},
  ];
  HoolaTabsDebug.apps = [
    {'pack_id': 'swiggy', 'name': 'Swiggy', 'status': 'needs_link', 'does': 'Food orders and tracking'},
    {'pack_id': 'indiamart', 'name': 'IndiaMART', 'status': 'ready', 'no_login': true, 'does': 'Supplier prices city by city'},
  ];
}

Future<void> _shot(WidgetTester t, String name, Widget Function(Santosh app) screen,
    {void Function(Santosh app)? prep, Finder? tab, Map<String, Object> prefs = const {}, Duration settle = const Duration(milliseconds: 900),
    bool a11y = false, double text = 1.0}) async {
  final app = await _app(prefs: prefs);
  prep?.call(app);
  t.view.physicalSize = _logical * _ratio;
  t.view.devicePixelRatio = _ratio;
  addTearDown(t.view.reset);

  await t.pumpWidget(MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: santoshTheme(),
    // R9: text size as the phone's font setting makes it (200 % = the largest Android offers)
    builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(textScaler: TextScaler.linear(text)), child: child!),
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
  if (a11y) {
    // R9 TalkBack + touch: every tap target is big enough (48 dp) and has a name a screen reader can say.
    // Text contrast is proven on the colours themselves (test/design_rules_test.dart: every text pair >= 4.5:1);
    // Flutter's textContrastGuideline samples PIXELS and, with real anti-aliased fonts, read the tab bar's border
    // and a fading-in greeting as the text colour (near-black ink measured as #9F9F9E) - a false alarm, not a gate.
    final h = t.ensureSemantics();
    await expectLater(t, meetsGuideline(androidTapTargetGuideline));
    await expectLater(t, meetsGuideline(labeledTapTargetGuideline));
    h.dispose();
  }

  // leave nothing running: the screen goes, and its timers run out with it
  await t.pumpWidget(const SizedBox.shrink());
  app.dispose();
  await t.pump(const Duration(seconds: 25));   // the shell's own delayed checks (20 s update offer) run out
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

  // v0.868 R8: a desk in the shared frame, drawn with the same old widgets every desk uses, flat in the new design
  testWidgets('45 desk frame (new design)', (t) async {
    NightGlass.flat.value = true;
    addTearDown(() => NightGlass.flat.value = false);
    await _shot(t, '45_desk_frame', (a) => const _SampleDesk(), a11y: true);
  });
  testWidgets('46 desk frame (old look)', (t) => _shot(t, '46_desk_frame_old', (a) => const _SampleDesk()));
  // v0.870 R8 wave 3: a swipe-tab desk (DeskTabsScaffold + pill DeskTabBar), flat in the new design
  testWidgets('47 swipe-tab desk (new design)', (t) async {
    NightGlass.flat.value = true;
    addTearDown(() => NightGlass.flat.value = false);
    await _shot(t, '47_desk_tabs', (a) => const _SampleTabsDesk(), a11y: true);
  });
  // v0.871 R8 wave 4: a one-page desk (DeskPage), flat in the new design
  testWidgets('48 one-page desk (new design)', (t) async {
    NightGlass.flat.value = true;
    addTearDown(() => NightGlass.flat.value = false);
    await _shot(t, '48_desk_page', (a) => DeskPage(
          title: 'Google Drive',
          onRefresh: () async {},
          body: () => ListView(padding: const EdgeInsets.all(16), children: const [
            Caption('RECENT FILES'),
            Glass(child: Text('Quotation_Shree_Traders.pdf · 2 days ago', style: TextStyle(fontSize: 14.5))),
            SizedBox(height: 8),
            Glass(child: Text('GST_October.xlsx · 5 days ago', style: TextStyle(fontSize: 14.5))),
          ]),
        ));
  });

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
    testWidgets('30 new home ($mode)', (t) => _shot(t, '30_new_home_$mode', home, prefs: prefs, a11y: true));
    testWidgets('31 new drawer ($mode)', (t) => _shot(t, '31_new_drawer_$mode', home, prefs: prefs, prep: chats, tab: find.byTooltip('Open chats')));
    testWidgets('32 new employees tab ($mode)', (t) => _shot(t, '32_new_employees_$mode', home, prefs: prefs, prep: _tabsData, a11y: true, tab: find.text('AI Employees')));
    // v0.862 R3 the new chat
    testWidgets('33 new chat ($mode)', (t) => _shot(t, '33_new_chat_$mode', home, prefs: prefs, prep: _richChat, a11y: true));
    testWidgets('34 new chat working ($mode)', (t) => _shot(t, '34_new_chat_working_$mode', home, prefs: prefs,
        prep: (a) => _richChat(a, working: true)));
    testWidgets('36 new cards ($mode)', (t) => _shot(t, '36_new_cards_$mode', home, prefs: prefs, prep: _cardsChat, a11y: true));
    testWidgets('37 new made cards ($mode)', (t) => _shot(t, '37_new_made_$mode', home, prefs: prefs, prep: _madeChat));
    // v0.900 every card in the new design
    testWidgets('57 long task cards ($mode)', (t) => _shot(t, '57_long_task_$mode', home, prefs: prefs, prep: _goalChat, a11y: true));
    testWidgets('58 more cards ($mode)', (t) => _shot(t, '58_more_cards_$mode', home, prefs: prefs, prep: _moreCards, a11y: true));
    testWidgets('38 new talk ($mode)', (t) => _shot(t, '38_new_talk_$mode', home, prefs: prefs,
        prep: (a) => a.realtimeVoice = true, tab: find.bySemanticsLabel('Start a call')));
    testWidgets('39 new talk in call ($mode)', (t) => _shot(t, '39_new_talk_call_$mode', home, prefs: prefs,
        prep: (a) {
          a.realtimeVoice = true;
          _inCall(a);
        }, tab: find.bySemanticsLabel('Start a call')));
    // v0.898 the four tabs: Hoola, AI Employees, Tools, Computer; Work, Made and Connectors as pages of their own
    testWidgets('40 new tools ($mode)', (t) => _shot(t, '40_new_tools_$mode', home, prefs: prefs, prep: _tabsData, tab: find.text('Tools'), a11y: true));
    testWidgets('41 new connectors page ($mode)', (t) => _shot(t, '41_new_connect_$mode',
        (a) => HoolaTheme(appearance: a.appearance, child: HoolaConnectorsPage(app: a)), prefs: prefs, prep: _tabsData, a11y: true));
    testWidgets('42 new made page ($mode)', (t) => _shot(t, '42_new_made_$mode',
        (a) => HoolaTheme(appearance: a.appearance, child: HoolaPageFrame(child: HoolaMade(app: a))), prefs: prefs, prep: _tabsData, a11y: true));
    testWidgets('45 new work page ($mode)', (t) => _shot(t, '45_new_work_$mode',
        (a) => HoolaTheme(appearance: a.appearance, child: HoolaPageFrame(child: HoolaWork(app: a, onOpenChat: (_) {}, onTeam: () {}, onToday: () {}))),
        prefs: prefs, prep: _tabsData, a11y: true));
    // v0.867 R7 Settings and Your AI team
    testWidgets('43 new settings ($mode)', (t) => _shot(t, '43_new_settings_$mode',
        (a) => HoolaTheme(appearance: a.appearance, child: HoolaSettings(app: a, onReset: () {})), prefs: prefs, a11y: true));
    testWidgets('44 new team ($mode)', (t) => _shot(t, '44_new_team_$mode',
        (a) => HoolaTheme(appearance: a.appearance, child: HoolaTeam(app: a)), prefs: prefs, a11y: true));
    // v0.888 her 13 Nov screenshot: the server's "Thinking, one minute..." placeholder must be the working row,
    // never a reply with Copy / Share / Ask again, and the tab bar steps aside while Hoola works
    testWidgets('55 new chat placeholder ($mode)', (t) => _shot(t, '55_new_chat_ack_$mode', home, prefs: prefs, a11y: true,
        prep: (a) {
          _richChat(a, working: true);
          a.currentStep = '';
          a.feed.add(FeedItem('message', {'role': 'assistant', 'text': 'Thinking, one minute…', 'ack': true,
              'at': DateTime(2026, 11, 12, 15, 11).toIso8601String()}));
        }));
    testWidgets('35 new chat writing ($mode)', (t) => _shot(t, '35_new_chat_writing_$mode', home, prefs: prefs,
        prep: (a) => _richChat(a, writing: true)));
  }

  // R9: the new screens with the phone's text at 200 % (an overflow fails the test), dark
  final big = <String, Object>{'new_look': true, 'appearance': 'dark'};
  testWidgets('50 home at 200 % text', (t) => _shot(t, '50_text200_home', home, prefs: big, text: 2));
  testWidgets('51 chat at 200 % text', (t) => _shot(t, '51_text200_chat', home, prefs: big, prep: _richChat, text: 2));
  testWidgets('52 employees at 200 % text', (t) => _shot(t, '52_text200_employees', home, prefs: big, prep: _tabsData, tab: find.text('AI Employees'), text: 2));
  testWidgets('56 tools at 200 % text', (t) => _shot(t, '56_text200_tools', home, prefs: big, prep: _tabsData, tab: find.text('Tools'), text: 2));
  testWidgets('53 settings at 200 % text', (t) => _shot(t, '53_text200_settings',
      (a) => HoolaTheme(appearance: a.appearance, child: HoolaSettings(app: a, onReset: () {})), prefs: big, text: 2));
  testWidgets('54 desk at 200 % text', (t) async {
    NightGlass.flat.value = true;
    addTearDown(() => NightGlass.flat.value = false);
    await _shot(t, '54_text200_desk', (a) => const _SampleTabsDesk(), text: 2);
  });

}

/// v0.868 R8: a desk the way the 30 wave-1 desks are built - DeskScaffold outside, the old Glass parts inside.
class _SampleDesk extends StatelessWidget {
  const _SampleDesk();
  @override
  Widget build(BuildContext context) => DeskScaffold(
        title: 'Notary desk',
        tabs: const ['Aaj', 'Documents', 'Register', 'Apostille', 'Niyam'],
        tab: 0,
        onTab: (_) {},
        loading: false,
        busy: false,
        onRefresh: () async {},
        body: () => ListView(padding: const EdgeInsets.all(16), children: [
          const Glass(child: Text('3 documents wait for your yes before the final print. One affidavit has 2 blanks.',
              style: TextStyle(fontSize: 14.5, height: 1.4))),
          const SizedBox(height: 12),
          GradientButton(label: 'New document', icon: Icons.note_add_rounded, height: 46, onTap: () {}),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GlassButton(label: 'Spoken / written', icon: Icons.record_voice_over_rounded, height: 42, onTap: () {})),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'From Rentdesk', icon: Icons.home_work_rounded, height: 42, onTap: () {})),
          ]),
          const SizedBox(height: 16),
          const Caption('FINAL PRINT: YOUR YES PENDING'),
          for (final (n, who, st) in const [
            ('N-0142 · Affidavit', 'Ramesh Patil · English · Stamp Rs 100', 'Draft'),
            ('N-0141 · Power of attorney', 'Sunita Deshmukh · Marathi · Stamp Rs 500', 'Final'),
            ('N-0139 · Rent agreement', 'Shree Traders · English · Stamp Rs 1,000', 'Notarised'),
          ])
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    const Icon(Icons.gavel_rounded, color: C.accent, size: 20),
                    const SizedBox(width: 8),
                    Expanded(child: Text(n, style: const TextStyle(fontWeight: FontWeight.w700))),
                    Pill(st, fg: st == 'Draft' ? C.warn : C.ok),
                  ]),
                  const SizedBox(height: 2),
                  Text(who, style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ]),
              ),
            ),
        ]),
      );
}

class _SampleTabsDesk extends StatelessWidget {
  const _SampleTabsDesk();
  @override
  Widget build(BuildContext context) => DeskTabsScaffold(
        title: 'Office manager',
        tabs: const ['Aaj', 'Goods', 'Repair', 'Renewal', 'Team', 'Kharcha', 'Niyam'],
        onRefresh: () async {},
        fab: FloatingActionButton.extended(onPressed: () {}, icon: const Icon(Icons.add_rounded), label: const Text('New task')),
        pages: () => [
          for (var i = 0; i < 7; i++)
            ListView(padding: const EdgeInsets.all(16), children: const [
              Glass(child: Text('2 printer cartridges are low. The AMC for the AC ends on 30 Nov - renew or not?',
                  style: TextStyle(fontSize: 14.5, height: 1.4))),
              SizedBox(height: 12),
              Caption('NEEDS YOU'),
              Glass(child: Text('Spend Rs 4,200 on chairs: waiting for your yes.', style: TextStyle(fontSize: 14))),
            ]),
        ],
      );
}
