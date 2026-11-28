// v1.1 HOOLA CODE HELPERS: what the session's typing box offers while she writes, like Claude Code.
// - the context meter (how full the conversation is before Hoola sums it up; /compact frees it)
// - a question Hoola asks in the middle of its work, with choices and her own words
// - @ files (a list of matching files from the working copy) and / commands (Hoola's own + the repo's .claude/commands)
// - the repo's Claude Code setup (commands, agents, hooks, permission rules) as one sheet
// The server routes are /api/devsahayak/tasks/{id}/find, /commands and /permit; nothing here runs on its own.
import 'dart:async';

import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'code_claude.dart';
import 'code_home.dart' show codeModes;
import 'code_kit.dart';

String _taskBase(String id) => '/api/devsahayak/tasks/${Uri.encodeComponent(id)}';

// ---------------------------------------------------------------------------------------------- the repo's commands
/// What GET /tasks/{id}/commands said, kept per session (the repo's .claude/ does not change while she types).
class CodeCommands {
  static final Map<String, Map<String, dynamic>> _by = {};
  static final Map<String, Future<Map<String, dynamic>>> _loading = {};

  static Map<String, dynamic>? cached(String id) => _by[id];

  static Future<Map<String, dynamic>> of(Santosh app, String id, {bool fresh = false}) {
    if (!fresh && _by[id] != null) return Future.value(_by[id]!);
    final going = _loading[id];
    if (going != null) return going;
    final f = _fetch(app, id);
    _loading[id] = f;
    return f;
  }

  static Future<Map<String, dynamic>> _fetch(Santosh app, String id) async {
    final api = app.api;
    try {
      if (api == null) return const <String, dynamic>{};
      final r = cm(await api.call('GET', '${_taskBase(id)}/commands'));
      _by[id] = r;
      return r;
    } catch (_) {
      _by[id] = const <String, dynamic>{};   // not asked again while she types; the setup sheet asks afresh
      return const <String, dynamic>{};
    } finally {
      _loading.remove(id);
    }
  }
}

/// Hoola's own slash commands: (name, what it does). These are Claude Code's built-in commands as they work here; a
/// repo command of the same name is hidden (the built-in wins). The most used come first.
const List<(String, String)> codeOwnCommands = [
  ('help', 'Every command you can type here'),
  ('compact', 'Summarise the conversation (add what to keep)'),
  ('clear', 'Start a new session (this one stays in your list)'),
  ('review', 'Review the changes on this branch'),
  ('security-review', 'Review the changes for security problems'),
  ('ponytail', 'The smallest change that fully works: lite, full, ultra or off'),
  ('ponytail-review', 'Review this change like the senior dev who gets paged'),
  ('ponytail-audit', 'The same check for the whole repo, most important first'),
  ('ponytail-debt', 'List the shortcut: comments left for later'),
  ('brainstorm', 'Shape an idea with Hoola before any code'),
  ('write-plan', 'A step-by-step plan, each step with its check'),
  ('execute-plan', 'Carry out the approved plan task by task'),
  ('init', 'Write AGENTS.md'),
  ('status', 'Repo, branch, pull request, context and cost'),
  ('context', 'How full the conversation is'),
  ('cost', 'What this session has cost so far'),
  ('usage', 'Same as /cost'),
  ('model', 'Pick the quality Hoola works at'),
  ('todos', "Hoola's to-do list for this session"),
  ('rewind', 'Go back to an earlier checkpoint'),
  ('resume', 'Back to all your sessions'),
  ('bashes', 'Commands running in the background'),
  ('doctor', "Check this session's setup for problems"),
  ('pr-comments', "Reviewers' comments on the pull request"),
  ('agents', "The repo's agents and Claude Code files"),
  ('memory', 'Edit CLAUDE.md, the rules Hoola reads first'),
  ('hooks', 'Edit the hooks in .claude/settings.json'),
  ('permissions', 'Edit the permission rules in .claude/settings.json'),
  ('mcp', "The repo's MCP servers and setup"),
  ('plugins', 'Your plugins'),
  ('plugin', 'Same as /plugins'),
  ('style', 'Pick how Hoola writes to you'),
  ('output-style', 'Same as /style (add a style name)'),
  ('export', 'Share the conversation as a file'),
  ('config', 'Hoola Code settings'),
  ('add-dir', 'How to work with other repos'),
  ('login', 'Connect GitHub'),
  ('logout', 'Disconnect GitHub'),
  ('install-github-app', 'Connect the GitHub app'),
];

