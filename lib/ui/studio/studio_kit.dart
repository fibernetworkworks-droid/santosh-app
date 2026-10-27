import 'dart:io';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:video_player/video_player.dart';

import '../../state.dart';
import '../glass.dart';

/// v0.159 Hoola Video Studio, rebuilt as a real studio (owner approved the 12 screen designs):
/// shared look, labels and small widgets used by every studio screen.

// ---- palette (Hoola's own dark theme, from the approved designs) ----
class SC {
  static const bg = Color(0xFF0B0A1A);
  static const stage = Color(0xFF06050F);
  static const card = Color(0xFF15112B);
  static const card2 = Color(0xFF1D1838);
  static const field = Color(0xFF0F0C22);
  static const line = Color(0x14FFFFFF);
  static const line2 = Color(0x1FFFFFFF);
  static const teal = Color(0xFF5EEAD4);
  static const violet = Color(0xFFC9BEFF);
}

TextStyle sora(double size, {FontWeight w = FontWeight.w600, Color color = C.ink}) =>
    GoogleFonts.sora(fontSize: size, fontWeight: w, color: color, letterSpacing: -size * .012);
TextStyle body(double size, {FontWeight w = FontWeight.w600, Color color = C.ink, double? height}) =>
    GoogleFonts.manrope(fontSize: size, fontWeight: w, color: color, height: height);

void studioSnack(BuildContext context, String t) =>
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t), behavior: SnackBarBehavior.floating));

