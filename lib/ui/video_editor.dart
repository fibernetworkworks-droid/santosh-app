import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:video_player/video_player.dart';

import '../state.dart';
import 'attach.dart';
import 'glass.dart';

/// v0.65 Hoola Video Editor: the owner gives raw footage + a line of what she wants; Hoola watches it, plans the edit,
/// renders it, looks at the result itself, fixes what it doesn't like and hands back a finished video. Changes are
/// asked for in plain words ("title bada karo", "music halka") and come back as a new version. Nothing is ever posted
/// by Hoola: she downloads / shares it herself.

const _stageWords = {
  'queued': 'Line mein hai',
  'watching': 'Video dekh raha hai',
  'planning': 'Edit soch raha hai',
  'rendering': 'Bana raha hai',
  'checking': 'Khud check kar raha hai',
  'done': 'Taiyaar',
  'failed': 'Nahi ban paya',
  'cancelled': 'Rok diya',
};
const _active = {'queued', 'watching', 'planning', 'rendering', 'checking'};

String _dur(num? s) {
  if (s == null) return '';
  final t = s.round();
  return t >= 60 ? '${t ~/ 60}:${(t % 60).toString().padLeft(2, '0')} min' : '$t s';
}

void _snack(BuildContext context, String t) =>
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));

/// The live card in chat (and in the editor list). Updates in place as the job moves; done = thumbnail + play,
/// post caption, self-check score, versions and a box for changes.
class VideoJobCard extends StatefulWidget {
  const VideoJobCard({super.key, required this.v, required this.app, this.full = false});
  final Map<String, dynamic> v;
  final Santosh app;
  final bool full;
  @override
  State<VideoJobCard> createState() => _VideoJobCardState();
}

class _VideoJobCardState extends State<VideoJobCard> {
  final _change = TextEditingController();
  bool _busy = false;
  int? _pick; // which version is shown (null = latest)
  Map<String, dynamic>? _fresh;

  Map<String, dynamic> get v {
    final f = _fresh;
    if (f == null) return widget.v;
    return '${f['updated_at'] ?? ''}'.compareTo('${widget.v['updated_at'] ?? ''}') >= 0 ? f : widget.v;
  }

  @override
  void dispose() {
    _change.dispose();
    super.dispose();
  }

