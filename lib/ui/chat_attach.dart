import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../state.dart';
import 'glass.dart';
import 'hoola_media.dart';

/// v0.281 ATTACHMENTS LIKE CLAUDE on the phone (same as the web console's attach.js).
/// Typing box: square tiles - a photo shows itself the moment she picks it (her own bytes), a PDF its first page and
/// a video its frame + length once uploaded (the server's small preview), text its first lines; a real upload bar on
/// each tile, a failed upload stays red with Retry, ✕ removes.
/// Sent message: the same tiles sit ABOVE her bubble, right-aligned; one photo alone shows large in its own shape.
/// Tap: photo / video / audio = a full-screen viewer (swipe between the message's files, pinch to zoom, the FULL photo
/// not the small preview); PDF / Office / any other file opens in the phone's own app (the signed link, as before).

/// The words a files-only message carries to Hoola (the bubble then shows only the tiles).
const fileOnlyText = 'Ye file dekho';

/// One file waiting in the typing box.
class TrayFile {
  TrayFile(this.name, this.bytes) : media = attachKind(name);
  final String name;
  final List<int> bytes;
  String media;
  Map<String, dynamic>? sent;     // the server's answer once uploaded (file_id, preview, pages, duration...)
  double pct = 0;
  String? err;
  Uint8List? _local;
  bool get done => sent != null;
  bool get uploading => sent == null && err == null;
  Uint8List? get localImage => media == 'image' ? (_local ??= Uint8List.fromList(bytes)) : null;
  Map<String, dynamic> get view => {'name': name, 'size': bytes.length, 'media': media, ...?sent};
}

final _img = RegExp(r'\.(png|jpe?g|gif|webp|heic|heif|bmp|avif)$', caseSensitive: false);
final _vid = RegExp(r'\.(mp4|webm|mov|m4v|mkv|3gp)$', caseSensitive: false);
final _aud = RegExp(r'\.(mp3|m4a|ogg|oga|wav|aac|opus|flac)$', caseSensitive: false);

String attachKind(String name, [String media = '']) {
  if (media.isNotEmpty && media != 'other') return media;
  final n = name.toLowerCase();
  if (_img.hasMatch(n)) return 'image';
  if (_vid.hasMatch(n)) return 'video';
  if (_aud.hasMatch(n)) return 'audio';
  if (n.endsWith('.pdf')) return 'pdf';
  if (RegExp(r'\.(docx?|odt|rtf)$').hasMatch(n)) return 'doc';
  if (RegExp(r'\.(xlsx?|csv|ods)$').hasMatch(n)) return 'sheet';
  if (RegExp(r'\.(pptx?|odp|key)$').hasMatch(n)) return 'slides';
  if (RegExp(r'\.(txt|md|json|html?|css|js|py|xml|ya?ml|log|sql)$').hasMatch(n)) return 'text';
  return 'file';
}

String _ext(String name) {
  final m = RegExp(r'\.([A-Za-z0-9]{1,5})$').firstMatch(name);
  return m == null ? 'FILE' : m.group(1)!.toUpperCase();
}

Color _kindColor(String k) => switch (k) {
      'pdf' => const Color(0xFFF07B72),
      'sheet' => const Color(0xFF4CC38A),
      'doc' => const Color(0xFF7FA6F5),
      'slides' => const Color(0xFFF0A35E),
      _ => C.accentSoft,
    };

/// "PDF · 4 pages", "0:14", "Pasted · 9 KB"...
String _meta(Map<String, dynamic> f) {
  final k = attachKind('${f['name'] ?? ''}', '${f['media'] ?? ''}');
  final name = '${f['name'] ?? ''}';
  final tag = name.startsWith('pasted-text-') ? 'Pasted' : _ext(name);
  if (k == 'pdf' && f['pages'] is num) return '$tag · ${f['pages']} ${(f['pages'] as num) == 1 ? 'page' : 'pages'}';
  if ((k == 'video' || k == 'audio') && hoolaDuration(f['duration']).isNotEmpty) return hoolaDuration(f['duration']);
  final s = hoolaSize(f['size']);
  return s.isEmpty ? tag : '$tag · $s';
}

