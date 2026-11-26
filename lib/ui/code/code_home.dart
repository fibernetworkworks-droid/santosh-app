// v0.921 HOOLA CODE NATIVE - the home (screen 1 of claude.ai/artifact/GF4AtP5MNfV8kARgTGymuh). Tools > Hoola Code and
// Your AI team > Developer both open this. v0.924: a session starts on its own New session screen (code_start.dart,
// the design claude.ai/artifact/Au9zBc5gmkVsNLwVc41rCM); the home keeps the list and a New session button.
import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_auto.dart' show AutoHomePage;
import '../hoola_theme.dart';
import 'code_kit.dart';
import 'code_more.dart';
import 'code_vps.dart';
import 'code_session.dart';
import 'code_start.dart';

/// Opens a page of Hoola Code in the new design.
Future<T?> codePush<T>(BuildContext context, Santosh app, Widget page) =>
    Navigator.of(context).push<T>(MaterialPageRoute<T>(builder: (_) => HoolaTheme(appearance: app.appearance, child: page)));

class HoolaCode extends StatefulWidget {
  const HoolaCode({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaCode> createState() => _HoolaCodeState();
}

class _HoolaCodeState extends State<HoolaCode> {
  Map<String, dynamic>? _ov;
  String? _error;
  bool _all = false;
  Timer? _poll;
  int _autoAll = -1; // v0.954 Hoola Auto projects (-1 = the server has none / not read yet)
  int _autoNeed = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) return;
    _loadAuto();
    try {
      final r = await api.call('GET', '/api/devsahayak');
      if (!mounted) return;
      setState(() {
        _ov = cm(r);
        _error = null;
      });
      final live = cl(_ov?['tasks']).any(codeRunning);
      if (live) {
        _poll ??= Timer.periodic(const Duration(seconds: 5), (_) => _load());
      } else {
        _poll?.cancel();
        _poll = null;
      }
    } catch (e) {
      if (mounted) setState(() => _error = '$e'.replaceFirst('Exception: ', ''));
    }
  }

  // v0.954 the door to Hoola Auto on this screen (it was only in the old drawer, which this screen never shows)
  Future<void> _loadAuto() async {
    try {
      final ps = cl(cm(await widget.app.api!.call('GET', '/api/auto/projects'))['projects']);
      if (!mounted) return;
      setState(() {
        _autoAll = ps.length;
        _autoNeed = ps.where((p) => cs(p['state']) == 'need').length;
      });
    } catch (_) {
      // a server without Hoola Auto: the card still opens it and says so there
    }
  }

