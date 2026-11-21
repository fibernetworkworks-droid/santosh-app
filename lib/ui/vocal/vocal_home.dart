// v0.999.89 HOOLA VOCAL, GLOBAL, ON THE PHONE (owner, on the design canvas claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue:
// "GO BUILD ALL"; contract docs/HOOLA_VOCAL_GLOBAL.md): Tools > Hoola Vocal on the phone is the console's Vocal chat - one
// Conversation of kind 'vocal' (/api/vocal/chat*), her Voice settings in ONE sheet behind a pill above the box (any
// language or Auto, a voice that speaks it, style, speed, 1-3 takes, the price from /api/vocal/quote), the takes Hoola
// makes land in the chat as a set (Take A, Take B) with quick changes (Slower / Warmer / Another voice), earlier Vocal
// chats, Your sounds, and failures said plainly ("Hoola can't answer right now" -> make it now; a take that could not be
// made -> Try again, nothing charged). Her picks ride her message as "[Vocal settings: ...]"; her bubble shows only her
// words. Nothing paid runs without her tap: a take is made when she sends.
import 'dart:async';
import 'dart:math' as math;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../state.dart';
import '../hoola_mark.dart';
import '../hoola_theme.dart';
import 'vocal_kit.dart';
import 'vocal_sounds.dart';
import 'vocal_voices.dart';

// ------------------------------------------------------------------------------------------------ the Vocal chat
class HoolaVocal extends StatefulWidget {
  const HoolaVocal({super.key, required this.app, this.settings});
  final Santosh app;
  /// Her settings to start from (tests, a link from another screen); else the phone's language.
  final VocalSettings? settings;
  @override
  State<HoolaVocal> createState() => _HoolaVocalState();
}

class _Up {
  _Up(this.name);
  final String name;
  String fileId = '', error = '';
  bool busy = true;
}

class _HoolaVocalState extends State<HoolaVocal> {
  late final VocalStore store = VocalStore(widget.app);
  late final VocalPlayer _player = VocalPlayer(widget.app);
  final _q = TextEditingController();
  final _scroll = ScrollController();
  final _focusNode = FocusNode();
  VocalSettings? _vs;
  String _conv = '', _title = 'Vocal chat', _focus = '', _focusTitle = '', _openError = '';
  List<Map<String, dynamic>> _rows = [];
  List<Map<String, dynamic>> _items = [];
  Map<String, dynamic>? _turn;
  Map<String, dynamic> _quote = const {};
  String _lastText = '';
  int _lastAt = 0;
  bool _sending = false, _loading = false, _makingNow = false;
  final List<_Up> _files = [];
  int _seen = 0;
  Timer? _timer;

  bool get _debug => VocalStore.debug;
  VocalSettings get vs => _vs ??= widget.settings ?? VocalSettings();

  @override
  void initState() {
    super.initState();
    _q.addListener(() => setState(() {}));
    unawaited(_boot());
  }

  Future<void> _boot() async {
    await store.load();
    if (!mounted) return;
    // the phone's language when a ready engine speaks it (the contract's global rule), unless she already chose one
    if (widget.settings == null && vs.lang == 'auto') vs.lang = VocalSettings.forPhone(store).lang;
    await _open();
    unawaited(_requote());
  }

