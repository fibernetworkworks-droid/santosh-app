// v0.999 HOOLA CODE CLAUDE FILES (the phone side of /export, /style, /plugins and editing the repo's Claude Code files,
// like Claude Code's /agents /hooks /permissions screens).
// - Export the conversation: GET /tasks/{id}/export (Markdown) handed to the share sheet, or copied when there is none
// - Output style: GET /tasks/{id}/commands (styles + style), PUT /tasks/{id}/style
// - The repo's Claude Code files: GET / PUT /tasks/{id}/claude-file (an empty file deletes it; the server checks the
//   path, the JSON and keeps keys and passwords out)
// - Her plugins: GET / POST /plugins, PATCH / DELETE /plugins/{name}
// Every change is her tap; a change to a file lands in the session's working copy and rides in its pull request.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import '../../native.dart';
import '../../state.dart';
import '../hoola_theme.dart';
import 'code_assist.dart';
import 'code_kit.dart';

String _tBase(String id) => '/api/devsahayak/tasks/${Uri.encodeComponent(id)}';
const String _pBase = '/api/devsahayak/plugins';

/// One call; (the answer, '') or (null, the server's own words).
Future<(Map<String, dynamic>?, String)> _ask(Santosh app, String method, String path,
    {Object? body, Map<String, String>? query}) async {
  final api = app.api;
  if (api == null) return (null, 'Not connected to Hoola.');
  try {
    final r = await api.call(method, path, body: body, query: query, timeout: const Duration(minutes: 2));
    return (r is Map ? Map<String, dynamic>.from(r) : <String, dynamic>{}, '');
  } catch (e) {
    final w = '$e'.replaceFirst('Exception: ', '').trim();
    return (null, w.isEmpty ? codeLoadFailedLine : w);
  }
}

/// Where a style, skill or command came from, in plain words.
String codeOriginWords(String origin) {
  final o = origin.trim();
  if (o.isEmpty || o == 'hoola') return 'Built in';
  if (o == 'repo') return 'This repo';
  if (o.startsWith('plugin ')) return 'Plugin ${o.substring(7)}';
  return o;
}

Future<T?> _push<T>(BuildContext context, Santosh app, Widget page) => Navigator.of(context)
    .push<T>(MaterialPageRoute<T>(builder: (_) => HoolaTheme(appearance: app.appearance, child: page)));

// ---------------------------------------------------------------------------------------------- export
/// The whole conversation as a Markdown file, handed to the share sheet (no share sheet = copied).
Future<void> codeExportConversation(BuildContext context, Santosh app, String id) async {
  final api = app.api;
  if (api == null) return;
  codeToast(context, 'Getting the conversation…');
  var text = '';
  var name = 'hoola-code-session.md';
  final client = http.Client();
  try {
    final b = api.baseUrl.endsWith('/') ? api.baseUrl.substring(0, api.baseUrl.length - 1) : api.baseUrl;
    final req = http.Request('GET', Uri.parse('$b${_tBase(id)}/export'));
    if (api.apiKey.isNotEmpty) req.headers['Authorization'] = 'Bearer ${api.apiKey}';
    final res = await http.Response.fromStream(await client.send(req).timeout(const Duration(seconds: 60)));
    final body = utf8.decode(res.bodyBytes, allowMalformed: true);
    if (res.statusCode >= 400) {
      var msg = 'Could not export the conversation.';
      try {
        msg = (jsonDecode(body) as Map)['detail']?.toString() ?? msg;
      } catch (_) {}
      if (context.mounted) codeToast(context, msg);
      return;
    }
    text = body;
    final cd = res.headers['content-disposition'] ?? '';
    final m = RegExp(r'filename="?([^";]+)"?', caseSensitive: false).firstMatch(cd);
    if (m != null) {
      final n = m.group(1)!.trim().replaceAll(RegExp(r'[^\w.-]+'), '-');
      if (n.isNotEmpty) name = n.endsWith('.md') ? n : '$n.md';
    }
  } catch (_) {
    if (context.mounted) codeToast(context, 'Could not export the conversation. Check your connection.');
    return;
  } finally {
    client.close();
  }
  if (text.trim().isEmpty) {
    if (context.mounted) codeToast(context, 'There is nothing to export yet.');
    return;
  }
  String? err;
  try {
    final dir = await getTemporaryDirectory();
    final f = File('${dir.path}/$name');
    await f.writeAsString(text);
    err = await Native.shareFile(f.path, mime: 'text/markdown', title: 'Share the conversation');
  } catch (_) {
    err = 'no share sheet';
  }
  if (err != null) {
    await Clipboard.setData(ClipboardData(text: text));
    if (context.mounted) codeToast(context, 'Copied the conversation');
  }
}

