// v0.999.90 HOOLA VOCAL, GLOBAL, ON THE PHONE (owner, on the design canvas claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue:
// "GO BUILD ALL"; the contract is docs/HOOLA_VOCAL_GLOBAL.md): the shared parts of the phone's Vocal screens - one store
// over /api/vocal/overview (voices, every language with its own-script name, styles, engines, her sounds), her Voice
// settings and the note they ride her message as ("[Vocal settings: ...]", like the Music chat's note), and one player
// for the page (one sound at a time). The Create kit (lib/ui/create/create_kit.dart) gives the blocks and the colours.
import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:video_player/video_player.dart';

import '../../state.dart';
import '../create/create_kit.dart';
import '../hoola_theme.dart';

export '../create/create_kit.dart';

// ------------------------------------------------------------------------------------------------ the store
/// Everything the Vocal screens read: GET /api/vocal/overview, kept for the visit.
class VocalStore extends ChangeNotifier {
  VocalStore(this.app);
  final Santosh app;

  /// Test seam: the Vocal data without a server ({overview, chat, quote, consent, design, dubs, chats}).
  static Map<String, dynamic>? debugData;
  static bool get debug => debugData != null;

  /// The languages she picked lately, newest first (this visit and the next ones on this phone run).
  static final List<String> recent = [];

  Map<String, dynamic> ov = const {};
  String error = '';
  bool loading = false;
  bool _gone = false;

  List<Map<String, dynamic>> get voices => crList(ov['voices']);
  List<Map<String, dynamic>> get langs => crList(ov['langs']);
  List<Map<String, dynamic>> get history => crList(ov['history']);
  List<Map<String, dynamic>> get engines => crList(ov['engines']);
  Map<String, dynamic> get connected => crMap(crMap(ov['status'])['connected']);

  /// Style id -> its name ("warm" -> "Warm"); the six the design shows when the server names none.
  Map<String, String> get styles {
    final s = crMap(ov['styles']);
    if (s.isEmpty) return kVocalStyles;
    return {for (final e in s.entries) e.key: crS(e.value)};
  }

  Future<void> load() async {
    final d = debugData;
    if (d != null) {
      ov = crMap(d['overview']);
      _tell();
      return;
    }
    final api = app.api;
    if (api == null) {
      error = 'Not connected to the server right now';
      _tell();
      return;
    }
    loading = true;
    _tell();
    try {
      ov = await api.vocalOverview();
      error = '';
    } catch (e) {
      error = 'Hoola Vocal did not open. ${crError(e)}';
    }
    loading = false;
    _tell();
  }

  Map<String, dynamic>? lang(String code) {
    for (final l in langs) {
      if (crS(l['code']) == code) return l;
    }
    return null;
  }

  Map<String, dynamic>? voice(String id) {
    for (final v in voices) {
      if (crS(v['id']) == id) return v;
    }
    return null;
  }

  /// A language as she reads it: its own-script name ("Kiswahili"), else its English name, else the code.
  String langNative(String code) {
    if (code.isEmpty || code == 'auto') return 'Auto';
    final l = lang(code);
    if (l == null) return code;
    return crS(l['native']).isNotEmpty ? crS(l['native']) : (crS(l['name']).isNotEmpty ? crS(l['name']) : code);
  }

  String langName(String code) {
    if (code.isEmpty || code == 'auto') return 'Auto';
    final l = lang(code);
    return l == null || crS(l['name']).isEmpty ? code : crS(l['name']);
  }

  /// The voices that speak a language (her own voices speak them all), ready ones first.
  List<Map<String, dynamic>> voicesFor(String code) {
    final out = voices.where((v) {
      if (crS(v['kind']) != 'hoola' && crS(v['kind']).isNotEmpty) return true;
      if (code.isEmpty || code == 'auto') return true;
      final ls = (v['langs'] is List) ? (v['langs'] as List).map(crS).toList() : const <String>[];
      return ls.isEmpty || ls.contains(code) || ls.contains('*');
    }).toList();
    out.sort((a, b) => (b['ready'] == false ? 0 : 1).compareTo(a['ready'] == false ? 0 : 1));
    return out;
  }

