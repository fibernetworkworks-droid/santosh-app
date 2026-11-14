// v0.912 CREATE NATIVE: the moving-picture screens of claude.ai/artifact/SARfWkfWm8ZtmmnAcU8dYn - Video (3), Director
// (4: the film list, a new film, and one film), and the Video editor (8). Video and Director drive the Video Studio
// (/api/studio) exactly as the console does: one call writes the shot plan, and every paid step becomes a price card
// that waits for her Haan (studioDecide carries the fingerprint proof); the Free preview costs nothing. The editor is
// the Video Editor (/api/video/jobs): her own clips in order, what to do in words, changes in words.
import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import '../shell/hoola_settings.dart' show hoolaOpenNew;
import '../video_editor.dart' show VideoPlayScreen;
import 'create_kit.dart';
import 'create_make.dart' show crUpload;

const _cams = [
  ('Auto', '', 'Hoola picks the move'),
  ('Static', 'the camera holds still on a tripod', 'The camera holds still'),
  ('Dolly in', 'slow dolly in towards the subject', 'Slow move towards the subject'),
  ('Dolly out', 'slow dolly out that reveals the scene', 'A slow move back that reveals the scene'),
  ('Crash zoom', 'a sudden fast zoom into the subject', 'A sudden fast zoom'),
  ('Orbit', 'the camera orbits around the subject', 'Circles around the subject'),
  ('Crane up', 'a crane shot rising up and over the scene', 'Rises up and over the scene'),
  ('Tracking', 'a tracking shot moving alongside the subject', 'Moves alongside the subject'),
  ('Pan', 'smooth slow pan across the scene', 'Turns slowly across the scene'),
  ('Drone', 'a high aerial drone shot moving forward', 'A high flight forward'),
  ('Handheld', 'natural handheld camera, slight movement', 'A light, human wobble'),
  ('Low angle', 'a low hero angle looking up, slow push in', 'Looks up at the hero'),
];
const _secs = [4, 5, 6, 8, 10, 12, 15];
const _spoken = ['Hindi', 'Hinglish', 'English', 'Marathi', 'Tamil', 'Telugu', 'Bengali', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi'];
String _qualityOf(String res) => {'360p': 'draft', '480p': 'draft', '540p': 'draft', '720p': 'draft', '768p': 'draft', '1080p': 'final'}[res] ?? 'premium';

Future<void> _play(BuildContext context, Santosh app, String url, String title) async {
  final api = app.api;
  if (api == null || url.isEmpty) return;
  await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => VideoPlayScreen(url: api.absolute(url), title: title)));
}

/// Her Haan / Not now on a studio price card (the fingerprint, when she set one, is asked by the app first).
Future<bool> crDecide(BuildContext context, Santosh app, String approvalId, bool yes) async {
  final api = app.api;
  if (api == null) return false;
  try {
    await api.studioDecide(approvalId, yes);
    if (context.mounted) crToast(context, yes ? 'Started. Nothing more is spent without you.' : 'Declined. Nothing was spent.');
    return true;
  } catch (e) {
    if (context.mounted) crToast(context, crError(e));
    return false;
  }
}

String _approvalWhat(Map<String, dynamic> a) => switch (crS(a['kind'])) {
      'keyframes' => 'Paint ${crInt(a['shots'])} opening ${crInt(a['shots']) == 1 ? 'picture' : 'pictures'}',
      'character' => 'Cast ${crS(a['name']).isEmpty ? 'a character' : crS(a['name'])}',
      'music' => 'Music for the film',
      _ => crInt(a['shots']) > 0
          ? 'Make ${crInt(a['shots'])} ${crInt(a['shots']) == 1 ? 'shot' : 'shots'} · ${crInt(a['seconds'])} s'
          : 'Make the video',
    };

/// The price card on a film or a clip: what it is, the rupees, Haan / Not now.
class CrApprovalCard extends StatefulWidget {
  const CrApprovalCard({super.key, required this.app, required this.approval, required this.onDone});
  final Santosh app;
  final Map<String, dynamic> approval;
  final VoidCallback onDone;
  @override
  State<CrApprovalCard> createState() => _CrApprovalCardState();
}

class _CrApprovalCardState extends State<CrApprovalCard> {
  bool _busy = false;
  Future<void> _go(bool yes) async {
    setState(() => _busy = true);
    final ok = await crDecide(context, widget.app, crS(widget.approval['id']), yes);
    if (mounted) setState(() => _busy = false);
    if (ok) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final a = widget.approval;
    final inr = (a['inr'] as num?) ?? 0;
    return CrCard(
      edge: c.warn.withOpacity(.6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(color: c.warnSoft, borderRadius: BorderRadius.circular(12)),
              child: Text('Waiting for your Haan', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: HoolaType.label(c).copyWith(color: c.warn)),
            ),
          ),
          const SizedBox(width: 10),
          Text(crRupees(inr), style: HoolaType.title(c).copyWith(fontSize: 18)),
        ]),
        const SizedBox(height: 10),
        Text(_approvalWhat(a), style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: 2),
        Text('You are never charged more than this price.', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: CrQuiet(label: 'Not now', height: 48, onTap: _busy ? null : () => _go(false), expand: true)),
          const SizedBox(width: 8),
          Expanded(flex: 3, child: CrMain(label: 'Haan · ${crRupees(inr)}', height: 48, busy: _busy, onTap: () => _go(true))),
        ]),
      ]),
    );
  }
}

/// Polls the studio while something is planning, working or waiting.
mixin _StudioPoll<T extends StatefulWidget> on State<T> {
  Timer? _timer;
  CreateStore get pollStore;
  bool get pollWanted;
  void startPolling() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) async {
      if (!pollWanted) return;
      await pollStore.reloadStudio();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}

// ------------------------------------------------------------------------------------------------ 3 · Video
class CreateVideo extends StatefulWidget {
  const CreateVideo({super.key, required this.store, this.prompt = ''});
  final CreateStore store;
  final String prompt;
  @override
  State<CreateVideo> createState() => _CreateVideoState();
}

class _CreateVideoState extends State<CreateVideo> with _StudioPoll<CreateVideo> {
  late final _q = TextEditingController(text: widget.prompt);
  String _cam = 'Auto', _aspect = '9:16', _res = '720p', _lang = 'Hindi', _model = '', _auto = 'quality';
  int _sec = 3, _takes = 1;   // index into _secs (8 s)
  bool _audio = true, _busy = false, _improving = false;
  Map<String, dynamic>? _price;
  String _priceErr = '';
  Timer? _priceT;
  int _priceN = 0;

  @override
  CreateStore get pollStore => widget.store;
  @override
  bool get pollWanted => _clips.any((p) => p['planning'] == true || p['working'] == true || crList(p['approvals']).isNotEmpty);

  List<Map<String, dynamic>> get _clips => widget.store.films.where((p) => crS(p['project']).startsWith('Clip ')).toList();

  @override
  void initState() {
    super.initState();
    _askPrice();
    startPolling();
  }

  @override
  void dispose() {
    _priceT?.cancel();
    _q.dispose();
    super.dispose();
  }

  void _askPrice() {
    _priceT?.cancel();
    final n = ++_priceN;
    _priceT = Timer(const Duration(milliseconds: 280), () async {
      final api = widget.store.app.api;
      if (api == null) return;
      try {
        final r = crMap(await api.call('POST', '/api/studio/price', body: {
          'model': _model, 'seconds': _secs[_sec], 'resolution': _res, 'audio': _audio, 'takes': _takes, 'auto': _auto,
        }));
        if (n == _priceN && mounted) setState(() {
          _price = r;
          _priceErr = '';
        });
      } catch (e) {
        if (n == _priceN && mounted) setState(() => _priceErr = crError(e));
      }
    });
  }

