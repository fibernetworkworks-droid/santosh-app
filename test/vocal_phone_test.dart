// v0.999.89 HOOLA VOCAL, GLOBAL, ON THE PHONE (design canvas claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue, "GO BUILD ALL";
// contract docs/HOOLA_VOCAL_GLOBAL.md): Tools > Hoola Vocal on the phone is the console's Vocal chat. These tests walk it
// with the contract's own shapes: the note her message carries (and her bubble without it), the start screen, a set of
// takes with its quick changes (light + dark), Voice settings with the quoted price and the language sheet (a language
// no engine speaks says so and cannot be picked), the Voices list, the design flow's three voices, and Your sounds with
// a dub that could not be made said plainly.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/vocal/vocal_home.dart';
import 'package:santosh/ui/vocal/vocal_kit.dart';
import 'package:santosh/ui/vocal/vocal_sounds.dart';
import 'package:santosh/ui/vocal/vocal_voices.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app({String mode = 'light'}) async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true, 'appearance': mode});
  return Santosh.load();
}

const _conv = 'vc1';

Map<String, dynamic> vocalOverview() => {
      'voices': [
        {'id': 'v_amani', 'name': 'Amani', 'gender': 'female', 'age': 'middle', 'tone': 'Warm', 'accent': '', 'langs': ['sw', 'en'],
         'use': 'Shops, welcomes', 'engine': 'gemini', 'tier': 'standard', 'kind': 'hoola', 'ready': true, 'color': '#C9E7DF'},
        {'id': 'v_zawadi', 'name': 'Zawadi', 'gender': 'female', 'tone': 'Bright', 'langs': ['sw'], 'engine': 'gemini', 'tier': 'standard',
         'kind': 'hoola', 'ready': true, 'color': '#F6C7D6'},
        {'id': 'v_baraka', 'name': 'Baraka', 'gender': 'male', 'tone': 'Calm, deep', 'langs': ['sw', 'en'], 'engine': 'gemini',
         'tier': 'standard', 'kind': 'hoola', 'ready': true, 'color': '#E8D9C9'},
        {'id': 'v_ana', 'name': 'Ana Beatriz', 'gender': 'female', 'tone': 'Upbeat', 'accent': 'Brasil', 'langs': ['pt'], 'engine': 'gemini',
         'tier': 'standard', 'kind': 'hoola', 'ready': true, 'color': '#C9C1F0'},
        {'id': 'v_layla', 'name': 'Layla', 'gender': 'female', 'tone': 'Storyteller', 'langs': ['ar'], 'engine': 'eleven', 'tier': 'premium',
         'kind': 'hoola', 'ready': true, 'color': '#FBE3B5'},
        {'id': 'v_kofi', 'name': 'Kofi', 'gender': 'male', 'tone': 'Calm, deep', 'accent': 'Ghana', 'langs': ['en'], 'engine': 'gemini',
         'tier': 'standard', 'kind': 'hoola', 'ready': true, 'color': '#E8D9C9'},
        {'id': 'my1', 'name': 'My voice', 'gender': 'female', 'langs': ['*'], 'engine': 'gemini', 'tier': 'standard', 'kind': 'clone',
         'ready': true, 'color': '#D6EBC9'},
      ],
      'langs': [
        {'code': 'sw', 'name': 'Swahili', 'native': 'Kiswahili', 'region': 'Africa', 'speech': 'yes', 'voices': 9},
        {'code': 'en', 'name': 'English', 'native': 'English', 'region': 'Europe', 'speech': 'yes', 'voices': 60},
        {'code': 'es', 'name': 'Spanish', 'native': 'Español', 'region': 'Europe', 'speech': 'yes', 'voices': 38},
        {'code': 'pt', 'name': 'Portuguese', 'native': 'Português', 'region': 'Americas', 'speech': 'yes', 'voices': 24},
        {'code': 'ar', 'name': 'Arabic', 'native': 'العربية', 'region': 'Middle East', 'speech': 'yes', 'voices': 22},
        {'code': 'zu', 'name': 'Zulu', 'native': 'isiZulu', 'region': 'Africa', 'speech': 'premium', 'voices': 3},
        {'code': 'qu', 'name': 'Quechua', 'native': 'Runa Simi', 'region': 'Americas', 'speech': 'none', 'voices': 0},
      ],
      'styles': {'warm': 'Warm', 'calm': 'Calm', 'cheerful': 'Cheerful', 'news': 'News', 'story': 'Story', 'ad': 'Ad'},
      'engines': [
        {'id': 'gemini', 'name': 'Gemini voice', 'does': 'speech, dialogue, clone, design', 'state': 'ready'},
        {'id': 'eleven', 'name': 'ElevenLabs (premium)', 'does': 'premium speech, dubbing', 'state': 'needs_key'},
      ],
      'history': [
        {'id': 'h1', 'kind': 'tts', 'title': 'Karibu Mkate Bora', 'voice_name': 'Amani', 'lang': 'sw', 'engine': 'gemini', 'seconds': 13,
         'made': 1700000300, 'ext': 'mp3'},
        {'id': 'h2', 'kind': 'tts', 'title': 'Olá, bem-vindos!', 'voice_name': 'Ana Beatriz', 'lang': 'pt', 'engine': 'gemini', 'seconds': 9,
         'made': 1700000200, 'ext': 'mp3'},
        {'id': 'h3', 'kind': 'dialogue', 'title': 'Tech Talk ep. 3 intro', 'voice_name': '2 voices', 'lang': 'en', 'engine': 'gemini',
         'seconds': 65, 'made': 1700000100, 'ext': 'mp3'},
        {'id': 'h4', 'kind': 'sfx', 'title': 'Shop door bell', 'voice_name': '', 'lang': '', 'engine': 'server', 'seconds': 2,
         'made': 1700000050, 'ext': 'wav'},
      ],
      'status': {'engines': {}, 'connected': {'clone': true, 'design': true}},
    };

