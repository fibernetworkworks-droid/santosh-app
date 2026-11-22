// v0.999.90 HOOLA VOCAL, GLOBAL, ON THE PHONE (owner, on the design canvas claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue:
// "GO BUILD ALL"; the contract is docs/HOOLA_VOCAL_GLOBAL.md): the shared parts of the phone's Vocal screens - one store
// over /api/vocal/overview (voices, every language with its own-script name, styles, engines, her sounds), her Voice
// settings and the note they ride her message as ("[Vocal settings: ...]", like the Music chat's note), and one player
// for the page (one sound at a time). The Create kit (lib/ui/create/create_kit.dart) gives the blocks and the colours.
import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:video_player/video_player.dart';

import '../../api.dart' show ApiException;
import '../../state.dart';
import '../../voice_recorder.dart';
import '../create/create_kit.dart';
import '../hoola_mark.dart';
import '../hoola_theme.dart';
import '../shell/hoola_credits.dart' show HoolaCreditsPage;

export '../create/create_kit.dart';

// ------------------------------------------------------------------------------------------------ the store
/// Everything the Vocal screens read: GET /api/vocal/overview, kept for the visit.
class VocalStore extends ChangeNotifier {
  VocalStore(this.app);
  final Santosh app;

  /// Test seam: the Vocal data without a server ({overview, chat, quote, consent, design, dubs, chats}).
  static Map<String, dynamic>? debugData;
  static bool get debug => debugData != null;

  /// Test seam: what the newer Vocal parts would have sent, in order (the route's name and its body).
  static final List<(String, Map<String, dynamic>)> debugCalls = [];

  /// Test seam: records a call and answers it from [debugData] under [key] (an empty map when the test gave none).
  static Map<String, dynamic> debugAnswer(String key, [Map<String, dynamic> body = const {}]) {
    debugCalls.add((key, body));
    return crMap(debugData?[key]);
  }

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
  int takes;       // 1, 2 or 4
  String engine;   // auto | gemini | eleven

  /// The phone's language when a ready engine speaks it, else Auto (the contract's global rule).
  static VocalSettings forPhone(VocalStore s) {
    final code = ui.PlatformDispatcher.instance.locale.languageCode;
    final l = s.lang(code);
    return VocalSettings(lang: l != null && crS(l['speech']) != 'none' ? code : 'auto');
  }

  /// Her saved defaults from the server (Settings page), when she saved any.
  void applySaved(VocalStore s) {
    final d = crMap(s.ov['settings']);
    if (crS(d['lang']).isNotEmpty) lang = crS(d['lang']);
    if (crS(d['voice']).isNotEmpty) voice = crS(d['voice']);
    if (crS(d['style']).isNotEmpty) style = crS(d['style']);
    if (crS(d['engine']).isNotEmpty) engine = crS(d['engine']);
    final t = crInt(d['takes']);
    if (t >= 1 && t <= kVocalMaxTakes) takes = t;
  }

  /// Saves these defaults on the server so the next visit (phone or console) starts with them.
  Future<void> save(VocalStore s) async {
    final api = s.app.api;
    if (VocalStore.debug || api == null) return;
    final saved = await api.vocalSettingsSave({'lang': lang, 'voice': voice, 'style': style, 'engine': engine, 'takes': takes});
    s.ov = {...s.ov, 'settings': saved};
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
        'takes ${takes.clamp(1, kVocalMaxTakes)}; engine $engine${focus.isEmpty ? '' : '; the take she means: id ${_clean(focus)}'}';
  }

  /// The body of speech made straight away (no chat turn): POST /api/vocal/tts.
  Map<String, dynamic> body(String text, {String chat = ''}) => {
        'text': text.length > 100000 ? text.substring(0, 100000) : text,
        'voice': voice,
        'lang': lang.isEmpty ? 'auto' : lang,
        'style': style,
        'speed': speed,
        'takes': takes.clamp(1, kVocalMaxTakes),
        'engine': engine,
        'format': 'mp3',
        'rules': true,
        if (chat.isNotEmpty) 'chat': chat,
      };

  Map<String, dynamic> quote(String text) => {
        'job': 'tts',
        'chars': math.max(1, text.trim().isEmpty ? 200 : text.trim().length),
        'takes': takes.clamp(1, kVocalMaxTakes),
        'voice': voice,
        'lang': lang.isEmpty ? 'auto' : lang,
        'engine': engine,
      };
}

/// The most takes one ask makes (the server's own limit, overview `limits.takes`).
const int kVocalMaxTakes = 4;

