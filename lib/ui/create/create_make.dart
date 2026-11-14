// v0.912 CREATE NATIVE: the six "make" screens of claude.ai/artifact/SARfWkfWm8ZtmmnAcU8dYn - Image (2), Music (5),
// Voice-over (6), Dubbing (7), Script writer (9) and AI casting (10). Each one is the console Create studio's own tool
// on the phone: the same choices, the same /api/create/jobs and /api/create/write calls, the same rules (the price
// on the button, references and videos are her own files, the result also lands in her chat). A running job shows
// its step and a moving bar; a failed one says why and can be dismissed; what is made sits right under the tool.
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import '../../native.dart';
import '../attach.dart';
import '../hoola_theme.dart';
import 'create_film.dart' show CreateDirector;
import 'create_keep.dart' show crOpenItem;
import 'create_kit.dart';

// ------------------------------------------------------------------------------------------------ shared
/// The results under a tool: running jobs, failed ones, then what is on her shelf of [kind].
List<Widget> crResults(BuildContext context, CreateStore store, String kind, String empty, Widget Function(Map<String, dynamic>) item) {
  final run = store.running(kind), bad = store.failed(kind), kept = store.shelf(kind);
  return [
    for (final j in run) ...[CrJobRow(job: j, store: store), const SizedBox(height: 10)],
    for (final j in bad) ...[CrJobRow(job: j, store: store), const SizedBox(height: 10)],
    if (run.isEmpty && bad.isEmpty && kept.isEmpty) CrNote(empty, glyph: CrGlyph.info),
    for (final it in kept.take(24)) ...[item(it), const SizedBox(height: 10)],
  ];
}

/// Picks her own file and uploads it to the open chat (that is where Create reads references and videos from).
Future<({String id, String name, List<int> bytes})?> crUpload(BuildContext context, CreateStore store, FileType type) async {
  final picked = await pickAttachmentsOfType(context, type);
  if (picked.isEmpty) return null;
  final f = picked.first;
  try {
    final r = await store.app.attachChatFile(f.name, f.bytes);
    return (id: crS(r['file_id']), name: f.name, bytes: f.bytes);
  } catch (e) {
    if (context.mounted) crToast(context, crError(e));
    return null;
  }
}

Future<void> _start(BuildContext context, CreateStore store, Map<String, dynamic> body, String said) async {
  try {
    await store.start(body);
    if (context.mounted) crToast(context, said);
  } catch (e) {
    if (context.mounted) crToast(context, crError(e));
  }
}

// ------------------------------------------------------------------------------------------------ 2 · Image
const _imgStyles = ['Auto', 'Photoreal', 'Cinematic', 'Festive glow', 'Product studio', 'Watercolour', 'Anime', '3D clay', 'Indian folk art'];
const _imgShapes = ['1:1', '4:5', '9:16', '16:9', '3:4', '4:3'];

class CreateImage extends StatefulWidget {
  const CreateImage({super.key, required this.store, this.prompt = ''});
  final CreateStore store;
  final String prompt;
  @override
  State<CreateImage> createState() => _CreateImageState();
}

class _CreateImageState extends State<CreateImage> {
  late final _q = TextEditingController(text: widget.prompt);
  final _avoid = TextEditingController();
  String _mode = 'New picture', _style = 'Auto', _shape = '1:1', _quality = 'fast';
  int _count = 1;
  bool _brand = false, _more = false, _enhancing = false, _busy = false, _uploading = false;
  final List<({String id, String name, List<int> bytes})> _refs = [];

  @override
  void dispose() {
    _q.dispose();
    _avoid.dispose();
    super.dispose();
  }

  int get _each => _quality == 'best' ? 12 : 3;

  Future<void> _enhance() async {
    final api = widget.store.app.api;
    if (api == null || _q.text.trim().isEmpty) {
      crToast(context, 'Write a few words first, then Enhance makes them richer.');
      return;
    }
    setState(() => _enhancing = true);
    try {
      final r = crMap(await api.call('POST', '/api/studio/improve',
          body: {'brief': _q.text.trim(), 'language': 'Hindi', 'seconds': 30, 'kind': 'image'}, timeout: const Duration(seconds: 90)));
      if (crS(r['brief']).isNotEmpty) _q.text = crS(r['brief']);
      if (mounted) crToast(context, 'Prompt enhanced: change anything, then create.');
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _enhancing = false);
  }

  Future<void> _addRef() async {
    if (_refs.length >= 3) return;
    setState(() => _uploading = true);
    final r = await crUpload(context, widget.store, FileType.image);
    if (!mounted) return;
    setState(() {
      _uploading = false;
      if (r != null) _refs.add(r);
    });
  }

