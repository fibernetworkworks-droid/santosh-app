import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:video_player/video_player.dart';

import '../api.dart';
import '../native.dart';
import 'glass.dart';
import 'tv_screen.dart' show HoolaTv;

/// Hoola Motion: short animated reels (business, recipe, logo intro, offer, or any idea) that Hoola writes as code and
/// the server turns into an MP4. Share to WhatsApp / Instagram, save to the gallery, or post to your own YouTube.
class MotionScreen extends StatefulWidget {
  const MotionScreen({super.key, this.kind});
  final String? kind;
  @override
  State<MotionScreen> createState() => _MotionScreenState();
}

class _MotionScreenState extends State<MotionScreen> {
  Map<String, dynamic>? _info;
  List<Map<String, dynamic>> _videos = [];
  String _kind = 'explainer';
  String _aspect = '9:16';
  String _music = 'upbeat';
  final _brief = TextEditingController();
  Map<String, dynamic>? _plan;
  String? _logo; // data URL
  String _busy = '';
  String? _err;
  Timer? _poll;

  Api? get _api => HoolaTv.api;

  List<Map<String, dynamic>> get _kinds =>
      List<Map<String, dynamic>>.from(((_info?['kinds'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
  Map<String, dynamic> get _k => _kinds.firstWhere((k) => k['id'] == _kind, orElse: () => {'id': _kind, 'label': _kind});

  @override
  void initState() {
    super.initState();
    if (widget.kind != null) _kind = widget.kind!;
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    _brief.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final api = _api;
    if (api == null) return;
    try {
      final info = await api.motionKinds();
      final vids = await api.motionList();
      if (!mounted) return;
      setState(() {
        _info = info;
        _videos = vids;
        _err = null;
      });
      _watch();
    } catch (e) {
      if (mounted) setState(() => _err = e is ApiException ? e.message : '$e');
    }
  }

  void _watch() {
    _poll?.cancel();
    if (!_videos.any((v) => v['status'] == 'queued' || v['status'] == 'rendering')) return;
    _poll = Timer(const Duration(seconds: 3), () async {
      try {
        final vids = await _api!.motionList();
        if (!mounted) return;
        final wasBusy = _videos.where((v) => v['status'] != 'done' && v['status'] != 'failed').map((v) => v['id']).toSet();
        setState(() => _videos = vids);
        final justDone = vids.where((v) => wasBusy.contains(v['id']) && v['status'] == 'done').toList();
        if (justDone.isNotEmpty) _snack('"${justDone.first['title']}" taiyaar hai 🎬');
      } catch (_) {}
      _watch();
    });
  }

  void _snack(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _makePlan() async {
    if (_brief.text.trim().length < 3) {
      _snack('Pehle do-teen line likhiye: kis baare mein video chahiye.');
      return;
    }
    setState(() => _busy = 'plan');
    try {
      final r = await _api!.motionPlan(_kind, _brief.text.trim());
      setState(() => _plan = Map<String, dynamic>.from(r['data'] as Map));
    } catch (e) {
      _snack(e is ApiException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _busy = '');
    }
  }

  Future<void> _render() async {
    setState(() => _busy = 'make');
    try {
      final data = {...?_plan, if (_kind == 'logo' && _logo != null) 'logo': _logo};
      await _api!.motionMake(_kind, data: _kind == 'custom' ? {} : data, brief: _kind == 'custom' ? _brief.text.trim() : '',
          aspect: _aspect, music: _music);
      _snack('Video ban rahi hai: 1-3 minute. Neeche dikhegi.');
      setState(() => _plan = null);
      await _load();
    } catch (e) {
      _snack(e is ApiException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _busy = '');
    }
  }

  Future<void> _pickLogo() async {
    final res = await FilePicker.platform.pickFiles(type: FileType.image, withData: true);
    final bytes = res?.files.single.bytes;
    if (bytes == null) return;
    try {
      // shrink to 512 px PNG so it travels light
      final codec = await ui.instantiateImageCodec(bytes, targetWidth: 512);
      final frame = await codec.getNextFrame();
      final png = await frame.image.toByteData(format: ui.ImageByteFormat.png);
      if (png == null) throw 'image';
      final b64 = base64Encode(png.buffer.asUint8List());
      if (b64.length > 650000) {
        _snack('Logo bahut bada hai; chhoti photo chuniye.');
        return;
      }
      setState(() => _logo = 'data:image/png;base64,$b64');
    } catch (_) {
      _snack('Yeh photo padh nahi paye.');
    }
  }

  Widget _chip(String label, bool on, VoidCallback tap) => Padding(
        padding: const EdgeInsets.only(right: 8, bottom: 8),
        child: Press(
          onTap: tap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              color: on ? C.accent : const Color(0x17FFFFFF),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: on ? C.accent : const Color(0x29FFFFFF)),
            ),
            child: Text(label, style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: on ? C.onAccent : C.ink)),
          ),
        ),
      );

  Widget _kindCard(Map<String, dynamic> k) {
    final on = k['id'] == _kind;
    return Press(
      onTap: () => setState(() {
        _kind = k['id'] as String;
        _plan = null;
      }),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 128,
        margin: const EdgeInsets.only(right: 10),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: on ? const Color(0x33FFB15C) : const Color(0x14FFFFFF),
          border: Border.all(color: on ? C.accent : const Color(0x22FFFFFF), width: on ? 1.6 : 1),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${k['emoji']}', style: const TextStyle(fontSize: 26)),
          const SizedBox(height: 6),
          Text('${k['label']}', maxLines: 2, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, height: 1.2)),
        ]),
      ),
    );
  }

  Widget _videoTile(Map<String, dynamic> v) {
    final st = v['status'] as String? ?? '';
    final api = _api!;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Press(
        onTap: st == 'done'
            ? () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MotionPlayerScreen(video: v))).then((_) => _load())
            : null,
        child: Glass(
          radius: 18,
          padding: const EdgeInsets.all(10),
          child: Row(children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: SizedBox(
                width: 64,
                height: 86,
                child: v['thumb'] != null
                    ? Image.network(api.absolute(v['thumb'] as String), fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const ColoredBox(color: Color(0x22FFFFFF)))
                    : ColoredBox(
                        color: const Color(0x22FFFFFF),
                        child: Center(
                            child: st == 'failed'
                                ? const Icon(Icons.error_outline_rounded, color: C.bad)
                                : const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2)))),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${v['title']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                if (st == 'done')
                  Text('${(v['duration'] as num? ?? 0).round()} sec · ${v['aspect']} · tap karke dekhiye', style: const TextStyle(color: C.muted, fontSize: 12)),
                if (st == 'queued' || st == 'rendering') ...[
                  Text(st == 'queued' ? 'Line mein hai…' : 'Ban rahi hai… ${((v['progress'] as num? ?? 0) * 100).round()}%',
                      style: const TextStyle(color: C.muted, fontSize: 12)),
                  const SizedBox(height: 6),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                        value: st == 'queued' ? null : (v['progress'] as num? ?? 0).toDouble(),
                        minHeight: 5,
                        backgroundColor: const Color(0x14FFFFFF),
                        color: C.accent),
                  ),
                ],
                if (st == 'failed') Text('${v['error']}', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.bad, fontSize: 12)),
              ]),
            ),
            if (st == 'failed')
              IconButton(
                icon: const Icon(Icons.delete_outline_rounded, color: C.muted),
                onPressed: () async {
                  await api.motionDelete(v['id'] as String);
                  _load();
                },
              ),
          ]),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final info = _info;
    final ready = info?['ready'] == true;
    final k = _k;
    return Scaffold(
      appBar: AppBar(title: const Text('Hoola Motion'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('Reel / Status ke liye animated video: Hoola khud code mein banata hai.', style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 12),
            if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
            if (info == null && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (info != null && !ready)
              Glass(
                radius: 18,
                padding: const EdgeInsets.all(14),
                child: Text('Server par video banane ka saamaan nahi hai (${info['missing']}). VPS par chalaiye:\n'
                    'bash ~/santosh_app/server/deploy/setup_motion.sh', style: const TextStyle(color: C.warn, fontSize: 13)),
              ),
            if (info != null) ...[
              SizedBox(height: 104, child: ListView(scrollDirection: Axis.horizontal, children: [for (final x in _kinds) _kindCard(x)])),
              const SizedBox(height: 10),
              Text('${k['about'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5, height: 1.35)),
              const SizedBox(height: 12),
              Glass(
                radius: 18,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                child: TextField(
                  controller: _brief,
                  maxLines: 5,
                  minLines: 3,
                  style: const TextStyle(color: C.ink, fontSize: 14.5),
                  decoration: InputDecoration(
                      hintText: 'Jaise: ${k['example'] ?? ''}',
                      hintMaxLines: 4,
                      hintStyle: const TextStyle(color: C.faint, fontSize: 13),
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none),
                ),
              ),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton(
                    onPressed: () => setState(() => _brief.text = '${k['example'] ?? ''}'),
                    child: const Text('Example bhar do', style: TextStyle(color: C.teal))),
              ),
              if (_kind == 'logo')
                Row(children: [
                  GlassButton(label: _logo == null ? 'Logo photo chuniye' : 'Logo badlo', icon: Icons.image_rounded, height: 42, onTap: _pickLogo),
                  if (_logo != null) ...[
                    const SizedBox(width: 10),
                    ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(base64Decode(_logo!.split(',').last), width: 42, height: 42, fit: BoxFit.cover)),
                    IconButton(icon: const Icon(Icons.close_rounded, color: C.muted), onPressed: () => setState(() => _logo = null)),
                  ],
                ]),
              const SizedBox(height: 10),
              const Caption('SIZE'),
              Wrap(children: [
                _chip('📱 Reel 9:16', _aspect == '9:16', () => setState(() => _aspect = '9:16')),
                _chip('⬛ Post 1:1', _aspect == '1:1', () => setState(() => _aspect = '1:1')),
                _chip('🖥 Wide 16:9', _aspect == '16:9', () => setState(() => _aspect = '16:9')),
              ]),
              const Caption('MUSIC'),
              Wrap(children: [
                for (final m in const [('upbeat', '⚡ Upbeat'), ('calm', '🌙 Calm'), ('festive', '🪔 Festive'), ('none', '🔇 Nahi')])
                  _chip(m.$2, _music == m.$1, () => setState(() => _music = m.$1)),
              ]),
              const SizedBox(height: 8),
              if (_plan != null) ...[
                const Caption('VIDEO MEIN KYA AAYEGA (badal sakte hain)'),
                Glass(radius: 18, padding: const EdgeInsets.all(12), child: _PlanEditor(data: _plan!, onChanged: () => setState(() {}))),
                const SizedBox(height: 12),
              ],
              if (_kind != 'custom' && _plan == null)
                GradientButton(
                    label: _busy == 'plan' ? 'Soch raha hoon…' : 'Plan banao',
                    icon: Icons.auto_awesome_rounded,
                    onTap: _busy.isEmpty && ready ? _makePlan : null),
              if (_kind == 'custom' || _plan != null)
                GradientButton(
                    label: _busy == 'make' ? 'Bhej raha hoon…' : 'Video banao',
                    icon: Icons.movie_creation_rounded,
                    onTap: _busy.isEmpty && ready ? _render : null),
              if (_plan != null)
                Center(child: TextButton(onPressed: () => setState(() => _plan = null), child: const Text('Plan dobara banao', style: TextStyle(color: C.muted)))),
              const SizedBox(height: 22),
              const Caption('MERI VIDEOS'),
              if (_videos.isEmpty) const Text('Abhi koi video nahi.', style: TextStyle(color: C.faint)),
              for (final v in _videos) _videoTile(v),
              const SizedBox(height: 10),
              const Text('Har video par "AI · Hoola" likha hota hai (IT Rules 2026). Phone number, daam, tareekh wahi aate hain jo aapne likhe.',
                  style: TextStyle(color: C.faint, fontSize: 11, height: 1.4)),
            ],
          ]),
        ),
      ),
    );
  }
}

