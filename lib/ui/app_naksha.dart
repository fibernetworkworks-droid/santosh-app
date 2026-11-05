// v0.542 NAKSHA (App Sahayak Pillar K): her one line as a whole plan, on her phone. She says yes to ONE module at a
// time - never to the whole thing at once - and each one says what she gets, what it needs first, and what it will
// ask of her. Building is her tap; nothing here builds anything on its own.
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

class AppNakshaPanel extends StatefulWidget {
  const AppNakshaPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppNakshaPanel> createState() => _AppNakshaPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
List<String> _ls(dynamic v) => v is List ? v.map((e) => '$e').toList() : <String>[];
String _s(dynamic v) => v == null ? '' : '$v';

const _state = {
  'waiting': 'Aapke Haan ka intezaar',
  'approved': 'Haan ho chuki',
  'built': 'Ban gaya',
  'failed': 'Bana, par dikkat hai',
  'changed': 'Banne ke baad badla hai',
};

class _Dim extends StatelessWidget {
  const _Dim(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Text(text, style: const TextStyle(color: C.muted, fontSize: 12));
}

class _AppNakshaPanelState extends State<AppNakshaPanel> {
  Map<String, dynamic> _v = {};
  final _words = TextEditingController();
  bool _busy = false;
  String _out = '';

  String get _base => '/api/apps/${widget.id}';

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
      final v = _m(await widget.app.api!.call('GET', '$_base/naksha'));
      if (mounted) setState(() => _v = v);
    } catch (_) {}
  }

  Future<void> _do(String what, Map<String, dynamic> body, String working) async {
    setState(() { _busy = true; _out = working; });
    try {
      final v = _m(await widget.app.api!.call('POST', '$_base/naksha/$what', body: body));
      if (mounted) setState(() => _out = _s(v['says']));
      await _load();
    } catch (e) {
      if (mounted) setState(() => _out = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final mods = _l(_v['modules']);
    final qs = _l(_v['questions']);
    final built = mods.where((m) => m['state'] == 'built').length;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.account_tree_outlined, color: C.muted, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('App ka naksha', style: display(15))),
        if (mods.isNotEmpty) _Dim('$built/${mods.length} bane'),
      ]),
      const _Dim('Aapki ek line se poori app ka naksha - kaun use karega, kya rakha jayega, kya hoga. Aap HAR MODULE '
          'par alag se Haan kehti hain; jis par Haan nahi, wo banta hi nahi.'),
      if (_s(_v['one_line']).isNotEmpty)
        Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(_v['one_line']), style: const TextStyle(fontWeight: FontWeight.w600))),
      const SizedBox(height: 8),
      TextField(
        controller: _words,
        decoration: InputDecoration(
          isDense: true,
          border: const OutlineInputBorder(),
          hintText: mods.isEmpty ? 'kirana dukaan ki app, ghar pe delivery' : 'badlav: riders ko bhi app chahiye',
        ),
      ),
      const SizedBox(height: 6),
      FilledButton(
        onPressed: _busy || _words.text.trim().isEmpty
            ? null
            : () => _do(mods.isEmpty ? 'plan' : 'revise', {'words': _words.text.trim()},
                mods.isEmpty ? 'Naksha bana rahi hoon…' : 'Badal rahi hoon…'),
        child: Text(mods.isEmpty ? 'Naksha banao' : 'Naksha badlo'),
      ),
      if (qs.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('Pehle ek baat', style: display(14)),
        const _Dim('Sirf wahi sawaal jinke jawab se build badalta hai.'),
        for (final q in qs) Padding(padding: const EdgeInsets.only(top: 4), child: _Dim('• ${_s(q['ask'])}')),
      ],
      const SizedBox(height: 10),
      for (final m in mods)
        Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(m['label']), style: const TextStyle(fontWeight: FontWeight.w600))),
                _Dim(_state[_s(m['state'])] ?? _s(m['state'])),
              ]),
              if (_s(m['why']).isNotEmpty) _Dim(_s(m['why'])),
              if (_ls(m['needs']).isNotEmpty) _Dim('Pehle chahiye: ${_ls(m['needs']).join(', ')}'),
              if (_ls(m['setup']).isNotEmpty) _Dim('Aapse chahiye hoga: ${_ls(m['setup']).join('; ')}'),
              if (_s(m['said']).isNotEmpty) _Dim(_s(m['said'])),
              const SizedBox(height: 4),
              Wrap(spacing: 8, children: [
                if (m['state'] == 'waiting' || m['state'] == 'changed')
                  FilledButton(
                      onPressed: _busy ? null : () => _do('approve', {'module': _s(m['key']), 'hash': _s(_v['hash'])}, ''),
                      child: const Text('Haan, yeh banao')),
                if (m['state'] == 'approved' || m['state'] == 'failed')
                  FilledButton(
                      onPressed: _busy ? null : () => _do('build', {'module': _s(m['key'])}, 'Bana rahi hoon…'),
                      child: const Text('Ab banao')),
              ]),
            ]),
          ),
        ),
      if (_out.isNotEmpty) _Dim(_out),
      if (_l(_v['changelog']).isNotEmpty) ...[
        const SizedBox(height: 8),
        Text('Kya kya hua', style: display(14)),
        for (final c in _l(_v['changelog']).take(6)) _Dim('• ${_s(c['said'])}'),
      ],
    ]);
  }
}