  Future<void> _create() async {
    var prompt = _q.text.trim();
    if (prompt.isEmpty) {
      crToast(context, 'Describe the picture first.');
      return;
    }
    if (_mode == 'Change my photo' && _refs.isEmpty) {
      crToast(context, 'Add the photo you want changed first.');
      return;
    }
    if (_brand) {
      final cols = crMap(widget.store.kit['colors']);
      if (cols.isNotEmpty) prompt += '\nUse my brand colours: ${cols.entries.map((e) => '${e.key} ${e.value}').join(', ')}.';
      final name = crS(widget.store.kit['name']);
      if (name.isNotEmpty) prompt += ' The brand is $name.';
    }
    if (_avoid.text.trim().isNotEmpty) prompt += '\nKeep out of the picture: ${_avoid.text.trim()}.';
    setState(() => _busy = true);
    await _start(context, widget.store, {
      'kind': 'image',
      'prompt': prompt,
      'file_ids': _refs.map((r) => r.id).toList(),
      'aspect': _shape,
      'quality': _quality,
      'count': _count,
      'style': _style == 'Auto' ? '' : _style,
      'title': _q.text.trim().length > 48 ? _q.text.trim().substring(0, 48) : _q.text.trim(),
    }, _count == 1 ? 'Painting your picture. It also arrives in your chat.' : 'Painting $_count pictures. They also arrive in your chat.');
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final store = widget.store;
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) => CrPage(
        title: 'Image',
        onRefresh: () => store.load(quiet: true),
        action: Row(children: [
          SizedBox(
            width: 148,
            child: CrStepper(
              value: '$_count',
              sub: _count == 1 ? 'picture' : 'pictures',
              height: 56,
              label: 'pictures',
              onLess: _count > 1 ? () => setState(() => _count--) : null,
              onMore: _count < 4 ? () => setState(() => _count++) : null,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(child: CrMain(label: 'Create · about ${crRupees(_each * _count)}', busy: _busy, onTap: _create)),
        ]),
        children: [
          CrSegment(options: const ['New picture', 'Change my photo'], picked: _mode, onPick: (v) => setState(() => _mode = v)),
          const SizedBox(height: 14),
          CrTextCard(
            title: _mode == 'New picture' ? 'Describe the picture' : 'What should change in your photo',
            controller: _q,
            hint: _mode == 'New picture'
                ? 'A festive poster of a clay kulhad of chai, steam rising, diyas, a headline in Hindi…'
                : 'Put me in front of a Diwali-lit shop, keep my face the same…',
            action: CrSmall(label: 'Enhance', busy: _enhancing, onTap: _enhance),
            footer: Align(
              alignment: Alignment.centerLeft,
              child: _refs.length >= 3
                  ? Text('3 references added', style: HoolaType.small(c).copyWith(fontSize: 12.5))
                  : CrSmall(label: _uploading ? 'Adding…' : (_mode == 'New picture' ? 'Add references' : 'Add your photo'),
                      glyph: CrGlyph.plus, busy: _uploading, onTap: _addRef),
            ),
          ),
          if (_refs.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final r in _refs)
                Stack(clipBehavior: Clip.none, children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(14),
                    child: Image.memory(Uint8List.fromList(r.bytes), width: 72, height: 72, fit: BoxFit.cover, cacheWidth: 216,
                        errorBuilder: (_, __, ___) => Container(width: 72, height: 72, color: c.sunk)),
                  ),
                  Positioned(
                    right: -17,
                    top: -17,
                    child: Semantics(
                      button: true,
                      label: 'Remove ${r.name}',
                      excludeSemantics: true,
                      onTap: () => setState(() => _refs.remove(r)),
                      child: GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: () => setState(() => _refs.remove(r)),
                        child: SizedBox(
                          width: 48,
                          height: 48,
                          child: Center(
                            child: Container(
                              width: 26,
                              height: 26,
                              decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle, border: Border.all(color: c.bg, width: 2)),
                              alignment: Alignment.center,
                              child: Text('×', style: TextStyle(color: c.onPill, fontSize: 14, height: 1)),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ]),
            ]),
          ],
          const SizedBox(height: 12),
          CrSwitch(
            title: 'Use my brand colours',
            sub: crS(store.kit['name']).isEmpty ? 'Set them once in Brand kit' : 'From ${crS(store.kit['name'])}’s brand kit',
            value: _brand,
            onChanged: (v) => setState(() => _brand = v),
          ),
          crGap,
          CrLabel('Style', note: _style == 'Auto' ? 'Hoola picks the look' : _style),
          CrTiles(options: _imgStyles, picked: _style, onPick: (v) => setState(() => _style = v)),
          crGap,
          const CrLabel('Shape'),
          _ShapeRow(options: _imgShapes, picked: _shape, onPick: (v) => setState(() => _shape = v)),
          crGap,
          const CrLabel('Quality'),
          Row(children: [
            Expanded(child: _QualityCard(on: _quality == 'fast', title: 'Standard', price: '₹3 a picture', sub: 'About 20 seconds',
                onTap: () => setState(() => _quality = 'fast'))),
            const SizedBox(width: 10),
            Expanded(child: _QualityCard(on: _quality == 'best', title: 'Best', price: '₹12 a picture', sub: 'Finer detail and text',
                onTap: () => setState(() => _quality = 'best'))),
          ]),
          const SizedBox(height: 12),
          CrCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            onTap: () => setState(() => _more = !_more),
            child: Column(children: [
              SizedBox(
                height: 48,
                child: Row(children: [
                  Expanded(child: Text('More settings', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500))),
                  AnimatedRotation(turns: _more ? .25 : 0, duration: HoolaMotion.of(context, HoolaMotion.menu),
                      child: CrIcon(CrGlyph.chevron, size: 16, color: c.ink3)),
                ]),
              ),
              if (_more)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: TextField(
                    controller: _avoid,
                    style: HoolaType.body(c),
                    decoration: InputDecoration(
                      labelText: 'Keep out of the picture',
                      hintText: 'Text, people, a logo…',
                      filled: true,
                      fillColor: c.sunk,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                    ),
                  ),
                ),
            ]),
          ),
          crGap,
          const CrLabel('Your pictures', note: 'Newest first'),
          _PictureGrid(store: store, kind: 'image'),
          const SizedBox(height: 12),
          const CrNote('Pictures made with AI are marked as AI. Only add photos you have the right to use.'),
        ],
      ),
    );
  }
}

