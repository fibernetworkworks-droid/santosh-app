// v0.999.83 HOOLA MUSIC ON THE PHONE (owner, on the design canvas claude.ai/artifact/Qq4WmnjktJD7VS9torkejn boards 11-13:
// "GO BUILD ALL"): Create > Music on the phone is the console's Music page - one chat (the same Conversation kind
// 'music', /api/music/chat*), Song settings in ONE sheet above the box (what, language Auto or any of 40, singers, style,
// mood, length, tempo, 1 / 2 / 4 versions, keep out, her lyrics by parts), the songs land in the chat as a set of versions
// (Reel cut / Fade the end / More like this), a song opens in its own dark player with its words and quick changes, every
// change is a NEW version (the old one stays), Your songs with search + filters, earlier Music chats, and failures said
// plainly ("Hoola can't answer right now" -> make the song straight away; a version that could not be made -> Try again).
// Her picks ride her message as the same "[Web console Song settings: ...]" note the console sends, so the server reads
// both the same; her bubble shows only her words. Money: a song is made when she sends (the price sits under the box);
// changes to a made song are free (ffmpeg on the server). Every song carries the AI mark.
import 'dart:async';
import 'dart:math' as math;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';

import '../../state.dart';
import '../hoola_mark.dart';
import '../hoola_theme.dart';
import 'create_kit.dart';

// ------------------------------------------------------------------------------------------------ choices
const kMusicLangs = ['Auto', 'English', 'Spanish', 'Portuguese', 'Hindi', 'Arabic', 'French', 'Japanese', 'Korean',
  'Chinese (Mandarin)', 'German', 'Italian', 'Russian', 'Turkish', 'Indonesian', 'Vietnamese', 'Thai', 'Filipino', 'Bengali',
  'Tamil', 'Telugu', 'Marathi', 'Punjabi', 'Urdu', 'Gujarati', 'Kannada', 'Malayalam', 'Hinglish', 'Swahili', 'Yoruba',
  'Igbo', 'Hausa', 'Zulu', 'Amharic', 'Persian', 'Hebrew', 'Polish', 'Dutch', 'Swedish', 'Greek', 'Ukrainian'];
/// The name a language is written in, shown beside the English one in the language sheet.
const kMusicLangNative = {
  'Spanish': 'Español', 'Portuguese': 'Português', 'Hindi': 'हिन्दी', 'Arabic': 'العربية', 'French': 'Français',
  'Japanese': '日本語', 'Korean': '한국어', 'Chinese (Mandarin)': '中文', 'German': 'Deutsch', 'Italian': 'Italiano',
  'Russian': 'Русский', 'Turkish': 'Türkçe', 'Indonesian': 'Bahasa Indonesia', 'Vietnamese': 'Tiếng Việt', 'Thai': 'ไทย',
  'Bengali': 'বাংলা', 'Tamil': 'தமிழ்', 'Telugu': 'తెలుగు', 'Marathi': 'मराठी', 'Punjabi': 'ਪੰਜਾਬੀ', 'Urdu': 'اردو',
  'Gujarati': 'ગુજરાતી', 'Kannada': 'ಕನ್ನಡ', 'Malayalam': 'മലയാളം', 'Swahili': 'Kiswahili', 'Persian': 'فارسی',
  'Hebrew': 'עברית', 'Polish': 'Polski', 'Dutch': 'Nederlands', 'Swedish': 'Svenska', 'Greek': 'Ελληνικά',
  'Ukrainian': 'Українська', 'Zulu': 'isiZulu', 'Amharic': 'አማርኛ',
};
const kMusicMostUsed = ['English', 'Spanish', 'Hindi', 'Arabic', 'Portuguese', 'French', 'Japanese', 'Swahili'];
const kMusicStyles = ['Pop', 'Hip-hop', 'R&B', 'Rock', 'EDM', 'Lo-fi', 'Jazz', 'Country', 'Gospel', 'Reggaeton', 'Latin pop',
  'Afrobeats', 'Amapiano', 'K-pop', 'J-pop', 'Bollywood', 'Bhangra', 'Sufi', 'Arabic pop', 'Bossa nova', 'Flamenco',
  'Classical', 'Devotional', 'Kids'];
const kMusicVox = ['Duet', 'Female', 'Male', 'Group', 'Choir', 'Child'];
const kMusicMoods = ['Auto', 'Warm', 'Joyful', 'Romantic', 'Energetic', 'Sad', 'Calm', 'Epic', 'Dreamy', 'Devotional'];
const kMusicKinds = ['Song', 'Instrumental', 'Jingle', 'Score'];
const kMusicLens = {'30 s': 30, '1 min': 60, '2 min': 120, '3 min': 180};
const kMusicTempo = {'Auto': 0, 'Slow': 80, 'Medium': 105, 'Fast': 128};
/// One version of a song (Lyria, about $0.08): the price under the box and on every card.
const kSongCredits = 80;
const kSongInr = 7;

int _c4(int n) => math.min(4, math.max(1, n));

String musicPrice(int versions) => '$versions version${versions > 1 ? 's' : ''} · ${versions * kSongCredits} credits';

/// Her words without the console notes that rode after them ("[Web console ...]").
String musicStripNotes(String t) => t.replaceFirst(RegExp(r'(?:\s*\[Web console [^\]\n]*\])+\s*$'), '').trimRight();

// ------------------------------------------------------------------------------------------------ her Song settings
class MusicSettings {
  String tab = 'Song', lang = 'Auto', vox = 'Duet', genre = '', mood = 'Auto', len = '1 min', tempo = 'Auto';
  int versions = 2;
  String keep = '', lyrics = '';

  bool get sung => tab == 'Song';
  int get seconds => kMusicLens[len] ?? 60;
  int get bpm => kMusicTempo[tempo] ?? 0;

  /// The line on the settings button.
  String get summary => '$tab · ${lang == 'Auto' ? 'Auto' : lang} · $versions version${versions > 1 ? 's' : ''}';

  static String _clean(String t) => t.replaceAll('[', '{').replaceAll(']', '}').replaceAll(RegExp(r'\n+'), ' / ');

  /// The note her message carries (the console's mHint, word for word in shape): the Music chat's rules read it.
  String hint({String focus = ''}) {
    final language = lang == 'Auto' ? 'Auto (the language of her words or lyrics)' : lang;
    final style = _clean(genre).isEmpty ? 'auto (you choose from her words)' : _clean(genre);
    final words = sung && lyrics.trim().isNotEmpty
        ? ', her lyrics word for word (part names in braces are part tags, " / " starts a new line): '
            '${_clean(lyrics.trim()).substring(0, math.min(2800, _clean(lyrics.trim()).length))}'
        : '';
    return 'Song settings: kind $tab, language $language${sung ? ', singers ${vox.toLowerCase()}' : ', no singing'}, style $style, '
        'mood ${mood == 'Auto' ? 'auto' : mood.toLowerCase()}, about $seconds seconds, tempo ${bpm > 0 ? 'about $bpm BPM' : 'auto'}, '
        '$versions version${versions > 1 ? 's' : ''}${keep.trim().isNotEmpty ? ', keep out: ${_clean(keep.trim())}' : ''}$words'
        '${focus.isNotEmpty ? ', the song she means: id $focus' : ''}. A new song = create_studio action=song; a change to a song '
        'made here = create_studio action=song_edit.';
  }

  /// The body of a song made straight away (no chat turn): POST /api/create/jobs.
  Map<String, dynamic> body(String brief) {
    final g = tab == 'Jingle' ? 'Jingle${genre.isEmpty ? '' : ', $genre'}' : tab == 'Score' ? 'Film score${genre.isEmpty ? '' : ', $genre'}' : genre;
    final b = brief.trim();
    return {
      'kind': 'song',
      'brief': b.length > 1200 ? b.substring(0, 1200) : b,
      'genre': g.length > 60 ? g.substring(0, 60) : g,
      'language': lang,
      'vocals': sung ? vox.toLowerCase() : 'none',
      'mood': mood == 'Auto' ? '' : mood,
      'bpm': bpm,
      'seconds': seconds,
      'lyrics': sung ? (lyrics.length > 3000 ? lyrics.substring(0, 3000) : lyrics) : '',
      'keep_out': keep,
      'versions': versions,
      'title': b.length > 48 ? b.substring(0, 48) : (b.isEmpty ? 'Hoola song' : b),
    };
  }
}

// ------------------------------------------------------------------------------------------------ a set of versions
class MusicSet {
  MusicSet(this.id, this.created);
  final String id;
  int created;
  final List<Map<String, dynamic>> items = [];
  Map<String, dynamic>? job;
  String edit = '', parent = '';
  num inr = 0;
}

/// Her songs made in this Music chat, grouped by the job that made them (version A, B...), plus the sets still being
/// made or that could not be made. Oldest first.
List<MusicSet> musicSets(CreateStore store, String conv) {
  final sets = <String, MusicSet>{};
  for (final it in store.items) {
    final m = crMap(it['meta']);
    if (it['kind'] != 'song' || conv.isEmpty || crS(m['chat']) != conv) continue;
    final k = crS(m['job']).isEmpty ? crS(it['id']) : crS(m['job']);
    final s = sets.putIfAbsent(k, () => MusicSet(k, crInt(it['created']))
      ..edit = crS(m['edit'])
      ..parent = crS(m['parent']));
    s.items.add(it);
    s.created = math.min(s.created, crInt(it['created']));
    s.inr += (m['inr'] is num) ? m['inr'] as num : 0;
  }
  for (final j in store.jobs.values) {
    if (j['kind'] != 'song' || crS(j['conv']) != conv || conv.isEmpty || sets.containsKey(crS(j['id'])) || j['status'] == 'done') {
      continue;
    }
    sets[crS(j['id'])] = MusicSet(crS(j['id']), crInt(j['created']))..job = j;
  }
  for (final s in sets.values) {
    s.items.sort((a, b) => crS(crMap(a['meta'])['version']).compareTo(crS(crMap(b['meta'])['version'])));
  }
  return sets.values.toList()..sort((a, b) => a.created.compareTo(b.created));
}