/// The takes she can choose: 1, 2 and 4 (fewer when the server's limit is lower).
List<String> vocalTakeChoices([VocalStore? s]) {
  final n = s == null ? kVocalMaxTakes : crInt(crMap(s.ov['limits'])['takes']);
  final max = n <= 0 ? kVocalMaxTakes : math.min(n, kVocalMaxTakes);
  return [for (final t in const [1, 2, 4]) if (t <= max) '$t'];
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

  /// How far this sound has played (0 = not started here, 1 = to the end): the waveform fills up to it.
  double frac(String key) {
    final c = _ctl;
    if (id != key || c == null) return 0;
    final d = c.value.duration.inMilliseconds;
    if (d <= 0) return 0;
    return (c.value.position.inMilliseconds / d).clamp(0.0, 1.0).toDouble();
  }

  /// The controller of this sound while it is the one on the page (a dubbed video draws its picture from it).
  VideoPlayerController? controllerFor(String key) => id == key && !loading ? _ctl : null;

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

  /// Plays a sound straight from an address while the server is still making it (a one-time stream link that needs no
  /// key). [onEnd] runs once, when it has played to the end or stopped with an error.
  Future<void> playUrl(BuildContext context, String key, String url, {VoidCallback? onEnd}) async {
    if (VocalStore.debug || app.api == null) return;
    await _ctl?.dispose();
    _ctl = null;
    id = key;
    loading = true;
    _tell();
    var ended = false;
    void end() {
      if (ended) return;
      ended = true;
      onEnd?.call();
    }

    VideoPlayerController? c;
    try {
      c = VideoPlayerController.networkUrl(Uri.parse(url));
      await c.initialize();
    } catch (e) {
      await c?.dispose();
      loading = false;
      id = '';
      _tell();
      if (context.mounted) crToast(context, 'This sound did not play: ${crError(e)}');
      end();
      return;
    }
    if (_gone || id != key) {
      await c.dispose();
      end();
      return;
    }
    final ctl = c;
    ctl.addListener(() {
      final v = ctl.value;
      if (v.hasError || (v.isInitialized && !v.isPlaying && v.duration > Duration.zero && v.position >= v.duration)) end();
      _tell();
    });
    _ctl = ctl;
    loading = false;
    await ctl.play();
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
      container: true,
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


// ================================================================================================ v0.999.96 the redesign
// docs/HOOLA_VOCAL_REDESIGN.md: the phone's Vocal = one top bar ("Vocal · <page>", a menu opening the drawer with the
// same groups as the console), every page reachable, one waveform, one black pill, one recorder, one download menu.

/// Every page of Hoola Vocal, in the drawer's order.
enum VocalPage {
  chat('Vocal chat', CrGlyph.voice),
  speech('Speech', CrGlyph.mic),
  dialogue('Dialogue', CrGlyph.people),
  studio('Studio', CrGlyph.book),
  dub('Dubbing', CrGlyph.dub),
  library('Voice library', CrGlyph.grid),
  yours('Your voice', CrGlyph.cast),
  changer('Voice changer', CrGlyph.refresh),
  cleanup('Clean-up', CrGlyph.spark),
  sfx('Sound effects', CrGlyph.music),
  sounds('Your sounds', CrGlyph.folder),
  dictionary('Dictionary', CrGlyph.pen),
  settings('Settings', CrGlyph.layers);

  const VocalPage(this.title, this.glyph);
  final String title;
  final CrGlyph glyph;
}

/// The drawer's groups (the console sidebar's own).
const List<(String, List<VocalPage>)> kVocalGroups = [
  ('Make', [VocalPage.chat, VocalPage.speech, VocalPage.dialogue, VocalPage.studio, VocalPage.dub]),
  ('Voices', [VocalPage.library, VocalPage.yours]),
  ('Tools', [VocalPage.changer, VocalPage.cleanup, VocalPage.sfx]),
  ('Assets', [VocalPage.sounds, VocalPage.dictionary, VocalPage.settings]),
];

/// A 48 dp round icon button with a name a screen reader says (the top bar's buttons, a row's More).
class VocalIconButton extends StatelessWidget {
  const VocalIconButton({super.key, required this.label, required this.onTap, this.glyph, this.icon, this.color});
  final String label;
  final VoidCallback? onTap;
  final CrGlyph? glyph;
  final IconData? icon;
  final Color? color;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final col = onTap == null ? c.ink3 : (color ?? c.ink2);
    return Semantics(
      container: true,
      button: true,
      enabled: onTap != null,
      label: label,
      excludeSemantics: true,
      onTap: onTap,
      child: SizedBox(
        width: 48,
        height: 48,
        child: Material(
          type: MaterialType.transparency,
          shape: const CircleBorder(),
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: onTap,
            child: Center(child: icon != null ? Icon(icon, size: 20, color: col) : CrIcon(glyph ?? CrGlyph.info, size: 19, color: col)),
          ),
        ),
      ),
    );
  }
}

/// The 52 dp top bar: the menu (or Back), "Vocal · <page>", and up to two buttons.
class VocalBar extends StatelessWidget {
  const VocalBar({super.key, required this.page, this.crumb = 'Vocal', this.onMenu, this.onBack, this.actions = const []});
  final String page, crumb;
  final VoidCallback? onMenu, onBack;
  final List<Widget> actions;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      height: 52,
      padding: const EdgeInsets.fromLTRB(2, 0, 4, 0),
      decoration: BoxDecoration(color: c.bg, border: Border(bottom: BorderSide(color: c.line))),
      child: Row(children: [
        if (onBack != null)
          VocalIconButton(label: 'Back', glyph: CrGlyph.back, color: c.ink, onTap: onBack)
        else if (onMenu != null)
          VocalIconButton(label: 'Open the Vocal menu', icon: Icons.menu_rounded, color: c.ink, onTap: onMenu)
        else
          const SizedBox(width: 12),
        const SizedBox(width: 2),
        Expanded(
          child: Semantics(
            header: true,
            child: Text.rich(
              TextSpan(children: [
                TextSpan(text: '$crumb · ', style: HoolaType.body(c).copyWith(color: c.ink2)),
                TextSpan(text: page, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
              ]),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
        ...actions,
      ]),
    );
  }
}

/// The drawer: the Hoola mark + a Vocal badge, every group, the month's credits at the bottom.
class VocalDrawer extends StatelessWidget {
  const VocalDrawer({super.key, required this.store, required this.page, required this.onPick, this.onLeave});
  final VocalStore store;
  final VocalPage page;
  final ValueChanged<VocalPage> onPick;
  final VoidCallback? onLeave;

  Widget _row(BuildContext context, HoolaColors c, String label, CrGlyph glyph, bool on, VoidCallback onTap) => Semantics(
        container: true,
        button: true,
        selected: on,
        label: label,
        excludeSemantics: true,
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 1),
          child: Material(
            color: on ? c.accentSoft : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            child: InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: onTap,
              child: SizedBox(
                height: 48,
                child: Row(children: [
                  Container(width: 3, height: 22, decoration: BoxDecoration(color: on ? c.accent : Colors.transparent,
                      borderRadius: BorderRadius.circular(2))),
                  const SizedBox(width: 11),
                  CrIcon(glyph, size: 18, color: on ? c.accent : c.ink2),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: HoolaType.body(c).copyWith(fontWeight: on ? FontWeight.w600 : FontWeight.w400)),
                  ),
                ]),
              ),
            ),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final w = math.min(320.0, MediaQuery.sizeOf(context).width * .86);
    // the drawer is closed the way Flutter closes one (it sits on the page's own history), then the page changes
    void go(VocalPage p) {
      Navigator.of(context).pop();
      onPick(p);
    }

