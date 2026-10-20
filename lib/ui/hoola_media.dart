import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

/// v0.43 Hoola Network media: real photos, videos, PDFs and files between avatars, what the avatar SAW in them,
/// and reply ideas. Previews are small JPEGs made by our own server from the real bytes.

Uint8List? hoolaPreview(Map<String, dynamic> b) {
  final p = b['preview'];
  if (p is! String || p.isEmpty) return null;
  try {
    return base64Decode(p);
  } catch (_) {
    return null;
  }
}

String hoolaDuration(dynamic d) {
  final s = (d is num) ? d.round() : 0;
  if (s <= 0) return '';
  return '${s ~/ 60}:${(s % 60).toString().padLeft(2, '0')}';
}

String hoolaSize(dynamic n) {
  final b = (n is num) ? n.toDouble() : 0.0;
  if (b <= 0) return '';
  if (b < 1024 * 1024) return '${(b / 1024).toStringAsFixed(0)} KB';
  return '${(b / 1024 / 1024).toStringAsFixed(1)} MB';
}

IconData hoolaFileIcon(String media) => switch (media) {
      'image' => Icons.image_rounded,
      'video' => Icons.play_circle_fill_rounded,
      'audio' => Icons.graphic_eq_rounded,
      'pdf' => Icons.picture_as_pdf_rounded,
      'doc' => Icons.description_rounded,
      'sheet' => Icons.table_chart_rounded,
      'slides' => Icons.slideshow_rounded,
      _ => Icons.insert_drive_file_rounded,
    };

Future<void> hoolaOpenUrl(Santosh app, String url) async {
  if (url.isEmpty) return;
  final abs = url.startsWith('http') ? url : (app.api?.absolute(url) ?? url);
  await launchUrl(Uri.parse(abs), mode: LaunchMode.externalApplication).catchError((_) => false);
}

/// Where the real file can be opened from: the receiver after Haan (`delivered`), the sender always (`local`).
String hoolaFileUrl(Map<String, dynamic> b) {
  for (final k in const ['delivered', 'local']) {
    final x = b[k];
    if (x is Map && (x['url'] ?? '') != '') return x['url'] as String;
  }
  return '';
}

/// Merges the sender-side view (`local`) into the body so one widget draws both sides.
Map<String, dynamic> hoolaMediaOf(Map<String, dynamic> b) {
  final local = b['local'] is Map ? Map<String, dynamic>.from(b['local'] as Map) : const <String, dynamic>{};
  return {...local, ...b..remove('local')};
}

/// A photo / video / PDF / file inside a card or chat bubble. Tap = full view (photo) or open the real file.
class HoolaMediaTile extends StatelessWidget {
  const HoolaMediaTile({super.key, required this.body, required this.app, this.locked = false, this.maxWidth = 260});
  final Map<String, dynamic> body;
  final Santosh app;
  /// Still in quarantine on the receiver side: show the preview, but the file opens only after Haan.
  final bool locked;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    final b = hoolaMediaOf(Map<String, dynamic>.from(body));
    final name = (b['name'] as String? ?? '').trim();
    if (name.isEmpty && b['preview'] == null) return const SizedBox.shrink();
    final media = b['media'] as String? ?? '';
    final img = hoolaPreview(b);
    final url = hoolaFileUrl(body);
    final w = (b['width'] is num) ? (b['width'] as num).toDouble() : 0.0;
    final h = (b['height'] is num) ? (b['height'] as num).toDouble() : 0.0;
    final ratio = (w > 0 && h > 0) ? (w / h).clamp(0.6, 1.9) : (media == 'pdf' ? 0.75 : 1.4);

