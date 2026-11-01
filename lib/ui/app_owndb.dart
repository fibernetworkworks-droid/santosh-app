// v0.391 APNA DATABASE: this app's data in HER own database (Supabase, Neon, AWS, Google, Azure, DigitalOcean ... any
// PostgreSQL-wire). Pick one of her connected databases (Profile > Postgres database), primary or copy mode, her tap
// moves the data (backup first, counts compared); sync now / compare / disconnect (her data stays in both places).
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';
import 'postgres_screen.dart';

class AppOwnDbPanel extends StatefulWidget {
  const AppOwnDbPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppOwnDbPanel> createState() => _AppOwnDbPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
String _s(dynamic v) => v == null ? '' : '$v';

class _AppOwnDbPanelState extends State<AppOwnDbPanel> {
  Map<String, dynamic> _v = {};
  String _conn = '';
  String _mode = 'primary';
  bool _busy = false;

  String get _base => '/api/apps/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = _m(await widget.app.api!.call('GET', '$_base/owndb'));
      if (!mounted) return;
      setState(() {
        _v = v;
        final cs = _l(v['connections']);
        if (_conn.isEmpty && cs.isNotEmpty) _conn = _s(cs.first['id']);
      });
    } catch (_) {}
  }

  void _say(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _do(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call(method, '$_base/$path', body: body, timeout: const Duration(seconds: 300)));
      _say(_s(r['say']).isNotEmpty ? _s(r['say']) : (r['ok'] == true ? 'Ho gaya.' : 'Ginti: ${_s(r['counts'])}'));
    } catch (e) {
      _say('$e');
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  Future<void> _link() async {
    final name = _l(_v['connections']).firstWhere((c) => _s(c['id']) == _conn, orElse: () => {})['name'];
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Data apne database mein le jaayein?'),
        content: Text('Is app ka saara data "${_s(name)}" mein copy hoga (pehle backup, phir ginti milaayi jaayegi). '
            '${_mode == 'primary' ? 'Har nayi entry pehle wahin save hogi.' : 'Wahan ek live copy rahegi.'}'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Nahi')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan, le jaao')),
        ],
      ),
    );
    if (ok == true) _do('POST', 'owndb/link', {'conn': _conn, 'mode': _mode});
  }

  @override
  Widget build(BuildContext context) {
    final linked = _v['linked'] == true;
    final ln = _m(_v['link']);
    final conns = _l(_v['connections']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.storage_rounded, color: C.accent, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Apna database', style: display(15))),
        if (linked) Pill(_s(ln['mode']) == 'primary' ? 'Data wahin' : 'Copy', fg: C.ok),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Taaza karo'),
      ]),
      Text('Is app ka data apne database mein chalaiye: Supabase, Neon, AWS, Google Cloud, Azure, DigitalOcean aur '
          '${(_l(_v['providers']).length - 6).clamp(0, 99)}+ aur.', style: const TextStyle(color: C.muted, fontSize: 12)),
      const SizedBox(height: 6),
      if (linked) ...[
        Text('${_s(ln['name'])} · ${_s(ln['label'])}', style: const TextStyle(color: C.ink, fontSize: 12.5)),
        Text('Schema ${_s(ln['schema'])} · sync baaki: ${_s(_v['lag'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
        if (_s(ln['last_error']).isNotEmpty) Text('Dikkat: ${_s(ln['last_error'])}', style: const TextStyle(color: C.bad, fontSize: 12)),
        Wrap(spacing: 8, children: [
          TextButton(onPressed: _busy ? null : () => _do('POST', 'owndb/sync'), child: const Text('Abhi sync')),
          TextButton(onPressed: _busy ? null : () => _do('POST', 'owndb/verify'), child: const Text('Ginti milao')),
          TextButton(onPressed: _busy ? null : () => _do('POST', 'owndb/unlink'), child: const Text('Alag karo')),
        ]),
      ] else ...[
        if (conns.isEmpty) const Text('Abhi koi database juda nahi.', style: TextStyle(color: C.muted, fontSize: 12.5)),
        if (conns.isNotEmpty) ...[
          DropdownButton<String>(
            value: _conn.isEmpty ? null : _conn,
            isExpanded: true,
            items: [for (final c in conns) DropdownMenuItem(value: _s(c['id']), child: Text('${_s(c['name'])} (${_s(c['label'])})', overflow: TextOverflow.ellipsis))],
            onChanged: (x) => setState(() => _conn = x ?? ''),
          ),
          SegmentedButton<String>(
            segments: const [ButtonSegment(value: 'primary', label: Text('Data wahin')), ButtonSegment(value: 'mirror', label: Text('Sirf copy'))],
            selected: {_mode},
            onSelectionChanged: (x) => setState(() => _mode = x.first),
          ),
          const SizedBox(height: 6),
          FilledButton(onPressed: _busy || _conn.isEmpty ? null : _link, child: Text(_busy ? 'Copy ho raha hai…' : 'Data wahan le jaao')),
        ],
        TextButton.icon(
          onPressed: () async {
            await Navigator.push(context, MaterialPageRoute(builder: (_) => PostgresScreen(app: widget.app)));
            _load();
          },
          icon: const Icon(Icons.add_rounded, size: 18),
          label: const Text('Database jodo'),
        ),
      ],
    ]);
  }
}