    return Drawer(
      width: w,
      backgroundColor: c.surface,
      child: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 14, 12, 8),
            child: Row(children: [
              const HoolaMark(size: 24, animate: false),
              const SizedBox(width: 10),
              Text('Hoola', style: HoolaType.title(c)),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: c.accentSoft, borderRadius: BorderRadius.circular(6)),
                child: Text('Vocal', style: HoolaType.label(c).copyWith(color: c.ink)),
              ),
            ]),
          ),
          if (onLeave != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: _row(context, c, 'Back to Hoola', CrGlyph.back, false, () {
                Navigator.of(context).pop();
                onLeave!();
              }),
            ),
          Expanded(
            child: ListView(padding: const EdgeInsets.fromLTRB(8, 4, 8, 8), children: [
              for (final g in kVocalGroups) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(14, 14, 8, 4),
                  child: Semantics(header: true, child: Text(g.$1, style: HoolaType.label(c))),
                ),
                for (final p in g.$2) _row(context, c, p.title, p.glyph, p == page, () => go(p)),
              ],
            ]),
          ),
          Padding(padding: const EdgeInsets.fromLTRB(12, 4, 12, 12), child: VocalCredits(store: store)),
        ]),
      ),
    );
  }
}

/// "This month · N credits left", a bar, "X of Y used" (from the overview's usage; credits only, never money).
class VocalCredits extends StatelessWidget {
  const VocalCredits({super.key, required this.store});
  final VocalStore store;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final u = crMap(store.ov['usage']);
    final used = crInt(u['credits_used'] ?? u['credits']);
    final hasLeft = u['credits_left'] != null;
    final left = crInt(u['credits_left']);
    final total = used + left;
    final frac = hasLeft && total > 0 ? used / total : 0.0;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(12)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text(hasLeft ? 'This month · $left credits left' : 'This month · $used credit${used == 1 ? '' : 's'} used',
            style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500)),
        if (hasLeft) ...[
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: SizedBox(height: 6, child: LinearProgressIndicator(value: frac, color: c.accent, backgroundColor: c.line)),
          ),
          const SizedBox(height: 6),
          Text('$used of $total used', style: HoolaType.small(c).copyWith(fontSize: 12)),
        ],
      ]),
    );
  }
}

/// The quiet waveform every take shows: bars from the sound's id (the same shape each time), filled to where it plays.
class VocalWave extends StatelessWidget {
  const VocalWave({super.key, required this.seed, this.frac = 0, this.bars = 34, this.height = 20, this.levels});
  final String seed;
  final double frac;
  final int bars;
  final double height;
  /// Live loudness (a recording in progress), newest last; replaces the drawn shape.
  final List<double>? levels;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return ExcludeSemantics(
      child: SizedBox(
        height: height,
        width: double.infinity,
        child: CustomPaint(painter: _VocalWavePainter(seed, frac, bars, levels, c.ink, c.lineStrong, c.accent)),
      ),
    );
  }
}

class _VocalWavePainter extends CustomPainter {
  _VocalWavePainter(this.seed, this.frac, this.bars, this.levels, this.on, this.off, this.live);
  final String seed;
  final double frac;
  final int bars;
  final List<double>? levels;
  final Color on, off, live;
  @override
  void paint(Canvas canvas, Size size) {
    if (size.width <= 0 || bars <= 0) return;
    final slot = size.width / bars;
    final w = math.min(3.0, slot * .6);
    final s = (seed.codeUnits.fold<int>(7, (a, b) => (a * 31 + b) & 0x7fffffff) % 1000) / 160.0;
    final lv = levels;
    for (var i = 0; i < bars; i++) {
      double h;
      Color col;
      if (lv != null) {
        final k = lv.length - bars + i;
        final v = k >= 0 && k < lv.length ? lv[k] : 0.0;
        h = 3 + math.min(1.0, v * 6) * (size.height - 3);
        col = k >= 0 ? live : off;
      } else {
        h = 4 + (math.sin(i * .7 + s) * math.cos(i * .23 + s * 2)).abs() * (size.height - 6);
        col = frac <= 0 || (i + .5) / bars <= frac ? on.withOpacity(frac <= 0 ? .78 : 1.0) : off;
      }
      canvas.drawRRect(
          RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(slot * (i + .5), size.height / 2), width: w, height: h),
              const Radius.circular(2)),
          Paint()..color = col);
    }
  }

  @override
  bool shouldRepaint(_VocalWavePainter o) =>
      o.frac != frac || o.seed != seed || o.on != on || o.off != off || o.levels?.length != levels?.length;
}

