// v0.912 CREATE NATIVE (design canvas claude.ai/artifact/SARfWkfWm8ZtmmnAcU8dYn, "GO BUILD"): the Tools tab's Create
// is the app's own studio - a home with five modes and ten tools, and a native screen for every console Create page,
// on the console's own routes. These tests walk every screen (light and dark), the store's calls, and the rules:
// a price on every paid button, Haan before money, delete asks first.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/api.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/create/create_film.dart';
import 'package:santosh/ui/create/create_home.dart';
import 'package:santosh/ui/create/create_keep.dart';
import 'package:santosh/ui/create/create_kit.dart';
import 'package:santosh/ui/create/create_make.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

/// The same shapes the server answers with (create/jobs.py, studio/service.py view, brand kit).
final Map<String, dynamic> createData = {
  'conf': {
    'ready': {'song': true, 'voice': true, 'dub': true},
    'voices': {'female': {'Kore': 'firm, clear', 'Aoede': 'breezy'}, 'male': {'Puck': 'upbeat', 'Charon': 'deep'}},
    'styles': ['friendly', 'calm', 'excited', 'news', 'story', 'ad'],
    'languages': ['Hindi', 'Hinglish', 'English'],
  },
  'items': [
    {'id': 'cr1', 'kind': 'image', 'title': 'Diwali offer poster', 'mime': 'image/png', 'size': 1, 'created': 1700000000,
     'meta': {'aspect': '1:1', 'quality': 'best'}},
    {'id': 'cr2', 'kind': 'song', 'title': 'Roshni ka tyohaar', 'mime': 'audio/wav', 'size': 1, 'created': 1700000000,
     'meta': {'genre': 'Jingle', 'language': 'Hindi', 'vocals': 'duet', 'mood': 'Joyful'}},
    {'id': 'cr3', 'kind': 'voice', 'title': 'Diwali offer', 'mime': 'audio/wav', 'size': 1, 'created': 1700000000,
     'meta': {'voice': 'mine', 'language': 'Hindi', 'style': 'friendly'}},
    {'id': 'cr4', 'kind': 'cast', 'title': 'Cast · Sharma ji', 'mime': 'image/png', 'size': 1, 'created': 1700000000,
     'meta': {'name': 'Sharma ji'}},
    {'id': 'cr5', 'kind': 'script', 'title': 'Script · Diwali ad', 'mime': 'text/plain', 'size': 1, 'created': 1700000000},
    {'id': 'cr6', 'kind': 'dub', 'title': 'shop-tour · Tamil dub', 'mime': 'video/mp4', 'size': 1, 'created': 1700000000,
     'meta': {'language': 'Tamil'}},
  ],
  'jobs': [
    {'id': 'cj1', 'kind': 'image', 'status': 'running', 'title': 'Kaju katli box', 'step': '1 / 2'},
    {'id': 'cj2', 'kind': 'song', 'status': 'failed', 'title': 'A sad ghazal', 'error': 'The music engine is busy. Try again in a minute.'},
  ],
  'studio': {
    'models': [
      {'model': 'veo-3', 'label': 'Veo 3', 'ready': true, 'inr_per_second': 32},
      {'model': 'kling', 'label': 'Kling 2.1', 'ready': false},
    ],
    'projects': [
      {
        'project': 'Diwali at Sharma Sweets', 'aspect': '9:16', 'language': 'Hindi', 'seconds': 15, 'spent_inr': 63,
        'brief': 'A family walks into the shop at dusk, the owner hands a box of kaju katli, diyas glow.',
        'keyframes': 2, 'music': false, 'planning': false, 'working': false,
        'prefs': {'cast_skip': false}, 'quality_pref': 'final',
        'character_list': [{'name': 'Sharma ji', 'image': ''}, {'name': 'Priya', 'image': ''}],
        'casting': [],
        'shots': [
          {'id': 's1', 'prompt': 'Shop front at dusk, lights strung over the board', 'duration': 5, 'camera': 'slow push in',
           'phase': 'pictured', 'keyframe': '', 'picked': null},
          {'id': 's2', 'prompt': 'Sharma ji smiles behind the counter', 'duration': 5, 'dialogue': 'Aaiye, aaiye!',
           'phase': 'pictured', 'keyframe': '', 'picked': null},
          {'id': 's3', 'prompt': 'Hands pass a gold box over the counter', 'duration': 5, 'phase': 'new', 'keyframe': '', 'picked': null},
        ],
        'outputs': [],
        'approvals': [],
        'next': {'kind': 'keyframes', 'label': 'Pehli tasveerein', 'inr': 12},
      },
      {
        'project': 'Clip 14 Nov 10:20', 'aspect': '9:16', 'language': 'Hindi', 'seconds': 8, 'spent_inr': 0,
        'brief': 'Chai on a rainy balcony\nCamera: slow dolly in towards the subject.', 'planning': false, 'working': false,
        'shots': [], 'outputs': [],
        'approvals': [{'id': 'sa1', 'kind': 'video', 'inr': 144, 'shots': 1, 'seconds': 8, 'status': 'pending'}],
      },
    ],
  },
  'kit': {
    'name': 'Sharma Sweets', 'tagline': 'Akola ki asli mithaas, 1978 se', 'tone': 'Warm and family',
    'colors': {'primary': '#7A1F2B', 'accent': '#E8A33D', 'secondary': '#3A1208', 'light': '#FFF6E9', 'dark': '#3A1208'},
    'fonts': {'poppins': 'Poppins (modern)', 'mukta': 'Mukta (Hindi / Marathi)'}, 'font': 'poppins',
    'contact': {'phone': '98xxx xxxxx', 'website': 'sharmasweets.in'}, 'logo': false,
  },
  'cinema': {'key_set': false, 'jobs': []},
};

