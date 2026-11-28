// v0.999.96 HOOLA VOCAL REDESIGN, PHONE (docs/HOOLA_VOCAL_REDESIGN.md sections 2-3 + 5, boards SoundTools, Settings):
// the Tools and the Assets pages.
//  - Voice changer: say it your way (recorded in the app, or a recording she has), it comes out in another voice with her
//    timing and feeling; her own cloned voice too when the server can (it says plainly when it cannot).
//  - Clean-up: Hoola listens first and picks the fixes; noise, a clearer voice, long pauses, loudness for where it is heard, the voice out
//    of music or street sounds; before and after with the readings, clean again from her kept recording.
//  - Sound effects: describe the sound (Improve the words), its length, how closely to follow the words, a smooth loop,
//    takes kept with a star; game sounds made on the server for free, heard without keeping, numbered versions.
//  - Dictionary: how a word is said (with its sounds in IPA, a language, a list imported at once).
//  - Settings: the engines (Hoola Auto picks one per job), what things cost in credits, her defaults, how long her sounds
//    are kept, keys and webhooks for her own apps (each key or signing secret shown once), the AI mark.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../api.dart' show ApiException;
import '../hoola_theme.dart';
import 'vocal_home.dart' show VocalLanguageSheet;
import 'vocal_kit.dart';
import 'vocal_make.dart' show vocalPickVoice, vocalVoiceName;

/// A recording to work on: recorded here, or a file she chose.
class _Source extends StatelessWidget {
  const _Source({required this.file, required this.onFile, required this.what, this.max = 300});
  final VocalFile? file;
  final ValueChanged<VocalFile> onFile;
  final String what;
  final int max;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return VocalBox(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        VocalRecorder(what: what, minSeconds: 1, maxSeconds: max, onDone: onFile),
        const SizedBox(height: 4),
        Semantics(
          button: true,
          label: file == null ? 'Or choose a recording' : 'Chosen: ${file!.name}. Choose another',
          excludeSemantics: true,
          onTap: () => _choose(context),
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => _choose(context),
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48),
              child: Row(children: [
                CrIcon(file == null ? CrGlyph.folder : CrGlyph.check, size: 16, color: file == null ? c.ink2 : c.ok),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(file == null ? 'Or choose a recording · up to ${max ~/ 60} minutes' : file!.name, maxLines: 1,
                      overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontSize: 14, color: c.ink2)),
                ),
              ]),
            ),
          ),
        ),
      ]),
    );
  }

  Future<void> _choose(BuildContext context) async {
    final f = await vocalPickFile(context);
    if (f != null) onFile(f);
  }
}

/// The made sound(s) under a tool, each with play and More.
// ================================================================================================ Voice changer
// v0.999.159 (design canvas claude.ai/artifact/HGbVJ4bghAiMFg9QyFCh2P): her recording, the voice, room noise, how close
// to the voice and how much of her feeling stays; Before / After on the result (her own recording is kept 30 days); her
// recent changes, each one changed again into another voice from the kept recording.
class VocalChangerPage extends StatefulWidget {
  const VocalChangerPage({super.key, required this.store, required this.player, this.conv = '', this.embedded = true});
  final VocalStore store;
  final VocalPlayer player;
  final String conv;
  final bool embedded;
  @override
  State<VocalChangerPage> createState() => _VocalChangerPageState();
}

class _VocalChangerPageState extends State<VocalChangerPage> {
  VocalFile? _file;
  String _voice = '', _hear = 'After';
  bool _denoise = true, _busy = false;
  double _close = 75, _feel = 50;
  Map<String, dynamic> _quote = const {};
  Map<String, dynamic>? _out;
  VocalStore get store => widget.store;

  @override
  void initState() {
    super.initState();
    _requote();
  }

  Future<void> _requote() async {
    if (VocalStore.debug) {
      setState(() => _quote = crMap(VocalStore.debugData!['quote']));
      return;
    }
    try {
      final q = await store.app.api?.vocalQuote({'job': 'change', 'seconds': (_file?.seconds ?? 0) > 0 ? _file!.seconds : 60, 'voice': _voice});
      if (q != null && mounted) setState(() => _quote = q);
    } catch (_) {}
  }

  Future<void> _pickVoice() async {
    final id = await vocalPickVoice(context, store, widget.player, picked: _voice);
    if (id != null && mounted) {
      setState(() => _voice = id);
      _requote();
    }
  }

  Map<String, dynamic> get _settings => {'denoise': _denoise, 'closeness': _close.round(), 'feel': _feel.round()};

  Future<void> _go() async {
    final f = _file;
    if (f == null || _voice.isEmpty) return;
    setState(() => _busy = true);
    try {
      List<Map<String, dynamic>> made;
      if (VocalStore.debug) {
        made = crList(VocalStore.debugData!['speech']).take(1).toList();
      } else {
        final fid = await vocalUpload(store, widget.conv, f);
        made = vocalMade(await store.app.api!.vocalChange({'file_id': fid, 'voice': _voice, ..._settings}));
        unawaited(store.load());
      }
      if (mounted && made.isNotEmpty) setState(() { _out = made.first; _hear = 'After'; });
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  /// Again into another voice, from her recording kept beside an earlier change; the price is asked first.
  Future<void> _another(Map<String, dynamic> h) async {
    final v = await vocalPickVoice(context, store, widget.player, picked: '');
    if (v == null || !mounted) return;
    final api = store.app.api;
    if (api == null) return;
    try {
      final q = await api.vocalQuote({'job': 'change', 'seconds': (h['src_secs'] ?? h['seconds'] ?? 60), 'voice': v});
      final cr = vocalCredits(q);
      if (!mounted) return;
      final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
        title: const Text('Change it into another voice?'),
        content: Text('“${crS(h['title'])}” in ${vocalVoiceName(store, v)}${cr.isEmpty ? '' : '. About $cr'}.'),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Not now')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Change it'))]));
      if (ok != true || !mounted) return;
      setState(() => _busy = true);
      final made = vocalMade(await api.vocalChange({'source_of': crS(h['id']), 'voices': [v], 'denoise': h['denoise'] != false,
        'closeness': _close.round(), 'feel': _feel.round()}));
      unawaited(store.load());
      if (mounted && made.isNotEmpty) setState(() { _out = made.first; _voice = v; _hear = 'After'; });
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _more(Map<String, dynamic> h) async {
    final pick = await vocalMore(context, crS(h['title']), [if (crS(h['src']).isNotEmpty) 'Into another voice', 'Download', 'Delete']);
    if (!mounted || pick == null) return;
    if (pick == 'Into another voice') return _another(h);
    if (pick == 'Download') return vocalShare(context, store.app, h, store: store);
    if (pick == 'Delete' && await vocalDeleteSound(context, store, h) && mounted && crS(_out?['id']) == crS(h['id'])) setState(() => _out = null);
  }

  Widget _slider(HoolaColors c, String label, String left, String right, double v, ValueChanged<double> on) =>
      Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        VocalLabel(label),
        Semantics(label: label, value: '${v.round()} percent', child: Slider(value: v, min: 0, max: 100, divisions: 20, activeColor: CrHue.voice.b, onChanged: on)),
        Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: Row(children: [
          Text(left, style: HoolaType.small(c).copyWith(color: c.ink3)), const Spacer(), Text(right, style: HoolaType.small(c).copyWith(color: c.ink3))])),
      ]);

  Widget _hearBox(BuildContext context, HoolaColors c, Map<String, dynamic> h) {
    final p = widget.player, before = _hear == 'Before', kept = crS(h['src']).isNotEmpty, id = crS(h['id']);
    final key = before ? 'chgsrc:$id' : id;
    return VocalBox(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      VocalTabs(tabs: const ['Before', 'After'], picked: _hear, onPick: (v) => setState(() => _hear = v)),
      const SizedBox(height: 12),
      Row(children: [
        VocalPlayButton(label: before ? 'Play your own recording' : 'Play the new voice', playing: p.playing(key), loading: p.busy(key),
            size: 48, onTap: () {
              if (before && !kept) return;
              p.toggle(context, key, () => before ? store.app.api!.vocalChangeSource(id) : store.app.api!.vocalAudio(id), ext: 'wav');
            }),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(before ? 'You' : crS(h['voice_name']).isEmpty ? 'The new voice' : crS(h['voice_name']), style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
          Text(before && !kept ? 'Your own recording is no longer kept.' : 'Same words, same timing.', style: HoolaType.small(c).copyWith(color: c.ink3)),
        ])),
      ]),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: VocalChip(label: 'Download', onTap: () => vocalShare(context, store.app, h, store: store))),
        const SizedBox(width: 8),
        if (kept) Expanded(child: VocalChip(label: 'Other voices', onTap: () => _another(h))),
      ]),
    ]));
  }

  @override
  Widget build(BuildContext context) {
    final body = ListenableBuilder(
      listenable: Listenable.merge([store, widget.player]),
      builder: (context, _) {
        final c = HoolaColors.of(context);
        final credits = vocalCredits(_quote);
        final out = _out == null ? null : store.history.firstWhere((x) => crS(x['id']) == crS(_out!['id']), orElse: () => _out!);
        final recent = store.history.where((x) => crS(x['kind']) == 'change' && crS(x['id']) != crS(out?['id'])).take(3).toList();
        return Column(children: [
          Expanded(
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 14, 16, 24), children: [
              Text('Say it your way. It comes back in another voice, with your timing and feeling.',
                  style: HoolaType.small(c).copyWith(fontSize: 14, color: c.ink2)),
              const SizedBox(height: 12),
              _Source(file: _file, what: 'change', onFile: (f) {
                setState(() { _file = f; _out = null; });
                _requote();
              }),
              const SizedBox(height: 12),
              VocalRows([('Into', _voice.isEmpty ? 'Choose a voice' : vocalVoiceName(store, _voice), _pickVoice)]),
              const SizedBox(height: 10),
              CrSwitch(title: 'Remove room noise first', sub: 'Fans, traffic, echo.', value: _denoise,
                  onChanged: (v) => setState(() => _denoise = v)),
              const SizedBox(height: 6),
              _slider(c, _voice.isEmpty ? 'How close to the voice' : 'How close to ${vocalVoiceName(store, _voice).split(' ').first}',
                  'More of you', 'All the voice', _close, (v) => setState(() => _close = v)),
              _slider(c, 'Keep my feeling', 'Even', 'Every rise and laugh', _feel, (v) => setState(() => _feel = v)),
              if (out != null) ...[
                const SizedBox(height: 16),
                const VocalLabel('Hear the difference'),
                _hearBox(context, c, out),
              ],
              if (recent.isNotEmpty) ...[
                const SizedBox(height: 16),
                const VocalLabel('Recent changes'),
                VocalBox(child: Column(children: [
                  for (var i = 0; i < recent.length; i++) ...[
                    if (i > 0) const SizedBox(height: 8),
                    VocalTakeRow(store: store, player: widget.player, item: recent[i], name: crS(recent[i]['title']).isEmpty ? 'Change' : crS(recent[i]['title']),
                        note: crS(recent[i]['voice_name']), onMore: () => _more(recent[i])),
                  ],
                ])),
              ],
              const SizedBox(height: 12),
              Text('Only the voice changes. Change only your own voice, or one you have the right to use. Your own recording is kept beside the change for 30 days.',
                  style: HoolaType.small(c).copyWith(color: c.ink3)),
            ]),
          ),
          VocalDock(
            note: 'Nothing is spent until you tap.',
            child: VocalPill(label: credits.isEmpty ? 'Change it' : 'Change it · $credits', busy: _busy,
                onTap: _file == null || _voice.isEmpty ? null : _go),
          ),
        ]);
      },
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Voice changer', body: body);
  }
}

