// v0.943 HOOLA CODE FILES + WHAT IT SAW (owner, on the Cursor comparison: "No editor ... It doesn't open a browser to
// check the app it changed").
// Not an editor: a reader of the session's working copy - folders, then a file with line numbers. Tap lines to pick
// them and "Ask Hoola about these lines" puts them, quoted with their path and numbers, into her next message.
// Also: the look card (the screenshots Hoola took of the page it changed) and the red risky-files note.
// Routes: GET /api/devsahayak/tasks/{id}/files?path=, GET /api/devsahayak/tasks/{id}/shots/{name}.
import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'code_kit.dart';

// ============================================================================================== the file reader
class CodeFilesPage extends StatefulWidget {
  const CodeFilesPage({super.key, required this.app, required this.id, this.path = ''});
  final Santosh app;
  final String id;
  final String path;
  @override
  State<CodeFilesPage> createState() => _CodeFilesPageState();
}

class _CodeFilesPageState extends State<CodeFilesPage> {
  late String _path = widget.path;
  List<Map<String, dynamic>> _rows = [];
  String? _text;
  bool _hidden = false;
  bool _loading = true;
  final Set<int> _pick = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/tasks/${widget.id}/files',
        query: {'path': _path}, quiet: true);
    if (!mounted) return;
    setState(() {
      _loading = false;
      _pick.clear();
      if (r != null && r.containsKey('text')) {
        _text = cs(r['text']);
        _hidden = r['hidden'] == true;
        _rows = [];
      } else {
        _text = null;
        _hidden = false;
        _rows = cl(r?['entries']);
      }
    });
  }

  void _open(String p) {
    _path = p;
    _load();
  }

  void _up() {
    if (_path.isEmpty) {
      Navigator.of(context).maybePop();
      return;
    }
    final i = _path.lastIndexOf('/');
    _open(i < 0 ? '' : _path.substring(0, i));
  }

  void _ask() {
    final lines = (_text ?? '').split('\n');
    final picked = _pick.toList()..sort();
    if (picked.isEmpty) return;
    final from = picked.first + 1, to = picked.last + 1;
    final body = [for (var i = picked.first; i <= picked.last && i < lines.length; i++) lines[i]].join('\n');
    final quote = 'In $_path, lines $from${to > from ? '-$to' : ''}:\n```\n$body\n```\n';
    Navigator.of(context).pop(quote);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final name = _path.isEmpty ? 'Files' : _path.split('/').last;
    return PopScope(
      canPop: _path.isEmpty,
      onPopInvokedWithResult: (did, _) {
        if (!did) _up();
      },
      child: Scaffold(
        backgroundColor: c.bg,
        body: SafeArea(
          child: Column(children: [
            SizedBox(
              height: 60,
              child: Row(children: [
                CodeIconButton(icon: Icons.arrow_back_rounded, label: 'Back', onTap: _up),
                Expanded(
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 16, weight: FontWeight.w600, height: 1.25)),
                    if (_path.isNotEmpty)
                      Text(_path, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 12, color: c.ink3)),
                  ]),
                ),
                const SizedBox(width: 12),
              ]),
            ),
            if (_loading) LinearProgressIndicator(minHeight: 2, color: c.ink, backgroundColor: c.sunk),
            Expanded(child: _text != null ? _file(c) : _folder(c)),
            if (_text != null && _pick.isNotEmpty)
              Container(
                decoration: BoxDecoration(color: c.surface, border: Border(top: BorderSide(color: c.line))),
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Text('${cPlural(_pick.length, 'line')} picked', style: codeSans(c, size: 13.5, color: c.ink2)),
                  const SizedBox(height: 8),
                  CodeMain('Ask Hoola about these lines', onTap: _ask),
                ]),
              ),
          ]),
        ),
      ),
    );
  }

  Widget _folder(HoolaColors c) {
    if (_rows.isEmpty && !_loading) {
      return Center(child: Text('Nothing here yet.', style: codeSans(c, size: 14, color: c.ink3)));
    }
    return ListView.builder(
      itemCount: _rows.length,
      itemBuilder: (_, i) {
        final r = _rows[i];
        final dir = r['dir'] == true;
        final ch = cs(r['changed']);
        return InkWell(
          onTap: () => _open(cs(r['path'])),
          child: Container(
            constraints: const BoxConstraints(minHeight: 52),
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
            child: Row(children: [
              Icon(dir ? Icons.folder_outlined : Icons.description_outlined, size: 20, color: c.ink2),
              const SizedBox(width: 12),
              Expanded(child: Text(cs(r['name']), style: codeMono(c, size: 13.5, color: c.ink))),
              if (ch.isNotEmpty) CodeBadge(ch == 'A' ? 'New' : 'Changed', fg: c.accent, bg: c.accentSoft),
              if (dir) Icon(Icons.chevron_right_rounded, size: 20, color: c.ink3),
            ]),
          ),
        );
      },
    );
  }

  Widget _file(HoolaColors c) {
    if (_hidden) {
      return Padding(padding: const EdgeInsets.all(20), child: Text(_text ?? '', style: codeSans(c, size: 14, color: c.ink2)));
    }
    final lines = (_text ?? '').split('\n');
    final w = '${lines.length}'.length * 8.0 + 14;
    return Scrollbar(
      child: ListView.builder(
        itemCount: lines.length,
        itemBuilder: (_, i) {
          final on = _pick.contains(i);
          return GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => setState(() => on ? _pick.remove(i) : _pick.add(i)),
            child: Container(
              color: on ? c.accentSoft : null,
              constraints: const BoxConstraints(minHeight: 22),
              padding: const EdgeInsets.only(right: 12),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(
                    width: w,
                    child: Text('${i + 1}', textAlign: TextAlign.right, style: codeMono(c, size: 12, color: on ? c.accent : c.ink3))),
                const SizedBox(width: 10),
                Expanded(child: Text(lines[i], style: codeMono(c, size: 12.5, color: c.ink))),
              ]),
            ),
          );
        },
      ),
    );
  }
}