// ---------------------------------------------------------------------------------------------- output style
/// How Hoola writes in this session: the built-in styles and the repo's own (.claude/output-styles).
/// [name] (typed as "/output-style NAME") picks that style at once when it exists; otherwise the list opens.
Future<void> showCodeStylePicker(BuildContext context, Santosh app, String id, {String name = ''}) async {
  final r = await CodeCommands.of(app, id, fresh: true);
  if (!context.mounted) return;
  final styles = cl(r['styles']);
  final now = cs(r['style']).isEmpty ? 'default' : cs(r['style']);
  if (styles.isEmpty) {
    codeToast(context, 'Output styles show once this session has its working copy.');
    return;
  }
  final want = name.trim().toLowerCase();
  final named = want.isEmpty ? '' : cs(styles.firstWhere((s) => cs(s['name']).toLowerCase() == want, orElse: () => const <String, dynamic>{})['name']);
  if (want.isNotEmpty && named.isEmpty) codeToast(context, 'No output style called "${name.trim()}". Pick one from the list.');
  final pick = named.isNotEmpty ? named : await codeSheet<String>(context, app,
      title: 'Output style',
      body: (ctx) {
        final c = HoolaColors.of(ctx);
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('How Hoola writes to you in this session. The work itself is the same.', style: codeSans(c, size: 14, color: c.ink2)),
          const SizedBox(height: 12),
          for (final s in styles)
            CodeChoiceRow(
              label: cs(s['name']),
              sub: [cs(s['description']), codeOriginWords(cs(s['origin']))].where((e) => e.isNotEmpty).join(' · '),
              on: cs(s['name']) == now,
              onTap: () => Navigator.pop(ctx, cs(s['name'])),
            ),
          Text('Add your own in .claude/output-styles - Edit the files, then Add.', style: codeSans(c, size: 13, color: c.ink3)),
        ]);
      });
  if (named.isNotEmpty && named == now) {
    codeToast(context, 'The output style is already $now.');
    return;
  }
  if (pick == null || pick == now || !context.mounted) return;
  final (got, why) = await _ask(app, 'PUT', '${_tBase(id)}/style', body: {'style': pick});
  if (!context.mounted) return;
  if (got == null) {
    codeToast(context, why);
    return;
  }
  CodeCommands.of(app, id, fresh: true);
  codeToast(context, 'Output style: ${cs(got['style']).isEmpty ? pick : cs(got['style'])}');
}

/// v0.999 /ponytail [lite|full|ultra|off]: Ponytail's level for this session (no word = switch on, or say which).
Future<void> codeSetPonytail(BuildContext context, Santosh app, String id, String level) async {
  final (got, why) = await _ask(app, 'PUT', '${_tBase(id)}/ponytail', body: {'level': level.trim().toLowerCase()});
  if (!context.mounted) return;
  if (got == null) {
    codeToast(context, why);
    return;
  }
  codeToast(context, cs(got['said']).isEmpty ? 'Ponytail: ${cs(got['ponytail'])}' : cs(got['said']));
}

// ---------------------------------------------------------------------------------------------- plugins
/// Her plugins (from GitHub): turn on / off, remove, add from a link. [id] = the session whose setup to refresh.
Future<void> showCodePlugins(BuildContext context, Santosh app, {String? id}) async {
  await codeSheet<void>(context, app, title: 'Your plugins', body: (ctx) => _PluginsBody(app: app));
  if (id != null) CodeCommands.of(app, id, fresh: true);
}

class _PluginsBody extends StatefulWidget {
  const _PluginsBody({required this.app});
  final Santosh app;
  @override
  State<_PluginsBody> createState() => _PluginsBodyState();
}

class _PluginsBodyState extends State<_PluginsBody> {
  final _link = TextEditingController();
  List<Map<String, dynamic>> _list = const [];
  bool _loading = true, _adding = false;
  String _busy = '';                  // the plugin being changed
  String _error = '';

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  @override
  void dispose() {
    _link.dispose();
    super.dispose();
  }

