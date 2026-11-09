// v0.390 PAKKI NEEV (App Sahayak Pillar B): her app's data is safe - entries / files / writes against its limits, a
// backup now, and a restore to any backup (HER tap, after a confirm; a safety copy of today's data is taken first).
// The full ZIP export and restore-to-a-minute are on the web console's app page.
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

class AppSafetyPanel extends StatefulWidget {
  const AppSafetyPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppSafetyPanel> createState() => _AppSafetyPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
String _s(dynamic v) => v == null ? '' : '$v';
num _n(dynamic v) => v is num ? v : (num.tryParse('$v') ?? 0);

class _AppSafetyPanelState extends State<AppSafetyPanel> {
  Map<String, dynamic> _u = {};
  List<Map<String, dynamic>> _b = [];
  bool _busy = false;

  String get _base => '/api/apps/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final u = _m(await widget.app.api!.call('GET', '$_base/usage'));
      final b = _m(await widget.app.api!.call('GET', '$_base/backups'));
      if (!mounted) return;
      setState(() {
        _u = u;
        _b = _l(b['backups']);
      });
    } catch (_) {}
  }

  void _say(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _snap() async {
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '$_base/backups/now'));
      _say('Backed up: ${_s(r['rows'])} entries.');
    } catch (e) {
      _say('$e');
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  Future<void> _restore(Map<String, dynamic> b) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Restore the data?'),
        content: Text('The app data ${_s(b['at']).length >= 16 ? _s(b['at']).replaceAll('T', ' ').substring(0, 16) : _s(b['name'])} (UTC) will become the same as that backup. '
            'A safety copy of the current data will be made first.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, restore')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '$_base/backups/restore', body: {'name': _s(b['name'])}, timeout: const Duration(seconds: 120)));
      _say(_s(r['say']));
    } catch (e) {
      _say('$e');
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  Widget _meter(String label, num used, num cap, num pct) => Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('$label: ${used.toStringAsFixed(used % 1 == 0 ? 0 : 1)} / ${cap.toStringAsFixed(0)} (${pct.toStringAsFixed(0)}%)',
              style: const TextStyle(color: C.ink, fontSize: 12.5)),
          const SizedBox(height: 3),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(value: (pct / 100).clamp(0, 1).toDouble(), minHeight: 6,
                color: pct >= 95 ? C.bad : (pct >= 80 ? C.warn : C.ok), backgroundColor: const Color(0x22FFFFFF)),
          ),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final lim = _m(_u['limits']);
    final pc = _m(_u['percent']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.shield_rounded, color: C.ok, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Data safety', style: display(15))),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Refresh'),
      ]),
      const Text('Every change is recorded; a full backup every day and before every big change. You can go back to any backup.',
          style: TextStyle(color: C.muted, fontSize: 12)),
      if (_u.isNotEmpty) ...[
        _meter('Entries', _n(_u['rows']), _n(lim['rows']), _n(pc['rows'])),
        _meter('Files (MB)', _n(_u['files_mb']), _n(lim['files_mb']), _n(pc['files_mb'])),
        _meter('Today\'s writes', _n(_u['writes_today']), _n(lim['writes_day']), _n(pc['writes_day'])),
      ],
      const SizedBox(height: 8),
      FilledButton.icon(onPressed: _busy ? null : _snap, icon: const Icon(Icons.backup_rounded, size: 18), label: const Text('Back up now')),
      if (_b.isNotEmpty) ...[
        const SizedBox(height: 8),
        Text('Backups (${_b.length})', style: display(13.5)),
        for (final b in _b.take(12))
          Row(children: [
            Expanded(
              child: Text('${_s(b['at']).length >= 16 ? _s(b['at']).substring(0, 16).replaceAll('T', ' ') : ''} · ${_s(b['kind'])} · ${_s(b['rows'])} entries',
                  style: const TextStyle(color: C.ink, fontSize: 12.5)),
            ),
            TextButton(onPressed: _busy ? null : () => _restore(b), child: const Text('Restore')),
          ]),
      ],
    ]);
  }
}
