import 'package:flutter/material.dart';

import '../../state.dart';
import '../glass.dart';
import 'studio_approve.dart';
import 'studio_kit.dart';

/// v0.159 Screen 10 · Takes: watch every take of a shot, what the AI check found (right / wrong, with the second), keep
/// the best one, or write what to change and make it again (a price card first).
class TakesScreen extends StatefulWidget {
  const TakesScreen({super.key, required this.app, required this.name, required this.shotId});
  final Santosh app;
  final String name;
  final String shotId;
  @override
  State<TakesScreen> createState() => _TakesScreenState();
}

class _TakesScreenState extends State<TakesScreen> {
  Map<String, dynamic>? _v;
  late String _id = widget.shotId;
  int? _n;
  bool _busy = false;
  final _fix = TextEditingController();

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _fix.dispose();
    super.dispose();
  }

  Map<String, dynamic> get _shot => sList(_v?['shots']).firstWhere((s) => '${s['id']}' == _id, orElse: () => <String, dynamic>{});

  Future<void> _load() async {
    try {
      final v = await app.api!.studioProject(widget.name);
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) studioSnack(context, '$e');
    }
  }

  Future<void> _pick(int n) async {
    setState(() => _busy = true);
    try {
      await app.api!.studioPick(widget.name, _id, n);
      if (mounted) studioSnack(context, 'Take $n rakha');
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  Future<void> _redo({String quality = ''}) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.studioRedo(widget.name, _id, _fix.text.trim(), quality: quality);
      final id = '${r['waiting_owner'] ?? ''}';
      if (id.isNotEmpty && mounted) {
        final yes = await showModalBottomSheet<bool>(
          context: context,
          backgroundColor: SC.card,
          shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          builder: (ctx) => SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text('Shot ${_id.toUpperCase()} dobara banana', style: sora(18)),
                const SizedBox(height: 6),
                if (_fix.text.trim().isNotEmpty) Text('Badlav: ${_fix.text.trim()}', style: body(13, color: C.muted)),
                const SizedBox(height: 12),
                Text(rupees(r['inr']), style: sora(34, w: FontWeight.w700)),
                const SizedBox(height: 6),
                Text('Asli kharcha isse zyada nahi. Purane takes rahenge.', style: body(12, color: C.faint)),
                const SizedBox(height: 16),
                Row(children: [
                  Expanded(child: SButton(label: 'Abhi nahi', primary: false, onTap: () => Navigator.pop(ctx, false))),
                  const SizedBox(width: 10),
                  Expanded(flex: 2, child: SButton(label: 'Haan, ${rupees(r['inr'])}', icon: Icons.check_rounded, onTap: () => Navigator.pop(ctx, true))),
                ]),
              ]),
            ),
          ),
        );
        final d = await app.api!.studioDecide(id, yes == true);
        if (mounted && yes == true) {
          if ('${d['status']}' == 'failed') throw '${d['error'] ?? 'Shuru nahi ho paya'}';
          _fix.clear();
          studioSnack(context, 'Naya take ban raha hai (1-5 min). Taiyaar hote hi bataunga.');
        }
      }
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  void _go(int step) {
    final ids = sList(_v?['shots']).where((s) => sList(s['take_list']).isNotEmpty).map((s) => '${s['id']}').toList();
    final i = ids.indexOf(_id) + step;
    if (i < 0 || i >= ids.length) return;
    setState(() {
      _id = ids[i];
      _n = null;
      _fix.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final s = _shot;
    final takes = sList(s['take_list']);
    final picked = takes.where((t) => t['picked'] == true).toList();
    final cur = takes.firstWhere((t) => t['n'] == _n,
        orElse: () => picked.isNotEmpty ? picked.first : (takes.isNotEmpty ? takes.last : <String, dynamic>{}));
    final ar = aspectOf('${v?['aspect'] ?? '9:16'}');
    return Scaffold(
      backgroundColor: SC.bg,
      body: SafeArea(
        bottom: false,
        child: v == null
            ? const Center(child: CircularProgressIndicator())
            : Column(children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 8, 4, 6),
                  child: Row(children: [
                    IconButton(onPressed: () => Navigator.maybePop(context), icon: const Icon(Icons.chevron_left_rounded, size: 30)),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${_id.toUpperCase()} · ${kindLabel['${s['kind']}'] ?? ''}', style: sora(17)),
                        Text('${takes.length} take · ek chuniye', style: body(11.5, color: C.faint)),
                      ]),
                    ),
                    IconButton(onPressed: () => _go(-1), icon: const Icon(Icons.chevron_left_rounded)),
                    IconButton(onPressed: () => _go(1), icon: const Icon(Icons.chevron_right_rounded)),
                  ]),
                ),
                Expanded(
                  child: ListView(padding: const EdgeInsets.only(bottom: 20), children: [
                    Container(
                      color: SC.stage,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      alignment: Alignment.center,
                      child: SizedBox(
                        height: ar < 1 ? 360 : 220,
                        width: ar < 1 ? 360 * ar : 220 * ar,
                        child: cur.isEmpty
                            ? SImage(app: app, url: '${s['keyframe'] ?? ''}', radius: 16)
                            : SVideo(key: ValueKey('take${cur['url']}'), app: app, url: '${cur['url']}', poster: '${s['keyframe'] ?? ''}',
                                autoplay: true, badge: 'Take ${cur['n']} · ${qualityShort['${cur['quality']}'] ?? ''}'),
                      ),
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      height: 76,
                      child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 16), children: [
                        for (final t in takes.reversed) ...[_takeTile(t, s, t['n'] == cur['n']), const SizedBox(width: 10)],
                      ]),
                    ),
                    if (cur.isNotEmpty) _check(cur),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                        const SLabel('Kuch badalna hai?'),
                        Row(children: [
                          Expanded(
                            child: TextField(
                              controller: _fix,
                              style: body(13.5, w: FontWeight.w500),
                              decoration: InputDecoration(
                                hintText: '${cur['fix'] ?? ''}'.isNotEmpty ? 'Sujhav: ${cur['fix']}' : 'Jaise: haath goad mein, roshni thodi kam',
                                hintMaxLines: 2,
                                hintStyle: body(12.5, w: FontWeight.w500, color: C.faint),
                                filled: true,
                                fillColor: SC.card,
                                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: SC.line2)),
                                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: C.accent)),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          SizedBox(width: 110, child: SButton(label: 'Dobara', primary: false, height: 48, busy: _busy, onTap: () => _redo())),
                        ]),
                        const SizedBox(height: 8),
                        Wrap(spacing: 8, children: [
                          SChip(label: 'Premium mein dobara', icon: Icons.diamond_outlined, on: false, onTap: _busy ? null : () => _redo(quality: 'premium')),
                          if (cur['quality'] == 'preview')
                            SChip(label: 'HD mein banao', icon: Icons.hd_outlined, on: false, onTap: _busy ? null : () async {
                              final ok = await approveGenerate(context, app, v, shots: [_id]);
                              if (ok) _load();
                            }),
                        ]),
                      ]),
                    ),
                  ]),
                ),
                SBottomBar(
                  child: Row(children: [
                    Expanded(child: SButton(label: 'Baaki shots', primary: false, onTap: () => Navigator.maybePop(context))),
                    const SizedBox(width: 10),
                    Expanded(
                      flex: 2,
                      child: cur.isEmpty || cur['picked'] == true
                          ? SButton(label: cur.isEmpty ? 'Abhi koi take nahi' : 'Take ${cur['n']} chuna hua hai', icon: Icons.check_rounded,
                              light: true, primary: false, onTap: null)
                          : SButton(label: 'Take ${cur['n']} rakho', icon: Icons.check_rounded, busy: _busy, onTap: () => _pick(sInt(cur['n']))),
                    ),
                  ]),
                ),
              ]),
      ),
    );
  }

  Widget _takeTile(Map<String, dynamic> t, Map<String, dynamic> s, bool on) {
    final score = t['score'];
    return Press(
      onTap: () => setState(() => _n = sInt(t['n'])),
      child: Container(
        width: 150,
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: on ? C.accent.withOpacity(.08) : SC.card,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: on ? C.accent : SC.line2, width: on ? 1.5 : 1),
        ),
        child: Row(children: [
          SizedBox(width: 34, height: 56, child: SImage(app: app, url: '${s['keyframe'] ?? ''}', radius: 6)),
          const SizedBox(width: 8),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
              Text('Take ${t['n']}${t['picked'] == true ? ' ✓' : ''}', style: body(12.5, w: FontWeight.w800)),
              Text('${qualityShort['${t['quality']}'] ?? ''} · ${rupees(t['cost_inr'])}', style: body(10.5, color: C.faint)),
              if (score != null)
                Text('$score / 10', style: body(11.5, w: FontWeight.w800, color: (score as num) < 6 ? C.warn : C.ok)),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _check(Map<String, dynamic> t) {
    final good = List<String>.from(((t['good'] as List?) ?? const []).map((e) => '$e'));
    final bad = List<String>.from(((t['problems'] as List?) ?? const []).map((e) => '$e'));
    if (t['score'] == null && good.isEmpty && bad.isEmpty) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
        child: Text(t['quality'] == 'preview' ? 'Yeh free preview hai: sirf kahani aur timing dekhne ke liye.'
            : 'AI jaanch abhi nahi hui.', style: body(12.5, color: C.faint)),
      );
    }
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 14, 16, 0),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(18), border: Border.all(color: SC.line)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(color: C.violet.withOpacity(.18), borderRadius: BorderRadius.circular(10)),
            child: const Icon(Icons.search_rounded, size: 17, color: SC.violet),
          ),
          const SizedBox(width: 10),
          Expanded(child: Text('AI jaanch · Take ${t['n']}', style: body(14, w: FontWeight.w800))),
          if (t['score'] != null)
            Text('${t['score']}', style: body(14, w: FontWeight.w800, color: (t['score'] as num) < 6 ? C.warn : C.ok)),
        ]),
        const SizedBox(height: 10),
        for (final g in good) _line('✓', g, C.ok),
        for (final b in bad) _line('!', b, C.warn),
        if (t['lipsync'] == true) _line('✓', 'Hoth line ke saath mile hue (Sync 3)', C.ok),
        if ('${t['lipsync_error'] ?? ''}'.isNotEmpty) _line('!', 'Lip sync nahi hua: line kathan ki tarah lagegi', C.warn),
      ]),
    );
  }

  Widget _line(String mark, String text, Color c) => Padding(
        padding: const EdgeInsets.only(bottom: 7),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 16, child: Text(mark, style: body(13, w: FontWeight.w900, color: c))),
          Expanded(child: Text(text, style: body(12.5, color: C.chip, height: 1.4))),
        ]),
      );
}