Map<String, dynamic> vocalData({Map<String, dynamic>? turn, bool started = true, bool failedTake = false}) => {
      'overview': vocalOverview(),
      'quote': {'credits': 4, 'usd': .004, 'engine': 'gemini', 'engine_name': 'Gemini voice', 'line': 'Gemini voice · 2 takes ≈ 4 credits'},
      'consent': {'line': 'Concordo que o Hoola crie a minha voz, apenas para o meu uso.',
                  'english': 'I agree that Hoola makes my voice, for my own use only.', 'lang': 'pt', 'locale': 'pt-BR'},
      'design': {'previews': [
        {'pid': 'p1', 'title': 'Warm and slow', 'audio_id': 'a1'},
        {'pid': 'p2', 'title': 'Husky, older', 'audio_id': 'a2'},
        {'pid': 'p3', 'title': 'Soft, bright', 'audio_id': 'a3'},
      ]},
      'dubs': [
        {'id': 'd1', 'status': 'failed', 'title': 'Product tour', 'mode': 'matched', 'made': 1700000400,
         'langs': [{'code': 'qu', 'name': 'Quechua', 'status': 'failed'}], 'error': 'No voice engine speaks Quechua yet'},
      ],
      'chats': [
        {'id': _conv, 'title': 'Karibu Mkate Bora', 'at': '2023-11-14T22:14:50'},
      ],
      'chat': {
        'conv': _conv,
        'title': 'Karibu Mkate Bora',
        'turn': turn,
        'rows': started
            ? [
                {'id': 1, 'role': 'assistant', 'text': 'Tell me what to say, in any language.', 'at': '2023-11-14T22:13:00'},
                {'id': 2, 'role': 'user', 'text': 'Read our shop welcome in Swahili, a warm woman, a little slow\n\n'
                    '[Vocal settings: language Swahili (sw); voice Amani (v_amani); style warm; speed 0.9; takes 2; engine auto]',
                 'at': '2023-11-14T22:14:50'},
                {'id': 3, 'role': 'assistant', 'text': 'Here are two takes in Kiswahili with Amani. B is a touch slower.',
                 'at': '2023-11-14T22:14:55'},
              ]
            : [],
        'items': started
            ? [
                {'id': 't2', 'kind': 'tts', 'title': 'Karibu Mkate Bora', 'voice_name': 'Amani', 'lang': 'sw', 'engine': 'gemini',
                 'seconds': 13, 'made': 1700000101, 'ext': 'mp3', 'take': 'B', 'job': 'j1', 'chat': _conv},
                {'id': 't1', 'kind': 'tts', 'title': 'Karibu Mkate Bora', 'voice_name': 'Amani', 'lang': 'sw', 'engine': 'gemini',
                 'seconds': 12, 'made': 1700000100, 'ext': 'mp3', 'take': 'A', 'job': 'j1', 'chat': _conv},
                if (failedTake)
                  {'id': 't3', 'kind': 'tts', 'title': 'Karibu Mkate Bora', 'lang': 'sw', 'made': 1700000102, 'take': 'C', 'job': 'j1',
                   'status': 'failed', 'error': 'The voice engine was busy'},
              ]
            : [],
      },
    };