/// One square tile: picture / video frame / first page / first lines / icon + name.
class _Tile extends StatelessWidget {
  const _Tile({required this.f, required this.size, this.local});
  final Map<String, dynamic> f;
  final double size;
  final Uint8List? local;

  @override
  Widget build(BuildContext context) {
    final name = '${f['name'] ?? 'file'}';
    final k = attachKind(name, '${f['media'] ?? ''}');
    final img = local ?? hoolaPreview(f);
    final snippet = '${f['snippet'] ?? ''}';
    Widget nameBar({bool tight = false}) => Container(
          width: double.infinity,
          color: const Color(0xFF1E1A38),
          padding: const EdgeInsets.fromLTRB(8, 5, 8, 6),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(name, maxLines: tight ? 1 : 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: C.ink, height: 1.25)),
            Text(_meta(f), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: C.faint)),
          ]),
        );
    Widget body;
    if ((k == 'image' || k == 'video') && img != null) {
      body = Stack(fit: StackFit.expand, children: [
        Image.memory(img, fit: BoxFit.cover, gaplessPlayback: true, cacheWidth: (size * 3).round(),
            errorBuilder: (_, __, ___) => Center(child: Icon(hoolaFileIcon(k), size: 28, color: C.accentSoft))),
        if (k == 'video') ...[
          const Center(child: _PlayMark()),
          if (hoolaDuration(f['duration']).isNotEmpty)
            Positioned(right: 6, bottom: 6, child: _Badge(hoolaDuration(f['duration']))),
        ],
      ]);
    } else if (k == 'video') {
      body = Container(color: const Color(0xFF1B1830), child: const Center(child: _PlayMark()));
    } else if (img != null) {   // a PDF / Office file's first page
      body = Column(children: [
        Expanded(child: Container(width: double.infinity, color: Colors.white,
            child: Image.memory(img, fit: BoxFit.cover, alignment: Alignment.topCenter, gaplessPlayback: true))),
        nameBar(tight: true),
      ]);
    } else if (snippet.isNotEmpty) {
      body = Column(children: [
        Expanded(child: Container(width: double.infinity, color: const Color(0xFF15122B), padding: const EdgeInsets.fromLTRB(8, 7, 8, 0),
            child: Text(snippet, overflow: TextOverflow.fade,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12, height: 1.35, color: C.muted)))),
        nameBar(tight: true),
      ]);
    } else {
      body = Column(children: [
        Expanded(child: Center(child: Icon(hoolaFileIcon(k), size: 28, color: _kindColor(k)))),
        nameBar(),
      ]);
    }
    return Semantics(
      label: '$name, ${_meta(f)}',
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: const Color(0xFF1A1733), borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0x26FFFFFF))),
        child: ClipRRect(borderRadius: BorderRadius.circular(11), child: body),
      ),
    );
  }
}

class _PlayMark extends StatelessWidget {
  const _PlayMark();
  @override
  Widget build(BuildContext context) => Container(
        width: 34,
        height: 34,
        decoration: const BoxDecoration(color: Color(0xB8110F20), shape: BoxShape.circle),
        child: const Icon(Icons.play_arrow_rounded, color: Colors.white, size: 22),
      );
}

class _Badge extends StatelessWidget {
  const _Badge(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        decoration: BoxDecoration(color: const Color(0xC7110F20), borderRadius: BorderRadius.circular(6)),
        child: Text(text, style: const TextStyle(color: Colors.white, fontSize: 12)),
      );
}

/// The row of tiles above the typing box.
class AttachTray extends StatelessWidget {
  const AttachTray({super.key, required this.files, required this.onRemove, required this.onRetry, required this.onOpen, this.retryLabel = 'Retry'});
  final List<TrayFile> files;
  final void Function(TrayFile) onRemove, onRetry, onOpen;
  final String retryLabel;