  Future<void> _fetch() async {
    final (got, why) = await _ask(widget.app, 'GET', _pBase);
    if (!mounted) return;
    setState(() {
      _loading = false;
      if (got != null) {
        _list = cl(got['plugins']);
        _error = '';
      } else {
        _error = why;
      }
    });
  }

  void _took(Map<String, dynamic>? got, String why) {
    if (!mounted) return;
    setState(() {
      _busy = '';
      _adding = false;
      if (got != null) {
        _list = cl(got['plugins']);
        _error = '';
      } else {
        _error = why;
      }
    });
  }

  Future<void> _add() async {
    final url = _link.text.trim();
    if (url.isEmpty || _adding) return;
    if (!url.startsWith('https://github.com/')) {
      setState(() => _error = 'Paste a GitHub link like https://github.com/owner/repo');
      return;
    }
    setState(() {
      _adding = true;
      _error = '';
    });
    final (got, why) = await _ask(widget.app, 'POST', _pBase, body: {'url': url});
    if (got != null) _link.clear();
    _took(got, why);
  }

  Future<void> _turn(String name, bool on) async {
    if (_busy.isNotEmpty) return;
    setState(() => _busy = name);
    final (got, why) = await _ask(widget.app, 'PATCH', '$_pBase/${Uri.encodeComponent(name)}', body: {'enabled': on});
    _took(got, why);
  }

  Future<void> _remove(String name) async {
    if (_busy.isNotEmpty) return;
    final yes = await codeSheet<bool>(context, widget.app,
        title: 'Remove $name?',
        body: (ctx) {
          final c = HoolaColors.of(ctx);
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Its commands, agents, skills, hooks and MCP servers leave every session of yours. You can add it again from its link.',
                style: codeSans(c, size: 14.5, color: c.ink2)),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: CodeOutline('Keep it', onTap: () => Navigator.pop(ctx, false))),
              const SizedBox(width: 10),
              Expanded(child: CodeOutline('Remove', color: c.bad, icon: Icons.delete_outline_rounded, onTap: () => Navigator.pop(ctx, true))),
            ]),
          ]);
        });
    if (yes != true || !mounted) return;
    setState(() => _busy = name);
    final (got, why) = await _ask(widget.app, 'DELETE', '$_pBase/${Uri.encodeComponent(name)}');
    _took(got, why);
  }

  static String _has(Map<String, dynamic> p) {
    final h = cm(p['has']);
    final parts = <String>[
      if (ci(h['commands']) > 0) cPlural(ci(h['commands']), 'command'),
      if (ci(h['agents']) > 0) cPlural(ci(h['agents']), 'agent'),
      if (ci(h['skills']) > 0) cPlural(ci(h['skills']), 'skill'),
      if (ci(h['hooks']) > 0) 'hooks',
      if (ci(h['mcp']) > 0) 'MCP servers',
    ];
    return parts.join(', ');
  }

  Widget _plugin(HoolaColors c, Map<String, dynamic> p) {
    final name = cs(p['name']);
    final on = p['enabled'] == true;
    final busy = _busy == name;
    final has = _has(p);
    final ver = cs(p['version']);
    final desc = cs(p['description']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: CodeCard(
        padding: const EdgeInsets.fromLTRB(0, 2, 0, 10),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          CodeSwitchRow(
            label: ver.isEmpty ? name : '$name · $ver',
            sub: on ? 'On in every session' : 'Off',
            value: on,
            last: true,
            onChanged: busy || _busy.isNotEmpty ? null : (v) => _turn(name, v),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              if (desc.isNotEmpty) Text(desc, style: codeSans(c, size: 13.5, color: c.ink2, height: 1.4)),
              if (has.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text('Adds $has', style: codeSans(c, size: 13, color: c.ink3)),
              ],
              if (cs(p['url']).isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(cs(p['url']), maxLines: 1, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 12, color: c.ink3)),
              ],
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: busy
                    ? const Padding(padding: EdgeInsets.all(14), child: CodeRing(size: 16))
                    : CodeOutline('Remove', height: 48, color: c.bad, icon: Icons.delete_outline_rounded,
                        onTap: _busy.isNotEmpty ? null : () => _remove(name)),
              ),
            ]),
          ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('A plugin adds commands, agents, skills, hooks and MCP servers to every session of yours. '
          'Add only plugins from people you trust: their hooks run in the locked box.',
          style: codeSans(c, size: 14, color: c.ink2)),
      const SizedBox(height: 14),
      CodeField(controller: _link, label: 'Add a plugin from GitHub', hint: 'https://github.com/owner/repo', mono: true),
      CodeMain('Add', icon: Icons.add_rounded, busy: _adding, onTap: _adding ? null : _add),
      if (_error.isNotEmpty)
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Semantics(liveRegion: true, child: Text(_error, style: codeSans(c, size: 13.5, color: c.bad))),
        ),
      CodeSection(_loading ? 'Added plugins' : 'Added plugins · ${_list.length}'),
      if (_loading)
        const Padding(padding: EdgeInsets.all(16), child: Center(child: CodeRing(size: 18)))
      else if (_list.isEmpty)
        Text('No plugins yet.', style: codeSans(c, size: 14, color: c.ink3))
      else
        for (final p in _list) _plugin(c, p),
      const SizedBox(height: 8),
    ]);
  }
}

