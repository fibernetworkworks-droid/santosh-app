// v0.155 Hoola Notebook: the Studio viewers (audio with Join, video, slides with revise, infographic, mind map,
// report, flashcards, quiz, data table, deep research) + the small Markdown renderer with tappable [n] citations.
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:video_player/video_player.dart' hide Caption;

import '../native.dart';
import '../state.dart';
import 'glass.dart';
import 'video_editor.dart' show VideoPlayScreen;

List<Map<String, dynamic>> nbList(Object? o) =>
    List<Map<String, dynamic>>.from(((o as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> nbMap(Object? o) => o is Map ? Map<String, dynamic>.from(o) : <String, dynamic>{};

void nbSnack(BuildContext context, String t) {
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
}

String nbMime(String name) {
  final ext = name.split('.').last.toLowerCase();
  return switch (ext) {
    'mp3' => 'audio/mpeg',
    'wav' => 'audio/wav',
    'mp4' => 'video/mp4',
    'png' => 'image/png',
    'jpg' || 'jpeg' => 'image/jpeg',
    'pdf' => 'application/pdf',
    'pptx' => 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'docx' => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xlsx' => 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'csv' => 'text/csv',
    'srt' || 'md' || 'txt' => 'text/plain',
    _ => 'application/octet-stream',
  };
}

/// Download one Studio file (signed link) into the cache and hand it to Android's share sheet, or the gallery.
Future<void> nbShareFile(BuildContext context, Santosh app, String url, String name, {String title = 'Bhejo', bool gallery = false}) async {
  try {
    final res = await http.get(Uri.parse(app.api!.absolute(url))).timeout(const Duration(seconds: 180));
    if (res.statusCode >= 400) throw Exception('Download nahi hua (${res.statusCode})');
    final dir = await getTemporaryDirectory();
    final f = File('${dir.path}/shared/$name');
    await f.parent.create(recursive: true);
    await f.writeAsBytes(res.bodyBytes);
    final ext = name.split('.').last.toLowerCase();
    String? err;
    if (gallery && (ext == 'mp4')) {
      err = await Native.saveVideo(f.path, name);
    } else if (gallery) {
      err = await Native.saveImage(f.path, name);
    } else {
      err = await Native.shareFile(f.path, mime: nbMime(name), title: title);
    }
    if (context.mounted) nbSnack(context, err ?? (gallery ? 'Gallery mein save ho gaya' : 'Share sheet khul gayi'));
  } catch (e) {
    if (context.mounted) nbSnack(context, '$e');
  }
}

/// The files of a Studio item as share chips (PDF / PowerPoint / Word / Excel / PNG / MP3 / MP4 ...).
class NbFileChips extends StatelessWidget {
  const NbFileChips({super.key, required this.app, required this.files, this.skip = const {}});
  final Santosh app;
  final Map<String, dynamic> files;
  final Set<String> skip;
  static const _labels = {
    'pdf': ('PDF', Icons.picture_as_pdf_rounded), 'pptx': ('PowerPoint', Icons.slideshow_rounded),
    'docx': ('Word', Icons.description_rounded), 'xlsx': ('Excel', Icons.table_chart_rounded),
    'csv': ('CSV', Icons.grid_on_rounded), 'md': ('Markdown', Icons.notes_rounded), 'mp3': ('MP3', Icons.audiotrack_rounded),
    'wav': ('Audio', Icons.audiotrack_rounded), 'mp4': ('Video', Icons.movie_rounded), 'srt': ('Captions', Icons.subtitles_rounded),
    'png': ('Image', Icons.image_rounded),
  };
  @override
  Widget build(BuildContext context) {
    final names = files.keys.where((n) => !skip.contains(n) && !n.startsWith('frame-') && !n.startsWith('pic-') &&
        !n.startsWith('slide-') && !n.startsWith('join-') && n != 'cover.jpg').toList()..sort();
    if (names.isEmpty) return const SizedBox.shrink();
    return Wrap(spacing: 8, runSpacing: 8, children: [
      for (final n in names)
        ActionChip(
          avatar: Icon((_labels[n.split('.').last] ?? ('', Icons.download_rounded)).$2, size: 18, color: C.accent),
          label: Text((_labels[n.split('.').last] ?? (n, Icons.download_rounded)).$1),
          onPressed: () => nbShareFile(context, app, files[n] as String, n),
        ),
    ]);
  }
}

// ---------------------------------------------------------------- Markdown-lite with [n] citations
typedef CiteTap = void Function(int n);

class NbMarkdown extends StatelessWidget {
  const NbMarkdown(this.text, {super.key, this.onCite, this.size = 14.5, this.color = C.ink});
  final String text;
  final CiteTap? onCite;
  final double size;
  final Color color;

  List<InlineSpan> _inline(String s, TextStyle base) {
    final out = <InlineSpan>[];
    final re = RegExp(r'\*\*(.+?)\*\*|\[(\d{1,3})\]|`([^`]+)`');
    var last = 0;
    for (final m in re.allMatches(s)) {
      if (m.start > last) out.add(TextSpan(text: s.substring(last, m.start), style: base));
      if (m.group(1) != null) {
        out.add(TextSpan(text: m.group(1), style: base.copyWith(fontWeight: FontWeight.w800, color: C.accentSoft)));
      } else if (m.group(2) != null) {
        final n = int.parse(m.group(2)!);
        out.add(WidgetSpan(
          alignment: PlaceholderAlignment.middle,
          child: GestureDetector(
            onTap: onCite == null ? null : () => onCite!(n),
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 2),
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
              decoration: BoxDecoration(color: C.violet.withOpacity(.35), borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: C.violet.withOpacity(.7))),
              child: Text('$n', style: TextStyle(fontSize: size - 3.5, fontWeight: FontWeight.w800, color: Colors.white)),
            ),
          ),
        ));
      } else if (m.group(3) != null) {
        out.add(TextSpan(text: m.group(3), style: base.copyWith(fontFamily: 'monospace', backgroundColor: C.panel)));
      }
      last = m.end;
    }
    if (last < s.length) out.add(TextSpan(text: s.substring(last), style: base));
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final base = TextStyle(fontSize: size, height: 1.45, color: color);
    final lines = text.replaceAll('\r', '').split('\n');
    final kids = <Widget>[];
    var i = 0;
    while (i < lines.length) {
      final ln = lines[i];
      final t = ln.trim();
      if (t.startsWith('|') && i + 1 < lines.length && RegExp(r'^\s*\|?\s*:?-{2,}').hasMatch(lines[i + 1])) {
        final head = t.replaceAll(RegExp(r'^\||\|$'), '').split('|').map((c) => c.trim()).toList();
        final rows = <List<String>>[];
        i += 2;
        while (i < lines.length && lines[i].trim().startsWith('|')) {
          rows.add(lines[i].trim().replaceAll(RegExp(r'^\||\|$'), '').split('|').map((c) => c.trim()).toList());
          i++;
        }
        kids.add(SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Table(
              defaultColumnWidth: const IntrinsicColumnWidth(),
              border: TableBorder.all(color: C.line, width: 1),
              children: [
                TableRow(decoration: const BoxDecoration(color: C.panel), children: [
                  for (final h in head) Padding(padding: const EdgeInsets.all(8), child: Text.rich(TextSpan(children: _inline(h, base.copyWith(fontWeight: FontWeight.w800, fontSize: size - 1))))),
                ]),
                for (final r in rows)
                  TableRow(children: [
                    for (var k = 0; k < head.length; k++)
                      Padding(padding: const EdgeInsets.all(8), child: Text.rich(TextSpan(children: _inline(k < r.length ? r[k] : '', base.copyWith(fontSize: size - 1))))),
                  ]),
              ],
            ),
          ),
        ));
        continue;
      }
      final h = RegExp(r'^(#{1,4})\s+(.*)').firstMatch(t);
      if (h != null) {
        final lv = h.group(1)!.length;
        kids.add(Padding(
          padding: EdgeInsets.only(top: lv == 1 ? 6 : 12, bottom: 4),
          child: Text.rich(TextSpan(children: _inline(h.group(2)!, base.copyWith(
              fontSize: size + (lv == 1 ? 7 : lv == 2 ? 4 : 2), fontWeight: FontWeight.w800,
              color: lv == 2 ? C.accentSoft : color)))),
        ));
      } else if (RegExp(r'^\s*[-*•]\s+').hasMatch(ln)) {
        final indent = RegExp(r'^\s*').firstMatch(ln)!.group(0)!.length;
        kids.add(Padding(
          padding: EdgeInsets.only(left: 6.0 + indent * 6, top: 2, bottom: 2),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Padding(padding: EdgeInsets.only(top: size * .55), child: Container(width: 6, height: 6, decoration: const BoxDecoration(color: C.accent, shape: BoxShape.circle))),
            const SizedBox(width: 10),
            Expanded(child: Text.rich(TextSpan(children: _inline(ln.replaceFirst(RegExp(r'^\s*[-*•]\s+'), ''), base)))),
          ]),
        ));
      } else if (RegExp(r'^\s*\d+[.)]\s+').hasMatch(ln)) {
        final m = RegExp(r'^\s*(\d+)[.)]\s+(.*)').firstMatch(ln)!;
        kids.add(Padding(
          padding: const EdgeInsets.only(left: 4, top: 2, bottom: 2),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 24, child: Text('${m.group(1)}.', style: base.copyWith(fontWeight: FontWeight.w800, color: C.accent))),
            Expanded(child: Text.rich(TextSpan(children: _inline(m.group(2)!, base)))),
          ]),
        ));
      } else if (t.startsWith('>')) {
        kids.add(Container(
          margin: const EdgeInsets.symmetric(vertical: 6),
          padding: const EdgeInsets.fromLTRB(12, 6, 8, 6),
          decoration: const BoxDecoration(border: Border(left: BorderSide(color: C.violet, width: 4))),
          child: Text.rich(TextSpan(children: _inline(t.replaceFirst(RegExp(r'^>\s*'), ''), base.copyWith(color: C.muted)))),
        ));
      } else if (RegExp(r'^(-{3,}|\*{3,})$').hasMatch(t)) {
        kids.add(const Divider(color: C.line, height: 18));
      } else if (t.isEmpty) {
        kids.add(const SizedBox(height: 6));
      } else {
        kids.add(Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text.rich(TextSpan(children: _inline(ln, base)))));
      }
      i++;
    }
    return SelectionArea(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: kids));
  }
}