  void _set(VoidCallback f) {
    setState(f);
    _askPrice();
  }

  String get _modelName {
    if (_model.isEmpty) return 'Hoola Auto · ${{'quality': 'best quality', 'value': 'best value', 'cheap': 'lowest price'}[_auto]}';
    final m = crList(widget.store.studio['models']).firstWhere((m) => m['model'] == _model, orElse: () => {});
    return crS(m['label']).isEmpty ? _model : crS(m['label']);
  }

  Future<void> _pickModel() async {
    final c = HoolaColors.of(context);
    final models = crList(widget.store.studio['models']);
    final v = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * .75),
          child: ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(8, 0, 8, 16), children: [
            Padding(padding: const EdgeInsets.fromLTRB(14, 0, 14, 8), child: Text('Model', style: HoolaType.heading(c))),
            for (final a in const [('quality', 'Hoola Auto · best quality', 'Picks the best ready model for each shot'),
              ('value', 'Hoola Auto · best value', 'Good quality at a fair price'),
              ('cheap', 'Hoola Auto · lowest price', 'The cheapest ready model')])
              ListTile(
                minVerticalPadding: 12,
                title: Text(a.$2, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                subtitle: Text(a.$3, style: HoolaType.small(c)),
                trailing: _model.isEmpty && _auto == a.$1 ? CrIcon(CrGlyph.check, size: 18, color: c.ink) : null,
                onTap: () => Navigator.of(ctx).pop('auto:${a.$1}'),
              ),
            if (models.isNotEmpty) Divider(color: c.line),
            for (final m in models)
              ListTile(
                minVerticalPadding: 12,
                enabled: m['ready'] == true,
                title: Text(crS(m['label']), style: HoolaType.body(c)),
                subtitle: Text(
                    m['ready'] == true
                        ? (m['inr_per_second'] is num ? 'About ${crRupees(m['inr_per_second'] as num)} a second' : 'Ready')
                        : 'Not switched on on the server yet',
                    style: HoolaType.small(c)),
                trailing: _model == m['model'] ? CrIcon(CrGlyph.check, size: 18, color: c.ink) : null,
                onTap: () => Navigator.of(ctx).pop(crS(m['model'])),
              ),
          ]),
        ),
      ),
    );
    if (v == null) return;
    _set(() {
      if (v.startsWith('auto:')) {
        _model = '';
        _auto = v.substring(5);
      } else {
        _model = v;
      }
    });
  }

  Future<void> _improve() async {
    final api = widget.store.app.api;
    if (api == null || _q.text.trim().isEmpty) {
      crToast(context, 'Write a few words first, then Improve makes them richer.');
      return;
    }
    setState(() => _improving = true);
    try {
      final r = await api.studioImprove(_q.text.trim(), _lang, _secs[_sec]);
      if (crS(r['brief']).isNotEmpty) _q.text = crS(r['brief']);
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _improving = false);
  }

  Future<void> _create(bool preview) async {
    final api = widget.store.app.api;
    var brief = _q.text.trim();
    if (api == null) return;
    if (brief.isEmpty) {
      crToast(context, 'Describe the shot first.');
      return;
    }
    final cam = _cams.firstWhere((x) => x.$1 == _cam).$2;
    if (cam.isNotEmpty) brief += '\nCamera: $cam.';
    final now = DateTime.now();
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    final name = 'Clip ${now.day.toString().padLeft(2, '0')} ${months[now.month - 1]} '
        '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
    setState(() => _busy = true);
    try {
      await api.studioNew({
        'name': name, 'brief': brief, 'aspect': _aspect, 'seconds': _secs[_sec], 'language': _lang,
        'quality': preview ? 'draft' : _qualityOf(_res), 'model': _model, 'resolution': _res, 'auto': _auto,
        'then': preview ? 'preview' : 'generate', 'variants': preview ? 1 : _takes,
      });
      if (mounted) {
        crToast(context, preview
            ? 'Writing the shot plan, then your free preview starts below.'
            : 'Writing the shot plan (about a minute). The price card appears below; nothing is spent until you tap Haan.');
      }
      await widget.store.reloadStudio();
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final store = widget.store;
    final p = _price;
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) => CrPage(
        title: 'Video',
        onRefresh: () => store.reloadStudio(),
        action: Row(children: [
          CrQuiet(label: 'Free preview', onTap: _busy ? null : () => _create(true)),
          const SizedBox(width: 10),
          Expanded(child: CrMain(label: 'Create · see the price', busy: _busy, onTap: () => _create(false))),
        ]),
        children: [
          CrCard(
            onTap: _pickModel,
            child: Row(children: [
              const CrDisc(CrGlyph.spark),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Model', style: HoolaType.small(c).copyWith(fontSize: 12)),
                  Text(_modelName, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                  Text(_model.isEmpty ? 'Picks the best ready model for each shot' : 'Your pick for this clip',
                      style: HoolaType.small(c).copyWith(fontSize: 12.5)),
                ]),
              ),
              Text('Change', style: HoolaType.small(c).copyWith(color: c.ink2)),
              CrIcon(CrGlyph.chevron, size: 14, color: c.ink2),
            ]),
          ),
          const SizedBox(height: 12),
          CrTextCard(
            title: 'Describe your shot',
            controller: _q,
            max: 2000,
            lines: 4,
            hint: 'Steam rising from a clay kulhad of chai on a rainy balcony in Mumbai, warm evening light…',
            action: CrSmall(label: 'Improve', busy: _improving, onTap: _improve),
          ),
          crGap,
          CrLabel('Camera', note: _cams.firstWhere((x) => x.$1 == _cam).$3),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final x in _cams) CrChip(label: x.$1, on: x.$1 == _cam, onTap: () => setState(() => _cam = x.$1)),
          ]),
          crGap,
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const CrLabel('Shape'),
                CrSegment(options: const ['9:16', '16:9', '1:1'], picked: _aspect, height: 48, onPick: (v) => setState(() => _aspect = v)),
              ]),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const CrLabel('Length'),
                CrStepper(
                  value: '${_secs[_sec]} s',
                  height: 56,
                  label: 'length',
                  onLess: _sec > 0 ? () => _set(() => _sec--) : null,
                  onMore: _sec < _secs.length - 1 ? () => _set(() => _sec++) : null,
                ),
              ]),
            ),
          ]),
          crGap,
          CrSettings([
            CrSetting('Resolution', _res, const ['720p', '1080p'], (v) => _set(() => _res = v),
                notes: const {'720p': 'Draft quality, cheaper', '1080p': 'HD, for the final post'}),
            CrSetting('Sound', _audio ? 'On · voices and ambience' : 'Off · silent', const ['On · voices and ambience', 'Off · silent'],
                (v) => _set(() => _audio = v.startsWith('On'))),
            CrSetting('Takes', '$_takes ${_takes == 1 ? 'take' : 'takes'}', const ['1 take', '2 takes', '3 takes', '4 takes'],
                (v) => _set(() => _takes = int.parse(v.split(' ').first)),
                notes: const {'2 takes': 'Pick the one you like', '3 takes': 'Pick the one you like', '4 takes': 'Pick the one you like'}),
            CrSetting('Spoken lines in', _lang, _spoken, (v) => setState(() => _lang = v)),
          ]),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
            decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(18)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(
                  child: Text('This clip · ${_secs[_sec]} s · $_res${_audio ? ' · sound' : ''}${_takes > 1 ? ' · $_takes takes' : ''}',
                      style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14)),
                ),
                Text(p == null ? (_priceErr.isEmpty ? '…' : '–') : '≈ ${crRupees((p['inr'] as num?) ?? 0)}',
                    style: HoolaType.title(c).copyWith(fontSize: 16)),
              ]),
              if (p != null && crS(p['name']).isNotEmpty) ...[
                const SizedBox(height: 4),
                Text('${crS(p['name'])}${p['inr_per_s'] is num ? ' · ${crRupees(p['inr_per_s'] as num)} a second' : ''}',
                    style: HoolaType.small(c).copyWith(fontSize: 12.5)),
              ],
              if (p != null && p['ready'] == false) ...[
                const SizedBox(height: 4),
                Text('This model is not switched on on the server yet.', style: HoolaType.small(c).copyWith(color: c.warn)),
              ],
              if (_priceErr.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(_priceErr, style: HoolaType.small(c).copyWith(color: c.bad)),
              ],
              Divider(height: 20, color: c.line),
              Row(children: [
                CrIcon(CrGlyph.shield, size: 15, color: c.ink2),
                const SizedBox(width: 8),
                Expanded(child: Text('Nothing is spent until you tap Haan on the price card.', style: HoolaType.small(c).copyWith(color: c.ink2))),
              ]),
            ]),
          ),
          crGap,
          const CrLabel('Your clips', note: 'Newest first'),
          if (_clips.isEmpty) const CrNote('Clips you make appear here with their price card.', glyph: CrGlyph.info),
          for (final p in _clips.take(12)) ...[_ClipCard(store: store, p: p), const SizedBox(height: 10)],
        ],
      ),
    );
  }
}