/// The settings the design shows: Kiswahili, Amani, Warm, 0.9x, two takes.
VocalSettings vocalDesignSettings() => VocalSettings(lang: 'sw', voice: 'v_amani', style: 'warm', speed: .9, takes: 2);

Widget _host(Widget w, {String mode = 'light'}) => MaterialApp(
      builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(disableAnimations: true), child: child!),
      home: HoolaTheme(appearance: mode, child: w),
    );

SemanticsHandle? _sem;

void _phone(WidgetTester t) {
  t.view.physicalSize = const Size(390 * 3, 2400 * 3);
  t.view.devicePixelRatio = 3;
  addTearDown(t.view.reset);
  _sem = t.ensureSemantics();
}

Future<void> _settle(WidgetTester t) async {
  await t.pump();
  await t.pump(const Duration(milliseconds: 600));
}

Future<Santosh> _open(WidgetTester t, Map<String, dynamic> data, {String mode = 'light'}) async {
  VocalStore.debugData = data;
  final app = await _app(mode: mode);
  await t.pumpWidget(_host(HoolaVocal(app: app, settings: vocalDesignSettings()), mode: mode));
  await _settle(t);
  return app;
}

Future<void> _done(WidgetTester t, Santosh app) async {
  await t.pumpWidget(const SizedBox.shrink());
  app.dispose();
  _sem?.dispose();
  _sem = null;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);
  tearDown(() => VocalStore.debugData = null);

  test('her settings ride her message as the Vocal note; her bubble shows only her words', () async {
    final app = await _app();
    final store = VocalStore(app)..ov = vocalOverview();
    final s = vocalDesignSettings();
    final n = s.note(store, focus: 't2');
    expect(n, 'Vocal settings: language Swahili (sw); voice Amani (v_amani); style warm; speed 0.9; takes 2; engine auto; '
        'the take she means: id t2');
    expect(n.contains('[') || n.contains(']') || n.contains('\n'), isFalse, reason: 'the note rides inside [ ... ]');
    expect(vocalStripNotes('Karibu\n\n[$n]'), 'Karibu');
    expect(VocalSettings().note(store), startsWith('Vocal settings: language auto; voice auto; style warm; speed 1.0; takes 2'));
    expect(s.summary(store), 'Kiswahili · Amani · Warm · 0.9x');
    expect(vocalSpeed(.85), '0.85');
    final b = s.body('Karibu', chat: 'vc1');
    expect(b['lang'], 'sw');
    expect(b['takes'], 2);
    expect(b['chat'], 'vc1');
    expect(vocalQuoteLine(const {'credits': 6, 'engine_name': 'Gemini voice'}, 3), 'Gemini voice · 3 takes ≈ 6 credits');
    final sets = vocalSets((vocalData()['chat'] as Map)['items'] as List<Map<String, dynamic>>);
    expect(sets.length, 1);
    expect(sets.first.takes.map((x) => x['take']), ['A', 'B'], reason: 'takes in order, one set per job');
    store.dispose();
    app.dispose();
  });

  testWidgets('a new Vocal chat starts with one line and four ideas; an idea fills the box, never sends', (t) async {
    _phone(t);
    final app = await _open(t, vocalData(started: false));
    expect(find.text('What should Hoola say?'), findsOneWidget);
    expect(find.text('Try one'), findsOneWidget);
    expect(find.text('Our shop welcome in Swahili'), findsOneWidget);
    expect(find.bySemanticsLabel('Voice settings: Kiswahili · Amani · Warm · 0.9x'), findsOneWidget);
    expect(find.text('Gemini voice · 2 takes ≈ 4 credits'), findsOneWidget);
    await t.tap(find.text('Our shop welcome in Swahili'));
    await t.pump();
    expect(find.textContaining('Karibu Mkate Bora, mkate safi'), findsWidgets);
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  for (final mode in ['light', 'dark']) {
    testWidgets('$mode the chat: her words without the note, the reply, takes A and B, quick changes', (t) async {
      _phone(t);
      final app = await _open(t, vocalData(), mode: mode);
      expect(find.text('Read our shop welcome in Swahili, a warm woman, a little slow'), findsOneWidget);
      expect(find.textContaining('Vocal settings:'), findsNothing, reason: 'her bubble shows only her words');
      expect(find.text('Here are two takes in Kiswahili with Amani. B is a touch slower.'), findsOneWidget);
      expect(find.text('Take A'), findsOneWidget);
      expect(find.text('Take B'), findsOneWidget);
      expect(find.text('Kiswahili · Amani · 0:12'), findsOneWidget);
      expect(find.bySemanticsLabel('Play Take A'), findsOneWidget);
      expect(find.bySemanticsLabel('More for Take B'), findsOneWidget);
      for (final q in ['Slower', 'Warmer', 'Another voice']) {
        expect(find.bySemanticsLabel(q), findsOneWidget);
      }
      expect(find.text('Made by AI · marked in the file'), findsOneWidget);
      expect(t.takeException(), isNull);
      await _done(t, app);
    });
  }

  testWidgets('a take that could not be made says why, that nothing was charged, and offers Try again', (t) async {
    _phone(t);
    final app = await _open(t, vocalData(failedTake: true));
    expect(find.text('Could not be made'), findsOneWidget);
    expect(find.text('The voice engine was busy. Nothing was charged.'), findsOneWidget);
    expect(find.bySemanticsLabel('Try again'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  testWidgets('Hoola cannot answer: the takes can be made straight away, the price on the button', (t) async {
    _phone(t);
    final d = vocalData(turn: {'status': 'failed', 'line': ''});
    ((d['chat'] as Map)['rows'] as List).add({'id': 4, 'role': 'user',
        'text': 'Read: Asante kwa kununua\n\n[Vocal settings: language auto]', 'at': '2023-11-14T23:00:00'});
    final app = await _open(t, d);
    expect(find.text('Hoola can’t answer right now'), findsOneWidget);
    expect(find.bySemanticsLabel('Make it now · 4 credits'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  testWidgets('Voice settings: voices for the language, styles, speed, takes, the price; the language sheet', (t) async {
    _phone(t);
    final app = await _open(t, vocalData());
    await t.tap(find.bySemanticsLabel(RegExp('^Voice settings: ')));
    await _settle(t);
    expect(find.text('Voice settings'), findsOneWidget);
    expect(find.bySemanticsLabel('Amani'), findsOneWidget);
    expect(find.bySemanticsLabel('Zawadi'), findsOneWidget);
    expect(find.bySemanticsLabel('Ana Beatriz'), findsNothing, reason: 'only voices that speak Kiswahili (and hers)');
    expect(find.bySemanticsLabel('My voice'), findsOneWidget);
    expect(find.bySemanticsLabel('All voices'), findsOneWidget);
    expect(find.text('Cheerful'), findsOneWidget);
    expect(find.text('0.9x'), findsOneWidget);
    expect(find.text('Gemini voice · 2 takes ≈ 4 credits'), findsWidgets);
    await t.tap(find.text('3').last);
    await t.pump();
    await t.tap(find.bySemanticsLabel(RegExp('^Language: ')));
    await _settle(t);
    expect(find.text('Search 7 languages'), findsOneWidget);
    expect(find.text('Runa Simi'), findsOneWidget);
    expect(find.text('No engine yet'), findsOneWidget);
    expect(find.text('Premium'), findsOneWidget);
    expect(find.text('9 voices'), findsOneWidget);
    await t.tap(find.text('Runa Simi'));
    await _settle(t);
    expect(find.text('Search 7 languages'), findsOneWidget, reason: 'a language no engine speaks cannot be picked');
    await t.enterText(find.byType(TextField).last, 'portu');
    await t.pump();
    expect(find.text('Português'), findsOneWidget);
    expect(find.text('Kiswahili'), findsNothing);
    await t.tap(find.text('Português'));
    await _settle(t);
    expect(find.text('Português · Portuguese'), findsOneWidget);
    expect(find.bySemanticsLabel('Ana Beatriz'), findsOneWidget, reason: 'the voices follow the language');
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  testWidgets('the Voices list: search, women / men, Hear and Use; Your voice opens', (t) async {
    _phone(t);
    VocalStore.debugData = vocalData();
    final app = await _app();
    final store = VocalStore(app);
    await store.load();
    await t.pumpWidget(_host(VocalVoicesPage(store: store, player: VocalPlayer(app), lang: 'sw', picked: 'v_amani')));
    await _settle(t);
    expect(find.text('Voices'), findsOneWidget);
    expect(find.text('Layla'), findsOneWidget);
    expect(find.textContaining('Premium'), findsWidgets);
    expect(find.bySemanticsLabel('Hear Kofi'), findsOneWidget);
    expect(find.bySemanticsLabel('Amani is in use'), findsOneWidget);
    expect(find.text('Your clone · every language'), findsOneWidget);
    await t.tap(find.text('Men'));
    await t.pump();
    expect(find.text('Kofi'), findsOneWidget);
    expect(find.text('Layla'), findsNothing);
    await t.tap(find.text('All'));
    await t.pump();
    await t.enterText(find.byType(TextField), 'arabic');
    await t.pump();
    expect(find.text('Layla'), findsOneWidget);
    expect(find.text('Kofi'), findsNothing);
    await t.tap(find.bySemanticsLabel('Your voice: make or copy one'));
    await _settle(t);
    expect(find.text('Describe a voice'), findsOneWidget);
    expect(t.takeException(), isNull);
    await t.pumpWidget(const SizedBox.shrink());
    store.dispose();
    await _done(t, app);
  });

  testWidgets('Your voice: design three to hear, pick, name, save; the clone asks for her spoken yes', (t) async {
    _phone(t);
    VocalStore.debugData = vocalData();
    final app = await _app();
    final store = VocalStore(app);
    await store.load();
    await t.pumpWidget(_host(VocalYourVoicePage(store: store, player: VocalPlayer(app))));
    await _settle(t);
    await t.enterText(find.byType(TextField).first, 'A calm grandmother from Nairobi, warm and slow');
    await t.pump();
    await t.tap(find.bySemanticsLabel('Make 3 voices to hear'));
    await _settle(t);
    expect(find.text('Warm and slow'), findsOneWidget);
    expect(find.text('Husky, older'), findsOneWidget);
    expect(find.text('Soft, bright'), findsOneWidget);
    expect(find.bySemanticsLabel('Play Husky, older'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Pick Husky, older'));
    await t.pump();
    expect(find.bySemanticsLabel('Husky, older is picked'), findsOneWidget);
    expect(find.text('Its name'), findsOneWidget);
    expect(find.text('My voice'), findsOneWidget, reason: 'Your voices lists her clone');
    // the clone: step 1 a recording, step 2 the consent line in her language, step 3 the name and her yes
    await t.tap(find.text('Clone'));
    await t.pump();
    expect(find.text('Your voice, in 10 to 30 seconds'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Choose the recording'));
    await t.pump();
    await t.tap(find.bySemanticsLabel('Next'));
    await _settle(t);
    expect(find.text('Now say yes, in your own voice'), findsOneWidget);
    expect(find.text('“Concordo que o Hoola crie a minha voz, apenas para o meu uso.”'), findsOneWidget);
    expect(find.text('“I agree that Hoola makes my voice, for my own use only.”'), findsOneWidget);
    expect(t.takeException(), isNull);
    await t.pumpWidget(const SizedBox.shrink());
    store.dispose();
    await _done(t, app);
  });

  testWidgets('Your sounds: filters by kind, and a dub that could not be made is said plainly', (t) async {
    _phone(t);
    VocalStore.debugData = vocalData();
    final app = await _app();
    final store = VocalStore(app);
    await store.load();
    String asked = '';
    await t.pumpWidget(_host(VocalSoundsPage(store: store, player: VocalPlayer(app), onAsk: (w) => asked = w)));
    await _settle(t);
    expect(find.text('Karibu Mkate Bora'), findsOneWidget);
    expect(find.text('Speech · Amani · Kiswahili · 0:13'), findsOneWidget);
    expect(find.text('Tech Talk ep. 3 intro'), findsOneWidget);
    expect(find.text('Dub into Quechua could not be made'), findsOneWidget);
    expect(find.text('No voice engine speaks Quechua yet. Nothing was charged.'), findsOneWidget);
    expect(find.bySemanticsLabel('More for Karibu Mkate Bora'), findsOneWidget);
    await t.tap(find.text('Dialogue'));
    await t.pump();
    expect(find.text('Tech Talk ep. 3 intro'), findsOneWidget);
    expect(find.text('Karibu Mkate Bora'), findsNothing);
    await t.tap(find.text('Dubs'));
    await t.pump();
    expect(find.text('Dub into Quechua could not be made'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Choose another language'));
    await t.pump();
    expect(asked, 'Dub Product tour into ');
    expect(t.takeException(), isNull);
    await t.pumpWidget(const SizedBox.shrink());
    store.dispose();
    await _done(t, app);
  });

  test('the Tools tab opens the native Vocal screen, not the console page', () {
    expect(_toolsSource(), contains("t.title == 'Hoola Vocal'"));
    expect(_toolsSource(), contains('HoolaVocal(app: app)'));
  });
}

String _toolsSource() => File('lib/ui/shell/hoola_tools.dart').readAsStringSync();