/// What a song is, in one line (style, language, length).
String musicLine(Map<String, dynamic> it) {
  final m = crMap(it['meta']);
  final secs = crInt(m['seconds']);
  final parts = <String>[
    if (crS(m['version']).isNotEmpty) 'Version ${crS(m['version'])}',
    if (crS(m['edit']).isNotEmpty) crS(m['edit']),
    if (crS(m['genre']).isNotEmpty) crS(m['genre']),
    if (crS(m['language']).isNotEmpty && crS(m['language']) != 'Auto') crS(m['language']),
    if (secs > 0) musicClock(secs),
  ];
  return parts.join(' · ');
}

String musicClock(int secs) => '${secs ~/ 60}:${(secs % 60).toString().padLeft(2, '0')}';

String musicTitle(Map<String, dynamic> it) => crS(it['title']).replaceFirst(RegExp(r' · [A-D]$'), '');

// ------------------------------------------------------------------------------------------------ one player for the page
/// Plays one song at a time on a page (a second play stops the first).
class MusicPlayer extends ChangeNotifier {
  MusicPlayer(this.app);
  final Santosh app;
  VideoPlayerController? _ctl;
  String id = '';
  bool loading = false;
  bool _gone = false;

  bool playing(String itemId) => id == itemId && (_ctl?.value.isPlaying ?? false);
  Duration get position => _ctl?.value.position ?? Duration.zero;
  Duration get duration => _ctl?.value.duration ?? Duration.zero;
  double frac(String itemId) {
    if (id != itemId) return 0;
    final d = duration.inMilliseconds;
    return d == 0 ? 0 : (position.inMilliseconds / d).clamp(0.0, 1.0);
  }