Widget _host(Widget w, {String mode = 'light'}) => MaterialApp(
      builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(disableAnimations: true), child: child!),
      home: HoolaTheme(appearance: mode, child: w),
    );

void _phone(WidgetTester t) {
  t.view.physicalSize = const Size(390 * 3, 2600 * 3);
  t.view.devicePixelRatio = 3;
  addTearDown(t.view.reset);
}

Future<void> _settle(WidgetTester t) async {
  await t.pump();
  await t.pump(const Duration(milliseconds: 600));
}

Future<void> _done(WidgetTester t, Santosh app, [CreateStore? store]) async {
  await t.pumpWidget(const SizedBox.shrink());
  store?.dispose();
  app.dispose();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);
  setUp(() => CreateStore.debugData = createData);
  tearDown(() => CreateStore.debugData = null);

  test('the store reads the console\'s routes, starts a job with the open chat, and follows it to done', () async {
    CreateStore.debugData = null;
    HttpOverrides.global = null;
    final seen = <String>[];
    var polls = 0;
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((req) async {
      final body = await utf8.decoder.bind(req).join();
      seen.add('${req.method} ${req.uri.path}${body.isEmpty ? '' : ' $body'}');
      req.response.headers.contentType = ContentType.json;
      final p = req.uri.path;
      Object out = {'ok': true};
      if (p == '/api/create') out = createData['conf'] as Object;
      if (p == '/api/create/items') out = {'items': polls > 0 ? createData['items'] : []};
      if (p == '/api/create/jobs' && req.method == 'GET') out = {'jobs': []};
      if (p == '/api/create/jobs' && req.method == 'POST') out = {'id': 'cj9', 'kind': 'image', 'status': 'running', 'title': 'Tea'};
      if (p == '/api/create/jobs/cj9') {
        polls++;
        out = {'id': 'cj9', 'kind': 'image', 'status': 'done', 'title': 'Tea', 'items': []};
      }
      if (p == '/api/studio') out = createData['studio'] as Object;
      if (p == '/api/brand/kit') out = createData['kit'] as Object;
      req.response.write(jsonEncode(out));
      await req.response.close();
    });
    final app = await _app();
    app.api = Api('http://127.0.0.1:${server.port}', 'k');
    app.conversationId = 'c1';
    final store = CreateStore(app);
    await store.load();
    expect(store.films.length, 2);
    expect(crS(store.kit['name']), 'Sharma Sweets');
    expect(store.items, isEmpty);
    await store.start({'kind': 'image', 'prompt': 'Tea'});
    expect(store.running('image').length, 1);
    await Future<void>.delayed(const Duration(milliseconds: 3200));
    expect(store.running('image'), isEmpty, reason: 'the poll saw it finish');
    expect(store.items.length, 6, reason: 'a finished job reloads the shelf');
    expect(seen, containsAll(['GET /api/create', 'GET /api/create/items', 'GET /api/create/jobs', 'GET /api/studio', 'GET /api/brand/kit']));
    expect(seen.firstWhere((s) => s.startsWith('POST /api/create/jobs')), contains('"conversation_id":"c1"'),
        reason: 'the result also lands in her open chat');
    store.dispose();
    app.dispose();
    await server.close(force: true);
  });

  test('small helpers read like the console', () {
    expect(crRupees(3), '₹3');
    expect(crRupees(7.5), '₹7.5');
    expect(crRupees(144.4), '₹144');
    expect(crKindName('voice'), 'Voice-over');
    expect(crHex('#7A1F2B'), const Color.fromARGB(255, 0x7A, 0x1F, 0x2B));
    expect(crHex('blue'), isNull);
    expect(filmPhase({'planning': true}), 'Writing the storyboard…');
    expect(filmPhase({'approvals': [{'id': 'a'}]}), 'Waiting for your Haan');
    expect(filmPhase({'outputs': [{'preview': false}]}), 'Ready to watch');
  });

  for (final mode in ['light', 'dark']) {
    testWidgets('$mode Create home: the question, five modes, ten tools on black, recent, starters', (t) async {
      _phone(t);
      final app = await _app();
      await t.pumpWidget(_host(HoolaCreate(app: app), mode: mode));
      await _settle(t);
      expect(find.text('What shall we create today?'), findsOneWidget);
      for (final m in ['Film', 'Picture', 'Video clip', 'Song', 'Voice-over']) {
        expect(find.text(m), findsWidgets, reason: 'mode $m');
      }
      for (final tool in ['Director', 'Image', 'Video', 'Music', 'Dubbing', 'Video editor', 'Script writer', 'AI casting', 'Hoola Cinema']) {
        expect(find.text(tool), findsWidgets, reason: 'tool $tool');
      }
      expect(find.text('Storyboard free'), findsOneWidget, reason: 'Film is the first mode');
      await t.tap(find.text('Song').first);
      await t.pump();
      expect(find.text('About ₹7'), findsOneWidget, reason: 'the mode changes the price line');
      expect(find.text('Recent'), findsOneWidget);
      expect(find.text('Diwali offer poster'), findsWidgets);
      final c = mode == 'light' ? HoolaColors.light : HoolaColors.darkSet;
      final discs = t.widgetList<CrDisc>(find.byType(CrDisc)).length;
      expect(discs, greaterThanOrEqualTo(10), reason: 'every tool on its own black circle');
      for (final box in t.widgetList<Container>(find.descendant(of: find.byType(CrDisc), matching: find.byType(Container)))) {
        expect((box.decoration as BoxDecoration).color, c.pill);
      }
      expect(t.takeException(), isNull);
      await _done(t, app);
    });
  }

  testWidgets('the ask box opens the right tool with her words in it', (t) async {
    _phone(t);
    final sem = t.ensureSemantics();
    addTearDown(sem.dispose);
    final app = await _app();
    await t.pumpWidget(_host(HoolaCreate(app: app)));
    await _settle(t);
    await t.tap(find.text('Picture').first);
    await t.pump();
    await t.enterText(find.byType(TextField).first, 'A poster of chai');
    await t.tap(find.bySemanticsLabel('Start picture'));
    await _settle(t);
    expect(find.text('Describe the picture'), findsOneWidget);
    expect(find.text('A poster of chai'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  for (final mode in ['light', 'dark']) {
    testWidgets('$mode every Create screen opens with its own controls and no errors', (t) async {
      _phone(t);
      final app = await _app();
      final store = CreateStore(app);
      await store.load();
      final screens = <(String, Widget, List<String>)>[
        ('Image', CreateImage(store: store), ['New picture', 'Change my photo', 'Festive glow', 'Standard', 'Best', 'Create · about ₹3', 'Painting 1 / 2']),
        ('Video', CreateVideo(store: store), ['Hoola Auto · best quality', 'Dolly in', '8 s', 'Free preview', 'Create · see the price', 'Waiting for your Haan', 'Haan · ₹144']),
        ('Director', CreateDirector(store: store), ['Your films', 'Diwali at Sharma Sweets', '9:16 · Hindi']),
        ('Film', CreateFilm(store: store, project: 'Diwali at Sharma Sweets'), ['Step 4 of 8 · Pictures', 'Paint the opening pictures', 'See the price · about ₹12', 'Skip pictures', 'Sharma ji', 'Storyboard']),
        ('Music', CreateMusic(store: store), ['Song', 'Instrumental', 'Jingle', 'Score', 'Bollywood romantic', 'Lyrics', 'Write with Hoola', 'Make the song · about ₹7', 'A sad ghazal', 'Roshni ka tyohaar']),
        ('Voice', CreateVoice(store: store), ['What should be said', 'Marathi', 'Your Santosh’s voice', 'Kore', 'Puck', 'Friendly', '1.0×', 'Make the voice-over · a few paise']),
        ('Dub', CreateDub(store: store), ['Your video, in more languages', 'Add your video', 'Tamil', 'All languages', 'Keep background sound', 'Dub into 1 language']),
        ('Editor', CreateEditor(store: store), ['Your clips', 'What should Hoola do?', 'Cut the silences', 'Instagram Reel', 'Captions', 'Make the edit']),
        ('Script', CreateScript(store: store), ['What is it about?', 'Ad film', 'Web episode', 'Hinglish', 'Write the script', 'Your scripts']),
        ('Casting', CreateCasting(store: store), ['Make a character once, use them everywhere', 'Photoreal cinematic', 'Female voice', 'Cast this character · about ₹12', 'Your cast']),
        ('Library', CreateLibrary(store: store), ['My creations', 'Pictures', 'Songs', '6 items', 'Newest first']),
        ('Brand', CreateBrand(store: store), ['Sharma Sweets', 'Akola ki asli mithaas, 1978 se', 'Main', 'Accent', 'Poppins (modern)', 'Save brand kit']),
        ('Cinema', CreateCinema(store: store), ['Change a video like a film studio', 'Motion transfer', 'Talking photo', 'Content factory']),
        ('Guides', CreateGuides(store: store, open: (_) {}), ['Make your first ad film', 'Open Director']),
      ];
      for (final s in screens) {
        await t.pumpWidget(_host(s.$2, mode: mode));
        await _settle(t);
        for (final w in s.$3) {
          expect(find.text(w), findsWidgets, reason: '${s.$1}: $w');
        }
        expect(t.takeException(), isNull, reason: s.$1);
      }
      await _done(t, app, store);
    });
  }

  testWidgets('Image: the count changes the price on the button; Video: Haan sits on the price card', (t) async {
    _phone(t);
    final sem = t.ensureSemantics();
    addTearDown(sem.dispose);
    final app = await _app();
    final store = CreateStore(app);
    await store.load();
    await t.pumpWidget(_host(CreateImage(store: store)));
    await _settle(t);
    await t.tap(find.bySemanticsLabel('More pictures'));
    await t.pump();
    expect(find.text('Create · about ₹6'), findsOneWidget);
    await t.tap(find.text('Best'));
    await t.pump();
    expect(find.text('Create · about ₹24'), findsOneWidget, reason: 'Best is ₹12 a picture');
    await t.pumpWidget(_host(CreateVideo(store: store)));
    await _settle(t);
    expect(find.text('Nothing is spent until you tap Haan on the price card.'), findsOneWidget);
    expect(find.text('You are never charged more than this price.'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('My creations: Select ticks, and Delete asks first', (t) async {
    _phone(t);
    final sem = t.ensureSemantics();
    addTearDown(sem.dispose);
    final app = await _app();
    final store = CreateStore(app);
    await store.load();
    await t.pumpWidget(_host(CreateLibrary(store: store)));
    await _settle(t);
    await t.tap(find.text('Select'));
    await t.pump();
    expect(find.text('Tick what to save'), findsOneWidget);
    await t.tap(find.bySemanticsLabel(RegExp('Picture: Diwali offer poster')));
    await t.pump();
    expect(find.text('Save 1 to phone'), findsOneWidget);
    await t.tap(find.text('Delete'));
    await t.pump();
    expect(find.text('Delete this creation?'), findsOneWidget, reason: 'never deleted without asking');
    await t.tap(find.text('Keep'));
    await t.pump();
    expect(store.items.length, 6);
    await t.tap(find.text('Songs'));
    await t.pump();
    expect(find.textContaining('1 chosen'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  test('the Tools tab opens the native Create, and the console can open Cinema straight away', () {
    final tools = File('lib/ui/shell/hoola_tools.dart').readAsStringSync();
    expect(tools, contains("t.title == 'Create'"));
    expect(tools, contains('HoolaCreate(app: app)'));
    final v2 = File('server/app/static/console/v2.js').readAsStringSync();
    expect(v2, contains("if (v === 'creative' && CREATE) { CREATE.open(arg); return; }"));
    // the design rules: every colour from the theme, no tiny or heavy type, no blur
    for (final f in Directory('lib/ui/create').listSync().whereType<File>()) {
      final s = f.readAsStringSync();
      expect(RegExp(r'Color\(0x').hasMatch(s), isFalse, reason: '${f.path}: a raw colour');
      expect(RegExp(r'FontWeight\.w(?:800|900)').hasMatch(s), isFalse, reason: f.path);
      expect(s.contains('BackdropFilter'), isFalse, reason: f.path);
      for (final m in RegExp(r'fontSize:\s*(\d+(?:\.\d+)?)').allMatches(s)) {
        expect(double.parse(m.group(1)!), greaterThanOrEqualTo(12), reason: '${f.path}: ${m.group(0)}');
      }
    }
    unawaited(Future<void>.value());
  });
}
