// v0.999.96 HOOLA VOCAL REDESIGN, PHONE (docs/HOOLA_VOCAL_REDESIGN.md sections 2-3 + 5, boards Dialogue, Studio, Dubbing,
// PhoneDubbing): the three Make pages beside Speech.
//  - Dialogue: speakers with their voices, the lines, and how it sounds - "Natural talk, one take" (both voices made
//    together) or "Line by line" (each line its own take) - the price in credits on the one black pill.
//  - Studio: long readings (a book, a document, pasted text) in chapters; a chapter re-made re-reads only what changed;
//    who reads whom; export as one file.
//  - Dubbing: her video in other languages (up to 6), then the line editor per language: what they said, what is said
//    now, a line longer than the original flagged, edit one line, Redo only that line (1 credit), Download the video,
//    the sound, or the subtitles (SRT / VTT). Nothing paid runs without her tap.
import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../hoola_theme.dart';
import 'vocal_home.dart' show VocalLanguageSheet;
import 'vocal_kit.dart';
import 'vocal_voices.dart' show VocalVoicesPage;

/// Picks one voice (the Voice library as a picker): its id, or null.
Future<String?> vocalPickVoice(BuildContext context, VocalStore store, VocalPlayer player, {String lang = 'auto', String picked = ''}) =>
    Navigator.of(context).push<String>(MaterialPageRoute(
        builder: (_) => HoolaTheme(appearance: store.app.appearance,
            child: VocalVoicesPage(store: store, player: player, lang: lang, picked: picked))));

/// A voice's name, else "Choose a voice".
String vocalVoiceName(VocalStore store, String id) {
  if (id.isEmpty) return 'Choose a voice';
  final v = store.voice(id);
  return v == null ? id : crS(v['name']);
}

// ================================================================================================ Dialogue
class _Line {
  _Line(this.speaker, [String text = '']) : ctl = TextEditingController(text: text);
  String speaker;
  final TextEditingController ctl;
}

class VocalDialoguePage extends StatefulWidget {
  const VocalDialoguePage({super.key, required this.store, required this.player, required this.settings, this.conv = '', this.embedded = true});
  final VocalStore store;
  final VocalPlayer player;
  final VocalSettings settings;
  final String conv;
  final bool embedded;
  @override
  State<VocalDialoguePage> createState() => _VocalDialoguePageState();
}

class _VocalDialoguePageState extends State<VocalDialoguePage> {
  final List<String> _speakers = ['Host', 'Guest'];
  final Map<String, String> _cast = {};
  final List<_Line> _lines = [_Line('Host'), _Line('Guest')];
  String _mode = 'natural';
  List<Map<String, dynamic>> _made = [];
  Map<String, dynamic> _quote = const {};
  bool _busy = false;
  Timer? _wait;
  VocalStore get store => widget.store;

  @override
  void initState() {
    super.initState();
    for (final l in _lines) {
      l.ctl.addListener(_typed);
    }
    _requote();
  }

  @override
  void dispose() {
    _wait?.cancel();
    for (final l in _lines) {
      l.ctl.dispose();
    }
    super.dispose();
  }

  void _typed() {
    if (!mounted) return;
    setState(() {});
    _wait?.cancel();
    _wait = Timer(const Duration(milliseconds: 500), _requote);
  }

  int get _chars => _lines.fold<int>(0, (a, l) => a + l.ctl.text.trim().length);
  List<String> get _used => [for (final s in _speakers) if (_lines.any((l) => l.speaker == s && l.ctl.text.trim().isNotEmpty)) s];

  Future<void> _requote() async {
    if (VocalStore.debug) {
      if (mounted) setState(() => _quote = crMap(VocalStore.debugData!['quote']));
      return;
    }
    try {
      final q = await store.app.api?.vocalQuote({'job': 'dialogue', 'chars': _chars == 0 ? 200 : _chars, 'takes': 1});
      if (q != null && mounted) setState(() => _quote = q);
    } catch (_) {}
  }

  /// A voice for a speaker: theirs, else the first that speaks the language and no one else has.
  String _voiceOf(String s) {
    final v = _cast[s];
    if (v != null && v.isNotEmpty) return v;
    final taken = _cast.values.toSet();
    for (final x in store.voicesFor(widget.settings.lang)) {
      final id = crS(x['id']);
      if (x['ready'] != false && !taken.contains(id) && crS(x['kind']) == 'hoola') {
        _cast[s] = id;
        return id;
      }
    }
    return '';
  }

  Future<void> _castVoice(String s) async {
    final id = await vocalPickVoice(context, store, widget.player, lang: widget.settings.lang, picked: _cast[s] ?? '');
    if (id != null && mounted) setState(() => _cast[s] = id);
  }