  @override
  Widget build(BuildContext context) {
    if (files.isEmpty) return const SizedBox.shrink();
    return SizedBox(
      height: 100,
      child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.fromLTRB(18, 10, 18, 4), children: [
        for (final f in files)
          Padding(
            padding: const EdgeInsets.only(right: 10),
            child: Stack(clipBehavior: Clip.none, children: [
              GestureDetector(
                onTap: f.done ? () => onOpen(f) : null,
                child: Opacity(opacity: f.done ? 1 : .55, child: _Tile(f: f.view, size: 84, local: f.localImage)),
              ),
              if (f.uploading)
                Positioned(left: 0, right: 0, bottom: 0, child: ClipRRect(
                  borderRadius: const BorderRadius.vertical(bottom: Radius.circular(12)),
                  child: LinearProgressIndicator(value: f.pct <= 0 ? null : f.pct.clamp(.04, 1.0).toDouble(), minHeight: 4,
                      backgroundColor: const Color(0x26FFFFFF), color: C.accent),
                )),
              if (f.err != null)
                Positioned.fill(child: Container(
                  decoration: BoxDecoration(color: const Color(0xE6160F24), borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: C.bad.withOpacity(.7))),
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    const Icon(Icons.error_outline_rounded, color: C.bad, size: 20),
                    const SizedBox(height: 4),
                    GestureDetector(
                      onTap: () => onRetry(f),
                      child: Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(color: const Color(0x1FFFFFFF), borderRadius: BorderRadius.circular(8)),
                          child: Text(retryLabel, style: const TextStyle(fontSize: 12, color: C.ink, fontWeight: FontWeight.w500))),
                    ),
                  ]),
                )),
              Positioned(
                top: -7,
                right: -7,
                child: Semantics(
                  button: true,
                  label: 'Remove ${f.name}',
                  child: GestureDetector(
                    onTap: () => onRemove(f),
                    child: Container(
                      width: 24,
                      height: 24,
                      decoration: BoxDecoration(color: const Color(0xFF2A2547), shape: BoxShape.circle,
                          border: Border.all(color: const Color(0x40FFFFFF))),
                      child: const Icon(Icons.close_rounded, size: 14, color: C.ink),
                    ),
                  ),
                ),
              ),
            ]),
          ),
      ]),
    );
  }
}

/// A files-only message: the text is our stand-in (or the old "📎 name" lines), so only the tiles show.
bool filesOnlyText(String text, List files) {
  final t = text.trim();
  if (files.isEmpty) return false;
  if (t == fileOnlyText) return true;
  final lines = t.split('\n').where((l) => l.trim().isNotEmpty).toList();
  return lines.isNotEmpty && lines.every((l) => l.trim().startsWith('📎 '));
}

/// Her sent files, above her bubble.
class SentFiles extends StatelessWidget {
  const SentFiles({super.key, required this.files, required this.app});
  final List files;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final list = [for (final f in files) if (f is Map) Map<String, dynamic>.from(f)];
    if (list.isEmpty) return const SizedBox.shrink();
    final solo = list.length == 1 && const {'image', 'video'}.contains(attachKind('${list[0]['name'] ?? ''}', '${list[0]['media'] ?? ''}'))
        && hoolaPreview(list[0]) != null;
    if (solo) {
      final f = list[0];
      final w = (f['width'] is num) ? (f['width'] as num).toDouble() : 0.0;
      final h = (f['height'] is num) ? (f['height'] as num).toDouble() : 0.0;
      final ratio = (w > 0 && h > 0) ? (w / h).clamp(.62, 1.8).toDouble() : 1.0;
      final video = attachKind('${f['name'] ?? ''}', '${f['media'] ?? ''}') == 'video';
      return Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Semantics(
          button: true,
          label: 'Open ${f['name'] ?? 'photo'}',
          child: GestureDetector(
            onTap: () => openAttachment(context, app, list, 0),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 250, maxHeight: 320),
              child: AspectRatio(
                aspectRatio: ratio,
                child: Container(
                  decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0x26FFFFFF))),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(15),
                    child: Stack(fit: StackFit.expand, children: [
                      Image.memory(hoolaPreview(f)!, fit: BoxFit.cover, gaplessPlayback: true),
                      if (video) ...[
                        const Center(child: _PlayMark()),
                        if (hoolaDuration(f['duration']).isNotEmpty) Positioned(right: 8, bottom: 8, child: _Badge(hoolaDuration(f['duration']))),
                      ],
                    ]),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Wrap(alignment: WrapAlignment.end, spacing: 8, runSpacing: 8, children: [
        for (var i = 0; i < list.length; i++)
          GestureDetector(
            onTap: () => openAttachment(context, app, list, i),
            child: _Tile(f: list[i], size: 104),
          ),
      ]),
    );
  }
}