// ---------------------------------------------------------------------------------------------- the Claude Code files
/// What a Claude Code file of the repo is for, in plain words.
String codeClaudeFileWords(String path) {
  if (path == 'CLAUDE.md') return 'Rules Hoola reads first';
  if (path == 'CLAUDE.local.md') return 'Your own notes for this repo';
  if (path == 'AGENTS.md') return 'Rules for any coding agent';
  if (path == '.mcp.json') return 'MCP servers';
  if (path == '.claude/settings.json') return 'Permissions, hooks, variables and the starting mode';
  if (path == '.claude/settings.local.json') return 'Your own settings, not shared';
  if (path.startsWith('.claude/commands/')) return 'A slash command';
  if (path.startsWith('.claude/agents/')) return 'An agent';
  if (path.startsWith('.claude/output-styles/')) return 'An output style';
  if (path.startsWith('.claude/skills/')) return 'A skill';
  return '';
}

IconData _fileIcon(String path) {
  if (path.endsWith('.json')) return Icons.settings_outlined;
  if (path.startsWith('.claude/commands/')) return Icons.terminal_rounded;
  if (path.startsWith('.claude/agents/')) return Icons.groups_outlined;
  if (path.startsWith('.claude/skills/')) return Icons.menu_book_outlined;
  if (path.startsWith('.claude/output-styles/')) return Icons.edit_note_rounded;
  return Icons.description_outlined;
}

/// (id, label, path with NAME, what it is) - the files Add can start.
const List<(String, String, String, String)> _templates = [
  ('agent', 'An agent', '.claude/agents/NAME.md', 'A helper Hoola can hand part of the work to'),
  ('command', 'A slash command', '.claude/commands/NAME.md', 'Typed as /NAME in the typing box'),
  ('skill', 'A skill', '.claude/skills/NAME/SKILL.md', 'Steps Hoola follows for one kind of job'),
  ('style', 'An output style', '.claude/output-styles/NAME.md', 'How Hoola writes to you'),
  ('settings', 'settings.json', '.claude/settings.json', 'Permissions, hooks, variables, mode'),
  ('mcp', '.mcp.json', '.mcp.json', 'MCP servers for this repo'),
  ('claude', 'CLAUDE.md', 'CLAUDE.md', 'Rules Hoola reads first'),
];

String _starter(String id, String name) {
  switch (id) {
    case 'agent':
      return '---\nname: $name\ndescription: When Hoola should hand work to this agent\ntools: Read, Grep, Glob\n---\n\n'
          'You are $name. Say what this agent does, step by step.\n';
    case 'command':
      return '---\ndescription: What this command does\nargument-hint: [what to pass]\n---\n\n'
          'Do this for \$ARGUMENTS:\n1. \n2. \n';
    case 'skill':
      return '---\nname: $name\ndescription: When to use this skill\n---\n\n# $name\n\nSteps to follow when this skill is used:\n1. \n';
    case 'style':
      return '---\nname: $name\ndescription: How the replies should read\n---\n\nWrite every reply like this:\n- \n';
    case 'settings':
      return '{\n  "permissions": {\n    "allow": [],\n    "ask": [],\n    "deny": []\n  },\n  "env": {}\n}\n';
    case 'mcp':
      return '{\n  "mcpServers": {}\n}\n';
    default:
      return '# Project rules\n\n- How to build:\n- How to run the tests:\n- Rules for every change:\n';
  }
}