  Future<void> toggle(BuildContext context, String itemId) async {
    final api = app.api;
    if (api == null || CreateStore.debugData != null) return;
    if (id == itemId && _ctl != null) {
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
    id = itemId;
    loading = true;
    _tell();
    final c = VideoPlayerController.networkUrl(Uri.parse(api.createItemUrl(itemId)), httpHeaders: api.authHeaders);
    try {
      await c.initialize();
    } catch (e) {
      await c.dispose();
      loading = false;
      id = '';
      _tell();
      if (context.mounted) crToast(context, 'This song did not open: ${crError(e)}');
      return;
    }
    if (_gone) {
      await c.dispose();
      return;
    }
    c.addListener(_tell);
    _ctl = c;
    loading = false;
    await c.play();
    _tell();
  }

  Future<void> seekBy(int seconds) async {
    final c = _ctl;
    if (c == null) return;
    final to = c.value.position + Duration(seconds: seconds);
    await c.seekTo(to < Duration.zero ? Duration.zero : (to > c.value.duration ? c.value.duration : to));
  }

  Future<void> seekTo(double frac) async {
    final c = _ctl;
    if (c == null) return;
    await c.seekTo(Duration(milliseconds: (c.value.duration.inMilliseconds * frac).round()));
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

// ------------------------------------------------------------------------------------------------ the Music page
class CreateMusic extends StatefulWidget {
  const CreateMusic({super.key, required this.store, this.brief = ''});
  final CreateStore store;
  final String brief;
  @override
  State<CreateMusic> createState() => _CreateMusicState();
}

class _Up {
  _Up(this.name);
  final String name;
  String fileId = '', error = '';
  bool busy = true;
}

class _CreateMusicState extends State<CreateMusic> {
  late final _q = TextEditingController(text: widget.brief);
  final _scroll = ScrollController();
  final _focusNode = FocusNode();
  final _ms = MusicSettings();
  late final MusicPlayer _player = MusicPlayer(widget.store.app);
  String _conv = '', _title = 'Music chat', _focus = '', _focusTitle = '', _openError = '';
  List<Map<String, dynamic>> _rows = [];
  Map<String, dynamic>? _turn;
  Map<String, dynamic>? _last;   // what she sent last (its body, for "Make the song straight away")
  final List<_Up> _files = [];
  bool _sending = false, _loading = false, _improving = false;
  int _seen = 0;
  Timer? _timer;

  CreateStore get store => widget.store;
  bool get _debug => CreateStore.debugData != null;

  @override
  void initState() {
    super.initState();
    _q.addListener(() => setState(() {}));
    if (store.conf.isEmpty && store.items.isEmpty) unawaited(store.load(quiet: true));
    unawaited(_open());
  }

  @override
  void dispose() {
    _timer?.cancel();
    _q.dispose();
    _scroll.dispose();
    _focusNode.dispose();
    _player.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------- the chat
  Future<void> _open([String? id, String? title]) async {
    if (_debug) {
      final d = crMap(CreateStore.debugData!['music']);
      setState(() {
        _conv = crS(d['conv']).isEmpty ? 'mc-debug' : crS(d['conv']);
        _title = crS(d['title']).isEmpty ? 'Music chat' : crS(d['title']);
        _rows = crList(d['rows']);
        _turn = d['turn'] is Map ? crMap(d['turn']) : null;
      });
      return;
    }
    final api = store.app.api;
    if (api == null) {
      setState(() => _openError = 'Not connected to the server right now');
      return;
    }
    try {
      final c = id == null ? crMap(await api.call('GET', '/api/music/chat')) : {'id': id, 'title': title ?? 'Music chat'};
      if (!mounted) return;
      setState(() {
        _conv = crS(c['id']);
        _title = crS(c['title']).isEmpty ? 'Music chat' : crS(c['title']);
        _rows = [];
        _turn = null;
        _last = null;
        _focus = '';
        _openError = '';
      });
      await _load(first: true);
    } catch (e) {
      if (mounted) setState(() => _openError = 'The music chat could not open. ${crError(e)}');
    }
    _schedule();
  }

  bool get _working {
    if (_sending) return true;
    final st = _turn == null ? '' : crS(_turn!['status']);
    final last = _rows.isEmpty ? null : _rows.last;
    if (st.isNotEmpty) return st == 'working' || st == 'queued';
    return last != null && last['role'] == 'user';
  }

  bool get _songsBeingMade => musicSets(store, _conv).any((s) => s.job != null && s.job!['status'] == 'running');

  void _schedule() {
    _timer?.cancel();
    if (_debug || !mounted) return;
    _timer = Timer(Duration(milliseconds: _working || _songsBeingMade ? 2000 : 8000), () async {
      await _load();
      _schedule();
    });
  }

  Future<void> _load({bool first = false}) async {
    final api = store.app.api;
    if (api == null || _conv.isEmpty || _loading || _debug) return;
    final conv = _conv;
    _loading = true;
    try {
      final last = _rows.isEmpty ? null : _rows.last;
      Map<String, dynamic>? turn = _turn;
      if (first || _sending || _working || (last != null && last['role'] == 'user')) {
        try {
          turn = crMap(await api.call('GET', '/api/conversations/${Uri.encodeComponent(conv)}/result'));
        } catch (_) {}
      }
      final rows = crList(crMap(await api.call('GET', '/api/conversations/${Uri.encodeComponent(conv)}/messages',
          query: {'limit': '200'}))['messages']);
      var finished = false;
      try {
        for (final j in crList(crMap(await api.call('GET', '/api/create/jobs'))['jobs'])) {
          final before = store.jobs[crS(j['id'])];
          if (before != null && before['status'] == 'running' && j['status'] != 'running') finished = true;
          if (before == null && j['status'] == 'done' && crS(j['conv']) == conv) finished = true;
          store.jobs[crS(j['id'])] = j;
        }
      } catch (_) {}
      if (finished || first) await store.reloadItems();
      if (!mounted || conv != _conv) return;
      setState(() {
        _rows = rows;
        _turn = turn;
      });
      _follow();
    } catch (_) {
      // the next tick tries again; nothing she typed is lost
    } finally {
      _loading = false;
    }
  }

  void _follow() {
    final n = _rows.length + musicSets(store, _conv).length;
    if (n == _seen) return;
    _seen = n;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent, duration: HoolaMotion.of(context, HoolaMotion.menu), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _send([String? asked]) async {
    final text = (asked ?? _q.text).trim();
    final api = store.app.api;
    if (_working && !_sending && text.isEmpty) {
      try {
        await api?.call('POST', '/api/conversations/${Uri.encodeComponent(_conv)}/stop');
        if (mounted) crToast(context, 'Stopping.');
      } catch (e) {
        if (mounted) crToast(context, crError(e));
      }
      return;
    }
    if (text.isEmpty) {
      _focusNode.requestFocus();
      crToast(context, 'Describe the song first.');
      return;
    }
    if (_files.any((f) => f.busy)) {
      crToast(context, 'Wait for the files to finish uploading.');
      return;
    }
    if (api == null || _conv.isEmpty) {
      crToast(context, 'Not connected to the server right now.');
      return;
    }
    HapticFeedback.selectionClick();
    final focus = _focus;
    final files = _files.where((f) => f.fileId.isNotEmpty).map((f) => f.fileId).toList();
    final full = '$text\n\n[Web console ${_ms.hint(focus: focus)}]';
    setState(() {
      _sending = true;
      _turn = null;
      _last = {'body': _ms.body(text), 'at': DateTime.now().millisecondsSinceEpoch ~/ 1000, 'edit': asked != null || focus.isNotEmpty};
      _rows = [..._rows, {'id': -1, 'role': 'user', 'text': text, 'at': DateTime.now().toUtc().toIso8601String()}];
      if (asked == null) _q.clear();
      _files.clear();
      _focus = '';
      _focusTitle = '';
    });
    _follow();
    try {
      await api.sendMessage(_conv, full, files: files);
    } catch (e) {
      if (mounted) {
        crToast(context, crError(e));
        setState(() {
          _rows = _rows.where((r) => r['id'] != -1).toList();
          if (asked == null) _q.text = text;
        });
      }
    }
    if (mounted) setState(() => _sending = false);
    await _load();
    _schedule();
  }

  /// A song made without a chat turn ("More like this", "Make the song now", "Try again"): her tap, the price on it.
  Future<void> _make(Map<String, dynamic> body) async {
    final api = store.app.api;
    final ready = store.conf['ready'];
    if (ready is Map && ready['song'] == false) {
      final need = store.conf['need'];
      crToast(context, need is Map && crS(need['song']).isNotEmpty ? crS(need['song']) : 'The music engine is not set up on the server.');
      return;
    }
    if (api == null) return;
    try {
      final j = crMap(await api.call('POST', '/api/create/jobs', body: {...body, 'conversation_id': _conv}));
      store.jobs[crS(j['id'])] = j;
      final n = _c4(crInt(body['versions']));
      if (mounted) {
        setState(() {});
        crToast(context, 'Making ${musicPrice(n)}.');
      }
      _follow();
      _schedule();
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
  }

  void _more(Map<String, dynamic> it) {
    final m = crMap(it['meta']);
    final job = crS(m['job']);
    final n = job.isEmpty ? 1 : store.items.where((x) => crS(crMap(x['meta'])['job']) == job).length;
    final brief = crS(m['brief']).isEmpty ? musicTitle(it) : crS(m['brief']);
    _make({
      'kind': 'song', 'brief': brief.length > 1200 ? brief.substring(0, 1200) : brief, 'genre': crS(m['genre']),
      'language': crS(m['language']).isEmpty ? 'Auto' : crS(m['language']), 'vocals': crS(m['vocals']).isEmpty ? 'duet' : crS(m['vocals']),
      'mood': crS(m['mood']), 'bpm': crInt(m['bpm']), 'seconds': crInt(m['asked_seconds']), 'lyrics': crS(m['lyrics']),
      'keep_out': crS(m['keep_out']), 'versions': _c4(n), 'title': musicTitle(it),
    });
  }

  Future<void> _addFiles() async {
    if (_conv.isEmpty || _debug) return;
    final r = await FilePicker.platform.pickFiles(allowMultiple: true, withData: true,
        type: FileType.custom, allowedExtensions: const ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'mp4', 'mov', 'txt', 'pdf', 'docx']);
    if (r == null) return;
    final api = store.app.api;
    for (final f in r.files.take(math.max(0, 10 - _files.length))) {
      final up = _Up(f.name);
      setState(() => _files.add(up));
      final bytes = f.bytes;
      if (bytes == null || api == null) {
        setState(() {
          up.busy = false;
          up.error = 'Could not read';
        });
        continue;
      }
      if (bytes.length > 30 * 1024 * 1024) {
        setState(() {
          up.busy = false;
          up.error = 'Over 30 MB';
        });
        continue;
      }
      try {
        final res = await api.chatFile(_conv, f.name, bytes);
        up.fileId = crS(res['file_id']);
      } catch (e) {
        up.error = 'Not uploaded';
        if (mounted) crToast(context, '${f.name}: ${crError(e)}');
      }
      if (mounted) setState(() => up.busy = false);
    }
  }

  Future<void> _improve() async {
    final text = _q.text.trim();
    final api = store.app.api;
    if (text.length < 4 || api == null) {
      crToast(context, 'Write a few words first, then Improve makes them clearer.');
      return;
    }
    setState(() => _improving = true);
    String better = '';
    try {
      final r = crMap(await api.call('POST', '/api/prompting/understand', body: {'text': text, 'section': 'music'},
          timeout: const Duration(seconds: 60)));
      better = crS(crMap(r['out'])['prompt']).trim();
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (!mounted) return;
    setState(() => _improving = false);
    if (better.isEmpty || better == text) {
      if (better == text) crToast(context, 'Your words are already clear.');
      return;
    }
    final use = await showModalBottomSheet<bool>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) {
        final c = HoolaColors.of(ctx);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('A clearer way to say it', style: HoolaType.heading(c)),
              const SizedBox(height: 6),
              Text('Your words stay as they are unless you tap Use this.', style: HoolaType.small(c)),
              const SizedBox(height: 14),
              ConstrainedBox(
                constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * .45),
                child: SingleChildScrollView(child: Text(better, style: HoolaType.reply(c))),
              ),
              const SizedBox(height: 16),
              Row(children: [
                Expanded(child: CrQuiet(label: 'Keep mine', height: 48, onTap: () => Navigator.of(ctx).pop(false))),
                const SizedBox(width: 10),
                Expanded(child: CrHueScope(hue: CrHue.song, child: CrMain(label: 'Use this', height: 48, onTap: () => Navigator.of(ctx).pop(true)))),
              ]),
            ]),
          ),
        );
      },
    );
    if (use == true && mounted) _q.text = better;
  }

  Future<void> _history() async {
    final api = store.app.api;
    List<Map<String, dynamic>> cs = [];
    if (api != null && !_debug) {
      try {
        cs = crList(crMap(await api.call('GET', '/api/music/chats'))['chats']);
      } catch (e) {
        if (mounted) crToast(context, crError(e));
        return;
      }
    }
    if (!mounted) return;
    final pick = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => MusicChatsSheet(chats: cs, current: _conv),
    );
    if (pick == null || !mounted) return;
    if (pick == '+new') {
      try {
        final c = crMap(await api!.call('POST', '/api/music/chat/new'));
        await _open(crS(c['id']), crS(c['title']));
      } catch (e) {
        if (mounted) crToast(context, crError(e));
      }
      return;
    }
    final c = cs.firstWhere((x) => crS(x['id']) == pick, orElse: () => const {});
    await _open(pick, crS(c['title']));
  }

  Future<void> _settings() async {
    final api = store.app.api;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => CrHueScope(
        hue: CrHue.song,
        child: MusicSettingsSheet(settings: _ms, store: store, brief: _q.text, canWrite: api != null && !_debug),
      ),
    );
    if (mounted) setState(() {});
  }

  void _changeThis(Map<String, dynamic> it) {
    setState(() {
      _focus = crS(it['id']);
      _focusTitle = musicTitle(it) + (crS(crMap(it['meta'])['version']).isEmpty ? '' : ' · ${crS(crMap(it['meta'])['version'])}');
    });
    _focusNode.requestFocus();
  }

  Future<void> _openSong(Map<String, dynamic> it, List<Map<String, dynamic>> versions) async {
    final ask = await Navigator.of(context).push<(String, String)>(MaterialPageRoute(
        builder: (_) => MusicPlayerPage(store: store, player: _player, item: it, versions: versions)));
    if (ask != null && mounted) {
      setState(() => _focus = ask.$2);
      await _send(ask.$1);
    }
  }

  Future<void> _delete(Map<String, dynamic> it, {bool undo = false}) async {
    final ok = await musicConfirmDelete(context, it, undo: undo);
    if (ok != true) return;
    try {
      await store.delete(crS(it['id']));
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
  }

  Future<void> _itemMenu(Map<String, dynamic> it, List<Map<String, dynamic>> versions) async {
    final pick = await crPick(context, musicTitle(it), const ['Open', 'Change this song', 'Save or share', 'Delete'], '');
    if (!mounted || pick == null) return;
    switch (pick) {
      case 'Open':
        await _openSong(it, versions);
      case 'Change this song':
        _changeThis(it);
      case 'Save or share':
        await crShareItem(context, store.app, it);
      case 'Delete':
        await _delete(it);
    }
  }

  // ---------------------------------------------------------------- the screen
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrHueScope(
      hue: CrHue.song,
      child: ListenableBuilder(
        listenable: Listenable.merge([store, _player]),
        builder: (context, _) {
          final sets = musicSets(store, _conv);
          final started = _rows.any((r) => r['role'] == 'user') || sets.isNotEmpty;
          return Scaffold(
            backgroundColor: c.bg,
            body: SafeArea(
              child: Column(children: [
                _top(c),
                Expanded(child: started ? _thread(c, sets) : _start(c)),
                _composer(c),
              ]),
            ),
          );
        },
      ),
    );
  }

  Widget _top(HoolaColors c) => SizedBox(
        height: 60,
        child: Row(children: [
          const SizedBox(width: 4),
          CrRoundButton(glyph: CrGlyph.back, label: 'Back', onTap: () => Navigator.of(context).maybePop()),
          Expanded(
            child: Semantics(
              header: true,
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text(_rows.any((r) => r['role'] == 'user') ? _title : 'Music', maxLines: 1, overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center, style: HoolaType.title(c)),
                if (_rows.any((r) => r['role'] == 'user'))
                  Text('Music chat', style: HoolaType.small(c).copyWith(fontSize: 12)),
              ]),
            ),
          ),
          CrRoundButton(glyph: CrGlyph.folder, label: 'Your songs', onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
              builder: (_) => MusicLibraryPage(store: store, player: _player, onAsk: (t, id) {
                setState(() => _focus = id);
                _send(t);
              })))),
          CrRoundButton(glyph: CrGlyph.clock, label: 'Earlier Music chats', onTap: _history),
          const SizedBox(width: 4),
        ]),
      );

  Widget _start(HoolaColors c) {
    const tries = [
      ('A birthday song for Lucía, in Spanish', 'Pop · claps · 1 min', 'A happy birthday song in Spanish for my daughter Lucía, she turns 6, with hand claps'),
      ('A 30 second jingle for my bakery', 'Jingle · group · 30 s', 'A 30 second happy jingle for my neighbourhood bakery called Sunny Bakes'),
      ('A calm lo-fi beat to study, no voice', 'Instrumental · 2 min', 'A calm lo-fi study beat with soft keys and rain, no singing'),
      ('Hindi verses, an English chorus', 'Duet · indie pop', 'A duet with Hindi verses and an English chorus about a long-distance friendship'),
    ];
    return ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 12), children: [
      const SizedBox(height: 12),
      const Center(child: HoolaMark(size: 40)),
      const SizedBox(height: 14),
      Text('What shall we make?', textAlign: TextAlign.center, style: HoolaType.replyH1(c).copyWith(fontSize: 28, fontWeight: FontWeight.w400)),
      const SizedBox(height: 8),
      Text('Any language. A song, an instrumental, a jingle or a film score; your own lyrics or mine. You get two versions to pick from.',
          textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 15)),
      if (_openError.isNotEmpty) ...[const SizedBox(height: 14), CrNote(_openError, glyph: CrGlyph.info)],
      const SizedBox(height: 22),
      Text('Try one', style: HoolaType.label(c)),
      const SizedBox(height: 8),
      LayoutBuilder(builder: (context, box) {
        final w = (box.maxWidth - 8) / 2;
        return Wrap(spacing: 8, runSpacing: 8, children: [
          for (final t in tries)
            SizedBox(
              width: w,
              child: Semantics(
                button: true,
                label: 'Try: ${t.$1}',
                excludeSemantics: true,
                child: CrCard(
                  padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                  onTap: () {
                    _q.text = t.$3;
                    _focusNode.requestFocus();
                  },
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(minHeight: 72),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(t.$1, style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500, height: 1.35)),
                      const SizedBox(height: 4),
                      Text(t.$2, style: HoolaType.small(c).copyWith(fontSize: 12)),
                    ]),
                  ),
                ),
              ),
            ),
        ]);
      }),
    ]);
  }

  Widget _thread(HoolaColors c, List<MusicSet> sets) {
    int epoch(Map<String, dynamic> r) {
      final s = crS(r['at']);
      final t = DateTime.tryParse(s.endsWith('Z') || RegExp(r'[+-]\d\d:\d\d$').hasMatch(s) ? s : '${s}Z');
      return t == null ? 0 : t.millisecondsSinceEpoch ~/ 1000;
    }

    // a set sits after the reply of the turn that made it (or after her message when there is none)
    final after = <int, List<MusicSet>>{};
    for (final s in sets) {
      var i = -1;
      for (var j = 0; j < _rows.length; j++) {
        if (epoch(_rows[j]) <= s.created + 1) i = j;
      }
      if (i >= 0 && _rows[i]['role'] == 'user' && i + 1 < _rows.length && _rows[i + 1]['role'] != 'user') i++;
      after.putIfAbsent(i, () => []).add(s);
    }
    final kids = <Widget>[for (final s in after[-1] ?? const <MusicSet>[]) _setCard(c, s)];
    for (var j = 0; j < _rows.length; j++) {
      final r = _rows[j];
      final text = crS(r['text']);
      if (r['role'] == 'user') {
        final shown = musicStripNotes(text);
        if (shown.isNotEmpty) kids.add(_her(c, shown));
      } else if (text.trim().isNotEmpty && j > 0) {
        kids.add(_hoola(c, text.trim()));
      }
      for (final s in after[j] ?? const <MusicSet>[]) {
        kids.add(_setCard(c, s));
      }
    }
    if (_working) kids.add(_workRow(c));
    final fail = _failCard(c, sets);
    if (fail != null) kids.add(fail);
    return ListView.separated(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      itemCount: kids.length,
      separatorBuilder: (_, __) => const SizedBox(height: 14),
      itemBuilder: (_, i) => kids[i],
    );
  }

  Widget _her(HoolaColors c, String text) => Align(
        alignment: Alignment.centerRight,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * .8),
          child: Container(
            padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
            decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(18)),
            child: SelectableText(text, style: HoolaType.body(c)),
          ),
        ),
      );

  Widget _hoola(HoolaColors c, String text) => Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Padding(padding: EdgeInsets.only(top: 2), child: HoolaMark(size: 22, animate: false)),
        const SizedBox(width: 10),
        Expanded(child: SelectableText(text, style: HoolaType.reply(c))),
      ]);

  Widget _workRow(HoolaColors c) {
    final line = _turn != null && crS(_turn!['line']).isNotEmpty ? crS(_turn!['line']) : 'Listening to your words…';
    return Semantics(
      liveRegion: true,
      label: line,
      child: Row(children: [
        const HoolaMark(size: 22),
        const SizedBox(width: 10),
        Expanded(child: Text(line, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 13, color: c.ink2))),
      ]),
    );
  }

  /// Hoola could not answer: the same song can still be made straight away from her words and settings.
  Widget? _failCard(HoolaColors c, List<MusicSet> sets) {
    if (_working || _rows.isEmpty) return null;
    final st = _turn == null ? '' : crS(_turn!['status']);
    if (!RegExp('fail|error|stuck').hasMatch(st)) return null;
    final since = crInt(_last?['at']);
    if (sets.any((s) => s.created >= since - 1 && since > 0)) return null;
    if (_last != null && _last!['edit'] == true) return null;
    final hers = _rows.lastWhere((r) => r['role'] == 'user', orElse: () => const {});
    final body = _last != null ? crMap(_last!['body']) : _ms.body(musicStripNotes(crS(hers['text'])));
    if (crS(body['brief']).isEmpty) return null;
    final n = _c4(crInt(body['versions']));
    return Semantics(
      container: true,
      explicitChildNodes: true,
      child: Padding(
      padding: const EdgeInsets.only(left: 32),
      child: Container(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
        decoration: BoxDecoration(color: c.warnSoft, borderRadius: BorderRadius.circular(16), border: Border.all(color: c.line)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Hoola can’t answer right now', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text('Your words and Song settings are ready. Make the song straight away, without the chat.',
              style: HoolaType.small(c).copyWith(color: c.ink2)),
          const SizedBox(height: 10),
          CrMain(label: 'Make the song now · ${n * kSongCredits} credits', height: 48, glyph: CrGlyph.music, onTap: () {
            _last = {...?_last, 'edit': true};
            _make(body);
          }),
        ]),
      ),
    ));
  }

  Widget _setCard(HoolaColors c, MusicSet s) {
    final j = s.job;
    // its own semantics node, so a lone button inside (Try again) stays a button and never swallows the card's words
    Widget card(List<Widget> kids) => Semantics(
        container: true,
        explicitChildNodes: true,
        child: Padding(
          padding: const EdgeInsets.only(left: 32),
          child: CrCard(padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: kids)),
        ));
    if (j != null && j['status'] == 'running') {
      final n = _c4(crInt(j['count']));
      return Semantics(
        liveRegion: true,
        child: card([
          Row(children: [
            SizedBox(width: 36, height: 36, child: CircularProgressIndicator(strokeWidth: 2.4, color: CrHue.song.b)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Making $n version${n > 1 ? 's' : ''}${crS(j['step']).isEmpty ? '' : ' · ${crS(j['step'])}'}',
                    style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                Text('About a minute a version · ${n * kSongCredits} credits', style: HoolaType.small(c).copyWith(fontSize: 12)),
              ]),
            ),
          ]),
        ]),
      );
    }
    if (j != null) {
      final title = crS(j['title']);
      return card([
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(color: c.badSoft, shape: BoxShape.circle),
            child: Center(child: CrIcon(CrGlyph.info, size: 16, color: c.bad)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Could not be made', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
              Text(crS(j['error']).isEmpty ? 'It did not work this time. Nothing was charged for it.' : '${crS(j['error'])} Nothing was charged for it.',
                  style: HoolaType.small(c).copyWith(fontSize: 12)),
            ]),
          ),
        ]),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerRight,
          child: Semantics(container: true, child: CrSmall(label: 'Try again', glyph: CrGlyph.refresh, onTap: () {
            store.dismiss(crS(j['id']));
            store.jobs.remove(crS(j['id']));
            final b = (_last != null ? crMap(_last!['body']) : _ms.body(title));
            _make({...b, 'brief': crS(b['brief']).isEmpty ? title : b['brief'], 'versions': _c4(crInt(j['count']))});
          })),
        ),
      ]);
    }
    if (s.items.isEmpty) return const SizedBox.shrink();
    final first = s.items.first;
    final from = s.parent.isEmpty ? null : store.items.cast<Map<String, dynamic>?>().firstWhere((x) => crS(x?['id']) == s.parent, orElse: () => null);
    final m = crMap(first['meta']);
    final meta = s.parent.isNotEmpty
        ? 'Changed: ${s.edit}${from == null ? '' : ' · from ${musicTitle(from)}${crS(crMap(from['meta'])['version']).isEmpty ? '' : ' ${crS(crMap(from['meta'])['version'])}'}'} · free'
        : [
            if (crS(m['genre']).isNotEmpty) crS(m['genre']),
            if (crS(m['language']).isNotEmpty && crS(m['language']) != 'Auto') crS(m['language']),
            if (crS(m['vocals']).isNotEmpty) crS(m['vocals']),
            '${s.items.length} version${s.items.length > 1 ? 's' : ''}',
          ].join(' · ');
    return card([
      Row(children: [
        Container(
          width: 40, height: 40,
          decoration: BoxDecoration(gradient: CrHue.song.gradient, borderRadius: BorderRadius.circular(10)),
          child: const Center(child: CrIcon(CrGlyph.music, size: 20, color: CreateHues.onHue)),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(musicTitle(first), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
            Text(meta, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
        ),
      ]),
      const SizedBox(height: 6),
      for (final it in s.items) _versionRow(c, it, s.items),
      const SizedBox(height: 6),
      Wrap(spacing: 6, runSpacing: 6, children: [
        CrSmall(label: 'Reel cut', glyph: CrGlyph.cut, onTap: () {
          setState(() => _focus = crS(first['id']));
          _send('Make a 30 second reel cut of ${crS(first['title'])}: start on the chorus and fade out the end');
        }),
        CrSmall(label: 'Fade the end', glyph: CrGlyph.minus, onTap: () {
          setState(() => _focus = crS(first['id']));
          _send('Fade out the last 3 seconds of ${crS(first['title'])}');
        }),
        if (s.parent.isEmpty)
          CrSmall(label: 'More like this', glyph: CrGlyph.spark, onTap: () => _more(first))
        else
          CrSmall(label: 'Undo', glyph: CrGlyph.back, onTap: () => _delete(first, undo: true)),
      ]),
      const SizedBox(height: 6),
      Text('Made by AI · marked in the file', style: HoolaType.small(c).copyWith(fontSize: 12)),
    ]);
  }

  Widget _versionRow(HoolaColors c, Map<String, dynamic> it, List<Map<String, dynamic>> versions) {
    final id = crS(it['id']);
    final m = crMap(it['meta']);
    final v = crS(m['version']);
    final name = v.isNotEmpty ? 'Version $v' : (crS(m['edit']).isNotEmpty ? crS(m['edit']) : musicTitle(it));
    final playing = _player.playing(id);
    final secs = crInt(m['seconds']);
    final pos = _player.id == id ? _player.position : Duration.zero;
    return Row(children: [
      MusicPlayButton(
        label: '${playing ? 'Pause' : 'Play'} ${musicTitle(it)}${v.isEmpty ? '' : ' version $v'}',
        playing: playing,
        loading: _player.loading && _player.id == id,
        onTap: () => _player.toggle(context, id),
      ),
      const SizedBox(width: 6),
      Expanded(
        child: Semantics(
          button: true,
          label: 'Open $name',
          excludeSemantics: true,
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => _openSong(it, versions),
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48),
              child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(name, style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w600)),
                const SizedBox(height: 3),
                MusicWave(seed: id, frac: _player.frac(id), height: 18),
              ]),
            ),
          ),
        ),
      ),
      const SizedBox(width: 8),
      Text(_player.id == id && pos > Duration.zero ? musicClock(pos.inSeconds) : (secs > 0 ? musicClock(secs) : ''),
          style: HoolaType.small(c).copyWith(fontSize: 12, fontFeatures: const [FontFeature.tabularFigures()])),
      CrRoundButton(glyph: CrGlyph.layers, label: 'More for $name', size: 36, onTap: () => _itemMenu(it, versions)),
    ]);
  }

  Widget _composer(HoolaColors c) {
    final working = _working && !_sending;
    final typed = _q.text.trim().isNotEmpty;
    final bottom = MediaQuery.viewInsetsOf(context).bottom > 0 ? 8.0 : 12.0;
    final price = _focus.isNotEmpty
        ? 'A change to a made song is free and makes a new version'
        : '${musicPrice(_ms.versions)} · made when you send';
    return Padding(
      padding: EdgeInsets.fromLTRB(12, 6, 12, bottom),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Container(
          padding: const EdgeInsets.fromLTRB(14, 2, 8, 6),
          decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(22), border: Border.all(color: c.lineStrong)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            if (_focusTitle.isNotEmpty || _files.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Wrap(spacing: 6, runSpacing: 6, children: [
                  if (_focusTitle.isNotEmpty)
                    _trayChip(c, 'Changing: $_focusTitle', () => setState(() {
                          _focus = '';
                          _focusTitle = '';
                        })),
                  for (final f in _files)
                    _trayChip(c, f.busy ? '${f.name} · uploading' : (f.error.isEmpty ? f.name : '${f.name} · ${f.error}'),
                        () => setState(() => _files.remove(f))),
                ]),
              ),
            TextField(
              controller: _q,
              focusNode: _focusNode,
              minLines: 1,
              maxLines: 5,
              textCapitalization: TextCapitalization.sentences,
              style: HoolaType.bodyLarge(c),
              decoration: InputDecoration(
                hintText: _rows.any((r) => r['role'] == 'user') ? 'Ask for a change: shorter, a fade, louder…' : 'Tell Hoola the song you want…',
                hintStyle: HoolaType.bodyLarge(c).copyWith(color: c.ink3),
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                filled: false,
                isDense: true,
                // 48 dp of tap room even on one line (the tap-target rule)
                contentPadding: const EdgeInsets.symmetric(vertical: 13),
              ),
            ),
            Row(children: [
              CrRoundButton(glyph: CrGlyph.plus, label: 'Add a file or a voice note', size: 36, onTap: _addFiles),
              Expanded(
                child: Align(
                alignment: Alignment.centerLeft,
                child: Semantics(
                  button: true,
                  label: 'Song settings: ${_ms.summary}',
                  excludeSemantics: true,
                  child: crTap48(_settings, Container(
                    height: 36,
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    decoration: BoxDecoration(color: crWash(c), borderRadius: BorderRadius.circular(18)),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      CrIcon(CrGlyph.layers, size: 14, color: c.ink2),
                      const SizedBox(width: 6),
                      Flexible(child: Text(_ms.summary, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500))),
                    ]),
                  )),
                ),
              )),
              Semantics(
                button: true,
                label: 'Improve my words',
                excludeSemantics: true,
                child: crTap48(_improving ? null : _improve, Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                  child: _improving
                      ? SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 1.8, color: c.accent))
                      : CrIcon(CrGlyph.wand, size: 20, color: c.accent),
                )),
              ),
              _sendButton(c, working: working, on: typed || working),
            ]),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 6, 8, 0),
          child: Text(price, style: HoolaType.small(c).copyWith(fontSize: 12)),
        ),
      ]),
    );
  }

  Widget _trayChip(HoolaColors c, String text, VoidCallback onRemove) => Semantics(
        button: true,
        label: 'Remove $text',
        excludeSemantics: true,
        child: crTap48(onRemove, Container(
          height: 32,
          padding: const EdgeInsets.fromLTRB(10, 0, 8, 0),
          decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(10)),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            ConstrainedBox(constraints: const BoxConstraints(maxWidth: 220),
                child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12, color: c.ink))),
            const SizedBox(width: 6),
            CrIcon(CrGlyph.minus, size: 12, color: c.ink2),
          ]),
        )),
      );

  Widget _sendButton(HoolaColors c, {required bool working, required bool on}) => Semantics(
        button: true,
        label: working ? 'Stop' : 'Send',
        excludeSemantics: true,
        child: crTap48(on ? () => _send() : null, Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(color: on ? c.pill : c.lineStrong, shape: BoxShape.circle),
          child: Center(
            child: working
                ? Container(width: 11, height: 11, decoration: BoxDecoration(color: c.onPill, borderRadius: BorderRadius.circular(2)))
                : Icon(Icons.arrow_upward_rounded, size: 18, color: c.onPill),
          ),
        )),
      );
}