// ================================================================================================ Clean-up
// v0.999.161: Hoola listens first (what it heard, measured on the server) and picks the fixes; a kind of recording sets
// them; how much noise, where it will be heard, how long a pause; Before / After from her kept recording, the readings
// before and after, Download and Clean again.
const _clKinds = <(String, String, Map<String, Object>)>[
  ('phone', 'Phone recording', {'denoise': true, 'noise': 'light', 'voice': true, 'level': true, 'target': 'reels', 'silence': false, 'people': false, 'music': false}),
  ('podcast', 'Podcast', {'denoise': true, 'noise': 'medium', 'voice': true, 'level': true, 'target': 'podcast', 'silence': true, 'gap': 1.0, 'people': false, 'music': false}),
  ('meeting', 'Meeting call', {'denoise': true, 'noise': 'strong', 'voice': true, 'level': true, 'target': 'podcast', 'silence': true, 'gap': 2.0, 'people': false, 'music': false}),
  ('outside', 'Interview outside', {'denoise': true, 'noise': 'strong', 'voice': true, 'level': true, 'target': 'podcast', 'silence': true, 'gap': 1.0, 'people': true, 'music': false}),
  ('music', 'Voice in music', {'denoise': false, 'voice': false, 'level': true, 'target': 'reels', 'silence': false, 'people': false, 'music': true}),
];
const _clTargets = {'podcast': 'Podcast', 'reels': 'Reels', 'audiobook': 'Audiobook', 'broadcast': 'Radio'};
const _clNoise = {'light': 'Light', 'medium': 'Medium', 'strong': 'Strong'};
final _clGaps = <double, String>{0.5: '0.5 s', 1.0: '1 s', 2.0: '2 s'};

String _db(Object? v) => v is num ? '${v > 0 ? '+' : ''}${v.toStringAsFixed(1)} dB' : '–';
String _lu(Object? v) => v is num ? '${v.round()} LUFS' : '–';
double _d(Object? v) => v is num ? v.toDouble() : double.tryParse('$v') ?? 0;

class VocalCleanupPage extends StatefulWidget {
  const VocalCleanupPage({super.key, required this.store, required this.player, this.conv = '', this.embedded = true});
  final VocalStore store;
  final VocalPlayer player;
  final String conv;
  final bool embedded;
  @override
  State<VocalCleanupPage> createState() => _VocalCleanupPageState();
}

class _VocalCleanupPageState extends State<VocalCleanupPage> {
  VocalFile? _file;
  String _fid = '', _from = '', _kind = '', _noise = 'medium', _target = 'podcast', _hear = 'After';
  double _gap = 1;
  bool _denoise = true, _voice = true, _silence = false, _level = true, _music = false, _people = false, _busy = false, _listening = false;
  Map<String, dynamic>? _heard, _out;
  VocalStore get store => widget.store;
  bool get _premium => _music || _people;

  Map<String, dynamic> get _fixes => {'denoise': _denoise, 'noise': _noise, 'voice': _voice, 'level': _level, 'target': _target,
      'silence': _silence, 'gap': _gap, 'people': _people, 'music': _music};

  void _apply(Map<String, Object?> m) {
    _denoise = m['denoise'] as bool? ?? _denoise;
    _noise = m['noise'] as String? ?? _noise;
    _voice = m['voice'] as bool? ?? _voice;
    _level = m['level'] as bool? ?? _level;
    _target = m['target'] as String? ?? _target;
    _silence = m['silence'] as bool? ?? _silence;
    _gap = (m['gap'] as num?)?.toDouble() ?? _gap;
    _people = m['people'] as bool? ?? _people;
    _music = m['music'] as bool? ?? _music;
  }

  Future<void> _chosen(VocalFile f) async {
    setState(() { _file = f; _fid = ''; _from = ''; _heard = null; _kind = ''; _listening = true; });
    try {
      Map<String, dynamic> r;
      if (VocalStore.debug) {
        r = crMap(crMap(VocalStore.debugData!['cleanup'])['heard']);
      } else {
        _fid = await vocalUpload(store, widget.conv, f);
        r = await store.app.api!.vocalCleanupListen({'file_id': _fid});
      }
      if (!mounted || _file != f) return;
      setState(() {
        _heard = r;
        final pick = crMap(r['pick']);
        if (pick.isNotEmpty) _apply({'denoise': pick['denoise'], 'noise': pick['noise'], 'level': pick['level'], 'silence': pick['silence'], 'voice': true});
      });
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _listening = false);
  }

