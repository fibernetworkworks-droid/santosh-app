/// v0.879 HOOLA CODE PHONE: one session (design docs/design/hoola_code/PhoneSession.png) and its Changes page
/// (PhoneChanges.png). The session: a header with the drawer, the title over "repo · environment", the "+N −M" pill
/// that opens Changes and a ⋯ menu; her ask on the right, Hoola's words in the serif, the steps in bordered cards
/// (green check done, violet dot running, the time on the right), the plan / question / PR cards with a cream main
/// button, "Working · 1m 42s", her queued messages, and the pill composer with the cream Stop while Hoola works.
/// Changes: branch → base, the PR pill and CI, the PR buttons the server really has, Auto-fix, file chips, the diff
/// in mono with line numbers, long-press a line to leave a comment that rides her next message.
/// Merge stays a REQUEST card that waits for her tap (DevActionCard), exactly as before.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'devsahayak_drawer.dart';
import 'devsahayak_kit.dart';
import 'devsahayak_screen.dart' show DevActionCard;
import 'hoola_theme.dart';

const List<String> _canReviseStatus = ['pr_open', 'checks_failed', 'ready', 'refused'];
const Map<String, String> _statusWords = {
  'new': 'starting',
  'plan_wait': 'plan waits for you',
  'ready': 'ready for the PR',
  'pr_open': 'PR open',
  'ci_running': 'CI running',
  'checks_failed': 'CI failed',
  'merged': 'merged',
  'closed': 'PR closed',
  'explained': 'explained',
  'refused': 'stopped by a rule',
  'failed': 'could not finish',
  'cancelled': 'stopped',
};

String devStatusWords(Map<String, dynamic> t) {
  if (t['running'] == true) return 'working';
  if (hcS(t['question']).isNotEmpty) return 'needs you';
  final st = hcS(t['status']);
  final pr = hcInt(t['pr_number']);
  if (pr != 0 && (st == 'pr_open' || st == 'ci_running' || st == 'checks_failed')) return 'PR #$pr ${st == 'checks_failed' ? 'CI failed' : 'open'}';
  return _statusWords[st] ?? st;
}

/// Lines added / removed over all changed files: [added, removed].
List<int> devStat(Map<String, dynamic> t) {
  var a = 0, r = 0;
  for (final f in hcList(t['files'])) {
    a += hcInt(f['added']);
    r += hcInt(f['removed']);
  }
  return [a, r];
}

Future<void> _openGitHub(String url) async {
  if (url.startsWith('https://github.com/')) await Native.openExternal(url: url);
}

Future<Map<String, dynamic>?> _api(BuildContext context, Santosh app, String method, String path, [Object? body]) async {
  try {
    final r = hcM(await app.api!.call(method, path, body: body, timeout: const Duration(minutes: 4)));
    if (context.mounted) hcSay(context, hcS(r['say']));
    return r;
  } catch (e) {
    if (context.mounted) hcSay(context, '$e');
    return null;
  }
}

/// One session page.
class DevTaskPage extends StatelessWidget {
  const DevTaskPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;

  @override
  Widget build(BuildContext context) => HoolaTheme(appearance: app.appearance, child: _DevTaskPageBody(app: app, id: id));
}

