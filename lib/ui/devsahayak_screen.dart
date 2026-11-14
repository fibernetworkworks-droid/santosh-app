/// Profile > Hoola Code: Hoola as a software developer in HER GitHub repos, laid out like the web page (/console/code).
/// Sessions (Working / Needs you / Earlier, a New session box, one page per session: her ask, the steps, the change,
/// the status, a message box) · Scheduled (see, Run now, Pause) · Review (her team's PRs, draft reviews she posts) ·
/// Merge / Deploy (cards waiting for her tap) · Repos · Rules (token typed only here, limits, review mode).
/// Merge, deploy, posting a review and opening a PR that waits happen ONLY from her tap on these cards.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'desk/desk_kit.dart';
import 'devsahayak_new.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _ciColor(String s) => switch (s) { 'success' => C.ok, 'failure' => C.bad, 'pending' => C.warn, _ => C.muted };
String _ciLabel(String s) => switch (s) { 'success' => 'CI pass', 'failure' => 'CI fail', 'pending' => 'CI running', _ => 'No CI' };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Continue', bool obscureFirst = false, Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (i, (k, label)) in fields.indexed)
            TextField(
              controller: c[k],
              obscureText: obscureFirst && i == 0,
              autocorrect: !(obscureFirst && i == 0),
              enableSuggestions: !(obscureFirst && i == 0),
              decoration: InputDecoration(labelText: label),
              maxLines: (obscureFirst && i == 0) ? 1 : (k == 'text' || k == 'summary' || k == 'rules' ? 5 : 1),
            ),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

