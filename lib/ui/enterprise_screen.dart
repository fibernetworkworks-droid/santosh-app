import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.396 CONNECT — "Apne system jodiye": where her own ERP / CRM address and key are actually entered.
///
/// Everything the enterprise desks can do has existed since v0.358 and none of it could touch a real system,
/// because there was nowhere to put a credential. The chat refuses a key on purpose — a secret typed into a
/// conversation sits in the history, in the model's context and in any export of either — so this screen (and
/// the console's Systems page) is the only door. The key is sent once, sealed server-side the instant it
/// arrives, and no route ever returns it: after saving she only ever sees the masked form.
///
/// "Check" asks her real system, READ-ONLY, whether it works, and shows what it answered rather than a
/// green tick: a wrong key (401) is not a missing permission (403), and a CSRF token that cannot be fetched
/// means a write would fail later, so it is better said now.
class EnterpriseScreen extends StatefulWidget {
  const EnterpriseScreen({super.key, required this.app, this.role = 'erp'});
  final Santosh app;
  final String role;

  @override
  State<EnterpriseScreen> createState() => _EnterpriseScreenState();
}

class _EnterpriseScreenState extends State<EnterpriseScreen> {
  Map<String, dynamic>? _d;
  String? _err;
  String? _open; // which system's form is open
  bool _busy = false;
  Map<String, dynamic>? _verdict;
  String? _verdictFor;

  static const _kinds = {
    'bearer': 'Bearer token (OAuth)',
    'basic': 'Basic (user:pass, base64)',
    'header': 'API key in one header',
  };
  // what goes in the address box, per system — guessing the API URL is the commonest reason a join fails
  static const _hint = {
    'sap': 'https://<your-sap>/sap/opu/odata/sap/<SERVICE> — ask your Basis team for the full OData address',
    'oracle': 'https://<account>.suitetalk.api.netsuite.com/services/rest/record/v1',
    'salesforce': 'https://<your-org>.my.salesforce.com/services/data/v64.0',
    'windchill': 'https://<your-windchill>/Windchill/servlet/odata — if OAuth is on, use /Windchill/oauth/servlet/odata',
    'teamcenter': 'Read-only for now: Siemens\' real route is SOA, which Hoola does not speak',
  };

  final _addr = TextEditingController();
  final _key = TextEditingController();
  final _hdr = TextEditingController();
  String _kind = 'bearer';
  String _env = 'test';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _addr.dispose();
    _key.dispose();
    _hdr.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.entSystems(widget.role);
      if (mounted) {
        setState(() {
          _d = d;
          _err = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Map<String, dynamic>? _joined(String system) {
    for (final s in (_d?['systems'] as List? ?? const [])) {
      if (s is Map && s['system'] == system) return Map<String, dynamic>.from(s);
    }
    return null;
  }

  void _openForm(String system) {
    final live = _joined(system);
    setState(() {
      _open = system;
      _addr.text = (live?['base_url'] ?? '') as String;
      _key.text = '';
      _hdr.text = '';
      _kind = 'bearer';
      _env = (live?['env'] ?? 'test') as String;
    });
  }

  Future<void> _save(String system) async {
    final addr = _addr.text.trim();
    if (addr.isEmpty) {
      _say('The API address is needed.');
      return;
    }
    setState(() => _busy = true);
    try {
      await widget.app.api!.entConnect(widget.role, {
        'system': system,
        'base_url': addr,
        'auth': _key.text,
        'auth_kind': _kind,
        'env': _env,
        'header_name': _hdr.text.trim(),
      });
      _key.clear(); // never keep the key in the field
      if (mounted) setState(() => _open = null);
      await _load();
      await _verify(system);
    } catch (e) {
      _say('$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify(String system) async {
    setState(() {
      _busy = true;
      _verdictFor = system;
      _verdict = null;
    });
    try {
      final r = await widget.app.api!.entVerify(widget.role, system);
      if (mounted) setState(() => _verdict = r);
      if (r['theek'] == true) await _load();
    } catch (e) {
      if (mounted) setState(() => _verdict = {'theek': false, 'aage': '$e', 'jaanch': const []});
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _forget(String system) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Remove the address and key?'),
        content: const Text('Past jobs and papers stay as they are. Only the way in will be removed.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Keep it')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Remove')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await widget.app.api!.entForget(widget.role, system);
      if (mounted) setState(() => _verdict = null);
      await _load();
    } catch (e) {
      _say('$e');
    }
  }

  void _say(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  @override
  Widget build(BuildContext context) {
    final can = (_d?['jod_sakte_hain'] as List? ?? const []);
    return Scaffold(
      appBar: AppBar(title: const Text('Connect your systems')),
      body: _err != null
          ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(_err!)))
          : _d == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      Glass(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: const [
                          Text('Where the key goes', style: TextStyle(fontWeight: FontWeight.w600)),
                          SizedBox(height: 6),
                          Text('A key you enter here is encrypted the moment it arrives. No address '
                              'returns it - not this screen, not the chat, not the AI. Only •••• will show from now on.'),
                        ]),
                      ),
                      const SizedBox(height: 12),
                      for (final s in can)
                        if (s is Map) _systemCard(Map<String, dynamic>.from(s)),
                    ],
                  ),
                ),
    );
  }

