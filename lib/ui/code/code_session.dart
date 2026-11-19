// v0.921 HOOLA CODE NATIVE - one session (screens 2, 3, 4 and 6 of claude.ai/artifact/GF4AtP5MNfV8kARgTGymuh): her ask,
// Hoola's words in the reply serif, the real steps folded under "Worked for", the plan card that waits for her yes,
// the one question with choices, the pull request with its checks and Merge, and the typing box (a note while it
// works, her answer, her note with the plan, or a change on the same PR). Opening the PR, merging and a plan's start
// are her taps; the server re-checks every one.
// v0.935 HOOLA CODE FEED (owner, on the design canvas claude.ai/artifact/27Hw4XRUj5qG83sWaeX2J5 -> "GO"): the working row
// sits at the end of the thread like the Hoola chat (never pinned above the typing box), the newest steps show as light
// rows while it works and fold into one line when its words start, and Hoola's words land word by word at the Hoola
// chat's reading speed from the server's live stream ("live"), checked every second while it works.
import 'dart:async';

import 'package:flutter/material.dart';

import '../../state.dart';
import '../chat/hoola_md.dart';
import '../hoola_mark.dart';
import '../hoola_theme.dart';
import 'code_changes.dart';
import 'code_files.dart';
import 'code_home.dart';
import '../shell/hoola_quality.dart' show HoolaQualityRow;
import 'code_kit.dart';
import 'code_made.dart';
import 'code_vps.dart';
import 'code_start.dart';
import 'code_words.dart';

/// Her comments on lines of a change, kept per session until they go with her next message.
class CodeComments {
  static final Map<String, List<Map<String, dynamic>>> _by = {};
  static List<Map<String, dynamic>> of(String id) => _by.putIfAbsent(id, () => []);
  static void clear(String id) => _by.remove(id);
}

class CodeSessionPage extends StatefulWidget {
  const CodeSessionPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<CodeSessionPage> createState() => _CodeSessionPageState();
}

class _CodeSessionPageState extends State<CodeSessionPage> with WidgetsBindingObserver {
  Map<String, dynamic>? _t;
  Map<String, dynamic>? _merge;
  String? _error;
  bool _busy = false, _thinking = false, _lookedForMerge = false;
  String? _selecting;                 // v0.928 the message whose text she is selecting
  bool _away = false;                 // she scrolled up: the Newest arrow shows and nothing pulls her down
  int _seen = -1;                     // how many steps were drawn last time (new ones follow her to the end)
  Timer? _pollTimer, _tick;
  int _pollEvery = 0;                 // v0.935 1 s while it works, 10 s when it is quiet
  bool _loading = false;
  int _openN = -2;                    // v0.944 the newest step number when the page opened: older messages show at once
  String _explainSeen = '';           // v0.937 a closing answer that arrives while she watches lands like the rest
  int _lastN = -1;                    // v0.944 the newest step the phone holds: each check asks only for newer ones
  int _lastSayN = -1;                 // v0.944 the newest of Hoola's messages seen (its live words hand over to it)
  String _liveHead = '';              // v0.944 the start of the words being written now (a new reply starts from zero)
  int _fullAt = 0;                    // v0.944 when the whole session (diff, log) was last fetched
  String? _sent;                      // v0.940 her message just sent, shown until the server writes it into the thread
  int _sentAt = -1;                   // v0.945 the newest step number when she sent it
  bool _wantFull = false;             // v0.945 a whole fetch asked for while a check was running: it follows at once
  bool _resumed = false;              // v0.945 back from the background: what came meanwhile shows at once, not word by word
  bool _sentSeen = false;
  DateTime? _runSeen;                 // v0.937 the last check that said it works (a one-check gap never blinks the page)
  Map<String, dynamic> _runCarry = const {};
  final Map<String, int> _landed = {};   // v0.935 how many words of each new message have landed (key: n<step> / live / explain)
  // v0.962 the live stream (words pushed as Hoola writes them, like Claude Code): while it runs, the page reads its words
  // from here and asks the server for the whole session only when a step comes, or every 5 s as a safety net
  StreamSubscription<dynamic>? _liveSub;
  bool _streaming = false;
  String _streamLive = '';
  DateTime _loadedAt = DateTime(2000);
  final _msg = TextEditingController();
  final _focus = FocusNode();
  final _scroll = ScrollController();