/// Tap on a tile: pictures / video / audio open full screen, everything else in the phone's own app.
void openAttachment(BuildContext context, Santosh app, List<Map<String, dynamic>> files, int i) {
  final f = files[i];
  final k = attachKind('${f['name'] ?? ''}', '${f['media'] ?? ''}');
  final url = '${f['url'] ?? ''}';
  if (!const {'image', 'video', 'audio'}.contains(k)) {
    if (url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Yeh file ab server par nahi hai (24 ghante baad hat jaati hai).')));
    } else {
      hoolaOpenUrl(app, url);
    }
    return;
  }
  final media = [for (final x in files) if (const {'image', 'video', 'audio'}.contains(attachKind('${x['name'] ?? ''}', '${x['media'] ?? ''}'))) x];
  Navigator.of(context).push(PageRouteBuilder(
    opaque: true,
    pageBuilder: (_, __, ___) => AttachViewer(items: media, start: media.contains(f) ? media.indexOf(f) : 0, app: app),
    transitionsBuilder: (_, a, __, child) => FadeTransition(opacity: a, child: child),
  ));
}

/// The full-screen viewer: swipe between the message's photos / videos / audio, pinch to zoom.
class AttachViewer extends StatefulWidget {
  const AttachViewer({super.key, required this.items, required this.start, required this.app});
  final List<Map<String, dynamic>> items;
  final int start;
  final Santosh app;
  @override
  State<AttachViewer> createState() => _AttachViewerState();
}

class _AttachViewerState extends State<AttachViewer> {
  late final PageController _pages = PageController(initialPage: widget.start);
  late int _at = widget.start;

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final f = widget.items[_at];
    final url = '${f['url'] ?? ''}';
    final count = widget.items.length;
    return Scaffold(
      backgroundColor: const Color(0xFF07060F),
      appBar: AppBar(
        backgroundColor: const Color(0xFF07060F),
        foregroundColor: Colors.white,
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${f['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
          Text([if (count > 1) '${_at + 1} / $count', hoolaSize(f['size'])].where((e) => e.isNotEmpty).join(' · '),
              style: const TextStyle(fontSize: 12, color: Color(0xFFB9B5D0))),
        ]),
        actions: [
          if (url.isNotEmpty)
            IconButton(tooltip: 'Phone mein kholiye / download', onPressed: () => hoolaOpenUrl(widget.app, url), icon: const Icon(Icons.download_rounded)),
        ],
      ),
      body: PageView.builder(
        controller: _pages,
        itemCount: count,
        onPageChanged: (i) => setState(() => _at = i),
        itemBuilder: (_, i) {
          final x = widget.items[i];
          final k = attachKind('${x['name'] ?? ''}', '${x['media'] ?? ''}');
          return k == 'image' ? _FullPhoto(f: x, app: widget.app) : _FullPlayer(key: ValueKey(x['file_id'] ?? i), f: x, app: widget.app, video: k == 'video');
        },
      ),
    );
  }
}