/// One clip or film: price card when it waits, progress when it works, play + share when it is made.
class _ClipCard extends StatelessWidget {
  const _ClipCard({required this.store, required this.p});
  final CreateStore store;
  final Map<String, dynamic> p;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final app = store.app;
    final appr = crList(p['approvals']);
    final outs = crList(p['outputs']);
    final shots = crList(p['shots']);
    var url = outs.isEmpty ? '' : crS(outs.last['url']);
    if (url.isEmpty) {
      for (final s in shots) {
        final takes = crList(s['take_list']);
        final t = takes.firstWhere((x) => x['picked'] == true, orElse: () => takes.isEmpty ? {} : takes.last);
        if (crS(t['url']).isNotEmpty) {
          url = crS(t['url']);
          break;
        }
      }
    }
    final thumb = outs.isNotEmpty && crS(outs.last['thumb']).isNotEmpty
        ? crS(outs.last['thumb'])
        : shots.isNotEmpty ? crS(shots.first['keyframe']) : '';
    final state = p['planning'] == true
        ? 'Writing the shot plan…'
        : p['working'] == true
            ? (crMap(p['progress'])['pct'] != null ? 'Filming · ${crInt(crMap(p['progress'])['pct'])}%' : 'Filming…')
            : appr.isNotEmpty
                ? ''
                : url.isNotEmpty
                    ? '${crInt(p['seconds'])} s · ${crS(p['aspect'])}'
                    : crS(p['error']).isNotEmpty
                        ? crS(p['error'])
                        : 'Planned · ${crInt(p['seconds'])} s';
    return Column(children: [
      CrCard(
        padding: EdgeInsets.zero,
        onTap: url.isEmpty ? null : () => _play(context, app, url, crS(p['project'])),
        child: Column(children: [
          if (url.isNotEmpty || thumb.isNotEmpty)
            ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(21)),
              child: SizedBox(
                height: 190,
                width: double.infinity,
                child: Stack(fit: StackFit.expand, children: [
                  CrNetImage(app: app, url: thumb, seed: p['project']),
                  if (url.isNotEmpty)
                    Center(
                      child: Container(
                        width: 56,
                        height: 56,
                        decoration: BoxDecoration(color: Colors.black.withOpacity(.55), shape: BoxShape.circle),
                        alignment: Alignment.center,
                        child: const CrIcon(CrGlyph.play, size: 22, color: Colors.white),
                      ),
                    ),
                ]),
              ),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(crS(p['brief']).split('\n').first.isEmpty ? crS(p['project']) : crS(p['brief']).split('\n').first,
                      maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                  if (state.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(state, maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: HoolaType.small(c).copyWith(fontSize: 12.5, color: crS(p['error']).isNotEmpty && url.isEmpty ? c.bad : c.ink3)),
                  ],
                  if (p['planning'] == true || p['working'] == true) ...[
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(3),
                      child: LinearProgressIndicator(
                        minHeight: 5,
                        value: crMap(p['progress'])['pct'] is num ? (crMap(p['progress'])['pct'] as num) / 100 : null,
                        backgroundColor: c.sunk,
                        color: c.ink,
                      ),
                    ),
                  ],
                ]),
              ),
              if (url.isNotEmpty)
                CrRoundButton(glyph: CrGlyph.share, label: 'Save or share', onTap: () => _shareUrl(context, app, url, crS(p['project']))),
            ]),
          ),
        ]),
      ),
      for (final a in appr) ...[const SizedBox(height: 8), CrApprovalCard(app: app, approval: a, onDone: store.reloadStudio)],
    ]);
  }
}

Future<void> _shareUrl(BuildContext context, Santosh app, String url, String title) async {
  final api = app.api;
  if (api == null) return;
  crToast(context, 'Getting the video…');
  try {
    final bytes = await api.brandBytes(url);
    if (!context.mounted) return;
    await crShareBytes(context, bytes, '$title.mp4', 'video/mp4');
  } catch (e) {
    if (context.mounted) crToast(context, crError(e));
  }
}

// ------------------------------------------------------------------------------------------------ 4 · Director
class CreateDirector extends StatefulWidget {
  const CreateDirector({super.key, required this.store, this.brief = ''});
  final CreateStore store;
  final String brief;
  @override
  State<CreateDirector> createState() => _CreateDirectorState();
}

class _CreateDirectorState extends State<CreateDirector> with _StudioPoll<CreateDirector> {
  late final _q = TextEditingController(text: widget.brief);
  final _name = TextEditingController();
  String _aspect = '16:9', _len = '30 s', _lang = 'Hindi', _music = 'Cinematic';
  bool _busy = false;
  late bool _new = widget.brief.isNotEmpty || widget.store.films.where(_isFilm).isEmpty;

  @override
  CreateStore get pollStore => widget.store;
  @override
  bool get pollWanted => _films.any((p) => p['planning'] == true || p['working'] == true);

  static bool _isFilm(Map<String, dynamic> p) => !crS(p['project']).startsWith('Clip ');
  List<Map<String, dynamic>> get _films => widget.store.films.where(_isFilm).toList();

  @override
  void initState() {
    super.initState();
    startPolling();
  }

