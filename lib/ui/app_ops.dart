// v0.546 CHALTA KAAM (App Sahayak Pillar L): her app AFTER it ships, on her phone. How many people use it, how fast
// its own backend answers, what is failing, what real phones reported, and what it has cost her - plus what the next
// big job cost her LAST times, before she starts it. Every number is measured; the speed bands say they are bands.
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

class AppOpsPanel extends StatefulWidget {
  const AppOpsPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppOpsPanel> createState() => _AppOpsPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
List<String> _ls(dynamic v) => v is List ? v.map((e) => '$e').toList() : <String>[];
String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
double _d(dynamic v) => v is num ? v.toDouble() : double.tryParse('$v') ?? 0;

class _Dim extends StatelessWidget {
  const _Dim(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Text(text, style: const TextStyle(color: C.muted, fontSize: 12));
}

class _AppOpsPanelState extends State<AppOpsPanel> {
  Map<String, dynamic> _v = {};
  String _out = '';
  bool _busy = false;

  String get _base => '/api/apps/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = _m(await widget.app.api!.call('GET', '$_base/ops'));
      if (mounted) setState(() => _v = v);
    } catch (_) {}
  }

  Future<void> _estimate(String job) async {
    setState(() { _busy = true; _out = '…'; });
    try {
      final v = _m(await widget.app.api!.call('POST', '$_base/ops/estimate', body: {'job': job}));
      if (mounted) setState(() => _out = _s(v['says']));
    } catch (e) {
      if (mounted) setState(() => _out = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final tr = _m(_v['traffic']);
    final cs = _m(_v['cost']);
    final fd = _m(_v['field']);
    final pe = _m(_v['people']);
    final alerts = _l(_v['alerts']);
    final gaps = _ls(_v['not_measured']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.monitor_heart_outlined, color: C.muted, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('How the app is doing', style: display(15))),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Refresh'),
      ]),
      const _Dim('Once an app is built, this is the part nobody watches: how many people, how fast, what is failing, '
          'and how much it costs. Everything is measured from your app\'s real calls.'),
      const SizedBox(height: 6),
      for (final a in alerts)
        Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(a['level'] == 'bad' ? Icons.error_outline : Icons.info_outline,
                size: 16, color: a['level'] == 'bad' ? C.bad : C.warn),
            const SizedBox(width: 6),
            Expanded(child: Text(_s(a['say']), style: const TextStyle(fontSize: 12.5))),
          ]),
        ),
      const SizedBox(height: 4),
      _row('Log', '${_i(pe['accounts'])} accounts · ${_i(pe['rows'])} rows'
          '${_i(pe['orders']) > 0 ? " · ${_i(pe['orders'])} orders" : ''}'),
      _row('Speed', _i(tr['calls']) == 0
          ? 'no calls yet'
          : 'half under ${_s(tr['p50'])}, 95% under ${_s(tr['p95'])} · slowest ${_i(tr['slowest_ms'])}ms'),
      _row('Fail', '${_i(tr['errors'])} / ${_i(tr['calls'])}'
          '${_i(tr['calls']) > 0 ? " (${tr['error_percent']}%)" : ''}'),
      _row('From phones', _s(fd['says'])),
      _row('Cost (30 days)', 'Rs ${_d(cs['inr']).toStringAsFixed(2)}'
          '${_ls(cs['not_priced']).isNotEmpty ? " · price not set: ${_ls(cs['not_priced']).join(', ')}" : ''}'),
      if (gaps.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: _Dim('Not measured yet: ${gaps.join('; ')}.')),
      const SizedBox(height: 10),
      Text('Before a big job', style: display(14)),
      const _Dim('What it cost YOU last time - not a number from a table.'),
      const SizedBox(height: 4),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final j in const ['build', 'ios', 'logic', 'naksha', 'jaanch'])
          OutlinedButton(onPressed: _busy ? null : () => _estimate(j), child: Text(j)),
      ]),
      if (_out.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: _Dim(_out)),
    ]);
  }

  Widget _row(String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 3),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 118, child: _Dim(k)),
          Expanded(child: Text(v, style: const TextStyle(fontSize: 12.5))),
        ]),
      );
}