// ------------------------------------------------------------------------------------------------ small shared parts
/// A round play / pause button for one song (48 dp of tap room).
class MusicPlayButton extends StatelessWidget {
  const MusicPlayButton({super.key, required this.label, required this.playing, required this.onTap, this.loading = false,
      this.size = 36, this.onDark = false});
  final String label;
  final bool playing, loading, onDark;
  final VoidCallback onTap;
  final double size;
  @override
  Widget build(BuildContext context) {
    final c = onDark ? HoolaColors.darkSet : HoolaColors.of(context);
    final bg = onDark ? c.ink : c.pill;
    final fg = onDark ? c.bg : c.onPill;
    return Semantics(
      button: true,
      label: label,
      excludeSemantics: true,
      child: crTap48(onTap, Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: bg, shape: BoxShape.circle),
        child: Center(
          child: loading
              ? SizedBox(width: size * .4, height: size * .4, child: CircularProgressIndicator(strokeWidth: 2, color: fg))
              : playing
                  ? Row(mainAxisSize: MainAxisSize.min, children: [
                      Container(width: size * .1, height: size * .36, decoration: BoxDecoration(color: fg, borderRadius: BorderRadius.circular(2))),
                      SizedBox(width: size * .1),
                      Container(width: size * .1, height: size * .36, decoration: BoxDecoration(color: fg, borderRadius: BorderRadius.circular(2))),
                    ])
                  : CrIcon(CrGlyph.play, size: size * .36, color: fg),
        ),
      )),
    );
  }
}