/// The small preview at once, the full photo over it as soon as it arrives.
class _FullPhoto extends StatelessWidget {
  const _FullPhoto({required this.f, required this.app});
  final Map<String, dynamic> f;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final small = hoolaPreview(f);
    final url = '${f['url'] ?? ''}';
    final abs = url.isEmpty ? '' : (app.api?.absolute(url) ?? url);
    return InteractiveViewer(
      maxScale: 5,
      child: Center(
        child: Stack(alignment: Alignment.center, children: [
          if (small != null) Image.memory(small, fit: BoxFit.contain, gaplessPlayback: true),
          if (abs.isNotEmpty)
            Image.network(abs, fit: BoxFit.contain, gaplessPlayback: true,
                frameBuilder: (_, child, frame, sync) => AnimatedOpacity(opacity: frame == null ? 0 : 1, duration: const Duration(milliseconds: 160), child: child),
                errorBuilder: (_, __, ___) => small == null
                    ? const Text('Photo ab server par nahi hai.', style: TextStyle(color: Colors.white70))
                    : const SizedBox.shrink()),
        ]),
      ),
    );
  }
}

class _FullPlayer extends StatefulWidget {
  const _FullPlayer({super.key, required this.f, required this.app, required this.video});
  final Map<String, dynamic> f;
  final Santosh app;
  final bool video;
  @override
  State<_FullPlayer> createState() => _FullPlayerState();
}

class _FullPlayerState extends State<_FullPlayer> {
  VideoPlayerController? _c;
  String? _err;

  @override
  void initState() {
    super.initState();
    final url = '${widget.f['url'] ?? ''}';
    if (url.isEmpty) {
      _err = 'Yeh file ab server par nahi hai.';
      return;
    }
    final c = VideoPlayerController.networkUrl(Uri.parse(widget.app.api?.absolute(url) ?? url));
    _c = c;
    c.initialize().then((_) {
      if (!mounted) return;
      setState(() {});
      c.play();
    }).catchError((Object e) {
      if (mounted) setState(() => _err = 'Chal nahi paya: $e');
    });
    c.addListener(_tick);
  }

  void _tick() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _c?.removeListener(_tick);
    _c?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final small = hoolaPreview(widget.f);
    if (_err != null) return Center(child: Text(_err!, style: const TextStyle(color: Colors.white70)));
    final c = _c;
    if (c == null || !c.value.isInitialized) {
      return Center(child: Stack(alignment: Alignment.center, children: [
        if (small != null && widget.video) Image.memory(small, fit: BoxFit.contain),
        const CircularProgressIndicator(color: C.accent),
      ]));
    }
    final pos = c.value.position, len = c.value.duration;
    String mmss(Duration d) => '${d.inMinutes}:${(d.inSeconds % 60).toString().padLeft(2, '0')}';
    return Column(children: [
      Expanded(
        child: Center(
          child: widget.video
              ? AspectRatio(aspectRatio: c.value.aspectRatio, child: VideoPlayer(c))
              : const Icon(Icons.graphic_eq_rounded, size: 96, color: C.accentSoft),
        ),
      ),
      SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(8, 4, 16, 10),
            child: Row(children: [
              IconButton(
                tooltip: c.value.isPlaying ? 'Pause' : 'Play',
                onPressed: () => c.value.isPlaying ? c.pause() : c.play(),
                icon: Icon(c.value.isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded, color: Colors.white, size: 30),
              ),
              Expanded(child: VideoProgressIndicator(c, allowScrubbing: true,
                  colors: const VideoProgressColors(playedColor: C.accent, bufferedColor: Color(0x55FFFFFF), backgroundColor: Color(0x26FFFFFF)))),
              const SizedBox(width: 10),
              Text('${mmss(pos)} / ${mmss(len)}', style: const TextStyle(color: Colors.white70, fontSize: 12)),
            ]),
          ),
        ),
    ]);
  }
}