/// Claude Code commands that only make sense in a terminal. Typed here, Hoola says so instead of sending them.
const List<String> codeTerminalOnlyCommands = [
  'vim', 'terminal-setup', 'statusline', 'ide', 'exit', 'quit', 'upgrade', 'bug', 'release-notes', 'privacy-settings',
];

/// Every name the phone handles itself (a repo command with one of these names is never shown or sent).
final Set<String> codeBuiltinNames = {for (final x in codeOwnCommands) x.$1, ...codeTerminalOnlyCommands};

/// Own commands that go to Hoola as her message (the server knows them), not done on the phone.
const Set<String> codeSentToHoola = {
  'security-review', 'ponytail-review', 'ponytail-audit', 'ponytail-debt', 'brainstorm', 'write-plan', 'execute-plan'
};

// ---------------------------------------------------------------------------------------------- @ files and / commands
/// The list above the typing box while she types '@part' (files) or '/name' (commands). A tap puts the pick in the box.
class CodeAssistList extends StatefulWidget {
  const CodeAssistList({super.key, required this.app, required this.id, required this.controller, this.focus});
  final Santosh app;
  final String id;
  final TextEditingController controller;
  final FocusNode? focus;
  @override
  State<CodeAssistList> createState() => _CodeAssistListState();
}

