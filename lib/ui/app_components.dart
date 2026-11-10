// v0.425 RANG (App Sahayak Pillar G): her app's custom native components on the phone - describe one ("Likh do"),
// read what it does, Approve (her tap, after a confirm) or remove. The code itself is shown on the web console.
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

class AppComponentsPanel extends StatefulWidget {
  const AppComponentsPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppComponentsPanel> createState() => _AppComponentsPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
String _s(dynamic v) => v == null ? '' : '$v';

class _AppComponentsPanelState extends State<AppComponentsPanel> {
  List<Map<String, dynamic>> _c = [];
  bool _busy = false;
  final _words = TextEditingController();

  String get _base => '/api/apps/${widget.id}/components';

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

  Future<void> _load() async {
    try {
      final c = _m(await widget.app.api!.call('GET', _base));
      if (mounted) setState(() => _c = _l(c['components']));
    } catch (_) {}
  }

  void _say(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _draft() async {
    if (_words.text.trim().length < 8) return;
    setState(() => _busy = true);
    try {
      await widget.app.api!.call('POST', '$_base/draft', body: {'words': _words.text.trim()}, timeout: const Duration(seconds: 180));
      _words.clear();
      _say('The component is written - read it and approve.');
    } catch (e) {
      _say('$e');
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  Future<void> _approve(Map<String, dynamic> x) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text('Approve ${_s(x['name'])}?'),
        content: Text('${_s(x['purpose'])}\n\nDisplay-only part (no internet / files - checked by code). It will go into the app in the next build.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await widget.app.api!.call('POST', '$_base/${_s(x['name'])}/approve', body: {'her_tap': true});
    } catch (e) {
      _say('$e');
    }
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.widgets_rounded, color: C.muted, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Custom components', style: display(15))),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Refresh'),
      ]),
      const Text('When no ready-made part fits, write it here - Hoola will write one component for both Android + iPhone. It goes in the next build after you approve.',
          style: TextStyle(color: C.muted, fontSize: 12)),
      TextField(controller: _words, maxLength: 800, decoration: const InputDecoration(hintText: 'e.g. one bar for each star, how many ratings came')),
      FilledButton(onPressed: _busy ? null : _draft, child: Text(_busy ? 'Writing…' : 'Write it')),
      for (final x in _c)
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text(_s(x['name']), style: const TextStyle(color: C.ink)),
          subtitle: Text('${_s(x['status'])} · ${_s(x['purpose'])}${_s(x['error']).isNotEmpty ? ' · build: ${_s(x['error'])}' : ''}',
              style: const TextStyle(color: C.muted, fontSize: 12), maxLines: 3, overflow: TextOverflow.ellipsis),
          trailing: x['approved'] == true ? const Icon(Icons.check_circle_rounded, color: C.ok, size: 20)
              : TextButton(onPressed: () => _approve(x), child: const Text('Approve')),
        ),
    ]);
  }
}
