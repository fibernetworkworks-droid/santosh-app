import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';

/// v0.616 BAHAR SE BAAT: talk to your own Hoola from WhatsApp, Telegram, Slack and Microsoft Teams.
/// Only her: each channel shows a 6-digit pairing code; she sends "HOOLA <code>" from that app once, and from then
/// on only her account there reaches Hoola. WhatsApp uses HER own WhatsApp Business number through Meta's official
/// API - never personal WhatsApp.
class BaharScreen extends StatefulWidget {
  const BaharScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<BaharScreen> createState() => _BaharScreenState();
}

class _BaharScreenState extends State<BaharScreen> {
  List<Map<String, dynamic>> _rows = [];
  bool _loaded = false;
  String _busy = '';
  final Map<String, Map<String, dynamic>> _pair = {};

  static const _fields = {
    'whatsapp': <List<String>>[],
    'telegram': [['token', 'Bot token (@BotFather se)']],
    'slack': [['bot_token', 'Bot token (xoxb-...)'], ['signing_secret', 'Signing secret']],
    'teams': [['app_id', 'Microsoft App ID'], ['app_password', 'Client secret'], ['app_tenant', 'Tenant ID (single-tenant bot ho to)']],
  };
  static const _icons = {
    'whatsapp': Icons.chat_rounded,
    'telegram': Icons.send_rounded,
    'slack': Icons.tag_rounded,
    'teams': Icons.groups_rounded,
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.baharList();
      if (mounted) setState(() { _rows = r; _loaded = true; });
    } catch (e) {
      if (mounted) setState(() => _loaded = true);
      _say('$e');
    }
  }

  void _say(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  Future<void> _setup(String ch, Map<String, String> creds) async {
    setState(() => _busy = ch);
    try {
      final r = await widget.app.api!.baharSetup(ch, creds);
      _pair[ch] = r;
      await _load();
    } catch (e) {
      _say('$e');
    } finally {
      if (mounted) setState(() => _busy = '');
    }
  }

  Future<void> _remove(String ch, String label) async {
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
              title: Text('$label se Hoola hataayein?'),
              content: const Text('Wahan se Hoola ab jawab nahi dega. Us chat ki baatein Hoola app mein rahengi.'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Nahi')),
                TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Hataiye')),
              ],
            ));
    if (ok != true) return;
    try {
      await widget.app.api!.baharRemove(ch);
      _pair.remove(ch);
      await _load();
    } catch (e) {
      _say('$e');
    }
  }

  Future<void> _ask(String ch, String label) async {
    final fields = _fields[ch] ?? const <List<String>>[];
    if (fields.isEmpty) return _setup(ch, {});
    final ctrls = {for (final f in fields) f[0]: TextEditingController()};
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
              title: Text('$label jodiye'),
              content: SingleChildScrollView(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  const Text('Yeh keys sirf yahan daaliye - chat mein kabhi nahi. Server par band (encrypted) rehti hain.',
                      style: TextStyle(fontSize: 12, color: C.faint)),
                  for (final f in fields)
                    TextField(controller: ctrls[f[0]], obscureText: f[0] != 'app_id' && f[0] != 'app_tenant',
                        decoration: InputDecoration(labelText: f[1])),
                ]),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Rehne dijiye')),
                TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Jodiye')),
              ],
            ));
    final creds = {for (final e in ctrls.entries) e.key: e.value.text.trim()};
    for (final c in ctrls.values) {
      c.dispose();
    }
    if (ok == true) await _setup(ch, creds);
  }

  Widget _card(Map<String, dynamic> r) {
    final ch = '${r['channel']}';
    final label = '${r['label'] ?? ch}';
    final status = '${r['status'] ?? 'off'}';
    final pair = _pair[ch];
    final linked = status == 'linked';
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(_icons[ch] ?? Icons.chat_bubble_outline, color: linked ? C.ok : C.muted),
            const SizedBox(width: 10),
            Expanded(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15))),
            Text(linked ? 'Juda hai' : status == 'pairing' ? 'Code ka intezaar' : 'Band',
                style: TextStyle(color: linked ? C.ok : C.faint, fontSize: 12)),
          ]),
          const SizedBox(height: 6),
          if (ch == 'whatsapp')
            const Text('Aapke WhatsApp Business number se (Meta ka official API). Personal WhatsApp kabhi nahi. '
                'Graahak pehle jaise business inbox mein hi rahenge.', style: TextStyle(color: C.faint, fontSize: 12)),
          if (linked && '${r['paired_with'] ?? ''}'.isNotEmpty)
            Text('Sirf aap: ${r['paired_with']}', style: const TextStyle(color: C.muted, fontSize: 12)),
          if (r['webhook'] != null && !linked) ...[
            const SizedBox(height: 6),
            SelectableText('${r['webhook']}', style: const TextStyle(fontSize: 11.5, color: C.chip)),
          ],
          if (pair != null && !linked) ...[
            const SizedBox(height: 8),
            Row(children: [
              Text('HOOLA ${pair['code']}', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: C.accent)),
              IconButton(
                  icon: const Icon(Icons.copy_rounded, size: 18),
                  onPressed: () => Clipboard.setData(ClipboardData(text: 'HOOLA ${pair['code']}'))),
            ]),
            Text('${pair['how'] ?? ''} (code ${pair['code_minutes'] ?? 15} minute chalega)',
                style: const TextStyle(fontSize: 12.5, height: 1.4)),
          ],
          const SizedBox(height: 8),
          Wrap(spacing: 8, children: [
            if (_busy == ch)
              const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))
            else
              FilledButton.tonal(
                  onPressed: () => _ask(ch, label),
                  child: Text(status == 'off' ? 'Jodiye' : linked ? 'Naya code' : 'Code dobara')),
            if (status != 'off') TextButton(onPressed: () => _remove(ch, label), child: const Text('Hataiye')),
          ]),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Bahar se baat')),
      body: !_loaded
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                const Padding(
                  padding: EdgeInsets.only(bottom: 12),
                  child: Text(
                      'Apne Hoola se WhatsApp, Telegram, Slack ya Teams par baat kijiye - wahi yaad, wahi kaam. '
                      'Sirf aap: jodne ke baad jo code dikhe woh us app se bhejiye. Paisa / bhejna / delete ke card '
                      'hamesha Hoola app mein hi tap honge.',
                      style: TextStyle(color: C.muted, fontSize: 13, height: 1.4)),
                ),
                for (final r in _rows) _card(r),
              ]),
            ),
    );
  }
}