class _CodeAssistListState extends State<CodeAssistList> {
  String _kind = '';                  // '' | 'file' | 'cmd'
  String _q = '';
  int _from = -1;                     // where the '@' word starts in the text
  List<String> _files = const [];
  bool _finding = false;
  String _asked = '\u0000';           // the file query the list now answers
  Timer? _wait;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_changed);
    widget.focus?.addListener(_changed);
  }

  @override
  void didUpdateWidget(CodeAssistList old) {
    super.didUpdateWidget(old);
    if (old.controller != widget.controller) {
      old.controller.removeListener(_changed);
      widget.controller.addListener(_changed);
    }
    if (old.focus != widget.focus) {
      old.focus?.removeListener(_changed);
      widget.focus?.addListener(_changed);
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_changed);
    widget.focus?.removeListener(_changed);
    _wait?.cancel();
    super.dispose();
  }

  /// What she is typing now: a '/name' at the very start, or an '@part' word ending at the cursor.
  (String, String, int) _token() {
    final text = widget.controller.text;
    if (widget.focus != null && !widget.focus!.hasFocus) return ('', '', -1);
    if (text.startsWith('/') && !text.contains(RegExp(r'\s'))) return ('cmd', text.substring(1).toLowerCase(), 0);
    var at = widget.controller.selection.baseOffset;
    if (at < 0 || at > text.length) at = text.length;
    var i = at;
    while (i > 0 && !RegExp(r'\s').hasMatch(text[i - 1])) {
      i--;
    }
    final word = text.substring(i, at);
    if (word.startsWith('@') && !word.substring(1).contains('@')) return ('file', word.substring(1), i);
    return ('', '', -1);
  }

  void _changed() {
    final (kind, q, from) = _token();
    if (kind == _kind && q == _q && from == _from) return;
    if (!mounted) return;
    setState(() {
      _kind = kind;
      _q = q;
      _from = from;
    });
    if (kind == 'file') {
      _wait?.cancel();
      _wait = Timer(const Duration(milliseconds: 250), () => _find(q));
    } else if (kind == 'cmd' && CodeCommands.cached(widget.id) == null) {
      CodeCommands.of(widget.app, widget.id).then((_) {
        if (mounted) setState(() {});
      });
    }
  }

  Future<void> _find(String q) async {
    final api = widget.app.api;
    if (api == null || !mounted) return;
    setState(() => _finding = true);
    var got = <String>[];
    try {
      final r = cm(await api.call('GET', '${_taskBase(widget.id)}/find', query: {'q': q}));
      got = [for (final f in (r['files'] as List?) ?? const []) cs(f)].where((e) => e.isNotEmpty).take(8).toList();
    } catch (_) {}
    if (!mounted) return;
    if (_kind != 'file' || _q != q) {
      setState(() => _finding = false);   // she typed on; the next look answers
      return;
    }
    setState(() {
      _finding = false;
      _files = got;
      _asked = q;
    });
  }

  void _pickFile(String path) {
    final text = widget.controller.text;
    var end = widget.controller.selection.baseOffset;
    if (end < 0 || end > text.length) end = text.length;
    final from = _from < 0 || _from > end ? end : _from;
    final put = '@$path ';
    final next = text.replaceRange(from, end, put);
    widget.controller.value = TextEditingValue(text: next, selection: TextSelection.collapsed(offset: from + put.length));
    widget.focus?.requestFocus();
  }

  void _pickCmd(String name) {
    final put = '/$name ';
    widget.controller.value = TextEditingValue(text: put, selection: TextSelection.collapsed(offset: put.length));
    widget.focus?.requestFocus();
  }

  Widget _row(HoolaColors c, {required IconData icon, required String main, String sub = '', bool mono = false, required VoidCallback onTap}) =>
      Semantics(
        button: true,
        label: sub.isEmpty ? main : '$main, $sub',
        excludeSemantics: true,
        child: InkWell(
          onTap: onTap,
          child: Container(
            constraints: const BoxConstraints(minHeight: 48),
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Row(children: [
              Icon(icon, size: 18, color: c.ink3),
              const SizedBox(width: 10),
              Flexible(
                child: Text(main,
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: mono ? codeMono(c, size: 13.5) : codeSans(c, size: 14.5, weight: FontWeight.w500)),
              ),
              if (sub.isNotEmpty) ...[
                const SizedBox(width: 8),
                Expanded(child: Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 13, color: c.ink3))),
              ],
            ]),
          ),
        ),
      );

  List<Widget> _cmdRows(HoolaColors c) {
    final repo = cl(CodeCommands.cached(widget.id)?['commands']);
    final own = codeBuiltinNames;
    final rows = <Widget>[];
    for (final (name, what) in codeOwnCommands) {
      if (!name.startsWith(_q)) continue;
      rows.add(_row(c, icon: Icons.bolt_rounded, main: '/$name', sub: what, mono: true, onTap: () => _pickCmd(name)));
    }
    for (final x in repo) {
      final name = cs(x['name']).replaceFirst(RegExp(r'^/'), '');
      if (name.isEmpty || own.contains(name.toLowerCase()) || !name.toLowerCase().startsWith(_q)) continue;
      final hint = cs(x['hint']);
      final what = cs(x['description']);
      rows.add(_row(c,
          icon: Icons.terminal_rounded,
          main: '/$name',
          sub: [what, if (hint.isNotEmpty) hint].where((e) => e.isNotEmpty).join(' · '),
          mono: true,
          onTap: () => _pickCmd(name)));
    }
    return rows.take(12).toList();
  }

  @override
  Widget build(BuildContext context) {
    if (_kind.isEmpty) return const SizedBox.shrink();
    final c = HoolaColors.of(context);
    final List<Widget> rows;
    if (_kind == 'cmd') {
      rows = _cmdRows(c);
      if (rows.isEmpty) return const SizedBox.shrink();
    } else {
      final fresh = _asked == _q;
      rows = [
        if (fresh)
          for (final f in _files) _row(c, icon: Icons.description_outlined, main: f, mono: true, onTap: () => _pickFile(f)),
        if (!fresh || _finding)
          Container(
            constraints: const BoxConstraints(minHeight: 48),
            padding: const EdgeInsets.symmetric(horizontal: 14),
            alignment: Alignment.centerLeft,
            child: Row(children: [
              const CodeRing(size: 14),
              const SizedBox(width: 10),
              Text('Looking for files…', style: codeSans(c, size: 13.5, color: c.ink3)),
            ]),
          )
        else if (_files.isEmpty)
          Container(
            constraints: const BoxConstraints(minHeight: 48),
            padding: const EdgeInsets.symmetric(horizontal: 14),
            alignment: Alignment.centerLeft,
            child: Text(_q.isEmpty ? 'Type part of a file name' : 'No file matches “$_q”', style: codeSans(c, size: 13.5, color: c.ink3)),
          ),
      ];
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(2, 0, 2, 8),
      child: Container(
        constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * .36),
        decoration: BoxDecoration(
          color: c.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: c.line),
        ),
        clipBehavior: Clip.antiAlias,
        child: Material(
          type: MaterialType.transparency,
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: rows),
          ),
        ),
      ),
    );
  }
}

/// Puts '@' at the cursor (a space before it when needed) so the file list opens.
void codeInsertAt(TextEditingController box, FocusNode? focus) {
  final text = box.text;
  var at = box.selection.baseOffset;
  if (at < 0 || at > text.length) at = text.length;
  final gap = at > 0 && !RegExp(r'\s').hasMatch(text[at - 1]) ? ' ' : '';
  final put = '$gap@';
  box.value = TextEditingValue(text: text.replaceRange(at, at, put), selection: TextSelection.collapsed(offset: at + put.length));
  focus?.requestFocus();
}