/// Opens the list of the repo's Claude Code files.
Future<void> openCodeClaudeFiles(BuildContext context, Santosh app, String id) =>
    _push<void>(context, app, CodeClaudeFilesPage(app: app, id: id));

/// Opens one Claude Code file of the repo in the editor (typed as /memory, /hooks, /permissions). A file the working copy
/// does not have yet starts from [starter]; Save writes it into this session's working copy like any other change.
Future<void> openCodeClaudeFile(BuildContext context, Santosh app, String id, String path, String starter) async {
  final r = await CodeCommands.of(app, id, fresh: true);
  if (!context.mounted) return;
  final has = [for (final f in (r['files'] as List?) ?? const []) cs(f)].contains(path);
  final what = await _push<String>(context, app, CodeClaudeFileEditor(app: app, id: id, path: path, starter: has ? null : starter));
  if (!context.mounted || what == null) return;
  codeToast(context, what == 'deleted' ? 'Deleted $path' : 'Saved $path');
  CodeCommands.of(app, id, fresh: true);
}

class CodeClaudeFilesPage extends StatefulWidget {
  const CodeClaudeFilesPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<CodeClaudeFilesPage> createState() => _CodeClaudeFilesPageState();
}

class _CodeClaudeFilesPageState extends State<CodeClaudeFilesPage> {
  List<String> _files = const [];
  bool _loading = true, _failed = false;

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    final (got, _) = await _ask(widget.app, 'GET', '${_tBase(widget.id)}/commands');
    if (!mounted) return;
    setState(() {
      _loading = false;
      _failed = got == null;
      if (got != null) _files = [for (final f in (got['files'] as List?) ?? const []) cs(f)].where((e) => e.isNotEmpty).toList();
    });
    CodeCommands.of(widget.app, widget.id, fresh: true);
  }

  void _reload() {
    setState(() {
      _loading = true;
      _failed = false;
    });
    _fetch();
  }

  Future<void> _open(String path, {String? starter}) async {
    final what = await _push<String>(context, widget.app,
        CodeClaudeFileEditor(app: widget.app, id: widget.id, path: path, starter: starter));
    if (!mounted || what == null) return;
    codeToast(context, what == 'deleted' ? 'Deleted $path' : 'Saved $path');
    _reload();
  }

  Future<void> _add() async {
    final pick = await codeSheet<String>(context, widget.app,
        title: 'Add a file',
        body: (ctx) {
          final c = HoolaColors.of(ctx);
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            for (final (id, label, path, sub) in _templates)
              InkWell(
                onTap: () => Navigator.pop(ctx, id),
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  constraints: const BoxConstraints(minHeight: 56),
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
                  child: Row(children: [
                    Icon(_fileIcon(path), size: 21, color: c.ink2),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(label, style: codeSans(c, size: 15, weight: FontWeight.w500)),
                        Text(sub, style: codeSans(c, size: 13, color: c.ink3, height: 1.35)),
                      ]),
                    ),
                  ]),
                ),
              ),
          ]);
        });
    if (pick == null || !mounted) return;
    final t = _templates.firstWhere((x) => x.$1 == pick);
    var path = t.$3;
    var name = '';
    if (path.contains('NAME')) {
      final got = await _askName(t.$2);
      if (got == null || !mounted) return;
      name = got;
      path = path.replaceAll('NAME', name);
    }
    // a file the repo already has opens as it is; a new one starts from the template
    _open(path, starter: _files.contains(path) ? null : _starter(pick, name.isEmpty ? 'project' : name));
  }

  /// The name for a new agent / command / skill / style: small letters, digits and dashes.
  Future<String?> _askName(String what) async {
    final box = TextEditingController();
    final go = await codeSheet<bool>(context, widget.app,
        title: 'Name for ${what.toLowerCase()}',
        body: (ctx) {
          final c = HoolaColors.of(ctx);
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            CodeField(controller: box, label: 'Name', hint: 'for example code-reviewer', mono: true),
            Text('Small letters, numbers and dashes. Spaces become dashes.', style: codeSans(c, size: 13, color: c.ink3)),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: CodeOutline('Cancel', onTap: () => Navigator.pop(ctx, false))),
              const SizedBox(width: 10),
              Expanded(flex: 2, child: CodeMain('Next', onTap: () => Navigator.pop(ctx, true))),
            ]),
          ]);
        });
    final raw = box.text;
    Future<void>.delayed(const Duration(milliseconds: 500), box.dispose);
    if (go != true) return null;
    final name = raw.trim().toLowerCase().replaceAll(RegExp(r'\s+'), '-').replaceAll(RegExp(r'[^a-z0-9._-]'), '');
    if (name.isEmpty || name.length > 60) {
      if (mounted) codeToast(context, 'Give it a short name, like code-reviewer.');
      return null;
    }
    return name;
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    Widget body;
    if (_loading) {
      body = const Center(child: CodeRing(size: 20));
    } else if (_failed) {
      body = CodeLoadFailed(onRetry: _reload);
    } else {
      body = ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), children: [
        Text("These are this repo's Claude Code files. A change is made in this session's working copy and goes into its "
            'pull request. Keep keys and passwords out of them.',
            style: codeSans(c, size: 14, color: c.ink2)),
        CodeSection('Files · ${_files.length}',
            trailing: CodeOutline('Add', height: 48, icon: Icons.add_rounded, onTap: _add)),
        if (_files.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text('This repo has none yet. Tap Add to start one.', style: codeSans(c, size: 14, color: c.ink3)),
          ),
        for (final f in _files)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: CodeCard(
              onTap: () => _open(f),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(children: [
                Icon(_fileIcon(f), size: 20, color: c.ink2),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(f, maxLines: 2, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 13.5)),
                    if (codeClaudeFileWords(f).isNotEmpty)
                      Text(codeClaudeFileWords(f), style: codeSans(c, size: 13, color: c.ink3, height: 1.35)),
                  ]),
                ),
                Icon(Icons.chevron_right_rounded, size: 20, color: c.ink3),
              ]),
            ),
          ),
      ]);
    }
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          CodeTopBar(
            title: 'Claude Code files',
            sub: 'CLAUDE.md, .claude/',
            actions: [CodeIconButton(icon: Icons.add_rounded, label: 'Add a file', onTap: _loading || _failed ? null : _add)],
          ),
          Expanded(child: body),
        ]),
      ),
    );
  }
}