  Future<void> _revise() async {
    final t = _change.text.trim();
    if (t.isEmpty || widget.app.api == null) return;
    setState(() => _busy = true);
    try {
      _fresh = await widget.app.api!.videoRevise('${v['id']}', t);
      _change.clear();
      _pick = null;
      if (mounted) _snack(context, 'Theek hai, badal raha hoon. Naya version yahin aayega.');
    } catch (e) {
      if (mounted) _snack(context, 'Nahi ho paya: $e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _cancel() async {
    try {
      _fresh = await widget.app.api!.videoCancel('${v['id']}');
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) _snack(context, 'Nahi ruka: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final status = '${v['status'] ?? 'queued'}';
    final versions = List<Map<String, dynamic>>.from(((v['versions'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final shown = versions.isEmpty ? null : versions[(_pick ?? versions.length - 1).clamp(0, versions.length - 1)];
    final active = _active.contains(status);
    final progress = (v['progress'] as num?)?.toDouble() ?? 0;
    final title = '${v['title'] ?? ''}'.trim();
    return Glass(
      margin: widget.full ? EdgeInsets.zero : const EdgeInsets.symmetric(vertical: 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(active ? Icons.movie_filter_rounded : status == 'done' ? Icons.movie_rounded : Icons.movie_creation_outlined,
              color: status == 'failed' ? C.bad : C.accent),
          const SizedBox(width: 8),
          Expanded(
            child: Text(title.isNotEmpty ? title : 'Video edit · ${v['platform_label'] ?? ''}',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15), maxLines: 2, overflow: TextOverflow.ellipsis),
          ),
          Pill(_stageWords[status] ?? status,
              fg: status == 'done' ? C.ok : status == 'failed' ? C.bad : C.accent),
        ]),
        const SizedBox(height: 6),
        Text('${v['platform_label'] ?? ''} · ${(v['sources'] as List?)?.length ?? 0} file${v['captions'] == true ? ' · captions' : ''}',
            style: const TextStyle(color: C.faint, fontSize: 12)),
        if (active) ...[
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(value: progress > 0 ? progress / 100 : null, minHeight: 6,
                backgroundColor: C.panel, color: C.accent),
          ),
          const SizedBox(height: 6),
          Row(children: [
            Expanded(child: Text('${v['stage'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5))),
            TextButton(onPressed: _cancel, child: const Text('Rok do')),
          ]),
          if ('${v['pending'] ?? ''}'.isNotEmpty)
            Text('Badlav: ${v['pending']}', style: const TextStyle(color: C.faint, fontSize: 12)),
        ],
        if (status == 'failed')
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('${v['error'] ?? 'Kuch gadbad hui.'}', style: const TextStyle(color: C.bad, fontSize: 13)),
          ),
        if (shown != null) ...[
          const SizedBox(height: 10),
          _Thumb(ver: shown, app: widget.app),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            Pill('v${shown['n']}'),
            Pill(_dur(shown['duration'] as num?)),
            Pill('${shown['width']}×${shown['height']}'),
            if (shown['check'] is Map && (shown['check'] as Map)['score'] != null)
              Pill('Khud check: ${(shown['check'] as Map)['score']}/10', fg: C.ok),
          ]),
          if ('${shown['change'] ?? ''}'.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text('Badlav: ${shown['change']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            ),
          if (versions.length > 1) ...[
            const SizedBox(height: 8),
            Wrap(spacing: 6, children: [
              for (var i = 0; i < versions.length; i++)
                ChoiceChip(
                  label: Text('v${versions[i]['n']}'),
                  selected: (_pick ?? versions.length - 1) == i,
                  onSelected: (_) => setState(() => _pick = i),
                ),
            ]),
          ],
          if ('${v['notes'] ?? ''}'.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text('${v['notes']}', style: const TextStyle(fontSize: 13, height: 1.35)),
          ],
          if ('${v['post_caption'] ?? ''}'.isNotEmpty || ((v['hashtags'] as List?) ?? const []).isNotEmpty) ...[
            const SizedBox(height: 8),
            _CaptionBox(text: '${v['post_caption'] ?? ''}', tags: List<String>.from(((v['hashtags'] as List?) ?? const []).map((e) => '$e'))),
          ],
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
              child: GlassButton(
                label: 'Download',
                icon: Icons.download_rounded,
                onTap: () async {
                  final u = widget.app.api?.absolute('${shown['url']}');
                  if (u == null) return;
                  if (!await launchUrl(Uri.parse(u), mode: LaunchMode.externalApplication) && context.mounted) {
                    _snack(context, 'Link nahi khula');
                  }
                },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: GlassButton(
                label: 'Link copy',
                icon: Icons.link_rounded,
                onTap: () {
                  final u = widget.app.api?.absolute('${shown['url']}') ?? '';
                  Clipboard.setData(ClipboardData(text: u));
                  _snack(context, 'Link copy ho gaya (10 din chalega)');
                },
              ),
            ),
          ]),
        ],
        if (status == 'done') ...[
          const SizedBox(height: 10),
          Row(children: [
            Expanded(
              child: TextField(
                controller: _change,
                minLines: 1,
                maxLines: 3,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _revise(),
                decoration: InputDecoration(
                  hintText: 'Kuch badalna hai? "title bada karo", "intro chhota"...',
                  hintStyle: const TextStyle(color: C.faint, fontSize: 13),
                  isDense: true,
                  filled: true,
                  fillColor: C.panel,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                ),
              ),
            ),
            const SizedBox(width: 6),
            IconButton(
              onPressed: _busy ? null : _revise,
              icon: _busy
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.send_rounded, color: C.accent),
            ),
          ]),
        ],
      ]),
    );
  }
}