/// The song's sound as bars (drawn from its id, not its real wave): played bars in the song colours.
class MusicWave extends StatelessWidget {
  const MusicWave({super.key, required this.seed, required this.frac, this.height = 24, this.off});
  final String seed;
  final double frac, height;
  final Color? off;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return ExcludeSemantics(
      child: SizedBox(
        height: height,
        width: double.infinity,
        child: CustomPaint(painter: _WaveBars(seed, frac, off ?? crWash(c).withOpacity(.9))),
      ),
    );
  }
}

class _WaveBars extends CustomPainter {
  _WaveBars(this.seed, this.frac, this.off);
  final String seed;
  final double frac;
  final Color off;
  @override
  void paint(Canvas canvas, Size size) {
    final n = math.max(12, (size.width / 6).floor());
    final r = math.Random(seed.codeUnits.fold<int>(7, (a, b) => a * 31 + b) & 0x7fffffff);
    final w = size.width / n;
    for (var i = 0; i < n; i++) {
      final env = math.sin(math.pi * (i + .5) / n);
      final h = math.max(3.0, size.height * (.25 + .75 * r.nextDouble()) * (.4 + .6 * env));
      final played = frac > 0 && (i + .5) / n <= frac;
      final p = Paint()..color = played ? Color.lerp(CrHue.song.a, CrHue.song.b, i / n)! : off;
      canvas.drawRRect(RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(w * (i + .5), size.height / 2), width: w * .5, height: h),
          const Radius.circular(2)), p);
    }
  }

  @override
  bool shouldRepaint(_WaveBars o) => o.frac != frac || o.seed != seed || o.off != off;
}