/// One Claude Code file: its text in a monospace box, Save and Cancel. Pops with 'saved' / 'deleted' when it changed.
class CodeClaudeFileEditor extends StatefulWidget {
  const CodeClaudeFileEditor({super.key, required this.app, required this.id, required this.path, this.starter});
  final Santosh app;
  final String id;
  final String path;
  /// A new file's first text (from a template); null = read the file from the working copy.
  final String? starter;
  @override
  State<CodeClaudeFileEditor> createState() => _CodeClaudeFileEditorState();
}

class _CodeClaudeFileEditorState extends State<CodeClaudeFileEditor> {
  final _box = TextEditingController();
  String _orig = '';
  bool _loading = true, _saving = false, _exists = false, _failed = false;
  late bool _shownDirty = widget.starter != null;   // what the back gesture knows (asks before it drops her changes)
  String _error = '';

  @override
  void initState() {
    super.initState();
    final s = widget.starter;
    if (s != null) {
      _box.text = s;
      _loading = false;
    } else {
      _fetch();
    }
    _box.addListener(_changed);
  }

  @override
  void dispose() {
    _box.removeListener(_changed);
    _box.dispose();
    super.dispose();
  }

  void _changed() {
    if (!mounted) return;
    final d = _dirty;
    if (d == _shownDirty && _error.isEmpty) return;
    setState(() {
      _shownDirty = d;
      _error = '';
    });
  }

  bool get _dirty => _box.text != _orig || widget.starter != null;

  Future<void> _fetch() async {
    final (got, _) = await _ask(widget.app, 'GET', '${_tBase(widget.id)}/claude-file', query: {'path': widget.path});
    if (!mounted) return;
    if (got != null) {
      _orig = cs(got['text']);
      _exists = got['exists'] == true || _orig.isNotEmpty;
      _box.text = _orig;
    }
    setState(() {
      _loading = false;
      _failed = got == null;
      _shownDirty = false;
    });
  }

  void _retry() {
    setState(() {
      _loading = true;
      _failed = false;
    });
    _fetch();
  }