String nbClock(Duration d) {
  final m = d.inMinutes;
  final s = d.inSeconds % 60;
  return '$m:${s.toString().padLeft(2, '0')}';
}

// ---------------------------------------------------------------- open the right viewer
Future<String?> openNbOutput(BuildContext context, Santosh app, String nid, Map<String, dynamic> o) async {
  final kind = o['kind'] as String? ?? '';
  if (o['status'] != 'ready') {
    nbSnack(context, o['status'] == 'failed' ? (o['error'] as String? ?? 'Nahi bana') : 'Abhi ban raha hai: ${o['stage'] ?? ''}');
    return null;
  }
  Map<String, dynamic> full;
  try {
    full = await app.api!.notebookOutput(nid, o['id'] as String);
  } catch (e) {
    if (context.mounted) nbSnack(context, '$e');
    return null;
  }
  if (!context.mounted) return null;
  final files = nbMap(full['files']);
  if (kind == 'video') {
    final url = files['overview.mp4'] as String?;
    if (url == null) return null;
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => NbVideoScreen(app: app, o: full)));
    return null;
  }
  final page = switch (kind) {
    'audio' => NbAudioScreen(app: app, nid: nid, o: full),
    'slides' => NbSlidesScreen(app: app, nid: nid, o: full),
    'infographic' => NbImageScreen(app: app, o: full, name: files.containsKey('infographic.jpg') ? 'infographic.jpg' : 'infographic.png'),
    'mind_map' => NbMindMapScreen(app: app, o: full),
    'flashcards' => NbFlashcardsScreen(app: app, o: full),
    'quiz' => NbQuizScreen(app: app, o: full),
    'table' => NbTableScreen(app: app, o: full),
    _ => NbReportScreen(app: app, nid: nid, o: full),
  };
  return Navigator.of(context).push<String>(MaterialPageRoute(builder: (_) => page));
}