  String get _base => '/api/devsahayak/tasks/${Uri.encodeComponent(widget.id)}';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _scroll.addListener(() {
      final away = _scroll.hasClients && _scroll.position.maxScrollExtent - _scroll.offset > 240;
      if (away != _away && mounted) setState(() => _away = away);
    });
    _load();
    _listen();
  }

  void _listen() {
    final api = widget.app.api;
    if (api == null || _liveSub != null) return;
    _liveSub = api.codeStream(widget.id).listen((ev) {
      if (!mounted) return;
      _streaming = true;
      _onLive(ev.kind, ev.payload);
    }, onDone: () {
      _streaming = false;                 // an older server, or the key refused: the page asks once a second again
      _liveSub = null;
    }, onError: (_) {});
  }

  void _unlisten() {
    _liveSub?.cancel();
    _liveSub = null;
    _streaming = false;
  }

  /// v0.962 one live event: the words grow as they are written (no 1 s bursts), the working row says the step working
  /// now, and a new step or a round starting / ending fetches only what is new.
  void _onLive(String kind, Map<String, dynamic> p) {
    if (kind != 'code_open' && kind != 'code_live') return;
    if (kind == 'code_open' || p.containsKey('live')) _streamLive = cs(p['live']);
    if (p.containsKey('add')) _streamLive += cs(p['add']);
    final t = _t;
    if (t == null) return;
    final writing = _streamLive.trim();
    if (writing.isNotEmpty && (_liveHead.isEmpty || !writing.startsWith(_liveHead))) {
      _landed['live'] = 0;                // a new reply: from its first word, under a fresh widget
      _keyOf['live'] = 'live${++_liveSeq}';
    }
    if (writing.isNotEmpty) _liveHead = writing.length > 24 ? writing.substring(0, 24) : writing;
    // the words just became a saved message: they stay on screen until the fetch brings that message (they vanished
    // for a moment and came back otherwise); the fetch then hands them over to it
    final cleared = writing.isEmpty && cs(t['live']).trim().isNotEmpty;
    final next = <String, dynamic>{...t, 'live': cleared ? t['live'] : _streamLive};
    if (p.containsKey('now')) next['now'] = p['now'];
    setState(() => _t = next);
    final n = p['n'];
    if (cleared || (n is num && n.toInt() > _lastN) || p.containsKey('running')) _load();
  }

  /// The once-a-second check; with the live stream on it only runs every 5 s (steps already fetch when they come).
  void _poll() {
    if (_streaming && DateTime.now().difference(_loadedAt) < const Duration(seconds: 5)) return;
    _load();
  }

  /// v0.957 ONE way the thread follows the newest words: after each layout, while she has not scrolled up, it sits at the
  /// true end - no 260 ms slide racing a snap (the plan card and the words above it shook between the two).
  bool _stickQueued = false;
  void _stick() {
    if (_away || _stickQueued) return;
    _stickQueued = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _stickQueued = false;
      if (!mounted || _away || !_scroll.hasClients) return;
      final p = _scroll.position;
      if (p.isScrollingNotifier.value) return;       // her finger or a fling: never pulled against it
      if ((p.maxScrollExtent - p.pixels).abs() > .5) _scroll.jumpTo(p.maxScrollExtent);
    });
  }

  bool _planOpen = false;             // v0.957 the plan dock above the typing box, folded to one line until she opens it

  void _toEnd({bool animate = true, int tries = 4}) {
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!_scroll.hasClients) return;
      final end = _scroll.position.maxScrollExtent;
      if (animate) {
        await _scroll.animateTo(end, duration: const Duration(milliseconds: 260), curve: Curves.easeOut);
      } else {
        _scroll.jumpTo(end);
      }
      // v0.945 the list builds lazily, so its true end is known only once the last rows are laid out: go again
      if (tries > 1 && mounted && _scroll.hasClients && _scroll.position.maxScrollExtent - _scroll.offset > 1) {
        _toEnd(animate: false, tries: tries - 1);
      }
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // v0.945 in the background the page stops asking every second; back on screen it reads the session whole once
    if (state == AppLifecycleState.paused || state == AppLifecycleState.hidden) {
      _pollTimer?.cancel();
      _pollTimer = null;
      _pollEvery = 0;
      _unlisten();
      _tick?.cancel();
      _tick = null;
    } else if (state == AppLifecycleState.resumed) {
      _resumed = true;
      _load(full: true);
      _listen();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _pollTimer?.cancel();
    _unlisten();
    _tick?.cancel();
    _msg.dispose();
    _focus.dispose();
    _scroll.dispose();
    super.dispose();
  }

  bool _live(Map<String, dynamic> t) => codeRunning(t) || const {'ci_running', 'new'}.contains(cs(t['status']));

  Future<void> _load({bool full = false, bool replace = false}) async {
    final api = widget.app.api;
    if (api == null) return;
    if (_loading) {
      if (full) _wantFull = true;                     // v0.945 never lost: it runs as soon as this check ends
      return;
    }
    _loading = true;
    _loadedAt = DateTime.now();
    try {
      // v0.944 a check asks only for the steps after the newest one it holds and leaves the diff / log out; the whole
      // session comes on open, after anything she does, every 30 s, and when a round finishes
      final prev = _t;
      final delta = !full && prev != null && _lastN >= 0 && DateTime.now().millisecondsSinceEpoch - _fullAt < 30000;
      var t = cm(await api.call('GET', _base, query: delta ? {'since': '$_lastN'} : null));
      if (!mounted) return;
      if (delta) {
        final old = prev!;
        final fresh = cl(t['steps']);
        if (ci(t['last_n']) < _lastN) {                 // the server's list went back (should not happen): read it whole
          _loading = false;
          return _load(full: true);
        }
        t = {
          ...old,                                       // v0.945 what a check leaves out (diff, log, working copy) stays
          ...t,
          'steps': [...cl(old['steps']), ...fresh.where((x) => _stepN(x, -1) > _lastN)],
        };
        if (codeRunning(old) && !codeRunning(t)) Future.microtask(() => _load(full: true));   // a round ended: the diff changed
      } else {
        _fullAt = DateTime.now().millisecondsSinceEpoch;
        if (prev != null && !replace) {
          // v0.945 a whole fetch never takes away a message she already saw (a long session folds old work steps on
          // the server): the steps she holds stay, in step order, and new ones join them
          final fresh = cl(t['steps']);
          final have = {for (final x in fresh) _stepN(x, -1)};
          t = {
            ...t,
            'steps': [...fresh, ...cl(prev['steps']).where((x) => !have.contains(_stepN(x, -1)))]
              ..sort((a, b) => _stepN(a, -1).compareTo(_stepN(b, -1))),
          };
        }
      }
      final allSteps = cl(t['steps']);
      if (allSteps.isNotEmpty) _lastN = _stepN(allSteps.last, allSteps.length - 1);
      // v0.937 a round ends and the next part starts (a CI look, the PR step) with a check or two between: the page
      // keeps its working look for 3 s instead of flashing "finished" and back
      if (codeRunning(t)) {
        _runSeen = DateTime.now();
        _runCarry = {'live': t['live'], 'now': t['now'], 'status': t['status']};
      } else if (_runSeen != null && DateTime.now().difference(_runSeen!) < const Duration(seconds: 3) &&
          cs(_runCarry['status']) == cs(t['status']) && cs(t['question']).isEmpty) {
        // v0.945 the words it was writing became a message already: they are not drawn a second time
        final says = cl(t['steps']).where((x) => cs(x['k']) == 'say').toList();
        final saved = says.isNotEmpty && _stepN(says.last, -1) > _lastSayN;
        t = {...t, 'running': true, 'live': saved ? '' : _runCarry['live'], 'now': _runCarry['now']};
      }
      // v0.962 with the live stream on, the words being written come from the stream only (a check that answers a
      // moment later never puts back older words under the ones already added)
      if (_streaming) t = {...t, 'live': _streamLive};
      final steps = cl(t['steps']);
      final n = steps.length;                 // v0.937 only new steps move the page; growing words follow on their own
      final first = _seen < 0;
      final writing = cs(t['live']).trim();
      if (first) {
        _openN = _lastN;
        _explainSeen = cs(t['explain']);
        _openExplain = cs(t['explain']);
        if (writing.isNotEmpty) _landed['live'] = _words(writing).length;   // opened mid-sentence: carry on from here
      } else {
        // v0.944 the words being written become a message: it carries on from the word it had reached
        // v0.964 one check can bring TWO new messages (the long one it was writing live + the closing answer): the
        // words already shown belong to the message that carries those words, never simply to the newest one (the
        // closing answer popped up whole and the long message above it started again from its first word)
        final fresh = steps.where((x) => cs(x['k']) == 'say' && _stepN(x, -1) > _lastSayN).toList();
        if (fresh.isNotEmpty && _landed.containsKey('live')) {
          final head = _liveHead.trim();
          final to = fresh.firstWhere((x) => head.isNotEmpty && cs(x['text']).trim().startsWith(head), orElse: () => fresh.first);
          final key = 'n${_stepN(to, -1)}';
          _landed[key] = _landed.remove('live')!;
          _keyOf[key] = _keyOf.remove('live') ?? 'live';   // v0.960 the same widget carries on
        }
        if (writing.isNotEmpty && (_liveHead.isEmpty || !writing.startsWith(_liveHead))) {
          _landed['live'] = 0;                                     // a new reply
          _keyOf['live'] = 'live${++_liveSeq}';
        }
        if (cs(t['explain']) != _explainSeen) {
          _explainSeen = cs(t['explain']);
          _landed.remove('explain');
        }
      }
      if (_resumed) {
        // v0.945 back from the background: what arrived meanwhile is shown whole, the page does not replay it
        _resumed = false;
        _openN = _lastN;
        _landed.clear();
        if (writing.isNotEmpty) _landed['live'] = _words(writing).length;
      }
      final says0 = steps.where((x) => cs(x['k']) == 'say').toList();
      _lastSayN = says0.isEmpty ? -1 : _stepN(says0.last, -1);
      _liveHead = writing.length > 24 ? writing.substring(0, 24) : writing;
      setState(() {
        _t = t;
        _error = null;
      });
      if (first || !_away) _stick();     // v0.957 new words follow her unless she scrolled up (one mechanism, no slide)
      _seen = n;
      final live = _live(t);
      final every = live ? 1 : 10;
      if (_pollEvery != every) {
        _pollTimer?.cancel();
        _pollTimer = Timer.periodic(Duration(seconds: every), (_) => _poll());
        _pollEvery = every;
      }
      if (live) {
        _tick ??= Timer.periodic(const Duration(seconds: 1), (_) {
          if (mounted) setState(() {});
        });
      } else {
        _tick?.cancel();
        _tick = null;
      }
      if (!_lookedForMerge && ci(t['pr_number']) != 0 && !codeRunning(t)) {
        _lookedForMerge = true;
        _findMerge(t);
      }
    } catch (e) {
      if (mounted && _t == null) setState(() => _error = '$e'.replaceFirst('Exception: ', ''));
    } finally {
      _loading = false;
      if (_wantFull && mounted) {
        _wantFull = false;
        Future.microtask(() => _load(full: true));
      }
    }
  }

  /// v0.944 a step's own number (older sessions: its place in the list).
  static int _stepN(Map<String, dynamic> s, int fallback) => s['n'] is num ? (s['n'] as num).toInt() : fallback;

  static List<String> _words(String text) => text.split(RegExp(r'(?<=\s)'));

  /// A landing message said how far it got: follow it to the end unless she scrolled up.
  void _landedTo(String i, int words) {
    final was = _landed[i] ?? 0;
    _landed[i] = words;
    // v0.957 a message finished landing: the next one waiting below it starts now
    if (was < (_landTotal[i] ?? 1 << 30) && words >= (_landTotal[i] ?? 1 << 30) && mounted) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) setState(() {});
      });
    }
    _stick();                           // v0.957 the same follow as everything else: after layout, never mid-scroll
  }

  /// A merge card she asked for earlier and has not answered is offered again.
  Future<void> _findMerge(Map<String, dynamic> t) async {
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/actions', quiet: true);
    for (final a in cl(r?['actions'])) {
      if (cs(a['kind']) == 'merge' && cs(a['status']) == 'waiting' && cs(a['repo']) == cs(t['repo']) && ci(a['pr_number']) == ci(t['pr_number'])) {
        if (mounted) setState(() => _merge = a);
        return;
      }
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    if (_busy) return null;
    setState(() => _busy = true);
    final r = await codeCall(context, widget.app, method, path, body: body);
    await _load(full: true);
    if (mounted) setState(() => _busy = false);
    return r;
  }

  bool _canRevise(Map<String, dynamic> t) => codeCanRevise.contains(cs(t['status'])) || t['can_continue'] == true;

  /// note | answer | plan | revise | off
  String _mode(Map<String, dynamic> t) {
    if (codeRunning(t)) return 'note';
    if (cs(t['question']).isNotEmpty) return 'answer';
    if (cs(t['status']) == 'plan_wait') return 'plan';
    if (_canRevise(t)) return 'revise';
    return 'off';
  }

  Future<void> _send([String? words]) async {
    final t = _t;
    if (t == null) return;
    final mode = _mode(t);
    final text = (words ?? _msg.text).trim();
    final comments = (mode == 'note' || mode == 'revise') ? CodeComments.of(widget.id) : const <Map<String, dynamic>>[];
    if (mode == 'off' || (text.isEmpty && comments.isEmpty && mode != 'plan')) return;
    if (text.isNotEmpty && mode != 'plan') {
      setState(() {
        _sent = text;
        _sentAt = _lastN;                             // v0.945 by step number, not by place in the list
        _away = false;
      });
      if (words == null) _msg.clear();
      _stick();
    }
    final r = switch (mode) {
      'note' => await _run('POST', '$_base/note', {'text': text, 'comments': comments}),
      'answer' => await _run('POST', '$_base/answer', {'text': text}),
      'plan' => await _run('POST', '$_base/bg/plan_ok', {'hash': cs(t['hash']), 'note': text}),
      _ => await _run('POST', '$_base/bg/revise', {'text': text, 'comments': comments}),
    };
    if (r != null) {
      if (comments.isNotEmpty) CodeComments.clear(widget.id);
      if (words == null) _msg.clear();
    } else if (_sent == text && mounted) {
      setState(() => _sent = null);     // it did not go: her words go back into the box
      if (words == null && _msg.text.isEmpty) _msg.text = text;
    }
  }

  Future<void> _askMerge() async {
    final r = await _run('POST', '$_base/merge_request', const <String, dynamic>{});
    if (r != null && cs(r['id']).isNotEmpty && mounted) {
      setState(() => _merge = r);
      _decideMerge();
    }
  }

  Future<void> _decideMerge() async {
    final a = _merge;
    if (a == null) return;
    final c = HoolaColors.of(context);
    final force = a['needs_force'] == true;
    final reason = TextEditingController();
    final yes = await codeSheet<bool>(context, widget.app,
        title: 'Merge pull request #${ci(a['pr_number'])}?',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('${cs(a['method']).isEmpty ? 'Squash' : cs(a['method'])} into ${cs(a['base']).isEmpty ? 'main' : cs(a['base'])} · commit ${cs(a['head_sha'])}',
                  style: codeMono(c, size: 12.5, color: c.ink2)),
              const SizedBox(height: 8),
              Text(cs(cm(a['ci'])['say']).isNotEmpty ? cs(cm(a['ci'])['say']) : 'CI: ${cs(a['ci_state']).isEmpty ? 'none' : cs(a['ci_state'])}',
                  style: codeSans(c, size: 14, color: force ? c.bad : c.ink)),
              for (final n in ((a['notes'] as List?) ?? const [])) Text('• $n', style: codeSans(c, size: 13, color: c.warn)),
              const SizedBox(height: 12),
              if (force) CodeField(controller: reason, label: 'Why merge anyway? (at least 8 letters)', lines: 2),
              Row(children: [
                Expanded(child: CodeOutline('Not now', onTap: () => Navigator.pop(ctx, false))),
                const SizedBox(width: 10),
                Expanded(flex: 2, child: CodeMain(force ? 'Merge anyway' : 'Yes, merge', icon: Icons.merge_rounded, onTap: () => Navigator.pop(ctx, true))),
              ]),
            ]));
    if (yes == null || !mounted) {
      reason.dispose();
      return;
    }
    if (yes && force && reason.text.trim().length < 8) {
      codeToast(context, 'A reason of at least 8 letters is needed.');
      reason.dispose();
      return;
    }
    final r = await _run('POST', '/api/devsahayak/actions/${Uri.encodeComponent(cs(a['id']))}/decide',
        {'yes': yes, 'hash': cs(a['hash']), if (yes && force) 'force_reason': reason.text.trim()});
    reason.dispose();
    if (mounted) setState(() => _merge = (r != null && cs(r['status']) == 'waiting') ? r : null);
  }

  Future<void> _more() async {
    final t = _t;
    if (t == null) return;
    final c = HoolaColors.of(context);
    final cps = cl(cm(t['ws'])['checkpoints']);
    Widget row(BuildContext ctx, IconData icon, String label, String id, {Color? color}) => InkWell(
          onTap: () => Navigator.pop(ctx, id),
          child: Container(
            constraints: const BoxConstraints(minHeight: 52),
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Row(children: [
              Icon(icon, size: 21, color: color ?? c.ink),
              const SizedBox(width: 14),
              Expanded(child: Text(label, style: codeSans(c, size: 15.5, color: color ?? c.ink))),
            ]),
          ),
        );
    final pick = await codeSheet<String>(context, widget.app,
        title: codeTitle(t),
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              if (codeRunning(t)) row(ctx, Icons.stop_circle_outlined, 'Stop after this step', 'stop', color: c.bad),
              row(ctx, Icons.psychology_outlined, _thinking ? 'Hide what Hoola thought' : 'Show what Hoola thought', 'think'),
              if (cl(t['files']).isNotEmpty) row(ctx, Icons.difference_outlined, 'See the changes', 'changes'),
              if ((t['ws'] as Map?)?['exists'] == true) row(ctx, Icons.folder_open_outlined, 'Browse the files', 'files'),
              if (cs(t['pr_url']).isNotEmpty) row(ctx, Icons.open_in_new_rounded, 'Open on GitHub', 'github'),
              if (!codeRunning(t) && cps.length > 1) row(ctx, Icons.undo_rounded, 'Go back to an earlier checkpoint', 'rewind'),
              if (cs(t['status']) == 'plan_wait') row(ctx, Icons.close_rounded, 'Cancel this job', 'cancel'),
              row(ctx, Icons.add_rounded, 'New session', 'new'),
              row(ctx, Icons.archive_outlined, t['archived'] == true ? 'Bring back from the archive' : 'Archive', 'archive'),
              row(ctx, Icons.delete_outline_rounded, 'Delete session', 'delete', color: c.bad),
            ]));
    if (!mounted || pick == null) return;
    switch (pick) {
      case 'stop':
        _run('POST', '$_base/stop');
      case 'think':
        setState(() => _thinking = !_thinking);
      case 'changes':
        _changes();
      case 'files':
        _files();
      case 'github':
        codeOpenGithub(cs(t['pr_url']));
      case 'rewind':
        _rewind(cps);
      case 'cancel':
        _run('POST', '$_base/cancel');
      case 'new':
        showCodeNewSession(context, widget.app, onStarted: (id) {
          Navigator.of(context).pushReplacement(MaterialPageRoute<void>(
              builder: (_) => HoolaTheme(appearance: widget.app.appearance, child: CodeSessionPage(app: widget.app, id: id))));
        });
      case 'archive':
        _run('PATCH', _base, {'archived': t['archived'] != true});
      case 'delete':
        await _delete();
    }
  }

  Future<void> _delete() async {
    {
        final ok = await codeSheet<bool>(context, widget.app,
            title: 'Delete this session?',
            body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Text('Its steps and working copy go. A pull request on GitHub stays as it is.', style: codeSans(HoolaColors.of(ctx), color: HoolaColors.of(ctx).ink2)),
                  const SizedBox(height: 14),
                  Row(children: [
                    Expanded(child: CodeOutline('Keep', onTap: () => Navigator.pop(ctx, false))),
                    const SizedBox(width: 10),
                    Expanded(child: CodeMain('Delete', onTap: () => Navigator.pop(ctx, true))),
                  ]),
                ]));
        if (ok == true && mounted) {
          final r = await codeCall(context, widget.app, 'DELETE', _base);
          if (r != null && mounted) Navigator.of(context).maybePop();
        }
    }
  }

  Future<void> _rewind(List<Map<String, dynamic>> cps) async {
    final n = await codeSheet<int>(context, widget.app,
        title: 'Go back to a checkpoint',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('The working copy and the conversation go back to how they were then.', style: codeSans(HoolaColors.of(ctx), size: 13.5, color: HoolaColors.of(ctx).ink2)),
              const SizedBox(height: 10),
              for (final cp in cps.reversed.take(8))
                CodeChoiceRow(label: 'Checkpoint ${ci(cp['n'])}', sub: cs(cp['label']), on: false, onTap: () => Navigator.pop(ctx, ci(cp['n']))),
            ]));
    if (n != null && n > 0) _run('POST', '$_base/rewind', {'n': n});
  }

  // v0.943 her own look at the working copy; picked lines come back quoted into her next message
  Future<void> _files() async {
    final quote = await Navigator.of(context).push<String>(MaterialPageRoute<String>(
        builder: (_) => HoolaTheme(appearance: widget.app.appearance, child: CodeFilesPage(app: widget.app, id: widget.id))));
    if (!mounted || quote == null || quote.isEmpty) return;
    final cur = _msg.text.trim();
    _msg.text = cur.isEmpty ? quote : '$cur\n\n$quote';
    _msg.selection = TextSelection.collapsed(offset: _msg.text.length);
    setState(() {});
  }

  Future<void> _changes() async {
    await _load(full: true);                          // v0.944 checks leave the diff out: fetch it before showing it
    final t = _t;
    if (t == null) return;
    final send = await Navigator.of(context).push<bool>(MaterialPageRoute<bool>(
        builder: (_) => HoolaTheme(appearance: widget.app.appearance, child: CodeChangesPage(app: widget.app, task: t))));
    if (!mounted) return;
    setState(() {});
    if (send == true) _send('');
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final t = _t;
    final (a, r) = t == null ? (0, 0) : codeStat(t);
    final madeN = t == null ? 0 : cl(t['made']).length;
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          CodeTopBar(
            centered: true,
            line: false,
            title: t == null ? 'Hoola Code' : codeTitle(t),
            sub: t == null ? '' : [cRepoShort(cs(t['repo'])), _envName(t)].where((e) => e.isNotEmpty).join(' · '),
            actions: [
              if (t != null && codeRunning(t))
                Semantics(label: 'Hoola is working', child: const SizedBox(width: 44, height: 44, child: Center(child: CodeRing(size: 20))))
              else
                const SizedBox(width: 44),
              CodeIconButton(icon: Icons.more_vert_rounded, label: 'Session menu', onTap: t == null ? null : _more),
            ],
          ),
          Expanded(
            child: t == null
                ? Center(
                    child: _error == null
                        ? const CodeRing(size: 22)
                        : Padding(padding: const EdgeInsets.all(24), child: Text(_error!, textAlign: TextAlign.center, style: codeSans(c, color: c.ink2))))
                : RefreshIndicator(
                    onRefresh: () => _load(full: true, replace: true),
                    color: c.ink,
                    child: Stack(fit: StackFit.expand, children: [
                      Builder(builder: (_) {
                        // v0.945 a long session lays out only the rows on screen
                        final rows = _body(c, t);
                        // v0.957 a row with a key (the words landing now, the working row) keeps its state when a row
                        // above it comes or goes - it was rebuilt from scratch, so its fade and turning mark restarted
                        final at = <Key, int>{for (var i = 0; i < rows.length; i++) if (rows[i].key != null) rows[i].key!: i};
                        _stick();
                        return NotificationListener<ScrollMetricsNotification>(
                          onNotification: (_) {
                            _stick();                 // the thread grew (a word wrapped, a row came): stay at the end
                            return false;
                          },
                          child: ListView.builder(
                              controller: _scroll,
                              padding: EdgeInsets.fromLTRB(20, 16, 20, a + r > 0 || madeN > 0 ? 76 : 24),
                              itemCount: rows.length,
                              findChildIndexCallback: (k) => at[k],
                              itemBuilder: (_, i) => rows[i]),
                        );
                      }),
                      if (_away || a + r > 0 || madeN > 0)
                        Positioned(
                          bottom: 12,
                          left: 0,
                          right: 0,
                          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                            if (_away) CodeNewestButton(onTap: () => _toEnd()),
                            if (_away && a + r > 0) const SizedBox(width: 10),
                            if (a + r > 0) _changesPill(c, a, r),
                            if ((_away || a + r > 0) && madeN > 0) const SizedBox(width: 10),
                            if (madeN > 0) _madePill(c, cl(t['made'])),
                          ]),
                        ),
                      if (_selecting != null)
                        Positioned(
                          top: 8,
                          right: 12,
                          child: CodeChip('Done selecting', icon: Icons.check_rounded, onTap: () => setState(() => _selecting = null)),
                        ),
                    ]),
                  ),
          ),
          if (t != null && _todoItems(t).isNotEmpty) _planDock(c, _todoItems(t)),
          if (t != null) _composer(c, t),
        ]),
      ),
    );
  }

  // ---------------------------------------------------------------------------------------------- the thread
  List<Widget> _body(HoolaColors c, Map<String, dynamic> t) {
    final steps = cl(t['steps']);
    _sentSeen = false;
    _landBusy = false;
    final running = codeRunning(t);
    final st = cs(t['status']);
    final out = <Widget>[_her(c, cs(t['text']), cl(t['attach']))];
    // v0.935 the words Hoola is writing right now (the server's live stream), unless they are already a step
    var live = running ? cs(t['live']).trim() : '';
    final newestSay = steps.lastWhere((s) => cs(s['k']) == 'say', orElse: () => const <String, dynamic>{});
    if (live.isNotEmpty && cs(newestSay['text']).trim().startsWith(live)) live = '';   // already a step: drawn once
    // the steps between Hoola's words: the newest show as light rows while it works, the rest fold into one line
    final group = <Map<String, dynamic>>[];
    var lastSay = -1;
    var hasFinal = false;
    for (var i = 0; i < steps.length; i++) {
      if (cs(steps[i]['k']) == 'say') lastSay = i;
      if (steps[i]['final'] == true) hasFinal = true;
    }
    final question = cs(t['question']).trim();
    var si = -1;
    // v0.939 the things it made: the full card sits with each thing's newest version, earlier versions are one faint line
    final made = {for (final m in cl(t['made'])) cs(m['id']): m};
    final lastOf = <String, int>{};
    var lastMade = -1;
    for (var i = 0; i < steps.length; i++) {
      if (cs(steps[i]['k']) == 'made') {
        lastOf[cs(steps[i]['id'])] = i;
        lastMade = i;
      }
    }
    var nowGroup = const <Map<String, dynamic>>[];
    void flush({required bool last}) {
      if (group.isEmpty) return;
      // v0.957 the part working now folds into the ONE working row at the very end (drawn below); with words streaming
      // it is a faint line where it will stay once those words are saved, so nothing moves when they are
      if (running && last && live.isEmpty) {
        nowGroup = List.of(group);
      } else {
        out.add(_group(c, List.of(group)));
      }
      group.clear();
    }

    // v0.945 what a "go back to a checkpoint" undid stays readable but greyed out
    final undone = <(int, int)>[
      for (final s in steps)
        if (cs(s['k']) == 'rewind' && ci(s['from']) >= 0 && s.containsKey('from')) (ci(s['from']), _stepN(s, -1)),
    ];
    var dimFrom = out.length;
    var dimOn = false;
    void dimEnd() {
      if (!dimOn) return;
      for (var j = dimFrom; j < out.length; j++) {
        out[j] = Opacity(opacity: .45, child: out[j]);
      }
    }

    for (final s in steps) {
      si++;
      final k = cs(s['k']);
      final sn0 = _stepN(s, si);
      // v0.964 everything after a message that is still landing waits for it (in order, like Claude Code): a newer
      // message, the step rows and the "Worked for" line no longer show before the words above them have landed
      if (_landBusy && _openN > -2 && sn0 > _openN && !_away) break;
      final u = undone.any((r) => sn0 > r.$1 && sn0 < r.$2);
      if (u != dimOn) {
        flush(last: false);
        dimEnd();
        dimFrom = out.length;
        dimOn = u;
      }
      if (k == 'say') {
        flush(last: false);
        final text = cs(s['text']);
        final sn = _stepN(s, si);
        // v0.944 the question card already shows this question: the message is not drawn twice
        if (s['final'] == true && question.isNotEmpty && text.trim() == question && si == lastSay) continue;
        final actions = si == lastSay && !running;
        final key = 'n$sn';
        out.add(_openN > -2 && sn > _openN && (_landed[key] ?? 0) < _words(text).length
            ? _land(text, key, done: true, actions: actions)
            : _reply(text, 'say$sn', actions: actions));
      } else if (k == 'round') {
        // v0.944 where one piece of work ended: "Worked for 3m 12s", like Claude Code
        flush(last: false);
        out.add(_roundLine(c, cs(s['text']).isNotEmpty ? cs(s['text']) : 'Worked for ${codeClock(ci(s['secs']))}'));
      } else if (k == 'made') {
        final row = made[cs(s['id'])];
        if (row != null) {
          flush(last: false);
          out.add(lastOf[cs(s['id'])] == si
              ? CodeMadeCard(
                  key: ValueKey('made${cs(s['id'])}'),
                  row: row,
                  newest: si == lastMade,
                  onOpen: () => _openMade(row),
                  onShare: () => codeMadeShare(context, widget.app, widget.id, row))
              : CodeMadeEarlier(
                  key: ValueKey('made${cs(s['id'])}v${ci(s['v'])}'),
                  title: cs(row['title']),
                  v: ci(s['v']),
                  onOpen: () => _openMade(row, version: ci(s['v']))));
        }
      } else if (k == 'server') {
        // v0.941 a command on her own server: a waiting one shows the approval card; a refused one says so
        if (cs(s['state']) == 'waiting' || cs(s['state']) == 'refused') {
          flush(last: false);
          out.add(Padding(
              padding: const EdgeInsets.only(top: 10),
              child: CodeServerCard(key: ValueKey('srv${cs(s['id'])}${cs(s['state'])}${_stepN(s, si)}'), app: widget.app, step: s)));
        } else {
          group.add(s);
        }
      } else if (k == 'look') {
        // v0.943 the page Hoola opened in a real browser to check its own change
        flush(last: false);
        out.add(Padding(
            padding: const EdgeInsets.only(top: 10),
            child: CodeLookCard(key: ValueKey('look${_stepN(s, si)}'), app: widget.app, id: widget.id, step: s)));
      } else if (k == 'note') {
        flush(last: false);
        // v0.940 every message she sends after the first is HER message, drawn like the first one
        out.add(Padding(padding: const EdgeInsets.only(top: 18), child: _her(c, cs(s['text']), const [], key: 'note${_stepN(s, si)}')));
        if (_sent != null && _stepN(s, si) > _sentAt && _same(cs(s['text']), _sent!)) _sentSeen = true;
      } else if (k == 'todo') {
        // v0.957 the plan shows in the dock above the typing box (_planDock), never in the thread
      } else if (k == 'think') {
        if (_thinking) group.add(s);
      } else {
        group.add(s);
      }
    }
    flush(last: true);
    dimEnd();
    if (!running && cl(t['risky_files']).isNotEmpty) out.add(CodeRiskyNote(files: cl(t['risky_files'])));
    if (live.isNotEmpty) out.add(_land(live, 'live', done: false));
    // v0.957 the plan is the dock above the typing box, not a 300 px card at the end of the thread that every new word
    // and every coming and going of the working row pushed up and down
    final queued = [for (final n in running ? ((t['notes'] as List?) ?? const []) : const []) if (cs(n).isNotEmpty) cs(n)];
    for (final n in queued) {
      if (_sent != null && _same(n, _sent!)) _sentSeen = true;
      out.add(_herWaiting(c, n, 'Hoola reads it at its next step'));
    }
    // v0.940 what she just sent shows at once, before the server has written it down
    if (_sent != null && !_sentSeen) out.add(_herWaiting(c, _sent!, 'Sending…'));
    if (_sentSeen) _sent = null;
    if (!running && !(_landBusy && !_away)) {
      // v0.964 the question / PR / ready cards wait until the closing words above them have landed
      // v0.944 older sessions keep their closing answer only on the session: shown when no message carries it
      final ex = cs(t['explain']).trim();
      final lastText = lastSay < 0 ? '' : cs(steps[lastSay]['text']).trim();
      if (!hasFinal && ex.isNotEmpty && ex != lastText && ex != question) {
        out.add(_seen >= 0 && _explainSeen.isNotEmpty && !_explainAtOpenSeen && (_landed['explain'] ?? 0) < _words(ex).length
            ? _land(ex, 'explain', done: true, actions: true)     // v0.937 it lands, it does not appear at once
            : _reply(ex, 'explain', actions: true));
      }
      if (st == 'plan_wait' && cm(t['plan']).isNotEmpty) out.add(_plan(c, t));
      if (cs(t['question']).isNotEmpty) out.addAll(_question(c, t));
      if ((st == 'failed' || st == 'refused') && cs(t['error']).isNotEmpty) {
        out.add(Padding(
          padding: const EdgeInsets.only(top: 14),
          child: CodeCard(
            edge: c.bad,
            child: Text('${st == 'refused' ? 'A safety rule stopped this change.' : 'It could not finish.'} ${cs(t['error'])}', style: codeSans(c, size: 14.5)),
          ),
        ));
      }
      if (st == 'ready' && cs(t['hash']).isNotEmpty) out.add(_ready(c, t));
      if (ci(t['pr_number']) != 0) out.add(_pr(c, t));
    }
    // v0.957 the working row stays at the end the whole time it works - also while its words stream (it vanished then
    // and came back, 44 px each time, which shook everything under it)
    if (running) out.add(_runningRow(c, t, nowGroup));
    return out;
  }

  bool get _explainAtOpenSeen => _openExplain == cs(_t?['explain']) && _openExplain.isNotEmpty;
  String _openExplain = '';

  Widget _roundLine(HoolaColors c, String text) => Padding(
        padding: const EdgeInsets.only(top: 6, bottom: 2),
        child: Row(children: [
          Expanded(child: Divider(color: c.line, height: 1)),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Text(text, style: codeSans(c, size: 12.5, color: c.ink3).copyWith(fontFeatures: const [FontFeature.tabularFigures()])),
          ),
          Expanded(child: Divider(color: c.line, height: 1)),
        ]),
      );

  bool _same(String a, String b) {
    String k(String x) => x.trim().replaceAll(RegExp(r'\s+'), ' ');
    final x = k(a), y = k(b);
    if (x.isEmpty || y.isEmpty) return false;
    final n = x.length < y.length ? x.length : y.length;
    return x.substring(0, n > 80 ? 80 : n) == y.substring(0, n > 80 ? 80 : n);
  }

  Widget _herWaiting(HoolaColors c, String text, String note) => Padding(
        padding: const EdgeInsets.only(top: 18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Opacity(opacity: .72, child: _her(c, text, const [], key: 'wait${text.hashCode}')),
          Padding(padding: const EdgeInsets.only(top: 4, right: 4), child: Text(note, style: codeSans(c, size: 12, color: c.ink3))),
        ]),
      );

  /// v0.939 a thing it made, full screen; a change she asks for there goes to Hoola as her next message.
  Future<void> _openMade(Map<String, dynamic> row, {int version = 0}) async {
    final ask = await Navigator.of(context).push<String>(MaterialPageRoute(
        builder: (_) => HoolaTheme(
            appearance: widget.app.appearance,
            child: CodeMadeViewer(app: widget.app, taskId: widget.id, madeId: cs(row['id']), version: version))));
    if (ask == null || ask.trim().isEmpty || !mounted) return;
    await _send('Change the ${cs(row['kind_label']).toLowerCase()} "${cs(row['title'])}" (make id ${cs(row['id'])}): ${ask.trim()}');
  }

  Widget _madePill(HoolaColors c, List<Map<String, dynamic>> made) => Semantics(
        button: true,
        label: '${cPlural(made.length, 'thing')} made in this session',
        child: Material(
          color: c.surface,
          shape: StadiumBorder(side: BorderSide(color: c.lineStrong)),
          child: InkWell(
            customBorder: const StadiumBorder(),
            onTap: () => showCodeMadeList(context, widget.app, widget.id, made, onOpen: (r) => _openMade(r)),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.layers_outlined, size: 16, color: c.ink2),
                const SizedBox(width: 6),
                Text('${made.length} made', style: codeSans(c, size: 13, weight: FontWeight.w500)),
              ]),
            ),
          ),
        ),
      );

  /// v0.935 a new message of Hoola's landing word by word (done = the whole message is here; else it is still being
  /// written and more words come with the next check).
  Widget _land(String text, String i, {required bool done, bool actions = false}) {
    // v0.957 one message lands at a time, in order: a newer one waits until the one above it has fully landed (two
    // places growing at once made the page jump between them)
    final total = _words(text).length;
    _landTotal[i] = total;
    final hold = _landBusy;
    if ((_landed[i] ?? 0) < total) _landBusy = true;
    return CodeLanding(
        // v0.960 the same widget carries on when the words being written become a saved message (its key moves with
        // them): it was rebuilt from scratch at that moment, so the newest words flashed to full ink and the size reset
        key: ValueKey('land${_keyOf[i] ?? i}'),
        text: text,
        from: _landed[i] ?? 0,
        done: done,
        hold: hold,
        onLanded: (n) => _landedTo(i, n),
        // v0.960 a new line grows in over a moment instead of pushing everything under it down a whole line at once;
        // the thread follows it frame by frame (ScrollMetricsNotification -> _stick), so the page glides
        builder: (shown, streaming, tail) => AnimatedSize(
          duration: HoolaMotion.of(context, const Duration(milliseconds: 180)),
          curve: Curves.easeOutCubic,
          alignment: Alignment.topCenter,
          child: CodeReply(
            app: widget.app,
            text: shown,
            streaming: streaming,
            tail: tail,
            actions: actions && !streaming,
            selecting: _selecting == 'land$i',
            onQuote: _mode(_t ?? const {}) == 'off' ? null : (q) => codeQuoteInto(_msg, _focus, q),
            onSelect: () => setState(() => _selecting = 'land$i'),
          ),
        ),
      );
  }

  final Map<String, String> _keyOf = {};  // v0.960 landing -> its widget's id, kept when live words become a message
  int _liveSeq = 0;

  final Map<String, int> _landTotal = {};
  bool _landBusy = false;               // set while the thread is built: a message above is still landing

  /// v0.936 the step running now, Claude Code's way: >_ and what it is doing in her words (never the raw command) in a
  /// soft moving light, the clock on the right; a tap opens the steps of this part.
  Widget _runningRow(HoolaColors c, Map<String, dynamic> t, List<Map<String, dynamic>> g) {
    final steps = cl(t['steps']);
    final label = t['stopping'] == true
        ? 'Stopping after this step'
        : cs(t['now']).isNotEmpty
            ? cs(t['now'])
            : steps.isEmpty
                ? 'Starting'
                : _nowWords(steps.last);
    final secs = DateTime.now().difference(codeTime(cs(t['run_at']).isEmpty ? cs(t['at']) : cs(t['run_at'])) ?? DateTime.now()).inSeconds;
    return Padding(
      key: const ValueKey('working'),       // v0.937 one working row that keeps its turning mark between checks
      padding: const EdgeInsets.only(top: 6),
      child: Semantics(
        liveRegion: true,
        button: g.isNotEmpty,
        label: 'Hoola is working: $label',
        excludeSemantics: true,
        child: InkWell(
          onTap: g.isEmpty ? null : () => _openSteps(_summary(g), g),
          borderRadius: BorderRadius.circular(12),
          child: Container(
            constraints: const BoxConstraints(minHeight: 44),
            child: Row(children: [
              const HoolaMark(size: 22),   // v0.937 the Hoola mark, turning, like the Hoola chat's working row
              const SizedBox(width: 10),
              Flexible(                              // v0.938 the words and the clock sit together, not at the far edge
                child: AnimatedSwitcher(
                  duration: HoolaMotion.of(context, HoolaMotion.fade),
                  layoutBuilder: (cur, prev) => Stack(alignment: Alignment.centerLeft, children: [...prev, if (cur != null) cur]),
                  child: CodeShimmer(label, key: ValueKey(label), style: codeSans(c, size: 16, color: c.ink2)),
                ),
              ),
              const SizedBox(width: 8),
              Text('· ${codeClock(secs)}',              // v0.938 same sans and size as the words beside it
                  style: codeSans(c, size: 16, color: c.ink3).copyWith(fontFeatures: const [FontFeature.tabularFigures()])),
            ]),
          ),
        ),
      ),
    );
  }

  /// v0.936 "Changes +12 −3", floating above the typing box: opens the change.
  Widget _changesPill(HoolaColors c, int a, int r) => Semantics(
        button: true,
        label: 'Changes: $a lines added, $r removed',
        excludeSemantics: true,
        child: Material(
          color: c.surface,
          shape: StadiumBorder(side: BorderSide(color: c.lineStrong)),
          elevation: 2,
          child: InkWell(
            customBorder: const StadiumBorder(),
            onTap: _changes,
            child: Container(
              height: 44,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text('Changes', style: codeSans(c, size: 15, weight: FontWeight.w500)),
                const SizedBox(width: 8),
                CodeStat(a, r, size: 13),
              ]),
            ),
          ),
        ),
      );

  /// v0.928 Hoola's words like a Hoola chat reply (renderer, long-press sheet, Copy · Read aloud · Share on the newest).
  Widget _reply(String text, String key, {bool actions = false}) => CodeReply(
        app: widget.app,
        text: text,
        actions: actions,
        selecting: _selecting == key,
        onQuote: _mode(_t ?? const {}) == 'off' ? null : (q) => codeQuoteInto(_msg, _focus, q),
        onSelect: () => setState(() => _selecting = key),
      );

  void _herMenu(String text, String key) => codeMessageMenu(context, widget.app, text,
      mine: true,
      onQuote: _mode(_t ?? const {}) == 'off' ? null : () => codeQuoteInto(_msg, _focus, text),
      onEdit: _mode(_t ?? const {}) == 'off'
          ? null
          : () {
              _msg.text = text;
              _msg.selection = TextSelection.collapsed(offset: text.length);
              _focus.requestFocus();
            },
      onSelect: () => setState(() => _selecting = key));

  Widget _her(HoolaColors c, String text, List<Map<String, dynamic>> attach, {bool small = false, String key = 'ask'}) => Padding(
        padding: EdgeInsets.only(top: small ? 12 : 0, left: 48),
        child: Align(
          alignment: Alignment.centerRight,
          child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            if (attach.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Wrap(spacing: 6, runSpacing: 6, alignment: WrapAlignment.end, children: [
                  for (final x in attach)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(10), border: Border.all(color: c.line)),
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        Icon(cs(x['kind']) == 'image' ? Icons.image_outlined : Icons.description_outlined, size: 15, color: c.ink2),
                        const SizedBox(width: 6),
                        Text(cs(x['name']), style: codeMono(c, size: 12)),
                      ]),
                    ),
                ]),
              ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: c.sunk,
                borderRadius: BorderRadius.circular(20),
              ),
              child: _selecting == key
                  ? SelectableText(text, style: codeSans(c, size: small ? 15.5 : 17, height: 1.45))
                  : GestureDetector(
                      onLongPress: () => _herMenu(text, key),
                      child: Text(text, style: codeSans(c, size: small ? 15.5 : 17, height: 1.45)),
                    ),
            ),
          ]),
        ),
      );

  /// v0.936 one part of the work between two of Hoola's messages = ONE faint line ("Ran 3 commands", "Searched the
  /// code, read 2 files", "Edited LoginActivity.java +12 −3"), no icon, no box; a tap opens the steps inside it.
  Widget _group(HoolaColors c, List<Map<String, dynamic>> g) {
    final label = _summary(g);
    var add = 0, rem = 0;
    for (final s in g) {
      if (const {'edit', 'new'}.contains(cs(s['k']))) {
        add += ci(s['added']);
        rem += ci(s['removed']);
      }
    }
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Align(
        alignment: Alignment.centerLeft,
        child: Semantics(
          button: true,
          label: '$label. Show the steps',
          excludeSemantics: true,
          child: InkWell(
            onTap: () => _openSteps(label, g),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              constraints: const BoxConstraints(minHeight: 44),
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Flexible(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 16, color: c.ink3))),
                if (add + rem > 0) ...[const SizedBox(width: 8), CodeStat(add, rem, size: 12)],
                const SizedBox(width: 4),
                Icon(Icons.chevron_right_rounded, size: 18, color: c.ink3),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  /// What a part of the work did, in her words.
  String _summary(List<Map<String, dynamic>> g) {
    int n(Set<String> ks) => g.where((s) => ks.contains(cs(s['k']))).length;
    final edits = g.where((s) => const {'edit', 'new'}.contains(cs(s['k']))).map((s) => cs(s['path']).split('/').last).toSet().toList();
    final parts = <String>[
      if (n({'search', 'grep', 'usages'}) > 0) 'searched the code',
      if (n({'read'}) > 0) 'read ${cPlural(n({'read'}), 'file')}',
      if (n({'list'}) > 0) 'looked in ${cPlural(n({'list'}), 'folder')}',
      if (n({'bash'}) > 0) 'ran ${cPlural(n({'bash'}), 'command')}',
      if (n({'check'}) > 0) 'ran your tests',
      if (edits.length == 1) 'edited ${edits.first}' else if (edits.length > 1) 'edited ${cPlural(edits.length, 'file')}',
      if (n({'agent'}) > 0) 'asked ${cPlural(n({'agent'}), 'helper')}',
    ];
    if (parts.isEmpty) return _passTitle(g);
    final line = parts.take(3).join(', ');
    return line[0].toUpperCase() + line.substring(1);
  }

  /// The steps inside one line, as a sheet (Claude Code's "Ran 3 commands"): one row each, what it did in plain words;
  /// the command, its output and the lines of an edit only after a tap on that row.
  void _openSteps(String title, List<Map<String, dynamic>> g) {
    final rows = [for (final s in g) if (!const {'think', 'ckpt', 'todo'}.contains(cs(s['k']))) s];
    if (rows.isEmpty) return;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      backgroundColor: HoolaColors.of(context).surface,
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: .6,
        maxChildSize: .92,
        builder: (ctx, scroll) => CodeStepsSheet(title: title, steps: rows, scroll: scroll, fallback: (s) => _step(HoolaColors.of(ctx), s)),
      ),
    );
  }

  Widget _line(HoolaColors c, IconData icon, List<InlineSpan> spans, {Color? iconColor, Widget? trailing, bool live = false}) => Container(
        constraints: const BoxConstraints(minHeight: 30),
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
          SizedBox(width: 18, child: live ? const CodeRing(size: 14) : Icon(icon, size: 16, color: iconColor ?? c.ink3)),
          const SizedBox(width: 10),
          Expanded(child: Text.rich(TextSpan(style: codeSans(c, size: 14, color: c.ink2, height: 1.35), children: spans))),
          if (trailing != null) ...[const SizedBox(width: 8), trailing],
        ]),
      );

  TextSpan _code(HoolaColors c, String s) => TextSpan(text: s, style: codeMono(c, size: 13, color: c.ink));

  Widget? _step(HoolaColors c, Map<String, dynamic> s) {
    final k = cs(s['k']);
    switch (k) {
      case 'rules':
        return _line(c, Icons.rule_rounded, [const TextSpan(text: "Read the repo's own rules")]);
      case 'read':
        return _line(c, Icons.description_outlined, [const TextSpan(text: 'Read '), _code(c, cs(s['path']))]);
      case 'search':
        return _line(c, Icons.search_rounded, [const TextSpan(text: 'Searched '), _code(c, cs(s['q'])), TextSpan(text: ' · ${cPlural(ci(s['num'] ?? s['n']), 'place')}')]);
      case 'list':
        return _line(c, Icons.folder_open_rounded, [const TextSpan(text: 'Looked in '), _code(c, cs(s['path']).isEmpty ? '/' : cs(s['path']))]);
      case 'usages':
        return _line(c, Icons.search_rounded, [const TextSpan(text: 'Found where '), _code(c, cs(s['name'])), TextSpan(text: ' is used · ${cPlural(ci(s['num'] ?? s['n']), 'place')}')]);
      case 'edit':
        return _line(c, Icons.edit_outlined, [const TextSpan(text: 'Edited '), _code(c, cs(s['path']))], trailing: CodeStat(ci(s['added']), ci(s['removed']), size: 12));
      case 'new':
        return _line(c, Icons.add_rounded, [const TextSpan(text: 'Wrote '), _code(c, cs(s['path']))], trailing: CodeStat(ci(s['added']), 0, size: 12));
      case 'diff':
        return _line(c, Icons.difference_outlined, [TextSpan(text: 'Checked its own change · ${cPlural(ci(s['num'] ?? s['n']), 'file')}')]);
      case 'check':
        {
          final ok = s['ok'] == true;
          return _line(c, ok ? Icons.check_circle_outline_rounded : Icons.cancel_outlined, [
            const TextSpan(text: 'Ran your tests · '),
            TextSpan(text: ok ? 'passed' : 'failed', style: TextStyle(color: ok ? c.ok : c.bad, fontWeight: FontWeight.w600)),
          ], iconColor: ok ? c.ok : c.bad);
        }
      case 'check_off':
        return _line(c, Icons.block_rounded, [const TextSpan(text: 'Your tests could not run here - this change is not measured')]);
      case 'grep':
        return _line(c, Icons.search_rounded, [const TextSpan(text: 'Searched the test log for '), _code(c, cs(s['q']))]);
      case 'refused':
        return _line(c, Icons.block_rounded, [TextSpan(text: 'A step was refused: ${cs(s['why'])}')], iconColor: c.warn);
      case 'bash':
        {
          final done = s.containsKey('rc');
          final ok = ci(s['rc']) == 0 && s['timed_out'] != true;
          final end = !done ? '' : (s['timed_out'] == true ? ' · timed out' : ' · exit ${ci(s['rc'])}');
          return _line(c, Icons.terminal_rounded, [_code(c, '\$ ${cs(s['cmd'])}'), TextSpan(text: end, style: TextStyle(color: done && !ok ? c.bad : c.ink3))],
              iconColor: !done ? null : (ok ? c.ok : c.bad));
        }
      case 'agent':
        return _line(c, Icons.groups_outlined, [TextSpan(text: cs(s['text']).isNotEmpty ? cs(s['text']) : 'A helper agent: ${cs(s['name'])}')]);
      case 'compact' || 'ws' || 'gate' || 'reality' || 'memory':
        {
          final txt = cs(s['text']);
          return txt.isEmpty ? null : _line(c, Icons.info_outline_rounded, [TextSpan(text: txt)]);
        }
      case 'wait':
        return _line(c, Icons.hourglass_empty_rounded, [TextSpan(text: cs(s['text']).isEmpty ? 'Waiting for a free coding slot' : cs(s['text']))]);
      case 'ckpt':
        return _line(c, Icons.bookmark_border_rounded, [TextSpan(text: 'Checkpoint ${ci(s['num'] ?? s['n'])} saved')]);
      case 'rewind':
        return _line(c, Icons.undo_rounded, [
          TextSpan(text: 'Went back to checkpoint ${ci(s['num'] ?? s['n'])}${ci(s['from']) >= 0 && s.containsKey('from') ? ' - the greyed part above was undone' : ''}')
        ]);
      case 'pass':
        {
          const names = {'plan': 'Plan pass', 'review': "Hoola's own review", 'ci_fix': 'CI fix round', 'comments': "Reviewers' comments"};
          final end = cs(s['state']) == 'end';
          final note = cs(s['note']);
          return _line(c, end ? (s['ok'] == false ? Icons.cancel_outlined : Icons.check_rounded) : Icons.more_horiz_rounded,
              [TextSpan(text: '${names[cs(s['name'])] ?? cs(s['name'])} ${end ? 'ended' : 'started'}${note.isEmpty ? '' : ' · $note'}')]);
        }
      case 'think':
        return Container(
          margin: const EdgeInsets.fromLTRB(28, 4, 0, 6),
          padding: const EdgeInsets.only(left: 10),
          decoration: BoxDecoration(border: Border(left: BorderSide(color: c.line, width: 2))),
          child: Text(cs(s['text']), maxLines: 12, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 13, color: c.ink3, height: 1.45)),
        );
      case 'stopped':
        return _line(c, Icons.stop_circle_outlined, [const TextSpan(text: 'Stopped. Nothing was pushed.')], iconColor: c.bad);
      default:
        {
          final txt = cs(s['text']);
          return txt.isEmpty ? null : _line(c, Icons.circle_outlined, [TextSpan(text: txt)]);
        }
    }
  }

  /// v0.957 the newest plan Hoola wrote (its todo list), or nothing.
  static List<Map<String, dynamic>> _todoItems(Map<String, dynamic> t) {
    final steps = cl(t['steps']);
    for (var i = steps.length - 1; i >= 0; i--) {
      if (cs(steps[i]['k']) == 'todo') return cl(steps[i]['items']).take(20).toList();
    }
    return const [];
  }

  /// v0.957 the plan as a dock just above the typing box, like Claude Code's todo list: one steady line (the step it is
  /// on, "4 of 9", a bar that slides) that never moves with the thread; a tap opens every step. It was a 300 px card at
  /// the end of the thread that jumped every time a word wrapped or the working row came and went.
  Widget _planDock(HoolaColors c, List<Map<String, dynamic>> items) {
    final done = items.where((x) => cs(x['status']) == 'completed').length;
    final cur = items.firstWhere((x) => cs(x['status']) == 'in_progress',
        orElse: () => items.firstWhere((x) => cs(x['status']) != 'completed', orElse: () => const <String, dynamic>{}));
    final now = cur.isEmpty ? 'All done' : cs(cur['content']);
    final fade = HoolaMotion.of(context, HoolaMotion.fade);
    Widget mark(String st) => SizedBox(
          width: 20,
          child: Text(switch (st) { 'completed' => '✓', 'in_progress' => '●', _ => '○' },
              style: codeSans(c, size: 13.5, color: switch (st) { 'completed' => c.ok, 'in_progress' => c.accent, _ => c.lineStrong })),
        );
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 4, 14, 2),
      child: Semantics(
        button: true,
        label: 'Plan: $done of ${items.length} done. Now: $now. ${_planOpen ? 'Hide the steps' : 'Show every step'}',
        excludeSemantics: true,
        child: Material(
          color: c.surface,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: c.line)),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => setState(() => _planOpen = !_planOpen),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 10, 10, 10),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                SizedBox(
                  height: 24,
                  child: Row(children: [
                    Text('Plan', style: codeSans(c, size: 13.5, weight: FontWeight.w600)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: AnimatedSwitcher(
                        duration: fade,
                        layoutBuilder: (cur0, prev) => Stack(alignment: Alignment.centerLeft, children: [...prev, if (cur0 != null) cur0]),
                        child: Text(_planOpen ? '' : now,
                            key: ValueKey(_planOpen ? '' : now),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: codeSans(c, size: 13.5, color: c.ink2)),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text('$done of ${items.length}',
                        style: codeSans(c, size: 12.5, color: c.ink3).copyWith(fontFeatures: const [FontFeature.tabularFigures()])),
                    AnimatedRotation(
                      turns: _planOpen ? .5 : 0,
                      duration: fade,
                      child: Icon(Icons.expand_less_rounded, size: 20, color: c.ink3),
                    ),
                  ]),
                ),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(2),
                  child: TweenAnimationBuilder<double>(
                    tween: Tween(end: items.isEmpty ? 0 : done / items.length),
                    duration: const Duration(milliseconds: 420),
                    curve: Curves.easeOutCubic,
                    builder: (_, v, __) => LinearProgressIndicator(value: v, minHeight: 3, color: c.ink, backgroundColor: c.sunk),
                  ),
                ),
                AnimatedSize(
                  duration: HoolaMotion.of(context, const Duration(milliseconds: 220)),
                  curve: Curves.easeOutCubic,
                  alignment: Alignment.topCenter,
                  child: !_planOpen
                      ? const SizedBox(width: double.infinity)
                      : ConstrainedBox(
                          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * .4),
                          child: SingleChildScrollView(
                            padding: const EdgeInsets.only(top: 8),
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              for (final x in items)
                                Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 3),
                                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                    mark(cs(x['status'])),
                                    Expanded(
                                      child: Text(cs(x['content']),
                                          style: codeSans(c, size: 13.5, color: cs(x['status']) == 'in_progress' ? c.ink : c.ink2, height: 1.4)),
                                    ),
                                  ]),
                                ),
                            ]),
                          ),
                        ),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Widget _label(HoolaColors c, String s) => Padding(padding: const EdgeInsets.only(top: 12, bottom: 4), child: Text(s, style: codeSans(c, size: 12.5, weight: FontWeight.w600, color: c.ink2)));

  Widget _plan(HoolaColors c, Map<String, dynamic> t) {
    final p = cm(t['plan']);
    String item(dynamic x) => x is Map ? '${cs(x['path'])}${cs(x['why']).isEmpty ? '' : ' - ${cs(x['why'])}'}' : cs(x);
    final files = (p['files'] as List?) ?? const [];
    final steps = (p['steps'] as List?) ?? const [];
    final done = (p['done_when'] as List?) ?? const [];
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: CodeCard(
        edge: c.warn,
        lifted: true,
        radius: 18,
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            CodeBadge('Waiting for you', fg: c.warn, bg: c.warnSoft),
            if (cs(t['tier']).isNotEmpty) ...[const SizedBox(width: 8), Text('${cs(t['tier'])[0].toUpperCase()}${cs(t['tier']).substring(1)} job', style: codeSans(c, size: 12.5, color: c.ink3))],
          ]),
          if (cs(p['goal']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 10), child: Text(cs(p['goal']), style: HoolaType.replyH2(c).copyWith(fontSize: 19))),
          if (files.isNotEmpty) ...[
            _label(c, 'Files it will change · ${files.length}'),
            for (final f in files.take(12)) Text(item(f), style: codeMono(c, size: 12.5)),
          ],
          if (steps.isNotEmpty) ...[
            _label(c, 'Steps'),
            for (final (i, s) in steps.take(12).indexed) Padding(padding: const EdgeInsets.only(bottom: 3), child: Text('${i + 1}. ${item(s)}', style: codeSans(c, size: 14, height: 1.45))),
          ],
          if (done.isNotEmpty) ...[
            _label(c, 'Done when'),
            for (final d in done.take(8))
              Padding(
                padding: const EdgeInsets.only(bottom: 3),
                child: Text.rich(TextSpan(children: [TextSpan(text: '✓  ', style: TextStyle(color: c.ok)), TextSpan(text: item(d))]), style: codeSans(c, size: 14, height: 1.45)),
              ),
          ],
          if (cs(p['risk']).isNotEmpty)
            Container(
              margin: const EdgeInsets.only(top: 10),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(10)),
              child: Text('Risk: ${cs(p['risk'])}', style: codeSans(c, size: 13, color: c.ink2)),
            ),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: CodeOutline('Change something', onTap: () => _focus.requestFocus())),
            const SizedBox(width: 10),
            Expanded(child: CodeMain('Yes, start', icon: Icons.check_rounded, busy: _busy, onTap: () => _run('POST', '$_base/bg/plan_ok', {'hash': cs(t['hash'])}))),
          ]),
          const SizedBox(height: 8),
          Text('Nothing in the repo is touched until you say yes. A note in the box below goes with your yes.', style: codeSans(c, size: 12.5, color: c.ink3)),
        ]),
      ),
    );
  }

  List<Widget> _question(HoolaColors c, Map<String, dynamic> t) {
    final choices = ((cm(t['ws'])['choices'] as List?) ?? const []).map(cs).where((e) => e.isNotEmpty).take(4).toList();
    return [
      Padding(padding: const EdgeInsets.only(top: 14), child: HoolaMd(cs(t['question']))),
      for (final ch in choices)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: CodeCard(
            onTap: _busy ? null : () => _send(ch),
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
            child: Row(children: [
              Icon(Icons.radio_button_unchecked_rounded, size: 20, color: c.ink3),
              const SizedBox(width: 12),
              Expanded(child: Text(ch, style: codeSans(c, size: 15, weight: FontWeight.w500))),
            ]),
          ),
        ),
      Padding(padding: const EdgeInsets.only(top: 10), child: Text(choices.isEmpty ? 'Type your answer below.' : 'Or type your own answer below.', style: codeSans(c, size: 13, color: c.ink3))),
    ];
  }

  Widget _ready(HoolaColors c, Map<String, dynamic> t) {
    final (a, r) = codeStat(t);
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: CodeCard(
        edge: c.warn,
        lifted: true,
        radius: 18,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [CodeBadge('Ready for you', fg: c.warn, bg: c.warnSoft), const Spacer(), CodeStat(a, r)]),
          const SizedBox(height: 10),
          Text('The change is ready on its own branch. Open the pull request when you are happy with it.', style: codeSans(c, size: 14.5)),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: CodeOutline('See changes', onTap: _changes)),
            const SizedBox(width: 10),
            Expanded(flex: 2, child: CodeMain('Open the pull request', busy: _busy, onTap: () => _run('POST', '$_base/push', {'hash': cs(t['hash'])}))),
          ]),
        ]),
      ),
    );
  }

  static const _proof = {
    'proven': ('ok', 'Bug proven: your CI failed the test first'),
    'proven_local': ('ok', 'Bug proven: test red before, green after'),
    'proven_unnamed': ('ok', 'Your CI went red on the test first'),
    'not_proven': ('warn', 'The test passed on the old code - it does not prove the bug'),
    'not_proven_local': ('warn', 'The test passed on the old code - it does not prove the bug'),
    'still_failing': ('bad', 'Your tests still fail after the fix'),
    'checked_local': ('ok', 'Your tests passed'),
    'check_failed_local': ('bad', 'Your tests failed'),
    'wait': ('run', 'Waiting for your CI'),
  };

  Widget _check(HoolaColors c, String kind, String text, {Widget? trailing}) {
    final (Color fg, Color bg, IconData? icon) = switch (kind) {
      'ok' => (c.ok, c.okSoft, Icons.check_rounded),
      'bad' => (c.bad, c.badSoft, Icons.close_rounded),
      'run' => (c.accent, c.accentSoft, null),
      _ => (c.warn, c.warnSoft, null),
    };
    return Container(
      constraints: const BoxConstraints(minHeight: 44),
      child: Row(children: [
        Container(
          width: 22,
          height: 22,
          decoration: BoxDecoration(color: bg, shape: BoxShape.circle),
          child: icon != null ? Icon(icon, size: 13, color: fg) : Center(child: Container(width: 6, height: 6, decoration: BoxDecoration(color: fg, shape: BoxShape.circle))),
        ),
        const SizedBox(width: 10),
        Expanded(child: Text(text, style: codeSans(c, size: 14))),
        if (trailing != null) trailing,
      ]),
    );
  }

  Widget _pr(HoolaColors c, Map<String, dynamic> t) {
    final st = cs(t['status']);
    final ciState = cs(cm(t['ci'])['state']);
    final sr = cm(t['self_review']);
    final verdict = cs(sr['verdict']);
    final open = ((sr['problems'] as List?) ?? const []).length;
    final comments = cl(t['pr_comments']).length;
    final pf = _proof[cs(cm(t['proof'])['state'])];
    final merged = st == 'merged';
    final closed = st == 'closed';
    final canMerge = (st == 'pr_open' || st == 'checks_failed') && !codeRunning(t);
    final (String head, Color hc) = merged
        ? ('Merged', c.ok)
        : closed
            ? ('Closed', c.ink3)
            : st == 'checks_failed'
                ? ('CI failed', c.bad)
                : st == 'ci_running'
                    ? ('CI running', c.accent)
                    : ('Ready to merge', c.ok);
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: CodeCard(
        lifted: true,
        radius: 18,
        padding: EdgeInsets.zero,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon(merged ? Icons.merge_rounded : Icons.call_split_rounded, size: 18, color: hc),
                const SizedBox(width: 8),
                Text(head, style: codeSans(c, size: 13, weight: FontWeight.w600, color: hc)),
                Text('  ·  PR #${ci(t['pr_number'])}', style: codeSans(c, size: 13, color: c.ink3)),
              ]),
              const SizedBox(height: 6),
              Text(codeTitle(t), style: HoolaType.replyH2(c)),
              if (cs(t['branch']).isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text('${cs(t['branch'])} → ${cs(t['base']).isEmpty ? 'main' : cs(t['base'])}', style: codeMono(c, size: 12, color: c.ink3)),
                ),
            ]),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
            decoration: BoxDecoration(border: Border(top: BorderSide(color: c.sunk))),
            child: Column(children: [
              if (ciState.isNotEmpty)
                _check(c, switch (ciState) { 'success' => 'ok', 'failure' => 'bad', 'pending' => 'run', _ => 'warn' },
                    switch (ciState) { 'success' => 'Your CI passed', 'failure' => 'Your CI failed', 'pending' => 'Your CI is running', _ => 'No CI on this repo' }),
              if (pf != null) _check(c, pf.$1, pf.$2),
              if (verdict.isNotEmpty) _check(c, verdict == 'ok' ? 'ok' : 'warn', verdict == 'ok' ? "Hoola's own review: nothing left open" : "Hoola's own review: ${cPlural(open, 'point')} open"),
              if (comments > 0)
                _check(c, 'warn', cPlural(comments, 'reviewer comment'),
                    trailing: (st == 'pr_open' || st == 'checks_failed') ? _small(c, 'Fix it', () => _run('POST', '$_base/bg/fix_comments')) : null),
              if (st == 'checks_failed') _check(c, 'bad', 'CI failed on GitHub', trailing: _small(c, 'Fix it', () => _run('POST', '$_base/bg/fix_ci'))),
            ]),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
            decoration: BoxDecoration(border: Border(top: BorderSide(color: c.sunk))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                if (cs(t['pr_url']).isNotEmpty) Expanded(child: CodeOutline('GitHub', icon: Icons.open_in_new_rounded, height: 46, onTap: () => codeOpenGithub(cs(t['pr_url'])))),
                if (cs(t['pr_url']).isNotEmpty && canMerge) const SizedBox(width: 10),
                if (canMerge)
                  Expanded(
                    flex: 2,
                    child: CodeMain(_merge != null ? 'Merge · waiting for you' : 'Merge pull request',
                        icon: Icons.merge_rounded, height: 46, busy: _busy, onTap: _merge != null ? _decideMerge : _askMerge),
                  ),
              ]),
              if (canMerge || st == 'ci_running')
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Row(children: [
                    Expanded(child: Text('Nothing is merged without your tap.', style: codeSans(c, size: 12, color: c.ink3))),
                    InkWell(
                      onTap: _busy ? null : () => _run('POST', '$_base/refresh'),
                      child: Padding(padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 4), child: Text('Check CI again', style: codeSans(c, size: 13, weight: FontWeight.w500, color: c.ink2))),
                    ),
                  ]),
                ),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _small(HoolaColors c, String label, VoidCallback onTap) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Material(
          color: c.surface,
          shape: StadiumBorder(side: BorderSide(color: c.lineStrong)),
          child: InkWell(
            customBorder: const StadiumBorder(),
            onTap: _busy ? null : onTap,
            child: Container(
              constraints: const BoxConstraints(minHeight: 36, minWidth: 64),
              padding: const EdgeInsets.symmetric(horizontal: 12),
              alignment: Alignment.center,
              child: Text(label, style: codeSans(c, size: 13, weight: FontWeight.w500)),
            ),
          ),
        ),
      );

  // ---------------------------------------------------------------------------------------------- the typing box
  Widget _composer(HoolaColors c, Map<String, dynamic> t) {
    final mode = _mode(t);
    final running = codeRunning(t);
    final comments = CodeComments.of(widget.id).length;
    if (mode == 'off') {
      return Container(
        padding: const EdgeInsets.fromLTRB(20, 12, 16, 14),
        decoration: BoxDecoration(color: c.bg, border: Border(top: BorderSide(color: c.sunk))),
        child: Row(children: [
          Expanded(child: Text('This session is finished.', style: codeSans(c, size: 14, color: c.ink2))),
          CodeOutline('New session', height: 44, icon: Icons.add_rounded, onTap: () => showCodeNewSession(context, widget.app, onStarted: (id) {
                Navigator.of(context).pushReplacement(MaterialPageRoute<void>(
                    builder: (_) => HoolaTheme(appearance: widget.app.appearance, child: CodeSessionPage(app: widget.app, id: id))));
              })),
        ]),
      );
    }
    const hints = {
      'note': 'Reply or hold to talk',
      'answer': 'Answer Hoola…',
      'plan': 'A note to go with your yes…',
      'revise': 'Ask for a change on the same pull request…',
    };
    final hint = mode == 'revise' ? cs(t['hint']) : '';
    final stopping = t['stopping'] == true;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 6, 14, 12),
      decoration: BoxDecoration(color: c.bg),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (comments > 0)
          Padding(
            padding: const EdgeInsets.fromLTRB(6, 0, 6, 8),
            child: Text('${cPlural(comments, 'comment')} on lines goes with your next message', style: codeSans(c, size: 13, color: c.accent)),
          ),
        if (!running)
          Padding(
            padding: const EdgeInsets.fromLTRB(2, 0, 2, 10),
            child: Row(children: [
              CodeBarChip(
                icon: Icon(_envName(t) == 'Auto' ? Icons.auto_mode_rounded : Icons.cloud_outlined, size: 17, color: c.ink2),
                label: _envName(t),
                semantics: 'Environment: ${_envName(t)}',
                onTap: () => _pickEnv(t),
              ),
              const SizedBox(width: 12),
              Expanded(child: HoolaQualityRow(app: widget.app)),   // v0.999.29 credits + the quality tier, no model name
            ]),
          ),
        CodeBar(
          app: widget.app,
          controller: _msg,
          focus: _focus,
          hint: hints[mode] ?? 'Reply or hold to talk',
          top: hint.isNotEmpty && _msg.text.isEmpty
              ? CodeChip(hint, chevron: true, onTap: () => setState(() {
                    _msg.text = hint;
                    _msg.selection = TextSelection.collapsed(offset: hint.length);
                  }))
              : null,
          maxLength: 4000,
          onPlus: _more,
          plusLabel: 'Session menu',
          canSendEmpty: comments > 0 || mode == 'plan',
          sendLabel: mode == 'plan' && _msg.text.trim().isEmpty ? 'Yes, start' : 'Send',
          onSend: _busy ? null : () => _send(),
          onStop: running ? () => _run('POST', '$_base/stop') : null,
          stopLabel: stopping ? 'Stopping' : 'Stop',
          busy: _busy || stopping,
        ),
      ]),
    );
  }

  String _envName(Map<String, dynamic> t) {
    final e = cm(t['env']);
    final n = cs(e['name']);
    return n.isEmpty ? 'Auto' : n;
  }

  /// The environment of this session; a change applies from the next round (PUT /tasks/{id}/env).
  Future<void> _pickEnv(Map<String, dynamic> t) async {
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/envs', quiet: true);
    if (!mounted) return;
    final now = cs(cm(t['env'])['id']).isEmpty ? 'auto' : cs(cm(t['env'])['id']);
    final envs = [for (final e in cl(r?['envs'])) if (e['archived'] != true) e];
    final pick = await codeSheet<String>(context, widget.app,
        title: 'Environment',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              CodeChoiceRow(label: 'Auto', sub: 'Follows each repo\'s own settings', on: now == 'auto', onTap: () => Navigator.pop(ctx, 'auto')),
              for (final e in envs)
                CodeChoiceRow(label: cs(e['name']), sub: cs(cm(e['net'])['level']), on: cs(e['id']) == now, onTap: () => Navigator.pop(ctx, cs(e['id']))),
              Text('A round already running keeps what it started with.', style: codeSans(HoolaColors.of(ctx), size: 13, color: HoolaColors.of(ctx).ink3)),
            ]));
    if (pick == null || pick == now || !mounted) return;
    await _run('PUT', '$_base/env', {'env': pick});
  }

  /// Between two steps (the step itself, when running, comes from the server's "now"): what it is doing.
  String _nowWords(Map<String, dynamic> s) => switch (cs(s['k'])) {
        'wait' => 'Waiting for a free coding slot',
        'pass' => cs(s['state']) == 'end' ? 'Thinking' : _passWords(cs(s['name'])),
        _ => 'Thinking',
      };

  /// v0.927 what a pass is doing, in her words (the plan pass only reads; it was shown as "Checking its own work").
  static String _passWords(String name) => switch (name) {
        'plan' => 'Planning · reading the code',
        'ci' || 'ci_fix' => 'Fixing the failed checks',
        'comments' => "Reading the reviewers' comments",
        _ => 'Checking its own work',
      };

  /// A step group with nothing counted yet (only a pass has started) says what is going on, never "0 steps".
  String _passTitle(List<Map<String, dynamic>> g) {
    for (final s in g.reversed) {
      if (cs(s['k']) == 'pass') return cs(s['state']) == 'end' ? 'Getting ready' : _passWords(cs(s['name']));
    }
    return 'Getting ready';
  }
}

