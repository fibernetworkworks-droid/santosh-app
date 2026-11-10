// v0.412 NAKSHA LIVE (App Sahayak Pillar D): her live-tracking switch for one app (which list, which statuses mean "on
// the way") and every rider on shift right now (open in Maps). The live map of all riders is on the web console's app page.
// Staff start / end their own shift in the app; their location is shared only during the shift, and a customer sees only
// the rider bringing HER order.
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

class AppTrackPanel extends StatefulWidget {
  const AppTrackPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppTrackPanel> createState() => _AppTrackPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
String _s(dynamic v) => v == null ? '' : '$v';

class _AppTrackPanelState extends State<AppTrackPanel> {
  Map<String, dynamic> _t = {};
  String _coll = '';
  Set<String> _st = {};
  bool _busy = false;

  String get _base => '/api/apps/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final t = _m(await widget.app.api!.call('GET', '$_base/track'));
      if (!mounted) return;
      setState(() {
        _t = t;
        _coll = _s(t['coll']);
        _st = {for (final x in (t['statuses'] is List ? t['statuses'] as List : const [])) _s(x)};
      });
    } catch (_) {}
  }

  void _say(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _save(bool on) async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.call('PUT', '$_base/track', body: {'on': on, 'coll': _coll, 'statuses': _st.toList()});
      _say(on ? 'Live tracking is on. Build the app again for it to reach phones.' : 'Live tracking is off.');
    } catch (e) {
      _say('$e');
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final lists = _l(_t['lists']).where((x) => (x['statuses'] is List) && (x['statuses'] as List).isNotEmpty).toList();
    if (_t.isEmpty || lists.isEmpty) return const SizedBox.shrink();
    final cur = lists.firstWhere((x) => _s(x['key']) == _coll, orElse: () => lists.first);
    final on = _t['on'] == true;
    final riders = _l(_t['riders']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Icon(Icons.delivery_dining_rounded, color: on ? C.ok : C.muted, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Live tracking${on ? ' · on' : ''}', style: display(15))),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Refresh'),
      ]),
      const Text('Staff tap Start shift in the app; location is shared only during the shift. A customer sees only the rider bringing their own order, '
          'and only while the order is on the way.', style: TextStyle(color: C.muted, fontSize: 12)),
      const SizedBox(height: 8),
      DropdownButton<String>(
        value: _s(cur['key']),
        isExpanded: true,
        items: [for (final x in lists) DropdownMenuItem(value: _s(x['key']), child: Text(_s(x['label'])))],
        onChanged: (v) => setState(() { _coll = v ?? _coll; _st = {}; }),
      ),
      const Text('When to count it as on the way:', style: TextStyle(color: C.muted, fontSize: 12)),
      Wrap(spacing: 6, children: [
        for (final s in (cur['statuses'] as List).map(_s))
          FilterChip(label: Text(s), selected: _st.contains(s), onSelected: (v) => setState(() => v ? _st.add(s) : _st.remove(s))),
      ]),
      if (cur['location'] != true)
        const Text('This list has no location field: the map will show the rider, not the customer\'s place.', style: TextStyle(color: C.muted, fontSize: 12)),
      const SizedBox(height: 8),
      Row(children: [
        FilledButton(onPressed: _busy || _st.isEmpty ? null : () => _save(true), child: Text(on ? 'Save' : 'Turn tracking on')),
        const SizedBox(width: 8),
        if (on) TextButton(onPressed: _busy ? null : () => _save(false), child: const Text('Turn off')),
      ]),
      if (on) ...[
        const SizedBox(height: 8),
        Text(riders.isEmpty ? 'Nobody is on shift right now.' : 'On shift: ${riders.length}', style: display(13.5)),
        for (final r in riders)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Icon(Icons.circle, size: 12, color: r['fresh'] == true ? C.ok : C.muted),
            title: Text(_s(r['name']), style: const TextStyle(color: C.ink)),
            subtitle: Text('${_s(r['orders'])} orders on the way${_s(r['at']).length >= 16 ? ' · ${_s(r['at']).substring(11, 16)} UTC' : ''}',
                style: const TextStyle(color: C.muted, fontSize: 12)),
            trailing: r['lat'] == null
                ? null
                : IconButton(
                    icon: const Icon(Icons.map_rounded, color: C.muted),
                    tooltip: 'View on map',
                    onPressed: () => launchUrl(Uri.parse('https://www.google.com/maps/search/?api=1&query=${r['lat']},${r['lng']}'),
                        mode: LaunchMode.externalApplication)),
          ),
      ],
    ]);
  }
}