  List<Map<String, dynamic>> get mine => voices.where((v) => crS(v['kind']).isNotEmpty && crS(v['kind']) != 'hoola').toList();

  /// Can this server make her own voice (copy a recording / design one from words)? An engine that is not set up says why.
  bool get canClone => connected['clone'] != false;
  bool get canDesign => (connected['design'] ?? connected['clone']) != false;
  String whyNot(String job) {
    for (final e in engines) {
      if (crS(e['state']) == 'ready') continue;
      final does = crS(e['does']).toLowerCase();
      if (does.contains(job)) {
        return '${crS(e['name'])} is not set up on this server yet (${crS(e['state']) == 'needs_key' ? 'it needs its key' : 'it is off'}).';
      }
    }
    return 'Making your own voice is not set up on this server yet.';
  }

  void tell() => _tell();
  void _tell() {
    if (!_gone) notifyListeners();
  }

  @override
  void dispose() {
    _gone = true;
    super.dispose();
  }
}

/// The styles the design shows when the server sends none.
const Map<String, String> kVocalStyles = {
  'warm': 'Warm', 'calm': 'Calm', 'cheerful': 'Cheerful', 'news': 'News', 'story': 'Story', 'ad': 'Ad',
};

// ------------------------------------------------------------------------------------------------ her Voice settings
class VocalSettings {
  VocalSettings({this.lang = 'auto', this.voice = '', this.style = 'warm', this.speed = 1.0, this.takes = 2, this.engine = 'auto'});
  String lang;     // a language code, or 'auto' = the language of her words
  String voice;    // a voice id, or '' = Hoola picks
  String style;    // a style id
  double speed;    // 0.7 - 1.3
  int takes;       // 1 - 3
  String engine;   // auto | gemini | eleven

  /// The phone's language when a ready engine speaks it, else Auto (the contract's global rule).
  static VocalSettings forPhone(VocalStore s) {
    final code = ui.PlatformDispatcher.instance.locale.languageCode;
    final l = s.lang(code);
    return VocalSettings(lang: l != null && crS(l['speech']) != 'none' ? code : 'auto');
  }

  String voiceName(VocalStore s) {
    if (voice.isEmpty) return 'Hoola picks';
    final v = s.voice(voice);
    return v == null ? voice : crS(v['name']);
  }

  String styleName(VocalStore s) => s.styles[style] ?? (style.isEmpty ? 'Natural' : style);

  /// The line on the settings pill: "Kiswahili · Amani · Warm · 0.9x".
  String summary(VocalStore s) => '${s.langNative(lang)} · ${voiceName(s)} · ${styleName(s)} · ${vocalSpeed(speed)}x';

  static String _clean(String t) => t.replaceAll(RegExp(r'[\[\];\n]+'), ' ').trim();

  /// The note her message carries (the console sends the same): the Vocal chat's rules read it.
  String note(VocalStore s, {String focus = ''}) {
    final language = lang == 'auto' || lang.isEmpty ? 'auto' : '${_clean(s.langName(lang))} ($lang)';
    final v = voice.isEmpty ? 'auto' : '${_clean(voiceName(s))} ($voice)';
    return 'Vocal settings: language $language; voice $v; style ${_clean(style.isEmpty ? 'auto' : style)}; speed ${vocalSpeed(speed)}; '
        'takes ${takes.clamp(1, 3)}; engine $engine${focus.isEmpty ? '' : '; the take she means: id ${_clean(focus)}'}';
  }

  /// The body of speech made straight away (no chat turn): POST /api/vocal/tts.
  Map<String, dynamic> body(String text, {String chat = ''}) => {
        'text': text.length > 100000 ? text.substring(0, 100000) : text,
        'voice': voice,
        'lang': lang.isEmpty ? 'auto' : lang,
        'style': style,
        'speed': speed,
        'takes': takes.clamp(1, 3),
        'engine': engine,
        'format': 'mp3',
        'rules': true,
        if (chat.isNotEmpty) 'chat': chat,
      };