  Future<void> _go({String again = ''}) async {
    if (_file == null && again.isEmpty && _from.isEmpty) return;
    if (!(_denoise || _voice || _silence || _level || _music || _people)) {
      crToast(context, 'Choose at least one thing to fix.');
      return;
    }
    setState(() => _busy = true);
    try {
      Map<String, dynamic> made;
      if (VocalStore.debug) {
        made = crMap(crMap(VocalStore.debugData!['cleanup'])['made']);
      } else {
        final src = again.isNotEmpty ? again : _from;
        if (src.isEmpty && _fid.isEmpty) _fid = await vocalUpload(store, widget.conv, _file!);
        made = await store.app.api!.vocalCleanup({
          if (src.isNotEmpty) 'source_of': src else 'file_id': _fid,
          'name': _file?.name ?? crS(_out?['title']), ..._fixes,
        });
        unawaited(store.load());
      }
      if (mounted) setState(() { _out = made; _hear = 'After'; });
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  void _open(Map<String, dynamic> h, {bool stronger = false}) {
    final fx = crMap(h['fixes']);
    setState(() {
      _out = h;
      _hear = 'After';
      _kind = '';
      _from = crS(h['src']).isNotEmpty ? crS(h['id']) : '';
      _heard = crMap(h['before']).containsKey('found') ? crMap(h['before']) : null;
      if (fx.isNotEmpty) _apply(fx);
      if (stronger) {
        _denoise = true;
        _noise = _noise == 'light' ? 'medium' : 'strong';
      }
    });
    if (stronger) _go(again: crS(h['id']));
  }

  Widget _heardBox(HoolaColors c, Map<String, dynamic> m) {
    final f = crMap(m['found']);
    final rows = <(bool, String, String)>[
      (f['noise'] != true, f['noise'] == true ? 'Background noise' : 'Little background noise', '${_db(m['background'])} background'),
      (f['quiet'] != true && f['loud'] != true, f['quiet'] == true ? 'Quiet' : f['loud'] == true ? 'Loud' : 'Loudness is fine', _lu(m['lufs'])),
      (f['clips'] != true, f['clips'] == true ? 'Loud words hit the top ${crInt(m['clips']) > 1 ? '${crInt(m['clips'])} times' : ''}'.trim() : 'No crackle', 'loudest ${_db(m['peak'])}'),
      (f['pauses'] != true, f['pauses'] == true ? '${crInt(m['pauses'])} long pause${crInt(m['pauses']) == 1 ? '' : 's'}' : 'No long pauses',
          f['pauses'] == true ? 'longest ${_d(m['longest']).toStringAsFixed(1)} s' : 'none over 1 s'),
    ];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('What Hoola heard', style: HoolaType.small(c).copyWith(color: c.ink3)),
      const SizedBox(height: 6),
      Wrap(spacing: 6, runSpacing: 6, children: [
        for (final (ok, t, v) in rows)
          Semantics(
            label: '$t, $v',
            excludeSemantics: true,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(color: ok ? c.sunk : c.warnSoft, borderRadius: BorderRadius.circular(12)),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Container(width: 7, height: 7, decoration: BoxDecoration(color: ok ? c.ok : c.warn, shape: BoxShape.circle)),
                const SizedBox(width: 6),
                Flexible(child: Text(t, style: HoolaType.small(c).copyWith(fontWeight: FontWeight.w600, color: c.ink))),
              ]),
            ),
          ),
      ]),
    ]);
  }

  Widget _fix(String label, bool on, ValueChanged<bool> put, {bool found = false, Widget? more}) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          CrSwitch(title: label, sub: found ? 'Found in your recording' : '', value: on, onChanged: (v) => setState(() => put(v))),
          if (on && more != null) Padding(padding: const EdgeInsets.only(top: 6), child: more),
        ]),
      );

  Widget _resultBox(BuildContext context, HoolaColors c, Map<String, dynamic> h) {
    final p = widget.player, before = _hear == 'Before', kept = crS(h['src']).isNotEmpty, id = crS(h['id']);
    final key = before ? 'clsrc:$id' : id, b = crMap(h['before']), a = crMap(h['after']), fx = crMap(h['fixes']);
    return VocalBox(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      VocalTabs(tabs: const ['Before', 'After'], picked: _hear, onPick: (v) => setState(() => _hear = v)),
      const SizedBox(height: 12),
      Row(children: [
        VocalPlayButton(label: before ? 'Play your recording as it was' : 'Play the cleaned recording', playing: p.playing(key), loading: p.busy(key),
            size: 48, onTap: () {
              if (before && !kept) return;
              p.toggle(context, key, () => before ? store.app.api!.vocalCleanupSource(id) : store.app.api!.vocalAudio(id),
                  ext: before ? (crS(h['src_ext']).isEmpty ? 'wav' : crS(h['src_ext'])) : (crS(h['ext']).isEmpty ? 'mp3' : crS(h['ext'])));
            }),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(before ? 'As recorded' : 'Cleaned', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
          Text(before && !kept ? 'Your own recording is no longer kept.' : 'Your words and timing stay.', style: HoolaType.small(c).copyWith(color: c.ink3)),
        ])),
      ]),
      if (b.isNotEmpty && a.isNotEmpty) ...[
        const SizedBox(height: 12),
        Text('Loudness ${_lu(b['lufs'])} → ${_lu(a['lufs'])} · background ${_db(b['background'])} → ${_db(a['background'])}',
            style: HoolaType.small(c).copyWith(fontFeatures: const [FontFeature.tabularFigures()], color: c.ink2)),
        if (fx['silence'] == true && crInt(b['pauses']) > 0)
          Text('${crInt(b['pauses'])} pause${crInt(b['pauses']) == 1 ? '' : 's'} shortened · ${vocalClock(_d(b['seconds']))} → ${vocalClock(_d(a['seconds']))}',
              style: HoolaType.small(c).copyWith(color: c.ink2)),
      ],
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: VocalChip(label: 'Download', onTap: () => vocalShare(context, store.app, h, store: store))),
        const SizedBox(width: 8),
        if (kept) Expanded(child: VocalChip(label: fx['noise'] == 'strong' ? 'Clean again' : 'Clean again, stronger',
            onTap: _busy ? null : () => fx['noise'] == 'strong' ? _open(h) : _open(h, stronger: true))),
      ]),
    ]));
  }

  @override
  Widget build(BuildContext context) {
    final body = ListenableBuilder(
      listenable: Listenable.merge([store, widget.player]),
      builder: (context, _) {
        final c = HoolaColors.of(context);
        final f = _file;
        final fnd = crMap(_heard?['found']);
        final premOk = store.engines.any((e) => crS(e['id']) == 'eleven' && crS(e['state']) == 'ready');
        final out = _out == null ? null : store.history.firstWhere((x) => crS(x['id']) == crS(_out!['id']), orElse: () => _out!);
        final recent = store.history.where((x) => crS(x['kind']) == 'cleanup' && crS(x['id']) != crS(out?['id'])).take(3).toList();
        return Column(children: [
          Expanded(
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 14, 16, 24), children: [
              Text('Hoola listens first, tells you what is wrong, and fixes only that.', style: HoolaType.small(c).copyWith(fontSize: 14, color: c.ink2)),
              const SizedBox(height: 12),
              _Source(file: f, what: 'cleanup', onFile: _chosen),
              if (_listening) ...[
                const SizedBox(height: 10),
                Semantics(liveRegion: true, child: Text('Listening for noise, loudness, crackle and long pauses…', style: HoolaType.small(c).copyWith(color: c.ink3))),
              ] else if (_heard != null) ...[
                const SizedBox(height: 10),
                _heardBox(c, _heard!),
              ],
              const SizedBox(height: 14),
              const VocalLabel('What kind of recording is it?'),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(children: [
                  for (final (k, l, m) in _clKinds)
                    Padding(padding: const EdgeInsets.only(right: 6), child: VocalChip(label: l, on: _kind == k, onTap: () => setState(() { _kind = k; _gap = 1; _apply(m); }))),
                ]),
              ),
              const SizedBox(height: 12),
              const VocalLabel('Fix'),
              _fix('Remove background noise', _denoise, (v) => _denoise = v, found: fnd['noise'] == true,
                  more: VocalTabs(tabs: _clNoise.values.toList(), picked: _clNoise[_noise] ?? 'Medium',
                      onPick: (v) => setState(() => _noise = _clNoise.entries.firstWhere((e) => e.value == v).key))),
              _fix('Make the voice clearer', _voice, (v) => _voice = v),
              _fix('Even out the loudness', _level, (v) => _level = v, found: fnd['quiet'] == true || fnd['loud'] == true || fnd['clips'] == true,
                  more: VocalTabs(tabs: _clTargets.values.toList(), picked: _clTargets[_target] ?? 'Podcast',
                      onPick: (v) => setState(() => _target = _clTargets.entries.firstWhere((e) => e.value == v).key))),
              _fix('Shorten long pauses', _silence, (v) => _silence = v, found: fnd['pauses'] == true,
                  more: VocalTabs(tabs: _clGaps.values.toList(), picked: _clGaps[_gap] ?? '1 s',
                      onPick: (v) => setState(() => _gap = _clGaps.entries.firstWhere((e) => e.value == v).key))),
              const SizedBox(height: 6),
              VocalLabel(premOk ? 'Lift the voice out · uses credits' : 'Lift the voice out · not connected on this server'),
              _fix('Remove street sounds and other people', _people && premOk, (v) => _people = premOk && v),
              _fix('Take the voice out of music', _music && premOk, (v) => _music = premOk && v),
              if (out != null) ...[
                const SizedBox(height: 16),
                const VocalLabel('Hear the difference'),
                _resultBox(context, c, out),
              ],
              if (recent.isNotEmpty) ...[
                const SizedBox(height: 16),
                const VocalLabel('Recent clean-ups'),
                for (final h in recent)
                  Semantics(
                    button: true,
                    label: 'Open ${crS(h['title']).isEmpty ? 'clean-up' : crS(h['title'])}',
                    excludeSemantics: true,
                    onTap: () => _open(h),
                    child: InkWell(
                      onTap: () => _open(h),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(minHeight: 48),
                        child: Row(children: [
                          Expanded(child: Text(crS(h['title']).isEmpty ? 'Clean-up' : crS(h['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                              style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500))),
                          const SizedBox(width: 8),
                          Flexible(child: Text(crS(h['voice_name']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.ink3))),
                        ]),
                      ),
                    ),
                  ),
              ],
            ]),
          ),
          VocalDock(
            note: _premium && premOk ? 'Lifting the voice out uses credits · the rest is free' : 'Noise, clarity, pauses and loudness are free',
            child: VocalPill(label: _premium && premOk ? 'Clean it' : 'Clean it · free', busy: _busy, onTap: f == null && _from.isEmpty ? null : () => _go()),
          ),
        ]);
      },
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Clean-up', body: body);
  }
}

// ================================================================================================ Sound effects
// v0.999.162 (design canvas claude.ai/artifact/2vU7LhKsPWKeT58GXAwRdK): From words = describe it (Improve the words, add to
// the words), length, how closely to follow the words, a smooth loop, takes; each take kept with a star. Game sounds = made
// on Hoola's own server for free, heard without being kept, numbered versions, kept with a star.
const _fxAdds = [('Far away', 'far away'), ('Close up', 'close up'), ('Echo', 'with an echo'), ('Indoors', 'indoors'), ('Outdoors', 'outdoors'), ('Slow', 'slow')];
const _fxPadNames = {'coin': 'Coin', 'jump': 'Jump', 'powerup': 'Power-up', 'laser': 'Laser', 'explosion': 'Explosion', 'hit': 'Hit', 'hurt': 'Hurt',
  'blip': 'Blip', 'click': 'Click', 'select': 'Select'};
String _fxPad(String p) => _fxPadNames[p] ?? (p.isEmpty ? '' : p.replaceAll('_', ' ')[0].toUpperCase() + p.replaceAll('_', ' ').substring(1));

class VocalSfxPage extends StatefulWidget {
  const VocalSfxPage({super.key, required this.store, required this.player, this.conv = '', this.embedded = true});
  final VocalStore store;
  final VocalPlayer player;
  final String conv;
  final bool embedded;
  @override
  State<VocalSfxPage> createState() => _VocalSfxPageState();
}

class _VocalSfxPageState extends State<VocalSfxPage> {
  final _prompt = TextEditingController();
  String _tab = 'From words', _secs = 'Auto', _pad = '';
  bool _loop = false, _busy = false, _improving = false;
  int _takes = 4, _seed = 1;
  double _follow = 3;
  Map<String, dynamic> _quote = const {}, _imp = const {}, _partial = const {};
  List<Map<String, dynamic>> _made = [];
  VocalStore get store => widget.store;

  @override
  void initState() {
    super.initState();
    _prompt.addListener(() {
      if (mounted) setState(() {});
    });
    _requote();
  }

  @override
  void dispose() {
    _prompt.dispose();
    super.dispose();
  }

  double get _seconds => _secs == 'Auto' ? 0 : (double.tryParse(_secs.replaceAll(' s', '')) ?? 0);
  String get _followWord => _follow <= 2 ? 'Loose' : _follow <= 6 ? 'Balanced' : 'Close';
  bool get _wordsReady => store.engines.isEmpty || store.engines.any((e) => crS(e['id']) == 'eleven' && crS(e['state']) == 'ready');
  List<String> get _pads => (store.ov['sfx'] is List) ? (store.ov['sfx'] as List).map(crS).where((x) => x.isNotEmpty).toList() : const <String>[];
  bool _has(String w) => RegExp('(^|[\\s,])${RegExp.escape(w)}(\$|[\\s,.])', caseSensitive: false).hasMatch(_prompt.text);