// ============================================================================================== what it saw
/// The screenshots Hoola took of the page it changed (`look`), phone and computer, with what it noticed.
class CodeLookCard extends StatelessWidget {
  const CodeLookCard({super.key, required this.app, required this.id, required this.step});
  final Santosh app;
  final String id;
  final Map<String, dynamic> step;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final shots = [for (final s in (step['shots'] as List?) ?? const []) cs(s)];
    final errs = ci(step['errors']);
    final api = app.api;
    return CodeCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.visibility_outlined, size: 18, color: c.ink2),
          const SizedBox(width: 8),
          Expanded(child: Text('Looked at ${cs(step['path'])}', style: codeSans(c, size: 14, weight: FontWeight.w600))),
          if (errs > 0) CodeBadge(cPlural(errs, 'error'), fg: c.bad, bg: c.badSoft),
        ]),
        if (api != null && shots.isNotEmpty) ...[
          const SizedBox(height: 10),
          SizedBox(
            height: 220,
            child: ListView(scrollDirection: Axis.horizontal, children: [
              for (final s in shots)
                Padding(
                  padding: const EdgeInsets.only(right: 10),
                  child: GestureDetector(
                    onTap: () => _full(context, api.absolute('/api/devsahayak/tasks/$id/shots/$s'), api.authHeaders),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: Container(
                        decoration: BoxDecoration(border: Border.all(color: c.line), borderRadius: BorderRadius.circular(10)),
                        child: Image.network(api.absolute('/api/devsahayak/tasks/$id/shots/$s'),
                            headers: api.authHeaders,
                            height: 220,
                            fit: BoxFit.contain,
                            semanticLabel: s.contains('phone') ? 'Phone screenshot' : 'Computer screenshot',
                            errorBuilder: (_, __, ___) => SizedBox(
                                width: 120,
                                height: 220,
                                child: Center(child: Text('Not kept', style: codeSans(c, size: 12, color: c.ink3))))),
                      ),
                    ),
                  ),
                ),
            ]),
          ),
        ],
        if (cs(step['text']).isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(errs > 0 ? 'The page printed errors - Hoola reads them before it calls the work done.' : 'No errors in the page.',
              style: codeSans(c, size: 13, color: c.ink2)),
        ],
      ]),
    );
  }

  void _full(BuildContext context, String url, Map<String, String> headers) {
    Navigator.of(context).push(MaterialPageRoute<void>(
        builder: (_) => HoolaTheme(
            appearance: app.appearance,
            child: Builder(builder: (ctx) {
              final c = HoolaColors.of(ctx);
              return Scaffold(
                backgroundColor: c.bg,
                body: SafeArea(
                  child: Stack(children: [
                    Positioned.fill(
                        child: InteractiveViewer(maxScale: 4, child: Center(child: Image.network(url, headers: headers, fit: BoxFit.contain)))),
                    Positioned(
                        top: 4,
                        left: 4,
                        child: CodeIconButton(icon: Icons.close_rounded, label: 'Close', onTap: () => Navigator.of(ctx).maybePop())),
                  ]),
                ),
              );
            }))));
  }
}

// ============================================================================================== risky files
/// Files that change how her tools, CI or a coding agent run - shown in red before she merges.
class CodeRiskyNote extends StatelessWidget {
  const CodeRiskyNote({super.key, required this.files});
  final List<Map<String, dynamic>> files;

  @override
  Widget build(BuildContext context) {
    if (files.isEmpty) return const SizedBox.shrink();
    final c = HoolaColors.of(context);
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: c.badSoft, borderRadius: BorderRadius.circular(12), border: Border.all(color: c.bad)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.warning_amber_rounded, size: 18, color: c.bad),
          const SizedBox(width: 8),
          Expanded(
              child: Text('Check these before you merge', style: codeSans(c, size: 14, weight: FontWeight.w600, color: c.bad))),
        ]),
        const SizedBox(height: 6),
        Text('They change how your tools, your CI or a coding agent behave, so a bad change here can run code on your machines.',
            style: codeSans(c, size: 13, color: c.ink2)),
        const SizedBox(height: 6),
        for (final f in files)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text.rich(TextSpan(children: [
              TextSpan(text: cs(f['path']), style: codeMono(c, size: 12.5, color: c.ink)),
              TextSpan(text: '  ${cs(f['why'])}', style: codeSans(c, size: 12.5, color: c.ink2)),
            ])),
          ),
      ]),
    );
  }
}