// ---------------------------------------------------------------------------------------------- the context meter
/// "Context 62% used" with a small ring; a tap explains it and offers Compact now.
class CodeContextMeter extends StatelessWidget {
  const CodeContextMeter({super.key, required this.app, required this.ctx, required this.onCompact, this.running = false});
  final Santosh app;
  final int ctx;                      // 0-100
  final VoidCallback onCompact;
  final bool running;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final v = ctx.clamp(0, 100);
    final full = v >= 80;
    final ink = full ? c.warn : c.ink3;
    final words = 'Context $v% used${full ? ' · /compact to free it' : ''}';
    return Semantics(
      button: true,
      label: '$words. What this means',
      excludeSemantics: true,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _explain(context, v),
        child: Container(
          constraints: const BoxConstraints(minHeight: 48),
          padding: const EdgeInsets.symmetric(horizontal: 6),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(value: v / 100, strokeWidth: 2.4, color: full ? c.warn : c.ink2, backgroundColor: c.line),
            ),
            const SizedBox(width: 8),
            Flexible(
              child: Text(words,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: codeSans(c, size: 12.5, color: ink, weight: full ? FontWeight.w600 : FontWeight.w400)
                      .copyWith(fontFeatures: const [FontFeature.tabularFigures()])),
            ),
          ]),
        ),
      ),
    );
  }

  Future<void> _explain(BuildContext context, int v) => showCodeContextExplain(context, app, v, running: running, onCompact: onCompact);
}

/// What the context meter means, with Compact now (also typed as /context).
Future<void> showCodeContextExplain(BuildContext context, Santosh app, int v, {required bool running, required VoidCallback onCompact}) async {
  final go = await codeSheet<bool>(context, app,
      title: 'Context $v% used',
      body: (ctx) {
        final c = HoolaColors.of(ctx);
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(
              'This is how full the conversation is that Hoola keeps in mind for this session. When it is full, '
              'Hoola sums up the older part by itself and carries on from the summary.',
              style: codeSans(c, size: 14.5, color: c.ink2)),
          const SizedBox(height: 10),
          Text('Compact now does it at once: the earlier steps become a short summary and the space is free again. '
              'Your changes and the pull request stay as they are.',
              style: codeSans(c, size: 14.5, color: c.ink2)),
          if (running) ...[
            const SizedBox(height: 10),
            Text('Hoola is working. You can compact once it finishes.', style: codeSans(c, size: 13.5, color: c.warn)),
          ],
          const SizedBox(height: 16),
          Row(children: [
            Expanded(child: CodeOutline('Close', onTap: () => Navigator.pop(ctx, false))),
            const SizedBox(width: 10),
            Expanded(
                flex: 2,
                child: CodeMain('Compact now', icon: Icons.compress_rounded, onTap: running ? null : () => Navigator.pop(ctx, true))),
          ]),
        ]);
      });
  if (go == true) onCompact();
}

// ---------------------------------------------------------------------------------------------- a question mid-work
/// Hoola stopped to ask her something: the question, one button per choice, and a field for her own words.
class CodeQuestionCard extends StatefulWidget {
  const CodeQuestionCard({super.key, required this.ask, required this.busy, required this.onAnswer});
  final Map<String, dynamic> ask;
  final bool busy;
  final ValueChanged<String> onAnswer;
  @override
  State<CodeQuestionCard> createState() => _CodeQuestionCardState();
}

class _CodeQuestionCardState extends State<CodeQuestionCard> {
  final _box = TextEditingController();

  @override
  void initState() {
    super.initState();
    _box.addListener(_redraw);
  }

