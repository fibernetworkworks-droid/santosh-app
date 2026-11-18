// v0.921 HOOLA CODE NATIVE - the changes (screen 5 of claude.ai/artifact/GF4AtP5MNfV8kARgTGymuh): one file per chip,
// the lines with their old / new numbers, "This round" or against the base branch (as GitHub computes it), and her
// comments on lines - hold a line to comment; the comments go with her next message to Hoola.
import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'code_files.dart';
import 'code_kit.dart';
import 'code_session.dart';

class CodeChangesPage extends StatefulWidget {
  const CodeChangesPage({super.key, required this.app, required this.task});
  final Santosh app;
  final Map<String, dynamic> task;
  @override
  State<CodeChangesPage> createState() => _CodeChangesPageState();
}

class _Row {
  const _Row(this.t, this.text, {this.o = 0, this.n = 0});
  final String t; // hunk | add | del | ctx
  final String text;
  final int o, n;
}

List<_Row> _parse(String diff) {
  final out = <_Row>[];
  var o = 0, n = 0;
  final re = RegExp(r'^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@');
  for (final l in diff.replaceAll(RegExp(r'\n$'), '').split('\n')) {
    if (l.startsWith('--- ') || l.startsWith('+++ ') || l.startsWith(r'\')) continue;
    final m = re.firstMatch(l);
    if (m != null) {
      o = int.parse(m.group(1)!);
      n = int.parse(m.group(2)!);
      out.add(_Row('hunk', l));
    } else if (l.startsWith('+')) {
      out.add(_Row('add', l.substring(1), n: n++));
    } else if (l.startsWith('-')) {
      out.add(_Row('del', l.substring(1), o: o++));
    } else {
      out.add(_Row('ctx', l.isEmpty ? '' : l.substring(1), o: o++, n: n++));
    }
  }
  return out;
}

class _CodeChangesPageState extends State<CodeChangesPage> {
  int _file = 0;
  bool _vsBase = false, _loading = false;
  Map<String, dynamic>? _cmp;

  Map<String, dynamic> get t => widget.task;
  String get _id => cs(t['id']);
  bool get _pushed => ci(t['pr_number']) != 0 || cs(t['head_sha']).isNotEmpty;
  String get _baseName => cs(t['base']).isNotEmpty ? cs(t['base']) : 'main';
  List<Map<String, dynamic>> get _files => _vsBase && _cmp != null ? cl(_cmp!['files']) : cl(t['file_diffs']);
  List<Map<String, dynamic>> get _comments => CodeComments.of(_id);

  bool get _canSend => codeRunning(t) || codeCanRevise.contains(cs(t['status'])) || t['can_continue'] == true;

  Future<void> _compare(bool on) async {
    if (!on) {
      setState(() {
        _vsBase = false;
        _file = 0;
      });
      return;
    }
    setState(() => _loading = true);
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/tasks/${Uri.encodeComponent(_id)}/compare', query: {'base': _baseName});
    if (!mounted) return;
    setState(() {
      _loading = false;
      if (r != null) {
        _cmp = r;
        _vsBase = true;
        _file = 0;
      }
    });
  }

  Future<void> _comment(String path, _Row row, {int? edit}) async {
    final line = row.n != 0 ? row.n : row.o;
    final ctl = TextEditingController(text: edit == null ? '' : cs(_comments[edit]['text']));
    final c = HoolaColors.of(context);
    final ok = await codeSheet<bool>(context, widget.app,
        title: 'Comment on line $line',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(10)),
                child: Text(row.text.trim().isEmpty ? '(empty line)' : row.text, maxLines: 3, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 12)),
              ),
              CodeField(controller: ctl, label: 'What should Hoola change here?', lines: 3),
              CodeMain(edit == null ? 'Add comment' : 'Save', onTap: () => Navigator.pop(ctx, true)),
            ]));
    final text = ctl.text.trim();
    ctl.dispose();
    if (ok != true || text.isEmpty || !mounted) return;
    setState(() {
      if (edit == null) {
        _comments.add({'path': path, 'line': line, 'code': row.text.trim(), 'text': text});
      } else {
        _comments[edit]['text'] = text;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final files = _files;
    final (a, r) = codeStat(t);
    if (_file >= files.length) _file = 0;
    final f = files.isEmpty ? null : files[_file];
    final rows = f == null ? const <_Row>[] : _parse(cs(f['diff']));
    final path = f == null ? '' : cs(f['path']);
    final comments = _comments;
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          Container(
            height: 60,
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Row(children: [
              CodeIconButton(icon: Icons.close_rounded, label: 'Close', onTap: () => Navigator.of(context).maybePop(false)),
              Expanded(
                child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Changes', style: codeSans(c, size: 16, weight: FontWeight.w600, height: 1.25)),
                  Row(children: [
                    Text('${cPlural(cl(t['files']).length, 'file')} · ', style: codeSans(c, size: 12, color: c.ink3)),
                    CodeStat(a, r, size: 12),
                  ]),
                ]),
              ),
              if (_pushed)
                Container(
                  margin: const EdgeInsets.only(right: 8),
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(17)),
                  child: Row(children: [
                    _seg(c, 'This round', !_vsBase, () => _compare(false)),
                    _seg(c, 'vs $_baseName', _vsBase, () => _compare(true)),
                  ]),
                ),
            ]),
          ),
          if (_loading) LinearProgressIndicator(minHeight: 2, color: c.ink, backgroundColor: c.sunk),
          CodeRiskyNote(files: cl(t['risky_files'])),
          if (files.isNotEmpty)
            SizedBox(
              height: 48,
              child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 16), children: [
                for (final (i, x) in files.indexed) ...[
                  CodeChip(cs(x['path']),
                      mono: true,
                      on: i == _file,
                      onTap: () => setState(() => _file = i),
                      trailing: CodeStat(ci(x['added']), ci(x['removed']), size: 12)),
                  const SizedBox(width: 8),
                ],
              ]),
            ),
          if (_vsBase && _cmp != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 6),
              child: Text('${cs(_cmp!['head'])} against ${cs(_cmp!['base'])} · ${ci(_cmp!['ahead'])} ahead, ${ci(_cmp!['behind'])} behind · as GitHub counts it',
                  style: codeSans(c, size: 12, color: c.ink3)),
            ),
          Expanded(
            child: f == null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(codeRunning(t) ? 'Hoola is still writing - the lines show here when the round ends.' : 'No changes in this session.',
                          textAlign: TextAlign.center, style: codeSans(c, color: c.ink2)),
                    ),
                  )
                : ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 20), children: [
                    Container(
                      decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: c.line)),
                      clipBehavior: Clip.antiAlias,
                      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                        for (final row in rows.take(1500)) ..._rowWidgets(c, path, row, comments),
                        if (rows.length > 1500) Padding(padding: const EdgeInsets.all(12), child: Text('… ${rows.length - 1500} more lines', style: codeSans(c, size: 12.5, color: c.ink3))),
                      ]),
                    ),
                    Padding(padding: const EdgeInsets.fromLTRB(8, 10, 8, 0), child: Text('Hold a line to comment on it.', style: codeSans(c, size: 12.5, color: c.ink3))),
                  ]),
          ),
          if (comments.isNotEmpty)
            Container(
              padding: const EdgeInsets.fromLTRB(20, 12, 16, 14),
              decoration: BoxDecoration(color: c.bg, border: Border(top: BorderSide(color: c.sunk))),
              child: Row(children: [
                Expanded(
                  child: Text(
                      _canSend ? '${cPlural(comments.length, 'comment')} goes with your next message' : 'This session cannot take changes any more.',
                      style: codeSans(c, size: 13, color: c.ink2)),
                ),
                if (_canSend) CodeMain('Send to Hoola', height: 46, onTap: () => Navigator.of(context).pop(true)),
              ]),
            ),
        ]),
      ),
    );
  }

  Widget _seg(HoolaColors c, String label, bool on, VoidCallback onTap) => Semantics(
        selected: on,
        button: true,
        label: label,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(15),
          child: Container(
            constraints: const BoxConstraints(minHeight: 36),
            padding: const EdgeInsets.symmetric(horizontal: 12),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: on ? c.surface : null,
              borderRadius: BorderRadius.circular(15),
              boxShadow: on && !c.dark ? [BoxShadow(color: c.shadow.withOpacity(.12), blurRadius: 2, offset: const Offset(0, 1))] : null,
            ),
            child: Text(label, style: codeSans(c, size: 12.5, weight: FontWeight.w500, color: on ? c.ink : c.ink2)),
          ),
        ),
      );

  List<Widget> _rowWidgets(HoolaColors c, String path, _Row row, List<Map<String, dynamic>> comments) {
    if (row.t == 'hunk') {
      return [
        Container(
          color: c.sunk,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          child: Text(row.text, style: codeMono(c, size: 12, color: c.ink2)),
        ),
      ];
    }
    final bg = switch (row.t) { 'add' => c.okSoft, 'del' => c.badSoft, _ => null };
    final fg = switch (row.t) { 'add' => c.ok, 'del' => c.bad, _ => c.ink };
    final ns = TextStyle(fontFamily: HoolaFont.mono, fontSize: 12, color: row.t == 'ctx' ? c.ink3 : fg, height: 1.6);
    final line = row.n != 0 ? row.n : row.o;
    final mine = [for (final (i, x) in comments.indexed) if (cs(x['path']) == path && ci(x['line']) == line) i];
    return [
      GestureDetector(
        onLongPress: row.t == 'del' && row.n == 0 && row.o == 0 ? null : () => _comment(path, row),
        child: Container(
          color: bg,
          constraints: const BoxConstraints(minHeight: 24),
          padding: const EdgeInsets.symmetric(vertical: 1),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 34, child: Text(row.o == 0 ? '' : '${row.o}', textAlign: TextAlign.right, style: ns)),
            SizedBox(width: 34, child: Text(row.n == 0 ? '' : '${row.n}', textAlign: TextAlign.right, style: ns)),
            const SizedBox(width: 6),
            SizedBox(width: 12, child: Text(switch (row.t) { 'add' => '+', 'del' => '−', _ => '' }, style: ns)),
            Expanded(
              child: Text(row.text.isEmpty ? ' ' : row.text, style: TextStyle(fontFamily: HoolaFont.mono, fontSize: 12, height: 1.6, color: row.t == 'ctx' ? c.ink : fg)),
            ),
            const SizedBox(width: 8),
          ]),
        ),
      ),
      for (final i in mine) _commentBox(c, path, row, i),
    ];
  }

  Widget _commentBox(HoolaColors c, String path, _Row row, int i) {
    final x = _comments[i];
    return Container(
      margin: const EdgeInsets.fromLTRB(10, 6, 10, 8),
      padding: const EdgeInsets.fromLTRB(12, 10, 8, 6),
      decoration: BoxDecoration(color: c.bg, borderRadius: BorderRadius.circular(12), border: Border.all(color: c.line)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(
            width: 22,
            height: 22,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: c.accentSoft, shape: BoxShape.circle),
            child: Icon(Icons.person_outline_rounded, size: 14, color: c.accent),
          ),
          const SizedBox(width: 8),
          Text('You · line ${ci(x['line'])}', style: codeSans(c, size: 12.5, weight: FontWeight.w600)),
        ]),
        const SizedBox(height: 6),
        Text(cs(x['text']), style: codeSans(c, size: 14)),
        Row(children: [
          TextButton(onPressed: () => _comment(path, row, edit: i), child: Text('Edit', style: codeSans(c, size: 13, color: c.ink2))),
          TextButton(onPressed: () => setState(() => _comments.removeAt(i)), child: Text('Remove', style: codeSans(c, size: 13, color: c.ink2))),
        ]),
      ]),
    );
  }
}