/// Edits the plan Hoola wrote (texts, lists of steps / items, colours) before the video is made.
class _PlanEditor extends StatelessWidget {
  const _PlanEditor({required this.data, required this.onChanged});
  final Map<String, dynamic> data;
  final VoidCallback onChanged;

  static const _labels = {
    'brand': 'Naam', 'tagline': 'Tagline', 'emoji': 'Emoji', 'problem': 'Pareshani', 'solution': 'Hum kya karte hain',
    'steps': 'Steps', 'steps_title': 'Steps ka title', 'proof': 'Bharosa', 'cta': 'Aakhri screen', 'title': 'Text', 'sub': 'Chhota text',
    'tag': 'Label', 'big': 'Bada number / offer', 'offer': 'Offer', 'phone': 'Phone', 'place': 'Jagah', 'extra': 'Aur',
    'dish': 'Dish', 'time': 'Samay', 'serves': 'Kitne log', 'level': 'Mushkil', 'ingredients': 'Saamaan', 'ingredients_title': 'Saamaan ka title',
    'qty': 'Kitna', 'name': 'Naam', 'end': 'Aakhri line', 'credit': 'Credit', 'monogram': 'Akshar (logo na ho to)',
    'festival': 'Tyohaar', 'headline': 'Headline', 'big_note': 'Offer ke neeche', 'items_title': 'List ka title', 'items': 'List',
    'dates': 'Tareekh', 'upi': 'UPI', 'colors': 'Rang',
  };