PreferredSizeWidget nbBar(String title, {List<Widget>? actions}) =>
    AppBar(title: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis), backgroundColor: Colors.transparent, actions: actions);

// ---------------------------------------------------------------- audio overview + Join
class NbAudioScreen extends StatefulWidget {
  const NbAudioScreen({super.key, required this.app, required this.nid, required this.o});
  final Santosh app;
  final String nid;
  final Map<String, dynamic> o;
  @override
  State<NbAudioScreen> createState() => _NbAudioScreenState();
}

class _NbAudioScreenState extends State<NbAudioScreen> {
  VideoPlayerController? _c;
  VideoPlayerController? _clip;
  String? _err;
  double _speed = 1.0;
  bool _joining = false;
  bool _showScript = false;
  final SpeechToText _stt = SpeechToText();
  late List<Map<String, dynamic>> _joins;

  Map<String, dynamic> get data => nbMap(widget.o['data']);
  Map<String, dynamic> get files => nbMap(widget.o['files']);

  @override
  void initState() {
    super.initState();
    _joins = nbList(data['joins']);
    final name = data['audio'] as String? ?? files.keys.firstWhere((n) => n.startsWith('overview.'), orElse: () => '');
    final url = files[name] as String?;
    if (url == null) {
      _err = 'Audio file nahi mili';
      return;
    }
    final c = VideoPlayerController.networkUrl(Uri.parse(widget.app.api!.absolute(url)));
    _c = c;
    c.addListener(() {
      if (mounted) setState(() {});
    });
    c.initialize().then((_) {
      if (mounted) setState(() {});
      c.play();
    }).catchError((Object e) {
      if (mounted) setState(() => _err = '$e');
    });
  }

  @override
  void dispose() {
    _c?.dispose();
    _clip?.dispose();
    super.dispose();
  }

  Future<void> _join() async {
    final c = _c;
    final at = c?.value.position.inSeconds ?? 0;
    await c?.pause();
    if (!mounted) return;
    final q = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      builder: (_) => _JoinSheet(stt: _stt, lang: widget.app.language),
    );
    if (q == null || q.trim().isEmpty) {
      await c?.play();
      return;
    }
    setState(() => _joining = true);
    try {
      final r = await widget.app.api!.notebookJoin(widget.nid, widget.o['id'] as String, q.trim(), at: at);
      final clip = VideoPlayerController.networkUrl(Uri.parse(widget.app.api!.absolute(r['url'] as String)));
      _clip?.dispose();
      _clip = clip;
      await clip.initialize();
      _joins.add({'q': q.trim(), 'script': r['script'], 'url': r['url']});
      clip.addListener(() {
        final v = clip.value;
        if (v.isInitialized && !v.isPlaying && v.position >= v.duration - const Duration(milliseconds: 300) && _clip == clip) {
          _clip = null;
          clip.dispose();
          if (mounted) setState(() {});
          _c?.play();                       // back to the show
        }
      });
      await clip.play();
    } catch (e) {
      if (mounted) nbSnack(context, '$e');
      await c?.play();
    } finally {
      if (mounted) setState(() => _joining = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final v = c?.value;
    final ready = v?.isInitialized ?? false;
    final pos = v?.position ?? Duration.zero;
    final dur = v?.duration ?? Duration.zero;
    final opts = nbMap(widget.o['options']);
    return Scaffold(
      appBar: nbBar('Audio Overview'),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(18, 8, 18, 40), children: [
          Glass(
            padding: const EdgeInsets.all(20),
            child: Column(children: [
              Container(
                width: 150,
                height: 150,
                decoration: BoxDecoration(shape: BoxShape.circle, gradient: C.gradient,
                    boxShadow: [BoxShadow(color: C.accent2.withOpacity(.45), blurRadius: 40)]),
                child: Center(child: Icon(_clip != null ? Icons.record_voice_over_rounded : Icons.podcasts_rounded, size: 70, color: C.onAccent)),
              ),
              const SizedBox(height: 16),
              Text(widget.o['title'] as String? ?? '', textAlign: TextAlign.center,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
              const SizedBox(height: 4),
              Text('Ravi aur Priya · ${(opts['format'] ?? '').toString().replaceAll('_', ' ')} · ${opts['language'] ?? ''}',
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              if (_clip != null) ...[
                const SizedBox(height: 10),
                const Pill('AAPKE SAWAAL KA JAWAB', fg: C.teal),
              ],
              const SizedBox(height: 14),
              if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
              Slider(
                value: ready && dur.inMilliseconds > 0 ? pos.inMilliseconds.clamp(0, dur.inMilliseconds).toDouble() : 0,
                max: ready && dur.inMilliseconds > 0 ? dur.inMilliseconds.toDouble() : 1,
                activeColor: C.accent,
                onChanged: ready ? (x) => c!.seekTo(Duration(milliseconds: x.round())) : null,
              ),
              Row(children: [
                Text(nbClock(pos), style: const TextStyle(color: C.muted, fontSize: 12)),
                const Spacer(),
                Text(nbClock(dur), style: const TextStyle(color: C.muted, fontSize: 12)),
              ]),
              Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                IconButton(iconSize: 32, onPressed: ready ? () => c!.seekTo(pos - const Duration(seconds: 10)) : null,
                    icon: const Icon(Icons.replay_10_rounded)),
                const SizedBox(width: 10),
                Press(
                  onTap: ready ? () => (v!.isPlaying ? c!.pause() : c!.play()) : null,
                  child: Container(
                    width: 70, height: 70,
                    decoration: const BoxDecoration(color: C.accent, shape: BoxShape.circle),
                    child: Icon((v?.isPlaying ?? false) ? Icons.pause_rounded : Icons.play_arrow_rounded, size: 40, color: C.onAccent),
                  ),
                ),
                const SizedBox(width: 10),
                IconButton(iconSize: 32, onPressed: ready ? () => c!.seekTo(pos + const Duration(seconds: 10)) : null,
                    icon: const Icon(Icons.forward_10_rounded)),
              ]),
              const SizedBox(height: 6),
              Wrap(spacing: 6, children: [
                for (final sp in const [0.75, 1.0, 1.25, 1.5, 2.0])
                  ChoiceChip(label: Text('${sp}x'), selected: _speed == sp, onSelected: (_) {
                    setState(() => _speed = sp);
                    c?.setPlaybackSpeed(sp);
                  }),
              ]),
            ]),
          ),
          const SizedBox(height: 14),
          GradientButton(
            label: _joining ? 'Hosts soch rahe hain…' : 'Join karo: hosts se poochho',
            icon: Icons.front_hand_rounded,
            onTap: _joining || !ready ? null : _join,
          ),
          const SizedBox(height: 6),
          const Text('Podcast ke beech apna sawaal poochhiye: Ravi aur Priya sirf aapke sources se jawab dekar wapas show par aate hain.',
              textAlign: TextAlign.center, style: TextStyle(color: C.faint, fontSize: 12)),
          const SizedBox(height: 14),
          NbFileChips(app: widget.app, files: files),
          if (_joins.isNotEmpty) ...[
            const SizedBox(height: 16),
            const Caption('AAPKE SAWAAL'),
            for (final j in _joins)
              Glass(
                margin: const EdgeInsets.only(bottom: 8),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('❓ ${j['q']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  Text('${j['script'] ?? ''}', style: const TextStyle(color: C.chip, fontSize: 13, height: 1.4)),
                ]),
              ),
          ],
          const SizedBox(height: 10),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              InkWell(
                onTap: () => setState(() => _showScript = !_showScript),
                child: Row(children: [
                  const Icon(Icons.subject_rounded, color: C.muted),
                  const SizedBox(width: 8),
                  const Expanded(child: Text('Poori baatcheet (transcript)', style: TextStyle(fontWeight: FontWeight.w700))),
                  Icon(_showScript ? Icons.expand_less_rounded : Icons.expand_more_rounded),
                ]),
              ),
              if (_showScript) ...[
                const SizedBox(height: 10),
                for (final ln in '${data['script'] ?? ''}'.split('\n'))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Text.rich(TextSpan(children: [
                      TextSpan(text: ln.split(':').first, style: TextStyle(fontWeight: FontWeight.w800,
                          color: ln.startsWith('Ravi') ? C.teal : C.accentSoft)),
                      TextSpan(text: ln.contains(':') ? ln.substring(ln.indexOf(':')) : '', style: const TextStyle(color: C.ink, height: 1.4)),
                    ])),
                  ),
              ],
            ]),
          ),
        ]),
      ),
    );
  }
}