Future<bool?> musicConfirmDelete(BuildContext context, Map<String, dynamic> it, {bool undo = false}) => showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(undo ? 'Undo this change?' : 'Delete this song?'),
        content: Text(undo
            ? 'This removes ${musicTitle(it)} (${crS(crMap(it['meta'])['edit'])}). The version it came from stays.'
            : 'It is removed from Your songs and from this chat. This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Keep')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(undo ? 'Undo' : 'Delete')),
        ],
      ),
    );

// ------------------------------------------------------------------------------------------------ Song settings
class MusicSettingsSheet extends StatefulWidget {
  const MusicSettingsSheet({super.key, required this.settings, required this.store, required this.brief, this.canWrite = true});
  final MusicSettings settings;
  final CreateStore store;
  final String brief;
  final bool canWrite;
  @override
  State<MusicSettingsSheet> createState() => _MusicSettingsSheetState();
}

class _MusicSettingsSheetState extends State<MusicSettingsSheet> {
  MusicSettings get s => widget.settings;
  late final _keep = TextEditingController(text: s.keep);
  late final _lyrics = TextEditingController(text: s.lyrics);
  bool _writing = false;

  @override
  void initState() {
    super.initState();
    // a sheet swiped away keeps what she typed (Done is not the only way out)
    _keep.addListener(() => s.keep = _keep.text.trim());
    _lyrics.addListener(() => s.lyrics = _lyrics.text);
  }

  @override
  void dispose() {
    _keep.dispose();
    _lyrics.dispose();
    super.dispose();
  }

  void _put(VoidCallback f) => setState(f);

  void _tag(String t) {
    final v = _lyrics.text;
    final at = _lyrics.selection.isValid ? _lyrics.selection.start : v.length;
    final pre = at > 0 && !v.substring(0, at).endsWith('\n') ? '\n' : '';
    final ins = '$pre[$t]\n';
    _lyrics.value = TextEditingValue(text: v.replaceRange(at, at, ins), selection: TextSelection.collapsed(offset: at + ins.length));
    s.lyrics = _lyrics.text;
    setState(() {});
  }

  Future<void> _write() async {
    final idea = widget.brief.trim();
    if (idea.length < 4) {
      crToast(context, 'Describe the song in the box first, then Hoola writes its words.');
      return;
    }
    setState(() => _writing = true);
    try {
      final r = await widget.store.write({
        'kind': 'lyrics', 'brief': idea, 'genre': s.genre, 'language': s.lang == 'Auto' ? '' : s.lang,
        'mood': s.mood == 'Auto' ? '' : s.mood,
      });
      _lyrics.text = crS(r['text']);
      s.lyrics = _lyrics.text;
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _writing = false);
  }

  Future<void> _language() async {
    final v = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => MusicLanguageSheet(current: s.lang),
    );
    if (v != null) _put(() => s.lang = v);
  }

  Future<void> _style() async {
    final v = await crPick(context, 'Style', ['Auto', ...kMusicStyles], s.genre.isEmpty ? 'Auto' : s.genre,
        notes: const {'Auto': 'Hoola picks from your words'});
    if (v != null) _put(() => s.genre = v == 'Auto' ? '' : v);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final shownStyles = ['Auto', 'Pop', 'Reggaeton', 'Afrobeats', 'K-pop', 'Bollywood'];
    final styleNow = s.genre.isEmpty ? 'Auto' : s.genre;
    if (!shownStyles.contains(styleNow)) shownStyles.add(styleNow);
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * .88),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 8, 4),
              child: Row(children: [
                Expanded(child: Semantics(header: true, child: Text('Song settings', style: HoolaType.heading(c)))),
                Semantics(
                  button: true,
                  label: 'Start again with the usual settings',
                  excludeSemantics: true,
                  child: crTap48(() => _put(() {
                        final d = MusicSettings();
                        s
                          ..tab = d.tab ..lang = d.lang ..vox = d.vox ..genre = d.genre ..mood = d.mood
                          ..len = d.len ..tempo = d.tempo ..versions = d.versions ..keep = '' ..lyrics = '';
                        _keep.clear();
                        _lyrics.clear();
                      }), Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Text('Reset', style: HoolaType.body(c).copyWith(color: c.accent, fontWeight: FontWeight.w500)),
                  )),
                ),
              ]),
            ),
            Flexible(
              child: ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(20, 4, 20, 12), children: [
                const CrLabel('What'),
                CrSegment(options: kMusicKinds, picked: s.tab, onPick: (v) => _put(() => s.tab = v)),
                const SizedBox(height: 16),
                const CrLabel('Language'),
                Semantics(
                  button: true,
                  label: 'Language: ${s.lang == 'Auto' ? 'Auto, from your words' : s.lang}',
                  excludeSemantics: true,
                  child: CrCard(
                    padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
                    onTap: _language,
                    child: Row(children: [
                      Expanded(
                        child: Text.rich(TextSpan(children: [
                          TextSpan(text: s.lang, style: HoolaType.body(c)),
                          if (s.lang == 'Auto') TextSpan(text: ' · from your words or lyrics', style: HoolaType.body(c).copyWith(color: c.ink3)),
                        ])),
                      ),
                      CrIcon(CrGlyph.chevron, size: 16, color: c.ink3),
                    ]),
                  ),
                ),
                if (s.sung) ...[
                  const SizedBox(height: 16),
                  const CrLabel('Singers'),
                  CrChips(options: kMusicVox, picked: s.vox, onPick: (v) => _put(() => s.vox = v)),
                ],
                const SizedBox(height: 16),
                const CrLabel('Style', note: 'from every region'),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  for (final o in shownStyles) CrChip(label: o, on: o == styleNow, onTap: () => _put(() => s.genre = o == 'Auto' ? '' : o)),
                  CrChip(label: 'More…', on: false, onTap: _style),
                ]),
                const SizedBox(height: 16),
                CrSettings([CrSetting('Mood', s.mood, kMusicMoods, (v) => _put(() => s.mood = v))]),
                const SizedBox(height: 16),
                const CrLabel('Length'),
                CrSegment(options: kMusicLens.keys.toList(), picked: s.len, onPick: (v) => _put(() => s.len = v)),
                const SizedBox(height: 16),
                const CrLabel('Tempo'),
                CrSegment(options: kMusicTempo.keys.toList(), picked: s.tempo, onPick: (v) => _put(() => s.tempo = v)),
                const SizedBox(height: 16),
                CrLabel('Versions', note: '$kSongCredits credits each'),
                CrSegment(options: const ['1', '2', '4'], picked: '${s.versions}', onPick: (v) => _put(() => s.versions = int.parse(v))),
                const SizedBox(height: 16),
                CrTextCard(
                  title: 'Keep out',
                  controller: _keep,
                  max: 200,
                  lines: 1,
                  hint: 'Anything the song must not have: drums, English words…',
                ),
                if (s.sung) ...[
                  const SizedBox(height: 16),
                  CrTextCard(
                    title: 'My lyrics',
                    controller: _lyrics,
                    max: 3000,
                    lines: 5,
                    serif: true,
                    hint: 'Leave empty and Hoola writes the words, or paste yours. Add parts with the buttons below.',
                    action: widget.canWrite
                        ? CrSmall(label: 'Write with Hoola', glyph: CrGlyph.pen, busy: _writing, onTap: _write)
                        : null,
                  ),
                  const SizedBox(height: 8),
                  Wrap(spacing: 6, runSpacing: 6, children: [
                    for (final t in const ['Intro', 'Verse 1', 'Chorus', 'Verse 2', 'Bridge', 'Outro'])
                      CrSmall(label: '+ $t', glyph: CrGlyph.plus, onTap: () => _tag(t)),
                  ]),
                ],
              ]),
            ),
            Container(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
              decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
              child: Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                    Text(musicPrice(s.versions), style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                    Text('About ${crRupees(s.versions * kSongInr)} · made when you send', style: HoolaType.small(c).copyWith(fontSize: 12)),
                  ]),
                ),
                SizedBox(
                  width: 120,
                  child: CrMain(label: 'Done', height: 48, onTap: () {
                    s
                      ..keep = _keep.text.trim()
                      ..lyrics = _lyrics.text;
                    Navigator.of(context).pop();
                  }),
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ the language sheet
class MusicLanguageSheet extends StatefulWidget {
  const MusicLanguageSheet({super.key, required this.current});
  final String current;
  @override
  State<MusicLanguageSheet> createState() => _MusicLanguageSheetState();
}

class _MusicLanguageSheetState extends State<MusicLanguageSheet> {
  final _q = TextEditingController();

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  Widget _row(HoolaColors c, String l, {String sub = ''}) {
    final on = l == widget.current;
    final native = kMusicLangNative[l];
    final title = native == null ? l : native;
    final under = sub.isNotEmpty ? sub : (native == null ? '' : l);
    return Semantics(
      button: true,
      selected: on,
      label: l == 'Auto' ? 'Auto, the language of your words or lyrics' : l,
      excludeSemantics: true,
      child: InkWell(
        onTap: () => Navigator.of(context).pop(l),
        borderRadius: BorderRadius.circular(12),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 52),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                  Text(title, style: HoolaType.body(c).copyWith(fontWeight: on ? FontWeight.w600 : FontWeight.w400)),
                  if (under.isNotEmpty) Text(under, style: HoolaType.small(c).copyWith(fontSize: 12)),
                ]),
              ),
              if (on) CrIcon(CrGlyph.check, size: 18, color: c.accent),
            ]),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final q = _q.text.trim().toLowerCase();
    final hits = kMusicLangs.where((l) => l != 'Auto' && (q.isEmpty || l.toLowerCase().contains(q) ||
        (kMusicLangNative[l] ?? '').toLowerCase().contains(q))).toList();
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * .85),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
              child: Semantics(header: true, child: Text('Language', style: HoolaType.heading(c))),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: TextField(
                controller: _q,
                onChanged: (_) => setState(() {}),
                style: HoolaType.body(c),
                decoration: InputDecoration(
                  hintText: 'Search ${kMusicLangs.length - 1} languages',
                  prefixIcon: Padding(padding: const EdgeInsets.all(14), child: CrIcon(CrGlyph.search, size: 16, color: c.ink3)),
                  filled: true,
                  fillColor: c.sunk,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: c.lineStrong)),
                ),
              ),
            ),
            Flexible(
              child: ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(12, 0, 12, 8), children: [
                if (q.isEmpty) ...[
                  _row(c, 'Auto', sub: 'The language of your words or lyrics'),
                  Padding(padding: const EdgeInsets.fromLTRB(8, 12, 8, 4), child: Text('Most used', style: HoolaType.label(c))),
                  for (final l in kMusicMostUsed) _row(c, l),
                  Padding(padding: const EdgeInsets.fromLTRB(8, 12, 8, 4), child: Text('All languages', style: HoolaType.label(c))),
                  for (final l in hits.where((l) => !kMusicMostUsed.contains(l))) _row(c, l),
                ] else if (hits.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text('Not in the list. Choose Auto and write your words in that language: Hoola sings in it if the engine can.',
                        style: HoolaType.small(c)),
                  )
                else
                  for (final l in hits) _row(c, l),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
              child: Text('Two languages in one song? Say it in the chat: “Hindi verses, English chorus”.', style: HoolaType.small(c)),
            ),
          ]),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ earlier Music chats
