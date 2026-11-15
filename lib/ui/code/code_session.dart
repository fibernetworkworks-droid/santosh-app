// v0.921 HOOLA CODE NATIVE - one session (screens 2, 3, 4 and 6 of claude.ai/artifact/GF4AtP5MNfV8kARgTGymuh): her ask,
// Hoola's words in the reply serif, the real steps folded under "Worked for", the plan card that waits for her yes,
// the one question with choices, the pull request with its checks and Merge, and the typing box (a note while it
// works, her answer, her note with the plan, or a change on the same PR). Opening the PR, merging and a plan's start
// are her taps; the server re-checks every one.
import 'dart:async';

import 'package:flutter/material.dart';

import '../../state.dart';
import '../chat/hoola_md.dart';
import '../hoola_mark.dart';
import '../hoola_theme.dart';
import 'code_changes.dart';
import 'code_home.dart';
import 'code_kit.dart';
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

class _CodeSessionPageState extends State<CodeSessionPage> {
  Map<String, dynamic>? _t;
  Map<String, dynamic>? _merge;
  String? _error;
  bool _busy = false, _thinking = false, _lookedForMerge = false;
  final Set<int> _open = {};
  String? _selecting;                 // v0.928 the message whose text she is selecting
  bool _away = false;                 // she scrolled up: the Newest arrow shows and nothing pulls her down
  int _seen = -1;                     // how many steps were drawn last time (new ones follow her to the end)
  Timer? _poll, _tick;
  final _msg = TextEditingController();
  final _focus = FocusNode();
  final _scroll = ScrollController();