  @override
  void dispose() {
    _q.dispose();
    _name.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    final api = widget.store.app.api;
    final brief = _q.text.trim();
    if (api == null) return;
    if (brief.length < 8) {
      crToast(context, 'Write one line about the film first.');
      return;
    }
    var name = _name.text.trim();
    if (name.length < 2) {
      final w = brief.split(RegExp(r'\s+')).take(5).join(' ');
      name = w.length > 40 ? w.substring(0, 40) : w;
    }
    setState(() => _busy = true);
    try {
      final v = await api.studioNew({
        'name': name, 'brief': brief, 'aspect': _aspect, 'seconds': int.parse(_len.split(' ').first),
        'language': _lang, 'music': _music == 'No music' ? '' : _music.toLowerCase(), 'quality': 'final',
        'style': _aspect == '9:16' ? 'reel' : 'film',
      });
      await widget.store.reloadStudio();
      if (!mounted) return;
      setState(() {
        _busy = false;
        _new = false;
      });
      await hoolaOpenNew(context, widget.store.app, CreateFilm(store: widget.store, project: crS(v['project'])));
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        crToast(context, crError(e));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final store = widget.store;
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) => CrPage(
        title: 'Director',
        onRefresh: () => store.reloadStudio(),
        trailing: _new
            ? null
            : CrRoundButton(glyph: CrGlyph.plus, label: 'New film', onTap: () => setState(() => _new = true)),
        action: _new ? CrMain(label: 'Write the storyboard · free', busy: _busy, onTap: _start, glyph: CrGlyph.film) : null,
        children: [
          if (_new) ...[
            const CrIntro('A whole film from one line', 'Hoola writes the storyboard for free. Every paid step after it shows its price first.'),
            crGap,
            CrTextCard(title: 'What is the film about?', controller: _q, max: 2000, lines: 4,
                hint: 'A 30-second Diwali ad for my sweet shop: a family walks in at dusk, the owner hands over a box of kaju katli, diyas glow…'),
            const SizedBox(height: 10),
            TextField(
              controller: _name,
              maxLength: 60,
              buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null,
              style: HoolaType.body(c),
              decoration: InputDecoration(
                labelText: 'Film name (optional)',
                filled: true,
                fillColor: c.surface,
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.line)),
                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.ink)),
              ),
            ),
            crGap,
            const CrLabel('Shape'),
            CrSegment(options: const ['16:9', '9:16', '1:1'], picked: _aspect, onPick: (v) => setState(() => _aspect = v)),
            crGap,
            CrSettings([
              CrSetting('Length', _len, const ['15 s', '30 s', '45 s', '60 s', '90 s', '180 s'], (v) => setState(() => _len = v)),
              CrSetting('Language', _lang, _spoken, (v) => setState(() => _lang = v)),
              CrSetting('Music', _music, const ['Cinematic', 'Festive', 'Upbeat', 'Calm', 'Corporate', 'Lofi', 'No music'],
                  (v) => setState(() => _music = v), notes: const {'No music': 'Add it later if you like'}),
            ]),
            const SizedBox(height: 14),
            const CrNote('The storyboard is free. Cast, pictures, shots and music each show a price card first.'),
            if (_films.isNotEmpty) ...[
              crGap,
              Center(child: TextButton(onPressed: () => setState(() => _new = false), child: const Text('See your films'))),
            ],
          ] else ...[
            const CrIntro('Your films', 'Open one to see where it is and what comes next.'),
            crGap,
            for (final p in _films) ...[_FilmRow(store: store, p: p), const SizedBox(height: 10)],
          ],
        ],
      ),
    );
  }
}

String filmPhase(Map<String, dynamic> p) {
  if (p['planning'] == true) return 'Writing the storyboard…';
  if (crList(p['approvals']).isNotEmpty) return 'Waiting for your Haan';
  if (p['working'] == true) return 'Working on it…';
  if (crList(p['outputs']).any((o) => o['preview'] != true)) return 'Ready to watch';
  if (crList(p['shots']).isEmpty) return 'No storyboard yet';
  return '${crList(p['shots']).length} scenes · ${crInt(p['seconds'])} s';
}

class _FilmRow extends StatelessWidget {
  const _FilmRow({required this.store, required this.p});
  final CreateStore store;
  final Map<String, dynamic> p;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final shots = crList(p['shots']);
    final thumb = shots.map((s) => crS(s['keyframe'])).firstWhere((u) => u.isNotEmpty, orElse: () => '');
    final waits = crList(p['approvals']).isNotEmpty;
    return CrCard(
      edge: waits ? c.warn.withOpacity(.6) : null,
      onTap: () => hoolaOpenNew(context, store.app, CreateFilm(store: store, project: crS(p['project']))),
      child: Row(children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: SizedBox(width: 64, height: 80, child: CrNetImage(app: store.app, url: thumb, seed: p['project'])),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(crS(p['project']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 2),
            Text('${crS(p['aspect'])} · ${crS(p['language'])}', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
            const SizedBox(height: 4),
            Text(filmPhase(p), style: HoolaType.small(c).copyWith(fontSize: 12.5, color: waits ? c.warn : c.ink2, fontWeight: FontWeight.w500)),
          ]),
        ),
        CrIcon(CrGlyph.chevron, size: 16, color: c.ink3),
      ]),
    );
  }
}

// ------------------------------------------------------------------------------------------------ one film
class CreateFilm extends StatefulWidget {
  const CreateFilm({super.key, required this.store, required this.project});
  final CreateStore store;
  final String project;
  @override
  State<CreateFilm> createState() => _CreateFilmState();
}

List<String> _casting(Map<String, dynamic> v) => v['casting'] is List ? [for (final e in v['casting'] as List) '$e'] : const [];

const _steps = ['Brief', 'Storyboard', 'Cast', 'Pictures', 'Preview', 'Shots', 'Music', 'Final film'];

class _CreateFilmState extends State<CreateFilm> {
  Map<String, dynamic> _v = const {};
  String _err = '';
  bool _acting = false;
  Timer? _t;
  final _change = TextEditingController();

  Santosh get _app => widget.store.app;

  @override
  void initState() {
    super.initState();
    final d = CreateStore.debugData;
    if (d != null) {
      _v = widget.store.films.firstWhere((p) => p['project'] == widget.project, orElse: () => {});
    } else {
      _load();
      _t = Timer.periodic(const Duration(seconds: 4), (_) {
        if (_v['planning'] == true || _v['working'] == true || _casting(_v).isNotEmpty) _load();
      });
    }
  }

  @override
  void dispose() {
    _t?.cancel();
    _change.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final api = _app.api;
    if (api == null) return;
    try {
      final v = await api.studioProject(widget.project);
      if (mounted) setState(() {
        _v = v;
        _err = '';
      });
    } catch (e) {
      if (mounted) setState(() => _err = crError(e));
    }
  }