class MusicChatsSheet extends StatelessWidget {
  const MusicChatsSheet({super.key, required this.chats, required this.current});
  final List<Map<String, dynamic>> chats;
  final String current;

  String _when(String at) {
    final t = DateTime.tryParse(at.endsWith('Z') || RegExp(r'[+-]\d\d:\d\d$').hasMatch(at) ? at : '${at}Z');
    if (t == null) return '';
    return crWhen(t.millisecondsSinceEpoch ~/ 1000);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrHueScope(
      hue: CrHue.song,
      child: SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * .8),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
              child: Semantics(header: true, child: Text('Music chats', style: HoolaType.heading(c))),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: CrMain(label: 'New Music chat', height: 48, glyph: CrGlyph.plus, onTap: () => Navigator.of(context).pop('+new')),
            ),
            Flexible(
              child: chats.isEmpty
                  ? Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
                      child: Text('No earlier Music chats yet.', style: HoolaType.small(c)),
                    )
                  : ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(12, 4, 12, 8), children: [
                      for (final ch in chats)
                        Semantics(
                          button: true,
                          selected: crS(ch['id']) == current,
                          label: crS(ch['title']),
                          excludeSemantics: true,
                          child: InkWell(
                            borderRadius: BorderRadius.circular(12),
                            onTap: () => Navigator.of(context).pop(crS(ch['id'])),
                            child: Container(
                              constraints: const BoxConstraints(minHeight: 56),
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                              decoration: BoxDecoration(
                                  color: crS(ch['id']) == current ? c.sunk : null, borderRadius: BorderRadius.circular(12)),
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
                                Text(crS(ch['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                                    style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                                if (_when(crS(ch['at'])).isNotEmpty) Text(_when(crS(ch['at'])), style: HoolaType.small(c).copyWith(fontSize: 12)),
                              ]),
                            ),
                          ),
                        ),
                    ]),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
              child: Text('Music chats stay out of your Hoola chats list. What you tell Hoola here still reaches your one memory.',
                  style: HoolaType.small(c)),
            ),
          ]),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ one song: the player
/// One song in a dark room: its versions, its words, the time line, quick changes and "Ask Hoola". A change or an ask
/// goes back to the Music chat as her message (popped as (words, song id)), where it becomes a new version.
class MusicPlayerPage extends StatefulWidget {
  const MusicPlayerPage({super.key, required this.store, required this.player, required this.item, required this.versions});
  final CreateStore store;
  final MusicPlayer player;
  final Map<String, dynamic> item;
  final List<Map<String, dynamic>> versions;
  @override
  State<MusicPlayerPage> createState() => _MusicPlayerPageState();
}

class _MusicPlayerPageState extends State<MusicPlayerPage> {
  late Map<String, dynamic> _it = widget.item;
  final _ask = TextEditingController();

  @override
  void dispose() {
    _ask.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> get _all {
    final ids = widget.versions.map((x) => crS(x['id'])).toSet();
    final edits = widget.store.items.where((x) => ids.contains(crS(crMap(x['meta'])['parent'])) && !ids.contains(crS(x['id'])));
    final out = [...widget.versions, ...edits];
    if (!out.any((x) => crS(x['id']) == crS(_it['id']))) out.insert(0, _it);
    return out;
  }

  String _tab(Map<String, dynamic> x) {
    final m = crMap(x['meta']);
    if (crS(m['version']).isNotEmpty) return 'Version ${crS(m['version'])}';
    if (crS(m['edit']).isNotEmpty) return crS(m['edit']);
    return 'This song';
  }

  void _back(String words) => Navigator.of(context).pop((words, crS(_it['id'])));

  @override
  Widget build(BuildContext context) {
    const d = HoolaColors.darkSet;
    final m = crMap(_it['meta']);
    final id = crS(_it['id']);
    final title = musicTitle(_it);
    final lyrics = crS(m['lyrics']).trim();
    return Theme(
      data: Theme.of(context).copyWith(extensions: [d]),
      child: CrHueScope(
        hue: CrHue.song,
        child: ListenableBuilder(
        listenable: widget.player,
        builder: (context, _) {
          final p = widget.player;
          final mine = p.id == id;
          final pos = mine ? p.position : Duration.zero;
          final total = mine && p.duration > Duration.zero ? p.duration : Duration(seconds: crInt(m['seconds']));
          return Scaffold(
            backgroundColor: d.bg,
            body: SafeArea(
              child: Column(children: [
                SizedBox(
                  height: 60,
                  child: Row(children: [
                    const SizedBox(width: 4),
                    CrRoundButton(glyph: CrGlyph.back, label: 'Close the player', onTap: () => Navigator.of(context).maybePop()),
                    const Spacer(),
                    CrRoundButton(glyph: CrGlyph.share, label: 'Save or share', onTap: () => crShareItem(context, widget.store.app, _it)),
                    const SizedBox(width: 4),
                  ]),
                ),
                Expanded(
                  child: ListView(padding: const EdgeInsets.fromLTRB(22, 4, 22, 8), children: [
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(children: [
                        for (final x in _all)
                          Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: CrChip(label: _tab(x), on: crS(x['id']) == id, onTap: () => setState(() => _it = x)),
                          ),
                      ]),
                    ),
                    const SizedBox(height: 18),
                    Text(title, style: HoolaType.display(d)),
                    const SizedBox(height: 4),
                    Text([musicLine(_it), 'made by AI'].where((x) => x.isNotEmpty).join(' · '), style: HoolaType.small(d).copyWith(fontSize: 15)),
                    const SizedBox(height: 22),
                    if (lyrics.isEmpty)
                      Text(crS(m['vocals']) == 'none' ? 'Music only, no words.' : 'The words Hoola wrote are sung in the song.',
                          style: HoolaType.reply(d).copyWith(color: d.ink2))
                    else
                      for (final line in lyrics.split('\n'))
                        if (line.trim().isEmpty)
                          const SizedBox(height: 8)
                        else if (RegExp(r'^\s*\[.*\]\s*$').hasMatch(line))
                          Padding(padding: const EdgeInsets.only(top: 10, bottom: 2), child: Text(line.trim().replaceAll(RegExp(r'[\[\]]'), ''), style: HoolaType.label(d)))
                        else
                          Text(line.trim(), style: HoolaType.reply(d).copyWith(fontSize: 18, height: 1.45)),
                  ]),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(22, 4, 22, 0),
                  child: Column(children: [
                    Semantics(
                      slider: true,
                      label: 'Where the song is',
                      value: '${musicClock(pos.inSeconds)} of ${musicClock(total.inSeconds)}',
                      child: LayoutBuilder(
                        builder: (context, box) => GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTapDown: (e) {
                            if (mine && box.maxWidth > 0) p.seekTo((e.localPosition.dx / box.maxWidth).clamp(0.0, 1.0));
                          },
                          child: SizedBox(height: 48, child: Center(child: MusicWave(seed: id, frac: p.frac(id), height: 36, off: d.lineStrong))),
                        ),
                      ),
                    ),
                    Row(children: [
                      Text(musicClock(pos.inSeconds), style: HoolaType.small(d).copyWith(fontSize: 12)),
                      const Spacer(),
                      Text(musicClock(total.inSeconds), style: HoolaType.small(d).copyWith(fontSize: 12)),
                    ]),
                    Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Semantics(
                        button: true,
                        label: 'Back 10 seconds',
                        excludeSemantics: true,
                        child: crTap48(mine ? () => p.seekBy(-10) : null,
                            Padding(padding: const EdgeInsets.all(8), child: Text('−10', style: HoolaType.body(d)))),
                      ),
                      const SizedBox(width: 20),
                      MusicPlayButton(label: p.playing(id) ? 'Pause' : 'Play', playing: p.playing(id), loading: p.loading && mine,
                          size: 64, onDark: true, onTap: () => p.toggle(context, id)),
                      const SizedBox(width: 20),
                      Semantics(
                        button: true,
                        label: 'Forward 10 seconds',
                        excludeSemantics: true,
                        child: crTap48(mine ? () => p.seekBy(10) : null,
                            Padding(padding: const EdgeInsets.all(8), child: Text('+10', style: HoolaType.body(d)))),
                      ),
                    ]),
                  ]),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(14, 12, 14, 0),
                  child: Row(children: [
                    for (final a in [
                      ('Reel cut', CrGlyph.cut, 'Make a 30 second reel cut of ${crS(_it['title'])}: start on the chorus and fade out the end'),
                      ('Fade end', CrGlyph.minus, 'Fade out the last 3 seconds of ${crS(_it['title'])}'),
                      ('Louder', CrGlyph.plus, 'Make ${crS(_it['title'])} louder for social media'),
                      ('Like this', CrGlyph.spark, ''),
                    ])
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 3),
                          child: Semantics(
                            button: true,
                            label: a.$1 == 'Like this' ? 'More like this' : a.$1,
                            excludeSemantics: true,
                            child: Material(
                              color: d.sunk,
                              borderRadius: BorderRadius.circular(16),
                              child: InkWell(
                                borderRadius: BorderRadius.circular(16),
                                onTap: () => a.$3.isEmpty ? _back('Make another song like ${crS(_it['title'])}, same words and feel') : _back(a.$3),
                                child: SizedBox(
                                  height: 64,
                                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                                    CrIcon(a.$2, size: 18, color: d.ink),
                                    const SizedBox(height: 6),
                                    Text(a.$1, style: HoolaType.small(d).copyWith(fontSize: 12, color: d.ink)),
                                  ]),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                  ]),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
                  child: Container(
                    padding: const EdgeInsets.fromLTRB(16, 2, 4, 2),
                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(24), border: Border.all(color: d.lineStrong)),
                    child: Row(children: [
                      Expanded(
                        child: TextField(
                          controller: _ask,
                          style: HoolaType.body(d),
                          textInputAction: TextInputAction.send,
                          onSubmitted: (t) {
                            if (t.trim().isNotEmpty) _back(t.trim());
                          },
                          decoration: InputDecoration(
                            hintText: 'Ask Hoola: make it slower, end softly…',
                            hintStyle: HoolaType.body(d).copyWith(color: d.ink3),
                            border: InputBorder.none,
                            enabledBorder: InputBorder.none,
                            focusedBorder: InputBorder.none,
                            filled: false,
                            isDense: true,
                          ),
                        ),
                      ),
                      Semantics(
                        button: true,
                        label: 'Ask Hoola',
                        excludeSemantics: true,
                        child: crTap48(() {
                          final t = _ask.text.trim();
                          if (t.isNotEmpty) _back(t);
                        }, Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(color: d.ink, shape: BoxShape.circle),
                          child: Icon(Icons.arrow_upward_rounded, size: 18, color: d.bg),
                        )),
                      ),
                    ]),
                  ),
                ),
              ]),
            ),
          );
        },
      ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ Your songs
