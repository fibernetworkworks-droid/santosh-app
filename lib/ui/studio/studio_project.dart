import 'dart:async';

import 'package:flutter/material.dart';

import '../../state.dart';
import '../glass.dart';
import '../video_editor.dart' show VideoPlayScreen;
import 'studio_approve.dart';
import 'studio_audio.dart';
import 'studio_cast.dart';
import 'studio_final.dart';
import 'studio_kit.dart';
import 'studio_render.dart';
import 'studio_shot.dart';
import 'studio_takes.dart';

/// v0.159 Screens 4 + 5 · One video project: while the storyboard is being written, the director's checklist; then a
/// real editor: monitor, timeline (video / spoken line / music tracks), tabs Shots · Cast · Awaaz · Brand, and one
/// clear next step at the bottom (Preview free · Banao with its price · Final jodo · Final dekho).
class StudioProjectScreen extends StatefulWidget {
  const StudioProjectScreen({super.key, required this.app, required this.name});
  final Santosh app;
  final String name;
  @override
  State<StudioProjectScreen> createState() => _StudioProjectScreenState();
}

class _StudioProjectScreenState extends State<StudioProjectScreen> {
  Map<String, dynamic>? _v;
  String? _err;
  int _tick = -1;
  Timer? _poll;
  bool _busy = false;
  int _tab = 0;
  String _sel = '';
  final _opened = DateTime.now();

  Santosh get app => widget.app;
  String get name => widget.name;

  @override
  void initState() {
    super.initState();
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _poll?.cancel();
    super.dispose();
  }

  void _onApp() {
    if (app.studioTick != _tick) {
      _tick = app.studioTick;
      _load();
    }
  }