List<Map<String, dynamic>> sList(Object? o) =>
    List<Map<String, dynamic>>.from(((o as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> sMap(Object? o) => o is Map ? Map<String, dynamic>.from(o) : <String, dynamic>{};
int sInt(Object? o, [int d = 0]) => (o as num?)?.toInt() ?? d;

/// ₹ with Indian grouping (1,450 / 1,24,500).
String rupees(Object? v) {
  final n = (v as num? ?? 0).round();
  final s = n.abs().toString();
  if (s.length <= 3) return '₹${n < 0 ? '-' : ''}$s';
  final last = s.substring(s.length - 3);
  var rest = s.substring(0, s.length - 3);
  final parts = <String>[];
  while (rest.length > 2) {
    parts.insert(0, rest.substring(rest.length - 2));
    rest = rest.substring(0, rest.length - 2);
  }
  if (rest.isNotEmpty) parts.insert(0, rest);
  return '₹${n < 0 ? '-' : ''}${parts.join(',')},$last';
}

String secs(Object? s) {
  final n = (s as num? ?? 0).round();
  if (n < 60) return '${n}s';
  return '${n ~/ 60}:${(n % 60).toString().padLeft(2, '0')}';
}

const kindLabel = {'scene': 'Drishya', 'product': 'Product', 'talk': 'Bolta hai', 'dialogue': 'Do log baat', 'link': 'Jodne wala'};
const kindColor = {
  'scene': SC.teal, 'product': Color(0xFF7FB2FF), 'talk': C.accentSoft, 'dialogue': C.accentSoft, 'link': SC.violet,
};
const qualityLabel = {'preview': 'Preview', 'draft': 'Draft · 720p', 'final': 'HD · 1080p', 'premium': 'Premium'};
const qualityShort = {'preview': 'Preview', 'draft': 'Draft', 'final': 'HD', 'premium': 'Premium'};
const qualityWhat = {
  'preview': 'Tasveeron se chalti kahani · sirf dekhne ke liye',
  'draft': 'Seedance 2 Fast · tez, idea jaanchne ko',
  'final': 'Wan 3.0 kahani · MiniMax H3 product',
  'premium': 'Seedance 2.5 · film jaisa, sabse saaf chehra',
};
const styleLabel = {
  'reel': 'Reel', 'cinematic': 'Cinematic', 'ad': 'Ad', 'indian_wedding': 'Shaadi', 'documentary': 'Documentary',
  'animation_3d': '3D cartoon', 'anime': 'Anime', 'news': 'News style',
};
const cameraLabel = {
  'static': 'Sthir', 'dolly_in': 'Andar', 'dolly_out': 'Bahar', 'pan_left': 'Pan baayein', 'pan_right': 'Pan daayein',
  'tilt_up': 'Upar', 'tilt_down': 'Neeche', 'orbit': 'Orbit', 'crane_up': 'Crane', 'tracking': 'Peechha',
  'handheld': 'Haath mein', 'drone': 'Drone', 'zoom_in': 'Zoom', 'whip_pan': 'Jhatka pan',
};
const cameraIcon = {
  'static': Icons.crop_square_rounded, 'dolly_in': Icons.zoom_in_map_rounded, 'dolly_out': Icons.zoom_out_map_rounded,
  'pan_left': Icons.west_rounded, 'pan_right': Icons.east_rounded, 'tilt_up': Icons.north_rounded, 'tilt_down': Icons.south_rounded,
  'orbit': Icons.threesixty_rounded, 'crane_up': Icons.height_rounded, 'tracking': Icons.directions_walk_rounded,
  'handheld': Icons.back_hand_rounded, 'drone': Icons.flight_rounded, 'zoom_in': Icons.center_focus_strong_rounded,
  'whip_pan': Icons.swap_horiz_rounded,
};
const moodLabel = {
  'calm': 'Shaant', 'cinematic': 'Cinematic', 'festive': 'Utsav', 'upbeat': 'Upbeat', 'lofi': 'Lofi', 'corporate': 'Office',
};
const langs = [
  ['Hindi', 'हिंदी'], ['Marathi', 'मराठी'], ['English', 'English'], ['Hinglish', 'Hinglish'], ['Tamil', 'தமிழ்'],
  ['Telugu', 'తెలుగు'], ['Bengali', 'বাংলা'], ['Gujarati', 'ગુજરાતી'], ['Kannada', 'ಕನ್ನಡ'], ['Malayalam', 'മലയാളം'],
  ['Punjabi', 'ਪੰਜਾਬੀ'],
];
String langShown(String l) => langs.firstWhere((x) => x[0] == l, orElse: () => [l, l])[1];

/// The tone of a project's placeholder (before a picture exists), stable per name.
Color toneOf(String key) {
  const tones = [Color(0xFF2A1A0C), Color(0xFF10283A), Color(0xFF3B1230), Color(0xFF1A2A1A), Color(0xFF2B1650), Color(0xFF2F2A10)];
  var h = 0;
  for (final c in key.codeUnits) {
    h = (h * 31 + c) & 0x7fffffff;
  }
  return tones[h % tones.length];
}

/// A signed studio picture (opening frame, character photo, thumbnail), with a calm placeholder.
class SImage extends StatelessWidget {
  const SImage({super.key, required this.app, required this.url, this.tone, this.icon, this.radius = 12, this.fit = BoxFit.cover});
  final Santosh app;
  final String url;
  final Color? tone;
  final IconData? icon;
  final double radius;
  final BoxFit fit;

  @override
  Widget build(BuildContext context) {
    final ph = Container(
      color: tone ?? SC.card2,
      alignment: Alignment.center,
      child: icon == null ? null : Icon(icon, color: Colors.white.withOpacity(.35), size: 22),
    );
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: url.isEmpty || app.api == null
          ? ph
          : Image.network(app.api!.absolute(url), fit: fit, gaplessPlayback: true,
              errorBuilder: (_, __, ___) => ph,
              loadingBuilder: (c, child, p) => p == null ? child : Stack(fit: StackFit.expand, children: [ph, child])),
    );
  }
}

/// Small rounded label (kind, model, status).
class Tag extends StatelessWidget {
  const Tag(this.text, {super.key, this.fg = C.chip, this.bg, this.size = 10.5});
  final String text;
  final Color fg;
  final Color? bg;
  final double size;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(color: bg ?? fg.withOpacity(.14), borderRadius: BorderRadius.circular(6)),
        child: Text(text, style: body(size, w: FontWeight.w800, color: fg)),
      );
}

/// Section label in capitals ("LAMBAI", "SHAPE").
class SLabel extends StatelessWidget {
  const SLabel(this.text, {super.key, this.trailing});
  final String text;
  final String? trailing;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Expanded(child: Text(text.toUpperCase(), style: body(12, w: FontWeight.w700, color: C.muted).copyWith(letterSpacing: .4))),
          if (trailing != null) Text(trailing!, style: body(11, w: FontWeight.w600, color: C.faint)),
        ]),
      );
}