class _ShapeRow extends StatelessWidget {
  const _ShapeRow({required this.options, required this.picked, required this.onPick});
  final List<String> options;
  final String picked;
  final ValueChanged<String> onPick;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Row(children: [
      for (var i = 0; i < options.length; i++) ...[
        if (i > 0) const SizedBox(width: 6),
        Expanded(
          child: Semantics(
            button: true,
            selected: options[i] == picked,
            label: 'Shape ${options[i]}',
            excludeSemantics: true,
            onTap: () => onPick(options[i]),
            child: GestureDetector(
              onTap: () {
                HapticFeedback.selectionClick();
                onPick(options[i]);
              },
              child: AnimatedContainer(
                duration: HoolaMotion.of(context, HoolaMotion.menu),
                height: 64,
                decoration: BoxDecoration(
                  color: options[i] == picked ? c.pill : c.surface,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: options[i] == picked ? c.pill : c.line),
                ),
                child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Builder(builder: (_) {
                    final p = options[i].split(':').map(double.parse).toList();
                    final k = 22 / (p[0] > p[1] ? p[0] : p[1]);
                    return Container(
                      width: p[0] * k,
                      height: p[1] * k,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(3),
                        border: Border.all(color: options[i] == picked ? c.onPill : c.ink2, width: 1.6),
                      ),
                    );
                  }),
                  const SizedBox(height: 6),
                  Text(options[i], style: HoolaType.label(c).copyWith(color: options[i] == picked ? c.onPill : c.ink2)),
                ]),
              ),
            ),
          ),
        ),
      ],
    ]);
  }
}

class _QualityCard extends StatelessWidget {
  const _QualityCard({required this.on, required this.title, required this.price, required this.sub, required this.onTap});
  final bool on;
  final String title, price, sub;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      selected: on,
      label: '$title, $price, $sub',
      excludeSemantics: true,
      onTap: onTap,
      child: CrCard(
        onTap: onTap,
        edge: on ? c.ink : null,
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: HoolaType.title(c).copyWith(fontSize: 15)),
              const SizedBox(height: 2),
              Text(price, style: HoolaType.body(c).copyWith(fontSize: 13.5)),
              Text(sub, style: HoolaType.small(c).copyWith(fontSize: 12)),
            ]),
          ),
          Container(
            width: 22,
            height: 22,
            decoration: BoxDecoration(
                color: on ? c.pill : null, shape: BoxShape.circle, border: on ? null : Border.all(color: c.lineStrong)),
            alignment: Alignment.center,
            child: on ? CrIcon(CrGlyph.check, size: 12, color: c.onPill) : null,
          ),
        ]),
      ),
    );
  }
}

/// Her pictures of [kind] as a two-column grid, with the running jobs as painting tiles first.
class _PictureGrid extends StatelessWidget {
  const _PictureGrid({required this.store, required this.kind, this.ratio = 1});
  final CreateStore store;
  final String kind;
  final double ratio;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final run = store.running(kind), bad = store.failed(kind), kept = store.shelf(kind);
    if (run.isEmpty && bad.isEmpty && kept.isEmpty) {
      return CrNote(kind == 'cast' ? 'Characters you cast appear here.' : 'Your pictures appear here, with a copy in your chat.',
          glyph: CrGlyph.info);
    }
    return Column(children: [
      for (final j in bad) ...[CrJobRow(job: j, store: store), const SizedBox(height: 10)],
      LayoutBuilder(builder: (context, box) {
        final w = (box.maxWidth - 10) / 2;
        return Wrap(spacing: 10, runSpacing: 10, children: [
          for (final j in run)
            SizedBox(
              width: w,
              child: AspectRatio(
                aspectRatio: ratio,
                child: Semantics(
                  label: 'Painting ${crS(j['title'])}',
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: Stack(fit: StackFit.expand, children: [
                      Container(color: c.sunk),
                      const _Sheen(),
                      Center(
                        child: Column(mainAxisSize: MainAxisSize.min, children: [
                          SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2)),
                          const SizedBox(height: 8),
                          Text(crS(j['step']).isEmpty ? 'Painting…' : 'Painting ${crS(j['step'])}',
                              style: HoolaType.small(c).copyWith(color: c.ink2)),
                        ]),
                      ),
                    ]),
                  ),
                ),
              ),
            ),
          for (final it in kept.take(30))
            SizedBox(
              width: w,
              child: Semantics(
                button: true,
                label: 'Open ${crS(it['title'])}',
                excludeSemantics: true,
                onTap: () => crOpenItem(context, store, it),
                child: GestureDetector(
                  onTap: () => crOpenItem(context, store, it),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    AspectRatio(
                      aspectRatio: ratio,
                      child: ClipRRect(borderRadius: BorderRadius.circular(16), child: CrItemImage(app: store.app, item: it)),
                    ),
                    const SizedBox(height: 6),
                    Text(crS(it['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: HoolaType.small(c).copyWith(color: c.ink, fontWeight: FontWeight.w500)),
                    Text('${crWhen(it['created'])}${crS(crMap(it['meta'])['quality']) == 'best' ? ' · Best' : ''}',
                        style: HoolaType.small(c).copyWith(fontSize: 12)),
                  ]),
                ),
              ),
            ),
        ]);
      }),
    ]);
  }
}

/// A soft light that slides across a tile while it paints (still under reduce motion).
class _Sheen extends StatefulWidget {
  const _Sheen();
  @override
  State<_Sheen> createState() => _SheenState();
}

