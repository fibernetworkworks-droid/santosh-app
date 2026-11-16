// v0.921 HOOLA CODE NATIVE - around the sessions (screens 8, 9 and 10 of claude.ai/artifact/GF4AtP5MNfV8kARgTGymuh):
// Pull requests (her team's open PRs, Hoola's draft reviews she posts, merge / deploy cards), Scheduled tasks, and
// Repos & GitHub (the token typed only here, each repo's box settings, how Hoola works). Posting, merging, deploying
// and connecting are all her taps; the server re-checks every one.
import 'package:flutter/material.dart';

import '../../native.dart';
import '../../state.dart';
import '../hoola_theme.dart';
import 'code_kit.dart';
import 'code_session.dart';
import 'code_vps.dart';

Future<void> _openSession(BuildContext context, Santosh app, String id) async {
  if (id.isEmpty) return;
  await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => HoolaTheme(appearance: app.appearance, child: CodeSessionPage(app: app, id: id))));
}

/// The frame every one of these pages shares: the top bar and a pull-to-refresh list.
class _Frame extends StatelessWidget {
  const _Frame({required this.title, required this.loading, required this.onRefresh, required this.children, this.actions = const [], this.bottom});
  final String title;
  final bool loading;
  final Future<void> Function() onRefresh;
  final List<Widget> children;
  final List<Widget> actions;
  final Widget? bottom;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          CodeTopBar(title: title, actions: actions, line: false),
          Expanded(
            child: loading
                ? const Center(child: CodeRing(size: 22))
                : RefreshIndicator(
                    onRefresh: onRefresh,
                    color: c.ink,
                    child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 28), children: children),
                  ),
          ),
          if (bottom != null) bottom!,
        ]),
      ),
    );
  }
}

// ============================================================================================== 8 · Pull requests
class CodePrsPage extends StatefulWidget {
  const CodePrsPage({super.key, required this.app});
  final Santosh app;
  @override
  State<CodePrsPage> createState() => _CodePrsPageState();
}

class _CodePrsPageState extends State<CodePrsPage> {
  Map<String, dynamic>? _ov;
  List<Map<String, dynamic>> _prs = [];
  String _repo = '';
  bool _busy = false, _prsLoading = false;
  final Map<String, String> _event = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  List<String> get _repos => [for (final r in cl(_ov?['repos'])) if (cs(r['repo']).isNotEmpty) cs(r['repo'])];

  Future<void> _load() async {
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak', quiet: true);
    if (!mounted || r == null) return;
    setState(() {
      _ov = r;
      if (!_repos.contains(_repo)) {
        final def = cs(cm(r['settings'])['default_repo']);
        _repo = _repos.contains(def) ? def : (_repos.isEmpty ? '' : _repos.first);
      }
    });
    _loadPrs();
  }

  Future<void> _loadPrs() async {
    if (_repo.isEmpty) return;
    setState(() => _prsLoading = true);
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/prs', query: {'repo': _repo}, quiet: true);
    if (mounted) setState(() {
      _prsLoading = false;
      _prs = cl(r?['prs']);
    });
  }

  Future<void> _act(String method, String path, [Object? body]) async {
    if (_busy) return;
    setState(() => _busy = true);
    await codeCall(context, widget.app, method, path, body: body);
    if (!mounted) return;
    setState(() => _busy = false);
    await _load();
  }