  Future<void> _act(Future<Object?> Function() f, [String said = '']) async {
    setState(() => _acting = true);
    try {
      await f();
      if (said.isNotEmpty && mounted) crToast(context, said);
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    await _load();
    unawaited(widget.store.reloadStudio());
    if (mounted) setState(() => _acting = false);
  }

  /// Where the film is, step by step (done / now / later), read from the studio's own view.
  List<int> _state() {
    final shots = crList(_v['shots']);
    final prefs = crMap(_v['prefs']);
    final outs = crList(_v['outputs']);
    final done = <bool>[
      crS(_v['brief']).isNotEmpty,
      shots.isNotEmpty,
      crList(_v['character_list']).isNotEmpty || prefs['cast_skip'] == true,
      shots.isNotEmpty && (crInt(_v['keyframes']) >= shots.length || prefs['pics_skip'] == true),
      outs.any((o) => o['preview'] == true) || shots.any((s) => s['picked'] != null),
      shots.isNotEmpty && shots.every((s) => s['picked'] != null && crS(s['quality']) != 'preview'),
      _v['music'] == true,
      outs.any((o) => o['preview'] != true),
    ];
    final now = done.indexWhere((d) => !d);
    return [for (var i = 0; i < done.length; i++) done[i] ? 2 : (i == now ? 1 : 0)];
  }

  (String, String, int, Future<Object?> Function()?) _next() {
    final n = crMap(_v['next']);
    final inr = crInt(n['inr']);
    final name = widget.project;
    return switch (crS(n['kind'])) {
      'plan' => ('Write the storyboard', 'Hoola writes the scenes, free.', 0,
          () => _app.api!.studioPlan(name, crS(_v['brief']), crInt(_v['seconds']) == 0 ? 30 : crInt(_v['seconds']))),
      'keyframes' => ('Paint the opening pictures', 'One picture a scene, so every shot starts right.', inr, () => _app.api!.studioKeyframes(name)),
      'generate' => ('Make the video shots', 'The real HD shots of every scene.', inr, () => _app.api!.studioGenerate(name, crS(_v['quality_pref']).isEmpty ? 'final' : crS(_v['quality_pref']))),
      'assemble' => ('Put the final film together', 'Joins the shots, music and words, free.', 0, () => _app.api!.studioAssemble(name)),
      'done' => ('Your film is ready', 'Watch it below, or change any scene.', 0, null),
      _ => ('Working on it', 'Hoola is making this step. It updates here by itself.', 0, null),
    };
  }

  Future<void> _addCast() async {
    final c = HoolaColors.of(context);
    final nameC = TextEditingController(), descC = TextEditingController();
    var voice = 'female';
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => Padding(
          padding: EdgeInsets.fromLTRB(20, 0, 20, 20 + MediaQuery.viewInsetsOf(ctx).bottom),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Add a character', style: HoolaType.heading(c)),
            const SizedBox(height: 4),
            Text('An AI character keeps the same face in every shot. A real person needs their permission.', style: HoolaType.small(c)),
            const SizedBox(height: 14),
            TextField(controller: nameC, decoration: const InputDecoration(labelText: 'Name')),
            const SizedBox(height: 10),
            TextField(controller: descC, minLines: 2, maxLines: 4, decoration: const InputDecoration(labelText: 'Looks like')),
            const SizedBox(height: 14),
            CrSegment(options: const ['Female voice', 'Male voice'], picked: voice == 'female' ? 'Female voice' : 'Male voice',
                onPick: (v) => set(() => voice = v.startsWith('Female') ? 'female' : 'male')),
            const SizedBox(height: 16),
            CrMain(label: 'Cast · see the price', height: 52, onTap: () => Navigator.of(ctx).pop(true)),
          ]),
        ),
      ),
    );
    if (ok == true && nameC.text.trim().isNotEmpty && descC.text.trim().isNotEmpty) {
      await _act(() => _app.api!.studioCharacter(widget.project,
          {'name': nameC.text.trim(), 'description': descC.text.trim(), 'voice': voice, 'kind': 'person'}), 'The price card is below.');
    }
    nameC.dispose();
    descC.dispose();
  }

  Future<void> _editScene(Map<String, dynamic> s, int n) async {
    final c = HoolaColors.of(context);
    final ctl = TextEditingController(text: crS(s['prompt']));
    final r = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(20, 0, 20, 20 + MediaQuery.viewInsetsOf(ctx).bottom),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Scene $n', style: HoolaType.heading(c)),
          const SizedBox(height: 4),
          Text('${crInt(s['duration'])} s${crS(s['camera']).isEmpty ? '' : ' · ${crS(s['camera'])}'}', style: HoolaType.small(c)),
          const SizedBox(height: 12),
          TextField(controller: ctl, minLines: 3, maxLines: 8, style: HoolaType.body(c),
              decoration: const InputDecoration(labelText: 'What happens in this scene')),
          const SizedBox(height: 16),
          Row(children: [
            Expanded(child: CrQuiet(label: 'Cancel', height: 52, expand: true, onTap: () => Navigator.of(ctx).pop())),
            const SizedBox(width: 10),
            Expanded(flex: 2, child: CrMain(label: 'Save the scene', height: 52, onTap: () => Navigator.of(ctx).pop(ctl.text.trim()))),
          ]),
        ]),
      ),
    );
    ctl.dispose();
    if (r != null && r.isNotEmpty && r != crS(s['prompt'])) {
      await _act(() => _app.api!.studioShot(widget.project, crS(s['id']), {'prompt': r}), 'Scene saved.');
    }
  }

  Future<void> _sendChange() async {
    final t = _change.text.trim();
    if (t.isEmpty) return;
    final ok = await _app.send('In my film "${widget.project}": $t');
    if (!mounted) return;
    if (ok) {
      _change.clear();
      crToast(context, 'Sent to ${_app.aName} in your chat. The film updates here when the change is made.');
    } else {
      crToast(context, 'That did not send. Check your internet and try again.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final v = _v;
    if (v.isEmpty) {
      return CrPage(title: 'Director', children: [
        const SizedBox(height: 80),
        Center(
          child: _err.isEmpty
              ? SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2))
              : CrNote(_err, glyph: CrGlyph.info),
        ),
      ]);
    }
    final st = _state();
    final now = st.indexOf(1);
    final shots = crList(v['shots']);
    final cast = crList(v['character_list']);
    final appr = crList(v['approvals']);
    final outs = crList(v['outputs']);
    final total = shots.fold<int>(0, (a, s) => a + crInt(s['duration']));
    final nx = _next();
    final prefs = crMap(v['prefs']);
    return CrPage(
      title: 'Director',
      onRefresh: _load,
      action: Container(
        height: 56,
        decoration: BoxDecoration(
          color: c.surface,
          borderRadius: BorderRadius.circular(28),
          border: Border.all(color: c.lineStrong),
          boxShadow: c.dark ? null : HoolaShadow.float(c),
        ),
        padding: const EdgeInsets.only(left: 18, right: 4),
        child: Row(children: [
          Expanded(
            child: TextField(
              controller: _change,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _sendChange(),
              style: HoolaType.body(c),
              decoration: InputDecoration(
                hintText: 'Change something… “make scene 3 brighter”',
                hintStyle: HoolaType.body(c).copyWith(color: c.ink3),
                border: InputBorder.none,
                filled: false,
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          Semantics(
            button: true,
            label: 'Send the change',
            excludeSemantics: true,
            onTap: _sendChange,
            child: Material(
              color: c.pill,
              shape: const CircleBorder(),
              child: InkWell(
                customBorder: const CircleBorder(),
                onTap: _sendChange,
                child: SizedBox(width: 48, height: 48,
                    child: Center(child: Transform.rotate(angle: -1.5708, child: CrIcon(CrGlyph.chevron, size: 18, color: c.onPill)))),
              ),
            ),
          ),
        ]),
      ),
      children: [
        Text('Film · ${total == 0 ? crInt(v['seconds']) : total} s · ${crS(v['aspect'])} · ${crS(v['language'])}',
            style: HoolaType.small(c).copyWith(fontSize: 12.5)),
        const SizedBox(height: 6),
        Semantics(
          header: true,
          child: Text(crS(v['project']),
              style: TextStyle(fontFamily: c.dark ? HoolaFont.serifDark : HoolaFont.serif, fontSize: 28, height: 1.2, color: c.ink)),
        ),
        if (crS(v['brief']).isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(crS(v['brief']), maxLines: 4, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14.5)),
        ],
        crGap,
        CrCard(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(
                child: Text(now < 0 ? 'All steps done' : 'Step ${now + 1} of 8 · ${_steps[now]}',
                    style: HoolaType.title(c).copyWith(fontSize: 14)),
              ),
              Text('${crRupees((v['spent_inr'] as num?) ?? 0)} spent', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
            ]),
            const SizedBox(height: 12),
            Row(children: [
              for (var i = 0; i < 8; i++) ...[
                if (i > 0) const SizedBox(width: 4),
                Expanded(
                  child: Container(
                    height: 5,
                    decoration: BoxDecoration(
                      color: st[i] == 2 ? c.ink : st[i] == 1 ? c.ink3 : c.sunk,
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                ),
              ],
            ]),
            const SizedBox(height: 10),
            for (var i = 0; i < 8; i++)
              if (st[i] != 0 || i == now + 1)
                SizedBox(
                  height: 36,
                  child: Row(children: [
                    Container(
                      width: 24,
                      height: 24,
                      decoration: BoxDecoration(
                        color: st[i] == 2 ? c.okSoft : st[i] == 1 ? c.pill : null,
                        shape: BoxShape.circle,
                        border: st[i] == 0 ? Border.all(color: c.lineStrong) : null,
                      ),
                      alignment: Alignment.center,
                      child: st[i] == 2
                          ? CrIcon(CrGlyph.check, size: 12, color: c.ok)
                          : Text('${i + 1}', style: HoolaType.label(c).copyWith(color: st[i] == 1 ? c.onPill : c.ink3)),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(_steps[i],
                          style: HoolaType.body(c).copyWith(
                              fontSize: 14, fontWeight: st[i] == 1 ? FontWeight.w600 : FontWeight.w400, color: st[i] == 0 ? c.ink3 : c.ink)),
                    ),
                  ]),
                ),
          ]),
        ),
        for (final a in appr) ...[const SizedBox(height: 12), CrApprovalCard(app: _app, approval: a, onDone: _load)],
        if (appr.isEmpty) ...[
          const SizedBox(height: 12),
          CrCard(
            edge: c.lineStrong,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const CrDisc(CrGlyph.film),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Next step', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
                    Text(nx.$1, style: HoolaType.title(c)),
                    const SizedBox(height: 2),
                    Text(nx.$2, style: HoolaType.small(c).copyWith(color: c.ink2, fontSize: 13.5)),
                  ]),
                ),
              ]),
              if (nx.$4 != null) ...[
                const SizedBox(height: 12),
                Row(children: [
                  if (crS(crMap(v['next'])['kind']) == 'generate' || crS(crMap(v['next'])['kind']) == 'keyframes')
                    CrQuiet(
                      label: crS(crMap(v['next'])['kind']) == 'keyframes' ? 'Skip pictures' : 'Free preview',
                      height: 48,
                      onTap: _acting
                          ? null
                          : () => crS(crMap(v['next'])['kind']) == 'keyframes'
                              ? _act(() => _app.api!.studioSettings(widget.project, {'pics_skip': true}), 'Going on without opening pictures.')
                              : _act(() => _app.api!.studioGenerate(widget.project, 'preview'), 'Making the free preview.'),
                    ),
                  if (crS(crMap(v['next'])['kind']) == 'generate' || crS(crMap(v['next'])['kind']) == 'keyframes') const SizedBox(width: 8),
                  Expanded(
                    child: CrMain(
                      label: nx.$3 > 0 ? 'See the price · about ${crRupees(nx.$3)}' : nx.$1,
                      height: 48,
                      busy: _acting,
                      onTap: () => _act(nx.$4!, nx.$3 > 0 ? 'The price card is above. Nothing is spent until you tap Haan.' : ''),
                    ),
                  ),
                ]),
              ] else if (v['working'] == true || v['planning'] == true) ...[
                const SizedBox(height: 12),
                ClipRRect(
                  borderRadius: BorderRadius.circular(3),
                  child: LinearProgressIndicator(
                    minHeight: 5,
                    value: crMap(v['progress'])['pct'] is num ? (crMap(v['progress'])['pct'] as num) / 100 : null,
                    backgroundColor: c.sunk,
                    color: c.ink,
                  ),
                ),
                const SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerLeft,
                  child: CrQuiet(label: 'Stop', height: 48, onTap: () => _act(() => _app.api!.studioCancel(widget.project), 'Stopped.')),
                ),
              ],
            ]),
          ),
        ],
        if (crS(v['error']).isNotEmpty || crS(v['pics_error']).isNotEmpty || crS(v['cast_error']).isNotEmpty) ...[
          const SizedBox(height: 12),
          CrNote([v['error'], v['pics_error'], v['cast_error']].map(crS).where((s) => s.isNotEmpty).join('\n'), glyph: CrGlyph.info),
        ],
        if (outs.isNotEmpty) ...[
          crGap,
          const CrLabel('Your film'),
          for (final o in outs.reversed) ...[
            CrCard(
              padding: EdgeInsets.zero,
              onTap: () => _play(context, _app, crS(o['url']), crS(v['project'])),
              child: Column(children: [
                ClipRRect(
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(21)),
                  child: SizedBox(
                    height: 200,
                    width: double.infinity,
                    child: Stack(fit: StackFit.expand, children: [
                      CrNetImage(app: _app, url: crS(o['thumb']), seed: o['name']),
                      Center(
                        child: Container(
                          width: 56,
                          height: 56,
                          decoration: BoxDecoration(color: Colors.black.withOpacity(.55), shape: BoxShape.circle),
                          alignment: Alignment.center,
                          child: const CrIcon(CrGlyph.play, size: 22, color: Colors.white),
                        ),
                      ),
                    ]),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
                  child: Row(children: [
                    Expanded(
                      child: Text('${o['preview'] == true ? 'Free preview' : 'Final film'} · ${crInt(o['seconds'])} s · ${crS(o['mb'])} MB',
                          style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                    ),
                    CrRoundButton(glyph: CrGlyph.share, label: 'Save or share', onTap: () => _shareUrl(context, _app, crS(o['url']), crS(v['project']))),
                  ]),
                ),
              ]),
            ),
            const SizedBox(height: 10),
          ],
        ],
        crGap,
        CrLabel('Cast', note: prefs['cast_skip'] == true ? 'No fixed characters' : 'Same face in every scene'),
        if (cast.isEmpty && _casting(v).isEmpty)
          CrCard(
            child: Row(children: [
              Expanded(child: Text('No characters yet', style: HoolaType.body(c).copyWith(color: c.ink2))),
              if (prefs['cast_skip'] != true)
                TextButton(onPressed: () => _act(() => _app.api!.studioSettings(widget.project, {'cast_skip': true})), child: const Text('Skip')),
              CrQuiet(label: 'Add', height: 48, onTap: _addCast),
            ]),
          )
        else
          SizedBox(
            height: 170,
            child: ListView(scrollDirection: Axis.horizontal, children: [
              for (final ch in cast)
                Padding(
                  padding: const EdgeInsets.only(right: 10),
                  child: SizedBox(
                    width: 104,
                    child: Column(children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(16),
                        child: SizedBox(width: 104, height: 130, child: CrNetImage(app: _app, url: crS(ch['image']), seed: ch['name'])),
                      ),
                      const SizedBox(height: 6),
                      Text(crS(ch['name']), maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: HoolaType.small(c).copyWith(color: c.ink, fontWeight: FontWeight.w500)),
                    ]),
                  ),
                ),
              for (final n in _casting(v))
                Padding(
                  padding: const EdgeInsets.only(right: 10),
                  child: SizedBox(
                    width: 104,
                    child: Column(children: [
                      Container(
                        width: 104,
                        height: 130,
                        decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(16)),
                        alignment: Alignment.center,
                        child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2)),
                      ),
                      const SizedBox(height: 6),
                      Text('Painting $n…', maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
                    ]),
                  ),
                ),
              Semantics(
                button: true,
                label: 'Add a character',
                excludeSemantics: true,
                onTap: _addCast,
                child: GestureDetector(
                  onTap: _addCast,
                  child: Container(
                    width: 104,
                    height: 130,
                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: c.lineStrong, width: 1.4)),
                    alignment: Alignment.center,
                    child: CrIcon(CrGlyph.plus, size: 22, color: c.ink2),
                  ),
                ),
              ),
            ]),
          ),
        crGap,
        CrLabel('Storyboard', note: shots.isEmpty ? '' : '${shots.length} scenes · tap one to change it'),
        if (shots.isEmpty)
          CrNote(v['planning'] == true ? 'Hoola is writing the scenes now.' : 'The storyboard appears here once it is written.', glyph: CrGlyph.info)
        else ...[
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: SizedBox(
              height: 8,
              child: Row(children: [
                for (var i = 0; i < shots.length; i++) ...[
                  if (i > 0) const SizedBox(width: 2),
                  Expanded(
                    flex: crInt(shots[i]['duration']).clamp(1, 60).toInt(),
                    child: Container(
                      color: shots[i]['picked'] != null ? c.ink : crS(shots[i]['keyframe']).isNotEmpty ? c.ink3 : c.lineStrong,
                    ),
                  ),
                ],
              ]),
            ),
          ),
          const SizedBox(height: 6),
          Row(children: [
            Text('0:00', style: HoolaType.small(c).copyWith(fontSize: 12)),
            const Spacer(),
            Text('0:${total.toString().padLeft(2, '0')}', style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
          const SizedBox(height: 12),
          for (var i = 0; i < shots.length; i++) ...[
            _SceneCard(app: _app, s: shots[i], n: i + 1, onTap: () => _editScene(shots[i], i + 1)),
            const SizedBox(height: 10),
          ],
        ],
        const SizedBox(height: 4),
        const CrNote('Every paid step shows its price first. Nothing is spent until you tap Haan. Tell Hoola what to change in plain words.'),
      ],
    );
  }
}

