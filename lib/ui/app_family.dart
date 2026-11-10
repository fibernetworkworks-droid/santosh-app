// v0.435 PARIVAAR (App Sahayak Pillar H): the apps on one business (main app, delivery partner app, partner shop app,
// staff app) + the partners waiting for her Haan, on the phone. The rules (which statuses riders see, shop steps) and the
// web admin link are on the web console's app page; here she adds an app and decides partners.
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

class AppFamilyPanel extends StatefulWidget {
  const AppFamilyPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppFamilyPanel> createState() => _AppFamilyPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
String _s(dynamic v) => v == null ? '' : '$v';

class _AppFamilyPanelState extends State<AppFamilyPanel> {
  Map<String, dynamic> _f = {};
  bool _busy = false;

  String get _base => '/api/apps/${widget.id}/family';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final f = _m(await widget.app.api!.call('GET', _base));
      if (mounted) setState(() => _f = f);
    } catch (_) {}
  }

  Future<void> _run(Future<dynamic> Function() go, String done) async {
    setState(() => _busy = true);
    try {
      await go();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(done)));
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _add(String kind, String label) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text('$label banayein?'),
        content: const Text('A new app on the same app data: its own plan, design and build; accounts and orders stay the same.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes')),
        ],
      ),
    );
    if (ok != true) return;
    await _run(() => widget.app.api!.call('POST', '$_base/face', body: {'kind': kind}), 'The $label plan is ready.');
  }

  Future<void> _decide(Map<String, dynamic> p, String action) async {
    String link = '';
    if (action == 'approve' && p['kind'] == 'vendor') {
      final linkColl = _s(_m(_m(_f['settings'])['vendor'])['link']);
      if (linkColl.isEmpty) return;
      List<Map<String, dynamic>> shops = [];
      try {
        shops = _l(_m(await widget.app.api!.call('GET', '/api/apps/${widget.id}/data/$linkColl'))['rows']);
      } catch (_) {}
      if (!mounted) return;
      final pick = await showDialog<String>(
        context: context,
        builder: (c) => SimpleDialog(
          title: Text('${_s(p['name'])} which shop is it?'),
          children: [
            for (final sh in shops.take(60))
              SimpleDialogOption(onPressed: () => Navigator.pop(c, _s(sh['id'])), child: Text(_s(sh['name'] ?? sh['title'] ?? sh['id']))),
          ],
        ),
      );
      if (pick == null || pick.isEmpty) return;
      link = pick;
    } else if (action == 'remove') {
      final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          title: Text('${_s(p['name'])} ko hatayein?'),
          content: const Text('Their sign-in will stop and their open jobs will go back to everyone.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, remove')),
          ],
        ),
      );
      if (ok != true) return;
    }
    await _run(() => widget.app.api!.call('POST', '$_base/partners/${_s(p['id'])}', body: {'action': action, 'link_row': link}), 'Done.');
  }

  @override
  Widget build(BuildContext context) {
    if (_f.isEmpty) return const SizedBox.shrink();
    final faces = _l(_f['faces']);
    final partners = _l(_f['partners']);
    final kinds = _m(_f['kinds']);
    final problems = _m(_f['problems']);
    final have = faces.map((x) => _s(x['kind'])).toSet();
    final waiting = partners.where((p) => p['state'] == 'waiting').length;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.apps_rounded, color: C.muted, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('App parivaar (${faces.length}${waiting > 0 ? ' · $waiting ruke' : ''})', style: display(15))),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Refresh'),
      ]),
      const Text('More apps on this same data: delivery partner, partner shop (restaurant / seller), staff. Partners apply from their own app; '
          'only you (or the app admin) can approve.', style: TextStyle(color: C.muted, fontSize: 12)),
      for (final x in faces)
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text('${_s(x['name'])} (${_s(x['number'])})'),
          subtitle: Text('${x['kind'] == 'main' ? 'Main app' : _s(x['label'])} · ${_s(x['status'])}'),
        ),
      Wrap(spacing: 8, children: [
        for (final k in const ['rider', 'vendor', 'staff'])
          if (!have.contains(k))
            OutlinedButton(
              onPressed: _busy || _s(problems[k]).isNotEmpty ? null : () => _add(k, _s(kinds[k])),
              child: Text('+ ${_s(kinds[k])}'),
            ),
      ]),
      for (final k in const ['rider', 'vendor'])
        if (!have.contains(k) && _s(problems[k]).isNotEmpty)
          Text('${_s(kinds[k])}: ${_s(problems[k])}', style: const TextStyle(color: C.muted, fontSize: 12)),
      if (_s(_f['admin_url']).isNotEmpty)
        SelectableText('Web admin: ${_s(_f['admin_url'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
      if (partners.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text('Partners', style: display(14))),
      for (final p in partners.take(40))
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text(_s(p['name'])),
          subtitle: Text('${_s(p['label'])} · ${_s(p['state'])}${_s(p['link_name']).isNotEmpty ? ' · ${_s(p['link_name'])}' : ''}'),
          trailing: Wrap(spacing: 4, children: [
            if (p['state'] != 'approved')
              TextButton(onPressed: _busy ? null : () => _decide(p, 'approve'), child: const Text('Yes')),
            if (p['state'] == 'waiting')
              TextButton(onPressed: _busy ? null : () => _decide(p, 'refuse'), child: const Text('No')),
            if (p['state'] == 'approved')
              TextButton(onPressed: _busy ? null : () => _decide(p, 'remove'), child: const Text('Hatao')),
          ]),
        ),
    ]);
  }
}
