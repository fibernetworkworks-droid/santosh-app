// v0.895 ATTACH LIKE CLAUDE (owner: "UPLOAD OF IMAGE, VIDEO, APK, DOCUMENT ETC --- MAKE IT PERFECTLY SAME AS CLAUDE
// DOES. 1) MULTIFILE ATTACHMENT 2) ANY FILE ATTACHMENT 3) OPTION LIKE CLAUDE HAS IN ADD SECTION 4) IN CHAT SPACE IMAGES
// AND ALL FILES SHOULD LAND PROPERLY"), read from her four Claude screenshots:
//   typing box  = big rounded thumbnails in a row above the words (a photo shows itself the moment she picks it), a dark
//                 round x on each, a spinner while it goes up, red + Retry when it did not
//   + button    = an "Add to chat" sheet: Camera / Photos / Files tiles, then the switches and places (Research, Memory,
//                 Connectors, Your computers, AI team)
//   chat        = her files land ABOVE her bubble, right-aligned: one photo alone large in its own shape, several as a
//                 row of big thumbnails she can swipe; tap = the full-screen viewer (photos / video / audio) or the phone's
//                 own app (PDF, APK, any other file)
// The new design only; the old look keeps lib/ui/chat_attach.dart. Colours come from the theme roles.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../state.dart';
import '../chat_attach.dart' show TrayFile, attachKind, openAttachment;
import '../hoola_media.dart';
import '../hoola_theme.dart';

/// Claude's limits: 20 files in one message, 30 MB each (the server holds the same numbers).
const hoolaMaxFiles = 20;
const hoolaMaxBytes = 30 * 1024 * 1024;

String _ext(String name) {
  final m = RegExp(r'\.([A-Za-z0-9]{1,5})$').firstMatch(name);
  return m == null ? 'FILE' : m.group(1)!.toUpperCase();
}

/// "PDF · 4 pages", "APK · 18.2 MB", "0:14"...
String hoolaFileMeta(Map<String, dynamic> f) {
  final name = '${f['name'] ?? ''}';
  final k = attachKind(name, '${f['media'] ?? ''}');
  final tag = _ext(name);
  if (k == 'pdf' && f['pages'] is num) return '$tag · ${f['pages']} ${(f['pages'] as num) == 1 ? 'page' : 'pages'}';
  if ((k == 'video' || k == 'audio') && hoolaDuration(f['duration']).isNotEmpty) return '$tag · ${hoolaDuration(f['duration'])}';
  final n = (f['size'] is num) ? (f['size'] as num).toDouble() : 0.0;
  final s = n <= 0 ? '' : (n < 1024 ? '1 KB' : hoolaSize(n));
  return s.isEmpty ? tag : '$tag · $s';
}

IconData _icon(String k, String name) {
  if (name.toLowerCase().endsWith('.apk') || name.toLowerCase().endsWith('.aab')) return Icons.android_rounded;
  if (RegExp(r'\.(zip|rar|7z|tar|gz)$', caseSensitive: false).hasMatch(name)) return Icons.folder_zip_outlined;
  return switch (k) {
    'image' => Icons.image_outlined,
    'video' => Icons.movie_outlined,
    'audio' => Icons.graphic_eq_rounded,
    'pdf' => Icons.picture_as_pdf_outlined,
    'doc' => Icons.description_outlined,
    'sheet' => Icons.table_chart_outlined,
    'slides' => Icons.slideshow_outlined,
    'text' => Icons.notes_rounded,
    _ => Icons.insert_drive_file_outlined,
  };
}