class _SceneCard extends StatelessWidget {
  const _SceneCard({required this.app, required this.s, required this.n, required this.onTap});
  final Santosh app;
  final Map<String, dynamic> s;
  final int n;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final phase = crS(s['phase']);
    final line = switch (phase) {
      'paint' => 'Painting the picture…',
      'video' => 'Filming${s['pct'] is num ? ' · ${crInt(s['pct'])}%' : '…'}',
      'queued' => 'Waiting its turn',
      'retrying' => 'Trying again',
      'lipsync' => 'Matching the lips',
      'failed' => crS(s['error']).isEmpty ? 'This shot did not work' : crS(s['error']),
      'done' => 'Shot made${crS(s['model_label']).isEmpty ? '' : ' · ${crS(s['model_label'])}'}',
      'pictured' => 'Picture ready',
      _ => 'Waiting to paint',
    };
    final text = crS(s['caption']).isNotEmpty ? crS(s['caption']) : crS(s['prompt']);
    return Semantics(
      button: true,
      label: 'Scene $n. $text. $line',
      excludeSemantics: true,
      onTap: onTap,
      child: CrCard(
        padding: const EdgeInsets.all(12),
        onTap: onTap,
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: SizedBox(
              width: 72,
              height: 96,
              child: Stack(fit: StackFit.expand, children: [
                CrNetImage(app: app, url: crS(s['keyframe']), seed: '${s['id']}'),
                Positioned(
                  left: 6,
                  top: 6,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                    decoration: BoxDecoration(color: Colors.black.withOpacity(.55), borderRadius: BorderRadius.circular(10)),
                    child: Text('$n', style: const TextStyle(color: Colors.white, fontSize: 12)),
                  ),
                ),
                if (phase == 'paint' || phase == 'video' || phase == 'queued')
                  Center(child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2))),
              ]),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(text.split('\n').first, maxLines: 3, overflow: TextOverflow.ellipsis,
                  style: HoolaType.body(c).copyWith(fontSize: 14, height: 1.45)),
              if (crS(s['dialogue']).isNotEmpty) ...[
                const SizedBox(height: 4),
                Text('“${crS(s['dialogue'])}”', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: HoolaType.small(c).copyWith(color: c.ink2, fontStyle: FontStyle.italic)),
              ],
              const SizedBox(height: 4),
              Text('${crInt(s['duration'])} s${crS(s['camera']).isEmpty ? '' : ' · ${crS(s['camera'])}'} · $line',
                  maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: HoolaType.small(c).copyWith(fontSize: 12, color: phase == 'failed' ? c.bad : c.ink3)),
            ]),
          ),
        ]),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ 8 · Video editor