  Future<void> _addSpeaker() async {
    if (_speakers.length >= 6) {
      crToast(context, 'Up to 6 speakers in one dialogue.');
      return;
    }
    final ctl = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add a speaker'),
        content: TextField(controller: ctl, autofocus: true, maxLength: 30, decoration: const InputDecoration(hintText: 'Their name or role')),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(ctl.text.trim()), child: const Text('Add')),
        ],
      ),
    );
    ctl.dispose();
    if (name == null || name.isEmpty || !mounted) return;
    if (_speakers.contains(name)) {
      crToast(context, '$name is already a speaker.');
      return;
    }
    setState(() => _speakers.add(name));
  }

  void _removeSpeaker(String s) {
    if (_speakers.length <= 1) return;
    setState(() {
      _speakers.remove(s);
      _cast.remove(s);
      for (final l in _lines) {
        if (l.speaker == s) l.speaker = _speakers.first;
      }
    });
  }

  void _addLine() {
    final last = _lines.isEmpty ? '' : _lines.last.speaker;
    final i = _speakers.indexOf(last);
    final next = _speakers[(i + 1) % _speakers.length];
    final l = _Line(next);
    l.ctl.addListener(_typed);
    setState(() => _lines.add(l));
  }

  void _removeLine(_Line l) {
    setState(() => _lines.remove(l));
    l.ctl.dispose();
    _requote();
  }

  Future<void> _speakerOf(_Line l) async {
    final v = await crPick(context, 'Who says this', _speakers, l.speaker);
    if (v != null && mounted) setState(() => l.speaker = v);
  }

  Future<void> _make() async {
    final rows = [for (final l in _lines) if (l.ctl.text.trim().isNotEmpty) {'speaker': l.speaker, 'text': l.ctl.text.trim()}];
    if (rows.isEmpty) {
      crToast(context, 'Write at least one line.');
      return;
    }
    final cast = <String, String>{};
    for (final s in _used) {
      final v = _voiceOf(s);
      if (v.isEmpty) {
        crToast(context, 'Choose a voice for $s.');
        return;
      }
      cast[s] = v;
    }
    setState(() => _busy = true);
    try {
      List<Map<String, dynamic>> made;
      if (VocalStore.debug) {
        made = crList(VocalStore.debugData!['speech']).take(1).toList();
      } else {
        final api = store.app.api;
        if (api == null) throw Exception('Not connected to the server right now');
        made = vocalMade(await api.vocalDialogue({
          'lines': rows,
          'cast': cast,
          'lang': widget.settings.lang.isEmpty ? 'auto' : widget.settings.lang,
          'style': widget.settings.style,
          'mode': _mode,
          if (widget.conv.isNotEmpty) 'chat': widget.conv,
        }));
      }
      if (!mounted) return;
      setState(() => _made = [...made, ..._made]);
      if (made.isNotEmpty) {
        final id = crS(made.first['id']);
        unawaited(widget.player.toggle(context, id, () => store.app.api!.vocalAudio(id, format: 'mp3'), ext: 'mp3'));
      }
      unawaited(store.load());
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _modeCard(HoolaColors c, String id, String title, String line) {
    final on = _mode == id;
    return Semantics(
      button: true,
      selected: on,
      label: title,
      excludeSemantics: true,
      onTap: () => setState(() => _mode = id),
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => setState(() => _mode = id),
        child: Container(
          constraints: const BoxConstraints(minHeight: 56),
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
          decoration: BoxDecoration(
            color: on ? c.accentSoft : c.surface,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: on ? c.accent : c.line),
          ),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(on ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded, size: 20, color: on ? c.accent : c.ink3),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                Text(line, style: HoolaType.small(c).copyWith(fontSize: 12, color: c.ink2)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final body = ListenableBuilder(
      listenable: Listenable.merge([store, widget.player]),
      builder: (context, _) {
        final c = HoolaColors.of(context);
        final credits = vocalCredits(_quote);
        final two = _used.length == 2 || (_used.isEmpty && _speakers.length == 2);
        return Column(children: [
          Expanded(
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 14, 16, 24), children: [
              VocalLabel('Speakers', note: '${_speakers.length} of 6'),
              VocalBox(
                padding: const EdgeInsets.fromLTRB(10, 4, 4, 4),
                child: Column(children: [
                  for (final s in _speakers)
                    Row(children: [
                      VocalVoiceDot(voice: store.voice(_voiceOf(s)), name: s, size: 32),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text.rich(TextSpan(children: [
                          TextSpan(text: s, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                          TextSpan(text: ' · ${vocalVoiceName(store, _voiceOf(s))}', style: HoolaType.body(c).copyWith(color: c.ink2)),
                        ]), maxLines: 1, overflow: TextOverflow.ellipsis),
                      ),
                      VocalChip(label: 'Change', onTap: () => _castVoice(s)),
                      if (_speakers.length > 1) VocalIconButton(label: 'Remove $s', glyph: CrGlyph.minus, onTap: () => _removeSpeaker(s)),
                    ]),
                  Align(alignment: Alignment.centerLeft, child: VocalChip(label: 'Add a speaker', onTap: _addSpeaker)),
                ]),
              ),
              const SizedBox(height: 16),
              VocalLabel('Lines', note: '${_lines.length} of 40'),
              for (final l in _lines)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: VocalBox(
                    padding: const EdgeInsets.fromLTRB(10, 2, 2, 8),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        VocalChip(label: l.speaker, menu: true, onTap: () => _speakerOf(l)),
                        const Spacer(),
                        VocalIconButton(label: 'Remove this line', glyph: CrGlyph.trash, onTap: () => _removeLine(l)),
                      ]),
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: TextField(
                          controller: l.ctl,
                          minLines: 1,
                          maxLines: 6,
                          maxLength: 1500,
                          buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null,
                          textCapitalization: TextCapitalization.sentences,
                          style: HoolaType.body(c),
                          decoration: vocalInput(c, 'What ${l.speaker} says. [laughs] and [pause] work here.'),
                        ),
                      ),
                    ]),
                  ),
                ),
              Align(
                alignment: Alignment.centerLeft,
                child: VocalChip(label: 'Add a line', onTap: _lines.length >= 40 ? null : _addLine),
              ),
              const SizedBox(height: 16),
              const VocalLabel('How it sounds'),
              _modeCard(c, 'natural', 'Natural talk, one take', 'Both voices made together, so they react, pause and overlap like people'),
              const SizedBox(height: 8),
              _modeCard(c, 'lines', 'Line by line', 'Each line its own take, easier to redo one line'),
              if (_mode == 'natural' && !two) ...[
                const SizedBox(height: 8),
                Text('Natural talk with more than two speakers needs the premium engine; with two it is made on Gemini voice.',
                    style: HoolaType.small(c).copyWith(fontSize: 12, color: c.ink2)),
              ],
              if (_made.isNotEmpty) ...[
                const SizedBox(height: 18),
                const VocalLabel('Made'),
                VocalBox(
                  child: Column(children: [
                    for (var i = 0; i < _made.length; i++) ...[
                      if (i > 0) const SizedBox(height: 8),
                      VocalTakeRow(
                        store: store,
                        player: widget.player,
                        item: _made[i],
                        name: 'Version ${_made.length - i}',
                        onMore: () => _more(_made[i], 'Version ${_made.length - i}'),
                      ),
                    ],
                  ]),
                ),
              ],
            ]),
          ),
          VocalDock(
            note: 'Nothing is spent until you tap',
            child: VocalPill(label: credits.isEmpty ? 'Make the dialogue' : 'Make the dialogue · $credits', busy: _busy,
                onTap: _chars == 0 ? null : _make),
          ),
        ]);
      },
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Dialogue', body: body);
  }

  Future<void> _more(Map<String, dynamic> t, String name) async {
    final pick = await vocalMore(context, name, const ['Download', 'Delete']);
    if (!mounted || pick == null) return;
    if (pick == 'Download') await vocalShare(context, store.app, t, store: store);
    if (pick == 'Delete' && mounted && await vocalDeleteSound(context, store, t)) {
      setState(() => _made = _made.where((x) => crS(x['id']) != crS(t['id'])).toList());
    }
  }
}