Future<Map<String, dynamic>?> _call(BuildContext context, Santosh app, String method, String path, [Object? body]) async {
  try {
    final r = await app.api!.call(method, path, body: body, timeout: const Duration(minutes: 4));
    final m = _m(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Future<void> _open(String url) async {
  if (url.startsWith('https://github.com/')) await Native.openExternal(url: url);
}

// ---- the session model, the same rules as the web page (/console/code, code.js) ----
const Map<String, String> _statusWords = {
  'new': 'Starting',
  'plan_wait': 'Plan waits for your OK',
  'ready': 'Ready - open the PR?',
  'pr_open': 'PR open',
  'ci_running': 'CI running',
  'checks_failed': 'CI failed',
  'merged': 'Merged',
  'closed': 'PR closed',
  'explained': 'Explained',
  'refused': 'Stopped by a safety rule',
  'failed': 'Could not finish',
  'cancelled': 'Stopped',
};
const List<String> _needsStatus = ['plan_wait', 'ready', 'checks_failed', 'refused'];
const List<String> _canReviseStatus = ['pr_open', 'checks_failed', 'ready', 'refused'];
const List<List<String>> _modes = [
  ['ask', 'Ask before the PR'],
  ['auto', 'Work and open the PR'],
  ['plan', 'Plan first'],
];

int _int(dynamic v) => v is num ? v.toInt() : (int.tryParse('${v ?? ''}') ?? 0);
bool _running(Map<String, dynamic> t) => t['running'] == true;
String _statusLabel(Map<String, dynamic> t) => _statusWords[_s(t['status'])] ?? _s(t['status']);

bool _needsYou(Map<String, dynamic> t, List<Map<String, dynamic>> actions) {
  if (_s(t['question']).isNotEmpty) return true;
  if (_needsStatus.contains(_s(t['status']))) return true;
  final pr = _int(t['pr_number']);
  if (pr == 0) return false;
  for (final a in actions) {
    if (_s(a['status']) == 'waiting' && _s(a['repo']) == _s(t['repo']) && _int(a['pr_number']) == pr) return true;
  }
  return false;
}

/// 'run' | 'need' | 'old'
String _groupOf(Map<String, dynamic> t, List<Map<String, dynamic>> actions) =>
    _running(t) ? 'run' : (_needsYou(t, actions) ? 'need' : 'old');

Color _dotColor(Map<String, dynamic> t, String group) {
  if (group == 'run') return C.accent;
  if (group == 'need') return C.warn;
  if (_s(t['status']) == 'merged') return C.ok;
  if (_s(t['status']) == 'failed') return C.bad;
  return C.faint;
}

String _subWords(Map<String, dynamic> t) {
  if (_running(t)) return 'Working';
  if (_s(t['question']).isNotEmpty) return 'Hoola asks you a question';
  return _statusLabel(t);
}

String _repoShort(String full) {
  final i = full.indexOf('/');
  return i < 0 ? full : full.substring(i + 1);
}

String _titleOf(Map<String, dynamic> t) => _s(t['title']).isNotEmpty ? _s(t['title']) : _s(t['number']);

/// Lines added / removed over all changed files: [added, removed].
List<int> _stat(Map<String, dynamic> t) {
  var a = 0;
  var r = 0;
  for (final f in _list(t['files'])) {
    a += _int(f['added']);
    r += _int(f['removed']);
  }
  return [a, r];
}

Widget _statText(List<int> st, {double size = 12}) {
  if (st[0] == 0 && st[1] == 0) return const SizedBox.shrink();
  return Row(mainAxisSize: MainAxisSize.min, children: [
    Text('+${st[0]}', style: TextStyle(fontSize: size, color: C.ok, fontFamily: 'monospace')),
    const SizedBox(width: 6),
    Text('−${st[1]}', style: TextStyle(fontSize: size, color: C.bad, fontFamily: 'monospace')),
  ]);
}

String _dur(int seconds) {
  final s = seconds < 0 ? 0 : seconds;
  if (s < 60) return '$s s';
  if (s < 3600) return '${s ~/ 60} min ${(s % 60).toString().padLeft(2, '0')} s';
  return '${s ~/ 3600} h ${((s % 3600) ~/ 60).toString().padLeft(2, '0')} min';
}

String _ago(String iso) {
  final d = DateTime.tryParse(iso);
  if (d == null) return '';
  final m = DateTime.now().difference(d).inMinutes;
  if (m < 1) return 'just now';
  if (m < 60) return '$m min ago';
  if (m < 1440) return '${(m / 60).round()} h ago';
  return '${(m / 1440).round()} days ago';
}

String _until(String iso) {
  final d = DateTime.tryParse(iso);
  if (d == null) return '';
  final m = d.difference(DateTime.now()).inMinutes;
  if (m < 1) return 'in a minute';
  if (m < 60) return 'in $m min';
  if (m < 1440) return 'in ${(m / 60).round()} h';
  return 'in ${(m / 1440).round()} days';
}

String _plural(int n, String one, [String? many]) => '$n ${n == 1 ? one : (many ?? '${one}s')}';

class DevsahayakScreen extends StatefulWidget {
  const DevsahayakScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<DevsahayakScreen> createState() => _DevsahayakScreenState();
}

class _DevsahayakScreenState extends State<DevsahayakScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  bool _busy = false;
  List<Map<String, dynamic>> _prs = [];
  String _repo = '';
  final String _mode = '';   // v0.878 the mode is picked on the New session page now

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/devsahayak'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    if (mounted) setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  Map<String, dynamic> get _st => _m(_d?['settings']);

  void _openTask(String id) {
    if (id.isEmpty) return;
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => DevTaskPage(app: widget.app, id: id))).then((_) => _load());
  }

  // ---- sessions -------------------------------------------------------------------------------------------------
  List<String> get _repoNames => [for (final r in _list(_d?['repos'])) if (_s(r['repo']).isNotEmpty) _s(r['repo'])];

  String get _repoNow {
    final names = _repoNames;
    if (names.contains(_repo)) return _repo;
    final def = _s(_st['default_repo']);
    if (names.contains(def)) return def;
    return names.isEmpty ? '' : names.first;
  }

  String get _modeNow => _mode.isNotEmpty ? _mode : (_st['ask_before_pr'] == true ? 'ask' : 'auto');

  /// v0.878 New session opens its own page, like Claude Code's mobile Code tab: the environment chip, the repository
  /// chip and one composer (devsahayak_new.dart).
  Future<void> _newPage() async {
    final id = await Navigator.push<String>(
        context,
        MaterialPageRoute(
            builder: (_) => DevNewSessionPage(app: widget.app, repos: List<String>.of(_repoNames), repo: _repoNow, mode: _modeNow, modes: _modes)));
    if (!mounted) return;
    await _load();
    if (id != null && id.isNotEmpty) _openTask(id);
  }

  Widget _newSession() {
    return Press(
      onTap: _busy ? null : _newPage,
      child: Glass(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        child: Row(children: [
          const Icon(Icons.add_circle_outline_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('New session', style: display(15)),
              const SizedBox(height: 2),
              Text(_repoNow.isEmpty ? 'Pick an environment and a repository' : 'In ${_repoShort(_repoNow)} · pick an environment',
                  style: const TextStyle(fontSize: 12, color: C.muted)),
            ]),
          ),
          const Icon(Icons.chevron_right_rounded, color: C.muted),
        ]),
      ),
    );
  }

  Widget _sessionRow(Map<String, dynamic> t, String group) {
    final sub = [_repoShort(_s(t['repo'])), _subWords(t), _ago(_s(t['updated']).isNotEmpty ? _s(t['updated']) : _s(t['at']))]
        .where((e) => e.isNotEmpty)
        .join(' · ');
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _openTask(_s(t['id'])),
        child: Glass(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          border: group == 'need' ? C.warn : null,
          child: Row(children: [
            Container(width: 9, height: 9, decoration: BoxDecoration(color: _dotColor(t, group), shape: BoxShape.circle)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_titleOf(t), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12)),
              ]),
            ),
            const SizedBox(width: 8),
            _statText(_stat(t)),
          ]),
        ),
      ),
    );
  }

  Widget _sessions() {
    final tasks = _list(_d?['tasks']);
    final actions = _list(_d?['actions']);
    final by = <String, List<Map<String, dynamic>>>{'run': [], 'need': [], 'old': []};
    for (final t in tasks) {
      by[_groupOf(t, actions)]!.add(t);
    }
    const names = {'run': 'Working', 'need': 'Needs you', 'old': 'Earlier'};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (_st['github'] != true)
        Glass(
          border: C.warn,
          margin: const EdgeInsets.only(bottom: 8),
          child: const Text('Connect GitHub first: add your fine-grained token in Rules. It is typed only there.', style: TextStyle(fontSize: 13)),
        ),
      _newSession(),
      const SizedBox(height: 12),
      if (tasks.isEmpty) const Text('No sessions yet.', style: TextStyle(color: C.muted)),
      for (final g in const ['run', 'need', 'old'])
        if (by[g]!.isNotEmpty) ...[
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 6),
            child: Text('${names[g]} · ${by[g]!.length}', style: const TextStyle(fontSize: 12.5, color: C.muted, fontWeight: FontWeight.w600)),
          ),
          for (final t in by[g]!) _sessionRow(t, g),
        ],
    ]);
  }

  // ---- scheduled tasks (made on the web console; here: see them, Run now, Pause / Resume) ---------------------------
  Widget _scheduled() {
    final list = _list(_d?['schedules']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('A coding task that starts by itself. Every run is an ordinary session, and merging is always your tap.',
          style: TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 8),
      if (list.isEmpty) const Text('No scheduled tasks yet.', style: TextStyle(color: C.muted)),
      for (final sc in list)
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(_s(sc['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700))),
              const SizedBox(width: 8),
              Pill(sc['enabled'] != true ? 'Paused' : (_s(sc['next_run']).isNotEmpty ? 'Next run ${_until(_s(sc['next_run']))}' : 'On demand')),
            ]),
            const SizedBox(height: 4),
            Text([_repoShort(_s(sc['repo'])), _s(sc['when'])].where((e) => e.isNotEmpty).join(' · '), style: const TextStyle(fontSize: 12, color: C.muted)),
            if (_s(sc['last_note']).isNotEmpty) Text(_s(sc['last_note']), style: const TextStyle(fontSize: 12, color: C.bad)),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(
                child: GlassButton(
                    label: 'Run now',
                    icon: Icons.play_arrow_rounded,
                    height: 42,
                    onTap: _busy
                        ? null
                        : () async {
                            final r = await _run('POST', '/api/devsahayak/schedules/${_s(sc['id'])}/run');
                            if (r != null && _s(r['id']).isNotEmpty && mounted) _openTask(_s(r['id']));
                          }),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: GlassButton(
                    label: sc['enabled'] == true ? 'Pause' : 'Resume',
                    icon: sc['enabled'] == true ? Icons.pause_rounded : Icons.play_circle_outline_rounded,
                    height: 42,
                    onTap: _busy ? null : () => _run('PATCH', '/api/devsahayak/schedules/${_s(sc['id'])}', {'enabled': sc['enabled'] != true})),
              ),
            ]),
            for (final r in _list(sc['runs']).take(4))
              InkWell(
                onTap: () => _openTask(_s(r['id'])),
                child: Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                      '${_s(r['title']).isNotEmpty ? _s(r['title']) : _s(r['number'])} · ${_statusWords[_s(r['status'])] ?? _s(r['status'])} · ${_ago(_s(r['at']))}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12, color: C.chip)),
                ),
              ),
          ]),
        ),
      const SizedBox(height: 4),
      const Text('Make new ones on the web console (Hoola Code > Scheduled).', style: TextStyle(fontSize: 12, color: C.faint)),
    ]);
  }

  Future<void> _loadPrs(String repo) async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/devsahayak/prs', query: {if (repo.isNotEmpty) 'repo': repo}));
      if (mounted) setState(() => _prs = _list(r['prs']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _review() {
    final reviews = _list(_d?['reviews']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Expanded(child: GlassButton(label: 'See open PRs', icon: Icons.call_split_rounded, onTap: _busy ? null : () => _loadPrs(_repoNow))),
      ]),
      const SizedBox(height: 8),
      for (final p in _prs)
        ListTile(
          contentPadding: EdgeInsets.zero,
          dense: true,
          title: Text('#${p['number']} ${_s(p['title'])}'),
          subtitle: Text('${_s(p['author'])}${p['by_hoola'] == true ? ' · Hoola\'s' : ''}${p['draft'] == true ? ' · draft' : ''}'),
          trailing: Wrap(spacing: 4, children: [
            IconButton(
                tooltip: 'Review',
                icon: const Icon(Icons.rate_review_rounded),
                onPressed: _busy ? null : () => _run('POST', '/api/devsahayak/reviews', {'repo': _s(p['repo']).isNotEmpty ? _s(p['repo']) : _repoNow, 'pr': p['number']})),
            IconButton(
                tooltip: 'Merge card',
                icon: const Icon(Icons.merge_rounded),
                onPressed: _busy ? null : () => _run('POST', '/api/devsahayak/merge_request', {'repo': _s(p['repo']).isNotEmpty ? _s(p['repo']) : _repoNow, 'pr': p['number']})),
          ]),
        ),
      const SizedBox(height: 8),
      for (final r in reviews)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: DevReviewCard(app: widget.app, data: {'review': r}, onDone: _load)),
      if (reviews.isEmpty) const Text('No reviews yet.', style: TextStyle(color: C.muted)),
    ]);
  }

  Widget _actions() {
    final acts = _list(_d?['actions']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      GlassButton(label: 'Ask for a deploy card', icon: Icons.rocket_launch_rounded, onTap: _busy ? null : _deploy),
      const SizedBox(height: 10),
      if (acts.isEmpty) const Text('No merge / deploy cards.', style: TextStyle(color: C.muted)),
      for (final a in acts)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: DevActionCard(app: widget.app, data: {'action': a}, onDone: _load)),
    ]);
  }

  Future<void> _deploy() async {
    final f = await _form(context, 'Deploy (your repo\'s own workflow)', const [
      ('repo', 'Repo (empty = default)'),
      ('workflow', 'Workflow file (empty = the one set in the repo)'),
      ('ref', 'Branch (empty = default)'),
      ('env', "Input 'env' (if any)"),
    ], ok: 'Make card');
    if (f == null) return;
    await _run('POST', '/api/devsahayak/deploy_request', {
      for (final k in ['repo', 'workflow', 'ref']) if ((f[k] ?? '').isNotEmpty) k: f[k],
      if ((f['env'] ?? '').isNotEmpty) 'inputs': {'env': f['env']},
    });
  }

  Future<void> _addRepo() async {
    final f = await _form(context, 'Add repo', const [
      ('repo', 'owner/name'),
      ('deploy_workflow', 'Deploy workflow file (with workflow_dispatch, if any)'),
      ('deploy_ref', 'Deploy branch (empty = default)'),
    ], ok: 'Add');
    if (f == null || (f['repo'] ?? '').isEmpty) return;
    await _run('POST', '/api/devsahayak/repos', f);
  }

  Widget _repos() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GlassButton(label: 'Add repo', icon: Icons.add_rounded, onTap: _busy ? null : _addRepo),
        const SizedBox(height: 8),
        for (final r in _list(_d?['repos']))
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Icon(r['private'] == true ? Icons.lock_rounded : Icons.public_rounded, color: r['private'] == true ? C.ok : C.warn),
              const SizedBox(width: 8),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(r['repo']), style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text(
                      [
                        _s(r['default_branch']),
                        if (_s(r['language']).isNotEmpty) _s(r['language']),
                        r['private'] == true ? 'private' : 'PUBLIC (PR needs your approval)',
                        if (_s(r['deploy_workflow']).isNotEmpty) 'deploy: ${_s(r['deploy_workflow'])}',
                      ].join(' · '),
                      style: const TextStyle(fontSize: 12, color: C.muted)),
                ]),
              ),
              IconButton(
                  tooltip: 'Remove',
                  icon: const Icon(Icons.delete_outline_rounded),
                  onPressed: _busy ? null : () => _run('DELETE', '/api/devsahayak/repos/${_s(r['repo'])}')),
            ]),
          ),
      ]);

  Future<void> _token() async {
    final f = await _form(context, 'GitHub token (only here)', const [('token', 'Fine-grained token (github_pat_...)')],
        ok: 'Add', obscureFirst: true);
    if (f == null || (f['token'] ?? '').isEmpty) return;
    await _run('PUT', '/api/devsahayak/token', {'token': f['token']});
  }

  Widget _rules() {
    final st = _st;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(st['github'] == true ? 'GitHub: ${_s(st['token_label'])}' : 'GitHub not linked', style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text('Give the token only these permissions (for the chosen repos):', style: TextStyle(fontSize: 12.5, color: C.muted)),
          for (final p in (st['permissions'] as List?) ?? const []) Text('• $p', style: const TextStyle(fontSize: 12.5)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GradientButton(label: 'Add token', icon: Icons.key_rounded, height: 44, onTap: _busy ? null : _token)),
            const SizedBox(width: 8),
            if (st['github'] == true)
              Expanded(child: GlassButton(label: 'Remove', icon: Icons.link_off_rounded, onTap: _busy ? null : () => _run('DELETE', '/api/devsahayak/token'))),
          ]),
        ]),
      ),
      const SizedBox(height: 8),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Post the review directly (COMMENT only)'),
        subtitle: const Text('Off = every review goes with your tap. Approve is always with your tap.'),
        value: st['review_post'] == 'direct',
        onChanged: _busy ? null : (v) => _run('PUT', '/api/devsahayak/settings', {'review_post': v ? 'direct' : 'draft'}),
      ),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Ask first even for a PR in a private repo'),
        value: st['ask_before_pr'] == true,
        onChanged: _busy ? null : (v) => _run('PUT', '/api/devsahayak/settings', {'ask_before_pr': v}),
      ),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Open the PR as a draft'),
        value: st['draft_pr'] == true,
        onChanged: _busy ? null : (v) => _run('PUT', '/api/devsahayak/settings', {'draft_pr': v}),
      ),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Can change CI workflow files'),
        subtitle: const Text('Risk: a workflow runs with the repo\'s permissions (supply chain). The token also needs Workflows: write.'),
        value: st['allow_workflows'] == true,
        onChanged: _busy ? null : (v) => _run('PUT', '/api/devsahayak/settings', {'allow_workflows': v}),
      ),
      Wrap(spacing: 6, children: [
        for (final m in const ['squash', 'merge', 'rebase'])
          ChoiceChip(
              label: Text(m),
              selected: st['merge_method'] == m,
              onSelected: _busy ? null : (_) => _run('PUT', '/api/devsahayak/settings', {'merge_method': m})),
      ]),
      const SizedBox(height: 8),
      GlassButton(
          label: 'Limits and coding rules',
          icon: Icons.rule_rounded,
          onTap: _busy
              ? null
              : () async {
                  final f = await _form(context, 'Rules', const [
                    ('max_files', 'Max files in one PR'),
                    ('max_lines', 'Max lines in one PR'),
                    ('default_repo', 'Default repo'),
                    ('rules', 'Coding rules (style, stack, what not to do)'),
                  ], ok: 'Save', initial: {
                    'max_files': _s(st['max_files']),
                    'max_lines': _s(st['max_lines']),
                    'default_repo': _s(st['default_repo']),
                    'rules': _s(st['rules']),
                  });
                  if (f == null) return;
                  await _run('PUT', '/api/devsahayak/settings', {
                    if (f['max_files'] != null) 'max_files': int.tryParse(f['max_files']!) ?? 20,
                    if (f['max_lines'] != null) 'max_lines': int.tryParse(f['max_lines']!) ?? 1500,
                    'default_repo': f['default_repo'] ?? '',
                    'rules': f['rules'] ?? '',
                  });
                }),
      const SizedBox(height: 10),
      for (final n in (st['never'] as List?) ?? const []) Text('• $n', style: const TextStyle(fontSize: 12, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    // v0.869 R8 wave 2: the shared desk frame (lib/ui/desk/desk_kit.dart)
    return DeskScaffold(
      title: 'Hoola Code',
      tabs: const ['Sessions', 'Scheduled', 'Review', 'Merge / Deploy', 'Repos', 'Rules'],
      tab: _tab,
      onTab: (i) => setState(() => _tab = i),
      loading: _d == null,
      busy: _busy,
      onRefresh: _load,
      body: () => ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
        [_sessions(), _scheduled(), _review(), _actions(), _repos(), _rules()][_tab],
        const SizedBox(height: 14),
        const Text(
                  'Hoola works only on a hoola/* branch and opens a pull request; never directly on main. '
                  'Merge and deploy only with your tap. Never send the token in chat.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
}

/// One session, laid out like the web page: her ask, the steps (folded when the work is over), what Hoola said, the
/// changed files, the status, and the message box. Everything that changes GitHub is her tap on a button here.
class DevTaskPage extends StatefulWidget {
  const DevTaskPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<DevTaskPage> createState() => _DevTaskPageState();
}

class _DevTaskPageState extends State<DevTaskPage> {
  Map<String, dynamic>? _t;
  Map<String, dynamic>? _action; // the merge card that waits for her tap (made by "Merge…")
  bool _busy = false;
  bool _stepsOpen = false;
  bool _thinking = false;
  bool _askedActions = false;
  Timer? _poll;
  final TextEditingController _msg = TextEditingController();

  String get _base => '/api/devsahayak/tasks/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    _msg.dispose();
    super.dispose();
  }

  bool _live(Map<String, dynamic> t) => _running(t) || _s(t['status']) == 'ci_running' || _s(t['status']) == 'new';

  void _setPoll(Map<String, dynamic> t) {
    if (_live(t)) {
      _poll ??= Timer.periodic(const Duration(seconds: 3), (_) => _load(quiet: true));
    } else {
      _poll?.cancel();
      _poll = null;
    }
  }

  Future<void> _load({bool quiet = false}) async {
    try {
      final t = _m(await widget.app.api!.call('GET', _base));
      if (!mounted) return;
      setState(() => _t = t);
      _setPoll(t);
      if (!_askedActions && _int(t['pr_number']) != 0 && !_running(t)) {
        _askedActions = true;
        _findWaitingMerge(t);
      }
    } catch (e) {
      if (mounted && !quiet) _snack(context, '$e');
    }
  }

  /// A merge card she asked for earlier and has not answered yet is shown again when she comes back.
  Future<void> _findWaitingMerge(Map<String, dynamic> t) async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/devsahayak/actions'));
      for (final a in _list(r['actions'])) {
        if (_s(a['kind']) == 'merge' && _s(a['status']) == 'waiting' && _s(a['repo']) == _s(t['repo']) && _int(a['pr_number']) == _int(t['pr_number'])) {
          if (mounted) setState(() => _action = a);
          return;
        }
      }
    } catch (_) {
      // the list is a convenience; the Merge button still works
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    if (mounted) setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    await _load(quiet: true);
    if (mounted) setState(() => _busy = false);
    return r;
  }

  bool _canRevise(Map<String, dynamic> t) => _canReviseStatus.contains(_s(t['status'])) || t['can_continue'] == true;

  /// note | answer | plan | revise | off - the same rule as the web page
  String _mode(Map<String, dynamic> t) {
    if (_running(t)) return 'note';
    if (_s(t['question']).isNotEmpty) return 'answer';
    if (_s(t['status']) == 'plan_wait') return 'plan';
    if (_canRevise(t)) return 'revise';
    return 'off';
  }

  Future<void> _send([String? words]) async {
    final t = _t;
    if (t == null || _busy) return;
    final mode = _mode(t);
    final text = (words ?? _msg.text).trim();
    if (mode == 'off') return;
    if (text.isEmpty && mode != 'plan') return;
    Map<String, dynamic>? r;
    if (mode == 'note') {
      r = await _run('POST', '$_base/note', {'text': text});
    } else if (mode == 'answer') {
      r = await _run('POST', '$_base/answer', {'text': text});
    } else if (mode == 'plan') {
      r = await _run('POST', '$_base/bg/plan_ok', {'hash': _s(t['hash']), 'note': text});
    } else {
      r = await _run('POST', '$_base/bg/revise', {'text': text});
    }
    if (r != null && words == null && mounted) _msg.clear();
  }

  Future<void> _mergeAsk() async {
    final r = await _run('POST', '$_base/merge_request', const <String, dynamic>{});
    if (r != null && _s(r['id']).isNotEmpty && mounted) setState(() => _action = r);
  }

  // ---- steps ----------------------------------------------------------------------------------------------------
  Widget _line(IconData icon, String text, {Color color = C.chip, Color? iconColor}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(padding: const EdgeInsets.only(top: 2), child: Icon(icon, size: 15, color: iconColor ?? C.faint)),
          const SizedBox(width: 8),
          Expanded(child: Text(text, style: TextStyle(fontSize: 13, height: 1.35, color: color))),
        ]),
      );

  Widget? _step(Map<String, dynamic> s) {
    final k = _s(s['k']);
    if (k == 'say') {
      return Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Text(_s(s['text']), style: replyText(size: 15)));
    }
    if (k == 'note') {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(color: C.violet.withOpacity(.22), borderRadius: BorderRadius.circular(14)),
          child: Text(_s(s['text']), style: const TextStyle(fontSize: 13)),
        ),
      );
    }
    if (k == 'think') {
      if (!_thinking) return null;
      return Container(
        margin: const EdgeInsets.fromLTRB(22, 4, 0, 6),
        padding: const EdgeInsets.only(left: 10),
        decoration: const BoxDecoration(border: Border(left: BorderSide(color: C.line, width: 2))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Thinking', style: TextStyle(fontSize: 11.5, color: C.faint, fontWeight: FontWeight.w600)),
          Text(_s(s['text']), maxLines: 14, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, height: 1.4, color: C.muted)),
        ]),
      );
    }
    if (k == 'rules') return _line(Icons.list_rounded, "Read the repo's rules");
    if (k == 'read') return _line(Icons.description_outlined, 'Read ${_s(s['path'])}');
    if (k == 'search') return _line(Icons.search_rounded, 'Searched "${_s(s['q'])}" · ${_plural(_int(s['n']), 'file')}');
    if (k == 'list') return _line(Icons.folder_open_rounded, 'Looked in folder ${_s(s['path']).isEmpty ? '/' : _s(s['path'])}');
    if (k == 'usages') return _line(Icons.search_rounded, 'Found where ${_s(s['name'])} is used · ${_plural(_int(s['n']), 'place')}');
    if (k == 'edit') return _line(Icons.edit_outlined, 'Edited ${_s(s['path'])}  +${_int(s['added'])} −${_int(s['removed'])}', color: C.ink);
    if (k == 'new') return _line(Icons.add_rounded, 'Created ${_s(s['path'])}  +${_int(s['added'])}', color: C.ink);
    if (k == 'diff') return _line(Icons.description_outlined, 'Checked its own change · ${_plural(_int(s['n']), 'file')}');
    if (k == 'check') {
      final ok = s['ok'] == true;
      return _line(ok ? Icons.check_rounded : Icons.close_rounded, 'Ran your tests · ${ok ? 'passed' : 'failed'}',
          color: C.ink, iconColor: ok ? C.ok : C.bad);
    }
    if (k == 'check_off') return _line(Icons.close_rounded, 'Your tests could not run here - this change is not measured');
    if (k == 'grep') return _line(Icons.search_rounded, 'Searched the test log for "${_s(s['q'])}"');
    if (k == 'refused') return _line(Icons.block_rounded, 'A step was refused: ${_s(s['why'])}', color: C.muted);
    if (k == 'bash') {
      final ok = _int(s['rc']) == 0 && s['timed_out'] != true;
      final end = s['timed_out'] == true ? 'timed out' : 'exit ${_int(s['rc'])}';
      return _line(Icons.terminal_rounded, '\$ ${_s(s['cmd'])} · $end', color: C.ink, iconColor: ok ? C.ok : C.bad);
    }
    if (k == 'todo') {
      return Padding(
        padding: const EdgeInsets.fromLTRB(23, 4, 0, 4),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          for (final x in _list(s['items']))
            Text('${_s(x['status']) == 'completed' ? '✓' : (_s(x['status']) == 'in_progress' ? '●' : '○')}  ${_s(x['content'])}',
                style: TextStyle(fontSize: 12.5, height: 1.4, color: _s(x['status']) == 'completed' ? C.muted : C.ink)),
        ]),
      );
    }
    if (k == 'compact' || k == 'ws') return _line(Icons.list_rounded, _s(s['text']), color: C.muted);
    if (k == 'wait') return _line(Icons.hourglass_empty_rounded, _s(s['text']).isEmpty ? 'Waiting for a free coding slot' : _s(s['text']));
    if (k == 'ckpt') return _line(Icons.check_rounded, 'Checkpoint ${_int(s['n'])} saved', color: C.muted);
    if (k == 'rewind') return _line(Icons.undo_rounded, 'Went back to checkpoint ${_int(s['n'])}');
    if (k == 'pass') {
      const names = {'plan': 'Plan pass', 'review': "Hoola's own review", 'ci_fix': 'CI fix round', 'comments': "Reviewers' comments"};
      final name = names[_s(s['name'])] ?? _s(s['name']);
      final end = _s(s['state']) == 'end';
      final note = _s(s['note']);
      return _line(end ? (s['ok'] == false ? Icons.close_rounded : Icons.check_rounded) : Icons.more_horiz_rounded,
          '$name ${end ? 'ended' : 'started'}${note.isEmpty ? '' : ' · $note'}',
          color: C.muted);
    }
    if (k == 'stopped') return _line(Icons.stop_circle_outlined, 'Stopped. Nothing was pushed.', color: C.ink, iconColor: C.bad);
    return null; // a kind this app version does not know: skipped
  }

  List<Widget> _stepsBlock(Map<String, dynamic> t) {
    final steps = _list(t['steps']);
    if (steps.isEmpty) return const [];
    final rows = <Widget>[];
    for (final s in steps) {
      final w = _step(s);
      if (w != null) rows.add(w);
    }
    if (_running(t)) {
      // while it works: the newest steps, open
      final from = rows.length > 40 ? rows.length - 40 : 0;
      return rows.sublist(from);
    }
    var counted = 0;
    for (final s in steps) {
      final k = _s(s['k']);
      if (k != 'think' && k != 'pass') counted++;
    }
    final a = DateTime.tryParse(_s(t['at']));
    final b = DateTime.tryParse(_s(steps.last['at']));
    final secs = (a != null && b != null) ? b.difference(a).inSeconds : 0;
    return [
      InkWell(
        onTap: () => setState(() => _stepsOpen = !_stepsOpen),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Row(children: [
            Icon(_stepsOpen ? Icons.expand_more_rounded : Icons.chevron_right_rounded, size: 18, color: C.muted),
            const SizedBox(width: 6),
            Expanded(child: Text('Worked for ${_dur(secs)} · ${_plural(counted, 'step')}', style: const TextStyle(fontSize: 13, color: C.muted))),
          ]),
        ),
      ),
      if (_stepsOpen) ...rows,
    ];
  }

  // ---- the change -----------------------------------------------------------------------------------------------
  void _showDiff(Map<String, dynamic> t, String path) {
    var text = '';
    for (final f in _list(t['file_diffs'])) {
      if (_s(f['path']) == path) text = _s(f['diff']);
    }
    final all = text.split('\n');
    final lines = all.length > 800 ? all.sublist(0, 800) : all;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF17122F),
      builder: (c) => SafeArea(
        child: SizedBox(
          height: MediaQuery.of(c).size.height * .8,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 8, 8),
              child: Row(children: [
                Expanded(child: Text(path, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontFamily: 'monospace', fontSize: 13, fontWeight: FontWeight.w700))),
                IconButton(
                    tooltip: 'Copy',
                    icon: const Icon(Icons.copy_rounded, size: 18),
                    onPressed: () => Clipboard.setData(ClipboardData(text: text))),
                IconButton(tooltip: 'Close', icon: const Icon(Icons.close_rounded), onPressed: () => Navigator.pop(c)),
              ]),
            ),
            Expanded(
              child: text.trim().isEmpty
                  ? const Padding(padding: EdgeInsets.all(16), child: Text('The lines of this change are not ready yet.', style: TextStyle(color: C.muted)))
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(12, 0, 12, 20),
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          for (final l in lines)
                            Text(l.isEmpty ? ' ' : l,
                                softWrap: false,
                                style: TextStyle(
                                    fontFamily: 'monospace',
                                    fontSize: 11.5,
                                    height: 1.35,
                                    color: l.startsWith('+') ? C.ok : (l.startsWith('-') ? C.bad : (l.startsWith('@@') ? C.faint : C.chip)))),
                          if (all.length > lines.length) Text('… ${all.length - lines.length} more lines', style: const TextStyle(fontSize: 11.5, color: C.faint)),
                        ]),
                      ),
                    ),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _filesCard(Map<String, dynamic> t) {
    final files = _list(t['files']);
    return Glass(
      padding: const EdgeInsets.all(12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('Changes · ${_plural(files.length, 'file')}', style: const TextStyle(fontWeight: FontWeight.w700))),
          _statText(_stat(t), size: 12.5),
        ]),
        for (final f in files)
          InkWell(
            onTap: () => _showDiff(t, _s(f['path'])),
            child: Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(children: [
                Expanded(child: Text(_s(f['path']), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontFamily: 'monospace', fontSize: 12))),
                const SizedBox(width: 8),
                Text('+${_int(f['added'])}', style: const TextStyle(fontSize: 12, color: C.ok, fontFamily: 'monospace')),
                const SizedBox(width: 6),
                Text('−${_int(f['removed'])}', style: const TextStyle(fontSize: 12, color: C.bad, fontFamily: 'monospace')),
                const Icon(Icons.chevron_right_rounded, size: 16, color: C.faint),
              ]),
            ),
          ),
      ]),
    );
  }

  Widget _kv(String a, String b, {Color color = C.ink}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          Expanded(child: Text(a, style: const TextStyle(fontSize: 12.5, color: C.muted))),
          Text(b, style: TextStyle(fontSize: 12.5, color: color, fontWeight: FontWeight.w600)),
        ]),
      );

  Widget _statusCard(Map<String, dynamic> t) {
    final ci = _s(_m(t['ci'])['state']);
    final sr = _m(t['self_review']);
    final verdict = _s(sr['verdict']);
    final open = ((sr['problems'] as List?) ?? const []).length;
    final comments = _list(t['pr_comments']).length;
    return Glass(
      padding: const EdgeInsets.all(12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _kv('Repo', _repoShort(_s(t['repo']))),
        if (_s(t['branch']).isNotEmpty) _kv('Branch', _s(t['branch'])),
        if (_int(t['pr_number']) != 0) _kv('Pull request', '#${_int(t['pr_number'])} · ${_statusLabel(t)}'),
        if (_int(t['pr_number']) != 0 && ci.isNotEmpty) _kv('CI on GitHub', _ciLabel(ci), color: _ciColor(ci)),
        if (verdict.isNotEmpty) _kv("Hoola's own review", verdict == 'ok' ? 'Clean' : '${_plural(open, 'point')} open', color: verdict == 'ok' ? C.ok : C.warn),
        if (comments > 0) _kv("Reviewers' comments", '$comments new', color: C.warn),
      ]),
    );
  }

  Widget _planCard(Map<String, dynamic> t) {
    final plan = _m(t['plan']);
    final files = (plan['files'] as List?) ?? const [];
    final steps = (plan['steps'] as List?) ?? const [];
    final done = (plan['done_when'] as List?) ?? const [];
    String item(dynamic x) => x is Map ? '${_s(x['path'])}${_s(x['why']).isEmpty ? '' : ' - ${_s(x['why'])}'}' : _s(x);
    return Glass(
      border: C.accent,
      padding: const EdgeInsets.all(12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('The plan', style: display(15)),
        if (_s(plan['goal']).isNotEmpty) ...[const SizedBox(height: 4), Text(_s(plan['goal']), style: const TextStyle(fontSize: 13, height: 1.35, fontWeight: FontWeight.w600))],
        if (files.isNotEmpty) ...[
          const SizedBox(height: 6),
          const Text('Files it will change', style: TextStyle(fontSize: 12, color: C.muted)),
          for (final f in files.take(12)) Text('• ${item(f)}', style: const TextStyle(fontSize: 12, height: 1.3)),
        ],
        if (steps.isNotEmpty) ...[
          const SizedBox(height: 6),
          const Text('Steps', style: TextStyle(fontSize: 12, color: C.muted)),
          for (var i = 0; i < steps.length && i < 12; i++) Text('${i + 1}. ${item(steps[i])}', style: const TextStyle(fontSize: 12, height: 1.3)),
        ],
        if (done.isNotEmpty) ...[
          const SizedBox(height: 6),
          const Text('Done when', style: TextStyle(fontSize: 12, color: C.muted)),
          for (final d in done.take(8)) Text('✓ ${item(d)}', style: const TextStyle(fontSize: 12, height: 1.3)),
        ],
        if (_s(plan['risk']).isNotEmpty) ...[const SizedBox(height: 6), Text('Risk: ${_s(plan['risk'])}', style: const TextStyle(fontSize: 12, color: C.muted))],
        const SizedBox(height: 8),
        const Text('Nothing is touched until you say yes.', style: TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(
              child: GradientButton(
                  label: 'Yes, start',
                  icon: Icons.play_arrow_rounded,
                  height: 44,
                  onTap: _busy ? null : () => _run('POST', '$_base/bg/plan_ok', {'hash': _s(t['hash'])}))),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Cancel job', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _run('POST', '$_base/cancel'))),
        ]),
      ]),
    );
  }

  Widget _questionCard(Map<String, dynamic> t) {
    final choices = (_m(t['ws'])['choices'] as List?) ?? const [];
    return Glass(
      border: C.accent,
      padding: const EdgeInsets.all(12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Hoola asks before it changes anything:', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
        const SizedBox(height: 4),
        Text(_s(t['question']), style: const TextStyle(fontSize: 13.5, height: 1.35)),
        if (choices.isNotEmpty) ...[
          const SizedBox(height: 8),
          for (final c in choices.take(4))
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: _busy ? null : () => _send(_s(c)),
                  child: Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Text(_s(c), textAlign: TextAlign.center)),
                ),
              ),
            ),
        ],
        const SizedBox(height: 6),
        const Text('Or type your own answer below.', style: TextStyle(fontSize: 12, color: C.muted)),
      ]),
    );
  }

  List<Widget> _actions(Map<String, dynamic> t) {
    if (_running(t)) return const [];
    final st = _s(t['status']);
    final comments = _list(t['pr_comments']).length;
    return [
      if (st == 'ready' && _s(t['hash']).isNotEmpty)
        GradientButton(
            label: 'Open the pull request',
            icon: Icons.check_rounded,
            height: 44,
            onTap: _busy ? null : () => _run('POST', '$_base/push', {'hash': _s(t['hash'])})),
      if (st == 'checks_failed')
        GlassButton(label: 'Fix the CI failure', icon: Icons.build_rounded, height: 44, onTap: _busy ? null : () => _run('POST', '$_base/bg/fix_ci')),
      if (comments > 0 && (st == 'pr_open' || st == 'checks_failed'))
        GlassButton(
            label: 'Fix ${_plural(comments, 'reviewer comment')}',
            icon: Icons.rate_review_rounded,
            height: 44,
            onTap: _busy ? null : () => _run('POST', '$_base/bg/fix_comments')),
      if ((st == 'pr_open' || st == 'checks_failed') && _int(t['pr_number']) != 0 && _action == null)
        GlassButton(label: 'Merge…', icon: Icons.merge_rounded, height: 44, onTap: _busy ? null : _mergeAsk),
      if (st == 'pr_open' || st == 'checks_failed' || st == 'ci_running')
        GlassButton(label: 'Check CI again', icon: Icons.sync_rounded, height: 44, onTap: _busy ? null : () => _run('POST', '$_base/refresh')),
      if (_s(t['pr_url']).isNotEmpty) GlassButton(label: 'On GitHub', icon: Icons.open_in_new_rounded, height: 44, onTap: () => _open(_s(t['pr_url']))),
    ];
  }

  // ---- the message box ------------------------------------------------------------------------------------------
  Widget _composer(Map<String, dynamic> t) {
    final mode = _mode(t);
    if (mode == 'off') {
      return const Padding(
        padding: EdgeInsets.fromLTRB(16, 8, 16, 14),
        child: Text('This session is finished. Start a new one from the Hoola Code screen.', style: TextStyle(fontSize: 12.5, color: C.muted)),
      );
    }
    const hints = {
      'note': 'Message Hoola - it reads it before its next step',
      'answer': 'Type your answer - Hoola continues this session',
      'plan': 'Add a note for Hoola - it starts on the plan with your note',
      'revise': 'Ask for a change - Hoola adds a commit to the same pull request',
    };
    final hint = mode == 'revise' ? _s(t['hint']) : '';
    final stopping = t['stopping'] == true;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 6, 12, 10),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (hint.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: ActionChip(
              label: Text(hint, maxLines: 1, overflow: TextOverflow.ellipsis),
              avatar: const Icon(Icons.lightbulb_outline_rounded, size: 16),
              onPressed: () => setState(() {
                _msg.text = hint;
                _msg.selection = TextSelection.collapsed(offset: hint.length);
              }),
            ),
          ),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Expanded(
            child: TextField(
              controller: _msg,
              minLines: 1,
              maxLines: 5,
              maxLength: 4000,
              textInputAction: TextInputAction.newline,
              decoration: InputDecoration(hintText: hints[mode] ?? '', counterText: ''),
            ),
          ),
          const SizedBox(width: 6),
          IconButton(tooltip: 'Send', icon: const Icon(Icons.arrow_upward_rounded, color: C.accent), onPressed: _busy ? null : () => _send()),
          if (_running(t))
            IconButton(
                tooltip: stopping ? 'Stopping after this step' : 'Stop',
                icon: const Icon(Icons.stop_circle_outlined, color: C.bad),
                onPressed: (_busy || stopping) ? null : () => _run('POST', '$_base/stop')),
        ]),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = _t;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text(t == null ? 'Hoola Code' : _titleOf(t), maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
              tooltip: _thinking ? 'Hide what Hoola thought' : 'Show what Hoola thought',
              icon: Icon(Icons.psychology_rounded, color: _thinking ? C.accent : C.muted),
              onPressed: () => setState(() => _thinking = !_thinking)),
        ],
      ),
      body: Aurora(
        child: t == null
            ? const Center(child: CircularProgressIndicator())
            : SafeArea(
                top: false,
                child: Column(children: [
                  if (_busy) const LinearProgressIndicator(),
                  Expanded(
                    child: RefreshIndicator(
                      onRefresh: _load,
                      child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 16), children: _body(t)),
                    ),
                  ),
                  _composer(t),
                ]),
              ),
      ),
    );
  }

  List<Widget> _body(Map<String, dynamic> t) {
    final st = _s(t['status']);
    final running = _running(t);
    final acts = _actions(t);
    final notes = running ? (((t['notes'] as List?) ?? const []).map((e) => _s(e)).where((e) => e.isNotEmpty).toList()) : const <String>[];
    return [
      Row(children: [
        Pill(running ? (t['stopping'] == true ? 'Stopping after this step' : 'Working') : _statusLabel(t)),
        const SizedBox(width: 8),
        Expanded(child: Text(_s(t['number']), style: const TextStyle(fontSize: 12, color: C.faint))),
      ]),
      const SizedBox(height: 8),
      // her ask
      Align(
        alignment: Alignment.centerRight,
        child: Container(
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * .86),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(color: C.violet.withOpacity(.25), borderRadius: BorderRadius.circular(18)),
          child: Text(_s(t['text']), maxLines: 14, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14, height: 1.35)),
        ),
      ),
      const SizedBox(height: 6),
      ..._stepsBlock(t),
      if (running && t['stopping'] != true)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: Row(children: [
            SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
            SizedBox(width: 10),
            Text('Working…', style: TextStyle(fontSize: 13, color: C.muted)),
          ]),
        ),
      for (final n in notes)
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text('Queued: $n', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        ),
      if (st == 'plan_wait' && _m(t['plan']).isNotEmpty) ...[const SizedBox(height: 8), _planCard(t)],
      if (!running && st != 'plan_wait') ...[
        if (_s(t['error']).isNotEmpty && (st == 'failed' || st == 'refused')) ...[
          const SizedBox(height: 8),
          Glass(
            border: C.bad,
            padding: const EdgeInsets.all(12),
            child: Text('${st == 'refused' ? 'A safety rule stopped this change.' : 'It could not finish.'} ${_s(t['error'])}',
                style: const TextStyle(fontSize: 13, height: 1.35)),
          ),
        ],
        if (_s(t['question']).isNotEmpty) ...[const SizedBox(height: 8), _questionCard(t)]
        else if (_s(t['explain']).isNotEmpty)
          Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Text(_s(t['explain']), style: replyText(size: 15.5))),
        if (_s(t['risk']).isNotEmpty) Text('Risk: ${_s(t['risk'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
      ],
      if (_list(t['files']).isNotEmpty) ...[const SizedBox(height: 10), _filesCard(t)],
      const SizedBox(height: 10),
      _statusCard(t),
      if (acts.isNotEmpty) ...[
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: acts),
      ],
      if (_action != null) ...[
        const SizedBox(height: 10),
        DevActionCard(key: ValueKey('da${_s(_action!['id'])}'), app: widget.app, data: {'action': _action!}, onDone: () => _load(quiet: true)),
      ],
    ];
  }
}