class _JoinSheet extends StatefulWidget {
  const _JoinSheet({required this.stt, required this.lang});
  final SpeechToText stt;
  final String lang;
  @override
  State<_JoinSheet> createState() => _JoinSheetState();
}

class _JoinSheetState extends State<_JoinSheet> {
  final _t = TextEditingController();
  bool _listening = false;

  Future<void> _mic() async {
    final ok = await widget.stt.initialize(onStatus: (s) {
      if ((s == 'done' || s == 'notListening') && mounted) setState(() => _listening = false);
    });
    if (!ok) {
      if (mounted) nbSnack(context, 'Microphone permission chahiye.');
      return;
    }
    setState(() => _listening = true);
    await widget.stt.listen(
      localeId: widget.lang.replaceAll('-', '_'),
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
      onResult: (r) => setState(() => _t.text = r.recognizedWords),
    );
  }

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.fromLTRB(18, 18, 18, 18 + MediaQuery.of(context).viewInsets.bottom),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Hosts se poochhiye', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: TextField(controller: _t, autofocus: true, minLines: 1, maxLines: 4,
                decoration: const InputDecoration(hintText: 'Jaise: iska matlab aasaan shabdon mein?'))),
            IconButton(onPressed: _listening ? null : _mic,
                icon: Icon(_listening ? Icons.graphic_eq_rounded : Icons.mic_rounded, color: C.accent)),
          ]),
          const SizedBox(height: 14),
          GradientButton(label: 'Poochho', icon: Icons.send_rounded, onTap: () => Navigator.pop(context, _t.text)),
        ]),
      );
}

// ---------------------------------------------------------------- video
class NbVideoScreen extends StatelessWidget {
  const NbVideoScreen({super.key, required this.app, required this.o});
  final Santosh app;
  final Map<String, dynamic> o;
  @override
  Widget build(BuildContext context) {
    final files = nbMap(o['files']);
    final data = nbMap(o['data']);
    final scenes = nbList(data['scenes']);
    return Scaffold(
      appBar: nbBar('Video Overview'),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
          Press(
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) =>
                VideoPlayScreen(url: app.api!.absolute(files['overview.mp4'] as String), title: o['title'] as String? ?? 'Video'))),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: AspectRatio(
                aspectRatio: 16 / 9,
                child: Stack(fit: StackFit.expand, children: [
                  if (files['cover.jpg'] != null)
                    Image.network(app.api!.absolute(files['cover.jpg'] as String), fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const ColoredBox(color: C.panel))
                  else
                    const ColoredBox(color: C.panel),
                  const ColoredBox(color: Color(0x55000000)),
                  const Center(child: Icon(Icons.play_circle_fill_rounded, size: 76, color: Colors.white)),
                ]),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(o['title'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
          Text('${nbClock(Duration(seconds: (o['seconds'] as num? ?? 0).toInt()))} · ${data['style'] ?? ''} · ${scenes.length} scenes',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            ActionChip(avatar: const Icon(Icons.download_rounded, size: 18, color: C.accent), label: const Text('Gallery mein save'),
                onPressed: () => nbShareFile(context, app, files['overview.mp4'] as String, 'overview.mp4', gallery: true)),
          ]),
          const SizedBox(height: 8),
          NbFileChips(app: app, files: files),
          const SizedBox(height: 16),
          const Caption('SCRIPT'),
          for (var i = 0; i < scenes.length; i++)
            Glass(
              margin: const EdgeInsets.only(bottom: 8),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (files['frame-${(i + 1).toString().padLeft(2, '0')}.jpg'] != null)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.network(app.api!.absolute(files['frame-${(i + 1).toString().padLeft(2, '0')}.jpg'] as String),
                        width: 110, height: 62, fit: BoxFit.cover, errorBuilder: (_, __, ___) => const SizedBox(width: 110, height: 62)),
                  ),
                const SizedBox(width: 10),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${scenes[i]['headline'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text('${scenes[i]['narration'] ?? ''}', style: const TextStyle(color: C.chip, fontSize: 12.5, height: 1.4)),
                ])),
              ]),
            ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- slide deck (+ revise)