/// The page's main action: the black pill ([quiet] = the outline one beside it).
class VocalPill extends StatelessWidget {
  const VocalPill({super.key, required this.label, required this.onTap, this.busy = false, this.quiet = false, this.height = 48, this.glyph});
  final String label;
  final VoidCallback? onTap;
  final bool busy, quiet;
  final double height;
  final CrGlyph? glyph;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final on = onTap != null && !busy;
    final fg = quiet ? (on ? c.ink : c.ink3) : c.onPill;
    return Semantics(
      container: true,
      button: true,
      enabled: on,
      label: label,
      excludeSemantics: true,
      onTap: on ? onTap : null,
      child: Opacity(
        opacity: on || quiet ? 1.0 : 0.5,
        child: Material(
          color: quiet ? c.surface : c.pill,
          shape: StadiumBorder(side: quiet ? BorderSide(color: c.lineStrong) : BorderSide.none),
          child: InkWell(
            customBorder: const StadiumBorder(),
            onTap: on ? onTap : null,
            child: SizedBox(
              height: height,
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    if (busy)
                      SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: fg))
                    else if (glyph != null)
                      CrIcon(glyph!, size: 16, color: fg),
                    if (busy || glyph != null) const SizedBox(width: 8),
                    Flexible(
                      child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500, color: fg)),
                    ),
                  ]),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// The docked bottom of a tool page: its action(s) and a quiet line ("Nothing is spent until you tap").
class VocalDock extends StatelessWidget {
  const VocalDock({super.key, required this.child, this.note = ''});
  final Widget child;
  final String note;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      decoration: BoxDecoration(color: c.bg, border: Border(top: BorderSide(color: c.line))),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        child,
        if (note.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(note, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: HoolaType.small(c).copyWith(fontSize: 12, color: c.ink2)),
        ],
      ]),
    );
  }
}

/// A chip: the black pill when on, an outline when off; [menu] adds a small arrow (it opens a list).
class VocalChip extends StatelessWidget {
  const VocalChip({super.key, required this.label, required this.onTap, this.on = false, this.menu = false});
  final String label;
  final VoidCallback? onTap;
  final bool on, menu;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final fg = on ? c.onPill : c.ink;
    return Semantics(
      container: true,
      button: true,
      selected: on,
      label: label,
      excludeSemantics: true,
      onTap: onTap,
      child: crTap48(onTap, Container(
        height: 36,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          color: on ? c.pill : c.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: on ? c.pill : c.line),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Flexible(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 220),
              child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontSize: 13, color: fg)),
            ),
          ),
          if (menu) ...[const SizedBox(width: 2), Icon(Icons.expand_more_rounded, size: 16, color: fg)],
        ]),
      )),
    );
  }
}

/// A sunk tray of tabs (Hoola / Shared / Yours); the chosen one lifts out on the page colour.
class VocalTabs extends StatelessWidget {
  const VocalTabs({super.key, required this.tabs, required this.picked, required this.onPick});
  final List<String> tabs;
  final String picked;
  final ValueChanged<String> onPick;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(12)),
      child: Row(children: [
        for (final t in tabs)
          Expanded(
            child: Semantics(
              container: true,
              button: true,
              selected: t == picked,
              label: t,
              excludeSemantics: true,
              onTap: () => onPick(t),
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => onPick(t),
                child: Container(
                  height: 48,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(color: t == picked ? c.surface : Colors.transparent, borderRadius: BorderRadius.circular(9)),
                  child: Text(t, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: t == picked ? FontWeight.w600 : FontWeight.w400)),
                ),
              ),
            ),
          ),
      ]),
    );
  }
}

/// A card of setting rows ("Language  Hindi  >"), each opening its own list.
class VocalRows extends StatelessWidget {
  const VocalRows(this.rows, {super.key});
  final List<(String, String, VoidCallback?)> rows;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: c.line)),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: Column(children: [
          for (var i = 0; i < rows.length; i++) ...[
            if (i > 0) Divider(height: 1, thickness: 1, color: c.line),
            Semantics(
              container: true,
              button: rows[i].$3 != null,
              label: '${rows[i].$1}: ${rows[i].$2}',
              excludeSemantics: true,
              onTap: rows[i].$3,
              child: Material(
                type: MaterialType.transparency,
                child: InkWell(
                  onTap: rows[i].$3,
                  child: SizedBox(
                    height: 52,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      child: Row(children: [
                        Expanded(child: Text(rows[i].$1, maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: HoolaType.body(c).copyWith(fontSize: 14, color: c.ink2))),
                        const SizedBox(width: 8),
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 210),
                          child: Text(rows[i].$2, maxLines: 1, overflow: TextOverflow.ellipsis,
                              style: HoolaType.body(c).copyWith(fontSize: 14)),
                        ),
                        if (rows[i].$3 != null) ...[const SizedBox(width: 6), CrIcon(CrGlyph.chevron, size: 14, color: c.ink3)],
                      ]),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ]),
      ),
    );
  }
}

/// A plain bordered input (the boards' text boxes).
InputDecoration vocalInput(HoolaColors c, String hint) => InputDecoration(
      hintText: hint,
      hintStyle: HoolaType.body(c).copyWith(color: c.ink3),
      filled: true,
      fillColor: c.surface,
      isDense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
      constraints: const BoxConstraints(minHeight: 48),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: c.lineStrong)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: c.lineStrong)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: c.accent)),
    );

/// A small section name above a block.
class VocalLabel extends StatelessWidget {
  const VocalLabel(this.text, {super.key, this.note = ''});
  final String text, note;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(children: [
        Expanded(child: Semantics(header: true, child: Text(text, style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500)))),
        if (note.isNotEmpty) Text(note, style: HoolaType.small(c).copyWith(fontSize: 12)),
      ]),
    );
  }
}

