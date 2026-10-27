import 'package:flutter/material.dart';

import '../../state.dart';
import '../glass.dart';
import 'studio_approve.dart';
import 'studio_kit.dart';
import 'studio_takes.dart';

/// v0.159 Screen 6 · Shot editor: the opening picture, what kind of shot, what we see, who is in it, the camera move,
/// the length, the spoken line (hear it), caption, transition, and which AI model makes it. Save, or make just this shot.
class ShotEditorScreen extends StatefulWidget {
  const ShotEditorScreen({super.key, required this.app, required this.name, required this.shotId});
  final Santosh app;
  final String name;
  final String shotId;
  @override
  State<ShotEditorScreen> createState() => _ShotEditorScreenState();
}

class _ShotEditorScreenState extends State<ShotEditorScreen> {
  Map<String, dynamic>? _v;
  late String _id = widget.shotId;
  final _prompt = TextEditingController();
  final _line = TextEditingController();
  final _cap = TextEditingController();
  String _kind = 'scene';
  String _camera = '';
  String _transition = '';
  int _dur = 5;
  List<String> _chars = [];
  bool _dirty = false;
  bool _busy = false;
  bool _allCams = false;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _prompt.dispose();
    _line.dispose();
    _cap.dispose();
    super.dispose();
  }

  Map<String, dynamic> get _shot =>
      sList(_v?['shots']).firstWhere((s) => '${s['id']}' == _id, orElse: () => <String, dynamic>{});

  Future<void> _load({bool keep = false}) async {
    try {
      final v = await app.api!.studioProject(widget.name);
      if (!mounted) return;
      setState(() => _v = v);
      if (!keep) _fill();
    } catch (e) {
      if (mounted) studioSnack(context, '$e');
    }
  }

  void _fill() {
    final s = _shot;
    if (s.isEmpty) return;
    setState(() {
      _prompt.text = '${s['prompt'] ?? ''}';
      _line.text = '${s['dialogue'] ?? ''}';
      _cap.text = '${s['caption'] ?? ''}';
      _kind = '${s['kind'] ?? 'scene'}';
      _camera = '${s['camera'] ?? ''}';
      _transition = '${s['transition'] ?? ''}';
      _dur = sInt(s['duration'], 5);
      _chars = List<String>.from(((s['characters'] as List?) ?? const []).map((e) => '$e'));
      _dirty = false;
    });
  }

  void _touch(VoidCallback f) => setState(() {
        f();
        _dirty = true;
      });

  Future<bool> _save({bool quiet = false}) async {
    if (!_dirty) return true;
    if (_prompt.text.trim().isEmpty && _line.text.trim().isEmpty) {
      studioSnack(context, 'Kya dikhe, yeh likhiye');
      return false;
    }
    if ((_kind == 'talk' || _kind == 'dialogue') && _line.text.trim().isEmpty) {
      studioSnack(context, 'Bolne wali line likhiye');
      return false;
    }
    setState(() => _busy = true);
    var ok = false;
    try {
      final v = await app.api!.studioShot(widget.name, _id, {
        'prompt': _prompt.text.trim(), 'dialogue': _line.text.trim(), 'caption': _cap.text.trim(), 'duration': _dur, 'kind': _kind,
        if (_camera.isNotEmpty) 'camera': _camera, 'characters': _chars, 'transition': _transition,
      });
      if (mounted) {
        setState(() {
          _v = v;
          _dirty = false;
        });
        if (!quiet) studioSnack(context, 'Shot save ho gaya');
      }
      ok = true;
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
    return ok;
  }

  Future<void> _go(int step) async {
    final ids = sList(_v?['shots']).map((s) => '${s['id']}').toList();
    final i = ids.indexOf(_id) + step;
    if (i < 0 || i >= ids.length) return;
    if (!await _save(quiet: true)) return;
    setState(() => _id = ids[i]);
    _fill();
  }

  Future<void> _picture() async {
    if (!await _save(quiet: true)) return;
    if (!mounted) return;
    final ok = await approveSimple(context, app,
        title: 'Shot $_id ki nayi tasveer',
        sub: '${widget.name} · Nano Banana Pro',
        rows: const [PriceRow(Icons.image_rounded, SC.violet, 'Pehli tasveer · 1', 'Shot ka pehla frame', 12)],
        inr: 12,
        month: sMap(_v?['month']),
        ask: () => app.api!.studioKeyframes(widget.name, shots: [_id]));
    if (ok && mounted) {
      studioSnack(context, 'Tasveer ban rahi hai (lagbhag 30 sec)');
      Future.delayed(const Duration(seconds: 25), () => mounted ? _load(keep: true) : null);
    }
  }

  Future<void> _makeThis() async {
    if (!await _save(quiet: true)) return;
    if (!mounted || _v == null) return;
    final ok = await approveGenerate(context, app, _v!, shots: [_id]);
    if (ok && mounted) {
      studioSnack(context, 'Shot $_id ban raha hai');
      Navigator.pop(context);
    }
  }

  Future<void> _delete() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: SC.card,
        title: Text('Shot $_id hatayein?', style: sora(17)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Hatao', style: TextStyle(color: C.bad))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await app.api!.studioDeleteShot(widget.name, _id);
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final s = _shot;
    final ids = sList(v?['shots']).map((x) => '${x['id']}').toList();
    final i = ids.indexOf(_id);
    var start = 0;
    for (final x in sList(v?['shots'])) {
      if (x['id'] == _id) break;
      start += sInt(x['duration']);
    }
    return PopScope(
      canPop: !_dirty,
      onPopInvoked: (did) async {
        if (did) return;
        final keep = await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: SC.card,
            title: Text('Badlav save karein?', style: sora(17)),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Chhod do')),
              TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
            ],
          ),
        );
        if (keep == true) await _save();
        if (mounted) {
          setState(() => _dirty = false);
          Navigator.pop(context);
        }
      },
      child: Scaffold(
        backgroundColor: SC.bg,
        body: SafeArea(
          bottom: false,
          child: v == null || s.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : Column(children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(4, 8, 4, 6),
                    child: Row(children: [
                      IconButton(onPressed: () => Navigator.maybePop(context), icon: const Icon(Icons.close_rounded)),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('Shot ${_id.toUpperCase()}', style: sora(17)),
                          Text('${i + 1} / ${ids.length} · ${secs(start)} se ${secs(start + _dur)}', style: body(11.5, color: C.faint)),
                        ]),
                      ),
                      IconButton(onPressed: i > 0 ? () => _go(-1) : null, icon: const Icon(Icons.chevron_left_rounded)),
                      IconButton(onPressed: i < ids.length - 1 ? () => _go(1) : null, icon: const Icon(Icons.chevron_right_rounded)),
                      IconButton(onPressed: ids.length > 1 ? _delete : null, icon: const Icon(Icons.delete_outline_rounded)),
                    ]),
                  ),
                  Expanded(child: _form(v, s)),
                  SBottomBar(
                    child: Row(children: [
                      Expanded(child: SButton(label: _dirty ? 'Save' : 'Saved', primary: false, busy: _busy && _dirty,
                          onTap: _dirty ? () => _save() : null)),
                      const SizedBox(width: 10),
                      Expanded(flex: 2, child: SButton(label: 'Sirf yeh shot banao', icon: Icons.movie_creation_outlined, onTap: _busy ? null : _makeThis)),
                    ]),
                  ),
                ]),
        ),
      ),
    );
  }

  Widget _form(Map<String, dynamic> v, Map<String, dynamic> s) {
    final ar = aspectOf('${v['aspect']}');
    final takes = sList(s['take_list']);
    final chars = sList(v['character_list']);
    final talking = _kind == 'talk' || _kind == 'dialogue';
    final cams = _allCams ? cameraLabel.keys.toList() : const ['static', 'dolly_in', 'pan_left', 'orbit', 'crane_up', 'handheld', 'drone', 'zoom_in'];
    return ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
      Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        SizedBox(
          width: 150,
          height: (150 / ar).clamp(110.0, 270.0).toDouble(),
          child: Stack(fit: StackFit.expand, children: [
            SImage(app: app, url: '${s['keyframe'] ?? ''}', radius: 14, tone: toneOf('${widget.name}$_id'), icon: Icons.image_outlined),
            Positioned(left: 8, top: 8, child: Tag('${s['keyframe']}'.isEmpty ? 'Tasveer baaki' : 'Pehli tasveer', fg: C.ink,
                bg: const Color(0xB306050F))),
            if (s['phase'] == 'paint')
              Container(color: Colors.black45, child: const Center(child: CircularProgressIndicator(color: C.accent))),
          ]),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Video isi tasveer se shuru hoga. Chehra har shot mein yahi rahega.', style: body(11.5, color: C.faint, height: 1.4)),
            const SizedBox(height: 10),
            _act(Icons.auto_awesome_rounded, '${s['keyframe']}'.isEmpty ? 'Tasveer banao · ₹12' : 'Nayi tasveer · ₹12',
                v['can_paint'] == true ? _picture : null),
            const SizedBox(height: 8),
            _act(Icons.play_circle_outline_rounded, 'Pichhle takes (${takes.length})', takes.isEmpty ? null : () {
              Navigator.of(context).push(MaterialPageRoute(builder: (_) => TakesScreen(app: app, name: widget.name, shotId: _id)));
            }),
          ]),
        ),
      ]),
      const SizedBox(height: 20),
      const SLabel('Shot ka type'),
      Wrap(spacing: 6, runSpacing: 6, children: [
        for (final k in kindLabel.entries) SChip(label: k.value, on: _kind == k.key, solid: true, onTap: () => _touch(() => _kind = k.key)),
      ]),
      const SizedBox(height: 18),
      SLabel(_kind == 'talk' ? 'Peeche kya dikhe' : 'Kya dikhe'),
      _box(_prompt, 'Kaun, kya kar raha hai, kahan, kaisi roshni', lines: 3),
      if (talking) ...[
        const SizedBox(height: 18),
        Row(children: [
          const Expanded(child: SLabel('Kya bole (lip sync)')),
          if ('${s['dialogue'] ?? ''}'.isNotEmpty && !_dirty)
            SoundButton(app: app, url: '${s['line_url'] ?? ''}', size: 34,
                load: () async => '${(await app.api!.studioLine(widget.name, _id))['url']}'),
        ]),
        _box(_line, 'Jaise: मन शांत ठेवा, तेच खरे सुख.', lines: 2),
        Padding(padding: const EdgeInsets.only(top: 6),
            child: Text('${langShown('${v['language']}')} mein, aapki chuni hui awaaz mein · Sync 3 hoth milata hai', style: body(11, color: C.faint))),
      ],
      const SizedBox(height: 18),
      SLabel('Camera', trailing: _allCams ? null : '8 / ${cameraLabel.length}'),
      GridView.count(
        crossAxisCount: 4,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 6,
        crossAxisSpacing: 6,
        childAspectRatio: 1.25,
        children: [
          for (final c in cams)
            Press(
              onTap: () => _touch(() => _camera = _camera == c ? '' : c),
              child: Container(
                decoration: BoxDecoration(
                  color: _camera == c ? C.accent.withOpacity(.10) : SC.card,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: _camera == c ? C.accent : SC.line2, width: _camera == c ? 1.5 : 1),
                ),
                child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Icon(cameraIcon[c] ?? Icons.videocam_rounded, size: 18, color: _camera == c ? C.accentSoft : C.chip),
                  const SizedBox(height: 4),
                  Text(cameraLabel[c] ?? c, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: body(10.5, w: FontWeight.w700, color: _camera == c ? C.accentSoft : C.chip)),
                ]),
              ),
            ),
        ],
      ),
      if (!_allCams)
        Align(alignment: Alignment.centerLeft,
            child: TextButton(onPressed: () => setState(() => _allCams = true), child: Text('Aur camera', style: body(12.5, color: C.accent)))),
      const SizedBox(height: 14),
      Row(children: [
        const Expanded(child: SLabel('Lambai')),
        Text('$_dur sec', style: body(14, w: FontWeight.w800)),
      ]),
      Slider(value: _dur.toDouble().clamp(2, 30).toDouble(), min: 2, max: 30, divisions: 28, activeColor: C.accent,
          onChanged: (x) => _touch(() => _dur = x.round())),
      if (chars.isNotEmpty) ...[
        const SizedBox(height: 8),
        const SLabel('Is shot mein'),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final c in chars)
            Press(
              onTap: () => _touch(() {
                final n = '${c['name']}';
                if (_chars.contains(n)) {
                  _chars.remove(n);
                } else {
                  _chars.add(n);
                }
              }),
              child: Container(
                height: 42,
                padding: const EdgeInsets.fromLTRB(4, 4, 12, 4),
                decoration: BoxDecoration(
                  color: _chars.contains('${c['name']}') ? C.accent.withOpacity(.12) : Colors.transparent,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: _chars.contains('${c['name']}') ? C.accent : SC.line2),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  SizedBox(width: 32, height: 32, child: SImage(app: app, url: '${c['image'] ?? ''}', radius: 16, icon: Icons.person_rounded)),
                  const SizedBox(width: 8),
                  Text('${c['name']}', style: body(13, w: FontWeight.w700)),
                ]),
              ),
            ),
        ]),
      ],
      const SizedBox(height: 18),
      const SLabel('Caption'),
      _box(_cap, 'Screen par 2-6 shabd (khaali = caption nahi)'),
      const SizedBox(height: 18),
      const SLabel('Agle shot tak'),
      Wrap(spacing: 6, runSpacing: 6, children: [
        for (final t in const {'': 'Cut', 'fade': 'Fade', 'dissolve': 'Dissolve', 'slideleft': 'Slide'}.entries)
          SChip(label: t.value, on: _transition == t.key, onTap: () => _touch(() => _transition = t.key)),
      ]),
      const SizedBox(height: 18),
      Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(16), border: Border.all(color: SC.line)),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('MODEL (APNE AAP)', style: body(10.5, w: FontWeight.w800, color: C.faint)),
              const SizedBox(height: 2),
              Text('${s['model_label'] ?? ''} · ${qualityShort['${v['quality_pref']}'] ?? 'HD'}', style: body(14, w: FontWeight.w800)),
              Text(_kind == 'talk' ? 'tasveer + aawaz se bolta chehra'
                  : _kind == 'product' ? 'product ko saaf, chamakta dikhane ke liye sabse achha'
                  : _kind == 'link' ? 'ek tasveer se doosri tak smooth'
                  : 'kahani wale drishya ke liye sabse achha', style: body(11.5, color: C.faint)),
              if (s['lipsync'] == true) Text('+ Sync 3 lip sync', style: body(11.5, w: FontWeight.w700, color: C.accentSoft)),
            ]),
          ),
        ]),
      ),
    ]);
  }

  Widget _box(TextEditingController c, String hint, {int lines = 1}) => TextField(
        controller: c,
        minLines: lines,
        maxLines: lines == 1 ? 1 : lines + 4,
        onChanged: (_) => setState(() => _dirty = true),
        style: body(14, w: FontWeight.w500, height: 1.45),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: body(13.5, w: FontWeight.w500, color: C.faint),
          filled: true,
          fillColor: SC.card,
          contentPadding: const EdgeInsets.all(12),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: SC.line2)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: C.accent)),
        ),
      );

  Widget _act(IconData icon, String label, VoidCallback? onTap) => Opacity(
        opacity: onTap == null ? .45 : 1,
        child: Press(
          onTap: onTap,
          child: Container(
            height: 44,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(color: SC.card2, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              Icon(icon, size: 16, color: C.ink),
              const SizedBox(width: 8),
              Expanded(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: body(13, w: FontWeight.w700))),
            ]),
          ),
        ),
      );
}