  Widget _field(String label, String value, ValueChanged<String> set, {bool small = false}) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: TextFormField(
          initialValue: value,
          style: TextStyle(color: C.ink, fontSize: small ? 13 : 14),
          decoration: InputDecoration(
            isDense: true,
            labelText: label,
            labelStyle: const TextStyle(color: C.faint, fontSize: 12),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0x33FFFFFF))),
            focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: C.accent)),
          ),
          onChanged: (v) {
            set(v);
            onChanged();
          },
        ),
      );

  Widget _colors(Map<String, dynamic> c) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(children: [
          const Text('Rang  ', style: TextStyle(color: C.faint, fontSize: 12)),
          for (final e in c.entries)
            Container(
              width: 24,
              height: 24,
              margin: const EdgeInsets.only(right: 6),
              decoration: BoxDecoration(
                color: Color(int.tryParse('FF${'${e.value}'.replaceFirst('#', '')}', radix: 16) ?? 0xFF888888),
                shape: BoxShape.circle,
                border: Border.all(color: const Color(0x55FFFFFF)),
              ),
            ),
        ]),
      );

  List<Widget> _build(Map<String, dynamic> m, {String prefix = ''}) {
    final out = <Widget>[];
    for (final key in m.keys.toList()) {
      final v = m[key];
      final label = '$prefix${_labels[key] ?? key}';
      if (key == 'logo') continue;
      if (key == 'colors' && v is Map) {
        out.add(_colors(Map<String, dynamic>.from(v)));
      } else if (v is String) {
        out.add(_field(label, v, (s) => m[key] = s));
      } else if (v is Map) {
        final mm = Map<String, dynamic>.from(v);
        m[key] = mm;
        out.add(Padding(padding: const EdgeInsets.fromLTRB(2, 6, 0, 6), child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, color: C.accent))));
        out.addAll(_build(mm, prefix: ''));
      } else if (v is List) {
        out.add(Padding(padding: const EdgeInsets.fromLTRB(2, 6, 0, 6), child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, color: C.accent))));
        for (var i = 0; i < v.length; i++) {
          final it = v[i];
          if (it is String) {
            out.add(_field('${i + 1}', it, (s) => v[i] = s, small: true));
          } else if (it is Map) {
            final mm = Map<String, dynamic>.from(it);
            v[i] = mm;
            out.addAll(_build(mm, prefix: '${i + 1}. '));
          }
        }
      }
    }
    return out;
  }

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: _build(data));
}