const _platforms = [
  ('reel', 'Instagram Reel', 30),
  ('short', 'YouTube Short', 40),
  ('status', 'WhatsApp Status', 30),
  ('youtube', 'YouTube video', 120),
];
const _quick = ['Cut the silences', 'Hindi captions', 'Make it 9:16', 'Beat-synced cuts', 'Brighter colours', 'Shorter intro'];

class CreateEditor extends StatefulWidget {
  const CreateEditor({super.key, required this.store, this.brief = ''});
  final CreateStore store;
  final String brief;
  @override
  State<CreateEditor> createState() => _CreateEditorState();
}

class _CreateEditorState extends State<CreateEditor> {
  late final _q = TextEditingController(text: widget.brief);
  final _revise = TextEditingController();
  final List<({String id, String name})> _clips = [];
  final Set<String> _asks = {};
  String _platform = 'reel', _len = 'Auto';
  bool _captions = true, _busy = false, _adding = false;
  List<Map<String, dynamic>> _jobs = const [];
  Timer? _t;

  @override
  void initState() {
    super.initState();
    _load();
    _t = Timer.periodic(const Duration(seconds: 4), (_) {
      if (_jobs.any((j) => !const ['done', 'failed', 'cancelled'].contains(crS(j['status'])))) _load();
    });
  }

  @override
  void dispose() {
    _t?.cancel();
    _q.dispose();
    _revise.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final api = widget.store.app.api;
    if (api == null || CreateStore.debugData != null) return;
    try {
      final r = await api.videoJobs();
      if (mounted) setState(() => _jobs = crList(r['jobs']));
    } catch (_) {}
  }

  Future<void> _add() async {
    if (_clips.length >= 8) return;
    setState(() => _adding = true);
    final r = await crUpload(context, widget.store, FileType.video);
    if (!mounted) return;
    setState(() {
      _adding = false;
      if (r != null) _clips.add((id: r.id, name: r.name));
    });
  }

