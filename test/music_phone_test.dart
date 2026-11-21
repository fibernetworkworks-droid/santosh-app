// v0.999.81 HOOLA MUSIC ON THE PHONE (design canvas claude.ai/artifact/Qq4WmnjktJD7VS9torkejn boards 11-13, "GO BUILD ALL"):
// Create > Music on the phone is the console's Music chat. These tests walk it with the server's own shapes: the start
// screen, Song settings (the price follows the versions), her words shown without the settings note, Hoola's reply, a
// set of versions with its changes, a set being made, a set that could not be made (Try again, nothing charged), the
// "Hoola can't answer" card, the player with the song's words, Your songs with filters, the 40-language sheet, and the
// note her message carries (the same one the console sends).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/create/create_kit.dart';
import 'package:santosh/ui/create/create_music.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

const _conv = 'mc1';

Map<String, dynamic> musicData({Map<String, dynamic>? turn, bool running = false, bool failed = false}) => {
      'conf': {'ready': {'song': true}},
      'items': [
        {'id': 'cr10', 'kind': 'song', 'title': 'Feliz cumple, Lucía · A', 'mime': 'audio/mpeg', 'size': 1, 'created': 1700000100,
         'meta': {'chat': _conv, 'job': 'cj10', 'version': 'A', 'genre': 'Pop', 'language': 'Spanish', 'vocals': 'female',
                  'seconds': 62, 'brief': 'Canción de cumpleaños para Lucía', 'lyrics': '[Coro]\nFeliz cumple, Lucía, hoy tienes seis\nPalmas, palmas'}},
        {'id': 'cr11', 'kind': 'song', 'title': 'Feliz cumple, Lucía · B', 'mime': 'audio/mpeg', 'size': 1, 'created': 1700000101,
         'meta': {'chat': _conv, 'job': 'cj10', 'version': 'B', 'genre': 'Pop', 'language': 'Spanish', 'vocals': 'female', 'seconds': 58}},
        {'id': 'cr12', 'kind': 'song', 'title': 'Feliz cumple, Lucía · A', 'mime': 'audio/mpeg', 'size': 1, 'created': 1700000200,
         'meta': {'chat': _conv, 'job': 'cj11', 'parent': 'cr10', 'edit': 'Reel cut', 'seconds': 30}},
        {'id': 'cr13', 'kind': 'song', 'title': 'Night study', 'mime': 'audio/mpeg', 'size': 1, 'created': 1700000000,
         'meta': {'genre': 'Lo-fi', 'vocals': 'none', 'seconds': 120}},
        {'id': 'cr14', 'kind': 'song', 'title': 'Sunny Bakes', 'mime': 'audio/mpeg', 'size': 1, 'created': 1700000000,
         'meta': {'genre': 'Jingle, Pop', 'vocals': 'group', 'language': 'English', 'seconds': 30}},
      ],
      'jobs': [
        if (running) {'id': 'cj20', 'kind': 'song', 'status': 'running', 'title': 'Lluvia', 'count': 2, 'step': 'Version A · 1 of 2',
          'conv': _conv, 'created': 1700000300},
        if (failed) {'id': 'cj21', 'kind': 'song', 'status': 'failed', 'title': 'Lluvia', 'count': 2, 'conv': _conv, 'created': 1700000300,
          'error': 'The song engine was busy.'},
      ],
      'music': {
        'conv': _conv,
        'title': 'Feliz cumple, Lucía',
        'turn': turn,
        'rows': [
          {'id': 1, 'role': 'assistant', 'text': 'Tell me the song you want, in any language.', 'at': '2023-11-14T22:13:00'},
          {'id': 2, 'role': 'user', 'text': 'Canción de cumpleaños para Lucía, alegre, con palmas\n\n[Web console Song settings: kind Song, language Auto]',
           'at': '2023-11-14T22:14:50'},
          {'id': 3, 'role': 'assistant', 'text': 'Hago dos versiones alegres, con palmas, para Lucía.', 'at': '2023-11-14T22:14:55'},
        ],
      },
    };