  @override
  void dispose() {
    _timer?.cancel();
    _q.dispose();
    _scroll.dispose();
    _focusNode.dispose();
    _player.dispose();
    store.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------- the chat
  Future<void> _open([String? id, String? title]) async {
    if (_debug) {
      final d = crMap(VocalStore.debugData!['chat']);
      setState(() {
        _conv = crS(d['conv']).isEmpty ? 'vc-debug' : crS(d['conv']);
        _title = crS(d['title']).isEmpty ? 'Vocal chat' : crS(d['title']);
        _rows = crList(d['rows']);
        _items = crList(d['items']);
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
      // an earlier chat is checked as hers first (and marked a Vocal chat for its turns), as the console does
      if (id != null) await api.call('GET', '/api/vocal/chat/${Uri.encodeComponent(id)}/ok');
      final c = id == null ? await api.vocalChat() : {'id': id, 'title': title ?? 'Vocal chat'};
      if (!mounted) return;
      setState(() {
        _conv = crS(c['id']).isEmpty ? crS(c['conversation_id']) : crS(c['id']);
        _title = crS(c['title']).isEmpty ? 'Vocal chat' : crS(c['title']);
        _rows = [];
        _items = [];
        _turn = null;
        _focus = '';
        _focusTitle = '';
        _openError = '';
      });
      await _load(first: true);
    } catch (e) {
      if (mounted) setState(() => _openError = 'The Vocal chat could not open. ${crError(e)}');
    }
    _schedule();
  }

  bool get _working {
    if (_sending) return true;
    final st = _turn == null ? '' : crS(_turn!['status']);
    if (st.isNotEmpty) return st == 'working' || st == 'queued';
    return _rows.isNotEmpty && _rows.last['role'] == 'user';
  }

  void _schedule() {
    _timer?.cancel();
    if (_debug || !mounted) return;
    _timer = Timer(Duration(milliseconds: _working ? 2000 : 8000), () async {
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
      Map<String, dynamic>? turn = _turn;
      if (first || _working) {
        try {
          turn = crMap(await api.call('GET', '/api/conversations/${Uri.encodeComponent(conv)}/result'));
        } catch (_) {}
      }
      final rows = crList(crMap(await api.call('GET', '/api/conversations/${Uri.encodeComponent(conv)}/messages',
          query: {'limit': '200'}))['messages']);
      var items = _items;
      try {
        items = await api.vocalChatItems(conv);
      } catch (_) {}
      if (!mounted || conv != _conv) return;
      setState(() {
        _rows = rows;
        _items = items;
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
    final n = _rows.length + _items.length;
    if (n == _seen) return;
    _seen = n;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent, duration: HoolaMotion.of(context, HoolaMotion.menu), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _requote() async {
    final api = store.app.api;
    if (_debug) {
      if (mounted) setState(() => _quote = crMap(VocalStore.debugData!['quote']));
      return;
    }
    if (api == null) return;
    try {
      final q = await api.vocalQuote(vs.quote(_q.text));
      if (mounted) setState(() => _quote = q);
    } catch (_) {}
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
      crToast(context, 'Write what Hoola should say first.');
      return;
    }
    if (_files.any((f) => f.busy)) {
      crToast(context, 'Wait for the files to finish uploading.');
      return;
    }
    final l = store.lang(vs.lang);
    if (l != null && crS(l['speech']) == 'none') {
      crToast(context, 'No voice engine speaks ${store.langName(vs.lang)} yet. Choose another language in Voice settings.');
      return;
    }
    if (api == null || _conv.isEmpty) {
      crToast(context, 'Not connected to the server right now.');
      return;
    }
    HapticFeedback.selectionClick();
    final focus = _focus;
    final files = _files.where((f) => f.fileId.isNotEmpty).map((f) => f.fileId).toList();
    final full = '$text\n\n[${vs.note(store, focus: focus)}]';
    setState(() {
      _sending = true;
      _turn = null;
      _lastText = text;
      _lastAt = DateTime.now().millisecondsSinceEpoch ~/ 1000;
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

  /// Hoola could not answer: the same words are read straight away with her settings (POST /api/vocal/tts), her tap.
  Future<void> _makeNow(String text) async {
    final api = store.app.api;
    if (api == null || _debug || text.trim().isEmpty) return;
    setState(() => _makingNow = true);
    try {
      final r = await api.vocalTts(vs.body(text, chat: _conv));
      if (mounted) crToast(context, 'Made ${crList(r['items']).length} take${crList(r['items']).length == 1 ? '' : 's'}.');
      _lastAt = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      await _load();
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _makingNow = false);
  }

  Future<void> _addFiles() async {
    if (_conv.isEmpty || _debug) return;
    final r = await FilePicker.platform.pickFiles(allowMultiple: true, withData: true,
        type: FileType.custom, allowedExtensions: const ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'mp4', 'mov', 'txt', 'pdf', 'docx', 'epub']);
    if (r == null) return;
    final api = store.app.api;
    for (final f in r.files.take(math.max(0, 6 - _files.length))) {
      final up = _Up(f.name);
      setState(() => _files.add(up));
      final bytes = f.bytes;
      if (bytes == null || api == null || bytes.length > 30 * 1024 * 1024) {
        setState(() {
          up.busy = false;
          up.error = bytes == null ? 'Could not read' : 'Over 30 MB';
        });
        continue;
      }
      try {
        up.fileId = crS((await api.chatFile(_conv, f.name, bytes))['file_id']);
      } catch (e) {
        up.error = 'Not uploaded';
        if (mounted) crToast(context, '${f.name}: ${crError(e)}');
      }
      if (mounted) setState(() => up.busy = false);
    }
  }

  Future<void> _history() async {
    final api = store.app.api;
    List<Map<String, dynamic>> cs = [];
    if (_debug) {
      cs = crList(VocalStore.debugData!['chats']);
    } else if (api != null) {
      try {
        cs = await api.vocalChats();
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
      builder: (ctx) => VocalChatsSheet(chats: cs, current: _conv),
    );
    if (pick == null || !mounted || _debug) return;
    if (pick == '+new') {
      try {
        final c = await api!.vocalChatNew();
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
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => CrHueScope(hue: CrHue.voice, child: VocalSettingsSheet(settings: vs, store: store, player: _player, text: _q.text)),
    );
    if (mounted) setState(() {});
    unawaited(_requote());
  }

  Future<void> _voices() async {
    final id = await Navigator.of(context).push<String>(MaterialPageRoute(
        builder: (_) => HoolaTheme(appearance: widget.app.appearance,
            child: VocalVoicesPage(store: store, player: _player, lang: vs.lang, picked: vs.voice, conv: _conv))));
    if (id != null && mounted) {
      setState(() => vs.voice = id);
      unawaited(_requote());
    }
  }

  void _sounds() => Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => HoolaTheme(appearance: widget.app.appearance,
          child: VocalSoundsPage(store: store, player: _player, onAsk: (t) {
            _q.text = t;
            _focusNode.requestFocus();
          }))));

  Future<void> _takeMenu(Map<String, dynamic> it, String name) async {
    final pick = await crPick(context, name, const ['Change this take', 'Download or share', 'Delete'], '');
    if (!mounted || pick == null) return;
    switch (pick) {
      case 'Change this take':
        setState(() {
          _focus = crS(it['id']);
          _focusTitle = name;
        });
        _focusNode.requestFocus();
      case 'Download or share':
        await vocalShare(context, widget.app, it);
      case 'Delete':
        final ok = await vocalConfirm(context, 'Delete this take?', 'It is removed from this chat and from Your sounds. This cannot be undone.', 'Delete');
        if (ok != true || !mounted) return;
        try {
          if (!_debug) await store.app.api?.vocalHistoryDelete(crS(it['id']));
          setState(() => _items = _items.where((x) => crS(x['id']) != crS(it['id'])).toList());
        } catch (e) {
          if (mounted) crToast(context, crError(e));
        }
    }
  }

  // ---------------------------------------------------------------- the screen
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrHueScope(
      hue: CrHue.voice,
      child: ListenableBuilder(
        listenable: Listenable.merge([store, _player]),
        builder: (context, _) {
          final sets = vocalSets(_items);
          final started = _rows.any((r) => r['role'] == 'user') || sets.isNotEmpty;
          return Scaffold(
            backgroundColor: c.bg,
            body: SafeArea(
              child: Column(children: [
                VocalTop(
                  title: started ? _title : 'Vocal',
                  sub: started ? 'Vocal chat' : '',
                  actions: [
                    CrRoundButton(glyph: CrGlyph.voice, label: 'Voices', onTap: _voices),
                    CrRoundButton(glyph: CrGlyph.folder, label: 'Your sounds', onTap: _sounds),
                    CrRoundButton(glyph: CrGlyph.clock, label: 'Earlier Vocal chats', onTap: _history),
                  ],
                ),
                Expanded(child: started ? _thread(c, sets) : _start(c)),
                _composer(c),
              ]),
            ),
          );
        },
      ),
    );
  }

  Widget _start(HoolaColors c) {
    const tries = [
      ('Our shop welcome in Swahili', 'A warm woman · a little slow', 'Read our shop welcome in Swahili, a warm woman, a little slow: Karibu Mkate Bora, mkate safi kila asubuhi.'),
      ('A birthday wish in Spanish', 'Cheerful · two takes', '¡Feliz cumpleaños, Lucía! Hoy cumples seis años. Read it cheerful, like a happy aunt.'),
      ('A calm Hindi announcement', 'News style · a man', 'A calm Hindi announcement for our clinic: कल क्लिनिक सुबह दस बजे खुलेगा।'),
      ('A podcast intro, two voices', 'Dialogue · English', 'A 20 second podcast intro with two hosts, Asha and Kofi, for our show Tech Talk.'),
    ];
    return ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 12), children: [
      const SizedBox(height: 12),
      const Center(child: HoolaMark(size: 40)),
      const SizedBox(height: 14),
      Text('What should Hoola say?', textAlign: TextAlign.center, style: HoolaType.replyH1(c).copyWith(fontSize: 28, fontWeight: FontWeight.w400)),
      const SizedBox(height: 8),
      Text('Any words, in any language Hoola speaks. Pick a voice, or let Hoola choose; you get takes to pick from.',
          textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 15)),
      if (_openError.isNotEmpty || store.error.isNotEmpty) ...[
        const SizedBox(height: 14),
        CrNote(_openError.isNotEmpty ? _openError : store.error, glyph: CrGlyph.info),
      ],
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

  Widget _thread(HoolaColors c, List<VocalSet> sets) {
    // a set sits after the reply of the turn that made it (or after her message when there is none)
    final after = <int, List<VocalSet>>{};
    for (final s in sets) {
      var i = -1;
      for (var j = 0; j < _rows.length; j++) {
        if (vocalEpoch(_rows[j]['at']) <= s.created + 1) i = j;
      }
      if (i >= 0 && _rows[i]['role'] == 'user' && i + 1 < _rows.length && _rows[i + 1]['role'] != 'user') i++;
      after.putIfAbsent(i, () => []).add(s);
    }
    final kids = <Widget>[for (final s in after[-1] ?? const <VocalSet>[]) _setCard(c, s, s == sets.last)];
    for (var j = 0; j < _rows.length; j++) {
      final r = _rows[j];
      final text = crS(r['text']);
      if (r['role'] == 'user') {
        final shown = vocalStripNotes(text);
        if (shown.isNotEmpty) kids.add(_her(c, shown));
      } else if (text.trim().isNotEmpty && j > 0) {
        kids.add(_hoola(c, text.trim()));
      }
      for (final s in after[j] ?? const <VocalSet>[]) {
        kids.add(_setCard(c, s, s == sets.last));
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
    final line = _turn != null && crS(_turn!['line']).isNotEmpty ? crS(_turn!['line']) : 'Reading your words…';
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

  /// Hoola could not answer: her words can still be read straight away with her Voice settings.
  Widget? _failCard(HoolaColors c, List<VocalSet> sets) {
    if (_working || _rows.isEmpty) return null;
    final st = _turn == null ? '' : crS(_turn!['status']);
    if (!RegExp('fail|error|stuck').hasMatch(st)) return null;
    if (_lastAt > 0 && sets.any((s) => s.created >= _lastAt - 1)) return null;
    final hers = _rows.lastWhere((r) => r['role'] == 'user', orElse: () => const {});
    final text = _lastText.isNotEmpty ? _lastText : vocalStripNotes(crS(hers['text']));
    if (text.isEmpty) return null;
    final credits = crInt(_quote['credits']);
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
            Text('Your words and Voice settings are ready. Make the takes straight away, without the chat.',
                style: HoolaType.small(c).copyWith(color: c.ink2)),
            const SizedBox(height: 10),
            CrMain(
              label: credits > 0 ? 'Make it now · $credits credits' : 'Make it now',
              height: 48,
              glyph: CrGlyph.voice,
              busy: _makingNow,
              onTap: () => _makeNow(text),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _setCard(HoolaColors c, VocalSet s, bool newest) {
    final made = s.takes.where((t) => !vocalFailed(t)).toList();
    final failed = s.takes.where(vocalFailed).toList();
    final kids = <Widget>[];
    for (var i = 0; i < s.takes.length; i++) {
      final t = s.takes[i];
      if (vocalFailed(t)) continue;
      kids.add(_takeRow(c, t, vocalTakeLetter(t, i), highlight: newest && i == s.takes.length - 1));
      kids.add(const SizedBox(height: 8));
    }
    if (failed.isNotEmpty) {
      final f = failed.first;
      kids.add(_failedTake(c, f));
      kids.add(const SizedBox(height: 8));
    }
    if (made.isNotEmpty) {
      final last = made.last;
      final letter = vocalTakeLetter(last, s.takes.indexOf(last));
      final what = crS(last['title']).isEmpty ? '' : ' ("${crS(last['title'])}")';
      void ask(String words) {
        setState(() => _focus = crS(last['id']));
        _send(words);
      }

      kids.add(Wrap(spacing: 6, runSpacing: 6, children: [
        CrSmall(label: 'Slower', glyph: CrGlyph.minus, onTap: () => ask('Make take $letter$what a little slower')),
        CrSmall(label: 'Warmer', glyph: CrGlyph.spark, onTap: () => ask('Make take $letter$what warmer')),
        CrSmall(label: 'Another voice', glyph: CrGlyph.voice, onTap: () => ask('Read take $letter$what again in another voice')),
      ]));
      kids.add(const SizedBox(height: 6));
      kids.add(Text('Made by AI · marked in the file', style: HoolaType.small(c).copyWith(fontSize: 12)));
    }
    return Semantics(
      container: true,
      explicitChildNodes: true,
      child: Padding(
        padding: const EdgeInsets.only(left: 32),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: kids),
      ),
    );
  }

  Widget _takeRow(HoolaColors c, Map<String, dynamic> t, String letter, {bool highlight = false}) {
    final id = crS(t['id']);
    final name = 'Take $letter';
    final playing = _player.playing(id);
    final secs = (t['seconds'] is num) ? t['seconds'] as num : 0;
    final line = [
      store.langNative(crS(t['lang'])),
      if (crS(t['voice_name']).isNotEmpty) crS(t['voice_name']),
      if (secs > 0) vocalClock(secs),
    ].where((x) => x.isNotEmpty && x != 'Auto').join(' · ');
    return CrCard(
      padding: const EdgeInsets.fromLTRB(8, 4, 4, 4),
      edge: highlight || playing ? CrHue.voice.a : null,
      child: Row(children: [
        VocalPlayButton(
          label: '${playing ? 'Pause' : 'Play'} $name',
          playing: playing,
          loading: _player.busy(id),
          onTap: () => _player.toggle(context, id, () => store.app.api!.vocalAudio(id, format: 'mp3'), ext: 'mp3'),
        ),
        const SizedBox(width: 4),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(name, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
            if (line.isNotEmpty) Text(line, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
        ),
        CrRoundButton(glyph: CrGlyph.layers, label: 'More for $name', size: 36, onTap: () => _takeMenu(t, name)),
      ]),
    );
  }

  Widget _failedTake(HoolaColors c, Map<String, dynamic> f) {
    final err = crS(f['error']);
    return CrCard(
      padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(color: c.badSoft, shape: BoxShape.circle),
            child: Center(child: CrIcon(CrGlyph.info, size: 16, color: c.bad)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Could not be made', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
              Text(err.isEmpty ? 'It did not work this time. Nothing was charged.' : '${err.endsWith('.') ? err : '$err.'} Nothing was charged.',
                  style: HoolaType.small(c).copyWith(fontSize: 12)),
            ]),
          ),
        ]),
        Align(
          alignment: Alignment.centerRight,
          child: Semantics(container: true, child: CrSmall(label: 'Try again', glyph: CrGlyph.refresh, onTap: () {
            final text = _lastText.isNotEmpty ? _lastText : vocalStripNotes(crS(_rows.lastWhere((r) => r['role'] == 'user', orElse: () => const {})['text']));
            if (text.isNotEmpty) _send(text);
          })),
        ),
      ]),
    );
  }

  Widget _composer(HoolaColors c) {
    final working = _working && !_sending;
    final typed = _q.text.trim().isNotEmpty;
    final bottom = MediaQuery.viewInsetsOf(context).bottom > 0 ? 8.0 : 12.0;
    final started = _rows.any((r) => r['role'] == 'user');
    final price = _focus.isNotEmpty ? 'A change makes a new take; the take you had stays' : vocalQuoteLine(_quote, vs.takes);
    return Padding(
      padding: EdgeInsets.fromLTRB(12, 4, 12, bottom),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Semantics(
          button: true,
          label: 'Voice settings: ${vs.summary(store)}',
          excludeSemantics: true,
          child: crTap48(_settings, Container(
            height: 36,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(color: crWash(c), borderRadius: BorderRadius.circular(18)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              CrIcon(CrGlyph.voice, size: 14, color: c.ink2),
              const SizedBox(width: 6),
              Flexible(child: Text(vs.summary(store), maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500))),
              const SizedBox(width: 4),
              CrIcon(CrGlyph.chevron, size: 12, color: c.ink3),
            ]),
          )),
        ),
        const SizedBox(height: 4),
        Container(
          padding: const EdgeInsets.fromLTRB(4, 2, 6, 2),
          decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(26), border: Border.all(color: c.lineStrong)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            if (_focusTitle.isNotEmpty || _files.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(10, 6, 0, 0),
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
            Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
              CrRoundButton(glyph: CrGlyph.plus, label: 'Add a file or a recording', size: 36, onTap: _addFiles),
              Expanded(
                child: TextField(
                  controller: _q,
                  focusNode: _focusNode,
                  minLines: 1,
                  maxLines: 5,
                  textCapitalization: TextCapitalization.sentences,
                  style: HoolaType.bodyLarge(c),
                  decoration: InputDecoration(
                    hintText: started ? 'Say what to change' : 'Write what Hoola should say…',
                    hintStyle: HoolaType.bodyLarge(c).copyWith(color: c.ink3),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    filled: false,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(vertical: 13),
                  ),
                ),
              ),
              _sendButton(c, working: working, on: typed || working),
            ]),
          ]),
        ),
        if (price.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(8, 6, 8, 0),
            child: Text(price, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
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

// ------------------------------------------------------------------------------------------------ Voice settings
class VocalSettingsSheet extends StatefulWidget {
  const VocalSettingsSheet({super.key, required this.settings, required this.store, required this.player, this.text = ''});
  final VocalSettings settings;
  final VocalStore store;
  final VocalPlayer player;
  final String text;
  @override
  State<VocalSettingsSheet> createState() => _VocalSettingsSheetState();
}

class _VocalSettingsSheetState extends State<VocalSettingsSheet> {
  VocalSettings get s => widget.settings;
  VocalStore get store => widget.store;
  Map<String, dynamic> _quote = const {};
  bool _quoting = false;
  Timer? _wait;

  @override
  void initState() {
    super.initState();
    _requote(now: true);
  }

  @override
  void dispose() {
    _wait?.cancel();
    super.dispose();
  }

  void _put(VoidCallback f) {
    setState(f);
    _requote();
  }

  void _requote({bool now = false}) {
    _wait?.cancel();
    if (VocalStore.debug) {
      _quote = crMap(VocalStore.debugData!['quote']);
      return;
    }
    _wait = Timer(Duration(milliseconds: now ? 0 : 350), () async {
      final api = store.app.api;
      if (api == null) return;
      if (mounted) setState(() => _quoting = true);
      try {
        final q = await api.vocalQuote(s.quote(widget.text));
        if (mounted) setState(() => _quote = q);
      } catch (_) {}
      if (mounted) setState(() => _quoting = false);
    });
  }

  Future<void> _language() async {
    final v = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => CrHueScope(hue: CrHue.voice, child: VocalLanguageSheet(store: store, current: s.lang)),
    );
    if (v == null) return;
    _put(() {
      s.lang = v;
      if (v != 'auto') {
        VocalStore.recent
          ..remove(v)
          ..insert(0, v);
        if (VocalStore.recent.length > 4) VocalStore.recent.removeLast();
      }
      // a voice that does not speak the new language gives way to Hoola's pick
      if (s.voice.isNotEmpty && !store.voicesFor(v).any((x) => crS(x['id']) == s.voice)) s.voice = '';
    });
  }

  Future<void> _allVoices() async {
    final id = await Navigator.of(context).push<String>(MaterialPageRoute(
        builder: (_) => HoolaTheme(appearance: store.app.appearance,
            child: VocalVoicesPage(store: store, player: widget.player, lang: s.lang, picked: s.voice))));
    if (id != null) _put(() => s.voice = id);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final shown = store.voicesFor(s.lang).take(8).toList();
    if (s.voice.isNotEmpty && !shown.any((v) => crS(v['id']) == s.voice)) {
      final v = store.voice(s.voice);
      if (v != null) shown.insert(0, v);
    }
    final langLine = s.lang == 'auto' ? 'Auto · the language of your words' : '${store.langNative(s.lang)} · ${store.langName(s.lang)}';
    final line = vocalQuoteLine(_quote, s.takes);
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * .88),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 8, 4),
            child: Row(children: [
              Expanded(child: Semantics(header: true, child: Text('Voice settings', style: HoolaType.heading(c)))),
              Semantics(
                button: true,
                label: 'Start again with the usual settings',
                excludeSemantics: true,
                child: crTap48(() => _put(() {
                      final d = VocalSettings();
                      s
                        ..voice = d.voice
                        ..style = d.style
                        ..speed = d.speed
                        ..takes = d.takes
                        ..engine = d.engine;
                    }), Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Text('Reset', style: HoolaType.body(c).copyWith(color: c.accent, fontWeight: FontWeight.w500)),
                )),
              ),
            ]),
          ),
          Flexible(
            child: ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(20, 4, 20, 12), children: [
              const CrLabel('Language'),
              Semantics(
                button: true,
                label: 'Language: $langLine',
                excludeSemantics: true,
                child: CrCard(
                  padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
                  onTap: _language,
                  child: Row(children: [
                    Expanded(child: Text(langLine, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c))),
                    CrIcon(CrGlyph.chevron, size: 16, color: c.ink3),
                  ]),
                ),
              ),
              const SizedBox(height: 16),
              CrLabel('Voice', note: s.lang == 'auto' ? 'any language' : 'speak ${store.langNative(s.lang)}'),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(children: [
                  _voiceChip(c, null, s.voice.isEmpty),
                  for (final v in shown) _voiceChip(c, v, crS(v['id']) == s.voice),
                  Semantics(
                    button: true,
                    label: 'All voices',
                    excludeSemantics: true,
                    child: crTap48(_allVoices, Container(
                      height: 40,
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      decoration: BoxDecoration(borderRadius: BorderRadius.circular(20), border: Border.all(color: c.lineStrong)),
                      child: Center(child: Text('All voices', style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500))),
                    )),
                  ),
                ]),
              ),
              const SizedBox(height: 16),
              const CrLabel('Style'),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final e in store.styles.entries) CrChip(label: e.value, on: e.key == s.style, onTap: () => _put(() => s.style = e.key)),
              ]),
              const SizedBox(height: 16),
              CrLabel('Speed', note: '${vocalSpeed(s.speed)}x'),
              Semantics(
                label: 'Speed',
                value: '${vocalSpeed(s.speed)} times',
                child: Slider(
                  value: s.speed.clamp(.7, 1.3),
                  min: .7,
                  max: 1.3,
                  divisions: 12,
                  activeColor: CrHue.voice.b,
                  label: '${vocalSpeed(s.speed)}x',
                  onChanged: (v) => setState(() => s.speed = (v * 20).round() / 20),
                  onChangeEnd: (_) => _requote(),
                ),
              ),
              const SizedBox(height: 8),
              const CrLabel('Takes', note: 'pick the one you like'),
              CrSegment(options: const ['1', '2', '3'], picked: '${s.takes}', onPick: (v) => _put(() => s.takes = int.parse(v))),
            ]),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
            decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                  Text(line.isEmpty ? (_quoting ? 'Working out the price…' : '${s.takes} take${s.takes > 1 ? 's' : ''}') : line,
                      style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                  Text('An estimate · made when you send', style: HoolaType.small(c).copyWith(fontSize: 12)),
                ]),
              ),
              SizedBox(width: 120, child: CrMain(label: 'Done', height: 48, onTap: () => Navigator.of(context).maybePop())),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _voiceChip(HoolaColors c, Map<String, dynamic>? v, bool on) {
    final name = v == null ? 'Hoola picks' : crS(v['name']);
    final ready = v == null || v['ready'] != false;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Semantics(
        button: true,
        selected: on,
        enabled: ready,
        label: ready ? name : '$name, not ready',
        excludeSemantics: true,
        child: crTap48(ready ? () => _put(() => s.voice = v == null ? '' : crS(v['id'])) : null, Container(
          height: 40,
          padding: const EdgeInsets.fromLTRB(4, 0, 14, 0),
          decoration: BoxDecoration(
            color: on ? c.accentSoft : null,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: on ? c.accent : c.lineStrong),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            if (v == null)
              Container(width: 32, height: 32, decoration: BoxDecoration(gradient: CrHue.voice.gradient, shape: BoxShape.circle),
                  child: const Center(child: CrIcon(CrGlyph.spark, size: 14, color: CreateHues.onHue)))
            else
              VocalVoiceDot(voice: v, size: 32),
            const SizedBox(width: 8),
            Text(name, style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: on ? FontWeight.w600 : FontWeight.w500,
                color: ready ? c.ink : c.ink3)),
          ]),
        )),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ the language sheet
