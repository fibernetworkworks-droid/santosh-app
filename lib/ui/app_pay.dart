// v0.419 PAISA (App Sahayak Pillar E): her own payment gateway for one app - join it (keys typed HERE, checked with the
// gateway, sealed on the server, never shown again), see online payments, refund by HER tap (after a confirm), make a
// payment link she sends herself. Plans, AutoPay, settlements and vendor payouts are on the web console's app page.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';

class AppPayPanel extends StatefulWidget {
  const AppPayPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppPayPanel> createState() => _AppPayPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
String _s(dynamic v) => v == null ? '' : '$v';
num _n(dynamic v) => v is num ? v : (num.tryParse('$v') ?? 0);
String _rs(dynamic p) => 'Rs ${(_n(p) / 100).toStringAsFixed(_n(p) % 100 == 0 ? 0 : 2)}';

class _AppPayPanelState extends State<AppPayPanel> {
  Map<String, dynamic> _p = {};
  bool _busy = false;
  String _gw = 'razorpay';
  bool _test = false;
  final Map<String, TextEditingController> _k = {};

  String get _base => '/api/apps/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in _k.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final p = _m(await widget.app.api!.call('GET', '$_base/pay'));
      if (mounted) setState(() => _p = p);
    } catch (_) {}
  }

  void _say(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  TextEditingController _c(String k) => _k.putIfAbsent(k, () => TextEditingController());

  Future<void> _join() async {
    setState(() => _busy = true);
    try {
      final fields = (_m(_p['fields'])[_gw] as List? ?? const []).map(_s);
      await widget.app.api!.call('PUT', '$_base/pay/keys', body: {
        'gateway': _gw,
        'test': _test,
        'keys': {for (final f in fields) f: _c('$_gw.$f').text.trim()},
      });
      for (final c in _k.values) {
        c.clear();
      }
      _say('Gateway connected. Enter the webhook address in your gateway dashboard.');
    } catch (e) {
      _say('$e');
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  Future<void> _refund(Map<String, dynamic> p) async {
    final amt = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text('Refund - ${_s(p['label'])}'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Paid ${_s(p['amount_rs'])}, refunded ${_rs(p['refunded'])}. The money goes back to the customer\'s original payment method (5-7 days).'),
          TextField(controller: amt, keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Amount (blank = all the rest)')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, refund')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '$_base/pay/${_s(p['id'])}/refund',
          body: {'amount': amt.text.trim().isEmpty ? null : amt.text.trim(), 'her_tap': true}));
      _say(_s(r['say']));
    } catch (e) {
      _say('$e');
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  Future<void> _link() async {
    final amt = TextEditingController(), what = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Payment link'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: amt, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Amount (Rs)')),
          TextField(controller: what, decoration: const InputDecoration(labelText: 'For what (e.g. credit)')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Make link')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = _m(await widget.app.api!.call('POST', '$_base/pay/link', body: {'amount': amt.text.trim(), 'purpose': what.text.trim(), 'her_tap': true}));
      if (_s(r['url']).isNotEmpty) {
        await Clipboard.setData(ClipboardData(text: _s(r['url'])));
        _say('Link copied - send it yourself by WhatsApp / SMS.');
      }
    } catch (e) {
      _say('$e');
    }
    _load();
  }

  @override
  Widget build(BuildContext context) {
    if (_p.isEmpty) return const SizedBox.shrink();
    final on = _p['on'] == true;
    final head = Row(children: [
      Icon(Icons.payments_rounded, color: on ? C.ok : C.muted, size: 20),
      const SizedBox(width: 6),
      Expanded(child: Text('Online payment${on ? ' · ${_s(_p['gateway'])}${_p['test'] == true ? ' (test)' : ''}' : ''}', style: display(15))),
      IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Refresh'),
    ]);
    if (!on) {
      final fields = (_m(_p['fields'])[_gw] as List? ?? const []).map(_s).toList();
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        head,
        const Text('Connect your gateway. The customer pays on the gateway\'s page, the money goes to your bank; Hoola never holds money. '
            'An order counts as paid only when the gateway itself says so. Enter the key here - never in the chat.', style: TextStyle(color: C.muted, fontSize: 12)),
        DropdownButton<String>(
          value: _gw,
          isExpanded: true,
          items: [for (final g in (_p['gateways'] as List? ?? const []).map(_s)) DropdownMenuItem(value: g, child: Text(g))],
          onChanged: (v) => setState(() => _gw = v ?? _gw),
        ),
        for (final f in fields)
          TextField(controller: _c('$_gw.$f'), obscureText: f.contains('secret') || f.contains('password'), autocorrect: false,
              enableSuggestions: false, decoration: InputDecoration(labelText: f.replaceAll('_', ' '))),
        CheckboxListTile(value: _test, onChanged: (v) => setState(() => _test = v ?? false), title: const Text('Test mode'),
            contentPadding: EdgeInsets.zero, dense: true),
        FilledButton(onPressed: _busy ? null : _join, child: const Text('Check and connect')),
      ]);
    }
    final t = _m(_p['totals']);
    final pays = _l(_p['payments']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      head,
      Text('Received: ${_rs(t['paid'])} (${_s(t['count'])}) · refund: ${_rs(t['refunded'])}${_n(t['mismatch']) > 0 ? ' · ${_s(t['mismatch'])} amount mismatch - please check' : ''}',
          style: const TextStyle(color: C.ink, fontSize: 12.5)),
      const SizedBox(height: 4),
      SelectableText('Webhook: ${_s(_p['webhook_url'])}', style: const TextStyle(color: C.muted, fontSize: 11.5)),
      if ((_p['can'] as List? ?? const []).contains('links'))
        TextButton.icon(onPressed: _link, icon: const Icon(Icons.link_rounded, size: 18), label: const Text('Make payment link')),
      for (final p in pays.take(15))
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text('${_s(p['label'])} · ${_s(p['amount_rs'])}', style: const TextStyle(color: C.ink)),
          subtitle: Text('${_s(p['status'])}${_n(p['refunded']) > 0 ? ' · refund ${_rs(p['refunded'])}' : ''} · ${_s(p['created']).length >= 16 ? _s(p['created']).substring(0, 16).replaceAll('T', ' ') : ''}',
              style: const TextStyle(color: C.muted, fontSize: 12)),
          trailing: p['status'] == 'paid' && _n(p['refunded']) < _n(p['amount'])
              ? TextButton(onPressed: _busy ? null : () => _refund(p), child: const Text('Refund'))
              : null,
        ),
    ]);
  }
}