  Future<void> _requote() async {
    if (VocalStore.debug) {
      setState(() => _quote = crMap(VocalStore.debugData!['quote']));
      return;
    }
    try {
      final q = await store.app.api?.vocalQuote({'job': 'sfx', 'seconds': _seconds == 0 ? 5 : _seconds, 'takes': _takes});
      if (q != null && mounted) setState(() => _quote = q);
    } catch (_) {}
  }

  void _add(String w) {
    var t = _prompt.text.trim();
    if (_has(w)) {
      t = t.replaceFirst(RegExp('\\s*,?\\s*${RegExp.escape(w)}(?=\$|[\\s,.])', caseSensitive: false), '').replaceFirst(RegExp(r'^\s*,\s*'), '').trim();
    } else {
      t = t.replaceFirst(RegExp(r'[.,\s]+$'), '');
      t = t.isEmpty ? w : '$t, $w';
    }
    _prompt.text = t.length > 450 ? t.substring(0, 450) : t;
  }

  Future<void> _improve() async {
    final p = _prompt.text.trim();
    if (p.length < 3) return;
    setState(() => _improving = true);
    try {
      final r = VocalStore.debug ? crMap(VocalStore.debugData!['sfx_improve']) : await store.app.api!.vocalSfxImprove(p);
      if (mounted) setState(() => _imp = r);
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _improving = false);
  }

  Future<void> _go({int? takes}) async {
    final p = _prompt.text.trim();
    if (p.length < 3) return;
    final n = takes ?? _takes;
    setState(() => _busy = true);
    try {
      Map<String, dynamic> r;
      if (VocalStore.debug) {
        r = {'items': crList(VocalStore.debugData!['speech']), 'made': 1, 'asked': 1};
      } else {
        r = await store.app.api!.vocalSfx({'prompt': p, 'seconds': _seconds, 'loop': _loop, 'takes': n, 'follow': _follow / 10,
          if (widget.conv.isNotEmpty) 'chat': widget.conv});
        unawaited(store.load());
      }
      final made = vocalMade(r);
      if (mounted) setState(() { _made = made; _partial = (r['failed'] is num && (r['failed'] as num) > 0) ? r : const {}; });
      if (made.isNotEmpty && mounted) _play(made.first);
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  void _play(Map<String, dynamic> t) {
    final id = crS(t['id']);
    final ext = crS(t['ext']).isEmpty ? 'mp3' : crS(t['ext']);
    unawaited(widget.player.toggle(context, id, () => store.app.api!.vocalAudio(id, format: ext), ext: ext));
  }

  Future<void> _star(Map<String, dynamic> t) async {
    final on = t['star'] != true;
    try {
      if (!VocalStore.debug) await store.app.api!.vocalHistoryStar(crS(t['id']), on);
      if (!mounted) return;
      setState(() => _made = [for (final x in _made) crS(x['id']) == crS(t['id']) ? {...x, 'star': on} : x]);
      crToast(context, on ? 'Kept in Your sound effects.' : 'No longer kept.');
      if (!VocalStore.debug) unawaited(store.load());
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  void _hear() {
    final p = _pad.isEmpty && _pads.isNotEmpty ? _pads.first : _pad;
    if (p.isEmpty || VocalStore.debug) return;
    unawaited(widget.player.toggle(context, 'fx:$p:$_seed', () => store.app.api!.vocalSfxPlay(p, _seed), ext: 'wav'));
  }

  Future<void> _keepGame() async {
    final p = _pad.isEmpty && _pads.isNotEmpty ? _pads.first : _pad;
    if (p.isEmpty) return;
    setState(() => _busy = true);
    try {
      if (!VocalStore.debug) {
        final r = await store.app.api!.vocalSfx({'preset': p, 'seed': _seed});
        await store.app.api!.vocalHistoryStar(crS(r['id']), true);
        unawaited(store.load());
      }
      if (mounted) crToast(context, 'Kept ${_fxPad(p)} #$_seed in Your sound effects.');
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _words(BuildContext context, HoolaColors c) {
    final ready = _wordsReady;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      if (!ready)
        VocalBox(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Sounds from words are not on this server yet', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text('They run on ElevenLabs, which is not connected here. Nothing was charged. Game sounds always work.', style: HoolaType.small(c).copyWith(color: c.ink2)),
          const SizedBox(height: 8),
          VocalChip(label: 'Open game sounds', onTap: () => setState(() => _tab = 'Game sounds')),
        ])),
      if (!ready) const SizedBox(height: 12),
      const VocalLabel('Describe the sound'),
      TextField(controller: _prompt, minLines: 2, maxLines: 4, maxLength: 450, style: HoolaType.reply(c).copyWith(fontSize: 16),
          buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null,
          decoration: vocalInput(c, 'A temple bell rung once, far away, with a soft echo')),
      const SizedBox(height: 6),
      Row(children: [
        Expanded(child: Align(alignment: Alignment.centerLeft,
            child: VocalChip(label: _improving ? 'Improving…' : 'Improve the words', onTap: _improving || _prompt.text.trim().length < 3 ? null : _improve))),
        const SizedBox(width: 8),
        Text('${_prompt.text.length} / 450', style: HoolaType.small(c).copyWith(color: c.ink3)),
      ]),
      if (_imp.isNotEmpty) ...[
        const SizedBox(height: 8),
        VocalBox(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(crS(_imp['why']).isEmpty ? 'Hoola suggests' : 'Hoola suggests · ${crS(_imp['why'])}', style: HoolaType.small(c).copyWith(color: c.ink2)),
          const SizedBox(height: 4),
          Text(crS(_imp['text']), style: HoolaType.reply(c).copyWith(fontSize: 15)),
          const SizedBox(height: 8),
          Wrap(spacing: 6, children: [
            VocalChip(label: 'Use these words', on: true, onTap: () => setState(() { _prompt.text = crS(_imp['text']); _imp = const {}; })),
            VocalChip(label: 'Keep mine', onTap: () => setState(() => _imp = const {})),
          ]),
        ])),
      ],
      const SizedBox(height: 10),
      const VocalLabel('Add to the words'),
      Wrap(spacing: 6, runSpacing: 0, children: [
        for (final (l, w) in _fxAdds) VocalChip(label: l, on: _has(w), onTap: () => setState(() => _add(w))),
      ]),
      const SizedBox(height: 8),
      const VocalLabel('Length'),
      Wrap(spacing: 6, runSpacing: 0, children: [
        for (final s in const ['Auto', '1 s', '3 s', '5 s', '10 s', '30 s']) VocalChip(label: s, on: s == _secs, onTap: () {
          setState(() => _secs = s);
          _requote();
        }),
      ]),
      const SizedBox(height: 8),
      Row(children: [const Expanded(child: VocalLabel('How closely to follow your words')), Text(_followWord, style: HoolaType.small(c).copyWith(color: CrHue.voice.b, fontWeight: FontWeight.w500))]),
      Semantics(label: 'How closely to follow your words', value: _followWord,
          child: Slider(value: _follow, min: 0, max: 10, divisions: 10, activeColor: CrHue.voice.b, onChanged: (v) => setState(() => _follow = v))),
      Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: Row(children: [
        Expanded(child: Text('Free, more surprising', style: HoolaType.small(c).copyWith(color: c.ink3))),
        Expanded(child: Text('Exactly what I wrote', textAlign: TextAlign.end, style: HoolaType.small(c).copyWith(color: c.ink3)))])),
      const SizedBox(height: 8),
      CrSwitch(title: 'Loops smoothly', sub: 'The end runs into the start, for rain, a fan or a crowd behind a video.', value: _loop,
          onChanged: (v) => setState(() => _loop = v)),
      const SizedBox(height: 8),
      const VocalLabel('Takes'),
      Wrap(spacing: 6, runSpacing: 0, children: [
        for (final n in const [1, 2, 3, 4]) VocalChip(label: '$n', on: n == _takes, onTap: () {
          setState(() => _takes = n);
          _requote();
        }),
      ]),
      if (_partial.isNotEmpty) ...[
        const SizedBox(height: 12),
        VocalBox(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${_partial['made']} of ${_partial['asked']} takes were made', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
          Text('${crS(_partial['error'])} You were charged only for the takes that landed.', style: HoolaType.small(c).copyWith(color: c.ink2)),
          const SizedBox(height: 6),
          VocalChip(label: 'Make ${_partial['failed']} more', onTap: _busy ? null : () => _go(takes: (_partial['failed'] as num).toInt())),
        ])),
      ],
      if (_made.isNotEmpty) ...[
        const SizedBox(height: 16),
        VocalLabel(_made.length == 1 ? 'Your sound' : '${_made.length} takes'),
        VocalBox(child: Column(children: [
          for (var i = 0; i < _made.length; i++) ...[
            if (i > 0) const SizedBox(height: 8),
            VocalTakeRow(store: store, player: widget.player, item: _made[i], name: 'Take ${crS(_made[i]['take']).isEmpty ? i + 1 : crS(_made[i]['take'])}',
                trailing: VocalIconButton(label: _made[i]['star'] == true ? 'Kept: tap to unkeep' : 'Keep this take',
                    icon: _made[i]['star'] == true ? Icons.star_rounded : Icons.star_outline_rounded, onTap: () => _star(_made[i])),
                onMore: () async {
                  final pick = await vocalMore(context, 'Take ${i + 1}', const ['Download', 'Delete']);
                  if (!context.mounted || pick == null) return;
                  if (pick == 'Download') await vocalShare(context, store.app, _made[i], store: store);
                  if (pick == 'Delete' && context.mounted && await vocalDeleteSound(context, store, _made[i])) {
                    setState(() => _made = _made.where((x) => crS(x['id']) != crS(_made[i]['id'])).toList());
                  }
                }),
          ],
        ])),
      ],
    ]);
  }

  Widget _game(BuildContext context, HoolaColors c) {
    final pads = _pads;
    if (pads.isEmpty) return Text('No game sounds on this server.', style: HoolaType.small(c).copyWith(color: c.ink2));
    final cur = _pad.isEmpty ? pads.first : _pad;
    final lo = _seed > 2 ? _seed - 2 : 1;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('Free, made on Hoola’s own server. Tap to hear one. Listening keeps nothing; the same number always gives the same sound.',
          style: HoolaType.small(c).copyWith(color: c.ink2)),
      const SizedBox(height: 10),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final p in pads)
          SizedBox(width: 160, child: VocalChip(label: _fxPad(p), on: p == cur, onTap: () {
            setState(() { if (_pad != p) _seed = 1; _pad = p; });
            _hear();
          })),
      ]),
      const SizedBox(height: 14),
      VocalLabel('Other versions of ${_fxPad(cur)}'),
      Wrap(spacing: 6, runSpacing: 0, children: [
        for (var n = lo; n < lo + 6; n++) VocalChip(label: '#$n', on: n == _seed, onTap: () {
          setState(() { _pad = cur; _seed = n; });
          _hear();
        }),
        VocalChip(label: 'Another one', onTap: () {
          setState(() { _pad = cur; _seed += 1; });
          _hear();
        }),
      ]),
      const SizedBox(height: 14),
      VocalPill(label: 'Keep ${_fxPad(cur)} #$_seed', busy: _busy, onTap: _keepGame),
      const SizedBox(height: 8),
      Text('Need a door, a crowd or rain? Describe it under From words.', style: HoolaType.small(c).copyWith(color: c.ink3)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final body = ListenableBuilder(
      listenable: Listenable.merge([store, widget.player]),
      builder: (context, _) {
        final c = HoolaColors.of(context);
        final credits = vocalCredits(_quote);
        final words = _tab == 'From words';
        return Column(children: [
          Expanded(
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 14, 16, 24), children: [
              VocalTabs(tabs: const ['From words', 'Game sounds'], picked: _tab, onPick: (t) => setState(() => _tab = t)),
              const SizedBox(height: 14),
              words ? _words(context, c) : _game(context, c),
            ]),
          ),
          if (words)
            VocalDock(
              note: 'Sounds from words run on ElevenLabs · nothing is spent until you tap',
              child: VocalPill(label: credits.isEmpty ? 'Make $_takes ${_takes == 1 ? 'take' : 'takes'}' : 'Make $_takes ${_takes == 1 ? 'take' : 'takes'} · $credits', busy: _busy,
                  onTap: !_wordsReady || _prompt.text.trim().length < 3 ? null : () => _go()),
            ),
        ]);
      },
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Sound effects', body: body);
  }
}