  Map<String, dynamic> quote(String text) => {
        'job': 'tts',
        'chars': math.max(1, text.trim().isEmpty ? 200 : text.trim().length),
        'takes': takes.clamp(1, 3),
        'voice': voice,
        'lang': lang.isEmpty ? 'auto' : lang,
        'engine': engine,
      };
}

/// 0.9 -> "0.9", 1.0 -> "1.0", 0.85 -> "0.85".
String vocalSpeed(double v) {
  final s = v.toStringAsFixed(2);
  return s.endsWith('0') ? v.toStringAsFixed(1) : s;
}

/// Her words without the settings note that rode after them ("[Vocal settings: ...]").
String vocalStripNotes(String t) => t.replaceFirst(RegExp(r'(?:\s*\[(?:Vocal settings|Web console)[^\]\n]*\])+\s*$'), '').trimRight();

/// The price line under a button: the server's own sentence, else "Gemini voice · 2 takes ≈ 4 credits".
String vocalQuoteLine(Map<String, dynamic> q, int takes) {
  if (crS(q['line']).isNotEmpty) return crS(q['line']);
  if (q.isEmpty) return '';
  final who = crS(q['engine_name']).isEmpty ? 'Hoola' : crS(q['engine_name']);
  return '$who · $takes take${takes > 1 ? 's' : ''} ≈ ${crInt(q['credits'])} credit${crInt(q['credits']) == 1 ? '' : 's'}';
}

// ------------------------------------------------------------------------------------------------ rows and takes
/// A row's time in epoch seconds (`made` may be seconds or an ISO time).
int vocalEpoch(Object? v) {
  if (v is num) return v.round();
  final s = crS(v);
  if (s.isEmpty) return 0;
  final n = int.tryParse(s);
  if (n != null) return n;
  final t = DateTime.tryParse(s.endsWith('Z') || RegExp(r'[+-]\d\d:\d\d$').hasMatch(s) ? s : '${s}Z');
  return t == null ? 0 : t.millisecondsSinceEpoch ~/ 1000;
}

String vocalClock(num secs) {
  final s = secs.round();
  return '${s ~/ 60}:${(s % 60).toString().padLeft(2, '0')}';
}

/// A row that could not be made (the server says so with `status` or `error`).
bool vocalFailed(Map<String, dynamic> r) => crS(r['status']) == 'failed' || crS(r['error']).isNotEmpty;

/// What a kind of sound is called.
String vocalKindName(String kind) => switch (kind) {
      'tts' || 'chapter' || 'book' => 'Speech',
      'dialogue' => 'Dialogue',
      'dub' => 'Dub',
      'sfx' => 'Effect',
      'cleanup' => 'Clean-up',
      'change' => 'Voice change',
      'music' => 'Music',
      _ => 'Sound',
    };

/// The Your sounds filter a kind belongs to.
String vocalFilterOf(String kind) => switch (kind) {
      'tts' || 'chapter' || 'book' => 'Speech',
      'dialogue' => 'Dialogue',
      'dub' => 'Dubs',
      'sfx' => 'Effects',
      _ => 'Other',
    };

/// One ask in the chat = one job, holding its takes (A, B, C).
class VocalSet {
  VocalSet(this.job, this.created);
  final String job;
  int created;
  final List<Map<String, dynamic>> takes = [];
}

/// The takes made in a Vocal chat, grouped by `job`, oldest set first, each set's takes in order.
List<VocalSet> vocalSets(List<Map<String, dynamic>> items) {
  final sets = <String, VocalSet>{};
  for (final it in items) {
    final k = crS(it['job']).isEmpty ? crS(it['id']) : crS(it['job']);
    final s = sets.putIfAbsent(k, () => VocalSet(k, vocalEpoch(it['made'])));
    s.takes.add(it);
    s.created = math.min(s.created, vocalEpoch(it['made']));
  }
  for (final s in sets.values) {
    s.takes.sort((a, b) {
      final t = vocalTakeOrder(a).compareTo(vocalTakeOrder(b));
      return t != 0 ? t : vocalEpoch(a['made']).compareTo(vocalEpoch(b['made']));
    });
  }
  return sets.values.toList()..sort((a, b) => a.created.compareTo(b.created));
}

