// v0.446 SURAKSHIT LOGIN (App Sahayak Pillar I): the ways into her app and the security check, on the phone.
// The client ids here are PUBLIC identifiers; no secret is asked for or accepted (native sign-in does not use one).
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

class AppLoginPanel extends StatefulWidget {
  const AppLoginPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppLoginPanel> createState() => _AppLoginPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
String _s(dynamic v) => v == null ? '' : '$v';

const _ways = [
  ['email_password', 'Email + password'],
  ['phone_otp', 'Mobile number + OTP'],
  ['google', 'Google se login'],
  ['apple', 'Apple se login'],
];

class _AppLoginPanelState extends State<AppLoginPanel> {
  Map<String, dynamic> _v = {};
  bool _busy = false;
  Map<String, dynamic>? _check;

  String get _base => '/api/apps/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = _m(await widget.app.api!.call('GET', '$_base/sign'));
      if (mounted) setState(() => _v = v);
    } catch (_) {}
  }

  Future<void> _save(List<String> ways, bool staff2fa) async {
    setState(() => _busy = true);
    try {
      final v = _m(await widget.app.api!.call('PUT', '$_base/sign', body: {'ways': ways, 'staff_2fa': staff2fa}));
      if (mounted) setState(() => _v = {..._v, ...v});
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Agli build se app mein dikhega.')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _run(String platform) async {
    setState(() => _busy = true);
    try {
      final v = _m(await widget.app.api!.call('POST', '$_base/security/check', body: {'platform': platform}));
      if (mounted) setState(() => _check = v);
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_v.isEmpty) return const SizedBox.shrink();
    final ways = (_v['ways'] as List? ?? const []).map((e) => '$e').toList();
    final problems = _m(_v['problems']);
    final gate = _m(_check ?? _v['gate']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.lock_outline_rounded, color: C.muted, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Login aur suraksha', style: display(15))),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Taaza karo'),
      ]),
      const Text('App ke log kaise login karte hain. Code ya token sirf server par jaancha jata hai, phone par kabhi nahi. '
          'Client SECRET ki zaroorat yahan nahi padti.', style: TextStyle(color: C.muted, fontSize: 12)),
      for (final w in _ways)
        CheckboxListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          value: ways.contains(w[0]),
          title: Text(w[1]),
          subtitle: _s(problems[w[0]]).isEmpty ? null : Text(_s(problems[w[0]]), style: const TextStyle(color: C.muted, fontSize: 11.5)),
          onChanged: _busy
              ? null
              : (on) {
                  final next = [...ways];
                  if (on == true) {
                    next.add(w[0]);
                  } else {
                    next.remove(w[0]);
                  }
                  _save(next, _v['staff_2fa'] == true);
                },
        ),
      SwitchListTile(
        dense: true,
        contentPadding: EdgeInsets.zero,
        value: _v['staff_2fa'] == true,
        title: const Text('Staff ke liye authenticator doosra step zaroori'),
        onChanged: _busy ? null : (on) => _save(ways, on),
      ),
      const Text('Google ya Apple ki client id web console ke app page par daaliye (public id hai).',
          style: TextStyle(color: C.muted, fontSize: 11.5)),
      const SizedBox(height: 8),
      Text('Suraksha jaanch', style: display(14)),
      const Text('App ke andar koi key, permissions, release settings, library CVE (OSV.dev), login aur data ke niyam. '
          'Fail hui to store par upload rukta hai.', style: TextStyle(color: C.muted, fontSize: 12)),
      if (gate.isNotEmpty && _s(gate['at']).isNotEmpty)
        Text('${_s(gate['platform'])} build ${_s(gate['build'])}: '
            '${gate['ok'] == true ? 'pass' : '${_s(gate['fail'])} fail'} · ${_s(gate['pass'])} pass, '
            '${_s(gate['warn'])} warn, ${_s(gate['not_checked'])} dekha nahi',
            style: TextStyle(color: gate['ok'] == true ? C.muted : Colors.redAccent, fontSize: 12.5)),
      for (final b in (gate['blocks'] as List? ?? const []).take(4))
        Text('• ${_s(b)}', style: const TextStyle(color: Colors.redAccent, fontSize: 11.5)),
      Wrap(spacing: 8, children: [
        OutlinedButton(onPressed: _busy ? null : () => _run('android'), child: const Text('Android jaancho')),
        OutlinedButton(onPressed: _busy ? null : () => _run('ios'), child: const Text('iPhone jaancho')),
      ]),
      if (_check != null)
        for (final row in _l(_check!['rows']).take(14))
          Text('${_s(row['state'])} · ${_s(row['check'])}: ${_s(row['say'])}',
              style: TextStyle(fontSize: 11.5, color: row['state'] == 'fail' ? Colors.redAccent : C.muted)),
    ]);
  }
}