  Widget _systemCard(Map<String, dynamic> sys) {
    final key = (sys['system'] ?? '') as String;
    if (key == 'sheet' || key == 'composio') return const SizedBox.shrink(); // no address needed
    final live = _joined(key);
    final readOnly = sys['how'] == 'read_only';
    final isOpen = _open == key;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Wrap(spacing: 8, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
            Text((sys['label'] ?? key) as String, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
            if (live == null) _chip('not connected') else _chip(live['verified'] == true ? 'verified' : 'connected, not verified', good: live['verified'] == true),
            if (readOnly) _chip('read-only'),
            if (live != null) _chip((live['env'] ?? '') as String, warn: live['env'] == 'production'),
          ]),
          if ((sys['note'] ?? '').toString().isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text(sys['note'] as String, style: const TextStyle(fontSize: 13, height: 1.4))),
          if (live != null && !isOpen) ...[
            const SizedBox(height: 8),
            Text('Address: ${live['base_url']}', style: const TextStyle(fontSize: 12.5)),
            Text('Key: ${live['auth'] ?? '••••'}  (sealed)', style: const TextStyle(fontSize: 12.5)),
          ],
          if (isOpen) _form(key, live) else _buttons(key, live),
          if (_verdictFor == key && (_busy || _verdict != null)) _verdictBox(),
        ]),
      ),
    );
  }

  Widget _buttons(String key, Map<String, dynamic>? live) => Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Wrap(spacing: 8, runSpacing: 8, children: [
          if (live == null)
            FilledButton(onPressed: _busy ? null : () => _openForm(key), child: const Text('Connect'))
          else ...[
            FilledButton(onPressed: _busy ? null : () => _verify(key), child: const Text('Check')),
            OutlinedButton(onPressed: _busy ? null : () => _openForm(key), child: const Text('Change')),
            OutlinedButton(onPressed: _busy ? null : () => _forget(key), child: const Text('Remove')),
          ],
        ]),
      );

  Widget _form(String key, Map<String, dynamic>? live) => Padding(
        padding: const EdgeInsets.only(top: 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(
            controller: _addr,
            autocorrect: false,
            decoration: const InputDecoration(labelText: 'API address', hintText: 'https://…'),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(_hint[key] ?? 'The system\'s API address, starting with https://', style: const TextStyle(fontSize: 12.5, height: 1.4)),
          ),
          const SizedBox(height: 10),
          DropdownButtonFormField<String>(
            value: _kind,
            decoration: const InputDecoration(labelText: 'Kind of key'),
            items: [for (final e in _kinds.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
            onChanged: (v) => setState(() => _kind = v ?? 'bearer'),
          ),
          if (_kind == 'header')
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: TextField(
                controller: _hdr,
                autocorrect: false,
                decoration: const InputDecoration(labelText: 'Header name', hintText: 'X-API-Key'),
              ),
            ),
          const SizedBox(height: 10),
          TextField(
            controller: _key,
            obscureText: true,
            autocorrect: false,
            enableSuggestions: false,
            decoration: InputDecoration(
              labelText: 'Key / token',
              hintText: live != null ? 'Leave blank to keep it as it is' : 'Enter it here',
            ),
          ),
          const SizedBox(height: 10),
          DropdownButtonFormField<String>(
            value: _env,
            decoration: const InputDecoration(labelText: 'Which system it is'),
            items: const [
              DropdownMenuItem(value: 'test', child: Text('Test / sandbox')),
              DropdownMenuItem(value: 'production', child: Text('PRODUCTION (real)')),
            ],
            onChanged: (v) => setState(() => _env = v ?? 'test'),
          ),
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('Even if you choose Production, nothing is written without your yes - and along with the yes '
                "you must type 'production'.",
                style: TextStyle(fontSize: 12.5, height: 1.4)),
          ),
          const SizedBox(height: 12),
          Wrap(spacing: 8, children: [
            FilledButton(onPressed: _busy ? null : () => _save(key), child: Text(_busy ? 'Please wait…' : 'Save and check')),
            OutlinedButton(onPressed: _busy ? null : () => setState(() => _open = null), child: const Text('Keep it')),
          ]),
        ]),
      );

  Widget _verdictBox() {
    if (_verdict == null) {
      return const Padding(
        padding: EdgeInsets.only(top: 12),
        child: Row(children: [
          SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
          SizedBox(width: 8),
          Expanded(child: Text('Asking the system… (nothing will be written)', style: TextStyle(fontSize: 13))),
        ]),
      );
    }
    final ok = _verdict!['theek'] == true;
    final rows = (_verdict!['jaanch'] as List? ?? const []);
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(ok ? 'Working' : 'Not working right now', style: const TextStyle(fontWeight: FontWeight.w600)),
        for (final j in rows)
          if (j is Map)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(j['theek'] == true ? Icons.check : j['theek'] == false ? Icons.close : Icons.info_outline, size: 16),
                const SizedBox(width: 6),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${j['kya']}', style: const TextStyle(fontSize: 13)),
                    if ((j['kaha'] ?? '').toString().isNotEmpty)
                      Text('${j['kaha']}', style: const TextStyle(fontSize: 12.5, height: 1.4)),
                  ]),
                ),
              ]),
            ),
        if ((_verdict!['aage'] ?? '').toString().isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('${_verdict!['aage']}', style: const TextStyle(fontSize: 12.5, height: 1.4)),
          ),
      ]),
    );
  }

  Widget _chip(String t, {bool good = false, bool warn = false}) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Theme.of(context).dividerColor),
        ),
        child: Text(t, style: TextStyle(fontSize: 12, fontWeight: good || warn ? FontWeight.w600 : FontWeight.w400)),
      );
}