/// One take: play (44 dp), its name over the waveform, its length, and More.
class VocalTakeRow extends StatelessWidget {
  const VocalTakeRow({super.key, required this.store, required this.player, required this.item, required this.name, this.note = '',
      this.onMore});
  final VocalStore store;
  final VocalPlayer player;
  final Map<String, dynamic> item;
  final String name, note;
  final VoidCallback? onMore;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final id = crS(item['id']);
    final playing = player.playing(id);
    final secs = item['seconds'] is num ? item['seconds'] as num : 0;
    final ext = crS(item['ext']) == 'mp4' ? 'mp4' : 'mp3';
    return Row(children: [
      VocalPlayButton(
        label: '${playing ? 'Pause' : 'Play'} $name',
        playing: playing,
        loading: player.busy(id),
        size: 44,
        onTap: () => player.toggle(context, id, () => store.app.api!.vocalAudio(id, format: ext), ext: ext),
      ),
      const SizedBox(width: 8),
      Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          Text.rich(
            TextSpan(children: [
              TextSpan(text: name, style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500)),
              if (note.isNotEmpty) TextSpan(text: ' · $note', style: HoolaType.body(c).copyWith(fontSize: 13, color: c.ink2)),
            ]),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          VocalWave(seed: id, frac: player.frac(id)),
        ]),
      ),
      const SizedBox(width: 8),
      if (secs > 0)
        Text(vocalClock(secs), style: HoolaType.small(c).copyWith(fontSize: 12, fontFeatures: const [ui.FontFeature.tabularFigures()])),
      if (onMore != null) VocalIconButton(label: 'More for $name', icon: Icons.more_horiz_rounded, onTap: onMore),
    ]);
  }
}

/// A card around a block (bordered, the boards' look).
class VocalBox extends StatelessWidget {
  const VocalBox({super.key, required this.child, this.padding = const EdgeInsets.all(12), this.edge, this.fill});
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? edge, fill;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      padding: padding,
      decoration: BoxDecoration(color: fill ?? c.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: edge ?? c.line)),
      child: child,
    );
  }
}

// ------------------------------------------------------------------------------------------------ files in and out
/// A file she picked or recorded: its name and bytes (seconds when the phone measured them).
class VocalFile {
  VocalFile(this.name, this.bytes, {this.seconds = 0, this.level = 0});
  final String name;
  final List<int> bytes;
  final double seconds;   // 0 = not measured here
  final double level;     // the recording's average loudness 0..1 (0 = not measured)
}

/// A file from the phone (audio by default; video for a dub), up to [maxMb].
Future<VocalFile?> vocalPickFile(BuildContext context, {bool video = false, int maxMb = 30}) async {
  if (VocalStore.debug) return VocalFile(video ? 'product.mp4' : 'recording.m4a', const [1, 2, 3], seconds: video ? 62.0 : 24.0);
  final r = await FilePicker.platform.pickFiles(type: video ? FileType.video : FileType.audio, withData: true);
  final f = r?.files.firstOrNull;
  if (f == null) return null;
  final b = f.bytes;
  if (b == null) {
    if (context.mounted) crToast(context, 'This file could not be read.');
    return null;
  }
  if (b.length > maxMb * 1024 * 1024) {
    if (context.mounted) crToast(context, 'This file is over $maxMb MB. Choose a shorter one.');
    return null;
  }
  return VocalFile(f.name, b);
}

/// A file up to the server through the chat file lane (owner-checked there): its file id.
Future<String> vocalUpload(VocalStore store, String conv, VocalFile f) async {
  if (VocalStore.debug) return 'f_debug';
  final api = store.app.api;
  if (api == null) throw Exception('Not connected to the server right now');
  var cv = conv;
  if (cv.isEmpty) cv = crS((await api.vocalChat())['id']);
  final id = crS((await api.chatFile(cv, f.name, f.bytes))['file_id']);
  if (id.isEmpty) throw Exception('The file did not upload. Try again.');
  return id;
}

/// What a file is called for the phone's share sheet.
String vocalMime(String ext) => switch (ext) {
      'mp3' => 'audio/mpeg',
      'wav' => 'audio/wav',
      'ogg' => 'audio/ogg',
      'm4a' => 'audio/mp4',
      'flac' => 'audio/flac',
      'mp4' => 'video/mp4',
      'srt' => 'application/x-subrip',
      'vtt' => 'text/vtt',
      _ => 'application/octet-stream',
    };

/// The download formats the server lists (overview `formats`), else the four it makes.
List<Map<String, dynamic>> vocalFormats(VocalStore s) {
  final f = crList(s.ov['formats']);
  return f.isNotEmpty ? f : kVocalFormats;
}

const List<Map<String, dynamic>> kVocalFormats = [
  {'id': 'mp3', 'name': 'MP3', 'note': 'small, for sharing'},
  {'id': 'wav', 'name': 'WAV', 'note': 'studio quality'},
  {'id': 'ogg', 'name': 'OGG', 'note': 'for WhatsApp'},
  {'id': 'm4a', 'name': 'M4A', 'note': 'for iPhone'},
];

/// "MP3", or the format's name when it is known.
String vocalFormatName(VocalStore s, String id) {
  for (final f in vocalFormats(s)) {
    if (crS(f['id']) == id) return crS(f['name']).isEmpty ? id.toUpperCase() : crS(f['name']);
  }
  return id.toUpperCase();
}

/// Asks which format, then hands the file to the phone's share sheet (save to files, WhatsApp...). A video goes as it is.
Future<void> vocalShare(BuildContext context, Santosh app, Map<String, dynamic> r, {VocalStore? store}) async {
  final api = app.api;
  if (api == null || VocalStore.debug) return;
  var fmt = crS(r['ext']) == 'mp4' ? 'mp4' : 'mp3';
  if (fmt != 'mp4') {
    final list = store == null ? kVocalFormats : vocalFormats(store);
    final names = [for (final f in list) crS(f['name'])];
    final pick = await crPick(context, 'Download as', names, '', notes: {for (final f in list) crS(f['name']): crS(f['note'])});
    if (pick == null || !context.mounted) return;
    fmt = crS(list.firstWhere((f) => crS(f['name']) == pick, orElse: () => kVocalFormats.first)['id']);
  }
  crToast(context, 'Getting the file…');
  try {
    final bytes = await api.vocalAudio(crS(r['id']), format: fmt == 'mp4' ? '' : fmt);
    if (bytes == null) throw Exception('This sound is no longer on Hoola.');
    if (!context.mounted) return;
    await crShareBytes(context, bytes, '${crS(r['title']).isEmpty ? 'Hoola sound' : crS(r['title'])}.$fmt', vocalMime(fmt));
  } catch (e) {
    if (context.mounted) crToast(context, crError(e));
  }
}