/// Section title (Sora) with an optional count / action.
class SHead extends StatelessWidget {
  const SHead(this.text, {super.key, this.trailing, this.onTap});
  final String text;
  final String? trailing;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(children: [
          Expanded(child: Text(text, style: sora(15.5))),
          if (trailing != null)
            onTap == null
                ? Text(trailing!, style: body(12, color: C.faint))
                : TextButton(onPressed: onTap, child: Text(trailing!, style: body(12.5, w: FontWeight.w700, color: C.accent))),
        ]),
      );
}

/// A choice chip in the studio look (selected = saffron outline).
class SChip extends StatelessWidget {
  const SChip({super.key, required this.label, required this.on, required this.onTap, this.icon, this.solid = false});
  final String label;
  final bool on;
  final VoidCallback? onTap;
  final IconData? icon;
  final bool solid;
  @override
  Widget build(BuildContext context) => Press(
        onTap: onTap,
        child: Container(
          height: 38,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: on ? (solid ? C.ink : C.accent.withOpacity(.12)) : Colors.transparent,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: on ? (solid ? C.ink : C.accent) : SC.line2),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            if (icon != null) ...[Icon(icon, size: 15, color: on ? (solid ? SC.bg : C.accentSoft) : C.chip), const SizedBox(width: 6)],
            Text(label, style: body(13, w: on ? FontWeight.w800 : FontWeight.w700, color: on ? (solid ? SC.bg : C.accentSoft) : C.chip)),
          ]),
        ),
      );
}

/// Segmented picker (equal parts).
class SSegment<T> extends StatelessWidget {
  const SSegment({super.key, required this.items, required this.value, required this.onChanged, this.height = 40});
  final Map<T, String> items;
  final T value;
  final ValueChanged<T> onChanged;
  final double height;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(14)),
        child: Row(children: [
          for (final e in items.entries)
            Expanded(
              child: Press(
                onTap: () => onChanged(e.key),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 160),
                  height: height,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(color: e.key == value ? C.accent : Colors.transparent, borderRadius: BorderRadius.circular(10)),
                  child: Text(e.value, textAlign: TextAlign.center,
                      style: body(13, w: e.key == value ? FontWeight.w800 : FontWeight.w700, color: e.key == value ? C.onAccent : C.muted)),
                ),
              ),
            ),
        ]),
      );
}

/// Primary (saffron) and secondary (outlined) buttons of the studio.
class SButton extends StatelessWidget {
  const SButton({super.key, required this.label, required this.onTap, this.icon, this.primary = true, this.height = 52,
      this.busy = false, this.danger = false, this.light = false});
  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final bool primary;
  final double height;
  final bool busy;
  final bool danger;
  final bool light;
  @override
  Widget build(BuildContext context) {
    final fg = primary ? C.onAccent : light ? SC.bg : danger ? const Color(0xFFFCA5A5) : C.ink;
    return Opacity(
      opacity: onTap == null && !busy ? .45 : 1,
      child: Press(
        onTap: busy ? null : onTap,
        child: Container(
          height: height,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: primary ? C.accent : light ? C.ink : Colors.transparent,
            borderRadius: BorderRadius.circular(15),
            border: primary || light ? null : Border.all(color: danger ? C.bad.withOpacity(.5) : const Color(0x29FFFFFF)),
          ),
          alignment: Alignment.center,
          child: busy
              ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.4, color: fg))
              : Row(mainAxisSize: MainAxisSize.min, children: [
                  if (icon != null) ...[Icon(icon, size: 18, color: fg), const SizedBox(width: 8)],
                  Flexible(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: body(14.5, w: FontWeight.w800, color: fg))),
                ]),
        ),
      ),
    );
  }
}