  Future<void> _pickRepo() async {
    final pick = await codeSheet<String>(context, widget.app,
        title: 'Repository',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              for (final r in _repos) CodeChoiceRow(label: r, mono: true, on: r == _repo, onTap: () => Navigator.pop(ctx, r)),
            ]));
    if (pick != null && mounted) {
      setState(() => _repo = pick);
      _loadPrs();
    }
  }

  Future<void> _deploy() async {
    final wf = TextEditingController(), ref = TextEditingController(), env = TextEditingController();
    final ok = await codeSheet<bool>(context, widget.app,
        title: 'Ask for a deploy',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('Runs your repo\'s own deploy workflow on ${cRepoShort(_repo)} - only after your yes on the card.',
                  style: codeSans(HoolaColors.of(ctx), size: 13.5, color: HoolaColors.of(ctx).ink2)),
              const SizedBox(height: 12),
              CodeField(controller: wf, label: 'Workflow file', hint: 'Empty = the one set for the repo', mono: true),
              CodeField(controller: ref, label: 'Branch', hint: 'Empty = the default branch', mono: true),
              CodeField(controller: env, label: "Input 'env' (if your workflow has one)", mono: true),
              CodeMain('Make the deploy card', onTap: () => Navigator.pop(ctx, true)),
            ]));
    if (ok == true && mounted) {
      await _act('POST', '/api/devsahayak/deploy_request', {
        'repo': _repo,
        if (wf.text.trim().isNotEmpty) 'workflow': wf.text.trim(),
        if (ref.text.trim().isNotEmpty) 'ref': ref.text.trim(),
        if (env.text.trim().isNotEmpty) 'inputs': {'env': env.text.trim()},
      });
    }
    wf.dispose();
    ref.dispose();
    env.dispose();
  }

  Future<void> _decide(Map<String, dynamic> a) async {
    final c = HoolaColors.of(context);
    final merge = cs(a['kind']) == 'merge';
    final force = a['needs_force'] == true;
    final reason = TextEditingController();
    final yes = await codeSheet<bool>(context, widget.app,
        title: merge ? 'Merge pull request #${ci(a['pr_number'])}?' : 'Deploy ${cRepoShort(cs(a['repo']))}?',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text(merge ? '${cs(a['method'])} into ${cs(a['base'])} · commit ${cs(a['head_sha'])}' : '${cs(a['workflow'])} · ${cs(a['ref'])} · commit ${cs(a['head_sha'])}',
                  style: codeMono(c, size: 12.5, color: c.ink2)),
              const SizedBox(height: 8),
              Text(cs(cm(a['ci'])['say']).isNotEmpty ? cs(cm(a['ci'])['say']) : 'CI: ${cs(a['ci_state']).isEmpty ? 'none' : cs(a['ci_state'])}',
                  style: codeSans(c, size: 14, color: force ? c.bad : c.ink)),
              for (final n in ((a['notes'] as List?) ?? const [])) Text('• $n', style: codeSans(c, size: 13, color: c.warn)),
              const SizedBox(height: 12),
              if (force) CodeField(controller: reason, label: 'Why go ahead anyway? (at least 8 letters)', lines: 2),
              Row(children: [
                Expanded(child: CodeOutline('No', onTap: () => Navigator.pop(ctx, false))),
                const SizedBox(width: 10),
                Expanded(flex: 2, child: CodeMain(force ? 'Go ahead anyway' : (merge ? 'Yes, merge' : 'Yes, deploy'), onTap: () => Navigator.pop(ctx, true))),
              ]),
            ]));
    final why = reason.text.trim();
    reason.dispose();
    if (yes == null || !mounted) return;
    if (yes && force && why.length < 8) {
      codeToast(context, 'A reason of at least 8 letters is needed.');
      return;
    }
    await _act('POST', '/api/devsahayak/actions/${Uri.encodeComponent(cs(a['id']))}/decide', {'yes': yes, 'hash': cs(a['hash']), if (yes && force) 'force_reason': why});
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final reviews = cl(_ov?['reviews']);
    final drafts = reviews.where((r) => cs(r['status']) == 'draft' && cs(r['hash']).isNotEmpty).toList();
    final posted = reviews.where((r) => cs(r['status']) != 'draft').take(8).toList();
    final waiting = cl(_ov?['actions']).where((a) => cs(a['status']) == 'waiting' && cs(a['hash']).isNotEmpty).toList();
    return _Frame(
      title: 'Pull requests',
      loading: _ov == null,
      onRefresh: _load,
      actions: [
        if (_repos.isNotEmpty) CodeChip(cRepoShort(_repo), mono: true, chevron: true, onTap: _pickRepo),
        const SizedBox(width: 4),
      ],
      children: [
        if (_repos.isEmpty) Padding(padding: const EdgeInsets.all(8), child: Text('Add a repo first, in Repos & GitHub.', style: codeSans(c, color: c.ink2))),
        if (waiting.isNotEmpty) ...[
          const CodeSection('Waiting for your yes'),
          for (final a in waiting)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: CodeCard(
                edge: a['needs_force'] == true ? c.bad : c.warn,
                onTap: _busy ? null : () => _decide(a),
                child: Row(children: [
                  Icon(cs(a['kind']) == 'merge' ? Icons.merge_rounded : Icons.rocket_launch_outlined, size: 20, color: c.ink2),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(cs(a['kind']) == 'merge' ? 'Merge #${ci(a['pr_number'])} ${cs(a['pr_title'])}' : 'Deploy ${cRepoShort(cs(a['repo']))}',
                          maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 15, weight: FontWeight.w500)),
                      Text(cs(cm(a['ci'])['say']).isNotEmpty ? cs(cm(a['ci'])['say']) : cRepoShort(cs(a['repo'])), maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 12.5, color: c.ink3)),
                    ]),
                  ),
                  Icon(Icons.chevron_right_rounded, color: c.ink3),
                ]),
              ),
            ),
        ],
        CodeSection('Open pull requests', trailing: _prsLoading ? const CodeRing(size: 14) : null),
        if (!_prsLoading && _prs.isEmpty && _repos.isNotEmpty) Padding(padding: const EdgeInsets.fromLTRB(4, 0, 4, 4), child: Text('No open pull requests on ${cRepoShort(_repo)}.', style: codeSans(c, size: 14, color: c.ink3))),
        if (_prs.isNotEmpty)
          CodeCard(
            padding: EdgeInsets.zero,
            child: Column(children: [
              for (final (i, p) in _prs.indexed) _prRow(c, p, reviews, last: i == _prs.length - 1),
            ]),
          ),
        for (final r in drafts) Padding(padding: const EdgeInsets.only(top: 12), child: _draft(c, r)),
        if (posted.isNotEmpty) ...[
          const CodeSection('Posted reviews'),
          CodeCard(
            padding: EdgeInsets.zero,
            child: Column(children: [
              for (final (i, r) in posted.indexed)
                InkWell(
                  onTap: () => codeOpenGithub(cs(r['url'])),
                  child: Container(
                    constraints: const BoxConstraints(minHeight: 52),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(border: i == posted.length - 1 ? null : Border(bottom: BorderSide(color: c.sunk))),
                    child: Row(children: [
                      Expanded(child: Text('#${ci(r['pr_number'])} ${cs(r['pr_title'])}', maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 14.5))),
                      Text(cs(r['status']), style: codeSans(c, size: 12.5, color: c.ink3)),
                    ]),
                  ),
                ),
            ]),
          ),
        ],
        const SizedBox(height: 16),
        if (_repos.isNotEmpty) CodeOutline('Ask for a deploy', icon: Icons.rocket_launch_outlined, onTap: _busy ? null : _deploy),
      ],
    );
  }

  Widget _prRow(HoolaColors c, Map<String, dynamic> p, List<Map<String, dynamic>> reviews, {required bool last}) {
    final n = ci(p['number']);
    final has = reviews.any((r) => ci(r['pr_number']) == n && cs(r['repo']) == _repo && cs(r['status']) != 'discarded');
    final sub = [cs(p['author']), if (p['by_hoola'] == true) "Hoola's", if (p['draft'] == true) 'draft'].where((e) => e.isNotEmpty).join(' · ');
    return Container(
      constraints: const BoxConstraints(minHeight: 60),
      padding: const EdgeInsets.fromLTRB(14, 8, 10, 8),
      decoration: BoxDecoration(border: last ? null : Border(bottom: BorderSide(color: c.sunk))),
      child: Row(children: [
        SizedBox(width: 44, child: Text('#$n', style: codeMono(c, size: 12, color: c.ink3))),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(cs(p['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 14.5)),
            if (sub.isNotEmpty) Text(sub, style: codeSans(c, size: 12.5, color: c.ink3)),
          ]),
        ),
        const SizedBox(width: 8),
        if (has)
          CodeBadge('Reviewed', fg: c.accent, bg: c.accentSoft)
        else
          CodeChip('Review', onTap: _busy ? null : () => _act('POST', '/api/devsahayak/reviews', {'repo': _repo, 'pr': n})),
      ]),
    );
  }

  Widget _draft(HoolaColors c, Map<String, dynamic> r) {
    final id = cs(r['id']);
    final ev = _event[id] ?? (cs(r['suggest']).isEmpty ? 'COMMENT' : cs(r['suggest']));
    (String, Color, Color) sev(String s) => switch (s) {
          'high' => ('Must fix', c.bad, c.badSoft),
          'medium' => ('Should fix', c.warn, c.warnSoft),
          _ => ('Small', c.ink2, c.sunk),
        };
    return CodeCard(
      lifted: true,
      radius: 18,
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        CodeBadge('Draft · only you see it', fg: c.warn, bg: c.warnSoft),
        const SizedBox(height: 8),
        Text('Review of #${ci(r['pr_number'])} · ${cs(r['pr_title'])}', style: HoolaType.replyH2(c)),
        if (cs(r['summary']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(cs(r['summary']), style: HoolaType.reply(c).copyWith(fontSize: 15))),
        const SizedBox(height: 8),
        for (final x in cl(r['comments']).take(12))
          Container(
            margin: const EdgeInsets.only(top: 8),
            padding: const EdgeInsets.fromLTRB(11, 9, 11, 9),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), border: Border.all(color: c.sunk)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                CodeBadge(sev(cs(x['severity'])).$1, fg: sev(cs(x['severity'])).$2, bg: sev(cs(x['severity'])).$3),
                const SizedBox(width: 8),
                Expanded(
                  child: Text('${cs(x['path'])}${ci(x['line']) != 0 ? ':${ci(x['line'])}' : ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 12, color: c.ink2)),
                ),
              ]),
              const SizedBox(height: 4),
              Text(cs(x['body']), style: codeSans(c, size: 14)),
            ]),
          ),
        const SizedBox(height: 14),
        Text('Post it as', style: codeSans(c, size: 12.5, weight: FontWeight.w600, color: c.ink2)),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.all(3),
          decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(14)),
          child: Row(children: [
            for (final (e, l) in const [('COMMENT', 'Comment'), ('REQUEST_CHANGES', 'Request changes'), ('APPROVE', 'Approve')])
              Expanded(
                child: Semantics(
                  selected: ev == e,
                  button: true,
                  label: l,
                  child: InkWell(
                    onTap: () => setState(() => _event[id] = e),
                    borderRadius: BorderRadius.circular(11),
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 40),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(color: ev == e ? c.surface : null, borderRadius: BorderRadius.circular(11)),
                      child: Text(l, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 12.5, weight: ev == e ? FontWeight.w600 : FontWeight.w500, color: ev == e ? c.ink : c.ink2)),
                    ),
                  ),
                ),
              ),
          ]),
        ),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(child: CodeOutline('Discard', onTap: _busy ? null : () => _act('POST', '/api/devsahayak/reviews/${Uri.encodeComponent(id)}/discard'))),
          const SizedBox(width: 10),
          Expanded(
            flex: 2,
            child: CodeMain('Post to GitHub', busy: _busy, onTap: () => _act('POST', '/api/devsahayak/reviews/${Uri.encodeComponent(id)}/post', {'hash': cs(r['hash']), 'event': ev})),
          ),
        ]),
      ]),
    );
  }
}