/// One square thumbnail: the photo / video frame / first page / first lines, or the kind's icon + name + size.
class HoolaFileTile extends StatelessWidget {
  const HoolaFileTile({super.key, required this.f, required this.size, this.local});
  final Map<String, dynamic> f;
  final double size;
  final Uint8List? local;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final name = '${f['name'] ?? 'file'}';
    final k = attachKind(name, '${f['media'] ?? ''}');
    final img = local ?? hoolaPreview(f);
    final snippet = '${f['snippet'] ?? ''}';
    Widget body;
    if ((k == 'image' || k == 'video') && img != null) {
      body = Stack(fit: StackFit.expand, children: [
        Image.memory(img, fit: BoxFit.cover, gaplessPlayback: true,
            cacheWidth: (size * 3).round(),
            errorBuilder: (_, __, ___) => Center(child: Icon(_icon(k, name), size: 28, color: c.ink3))),
        if (k == 'video') ...[
          const Center(child: _Play()),
          if (hoolaDuration(f['duration']).isNotEmpty)
            Positioned(right: 6, bottom: 6, child: _Pill(hoolaDuration(f['duration']))),
        ],
      ]);
    } else if (k == 'video') {
      body = Container(color: c.ink, child: const Center(child: _Play()));
    } else if (img != null) {
      // a PDF / Office file's first page on white, the name under it
      body = Column(children: [
        Expanded(
          child: Container(
            width: double.infinity,
            color: c.surface,
            child: Image.memory(img, fit: BoxFit.cover, alignment: Alignment.topCenter, gaplessPlayback: true),
          ),
        ),
        _NameBar(name: name, meta: hoolaFileMeta(f), lines: 1),
      ]);
    } else if (snippet.isNotEmpty) {
      body = Column(children: [
        Expanded(
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
            child: Text(snippet,
                overflow: TextOverflow.fade, style: HoolaType.code(c, size: 12).copyWith(color: c.ink2, height: 1.35)),
          ),
        ),
        _NameBar(name: name, meta: hoolaFileMeta(f), lines: 1),
      ]);
    } else {
      body = Column(children: [
        Expanded(child: Center(child: Icon(_icon(k, name), size: size > 100 ? 34 : 28, color: c.ink2))),
        _NameBar(name: name, meta: hoolaFileMeta(f), lines: 2),
      ]);
    }
    return Semantics(
      container: true,
      label: '$name, ${hoolaFileMeta(f)}',
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: c.sunk,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: c.line),
        ),
        child: ClipRRect(borderRadius: BorderRadius.circular(15), child: body),
      ),
    );
  }
}

class _NameBar extends StatelessWidget {
  const _NameBar({required this.name, required this.meta, required this.lines});
  final String name, meta;
  final int lines;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      width: double.infinity,
      color: c.surface,
      padding: const EdgeInsets.fromLTRB(8, 5, 8, 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text(name, maxLines: lines, overflow: TextOverflow.ellipsis,
            style: HoolaType.small(c).copyWith(color: c.ink, fontWeight: FontWeight.w500, height: 1.25)),
        Text(meta, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.ink3, height: 1.25)),
      ]),
    );
  }
}

class _Play extends StatelessWidget {
  const _Play();
  @override
  Widget build(BuildContext context) => Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(color: Colors.black.withOpacity(.55), shape: BoxShape.circle),
        child: const Icon(Icons.play_arrow_rounded, color: Colors.white, size: 24),
      );
}

class _Pill extends StatelessWidget {
  const _Pill(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        decoration: BoxDecoration(color: Colors.black.withOpacity(.6), borderRadius: BorderRadius.circular(6)),
        child: Text(text, style: HoolaType.small(HoolaColors.of(context)).copyWith(color: Colors.white)),
      );
}

// ------------------------------------------------------------------------------------------------ the typing box tray

/// The row of thumbnails inside the typing box (Claude: ~100 dp rounded cards, a dark round x on each).
class HoolaAttachTray extends StatelessWidget {
  const HoolaAttachTray({super.key, required this.files, required this.onRemove, required this.onRetry, required this.onOpen});
  final List<TrayFile> files;
  final void Function(TrayFile) onRemove, onRetry, onOpen;

  static const double tile = 100;

  @override
  Widget build(BuildContext context) {
    if (files.isEmpty) return const SizedBox.shrink();
    final c = HoolaColors.of(context);
    return SizedBox(
      height: tile + 14,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(10, 10, 10, 4),
        itemCount: files.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final f = files[i];
          return SizedBox(
            width: tile,
            height: tile,
            child: Stack(children: [
              GestureDetector(
                onTap: f.done ? () => onOpen(f) : null,
                child: HoolaFileTile(f: f.view, size: tile, local: f.localImage),
              ),
              if (f.uploading)
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(color: c.scrim.withOpacity(.35), borderRadius: BorderRadius.circular(16)),
                    child: Center(
                      child: SizedBox(
                        width: 26,
                        height: 26,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.5,
                          value: f.pct <= 0 ? null : f.pct.clamp(.05, 1.0).toDouble(),
                          color: Colors.white,
                          backgroundColor: Colors.white.withOpacity(.3),
                        ),
                      ),
                    ),
                  ),
                ),
              if (f.err != null)
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(
                      color: c.surface.withOpacity(.92),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: c.bad, width: 1.5),
                    ),
                    padding: const EdgeInsets.all(6),
                    child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Icon(Icons.error_outline_rounded, color: c.bad, size: 20),
                      const SizedBox(height: 3),
                      Text(f.err!, maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                          style: HoolaType.small(c).copyWith(color: c.ink, height: 1.2)),
                      if (f.bytes.isNotEmpty && f.bytes.length <= hoolaMaxBytes) ...[
                        const SizedBox(height: 4),
                        Semantics(
                          container: true,
                          button: true,
                          label: 'Try ${f.name} again',
                          excludeSemantics: true,
                          child: GestureDetector(
                            onTap: () => onRetry(f),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                              decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(8)),
                              child: Text('Retry', style: HoolaType.small(c).copyWith(color: c.ink, fontWeight: FontWeight.w600)),
                            ),
                          ),
                        ),
                      ],
                    ]),
                  ),
                ),
              Positioned(
                top: 5,
                right: 5,
                child: Semantics(
                  container: true,
                  button: true,
                  label: 'Remove ${f.name}',
                  excludeSemantics: true,
                  child: GestureDetector(
                    onTap: () => onRemove(f),
                    behavior: HitTestBehavior.opaque,
                    child: Padding(
                      padding: const EdgeInsets.all(2),
                      child: Container(
                        width: 26,
                        height: 26,
                        decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle),
                        child: Icon(Icons.close_rounded, size: 16, color: c.onPill),
                      ),
                    ),
                  ),
                ),
              ),
            ]),
          );
        },
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ her sent files