/// The fixed action bar at the bottom of a studio screen.
class SBottomBar extends StatelessWidget {
  const SBottomBar({super.key, required this.child, this.note});
  final Widget child;
  final String? note;
  @override
  Widget build(BuildContext context) => Container(
        padding: EdgeInsets.fromLTRB(16, 12, 16, 12 + MediaQuery.of(context).padding.bottom),
        decoration: const BoxDecoration(color: SC.bg, border: Border(top: BorderSide(color: SC.line))),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (note != null) ...[Text(note!, textAlign: TextAlign.center, style: body(11.5, w: FontWeight.w600, color: C.faint)), const SizedBox(height: 8)],
          child,
        ]),
      );
}

/// Round play button that plays a short sound (a voice sample, a spoken line, the music) from a signed link.
class SoundButton extends StatefulWidget {
  const SoundButton({super.key, required this.app, required this.url, this.size = 40, this.load, this.light = false});
  final Santosh app;
  final String url;
  final double size;
  /// Called when there is no url yet (makes it first, e.g. the voice sample); returns the url.
  final Future<String> Function()? load;
  final bool light;
  @override
  State<SoundButton> createState() => _SoundButtonState();
}

class _SoundButtonState extends State<SoundButton> {
  VideoPlayerController? _c;
  bool _busy = false;
  bool _playing = false;

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  Future<void> _tap() async {
    if (_playing) {
      await _c?.pause();
      setState(() => _playing = false);
      return;
    }
    setState(() => _busy = true);
    try {
      var url = widget.url;
      if (url.isEmpty && widget.load != null) url = await widget.load!();
      if (url.isEmpty) throw 'Abhi sunne ko kuch nahi hai';
      if (_c == null || _c!.dataSource != widget.app.api!.absolute(url)) {
        await _c?.dispose();
        final c = VideoPlayerController.networkUrl(Uri.parse(widget.app.api!.absolute(url)));
        await c.initialize();
        c.addListener(() {
          final v = c.value;
          if (mounted && _playing && !v.isPlaying && v.position >= v.duration) setState(() => _playing = false);
        });
        _c = c;
      }
      await _c!.seekTo(Duration.zero);
      await _c!.play();
      if (mounted) setState(() => _playing = true);
    } catch (e) {
      if (mounted) studioSnack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) => Press(
        onTap: _busy ? null : _tap,
        child: Container(
          width: widget.size,
          height: widget.size,
          decoration: BoxDecoration(shape: BoxShape.circle, color: widget.light ? C.ink : SC.card2),
          alignment: Alignment.center,
          child: _busy
              ? SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: widget.light ? SC.bg : C.ink))
              : Icon(_playing ? Icons.pause_rounded : Icons.play_arrow_rounded, size: widget.size * .5, color: widget.light ? SC.bg : C.ink),
        ),
      );
}

/// An inline video (take / final), tap to play or pause; fills its box like a phone screen.
class SVideo extends StatefulWidget {
  const SVideo({super.key, required this.app, required this.url, this.poster = '', this.loop = true, this.autoplay = false,
      this.badge, this.overlay});
  final Santosh app;
  final String url;
  final String poster;
  final bool loop;
  final bool autoplay;
  final String? badge;
  final Widget? overlay;
  @override
  State<SVideo> createState() => _SVideoState();
}

class _SVideoState extends State<SVideo> {
  VideoPlayerController? _c;
  bool _busy = false;
  String _err = '';

  @override
  void initState() {
    super.initState();
    if (widget.autoplay) _start();
  }

  @override
  void didUpdateWidget(SVideo old) {
    super.didUpdateWidget(old);
    if (old.url != widget.url) {
      _c?.dispose();
      _c = null;
      _err = '';
      if (widget.autoplay) _start();
    }
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    if (widget.url.isEmpty || widget.app.api == null) return;
    setState(() => _busy = true);
    try {
      final c = VideoPlayerController.networkUrl(Uri.parse(widget.app.api!.absolute(widget.url)));
      await c.initialize();
      await c.setLooping(widget.loop);
      c.addListener(() {
        if (mounted) setState(() {});
      });
      await c.play();
      if (!mounted) {
        await c.dispose();
        return;
      }
      setState(() => _c = c);
    } catch (e) {
      if (mounted) setState(() => _err = 'Video nahi chal paya');
    }
    if (mounted) setState(() => _busy = false);
  }