/// A silent 16 kHz WAV of [seconds] (tests and the debug seam stand in for the microphone with it).
Uint8List vocalSilentWav(int seconds) => VoiceRecorder.wav(Uint8List(seconds * 32000));

/// What the phone can check about a recording before it goes up: long enough, loud enough, not too long.
List<(bool, String)> vocalChecks(VocalFile f, {int min = 10, int max = 30}) {
  if (f.seconds <= 0) return const [];
  final s = f.seconds;
  return [
    if (s < min) (false, '${(min - s).ceil()} more second${(min - s).ceil() == 1 ? '' : 's'} needed') else (true, 'Long enough'),
    if (f.level > 0) f.level < .012 ? (false, 'Too quiet: hold the phone closer') : (true, 'Loud enough'),
    if (s > max + .5) (false, 'Only the first $max seconds are used'),
  ];
}

/// Records with the phone's microphone (the app's own recorder, 16 kHz WAV): a big round button, the live loudness, the
/// clock, and the checks after. Stops by itself at [maxSeconds].
class VocalRecorder extends StatefulWidget {
  const VocalRecorder({super.key, required this.onDone, this.maxSeconds = 30, this.minSeconds = 10, this.what = 'recording'});
  final ValueChanged<VocalFile> onDone;
  final int maxSeconds, minSeconds;
  final String what;
  @override
  State<VocalRecorder> createState() => _VocalRecorderState();
}

class _VocalRecorderState extends State<VocalRecorder> {
  VoiceRecorder? _rec;
  Timer? _tick;
  String _err = '';
  final List<double> _levels = [];
  VocalFile? _done;
  bool _starting = false;

  bool get _on => _rec != null;

  Future<void> _start() async {
    if (_on || _starting) return;
    if (VocalStore.debug) {
      _finish(VocalFile('${widget.what}.wav', vocalSilentWav(1), seconds: math.min(24, widget.maxSeconds).toDouble(), level: .2));
      return;
    }
    setState(() => _starting = true);
    final r = VoiceRecorder();
    String? e;
    try {
      e = await r.start();
    } catch (x) {
      e = crError(x);
    }
    if (!mounted) {
      await r.stop();
      return;
    }
    if (e != null) {
      setState(() {
        _err = e!;
        _starting = false;
      });
      return;
    }
    setState(() {
      _rec = r;
      _starting = false;
      _err = '';
      _done = null;
      _levels.clear();
    });
    _tick = Timer.periodic(const Duration(milliseconds: 150), (_) {
      final rr = _rec;
      if (!mounted || rr == null) return;
      setState(() => _levels.add(rr.level));
      if (rr.length.inMilliseconds >= widget.maxSeconds * 1000) _stop();
    });
  }

  Future<void> _stop() async {
    _tick?.cancel();
    final r = _rec;
    if (r == null) return;
    _rec = null;
    final wav = await r.stop();
    final secs = math.max(0, wav.length - 44) / 32000;
    final avg = _levels.isEmpty ? 0.0 : _levels.reduce((a, b) => a + b) / _levels.length;
    final stamp = DateTime.now().toIso8601String().substring(0, 16).replaceAll(':', '-');
    _finish(VocalFile('${widget.what}-$stamp.wav', wav, seconds: secs, level: avg));
  }

  void _finish(VocalFile f) {
    if (!mounted) return;
    setState(() => _done = f);
    widget.onDone(f);
  }

  @override
  void dispose() {
    _tick?.cancel();
    final r = _rec;
    if (r != null && r.recording) r.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final secs = _on ? _rec!.length.inMilliseconds / 1000 : (_done?.seconds ?? 0);
    final label = _on ? 'Stop recording' : (_done == null ? 'Record' : 'Record again');
    return Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
      Row(children: [
        Semantics(
          container: true,
          button: true,
          label: label,
          excludeSemantics: true,
          onTap: _on ? _stop : _start,
          child: GestureDetector(
            onTap: _on ? _stop : _start,
            child: Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(color: _on ? c.bad : c.pill, shape: BoxShape.circle),
              child: Center(
                child: _starting
                    ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                    : _on
                        ? Container(width: 16, height: 16, decoration: BoxDecoration(color: c.onPill, borderRadius: BorderRadius.circular(3)))
                        : CrIcon(CrGlyph.mic, size: 22, color: c.onPill),
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(_on ? 'Recording' : (_done == null ? 'Tap to record' : 'Recorded'),
                style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500)),
            const SizedBox(height: 4),
            VocalWave(seed: widget.what, levels: _on ? _levels : (_done == null ? const <double>[] : null), frac: _done == null ? 0.0 : 1.0, bars: 40),
            const SizedBox(height: 2),
            Text('${vocalClock(secs)} of ${vocalClock(widget.maxSeconds)}',
                style: HoolaType.small(c).copyWith(fontSize: 12, fontFeatures: const [ui.FontFeature.tabularFigures()])),
          ]),
        ),
      ]),
      if (_err.isNotEmpty) ...[
        const SizedBox(height: 8),
        Text(_err, style: HoolaType.small(c).copyWith(color: c.bad)),
      ],
      if (_done != null) ...[
        const SizedBox(height: 10),
        Wrap(spacing: 12, runSpacing: 6, children: [
          for (final k in vocalChecks(_done!, min: widget.minSeconds, max: widget.maxSeconds))
            Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(k.$1 ? Icons.check_rounded : Icons.error_outline_rounded, size: 16, color: k.$1 ? c.ok : c.warn),
              const SizedBox(width: 4),
              Text(k.$2, style: HoolaType.small(c).copyWith(fontSize: 12, color: k.$1 ? c.ok : c.warn)),
            ]),
        ]),
      ],
    ]);
  }
}