/// `devsahayak_task`, `devsahayak_push` and `devsahayak_plan`: one card per task (key data['task']['id']), updated in place.
/// A 'ready' task (public repo / ask_before_pr) shows "Haan, PR kholo": only this tap opens the PR.
/// v0.451 ECC PHASE 4: a 'plan_wait' task shows the plan (what will change, in what order, how we know it is done) and
/// "Haan, shuru karo" - no file is touched until that tap.
class DevTaskCard extends StatefulWidget {
  const DevTaskCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<DevTaskCard> createState() => _DevTaskCardState();
}

class _DevTaskCardState extends State<DevTaskCard> {
  bool _busy = false;
  Map<String, dynamic>? _after;

  Map<String, dynamic> get _t => _after ?? _m(widget.data['task']);

  Future<void> _planOk() async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/devsahayak/tasks/${_s(_t['id'])}/bg/plan_ok', {'hash': _s(_t['hash'])});
    if (mounted) setState(() {
      _busy = false;
      if (r != null && _s(r['id']).isNotEmpty) _after = r;
    });
    widget.onDone?.call();
  }

  Future<void> _push() async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/devsahayak/tasks/${_s(_t['id'])}/push', {'hash': _s(_t['hash'])});
    if (mounted) setState(() {
      _busy = false;
      if (r != null && _s(r['id']).isNotEmpty) _after = r;
    });
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final t = _t;
    final ci = _m(t['ci']);
    final ready = t['status'] == 'ready' && _s(t['hash']).isNotEmpty;
    final plan = _m(t['plan']);
    final planWait = t['status'] == 'plan_wait' && _s(t['hash']).isNotEmpty;
    final say = _s(widget.data['say']);
    return Glass(
      border: (ready || planWait) ? C.accent : (t['status'] == 'refused' || t['status'] == 'checks_failed' ? C.bad : null),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.terminal_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(t['number'])} · ${_s(t['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(t['status_label'])),
        ]),
        const SizedBox(height: 4),
        Text([_s(t['repo']), if (_s(t['branch']).isNotEmpty) _s(t['branch']), if ((t['pr_number'] ?? 0) != 0) 'PR #${t['pr_number']}'].join(' · '),
            style: const TextStyle(fontSize: 12, color: C.muted)),
        if (say.isNotEmpty && _after == null) ...[const SizedBox(height: 6), Text(say, style: const TextStyle(fontSize: 13, height: 1.3))],
        if (_s(t['explain']).isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(_s(t['explain']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
        ],
        if (plan.isNotEmpty) ...[
          if (_s(plan['goal']).isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(_s(plan['goal']), style: const TextStyle(fontSize: 13, height: 1.35, fontWeight: FontWeight.w600)),
          ],
          for (final f in _list(plan['files']).take(12))
            Text('• ${_s(f['path'])}${f['new'] == true ? ' (new)' : ''} — ${_s(f['why'])}',
                style: const TextStyle(fontSize: 12, height: 1.3)),
          if (_list(plan['steps']).isNotEmpty) ...[
            const SizedBox(height: 4),
            const Text('Step', style: TextStyle(fontSize: 12, color: C.muted)),
            for (var i = 0; i < _list(plan['steps']).length && i < 12; i++)
              Text('${i + 1}. ${_s(_list(plan['steps'])[i])}', style: const TextStyle(fontSize: 12, height: 1.3)),
          ],
          if (_list(plan['done_when']).isNotEmpty) ...[
            const SizedBox(height: 4),
            const Text('When the task counts as done', style: TextStyle(fontSize: 12, color: C.muted)),
            for (final d in _list(plan['done_when']).take(8))
              Text('✓ ${_s(d)}', style: const TextStyle(fontSize: 12, height: 1.3)),
          ],
          for (final q in _list(plan['questions']).take(3))
            Text('? ${_s(q)}', style: const TextStyle(fontSize: 12.5, height: 1.3, color: C.warn)),
        ],
        for (final f in _list(t['files']))
          Text('• ${_s(f['path'])}  +${f['added'] ?? 0} −${f['removed'] ?? 0}${f['new'] == true ? ' (new)' : ''}',
              style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
        for (final c in _list(t['checks']).take(6))
          Text('⚠ ${_s(c['owasp'])} ${_s(c['path'])}: ${_s(c['say'])}', style: const TextStyle(fontSize: 11.5, color: C.warn)),
        if (_s(t['error']).isNotEmpty && t['status'] == 'refused')
          Text(_s(t['error']), style: const TextStyle(fontSize: 12, color: C.bad)),
        if ((t['pr_number'] ?? 0) != 0 && _s(ci['say']).isNotEmpty)
          Text(_s(ci['say']), style: TextStyle(fontSize: 12.5, color: _ciColor(_s(ci['state'])))),
        if (_s(t['risk']).isNotEmpty) Text('Risk: ${_s(t['risk'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        if (planWait)
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes, start', icon: Icons.play_arrow_rounded, height: 44, onTap: _busy ? null : _planOk)),
            const SizedBox(width: 8),
            Expanded(
                child: GlassButton(
                    label: 'Declined',
                    icon: Icons.close_rounded,
                    height: 44,
                    onTap: _busy
                        ? null
                        : () async {
                            await _call(context, widget.app, 'POST', '/api/devsahayak/tasks/${_s(t['id'])}/cancel');
                            widget.onDone?.call();
                          })),
          ])
        else if (ready)
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes, open the PR', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : _push)),
            const SizedBox(width: 8),
            Expanded(
                child: GlassButton(
                    label: 'Declined',
                    icon: Icons.close_rounded,
                    height: 44,
                    onTap: _busy
                        ? null
                        : () async {
                            await _call(context, widget.app, 'POST', '/api/devsahayak/tasks/${_s(t['id'])}/cancel');
                            widget.onDone?.call();
                          })),
          ])
        else if (_s(t['pr_url']).isNotEmpty)
          Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(onPressed: () => _open(_s(t['pr_url'])), icon: const Icon(Icons.open_in_new_rounded, size: 16), label: const Text('See PR'))),
      ]),
    );
  }
}