class _DevTaskPageBody extends StatefulWidget {
  const _DevTaskPageBody({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<_DevTaskPageBody> createState() => _DevTaskPageState();
}

class _StepRow {
  _StepRow(this.text, {this.ok, this.at, this.mono = false});
  final String text;
  final bool? ok;     // null = a plain done step, false = it failed
  final DateTime? at;
  final bool mono;
}

class _DevTaskPageState extends State<_DevTaskPageBody> {
  Map<String, dynamic>? _t;
  Map<String, dynamic>? _action;   // the merge card that waits for her tap
  bool _busy = false;
  bool _thinking = false;
  bool _askedActions = false;
  Timer? _poll;
  Timer? _tick;
  final _msg = TextEditingController();
  final List<Map<String, dynamic>> _comments = [];   // her line comments from Changes: {path, line, code, text}
  final Set<int> _openGroups = {};

  String get _base => '/api/devsahayak/tasks/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    _tick?.cancel();
    _msg.dispose();
    super.dispose();
  }

  bool _running(Map<String, dynamic> t) => t['running'] == true;
  bool _live(Map<String, dynamic> t) => _running(t) || hcS(t['status']) == 'ci_running' || hcS(t['status']) == 'new';

  void _timers(Map<String, dynamic> t) {
    if (_live(t)) {
      _poll ??= Timer.periodic(const Duration(seconds: 3), (_) => _load(quiet: true));
    } else {
      _poll?.cancel();
      _poll = null;
    }
    if (_running(t)) {
      _tick ??= Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) setState(() {});
      });
    } else {
      _tick?.cancel();
      _tick = null;
    }
  }

  Future<void> _load({bool quiet = false}) async {
    try {
      final t = hcM(await widget.app.api!.call('GET', _base));
      if (!mounted) return;
      setState(() => _t = t);
      _timers(t);
      if (!_askedActions && hcInt(t['pr_number']) != 0 && !_running(t)) {
        _askedActions = true;
        _findWaitingMerge(t);
      }
    } catch (e) {
      if (mounted && !quiet) hcSay(context, '$e');
    }
  }

  /// A merge card she asked for earlier and has not answered yet is shown again when she comes back.
  Future<void> _findWaitingMerge(Map<String, dynamic> t) async {
    try {
      final r = hcM(await widget.app.api!.call('GET', '/api/devsahayak/actions'));
      for (final a in hcList(r['actions'])) {
        if (hcS(a['kind']) == 'merge' && hcS(a['status']) == 'waiting' && hcS(a['repo']) == hcS(t['repo']) && hcInt(a['pr_number']) == hcInt(t['pr_number'])) {
          if (mounted) setState(() => _action = a);
          return;
        }
      }
    } catch (_) {
      // a convenience only; Merge still works
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    if (mounted) setState(() => _busy = true);
    final r = await _api(context, widget.app, method, path, body);
    await _load(quiet: true);
    if (mounted) setState(() => _busy = false);
    return r;
  }

  bool _canRevise(Map<String, dynamic> t) => _canReviseStatus.contains(hcS(t['status'])) || t['can_continue'] == true;

  /// note | answer | plan | revise | off - the same rule as the web page
  String _mode(Map<String, dynamic> t) {
    if (_running(t)) return 'note';
    if (hcS(t['question']).isNotEmpty) return 'answer';
    if (hcS(t['status']) == 'plan_wait') return 'plan';
    if (_canRevise(t)) return 'revise';
    return 'off';
  }

  Future<void> _send([String? words]) async {
    final t = _t;
    if (t == null || _busy) return;
    final mode = _mode(t);
    final text = (words ?? _msg.text).trim();
    if (mode == 'off') return;
    if (text.isEmpty && mode != 'plan' && _comments.isEmpty) return;
    final comments = List<Map<String, dynamic>>.of(_comments);
    Map<String, dynamic>? r;
    if (mode == 'note') {
      r = await _run('POST', '$_base/note', {'text': text, if (comments.isNotEmpty) 'comments': comments});
    } else if (mode == 'answer') {
      // an answer carries no line comments on the server: they are said in the words
      final extra = comments.map((c) => 'Comment on ${hcS(c['path'])}:${hcInt(c['line'])}: ${hcS(c['text'])}').join('\n');
      r = await _run('POST', '$_base/answer', {'text': [text, extra].where((e) => e.isNotEmpty).join('\n\n')});
    } else if (mode == 'plan') {
      r = await _run('POST', '$_base/bg/plan_ok', {'hash': hcS(t['hash']), 'note': text});
    } else {
      r = await _run('POST', '$_base/bg/revise', {'text': text, if (comments.isNotEmpty) 'comments': comments});
    }
    if (r != null && mounted) {
      setState(() {
        if (words == null) _msg.clear();
        if (mode != 'plan') _comments.clear();
      });
    }
  }

  Future<void> _takeBack(int index) async {
    try {
      final r = hcM(await widget.app.api!.call('DELETE', '$_base/note/$index'));
      if (!mounted) return;
      final text = hcS(r['text']);
      if (text.isNotEmpty && _msg.text.trim().isEmpty) {
        _msg.text = text;
        _msg.selection = TextSelection.collapsed(offset: text.length);
      }
      await _load(quiet: true);
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  Future<void> _mergeAsk() async {
    final r = await _run('POST', '$_base/merge_request', const <String, dynamic>{});
    if (r != null && hcS(r['id']).isNotEmpty && mounted) setState(() => _action = r);
  }

  // ---- the ⋯ menu ------------------------------------------------------------------------------------------------
  Future<void> _menu(Map<String, dynamic> t) async {
    final c = CodeColors.of(context);
    final share = hcM(t['share']);
    final pick = await hcSheet<String>(
      context,
      (sheet) {
        Widget item(String id, IconData icon, String label, {bool danger = false}) => InkWell(
              onTap: () => Navigator.pop(sheet, id),
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 52),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Row(children: [
                    Icon(icon, size: 20, color: danger ? c.red : c.ink2),
                    const SizedBox(width: 14),
                    Expanded(child: Text(label, style: HcType.ui(c, 16, color: danger ? c.red : c.ink))),
                  ]),
                ),
              ),
            );
        return SafeArea(
          top: false,
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            HcSheetHead(title: 'Session'),
            const SizedBox(height: 6),
            item('rename', Icons.edit_outlined, 'Rename'),
            item('think', Icons.psychology_outlined, _thinking ? 'Hide what Hoola thought' : 'Show what Hoola thought'),
            if (share['on'] == true) item('share_copy', Icons.link_rounded, 'Copy the share link'),
            item(share['on'] == true ? 'share_off' : 'share_on', Icons.ios_share_rounded,
                share['on'] == true ? 'Stop sharing' : 'Share a read-only link'),
            item(t['archived'] == true ? 'unarchive' : 'archive', Icons.archive_outlined, t['archived'] == true ? 'Unarchive' : 'Archive'),
            item('delete', Icons.delete_outline_rounded, 'Delete', danger: true),
            const SizedBox(height: 12),
          ]),
        );
      },
    );
    if (pick == null || !mounted) return;
    switch (pick) {
      case 'rename': {
        final tc = TextEditingController(text: hcS(t['title']));
        final ok = await showDialog<bool>(
          context: context,
          builder: (d) => AlertDialog(
            title: const Text('Rename session'),
            content: TextField(controller: tc, autofocus: true, maxLength: 200, decoration: const InputDecoration(counterText: '')),
            actions: [
              TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
              TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
            ],
          ),
        );
        final title = tc.text.trim();
        tc.dispose();
        if (ok == true) await _run('PATCH', _base, {'title': title});
      }
      case 'think': {
        setState(() => _thinking = !_thinking);
      }
      case 'share_on': {
        final ok = await showDialog<bool>(
          context: context,
          builder: (d) => AlertDialog(
            title: const Text('Share a read-only link?'),
            content: const Text('Anyone with the link can read this session and its change for 7 days. You can stop it any time.'),
            actions: [
              TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
              TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Share')),
            ],
          ),
        );
        if (ok == true) {
          await _run('POST', '$_base/share', {'on': true});
          _copyShare();
        }
      }
      case 'share_copy': {
        _copyShare();
      }
      case 'share_off': {
        await _run('POST', '$_base/share', {'on': false});
      }
      case 'archive': {
        await _run('PATCH', _base, {'archived': true});
      }
      case 'unarchive': {
        await _run('PATCH', _base, {'archived': false});
      }
      case 'delete': {
        final ok = await showDialog<bool>(
          context: context,
          builder: (d) => AlertDialog(
            title: const Text('Delete this session?'),
            content: const Text('It leaves Hoola for good. Nothing changes on GitHub: an open pull request and its branch stay.'),
            actions: [
              TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
              TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Delete')),
            ],
          ),
        );
        if (ok != true || !mounted) return;
        final r = await _api(context, widget.app, 'DELETE', _base);
        if (r != null && mounted) Navigator.maybePop(context);
      }
    }
  }

  void _copyShare() {
    final path = hcS(hcM(_t?['share'])['path']);
    if (path.isEmpty) return;
    final base = widget.app.api!.baseUrl;
    final url = (base.endsWith('/') ? base.substring(0, base.length - 1) : base) + path;
    Clipboard.setData(ClipboardData(text: url));
    hcSay(context, 'Link copied. It works for 7 days.');
  }

  Future<void> _openChanges(Map<String, dynamic> t) async {
    await Navigator.push<void>(
        context, MaterialPageRoute(builder: (_) => DevChangesPage(app: widget.app, id: widget.id, task: t, comments: _comments)));
    if (!mounted) return;
    setState(() => _askedActions = false);   // a merge card asked for on Changes shows here too
    await _load(quiet: true);
  }

  // ---- steps -----------------------------------------------------------------------------------------------------
  String _plural(int n, String one) => '$n ${n == 1 ? one : '${one}s'}';

  _StepRow? _rowOf(Map<String, dynamic> s) {
    final k = hcS(s['k']);
    final at = DateTime.tryParse(hcS(s['at']));
    _StepRow r(String text, {bool? ok, bool mono = false}) => _StepRow(text, ok: ok, at: at, mono: mono);
    switch (k) {
      case 'rules':
        return r("Read the repo's rules");
      case 'read':
        return r('Read ${hcS(s['path'])}');
      case 'search':
        return r('Searched "${hcS(s['q'])}" · ${_plural(hcInt(s['n']), 'file')}');
      case 'list':
        return r('Looked in ${hcS(s['path']).isEmpty ? '/' : hcS(s['path'])}');
      case 'usages':
        return r('Found where ${hcS(s['name'])} is used · ${_plural(hcInt(s['n']), 'place')}');
      case 'edit':
        return r('Edited ${hcS(s['path'])} +${hcInt(s['added'])} −${hcInt(s['removed'])}');
      case 'new':
        return r('Created ${hcS(s['path'])} +${hcInt(s['added'])}');
      case 'diff':
        return r('Checked its own change · ${_plural(hcInt(s['n']), 'file')}');
      case 'check': {
        final ok = s['ok'] == true;
        return r('Ran your tests · ${ok ? 'passed' : 'failed'}', ok: ok ? null : false);
      }
      case 'check_off':
        return r('Your tests could not run here', ok: false);
      case 'grep':
        return r('Searched the test log for "${hcS(s['q'])}"');
      case 'refused':
        return r('A step was refused: ${hcS(s['why'])}', ok: false);
      case 'bash': {
        final ok = hcInt(s['rc']) == 0 && s['timed_out'] != true;
        return r('\$ ${hcS(s['cmd'])} · ${s['timed_out'] == true ? 'timed out' : 'exit ${hcInt(s['rc'])}'}', ok: ok ? null : false, mono: true);
      }
      case 'compact':
      case 'ws':
      case 'gap':
        return hcS(s['text']).isEmpty ? null : r(hcS(s['text']));
      case 'wait':
        return r(hcS(s['text']).isEmpty ? 'Waiting for a free coding slot' : hcS(s['text']));
      case 'ckpt':
        return r('Checkpoint ${hcInt(s['n'])} saved');
      case 'rewind':
        return r('Went back to checkpoint ${hcInt(s['n'])}');
      case 'pass': {
        const names = {'plan': 'Plan pass', 'review': "Hoola's own review", 'ci_fix': 'CI fix round', 'comments': "Reviewers' comments"};
        final name = names[hcS(s['name'])] ?? hcS(s['name']);
        final end = hcS(s['state']) == 'end';
        final note = hcS(s['note']);
        return r('$name ${end ? 'ended' : 'started'}${note.isEmpty ? '' : ' · $note'}', ok: end && s['ok'] == false ? false : null);
      }
      case 'stopped':
        return r('Stopped. Nothing was pushed.', ok: false);
    }
    return null;   // a kind this app version does not know: skipped
  }

  /// The session's story: her ask, Hoola's words, her notes, thinking (when shown) and the tool steps grouped in cards.
  List<Widget> _story(Map<String, dynamic> t, CodeColors c) {
    final steps = hcList(t['steps']);
    final running = _running(t);
    final out = <Widget>[];
    var group = <_StepRow>[];
    final todos = <List<Map<String, dynamic>>>[];
    var groupNo = 0;
    void flush({bool last = false}) {
      if (group.isEmpty) return;
      out.add(_stepsCard(group, c, groupNo, live: last && running));
      groupNo++;
      group = <_StepRow>[];
    }

    for (final s in steps) {
      final k = hcS(s['k']);
      if (k == 'say') {
        flush();
        out.add(Text(hcS(s['text']), style: HcType.prose(c)));
      } else if (k == 'note') {
        flush();
        out.add(_bubble(hcS(s['text']), c));
      } else if (k == 'think') {
        if (_thinking) {
          flush();
          out.add(Container(
            padding: const EdgeInsets.only(left: 12),
            decoration: BoxDecoration(border: Border(left: BorderSide(color: c.line3, width: 2))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Thinking', style: HcType.ui(c, 12, weight: FontWeight.w600, color: c.ink4)),
              const SizedBox(height: 2),
              Text(hcS(s['text']), maxLines: 14, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink3, height: 1.45)),
            ]),
          ));
        }
      } else if (k == 'todo') {
        todos.add(hcList(s['items']));
      } else {
        final row = _rowOf(s);
        if (row != null) group.add(row);
      }
    }
    flush(last: true);
    if (todos.isNotEmpty && running) out.add(_todoCard(todos.last, c));
    return out;
  }

  Widget _bubble(String text, CodeColors c) => Align(
        alignment: Alignment.centerRight,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * .82),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 11),
            decoration: BoxDecoration(color: c.raised, borderRadius: HoolaRadius.r(18)),
            child: Text(text, maxLines: 20, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 16, height: 1.45)),
          ),
        ),
      );

  Widget _stepsCard(List<_StepRow> rows, CodeColors c, int no, {required bool live}) {
    final open = live || _openGroups.contains(no) || rows.length <= 4;
    final shown = open ? (rows.length > 40 ? rows.sublist(rows.length - 40) : rows) : const <_StepRow>[];
    Widget line(_StepRow r, int i, {required bool runningNow, DateTime? next}) {
      final secs = (r.at != null && next != null) ? next.difference(r.at!).inSeconds : -1;
      return Container(
        constraints: const BoxConstraints(minHeight: 44),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(border: i == 0 ? null : Border(top: BorderSide(color: c.chip))),
        child: Row(children: [
          SizedBox(
            width: 18,
            child: Center(
              child: runningNow
                  ? HcDot(c.accent)
                  : Icon(r.ok == false ? Icons.close_rounded : Icons.check_rounded, size: 16, color: r.ok == false ? c.red : c.green),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(runningNow ? '${r.text}…' : r.text,
                maxLines: 1, overflow: TextOverflow.ellipsis, style: r.mono ? HcType.mono(c, 13, color: c.ink2) : HcType.ui(c, 14, color: c.ink2)),
          ),
          if (secs >= 0) ...[const SizedBox(width: 8), Text(hcClock(secs), style: HcType.ui(c, 12, color: c.ink4))],
        ]),
      );
    }

    final children = <Widget>[];
    if (!open) {
      final a = rows.first.at, b = rows.last.at;
      final secs = (a != null && b != null) ? b.difference(a).inSeconds : 0;
      children.add(InkWell(
        onTap: () => setState(() => _openGroups.add(no)),
        child: Container(
          constraints: const BoxConstraints(minHeight: 44),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(children: [
            Icon(Icons.check_rounded, size: 16, color: c.green),
            const SizedBox(width: 10),
            Expanded(child: Text('${_plural(rows.length, 'step')}${secs > 0 ? ' · ${hcClock(secs)}' : ''}', style: HcType.ui(c, 14, color: c.ink2))),
            Icon(Icons.expand_more_rounded, size: 20, color: c.ink4),
          ]),
        ),
      ));
    } else {
      for (var i = 0; i < shown.length; i++) {
        final isLast = i == shown.length - 1;
        children.add(line(shown[i], i, runningNow: live && isLast, next: isLast ? null : shown[i + 1].at));
      }
      if (!live && _openGroups.contains(no) && rows.length > 4) {
        children.add(InkWell(
          onTap: () => setState(() => _openGroups.remove(no)),
          child: Container(
            constraints: const BoxConstraints(minHeight: 40),
            alignment: Alignment.center,
            decoration: BoxDecoration(border: Border(top: BorderSide(color: c.chip))),
            child: Text('Fold the steps', style: HcType.ui(c, 13, color: c.ink4)),
          ),
        ));
      }
    }
    return Container(
      decoration: BoxDecoration(borderRadius: HoolaRadius.r(14), border: Border.all(color: c.line)),
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children),
    );
  }

  Widget _todoCard(List<Map<String, dynamic>> items, CodeColors c) => Container(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        decoration: BoxDecoration(borderRadius: HoolaRadius.r(14), border: Border.all(color: c.line)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('To do', style: HcType.ui(c, 13, color: c.ink4)),
          const SizedBox(height: 6),
          for (final x in items)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Padding(
                  padding: const EdgeInsets.only(top: 3),
                  child: hcS(x['status']) == 'completed'
                      ? Icon(Icons.check_rounded, size: 14, color: c.green)
                      : (hcS(x['status']) == 'in_progress' ? HcDot(c.accent) : Icon(Icons.circle_outlined, size: 12, color: c.ink4)),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(hcS(x['content']),
                      style: HcType.ui(c, 14, color: hcS(x['status']) == 'completed' ? c.ink4 : c.ink2, height: 1.4)),
                ),
              ]),
            ),
        ]),
      );

  /// A card that asks her (design: "Hoola wants to run a command"): a title, an optional box, cream + outline buttons.
  Widget _askCard(CodeColors c, {required String title, String? body, Widget? extra, List<Widget> buttons = const []}) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: c.sheet, borderRadius: HoolaRadius.r(14), border: Border.all(color: c.line3)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(title, style: HcType.ui(c, 15, weight: FontWeight.w600)),
          if (body != null && body.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
              decoration: BoxDecoration(color: c.bg, borderRadius: HoolaRadius.r(9)),
              child: Text(body, style: HcType.ui(c, 14, height: 1.45)),
            ),
          ],
          if (extra != null) ...[const SizedBox(height: 10), extra],
          if (buttons.isNotEmpty) ...[
            const SizedBox(height: 10),
            Row(children: [
              for (var i = 0; i < buttons.length; i++) ...[
                if (i > 0) const SizedBox(width: 8),
                Expanded(child: buttons[i]),
              ],
            ]),
          ],
        ]),
      );

  Widget _planCard(Map<String, dynamic> t, CodeColors c) {
    final plan = hcM(t['plan']);
    String item(dynamic x) => x is Map ? '${hcS(x['path'])}${hcS(x['why']).isEmpty ? '' : ' - ${hcS(x['why'])}'}' : hcS(x);
    final files = (plan['files'] as List?) ?? const [];
    final steps = (plan['steps'] as List?) ?? const [];
    final done = (plan['done_when'] as List?) ?? const [];
    Widget section(String head, List<String> lines) => Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(head, style: HcType.ui(c, 13, color: c.ink4)),
            const SizedBox(height: 2),
            for (final l in lines) Text(l, style: HcType.ui(c, 14, color: c.ink2, height: 1.4)),
          ]),
        );
    return _askCard(
      c,
      title: 'Hoola has a plan - nothing is touched until you say yes',
      body: hcS(plan['goal']),
      extra: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (files.isNotEmpty) section('Files it will change', [for (final f in files.take(12)) '• ${item(f)}']),
        if (steps.isNotEmpty) section('Steps', [for (var i = 0; i < steps.length && i < 12; i++) '${i + 1}. ${item(steps[i])}']),
        if (done.isNotEmpty) section('Done when', [for (final d in done.take(8)) '✓ ${item(d)}']),
        if (hcS(plan['risk']).isNotEmpty) section('Risk', [hcS(plan['risk'])]),
      ]),
      buttons: [
        HcCreamButton(
            label: 'Yes, start',
            size: 15,
            height: 46,
            onTap: _busy ? null : () => _run('POST', '$_base/bg/plan_ok', {'hash': hcS(t['hash']), 'note': _msg.text.trim()})),
        HcOutlineButton(label: 'Cancel job', onTap: _busy ? null : () => _run('POST', '$_base/cancel')),
      ],
    );
  }

  Widget _questionCard(Map<String, dynamic> t, CodeColors c) {
    final choices = [for (final x in (hcM(t['ws'])['choices'] as List?) ?? const []) '$x'];
    return _askCard(
      c,
      title: 'Hoola asks before it changes anything',
      body: hcS(t['question']),
      extra: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        for (final ch in choices.take(4))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: HcOutlineButton(label: ch, onTap: _busy ? null : () => _send(ch)),
          ),
        Text('Or type your own answer below.', style: HcType.ui(c, 13, color: c.ink4)),
      ]),
    );
  }

  List<Widget> _after(Map<String, dynamic> t, CodeColors c) {
    final st = hcS(t['status']);
    final running = _running(t);
    final out = <Widget>[];
    if (st == 'plan_wait' && hcM(t['plan']).isNotEmpty) out.add(_planCard(t, c));
    if (running || st == 'plan_wait') return out;
    if (hcS(t['error']).isNotEmpty && (st == 'failed' || st == 'refused')) {
      out.add(Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: c.delBg, borderRadius: HoolaRadius.r(14)),
        child: Text('${st == 'refused' ? 'A safety rule stopped this change.' : 'It could not finish.'} ${hcS(t['error'])}',
            style: HcType.ui(c, 14, color: c.delInk, height: 1.45)),
      ));
    }
    if (hcS(t['question']).isNotEmpty) {
      out.add(_questionCard(t, c));
    } else if (hcS(t['explain']).isNotEmpty) {
      out.add(Text(hcS(t['explain']), style: HcType.prose(c)));
    }
    if (hcS(t['risk']).isNotEmpty) out.add(Text('Risk: ${hcS(t['risk'])}', style: HcType.ui(c, 13, color: c.ink4, height: 1.4)));
    final comments = hcList(t['pr_comments']).length;
    final pr = hcInt(t['pr_number']);
    if (st == 'ready' && hcS(t['hash']).isNotEmpty) {
      out.add(_askCard(c,
          title: 'Open the pull request?',
          body: 'Hoola pushes its hoola/ branch and opens a pull request. Nothing is merged.',
          buttons: [
            HcCreamButton(label: 'Open the PR', size: 15, height: 46, onTap: _busy ? null : () => _run('POST', '$_base/push', {'hash': hcS(t['hash'])})),
            HcOutlineButton(label: 'Not now', onTap: _busy ? null : () => _run('POST', '$_base/cancel')),
          ]));
    }
    final acts = <Widget>[
      if (st == 'checks_failed') HcOutlineButton(label: 'Fix the CI failure', icon: Icons.build_outlined, onTap: _busy ? null : () => _run('POST', '$_base/bg/fix_ci')),
      if (comments > 0 && (st == 'pr_open' || st == 'checks_failed'))
        HcOutlineButton(label: 'Fix ${_plural(comments, 'reviewer comment')}', icon: Icons.rate_review_outlined, onTap: _busy ? null : () => _run('POST', '$_base/bg/fix_comments')),
      if ((st == 'pr_open' || st == 'checks_failed') && pr != 0 && _action == null)
        HcOutlineButton(label: 'Merge…', icon: Icons.merge_rounded, onTap: _busy ? null : _mergeAsk),
      if (st == 'pr_open' || st == 'checks_failed' || st == 'ci_running')
        HcOutlineButton(label: 'Check CI again', icon: Icons.sync_rounded, onTap: _busy ? null : () => _run('POST', '$_base/refresh')),
      if (hcS(t['pr_url']).isNotEmpty) HcOutlineButton(label: 'View on GitHub', icon: Icons.open_in_new_rounded, onTap: () => _openGitHub(hcS(t['pr_url']))),
    ];
    if (acts.isNotEmpty) out.add(Wrap(spacing: 8, runSpacing: 8, children: acts));
    if (_action != null) {
      out.add(DevActionCard(key: ValueKey('da${hcS(_action!['id'])}'), app: widget.app, data: {'action': _action!}, onDone: () => _load(quiet: true)));
    }
    return out;
  }

  int _workingSecs(Map<String, dynamic> t) {
    DateTime? from;
    for (final s in hcList(t['steps']).reversed) {
      if (hcS(s['k']) == 'note' || hcS(s['k']) == 'say') {
        from = DateTime.tryParse(hcS(s['at']));
        break;
      }
    }
    from ??= DateTime.tryParse(hcS(t['at']));
    if (from == null) return 0;
    return DateTime.now().difference(from).inSeconds;
  }

  String _metaLine(Map<String, dynamic> t) {
    final mode = switch (hcS(t['mode'])) { 'ask' => 'Ask first', 'plan' => 'Plan first', 'auto' => 'Auto', _ => '' };
    var model = hcS(t['model']).replaceFirst(RegExp(r'^claude-'), '');
    if (model.isNotEmpty) {
      model = model.split('-').map((w) => w.isEmpty ? w : w[0].toUpperCase() + w.substring(1)).join(' ');
    }
    final effort = hcS(t['effort']);
    final inr = hcM(t['cost'])['inr'];
    final cost = inr is num && inr > 0 ? 'Rs ${inr.toStringAsFixed(inr < 10 ? 2 : 0)} so far' : '';
    return [
      mode,
      [model, if (effort.isNotEmpty) effort[0].toUpperCase() + effort.substring(1)].where((e) => e.isNotEmpty).join(' · '),
      cost,
    ].where((e) => e.isNotEmpty).join('   ');
  }

  // ---- the page ----------------------------------------------------------------------------------------------------
  @override
  Widget build(BuildContext context) {
    return Builder(builder: (context) {
      final c = CodeColors.of(context);
      final t = _t;
      return Scaffold(
        backgroundColor: c.bg,
        drawer: DevCodeDrawer(app: widget.app, current: widget.id),
        drawerScrimColor: c.scrim,
        body: SafeArea(
          child: t == null
              ? Column(children: [
                  _header(c, null),
                  Expanded(child: Center(child: CircularProgressIndicator(strokeWidth: 2, color: c.accent))),
                ])
              : Column(children: [
                  _header(c, t),
                  if (_busy) LinearProgressIndicator(minHeight: 2, color: c.accent, backgroundColor: c.line),
                  Expanded(
                    child: RefreshIndicator(
                      color: c.accent,
                      onRefresh: _load,
                      child: ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          for (final w in _body(t, c)) Padding(padding: const EdgeInsets.only(bottom: 14), child: w),
                        ],
                      ),
                    ),
                  ),
                  _bottom(t, c),
                ]),
        ),
      );
    });
  }

  Widget _header(CodeColors c, Map<String, dynamic>? t) {
    final st = t == null ? const [0, 0] : devStat(t);
    final env = t == null ? '' : hcS(hcM(t['env'])['name']);
    final sub = t == null ? '' : [hcShortRepo(hcS(t['repo'])), env].where((e) => e.isNotEmpty).join(' · ');
    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
      child: Row(children: [
        Builder(builder: (ctx) => HcIconButton(icon: Icons.notes_rounded, label: 'Sessions', onTap: () => Scaffold.of(ctx).openDrawer())),
        Expanded(
          child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(t == null ? 'Hoola Code' : hcS(t['title']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 16, weight: FontWeight.w600)),
            if (sub.isNotEmpty) Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink4)),
          ]),
        ),
        if (t != null && hcList(t['files']).isNotEmpty)
          Semantics(
            button: true,
            label: 'Changes: ${st[0]} lines added, ${st[1]} removed',
            excludeSemantics: true,
            child: Material(
              color: c.surface,
              shape: const StadiumBorder(),
              child: InkWell(
                customBorder: const StadiumBorder(),
                onTap: () => _openChanges(t),
                child: Container(
                  height: 36,
                  constraints: const BoxConstraints(minWidth: 48),
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  alignment: Alignment.center,
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Text('+${st[0]}', style: HcType.mono(c, 13, color: c.green)),
                    const SizedBox(width: 6),
                    Text('−${st[1]}', style: HcType.mono(c, 13, color: c.red)),
                  ]),
                ),
              ),
            ),
          ),
        if (t != null) HcIconButton(icon: Icons.more_horiz_rounded, label: 'Session menu', onTap: () => _menu(t)),
      ]),
    );
  }

  List<Widget> _body(Map<String, dynamic> t, CodeColors c) {
    final running = _running(t);
    return [
      _bubble(hcS(t['text']).isNotEmpty ? hcS(t['text']) : hcS(t['title']), c),
      ..._story(t, c),
      ..._after(t, c),
      if (running)
        Row(children: [
          HcDot(t['stopping'] == true ? c.amber : c.accent, size: 9),
          const SizedBox(width: 10),
          Text(t['stopping'] == true ? 'Stopping after this step' : 'Working · ${hcClock(_workingSecs(t))}',
              style: HcType.ui(c, 14, color: c.ink3)),
        ]),
    ];
  }

  Widget _bottom(Map<String, dynamic> t, CodeColors c) {
    final mode = _mode(t);
    final running = _running(t);
    final notes = running ? [for (final n in (t['notes'] as List?) ?? const []) '$n'] : const <String>[];
    const hints = {
      'note': 'Steer or queue a message',
      'answer': 'Type your answer',
      'plan': 'Add a note for the plan',
      'revise': 'Ask for a change',
    };
    final hint = mode == 'revise' ? hcS(t['hint']) : '';
    final meta = _metaLine(t);
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 10),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 6, children: [
          for (final (i, n) in notes.indexed)
            _smallChip(c, '${i == 0 ? '${notes.length} queued: ' : ''}“${n.length > 40 ? '${n.substring(0, 40)}…' : n}”',
                'Take back this queued message', () => _takeBack(i), icon: Icons.undo_rounded),
          if (_comments.isNotEmpty)
            _smallChip(c, '${_plural(_comments.length, 'comment')} on the diff go with your next message', 'Clear the comments',
                () => setState(() => _comments.clear()), icon: Icons.close_rounded),
          if (hint.isNotEmpty)
            _smallChip(c, hint, 'Use this suggestion', () {
              _msg.text = hint;
              _msg.selection = TextSelection.collapsed(offset: hint.length);
            }, icon: Icons.lightbulb_outline_rounded),
        ]),
        if (notes.isNotEmpty || _comments.isNotEmpty || hint.isNotEmpty) const SizedBox(height: 8),
        if (mode == 'off')
          Padding(
            padding: const EdgeInsets.fromLTRB(6, 4, 6, 4),
            child: Text('This session is finished. Start a new one from the drawer.', style: HcType.ui(c, 13, color: c.ink4)),
          )
        else
          HcComposer(
            controller: _msg,
            hint: hints[mode] ?? '',
            language: widget.app.language,
            busy: _busy,
            onSend: () => _send(),
            onStop: running ? () => _run('POST', '$_base/stop') : null,
            stopping: t['stopping'] == true,
          ),
        if (meta.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Center(child: Text(meta, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink3))),
          ),
      ]),
    );
  }

  Widget _smallChip(CodeColors c, String text, String semantics, VoidCallback onTap, {IconData? icon}) => Semantics(
        button: true,
        label: '$text. $semantics',
        excludeSemantics: true,
        child: Material(
          color: Colors.transparent,
          shape: StadiumBorder(side: BorderSide(color: c.line3)),
          child: InkWell(
            customBorder: const StadiumBorder(),
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 32),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Flexible(child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink4))),
                  if (icon != null) ...[const SizedBox(width: 6), Icon(icon, size: 14, color: c.ink4)],
                ]),
              ),
            ),
          ),
        ),
      );
}