  Future<void> _save() async {
    if (_saving) return;
    final text = _box.text;
    final empty = text.trim().isEmpty;
    if (empty && !_exists) {
      setState(() => _error = 'The file is empty - there is nothing to save.');
      return;
    }
    if (!empty && widget.path.endsWith('.json')) {
      try {
        jsonDecode(text);
      } catch (e) {
        setState(() => _error = 'That is not valid JSON: ${'$e'.replaceFirst('FormatException: ', '')}');
        return;
      }
    }
    if (empty) {
      final yes = await codeSheet<bool>(context, widget.app,
          title: 'Delete ${widget.path.split('/').last}?',
          body: (ctx) {
            final c = HoolaColors.of(ctx);
            return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('An empty file is deleted from this session\'s working copy. The deletion goes into its pull request.',
                  style: codeSans(c, size: 14.5, color: c.ink2)),
              const SizedBox(height: 16),
              Row(children: [
                Expanded(child: CodeOutline('Keep it', onTap: () => Navigator.pop(ctx, false))),
                const SizedBox(width: 10),
                Expanded(child: CodeOutline('Delete', color: c.bad, icon: Icons.delete_outline_rounded, onTap: () => Navigator.pop(ctx, true))),
              ]),
            ]);
          });
      if (yes != true || !mounted) return;
    }
    setState(() {
      _saving = true;
      _error = '';
    });
    final (got, why) = await _ask(widget.app, 'PUT', '${_tBase(widget.id)}/claude-file', body: {'path': widget.path, 'text': empty ? '' : text});
    if (!mounted) return;
    if (got == null) {
      setState(() {
        _saving = false;
        _error = why;
      });
      return;
    }
    _orig = _box.text;
    _saving = false;
    Navigator.of(context).pop(cs(got['what']).isEmpty ? (empty ? 'deleted' : 'saved') : cs(got['what']));
  }

  Future<void> _leave() async {
    if (!_dirty || _loading) {
      Navigator.of(context).pop();
      return;
    }
    final go = await codeSheet<bool>(context, widget.app,
        title: 'Leave without saving?',
        body: (ctx) {
          final c = HoolaColors.of(ctx);
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Your changes to this file are not saved.', style: codeSans(c, size: 14.5, color: c.ink2)),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: CodeOutline('Keep editing', onTap: () => Navigator.pop(ctx, false))),
              const SizedBox(width: 10),
              Expanded(child: CodeOutline('Leave', color: c.bad, onTap: () => Navigator.pop(ctx, true))),
            ]),
          ]);
        });
    if (go == true && mounted) {
      _orig = _box.text;
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final name = widget.path.split('/').last;
    Widget body;
    if (_loading) {
      body = const Center(child: CodeRing(size: 20));
    } else if (_failed) {
      body = CodeLoadFailed(onRetry: _retry);
    } else {
      body = Container(
        margin: const EdgeInsets.fromLTRB(12, 10, 12, 0),
        decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: c.line)),
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: TextField(
          controller: _box,
          expands: true,
          minLines: null,
          maxLines: null,
          keyboardType: TextInputType.multiline,
          textAlignVertical: TextAlignVertical.top,
          autocorrect: false,
          enableSuggestions: false,
          style: codeMono(c, size: 13.5),
          cursorColor: c.accent,
          decoration: codeBareInput(c, hint: 'Write the file here', size: 14, padding: const EdgeInsets.symmetric(vertical: 12)),
        ),
      );
    }
    return PopScope(
      canPop: !_shownDirty || _loading || _failed,
      onPopInvokedWithResult: (did, _) {
        if (!did) _leave();
      },
      child: Scaffold(
        backgroundColor: c.bg,
        body: SafeArea(
          child: Column(children: [
            SizedBox(
              height: 60,
              child: Row(children: [
                CodeIconButton(icon: Icons.close_rounded, label: 'Cancel', onTap: _leave),
                Expanded(
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 16, weight: FontWeight.w600, height: 1.25)),
                    Text(widget.path, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 12, color: c.ink3)),
                  ]),
                ),
                const SizedBox(width: 12),
              ]),
            ),
            Expanded(child: body),
            Container(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
                if (_error.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Semantics(liveRegion: true, child: Text(_error, style: codeSans(c, size: 13.5, color: c.bad))),
                  ),
                Text('Save an empty file to delete it.', style: codeSans(c, size: 12.5, color: c.ink3)),
                const SizedBox(height: 8),
                Row(children: [
                  Expanded(child: CodeOutline('Cancel', height: 48, onTap: _saving ? null : _leave)),
                  const SizedBox(width: 10),
                  Expanded(
                      flex: 2,
                      child: CodeMain('Save', icon: Icons.check_rounded, height: 48, busy: _saving,
                          onTap: _loading || _failed ? null : _save)),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}