class _Thumb extends StatelessWidget {
  const _Thumb({required this.ver, required this.app});
  final Map<String, dynamic> ver;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final t = '${ver['thumb'] ?? ''}';
    final w = (ver['width'] as num?)?.toDouble() ?? 9;
    final h = (ver['height'] as num?)?.toDouble() ?? 16;
    final ratio = (w > 0 && h > 0) ? w / h : 9 / 16;
    final img = t.isEmpty
        ? Container(color: C.panel)
        : Image.memory(base64Decode(t), fit: BoxFit.cover, gaplessPlayback: true,
            errorBuilder: (_, __, ___) => Container(color: C.panel));
    return GestureDetector(
      onTap: () {
        final u = app.api?.absolute('${ver['url']}');
        if (u == null) return;
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => VideoPlayScreen(url: u, title: '${ver['name'] ?? 'Video'}')));
      },
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 340),
          child: AspectRatio(
            aspectRatio: ratio,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Stack(fit: StackFit.expand, children: [
                img,
                const Center(
                  child: CircleAvatar(radius: 26, backgroundColor: Color(0x99000000),
                      child: Icon(Icons.play_arrow_rounded, color: Colors.white, size: 34)),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

class _CaptionBox extends StatelessWidget {
  const _CaptionBox({required this.text, required this.tags});
  final String text;
  final List<String> tags;

  @override
  Widget build(BuildContext context) {
    final all = [text, if (tags.isNotEmpty) tags.join(' ')].where((e) => e.trim().isNotEmpty).join('\n\n');
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Post ke liye caption', style: TextStyle(color: C.faint, fontSize: 11.5)),
        const SizedBox(height: 4),
        SelectableText(all, style: const TextStyle(fontSize: 13, height: 1.35)),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton.icon(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: all));
              _snack(context, 'Caption copy ho gaya');
            },
            icon: const Icon(Icons.copy_rounded, size: 16),
            label: const Text('Copy'),
          ),
        ),
      ]),
    );
  }
}

/// Full-screen player for a finished version (signed link from the server).
class VideoPlayScreen extends StatefulWidget {
  const VideoPlayScreen({super.key, required this.url, required this.title});
  final String url;
  final String title;
  @override
  State<VideoPlayScreen> createState() => _VideoPlayScreenState();
}

class _VideoPlayScreenState extends State<VideoPlayScreen> {
  VideoPlayerController? _c;
  String? _err;

  @override
  void initState() {
    super.initState();
    final c = VideoPlayerController.networkUrl(Uri.parse(widget.url));
    _c = c;
    _open(c);
    c.addListener(() {
      if (mounted) setState(() {});
    });
  }

  Future<void> _open(VideoPlayerController c) async {
    try {
      await c.initialize();
      if (!mounted) return;
      await c.setLooping(true);
      await c.play();
      setState(() {});
    } catch (e) {
      if (mounted) setState(() => _err = 'Video nahi chala: $e');
    }
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final ready = c != null && c.value.isInitialized;
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(backgroundColor: Colors.black, title: Text(widget.title, overflow: TextOverflow.ellipsis)),
      body: Center(
        child: _err != null
            ? Padding(padding: const EdgeInsets.all(24), child: Text(_err!, style: const TextStyle(color: C.bad)))
            : !ready
                ? const CircularProgressIndicator()
                : GestureDetector(
                    onTap: () => c.value.isPlaying ? c.pause() : c.play(),
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      Flexible(child: AspectRatio(aspectRatio: c.value.aspectRatio, child: VideoPlayer(c))),
                      VideoProgressIndicator(c, allowScrubbing: true,
                          colors: const VideoProgressColors(playedColor: C.accent),
                          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12)),
                      Icon(c.value.isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded, color: Colors.white, size: 36),
                    ]),
                  ),
      ),
    );
  }
}

/// Profile > "<name> · Video Editor": all edits + a new one.
class VideoEditorScreen extends StatefulWidget {
  const VideoEditorScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<VideoEditorScreen> createState() => _VideoEditorScreenState();
}