    void tap() {
      if (img != null && media == 'image') {
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => _PhotoView(bytes: img, name: name, onOpen: url.isEmpty ? null : () => hoolaOpenUrl(app, url))));
      } else if (url.isNotEmpty) {
        hoolaOpenUrl(app, url);
      } else if (locked) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Pehle "Haan" dabaiye, phir file khulegi.')));
      }
    }

    final meta = [
      if (media == 'pdf' && b['pages'] != null) '${b['pages']} page',
      if (media == 'video' || media == 'audio') hoolaDuration(b['duration']),
      hoolaSize(b['size']),
    ].where((e) => e.isNotEmpty).join(' · ');

    if (img != null) {
      return Padding(
        padding: const EdgeInsets.only(top: 6),
        child: GestureDetector(
          onTap: tap,
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: maxWidth),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Stack(children: [
                AspectRatio(
                  aspectRatio: ratio,
                  child: Image.memory(img, fit: BoxFit.cover, gaplessPlayback: true),
                ),
                if (media == 'video')
                  const Positioned.fill(
                    child: Center(child: Icon(Icons.play_circle_fill_rounded, size: 54, color: Colors.white70)),
                  ),
                if (media == 'pdf')
                  Positioned(
                    left: 8,
                    top: 8,
                    child: _Pill(icon: Icons.picture_as_pdf_rounded, text: 'PDF'),
                  ),
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
                  child: Container(
                    padding: const EdgeInsets.fromLTRB(10, 18, 10, 7),
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Colors.transparent, Color(0xAA000000)]),
                    ),
                    child: Row(children: [
                      Expanded(
                        child: Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600)),
                      ),
                      if (meta.isNotEmpty) Text(meta, style: const TextStyle(color: Colors.white70, fontSize: 11)),
                      if (locked) const Padding(padding: EdgeInsets.only(left: 6), child: Icon(Icons.lock_rounded, size: 14, color: Colors.white70)),
                    ]),
                  ),
                ),
              ]),
            ),
          ),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: tap,
        child: Container(
          constraints: BoxConstraints(maxWidth: maxWidth),
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: const Color(0x14FFFFFF), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0x22FFFFFF))),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(hoolaFileIcon(media), color: media == 'pdf' ? C.bad : C.accentSoft, size: 30),
            const SizedBox(width: 10),
            Flexible(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(name.isEmpty ? 'File' : name, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                if (meta.isNotEmpty) Text(meta, style: const TextStyle(color: C.faint, fontSize: 11.5)),
              ]),
            ),
            const SizedBox(width: 8),
            Icon(locked ? Icons.lock_rounded : (url.isEmpty ? Icons.hourglass_empty_rounded : Icons.open_in_new_rounded), size: 18, color: C.muted),
          ]),
        ),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.icon, required this.text});
  final IconData icon;
  final String text;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(color: const Color(0xCC000000), borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 13, color: Colors.white),
          const SizedBox(width: 3),
          Text(text, style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w700)),
        ]),
      );
}

class _PhotoView extends StatelessWidget {
  const _PhotoView({required this.bytes, required this.name, this.onOpen});
  final Uint8List bytes;
  final String name;
  final VoidCallback? onOpen;
  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(
          backgroundColor: Colors.black,
          title: Text(name, style: const TextStyle(fontSize: 15)),
          actions: [if (onOpen != null) IconButton(tooltip: 'Poori file kholiye', onPressed: onOpen, icon: const Icon(Icons.open_in_new_rounded))],
        ),
        body: Center(
          child: InteractiveViewer(
            maxScale: 5,
            child: Image.memory(bytes, fit: BoxFit.contain),
          ),
        ),
      );
}

