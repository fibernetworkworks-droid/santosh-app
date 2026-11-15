// v0.921 HOOLA CODE NATIVE - the home (screen 1 of claude.ai/artifact/GF4AtP5MNfV8kARgTGymuh) and the composer that
// starts a session (screen 7). Tools > Hoola Code and Your AI team > Developer both open this.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'code_kit.dart';
import 'code_more.dart';
import 'code_session.dart';

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
  final _draft = CodeDraft();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    _draft.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) return;
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

  Future<void> _open(String id) async {
    if (id.isEmpty) return;
    await codePush<void>(context, widget.app, CodeSessionPage(app: widget.app, id: id));
    _load();
  }

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
      Text('What should we build today?', style: HoolaType.hero(c).copyWith(fontSize: 28)),
      const SizedBox(height: 14),
      if (st['github'] != true)
        _note(c, Icons.link_rounded, 'Connect GitHub first', 'Add your fine-grained token in Repos & GitHub. It is typed only there.',
            () => _go(CodeSettingsPage(app: widget.app)))
      else if (repos.isEmpty)
        _note(c, Icons.add_rounded, 'Add a repo', 'Pick the repos Hoola may work in.', () => _go(CodeSettingsPage(app: widget.app))),
      CodeComposer(app: widget.app, ov: ov, draft: _draft, onStarted: (id) {
        _load();
        _open(id);
      }),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          for (final (label, fill) in const [('Fix a bug', '/fix '), ('Write tests', '/tests '), ('Explain the repo', 'Explain how this repo is laid out')]) ...[
            CodeChip(label, onTap: () => _draft.prefill(fill)),
            const SizedBox(width: 8),
          ],
          CodeChip('Review a PR', onTap: () => _go(CodePrsPage(app: widget.app))),
        ]),
      ),
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
    final secs = DateTime.now().difference(DateTime.tryParse(cs(t['at'])) ?? DateTime.now()).inSeconds;
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

/// Slash words she can type at the start: /fix /tests /docs /explain /feature /plan.
const _slash = {'fix': 'fix', 'bug': 'fix', 'tests': 'tests', 'test': 'tests', 'docs': 'docs', 'explain': 'explain', 'feature': 'write', 'write': 'write'};

class CodeComposer extends StatefulWidget {
  const CodeComposer({super.key, required this.app, required this.ov, required this.draft, required this.onStarted, this.inSheet = false});
  final Santosh app;
  final Map<String, dynamic> ov;
  final CodeDraft draft;
  final ValueChanged<String> onStarted;
  final bool inSheet;
  @override
  State<CodeComposer> createState() => _CodeComposerState();
}

class _CodeComposerState extends State<CodeComposer> {
  bool _busy = false;
  CodeDraft get d => widget.draft;
  Map<String, dynamic> get _st => cm(widget.ov['settings']);
  Map<String, dynamic> get _models => cm(widget.ov['models']);
  List<String> get _repos => [for (final r in cl(widget.ov['repos'])) if (cs(r['repo']).isNotEmpty) cs(r['repo'])];

  String get repo {
    if (_repos.contains(d.repo)) return d.repo;
    final def = cs(_st['default_repo']);
    if (_repos.contains(def)) return def;
    return _repos.isEmpty ? '' : _repos.first;
  }

  String get mode => d.mode.isNotEmpty ? d.mode : (_st['ask_before_pr'] == true ? 'ask' : 'auto');

  String get _branch {
    if (d.base.isNotEmpty) return d.base;
    for (final r in cl(widget.ov['repos'])) {
      if (cs(r['repo']) == repo) return cs(r['default_branch']).isEmpty ? 'main' : cs(r['default_branch']);
    }
    return 'main';
  }

  String get _modelLabel {
    final f = cm(_models['forced']);
    if (f.isNotEmpty) return cs(f['model']);
    final id = d.model.isNotEmpty ? d.model : cs(_models['default']);
    final opt = cl(_models['options']).firstWhere((o) => cs(o['id']) == id, orElse: () => {'label': id});
    final eff = d.effort.isNotEmpty ? d.effort : cs(_models['default_effort']);
    final e = eff.isEmpty ? '' : ' · ${eff[0].toUpperCase()}${eff.substring(1)}';
    return '${cs(opt['label']).isEmpty ? 'Default model' : cs(opt['label'])}$e';
  }