Widget _host(Widget w, {String mode = 'light'}) => MaterialApp(
      builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(disableAnimations: true), child: child!),
      home: HoolaTheme(appearance: mode, child: w),
    );

void _phone(WidgetTester t) {
  t.view.physicalSize = const Size(390 * 3, 2400 * 3);
  t.view.devicePixelRatio = 3;
  addTearDown(t.view.reset);
  _sem = t.ensureSemantics();
}

SemanticsHandle? _sem;

Future<void> _settle(WidgetTester t) async {
  await t.pump();
  await t.pump(const Duration(milliseconds: 600));
}

Future<(Santosh, CreateStore)> _open(WidgetTester t, Map<String, dynamic> data, {String mode = 'light'}) async {
  CreateStore.debugData = data;
  final app = await _app();
  final store = CreateStore(app);
  await store.load();
  await t.pumpWidget(_host(CreateMusic(store: store), mode: mode));
  await _settle(t);
  return (app, store);
}

Future<void> _done(WidgetTester t, Santosh app, CreateStore store) async {
  await t.pumpWidget(const SizedBox.shrink());
  store.dispose();
  app.dispose();
}

void _unsee() {
  _sem?.dispose();
  _sem = null;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);
  tearDown(() => CreateStore.debugData = null);

  test('her settings ride her message as the console note: no square brackets, lyrics by parts, the song she means', () {
    final s = MusicSettings()
      ..lang = 'Spanish'
      ..vox = 'Female'
      ..versions = 4
      ..keep = 'drums'
      ..lyrics = '[Chorus]\nFeliz cumple\nPalmas';
    final h = s.hint(focus: 'cr10');
    expect(h, startsWith('Song settings: kind Song, language Spanish, singers female'));
    expect(h, contains('4 versions'));
    expect(h, contains('keep out: drums'));
    expect(h, contains('{Chorus} / Feliz cumple / Palmas'));
    expect(h, contains('the song she means: id cr10'));
    expect(h.contains('[') || h.contains(']') || h.contains('\n'), isFalse, reason: 'the note rides inside [Web console ...]');
    expect(musicStripNotes('Hola\n\n[Web console $h]'), 'Hola');
    final b = (MusicSettings()..tab = 'Instrumental').body('Lo-fi beat');
    expect(b['vocals'], 'none');
    expect(b['lyrics'], '');
    expect(b['versions'], 2);
    expect(musicPrice(2), '2 versions · 160 credits');
  });

  testWidgets('a new Music chat starts with one line and four ideas; the price sits under the box', (t) async {
    _phone(t);
    final d = musicData()..['music'] = {'conv': 'mc-new', 'rows': []};
    final (app, store) = await _open(t, d);
    expect(find.text('What shall we make?'), findsOneWidget);
    expect(find.text('Try one'), findsOneWidget);
    expect(find.text('A 30 second jingle for my bakery'), findsOneWidget);
    expect(find.text('2 versions · 160 credits · made when you send'), findsOneWidget);
    await t.tap(find.text('A 30 second jingle for my bakery'));
    await t.pump();
    expect(find.textContaining('Sunny Bakes'), findsWidgets, reason: 'an idea fills the box, it never sends by itself');
    expect(t.takeException(), isNull);
    await _done(t, app, store);
    _unsee();
  });

  for (final mode in ['light', 'dark']) {
    testWidgets('$mode the chat: her words without the note, the reply, versions A and B, a free change with Undo', (t) async {
      _phone(t);
      final (app, store) = await _open(t, musicData(), mode: mode);
      expect(find.text('Canción de cumpleaños para Lucía, alegre, con palmas'), findsOneWidget);
      expect(find.textContaining('Web console'), findsNothing, reason: 'her bubble shows only her words');
      expect(find.text('Hago dos versiones alegres, con palmas, para Lucía.'), findsOneWidget);
      expect(find.text('Version A'), findsOneWidget);
      expect(find.text('Version B'), findsOneWidget);
      expect(find.bySemanticsLabel('Reel cut'), findsWidgets);
      expect(find.bySemanticsLabel('More like this'), findsOneWidget);
      expect(find.textContaining('Changed: Reel cut'), findsOneWidget);
      expect(find.bySemanticsLabel('Undo'), findsOneWidget, reason: 'a change is a new version she can undo');
      expect(find.text('Made by AI · marked in the file'), findsWidgets);
      expect(t.takeException(), isNull);
      await _done(t, app, store);
      _unsee();
    });
  }

  testWidgets('a set being made, and one that could not be made: Try again, nothing charged', (t) async {
    _phone(t);
    var (app, store) = await _open(t, musicData(running: true));
    expect(find.text('Making 2 versions · Version A · 1 of 2'), findsOneWidget);
    expect(find.text('About a minute a version · 160 credits'), findsOneWidget);
    await _done(t, app, store);
    (app, store) = await _open(t, musicData(failed: true));
    expect(find.text('Could not be made'), findsOneWidget);
    expect(find.text('The song engine was busy. Nothing was charged for it.'), findsOneWidget);
    expect(find.bySemanticsLabel('Try again'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
    _unsee();
  });

  testWidgets('Hoola cannot answer: the song can still be made straight away, its price on the button', (t) async {
    _phone(t);
    final d = musicData(turn: {'status': 'failed', 'line': ''});
    final rows = (d['music'] as Map)['rows'] as List;
    rows.add({'id': 4, 'role': 'user', 'text': 'Una canción triste de lluvia\n\n[Web console Song settings: kind Song]', 'at': '2023-11-14T23:00:00'});
    final (app, store) = await _open(t, d);
    expect(find.text('Hoola can’t answer right now'), findsOneWidget);
    expect(find.bySemanticsLabel('Make the song now · 160 credits'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
    _unsee();
  });

  testWidgets('Song settings: versions change the price; the language sheet searches 40 languages', (t) async {
    _phone(t);
    final (app, store) = await _open(t, musicData());
    await t.tap(find.text('Song · Auto · 2 versions'));
    await _settle(t);
    expect(find.text('Song settings'), findsOneWidget);
    expect(find.text('2 versions · 160 credits'), findsOneWidget);
    await t.tap(find.text('4').last);
    await t.pump();
    expect(find.text('4 versions · 320 credits'), findsOneWidget);
    await t.tap(find.bySemanticsLabel(RegExp('^Language: ')));
    await _settle(t);
    expect(find.text('Most used'), findsOneWidget);
    expect(find.text('Español'), findsOneWidget);
    await t.enterText(find.byType(TextField).last, 'swa');
    await t.pump();
    expect(find.text('Kiswahili'), findsOneWidget);
    await t.tap(find.text('Kiswahili'));
    await _settle(t);
    expect(find.textContaining('Swahili'), findsWidgets);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
    _unsee();
  });

  testWidgets('a song opens in its player with its versions and its words; Your songs filters by kind', (t) async {
    _phone(t);
    final (app, store) = await _open(t, musicData());
    await t.tap(find.bySemanticsLabel('Open Version A'));
    await _settle(t);
    expect(find.text('Feliz cumple, Lucía, hoy tienes seis'), findsOneWidget);
    expect(find.text('Coro'), findsOneWidget, reason: 'a part tag is shown as a small label');
    expect(find.text('Reel cut'), findsWidgets);
    expect(find.bySemanticsLabel('More like this'), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Close the player'));
    await _settle(t);
    await t.tap(find.bySemanticsLabel('Your songs'));
    await _settle(t);
    expect(find.text('Night study'), findsOneWidget);
    expect(find.text('Sunny Bakes'), findsOneWidget);
    await t.tap(find.text('Jingles'));
    await t.pump();
    expect(find.text('Sunny Bakes'), findsOneWidget);
    expect(find.text('Night study'), findsNothing);
    await t.tap(find.text('Instrumentals'));
    await t.pump();
    expect(find.text('Night study'), findsOneWidget);
    expect(t.takeException(), isNull);
    await _done(t, app, store);
    _unsee();
  });
}