class _VideoEditorScreenState extends State<VideoEditorScreen> {
  List<Map<String, dynamic>> _jobs = const [];
  List<Map<String, dynamic>> _platforms = const [];
  bool _loading = true;
  String? _err;
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
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.videoTick != _tick) {
      _tick = app.videoTick;
      _load();
    }
  }

  Future<void> _load() async {
    if (app.api == null) return;
    try {
      final r = await app.api!.videoJobs();
      _jobs = List<Map<String, dynamic>>.from((r['jobs'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
      _platforms = List<Map<String, dynamic>>.from((r['platforms'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
      _err = null;
    } catch (e) {
      _err = '$e';
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _new() async {
    final ok = await Navigator.of(context).push<bool>(
        MaterialPageRoute(builder: (_) => _NewVideoScreen(app: app, platforms: _platforms)));
    if (ok == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C.bgBottom,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${app.aName} · Video Editor')),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: C.accent,
        foregroundColor: C.onAccent,
        onPressed: _new,
        icon: const Icon(Icons.add_rounded),
        label: const Text('Naya video'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 96), children: [
          Glass(
            child: Text(
              'Kachcha video / photos dijiye aur ek line mein bataiye kya chahiye — "dukaan ki 30 sec reel, naya stock dikhao". '
              '${app.aName} video dekhta hai, achhe hisse chunta hai, kaat-chhaant, text, captions, music, logo lagata hai, '
              'phir khud dekh ke check karta hai aur galti ho to theek karta hai. Badlav seedhe shabdon mein boliye. '
              'Post aap khud karti hain — ${app.aName} kuch bhi apne aap post nahi karta.',
              style: const TextStyle(fontSize: 13, height: 1.4, color: C.muted),
            ),
          ),
          const SizedBox(height: 12),
          if (_loading) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
          if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
          if (!_loading && _jobs.isEmpty && _err == null)
            const Padding(
              padding: EdgeInsets.all(30),
              child: Center(child: Text('Abhi koi video nahi. "Naya video" dabaiye.', style: TextStyle(color: C.faint))),
            ),
          for (final j in _jobs) VideoJobCard(key: ValueKey('vjl${j['id']}${j['updated_at']}'), v: j, app: app),
        ]),
      ),
    );
  }
}

class _NewVideoScreen extends StatefulWidget {
  const _NewVideoScreen({required this.app, required this.platforms});
  final Santosh app;
  final List<Map<String, dynamic>> platforms;
  @override
  State<_NewVideoScreen> createState() => _NewVideoScreenState();
}

class _NewVideoScreenState extends State<_NewVideoScreen> {
  final _brief = TextEditingController();
  final List<({String id, String name})> _files = [];
  ({String id, String name})? _logo;
  ({String id, String name})? _music;
  String _platform = 'reel';
  bool _captions = true;
  double _len = 30;
  bool _uploading = false;
  bool _starting = false;

  Santosh get app => widget.app;

  List<Map<String, dynamic>> get _pfs => widget.platforms.isNotEmpty
      ? widget.platforms
      : const [
          {'id': 'reel', 'label': 'Instagram Reel', 'default': 30, 'max': 90},
          {'id': 'short', 'label': 'YouTube Short', 'default': 40, 'max': 180},
          {'id': 'status', 'label': 'WhatsApp Status', 'default': 30, 'max': 60},
          {'id': 'youtube', 'label': 'YouTube video', 'default': 120, 'max': 600},
        ];

  Map<String, dynamic> get _pf => _pfs.firstWhere((p) => p['id'] == _platform, orElse: () => _pfs.first);

  @override
  void dispose() {
    _brief.dispose();
    super.dispose();
  }

  Future<({String id, String name})?> _up(PickedFile f) async {
    final r = await app.attachChatFile(f.name, f.bytes);
    return (id: '${r['file_id']}', name: f.name);
  }

  Future<void> _add(FileType type, {String slot = 'src'}) async {
    final picked = slot == 'src'
        ? await pickAttachments(context, max: 8 - _files.length, showSheet: false, type: type)
        : await pickAttachmentsOfType(context, type);
    if (picked.isEmpty) return;
    setState(() => _uploading = true);
    try {
      for (final f in picked) {
        final r = await _up(f);
        if (r == null) continue;
        if (slot == 'logo') {
          _logo = r;
        } else if (slot == 'music') {
          _music = r;
        } else {
          _files.add(r);
        }
        if (mounted) setState(() {});
      }
    } catch (e) {
      if (mounted) _snack(context, 'Upload nahi hua: $e');
    }
    if (mounted) setState(() => _uploading = false);
  }

  Future<void> _start() async {
    if (_files.isEmpty) {
      _snack(context, 'Pehle video ya photos lagaiye');
      return;
    }
    setState(() => _starting = true);
    try {
      await app.api!.videoStart(_files.map((e) => e.id).toList(), _brief.text.trim(),
          platform: _platform, lengthS: _len.round(), captions: _captions, logoFileId: _logo?.id ?? '',
          musicFileId: _music?.id ?? '', conversationId: app.conversationId ?? '');
      if (!mounted) return;
      _snack(context, '${app.aName} kaam pe lag gaya. Video taiyaar hote hi chat mein aayega.');
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) _snack(context, 'Shuru nahi hua: $e');
    }
    if (mounted) setState(() => _starting = false);
  }

  @override
  Widget build(BuildContext context) {
    final max = ((_pf['max'] as num?) ?? 90).toDouble();
    if (_len > max) _len = max;
    return Scaffold(
      backgroundColor: C.bgBottom,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Naya video')),
      body: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 28), children: [
        const Text('1. Footage', style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final f in _files)
            InputChip(label: Text(f.name, overflow: TextOverflow.ellipsis), onDeleted: () => setState(() => _files.remove(f))),
          ActionChip(
            avatar: const Icon(Icons.video_library_rounded, size: 18),
            label: Text(_files.isEmpty ? 'Video / photos chuniye' : 'Aur jodiye'),
            onPressed: _uploading || _files.length >= 8 ? null : () => _add(FileType.media),
          ),
        ]),
        if (_uploading) const Padding(padding: EdgeInsets.only(top: 8), child: LinearProgressIndicator(color: C.accent)),
        const SizedBox(height: 16),
        const Text('2. Kya chahiye?', style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        TextField(
          controller: _brief,
          minLines: 3,
          maxLines: 6,
          decoration: InputDecoration(
            hintText: 'Jaise: "Diwali sale ki reel, pehle 2 sec mein 50% off dikhao, energetic music, end mein dukaan ka pata"',
            hintStyle: const TextStyle(color: C.faint, fontSize: 13),
            filled: true,
            fillColor: C.panel,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
          ),
        ),
        const SizedBox(height: 16),
        const Text('3. Kahan ke liye?', style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final p in _pfs)
            ChoiceChip(
              label: Text('${p['label']}'),
              selected: _platform == p['id'],
              onSelected: (_) => setState(() {
                _platform = '${p['id']}';
                _len = ((p['default'] as num?) ?? 30).toDouble();
              }),
            ),
        ]),
        const SizedBox(height: 12),
        Text('Lambai: lagbhag ${_dur(_len)}', style: const TextStyle(color: C.muted)),
        Slider(value: _len.clamp(5, max), min: 5, max: max, divisions: ((max - 5) / 5).round().clamp(1, 200),
            activeColor: C.accent, onChanged: (x) => setState(() => _len = x)),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: _captions,
          activeColor: C.accent,
          onChanged: (x) => setState(() => _captions = x),
          title: const Text('Captions (jo bola gaya, video pe likha)'),
        ),
        const SizedBox(height: 4),
        Wrap(spacing: 6, runSpacing: 6, children: [
          ActionChip(
            avatar: const Icon(Icons.branding_watermark_rounded, size: 18),
            label: Text(_logo == null ? 'Logo (optional)' : 'Logo: ${_logo!.name}'),
            onPressed: _uploading ? null : () => _add(FileType.image, slot: 'logo'),
          ),
          ActionChip(
            avatar: const Icon(Icons.music_note_rounded, size: 18),
            label: Text(_music == null ? 'Apna music (optional)' : 'Music: ${_music!.name}'),
            onPressed: _uploading ? null : () => _add(FileType.audio, slot: 'music'),
          ),
        ]),
        const Padding(
          padding: EdgeInsets.only(top: 6),
          child: Text('Music sirf wahi lagaiye jiska haq aapke paas ho.', style: TextStyle(color: C.faint, fontSize: 11.5)),
        ),
        const SizedBox(height: 20),
        GradientButton(
          label: _starting ? 'Shuru ho raha hai...' : 'Video banao',
          icon: Icons.auto_awesome_rounded,
          onTap: _starting || _uploading ? null : _start,
        ),
      ]),
    );
  }
}