  Future<void> _load() async {
    if (app.api == null) return;
    try {
      final v = await app.api!.studioProject(name);
      if (!mounted) return;
      setState(() {
        _v = v;
        _err = null;
        final ids = sList(v['shots']).map((s) => '${s['id']}').toList();
        if (!ids.contains(_sel)) _sel = ids.isEmpty ? '' : ids.first;
      });
      _poll?.cancel();
      final phase = '${v['phase']}';
      if (const ['planning', 'painting', 'working', 'reviewing', 'assembling'].contains(phase)) {
        _poll = Timer(Duration(seconds: phase == 'planning' ? 3 : 5), _load);
      }
    } catch (e) {
      if (mounted) setState(() => _err = '$e'.replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() f, {String ok = ''}) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      final say = '${r['say'] ?? ''}';
      if (mounted && (say.isNotEmpty || ok.isNotEmpty)) studioSnack(context, say.isNotEmpty ? say : ok);
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  Future<void> _push(Widget w) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => w));
    _load();
  }

  // ---- actions ----
  Future<void> _preview() => _run(() => app.api!.studioGenerate(name, 'preview'),
      ok: 'Free preview ban raha hai: tasveeron se chalti kahani.');

  Future<void> _make({List<String>? shots}) async {
    final ok = await approveGenerate(context, app, _v!, shots: shots);
    if (ok && mounted) {
      studioSnack(context, 'Shuru ho gaya. App band kar sakti hain, taiyaar hote hi bataunga.');
      await _load();
      if (mounted) _push(RenderScreen(app: app, name: name));
    }
  }

  Future<void> _pictures({List<String>? shots}) async {
    final v = _v!;
    final all = sList(v['shots']);
    final ids = shots ?? all.where((s) => '${s['keyframe']}'.isEmpty).map((s) => '${s['id']}').toList();
    if (ids.isEmpty) {
      studioSnack(context, 'Sab shots ki tasveer ban chuki hai.');
      return;
    }
    final inr = (ids.length * 12);
    final ok = await approveSimple(context, app,
        title: ids.length == 1 ? 'Shot ${ids.first} ki nayi tasveer' : '${ids.length} shots ki pehli tasveer',
        sub: '$name · Nano Banana Pro',
        rows: [PriceRow(Icons.image_rounded, SC.violet, 'Pehli tasveerein · ${ids.length}', 'Har shot ka pehla frame, same chehra', inr)],
        inr: inr,
        month: sMap(v['month']),
        ask: () => app.api!.studioKeyframes(name, shots: ids));
    if (ok) _load();
  }

  Future<void> _assemble() => _run(() => app.api!.studioAssemble(name), ok: 'Final video jod raha hoon (1-3 minute).');

  Future<void> _replan() async {
    final v = _v!;
    final brief = TextEditingController(text: '${v['brief'] ?? ''}');
    var secs = sInt(v['seconds'], 30);
    if (secs < 15) secs = 15;
    if (secs > 300) secs = 300;
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: SC.card,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => Padding(
          padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + MediaQuery.of(ctx).viewInsets.bottom),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Storyboard dobara likhein?', style: sora(18)),
            const SizedBox(height: 6),
            Text('Purane shots hat jayenge (bane hue takes nahi).', style: body(12.5, color: C.faint)),
            const SizedBox(height: 14),
            TextField(controller: brief, minLines: 3, maxLines: 7, style: body(14.5, w: FontWeight.w500),
                decoration: InputDecoration(filled: true, fillColor: SC.field,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none))),
            const SizedBox(height: 12),
            SSegment<int>(items: const {15: '15s', 30: '30s', 60: '1m', 120: '2m', 300: '5m'},
                value: const [15, 30, 60, 120, 300].contains(secs) ? secs : 30, onChanged: (x) => set(() => secs = x)),
            const SizedBox(height: 16),
            SButton(label: 'Likho · free', icon: Icons.auto_awesome_rounded, onTap: () => Navigator.pop(ctx, true)),
          ]),
        ),
      ),
    );
    if (ok == true) await _run(() => app.api!.studioPlan(name, brief.text.trim(), secs));
  }

  Future<void> _addShot() async {
    final prompt = TextEditingController();
    var dur = 5;
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: SC.card,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => Padding(
          padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + MediaQuery.of(ctx).viewInsets.bottom),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Naya shot', style: sora(18)),
            const SizedBox(height: 12),
            TextField(controller: prompt, minLines: 3, maxLines: 6, autofocus: true, style: body(14.5, w: FontWeight.w500),
                decoration: InputDecoration(hintText: 'Kya dikhe: kaun, kya kar raha hai, kahan, kaisi roshni', filled: true,
                    fillColor: SC.field, border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none))),
            const SizedBox(height: 12),
            Row(children: [
              Text('Lambai', style: body(13, color: C.muted)),
              Expanded(child: Slider(value: dur.toDouble(), min: 2, max: 15, divisions: 13, activeColor: C.accent,
                  onChanged: (x) => set(() => dur = x.round()))),
              Text('$dur sec', style: body(13, w: FontWeight.w800)),
            ]),
            const SizedBox(height: 12),
            SButton(label: 'Jodo', onTap: () => Navigator.pop(ctx, true)),
          ]),
        ),
      ),
    );
    if (ok == true && prompt.text.trim().isNotEmpty) {
      await _run(() => app.api!.studioAddShot(name, {'prompt': prompt.text.trim(), 'duration': dur, 'after': _sel}));
    }
  }

  Future<void> _menu() async {
    final v = _v!;
    final hasOut = sList(v['outputs']).isNotEmpty;
    final k = await pickOne<String>(context, name, {
      'replan': 'Storyboard dobara likho',
      'pictures': 'Pehli tasveerein banao',
      'look': 'Look badlo (${styleLabel['${v['style']}'] ?? v['style']})',
      if (hasOut) 'final': 'Final video dekho',
      'live': 'Kya ban raha hai (live)',
    });
    switch (k) {
      case 'replan':
        return _replan();
      case 'pictures':
        return _pictures();
      case 'look':
        final s = await pickOne<String>(context, 'Look', styleLabel, current: '${v['style']}');
        if (s != null) await _run(() => app.api!.studioSettings(name, {'style': s}), ok: 'Look badal gaya; naye shots isi mein banenge.');
        return;
      case 'final':
        return _push(FinalScreen(app: app, name: name));
      case 'live':
        return _push(RenderScreen(app: app, name: name));
    }
  }

  // ---- build ----
  @override
  Widget build(BuildContext context) {
    final v = _v;
    return Scaffold(
      backgroundColor: SC.bg,
      body: SafeArea(
        bottom: false,
        child: v == null
            ? Center(
                child: _err != null
                    ? Padding(padding: const EdgeInsets.all(24), child: Text(_err!, textAlign: TextAlign.center, style: body(14, color: C.bad)))
                    : const CircularProgressIndicator())
            : ('${v['phase']}' == 'planning' || (v['planning'] == true && sList(v['shots']).isEmpty))
                ? _planning(v)
                : _editor(v),
      ),
    );
  }

  Widget _header(Map<String, dynamic> v, {bool menu = true}) {
    final shots = sList(v['shots']);
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 8, 4, 6),
      child: Row(children: [
        IconButton(onPressed: () => Navigator.maybePop(context), icon: const Icon(Icons.chevron_left_rounded, size: 30)),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: sora(17)),
            Text('${v['aspect']} · ${styleLabel['${v['style']}'] ?? v['style']} · ${langShown('${v['language']}')}'
                '${shots.isEmpty ? '' : ' · ${shots.length} shots · ${v['seconds'] ?? 0}s'}',
                maxLines: 1, overflow: TextOverflow.ellipsis, style: body(11.5, color: C.faint)),
          ]),
        ),
        Container(
          height: 34,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          alignment: Alignment.center,
          decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(999), border: Border.all(color: SC.line)),
          child: Text(rupees(v['spent_inr']), style: body(12, w: FontWeight.w800)),
        ),
        if (menu) IconButton(onPressed: _busy ? null : _menu, icon: const Icon(Icons.more_vert_rounded)),
      ]),
    );
  }

  // Screen 4: the director's checklist while Claude writes the storyboard
  Widget _planning(Map<String, dynamic> v) {
    final t = DateTime.now().difference(_opened).inSeconds;
    const steps = [
      'Kahani samjhi',
      'Shots mein baanta',
      'Camera, roshni aur rang tay kar raha hoon',
      'Bolne wali line + lip sync shot',
      'Captions, music ka mood, sahi model har shot ko',
    ];
    final at = (t ~/ 5).clamp(0, steps.length - 1);
    return Column(children: [
      _header(v, menu: false),
      Expanded(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(24), border: Border.all(color: SC.line)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                const SizedBox(width: 48, height: 48, child: CircularProgressIndicator(strokeWidth: 3, color: C.accent)),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Director kaam par hai', style: sora(16)),
                    const SizedBox(height: 3),
                    Text('Claude har shot ka drishya, camera aur bolna likh raha hai', style: body(12.5, color: C.muted)),
                  ]),
                ),
              ]),
              const SizedBox(height: 18),
              for (var i = 0; i < steps.length; i++)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(children: [
                    Container(
                      width: 22,
                      height: 22,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: i < at ? C.ok : Colors.transparent,
                        border: i < at ? null : Border.all(color: i == at ? C.accent : Colors.white24, width: 2),
                      ),
                      child: i < at
                          ? const Icon(Icons.check_rounded, size: 14, color: SC.bg)
                          : i == at
                              ? Center(child: Container(width: 8, height: 8, decoration: const BoxDecoration(shape: BoxShape.circle, color: C.accent)))
                              : null,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(steps[i], style: body(13.5, w: i == at ? FontWeight.w700 : FontWeight.w600,
                          color: i == at ? C.accentSoft : i < at ? C.ink : C.faint)),
                    ),
                  ]),
                ),
            ]),
          ),
          const SizedBox(height: 22),
          Text('Shots aa rahe hain', style: sora(15)),
          const SizedBox(height: 10),
          for (var i = 0; i < 3; i++)
            Opacity(
              opacity: 1 - i * .25,
              child: Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(18)),
                child: Row(children: [
                  Container(width: 54, height: 96, decoration: BoxDecoration(color: SC.card2, borderRadius: BorderRadius.circular(10))),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      for (final w in const [.4, .95, .7])
                        FractionallySizedBox(
                          widthFactor: w,
                          child: Container(height: 10, margin: const EdgeInsets.only(bottom: 8),
                              decoration: BoxDecoration(color: SC.card2, borderRadius: BorderRadius.circular(5))),
                        ),
                    ]),
                  ),
                ]),
              ),
            ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(16)),
            child: Row(children: [
              const Icon(Icons.schedule_rounded, color: C.muted, size: 20),
              const SizedBox(width: 12),
              Expanded(
                child: Text('Lagbhag 20-60 second. App band kar sakti hain, taiyaar hote hi chat mein card aayega.',
                    style: body(12.5, color: C.muted, height: 1.4)),
              ),
            ]),
          ),
        ]),
      ),
    ]);
  }

  Widget _editor(Map<String, dynamic> v) {
    final shots = sList(v['shots']);
    final sel = shots.firstWhere((s) => '${s['id']}' == _sel, orElse: () => shots.isEmpty ? <String, dynamic>{} : shots.first);
    final outs = sList(v['outputs']);
    final phase = '${v['phase']}';
    final prog = sMap(v['progress']);
    return Column(children: [
      _header(v),
      Expanded(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.only(bottom: 16), children: [
            _monitor(v, sel, shots),
            if (shots.isNotEmpty) _timeline(v, shots),
            if (const ['painting', 'working', 'reviewing', 'assembling'].contains(phase))
              _banner(Icons.auto_awesome_motion_rounded, C.accent,
                  phase == 'painting' ? 'Pehli tasveerein ban rahi hain…' : phase == 'reviewing' ? 'AI har take jaanch raha hai…'
                      : phase == 'assembling' ? 'Final video jod raha hoon…' : 'Ban raha hai · ${prog['pct'] ?? 0}% · ${prog['done'] ?? 0}/${prog['total'] ?? 0} shots',
                  'Live dekho', () => _push(RenderScreen(app: app, name: name)))
            else if (outs.isNotEmpty)
              _banner(outs.last['preview'] == true ? Icons.slideshow_rounded : Icons.check_circle_rounded,
                  outs.last['preview'] == true ? C.muted : C.ok,
                  outs.last['preview'] == true ? 'Free preview taiyaar' : 'Final video taiyaar · ${secs(outs.last['seconds'])}',
                  'Dekho', () => _push(FinalScreen(app: app, name: name))),
            for (final a in sList(v['approvals'])) Padding(padding: const EdgeInsets.symmetric(horizontal: 16),
                child: StudioApprovalCard(key: ValueKey('ap${a['id']}'), v: a, app: app)),
            _tabs(),
            if (_tab == 0) _shotsTab(v, shots),
            if (_tab == 1) CastTab(app: app, v: v, onChanged: _load),
            if (_tab == 2) AudioTab(app: app, v: v, onChanged: _load),
            if (_tab == 3) BrandTab(app: app, v: v, onChanged: _load),
          ]),
        ),
      ),
      _bottom(v),
    ]);
  }

  Widget _monitor(Map<String, dynamic> v, Map<String, dynamic> sel, List<Map<String, dynamic>> shots) {
    final ar = aspectOf('${v['aspect']}');
    const h = 300.0;
    final w = (h * ar).clamp(120.0, 340.0);
    final takes = sList(sel['take_list']);
    final picked = takes.where((t) => t['picked'] == true).toList();
    final take = picked.isNotEmpty ? picked.first : (takes.isNotEmpty ? takes.last : <String, dynamic>{});
    var start = 0;
    for (final s in shots) {
      if (s['id'] == sel['id']) break;
      start += sInt(s['duration']);
    }
    final outs = sList(v['outputs']);
    return Container(
      color: SC.stage,
      padding: const EdgeInsets.symmetric(vertical: 14),
      child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        SizedBox(
          width: w.toDouble(),
          height: h,
          child: '${take['url'] ?? ''}'.isNotEmpty
              ? SVideo(key: ValueKey('mon${take['url']}'), app: app, url: '${take['url']}', poster: '${sel['keyframe'] ?? ''}',
                  badge: '${sel['id']} · take ${take['n']}')
              : Stack(fit: StackFit.expand, children: [
                  SImage(app: app, url: '${sel['keyframe'] ?? ''}', radius: 14, tone: toneOf('$name${sel['id']}'),
                      icon: Icons.image_outlined),
                  if (sel.isNotEmpty) Positioned(left: 10, top: 10,
                      child: Tag('${sel['id']} · ${'${sel['keyframe']}'.isEmpty ? 'tasveer baaki' : 'tasveer'}', fg: C.ink, bg: const Color(0xB306050F))),
                  if ('${sel['caption'] ?? ''}'.isNotEmpty)
                    Positioned(left: 8, right: 8, bottom: 26,
                        child: Text('${sel['caption']}', textAlign: TextAlign.center, style: body(13, w: FontWeight.w800,
                            color: Colors.white).copyWith(shadows: const [Shadow(blurRadius: 6, color: Colors.black)]))),
                  Positioned(right: 8, bottom: 8, child: Tag('AI-generated · Hoola', fg: C.chip, bg: const Color(0xB306050F), size: 9)),
                ]),
        ),
        const SizedBox(width: 18),
        Column(mainAxisSize: MainAxisSize.min, children: [
          Text('${secs(start)} / ${secs(v['seconds'])}', style: body(12, w: FontWeight.w700, color: C.chip)),
          const SizedBox(height: 12),
          _round(Icons.fullscreen_rounded, 'Poori screen', outs.isEmpty && '${take['url'] ?? ''}'.isEmpty ? null : () {
            final u = outs.isNotEmpty ? '${outs.last['url']}' : '${take['url']}';
            Navigator.of(context).push(MaterialPageRoute(builder: (_) => VideoPlayScreen(url: app.api!.absolute(u), title: name)));
          }),
          const SizedBox(height: 10),
          _round(Icons.edit_rounded, 'Shot badlo', sel.isEmpty ? null : () => _push(ShotEditorScreen(app: app, name: name, shotId: '${sel['id']}'))),
        ]),
      ]),
    );
  }

  Widget _round(IconData icon, String tip, VoidCallback? onTap) => Tooltip(
        message: tip,
        child: Press(
          onTap: onTap,
          child: Opacity(
            opacity: onTap == null ? .35 : 1,
            child: Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: Colors.white24)),
              child: Icon(icon, color: C.chip, size: 20),
            ),
          ),
        ),
      );

  Widget _timeline(Map<String, dynamic> v, List<Map<String, dynamic>> shots) {
    final total = shots.fold<int>(0, (a, s) => a + sInt(s['duration'], 1));
    final music = v['music_info'] != null || '${sMap(v['prefs'])['music'] ?? ''}'.isNotEmpty;
    final moodName = '${sMap(v['music_info'])['mood'] ?? sMap(v['prefs'])['music'] ?? ''}';
    Widget label(String t) => SizedBox(width: 30, child: Text(t, style: body(9.5, w: FontWeight.w800, color: C.faint)));
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: const BoxDecoration(color: SC.field, border: Border.symmetric(horizontal: BorderSide(color: SC.line))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Padding(
          padding: const EdgeInsets.only(left: 30, bottom: 6),
          child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            for (var i = 0; i <= 4; i++) Text(secs(total * i / 4), style: body(9.5, color: C.faint)),
          ]),
        ),
        Row(children: [
          label('VID'),
          Expanded(
            child: SizedBox(
              height: 52,
              child: Row(children: [
                for (final s in shots)
                  Expanded(
                    flex: sInt(s['duration'], 1),
                    child: GestureDetector(
                      onTap: () => setState(() => _sel = '${s['id']}'),
                      child: Container(
                        margin: const EdgeInsets.only(right: 2),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                              color: s['id'] == _sel ? C.accent : '${s['keyframe']}'.isEmpty ? Colors.white24 : Colors.transparent,
                              width: s['id'] == _sel ? 2 : 1),
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(5),
                          child: Stack(fit: StackFit.expand, children: [
                            '${s['keyframe']}'.isEmpty
                                ? Container(color: SC.card2)
                                : SImage(app: app, url: '${s['keyframe']}', radius: 0),
                            if (s['phase'] == 'video' || s['phase'] == 'paint' || s['phase'] == 'lipsync')
                              Container(color: Colors.black38, child: const Center(child: SizedBox(width: 14, height: 14,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: C.accent)))),
                            Positioned(left: 3, top: 2, child: Text('${s['id']}'.toUpperCase(),
                                style: body(9, w: FontWeight.w800).copyWith(shadows: const [Shadow(blurRadius: 4, color: Colors.black)]))),
                          ]),
                        ),
                      ),
                    ),
                  ),
              ]),
            ),
          ),
        ]),
        const SizedBox(height: 5),
        Row(children: [
          label('BOL'),
          Expanded(
            child: SizedBox(
              height: 14,
              child: Row(children: [
                for (final s in shots)
                  Expanded(
                    flex: sInt(s['duration'], 1),
                    child: Container(
                      margin: const EdgeInsets.only(right: 2),
                      decoration: '${s['dialogue'] ?? ''}'.isEmpty && '${s['voiceover'] ?? ''}'.isEmpty && '${s['vo_url'] ?? ''}'.isEmpty
                          ? null
                          : BoxDecoration(color: C.accent.withOpacity(.35), borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: C.accent)),
                    ),
                  ),
              ]),
            ),
          ),
        ]),
        const SizedBox(height: 5),
        Row(children: [
          label('SUR'),
          Expanded(
            child: Container(
              height: 16,
              padding: const EdgeInsets.only(left: 6),
              alignment: Alignment.centerLeft,
              decoration: BoxDecoration(
                color: music ? C.violet.withOpacity(.25) : Colors.transparent,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: music ? C.violet.withOpacity(.6) : Colors.white12),
              ),
              child: Text(music ? 'Lyria · ${moodLabel[moodName] ?? moodName}' : 'music nahi', style: body(9, w: FontWeight.w700,
                  color: music ? SC.violet : C.faint)),
            ),
          ),
        ]),
      ]),
    );
  }

  Widget _banner(IconData icon, Color color, String text, String action, VoidCallback onTap) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
        child: Press(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.fromLTRB(14, 10, 10, 10),
            decoration: BoxDecoration(color: color.withOpacity(.10), borderRadius: BorderRadius.circular(14),
                border: Border.all(color: color.withOpacity(.4))),
            child: Row(children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 10),
              Expanded(child: Text(text, style: body(13, w: FontWeight.w700))),
              Text(action, style: body(13, w: FontWeight.w800, color: color)),
              Icon(Icons.chevron_right_rounded, color: color),
            ]),
          ),
        ),
      );

  Widget _tabs() => Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
        child: Row(children: [
          for (final t in const ['Shots', 'Cast', 'Awaaz', 'Brand'].asMap().entries) ...[
            Press(
              onTap: () => setState(() => _tab = t.key),
              child: Container(
                height: 38,
                padding: const EdgeInsets.symmetric(horizontal: 15),
                alignment: Alignment.center,
                decoration: BoxDecoration(color: _tab == t.key ? C.ink : Colors.transparent, borderRadius: BorderRadius.circular(999)),
                child: Text(t.value, style: body(13, w: _tab == t.key ? FontWeight.w800 : FontWeight.w700,
                    color: _tab == t.key ? SC.bg : C.chip)),
              ),
            ),
            const SizedBox(width: 4),
          ],
        ]),
      );

  Widget _shotsTab(Map<String, dynamic> v, List<Map<String, dynamic>> shots) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (shots.isEmpty)
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(18)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text('Abhi storyboard nahi hai', style: sora(15)),
                const SizedBox(height: 6),
                Text('Hoola se likhwaiye (free) ya khud shot jodiye.', style: body(13, color: C.muted)),
                const SizedBox(height: 12),
                SButton(label: 'Storyboard likho · free', icon: Icons.auto_awesome_rounded, onTap: _replan),
              ]),
            ),
          for (final s in shots) ...[
            ShotCard(app: app, project: name, s: s, selected: s['id'] == _sel,
                onTap: () {
                  setState(() => _sel = '${s['id']}');
                  _push(ShotEditorScreen(app: app, name: name, shotId: '${s['id']}'));
                },
                onTakes: sList(s['take_list']).isEmpty ? null : () => _push(TakesScreen(app: app, name: name, shotId: '${s['id']}')),
                onPicture: () => _pictures(shots: ['${s['id']}'])),
            const SizedBox(height: 10),
          ],
          Press(
            onTap: _busy ? null : _addShot,
            child: Container(
              height: 50,
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white24, width: 1.5)),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                const Icon(Icons.add_rounded, color: C.chip),
                const SizedBox(width: 8),
                Text('Shot jodiye', style: body(13.5, w: FontWeight.w700, color: C.chip)),
              ]),
            ),
          ),
        ]),
      );

  Widget _bottom(Map<String, dynamic> v) {
    final shots = sList(v['shots']);
    final nxt = sMap(v['next']);
    final kind = '${nxt['kind']}';
    final est = sMap(sMap(v['estimates'])['${v['quality_pref'] ?? 'final'}']);
    if (shots.isEmpty) return const SizedBox.shrink();
    Widget primary;
    if (kind == 'wait') {
      primary = SButton(label: 'Live dekho', icon: Icons.visibility_rounded, light: true, primary: false,
          onTap: () => _push(RenderScreen(app: app, name: name)));
    } else if (kind == 'assemble') {
      primary = SButton(label: 'Final video jodo · free', icon: Icons.movie_creation_rounded, busy: _busy, onTap: _assemble);
    } else if (kind == 'done') {
      primary = SButton(label: 'Final dekho', icon: Icons.play_arrow_rounded, onTap: () => _push(FinalScreen(app: app, name: name)));
    } else {
      primary = SButton(label: 'Banao', icon: Icons.arrow_forward_rounded, busy: _busy, onTap: () => _make());
    }
    return SBottomBar(
      child: Row(children: [
        if (kind != 'done' && kind != 'wait')
          Expanded(
            flex: 3,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text('~${rupees(est['inr'])}', style: body(16, w: FontWeight.w800)),
              Text('${qualityShort['${v['quality_pref']}'] ?? 'HD'} · ${v['seconds'] ?? 0}s · sab mila kar', style: body(11, color: C.faint)),
            ]),
          ),
        if (kind != 'done' && kind != 'wait') ...[
          Expanded(flex: 3, child: SButton(label: 'Preview · free', primary: false, height: 50, onTap: _busy ? null : _preview)),
          const SizedBox(width: 8),
        ],
        Expanded(flex: 3, child: primary),
      ]),
    );
  }
}

