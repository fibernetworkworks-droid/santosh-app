// v0.999.90 HOOLA VOCAL, GLOBAL, ON THE PHONE + v0.999.96 THE REDESIGN (docs/HOOLA_VOCAL_REDESIGN.md section 5, boards
// PhoneChat / PhoneSpeech / PhoneVoices / PhoneDubbing): Tools > Hoola Vocal on the phone is the whole of Vocal - the top
// bar "Vocal · <page>", the drawer with the console's groups, the chat with the docked bar (+ / ONE settings pill /
// Improve / send) and take cards with waveforms, and every page: Speech, Dialogue, Studio, Dubbing (the line editor),
// Voice library (Hoola / Shared / Yours), Your voice (record in the app, the consent statement), Voice changer, Clean-up,
// Sound effects, Your sounds, Dictionary, Settings. These tests walk them with the contract's own shapes.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/vocal/vocal_home.dart';
import 'package:santosh/ui/vocal/vocal_kit.dart';
import 'package:santosh/ui/vocal/vocal_make.dart';
import 'package:santosh/ui/vocal/vocal_sounds.dart';
import 'package:santosh/ui/vocal/vocal_speech.dart';
import 'package:santosh/ui/vocal/vocal_tools.dart';
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
      'formats': [
        {'id': 'mp3', 'name': 'MP3', 'note': 'small, for sharing'},
        {'id': 'wav', 'name': 'WAV', 'note': 'studio quality'},
        {'id': 'ogg', 'name': 'OGG', 'note': 'for WhatsApp'},
        {'id': 'm4a', 'name': 'M4A', 'note': 'for iPhone'},
      ],
      'rules': [
        {'id': 'pr1', 'word': 'Mithas', 'say': 'Mi-thaas', 'ipa': 'mɪˈt̪ʰaːs', 'lang': ''},
      ],
      'projects': [
        {'id': 'vp1', 'title': 'The Lighthouse Keeper', 'author': 'Asha Rao', 'voice': 'v_kofi', 'lang': 'en', 'cast': {'Narrator': 'v_kofi', 'Elias': 'v_kofi'}, 'chapters': [
          {'title': 'The keeper', 'text': 'The wind came off the sea.', 'audio': 'h9', 'seconds': 640},
          {'title': 'The storm', 'text': 'Below, the boy had woken.'},
          {'title': 'The lamp', 'text': 'He lit the lamp.\n\n“Keep it burning,” said Elias.', 'audio': 'h9', 'seconds': 120,
            'paragraphs': [{'who': 'Narrator', 'text': 'He lit the lamp.'}, {'who': 'Elias', 'text': '“Keep it burning,” said Elias.'}],
            'segments': [{'who': 'Narrator', 'text': 'He lit the lamp.'}, {'who': 'Elias', 'text': '“Keep it alive,” said Elias.'}]},
        ]},
      ],
      'prices': [
        {'job': 'Speech, 1 minute', 'engine': 'gemini', 'credits': 2},
        {'job': 'Noise clean-up', 'engine': 'server', 'credits': 0},
      ],
      'usage': {'credits_used': 40, 'credits_left': 960},
      'limits': {'dub_langs_matched': 4, 'dub_langs_own': 6, 'takes': 4},
      'sfx': ['door_bell', 'coin'],
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
        {'id': 'd2', 'status': 'ready', 'name': 'Product video', 'mode': 'matched', 'made': 1700000500,
         'langs': [{'code': 'es', 'name': 'Spanish', 'status': 'ready', 'video_id': 'hv1'}]},
      ],
      'dub_lines': {'lang': 'es', 'editable': true, 'credits_redo': 1, 'lines': [
        {'n': 0, 'start': 0, 'end': 4, 'speaker': 'Priya', 'src': 'Every box is made by hand, every morning.',
         'dst': 'Cada caja se hace a mano, cada mañana.', 'too_long': false},
        {'n': 2, 'start': 9, 'end': 11, 'speaker': 'Rahul', 'src': 'And no colours. Ever.',
         'dst': 'Y nada de colorantes. Nunca jamás, en ningún caso.', 'too_long': true, 'edited': true},
      ]},
      'speech': [
        {'id': 's1', 'kind': 'tts', 'title': 'Diwali offer', 'voice_name': 'Amani', 'lang': 'sw', 'seconds': 14, 'take': 'A', 'ext': 'mp3'},
        {'id': 's2', 'kind': 'tts', 'title': 'Diwali offer', 'voice_name': 'Amani', 'lang': 'sw', 'seconds': 15, 'take': 'B', 'ext': 'mp3'},
      ],
      'library': {'ready': true, 'more': false, 'voices': [
        {'id': 'sv1', 'owner': 'u1', 'name': 'Kavya', 'line': 'Bright · Hindi, Marathi · ads', 'langs': ['hi', 'mr'], 'gender': 'female',
         'age': 'young', 'accent': 'Pune', 'use': 'Ads, explainers', 'uses': 12400, 'preview': '/api/vocal/library/preview?url=x'},
        {'id': 'sv2', 'owner': 'u2', 'name': 'Ravi', 'line': 'Deep · Tamil · news', 'langs': ['ta'], 'gender': 'male', 'uses': 300},
      ]},
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

Future<Santosh> _open(WidgetTester t, Map<String, dynamic> data, {String mode = 'light', VocalPage page = VocalPage.chat}) async {
  VocalStore.debugData = data;
  final app = await _app(mode: mode);
  await t.pumpWidget(_host(HoolaVocal(app: app, settings: vocalDesignSettings(), page: page), mode: mode));
  await _settle(t);
  return app;
}

/// One page on its own (with its own Back bar), on a loaded store.
Future<(Santosh, VocalStore)> _page(WidgetTester t, Widget Function(VocalStore s, VocalPlayer p) build, {String mode = 'light'}) async {
  VocalStore.debugData = vocalData();
  final app = await _app(mode: mode);
  final store = VocalStore(app);
  await store.load();
  await t.pumpWidget(_host(build(store, VocalPlayer(app)), mode: mode));
  await _settle(t);
  return (app, store);
}

/// One page on its own with the test's own data.
Future<(Santosh, VocalStore)> _pageWith(WidgetTester t, Map<String, dynamic> data, Widget Function(VocalStore s, VocalPlayer p) build) async {
  VocalStore.debugData = data;
  final app = await _app();
  final store = VocalStore(app);
  await store.load();
  await t.pumpWidget(_host(build(store, VocalPlayer(app))));
  await _settle(t);
  return (app, store);
}