/// `devsahayak_review`: Hoola's draft review. Only her tap posts it (her chosen event; APPROVE only ever here).
class DevReviewCard extends StatefulWidget {
  const DevReviewCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<DevReviewCard> createState() => _DevReviewCardState();
}

class _DevReviewCardState extends State<DevReviewCard> {
  bool _busy = false;
  late String _status = _s(_m(widget.data['review'])['status']);
  late String _event = _s(_m(widget.data['review'])['suggest']).isEmpty ? 'COMMENT' : _s(_m(widget.data['review'])['suggest']);

  Future<void> _post() async {
    final r = _m(widget.data['review']);
    setState(() => _busy = true);
    final out = await _call(context, widget.app, 'POST', '/api/devsahayak/reviews/${_s(r['id'])}/post', {'hash': _s(r['hash']), 'event': _event});
    if (mounted) setState(() {
      _busy = false;
      if (out != null) _status = _s(out['status']);
    });
    widget.onDone?.call();
  }

  Future<void> _discard() async {
    final r = _m(widget.data['review']);
    setState(() => _busy = true);
    final out = await _call(context, widget.app, 'POST', '/api/devsahayak/reviews/${_s(r['id'])}/discard');
    if (mounted) setState(() {
      _busy = false;
      if (out != null) _status = 'discarded';
    });
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final r = _m(widget.data['review']);
    final draft = _status == 'draft' && _s(r['hash']).isNotEmpty;
    return Glass(
      border: draft ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.rate_review_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Review · PR #${r['pr_number']} ${_s(r['pr_title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_status),
        ]),
        Text('${_s(r['repo'])} · ${_s(r['author'])} · ${_s(r['head_sha'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 6),
        Text(_s(r['summary']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
        for (final c in _list(r['comments']).take(10))
          Text('• ${_s(c['path'])}${(c['line'] ?? 0) != 0 ? ':${c['line']}' : ''} [${_s(c['severity'])}] ${_s(c['body'])}',
              style: TextStyle(fontSize: 12, color: c['severity'] == 'high' ? C.bad : C.chip)),
        const SizedBox(height: 8),
        if (draft) ...[
          Wrap(spacing: 6, children: [
            for (final (e, l) in const [('COMMENT', 'Comment'), ('REQUEST_CHANGES', 'Request a change'), ('APPROVE', 'Approve')])
              ChoiceChip(label: Text(l), selected: _event == e, onSelected: (_) => setState(() => _event = e)),
          ]),
          const SizedBox(height: 6),
          Row(children: [
            Expanded(child: GradientButton(label: 'Post on GitHub', icon: Icons.send_rounded, height: 44, onTap: _busy ? null : _post)),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Cancel', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : _discard)),
          ]),
        ] else if (_s(r['url']).isNotEmpty)
          TextButton.icon(onPressed: () => _open(_s(r['url'])), icon: const Icon(Icons.open_in_new_rounded, size: 16), label: const Text('See on GitHub')),
      ]),
    );
  }
}