/// Watch a finished video; share it, save it to the gallery, or post it to your own YouTube (your tap approves it).
class MotionPlayerScreen extends StatefulWidget {
  const MotionPlayerScreen({super.key, required this.video});
  final Map<String, dynamic> video;
  @override
  State<MotionPlayerScreen> createState() => _MotionPlayerScreenState();
}

class _MotionPlayerScreenState extends State<MotionPlayerScreen> {
  VideoPlayerController? _vc;
  String _busy = '';
  String? _err;
  String? _local;

  Api? get _api => HoolaTv.api;
  Map<String, dynamic> get _v => widget.video;

  @override
  void initState() {
    super.initState();
    _open();
  }

  @override
  void dispose() {
    _vc?.dispose();
    super.dispose();
  }

  Future<void> _open() async {
    final api = _api;
    if (api == null || _v['url'] == null) return;
    final vc = VideoPlayerController.networkUrl(Uri.parse(api.absolute(_v['url'] as String)));
    try {
      await vc.initialize();
      await vc.setLooping(true);
      await vc.play();
      if (mounted) setState(() => _vc = vc);
    } catch (e) {
      await vc.dispose();
      if (mounted) setState(() => _err = 'Video chal nahi rahi: $e');
    }
  }

  /// The MP4 in the app cache (downloaded once), for share / save.
  Future<String> _file() async {
    if (_local != null && await File(_local!).exists()) return _local!;
    final res = await http.get(Uri.parse(_api!.absolute(_v['url'] as String))).timeout(const Duration(seconds: 120));
    if (res.statusCode != 200) throw 'Download nahi hua (${res.statusCode})';
    final dir = await getTemporaryDirectory();
    final safe = '${_v['title']}'.replaceAll(RegExp(r'[^A-Za-z0-9_-]+'), '_');
    final f = File('${dir.path}/hoola_${safe.isEmpty ? 'video' : safe}_${_v['id']}.mp4');
    await f.writeAsBytes(res.bodyBytes);
    _local = f.path;
    return f.path;
  }