// ================================================================================================ Dictionary
// v0.999.163 (canvas claude.ai/artifact/VDXqUd7zx9TMxwTjVcXiJz): add or change a word with Hear it before saving and IPA
// keys, test a sentence (the words read her way are marked and named), every word with Hear / Change / Remove and how
// many of her sounds use it, find a word, a language filter, and Import a list checked line by line before anything is added.
class VocalDictionaryPage extends StatefulWidget {
  const VocalDictionaryPage({super.key, required this.store, this.player, this.embedded = true});
  final VocalStore store;
  final VocalPlayer? player;
  final bool embedded;
  @override
  State<VocalDictionaryPage> createState() => _VocalDictionaryPageState();
}

class _VocalDictionaryPageState extends State<VocalDictionaryPage> {
  final _word = TextEditingController();
  final _say = TextEditingController();
  final _ipa = TextEditingController();
  final _test = TextEditingController();
  String _lang = '';
  String _edit = '';
  String _q = '';
  String _lf = '';
  bool _busy = false;
  VocalPlayer? _own;
  final _formKey = GlobalKey();
  VocalStore get store => widget.store;
  VocalPlayer get _player => widget.player ?? (_own ??= VocalPlayer(store.app));

  static const _ipaKeys = ['ə', 'ɪ', 'ʊ', 'ɛ', 'ɔ', 'aː', 'iː', 'uː', 'ʃ', 'ʒ', 'θ', 'ð', 'ŋ', 't̪', 'd̪', 'ɳ', 'ɾ', 'ʰ', 'ː', 'ˈ'];

  @override
  void initState() {
    super.initState();
    for (final t in [_word, _say, _ipa, _test]) {
      t.addListener(() {
        if (mounted) setState(() {});
      });
    }
  }