// ============================================================================================== 9 · Scheduled tasks
class CodeScheduledPage extends StatefulWidget {
  const CodeScheduledPage({super.key, required this.app});
  final Santosh app;
  @override
  State<CodeScheduledPage> createState() => _CodeScheduledPageState();
}

class _CodeScheduledPageState extends State<CodeScheduledPage> {
  Map<String, dynamic>? _ov;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak', quiet: true);
    if (mounted && r != null) setState(() => _ov = r);
  }

  Future<Map<String, dynamic>?> _act(String method, String path, [Object? body]) async {
    if (_busy) return null;
    setState(() => _busy = true);
    final r = await codeCall(context, widget.app, method, path, body: body);
    if (!mounted) return r;
    setState(() => _busy = false);
    await _load();
    return r;
  }

  Future<void> _new() async {
    final repos = [for (final r in cl(_ov?['repos'])) if (cs(r['repo']).isNotEmpty) cs(r['repo'])];
    if (repos.isEmpty) {
      codeToast(context, 'Add a repo first, in Repos & GitHub.');
      return;
    }
    final title = TextEditingController(), text = TextEditingController(), at = TextEditingController(text: '09:15');
    var repo = repos.first, days = 'weekly:0', mode = 'ask';
    final ok = await codeSheet<bool>(context, widget.app,
        title: 'New scheduled task',
        body: (ctx) => StatefulBuilder(builder: (ctx, set) {
              final c = HoolaColors.of(ctx);
              return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                CodeField(controller: title, label: 'Name', hint: 'Update packages and run the tests'),
                CodeField(controller: text, label: 'What Hoola should do each time', lines: 3),
                Text('Repository', style: codeSans(c, size: 12.5, weight: FontWeight.w600, color: c.ink2)),
                const SizedBox(height: 6),
                Wrap(spacing: 8, children: [for (final r in repos) CodeChip(cRepoShort(r), mono: true, on: r == repo, onTap: () => set(() => repo = r))]),
                const SizedBox(height: 10),
                Text('When', style: codeSans(c, size: 12.5, weight: FontWeight.w600, color: c.ink2)),
                const SizedBox(height: 6),
                Wrap(spacing: 8, children: [
                  for (final (d, l) in const [('daily', 'Every day'), ('weekdays', 'Mon to Fri'), ('weekly:0', 'Every Monday'), ('off', 'Only on Run now')])
                    CodeChip(l, on: d == days, onTap: () => set(() => days = d)),
                ]),
                if (days != 'off') ...[const SizedBox(height: 8), CodeField(controller: at, label: 'Time (24-hour, India time)', hint: '09:15', mono: true)],
                Text('After the run', style: codeSans(c, size: 12.5, weight: FontWeight.w600, color: c.ink2)),
                const SizedBox(height: 6),
                Wrap(spacing: 8, children: [
                  CodeChip('Ask me first', on: mode == 'ask', onTap: () => set(() => mode = 'ask')),
                  CodeChip('Open the pull request', on: mode == 'auto', onTap: () => set(() => mode = 'auto')),
                ]),
                const SizedBox(height: 14),
                CodeMain('Save', onTap: () => Navigator.pop(ctx, true)),
                const SizedBox(height: 6),
                Text('Every run is an ordinary session; merging is always your tap.', style: codeSans(c, size: 12.5, color: c.ink3)),
              ]);
            }));
    if (ok == true && mounted) {
      await _act('POST', '/api/devsahayak/schedules', {
        'title': title.text.trim(),
        'text': text.text.trim(),
        'repo': repo,
        'days': days,
        if (days != 'off') 'at': at.text.trim(),
        'mode': mode,
      });
    }
    title.dispose();
    text.dispose();
    at.dispose();
  }

  Future<void> _more(Map<String, dynamic> sc) async {
    final c = HoolaColors.of(context);
    final pick = await codeSheet<String>(context, widget.app,
        title: cs(sc['title']),
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text(cs(sc['text']), maxLines: 6, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 14, color: c.ink2)),
              const SizedBox(height: 12),
              for (final r in cl(sc['runs']).take(8))
                InkWell(
                  onTap: () => Navigator.pop(ctx, 'open:${cs(r['id'])}'),
                  child: Container(
                    constraints: const BoxConstraints(minHeight: 48),
                    child: Row(children: [
                      Container(width: 8, height: 8, decoration: BoxDecoration(color: _runColor(c, r), shape: BoxShape.circle)),
                      const SizedBox(width: 12),
                      Expanded(child: Text('${codeTitle(r)} · ${codeStatusWords[cs(r['status'])] ?? cs(r['status'])}', maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 14))),
                      Text(codeAgo(cs(r['at'])), style: codeSans(c, size: 12.5, color: c.ink3)),
                    ]),
                  ),
                ),
              const SizedBox(height: 12),
              CodeOutline('Delete this scheduled task', color: c.bad, onTap: () => Navigator.pop(ctx, 'delete')),
            ]));
    if (pick == null || !mounted) return;
    if (pick.startsWith('open:')) {
      await _openSession(context, widget.app, pick.substring(5));
      _load();
    } else if (pick == 'delete') {
      await _act('DELETE', '/api/devsahayak/schedules/${Uri.encodeComponent(cs(sc['id']))}');
    }
  }

  Color _runColor(HoolaColors c, Map<String, dynamic> r) => switch (cs(r['status'])) {
        'merged' || 'pr_open' || 'explained' => c.ok,
        'failed' || 'checks_failed' || 'refused' => c.bad,
        'plan_wait' || 'ready' => c.warn,
        _ => c.lineStrong,
      };

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final list = cl(_ov?['schedules']);
    return _Frame(
      title: 'Scheduled tasks',
      loading: _ov == null,
      onRefresh: _load,
      actions: [CodeIconButton(icon: Icons.add_rounded, label: 'New scheduled task', onTap: _busy ? null : _new)],
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 0, 4, 12),
          child: Text('A coding task that starts by itself. Every run is an ordinary session, and merging is always your tap.', style: codeSans(c, size: 14, color: c.ink2)),
        ),
        if (list.isEmpty) Padding(padding: const EdgeInsets.all(4), child: Text('No scheduled tasks yet. Tap + to make one.', style: codeSans(c, color: c.ink3))),
        for (final sc in list)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: CodeCard(
              radius: 18,
              padding: const EdgeInsets.fromLTRB(16, 12, 8, 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(cs(sc['title']), style: codeSans(c, size: 15, weight: FontWeight.w500)),
                        const SizedBox(height: 2),
                        Text('${cs(sc['when'])} · ${cRepoShort(cs(sc['repo']))}', style: codeSans(c, size: 12.5, color: c.ink3)),
                      ]),
                    ),
                  ),
                  Switch(
                    value: sc['enabled'] == true,
                    onChanged: _busy ? null : (v) => _act('PATCH', '/api/devsahayak/schedules/${Uri.encodeComponent(cs(sc['id']))}', {'enabled': v}),
                    activeColor: c.onPill,
                    activeTrackColor: c.pill,
                    inactiveThumbColor: c.surface,
                    inactiveTrackColor: c.lineStrong,
                  ),
                ]),
                if (cl(sc['runs']).isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 10, right: 8),
                    child: Row(children: [
                      for (final r in cl(sc['runs']).take(6).toList().reversed)
                        Container(width: 22, height: 6, margin: const EdgeInsets.only(right: 6), decoration: BoxDecoration(color: _runColor(c, r), borderRadius: BorderRadius.circular(3))),
                      const Spacer(),
                      Flexible(
                        flex: 4,
                        child: Text('Last run: ${codeStatusWords[cs(cl(sc['runs']).first['status'])] ?? cs(cl(sc['runs']).first['status'])}',
                            maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.right, style: codeSans(c, size: 12, color: c.ink3)),
                      ),
                    ]),
                  ),
                if (cs(sc['last_note']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(cs(sc['last_note']), style: codeSans(c, size: 12.5, color: c.bad))),
                const SizedBox(height: 6),
                Row(children: [
                  CodeChip('Run now', icon: Icons.play_arrow_rounded, onTap: _busy
                      ? null
                      : () async {
                          final r = await _act('POST', '/api/devsahayak/schedules/${Uri.encodeComponent(cs(sc['id']))}/run');
                          if (r != null && cs(r['id']).isNotEmpty && mounted) _openSession(context, widget.app, cs(r['id']));
                        }),
                  const SizedBox(width: 8),
                  CodeChip('History', onTap: () => _more(sc)),
                ]),
              ]),
            ),
          ),
      ],
    );
  }
}