  String get _base => '/api/devsahayak/tasks/${Uri.encodeComponent(widget.id)}';

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      final away = _scroll.hasClients && _scroll.position.maxScrollExtent - _scroll.offset > 240;
      if (away != _away && mounted) setState(() => _away = away);
    });
    _load();
  }

  void _toEnd({bool animate = true}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      final end = _scroll.position.maxScrollExtent;
      animate ? _scroll.animateTo(end, duration: const Duration(milliseconds: 260), curve: Curves.easeOut) : _scroll.jumpTo(end);
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    _tick?.cancel();
    _msg.dispose();
    _focus.dispose();
    _scroll.dispose();
    super.dispose();
  }

  bool _live(Map<String, dynamic> t) => codeRunning(t) || const {'ci_running', 'new'}.contains(cs(t['status']));

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) return;
    try {
      final t = cm(await api.call('GET', _base));
      if (!mounted) return;
      final n = cl(t['steps']).length;
      final first = _seen < 0;
      setState(() {
        _t = t;
        _error = null;
      });
      if (n != _seen && (first || !_away)) _toEnd(animate: !first);   // new words follow her unless she scrolled up
      _seen = n;
      if (_live(t)) {
        _poll ??= Timer.periodic(const Duration(seconds: 3), (_) => _load());
        _tick ??= Timer.periodic(const Duration(seconds: 1), (_) {
          if (mounted) setState(() {});
        });
      } else {
        _poll?.cancel();
        _poll = null;
        _tick?.cancel();
        _tick = null;
      }
      if (!_lookedForMerge && ci(t['pr_number']) != 0 && !codeRunning(t)) {
        _lookedForMerge = true;
        _findMerge(t);
      }
    } catch (e) {
      if (mounted) setState(() => _error = '$e'.replaceFirst('Exception: ', ''));
    }
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
    await _load();
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
    final r = switch (mode) {
      'note' => await _run('POST', '$_base/note', {'text': text, 'comments': comments}),
      'answer' => await _run('POST', '$_base/answer', {'text': text}),
      'plan' => await _run('POST', '$_base/bg/plan_ok', {'hash': cs(t['hash']), 'note': text}),
      _ => await _run('POST', '$_base/bg/revise', {'text': text, 'comments': comments}),
    };
    if (r != null) {
      if (comments.isNotEmpty) CodeComments.clear(widget.id);
      if (words == null) _msg.clear();
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

  Future<void> _changes() async {
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
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          CodeTopBar(
            title: t == null ? 'Hoola Code' : codeTitle(t),
            sub: t == null ? '' : [cRepoShort(cs(t['repo'])), cs(t['branch'])].where((e) => e.isNotEmpty).join(' · '),
            actions: [
              if (a + r > 0)
                Semantics(
                  button: true,
                  label: 'Changes: $a lines added, $r removed',
                  child: InkWell(
                    onTap: _changes,
                    borderRadius: BorderRadius.circular(18),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Container(
                        height: 36,
                        padding: const EdgeInsets.symmetric(horizontal: 10),
                        decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(18), border: Border.all(color: c.line)),
                        child: Center(child: CodeStat(a, r)),
                      ),
                    ),
                  ),
                ),
              CodeIconButton(icon: Icons.more_horiz_rounded, label: 'More', onTap: t == null ? null : _more),
            ],
          ),
          Expanded(
            child: t == null
                ? Center(
                    child: _error == null
                        ? const CodeRing(size: 22)
                        : Padding(padding: const EdgeInsets.all(24), child: Text(_error!, textAlign: TextAlign.center, style: codeSans(c, color: c.ink2))))
                : RefreshIndicator(
                    onRefresh: _load,
                    color: c.ink,
                    child: Stack(fit: StackFit.expand, children: [
                      ListView(controller: _scroll, padding: const EdgeInsets.fromLTRB(20, 16, 20, 24), children: _body(c, t)),
                      if (_away)
                        Positioned(bottom: 12, left: 0, right: 0, child: Center(child: CodeNewestButton(onTap: () => _toEnd()))),
                      if (_selecting != null)
                        Positioned(
                          top: 8,
                          right: 12,
                          child: CodeChip('Done selecting', icon: Icons.check_rounded, onTap: () => setState(() => _selecting = null)),
                        ),
                    ]),
                  ),
          ),
          if (t != null) _composer(c, t),
        ]),
      ),
    );
  }

  // ---------------------------------------------------------------------------------------------- the thread
  List<Widget> _body(HoolaColors c, Map<String, dynamic> t) {
    final steps = cl(t['steps']);
    final running = codeRunning(t);
    final st = cs(t['status']);
    final out = <Widget>[_her(c, cs(t['text']), cl(t['attach']))];
    // the steps between Hoola's words fold into one "Worked for" group each
    final group = <Map<String, dynamic>>[];
    var gi = 0;
    Map<String, dynamic>? todo;
    var said = false;
    var lastSay = -1;
    for (var i = 0; i < steps.length; i++) {
      if (cs(steps[i]['k']) == 'say') lastSay = i;
    }
    var si = -1;
    void flush({required bool last}) {
      if (group.isEmpty) return;
      out.add(_group(c, List.of(group), gi, open: (running && last) || _open.contains(gi)));
      gi++;
      group.clear();
    }

    for (final s in steps) {
      si++;
      final k = cs(s['k']);
      if (k == 'say') {
        flush(last: false);
        said = true;
        out.add(_reply(cs(s['text']), 'say$si', actions: si == lastSay && !running));
      } else if (k == 'note') {
        flush(last: false);
        out.add(_her(c, cs(s['text']), const [], small: true, key: 'note$si'));
      } else if (k == 'todo') {
        todo = s;
      } else if (k == 'think') {
        if (_thinking) group.add(s);
      } else {
        group.add(s);
      }
    }
    flush(last: true);
    if (todo != null && cl(todo['items']).isNotEmpty) out.add(_todo(c, cl(todo['items'])));
    for (final n in running ? ((t['notes'] as List?) ?? const []) : const []) {
      if (cs(n).isNotEmpty) out.add(Padding(padding: const EdgeInsets.only(top: 10), child: Text('Queued for its next step: ${cs(n)}', style: codeSans(c, size: 13, color: c.ink3))));
    }
    if (!running) {
      if (!said && cs(t['explain']).isNotEmpty) out.add(_reply(cs(t['explain']), 'explain', actions: true));
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
    return out;
  }

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
                borderRadius: const BorderRadius.only(topLeft: Radius.circular(20), topRight: Radius.circular(20), bottomLeft: Radius.circular(20), bottomRight: Radius.circular(6)),
              ),
              child: _selecting == key
                  ? SelectableText(text, style: codeSans(c, size: small ? 14.5 : 15.5, height: 1.45))
                  : GestureDetector(
                      onLongPress: () => _herMenu(text, key),
                      child: Text(text, style: codeSans(c, size: small ? 14.5 : 15.5, height: 1.45)),
                    ),
            ),
          ]),
        ),
      );

  int _secs(List<Map<String, dynamic>> g) {
    final a = codeTime(cs(g.first['at']));
    final b = codeTime(cs(g.last['at']));
    if (a == null) return 0;
    return (b ?? DateTime.now()).difference(a).inSeconds;
  }

  Widget _group(HoolaColors c, List<Map<String, dynamic>> g, int i, {required bool open}) {
    final counted = g.where((s) => !const {'think', 'pass', 'ckpt'}.contains(cs(s['k']))).length;
    final secs = _secs(g);
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: CodeCard(
        padding: EdgeInsets.zero,
        radius: 14,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Semantics(
            button: true,
            label: open ? 'Hide the steps' : 'Show the steps',
            child: InkWell(
              onTap: () => setState(() => open ? _open.remove(i) : _open.add(i)),
              child: Container(
                height: 48,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                decoration: BoxDecoration(border: open ? Border(bottom: BorderSide(color: c.sunk)) : null),
                child: Row(children: [
                  Icon(Icons.subject_rounded, size: 17, color: c.ink2),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(counted == 0 ? _passTitle(g) : secs > 0 ? 'Worked for ${codeLong(secs)} · ${cPlural(counted, 'step')}' : cPlural(counted, 'step'),
                        style: codeSans(c, size: 13.5, weight: FontWeight.w500)),
                  ),
                  Icon(open ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded, size: 18, color: c.ink3),
                ]),
              ),
            ),
          ),
          if (open)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 6, 12, 10),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: (g.length > 60 ? g.sublist(g.length - 60) : g).map((s) => _step(c, s)).whereType<Widget>().toList()),
            ),
        ]),
      ),
    );
  }

  Widget _line(HoolaColors c, IconData icon, List<InlineSpan> spans, {Color? iconColor, Widget? trailing, bool live = false}) => Container(
        constraints: const BoxConstraints(minHeight: 32),
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
          SizedBox(width: 18, child: live ? const CodeRing(size: 14) : Icon(icon, size: 16, color: iconColor ?? c.ink3)),
          const SizedBox(width: 10),
          Expanded(child: Text.rich(TextSpan(style: codeSans(c, size: 13.5, color: c.ink2, height: 1.35), children: spans))),
          if (trailing != null) ...[const SizedBox(width: 8), trailing],
        ]),
      );

  TextSpan _code(HoolaColors c, String s) => TextSpan(text: s, style: codeMono(c, size: 12.5));

  Widget? _step(HoolaColors c, Map<String, dynamic> s) {
    final k = cs(s['k']);
    switch (k) {
      case 'rules':
        return _line(c, Icons.rule_rounded, [const TextSpan(text: "Read the repo's own rules")]);
      case 'read':
        return _line(c, Icons.description_outlined, [const TextSpan(text: 'Read '), _code(c, cs(s['path']))]);
      case 'search':
        return _line(c, Icons.search_rounded, [const TextSpan(text: 'Searched '), _code(c, cs(s['q'])), TextSpan(text: ' · ${cPlural(ci(s['n']), 'place')}')]);
      case 'list':
        return _line(c, Icons.folder_open_rounded, [const TextSpan(text: 'Looked in '), _code(c, cs(s['path']).isEmpty ? '/' : cs(s['path']))]);
      case 'usages':
        return _line(c, Icons.search_rounded, [const TextSpan(text: 'Found where '), _code(c, cs(s['name'])), TextSpan(text: ' is used · ${cPlural(ci(s['n']), 'place')}')]);
      case 'edit':
        return _line(c, Icons.edit_outlined, [const TextSpan(text: 'Edited '), _code(c, cs(s['path']))], trailing: CodeStat(ci(s['added']), ci(s['removed']), size: 12));
      case 'new':
        return _line(c, Icons.add_rounded, [const TextSpan(text: 'Wrote '), _code(c, cs(s['path']))], trailing: CodeStat(ci(s['added']), 0, size: 12));
      case 'diff':
        return _line(c, Icons.difference_outlined, [TextSpan(text: 'Checked its own change · ${cPlural(ci(s['n']), 'file')}')]);
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
        return _line(c, Icons.bookmark_border_rounded, [TextSpan(text: 'Checkpoint ${ci(s['n'])} saved')]);
      case 'rewind':
        return _line(c, Icons.undo_rounded, [TextSpan(text: 'Went back to checkpoint ${ci(s['n'])}')]);
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

  Widget _todo(HoolaColors c, List<Map<String, dynamic>> items) {
    final done = items.where((x) => cs(x['status']) == 'completed').length;
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: CodeCard(
        radius: 14,
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('Plan', style: codeSans(c, size: 13.5, weight: FontWeight.w600))),
            Text('$done of ${items.length} done', style: codeSans(c, size: 12.5, color: c.ink3)),
          ]),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(value: items.isEmpty ? 0 : done / items.length, minHeight: 4, color: c.ink, backgroundColor: c.sunk),
          ),
          const SizedBox(height: 8),
          for (final x in items.take(12))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(
                  width: 20,
                  child: Text(switch (cs(x['status'])) { 'completed' => '✓', 'in_progress' => '●', _ => '○' },
                      style: codeSans(c, size: 13.5, color: switch (cs(x['status'])) { 'completed' => c.ok, 'in_progress' => c.accent, _ => c.lineStrong })),
                ),
                Expanded(
                  child: Text(cs(x['content']),
                      style: codeSans(c, size: 13.5, color: cs(x['status']) == 'in_progress' ? c.ink : c.ink2, height: 1.4)),
                ),
              ]),
            ),
        ]),
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
      'note': 'Add a note while it works…',
      'answer': 'Answer Hoola…',
      'plan': 'A note to go with your yes…',
      'revise': 'Ask for a change on the same pull request…',
    };
    final hint = mode == 'revise' ? cs(t['hint']) : '';
    final secs = DateTime.now().difference(codeTime(cs(t['run_at']).isEmpty ? cs(t['at']) : cs(t['run_at'])) ?? DateTime.now()).inSeconds;
    final stopping = t['stopping'] == true;
    final steps = cl(t['steps']);
    final now = steps.isEmpty ? 'Starting' : _nowWords(steps.last);
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 6, 14, 12),
      decoration: BoxDecoration(color: c.bg),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (running)
          Padding(
            padding: const EdgeInsets.fromLTRB(6, 2, 6, 8),
            child: Row(children: [
              const HoolaMark(size: 20),
              const SizedBox(width: 9),
              Expanded(child: Text(stopping ? 'Stopping after this step' : now, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 13.5, color: c.ink2))),
              Text(codeClock(secs), style: codeMono(c, size: 12, color: c.ink3)),
            ]),
          ),
        if (comments > 0)
          Padding(
            padding: const EdgeInsets.fromLTRB(6, 0, 6, 8),
            child: Text('${cPlural(comments, 'comment')} on lines goes with your next message', style: codeSans(c, size: 13, color: c.accent)),
          ),
        if (hint.isNotEmpty && _msg.text.isEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Align(
              alignment: Alignment.centerLeft,
              child: CodeChip(hint, icon: Icons.lightbulb_outline_rounded, onTap: () => setState(() {
                    _msg.text = hint;
                    _msg.selection = TextSelection.collapsed(offset: hint.length);
                  })),
            ),
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(2, 0, 2, 10),
          child: Row(children: [
            CodeBarChip(
              icon: Icon(_envName(t) == 'Auto' ? Icons.auto_mode_rounded : Icons.cloud_outlined, size: 17, color: c.ink2),
              label: _envName(t),
              semantics: 'Environment: ${_envName(t)}',
              onTap: () => _pickEnv(t),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(running ? 'Your notes reach Hoola between steps' : 'Changes go on the same branch',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 13, color: c.ink3)),
            ),
          ]),
        ),
        CodeBar(
          app: widget.app,
          controller: _msg,
          focus: _focus,
          hint: hints[mode] ?? 'Reply to Hoola',
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

  String _nowWords(Map<String, dynamic> s) => switch (cs(s['k'])) {
        'read' => 'Reading ${cs(s['path'])}',
        'search' || 'grep' || 'usages' => 'Searching the code',
        'edit' || 'new' => 'Writing ${cs(s['path'])}',
        'bash' => s.containsKey('rc') ? 'Working' : 'Running ${cs(s['cmd'])}',
        'check' => 'Checked your tests',
        'say' || 'think' => 'Thinking',
        'wait' => 'Waiting for a free coding slot',
        'pass' => cs(s['state']) == 'end' ? 'Working' : _passWords(cs(s['name'])),
        _ => 'Working',
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