  @override
  void dispose() {
    _word.dispose();
    _say.dispose();
    _ipa.dispose();
    _test.dispose();
    _own?.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> get _rules => crList(store.ov['rules']);
  Map<String, dynamic> get _uses => crMap(store.ov['rule_uses']);
  int get _max {
    final n = crInt(crMap(store.ov['limits'])['rules']);
    return n > 0 ? n : 200;
  }

  bool get _ready => _word.text.trim().isNotEmpty && (_say.text.trim().isNotEmpty || _ipa.text.trim().isNotEmpty);

  /// The words of hers this text has in it (whole words, any letter case).
  List<Map<String, dynamic>> _found(String text) => [
        for (final r in _rules)
          if (crS(r['word']).isNotEmpty &&
              RegExp('(^|[^\\p{L}\\p{N}])${RegExp.escape(crS(r['word']))}(\$|[^\\p{L}\\p{N}])', caseSensitive: false, unicode: true).hasMatch(text))
            r,
      ];

  Future<void> _save() async {
    final w = _word.text.trim(), s = _say.text.trim(), i = _ipa.text.trim();
    if (!_ready) return;
    setState(() => _busy = true);
    try {
      if (VocalStore.debug) {
        if (_edit.isNotEmpty) {
          VocalStore.debugAnswer('rule_update', {'id': _edit, 'word': w, 'say': s, 'ipa': i, 'lang': _lang});
          store.ov = {...store.ov, 'rules': [for (final r in _rules) crS(r['id']) == _edit ? {...r, 'word': w, 'say': s, 'ipa': i, 'lang': _lang} : r]};
        } else {
          store.ov = {...store.ov, 'rules': [{'id': 'pr_new', 'word': w, 'say': s, 'ipa': i, 'lang': _lang}, ..._rules]};
        }
        store.tell();
      } else {
        if (_edit.isNotEmpty) {
          await store.app.api!.vocalRuleUpdate(_edit, w, s, ipa: i, lang: _lang);
        } else {
          await store.app.api!.vocalRule(w, s, ipa: i, lang: _lang);
        }
        await store.load();
      }
      if (mounted) {
        crToast(context, _edit.isNotEmpty ? '“$w” changed. Every voice reads it your way now.' : '$w is in your dictionary.');
        _clear();
      }
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  void _clear() {
    _word.clear();
    _say.clear();
    _ipa.clear();
    setState(() {
      _edit = '';
      _lang = '';
    });
  }

  void _change(Map<String, dynamic> r) {
    _word.text = crS(r['word']);
    _say.text = crS(r['say']);
    _ipa.text = crS(r['ipa']);
    setState(() {
      _edit = crS(r['id']);
      _lang = crS(r['lang']);
    });
    final fc = _formKey.currentContext;
    if (fc != null) Scrollable.ensureVisible(fc, duration: const Duration(milliseconds: 200));
  }

  Future<void> _remove(Map<String, dynamic> r) async {
    final n = crInt(_uses[crS(r['id'])]);
    final ok = await vocalConfirm(context, 'Remove “${crS(r['word'])}”?',
        n > 0 ? 'It is in $n of your sounds. Those stay as they are; new sounds read it the usual way.' : 'New sounds read it the usual way.', 'Remove');
    if (ok != true || !mounted) return;
    try {
      if (!VocalStore.debug) {
        await store.app.api!.vocalRuleDelete(crS(r['id']));
        await store.load();
      } else {
        store.ov = {...store.ov, 'rules': _rules.where((x) => crS(x['id']) != crS(r['id'])).toList()};
        store.tell();
      }
      if (_edit == crS(r['id'])) _clear();
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  /// A short free sample: a word, the respelling being written, or her sentence.
  Future<void> _hear(String text) async {
    final t = text.trim();
    if (t.isEmpty) {
      crToast(context, 'Write the word first.');
      return;
    }
    if (VocalStore.debug) {
      VocalStore.debugAnswer('hear', {'text': t, 'lang': _lang});
      return;
    }
    try {
      await _player.toggle(context, 'hear_${t.hashCode.toUnsigned(32)}', () => store.app.api!.vocalHear(t, lang: _lang), ext: 'wav');
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  Future<void> _import() async {
    final text = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => CrHueScope(hue: CrHue.voice, child: _DictImportSheet(store: store)),
    );
    if (text == null || text.isEmpty || !mounted) return;
    try {
      if (!VocalStore.debug) {
        final r = await store.app.api!.vocalRulesImport(text);
        await store.load();
        final n = crInt(r['added'] ?? r['count']);
        if (mounted) crToast(context, n > 0 ? '$n word${n == 1 ? '' : 's'} added.' : 'The list was read.');
      } else {
        VocalStore.debugAnswer('rules_import', {'text': text});
      }
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  Future<void> _pickLang() async {
    final v = await showModalBottomSheet<String>(context: context, showDragHandle: true, isScrollControlled: true,
        builder: (_) => CrHueScope(hue: CrHue.voice, child: VocalLanguageSheet(store: store, current: _lang.isEmpty ? 'auto' : _lang)));
    if (v != null && mounted) setState(() => _lang = v == 'auto' ? '' : v);
  }

  Widget _field(HoolaColors c, TextEditingController t, String hint, int max, {bool mono = false}) => TextField(
        controller: t,
        maxLength: max,
        style: mono ? HoolaType.body(c).copyWith(fontFamily: 'monospace') : HoolaType.body(c),
        decoration: vocalInput(c, hint),
        buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null,
      );

  void _key(String k) {
    final v = _ipa.value, sel = v.selection.isValid ? v.selection : TextSelection.collapsed(offset: v.text.length);
    final text = v.text.replaceRange(sel.start, sel.end, k);
    _ipa.value = TextEditingValue(text: text, selection: TextSelection.collapsed(offset: sel.start + k.length));
  }

  @override
  Widget build(BuildContext context) {
    final body = ListenableBuilder(
      listenable: store,
      builder: (context, _) {
        final c = HoolaColors.of(context);
        final rules = _rules;
        final langs = <String>{for (final r in rules) crS(r['lang'])}.toList();
        final q = _q.trim().toLowerCase();
        final shown = [
          for (final r in rules)
            if ((_lf.isEmpty || (_lf == '*' ? crS(r['lang']).isEmpty : crS(r['lang']) == _lf)) &&
                (q.isEmpty || '${crS(r['word'])} ${crS(r['say'])}'.toLowerCase().contains(q)))
              r,
        ];
        final hits = _found(_test.text);
        final small = HoolaType.small(c).copyWith(fontSize: 12);
        return ListView(padding: const EdgeInsets.fromLTRB(16, 14, 16, 24), children: [
          Text('How your names, places and products are said, by every voice.', style: HoolaType.small(c).copyWith(fontSize: 14, color: c.ink2)),
          const SizedBox(height: 12),
          VocalBox(
            key: _formKey,
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              VocalLabel(_edit.isNotEmpty ? 'Change a word' : 'Add a word'),
              _field(c, _word, 'Word, as written: Mithas', 60),
              const SizedBox(height: 8),
              _field(c, _say, 'Say it as: Mi-thaas', 120),
              const SizedBox(height: 8),
              _field(c, _ipa, 'Sounds in IPA (optional): mɪˈt̪ʰaːs', 120, mono: true),
              const SizedBox(height: 6),
              Wrap(spacing: 4, runSpacing: 4, children: [
                for (final k in _ipaKeys)
                  Semantics(
                    button: true,
                    label: 'Add the sound $k',
                    excludeSemantics: true,
                    onTap: () => _key(k),
                    child: InkWell(
                      onTap: () => _key(k),
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                        alignment: Alignment.center,
                        decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(8)),
                        child: Text(k, style: HoolaType.body(c).copyWith(fontFamily: 'monospace', fontSize: 14)),
                      ),
                    ),
                  ),
              ]),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: VocalChip(label: _lang.isEmpty ? 'Every language' : store.langNative(_lang), menu: true, onTap: _pickLang),
                  ),
                ),
                VocalChip(label: 'Hear it', onTap: _word.text.trim().isEmpty ? null : () => _hear(_say.text.trim().isEmpty ? _word.text : _say.text)),
              ]),
              const SizedBox(height: 8),
              Row(children: [
                if (_edit.isNotEmpty) ...[
                  Expanded(child: VocalChip(label: 'Cancel', onTap: _clear)),
                  const SizedBox(width: 8),
                ],
                Expanded(child: VocalPill(label: _edit.isNotEmpty ? 'Save the change' : 'Add', busy: _busy, onTap: _ready ? _save : null)),
              ]),
              if (!_ready)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(_word.text.trim().isEmpty ? 'Write the word as it is written.' : 'Write how to say it, or its sounds.',
                      style: small.copyWith(color: c.warn)),
                ),
            ]),
          ),
          const SizedBox(height: 12),
          VocalBox(
            fill: c.sunk,
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const VocalLabel('Test a sentence'),
              TextField(controller: _test, minLines: 2, maxLines: 4, maxLength: 200, style: HoolaType.body(c),
                  decoration: vocalInput(c, 'Aaj hi aaiye Mithas Sweets, Nashik mein.'),
                  buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null),
              const SizedBox(height: 6),
              Text(_test.text.trim().isEmpty
                  ? 'Write a sentence with your words in it.'
                  : hits.isEmpty
                      ? 'No word from your dictionary is in it.'
                      : '${hits.length} word${hits.length == 1 ? '' : 's'} will be read your way: '
                          '${hits.map((r) => '${crS(r['word'])} as ${crS(r['say']).isEmpty ? '/${crS(r['ipa'])}/' : crS(r['say'])}').join(', ')}.',
                  style: small),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: VocalChip(label: 'Hear it · free', onTap: _test.text.trim().isEmpty ? null : () => _hear(_test.text)),
              ),
            ]),
          ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: VocalLabel('Your words', note: '${rules.length} of $_max')),
          ]),
          Row(children: [
            VocalChip(label: 'Import a list', onTap: _import),
          ]),
          const SizedBox(height: 8),
          if (rules.length > 6)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: TextField(
                style: HoolaType.body(c),
                decoration: vocalInput(c, 'Find a word').copyWith(prefixIcon: Icon(Icons.search_rounded, size: 20, color: c.ink3)),
                onChanged: (v) => setState(() => _q = v),
              ),
            ),
          if (langs.length > 1)
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(children: [
                for (final l in ['', ...langs.map((x) => x.isEmpty ? '*' : x)])
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: VocalChip(label: l.isEmpty ? 'All' : l == '*' ? 'Every language' : store.langNative(l), on: _lf == l,
                        onTap: () => setState(() => _lf = l)),
                  ),
              ]),
            ),
          if (rules.isEmpty)
            Text('None yet. Add a name your voices say wrong, and every voice reads it your way.', style: HoolaType.small(c))
          else if (shown.isEmpty)
            Text('No word matches.', style: HoolaType.small(c))
          else
            for (final r in shown)
              Container(
                padding: const EdgeInsets.fromLTRB(4, 4, 0, 4),
                decoration: BoxDecoration(
                    color: _edit == crS(r['id']) ? c.accentSoft : null, border: Border(bottom: BorderSide(color: c.line))),
                child: Row(children: [
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text.rich(TextSpan(children: [
                        TextSpan(text: crS(r['word']), style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                        if (crS(r['say']).isNotEmpty) TextSpan(text: '  →  ${crS(r['say'])}', style: HoolaType.body(c)),
                      ])),
                      Text([
                        if (crS(r['ipa']).isNotEmpty) '/${crS(r['ipa'])}/',
                        crS(r['lang']).isEmpty ? 'Every language' : store.langNative(crS(r['lang'])),
                        if (_uses.containsKey(crS(r['id'])))
                          crInt(_uses[crS(r['id'])]) > 0 ? 'in ${crInt(_uses[crS(r['id'])])} sound${crInt(_uses[crS(r['id'])]) == 1 ? '' : 's'}' : 'not used yet',
                      ].join(' · '), style: small),
                    ]),
                  ),
                  VocalIconButton(label: 'Hear ${crS(r['word'])}', icon: Icons.play_arrow_rounded, onTap: () => _hear(crS(r['word']))),
                  VocalIconButton(label: 'Change ${crS(r['word'])}', icon: Icons.edit_outlined, onTap: () => _change(r)),
                  VocalIconButton(label: 'Remove ${crS(r['word'])}', glyph: CrGlyph.trash, onTap: () => _remove(r)),
                ]),
              ),
          const SizedBox(height: 10),
          Text('A word matches whole, in any letter case. Your sounds keep the words as you wrote them; only the voice reads them your way.',
              style: small),
        ]);
      },
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Dictionary', body: body);
  }
}

/// Import a list: paste lines, Check them (New / Replaces yours / Left out, with why), then Add the good ones.
class _DictImportSheet extends StatefulWidget {
  const _DictImportSheet({required this.store});
  final VocalStore store;
  @override
  State<_DictImportSheet> createState() => _DictImportSheetState();
}

class _DictImportSheetState extends State<_DictImportSheet> {
  final _ctl = TextEditingController();
  Map<String, dynamic>? _check;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _ctl.addListener(() {
      if (mounted) setState(() => _check = null);
    });
  }

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  Future<void> _go() async {
    setState(() => _busy = true);
    try {
      final r = VocalStore.debug ? VocalStore.debugAnswer('rules_check', {'text': _ctl.text}) : await widget.store.app.api!.vocalRulesCheck(_ctl.text);
      if (mounted) setState(() => _check = r);
    } catch (e) {
      if (mounted) vocalError(context, widget.store, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  String _good() {
    String q(String v) => RegExp(r'[",\n]').hasMatch(v) ? '"${v.replaceAll('"', '""')}"' : v;
    return [
      for (final r in crList(_check?['rows']))
        if (crS(r['state']) != 'bad') [crS(r['word']), crS(r['say']), crS(r['ipa']), crS(r['lang'])].map(q).join(','),
    ].join('\n');
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final ck = _check;
    final small = HoolaType.small(c).copyWith(fontSize: 12);
    final ok = ck == null ? 0 : crInt(ck['new']) + crInt(ck['replace']);
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Import a list', style: HoolaType.title(c)),
          const SizedBox(height: 4),
          Text('One word a line: word, how to say it, its sounds (IPA, optional), language (optional). Nothing is added until you see the check.',
              style: small),
          const SizedBox(height: 8),
          TextField(controller: _ctl, minLines: 4, maxLines: 8, style: HoolaType.body(c), decoration: vocalInput(c, 'Nashik,Naa-shik,ˈnaːʃɪk,hi')),
          const SizedBox(height: 8),
          if (ck != null) ...[
            Text('${crInt(ck['new'])} new · ${crInt(ck['replace'])} replace yours · ${crInt(ck['bad'])} left out', style: HoolaType.body(c)),
            const SizedBox(height: 4),
            for (final r in crList(ck['rows']).take(40))
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(
                  'Line ${crInt(r['line'])}: ${crS(r['word']).isEmpty ? '—' : crS(r['word'])} · '
                  '${switch (crS(r['state'])) { 'new' => 'New', 'replace' => 'Replaces yours', _ => 'Left out: ${crS(r['why'])}' }}',
                  style: small.copyWith(color: crS(r['state']) == 'bad' ? c.bad : c.ink2),
                ),
              ),
            if (ok > crInt(ck['room']) && crInt(ck['room']) >= 0)
              Text('Only ${crInt(ck['room'])} more fit in your dictionary.', style: small.copyWith(color: c.warn)),
            const SizedBox(height: 8),
          ],
          ck == null
              ? VocalPill(label: 'Check the list', busy: _busy, onTap: _ctl.text.trim().isEmpty ? null : _go)
              : VocalPill(label: ok == 0 ? 'Nothing to add' : 'Add $ok word${ok == 1 ? '' : 's'}',
                  onTap: ok == 0 ? null : () => Navigator.of(context).pop(_good())),
        ]),
      ),
    );
  }
}

