// v0.540 JAANCH (App Sahayak Pillar J): on her phone - what has really been proved about her app, what real phones
// reported, and the staged rollout she controls. Nothing here runs against her live app: the scenario tests play on a
// throwaway copy. Giving a build to more users, and sending an old one back, are her taps and nobody else's.
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

class AppJaanchPanel extends StatefulWidget {
  const AppJaanchPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppJaanchPanel> createState() => _AppJaanchPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;

/// Small grey line, the same one the other app panels use.
class _Dim extends StatelessWidget {
  const _Dim(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Text(text, style: const TextStyle(color: C.muted, fontSize: 12));
}

class _AppJaanchPanelState extends State<AppJaanchPanel> {
  Map<String, dynamic> _j = {};
  Map<String, dynamic> _ro = {};
  bool _busy = false;
  String _out = '';

  String get _base => '/api/apps/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final j = _m(await widget.app.api!.call('GET', '$_base/jaanch'));
      Map<String, dynamic> ro = {};
      try {
        ro = _m(await widget.app.api!.call('GET', '$_base/rollout'));
      } catch (_) {}
      if (mounted) setState(() { _j = j; _ro = ro; });
    } catch (_) {}
  }

  Future<void> _do(String path, {Map<String, dynamic>? body, String working = 'Chal raha hai…'}) async {
    setState(() { _busy = true; _out = working; });
    try {
      final v = _m(await widget.app.api!.call('POST', '$_base/$path', body: body ?? {}));
      if (mounted) setState(() => _out = _s(v['says']).isNotEmpty ? _s(v['says']) : 'Ho gaya.');
      await _load();
    } catch (e) {
      if (mounted) setState(() => _out = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<bool> _ask(String q) async =>
      await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          content: Text(q),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Nahi')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan')),
          ],
        ),
      ) ??
      false;

  @override
  Widget build(BuildContext context) {
    final last = _m(_j['last_run']);
    final field = _m(_j['field']);
    final rl = _m(_ro['rollout']);
    final flags = _l(_ro['flags']);
    final gaps = (_j['not_checked'] is List) ? (_j['not_checked'] as List).map(_s).toList() : <String>[];
    final pct = ((_m(_ro['rollout'])['fraction'] ?? 0) as num) * 100;
    final running = _s(rl['status']) == 'inProgress';
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Jaanch', style: display(15)),
      const _Dim('Aapki app saabit hoti hai, maani nahi jaati: har kahani ek copy par chal kar dekhi jaati hai - '
          'sign up, order, aur doosre customer ko MANA hona. Aapka asli data kabhi chhua nahi jata.'),
      const SizedBox(height: 6),
      if (last.isEmpty)
        const _Dim('Abhi tak ek baar bhi nahi chali.')
      else
        Text('${_i(last['pass'])}/${_i(last['total'])} kahaniyan pass'
            '${_i(last['fail']) > 0 ? " · ${_i(last['fail'])} fail" : ''}'
            '${_i(last['not_run']) > 0 ? " · ${_i(last['not_run'])} chal nahi payi" : ''}',
            style: const TextStyle(fontWeight: FontWeight.w600)),
      if (_s(last['says']).isNotEmpty) _Dim(_s(last['says'])),
      for (final f in _l(last['failed'])) _Dim('• ${_s(f['story'])}: ${_s(f['why'])}'),
      const SizedBox(height: 6),
      Wrap(spacing: 8, runSpacing: 8, children: [
        OutlinedButton(onPressed: _busy ? null : () => _do('jaanch/stories', working: 'Kahaniyan likh rahi hoon…'),
            child: const Text('Kahaniyan banao')),
        FilledButton(onPressed: _busy ? null : () => _do('jaanch/run', working: 'Chala rahi hoon…'),
            child: const Text('Jaanch chalao')),
        OutlinedButton(onPressed: _busy ? null : () => _do('jaanch/rules', working: 'Rules dekh rahi hoon…'),
            child: const Text('Rules dekho')),
      ]),
      if (_out.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: _Dim(_out)),
      const SizedBox(height: 10),
      Text('Asli phones se', style: display(15)),
      _Dim(_s(field['says'])),
      for (final c in _l(field['top']).take(3))
        _Dim('• ${_s(c['kind'])} ×${_i(c['count'])} · ${_s(c['what'])}'),
      if (gaps.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: _Dim('Abhi tak nahi hua: ${gaps.join('; ')}.')),
      const SizedBox(height: 10),
      Text('Dheere chhodna', style: display(15)),
      const _Dim('Nayi version pehle 5% logon ko, phir 20, 50, 100 - har kadam aapka tap. Galat lage to turant rokiye. '
          'Jin phones mein chali gayi hai unse Play version hata nahi sakta; rok dene se baaki sabko nahi jayegi.'),
      if (rl['version_code'] == null)
        const _Dim('Abhi koi staged rollout nahi chal raha.')
      else
        Text('v${_s(rl['version_name']).isNotEmpty ? _s(rl['version_name']) : _s(rl['version_code'])} · '
            '${_s(rl['status']) == 'halted' ? 'ROKA hua' : '${pct.round()}% users'}',
            style: const TextStyle(fontWeight: FontWeight.w600)),
      Wrap(spacing: 8, runSpacing: 8, children: [
        if (running)
          FilledButton(
              onPressed: _busy
                  ? null
                  : () async {
                      if (await _ask('Is version ko aur logon tak pahunchaun?')) _do('rollout/advance', body: {'her_tap': true});
                    },
              child: const Text('Aur logon ko do')),
        if (running) OutlinedButton(onPressed: _busy ? null : () => _do('rollout/halt'), child: const Text('Roko')),
        if (_ro['can_rollback'] == true)
          OutlinedButton(
              onPressed: _busy
                  ? null
                  : () async {
                      if (await _ask('Purani build wapas sabko bhejun?')) _do('rollout/rollback', body: {'her_tap': true});
                    },
              child: const Text('Purani wapas')),
      ]),
      if (flags.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('Feature switch', style: display(15)),
        const _Dim('Bina nayi build ke kuch band kijiye - yahi ek badlav hai jo minuton mein har phone tak pahunchta hai.'),
        for (final f in flags)
          SwitchListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text(_s(f['label']).isNotEmpty ? _s(f['label']) : _s(f['key'])),
            subtitle: _Dim(_i(f['percent']) < 100 ? '${_i(f['percent'])}% users' : 'sab users'),
            value: f['on'] == true,
            onChanged: _busy ? null : (v) => _do('rollout/flag', body: {'key': _s(f['key']), 'on': v}, working: ''),
          ),
      ],
    ]);
  }
}
