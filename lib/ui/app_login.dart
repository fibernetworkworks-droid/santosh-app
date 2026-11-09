// v0.455 SURAKSHIT LOGIN (App Sahayak Pillar I): the ways into her app and the security check, on the phone.
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
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('It will show in the app from the next build.')));
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
        Expanded(child: Text('Login and security', style: display(15))),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Refresh'),
      ]),
      const Text('How the app\'s users log in. The code or token is checked only on the server, never on the phone. '
          'No client SECRET is needed here.', style: TextStyle(color: C.muted, fontSize: 12)),
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
        title: const Text('Authenticator second step required for staff'),
        onChanged: _busy ? null : (on) => _save(ways, on),
      ),
      const Text('Enter the Google or Apple client id on the app page in the web console (it is a public id).',
          style: TextStyle(color: C.muted, fontSize: 11.5)),
      const SizedBox(height: 8),
      Text('Security check', style: display(14)),
      const Text('Checks for keys inside the app, permissions, release settings, library CVEs (OSV.dev), and login and data rules. '
          'If a check fails, the store upload is blocked.', style: TextStyle(color: C.muted, fontSize: 12)),
      if (gate.isNotEmpty && _s(gate['at']).isNotEmpty)
        Text('${_s(gate['platform'])} build ${_s(gate['build'])}: '
            '${gate['ok'] == true ? 'pass' : '${_s(gate['fail'])} fail'} · ${_s(gate['pass'])} pass, '
            '${_s(gate['warn'])} warn, ${_s(gate['not_checked'])} not checked',
            style: TextStyle(color: gate['ok'] == true ? C.muted : Colors.redAccent, fontSize: 12.5)),
      for (final b in (gate['blocks'] as List? ?? const []).take(4))
        Text('• ${_s(b)}', style: const TextStyle(color: Colors.redAccent, fontSize: 11.5)),
      Wrap(spacing: 8, children: [
        OutlinedButton(onPressed: _busy ? null : () => _run('android'), child: const Text('Check Android')),
        OutlinedButton(onPressed: _busy ? null : () => _run('ios'), child: const Text('Check iPhone')),
      ]),
      if (_check != null)
        for (final row in _l(_check!['rows']).take(14))
          Text('${_s(row['state'])} · ${_s(row['check'])}: ${_s(row['say'])}',
              style: TextStyle(fontSize: 11.5, color: row['state'] == 'fail' ? Colors.redAccent : C.muted)),
    ]);
  }
}