class _SheenState extends State<_Sheen> with SingleTickerProviderStateMixin {
  late final AnimationController _a = AnimationController(vsync: this, duration: const Duration(milliseconds: 1600));
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (HoolaMotion.reduced(context)) {
      _a.stop();
    } else if (!_a.isAnimating) {
      _a.repeat();
    }
  }

  @override
  void dispose() {
    _a.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return AnimatedBuilder(
      animation: _a,
      builder: (_, __) => FractionalTranslation(
        translation: Offset(-1 + 2 * _a.value, 0),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [c.sunk.withOpacity(0), c.surface.withOpacity(.55), c.sunk.withOpacity(0)]),
          ),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ 5 · Music
const _genres = ['Bollywood romantic', 'Punjabi pop', 'Sufi', 'Indie pop', 'Lo-fi', 'Carnatic fusion', 'Garba', 'Ghazal', 'Hip-hop',
  'Devotional', 'Film score', 'Jingle'];
const _musicLangs = ['Hindi', 'Hinglish', 'Punjabi', 'Tamil', 'Telugu', 'Marathi', 'Bengali', 'English'];
const _vox = ['Duet', 'Female', 'Male', 'Choir'];
const _moods = ['Warm', 'Joyful', 'Romantic', 'Energetic', 'Sad', 'Devotional', 'Epic', 'Calm'];
const _lens = {'30 s': 30, '1 min': 60, '2 min': 120, '3 min': 180};

class CreateMusic extends StatefulWidget {
  const CreateMusic({super.key, required this.store, this.brief = ''});
  final CreateStore store;
  final String brief;
  @override
  State<CreateMusic> createState() => _CreateMusicState();
}

class _CreateMusicState extends State<CreateMusic> {
  late final _q = TextEditingController(text: widget.brief);
  final _lyrics = TextEditingController();
  String _kind = 'Song', _genre = 'Bollywood romantic', _lang = 'Hindi', _vx = 'Duet', _mood = 'Warm', _len = '2 min';
  double _bpm = 92;
  bool _writing = false, _busy = false;

  bool get _sung => _kind == 'Song';

  @override
  void dispose() {
    _q.dispose();
    _lyrics.dispose();
    super.dispose();
  }

  Future<void> _write() async {
    final idea = _q.text.trim();
    if (idea.length < 4) {
      crToast(context, 'Describe the song first, then Hoola writes its words.');
      return;
    }
    setState(() => _writing = true);
    try {
      final r = await widget.store.write({'kind': 'lyrics', 'brief': idea, 'genre': _genre, 'language': _lang, 'mood': _mood});
      _lyrics.text = crS(r['text']);
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _writing = false);
  }

  Future<void> _create() async {
    final brief = _q.text.trim();
    if (brief.isEmpty && _lyrics.text.trim().isEmpty) {
      crToast(context, 'Describe the ${_kind.toLowerCase()} first.');
      return;
    }
    final genre = _kind == 'Jingle' ? 'Jingle, $_genre' : _kind == 'Score' ? 'Film score, $_genre' : _genre;
    setState(() => _busy = true);
    await _start(context, widget.store, {
      'kind': 'song',
      'brief': brief,
      'genre': genre,
      'language': _lang,
      'vocals': _sung ? _vx.toLowerCase() : 'none',
      'mood': _mood,
      'bpm': _bpm.round(),
      'seconds': _lens[_len],
      'lyrics': _sung ? _lyrics.text.trim() : '',
      'title': (brief.isEmpty ? _genre : brief).length > 48 ? (brief.isEmpty ? _genre : brief).substring(0, 48) : (brief.isEmpty ? _genre : brief),
    }, 'Making your ${_kind.toLowerCase()}. It takes about a minute and also arrives in your chat.');
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final store = widget.store;
    final feel = _bpm < 90 ? 'relaxed' : _bpm < 130 ? 'lively' : 'fast and energetic';
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) => CrPage(
        title: 'Music',
        onRefresh: () => store.load(quiet: true),
        action: CrMain(label: 'Make the ${_kind.toLowerCase()} · about ₹7', busy: _busy, onTap: _create, glyph: CrGlyph.music),
        children: [
          CrSegment(options: const ['Song', 'Instrumental', 'Jingle', 'Score'], picked: _kind, onPick: (v) => setState(() => _kind = v)),
          const SizedBox(height: 14),
          CrTextCard(
            title: 'Describe the ${_kind.toLowerCase()}',
            controller: _q,
            max: 1200,
            lines: 3,
            hint: switch (_kind) {
              'Song' => 'A warm Hindi duet about a chai shop where two strangers meet every rainy evening…',
              'Instrumental' => 'Calm sitar and tabla for a yoga class, no singing…',
              'Jingle' => 'A 30 second Diwali jingle for my sweet shop, bright and happy…',
              _ => 'Tense background score for a chase in a crowded market…',
            },
          ),
          crGap,
          CrLabel('Style', note: _genre),
          CrTiles(options: _genres, picked: _genre, onPick: (v) => setState(() => _genre = v), swatch: true),
          crGap,
          CrSettings([
            if (_sung) CrSetting('Language', _lang, _musicLangs, (v) => setState(() => _lang = v)),
            if (_sung) CrSetting('Singers', _vx, _vox, (v) => setState(() => _vx = v)),
            CrSetting('Mood', _mood, _moods, (v) => setState(() => _mood = v)),
            CrSetting('Length', _len, _lens.keys.toList(), (v) => setState(() => _len = v)),
          ]),
          crGap,
          CrLabel('Tempo', note: '${_bpm.round()} beats a minute · $feel'),
          Semantics(
            label: 'Tempo',
            value: '${_bpm.round()} beats a minute',
            child: Slider(
              value: _bpm,
              min: 60,
              max: 180,
              divisions: 30,
              label: '${_bpm.round()}',
              onChanged: (v) => setState(() => _bpm = v),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(children: [
              Text('60 slow', style: HoolaType.small(c).copyWith(fontSize: 12)),
              const Spacer(),
              Text('180 fast', style: HoolaType.small(c).copyWith(fontSize: 12)),
            ]),
          ),
          if (_sung) ...[
            crGap,
            CrTextCard(
              title: 'Lyrics',
              controller: _lyrics,
              max: 3000,
              lines: 5,
              serif: true,
              hint: 'Leave empty and the song gets its own words, or paste yours',
              action: CrSmall(label: 'Write with Hoola', glyph: CrGlyph.pen, busy: _writing, onTap: _write),
            ),
          ],
          crGap,
          const CrLabel('Your songs'),
          ...crResults(context, store, 'song', 'Your songs appear here, with a copy in your chat.', (it) {
            final m = crMap(it['meta']);
            return CrAudioCard(
                app: store.app,
                item: it,
                line: [m['genre'], m['language'], m['vocals'], m['mood']].map(crS).where((s) => s.isNotEmpty).join(' · '));
          }),
          const CrNote('Made by Google Lyria and marked as AI. Your own lyrics are sung word for word.', glyph: CrGlyph.info),
        ],
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ 6 · Voice-over
const _voiceLangs = ['Hindi', 'Hinglish', 'English', 'Marathi', 'Tamil', 'Telugu', 'Bengali', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi'];

class CreateVoice extends StatefulWidget {
  const CreateVoice({super.key, required this.store, this.text = ''});
  final CreateStore store;
  final String text;
  @override
  State<CreateVoice> createState() => _CreateVoiceState();
}

class _CreateVoiceState extends State<CreateVoice> {
  late final _q = TextEditingController(text: widget.text);
  String _lang = 'Hindi', _g = 'All', _voice = 'mine', _style = 'friendly';
  double _speed = 1;
  bool _busy = false;

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  List<(String, String, String)> _voices() {
    final vs = crMap(widget.store.conf['voices']);
    return [
      ('mine', 'Your ${widget.store.app.aName}’s voice', 'The voice from your calls'),
      if (_g != 'Male') for (final e in crMap(vs['female']).entries) (e.key, e.key, 'Female · ${e.value}'),
      if (_g != 'Female') for (final e in crMap(vs['male']).entries) (e.key, e.key, 'Male · ${e.value}'),
    ];
  }

  Future<void> _create() async {
    final t = _q.text.trim();
    if (t.isEmpty) {
      crToast(context, 'Write what should be said first.');
      return;
    }
    setState(() => _busy = true);
    final first = t.split(RegExp(r'[.!?\n]')).first.trim();
    await _start(context, widget.store, {
      'kind': 'voice',
      'text': t,
      'voice': _voice,
      'language': _lang,
      'style': _style,
      'speed': double.parse(_speed.toStringAsFixed(1)),
      'title': first.length > 48 ? first.substring(0, 48) : first,
    }, 'Making the voice-over. It also arrives in your chat.');
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final store = widget.store;
    final styles = store.conf['styles'] is List && (store.conf['styles'] as List).isNotEmpty
        ? (store.conf['styles'] as List).map((e) => '$e').toList()
        : const ['friendly', 'calm', 'excited', 'news', 'story', 'ad'];
    final words = _q.text.trim().isEmpty ? 0 : _q.text.trim().split(RegExp(r'\s+')).length;
    final secs = (words / 2.4 / _speed).round();
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) => CrPage(
        title: 'Voice-over',
        onRefresh: () => store.load(quiet: true),
        action: CrMain(label: 'Make the voice-over · a few paise', busy: _busy, onTap: _create, glyph: CrGlyph.voice),
        children: [
          CrTextCard(
            title: 'What should be said',
            controller: _q,
            max: 5000,
            lines: 5,
            serif: true,
            hint: 'Is Diwali, apne ghar ko roshan kijiye. Har shaam khaas.',
          ),
          crGap,
          CrLabel('Language', note: 'The voice reads it naturally'),
          CrChips(options: _voiceLangs, picked: _lang, onPick: (v) => setState(() => _lang = v)),
          crGap,
          Row(children: [
            Expanded(child: Semantics(header: true, child: Text('Voice', style: HoolaType.title(c).copyWith(fontSize: 14)))),
            SizedBox(width: 210, child: CrSegment(options: const ['All', 'Female', 'Male'], picked: _g, height: 40,
                onPick: (v) => setState(() => _g = v))),
          ]),
          const SizedBox(height: 10),
          CrCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(children: [
              for (final (i, v) in _voices().indexed) ...[
                if (i > 0) Divider(height: 1, color: c.line),
                Semantics(
                  button: true,
                  selected: v.$1 == _voice,
                  label: '${v.$2}. ${v.$3}',
                  excludeSemantics: true,
                  onTap: () => setState(() => _voice = v.$1),
                  child: InkWell(
                    onTap: () {
                      HapticFeedback.selectionClick();
                      setState(() => _voice = v.$1);
                    },
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      child: Row(children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(color: v.$1 == 'mine' ? c.pill : crTone(c, v.$1), shape: BoxShape.circle),
                          alignment: Alignment.center,
                          child: v.$1 == 'mine'
                              ? CrIcon(CrGlyph.voice, size: 18, color: c.onPill)
                              : Text(v.$2.isEmpty ? '?' : v.$2.substring(0, 1), style: HoolaType.title(c).copyWith(fontSize: 15)),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(v.$2, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                            Text(v.$3, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12.5)),
                          ]),
                        ),
                        Container(
                          width: 24,
                          height: 24,
                          decoration: BoxDecoration(
                              color: v.$1 == _voice ? c.pill : null,
                              shape: BoxShape.circle,
                              border: v.$1 == _voice ? null : Border.all(color: c.lineStrong)),
                          alignment: Alignment.center,
                          child: v.$1 == _voice ? CrIcon(CrGlyph.check, size: 12, color: c.onPill) : null,
                        ),
                      ]),
                    ),
                  ),
                ),
              ],
            ]),
          ),
          crGap,
          const CrLabel('How it sounds'),
          CrTiles(
            options: [for (final s in styles) s[0].toUpperCase() + s.substring(1)],
            picked: _style[0].toUpperCase() + _style.substring(1),
            onPick: (v) => setState(() => _style = v.toLowerCase()),
          ),
          crGap,
          CrLabel('Pace', note: _speed < 1 ? 'Slower, easy to follow' : _speed > 1 ? 'Quicker, for short ads' : 'Natural speaking pace'),
          CrStepper(
            value: '${_speed.toStringAsFixed(1)}×',
            sub: secs > 0 ? 'about $secs seconds' : '',
            label: 'pace',
            onLess: _speed > .65 ? () => setState(() => _speed = (_speed - .1).clamp(.6, 1.6)) : null,
            onMore: _speed < 1.55 ? () => setState(() => _speed = (_speed + .1).clamp(.6, 1.6)) : null,
          ),
          crGap,
          const CrLabel('Made'),
          ...crResults(context, store, 'voice', 'Your voice-overs appear here, with a copy in your chat.', (it) {
            final m = crMap(it['meta']);
            return CrAudioCard(
                app: store.app,
                item: it,
                line: [m['language'], m['voice'] == 'mine' ? 'your Hoola’s voice' : m['voice'], m['style']]
                    .map(crS)
                    .where((s) => s.isNotEmpty)
                    .join(' · '));
          }),
        ],
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ 7 · Dubbing
const _dubTop = ['Hindi', 'Tamil', 'Telugu', 'Bengali', 'Marathi', 'English'];
const _dubAll = ['Hindi', 'Hinglish', 'English', 'Marathi', 'Tamil', 'Telugu', 'Bengali', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi', 'Odia'];

class CreateDub extends StatefulWidget {
  const CreateDub({super.key, required this.store});
  final CreateStore store;
  @override
  State<CreateDub> createState() => _CreateDubState();
}

class _CreateDubState extends State<CreateDub> {
  ({String id, String name, List<int> bytes})? _src;
  final Set<String> _to = {'Tamil'};
  bool _keep = true, _busy = false, _uploading = false;

  Future<void> _pick() async {
    setState(() => _uploading = true);
    final r = await crUpload(context, widget.store, FileType.video);
    if (!mounted) return;
    setState(() {
      _uploading = false;
      if (r != null) _src = r;
    });
  }

  void _flip(String l) {
    setState(() {
      if (_to.contains(l)) {
        _to.remove(l);
      } else if (_to.length < 4) {
        _to.add(l);
      } else {
        crToast(context, 'Up to 4 languages at a time.');
      }
    });
  }

  Future<void> _allLangs() async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, set) {
        final c = HoolaColors.of(ctx);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('All languages', style: HoolaType.heading(c)),
              const SizedBox(height: 4),
              Text('${_to.length} of 4 chosen', style: HoolaType.small(c)),
              const SizedBox(height: 14),
              CrChips(options: _dubAll, picked: '', multi: _to, onPick: (l) {
                _flip(l);
                set(() {});
              }),
              const SizedBox(height: 16),
              CrMain(label: 'Done', height: 52, onTap: () => Navigator.of(ctx).pop()),
            ]),
          ),
        );
      }),
    );
    if (mounted) setState(() {});
  }

  Future<void> _dub() async {
    final s = _src;
    if (s == null) {
      crToast(context, 'Add your video first.');
      return;
    }
    if (_to.isEmpty) {
      crToast(context, 'Pick at least one language.');
      return;
    }
    setState(() => _busy = true);
    final stem = s.name.replaceAll(RegExp(r'\.[^.]+$'), '');
    await _start(context, widget.store, {
      'kind': 'dub',
      'file_id': s.id,
      'languages': _to.toList(),
      'keep_sound': _keep,
      'title': '${stem.length > 40 ? stem.substring(0, 40) : stem} · ${_to.join(', ')}',
    }, 'Dubbing started. Each language comes back as its own video, also in your chat.');
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final store = widget.store;
    final s = _src;
    final extra = _to.where((l) => !_dubTop.contains(l)).toList();
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) => CrPage(
        title: 'Dubbing',
        onRefresh: () => store.load(quiet: true),
        action: CrMain(
          label: 'Dub into ${_to.length} ${_to.length == 1 ? 'language' : 'languages'}',
          busy: _busy,
          onTap: _dub,
          glyph: CrGlyph.dub,
        ),
        children: [
          const CrIntro('Your video, in more languages', 'Hoola listens, translates and speaks each line again in a matching voice.'),
          crGap,
          if (s == null)
            Semantics(
              button: true,
              label: 'Add your video',
              excludeSemantics: true,
              onTap: _uploading ? null : _pick,
              child: GestureDetector(
                onTap: _uploading ? null : _pick,
                child: Container(
                  height: 170,
                  decoration: BoxDecoration(
                    color: c.surface,
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(color: c.lineStrong, width: 1.4),
                  ),
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    if (_uploading)
                      SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2))
                    else
                      const CrDisc(CrGlyph.plus, size: 52),
                    const SizedBox(height: 12),
                    Text(_uploading ? 'Adding your video…' : 'Add your video', style: HoolaType.title(c).copyWith(fontSize: 15)),
                    const SizedBox(height: 2),
                    Text('MP4, MOV or WebM · up to 25 MB and 3 minutes', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
                  ]),
                ),
              ),
            )
          else
            CrCard(
              child: Row(children: [
                Container(
                  width: 56,
                  height: 72,
                  decoration: BoxDecoration(color: c.infoSoft, borderRadius: BorderRadius.circular(12)),
                  alignment: Alignment.center,
                  child: CrIcon(CrGlyph.video, size: 20, color: c.ink2),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(s.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                    Text('${(s.bytes.length / 1048576).toStringAsFixed(1)} MB · ready to dub', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
                  ]),
                ),
                CrQuiet(label: 'Change', height: 48, onTap: _uploading ? null : _pick),
              ]),
            ),
          crGap,
          CrLabel('Dub into', note: '${_to.length} of 4 chosen'),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final l in [..._dubTop, ...extra]) CrChip(label: l, on: _to.contains(l), onTap: () => _flip(l)),
            CrChip(label: 'All languages', on: false, glyph: CrGlyph.globe, onTap: _allLangs),
          ]),
          const SizedBox(height: 14),
          CrSwitch(
            title: 'Keep background sound',
            sub: 'Music and room noise stay, only the voice changes',
            value: _keep,
            onChanged: (v) => setState(() => _keep = v),
          ),
          crGap,
          const CrLabel('Your dubs'),
          ...crResults(context, store, 'dub', 'Dubbed videos appear here, with a copy in your chat.', (it) {
            final m = crMap(it['meta']);
            return CrCard(
              onTap: () => crOpenItem(context, store, it),
              child: Row(children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(color: c.sunk, shape: BoxShape.circle),
                  alignment: Alignment.center,
                  child: Text(crS(m['language']).isEmpty ? '?' : crS(m['language']).substring(0, 2).toLowerCase(),
                      style: HoolaType.title(c).copyWith(fontSize: 13)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(crS(m['language']).isEmpty ? crS(it['title']) : crS(m['language']),
                        style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                    Text('Ready · ${crS(it['title'])}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: HoolaType.small(c).copyWith(fontSize: 12.5)),
                  ]),
                ),
                CrRoundButton(glyph: CrGlyph.down, label: 'Save or share', onTap: () => crShareItem(context, store.app, it)),
              ]),
            );
          }),
          const CrNote('Voices are matched, not cloned, and lips are not re-synced. Only dub videos you have the right to use.',
              glyph: CrGlyph.info),
        ],
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ 9 · Script writer
const _formats = ['Ad film', 'Short film', 'Web episode', 'Music video', 'Reel', 'Explainer'];
const _fmtLine = {
  'Ad film': 'Short, with one clear offer at the end',
  'Short film': 'A small story with a beginning and an end',
  'Web episode': 'One episode with scenes and dialogue',
  'Music video': 'Shots written around a song',
  'Reel': 'Fast, 15 to 30 seconds, a hook first',
  'Explainer': 'Steps told simply, one idea a scene',
};