  Widget _autoCard(HoolaColors c) {
    final sub = _autoNeed > 0
        ? '$_autoNeed ${_autoNeed == 1 ? 'project needs' : 'projects need'} you'
        : _autoAll > 0
            ? '$_autoAll ${_autoAll == 1 ? 'project' : 'projects'} · intake, talk, monitor'
            : 'Hand over a whole client project to a team of agents';
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: CodeCard(
        key: const ValueKey('code-home-auto'),
        edge: _autoNeed > 0 ? c.warn : null,
        onTap: () => _go(AutoHomePage(app: widget.app)),
        child: Row(children: [
          Icon(Icons.hub_outlined, size: 22, color: _autoNeed > 0 ? c.warn : c.ink),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Hoola Auto', style: codeSans(c, size: 15, weight: FontWeight.w500)),
              Text(sub, style: codeSans(c, size: 13, color: c.ink2)),
            ]),
          ),
          Icon(Icons.chevron_right_rounded, color: c.ink3),
        ]),
      ),
    );
  }

  Future<void> _open(String id) async {
    if (id.isEmpty) return;
    await codePush<void>(context, widget.app, CodeSessionPage(app: widget.app, id: id));
    _load();
  }

  Future<void> _newSession([String prefill = '']) => showCodeNewSession(context, widget.app, prefill: prefill, onStarted: (id) {
        _load();
        _open(id);
      });

  Future<void> _go(Widget page) async {
    await codePush<void>(context, widget.app, page);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final ov = _ov;
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          Container(
            height: 56,
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Row(children: [
              CodeIconButton(icon: Icons.arrow_back_ios_new_rounded, size: 19, label: 'Back', onTap: () => Navigator.of(context).maybePop()),
              const CodeMark(size: 21),
              const SizedBox(width: 8),
              Expanded(child: Text('Hoola Code', style: codeSans(c, size: 17, weight: FontWeight.w600))),
              CodeIconButton(icon: Icons.call_split_rounded, label: 'Pull requests', onTap: ov == null ? null : () => _go(CodePrsPage(app: widget.app))),
              CodeIconButton(icon: Icons.schedule_rounded, label: 'Scheduled tasks', onTap: ov == null ? null : () => _go(CodeScheduledPage(app: widget.app))),
              CodeIconButton(icon: Icons.dns_rounded, label: 'Servers', onTap: () => _go(CodeServersPage(app: widget.app))),
              CodeIconButton(icon: Icons.tune_rounded, label: 'Repos and GitHub', onTap: ov == null ? null : () => _go(CodeSettingsPage(app: widget.app))),
            ]),
          ),
          Expanded(
            child: ov == null
                ? Center(
                    child: _error == null
                        ? const CodeRing(size: 22)
                        : Padding(
                            padding: const EdgeInsets.all(24),
                            child: Column(mainAxisSize: MainAxisSize.min, children: [
                              Text(_error!, textAlign: TextAlign.center, style: codeSans(c, color: c.ink2)),
                              const SizedBox(height: 14),
                              CodeOutline('Try again', onTap: _load, icon: Icons.refresh_rounded),
                            ]),
                          ))
                : RefreshIndicator(
                    onRefresh: _load,
                    color: c.ink,
                    child: ListView(padding: const EdgeInsets.fromLTRB(20, 10, 20, 32), children: _body(c, ov)),
                  ),
          ),
          if (ov != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 14),
              child: CodeMain('New session', icon: Icons.add_rounded, onTap: () => _newSession()),
            ),
        ]),
      ),
    );
  }

  List<Widget> _body(HoolaColors c, Map<String, dynamic> ov) {
    final st = cm(ov['settings']);
    final repos = cl(ov['repos']);
    final tasks = cl(ov['tasks']).where((t) => t['archived'] != true).toList();
    final actions = cl(ov['actions']);
    final by = <String, List<Map<String, dynamic>>>{'need': [], 'run': [], 'old': []};
    for (final t in tasks) {
      by[codeGroup(t, actions)]!.add(t);
    }
    final old = _all ? by['old']! : by['old']!.take(6).toList();
    return [
      Text('What should we build today?', style: HoolaType.hero(c)),
      const SizedBox(height: 14),
      if (st['github'] != true)
        _note(c, Icons.link_rounded, 'Connect GitHub first', 'Add your fine-grained token in Repos & GitHub. It is typed only there.',
            () => _go(CodeSettingsPage(app: widget.app)))
      else if (repos.isEmpty)
        _note(c, Icons.add_rounded, 'Add a repo', 'Pick the repos Hoola may work in.', () => _go(CodeSettingsPage(app: widget.app))),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          for (final (label, fill) in const [('Fix a bug', '/fix '), ('Write tests', '/tests '), ('Explain the repo', 'Explain how this repo is laid out')]) ...[
            CodeChip(label, onTap: () => _newSession(fill)),
            const SizedBox(width: 8),
          ],
          CodeChip('Review a PR', onTap: () => _go(CodePrsPage(app: widget.app))),
        ]),
      ),
      _autoCard(c),
      if (tasks.isEmpty)
        Padding(
          padding: const EdgeInsets.only(top: 28),
          child: Text('Your sessions show here. Each one works on its own branch and ends with a pull request you can check.',
              style: codeSans(c, size: 14, color: c.ink3)),
        ),
      if (by['need']!.isNotEmpty) ...[
        CodeSection('Needs you', trailing: Text('${by['need']!.length}', style: codeSans(c, size: 12.5, color: c.ink3))),
        for (final t in by['need']!) Padding(padding: const EdgeInsets.only(bottom: 8), child: _row(c, t, 'need')),
      ],
      if (by['run']!.isNotEmpty) ...[
        CodeSection('Working', trailing: Text('${by['run']!.length}', style: codeSans(c, size: 12.5, color: c.ink3))),
        for (final t in by['run']!) Padding(padding: const EdgeInsets.only(bottom: 8), child: _row(c, t, 'run')),
      ],
      if (old.isNotEmpty) ...[
        CodeSection('Earlier',
            trailing: by['old']!.length > 6
                ? InkWell(
                    onTap: () => setState(() => _all = !_all),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
                      child: Text(_all ? 'Show less' : 'See all', style: codeSans(c, size: 13, color: c.ink2)),
                    ),
                  )
                : null),
        CodeCard(
          padding: EdgeInsets.zero,
          child: Column(children: [for (final (i, t) in old.indexed) _oldRow(c, t, last: i == old.length - 1)]),
        ),
      ],
    ];
  }

  Widget _note(HoolaColors c, IconData icon, String title, String sub, VoidCallback onTap) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: CodeCard(
          edge: c.warn,
          onTap: onTap,
          child: Row(children: [
            Icon(icon, size: 20, color: c.warn),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: codeSans(c, size: 15, weight: FontWeight.w500)),
                Text(sub, style: codeSans(c, size: 13, color: c.ink2)),
              ]),
            ),
            Icon(Icons.chevron_right_rounded, color: c.ink3),
          ]),
        ),
      );

  Widget _row(HoolaColors c, Map<String, dynamic> t, String group) {
    final need = group == 'need';
    final secs = DateTime.now().difference(codeTime(cs(t['run_at']).isEmpty ? cs(t['at']) : cs(t['run_at'])) ?? DateTime.now()).inSeconds;
    final words = cs(t['question']).isNotEmpty ? 'Hoola asks you a question' : codeStatus(t);
    final (a, r) = codeStat(t);
    return CodeCard(
      edge: need ? c.warn : null,
      onTap: () => _open(cs(t['id'])),
      padding: const EdgeInsets.fromLTRB(16, 12, 14, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(codeTitle(t), maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 15, weight: FontWeight.w500))),
          const SizedBox(width: 8),
          if (need) CodeBadge(words.length > 22 ? 'Needs you' : words, fg: c.warn, bg: c.warnSoft)
          else Text(codeClock(secs), style: codeMono(c, size: 12, color: c.ink3)),
        ]),
        const SizedBox(height: 5),
        Row(children: [
          if (!need) ...[const CodeRing(size: 14), const SizedBox(width: 8)],
          Expanded(
            child: Text(
                need ? '${cRepoShort(cs(t['repo']))} · ${cPlural(cl(t['files']).length, 'file')} · ${words.toLowerCase()}' : '${cRepoShort(cs(t['repo']))} · working',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: codeSans(c, size: 13, color: c.ink2)),
          ),
          CodeStat(a, r),
        ]),
      ]),
    );
  }

  Widget _oldRow(HoolaColors c, Map<String, dynamic> t, {required bool last}) {
    final st = cs(t['status']);
    final pr = ci(t['pr_number']);
    final (IconData icon, Color col) = switch (st) {
      'merged' => (Icons.merge_rounded, c.ok),
      'explained' => (Icons.notes_rounded, c.ink3),
      'failed' || 'refused' => (Icons.error_outline_rounded, c.bad),
      'cancelled' || 'closed' => (Icons.do_not_disturb_on_outlined, c.ink3),
      _ => (Icons.call_split_rounded, c.ok),
    };
    final sub = [if (pr != 0) 'PR #$pr', codeStatus(t), codeAgo(cs(t['updated']).isNotEmpty ? cs(t['updated']) : cs(t['at']))]
        .where((e) => e.isNotEmpty)
        .join(' · ');
    final (a, r) = codeStat(t);
    return InkWell(
      onTap: () => _open(cs(t['id'])),
      child: Container(
        constraints: const BoxConstraints(minHeight: 60),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(border: last ? null : Border(bottom: BorderSide(color: c.sunk))),
        child: Row(children: [
          Icon(icon, size: 19, color: col),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(codeTitle(t), maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 14.5)),
              Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 12.5, color: c.ink3)),
            ]),
          ),
          const SizedBox(width: 8),
          CodeStat(a, r),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------------------------------------- the composer
/// What she is about to start; kept while she looks at another screen.
class CodeDraft extends ChangeNotifier {
  final text = TextEditingController();
  String repo = '', base = '', mode = '', model = '', effort = '';
  final images = <({String name, Uint8List bytes})>[];
  final docs = <({String name, String text})>[];

  void prefill(String s) {
    text.text = s;
    text.selection = TextSelection.collapsed(offset: s.length);
    notifyListeners();
  }

  void clear() {
    text.clear();
    images.clear();
    docs.clear();
    base = '';
    notifyListeners();
  }

  @override
  void dispose() {
    text.dispose();
    super.dispose();
  }
}

const codeModes = [
  ('ask', 'Ask first', 'Hoola shows the change, you open the pull request'),
  ('plan', 'Plan first', 'A plan to check before any file is touched'),
  ('auto', 'On its own', 'Works and opens the pull request by itself'),
];