/// Auto, the ones she used lately, then every language in its own script, searchable. A language no ready engine speaks
/// says "No engine yet" and cannot be picked (it is never read in another language).
class VocalLanguageSheet extends StatefulWidget {
  const VocalLanguageSheet({super.key, required this.store, required this.current});
  final VocalStore store;
  final String current;
  @override
  State<VocalLanguageSheet> createState() => _VocalLanguageSheetState();
}

class _VocalLanguageSheetState extends State<VocalLanguageSheet> {
  final _q = TextEditingController();

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  Widget _row(HoolaColors c, Map<String, dynamic>? l) {
    final code = l == null ? 'auto' : crS(l['code']);
    final on = code == widget.current;
    final speech = l == null ? 'yes' : crS(l['speech']);
    final none = speech == 'none';
    final title = l == null ? 'Auto · the language of your words' : (crS(l['native']).isEmpty ? crS(l['name']) : crS(l['native']));
    final under = l == null ? 'Hoola hears which language you wrote in' : crS(l['name']);
    final note = l == null ? '' : none ? 'No engine yet' : speech == 'premium' ? 'Premium' : '${crInt(l['voices'])} voices';
    final noteColor = none ? c.bad : speech == 'premium' ? c.warn : c.ink3;
    return Semantics(
      button: !none,
      selected: on,
      enabled: !none,
      label: l == null ? 'Auto, the language of your words' : '$title, ${crS(l['name'])}${note.isEmpty ? '' : ', $note'}',
      excludeSemantics: true,
      child: InkWell(
        onTap: none ? null : () => Navigator.of(context).pop(code),
        borderRadius: BorderRadius.circular(12),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 52),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                  Text(title, style: HoolaType.body(c).copyWith(fontWeight: on ? FontWeight.w600 : FontWeight.w400, color: none ? c.ink3 : c.ink)),
                  if (under.isNotEmpty && under != title) Text(under, style: HoolaType.small(c).copyWith(fontSize: 12)),
                ]),
              ),
              if (note.isNotEmpty) Text(note, style: HoolaType.small(c).copyWith(fontSize: 12, color: noteColor, fontWeight: FontWeight.w500)),
              if (on) ...[const SizedBox(width: 8), CrIcon(CrGlyph.check, size: 18, color: c.accent)],
            ]),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final store = widget.store;
    final q = _q.text.trim().toLowerCase();
    final all = store.langs;
    final hits = all.where((l) => q.isEmpty ||
        [l['name'], l['native'], l['code'], l['region']].map((x) => crS(x).toLowerCase()).any((x) => x.contains(q))).toList();
    final recent = [for (final code in VocalStore.recent) if (store.lang(code) != null) store.lang(code)!];
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
              child: VocalSearch(controller: _q, hint: 'Search ${all.length} languages', onChanged: (_) => setState(() {})),
            ),
            Flexible(
              child: ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(12, 0, 12, 8), children: [
                if (q.isEmpty) ...[
                  _row(c, null),
                  if (recent.isNotEmpty) ...[
                    Padding(padding: const EdgeInsets.fromLTRB(8, 12, 8, 4), child: Text('Recently used', style: HoolaType.label(c))),
                    for (final l in recent) _row(c, l),
                  ],
                  Padding(padding: const EdgeInsets.fromLTRB(8, 12, 8, 4), child: Text('All languages', style: HoolaType.label(c))),
                  for (final l in hits) _row(c, l),
                ] else if (hits.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text('Not in the list. Choose Auto and write your words in that language: Hoola says if no engine speaks it.',
                        style: HoolaType.small(c)),
                  )
                else
                  for (final l in hits) _row(c, l),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ earlier Vocal chats
class VocalChatsSheet extends StatelessWidget {
  const VocalChatsSheet({super.key, required this.chats, required this.current});
  final List<Map<String, dynamic>> chats;
  final String current;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrHueScope(
      hue: CrHue.voice,
      child: SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * .8),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
              child: Semantics(header: true, child: Text('Vocal chats', style: HoolaType.heading(c))),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: CrMain(label: 'New Vocal chat', height: 48, glyph: CrGlyph.plus, onTap: () => Navigator.of(context).pop('+new')),
            ),
            Flexible(
              child: chats.isEmpty
                  ? Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
                      child: Text('No earlier Vocal chats yet.', style: HoolaType.small(c)),
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
                              decoration: BoxDecoration(color: crS(ch['id']) == current ? c.sunk : null, borderRadius: BorderRadius.circular(12)),
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
                                Text(crS(ch['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                                    style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                                if (vocalEpoch(ch['at']) > 0) Text(crWhen(vocalEpoch(ch['at'])), style: HoolaType.small(c).copyWith(fontSize: 12)),
                              ]),
                            ),
                          ),
                        ),
                    ]),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
              child: Text('Vocal chats stay out of your Hoola chats list. What you tell Hoola here still reaches your one memory.',
                  style: HoolaType.small(c)),
            ),
          ]),
        ),
      ),
    );
  }
}