class CreateScript extends StatefulWidget {
  const CreateScript({super.key, required this.store, this.brief = ''});
  final CreateStore store;
  final String brief;
  @override
  State<CreateScript> createState() => _CreateScriptState();
}

class _CreateScriptState extends State<CreateScript> {
  late final _q = TextEditingController(text: widget.brief);
  final _doc = TextEditingController();
  String _fmt = 'Ad film', _len = '45 seconds', _lang = 'Hinglish', _tone = 'Warm', _id = '';
  bool _busy = false;
  Timer? _save;
  String _saved = '';

  @override
  void initState() {
    super.initState();
    _doc.addListener(_changed);
  }

  @override
  void dispose() {
    _save?.cancel();
    _q.dispose();
    _doc.dispose();
    super.dispose();
  }

  void _changed() {
    if (_id.isEmpty || _doc.text == _saved) return;
    _save?.cancel();
    _save = Timer(const Duration(milliseconds: 900), () async {
      final api = widget.store.app.api;
      if (api == null) return;
      try {
        await api.call('PUT', '/api/create/items/${Uri.encodeComponent(_id)}/text', body: {'text': _doc.text});
        _saved = _doc.text;
        if (mounted) setState(() {});
      } catch (e) {
        if (mounted) crToast(context, crError(e));
      }
    });
    setState(() {});
  }