// ================================================================================================== Changes
class _DiffLine {
  _DiffLine(this.n, this.sign, this.text, {this.hunk = false});
  final int n;          // the line number shown (new side; old side for a removed line), 0 = none
  final String sign;    // '+', '-', ' '
  final String text;
  final bool hunk;
}

List<_DiffLine> _parseDiff(String diff) {
  final out = <_DiffLine>[];
  var oldN = 0, newN = 0;
  final hunk = RegExp(r'^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$');
  for (final raw in diff.split('\n')) {
    if (raw.startsWith('diff ') || raw.startsWith('index ') || raw.startsWith('--- ') || raw.startsWith('+++ ') || raw.startsWith('\\ ')) continue;
    final m = hunk.firstMatch(raw);
    if (m != null) {
      oldN = int.parse(m.group(1)!);
      newN = int.parse(m.group(2)!);
      out.add(_DiffLine(0, ' ', m.group(3)!.trim().isEmpty ? '⋯' : '⋯ ${m.group(3)!.trim()}', hunk: true));
      continue;
    }
    if (raw.startsWith('+')) {
      out.add(_DiffLine(newN, '+', raw.substring(1)));
      newN++;
    } else if (raw.startsWith('-')) {
      out.add(_DiffLine(oldN, '-', raw.substring(1)));
      oldN++;
    } else {
      final text = raw.startsWith(' ') ? raw.substring(1) : raw;
      if (raw.isEmpty && out.isNotEmpty && oldN == 0 && newN == 0) continue;
      out.add(_DiffLine(newN, ' ', text));
      oldN++;
      newN++;
    }
  }
  while (out.isNotEmpty && out.last.text.isEmpty && out.last.sign == ' ') {
    out.removeLast();
  }
  return out;
}

