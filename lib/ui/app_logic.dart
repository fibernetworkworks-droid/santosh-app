// v0.382 DIMAAG (App Sahayak Phases 43-46): her app's BRAIN on her phone - what the logic does in plain lines, a new draft
// from her words (Opus writes it, the server's checker proves it), HER "Lagu karo" tap that makes it live, the approvals
// waiting for her, timed jobs (Abhi chalao) and the last automatic actions. Same owner routes as the web console.
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

class AppLogicPanel extends StatefulWidget {
  const AppLogicPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppLogicPanel> createState() => _AppLogicPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
List<String> _ls(dynamic v) => v is List ? v.map((e) => '$e').toList() : <String>[];
String _s(dynamic v) => v == null ? '' : '$v';

class _AppLogicPanelState extends State<AppLogicPanel> {
  Map<String, dynamic> _v = {};
  bool _loaded = false;
  bool _busy = false;
  final _words = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _words.dispose();
    super.dispose();
  }

  String get _base => '/api/apps/${widget.id}';

  Future<void> _load() async {
    try {
      final v = _m(await widget.app.api!.call('GET', '$_base/logic'));
      if (!mounted) return;
      setState(() {
        _v = v;
        _loaded = true;
      });
    } catch (_) {
      if (mounted) setState(() => _loaded = true);
    }
  }

  void _say(String t) {
    if (mounted && t.isNotEmpty) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _do(String method, String path, [Object? body]) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call(method, '$_base/$path', body: body, timeout: const Duration(seconds: 180)));
      _say(_s(r['say']).isNotEmpty ? _s(r['say']) : (r['acted'] != null ? '${r['acted']} entries done.' : 'Done.'));
    } catch (e) {
      _say('$e');
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  Widget _line(String t, {Color color = C.ink}) =>
      Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $t', style: TextStyle(color: color, fontSize: 12.5)));

  @override
  Widget build(BuildContext context) {
    final has = _v['has_logic'] == true;
    final on = _v['on'] == true;
    final d = _v['draft'] == null ? null : _m(_v['draft']);
    final apps = _l(_v['approvals']).where((a) => a['status'] == 'pending').toList();
    final jobs = _l(_m(_v['spec'])['schedules']);
    final audit = _l(_v['audit']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.account_tree_rounded, color: C.accent, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('The app\'s brain (logic)', style: display(15))),
        if (has) Pill(on ? 'On · rev ${_s(_v['rev'])}' : 'Off', fg: on ? C.ok : C.warn),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Refresh'),
      ]),
      if (!_loaded) const Text('Loading…', style: TextStyle(color: C.muted, fontSize: 12.5)),
      const Text('Linked lists (customer → order → items), automatic calculations, rules, tasks needing approval, automatic tasks and timed tasks. '
          'Hoola makes a draft; nothing changes in the app without your "Apply".',
          style: TextStyle(color: C.muted, fontSize: 12)),
      if (has) for (final x in _ls(_v['summary']).take(14)) _line(x),
      const SizedBox(height: 8),
      TextField(
        controller: _words,
        minLines: 1,
        maxLines: 4,
        style: const TextStyle(color: C.ink, fontSize: 13),
        decoration: InputDecoration(
          hintText: has ? 'What to change? for example: a quote above 50,000 needs the manager and then the director to approve' : 'Leave blank = full logic from the brief; or write it in your own words',
          isDense: true,
        ),
      ),
      const SizedBox(height: 6),
      Wrap(spacing: 8, runSpacing: 6, children: [
        FilledButton.icon(
          onPressed: _busy ? null : () => _do('POST', 'logic/draft', {'words': _words.text.trim()}),
          icon: const Icon(Icons.auto_awesome_rounded, size: 18),
          label: Text(_busy ? 'Being made…' : 'Make logic draft'),
        ),
        if (has)
          OutlinedButton(
            onPressed: _busy ? null : () => _do('POST', 'logic/switch', {'on': !on}),
            child: Text(on ? 'Turn off logic' : 'Turn on logic'),
          ),
      ]),
      if (d != null) ...[
        const SizedBox(height: 10),
        Text(_ls(d['errors']).isEmpty ? 'Draft ready' : 'In the draft ${_ls(d['errors']).length} errors', style: display(13.5)),
        if (_s(d['summary']).isNotEmpty) Text(_s(d['summary']), style: const TextStyle(color: C.ink, fontSize: 12.5)),
        for (final x in _ls(d['lines']).take(20)) _line(x),
        for (final x in _ls(d['schema_changes'])) _line('New: $x', color: C.accent),
        for (final x in _ls(d['questions'])) _line('Question: $x', color: C.warn),
        for (final x in _ls(d['errors']).take(8)) _line(x, color: C.bad),
        const SizedBox(height: 6),
        Wrap(spacing: 8, children: [
          if (_ls(d['errors']).isEmpty)
            FilledButton(
              onPressed: _busy ? null : () => _do('POST', 'logic/apply', {'hash': _s(d['hash'])}),
              child: const Text('Apply'),
            ),
          TextButton(onPressed: _busy ? null : () => _do('DELETE', 'logic/draft'), child: const Text('Remove draft')),
        ]),
      ],
      if (apps.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('Approval is pending (${apps.length})', style: display(13.5)),
        for (final a in apps.take(20))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Row(children: [
              Expanded(
                child: Text('${_s(a['title'])} · ${_s(a['label'])}: ${_s(a['from'])} → ${_s(a['to'])} · step ${_s(a['step'])}/${_s(a['of'])}'
                    '${_s(a['maker']).isNotEmpty ? ' · ${_s(a['maker'])}' : ''}',
                    style: const TextStyle(color: C.ink, fontSize: 12.5)),
              ),
              IconButton(
                onPressed: _busy ? null : () => _do('POST', 'approvals/${_s(a['id'])}', {'decision': 'approve'}),
                icon: const Icon(Icons.check_circle_rounded, color: C.ok, size: 22),
                tooltip: 'Approved',
              ),
              IconButton(
                onPressed: _busy ? null : () => _do('POST', 'approvals/${_s(a['id'])}', {'decision': 'reject'}),
                icon: const Icon(Icons.cancel_rounded, color: C.bad, size: 22),
                tooltip: 'Decline',
              ),
            ]),
          ),
      ],
      if (jobs.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('Timed tasks', style: display(13.5)),
        for (final j in jobs)
          Row(children: [
            Expanded(child: Text('${_s(j['label']).isNotEmpty ? _s(j['label']) : _s(j['name'])} · ${_s(j['every'])}',
                style: const TextStyle(color: C.ink, fontSize: 12.5))),
            TextButton(onPressed: _busy ? null : () => _do('POST', 'logic/run/${_s(j['name'])}'), child: const Text('Run now')),
          ]),
      ],
      if (audit.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('What the logic did', style: display(13.5)),
        for (final x in audit.take(8))
          _line('${_s(x['at']).length >= 16 ? _s(x['at']).substring(5, 16).replaceAll('T', ' ') : ''} · ${_s(x['kind'])} · ${_s(x['what'])}',
              color: C.muted),
      ],
    ]);
  }
}