  Future<void> _write([String change = '']) async {
    final brief = _q.text.trim();
    if (brief.length < 4) {
      crToast(context, 'Say what the script is about first.');
      return;
    }
    var ask = brief;
    if (change.isNotEmpty && _doc.text.trim().isNotEmpty) {
      ask = '$brief\n\nRewrite this script. Change: $change\n\n${_doc.text.trim()}';
      if (ask.length > 3000) ask = ask.substring(0, 3000);
    }
    setState(() => _busy = true);
    try {
      final r = await widget.store.write({
        'kind': 'script',
        'brief': ask,
        'format': _fmt,
        'length': _len,
        'language': _lang,
        'tone': _tone,
        'title': 'Script · ${brief.length > 40 ? brief.substring(0, 40) : brief}',
      });
      _id = crS(crMap(r['item'])['id']);
      _saved = crS(r['text']);
      _doc.text = _saved;
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _open(Map<String, dynamic> it) async {
    final bytes = await widget.store.app.api?.createItemBytes(crS(it['id']));
    if (bytes == null || !mounted) return;
    _id = crS(it['id']);
    _saved = utf8.decode(bytes, allowMalformed: true);
    _doc.text = _saved;
    setState(() {});
  }

  Future<void> _download() async {
    if (_doc.text.trim().isEmpty) return;
    try {
      final dir = await getTemporaryDirectory();
      final f = File('${dir.path}/hoola-script.txt');
      await f.writeAsString(_doc.text, flush: true);
      await Native.shareFile(f.path, mime: 'text/plain', title: 'Script');
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final store = widget.store;
    final has = _doc.text.trim().isNotEmpty;
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) => CrPage(
        title: 'Script writer',
        action: Row(children: [
          CrRoundButton(glyph: CrGlyph.down, label: 'Save or share the script', size: 56, onTap: has ? _download : null),
          const SizedBox(width: 10),
          Expanded(child: CrMain(label: has ? 'Write it again' : 'Write the script', busy: _busy, onTap: _write, glyph: CrGlyph.pen)),
        ]),
        children: [
          CrTextCard(title: 'What is it about?', controller: _q, max: 3000, lines: 3,
              hint: 'A Diwali ad for my sweet shop in Akola. A family visits, the son loves the kaju katli, end with 10% off.'),
          crGap,
          CrLabel('Format', note: _fmtLine[_fmt] ?? ''),
          CrTiles(options: _formats, picked: _fmt, onPick: (v) => setState(() => _fmt = v)),
          crGap,
          CrSettings([
            CrSetting('Length', _len, const ['15 seconds', '30 seconds', '45 seconds', '60 seconds', '2 minutes', '5 minutes', '10 minutes'],
                (v) => setState(() => _len = v)),
            CrSetting('Language', _lang, const ['Hinglish', 'Hindi', 'English', 'Marathi', 'Tamil', 'Telugu', 'Bengali', 'Gujarati'],
                (v) => setState(() => _lang = v)),
            CrSetting('Tone', _tone, const ['Warm', 'Funny', 'Emotional', 'Premium', 'Energetic', 'Serious'], (v) => setState(() => _tone = v)),
          ]),
          if (has || _busy) ...[
            crGap,
            Row(children: [
              Expanded(child: Semantics(header: true, child: Text('The script', style: HoolaType.title(c).copyWith(fontSize: 14)))),
              Text(_busy ? 'Writing…' : (_doc.text == _saved ? 'Saved' : 'Saving…'), style: HoolaType.small(c).copyWith(fontSize: 12.5)),
            ]),
            const SizedBox(height: 10),
            CrCard(
              padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
              child: _busy && !has
                  ? Padding(
                      padding: const EdgeInsets.symmetric(vertical: 20),
                      child: Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2))),
                    )
                  : TextField(
                      controller: _doc,
                      minLines: 8,
                      maxLines: null,
                      style: TextStyle(fontFamily: c.dark ? HoolaFont.serifDark : HoolaFont.serif, fontSize: 15, height: 1.6, color: c.ink),
                      decoration: const InputDecoration(border: InputBorder.none, filled: false, isDense: true, contentPadding: EdgeInsets.zero),
                    ),
            ),
            const SizedBox(height: 10),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final x in const ['Make it funnier', 'Shorter', 'In English', 'Add a song line'])
                CrChip(label: x, on: false, onTap: () => _write(x)),
            ]),
            const SizedBox(height: 14),
            CrCard(
              onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                  builder: (_) => HoolaTheme(
                      appearance: store.app.appearance,
                      child: CreateDirector(store: store, brief: _doc.text.length > 2000 ? _doc.text.substring(0, 2000) : _doc.text)))),
              child: Row(children: [
                const CrDisc(CrGlyph.film),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Turn it into a film', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                    Text('Director makes the storyboard from this script, free', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
                  ]),
                ),
                CrIcon(CrGlyph.chevron, size: 16, color: c.ink3),
              ]),
            ),
          ],
          if (store.shelf('script').isNotEmpty) ...[
            crGap,
            const CrLabel('Your scripts'),
            CrCard(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(children: [
                for (final (i, it) in store.shelf('script').take(12).indexed) ...[
                  if (i > 0) Divider(height: 1, color: c.line),
                  ListTile(
                    minVerticalPadding: 12,
                    leading: CrIcon(CrGlyph.pen, size: 18, color: c.ink2),
                    title: Text(crS(it['title']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c)),
                    subtitle: Text(crWhen(it['created']), style: HoolaType.small(c)),
                    selected: crS(it['id']) == _id,
                    onTap: () => _open(it),
                  ),
                ],
              ]),
            ),
          ],
        ],
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ 10 · AI casting
const _castStyles = ['Photoreal cinematic', 'Animated 3D', 'Anime', 'Illustrated'];