/// The Changes page of one session.
class DevChangesPage extends StatelessWidget {
  const DevChangesPage({super.key, required this.app, required this.id, required this.task, required this.comments});
  final Santosh app;
  final String id;
  final Map<String, dynamic> task;
  final List<Map<String, dynamic>> comments;

  @override
  Widget build(BuildContext context) => HoolaTheme(appearance: app.appearance, child: _DevChangesPageBody(app: app, id: id, task: task, comments: comments));
}

class _DevChangesPageBody extends StatefulWidget {
  const _DevChangesPageBody({super.key, required this.app, required this.id, required this.task, required this.comments});
  final Santosh app;
  final String id;
  final Map<String, dynamic> task;
  final List<Map<String, dynamic>> comments;   // shared with the session page: they ride her next message

  @override
  State<_DevChangesPageBody> createState() => _DevChangesPageState();
}

class _DevChangesPageState extends State<_DevChangesPageBody> {
  late Map<String, dynamic> _t = widget.task;
  String _file = '';
  bool _busy = false;

  String get _base => '/api/devsahayak/tasks/${widget.id}';

  @override
  void initState() {
    super.initState();
    final files = hcList(_t['file_diffs']);
    if (files.isNotEmpty) _file = hcS(files.first['path']);
  }

  Future<void> _reload() async {
    try {
      final t = hcM(await widget.app.api!.call('GET', _base));
      if (mounted) setState(() => _t = t);
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _api(context, widget.app, method, path, body);
    await _reload();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  Future<void> _comment(_DiffLine l) async {
    final tc = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text('Comment on line ${l.n}'),
        content: TextField(
          controller: tc,
          autofocus: true,
          minLines: 2,
          maxLines: 6,
          maxLength: 1000,
          decoration: const InputDecoration(hintText: 'What should change here?', counterText: ''),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Add comment')),
        ],
      ),
    );
    final text = tc.text.trim();
    tc.dispose();
    if (ok != true || text.isEmpty || !mounted) return;
    setState(() => widget.comments.add({'path': _file, 'line': l.n, 'code': l.text.trim(), 'text': text}));
  }