// ================================================================================================ Settings
class VocalSettingsPage extends StatefulWidget {
  const VocalSettingsPage({super.key, required this.store, required this.settings, this.onDictionary, this.embedded = true});
  final VocalStore store;
  final VocalSettings settings;
  final VoidCallback? onDictionary;
  final bool embedded;
  @override
  State<VocalSettingsPage> createState() => _VocalSettingsPageState();
}

class _VocalSettingsPageState extends State<VocalSettingsPage> {
  VocalStore get store => widget.store;
  VocalSettings get vs => widget.settings;
  Map<String, dynamic> _apps = const {};
  String _appsError = '';
  bool _appsLoading = true;

  @override
  void initState() {
    super.initState();
    _loadApps();
  }

  // ---------------------------------------------------------------- how long her sounds are kept
  // v0.999.163: four cards (Never / 90 / 30 / 7 days) and how many are kept on this server; starred sounds always stay.
  static const List<(int, String, String)> _keeps = [
    (0, 'Never', 'Kept until you remove them'),
    (90, '90 days', 'Then removed by Hoola'),
    (30, '30 days', 'Then removed by Hoola'),
    (7, '7 days', 'Then removed by Hoola'),
  ];

  int get _keepDays => crInt(crMap(store.ov['settings'])['keep_days']);

