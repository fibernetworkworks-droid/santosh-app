// v0.424 JODO (App Sahayak Pillar F): her app's connectors on the phone - what each one sends where, Approve (her tap,
// after a confirm) and the last runs. Adding packs, keys and webhooks is on the web console's app page.
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

class AppConnectPanel extends StatefulWidget {
  const AppConnectPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppConnectPanel> createState() => _AppConnectPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
String _s(dynamic v) => v == null ? '' : '$v';

class _AppConnectPanelState extends State<AppConnectPanel> {
  Map<String, dynamic> _c = {};
  bool _busy = false;

  String get _base => '/api/apps/${widget.id}/connect';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = _m(await widget.app.api!.call('GET', _base));
      if (mounted) setState(() => _c = c);
    } catch (_) {}
  }

  Future<void> _approve(Map<String, dynamic> a) async {
    final lv = _m(a['leaves']);
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text('Approve: ${_s(a['label'])}?'),
        content: Text('${_s(lv['method'])} ${_s(lv['host'])}\nWhen: ${_s(lv['when'])}\nSends: ${(lv['fields'] as List? ?? const []).join(', ')}\n'
            'Key: ${(lv['secrets'] as List? ?? const []).join(', ')}'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, approve')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final c = _m(await widget.app.api!.call('POST', '$_base/actions/${_s(a['key'])}/approve', body: {'her_tap': true}));
      if (mounted) setState(() => _c = c);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final acts = _l(_c['actions']);
    if (_c.isEmpty) return const SizedBox.shrink();
    final runs = _l(_c['runs']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.hub_rounded, color: C.muted, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Connectors (${acts.where((a) => a['approved'] == true).length} on)', style: display(15))),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Refresh'),
      ]),
      const Text('Courier / SMS / WhatsApp / e-mail / Sheets / accounts with your key. Every connector runs only when you approve it. '
          'Add a new pack and key on the app page of the web console.', style: TextStyle(color: C.muted, fontSize: 12)),
      if (acts.isEmpty) const Text('No connectors yet.', style: TextStyle(color: C.muted, fontSize: 12.5)),
      for (final a in acts)
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text(_s(a['label']), style: const TextStyle(color: C.ink)),
          subtitle: Text('${_s(_m(a['leaves'])['host'])} · ${_s(_m(a['leaves'])['when'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
          trailing: a['approved'] == true
              ? const Icon(Icons.check_circle_rounded, color: C.ok, size: 20)
              : TextButton(onPressed: _busy ? null : () => _approve(a), child: const Text('Approve')),
        ),
      if (runs.isNotEmpty) ...[
        const SizedBox(height: 4),
        Text('Previous runs', style: display(13.5)),
        for (final x in runs.take(6))
          Text('${_s(x['at']).length >= 16 ? _s(x['at']).substring(11, 16) : ''} · ${_s(x['action'])} · ${_s(x['status'])}${_s(x['note']).isNotEmpty ? ' · ${_s(x['note'])}' : ''}',
              style: const TextStyle(color: C.muted, fontSize: 12), maxLines: 2, overflow: TextOverflow.ellipsis),
      ],
    ]);
  }
}