int vocalTakeOrder(Map<String, dynamic> r) {
  final t = r['take'];
  if (t is num) return t.round();
  final s = crS(t).trim();
  if (s.isEmpty) return 99;
  return int.tryParse(s) ?? (s.codeUnitAt(0) - 64);
}

/// "A", "B" ... from the row's `take` (a letter or a number), else its place in the set.
String vocalTakeLetter(Map<String, dynamic> r, int index) {
  final t = r['take'];
  if (t is num && t >= 1 && t <= 26) return String.fromCharCode(64 + t.round());
  final s = crS(t).trim();
  if (s.isNotEmpty) {
    final n = int.tryParse(s);
    if (n != null && n >= 1 && n <= 26) return String.fromCharCode(64 + n);
    return s.toUpperCase();
  }
  return String.fromCharCode(65 + index);
}

/// The colour a voice is drawn in (the server's own colour), else the voice hue.
Color vocalColor(Map<String, dynamic>? v) {
  final h = crS(v?['color']).replaceAll('#', '');
  if (h.length == 6) {
    final n = int.tryParse(h, radix: 16);
    if (n != null) return Color(n | 0xFF000000);
  }
  return CrHue.voice.a;
}

// ------------------------------------------------------------------------------------------------ one player
/// Plays one sound at a time on a page: the bytes come with her key (a voice preview, a take), go to a temporary file
/// and play from there. A second play stops the first.
class VocalPlayer extends ChangeNotifier {
  VocalPlayer(this.app);
  final Santosh app;
  VideoPlayerController? _ctl;
  String id = '';
  bool loading = false;
  bool _gone = false;

  bool playing(String key) => id == key && (_ctl?.value.isPlaying ?? false);
  bool busy(String key) => id == key && loading;
  Duration get position => _ctl?.value.position ?? Duration.zero;

  Future<void> toggle(BuildContext context, String key, Future<List<int>?> Function() fetch, {String ext = 'mp3'}) async {
    if (VocalStore.debug || app.api == null) return;
    if (id == key && _ctl != null) {
      final c = _ctl!;
      if (c.value.isPlaying) {
        await c.pause();
      } else {
        if (c.value.position >= c.value.duration && c.value.duration > Duration.zero) await c.seekTo(Duration.zero);
        await c.play();
      }
      _tell();
      return;
    }
    await _ctl?.dispose();
    _ctl = null;
    id = key;
    loading = true;
    _tell();
    VideoPlayerController? c;
    try {
      final dir = await getTemporaryDirectory();
      final safe = key.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
      final f = File('${dir.path}/vocal_$safe.${ext.isEmpty ? 'mp3' : ext}');
      if (!await f.exists() || await f.length() == 0) {
        final bytes = await fetch();
        if (bytes == null || bytes.isEmpty) throw Exception('This sound is no longer on Hoola.');
        await f.writeAsBytes(bytes, flush: true);
      }
      c = VideoPlayerController.file(f);
      await c.initialize();
    } catch (e) {
      await c?.dispose();
      loading = false;
      id = '';
      _tell();
      if (context.mounted) crToast(context, 'This sound did not open: ${crError(e)}');
      return;
    }
    if (_gone || id != key) {
      await c.dispose();
      return;
    }
    c.addListener(_tell);
    _ctl = c;
    loading = false;
    await c.play();
    _tell();
  }

  Future<void> stop() async {
    await _ctl?.pause();
    _tell();
  }

  void _tell() {
    if (!_gone) notifyListeners();
  }

  @override
  void dispose() {
    _gone = true;
    _ctl?.dispose();
    super.dispose();
  }
}