/// A page body on its own screen (a Back bar above it), or as it is inside the Vocal frame ([embedded]).
Widget vocalFrame(BuildContext context, {required bool embedded, required String title, required Widget body}) {
  if (embedded) return body;
  final c = HoolaColors.of(context);
  return CrHueScope(
    hue: CrHue.voice,
    child: Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          VocalBar(page: title, onBack: () => Navigator.of(context).maybePop()),
          Expanded(child: body),
        ]),
      ),
    ),
  );
}

/// A row's More menu: its choices in a sheet.
Future<String?> vocalMore(BuildContext context, String title, List<String> choices) => crPick(context, title, choices, '');

/// Removes one sound from Your sounds (asks first): true when it went.
Future<bool> vocalDeleteSound(BuildContext context, VocalStore store, Map<String, dynamic> r) async {
  final ok = await vocalConfirm(context, 'Delete this sound?', 'It is removed from Your sounds and from its chat. This cannot be undone.', 'Delete');
  if (ok != true) return false;
  try {
    if (!VocalStore.debug) await store.app.api?.vocalHistoryDelete(crS(r['id']));
    store.ov = {...store.ov, 'history': store.history.where((x) => crS(x['id']) != crS(r['id'])).toList()};
    store.tell();
    return true;
  } catch (e) {
    if (context.mounted) crToast(context, crError(e));
    return false;
  }
}

/// The takes a job answered with: its `items`, or the one row it made.
List<Map<String, dynamic>> vocalMade(Map<String, dynamic> r) {
  final items = crList(r['items']);
  if (items.isNotEmpty) return items;
  return crS(r['id']).isEmpty ? const [] : [r];
}

/// "4 credits" from a quote, else "".
String vocalCredits(Map<String, dynamic> q) {
  final n = crInt(q['credits']);
  return n > 0 ? '$n credit${n == 1 ? '' : 's'}' : '';
}

/// A job that went wrong, said plainly; out of credits (402) offers the Credits screen.
void vocalError(BuildContext context, VocalStore store, Object e) {
  if (e is ApiException && e.status == 402) {
    final m = ScaffoldMessenger.maybeOf(context);
    if (m == null) return;
    m
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(
        content: Text(e.message.isEmpty ? 'You are out of credits.' : e.message),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 6),
        action: SnackBarAction(
          label: 'Get credits',
          onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
              builder: (_) => HoolaTheme(appearance: store.app.appearance, child: HoolaCreditsPage(app: store.app)))),
        ),
      ));
    return;
  }
  crToast(context, crError(e));
}

// ================================================================================================ v0.999.101 the last parts
/// A document from the phone (text, PDF, Word, web page, ebook), up to 30 MB.
Future<VocalFile?> vocalPickDoc(BuildContext context) async {
  if (VocalStore.debug) return VocalFile('notes.txt', const [1]);
  final r = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom,
      allowedExtensions: const ['txt', 'md', 'pdf', 'docx', 'epub', 'html']);
  final f = r?.files.firstOrNull;
  final b = f?.bytes;
  if (f == null || b == null) return null;
  if (b.length > 30 * 1024 * 1024) {
    if (context.mounted) crToast(context, 'This file is over 30 MB.');
    return null;
  }
  return VocalFile(f.name, b);
}

/// Dub it works on a finished speech or dialogue take.
bool vocalCanDub(Map<String, dynamic> r) =>
    !vocalFailed(r) && r['failed_dub'] != true && (crS(r['kind']) == 'tts' || crS(r['kind']) == 'dialogue');

/// The most languages one take is dubbed into at once.
const int kVocalTakeDubMax = 4;

/// Dub it on one take: she picks up to four languages (the price shows first), then each language comes back as its own
/// take in the same voice(s). The new takes are shown with a play button; a language that could not be made is said
/// plainly. Returns the new takes ([] when she stopped or nothing was made).
Future<List<Map<String, dynamic>>> vocalDubTake(BuildContext context, VocalStore store, VocalPlayer player, Map<String, dynamic> take,
    {String chat = ''}) async {
  final langs = await showModalBottomSheet<List<String>>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (_) => CrHueScope(hue: CrHue.voice, child: VocalTakeDubSheet(store: store, take: take)),
  );
  if (langs == null || langs.isEmpty || !context.mounted) return const [];
  crToast(context, 'Dubbing into ${langs.map(store.langName).join(', ')}…');
  Map<String, dynamic> r;
  try {
    final id = crS(take['id']);
    final body = {'langs': langs, if (chat.isNotEmpty) 'chat': chat};
    if (VocalStore.debug) {
      r = VocalStore.debugAnswer('take_dub', {'id': id, ...body});
    } else {
      final api = store.app.api;
      if (api == null) throw Exception('Not connected to the server right now');
      r = await api.vocalTakeDub(id, langs, chat: chat);
    }
  } catch (e) {
    if (context.mounted) vocalError(context, store, e);
    return const [];
  }
  final made = crList(r['items']);
  final failed = crList(r['failed']);
  unawaited(store.load());
  if (context.mounted) {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => CrHueScope(hue: CrHue.voice,
          child: VocalTakeDubDone(store: store, player: player, made: made, failed: failed, credits: crInt(r['credits']))),
    );
  }
  return made;
}