  Future<void> _do(String what, Future<void> Function() fn) async {
    if (_busy.isNotEmpty) return;
    setState(() => _busy = what);
    try {
      await fn();
    } catch (e) {
      _snack(e is ApiException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _busy = '');
    }
  }

  void _snack(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _share() => _do('share', () async {
        final err = await Native.shareFile(await _file(), title: 'Video bhejo');
        if (err != null) _snack(err);
      });

  Future<void> _save() => _do('save', () async {
        final err = await Native.saveVideo(await _file(), 'hoola_${_v['id']}.mp4');
        _snack(err ?? 'Gallery mein save ho gayi (Movies/Hoola)');
      });

  Future<void> _youtube() async {
    final title = TextEditingController(text: '${_v['title']}');
    var privacy = 'private';
    final go = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Apne YouTube par daalein?'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Title')),
            const SizedBox(height: 12),
            for (final p in const [('private', 'Private (sirf aap)'), ('unlisted', 'Unlisted (link wale)'), ('public', 'Public (sab log)')])
              RadioListTile<String>(
                contentPadding: EdgeInsets.zero,
                dense: true,
                value: p.$1,
                groupValue: privacy,
                title: Text(p.$2),
                onChanged: (v) => set(() => privacy = v ?? 'private'),
              ),
            const Text('YouTube par bataya jayega ki yeh AI se bani video hai.', style: TextStyle(fontSize: 12)),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Haan, daalo')),
          ],
        ),
      ),
    );
    if (go != true) return;
    await _do('yt', () async {
      final r = await _api!.motionYoutube(_v['id'] as String, title: title.text.trim(), privacy: privacy);
      final id = r['approval_id'] as String?;
      if (id == null) {
        _snack('${r['say'] ?? 'Chat mein manzoori dijiye'}');
        return;
      }
      final done = await _api!.bazarDecide(id, 'approve');   // the owner's tap above is the approval
      _snack('${done['say'] ?? done['message'] ?? 'YouTube par upload shuru ho gaya'}');
    });
  }

  Future<void> _delete() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Video hatayein?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Nahi')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Hatao', style: TextStyle(color: C.bad))),
        ],
      ),
    );
    if (yes != true) return;
    await _do('del', () async {
      await _api!.motionDelete(_v['id'] as String);
      if (mounted) Navigator.of(context).pop();
    });
  }

  Widget _btn(String key, IconData icon, String label, VoidCallback onTap) => Expanded(
        child: Press(
          onTap: onTap,
          child: Glass(
            radius: 16,
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              _busy == key ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2)) : Icon(icon, color: C.accent),
              const SizedBox(height: 4),
              Text(label, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
            ]),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final vc = _vc;
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: Text('${_v['title']}'), backgroundColor: Colors.black, actions: [
        IconButton(icon: const Icon(Icons.delete_outline_rounded), onPressed: _delete),
      ]),
      body: SafeArea(
        child: Column(children: [
          Expanded(
            child: Center(
              child: vc == null
                  ? (_err != null ? Padding(padding: const EdgeInsets.all(20), child: Text(_err!, style: const TextStyle(color: C.bad))) : const CircularProgressIndicator())
                  : GestureDetector(
                      onTap: () => setState(() => vc.value.isPlaying ? vc.pause() : vc.play()),
                      child: AspectRatio(aspectRatio: vc.value.aspectRatio, child: VideoPlayer(vc)),
                    ),
            ),
          ),
          if (vc != null) VideoProgressIndicator(vc, allowScrubbing: true, colors: const VideoProgressColors(playedColor: C.accent)),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 4),
            child: Row(children: [
              _btn('share', Icons.share_rounded, 'WhatsApp / Insta', _share),
              const SizedBox(width: 8),
              _btn('save', Icons.download_rounded, 'Gallery', _save),
              const SizedBox(width: 8),
              _btn('yt', Icons.smart_display_rounded, 'YouTube', _youtube),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 10, top: 4),
            child: Text('${_v['ai_label'] ?? 'AI se bani video · Hoola'}', style: const TextStyle(color: C.faint, fontSize: 11)),
          ),
        ]),
      ),
    );
  }
}