  void _redraw() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _box.removeListener(_redraw);
    _box.dispose();
    super.dispose();
  }

  void _send() {
    final words = _box.text.trim();
    if (words.isEmpty || widget.busy) return;
    widget.onAnswer(words);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final question = cs(widget.ask['what']).trim().isNotEmpty ? cs(widget.ask['what']).trim() : 'Hoola has a question for you.';
    final choices = [for (final x in (widget.ask['choices'] as List?) ?? const []) cs(x).trim()].where((e) => e.isNotEmpty).take(4).toList();
    final has = _box.text.trim().isNotEmpty;
    return Container(
      decoration: BoxDecoration(
        color: Color.alphaBlend(c.accent.withOpacity(0.03), c.surface),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: c.accent, width: 2),
      ),
      clipBehavior: Clip.antiAlias,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
          Row(children: [
            Icon(Icons.help_outline_rounded, size: 18, color: c.accent),
            const SizedBox(width: 8),
            Text('Hoola asks', style: codeSans(c, size: 13, weight: FontWeight.w600, color: c.accent)),
          ]),
          const SizedBox(height: 8),
          Semantics(liveRegion: true, child: Text(question, style: codeSans(c, size: 15.5, weight: FontWeight.w500, height: 1.45))),
          const SizedBox(height: 12),
          for (final ch in choices)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: CodeOutline(ch, height: 48, onTap: widget.busy ? null : () => widget.onAnswer(ch)),
            ),
          if (choices.isNotEmpty) const SizedBox(height: 4),
          Container(
            decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(24), border: Border.all(color: c.line)),
            padding: const EdgeInsets.only(left: 14, right: 4),
            child: Row(children: [
              Expanded(
                child: TextField(
                  controller: _box,
                  minLines: 1,
                  maxLines: 4,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _send(),
                  style: codeSans(c, size: 15, height: 1.4),
                  cursorColor: c.accent,
                  decoration: codeBareInput(c, hint: choices.isEmpty ? 'Type your answer' : 'Or type your answer', size: 15),
                ),
              ),
              Semantics(
                button: true,
                label: has ? 'Send your answer' : 'Send your answer (type something first)',
                excludeSemantics: true,
                child: InkResponse(
                  onTap: has && !widget.busy ? _send : null,
                  radius: 24,
                  child: SizedBox(
                    width: 48,
                    height: 48,
                    child: Center(
                      child: Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(color: has && !widget.busy ? c.pill : c.navOn, shape: BoxShape.circle),
                        child: widget.busy
                            ? Center(child: SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill)))
                            : Icon(Icons.arrow_upward_rounded, size: 19, color: has ? c.onPill : c.ink3),
                      ),
                    ),
                  ),
                ),
              ),
            ]),
          ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------------------------------------- the repo's setup
int _count(dynamic v) => v is List ? v.length : (v is Map ? v.length : ci(v));

String _toolsLevel(Map<String, dynamic> a) {
  final t = a['tools'];
  if (t is List) return t.isEmpty ? 'no tools' : t.map(cs).join(', ');
  for (final k in const ['tools', 'level', 'access']) {
    if (cs(a[k]).isNotEmpty) return cs(a[k]);
  }
  return '';
}

