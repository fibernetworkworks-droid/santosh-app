/// Profile > Order karo (v0.80): Hoola orders / books from shopping, grocery, food and travel sites up to the payment;
/// the owner pays herself. Shows her orders with their status and starts a new one.
library;

import 'package:flutter/material.dart';

import '../api.dart';
import '../state.dart';
import 'glass.dart';

class ShopScreen extends StatefulWidget {
  const ShopScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ShopScreen> createState() => _ShopScreenState();
}

class _ShopScreenState extends State<ShopScreen> {
  List<Map<String, dynamic>>? _orders;
  List<Map<String, dynamic>> _sites = const [];
  final _what = TextEditingController();
  final _budget = TextEditingController();
  String _site = '';
  bool _busy = false;
  String? _err;
  Api get _api => widget.app.api!;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _what.dispose();
    _budget.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final o = await _api.shopOrders();
      final s = _sites.isEmpty ? await _api.shopSites() : _sites;
      if (mounted) setState(() {
        _orders = o;
        _sites = s;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _order() async {
    final what = _what.text.trim();
    if (what.length < 3) return;
    setState(() => _busy = true);
    try {
      final r = await _api.shopOrder(what, site: _site, budget: _budget.text.trim(), conversationId: widget.app.conversationId ?? '');
      _what.clear();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${r['say'] ?? 'Order shuru'}')));
      }
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  static const _words = {
    'working': 'Taiyaar ho raha hai',
    'waiting_payment': 'Aapke payment ka intezaar',
    'placed': 'Order ho gaya',
    'failed': 'Nahi ho paya',
    'cancelled': 'Band kiya',
  };

  Color _col(String s) => s == 'placed' ? C.teal : (s == 'waiting_payment' ? C.warn : (s == 'failed' ? C.bad : C.accentSoft));

  @override
  Widget build(BuildContext context) {
    final name = widget.app.aName;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Order karo')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('$name item dhoondh ke, sahi size / quantity chun ke, cart, address aur slot tak sab karta hai. '
                    'Aakhri payment aap khud karti hain (card aayega, ya apne UPI app mein).',
                    style: const TextStyle(color: C.chip, height: 1.35, fontSize: 13)),
                const SizedBox(height: 10),
                TextField(
                  controller: _what,
                  minLines: 1,
                  maxLines: 3,
                  decoration: const InputDecoration(hintText: 'Jaise: Blinkit se 2 litre Amul doodh aur 1 brown bread'),
                ),
                const SizedBox(height: 8),
                Row(children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _site,
                      isExpanded: true,
                      decoration: const InputDecoration(labelText: 'Site'),
                      items: [
                        const DropdownMenuItem(value: '', child: Text('Hoola chune')),
                        for (final s in _sites) DropdownMenuItem(value: '${s['id']}', child: Text('${s['name']}')),
                      ],
                      onChanged: (v) => setState(() => _site = v ?? ''),
                    ),
                  ),
                  const SizedBox(width: 10),
                  SizedBox(
                    width: 110,
                    child: TextField(controller: _budget, decoration: const InputDecoration(labelText: 'Budget ₹'), keyboardType: TextInputType.number),
                  ),
                ]),
                const SizedBox(height: 12),
                GradientButton(label: _busy ? 'Shuru ho raha hai...' : 'Order taiyaar karo', icon: Icons.shopping_bag_rounded, height: 48, onTap: _busy ? null : _order),
              ]),
            ),
            const SizedBox(height: 14),
            if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
            if (_orders == null && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (_orders != null && _orders!.isEmpty)
              const Padding(padding: EdgeInsets.all(24), child: Center(child: Text('Abhi koi order nahi.', style: TextStyle(color: C.muted)))),
            for (final o in _orders ?? const <Map<String, dynamic>>[])
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(child: Text('${o['site_name']}', style: const TextStyle(fontWeight: FontWeight.w800))),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(color: _col('${o['status']}').withOpacity(.18), borderRadius: BorderRadius.circular(8)),
                        child: Text(_words['${o['status']}'] ?? '${o['status']}',
                            style: TextStyle(color: _col('${o['status']}'), fontSize: 11.5, fontWeight: FontWeight.w700)),
                      ),
                    ]),
                    const SizedBox(height: 4),
                    Text('${o['what']}', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
                    if ('${o['total'] ?? ''}'.isNotEmpty || '${o['order_ref'] ?? ''}'.isNotEmpty)
                      Text([if ('${o['total']}'.isNotEmpty) '${o['total']}', if ('${o['order_ref']}'.isNotEmpty) 'Order ${o['order_ref']}'].join(' · '),
                          style: const TextStyle(color: C.teal, fontSize: 12)),
                    if ('${o['summary'] ?? ''}'.isNotEmpty)
                      Text('${o['summary']}', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                ),
              ),
          ]),
        ),
      ),
    );
  }
}