/// The body the page would have sent to one route (the newest call of it).
Map<String, dynamic> _sent(String key) =>
    VocalStore.debugCalls.lastWhere((x) => x.$1 == key, orElse: () => (key, const <String, dynamic>{})).$2;

Future<void> _done(WidgetTester t, Santosh app, [VocalStore? store]) async {
  await t.pumpWidget(const SizedBox.shrink());
  store?.dispose();
  app.dispose();
  _sem?.dispose();
  _sem = null;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);
  tearDown(() {
    VocalStore.debugData = null;
    VocalStore.debugCalls.clear();
  });

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
    // the drawer's groups are the console sidebar's
    expect(kVocalGroups.map((g) => g.$1), ['Make', 'Voices', 'Tools', 'Assets']);
    expect([for (final g in kVocalGroups) ...g.$2].length, VocalPage.values.length, reason: 'every page is in the drawer');
    expect(vocalFormats(store).map((f) => f['id']), ['mp3', 'wav', 'ogg', 'm4a']);
    expect(vocalChecks(VocalFile('a.wav', const [1], seconds: 4, level: .2)).first.$2, '6 more seconds needed');
    expect(vocalChecks(VocalFile('a.wav', const [1], seconds: 24, level: .2)).map((x) => x.$1), [true, true]);
    expect(vocalTakeChoices(store), ['1', '2', '4'], reason: 'up to 4 takes now');
    expect(VocalSettings(takes: 4).body('x')['takes'], 4);
    expect(vocalCanDub(const {'kind': 'tts', 'id': 'a'}), isTrue);
    expect(vocalCanDub(const {'kind': 'dialogue', 'id': 'a'}), isTrue);
    expect(vocalCanDub(const {'kind': 'sfx', 'id': 'a'}), isFalse);
    store.dispose();
    app.dispose();
  });

  testWidgets('a new Vocal chat: the top bar, one line and four ideas; an idea fills the box, never sends', (t) async {
    _phone(t);
    final app = await _open(t, vocalData(started: false));
    expect(find.text('Vocal · Vocal chat'), findsOneWidget);
    expect(find.bySemanticsLabel('Open the Vocal menu'), findsOneWidget);
    expect(find.bySemanticsLabel('Earlier chats'), findsOneWidget);
    expect(find.bySemanticsLabel('Your sounds'), findsOneWidget);
    expect(find.text('What should Hoola say?'), findsOneWidget);
    expect(find.text('Try one'), findsOneWidget);
    expect(find.text('Our shop welcome in Swahili'), findsOneWidget);
    expect(find.bySemanticsLabel('Voice settings: Kiswahili · Amani · Warm · 0.9x'), findsOneWidget);
    expect(find.text('Speech · Kiswahili · Amani'), findsOneWidget, reason: 'the ONE settings pill on the bar');
    expect(find.bySemanticsLabel('Improve what I wrote'), findsOneWidget);
    expect(find.bySemanticsLabel('Add a recording or a file'), findsOneWidget);
    expect(find.text('4 credits · 2 takes · made when you send'), findsOneWidget, reason: 'the price in credits');
    await t.tap(find.text('Our shop welcome in Swahili'));
    await t.pump();
    expect(find.textContaining('Karibu Mkate Bora, mkate safi'), findsWidgets);
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  for (final mode in ['light', 'dark']) {
    testWidgets('$mode the chat: her words without the note, the reply, a take card with A and B, quick changes', (t) async {
      _phone(t);
      final app = await _open(t, vocalData(), mode: mode);
      expect(find.text('Read our shop welcome in Swahili, a warm woman, a little slow'), findsOneWidget);
      expect(find.textContaining('Vocal settings:'), findsNothing, reason: 'her bubble shows only her words');
      expect(find.text('Here are two takes in Kiswahili with Amani. B is a touch slower.'), findsOneWidget);
      expect(find.text('Karibu Mkate Bora'), findsOneWidget, reason: 'the card names what was made');
      expect(find.text('Kiswahili · Amani · 2 takes'), findsOneWidget);
      expect(find.text('Take A'), findsOneWidget);
      expect(find.text('Take B'), findsOneWidget);
      expect(find.text('0:12'), findsOneWidget);
      expect(find.byType(VocalWave), findsNWidgets(2), reason: 'every take has its waveform');
      expect(find.bySemanticsLabel('Play Take A'), findsOneWidget);
      expect(find.bySemanticsLabel('More for Take B'), findsOneWidget);
      for (final q in ['Slower', 'Another voice', 'Make it English']) {
        expect(find.bySemanticsLabel(q), findsOneWidget);
      }
      expect(find.text('Made by AI · marked in the file · Gemini voice'), findsOneWidget);
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
    expect(find.text('3'), findsNothing, reason: 'takes are 1, 2 or 4');
    await t.tap(find.text('4').last);
    await t.pump();
    await t.tap(find.bySemanticsLabel(RegExp('^Language: ')));
    await _settle(t);
    expect(find.text('Search 7 languages'), findsOneWidget);
    expect(find.text('Runa Simi'), findsOneWidget);
    expect(find.text('No engine yet'), findsOneWidget);
    await t.tap(find.text('Runa Simi'));
    await _settle(t);
    expect(find.text('Search 7 languages'), findsOneWidget, reason: 'a language no engine speaks cannot be picked');
    await t.enterText(find.byType(TextField).last, 'portu');
    await t.pump();
    await t.tap(find.text('Português'));
    await _settle(t);
    expect(find.text('Português · Portuguese'), findsOneWidget);
    expect(find.bySemanticsLabel('Ana Beatriz'), findsOneWidget, reason: 'the voices follow the language');
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  testWidgets('the menu opens the drawer with every group; Speech opens in the same frame and speaks', (t) async {
    _phone(t);
    final app = await _open(t, vocalData());
    await t.tap(find.bySemanticsLabel('Open the Vocal menu'));
    await _settle(t);
    for (final g in ['Make', 'Voices', 'Tools', 'Assets']) {
      expect(find.text(g), findsOneWidget, reason: 'group $g');
    }
    for (final p in VocalPage.values) {
      expect(find.bySemanticsLabel(p.title), findsWidgets, reason: 'page ${p.title}');
    }
    expect(find.text('This month · 960 credits left'), findsOneWidget);
    expect(find.text('40 of 1000 used'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Speech').last);
    await _settle(t);
    expect(find.text('Vocal · Speech'), findsOneWidget);
    expect(find.text('Words'), findsOneWidget);
    expect(find.bySemanticsLabel('Voice: Amani. Change'), findsOneWidget, reason: 'the voice as a card');
    for (final r in ['Language: Kiswahili', 'Style: Warm', 'Speed: 0.9x', 'Takes: 2', 'Download as: MP3']) {
      expect(find.bySemanticsLabel(r), findsOneWidget, reason: r);
    }
    expect(find.bySemanticsLabel('Speak it · 4 credits'), findsOneWidget);
    expect(find.text('Nothing is spent until you tap'), findsOneWidget);
    await t.enterText(find.byType(TextField).first, 'Karibu');
    await t.tap(find.text('[warm]'));
    await t.pump();
    expect(find.text('Karibu [warm] '), findsOneWidget, reason: 'a tone goes where the cursor is');
    await t.tap(find.bySemanticsLabel('Speak it · 4 credits'));
    await _settle(t);
    expect(find.text('Take A'), findsOneWidget);
    expect(find.text('Take B'), findsOneWidget);
    expect(find.text('0:15'), findsOneWidget);
    expect(find.text('1 word · about 0:00 · tones are never read aloud'), findsNothing);
    expect(find.bySemanticsLabel('Keep Take A'), findsOneWidget, reason: 'Keep on every take');
    await t.tap(find.bySemanticsLabel('Keep Take A'));
    await t.pump();
    expect(find.bySemanticsLabel('Take A is kept'), findsOneWidget);
    // Back returns to the chat
    final dynamic nav = t.state(find.byType(Navigator));
    await (nav as NavigatorState).maybePop();
    await _settle(t);
    expect(find.text('Vocal · Vocal chat'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  testWidgets('Create > Voice opens Hoola Vocal on its Speech page', (t) async {
    _phone(t);
    final app = await _open(t, vocalData(), page: VocalPage.speech);
    expect(find.text('Vocal · Speech'), findsOneWidget);
    expect(find.text('Words'), findsOneWidget);
    expect(_source('lib/ui/create/create_home.dart'), contains("'Voice-over' => HoolaVocal(app: _store.app, page: VocalPage.speech"));
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  testWidgets('the Voice library: Hoola / Shared / Yours, filters, hear, the shared library, Add to my voices', (t) async {
    _phone(t);
    final (app, store) = await _page(t, (s, p) => VocalVoicesPage(store: s, player: p, lang: 'sw', picked: 'v_amani'));
    expect(find.text('Vocal · Voice library'), findsOneWidget);
    for (final tab in ['Hoola', 'Shared', 'Yours']) {
      expect(find.bySemanticsLabel(tab), findsOneWidget, reason: 'tab $tab');
    }
    expect(find.text('Amani'), findsOneWidget, reason: 'the language filter starts on Kiswahili');
    expect(find.text('Kofi'), findsNothing);
    await t.tap(find.text('Kiswahili'));
    await _settle(t);
    await t.tap(find.text('Auto · the language of your words'));
    await _settle(t);
    expect(find.text('Layla'), findsOneWidget);
    expect(find.textContaining('Premium'), findsWidgets);
    expect(find.bySemanticsLabel('Hear Kofi'), findsOneWidget);
    expect(find.bySemanticsLabel('Amani is in use'), findsOneWidget);
    await t.tap(find.text('Any gender'));
    await _settle(t);
    await t.tap(find.text('Men').last);
    await _settle(t);
    expect(find.text('Kofi'), findsOneWidget);
    expect(find.text('Layla'), findsNothing);
    await t.enterText(find.byType(TextField), 'ghana');
    await t.pump();
    expect(find.text('Kofi'), findsOneWidget);
    expect(find.text('Baraka'), findsNothing);
    // the shared library
    await t.tap(find.bySemanticsLabel('Shared'));
    await _settle(t);
    await t.pump(const Duration(milliseconds: 600));
    expect(find.text('Kavya'), findsOneWidget);
    expect(find.text('Bright · Hindi, Marathi · ads'), findsOneWidget);
    expect(find.bySemanticsLabel('Hear Kavya'), findsOneWidget);
    expect(find.text('Most used'), findsOneWidget, reason: 'the shared library has its order');
    await t.tap(find.bySemanticsLabel('Kavya'));
    await _settle(t);
    expect(find.text('Shared library · used 12400 times'), findsOneWidget);
    expect(find.bySemanticsLabel('Add to my voices'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Add to my voices'));
    await _settle(t);
    // Yours
    await t.enterText(find.byType(TextField), '');
    await t.tap(find.bySemanticsLabel('Yours'));
    await _settle(t);
    expect(find.text('My voice'), findsOneWidget);
    expect(find.text('Your clone · every language'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Make your own voice'));
    await _settle(t);
    expect(find.text('Vocal · Your voice'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('Your voice: record the statement in the app (checked), tick, make; describe three; change one', (t) async {
    _phone(t);
    final (app, store) = await _page(t, (s, p) => VocalYourVoicePage(store: s, player: p));
    expect(find.text('Vocal · Your voice'), findsOneWidget);
    for (final w in ['Record your voice', 'Describe a voice', 'Change a voice']) {
      expect(find.bySemanticsLabel(w), findsOneWidget, reason: w);
    }
    expect(find.text('Read this out loud, in your own voice'), findsOneWidget);
    expect(find.text('“Concordo que o Hoola crie a minha voz, apenas para o meu uso.”'), findsOneWidget);
    expect(find.text('“I agree that Hoola makes my voice, for my own use only.”'), findsOneWidget);
    expect(find.text('Tap to record'), findsOneWidget);
    expect(find.text('0:00 of 0:30'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Record'));
    await _settle(t);
    expect(find.text('Recorded'), findsOneWidget);
    expect(find.text('0:24 of 0:30'), findsOneWidget);
    expect(find.text('Long enough'), findsOneWidget);
    expect(find.text('Loud enough'), findsOneWidget);
    final make = find.bySemanticsLabel('Make my voice · 4 credits');
    expect(make, findsOneWidget);
    expect(t.getSemantics(make).hasFlag(SemanticsFlag.isEnabled), isFalse, reason: 'not before her tick');
    await t.tap(find.byType(Switch));
    await t.pump();
    expect(t.getSemantics(make).hasFlag(SemanticsFlag.isEnabled), isTrue);
    // describe
    await t.tap(find.bySemanticsLabel('Describe a voice'));
    await t.pump();
    await t.enterText(find.byType(TextField).first, 'A calm grandmother from Nairobi, warm and slow');
    await t.pump();
    await t.tap(find.bySemanticsLabel('Make 3 voices to hear'));
    await _settle(t);
    expect(find.text('Warm and slow'), findsOneWidget);
    expect(find.text('Husky, older'), findsOneWidget);
    expect(find.bySemanticsLabel('Play Husky, older'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Pick').at(1));
    await t.pump();
    expect(find.text('Picked'), findsOneWidget);
    expect(find.text('Its name'), findsOneWidget);
    // change
    await t.tap(find.bySemanticsLabel('Change a voice'));
    await t.pump();
    expect(find.text('Start from'), findsOneWidget);
    expect(find.bySemanticsLabel('Make the changed voice'), findsOneWidget);
    expect(find.text('Recorded · consent kept'), findsOneWidget, reason: 'Your voices lists her clone');
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('Dubbing: a new dub (video, languages, voices), then the line editor with Redo and Download', (t) async {
    _phone(t);
    final (app, store) = await _page(t, (s, p) => VocalDubbingPage(store: s, player: p, embedded: false));
    expect(find.text('Vocal · Dubbing'), findsOneWidget);
    expect(find.bySemanticsLabel('Choose the video'), findsOneWidget);
    expect(find.text('0 of 4'), findsOneWidget, reason: 'matched voices take 4 languages');
    await t.tap(find.bySemanticsLabel('Choose the video'));
    await _settle(t);
    expect(find.text('product.mp4'), findsOneWidget);
    await t.tap(find.text('Español'));
    await t.pump();
    expect(find.text('1 of 4'), findsOneWidget);
    await t.tap(find.text('Their own voices'));
    await t.pump();
    expect(find.text('1 of 6'), findsOneWidget);
    expect(find.bySemanticsLabel('Dub it · 4 credits'), findsOneWidget);
    expect(find.text('Dub into Quechua could not be made'), findsNothing);
    expect(find.textContaining('No voice engine speaks Quechua yet'), findsOneWidget, reason: 'a failed dub says why');
    await t.tap(find.bySemanticsLabel('Product video, Spanish'));
    await _settle(t);
    expect(find.text('Cada caja se hace a mano, cada mañana.'), findsWidgets);
    expect(find.text('Every box is made by hand, every morning.'), findsOneWidget);
    expect(find.text('Longer than the original. Shorten it, or it is read a little faster.'), findsOneWidget);
    expect(find.text('Rahul · edited'), findsOneWidget);
    expect(find.bySemanticsLabel('Redo'), findsNWidgets(2));
    expect(find.bySemanticsLabel('Download'), findsOneWidget);
    expect(find.bySemanticsLabel('Add a language'), findsWidgets);
    expect(find.text('Edit any line, then redo only that line · 1 credit a line'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Download'));
    await _settle(t);
    for (final o in ['Video with the dub', 'Sound only, MP3', 'Subtitles, SRT', 'Subtitles, VTT']) {
      expect(find.text(o), findsOneWidget, reason: o);
    }
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('a dub made in their own voices says plainly why its lines cannot be changed', (t) async {
    _phone(t);
    VocalStore.debugData = vocalData();
    (VocalStore.debugData!['dub_lines'] as Map)['editable'] = false;
    (VocalStore.debugData!['dub_lines'] as Map)['why'] = 'Made in their own voices: the lines cannot be changed one by one.';
    final app = await _app();
    final store = VocalStore(app);
    await store.load();
    await t.pumpWidget(_host(VocalDubbingPage(store: store, player: VocalPlayer(app), embedded: false)));
    await _settle(t);
    await t.tap(find.bySemanticsLabel('Product video, Spanish'));
    await _settle(t);
    expect(find.text('Made in their own voices: the lines cannot be changed one by one.'), findsOneWidget);
    expect(find.bySemanticsLabel('Redo'), findsNothing);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('Dialogue, Studio and the tools open with their own controls', (t) async {
    _phone(t);
    final pages = <(String, Widget Function(VocalStore, VocalPlayer), List<String>)>[
      ('Dialogue', (s, p) => VocalDialoguePage(store: s, player: p, settings: vocalDesignSettings(), embedded: false),
          ['Speakers', 'Host', 'Guest', 'Natural talk, one take', 'Line by line', 'Add a line', 'Add a speaker']),
      ('Studio', (s, p) => VocalStudioPage(store: s, player: p, settings: vocalDesignSettings(), embedded: false),
          ['New reading', 'Your readings', 'The Lighthouse Keeper', '3 chapters · 2 made · English']),
      ('Voice changer', (s, p) => VocalChangerPage(store: s, player: p, embedded: false),
          ['Tap to record', 'Remove room noise first', 'Change it · 4 credits']),
      ('Clean-up', (s, p) => VocalCleanupPage(store: s, player: p, embedded: false),
          ['Remove background noise', 'Even out the loudness', 'Take the voice out of music', 'Clean it']),
      ('Sound effects', (s, p) => VocalSfxPage(store: s, player: p, embedded: false),
          ['Describe the sound', 'Loops smoothly', 'Ready-made, free', 'door bell']),
      ('Dictionary', (s, p) => VocalDictionaryPage(store: s, embedded: false),
          ['Add a word', 'Import a list', 'Mithas', '/mɪˈt̪ʰaːs/ · Every language']),
      ('Settings', (s, p) => VocalSettingsPage(store: s, settings: vocalDesignSettings(), embedded: false),
          ['Engines', 'Gemini voice', 'Not set up', 'What things cost', '2 credits', 'Free', 'Defaults', 'This month · 960 credits left']),
      ('Your sounds', (s, p) => VocalSoundsPage(store: s, player: p, onAsk: (_) {}),
          ['Karibu Mkate Bora', 'Dub into Quechua could not be made']),
    ];
    for (final (title, build, texts) in pages) {
      final (app, store) = await _page(t, build);
      expect(find.text('Vocal · $title'), findsOneWidget, reason: title);
      for (final x in texts) {
        expect(find.textContaining(x), findsWidgets, reason: '$title: $x');
      }
      expect(t.takeException(), isNull, reason: title);
      await t.pumpWidget(const SizedBox.shrink());
      store.dispose();
      app.dispose();
    }
    _sem?.dispose();
    _sem = null;
  });

  testWidgets('Studio: a reading opens with its chapters, who reads it, Make and Export', (t) async {
    _phone(t);
    final (app, store) = await _page(t, (s, p) => VocalStudioPage(store: s, player: p, settings: vocalDesignSettings(), embedded: false));
    await t.tap(find.bySemanticsLabel('The Lighthouse Keeper'));
    await _settle(t);
    expect(find.bySemanticsLabel('Who reads it: Kofi'), findsOneWidget);
    expect(find.text('The keeper'), findsOneWidget);
    expect(find.text('Made · 10:40'), findsOneWidget);
    expect(find.text('Not made yet'), findsOneWidget);
    expect(find.text('1 paragraph changed · 2:00'), findsOneWidget);
    expect(find.text('By Asha Rao'), findsOneWidget);
    expect(find.text('2 of 3 chapters made'), findsOneWidget);
    expect(find.bySemanticsLabel('Make again'), findsOneWidget);
    expect(find.bySemanticsLabel('Make'), findsOneWidget);
    expect(find.bySemanticsLabel('Make the changes'), findsOneWidget);
    expect(find.text('2 chapters not made yet · you can stop any time, nothing made is lost'), findsOneWidget);
    expect(find.bySemanticsLabel('Make all 2 left'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Choose who reads whom'));
    await _settle(t);
    expect(find.text('The narrator reads small parts'), findsOneWidget);
    expect(find.textContaining('Elias'), findsWidgets);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('Your sounds: filters by kind, and a dub that could not be made is said plainly', (t) async {
    _phone(t);
    String asked = '';
    final (app, store) = await _page(t, (s, p) => VocalSoundsPage(store: s, player: p, onAsk: (w) => asked = w));
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
    await _done(t, app, store);
  });


  testWidgets('Dialogue: Small reactions and Soft music under it ride the body; the version says what it carries', (t) async {
    _phone(t);
    final d = vocalData()
      ..['dialogue'] = {'id': 'dl1', 'kind': 'dialogue', 'title': 'Bakery talk', 'seconds': 21, 'ext': 'mp3', 'reactions': 3, 'music': 'soft'};
    final (app, store) = await _pageWith(t, d, (s, p) => VocalDialoguePage(store: s, player: p, settings: vocalDesignSettings(), embedded: false));
    expect(find.text('Small reactions'), findsOneWidget);
    expect(find.text('Short listener sounds like “Mm-hmm.” between the longer lines.'), findsOneWidget);
    expect(find.text('Soft music under it'), findsOneWidget);
    expect(find.textContaining('A quiet music bed under the voices'), findsOneWidget);
    await t.enterText(find.byType(TextField).first, 'Welcome to the show.');
    await t.pump();
    final switches = find.byType(Switch);
    expect(switches, findsNWidgets(2));
    await t.ensureVisible(switches.first);
    await t.tap(switches.first);
    await t.pump();
    await t.tap(switches.last);
    await t.pump();
    await t.tap(find.bySemanticsLabel('Make the talk · 4 credits'));
    await _settle(t);
    final body = _sent('dialogue');
    expect(body['reactions'], isTrue);
    expect(body['music'], 'soft');
    expect(body['mode'], 'natural');
    expect((body['lines'] as List).single, {'speaker': 'Host', 'text': 'Welcome to the show.'});
    expect(find.text('Version 1 · 3 reactions · soft music'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('Dialogue: Write it from a document fills the lines with the script, nothing is made yet', (t) async {
    _phone(t);
    final d = vocalData()
      ..['podcast'] = {'title': 'Sourdough at dawn', 'lang': 'sw', 'lines': [
        {'speaker': 'Host', 'text': 'Welcome to the bakery show.'},
        {'speaker': 'Guest', 'text': 'Thanks for having me.'},
        {'speaker': 'Host', 'text': 'Tell us about sourdough.'},
      ]};
    final (app, store) = await _pageWith(t, d, (s, p) => VocalDialoguePage(store: s, player: p, settings: vocalDesignSettings(), embedded: false));
    await t.tap(find.bySemanticsLabel('Write it from a document'));
    await _settle(t);
    expect(find.text('Write it from a document'), findsWidgets);
    for (final tab in ['Paste text', 'Web address', 'A file']) {
      expect(find.bySemanticsLabel(tab), findsOneWidget, reason: tab);
    }
    expect(find.text('3 minutes'), findsOneWidget);
    expect(find.text('Speakers: Host, Guest'), findsOneWidget);
    await t.enterText(find.widgetWithText(TextField, 'Paste an article, notes or a report'), 'Our bakery opens at five. We bake sourdough every morning.');
    await t.pump();
    await t.tap(find.bySemanticsLabel('Write the script'));
    await _settle(t);
    final body = _sent('podcast');
    expect(body['text'], startsWith('Our bakery opens at five.'));
    expect(body['minutes'], 3);
    expect(body['lang'], 'sw');
    expect([for (final h in body['hosts'] as List) (h as Map)['name']], ['Host', 'Guest']);
    expect((body['hosts'] as List).first, {'name': 'Host', 'voice': 'v_amani'});
    expect(find.text('Welcome to the bakery show.'), findsOneWidget);
    expect(find.text('Thanks for having me.'), findsOneWidget);
    expect(find.text('Tell us about sourdough.'), findsOneWidget);
    expect(find.text('3 of 40'), findsOneWidget);
    expect(VocalStore.debugCalls.where((x) => x.$1 == 'dialogue'), isEmpty, reason: 'only the words are written; the sound waits for her tap');
    // a web address goes as a web address
    await t.tap(find.bySemanticsLabel('Write it from a document'));
    await _settle(t);
    await t.tap(find.bySemanticsLabel('Web address'));
    await t.pump();
    await t.enterText(find.widgetWithText(TextField, 'https://…'), 'example.com/bakery');
    await t.pump();
    await t.tap(find.bySemanticsLabel('Write the script'));
    await _settle(t);
    expect(_sent('podcast')['url'], 'https://example.com/bakery');
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('Dub it on a take: up to four languages, the price first, the new takes and the languages that failed', (t) async {
    _phone(t);
    final d = vocalData()
      ..['take_dub'] = {'items': [
        {'id': 'td1', 'kind': 'tts', 'title': 'Karibu Mkate Bora', 'lang': 'es', 'seconds': 13, 'ext': 'mp3', 'dubbed_from': 'h1'},
      ], 'failed': [
        {'lang': 'pt', 'name': 'Portuguese', 'why': 'Amani does not speak Portuguese'},
      ], 'credits': 4};
    final (app, store) = await _pageWith(t, d, (s, p) => VocalSoundsPage(store: s, player: p, onAsk: (_) {}));
    await t.tap(find.bySemanticsLabel('More for Shop door bell'));
    await _settle(t);
    expect(find.text('Dub it'), findsNothing, reason: 'an effect cannot be dubbed');
    await t.tapAt(const Offset(20, 20));
    await _settle(t);
    await t.tap(find.bySemanticsLabel('More for Karibu Mkate Bora'));
    await _settle(t);
    await t.tap(find.text('Dub it'));
    await _settle(t);
    expect(find.text('0 of 4'), findsOneWidget);
    expect(find.text('Kiswahili'), findsNothing, reason: 'its own language is not offered');
    expect(find.text('Runa Simi'), findsNothing, reason: 'a language no engine speaks is not offered');
    expect(t.getSemantics(find.bySemanticsLabel('Dub it')).hasFlag(SemanticsFlag.isEnabled), isFalse);
    await t.tap(find.text('Español'));
    await t.pump();
    await t.tap(find.text('Português'));
    await t.pump();
    expect(find.text('2 of 4'), findsOneWidget);
    expect(find.text('About 4 credits a language · 2 languages ≈ 8 credits'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Dub it · 8 credits'));
    await _settle(t);
    final body = _sent('take_dub');
    expect(body['id'], 'h1');
    expect(body['langs'], ['es', 'pt']);
    expect(find.text('Dubbed'), findsOneWidget);
    expect(find.bySemanticsLabel('Play Español'), findsOneWidget);
    expect(find.text('Portuguese could not be made: Amani does not speak Portuguese. Nothing was charged for it.'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('the chat take card offers Dub it on a speech take', (t) async {
    _phone(t);
    final app = await _open(t, vocalData());
    expect(find.text('Dub it'), findsOneWidget);                 // the chip under the takes (v0.999.128)
    await t.tap(find.bySemanticsLabel('More for Take A'));
    await _settle(t);
    expect(find.text('Dub it'), findsNWidgets(2));               // and the take's own menu
    expect(find.text('Change this take'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  testWidgets('a take is kept with one tap and the card shows the voice', (t) async {
    _phone(t);
    final app = await _open(t, vocalData());
    final keep = find.bySemanticsLabel('Keep Take A');
    expect(keep, findsOneWidget);
    await t.tap(keep);
    await _settle(t);
    expect(find.bySemanticsLabel('Take A is kept'), findsOneWidget);
    expect(find.text('Kept'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app);
  });

  testWidgets('an own-voice dub: lines are edited, then one Make the changes makes them again together', (t) async {
    _phone(t);
    final d = vocalData()
      ..['dub_lines'] = {'lang': 'es', 'editable': true, 'own': true, 'remaking': false,
        'note': 'Changed lines are made again together when you tap Make the changes. ElevenLabs allows this on Enterprise accounts.',
        'lines': [
          {'n': 0, 'start': 0, 'end': 4, 'speaker': 'speaker_0', 'src': 'Every box is made by hand.', 'dst': 'Cada caja se hace a mano.',
           'edited': true},
          {'n': 1, 'start': 4, 'end': 8, 'speaker': 'speaker_1', 'src': 'Every morning.', 'dst': 'Cada mañana.', 'edited': false},
        ]}
      ..['dub_redo'] = {'status': 'working', 'lines': 1, 'charged_seconds': 4, 'credits': 3};
    final (app, store) = await _pageWith(t, d, (s, p) => VocalDubbingPage(store: s, player: p, embedded: false));
    await t.tap(find.bySemanticsLabel('Product video, Spanish'));
    await _settle(t);
    expect(find.text('Changed lines are made again together when you tap Make the changes. ElevenLabs allows this on Enterprise accounts.'),
        findsOneWidget);
    expect(find.bySemanticsLabel('Redo'), findsNothing, reason: 'own voices: no per-line Redo');
    expect(find.bySemanticsLabel(RegExp('^Edit the line at ')), findsNWidgets(2));
    expect(find.text('speaker_0 · edited'), findsOneWidget);
    final make = find.bySemanticsLabel('Make the changes');
    expect(make, findsOneWidget);
    expect(t.getSemantics(make).hasFlag(SemanticsFlag.isEnabled), isTrue);
    await t.tap(make);
    await _settle(t);
    expect(_sent('dub_redo'), {'n': 0, 'lang': 'es'});
    expect(find.text('Making the changed lines…'), findsOneWidget);
    expect(find.bySemanticsLabel(RegExp('^Edit the line at ')), findsNothing, reason: 'no edits while the lines are made again');
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('a dub made in steps: the lines wait for her OK, a long line is shortened, names and the new downloads', (t) async {
    _phone(t);
    final d = vocalData();
    (d['dubs'] as List)[1] = {'id': 'd2', 'v': 2, 'status': 'check', 'name': 'Product video', 'mode': 'matched', 'made': 1700000500, 'check': true,
      'langs': [{'code': 'es', 'name': 'Spanish', 'status': 'check', 'step': 'check'}], 'changed': {'es': 0},
      'people': [{'id': 'S1', 'name': 'Priya', 'lines': 1}, {'id': 'S2', 'name': 'Speaker 2', 'lines': 1}]};
    d['dub_lines'] = {'lang': 'es', 'editable': true, 'status': 'check', 'lines': [
      {'n': 0, 'start': 0, 'end': 4, 'speaker': 'S1', 'name': 'Priya', 'src': 'Welcome to Asha Sweets.', 'dst': 'Bienvenidos a Asha Dulces.',
       'fit': 82, 'kept_missing': ['Asha Sweets']},
      {'n': 1, 'start': 4, 'end': 5, 'speaker': 'S2', 'name': 'Speaker 2', 'src': 'No colours. Ever.', 'dst': 'Nunca colores. Jamás, es nuestra promesa.',
       'fit': 168, 'too_long': true},
    ]};
    d['dub_shorten'] = {'line': {'n': 1, 'dst': 'Nunca colores.', 'fit': 92, 'too_long': false, 'edited': true}, 'before': 'Nunca colores. Jamás, es nuestra promesa.'};
    final (app, store) = await _pageWith(t, d, (s, p) => VocalDubbingPage(store: s, player: p, embedded: false));
    await t.tap(find.bySemanticsLabel(RegExp('^Product video')));
    await _settle(t);
    expect(find.text('Nothing is spoken yet. Read the Spanish lines, change any, then say OK.'), findsOneWidget);
    expect(find.text('Priya'), findsOneWidget, reason: 'the lines say who speaks by name');
    expect(find.text('168% of their time'), findsOneWidget);
    expect(find.text('“Asha Sweets” is missing; it is kept as it is.'), findsOneWidget);
    expect(find.bySemanticsLabel('Redo'), findsNothing, reason: 'changed lines are made again together');
    await t.tap(find.bySemanticsLabel('Shorten'));
    await _settle(t);
    expect(_sent('dub_shorten'), {'n': 1, 'lang': 'es'});
    expect(find.text('Nunca colores.'), findsOneWidget);
    expect(find.bySemanticsLabel('Shorten'), findsNothing);
    await t.pump(const Duration(seconds: 5));                                     // the toast over the dock goes first
    await _settle(t);
    await t.tap(find.bySemanticsLabel('OK, speak them'));
    await _settle(t);
    expect(_sent('dub_ok'), {'lang': 'es'});
    expect(find.text('Names', skipOffstage: false), findsOneWidget, reason: 'the people can be named');
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('a new dub asks for her OK first and keeps her words', (t) async {
    _phone(t);
    final (app, store) = await _page(t, (s, p) => VocalDubbingPage(store: s, player: p, embedded: false));
    expect(find.text('Let me read the lines before they are spoken'), findsOneWidget);
    expect(find.text('Words to keep as they are'), findsOneWidget);
    await t.enterText(find.byType(TextField).last, 'Kaju Katli');
    await t.testTextInput.receiveAction(TextInputAction.done);
    await t.pump();
    expect(find.text('Kaju Katli  ×'), findsOneWidget);
    await t.tap(find.text('Their own voices'));
    await t.pump();
    expect(find.text('Let me read the lines before they are spoken'), findsNothing, reason: 'their own voices are made in one go');
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('an own-voice dub that could not be made again says why', (t) async {
    _phone(t);
    final d = vocalData();
    ((d['dubs'] as List)[1]['langs'] as List)[0] = {'code': 'es', 'name': 'Spanish', 'status': 'ready', 'video_id': 'hv1',
        'remake_error': 'ElevenLabs did not finish the changed lines. Nothing was charged.'};
    d['dub_lines'] = {'lang': 'es', 'editable': true, 'own': true, 'remaking': false, 'note': '', 'lines': [
      {'n': 0, 'start': 0, 'end': 4, 'speaker': 'speaker_0', 'src': 'Hi.', 'dst': 'Hola.', 'edited': true},
    ]};
    final (app, store) = await _pageWith(t, d, (s, p) => VocalDubbingPage(store: s, player: p, embedded: false));
    await t.tap(find.bySemanticsLabel('Product video, Spanish'));
    await _settle(t);
    expect(find.text('ElevenLabs did not finish the changed lines. Nothing was charged.'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('Speech: Play while it is made only for a Premium voice when the server can stream', (t) async {
    _phone(t);
    final premium = VocalSettings(lang: 'ar', voice: 'v_layla', style: 'warm', takes: 1);
    // a standard voice: not offered
    var d = vocalData();
    (d['overview'] as Map)['status'] = {'connected': {'stream': true}};
    var (app, store) = await _pageWith(t, d, (s, p) => VocalSpeechPage(store: s, player: p, settings: vocalDesignSettings(), embedded: false));
    expect(find.bySemanticsLabel('Play while it is made'), findsNothing, reason: 'Amani is a standard voice');
    await _done(t, app, store);
    // a Premium voice but no streaming on this server: not offered
    _phone(t);
    d = vocalData();
    (app, store) = await _pageWith(t, d, (s, p) => VocalSpeechPage(store: s, player: p, settings: premium, embedded: false));
    expect(find.bySemanticsLabel('Play while it is made'), findsNothing, reason: 'stream is not connected');
    await _done(t, app, store);
    // a Premium voice and streaming: offered, and the body carries her words and voice
    _phone(t);
    d = vocalData()..['tts_stream'] = {'url': '/api/vocal/stream/tok1', 'format': 'mp3', 'credits': 2, 'voice_name': 'Layla'};
    (d['overview'] as Map)['status'] = {'connected': {'stream': true}};
    (app, store) = await _pageWith(t, d, (s, p) => VocalSpeechPage(store: s, player: p, settings: premium, embedded: false));
    final play = find.bySemanticsLabel('Play while it is made');
    expect(play, findsOneWidget);
    expect(find.textContaining('one take, heard as it is spoken'), findsOneWidget);
    await t.enterText(find.byType(TextField).first, 'مرحبا بكم');
    await t.pump();
    await t.tap(play);
    await t.pump();
    final body = _sent('tts_stream');
    expect(body['voice'], 'v_layla');
    expect(body['lang'], 'ar');
    expect(body['text'], 'مرحبا بكم');
    expect(find.text('Playing as it is made · 2 credits. It is kept in Your sounds.'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('Settings: Keep my sounds is saved; an app key is shown once; removing a key asks first', (t) async {
    _phone(t);
    final d = vocalData()
      ..['apps'] = {
        'keys': [{'id': 'k1', 'name': 'Shop site', 'last4': 'Ab12', 'made': '2026-11-01T10:00:00', 'used_at': '', 'calls': 5}],
        'hooks': [{'id': 'wh1', 'url': 'https://shop.example/hoola', 'events': ['sound.ready'], 'last_status': '200'}],
        'events': ['sound.ready', 'dub.ready', 'dub.failed'], 'max_keys': 5, 'max_hooks': 3, 'rate_hour': 600,
        'doors': [{'method': 'POST', 'path': '/api/vocal/v1/speech', 'does': 'Words in, one take out (the sound file)'}],
        'signature': 'X-Hoola-Signature: t=<unix time>,v1=<hex HMAC-SHA256>',
      }
      ..['app_key'] = {'id': 'k2', 'name': 'Shop app', 'last4': 'Zz99', 'key': 'hv_live_FULLKEY123',
        'note': 'Copy this key now. It is shown only once; Hoola keeps only a fingerprint of it.'};
    final (app, store) = await _pageWith(t, d, (s, p) => VocalSettingsPage(store: s, settings: vocalDesignSettings(), embedded: false));
    // keep my sounds
    expect(find.text('Your voices and dictionary are always kept.'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Keep my sounds: Forever'));
    await _settle(t);
    for (final o in ['Forever', '7 days', '30 days', '90 days']) {
      expect(find.text(o), findsWidgets, reason: o);
    }
    await t.tap(find.text('30 days').last);
    await _settle(t);
    expect(_sent('settings'), {'keep_days': 30});
    expect(find.bySemanticsLabel('Keep my sounds: 30 days'), findsOneWidget);
    // for your own apps
    expect(find.text('Shop site'), findsOneWidget);
    expect(find.text('Ends in Ab12 · 5 calls'), findsOneWidget);
    expect(find.text('https://shop.example/hoola'), findsOneWidget);
    expect(find.text('sound.ready · last answer 200'), findsOneWidget);
    expect(find.text('POST /api/vocal/v1/speech · Words in, one take out (the sound file)'), findsOneWidget);
    expect(find.textContaining('X-Hoola-Signature'), findsOneWidget);
    expect(find.text('1 of 5'), findsOneWidget);
    await t.ensureVisible(find.bySemanticsLabel('Make a key'));
    await t.tap(find.bySemanticsLabel('Make a key'));
    await _settle(t);
    await t.enterText(find.byType(TextField).last, 'Shop app');
    await t.tap(find.text('Make it'));
    await _settle(t);
    expect(_sent('app_key'), {'name': 'Shop app'});
    expect(find.text('Your new key'), findsOneWidget);
    expect(find.text('hv_live_FULLKEY123'), findsOneWidget);
    expect(find.text('Copy this key now. It is shown only once; Hoola keeps only a fingerprint of it.'), findsOneWidget);
    expect(find.text('Copy'), findsOneWidget);
    await t.tap(find.text('Done'));
    await _settle(t);
    expect(find.text('hv_live_FULLKEY123'), findsNothing, reason: 'the full key is shown once');
    // removing asks first
    await t.ensureVisible(find.bySemanticsLabel('Remove the key Shop site'));
    await t.tap(find.bySemanticsLabel('Remove the key Shop site'));
    await _settle(t);
    expect(find.text('Remove this key?'), findsOneWidget);
    await t.tap(find.text('Keep'));
    await _settle(t);
    expect(VocalStore.debugCalls.where((x) => x.$1 == 'app_key_delete'), isEmpty);
    await t.tap(find.bySemanticsLabel('Remove the key Shop site'));
    await _settle(t);
    await t.tap(find.text('Remove'));
    await _settle(t);
    expect(_sent('app_key_delete'), {'id': 'k1'});
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('Dialogue: a pause and a cut-in ride the body; Line by line makes one changed line again on its own', (t) async {
    _phone(t);
    final d = vocalData()
      ..['dialogue'] = {'id': 'dl1', 'kind': 'dialogue', 'title': 'Bakery talk', 'seconds': 6, 'ext': 'mp3', 'mode': 'lines', 'take': 'A',
        'cast': {'Host': 'v_amani', 'Guest': 'v_kofi'}, 'segments': [
          {'speaker': 'Host', 'text': 'Welcome to the show.', 'start': 0, 'end': 2, 'pause': 1, 'cut': false},
          {'speaker': 'Guest', 'text': 'Glad to be here.', 'start': 2.9, 'end': 4.5, 'pause': 0, 'cut': true}]}
      ..['dialogue_line'] = {'id': 'dl2', 'kind': 'dialogue', 'title': 'Bakery talk', 'seconds': 6, 'ext': 'mp3', 'mode': 'lines', 'take': 'B', 'remade': 1};
    final (app, store) = await _pageWith(t, d, (s, p) => VocalDialoguePage(store: s, player: p, settings: vocalDesignSettings(), embedded: false));
    await t.enterText(find.byType(TextField).at(0), 'Welcome to the show.');
    await t.enterText(find.byType(TextField).at(1), 'Glad to be here.');
    await t.pump();
    await t.tap(find.bySemanticsLabel('Pause after').first);
    await t.pump();
    await t.tap(find.bySemanticsLabel('Pause · half a second'));
    await t.pump();
    expect(find.bySemanticsLabel('Pause · 1 second'), findsOneWidget);
    expect(find.bySemanticsLabel('Cuts in'), findsOneWidget, reason: 'only a line after the first can cut in');
    await t.tap(find.bySemanticsLabel('Cuts in'));
    await t.pump();
    await t.ensureVisible(find.text('Line by line'));
    await t.tap(find.text('Line by line'));
    await t.pump();
    await t.tap(find.bySemanticsLabel('Make the talk · 4 credits'));
    await _settle(t);
    final body = _sent('dialogue');
    expect(body['mode'], 'lines');
    expect((body['lines'] as List).first, {'speaker': 'Host', 'text': 'Welcome to the show.', 'pause': 1.0});
    expect((body['lines'] as List).last, {'speaker': 'Guest', 'text': 'Glad to be here.', 'cut': true});
    expect(find.text('Made'), findsNWidgets(2));
    await t.enterText(find.byType(TextField).at(1), 'So glad to be here.');
    await t.pump();
    expect(find.text('Changed'), findsOneWidget);
    await t.ensureVisible(find.bySemanticsLabel('Make only this line'));
    await t.tap(find.bySemanticsLabel('Make only this line'));
    await _settle(t);
    expect(_sent('dialogue_line'), {'id': 'dl1', 'n': 1, 'text': 'So glad to be here.', 'speaker': 'Guest'});
    expect(VocalStore.debugCalls.where((x) => x.$1 == 'dialogue').length, 1, reason: 'only the one line is made again');
    expect(find.textContaining('line 2 made again'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  testWidgets('Dialogue: a script from a document carries its kind and what to say; a figure not in it is flagged', (t) async {
    _phone(t);
    final d = vocalData()
      ..['podcast'] = {'title': 'Diwali menu', 'lang': 'en', 'unchecked': 1, 'lines': [
        {'speaker': 'Host', 'text': 'Every box is 20% off.', 'from': 'page 2'},
        {'speaker': 'Guest', 'text': 'We packed 900 boxes.', 'unchecked': ['900']},
      ]};
    final (app, store) = await _pageWith(t, d, (s, p) => VocalDialoguePage(store: s, player: p, settings: vocalDesignSettings(), embedded: false));
    await t.tap(find.bySemanticsLabel('Write it from a document'));
    await _settle(t);
    await t.tap(find.bySemanticsLabel('Interview'));
    await t.pump();
    await t.enterText(find.widgetWithText(TextField, 'Anything to be sure they say (optional)'), 'The offer ends Sunday');
    await t.enterText(find.widgetWithText(TextField, 'Paste an article, notes or a report'), 'Kaju katli is twenty percent off this week, until Sunday.');
    await t.pump();
    await t.tap(find.bySemanticsLabel('Write the script'));
    await _settle(t);
    final body = _sent('podcast');
    expect(body['kind'], 'interview');
    expect(body['must'], 'The offer ends Sunday');
    expect(find.text('From page 2'), findsOneWidget);
    expect(find.text('Check: 900 is not in the document'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
  });

  test('the Tools tab opens the native Vocal screen, not the console page', () {
    expect(_source('lib/ui/shell/hoola_tools.dart'), contains("t.title == 'Hoola Vocal'"));
    expect(_source('lib/ui/shell/hoola_tools.dart'), contains('HoolaVocal(app: app)'));
  });

  test('no server key name and no money shows on a Vocal page', () {
    for (final f in Directory('lib/ui/vocal').listSync().whereType<File>()) {
      final s = f.readAsStringSync();
      expect(s.contains('_API_KEY'), isFalse, reason: f.path);
      expect(RegExp(r'[₹$]\s?\d').hasMatch(s.replaceAll(RegExp(r'\.\$\d|\$\{|\$[a-z_]'), '')), isFalse, reason: '${f.path}: prices are credits only');
    }
  });
}

String _source(String path) => File(path).readAsStringSync();
