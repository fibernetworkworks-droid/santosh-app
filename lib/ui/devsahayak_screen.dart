/// Profile > Developer Sahayak: Hoola as a software developer in HER GitHub repos.
/// Kaam (write / fix / tests / docs / explain -> hoola/* branch + pull request, CI result) · Review (her team's PRs, draft reviews
/// she posts) · Merge / Deploy (cards waiting for her tap) · Repos · Niyam (token typed only here, limits, review mode).
/// Merge, deploy, posting a review and a PR on a public repo happen ONLY from her tap on these cards.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
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
String _ciLabel(String s) => switch (s) { 'success' => 'CI pass', 'failure' => 'CI fail', 'pending' => 'CI chal raha', _ => 'CI nahi' };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', bool obscureFirst = false, Map<String, String> initial = const {}}) async {
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
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
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

  @override
  void initState() {
    super.initState();
    _load();
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
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  Map<String, dynamic> get _st => _m(_d?['settings']);

  void _openTask(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => DevTaskPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _newTask(String kind) async {
    final label = _s(_m(_d?['kinds'])[kind]);
    final f = await _form(context, label.isEmpty ? 'Naya kaam' : label, [
      ('text', kind == 'fix' || kind == 'explain' ? 'Kya dikkat hai + error / log yahan chipkaiye' : 'Kya chahiye (apne shabdon mein)'),
      ('repo', 'Repo (owner/naam; khaali = ${_s(_st['default_repo']).isEmpty ? 'pehla' : _s(_st['default_repo'])})'),
      if (kind == 'fix' || kind == 'explain') ('issue', 'GitHub issue number (ho to)'),
      ('files', 'Files (comma se, ho to)'),
    ], ok: 'Shuru karo');
    if (f == null || ((f['text'] ?? '').isEmpty && (f['issue'] ?? '').isEmpty)) return;
    final r = await _run('POST', '/api/devsahayak/tasks', {
      'kind': kind,
      'text': f['text'] ?? '',
      if ((f['repo'] ?? '').isNotEmpty) 'repo': f['repo'],
      if ((f['issue'] ?? '').isNotEmpty) 'issue': int.tryParse(f['issue']!) ?? 0,
      if ((f['files'] ?? '').isNotEmpty) 'files': f['files']!.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
    });
    if (r != null && _s(r['id']).isNotEmpty && mounted) _openTask(_s(r['id']));
  }

  Widget _taskTile(Map<String, dynamic> t) {
    final ci = _m(t['ci']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _openTask(_s(t['id'])),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: t['status'] == 'ready' ? C.accent : (t['status'] == 'checks_failed' ? C.bad : null),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Pill(_s(t['kind_label'])),
              const SizedBox(width: 6),
              Expanded(child: Text('${_s(t['number'])} · ${_s(t['title'])}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(t['status_label'])),
            ]),
            const SizedBox(height: 4),
            Text([_s(t['repo']), if ((t['pr_number'] ?? 0) != 0) 'PR #${t['pr_number']}', '${_list(t['files']).length} file'].join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12)),
            if (_s(ci['state']).isNotEmpty && (t['pr_number'] ?? 0) != 0)
              Text(_ciLabel(_s(ci['state'])), style: TextStyle(fontSize: 12, color: _ciColor(_s(ci['state'])))),
          ]),
        ),
      ),
    );
  }

  Widget _work() {
    final tasks = _list(_d?['tasks']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (_st['github'] != true)
        Glass(
          border: C.warn,
          child: const Text('Pehle Niyam mein apna GitHub fine-grained token daaliye (sirf chune hue repos ke liye).',
              style: TextStyle(fontSize: 13)),
        ),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Bug fix', icon: Icons.bug_report_rounded, onTap: _busy ? null : () => _newTask('fix')),
        GlassButton(label: 'Naya code', icon: Icons.code_rounded, onTap: _busy ? null : () => _newTask('write')),
        GlassButton(label: 'Tests', icon: Icons.science_rounded, onTap: _busy ? null : () => _newTask('tests')),
        GlassButton(label: 'Docs', icon: Icons.menu_book_rounded, onTap: _busy ? null : () => _newTask('docs')),
        GlassButton(label: 'Sirf samjhao', icon: Icons.lightbulb_rounded, onTap: _busy ? null : () => _newTask('explain')),
      ]),
      const SizedBox(height: 10),
      if (tasks.isEmpty) const Text('Abhi koi kaam nahi.', style: TextStyle(color: C.muted)),
      for (final t in tasks) _taskTile(t),
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
        Expanded(child: GlassButton(label: 'Khule PR dekho', icon: Icons.call_split_rounded, onTap: _busy ? null : () => _loadPrs(''))),
      ]),
      const SizedBox(height: 8),
      for (final p in _prs)
        ListTile(
          contentPadding: EdgeInsets.zero,
          dense: true,
          title: Text('#${p['number']} ${_s(p['title'])}'),
          subtitle: Text('${_s(p['author'])}${p['by_hoola'] == true ? ' · Hoola ka' : ''}${p['draft'] == true ? ' · draft' : ''}'),
          trailing: Wrap(spacing: 4, children: [
            IconButton(
                tooltip: 'Review karo',
                icon: const Icon(Icons.rate_review_rounded),
                onPressed: _busy ? null : () => _run('POST', '/api/devsahayak/reviews', {'pr': p['number']})),
            IconButton(
                tooltip: 'Merge card',
                icon: const Icon(Icons.merge_rounded),
                onPressed: _busy ? null : () => _run('POST', '/api/devsahayak/merge_request', {'pr': p['number']})),
          ]),
        ),
      const SizedBox(height: 8),
      for (final r in reviews)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: DevReviewCard(app: widget.app, data: {'review': r}, onDone: _load)),
      if (reviews.isEmpty) const Text('Abhi koi review nahi.', style: TextStyle(color: C.muted)),
    ]);
  }

  Widget _actions() {
    final acts = _list(_d?['actions']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      GlassButton(label: 'Deploy card mangao', icon: Icons.rocket_launch_rounded, onTap: _busy ? null : _deploy),
      const SizedBox(height: 10),
      if (acts.isEmpty) const Text('Koi merge / deploy card nahi.', style: TextStyle(color: C.muted)),
      for (final a in acts)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: DevActionCard(app: widget.app, data: {'action': a}, onDone: _load)),
    ]);
  }

  Future<void> _deploy() async {
    final f = await _form(context, 'Deploy (aapke repo ka apna workflow)', const [
      ('repo', 'Repo (khaali = default)'),
      ('workflow', 'Workflow file (khaali = repo mein set wala)'),
      ('ref', 'Branch (khaali = default)'),
      ('env', "Input 'env' (ho to)"),
    ], ok: 'Card banao');
    if (f == null) return;
    await _run('POST', '/api/devsahayak/deploy_request', {
      for (final k in ['repo', 'workflow', 'ref']) if ((f[k] ?? '').isNotEmpty) k: f[k],
      if ((f['env'] ?? '').isNotEmpty) 'inputs': {'env': f['env']},
    });
  }

  Future<void> _addRepo() async {
    final f = await _form(context, 'Repo jodo', const [
      ('repo', 'owner/naam'),
      ('deploy_workflow', 'Deploy workflow file (workflow_dispatch wala, ho to)'),
      ('deploy_ref', 'Deploy branch (khaali = default)'),
    ], ok: 'Jodo');
    if (f == null || (f['repo'] ?? '').isEmpty) return;
    await _run('POST', '/api/devsahayak/repos', f);
  }

  Widget _repos() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GlassButton(label: 'Repo jodo', icon: Icons.add_rounded, onTap: _busy ? null : _addRepo),
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
                        r['private'] == true ? 'private' : 'PUBLIC (PR aapki haan se)',
                        if (_s(r['deploy_workflow']).isNotEmpty) 'deploy: ${_s(r['deploy_workflow'])}',
                      ].join(' · '),
                      style: const TextStyle(fontSize: 12, color: C.muted)),
                ]),
              ),
              IconButton(
                  tooltip: 'Hatao',
                  icon: const Icon(Icons.delete_outline_rounded),
                  onPressed: _busy ? null : () => _run('DELETE', '/api/devsahayak/repos/${_s(r['repo'])}')),
            ]),
          ),
      ]);

  Future<void> _token() async {
    final f = await _form(context, 'GitHub token (sirf yahan)', const [('token', 'Fine-grained token (github_pat_...)')],
        ok: 'Jodo', obscureFirst: true);
    if (f == null || (f['token'] ?? '').isEmpty) return;
    await _run('PUT', '/api/devsahayak/token', {'token': f['token']});
  }

  Widget _rules() {
    final st = _st;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(st['github'] == true ? 'GitHub: ${_s(st['token_label'])}' : 'GitHub juda nahi', style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text('Token mein sirf yeh ijazat dijiye (chune hue repos):', style: TextStyle(fontSize: 12.5, color: C.muted)),
          for (final p in (st['permissions'] as List?) ?? const []) Text('• $p', style: const TextStyle(fontSize: 12.5)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GradientButton(label: 'Token daalo', icon: Icons.key_rounded, height: 44, onTap: _busy ? null : _token)),
            const SizedBox(width: 8),
            if (st['github'] == true)
              Expanded(child: GlassButton(label: 'Hatao', icon: Icons.link_off_rounded, onTap: _busy ? null : () => _run('DELETE', '/api/devsahayak/token'))),
          ]),
        ]),
      ),
      const SizedBox(height: 8),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Review seedha post karo (sirf COMMENT)'),
        subtitle: const Text('Band = har review aapke tap se jata hai. Approve hamesha aapke tap se.'),
        value: st['review_post'] == 'direct',
        onChanged: _busy ? null : (v) => _run('PUT', '/api/devsahayak/settings', {'review_post': v ? 'direct' : 'draft'}),
      ),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Private repo mein bhi PR se pehle poochho'),
        value: st['ask_before_pr'] == true,
        onChanged: _busy ? null : (v) => _run('PUT', '/api/devsahayak/settings', {'ask_before_pr': v}),
      ),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('PR draft ke roop mein kholo'),
        value: st['draft_pr'] == true,
        onChanged: _busy ? null : (v) => _run('PUT', '/api/devsahayak/settings', {'draft_pr': v}),
      ),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('CI workflow files badal sakta hai'),
        subtitle: const Text('Khatra: workflow repo ki ijazat se chalta hai (supply chain). Token ko Workflows: write bhi chahiye.'),
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
          label: 'Seemayein aur coding niyam',
          icon: Icons.rule_rounded,
          onTap: _busy
              ? null
              : () async {
                  final f = await _form(context, 'Niyam', const [
                    ('max_files', 'Ek PR mein max files'),
                    ('max_lines', 'Ek PR mein max lines'),
                    ('default_repo', 'Default repo'),
                    ('rules', 'Coding niyam (style, stack, kya na karein)'),
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
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Developer Sahayak')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Kaam'), (1, 'Review'), (2, 'Merge / Deploy'), (3, 'Repos'), (4, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_work(), _review(), _actions(), _repos(), _rules()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Hoola sirf hoola/* branch par kaam karke pull request kholta hai; main par seedha kabhi nahi. Tests aapke GitHub CI mein chalte hain. '
                  'Merge aur deploy sirf aapke tap se. Token kabhi chat mein mat bhejiye.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

/// One task: explanation, files + diff, checks, CI, revise, fix CI, merge card.
class DevTaskPage extends StatefulWidget {
  const DevTaskPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<DevTaskPage> createState() => _DevTaskPageState();
}

class _DevTaskPageState extends State<DevTaskPage> {
  Map<String, dynamic>? _t;
  bool _busy = false;
  bool _diff = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final t = _m(await widget.app.api!.call('GET', '/api/devsahayak/tasks/${widget.id}'));
      if (mounted) setState(() => _t = t);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final t = _t;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(t == null ? 'Kaam' : '${_s(t['number'])} · ${_s(t['kind_label'])}')),
      body: Aurora(
        child: t == null
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 60), children: [
                  if (_busy) const LinearProgressIndicator(),
                  DevTaskCard(app: widget.app, data: {'task': t}, onDone: _load),
                  const SizedBox(height: 10),
                  if (_s(t['text']).isNotEmpty)
                    Glass(child: Text(_s(t['text']), maxLines: 12, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, color: C.muted))),
                  const SizedBox(height: 8),
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    if ((t['pr_number'] ?? 0) != 0)
                      GlassButton(label: 'CI dekho', icon: Icons.sync_rounded, onTap: _busy ? null : () => _run('POST', '/api/devsahayak/tasks/${widget.id}/refresh')),
                    if (t['status'] == 'checks_failed')
                      GlassButton(label: 'CI theek karo', icon: Icons.build_rounded, onTap: _busy ? null : () => _run('POST', '/api/devsahayak/tasks/${widget.id}/fix_ci')),
                    if (const ['pr_open', 'checks_failed', 'ready', 'refused'].contains(t['status']))
                      GlassButton(
                          label: 'Badlav bolo',
                          icon: Icons.edit_note_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Kya badalna hai', const [('text', 'Apne shabdon mein')], ok: 'Bhejo');
                                  if (f == null || (f['text'] ?? '').isEmpty) return;
                                  await _run('POST', '/api/devsahayak/tasks/${widget.id}/revise', {'text': f['text']});
                                }),
                    if (const ['pr_open', 'checks_failed'].contains(t['status']))
                      GlassButton(label: 'Merge card', icon: Icons.merge_rounded, onTap: _busy ? null : () => _run('POST', '/api/devsahayak/tasks/${widget.id}/merge_request')),
                    if (_s(t['pr_url']).isNotEmpty)
                      GlassButton(label: 'GitHub par', icon: Icons.open_in_new_rounded, onTap: () => _open(_s(t['pr_url']))),
                    if (!const ['merged', 'cancelled'].contains(t['status']))
                      GlassButton(label: 'Band karo', icon: Icons.close_rounded, color: C.bad, onTap: _busy ? null : () => _run('POST', '/api/devsahayak/tasks/${widget.id}/cancel')),
                  ]),
                  const SizedBox(height: 10),
                  if (_s(t['diff']).isNotEmpty) ...[
                    Row(children: [
                      Text('Diff', style: display(14)),
                      const Spacer(),
                      TextButton(onPressed: () => setState(() => _diff = !_diff), child: Text(_diff ? 'Chhupao' : 'Dikhao')),
                      IconButton(
                          tooltip: 'Copy',
                          icon: const Icon(Icons.copy_rounded, size: 18),
                          onPressed: () => Clipboard.setData(ClipboardData(text: _s(t['diff'])))),
                    ]),
                    if (_diff)
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(color: const Color(0x33000000), borderRadius: BorderRadius.circular(12)),
                        child: SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: SelectableText(_s(t['diff']), style: const TextStyle(fontFamily: 'monospace', fontSize: 11.5, height: 1.3)),
                        ),
                      ),
                  ],
                  if (_s(t['test_plan']).isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text('Test plan', style: display(14)),
                    Text(_s(t['test_plan']), style: const TextStyle(fontSize: 12.5)),
                  ],
                  const SizedBox(height: 10),
                  for (final l in _list(t['log']).reversed.take(12))
                    Text('• ${_s(l['say'])}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
                ]),
              ),
      ),
    );
  }
}

/// `devsahayak_task` and `devsahayak_push`: one card per task (key data['task']['id']), updated in place.
/// A 'ready' task (public repo / ask_before_pr) shows "Haan, PR kholo": only this tap opens the PR.
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
    final say = _s(widget.data['say']);
    return Glass(
      border: ready ? C.accent : (t['status'] == 'refused' || t['status'] == 'checks_failed' ? C.bad : null),
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
        for (final f in _list(t['files']))
          Text('• ${_s(f['path'])}  +${f['added'] ?? 0} −${f['removed'] ?? 0}${f['new'] == true ? ' (nayi)' : ''}',
              style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
        for (final c in _list(t['checks']).take(6))
          Text('⚠ ${_s(c['owasp'])} ${_s(c['path'])}: ${_s(c['say'])}', style: const TextStyle(fontSize: 11.5, color: C.warn)),
        if (_s(t['error']).isNotEmpty && t['status'] == 'refused')
          Text(_s(t['error']), style: const TextStyle(fontSize: 12, color: C.bad)),
        if ((t['pr_number'] ?? 0) != 0 && _s(ci['say']).isNotEmpty)
          Text(_s(ci['say']), style: TextStyle(fontSize: 12.5, color: _ciColor(_s(ci['state'])))),
        if (_s(t['risk']).isNotEmpty) Text('Khatra: ${_s(t['risk'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        if (ready)
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, PR kholo', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : _push)),
            const SizedBox(width: 8),
            Expanded(
                child: GlassButton(
                    label: 'Mana',
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
              child: TextButton.icon(onPressed: () => _open(_s(t['pr_url'])), icon: const Icon(Icons.open_in_new_rounded, size: 16), label: const Text('PR dekho'))),
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
            for (final (e, l) in const [('COMMENT', 'Comment'), ('REQUEST_CHANGES', 'Badlav maango'), ('APPROVE', 'Approve')])
              ChoiceChip(label: Text(l), selected: _event == e, onSelected: (_) => setState(() => _event = e)),
          ]),
          const SizedBox(height: 6),
          Row(children: [
            Expanded(child: GradientButton(label: 'GitHub par post karo', icon: Icons.send_rounded, height: 44, onTap: _busy ? null : _post)),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Rehne do', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : _discard)),
          ]),
        ] else if (_s(r['url']).isNotEmpty)
          TextButton.icon(onPressed: () => _open(_s(r['url'])), icon: const Icon(Icons.open_in_new_rounded, size: 16), label: const Text('GitHub par dekho')),
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
      final f = await _form(context, 'CI ${_ciLabel(_s(a['ci_state']))}: phir bhi kyun?', const [('reason', 'Wajah (zaroori)')], ok: 'Phir bhi karo');
      if (f == null || (f['reason'] ?? '').length < 8) {
        if (mounted) _snack(context, 'Kam se kam 8 akshar ki wajah chahiye.');
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
                ? '${_s(a['repo'])} · ${_s(a['base'])} mein ${_s(a['method'])} · commit ${_s(a['head_sha'])}'
                : '${_s(a['workflow'])} · ${_s(a['ref'])} · commit ${_s(a['head_sha'])}',
            style: const TextStyle(fontSize: 12, color: C.muted)),
        Text(_s(_m(a['ci'])['say']).isEmpty ? _ciLabel(_s(a['ci_state'])) : _s(_m(a['ci'])['say']),
            style: TextStyle(fontSize: 12.5, color: _ciColor(_s(a['ci_state'])))),
        for (final n in (a['notes'] as List?) ?? const []) Text('• $n', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_m(a['inputs']).isNotEmpty) Text('Inputs: ${_m(a['inputs']).entries.map((e) => '${e.key}=${e.value}').join(', ')}', style: const TextStyle(fontSize: 12)),
        if (_s(a['force_reason']).isNotEmpty) Text('Phir bhi ki wajah: ${_s(a['force_reason'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(res['error']).isNotEmpty) Text(_s(res['error']), style: const TextStyle(fontSize: 12, color: C.bad)),
        if (_s(res['conclusion']).isNotEmpty) Text('Nateeja: ${_s(res['conclusion'])}', style: TextStyle(fontSize: 12.5, color: res['conclusion'] == 'success' ? C.ok : C.bad)),
        const SizedBox(height: 8),
        if (waiting)
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: a['needs_force'] == true ? 'Phir bhi ${merge ? 'merge' : 'deploy'}' : (merge ? 'Haan, merge karo' : 'Haan, deploy karo'),
                    icon: Icons.check_rounded,
                    height: 44,
                    onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
          ])
        else if (_s(res['url']).isNotEmpty)
          TextButton.icon(onPressed: () => _open(_s(res['url'])), icon: const Icon(Icons.open_in_new_rounded, size: 16), label: const Text('Run dekho')),
      ]),
    );
  }
}