class CreateCasting extends StatefulWidget {
  const CreateCasting({super.key, required this.store});
  final CreateStore store;
  @override
  State<CreateCasting> createState() => _CreateCastingState();
}

class _CreateCastingState extends State<CreateCasting> {
  final _name = TextEditingController();
  final _desc = TextEditingController();
  String _style = 'Photoreal cinematic', _voice = 'Female voice';
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _desc.dispose();
    super.dispose();
  }

  Future<void> _cast() async {
    final name = _name.text.trim(), desc = _desc.text.trim();
    if (name.isEmpty || desc.isEmpty) {
      crToast(context, 'Give the character a name and say how they look.');
      return;
    }
    setState(() => _busy = true);
    await _start(context, widget.store, {
      'kind': 'cast',
      'name': name.length > 40 ? name.substring(0, 40) : name,
      'prompt': desc,
      'style': _style,
      'voice': _voice.startsWith('Female') ? 'female' : 'male',
      'quality': 'best',
    }, 'Casting $name: a four-view character sheet. It also arrives in your chat.');
    if (mounted) {
      setState(() => _busy = false);
      _name.clear();
      _desc.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final store = widget.store;
    InputDecoration field(String label, String hint) => InputDecoration(
          labelText: label,
          hintText: hint,
          filled: true,
          fillColor: c.surface,
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.line)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.ink)),
        );
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) => CrPage(
        title: 'AI casting',
        onRefresh: () => store.load(quiet: true),
        action: CrMain(label: 'Cast this character · about ₹12', busy: _busy, onTap: _cast, glyph: CrGlyph.cast),
        children: [
          const CrIntro('Make a character once, use them everywhere',
              'The same face in every picture and film. Characters are made up, never a real person.'),
          crGap,
          TextField(controller: _name, maxLength: 40, buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null,
              style: HoolaType.body(c), decoration: field('Name', 'Sharma ji')),
          const SizedBox(height: 10),
          TextField(
            controller: _desc,
            minLines: 2,
            maxLines: 5,
            maxLength: 600,
            buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null,
            style: HoolaType.body(c),
            decoration: field('Looks like', 'A kind shopkeeper in his fifties, grey moustache, white kurta, spectacles'),
          ),
          crGap,
          const CrLabel('Style'),
          CrTiles(options: _castStyles, picked: _style, onPick: (v) => setState(() => _style = v), cols: 2, swatch: true),
          crGap,
          const CrLabel('Voice', note: 'Used when they speak in a film'),
          CrSegment(options: const ['Female voice', 'Male voice'], picked: _voice, onPick: (v) => setState(() => _voice = v)),
          crGap,
          const CrLabel('Your cast', note: 'Four views, so the face stays the same'),
          _PictureGrid(store: store, kind: 'cast', ratio: 16 / 9),
        ],
      ),
    );
  }
}