class NbSlidesScreen extends StatefulWidget {
  const NbSlidesScreen({super.key, required this.app, required this.nid, required this.o});
  final Santosh app;
  final String nid;
  final Map<String, dynamic> o;
  @override
  State<NbSlidesScreen> createState() => _NbSlidesScreenState();
}

class _NbSlidesScreenState extends State<NbSlidesScreen> {
  late Map<String, dynamic> _o = widget.o;
  final _page = PageController();
  int _at = 0;
  final Map<int, String> _edits = {};
  bool _busy = false;
  int _bust = 0;

  List<Map<String, dynamic>> get slides => nbList(nbMap(_o['data'])['slides']);
  Map<String, dynamic> get files => nbMap(_o['files']);

  /// v0.155 painted slides are slide-NN.jpg, HTML-designed ones slide-NN.png.
  String? _slideUrl(int i) {
    final n = (i + 1).toString().padLeft(2, '0');
    return (files['slide-$n.jpg'] ?? files['slide-$n.png']) as String?;
  }

  Future<void> _edit(int n) async {
    final t = TextEditingController(text: _edits[n] ?? '');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: Text('Slide $n mein kya badlein?'),
        content: TextField(controller: t, autofocus: true, minLines: 2, maxLines: 5,
            decoration: const InputDecoration(hintText: 'Jaise: title chhota karo, ek number wali slide banao, Hindi mein likho')),
        actions: [
          if (_edits.containsKey(n)) TextButton(onPressed: () { _edits.remove(n); Navigator.pop(ctx, false); }, child: const Text('Hatao')),
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Line mein lagao')),
        ],
      ),
    );
    if (ok == true && t.text.trim().isNotEmpty) _edits[n] = t.text.trim();
    setState(() {});
  }

  Future<void> _apply() async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.notebookRevise(widget.nid, _o['id'] as String,
          [for (final e in _edits.entries) {'n': e.key, 'instruction': e.value}]);
      setState(() {
        _o = r;
        _edits.clear();
        _bust++;
      });
      if (mounted) nbSnack(context, 'Slides badal di. PDF / PowerPoint bhi naye hain.');
    } catch (e) {
      if (mounted) nbSnack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sl = slides;
    final cur = _at < sl.length ? sl[_at] : <String, dynamic>{};
    return Scaffold(
      appBar: nbBar(_o['title'] as String? ?? 'Slides'),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(14, 6, 14, 40), children: [
          AspectRatio(
            aspectRatio: 16 / 9,
            child: PageView.builder(
              controller: _page,
              itemCount: sl.length,
              onPageChanged: (i) => setState(() => _at = i),
              itemBuilder: (_, i) {
                final url = _slideUrl(i);
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(14),
                    child: url == null
                        ? const ColoredBox(color: C.panel)
                        : InteractiveViewer(child: Image.network('${widget.app.api!.absolute(url)}&v=$_bust', fit: BoxFit.contain,
                            errorBuilder: (_, __, ___) => const Center(child: Icon(Icons.broken_image_rounded)))),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 10),
          Row(children: [
            Text('Slide ${_at + 1} / ${sl.length}', style: const TextStyle(color: C.muted)),
            const Spacer(),
            if (_edits.containsKey(_at + 1)) const Pill('BADLAV LINE MEIN', fg: C.warn),
            const SizedBox(width: 6),
            GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: _busy ? null : () => _edit(_at + 1)),
          ]),
          if ((cur['notes'] as String? ?? '').isNotEmpty) ...[
            const SizedBox(height: 10),
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Speaker notes', style: TextStyle(fontWeight: FontWeight.w700, color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 4),
              Text(cur['notes'] as String, style: const TextStyle(height: 1.4)),
            ])),
          ],
          if (_edits.isNotEmpty) ...[
            const SizedBox(height: 12),
            GradientButton(label: _busy ? 'Badal raha hoon…' : 'Badlav lagao (${_edits.length})', icon: Icons.auto_fix_high_rounded,
                onTap: _busy ? null : _apply),
          ],
          const SizedBox(height: 14),
          NbFileChips(app: widget.app, files: files),
          const SizedBox(height: 14),
          SizedBox(
            height: 70,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              itemCount: sl.length,
              itemBuilder: (_, i) {
                final url = _slideUrl(i);
                return GestureDetector(
                  onTap: () => _page.animateToPage(i, duration: const Duration(milliseconds: 300), curve: Curves.easeOut),
                  child: Container(
                    width: 112,
                    margin: const EdgeInsets.only(right: 8),
                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: i == _at ? C.accent : C.line, width: 2)),
                    clipBehavior: Clip.antiAlias,
                    child: url == null ? const SizedBox() : Image.network('${widget.app.api!.absolute(url)}&v=$_bust', fit: BoxFit.cover),
                  ),
                );
              },
            ),
          ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- one picture (infographic / mind map image)