/// A round play / pause button for one sound (48 dp of tap room).
class VocalPlayButton extends StatelessWidget {
  const VocalPlayButton({super.key, required this.label, required this.playing, required this.onTap, this.loading = false, this.size = 40});
  final String label;
  final bool playing, loading;
  final VoidCallback onTap;
  final double size;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: label,
      excludeSemantics: true,
      child: crTap48(onTap, Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle),
        child: Center(
          child: loading
              ? SizedBox(width: size * .4, height: size * .4, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
              : playing
                  ? Row(mainAxisSize: MainAxisSize.min, children: [
                      Container(width: size * .1, height: size * .36, decoration: BoxDecoration(color: c.onPill, borderRadius: BorderRadius.circular(2))),
                      SizedBox(width: size * .1),
                      Container(width: size * .1, height: size * .36, decoration: BoxDecoration(color: c.onPill, borderRadius: BorderRadius.circular(2))),
                    ])
                  : CrIcon(CrGlyph.play, size: size * .36, color: c.onPill),
        ),
      )),
    );
  }
}

/// A voice's round mark: its own colour and its first letter.
class VocalVoiceDot extends StatelessWidget {
  const VocalVoiceDot({super.key, required this.voice, this.size = 36, this.name = ''});
  final Map<String, dynamic>? voice;
  final double size;
  final String name;
  @override
  Widget build(BuildContext context) {
    final n = name.isNotEmpty ? name : crS(voice?['name']);
    return ExcludeSemantics(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: vocalColor(voice), shape: BoxShape.circle),
        child: Center(
          child: Text(n.isEmpty ? '·' : n.characters.first.toUpperCase(),
              style: HoolaType.body(HoolaColors.of(context)).copyWith(fontSize: size >= 40 ? 16 : 13, fontWeight: FontWeight.w600,
                  color: CreateHues.onHue)),
        ),
      ),
    );
  }
}

/// The search box every Vocal list starts with.
class VocalSearch extends StatelessWidget {
  const VocalSearch({super.key, required this.controller, required this.hint, required this.onChanged});
  final TextEditingController controller;
  final String hint;
  final ValueChanged<String> onChanged;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return TextField(
      controller: controller,
      onChanged: onChanged,
      style: HoolaType.body(c),
      decoration: InputDecoration(
        hintText: hint,
        prefixIcon: Padding(padding: const EdgeInsets.all(14), child: CrIcon(CrGlyph.search, size: 16, color: c.ink3)),
        filled: true,
        fillColor: c.sunk,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: c.lineStrong)),
      ),
    );
  }
}

/// The top bar of a Vocal page: back, its name, and up to two round buttons.
class VocalTop extends StatelessWidget {
  const VocalTop({super.key, required this.title, this.sub = '', this.actions = const []});
  final String title, sub;
  final List<Widget> actions;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return SizedBox(
      height: 60,
      child: Row(children: [
        const SizedBox(width: 4),
        CrRoundButton(glyph: CrGlyph.back, label: 'Back', onTap: () => Navigator.of(context).maybePop()),
        Expanded(
          child: Semantics(
            header: true,
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center, style: HoolaType.title(c)),
              if (sub.isNotEmpty) Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
            ]),
          ),
        ),
        if (actions.isEmpty) const SizedBox(width: 48) else ...actions,
        const SizedBox(width: 4),
      ]),
    );
  }
}

Future<bool?> vocalConfirm(BuildContext context, String title, String body, String yes) => showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Keep')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(yes)),
        ],
      ),
    );

/// A sound into a temporary file and the phone's share sheet (save to files, WhatsApp...).
Future<void> vocalShare(BuildContext context, Santosh app, Map<String, dynamic> r) async {
  final api = app.api;
  if (api == null || VocalStore.debug) return;
  crToast(context, 'Getting the file…');
  try {
    final ext = crS(r['ext']).isEmpty ? 'mp3' : crS(r['ext']);
    final bytes = await api.vocalAudio(crS(r['id']), format: ext == 'wav' || ext == 'flac' ? ext : 'mp3');
    if (bytes == null) throw Exception('This sound is no longer on Hoola.');
    if (!context.mounted) return;
    final out = ext == 'wav' || ext == 'flac' ? ext : 'mp3';
    await crShareBytes(context, bytes, '${crS(r['title']).isEmpty ? 'Hoola sound' : crS(r['title'])}.$out',
        out == 'mp3' ? 'audio/mpeg' : (out == 'wav' ? 'audio/wav' : 'audio/flac'));
  } catch (e) {
    if (context.mounted) crToast(context, crError(e));
  }
}