  Future<void> _keep(int days) async {
    if (days == _keepDays) return;
    try {
      Map<String, dynamic> saved;
      if (VocalStore.debug) {
        VocalStore.debugAnswer('settings', {'keep_days': days});
        saved = {...crMap(store.ov['settings']), 'keep_days': days};
      } else {
        saved = await store.app.api!.vocalSettingsSave({'keep_days': days});
      }
      final st = crMap(saved['settings']).isNotEmpty ? crMap(saved['settings']) : saved;
      store.ov = {...store.ov, 'settings': st.isEmpty ? {...crMap(store.ov['settings']), 'keep_days': days} : st};
      store.tell();
      if (mounted) {
        crToast(context, days == 0 ? 'Your sounds are kept until you remove them.' : 'Sounds older than $days days will be deleted. Starred sounds stay.');
      }
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  Widget _keepSection(HoolaColors c) {
    final small = HoolaType.small(c).copyWith(fontSize: 12);
    final n = store.history.length, stars = store.history.where((h) => h['star'] == true).length;
    final u = crMap(store.ov['usage']), l = crMap(store.ov['limits']);
    final max = crInt(u['kept_max']) > 0 ? crInt(u['kept_max']) : (crInt(l['history']) > 0 ? crInt(l['history']) : 300);
    Widget card((int, String, String) k) {
      final on = k.$1 == _keepDays;
      return Semantics(
        container: true,
        button: true,
        selected: on,
        checked: on,
        label: 'Keep my sounds: ${k.$2}',
        excludeSemantics: true,
        onTap: () => _keep(k.$1),
        child: InkWell(
          onTap: () => _keep(k.$1),
          borderRadius: BorderRadius.circular(14),
          child: Container(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
            decoration: BoxDecoration(
              color: on ? c.accentSoft : c.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: on ? c.accent : c.line, width: on ? 2 : 1),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(k.$2, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 2),
              Text(k.$3, style: small),
            ]),
          ),
        ),
      );
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('What stays on this server, and for how long.', style: HoolaType.small(c).copyWith(fontSize: 13, color: c.ink2)),
      const SizedBox(height: 8),
      Row(children: [Expanded(child: card(_keeps[0])), const SizedBox(width: 8), Expanded(child: card(_keeps[1]))]),
      const SizedBox(height: 8),
      Row(children: [Expanded(child: card(_keeps[2])), const SizedBox(width: 8), Expanded(child: card(_keeps[3]))]),
      const SizedBox(height: 8),
      VocalBox(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Kept on this server · $n of $max sounds${stars > 0 ? ' · $stars kept with a star' : ''}',
              style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500)),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(value: (n / max).clamp(0, 1).toDouble(), minHeight: 5, backgroundColor: c.sunk, color: c.accent),
          ),
          const SizedBox(height: 6),
          Text('Past $max, the oldest sound without a star goes first. Your voices, your dictionary and starred sounds always stay.',
              style: small),
        ]),
      ),
    ]);
  }

  // ---------------------------------------------------------------- for her own apps
  Future<void> _loadApps() async {
    try {
      final r = VocalStore.debug ? crMap(VocalStore.debugData!['apps']) : await store.app.api?.vocalApps();
      if (mounted) {
        setState(() {
          _apps = r ?? const {};
          _appsError = '';
        });
      }
    } catch (e) {
      if (mounted) setState(() => _appsError = crError(e));
    }
    if (mounted) setState(() => _appsLoading = false);
  }

  void _failed(Object e) {
    if (!mounted) return;
    if (e is ApiException && e.status == 422) setState(() => _appsError = e.message);
    vocalError(context, store, e);
  }

  Future<String?> _ask(String title, String hint, {String body = '', TextInputType type = TextInputType.text, String yes = 'Make it'}) =>
      showDialog<String>(context: context, builder: (_) => _AskDialog(title: title, hint: hint, body: body, type: type, yes: yes));

  /// A key or a signing secret, shown this once: Copy, and the server's note.
  Future<void> _showOnce(String title, String value, String note) => showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (ctx) {
          final c = HoolaColors.of(ctx);
          return AlertDialog(
            title: Text(title),
            content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(10)),
                child: SelectableText(value, style: HoolaType.body(c).copyWith(fontFamily: 'monospace', fontSize: 13)),
              ),
              const SizedBox(height: 10),
              Text(note.isEmpty ? 'Copy it now. It is shown only once.' : note, style: HoolaType.small(c).copyWith(color: c.ink2)),
            ]),
            actions: [
              TextButton(
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: value));
                  if (ctx.mounted) crToast(ctx, 'Copied');
                },
                child: const Text('Copy'),
              ),
              TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Done')),
            ],
          );
        },
      );

  Future<void> _newKey() async {
    final name = await _ask('A key for your app', 'Its name, like My shop app',
        body: 'Your app uses this key to make speech with your voices. It is shown once.');
    if (name == null || !mounted) return;
    try {
      final r = VocalStore.debug
          ? VocalStore.debugAnswer('app_key', {'name': name})
          : await store.app.api!.vocalAppKeyNew(name.isEmpty ? 'My app' : name);
      if (!mounted) return;
      if (crS(r['key']).isNotEmpty) await _showOnce('Your new key', crS(r['key']), crS(r['note']));
      await _loadApps();
    } catch (e) {
      _failed(e);
    }
  }

  Future<void> _dropKey(Map<String, dynamic> k) async {
    final ok = await vocalConfirm(context, 'Remove this key?', 'Apps that use “${crS(k['name'])}” stop working at once. This cannot be undone.',
        'Remove');
    if (ok != true || !mounted) return;
    try {
      if (VocalStore.debug) {
        VocalStore.debugAnswer('app_key_delete', {'id': crS(k['id'])});
      } else {
        await store.app.api!.vocalAppKeyDelete(crS(k['id']));
      }
      await _loadApps();
    } catch (e) {
      _failed(e);
    }
  }

  Future<void> _newHook() async {
    final url = await _ask('A webhook', 'https://your-app.example/hoola', type: TextInputType.url, yes: 'Add it',
        body: 'Hoola tells this address when a sound or a dub is ready, signed with a secret shown once.');
    if (url == null || url.isEmpty || !mounted) return;
    try {
      final r = VocalStore.debug ? VocalStore.debugAnswer('app_hook', {'url': url}) : await store.app.api!.vocalAppHookNew(url);
      if (!mounted) return;
      if (crS(r['secret']).isNotEmpty) await _showOnce('Your signing secret', crS(r['secret']), crS(r['note']));
      await _loadApps();
    } catch (e) {
      _failed(e);
    }
  }

  Future<void> _dropHook(Map<String, dynamic> h) async {
    final ok = await vocalConfirm(context, 'Remove this webhook?', 'Hoola stops telling ${crS(h['url'])}. This cannot be undone.', 'Remove');
    if (ok != true || !mounted) return;
    try {
      if (VocalStore.debug) {
        VocalStore.debugAnswer('app_hook_delete', {'id': crS(h['id'])});
      } else {
        await store.app.api!.vocalAppHookDelete(crS(h['id']));
      }
      await _loadApps();
    } catch (e) {
      _failed(e);
    }
  }

  Future<void> _testHook(Map<String, dynamic> h) async {
    try {
      final r = VocalStore.debug
          ? VocalStore.debugAnswer('app_hook_test', {'id': crS(h['id'])})
          : await store.app.api!.vocalAppHookTest(crS(h['id']));
      if (!mounted) return;
      final st = crS(r['last_status']);
      crToast(context, st.isEmpty ? 'The test was sent.' : 'The test was sent. Your app answered: $st');
      await _loadApps();
    } catch (e) {
      _failed(e);
    }
  }

  Widget _appsSection(HoolaColors c) {
    final keys = crList(_apps['keys']);
    final hooks = crList(_apps['hooks']);
    final doors = crList(_apps['doors']);
    final maxKeys = crInt(_apps['max_keys']);
    final maxHooks = crInt(_apps['max_hooks']);
    final rate = crInt(_apps['rate_hour']);
    final small = HoolaType.small(c).copyWith(fontSize: 12);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('Keys let your own app or website make speech with your voices. Webhooks tell your app when a sound is ready.',
          style: HoolaType.small(c).copyWith(fontSize: 13, color: c.ink2)),
      const SizedBox(height: 8),
      if (_appsError.isNotEmpty) Padding(padding: const EdgeInsets.only(bottom: 8), child: CrNote(_appsError, glyph: CrGlyph.info)),
      if (_appsLoading)
        const Padding(padding: EdgeInsets.all(12), child: Center(child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))))
      else ...[
        VocalLabel('Keys', note: maxKeys > 0 ? '${keys.length} of $maxKeys' : '${keys.length}'),
        VocalBox(
          padding: const EdgeInsets.fromLTRB(14, 4, 4, 4),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            for (final k in keys)
              Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(crS(k['name']).isEmpty ? 'My app' : crS(k['name']), style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                    Text([
                      'Ends in ${crS(k['last4'])}',
                      '${crInt(k['calls'])} call${crInt(k['calls']) == 1 ? '' : 's'}',
                      if (crS(k['used_at']).isNotEmpty) 'last used ${crWhen(vocalEpoch(k['used_at']))}',
                    ].join(' · '), style: small),
                  ]),
                ),
                VocalIconButton(label: 'Remove the key ${crS(k['name'])}', glyph: CrGlyph.trash, onTap: () => _dropKey(k)),
              ]),
            if (keys.isEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 10), child: Text('No keys yet.', style: small)),
            Align(
              alignment: Alignment.centerLeft,
              child: VocalChip(label: 'Make a key', onTap: maxKeys > 0 && keys.length >= maxKeys ? null : _newKey),
            ),
          ]),
        ),
        const SizedBox(height: 12),
        VocalLabel('Webhooks', note: maxHooks > 0 ? '${hooks.length} of $maxHooks' : '${hooks.length}'),
        VocalBox(
          padding: const EdgeInsets.fromLTRB(14, 4, 4, 4),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            for (final h in hooks)
              Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(crS(h['url']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                    Text([
                      if (h['events'] is List) (h['events'] as List).map(crS).join(', '),
                      if (crS(h['last_status']).isNotEmpty) 'last answer ${crS(h['last_status'])}' else 'not called yet',
                    ].where((x) => x.isNotEmpty).join(' · '), maxLines: 2, overflow: TextOverflow.ellipsis, style: small),
                  ]),
                ),
                VocalChip(label: 'Test', onTap: () => _testHook(h)),
                VocalIconButton(label: 'Remove the webhook ${crS(h['url'])}', glyph: CrGlyph.trash, onTap: () => _dropHook(h)),
              ]),
            if (hooks.isEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 10), child: Text('No webhooks yet.', style: small)),
            Align(
              alignment: Alignment.centerLeft,
              child: VocalChip(label: 'Add a webhook', onTap: maxHooks > 0 && hooks.length >= maxHooks ? null : _newHook),
            ),
          ]),
        ),
        if (doors.isNotEmpty) ...[
          const SizedBox(height: 10),
          Text('What your app can call', style: small.copyWith(fontWeight: FontWeight.w600)),
          for (final d in doors)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text('${crS(d['method'])} ${crS(d['path'])} · ${crS(d['does'])}', style: small),
            ),
        ],
        if (crS(_apps['signature']).isNotEmpty) ...[
          const SizedBox(height: 6),
          Text('Each webhook call is signed: ${crS(_apps['signature'])}', style: small),
        ],
        if (rate > 0) ...[
          const SizedBox(height: 4),
          Text('Up to $rate calls an hour for each key.', style: small),
        ],
      ],
    ]);
  }

  String _state(Map<String, dynamic> e) => switch (crS(e['state'])) {
        'ready' => 'Ready',
        'needs_key' => 'Not set up',
        'off' => 'Off',
        '' => 'Ready',
        _ => 'Not set up',
      };

  String _engineName(String id) => switch (id) {
        'auto' => 'Hoola Auto',
        'gemini' => 'Gemini voice',
        'eleven' => 'ElevenLabs (premium)',
        _ => id,
      };

  Future<void> _engine() async {
    final ids = ['auto', for (final e in store.engines) if (crS(e['state']) == 'ready' && crS(e['id']) != 'server') crS(e['id'])];
    final v = await crPick(context, 'Engine', [for (final i in ids) _engineName(i)], _engineName(vs.engine),
        notes: const {'Hoola Auto': 'Picks the engine for each job'});
    if (v == null || !mounted) return;
    setState(() => vs.engine = ids.firstWhere((i) => _engineName(i) == v, orElse: () => 'auto'));
    await _save();
  }

  Future<void> _save() async {
    try {
      await vs.save(store);
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
  }

  Future<void> _lang() async {
    final v = await showModalBottomSheet<String>(context: context, showDragHandle: true, isScrollControlled: true,
        builder: (_) => CrHueScope(hue: CrHue.voice, child: VocalLanguageSheet(store: store, current: vs.lang)));
    if (v == null || !mounted) return;
    setState(() => vs.lang = v);
    await _save();
  }

  Future<void> _takes() async {
    final v = await crPick(context, 'Takes', vocalTakeChoices(store), '${vs.takes}');
    if (v == null || !mounted) return;
    setState(() => vs.takes = int.tryParse(v) ?? 2);
    await _save();
  }

  @override
  Widget build(BuildContext context) {
    final body = ListenableBuilder(
      listenable: store,
      builder: (context, _) {
        final c = HoolaColors.of(context);
        final prices = crList(store.ov['prices']);
        return ListView(padding: const EdgeInsets.fromLTRB(16, 14, 16, 24), children: [
          Text('How Hoola Vocal works for you, on every device.', style: HoolaType.small(c).copyWith(fontSize: 14, color: c.ink2)),
          const SizedBox(height: 14),
          const VocalLabel('Defaults'),
          Text('Every page starts from these. You can change them for one sound any time.', style: HoolaType.small(c).copyWith(fontSize: 13, color: c.ink2)),
          const SizedBox(height: 8),
          VocalRows([
            ('Language', vs.lang == 'auto' ? 'Auto, from my words' : store.langNative(vs.lang), _lang),
            ('Voice', vs.voiceName(store), null),
            ('Takes', '${vs.takes}', _takes),
            ('Engine', _engineName(vs.engine), _engine),
          ]),
          const SizedBox(height: 18),
          const VocalLabel('Engines'),
          Text('Hoola Auto picks the engine for each job. You can pin one.', style: HoolaType.small(c).copyWith(fontSize: 13, color: c.ink2)),
          const SizedBox(height: 8),
          VocalBox(
            padding: const EdgeInsets.fromLTRB(14, 6, 14, 6),
            child: Column(children: [
              for (final e in store.engines)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Row(children: [
                    Container(width: 8, height: 8, decoration: BoxDecoration(color: _state(e) == 'Ready' ? c.ok : c.ink3, shape: BoxShape.circle)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(crS(e['name']), style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                        if (crS(e['does']).isNotEmpty) Text(crS(e['does']), style: HoolaType.small(c).copyWith(fontSize: 12)),
                      ]),
                    ),
                    Text(_state(e), style: HoolaType.small(c).copyWith(fontSize: 12, color: _state(e) == 'Ready' ? c.ok : c.ink2)),
                  ]),
                ),
              if (store.engines.isEmpty) Text('No engine is listed by this server.', style: HoolaType.small(c)),
            ]),
          ),
          const SizedBox(height: 18),
          const VocalLabel('What things cost'),
          if (prices.isEmpty)
            Text('The price shows before every job.', style: HoolaType.small(c))
          else
            VocalRows([
              for (final p in prices)
                (crS(p['job']), crInt(p['credits']) > 0 ? '${crInt(p['credits'])} credit${crInt(p['credits']) == 1 ? '' : 's'}' : 'Free', null),
            ]),
          const SizedBox(height: 6),
          Text('You always see the price before you tap.', style: HoolaType.small(c).copyWith(fontSize: 12)),
          const SizedBox(height: 18),
          const VocalLabel('This month'),
          VocalCredits(store: store),
          const SizedBox(height: 18),
          const VocalLabel('Keep my sounds'),
          _keepSection(c),
          const SizedBox(height: 18),
          const VocalLabel('For your own apps'),
          _appsSection(c),
          const SizedBox(height: 18),
          const VocalLabel('Pronunciation'),
          VocalRows([('Dictionary', '${crList(store.ov['rules']).length} words', widget.onDictionary)]),
          const SizedBox(height: 18),
          const VocalLabel('The rules Hoola keeps'),
          for (final r in (store.ov['rules_kept'] is List ? (store.ov['rules_kept'] as List).map(crS).toList()
              : const ['Every file carries an AI mark.', 'The price shows before every job; nothing paid runs without your tap.']))
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Padding(padding: const EdgeInsets.only(top: 3), child: Icon(Icons.check_rounded, size: 16, color: c.ok)),
                const SizedBox(width: 8),
                Expanded(child: Text(r, style: HoolaType.small(c).copyWith(color: c.ink2))),
              ]),
            ),
        ]);
      },
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Settings', body: body);
  }
}

/// One line asked in a dialog (it owns its text box, so the box lives as long as the dialog).
class _AskDialog extends StatefulWidget {
  const _AskDialog({required this.title, required this.hint, required this.body, required this.type, required this.yes});
  final String title, hint, body, yes;
  final TextInputType type;
  @override
  State<_AskDialog> createState() => _AskDialogState();
}

class _AskDialogState extends State<_AskDialog> {
  final _ctl = TextEditingController();

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: Text(widget.title),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (widget.body.isNotEmpty) Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(widget.body)),
          TextField(controller: _ctl, autofocus: true, keyboardType: widget.type, maxLength: 300,
              decoration: InputDecoration(hintText: widget.hint)),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(context).pop(_ctl.text.trim()), child: Text(widget.yes)),
        ],
      );
}