class NbImageScreen extends StatelessWidget {
  const NbImageScreen({super.key, required this.app, required this.o, required this.name});
  final Santosh app;
  final Map<String, dynamic> o;
  final String name;
  @override
  Widget build(BuildContext context) {
    final files = nbMap(o['files']);
    final url = files[name] as String?;
    return Scaffold(
      appBar: nbBar(o['title'] as String? ?? '', actions: [
        if (url != null) IconButton(tooltip: 'Gallery', icon: const Icon(Icons.download_rounded), onPressed: () => nbShareFile(context, app, url, name, gallery: true)),
        if (url != null) IconButton(tooltip: 'Bhejo', icon: const Icon(Icons.share_rounded), onPressed: () => nbShareFile(context, app, url, name)),
      ]),
      body: Aurora(
        child: Column(children: [
          Expanded(
            child: url == null
                ? const Center(child: Text('Tasveer nahi mili'))
                : InteractiveViewer(maxScale: 6, child: Center(child: Image.network(app.api!.absolute(url), fit: BoxFit.contain))),
          ),
          Padding(padding: const EdgeInsets.all(12), child: NbFileChips(app: app, files: files)),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- mind map (interactive)
class NbMindMapScreen extends StatefulWidget {
  const NbMindMapScreen({super.key, required this.app, required this.o});
  final Santosh app;
  final Map<String, dynamic> o;
  @override
  State<NbMindMapScreen> createState() => _NbMindMapScreenState();
}

class _NbMindMapScreenState extends State<NbMindMapScreen> {
  final Set<String> _open = {'0'};
  static const _colors = [Color(0xFF7C5CFF), Color(0xFF2DD4BF), Color(0xFFFFB15C), Color(0xFF34D399), Color(0xFFC055F5), Color(0xFFF87171), Color(0xFF38BDF8)];

  Widget _node(Map<String, dynamic> n, String path, int depth, Color color, List<String> trail) {
    final kids = nbList(n['children']);
    final open = _open.contains(path);
    final label = '${n['label'] ?? ''}';
    final here = [...trail, label];
    return Padding(
      padding: EdgeInsets.only(left: depth == 0 ? 0 : 18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(children: [
            if (depth > 0) Container(width: 14, height: 2, color: color.withOpacity(.7)),
            Flexible(
              child: Press(
                onTap: () => setState(() => open ? _open.remove(path) : _open.add(path)),
                child: Container(
                  padding: EdgeInsets.symmetric(horizontal: depth == 0 ? 16 : 12, vertical: depth == 0 ? 12 : 8),
                  decoration: BoxDecoration(
                    color: depth <= 1 ? color : color.withOpacity(.14),
                    borderRadius: BorderRadius.circular(depth == 0 ? 16 : 12),
                    border: Border.all(color: color.withOpacity(depth <= 1 ? 0 : .7), width: 1.5),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Flexible(child: Text(label, style: TextStyle(fontWeight: depth <= 1 ? FontWeight.w800 : FontWeight.w600,
                        fontSize: depth == 0 ? 17 : 14.5, color: depth <= 1 ? Colors.white : C.ink))),
                    if (kids.isNotEmpty) ...[
                      const SizedBox(width: 6),
                      Icon(open ? Icons.remove_circle_outline_rounded : Icons.add_circle_outline_rounded, size: 18,
                          color: depth <= 1 ? Colors.white : color),
                    ],
                  ]),
                ),
              ),
            ),
            IconButton(
              tooltip: 'Chat mein poochho',
              visualDensity: VisualDensity.compact,
              icon: const Icon(Icons.forum_rounded, size: 18, color: C.muted),
              onPressed: () => Navigator.pop(context,
                  'Notebook ke sources ke hisaab se samjhaiye: ${here.length > 1 ? here.sublist(1).join(' → ') : label}'),
            ),
          ]),
        ),
        if (open)
          for (var i = 0; i < kids.length; i++)
            _node(kids[i], '$path.$i', depth + 1, depth == 0 ? _colors[i % _colors.length] : color, here),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final root = nbMap(nbMap(widget.o['data'])['root']);
    final files = nbMap(widget.o['files']);
    return Scaffold(
      appBar: nbBar(widget.o['title'] as String? ?? 'Mind map', actions: [
        IconButton(tooltip: 'Sab kholo', icon: const Icon(Icons.unfold_more_rounded), onPressed: () {
          void walk(Map<String, dynamic> n, String p) {
            _open.add(p);
            final k = nbList(n['children']);
            for (var i = 0; i < k.length; i++) {
              walk(k[i], '$p.$i');
            }
          }
          setState(() => walk(root, '0'));
        }),
        if (files['mindmap.png'] != null)
          IconButton(tooltip: 'Tasveer', icon: const Icon(Icons.image_rounded), onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => NbImageScreen(app: widget.app, o: widget.o, name: 'mindmap.png')))),
      ]),
      body: Aurora(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 40),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: ConstrainedBox(
              constraints: BoxConstraints(minWidth: MediaQuery.of(context).size.width - 28, maxWidth: math.max(MediaQuery.of(context).size.width * 1.6, 560.0)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Branch par tap karke kholiye; 💬 se us baat par chat mein sawaal.', style: TextStyle(color: C.faint, fontSize: 12)),
                const SizedBox(height: 10),
                _node(root, '0', 0, const Color(0xFF3D2F7A), const []),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- report / deep research
class NbReportScreen extends StatelessWidget {
  const NbReportScreen({super.key, required this.app, required this.nid, required this.o});
  final Santosh app;
  final String nid;
  final Map<String, dynamic> o;
  @override
  Widget build(BuildContext context) {
    final data = nbMap(o['data']);
    final md = '${data['markdown'] ?? ''}';
    final srcs = nbList(data['sources']);
    return Scaffold(
      appBar: nbBar(o['title'] as String? ?? 'Report', actions: [
        IconButton(tooltip: 'Copy', icon: const Icon(Icons.copy_rounded), onPressed: () {
          Clipboard.setData(ClipboardData(text: md));
          nbSnack(context, 'Copy ho gaya');
        }),
      ]),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
          NbFileChips(app: app, files: nbMap(o['files'])),
          const SizedBox(height: 12),
          Glass(padding: const EdgeInsets.all(16), child: NbMarkdown(md)),
          if (srcs.isNotEmpty) ...[
            const SizedBox(height: 14),
            const Caption('WEB SOURCES'),
            for (final s in srcs)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.language_rounded, color: C.teal),
                title: Text('${s['title']}', maxLines: 2, overflow: TextOverflow.ellipsis),
                subtitle: Text('${s['url']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 11.5)),
                trailing: IconButton(
                  tooltip: 'Source jodo',
                  icon: const Icon(Icons.add_circle_outline_rounded, color: C.accent),
                  onPressed: () async {
                    try {
                      await app.api!.notebookAddSource(nid, {'url': s['url']});
                      if (context.mounted) nbSnack(context, 'Source jud gaya');
                    } catch (e) {
                      if (context.mounted) nbSnack(context, '$e');
                    }
                  },
                ),
                onTap: () => launchUrl(Uri.parse('${s['url']}'), mode: LaunchMode.externalApplication),
              ),
          ],
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- flashcards
class NbFlashcardsScreen extends StatefulWidget {
  const NbFlashcardsScreen({super.key, required this.app, required this.o});
  final Santosh app;
  final Map<String, dynamic> o;
  @override
  State<NbFlashcardsScreen> createState() => _NbFlashcardsScreenState();
}

class _NbFlashcardsScreenState extends State<NbFlashcardsScreen> {
  late List<Map<String, dynamic>> _cards = nbList(nbMap(widget.o['data'])['cards']);
  int _i = 0;
  bool _back = false;
  final Set<int> _known = {};
  final Set<int> _again = {};

  void _next(bool knew) {
    setState(() {
      (knew ? _known : _again).add(_i);
      (knew ? _again : _known).remove(_i);
      _back = false;
      if (_i < _cards.length - 1) _i++;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_cards.isEmpty) return Scaffold(appBar: nbBar('Flashcards'), body: const Center(child: Text('Koi card nahi')));
    final c = _cards[_i];
    final done = _known.length + _again.length;
    return Scaffold(
      appBar: nbBar(widget.o['title'] as String? ?? 'Flashcards', actions: [
        IconButton(tooltip: 'Shuffle', icon: const Icon(Icons.shuffle_rounded), onPressed: () => setState(() {
              _cards = [..._cards]..shuffle();
              _i = 0;
              _back = false;
              _known.clear();
              _again.clear();
            })),
      ]),
      body: Aurora(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 24),
          child: Column(children: [
            LinearProgressIndicator(value: done / _cards.length, color: C.ok, backgroundColor: C.panel, minHeight: 6,
                borderRadius: BorderRadius.circular(4)),
            const SizedBox(height: 8),
            Row(children: [
              Text('Card ${_i + 1} / ${_cards.length}', style: const TextStyle(color: C.muted)),
              const Spacer(),
              Text('✓ ${_known.length}   ↻ ${_again.length}', style: const TextStyle(color: C.muted)),
            ]),
            const SizedBox(height: 14),
            Expanded(
              child: GestureDetector(
                onTap: () => setState(() => _back = !_back),
                onHorizontalDragEnd: (d) {
                  final v = d.primaryVelocity ?? 0;
                  setState(() {
                    if (v < -200 && _i < _cards.length - 1) { _i++; _back = false; }
                    if (v > 200 && _i > 0) { _i--; _back = false; }
                  });
                },
                child: TweenAnimationBuilder<double>(
                  key: ValueKey('$_i'),
                  tween: Tween(begin: 0, end: _back ? 1 : 0),
                  duration: const Duration(milliseconds: 380),
                  curve: Curves.easeInOutCubic,
                  builder: (_, t, __) {
                    final showBack = t > .5;
                    return Transform(
                      alignment: Alignment.center,
                      transform: Matrix4.identity()..setEntry(3, 2, .0012)..rotateY(math.pi * t),
                      child: Transform(
                        alignment: Alignment.center,
                        transform: Matrix4.identity()..rotateY(showBack ? math.pi : 0),
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(28),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(28),
                            gradient: showBack ? C.youGradient : const LinearGradient(colors: [Color(0xFF231B4A), Color(0xFF1A1438)]),
                            border: Border.all(color: Colors.white.withOpacity(.16)),
                            boxShadow: const [BoxShadow(color: Color(0x66000000), blurRadius: 30, offset: Offset(0, 12))],
                          ),
                          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                            Pill(showBack ? 'JAWAB' : 'SAWAAL', fg: showBack ? Colors.white : C.accent),
                            const SizedBox(height: 18),
                            Text(showBack ? '${c['back']}' : '${c['front']}', textAlign: TextAlign.center,
                                style: TextStyle(fontSize: showBack ? 19 : 23, fontWeight: FontWeight.w700, height: 1.35)),
                            const SizedBox(height: 18),
                            Text(showBack ? (c['source'] != null ? 'Source ${c['source']}' : '') : 'Tap karke palto',
                                style: const TextStyle(color: C.muted, fontSize: 12)),
                          ]),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: GlassButton(label: 'Dobara dekhna', icon: Icons.refresh_rounded, onTap: () => _next(false))),
              const SizedBox(width: 10),
              Expanded(child: GradientButton(label: 'Pata tha', icon: Icons.check_rounded, height: 48, onTap: () => _next(true))),
            ]),
            const SizedBox(height: 10),
            NbFileChips(app: widget.app, files: nbMap(widget.o['files'])),
          ]),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- quiz
class NbQuizScreen extends StatefulWidget {
  const NbQuizScreen({super.key, required this.app, required this.o});
  final Santosh app;
  final Map<String, dynamic> o;
  @override
  State<NbQuizScreen> createState() => _NbQuizScreenState();
}

class _NbQuizScreenState extends State<NbQuizScreen> {
  late final List<Map<String, dynamic>> _qs = nbList(nbMap(widget.o['data'])['questions']);
  int _i = 0;
  int? _picked;
  bool _hint = false;
  int _score = 0;
  bool _done = false;

  void _pick(int k) {
    if (_picked != null) return;
    setState(() {
      _picked = k;
      if (k == (_qs[_i]['answer'] as num).toInt()) _score++;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_qs.isEmpty) return Scaffold(appBar: nbBar('Quiz'), body: const Center(child: Text('Koi sawaal nahi')));
    if (_done) {
      final pct = (_score * 100 / _qs.length).round();
      return Scaffold(
        appBar: nbBar(widget.o['title'] as String? ?? 'Quiz'),
        body: Aurora(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text(pct >= 80 ? '🏆' : pct >= 50 ? '👏' : '📚', style: const TextStyle(fontSize: 64)),
                const SizedBox(height: 10),
                Text('$_score / ${_qs.length}', style: const TextStyle(fontSize: 40, fontWeight: FontWeight.w800)),
                Text(pct >= 80 ? 'Shaandaar!' : pct >= 50 ? 'Achha hai, thoda aur!' : 'Ek baar aur padhiye, phir try kijiye',
                    style: const TextStyle(color: C.muted)),
                const SizedBox(height: 22),
                GradientButton(label: 'Phir se karo', icon: Icons.replay_rounded, onTap: () => setState(() {
                      _i = 0;
                      _picked = null;
                      _score = 0;
                      _done = false;
                      _hint = false;
                    })),
              ]),
            ),
          ),
        ),
      );
    }
    final q = _qs[_i];
    final opts = List<String>.from((q['options'] as List? ?? const []).map((e) => '$e'));
    final ans = (q['answer'] as num? ?? 0).toInt();
    return Scaffold(
      appBar: nbBar(widget.o['title'] as String? ?? 'Quiz'),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(18, 8, 18, 40), children: [
          LinearProgressIndicator(value: (_i + 1) / _qs.length, color: C.accent, backgroundColor: C.panel, minHeight: 6,
              borderRadius: BorderRadius.circular(4)),
          const SizedBox(height: 10),
          Text('Sawaal ${_i + 1} / ${_qs.length}  ·  Score $_score', style: const TextStyle(color: C.muted)),
          const SizedBox(height: 14),
          Text('${q['q']}', style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800, height: 1.35)),
          const SizedBox(height: 16),
          for (var k = 0; k < opts.length; k++)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Press(
                onTap: () => _pick(k),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 220),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16),
                    color: _picked == null ? C.panel : k == ans ? C.ok.withOpacity(.22) : k == _picked ? C.bad.withOpacity(.22) : C.panel,
                    border: Border.all(color: _picked == null ? C.line : k == ans ? C.ok : k == _picked ? C.bad : C.line, width: 1.5),
                  ),
                  child: Row(children: [
                    CircleAvatar(radius: 14, backgroundColor: C.violet.withOpacity(.35),
                        child: Text(String.fromCharCode(65 + k), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Colors.white))),
                    const SizedBox(width: 12),
                    Expanded(child: Text(opts[k], style: const TextStyle(fontSize: 15.5, height: 1.3))),
                    if (_picked != null && k == ans) const Icon(Icons.check_circle_rounded, color: C.ok),
                    if (_picked == k && k != ans) const Icon(Icons.cancel_rounded, color: C.bad),
                  ]),
                ),
              ),
            ),
          if (_picked == null && (q['hint'] as String? ?? '').isNotEmpty)
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(onPressed: () => setState(() => _hint = true), icon: const Icon(Icons.lightbulb_outline_rounded),
                  label: Text(_hint ? '${q['hint']}' : 'Hint')),
            ),
          if (_picked != null) ...[
            const SizedBox(height: 6),
            Glass(child: Text('${_picked == ans ? '✅ Sahi!' : '❌ Sahi jawab: ${String.fromCharCode(65 + ans)}'}\n${q['why'] ?? ''}',
                style: const TextStyle(height: 1.4))),
            const SizedBox(height: 14),
            GradientButton(
              label: _i < _qs.length - 1 ? 'Agla sawaal' : 'Nateeja dekho',
              icon: Icons.arrow_forward_rounded,
              onTap: () => setState(() {
                if (_i < _qs.length - 1) {
                  _i++;
                  _picked = null;
                  _hint = false;
                } else {
                  _done = true;
                }
              }),
            ),
          ],
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- data table
class NbTableScreen extends StatelessWidget {
  const NbTableScreen({super.key, required this.app, required this.o});
  final Santosh app;
  final Map<String, dynamic> o;
  @override
  Widget build(BuildContext context) {
    final d = nbMap(o['data']);
    final cols = List<String>.from((d['columns'] as List? ?? const []).map((e) => '$e'));
    final rows = (d['rows'] as List? ?? const []).map((r) => List<String>.from((r as List).map((e) => '$e'))).toList();
    return Scaffold(
      appBar: nbBar(o['title'] as String? ?? 'Data table'),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(12, 8, 12, 40), children: [
          NbFileChips(app: app, files: nbMap(o['files'])),
          const SizedBox(height: 12),
          Glass(
            padding: EdgeInsets.zero,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                headingRowColor: WidgetStateProperty.all(C.panel),
                columnSpacing: 22,
                dataRowMaxHeight: 96,
                columns: [for (final c in cols) DataColumn(label: Text(c, style: const TextStyle(fontWeight: FontWeight.w800)))],
                rows: [
                  for (final r in rows)
                    DataRow(cells: [
                      for (var k = 0; k < cols.length; k++)
                        DataCell(ConstrainedBox(constraints: const BoxConstraints(maxWidth: 260),
                            child: Text(k < r.length ? r[k] : '', style: const TextStyle(fontSize: 13)))),
                    ]),
                ],
              ),
            ),
          ),
          if ((d['notes'] as String? ?? '').isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 10), child: Text('${d['notes']}', style: const TextStyle(color: C.muted, fontSize: 12.5))),
        ]),
      ),
    );
  }
}