  Future<void> _make() async {
    final api = widget.store.app.api;
    if (api == null) return;
    if (_clips.isEmpty) {
      crToast(context, 'Add your clips first.');
      return;
    }
    final brief = [_q.text.trim(), ..._asks].where((s) => s.isNotEmpty).join('. ');
    if (brief.isEmpty) {
      crToast(context, 'Say what Hoola should do, or tap a quick ask.');
      return;
    }
    setState(() => _busy = true);
    try {
      await api.videoStart(_clips.map((c) => c.id).toList(), brief,
          platform: _platform,
          lengthS: _len == 'Auto' ? null : int.parse(_len.split(' ').first),
          captions: _captions,
          title: brief.length > 48 ? brief.substring(0, 48) : brief,
          conversationId: widget.store.app.conversationId ?? '');
      if (mounted) crToast(context, 'Editing now. The new version appears here and in your chat.');
      await _load();
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _change(Map<String, dynamic> j) async {
    final t = _revise.text.trim();
    if (t.isEmpty) return;
    try {
      await widget.store.app.api!.videoRevise(crS(j['id']), t);
      _revise.clear();
      if (mounted) crToast(context, 'Making the change.');
      await _load();
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final app = widget.store.app;
    final latest = _jobs.isEmpty ? null : _jobs.first;
    final versions = latest == null ? const <Map<String, dynamic>>[] : crList(latest['versions']);
    final shown = versions.isEmpty ? null : versions.last;
    final working = latest != null && !const ['done', 'failed', 'cancelled'].contains(crS(latest['status']));
    return CrPage(
      title: 'Video editor',
      onRefresh: _load,
      action: CrMain(label: 'Make the edit', busy: _busy, onTap: _make, glyph: CrGlyph.cut),
      children: [
        if (latest != null) ...[
          CrCard(
            padding: EdgeInsets.zero,
            onTap: shown == null ? null : () => _play(context, app, crS(shown['url']), crS(latest['title'])),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              ClipRRect(
                borderRadius: const BorderRadius.vertical(top: Radius.circular(21)),
                child: SizedBox(
                  height: 220,
                  width: double.infinity,
                  child: Stack(fit: StackFit.expand, children: [
                    CrNetImage(app: app, url: crS(shown?['thumb']), seed: latest['id']),
                    if (shown != null)
                      Center(
                        child: Container(
                          width: 56,
                          height: 56,
                          decoration: BoxDecoration(color: Colors.black.withOpacity(.55), shape: BoxShape.circle),
                          alignment: Alignment.center,
                          child: const CrIcon(CrGlyph.play, size: 22, color: Colors.white),
                        ),
                      )
                    else
                      Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2))),
                    if (shown != null)
                      Positioned(
                        left: 12,
                        top: 12,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                          decoration: BoxDecoration(color: Colors.black.withOpacity(.55), borderRadius: BorderRadius.circular(12)),
                          child: Text('Version ${crS(shown['n'])}', style: const TextStyle(color: Colors.white, fontSize: 12)),
                        ),
                      ),
                  ]),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
                child: Row(children: [
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(crS(latest['title']).isEmpty ? 'Your edit' : crS(latest['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                      Text(
                          working
                              ? (crS(latest['stage']).isEmpty ? 'Editing…' : crS(latest['stage']))
                              : crS(latest['status']) == 'failed'
                                  ? (crS(latest['error']).isEmpty ? 'This edit did not work.' : crS(latest['error']))
                                  : '${crS(latest['platform_label'])}${latest['captions'] == true ? ' · captions' : ''}',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: HoolaType.small(c).copyWith(fontSize: 12.5, color: crS(latest['status']) == 'failed' ? c.bad : c.ink3)),
                      if (working) ...[
                        const SizedBox(height: 8),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(3),
                          child: LinearProgressIndicator(
                            minHeight: 5,
                            value: latest['progress'] is num ? ((latest['progress'] as num).toDouble() / ((latest['progress'] as num) > 1 ? 100 : 1)) : null,
                            backgroundColor: c.sunk,
                            color: c.ink,
                          ),
                        ),
                      ],
                    ]),
                  ),
                  if (shown != null)
                    CrRoundButton(glyph: CrGlyph.share, label: 'Save or share', onTap: () => _shareUrl(context, app, crS(shown['url']), crS(latest['title']))),
                ]),
              ),
            ]),
          ),
          if (shown != null) ...[
            const SizedBox(height: 10),
            Row(children: [
              Expanded(
                child: TextField(
                  controller: _revise,
                  style: HoolaType.body(c),
                  decoration: InputDecoration(
                    hintText: 'Change this edit… “music softer”',
                    filled: true,
                    fillColor: c.surface,
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide(color: c.line)),
                    focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide(color: c.ink)),
                  ),
                  onSubmitted: (_) => _change(latest),
                ),
              ),
              const SizedBox(width: 8),
              CrQuiet(label: 'Change', height: 48, onTap: () => _change(latest)),
            ]),
          ],
          if (crS(latest['post_caption']).isNotEmpty) ...[
            crGap,
            const CrLabel('Post caption', note: 'Written by Hoola'),
            CrCard(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SelectableText(
                    '${crS(latest['post_caption'])}${latest['hashtags'] is List && (latest['hashtags'] as List).isNotEmpty ? '\n${(latest['hashtags'] as List).join(' ')}' : ''}',
                    style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14.5)),
                const SizedBox(height: 10),
                CrChip(
                  label: 'Copy',
                  on: false,
                  onTap: () {
                    Clipboard.setData(ClipboardData(text: crS(latest['post_caption'])));
                    crToast(context, 'Caption copied.');
                  },
                ),
              ]),
            ),
          ],
          crGap,
        ],
        CrLabel('Your clips', note: '${_clips.length} of 8 · in this order'),
        SizedBox(
          height: 140,
          child: ReorderableListView(
            scrollDirection: Axis.horizontal,
            buildDefaultDragHandles: true,
            onReorder: (a, b) => setState(() {
              if (b > a) b--;
              final x = _clips.removeAt(a);
              _clips.insert(b, x);
            }),
            footer: _clips.length >= 8
                ? null
                : Semantics(
                    button: true,
                    label: 'Add clips',
                    excludeSemantics: true,
                    onTap: _adding ? null : _add,
                    child: GestureDetector(
                      onTap: _adding ? null : _add,
                      child: Container(
                        width: 88,
                        margin: const EdgeInsets.only(bottom: 26),
                        decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: c.lineStrong, width: 1.4)),
                        alignment: Alignment.center,
                        child: _adding
                            ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2))
                            : Column(mainAxisSize: MainAxisSize.min, children: [
                                CrIcon(CrGlyph.plus, size: 20, color: c.ink2),
                                const SizedBox(height: 4),
                                Text('Add', style: HoolaType.small(c).copyWith(color: c.ink2)),
                              ]),
                      ),
                    ),
                  ),
            children: [
              for (var i = 0; i < _clips.length; i++)
                Padding(
                  key: ValueKey(_clips[i].id),
                  padding: const EdgeInsets.only(right: 10),
                  child: SizedBox(
                    width: 88,
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Container(
                        height: 108,
                        decoration: BoxDecoration(color: crTone(c, _clips[i].id), borderRadius: BorderRadius.circular(14)),
                        child: Stack(children: [
                          Positioned(
                            left: 6,
                            top: 6,
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                              decoration: BoxDecoration(color: Colors.black.withOpacity(.55), borderRadius: BorderRadius.circular(10)),
                              child: Text('${i + 1}', style: const TextStyle(color: Colors.white, fontSize: 12)),
                            ),
                          ),
                          Center(child: CrIcon(CrGlyph.video, size: 20, color: c.ink2)),
                          Positioned(
                            right: 0,
                            top: 0,
                            child: IconButton(
                              tooltip: 'Remove',
                              onPressed: () => setState(() => _clips.removeAt(i)),
                              icon: CrIcon(CrGlyph.trash, size: 15, color: c.ink2),
                            ),
                          ),
                        ]),
                      ),
                      const SizedBox(height: 6),
                      Text(_clips[i].name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
                    ]),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        CrTextCard(title: 'What should Hoola do?', controller: _q, max: 1500, lines: 3,
            hint: 'Make a 30 second reel, cut the slow parts, add Hindi captions and upbeat music under it.'),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final a in _quick)
            CrChip(label: a, on: _asks.contains(a), onTap: () => setState(() => _asks.contains(a) ? _asks.remove(a) : _asks.add(a))),
        ]),
        crGap,
        CrSettings([
          CrSetting('Made for', _platforms.firstWhere((p) => p.$1 == _platform).$2, [for (final p in _platforms) p.$2],
              (v) => setState(() => _platform = _platforms.firstWhere((p) => p.$2 == v).$1)),
          CrSetting('Length', _len, const ['Auto', '15 s', '30 s', '60 s'], (v) => setState(() => _len = v)),
        ]),
        const SizedBox(height: 12),
        CrSwitch(title: 'Captions', sub: 'Burned into the video, in the spoken language', value: _captions,
            onChanged: (v) => setState(() => _captions = v)),
        const SizedBox(height: 12),
        const CrNote('Only edit videos you have the right to use. Every version stays here, so you can go back.', glyph: CrGlyph.info),
      ],
    );
  }
}