/// `devsahayak_merge` and `devsahayak_deploy`: waits for HER tap. CI failed / running -> she must write a reason to go ahead.
class DevActionCard extends StatefulWidget {
  const DevActionCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<DevActionCard> createState() => _DevActionCardState();
}

class _DevActionCardState extends State<DevActionCard> {
  bool _busy = false;
  Map<String, dynamic>? _after;

  Map<String, dynamic> get _a => _after ?? _m(widget.data['action']);

  Future<void> _decide(bool yes) async {
    final a = _a;
    String reason = '';
    if (yes && a['needs_force'] == true) {
      final f = await _form(context, 'CI ${_ciLabel(_s(a['ci_state']))}: why continue anyway?', const [('reason', 'Reason (required)')], ok: 'Do it anyway');
      if (f == null || (f['reason'] ?? '').length < 8) {
        if (mounted) _snack(context, 'A reason of at least 8 characters is needed.');
        return;
      }
      reason = f['reason']!;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/devsahayak/actions/${_s(a['id'])}/decide',
        {'yes': yes, 'hash': _s(a['hash']), if (reason.isNotEmpty) 'force_reason': reason});
    if (mounted) setState(() {
      _busy = false;
      if (r != null && _s(r['id']).isNotEmpty) _after = r;
    });
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final a = _a;
    final merge = a['kind'] == 'merge';
    final waiting = a['status'] == 'waiting' && _s(a['hash']).isNotEmpty;
    final res = _m(a['result']);
    return Glass(
      border: waiting ? (a['needs_force'] == true ? C.bad : C.accent) : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(merge ? Icons.merge_rounded : Icons.rocket_launch_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text(merge ? 'Merge · PR #${a['pr_number']} ${_s(a['pr_title'])}' : 'Deploy · ${_s(a['repo'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(a['status'])),
        ]),
        Text(
            merge
                ? '${_s(a['repo'])} · ${_s(a['method'])} into ${_s(a['base'])} · commit ${_s(a['head_sha'])}'
                : '${_s(a['workflow'])} · ${_s(a['ref'])} · commit ${_s(a['head_sha'])}',
            style: const TextStyle(fontSize: 12, color: C.muted)),
        Text(_s(_m(a['ci'])['say']).isEmpty ? _ciLabel(_s(a['ci_state'])) : _s(_m(a['ci'])['say']),
            style: TextStyle(fontSize: 12.5, color: _ciColor(_s(a['ci_state'])))),
        for (final n in (a['notes'] as List?) ?? const []) Text('• $n', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_m(a['inputs']).isNotEmpty) Text('Inputs: ${_m(a['inputs']).entries.map((e) => '${e.key}=${e.value}').join(', ')}', style: const TextStyle(fontSize: 12)),
        if (_s(a['force_reason']).isNotEmpty) Text('Reason for going ahead: ${_s(a['force_reason'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(res['error']).isNotEmpty) Text(_s(res['error']), style: const TextStyle(fontSize: 12, color: C.bad)),
        if (_s(res['conclusion']).isNotEmpty) Text('Result: ${_s(res['conclusion'])}', style: TextStyle(fontSize: 12.5, color: res['conclusion'] == 'success' ? C.ok : C.bad)),
        const SizedBox(height: 8),
        if (waiting)
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: a['needs_force'] == true ? '${merge ? 'Merge' : 'Deploy'} anyway' : (merge ? 'Yes, merge' : 'Yes, deploy'),
                    icon: Icons.check_rounded,
                    height: 44,
                    onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Declined', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
          ])
        else if (_s(res['url']).isNotEmpty)
          TextButton.icon(onPressed: () => _open(_s(res['url'])), icon: const Icon(Icons.open_in_new_rounded, size: 16), label: const Text('See run')),
      ]),
    );
  }
}