  String _ciLine(Map<String, dynamic> ci) {
    final rows = hcList(ci['rows']);
    final st = hcS(ci['state']);
    if (rows.isEmpty) return st == 'pending' ? 'CI starting' : (st == 'none' || st.isEmpty ? 'No CI' : hcS(ci['say']));
    final passed = rows.where((r) => hcS(r['state']) == 'success').length;
    final failed = rows.where((r) => hcS(r['state']) == 'failure').length;
    if (failed > 0) return 'CI · $failed of ${rows.length} failed';
    if (passed == rows.length) return 'CI · $passed of ${rows.length} passed';
    return 'CI · $passed of ${rows.length} passed, ${rows.length - passed - failed} running';
  }

  @override
  Widget build(BuildContext context) {
    return Builder(builder: (context) {
      final c = CodeColors.of(context);
      final t = _t;
      final st = devStat(t);
      final status = hcS(t['status']);
      final pr = hcInt(t['pr_number']);
      final ci = hcM(t['ci']);
      final ciState = hcS(ci['state']);
      final files = hcList(t['file_diffs']);
      var diff = '';
      for (final f in files) {
        if (hcS(f['path']) == _file) diff = hcS(f['diff']);
      }
      final lines = _parseDiff(diff);
      final shown = lines.length > 1500 ? lines.sublist(0, 1500) : lines;
      final longest = shown.fold<int>(0, (m, l) => l.text.length > m ? l.text.length : m);
      final screenW = MediaQuery.sizeOf(context).width;
      final rowW = [screenW, 12 + 30 + 6 + 14 + 6 + longest * 8.4 + 24].reduce((a, b) => a > b ? a : b);
      final branch = hcS(t['branch']);
      final base = hcS(t['base']);

      final prLabel = pr == 0
          ? (status == 'ready' ? 'Ready for a PR' : 'Not pushed yet')
          : switch (status) {
              'ci_running' => 'Draft PR #$pr',
              'merged' => 'Merged #$pr',
              'closed' => 'Closed #$pr',
              _ => 'PR #$pr',
            };
      final prColor = status == 'closed' ? c.ink4 : (status == 'merged' ? c.accent : c.green);
      Widget? primary;
      if (status == 'ready' && hcS(t['hash']).isNotEmpty) {
        primary = HcCreamButton(label: 'Open the PR', size: 15, height: 46, onTap: _busy ? null : () => _run('POST', '$_base/push', {'hash': hcS(t['hash'])}));
      } else if ((status == 'pr_open' || status == 'checks_failed') && pr != 0) {
        primary = HcCreamButton(
            label: 'Ask to merge',
            size: 15,
            height: 46,
            onTap: _busy
                ? null
                : () async {
                    final r = await _run('POST', '$_base/merge_request', const <String, dynamic>{});
                    if (r != null && mounted) hcSay(context, 'A merge card is waiting for your tap in the session.');
                  });
      }
      final gh = hcS(t['pr_url']).isNotEmpty ? HcOutlineButton(label: 'View on GitHub', onTap: () => _openGitHub(hcS(t['pr_url']))) : null;

      return Scaffold(
        backgroundColor: c.bg,
        body: SafeArea(
          child: Column(children: [
            Container(
              height: 56,
              padding: const EdgeInsets.symmetric(horizontal: 4),
              decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
              child: Row(children: [
                HcIconButton(icon: Icons.arrow_back_ios_new_rounded, label: 'Back', color: c.ink, size: 20, onTap: () => Navigator.maybePop(context)),
                Expanded(
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Changes', style: HcType.ui(c, 16, weight: FontWeight.w600)),
                    if (branch.isNotEmpty || base.isNotEmpty)
                      Text('${branch.isEmpty ? 'not pushed' : branch} → ${base.isEmpty ? 'default' : base}',
                          maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.mono(c, 13, color: c.ink4)),
                  ]),
                ),
                Padding(
                  padding: const EdgeInsets.only(right: 12),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Text('+${st[0]}', style: HcType.mono(c, 13, color: c.green)),
                    const SizedBox(width: 6),
                    Text('−${st[1]}', style: HcType.mono(c, 13, color: c.red)),
                  ]),
                ),
              ]),
            ),
            if (_busy) LinearProgressIndicator(minHeight: 2, color: c.accent, backgroundColor: c.line),
            Container(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
              decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Row(children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                    decoration: BoxDecoration(color: pr == 0 ? c.chip : c.greenSoft, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
                    child: Text(prLabel, style: HcType.ui(c, 13, weight: FontWeight.w600, color: pr == 0 ? c.ink3 : prColor)),
                  ),
                  const SizedBox(width: 10),
                  if (pr != 0)
                    Expanded(
                      child: Row(children: [
                        if (ciState == 'success') ...[Icon(Icons.check_rounded, size: 16, color: c.green), const SizedBox(width: 4)],
                        if (ciState == 'failure') ...[Icon(Icons.close_rounded, size: 16, color: c.red), const SizedBox(width: 4)],
                        Flexible(child: Text(_ciLine(ci), maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 14, color: c.ink3))),
                      ]),
                    ),
                ]),
                if (primary != null || gh != null) ...[
                  const SizedBox(height: 10),
                  Row(children: [
                    if (primary != null) Expanded(child: primary),
                    if (primary != null && gh != null) const SizedBox(width: 8),
                    if (gh != null) Expanded(child: gh),
                  ]),
                ],
                if (pr != 0 && status != 'merged' && status != 'closed') ...[
                  const SizedBox(height: 6),
                  Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Auto-fix', style: HcType.ui(c, 15)),
                        Text('Fix failing CI by itself', style: HcType.ui(c, 13, color: c.ink4)),
                      ]),
                    ),
                    HcSwitch(
                      value: t['auto_fix'] != false,
                      label: 'Auto-fix',
                      onChanged: _busy ? null : (v) => _run('PATCH', _base, {'auto_fix': v}),
                    ),
                  ]),
                ],
              ]),
            ),
            if (files.isNotEmpty)
              SizedBox(
                height: 56,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  children: [
                    for (final f in files)
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: Semantics(
                          button: true,
                          selected: hcS(f['path']) == _file,
                          label: hcS(f['path']),
                          excludeSemantics: true,
                          child: Material(
                            color: hcS(f['path']) == _file ? c.raised : Colors.transparent,
                            shape: StadiumBorder(side: BorderSide(color: hcS(f['path']) == _file ? Colors.transparent : c.line3)),
                            child: InkWell(
                              customBorder: const StadiumBorder(),
                              onTap: () => setState(() => _file = hcS(f['path'])),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                                child: Text(hcS(f['path']),
                                    style: HcType.mono(c, 13, color: hcS(f['path']) == _file ? c.ink : c.ink3, height: 1.2)),
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            Expanded(
              child: files.isEmpty
                  ? Center(child: Text('No changed files yet.', style: HcType.ui(c, 14, color: c.ink4)))
                  : diff.trim().isEmpty
                      ? Center(child: Text('The lines of this change are not ready yet.', style: HcType.ui(c, 14, color: c.ink4)))
                      : ListView(
                          padding: const EdgeInsets.only(bottom: 12),
                          children: [
                            SingleChildScrollView(
                              scrollDirection: Axis.horizontal,
                              child: SizedBox(
                                width: rowW,
                                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                                  for (final l in shown) _diffRow(l, c),
                                  if (lines.length > shown.length)
                                    Padding(
                                      padding: const EdgeInsets.all(12),
                                      child: Text('… ${lines.length - shown.length} more lines', style: HcType.ui(c, 13, color: c.ink4)),
                                    ),
                                ]),
                              ),
                            ),
                            for (final cm in widget.comments.where((x) => hcS(x['path']) == _file)) _commentCard(cm, c),
                          ],
                        ),
            ),
            Container(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 14),
              decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
              child: Text('Long-press a line to comment · merging is always your tap',
                  textAlign: TextAlign.center, style: HcType.ui(c, 13, color: c.ink4)),
            ),
          ]),
        ),
      );
    });
  }

  Widget _diffRow(_DiffLine l, CodeColors c) {
    final bg = l.sign == '+' ? c.addBg : (l.sign == '-' ? c.delBg : Colors.transparent);
    final ink = l.hunk ? c.ink5 : (l.sign == '+' ? c.addInk : (l.sign == '-' ? c.delInk : c.ink3));
    final row = Container(
      color: bg,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Row(children: [
        SizedBox(
          width: 30,
          child: Text(l.n == 0 ? '' : '${l.n}', textAlign: TextAlign.right, style: HcType.mono(c, 13, color: c.ink5, height: 1.65)),
        ),
        const SizedBox(width: 6),
        SizedBox(width: 14, child: Text(l.sign == ' ' ? '' : l.sign, textAlign: TextAlign.center, style: HcType.mono(c, 13, color: ink, height: 1.65))),
        const SizedBox(width: 6),
        Expanded(child: Text(l.text.isEmpty ? ' ' : l.text, softWrap: false, overflow: TextOverflow.clip, style: HcType.mono(c, 13, color: ink, height: 1.65))),
      ]),
    );
    if (l.hunk || l.n == 0) return row;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onLongPress: () => _comment(l),
      child: Semantics(onLongPressHint: 'Comment on this line', child: row),
    );
  }

  Widget _commentCard(Map<String, dynamic> cm, CodeColors c) => Container(
        margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: c.sheet, borderRadius: HoolaRadius.r(HoolaRadius.tile), border: Border.all(color: c.line3)),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Comment on line ${hcInt(cm['line'])}', style: HcType.ui(c, 13, color: c.ink4)),
              const SizedBox(height: 8),
              Text(hcS(cm['text']), style: HcType.ui(c, 15, height: 1.4)),
              const SizedBox(height: 8),
              Text('Goes with your next message', style: HcType.ui(c, 13, color: c.accentInk)),
            ]),
          ),
          HcIconButton(icon: Icons.close_rounded, label: 'Remove comment', size: 18, onTap: () => setState(() => widget.comments.remove(cm))),
        ]),
      );
}