/// The card in chat when a video Hoola was asked to make is ready.
class MotionCard extends StatelessWidget {
  const MotionCard({super.key, required this.v});
  final Map<String, dynamic> v;

  @override
  Widget build(BuildContext context) {
    final api = HoolaTv.api;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Press(
        onTap: () async {
          if (api == null) return;
          try {
            final full = await api.motionGet(v['id'] as String);
            if (context.mounted) Navigator.of(context).push(MaterialPageRoute(builder: (_) => MotionPlayerScreen(video: full)));
          } catch (_) {}
        },
        child: Glass(
          radius: 18,
          padding: const EdgeInsets.all(10),
          child: Row(children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: SizedBox(
                width: 60,
                height: 80,
                child: (v['thumb'] != null && api != null)
                    ? Image.network(api.absolute(v['thumb'] as String), fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const ColoredBox(color: Color(0x22FFFFFF)))
                    : const ColoredBox(color: Color(0x22FFFFFF), child: Icon(Icons.movie_rounded, color: C.accent)),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('🎬 Video taiyaar', style: TextStyle(color: C.accent, fontWeight: FontWeight.w800, fontSize: 12)),
                const SizedBox(height: 2),
                Text('${v['title']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 2),
                Text('${(v['duration'] as num? ?? 0).round()} sec · dekhne / bhejne ke liye tap kijiye',
                    style: const TextStyle(color: C.muted, fontSize: 12)),
              ]),
            ),
            const Icon(Icons.play_circle_fill_rounded, color: C.accent, size: 34),
          ]),
        ),
      ),
    );
  }
}