  @override
  void initState() {
    super.initState();
    d.addListener(_changed);
  }

  @override
  void dispose() {
    d.removeListener(_changed);
    super.dispose();
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  Future<void> _pickRepo() async {
    final c = HoolaColors.of(context);
    final pick = await codeSheet<String>(context, widget.app,
        title: 'Repository',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              for (final r in cl(widget.ov['repos']))
                CodeChoiceRow(
                    label: cs(r['repo']),
                    sub: [cs(r['default_branch']), r['private'] == true ? 'private' : 'public', cs(r['language'])].where((e) => e.isNotEmpty).join(' · '),
                    mono: true,
                    on: cs(r['repo']) == repo,
                    onTap: () => Navigator.pop(ctx, cs(r['repo']))),
              if (_repos.isEmpty) Text('No repo yet - add one in Repos & GitHub.', style: codeSans(c, color: c.ink2)),
            ]));
    if (pick != null && mounted) setState(() {
      d.repo = pick;
      d.base = '';
    });
  }

  Future<void> _pickBranch() async {
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/branches', query: {'repo': repo}, quiet: true);
    if (!mounted) return;
    final list = [for (final b in ((r?['branches'] as List?) ?? const [])) if (!cs(b is Map ? b['name'] : b).startsWith('hoola/')) cs(b is Map ? b['name'] : b)];
    if (list.isEmpty) list.add(_branch);
    final pick = await codeSheet<String>(context, widget.app,
        title: 'Start from',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              for (final b in list.take(40)) CodeChoiceRow(label: b, mono: true, on: b == _branch, onTap: () => Navigator.pop(ctx, b)),
            ]));
    if (pick != null && mounted) setState(() => d.base = pick);
  }

  Future<void> _pickMode() async {
    final pick = await codeSheet<String>(context, widget.app,
        title: 'How it works',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              for (final (id, label, sub) in codeModes) CodeChoiceRow(label: label, sub: sub, on: id == mode, onTap: () => Navigator.pop(ctx, id)),
              Text('Nothing is ever merged without your tap.', style: codeSans(HoolaColors.of(ctx), size: 13, color: HoolaColors.of(ctx).ink3)),
            ]));
    if (pick != null && mounted) setState(() => d.mode = pick);
  }

  Future<void> _pickModel() async {
    final f = cm(_models['forced']);
    if (f.isNotEmpty) {
      codeToast(context, cs(f['why']));
      return;
    }
    await codeSheet<void>(context, widget.app,
        title: 'Model',
        body: (ctx) => StatefulBuilder(builder: (ctx, set) {
              final c = HoolaColors.of(ctx);
              final id = d.model.isNotEmpty ? d.model : cs(_models['default']);
              final eff = d.effort.isNotEmpty ? d.effort : cs(_models['default_effort']);
              return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                for (final o in cl(_models['options']))
                  CodeChoiceRow(label: cs(o['label']), on: cs(o['id']) == id, onTap: () => set(() => d.model = cs(o['id']))),
                const SizedBox(height: 6),
                Text('How hard it thinks', style: codeSans(c, size: 12.5, weight: FontWeight.w600, color: c.ink2)),
                const SizedBox(height: 6),
                Wrap(spacing: 8, children: [
                  for (final e in ((_models['efforts'] as List?) ?? const ['low', 'medium', 'high']))
                    CodeChip('${cs(e)[0].toUpperCase()}${cs(e).substring(1)}', on: cs(e) == eff, onTap: () => set(() => d.effort = cs(e))),
                ]),
                Text('Higher is slower and costs more.', style: codeSans(c, size: 12.5, color: c.ink3)),
                const SizedBox(height: 12),
                CodeMain('Done', onTap: () => Navigator.pop(ctx)),
              ]);
            }));
    if (mounted) setState(() {});
  }

  Future<void> _attach() async {
    final pick = await codeSheet<String>(context, widget.app,
        title: 'Add to the session',
        body: (ctx) {
          final c = HoolaColors.of(ctx);
          Widget row(String id, IconData icon, String label, String sub) => InkWell(
                onTap: () => Navigator.pop(ctx, id),
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  constraints: const BoxConstraints(minHeight: 56),
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: c.line)),
                  child: Row(children: [
                    Icon(icon, color: c.ink2),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(label, style: codeSans(c, weight: FontWeight.w500)),
                        Text(sub, style: codeSans(c, size: 12.5, color: c.ink3)),
                      ]),
                    ),
                  ]),
                ),
              );
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            row('pic', Icons.photo_library_outlined, 'Pictures', 'A screenshot of the problem · up to 3'),
            row('doc', Icons.description_outlined, 'Text file', 'A log, an error, a spec · up to 3'),
          ]);
        });
    if (!mounted || pick == null) return;
    try {
      if (pick == 'pic') {
        final xs = await ImagePicker().pickMultiImage(imageQuality: 85, maxWidth: 2400, maxHeight: 2400);
        for (final x in xs) {
          if (d.images.length >= 3) break;
          final b = await x.readAsBytes();
          if (b.length > 3000000) {
            if (mounted) codeToast(context, '${x.name} is bigger than 3 MB.');
            continue;
          }
          d.images.add((name: x.name, bytes: b));
        }
      } else {
        final res = await FilePicker.platform.pickFiles(withData: true, allowMultiple: true, type: FileType.any);
        for (final f in res?.files ?? const <PlatformFile>[]) {
          if (d.docs.length >= 3) break;
          final b = f.bytes;
          if (b == null) continue;
          final text = utf8.decode(b, allowMalformed: true);
          if (text.contains('\u0000')) {
            if (mounted) codeToast(context, '${f.name} is not a text file.');
            continue;
          }
          d.docs.add((name: f.name, text: text.length > 12000 ? text.substring(0, 12000) : text));
        }
      }
    } catch (e) {
      if (mounted) codeToast(context, 'It did not open: $e');
    }
    if (mounted) setState(() {});
  }

  Future<void> _start() async {
    var text = d.text.text.trim();
    var kind = 'auto';
    var m = mode;
    final sl = RegExp(r'^/([a-z]+)\b\s*').firstMatch(text);
    if (sl != null) {
      final w = sl.group(1)!;
      if (w == 'plan') {
        m = 'plan';
      } else if (_slash.containsKey(w)) {
        kind = _slash[w]!;
      }
      text = text.substring(sl.end).trim();
    }
    if (text.isEmpty) {
      codeToast(context, 'Describe the task, or paste the error.');
      return;
    }
    if (repo.isEmpty) {
      codeToast(context, 'Add a repo first, in Repos & GitHub.');
      return;
    }
    setState(() => _busy = true);
    final r = await codeCall(context, widget.app, 'POST', '/api/devsahayak/tasks/start', body: {
      'kind': kind,
      'text': text,
      'repo': repo,
      'base': d.base,
      'mode': m,
      'model': d.model,
      'effort': d.effort,
      'images': [for (final i in d.images) {'name': i.name, 'data': base64Encode(i.bytes)}],
      'docs': [for (final x in d.docs) {'name': x.name, 'text': x.text}],
    });
    if (!mounted) return;
    setState(() => _busy = false);
    final id = cs(r?['id']);
    if (id.isNotEmpty) {
      d.clear();
      widget.onStarted(id);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final modeLabel = codeModes.firstWhere((x) => x.$1 == mode, orElse: () => codeModes.first).$2;
    final hasFiles = d.images.isNotEmpty || d.docs.isNotEmpty;
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 10, 8),
      decoration: BoxDecoration(
        color: c.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: c.line.withOpacity(.8)),
        boxShadow: c.dark ? null : [BoxShadow(color: c.shadow.withOpacity(.16), blurRadius: 24, spreadRadius: -16, offset: const Offset(0, 8))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 6, children: [
          CodeChip(repo.isEmpty ? 'No repo yet' : cRepoShort(repo), icon: Icons.account_tree_outlined, mono: true, chevron: true, onTap: _pickRepo),
          if (repo.isNotEmpty) CodeChip(_branch, mono: true, chevron: true, onTap: _pickBranch),
        ]),
        if (hasFiles)
          SizedBox(
            height: 64,
            child: ListView(scrollDirection: Axis.horizontal, children: [
              for (final (i, im) in d.images.indexed) _thumb(c, Image.memory(im.bytes, width: 56, height: 56, fit: BoxFit.cover), () => setState(() => d.images.removeAt(i)), im.name),
              for (final (i, x) in d.docs.indexed) _docChip(c, x.name, () => setState(() => d.docs.removeAt(i))),
            ]),
          ),
        TextField(
          controller: d.text,
          minLines: widget.inSheet ? 3 : 2,
          maxLines: 8,
          maxLength: 20000,
          textInputAction: TextInputAction.newline,
          style: codeSans(c, size: 16, height: 1.45),
          decoration: InputDecoration(
            hintText: 'Describe a task for this repo…',
            hintStyle: codeSans(c, size: 16, color: c.ink3),
            border: InputBorder.none,
            counterText: '',
            contentPadding: const EdgeInsets.fromLTRB(2, 6, 2, 6),
          ),
        ),
        Row(children: [
          Semantics(
            button: true,
            label: 'Add pictures or a text file',
            child: InkResponse(
              onTap: _attach,
              radius: 24,
              child: Container(
                width: 48,
                height: 48,
                alignment: Alignment.center,
                child: Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: c.line)),
                  child: Icon(Icons.add_rounded, size: 20, color: c.ink),
                ),
              ),
            ),
          ),
          Flexible(child: CodeChip(modeLabel, icon: Icons.fact_check_outlined, onTap: _pickMode)),
          const SizedBox(width: 6),
          Flexible(child: CodeChip(_modelLabel, onTap: _pickModel)),
          const Spacer(),
          Semantics(
            button: true,
            label: 'Start session',
            child: InkResponse(
              onTap: _busy ? null : _start,
              radius: 24,
              child: SizedBox(
                width: 48,
                height: 48,
                child: Center(
                  child: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle),
                    child: _busy
                        ? Padding(padding: const EdgeInsets.all(11), child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                        : Icon(Icons.arrow_upward_rounded, size: 20, color: c.onPill),
                  ),
                ),
              ),
            ),
          ),
        ]),
      ]),
    );
  }

  Widget _thumb(HoolaColors c, Widget img, VoidCallback remove, String name) => Padding(
        padding: const EdgeInsets.fromLTRB(0, 6, 10, 2),
        child: Stack(clipBehavior: Clip.none, children: [
          ClipRRect(borderRadius: BorderRadius.circular(12), child: img),
          Positioned(
            top: -6,
            right: -6,
            child: Semantics(
              button: true,
              label: 'Remove $name',
              child: GestureDetector(
                onTap: remove,
                child: Container(
                  width: 24,
                  height: 24,
                  decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle, border: Border.all(color: c.surface, width: 2)),
                  child: Icon(Icons.close_rounded, size: 13, color: c.onPill),
                ),
              ),
            ),
          ),
        ]),
      );

  Widget _docChip(HoolaColors c, String name, VoidCallback remove) => Padding(
        padding: const EdgeInsets.fromLTRB(0, 6, 10, 2),
        child: Container(
          height: 56,
          padding: const EdgeInsets.only(left: 12),
          decoration: BoxDecoration(color: c.bg, borderRadius: BorderRadius.circular(12), border: Border.all(color: c.line)),
          child: Row(children: [
            Icon(Icons.description_outlined, size: 18, color: c.ink2),
            const SizedBox(width: 8),
            ConstrainedBox(constraints: const BoxConstraints(maxWidth: 140), child: Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 12))),
            CodeIconButton(icon: Icons.close_rounded, size: 16, label: 'Remove $name', onTap: remove),
          ]),
        ),
      );
}

/// Screen 7: the New session sheet (from a finished session).
Future<void> showCodeNewSession(BuildContext context, Santosh app, {required ValueChanged<String> onStarted}) async {
  final r = await codeCall(context, app, 'GET', '/api/devsahayak', quiet: true);
  if (r == null || !context.mounted) return;
  final draft = CodeDraft();
  await codeSheet<void>(context, app,
      title: 'New session',
      body: (ctx) => CodeComposer(
          app: app,
          ov: r,
          draft: draft,
          inSheet: true,
          onStarted: (id) {
            Navigator.pop(ctx);
            onStarted(id);
          }));
  draft.dispose();
}