  void _toggle() {
    final c = _c;
    if (c == null) {
      _start();
      return;
    }
    c.value.isPlaying ? c.pause() : c.play();
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final playing = c != null && c.value.isPlaying;
    final dur = c?.value.duration.inMilliseconds ?? 0;
    final pos = c?.value.position.inMilliseconds ?? 0;
    return GestureDetector(
      onTap: _toggle,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Stack(fit: StackFit.expand, children: [
          if (c != null && c.value.isInitialized)
            FittedBox(fit: BoxFit.cover, clipBehavior: Clip.hardEdge,
                child: SizedBox(width: c.value.size.width, height: c.value.size.height, child: VideoPlayer(c)))
          else
            SImage(app: widget.app, url: widget.poster, radius: 0, icon: Icons.movie_rounded),
          if (widget.overlay != null) widget.overlay!,
          if (widget.badge != null)
            Positioned(left: 10, top: 10, child: Tag(widget.badge!, fg: C.ink, bg: const Color(0xB306050F))),
          if (!playing)
            Center(
              child: Container(
                width: 60,
                height: 60,
                decoration: const BoxDecoration(shape: BoxShape.circle, color: Color(0xEBF4F2FF)),
                alignment: Alignment.center,
                child: _busy
                    ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: SC.bg))
                    : const Icon(Icons.play_arrow_rounded, color: SC.bg, size: 34),
              ),
            ),
          if (_err.isNotEmpty)
            Positioned(left: 10, right: 10, bottom: 18, child: Text(_err, textAlign: TextAlign.center, style: body(12, color: C.bad))),
          if (dur > 0)
            Positioned(
              left: 10,
              right: 10,
              bottom: 8,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(2),
                child: LinearProgressIndicator(value: (pos / dur).clamp(0, 1).toDouble(), minHeight: 3,
                    backgroundColor: Colors.white24, color: C.ink),
              ),
            ),
        ]),
      ),
    );
  }
}

/// The aspect ratio of a project shape ("9:16" -> 9/16).
double aspectOf(String a) {
  final p = a.split(':');
  if (p.length != 2) return 9 / 16;
  final w = double.tryParse(p[0]) ?? 9;
  final h = double.tryParse(p[1]) ?? 16;
  return w / h;
}

/// Downloads a finished video to the app cache once (share / save need a local file).
Future<String> localCopy(Santosh app, String url, String name) async {
  final dir = await getTemporaryDirectory();
  final safe = name.replaceAll(RegExp(r'[^\w\-.]'), '_');
  final f = File('${dir.path}/$safe');
  if (await f.exists() && await f.length() > 0) return f.path;
  final res = await http.get(Uri.parse(app.api!.absolute(url))).timeout(const Duration(seconds: 180));
  if (res.statusCode != 200) throw 'Video download nahi ho paya (${res.statusCode})';
  await f.writeAsBytes(res.bodyBytes);
  return f.path;
}

/// Bottom sheet with simple choices; returns the picked key.
Future<T?> pickOne<T>(BuildContext context, String title, Map<T, String> items, {T? current}) => showModalBottomSheet<T>(
      context: context,
      backgroundColor: SC.card,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(padding: const EdgeInsets.fromLTRB(20, 18, 20, 8), child: Text(title, style: sora(17))),
          Flexible(
            child: ListView(shrinkWrap: true, children: [
              for (final e in items.entries)
                ListTile(
                  title: Text(e.value, style: body(14.5, w: e.key == current ? FontWeight.w800 : FontWeight.w600,
                      color: e.key == current ? C.accentSoft : C.ink)),
                  trailing: e.key == current ? const Icon(Icons.check_rounded, color: C.accent) : null,
                  onTap: () => Navigator.pop(ctx, e.key),
                ),
            ]),
          ),
          const SizedBox(height: 8),
        ]),
      ),
    );

/// Waits a moment (lets a screen breathe between server calls).
Future<void> pause([int ms = 400]) => Future<void>.delayed(Duration(milliseconds: ms));