class MusicLibraryPage extends StatefulWidget {
  const MusicLibraryPage({super.key, required this.store, required this.player, required this.onAsk});
  final CreateStore store;
  final MusicPlayer player;
  final void Function(String words, String id) onAsk;
  @override
  State<MusicLibraryPage> createState() => _MusicLibraryPageState();
}

class _MusicLibraryPageState extends State<MusicLibraryPage> {
  final _q = TextEditingController();
  String _filter = 'All';

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  static String kindOf(Map<String, dynamic> it) {
    final m = crMap(it['meta']);
    if (crS(m['parent']).isNotEmpty) return 'Edits';
    final g = crS(m['genre']).toLowerCase();
    if (g.contains('jingle')) return 'Jingles';
    if (crS(m['vocals']) == 'none') return 'Instrumentals';
    return 'Songs';
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrHueScope(
      hue: CrHue.song,
      child: ListenableBuilder(
        listenable: Listenable.merge([widget.store, widget.player]),
        builder: (context, _) {
          final q = _q.text.trim().toLowerCase();
          final all = widget.store.shelf('song');
          final shown = all.where((it) {
            if (_filter != 'All' && kindOf(it) != _filter) return false;
            if (q.isEmpty) return true;
            final m = crMap(it['meta']);
            return [it['title'], m['lyrics'], m['language'], m['genre'], m['brief']].map(crS).join(' ').toLowerCase().contains(q);
          }).toList();
          final groups = <String, List<Map<String, dynamic>>>{};
          for (final it in shown) {
            final w = crWhen(it['created']);
            groups.putIfAbsent(w.isEmpty ? 'Earlier' : w, () => []).add(it);
          }
          return Scaffold(
            backgroundColor: c.bg,
            body: SafeArea(
              child: Column(children: [
                SizedBox(
                  height: 60,
                  child: Row(children: [
                    const SizedBox(width: 4),
                    CrRoundButton(glyph: CrGlyph.back, label: 'Back', onTap: () => Navigator.of(context).maybePop()),
                    Expanded(child: Semantics(header: true, child: Text('Your songs', textAlign: TextAlign.center, style: HoolaType.title(c)))),
                    const SizedBox(width: 52),
                  ]),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                  child: TextField(
                    controller: _q,
                    onChanged: (_) => setState(() {}),
                    style: HoolaType.body(c),
                    decoration: InputDecoration(
                      hintText: 'Search by name, words or language',
                      prefixIcon: Padding(padding: const EdgeInsets.all(14), child: CrIcon(CrGlyph.search, size: 16, color: c.ink3)),
                      filled: true,
                      fillColor: c.sunk,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: c.lineStrong)),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Wrap(spacing: 6, runSpacing: 6, children: [
                    for (final f in const ['All', 'Songs', 'Instrumentals', 'Jingles', 'Edits'])
                      CrChip(label: f, on: f == _filter, onTap: () => setState(() => _filter = f)),
                  ]),
                ),
                Expanded(
                  child: shown.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(32),
                            child: Text(all.isEmpty ? 'Your songs appear here. Describe a song in the Music chat, in any language, and send.'
                                : 'No songs match.', textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 15)),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: widget.store.reloadItems,
                          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 8, 24), children: [
                            for (final g in groups.entries) ...[
                              Padding(padding: const EdgeInsets.fromLTRB(0, 10, 0, 4), child: Text(g.key, style: HoolaType.label(c))),
                              for (final it in g.value) _row(c, it),
                            ],
                          ]),
                        ),
                ),
              ]),
            ),
          );
        },
      ),
    );
  }

  Widget _row(HoolaColors c, Map<String, dynamic> it) {
    final id = crS(it['id']);
    final p = widget.player;
    final m = crMap(it['meta']);
    final job = crS(m['job']);
    final versions = job.isEmpty ? [it] : widget.store.items.where((x) => crS(crMap(x['meta'])['job']) == job).toList();
    Future<void> open() async {
      final ask = await Navigator.of(context).push<(String, String)>(MaterialPageRoute(
          builder: (_) => MusicPlayerPage(store: widget.store, player: p, item: it, versions: versions)));
      if (ask != null && mounted) {
        Navigator.of(context).pop();
        widget.onAsk(ask.$1, ask.$2);
      }
    }

    return Row(children: [
      Expanded(
        child: Semantics(
          button: true,
          label: 'Open ${musicTitle(it)}, ${musicLine(it)}',
          excludeSemantics: true,
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: open,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(children: [
                Container(
                  width: 48, height: 48,
                  decoration: BoxDecoration(gradient: CrHue.song.gradient, borderRadius: BorderRadius.circular(12)),
                  child: Center(child: CrIcon(kindOf(it) == 'Edits' ? CrGlyph.cut : CrGlyph.music, size: 20, color: CreateHues.onHue)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(musicTitle(it), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                    Text(musicLine(it), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
                  ]),
                ),
              ]),
            ),
          ),
        ),
      ),
      MusicPlayButton(
        label: '${p.playing(id) ? 'Pause' : 'Play'} ${musicTitle(it)}',
        playing: p.playing(id),
        loading: p.loading && p.id == id,
        size: 40,
        onTap: () => p.toggle(context, id),
      ),
      CrRoundButton(glyph: CrGlyph.layers, label: 'More for ${musicTitle(it)}', size: 36, onTap: () async {
        final pick = await crPick(context, musicTitle(it), const ['Open', 'Save or share', 'Delete'], '');
        if (!mounted || pick == null) return;
        if (pick == 'Open') await open();
        if (pick == 'Save or share' && mounted) await crShareItem(context, widget.store.app, it);
        if (pick == 'Delete' && mounted) {
          final ok = await musicConfirmDelete(context, it);
          if (ok == true) await widget.store.delete(id);
        }
      }),
    ]);
  }
}