/// The repo's .claude/ as Hoola reads it: its commands, agents, skills, MCP servers, hooks, permission rules, starting
/// mode, variables and her plugins (GET /tasks/{id}/commands), with ways to edit the files and the plugins.
Future<void> showCodeRepoSetup(BuildContext context, Santosh app, String id) async {
  final r = await CodeCommands.of(app, id, fresh: true);
  if (!context.mounted) return;
  final cmds = cl(r['commands']);
  final agents = [for (final a in (r['agents'] as List?) ?? const []) a is Map ? Map<String, dynamic>.from(a) : <String, dynamic>{'name': cs(a)}];
  final hooks = <String>[];
  for (final h in (r['hooks'] as List?) ?? const []) {
    final e = h is Map ? cs(h['event']) : cs(h);
    if (e.isNotEmpty && !hooks.contains(e)) hooks.add(e);
  }
  final rules = cm(r['rules']);
  final allow = _count(rules['allow']), ask = _count(rules['ask']), deny = _count(rules['deny']);
  final skills = cl(r['skills']);
  final mcp = cl(r['mcp']);
  final env = [for (final e in (r['env'] as List?) ?? const []) cs(e)].where((e) => e.isNotEmpty).toList();
  final mode = cs(r['mode']);
  final modeLabel = mode.isEmpty ? '' : codeModes.firstWhere((x) => x.$1 == mode, orElse: () => (mode, mode, '')).$2;
  final plugins = cl(r['plugins']);
  final style = cs(r['style']);
  final none = cmds.isEmpty && agents.isEmpty && hooks.isEmpty && allow + ask + deny == 0 && skills.isEmpty && mcp.isEmpty && env.isEmpty &&
      mode.isEmpty;
  final pick = await codeSheet<String>(context, app,
      title: "This repo's Claude Code setup",
      body: (ctx) {
        final c = HoolaColors.of(ctx);
        Widget item(String main, String sub, {bool mono = true, Color? subColor}) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(main, style: mono ? codeMono(c, size: 13.5) : codeSans(c, size: 14.5, weight: FontWeight.w500)),
                if (sub.isNotEmpty) Text(sub, style: codeSans(c, size: 13, color: subColor ?? c.ink3, height: 1.35)),
              ]),
            );
        String from(Map<String, dynamic> x) {
          final o = cs(x['origin']);
          return o.isEmpty || o == 'repo' ? '' : codeOriginWords(o);
        }

        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Hoola follows .claude/ in this repo and your plugins: commands, agents, skills, MCP servers, hooks and permission '
              'rules. Hooks run in the locked box.',
              style: codeSans(c, size: 14, color: c.ink2)),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: CodeOutline('Edit the files', icon: Icons.edit_outlined, height: 48, onTap: () => Navigator.pop(ctx, 'files'))),
            const SizedBox(width: 10),
            Expanded(child: CodeOutline('Plugins', icon: Icons.extension_rounded, height: 48, onTap: () => Navigator.pop(ctx, 'plugins'))),
          ]),
          if (none)
            Padding(
              padding: const EdgeInsets.only(top: 16, bottom: 8),
              child: Text('This repo has no Claude Code setup yet. Tap Edit the files to add commands, agents, skills or settings.',
                  style: codeSans(c, size: 14, color: c.ink3)),
            ),
          if (mode.isNotEmpty) ...[
            const CodeSection('Starting mode'),
            item(modeLabel, 'From .claude/settings.json', mono: false),
          ],
          if (style.isNotEmpty && style != 'default') ...[
            const CodeSection('Output style'),
            item(style, ''),
          ],
          if (cmds.isNotEmpty) ...[
            CodeSection('Commands · ${cmds.length}'),
            for (final x in cmds)
              item('/${cs(x['name']).replaceFirst(RegExp(r'^/'), '')}${cs(x['hint']).isEmpty ? '' : ' ${cs(x['hint'])}'}',
                  [cs(x['description']), from(x)].where((e) => e.isNotEmpty).join(' · ')),
          ],
          if (agents.isNotEmpty) ...[
            CodeSection('Agents · ${agents.length}'),
            for (final a in agents)
              item(cs(a['name']), [cs(a['description']), _toolsLevel(a), if (cs(a['model']).isNotEmpty && cs(a['model']) != 'inherit') 'model ${cs(a['model'])}', from(a)].where((e) => e.isNotEmpty).join(' · '), mono: false),
          ],
          if (skills.isNotEmpty) ...[
            CodeSection('Skills · ${skills.length}'),
            for (final x in skills) item(cs(x['name']), [cs(x['description']), from(x)].where((e) => e.isNotEmpty).join(' · '), mono: false),
          ],
          if (mcp.isNotEmpty) ...[
            CodeSection('MCP servers · ${mcp.length}'),
            for (final x in mcp)
              item(cs(x['name']), x['ok'] == true
                      ? (cs(x['kind']) == 'stdio' ? 'Runs in the locked box${cs(x['program']).isEmpty ? '' : ' · ${cs(x['program'])}'}' : 'Online')
                      : (cs(x['why']).isEmpty ? 'Not reachable' : cs(x['why'])),
                  subColor: x['ok'] == true ? c.ok : c.warn),
          ],
          if (hooks.isNotEmpty) ...[
            CodeSection('Hooks · ${hooks.length}'),
            for (final h in hooks) item(h, ''),
          ],
          if (allow + ask + deny > 0) ...[
            const CodeSection('Permission rules'),
            Text('$allow allowed, $ask ${ask == 1 ? 'asks' : 'ask'} first, $deny denied', style: codeSans(c, size: 14.5)),
          ],
          if (env.isNotEmpty) ...[
            CodeSection('Variables · ${env.length}'),
            Text(env.join(', '), style: codeMono(c, size: 13, color: c.ink2)),
            Text('Only the names are shown here.', style: codeSans(c, size: 12.5, color: c.ink3)),
          ],
          CodeSection('Your plugins · ${plugins.length}'),
          if (plugins.isEmpty)
            Text('No plugins yet. Tap Plugins to add one from a GitHub link.', style: codeSans(c, size: 14, color: c.ink3))
          else
            for (final p in plugins)
              item(cs(p['name']), [p['enabled'] == true ? 'On' : 'Off', cs(p['description'])].where((e) => e.isNotEmpty).join(' · '),
                  mono: false),
          const SizedBox(height: 12),
        ]);
      });
  if (!context.mounted) return;
  if (pick == 'files') {
    await openCodeClaudeFiles(context, app, id);
  } else if (pick == 'plugins') {
    await showCodePlugins(context, app, id: id);
  }
}