/// "Raju ne dekha: ..." — what the avatar saw inside a photo / video / PDF, or read in a document.
class HoolaSeen extends StatelessWidget {
  const HoolaSeen({super.key, required this.app, required this.v});
  final Santosh app;
  final Map<String, dynamic> v;
  @override
  Widget build(BuildContext context) {
    final b = v['body'] is Map ? Map<String, dynamic>.from(v['body'] as Map) : const <String, dynamic>{};
    final seen = ((v['seen'] ?? b['seen']) as String? ?? '').trim();
    final summary = ((v['summary'] ?? b['summary']) as String? ?? '').trim();
    final text = seen.isNotEmpty ? seen : summary;
    if (text.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
      decoration: BoxDecoration(color: const Color(0x182DD4BF), borderRadius: BorderRadius.circular(12)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(seen.isNotEmpty ? Icons.visibility_rounded : Icons.auto_stories_rounded, size: 16, color: C.teal),
        const SizedBox(width: 6),
        Expanded(
          child: Text.rich(TextSpan(children: [
            TextSpan(text: '${app.aName} ne ${seen.isNotEmpty ? 'dekha' : 'padha'}: ', style: const TextStyle(fontWeight: FontWeight.w700, color: C.teal)),
            TextSpan(text: text),
          ]), style: const TextStyle(fontSize: 12.5, height: 1.35)),
        ),
      ]),
    );
  }
}

/// What they want in one line + reply ideas. Tapping an idea never sends: it fills the box / reply.
class HoolaInsight extends StatelessWidget {
  const HoolaInsight({super.key, required this.v, required this.onPick, this.showGist = true});
  final Map<String, dynamic> v;
  final ValueChanged<String> onPick;
  final bool showGist;
  @override
  Widget build(BuildContext context) {
    final b = v['body'] is Map ? Map<String, dynamic>.from(v['body'] as Map) : const <String, dynamic>{};
    final raw = v['insight'] ?? b['insight'];
    if (raw is! Map) return const SizedBox.shrink();
    final ins = Map<String, dynamic>.from(raw);
    final gist = (ins['gist'] as String? ?? '').trim();
    final sugg = List<String>.from((ins['suggestions'] as List? ?? const []).map((e) => '$e'));
    final tone = ins['tone'] as String? ?? '';
    if (gist.isEmpty && sugg.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (showGist && gist.isNotEmpty)
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(tone == 'urgent' ? Icons.priority_high_rounded : Icons.lightbulb_rounded, size: 16, color: tone == 'urgent' ? C.warn : C.accent),
            const SizedBox(width: 6),
            Expanded(child: Text(gist, style: const TextStyle(fontSize: 12.5, color: C.ink, height: 1.3))),
          ]),
        if (sugg.isNotEmpty) ...[
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final s in sugg)
              ActionChip(
                visualDensity: VisualDensity.compact,
                avatar: const Icon(Icons.reply_rounded, size: 14, color: C.accentSoft),
                label: Text(s, style: const TextStyle(fontSize: 12, color: C.chip)),
                backgroundColor: const Color(0x14FFFFFF),
                side: const BorderSide(color: Color(0x22FFFFFF)),
                onPressed: () => onPick(s),
              ),
          ]),
        ],
      ]),
    );
  }
}

/// "Kunal ka Raju → aapka Santosh": both avatars by name on every card.
class HoolaFromTo extends StatelessWidget {
  const HoolaFromTo({super.key, required this.v, required this.app, this.incoming = true});
  final Map<String, dynamic> v;
  final Santosh app;
  final bool incoming;
  @override
  Widget build(BuildContext context) {
    final peer = (v['peer_avatar'] as String? ?? '').trim();
    final owner = (v['peer_owner'] as String? ?? '').trim();
    final mine = (v['my_avatar'] as String? ?? '').trim().isNotEmpty ? v['my_avatar'] as String : app.aName;
    if (peer.isEmpty) return const SizedBox.shrink();
    final them = owner.isEmpty ? peer : '$peer ($owner)';
    return Padding(
      padding: const EdgeInsets.only(top: 2),
      child: Row(children: [
        Flexible(child: Text(incoming ? them : 'Aapka $mine', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5, color: C.chip))),
        const Padding(padding: EdgeInsets.symmetric(horizontal: 4), child: Icon(Icons.arrow_forward_rounded, size: 13, color: C.faint)),
        Flexible(child: Text(incoming ? 'aapka $mine' : them, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5, color: C.accentSoft, fontWeight: FontWeight.w700))),
      ]),
    );
  }
}