// ============================================================================================== 10 · Repos & GitHub
class CodeSettingsPage extends StatefulWidget {
  const CodeSettingsPage({super.key, required this.app});
  final Santosh app;
  @override
  State<CodeSettingsPage> createState() => _CodeSettingsPageState();
}

class _CodeSettingsPageState extends State<CodeSettingsPage> {
  Map<String, dynamic>? _ov;
  bool _busy = false;
  String _open = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak', quiet: true);
    if (mounted && r != null) setState(() => _ov = r);
  }

  Future<void> _act(String method, String path, [Object? body]) async {
    if (_busy) return;
    setState(() => _busy = true);
    await codeCall(context, widget.app, method, path, body: body);
    if (!mounted) return;
    setState(() => _busy = false);
    await _load();
  }

  Map<String, dynamic> get _st => cm(_ov?['settings']);
  String _path(String full) => '/api/devsahayak/repos/${full.split('/').map(Uri.encodeComponent).join('/')}';

  Future<void> _token() async {
    final ctl = TextEditingController();
    final c = HoolaColors.of(context);
    final ok = await codeSheet<bool>(context, widget.app,
        title: 'Connect GitHub',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('Make a fine-grained token on GitHub for only the repos Hoola may work in, with these permissions:', style: codeSans(c, size: 13.5, color: c.ink2)),
              const SizedBox(height: 6),
              for (final p in ((_st['permissions'] as List?) ?? const [])) Text('• $p', style: codeSans(c, size: 13.5)),
              const SizedBox(height: 12),
              CodeField(controller: ctl, label: 'Fine-grained token', hint: 'github_pat_…', secret: true),
              CodeMain('Connect', onTap: () => Navigator.pop(ctx, true)),
              const SizedBox(height: 6),
              Text('It is typed only here, kept sealed on the server, and never sent in a chat.', style: codeSans(c, size: 12.5, color: c.ink3)),
            ]));
    final v = ctl.text.trim();
    ctl.dispose();
    if (ok == true && v.isNotEmpty && mounted) await _act('PUT', '/api/devsahayak/token', {'token': v});
  }

  // v0.942 connect GitHub like Claude Code: open the App install page, she picks her repos there, no token typed
  Future<void> _connectGithub() async {
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/github/connect', quiet: true);
    final url = cs(r?['url']);
    if (url.isEmpty || !mounted) return;
    await Native.openExternal(url: url, package: 'browser');   // v0.956 the browser, never the GitHub app
    if (!mounted) return;
    final c = HoolaColors.of(context);
    var tries = 0;
    await codeSheet<bool>(context, widget.app,
        title: 'Connecting GitHub',
        body: (ctx) => StatefulBuilder(builder: (ctx, set) {
              Future<void> check() async {
                final s = await codeCall(ctx, widget.app, 'GET', '/api/devsahayak', quiet: true);
                if (cm(s?['settings'])['app_connected'] == true && ctx.mounted) Navigator.pop(ctx, true);
              }
              if (tries == 0) {
                tries = 1;
                Future.doWhile(() async {
                  await Future<void>.delayed(const Duration(seconds: 3));
                  if (!ctx.mounted) return false;
                  await check();
                  return ctx.mounted && (tries++) < 40;
                });
              }
              return Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
                Text('Sign in on GitHub and pick the repositories Hoola may work on. Hoola brings you back here by itself — nothing to type, no token.',
                    style: codeSans(c, size: 14, color: c.ink2, height: 1.5)),
                const SizedBox(height: 14),
                Row(children: [const CodeRing(size: 18), const SizedBox(width: 10), Text('Waiting for GitHub…', style: codeSans(c, size: 14, color: c.ink3))]),
                const SizedBox(height: 14),
                CodeMain("I'm done", onTap: () => Navigator.pop(ctx, true)),
              ]);
            }));
    if (mounted) await _load();
  }

  Future<void> _addRepo() async {
    final mine = await codeCall(context, widget.app, 'GET', '/api/devsahayak/github_repos', quiet: true);
    if (!mounted) return;
    final have = {for (final r in cl(_ov?['repos'])) cs(r['repo'])};
    final ctl = TextEditingController();
    final pick = await codeSheet<String>(context, widget.app,
        title: 'Add a repo',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              for (final r in cl(mine?['repos']).where((r) => !have.contains(cs(r['repo']))).take(40))
                CodeChoiceRow(
                    label: cs(r['repo']),
                    sub: [r['private'] == true ? 'private' : 'public', cs(r['language'])].where((e) => e.isNotEmpty).join(' · '),
                    mono: true,
                    on: false,
                    onTap: () => Navigator.pop(ctx, cs(r['repo']))),
              CodeField(controller: ctl, label: 'Or type it', hint: 'owner/name', mono: true),
              CodeMain('Add', onTap: () => Navigator.pop(ctx, ctl.text.trim())),
            ]));
    ctl.dispose();
    if (pick != null && pick.contains('/') && mounted) await _act('POST', '/api/devsahayak/repos', {'repo': pick});
  }

  Future<void> _editRepo(Map<String, dynamic> r) async {
    final setup = TextEditingController(text: cs(r['setup_cmd'])), test = TextEditingController(text: cs(r['test_cmd']));
    var net = cs(cm(r['net'])['level']).isEmpty ? 'none' : cs(cm(r['net'])['level']);
    final ok = await codeSheet<bool>(context, widget.app,
        title: cs(r['repo']),
        body: (ctx) => StatefulBuilder(builder: (ctx, set) {
              final c = HoolaColors.of(ctx);
              return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                CodeField(controller: setup, label: 'Setup (installs what the code needs, once)', hint: 'pip install -r requirements.txt', mono: true),
                CodeField(controller: test, label: 'Tests', hint: 'pytest -q', mono: true),
                Text('Internet for commands in the box', style: codeSans(c, size: 12.5, weight: FontWeight.w600, color: c.ink2)),
                const SizedBox(height: 6),
                for (final (id, l, s) in const [('none', 'No internet', 'The safest'), ('limited', 'Package sites only', 'And the hosts you add on the console'), ('full', 'Any public site', 'Private addresses are always refused')])
                  CodeChoiceRow(label: l, sub: s, on: net == id, onTap: () => set(() => net = id)),
                const SizedBox(height: 6),
                CodeMain('Save', onTap: () => Navigator.pop(ctx, true)),
                const SizedBox(height: 6),
                Text('One plain line each. No key or password here - the box output is shown to the AI.', style: codeSans(c, size: 12.5, color: c.ink3)),
              ]);
            }));
    if (ok == true && mounted) {
      await _act('PATCH', _path(cs(r['repo'])), {'setup_cmd': setup.text.trim(), 'test_cmd': test.text.trim(), 'net_level': net});
    }
    setup.dispose();
    test.dispose();
  }

  Future<void> _memory(String repo) async {
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/memory', query: {'repo': repo}, quiet: true);
    if (!mounted || r == null) return;
    final rows = cl(r['observations']);
    await codeSheet<void>(context, widget.app,
        title: 'What Hoola remembers',
        body: (ctx) {
          final c = HoolaColors.of(ctx);
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('About ${cRepoShort(repo)}: what it learned in earlier sessions. Keys and private notes are never kept.', style: codeSans(c, size: 13.5, color: c.ink2)),
            const SizedBox(height: 10),
            if (rows.isEmpty) Text('Nothing yet.', style: codeSans(c, color: c.ink3)),
            for (final o in rows.take(30))
              Container(
                padding: const EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.sunk))),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(cs(o['title']).isNotEmpty ? cs(o['title']) : cs(o['text']), style: codeSans(c, size: 14.5)),
                  if (cs(o['type']).isNotEmpty) Text(cs(o['type']), style: codeSans(c, size: 12.5, color: c.ink3)),
                ]),
              ),
          ]);
        });
  }

  Future<void> _merge() async {
    final now = cs(_st['merge_method']).isEmpty ? 'squash' : cs(_st['merge_method']);
    final pick = await codeSheet<String>(context, widget.app,
        title: 'Merge method',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              for (final (id, l, s) in const [('squash', 'Squash', 'One tidy commit on main'), ('merge', 'Merge commit', 'Every commit kept'), ('rebase', 'Rebase', 'The commits replayed on main')])
                CodeChoiceRow(label: l, sub: s, on: id == now, onTap: () => Navigator.pop(ctx, id)),
            ]));
    if (pick != null && pick != now) _act('PUT', '/api/devsahayak/settings', {'merge_method': pick});
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final st = _st;
    final repos = cl(_ov?['repos']);
    final linked = st['github'] == true;
    final mm = cs(st['merge_method']).isEmpty ? 'squash' : cs(st['merge_method']);
    return _Frame(
      title: 'Repos & GitHub',
      loading: _ov == null,
      onRefresh: _load,
      children: [
        CodeCard(
          radius: 18,
          padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
          child: Row(children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle),
              child: Icon(Icons.hub_outlined, size: 20, color: c.onPill),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(linked ? 'GitHub is connected' : 'GitHub is not connected', style: codeSans(c, size: 15, weight: FontWeight.w500)),
                Text(linked
                        ? cs(st['token_label'])
                        : (st['app_available'] == true ? 'Pick your repos on GitHub — no token to type' : 'A fine-grained token, typed only here'),
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 12.5, color: c.ink3)),
              ]),
            ),
            if (st['app_connected'] == true)
              CodeChip('Remove', onTap: _busy ? null : () => _act('POST', '/api/devsahayak/github/disconnect'))
            else if (linked)
              CodeChip('Remove', onTap: _busy ? null : () => _act('DELETE', '/api/devsahayak/token'))
            else if (st['app_available'] == true)
              CodeChip('Connect', on: true, onTap: _busy ? null : _connectGithub)
            else
              CodeChip('Connect', on: true, onTap: _busy ? null : _token),
          ]),
        ),
        const CodeSection('Repos'),
        if (repos.isNotEmpty)
          CodeCard(
            radius: 18,
            padding: EdgeInsets.zero,
            child: Column(children: [for (final (i, r) in repos.indexed) _repo(c, r, last: i == repos.length - 1)]),
          ),
        const SizedBox(height: 8),
        CodeOutline('Add a repo', icon: Icons.add_rounded, onTap: _busy || !linked ? null : _addRepo),
        const CodeSection('Your servers'),
        CodeCard(
          radius: 18,
          onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
              builder: (_) => HoolaTheme(appearance: widget.app.appearance, child: CodeServersPage(app: widget.app)))),
          child: Row(children: [
            Container(width: 40, height: 40, decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle),
                child: Icon(Icons.dns_rounded, size: 20, color: c.onPill)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Connect a server', style: codeSans(c, size: 15, weight: FontWeight.w500)),
                Text('Deploy, read logs and restart your app on your own VPS', maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 12.5, color: c.ink3)),
              ]),
            ),
            Icon(Icons.chevron_right_rounded, size: 20, color: c.ink3),
          ]),
        ),
        const CodeSection('How Hoola works'),
        CodeCard(
          radius: 18,
          padding: EdgeInsets.zero,
          child: Column(children: [
            CodeSwitchRow(label: 'Open pull requests as drafts', value: st['draft_pr'] == true, onChanged: _busy ? null : (v) => _act('PUT', '/api/devsahayak/settings', {'draft_pr': v})),
            CodeSwitchRow(
                label: 'Ask before every pull request',
                sub: 'A public repo always asks',
                value: st['ask_before_pr'] == true,
                onChanged: _busy ? null : (v) => _act('PUT', '/api/devsahayak/settings', {'ask_before_pr': v})),
            CodeSwitchRow(
                label: 'Post reviews straight away',
                sub: 'Comments only. Approve is always your tap',
                value: st['review_post'] == 'direct',
                onChanged: _busy ? null : (v) => _act('PUT', '/api/devsahayak/settings', {'review_post': v ? 'direct' : 'draft'})),
            CodeSwitchRow(
                label: 'May change CI workflow files',
                sub: 'A workflow runs with the repo\'s permissions',
                value: st['allow_workflows'] == true,
                onChanged: _busy ? null : (v) => _act('PUT', '/api/devsahayak/settings', {'allow_workflows': v})),
            InkWell(
              onTap: _busy ? null : _merge,
              child: Container(
                constraints: const BoxConstraints(minHeight: 52),
                padding: const EdgeInsets.fromLTRB(14, 8, 14, 8),
                child: Row(children: [
                  Expanded(child: Text('Merge method', style: codeSans(c, size: 14.5))),
                  Text('${mm[0].toUpperCase()}${mm.substring(1)}', style: codeSans(c, size: 14, color: c.ink2)),
                  Icon(Icons.chevron_right_rounded, color: c.ink3),
                ]),
              ),
            ),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(6, 12, 6, 0),
          child: Text('Hoola never merges, deploys or touches main on its own. Keys are typed only here and never reach the box.',
              style: codeSans(c, size: 12.5, color: c.ink3)),
        ),
      ],
    );
  }

  Widget _repo(HoolaColors c, Map<String, dynamic> r, {required bool last}) {
    final full = cs(r['repo']);
    final open = _open == full;
    final net = cs(cm(r['net'])['level']);
    final keys = cl(cm(r['net'])['secrets']);
    Widget kv(String k, String v, {bool mono = false}) => Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 92, child: Text(k, style: codeSans(c, size: 13, color: c.ink3))),
            Expanded(child: Text(v.isEmpty ? '—' : v, maxLines: 2, overflow: TextOverflow.ellipsis, style: mono && v.isNotEmpty ? codeMono(c, size: 12.5) : codeSans(c, size: 13.5))),
          ]),
        );
    return Container(
      decoration: BoxDecoration(border: last ? null : Border(bottom: BorderSide(color: c.sunk))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        InkWell(
          onTap: () => setState(() => _open = open ? '' : full),
          child: Container(
            constraints: const BoxConstraints(minHeight: 54),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            child: Row(children: [
              Icon(r['private'] == true ? Icons.lock_outline_rounded : Icons.public_rounded, size: 17, color: c.ink3),
              const SizedBox(width: 10),
              Expanded(child: Text(full, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 13.5))),
              if (!open) Text(net == 'full' ? 'Any site' : (net == 'limited' ? 'Packages' : 'No internet'), style: codeSans(c, size: 12, color: c.ink3)),
              Icon(open ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded, size: 18, color: c.ink3),
            ]),
          ),
        ),
        if (open)
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              kv('Branch', cs(r['default_branch']), mono: true),
              kv('Setup', cs(r['setup_cmd']), mono: true),
              kv('Tests', cs(r['test_cmd']), mono: true),
              kv('Internet', net == 'full' ? 'Any public site' : (net == 'limited' ? 'Package sites only' : 'No internet')),
              kv('Keys', keys.isEmpty ? 'None' : '${keys.length} · ${keys.map((k) => cs(k['host'])).join(', ')}'),
              kv('GitHub events', cm(r['events'])['on'] == true ? 'On' : 'Off'),
              const SizedBox(height: 4),
              Wrap(spacing: 8, children: [
                CodeChip('Edit', onTap: _busy ? null : () => _editRepo(r)),
                CodeChip('What Hoola remembers', onTap: () => _memory(full)),
                CodeChip('Remove', onTap: _busy ? null : () => _act('DELETE', _path(full))),
              ]),
            ]),
          ),
      ]),
    );
  }
}