/// Pick the languages for Dub it: search, up to four, the price before the tap.
class VocalTakeDubSheet extends StatefulWidget {
  const VocalTakeDubSheet({super.key, required this.store, required this.take});
  final VocalStore store;
  final Map<String, dynamic> take;
  @override
  State<VocalTakeDubSheet> createState() => _VocalTakeDubSheetState();
}

class _VocalTakeDubSheetState extends State<VocalTakeDubSheet> {
  final _find = TextEditingController();
  final List<String> _pick = [];
  Map<String, dynamic> _quote = const {};
  VocalStore get store => widget.store;

  @override
  void initState() {
    super.initState();
    _requote();
  }

  @override
  void dispose() {
    _find.dispose();
    super.dispose();
  }

  Future<void> _requote() async {
    final t = widget.take;
    final body = {
      'job': crS(t['kind']) == 'dialogue' ? 'dialogue' : 'tts',
      'seconds': t['seconds'] is num ? t['seconds'] as num : 15,
      'takes': 1,
      if (crS(t['voice']).isNotEmpty) 'voice': crS(t['voice']),
    };
    if (VocalStore.debug) {
      setState(() => _quote = crMap(VocalStore.debugData!['quote']));
      return;
    }
    try {
      final q = await store.app.api?.vocalQuote(body);
      if (q != null && mounted) setState(() => _quote = q);
    } catch (_) {}
  }

  void _toggle(String code) {
    setState(() {
      if (_pick.contains(code)) {
        _pick.remove(code);
      } else if (_pick.length < kVocalTakeDubMax) {
        _pick.add(code);
      } else {
        crToast(context, 'Up to $kVocalTakeDubMax languages at a time.');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final own = crS(widget.take['lang']);
    final q = _find.text.trim().toLowerCase();
    final langs = store.langs.where((l) {
      if (crS(l['speech']) == 'none' || crS(l['code']) == own) return false;
      if (q.isEmpty) return true;
      return '${crS(l['name'])} ${crS(l['native'])} ${crS(l['code'])}'.toLowerCase().contains(q);
    }).toList();
    final per = crInt(_quote['credits']);
    final total = per * (_pick.isEmpty ? 1 : _pick.length);
    final title = crS(widget.take['title']).isEmpty ? 'this take' : '“${crS(widget.take['title'])}”';
    final price = per <= 0
        ? ''
        : _pick.length <= 1
            ? 'About $per credit${per == 1 ? '' : 's'} a language'
            : 'About $per credit${per == 1 ? '' : 's'} a language · ${_pick.length} languages ≈ $total credits';
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(16, 0, 16, 12 + MediaQuery.viewInsetsOf(context).bottom),
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * .8),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Semantics(header: true, child: Text('Dub this take', style: HoolaType.title(c))),
            const SizedBox(height: 4),
            Text('$title said again in other languages, in the same voice. Each language is its own take.',
                style: HoolaType.small(c).copyWith(fontSize: 13, color: c.ink2)),
            const SizedBox(height: 10),
            VocalSearch(controller: _find, hint: 'Search languages', onChanged: (_) => setState(() {})),
            const SizedBox(height: 8),
            VocalLabel('Into', note: '${_pick.length} of $kVocalTakeDubMax'),
            Flexible(
              child: SingleChildScrollView(
                child: Wrap(spacing: 6, runSpacing: 0, children: [
                  for (final l in langs)
                    VocalChip(
                      label: crS(l['native']).isEmpty ? crS(l['name']) : crS(l['native']),
                      on: _pick.contains(crS(l['code'])),
                      onTap: () => _toggle(crS(l['code'])),
                    ),
                  if (langs.isEmpty) Padding(padding: const EdgeInsets.all(8), child: Text('No language matches.', style: HoolaType.small(c))),
                ]),
              ),
            ),
            const SizedBox(height: 10),
            if (price.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(price, textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 12, color: c.ink2)),
              ),
            VocalPill(
              label: per > 0 && _pick.isNotEmpty ? 'Dub it · $total credits' : 'Dub it',
              onTap: _pick.isEmpty ? null : () => Navigator.of(context).pop(List<String>.from(_pick)),
            ),
            const SizedBox(height: 4),
            Text('Nothing is spent until you tap', textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
        ),
      ),
    );
  }
}

/// What Dub it made: each language's take to play, and each language that could not be made, with why.
class VocalTakeDubDone extends StatelessWidget {
  const VocalTakeDubDone({super.key, required this.store, required this.player, required this.made, required this.failed, this.credits = 0});
  final VocalStore store;
  final VocalPlayer player;
  final List<Map<String, dynamic>> made, failed;
  final int credits;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: ListenableBuilder(
          listenable: player,
          builder: (context, _) => Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Semantics(header: true, child: Text(made.isEmpty ? 'Nothing was dubbed' : 'Dubbed', style: HoolaType.title(c))),
            if (credits > 0) Text('$credits credit${credits == 1 ? '' : 's'}', style: HoolaType.small(c).copyWith(fontSize: 12)),
            const SizedBox(height: 10),
            for (final t in made) ...[
              VocalTakeRow(store: store, player: player, item: t, name: store.langNative(crS(t['lang']))),
              const SizedBox(height: 6),
            ],
            for (final f in failed)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: CrNote('${crS(f['name']).isEmpty ? store.langName(crS(f['lang'])) : crS(f['name'])} could not be made: '
                    '${crS(f['why']).isEmpty ? 'it did not work this time' : crS(f['why'])}. Nothing was charged for it.', glyph: CrGlyph.info),
              ),
            const SizedBox(height: 12),
            VocalPill(label: 'Done', quiet: true, onTap: () => Navigator.of(context).pop()),
          ]),
        ),
      ),
    );
  }
}