/// Her files above her bubble, right-aligned: one photo / video alone shows large in its own shape; several (or any
/// other file) sit as big thumbnails in a row she can swipe, the newest edge on the right like Claude.
class HoolaSentFiles extends StatelessWidget {
  const HoolaSentFiles({super.key, required this.files, required this.app});
  final List files;
  final Santosh app;

  static const double tile = 112;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final list = [for (final f in files) if (f is Map) Map<String, dynamic>.from(f)];
    if (list.isEmpty) return const SizedBox.shrink();
    final first = list.first;
    final firstKind = attachKind('${first['name'] ?? ''}', '${first['media'] ?? ''}');
    if (list.length == 1 && (firstKind == 'image' || firstKind == 'video') && hoolaPreview(first) != null) {
      final w = (first['width'] is num) ? (first['width'] as num).toDouble() : 0.0;
      final h = (first['height'] is num) ? (first['height'] as num).toDouble() : 0.0;
      final ratio = (w > 0 && h > 0) ? (w / h).clamp(.6, 1.9).toDouble() : 1.0;
      return Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Align(
          alignment: Alignment.centerRight,
          child: Semantics(
            button: true,
            label: 'Open ${first['name'] ?? 'photo'}',
            child: GestureDetector(
              onTap: () => openAttachment(context, app, list, 0),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 260, maxHeight: 320),
                child: AspectRatio(
                  aspectRatio: ratio,
                  child: Container(
                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(18), border: Border.all(color: c.line)),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(17),
                      child: Stack(fit: StackFit.expand, children: [
                        Image.memory(hoolaPreview(first)!, fit: BoxFit.cover, gaplessPlayback: true),
                        if (firstKind == 'video') ...[
                          const Center(child: _Play()),
                          if (hoolaDuration(first['duration']).isNotEmpty)
                            Positioned(right: 8, bottom: 8, child: _Pill(hoolaDuration(first['duration']))),
                        ],
                      ]),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    }
    // reverse: the row starts on the right edge (under her bubble) and swipes left for more
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: SizedBox(
        height: tile,
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          reverse: true,
          child: Row(children: [
            for (var i = 0; i < list.length; i++) ...[
              if (i > 0) const SizedBox(width: 8),
              Semantics(
                button: true,
                label: 'Open ${list[i]['name'] ?? 'file'}',
                child: GestureDetector(
                  onTap: () => openAttachment(context, app, list, i),
                  child: HoolaFileTile(f: list[i], size: tile),
                ),
              ),
            ],
          ]),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ the Add sheet

enum HoolaAddPick { camera, photos, files, connectors, computers, team }

/// Claude's "Add to session" sheet for Hoola: Camera / Photos / Files, then the Research switch (this chat's next
/// messages search deeply), the Memory switch (Hoola uses and saves what it remembers, her memory setting), and the
/// places: Connectors, Your computers, AI team. Returns what she tapped (switches change in place).
Future<HoolaAddPick?> showHoolaAddSheet(
  BuildContext context, {
  required Santosh app,
  required bool research,
  required ValueChanged<bool> onResearch,
}) {
  HapticFeedback.selectionClick();
  return showModalBottomSheet<HoolaAddPick>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: HoolaColors.of(context).bg,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
    builder: (_) => HoolaTheme(appearance: app.appearance, child: _AddSheet(app: app, research: research, onResearch: onResearch)),
  );
}

class _AddSheet extends StatefulWidget {
  const _AddSheet({required this.app, required this.research, required this.onResearch});
  final Santosh app;
  final bool research;
  final ValueChanged<bool> onResearch;
  @override
  State<_AddSheet> createState() => _AddSheetState();
}

class _AddSheetState extends State<_AddSheet> {
  late bool _research = widget.research;
  bool? _memory;   // null = still reading her setting
  bool _memBusy = false;

  @override
  void initState() {
    super.initState();
    _readMemory();
  }

  Future<void> _readMemory() async {
    try {
      final s = await widget.app.api!.memorySettings();
      if (mounted) setState(() => _memory = s['recall'] != false && s['auto'] != false);
    } catch (_) {
      if (mounted) setState(() => _memory = true);
    }
  }

  Future<void> _setMemory(bool on) async {
    final was = _memory;
    setState(() {
      _memory = on;
      _memBusy = true;
    });
    try {
      await widget.app.api!.memorySwitches(auto: on, recall: on);
    } catch (_) {
      if (mounted) {
        setState(() => _memory = was);
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(const SnackBar(content: Text('Memory was not changed. Try again.')));
      }
    }
    if (mounted) setState(() => _memBusy = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    Widget tile(String label, IconData icon, HoolaAddPick pick) => Expanded(
          child: Semantics(
            button: true,
            label: label,
            excludeSemantics: true,
            child: Material(
              color: c.surface,
              borderRadius: BorderRadius.circular(20),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () => Navigator.of(context).pop(pick),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 18),
                  child: Column(children: [
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(color: c.sunk, shape: BoxShape.circle),
                      child: Icon(icon, size: 24, color: c.ink),
                    ),
                    const SizedBox(height: 10),
                    Text(label, style: HoolaType.bodyLarge(c)),
                  ]),
                ),
              ),
            ),
          ),
        );
    Widget row(String title, IconData icon, {String? sub, Widget? trailing, VoidCallback? onTap}) => InkWell(
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 64),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(color: c.sunk, shape: BoxShape.circle),
                  child: Icon(icon, size: 22, color: c.ink),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                    Text(title, style: HoolaType.bodyLarge(c)),
                    if (sub != null) Text(sub, style: HoolaType.small(c).copyWith(color: c.ink3)),
                  ]),
                ),
                trailing ?? Icon(Icons.chevron_right_rounded, color: c.ink3),
              ]),
            ),
          ),
        );
    Widget group(List<Widget> rows) => Container(
          decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(20)),
          clipBehavior: Clip.antiAlias,
          child: Column(children: [
            for (var i = 0; i < rows.length; i++) ...[
              if (i > 0) Divider(height: 1, thickness: 1, color: c.line, indent: 74),
              rows[i],
            ],
          ]),
        );
    return SafeArea(
      top: false,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 18),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Row(children: [
            IconButton(
              tooltip: 'Close',
              onPressed: () => Navigator.of(context).pop(),
              icon: Icon(Icons.close_rounded, color: c.ink),
            ),
            Expanded(child: Text('Add to chat', textAlign: TextAlign.center, style: HoolaType.title(c))),
            const SizedBox(width: 48),
          ]),
          const SizedBox(height: 12),
          Row(children: [
            tile('Camera', Icons.photo_camera_outlined, HoolaAddPick.camera),
            const SizedBox(width: 10),
            tile('Photos', Icons.photo_library_outlined, HoolaAddPick.photos),
            const SizedBox(width: 10),
            tile('Files', Icons.upload_file_outlined, HoolaAddPick.files),
          ]),
          const SizedBox(height: 14),
          group([
            row('Research', Icons.travel_explore_rounded,
                sub: 'Searches the web in depth and cites sources',
                onTap: () {
                  setState(() => _research = !_research);
                  widget.onResearch(_research);
                },
                trailing: Switch(
                  value: _research,
                  activeColor: c.onAccent,
                  activeTrackColor: c.accent,
                  onChanged: (v) {
                    setState(() => _research = v);
                    widget.onResearch(v);
                  },
                )),
          ]),
          const SizedBox(height: 14),
          group([
            row('Connectors', Icons.power_outlined, onTap: () => Navigator.of(context).pop(HoolaAddPick.connectors)),
            row('Your computers', Icons.computer_outlined, onTap: () => Navigator.of(context).pop(HoolaAddPick.computers)),
            row('AI team', Icons.groups_outlined, onTap: () => Navigator.of(context).pop(HoolaAddPick.team)),
            row('Memory', Icons.psychology_outlined,
                sub: _memory == false ? 'Off: Hoola will not use or save memory' : 'Hoola uses and saves what it learns',
                onTap: (_memory == null || _memBusy) ? null : () => _setMemory(!(_memory ?? true)),
                trailing: Switch(
                  value: _memory ?? true,
                  activeColor: c.onAccent,
                  activeTrackColor: c.accent,
                  onChanged: (_memory == null || _memBusy) ? null : _setMemory,
                )),
          ]),
        ]),
      ),
    );
  }
}