// ================================================================================================ Studio
class VocalStudioPage extends StatefulWidget {
  const VocalStudioPage({super.key, required this.store, required this.player, required this.settings, this.conv = '', this.embedded = true});
  final VocalStore store;
  final VocalPlayer player;
  final VocalSettings settings;
  final String conv;
  final bool embedded;
  @override
  State<VocalStudioPage> createState() => _VocalStudioPageState();
}

class _VocalStudioPageState extends State<VocalStudioPage> {
  String _open = '';
  String _busy = '';
  List<Map<String, dynamic>> _characters = [];
  VocalStore get store => widget.store;

  List<Map<String, dynamic>> get _projects => crList(store.ov['projects']);
  Map<String, dynamic> get _project => _projects.firstWhere((p) => crS(p['id']) == _open, orElse: () => const <String, dynamic>{});

  Future<void> _new() async {
    final title = TextEditingController();
    final text = TextEditingController();
    final how = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) {
        final c = HoolaColors.of(ctx);
        return CrHueScope(
          hue: CrHue.voice,
          child: SafeArea(
            child: Padding(
              padding: EdgeInsets.fromLTRB(20, 0, 20, 16 + MediaQuery.viewInsetsOf(ctx).bottom),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text('A new reading', style: HoolaType.heading(c)),
                const SizedBox(height: 6),
                Text('A book, a document or your own words, split into chapters.', style: HoolaType.small(c)),
                const SizedBox(height: 12),
                TextField(controller: title, maxLength: 80, style: HoolaType.body(c), decoration: vocalInput(c, 'Its title'),
                    buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null),
                const SizedBox(height: 8),
                TextField(controller: text, minLines: 4, maxLines: 8, style: HoolaType.body(c), decoration: vocalInput(c, 'Paste the text here')),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(child: VocalPill(label: 'Import a file', quiet: true, onTap: () => Navigator.of(ctx).pop('file'))),
                  const SizedBox(width: 10),
                  Expanded(child: VocalPill(label: 'Use this text', onTap: () => Navigator.of(ctx).pop('text'))),
                ]),
              ]),
            ),
          ),
        );
      },
    );
    final t = title.text.trim();
    final words = text.text.trim();
    title.dispose();
    text.dispose();
    if (how == null || !mounted) return;
    final body = <String, dynamic>{'title': t};
    if (how == 'text') {
      if (words.isEmpty) {
        crToast(context, 'Paste the text first.');
        return;
      }
      body['text'] = words;
    } else {
      final f = await _pickDoc();
      if (f == null || !mounted) return;
      setState(() => _busy = 'import');
      try {
        body['file_id'] = await vocalUpload(store, widget.conv, f);
      } catch (e) {
        if (mounted) {
          vocalError(context, store, e);
          setState(() => _busy = '');
        }
        return;
      }
    }
    setState(() => _busy = 'import');
    try {
      Map<String, dynamic> p;
      if (VocalStore.debug) {
        p = _projects.isEmpty ? const {} : _projects.first;
      } else {
        p = await store.app.api!.vocalProjectImport(body);
        await store.load();
      }
      if (mounted) setState(() => _open = crS(p['id']));
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = '');
  }

  Future<VocalFile?> _pickDoc() async {
    if (VocalStore.debug) return VocalFile('book.txt', const [1]);
    final r = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom,
        allowedExtensions: const ['txt', 'md', 'pdf', 'docx', 'epub', 'html']);
    final f = r?.files.firstOrNull;
    final b = f?.bytes;
    if (f == null || b == null) return null;
    if (b.length > 30 * 1024 * 1024) {
      if (mounted) crToast(context, 'This file is over 30 MB.');
      return null;
    }
    return VocalFile(f.name, b);
  }

  /// The reading saved with its chapters (the server replaces the chapters with what it is sent, so they always go).
  Future<void> _save(Map<String, dynamic> p, {String? voice}) async {
    if (VocalStore.debug) return;
    await store.app.api!.vocalProject({
      'id': crS(p['id']),
      'title': crS(p['title']),
      'voice': voice ?? crS(p['voice']),
      'lang': crS(p['lang']).isEmpty ? 'en' : crS(p['lang']),
      'chapters': [for (final ch in crList(p['chapters'])) {'title': crS(ch['title']), 'text': crS(ch['text'])}],
    });
    await store.load();
  }

  Future<void> _narrator(Map<String, dynamic> p) async {
    final id = await vocalPickVoice(context, store, widget.player, lang: crS(p['lang']), picked: crS(p['voice']));
    if (id == null || !mounted) return;
    try {
      await _save(p, voice: id);
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  Future<void> _read(Map<String, dynamic> p, int n) async {
    if (crS(p['voice']).isEmpty) {
      crToast(context, 'Choose who reads it first.');
      return;
    }
    setState(() => _busy = 'ch$n');
    try {
      if (!VocalStore.debug) {
        final r = await store.app.api!.vocalChapter(crS(p['id']), n);
        await store.load();
        final id = crS(r['id']);
        if (id.isNotEmpty && mounted) {
          unawaited(widget.player.toggle(context, id, () => store.app.api!.vocalAudio(id, format: 'mp3'), ext: 'mp3'));
        }
      }
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = '');
  }

  Future<void> _cast(Map<String, dynamic> p) async {
    setState(() => _busy = 'cast');
    try {
      if (!VocalStore.debug) {
        final r = await store.app.api!.vocalProjectCast(crS(p['id']), 0);
        if (mounted) setState(() => _characters = crList(r['characters']));
        await store.load();
      }
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = '');
  }

  Future<void> _export(Map<String, dynamic> p) async {
    const opts = {'One audiobook file, MP3': 'mp3', 'Audiobook with chapter marks, M4B': 'm4b', 'Studio quality, WAV': 'wav', 'Captions, SRT': 'srt'};
    final v = await crPick(context, 'Export', opts.keys.toList(), '');
    if (v == null || !mounted) return;
    final fmt = opts[v] ?? 'mp3';
    setState(() => _busy = 'export');
    try {
      if (!VocalStore.debug) {
        final r = await store.app.api!.vocalProjectExport(crS(p['id']), fmt);
        await store.load();
        final id = crS(r['id']);
        if (id.isNotEmpty && mounted) {
          final bytes = await store.app.api!.vocalAudio(id, format: fmt);
          if (bytes != null && mounted) await crShareBytes(context, bytes, '${crS(p['title'])}.$fmt', vocalMime(fmt == 'm4b' ? 'm4a' : fmt));
        }
      }
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = '');
  }

  Future<void> _remove(Map<String, dynamic> p) async {
    final ok = await vocalConfirm(context, 'Remove this reading?', 'Sounds already made stay in Your sounds.', 'Remove');
    if (ok != true) return;
    try {
      if (!VocalStore.debug) {
        await store.app.api!.vocalProjectDelete(crS(p['id']));
        await store.load();
      }
      if (mounted) setState(() => _open = '');
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  Widget _list(HoolaColors c) {
    final ps = _projects;
    return ListView(padding: const EdgeInsets.fromLTRB(16, 14, 16, 24), children: [
      Text('Long readings: a book, a document, a course. A chapter you change is read again only where its words changed.',
          style: HoolaType.small(c).copyWith(fontSize: 14, color: c.ink2)),
      const SizedBox(height: 12),
      VocalPill(label: 'New reading', glyph: CrGlyph.plus, busy: _busy == 'import', onTap: _new),
      const SizedBox(height: 16),
      VocalLabel('Your readings', note: ps.isEmpty ? '' : '${ps.length}'),
      if (ps.isEmpty)
        Text('None yet.', style: HoolaType.small(c))
      else
        for (final p in ps)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Semantics(
              button: true,
              label: crS(p['title']),
              excludeSemantics: true,
              onTap: () => setState(() => _open = crS(p['id'])),
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => setState(() => _open = crS(p['id'])),
                child: VocalBox(
                  child: Row(children: [
                    Container(
                      width: 40, height: 40,
                      decoration: BoxDecoration(color: c.accentSoft, borderRadius: BorderRadius.circular(10)),
                      child: Center(child: CrIcon(CrGlyph.book, size: 18, color: c.accent)),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(crS(p['title']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                        Text(_summary(p), style: HoolaType.small(c).copyWith(fontSize: 12)),
                      ]),
                    ),
                    CrIcon(CrGlyph.chevron, size: 14, color: c.ink3),
                  ]),
                ),
              ),
            ),
          ),
    ]);
  }

  String _summary(Map<String, dynamic> p) {
    final chs = crList(p['chapters']);
    final made = chs.where((x) => crS(x['audio']).isNotEmpty).length;
    return '${chs.length} chapter${chs.length == 1 ? '' : 's'} · $made made · ${store.langNative(crS(p['lang']))}';
  }

  Widget _one(HoolaColors c, Map<String, dynamic> p) {
    final chs = crList(p['chapters']);
    final left = chs.where((x) => crS(x['audio']).isEmpty).length;
    return Column(children: [
      Expanded(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 6, 16, 24), children: [
          Row(children: [
            VocalChip(label: 'All readings', onTap: () => setState(() => _open = '')),
            const Spacer(),
            VocalIconButton(label: 'Remove this reading', glyph: CrGlyph.trash, onTap: () => _remove(p)),
          ]),
          Text(crS(p['title']), style: HoolaType.heading(c)),
          Text(_summary(p), style: HoolaType.small(c).copyWith(fontSize: 12)),
          const SizedBox(height: 12),
          VocalRows([('Who reads it', vocalVoiceName(store, crS(p['voice'])), () => _narrator(p))]),
          const SizedBox(height: 14),
          const VocalLabel('Chapters'),
          for (var i = 0; i < chs.length; i++)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: VocalBox(
                padding: const EdgeInsets.fromLTRB(8, 4, 8, 4),
                child: Row(children: [
                  if (crS(chs[i]['audio']).isNotEmpty)
                    VocalPlayButton(
                      label: '${widget.player.playing(crS(chs[i]['audio'])) ? 'Pause' : 'Play'} ${crS(chs[i]['title'])}',
                      playing: widget.player.playing(crS(chs[i]['audio'])),
                      loading: widget.player.busy(crS(chs[i]['audio'])),
                      size: 40,
                      onTap: () {
                        final id = crS(chs[i]['audio']);
                        widget.player.toggle(context, id, () => store.app.api!.vocalAudio(id, format: 'mp3'), ext: 'mp3');
                      },
                    )
                  else
                    SizedBox(width: 48, height: 48, child: Center(child: Container(width: 10, height: 10,
                        decoration: BoxDecoration(color: c.lineStrong, shape: BoxShape.circle)))),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(crS(chs[i]['title']).isEmpty ? 'Chapter ${i + 1}' : crS(chs[i]['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                      Text(crS(chs[i]['audio']).isNotEmpty
                          ? 'Made${chs[i]['seconds'] is num ? ' · ${vocalClock(chs[i]['seconds'] as num)}' : ''}'
                          : 'Not made yet', style: HoolaType.small(c).copyWith(fontSize: 12, color: crS(chs[i]['audio']).isNotEmpty ? c.ok : c.ink3)),
                    ]),
                  ),
                  VocalChip(label: crS(chs[i]['audio']).isNotEmpty ? 'Make again' : 'Make', onTap: _busy.isNotEmpty ? null : () => _read(p, i)),
                  if (_busy == 'ch$i') const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                ]),
              ),
            ),
          const SizedBox(height: 12),
          const VocalLabel('Who reads whom'),
          if (_characters.isNotEmpty)
            VocalRows([for (final ch in _characters) (crS(ch['name']), vocalVoiceName(store, crS(ch['voice'])), null)]),
          if (_characters.isEmpty)
            Text('Hoola can find the characters in the text so quoted words go to their own voice.', style: HoolaType.small(c)),
          const SizedBox(height: 8),
          Align(alignment: Alignment.centerLeft, child: VocalChip(label: 'Find the characters', onTap: _busy.isNotEmpty ? null : () => _cast(p))),
        ]),
      ),
      VocalDock(
        note: left > 0 ? '$left chapter${left == 1 ? '' : 's'} not made yet · you can stop any time, nothing made is lost' : 'Every chapter is made',
        child: VocalPill(label: 'Export', busy: _busy == 'export', onTap: left > 0 || chs.isEmpty ? null : () => _export(p)),
      ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final body = ListenableBuilder(
      listenable: Listenable.merge([store, widget.player]),
      builder: (context, _) {
        final c = HoolaColors.of(context);
        final p = _project;
        return p.isEmpty ? _list(c) : _one(c, p);
      },
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Studio', body: body);
  }
}

// ================================================================================================ Dubbing
class VocalDubbingPage extends StatefulWidget {
  const VocalDubbingPage({super.key, required this.store, required this.player, this.conv = '', this.open = '', this.embedded = true,
      this.onCrumb});
  final VocalStore store;
  final VocalPlayer player;
  final String conv;
  /// A dub to open straight away (its id).
  final String open;
  final bool embedded;
  /// The open dub's name for the top bar ("Dubbing · Product video"), '' when the list shows.
  final ValueChanged<String>? onCrumb;
  @override
  State<VocalDubbingPage> createState() => _VocalDubbingPageState();
}

class _VocalDubbingPageState extends State<VocalDubbingPage> {
  List<Map<String, dynamic>> _dubs = [];
  Map<String, dynamic> _dub = const {};
  String _lang = '';
  Map<String, dynamic> _lines = const {};
  bool _loadingLines = false;
  final Set<int> _redoing = {};
  Timer? _poll;
  // a new dub
  VocalFile? _video;
  final List<String> _pick = [];
  String _mode = 'matched';
  bool _keep = true, _starting = false;
  Map<String, dynamic> _quote = const {};
  VocalStore get store => widget.store;

  @override
  void initState() {
    super.initState();
    _loadList();
    if (widget.open.isNotEmpty) WidgetsBinding.instance.addPostFrameCallback((_) => _openDub(widget.open));
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _loadList() async {
    try {
      final d = VocalStore.debug ? crList(VocalStore.debugData!['dubs']) : await store.app.api?.vocalDubs();
      if (d != null && mounted) setState(() => _dubs = d);
    } catch (_) {}
  }

  Future<void> _openDub(String id) async {
    try {
      Map<String, dynamic> d;
      if (VocalStore.debug) {
        d = crMap(crList(VocalStore.debugData!['dubs']).firstWhere((x) => crS(x['id']) == id, orElse: () => const {}));
      } else {
        d = await store.app.api!.vocalDub(id);
      }
      if (!mounted) return;
      final langs = crList(d['langs']);
      final ready = langs.where((l) => crS(l['status']) == 'ready').toList();
      setState(() {
        _dub = d;
        if (_lang.isEmpty || !langs.any((l) => crS(l['code']) == _lang)) {
          _lang = ready.isNotEmpty ? crS(ready.first['code']) : (langs.isEmpty ? '' : crS(langs.first['code']));
        }
      });
      widget.onCrumb?.call(crS(d['name']).isEmpty ? crS(d['title']) : crS(d['name']));
      if (_lines.isEmpty) unawaited(_loadLines());
      _poll?.cancel();
      if (crS(d['status']) == 'working') _poll = Timer(const Duration(seconds: 6), () => _openDub(id));
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  Future<void> _loadLines() async {
    final did = crS(_dub['id']);
    if (did.isEmpty || _lang.isEmpty) return;
    setState(() => _loadingLines = true);
    try {
      final r = VocalStore.debug ? crMap(VocalStore.debugData!['dub_lines']) : await store.app.api!.vocalDubLines(did, _lang);
      if (mounted) setState(() => _lines = r);
    } catch (e) {
      if (mounted) setState(() => _lines = {'lines': const [], 'editable': false, 'why': crError(e)});
    }
    if (mounted) setState(() => _loadingLines = false);
  }

  Map<String, dynamic>? get _langRow {
    for (final l in crList(_dub['langs'])) {
      if (crS(l['code']) == _lang) return l;
    }
    return null;
  }

  Future<void> _edit(Map<String, dynamic> ln) async {
    final n = crInt(ln['n']);
    final ctl = TextEditingController(text: crS(ln['dst']));
    final text = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Edit the line'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(crS(ln['src']), style: HoolaType.small(HoolaColors.of(ctx))),
          const SizedBox(height: 8),
          TextField(controller: ctl, autofocus: true, minLines: 2, maxLines: 5),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(ctl.text.trim()), child: const Text('Save')),
        ],
      ),
    );
    ctl.dispose();
    if (text == null || text.isEmpty || !mounted) return;
    try {
      if (!VocalStore.debug) await store.app.api!.vocalDubLineSave(crS(_dub['id']), n, _lang, text);
      final ls = crList(_lines['lines']).map((x) => crInt(x['n']) == n ? {...x, 'dst': text} : x).toList();
      setState(() => _lines = {..._lines, 'lines': ls});
      if (mounted) crToast(context, 'Saved. Tap Redo to hear the line said again.');
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  Future<void> _redo(Map<String, dynamic> ln) async {
    final n = crInt(ln['n']);
    setState(() => _redoing.add(n));
    try {
      if (!VocalStore.debug) {
        await store.app.api!.vocalDubLineRedo(crS(_dub['id']), n, _lang);
        await _openDub(crS(_dub['id']));
        await _loadLines();
      }
      if (mounted) crToast(context, 'The line was said again.');
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _redoing.remove(n));
  }

  Future<void> _download() async {
    final l = _langRow;
    final vid = crS(l?['video_id']);
    const opts = ['Video with the dub', 'Sound only, MP3', 'Subtitles, SRT', 'Subtitles, VTT'];
    final v = await crPick(context, 'Download', opts, '');
    if (v == null || !mounted || VocalStore.debug) return;
    final api = store.app.api;
    if (api == null) return;
    final name = '${crS(_dub['name']).isEmpty ? 'Dub' : crS(_dub['name'])} ${crS(l?['name'])}'.trim();
    crToast(context, 'Getting the file…');
    try {
      List<int>? bytes;
      var ext = 'mp4';
      if (v == opts[0] || v == opts[1]) {
        if (vid.isEmpty) throw Exception('This language is not made yet.');
        ext = v == opts[0] ? 'mp4' : 'mp3';
        bytes = await api.vocalAudio(vid, format: ext == 'mp4' ? '' : 'mp3');
      } else {
        ext = v == opts[2] ? 'srt' : 'vtt';
        bytes = await api.vocalDubSubtitles(crS(_dub['id']), _lang, ext);
      }
      if (bytes == null) throw Exception('This file is not on Hoola.');
      if (mounted) await crShareBytes(context, bytes, '$name.$ext', vocalMime(ext));
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  List<Map<String, dynamic>> get _dubLangs => store.langs.where((l) => crS(l['speech']) != 'none').toList();

  Future<String?> _chooseLang() async {
    final v = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => CrHueScope(hue: CrHue.voice, child: VocalLanguageSheet(store: store, current: '')),
    );
    return v == null || v == 'auto' ? null : v;
  }

  Future<void> _addLang() async {
    final v = await _chooseLang();
    if (v == null || !mounted) return;
    try {
      if (!VocalStore.debug) {
        final made = await store.app.api!.vocalDubAddLangs(crS(_dub['id']), [v]);
        // the server makes a NEW dub of the same video for the added language, with the same voices
        await _openDub(crS(made['id']).isNotEmpty ? crS(made['id']) : crS(_dub['id']));
      }
      if (mounted) crToast(context, '${store.langName(v)} is being made.');
    } catch (e) {
      if (mounted) {
        crToast(context, RegExp('not found|not allowed|404|405').hasMatch(crError(e).toLowerCase())
            ? 'Adding a language to a finished dub is not on this server yet. Start a new dub with the same video.'
            : crError(e));
      }
    }
  }

  Future<void> _requote() async {
    if (VocalStore.debug) {
      setState(() => _quote = crMap(VocalStore.debugData!['quote']));
      return;
    }
    try {
      final q = await store.app.api?.vocalQuote({
        'job': _mode == 'own' ? 'dub_own' : 'dub_matched',
        'seconds': (_video?.seconds ?? 0) > 0 ? _video!.seconds : 60,
        'langs': _pick.isEmpty ? 1 : _pick.length,
      });
      if (q != null && mounted) setState(() => _quote = q);
    } catch (_) {}
  }

  Future<void> _start() async {
    final v = _video;
    if (v == null || _pick.isEmpty) return;
    setState(() => _starting = true);
    try {
      Map<String, dynamic> d;
      if (VocalStore.debug) {
        d = _dubs.isEmpty ? const {} : _dubs.first;
      } else {
        final fid = await vocalUpload(store, widget.conv, v);
        d = await store.app.api!.vocalDubStart({'file_id': fid, 'langs': _pick.take(_maxLangs).toList(), 'mode': _mode, 'keep_sound': _keep,
            'name': v.name});
      }
      if (!mounted) return;
      setState(() {
        _video = null;
        _pick.clear();
      });
      if (crS(d['id']).isNotEmpty) await _openDub(crS(d['id']));
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _starting = false);
  }

  // ---------------------------------------------------------------- the list + a new dub
  Widget _home(HoolaColors c) {
    final credits = vocalCredits(_quote);
    final popular = _dubLangs.take(12).toList();
    return Column(children: [
      Expanded(
        child: RefreshIndicator(
          onRefresh: _loadList,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 14, 16, 24), children: [
            Text('Your video spoken again in other languages, in matched voices or in the speakers’ own.',
                style: HoolaType.small(c).copyWith(fontSize: 14, color: c.ink2)),
            const SizedBox(height: 12),
            Semantics(
              button: true,
              label: _video == null ? 'Choose the video' : 'Chosen: ${_video!.name}. Choose another',
              excludeSemantics: true,
              onTap: _chooseVideo,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: _chooseVideo,
                child: VocalBox(
                  child: Row(children: [
                    Container(
                      width: 40, height: 40,
                      decoration: BoxDecoration(color: c.accentSoft, borderRadius: BorderRadius.circular(10)),
                      child: Center(child: CrIcon(CrGlyph.video, size: 18, color: c.accent)),
                    ),
                    const SizedBox(width: 12),
                    Expanded(child: Text(_video == null ? 'Choose the video' : _video!.name, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500))),
                    CrIcon(_video == null ? CrGlyph.plus : CrGlyph.check, size: 16, color: _video == null ? c.ink3 : c.ok),
                  ]),
                ),
              ),
            ),
            const SizedBox(height: 14),
            VocalLabel('Into', note: '${_pick.length} of $_maxLangs'),
            Wrap(spacing: 6, runSpacing: 0, children: [
              for (final l in popular)
                VocalChip(
                  label: crS(l['native']).isEmpty ? crS(l['name']) : crS(l['native']),
                  on: _pick.contains(crS(l['code'])),
                  onTap: () => _toggleLang(crS(l['code'])),
                ),
              for (final code in _pick.where((x) => !popular.any((l) => crS(l['code']) == x)))
                VocalChip(label: store.langNative(code), on: true, onTap: () => _toggleLang(code)),
              VocalChip(label: 'Another language', menu: true, onTap: () async {
                final v = await _chooseLang();
                if (v != null && !_pick.contains(v)) _toggleLang(v);
              }),
            ]),
            const SizedBox(height: 14),
            const VocalLabel('Voices'),
            VocalTabs(tabs: const ['Matched voices', 'Their own voices'], picked: _mode == 'own' ? 'Their own voices' : 'Matched voices',
                onPick: (v) {
                  setState(() {
                    _mode = v == 'Their own voices' ? 'own' : 'matched';
                    if (_pick.length > _maxLangs) _pick.removeRange(_maxLangs, _pick.length);
                  });
                  _requote();
                }),
            const SizedBox(height: 6),
            Text(_mode == 'own' ? 'Each speaker keeps their own voice (the premium engine). Up to 6 speakers.'
                : 'Hoola picks a close voice for each speaker. Videos up to 3 minutes.', style: HoolaType.small(c).copyWith(fontSize: 12)),
            const SizedBox(height: 10),
            CrSwitch(title: 'Keep the background sound', sub: 'Music and room sound stay under the new voices.', value: _keep,
                onChanged: (v) => setState(() => _keep = v)),
            if (_dubs.isNotEmpty) ...[
              const SizedBox(height: 18),
              VocalLabel('Your dubs', note: '${_dubs.length}'),
              for (final d in _dubs) _dubRow(c, d),
            ],
          ]),
        ),
      ),
      VocalDock(
        note: 'Nothing is spent until you tap',
        child: VocalPill(label: credits.isEmpty ? 'Dub it' : 'Dub it · $credits', busy: _starting,
            onTap: _video == null || _pick.isEmpty ? null : _start),
      ),
    ]);
  }

  Future<void> _chooseVideo() async {
    final f = await vocalPickFile(context, video: true, maxMb: 200);
    if (f != null && mounted) {
      setState(() => _video = f);
      _requote();
    }
  }

  /// How many languages one dub takes (the server's limits: matched voices 4, their own voices 6).
  int get _maxLangs {
    final l = crMap(store.ov['limits']);
    final n = crInt(_mode == 'own' ? l['dub_langs_own'] : l['dub_langs_matched']);
    return n > 0 ? n : (_mode == 'own' ? 6 : 4);
  }

  void _toggleLang(String code) {
    setState(() {
      if (_pick.contains(code)) {
        _pick.remove(code);
      } else if (_pick.length < _maxLangs) {
        _pick.add(code);
      } else {
        crToast(context, 'Up to $_maxLangs languages in one dub with ${_mode == 'own' ? 'their own voices' : 'matched voices'}.');
      }
    });
    _requote();
  }

  Widget _dubRow(HoolaColors c, Map<String, dynamic> d) {
    final st = crS(d['status']);
    final langs = crList(d['langs']).map((l) => crS(l['name']).isEmpty ? store.langName(crS(l['code'])) : crS(l['name'])).join(', ');
    final name = crS(d['name']).isEmpty ? (crS(d['title']).isEmpty ? 'A dub' : crS(d['title'])) : crS(d['name']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Semantics(
        button: true,
        label: '$name, $langs',
        excludeSemantics: true,
        onTap: () => _openDub(crS(d['id'])),
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () => _openDub(crS(d['id'])),
          child: VocalBox(
            fill: st == 'failed' ? c.badSoft : null,
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                  Text(st == 'failed'
                      ? '${crS(d['error']).isEmpty ? 'Could not be made' : crS(d['error'])} · nothing was charged'
                      : st == 'working' ? 'Being made · $langs' : langs,
                      maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12, color: st == 'failed' ? c.bad : c.ink3)),
                ]),
              ),
              CrIcon(CrGlyph.chevron, size: 14, color: c.ink3),
            ]),
          ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------- one dub: the editor
  Widget _editor(HoolaColors c) {
    final langs = crList(_dub['langs']);
    final l = _langRow;
    final vid = crS(l?['video_id']);
    final ctl = widget.player.controllerFor(vid);
    final lines = crList(_lines['lines']);
    final editable = _lines['editable'] != false;
    final working = crS(_dub['status']) == 'working' || crS(l?['status']) == 'working' || crS(l?['status']) == 'waiting';
    final first = lines.isEmpty ? '' : crS(lines.first['dst']);
    return Column(children: [
      AspectRatio(
        aspectRatio: 16 / 9,
        child: Container(
          color: c.dark ? c.sunk : c.ink,
          child: Stack(alignment: Alignment.center, children: [
            if (ctl != null && ctl.value.isInitialized)
              Center(child: AspectRatio(aspectRatio: ctl.value.aspectRatio, child: VideoPlayer(ctl))),
            if (vid.isNotEmpty)
              Semantics(
                button: true,
                label: '${widget.player.playing(vid) ? 'Pause' : 'Play'} the ${crS(l?['name'])} video',
                excludeSemantics: true,
                onTap: () => widget.player.toggle(context, vid, () => store.app.api!.vocalAudio(vid), ext: 'mp4'),
                child: GestureDetector(
                  onTap: () => widget.player.toggle(context, vid, () => store.app.api!.vocalAudio(vid), ext: 'mp4'),
                  child: Opacity(
                    opacity: widget.player.playing(vid) ? 0.0 : 1.0,
                    child: Container(
                      width: 52, height: 52,
                      decoration: BoxDecoration(color: c.surface, shape: BoxShape.circle),
                      child: Center(child: widget.player.busy(vid)
                          ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink))
                          : CrIcon(CrGlyph.play, size: 18, color: c.ink)),
                    ),
                  ),
                ),
              )
            else
              Text(working ? 'Being made…' : 'Not made', style: HoolaType.body(c).copyWith(color: c.dark ? c.ink2 : c.bg)),
            if (first.isNotEmpty && !widget.player.playing(vid))
              Positioned(
                left: 12, right: 12, bottom: 10,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(color: c.scrim, borderRadius: BorderRadius.circular(6)),
                  child: Text(first, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: HoolaType.body(c).copyWith(fontSize: 13, color: c.dark ? c.ink : c.bg)),
                ),
              ),
          ]),
        ),
      ),
      SizedBox(
        height: 60,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.fromLTRB(16, 6, 16, 6), children: [
          for (final x in langs)
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: VocalChip(
                label: '${crS(x['name']).isEmpty ? store.langName(crS(x['code'])) : crS(x['name'])}'
                    '${crS(x['status']) == 'ready' ? '' : crS(x['status']) == 'failed' ? ' · not made' : ' · being made'}',
                on: crS(x['code']) == _lang,
                onTap: () {
                  setState(() {
                    _lang = crS(x['code']);
                    _lines = const {};
                  });
                  _loadLines();
                },
              ),
            ),
          VocalChip(label: 'Add a language', menu: true, onTap: _addLang),
        ]),
      ),
      Expanded(
        child: _loadingLines && lines.isEmpty
            ? const Center(child: CircularProgressIndicator(strokeWidth: 2))
            : ListView(padding: const EdgeInsets.fromLTRB(16, 0, 16, 16), children: [
                if (crS(_dub['status']) == 'failed')
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: CrNote('${crS(_dub['error']).isEmpty ? 'This dub could not be made.' : crS(_dub['error'])} Nothing was charged.',
                        glyph: CrGlyph.info),
                  ),
                if (!editable)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: CrNote(crS(_lines['why']).isNotEmpty ? crS(_lines['why'])
                        : 'These lines were made in the speakers’ own voices, so they cannot be changed one by one here.', glyph: CrGlyph.info),
                  ),
                if (lines.isEmpty && !_loadingLines)
                  Text(working ? 'The lines show here when this language is made.' : 'No lines for this language.', style: HoolaType.small(c)),
                for (final ln in lines) _lineRow(c, ln, editable),
                if (lines.isNotEmpty && editable)
                  Text('Edit any line, then redo only that line · 1 credit a line', style: HoolaType.small(c).copyWith(fontSize: 12)),
              ]),
      ),
      VocalDock(
        child: Row(children: [
          Expanded(child: VocalPill(label: 'Download', quiet: true, onTap: vid.isEmpty && lines.isEmpty ? null : _download)),
          const SizedBox(width: 10),
          Expanded(child: VocalPill(label: 'Add a language', onTap: _addLang)),
        ]),
      ),
    ]);
  }

  Widget _lineRow(HoolaColors c, Map<String, dynamic> ln, bool editable) {
    final n = crInt(ln['n']);
    final long = ln['too_long'] == true;
    final at = ln['start'] is num ? vocalClock(ln['start'] as num) : '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: VocalBox(
        padding: const EdgeInsets.fromLTRB(12, 2, 4, 10),
        edge: long ? c.warn : null,
        fill: long ? c.warnSoft : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            if (at.isNotEmpty) Text(at, style: HoolaType.small(c).copyWith(fontSize: 12, fontFeatures: const [FontFeature.tabularFigures()])),
            if (at.isNotEmpty) const SizedBox(width: 8),
            Expanded(child: Text('${crS(ln['speaker'])}${ln['edited'] == true ? ' · edited' : ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: HoolaType.small(c).copyWith(fontSize: 12, fontWeight: FontWeight.w500, color: c.accent))),
            if (editable) VocalIconButton(label: 'Edit the line at ${at.isEmpty ? '$n' : at}', glyph: CrGlyph.pen, onTap: () => _edit(ln)),
            if (editable)
              _redoing.contains(n)
                  ? const SizedBox(width: 48, height: 48, child: Center(child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))))
                  : VocalChip(label: 'Redo', onTap: () => _redo(ln)),
          ]),
          Text(crS(ln['src']), style: HoolaType.small(c).copyWith(fontSize: 12, color: c.ink2)),
          const SizedBox(height: 2),
          Text(crS(ln['dst']), style: HoolaType.body(c).copyWith(height: 1.45)),
          if (long) ...[
            const SizedBox(height: 4),
            Text('Longer than the original. Shorten it, or it is read a little faster.',
                style: HoolaType.small(c).copyWith(fontSize: 12, color: c.warn)),
          ],
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final body = ListenableBuilder(
      listenable: Listenable.merge([store, widget.player]),
      builder: (context, _) {
        final c = HoolaColors.of(context);
        // the frame's Back (or the phone's) closes an open dub: the frame builds this page again with a new key
        return _dub.isEmpty ? _home(c) : _editor(c);
      },
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Dubbing', body: body);
  }
}
