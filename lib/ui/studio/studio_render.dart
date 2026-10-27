import 'dart:async';

import 'package:flutter/material.dart';

import '../../state.dart';
import '../glass.dart';
import 'studio_final.dart';
import 'studio_kit.dart';
import 'studio_takes.dart';

/// v0.159 Screen 9 · Live: how far the video is (%), time left, money spent so far, the five stages, every shot's state
/// (picture, in line, being made, lip sync, AI score). Rok do stops what has not finished yet.
class RenderScreen extends StatefulWidget {
  const RenderScreen({super.key, required this.app, required this.name});
  final Santosh app;
  final String name;
  @override
  State<RenderScreen> createState() => _RenderScreenState();
}

class _RenderScreenState extends State<RenderScreen> {
  Map<String, dynamic>? _v;
  Timer? _t;
  bool _busy = false;
  int _tick = -1;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    _t?.cancel();
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.studioTick != _tick) {
      _tick = app.studioTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final v = await app.api!.studioProject(widget.name);
      if (!mounted) return;
      setState(() => _v = v);
      _t?.cancel();
      if (const ['painting', 'working', 'reviewing', 'assembling', 'planning'].contains('${v['phase']}')) {
        _t = Timer(const Duration(seconds: 3), _load);
      }
    } catch (_) {
      _t?.cancel();
      _t = Timer(const Duration(seconds: 6), _load);
    }
  }

  Future<void> _stop() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: SC.card,
        title: Text('Baaki shots rok dein?', style: sora(17)),
        content: Text('Jo ban chuke woh rahenge. Jo provider par shuru ho chuka tha, uska paisa provider le sakta hai.',
            style: body(13.5, color: C.muted, height: 1.4)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Chalne do')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Rok do', style: TextStyle(color: C.bad))),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final r = await app.api!.studioCancel(widget.name);
      if (mounted) studioSnack(context, '${r['say'] ?? 'Rok diya'}');
    } catch (e) {
      if (mounted) studioSnack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  Future<void> _assemble() async {
    setState(() => _busy = true);
    try {
      await app.api!.studioAssemble(widget.name);
      if (mounted) studioSnack(context, 'Final video jod raha hoon (1-3 minute)');
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    return Scaffold(
      backgroundColor: SC.bg,
      body: SafeArea(
        bottom: false,
        child: v == null ? const Center(child: CircularProgressIndicator()) : _body(v),
      ),
    );
  }

  Widget _body(Map<String, dynamic> v) {
    final prog = sMap(v['progress']);
    final shots = sList(v['shots']);
    final phase = '${v['phase']}';
    final live = const ['painting', 'working', 'reviewing', 'assembling'].contains(phase);
    final total = sInt(prog['total'], shots.length);
    final done = shots.where((s) => s['phase'] == 'done').length;
    final pct = live ? sInt(prog['pct']) : (total > 0 ? (100 * done / shots.length).round() : 0);
    final eta = sInt(prog['eta_s']);
    final step = sInt(v['step'], 5);
    final nxt = '${sMap(v['next'])['kind']}';
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(4, 8, 16, 6),
        child: Row(children: [
          IconButton(onPressed: () => Navigator.maybePop(context), icon: const Icon(Icons.chevron_left_rounded, size: 30)),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(widget.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: sora(17)),
              Text('${qualityLabel['${prog['quality'] ?? v['quality_pref']}'] ?? ''} · '
                  '${live ? (phase == 'assembling' ? 'jod raha hai' : 'ban raha hai') : phase == 'ready' ? 'taiyaar' : 'ruka hua'}',
                  style: body(11.5, color: C.faint)),
            ]),
          ),
        ]),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 6, 16, 20), children: [
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(24), border: Border.all(color: SC.line)),
              child: Row(children: [
                SizedBox(
                  width: 92,
                  height: 92,
                  child: Stack(fit: StackFit.expand, children: [
                    CircularProgressIndicator(value: (pct / 100).clamp(0, 1).toDouble(), strokeWidth: 8, backgroundColor: Colors.white12,
                        color: C.accent, strokeCap: StrokeCap.round),
                    Center(child: Text('$pct%', style: sora(20, w: FontWeight.w700))),
                  ]),
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('$done / ${shots.length} shots taiyaar', style: sora(16)),
                    const SizedBox(height: 6),
                    Text(live
                        ? (eta > 0 ? 'Lagbhag ${eta < 60 ? '$eta sec' : '${(eta / 60).ceil()} min'} aur' : 'Bas ho gaya')
                        : phase == 'ready' ? 'Final video taiyaar' : 'Abhi kuch nahi chal raha',
                        style: body(12.5, color: C.muted)),
                    const SizedBox(height: 3),
                    Text.rich(TextSpan(style: body(12.5, color: C.muted), children: [
                      const TextSpan(text: 'Kharch abhi tak '),
                      TextSpan(text: rupees(prog['spent_inr'] ?? v['spent_inr']), style: body(12.5, w: FontWeight.w800)),
                      if (prog['inr'] != null) TextSpan(text: ' / ${rupees(prog['inr'])}'),
                    ])),
                  ]),
                ),
              ]),
            ),
            const SizedBox(height: 16),
            Row(children: [
              for (var i = 0; i < 5; i++) ...[
                Expanded(
                  child: Column(children: [
                    Container(height: 4, decoration: BoxDecoration(
                        color: i < step ? C.ok : i == step && live ? C.accent : Colors.white12, borderRadius: BorderRadius.circular(2))),
                    const SizedBox(height: 6),
                    Text(const ['Tasveer', 'Video', 'Lip sync', 'AI jaanch', 'Jodna'][i], style: body(10.5,
                        w: i == step && live ? FontWeight.w800 : FontWeight.w700,
                        color: i < step ? C.ok : i == step && live ? C.accentSoft : C.faint)),
                  ]),
                ),
                if (i < 4) const SizedBox(width: 4),
              ],
            ]),
            const SizedBox(height: 18),
            for (final s in shots) ...[_row(s), const SizedBox(height: 8)],
          ]),
        ),
      ),
      SBottomBar(
        note: live ? 'App band kar sakti hain. Taiyaar hote hi notification aayega.' : null,
        child: Row(children: [
          if (live)
            Expanded(child: SButton(label: 'Rok do', primary: false, danger: true, busy: _busy, onTap: phase == 'assembling' ? null : _stop)),
          if (live) const SizedBox(width: 10),
          Expanded(
            flex: 2,
            child: nxt == 'assemble' && !live
                ? SButton(label: 'Final video jodo · free', icon: Icons.movie_creation_rounded, busy: _busy, onTap: _assemble)
                : phase == 'ready'
                    ? SButton(label: 'Final dekho', icon: Icons.play_arrow_rounded, onTap: () => Navigator.of(context)
                        .pushReplacement(MaterialPageRoute(builder: (_) => FinalScreen(app: app, name: widget.name))))
                    : SButton(label: 'Taiyaar shots dekhiye', light: true, primary: false,
                        onTap: done == 0 ? null : () {
                          final s = shots.firstWhere((x) => x['phase'] == 'done');
                          Navigator.of(context).push(MaterialPageRoute(builder: (_) => TakesScreen(app: app, name: widget.name, shotId: '${s['id']}')));
                        }),
          ),
        ]),
      ),
    ]);
  }

  Widget _row(Map<String, dynamic> s) {
    final phase = '${s['phase']}';
    final working = const ['video', 'lipsync', 'paint', 'retrying'].contains(phase);
    final takes = sList(s['take_list']);
    String sub;
    switch (phase) {
      case 'paint':
        sub = 'Pehli tasveer ban rahi';
        break;
      case 'queued':
        sub = 'Line mein · ${s['model_label'] ?? ''}';
        break;
      case 'video':
        sub = '${s['model_label'] ?? ''} par ban raha${s['pct'] == null ? '' : ' · ${s['pct']}%'}';
        break;
      case 'lipsync':
        sub = 'Awaaz taiyaar → Sync 3 lip sync';
        break;
      case 'retrying':
        sub = 'Provider dheema, dobara koshish';
        break;
      case 'failed':
        sub = 'Nahi bana: ${s['error'] ?? ''}';
        break;
      case 'cancelled':
        sub = 'Roka gaya';
        break;
      case 'done':
        final t = takes.where((x) => x['picked'] == true).toList();
        sub = '${t.isEmpty ? '' : '${t.first['model_label']} · '}${s['duration']}s${t.isEmpty ? '' : ' · ${rupees(t.first['cost_inr'])}'}';
        break;
      default:
        sub = '${s['model_label'] ?? ''} · ${s['duration']}s';
    }
    final score = s['score'];
    return Press(
      onTap: takes.isEmpty ? null : () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => TakesScreen(app: app, name: widget.name, shotId: '${s['id']}'))),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: SC.card,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: working ? C.accent.withOpacity(.35) : Colors.transparent),
        ),
        child: Column(children: [
          Row(children: [
            SizedBox(
              width: 40,
              height: 64,
              child: Stack(fit: StackFit.expand, children: [
                SImage(app: app, url: '${s['keyframe'] ?? ''}', radius: 8),
                if (working)
                  Container(decoration: BoxDecoration(color: Colors.black45, borderRadius: BorderRadius.circular(8)),
                      child: const Center(child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.5, color: C.accent))))
                else if (phase == 'done')
                  const Center(child: Icon(Icons.play_arrow_rounded, color: Colors.white, size: 20)),
              ]),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${'${s['id']}'.toUpperCase()} · ${kindLabel['${s['kind']}'] ?? ''}', style: body(13.5, w: FontWeight.w800)),
                const SizedBox(height: 2),
                Text(sub, maxLines: 2, overflow: TextOverflow.ellipsis, style: body(11.5, w: working ? FontWeight.w700 : FontWeight.w600,
                    color: working ? C.accentSoft : phase == 'failed' ? C.bad : C.faint)),
              ]),
            ),
            if (score != null)
              Tag((score as num) < 6 ? '$score · dekhiye' : '$score', fg: score < 6 ? C.warn : C.ok, size: 12)
            else if (phase == 'queued')
              Text('line mein', style: body(11, color: C.faint)),
          ]),
          if (phase == 'video' && s['pct'] != null) ...[
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(2),
              child: LinearProgressIndicator(value: sInt(s['pct']) / 100, minHeight: 4, backgroundColor: Colors.white10, color: C.accent),
            ),
          ],
        ]),
      ),
    );
  }
}
