// v0.376 MAALKIN PHONE (App Sahayak Phase 40): her money tools for an app on her phone - the month's hisaab line, who owes
// udhaar (WhatsApp her own reminder / write "paise mile"), stock running low and the live coupon codes. Everything the web
// console's app data page has for these, read and written through the same owner routes.
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

class AppMoneyPanel extends StatefulWidget {
  const AppMoneyPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppMoneyPanel> createState() => _AppMoneyPanelState();
}

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : [];
String _s(dynamic v) => v == null ? '' : '$v';
num _n(dynamic v) => v is num ? v : (num.tryParse('$v') ?? 0);
String _rs(dynamic v) => '₹${_n(v).toStringAsFixed(_n(v) % 1 == 0 ? 0 : 2)}';

class _AppMoneyPanelState extends State<AppMoneyPanel> {
  Map<String, dynamic> _hisaab = {};
  List<Map<String, dynamic>> _owe = [];
  List<Map<String, dynamic>> _low = [];
  List<Map<String, dynamic>> _codes = [];
  bool _loaded = false;
  final Map<String, TextEditingController> _paid = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in _paid.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<Map<String, dynamic>> _get(String path) async {
    try {
      return _m(await widget.app.api!.call('GET', '/api/apps/${widget.id}/$path'));
    } catch (_) {
      return {};
    }
  }

  Future<void> _load() async {
    final h = await _get('hisaab');
    final y = await _get('khata-yaad');
    final st = await _get('stock');
    final cp = await _get('coupons');
    if (!mounted) return;
    setState(() {
      _hisaab = h;
      _owe = _l(y['customers']);
      _low = _l(st['products']).where((p) => p['qty'] != null && _n(p['qty']) <= _n(p['low'] ?? 3)).toList();
      _codes = _l(cp['coupons']).where((c) => c['live'] == true).toList();
      _loaded = true;
    });
  }

  Future<void> _gotPaid(Map<String, dynamic> c) async {
    final ctl = _paid[_s(c['member'])];
    final amt = (ctl?.text ?? '').trim();
    if (amt.isEmpty) return;
    try {
      await widget.app.api!.call('POST', '/api/apps/${widget.id}/khata/${_s(c['member'])}/pay', body: {'amount': amt, 'mode': 'cash'});
      ctl?.clear();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${_s(c['name'])}: $amt noted.')));
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.account_balance_wallet_rounded, color: C.ok, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Money and accounts', style: display(15))),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Refresh'),
      ]),
      if (!_loaded) const Text('Loading…', style: TextStyle(color: C.muted, fontSize: 12.5)),
      if (_s(_hisaab['say']).isNotEmpty) Text(_s(_hisaab['say']), style: const TextStyle(color: C.ink, fontSize: 13)),
      if (_owe.isNotEmpty) ...[
        const SizedBox(height: 8),
        Text('Credit pending (${_owe.length})', style: display(13.5)),
        for (final c in _owe.take(30))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Row(children: [
              Expanded(child: Text('${_s(c['name'])} · ${_rs(c['balance'])}', style: const TextStyle(color: C.ink, fontSize: 12.5))),
              if (_s(c['link']).isNotEmpty)
                TextButton(
                  onPressed: () => launchUrl(Uri.parse(_s(c['link'])), mode: LaunchMode.externalApplication),
                  child: const Text('Open in WhatsApp'),
                ),
              SizedBox(
                width: 70,
                child: TextField(
                  controller: _paid.putIfAbsent(_s(c['member']), () => TextEditingController()),
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  style: const TextStyle(color: C.ink, fontSize: 12.5),
                  decoration: const InputDecoration(hintText: '₹', isDense: true),
                ),
              ),
              IconButton(onPressed: () => _gotPaid(c), icon: const Icon(Icons.check_circle_rounded, color: C.ok, size: 20), tooltip: 'Money received'),
            ]),
          ),
      ],
      if (_low.isNotEmpty) ...[
        const SizedBox(height: 8),
        Text('Low stock', style: display(13.5)),
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final p in _low) Pill('${_s(p['name'])}: ${_n(p['qty']) == 0 ? 'out of stock' : '${_n(p['qty'])} left'}', fg: _n(p['qty']) == 0 ? C.bad : C.warn),
        ]),
      ],
      if (_codes.isNotEmpty) ...[
        const SizedBox(height: 8),
        Text('Active coupons', style: display(13.5)),
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final c in _codes)
            Pill('${_s(c['code'])} · ${c['kind'] == 'percent' ? '${_n(c['value'])}%' : _rs(c['value'])} · ${_n(c['used'])} times', fg: C.accent),
        ]),
      ],
      if (_loaded && _owe.isEmpty && _low.isEmpty && _codes.isEmpty && _s(_hisaab['say']).isEmpty)
        const Text('Nothing to show yet.', style: TextStyle(color: C.faint, fontSize: 12.5)),
    ]);
  }
}