/// One shot in the Shots tab: its picture, kind, model, line, camera and state.
class ShotCard extends StatelessWidget {
  const ShotCard({super.key, required this.app, required this.project, required this.s, this.selected = false, this.onTap,
      this.onTakes, this.onPicture});
  final Santosh app;
  final String project;
  final Map<String, dynamic> s;
  final bool selected;
  final VoidCallback? onTap;
  final VoidCallback? onTakes;
  final VoidCallback? onPicture;

  @override
  Widget build(BuildContext context) {
    final kind = '${s['kind'] ?? 'scene'}';
    final kf = '${s['keyframe'] ?? ''}';
    final phase = '${s['phase']}';
    final takes = sList(s['take_list']);
    String state;
    Color sc;
    switch (phase) {
      case 'paint':
        state = 'tasveer ban rahi';
        sc = C.accentSoft;
        break;
      case 'queued':
        state = 'line mein';
        sc = C.faint;
        break;
      case 'video':
        state = 'video ban raha${s['pct'] == null ? '' : ' · ${s['pct']}%'}';
        sc = C.accentSoft;
        break;
      case 'lipsync':
        state = 'lip sync ho raha';
        sc = C.accentSoft;
        break;
      case 'retrying':
        state = 'dobara koshish';
        sc = C.warn;
        break;
      case 'failed':
        state = 'nahi bana';
        sc = C.bad;
        break;
      case 'cancelled':
        state = 'roka gaya';
        sc = C.faint;
        break;
      case 'done':
        state = '${qualityShort['${s['quality']}'] ?? ''} take taiyaar${s['score'] == null ? '' : ' · ${s['score']}/10'}';
        sc = C.ok;
        break;
      case 'pictured':
        state = 'tasveer taiyaar';
        sc = C.ok;
        break;
      default:
        state = kind == 'talk' ? 'pehli tasveer chahiye' : 'tasveer baaki';
        sc = kind == 'talk' ? C.accentSoft : C.faint;
    }
    return Press(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(18),
            border: Border.all(color: selected ? C.accent : SC.line, width: selected ? 1.5 : 1)),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          GestureDetector(
            onTap: kf.isEmpty ? onPicture : null,
            child: SizedBox(
              width: 58,
              height: 104,
              child: kf.isNotEmpty
                  ? SImage(app: app, url: kf, radius: 10)
                  : Container(
                      decoration: BoxDecoration(color: SC.card2, borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: Colors.white24)),
                      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                        const Icon(Icons.auto_awesome_rounded, size: 18, color: C.muted),
                        const SizedBox(height: 4),
                        Text('₹12', style: body(10, w: FontWeight.w800, color: C.muted)),
                      ]),
                    ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Wrap(spacing: 6, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
                Text('${s['id']}'.toUpperCase(), style: body(13.5, w: FontWeight.w800)),
                Tag((kindLabel[kind] ?? kind).toUpperCase(), fg: kindColor[kind] ?? SC.teal),
                Text('${s['duration']}s · ${s['model_label'] ?? ''}', style: body(10.5, w: FontWeight.w700, color: C.faint)),
              ]),
              const SizedBox(height: 6),
              if ('${s['dialogue'] ?? ''}'.isNotEmpty)
                Text('"${s['dialogue']}"', maxLines: 2, overflow: TextOverflow.ellipsis, style: body(13, w: FontWeight.w700, height: 1.35))
              else
                Text('${s['prompt']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: body(12.5, color: C.chip, height: 1.4)),
              const SizedBox(height: 6),
              Row(children: [
                if ('${s['camera'] ?? ''}'.isNotEmpty) ...[
                  Icon(cameraIcon['${s['camera']}'] ?? Icons.videocam_rounded, size: 13, color: C.faint),
                  const SizedBox(width: 4),
                  Text('${cameraLabel['${s['camera']}'] ?? s['camera']} · ', style: body(11, color: C.faint)),
                ],
                Flexible(child: Text(state, maxLines: 1, overflow: TextOverflow.ellipsis, style: body(11, w: FontWeight.w700, color: sc))),
              ]),
              if ('${s['error'] ?? ''}'.isNotEmpty)
                Padding(padding: const EdgeInsets.only(top: 4),
                    child: Text('${s['error']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: body(11, color: C.bad))),
              if (takes.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: GestureDetector(
                    onTap: onTakes,
                    child: Text('${takes.length} take · dekho aur chuno ›', style: body(11.5, w: FontWeight.w800, color: C.accent)),
                  ),
                ),
            ]),
          ),
        ]),
      ),
    );
  }
}
